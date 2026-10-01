# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P31.7 — claim re-sightings + latest-capture dating (ADR-R9-RESIGHT), real PG.

* The production ``on_duplicates`` hook (:func:`db.claim_sink.record_resightings`)
  appends one ``claim_evidence`` link per re-sighted claim to the execution's own
  synthetic capture — uncapped, inside the chunk transaction, +0 claims.
* The write is idempotent on ``(claim_id, capture_id, role)``: a resumed execution
  re-flushing the same capture, or a second ``assert_claims`` over the same
  records, links +0.
* A replay run (``is_replay``) records nothing — re-reading stored bytes is not a
  sighting of the source.
* Capture-dating reads the LATEST sighting (``capture_retrieved_at_latest``), so
  A → B → A resolves to A under ``latest_observation_wins``.
* A changed ``input_digest`` lands as a superseding decision: the prior live
  ``auto`` row's ``sys_period`` is closed (``close_superseded_resolutions``), the
  new row is the only live one, and a re-run over unchanged input stays +0.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

import psycopg
import pytest

_SPINE_TABLES = (
    "ingest_run_completion",
    "ingest_run_capture",
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identity_key",
    "entity_identifier",
    "ingest_run",
    "source_registry",
    "entity",
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _claims(
    subjects: list[str], *, value: object = "on", source: str = "resight_src"
) -> list[dict[str, Any]]:
    return [
        {
            "subject_id": s,
            "predicate_id": "sig.test.resight",
            "value": value,
            "source_id": source,
            "license": "CC0-1.0",
            "evidence_genre": "camera_registry",
        }
        for s in subjects
    ]


def _link_count(conn: psycopg.Connection[Any]) -> int:
    return conn.execute("SELECT count(*) FROM claim_evidence").fetchone()[0]


def test_unchanged_reingest_links_every_resighting_plus_zero_claims(clean_dsn: str) -> None:
    """Two later executions re-asserting the same claims: +0 claims, +1 link each."""
    from db.claim_sink import PgClaimSink, record_resightings

    claims = _claims(["rs:1", "rs:2", "rs:3"])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        first = PgClaimSink(conn, connector_name="rs", on_duplicates=record_resightings)
        first.assert_claims(claims)
        assert first.report.inserted == 3 and first.report.duplicates == 0
        assert _link_count(conn) == 3

        second = PgClaimSink(conn, connector_name="rs", on_duplicates=record_resightings)
        second.assert_claims(claims)
        assert second.report.inserted == 0 and second.report.duplicates == 3
        assert _link_count(conn) == 6  # every re-sighting recorded, uncapped
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == 3

        third = PgClaimSink(conn, connector_name="rs", on_duplicates=record_resightings)
        third.assert_claims(claims)
        assert _link_count(conn) == 9

        # One link per (claim, capture, 'establishes') — three distinct captures.
        rows = conn.execute(
            "SELECT claim_id, count(*) FROM claim_evidence GROUP BY claim_id"
        ).fetchall()
        assert sorted(r[1] for r in rows) == [3, 3, 3]
        captures = conn.execute("SELECT DISTINCT capture_id FROM claim_evidence").fetchall()
        assert len(captures) == 3


def test_resighting_links_are_idempotent_per_capture(clean_dsn: str) -> None:
    """A resumed execution re-flushes the SAME capture: the link dedupes to +0."""
    from db.claim_sink import PgClaimSink, record_resightings

    claims = _claims(["rs:r1"])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        first = PgClaimSink(conn, connector_name="rs", on_duplicates=record_resightings)
        first.assert_claims(claims)
        run_id = first.run_id

        resumed = PgClaimSink(
            conn,
            connector_name="rs",
            execution_id=first.execution_id,
            on_duplicates=record_resightings,
        )
        resumed.assert_claims(claims)
        assert resumed.run_id == run_id, "a resumed execution reuses its run"
        assert resumed.report.duplicates == 1 and resumed.report.inserted == 0
        # Same run → same synthetic capture → the (claim, capture, role) PK dedupes.
        assert _link_count(conn) == 1

        # Even a second assert on the SAME sink (same capture) links +0.
        first.assert_claims(claims)
        assert _link_count(conn) == 1


def test_a_replay_run_records_no_resighting(clean_dsn: str) -> None:
    """is_replay executions re-derive stored bytes — never a fresh sighting."""
    from db.claim_sink import PgClaimSink, record_resightings

    claims = _claims(["rs:rp1"])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        PgClaimSink(conn, connector_name="rs", on_duplicates=record_resightings).assert_claims(
            claims
        )
        replay = PgClaimSink(
            conn, connector_name="rs", is_replay=True, on_duplicates=record_resightings
        )
        replay.assert_claims(claims)
        assert replay.report.duplicates == 1
        assert _link_count(conn) == 1  # only the original establishing link


def test_the_hooks_links_roll_back_with_a_failed_chunk(clean_dsn: str) -> None:
    """The hook writes inside the chunk transaction, so an aborted chunk keeps
    nothing — the run row, the claims and the resighting links roll back whole."""
    from db.claim_sink import PgClaimSink, record_resightings

    claims = _claims(["rs:t1"])
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        PgClaimSink(conn, connector_name="rs", on_duplicates=record_resightings).assert_claims(
            claims
        )

        def poisoned(batch: Any) -> None:
            record_resightings(batch)  # the link lands…
            raise RuntimeError("chunk abort")  # …then the chunk transaction dies

        doomed = PgClaimSink(conn, connector_name="rs", on_duplicates=poisoned)
        with pytest.raises(RuntimeError):
            doomed.assert_claims(claims)
        assert _link_count(conn) == 1, "the aborted chunk's link rolled back with it"
        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == 1


# --- dating basis + resolution supersession (A → B → A) ------------------------


def _camera_claims(subject: str, status: str) -> list[dict[str, Any]]:
    return [
        {
            "subject_id": subject,
            "predicate_id": "camera_status",  # registry: latest_observation_wins
            "value": status,
            "source_id": "resight_camreg",
            "license": "CC0-1.0",
            "evidence_genre": "camera_registry",
        }
    ]


def _retime_capture(conn: psycopg.Connection[Any], run_id: str, when: str) -> None:
    """Pin a run's synthetic capture to a fixed retrieval time (test determinism)."""
    conn.execute(
        "UPDATE evidence_capture SET retrieved_at = %s::timestamptz "
        "WHERE retrieved_by_run_id = %s::uuid",
        (when, run_id),
    )


def _subject_entity(conn: psycopg.Connection[Any], subject: str) -> str:
    return str(
        conn.execute(
            "SELECT entity_id FROM entity_identifier "
            "WHERE scheme = 'sig.connector.subject' AND value = %s",
            (subject,),
        ).fetchone()[0]
    )


def test_a_to_b_to_a_resolves_to_a_and_supersedes_the_prior_decision(clean_dsn: str) -> None:
    """Run 1 asserts active, run 2 inactive, run 3 active again — a re-sighting of
    the SAME claim row. Latest-capture dating makes A the newest observation, so
    the materialized decision flips back to A, superseding the earlier B decision
    (its sys_period closed, kept as history); a re-run stays +0."""
    from db.claim_sink import PgClaimSink, record_resightings
    from reconcile.materialize import materialize_resolutions

    subject = "resight_cam:1"
    as_of = date(2026, 10, 1)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        run_ids: list[str] = []
        for status, when in (
            ("active", "2026-05-01T00:00:00Z"),  # A: the registry lists it active
            ("inactive", "2026-06-01T00:00:00Z"),  # B: the registry marks it gone
            ("active", "2026-07-01T00:00:00Z"),  # A restated — a RE-SIGHTING
        ):
            sink = PgClaimSink(conn, connector_name="camreg", on_duplicates=record_resightings)
            sink.assert_claims(_camera_claims(subject, status))
            _retime_capture(conn, sink.run_id, when)
            run_ids.append(sink.run_id)

        assert conn.execute("SELECT count(*) FROM claim").fetchone()[0] == 2  # A and B
        assert _link_count(conn) == 3  # A links cap1 AND cap3; B links cap2

        entity = _subject_entity(conn, subject)
        claim_a = conn.execute("SELECT claim_id FROM claim WHERE value_text = 'active'").fetchone()[
            0
        ]
        cap3 = conn.execute(
            "SELECT capture_id FROM evidence_capture WHERE retrieved_by_run_id = %s::uuid",
            (run_ids[2],),
        ).fetchone()[0]

        # First decide the A→B moment (A's restated sighting not yet recorded) —
        # the decision picks B, because A's only sighting (May) predates B's (Jun).
        conn.execute(
            "DELETE FROM claim_evidence WHERE claim_id = %s AND capture_id = %s",
            (claim_a, cap3),
        )
        first = materialize_resolutions(conn, subject=entity, as_of=as_of)
        assert first.inserted == 1
        row1 = conn.execute(
            "SELECT value_text FROM resolution WHERE subject_id = %s",
            (entity,),
        ).fetchone()
        assert row1[0] == "inactive", "B is the latest observation before the re-sighting"

        # Now the re-sighting lands — the link the hook wrote, restored.
        conn.execute(
            "INSERT INTO claim_evidence(claim_id, capture_id, role) VALUES (%s, %s, 'establishes')",
            (claim_a, cap3),
        )
        second = materialize_resolutions(conn, subject=entity, as_of=as_of)
        assert second.inserted == 1 and second.superseded == 1
        rows = conn.execute(
            "SELECT value_text, upper_inf(sys_period) "
            "FROM resolution WHERE subject_id = %s ORDER BY lower(sys_period)",
            (entity,),
        ).fetchall()
        assert [(r[0], r[1]) for r in rows] == [
            ("inactive", False),  # the prior decision: closed, kept as history
            ("active", True),  # the live decision: the restated value wins
        ]

        # The recorded decision labels the capture-time inference on the new basis.
        rules = conn.execute(
            "SELECT evidence_counts -> 'rules_fired' FROM resolution "
            "WHERE subject_id = %s AND upper_inf(sys_period)",
            (entity,),
        ).fetchone()[0]
        assert "SIG-RECON-008:observed_at=capture_retrieved_at_latest" in rules

        # An unchanged re-run is a no-op — and keeps exactly one live row.
        third = materialize_resolutions(conn, subject=entity, as_of=as_of)
        assert third.inserted == 0 and third.superseded == 0 and third.skipped_existing == 1
        live = conn.execute(
            "SELECT count(*) FROM resolution WHERE subject_id = %s AND upper_inf(sys_period)",
            (entity,),
        ).fetchone()[0]
        assert live == 1


def test_a_live_human_decision_blocks_supersession_not_the_batch(clean_dsn: str) -> None:
    """A non-auto live resolution is never closed by the batch supersession."""
    from db.claim_sink import PgClaimSink, record_resightings
    from reconcile.materialize import materialize_resolutions

    subject = "resight_cam:2"
    as_of = date(2026, 10, 1)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = PgClaimSink(conn, connector_name="camreg", on_duplicates=record_resightings)
        sink.assert_claims(_camera_claims(subject, "active"))
        _retime_capture(conn, sink.run_id, "2026-05-01T00:00:00Z")
        entity = _subject_entity(conn, subject)

        first = materialize_resolutions(conn, subject=entity, as_of=as_of)
        assert first.inserted == 1

        # Pin the decision as a human override: supersession must leave it live
        # and the batch must report the pair rather than crash on the exclusion.
        conn.execute(
            "UPDATE resolution SET decided_by = 'human-review', "
            "override_rationale = 'fixture pin' WHERE subject_id = %s",
            (entity,),
        )
        # A re-sighting changes the input digest (the claim's latest capture moves).
        sink2 = PgClaimSink(conn, connector_name="camreg", on_duplicates=record_resightings)
        sink2.assert_claims(_camera_claims(subject, "active"))
        _retime_capture(conn, sink2.run_id, "2026-08-01T00:00:00Z")

        second = materialize_resolutions(conn, subject=entity, as_of=as_of)
        assert second.inserted == 0 and second.superseded == 0 and second.skipped_pinned == 1
        live = conn.execute(
            "SELECT count(*) FROM resolution WHERE subject_id = %s AND upper_inf(sys_period)",
            (entity,),
        ).fetchone()[0]
        assert live == 1  # the human decision stands
