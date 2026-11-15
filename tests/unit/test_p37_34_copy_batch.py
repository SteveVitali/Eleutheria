# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project.

"""P37.34 — copy batch 23 parses, hashes verify, and every row is bound.

Batch 23 registers the WX-04b watch-feeds copy: the /watch/feeds/
directory's new feed-set sentences (WF-01…04 — the zero-item guarantee,
the "all" scope label, the per-item .ics note and the legacy-feeds
explanation). The test asserts: the file parses and every sha256 verifies;
the rendered `data-copy` ids on the touched page cite real batch rows (this
batch or a prior one — a shared line may re-pin).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/build/reports/copy-batches/batch-23.md"
PAGES = [
    ROOT / "web/src/pages/watch/feeds/index.astro",
]

ROW_RE = re.compile(r"^\| ([A-Z0-9]+-\d+) \| (.+?) \| (.+?) \| ([0-9a-f]{64}) \| (\w+) \|$")


def _rows() -> dict[str, dict[str, str]]:
    assert BATCH.exists(), "docs/build/reports/copy-batches/batch-23.md is missing"
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        rid, page, text, sha, status = m.groups()
        assert rid not in rows, f"duplicate row id {rid}"
        rows[rid] = {"page": page, "text": text, "sha256": sha, "status": status}
    return rows


def test_batch_23_file_exists_and_has_rows() -> None:
    assert _rows(), "batch-23.md has no parseable rows"


def test_every_row_sha_matches_its_sentence() -> None:
    for rid, row in _rows().items():
        actual = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        assert actual == row["sha256"], f"{rid}: sha256 does not match the text"


def test_status_vocabulary() -> None:
    for rid, row in _rows().items():
        assert row["status"] in {"pending", "confirmed"}, f"{rid}: bad status"


def test_every_batch_row_is_bound() -> None:
    """Each WF-* row is bound on the feeds directory via data-copy."""
    src = "\n".join(p.read_text(encoding="utf-8") for p in PAGES)
    bound = set()
    for ids in re.findall(r'data-copy="([A-Z0-9]+-\d+(?:\s+[A-Z0-9]+-\d+)*)"', src):
        bound.update(ids.split())
    for rid in _rows():
        assert rid in bound, f"{rid} is not data-copy bound on /watch/feeds/"


def test_every_binding_cites_a_batch_row() -> None:
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
