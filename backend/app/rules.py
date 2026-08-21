"""Codified business rules extracted from the authoritative documents.

Every threshold carries its documentary source so answers citing these rules
can be traced back to a specific document + section. Numbers here MUST mirror
the ingested documents; tests cross-check the load-bearing ones.

If the real assessment pack changes any number, update this file (and its
tests) together with the PDFs - the retrieval layer stays untouched.
"""

from __future__ import annotations

from typing import Any

# ---- Standard terms: Customer Support Policy v3 CURRENT (doc_id '01') -----
STANDARD: dict[str, Any] = {
    "support_hours": {
        "window_utc": "08:00-20:00",
        "days": [0, 1, 2, 3, 4],  # Mon-Fri
        "source": {"doc_id": "01", "section": "2. Support Channels and Hours"},
    },
    "response_sla_minutes": {
        "P1": 60,
        "P2": 240,
        "P3": 480,  # simplified: business-day treated as 8h block (see ASSUMPTIONS)
        "source": {"doc_id": "01", "section": "3. Severity Levels and Response SLAs"},
    },
    "resolution_sla_minutes": {
        "P1": 480,
        "P2": 1440,
        "P3": 2880,
        "source": {"doc_id": "01", "section": "3. Severity Levels and Response SLAs"},
    },
    "cancellation": {
        "free_window_minutes_after_booking": 60,
        "free_if_before_pickup": True,
        "after_pickup_pct_of_value": 0.25,
        "after_pickup_min_usd": 40.0,
        "source": {"doc_id": "01", "section": "4. Cancellation Policy"},
    },
    "late_pickup_credit": {
        "tier1_min_delay_minutes": 90,
        "tier1_usd": 25.0,
        "tier2_min_delay_minutes": 180,
        "tier2_pct_of_value": 0.10,
        "tier2_cap_usd": 150.0,
        "claim_window_days": 14,
        "source": {"doc_id": "01", "section": "5. Late Pickup Compensation"},
    },
    "credit_administration": {
        "monthly_cap_usd": 500.0,
        "approval_threshold_usd": 250.0,
        "good_standing_required": True,
        "source": {"doc_id": "01", "section": "6. Service Credit Administration"},
    },
}

# ---- Customer-specific overrides from signed agreements -------------------
# Northstar Logistics Enterprise Agreement (doc_id '05', effective 2026-03-01)
NORTHSTAR: dict[str, Any] = {
    "applies_to": "ACC-001",
    "agreement_ref": {"doc_id": "05", "title": "Northstar Logistics Enterprise Agreement"},
    "order_of_precedence": "agreement overrides standard support policy",
    "response_sla_minutes": {
        "P1": 15,
        "P2": 240,
        "P3": 480,
        "always_on": True,
        "source": {"doc_id": "05", "section": "4. Service Levels"},
    },
    "cancellation": {
        "free_if_before_pickup": True,
        "after_pickup_flat_usd": 75.0,
        "source": {"doc_id": "05", "section": "3. Cancellation Terms"},
    },
    "late_delivery_credit": {
        "trigger_delay_hours": 4,
        "pct_of_monthly_recurring_fee": 0.05,
        "monthly_cap_pct": 0.20,
        "claim_window_days": 30,
        "requires_field": "monthly_recurring_fee_usd",  # absent from dataset -> manual review
        "source": {"doc_id": "05", "section": "5. Late Delivery Compensation"},
    },
}

# LumenWorks Ltd Service Agreement (doc_id '06', effective 2026-01-15)
LUMENWORKS: dict[str, Any] = {
    "applies_to": "ACC-002",
    "agreement_ref": {"doc_id": "06", "title": "LumenWorks Ltd Service Agreement"},
    "order_of_precedence": "agreement overrides standard support policy",
    "cancellation": {
        "free_if_before_pickup": True,
        "after_pickup_lesser_of_flat_usd": 100.0,
        "after_pickup_lesser_of_pct": 0.20,
        "source": {"doc_id": "06", "section": "3. Cancellation Terms"},
    },
    "late_pickup_credit": {
        "tier1_min_delay_minutes": 60,
        "tier1_usd": 50.0,
        "claim_window_days": 14,
        "source": {"doc_id": "06", "section": "4. Pickup Reliability Credit"},
    },
}

ACCOUNT_RULES: dict[str, dict[str, Any]] = {
    NORTHSTAR["applies_to"]: NORTHSTAR,
    LUMENWORKS["applies_to"]: LUMENWORKS,
}


def rules_for_account(account_id: str | None) -> dict[str, Any]:
    """Merged view: standard rules with any account-specific overrides applied."""
    merged = {**STANDARD}
    override = ACCOUNT_RULES.get(account_id or "", {})
    for key, value in override.items():
        if key in ("applies_to", "agreement_ref", "order_of_precedence"):
            continue
        merged[key] = value
    merged["account_agreement"] = override.get("agreement_ref")
    return merged


def effective_rules(account: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(rules, provenance) for an account row."""
    account_id = str(account.get("account_id") or "")
    rules = rules_for_account(account_id)
    provenance = (
        {
            **rules["account_agreement"],
            "note": rules.get("order_of_precedence", ""),
        }
        if rules.get("account_agreement")
        else {"doc_id": "01", "note": "standard support policy applies"}
    )
    return rules, provenance
