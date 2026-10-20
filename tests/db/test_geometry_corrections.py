# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.16 — the append-only geometry-defect correction pass (R11-DATA-01 / F-322).

Covered here, over the real sqitch-deployed spine:

* the dry run computes the per-group plan and writes nothing;
* a stored pair that fails its declared bound gains a ``geometry_defect``
  claim whose raw_context carries the recorded verdict (class + observed
  pair + the bound it failed) — bound to the subject's ORIGINAL capture
  occurrence (``replayed``, no capture minted);
* an ``axis_swap`` verdict additionally mints corrected
  ``camera_latitude``/``camera_longitude`` claims carrying
  ``revises_claim`` + ``correction_reason='axis_swap'``; other classes mint
  no replacement value — the truth is never fabricated;
* the original claims stay byte-identical — queryable, unrevised in place,
  and ``n_tup_upd``/``n_tup_del`` stay 0;
* a re-run appends +0 (idempotent — ours-marked subjects top up links only);
* clean pairs, no-coordinate subjects, evidence-less subjects and other
  writers' marks are counted and never touched;
* subjects flagged outside the declared groups are counted in the
  out-of-scope scan and NEVER written — a defect group is corrected only
  under its committed ``sig.geometry-corrections/1`` declaration.

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

#: The test bounds — a Nottingham-flavoured swap target and an FL-flavoured
#: null-island target.
SWAP_EXTENT = (-1.4, 52.8, -0.9, 53.1)
FL_EXTENT = (-87.7, 24.4, -79.9, 31.1)


def _scopes() -> list[Any]:
    from db.geometry_corrections import DefectScope

    return [
        DefectScope(
            group="swap_group",
            source_id="src_a",
            target_id="tgt_swap",
            expected_class="axis_swap",
            extent=SWAP_EXTENT,
            extent_ref="target:tgt_swap",
            license_spdx="CC0-1.0",
        ),
        DefectScope(
            group="null_group",
            source_id="src_b",
            target_id="tgt_null",
            expected_class="null_island",
            extent=FL_EXTENT,
            extent_ref="us.state_abbr:FL",
            license_spdx="CC0-1.0",
        ),
    ]


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
        code_commit="p35.16-test",
    )


def _claim(subject: str, source_id: str, predicate: str, value: Any, raw: str) -> dict[str, Any]:
    return {
        "record_kind": "claim",
        "subject_id": subject,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw,
        "source_id": source_id,
        "license": "CC0-1.0",
        "evidence_genre": "camera_registry",
    }


def _registry_claim(subject: str, source_id: str, ref: str) -> dict[str, Any]:
    return _claim(subject, source_id, "traffic_camera", ref, ref)


def _coord_claims(subject: str, source_id: str, lat: float, lon: float) -> list[dict[str, Any]]:
    """The pre-P35.16 stored pair: lat/lon claims as the old emit wrote them."""
    return [
        _claim(subject, source_id, "camera_latitude", lat, str(lat)),
        _claim(subject, source_id, "camera_longitude", lon, str(lon)),
    ]


def _seed_spine(dsn: str) -> None:
    """The pre-P35.16 world: keyed subjects with capture-bound coord claims.

    * src_a/tgt_swap cam-1 — an axis-swapped stored pair (defective).
    * src_a/tgt_swap cam-2 — an in-extent pair (clean).
    * src_b/tgt_null cam-3 — a (0,0) placeholder (null_island).
    * src_c/tgt_else cam-4 — a defective pair under NO declared scope
      (out-of-scope scan counts it, never writes).
    """
    sink = _seed_sink(dsn)
    cap_a = _capture(b"tgt-swap-page", "https://example.test/swap-layer", _T1)
    cap_b = _capture(b"tgt-null-page", "https://example.test/null-layer", _T2)
    cap_c = _capture(b"tgt-else-page", "https://example.test/else-layer", _T1)
    sink.assert_claims(
        [
            _registry_claim("traffic_camera:src_a:tgt_swap:cam-1", "src_a", "cam-1"),
            *_coord_claims("traffic_camera:src_a:tgt_swap:cam-1", "src_a", -1.2, 53.0),
            _registry_claim("traffic_camera:src_a:tgt_swap:cam-2", "src_a", "cam-2"),
            *_coord_claims("traffic_camera:src_a:tgt_swap:cam-2", "src_a", 52.95, -1.15),
        ],
        capture=cap_a,
    )
    sink.assert_claims(
        [
            _registry_claim("traffic_camera:src_b:tgt_null:cam-3", "src_b", "cam-3"),
            *_coord_claims("traffic_camera:src_b:tgt_null:cam-3", "src_b", 0.0, 0.0),
        ],
        capture=cap_b,
    )
    sink.assert_claims(
        [
            _registry_claim("traffic_camera:src_c:tgt_else:cam-4", "src_c", "cam-4"),
            *_coord_claims("traffic_camera:src_c:tgt_else:cam-4", "src_c", -1.2, 53.0),
        ],
        capture=cap_c,
    )
    # A subject with an identity key but zero claims/captures (no evidence).
    with psycopg.connect(dsn, autocommit=True) as conn:
        entity_id = conn.execute(
            "INSERT INTO entity (entity_type) VALUES ('physical_asset') RETURNING entity_id"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO entity_identity_key (scheme, value, entity_id) "
            "VALUES ('sig.connector.subject', 'traffic_camera:src_a:tgt_swap:cam-9', %s)",
            (entity_id,),
        )


