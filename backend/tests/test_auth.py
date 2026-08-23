from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.agent.orchestrator import AgentOrchestrator
from app.api import routes as api_routes
from app.config import get_settings
from app.main import app
from tests.fake_llm import ScriptedLLM, text, tool_use

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _seeded_db():
    auth.bootstrap_auth(get_settings().sqlite_db_path_resolved)


def _login(username: str, password: str):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_seeded_customer_login_round_trip():
    res = _login("northstar", "demo1234")
    assert res.status_code == 200
    body = res.json()
    assert body["token"].startswith("ppat.")
    assert body["caller"]["kind"] == "customer"
    assert body["caller"]["account_id"] == "ACC-001"


def test_seeded_staff_login_carries_role():
    res = _login("agent", "staff1234")
    assert res.status_code == 200
    caller = res.json()["caller"]
    assert caller["kind"] == "internal"
    assert caller["role"] == "support_agent"


def test_wrong_password_rejected_without_user_enumeration():
    ok = _login("northstar", "demo1234").status_code
    bad = _login("northstar", "wrong-password")
    unknown = _login("no-such-user", "whatever1")
    assert bad.status_code == 401 and unknown.status_code == 401
    assert bad.json()["detail"] == unknown.json()["detail"] != ""
    assert ok == 200


def test_me_endpoint_accepts_signed_token():
    token = _login("northstar", "demo1234").json()["token"]
    res = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["account_id"] == "ACC-001"


def test_tampered_token_denied():
    token = _login("northstar", "demo1234").json()["token"]
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    res = client.get("/api/me", headers={"Authorization": f"Bearer {tampered}"})
    assert res.status_code == 403


def test_garbage_signed_format_denied():
    res = client.get("/api/me", headers={"Authorization": "Bearer ppat.not.valid"})
    assert res.status_code == 403


def test_customer_scoping_holds_for_credential_login():
    token = _login("northstar", "demo1234").json()["token"]
    llm = ScriptedLLM([
        tool_use("t1", "data_lookup", {"lookup_type": "orders_for_account", "account_id": "ACC-002"}),
        text("I cannot access data for other accounts."),
    ])
    original_get_orchestrator = api_routes.get_orchestrator
    api_routes.get_orchestrator = lambda conn: AgentOrchestrator(conn, llm)
    try:
        denied = client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Show me orders for account ACC-002"},
        )
        assert denied.status_code == 200
        # Assert tool layer denied cross-account access and returned error
        received = str(llm.tool_results_received()).lower()
        assert "different account" in received or "error" in received
    finally:
        api_routes.get_orchestrator = original_get_orchestrator


def test_viewer_credential_cannot_stage_actions():
    token = _login("viewer", "staff1234").json()["token"]
    res = client.get("/api/insights/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200  # viewer can read insights
    llm = ScriptedLLM([
        tool_use("t1", "stage_action", {"action_type": "create_escalation", "params": {"ticket_id": "TCK-2007", "reason": "escalate"}}),
        text("Your role is not permitted to perform that change."),
    ])
    original_get_orchestrator = api_routes.get_orchestrator
    api_routes.get_orchestrator = lambda conn: AgentOrchestrator(conn, llm)
    try:
        chat = client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Create an escalation for ticket TCK-2007"},
        )
        assert chat.status_code == 200  # refusal comes from the tool layer
        received = str(llm.tool_results_received()).lower()
        assert "not permitted" in received or "error" in received
    finally:
        api_routes.get_orchestrator = original_get_orchestrator


def test_staff_credential_reads_insights():
    token = _login("ops", "staff1234").json()["token"]
    res = client.get("/api/insights/summary", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "ticket_volume" in res.json()


def test_register_new_customer_on_existing_account():
    username = f"newco{uuid4().hex[:8]}"
    res = client.post(
        "/api/auth/register",
        json={"username": username, "password": "supersecret9", "account_id": "ACC-001"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["caller"]["account_id"] == "ACC-001"
    # new user can immediately log in and is scoped to that account
    login = _login(username, "supersecret9")
    assert login.status_code == 200
    assert login.json()["caller"]["account_id"] == "ACC-001"


def test_register_rejects_weak_password():
    res = client.post(
        "/api/auth/register",
        json={"username": f"weakpw{uuid4().hex[:8]}", "password": "short", "account_id": "ACC-001"},
    )
    assert res.status_code == 422


def test_register_rejects_duplicate_username():
    username = f"dupco{uuid4().hex[:8]}"
    payload = {"username": username, "password": "longenough8", "account_id": "ACC-002"}
    assert client.post("/api/auth/register", json=payload).status_code == 200
    dup = client.post("/api/auth/register", json={**payload, "account_id": "ACC-003"})
    assert dup.status_code == 409


def test_register_requires_existing_account():
    res = client.post(
        "/api/auth/register",
        json={"username": f"ghostco{uuid4().hex[:8]}", "password": "longenough8", "account_id": "ACC-999"},
    )
    assert res.status_code == 404
