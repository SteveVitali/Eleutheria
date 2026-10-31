# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.39 / K3 SRCH-04 (SIG-SRCH-002, SIG-SRCH-006, SIG-SRCH-007,
SIG-SRCH-008, SIG-SRCH-009) — the v2 no-JS results page the API answers to
``format=html``: site chrome + stamp + dispute + licences (DR-C4-02), typed
sections with evidence-basis cards, facet GET links, per-group paging, the
K3 §6.4 empty states, HTML error pages for every status (DR-C4-10), the
``sig.workspace-state/2`` "cite this search" mint, escaping, and the 320 px
reflow posture (DR-C4-14) — asserted over the P36.32 synthetic fixture
engine (invented names, K0 R-11), never a live query."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from exports.search_results_page import (  # noqa: E402
    INTERIM_CITE_SEARCH_TEXT,
    search_results_error_page_v2,
    search_results_page_v2,
)
from test_search_query_v2 import (  # noqa: E402
    PUB,
    _aliases,
    _catalog_docs,
    _records,
)

from exports import search_index_v2 as siv2  # noqa: E402
from exports import search_query_v2 as sqv  # noqa: E402


@pytest.fixture()
def engine(tmp_path: Path):
    """The same two-compartment synthetic engine test_search_query_v2
    builds, plus one "ice" word-hit record so the acronym-alias collapse
    has something to collapse."""
    rows = _records() + [
        {
            "record_key": "rk-ice",
            "entity_id": "ent-ice",
            "entity_type": "deployment",
            "label": "Kestrel ice post",
            "jurisdiction": "iso3166-2:MX-KL",
            "place_text": "Kelso · Miralba · KL",
            "source_id": "src_kelso",
            "technology": "",
            "claim_ids": [],
        }
    ]
    comp_paths = {}
    split = {
        "comp_a": [r for r in rows if r["record_key"] < "rk-040"],
        "comp_b": [r for r in rows if r["record_key"] >= "rk-040"],
    }
    for comp, comp_rows in split.items():
        comp_dir = tmp_path / comp
        comp_dir.mkdir()
        out = comp_dir / "search_index_v2.sqlite"
        siv2.build_record_index_v2(
            comp_rows,
            publication_id=PUB,
            compartment=comp,
            license_id="CC-BY-4.0",
            out=out,
            release_label="sig-test.1",
            as_of_world="2026-10-29",
            source_names={
                "src_mira": "Miralba transit registry",
                "src_kelso": "Kelso civic data",
            },
            place_names={},
        )
        comp_paths[comp] = (out, comp_dir / "claim_ref.sqlite")
    cat = tmp_path / "catalog.sqlite"
    siv2.build_catalog_index(
        _catalog_docs(),
        publication_id=PUB,
        out=cat,
        aliases=_aliases(),
        release_label="sig-test.1",
        as_of_world="2026-10-29",
    )
    eng = sqv.SearchEngineV2.open(cat, list(comp_paths.values()))
    yield eng
    eng.close()


def _page(engine, q: str | None = None, **kw) -> str:
    params = sqv.parse_params_v2(q=q, limit=kw.pop("limit", 10), **kw)
    result = engine.search(params)
    html = search_results_page_v2(
        requested=PUB,
        params={
            "q": params.q_raw or "",
            "types": sorted(params.types) if params.types else [],
            "filters": params.filters,
            "cursor": f"{params.group}:{params.cursor}" if params.group and params.cursor else None,
            "expand": "1" if params.expand_collapsed else None,
        },
        result=result,
        site_release={
            "schema": "sig.site-release/1",
            "label": "sig-test.1",
            "publication_id": PUB,
            "as_of_world": "2026-10-29T00:00:00Z",
            "built_at": "2026-10-29T01:00:00Z",
            "code": {"commit": "ab" * 20, "url": "https://example.test/commit"},
        },
        was_latest=False,
    )
    return html.decode()


def test_chrome_stamp_dispute_licence(engine):
    """DR-C4-02: site nav, the release stamp, the dispute link and the
    licence line are all present; the page carries no <script> (T0)."""
    html = _page(engine, "Kestrel")
    assert "<script" not in html
    assert 'aria-label="Site"' in html and 'href="/map/"' in html
    assert "Dispute or correct" in html
    assert "Licence of the data on this page" in html
    assert "sig-test.1" in html and "data as of" in html
    assert f"/releases/{PUB}/release.json" in html
    assert 'meta name="viewport"' in html
    assert "word-break:break-all" in html  # DR-C4-14 — ids wrap at 320 px


