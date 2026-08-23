"""HTTP API: mock login, chat turns, and pending-action confirm/cancel.

AccessDeniedError -> 403; missing LLM key -> 503 with guidance.
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from typing import Any, Generator

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ..config import get_settings
from ..access import Caller, AccessDeniedError, registry
from ..agent.orchestrator import get_orchestrator

@lru_cache
def _db_path() -> str:
    return get_settings().sqlite_db_path_resolved

def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

def current_caller(authorization: str | None = Header(default=None)) -> Caller:
    try:
        return registry.resolve(authorization)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

router = APIRouter(prefix="/api")

class LoginRequest(BaseModel):
    session_key: str

class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []

class ActionDecisionRequest(BaseModel):
    pass  # no body needed; the pending id is in the path

class AuthLoginRequest(BaseModel):
    username: str
    password: str

class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    account_id: str
    display_name: str | None = None

def _deterministic_order_lookup(
    conn: sqlite3.Connection, caller: Caller, message: str
) -> dict[str, Any] | None:
    """No-LLM fallback for explicit order-ID lookups only."""
    import re
    from ..access import scoped_get_order

    match = re.search(r"\bORD-\d+\b", message or "", flags=re.IGNORECASE)
    if not match:
        return None

    order_id = match.group(0).upper()

    try:
        order = scoped_get_order(conn, caller, order_id)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail="access denied") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    reply = (
        f"Order {order_id}: status {order.get('status')}; "
        f"service {order.get('service_type')}; "
        f"scheduled pickup {order.get('scheduled_pickup_at')}; "
        f"actual pickup {order.get('actual_pickup_at')}; "
        f"promised delivery {order.get('promised_delivery_at')}; "
        f"delivered {order.get('delivered_at')}."
    )
    return {
        "reply": reply,
        "tools_used": [
            {
                "tool": "deterministic_order_lookup",
                "input": {"order_id": order_id},
                "output": order,
                "status": "success",
                "label": f"Checking order records for {order_id}",
            }
        ],
        "citations": [],
        "conflicts": [],
        "pending_actions": [],
        "escalated": False,
    }


@router.post("/session/login")
def login(body: LoginRequest) -> dict[str, Any]:
    try:
        token = registry.login(body.session_key)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    caller = registry.resolve(f"Bearer {token}")
    return {"token": token, "caller": caller.describe()}


@router.post("/auth/login")
def auth_login(
    body: AuthLoginRequest, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Credential login for both user kinds (customers and internal staff)."""
    from .. import auth

    try:
        caller = auth.authenticate(conn, body.username, body.password)
        token = auth.issue_token(caller)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    # the session_id inside a signed token is stable per username; re-issue so
    # stage/confirm flows see one consistent session id
    resolved = auth.resolve_signed_token(f"Bearer {token}")
    return {"token": token, "caller": (resolved or caller).describe()}


