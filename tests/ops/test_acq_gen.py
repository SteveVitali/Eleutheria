# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.6 / ACQ-01 — the Round-11 acquisition-row generator.

The generator is a *registration* machine: it emits fail-closed
``[sources.<id>]`` rows (``ingestion_permitted = false``, rights
``UNDETERMINED``), ``[[targets]]`` rows for expandable layer kinds, the
Round-11 grouped batches at the reviewed 6h per-row bound, and a manifest of
dedupes/pendings/errors. The tests run it against small fixture CSVs — the
committed plan's own errors are planning data, not this suite's business.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from ops.acq_gen import (
    R11_TASK_TIMEOUT,
    GenerationError,
    cadence_toml,
    check_id_collisions,
    dispositions_toml,
    family_prefix,
    generate,
    manifest_json,
    normalize_id,
    sources_toml,
    targets_toml,
)

PLAN_HEADER = (
    "plan_id,cand_ids,family,tier,action,rights_batch,part_viii,"
    "expected_claims,cadence,ticket,depends_on,verification"
)

CAND_HEADER = (
    "i7_id,cand_ids_merged,name,url,publisher,publisher_type,"
    "technology_classes,geographies,licence_guess,registry_match,"
    "proposed_source_id,proposed_name,ontology_concepts"
)


def _write_fixture(
    tmp_path: Path, plan_rows: list[str], cand_rows: list[str]
) -> tuple[Path, Path, Path]:
    plan = tmp_path / "acquisition_plan.csv"
    plan.write_text(PLAN_HEADER + "\n" + "\n".join(plan_rows) + "\n")
    cands = tmp_path / "candidates.csv"
    cands.write_text(CAND_HEADER + "\n" + "\n".join(cand_rows) + "\n")
    plan_rows_csv = tmp_path / "round11_plan.csv"
    plan_rows_csv.write_text("id,cat_ids\nP36.4,R11-ACQ-08\nP36.5,R11-ACQ-11\n")
    return plan, cands, plan_rows_csv


# --- R2 id normalisation --------------------------------------------------------


def test_normalize_id_keeps_wellformed_proposal() -> None:
    assert (
        normalize_id(
            "camreg_rutland_vt_cameras",
            family="dot_511(arcgis_query)",
            geography="US-VT",
            name="ignored",
        )
        == "camreg_rutland_vt_cameras"
    )


def test_normalize_id_recomputes_oversized_proposal() -> None:
    sid = normalize_id(
        "camreg_" + "x" * 60,
        family="procurement(portal_tenants)",
        geography="US-IL:Cook County",
        name="Cook County Procurement Contracts",
    )
    assert sid.startswith("procportal_")
    assert len(sid) <= 40
    # whole tokens only — a recompute never cuts mid-token
    assert all(part for part in sid.split("_"))


def test_normalize_id_recomputes_prefixless_proposal() -> None:
    sid = normalize_id(
        "town_camera_feed",
        family="dot_511(arcgis_query)",
        geography="US-VT",
        name="Town Cameras",
    )
    assert sid.startswith("camreg_")


def test_normalize_id_refuses_underivable_seed() -> None:
    with pytest.raises(GenerationError):
        normalize_id("", family="", geography="", name="!!!")


def test_family_prefix_routes_plan_families() -> None:
    # Patterns are ordered — the first match wins ("disclosure" reaches the
    # statrep pattern before ccops; "dossier"/"ccops" reach ccops).
    assert family_prefix("procurement(portal_tenants:socrata)") == "procportal_"
    assert family_prefix("ccops") == "ccops_"
    assert family_prefix("dossier(captures)") == "ccops_"
    assert family_prefix("legislation(bills)") == "legis_"


# --- collision / prefix checks (NEW-1) -----------------------------------------


def test_check_id_collisions_exact_and_prefix() -> None:
    errors = check_id_collisions(
        ["ccops_newtown", "camreg_a", "camreg_a_b"],
        existing=["ccops_newtown", "dot_511_dc"],
    )
    assert any("collides with a registered" in e for e in errors)
    assert any("prefix relation" in e for e in errors)


def test_check_id_collisions_prefix_against_registered() -> None:
    errors = check_id_collisions(["camreg_dc_dot"], existing=["camreg_dc_dot_feed"])
    assert any("prefix relation with registered id" in e for e in errors)


def test_check_id_collisions_clean() -> None:
    assert check_id_collisions(["camreg_x", "ccops_y"], existing=["dot_511_z"]) == []


# --- generate() over a fixture plan ---------------------------------------------


