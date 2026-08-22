"""Deployment bootstrap: ensure the DB + vector index exist, then serve.

Free-tier hosts (Render etc.) have an EPHEMERAL disk, so the SQLite DB and
Chroma store are rebuilt from the source documents on every boot:

1. source = ./data_pack  (the real candidate pack, when the repo owner adds it)
           else ../fixtures/synthetic_datapack (committed synthetic pack)
2. python -m app.deploy_bootstrap     # ingest into SQLITE_DB_PATH/VECTOR_STORE_DIR
3. uvicorn app.main:app ...           # actual server (render.yaml startCommand)

Idempotent: if the DB already contains orders AND the vector store is
populated, ingestion is skipped (saves ~40s of cold-start on restarts where
the disk survived).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def pick_source() -> Path:
    real_pack = REPO_ROOT / "data_pack"
    has_documents = any(real_pack.glob("*.pdf")) and any(real_pack.glob("*.xlsx"))
    if has_documents:
        return real_pack
    fixtures = REPO_ROOT / "fixtures" / "synthetic_datapack"
    if any(fixtures.glob("*.pdf")):
        print(
            "[bootstrap] no files in data_pack/ - ingesting the committed "
            "synthetic fixtures so the deployed demo is fully functional."
        )
        return fixtures
    raise SystemExit(
        "[bootstrap] nothing to ingest: data_pack/ is empty and fixtures are missing"
    )


def already_ingested(db_path: Path) -> bool:
    if not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            meta = conn.execute(
                "SELECT COUNT(*) FROM dataset_meta WHERE key='snapshot_utc'"
            ).fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return orders > 0 and docs > 0 and meta > 0


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from app.config import get_settings
    from app.ingestion.run import ingest

    settings = get_settings()
    db_path = Path(settings.sqlite_db_path_resolved)
    vector_dir = Path(settings.vector_store_dir_resolved)

    marker = vector_dir / ".ingested_ok"
    if db_path.exists() and marker.exists() and already_ingested(db_path):
        print("[bootstrap] database and vector index present - skipping ingestion")
        return 0

    source = pick_source()
    print(f"[bootstrap] ingesting from {source}")
    summary = ingest(source, db_path, include_vectors=True)
    print(f"[bootstrap] ingested: {summary.get('documents', '?')} docs, "
          f"{summary.get('accounts', '?')} accounts, {summary.get('orders', '?')} orders")
    vector_dir.mkdir(parents=True, exist_ok=True)
    marker.write_text(summary.get("snapshot_utc", ""), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
