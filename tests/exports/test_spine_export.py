# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the spine-backed national export (P27.4, LAUNCH.4).

Pure tests over fabricated shaping rows — no database. The DB-backed seeded-spine
end-to-end lives in ``tests/db/test_spine_export_over_seeded_spine.py``. These tests
prove: the ten P27.1 web surfaces match the FROZEN contract; the fail-closed licence
gate holds (ODbL apart from CC-BY, refused records dropped loudly); per-source site
slices recompute their own envelopes (never a silent cross-source merge); honest
absence for empty spine tables; PMTiles per compartment; and byte-determinism.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import jsonschema
from exports.compartments import assert_separated
from exports.manifest import BuildSpec
from exports.provo import validate_prov_graph
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import (
    NOT_YET_CLASSIFIED,
    build_spine_export,
    contradictions_visible_metric,
    resolved_site_counts,
    resolved_sites_metric,
    surface_license,
)
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, XSD
from support import REPO_ROOT
from tasks.vocabulary import Disposition

SCHEMA = json.loads(
    (REPO_ROOT / "docs" / "build" / "reports" / "public_surface_contracts.schema.json").read_text(
        encoding="utf-8"
    )
)
_DEFS = SCHEMA["$defs"]


def _sub(node: dict) -> dict:
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": _DEFS, **node}


def _claim(
    cid: str,
    sid: str,
    pred: str,
    *,
    value_text: str | None = None,
    source_id: str = "src_a",
    spdx: str = "ODbL-1.0",
    redistributable: str = "yes",
    derivative_permitted: str = "yes",
    tier: int = 0,
) -> ShapingClaim:
    return ShapingClaim(
        claim_id=cid,
        subject_id=sid,
        predicate_id=pred,
        value_kind="value",
        value_text=value_text,
        value_num=None,
        raw_value=value_text or "",
        observed_at=date(2026, 5, 1),
        sensitivity_tier=tier,
        source_id=source_id,
        connector_name="camreg",
        effective_rights_id=f"rights-{spdx}-{redistributable}-{derivative_permitted}",
        effective_spdx=spdx,
        effective_redistributable=redistributable,
        effective_derivative_permitted=derivative_permitted,
        effective_attribution=f"© {source_id}",
        effective_terms_url="https://example/terms",
    )


def _site(
    subject: str,
    lat: str,
    lon: str,
    juris: str,
    *,
    source_id: str = "src_a",
    spdx: str = "ODbL-1.0",
    **over: str,
) -> list[ShapingClaim]:
    return [
        _claim(
            f"{subject}-{source_id}-lat",
            subject,
            "camera_latitude",
            value_text=lat,
            source_id=source_id,
            spdx=spdx,
            **over,
        ),
        _claim(
            f"{subject}-{source_id}-lon",
            subject,
            "camera_longitude",
            value_text=lon,
            source_id=source_id,
            spdx=spdx,
            **over,
        ),
        _claim(
            f"{subject}-{source_id}-jur",
            subject,
            "camera_jurisdiction",
            value_text=juris,
            source_id=source_id,
            spdx=spdx,
            **over,
        ),
    ]


def _rows(claims: list[ShapingClaim]) -> list[tuple]:
    return [
        (
            c.claim_id,
            c.subject_id,
            c.predicate_id,
            c.value_kind,
            c.value_text,
            c.value_num,
            c.raw_value,
            c.observed_at,
            c.sensitivity_tier,
            c.source_id,
            c.connector_name,
            c.occurrence_capture_id,
            c.occurrence_retrieved_at,
            c.occurrence_bound_at,
            c.effective_rights_id,
            c.effective_spdx,
            c.effective_redistributable,
            c.effective_derivative_permitted,
            c.effective_attribution,
            c.effective_terms_url,
        )
        for c in claims
    ]


def _build(
    claims: list[ShapingClaim],
    raw_over: dict | None = None,
    dossier_packets: list[dict] | None = None,
):
    rows = _rows(claims)
    subjects = sorted({c.subject_id for c in claims})
    raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    dataset = build_shaped_dataset(
        raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )
    bs = BuildSpec(
        as_of_snapshot=date(2026, 9, 22),
        as_of_belief=date(2026, 9, 22),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
    )
    return build_spine_export(
        dataset,
        raw_over or {},
        build_spec=bs,
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
        dossier_packets=dossier_packets,
    )


def _web(export, name: str):
    return json.loads(export.web_artifacts[f"web/{name}.json"].decode("utf-8"))


# --- the ten P27.1-contract surfaces ---------------------------------------- #


def test_ten_web_surfaces_match_the_frozen_contract() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    property_for = {
        "dossier_index": "dossier_index",
        "map": "map_layer",
        "network": "network",
        "freshness": "data_freshness",
        "coverage": "coverage",
        "watch": "watch",
        "evidence": "evidence",
        "corrections": "corrections",
        "research_queue": "research_queue",
    }
    for name, key in property_for.items():
        jsonschema.validate(_web(export, name), _sub(SCHEMA["properties"][key]))
    for dossier in _web(export, "dossiers"):
        jsonschema.validate(dossier, _sub(_DEFS["Dossier"]))


def test_dossier_has_twelve_sections_and_first_class_gaps() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    dossier = _web(export, "dossiers")[0]
    assert [s["section_id"] for s in dossier["sections"]] == [
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
    ]
    # P32.17 (SIG-DOS-001): dossier gaps are evidence-backed field states — an
    # empty spine emits NO gap row (the hardcoded generic "Data-sharing
    # partners / NOT_RESEARCHED" row is gone; nothing is fabricated).
    assert dossier["gaps"] == []


