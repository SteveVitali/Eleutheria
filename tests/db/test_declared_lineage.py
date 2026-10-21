# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Live-PG contract for declared claim lineage (P35.25 / R11-L3-CP4,
SIG-CONF-014).

A real spine exercises the whole contract:

* the emit path writes one immutable ``claim_lineage`` row per new claim in
  the same transaction — declared values from the ``lineage_resolver``,
  explicit ``undeclared``/``unclassified`` when nothing is declared;
* a claim record declaring an ``id_namespace`` outside the committed
  vocabulary quarantines ``unknown_id_namespace`` — never silently
  namespaced;
* ``derived_from_claim_ids`` persists on the lineage row at emit;
* the rows are immutable (UPDATE/DELETE raise);
* ``db.lineage_rematerialize`` plans without writing, applies append-only
  (declared where the claim's source resolves, explicit ``undeclared``
  where it does not, ancestry back-populated from the claim row), and
  re-runs +0 — claim rows are never UPDATEd.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from conftest import _id_of, insert_claim, seed_claim_prerequisites
from psycopg.rows import dict_row

_T1 = datetime(2026, 8, 1, tzinfo=UTC)

_TABLES = (
    "assertion_quarantine",
    "claim_lineage",
    "source_lineage",
    "claim_evidence",
    "claim",
    "extraction",
    "evidence_capture",
    "evidence_blob",
    "evidence_artifact",
    "source_registry",
    "entity_identifier",
    "entity_identity_key",
    "ingest_run",
    "entity",
    "rights_record",
)


def _dsn(params: dict[str, object]) -> str:
    return (
        f"postgresql://{params['user']}:{params['password']}"
        f"@{params['host']}:{params['port']}/{params['dbname']}"
    )


@pytest.fixture
def dsn(sig_database: dict[str, object]) -> Iterator[str]:
    dsn = _dsn(sig_database)
    truncate = "TRUNCATE " + ", ".join(_TABLES) + " CASCADE"
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(truncate)
    yield dsn
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute(truncate)


def _claim_row(
    subject: str, source_id: str, predicate: str = "camera_latitude", **extra: Any
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "record_kind": "claim",
        "subject_id": subject,
        "predicate_id": predicate,
        "value": "35.46",
        "raw_value": "35.46",
        "source_id": source_id,
        "license": "CC0-1.0",
        "evidence_genre": "camera_registry",
    }
    row.update(extra)
    return row


def _sink(dsn: str, lineage_resolver: Any = None) -> Any:
    from db.claim_sink import PgClaimSink

    return PgClaimSink.from_dsn(
        dsn,
        connector_name="fixture_connector",
        connector_version="1.0.0",
        code_commit="p35.25-test",
        lineage_resolver=lineage_resolver,
    )


def _lineage_rows(dsn: str) -> list[dict[str, Any]]:
    with psycopg.connect(dsn, row_factory=dict_row) as c:
        return c.execute("SELECT * FROM claim_lineage ORDER BY recorded_at, claim_id").fetchall()


def _claim_ids(dsn: str) -> list[str]:
    with psycopg.connect(dsn) as c:
        return [str(r[0]) for r in c.execute("SELECT claim_id FROM claim ORDER BY claim_id")]


# --- emit path -------------------------------------------------------------- #


def test_emit_writes_one_lineage_row_per_claim_with_declared_values(
    dsn: str,
) -> None:
    from db.lineage import ClaimLineage

    sink = _sink(
        dsn,
        lineage_resolver=lambda source_id: ClaimLineage(
            source_id=source_id,
            id_namespace="osm.element",
            lineage_kind="primary",
            independence_class=f"src:{source_id}",
            basis="registry:sources.toml+sig.id-namespaces/1",
        ),
    )
    sink.assert_claims(
        [
            _claim_row("traffic_camera:src_a:t1:cam-1", "src_a"),
            _claim_row("traffic_camera:src_a:t1:cam-2", "src_a"),
        ]
    )
    rows = _lineage_rows(dsn)
    assert len(rows) == 2
    for row in rows:
        assert row["source_id"] == "src_a"
        assert row["id_namespace"] == "osm.element"
        assert row["lineage_kind"] == "primary"
        assert row["independence_class"] == "src:src_a"
        assert row["basis"] == "registry:sources.toml+sig.id-namespaces/1"
        assert row["derived_from_claim_ids"] is None
    # one row per claim — the lineage set and the claim set coincide
    assert {str(r["claim_id"]) for r in rows} == set(_claim_ids(dsn))


