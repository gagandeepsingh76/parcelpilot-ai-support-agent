"""State-changing action tools (Tool 3) with a mandatory confirmation gate.

Flow: stage_action() -> pending preview (nothing touched yet)
      confirm_action() -> applies changes + writes an audit log row
      cancel_action()  -> discards the staged action

The agent layer must ALWAYS show the preview to the user and only call
confirm after the user explicitly agrees - enforced by API design: effects
are reachable exclusively through confirm_action(pending_id).
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any

VALID_ACTION_TYPES = ("create_escalation", "update_ticket", "create_follow_up_task")

TICKET_MUTABLE_FIELDS = {"status": str, "resolution_note": str, "priority": str}
TICKET_STATUSES = {"open", "in_progress", "resolved"}


class ActionError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "_Z")


def _new_id(prefix: str, conn: sqlite3.Connection, table: str, column: str) -> str:
    """Next sequential id (e.g. TCK-2023) based on existing rows."""
    rows = conn.execute(f"SELECT {column} FROM {table}").fetchall()
    max_n = 0
    for row in rows:
        value = str(row[0])
        if "_" in value:
            try:
                max_n = max(max_n, int(value.split("_", 1)[1]))
            except ValueError:
                continue
    return f"{prefix}-{max_n + 1}" if prefix != "PND" else f"{prefix}-{secrets.token_hex(4)}"


# --------------------------------------------------------------------------
# previews (pure - describe what WOULD happen)
# --------------------------------------------------------------------------
def build_preview(
    conn: sqlite3.Connection,
    caller: dict[str, Any],
    action_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    if action_type not in VALID_ACTION_TYPES:
        raise ActionError(
            f"unsupported action '{action_type}'. Valid types: {', '.join(VALID_ACTION_TYPES)}"
        )

    if action_type == "create_escalation":
        return _preview_escalation(conn, params)
    if action_type == "update_ticket":
        return _preview_update_ticket(conn, params)
    return _preview_follow_up(conn, params)


def _require_ticket(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any]:
    from app.tools.data import get_ticket

    try:
        return get_ticket(conn, ticket_id)
    except LookupError as exc:
        raise ActionError(str(exc)) from exc


def _preview_escalation(conn: sqlite3.Connection, params: dict[str, Any]) -> dict[str, Any]:
    reason = (params.get("reason") or "").strip()
    if not reason:
        raise ActionError("create_escalation requires a non-empty 'reason'")
    order_id = params.get("order_id")
    ticket_id = params.get("ticket_id")
    account_id = params.get("account_id")
    if bool(order_id) + bool(ticket_id) + bool(account_id) != 1:
        raise ActionError("create_escalation requires exactly one of order_id | ticket_id | account_id")

    if order_id:
        from app.tools.data import get_order

        try:
            record = get_order(conn, str(order_id))
        except LookupError as exc:
            raise ActionError(str(exc)) from exc
        account_id = record["account_id"]
        link = f"order {order_id}"
    elif ticket_id:
        record = _require_ticket(conn, str(ticket_id))
        account_id = record["account_id"]
        link = f"ticket {ticket_id}"
    else:
        from app.tools.data import get_account

        try:
            get_account(conn, str(account_id))
        except LookupError as exc:
            raise ActionError(str(exc)) from exc
        record, link = None, None

    priority = str(params.get("priority") or "P2").upper()
    if priority not in {"P1", "P2", "P3"}:
        raise ActionError("priority must be one of P1/P2/P3")

    return {
        "action_type": "create_escalation",
        "summary": (
            f"Open a human escalation ({priority}) for account {account_id}"
            + (f" referencing {link}" if link else "")
            + f". Reason recorded: \"{reason}\"."
        ),
        "affects": {
            "table": "tickets",
            "account_id": account_id,
            "linked_order_id": order_id,
            "linked_ticket_id": ticket_id,
            "new_record": True,
        },
        "changes": {
            "category": "escalation",
            "priority": priority,
            "subject": f"Human escalation - {reason[:60]}",
            "description": reason,
        },
        "irreversible": False,
    }


def _validate_ticket_update(params: dict[str, Any]) -> dict[str, str]:
    updates = params.get("updates") or {}
    if not isinstance(updates, dict) or not updates:
        raise ActionError("update_ticket requires a non-empty 'updates' object")
    cleaned: dict[str, str] = {}
    for key, value in updates.items():
        if key not in TICKET_MUTABLE_FIELDS:
            raise ActionError(
                f"field '{key}' is not mutable. Allowed: {', '.join(sorted(TICKET_MUTABLE_FIELDS))}"
            )
        text = str(value).strip()
        if not text:
            raise ActionError(f"field '{key}' cannot be empty")
        if key == "status" and text.lower() not in TICKET_STATUSES:
            raise ActionError(f"status must be one of: {', '.join(sorted(TICKET_STATUSES))}")
        cleaned[key] = text.lower() if key == "status" else text
    return cleaned


def _preview_update_ticket(conn: sqlite3.Connection, params: dict[str, Any]) -> dict[str, Any]:
    ticket = _require_ticket(conn, str(params.get("ticket_id")))
    updates = _validate_ticket_update(params)
    before_after = {
        key: {"from": ticket.get(key), "to": value} for key, value in updates.items()
    }
    readable = "; ".join(f"{k}: '{v['from']}' -> '{v['to']}'" for k, v in before_after.items())
    return {
        "action_type": "update_ticket",
        "summary": f"Update ticket {ticket['ticket_id']} ({ticket['account_id']}): {readable}.",
        "affects": {
            "table": "tickets",
            "record_id": ticket["ticket_id"],
            "account_id": ticket["account_id"],
            "new_record": False,
        },
        "changes": before_after,
        "irreversible": False,
    }


def _preview_follow_up(conn: sqlite3.Connection, params: dict[str, Any]) -> dict[str, Any]:
    subject = (params.get("subject") or "").strip()
    if not subject:
        raise ActionError("create_follow_up_task requires a non-empty 'subject'")
    account_id = str(params.get("account_id") or "")
    from app.tools.data import get_account

    try:
        get_account(conn, account_id)
    except LookupError as exc:
        raise ActionError(str(exc)) from exc
    due_at = params.get("due_at")
    return {
        "action_type": "create_follow_up_task",
        "summary": (
            f"Create a follow-up task for account {account_id}: \"{subject}\""
            + (f" due {due_at}" if due_at else " with no due date")
            + "."
        ),
        "affects": {"table": "follow_up_tasks", "account_id": account_id, "new_record": True},
        "changes": {"subject": subject, "due_at": due_at},
        "irreversible": False,
    }


# --------------------------------------------------------------------------
# staging / confirming / cancelling
# --------------------------------------------------------------------------
def stage_action(
    conn: sqlite3.Connection,
    caller: dict[str, Any],
    action_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    preview = build_preview(conn, caller, action_type, params)
    pending_id = f"PND-{secrets.token_hex(4)}"
    created_at = _now()
    conn.execute(
        """INSERT INTO pending_actions
             (id, created_at, caller_json, action_type, params_json, preview_json, status)
           VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
        (
            pending_id,
            created_at,
            json.dumps(caller),
            action_type,
            json.dumps(params),
            json.dumps(preview),
        ),
    )
    conn.commit()
    return {"pending_action_id": pending_id, "created_at": created_at, **preview}


