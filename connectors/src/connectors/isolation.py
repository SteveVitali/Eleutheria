# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Network isolation for the post-capture stages and replay (SIG-INGEST-002/018).

Every stage after ``capture()`` MUST be a pure function of stored artifacts, and
replay MUST run against archived snapshots only, in a **network-isolated
context** — the interface makes contacting the source impossible during replay
(SIG-INGEST-018). This module provides that context: inside
:func:`network_isolated` any attempt to open a socket raises
:class:`NetworkEgressBlocked`, so an accidental egress in ``parse()`` or later
**fails the run** rather than silently succeeding (SIG-INGEST-002).

Isolation is deliberately enforced at the socket layer, below any HTTP client, so
it holds no matter what a connector reaches for.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


class NetworkEgressBlocked(RuntimeError):
    """Raised when code under network isolation attempts to open a socket."""


# The socket entry points that could open an outbound connection *or resolve a
# name* — DNS resolution is itself network egress, and HTTP clients call it before
# connecting. Patching the module attributes catches urllib, requests, httpx, and
# raw-socket users alike, and closes the DNS-only escape hatch.
_GUARDED = (
    "socket",
    "create_connection",
    "getaddrinfo",
    "gethostbyname",
    "gethostbyname_ex",
    "getnameinfo",
)


@contextmanager
def network_isolated() -> Iterator[None]:
    """Forbid all network egress for the duration of the block (SIG-INGEST-002).

    Used by the pipeline for the post-capture stages and by the replay harness
    for the whole replay. A blocked egress raises :class:`NetworkEgressBlocked`,
    which propagates and fails the run — the guarantee AC "a network call after
    capture() fails the run" depends on.
    """
    saved: dict[str, Any] = {name: getattr(socket, name) for name in _GUARDED}

    def _blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise NetworkEgressBlocked(
            "network egress is forbidden here: every stage after capture() is a "
            "pure function of stored artifacts, and replay runs network-isolated "
            "(SIG-INGEST-002/018)."
        )

    for name in _GUARDED:
        setattr(socket, name, _blocked)
    try:
        yield
    finally:
        for name, original in saved.items():
            setattr(socket, name, original)


__all__ = ["NetworkEgressBlocked", "network_isolated"]
