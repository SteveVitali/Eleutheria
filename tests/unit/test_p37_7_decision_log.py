# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.7 invariants for ``/about/editorial-decisions/`` (R11-GOV-02, ADR-164 /
WV-02, spec §46.2 compensating controls).

The page is T1 under ADR-155 (no ``<script>``, no island, no runtime
dependency), sits under the About namespace it is registered against in
``web/src/lib/page-types.ts``, renders the committed
``sig.editorial-decision/1`` log, and every drafted sentence is a
sha256-pinned ``DL-*`` row in
``docs/build/reports/copy-batches/batch-18.md`` pending verbatim
confirmation (B-2). These tests bind the two sides: a ``data-copy`` id
without a batch row, a batch hash that stops verifying, a script element,
or a page that stops rendering each entry's GATE DECISIONS citation fails
loud.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "web/src/pages/about/editorial-decisions.astro"
LIB_PATH = REPO_ROOT / "web/src/lib/editorial-decisions.ts"
REGISTRY_PATH = REPO_ROOT / "web/src/lib/page-types.ts"
NAV_PATH = REPO_ROOT / "web/src/lib/nav.ts"
BATCH_PATH = REPO_ROOT / "docs/build/reports/copy-batches/batch-18.md"
ROUTE = "/about/editorial-decisions/"
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
    """id → {text, sha256, status} for every batch-18 row."""
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


def _elements() -> list[tuple[list[str], str]]:
    parser = _CopyParser()
    parser.feed(_template(PAGE_PATH.read_text(encoding="utf-8")))
    parser.close()
    return parser.elements


def test_batch_rows_are_well_formed_and_hashes_verify() -> None:
    rows = _batch_rows()
    assert rows, "batch-18 carries no rows"
    for rid, row in rows.items():
        assert rid.startswith("DL-"), f"{rid}: wrong id prefix for batch-18"
        assert row["page"] == ROUTE, f"{rid}: bound to {row['page']!r}, not {ROUTE}"
        assert row["status"] in VALID_STATUSES, f"{rid}: unknown status {row['status']!r}"
        assert row["sha256"] == hashlib.sha256(row["text"].encode("utf-8")).hexdigest(), (
            f"{rid}: sha256 does not verify the recorded text"
        )


def test_every_data_copy_element_renders_its_rows() -> None:
    rows = _batch_rows()
    elements = _elements()
    assert elements, "the page carries no data-copy elements"
    carried: set[str] = set()
    for ids, rendered in elements:
        actual = _norm(rendered)
        for rid in ids:
            assert rid in rows, f"data-copy names {rid}, which has no batch-18 row"
            assert _norm(rows[rid]["text"]) in actual, (
                f"{ids}: {actual!r} does not carry {rid}'s pinned text"
            )
            carried.add(rid)
    orphans = set(rows) - carried
    assert not orphans, f"batch-18 rows bound to no element: {sorted(orphans)}"


def test_page_is_t1_zero_js() -> None:
    # the emitted markup region — frontmatter comments may name the rule
    src = _template(PAGE_PATH.read_text(encoding="utf-8"))
    assert "<script" not in src
    assert "client:" not in src
    assert " on:" not in src and " on*" not in src
    assert "javascript:" not in src
    assert 'path="/about/editorial-decisions/"' in PAGE_PATH.read_text(encoding="utf-8")
    # one h1 — emitted by BaseLayout from the page title
    assert src.count("<h1") == 0, "the page must not emit its own h1"


def test_page_renders_every_entry_with_its_gate_citation() -> None:
    """The acceptance shape is structural: each entry renders the decision,
    the class label, and the GATE DECISIONS citation (`e.gate_ref`) — the
    template can never drop the citation field."""
    src = PAGE_PATH.read_text(encoding="utf-8")
    assert "orderedDecisions" in src
    assert "e.gate_ref.row" in src
    assert "e.gate_ref.recorded_at" in src
    assert "e.evidence" in src
    assert "DECISION_CLASS_LABELS" in src
    assert 'data-testid="editorial-decision"' in src
    assert 'data-testid="decision-gate-ref"' in src
    assert "e.decision_id" in src


def test_route_is_registered_and_nav_item_declared() -> None:
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    assert f'patterns: ["{ROUTE}"]' in registry
    assert 'contract: "sig.editorial-decision/1"' in registry
    assert 'owner: "P37.7"' in registry
    nav = NAV_PATH.read_text(encoding="utf-8")
    assert 'route: "about/editorial-decisions/"' in nav


def test_log_record_keeps_the_append_only_shape() -> None:
    """Every committed entry is a ``sig.editorial-decision/1`` object that
    names its class, dates and citation — the source module itself holds
    the contract (the vitest suite asserts the record's invariants)."""
    src = LIB_PATH.read_text(encoding="utf-8")
    assert 'EDITORIAL_DECISION_SCHEMA = "sig.editorial-decision/1"' in src
    for cls in ("authority", "sensitivity_classification", "naming", "contested_claim", "deletion", "purge"):
        assert f'"{cls}"' in src, f"class {cls} missing from the vocabulary"
    # every entry carries a gate_ref literal — the citation field
    assert src.count("gate_ref: {") == src.count("decision_id: "), (
        "an entry without its GATE DECISIONS citation"
    )
    # tombstone classes carry the never-content rule in the contract
    assert "never its content" in src or "never content" in src