def test_dossier_gaps_are_evidence_backed_coverage_states() -> None:
    """P32.17: negative-space coverage_record rows become the dossier's gaps —
    absence kind + named searched sources, attributed to their jurisdiction by
    subject or by entity label. Nothing else mints a gap."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    coverage = [
        {
            "coverage_id": "cov-1",
            "subject_id": "A",
            "subject_class": "deployment",
            "jurisdiction_id": None,
            "predicate_id": "retention_period",
            "absence_kind": "searched_not_found",
            "sources_searched": ["vendor portal", "council minutes"],
            "metric_method": None,
            "metric_label": None,
            "numerator": None,
            "denominator": None,
            "not_evaluable": None,
            "named_denominator": None,
            "metric_value": None,
        },
        {
            # An unresearched gap on the OTHER jurisdiction must not leak.
            "coverage_id": "cov-2",
            "subject_id": "B",
            "subject_class": "deployment",
            "jurisdiction_id": None,
            "predicate_id": "sharing_partners",
            "absence_kind": "not_researched",
            "sources_searched": None,
            "metric_method": None,
            "metric_label": None,
            "numerator": None,
            "denominator": None,
            "not_evaluable": None,
            "named_denominator": None,
            "metric_value": None,
        },
        {
            # A metric row is not a gap.
            "coverage_id": "cov-3",
            "subject_id": "A",
            "subject_class": "deployment",
            "jurisdiction_id": None,
            "predicate_id": "claimed_device_count",
            "absence_kind": None,
            "sources_searched": None,
            "metric_method": "counted_records",
            "metric_label": "sites",
            "numerator": 2.0,
            "denominator": 5.0,
            "not_evaluable": None,
            "named_denominator": "registry rows",
            "metric_value": None,
        },
    ]
    export = _build(claims, {"materialized_coverage": coverage})
    okc = next(d for d in _web(export, "dossiers") if d["jurisdiction"] == "Oklahoma")
    assert okc["gaps"] == [
        {
            "label": "retention period",
            "kind": "NO_EVIDENCE_FOUND",
            "subject_id": "A",
            "predicate_id": "retention_period",
            "note": "Recorded negative-space coverage finding (§32.1).",
            "sources_searched": ["vendor portal", "council minutes"],
        }
    ]
    paris = next(d for d in _web(export, "dossiers") if d["jurisdiction"] == "Paris")
    assert paris["gaps"] == [
        {
            "label": "sharing partners",
            "kind": "NOT_RESEARCHED",
            "subject_id": "B",
            "predicate_id": "sharing_partners",
            "note": "Recorded negative-space coverage finding (§32.1).",
        }
    ]


def test_dossier_action_blocks_are_full_shape_and_explicitly_unknown() -> None:
    # P30.3: `{}` rendered auto-renewal as "no" (a fabricated fact) and crashed the print
    # page on `disclosure_duties.length`; every field is now present and explicitly unknown.
    (d, *_) = _web(_build(_site("A", "35.46", "-97.51", "Oklahoma")), "dossiers")
    assert d["authorization"] == {
        "approving_body": None,
        "vote": None,
        "consent_agenda": None,
        "public_comment": None,
        "date": None,
    }
    assert d["termination"] == {
        "auto_renews": None,
        "notice_window_days": None,
        "expiry_date": None,
    }
    assert d["legal_regime"] == {
        "state_statute": None,
        "local_ordinance": None,
        "disclosure_duties": [],
    }


def test_map_location_absence_uses_the_web_absence_vocabulary() -> None:
    # P30.3: "conflicted"/"no_resolved_point" are not §9.5 absence kinds — the national
    # /map/ build crashed looking them up. Pinned to web `epistemic.ts#ABSENCE_KINDS`.
    kinds = {"NOT_RESEARCHED", "NO_EVIDENCE_FOUND", "EVIDENCE_OF_ABSENCE", "UNRESOLVED"}
    point_less = [_claim("N-jur", "N", "camera_jurisdiction", value_text="Oklahoma")]
    conflicted = [
        _claim("C-lat1", "C", "camera_latitude", value_text="35.1"),
        # P32.4: a same-source re-observation supersedes — a real conflict needs
        # two independent sources to stay concurrent candidates (ADR-123).
        _claim("C-lat2", "C", "camera_latitude", value_text="36.9", source_id="src_b"),
        _claim("C-lon", "C", "camera_longitude", value_text="-97.5"),
        _claim("C-jur", "C", "camera_jurisdiction", value_text="Oklahoma"),
    ]
    assets = {a["id"]: a for a in _web(_build(point_less + conflicted), "map")["assets"]}
    assert assets["N"]["locationAbsence"] == "NO_EVIDENCE_FOUND"
    assert assets["C"]["locationAbsence"] == "UNRESOLVED"
    assert all(a.get("locationAbsence", "UNRESOLVED") in kinds for a in assets.values())


def test_dossier_slugs_are_unique_across_jurisdictions() -> None:
    claims = (
        _site("A", "35.46", "-97.51", "Oklahoma")
        + _site("B", "40.71", "-74.0", "New York")
        + _site("C", "41.0", "-73.0", "unresolved")
    )
    export = _build(claims)
    slugs = [d["slug"] for d in _web(export, "dossiers")]
    assert len(slugs) == len(set(slugs))  # deduped/deterministic
    assert _web(export, "dossier_index")  # index mirrors the dossiers


def test_coverage_never_publishes_a_population_total() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    for metric in _web(export, "coverage"):
        assert metric["is_population_total"] is False
        assert metric["denominator"]  # a NAMED denominator, never a bare total


# --- the fail-closed licence gate ------------------------------------------- #


def test_odbl_and_ccby_land_in_separate_compartments() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma", source_id="osm", spdx="ODbL-1.0") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    by_comp = {}
    for pt in export.bundle.placed:
        if pt.table.name == "sites":
            by_comp[pt.compartment] = pt.license
    assert by_comp.get("osm_physical") == "ODbL-1.0"
    assert by_comp.get("sig_graph") == "CC-BY-4.0"
    # The separation invariant holds across the whole release.
    assert_separated(export.bundle.placed)
    # Physically different files.
    paths = set(export.bundle.artifact_bytes)
    assert "osm_physical/sites.geojson" in paths
    assert "sig_graph/sites.geojson" in paths


def test_refused_record_is_dropped_loudly_not_comingled() -> None:
    # Publishable (redistributable=yes, tier 0) but derivative-forbidden → the export
    # gate refuses it; it must be dropped into the exclusions report, not shipped.
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "R",
        "10.0",
        "10.0",
        "Nowhere",
        source_id="nd",
        spdx="CC-BY-4.0",
        derivative_permitted="no",
    )
    export = _build(claims)
    assert export.exclusions["totals"]["refused_slices"] == 1
    refused = export.exclusions["refused"][0]
    assert refused["source_id"] == "nd"
    assert refused["reason"] == "derivative_permitted=false"
    # The refused subject appears in NO shipped site row.
    for pt in export.bundle.placed:
        if pt.table.name == "sites":
            assert all(r.data["entity_id"] != "R" for r in pt.table.rows)


def test_undetermined_record_is_refused() -> None:
    # An UNDETERMINED-licence record that is still marked redistributable is refused
    # by the export gate (SIG-LIC-004), dropped loudly.
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "U",
        "20.0",
        "20.0",
        "Nowhere",
        source_id="ud",
        spdx="UNDETERMINED",
    )
    export = _build(claims)
    reasons = {e["reason"] for e in export.exclusions["refused"]}
    assert "UNDETERMINED" in reasons


def test_a_source_with_two_rights_records_is_sliced_per_rights_never_merged() -> None:
    # P30.3 (hosted finding, dot_511_ky): ONE source whose claims carry two effective rights
    # records under different licences (CC0 rows + decision-resolved public-record rows). The
    # per-source rights index used to keep only the first record, so the second licence's
    # compartment table computed a CC0+PublicRecord mix and the fail-closed gate stopped the
    # build. Each (source, rights) slice is now placed + attributed by its OWN record.
    cc0 = _site("K1", "38.2", "-85.7", "Kentucky", source_id="dot_ky", spdx="CC0-1.0")
    pr = _site(
        "K2",
        "38.3",
        "-85.8",
        "Kentucky",
        source_id="dot_ky",
        spdx="LicenseRef-PublicRecord-FactualCompilation",
    )
    export = _build(cc0 + pr)
    by_comp = {pt.compartment: pt for pt in export.bundle.placed if pt.table.name == "sites"}
    # CC0 is placed under its most-constraining relicensable target (policy.licensing), the
    # CC-BY-SA-4.0 `portal` compartment — the point is it is NOT merged with public_record.
    assert by_comp["portal"].license == "CC-BY-SA-4.0"
    assert by_comp["public_record"].license == "LicenseRef-PublicRecord-FactualCompilation"
    assert {r.data["entity_id"] for r in by_comp["portal"].table.rows} == {"K1"}
    assert {r.data["entity_id"] for r in by_comp["public_record"].table.rows} == {"K2"}
    # the rows still carry the TRUE source id; only the placement key is per-slice
    for pt in by_comp.values():
        assert {r.data["source_id"] for r in pt.table.rows} == {"dot_ky"}
    assert_separated(export.bundle.placed)


def test_a_single_rights_source_keeps_its_plain_source_key() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma", source_id="osm"))
    rows = [r for pt in export.bundle.placed if pt.table.name == "sites" for r in pt.table.rows]
    assert {r.source_id for r in rows} == {"osm"}


def test_map_surface_is_labelled_with_every_licence_it_draws_on() -> None:
    # ADR-106: the map render surface carries every published subject's own point, so an
    # ODbL + CC-BY mix is labelled as BOTH (a mixed-licence artifact the public classifier
    # keeps out of every public object); the aggregate surfaces stay SIG CC-BY-4.0.
    claims = _site("A", "35.46", "-97.51", "Oklahoma", source_id="osm", spdx="ODbL-1.0") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr", spdx="CC-BY-4.0"
    )
    arts = {a.path: a for a in _build(claims).manifest.artifacts}
    assert arts["web/map.json"].license == "CC-BY-4.0 AND ODbL-1.0"
    assert arts["web/coverage.json"].license == "CC-BY-4.0"
    assert arts["web/dossiers.json"].license == "CC-BY-4.0"


def test_a_single_licence_map_surface_carries_that_licence() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma", source_id="osm", spdx="ODbL-1.0"))
    arts = {a.path: a for a in export.manifest.artifacts}
    assert arts["web/map.json"].license == "ODbL-1.0"


def test_a_refused_subject_never_reaches_the_map_surface() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "R", "10.0", "10.0", "Nowhere", source_id="nd", spdx="CC-BY-4.0", derivative_permitted="no"
    )
    export = _build(claims)
    assert {a["id"] for a in _web(export, "map")["assets"]} == {"A"}
    assert export.exclusions["totals"]["refused_slices"] == 1


def test_surface_license_labels() -> None:
    assert surface_license(set()) == "CC-BY-4.0"
    assert surface_license({"ODbL-1.0"}) == "ODbL-1.0"
    assert surface_license({"ODbL-1.0", "CC0-1.0"}) == "CC0-1.0 AND ODbL-1.0"


def test_per_source_slice_recomputes_its_own_envelope() -> None:
    # Two sources disagree on the coordinate of the SAME subject. The aggregate site
    # is conflicted (null point), but each source's slice keeps ITS OWN resolved point
    # — proof the slice envelope is recomputed per source, never a silent merge.
    claims = _site("X", "35.46", "-97.51", "Oklahoma", source_id="osm", spdx="ODbL-1.0") + _site(
        "X", "36.00", "-98.00", "Oklahoma", source_id="cc", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    # aggregate site is conflicted → no picked point in the map surface
    asset_x = next(a for a in _web(export, "map")["assets"] if a["id"] == "X")
    assert asset_x["lat"] is None
    # each per-source slice has its own Point geometry
    geoms = {}
    for pt in export.bundle.placed:
        if pt.table.name == "sites":
            for r in pt.table.rows:
                if r.data["entity_id"] == "X":
                    geoms[r.data["source_id"]] = r.data["geometry"]
    assert geoms["osm"] == {"type": "Point", "coordinates": [-97.51, 35.46]}
    assert geoms["cc"] == {"type": "Point", "coordinates": [-98.0, 36.0]}


# --- honest absence --------------------------------------------------------- #


def test_empty_supplementary_surfaces_emit_honest_absence() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    assert _web(export, "watch") == []
    assert _web(export, "corrections") == []
    assert _web(export, "research_queue") == []
    assert _web(export, "evidence") == {"artifacts": [], "claim_views": []}
    # network: no classifiable sharing edges → honest empty typed network.
    assert _web(export, "network")["edges"] == []


def test_supplementary_rows_flow_through_when_present() -> None:
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "research_tasks": [
                (
                    "t1",
                    "geolocate_devices",
                    "subjX",
                    "jurY",
                    5.0,
                    "generated",
                    None,
                    "≥1 coordinate claim exists for subjX",
                    "det/1",
                ),
            ],
        },
    )
    queue = _web(export, "research_queue")
    assert len(queue) == 1
    assert queue[0]["closing_condition"] == "≥1 coordinate claim exists for subjX"
    jsonschema.validate(queue, _sub(SCHEMA["properties"]["research_queue"]))


# --- P34.12 (K11 RQ-00 / C3 NEW-10): catalog-true queue shaping --------------- #


def test_research_queue_card_carries_task_id_and_catalog_classification() -> None:
    """A task whose type IS in the §33.2 catalog gets the catalog's assignee
    class, effort estimate, geographic scope and permitted dispositions — plus
    its own `task_id` (the export used to discard it and invent
    `contributor`/`unknown`/`[]` placeholders)."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "research_tasks": [
                (
                    "task-0001",
                    "missing_physical_devices",
                    "agency:okc",
                    "Oklahoma City",
                    5.0,
                    "generated",
                    None,
                    "The mapped-device count reaches the active-device count.",
                    "det/1",
                ),
            ],
        },
    )
    queue = _web(export, "research_queue")
    assert len(queue) == 1
    card = queue[0]
    assert card["task_id"] == "task-0001"
    assert card["assignee_class"] == "field_mapper"  # catalog row, not "contributor"
    assert card["effort_estimate"] == "moderate"  # catalog row, not "unknown"
    # the SCOPE vocabulary, not the jurisdiction name
    assert card["geographic_scope"] == "jurisdiction"
    assert card["jurisdiction"] == "Oklahoma City"
    vocabulary = {d.value for d in Disposition}
    assert card["dispositions"], "dispositions must never be []"
    assert set(card["dispositions"]) <= vocabulary
    # SIG-TASK-009's searched-found-nothing outcome stays reachable.
    assert "resolved_no_evidence_exists" in card["dispositions"]
    jsonschema.validate(queue, _sub(SCHEMA["properties"]["research_queue"]))