def _load_pending(conn: sqlite3.Connection, pending_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM pending_actions WHERE id = ?", (pending_id,)
    ).fetchone()
    if row is None:
        raise ActionError(f"unknown pending_action_id '{pending_id}'")
    return row


def confirm_action(conn: sqlite3.Connection, pending_id: str) -> dict[str, Any]:
    row = _load_pending(conn, pending_id)
    if row["status"] != "pending":
        raise ActionError(
            f"pending action '{pending_id}' is already {row['status']} and cannot be confirmed again"
        )

    preview = json.loads(row["preview_json"])
    params = json.loads(row["params_json"])
    caller = json.loads(row["caller_json"])
    executed_at = _now()

    result: dict[str, Any]
    if row["action_type"] == "create_escalation":
        result = _apply_escalation(conn, preview, params, executed_at)
    elif row["action_type"] == "update_ticket":
        result = _apply_update_ticket(conn, preview, executed_at)
    else:
        result = _apply_follow_up(conn, preview, caller, executed_at)

    affected_account = preview["affects"].get("account_id")
    conn.execute(
        """INSERT INTO actions_log
             (created_at, account_id, actor_json, action_type, payload_json, result_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            executed_at,
            affected_account,
            json.dumps(caller),
            row["action_type"],
            json.dumps(params),
            json.dumps(result),
        ),
    )
    conn.execute(
        "UPDATE pending_actions SET status='executed', params_json=params_json WHERE id=?",
        (pending_id,),
    )
    conn.commit()
    return {"pending_action_id": pending_id, "executed_at": executed_at, **result}


def _apply_escalation(
    conn: sqlite3.Connection, preview: dict, params: dict, executed_at: str
) -> dict[str, Any]:
    affects = preview["affects"]
    new_id = _new_id("TCK", conn, "tickets", "ticket_id")
    changes = preview["changes"]
    conn.execute(
        """INSERT INTO tickets (ticket_id, account_id, order_id, category, subject,
                                description, priority, created_at, first_response_at,
                                resolved_at, status, resolution_note)
           VALUES (?, ?, ?, 'escalation', ?, ?, ?, ?, NULL, NULL, 'open', '')""",
        (
            new_id,
            affects["account_id"],
            affects.get("linked_order_id"),
            changes["subject"],
            changes["description"],
            changes["priority"],
            executed_at,
        ),
    )
    return {"created": {"table": "tickets", "ticket_id": new_id}}


def _apply_update_ticket(
    conn: sqlite3.Connection, preview: dict, executed_at: str
) -> dict[str, Any]:
    ticket_id = preview["affects"]["record_id"]
    assignments, values = [], []
    for field, change in preview["changes"].items():
        assignments.append(f"{field} = ?")
        values.append(change["to"])
    conn.execute(
        f"UPDATE tickets SET {', '.join(assignments)} WHERE ticket_id = ?",
        (*values, ticket_id),
    )
    return {"updated": {"table": "tickets", "ticket_id": ticket_id,
                        "fields": list(preview["changes"]) }}


def _apply_follow_up(
    conn: sqlite3.Connection, preview: dict, caller: dict, executed_at: str
) -> dict[str, Any]:
    task_id = _new_id("TSK", conn, "follow_up_tasks", "task_id")
    changes = preview["changes"]
    conn.execute(
        """INSERT INTO follow_up_tasks (task_id, account_id, subject, due_at,
                                        created_at, created_by, status)
           VALUES (?, ?, ?, ?, ?, ?, 'open')""",
        (
            task_id,
            preview["affects"]["account_id"],
            changes["subject"],
            changes.get("due_at"),
            executed_at,
            caller.get("display_name") or caller.get("role") or "agent",
        ),
    )
    return {"created": {"table": "follow_up_tasks", "task_id": task_id}}


def cancel_action(conn: sqlite3.Connection, pending_id: str) -> dict[str, Any]:
    row = _load_pending(conn, pending_id)
    if row["status"] != "pending":
        raise ActionError(f"pending action '{pending_id}' is already {row['status']}")
    conn.execute("UPDATE pending_actions SET status='cancelled' WHERE id=?", (pending_id,))
    conn.commit()
    return {"pending_action_id": pending_id, "cancelled": True}
