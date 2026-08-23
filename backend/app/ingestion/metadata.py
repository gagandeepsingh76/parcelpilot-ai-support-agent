"""Derive document metadata from filename + embedded content.

Contract (documented in data_pack/README.md):
- doc_type:  SOP -> sop | Policy -> policy | Guide -> product-guide |
             Agreement -> agreement  (filename first, then title line)
- version:   '_v3' in filename, else 'Version: 3' in content, else None
- status:    CURRENT/DEPRECATED from filename or content; defaults to CURRENT
             (with an 'assumed_current' flag so the runner can warn)
- customer_scope:
             'global' unless a scope token (northstar/lumenworks) appears in
             the filename AND matches an account_name in the workbook - then
             that account_id. Unmatched tokens stay as the token string so the
             retrieval layer can still prefer them by name.

doc_id comes from the leading number in the filename ('05_...' -> '05'),
falling back to a slug of the stem.
"""

from __future__ import annotations

import re
from pathlib import PurePath

DOC_TYPE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sop", ("SOP",)),
    ("product-guide", ("GUIDE",)),
    ("agreement", ("AGREEMENT",)),
    ("policy", ("POLICY",)),
)

SCOPE_TOKENS = {
    "northstar": "northstar",
    "lumenworks": "lumenworks",
}

_FILENAME_VERSION_RE = re.compile(r"_v(\d+)(?=$|[^0-9])", re.IGNORECASE)
_CONTENT_VERSION_RE = re.compile(r"\bVersion\s*[:\-]\s*v?(\d+)\b", re.IGNORECASE)
_FILENAME_STATUS_RE = re.compile(r"_(CURRENT|DEPRECATED)\b", re.IGNORECASE)
_CONTENT_STATUS_RE = re.compile(r"\bStatus\s*[:\-]\s*(CURRENT|DEPRECATED)\b", re.IGNORECASE)


def _doc_type_from_text(text: str) -> str | None:
    upper = text.upper()
    for doc_type, tokens in DOC_TYPE_RULES:
        if any(token in upper for token in tokens):
            return doc_type
    return None


def _title_from_content(page_texts: list[str], fallback: str) -> str:
    if page_texts:
        for line in page_texts[0].splitlines():
            candidate = line.strip()
            if not candidate or candidate.startswith("["):
                continue
            # first substantial line of page one is treated as the title
            if 4 <= len(candidate) <= 90 and not candidate.endswith("."):
                return candidate
            break
    words = re.sub(r"[_\-]+", " ", fallback).split()
    titled = " ".join(w.capitalize() if len(w) > 3 else w.upper() for w in words)
    return titled


def derive_docmeta(filename: str, page_texts: list[str], accounts: list[dict]) -> dict:
    stem = PurePath(filename).stem
    stem_lower = stem.lower()
    first_page = page_texts[0] if page_texts else ""
    combined_head = "\n".join([first_page] + ([page_texts[1][:400]] if len(page_texts) > 1 else []))

    doc_type = None
    stem_upper = stem.upper()
    for token, mapped in (
        ("SOP", "sop"),
        ("POLICY", "policy"),
        ("GUIDE", "product-guide"),
        ("AGREEMENT", "agreement"),
    ):
        if token in stem_upper:
            doc_type = mapped
            break
    if doc_type is None:
        doc_type = _doc_type_from_text(_title_from_content(page_texts, stem))
    if doc_type is None:
        raise ValueError(
            f"cannot infer doc_type for '{filename}': no SOP/POLICY/GUIDE/AGREEMENT "
            "token in filename or title"
        )

    version_match = _FILENAME_VERSION_RE.search(stem) or _CONTENT_VERSION_RE.search(combined_head)
    version = version_match.group(1) if version_match else None

    status_match = _FILENAME_STATUS_RE.search(stem.upper()) or _CONTENT_STATUS_RE.search(combined_head)
    status = status_match.group(1).upper() if status_match else None
    assumed_current = status is None
    status = status or "CURRENT"

    customer_scope = "global"
    for key, token in SCOPE_TOKENS.items():
        if key in stem_lower:
            for account in accounts:
                name = str(account.get("account_name") or "").lower()
                if key in name.replace(" ", ""):
                    customer_scope = str(account["account_id"])
                    break
            else:
                customer_scope = token
            break

    id_match = re.match(r"^(\d+)", stem)
    doc_id = id_match.group(1) if id_match else re.sub(r"[^a-z0-9]+", "-", stem_lower).strip("-")

    return {
        "doc_id": doc_id,
        "filename": filename,
        "title": _title_from_content(page_texts, stem),
        "version": version,
        "status": status,
        "doc_type": doc_type,
        "customer_scope": customer_scope,
        "assumed_current": assumed_current,
    }