def test_research_queue_unclassified_type_is_honestly_not_yet_classified() -> None:
    """A task whose type the catalog does not know (legacy/hand-inserted row)
    emits `not yet classified` — never an invented class — and the FULL §33.4
    disposition vocabulary, since every outcome is legal for it."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "research_tasks": [
                (
                    "task-0002",
                    "geolocate_devices",  # not a §33.2 catalog slug
                    "subjX",
                    "jurY",
                    5.0,
                    "generated",
                    None,
                    "≥1 coordinate claim exists for subjX",
                    "det/1",
                    "contradiction",
                    "trigger-9",
                ),
            ],
        },
    )
    card = _web(export, "research_queue")[0]
    assert card["task_id"] == "task-0002"
    assert card["assignee_class"] == NOT_YET_CLASSIFIED == "not yet classified"
    assert card["effort_estimate"] == NOT_YET_CLASSIFIED
    assert card["geographic_scope"] == NOT_YET_CLASSIFIED
    assert card["jurisdiction"] == "jurY"
    assert set(card["dispositions"]) == {d.value for d in Disposition}
    # The trigger citation (P29.2) survives the reshape.
    assert card["trigger"] == {"kind": "contradiction", "ref": "trigger-9"}
    jsonschema.validate(
        _web(export, "research_queue"), _sub(SCHEMA["properties"]["research_queue"])
    )


def test_research_queue_never_emits_the_retired_placeholders() -> None:
    """Whatever the rows carry, `contributor` and `unknown` can never come back
    as assignee/effort values (NEW-10)."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "research_tasks": [
                (
                    "task-0003",
                    "missing_physical_devices",
                    "s1",
                    None,
                    1.0,
                    "generated",
                    None,
                    "closing",
                    "det/1",
                ),
                (
                    "task-0004",
                    "geolocate_devices",
                    "s2",
                    None,
                    2.0,
                    "generated",
                    None,
                    "closing",
                    "d/2",
                ),
            ],
        },
    )
    for card in _web(export, "research_queue"):
        assert card["assignee_class"] != "contributor"
        assert card["effort_estimate"] != "unknown"
        assert card["dispositions"] != []
        # A missing jurisdiction is honestly unscoped — the filter labels it.
        assert card["jurisdiction"] == ""


def test_corrections_entry_names_both_assertions_and_gates_the_prior() -> None:
    """P32.16a (SIG-FIND-008): the log names old + new claim ids; a gated prior
    surfaces as the withheld tombstone — its value/date never re-published."""
    recorded = datetime(2026, 9, 20, tzinfo=UTC)
    old_belief = datetime(2026, 5, 1, tzinfo=UTC)
    corr_row = (
        "new-claim-1",  # c.claim_id
        "A",  # c.subject_id
        "camera_count",  # c.predicate_id
        "225",  # c.raw_value (the corrected value)
        "verified against the cited contract",  # c.correction_reason
        "old-claim-1",  # c.revises_claim
        None,  # c.retraction_of
        recorded,  # lower(c.sys_period)
        "old-claim-1",  # oc.claim_id
        "213",  # oc.raw_value
        old_belief,  # lower(oc.sys_period)
        True,  # old_eligible — the prior row is itself publicly eligible
    )
    gated_row = (
        "new-claim-2",
        "A",
        "camera_model",
        "AXIS Q3527",
        "safety withdrawal reviewed",
        None,
        "old-claim-2",  # a retraction entry
        recorded,
        "old-claim-2",
        "withheld-model",
        old_belief,
        False,  # the prior row is gated → withheld tombstone, never the value
    )
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"corrections": [corr_row, gated_row]},
    )
    log = {e["id"]: e for e in _web(export, "corrections")}
    rev = log["new-claim-1"]
    assert rev["category"] == "revision"
    assert rev["previous_claim_id"] == "old-claim-1"
    assert rev["revises_claim"] == "old-claim-1"
    assert rev["previous_value"] == "213"
    assert rev["corrected_value"] == "225"
    assert rev["previous_belief_date"] == "2026-05-01"
    assert rev["previous_withheld"] is False
    ret = log["new-claim-2"]
    assert ret["category"] == "retraction" and ret["retraction_of"] == "old-claim-2"
    assert ret["previous_withheld"] is True
    assert ret["previous_value"] == "" and ret["previous_belief_date"] == ""
    jsonschema.validate(list(log.values()), _sub(SCHEMA["properties"]["corrections"]))


# --- tiles, manifest, provenance, determinism ------------------------------- #


def test_pmtiles_rendered_per_compartment() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma", source_id="osm", spdx="ODbL-1.0") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr", spdx="CC-BY-4.0"
    )
    export = _build(claims)
    assert "web/tiles/osm_physical-sites.pmtiles" in export.web_artifacts
    assert "web/tiles/sig_graph-sites.pmtiles" in export.web_artifacts
    assert export.web_artifacts["web/tiles/osm_physical-sites.pmtiles"][:7] == b"PMTiles"
    # the ODbL tile is licensed ODbL in the extended manifest
    osm_tile = next(
        a for a in export.manifest.artifacts if a.path == "web/tiles/osm_physical-sites.pmtiles"
    )
    assert osm_tile.license == "ODbL-1.0" and osm_tile.compartment == "osm_physical"


def test_a_share_alike_tile_is_filed_under_its_own_compartment() -> None:
    # ADR-106: a CC-BY-SA-4.0 tile was labelled `sig_graph` (the old ODbL-else-sig_graph
    # rule); it is now filed under the compartment its sites were placed in.
    claims = _site("P", "40.0", "-75.0", "Somewhere", source_id="portal", spdx="CC-BY-SA-4.0")
    export = _build(claims)
    tile = next(a for a in export.manifest.artifacts if a.path.endswith("-sites.pmtiles"))
    assert (tile.compartment, tile.license) == ("portal", "CC-BY-SA-4.0")


