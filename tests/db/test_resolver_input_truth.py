# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Resolver input truth over the real spine (P35.27 / CP-9, F-519).

The materialize reader now supplies the resolver's truthful inputs — the
declared ``valid_period`` bounds (Phase 1.2's filter was vacuous on this path)
and the connector-DECLARED ``claim_directness`` distinguished from the
``connector_default_D2`` sink default via ``assertion_map_basis`` — and the
within-tolerance ``contested`` dissent signal persists on the resolution row.
The read-only ``rematerialize_report`` diffs the live materialized surface
against the recompute and names every delta class.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from conftest import seed_claim_prerequisites
from reconcile.materialize import (
    materialize_resolutions,
    read_claim_groups,
    rematerialize_report,
)

PRED = "contracted_device_count"  # IMMUTABLE, authoritative_source_wins, in registry


def _seed_predicate(conn: object, predicate_id: str = PRED, datatype: str = "integer") -> None:
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0',%s,'quantity','fixture','IMMUTABLE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (predicate_id, datatype),
    )


def _source_and_capture(conn: object, prereqs: dict, genre: str, key: str) -> object:
    conn.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy,ingestion_permitted) "
        "VALUES(%s,%s,'registry','R1','fixture',%s,'MIRROR','granted','obey',true) "
        "ON CONFLICT DO NOTHING",
        (key, key, prereqs["rights_id"]),
    )
    artifact_id = conn.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,%s,'registry_api','primary',%s,'captured') RETURNING artifact_id",
        (key, f"urn:sig:p3527:{key}", genre, prereqs["rights_id"]),
    ).fetchone()[0]
    return conn.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0',%s) RETURNING capture_id",
        (
            artifact_id,
            f"digest-{key}",
            prereqs["run_id"],
            f"urn:sig:p3527:{key}",
            f"urn:sig:p3527:{key}",
        ),
    ).fetchone()[0]


def _claim(
    conn: object,
    prereqs: dict,
    *,
    predicate: str = PRED,
    value: object,
    capture_id: object,
    reliability: str = "R1",
    observed: str = "2026-05-01T00:00:00Z",
    directness: str = "D1",
    basis: object = None,
    valid: object = None,  # e.g. ("2020-01-01", "2021-01-01") bounds pair
) -> object:
    params: list = [
        prereqs["subject_id"],
        predicate,
        str(value),
        float(value) if isinstance(value, (int, float)) else None,
        str(value),
        observed,
        reliability,
        directness,
        prereqs["author_id"],
        prereqs["run_id"],
        prereqs["rights_id"],
    ]
    if valid:
        valid_sql = "tstzrange(%s::timestamptz, %s::timestamptz, '[)')"
        params += [valid[0], valid[1]]
    else:
        # NOT NULL column — the unbounded range is the schema default.
        valid_sql = "tstzrange(NULL, NULL, '[)')"
    params.append(basis)
    claim_id = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,unit,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier,valid_period,assertion_map_basis) "
        "VALUES(%s,%s,'quantity','value',%s,%s,'devices',%s,%s,%s,%s,'I1',%s,'fixture',"
        "%s,%s,0," + valid_sql + ",%s) RETURNING claim_id",
        tuple(params),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (claim_id, capture_id),
    )
    return claim_id


def _fabricate_live_resolution(
    conn: object,
    prereqs: dict,
    *,
    predicate: str = PRED,
    state: str,
    digest: str,
) -> None:
    """A pre-P35.27 live materialized row (the 'before' the report diffs against)."""
    conn.execute(
        "INSERT INTO vocab_rationale(rationale_code,template) "
        "VALUES('RESOLVED_DIRECT','fixture') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_confidence(confidence,definition) "
        "VALUES('confirmed','fixture') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO resolution"
        "(subject_id,predicate_id,value_kind,value_text,valid_period,"
        " considered_claims,dissenting_claims,contradiction_state,"
        " strategy_id,rationale_code,rationale_text,confidence,evidence_counts,"
        " resolver_version,ruleset_version,decided_by,input_digest) "
        "VALUES(%s,%s,'value','299',tstzrange('2020-01-01',NULL,'[)'),"
        "'{}','{}',%s,'authoritative_source_wins','RESOLVED_DIRECT',"
        "'fixture','confirmed','{}','p08.1/1.1.0','2026.2','auto',%s)",
        (prereqs["subject_id"], predicate, state, digest),
    )


# --- reader truth: the materialize read supplies the truthful inputs ----------


