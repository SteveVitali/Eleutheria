# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project.

"""P37.24 — copy batch 21 parses, hashes verify, and every row is bound.

Batch 21 registers the /graphs/ overview surface's drafted copy (GX-08a):
the hub lede and honest-empty sentences (GO-01…03) and the per-overview
drill-down/empty/label sentences (GO-04…08 — GO-04/08 pin templates with
{place}/{title}/{ovId} placeholders, the batch-01 precedent).

The test asserts: the file parses and every sha256 verifies; every row is
bound somewhere — a `data-copy` attribute in the new pages — and every
`data-copy` id on the new pages cites a real batch row.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/build/reports/copy-batches/batch-21.md"
PAGES = [
    ROOT / "web/src/pages/graphs/index.astro",
    ROOT / "web/src/pages/graphs/[...parts].astro",
]

ROW_RE = re.compile(r"^\| ([A-Z0-9]+-\d+) \| (.+?) \| (.+?) \| ([0-9a-f]{64}) \| (\w+) \|$")


def _rows() -> dict[str, dict[str, str]]:
    assert BATCH.exists(), "docs/build/reports/copy-batches/batch-21.md is missing"
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        rid, page, text, sha, status = m.groups()
        assert rid not in rows, f"duplicate row id {rid}"
        rows[rid] = {"page": page, "text": text, "sha256": sha, "status": status}
    return rows


def test_batch_21_file_exists_and_has_rows() -> None:
    assert _rows(), "batch-21.md has no parseable rows"


def test_every_row_sha_matches_its_sentence() -> None:
    for rid, row in _rows().items():
        actual = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        assert actual == row["sha256"], f"{rid}: sha256 does not match the text"


def test_status_vocabulary() -> None:
    for rid, row in _rows().items():
        assert row["status"] in {"pending", "confirmed"}, f"{rid}: bad status"


def test_every_binding_cites_a_batch_row() -> None:
    """Every data-copy id on the new pages resolves to a batch-21 row (or a
    prior batch's row — a shared line may re-pin across batches)."""
    prior: set[str] = set()
    for other in (ROOT / "docs/build/reports/copy-batches").glob("batch-*.md"):
        if other == BATCH:
            continue
        for line in other.read_text(encoding="utf-8").splitlines():
            m = ROW_RE.match(line)
            if m:
                prior.add(m.group(1))
    rows = _rows()
    src = "\n".join(p.read_text(encoding="utf-8") for p in PAGES)
    for rid in re.findall(r'data-copy="([A-Z0-9]+-\d+(?:\s+[A-Z0-9]+-\d+)*)"', src):
        for token in rid.split():
            assert token in rows or token in prior, f"data-copy cites {token} — no copy-batch row"


def test_every_row_is_bound() -> None:
    """A registered sentence that binds nothing is dead copy — every
    batch-21 row appears as a `data-copy` attribute on the new pages."""
    rows = _rows()
    page_src = "\n".join(p.read_text(encoding="utf-8") for p in PAGES)
    for rid in rows:
        assert rid in page_src, f"batch-21 row {rid} is bound to no rendered element"


def test_binding_sources_exist() -> None:
    for p in PAGES:
        assert p.exists(), p
