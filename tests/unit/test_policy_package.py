# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-ENG-014 — policy/ is a real, tested Python package (no logic yet)."""

from __future__ import annotations

import importlib

from support import REPO_ROOT


def test_policy_is_a_real_typed_package() -> None:
    policy = importlib.import_module("policy")
    assert policy.__version__
    # Ships type information (py.typed) so downstream packages get checked types.
    assert (REPO_ROOT / "policy" / "src" / "policy" / "py.typed").is_file()


def test_policy_has_a_cli_like_every_stage() -> None:
    cli = importlib.import_module("policy.cli")
    assert cli.main([]) == 0
