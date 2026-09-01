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

Source-specific connectors plug into the framework and self-register on import
(SIG-INGEST-021): :mod:`connectors.osm` is the first (P04.2, §23.2),
:mod:`connectors.atlas` the second (P04.3, §23.3), and :mod:`connectors.records`
the third (P07.2, §23.5 — MuckRock/NextRequest/DocumentCloud as targeted-lookup
API clients). Importing the package imports the connectors so they appear in the
registry (``connectors.stages.registered_connectors``) and the CLI.
"""

# Importing the source-specific connectors registers them (SIG-INGEST-021). Kept
# at the bottom so the framework modules above are fully initialised first, and
# imported for the registration side effect only.
from . import atlas as atlas  # noqa: E402,F401
from . import osm as osm  # noqa: E402,F401
from . import records as records  # noqa: E402,F401

__version__ = "0.0.0"
