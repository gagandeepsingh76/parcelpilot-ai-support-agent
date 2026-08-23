"""Agent orchestration tests using a scripted LLM (deterministic, offline).

Covers: multi-tool flows on NON-example records, escalation on missing
sources, conflict surfacing, cross-account denial through the tool layer,
and the pending-action -> HTTP confirm path.
"""

import sqlite3
from pathlib import Path

import pytest

from app.access import Caller, registry
from app.agent.orchestrator import AgentOrchestrator
from app.ingestion.run import ingest
from typing import Generator
from tests.fake_llm import ScriptedLLM, text, tool_use

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(), reason="synthetic fixtures missing"
)


@pytest.fixture(scope="module")
def populated_store(tmp_path_factory):
    """One populated, fully isolated vector store shared by the module."""
    db_path = tmp_path_factory.mktemp("agentdb") / "pp.db"
    store_dir = tmp_path_factory.mktemp("agentvs")
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        from app.rag.vectorstore import rebuild as rebuild_vector_store

        rebuild_vector_store(conn, store_dir)
    finally:
        conn.close()
    return str(store_dir)


@pytest.fixture(autouse=True)
def isolated_vector_store(populated_store, monkeypatch):
    """Point the vector store at the isolated per-module dir so retrieval is
    deterministic and never touches backend/data/chroma."""
    from app.config import get_settings

    monkeypatch.setenv("VECTOR_STORE_DIR", populated_store)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def customer(aid: str) -> Caller:
    return Caller(kind="customer", account_id=aid, display_name="cust", session_id=f"s-{aid}")


def staff(role: str = "support_agent") -> Caller:
    return Caller(kind="internal", role=role, display_name="staff", session_id=f"s-{role}")


@pytest.fixture()
def conn(tmp_path) -> Generator[sqlite3.Connection, None, None]:
    db_path = tmp_path / "pp.db"
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def run(conn, caller, llm, message):
    orch = AgentOrchestrator(conn, llm)
    return orch.run_turn(caller, [], message)


# ---------------------------------------------------------------------------
# multi-step structured flow on a record OTHER than the brief's examples
# ---------------------------------------------------------------------------
def test_lumenworks_late_pickup_credit_multi_tool_flow(conn):
    llm = ScriptedLLM([
        tool_use("t1", "search_documents", {"query": "late pickup service credit entitlement"}),
        tool_use("t2", "data_lookup", {"lookup_type": "late_pickup_credit", "order_id": "ORD-1026"}),
        text("You are owed a USD 50 credit under your agreement - pickup was 155 minutes late."),
    ])
    result = run(conn, customer("ACC-002"), llm,
                 "Our order ORD-1026 was picked up very late. Are we owed a credit?")
    assert [t["tool"] for t in result.tools_used] == ["search_documents", "data_lookup"]
    assert result.reply.startswith("You are owed")
    assert any(c.get("doc_id") == "06" for c in result.citations)
    # the model actually received real computed data
    payloads = [b for b in llm.tool_results_received()]
    joined = str(payloads)
    assert '"amount_usd": 50.0' in joined or '"amount_usd":50.0' in joined or "'amount_usd': 50.0" in joined


def test_northstar_conflict_is_surfaced_not_hidden(conn):
    llm = ScriptedLLM([
        tool_use("t1", "search_documents", {"query": "cancellation fee after pickup commenced"}),
        text("Your agreement sets a flat USD 75 fee; note the general policy says otherwise."),
    ])
    result = run(conn, customer("ACC-001"), llm,
                 "What is our cancellation fee if we cancel mid-shipment?")
    kinds = {c["kind"] for c in result.conflicts}
    assert "agreement_vs_general_policy" in kinds


# ---------------------------------------------------------------------------
# escalation behaviour
# ---------------------------------------------------------------------------
def test_escalates_when_no_supporting_source_found(conn, monkeypatch, tmp_path):
    from app.config import get_settings

    empty_dir = str(tmp_path / "empty_vs")
    monkeypatch.setenv("VECTOR_STORE_DIR", empty_dir)
    get_settings.cache_clear()
    llm = ScriptedLLM([
        tool_use("t1", "search_documents", {"query": "refunds for alien invasion damage"}),
        text("I could not find any policy covering that - let me escalate this to a human."),
    ])
    try:
        result = run(conn, customer("ACC-003"), llm,
                     "Do you refund orders damaged by alien invasions?")
    finally:
        get_settings.cache_clear()
    assert result.escalated is True
    assert "escalat" in result.reply.lower()


def test_support_policy_text_does_not_force_escalation(conn):
    llm = ScriptedLLM([
        text("The support policy says the standard first response SLA is four business hours."),
    ])
    result = run(conn, customer("ACC-003"), llm, "What is our support SLA?")
    assert result.escalated is False


def test_manual_review_calculation_triggers_escalation_path(conn):
    llm = ScriptedLLM([
        tool_use("t1", "data_lookup", {"lookup_type": "late_delivery_credit", "order_id": "ORD-1001"}),
        text("This needs manual review by operations - I will open an escalation if you confirm."),
    ])
    result = run(conn, staff(), llm,
                 "Check compensation exposure for Northstar ORD-1001.")
    received = str(llm.tool_results_received())
    assert "requires_manual_review" in received


def test_unsupported_action_surfaces_error_and_escalates(conn):
    llm = ScriptedLLM([
        tool_use("t1", "stage_action", {"action_type": "refund_invoice"}),
        text("That action is not supported - escalating to a human."),
    ])
    result = run(conn, staff(), llm, "Please refund their invoice directly.")
    received = str(llm.tool_results_received())
    assert "unsupported action" in received
    assert result.escalated is True