def test_emit_without_resolver_records_explicit_undeclared(dsn: str) -> None:
    """No resolver = no registry declaration: the claim's lineage is recorded
    as the honest undeclared state — NULL is never an acceptable lineage."""
    sink = _sink(dsn)
    sink.assert_claims([_claim_row("traffic_camera:src_x:t1:cam-1", "src_x")])
    (row,) = _lineage_rows(dsn)
    assert row["id_namespace"] == "undeclared"
    assert row["lineage_kind"] == "undeclared"
    assert row["independence_class"] == "unclassified"
    assert row["basis"] == "undeclared"


def test_emit_idempotent_rerun_stays_plus_zero(dsn: str) -> None:
    sink = _sink(dsn)
    claims = [_claim_row("traffic_camera:src_a:t1:cam-1", "src_a")]
    sink.assert_claims(claims)
    sink2 = _sink(dsn)
    sink2.assert_claims(claims)
    assert len(_lineage_rows(dsn)) == 1


def test_claim_declared_id_namespace_wins_over_the_source_default(
    dsn: str,
) -> None:
    """A record may carry a narrower per-target namespace than its source's
    declaration — the record's declared (vocabulary-valid) value lands."""
    from db.lineage import ClaimLineage

    sink = _sink(
        dsn,
        lineage_resolver=lambda s: ClaimLineage(
            source_id=s,
            id_namespace="deflock.node",
            lineage_kind="primary",
            independence_class="src:s",
            basis="registry:v",
        ),
    )
    sink.assert_claims(
        [_claim_row("traffic_camera:src_a:t1:cam-1", "src_a", id_namespace="osm.element")]
    )
    (row,) = _lineage_rows(dsn)
    assert row["id_namespace"] == "osm.element"


def test_unknown_id_namespace_quarantines_fail_closed(dsn: str) -> None:
    sink = _sink(dsn)
    sink.assert_claims(
        [_claim_row("traffic_camera:src_a:t1:cam-1", "src_a", id_namespace="bogus.space")]
    )
    assert _claim_ids(dsn) == []
    assert _lineage_rows(dsn) == []
    with psycopg.connect(dsn, row_factory=dict_row) as c:
        rows = c.execute("SELECT reason, subject_ref FROM assertion_quarantine").fetchall()
    assert [r["reason"] for r in rows] == ["unknown_id_namespace"]


def test_derived_from_claim_ids_persist_on_the_lineage_row(dsn: str) -> None:
    """A derived claim's ancestry is persisted at emit (SIG-EPIS-009) — on the
    claim row AND copied onto its lineage row, never recomputed later."""
    sink = _sink(dsn)
    sink.assert_claims([_claim_row("traffic_camera:src_a:t1:cam-1", "src_a")])
    (parent_id,) = _claim_ids(dsn)
    sink.assert_claims(
        [
            _claim_row(
                "traffic_camera:src_a:t1:cam-2",
                "src_a",
                derived_from_claim_ids=[parent_id],
            )
        ]
    )
    rows = _lineage_rows(dsn)
    children = [r for r in rows if r["derived_from_claim_ids"]]
    assert len(children) == 1
    assert [str(u) for u in children[0]["derived_from_claim_ids"]] == [parent_id]
    parent = next(r for r in rows if str(r["claim_id"]) == parent_id)
    assert parent["derived_from_claim_ids"] is None


