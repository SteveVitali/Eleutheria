# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project.

"""P36.55 — the copy-batch-14 register exists, parses and stays honest.

Batch 14 is the row the dossier-template-v2 ticket (K6 VIZ-02) needed after
batch-13: it registers the new agent-drafted public sentences — the Figure-1
typed empty states + caption chrome, the locator statuses, the Explore bar
labels, the 'Next decisions' block, the 'Other public resources' block and
the network-slot empty states — so they are tracked, hashable and pending
operator verbatim confirmation rather than silently shipping (B-2).

The test does not judge wording. It asserts the batch file exists, that
every row carries the five fields (id, page, exact text, sha256, status),
that each sha256 actually matches its sentence, that every row is still
`pending` (none smuggled to `confirmed`), and — the honesty check — that
each new element's `data-copy` attribute names batch-14 rows that exist
(and that every batch-14 row's id is bound to a rendered element, so no
sentence sits unverifiable in the register).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/build/reports/copy-batches/batch-14.md"

# The source files whose data-copy attributes bind to batch-14 rows.
BINDING_SOURCES = [
    ROOT / "web/src/components/dossier/DossierMapFigure.astro",
    ROOT / "web/src/components/dossier/DossierLocator.astro",
    ROOT / "web/src/components/dossier/DossierExploreBar.astro",
    ROOT / "web/src/components/dossier/DossierNextDecisions.astro",
    ROOT / "web/src/components/dossier/OtherPublicResources.astro",
    ROOT / "web/src/components/dossier/NetworkFigureSlot.astro",
]

ROW_RE = re.compile(r"^\| ([A-Z]+-\d+) \| (.+?) \| (.+?) \| ([0-9a-f]{64}) \| (\w+) \|$")


def _parse_rows() -> dict[str, dict[str, str]]:
    assert BATCH.exists(), "docs/build/reports/copy-batches/batch-14.md is missing"
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        rid, page, text, sha, status = m.groups()
        assert rid not in rows, f"duplicate row id {rid}"
        rows[rid] = {"page": page, "text": text, "sha256": sha, "status": status}
    return rows


def test_batch_14_file_exists_and_has_rows() -> None:
    rows = _parse_rows()
    assert rows, "batch-14.md has no parseable rows"


def test_every_row_sha_matches_its_sentence() -> None:
    rows = _parse_rows()
    for rid, row in rows.items():
        actual = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        assert actual == row["sha256"], f"{rid}: sha256 does not match the text"


def test_every_row_is_pending_and_on_the_dossier_page() -> None:
    rows = _parse_rows()
    for rid, row in rows.items():
        assert row["status"] == "pending", (
            f"{rid} is {row['status']} — pending only until the operator confirms"
        )
        assert row["page"] == "/dossier/&lt;path&gt;/", f"{rid}: unexpected page {row['page']}"


def test_every_binding_cites_a_batch_14_row() -> None:
    rows = _parse_rows()
    src = "\n".join(p.read_text(encoding="utf-8") for p in BINDING_SOURCES)
    for rid in re.findall(r'"(MF-\d+|LC-\d+|EB-\d+|ND-\d+|OR-\d+|NF-\d+)"', src):
        assert rid in rows, f"source cites {rid} — no batch-14 row with that id"


def test_every_new_row_binds_to_a_rendered_element() -> None:
    rows = _parse_rows()
    src = "\n".join(p.read_text(encoding="utf-8") for p in BINDING_SOURCES)
    for rid in rows:
        assert f'"{rid}"' in src, f"batch-14 row {rid} is not bound to any rendered element"


@pytest.mark.parametrize(
    "path",
    [p for p in BINDING_SOURCES],
    ids=lambda p: p.name,
)
def test_binding_source_files_exist(path: Path) -> None:
    assert path.exists()
