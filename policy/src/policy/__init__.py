# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `policy` package (SIG-ENG-014).

The publication rules, sensitivity classification, and licence gates are
**executable logic, not prose in docs/**. Each governing rule that runs in the
pipeline is a pure, versioned function with a test:

* :mod:`policy.crawler` — Crawler Conduct Policy (§26).
* :mod:`policy.rights` / :mod:`policy.licensing` — rights records and the
  N-compartment export licence gates (§42).
* :mod:`policy.sensitivity` — the C1–C5 coordinate matrix and tier transforms
  (§43.3, §19.4).
* :mod:`policy.officer` — the five-prong officer-naming test (§43.4).
* :mod:`policy.publication` — categorical exclusions, de-pseudonymisation, and
  jurisdiction-conditional publication (§43.2/43.8).
* :mod:`policy.threat_model` — the versioned threat-model artifact (§44).

The tables these rules read (licence compartments, the sensitivity matrix, the
threat model, exclusions, crawler rules) are data under ``policy/data/``.
"""

from __future__ import annotations

__version__ = "0.1.0"
