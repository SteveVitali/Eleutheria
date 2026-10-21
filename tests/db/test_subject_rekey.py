# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Live-PG contract for the subject re-key run (P35.24 / ADR-212).

A REAL spine is seeded with collided subject keys (two upstream records
merged under one pinned key — the L2-M07/F-518 defect class), then
``db.subject_rekey`` plans and applies. Asserts the whole contract: collision
re-derivation, evidence-bundle constituent split, sys_period close + appended
corrections (never UPDATE/DELETE beyond the permitted close), evidence
re-binding, decision rows, unplaced claims staying put, and +0 on rerun.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest

_T1 = datetime(2026, 8, 1, tzinfo=UTC)
_T2 = datetime(2026, 8, 2, tzinfo=UTC)

_SPINE_TABLES = (
    "subject_rekey_decision",
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "entity_identifier",
    "entity_identity_key",
    "ingest_run",
    "entity",
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def clean_dsn(sig_database: dict[str, object]) -> Iterator[str]:
    """Truncated spine — every predicate this file uses is already a real
    vocab member, so no fixture registration is needed."""
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _capture(body: bytes, uri: str, when: datetime) -> Any:
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
        ocfl_version="v1",
    )


def _sink(dsn: str) -> Any:
    from db.claim_sink import PgClaimSink

    return PgClaimSink.from_dsn(
        dsn, connector_name="dot_511", connector_version="1.0.0", code_commit="p35.24-test"
    )


def _claim(
    subject: str,
    source_id: str,
    predicate: str,
    value: Any,
    raw: str,
    locator: dict | None = None,
    raw_context: dict | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "record_kind": "claim",
        "subject_id": subject,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw,
        "source_id": source_id,
        "license": "CC0-1.0",
        "evidence_genre": "camera_registry",
    }
    if locator is not None:
        row["locator"] = locator
    if raw_context is not None:
        row["raw_context"] = raw_context
    return row


def _seed_collided_camera(dsn: str) -> str:
    """`traffic_camera:src_a:tgt_dup:cam-9` merges TWO real cameras:
    capture A's row says (35.0, -97.0), capture B's says (35.5, -97.5) —
    the F-518 shape. A third bundle carries a camera_operator claim with no
    coordinate → stays unplaced on the legacy key."""
    sink = _sink(dsn)
    subject = "traffic_camera:src_a:tgt_dup:cam-9"
    sink.assert_claims(
        [
            _claim(
                subject,
                "src_a",
                "traffic_camera",
                "cam-9",
                "cam-9",
                locator={"kind": "row", "row": 0},
            ),
            _claim(
                subject, "src_a", "camera_latitude", 35.0, "35.0", locator={"kind": "row", "row": 0}
            ),
            _claim(
                subject,
                "src_a",
                "camera_longitude",
                -97.0,
                "-97.0",
                locator={"kind": "row", "row": 0},
            ),
        ],
        capture=_capture(b"cap-a", "https://example.test/layer-a", _T1),
    )
    sink.assert_claims(
        [
            _claim(
                subject, "src_a", "camera_latitude", 35.5, "35.5", locator={"kind": "row", "row": 1}
            ),
            _claim(
                subject,
                "src_a",
                "camera_longitude",
                -97.5,
                "-97.5",
                locator={"kind": "row", "row": 1},
            ),
        ],
        capture=_capture(b"cap-b", "https://example.test/layer-b", _T2),
    )
    sink.assert_claims(
        [
            _claim(
                subject,
                "src_a",
                "camera_operator",
                "OK DOT",
                "OK DOT",
                locator={"kind": "row", "row": 2},
            ),
        ],
        capture=_capture(b"cap-c", "https://example.test/layer-c", _T2),
    )
    return subject


def _seed_collided_atlas(dsn: str) -> str:
    """Legacy `atlas:Fresno PD:alpr` with two captures evidencing DIFFERENT
    states (cross-state agency merge — F-506)."""
    sink = _sink(dsn)
    subject = "atlas:Fresno PD:alpr"
    sink.assert_claims(
        [
            _claim(
                subject,
                "atlas",
                "deployment_exists",
                True,
                "ALPR",
                locator={"kind": "row", "row": 0},
                raw_context={"State": "CA"},
            ),
        ],
        capture=_capture(b"atlas-ca", "https://example.test/atlas-ca.csv", _T1),
    )
    sink.assert_claims(
        [
            _claim(
                subject,
                "atlas",
                "deployment_exists",
                True,
                "ALPR",
                locator={"kind": "row", "row": 1},
                raw_context={"State": "TX"},
            ),
        ],
        capture=_capture(b"atlas-tx", "https://example.test/atlas-tx.csv", _T2),
    )
    return subject


