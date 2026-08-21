"""Chroma persistent-collection wrapper for the authoritative document index.

The collection is rebuilt from scratch whenever ingestion runs; the corpus is
small so rebuild cost is negligible and staleness impossible.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import chromadb

from app.rag.chunking import build_chunks

COLLECTION_NAME = "parcelpilot_docs"


class VectorStoreError(RuntimeError):
    pass


def get_collection(store_dir: str | Path):
    try:
        client = chromadb.PersistentClient(path=str(store_dir))
    except Exception as exc:  # noqa: BLE001 - chroma raises varied types
        raise VectorStoreError(f"cannot open vector store at '{store_dir}': {exc}") from exc
    return client.get_or_create_collection(COLLECTION_NAME)


def rebuild(conn: sqlite3.Connection, store_dir: str | Path) -> int:
    """Drop and repopulate the collection from SQLite. Returns chunk count."""
    client = chromadb.PersistentClient(path=str(store_dir))
    existing = {c.name for c in client.list_collections()}
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    chunks = build_chunks(conn)
    if not chunks:
        raise VectorStoreError("no chunks produced - run document ingestion first")
    collection.add(
        ids=[c["chunk_id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    return len(chunks)


def is_populated(store_dir: str | Path) -> bool:
    try:
        return get_collection(store_dir).count() > 0
    except VectorStoreError:
        return False
