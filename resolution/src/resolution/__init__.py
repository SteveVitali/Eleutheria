# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `resolution` package: the identity substrate (§11.1-11.3, §14).

This package owns *stable identity before anything is counted* (Phase 3): the
Jurisdiction registry with temporally-versioned geometry (:mod:`resolution.jurisdiction`),
the Organization registry — identifiers-as-sets, the two classification axes, the
surrogate identity basis, and agency-name parsing (:mod:`resolution.identity`),
the reified bitemporal temporal-identity relations and the rule that a rename is
not a succession (:mod:`resolution.temporal_identity`), fixed-width GEOID
validation (:mod:`resolution.geoid`), the agency-centroid geometry guard
(:mod:`resolution.geometry_precision`), and the zero-record ingest guard
(:mod:`resolution.registry_ingest`). The probabilistic cascade, the crosswalk, and
public ``sig:`` identifier minting build on this in P03.2.
"""

__version__ = "0.0.0"
