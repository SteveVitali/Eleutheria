# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.17 (web honesty wave) copy-batch bindings (B-2).

Every sentence the wave authored or changed is a sha256-pinned `pending` row in
``docs/build/reports/copy-batches/batch-01.md`` — `sig-ops publish-web` refuses
to ship a pending sentence, so the rows are the operator's verbatim-
confirmation worklist for copy batch #1.

Binding conventions (same file):

* an element's ``data-copy`` attribute lists its row ids in render order;
* a row text may pin a template verbatim, placeholders included —
  ``{intakeAddress}``/``{releaseId}``/``{asOfWorld}`` are injected DATA (the
  operator's e-mail address under OP-10, the export's release stamp), not
  drafted copy;
* an element whose whole rendered text is one ``{expr}`` is literal-bound:
  its row lives under the lib file that owns the constant (DP-07, OC-01…OC-05
  → ``web/src/lib/corrections.ts``);
* superseded rows stay in the batch (append-only) bound to nothing.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_PATH = REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md"
VALID_STATUSES = {"pending", "confirmed"}

# batch `page` value → source file whose rendered elements bind its rows.
P3417_PAGES = {
    "/dispute/": "web/src/pages/dispute.astro",
    "/corrections/": "web/src/pages/corrections.astro",
    "/editorial-standards/": "web/src/pages/editorial-standards.astro",
    "/style-guide/": "web/src/pages/style-guide.astro",
    "/methodology/": "web/src/pages/methodology.astro",
    "/status/": "web/src/pages/status.astro",
    "/sources/": "web/src/pages/sources.astro",
    "/terms/": "web/src/pages/terms.astro",
    "/data-collection/": "web/src/pages/data-collection.astro",
    "/": "web/src/pages/index.astro",
    "component/BaseLayout": "web/src/layouts/BaseLayout.astro",
    "component/DisputeLink": "web/src/components/DisputeLink.astro",
}

# batch `page` value → a source file the row text must appear in verbatim.
P3417_LITERAL_PAGES = {
    "lib/corrections.ts": "web/src/lib/corrections.ts",
}

# Rows superseded by the wave (append-only: kept in the batch, bound to
# nothing). CL-03 → CL-06 (requirement id dropped), M-20 → M-43 ("frozen
# holdout" claim), DC-19 → DC-20 (the dispute page names the address now).
SUPERSEDED_ROWS = {"CL-03": "CL-06", "M-20": "M-43", "DC-19": "DC-20"}

# The P34.17 row ids (the `title` id repeats per page — page-scoped). SL-01…
# SL-04 were authored by P34.19 and stay its rows; the wave adds SL-05…SL-19.
P3417_ID = re.compile(
    r"^(DP|OC|ES|SG|MB|RS|PB|DL|ST)-\d+$"
    r"|^(HO-30|M-4\d|SL-0[5-9]|SL-1\d|TR-03|DC-20|CL-0[67])$"
    r"|^title$"
)


def _norm(text: str) -> str:
    text = re.sub(r'\{"\s*"\}', " ", text)
    text = " ".join(text.split())
    return re.sub(r" +([.,;:])", r"\1", text)


def _batch_rows() -> dict[tuple[str, str], dict[str, str]]:
    """(page, id) → row. Ids are page-scoped (`title` repeats)."""
    rows: dict[tuple[str, str], dict[str, str]] = {}
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
        rows[(page, rid)] = {"page": page, "text": text, "sha256": sha, "status": status}
    return rows


def _p3417_rows() -> dict[tuple[str, str], dict[str, str]]:
    in_scope = set(P3417_PAGES) | set(P3417_LITERAL_PAGES)
    return {
        k: r
        for k, r in _batch_rows().items()
        if P3417_ID.match(k[1]) and (k[0] in in_scope or k[0].startswith("docs/governance"))
    }


def _template(source: str) -> str:
    parts = source.split("---", 2)
    return parts[2] if len(parts) == 3 else source


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class _CopyParser(HTMLParser):
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
                if "{" in copy_attr:
                    continue  # dynamic attr (data-copy={e.copy}) — the P34.11 suite binds it
                self.elements.append((copy_attr.split(), text))
            if popped_tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if data.strip() and self._buffers:
            self._buffers[-1].append(data)


def _elements(path: str) -> list[tuple[list[str], str]]:
    parser = _CopyParser()
    parser.feed(_template(_source(path)))
    parser.close()
    return parser.elements


def _row_for(
    rows: dict[tuple[str, str], dict[str, str]], page: str, rid: str
) -> dict[str, str] | None:
    return rows.get((page, rid))