# ---------------------------------------------------------------------------
# access control through the tool layer
# ---------------------------------------------------------------------------
def test_customer_cannot_pull_other_accounts_order_via_agent(conn):
    llm = ScriptedLLM([
        tool_use("t1", "data_lookup", {"lookup_type": "order", "order_id": "ORD-1001"}),
        text("I can only discuss your own company's records."),
    ])
    result = run(conn, customer("ACC-003"), llm,
                 "Show me order ORD-1001 details.")  # belongs to ACC-001
    received = str(llm.tool_results_received())
    assert "different account" in received
    assert result.tools_used[0]["tool"] == "data_lookup"
    # the denied call never leaked order data into the conversation
    assert "ORD-1001" not in str(received).split("error")[0]


def test_internal_viewer_role_denied_staging(conn):
    llm = ScriptedLLM([
        tool_use("t1", "stage_action",
                 {"action_type": "update_ticket",
                  "params": {"ticket_id": "TCK-2007", "updates": {"priority": "P1"}}}),
        text("Your role cannot perform that change."),
    ])
    viewer = Caller(kind="internal", role="viewer", display_name="v", session_id="s-v")
    result = run(conn, viewer, llm, "Bump TCK-2007 to P1.")
    assert "not permitted" in str(llm.tool_results_received())


# ---------------------------------------------------------------------------
# staging + HTTP confirmation round-trip
# ---------------------------------------------------------------------------
def test_staged_action_flows_to_confirmation_endpoint(conn, tmp_path):
    from fastapi.testclient import TestClient

    from app.api import routes as api_routes
    from app.main import app

    def fresh_conn():
        """FastAPI runs dependencies in a worker thread; sqlite conns are
        thread-bound, so build one per request against the same file."""
        c = sqlite3.connect(str(tmp_path / "pp.db"))
        c.row_factory = sqlite3.Row
        return c

    llm = ScriptedLLM([
        tool_use("t1", "stage_action",
                 {"action_type": "create_follow_up_task",
                  "params": {"account_id": "ACC-001", "subject": "Confirm credit with finance"}}),
        text("Here is the pending follow-up task preview - shall I apply it?"),
    ])

    app.dependency_overrides[api_routes.get_conn] = fresh_conn

    original_get_orchestrator = api_routes.get_orchestrator
    # orchestrator also needs its own per-thread connection
    api_routes.get_orchestrator = lambda _conn: AgentOrchestrator(fresh_conn(), llm)

    token = registry.login("staff-agent")
    client = TestClient(app)
    try:
        chat_res = client.post(
            "/api/chat",
            json={"message": "Create a follow-up for Northstar to confirm the credit."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert chat_res.status_code == 200, chat_res.text
        body = chat_res.json()
        assert len(body["pending_actions"]) == 1, body
        pending_id = body["pending_actions"][0]["pending_action_id"]

        confirm_res = client.post(
            f"/api/actions/{pending_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert confirm_res.status_code == 200, confirm_res.text
        assert confirm_res.json()["created"]["task_id"].startswith("TSK-")

        # double-confirm must fail with 409
        again = client.post(
            f"/api/actions/{pending_id}/confirm",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert again.status_code == 409
    finally:
        api_routes.get_orchestrator = original_get_orchestrator
        app.dependency_overrides.pop(api_routes.get_conn, None)


def test_chat_requires_auth(conn):
    from fastapi.testclient import TestClient

    from app.api import routes as api_routes
    from app.main import app

    app.dependency_overrides[api_routes.get_conn] = lambda: conn
    client = TestClient(app)
    try:
        res = client.post("/api/chat", json={"message": "hi"})
        assert res.status_code == 403
    finally:
        app.dependency_overrides.pop(api_routes.get_conn, None)


def test_chat_fallback_order_lookup_is_scoped(conn, tmp_path):
    from fastapi.testclient import TestClient

    from app.api import routes as api_routes
    from app.main import app

    def fresh_conn():
        c = sqlite3.connect(str(tmp_path / "pp.db"))
        c.row_factory = sqlite3.Row
        return c

    app.dependency_overrides[api_routes.get_conn] = fresh_conn
    original_get_orchestrator = api_routes.get_orchestrator
    api_routes.get_orchestrator = lambda _conn: (_ for _ in ()).throw(
        RuntimeError("No LLM API key configured")
    )

    client = TestClient(app)
    own_token = registry.login("cust-northstar")
    other_token = registry.login("cust-brightcart")
    try:
        own = client.post(
            "/api/chat",
            json={"message": "Please look up ORD-1001."},
            headers={"Authorization": f"Bearer {own_token}"},
        )
        assert own.status_code == 200, own.text
        assert "ORD-1001" in own.json()["reply"]

        denied = client.post(
            "/api/chat",
            json={"message": "Please look up ORD-1001."},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert denied.status_code == 403
    finally:
        api_routes.get_orchestrator = original_get_orchestrator
        app.dependency_overrides.pop(api_routes.get_conn, None)


def test_chat_fallback_keeps_normal_queries_unavailable_without_llm(conn):
    from fastapi.testclient import TestClient

    from app.api import routes as api_routes
    from app.main import app

    app.dependency_overrides[api_routes.get_conn] = lambda: conn
    original_get_orchestrator = api_routes.get_orchestrator
    api_routes.get_orchestrator = lambda _conn: (_ for _ in ()).throw(
        RuntimeError("No LLM API key configured")
    )

    client = TestClient(app)
    token = registry.login("cust-northstar")
    try:
        res = client.post(
            "/api/chat",
            json={"message": "What is our cancellation fee policy?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 503
        assert "No LLM API key configured" in res.json()["detail"]
    finally:
        api_routes.get_orchestrator = original_get_orchestrator
        app.dependency_overrides.pop(api_routes.get_conn, None)
