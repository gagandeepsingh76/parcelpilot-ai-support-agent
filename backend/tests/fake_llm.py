"""Scripted LLM double for deterministic agent-loop tests (no network)."""

from __future__ import annotations

from typing import Any


class TextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class ToolUseBlock:
    def __init__(self, block_id: str, name: str, input: dict[str, Any]):
        self.type = "tool_use"
        self.id = block_id
        self.name = name
        self.input = input


class Response:
    def __init__(self, content: list, stop_reason: str = "end_turn"):
        self.content = content
        self.stop_reason = stop_reason


def text(t: str) -> Response:
    return Response([TextBlock(t)])


def tool_use(block_id: str, name: str, payload: dict[str, Any]) -> Response:
    return Response([ToolUseBlock(block_id, name, payload)], stop_reason="tool_use")


def tool_then_answer(tool_call: Response, answer: str) -> list[Response]:
    """Two-turn script: fire one tool call, then produce the final reply."""
    return [tool_call, text(answer)]


class _MessagesApi:
    """Mimics client.messages.create() of the Anthropic SDK."""

    def __init__(self, owner: "ScriptedLLM"):
        self._owner = owner

    def create(self, **kwargs):  # noqa: ANN003 - mirrors SDK signature
        return self._owner._next(**kwargs)


class ScriptedLLM:
    """Returns queued responses in order; records every create() call."""

    def __init__(self, responses: list[Response]):
        if not responses:
            raise ValueError("ScriptedLLM needs at least one response")
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.messages = _MessagesApi(self)

    def _next(self, **kwargs):
        if not self.responses:
            raise AssertionError("ScriptedLLM ran out of scripted responses")
        self.calls.append(kwargs)
        return self.responses.pop(0)

    @property
    def exhausted(self) -> bool:
        return not self.responses

    def last_messages(self) -> list[dict]:
        return self.calls[-1]["messages"] if self.calls else []

    def tool_results_received(self) -> list[dict]:
        """All tool_result blocks the model has been shown across turns."""
        results = []
        for call in self.calls:
            for message in call["messages"]:
                content = message.get("content")
                if isinstance(content, list):
                    results.extend(b for b in content if isinstance(b, dict) and b.get("type") == "tool_result")
        return results
