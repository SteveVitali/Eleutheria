# SPDX-License-Identifier: LicenseRef-SIG-Undetermined
# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final
# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md §42).
"""Shared constants for the SIG skeleton test suite."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# The exact §47 repository layout (docs/2_canonical_design_spec.md §47, SIG-ENG-012).
SIG47_DIRS: tuple[str, ...] = (
    "ontology",
    "db",
    "connectors",
    "parsing",
    "resolution",
    "reconcile",
    "inference",
    "tasks",
    "api",
    "web",
    "exports",
    "orchestration",
    "policy",
    "ops",
    "docs",
    "tests",
)

# The subset of §47 that are Python workspace packages (i.e. not web/ docs/ tests/).
NON_PACKAGE_DIRS: frozenset[str] = frozenset({"web", "docs", "tests"})
PY_PACKAGES: tuple[str, ...] = tuple(d for d in SIG47_DIRS if d not in NON_PACKAGE_DIRS)


def workspace_members() -> list[str]:
    """Read the uv workspace members declared in the root pyproject.toml."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return list(data["tool"]["uv"]["workspace"]["members"])
