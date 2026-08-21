"""Source-authority ranking and conflict detection.

Authority tiers (higher wins when similarity is comparable):
  4 - the requester's own signed agreement (customer_scope == account_id)
  3 - SOP / product guide (operational truth)
  2 - CURRENT general policy
  1 - DEPRECATED policy (only surfaces if nothing current matches, or the
      query explicitly asks about historical policy)

Conflicts are surfaced, never silently resolved: when top results for one
topic span different authority tiers with materially different guidance
(e.g. an enterprise agreement vs the generic policy, or CURRENT vs
DEPRECATED numbers) the retrieval result carries a `conflicts` list so the
agent can state both positions and which one governs.
"""

from __future__ import annotations

from typing import Any

# similarity weight vs authority weight in final ranking
SIMILARITY_WEIGHT = 0.7
AUTHORITY_WEIGHT = 0.3


def tier_of(metadata: dict[str, Any], account_id: str | None) -> int:
    doc_type = metadata.get("doc_type", "")
    status = metadata.get("status", "CURRENT")
    scope = metadata.get("customer_scope", "global")

    if status == "DEPRECATED":
        return 1
    if doc_type == "agreement" and account_id and scope == account_id:
        return 4
    if doc_type in ("sop", "product-guide"):
        return 3
    return 2  # CURRENT global policy / agreement of a different customer


def combined_score(similarity: float, metadata: dict[str, Any], account_id: str | None) -> float:
    """similarity: cosine similarity in [0, 1] as returned by chroma distance conversion."""
    tier = tier_of(metadata, account_id)
    normalized_tier = (tier - 1) / 3.0
    return SIMILARITY_WEIGHT * max(0.0, min(1.0, similarity)) + AUTHORITY_WEIGHT * normalized_tier


def detect_conflicts(
    results: list[dict[str, Any]], account_id: str | None
) -> list[dict[str, Any]]:
    """Return conflict descriptors for mixed-authority results on one topic."""
    conflicts: list[dict[str, Any]] = []
    scoped = [r for r in results if r["metadata"].get("customer_scope") == account_id]
    globals_ = [r for r in results if r["metadata"].get("customer_scope") == "global"]

    # customer agreement vs general policy on the same topic
    if scoped and globals_:
        conflicts.append(
            {
                "kind": "agreement_vs_general_policy",
                "governs": "the customer's signed agreement takes precedence",
                "sources": [
                    _source_ref(r) for r in (scoped + globals_)[:3]
                ],
            }
        )

    statuses = {r["metadata"].get("status") for r in results}
    if "CURRENT" in statuses and "DEPRECATED" in statuses:
        conflicts.append(
            {
                "kind": "current_vs_deprecated",
                "governs": "the CURRENT document supersedes the DEPRECATED one",
                "sources": [_source_ref(r) for r in results[:3]],
            }
        )
    return conflicts


def _source_ref(result: dict[str, Any]) -> dict[str, str]:
    md = result["metadata"]
    return {
        "doc_id": md.get("doc_id", ""),
        "title": md.get("title", ""),
        "heading": md.get("heading", ""),
        "status": md.get("status", ""),
        "doc_type": md.get("doc_type", ""),
        "customer_scope": md.get("customer_scope", ""),
        "filename": md.get("filename", ""),
    }
