# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""ISOLATION re-proof under the composed stack (P19.3; LD-X06, SIG-INGEST-002/018).

P04.1's self-review closed a DNS escape hatch in the network-isolation guard: DNS
resolution is itself network egress, so ``getaddrinfo`` / ``gethostbyname*`` are
guarded alongside ``socket`` / ``create_connection`` (``connectors/isolation.py``).
The composed suite re-proves that guarantee by driving a connector's post-capture
stages — the exact path replay runs under — and asserting a DNS lookup from
**inside a connector run** fails the run rather than silently succeeding.

This does not need Docker (the guard is a pure-Python contract), so it runs
whether or not the composed PG stack is available.
"""

from __future__ import annotations

import json
import socket
import uuid
from collections.abc import Mapping
from typing import Any

import pytest
from connectors.isolation import NetworkEgressBlocked, network_isolated
from connectors.pipeline import run_post_capture
from connectors.registry import get
from connectors.stages import (
    CaptureRef,
    Connector,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

# The DNS entry points the guard must block from inside a connector run (LD-X06).
_DNS_ENTRY_POINTS = ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "getnameinfo")


class _DnsLeakingConnector(Connector):
    """A connector that (wrongly) resolves DNS in parse() — must fail the run."""

    name = "dns-leak-reproof"
    version = "1"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> Any:  # pragma: no cover
        raise AssertionError("fetch is not exercised in the post-capture re-proof")

    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        # A post-capture stage MUST be a pure function of stored artifacts; a DNS
        # lookup here is network egress and must fail the run (SIG-INGEST-002).
        socket.getaddrinfo("example.com", 80)
        return json.loads(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:  # pragma: no cover
        return [{"subject_id": "s", "raw_value": "1"}]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:  # pragma: no cover
        return [dict(c) for c in raw_claims]

    def load(
        self, ctx: RunContext, linked: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:  # pragma: no cover
        return [{**c, "claim_id": str(uuid.uuid4())} for c in linked]


def _context() -> RunContext:
    import dataclasses

    source = dataclasses.replace(get("eyes_on_flock"), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun("dns-leak-reproof", "1", "deadbeef", "r1", "v1", ()),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )


def test_dns_lookup_inside_a_connector_run_is_blocked() -> None:
    # LD-X06: a DNS resolution in a post-capture stage fails the run — the guard
    # closes the DNS-only escape hatch, not just raw socket connects.
    ctx = _context()
    capture = ctx.captures.put(
        json.dumps({"id": "p1", "cameras": 1}).encode("utf-8"),
        media_type="application/json",
        source_uri="https://portal.example/p1",
    )
    with pytest.raises(NetworkEgressBlocked):
        run_post_capture(_DnsLeakingConnector(), ctx, capture)


@pytest.mark.parametrize("entry_point", _DNS_ENTRY_POINTS)
def test_every_dns_entry_point_is_guarded(entry_point: str) -> None:
    # Each DNS resolver on the socket module is replaced inside the isolated
    # context, so no HTTP client can resolve a name and then connect.
    with network_isolated():
        fn = getattr(socket, entry_point)
        with pytest.raises(NetworkEgressBlocked):
            if entry_point == "getnameinfo":
                fn(("127.0.0.1", 80), 0)
            else:
                fn("example.com", 80)


def test_dns_guard_is_restored_after_the_context() -> None:
    # The guard is scoped: after the block the real resolvers are back, so a
    # legitimate FETCH stage outside isolation is unaffected.
    before = {name: getattr(socket, name) for name in _DNS_ENTRY_POINTS}
    with network_isolated():
        pass
    for name, original in before.items():
        assert getattr(socket, name) is original