def test_manifest_extends_bundle_with_web_and_provenance_checksums() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    paths = {a.path for a in export.manifest.artifacts}
    assert "provenance.ttl" in paths
    assert "exclusions.json" in paths
    assert "web/map.json" in paths
    # every artifact carries a checksum + compartment + licence (SIG-EXPORT-001/006)
    for a in export.manifest.artifacts:
        assert a.sha256 and a.compartment and a.license


def test_provenance_is_valid_prov_o() -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    graph = Graph()
    graph.parse(data=export.provenance.decode("utf-8"), format="nt")
    validate_prov_graph(graph)  # raises if the SIG-INGEST-016 mapping is breached


_PROV = "https://surveillancegraph.org/prov/"
_PROV_NS = "http://www.w3.org/ns/prov#"


def _binding_detail(
    claim_id: str,
    *,
    capture_id: str,
    artifact_id: str,
    artifact_source_id: str,
    retrieved_at: str,
    run_id: str,
    connector_name: str,
    connector_version: str,
    run_started: str,
    run_finished: str,
) -> tuple:
    """One ``claim_binding_detail`` row (the EXPORT_QUERIES column order —
    ``statements.BINDING_DETAIL_COLUMNS``)."""
    from exports.statements import BINDING_DETAIL_COLUMNS

    row = {c: None for c in BINDING_DETAIL_COLUMNS}
    row.update(
        {
            "claim_id": claim_id,
            "capture_id": capture_id,
            "artifact_id": artifact_id,
            "role": "establishes",
            "binding_status": "bound_current",
            "bound_at": "2026-05-02T00:00:00+00:00",
            "extractor_version": "extractor/1.2",
            "retrieved_at": retrieved_at,
            "content_digest": "sha256:" + "ab" * 32,
            "byte_size": 0,
            "media_type": "text/html",
            "storage_tier": "public",
            "capture_classification": "synthetic",
            "retrieved_by_run_id": run_id,
            "artifact_url": None,
            "artifact_source_id": artifact_source_id,
            "acquisition_method": "http_get",
            "run_connector_name": connector_name,
            "run_connector_version": connector_version,
            "run_started_at": run_started,
            "run_finished_at": run_finished,
        }
    )
    return tuple(row[c] for c in BINDING_DETAIL_COLUMNS)


def test_provenance_stamps_real_capture_times_not_the_export_clock() -> None:
    """P35.38b (F5 PKG-09b): ``retrieved_at`` is the recorded retrieval instant —
    never ``generated_at`` — and each capture is generated by the run that
    actually retrieved it (the pre-fix defect stamped the export clock on every
    capture)."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="src_b", spdx="CC-BY-4.0"
    )
    detail = [
        _binding_detail(
            "A-src_a-lat",
            capture_id="cap-a",
            artifact_id="art-a",
            artifact_source_id="src_a",
            retrieved_at="2026-05-01T12:00:00+00:00",
            run_id="run-a",
            connector_name="camreg",
            connector_version="1.2",
            run_started="2026-05-01T11:59:00+00:00",
            run_finished="2026-05-01T12:01:00+00:00",
        ),
        _binding_detail(
            "B-src_b-lat",
            capture_id="cap-b",
            artifact_id="art-b",
            artifact_source_id="src_b",
            retrieved_at="2026-05-03T08:30:00+00:00",
            run_id="run-b",
            connector_name="frport",
            connector_version="2.0",
            run_started="2026-05-03T08:29:00+00:00",
            run_finished="2026-05-03T08:31:00+00:00",
        ),
    ]
    export = _build(claims, raw_over={"claim_binding_detail": detail})
    graph = Graph()
    graph.parse(data=export.provenance.decode("utf-8"), format="nt")
    validate_prov_graph(graph)

    gen = URIRef(f"{_PROV_NS}generatedAtTime")
    cap_a, cap_b = URIRef(f"{_PROV}capture/cap-a"), URIRef(f"{_PROV}capture/cap-b")
    run_a, run_b = URIRef(f"{_PROV}run/run-a"), URIRef(f"{_PROV}run/run-b")
    src_a, src_b = URIRef(f"{_PROV}source/src_a"), URIRef(f"{_PROV}source/src_b")

    # Every IRI the surface mints lives under the one declared base.
    for node in graph.subjects(RDF.type, None):
        assert str(node).startswith(_PROV), node

    # The capture instants are the recorded retrieved_at values — the export
    # clock (generated_at == 2026-09-22T00:00:00Z) never lands on a capture.
    assert (cap_a, gen, Literal("2026-05-01T12:00:00+00:00", datatype=XSD.dateTime)) in graph
    assert (cap_b, gen, Literal("2026-05-03T08:30:00+00:00", datatype=XSD.dateTime)) in graph
    for cap in (cap_a, cap_b):
        for _s, _p, o in graph.triples((cap, gen, None)):
            assert "2026-09-22" not in str(o)

    # Provenance edges: capture → its real run + its source; the export run
    # ``prov:used`` every bound capture; the ingest runs carry their own clock
    # and connector agent — never the export's.
    assert (cap_a, PROV.wasGeneratedBy, run_a) in graph
    assert (cap_b, PROV.wasGeneratedBy, run_b) in graph
    assert (cap_a, PROV.wasAttributedTo, src_a) in graph
    assert (cap_b, PROV.wasAttributedTo, src_b) in graph
    # The export run is the Activity that ``prov:used`` the captures.
    export_run = next(graph.subjects(PROV.used, cap_a), None)
    assert export_run is not None
    assert (export_run, PROV.used, cap_a) in graph
    assert (export_run, PROV.used, cap_b) in graph
    assert (run_a, PROV.wasAssociatedWith, URIRef(f"{_PROV}connector/camreg")) in graph
    assert (run_b, PROV.wasAssociatedWith, URIRef(f"{_PROV}connector/frport")) in graph
    assert (
        run_a,
        PROV.startedAtTime,
        Literal("2026-05-01T11:59:00+00:00", datatype=XSD.dateTime),
    ) in graph


def test_provenance_without_binding_rows_is_honest_absence() -> None:
    """A spine with no ``claim_binding_detail`` degrades to the source-agent +
    export-run skeleton — no fabricated capture entities."""
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    graph = Graph()
    graph.parse(data=export.provenance.decode("utf-8"), format="nt")
    validate_prov_graph(graph)

    entities = set(graph.subjects(RDF.type, PROV.Entity))
    assert entities == set()  # no captures without binding rows
    # …but the source agents + the export run still stand (the skeleton).
    assert (URIRef(f"{_PROV}source/src_a"), RDF.type, PROV.Agent) in graph


def test_export_is_byte_deterministic(tmp_path: Path) -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    e1 = _build(claims)
    e2 = _build(claims)
    assert e1.manifest.to_bytes() == e2.manifest.to_bytes()
    assert e1.provenance == e2.provenance
    assert e1.web_artifacts == e2.web_artifacts


def test_write_to_materialises_the_whole_export(tmp_path: Path) -> None:
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    export.write_to(tmp_path)
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "provenance.ttl").exists()
    assert (tmp_path / "exclusions.json").exists()
    assert (tmp_path / "web" / "map.json").exists()
    assert (tmp_path / "osm_physical" / "sites.geojson").exists()


# --- the CLI wiring (no DB) -------------------------------------------------- #


def test_cli_from_spine_requires_dsn(capsys) -> None:  # type: ignore[no-untyped-def]
    from exports.cli import main

    rc = main(["build", "--from-spine", "--out", "/tmp/x"])
    assert rc == 2
    assert "--dsn is required" in capsys.readouterr().out


def test_cli_from_spine_is_mutually_exclusive_with_jurisdiction(capsys) -> None:  # type: ignore[no-untyped-def]
    from exports.cli import main

    rc = main(
        [
            "build",
            "--from-spine",
            "--dsn",
            "postgresql://x",
            "--jurisdiction",
            "okc",
            "--out",
            "/tmp/x",
        ]
    )
    assert rc == 2
    assert "mutually exclusive" in capsys.readouterr().out


def test_cli_dsn_without_from_spine_errors(capsys) -> None:  # type: ignore[no-untyped-def]
    from exports.cli import main

    rc = main(["build", "req.json", "--dsn", "postgresql://x", "--out", "/tmp/x"])
    assert rc == 2
    assert "--dsn is only valid with --from-spine" in capsys.readouterr().out


# --- P28.5: refresh off the materialized graph (ADR-101) -------------------- #


def _materialized_raw(
    *,
    resolutions=None,
    edges=None,
    contradictions=None,
    coverage=None,
    accountability_links=None,
    site_runs=None,
) -> dict:
    return {
        "materialized_site_runs": site_runs or [],
        "materialized_resolutions": resolutions or [],
        "materialized_edges": edges or [],
        "materialized_contradictions": contradictions or [],
        "materialized_coverage": coverage or [],
        "materialized_accountability_links": accountability_links or [],
    }


def _acct_link(deployment_id, link_type, object_id, object_type, claims, **extra):
    return {
        "deployment_id": deployment_id,
        "predicate_id": f"accountability_link:{link_type}",
        "link_type": link_type,
        "chain_role": {
            "has_vendor": "vendor",
            "procured_under_contract": "contract",
            "funded_by": "funding",
            "governed_by_policy": "policy",
            "overseen_by": "oversight",
        }[link_type],
        "object_id": object_id,
        "object_type": object_type,
        "establishing_claims": claims,
        "confidence": "probable",
        "via_org": extra.get("via_org"),
        "via_contract": extra.get("via_contract"),
    }


def test_dossier_governance_chain_enriched_from_materialized_links() -> None:
    """P28.6 AC2: a dossier shows the deployment→vendor→contract→funding→policy→oversight
    chain where evidence exists (rows citing establishing claims), and honest gaps for the
    segments with none; an unmaterialized jurisdiction is left unchanged."""
    # A is a geolocated deployment in Oklahoma; B in Paris has NO governance links.
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site(
        "B", "48.85", "2.35", "Paris", source_id="fr_src", spdx="CC-BY-4.0"
    )
    links = [
        _acct_link(
            "A",
            "has_vendor",
            "ven1",
            "organization",
            ["c-op", "c-buy", "c-sell"],
            via_org="org1",
            via_contract="ct1",
        ),
        _acct_link(
            "A", "procured_under_contract", "ct1", "contract", ["c-op", "c-buy"], via_org="org1"
        ),
        _acct_link(
            "A", "funded_by", "fu1", "funding_instrument", ["c-op", "c-fund"], via_org="org1"
        ),
        _acct_link("A", "governed_by_policy", "pol1", "policy", ["c-pol"]),
        _acct_link("A", "overseen_by", "evt1", "accountability_event", ["c-evt"]),
    ]
    export = _build(claims, _materialized_raw(accountability_links=links))
    dossiers = _web(export, "dossiers")
    okc = next(d for d in dossiers if d["jurisdiction"] == "Oklahoma")
    paris = next(d for d in dossiers if d["jurisdiction"] == "Paris")

    # The full chain is present as a structured field, each segment evidenced.
    chain = okc["governance_chain"]["segments"]
    assert chain["vendor"]["status"] == "evidenced"
    assert chain["vendor"]["links"][0]["object_id"] == "ven1"
    assert chain["vendor"]["links"][0]["establishing_claims"] == ["c-op", "c-buy", "c-sell"]
    for role in ("vendor", "contract", "funding", "policy", "oversight"):
        assert chain[role]["status"] == "evidenced"

    # The chain rides the frozen Section/Row contract (no new IA) and every row cites claims.
    sections = {s["section_id"]: s for s in okc["sections"]}
    policy_rows = sections["policy"].get("rows", [])
    assert any(r["label"] == "Governing policy" and r["value"] == "pol1" for r in policy_rows)
    assert all("established by claim(s)" in r["note"] for r in policy_rows)
    events_rows = sections["accountability_events"].get("rows", [])
    assert any(r["label"] == "Oversight" and r["value"] == "evt1" for r in events_rows)

    # Paris has no attributed links → the dossier is unchanged (no governance_chain field).
    assert "governance_chain" not in paris


def test_dossier_governance_chain_honest_gap_when_a_segment_missing() -> None:
    """A jurisdiction with SOME links shows honest not_researched gaps for the missing ones."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    links = [_acct_link("A", "governed_by_policy", "pol1", "policy", ["c-pol"])]
    export = _build(claims, _materialized_raw(accountability_links=links))
    okc = next(d for d in _web(export, "dossiers") if d["jurisdiction"] == "Oklahoma")
    chain = okc["governance_chain"]["segments"]
    assert chain["policy"]["status"] == "evidenced"
    for role in ("vendor", "contract", "funding", "oversight"):
        assert chain[role]["status"] == "not_researched"
        assert chain[role]["links"] == []


