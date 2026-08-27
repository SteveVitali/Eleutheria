# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""AC2 — the §47 package layout exists and imports cleanly (SIG-ENG-012)."""

from __future__ import annotations

import importlib

import pytest
from support import PY_PACKAGES, REPO_ROOT, SIG47_DIRS, workspace_members


def test_all_section_47_directories_exist() -> None:
    missing = [d for d in SIG47_DIRS if not (REPO_ROOT / d).is_dir()]
    assert not missing, f"§47 directories missing from the repo: {missing}"


def test_workspace_members_match_section_47_python_packages() -> None:
    # The declared uv workspace members must be exactly the §47 Python packages —
    # no stray package, no renamed one (packages are frozen without an ADR).
    assert sorted(workspace_members()) == sorted(PY_PACKAGES)


@pytest.mark.parametrize("pkg", PY_PACKAGES)
def test_each_python_package_is_real_and_imports_cleanly(pkg: str) -> None:
    pkg_dir = REPO_ROOT / pkg
    assert (pkg_dir / "pyproject.toml").is_file(), f"{pkg} is not a real package"
    assert (pkg_dir / "src" / pkg / "__init__.py").is_file()

    module = importlib.import_module(pkg)
    assert module.__version__, f"{pkg} must expose a __version__"