def _current_claims(conn: Any, subject: str) -> list[Any]:
    return conn.execute(
        "SELECT c.claim_id::text, c.predicate_id, c.revises_claim::text,"
        " c.correction_reason, c.value_text, c.value_num "
        "FROM claim c JOIN entity_identifier i ON i.entity_id = c.subject_id"
        " AND i.scheme = 'sig.connector.subject' AND i.value = %s"
        " WHERE upper_inf(c.sys_period) ORDER BY c.predicate_id",
        (subject,),
    ).fetchall()


def _closed_claims(conn: Any, subject: str) -> list[Any]:
    return conn.execute(
        "SELECT c.claim_id::text, c.predicate_id FROM claim c"
        " JOIN entity_identifier i ON i.entity_id = c.subject_id"
        " AND i.scheme = 'sig.connector.subject' AND i.value = %s"
        " WHERE NOT upper_inf(c.sys_period) ORDER BY c.predicate_id",
        (subject,),
    ).fetchall()


def test_collision_scan_rederives_the_collided_set(clean_dsn: str) -> None:
    from db.subject_rekey import collision_scan

    _seed_collided_camera(clean_dsn)
    _seed_collided_atlas(clean_dsn)
    with psycopg.connect(clean_dsn, row_factory=psycopg.rows.dict_row) as conn:
        found = {c.value: c for c in collision_scan(conn)}
    assert set(found) == {
        "traffic_camera:src_a:tgt_dup:cam-9",
        "atlas:Fresno PD:alpr",
    }
    cam = found["traffic_camera:src_a:tgt_dup:cam-9"]
    assert cam.pin_id == "traffic_camera" and cam.distinct_values == 2


def test_plan_groups_claims_into_coordinate_constituents(clean_dsn: str) -> None:
    from db.subject_rekey import collision_scan, plan_subject

    subject = _seed_collided_camera(clean_dsn)
    with psycopg.connect(clean_dsn, row_factory=psycopg.rows.dict_row) as conn:
        [col] = [c for c in collision_scan(conn) if c.value == subject]
        plan = plan_subject(conn, col)
    assert plan.parsed is not None and plan.parsed.pin.pin_id == "traffic_camera"
    constituents = {m.new_value for m in plan.moves}
    # 5 claims move into 2 constituents (the registry claim shares bundle A's
    # locator); only the operator claim (its own coordinate-free bundle) stays
    assert len(plan.moves) == 5 and len(constituents) == 2
    assert all(v.startswith("traffic_camera:src_a:tgt_dup:cam-9:s") for v in constituents)
    assert len(plan.unplaced) == 1  # camera_operator — no coordinate evidence


def test_apply_moves_claims_append_only(clean_dsn: str) -> None:
    from db.subject_rekey import run

    subject = _seed_collided_camera(clean_dsn)
    report = run(clean_dsn, apply_mode=True)
    assert report["totals"]["pre_collision_count"] == 1
    assert report["totals"]["post_collision_count"] == 0
    assert report["totals"]["corrections_applied"] == 5
    assert report["totals"]["constituents"] == 2
    assert report["totals"]["unplaced_claims"] == 1

    with psycopg.connect(clean_dsn, row_factory=psycopg.rows.dict_row) as conn:
        # every moved claim closed; the corrections carry the markers
        closed = _closed_claims(conn, subject)
        assert len(closed) == 5
        remaining = _current_claims(conn, subject)
        assert {r["predicate_id"] for r in remaining} == {"camera_operator"}
        # constituents hold the split claims, revision-linked to their priors
        rows = conn.execute(
            "SELECT i.value, c.predicate_id, c.revises_claim::text, c.correction_reason,"
            " c.content_digest FROM claim c"
            " JOIN entity_identifier i ON i.entity_id = c.subject_id"
            "  AND i.scheme = 'sig.connector.subject'"
            " WHERE i.value LIKE 'traffic_camera:src_a:tgt_dup:cam-9:s%'"
            "  AND upper_inf(c.sys_period) ORDER BY i.value, c.predicate_id",
        ).fetchall()
        assert len(rows) == 5
        values = {r["value"] for r in rows}
        assert len(values) == 2
        assert all(r["revises_claim"] is not None for r in rows)
        assert all(r["correction_reason"] == "subject_rekey_constituent" for r in rows)
        assert all(r["content_digest"] is not None for r in rows)  # identity-class digest
        # evidence re-bound: each new claim links its capture
        new_ids = conn.execute(
            "SELECT c.claim_id::text AS claim_id FROM claim c"
            " JOIN entity_identifier i ON i.entity_id = c.subject_id"
            "  AND i.scheme = 'sig.connector.subject'"
            " WHERE i.value LIKE 'traffic_camera:src_a:tgt_dup:cam-9:s%'"
        ).fetchall()
        for r in new_ids:
            n = conn.execute(
                "SELECT count(*) FROM claim_evidence WHERE claim_id = %s::uuid",
                (r["claim_id"],),
            ).fetchone()["count"]
            assert n >= 1
        # decisions recorded (append-only)
        decisions = conn.execute(
            "SELECT old_value, new_value, claims_moved, registry_version, decided_by"
            " FROM subject_rekey_decision ORDER BY new_value",
        ).fetchall()
        assert len(decisions) == 2
        assert sorted(d["claims_moved"] for d in decisions) == [2, 3]  # 3+2 claims split
        assert all(d["old_value"] == subject for d in decisions)
        assert all(d["registry_version"] == "sig.subject-key-pins/1" for d in decisions)


