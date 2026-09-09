# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `exports` package: bulk dataset publication (§38) and lineage export (§21.6).

Two things live here: the PROV-O ingest-run lineage export (``provo``/``provo_io``,
SIG-INGEST-016) and the slice dossier renderer (``dossier``); and the P14.2 bulk-export
layer (§38) — ``manifest`` (versioning + checksums), ``compartments`` (the rights-keyed
licence gate), ``formats`` (the seven bulk formats), ``frictionless`` (Data Package +
RO-Crate), ``zenodo`` (the concept/version-DOI deposit), ``distribution`` (egress-friendly
publication), ``downstream`` (the six application classes), and ``bundle`` (the
orchestrator that builds a reproducible, licence-computed release).
"""

__version__ = "0.0.0"
