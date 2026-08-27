# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `evidence` package: the write-once OCFL evidence store (§17).

This package owns the evidence-store contract (ADR-006): content addressing as
multihash (:mod:`evidence.digest`), the OCFL 1.1 layout
(:mod:`evidence.ocfl`), the S3/Object-Lock object-store backend
(:mod:`evidence.storage`), the storage-tier and sealed-capture model
(:mod:`evidence.tiers`), the WACZ capture set (:mod:`evidence.capture`),
redaction-as-a-new-capture (:mod:`evidence.redaction`), disappearance / link-rot
handling (:mod:`evidence.disappearance`), and ingest-run reproducibility
(:mod:`evidence.ingest_run`). Every connector writes captures through this store.
"""

__version__ = "0.0.0"
