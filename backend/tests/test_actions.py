"""Tool 3 tests: staging produces previews only; confirming mutates + audits."""

import json
import sqlite3
from pathlib import Path

import pytest

from app.ingestion.run import ingest
from app.tools.actions import (
    ActionError,
    cancel_action,
    confirm_action,
    stage_action,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="synthetic fixtures missing"
)

INTERNAL_CALLER = {
    "kind": "internal",
    "role": "support_agent",
    "display_name": "Avery (support)",
}


from typing import Generator

@pytest.fixture()
def conn(tmp_path) -> Generator[sqlite3.Connection, None, None]:
    db_path = tmp_path / "pp.db"
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def ticket_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]


# ---- staging -----------------------------------------------------------------
def test_staging_creates_pending_but_mutates_nothing(conn):
    before = ticket_count(conn)
    staged = stage_action(conn, INTERNAL_CALLER, "create_escalation", {
        "order_id": "ORD-1001", "reason": "Late delivery compensation needs human sign-off",
    })
    assert staged["pending_action_id"].startswith("PND-")
    assert staged["affects"]["account_id"] == "ACC-001"
    assert ticket_count(conn) == before  # nothing applied yet


def test_preview_summarizes_exact_change(conn):
    staged = stage_action(conn, INTERNAL_CALLER, "update_ticket", {
        "ticket_id": "TCK-2007",
        "updates": {"status": "in_progress", "resolution_note": "Ops reviewing"},
    })
    assert "'open' -> 'in_progress'" in staged["summary"]
    assert staged["changes"]["status"] == {"from": "open", "to": "in_progress"}


def test_invalid_action_type_and_params_rejected(conn):
    with pytest.raises(ActionError):
        stage_action(conn, INTERNAL_CALLER, "delete_account", {})
    with pytest.raises(ActionError):
        stage_action(conn, INTERNAL_CALLER, "create_escalation", {"order_id": "ORD-1001"})
    with pytest.raises(ActionError):
        stage_action(
            conn, INTERNAL_CALLER, "update_ticket",
            {"ticket_id": "TCK-2007", "updates": {"account_id": "ACC-002"}},  # immutable field
        )
    with pytest.raises(ActionError):  # unknown ticket
        stage_action(
            conn, INTERNAL_CALLER, "update_ticket",
            {"ticket_id": "TCK-9999", "updates": {"priority": "P1"}},
        )


# ---- confirmation ---------------------------------------------------------------
def test_confirm_executes_and_writes_audit_log(conn):
    staged = stage_action(conn, INTERNAL_CALLER, "create_escalation", {
        "ticket_id": "TCK-2013", "reason": "Cold-chain claim above approval threshold",
        "priority": "P1",
    })
    receipt = confirm_action(conn, staged["pending_action_id"])
    new_id = receipt["created"]["ticket_id"]

    row = conn.execute("SELECT * FROM tickets WHERE ticket_id=?", (new_id,)).fetchone()
    assert row["category"] == "escalation" and row["priority"] == "P1"
    assert row["account_id"] == "ACC-005"

    log_rows = conn.execute("SELECT * FROM actions_log").fetchall()
    assert len(log_rows) == 1
    log = dict(log_rows[0])
    assert log["action_type"] == "create_escalation"
    assert log["account_id"] == "ACC-005"
    actor = json.loads(log["actor_json"])
    assert actor["role"] == "support_agent"


def test_double_confirmation_is_rejected(conn):
    staged = stage_action(conn, INTERNAL_CALLER, "create_follow_up_task", {
        "account_id": "ACC-001", "subject": "Call Northstar about credit", "due_at": "2026-08-25",
    })
    confirm_action(conn, staged["pending_action_id"])
    with pytest.raises(ActionError, match="already executed"):
        confirm_action(conn, staged["pending_action_id"])
    assert conn.execute("SELECT COUNT(*) FROM follow_up_tasks").fetchone()[0] == 1


def test_cancel_discards_without_side_effects(conn):
    staged = stage_action(conn, INTERNAL_CALLER, "create_follow_up_task", {
        "account_id": "ACC-002", "subject": "Verify packaging fix",
    })
    cancel_action(conn, staged["pending_action_id"])
    with pytest.raises(ActionError, match="cancelled"):
        confirm_action(conn, staged["pending_action_id"])
    assert conn.execute("SELECT COUNT(*) FROM follow_up_tasks").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM actions_log").fetchone()[0] == 0


def test_update_ticket_applies_whitelisted_fields(conn):
    staged = stage_action(conn, INTERNAL_CALLER, "update_ticket", {
        "ticket_id": "TCK-2009", "updates": {"priority": "P1", "status": "resolved"},
    })
    confirm_action(conn, staged["pending_action_id"])
    row = dict(conn.execute("SELECT * FROM tickets WHERE ticket_id='TCK-2009'").fetchone())
    assert row["priority"] == "P1" and row["status"] == "resolved"


def test_unknown_pending_id_errors_cleanly(conn):
    with pytest.raises(ActionError):
        confirm_action(conn, "PND-doesnotexist")
