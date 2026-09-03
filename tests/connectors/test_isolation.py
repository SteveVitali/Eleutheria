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
