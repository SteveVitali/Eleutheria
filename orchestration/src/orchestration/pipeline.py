# SPDX-License-Identifier: LicenseRef-SIG-Undetermined
# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final
# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md §42).
"""The orchestration seam (SIG-ENG-013 / SIG-INGEST-021).

`orchestration/` is the ONLY package permitted to import a workflow
orchestrator (e.g. Prefect / Dagster / Airflow / Luigi). Every other package
exposes plain-CLI stages (see each package's `cli.py`); this package is where
those stages are wired into a workflow engine in a later ticket.

The import boundary is enforced mechanically by
`tests/unit/test_import_boundary.py`. No orchestrator has been chosen yet, so
this module holds only the convention and the seam.
"""

from __future__ import annotations

#: Orchestrator modules that may ONLY be imported from within `orchestration/`.
#: Kept here so later tickets extend the list in one place; the boundary test
#: imports it as the single source of truth.
ORCHESTRATOR_MODULES: frozenset[str] = frozenset({"prefect", "dagster", "airflow", "luigi"})
