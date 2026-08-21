"""Deterministic SLA / lateness / credit calculations (Tool 2, calc half).

All arithmetic happens here - never in the LLM. Every result carries its
governing source so the agent can cite where a number came from.

'Now' is always the dataset snapshot time (timebase), never wall clock.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from app.rules import STANDARD, effective_rules, rules_for_account
from app.timebase import get_snapshot_time, parse_iso_utc
from app.tools.data import monthly_credits_issued


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def _ts(value: str | None) -> datetime | None:
    return parse_iso_utc(value) if value else None


def pickup_delay_minutes(order: dict[str, Any]) -> float | None:
    scheduled, actual = _ts(order.get("scheduled_pickup_at")), _ts(order.get("actual_pickup_at"))
    if not scheduled or not actual:
        return None
    return round((actual - scheduled).total_seconds() / 60.0, 1)


def delivery_delay_minutes(order: dict[str, Any]) -> float | None:
    promised, delivered = _ts(order.get("promised_delivery_at")), _ts(order.get("delivered_at"))
    if not promised or not delivered:
        return None
    return round((delivered - promised).total_seconds() / 60.0, 1)


# --------------------------------------------------------------------------
# cancellation fee
# --------------------------------------------------------------------------
def cancellation_fee(
    conn: sqlite3.Connection,
    order: dict[str, Any],
    account: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fee owed when this order is cancelled, under the governing source."""
    now = now or get_snapshot_time(conn)
    rules = rules_for_account(str(account["account_id"]))
    value = float(order.get("order_value_usd") or 0.0)

    actual_pickup = _ts(order.get("actual_pickup_at"))
    picked_up = actual_pickup is not None and actual_pickup <= now
    cancel_rule = rules["cancellation"]

    if not picked_up:
        return {
            "kind": "cancellation_fee",
            "order_id": order["order_id"],
            "pickup_commenced": False,
            "fee_usd": 0.0,
            "basis": (
                f"Pickup has not commenced as of {now.isoformat()}, so cancellation "
                "is free of charge."
            ),
            "governing_source": cancel_rule["source"],
        }

    if "after_pickup_flat_usd" in cancel_rule:  # Northstar-style agreement
        fee = float(cancel_rule["after_pickup_flat_usd"])
        basis = (
            f"Pickup commenced; the customer's agreement applies a flat USD {fee:.0f} "
            f"administrative fee regardless of order value."
        )
    elif "after_pickup_lesser_of_flat_usd" in cancel_rule:  # LumenWorks-style agreement
        fee = min(
            float(cancel_rule["after_pickup_lesser_of_flat_usd"]),
            value * float(cancel_rule["after_pickup_lesser_of_pct"]),
        )
        basis = (
            f"Pickup commenced; agreement fee is the lesser of USD "
            f"{cancel_rule['after_pickup_lesser_of_flat_usd']:.0f} or "
            f"{float(cancel_rule['after_pickup_lesser_of_pct']):.0%} of order value."
        )
    else:  # standard policy
        pct = float(cancel_rule["after_pickup_pct_of_value"])
        floor = float(cancel_rule["after_pickup_min_usd"])
        fee = max(value * pct, floor)
        basis = (
            f"Pickup commenced; standard policy fee is {pct:.0%} of order value "
            f"(minimum USD {floor:.0f})."
        )

    return {
        "kind": "cancellation_fee",
        "order_id": order["order_id"],
        "pickup_commenced": True,
        "fee_usd": round(fee, 2),
        "order_value_usd": value,
        "basis": basis,
        "governing_source": cancel_rule["source"],
    }


