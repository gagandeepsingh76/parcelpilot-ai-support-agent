"""Trust-hardening tests (Req P2 / Problem 2).

Covers: historical tickets reachable ONLY as stamped context-only lookups for
internal roles, never as retrievable authority; customer denial; keyword
scoping to a single account; and prompt-level trust rules.
"""

import sqlite3
from pathlib import Path

import pytest

from app.access import Caller
from app.agent.prompts import INTERNAL_PROMPT, SHARED_RULES
from app.agent.toolspec import execute_tool_call
from app.ingestion.run import ingest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="synthetic fixtures missing"
)


@pytest.fixture()
def conn(tmp_path) -> sqlite3.Connection:
    db_path = tmp_path / "pp.db"
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def customer(aid: str) -> Caller:
    return Caller(kind="customer", account_id=aid, display_name="cust", session_id=f"s-{aid}")


def staff(role: str = "support_agent") -> Caller:
    return Caller(kind="internal", role=role, display_name="staff", session_id=f"s-{role}")


def _lookup(conn, caller, **payload):
    result, _meta = execute_tool_call(
        conn, caller, "data_lookup", {"lookup_type": "similar_past_tickets", **payload}
    )
    return result


def test_customer_cannot_pull_past_tickets(conn):
    result = _lookup(conn, customer("ACC-001"), account_id="ACC-001", keywords=["late"])
    assert "error" in result
    assert "internal" in result["error"].lower()


def test_staff_gets_context_only_stamped_matches(conn):
    result = _lookup(conn, staff(), account_id="ACC-001", keywords=["late", "pickup"])
    assert "error" not in result
    records = result["records"]
    assert records, "fixture pack should contain resolved late-pickup tickets for ACC-001"
    for record in records:
        assert record["context_only"] is True
        assert record["verified"] is False
        assert "NOT an authoritative source" in record["note"]
        # scoping: every match belongs to the requested account
        row = conn.execute(
            "SELECT account_id FROM tickets WHERE ticket_id=?", (record["ticket_id"],)
        ).fetchone()
        assert row["account_id"] == "ACC-001"


def test_keywords_required_and_account_required(conn):
    missing_kw = _lookup(conn, staff(), account_id="ACC-001")
    assert "error" in missing_kw and "keywords" in missing_kw["error"]

    missing_acc = _lookup(conn, staff(), keywords=["late"])
    assert "error" in missing_acc and "account_id" in missing_acc["error"]


def test_unmatched_keywords_return_empty_not_error(conn):
    result = _lookup(conn, staff(), account_id="ACC-001", keywords=["zzz-no-such-issue"])
    assert result["records"] == []


def test_usage_rule_warns_against_citing(conn):
    result = _lookup(conn, staff(), account_id="ACC-002", keywords=["pickup"])
    assert "NOT authoritative sources" in result["usage_rule"]


def test_prompts_encode_trust_rules():
    assert "CONTEXT ONLY" in SHARED_RULES
    assert "verified=false" in SHARED_RULES
    assert "similar_past_tickets" in INTERNAL_PROMPT
