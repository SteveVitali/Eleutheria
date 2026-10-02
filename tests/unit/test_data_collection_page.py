# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.38a invariants for ``/data-collection/`` and copy batch #1.

The page is T0 under ADR-155 (no ``<script>``, no island, no runtime
dependency), names the owned contact URL exactly once, points at the dispute
channel as the opt-out route (Q-29), and every one of its sentences is a
sha256-pinned row in ``docs/build/reports/copy-batches/batch-01.md`` that ships
only in its operator-confirmed form (B-2). These tests bind the two sides:
they fail if a sentence drifts from its batch row, ships untracked, or a hash
stops verifying — and if the page ever carries a script, an e-mail or the
unowned contact domain.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE_PATH = REPO_ROOT / "web/src/pages/data-collection.astro"
BATCH_PATH = REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md"
ROUTE = "/data-collection/"
CONTACT_URL = "https://surveillancegraph.org/data-collection/"
VALID_STATUSES = {"pending", "confirmed"}


def _norm(text: str) -> str:
    """Collapse whitespace runs — markup line-wrapping is not copy."""
    return " ".join(text.split())


def _batch_rows() -> dict[str, dict[str, str]]:
    """id → {text, sha256, status} for every ``/data-collection/`` row."""
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        # Layout: | id | page | text | sha256 | status |
        if len(cells) != 5 or cells[1] != ROUTE:
            continue
        rid, _, text, sha, status = cells
        if rid in ("id", "—") or set(rid) <= {"-", ":"}:
            continue  # header / separator lines
        rows[rid] = {"text": text, "sha256": sha, "status": status}
    return rows


def _page_source() -> str:
    return PAGE_PATH.read_text(encoding="utf-8")


def _title_prop(source: str) -> str:
    m = re.search(r'<BaseLayout\s[^>]*?title="([^"]+)"', source)
    assert m, "the page must render through BaseLayout with a title prop"
    return m.group(1)


def _slot_markup(source: str) -> str:
    """The markup inside the page's ``<BaseLayout …>…</BaseLayout>`` element."""
    m = re.search(r"<BaseLayout\b[^>]*>(.*)</BaseLayout>", source, re.S)
    assert m, "the page must render its copy through BaseLayout's slot"
    return m.group(1)


class _SlotParser(HTMLParser):
    """Collect per-element text for ``data-copy`` elements and flag any visible
    text node that no ``data-copy`` element covers."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []  # (tag, data-copy attr)
        self.elements: list[tuple[list[str], str]] = []  # (ids, normalized text)
        self._buffers: list[list[str]] = []  # text pieces per open copy element
        self.uncovered: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        copy_attr = attr.get("data-copy")
        self.stack.append((tag, copy_attr))
        if copy_attr is not None:
            self._buffers.append([])

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pass  # self-closing tags carry no text

    def handle_endtag(self, tag: str) -> None:
        while self.stack:
            popped_tag, copy_attr = self.stack.pop()
            if copy_attr is not None:
                self.elements.append((copy_attr.split(), _norm("".join(self._buffers.pop()))))
            if popped_tag == tag:
                return
        raise AssertionError(f"unbalanced </{tag}> in the page slot")

    def handle_data(self, data: str) -> None:
        if not data.strip():
            return
        if self._buffers:
            self._buffers[-1].append(data)
        else:
            self.uncovered.append(data.strip())


def _slot_elements() -> tuple[list[tuple[list[str], str]], list[str]]:
    parser = _SlotParser()
    parser.feed(_slot_markup(_page_source()))
    parser.close()
    return parser.elements, parser.uncovered


def test_batch_rows_exist_and_are_well_formed() -> None:
    # B-2 / SEED-13b: every drafted sentence is a batch row — id, page, text,
    # sha256 over the text's UTF-8 bytes, and a status from the file's
    # vocabulary. Only the operator's verbatim confirmation flips `pending`.
    rows = _batch_rows()
    assert rows, f"no {ROUTE} rows in {BATCH_PATH.relative_to(REPO_ROOT)}"
    for rid, row in rows.items():
        assert row["sha256"] == hashlib.sha256(row["text"].encode("utf-8")).hexdigest(), (
            f"{rid}: sha256 does not verify the recorded text"
        )
        assert row["status"] in VALID_STATUSES, f"{rid}: unknown status {row['status']!r}"


def test_every_page_sentence_is_batch_recorded() -> None:
    # The two-directional binding: every visible text node on the page is
    # covered by a data-copy element, every element's rendered text equals its
    # rows' texts in order, every row is carried, and the title row binds the
    # BaseLayout title prop. A sentence edited on either side fails here.
    rows = _batch_rows()
    source = _page_source()
    title_row = rows.get("title")
    assert title_row is not None, "the batch must carry a `title` row for the page"
    assert _norm(_title_prop(source)) == _norm(title_row["text"])

    elements, uncovered = _slot_elements()
    assert uncovered == [], f"page text outside any data-copy element: {uncovered}"

    seen: list[str] = []
    for ids, rendered in elements:
        for rid in ids:
            assert rid in rows, f"data-copy names {rid}, which has no batch row"
        expected = " ".join(_norm(rows[rid]["text"]) for rid in ids)
        assert rendered == expected, f"element {ids}: {rendered!r} != batch text {expected!r}"
        seen.extend(ids)

    for rid in rows:
        assert rid == "title" or rid in seen, f"batch row {rid} is not carried by the page"


def _template(source: str) -> str:
    """The emitted markup region — everything after the frontmatter fence."""
    parts = source.split("---", 2)
    return parts[2] if len(parts) == 3 else source


def test_page_is_t0_script_free() -> None:
    # ADR-155 T0: no script element, no client directive, no island import —
    # the zero-JS assertion is also exercised on the built page by the e2e
    # sweep (the route is in ZERO_JS_PUBLIC_PAGES via SHELL_PAGES). The check
    # reads the emitted template region (frontmatter `//` comments never ship).
    template = _template(_page_source())
    assert "<script" not in template.lower()
    assert "client:" not in template
    assert not re.search(r'from\s+["\'][^"\']*islands?/', _page_source())


def test_page_states_the_contract_content() -> None:
    # Deliverable 4: the exact contact URL, the robots posture, the fail-closed
    # rights gate, and the opt-out route (the dispute page — Q-29).
    source = _page_source()
    assert CONTACT_URL in source
    assert "robots_disregarded" in source
    assert 'href="/dispute/"' in source
    # No e-mail and no unowned-domain literal anywhere on the page (A-17 / C-8 /
    # B-6): the rendered copy carries neither.
    assert "@" not in "".join(t for _, t in _slot_elements()[0])
    assert "sig-project.org" not in source


def test_page_sits_in_the_shell_registry() -> None:
    # The route joins the a11y sweep + zero-JS assertion + shell checks by
    # being listed in SHELL_PAGES (web/tests/e2e/pages.ts).
    registry = (REPO_ROOT / "web/tests/e2e/pages.ts").read_text(encoding="utf-8")
    assert f'"{ROUTE}"' in registry
