"""Chunking: SQLite documents/sections -> embeddable chunks with metadata.

One chunk per section (sections are short policy clauses), heading and doc
title prepended so embeddings carry context. Long sections are split on
sentence boundaries with overlap so no chunk exceeds max_chars.
"""

from __future__ import annotations

import re
import sqlite3

MAX_CHARS = 1200
OVERLAP_CHARS = 150


def _split_long(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail} {sentence}".strip()
        else:
            current = f"{current} {sentence}".strip() if current else sentence
    if current:
        chunks.append(current)
    return chunks


def build_chunks(conn: sqlite3.Connection) -> list[dict]:
    docs = {
        row["doc_id"]: dict(row)
        for row in conn.execute(
            "SELECT doc_id, filename, title, version, status, doc_type, customer_scope FROM documents"
        )
    }
    chunks: list[dict] = []
    for section in conn.execute(
        "SELECT doc_id, seq, level, heading, text FROM document_sections ORDER BY doc_id, seq"
    ):
        doc = docs[section["doc_id"]]
        prefix = f"{doc['title']} - {section['heading']}: " if section["heading"] else f"{doc['title']}: "
        body = section["text"] or ""
        for part_index, part in enumerate(_split_long(body)):
            chunk_id = f"{section['doc_id']}:{section['seq']}" + (
                f":{part_index}" if part_index else ""
            )
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": (prefix + part)[: MAX_CHARS * 2],
                    "metadata": {
                        "doc_id": doc["doc_id"],
                        "filename": doc["filename"],
                        "title": doc["title"],
                        "version": doc["version"] or "",
                        "status": doc["status"],
                        "doc_type": doc["doc_type"],
                        "customer_scope": doc["customer_scope"],
                        "heading": section["heading"] or "(front matter)",
                        "seq": int(section["seq"]),
                    },
                }
            )
    return chunks
