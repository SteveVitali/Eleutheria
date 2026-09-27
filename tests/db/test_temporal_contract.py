# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.4 (SIG-TRUST-005 / ADR-123): the shared bitemporal occurrence contract.

Two layers under one rule:

* the **pure conformance model** (``db.occurrences``) — belief bounds, valid-world
  bounds, the labelled undated fallback, deterministic ties (an id is never a
  clock), per-lineage concurrent candidates;
* **fixture/PG parity** — identical fixture vectors run through the pure model
  and the sqitch ``eligible_occurrence`` twin / ``occurrence_lateral`` readers
  must select identically, across every consumer (materializer read, camera-site
  read, export shaping read), with A→B→A behaving the same everywhere: A now,
  B at the intermediate belief, original A at the earlier belief — and a later
  capture/replay/correction never re-dating a frozen past-belief read.

Plus the per-execution completion contract (``camera_site_execution``: A→B→A
digest reuse still appends one completion; retry is +0; the latest completed
execution governs selection) and the ``spine_watermark`` invalidation facets
(D-P31.1-1: a bounded O(facets) read, never a claim-spine scan).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import pytest
from conftest import insert_claim, seed_claim_prerequisites
from db.occurrences import (
    CAPTURE_BASIS,
    ESTABLISHING_ROLE,
    UNDATED_DATE,
    WATERMARK_FACETS,
    WATERMARK_SQL,
    Binding,
    eligible_bindings,
    known_at,
    lineage_candidates,
    observation_instant,
    ordering_instant,
    select_observation,
    select_occurrence,
    spine_watermark,
    valid_at,
)

T1 = datetime(2026, 1, 1, tzinfo=UTC)
T2 = datetime(2026, 6, 1, tzinfo=UTC)
T3 = datetime(2026, 9, 1, tzinfo=UTC)


def _b(
    claim: str,
    cap: str,
    retrieved: datetime | None,
    bound: datetime | None,
    *,
    role: str = ESTABLISHING_ROLE,
    source: str = "s",
) -> Binding:
    return Binding(
        claim_id=claim,
        capture_id=cap,
        role=role,
        bound_at=bound,
        retrieved_at=retrieved,
        source_id=source,
    )


# --------------------------------------------------------------------------- #
# Pure conformance model                                                        #
# --------------------------------------------------------------------------- #


def test_empty_history_is_undated_and_historical() -> None:
    assert select_occurrence(()) is None
    obs = select_observation(observed_at=None, bindings=())
    assert obs.observed_at == UNDATED_DATE and obs.instant is None
    assert obs.basis == "claim" and obs.occurrence is None


def test_only_establishing_bindings_are_sightings() -> None:
    # A corroborating/contradicting link never re-dates the claim.
    obs = select_observation(
        observed_at=None,
        bindings=[_b("c", "cap-cor", T2, T2, role="corroborates")],
    )
    assert obs.occurrence is None and obs.observed_at == UNDATED_DATE


def test_belief_bound_freezes_a_past_read() -> None:
    a, b = _b("c", "cap-a", T1, T1), _b("c", "cap-b", T3, T3)
    # A→B→A knowledge: at the intermediate belief only cap-a is eligible.
    assert select_occurrence([a, b], belief=T2).capture_id == "cap-a"  # type: ignore[union-attr]
    assert select_occurrence([a, b], belief=None).capture_id == "cap-b"  # type: ignore[union-attr]
    assert [x.capture_id for x in eligible_bindings([a, b], belief=T2)] == ["cap-a"]


def test_equal_retrieved_at_tie_is_deterministic_not_temporal() -> None:
    # An exact-time tie breaks on the row id — the id is a tie-break, never a clock.
    z, a = _b("c", "cap-z", T1, T1), _b("c", "cap-a", T1, T1)
    assert select_occurrence([z, a]).capture_id == "cap-a"  # type: ignore[union-attr]
    assert select_occurrence([a, z]).capture_id == "cap-a"  # type: ignore[union-attr]


