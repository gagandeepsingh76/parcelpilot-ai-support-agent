"""LLM provider abstraction.

AgentOrchestrator uses this to communicate with Gemini.
"""

from __future__ import annotations

import json
from typing import Any
from google import genai
from google.genai import types

def build_llm_client() -> genai.Client:
    from app.config import get_settings
    settings = get_settings()

    key = settings.gemini_api_key
    if not key or key.startswith("your-"):
        raise RuntimeError(
            "No LLM API key configured - set GEMINI_API_KEY in backend/.env"
        )
    return genai.Client(api_key=key)

def build_gemini_tools(tool_schemas: list[dict[str, Any]]) -> list[Any]:
    declarations = []
    for s in tool_schemas:
        declarations.append(types.FunctionDeclaration(
            name=s["name"],
            description=s["description"],
            parameters=s.get("input_schema")
        ))
    return [types.Tool(function_declarations=declarations)]

__all__ = ["build_llm_client", "build_gemini_tools"]
