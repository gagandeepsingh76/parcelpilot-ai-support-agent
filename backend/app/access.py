"""Caller identities and access control enforced in the DATA/TOOL layer.

Auth is mocked (no IdP) but enforcement is real: every structured-data read
and every action-tool call passes through these guards, which filter/check
against the caller's identity INSIDE the function - never via system-prompt
instructions alone.

Scopes:
  customer sessions   - read their OWN account/orders/tickets only; may not
                        stage or execute state-changing actions.
  support_agent       - read/write tickets across accounts, open escalations,
                        create follow-ups.
  ops                 - everything support_agent does (superset reserved for
                        future ops-only tools).
  admin               - full control incl. destructive maintenance actions.
  viewer              - internal read-only (explicitly CANNOT stage actions).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

CUSTOMER = "customer"
INTERNAL_ROLES = ("support_agent", "ops", "admin", "viewer")

# which action types each internal role may stage/confirm
ROLE_ACTION_SCOPES: dict[str, set[str]] = {
    "support_agent": {"create_escalation", "update_ticket", "create_follow_up_task"},
    "ops": {"create_escalation", "update_ticket", "create_follow_up_task"},
    "admin": {"create_escalation", "update_ticket", "create_follow_up_task"},
    "viewer": set(),
}


class AccessDeniedError(PermissionError):
    """Raised when a caller tries to touch records/actions outside its scope."""

    def __init__(self, message: str = "access denied"):
        super().__init__(message)
        self.status_code = 403


@dataclass
class Caller:
    kind: str                       # 'customer' | 'internal'
    display_name: str
    account_id: str | None = None   # customer sessions only
    role: str | None = None         # internal sessions only
    session_id: str = "anon"

    @property
    def is_customer(self) -> bool:
        return self.kind == CUSTOMER

    def describe(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "display_name": self.display_name,
            **({"account_id": self.account_id} if self.is_customer else {"role": self.role}),
            "session_id": self.session_id,
        }


def require_customer_account(caller: Caller) -> str:
    if not caller.is_customer or not caller.account_id:
        raise AccessDeniedError("customer authentication required")
    return caller.account_id


def require_internal_role(caller: Caller) -> str:
    if caller.is_customer or caller.role not in INTERNAL_ROLES:
        raise AccessDeniedError("internal staff authentication required")
    return caller.role  # type: ignore[return-value]


def require_action_scope(caller: Caller, action_type: str) -> None:
    if caller.is_customer:
        raise AccessDeniedError(
            "customers cannot execute state-changing actions; ask support staff instead"
        )
    role = require_internal_role(caller)
    if action_type not in ROLE_ACTION_SCOPES.get(role, set()):
        raise AccessDeniedError(f"role '{role}' is not permitted to perform '{action_type}'")


# --------------------------------------------------------------------------
# scoped reads over the structured data (Tool 2)
# --------------------------------------------------------------------------
def scoped_get_account(conn: sqlite3.Connection, caller: Caller, account_id: str) -> dict[str, Any]:
    from app.tools.data import get_account

    if caller.is_customer and caller.account_id != account_id:
        raise AccessDeniedError("you may only view your own account")
    return get_account(conn, account_id)


def scoped_get_order(conn: sqlite3.Connection, caller: Caller, order_id: str) -> dict[str, Any]:
    from app.tools.data import get_order

    order = get_order(conn, order_id)
    if caller.is_customer and order["account_id"] != caller.account_id:
        raise AccessDeniedError("order belongs to a different account")
    return order


def _customer_scope_guard(caller: Caller, requested_account_id: str | None) -> str:
    """Resolve the account a caller may list; explicit denial on any mismatch."""
    if caller.is_customer:
        if requested_account_id and requested_account_id != caller.account_id:
            raise AccessDeniedError("you may only view your own account")
        return str(caller.account_id)
    require_internal_role(caller)
    if not requested_account_id:
        raise AccessDeniedError("internal callers must specify an account_id")
    return requested_account_id


def scoped_list_orders(conn: sqlite3.Connection, caller: Caller, account_id: str | None = None):
    from app.tools.data import list_orders_for_account

    effective = _customer_scope_guard(caller, account_id)
    return list_orders_for_account(conn, effective)


def scoped_get_ticket(conn: sqlite3.Connection, caller: Caller, ticket_id: str) -> dict[str, Any]:
    from app.tools.data import get_ticket

    ticket = get_ticket(conn, ticket_id)
    if caller.is_customer and ticket["account_id"] != caller.account_id:
        raise AccessDeniedError("ticket belongs to a different account")
    return ticket


def scoped_list_tickets(conn: sqlite3.Connection, caller: Caller, account_id: str | None = None):
    from app.tools.data import list_tickets_for_account

    effective = _customer_scope_guard(caller, account_id)
    return list_tickets_for_account(conn, effective)


def assert_can_view_record(caller: Caller, account_id: str) -> None:
    """Record-level guard for calculated results derived from another table."""
    if caller.is_customer and caller.account_id != account_id:
        raise AccessDeniedError("record belongs to a different account")


# --------------------------------------------------------------------------
# scoped action staging/confirming (Tool 3)
# --------------------------------------------------------------------------
def scoped_stage_action(
    conn: sqlite3.Connection,
    caller: Caller,
    action_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    from app.tools.actions import stage_action

    require_action_scope(caller, action_type)

    # the target record must be visible to the caller as well
    affected_account_id = _resolve_target_account(conn, action_type, params)
    if affected_account_id:
        assert_can_view_record(caller, affected_account_id)

    return stage_action(
        conn, {**caller.describe(), "session_id": caller.session_id}, action_type, params
    )


def scoped_confirm_action(conn: sqlite3.Connection, caller: Caller, pending_id: str) -> dict[str, Any]:
    from app.tools.actions import ActionError, confirm_action

    row = conn.execute(
        "SELECT caller_json, action_type, preview_json FROM pending_actions WHERE id=?",
        (pending_id,),
    ).fetchone()
    if row is None:
        raise ActionError(f"unknown pending_action_id '{pending_id}'")

    original_caller = __import__("json").loads(row["caller_json"])
    if original_caller.get("session_id") != caller.session_id:
        raise AccessDeniedError("pending action was staged by a different session")
    require_action_scope(caller, row["action_type"])
    return confirm_action(conn, pending_id)


def scoped_cancel_action(conn: sqlite3.Connection, caller: Caller, pending_id: str) -> dict[str, Any]:
    from app.tools.actions import ActionError, cancel_action

    row = conn.execute(
        "SELECT caller_json FROM pending_actions WHERE id=?", (pending_id,)
    ).fetchone()
    if row is None:
        raise ActionError(f"unknown pending_action_id '{pending_id}'")
    original_caller = __import__("json").loads(row["caller_json"])
    if original_caller.get("session_id") != caller.session_id:
        raise AccessDeniedError("pending action was staged by a different session")
    return cancel_action(conn, pending_id)


def _resolve_target_account(
    conn: sqlite3.Connection, action_type: str, params: dict[str, Any]
) -> str | None:
    """Account whose data an action would touch - checked BEFORE staging."""
    from app.tools.actions import build_preview

    # build_preview already validates ids exist; run it under a dry try so we
    # get the affected account without staging anything.
    probe_caller = {"kind": "system", "role": "admin", "display_name": "scope-probe"}
    try:
        preview = build_preview(conn, probe_caller, action_type, params)
    except Exception:
        return None  # invalid params will be reported by the real stage call
    affects = preview.get("affects") or {}
    return affects.get("account_id")


# --------------------------------------------------------------------------
# mock session resolution for the demo UI / tests
# --------------------------------------------------------------------------
MOCK_SESSIONS: dict[str, dict[str, Any]] = {
    "cust-northstar": {"kind": "customer", "account_id": "ACC-001",
                       "display_name": "Northstar Logistics portal"},
    "cust-lumenworks": {"kind": "customer", "account_id": "ACC-002",
                        "display_name": "LumenWorks Ltd portal"},
    "cust-brightcart": {"kind": "customer", "account_id": "ACC-003",
                        "display_name": "BrightCart Commerce portal"},
    "staff-agent": {"kind": "internal", "role": "support_agent",
                    "display_name": "Avery (support agent)"},
    "staff-ops": {"kind": "internal", "role": "ops", "display_name": "Priya (ops)"},
    "staff-admin": {"kind": "internal", "role": "admin", "display_name": "Root (admin)"},
    "staff-viewer": {"kind": "internal", "role": "viewer", "display_name": "Intern (viewer)"},
}


@dataclass
class SessionRegistry:
    tokens: dict[str, str] = field(default_factory=dict)

    def login(self, session_key: str) -> str:
        if session_key not in MOCK_SESSIONS:
            raise AccessDeniedError(f"unknown mock session '{session_key}'")
        token = f"tok-{session_key}"
        self.tokens[token] = session_key
        return token

    def resolve(self, authorization_header: str | None) -> Caller:
        if not authorization_header or not authorization_header.startswith("Bearer "):
            raise AccessDeniedError("missing bearer credentials")
        token = authorization_header.removeprefix("Bearer ").strip()
        session_key = self.tokens.get(token)
        if session_key is None:
            raise AccessDeniedError("invalid or expired session token")
        spec = MOCK_SESSIONS[session_key]
        return Caller(session_id=token, **spec)


registry = SessionRegistry()
