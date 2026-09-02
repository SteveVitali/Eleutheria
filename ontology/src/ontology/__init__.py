# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `ontology` package — the single ontology source of truth (§47, ADR-007).

The ontology is code before it is data (§51.1). One LinkML source
(``schema/sig.yaml``) plus the versioned vocabulary term lists (``vocab/*.yaml``)
generate every downstream form (§20.1): SQL DDL, JSON Schema, OWL/SHACL, Pydantic,
docs, the SKOS concept schemes (§13), the predicate registry (§13.6), and the
external crosswalks (§20.3). Generation is byte-deterministic so CI can gate
committed artifacts against a fresh generation (SIG-ENG-016). See
:mod:`ontology.generate`.
"""

__version__ = "0.1.0"
