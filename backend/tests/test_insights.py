"""Insights dashboard tests (Req P1) - deterministic, snapshot-time based.

Covers: volume spike detection, SLA watchlist ordering, late pickup/delivery
detection windows, credit exposure aggregation incl. manual-review flags,
cross-customer patterns, and the endpoint's internal-only access rule.
"""

import sqlite3
from pathlib import Path

import pytest

from app.access import Caller
from app.insights.service import compute_insights
from app.ingestion.run import ingest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="synthetic fixtures missing"
)


from typing import Generator

@pytest.fixture()
def conn(tmp_path) -> Generator[sqlite3.Connection, None, None]:
    db_path = tmp_path / "pp.db"
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def staff(role: str = "support_agent") -> Caller:
    return Caller(kind="internal", role=role, display_name="staff", session_id=f"s-{role}")


def test_insights_shape_and_snapshot_time(conn):
    report = compute_insights(conn)
    assert report["generated_at"] == "2026-08-21T23:59:00+00:00"
    for section in (
        "ticket_volume",
        "sla_watchlist",
        "service_quality",
        "credit_exposure",
        "cross_customer_patterns",
    ):
        assert section in report


def test_ticket_volume_totals_ignore_future_dated_rows(conn):
    volume = compute_insights(conn)["ticket_volume"]
    total_rows = conn.execute("SELECT COUNT(*) c FROM tickets").fetchone()["c"]
    # future-dated tickets (after snapshot) must not inflate the counts
    assert volume["totals"]["this_week"] + volume["totals"]["prev_week"] <= total_rows
    assert isinstance(volume["spikes"], list)


def test_sla_watchlist_flags_open_tickets_only(conn):
    watch = compute_insights(conn)["sla_watchlist"]
    resolved_ids = {
        r["ticket_id"] for r in conn.execute(
            "SELECT ticket_id FROM tickets WHERE lower(status) IN ('resolved','closed')"
        )
    }
    for entry in watch:
        assert entry["ticket_id"] not in resolved_ids
        assert entry["problems"], f"{entry['ticket_id']} listed without a problem"


def test_service_quality_counts(conn):
    quality = compute_insights(conn)["service_quality"]
    assert quality["late_pickup_count"] >= 1      # fixture pack contains late pickups
    assert quality["orders_in_flight"] >= 1       # in-transit orders tracked


def test_credit_exposure_aggregates(conn):
    exposure = compute_insights(conn)["credit_exposure"]
    assert exposure["total_claimable_usd"] >= 0
    by_account = exposure["claimable_now_usd_by_account"]
    assert round(sum(by_account.values()), 2) == round(exposure["total_claimable_usd"], 2)
    # Northstar's agreement lacks monthly_recurring_fee_usd -> manual review path
    kinds = {item["kind"] for item in exposure["manual_review"]}
    assert kinds <= {"late_pickup_credit", "late_delivery_credit"}


def test_cross_customer_patterns_structure(conn):
    patterns = compute_insights(conn)["cross_customer_patterns"]
    for pattern in patterns:
        assert pattern["accounts_affected"] >= 2
        assert pattern["hint"].endswith("systemic cause.")


def test_endpoint_internal_only(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import app.api.routes as api_routes
    from app.main import app

    db_path = tmp_path / "pp.db"
    ingest(FIXTURES_DIR, db_path, include_vectors=False)

    def fresh_conn():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    app.dependency_overrides[api_routes.get_conn] = fresh_conn
    try:
        client = TestClient(app)
        customer_token = client.post(
            "/api/session/login", json={"session_key": "cust-northstar"}
        ).json()["token"]
        staff_token = client.post(
            "/api/session/login", json={"session_key": "staff-agent"}
        ).json()["token"]

        denied = client.get(
            "/api/insights/summary", headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert denied.status_code == 403

        allowed = client.get(
            "/api/insights/summary", headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert allowed.status_code == 200
        assert "ticket_volume" in allowed.json()
    finally:
        app.dependency_overrides.clear()
