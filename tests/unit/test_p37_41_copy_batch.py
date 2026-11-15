# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.41 (R11-K13-UX10-4): every agent-drafted public sentence on the
per-source changelog surface is (a) bound to a ``data-copy`` attribute (or
an ``EmptyState`` ``batchIds`` literal) and (b) names a real batch-27 (or
earlier) row — the B-2 verbatim-confirmation contract.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/build/reports/copy-batches/batch-27.md"
PAGES = [
    ROOT / "web/src/pages/sources/[id]/index.astro",
    ROOT / "web/src/pages/sources/[id]/changelog/index.astro",
    ROOT / "web/src/pages/sources/[id]/changelog/page/[n].astro",
]
NEW_IDS = re.compile(r"^(SCL-\d+|PB-09)$")


def _rows() -> dict[str, tuple[str, str, str]]:
    out: dict[str, tuple[str, str, str]] = {}
    for line in BATCH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5 or not NEW_IDS.match(cells[0]):
            continue
        out[cells[0]] = (cells[2], cells[3], cells[4])
    return out


def _bound_ids() -> set[str]:
    ids: set[str] = set()
    for page in PAGES:
        src = page.read_text(encoding="utf-8")
        ids.update(re.findall(r'data-copy="([A-Z]+-\d+)"', src))
        ids.update(re.findall(r'"(SCL-\d+)"', src))  # ternary-bound SCL ids
        for m in re.findall(r"batchIds:\s*\{[^}]*\}", src):
            ids.update(re.findall(r'"([A-Z]+-\d+)"', m))
    return ids


def test_batch_file_exists_and_has_rows() -> None:
    assert BATCH.exists(), "docs/build/reports/copy-batches/batch-27.md is missing"
    assert _rows(), "batch-27.md has no parseable SCL-*/PB-09 rows"


def test_every_row_hash_verifies() -> None:
    for rid, (text, sha, _status) in _rows().items():
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == sha, f"{rid}: sha256 mismatch — the row text drifted"


def test_every_row_is_pending_until_operator_confirmed() -> None:
    for rid, (_text, _sha, status) in _rows().items():
        assert status == "pending", f"{rid} status {status!r} — agent-drafted copy is pending"


def test_every_row_is_bound_on_the_pages() -> None:
    bound = _bound_ids()
    for rid in _rows():
        assert rid in bound, f"{rid} is not data-copy bound on /sources/<id>/**"


def test_pages_bind_no_untracked_new_id() -> None:
    rows = set(_rows())
    prior: set[str] = set()
    for batch in (ROOT / "docs/build/reports/copy-batches").glob("batch-*.md"):
        if batch == BATCH:
            continue
        for line in batch.read_text(encoding="utf-8").splitlines():
            if line.startswith("| "):
                cells = [c.strip() for c in line.split("|")]
                if len(cells) >= 2 and re.fullmatch(r"[A-Z]+-\d+", cells[1] or ""):
                    prior.add(cells[1])
    # Only this ticket's new ids are bound-checked — PB-03…PB-08 predate the
    # batch convention on this page and carry no row (P36.69's set).
    stray = {i for i in _bound_ids() if NEW_IDS.match(i)} - rows - prior
    assert not stray, f"data-copy ids with no copy-batch row: {sorted(stray)}"