def test_claim_lineage_rows_are_immutable(dsn: str) -> None:
    sink = _sink(dsn)
    sink.assert_claims([_claim_row("traffic_camera:src_a:t1:cam-1", "src_a")])
    (row,) = _lineage_rows(dsn)
    with psycopg.connect(dsn) as c:
        with pytest.raises(Exception, match="immutable"):
            c.execute(
                "UPDATE claim_lineage SET independence_class = 'src:x' WHERE claim_id = %s",
                (row["claim_id"],),
            )
    with psycopg.connect(dsn) as c:
        with pytest.raises(Exception, match="immutable"):
            c.execute(
                "DELETE FROM claim_lineage WHERE claim_id = %s",
                (row["claim_id"],),
            )


# --- the rematerialize leg -------------------------------------------------- #


def _declarations(tmp_path: Path, sources: list[dict[str, Any]]) -> Path:
    doc = {
        "schema": "sig.source-lineage/1",
        "registry_version": "test-registry-v1",
        "sources": sources,
    }
    path = tmp_path / "declarations.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _declare(
    source_id: str,
    *,
    kind: str = "primary",
    independence_class: str | None = None,
    id_namespace: str = "undeclared",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "kind": kind,
        "independence_class": independence_class or f"src:{source_id}",
        "id_namespace": id_namespace,
        "evidence": "fixture declaration",
        **extra,
    }


def _seed_pending_claim(
    conn: Any,
    *,
    source_id: str | None,
    derived_from: list[str] | None = None,
) -> str:
    """A pre-P35.25-shape claim: a raw claim row (no claim_lineage), plus —
    when ``source_id`` is given — the establishing-evidence chain
    (source_registry → artifact → capture → claim_evidence) the rematerialize
    resolves the claim's source through."""
    prereqs = seed_claim_prerequisites(conn)
    if derived_from:
        # ancestry must land at INSERT — the claim row is append-only even to
        # fixtures (the trigger rejects the UPDATE; that IS the invariant)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
            "value_text,value_num,unit,raw_value,observed_at,source_reliability,"
            "claim_directness,artifact_integrity,asserted_by,assertion_rationale,"
            "ingest_run_id,rights_id,sensitivity_tier,derived_from_claim_ids) "
            "VALUES(%s,%s,'quantity','value','25',25,'cameras','25',"
            "'2026-05-01T00:00:00Z','R1','D1','I1',%s,'fixture',%s,%s,0,%s::uuid[]) "
            "RETURNING claim_id",
            (
                prereqs["subject_id"],
                prereqs["predicate_id"],
                prereqs["author_id"],
                prereqs["run_id"],
                prereqs["rights_id"],
                derived_from,
            ),
        )
        claim_id = str(_id_of(cur.fetchone(), "claim_id"))
    else:
        claim_id = str(insert_claim(conn, prereqs))
    cur = conn.cursor()
    if source_id is not None:
        cur.execute(
            "INSERT INTO rights_record(spdx_expression,redistributable,"
            "derivative_permitted,retrieval_date) "
            "VALUES('Apache-2.0','yes','yes','2026-01-01') RETURNING rights_id"
        )
        rights_id = _id_of(cur.fetchone(), "rights_id")
        cur.execute(
            "INSERT INTO source_registry"
            "(source_id,name,source_kind,default_reliability,"
            " reliability_justification,rights_id,custody_posture,"
            " compact_status,robots_policy) "
            "VALUES(%s,%s,'commercial','R2','fixture',%s,'MIRROR',"
            " 'no_response','honor') ON CONFLICT (source_id) DO NOTHING",
            (source_id, source_id, rights_id),
        )
        cur.execute(
            "INSERT INTO evidence_artifact"
            "(source_id,stable_locator,artifact_type,acquisition_method,"
            " primary_or_secondary,rights_id,capture_status) "
            "VALUES(%s,%s,'camera_registry','connector','primary',%s,'captured') "
            "ON CONFLICT (source_id, stable_locator) DO NOTHING RETURNING artifact_id",
            (source_id, f"sig:fixture:{source_id}", rights_id),
        )
        art = cur.fetchone()
        if art is None:
            art = cur.execute(
                "SELECT artifact_id FROM evidence_artifact WHERE stable_locator = %s",
                (f"sig:fixture:{source_id}",),
            ).fetchone()
        cur.execute(
            "INSERT INTO evidence_capture"
            "(artifact_id,content_digest,byte_size,media_type,retrieved_at,"
            " retrieved_by_run_id,ocfl_object_id,ocfl_version,"
            " capture_method,capture_tool_version) "
            "VALUES(%s,%s,0,'application/octet-stream',%s,%s,%s,'v1',"
            " 'connector','1.0') RETURNING capture_id",
            (
                str(_id_of(art, "artifact_id")),
                f"digest-{source_id}-{claim_id[:8]}",
                _T1,
                prereqs["run_id"],
                f"sig:evidence:{source_id}:{claim_id[:8]}",
            ),
        )
        capture_id = _id_of(cur.fetchone(), "capture_id")
        cur.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) "
            "VALUES(%s,%s,'establishes') ON CONFLICT DO NOTHING",
            (claim_id, str(capture_id)),
        )
    return claim_id


