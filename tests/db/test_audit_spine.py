# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Docker-gated seeded-spine end-to-end for the public-surface audit (P27.1, LAUNCH.1).

Seeds a small, fully-controlled spine on a real PG18+PostGIS testcontainer and runs
:func:`exports.audit.run_audit` against it, asserting every headline the ticket names is measured
correctly — the "unit-tested against a seeded spine" acceptance criterion. Read-only throughout;
the per-test connection is rolled back by the ``conn`` fixture.
"""

from __future__ import annotations

import json

from exports.audit import run_audit


def _seed_predicate(cur, predicate_id: str, object_type: str = "literal") -> None:
    cur.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('authoritative_source_wins','fixture') ON CONFLICT DO NOTHING"
    )
    cur.execute(
        "INSERT INTO vocab_predicate"
        "(predicate_id,vocab_version,value_datatype,object_type,definition,"
        " volatility_class,half_life_days,resolution_strategy) "
        "VALUES(%s,'1.0.0','string',%s,'fixture','MODERATE',365,"
        "'authoritative_source_wins') ON CONFLICT DO NOTHING",
        (predicate_id, object_type),
    )


def _rights(cur, spdx: str, redistributable: str) -> str:
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,redistributable,"
        "derivative_permitted,retrieval_date) VALUES(%s,%s,%s,'2026-01-01') RETURNING rights_id",
        (spdx, redistributable, redistributable),
    )
    return cur.fetchone()[0]


def _run(cur, connector: str) -> str:
    cur.execute(
        "INSERT INTO ingest_run(connector_name,connector_version,code_commit,"
        "ruleset_version,vocab_version,parameters,environment,input_digests) "
        "VALUES(%s,'0','sha','r1','1.0.0','{}','{}','{}') RETURNING run_id",
        (connector,),
    )
    return cur.fetchone()[0]


def _entity(cur, entity_type: str = "deployment") -> str:
    cur.execute("INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,))
    return cur.fetchone()[0]


def _claim(cur, *, subject, predicate, value, run_id, rights_id, author_id) -> None:
    cur.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,value_text,"
        "raw_value,observed_at,source_reliability,claim_directness,artifact_integrity,"
        "asserted_by,assertion_rationale,ingest_run_id,rights_id,sensitivity_tier) "
        "VALUES(%s,%s,'literal','value',%s,%s,'2026-05-01T00:00:00Z','R1','D1','I1',"
        "%s,'fixture',%s,%s,0)",
        (subject, predicate, value, value, author_id, run_id, rights_id),
    )


def test_audit_over_seeded_spine(conn) -> None:
    cur = conn.cursor()
    for pred in ("camera_latitude", "camera_longitude", "camera_jurisdiction"):
        _seed_predicate(cur, pred)

    cc0 = _rights(cur, "CC0-1.0", "yes")
    undet = _rights(cur, "LicenseRef-Unknown", "UNDETERMINED")
    osm_run = _run(cur, "osm")
    proc_run = _run(cur, "procurement")
    author = _entity(cur, "person")

    # Two geolocated deployment subjects (each a lat + lon + jurisdiction), CC0 via osm.
    subj_a = _entity(cur)
    subj_b = _entity(cur)
    for subj, lat, lon, juris in (
        (subj_a, "35.46", "-97.51", "OK"),
        (subj_b, "45.36", "-122.84", "OR"),
    ):
        _claim(
            cur,
            subject=subj,
            predicate="camera_latitude",
            value=lat,
            run_id=osm_run,
            rights_id=cc0,
            author_id=author,
        )
        _claim(
            cur,
            subject=subj,
            predicate="camera_longitude",
            value=lon,
            run_id=osm_run,
            rights_id=cc0,
            author_id=author,
        )
        _claim(
            cur,
            subject=subj,
            predicate="camera_jurisdiction",
            value=juris,
            run_id=osm_run,
            rights_id=cc0,
            author_id=author,
        )

    # A third subject with UNDETERMINED rights via the procurement connector (no coordinates).
    subj_c = _entity(cur)
    _claim(
        cur,
        subject=subj_c,
        predicate="camera_jurisdiction",
        value="unresolved",
        run_id=proc_run,
        rights_id=undet,
        author_id=author,
    )

    audit = run_audit(conn, as_of="2026-09-22", note="seeded", spine_label="seeded")

    # 7 claims total (6 CC0 geo/juris + 1 UNDETERMINED juris).
    assert audit.total_claims == 7
    # entities: author + 3 subjects = 4.
    assert audit.total_entities == 4

    # Licence mix: CC0 redistributable=yes (6), UNDETERMINED (1).
    mix = {r.spdx: r for r in audit.licence_mix}
    assert mix["CC0-1.0"].claims == 6
    assert mix["CC0-1.0"].redistributable == "yes"
    assert mix["LicenseRef-Unknown"].claims == 1
    assert audit.publishable.numerator == 6
    assert audit.undetermined.numerator == 1
    assert audit.publishable.denominator == 7  # denominator carried (never a bare total)

    # UNDETERMINED attributed to the procurement connector.
    undet_by_conn = {n.name: n.count for n in audit.undetermined_by_connector}
    assert undet_by_conn == {"procurement": 1}

    # Geolocation: 2 distinct subjects carry lat/lon (aggregate only).
    assert audit.geolocated_entities == 2
    assert audit.geolocated.denominator == 4
    geo = {n.name: n.count for n in audit.geo_claims}
    assert geo == {"camera_latitude": 2, "camera_longitude": 2}

    # Jurisdiction spread by distinct subject: OK 1, OR 1, unresolved 1.
    juris = {n.name: n.count for n in audit.jurisdiction_spread}
    assert juris == {"OK": 1, "OR": 1, "unresolved": 1}

    # Modeling tables all empty on a freshly-seeded spine; value_geom unused.
    assert all(m.empty for m in audit.modeling_tables)
    assert audit.value_geom_populated == 0

    # Deterministic output on a re-run over the same (unmutated) spine.
    # `generated_at` is the one legitimately-varying field (the wall clock), so
    # compare the JSON with it stripped — every other byte must be stable.
    again = run_audit(conn, as_of="2026-09-22", note="seeded", spine_label="seeded")
    first = json.loads(audit.to_json_str())
    second = json.loads(again.to_json_str())
    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_audit_does_not_write_to_the_spine(conn) -> None:
    """The audit is read-only: the claim count is identical before and after a run."""
    cur = conn.cursor()
    _seed_predicate(cur, "camera_latitude")
    cc0 = _rights(cur, "CC0-1.0", "yes")
    run_id = _run(cur, "osm")
    author = _entity(cur, "person")
    subj = _entity(cur)
    _claim(
        cur,
        subject=subj,
        predicate="camera_latitude",
        value="1.0",
        run_id=run_id,
        rights_id=cc0,
        author_id=author,
    )

    cur.execute("SELECT count(*) FROM claim")
    before = cur.fetchone()[0]
    run_audit(conn, spine_label="seeded")
    cur.execute("SELECT count(*) FROM claim")
    after = cur.fetchone()[0]
    assert before == after == 1
