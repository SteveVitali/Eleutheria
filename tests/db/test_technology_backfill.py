# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.15b — the append-only ``technology``-claim backfill (PKG-07 / F-329 / F-523).

Covered here, over the real sqitch-deployed spine:

* the dry run computes the per-target/per-slug plan and writes nothing;
* ``--apply`` lands ordinary ``sig.assertion/1`` technology claims whose value
  is the TARGET'S DECLARED slug — bound to the subject's ORIGINAL capture
  occurrence (``replayed``, no capture minted) and linked to every existing
  capture ('establishes' chosen, 'corroborates' the rest);
* every written claim carries the backfill provenance: rationale, derived-from
  registry-record claims, ``declared_technology_backfill`` extraction method,
  ``technology-backfill`` run;
* a re-run appends +0 (idempotent); an ours-typed subject missing links gets
  them topped up (interrupted-run convergence);
* undeclared targets, other-writer claims, and evidence-less subjects are
  counted and never touched;
* chunked commits (``commit_chunk_size=1``) land identically;
* ``n_tup_upd``/``n_tup_del`` stay 0 on ``claim``/``claim_evidence``.

DB-gated: runs under ``SIG_REQUIRE_DB_TESTS`` (``make test-db``) and skips
without Docker.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

_SPINE_TABLES = (
    "claim_qualifier",
    "claim_evidence",
    "assertion_quarantine",
    "claim",
    "extraction",
    "ingest_run_capture",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "entity_identifier",
    "entity_type_decision",
    "entity_identity_key",
    "ingest_run",
    "source_registry",
    "entity",
)
_TRUNCATE = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"

_T1 = datetime(2026, 5, 1, tzinfo=UTC)
_T2 = datetime(2026, 6, 1, tzinfo=UTC)

DECLARED = {
    ("src_a", "tgt_alpr"): "alpr-fixed",
    ("src_a", "tgt_cctv"): "fixed-camera-cctv",
}
LICENSES = {k: "CC0-1.0" for k in DECLARED}


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    """A DSN whose spine is truncated before AND after the test."""
    dsn = _dsn(sig_database)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(_TRUNCATE)


def _capture(body: bytes, uri: str, when: datetime, *, version: str = "v1") -> Any:
    """A CaptureRef shaped like the one OcflCaptureStore.put returns."""
    from connectors.stages import CaptureRef
    from evidence.digest import multihash

    d = multihash(body)
    return CaptureRef(
        digest=d,
        media_type="application/json",
        source_uri=uri,
        byte_size=len(body),
        retrieved_at=when,
        ocfl_object_id=f"sig:capture:{d}",
        ocfl_version=version,
    )


def _seed_sink(dsn: str, *, connector_name: str = "dot_511") -> Any:
    from db.claim_sink import PgClaimSink

    return PgClaimSink.from_dsn(
        dsn,
        connector_name=connector_name,
        connector_version="1.0.0",
        code_commit="p35.15b-test",
    )


def _registry_claim(subject: str, source_id: str, ref: str) -> dict[str, Any]:
    """A pre-PKG-07 registry-record claim (no technology claim anywhere)."""
    return {
        "record_kind": "claim",
        "subject_id": subject,
        "predicate_id": "traffic_camera",
        "value": ref,
        "raw_value": ref,
        "source_id": source_id,
        "license": "CC0-1.0",
        "evidence_genre": "camera_registry",
    }


