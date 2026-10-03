# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.11 copy-batch binding invariants (B-2, QW-6/QW-7/QW-9/QW-14, K12b/K14).

Every public sentence P34.11 authored or changed is a sha256-pinned row in
``docs/build/reports/copy-batches/batch-01.md`` (pending until the operator's
verbatim confirmation). This suite binds the rows to the code in both
directions: every ``data-copy`` element on a touched page resolves to batch rows
whose joined text equals the rendered text, every row is carried somewhere, and
every literal-bound row (shared lib strings, fixture notes, export strings)
appears verbatim in its source file. Generated template placeholders
(``{logStart}``, ``{permalink}``, …) are recorded verbatim so the operator
confirms the template itself.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_PATH = REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md"
VALID_STATUSES = {"pending", "confirmed"}

# The batch ids P34.11 authored (the DC-* rows belong to P35.38a) plus the rows
# P34.12 appended (HW-10, RQ-01, XC-03), P34.13 appended (HW-11…HW-13,
# MD-01, WM-01, NF-01/02, FB-01/02, GN-01, TR-01/02), P34.14 appended
# (JD-01…JD-07) and P34.15 appended (MP-01…MP-15, NW-01…NW-03, WS-01 —
# same batch, same checks).
# The DC-* rows belong to P35.38a; P34.17 added DC-20 (superseding DC-19),
# MB-01/02 (the /methodology/ basis label — GC-04/05's pinned texts), ES-01…05
# and SG-01 (the editorial-standards rewrite + the style-guide register
# sentence). The wave's other rows (DP/OC/ST/SL-05+/PB/RS/DL/TR-03+) bind on
# pages with placeholder-bearing elements this suite does not model —
# `tests/unit/test_p34_17_copy_batch.py` covers them.
P34_ID = re.compile(
    r"^(HO|DI|D|DS|HW|CC|CL|W|M|T|DF|CM|XD|XC|RQ|NF|FB|GN|TR|MD|WM|JD|MP|NW|WS|DC|MB|ES|SG)-\d+$"
)

# Batch rows whose page P34.12 retired (K11 §5.5 / RQ-00): the `/task/new/`
# fixture route is gone, so T-01 ("Return to the dossier index.") is recorded
# history that can never ship — kept in the batch (append-only) but bound to
# nothing. Asserted retired, never silently dropped.
RETIRED_ROWS = {"T-01": "web/src/pages/task/new/[slug].astro"}

# Rows P34.17 superseded with corrected sentences (the batch is append-only —
# the old rows stay recorded, bound to nothing): CL-03 → CL-06 (the
# requirement id dropped from public copy), M-20 → M-43 (the "frozen holdout"
# claim withdrawn). Asserted superseded, never silently dropped.
SUPERSEDED_ROWS = {"CL-03", "M-20", "DC-19"}

# batch `page` value → the .astro source whose rendered elements bind its rows.
ASTRO_PAGES = {
    "/": "web/src/pages/index.astro",
    "/dossier/": "web/src/pages/dossier/index.astro",
    "/dossier/[slug]/": "web/src/pages/dossier/[slug].astro",
    "/dossier/[slug]/print/": "web/src/pages/dossier/[slug]/print.astro",
    "/map/": "web/src/pages/map.astro",
    "/network/": "web/src/pages/network.astro",
    "/search/": "web/src/pages/search.astro",
    "/corrections/": "web/src/pages/corrections.astro",
    "/watch/": "web/src/pages/watch.astro",
    "/methodology/": "web/src/pages/methodology.astro",
    "/404.html": "web/src/pages/404.astro",
    "/403/": "web/src/pages/403.astro",
    "/410/": "web/src/pages/410.astro",
    "/terms/": "web/src/pages/terms.astro",
    "/data-collection/": "web/src/pages/data-collection.astro",
    "/editorial-standards/": "web/src/pages/editorial-standards.astro",
    "/style-guide/": "web/src/pages/style-guide.astro",
    "component/HowWeKnowThis": "web/src/components/HowWeKnowThis.astro",
    "component/Citation": "web/src/components/Citation.astro",
    "component/WhatWeDontKnow": "web/src/components/WhatWeDontKnow.astro",
}

# batch `page` value → a source file the row text must appear in verbatim
# (shared lib constants, fixture strings, export-emitted strings).
LITERAL_PAGES = {
    "lib/dossier.ts": "web/src/lib/dossier.ts",
    "lib/dossier-fixture.ts": "web/src/lib/dossier-fixture.ts",
    "lib/corrections-methodology-fixture.ts": "web/src/lib/corrections-methodology-fixture.ts",
    "lib/research-queue.ts": "web/src/lib/research-queue.ts",
    "lib/map.ts": "web/src/lib/map.ts",
    "lib/empty.ts": "web/src/lib/empty.ts",
    "lib/workspace-state.ts": "web/src/lib/workspace-state.ts",
    "lib/meta.ts": "web/src/lib/meta.ts",
    "component/BaseLayout": "web/src/layouts/BaseLayout.astro",
    "exports/web_dossier.py": "exports/src/exports/web_dossier.py",
    "exports/spine_export.py": "exports/src/exports/spine_export.py",
}


