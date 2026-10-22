# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of the transparency views (P35.33 / J3 §3.1 + §3.3 items
1–2, K10 §18 C-13): explicit columns only, ``sig_export``-only grants, and
the engine-side shared-run suppression the export's honesty tokens render.

* Column closure against ``policy.transparency`` allow-lists is also a unit
  test (``tests/unit/test_transparency_view_columns.py``); here we prove the
  deployed engine agrees.
* Never-exported fields (``parameters``/``environment``/``detail``/
  ``run_record_uri``/``request_fingerprint``/``payload``) are absent from
  both views.
* A run serving two recorded executions renders run-owned values NULL
  (C-13); the sole-execution run keeps them.
* The capture view binds a mark to its capture row 1:1 (LATERAL join — a
  mark never fans out), joins the artifact's source, and shows marks
  without a capture row with NULL capture fields.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from policy.transparency import (
    NEVER_EXPORTED_FIELDS,
    TRANSPARENCY_CAPTURE_VIEW_COLUMNS,
    TRANSPARENCY_RUN_VIEW_COLUMNS,
    TRANSPARENCY_SOURCE_VIEW_COLUMNS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_SPINE_TABLES = (
    "ingest_run_report",
    "ingest_run_completion",
    "source_redistribution",
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "ingest_run_capture",
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


def _insert_run(conn: psycopg.Connection, code_commit: str = "deadbeef") -> str:
    return str(
        conn.execute(
            "INSERT INTO ingest_run"
            " (connector_name, connector_version, code_commit, ruleset_version,"
            "  vocab_version, parameters, environment, input_digests)"
            " VALUES ('sig.test.transparency','0.0.0',%s,'1.0.0','1.0.0',"
            "        '{}'::jsonb,'{}'::jsonb,'{}')"
            " RETURNING run_id",
            (code_commit,),
        ).fetchone()[0]
    )


def _insert_report(
    conn: psycopg.Connection,
    run_id: str | None,
    source: str,
    link_basis: str = "live",
    clock_basis: str = "db",
    backfilled_from: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO ingest_run_report"
        " (run_id, source_id, link_basis, clock_basis, fetches, records_emitted,"
        "  backfilled_from)"
        " VALUES (%s, %s, %s, %s, 1, 5, %s)",
        (run_id, source, link_basis, clock_basis, backfilled_from),
    )


def test_view_columns_match_the_allow_lists(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        for view, expected in (
            ("v_transparency_run", TRANSPARENCY_RUN_VIEW_COLUMNS),
            ("v_transparency_capture", TRANSPARENCY_CAPTURE_VIEW_COLUMNS),
        ):
            cols = [
                r[0]
                for r in conn.execute(
                    "SELECT column_name FROM information_schema.columns"
                    " WHERE table_name = %s ORDER BY ordinal_position",
                    (view,),
                )
            ]
            assert cols == list(expected), view
            assert not NEVER_EXPORTED_FIELDS.intersection(cols)


def test_grants_sig_export_only(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        for view in ("v_transparency_run", "v_transparency_capture"):
            grantees = {
                r[0]
                for r in conn.execute(
                    "SELECT grantee FROM information_schema.role_table_grants"
                    " WHERE table_name = %s AND privilege_type = 'SELECT'",
                    (view,),
                )
            }
            assert "sig_export" in grantees, view
            assert "sig_read_public" not in grantees, view


def test_shared_run_suppresses_run_owned_values(clean_dsn: str) -> None:
    """Two executions recorded on one run → both view rows carry
    shared_run=true and NULL run-owned fields (C-13); the sole-execution
    run keeps them."""
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        shared = _insert_run(conn, "deadbeef")
        conn.execute(
            "INSERT INTO ingest_run_completion"
            " (run_id, source_id, status, claims_inserted)"
            " VALUES (%s, 'src.shared.demo', 'ok', 7)",
            (shared,),
        )
        _insert_report(conn, shared, "src.shared.demo", "live", "db")
        _insert_report(
            conn,
            shared,
            "src.shared.demo",
            "backfill:sole-candidate",
            "run_row",
            backfilled_from="gs://sig-test/ops/runs/src.shared.demo/1.json",
        )

        sole = _insert_run(conn, "cafef00d")
        conn.execute(
            "INSERT INTO ingest_run_completion"
            " (run_id, source_id, status, claims_inserted)"
            " VALUES (%s, 'src.sole.demo', 'ok', 11)",
            (sole,),
        )
        _insert_report(conn, sole, "src.sole.demo")

        shared_rows = conn.execute(
            "SELECT shared_run, code_commit, connector_name, claims_inserted,"
            "       finished_at, completion_status"
            "  FROM v_transparency_run WHERE run_id = %s",
            (shared,),
        ).fetchall()
        assert len(shared_rows) == 2
        for row in shared_rows:
            assert row[0] is True
            assert all(v is None for v in row[1:]), row

        sole_row = conn.execute(
            "SELECT shared_run, code_commit, claims_inserted, completion_status"
            "  FROM v_transparency_run WHERE run_id = %s",
            (sole,),
        ).fetchone()
        assert sole_row == (False, "cafef00d", 11, "ok")


def test_never_exported_fields_absent_even_when_populated(clean_dsn: str) -> None:
    """A run holding parameters/environment and a completion holding
    detail/run_record_uri still emits none of them through the view."""
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        run = conn.execute(
            "INSERT INTO ingest_run"
            " (connector_name, connector_version, code_commit, ruleset_version,"
            "  vocab_version, parameters, environment, input_digests)"
            " VALUES ('sig.test.transparency','0.0.0','aa','1.0.0','1.0.0',"
            '        \'{"token":"s3cr3t"}\'::jsonb,'
            "        '{\"AWS_SECRET\":\"xyz\"}'::jsonb,'{}')"
            " RETURNING run_id"
        ).fetchone()[0]
        _insert_report(conn, str(run), "src.secret.demo")
        row = conn.execute(
            "SELECT * FROM v_transparency_run WHERE run_id = %s",
            (run,),
        ).fetchone()
        cols = [
            d.name for d in conn.execute("SELECT * FROM v_transparency_run WHERE FALSE").description
        ]
        rec = dict(zip(cols, row, strict=False))
        blob = str(rec)
        for secret in ("s3cr3t", "AWS_SECRET", "xyz"):
            assert secret not in blob


def test_capture_view_binds_mark_to_capture_one_to_one(clean_dsn: str) -> None:
    """A flushed mark joins its evidence_capture via the content digest —
    exactly one view row per mark (the LATERAL join never fans out)."""
    from conftest import seed_claim_prerequisites

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        prereqs = seed_claim_prerequisites(conn)
        run = _insert_run(conn)
        conn.execute(
            "INSERT INTO source_registry(source_id,name,source_kind,"
            "default_reliability,reliability_justification,rights_id,"
            "custody_posture,compact_status,robots_policy) "
            "VALUES('cap_src','Fixture','portal','R2','fixture',%s,"
            "'MIRROR','no_response','obey')",
            (prereqs["rights_id"],),
        )
        artifact = conn.execute(
            "INSERT INTO evidence_artifact(source_id,stable_locator,"
            "artifact_type,acquisition_method,primary_or_secondary,rights_id,"
            "capture_status) "
            "VALUES('cap_src','urn:sig:cap:1','webpage','crawl','primary',%s,"
            "'captured') RETURNING artifact_id",
            (prereqs["rights_id"],),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO evidence_capture(artifact_id,content_digest,"
            "byte_size,media_type,retrieved_at,retrieved_by_run_id,"
            "ocfl_object_id,ocfl_version,capture_method,capture_tool_version,"
            "storage_tier,capture_classification,http_status) "
            "VALUES(%s,'digest-1',2048,'text/csv',now(),%s,'sig:cap:1','v1',"
            "'fetch','v','public','actual',200)",
            (artifact, run),
        )
        conn.execute(
            "INSERT INTO ingest_run_capture"
            " (run_id, target_key, state, capture_digest, source_uri,"
            "  media_type, byte_size, retrieved_at, records)"
            " VALUES (%s,'https://example.org/data.csv','flushed','digest-1',"
            "        'https://example.org/data.csv','text/csv',2048,now(),42)",
            (run,),
        )
        # A mark whose digest resolves to no capture row still emits, with
        # NULL capture fields — honest absence, never a fabricated join.
        conn.execute(
            "INSERT INTO ingest_run_capture"
            " (run_id, target_key, state, capture_digest, source_uri,"
            "  media_type, byte_size, retrieved_at, records)"
            " VALUES (%s,'https://example.org/gone','flushed','digest-none',"
            "        'https://example.org/gone','text/csv',10,now(),0)",
            (run,),
        )
        _insert_report(conn, run, "cap_src")

        rows = conn.execute(
            "SELECT run_id, target_key, state, source_uri, records,"
            "       mark_digest, capture_classification, storage_tier,"
            "       byte_size, http_status, source_id, shared_run"
            "  FROM v_transparency_capture ORDER BY target_key"
        ).fetchall()
        assert len(rows) == 2
        by_target = {r[1]: r for r in rows}
        bound = by_target["https://example.org/data.csv"]
        assert bound[4:] == (42, "digest-1", "actual", "public", 2048, 200, "cap_src", False)
        unbound = by_target["https://example.org/gone"]
        assert unbound[4] == 0 and unbound[5] == "digest-none"
        # No fabricated join: capture-side fields are NULL …
        assert unbound[6] is None and unbound[7] is None and unbound[9] is None
        # … but the sole report still attributes the source (C-13 guard is
        # satisfied: one execution owns the run).
        assert unbound[10] == "cap_src" and unbound[11] is False


def test_capture_view_sealed_tier_passes_to_sig_export(clean_dsn: str) -> None:
    """The view is sig_export-only so the recorded tier shows verbatim; the
    sealed URL's scrub happens at artifact emission (S-6), not in the view."""
    from conftest import seed_claim_prerequisites

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        prereqs = seed_claim_prerequisites(conn)
        run = _insert_run(conn)
        conn.execute(
            "INSERT INTO source_registry(source_id,name,source_kind,"
            "default_reliability,reliability_justification,rights_id,"
            "custody_posture,compact_status,robots_policy) "
            "VALUES('seal_src','Fixture','portal','R2','fixture',%s,"
            "'MIRROR','no_response','obey')",
            (prereqs["rights_id"],),
        )
        artifact = conn.execute(
            "INSERT INTO evidence_artifact(source_id,stable_locator,"
            "artifact_type,acquisition_method,primary_or_secondary,rights_id,"
            "capture_status) "
            "VALUES('seal_src','urn:sig:seal:1','webpage','crawl','primary',%s,"
            "'captured') RETURNING artifact_id",
            (prereqs["rights_id"],),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO evidence_capture(artifact_id,content_digest,"
            "byte_size,media_type,retrieved_at,retrieved_by_run_id,"
            "ocfl_object_id,ocfl_version,capture_method,capture_tool_version,"
            "storage_tier,capture_classification,redaction_applied,"
            "redaction_method,redaction_version) "
            "VALUES(%s,'digest-sealed',99,'text/html',now(),%s,'sig:cap:2',"
            "'v1','fetch','v','sealed','actual',true,'manual_review','v1')",
            (artifact, run),
        )
        conn.execute(
            "INSERT INTO ingest_run_capture"
            " (run_id, target_key, state, capture_digest, source_uri,"
            "  media_type, byte_size, retrieved_at, records)"
            " VALUES (%s,'https://sealed.example.org/x','captured',"
            "        'digest-sealed','https://sealed.example.org/x',"
            "        'text/html',99,now(),NULL)",
            (run,),
        )
        row = conn.execute(
            "SELECT storage_tier, redaction_applied, redacted_derivative,"
            "       bytes_retained, source_id"
            "  FROM v_transparency_capture"
            " WHERE target_key = 'https://sealed.example.org/x'"
        ).fetchone()
        assert row == ("sealed", True, False, False, "seal_src")


# ---------------------------------------------------------------------------
# P35.35 — v_transparency_source + the source_redistribution mirror
# ---------------------------------------------------------------------------


def _seed_source(conn: psycopg.Connection, source_id: str) -> None:
    from conftest import seed_claim_prerequisites

    prereqs = seed_claim_prerequisites(conn)
    conn.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,"
        "default_reliability,reliability_justification,rights_id,"
        "custody_posture,compact_status,robots_policy) "
        "VALUES(%s,'Fixture','portal','R2','fixture',%s,"
        "'MIRROR','no_response','obey')",
        (source_id, prereqs["rights_id"]),
    )


def test_source_view_columns_match_the_allow_list(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        cols = [
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name = 'v_transparency_source'"
                " ORDER BY ordinal_position"
            )
        ]
        assert cols == list(TRANSPARENCY_SOURCE_VIEW_COLUMNS)
        assert not NEVER_EXPORTED_FIELDS.intersection(cols)
        # A P8-1-classified licence string is never a column (Part VIII §0.7).
        for forbidden in (
            "license_terms",
            "licence_verbatim",
            "captured_terms_verbatim",
            "reviewed_by",
            "contact_channel",
            "auth_model",
            "access_method",
        ):
            assert forbidden not in cols


def test_source_view_grant_is_sig_export_only(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        grantees = {
            r[0]
            for r in conn.execute(
                "SELECT grantee FROM information_schema.role_table_grants"
                " WHERE table_name = 'v_transparency_source'"
                "   AND privilege_type = 'SELECT'"
            )
        }
        assert "sig_export" in grantees
        assert "sig_read_public" not in grantees


def test_source_redistribution_mirror_is_append_only_and_current(clean_dsn: str) -> None:
    """Two declarations for one source land as two rows; the current view
    renders the latest recorded version — an UPDATE/DELETE is never a path."""
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _seed_source(conn, "srd_src")
        conn.execute(
            "INSERT INTO source_redistribution(source_id,registry_version,lane,"
            "part_viii_class,evidence,decision_authority) "
            "VALUES('srd_src','v1','derived-only','none-known','first','D-J3-1 [B-19]'),"
            "      ('srd_src','v2','link-only','P8-3','second','D-J3-1 [B-19]')"
        )
        row = conn.execute(
            "SELECT lane, part_viii_class, registry_version"
            "  FROM source_redistribution_current WHERE source_id = 'srd_src'"
        ).fetchone()
        assert row == ("link-only", "P8-3", "v2")

        # The transparency view joins the recorded lane fields end-to-end.
        view_row = conn.execute(
            "SELECT lane, lane_evidence, lane_decision_authority, part_viii_class"
            "  FROM v_transparency_source WHERE source_id = 'srd_src'"
        ).fetchone()
        assert view_row == ("link-only", "second", "D-J3-1 [B-19]", "P8-3")

        # Append-only: UPDATE and DELETE both refuse.
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute(
                "UPDATE source_redistribution SET lane = 'raw-ok' WHERE source_id = 'srd_src'"
            )
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute("DELETE FROM source_redistribution WHERE source_id = 'srd_src'")
        # The closed lane vocabulary holds at the table too.
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO source_redistribution(source_id,registry_version,lane)"
                " VALUES('srd_src','v3','wide-open')"
            )


def test_sink_mirrors_the_recorded_declaration(clean_dsn: str) -> None:
    """PgClaimSink appends the resolver's recorded [redistribution] fields —
    a second write of the same version is +0 (ON CONFLICT DO NOTHING)."""
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _seed_source(conn, "sink_src")
        sink = PgClaimSink(conn, connector_name="sig.test")
        fields = {
            "lane": "raw-ok",
            "part_viii_class": "clear",
            "lane_evidence": "rights/sink_src.md",
            "lane_evidence_uri": "docs/.../redistribution.csv#sink_src",
            "lane_decision_authority": "D-J3-1 [B-19]",
            "lane_review_needed": False,
            "packet_limited": False,
            "sig_labelled_cc0": False,
            "redistribution_version": "sources.toml+aaaabbbb",
        }
        sink._lane_fields_by_source["sink_src"] = fields
        sink._mirror_source_redistribution("sink_src")
        sink._mirror_source_redistribution("sink_src")  # idempotent
        rows = conn.execute(
            "SELECT lane, part_viii_class, evidence, decision_authority,"
            "       review_needed, registry_version"
            "  FROM source_redistribution WHERE source_id = 'sink_src'"
        ).fetchall()
        assert rows == [
            (
                "raw-ok",
                "clear",
                "rights/sink_src.md",
                "D-J3-1 [B-19]",
                False,
                "sources.toml+aaaabbbb",
            )
        ]


def test_sink_without_recorded_lane_mirrors_nothing(clean_dsn: str) -> None:
    """A source whose resolver carries no recorded lane (undeclared block —
    the interim basis stays in charge) writes no mirror row: honest absence,
    never a fabricated verdict."""
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _seed_source(conn, "interim_src")
        sink = PgClaimSink(conn, connector_name="sig.test")
        sink._lane_fields_by_source["interim_src"] = {"custody_posture": "MIRROR"}
        sink._mirror_source_redistribution("interim_src")
        assert (
            conn.execute(
                "SELECT count(*) FROM source_redistribution WHERE source_id = 'interim_src'"
            ).fetchone()[0]
            == 0
        )


def test_recorded_raw_ok_clear_writes_and_serves_public(clean_dsn: str) -> None:
    """D-P35.31-1 closure evidence, end-to-end: a lane-evidenced ``raw-ok``
    + Part VIII-``clear`` source writes ``storage_tier='public'`` on its
    actual capture, the mirror row lands beside it, and the read path
    serves ``tier='public'`` with ``tier_basis='recorded'`` — never a
    default, always the recorded verdict."""
    from datetime import UTC, datetime

    from api.store_pg import PgReadStore
    from db.assertion import CaptureBinding
    from db.claim_sink import PgClaimSink
    from evidence.digest import multihash

    fields = {
        "lane": "raw-ok",
        "part_viii_class": "clear",
        "custody_posture": "MIRROR",
        "lane_evidence": "rights/e2e_src.md",
        "lane_decision_authority": "D-J3-1 [B-19]",
        "lane_review_needed": False,
        "packet_limited": False,
        "sig_labelled_cc0": False,
        "redistribution_version": "sources.toml+e2ee2ee2",
    }
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _seed_source(conn, "e2e_src")
        rights_id = conn.execute(
            "SELECT rights_id FROM source_registry WHERE source_id = 'e2e_src'"
        ).fetchone()[0]
        sink = PgClaimSink(
            conn,
            connector_name="sig.test",
            lane_resolver=lambda _sid: dict(fields),
        )
        capture_id = sink._ensure_actual_capture(
            CaptureBinding(
                digest=multihash(b"p35.35 e2e bytes"),
                source_uri="https://example.test/e2e/page.html",
                media_type="text/html",
                byte_size=17,
                retrieved_at=datetime(2026, 10, 19, tzinfo=UTC),
                ocfl_object_id="sig:capture:e2e",
                ocfl_version="v1",
            ),
            source_id="e2e_src",
            rights_id=str(rights_id),
            genre="connector_run",
        )
        assert capture_id is not None
        artifact_id, tier = conn.execute(
            "SELECT artifact_id, storage_tier FROM evidence_capture WHERE capture_id = %s",
            (capture_id,),
        ).fetchone()
        # The recorded verdict reaches the stored row — `public` is now
        # reachable where lane + Part VIII evidence say so (D-P35.31-1).
        assert tier == "public"
        # The mirror row landed on the same write path.
        assert conn.execute(
            "SELECT lane, part_viii_class FROM source_redistribution WHERE source_id = 'e2e_src'"
        ).fetchone() == ("raw-ok", "clear")

    store = PgReadStore(clean_dsn, pool_min=1, pool_max=2)
    try:
        meta = store.capture(str(artifact_id), capture_id)
    finally:
        store.close()
    assert meta is not None
    assert str(getattr(meta.tier, "value", meta.tier)) == "public"
    assert meta.tier_basis == "recorded"