def test_dossier_unchanged_without_materialized_links() -> None:
    """No accountability links → the dossier is byte-identical to today (honest degrade)."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    with_key = _build(claims, _materialized_raw())
    baseline = _build(claims, {})
    assert _web(with_key, "dossiers") == _web(baseline, "dossiers")
    assert all("governance_chain" not in d for d in _web(with_key, "dossiers"))


def _site_run(edges, *, proposed=0, m=0, n=0, human=(), refused=0, cannot_link=0):
    return {
        "run_key": "camsite:test",
        "observation_count": m,
        "cluster_count": n,
        "auto_write_tiers": [1, 3],
        "summary": {},
        "auto_write_edges": list(edges),
        "human_accept_edges": list(human),
        "resolved_edges": sorted(set(map(tuple, edges)) | set(map(tuple, human))),
        "proposed_count": proposed,
        "refused_count": refused,
        "cannot_link_count": cannot_link,
    }


def test_resolved_sites_metric_counts_post_er_clusters_of_the_same_device() -> None:
    # P30.2b / ADR-105: three observation-level records (A, B, C); the camera-site ER run
    # auto-wrote ONE same-device edge (A~B) and proposed one more (B~C, awaiting review).
    claims = (
        _site("A", "35.46", "-97.51", "Oklahoma")
        + _site("B", "35.46", "-97.51", "Oklahoma")
        + _site("C", "35.47", "-97.52", "Oklahoma")
    )
    export = _build(claims, _materialized_raw(site_runs=[_site_run([("A", "B")], proposed=1)]))
    coverage = _web(export, "coverage")
    resolved = next(m for m in coverage if m["id"] == "resolved_sites")
    # N = 2 clusters from M = 3 records: N <= M, dedup ratio 1 - N/M, never a total.
    assert resolved["value"] == (
        "2 resolved sites (from 3 observation-level records; dedup ratio 0.333)"
    )
    assert "observation-level sites" in resolved["denominator"]
    assert resolved["is_population_total"] is False
    assert "1 same-device merges were auto-written" in resolved["population_note"]
    assert "1 proposed merges still await review and are not counted" in resolved["population_note"]
    assert "0 were accepted in human review" in resolved["population_note"]
    assert "D-R6.1-EVAL" in resolved["population_note"]
    # The map layer flips to the resolved framing, one record's own point per asset.
    layers = _web(export, "map")["layers"]
    assert layers[0]["id"] == "resolved_sites"
    assert "2 resolved device sites" in layers[0]["description"]
    assert "from 3 observation-level records" in layers[0]["description"]
    # The whole coverage surface still validates against the FROZEN CoverageMetric contract.
    jsonschema.validate(coverage, _sub(SCHEMA["properties"]["coverage"]))


def test_resolved_sites_metric_counts_valid_human_accepts() -> None:
    # P31.11 / ADR-R9-HUMANER: a curator's accepted same-device edge joins a
    # resolved site exactly as an auto-written one does; rejects (cannot-link),
    # refused accepts and still-pending proposals are disclosed, never counted.
    claims = (
        _site("A", "35.46", "-97.51", "Oklahoma")
        + _site("B", "35.46", "-97.51", "Oklahoma")
        + _site("C", "35.47", "-97.52", "Oklahoma")
        + _site("D", "35.47", "-97.52", "Oklahoma")
    )
    run = _site_run([("A", "B")], human=[("C", "D")], proposed=2, refused=1, cannot_link=1, m=4)
    export = _build(claims, _materialized_raw(site_runs=[run]))
    resolved = next(m for m in _web(export, "coverage") if m["id"] == "resolved_sites")
    assert resolved["value"] == (
        "2 resolved sites (from 4 observation-level records; dedup ratio 0.500)"
    )
    assert "1 were accepted in human review" in resolved["population_note"]
    assert "2 proposed merges still await review" in resolved["population_note"]
    assert "1 reviewer rejects are recorded as cannot-link" in resolved["population_note"]
    assert "1 accepted merges were refused" in resolved["population_note"]


def test_value_decisions_are_never_counted_as_resolved_sites() -> None:
    # The P30.2a hazard, pinned: every site carries a §28 VALUE decision (a winning claim)
    # but no camera-site ER run has completed — that is NOT deduplication, so no
    # resolved-site metric is published (never "M resolved sites" from value decisions).
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site("B", "35.47", "-97.52", "Oklahoma")
    resolutions = [
        {"subject_id": s, "predicate_id": p, "resolved": True, "winning_claim": f"c-{s}-{p}"}
        for s in ("A", "B")
        for p in ("camera_latitude", "camera_longitude")
    ]
    export = _build(claims, _materialized_raw(resolutions=resolutions))
    assert not any(m["id"] == "resolved_sites" for m in _web(export, "coverage"))
    assert _web(export, "map")["layers"][0]["id"] == "observed_sites"


def test_an_honest_zero_merge_run_reports_n_equal_m() -> None:
    # An ER run that merged nothing is reported plainly (N = M, ratio 0.000), not hidden
    # and never inflated.
    claims = _site("A", "35.46", "-97.51", "Oklahoma") + _site("B", "35.47", "-97.52", "Oklahoma")
    export = _build(claims, _materialized_raw(site_runs=[_site_run([], proposed=4)]))
    resolved = next(m for m in _web(export, "coverage") if m["id"] == "resolved_sites")
    assert resolved["value"] == (
        "2 resolved sites (from 2 observation-level records; dedup ratio 0.000)"
    )


def test_no_materialized_resolution_degrades_to_observation_framing() -> None:
    # Empty materialized graph: no resolved-site metric, map keeps observation-level framing.
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    export = _build(claims, _materialized_raw())
    coverage = _web(export, "coverage")
    assert not any(m["id"] == "resolved_sites" for m in coverage)
    assert not any(m["id"] == "contradictions_visible" for m in coverage)
    layers = _web(export, "map")["layers"]
    assert layers[0]["id"] == "observed_sites"
    # The compute-on-read shaping coverage metrics are the honest fallback.
    assert coverage  # the shaping metrics are still present


def _dataset_of(claims: list[ShapingClaim]):
    """Build just the shaped dataset (no export) for the pure-mapper tests."""
    rows = _rows(claims)
    raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in sorted({c.subject_id for c in claims})],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    return build_shaped_dataset(
        raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )


def test_resolved_sites_metric_ignores_edges_outside_the_export_and_never_exceeds_m() -> None:
    dataset = _dataset_of(
        _site("A", "35.46", "-97.51", "Oklahoma") + _site("B", "35.46", "-97.51", "Oklahoma")
    )
    # No completed run → None (the observation framing stays; no fabricated count).
    assert resolved_sites_metric([], dataset) is None
    # An edge to a subject that is not an exported site cannot merge anything.
    metric = resolved_sites_metric([_site_run([("A", "ORG-1")])], dataset)
    assert metric is not None
    assert metric["value"].startswith("2 resolved sites (from 2 ")
    # A redundant edge set (A~B twice, B~A) is ONE merge: N = 1 of M = 2.
    counts = resolved_site_counts([_site_run([("A", "B"), ("A", "B"), ("B", "A")])], dataset)
    assert counts is not None
    assert (counts["observations"], counts["resolved_sites"], counts["merges"]) == (2, 1, 1)
    assert counts["resolved_sites"] <= counts["observations"]


def test_contradictions_visible_metric_counts_open_of_recorded() -> None:
    recorded = [
        {"contradiction_id": "x1", "status": "open", "claim_ids": ["c1", "c2"]},
        {"contradiction_id": "x2", "status": "superseded", "claim_ids": ["c3", "c4"]},
    ]
    metric = contradictions_visible_metric(recorded)
    assert metric is not None
    assert metric["value"] == "1 open of 2 recorded contradictions"
    assert metric["is_population_total"] is False
    assert "both evidence sides retained" in metric["denominator"]
    assert contradictions_visible_metric([]) is None


def test_contradictions_surface_on_coverage_when_materialized() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    contradictions = [{"contradiction_id": "x1", "status": "open", "claim_ids": ["c1", "c2"]}]
    export = _build(claims, _materialized_raw(contradictions=contradictions))
    coverage = _web(export, "coverage")
    vis = next(m for m in coverage if m["id"] == "contradictions_visible")
    assert vis["value"] == "1 open of 1 recorded contradictions"
    jsonschema.validate(coverage, _sub(SCHEMA["properties"]["coverage"]))


def test_network_reads_materialized_edges_else_falls_back() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    edges = [
        {
            "from_entity": "agency:okcpd",
            "to_entity": "vendor:flock",
            "edge_type": "configured_access",
            "access_kind": "configured_access",
            "direction": "directed",
            "evidence_claim": "c9",
        }
    ]
    export = _build(claims, _materialized_raw(edges=edges))
    network = _web(export, "network")
    assert {n["id"] for n in network["nodes"]} == {"agency:okcpd", "vendor:flock"}
    assert network["edges"][0]["access_kind"] == "configured_access"
    # P35.30 (SIG-EXPORT-D21): the relation renders in WORDS — never a raw slot
    # name — with the whole D21 evidence field set carried on the edge.
    assert network["edges"][0]["relation"] == "configured access"
    assert network["edges"][0]["date_kind"] == "undated"
    assert network["edges"][0]["claim_ids"] == ["c9"]
    assert network["edges"][0]["support"] == "WEAKLY_SUPPORTED"
    # P32.15 (SIG-FIND-004): the backing claim is emitted so the public surface
    # can NAME the support — a bare count was the unexplained-edge smell.
    assert network["edges"][0]["evidence"] == ["c9"]
    jsonschema.validate(network, _sub(SCHEMA["properties"]["network"]))


def test_coverage_prefers_materialized_rows_when_present() -> None:
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    materialized_coverage = [
        {
            "coverage_id": "cov1",
            "subject_id": None,
            "subject_class": "deployment",
            "jurisdiction_id": None,
            "predicate_id": "camera_device_count",
            "absence_kind": None,
            "sources_searched": [],
            "metric_method": "reconciliation_ratio",
            "metric_label": "resolved subjects of claimed subjects",
            "numerator": 38.0,
            "denominator": 42.0,
            "not_evaluable": 0.0,
            "named_denominator": "subjects with a camera_device_count claim",
            "metric_value": 0.9,
        },
        # A negative-space absence row (no metric_method) is NOT a coverage-list metric.
        {
            "coverage_id": "cov2",
            "subject_id": None,
            "subject_class": "deployment",
            "jurisdiction_id": None,
            "predicate_id": "sharing_partner",
            "absence_kind": "not_researched",
            "sources_searched": [],
            "metric_method": None,
            "metric_label": None,
            "numerator": None,
            "denominator": None,
            "not_evaluable": None,
            "named_denominator": None,
            "metric_value": None,
        },
    ]
    export = _build(claims, _materialized_raw(coverage=materialized_coverage))
    coverage = _web(export, "coverage")
    mat = next(m for m in coverage if m["id"].startswith("materialized_reconciliation_ratio"))
    assert mat["kind"] == "reconciliation_ratio"
    assert mat["value"] == "38 of 42"
    assert mat["denominator"] == "subjects with a camera_device_count claim"
    assert mat["is_population_total"] is False
    # The absence row did not become a metric.
    assert not any("sharing_partner" in m["id"] for m in coverage)
    jsonschema.validate(coverage, _sub(SCHEMA["properties"]["coverage"]))


def test_a_materialized_ratio_carries_its_exclusion_disclosure() -> None:
    """P35.20a / ED-42 (F-134): a materialized reconciliation ratio's excluded
    classes ride the emitted metric as data — ``exclusions`` + ``excluded_total``
    beside the "N of M" value, so the surface can never read N-of-N while
    subjects are excluded."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    materialized_coverage = [
        {
            "coverage_id": "cov1",
            "subject_id": None,
            "subject_class": "subject",
            "jurisdiction_id": None,
            "predicate_id": "camera_device_count",
            "absence_kind": None,
            "sources_searched": [],
            "metric_method": "reconciliation_ratio",
            "metric_label": "resolved subjects of claimed subjects",
            "numerator": 38.0,
            "denominator": 42.0,
            "not_evaluable": 4.0,
            "exclusions": {"conflicted": 3, "withheld": 1},
            "named_denominator": "subjects with a camera_device_count claim",
            "metric_value": 0.9,
        },
    ]
    export = _build(claims, _materialized_raw(coverage=materialized_coverage))
    coverage = _web(export, "coverage")
    mat = next(m for m in coverage if m["id"].startswith("materialized_reconciliation_ratio"))
    assert mat["value"] == "38 of 42"
    assert mat["exclusions"] == {"conflicted": 3, "withheld": 1}
    assert mat["excluded_total"] == 4
    # N + excluded = M — the disclosure always reconciles, never an N-of-N.
    assert 38 + mat["excluded_total"] == 42
    jsonschema.validate(coverage, _sub(SCHEMA["properties"]["coverage"]))


