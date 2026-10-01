# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the ``web/analytics/`` export artifact family (P31.14, SURFACE.1).

Pure tests over fabricated shaping rows — no database (the seeded-spine e2e lives in
``tests/db/test_spine_export_over_seeded_spine.py``). These tests prove: the five
analytics artifacts are emitted under ``web/analytics/`` (never the demo-guarded
``web/presentation/``); every file carries schema / as_of / a named denominator /
``is_population_total: false`` / its source compartments; density bins are
deterministic H3 over releasable tier-0 points only; centrality is honest degree
over the typed access edges with a deterministic focus rule; the decision point is
the earliest derivable watch decision or ``None``; provenance carries the W-tier
distributions; and the licence labels stay separated per compartment.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from exports.analytics import (
    ANALYTICS_DIR,
    ANALYTICS_FILES,
    DENSITY_H3_RESOLUTION,
    AnalyticsArtifact,
    assert_analytics_separated,
    build_analytics,
)
from exports.compartments import assert_separated
from exports.manifest import BuildSpec
from exports.shaping import build_shaped_dataset, parse_shaping_claims
from exports.spine_export import build_spine_export
from test_spine_export import _rows, _site

_ANALYTICS_PREFIX = "web/analytics/"


def _build_dataset(claims, raw_over=None, weight_axes=None):
    rows = _rows(claims)
    subjects = sorted({c.subject_id for c in claims})
    # The ``claim_weights`` supplementary read shape:
    # (claim_id, source_id, predicate_id, source_reliability, claim_directness,
    #  artifact_integrity, observed_at, spdx). ``weight_axes`` overrides the
    # R/D/I codes per claim_id (default R1/D1/I1).
    axes = weight_axes or {}
    raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "claim_weights": [
            (
                c.claim_id,
                c.source_id,
                c.predicate_id,
                *axes.get(c.claim_id, ("R1", "D1", "I1")),
                c.observed_at,
                c.effective_spdx,
            )
            for c in claims
        ],
        "spine_watermark": "claims=1",
    }
    raw.update(raw_over or {})
    dataset = build_shaped_dataset(
        raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )
    return dataset, raw, rows


def _export(claims, raw_over=None, materialized=None, site_runs=None, weight_axes=None):
    over = dict(raw_over or {})
    over.update(materialized or {})
    if site_runs is not None:
        over["materialized_site_runs"] = site_runs
    dataset, raw, rows = _build_dataset(claims, over, weight_axes)
    subjects = sorted({c.subject_id for c in claims})
    bs = BuildSpec(
        as_of_snapshot=date(2026, 9, 22),
        as_of_belief=date(2026, 9, 22),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
    )
    return build_spine_export(
        dataset,
        raw,
        build_spec=bs,
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
    )


def _analytic(export, name: str) -> dict:
    return json.loads(export.web_artifacts[f"{_ANALYTICS_PREFIX}{name}.json"].decode("utf-8"))


# --- the family + the envelope -----------------------------------------------


def test_the_five_analytics_files_are_emitted_under_web_analytics() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    for name in ANALYTICS_FILES:
        assert f"{_ANALYTICS_PREFIX}{name}.json" in export.web_artifacts
    # The demo-guarded presentation tree is NEVER emitted by a real export (P30.3/P31.14).
    assert not any(p.startswith("web/presentation/") for p in export.web_artifacts)


def test_every_analytic_carries_schema_asof_denominator_and_compartments() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    for name in ANALYTICS_FILES:
        payload = _analytic(export, name)
        assert payload["schema"].startswith("sig/analytics-"), name
        assert payload["as_of"] == "2026-09-22"
        # A NAMED denominator — what the number is a count/share of — never a bare total.
        assert isinstance(payload["denominator"], str) and payload["denominator"], name
        assert payload["is_population_total"] is False, name
        assert isinstance(payload["source_compartments"], list), name


def test_analytics_are_filed_in_the_manifest_with_compartment_and_licence() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    entries = {a.path: a for a in export.manifest.artifacts if a.path.startswith(_ANALYTICS_PREFIX)}
    assert {Path(p).name for p in entries} == {f"{n}.json" for n in ANALYTICS_FILES}
    for entry in entries.values():
        assert entry.compartment and entry.license