def test_undated_claim_dates_from_the_latest_eligible_occurrence() -> None:
    obs = select_observation(
        observed_at=None, bindings=[_b("c", "cap-b", T3, T3), _b("c", "cap-a", T1, T1)]
    )
    assert obs.basis == CAPTURE_BASIS and obs.instant == T3
    assert obs.occurrence is not None and obs.occurrence.capture_id == "cap-b"


def test_dated_claim_keeps_its_asserted_instant_and_cites_the_occurrence() -> None:
    obs = select_observation(observed_at=date(2026, 2, 2), bindings=[_b("c", "cap-b", T3, T3)])
    assert obs.basis == "claim" and obs.observed_at == date(2026, 2, 2)
    assert obs.instant == datetime(2026, 2, 2, tzinfo=UTC)
    # refs preserved even for a self-dated claim.
    assert obs.occurrence is not None and obs.occurrence.capture_id == "cap-b"


def test_observation_instant_prefers_claim_then_capture() -> None:
    assert observation_instant(T2, T3) == T2
    assert observation_instant(None, T3) == T3
    assert observation_instant(None, None) is None


def test_ordering_instant_uses_full_precision_then_utc_midnight() -> None:
    assert ordering_instant(T2, date(2026, 1, 1)) == T2
    assert ordering_instant(None, date(2026, 1, 1)) == datetime(2026, 1, 1, tzinfo=UTC)


def test_valid_world_bounds() -> None:
    # A future-effective value is not effective early; valid_to is exclusive.
    assert not valid_at(date(2026, 6, 1), None, date(2026, 5, 1))
    assert valid_at(date(2026, 6, 1), None, date(2026, 6, 1))
    assert not valid_at(None, date(2026, 6, 1), date(2026, 6, 1))
    assert valid_at(None, date(2026, 6, 1), date(2026, 5, 31))
    assert valid_at(None, None, date(1999, 1, 1))


def test_known_at_is_the_belief_predicate() -> None:
    assert known_at(T1, None, T2)
    assert not known_at(T3, None, T2)  # not yet known
    assert not known_at(T1, T2, T3)  # already closed
    assert known_at(T1, T2, T1)


@dataclass(frozen=True)
class _Row:
    claim_id: str
    source_id: str
    observed_at: date
    observed_instant: datetime | None = None


def test_lineage_candidates_supersede_within_a_source_only() -> None:
    old = _Row("c-old", "src-a", date(2026, 1, 1))
    new = _Row("c-new", "src-a", date(2026, 6, 1))
    rival = _Row("c-rival", "src-b", date(2026, 1, 1))
    out = lineage_candidates([old, new, rival])
    # The superseded same-source claim is history; the independent source stays
    # a concurrent candidate even though it is not the global latest.
    assert {r.claim_id for r in out} == {"c-new", "c-rival"}


def test_a_claim_id_is_never_a_clock() -> None:
    # The higher id has the EARLIER instant: recency still wins.
    early = _Row("z-late-id", "src", date(2026, 1, 1))
    late = _Row("a-early-id", "src", date(2026, 6, 1))
    assert [r.claim_id for r in lineage_candidates([early, late])] == ["a-early-id"]
    # An exact-time tie falls to the id — deterministic, not temporal.
    tie_a, tie_b = _Row("a", "src", date(2026, 6, 1)), _Row("b", "src", date(2026, 6, 1))
    assert [r.claim_id for r in lineage_candidates([tie_b, tie_a])] == ["b"]


# --------------------------------------------------------------------------- #
# Fixture/PG parity                                                             #
# --------------------------------------------------------------------------- #


def _seed_occurrence_chain(
    conn: Any,
    prereqs: dict[str, Any],
    *,
    source_id: str = "src_p32_4",
) -> dict[str, Any]:
    """source_registry + one artifact; returns ids for capture/binding inserts."""
    conn.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy,"
        "ingestion_permitted) VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted',"
        "'obey',true) ON CONFLICT DO NOTHING",
        (source_id, source_id, prereqs["rights_id"]),
    )
    artifact = conn.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'camera_registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (source_id, f"urn:sig:p32_4:{source_id}", prereqs["rights_id"]),
    ).fetchone()[0]
    return {"artifact": artifact}