def test_rematerialize_plan_writes_nothing(dsn: str, tmp_path: Path) -> None:
    from db.lineage_rematerialize import run

    decls = _declarations(tmp_path, [])
    with psycopg.connect(dsn) as conn:
        _seed_pending_claim(conn, source_id=None)
        conn.commit()
    report = run(dsn, declarations=decls)
    assert report["mode"] == "plan"
    assert report["totals"]["claims_scanned"] == 1
    assert report["totals"]["lineage_rows_planned"] == 1
    assert report["totals"]["lineage_rows_written"] == 0
    # plan mode touches nothing — no lineage row, no source_lineage mirror
    assert _lineage_rows(dsn) == []
    with psycopg.connect(dsn) as c:
        assert c.execute("SELECT count(*) FROM source_lineage").fetchone()[0] == 0


def test_rematerialize_apply_populates_declared_and_undeclared(dsn: str, tmp_path: Path) -> None:
    from db.lineage_rematerialize import run

    decls = _declarations(tmp_path, [_declare("src_a", id_namespace="osm.element")])
    with psycopg.connect(dsn) as conn:
        declared_claim = _seed_pending_claim(conn, source_id="src_a")
        # a claim with no establishing evidence at all — the honest
        # unresolvable state (its source is never guessed)
        orphans = {_seed_pending_claim(conn, source_id=None)}
        conn.commit()

    report = run(dsn, declarations=decls, apply_mode=True)
    totals = report["totals"]
    assert totals["claims_scanned"] == 2
    assert totals["lineage_rows_written"] == 2
    assert totals["declared"] == 1
    assert totals["unresolvable_source"] == 1
    assert totals["source_lineage_mirrored"] == 1

    rows = {str(r["claim_id"]): r for r in _lineage_rows(dsn)}
    declared = rows[declared_claim]
    assert declared["source_id"] == "src_a"
    assert declared["id_namespace"] == "osm.element"
    assert declared["lineage_kind"] == "primary"
    assert declared["independence_class"] == "src:src_a"
    assert declared["basis"] == "rematerialize:test-registry-v1"
    for orphan in orphans:
        row = rows[orphan]
        assert row["id_namespace"] == "undeclared"
        assert row["lineage_kind"] == "undeclared"
        assert row["independence_class"] == "unclassified"
        assert row["basis"] == "undeclared"

    # the declarations mirror lands versioned; the latest view resolves it
    with psycopg.connect(dsn, row_factory=dict_row) as c:
        mirror = c.execute(
            "SELECT * FROM source_lineage_current WHERE source_id = 'src_a'"
        ).fetchone()
    assert mirror is not None
    assert mirror["registry_version"] == "test-registry-v1"
    assert mirror["independence_class"] == "src:src_a"


