"""Proactive internal insights (Req P1).

compute_insights() scans orders + tickets at the dataset snapshot time and
surfaces what deserves staff attention today:

- ticket volume spikes (last 7 days vs the prior week, per account/category)
- SLA watchlist: breached or near-breach open tickets
- service quality: late pickups / late deliveries in the trailing window
- credit exposure: credits that WOULD be payable if claimed now, plus items
  flagged for manual review
- cross-customer patterns: same category recurring across >= 2 accounts

Everything is deterministic SQL/python - no LLM involved.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.rules import effective_rules
from app.timebase import get_snapshot_time, parse_iso_utc


def _ts(value: str | None) -> datetime | None:
    return parse_iso_utc(value) if value else None


def compute_insights(conn: sqlite3.Connection) -> dict[str, Any]:
    now = get_snapshot_time(conn)
    accounts = {
        row["account_id"]: dict(row)
        for row in conn.execute("SELECT * FROM accounts")
    }
    return {
        "generated_at": now.isoformat(),
        "ticket_volume": _ticket_volume(conn, now, accounts),
        "sla_watchlist": _sla_watchlist(conn, now, accounts),
        "service_quality": _service_quality(conn, now),
        "credit_exposure": _credit_exposure(conn, now, accounts),
        "cross_customer_patterns": _cross_customer_patterns(conn, now),
    }


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------
def _ticket_volume(
    conn: sqlite3.Connection, now: datetime, accounts: dict[str, dict]
) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT account_id, category, created_at FROM tickets
        WHERE created_at IS NOT NULL
        """
    ).fetchall()

    week_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)

    def bucket(created_iso: str) -> str | None:
        created = _ts(created_iso)
        if created is None or created > now:
            return None  # ignore future-dated fixture noise
        if created >= week_start:
            return "this_week"
        if created >= prev_start:
            return "prev_week"
        return None

    per_account: Counter[tuple[str, str]] = Counter()
    per_category: Counter[str] = Counter()
    for row in rows:
        period = bucket(row["created_at"])
        if period == "this_week":
            per_account[(row["account_id"], row["category"] or "uncategorised")] += 1
            per_category[row["category"] or "uncategorised"] += 1
        elif period == "prev_week":
            per_account[(row["account_id"], "*prev*")] += 1

    totals = {"this_week": sum(per_category.values()), "prev_week": 0}
    account_this_week: Counter[str] = Counter()
    for (account_id, category), count in per_account.items():
        if category != "*prev*":
            account_this_week[account_id] += count
    totals["prev_week"] = sum(
        count for (account_id, category), count in per_account.items() if category == "*prev*"
    )

    spikes = []
    for account_id, count in sorted(account_this_week.items()):
        prev = per_account.get((account_id, "*prev*"), 0)
        if count >= 2 and count > 2 * prev:
            top = [
                {"category": cat, "count": n}
                for (acc, cat), n in per_account.most_common()
                if acc == account_id and cat != "*prev*"
            ][:2]
            spikes.append(
                {
                    "account_id": account_id,
                    "account_name": accounts[account_id]["account_name"],
                    "this_week": count,
                    "prev_week": prev,
                    "top_categories": top,
                }
            )

    return {
        "totals": totals,
        "by_category": [
            {"category": cat, "count": n} for cat, n in per_category.most_common()
        ],
        "spikes": spikes,
    }


def _sla_watchlist(
    conn: sqlite3.Connection, now: datetime, accounts: dict[str, dict]
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT t.*, a.account_name FROM tickets t JOIN accounts a USING (account_id)
        WHERE lower(t.status) NOT IN ('resolved', 'closed')
          AND t.created_at IS NOT NULL
        ORDER BY t.created_at
        """
    ).fetchall()

    watch: list[dict[str, Any]] = []
    for row in rows:
        ticket = dict(row)
        created = _ts(ticket["created_at"])
        if created is None or created > now:
            continue
        rules, provenance = effective_rules(accounts[ticket["account_id"]])
        priority = (ticket.get("priority") or "P3").upper()
        responded_at = _ts(ticket.get("first_response_at"))
        resolved_at = _ts(ticket.get("resolved_at"))

        response_due = created + timedelta(
            minutes=int(rules["response_sla_minutes"].get(priority, 480))
        )
        resolution_due = created + timedelta(
            minutes=int(rules["resolution_sla_minutes"].get(priority, 2880))
        )

        entry: dict[str, Any] = {
            "ticket_id": ticket["ticket_id"],
            "account_name": ticket["account_name"],
            "subject": ticket["subject"],
            "priority": priority,
            "created_at": ticket["created_at"],
            "governing_source": provenance,
            "problems": [],
        }
        if responded_at is None and now > response_due:
            entry["problems"].append(
                f"first response overdue by {_fmt(now - response_due)}"
            )
        if resolved_at is None and now > resolution_due:
            entry["problems"].append(
                f"resolution overdue by {_fmt(now - resolution_due)}"
            )
        elif resolved_at is None and resolution_due - now <= timedelta(minutes=120):
            entry["problems"].append(
                f"resolution SLA due in {_fmt(resolution_due - now)}"
            )
        if entry["problems"]:
            watch.append(entry)

    # most urgent first: overdue before near-breach, P1/P2 first
    def urgency(entry: dict[str, Any]) -> tuple[int, int]:
        overdue = sum(1 for p in entry["problems"] if "overdue" in p)
        priority_rank = {"P1": 0, "P2": 1, "P3": 2}.get(entry["priority"], 3)
        return (-overdue, priority_rank)

    return sorted(watch, key=urgency)


def _service_quality(conn: sqlite3.Connection, now: datetime) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT * FROM orders
        WHERE scheduled_pickup_at IS NOT NULL OR promised_delivery_at IS NOT NULL
        """
    ).fetchall()

    window_start = now - timedelta(days=14)
    late_pickups: list[dict[str, Any]] = []
    late_deliveries: list[dict[str, Any]] = []
    in_flight = 0

    for row in rows:
        order = dict(row)
        scheduled = _ts(order.get("scheduled_pickup_at"))
        actual = _ts(order.get("actual_pickup_at"))
        promised = _ts(order.get("promised_delivery_at"))
        delivered = _ts(order.get("delivered_at"))

        status = (order.get("status") or "").lower()
        if status not in ("delivered", "cancelled_after_pickup", "cancelled_before_pickup"):
            in_flight += 1

        reference = scheduled or promised
        if reference is None or reference < window_start or reference > now:
            continue

        if scheduled and actual and actual > now - timedelta(days=14):
            delay_min = (actual - scheduled).total_seconds() / 60.0
            if delay_min > 10:
                late_pickups.append(
                    {"order_id": order["order_id"], "delay_minutes": round(delay_min)}
                )
        if promised and delivered and delivered <= now:
            delay_min = (delivered - promised).total_seconds() / 60.0
            if delay_min > 0:
                late_deliveries.append(
                    {
                        "order_id": order["order_id"],
                        "delay_minutes": round(delay_min),
                        "delay_hours": round(delay_min / 60.0, 1),
                    }
                )
        if promised and not delivered and promised < now and status == "in_transit":
            late_deliveries.append(
                {
                    "order_id": order["order_id"],
                    "delay_minutes": None,
                    "delay_hours": None,
                    "note": "past promised delivery, still in transit",
                }
            )

    late_pickups.sort(key=lambda x: -(x["delay_minutes"] or 0))
    late_deliveries.sort(key=lambda x: -(x["delay_minutes"] or 0))
    return {
        "window_days": 14,
        "late_pickups": late_pickups[:10],
        "late_pickup_count": len(late_pickups),
        "late_deliveries": late_deliveries[:10],
        "late_delivery_count": len(late_deliveries),
        "orders_in_flight": in_flight,
    }


