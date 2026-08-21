"""PDF text extraction + structural section splitting via pypdf.

Section detection is heuristic but deterministic:
- numbered headings like '3.' or '3.2 Heading' become level = dot-depth;
- short ALL-CAPS lines become level-1 headings;
- everything before the first heading lands in a '(Front matter)' bucket.
"""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

_NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(\S.{0,88})$")
_CAPS_HEADING_MAX = 90


class PdfParseError(RuntimeError):
    pass


def extract_page_texts(path: str | Path) -> list[str]:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        raise PdfParseError(f"failed to open PDF '{path}': {exc}") from exc
    texts = []
    for i, page in enumerate(reader.pages):
        try:
            texts.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            raise PdfParseError(f"failed to extract page {i + 1} of '{path}': {exc}") from exc
    if not texts:
        raise PdfParseError(f"'{path}' contains no pages")
    return texts


def split_sections(full_text: str) -> list[dict]:
    sections: list[dict] = []
    current_heading = "(Front matter)"
    current_level = 0
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        sections.append({"heading": current_heading, "level": current_level, "text": body})

    for line in full_text.splitlines():
        stripped = line.strip()
        numbered = _NUMBERED_HEADING_RE.match(stripped)
        caps = (
            stripped.isupper()
            and 4 <= len(stripped) <= _CAPS_HEADING_MAX
            and not stripped.endswith(".")
        )
        if numbered:
            if buf:
                flush()
            level = min(numbered.group(1).count(".") + 1, 3)
            heading = stripped.rstrip(".")
            current_heading, current_level, buf = heading, level, []
            continue
        if caps:
            if buf:
                flush()
            current_heading, current_level, buf = stripped.title(), 1, []
            continue
        buf.append(line)
    if buf:
        flush()
    # drop empty front matter produced by header-only documents
    return [s for s in sections if s["text"] or s["heading"] != "(Front matter)"]


def parse_pdf(path: str | Path) -> dict:
    """Return {page_texts, full_text, sections} for a PDF file."""
    page_texts = extract_page_texts(path)
    full_text = "\n\n".join(page_texts)
    return {
        "page_texts": page_texts,
        "full_text": full_text,
        "sections": split_sections(full_text),
    }