def _capture_at(
    conn: Any,
    prereqs: dict[str, Any],
    artifact: Any,
    *,
    digest: str,
    retrieved_at: datetime,
) -> str:
    return str(
        conn.execute(
            "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
            "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
            "capture_method,capture_tool_version,source_uri) "
            "VALUES(%s,%s,10,'application/json',%s,%s,%s,'v1','public',"
            "'registry_api','sig/0',%s) RETURNING capture_id",
            (artifact, digest, retrieved_at, prereqs["run_id"], f"urn:{digest}", f"urn:{digest}"),
        ).fetchone()[0]
    )


def _undated_claim(
    conn: Any, prereqs: dict[str, Any], *, known_from: datetime | None = None
) -> Any:
    """A claim with NULL observed_at (needs ``observed_unknown_reason``).

    ``known_from`` overrides ``sys_period``'s lower bound so fixture knowledge
    instants (T1/T2/…) predate the real-clock insert — the bitemporal fixtures
    need assertions the spine has "known" since the fixture era.
    """
    return conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,value_num,unit,raw_value,observed_at,observed_unknown_reason,"
        "source_reliability,claim_directness,artifact_integrity,asserted_by,"
        "assertion_rationale,ingest_run_id,rights_id,sensitivity_tier,sys_period) "
        "VALUES(%s,%s,'quantity','value','25',25,'cameras','25',NULL,'undated source row',"
        "'R1','D1','I1',%s,'fixture',%s,%s,0,tstzrange(%s,NULL)) RETURNING claim_id",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            known_from or datetime(2020, 1, 1, tzinfo=UTC),
        ),
    ).fetchone()[0]


def _bind(
    conn: Any,
    claim_id: Any,
    capture_id: str,
    *,
    bound_at: datetime,
    role: str = ESTABLISHING_ROLE,
) -> None:
    conn.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role,bound_at) VALUES(%s,%s,%s,%s)",
        (claim_id, capture_id, role, bound_at),
    )


