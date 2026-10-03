# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.14 jurisdiction display-name invariants (QW-8, K4 NEW-1, F-105).

The interim lookup (``web/src/lib/jurisdictions.ts``) names every jurisdiction
code the connectors emit, the name-led surfaces all go through it, the two
physically mixed buckets carry the recorded combines sentence as batch rows
``JD-01``/``JD-02``, and the unmapped-code flag rows ``JD-03…JD-07`` bind to the
conditional elements that render them. Fails when the lookup loses a code,
when a surface regresses to a bare code, or when the batch rows drift.
"""

from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_PATH = REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md"
LIB_PATH = REPO_ROOT / "web/src/lib/jurisdictions.ts"
REGISTRY_PATH = REPO_ROOT / "connectors/src/connectors/data/camera_registry_targets.toml"

COMBINES_TEXT = "This dossier combines {combinesList}."
UNMAPPED_TEXT = (
    "A jurisdiction code SIG has not yet named is on this page — flag it in the research queue."
)

# The five surfaces that show a jurisdiction name — each consumes the shared
# lookup and carries the unmapped-code flag (AC1/AC3/AC5).
SURFACES = {
    "web/src/pages/dossier/[slug].astro": "JD-03",
    "web/src/pages/dossier/[slug]/print.astro": "JD-07",
    "web/src/pages/dossier/index.astro": "JD-04",
    "web/src/pages/search.astro": "JD-05",
    "web/src/pages/index.astro": "JD-06",
}

COMBINES_PAGES = {
    "web/src/pages/dossier/[slug].astro": "JD-01",
    "web/src/pages/dossier/[slug]/print.astro": "JD-02",
}


def _norm(text: str) -> str:
    text = re.sub(r'\{"\s*"\}', " ", text)
    text = " ".join(text.split())
    return re.sub(r" +([.,;:])", r"\1", text)


def _batch_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) != 5 or cells[0] in ("id", "—") or set(cells[0]) <= {"-", ":"}:
            continue
        rows[cells[0]] = {
            "page": cells[1],
            "text": cells[2],
            "sha256": cells[3],
            "status": cells[4],
        }
    return rows


def _template(path: str) -> str:
    parts = (REPO_ROOT / path).read_text(encoding="utf-8").split("---", 2)
    return parts[2] if len(parts) == 3 else parts[-1]


class _CopyParser(HTMLParser):
    """Collect ``data-copy`` element ids → rendered text (subset of the P34.11
    binding parser — enough to bind the JD rows)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.buffers: list[list[str]] = []
        self.elements: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        copy_attr = dict(attrs).get("data-copy")
        self.stack.append((tag, copy_attr))
        if copy_attr is not None:
            self.buffers.append([])

    def handle_endtag(self, tag: str) -> None:
        while self.stack:
            popped_tag, copy_attr = self.stack.pop()
            if copy_attr is not None:
                text = _norm("".join(self.buffers.pop()))
                for rid in copy_attr.split():
                    self.elements[rid] = text
            if popped_tag == tag:
                return

    def handle_data(self, data: str) -> None:
        if data.strip() and self.buffers:
            self.buffers[-1].append(data)


def _copy_elements(path: str) -> dict[str, str]:
    parser = _CopyParser()
    parser.feed(_template(path))
    parser.close()
    return parser.elements


def _names_table() -> dict[str, str]:
    """Parse the ``JURISDICTION_NAMES`` literal out of the TS module."""
    src = LIB_PATH.read_text(encoding="utf-8")
    block = re.search(r"export const JURISDICTION_NAMES[^=]*= \{(.*?)\};", src, re.S)
    assert block, "JURISDICTION_NAMES table not found"
    return dict(re.findall(r'"?([A-Za-z0-9-]+)"?: "([^"]+)"', block.group(1)))


def _combines_table() -> dict[str, tuple[str, str]]:
    src = LIB_PATH.read_text(encoding="utf-8")
    block = re.search(r"export const JURISDICTION_COMBINES[^=]*= \{(.*?)\};", src, re.S)
    assert block, "JURISDICTION_COMBINES table not found"
    return {
        m.group(1): (m.group(2), m.group(3))
        for m in re.finditer(r'(\w+): \["([^"]+)", "([^"]+)"\]', block.group(1))
    }


def _emitted_codes() -> set[str]:
    return set(re.findall(r'state = "([^"]+)"', REGISTRY_PATH.read_text(encoding="utf-8")))


