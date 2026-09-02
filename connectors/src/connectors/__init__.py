# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `connectors` package: the seeded source registry and the ingestion gate (§22).

This package owns the seeded source registry (:mod:`connectors.registry`), the
local-group / partner registries (:mod:`connectors.ecosystem`), and the
``ingestion_permitted`` runtime gate every connector passes through
(:mod:`connectors.loader`). Connector fetch logic itself is Phase 4+ (§21.5).
"""

__version__ = "0.0.0"