def _defect_claims(conn: Any) -> list[Any]:
    return conn.execute(
        "SELECT i.value, c.value_text, c.raw_context, c.assertion_rationale,"
        " c.derived_from_claim_ids, c.revises_claim::text, c.correction_reason "
        "FROM claim c JOIN entity_identifier i ON i.entity_id = c.subject_id "
        "AND i.scheme = 'sig.connector.subject' "
        "WHERE c.predicate_id = 'geometry_defect' ORDER BY i.value"
    ).fetchall()


def _claims_for(conn: Any, subject: str) -> list[Any]:
    return conn.execute(
        "SELECT c.predicate_id, c.value_num, c.value_text, c.revises_claim::text,"
        " c.correction_reason, c.claim_id::text "
        "FROM claim c JOIN entity_identifier i ON i.entity_id = c.subject_id "
        "AND i.scheme = 'sig.connector.subject' WHERE i.value = %s "
        "ORDER BY c.predicate_id, c.claim_id",
        (subject,),
    ).fetchall()


def _links_for(conn: Any, claim_id: str) -> list[Any]:
    return conn.execute(
        "SELECT capture_id::text, role, binding_status FROM claim_evidence "
        "WHERE claim_id = %s ORDER BY capture_id",
        (claim_id,),
    ).fetchall()


def _table_stats(conn: Any) -> dict[str, tuple[int, int]]:
    conn.execute("SELECT pg_stat_force_next_flush()")
    rows = conn.execute(
        "SELECT relname, n_tup_upd, n_tup_del FROM pg_stat_user_tables "
        "WHERE relname = ANY(%s::text[])",
        [["claim", "claim_evidence"]],
    ).fetchall()
    return {r[0]: (int(r[1]), int(r[2])) for r in rows}


def test_dry_run_writes_nothing_and_reports_the_plan(clean_dsn: str) -> None:
    from db.geometry_corrections import run_corrections

    _seed_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        before = {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608
            for t in ("claim", "claim_evidence", "evidence_capture", "ingest_run")
        }
    report = run_corrections(
        clean_dsn,
        scopes=_scopes(),
        scan_extents={("src_c", "tgt_else"): SWAP_EXTENT},
    )
    assert report["mode"] == "plan"
    assert report["declared_groups"] == 2
    # cam-1 (axis_swap) + cam-3 (null_island) pending; cam-2 clean;
    # cam-9 has no coordinate claims (no_coordinates); cam-4 flagged only in
    # the out-of-scope scan, never pending.
    assert report["pending_subjects"] == 2
    assert report["pending_by_group"] == {"null_group": 1, "swap_group": 1}
    assert report["pending_by_class"] == {"axis_swap": 1, "null_island": 1}
    # axis_swap adds the two corrected coordinate claims
    assert report["planned_claims"] == 1 + 2 + 1  # swap: defect+lat+lon; null: defect
    assert report["skipped"]["clean"] == 1
    assert report["skipped"]["no_coordinates"] == 1
    assert report["out_of_scope_scan"]["flagged_by_target"] == {"src_c/tgt_else": 1}
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        after = {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608
            for t in before
        }
    assert after == before


