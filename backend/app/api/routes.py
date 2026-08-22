"""HTTP API: mock login, chat turns, and pending-action confirm/cancel.

AccessDeniedError -> 403; missing LLM key -> 503 with guidance.
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.access import Caller, AccessDeniedError, registry
from app.agent.orchestrator import AgentOrchestrator, get_orchestrator
from app.config import get_settings

router = APIRouter(prefix="/api")


@lru_cache
def _db_path() -> str:
    return get_settings().sqlite_db_path_resolved


def get_conn() -> sqlite3.Connection:
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


class LoginRequest(BaseModel):
    session_key: str


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []


class ActionDecisionRequest(BaseModel):
    pass  # no body needed; the pending id is in the path


@router.post("/session/login")
def login(body: LoginRequest) -> dict[str, Any]:
    try:
        token = registry.login(body.session_key)
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    caller = registry.resolve(f"Bearer {token}")
    return {"token": token, "caller": caller.describe()}


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    account_id: str
    display_name: str | None = None


@router.post("/auth/login")
def auth_login(
    body: AuthLoginRequest, conn: sqlite3.Connection = Depends(get_conn)
) -> dict[str, Any]:
    """Credential login for both user kinds (customers and internal staff)."""
    from app import auth

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
    from app import auth

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
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    result = orchestrator.run_turn(caller, body.history, body.message)
    return result.to_api_dict()


@router.post("/actions/{pending_id}/confirm")
def confirm_action(
    pending_id: str,
    caller: Caller = Depends(current_caller),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict[str, Any]:
    from app.access import scoped_confirm_action

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
    from app.access import scoped_cancel_action

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
    from app.insights.service import compute_insights

    return compute_insights(conn)