def test_rerun_is_zero_writes(clean_dsn: str) -> None:
    from db.subject_rekey import run

    subject = _seed_collided_camera(clean_dsn)
    run(clean_dsn, apply_mode=True)
    again = run(clean_dsn, apply_mode=True)
    assert again["totals"]["corrections_applied"] == 0
    with psycopg.connect(clean_dsn) as conn:
        decisions = conn.execute(
            "SELECT count(*) FROM subject_rekey_decision WHERE old_value = %s", (subject,)
        ).fetchone()[0]
        assert decisions == 2
        closed = conn.execute(
            "SELECT count(*) FROM claim c JOIN entity_identifier i"
            " ON i.entity_id = c.subject_id AND i.scheme='sig.connector.subject'"
            " AND i.value = %s WHERE NOT upper_inf(c.sys_period)",
            (subject,),
        ).fetchone()[0]
        assert closed == 5


def test_plan_only_touches_nothing(clean_dsn: str) -> None:
    from db.subject_rekey import run

    subject = _seed_collided_camera(clean_dsn)
    report = run(clean_dsn)
    assert report["mode"] == "plan"
    assert report["collided_subjects"] == 1
    assert report["totals"]["corrections_planned"] == 5
    with psycopg.connect(clean_dsn) as conn:
        assert len(_current_claims(conn, subject)) == 6
        assert conn.execute("SELECT count(*) FROM subject_rekey_decision").fetchone()[0] == 0
        assert (
            conn.execute(
                "SELECT count(*) FROM ingest_run WHERE connector_name = 'subject-rekey'"
            ).fetchone()[0]
            == 0
        )


def test_atlas_collision_splits_per_evidenced_state(clean_dsn: str) -> None:
    from db.subject_rekey import run

    _seed_collided_atlas(clean_dsn)
    report = run(clean_dsn, apply_mode=True)
    assert report["totals"]["corrections_applied"] == 2
    with psycopg.connect(clean_dsn) as conn:
        values = conn.execute(
            "SELECT DISTINCT i.value FROM entity_identifier i"
            " WHERE i.scheme = 'sig.connector.subject'"
            "  AND i.value LIKE 'atlas:us.state_abbr:%'",
        ).fetchall()
        assert {r[0] for r in values} == {
            "atlas:us.state_abbr:CA:Fresno PD:alpr",
            "atlas:us.state_abbr:TX:Fresno PD:alpr",
        }
        # nothing stays current under the collided legacy key
        assert _current_claims(conn, "atlas:Fresno PD:alpr") == []


def test_subject_key_pin_seeds_mirror_and_are_immutable(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn) as conn:
        rows = conn.execute(
            "SELECT pin_id, registry_version FROM subject_key_pin ORDER BY pin_id"
        ).fetchall()
        assert len(rows) == 6
        assert all(r[1] == "sig.subject-key-pins/1" for r in rows)
        with pytest.raises(Exception, match="immutable"):
            conn.execute("UPDATE subject_key_pin SET family = 'x:' WHERE pin_id = 'traffic_camera'")