# --------------------------------------------------------------------------- #
# P35.19 (JUR-02b, K4 §3.3/§5.3): the placement@1 columns end-to-end — the     #
# engine lands on ``_slice_sites`` rows, the map layer, ``web/placement.json`` #
# and the published-record jurisdiction block; absent inputs keep the export   #
# byte-identical to the pre-placement posture; the read path never writes the  #
# spine. The engine matrix itself lives in ``test_placement.py``.              #
# --------------------------------------------------------------------------- #

import importlib.util as _ilu  # noqa: E402

import pytest  # noqa: E402
from placement_fixtures import build_placement_env  # noqa: E402

_needs_duckdb = pytest.mark.skipif(
    _ilu.find_spec("duckdb") is None,
    reason="duckdb is required for the placement engine",
)

_PLACEMENT_COLUMNS = (
    "jurisdiction_key",
    "jurisdiction_chain",
    "placement_basis",
    "placement_check",
    "declared_scheme",
    "declared_value",
    "boundary_vintage",
)


@pytest.fixture(scope="module")
def placement_env(tmp_path_factory: pytest.TempPathFactory):
    return build_placement_env(tmp_path_factory.mktemp("spine_placement"))


@pytest.fixture(scope="module")
def placement_engine(placement_env):
    from exports.placement import PlacementEngine

    return PlacementEngine(
        placement_env.pack_dir,
        placement_env.registry_path,
        spec_path=placement_env.spec_path,
    )


