# SPDX-License-Identifier: LicenseRef-SIG-Undetermined
# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final
# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md §42).
"""Licence headers — every source file carries an SPDX tag (P00.1 deliverable 6)."""

from __future__ import annotations

from pathlib import Path

import pytest
from support import PY_PACKAGES, REPO_ROOT

SPDX_TAG = "SPDX-License-Identifier: LicenseRef-SIG-Undetermined"


def _source_files() -> list[Path]:
    files: list[Path] = []
    for pkg in PY_PACKAGES:
        files.extend((REPO_ROOT / pkg / "src").rglob("*.py"))
    files.extend((REPO_ROOT / "tests").rglob("*.py"))
    files.extend((REPO_ROOT / "web" / "src").rglob("*.ts"))
    return files


def test_there_are_source_files_to_check() -> None:
    assert _source_files()


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: str(p))
def test_source_file_has_spdx_header(path: Path) -> None:
    head = path.read_text(encoding="utf-8")[:400]
    assert SPDX_TAG in head, f"{path} is missing the SPDX licence header"
