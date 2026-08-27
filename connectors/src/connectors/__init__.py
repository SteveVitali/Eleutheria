# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `connectors` package: the connector framework, source registry, and gate (§21, §22).

This package owns two things. First, the seeded source registry
(:mod:`connectors.registry`), the local-group / partner registries
(:mod:`connectors.ecosystem`), and the connector-loader gate every connector
passes through (:mod:`connectors.loader`). Second — added in P04.1 — the reusable
**connector framework** (§21) every source adapter plugs into:

* :mod:`connectors.stages` — the eight-stage interface
  (``discover→fetch→capture→parse→extract→normalize→link→load``), content-addressed
  and separately retryable (SIG-INGEST-001/003), with ``fetch()`` the only egress
  stage (SIG-INGEST-002).
* :mod:`connectors.net` — the shared rate-limiter + robots layer connectors fetch
  through; connectors hold no HTTP client of their own (SIG-INGEST-011/012/013).
* :mod:`connectors.isolation` — the network-isolated context replay runs in
  (SIG-INGEST-002/018).
* :mod:`connectors.pipeline` — the driver that gates, isolates, and records a run.
* :mod:`connectors.replay` — backfill/replay + shadow-mode diffing
  (SIG-INGEST-017/018/019).
* :mod:`connectors.disappearance` — source disappearance as a first-class event +
  research task (SIG-INGEST-009/010).
* :mod:`connectors.lineage` — per-run lineage mapped to PROV-O (SIG-INGEST-015/016).

This ticket writes **no source-specific connector** — OSM and Atlas are P04.2/P04.3.
"""

__version__ = "0.0.0"
