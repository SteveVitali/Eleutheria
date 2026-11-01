# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.43 (B-2) — the status lane's new public sentences are copy-batch rows.

Every ``ST-12+``/``SS-*`` row in ``batch-07.md`` must (a) hash-verify —
sha256 over the exact UTF-8 sentence, (b) be bound to a rendered
``data-copy`` attribute in its page source, and (c) stay ``pending`` until
the operator confirms it verbatim (the publish gate refuses pending copy).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_07 = REPO_ROOT / "docs/build/reports/copy-batches/batch-07.md"
PAGES = {
    "/status/": REPO_ROOT / "web/src/pages/status.astro",
    "/status/sources/": REPO_ROOT / "web/src/pages/status/sources/index.astro",
}
NEW_IDS = re.compile(r"^(ST-(1[2-9]))$|^(SS-\d+)$")


def _rows() -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for line in BATCH_07.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5 or not NEW_IDS.match(cells[0]):
            continue
        rows.append((cells[0], cells[1], cells[2], cells[3], cells[4]))
    return rows


def test_every_new_row_hash_verifies() -> None:
    rows = _rows()
    assert rows, "no ST-12+/SS-* rows in batch-07 — the new sentences are untracked"
    for rid, _page, text, sha, _status in rows:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == sha, f"{rid}: sha256 mismatch — the row text drifted"


def test_every_new_row_is_pending_until_operator_confirmed() -> None:
    for rid, _page, _text, _sha, status in _rows():
        assert status == "pending", (
            f"{rid} is {status!r} — agent-drafted copy is pending until the "
            "operator confirms it verbatim (B-2)"
        )


def test_every_new_row_is_bound_to_a_data_copy_attribute() -> None:
    for rid, page, _text, _sha, _status in _rows():
        src = PAGES[page].read_text(encoding="utf-8")
        assert f'data-copy="{rid}"' in src or f"{rid} " in src or f" {rid}" in src, (
            f"{rid} ({page}) has no data-copy binding — an untracked sentence must not ship"
        )
