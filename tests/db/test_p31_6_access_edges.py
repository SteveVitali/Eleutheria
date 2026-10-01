# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Real-PG proof of P31.6 (ADR-113): access-edge claims + asserting replay.

The P31.6 connectors' post-capture stages run over committed fixtures
(network-isolated :func:`connectors.replay.replay`, same as the fixture suite)
and their records are written by the production-wired ``PgClaimSink``
(``object_resolver = record_object_ref``):

* ``flock_portal`` — ``configured_access_edge`` records now land as
  ``configured_sharing_partner`` claims carrying the partner's portal-slug
  entity-ref (``sig.connector.subject`` → the SAME entity the partner's own
  portal claims key on), so the P28.2 edge materializer writes
  ``configured_access`` ``relationship`` rows, re-run +0.
* ``audit_structural`` — SharedNetworks partners carry ADR-112 organisation
  refs where the name resolves (``sig.org.name``); refused names stay literal
  claims and materialize as ``skipped_unmapped``, never fabricated nodes.
* ``data_driven`` — the release's ``vendor`` constant and the NVLS
  pooled-lookup edge carry organisation twins, so the P28.6 accountability
  materializer writes ``has_vendor`` links anchored on the agency deployment
  subjects, re-run +0.
* ``runner.replay_ingest`` — the named asserting replay (ADR-113): reads only
  ``ingest_run_capture`` marks + the OCFL store, writes a fresh ``is_replay``
  run carrying the original capture lineage, tops up the claims the new code
  adds (the old run asserted none of the edge claims), and re-runs +0.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
import pytest
from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun

FIXTURES = Path(__file__).resolve().parents[1] / "connectors" / "fixtures"
RETRIEVED = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)

_SPINE_TABLES = (
    "inference.derived_fact",
    "relationship",
    "organization",
    "ingest_run_capture",
    "ingest_run_completion",
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


def _count(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...] = ()) -> int:
    row = conn.execute(sql, params).fetchall()
    return int(row[0][0])


def _replay_records(
    connector: Any,
    source_id: str,
    fixture: Path,
    *,
    media_type: str,
    source_uri: str,
    targets: tuple[dict[str, Any], ...] = (),
) -> tuple[list[dict[str, Any]], Any]:
    """Post-capture stages over one committed fixture — the asserting claim set."""
    from connectors.registry import get
    from connectors.replay import replay

    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    captures = InMemoryCaptureStore()
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, "1.0.0", "deadbeef", "r1", "v1", ()),
        captures=captures,
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [dict(t) for t in targets]},
    )
    capture = captures.put(
        fixture.read_bytes(),
        media_type=media_type,
        source_uri=source_uri,
        retrieved_at=RETRIEVED,
    )
    records = [dict(r) for r in replay(connector, ctx, [capture])]
    return records, capture


def _land(
    conn: psycopg.Connection[Any],
    connector_name: str,
    records: list[dict[str, Any]],
    **sink_kwargs: Any,
) -> Any:
    from db.claim_sink import PgClaimSink, record_object_ref

    sink = PgClaimSink(
        conn, connector_name=connector_name, object_resolver=record_object_ref, **sink_kwargs
    )
    sink.assert_claims(records)
    return sink


# --- flock_portal: portal-slug partner refs → configured_access edges ---------


def _flock_records() -> tuple[list[dict[str, Any]], Any]:
    from connectors.flock_portal import FlockPortalConnector

    return _replay_records(
        FlockPortalConnector(),
        "eyes_on_flock",
        FIXTURES / "flock_portal" / "snapshot_2026_08.json",
        media_type="application/json",
        source_uri="https://eyesonflock.com/api/v1/data",
    )


def test_flock_edge_claims_land_as_entity_refs(clean_dsn: str) -> None:
    records, _ = _flock_records()
    edges = [r for r in records if r.get("predicate_id") == "configured_sharing_partner"]
    assert edges
    assert all(r["record_kind"] == "claim" and r.get("object_ref") for r in edges)

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        sink = _land(conn, "flock_portal", records)
        rows = conn.execute(
            "SELECT c.subject_id::text, c.object_entity::text, c.value_text,"
            "       c.object_type, e.entity_type"
            "  FROM claim c JOIN entity e ON e.entity_id = c.object_entity"
            " WHERE c.predicate_id = 'configured_sharing_partner'"
        ).fetchall()
        assert len(rows) == len(edges)
        for _subject_entity, object_entity, value_text, object_type, object_type_e in rows:
            assert object_type == "entity_ref" and object_entity
            assert object_type_e == "deployment"  # the portal-subject placeholder type
            assert value_text  # the partner slug is preserved verbatim (P2)
        # The partner ref keys the SAME entity the partner's own portal subject
        # claims key on: tulsa-pd is itself a subject of this snapshot, so the
        # edge's object_entity IS tulsa-pd's subject entity.
        tulsa = conn.execute(
            "SELECT ei.entity_id::text FROM entity_identifier ei"
            " WHERE ei.scheme = 'sig.connector.subject'"
            "   AND ei.value = 'flock_portal:tulsa-pd'"
        ).fetchall()
        assert len(tulsa) == 1
        edge_to_tulsa = [r for r in rows if r[0] != tulsa[0][0] and r[1] == tulsa[0][0]]
        assert edge_to_tulsa
        # Non-claim records still never reach the spine.
        assert sink.report.inserted == _count(conn, "SELECT count(*) FROM claim")
        assert _count(conn, "SELECT count(*) FROM entity WHERE entity_type = 'person'") == 0