def test_pg_eligible_occurrence_matches_the_pure_model(conn: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    ev = _seed_occurrence_chain(conn, prereqs)
    claim_id = _undated_claim(conn, prereqs)
    cap_a = _capture_at(conn, prereqs, ev["artifact"], digest="d-a", retrieved_at=T1)
    cap_b = _capture_at(conn, prereqs, ev["artifact"], digest="d-b", retrieved_at=T3)
    _bind(conn, claim_id, cap_a, bound_at=T1)
    _bind(conn, claim_id, cap_b, bound_at=T3)

    for belief in (T1, T2, T3, None):
        pg = conn.execute(
            "SELECT capture_id::text, source_id, retrieved_at, bound_at"
            "  FROM eligible_occurrence(%s, %s)",
            (claim_id, belief),
        ).fetchone()
        # The pure model over the same bindings must select identically.
        bindings = [
            _b(str(claim_id), cap_a, T1, T1),
            _b(str(claim_id), cap_b, T3, T3),
        ]
        pure = select_occurrence(bindings, belief=belief)
        expected = cap_a if belief in (T1, T2) else cap_b
        assert pg is not None and str(pg[0]) == expected
        assert pure is not None and pure.capture_id == expected
        assert str(pg[0]) == pure.capture_id


def test_a_b_a_selects_the_same_instant_across_readers(conn: Any) -> None:
    """A→B→A: latest eligible occurrence is A now… wait, A-B knowledge: cap-b
    bound later. At an intermediate belief the same claim resolves to cap-a —
    the SQL twin and the materializer reader agree, and a belief before B's
    knowledge cannot see B at all."""
    prereqs = seed_claim_prerequisites(conn)
    ev = _seed_occurrence_chain(conn, prereqs)
    claim_id = _undated_claim(conn, prereqs)
    cap_a = _capture_at(conn, prereqs, ev["artifact"], digest="d-aba-a", retrieved_at=T1)
    cap_b = _capture_at(conn, prereqs, ev["artifact"], digest="d-aba-b", retrieved_at=T2)
    _bind(conn, claim_id, cap_a, bound_at=T1)
    _bind(conn, claim_id, cap_b, bound_at=T2)

    from reconcile.materialize import read_claim_groups

    def groups(belief: datetime | None):
        return read_claim_groups(
            conn,
            subject=str(prereqs["subject_id"]),
            predicate=prereqs["predicate_id"],
            as_of_belief=belief,
        )

    key = (str(prereqs["subject_id"]), prereqs["predicate_id"])
    now = groups(None)[key][0]
    assert now.occurrence_capture_id == cap_b
    assert now.observed_at_basis == CAPTURE_BASIS and now.observed_at == T2.date()
    mid = groups(datetime(2026, 3, 1, tzinfo=UTC))[key][0]
    assert mid.occurrence_capture_id == cap_a and mid.observed_at == T1.date()
    # And the SQL twin agrees at both instants.
    for belief, cap in ((datetime(2026, 3, 1, tzinfo=UTC), cap_a), (None, cap_b)):
        row = conn.execute(
            "SELECT capture_id::text FROM eligible_occurrence(%s, %s)", (claim_id, belief)
        ).fetchone()
        assert row is not None and row[0] == cap

    # The export reader sees the same occurrence at the same instants: the
    # shaping_claims query's claim_source CTE is belief-bounded by the same
    # instant as its sys_period filter.
    from db.occurrences import BELIEF_PARAM
    from exports.shaping import QUERIES, SHAPING_PREDICATES, expand_query

    sql = expand_query(QUERIES["shaping_claims"], bound=BELIEF_PARAM).replace(
        "upper_inf(c.sys_period)", "c.sys_period @> %s::timestamptz"
    )

    def export_row(belief: datetime):
        rows = conn.execute(
            sql,
            (belief, [*SHAPING_PREDICATES, prereqs["predicate_id"]], belief),
        ).fetchall()
        return next(r for r in rows if str(r[0]) == str(claim_id))

    mid_row = export_row(datetime(2026, 3, 1, tzinfo=UTC))
    assert str(mid_row[11]) == cap_a and mid_row[12] == T1
    now_row = export_row(datetime.now(UTC))
    assert str(now_row[11]) == cap_b and now_row[12] == T2


def test_a_later_binding_cannot_redate_a_frozen_belief_read(conn: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    ev = _seed_occurrence_chain(conn, prereqs)
    claim_id = _undated_claim(conn, prereqs)
    cap_a = _capture_at(conn, prereqs, ev["artifact"], digest="d-f-a", retrieved_at=T1)
    _bind(conn, claim_id, cap_a, bound_at=T1)
    frozen = datetime(2026, 2, 1, tzinfo=UTC)

    from reconcile.materialize import read_claim_groups

    key = (str(prereqs["subject_id"]), prereqs["predicate_id"])
    before = read_claim_groups(conn, subject=key[0], predicate=key[1], as_of_belief=frozen)[key][0]
    assert before.occurrence_capture_id == cap_a and before.observed_at == T1.date()

    # A new capture/binding arrives AFTER the frozen belief — replay/correction.
    cap_b = _capture_at(conn, prereqs, ev["artifact"], digest="d-f-b", retrieved_at=T3)
    _bind(conn, claim_id, cap_b, bound_at=T3)
    after = read_claim_groups(conn, subject=key[0], predicate=key[1], as_of_belief=frozen)[key][0]
    # Frozen past-belief output is byte-identical: still cap_a at T1.
    assert after.occurrence_capture_id == before.occurrence_capture_id
    assert after.observed_at == before.observed_at
    assert after.observed_instant == before.observed_instant


def test_a_correction_close_does_not_leak_into_an_earlier_belief(conn: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    claim_id = insert_claim(conn, prereqs)
    from reconcile.materialize import read_claim_groups

    key = (str(prereqs["subject_id"]), prereqs["predicate_id"])
    pin = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    assert key in read_claim_groups(conn, subject=key[0], predicate=key[1], as_of_belief=pin)

    # Close the claim's sys_period (the append-only correction path).
    conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period), clock_timestamp())"
        " WHERE claim_id = %s",
        (claim_id,),
    )
    # A belief at/after the close no longer sees it…
    now = conn.execute("SELECT clock_timestamp()").fetchone()[0]
    assert key not in read_claim_groups(conn, subject=key[0], predicate=key[1], as_of_belief=now)
    # …but the belief frozen before the close still does — history is not rewritten.
    assert key in read_claim_groups(conn, subject=key[0], predicate=key[1], as_of_belief=pin)