def test_analytics_are_byte_deterministic_for_one_snapshot() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    e1 = _export(claims)
    e2 = _export(claims)
    for name in ANALYTICS_FILES:
        assert (
            e1.web_artifacts[f"{_ANALYTICS_PREFIX}{name}.json"]
            == e2.web_artifacts[f"{_ANALYTICS_PREFIX}{name}.json"]
        )


# --- density bins -------------------------------------------------------------


def test_density_bins_are_h3_over_tier0_points_with_coverage() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    payload = _analytic(export, "density_bins")
    assert payload["grid"] == "h3"
    assert payload["h3_resolution"] == DENSITY_H3_RESOLUTION
    bins = payload["bins"]
    assert len(bins) >= 1
    for b in bins:
        assert set(b) == {"h3", "jurisdiction", "deviceCount", "coverage"}
        assert b["coverage"] in {"none", "low", "partial", "high"}
        assert b["deviceCount"] >= 1
    # The whole family's deviceCount totals the tier-0 sites in scope.
    assert sum(b["deviceCount"] for b in bins) == 1
    assert "1 published observation-level site" in payload["denominator"]


def test_density_bins_bin_two_nearby_points_into_one_cell() -> None:
    # Two sites ~600 m apart share an H3 res-3 cell.
    export = _export(
        _site("A", "35.460", "-97.510", "Oklahoma") + _site("B", "35.465", "-97.511", "Oklahoma")
    )
    bins = _analytic(export, "density_bins")["bins"]
    assert len(bins) == 1
    assert bins[0]["deviceCount"] == 2


def test_density_bins_exclude_tier1_points_and_say_so() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", tier=1
    )
    export = _export(claims)
    payload = _analytic(export, "density_bins")
    assert sum(b["deviceCount"] for b in payload["bins"]) == 1
    assert "tier-0" in payload["denominator"]


def test_density_bins_exclude_licence_refused_subjects() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", spdx="UNDETERMINED", redistributable="no"
    )
    export = _export(claims)
    payload = _analytic(export, "density_bins")
    assert sum(b["deviceCount"] for b in payload["bins"]) == 1
    assert "licence-refused" in payload["denominator"]


def test_density_bins_empty_state_is_honest_never_a_total() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma", tier=1))  # no tier-0 points
    payload = _analytic(export, "density_bins")
    assert payload["bins"] == []
    assert payload["is_population_total"] is False
    assert payload["denominator"]


def test_density_bins_name_their_source_compartments() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    payload = _analytic(_export(claims), "density_bins")
    assert set(payload["source_compartments"]) == {"osm_physical", "sig_graph"}


# --- licence separation for the family ---------------------------------------


def test_a_mixed_licence_density_file_carries_the_and_label_in_web_mixed() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _export(claims)
    entry = next(
        a for a in export.manifest.artifacts if a.path == "web/analytics/density_bins.json"
    )
    assert entry.license == "CC-BY-4.0 AND ODbL-1.0"
    assert entry.compartment == "web_mixed"


def test_a_single_ccby_density_file_stays_in_the_web_compartment() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma", spdx="CC-BY-4.0"))
    entry = next(
        a for a in export.manifest.artifacts if a.path == "web/analytics/density_bins.json"
    )
    assert entry.compartment == "web"
    assert entry.license == "CC-BY-4.0"


def test_a_single_non_ccby_density_file_is_filed_restricted_web_mixed() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    entry = next(
        a for a in export.manifest.artifacts if a.path == "web/analytics/density_bins.json"
    )
    assert entry.compartment == "web_mixed"
    assert entry.license == "ODbL-1.0"


def test_analytics_compartments_are_licence_separated() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _export(claims)
    # The whole placed tree — every analytics file included — carries one licence
    # per compartment (the assert_separated invariant).
    assert_separated(export.bundle.placed)
    by_compartment: dict[str, set[str]] = {}
    for a in export.manifest.artifacts:
        if a.path.startswith(_ANALYTICS_PREFIX):
            by_compartment.setdefault(a.compartment, set()).add(a.license)
    for compartment, licences in by_compartment.items():
        assert len(licences) == 1, (compartment, licences)


