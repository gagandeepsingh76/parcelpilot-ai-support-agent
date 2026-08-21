"""Ingestion orchestrator.

Rebuilds the SQLite database from scratch on every run:
  data_pack/*.pdf -> documents + document_sections (+ derived metadata)
  ParcelPilot_Assessment_Data.xlsx -> accounts, orders, tickets, dataset_meta

Usage:
  python -m app.ingestion.run [--source DIR] [--db PATH]
Defaults come from settings (DATA_PACK_DIR / SQLITE_DB_PATH).
Relative paths resolve against the repository root so the command works from
any working directory.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.ingestion.metadata import derive_docmeta
from app.ingestion.pdfparse import parse_pdf
from app.ingestion.xlsxload import (
    IngestionError,
    load_accounts,
    load_orders,
    load_tickets,
    open_workbook,
    read_key_values,
    require_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_path(path_value: str | Path) -> Path:
    """Resolve a path: absolute as-is, otherwise repo-root-relative.

    Repo-root-relative keeps every configured location stable no matter which
    working directory uvicorn/tests are started from.
    """
    path = Path(path_value)
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id         TEXT PRIMARY KEY,
    filename       TEXT NOT NULL UNIQUE,
    title          TEXT NOT NULL,
    version        TEXT,
    status         TEXT NOT NULL DEFAULT 'CURRENT'
                   CHECK (status IN ('CURRENT','DEPRECATED')),
    doc_type       TEXT NOT NULL CHECK (doc_type IN ('policy','sop','product-guide','agreement')),
    customer_scope TEXT NOT NULL DEFAULT 'global',
    page_count     INTEGER NOT NULL DEFAULT 0,
    ingested_at    TEXT NOT NULL,
    full_text      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_sections (
    section_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id     TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    seq        INTEGER NOT NULL,
    level      INTEGER NOT NULL DEFAULT 1,
    heading    TEXT NOT NULL,
    text       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sections_doc ON document_sections(doc_id);

CREATE TABLE IF NOT EXISTS accounts (
    account_id      TEXT PRIMARY KEY,
    account_name    TEXT NOT NULL,
    tier            TEXT,
    primary_contact TEXT,
    good_standing   INTEGER NOT NULL DEFAULT 1,
    onboarded_at    TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id            TEXT PRIMARY KEY,
    account_id          TEXT NOT NULL REFERENCES accounts(account_id),
    service_type        TEXT,
    booked_at           TEXT,
    scheduled_pickup_at TEXT,
    actual_pickup_at    TEXT,
    promised_delivery_at TEXT,
    delivered_at        TEXT,
    status              TEXT,
    order_value_usd     REAL
);
CREATE INDEX IF NOT EXISTS idx_orders_account ON orders(account_id);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id         TEXT PRIMARY KEY,
    account_id        TEXT NOT NULL REFERENCES accounts(account_id),
    order_id          TEXT REFERENCES orders(order_id),
    category          TEXT,
    subject           TEXT,
    description       TEXT,
    priority          TEXT,
    created_at        TEXT,
    first_response_at TEXT,
    resolved_at       TEXT,
    status            TEXT,
    resolution_note   TEXT
);
CREATE INDEX IF NOT EXISTS idx_tickets_account ON tickets(account_id);

CREATE TABLE IF NOT EXISTS dataset_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

TABLES_TO_DROP = ["document_sections", "documents", "tickets", "orders", "accounts", "dataset_meta"]


def _resolve_customer_scope_for_accounts(accounts: list[dict]) -> list[str]:
    warnings = []
    ids = [str(a.get("account_id")) for a in accounts]
    if len(ids) != len(set(ids)):
        warnings.append("duplicate account_id values found in workbook")
    return warnings


def ingest(source_dir: str | Path, db_path: str | Path, *, include_vectors: bool = True) -> dict:
    source = resolve_path(source_dir)
    db_path = resolve_path(db_path)

    pdf_paths = sorted(source.glob("*.pdf")) if source.exists() else []
    xlsx_paths = sorted(source.glob("*.xlsx")) if source.exists() else []

    if not pdf_paths and not xlsx_paths:
        raise IngestionError(
            f"no PDFs or XLSX found in '{source}'. Drop the candidate data pack there "
            "(see data_pack/README.md), or point --source at "
            "'fixtures/synthetic_datapack' to ingest the committed synthetic fixtures."
        )
    if not xlsx_paths:
        raise IngestionError(f"no ParcelPilot XLSX workbook found in '{source}'")
    if len(xlsx_paths) > 1:
        raise IngestionError(
            f"multiple .xlsx files in '{source}': {', '.join(p.name for p in xlsx_paths)} - keep exactly one"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        with conn:
            for table in TABLES_TO_DROP:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.executescript(SCHEMA_SQL)

            # ---- structured data -------------------------------------------
            wb = open_workbook(xlsx_paths[0])
            readme = read_key_values(find_readme_sheet(wb))
            snapshot_utc = require_snapshot(readme)

            accounts = load_accounts(wb)
            orders = load_orders(wb)
            tickets = load_tickets(wb)
            warnings = _resolve_customer_scope_for_accounts(accounts)

            account_ids = {str(a["account_id"]) for a in accounts}
            orphan_orders = [o["order_id"] for o in orders if str(o["account_id"]) not in account_ids]
            if orphan_orders:
                raise IngestionError(
                    f"orders reference unknown account_id(s): {', '.join(map(str, sorted(orphan_orders)))}"
                )
            orphan_tickets = [t["ticket_id"] for t in tickets if str(t["account_id"]) not in account_ids]
            if orphan_tickets:
                raise IngestionError(
                    f"tickets reference unknown account_id(s): {', '.join(map(str, sorted(orphan_tickets)))}"
                )

            conn.executemany(
                """INSERT INTO accounts (account_id, account_name, tier, primary_contact,
                                          good_standing, onboarded_at)
                   VALUES (:account_id, :account_name, :tier, :primary_contact,
                           COALESCE(:good_standing, 1), :onboarded_at)""",
                [_account_row(a) for a in accounts],
            )
            conn.executemany(
                """INSERT INTO orders (order_id, account_id, service_type, booked_at,
                                       scheduled_pickup_at, actual_pickup_at,
                                       promised_delivery_at, delivered_at, status,
                                       order_value_usd)
                   VALUES (:order_id, :account_id, :service_type, :booked_at,
                           :scheduled_pickup_at, :actual_pickup_at, :promised_delivery_at,
                           :delivered_at, :status, :order_value_usd)""",
                [_order_row(o) for o in orders],
            )
            conn.executemany(
                """INSERT INTO tickets (ticket_id, account_id, order_id, category, subject,
                                        description, priority, created_at, first_response_at,
                                        resolved_at, status, resolution_note)
                   VALUES (:ticket_id, :account_id, :order_id, :category, :subject,
                           :description, :priority, :created_at, :first_response_at,
                           :resolved_at, :status, :resolution_note)""",
                [_ticket_row(t) for t in tickets],
            )

            meta_rows = {
                "snapshot_utc": snapshot_utc,
                "source_file": xlsx_paths[0].name,
                "source_dir": str(source),
                "ingested_at": now,
                "dataset_version": readme.get("dataset_version", ""),
                "accounts_count": str(len(accounts)),
                "orders_count": str(len(orders)),
                "tickets_count": str(len(tickets)),
            }
            conn.executemany(
                "INSERT INTO dataset_meta(key, value) VALUES (?, ?)",
                sorted(meta_rows.items()),
            )

            # ---- documents ---------------------------------------------------
            doc_summaries = []
            for pdf_path in pdf_paths:
                parsed = parse_pdf(pdf_path)
                meta = derive_docmeta(pdf_path.name, parsed["page_texts"], accounts)
                if meta["assumed_current"]:
                    warnings.append(f"{pdf_path.name}: no explicit status found; assumed CURRENT")
                cur = conn.execute(
                    """INSERT INTO documents (doc_id, filename, title, version, status,
                                              doc_type, customer_scope, page_count,
                                              ingested_at, full_text)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        meta["doc_id"], meta["filename"], meta["title"], meta["version"],
                        meta["status"], meta["doc_type"], meta["customer_scope"],
                        len(parsed["page_texts"]), now, parsed["full_text"],
                    ),
                )
                if cur.rowcount != 1:
                    raise IngestionError(f"failed inserting document {meta['filename']}")
                conn.executemany(
                    """INSERT INTO document_sections (doc_id, seq, level, heading, text)
                       VALUES (?, ?, ?, ?, ?)""",
                    [
                        (meta["doc_id"], seq, s["level"], s["heading"], s["text"])
                        for seq, s in enumerate(parsed["sections"])
                    ],
                )
                doc_summaries.append(
                    f"{meta['filename']} -> id={meta['doc_id']} type={meta['doc_type']} "
                    f"status={meta['status']} scope={meta['customer_scope']} v{meta['version'] or '?'}"
                )
        vector_chunks = 0
        if include_vectors:
            from app.rag.vectorstore import rebuild as rebuild_vector_store

            vector_chunks = rebuild_vector_store(conn, resolve_path(get_settings().vector_store_dir))
        summary = {
            "db_path": str(db_path),
            "snapshot_utc": snapshot_utc,
            "accounts": len(accounts),
            "orders": len(orders),
            "tickets": len(tickets),
            "documents": len(pdf_paths),
            "vector_chunks": vector_chunks,
            "warnings": warnings,
            "documents_parsed": [s for s in doc_summaries],
        }
        return summary
    finally:
        conn.close()


