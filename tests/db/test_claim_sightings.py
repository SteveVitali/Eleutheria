# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.44 (T12/T13, DSRC-01) — ``v_claim_sightings`` on real PG.

* T12: the view exists with exactly ``CLAIM_SIGHTING_VIEW_COLUMNS``;
  ``sig_export`` selects, ``sig_read_public`` is denied, and nothing else is
  granted.
* T13: seeded claims produce the grouped sighting rows the export's
  ``EXPORT_QUERIES["claim_sightings"]`` aggregate returns — first/last
  retrieval, first/last run, sighting-run + link counts — executed through
  the same gate-substitution the export applies.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import psycopg
import pytest
from policy.transparency import CLAIM_SIGHTING_VIEW_COLUMNS, NEVER_EXPORTED_FIELDS

_SPINE_TABLES = (
    "claim_qualifier",
    "claim_evidence",
    "claim",
    "assertion_quarantine",
    "extraction",
    "ingest_run_capture",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
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
    from conftest import register_vocab_predicate

    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_SPINE_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)
        register_vocab_predicate(conn, "sig.p35_44.sight")
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(truncate)


def _claim(subject: str, value: Any = "present") -> dict[str, Any]:
    return {
        "subject_id": subject,
        "predicate_id": "sig.p35_44.sight",
        "value": value,
        "source_id": "p35_44_src",
        "license": "CC0-1.0",
        "evidence_genre": "camera_registry",
    }


def _capture(body: bytes, uri: str, when: datetime):
    """A CaptureRef shaped like the one OcflCaptureStore.put returns — passing
    it to ``assert_claims`` gives the binding its ``actual_capture`` status
    (the typed P32.2 path, never ``legacy_synthetic``)."""
    from connectors.stages import CaptureRef
    from evidence.digest import multihash

    d = multihash(body)
    return CaptureRef(
        digest=d,
        media_type="text/csv",
        source_uri=uri,
        byte_size=len(body),
        retrieved_at=when,
        ocfl_object_id=f"sig:capture:{d}",
        ocfl_version="v1",
    )


def _sink(dsn: str, **kw: Any):
    from db.claim_sink import PgClaimSink

    return PgClaimSink.from_dsn(
        dsn, connector_name="p35_44", connector_version="1.0.0", code_commit="p35.44-test", **kw
    )


def test_t12_view_columns_and_grant_boundary(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        cols = [
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name = 'v_claim_sightings' ORDER BY ordinal_position"
            )
        ]
        assert cols == list(CLAIM_SIGHTING_VIEW_COLUMNS)
        assert not NEVER_EXPORTED_FIELDS.intersection(cols)

        grantees = {
            r[0]
            for r in conn.execute(
                "SELECT grantee FROM information_schema.role_table_grants"
                " WHERE table_name = 'v_claim_sightings' AND privilege_type = 'SELECT'"
            )
        }
        assert "sig_export" in grantees
        assert "sig_read_public" not in grantees


def test_t12_sig_export_selects_sig_read_public_denied(clean_dsn: str) -> None:
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        conn.execute("SET ROLE sig_export")
        try:
            conn.execute("SELECT count(*) FROM v_claim_sightings").fetchone()
        finally:
            conn.execute("RESET ROLE")
        conn.execute("SET ROLE sig_read_public")
        try:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT count(*) FROM v_claim_sightings").fetchone()
        finally:
            conn.execute("RESET ROLE")


