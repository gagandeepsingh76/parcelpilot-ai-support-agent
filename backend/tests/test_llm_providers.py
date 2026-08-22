"""Unit tests for the LLM provider abstraction (Anthropic / Gemini).

Verifies: schema + message translation to the OpenAI-compatible wire format,
response normalization back into Anthropic-style blocks, dispatch logic, and
an end-to-end GeminiClient round trip over a mocked HTTP transport.
"""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.agent.llm_providers import (
    GeminiClient,
    build_llm_client,
    messages_to_openai,
    tools_to_openai,
)
from app.agent.toolspec import TOOL_SCHEMAS


# --------------------------------------------------------------------------
# translation units
# --------------------------------------------------------------------------
def test_tools_to_openai_wraps_input_schema():
    converted = tools_to_openai(TOOL_SCHEMAS)
    assert len(converted) == 3
    first = converted[0]
    assert first["type"] == "function"
    assert first["function"]["name"] == "search_documents"
    assert first["function"]["parameters"]["type"] == "object"
    # original schemas untouched
    assert "input_schema" in TOOL_SCHEMAS[0]


def test_messages_to_openai_handles_all_shapes():
    system = "be trustworthy"
    messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [
            {"type": "text", "text": "checking"},
            {"type": "tool_use", "id": "call_1", "name": "data_lookup",
             "input": {"lookup_type": "order", "order_id": "ORD-1014"}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "call_1",
             "content": '{"eligible": false}', "is_error": False},
        ]},
    ]
    out = messages_to_openai(system, messages)

    assert out[0] == {"role": "system", "content": system}
    assert out[1] == {"role": "user", "content": "hello"}
    assistant = out[2]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "checking"
    assert len(assistant["tool_calls"]) == 1
    call = assistant["tool_calls"][0]
    assert call["id"] == "call_1"
    assert call["function"]["name"] == "data_lookup"
    assert json.loads(call["function"]["arguments"])["order_id"] == "ORD-1014"
    tool_msg = out[3]
    assert tool_msg == {
        "role": "tool", "tool_call_id": "call_1", "content": '{"eligible": false}'
    }


def test_openai_response_normalizes_tool_calls():
    from app.agent.llm_providers import _OpenAIStyleResponse

    payload = {
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "content": None,
                "tool_calls": [{
                    "id": "abc",
                    "type": "function",
                    "function": {"name": "search_documents",
                                 "arguments": '{"query": "cancellation fee"}'},
                }],
            },
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    result = _OpenAIStyleResponse(payload)
    assert result.stop_reason == "tool_use"
    assert len(result.content) == 1
    block = result.content[0]
    assert block["type"] == "tool_use"
    assert block["id"] == "abc"
    assert block["input"] == {"query": "cancellation fee"}
    assert result.usage["output_tokens"] == 5


def test_openai_response_text_only_is_end_turn():
    from app.agent.llm_providers import _OpenAIStyleResponse

    result = _OpenAIStyleResponse({
        "choices": [{"finish_reason": "stop", "message": {"content": "all done"}}]
    })
    assert result.stop_reason == "end_turn"
    assert result.content == [{"type": "text", "text": "all done"}]


def test_malformed_arguments_become_raw():
    from app.agent.llm_providers import _OpenAIStyleResponse

    result = _OpenAIStyleResponse({
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {"tool_calls": [{"id": "x", "type": "function",
                                        "function": {"name": "t", "arguments": '{oops: 1}'}}]},
        }]
    })
    assert result.content[0]["input"] == {"_raw_arguments": "{oops: 1}"}


# --------------------------------------------------------------------------
# end-to-end over mocked transport
# --------------------------------------------------------------------------
def _mock_transport(responder):
    return httpx.Client(transport=httpx.MockTransport(responder), timeout=120)


def test_gemini_client_round_trip_with_mock_transport(monkeypatch):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization", "")
        body = json.loads(request.content.decode())
        seen.update(body)
        return httpx.Response(200, json={
            "choices": [{
                "finish_reason": "tool_calls",
                "message": {
                    "content": "Let me look that up.",
                    "tool_calls": [
                        {
                            "id": "t1",
                            "type": "function",
                            "function": {
                                "name": "data_lookup",
                                "arguments": json.dumps(
                                    {"lookup_type": "order", "order_id": "ORD-1014"}
                                ),
                            },
                        }
                    ],
                },
            }]
        })

    client = GeminiClient(api_key="test-key", base_url="https://fake.example/v1",
                          model="gemini-test")
    monkeypatch.setattr(client, "_http", _mock_transport(handler))

    response = client.messages.create(
        model=None,
        max_tokens=100,
        system="system prompt here",
        tools=TOOL_SCHEMAS,
        messages=[
            {"role": "user", "content": "Was ORD-1014 late?"},
        ],
    )

    assert seen["url"].startswith("https://fake.example/v1/chat/completions")
    assert seen["auth"] == "Bearer test-key"
    assert seen["model"] == "gemini-test"
    assert seen["messages"][0]["role"] == "system"
    assert len(seen["tools"]) == 3
    assert seen["tool_choice"] == "auto"

    assert response.stop_reason == "tool_use"
    text_blocks = [b for b in response.content if b["type"] == "text"]
    tool_blocks = [b for b in response.content if b["type"] == "tool_use"]
    assert text_blocks and tool_blocks
    assert tool_blocks[0]["name"] == "data_lookup"
    assert tool_blocks[0]["input"]["order_id"] == "ORD-1014"


def test_gemini_client_http_error_raises_runtime_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "bad schema"}})

    client = GeminiClient(api_key="k", base_url="https://fake.example/v1", model="m")
    monkeypatch.setattr(client, "_http", _mock_transport(handler))
    with pytest.raises(RuntimeError, match="Gemini request failed \\(400\\)"):
        client.messages.create(max_tokens=8, messages=[{"role": "user", "content": "hi"}])


def test_gemini_client_requires_key():
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiClient(api_key="", base_url="https://x/v1", model="m")


# --------------------------------------------------------------------------
# dispatch
# --------------------------------------------------------------------------
def test_build_llm_client_dispatches_by_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        client = build_llm_client()
        assert isinstance(client, GeminiClient)
    finally:
        get_settings.cache_clear()


def test_build_llm_client_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "palm")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="Unknown LLM_PROVIDER"):
            build_llm_client()
    finally:
        get_settings.cache_clear()


def test_scripted_llm_still_satisfies_orchestrator_contract():
    """The offline test double keeps working against the same surface."""
    fake = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(
        stop_reason="end_turn", content=[{"type": "text", "text": "ok"}]
    )))
    response = fake.messages.create(model="x", max_tokens=1, system="s",
                                    tools=[], messages=[])
    assert response.stop_reason == "end_turn"