def _credit_exposure(
    conn: sqlite3.Connection, now: datetime, accounts: dict[str, dict]
) -> dict[str, Any]:
    """Credits that would be payable if customers claimed them right now."""
    from app.tools.calculations import late_pickup_credit

    exposure: dict[str, float] = defaultdict(float)
    manual_review: list[dict[str, Any]] = []

    rows = conn.execute("SELECT * FROM orders").fetchall()
    for row in rows:
        order = dict(row)
        account = accounts[order["account_id"]]

        from app.tools.calculations import late_delivery_credit, late_pickup_credit

        result = late_pickup_credit(conn, order, account, requested_at=now)
        if result.get("eligible") and result.get("amount_usd"):
            exposure[order["account_id"]] += float(result["amount_usd"])
        if result.get("requires_manual_review"):
            manual_review.append(
                {"kind": result["kind"], "order_id": order["order_id"], "basis": result.get("basis")}
            )

        d = late_delivery_credit(conn, order, account, requested_at=now)
        if d.get("requires_manual_review"):
            manual_review.append(
                {"kind": d["kind"], "order_id": order["order_id"], "basis": d.get("basis")}
            )

    return {
        "claimable_now_usd_by_account": {
            account_id: round(amount, 2)
            for account_id, amount in sorted(exposure.items())
        },
        "total_claimable_usd": round(sum(exposure.values()), 2),
        "manual_review": manual_review,
        "basis": (
            "Deterministic SOP/policy check run against every order as of the "
            "snapshot time; 'claimable' means every eligibility gate passes today."
        ),
    }


_KEYWORD_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "on", "in", "is", "not",
    "with", "was", "were", "be", "been", "at", "by", "it", "this", "that",
}


def _cross_customer_patterns(conn: sqlite3.Connection, now: datetime) -> list[dict[str, Any]]:
    """Category clusters appearing across >=2 distinct accounts recently."""
    cutoff = (now - timedelta(days=14)).isoformat()
    rows = conn.execute(
        """
        SELECT account_id, category, subject, description, created_at
        FROM tickets
        WHERE created_at >= ? AND created_at <= ?
          AND lower(COALESCE(status, '')) NOT IN ('resolved', 'closed')
        """,
        (cutoff, now.isoformat()),
    ).fetchall()

    clusters: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        category = row["category"] or "uncategorised"
        words = {
            w.lower()
            for w in ((row["subject"] or "") + " " + (row["description"] or "")).split()
            if len(w) > 4 and w.lower() not in _KEYWORD_STOPWORDS
        }
        clusters[category]["accounts"].add(row["account_id"])
        clusters[category]["keywords"] |= words

    patterns = []
    for category, info in clusters.items():
        if len(info["accounts"]) >= 2:
            patterns.append(
                {
                    "category": category,
                    "accounts_affected": len(info["accounts"]),
                    "shared_keywords": sorted(info["keywords"])[:8],
                    "hint": (
                        f"'{category}' issues are open at {len(info['accounts'])} accounts "
                        "simultaneously - check for a systemic cause."
                    ),
                }
            )
    return sorted(patterns, key=lambda p: -p["accounts_affected"])


def _fmt(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes >= 1440:
        return f"{minutes // 1440}d {minutes % 1440 // 60}h"
    if minutes >= 60:
        return f"{minutes // 60}h {minutes % 60}m"
    return f"{minutes}m"


__all__ = ["compute_insights"]
