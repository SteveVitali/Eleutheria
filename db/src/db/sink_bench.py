# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Claim-sink throughput benchmark (P31.3 / ADR-110; closes the D-P30.1-1 measurement).

Measures what one :class:`db.claim_sink.PgClaimSink` pass costs: claims per minute
and **round trips per claim** (every ``execute`` the sink issues, plus the
``BEGIN``/``COMMIT`` of each chunk transaction). It depends only on the sink's
public surface (constructor, ``assert_claims``, ``record_completion``, ``report``),
so the same file measures the pre-P31.3 row-at-a-time sink and the batched one:
put the older tree's ``db/src`` first on ``PYTHONPATH`` to measure the baseline.

Two ways to drive it:

* ``sig-db sink-bench --dsn … --subjects N --scratch-db`` lands ``N`` synthetic
  subjects shaped like the OSM camera mirror (one non-claim ``traffic_camera``
  record and eight claims per subject: two float coordinates and six strings, a
  nested evidence dict, an ODbL licence). The first pass inserts everything; later
  passes replay the same records (+0, all duplicates), which is the shape of the
  monthly OSM re-ingest. ``--scratch-db`` is required because these claims are
  synthetic: never point this mode at the canonical spine.
* ``sig-ops sink-bench --source …`` fetches a real, green source once through the
  gated live connector and times the PG passes over those real records (see
  ``ops.cli``). That is the hosted bounded-replay measurement.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

import psycopg

#: The synthetic source id. It never collides with a registered source.
BENCH_SOURCE_ID = "sig_bench_osm_like"


def synthetic_osm_records(subjects: int, *, tag: str = "bench") -> list[dict[str, Any]]:
    """``subjects`` OSM-mirror-shaped subjects: 1 non-claim record + 8 claims each.

    The shape follows ``connectors.dot_511`` (the camera-registry connector the
    OSM mirror runs through): a ``traffic_camera`` entity record the sink skips,
    then ``camera_external_ref``, ``external_id``, ``camera_jurisdiction``,
    ``camera_operator``, the two float coordinates, ``camera_coordinate_source``
    and ``camera_direction``, each stamped with source, licence and vocab version
    and carrying the per-row evidence dict. Deterministic, so a second call
    returns byte-identical records (the +0 replay).
    """
    out: list[dict[str, Any]] = []
    for i in range(subjects):
        subject = f"traffic_camera:{BENCH_SOURCE_ID}:{tag}:{i}"
        ref = str(100000 + i)
        lat = round(-40.0 + (i * 0.000731) % 80.0, 7)
        lon = round(-170.0 + (i * 0.001337) % 340.0, 7)
        evidence = {
            "source_url": f"https://example.invalid/osm/FeatureServer/0/query?page={i // 2000}",
            "extraction_method": "arcgis_feature_attributes",
            "locator": {"kind": "row", "row": i % 2000},
        }
        stamp = {"source_id": BENCH_SOURCE_ID, "vocab_version": "1.0.0", "license": "ODbL-1.0"}
        out.append(
            {
                "record_kind": "traffic_camera",
                "subject_id": subject,
                "predicate_id": "traffic_camera",
                "external_id": ref,
                "raw_value": ref,
                "latitude": lat,
                "longitude": lon,
                "evidence_genre": "camera_registry",
                "evidence": evidence,
                **stamp,
            }
        )
        values: list[tuple[str, Any, str]] = [
            ("camera_external_ref", ref, ref),
            ("external_id", ref, ref),
            ("camera_jurisdiction", "unresolved", "unresolved"),
            ("camera_operator", "OpenStreetMap contributors", "OpenStreetMap contributors"),
            ("camera_latitude", lat, str(lat)),
            ("camera_longitude", lon, str(lon)),
            ("camera_coordinate_source", "osm_node", "osm_node"),
            ("camera_direction", ("N", "E", "S", "W")[i % 4], ("N", "E", "S", "W")[i % 4]),
        ]
        for predicate, value, raw in values:
            out.append(
                {
                    "record_kind": "claim",
                    "subject_id": subject,
                    "predicate_id": predicate,
                    "raw_value": raw,
                    "value": value,
                    "evidence_genre": "camera_registry",
                    "evidence": dict(evidence),
                    **stamp,
                }
            )
    return out


