"""Tool schemas + dispatcher for the agent loop.

Exactly three tools are exposed to the LLM (matching the assignment):
  1. search_documents - Tool 1 (RAG with authority ranking)
  2. data_lookup      - Tool 2 (structured lookups + deterministic calcs)
  3. stage_action     - Tool 3 (state-changing actions; preview only)

Every dispatch goes through the access-control wrappers from app.access -
the LLM can never reach raw queries or unscoped records.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.access import Caller
from app.tools import calculations as calc
from app.tools.actions import ActionError, stage_action  # noqa: F401 (re-exported)
from app.tools.data import NotFoundError

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_documents",
        "description": (
            "Search the authoritative ParcelPilot document index (policies, SOPs, "
            "product guide, customer agreements). Returns cited excerpts ranked by "
            "relevance AND source authority: the customer's own agreement outranks "
            "general policy; CURRENT documents outrank DEPRECATED ones. Use this for "
            "every policy, entitlement, fee-rule or known-issue question. Never quote "
            "fees or rules that did not come from here or from data_lookup."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search phrase, e.g. 'cancellation fee after pickup'.",
                },
                "include_deprecated": {
                    "type": "boolean",
                    "description": "Set true ONLY if the user explicitly asks about superseded/historical policy.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "data_lookup",
        "description": (
            "Query structured operational data (orders, tickets, accounts) and run "
            "deterministic calculations (cancellation fees, service-credit eligibility, "
            "SLA status). All amounts and timestamps come from the database - never "
            "compute these yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lookup_type": {
                    "type": "string",
                    "enum": [
                        "order", "orders_for_account", "ticket", "tickets_for_account",
                        "account", "cancellation_fee", "late_pickup_credit",
                        "late_delivery_credit", "sla_status", "similar_past_tickets",
                    ],
                },
                "order_id": {"type": "string"},
                "ticket_id": {"type": "string"},
                "account_id": {
                    "type": "string",
                    "description": "Internal staff only: the account to query.",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "similar_past_tickets only: 1-6 keywords to match against "
                        "resolved tickets of the given account. Results are "
                        "context-only and never citable as policy."
                    ),
                },
            },
            "required": ["lookup_type"],
        },
    },
    {
        "name": "stage_action",
        "description": (
            "Stage a state-changing action. This ONLY creates a pending preview - "
            "nothing changes until the user explicitly confirms it in a separate step. "
            "Always show the preview verbatim to the user and ask for clear "
            "confirmation. NEVER tell the user an action has been executed unless a "
            "separate confirmation receipt was returned by the system afterwards."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "enum": ["create_escalation", "update_ticket", "create_follow_up_task"],
                },
                "params": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string"},
                        "ticket_id": {"type": "string"},
                        "account_id": {"type": "string"},
                        "reason": {"type": "string"},
                        "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
                        "subject": {"type": "string"},
                        "due_at": {"type": "string"},
                        "updates": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string"},
                                "resolution_note": {"type": "string"},
                                "priority": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "required": ["action_type"],
        },
    },
]


def _deny_or_none(caller: Caller) -> str | None:
    return None


def execute_tool_call(
    conn: sqlite3.Connection,
    caller: Caller,
    name: str,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one tool call under access control.

    Returns (tool_result, trace_meta). Raises nothing: failures are returned as
    {'error': ...} so the model can react conversationally.
    """
    meta: dict[str, Any] = {}
    try:
        if name == "search_documents":
            from app.rag.retrieval import search_documents

            result = search_documents(
                payload["query"],
                account_id=caller.account_id if caller.is_customer else None,
                include_deprecated=bool(payload.get("include_deprecated", False)),
            )
            if not result["results"]:
                result["escalation_hint"] = (
                    "no supporting source found - offer to escalate to a human"
                )
                meta["escalated"] = True
            meta["citations"] = [r["citation"] for r in result["results"]]
            meta["conflicts"] = result["conflicts"]
            return result, meta

        if name == "data_lookup":
            return _data_lookup(conn, caller, payload), meta

        if name == "stage_action":
            from app.access import scoped_stage_action

            preview = scoped_stage_action(conn, caller, payload["action_type"], payload.get("params") or {})
            meta["pending_action"] = {
                "pending_action_id": preview["pending_action_id"],
                "summary": preview["summary"],
                "changes": preview.get("changes"),
            }
            return {
                "status": "pending_confirmation",
                "pending_action_id": preview["pending_action_id"],
                "summary": preview["summary"],
                "note": (
                    "Do NOT claim this was executed. Ask the user to confirm; the "
                    "system applies it only after explicit confirmation."
                ),
            }, meta

        return {"error": f"unknown tool '{name}'"}, meta

    except NotFoundError as exc:
        return {"error": str(exc), "escalation_hint": "record not found"}, meta
    except PermissionError as exc:
        return {"error": str(exc)}, {**meta, "denied": True}
    except ActionError as exc:
        return (
            {"error": str(exc), "escalation_hint": "requested action is not supported"},
            {**meta, "escalated": True},
        )
    except Exception as exc:  # noqa: BLE001 - never leak stack traces to the model
        return {"error": f"tool failure: {exc}"}, meta


def _data_lookup(
    conn: sqlite3.Connection, caller: Caller, payload: dict[str, Any]
) -> dict[str, Any]:
    from app import access as acl

    lookup = payload["lookup_type"]

    if lookup in ("orders_for_account", "tickets_for_account"):
        account_id = payload.get("account_id") or (caller.account_id if caller.is_customer else None)
        rows = (
            acl.scoped_list_tickets(conn, caller, account_id)
            if lookup == "tickets_for_account"
            else acl.scoped_list_orders(conn, caller, account_id)
        )
        return {"records": rows}

    if lookup == "account":
        account_id = payload.get("account_id") or caller.account_id
        return acl.scoped_get_account(conn, caller, account_id)

    order_id = payload.get("order_id")
    ticket_id = payload.get("ticket_id")

    if lookup in ("order", "cancellation_fee", "late_pickup_credit", "late_delivery_credit"):
        if not order_id:
            return {"error": f"lookup_type '{lookup}' requires order_id"}
        order = acl.scoped_get_order(conn, caller, order_id)
        account = acl.scoped_get_account(conn, caller, order["account_id"])
        if lookup == "order":
            return calc.summarize_order_timeseries(order) | {"service_type": order.get("service_type"),
                                                             "order_value_usd": order.get("order_value_usd")}
        if lookup == "cancellation_fee":
            return calc.cancellation_fee(conn, order, account)
        if lookup == "late_pickup_credit":
            return calc.late_pickup_credit(conn, order, account)
        return calc.late_delivery_credit(conn, order, account)

    if lookup in ("ticket", "sla_status"):
        if not ticket_id:
            return {"error": f"lookup_type '{lookup}' requires ticket_id"}
        ticket = acl.scoped_get_ticket(conn, caller, ticket_id)
        if lookup == "ticket":
            return ticket
        account = acl.scoped_get_account(conn, caller, ticket["account_id"])
        return calc.sla_status(conn, ticket, account)

    if lookup == "similar_past_tickets":
        from app.access import scoped_search_past_tickets

        keywords = [str(k) for k in payload.get("keywords") or []]
        if not keywords:
            return {"error": "similar_past_tickets requires keywords"}
        return scoped_search_past_tickets(
            conn, caller, payload.get("account_id"), keywords
        )

    return {"error": f"unsupported lookup_type '{lookup}'"}
