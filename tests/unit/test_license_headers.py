# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Licence headers — every source file carries an SPDX tag (P00.1 deliverable 6).

The repo-wide placeholder posture was resolved in P00.2: first-party code is
Apache-2.0 (SIG-LIC-005). Data and documentation carry per-artifact licences and
are not code source files, so they are not checked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from support import PY_PACKAGES, REPO_ROOT

SPDX_TAG = "SPDX-License-Identifier: Apache-2.0"


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
