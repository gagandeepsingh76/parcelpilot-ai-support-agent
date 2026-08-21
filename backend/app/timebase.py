"""Single source of truth for 'now'.

Every time-based calculation uses the dataset snapshot timestamp declared in
the workbook's README sheet (cached into dataset_meta at ingestion).
SNAPSHOT_TIME_OVERRIDE (settings.snapshot_time_override) exists purely for
deterministic tests.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.config import get_settings


def parse_iso_utc(value: str) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_snapshot_time(conn: sqlite3.Connection) -> datetime:
    override = get_settings().snapshot_time_override
    if override:
        return parse_iso_utc(override)

    row = conn.execute(
        "SELECT value FROM dataset_meta WHERE key = 'snapshot_utc'"
    ).fetchone()
    if row is None:
        raise LookupError(
            "dataset_meta.snapshot_utc missing - run ingestion "
            "(python -m app.ingestion.run) before using time-based logic"
        )
    return parse_iso_utc(row["value"])


def now_utc() -> datetime:
    """The effective 'now' for calculations that have no connection handy."""
    override = get_settings().snapshot_time_override
    if override:
        return parse_iso_utc(override)
    raise LookupError("no snapshot time available - pass a connection or set SNAPSHOT_TIME_OVERRIDE")