def find_readme_sheet(wb):
    from app.ingestion.xlsxload import find_sheet

    return find_sheet(wb, "readme")


def _account_row(a: dict) -> dict:
    standing = a.get("good_standing")
    if isinstance(standing, str):
        standing = 0 if standing.strip().lower() in {"0", "false", "no"} else 1
    return {
        "account_id": str(a["account_id"]),
        "account_name": str(a.get("account_name") or a["account_id"]),
        "tier": a.get("tier"),
        "primary_contact": a.get("primary_contact"),
        "good_standing": 1 if standing is None else int(bool(int(standing))),
        "onboarded_at": a.get("onboarded_at"),
    }


def _order_row(o: dict) -> dict:
    value = o.get("order_value_usd")
    try:
        value = float(value) if value is not None else None
    except (TypeError, ValueError):
        value = None
    return {
        "order_id": str(o["order_id"]),
        "account_id": str(o["account_id"]),
        "service_type": o.get("service_type"),
        "booked_at": o.get("booked_at"),
        "scheduled_pickup_at": o.get("scheduled_pickup_at"),
        "actual_pickup_at": o.get("actual_pickup_at"),
        "promised_delivery_at": o.get("promised_delivery_at"),
        "delivered_at": o.get("delivered_at"),
        "status": o.get("status"),
        "order_value_usd": value,
    }


