"""LLM provider abstraction.

AgentOrchestrator speaks ONE wire shape - Anthropic Messages-style content
blocks with a `.messages.create(...)` client surface:

    response.stop_reason in {'tool_use', 'end_turn', ...}
    response.content = [{'type': 'text', 'text': ...} |
                        {'type': 'tool_use', 'id': ..., 'name': ..., 'input': {...}}]

Providers:
  anthropic (default, the assignment's requirement) - thin pass-through over
  the official SDK.
  gemini - Google's OpenAI-compatible endpoint reached over httpx, with
  bidirectional translation of messages/tools/responses. Lets a Gemini key
  drive the exact same orchestration loop when no Anthropic key exists.
"""

from __future__ import annotations

import json
import uuid
from typing import Any


# --------------------------------------------------------------------------
# schema + message translation (OpenAI-compatible wire format)
# --------------------------------------------------------------------------
def tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object"}),
            },
        }
        for tool in tools
    ]


def _assistant_blocks_to_openai(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(b.get("text", "") for b in blocks if b["type"] == "text").strip()
    message: dict[str, Any] = {"role": "assistant", "content": text or None}
    tool_calls = [
        {
            "id": b.get("id") or f"call_{uuid.uuid4().hex[:12]}",
            "type": "function",
            "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})},
        }
        for b in blocks
        if b["type"] == "tool_use"
    ]
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _user_blocks_to_openai(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Anthropic tool_result blocks become one OpenAI 'tool' message each."""
    converted: list[dict[str, Any]] = []
    texts = [b.get("text", "") for b in blocks if b["type"] == "text"]
    if texts:
        converted.append({"role": "user", "content": "\n".join(texts)})
    for block in blocks:
        if block["type"] == "tool_result":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": block.get("tool_use_id", ""),
                    "content": str(block.get("content", "")),
                }
            )
    return converted


def messages_to_openai(
    system: str | None, messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    if system:
        converted.append({"role": "system", "content": system})
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            converted.append({"role": msg["role"], "content": content})
        elif isinstance(content, list):
            if msg["role"] == "assistant":
                converted.append(_assistant_blocks_to_openai(content))
            else:
                converted.extend(_user_blocks_to_openai(content))
    return converted


class _OpenAIStyleResponse:
    """Normalizes an OpenAI-shaped payload into Anthropic-style attributes."""

    def __init__(self, payload: dict[str, Any]):
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}

        blocks: list[dict[str, Any]] = []
        text = message.get("content")
        if isinstance(text, list):  # some providers return content parts
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
        if text:
            blocks.append({"type": "text", "text": text})
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {"_raw_arguments": function.get("arguments")}
            blocks.append(
                {
                    "type": "tool_use",
                    "id": call.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                    "name": function.get("name", ""),
                    "input": arguments,
                }
            )

        self.content: list[dict[str, Any]] = blocks
        finish = choice.get("finish_reason")
        self.stop_reason = "tool_use" if finish == "tool_calls" else "end_turn"
        usage = payload.get("usage") or {}
        self.usage = {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
        }


class _MessagesNamespace:
    def __init__(self, create_callable):
        self.create = create_callable


class OpenAICompatClient:
    """`.messages.create()`-compatible client over any OpenAI-compatible API.

    Covers Gemini's compat endpoint, OpenRouter, and similar gateways.
    """

    def __init__(self, api_key: str, base_url: str, model: str, extra_headers: dict | None = None):
        import httpx

        if not api_key or api_key.startswith("your-"):
            raise RuntimeError(
                "No API key configured for this provider - check the *_API_KEY "
                "value in backend/.env"
            )
        self.model = model
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}", **(extra_headers or {})}
        self._http = httpx.Client(timeout=120)
        self.messages = _MessagesNamespace(self._create)

    def _create(
        self,
        *,
        model: str | None = None,
        max_tokens: int,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        messages: list[dict[str, Any]],
    ) -> _OpenAIStyleResponse:
        import time

        body: dict[str, Any] = {
            "model": model or self.model,
            "max_tokens": max_tokens,
            "messages": messages_to_openai(system, messages),
        }
        if tools:
            body["tools"] = tools_to_openai(tools)
            body["tool_choice"] = "auto"

        last_error = ""
        for attempt in range(4):
            response = self._http.post(self._url, json=body, headers=self._headers)
            if response.status_code == 200:
                return _OpenAIStyleResponse(response.json())
            last_error = f"({response.status_code}): {response.text[:300]}"
            if response.status_code in (429, 500, 502, 503) and attempt < 3:
                wait = 25.0 * (attempt + 1)  # free tiers throttle per-minute
                time.sleep(wait)
                continue
            break
        raise RuntimeError(f"LLM provider request failed {last_error}")


class AnthropicClientAdapter:
    """Pass-through exposing the SDK's native .messages.create surface."""

    def __init__(self, sdk_client: Any):
        self.messages = sdk_client.messages


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------
def build_llm_client() -> Any:
    from app.config import get_settings

    settings = get_settings()
    provider = (settings.llm_provider or "anthropic").lower()

    if provider == "anthropic":
        key = settings.anthropic_api_key
        if not key or key.startswith("sk-ant-your-key"):
            raise RuntimeError(
                "No LLM API key configured - set ANTHROPIC_API_KEY (or "
                "LLM_PROVIDER=gemini + GEMINI_API_KEY) in backend/.env"
            )
        from anthropic import Anthropic

        return Anthropic(api_key=key)

    if provider == "gemini":
        return OpenAICompatClient(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=settings.gemini_model,
        )

    if provider == "openrouter":
        # attribution headers are requested by OpenRouter's ecosystem policy
        return OpenAICompatClient(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            extra_headers={
                "HTTP-Referer": "https://github.com/parcelpilot-demo",
                "X-Title": "ParcelPilot AI Support Agent",
            },
        )

    raise RuntimeError(
        f"Unknown LLM_PROVIDER '{provider}' (use 'anthropic', 'gemini' or 'openrouter')"
    )


# backwards-compatible alias: the Gemini path is just an OpenAI-compat client
GeminiClient = OpenAICompatClient


__all__ = [
    "AnthropicClientAdapter",
    "GeminiClient",
    "build_llm_client",
    "messages_to_openai",
    "tools_to_openai",
]
