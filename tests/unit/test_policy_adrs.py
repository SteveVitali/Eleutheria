# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""ADRs: the §15.5 set + stack ADRs, each naming a revisit trigger (SIG-STORE-007)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from support import REPO_ROOT

ADR_DIR = REPO_ROOT / "docs" / "adr"
ADR_FILES = sorted(ADR_DIR.glob("ADR-*.md"))
# ADR-001..012 (§15.5) plus the eight stack ADRs 013..020.
REQUIRED_NUMBERS = [f"{n:03d}" for n in range(1, 21)]


def test_all_required_adrs_exist() -> None:
    numbers = {re.match(r"ADR-(\d{3})", p.name).group(1) for p in ADR_FILES}  # type: ignore[union-attr]
    missing = [n for n in REQUIRED_NUMBERS if n not in numbers]
    assert not missing, f"missing ADRs: {missing}"


@pytest.mark.parametrize("path", ADR_FILES, ids=lambda p: p.name)
def test_every_adr_names_a_revisit_trigger(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^##\s+Revisit trigger\s*$(.*)", text, re.MULTILINE | re.DOTALL)
    assert match, f"{path.name} has no '## Revisit trigger' section (SIG-STORE-007)"
    assert match.group(1).strip(), f"{path.name} has an empty revisit trigger (SIG-STORE-007)"


def test_there_are_adrs_to_check() -> None:
    assert ADR_FILES