def _seed_spine(dsn: str) -> dict[str, str]:
    """Mint the pre-PKG-07 world: keyed subjects with real capture-bound claims.

    Returns the two seeded captures' ids for assertions.
    """
    sink = _seed_sink(dsn)
    cap_a = _capture(b"tgt-alpr-page", "https://example.test/alpr-layer", _T1)
    cap_b = _capture(b"tgt-cctv-page", "https://example.test/cctv-layer", _T2)
    sink.assert_claims(
        [
            _registry_claim("traffic_camera:src_a:tgt_alpr:cam-1", "src_a", "cam-1"),
            _registry_claim("traffic_camera:src_a:tgt_alpr:cam-2", "src_a", "cam-2"),
            _registry_claim("traffic_camera:src_a:tgt_cctv:cam-3", "src_a", "cam-3"),
            # A second sighting of cam-3 on cap_b's artifact? No — keep one
            # subject per capture; cam-3 gets a SECOND capture below.
        ],
        capture=cap_a,
    )
    sink.assert_claims(
        [
            _registry_claim("traffic_camera:src_a:tgt_cctv:cam-3", "src_a", "cam-3b"),
            # Undeclared target: exists on the spine, declares nothing.
            _registry_claim("traffic_camera:src_b:tgt_none:cam-4", "src_b", "cam-4"),
        ],
        capture=cap_b,
    )
    # A subject with an identity key but zero claims/captures (no evidence).
    with psycopg.connect(dsn, autocommit=True) as conn:
        entity_id = conn.execute(
            "INSERT INTO entity (entity_type) VALUES ('physical_asset') RETURNING entity_id"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO entity_identity_key (scheme, value, entity_id) "
            "VALUES ('sig.connector.subject', 'traffic_camera:src_a:tgt_alpr:cam-9', %s)",
            (entity_id,),
        )
    return {"cap_a_uri": cap_a.source_uri, "cap_b_uri": cap_b.source_uri}


def _tech_claims(conn: Any) -> list[Any]:
    return conn.execute(
        "SELECT c.claim_id::text, i.value, c.value_text, c.assertion_rationale,"
        " c.extraction_id::text, c.ingest_run_id::text, c.derived_from_claim_ids,"
        " c.observed_at "
        "FROM claim c JOIN entity_identifier i ON i.entity_id = c.subject_id "
        "AND i.scheme = 'sig.connector.subject' "
        "WHERE c.predicate_id = 'technology' ORDER BY i.value"
    ).fetchall()


def _links_for(conn: Any, claim_id: str) -> list[Any]:
    return conn.execute(
        "SELECT capture_id::text, role, binding_status FROM claim_evidence "
        "WHERE claim_id = %s ORDER BY capture_id",
        (claim_id,),
    ).fetchall()


def _table_counts(conn: Any, tables: tuple[str, ...] = ("claim", "claim_evidence")) -> dict:
    conn.execute("SELECT pg_stat_force_next_flush()")
    rows = conn.execute(
        "SELECT relname, n_tup_upd, n_tup_del FROM pg_stat_user_tables "
        "WHERE relname = ANY(%s::text[])",
        (list(tables),),
    ).fetchall()
    return {r[0]: (int(r[1]), int(r[2])) for r in rows}


def test_dry_run_writes_nothing_and_reports_the_plan(clean_dsn: str) -> None:
    from db.technology_backfill import run_backfill

    _seed_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        before = {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608
            for t in ("claim", "claim_evidence", "evidence_capture", "ingest_run")
        }
    report = run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES)
    assert report["mode"] == "plan"
    assert report["pending_claims"] == 3  # cam-1, cam-2, cam-3
    assert report["pending_by_slug"] == {"alpr-fixed": 2, "fixed-camera-cctv": 1}
    assert report["pending_by_target"] == {
        "src_a/tgt_alpr": 2,
        "src_a/tgt_cctv": 1,
    }
    assert report["skipped"]["undeclared"] == 1  # cam-4
    assert report["undeclared_by_target"] == {"src_b/tgt_none": 1}
    assert report["skipped"]["no_evidence"] == 1  # cam-9
    assert report["registered"] == {
        "technology_predicate": True,
        "camera_registry_genre": True,
    }
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        after = {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608
            for t in ("claim", "claim_evidence", "evidence_capture", "ingest_run")
        }
    assert after == before, "a dry run must never write"