def test_assert_analytics_separated_refuses_two_licences_in_one_compartment() -> None:
    from policy.licensing import LicenseIncompatibilityError

    with pytest.raises(LicenseIncompatibilityError, match="web"):
        assert_analytics_separated(
            [
                AnalyticsArtifact(
                    path=f"{ANALYTICS_DIR}/a.json",
                    compartment="web",
                    license="CC-BY-4.0",
                    payload={},
                ),
                AnalyticsArtifact(
                    path=f"{ANALYTICS_DIR}/b.json",
                    compartment="web",
                    license="ODbL-1.0",
                    payload={},
                ),
            ]
        )


# --- centrality + focus --------------------------------------------------------


def _m_edges(*edges: tuple[str, str, str]) -> list[dict]:
    return [
        {"from_entity": a, "to_entity": b, "access_kind": kind, "evidence_claim": f"c{i}"}
        for i, (a, b, kind) in enumerate(edges)
    ]


def test_centrality_is_degree_over_the_typed_access_edges() -> None:
    export = _export(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        materialized={
            "materialized_edges": _m_edges(
                ("e1", "e2", "observed_use"),
                ("e1", "e3", "configured_access"),
                ("e1", "e2", "observed_use"),  # a duplicate undirected pair counts once
                ("e4", "e5", "commercial_sale"),  # NOT a typed access kind — excluded
            )
        },
    )
    payload = _analytic(export, "centrality")
    assert "degree" in payload["measure"]
    stats = {s["node_id"]: s for s in payload["statistics"]}
    assert stats["e1"]["value"] == 2
    assert stats["e2"]["value"] == 1
    assert stats["e3"]["value"] == 1
    assert "e4" not in stats and "e5" not in stats
    # The focus rule is named and deterministic (max degree, lexical tie-break).
    assert payload["focus"]["entity_id"] == "e1"
    assert payload["focus"]["degree"] == 2
    assert payload["focus"]["rule"]
    assert "2 typed access edges" in payload["denominator"]


def test_centrality_stats_carry_the_disclosure_not_a_fabricated_er_eval() -> None:
    export = _export(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        materialized={"materialized_edges": _m_edges(("e1", "e2", "observed_use"))},
    )
    for stat in _analytic(export, "centrality")["statistics"]:
        # er_quality is the HONEST null — the stat does not rest on a probabilistic
        # ER eval — with the inline disclosure saying so (SIG-UI-023).
        assert stat["er_quality"] is None
        assert stat["disclosure"]


def test_centrality_focus_tie_resolves_lexically() -> None:
    export = _export(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        materialized={
            "materialized_edges": _m_edges(
                ("zz", "b", "observed_use"),
                ("aa", "b", "configured_access"),
                ("aa", "zz", "declared_policy"),
            )
        },
    )
    payload = _analytic(export, "centrality")
    # All three nodes have degree 2 → the lexically smallest id wins.
    assert payload["focus"]["entity_id"] == "aa"


def test_centrality_empty_state_is_honest() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    payload = _analytic(export, "centrality")
    assert payload["statistics"] == []
    assert payload["focus"] == {"entity_id": None, "degree": None, "rule": payload["focus"]["rule"]}
    assert payload["is_population_total"] is False


# --- the watch decision point ---------------------------------------------------


def _watch_row(subject: str, label: str, termination: dict) -> dict:
    return {"subject_id": subject, "subject_label": label, "termination": termination}


def test_decision_point_is_the_earliest_derivable_watch_date() -> None:
    export = _export(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "contract_watch": [
                _watch_row(
                    "s1",
                    "Contract 1",
                    {"expiry_date": "2027-06-30", "auto_renews": True, "notice_window_days": 90},
                ),
                _watch_row(
                    "s2",
                    "Contract 2",
                    {"expiry_date": "2027-01-31", "auto_renews": False, "notice_window_days": None},
                ),
                _watch_row("s3", "Contract 3", {"expiry_date": None}),
            ]
        },
    )
    payload = _analytic(export, "decision_point")
    dp = payload["decision_point"]
    assert dp is not None
    # SIG-UI-014b: s1 auto-renews → expiry − notice = 2027-04-01; s2 does not → the
    # expiry itself 2027-01-31; s3 has no expiry → no derivable date. Earliest wins.
    assert dp["date"] == "2027-01-31"
    assert dp["subject_id"] == "s2"
    assert dp["label"] == "Contract 2"
    assert payload["rule"]
    assert "3 contracts" in payload["denominator"]


