"""Scripted LLM double for deterministic agent-loop tests (Gemini SDK structure)."""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from google.genai import types

class _ModelsApi:
    def __init__(self, owner: "ScriptedLLM"):
        self._owner = owner

    def generate_content(self, **kwargs):
        return self._owner._next(**kwargs)


class ScriptedLLM:
    """Returns queued responses in order; records every generate_content() call."""

    def __init__(self, responses: list[Any]):
        if not responses:
            raise ValueError("ScriptedLLM needs at least one response")
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.models = _ModelsApi(self)

    def _next(self, **kwargs):
        if not self.responses:
            raise AssertionError("ScriptedLLM ran out of scripted responses")
        self.calls.append(kwargs)
        return self.responses.pop(0)

    @property
    def exhausted(self) -> bool:
        return not self.responses

    def last_messages(self) -> list[dict]:
        return self.calls[-1]["contents"] if self.calls else []

    def tool_results_received(self) -> list[dict]:
        """All tool_result blocks the model has been shown across turns."""
        results = []
        for call in self.calls:
            for content in call.get("contents", []):
                for part in getattr(content, "parts", []):
                    if getattr(part, "function_response", None):
                        results.append(part.function_response.model_dump())
        return results


def text(t: str) -> Any:
    # Mimic a GenerateContentResponse
    content = types.Content(role="model", parts=[types.Part.from_text(text=t)])
    candidate = types.Candidate(content=content)
    # create a mock response object
    class MockResponse:
        candidates = [candidate]
        text = t
    return MockResponse()

def tool_use(block_id: str, name: str, payload: dict[str, Any]) -> Any:
    call = types.FunctionCall(name=name, args=payload)
    content = types.Content(role="model", parts=[types.Part(function_call=call)])
    candidate = types.Candidate(content=content)
    class MockResponse:
        candidates = [candidate]
    return MockResponse()

def tool_then_answer(tool_call: Any, answer: str) -> list[Any]:
    return [tool_call, text(answer)]