def test_read_claim_groups_reads_valid_bounds_and_declared_directness(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap = _source_and_capture(conn, prereqs, "executed_contract", "c1")

    declared = _claim(
        conn,
        prereqs,
        value=299,
        capture_id=cap,
        directness="D6",
        basis="connector_record",
        valid=("2020-01-01", "2021-01-01"),
    )
    defaulted = _claim(
        conn,
        prereqs,
        value=298,
        capture_id=cap,
        directness="D2",
        basis="connector_record|claim_directness=connector_default_D2",
    )
    legacy = _claim(conn, prereqs, value=297, capture_id=cap, directness="D2", basis=None)

    groups = read_claim_groups(conn, subject=str(prereqs["subject_id"]))
    claims = {c.claim_id: c for c in groups[(str(prereqs["subject_id"]), PRED)]}
    by_id = {str(k): v for k, v in claims.items()}
    # The declared valid period now reaches the resolver (Phase 1.2 input truth).
    assert by_id[str(declared)].valid_from == date(2020, 1, 1)
    assert by_id[str(declared)].valid_to == date(2021, 1, 1)
    assert by_id[str(declared)].declared_directness == "D6"
    # A defaulted D2 is the absence of declaration — the matrix governs alone.
    assert by_id[str(defaulted)].declared_directness is None
    # A pre-P32.2 row (no basis) never declared either.
    assert by_id[str(legacy)].declared_directness is None


def test_api_reader_reads_the_same_truthful_inputs(conn: object) -> None:
    # The compute-on-read path resolves on the same inputs (F-519 — the two
    # read surfaces can no longer diverge): ``_public_claim_groups`` must hand
    # the resolver the declared directness, not the schema-defaulted column.
    from api.store_pg import PgReadStore

    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap = _source_and_capture(conn, prereqs, "executed_contract", "c2")
    d6 = _claim(
        conn,
        prereqs,
        value=299,
        capture_id=cap,
        directness="D6",
        basis="connector_record",
    )
    defaulted = _claim(
        conn,
        prereqs,
        value=298,
        capture_id=cap,
        directness="D2",
        basis="connector_record|claim_directness=connector_default_D2",
    )

    store = PgReadStore.__new__(PgReadStore)
    groups = store._public_claim_groups(conn, datetime.now(tz=UTC))
    claims = {c.claim_id: c for c in groups[(str(prereqs["subject_id"]), PRED)]}
    assert claims[str(d6)].declared_directness == "D6"
    # A defaulted D2 resolves to absent — the matrix governs alone.
    assert claims[str(defaulted)].declared_directness is None


# --- the contested dissent signal persists (deliverable 3) ---------------------


def _camera_claim(conn: object, prereqs: dict, value: float, capture_id: object) -> object:
    claim_id = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "value_num,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,'camera_latitude','literal','value',%s,%s,%s,"
        "'2026-05-01T00:00:00Z','R3','D2','I1',%s,'fixture',%s,%s,0) RETURNING claim_id",
        (
            prereqs["subject_id"],
            str(value),
            value,
            str(value),
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
        (claim_id, capture_id),
    )
    return claim_id


def test_within_tolerance_contested_dissent_persists_on_the_row(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn, "camera_latitude", datatype="decimal")
    cap_a = _source_and_capture(conn, prereqs, "camera_registry", "cra")
    cap_b = _source_and_capture(conn, prereqs, "camera_registry", "crb")
    a = _camera_claim(conn, prereqs, 52.1000, cap_a)
    b = _camera_claim(conn, prereqs, 52.1004, cap_b)  # within the 0.0005 tolerance

    summary = materialize_resolutions(
        conn, subject=str(prereqs["subject_id"]), as_of=date(2026, 9, 24)
    )
    assert summary.inserted == 1 and summary.resolved == 1
    row = conn.execute(
        "SELECT value_num, contradiction_state, dissenting_claims, evidence_counts "
        "  FROM resolution WHERE subject_id=%s AND predicate_id='camera_latitude'",
        (prereqs["subject_id"],),
    ).fetchone()
    assert float(row[0]) == 52.1000
    assert row[1] == "uncontested"  # disclosed dissent, never a contradiction
    # F-519: the within-tolerance disagreement is no longer silently absorbed —
    # the contested ids persist on the row AND in the machine-readable counts.
    assert set(str(x) for x in row[2]) == {str(b)}
    counts = row[3]
    assert counts["agreement"] == "MINOR_DISAGREEMENT"
    assert counts["n_contested"] == 1
    assert set(counts["contested_claim_ids"]) == {str(b)}
    assert "SIG-RECON-053:contested" in counts["rules_fired"]
    # a stays a supporter of the pooled value — it is not demoted.
    assert str(a) != str(b)


# --- the read-only rematerialize report (deliverable 5) ------------------------


def test_rematerialize_report_names_every_delta_class(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap = _source_and_capture(conn, prereqs, "executed_contract", "c3")

    # Temporal deconfliction: a pre-P35.27 row recorded a conflict because the
    # reader never saw the valid-period bounds; the truthful read excludes the
    # out-of-era claim under Phase 1.2.
    _claim(
        conn,
        prereqs,
        value=299,
        capture_id=cap,
        observed="2020-06-01T00:00:00Z",
        valid=("2020-01-01", "2021-01-01"),
        basis="connector_record",
    )
    _claim(
        conn,
        prereqs,
        value=42,
        capture_id=cap,
        observed="2025-04-01T00:00:00Z",
        valid=("2024-01-01", None),
        basis="connector_record",
    )
    _fabricate_live_resolution(conn, prereqs, state="unresolved_conflict", digest="before-t")

    report = rematerialize_report(conn, subject=str(prereqs["subject_id"]), as_of=date(2026, 1, 1))
    assert report.considered_pairs == 1
    assert report.unchanged == 0
    (delta,) = report.deltas
    assert delta.before_state == "unresolved_conflict"
    assert delta.after_state == "uncontested"
    assert "temporal-deconflicted" in delta.classes
    assert "state-shift" in delta.classes
    assert report.delta_class_counts["temporal-deconflicted"] == 1
    assert report.before == {"unresolved_conflict": 1}
    assert report.after == {"uncontested": 1}


def test_rematerialize_report_directness_and_contested_classes(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn, "camera_latitude", datatype="decimal")
    # Two DISTINCT sources — same-source re-assertions supersede (Phase 1.4)
    # before pooling ever sees them.
    cap_a = _source_and_capture(conn, prereqs, "camera_registry", "c4a")
    cap_b = _source_and_capture(conn, prereqs, "camera_registry", "c4b")
    _camera_claim(conn, prereqs, 52.1000, cap_a)
    _camera_claim(conn, prereqs, 52.1004, cap_b)
    _fabricate_live_resolution(
        conn, prereqs, predicate="camera_latitude", state="resolved_conflict", digest="before-c"
    )

    report = rematerialize_report(conn, subject=str(prereqs["subject_id"]), as_of=date(2026, 9, 24))
    (delta,) = report.deltas
    assert delta.before_state == "resolved_conflict"
    assert delta.after_state == "uncontested"
    assert "tolerance-de-escalated" in delta.classes
    assert "contested-disclosed" in delta.classes
    assert delta.contested_claim_ids


def test_rematerialize_report_declared_directness_class(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap = _source_and_capture(conn, prereqs, "executed_contract", "c5")
    _claim(
        conn,
        prereqs,
        value=299,
        capture_id=cap,
        directness="D6",
        basis="connector_record",  # a real connector declaration
    )
    _claim(conn, prereqs, value=299, capture_id=cap, directness="D1", basis="connector_record")
    _fabricate_live_resolution(conn, prereqs, state="unresolved_conflict", digest="before-d")

    report = rematerialize_report(conn, subject=str(prereqs["subject_id"]), as_of=date(2026, 9, 24))
    (delta,) = report.deltas
    assert "directness-reweighted" in delta.classes


def test_rematerialize_report_is_read_only_and_unchanged_pairs_skip(conn: object) -> None:
    prereqs = seed_claim_prerequisites(conn)
    _seed_predicate(conn)
    cap = _source_and_capture(conn, prereqs, "executed_contract", "c6")
    _claim(conn, prereqs, value=299, capture_id=cap, directness="D1", basis="connector_record")

    first = materialize_resolutions(conn, subject=str(prereqs["subject_id"]))
    assert first.inserted == 1
    report = rematerialize_report(conn, subject=str(prereqs["subject_id"]), as_of=date(2026, 9, 24))
    assert report.unchanged == 1 and not report.deltas

    # Idempotent +0: a real re-materialize over the same truthful inputs writes
    # nothing new, and the read-only report wrote nothing at all.
    n_rows = conn.execute(
        "SELECT count(*) FROM resolution WHERE subject_id=%s", (prereqs["subject_id"],)
    ).fetchone()[0]
    second = materialize_resolutions(conn, subject=str(prereqs["subject_id"]))
    assert second.inserted == 0 and second.skipped_existing == 1
    assert (
        conn.execute(
            "SELECT count(*) FROM resolution WHERE subject_id=%s",
            (prereqs["subject_id"],),
        ).fetchone()[0]
        == n_rows
    )