def test_decision_point_is_none_when_no_watch_item_carries_a_derivable_date() -> None:
    export = _export(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"contract_watch": [_watch_row("s1", "C", {"expiry_date": None})]},
    )
    payload = _analytic(export, "decision_point")
    assert payload["decision_point"] is None
    assert payload["is_population_total"] is False


def test_decision_point_derivation_matches_the_web_wire_contract() -> None:
    # The date is DERIVED (never a stored next_decision_date, SIG-UI-014b): the
    # web's resolveTermination/nextDecisionDate computes expiry − notice for an
    # auto-renewing contract; this artifact must not drift from it.
    export = _export(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "contract_watch": [
                _watch_row(
                    "s1",
                    "Contract 1",
                    {"expiry_date": "2027-06-30", "auto_renews": True, "notice_window_days": 90},
                )
            ]
        },
    )
    assert _analytic(export, "decision_point")["decision_point"]["date"] == "2027-04-01"


# --- provenance + queue meta -----------------------------------------------------


def test_provenance_carries_the_three_surfaces_and_the_wtier_distribution() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _export(claims)
    payload = _analytic(export, "provenance")
    assert set(payload["surfaces"]) == {"site", "corrections", "research_queue"}
    site = payload["surfaces"]["site"]
    # The real §10.6 evidence-tier analytics over the publishable claims —
    # R1/D1/I1 claims still-current at as_of → W4 (dispositive).
    assert site["tier_distribution"] == {"W4": len(claims)}
    assert site["source_independence_count"] == 2  # src_a + fr_src
    assert site["date_range"] == {"earliest": "2026-05-01", "latest": "2026-05-01"}
    assert site["rules_applied"] == ["ruleset/1"]
    assert site["human_review_status"] == "unreviewed"


def test_provenance_wtiers_follow_the_ordinal_composition_and_d6_is_untiered() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    # §10.6 ordinal table: R1/D1/I1 → W4; R4/D1/I1 → W2; D6 is non-probative —
    # excluded from the admissible set, counted honestly as ``untiered``.
    axes = {
        claims[0].claim_id: ("R4", "D1", "I1"),  # → W2
        claims[1].claim_id: ("R1", "D6", "I1"),  # → untiered (D6 excluded)
    }
    site = _analytic(_export(claims, weight_axes=axes), "provenance")["surfaces"]["site"]
    assert site["tier_distribution"] == {"W4": 4, "W2": 1, "untiered": 1}


def test_provenance_marks_human_review_when_the_review_materialization_says_so() -> None:
    export = _export(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        site_runs=[{"summary": {"human_review": {"verdict_pairs": 2}}}],
    )
    assert (
        _analytic(export, "provenance")["surfaces"]["site"]["human_review_status"]
        == "partially_reviewed"
    )


def test_provenance_corrections_and_queue_surfaces_are_honest_when_empty() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    payload = _analytic(export, "provenance")
    assert payload["surfaces"]["corrections"]["artifact_count"] == 0
    assert payload["surfaces"]["research_queue"]["artifact_count"] == 0


def test_queue_meta_is_honest_about_the_claim_spines_jurisdiction_gap() -> None:
    export = _export(_site("A", "35.46", "-97.51", "Oklahoma"))
    payload = _analytic(export, "queue_meta")
    assert payload["jurisdiction_claims"] == []
    assert payload["queue_as_of"] == "2026-09-22"
    assert "does not carry" in payload["denominator"]


# --- build_analytics surface licence computation (the producer seam) -------------


def test_build_analytics_labels_density_like_map_json() -> None:
    """The producer takes the same ``licences_by_subject`` map.json draws on."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    dataset, raw, _ = _build_dataset(claims)
    artifacts = build_analytics(
        dataset,
        raw,
        licences_by_subject={"A": {"ODbL-1.0"}},
        refused_subjects=set(),
        ruleset_version="ruleset/1",
    )
    paths = {a.path: a for a in artifacts}
    assert paths[f"{ANALYTICS_DIR}/density_bins.json"].license == "ODbL-1.0"
    # The non-CC-BY label lands the file in the restricted web_mixed partition.
    assert paths[f"{ANALYTICS_DIR}/density_bins.json"].compartment == "web_mixed"
