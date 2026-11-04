# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project.

"""P36.65 — copy batch 17 parses, hashes verify, and every row is bound.

Batch 17 registers the UXK14-11 copy: the ReadingKey chrome rows (KY-01/02
plus the KY-03 withheld line in lib/reading-key.ts), the fifteen EK-* rows
backing lib/empty.ts EMPTY_KIND_PARTS (the three non-absence cause classes),
and the HD-* rows for /about/how-to-read-a-dossier/ (the annotated walk's
drafted sentences; HD-02/07 pin sentence shapes with {name}/{section-bodies}
placeholders — the {reviewStatus} precedent).

The test asserts: the file parses and every sha256 verifies; every non-held
row is bound somewhere — a `data-copy` attribute in the rendered sources or
a `copy: <id>` comment in the lib (the onboarding.ts precedent); and the
rendered `data-copy` ids on the new page cite real batch rows.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/build/reports/copy-batches/batch-17.md"
PAGES = [
    ROOT / "web/src/pages/about/how-to-read-a-dossier.astro",
    ROOT / "web/src/components/ReadingKey.astro",
]
LIBS = [ROOT / "web/src/lib/empty.ts", ROOT / "web/src/lib/reading-key.ts"]

ROW_RE = re.compile(r"^\| ([A-Z0-9]+-\d+) \| (.+?) \| (.+?) \| ([0-9a-f]{64}) \| (\w+) \|$")


def _rows() -> dict[str, dict[str, str]]:
    assert BATCH.exists(), "docs/build/reports/copy-batches/batch-17.md is missing"
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        rid, page, text, sha, status = m.groups()
        assert rid not in rows, f"duplicate row id {rid}"
        rows[rid] = {"page": page, "text": text, "sha256": sha, "status": status}
    return rows


def test_batch_17_file_exists_and_has_rows() -> None:
    assert _rows(), "batch-17.md has no parseable rows"


def test_every_row_sha_matches_its_sentence() -> None:
    for rid, row in _rows().items():
        actual = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        assert actual == row["sha256"], f"{rid}: sha256 does not match the text"


def test_status_vocabulary() -> None:
    for rid, row in _rows().items():
        assert row["status"] in {"pending", "confirmed"}, f"{rid}: bad status"


def test_every_binding_cites_a_batch_row() -> None:
    """Every data-copy id on the new surfaces resolves to a batch-17 row (or a
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
    """A registered sentence that binds nothing is dead copy — every batch-17
    row must appear as a `data-copy` attribute, a `batchIds` member, or a
    `copy: <id>`/comment binding in the libs."""
    rows = _rows()
    page_src = "\n".join(p.read_text(encoding="utf-8") for p in PAGES)
    lib_src = "\n".join(p.read_text(encoding="utf-8") for p in LIBS)
    for rid in rows:
        bound = rid in page_src or rid in lib_src or f"copy: {rid}" in lib_src
        assert bound, f"batch-17 row {rid} is bound to no rendered element or lib copy"


def test_ek_rows_are_five_part_complete() -> None:
    """Each kind cause carries all five parts (state/missing/nearby/
    action/change) — a partial kind row is not the K14 contract."""
    ids = {rid for rid in _rows() if rid.startswith("EK-")}
    assert len(ids) == 20, f"expected 20 EK rows (4 causes × 5 parts), got {len(ids)}"


def test_binding_sources_exist() -> None:
    for p in PAGES + LIBS:
        assert p.exists(), p
