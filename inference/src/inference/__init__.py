# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `inference` package: §32 coverage, completeness, and quality metrics.

The §47 home for L4 derivations and the derived metrics that summarize the claim
spine (§32). This package makes negative space queryable rather than editorial:

* :mod:`inference.coverage` — the `CoverageRecord` and discovery-probe negatives.
* :mod:`inference.denominators` — every published aggregate carries its denominator;
  per-jurisdiction coverage; provenance completeness.
* :mod:`inference.freshness` — freshness relative to predicate volatility.
* :mod:`inference.completeness` — the capture–recapture prohibition and the
  publishable-completeness guardrails.
"""

__version__ = "0.0.0"
