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
from datetime import date
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
from exports.spine_export import build_spine_export
from rdflib import Graph
from support import REPO_ROOT

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
            c.effective_rights_id,
            c.effective_spdx,
            c.effective_redistributable,
            c.effective_derivative_permitted,
            c.effective_attribution,
            c.effective_terms_url,
        )
        for c in claims
    ]


def _build(claims: list[ShapingClaim], raw_over: dict | None = None):
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
    # An honest gap is first-class (NOT_RESEARCHED), never omitted (§3.1).
    assert any(g["kind"] == "NOT_RESEARCHED" for g in dossier["gaps"])


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