def _basic_fixture(tmp_path: Path):
    plan_rows = [
        # ACQ-08 layer row — emits source + arcgis_query target + batch member
        "P-001,C-001,dot_511(arcgis_query),1,new-row,RB-02,pass,10,"
        "monthly@r11-layers-01(17 7 16 * *),ACQ-08 -> live ACQ-16,,",
        # ACQ-08 with an un-expandable transport — manifest pending_kind
        "P-002,C-002,dot_511(arcgis_outstatistics),1,new-row,RB-02,pass,10,"
        "monthly@r11-layers-02(17 7 17 * *),ACQ-08,,",
    ]
    cand_rows = [
        "U-1,C-001,Town Cam Layer,https://gis.example.gov/arcgis/rest/services/L/0,"
        "Town GIS,municipal,T01,US-VT:Rutland,CC0,,camreg_rutland_vt_cameras,"
        "Rutland VT Cameras,traffic_camera",
        "U-2,C-002,County Counts Layer,https://gis2.example.gov/arcgis/rest/services/M/0,"
        "County GIS,municipal,T01,US-VT:Chittenden,CC0,,camreg_chittenden_vt_counts,"
        "Chittenden VT Counts,traffic_camera",
    ]
    return _write_fixture(tmp_path, plan_rows, cand_rows)


def test_generate_emits_fail_closed_source_rows(tmp_path: Path) -> None:
    plan, cands, plan_rows = _basic_fixture(tmp_path)
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    assert gen.errors == []
    ids = {item["id"] for item in gen.sources}
    assert "camreg_rutland_vt_cameras" in ids
    for item in gen.sources:
        row = item["row"]
        assert row["ingestion_permitted"] is False
        assert row["reliability_provisional"] is True
        assert row["verified"] is False
        assert row["rights"] == {"spdx": "UNDETERMINED", "redistributable": False}
        assert "HG-03" in row["notes"]


def test_generate_routes_expandable_vs_pending_kinds(tmp_path: Path) -> None:
    plan, cands, plan_rows = _basic_fixture(tmp_path)
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    # the arcgis_query row emits a registry target …
    assert any(t["kind"] == "arcgis_query" for t in gen.targets)
    assert all("source_id" in t for t in gen.targets)
    # … the arcgis_outstatistics row lands in the manifest pending list (ACQ-20)
    pending = gen.manifest.get("pending_kind", [])
    assert any(p["kind"] == "arcgis_outstatistics" for p in pending)


def test_generate_creates_r11_batches_at_the_reviewed_bound(tmp_path: Path) -> None:
    plan, cands, plan_rows = _basic_fixture(tmp_path)
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    batch = gen.batches["r11-layers-01"]
    assert batch["cron"] == "17 7 16 * *"
    assert batch["task_timeout"] == R11_TASK_TIMEOUT == "6h"
    assert "camreg_rutland_vt_cameras" in batch["members"]
    assert "paused" in batch["note"]  # R6 — created paused
    cad = tomllib.loads(cadence_toml(gen))
    emitted = {b["id"]: b for b in cad["batches"]}
    assert emitted["r11-layers-01"]["task_timeout"] == "6h"
    assert emitted["r11-layers-02"]["cron"] == "17 7 17 * *"


def test_generate_dispositions_and_manifest(tmp_path: Path) -> None:
    plan, cands, plan_rows = _basic_fixture(tmp_path)
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    dis = tomllib.loads(dispositions_toml(gen))
    row = dis["sources"]["camreg_rutland_vt_cameras"]
    assert row["disposition"] == "promote"
    assert row["class_ticket"] == "P36.4"
    manifest = json.loads(manifest_json(gen))
    assert manifest["emitted_ids"]


def test_generate_unresolved_ticket_is_an_error_never_a_silent_promote(
    tmp_path: Path,
) -> None:
    plan, cands, plan_rows = _write_fixture(
        tmp_path,
        [
            "P-001,C-001,dot_511(arcgis_query),1,new-row,RB-02,pass,10,"
            "monthly@r11-layers-01(17 7 16 * *),ACQ-99,,"
        ],
        [
            "U-1,C-001,L,https://gis.example.gov/arcgis/rest/services/L/0,Pub,"
            "municipal,T01,US-VT,CC0,,camreg_orphan_vt,N,traffic_camera"
        ],
    )
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    assert not gen.ok()
    assert any("resolves to no manifest ticket" in e for e in gen.errors)


def test_generate_per_source_job_ride_is_an_error(tmp_path: Path) -> None:
    plan, cands, plan_rows = _write_fixture(
        tmp_path,
        ["P-001,C-001,dot_511(arcgis_query),1,new-row,RB-02,pass,10,monthly@dc_511,ACQ-08,,"],
        [
            "U-1,C-001,L,https://gis.example.gov/arcgis/rest/services/L/0,Pub,"
            "municipal,T01,US-VT,CC0,,camreg_rider_vt,N,traffic_camera"
        ],
    )
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    assert not gen.ok()
    assert any("cannot ride a per-source job" in e for e in gen.errors)


