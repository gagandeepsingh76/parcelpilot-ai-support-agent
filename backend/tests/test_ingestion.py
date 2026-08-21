"""End-to-end ingestion tests over the committed synthetic fixture pack."""

import sqlite3
from pathlib import Path

import pytest

from app.ingestion.run import ingest
from app.timebase import get_snapshot_time

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures" / "synthetic_datapack"

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR.exists(),
    reason="synthetic fixture pack missing - regenerate with scripts/make_fixture_pack.py",
)


@pytest.fixture(scope="module")
def db(tmp_path_factory) -> Path:
    target = tmp_path_factory.mktemp("ingest") / "parcelpilot.db"
    summary = ingest(FIXTURES_DIR, target)
    assert summary["documents"] == 6
    return target


def open_db(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn


def test_structured_tables_populated(db):
    conn = open_db(db)
    assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 5
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] >= 20
    assert conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] >= 15


def test_documents_tagged_correctly(db):
    conn = open_db(db)
    rows = {r["doc_id"]: r for r in conn.execute("SELECT * FROM documents")}
    assert len(rows) == 6
    assert rows["01"]["doc_type"] == "policy" and rows["01"]["status"] == "CURRENT"
    assert rows["02"]["status"] == "DEPRECATED"
    assert rows["03"]["doc_type"] == "sop"
    assert rows["04"]["doc_type"] == "product-guide"
    # customer agreements scoped to their accounts, everything else global
    assert rows["05"]["customer_scope"] == "ACC-001"
    assert rows["06"]["customer_scope"] == "ACC-002"
    for doc_id in ("01", "02", "03", "04"):
        assert rows[doc_id]["customer_scope"] == "global"


def test_sections_extracted_with_headings(db):
    conn = open_db(db)
    sop_headings = [
        r["heading"]
        for r in conn.execute(
            "SELECT heading FROM document_sections WHERE doc_id='03' ORDER BY seq"
        )
    ]
    assert any("Service Credit Eligibility Checklist" in h for h in sop_headings)
    total = conn.execute("SELECT COUNT(*) FROM document_sections").fetchone()[0]
    assert total >= 30


def test_snapshot_time_cached_and_resolvable(db):
    conn = open_db(db)
    snapshot = get_snapshot_time(conn)
    assert snapshot.isoformat().startswith("2026-08-21T23:59:00")


def test_order_row_round_trips_timestamps(db):
    conn = open_db(db)
    row = dict(conn.execute("SELECT * FROM orders WHERE order_id='ORD-1001'").fetchone())
    assert row["account_id"] == "ACC-001"
    assert row["scheduled_pickup_at"] == "2026-08-18T09:00:00Z"
    assert row["actual_pickup_at"] == "2026-08-18T09:47:00Z"
    assert row["delivered_at"] == "2026-08-20T02:30:00Z"
    assert row["order_value_usd"] == 840.0


def test_reingest_is_idempotent(db, tmp_path):
    second = tmp_path / "again.db"
    ingest(FIXTURES_DIR, second)
    ingest(FIXTURES_DIR, second)  # rebuild must not duplicate or fail
    conn = open_db(second)
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 6
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == (
        open_db(db).execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    )


def test_missing_pack_gives_guidance(tmp_path):
    from app.ingestion.run import IngestionError

    with pytest.raises(IngestionError) as excinfo:
        ingest(tmp_path / "empty", tmp_path / "out.db")
    assert "no PDFs or XLSX found" in str(excinfo.value)
