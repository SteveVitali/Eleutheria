# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Concrete :class:`connectors.net.Transport` implementations (P21.3, §21.5).

The framework drives an injected :class:`~connectors.net.Transport` (robots
retrieval plus request execution) so the shared politeness layer
(:class:`~connectors.net.PoliteFetcher`) is testable without real sockets. The
in-memory / static transports live in the tests and the runner; this package
holds the **real network path** — :class:`~connectors.transports.httpx_transport.
HttpxTransport` over ``httpx`` — landed behind the connector-loader gate (P21.3,
LD-F03). It honours crawler conduct (§26): retry-with-backoff on 429/503,
Overpass 429/504 back-off semantics, conditional GET/ETag, and it never follows
an access-control circumvention technique (SIG-INGEST-037).
"""

from __future__ import annotations

from .httpx_transport import HttpxTransport, default_user_agent

__all__ = ["HttpxTransport", "default_user_agent"]