def test_coordinate_pair_never_mixes_occurrences(conn: Any) -> None:
    """lat from capture X + lon from capture Y is NOT a point."""
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('latest_observation_wins','fixture') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO vocab_predicate(predicate_id,vocab_version,value_datatype,object_type,"
        " definition,volatility_class,half_life_days,resolution_strategy) "
        "VALUES('camera_latitude','1','string','literal','f','SLOW',1,'latest_observation_wins'),"
        "      ('camera_longitude','1','string','literal','f','SLOW',1,'latest_observation_wins')"
        " ON CONFLICT DO NOTHING"
    )
    rights = conn.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,derivative_permitted,"
        "retrieval_date) VALUES('CC0-1.0','yes','yes','2026-01-01') RETURNING rights_id"
    ).fetchone()[0]
    run = conn.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,ruleset_version,"
        "vocab_version,parameters,environment,input_digests,status,finished_at) "
        "VALUES('p32_4','0','sha','r1','1.0.0','{}','{}','{}','succeeded','2026-09-01T00:00:00Z')"
        " RETURNING run_id"
    ).fetchone()[0]
    author = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('person') RETURNING entity_id"
    ).fetchone()[0]
    prereqs = {"rights_id": rights, "run_id": run}
    ev = _seed_occurrence_chain(conn, prereqs, source_id="src_pair")
    subject = conn.execute(
        "INSERT INTO entity(entity_type) VALUES('deployment') RETURNING entity_id"
    ).fetchone()[0]

    cap_x = _capture_at(conn, prereqs, ev["artifact"], digest="d-x", retrieved_at=T1)
    cap_y = _capture_at(conn, prereqs, ev["artifact"], digest="d-y", retrieved_at=T2)

    def cam_claim(pred: str, value: str, cap: str, bound: datetime) -> str:
        cid = conn.execute(
            "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
            "raw_value,observed_at,source_reliability,claim_directness,artifact_integrity,"
            "asserted_by,assertion_rationale,ingest_run_id,rights_id,sensitivity_tier) "
            "VALUES(%s,%s,'literal','value',%s,%s,%s,'R2','D2','I1',%s,'f',%s,%s,0)"
            " RETURNING claim_id",
            (subject, pred, value, value, T2, author, run, rights),
        ).fetchone()[0]
        _bind(conn, cid, cap, bound_at=bound)
        return str(cid)

    def close(cid: str) -> None:
        conn.execute(
            "UPDATE claim SET sys_period = tstzrange(lower(sys_period), clock_timestamp())"
            " WHERE claim_id = %s",
            (cid,),
        )

    from resolution.camera_sites_pg import read_camera_records

    def rec():
        return next(r for r in read_camera_records(conn) if r.subject_id == str(subject))

    lat1 = cam_claim("camera_latitude", "35.1", cap_x, T1)
    lon1 = cam_claim("camera_longitude", "-97.5", cap_y, T2)
    # No common establishing capture → no atomic pair → no point, ever.
    assert rec().latitude is None and rec().longitude is None
    assert rec().coordinate_capture_id is None

    # Replace the pair with two claims established in ONE capture → a point.
    close(lat1)
    close(lon1)
    cam_claim("camera_latitude", "35.1", cap_x, T1)
    cam_claim("camera_longitude", "-97.5", cap_x, T2)
    assert rec().latitude == pytest.approx(35.1)
    assert rec().longitude == pytest.approx(-97.5)
    assert rec().coordinate_capture_id == cap_x


# --------------------------------------------------------------------------- #
# Per-execution completion + watermark                                          #
# --------------------------------------------------------------------------- #


