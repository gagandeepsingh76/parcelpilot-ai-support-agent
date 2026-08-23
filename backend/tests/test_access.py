"""Access-control tests: cross-account denials enforced in the data layer."""

import json
import sqlite3
from pathlib import Path

import pytest
from typing import Generator


from app.access import (
    AccessDeniedError,
    Caller,
    registry,
    scoped_cancel_action,
    scoped_confirm_action,
    scoped_get_order,
    scoped_get_ticket,
    scoped_list_orders,
    scoped_list_tickets,
    scoped_stage_action,
)
from app.ingestion.run import ingest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="synthetic fixtures missing"
)


def customer(aid: str) -> Caller:
    return Caller(kind="customer", account_id=aid, display_name="cust", session_id=f"s-{aid}")


def staff(role: str) -> Caller:
    return Caller(kind="internal", role=role, display_name="staff", session_id=f"s-{role}")


@pytest.fixture()
def conn(tmp_path) -> Generator[sqlite3.Connection, None, None]:
    db_path = tmp_path / "pp.db"
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


# ---- customers cannot read other accounts' data ------------------------------
def test_customer_cannot_read_other_account_order(conn):
    with pytest.raises(AccessDeniedError):
        scoped_get_order(conn, customer("ACC-002"), "ORD-1001")  # Northstar order


def test_customer_cannot_read_other_account_ticket(conn):
    with pytest.raises(AccessDeniedError):
        scoped_get_ticket(conn, customer("ACC-003"), "TCK-2007")


def test_customer_cannot_list_other_account_records(conn):
    assert scoped_list_orders(conn, customer("ACC-001")) != []
    with pytest.raises(AccessDeniedError):
        scoped_list_orders(conn, customer("ACC-001"), account_id="ACC-002")
    tickets = scoped_list_tickets(conn, customer("ACC-001"))
    assert all(t["account_id"] == "ACC-001" for t in tickets)


def test_customer_reads_own_records_fine(conn):
    assert scoped_get_order(conn, customer("ACC-001"), "ORD-1001")["order_id"] == "ORD-1001"
    assert scoped_get_ticket(conn, customer("ACC-001"), "TCK-2007")["ticket_id"] == "TCK-2007"


# ---- internal roles ------------------------------------------------------------
def test_internal_can_read_any_account_with_explicit_id(conn):
    orders = scoped_list_orders(conn, staff("support_agent"), account_id="ACC-005")
    assert len(orders) > 0


def test_viewer_role_cannot_stage_actions(conn):
    with pytest.raises(AccessDeniedError):
        scoped_stage_action(
            conn, staff("viewer"), "create_escalation",
            {"order_id": "ORD-1001", "reason": "test"},
        )


def test_customer_cannot_stage_actions_at_all(conn):
    with pytest.raises(AccessDeniedError):
        scoped_stage_action(
            conn, customer("ACC-001"), "update_ticket",
            {"ticket_id": "TCK-2007", "updates": {"status": "resolved"}},
        )


def test_support_agent_stages_and_confirms_own_pending(conn):
    staged = scoped_stage_action(
        conn, staff("support_agent"), "create_follow_up_task",
        {"account_id": "ACC-001", "subject": "Confirm credit application"},
    )
    receipt = scoped_confirm_action(conn, staff("support_agent"), staged["pending_action_id"])
    assert receipt["created"]["task_id"].startswith("TSK-")
    log_row = conn.execute("SELECT actor_json FROM actions_log ORDER BY id DESC LIMIT 1").fetchone()
    assert json.loads(log_row["actor_json"])["role"] == "support_agent"


def test_cannot_confirm_someone_elses_pending_action(conn):
    staged = scoped_stage_action(
        conn, staff("support_agent"), "create_follow_up_task",
        {"account_id": "ACC-002", "subject": "Ops handoff"},
    )
    with pytest.raises(AccessDeniedError):
        scoped_confirm_action(conn, staff("ops"), staged["pending_action_id"])
    with pytest.raises(AccessDeniedError):
        scoped_cancel_action(conn, staff("ops"), staged["pending_action_id"])


# ---- mock session registry -------------------------------------------------------
def test_session_login_and_resolution():
    token = registry.login("cust-northstar")
    caller = registry.resolve(f"Bearer {token}")
    assert caller.is_customer and caller.account_id == "ACC-001"
    with pytest.raises(AccessDeniedError):
        registry.resolve("Bearer tok-bogus")
    with pytest.raises(AccessDeniedError):
        registry.resolve(None)
