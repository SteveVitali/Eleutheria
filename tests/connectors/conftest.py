# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Shared fixtures + a toy connector for the P04.1 connector-framework tests.

The framework writes no source-specific connector (that is P04.2/P04.3), so the
tests exercise it through a deliberately trivial :class:`ToyConnector` and a
:class:`FakeTransport` that never touches a real socket. This is the smallest
adapter that drives all eight stages, so the framework's guarantees can be
asserted end-to-end.
"""

from __future__ import annotations

import dataclasses
import json
import socket
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest
from connectors.net import PoliteFetcher, RobotsResult
from connectors.registry import SourceRecord, get
from connectors.stages import (
    CaptureRef,
    Connector,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


class FakeTransport:
    """A transport that serves canned responses — no real network (SIG-INGEST-011)."""

    def __init__(
        self,
        responses: Mapping[str, FetchResult],
        *,
        robots_text: str | None = _ROBOTS_ALLOW_ALL,
    ) -> None:
        self._responses = dict(responses)
        self._robots_text = robots_text
        self.request_log: list[str] = []
        self.robots_log: list[str] = []
        # Per-request headers seen, keyed nothing — appended in request order so a
        # test can assert an Authorization header rode the shared seam (§23.5).
        self.header_log: list[Mapping[str, str] | None] = []

    def robots(self, robots_url: str) -> RobotsResult:
        self.robots_log.append(robots_url)
        return RobotsResult(text=self._robots_text)

    def request(
        self, url: str, *, user_agent: str, headers: Mapping[str, str] | None = None
    ) -> FetchResult:
        self.request_log.append(url)
        self.header_log.append(dict(headers) if headers is not None else None)
        return self._responses[url]


def json_response_impl(url: str, payload: Mapping[str, Any], *, status: int = 200) -> FetchResult:
    """Build a canned JSON fetch result for the toy connector to parse."""
    return FetchResult(
        url=url,
        status=status,
        body=json.dumps(payload, sort_keys=True).encode("utf-8"),
        media_type="application/json",
        retrieved_at=datetime(2026, 6, 1, tzinfo=UTC),
    )


class ToyConnector(Connector):
    """The smallest connector that exercises all eight stages."""

    name = "toy"
    version = "1"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        return json.loads(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        return [{"portal_id": parsed["id"], "cameras_raw": str(parsed["cameras"])}]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {
                "subject_id": str(r["portal_id"]),
                "predicate_id": "camera_count",
                "raw_value": str(r["cameras_raw"]),
                "value_num": int(r["cameras_raw"]),
            }
            for r in raw_claims
        ]

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # A generated claim_id and transaction time differ every run; the
        # canonical claim tuple drops them (SIG-INGEST-003), so replay is
        # byte-identical modulo exactly these two columns.
        out: list[dict[str, Any]] = []
        for claim in linked:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid.uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        return out


class LeakyParseConnector(ToyConnector):
    """A connector that (wrongly) attempts network egress in parse() — must fail."""

    name = "leaky"

    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        # A stage after capture() must be a pure function of stored artifacts;
        # any egress here must fail the run (SIG-INGEST-002).
        socket.create_connection(("example.com", 80))
        return super().parse(ctx, capture)


@pytest.fixture
def permitted_source() -> SourceRecord:
    """A registry source that clears the full loader gate once permitted.

    eyes_on_flock is MIRROR + public_terms_only; flipping ingestion_permitted is
    the only remaining gate, matching the P00.4 seam.
    """
    return dataclasses.replace(get("eyes_on_flock"), ingestion_permitted=True)


@pytest.fixture
def ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="toy",
        connector_version="1",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


@pytest.fixture
def make_fetcher() -> Any:
    """Factory: build a PoliteFetcher over a FakeTransport."""

    def _make(transport: FakeTransport, **kwargs: Any) -> PoliteFetcher:
        return PoliteFetcher(
            connector_name="toy",
            connector_version="1",
            transport=transport,
            **kwargs,
        )

    return _make


@pytest.fixture
def make_context(permitted_source: SourceRecord, ingest_run: IngestRun) -> Any:
    """Factory: build a RunContext with fresh in-memory stores."""

    def _make(fetcher: Any = None, **kwargs: Any) -> RunContext:
        return RunContext(
            source=permitted_source,
            run=ingest_run,
            fetcher=fetcher,
            captures=InMemoryCaptureStore(),
            claim_sink=InMemoryClaimSink(),
            **kwargs,
        )

    return _make


# Helper classes/functions are exposed as fixtures because the tests/ layout does
# not make tests.connectors an importable package.
@pytest.fixture
def json_response() -> Any:
    return json_response_impl


@pytest.fixture
def transport_factory() -> Any:
    def _make(
        responses: Mapping[str, FetchResult], *, robots_text: str | None = _ROBOTS_ALLOW_ALL
    ) -> FakeTransport:
        return FakeTransport(responses, robots_text=robots_text)

    return _make


@pytest.fixture
def toy_connector() -> ToyConnector:
    return ToyConnector()


@pytest.fixture
def leaky_connector() -> LeakyParseConnector:
    return LeakyParseConnector()