def test_p3417_rows_well_formed_and_hashes_verify() -> None:
    rows = _p3417_rows()
    # The wave's authored/changed sentences — at least the 70 rows appended.
    assert len(rows) >= 60, f"expected ≥60 P34.17 rows, found {len(rows)}"
    for (page, rid), row in rows.items():
        assert row["sha256"] == hashlib.sha256(row["text"].encode("utf-8")).hexdigest(), (
            f"{page} {rid}: sha256 does not verify"
        )
        assert row["status"] in VALID_STATUSES, f"{page} {rid}: bad status {row['status']!r}"


def test_every_p3417_data_copy_element_renders_its_rows() -> None:
    rows = _batch_rows()  # any batch row satisfies a binding (SL-01…04 are P34.19's)
    for page, rel in P3417_PAGES.items():
        for ids, rendered in _elements(rel):
            if page == "/data-collection/":
                continue  # the P35.38a suite binds that page
            # Literal-bound element: the whole rendered text is one {expr} and
            # its row lives under a lib file — checked by the literal test.
            if re.fullmatch(r"\{[^}]*\}", rendered):
                for rid in ids:
                    row = next((r for (_p, i), r in rows.items() if i == rid), None)
                    assert row is not None and row["page"] in P3417_LITERAL_PAGES, (
                        f"{rel}: placeholder-only element {ids} must bind a lib row"
                    )
                continue
            for rid in ids:
                row = _row_for(rows, page, rid)
                assert row is not None, f"{rel}: data-copy names {rid}, no {page} batch row"
            expected = _norm(" ".join(_norm(_row_for(rows, page, rid)["text"]) for rid in ids))
            assert rendered == expected, (
                f"{rel} element {ids}: {rendered!r} != batch text {expected!r}"
            )


def test_literal_rows_appear_verbatim_in_source() -> None:
    rows = _p3417_rows()
    for page, rel in P3417_LITERAL_PAGES.items():
        src = _source(rel)
        joined = re.sub(r'"\s*\+\s*\n?\s*"', "", src)
        joined = re.sub(r'"\s*\n\s*"', "", joined)
        page_rows = {rid: r for (p, rid), r in rows.items() if p == page}
        assert page_rows, f"{page}: expected rows but none recorded"
        for rid, row in page_rows.items():
            assert row["text"] in joined, f"{rid}: row text not verbatim in {rel}"


def test_every_p3417_row_is_carried() -> None:
    rows = _p3417_rows()
    carried: set[tuple[str, str]] = set()
    for page, rel in P3417_PAGES.items():
        for ids, _ in _elements(rel):
            for rid in ids:
                carried.add((page, rid))
    for (page, rid), _row in rows.items():
        if page in P3417_LITERAL_PAGES:
            carried.add((page, rid))
    orphans = set(rows) - carried
    # The `title` rows bind the BaseLayout title prop, not a data-copy element.
    orphans = {k for k in orphans if k[1] != "title"}
    # GC-* rows bind the governance doc (P34.16's surface), not this wave's pages.
    orphans = {k for k in orphans if not k[0].startswith("docs/governance")}
    # ES-05 renders only when a recorded review exists (export artifact) — the
    # element is bound on the page already; this guard is belt-and-suspenders.
    assert not orphans, f"P34.17 batch rows carried nowhere: {sorted(orphans)}"


def test_title_props_match_title_rows() -> None:
    rows = _p3417_rows()
    titles = {"/dispute/": "Dispute or correct a record", "/status/": "Status"}
    for page, expected in titles.items():
        src = _source(P3417_PAGES[page])
        m = re.search(r'<BaseLayout\s[^>]*?title="([^"]+)"', src)
        assert m, f"{page}: no BaseLayout title"
        row = _row_for(rows, page, "title")
        assert row is not None, f"{page}: no `title` batch row"
        assert _norm(m.group(1)) == _norm(row["text"]) == expected


def test_superseded_rows_stay_recorded_but_unbound() -> None:
    """Append-only: the superseded sentences stay in the batch as pending
    history and are named by a data-copy id nowhere in the tree."""
    rows = _batch_rows()
    all_bound: set[str] = set()
    for rel in P3417_PAGES.values():
        for ids, _ in _elements(rel):
            all_bound.update(ids)
    for old, new in SUPERSEDED_ROWS.items():
        assert any(rid == old for (_, rid) in rows), f"superseded row {old} dropped (append-only)"
        assert old not in all_bound, f"superseded row {old} is still rendered"
        assert any(rid == new for (_, rid) in rows), f"successor row {new} missing"