def _ticket_row(t: dict) -> dict:
    return {
        "ticket_id": str(t["ticket_id"]),
        "account_id": str(t["account_id"]),
        "order_id": t.get("order_id"),
        "category": t.get("category"),
        "subject": t.get("subject"),
        "description": t.get("description"),
        "priority": t.get("priority"),
        "created_at": t.get("created_at"),
        "first_response_at": t.get("first_response_at"),
        "resolved_at": t.get("resolved_at"),
        "status": t.get("status"),
        "resolution_note": t.get("resolution_note"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the ParcelPilot SQLite database from the data pack.")
    parser.add_argument("--source", default=None, help="folder containing PDFs + XLSX (default: DATA_PACK_DIR, repo-root-relative)")
    parser.add_argument("--db", default=None, help="output SQLite database path (default: SQLITE_DB_PATH, repo-root-relative)")
    parser.add_argument("--skip-vectors", action="store_true", help="skip rebuilding the Chroma vector index")
    args = parser.parse_args(argv)
    # Explicit CLI args resolve against the current directory; settings
    # defaults are documented as repo-root-relative and resolved that way.
    source = Path(args.source).resolve() if args.source else resolve_path(get_settings().data_pack_dir)
    db = Path(args.db).resolve() if args.db else resolve_path(get_settings().sqlite_db_path)
    try:
        summary = ingest(source, db, include_vectors=not args.skip_vectors)
    except IngestionError as exc:
        print(f"[ingest] FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[ingest] UNEXPECTED FAILURE: {exc}", file=sys.stderr)
        return 2
    print(f"[ingest] database rebuilt at {summary['db_path']}")
    print(f"[ingest] snapshot_utc = {summary['snapshot_utc']}")
    print(f"[ingest] accounts={summary['accounts']} orders={summary['orders']} "
          f"tickets={summary['tickets']} documents={summary['documents']} "
          f"vector_chunks={summary['vector_chunks']}")
    for doc_line in summary.get("documents_parsed", []):
        print(f"[ingest][doc] {doc_line}")
    for warning in summary["warnings"]:
        print(f"[ingest][warn] {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