class CountingConnection:
    """Delegates to a real psycopg connection and counts the round trips the sink makes.

    A statement is one round trip. A chunk transaction adds two (``BEGIN`` and
    ``COMMIT``). Only ``execute`` and ``transaction`` are exposed: they are the whole
    surface the sink uses (``tests/db/test_claim_sink.py`` pins the same surface).
    """

    def __init__(self, real: psycopg.Connection[Any]) -> None:
        self._real = real
        self.statements = 0
        self.transactions = 0

    def execute(self, sql: Any, params: Any = None) -> Any:
        self.statements += 1
        return self._real.execute(sql) if params is None else self._real.execute(sql, params)

    def transaction(self) -> Any:
        self.transactions += 1
        return self._real.transaction()

    @property
    def round_trips(self) -> int:
        return self.statements + 2 * self.transactions


@dataclass
class PassResult:
    """One timed sink pass."""

    label: str
    records: int
    claims: int
    inserted: int
    duplicates: int
    entities: int
    seconds: float
    claims_per_min: float
    statements: int
    transactions: int
    round_trips: int
    round_trips_per_claim: float
    commit_chunk_size: int

    def as_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def run_pass(
    conn: psycopg.Connection[Any],
    records: Sequence[Mapping[str, Any]],
    *,
    label: str,
    connector_name: str,
    connector_version: str = "1.0.0",
    code_commit: str = "sink-bench",
    commit_chunk_size: int = 10_000,
    source_id: str | None = None,
    sink_kwargs: Mapping[str, Any] | None = None,
) -> PassResult:
    """Time one :class:`PgClaimSink` pass over ``records`` and count its round trips.

    The pass is a real execution: it lands claims append-only and records the
    execution's ``ok`` completion (outside the timed window), exactly as an ingest
    run would.
    """
    from .claim_sink import PgClaimSink

    counting = CountingConnection(conn)
    sink = PgClaimSink(
        counting,  # type: ignore[arg-type]
        connector_name=connector_name,
        connector_version=connector_version,
        code_commit=code_commit,
        commit_chunk_size=commit_chunk_size,
        **dict(sink_kwargs or {}),
    )
    started = time.perf_counter()
    sink.assert_claims(records)
    seconds = time.perf_counter() - started
    trips = counting.round_trips
    trans = counting.transactions
    stmts = counting.statements
    sink.record_completion("ok", source_id=source_id)
    report = sink.report
    claims = report.inserted + report.duplicates
    return PassResult(
        label=label,
        records=len(records),
        claims=claims,
        inserted=report.inserted,
        duplicates=report.duplicates,
        entities=report.entities,
        seconds=round(seconds, 3),
        claims_per_min=round(claims / seconds * 60.0, 1) if seconds > 0 else 0.0,
        statements=stmts,
        transactions=trans,
        round_trips=trips,
        round_trips_per_claim=round(trips / claims, 4) if claims else 0.0,
        commit_chunk_size=commit_chunk_size,
    )


def run_synthetic(
    dsn: str,
    *,
    subjects: int,
    passes: int,
    commit_chunk_size: int,
    tag: str,
    sink_kwargs: Mapping[str, Any] | None = None,
) -> list[PassResult]:
    """Land ``subjects`` synthetic subjects, then replay them ``passes - 1`` times."""
    records = synthetic_osm_records(subjects, tag=tag)
    results: list[PassResult] = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        for n in range(passes):
            results.append(
                run_pass(
                    conn,
                    records,
                    label="land" if n == 0 else f"replay-{n}",
                    connector_name="sink_bench",
                    commit_chunk_size=commit_chunk_size,
                    source_id=BENCH_SOURCE_ID,
                    sink_kwargs=sink_kwargs,
                )
            )
            print(results[-1].as_json(), flush=True)
    return results


__all__ = [
    "BENCH_SOURCE_ID",
    "CountingConnection",
    "PassResult",
    "run_pass",
    "run_synthetic",
    "synthetic_osm_records",
]
