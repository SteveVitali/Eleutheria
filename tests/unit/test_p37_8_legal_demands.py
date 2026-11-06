# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.8 invariants for ``/about/legal-demands/`` (R11-GOV-03, ADR-166 /
A-4 = Q-E2-09 c, ADR-167, spec §44.3 SIG-SEC-003).

The page is T1 under ADR-155 (no ``<script>``, no island, no runtime
dependency), sits under the About namespace it is registered against in
``web/src/lib/page-types.ts``, renders the committed
``sig.legal-demand-counts/1`` snapshot record, and every drafted sentence
is a sha256-pinned ``LD-*`` row in
``docs/build/reports/copy-batches/batch-19.md`` pending verbatim
confirmation (B-2). These tests bind the surfaces: a ``data-copy`` id
without a batch row, a batch hash that stops verifying, a script element,
a posture sentence that drifts from the governance document of record,
or a corrections page that loses its legal-demand counts all fail loud.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "web/src/pages/about/legal-demands.astro"
LIB_PATH = REPO_ROOT / "web/src/lib/legal-demands.ts"
REGISTRY_PATH = REPO_ROOT / "web/src/lib/page-types.ts"
NAV_PATH = REPO_ROOT / "web/src/lib/nav.ts"
CORRECTIONS_PATH = REPO_ROOT / "web/src/pages/corrections.astro"
BATCH_PATH = REPO_ROOT / "docs/build/reports/copy-batches/batch-19.md"
DOC_PATH = REPO_ROOT / "docs/governance/legal-demand-posture.md"
ROUTE = "/about/legal-demands/"
VALID_STATUSES = {"pending", "confirmed"}


def _norm(text: str) -> str:
    """Collapse whitespace runs and unfold ``{" "}`` JSX space literals —
    markup line-wrapping and tag boundaries are not copy."""
    text = re.sub(r'\{"\s*"\}', " ", text)
    return " ".join(text.split())


def _template(source: str) -> str:
    """The emitted markup region — everything after the frontmatter fence."""
    parts = source.split("---", 2)
    return parts[2] if len(parts) == 3 else source


def _batch_rows() -> dict[str, dict[str, str]]:
    """id → {page, text, sha256, status} for every batch-19 row."""
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5:
            continue
        rid, page, text, sha, status = cells
        if rid in ("id", "—") or set(rid) <= {"-", ":"}:
            continue
        rows[rid] = {"page": page, "text": text, "sha256": sha, "status": status}
    return rows