def test_a_b_a_execution_reuse_still_appends_a_completion(conn: Any) -> None:
    """camera_site_run is digest-keyed: the third execution (A again) reuses
    run A but MUST append its own completion, and the reader selects the run
    the LATEST COMPLETED EXECUTION produced — never the stale B."""
    from resolution.camera_sites import CameraRecord
    from resolution.camera_sites_pg import (
        materialize_camera_sites,
        read_resolved_site_runs,
    )

    a = [CameraRecord("subj:a", "s1", 35.0, -97.0)]
    b = [CameraRecord("subj:a", "s1", 35.001, -97.0)]
    kw: dict[str, Any] = {"gold": None, "threshold": 0.5}

    m1 = materialize_camera_sites(conn, records=a, **kw)
    m2 = materialize_camera_sites(conn, records=b, **kw)
    assert m1["run_key"] != m2["run_key"] and m1["run_record_inserted"]

    m3 = materialize_camera_sites(conn, records=a, **kw)
    # Digest reuse: no new run row, but ONE new execution completion.
    assert m3["run_key"] == m1["run_key"] and not m3["run_record_inserted"]
    assert m3["execution_appended"]

    n_exec = conn.execute(
        "SELECT count(*) FROM camera_site_execution WHERE run_key = %s", (m1["run_key"],)
    ).fetchone()[0]
    assert n_exec == 2  # exec1 + exec3 both completed on run A

    # The reader follows the latest completed execution → back on run A.
    runs = read_resolved_site_runs(conn)
    assert runs and runs[0]["run_key"] == m1["run_key"]

    # Idempotent retry of the same execution appends +0.
    again = materialize_camera_sites(conn, records=a, execution_id=m3["execution_id"], **kw)
    assert not again["execution_appended"]
    n_exec = conn.execute("SELECT count(*) FROM camera_site_execution").fetchone()[0]
    assert n_exec == 3


def test_watermark_tracks_claim_correction_and_completion(conn: Any) -> None:
    def facet(name: str) -> tuple[Any, ...]:
        row = conn.execute(
            "SELECT row_count, closed_count, bump FROM spine_watermark WHERE facet = %s",
            (name,),
        ).fetchone()
        assert row is not None, name
        return row

    # Every watched facet is seeded once.
    seeded = {r[0] for r in conn.execute("SELECT facet FROM spine_watermark").fetchall()}
    assert set(WATERMARK_FACETS) <= seeded

    mark0 = spine_watermark(conn)
    prereqs = seed_claim_prerequisites(conn)
    rows0, closed0, bump0 = facet("claim")
    claim_id = insert_claim(conn, prereqs)
    rows1, closed1, bump1 = facet("claim")
    assert (rows1, closed1, bump1) == (rows0 + 1, closed0, bump0 + 1)

    # A correction (sys_period close) bumps closed_count, not row_count.
    conn.execute(
        "UPDATE claim SET sys_period = tstzrange(lower(sys_period), clock_timestamp())"
        " WHERE claim_id = %s",
        (claim_id,),
    )
    rows2, closed2, bump2 = facet("claim")
    assert (rows2, closed2, bump2) == (rows1, closed1 + 1, bump1 + 1)

    # A completed materialization invalidates its own facet.
    conn.execute(
        "INSERT INTO camera_site_run(run_key,ruleset_version,resolver_version,"
        "gold_set_version,auto_write_tiers,observation_count,cluster_count,summary) "
        "VALUES('k-fixture','r','v','g','{1}',0,0,'{}') ON CONFLICT DO NOTHING"
    )
    conn.execute(
        "INSERT INTO camera_site_execution(execution_id,run_key,input_count,summary) "
        "VALUES(uuidv7(),'k-fixture',0,'{}')"
    )
    exec_facet = facet("camera_site_execution")
    assert exec_facet[0] >= 1 and exec_facet[2] >= 1

    # The disclosed watermark string moved — a comparing reader sees the change.
    mark1 = spine_watermark(conn)
    assert mark1 != mark0 and "claims=" in mark1


def test_the_watermark_read_is_bounded(conn: Any) -> None:
    """D-P31.1-1: the freshness read plans against the small facets table only —
    no claim-spine scan is involved in determining freshness."""
    plan = conn.execute(f"EXPLAIN {WATERMARK_SQL}").fetchall()
    text = " ".join(str(r[0]) for r in plan)
    assert "spine_watermark" in text and "claim" not in text.replace("spine_watermark", "")