def _norm(text: str) -> str:
    """Collapse whitespace, unfold ``{" "}`` JSX space literals, and repair the
    ``tag>.`` split artefacts — markup line-wrapping and tag boundaries
    contribute no copy."""
    text = re.sub(r'\{"\s*"\}', " ", text)
    text = " ".join(text.split())
    return re.sub(r" +([.,;:])", r"\1", text)


def _batch_rows() -> dict[str, dict[str, str]]:
    """id → {page, text, sha256, status} for every batch row."""
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


def _p34_rows() -> dict[str, dict[str, str]]:
    return {rid: r for rid, r in _batch_rows().items() if P34_ID.match(rid)}


def _template(source: str) -> str:
    """The emitted markup region — everything after the frontmatter fence."""
    parts = source.split("---", 2)
    return parts[2] if len(parts) == 3 else source


def _source(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


# `{CONSTANT}` placeholders in rendered text resolve to the exported literal —
# the dossier module's shared copy constants stay the single source of truth.
def _constants() -> dict[str, str]:
    out: dict[str, str] = {}
    src = _source("web/src/lib/dossier.ts")
    for name, value in re.findall(r'export const (\w+) = "([^"]*)";', src):
        out[name] = value
    return out


def _resolve(text: str) -> str:
    consts = _constants()

    def sub(m: re.Match[str]) -> str:
        name = m.group(1)
        return consts.get(name, m.group(0))

    return re.sub(r"\{([A-Z][A-Z_]*)\}", sub, text)


class _CopyParser(HTMLParser):
    """Collect per-element text for ``data-copy`` elements. Dynamic attributes
    (``data-copy={e.copy}``) are recorded separately for the ``copy:`` field
    binding check."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.elements: list[tuple[list[str], str]] = []  # (static ids, text)
        self.dynamic: list[str] = []  # dynamic attr sources, e.g. "{e.copy}"
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
                    self.dynamic.append((copy_attr, text))
                else:
                    self.elements.append((copy_attr.split(), text))
            if popped_tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if data.strip() and self._buffers:
            self._buffers[-1].append(data)


def _elements(path: str) -> tuple[list[tuple[list[str], str]], list[tuple[str, str]]]:
    parser = _CopyParser()
    parser.feed(_template(_source(path)))
    parser.close()
    return parser.elements, parser.dynamic


def test_p34_rows_are_well_formed_and_hashes_verify() -> None:
    rows = _p34_rows()
    assert len(rows) >= 40, "P34.11 authored rows must all be recorded in batch-01"
    for rid, row in rows.items():
        assert row["sha256"] == hashlib.sha256(row["text"].encode("utf-8")).hexdigest(), (
            f"{rid}: sha256 does not verify the recorded text"
        )
        assert row["status"] in VALID_STATUSES, f"{rid}: unknown status {row['status']!r}"
        assert row["page"] in ASTRO_PAGES or row["page"] in LITERAL_PAGES or rid in RETIRED_ROWS, (
            f"{rid}: unknown page scope {row['page']!r}"
        )


def test_every_data_copy_element_renders_its_rows() -> None:
    """Every static ``data-copy`` element's rendered text equals its rows'
    joined texts — sentence order in the attribute is binding order."""
    rows = _p34_rows()
    for rel in ASTRO_PAGES.values():
        for ids, rendered in _elements(rel)[0]:
            for rid in ids:
                assert rid in rows, f"{rel}: data-copy names {rid}, which has no batch row"
            expected = _norm(" ".join(_norm(rows[rid]["text"]) for rid in ids))
            actual = _norm(_resolve(rendered))
            assert actual == expected, f"{rel} element {ids}: {actual!r} != batch text {expected!r}"


def test_dynamic_copy_fields_bind_their_literals() -> None:
    """A ``data-copy={e.copy}`` element binds through the owning object's
    ``copy:`` field: that object's ``body:`` literal must equal the joined row
    texts (index.astro's ENTRY_POINTS)."""
    rows = _p34_rows()
    for rel in ["web/src/pages/index.astro"]:
        src = _source(rel)
        # ENTRY_POINTS objects: href/title/body[/copy] — the copy field names
        # the rows the body literal must match.
        for m in re.finditer(
            r'body:\s*(?:"([^"]*)"|"([^"]*)")(?:\s*\+\s*"([^"]*)")?,\s*\n\s*copy: "([^"]+)"',
            src,
        ):
            body = "".join(g for g in m.groups()[:3] if g)
            ids = m.group(4).split()
            for rid in ids:
                assert rid in rows, f"{rel}: copy field names {rid}, no batch row"
            expected = _norm(" ".join(_norm(rows[rid]["text"]) for rid in ids))
            assert _norm(body) == expected, (
                f"{rel} entry {ids}: body {body!r} != batch text {expected!r}"
            )
        # The field must actually render: the body span carries the binding.
        assert "data-copy={e.copy}" in src, f"{rel}: copy field never reaches markup"


def test_literal_rows_appear_verbatim_in_source() -> None:
    """Rows filed under a lib/exports file must appear there verbatim — string
    concatenation across lines is joined before the check."""
    rows = _p34_rows()
    for page, rel in LITERAL_PAGES.items():
        src = _source(rel)
        # Join `"a" + "b"` (TS/Python explicit) and `"a" "b"` (Python implicit).
        joined = re.sub(r'"\s*\+\s*\n?\s*"', "", src)
        joined = re.sub(r'"\s*\n\s*"', "", joined)
        page_rows = [rid for rid, r in rows.items() if r["page"] == page]
        assert page_rows, f"{page}: expected rows but none recorded"
        for rid in page_rows:
            text = rows[rid]["text"]
            assert text in joined, f"{rid}: row text not found verbatim in {rel}"


def test_every_p34_row_is_carried_somewhere() -> None:
    """No orphan rows: every P34.11 row is bound by an element, a copy field,
    or a literal-presence check on its page's file."""
    rows = _p34_rows()
    carried: set[str] = set()
    for rel in ASTRO_PAGES.values():
        elements, _ = _elements(rel)
        for ids, _text in elements:
            carried.update(ids)
    for page in LITERAL_PAGES:
        for rid, row in rows.items():
            if row["page"] == page:
                carried.add(rid)
    for rel in ["web/src/pages/index.astro"]:
        for ids in re.findall(r'copy: "([^"]+)"', _source(rel)):
            carried.update(ids.split())
    orphans = set(rows) - carried - set(RETIRED_ROWS) - SUPERSEDED_ROWS
    assert not orphans, f"batch rows never carried by any surface: {sorted(orphans)}"
    # A superseded row is only excused because a successor row replaced its
    # binding (P34.17) — and it must not be rendered.
    for rid in SUPERSEDED_ROWS:
        assert rid not in carried, f"superseded row {rid} is still bound by an element"
    # A retired row is only excused because its page no longer exists.
    for rid, page_file in RETIRED_ROWS.items():
        assert rid in rows, f"retired row {rid} must stay in the batch (append-only)"
        assert not (REPO_ROOT / page_file).exists(), (
            f"{rid}: marked retired but its page {page_file} exists — "
            "re-add the binding or delete the retirement marker"
        )


def test_shared_lib_rows_match_the_exported_constants() -> None:
    """lib/dossier.ts rows bind the actual exported copy, not a prose retelling:
    NO_RECORD_IN_SIG must equal DS-01's text exactly, and the banner's absence
    rule must equal DS-02's."""
    src = _source("web/src/lib/dossier.ts")
    rows = _p34_rows()
    m = re.search(r'export const NO_RECORD_IN_SIG = "([^"]*)";', src)
    assert m and m.group(1) == rows["DS-01"]["text"]
    assert rows["DS-02"]["text"] in src


def test_corrections_page_states_the_log_start() -> None:
    """QW-14: the corrections log states its own start date — it can never read
    as if it had always run — and the date is the earliest recorded correction,
    not a hand-written claim."""
    src = _source("web/src/pages/corrections.astro")
    assert 'data-testid="log-start"' in src
    assert "e.corrected_at" in src, "the start date must derive from the entries"


def test_public_surface_links_to_no_withdrawn_route() -> None:
    """C-12/LATER-03 + the P34.10 allow-list: no public page, layout or component
    links to a route the allow-list withdraws. (The internal/ tree keeps the
    pages themselves; only the public link surface is swept.)"""
    withdrawn = re.compile(
        r'href="(?:/(?:contribution-back|visual-language|research-dossier|releases|reference-map)/?)'
    )
    offenders: list[str] = []
    for base in ["web/src/pages", "web/src/components", "web/src/layouts"]:
        for path in (REPO_ROOT / base).rglob("*.astro"):
            if "internal" in path.parts:
                continue
            if withdrawn.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"withdrawn-route links remain: {offenders}"


def test_no_empty_dossier_section_asserts_an_absence_kind() -> None:
    """F-422's W0 half: the empty-section sentence asserts NO kind — it does not
    claim 'not researched', 'no evidence', or any other §9.5 state the data
    does not record."""
    rows = _p34_rows()
    text = rows["DS-01"]["text"]
    assert text == "No record in SIG."
    for forbidden in ["not researched", "no evidence", "absent", "does not exist"]:
        assert forbidden not in text.lower()
