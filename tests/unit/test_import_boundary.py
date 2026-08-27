# SPDX-License-Identifier: LicenseRef-SIG-Undetermined
# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final
# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md §42).
"""AC3 — only orchestration/ may import the orchestrator (SIG-ENG-013)."""

from __future__ import annotations

import ast

import pytest
from orchestration.pipeline import ORCHESTRATOR_MODULES
from support import PY_PACKAGES, REPO_ROOT

# Forbidden top-level imports outside orchestration/: the workflow orchestrators
# plus the orchestration package itself (nothing else may reach into it).
FORBIDDEN: frozenset[str] = ORCHESTRATOR_MODULES | {"orchestration"}

BOUNDED_PACKAGES = [p for p in PY_PACKAGES if p != "orchestration"]


def _imported_top_level_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("pkg", BOUNDED_PACKAGES)
def test_package_does_not_import_the_orchestrator(pkg: str) -> None:
    for path in (REPO_ROOT / pkg / "src").rglob("*.py"):
        offenders = _imported_top_level_modules(path.read_text(encoding="utf-8")) & FORBIDDEN
        assert not offenders, (
            f"{path.relative_to(REPO_ROOT)} imports {sorted(offenders)}; only "
            f"orchestration/ may import the orchestrator (SIG-ENG-013)."
        )


def test_orchestrator_module_list_is_non_empty() -> None:
    # Guards against the boundary test silently passing because the list emptied.
    assert ORCHESTRATOR_MODULES