def test_lookup_names_every_code_the_connectors_emit() -> None:
    names = _names_table()
    missing = _emitted_codes() - names.keys()
    assert not missing, f"codes the registry emits but the lookup cannot name: {missing}"
    for code, name in names.items():
        assert not re.fullmatch(r"[A-Z0-9-]+", name), (
            f"{code}: a display name is never a bare code ({name!r})"
        )


def test_mixed_buckets_carry_the_recorded_pairs() -> None:
    """K4 NEW-1 — the two physically mixed codes, verbatim."""
    assert _combines_table() == {
        "ID": ("Idaho (US)", "Indonesia"),
        "MN": ("Minnesota", "Mongolia"),
    }
    names = _names_table()
    assert names["ID"] == "Idaho (US) and Indonesia"
    assert names["MN"] == "Minnesota and Mongolia"


def test_jd_batch_rows_exist_pending_and_hash_pinned() -> None:
    rows = _batch_rows()
    expected = {
        "JD-01": ("/dossier/[slug]/", COMBINES_TEXT),
        "JD-02": ("/dossier/[slug]/print/", COMBINES_TEXT),
        "JD-03": ("/dossier/[slug]/", UNMAPPED_TEXT),
        "JD-04": ("/dossier/", UNMAPPED_TEXT),
        "JD-05": ("/search/", UNMAPPED_TEXT),
        "JD-06": ("/", UNMAPPED_TEXT),
        "JD-07": ("/dossier/[slug]/print/", UNMAPPED_TEXT),
    }
    for rid, (page, text) in expected.items():
        assert rid in rows, f"{rid} missing from batch-01 (B-2)"
        row = rows[rid]
        assert row["page"] == page, f"{rid}: page {row['page']!r} != {page!r}"
        assert row["text"] == text, f"{rid}: text drifted — {row['text']!r}"
        assert row["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert row["status"] == "pending", f"{rid}: agent rows stay pending (OM-07)"


def test_combines_elements_bind_the_rows_and_are_mixed_only() -> None:
    """The JD-01/JD-02 sentence renders ONLY inside the ``combinesList`` guard —
    a dossier that is not a physically mixed bucket can never claim one."""
    for page, rid in COMBINES_PAGES.items():
        src = (REPO_ROOT / page).read_text(encoding="utf-8")
        assert "combinesList &&" in src, f"{page}: combines element lost its guard"
        elements = _copy_elements(page)
        assert elements.get(rid) == COMBINES_TEXT, (
            f"{page}: element {rid} renders {elements.get(rid)!r}, not {COMBINES_TEXT!r}"
        )


def test_unmapped_flag_elements_bind_their_rows() -> None:
    for page, rid in SURFACES.items():
        elements = _copy_elements(page)
        assert elements.get(rid) == UNMAPPED_TEXT, (
            f"{page}: element {rid} renders {elements.get(rid)!r}, not {UNMAPPED_TEXT!r}"
        )


def test_every_name_surface_goes_through_the_lookup() -> None:
    """A surface that stops calling the shared lookup regresses to bare codes —
    the wire field stays the code, only the display transform names it."""
    for page in SURFACES:
        src = (REPO_ROOT / page).read_text(encoding="utf-8")
        assert "displayJurisdiction" in src, f"{page} no longer names jurisdictions"
    # Titles/H1s lead with the name: the subject-label code suffix is rewritten.
    for page in (
        "web/src/pages/dossier/[slug].astro",
        "web/src/pages/dossier/[slug]/print.astro",
        "web/src/pages/dossier/index.astro",
        "web/src/pages/search.astro",
        "web/src/pages/index.astro",
    ):
        src = (REPO_ROOT / page).read_text(encoding="utf-8")
        assert "dossierDisplayTitle" in src, f"{page} titles no longer lead with the name"


def test_wire_fields_keep_the_code() -> None:
    """Back-compat: the JSON wire form and the routing keys are untouched —
    only the human-facing display layer names the place."""
    dossier_lib = (REPO_ROOT / "web/src/lib/dossier.ts").read_text(encoding="utf-8")
    assert "jurisdiction: dossier.jurisdiction" in dossier_lib, (
        "the JSON wire form keeps emitting the bare jurisdiction code"
    )
    assert "subject: dossier.subject_label" in dossier_lib, (
        "the JSON wire form keeps emitting subject_label verbatim"
    )
    assert "jurisdictions" not in dossier_lib, "the wire layer never consumes the display lookup"
    index_src = (REPO_ROOT / "web/src/pages/dossier/index.astro").read_text(encoding="utf-8")
    assert "data-slug={d.slug}" in index_src, "slugs stay the routing key"