def test_generate_missing_candidate_is_an_error(tmp_path: Path) -> None:
    plan, cands, plan_rows = _write_fixture(
        tmp_path,
        [
            "P-001,C-NOPE,dot_511(arcgis_query),1,new-row,RB-02,pass,10,"
            "monthly@r11-layers-01(17 7 16 * *),ACQ-08,,"
        ],
        [],
    )
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    assert any("no candidate row" in e for e in gen.errors)


def test_registered_id_collision_is_an_error(tmp_path: Path) -> None:
    """A proposal colliding with a committed registry id fails (NEW-1)."""
    # 'ccops_boston' is a committed [sources.ccops_boston] row.
    plan, cands, plan_rows = _write_fixture(
        tmp_path,
        [
            "P-001,C-001,ccops(self_disclosure),1,new-row,RB-02,pass,10,"
            "monthly@r11-disclosures-01(27 7 21 * *),ACQ-08,,"
        ],
        ["U-1,C-001,L,https://example.gov/d,Pub,municipal,T01,US-MA,CC0,,ccops_boston,N,"],
    )
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    assert any("collides with a registered" in e for e in gen.errors)


def test_r1_dedupe_under_a_registered_source(tmp_path: Path) -> None:
    """A new-row id under an existing source becomes a target + manifest note."""
    # 'camreg_bellevue_wa' is a committed source; a proposal under it dedupes.
    plan, cands, plan_rows = _write_fixture(
        tmp_path,
        [
            "P-001,C-001,dot_511(arcgis_query),1,new-row,RB-02,pass,10,"
            "monthly@r11-layers-01(17 7 16 * *),ACQ-08,,"
        ],
        [
            "U-1,C-001,L,https://gis.example.gov/arcgis/rest/services/N/0,Pub,"
            "municipal,T01,US-WA,CC0,,camreg_bellevue_wa_speed_safety_cameras,"
            "N,traffic_camera"
        ],
    )
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    deduped = gen.manifest.get("deduped", [])
    assert any(
        d["proposed_source_id"] == "camreg_bellevue_wa_speed_safety_cameras"
        and d["under"] == "camreg_bellevue_wa"
        for d in deduped
    )


def test_emitted_sources_toml_parses(tmp_path: Path) -> None:
    plan, cands, plan_rows = _basic_fixture(tmp_path)
    gen = generate(plan_csv=plan, candidates_csv=cands, plan_rows_csv=plan_rows)
    doc = tomllib.loads(sources_toml(gen))
    assert "camreg_rutland_vt_cameras" in doc["sources"]
    row = doc["sources"]["camreg_rutland_vt_cameras"]
    assert row["ingestion_permitted"] is False
    targets = tomllib.loads(targets_toml(gen))
    for t in targets.get("targets", []):
        assert t["jurisdiction_scheme"] == "iso.3166_2"


def test_committed_plan_run_keeps_every_error_explicit() -> None:
    """The real plan run never fabricates: every unroutable row is an error or
    a manifest note, every emitted row stays fail-closed, and a re-run over a
    registry that already holds the emission *converges* — the generated ids
    land in the manifest's ``converged``/``emitted_ids`` record, never a
    NEW-1 self-collision."""
    from ops.acq_gen import DEFAULT_CANDIDATES, DEFAULT_PLAN, DEFAULT_PLAN_ROWS

    gen = generate(
        plan_csv=DEFAULT_PLAN,
        candidates_csv=DEFAULT_CANDIDATES,
        plan_rows_csv=DEFAULT_PLAN_ROWS,
    )
    emitted = set(gen.manifest.get("emitted_ids", []))
    if gen.sources:
        # A plan addition not yet committed — fresh emission still happens.
        for item in gen.sources:
            assert item["row"]["ingestion_permitted"] is False
    else:
        # The committed artifacts replay clean: every emitted id converged.
        converged = {r["source_id"] for r in gen.manifest.get("converged", [])}
        assert emitted and emitted <= converged
    assert gen.batches, "the committed plan emits Round-11 batches"
    # Whatever the plan's open inconsistencies, they are *reported*, never
    # silently dropped: every error is a non-empty human-readable string, and
    # the manifest records exactly what the run reported.
    assert all(isinstance(e, str) and e for e in gen.errors)
    assert json.loads(manifest_json(gen))["errors"] == gen.errors
