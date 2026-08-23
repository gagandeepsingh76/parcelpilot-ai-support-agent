"""The tool-calling agent loop using Google Gemini.

run_turn() drives Gemini with native tool_use over the registered
tools, executes every call under access control, and returns a structured
turn result: reply text, per-turn tool trace, citations, conflict flags,
staged pending actions, and whether the turn ended in an escalation.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from google.genai import types

from app.access import Caller
from app.agent.llm_providers import build_llm_client, build_gemini_tools
from app.agent.prompts import system_prompt_for
from app.agent.toolspec import TOOL_SCHEMAS, execute_tool_call
from app.config import get_settings

MAX_TOOL_ROUNDS = 6


def _describe_tool_call(tool: str, input_params: dict[str, Any]) -> str:
    """Generate a clean, professional user-facing description of tool activity."""
    if tool == "search_documents":
        q = input_params.get("query", "")
        return f"Searching authoritative policy & contract documents for '{q}'" if q else "Searching authoritative documents"
    if tool == "data_lookup":
        l_type = input_params.get("lookup_type", "")
        oid = input_params.get("order_id", "")
        tid = input_params.get("ticket_id", "")
        aid = input_params.get("account_id", "")
        if l_type == "order":
            return f"Checking order records for {oid}"
        if l_type == "cancellation_fee":
            return f"Calculating deterministic cancellation fee for order {oid}"
        if l_type == "late_pickup_credit":
            return f"Evaluating late pickup credit eligibility for order {oid}"
        if l_type == "late_delivery_credit":
            return f"Evaluating late delivery compensation for order {oid}"
        if l_type == "sla_status":
            return f"Checking SLA tracking status for ticket {tid}"
        if l_type == "orders_for_account":
            return f"Listing orders for account {aid}" if aid else "Listing account orders"
        if l_type == "tickets_for_account":
            return f"Listing tickets for account {aid}" if aid else "Listing account tickets"
        if l_type == "account":
            return f"Retrieving account details for {aid}" if aid else "Retrieving account details"
        if l_type == "similar_past_tickets":
            kw = ", ".join(input_params.get("keywords") or [])
            return f"Reviewing past resolved tickets matching [{kw}] (context only)"
        return f"Querying structured data: {l_type}"
    if tool == "stage_action":
        act = input_params.get("action_type", "")
        params = input_params.get("params") or {}
        if act == "create_escalation":
            return f"Staging human escalation ({params.get('priority', 'P2')}) for operational review"
        if act == "update_ticket":
            return f"Staging update for ticket {params.get('ticket_id', '')}"
        if act == "create_follow_up_task":
            return f"Staging follow-up task: '{params.get('subject', '')}'"
        return f"Staging action: {act}"
    return f"Executing {tool}"


@dataclass
class TurnResult:
    reply: str
    tools_used: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    pending_actions: list[dict[str, Any]] = field(default_factory=list)
    escalated: bool = False

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "tools_used": self.tools_used,
            "citations": self.citations,
            "conflicts": self.conflicts,
            "pending_actions": self.pending_actions,
            "escalated": self.escalated,
        }


class AgentOrchestrator:
    def __init__(self, conn: sqlite3.Connection, llm_client: Any):
        self.conn = conn
        self.llm = llm_client
        self.settings = get_settings()
        self.model = self.settings.gemini_model

    def run_turn(self, caller: Caller, history: list[dict[str, str]], user_message: str) -> TurnResult:
        result = TurnResult(reply="")
        
        # Build contents from history
        contents = []
        for m in history[-12:]:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
            
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))
        
        system = system_prompt_for(caller)
        gemini_tools = build_gemini_tools(TOOL_SCHEMAS)
        
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=gemini_tools,
        )

        for _round in range(MAX_TOOL_ROUNDS):
            try:
                response = self.llm.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
            except Exception as e:
                # Handle API unavailability, auth errors, etc
                raise RuntimeError(f"Gemini API request failed: {e}") from e

            if not response.candidates:
                raise RuntimeError("Empty response received from Gemini.")
            
            candidate = response.candidates[0]
            if not candidate.content:
                raise RuntimeError("Candidate content is empty.")
                
            parts = candidate.content.parts or []
            
            function_calls = []
            text_reply = ""
            for part in parts:
                if part.function_call:
                    function_calls.append(part.function_call)
                elif part.text:
                    text_reply += part.text + "\n"
                    
            if not function_calls:
                result.reply = text_reply.strip()
                break
                
            # Append model's response to contents
            contents.append(candidate.content)
            
            tool_responses_parts = []
            for call in function_calls:
                name = call.name
                
                # Gemini args is usually a dict or structurally similar
                inp = call.args if isinstance(call.args, dict) else dict(call.args)
                
                payload, meta = execute_tool_call(self.conn, caller, name, inp)
                is_err = bool(isinstance(payload, dict) and payload.get("error"))
                result.tools_used.append(
                    {
                        "tool": name,
                        "input": inp,
                        "output": payload,
                        "status": "error" if is_err else "success",
                        "label": _describe_tool_call(name, inp),
                    }
                )
                if meta.get("citations"):
                    result.citations.extend(meta["citations"])
                if meta.get("conflicts"):
                    result.conflicts.extend(meta["conflicts"])
                if meta.get("pending_action"):
                    result.pending_actions.append(meta["pending_action"])
                if meta.get("escalated") or (isinstance(payload, dict) and payload.get("escalation_hint")):
                    result.escalated = True
                    
                tool_responses_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response=payload
                    )
                )
                
            # Append user's tool responses
            contents.append(types.Content(role="user", parts=tool_responses_parts))
        else:
            result.reply = (
                result.reply
                or "This request needs more steps than I can take autonomously - escalating."
            )
            result.escalated = True

        # Heuristic backstop for replies that explicitly promise escalation.
        escalation_phrases = ("escalat", "manual review", "human review", "operator review")
        if not result.escalated and any(kw in result.reply.lower() for kw in escalation_phrases):
            result.escalated = True

        # de-duplicate citations while keeping order
        seen: set[tuple] = set()
        unique_citations = []
        for citation in result.citations:
            key = (citation.get("doc_id"), citation.get("section"))
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)
        result.citations = unique_citations
        return result


def _json(payload: dict[str, Any]) -> str:
    import json

    try:
        return json.dumps(payload, default=str)
    except (TypeError, ValueError):
        return str(payload)


_default_orchestrator: AgentOrchestrator | None = None


def get_orchestrator(conn: sqlite3.Connection) -> AgentOrchestrator:
    return AgentOrchestrator(conn, build_llm_client())


__all__ = ["AgentOrchestrator", "TurnResult", "get_orchestrator"]