@router.post("/auth/register")
def auth_register(
    body: AuthRegisterRequest, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Self-service registration for CUSTOMER logins on existing accounts.

    Internal staff are provisioned out-of-band (seeded demo users here).
    """
    from .. import auth

    try:
        caller = auth.register_customer(
            conn, body.username, body.password, body.account_id, body.display_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    token = auth.issue_token(caller)
    return {"token": token, "caller": caller.describe()}


@router.get("/me")
def me(caller: Caller = Depends(current_caller)) -> dict[str, Any]:
    return caller.describe()


@router.post("/chat")
def chat(
    body: ChatRequest,
    caller: Caller = Depends(current_caller),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    try:
        orchestrator = get_orchestrator(conn)
    except RuntimeError as exc:
        fallback = _deterministic_order_lookup(conn, caller, body.message)
        if fallback is not None:
            return fallback
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    result = orchestrator.run_turn(caller, body.history, body.message)
    return result.to_api_dict()


@router.post("/actions/{pending_id}/confirm")
def confirm_action(
    pending_id: str,
    caller: Caller = Depends(current_caller),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    from ..access import scoped_confirm_action

    try:
        return scoped_confirm_action(conn, caller, pending_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/actions/{pending_id}/cancel")
def cancel_action(
    pending_id: str,
    caller: Caller = Depends(current_caller),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    from ..access import scoped_cancel_action

    try:
        return scoped_cancel_action(conn, caller, pending_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/insights/summary")
def insights_summary(
    caller: Caller = Depends(current_caller),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Proactive issue detection across all accounts (internal roles only)."""
    if caller.is_customer:
        raise HTTPException(status_code=403, detail="internal only")
    from ..insights.service import compute_insights

    return compute_insights(conn)


@router.get("/metadata")
def get_metadata(conn: sqlite3.Connection = Depends(get_conn)) -> dict[str, Any]:
    """System overview, dataset snapshot timestamp, accounts list, and documents."""
    from ..timebase import get_snapshot_time

    snapshot = get_snapshot_time(conn).isoformat()
    accounts = [
        {
            "account_id": row["account_id"],
            "account_name": row["account_name"],
            "tier": row["tier"],
            "good_standing": bool(row["good_standing"]),
        }
        for row in conn.execute("SELECT account_id, account_name, tier, good_standing FROM accounts").fetchall()
    ]
    docs = [
        {
            "doc_id": row["doc_id"],
            "filename": row["filename"],
            "title": row["title"],
            "version": row["version"],
            "status": row["status"],
            "doc_type": row["doc_type"],
            "customer_scope": row["customer_scope"],
            "page_count": row["page_count"],
        }
        for row in conn.execute("SELECT doc_id, filename, title, version, status, doc_type, customer_scope, page_count FROM documents").fetchall()
    ]
    return {
        "app_name": "ParcelPilot AI Support Agent",
        "snapshot_utc": snapshot,
        "accounts": accounts,
        "documents": docs,
    }


@router.get("/documents")
def get_documents(conn: sqlite3.Connection = Depends(get_conn)) -> list[dict[str, Any]]:
    """List of all authoritative and historical documents in the knowledge base."""
    docs = []
    for row in conn.execute("SELECT * FROM documents ORDER BY doc_id").fetchall():
        sections = [
            {"seq": s["seq"], "level": s["level"], "heading": s["heading"]}
            for s in conn.execute("SELECT seq, level, heading FROM document_sections WHERE doc_id = ? ORDER BY seq", (row["doc_id"],)).fetchall()
        ]
        docs.append(
            {
                "doc_id": row["doc_id"],
                "filename": row["filename"],
                "title": row["title"],
                "version": row["version"],
                "status": row["status"],
                "doc_type": row["doc_type"],
                "customer_scope": row["customer_scope"],
                "page_count": row["page_count"],
                "sections": sections,
            }
        )
    return docs


@router.get("/records/summary")
def get_records_summary(
    caller: Caller = Depends(current_caller),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    """Summary of accessible operational records for the caller context."""
    from ..access import scoped_list_orders, scoped_list_tickets

    if caller.is_customer:
        orders = scoped_list_orders(conn, caller)
        tickets = scoped_list_tickets(conn, caller)
        open_tickets = [t for t in tickets if str(t.get("status", "")).lower() not in ("resolved", "closed")]
        return {
            "kind": "customer",
            "account_id": caller.account_id,
            "orders_count": len(orders),
            "tickets_count": len(tickets),
            "open_tickets_count": len(open_tickets),
            "recent_orders": orders[:5],
            "recent_tickets": tickets[:5],
        }
    # internal caller
    total_accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total_tickets = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    open_tickets = conn.execute("SELECT COUNT(*) FROM tickets WHERE lower(status) NOT IN ('resolved', 'closed')").fetchone()[0]
    return {
        "kind": "internal",
        "role": caller.role,
        "total_accounts": total_accounts,
        "total_orders": total_orders,
        "total_tickets": total_tickets,
        "open_tickets_count": open_tickets,
    }