# --------------------------------------------------------------------------
# service credits
# --------------------------------------------------------------------------
def late_pickup_credit(
    conn: sqlite3.Connection,
    order: dict[str, Any],
    account: dict[str, Any],
    *,
    requested_at: datetime | None = None,
) -> dict[str, Any]:
    """SOP §5 eligibility checklist applied to a late-pickup credit request."""
    now = requested_at or get_snapshot_time(conn)
    rules = rules_for_account(str(account["account_id"]))
    credit_rule = rules.get("late_pickup_credit", STANDARD["late_pickup_credit"])

    delay = pickup_delay_minutes(order)
    threshold = int(credit_rule.get("tier1_min_delay_minutes", 10**9))
    breach_confirmed = delay is not None and delay > threshold

    incident_at = _ts(order.get("scheduled_pickup_at")) or _ts(order.get("booked_at"))
    window_days = int(credit_rule.get("claim_window_days", STANDARD["late_pickup_credit"]["claim_window_days"]))
    within_window = bool(incident_at and now <= incident_at + timedelta(days=window_days))

    good_standing = bool(int(account.get("good_standing") or 0))

    checks = {
        "breach_confirmed": {
            "value": breach_confirmed,
            "detail": (
                f"pickup delayed {delay:.0f} min vs required >{threshold} min"
                if delay is not None
                else "no completed pickup recorded - cannot confirm breach"
            ),
        },
        "raised_within_claim_window": {
            "value": within_window,
            "detail": (
                f"incident {incident_at.date().isoformat()} vs request {now.date().isoformat()} "
                f"(window: {window_days} days)"
                if incident_at else "incident timestamp unavailable"
            ),
        },
        "account_good_standing": {
            "value": good_standing,
            "detail": "account flagged in good standing" if good_standing
            else "account has unpaid invoices older than 30 days",
        },
    }

    blockers = [name for name, check in checks.items() if not check["value"]]
    amount, needs_review = _credit_amount(rules, credit_rule, order, delay)

    eligible = not blockers and amount is not None
    approval_threshold = float(STANDARD["credit_administration"]["approval_threshold_usd"])
    monthly_cap = float(STANDARD["credit_administration"]["monthly_cap_usd"])
    already_issued = monthly_credits_issued(
        conn, str(account["account_id"]), now.strftime("%Y-%m-01T00:00:00Z")
    ) if eligible else 0.0
    cap_remaining = round(max(0.0, monthly_cap - already_issued), 2)

    return {
        "kind": "late_pickup_credit",
        "order_id": order["order_id"],
        "account_id": account["account_id"],
        "eligible": eligible,
        "amount_usd": round(amount, 2) if amount is not None else None,
        "requires_manual_review": needs_review,
        "approval_required_above_usd": approval_threshold if eligible and amount and amount > approval_threshold else None,
        "monthly_cap_remaining_usd": cap_remaining,
        "checks": checks,
        "blockers": blockers,
        "basis": _credit_basis(rules, credit_rule, order),
        "governing_source": credit_rule.get(
            "source", rules["account_agreement"] or STANDARD["late_pickup_credit"]["source"]
        ),
    }


def _credit_amount(
    rules: dict[str, Any], credit_rule: dict[str, Any], order: dict[str, Any], delay: float | None
) -> tuple[float | None, bool]:
    """(amount_usd, requires_manual_review) under the governing rule set."""
    if delay is None:
        return None, False
    if "tier1_usd" in credit_rule:  # flat-credit schemes (standard & LumenWorks)
        tier1 = int(credit_rule["tier1_min_delay_minutes"])
        if delay > tier1:
            amount = float(credit_rule["tier1_usd"])
            tier2_min = credit_rule.get("tier2_min_delay_minutes")
            if tier2_min and delay > int(tier2_min):
                pct = float(credit_rule["tier2_pct_of_value"])
                cap = float(credit_rule["tier2_cap_usd"])
                amount = max(amount, min(float(order.get("order_value_usd") or 0.0) * pct, cap))
            return amount, False
        return None, False
    return None, False


def _credit_basis(rules: dict[str, Any], credit_rule: dict[str, Any], order: dict[str, Any]) -> str:
    if "tier1_usd" in credit_rule:
        tier1 = credit_rule["tier1_min_delay_minutes"]
        text = (
            f"Governing terms grant USD {float(credit_rule['tier1_usd']):.0f} once pickup "
            f"exceeds {int(tier1)} minutes' delay"
        )
        if credit_rule.get("tier2_min_delay_minutes"):
            text += (
                f"; beyond {int(credit_rule['tier2_min_delay_minutes'])} minutes the credit is "
                f"{float(credit_rule['tier2_pct_of_value']):.0%} of order value capped at "
                f"USD {float(credit_rule['tier2_cap_usd']):.0f}"
            )
        return text + "."
    if "pct_of_monthly_recurring_fee" in credit_rule:
        return (
            "This customer's agreement bases late-delivery compensation on their monthly "
            "recurring platform fee, which is not present in the dataset - amounts need "
            "manual review by operations."
        )
    return "No matching compensation clause found."


