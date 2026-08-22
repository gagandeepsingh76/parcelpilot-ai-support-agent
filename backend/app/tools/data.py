"""Parameterized structured-data lookups (Tool 2, query half).

Every function takes an open sqlite3 connection and uses bound parameters.
Access-control scoping is applied by callers in the access layer (Step 5);
these functions stay pure so they are directly testable.
"""

from __future__ import annotations

import sqlite3
from typing import Any


class NotFoundError(LookupError):
    pass


def get_account(conn: sqlite3.Connection, account_id: str) -> dict[str, Any]:
    row = conn.execute(
        """SELECT account_id, account_name, tier, primary_contact,
                  good_standing, onboarded_at
           FROM accounts WHERE account_id = ?""",
        (account_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"unknown account_id '{account_id}'")
    return dict(row)


def get_order(conn: sqlite3.Connection, order_id: str) -> dict[str, Any]:
    row = conn.execute(
        """SELECT order_id, account_id, service_type, booked_at, scheduled_pickup_at,
                  actual_pickup_at, promised_delivery_at, delivered_at, status,
                  order_value_usd
           FROM orders WHERE order_id = ?""",
        (order_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"unknown order_id '{order_id}'")
    return dict(row)


def list_orders_for_account(conn: sqlite3.Connection, account_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT order_id, service_type, status, booked_at, scheduled_pickup_at,
                  actual_pickup_at, promised_delivery_at, delivered_at, order_value_usd
           FROM orders WHERE account_id = ? ORDER BY booked_at DESC LIMIT ?""",
        (account_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_ticket(conn: sqlite3.Connection, ticket_id: str) -> dict[str, Any]:
    row = conn.execute(
        """SELECT ticket_id, account_id, order_id, category, subject, description,
                  priority, created_at, first_response_at, resolved_at, status,
                  resolution_note
           FROM tickets WHERE ticket_id = ?""",
        (ticket_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError(f"unknown ticket_id '{ticket_id}'")
    return dict(row)


def list_tickets_for_account(conn: sqlite3.Connection, account_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT ticket_id, account_id, order_id, category, subject, priority,
                  created_at, first_response_at, resolved_at, status
           FROM tickets WHERE account_id = ? ORDER BY created_at DESC LIMIT ?""",
        (account_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def search_resolved_tickets(
    conn: sqlite3.Connection,
    account_id: str,
    keywords: list[str],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Similar RESOLVED tickets for an account - CONTEXT ONLY, never authority.

    Deliberately excluded from the RAG index (see Step 2/9); surfaced here so
    internal staff can reference precedent. Every row is stamped
    context_only=True / verified=False so the model cannot mistake it for a
    citable policy source.
    """
    if not keywords:
        return []
    like_clauses = []
    params: list[Any] = [account_id]
    for keyword in keywords[:6]:
        like_clauses.append(
            "(subject LIKE ? OR description LIKE ? OR resolution_note LIKE ?)"
        )
        escaped = f"%{keyword.strip()}%"
        params.extend([escaped, escaped, escaped])
    params.append(limit)
    rows = conn.execute(
        f"""
        SELECT ticket_id, order_id, category, subject, priority, created_at,
               resolved_at, resolution_note
        FROM tickets
        WHERE account_id = ?
          AND lower(COALESCE(status, '')) IN ('resolved', 'closed')
          AND ({' OR '.join(like_clauses)})
        ORDER BY resolved_at DESC LIMIT ?
        """,
        params,
    ).fetchall()
    return [
        {
            **dict(row),
            "context_only": True,
            "verified": False,
            "note": (
                "similar past ticket - operational context only; NOT an "
                "authoritative source. Never quote amounts, entitlements or "
                "terms from it."
            ),
        }
        for row in rows
    ]


def monthly_credits_issued(conn: sqlite3.Connection, account_id: str, month_start: str) -> float:
    """Sum of credits already issued this calendar month from the actions log.

    Reads the audited actions table (created in Step 4); before that table
    exists or when empty this returns 0.0.
    """
    try:
        row = conn.execute(
            """SELECT COALESCE(SUM(CAST(json_extract(payload_json, '$.amount_usd') AS REAL)), 0)
               FROM actions_log
               WHERE account_id = ?
                 AND action_type = 'issue_service_credit'
                 AND created_at >= ?""",
            (account_id, month_start),
        ).fetchone()
        return float(row[0] or 0.0)
    except sqlite3.OperationalError:
        return 0.0
