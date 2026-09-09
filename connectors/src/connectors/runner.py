# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The connector runner — fixture spine wiring (P19.4) and live/replay/shadow (P21.3).

This drives one registered connector end-to-end through the eight stages
(:func:`connectors.pipeline.run`). Two entry points:

* :func:`run_connector_over_fixture` (P19.4) — a **local fixture file**, no real
  network, a static transport serving the fixture bytes for every URL, asserting
  the run's claims into a selected :class:`~connectors.stages.ClaimSink`. The
  spine-wiring path the composed stack and ``--sink pg`` use.
* :func:`run_source` (P21.3) — the source-driven ``sig-connectors run`` surface
  with an explicit ``mode``: ``live`` **refuses** (raising :class:`LiveGateRefused`,
  CLI exit 3) unless the source's rights-review status is *fully green*
  (SIG-INGEST-028 / P21.1) — so a live fetch is structurally impossible without a
  green review-status (LD-X08 can never recur) — then executes the eight stages
  over the real :class:`~connectors.transports.HttpxTransport` into an
  :class:`~connectors.capture_ocfl.OcflCaptureStore`, writing a **fetch record**
  (:class:`FetchRecord`) that carries no content; ``replay`` / ``shadow`` run over
  a committed fixture under network isolation and never fetch.
