"""Unit tests for the LLM provider abstraction (Gemini)."""

import pytest

from app.agent.llm_providers import build_llm_client, build_gemini_tools
from app.agent.toolspec import TOOL_SCHEMAS

def test_build_gemini_tools():
    tools = build_gemini_tools(TOOL_SCHEMAS)
    assert len(tools) == 1
    assert tools[0].function_declarations is not None
    assert len(tools[0].function_declarations) == 3
    assert tools[0].function_declarations[0].name == "search_documents"

def test_build_llm_client_missing_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="No LLM API key configured"):
            build_llm_client()
    finally:
        get_settings.cache_clear()

def test_build_llm_client_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        client = build_llm_client()
        assert client is not None
    finally:
        get_settings.cache_clear()
