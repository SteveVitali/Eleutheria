# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.48 (B-2) — the sources table's new public sentences are copy-batch rows.

Every ``ST-*`` row in ``batch-09.md`` must (a) hash-verify — sha256 over the
exact UTF-8 sentence, (b) be bound to a rendered ``data-copy`` attribute (or
a title-binding comment) in the page family source, and (c) stay ``pending``
until the operator confirms it verbatim (the publish gate refuses pending
copy).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_09 = REPO_ROOT / "docs/build/reports/copy-batches/batch-09.md"
SOURCES = [
    REPO_ROOT / "web/src/pages/sources.astro",
    REPO_ROOT / "web/src/components/SourcesTablePage.astro",
    REPO_ROOT / "web/src/components/SourcesTable.astro",
    REPO_ROOT / "web/src/pages/sources/runs/index.astro",
    REPO_ROOT / "web/src/pages/sources/rights/index.astro",
    REPO_ROOT / "web/src/pages/status/sources/index.astro",
]
NEW_IDS = re.compile(r"^ST-\d+$")


def _rows() -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for line in BATCH_09.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5 or not NEW_IDS.match(cells[0]):
            continue
        rows.append((cells[0], cells[1], cells[2], cells[3], cells[4]))
    return rows


def _src() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in SOURCES)


def test_every_new_row_hash_verifies() -> None:
    rows = _rows()
    assert rows, "no ST-* rows in batch-09 — the new sentences are untracked"
    for rid, _page, text, sha, _status in rows:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == sha, f"{rid}: sha256 mismatch — the row text drifted"


def test_every_new_row_is_pending_until_operator_confirmed() -> None:
    for rid, _page, _text, _sha, status in _rows():
        assert status == "pending", (
            f"{rid} is {status!r} — agent-drafted copy is pending until the "
            "operator confirms it verbatim (B-2)"
        )


def test_every_new_row_is_bound_in_the_page_family() -> None:
    src = _src()
    for rid, _page, _text, _sha, _status in _rows():
        assert f'"{rid}"' in src, (
            f"{rid} (/sources/ table family) has no data-copy/title binding — "
            "an untracked sentence must not ship"
        )


def test_page_family_binds_no_untracked_st_id() -> None:
    src = _src()
    batch_ids = {r[0] for r in _rows()}
    rendered = set(re.findall(r'"(ST-\d+)"', src))
    stray = rendered - batch_ids
    assert not stray, f"data-copy ids with no batch-09 row: {sorted(stray)}"