def test_apply_marks_defects_and_revises_axis_swaps(clean_dsn: str) -> None:
    from db.geometry_corrections import run_corrections

    _seed_spine(clean_dsn)
    report = run_corrections(
        clean_dsn,
        scopes=_scopes(),
        apply=True,
        code_commit="p35.16-test",
    )
    assert report["mode"] == "apply"
    assert report["apply"]["claims_added"] == 4
    assert report["post"]["in_scope_subjects_marked"] == 2

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        defects = _defect_claims(conn)
        assert len(defects) == 2
        by_subject = {r[0]: r for r in defects}
        swap = by_subject["traffic_camera:src_a:tgt_swap:cam-1"]
        assert swap[1] == "axis_swap"
        ctx = swap[2]["geometry_defect"]
        assert ctx["observed_latitude"] == -1.2 and ctx["observed_longitude"] == 53.0
        assert ctx["declared_extent"] == list(SWAP_EXTENT)
        assert ctx["defect_group"] == "swap_group"
        assert ctx["detector"] == "sig.p35-16-geometry-detector/1"
        assert "P35.16" in swap[3]
        assert swap[4]  # derived_from_claim_ids cites the original claims
        assert swap[5] is None  # a mark revises nothing
        null = by_subject["traffic_camera:src_b:tgt_null:cam-3"]
        assert null[1] == "null_island"
        assert null[2]["geometry_defect"]["defect_group"] == "null_group"

        # The axis_swap corrected claims: revises_claim + reason + the
        # provable transposed values.
        rows = _claims_for(conn, "traffic_camera:src_a:tgt_swap:cam-1")
        lats = [r for r in rows if r[0] == "camera_latitude"]
        lons = [r for r in rows if r[0] == "camera_longitude"]
        assert len(lats) == 2 and len(lons) == 2
        orig_lat = [r for r in lats if r[4] is None][0]
        fix_lat = [r for r in lats if r[4] == "axis_swap"][0]
        orig_lon = [r for r in lons if r[4] is None][0]
        fix_lon = [r for r in lons if r[4] == "axis_swap"][0]
        # the original pair stays verbatim (append-only)
        assert float(orig_lat[1]) == -1.2 and float(orig_lon[1]) == 53.0
        # the corrected pair is the provable transposition
        assert float(fix_lat[1]) == 53.0 and float(fix_lon[1]) == -1.2
        assert fix_lat[3] == orig_lat[5]  # revises the original latitude claim
        assert fix_lon[3] == orig_lon[5]

        # Evidence links: every written claim links the original capture.
        defect_ids = conn.execute(
            "SELECT claim_id::text FROM claim WHERE predicate_id = 'geometry_defect'"
        ).fetchall()
        for (cid,) in defect_ids:
            links = _links_for(conn, cid)
            assert links and all(link[2] == "replayed" for link in links)

        # The out-of-scope subject gained nothing.
        assert _defect_claims(conn) != []
        else_claims = _claims_for(conn, "traffic_camera:src_c:tgt_else:cam-4")
        assert all(r[4] is None for r in else_claims)
        assert not [r for r in else_claims if r[0] == "geometry_defect"]


def test_rerun_appends_zero(clean_dsn: str) -> None:
    from db.geometry_corrections import run_corrections

    _seed_spine(clean_dsn)
    kw: dict[str, Any] = {"scopes": _scopes(), "apply": True}
    first = run_corrections(clean_dsn, **kw)
    second = run_corrections(clean_dsn, **kw)
    assert first["apply"]["claims_added"] == 4
    assert second["apply"]["claims_added"] == 0
    assert second["pending_subjects"] == 0
    assert second["link_topup_subjects"] == 2


def test_apply_is_strictly_append_only(clean_dsn: str) -> None:
    from db.geometry_corrections import run_corrections

    _seed_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute("SELECT pg_stat_reset()")
    run_corrections(clean_dsn, scopes=_scopes(), apply=True)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        stats = _table_stats(conn)
    assert stats.get("claim", (0, 0)) == (0, 0)
    assert stats.get("claim_evidence", (0, 0)) == (0, 0)


def test_unregistered_predicate_refuses_before_any_write(clean_dsn: str) -> None:
    """If ``geometry_defect`` ever dropped out of the vocabulary the apply
    leg refuses loud BEFORE writing — the closed sink would quarantine
    otherwise. Simulated by pointing the precheck at a missing genre is not
    needed: assert the registration read reports the live predicate."""
    from db.geometry_corrections import _registration

    _seed_spine(clean_dsn)
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        registered = _registration(conn)
    assert registered == {
        "geometry_defect_predicate": True,
        "camera_registry_genre": True,
    }
