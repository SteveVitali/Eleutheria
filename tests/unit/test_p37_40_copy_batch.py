# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.40 (R11-K13-CHG-01): every agent-drafted public sentence on the
/changes/ surface is (a) bound to a ``data-copy`` attribute and (b) names a
real batch-26 (or earlier) row — the B-2 verbatim-confirmation contract.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/build/reports/copy-batches/batch-26.md"
PAGES = [
    ROOT / "web/src/pages/changes/index.astro",
    ROOT / "web/src/pages/changes/feeds/index.astro",
]


def _rows() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in BATCH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| CHG-"):
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= 6:
                out[cells[1]] = cells[5]
    return out


def _prior_ids() -> set[str]:
    ids: set[str] = set()
    for batch in (ROOT / "docs/build/reports/copy-batches").glob("batch-*.md"):
        if batch == BATCH:
            continue
        for line in batch.read_text(encoding="utf-8").splitlines():
            if line.startswith("| "):
                cells = [c.strip() for c in line.split("|")]
                if len(cells) >= 2 and re.fullmatch(r"[A-Z]+-\d+", cells[1] or ""):
                    ids.add(cells[1])
    return ids


def _copy_ids() -> set[str]:
    ids: set[str] = set()
    for page in PAGES:
        src = page.read_text(encoding="utf-8")
        for attr in re.findall(r'data-copy="([A-Z0-9]+-\d+)"', src):
            ids.add(attr)
        for attr in re.findall(r"data-copy=\{parts\.batchIds\.(\w+)\}", src):
            ids.add(attr)  # resolved below via batchIds maps
        for m in re.findall(r"batchIds:\s*\{[^}]*\}", src):
            ids.update(re.findall(r'"([A-Z]+-\d+)"', m))
    return ids


def test_batch_file_exists_and_has_rows() -> None:
    assert BATCH.exists(), "docs/build/reports/copy-batches/batch-26.md is missing"
    assert _rows(), "batch-26.md has no parseable CHG-* rows"


def test_every_drafted_id_is_bound_on_the_pages() -> None:
    bound = _copy_ids()
    for rid in _rows():
        assert rid in bound, f"{rid} is not data-copy bound on /changes/**"


def test_every_bound_id_names_a_batch_row() -> None:
    rows = set(_rows()) | _prior_ids()
    for rid in _copy_ids():
        assert rid in rows, f"data-copy cites {rid} — no copy-batch row"


def test_pending_rows_are_marked_pending() -> None:
    for rid, status in _rows().items():
        assert status == "pending", f"{rid} status {status!r} — agent-drafted copy is pending"