def _claim24(
    cid: str,
    sid: str,
    pred: str,
    *,
    value_text: str | None = None,
    source_id: str = "src_a",
    spdx: str = "CC-BY-4.0",
    value_json: dict | None = None,
) -> ShapingClaim:
    """A shaping claim that carries the P35.18 ``value_json`` blob (the 24th
    column) — the declared {scheme, value} pair + LocatedPoint precision
    stamp placement reads."""
    from dataclasses import replace

    c = _claim(cid, sid, pred, value_text=value_text, source_id=source_id, spdx=spdx)
    if value_json is not None:
        return replace(c, value_json=json.dumps(value_json, sort_keys=True))
    return c


def _site24(
    subject: str,
    lat: str | None,
    lon: str | None,
    scheme: str,
    value: str,
    *,
    source_id: str = "src_a",
    lat_precision: str | None = None,
) -> list[ShapingClaim]:
    """A site with a declared (scheme, value) jurisdiction pair — the claim
    text stays the bare code; the pair rides ``value_json`` (P35.18)."""
    claims: list[ShapingClaim] = []
    if lat is not None and lon is not None:
        claims += [
            _claim24(
                f"{subject}-lat",
                subject,
                "camera_latitude",
                value_text=lat,
                source_id=source_id,
                value_json=(
                    {"geometry": lat, "precision": lat_precision}
                    if lat_precision is not None
                    else None
                ),
            ),
            _claim24(
                f"{subject}-lon",
                subject,
                "camera_longitude",
                value_text=lon,
                source_id=source_id,
            ),
        ]
    claims.append(
        _claim24(
            f"{subject}-jur",
            subject,
            "camera_jurisdiction",
            value_text=value,
            source_id=source_id,
            value_json={"scheme": scheme, "value": value},
        )
    )
    return claims


def _rows24(claims: list[ShapingClaim]) -> list[tuple]:
    """``_rows`` plus the trailing columns parse_shaping_claims reads:
    publication_permitted, decision decided_at/basis, ``value_json``."""
    base = [list(t) for t in _rows(claims)]
    for row, claim in zip(base, claims, strict=True):
        row.extend([True, None, None, claim.value_json])
    return [tuple(r) for r in base]


def _build24(
    claims: list[ShapingClaim],
    raw_over: dict | None = None,
    *,
    placement=None,
):
    """``_build`` over the 24-column row set, optionally with an engine."""
    rows = _rows24(claims)
    subjects = sorted({c.subject_id for c in claims})
    raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    dataset = build_shaped_dataset(
        raw, as_of="2026-09-22", generated_at="2026-09-22T00:00:00Z", spine_label="unit"
    )
    bs = BuildSpec(
        as_of_snapshot=date(2026, 9, 22),
        as_of_belief=date(2026, 9, 22),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
    )
    return build_spine_export(
        dataset,
        raw_over or {},
        build_spec=bs,
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
        placement=placement,
    )


def _site_rows(export) -> dict[str, dict]:
    """entity_id → the emitted sites.jsonl row (first compartment hit)."""
    out: dict[str, dict] = {}
    for path, data in export.bundle.artifact_bytes.items():
        if path.endswith("/sites.jsonl"):
            for line in data.decode("utf-8").splitlines():
                row = json.loads(line)
                out.setdefault(str(row["entity_id"]), row)
    return out


def _fixture_claims() -> list[ShapingClaim]:
    """The §7 fixture set staged through the shaping seam:

    * ``A`` — declared CA, point inside the full CA chain → consistent;
    * ``B`` — declared CA, point inside Florida → ``outside_declared``
      (located wins; the disclosure pair rides the report);
    * ``C`` — declared GB-ENG, point in no boundary but whose swap lands in
      GB-ENG → ``axis_swap_suspected``, point withheld;
    * ``D`` — declared GB-ENG, ``(0,0)`` → ``point_rejected:null_island``;
    * ``E`` — declared CA, coordinate claim stamped
      ``organization_centroid_or_unknown`` (SIG-IDENT-004) → declared
      fallback, point withheld.
    """
    return (
        _site24("A", "34.0", "-115.0", "us.state_abbr", "CA")
        + _site24("B", "26.5", "-81.5", "us.state_abbr", "CA")
        + _site24("C", "-1.15", "52.95", "iso.3166_2", "GB-ENG")
        + _site24("D", "0.0", "0.0", "iso.3166_2", "GB-ENG")
        + _site24(
            "E",
            "34.0",
            "-115.0",
            "us.state_abbr",
            "CA",
            lat_precision="organization_centroid_or_unknown",
        )
    )


@_needs_duckdb
def test_placement_columns_land_on_site_rows(placement_engine) -> None:
    """The seven K4 §5.3 columns ride every site row when the engine is
    bound; the legacy ``jurisdiction`` column stays the declared bucket."""
    export = _build24(_fixture_claims(), placement=placement_engine)
    rows = _site_rows(export)
    assert set(rows) == {"A", "B", "C", "D", "E"}
    for row in rows.values():
        assert set(_PLACEMENT_COLUMNS) <= set(row)
    a = rows["A"]
    assert a["jurisdiction_key"] == "us.census.geoid.place:0644000"
    assert a["jurisdiction_chain"] == [
        "iso3166-1:US",
        "iso3166-2:US-CA",
        "us.census.geoid.county:06037",
        "us.census.geoid.place:0644000",
    ]
    assert a["placement_basis"] == "point_in_polygon"
    assert a["placement_check"] == "consistent"
    assert a["declared_scheme"] == "us.state_abbr"
    assert a["declared_value"] == "CA"
    assert a["boundary_vintage"] == "tiger-2025"
    # The legacy column is the declared bucket — unchanged, back-compat.
    assert a["jurisdiction"] == "iso3166-2:US-CA"
    assert a["geometry"]["type"] == "Point"


@_needs_duckdb
def test_located_wins_and_the_disagreement_is_disclosed(placement_engine) -> None:
    """CA→FL on the row AND on the report: R4's pair is counted once and
    readable from both dossier sides (K4 §3.4)."""
    export = _build24(_fixture_claims(), placement=placement_engine)
    b = _site_rows(export)["B"]
    assert b["jurisdiction_key"] == "iso3166-2:US-FL"
    assert b["placement_check"] == "outside_declared"
    assert b["declared_scheme"] == "us.state_abbr" and b["declared_value"] == "CA"
    report = json.loads(export.web_artifacts["web/placement.json"].decode("utf-8"))
    assert report["schema"] == "sig.placement-report/1"
    assert report["rules"] == "placement@1"
    assert report["totals"]["records"] == 5
    assert sum(report["by_check"].values()) == 5
    assert report["by_check"]["outside_declared"] == 1
    assert {"declared": "iso3166-2:US-CA", "located": "iso3166-2:US-FL", "records": 1} in (
        report["disclosures"]
    )
    assert (
        report["disclosures_by_jurisdiction"]["iso3166-2:US-CA"]["declared_here_located_elsewhere"]
        == 1
    )
    assert (
        report["disclosures_by_jurisdiction"]["iso3166-2:US-FL"]["located_here_declared_elsewhere"]
        == 1
    )