"""

from __future__ import annotations

import dataclasses
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from evidence.ingest_run import IngestRun

from .loader import compact_permits_ingestion, custody_permits_fetch
from .net import FetchResult, PoliteFetcher, RobotsResult
from .pipeline import RunReport, run
from .registry import SourceRecord, get
from .replay import ShadowDiff, replay, replay_fingerprint, shadow_replay
from .review import has_review_metadata, has_rights_block
from .sinks import make_claim_sink
from .stages import ClaimSink, Connector, InMemoryCaptureStore, RunContext, registered_connectors

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"

#: The connector each critical-path source runs through, so ``run --source ID``
#: can pick the adapter without ``--connector`` (SIG-INGEST-021). Extend as
#: sources are wired; ``--connector`` overrides.
CONNECTOR_FOR_SOURCE: dict[str, str] = {
    "osm_overpass": "osm",
    "osm_element_history": "osm",
    "eff_atlas_of_surveillance": "atlas",
    "muckrock": "records",
    "usaspending": "procurement",
    "okc_council": "procurement",
    "eff_data_driven": "data_driven",
    "carnegie_ai_gsi": "coarse_international",
    "facial_recognition_world_map": "coarse_international",
    "aspi_mapping_chinas_tech_giants": "coarse_international",
}


class RunMode(StrEnum):
    """The three run modes ``sig-connectors run --mode`` accepts (SIG-INGEST-018/019)."""

    LIVE = "live"
    REPLAY = "replay"
    SHADOW = "shadow"


class LiveGateRefused(Exception):
    """Raised when a ``live`` run is attempted on a source that is not fully green.

    A live fetch is permitted **only** for a source whose rights-review status is
    fully green (flipped by the operator in P21.1 with recorded review metadata).
    Any other source is refused *before any fetch* (SIG-INGEST-014/028) — the
    structural guarantee that a live fetch is impossible without a green
    review-status (LD-X08 can never recur). The CLI maps this to exit code 3.
    """

    def __init__(self, source_id: str, reasons: Sequence[str]) -> None:
        self.source_id = source_id
        self.reasons = list(reasons)
        joined = "; ".join(self.reasons)
        super().__init__(
            f"live fetch refused for source {source_id!r}: {joined} "
            "(SIG-INGEST-028; a live fetch requires a fully-green review-status — P21.1/HG-03)."
        )


def live_gate_reasons(source: SourceRecord | str) -> list[str]:
    """Every reason a ``live`` fetch is refused for ``source`` — empty means green.

    "Fully green" is the P21.1 review-status: ``ingestion_permitted`` true, a
    compact status that permits ingestion, a content-fetching custody posture, a
    resolved (non-``UNDETERMINED``) rights block, and recorded review metadata
    (``rights_reviewed_by`` + ``rights_reviewed_on``). A single missing field
    refuses the fetch (fail-closed, SIG-INGEST-028).
    """
    record = get(source) if isinstance(source, str) else source
    reasons: list[str] = []
    if not record.ingestion_permitted:
        reasons.append("ingestion_permitted=false (not flipped by a reviewer, SIG-INGEST-028)")
    if not compact_permits_ingestion(record.compact_status):
        reasons.append(
            f"compact_status={record.compact_status.value!r} does not permit ingestion (§22.4)"
        )
    if not custody_permits_fetch(record.custody_posture):
        reasons.append(f"custody_posture={record.custody_posture.value!r} is link-only (§8.4)")
    if not has_rights_block(record):
        reasons.append("rights block is UNDETERMINED (SIG-LIC-004)")
    if not has_review_metadata(record):
        reasons.append("no recorded review metadata (rights_reviewed_by/on, SIG-INGEST-038)")
    return reasons


def is_review_status_green(source: SourceRecord | str) -> bool:
    """Whether a ``live`` fetch is permitted (review-status fully green, P21.1)."""
    return not live_gate_reasons(source)


class _StaticFileTransport:
    """Serves one fixture's bytes for any URL — no real network (SIG-INGEST-011)."""

    def __init__(self, body: bytes, media_type: str) -> None:
        self._body = body
        self._media_type = media_type

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self, url: str, *, user_agent: str, headers: Mapping[str, str] | None = None
    ) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type=self._media_type,
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def run_connector_over_fixture(
    connector_name: str,
    source_id: str,
    fixture: Path,
    *,
    media_type: str,
    kind: str,
    sink: ClaimSink | None = None,
    sink_kind: str = "memory",
    dsn: str | None = None,
    code_commit: str = "unknown",
) -> RunReport:
    """Run ``connector_name`` over ``fixture`` and assert claims into the sink.

    Either pass a built ``sink`` or a ``sink_kind`` (+ ``dsn`` for ``pg``); a PG
    sink is stamped with the connector identity so its ``ingest_run`` is coherent.
    """
    registry = registered_connectors()
    if connector_name not in registry:
        raise ValueError(f"unknown connector {connector_name!r}; registered: {sorted(registry)}")
    connector: Connector = registry[connector_name]()
    version = getattr(connector, "version", "1.0.0")

    if sink is None:
        if sink_kind == "pg":
            sink = make_claim_sink(
                "pg",
                dsn=dsn,
                connector_name=connector.name,
                connector_version=version,
                code_commit=code_commit,
            )
        else:
            sink = make_claim_sink(sink_kind)

    # A reviewer flips the seed row to permitted to run (the seed stays
    # ingestion_permitted=false; SIG-INGEST-028), exactly as the tests do.
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    transport = _StaticFileTransport(fixture.read_bytes(), media_type)
    fetcher = PoliteFetcher(
        connector_name=connector.name, connector_version=version, transport=transport
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, version, code_commit, "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=sink,
        parameters={"targets": [{"id": "t1", "url": f"https://{source_id}/x", "kind": kind}]},
    )
    return run(connector, ctx)


# --- the fetch record (P21.3 owns this format; SIG-INGEST-015) ----------------