def test_apply_writes_declared_claims_bound_to_existing_captures(clean_dsn: str) -> None:
    from db.technology_backfill import run_backfill

    _seed_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        caps_before = {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608
            for t in ("evidence_capture", "evidence_artifact", "evidence_blob")
        }
    report = run_backfill(
        clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True, code_commit="p35.15b"
    )
    assert "refused" not in report
    applied = report["apply"]
    assert applied["claims_added"] == 3
    assert applied["quarantined"] == 0
    # One supplementary row per (claim, existing capture): cam-1 + cam-2 carry
    # one capture each, cam-3 two (its 'establishes' on the chosen capture was
    # already written typed by the sink — the +1 is its 'corroborates' row).
    assert applied["links_planned"] == 4
    assert applied["links_inserted"] == 1
    assert report["post"]["in_scope_subjects_with_technology"] == 3
    assert report["post"]["in_scope_subjects_without_technology"] == 1  # cam-9

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # No captures/artifacts/blobs minted — the backfill cites EXISTING ones.
        caps_after = {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608
            for t in ("evidence_capture", "evidence_artifact", "evidence_blob")
        }
        assert caps_after == caps_before

        rows = _tech_claims(conn)
        assert {r[1]: r[2] for r in rows} == {
            "traffic_camera:src_a:tgt_alpr:cam-1": "alpr-fixed",
            "traffic_camera:src_a:tgt_alpr:cam-2": "alpr-fixed",
            "traffic_camera:src_a:tgt_cctv:cam-3": "fixed-camera-cctv",
        }
        for claim_id, _subject, _slug, rationale, extraction_id, run_id, derived, observed in rows:
            # Backfill provenance, never passed off as connector-fresh.
            assert rationale and "P35.15b" in rationale
            assert derived, "every backfilled claim cites its registry-record claims"
            run = conn.execute(
                "SELECT connector_name, is_replay FROM ingest_run WHERE run_id = %s",
                (run_id,),
            ).fetchone()
            assert run == ("technology-backfill", True)
            method = conn.execute(
                "SELECT method FROM extraction WHERE extraction_id = %s",
                (extraction_id,),
            ).fetchone()
            assert method == ("declared_technology_backfill",)
            # Bound to an EXISTING capture with the 'replayed' classification;
            # extra captures corroborate (cam-3 was sighted on two captures).
            links = _links_for(conn, claim_id)
            assert links, "no claim is written without an evidence link"
            establishes = [lnk for lnk in links if lnk[1] == "establishes"]
            assert len(establishes) == 1
            assert establishes[0][2] == "replayed"
            cap_at = conn.execute(
                "SELECT retrieved_at FROM evidence_capture WHERE capture_id = %s",
                (establishes[0][0],),
            ).fetchone()[0]
            assert observed == cap_at  # capture_retrieved_at observed-time basis
        roles_by_subject = {
            "traffic_camera:src_a:tgt_cctv:cam-3": {"establishes", "corroborates"},
            "traffic_camera:src_a:tgt_alpr:cam-1": {"establishes"},
        }
        for subj, expected in roles_by_subject.items():
            (claim_id,) = (r[0] for r in rows if r[1] == subj)
            assert {lnk[1] for lnk in _links_for(conn, claim_id)} == expected


def test_second_apply_is_plus_zero(clean_dsn: str) -> None:
    from db.technology_backfill import run_backfill

    _seed_spine(clean_dsn)
    run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    report = run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    applied = report["apply"]
    assert applied["claims_added"] == 0
    assert applied["links_inserted"] == 0
    assert report["already_typed"]["this_connector"] == 3


def test_ours_typed_subject_gets_links_topped_up(clean_dsn: str) -> None:
    """Interrupted-run convergence: a subject carrying OUR claim but missing
    evidence links gains them on re-run — never a second claim."""
    from db.technology_backfill import CONNECTOR_NAME, run_backfill

    _seed_spine(clean_dsn)
    # Simulate the interrupted run: OUR claim exists (legacy link only).
    ours = _seed_sink(clean_dsn, connector_name=CONNECTOR_NAME)
    ours.assert_claims(
        [
            {
                "record_kind": "claim",
                "subject_id": "traffic_camera:src_a:tgt_alpr:cam-1",
                "predicate_id": "technology",
                "value": "alpr-fixed",
                "raw_value": "alpr-fixed",
                "source_id": "src_a",
                "license": "CC0-1.0",
                "evidence_genre": "camera_registry",
                "extraction_method": "declared_technology_backfill",
            }
        ]
    )
    report = run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    applied = report["apply"]
    # cam-1 was already ours → only cam-2 + cam-3 are new claims.
    assert applied["claims_added"] == 2
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        links = conn.execute(
            "SELECT ce.role, ec.capture_classification FROM claim_evidence ce "
            "JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
            "JOIN claim c ON c.claim_id = ce.claim_id "
            "JOIN entity_identifier i ON i.entity_id = c.subject_id "
            "WHERE i.value = 'traffic_camera:src_a:tgt_alpr:cam-1' "
            "AND c.predicate_id = 'technology' ORDER BY ce.role"
        ).fetchall()
        roles = {r[0] for r in links}
        assert "establishes" in roles
        # The existing actual capture is linked, not just the run's synthetic one.
        assert "actual" in {r[1] for r in links}
    # And the topped-up subject converges: a further run is +0 everywhere.
    again = run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    assert again["apply"]["claims_added"] == 0
    assert again["apply"]["links_inserted"] == 0