def test_flock_edge_claims_materialize_relationship_rows(clean_dsn: str) -> None:
    from reconcile.materialize import materialize_sharing_edges, read_materialized_edges

    records, _ = _flock_records()
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _land(conn, "flock_portal", records)
        summary = materialize_sharing_edges(conn)
        assert summary.observations > 0
        assert summary.inserted > 0
        assert summary.by_access_kind == {"configured_access": summary.inserted}
        edges = read_materialized_edges(conn)
        assert edges
        claim_ids = {
            str(r[0])
            for r in conn.execute(
                "SELECT claim_id FROM claim WHERE predicate_id = 'configured_sharing_partner'"
            ).fetchall()
        }
        for edge in edges:
            # Every edge is evidenced by spine claims (never unevidenced, §3.1).
            assert edge["evidence_claim"] in claim_ids
            assert edge["access_kind"] == edge["edge_type"] == "configured_access"
            assert edge["valid_from_kind"] == "unknown"  # single snapshot (SIG-RECON-036)
        rerun = materialize_sharing_edges(conn)
        assert (rerun.inserted, rerun.skipped_existing) == (0, summary.inserted)


# --- audit_structural: org-name partner refs → edges + skipped_unmapped -------


def _audit_records() -> tuple[list[dict[str, Any]], Any]:
    from connectors.audit_structural import AuditStructuralConnector

    url = "https://eleutheria.example/records/SharedNetworks.csv"
    return _replay_records(
        AuditStructuralConnector(),
        "agency_audit_export",
        FIXTURES / "audit_structural" / "SharedNetworks.csv",
        media_type="text/csv",
        source_uri=url,
        targets=(
            {
                "id": "SharedNetworks.csv",
                "url": url,
                "file_kind": "shared_networks",
                "observed_at": "2026-08-01",
            },
        ),
    )


def test_audit_edge_claims_materialize_with_org_partners(clean_dsn: str) -> None:
    from reconcile.materialize import materialize_sharing_edges, read_materialized_edges

    records, _ = _audit_records()
    edges = [r for r in records if r.get("predicate_id") == "configured_sharing_partner"]
    assert edges
    resolved = {r["to_org"]: r.get("object_ref") for r in edges}
    assert resolved["Shelby County SO"]["scheme"] == "sig.org.name"
    assert resolved["Metro PD"] is None  # refused names stay literal claims

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _land(conn, "audit_structural", records)
        # Accepted partners mint organization entities; refused partners land as
        # literal claims with no object_entity.
        shelby = conn.execute(
            "SELECT k.entity_id::text FROM entity_identity_key k"
            " WHERE k.scheme = 'sig.org.name' AND k.value = 'shelby county so'"
        ).fetchall()
        assert len(shelby) == 1
        literal = conn.execute(
            "SELECT count(*) FROM claim WHERE predicate_id = 'configured_sharing_partner'"
            " AND object_entity IS NULL AND value_text = 'Metro PD'"
        ).fetchone()[0]
        assert literal == 1

        summary = materialize_sharing_edges(conn)
        assert summary.inserted >= 1
        # The refused partner's literal claim never enters the edge reader
        # (object_entity IS NULL) — the materializer fabricates nothing.
        assert summary.considered_claims < len(edges)
        org_edges = [e for e in read_materialized_edges(conn) if e["to_entity"] == shelby[0][0]]
        assert org_edges
        assert materialize_sharing_edges(conn).inserted == 0
        assert _count(conn, "SELECT count(*) FROM entity WHERE entity_type = 'person'") == 0


# --- data_driven: vendor + NVLS pool twins → has_vendor links -----------------


def _data_driven_records() -> tuple[list[dict[str, Any]], Any]:
    from connectors.data_driven import DataDrivenConnector

    return _replay_records(
        DataDrivenConnector(),
        "eff_data_driven",
        FIXTURES / "data_driven" / "eff_release_2016_2017.zip",
        media_type="application/zip",
        source_uri="https://www.eff.org/files/2020/01/28/alpr_2016-2017_update.zip",
    )


