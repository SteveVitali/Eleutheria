# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The §39.2 dossier content contract (SIG-UI-010..015), tested on the renderer in
isolation from the slice."""

from __future__ import annotations

from datetime import date

import pytest
from exports.dossier import (
    SECTION_IDS,
    DocumentRef,
    Dossier,
    Figure,
    Gap,
    Reconciliation,
    ReconClaim,
    Row,
    Section,
    render_json,
    render_print_html,
)


def _doc() -> DocumentRef:
    return DocumentRef(
        source_family="executed contract",
        stable_locator="https://example/contract",
        locator={"quote": "90 cameras", "text_span": [0, 10]},
        capture_digest="bexample",
        excerpt="90 cameras",
    )


def _figure() -> Figure:
    win = ReconClaim(90, "executed contract", "R1", 4, date(2023, 1, 1), _doc())
    dissent = ReconClaim(299, "community map", "R5", 2, date(2026, 8, 20), _doc())
    return Figure(
        key="contracted_device_count",
        label="Contracted device count",
        value=90,
        unit="cameras",
        reconciliation=Reconciliation(
            rule="contracted: W4",
            winning=win,
            competing=(dissent,),
            note="42 wins its own predicate.",
        ),
    )


def _dossier(**over: object) -> Dossier:
    sections = tuple(
        Section(
            sid,
            figures=(_figure(),) if sid == "what_is_deployed" else (),
            rows=(Row("Retention", None, status="not_researched"),)
            if sid == "configuration_and_retention"
            else (),
        )
        for sid in SECTION_IDS
    )
    kw: dict[str, object] = dict(
        subject_label="Test agency deployment",
        jurisdiction="Test City",
        as_of=date(2026, 9, 1),
        permalink="https://sig/dossier/test",
        sections=sections,
        gaps=(Gap("installed_device_count", "not_researched", "no inventory"),),
        unresearched_field_count=2,
        source_families=("executed contract", "community map"),
    )
    kw.update(over)
    return Dossier(**kw)  # type: ignore[arg-type]


def test_sections_are_the_twelve_in_order() -> None:
    # SIG-UI-010 — the exact §39.2 order.
    assert SECTION_IDS == (
        "at_a_glance",
        "what_is_deployed",
        "cost_and_expiry",
        "who_else_can_see",
        "configuration_and_retention",
        "usage",
        "where_the_hardware_is",
        "policy",
        "accountability_events",
        "timeline",
        "what_we_dont_know",
        "how_we_know_this",
    )
    js = render_json(_dossier())
    assert [s["id"] for s in js["sections"]] == list(SECTION_IDS)


def test_out_of_order_sections_are_rejected() -> None:
    d = _dossier()
    bad = Dossier(
        subject_label=d.subject_label,
        jurisdiction=d.jurisdiction,
        as_of=d.as_of,
        permalink=d.permalink,
        sections=tuple(reversed(d.sections)),
        gaps=d.gaps,
        unresearched_field_count=d.unresearched_field_count,
    )
    with pytest.raises(ValueError):
        render_json(bad)


def test_what_we_dont_know_is_in_summary_and_api_and_print() -> None:
    # SIG-UI-011 — not an appendix.
    js = render_json(_dossier())
    assert js["what_we_dont_know"], "gap list must be at the summary/API top level"
    assert any(s["id"] == "what_we_dont_know" for s in js["sections"])
    html = render_print_html(_dossier())
    assert "What we don't know" in html


def test_incompleteness_banner_names_count_and_absence_rule() -> None:
    # SIG-UI-012.
    js = render_json(_dossier(unresearched_field_count=5))
    banner = js["incompleteness_banner"]
    assert "5 unresearched field" in banner
    assert "absence of a row is not evidence of absence" in banner
    assert banner in render_print_html(_dossier(unresearched_field_count=5))


def test_print_path_has_sources_and_asof_and_permalink_on_every_page() -> None:
    # SIG-UI-013.
    html = render_print_html(_dossier())
    footers = html.count("<footer class='page-footer'>")
    pages = html.count("<div class='page'>")
    assert pages >= 1
    assert footers == pages, "every page must carry the footer"
    # each footer carries the as-of date and the permalink
    assert html.count("As of 2026-09-01") == footers
    assert html.count("https://sig/dossier/test") >= footers
    # sources are present (the document links behind figures + the how-we-know section)
    assert "https://example/contract" in html


def test_every_material_figure_is_expandable_to_its_reconciliation() -> None:
    # SIG-UI-014 — rule, competing claims, tier + date, document link.
    js = render_json(_dossier())
    deployed = next(s for s in js["sections"] if s["id"] == "what_is_deployed")
    assert deployed["figures"], "expected at least one material figure"
    for fig in deployed["figures"]:
        rec = fig["reconciliation"]
        assert rec["rule"]
        assert rec["winning"]["reliability"] and rec["winning"]["observed_at"]
        assert rec["winning"]["document"]["stable_locator"]
        for comp in rec["competing"]:
            assert comp["reliability"] and comp["observed_at"]
            assert comp["document"]["locator"]
    html = render_print_html(_dossier())
    assert "<details class='reconciliation'>" in html


def test_unknown_values_are_rendered_not_omitted() -> None:
    # SIG-UI-015.
    js = render_json(_dossier())
    cfg = next(s for s in js["sections"] if s["id"] == "configuration_and_retention")
    row = cfg["rows"][0]
    assert row["value"] is None
    assert row["display_value"] == "unknown"
    assert "unknown" in render_print_html(_dossier())
