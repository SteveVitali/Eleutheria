# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""A minimal connector runner over a committed fixture (P19.4 spine wiring).

This drives one registered connector end-to-end through the eight stages
(:func:`connectors.pipeline.run`) over a **local fixture file** — no real network,
a static transport serves the fixture bytes for every URL — and asserts the run's
claims into a selected :class:`~connectors.stages.ClaimSink`. It exists so the
connector output can be persisted to the PostgreSQL claim spine (``--sink pg
--dsn``) from the CLI; the full multi-source ``run`` orchestration CLI (live
transports, registry-driven target discovery) is P21.3's.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from evidence.ingest_run import IngestRun

from .net import FetchResult, PoliteFetcher, RobotsResult
from .pipeline import RunReport, run
from .registry import get
from .sinks import make_claim_sink
from .stages import ClaimSink, Connector, InMemoryCaptureStore, RunContext, registered_connectors

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


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


__all__ = ["run_connector_over_fixture"]