def test_undeclared_and_other_writer_subjects_are_untouched(clean_dsn: str) -> None:
    from db.technology_backfill import run_backfill

    _seed_spine(clean_dsn)
    # An OTHER writer's technology claim on a declared subject — never touched.
    other = _seed_sink(clean_dsn, connector_name="dot_511")
    other.assert_claims(
        [
            {
                "record_kind": "claim",
                "subject_id": "traffic_camera:src_a:tgt_alpr:cam-2",
                "predicate_id": "technology",
                "value": "alpr-fixed",
                "raw_value": "alpr-fixed",
                "source_id": "src_a",
                "license": "CC0-1.0",
                "evidence_genre": "camera_registry",
                "extraction_method": "arcgis_feature_json",
            }
        ]
    )
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        links_before = conn.execute(
            "SELECT count(*) FROM claim_evidence ce JOIN claim c ON c.claim_id = ce.claim_id "
            "JOIN entity_identifier i ON i.entity_id = c.subject_id "
            "WHERE i.value = 'traffic_camera:src_a:tgt_alpr:cam-2' "
            "AND c.predicate_id = 'technology'"
        ).fetchone()[0]
    report = run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    # cam-2 already typed by another writer → only cam-1 + cam-3 are new.
    assert report["apply"]["claims_added"] == 2
    assert report["already_typed"]["other"] == 1
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        links_after = conn.execute(
            "SELECT count(*) FROM claim_evidence ce JOIN claim c ON c.claim_id = ce.claim_id "
            "JOIN entity_identifier i ON i.entity_id = c.subject_id "
            "WHERE i.value = 'traffic_camera:src_a:tgt_alpr:cam-2' "
            "AND c.predicate_id = 'technology'"
        ).fetchone()[0]
        assert links_after == links_before, "an other-writer claim never gains our links"
        # The undeclared subject gained no claim at all.
        assert (
            conn.execute(
                "SELECT count(*) FROM claim c JOIN entity_identifier i "
                "ON i.entity_id = c.subject_id "
                "WHERE i.value = 'traffic_camera:src_b:tgt_none:cam-4'"
            ).fetchone()[0]
            == 1  # just its seeded registry claim
        )


def test_chunked_commits_land_identically(clean_dsn: str) -> None:
    from db.technology_backfill import run_backfill

    _seed_spine(clean_dsn)
    report = run_backfill(
        clean_dsn,
        declared=DECLARED,
        licenses=LICENSES,
        apply=True,
        commit_chunk_size=1,
    )
    assert report["apply"]["claims_added"] == 3
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert len(_tech_claims(conn)) == 3


def test_no_update_or_delete_on_the_claim_spine(clean_dsn: str) -> None:
    from db.technology_backfill import run_backfill

    _seed_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        before = _table_counts(conn)
    run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        after = _table_counts(conn)
    assert after == before, f"UPDATE/DELETE counters moved: {before} -> {after}"


def test_unregistered_predicate_refuses_before_writing(clean_dsn: str, monkeypatch: Any) -> None:
    """The live leg's voided-by check: a missing `technology` registration
    refuses the apply instead of quarantining every claim (P35.14a)."""
    import db.technology_backfill as tb

    _seed_spine(clean_dsn)
    monkeypatch.setattr(
        tb,
        "_registration",
        lambda conn: {"technology_predicate": False, "camera_registry_genre": True},
    )
    report = tb.run_backfill(clean_dsn, declared=DECLARED, licenses=LICENSES, apply=True)
    assert report["refused"]
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        assert _tech_claims(conn) == []