def test_rematerialize_back_populates_recoverable_ancestry(dsn: str, tmp_path: Path) -> None:
    """The claim row's own derived_from_claim_ids copies onto the lineage row —
    the claim row is never UPDATEd (append-only, P1–P3)."""
    from db.lineage_rematerialize import run

    parent = "aaaaaaaa-0000-4000-8000-000000000001"
    decls = _declarations(tmp_path, [])
    with psycopg.connect(dsn) as conn:
        claim_id = _seed_pending_claim(conn, source_id=None, derived_from=[parent])
        conn.commit()
    report = run(dsn, declarations=decls, apply_mode=True)
    assert report["totals"]["ancestry_recovered"] == 1
    (row,) = _lineage_rows(dsn)
    assert [str(u) for u in row["derived_from_claim_ids"]] == [parent]
    # ancestry not recoverable → NULL, not a fabricated value
    with psycopg.connect(dsn) as conn:
        _seed_pending_claim(conn, source_id=None)
        conn.commit()
    run(dsn, declarations=decls, apply_mode=True)
    rows = {str(r["claim_id"]): r for r in _lineage_rows(dsn)}
    second = next(r for k, r in rows.items() if k != claim_id)
    assert second["derived_from_claim_ids"] is None


def test_rematerialize_is_bounded_resumable_and_idempotent(dsn: str, tmp_path: Path) -> None:
    """--limit bounds a run; the keyset cursor + ON CONFLICT make a resumed
    run continue where it stopped; a full rerun is +0."""
    from db.lineage_rematerialize import run

    decls = _declarations(tmp_path, [])
    with psycopg.connect(dsn) as conn:
        for _ in range(3):
            _seed_pending_claim(conn, source_id=None)
        conn.commit()

    first = run(dsn, declarations=decls, apply_mode=True, limit=1)
    assert first["totals"]["lineage_rows_written"] == 1
    assert len(_lineage_rows(dsn)) == 1

    rest = run(dsn, declarations=decls, apply_mode=True)
    assert rest["totals"]["lineage_rows_written"] == 2
    assert len(_lineage_rows(dsn)) == 3

    again = run(dsn, declarations=decls, apply_mode=True)
    assert again["totals"]["claims_scanned"] == 0
    assert again["totals"]["lineage_rows_written"] == 0
    assert len(_lineage_rows(dsn)) == 3


def test_rematerialize_declarations_artifact_is_fail_closed(tmp_path: Path) -> None:
    from db.lineage_rematerialize import load_declarations

    with pytest.raises(ValueError, match="not a sig.source-lineage/1"):
        load_declarations(_declarations_raw(tmp_path, {"schema": "wrong"}))
    with pytest.raises(ValueError, match="missing registry_version"):
        load_declarations(_declarations_raw(tmp_path, {"schema": "sig.source-lineage/1"}))
    with pytest.raises(ValueError, match="not in"):
        load_declarations(
            _declarations_raw(
                tmp_path,
                {
                    "schema": "sig.source-lineage/1",
                    "registry_version": "v",
                    "sources": [
                        {
                            "source_id": "s",
                            "kind": "forked",
                            "independence_class": "src:s",
                            "id_namespace": "undeclared",
                        }
                    ],
                },
            )
        )
    with pytest.raises(ValueError, match="not a .*declared namespace"):
        load_declarations(
            _declarations_raw(
                tmp_path,
                {
                    "schema": "sig.source-lineage/1",
                    "registry_version": "v",
                    "sources": [
                        {
                            "source_id": "s",
                            "kind": "primary",
                            "independence_class": "src:s",
                            "id_namespace": "bogus.space",
                        }
                    ],
                },
            )
        )


def _declarations_raw(tmp_path: Path, doc: dict[str, Any]) -> Path:
    path = tmp_path / f"decl-{len(list(tmp_path.iterdir()))}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path