@_needs_duckdb
def test_withheld_points_never_re_emit_geometry_or_draw(placement_engine) -> None:
    """R3/R1/SIG-IDENT-004: a suspected swap, a null island and a guarded
    agency centroid all keep their record's declared placement but the point
    never re-emits — sites row geometry is null and the map asset carries no
    coordinates (``locationAbsence`` names the gap, ``placementCheck`` the
    verdict)."""
    export = _build24(_fixture_claims(), placement=placement_engine)
    rows = _site_rows(export)
    assert rows["C"]["placement_check"] == "axis_swap_suspected"
    assert rows["C"]["jurisdiction_key"] == "iso3166-2:GB-ENG"
    assert rows["C"]["geometry"] is None
    assert rows["D"]["placement_check"] == "point_rejected:null_island"
    assert rows["D"]["geometry"] is None
    # The centroid guard: full-precision tier label, claim-stamped centroid —
    # never point-placed, never drawn.
    assert rows["E"]["placement_check"] == "no_point"
    assert rows["E"]["jurisdiction_key"] == "iso3166-2:US-CA"
    assert rows["E"]["geometry"] is None

    assets = {a["id"]: a for a in _web(export, "map")["assets"]}
    for sid in ("C", "D", "E"):
        assert assets[sid]["lat"] is None and assets[sid]["lon"] is None
        assert assets[sid]["locationAbsence"] == "UNRESOLVED"
        assert "jurisdictionKey" in assets[sid]
        assert "placementCheck" in assets[sid]
    # The point_in_polygon-placed records still draw.
    assert assets["A"]["lat"] == 34.0 and assets["A"]["lon"] == -115.0
    assert assets["A"]["jurisdictionKey"] == "us.census.geoid.place:0644000"
    assert assets["B"]["jurisdictionKey"] == "iso3166-2:US-FL"


@_needs_duckdb
def test_placement_report_absent_without_engine() -> None:
    """Back-compat / additive posture: with no engine bound the sites rows
    carry none of the placement columns, no placement.json exists, and the
    map assets carry no placement fields — byte-identical to the
    pre-placement posture."""
    claims = _site("A", "35.46", "-97.51", "Oklahoma")
    export = _build(claims)
    assert "web/placement.json" not in export.web_artifacts
    for row in _site_rows(export).values():
        assert not set(_PLACEMENT_COLUMNS) & set(row)
    for asset in _web(export, "map")["assets"]:
        assert "jurisdictionKey" not in asset and "placementCheck" not in asset


@_needs_duckdb
def test_record_from_placed_site_row_carries_the_jurisdiction_block(
    placement_engine,
) -> None:
    """K4 §3.4: the published record's jurisdiction block carries the placed
    key + chain + basis + check + the declared pair + the boundary vintage."""
    from exports.published_record import record_from_site_row

    export = _build24(_fixture_claims(), placement=placement_engine)
    b = _site_rows(export)["B"]
    rec = record_from_site_row(b, compartment="sig_graph", license_id="CC-BY-4.0")
    j = rec.jurisdiction
    assert j["jkey"] == "iso3166-2:US-FL"
    assert j["chain"] == ["iso3166-1:US", "iso3166-2:US-FL"]
    assert j["basis"] == "point_in_polygon"
    assert j["check"] == "outside_declared"
    assert j["declared"] == {"scheme": "us.state_abbr", "value": "CA"}
    assert j["boundary_vintage"] == "tiger-2025"
    # The legacy id stays the declared bucket with its basis preserved.
    assert j["id"] == "iso3166-2:US-CA"
    assert j["id_basis"] == "camera_jurisdiction"
    # A withheld point records the honest location state, never the pair.
    c = _site_rows(export)["C"]
    rec_c = record_from_site_row(c, compartment="sig_graph", license_id="CC-BY-4.0")
    assert rec_c.location == {"kind": "point_withheld", "reason": "axis_swap_suspected"}
    assert rec_c.jurisdiction["jkey"] == "iso3166-2:GB-ENG"


@_needs_duckdb
def test_run_spine_export_placement_never_writes_the_spine(placement_env, monkeypatch) -> None:
    """The no-spine-write guard (ADR-092): the whole export — placement
    included — issues only reads on the spine connection; the engine works
    in its own in-memory DuckDB. Also proves the landed ``geometry_defect``
    claims flow from the export read into the placement verdicts."""
    import exports.shaping as shaping_mod
    import exports.spine_export as se

    claims = _fixture_claims()
    rows = _rows24(claims)
    subjects = sorted({c.subject_id for c in claims})
    shaping_raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    # C's declared pair is GB-ENG; the landed ``axis_swap`` defect claim is
    # what marks its point suspect — exercised end-to-end through the export
    # read path here.
    export_raw = {"geometry_defects": [("C", "axis_swap")]}

    monkeypatch.setattr(
        shaping_mod, "fetch_shaping_raw", lambda cur, queries, belief=None: shaping_raw
    )
    monkeypatch.setattr(se, "fetch_export_raw", lambda cur, belief=None: export_raw)
    monkeypatch.setattr(se, "fetch_materialized_graph", lambda cur: {})

    class _Cursor:
        def __init__(self) -> None:
            self.sql: list[str] = []
            self._next: list = []

        def execute(self, sql, params=None):
            self.sql.append(str(sql).strip())
            self._next = [(False,)]
            return self

        def fetchone(self):
            return self._next[0] if self._next else None

        def fetchall(self):
            return list(self._next)

    class _Conn:
        info = None  # transaction_status None → the export opens its own snapshot

        def __init__(self) -> None:
            self.cur = _Cursor()

        def cursor(self):
            return self.cur

        def close(self) -> None:
            pass

    conn = _Conn()
    export = se.run_spine_export(
        conn,
        build_spec=BuildSpec(
            as_of_snapshot=date(2026, 9, 22),
            as_of_belief=date(2026, 9, 22),
            ruleset_version="ruleset/1",
            resolver_version="resolver/1",
        ),
        generated_at=datetime(2026, 9, 22, tzinfo=UTC),
        spine_label="unit",
        boundary_pack=placement_env.pack_dir,
        jurisdiction_registry=placement_env.registry_path,
        boundary_spec=placement_env.spec_path,
    )
    # Every statement on the spine connection is a read or a transaction verb —
    # no INSERT/UPDATE/DELETE/DDL of any kind (the spine is append-only; the
    # export is compute-on-read).
    assert conn.cur.sql, "expected the snapshot read path to have run"
    allowed_heads = {"SET", "BEGIN", "SELECT", "ROLLBACK", "COMMIT", "WITH", "EXPLAIN"}
    for sql in conn.cur.sql:
        assert sql.split(None, 1)[0].upper() in allowed_heads, f"spine write: {sql}"

    assert "web/placement.json" in export.web_artifacts
    rows = _site_rows(export)
    # The landed defect claim drove the placement — C's point withheld.
    assert rows["C"]["placement_check"] == "axis_swap_suspected"
    assert rows["C"]["geometry"] is None


@_needs_duckdb
def test_run_spine_export_refuses_half_staged_placement_inputs(placement_env, monkeypatch) -> None:
    """--boundary-pack without --jurisdiction-registry (or vice versa)
    refuses — placement never runs on a half-staged input set."""
    from exports.placement import PlacementError
    from exports.spine_export import run_spine_export

    class _Conn:
        info = None

        def cursor(self):
            class _C:
                def execute(self, sql, params=None):
                    return self

                def fetchone(self):
                    return (False,)

            return _C()

    monkeypatch.setattr("exports.shaping.fetch_shaping_raw", lambda cur, queries, belief=None: {})
    monkeypatch.setattr("exports.spine_export.fetch_export_raw", lambda cur, belief=None: {})
    monkeypatch.setattr("exports.spine_export.fetch_materialized_graph", lambda cur: {})
    with pytest.raises(PlacementError, match="together"):
        run_spine_export(
            _Conn(),
            build_spec=BuildSpec(
                as_of_snapshot=date(2026, 9, 22),
                as_of_belief=date(2026, 9, 22),
                ruleset_version="ruleset/1",
                resolver_version="resolver/1",
            ),
            generated_at=datetime(2026, 9, 22, tzinfo=UTC),
            boundary_pack=placement_env.pack_dir,
        )


def test_cli_placement_flags_require_from_spine(capsys) -> None:  # type: ignore[no-untyped-def]
    from exports.cli import main

    rc = main(
        [
            "build",
            "req.json",
            "--out",
            "/tmp/x",
            "--boundary-pack",
            "p",
            "--jurisdiction-registry",
            "r",
        ]
    )
    assert rc == 2
    assert "only valid with --from-spine" in capsys.readouterr().out


def test_cli_placement_flags_must_be_paired(capsys) -> None:  # type: ignore[no-untyped-def]
    from exports.cli import main

    rc = main(
        [
            "build",
            "--from-spine",
            "--dsn",
            "postgresql://x",
            "--out",
            "/tmp/x",
            "--boundary-pack",
            "p",
        ]
    )
    assert rc == 2
    assert "together" in capsys.readouterr().out


def test_cli_boundary_spec_requires_the_pack(capsys) -> None:  # type: ignore[no-untyped-def]
    """--boundary-spec is the minting-rules override seam — meaningless (and
    refused) without the pack + registry it keys."""
    from exports.cli import main

    rc = main(
        [
            "build",
            "--from-spine",
            "--dsn",
            "postgresql://x",
            "--out",
            "/tmp/x",
            "--boundary-spec",
            "spec.toml",
        ]
    )
    assert rc == 2
    assert "--boundary-spec" in capsys.readouterr().out
