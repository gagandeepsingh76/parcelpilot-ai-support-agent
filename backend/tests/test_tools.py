"""Tool 2 tests: deterministic calculations against fixture data."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.ingestion.run import ingest
from app.tools import data as d
from app.tools.calculations import (
    cancellation_fee,
    delivery_delay_minutes,
    late_delivery_credit,
    late_pickup_credit,
    pickup_delay_minutes,
    sla_status,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="synthetic fixtures missing"
)


from typing import Generator

@pytest.fixture(scope="module")
def conn(tmp_path_factory) -> Generator[sqlite3.Connection, None, None]:
    db_path = tmp_path_factory.mktemp("calc") / "pp.db"
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def get_order(conn, order_id):
    return d.get_order(conn, order_id)


def get_account(conn, account_id):
    return d.get_account(conn, account_id)


# ---- lateness primitives ---------------------------------------------------
def test_pickup_delay_ord_1001_is_47_minutes(conn):
    assert pickup_delay_minutes(get_order(conn, "ORD-1001")) == 47.0


def test_delivery_delay_ord_1001_is_9h30(conn):
    assert delivery_delay_minutes(get_order(conn, "ORD-1001")) == 570.0


def test_no_actual_pickup_means_none(conn):
    assert pickup_delay_minutes(get_order(conn, "ORD-1005")) is None


# ---- cancellation fees -------------------------------------------------------
def test_cancellation_after_pickup_standard_policy(conn):
    fee = cancellation_fee(
        conn, get_order(conn, "ORD-1006"), get_account(conn, "ACC-003"),
        now=datetime(2026, 8, 8, 13, 0, tzinfo=timezone.utc),
    )
    assert fee["fee_usd"] == 80.0  # 25% of 320 >= USD 40 floor
    assert fee["governing_source"]["doc_id"] == "01"


def test_cancellation_northstar_flat_fee_overrides_percentage(conn):
    fee = cancellation_fee(
        conn, get_order(conn, "ORD-1014"), get_account(conn, "ACC-001"),
        now=datetime(2026, 8, 14, 11, 0, tzinfo=timezone.utc),
    )
    assert fee["fee_usd"] == 75.0  # flat, not 25% of 275
    assert fee["governing_source"]["doc_id"] == "05"


def test_cancellation_lumenworks_lesser_of_rule(conn):
    # pickup happened 13:35Z on 08-04; evaluate after that
    fee = cancellation_fee(
        conn, get_order(conn, "ORD-1026"), get_account(conn, "ACC-002"),
        now=datetime(2026, 8, 4, 14, 0, tzinfo=timezone.utc),
    )
    assert fee["fee_usd"] == min(100.0, 0.20 * 300.0)  # lesser-of: USD 60


def test_cancellation_before_pickup_free(conn):
    fee = cancellation_fee(conn, get_order(conn, "ORD-1005"), get_account(conn, "ACC-004"))
    assert fee["fee_usd"] == 0.0 and fee["pickup_commenced"] is False


# ---- late pickup credits ------------------------------------------------------
def test_lumenworks_credit_via_agreement_override(conn):
    res = late_pickup_credit(
        conn, get_order(conn, "ORD-1026"), get_account(conn, "ACC-002"),
        requested_at=datetime(2026, 8, 10, tzinfo=timezone.utc),  # 6 days after incident
    )
    assert res["eligible"] is True
    assert res["amount_usd"] == 50.0
    assert res["governing_source"]["doc_id"] == "06"


def test_standard_tier1_credit_for_swiftmed(conn):
    res = late_pickup_credit(
        conn, get_order(conn, "ORD-1003"), get_account(conn, "ACC-005"),
        requested_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )
    assert res["eligible"] is True
    assert res["amount_usd"] == 25.0  # 95 min late: >90 but <180


def test_claim_raised_outside_window_blocks_eligibility(conn):
    res = late_pickup_credit(
        conn, get_order(conn, "ORD-1002"), get_account(conn, "ACC-002"),
        requested_at=datetime(2026, 9, 2, tzinfo=timezone.utc),  # >14 days
    )
    assert res["eligible"] is False
    assert "raised_within_claim_window" in res["blockers"]
    assert res["checks"]["breach_confirmed"]["value"] is True


def test_poor_standing_blocks_credit_even_when_breach_confirmed(conn):
    res = late_pickup_credit(
        conn, get_order(conn, "ORD-1011"), get_account(conn, "ACC-004"),
        requested_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
    )
    assert res["checks"]["account_good_standing"]["value"] is False
    assert res["eligible"] is False


def test_below_threshold_no_credit(conn):
    res = late_pickup_credit(
        conn, get_order(conn, "ORD-1014"), get_account(conn, "ACC-001"),
        requested_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )  # 48 min < Northstar's own terms don't cover pickup; standard needs >90
    assert res["eligible"] is False
    assert res["amount_usd"] is None


# ---- late delivery credit (Northstar) ------------------------------------------
def test_northstar_late_delivery_needs_manual_review_missing_fee_field(conn):
    res = late_delivery_credit(
        conn, get_order(conn, "ORD-1001"), get_account(conn, "ACC-001"),
        requested_at=datetime(2026, 8, 22, tzinfo=timezone.utc),
    )
    assert res["breach_confirmed"] is True          # 9.5 h > 4 h trigger
    assert res["requires_manual_review"] is True    # monthly fee absent from dataset


def test_on_time_delivery_no_breach(conn):
    res = late_delivery_credit(
        conn, get_order(conn, "ORD-1009"), get_account(conn, "ACC-001"),
        requested_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )
    assert res["breach_confirmed"] is False


# ---- SLA status -------------------------------------------------------------
def test_open_p2_ticket_response_sla_overdue_at_snapshot(conn):
    ticket = d.get_ticket(conn, "TCK-2007")  # created 08-20T10:15, no response
    status = sla_status(conn, ticket, get_account(conn, "ACC-001"))
    assert status["first_response"]["overdue"] is True
    assert status["first_response"]["met"] is False
    assert status["governing_source"]["doc_id"] == "05"  # agreement governs


def test_resolved_ticket_marks_resolution(conn):
    ticket = d.get_ticket(conn, "TCK-2010")
    status = sla_status(conn, ticket, get_account(conn, "ACC-003"))
    assert status["resolution"]["resolved"] is True


# ---- lookup errors -----------------------------------------------------------
def test_unknown_ids_raise_not_found(conn):
    with pytest.raises(LookupError):
        d.get_order(conn, "ORD-9999")
    with pytest.raises(LookupError):
        d.get_account(conn, "ACC-999")