def test_t13_seeded_sightings_group(clean_dsn: str) -> None:
    """Two runs sighting one claim → one aggregate row with both runs, both
    links, the first/last instants, and has_actual_capture true."""
    from db.claim_sink import record_resightings

    cap1 = _capture(b"a1", "https://example.test/p35_44/a", datetime(2026, 5, 1, tzinfo=UTC))
    cap2 = _capture(b"a2", "https://example.test/p35_44/a", datetime(2026, 6, 1, tzinfo=UTC))
    first = _sink(clean_dsn)
    first.assert_claims([_claim("cam:d1")], capture=cap1)
    assert first.report.inserted == 1
    second = _sink(clean_dsn, on_duplicates=record_resightings)
    second.assert_claims([_claim("cam:d1")], capture=cap2)
    assert second.report.duplicates == 1  # the re-sighting linked, no new claim

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        # A third establishing binding carrying an actual_capture status — the
        # sink's document-asserted claims bind ``document_only``; the
        # has_actual_capture aggregate needs the real thing present.
        claim_row = conn.execute("SELECT claim_id FROM claim").fetchone()
        claim_id = claim_row[0]
        art = conn.execute("SELECT artifact_id FROM evidence_artifact LIMIT 1").fetchone()
        run_b = conn.execute(
            "SELECT run_id FROM ingest_run ORDER BY run_id DESC LIMIT 1"
        ).fetchone()
        cap3 = conn.execute(
            "INSERT INTO evidence_capture"
            " (artifact_id, content_digest, byte_size, media_type, retrieved_at,"
            "  retrieved_by_run_id, ocfl_object_id, ocfl_version, capture_method,"
            "  capture_tool_version)"
            " VALUES (%s,'sha256:p35_44_c3',10,'application/json',"
            "         '2026-07-01T00:00:00Z', %s,'p35_44:obj3','v1','fixture','0')"
            " RETURNING capture_id",
            (art[0], run_b[0]),
        ).fetchone()
        conn.execute(
            "INSERT INTO claim_evidence (claim_id, capture_id, role, binding_status)"
            " VALUES (%s, %s, 'establishes', 'actual_capture')",
            (claim_id, cap3[0]),
        )

        rows = conn.execute(
            "SELECT claim_id, subject_id, predicate_id, source_id, role,"
            "       binding_status, run_id, retrieved_at"
            "  FROM v_claim_sightings ORDER BY retrieved_at"
        ).fetchall()
        assert len(rows) == 3
        assert {r[4] for r in rows} == {"establishes"}
        assert rows[0][6] != rows[1][6]  # two different runs sighted it
        assert "actual_capture" in {r[5] for r in rows}

        # A 'contradicts' binding is evidence AGAINST — never a sighting.
        cap2 = conn.execute(
            "SELECT capture_id FROM claim_evidence WHERE claim_id = %s LIMIT 1",
            (rows[1][0],),
        ).fetchone()
        conn.execute(
            "INSERT INTO claim_evidence (claim_id, capture_id, role)"
            " VALUES (%s, %s, 'contradicts')",
            (claim_id, cap2[0]),
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM v_claim_sightings WHERE role = 'contradicts'"
            ).fetchone()[0]
            == 0
        )

        # The export's own aggregate, through the same substitution path
        # ``fetch_export_raw`` applies — fixture data clears every gate.
        from db.dispositions import artifact_eligible_sql, claim_eligible_sql
        from db.occurrences import BELIEF_NOW, claim_source_cte
        from exports.audit import _LATEST_DECISION_CTE
        from exports.dossier_sources import CLAIM_SIGHTINGS_COLUMNS
        from exports.spine_export import EXPORT_QUERIES

        _, sql = EXPORT_QUERIES["claim_sightings"]
        final = (
            sql.replace("{EFFECTIVE}", _LATEST_DECISION_CTE + claim_source_cte(BELIEF_NOW))
            .replace("{PUB_CLAIM_GATE}", claim_eligible_sql("c"))
            .replace("{PUB_ARTIFACT_GATE}", artifact_eligible_sql("ea.artifact_id"))
            .replace("{CAPTURE_SEAL_GATE}", "NOT capture_currently_sealed(ce.capture_id)")
            .replace("{SIGHTING_BOUND}", BELIEF_NOW)
        )
        agg = conn.execute(final).fetchall()
        assert len(agg) == 1
        named = dict(zip(CLAIM_SIGHTINGS_COLUMNS, agg[0], strict=True))
        assert named["claim_id"] == str(claim_id)
        assert named["source_id"] == "p35_44_src"
        assert named["sighting_runs"] == 2
        assert named["sighting_links"] == 3
        assert named["has_actual_capture"] is True
        assert named["first_seen_at"] < named["last_seen_at"]
        assert len(set(named["sighting_run_ids"])) == 2
        assert named["first_run_id"] != named["last_run_id"]
