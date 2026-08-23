"""Tool 1 - document search over the authoritative index.

search_documents() is the ONLY retrieval entry point used by the agent:
- filters to CURRENT docs by default (DEPRECATED only via explicit opt-in);
- scopes results to the caller's agreement + global sources;
- reranks by similarity *plus* source authority;
- returns structured citations and explicit conflict descriptors.
Historical ticket text is deliberately NOT in this index (see Step 9).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.rag.authority import combined_score, detect_conflicts
from app.rag.vectorstore import get_collection

FETCH_MULTIPLIER = 4


def _where_filter(account_id: str | None, include_deprecated: bool) -> dict[str, Any] | None:
    clauses: list[dict[str, Any]] = []
    if not include_deprecated:
        clauses.append({"status": {"$eq": "CURRENT"}})
    if account_id:
        clauses.append({"customer_scope": {"$in": ["global", account_id]}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search_documents(
    query: str,
    *,
    account_id: str | None = None,
    include_deprecated: bool = False,
    k: int = 5,
    store_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Semantic search with authority-aware reranking.

    account_id scopes retrieval to the caller's own agreement + global docs.
    """
    settings = get_settings()
    store = store_dir or settings.vector_store_dir_resolved
    collection = get_collection(store)

    fetch_k = max(k * FETCH_MULTIPLIER, 12)
    raw = collection.query(
        query_texts=[query],
        n_results=min(fetch_k, max(collection.count(), 1)),
        where=_where_filter(account_id, include_deprecated),
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict[str, Any]] = []
    documents = raw.get("documents") or [[]]
    metadatas = raw.get("metadatas") or [[]]
    distances = raw.get("distances") or [[]]
    for text, metadata, distance in zip(documents[0], metadatas[0], distances[0]):
        similarity = max(0.0, 1.0 - float(distance))  # cosine distance -> similarity
        meta_dict = dict(metadata) if metadata else {}
        hits.append(
            {
                "text": text,
                "metadata": meta_dict,
                "similarity": round(similarity, 4),
                "score": round(combined_score(similarity, meta_dict, account_id), 4),
            }
        )

    # diversify: keep the best chunk per document before cutting to k
    best_per_doc: dict[str, dict[str, Any]] = {}
    for hit in sorted(hits, key=lambda h: h["score"], reverse=True):
        doc_key = hit["metadata"].get("doc_id", hit["text"][:32])
        if doc_key not in best_per_doc:
            best_per_doc[doc_key] = hit
    ranked = list(best_per_doc.values())[:k]

    return {
        "query": query,
        "account_scoping": account_id or "unscoped (internal use)",
        "deprecated_included": bool(include_deprecated),
        "results": [
            {
                "citation": {
                    "doc_id": h["metadata"].get("doc_id"),
                    "title": h["metadata"].get("title"),
                    "section": h["metadata"].get("heading"),
                    "status": h["metadata"].get("status"),
                    "doc_type": h["metadata"].get("doc_type"),
                    "customer_scope": h["metadata"].get("customer_scope"),
                    "version": h["metadata"].get("version"),
                },
                "text": h["text"],
                "similarity": h["similarity"],
                "authority_score": h["score"],
            }
            for h in ranked
        ],
        "conflicts": detect_conflicts(ranked, account_id),
    }


def assert_index_ready(conn: sqlite3.Connection) -> None:
    from app.rag.vectorstore import is_populated

    if not is_populated(get_settings().vector_store_dir_resolved):
        raise RuntimeError(
            "vector index empty/missing - run ingestion first: python -m app.ingestion.run"
        )


__all__ = ["search_documents", "assert_index_ready"]