def test_header_strip_and_scope(engine):
    html = _page(engine, "Kestrel")
    assert "licence groups searched" in html
    assert "2026-10-29" in html


def test_typed_sections_and_cards(engine):
    """SIG-SRCH-002/007: typed sections in order, each card an <article>
    with an h3 link, its evidence basis and a stated match reason."""
    html = _page(engine, "Miralba")
    assert "<h2" in html and "<article>" in html and "<h3>" in html
    assert "matched:" in html
    # The place card shows what the release holds there (SIG-SRCH-007).
    assert "record(s) from" in html or "source:" in html


def test_place_homonyms_shown_with_parent(engine):
    """A1's leg — 'Kelso' names two places; both appear with parents."""
    html = _page(engine, "Kelso")
    assert "Kelso" in html and "iso3166-1:MX" in html


def test_alias_card_expansion_source_and_collapse(engine):
    """SIG-SRCH-005 region: 'ICE' = the alias card states the expansion and
    its cited source; word-hits collapse behind a show-them link."""
    html = _page(engine, "ICE")
    assert "Imaginary Customs Enforcement" in html
    assert "https://example.test/" in html
    assert "names no record" in html or "resolves to" in html
    assert "show them" in html and "expand=1" in html


def test_derived_name_marked(engine):
    """SIG-SRCH-007: an unlabelled record's derived name is marked."""
    html = _page(engine, None, limit=5)
    assert "name derived" in html


def test_suggestion_stated(engine):
    """SIG-SRCH-006: the suggestion is stated, never a silent rewrite."""
    html = _page(engine, "aldercrof")
    assert "Showing results for" in html
    assert "search instead for" in html


def test_no_match_empty_state(engine):
    """SIG-SRCH-008 / K3 §6.4: names the searched scope; never research
    status, never a recorded absence."""
    html = _page(engine, "zzqx-nonexistent")
    assert "does not contain these words" in html
    assert "licence groups searched" in html
    assert "not researched" not in html.lower()


def test_filtered_to_zero_names_filters(engine):
    html = _page(engine, "Kestrel", jurisdiction="iso3166-2:ZZ-ZZ")
    assert "without those filters" in html or "No record" in html


def test_per_group_cursor_paging(engine):
    """Per-group 'more' links carry the group cursor — never a global page."""
    html = _page(engine, None, limit=5)
    assert "More records in this licence group" in html
    assert "cursor=" in html


def test_facet_get_links(engine):
    html = _page(engine, "Kestrel")
    assert "Narrow this search" in html
    assert "format=html" in html
    # Facet links re-query — they are GET hrefs, never javascript: urls.
    assert "javascript:" not in html


def test_cite_this_search_mints_workspace_state(engine):
    html = _page(engine, "Kestrel", types=["record"])
    assert "Cite this search" in html
    assert f"/s/{PUB}/search/?" in html
    assert "v=2" in html and "view=list" in html
    assert f"release={PUB}" in html
    assert "q=Kestrel" in html and "type=record" in html
    assert INTERIM_CITE_SEARCH_TEXT.split(";")[0] in html


def test_every_dynamic_string_escaped(engine):
    html = _page(engine, '<img src=x onerror="boom()">')
    assert "<img" not in html
    assert "&lt;img" in html


def test_h1_names_the_query(engine):
    html = _page(engine, "Kestrel")
    assert "<h1>Search results for Kestrel</h1>" in html


# --------------------------------------------------------------------------- #
# The error representation (DR-C4-10)                                          #
# --------------------------------------------------------------------------- #


def test_error_page_every_status():
    for status in (400, 404, 409, 422, 429, 503):
        html = search_results_error_page_v2(
            requested="latest",
            status=status,
            code=f"err_{status}",
            detail="a plain-language detail",
        ).decode()
        assert "<script" not in html
        assert f"err_{status}" in html
        assert "a plain-language detail" in html
        assert 'aria-label="Site"' in html
        assert "Dispute or correct" in html


def test_error_page_410_tombstone():
    html = search_results_error_page_v2(
        requested=PUB,
        status=410,
        code="withdrawn",
        detail="withdrawn under the current publication-disposition policy",
        tombstone={
            "reason_category": "safety_withdrawal",
            "authority": "test-authority",
            "policy_version": "policy-test",
        },
    ).decode()
    assert "safety_withdrawal" in html
    assert "test-authority" in html


def test_error_page_escapes_detail():
    html = search_results_error_page_v2(
        requested="latest",
        status=422,
        code="unsupported_query",
        detail="<script>alert(1)</script>",
    ).decode()
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