def late_delivery_credit(
    conn: sqlite3.Connection,
    order: dict[str, Any],
    account: dict[str, Any],
    *,
    requested_at: datetime | None = None,
) -> dict[str, Any]:
    """Northstar-style late-delivery compensation (agreement-specific)."""
    now = requested_at or get_snapshot_time(conn)
    rules = rules_for_account(str(account["account_id"]))
    rule = rules.get("late_delivery_credit")
    if not rule:
        return {
            "kind": "late_delivery_credit",
            "order_id": order["order_id"],
            "eligible": False,
            "requires_manual_review": False,
            "basis": "No late-delivery compensation clause governs this account.",
            "governing_source": STANDARD["source"] if "source" in STANDARD else {"doc_id": "01"},
        }

    delay = delivery_delay_minutes(order)
    trigger_hours = float(rule["trigger_delay_hours"])
    breach = delay is not None and delay > trigger_hours * 60
    incident_at = _ts(order.get("promised_delivery_at"))
    within_window = bool(incident_at and now <= incident_at + timedelta(days=int(rule["claim_window_days"])))

    if breach and "monthly_recurring_fee_usd" not in (order | account):
        review_blocker = True
    else:
        review_blocker = False

    return {
        "kind": "late_delivery_credit",
        "order_id": order["order_id"],
        "eligible": False,  # final amount always needs the missing fee field
        "breach_confirmed": breach,
        "delay_minutes": delay,
        "requires_manual_review": breach and review_blocker,
        "checks": {
            "delivery_beyond_trigger": {"value": breach,
                                        "detail": f"{delay:.0f} min late vs trigger {trigger_hours:.0f} h" if delay is not None else "not yet delivered"},
            "raised_within_claim_window": {"value": within_window,
                                           "detail": f"window {rule['claim_window_days']} days from promised time"},
        },
        "blockers": [] if (breach and within_window) else ["entitlement_not_confirmed"],
        "basis": _credit_basis(rules, rule, order),
        "governing_source": rule["source"],
    }


# --------------------------------------------------------------------------
# ticket SLA tracking
# --------------------------------------------------------------------------
def sla_status(
    conn: sqlite3.Connection, ticket: dict[str, Any], account: dict[str, Any]
) -> dict[str, Any]:
    """Response/resolution SLA position of a ticket at snapshot time.

    Simplification: SLA clocks use elapsed wall-clock minutes (business-hours
    calendars are a documented v2 item - see ASSUMPTIONS.md).
    """
    now = get_snapshot_time(conn)
    rules, provenance = effective_rules(account)
    priority = (ticket.get("priority") or "P3").upper()
    created = _ts(ticket.get("created_at"))

    response_sla = rules["response_sla_minutes"].get(priority, 480)
    resolution_sla = rules["resolution_sla_minutes"].get(priority, 2880)

    def _position(due: datetime | None):
        if due is None:
            return None
        delta = due - now
        return {
            "due_at": due.isoformat(),
            "minutes_remaining": round(delta.total_seconds() / 60.0, 1),
            "overdue": delta.total_seconds() < 0,
        }

    first_response_due = created + timedelta(minutes=response_sla) if created else None
    resolution_due = created + timedelta(minutes=resolution_sla) if created else None
    responded = _ts(ticket.get("first_response_at"))
    resolved = _ts(ticket.get("resolved_at"))

    return {
        "ticket_id": ticket["ticket_id"],
        "priority": priority,
        "always_on_sla": bool(rules["response_sla_minutes"].get("always_on")),
        "first_response": {
            **(_position(first_response_due) or {}),
            "met": responded is not None and first_response_due is not None and responded <= first_response_due,
        } if first_response_due else {},
        "resolution": (_position(resolution_due) or {}) | {"resolved": resolved is not None},
        "governing_source": provenance,
    }


def summarize_order_timeseries(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": order["order_id"],
        "status": order.get("status"),
        "pickup_delay_minutes": pickup_delay_minutes(order),
        "delivery_delay_minutes": delivery_delay_minutes(order),
        "promised_delivery_at": order.get("promised_delivery_at"),
        "delivered_at": order.get("delivered_at"),
    }