def test_data_driven_vendor_twins_materialize_accountability_links(clean_dsn: str) -> None:
    from inference.accountability import (
        materialize_accountability_links,
        read_materialized_accountability_links,
    )
    from reconcile.materialize import materialize_sharing_edges

    records, _ = _data_driven_records()
    vendors = [r for r in records if r.get("predicate_id") == "vendor" and r.get("object_ref")]
    pools = [
        r
        for r in records
        if r.get("predicate_id") == "configured_sharing_partner" and r.get("object_ref")
    ]
    assert vendors and pools  # the ZIP path stamps the resolvable vendor label

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        _land(conn, "data_driven", records)
        orgs = conn.execute(
            "SELECT entity_id::text, cached_canonical_name FROM organization"
        ).fetchall()
        assert orgs == [(orgs[0][0], "Vigilant Solutions (LEARN)")]

        links = materialize_accountability_links(conn)
        assert links.inserted > 0
        assert links.by_link_type == {"has_vendor": links.inserted}
        vigilant = orgs[0][0]
        for row in read_materialized_accountability_links(conn):
            assert row["object_id"] == vigilant
            assert row["link_type"] == "has_vendor"
        rerun = materialize_accountability_links(conn)
        assert (rerun.inserted, rerun.skipped_existing) == (0, links.inserted)

        edges = materialize_sharing_edges(conn)
        assert edges.inserted > 0
        assert edges.by_access_kind == {"configured_access": edges.inserted}
        assert materialize_sharing_edges(conn).inserted == 0
        assert _count(conn, "SELECT count(*) FROM entity WHERE entity_type = 'person'") == 0


# --- replay_ingest: the asserting replay over persisted captures (ADR-113) ----


def test_replay_ingest_tops_up_new_claims_and_reruns_plus_zero(
    clean_dsn: str, tmp_path: Path
) -> None:
    """The original run asserted the pre-P31.6 claim set (no edge claims — the
    old code dropped them); the replay asserts the NEW claim set off the same
    persisted bytes, under a fresh ``is_replay`` run carrying the original
    capture's lineage. A second replay inserts +0.
    """
    from connectors.capture_ocfl import OcflCaptureStore
    from connectors.runner import replay_ingest
    from db.claim_sink import PgClaimSink, record_object_ref
    from evidence.ocfl import OcflStore
    from evidence.storage import LocalFileStore

    records, _ = _flock_records()
    ocfl_root = tmp_path / "ocfl"
    store = OcflStore(LocalFileStore(str(ocfl_root)))
    store.initialize_root()
    archived = OcflCaptureStore(store)
    capture_ref = archived.put(
        (FIXTURES / "flock_portal" / "snapshot_2026_08.json").read_bytes(),
        media_type="application/json",
        source_uri="https://eyesonflock.com/api/v1/data",
        retrieved_at=RETRIEVED,
    )

    # The ORIGINAL run: the old code's claim set (edge records were dropped as
    # non-claims), with a capture mark carrying the persisted digest.
    old_records = [r for r in records if r.get("predicate_id") != "configured_sharing_partner"]
    dsn = clean_dsn
    with psycopg.connect(dsn, autocommit=True) as conn:
        live = PgClaimSink(
            conn,
            connector_name="flock_portal",
            object_resolver=record_object_ref,
            logical_run="eyes_on_flock@2026-09-20",
        )
        live.assert_claims(old_records)
        live.record_capture(
            "https://eyesonflock.com/api/v1/data",
            state="flushed",
            capture_digest=capture_ref.digest,
            source_uri=capture_ref.source_uri,
            media_type="application/json",
            byte_size=capture_ref.byte_size,
            retrieved_at=RETRIEVED,
            records=len(old_records),
        )
        original_run = live.run_id
        before = _count(conn, "SELECT count(*) FROM claim")

    report = replay_ingest("eyes_on_flock", dsn=dsn, capture_dir=ocfl_root, run_ids=[original_run])
    assert report.status == "ok" and not report.missing_captures
    assert report.run_id and report.run_id != original_run
    assert report.replayed_from_runs == (original_run,)
    assert report.captures_replayed == 1
    expected_new = len(
        [r for r in records if r.get("predicate_id") == "configured_sharing_partner"]
    )
    old_claims = [r for r in old_records if r.get("record_kind", "claim") == "claim"]
    assert report.claims_inserted == expected_new > 0
    # Every previously-asserted claim dedupes; the non-claim records the driver
    # dropped are neither inserted nor duplicated (never claims).
    assert report.claims_duplicate == len(old_claims)

    with psycopg.connect(dsn, autocommit=True) as conn:
        # The replay run is marked is_replay and names the run it replayed.
        run_row = conn.execute(
            "SELECT is_replay, parameters ->> 'logical_run',"
            "       parameters ->> 'replay_of_runs'"
            "  FROM ingest_run WHERE run_id = %s",
            (report.run_id,),
        ).fetchone()
        assert run_row == (True, "eyes_on_flock@replay-p31-6", original_run)
        # Lineage: the replay run's marks carry the ORIGINAL capture digest/URI.
        marks = conn.execute(
            "SELECT target_key, state, capture_digest, source_uri, records"
            "  FROM ingest_run_capture WHERE run_id = %s",
            (report.run_id,),
        ).fetchall()
        assert marks == [
            (
                "replay:https://eyesonflock.com/api/v1/data",
                "flushed",
                capture_ref.digest,
                capture_ref.source_uri,
                len(records),
            )
        ]
        assert _count(conn, "SELECT count(*) FROM claim") == before + expected_new

    # Re-run: every claim dedupes — the +0 proof (ADR-113).
    again = replay_ingest("eyes_on_flock", dsn=dsn, capture_dir=ocfl_root, run_ids=[original_run])
    assert again.claims_inserted == 0
    assert again.claims_duplicate == len(
        [r for r in records if r.get("record_kind", "claim") == "claim"]
    )