@dataclass
class FetchRecord:
    """The immutable record one live run writes (``docs/build/live_runs/``).

    It carries **no content** — only what was fetched, from where, when, and the
    crawler-conduct evidence (rate-limit events + robots decisions, RISK-P21-04) a
    reviewer needs to audit the run. The captured bytes live in the OCFL store
    (content-addressed by ``capture_digests``); the record is provenance, not a
    copy (append-only, P1–P3: a re-run writes a new dated record, never edits one).
    """

    source_id: str
    connector: str
    mode: str
    started_at: str
    duration_seconds: float
    urls: list[str] = field(default_factory=list)
    status_codes: list[int] = field(default_factory=list)
    byte_counts: list[int] = field(default_factory=list)
    capture_digests: list[str] = field(default_factory=list)
    claim_count: int = 0
    rate_limit_events: list[Mapping[str, Any]] = field(default_factory=list)
    robots_decisions: list[Mapping[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serialisable dict; content is never included (§3.1, §17)."""
        return {
            "source_id": self.source_id,
            "connector": self.connector,
            "mode": self.mode,
            "started_at": self.started_at,
            "duration_seconds": round(self.duration_seconds, 6),
            "urls": list(self.urls),
            "status_codes": list(self.status_codes),
            "byte_counts": list(self.byte_counts),
            "capture_digests": list(self.capture_digests),
            "claim_count": self.claim_count,
            "rate_limit_events": [dict(e) for e in self.rate_limit_events],
            "robots_decisions": [dict(d) for d in self.robots_decisions],
        }


#: Where dated fetch records land (SIG-INGEST-015; P21.3 owns the format).
LIVE_RUNS_DIR = Path("docs/build/live_runs")


def write_fetch_record(record: FetchRecord, directory: Path | None = None) -> Path:
    """Write ``record`` to ``<directory>/<date>_<source>.json`` (append-only)."""
    directory = directory or LIVE_RUNS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    date = record.started_at[:10]
    path = directory / f"{date}_{record.source_id}.json"
    path.write_text(
        json.dumps(record.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


# --- the source-driven run surface (P21.3) ------------------------------------


@dataclass
class SourceRunReport:
    """The outcome of one ``sig-connectors run --source`` invocation."""

    source_id: str
    connector: str
    mode: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    captures: list[Any] = field(default_factory=list)
    asserted: bool = False
    diff: ShadowDiff | None = None
    replay_reproducible: bool | None = None
    fetch_record: FetchRecord | None = None


def _connector_for(source_id: str, connector_name: str | None) -> Connector:
    name = connector_name or CONNECTOR_FOR_SOURCE.get(source_id)
    if name is None:
        raise ValueError(
            f"no connector known for source {source_id!r}; pass --connector "
            f"(known: {sorted(CONNECTOR_FOR_SOURCE)})"
        )
    registry = registered_connectors()
    if name not in registry:
        raise ValueError(f"unknown connector {name!r}; registered: {sorted(registry)}")
    return registry[name]()


def run_source(
    source_id: str,
    *,
    mode: RunMode | str,
    connector_name: str | None = None,
    fixture: Path | None = None,
    media_type: str = "application/json",
    kind: str = "overpass",
    sink_kind: str = "memory",
    dsn: str | None = None,
    capture_dir: Path | None = None,
    wacz: bool = False,
    code_commit: str = "unknown",
) -> SourceRunReport:
    """Run one source in ``live`` / ``replay`` / ``shadow`` mode (P21.3).

    ``live`` refuses (raising :class:`LiveGateRefused`) unless the source's
    review-status is fully green — so a live fetch is impossible without a green
    review-status (LD-X08). ``replay`` / ``shadow`` run over ``fixture`` under the
    static transport and never touch the network.
    """
    mode = RunMode(mode)
    connector = _connector_for(source_id, connector_name)

    if mode is RunMode.LIVE:
        return _run_live(
            source_id,
            connector,
            sink_kind=sink_kind,
            dsn=dsn,
            capture_dir=capture_dir,
            wacz=wacz,
            code_commit=code_commit,
        )

    if fixture is None:
        raise ValueError(f"--fixture is required for {mode.value!r} mode (no live network)")
    return _run_over_fixture(
        source_id, connector, fixture, media_type=media_type, kind=kind, mode=mode
    )


def _run_live(
    source_id: str,
    connector: Connector,
    *,
    sink_kind: str,
    dsn: str | None,
    capture_dir: Path | None,
    wacz: bool,
    code_commit: str,
) -> SourceRunReport:
    # The gate is checked BEFORE any transport is constructed or any socket is
    # opened (SIG-INGEST-014/028): a non-green source is refused here.
    reasons = live_gate_reasons(source_id)
    if reasons:
        raise LiveGateRefused(source_id, reasons)

    # --- green-source live path (unreachable while no source is flipped) -------
    # Built with the real HTTP transport + OCFL capture store; kept correct so a
    # future green flip runs unchanged. Not exercised this run (HG-03 pending).
    from evidence.ocfl import OcflStore  # local import: heavy evidence deps
    from evidence.storage import LocalFileStore

    from .capture_ocfl import OcflCaptureStore
    from .transports import HttpxTransport

    version = getattr(connector, "version", "1.0.0")
    started = datetime.now(UTC)
    t0 = time.monotonic()
    transport = HttpxTransport()
    fetcher = PoliteFetcher(
        connector_name=connector.name, connector_version=version, transport=transport
    )
    capture_dir = capture_dir or Path(".sig/captures")
    store = OcflStore(LocalFileStore(str(capture_dir)))
    captures = OcflCaptureStore(store, capture_wacz=wacz)
    sink = make_claim_sink(
        sink_kind,
        dsn=dsn,
        connector_name=connector.name,
        connector_version=version,
        code_commit=code_commit,
    )
    source = get(source_id)
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, version, code_commit, "r1", "v1", ()),
        fetcher=fetcher,
        captures=captures,
        claim_sink=sink,
    )
    report = run(connector, ctx)
    fetch_record = FetchRecord(
        source_id=source_id,
        connector=connector.name,
        mode=RunMode.LIVE.value,
        started_at=started.isoformat(),
        duration_seconds=time.monotonic() - t0,
        capture_digests=[c.digest for c in report.captures],
        claim_count=len(report.claims),
        rate_limit_events=list(transport.rate_limit_events),
    )
    write_fetch_record(fetch_record, capture_dir / "live_runs")
    transport.close()
    return SourceRunReport(
        source_id=source_id,
        connector=connector.name,
        mode=RunMode.LIVE.value,
        claims=report.claims,
        captures=report.captures,
        asserted=report.asserted,
        fetch_record=fetch_record,
    )


def _run_over_fixture(
    source_id: str,
    connector: Connector,
    fixture: Path,
    *,
    media_type: str,
    kind: str,
    mode: RunMode,
) -> SourceRunReport:
    version = getattr(connector, "version", "1.0.0")
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    transport = _StaticFileTransport(fixture.read_bytes(), media_type)
    fetcher = PoliteFetcher(
        connector_name=connector.name, connector_version=version, transport=transport
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, version, "unknown", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=make_claim_sink("memory"),
        parameters={"targets": [{"id": "t1", "url": f"https://{source_id}/x", "kind": kind}]},
    )
    # Produce the fixture-encoded ("current") claim set + captures via the driver.
    fixture_report = run(connector, ctx)

    if mode is RunMode.REPLAY:
        replay_a = replay(connector, ctx, fixture_report.captures)
        replay_b = replay(connector, ctx, fixture_report.captures)
        return SourceRunReport(
            source_id=source_id,
            connector=connector.name,
            mode=mode.value,
            claims=replay_a,
            captures=fixture_report.captures,
            replay_reproducible=replay_fingerprint(replay_a) == replay_fingerprint(replay_b),
        )

    # SHADOW: diff a fresh replay against the fixture-encoded claim set. For an
    # unchanged parser over committed fixtures this is byte-identical => 0 diffs
    # (SIG-INGEST-019; the additive/back-compat invariant this ticket must hold).
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    return SourceRunReport(
        source_id=source_id,
        connector=connector.name,
        mode=mode.value,
        claims=fixture_report.claims,
        captures=fixture_report.captures,
        diff=diff,
    )


__all__ = [
    "CONNECTOR_FOR_SOURCE",
    "FetchRecord",
    "LIVE_RUNS_DIR",
    "LiveGateRefused",
    "RunMode",
    "SourceRunReport",
    "is_review_status_green",
    "live_gate_reasons",
    "run_connector_over_fixture",
    "run_source",
    "write_fetch_record",
]
