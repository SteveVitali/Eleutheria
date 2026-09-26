# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Text and link extraction over captured document bytes (P25.5, §24 layers 2–3).

The connector document adapters (resource indexes, disclosure index pages,
pathway documents, feeds) need two deterministic engines over **already-captured
bytes** — they run post-capture, network-isolated, and are pure functions of the
stored capture (SIG-INGEST-002):

* :func:`html_text` / :func:`html_links` — the layer-2 (``selector_template``)
  helpers: visible text and ``<a href>`` link discovery from captured HTML,
  stdlib-only.
* :func:`pdf_text_pages` — the layer-3 (``pdf_text``) engine: per-page text of a
  digital-native PDF via ``pypdf``. It is **fail-closed**: a malformed,
  non-PDF, encrypted, or image-only byte string yields no text — never a
  partial or fabricated page — so a connector can distinguish "document with no
  text layer" (an evidence artifact + a human-review outcome) from "document
  with text" deterministically.

Locators come from :mod:`parsing.locator` (SIG-PARSE-003): a PDF-derived claim
carries a ``page`` locator; an HTML/CSV/feed-derived claim carries a
``byte_range`` / ``row`` locator into the capture bytes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from .locator import Locator

__all__ = [
    "DocumentLink",
    "byte_range_locator",
    "html_links",
    "html_script_srcs",
    "html_text",
    "page_locator_for",
    "pdf_text_pages",
    "utf8_text",
]


# --- helpers ------------------------------------------------------------------


def utf8_text(data: bytes) -> str:
    """Decode captured bytes as UTF-8 text (lossy on stray bytes — never raises)."""
    return data.decode("utf-8", errors="replace")


def byte_range_locator(data: bytes, needle: str) -> dict[str, Any] | None:
    """A ``byte_range`` locator for ``needle`` inside the captured bytes (SIG-PARSE-003).

    The literal is searched case-sensitively first, then case-insensitively over
    the UTF-8 view. ``None`` when the literal is not in the capture — a caller
    that cannot locate its evidence does not emit the claim (OL-24-18).
    """
    encoded = needle.encode("utf-8")
    idx = data.find(encoded)
    if idx < 0:
        # Case-insensitive over the raw bytes (safe: offsets are byte-stable).
        folded = needle.lower().encode("utf-8")
        idx = data.lower().find(folded)
        encoded = folded
    if idx < 0:
        return None
    return Locator.byte_range(idx, idx + len(encoded)).to_row()


def page_locator_for(pages: tuple[str, ...], needle: str) -> dict[str, Any] | None:
    """A 1-based ``page`` locator for the page carrying ``needle`` (SIG-PARSE-003)."""
    folded = needle.lower()
    for i, page_text in enumerate(pages, start=1):
        if folded in page_text.lower():
            return Locator.page(i).to_row()
    return None


# --- layer 2: captured HTML ----------------------------------------------------


_SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "template"})


class _TextParser(HTMLParser):
    """Collect visible text; skip script/style/svg payloads (stdlib, deterministic)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_text(data: bytes) -> str:
    """The visible text of a captured HTML document, whitespace-normalized.

    Deterministic and stdlib-only: the bytes are decoded UTF-8 (lossy), markup
    noise (script/style/noscript/svg/template) is dropped, and runs of
    whitespace collapse to single spaces. Returns ``""`` when the capture has no
    text — never raises.
    """
    parser = _TextParser()
    try:
        parser.feed(utf8_text(data))
    except Exception:  # HTMLParser is forgiving; a truncated doc still yields its text
        pass
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


@dataclass(frozen=True)
class DocumentLink:
    """One ``<a href>`` discovered in a captured index page (document order)."""

    url: str
    anchor: str
    ordinal: int


class _LinkParser(HTMLParser):
    """Collect ``<a href>`` targets + their anchor text, in document order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._anchor: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._anchor = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, re.sub(r"\s+", " ", "".join(self._anchor)).strip()))
            self._href = None
            self._anchor = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._anchor.append(data)


def html_links(data: bytes, base_url: str) -> tuple[DocumentLink, ...]:
    """Every ``<a href>`` in the capture, resolved against ``base_url``.

    Absolute/relative hrefs are resolved with :func:`urllib.parse.urljoin`;
    ``javascript:``/``mailto:``/bare-fragment and schemeless hrefs are dropped;
    duplicates collapse to their first occurrence (document order preserved).
    """
    parser = _LinkParser()
    try:
        parser.feed(utf8_text(data))
    except Exception:
        pass
    seen: set[str] = set()
    out: list[DocumentLink] = []
    for href, anchor in parser.links:
        if href.strip().startswith("#"):
            continue  # a bare-fragment href points at the index page itself
        resolved = urljoin(base_url, href.strip())
        if not resolved.startswith(("http://", "https://")) or resolved in seen:
            continue
        seen.add(resolved)
        out.append(DocumentLink(url=resolved, anchor=anchor, ordinal=len(out)))
    return tuple(out)


class _ScriptSrcParser(HTMLParser):
    """Collect ``<script src>`` values, in document order (stdlib, deterministic)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        src = dict(attrs).get("src")
        if src:
            self.srcs.append(src)


def html_script_srcs(data: bytes, base_url: str) -> tuple[str, ...]:
    """Every ``<script src>`` in the capture, resolved against ``base_url``.

    A client-rendered page (a Next.js interactive, a data-driven map) often
    carries its dataset inside a referenced script chunk — the ``<script src>``
    list is the discovery surface a connector follows to the embedded data.
    Absolute/relative srcs resolve with :func:`urllib.parse.urljoin`;
    schemeless and non-HTTP(S) srcs are dropped; duplicates collapse to their
    first occurrence (document order preserved). Deterministic, stdlib-only.
    """
    parser = _ScriptSrcParser()
    try:
        parser.feed(utf8_text(data))
    except Exception:
        pass
    seen: set[str] = set()
    out: list[str] = []
    for src in parser.srcs:
        resolved = urljoin(base_url, src.strip())
        if not resolved.startswith(("http://", "https://")) or resolved in seen:
            continue
        seen.add(resolved)
        out.append(resolved)
    return tuple(out)


# --- layer 3: digital-native PDF text -------------------------------------------


def pdf_text_pages(data: bytes) -> tuple[str, ...]:
    """Per-page text of a captured PDF — the ``pdf_text`` layer-3 engine (§24.1).

    Fail-closed by construction: anything that is not a parseable, unencrypted,
    text-bearing PDF — malformed bytes, an HTML error page saved with a ``.pdf``
    name, an encrypted file, a scanned/image-only PDF — yields ``()``, so the
    caller distinguishes "no text layer" (an evidence artifact + a recorded
    human-review outcome, never a fabricated extraction) from "text present".
    """
    if not data.lstrip().startswith(b"%PDF"):
        return ()
    import io

    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - pypdf is a declared dependency
        return ()
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
    except Exception:
        return ()
    try:
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return ()
            if reader.is_encrypted:
                return ()
        pages: list[str] = []
        for page in reader.pages:
            try:
                pages.append((page.extract_text() or "").strip())
            except Exception:
                pages.append("")
        return tuple(pages)
    except Exception:
        return ()