class _CopyParser(HTMLParser):
    """Collect ``data-copy`` elements' static ids + text (the shared
    convention — markup contributes no copy)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.elements: list[tuple[list[str], str]] = []
        self._buffers: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        copy_attr = attr.get("data-copy")
        self.stack.append((tag, copy_attr))
        if copy_attr is not None:
            self._buffers.append([])

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pass

    def handle_endtag(self, tag: str) -> None:
        while self.stack:
            popped_tag, copy_attr = self.stack.pop()
            if copy_attr is not None:
                text = _norm("".join(self._buffers.pop()))
                if copy_attr.lstrip("{").rstrip("}") != copy_attr:
                    continue  # dynamic binding — the page has none
                self.elements.append((copy_attr.split(), text))
            if popped_tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if data.strip() and self._buffers:
            self._buffers[-1].append(data)


def _elements(path: Path) -> list[tuple[list[str], str]]:
    parser = _CopyParser()
    parser.feed(_template(path.read_text(encoding="utf-8")))
    parser.close()
    return parser.elements


def test_batch_rows_are_well_formed_and_hashes_verify() -> None:
    rows = _batch_rows()
    assert rows, "batch-19 carries no rows"
    for rid, row in rows.items():
        assert rid.startswith("LD-"), f"{rid}: wrong id prefix for batch-19"
        assert row["page"] in {ROUTE, "/corrections/"}, (
            f"{rid}: bound to {row['page']!r}"
        )
        assert row["status"] in VALID_STATUSES, f"{rid}: unknown status {row['status']!r}"
        assert row["sha256"] == hashlib.sha256(row["text"].encode("utf-8")).hexdigest(), (
            f"{rid}: sha256 does not verify the recorded text"
        )


def test_every_data_copy_element_renders_its_rows() -> None:
    rows = _batch_rows()
    page_elements = _elements(PAGE_PATH)
    corrections_elements = _elements(CORRECTIONS_PATH)
    carried: set[str] = set()
    for ids, rendered in page_elements + corrections_elements:
        actual = _norm(rendered)
        for rid in ids:
            if not rid.startswith("LD-"):
                continue
            assert rid in rows, f"data-copy names {rid}, which has no batch-19 row"
            assert _norm(rows[rid]["text"]) in actual, (
                f"{ids}: {actual!r} does not carry {rid}'s pinned text"
            )
            carried.add(rid)
    orphans = set(rows) - carried
    assert not orphans, f"batch-19 rows bound to no element: {sorted(orphans)}"


def test_page_is_t1_zero_js() -> None:
    # the emitted markup region — frontmatter comments may name the rule
    src = _template(PAGE_PATH.read_text(encoding="utf-8"))
    assert "<script" not in src
    assert "client:" not in src
    assert " on:" not in src and " on*" not in src
    assert "javascript:" not in src
    assert f'path="{ROUTE}"' in PAGE_PATH.read_text(encoding="utf-8")
    # one h1 — emitted by BaseLayout from the page title
    assert src.count("<h1") == 0, "the page must not emit its own h1"


def test_page_renders_the_counts_record_with_its_as_of() -> None:
    """The acceptance shape is structural: the counts render from the
    committed `sig.legal-demand-counts/1` snapshot with an as-of date —
    counts only, never a requester identity or case detail field."""
    src = PAGE_PATH.read_text(encoding="utf-8")
    assert "latestCounts" in src
    for field in ("counts.received", "counts.complied_with", "counts.refused", "counts.as_of"):
        assert field in src, f"{field} missing from the counts block"
    assert 'data-testid="legal-demand-counts"' in src
    assert 'data-testid="counts-as-of"' in src
    assert "fmtInt" in src  # K14 §3.6 grouping


def test_route_is_registered_and_nav_item_declared() -> None:
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    assert f'patterns: ["{ROUTE}"]' in registry
    assert 'contract: "sig.legal-demand-counts/1"' in registry
    assert 'owner: "P37.8"' in registry
    nav = NAV_PATH.read_text(encoding="utf-8")
    assert 'route: "about/legal-demands/"' in nav


def test_counts_record_keeps_the_append_only_counts_only_shape() -> None:
    """The committed record is `sig.legal-demand-counts/1` snapshots —
    append-only (a new snapshot per change), non-negative integers, and
    no requester-identity or case-detail field by construction."""
    src = LIB_PATH.read_text(encoding="utf-8")
    assert 'LEGAL_DEMAND_COUNTS_SCHEMA = "sig.legal-demand-counts/1"' in src
    assert 'LEGAL_DEMAND_POSTURE_SCHEMA = "sig.legal-demand-posture/1"' in src
    # the counts interface has no requester/case field — counts only
    counts_iface = re.search(
        r"export interface LegalDemandCounts \{(.*?)\}", src, re.S
    )
    assert counts_iface
    body = counts_iface.group(1)
    for forbidden in ("requester", "case", "identity", "detail"):
        assert forbidden not in body, f"counts interface carries {forbidden!r}"
    # the canary can only ever read "declined" on the posture record
    assert 'canary: "declined"' in src
    assert "counsel_reviewed: false" in src


def test_posture_sentences_match_the_governance_document() -> None:
    """The posture document of record carries the pinned posture
    sentences verbatim — page and document can never drift apart."""
    doc = _norm(DOC_PATH.read_text(encoding="utf-8"))
    rows = _batch_rows()
    # every pinned posture sentence appears verbatim in the doc — LD-01 is
    # page framing ("This page is…") and LD-08 the empty-state, neither is
    # posture text
    for rid, row in rows.items():
        if row["page"] != ROUTE or rid in {"LD-01", "LD-08"}:
            continue
        assert _norm(row["text"]) in doc, f"{rid}: posture sentence absent from the document"


def test_corrections_page_carries_the_counts_with_its_as_of() -> None:
    """Design E2-10 verbatim: `/corrections/` gains legal-demand counts
    (received, complied, refused) with an as-of date — the same record the
    legal-demands page renders, so the surfaces can never disagree."""
    src = CORRECTIONS_PATH.read_text(encoding="utf-8")
    assert "latestCounts" in src
    assert 'data-testid="legal-demand-counts"' in src
    assert "legalDemands.as_of" in src
    assert "legalDemands.received" in src
    assert "legalDemands.complied_with" in src
    assert "legalDemands.refused" in src
    assert 'data-copy="LD-10"' in src
