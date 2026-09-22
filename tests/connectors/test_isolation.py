# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Network isolation for post-capture stages and replay (SIG-INGEST-002/018)."""

from __future__ import annotations

import socket

import pytest
from connectors.isolation import NetworkEgressBlocked, network_isolated


def test_socket_egress_is_blocked_inside_the_context() -> None:
    # SIG-INGEST-002/018: a network call inside the isolated context fails the run.
    with network_isolated():
        with pytest.raises(NetworkEgressBlocked):
            socket.create_connection(("example.com", 80))
        with pytest.raises(NetworkEgressBlocked):
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def test_dns_resolution_is_also_blocked() -> None:
    # DNS resolution is network egress too; the isolation must close that hatch.
    with network_isolated():
        with pytest.raises(NetworkEgressBlocked):
            socket.getaddrinfo("example.com", 80)
        with pytest.raises(NetworkEgressBlocked):
            socket.gethostbyname("example.com")


def test_socket_is_restored_after_the_context() -> None:
    saved = socket.socket
    saved_create = socket.create_connection
    with network_isolated():
        pass
    assert socket.socket is saved
    assert socket.create_connection is saved_create


def test_isolation_is_restored_even_on_exception() -> None:
    saved = socket.socket
    with pytest.raises(ValueError):
        with network_isolated():
            raise ValueError("boom")
    assert socket.socket is saved


def test_httpx_transport_present_cannot_escape_isolation() -> None:
    # LD-X06: with the real HttpxTransport constructed, the isolation still holds —
    # a live transport cannot open a socket or resolve DNS inside the isolated
    # context (which is where the post-capture stages + replay run, SIG-INGEST-002).
    import httpx
    from connectors.transports import HttpxTransport

    # A real client (its own socket-backed transport, not a MockTransport): any
    # request inside isolation must be blocked at the socket layer, below httpx.
    transport = HttpxTransport()
    try:
        with network_isolated():
            with pytest.raises((NetworkEgressBlocked, httpx.HTTPError)):
                transport.request("https://example.com/x", user_agent="SIG/0 (+u)")
            # DNS resolution itself is egress and must be blocked too.
            with pytest.raises(NetworkEgressBlocked):
                socket.getaddrinfo("example.com", 443)
    finally:
        transport.close()


def test_httpx_transport_over_stub_is_allowed_outside_isolation() -> None:
    # Sanity: the same transport works over a local stub when NOT isolated — the
    # guard is the isolation context, not the transport itself.
    import httpx
    from connectors.transports import HttpxTransport

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    transport = HttpxTransport(client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = transport.request("https://x.test/d", user_agent="SIG/0 (+u)")
    assert result.status == 200
