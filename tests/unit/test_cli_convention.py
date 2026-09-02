# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-ENG-013 — every stage is invocable as a plain CLI."""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest
from support import PY_PACKAGES


@pytest.mark.parametrize("pkg", PY_PACKAGES)
def test_package_exposes_a_cli_main(pkg: str) -> None:
    cli = importlib.import_module(f"{pkg}.cli")
    assert callable(cli.main)
    assert cli.main([]) == 0  # help path, no domain logic yet


@pytest.mark.parametrize("pkg", PY_PACKAGES)
def test_package_is_runnable_with_dash_m(pkg: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", pkg, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert pkg in result.stdout