def test_replay_ingest_reports_missing_captures_never_fetches(
    clean_dsn: str, tmp_path: Path
) -> None:
    """A mark whose digest the store does not hold is reported missing and
    skipped — the replay never reaches for the network (ADR-113)."""
    from connectors.runner import replay_ingest
    from db.claim_sink import PgClaimSink

    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        live = PgClaimSink(conn, connector_name="flock_portal", logical_run="x@y")
        live.assert_claims(
            [
                {
                    "subject_id": "flock_portal:okc-pd",
                    "predicate_id": "deployment_exists",
                    "value": True,
                    "source_id": "eyes_on_flock",
                }
            ]
        )
        live.record_capture(
            "https://eyesonflock.com/api/v1/data",
            state="flushed",
            capture_digest="sha256:" + "0" * 64,
            source_uri="https://eyesonflock.com/api/v1/data",
            media_type="application/json",
            byte_size=10,
            records=1,
        )
        run_id = live.run_id

    report = replay_ingest(
        "eyes_on_flock", dsn=clean_dsn, capture_dir=tmp_path / "empty_ocfl", run_ids=[run_id]
    )
    assert report.status == "partial"
    assert report.missing_captures == ("sha256:" + "0" * 64,)
    assert report.captures_replayed == 0
    assert report.claims_inserted == 0


def test_replay_ingest_selects_the_sources_non_replay_runs(clean_dsn: str, tmp_path: Path) -> None:
    """Without ``run_ids`` the driver selects every NON-replay run whose
    logical_run carries the source prefix — replay runs are never re-replayed."""
    from connectors.capture_ocfl import OcflCaptureStore
    from connectors.runner import replay_ingest
    from db.claim_sink import PgClaimSink, record_object_ref
    from evidence.ocfl import OcflStore
    from evidence.storage import LocalFileStore

    records, _ = _flock_records()
    ocfl_root = tmp_path / "ocfl"
    store = OcflStore(LocalFileStore(str(ocfl_root)))
    store.initialize_root()
    ref = OcflCaptureStore(store).put(
        (FIXTURES / "flock_portal" / "snapshot_2026_08.json").read_bytes(),
        media_type="application/json",
        source_uri="https://eyesonflock.com/api/v1/data",
        retrieved_at=RETRIEVED,
    )
    with psycopg.connect(clean_dsn, autocommit=True) as conn:
        live = PgClaimSink(
            conn,
            connector_name="flock_portal",
            object_resolver=record_object_ref,
            logical_run="eyes_on_flock@2026-09-20",
        )
        live.assert_claims(
            [r for r in records if r.get("predicate_id") != "configured_sharing_partner"]
        )
        live.record_capture(
            "https://eyesonflock.com/api/v1/data",
            state="flushed",
            capture_digest=ref.digest,
            source_uri=ref.source_uri,
            media_type="application/json",
            byte_size=ref.byte_size,
            retrieved_at=RETRIEVED,
            records=1,
        )
        # A foreign source's run is never selected.
        other = PgClaimSink(conn, connector_name="data_driven", logical_run="eff_data_driven@x")
        other.assert_claims([])
    report = replay_ingest("eyes_on_flock", dsn=clean_dsn, capture_dir=ocfl_root)
    assert report.replayed_from_runs == (live.run_id,)
    assert report.claims_inserted > 0
    # The replay run itself is is_replay — a second source-wide call consumes
    # the same original run, not the replay's marks.
    again = replay_ingest("eyes_on_flock", dsn=clean_dsn, capture_dir=ocfl_root)
    assert again.replayed_from_runs == (live.run_id,)
    assert again.claims_inserted == 0
