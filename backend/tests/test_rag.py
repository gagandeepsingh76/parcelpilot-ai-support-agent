"""Tool 1 tests: authority ranking, scoping, conflict surfacing.

Builds an isolated vector store (tmp dir) from the synthetic fixtures so the
developer's shared store under backend/data/chroma is never touched.
"""

import sqlite3
from pathlib import Path

import pytest

from app.ingestion.run import ingest
from app.rag.retrieval import search_documents
from app.rag.vectorstore import rebuild as rebuild_vector_store

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(),
    reason="synthetic fixture pack missing - regenerate with scripts/make_fixture_pack.py",
)


@pytest.fixture(scope="module")
def store(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("rag") / "pp.db"
    store_dir = tmp_path_factory.mktemp("rag_store")
    ingest(FIXTURES_DIR, db_path, include_vectors=False)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        chunks = rebuild_vector_store(conn, store_dir)
    finally:
        conn.close()
    assert chunks > 20
    return store_dir


def top_citation(result: dict) -> dict:
    return result["results"][0]["citation"]


def test_current_policy_beats_deprecated_on_same_topic(store):
    res = search_documents("cancellation fee after pickup has started", store_dir=store)
    assert top_citation(res)["status"] == "CURRENT"
    deprecated = [r for r in res["results"] if r["citation"]["status"] == "DEPRECATED"]
    assert deprecated == []  # filtered out of the default index


def test_deprecated_available_only_when_explicitly_requested(store):
    res = search_documents(
        "cancellation fee after pickup", include_deprecated=True, store_dir=store
    )
    statuses = {r["citation"]["status"] for r in res["results"]}
    assert "DEPRECATED" in statuses or any(
        c["kind"] == "current_vs_deprecated" for c in res["conflicts"]
    )


def test_northstar_agreement_outranks_global_policy_for_that_customer(store):
    res = search_documents(
        "what is the cancellation fee for our orders?",
        account_id="ACC-001",
        store_dir=store,
    )
    top = top_citation(res)
    assert top["doc_id"] == "05"
    # and the conflict is surfaced, not hidden
    kinds = {c["kind"] for c in res["conflicts"]}
    assert "agreement_vs_general_policy" in kinds


def test_lumenworks_pickup_credit_found_via_their_agreement(store):
    res = search_documents(
        "our pickup arrived late - are we entitled to a service credit?",
        account_id="ACC-002",
        store_dir=store,
    )
    top = top_citation(res)
    assert top["doc_id"] == "06"
    assert "$50" in res["results"][0]["text"].replace("USD 50", "$50") or "USD 50" in res["results"][0]["text"]


def test_known_issue_lookup_hits_product_guide(store):
    res = search_documents("ETA jumping around on rural routes", store_dir=store)
    top = top_citation(res)
    assert top["doc_id"] == "04"
    assert "KB-2025-011" in res["results"][0]["text"]


def test_sop_eligibility_rules_retrievable(store):
    res = search_documents("service credit eligibility checklist good standing", store_dir=store)
    assert top_citation(res)["doc_type"] == "sop"


def test_scoping_excludes_other_customers_agreements(store):
    res = search_documents(
        "cancellation terms", account_id="ACC-003", k=8, store_dir=store
    )
    scopes = {r["citation"]["customer_scope"] for r in res["results"]}
    assert "ACC-001" not in scopes
    assert "ACC-002" not in scopes


def test_result_shape_carries_citations_and_scores(store):
    res = search_documents("support severity levels response times", store_dir=store)
    first = res["results"][0]
    assert set(first["citation"]) >= {"doc_id", "title", "section", "status", "doc_type"}
    assert 0.0 <= first["similarity"] <= 1.0
    assert isinstance(first["authority_score"], float)
