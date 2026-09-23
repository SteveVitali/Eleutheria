# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Docker-gated seeded-spine end-to-end for the spine-backed export (P27.4, LAUNCH.4).

Seeds a small, fully-controlled spine (an ODbL source + a CC0 source + an
UNDETERMINED source) on a real PG18+PostGIS testcontainer, then runs
:func:`exports.spine_export.run_spine_export` against it and asserts: the ten
P27.1 web surfaces are emitted, the licence gate keeps ODbL apart from the CC-BY
graph (``assert_separated``), the UNDETERMINED source never reaches a shipped row,
and the session stays read-only (no spine mutation). Self-contained seeding (the
same L0 evidence chain as ``test_shaping_spine``) so the suite has no cross-test
import coupling.
"""

from __future__ import annotations

import json

import pytest
from exports.compartments import assert_separated
from exports.spine_export import run_spine_export


def _seed_predicate(cur, predicate_id: str) -> None:
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','string','literal','fixture','MODERATE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (predicate_id,),
    )


def _rights(cur, spdx: str, redistributable: str) -> str:
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) VALUES(%s,%s,%s,'2026-01-01') RETURNING rights_id",
        (spdx, redistributable, redistributable),
    )
    return cur.fetchone()[0]


def _run(cur, connector: str, status: str = "succeeded") -> str:
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests,status,"
        "finished_at) VALUES(%s,'0','sha','r1','1.0.0','{}','{}','{}',%s,"
        "'2026-05-02T00:00:00Z') RETURNING run_id",
        (connector, status),
    )
    return cur.fetchone()[0]


def _source(cur, source_id: str, rights_id: str) -> None:
    cur.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy,ingestion_permitted) "
        "VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted','obey',true)",
        (source_id, source_id, rights_id),
    )


def _artifact_capture(cur, source_id: str, rights_id: str, run_id: str, key: str) -> str:
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (source_id, f"urn:sig:p274:{key}", rights_id),
    )
    artifact_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0',%s) RETURNING capture_id",
        (artifact_id, f"digest-{key}", run_id, f"urn:sig:p274:{key}", f"urn:sig:p274:{key}"),
    )
    return cur.fetchone()[0]


def _entity(cur, entity_type: str = "deployment") -> str:
    cur.execute("INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,))
    return cur.fetchone()[0]


def _claim(
    cur, *, subject, predicate, value, run_id, rights_id, author_id, capture_id, value_num=None
) -> None:
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,'literal','value',%s,%s,%s,'2026-05-01T00:00:00Z','R1','D1','I1',"
        "%s,'fixture',%s,%s,0) RETURNING claim_id",
        (subject, predicate, value, value_num, str(value), author_id, run_id, rights_id),
    )
    claim_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (claim_id, capture_id),
    )


@pytest.fixture
def seeded_export(conn) -> dict:
    """An ODbL subject + a CC0 subject + an UNDETERMINED subject (excluded)."""
    cur = conn.cursor()
    for pred in ("camera_latitude", "camera_longitude", "camera_jurisdiction", "camera_name"):
        _seed_predicate(cur, pred)

    cc0 = _rights(cur, "CC0-1.0", "yes")
    odbl = _rights(cur, "ODbL-1.0", "yes")
    undet = _rights(cur, "LicenseRef-Unknown", "UNDETERMINED")

    run_cc0 = _run(cur, "camreg_cc0")
    run_osm = _run(cur, "camreg_osm")
    run_ud = _run(cur, "muckrock", status="failed")

    _source(cur, "camreg_cc0", cc0)
    _source(cur, "camreg_osm", odbl)
    _source(cur, "muckrock", undet)

    cap_cc0 = _artifact_capture(cur, "camreg_cc0", cc0, run_cc0, "cc0")
    cap_osm = _artifact_capture(cur, "camreg_osm", odbl, run_osm, "osm")
    cap_ud = _artifact_capture(cur, "muckrock", undet, run_ud, "ud")
    author = _entity(cur, "person")

    def geo(subject, lat, lon, juris, *, cap, run, rights):
        _claim(
            cur,
            subject=subject,
            predicate="camera_latitude",
            value=lat,
            value_num=float(lat),
            run_id=run,
            rights_id=rights,
            author_id=author,
            capture_id=cap,
        )
        _claim(
            cur,
            subject=subject,
            predicate="camera_longitude",
            value=lon,
            value_num=float(lon),
            run_id=run,
            rights_id=rights,
            author_id=author,
            capture_id=cap,
        )
        _claim(
            cur,
            subject=subject,
            predicate="camera_jurisdiction",
            value=juris,
            run_id=run,
            rights_id=rights,
            author_id=author,
            capture_id=cap,
        )

    s_osm = _entity(cur)
    geo(s_osm, "35.46", "-97.51", "OK", cap=cap_osm, run=run_osm, rights=odbl)
    s_cc0 = _entity(cur)
    geo(s_cc0, "40.71", "-74.00", "NY", cap=cap_cc0, run=run_cc0, rights=cc0)
    s_ud = _entity(cur)
    geo(s_ud, "51.50", "-0.12", "LDN", cap=cap_ud, run=run_ud, rights=undet)

    return {"osm": str(s_osm), "cc0": str(s_cc0), "ud": str(s_ud)}


def test_spine_export_over_seeded_spine(conn, seeded_export) -> None:
    export = run_spine_export(conn, as_of="2026-09-23", note="seeded", spine_label="seeded")

    # The fail-closed licence gate holds: ODbL apart from the CC-BY graph.
    assert_separated(export.bundle.placed)
    site_comps = {pt.compartment for pt in export.bundle.placed if pt.table.name == "sites"}
    assert "osm_physical" in site_comps  # the ODbL subject
    assert "osm_physical/sites.geojson" in export.bundle.artifact_bytes

    # The UNDETERMINED subject never reaches a shipped site row (publishable scope).
    shipped = {
        r.data["entity_id"]
        for pt in export.bundle.placed
        if pt.table.name == "sites"
        for r in pt.table.rows
    }
    assert seeded_export["ud"] not in shipped
    assert seeded_export["osm"] in shipped

    # All ten P27.1 web surfaces are emitted (honest absence for the empty ones).
    for name in (
        "dossier_index",
        "dossiers",
        "map",
        "network",
        "freshness",
        "coverage",
        "watch",
        "evidence",
        "corrections",
        "research_queue",
    ):
        assert f"web/{name}.json" in export.web_artifacts
    for metric in json.loads(export.web_artifacts["web/coverage.json"]):
        assert metric["is_population_total"] is False

    # Manifest carries provenance + per-artifact checksums/compartments.
    paths = {a.path for a in export.manifest.artifacts}
    assert "provenance.ttl" in paths and "exclusions.json" in paths


def test_spine_export_session_is_read_only(conn, seeded_export) -> None:
    run_spine_export(conn, as_of="2026-09-23", spine_label="seeded")
    # The export puts the session in read-only mode (append-only spine held
    # trivially, §16) — no export path can INSERT/UPDATE/DELETE.
    cur = conn.cursor()
    cur.execute("SHOW default_transaction_read_only")
    assert cur.fetchone()[0] == "on"


# --- P28.5: the export reads the MATERIALIZED graph (ADR-101) --------------- #

_COUNT_PRED = "contracted_device_count"  # resolvable: authoritative_source_wins


def _seed_count_predicate(cur) -> None:
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','integer','quantity','fixture','IMMUTABLE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (_COUNT_PRED,),
    )


def _genre_capture(cur, source_id: str, rights_id: str, run_id: str, key: str, genre: str) -> str:
    """A capture whose artifact_type is a resolver-known genre (for count reconciliation)."""
    cur.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,%s,'records_request','primary',%s,'captured') RETURNING artifact_id",
        (source_id, f"urn:sig:p285:{key}", genre, rights_id),
    )
    artifact_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','records_request','sig/0',%s) RETURNING capture_id",
        (artifact_id, f"digest-{key}", run_id, f"urn:sig:p285:{key}", f"urn:sig:p285:{key}"),
    )
    return cur.fetchone()[0]


def _count_claim(
    cur, *, subject, value, run_id, rights_id, author_id, capture_id, reliability="R1"
) -> None:
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,unit,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,'quantity','value',%s,%s,'devices',%s,'2026-05-01T00:00:00Z',%s,"
        "'D1','I1',%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            subject,
            _COUNT_PRED,
            str(value),
            value,
            str(value),
            reliability,
            author_id,
            run_id,
            rights_id,
        ),
    )
    claim_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (claim_id, capture_id),
    )


def test_spine_export_reads_the_materialized_graph(conn, seeded_export) -> None:
    # Add resolvable device-count claims to the geolocated sites, then run the REAL P28.1/3/4
    # materializers over the spine (SIG-ENG-035, consumed not re-implemented). s_osm agrees
    # (299/299 → RESOLVED); s_cc0 disagrees (299/190 → a VISIBLE contradiction).
    from inference.materialize import materialize_coverage
    from reconcile.materialize import materialize_contradictions, materialize_resolutions

    cur = conn.cursor()
    _seed_count_predicate(cur)
    rights = _rights(cur, "CC0-1.0", "yes")
    run = _run(cur, "count_src")
    # Two DISTINCT sources (one per genre) so the two count claims are independent evidence —
    # a same-source pair collapses to one independence class (uncontested). The count claims'
    # genre must be one the predicate's directness map knows (executed_contract / invoice), so
    # the §28 resolver adjudicates rather than KeyError-skips.
    _source(cur, "count_contract", rights)
    _source(cur, "count_invoice", rights)
    cap_contract = _genre_capture(
        cur, "count_contract", rights, run, "contract", "executed_contract"
    )
    cap_invoice = _genre_capture(cur, "count_invoice", rights, run, "invoice", "invoice")
    author = _entity(cur, "person")
    s_osm, s_cc0 = seeded_export["osm"], seeded_export["cc0"]
    # s_osm: two agreeing sources → a RESOLVED envelope (a resolved site).
    _count_claim(
        cur,
        subject=s_osm,
        value=299,
        run_id=run,
        rights_id=rights,
        author_id=author,
        capture_id=cap_contract,
    )
    _count_claim(
        cur,
        subject=s_osm,
        value=299,
        run_id=run,
        rights_id=rights,
        author_id=author,
        capture_id=cap_invoice,
    )
    # s_cc0: 299 vs 190 → a VISIBLE contradiction (both evidence sides retained).
    _count_claim(
        cur,
        subject=s_cc0,
        value=299,
        run_id=run,
        rights_id=rights,
        author_id=author,
        capture_id=cap_contract,
        reliability="R1",
    )
    _count_claim(
        cur,
        subject=s_cc0,
        value=190,
        run_id=run,
        rights_id=rights,
        author_id=author,
        capture_id=cap_invoice,
        reliability="R2",
    )

    res = materialize_resolutions(conn)
    con = materialize_contradictions(conn)
    cov = materialize_coverage(conn)
    assert res.inserted >= 1  # at least s_osm's RESOLVED envelope written
    assert con.inserted >= 1  # s_cc0's 299-vs-190 contradiction written (kept VISIBLE)
    assert cov.inserted >= 1  # honest §32 coverage rows written

    export = run_spine_export(conn, as_of="2026-09-23", note="materialized", spine_label="seeded")
    coverage = json.loads(export.web_artifacts["web/coverage.json"])

    # The resolved-site framing rides the frozen CoverageMetric contract (ADR-101): only
    # s_osm resolved, so N = 1 resolved site; the denominator names the observations; no total.
    resolved = next(m for m in coverage if m["id"] == "resolved_sites")
    assert resolved["value"].startswith("1 resolved sites (from ")
    assert resolved["is_population_total"] is False
    assert "observation-level sites" in resolved["denominator"]
    # Contradictions stay VISIBLE — surfaced as an honest counted quantity (§3.1/§31).
    contradictions = next(m for m in coverage if m["id"] == "contradictions_visible")
    assert "contradictions" in contradictions["value"]
    # The materialized §32 coverage rows are read (not the compute-on-read shaping metrics).
    assert any(m["id"].startswith("materialized_") for m in coverage)
    # Every coverage metric is still non-total (§32, SIG-METRIC-010).
    for m in coverage:
        assert m["is_population_total"] is False
    # The map layer flips to the resolved framing.
    assert json.loads(export.web_artifacts["web/map.json"])["layers"][0]["id"] == "resolved_sites"
