# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project.

"""P36.64 — copy batch 16 parses, hashes verify, and the D-K14-1 held lines
never ship.

Batch 16 registers the UXK14-6 copy: the held K14 §2.1 lines (sub-head,
About paragraph, why-it-exists, four "is not" lines — D-K14-1 [C-4]: pending,
bound to NO element, never shipped text), the confirmed tagline (K14-00, the
answered half), and the new agent-drafted sentences on /, /about/,
/coverage-metrics/, /editorial-standards/ and lib/capabilities.ts.

The test asserts: the file parses and every sha256 verifies; every held
K14-* text is ABSENT from every web/src file (a fixture build carrying
unconfirmed copy fails — SIG-ENG-042); no "who runs SIG" section or
placeholder exists anywhere in the pages (D-K14-7 [C-5] — a hard failure);
every rendered `data-copy` id in the four pages cites a batch-16 row (or a
prior batch's row for shared copy like JD-06); and every non-held batch-16
row is bound somewhere (a `data-copy` attr or a `copy:` comment in the lib).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "docs/build/reports/copy-batches/batch-16.md"
PAGES = [
    ROOT / "web/src/pages/index.astro",
    ROOT / "web/src/pages/about.astro",
    ROOT / "web/src/pages/coverage-metrics.astro",
    ROOT / "web/src/pages/editorial-standards.astro",
]
LIBS = [ROOT / "web/src/lib/capabilities.ts", ROOT / "web/src/lib/onboarding.ts"]
WEB_SRC = ROOT / "web/src"

ROW_RE = re.compile(r"^\| ([A-Z0-9]+-\d+) \| (.+?) \| (.+?) \| ([0-9a-f]{64}) \| (\w+) \|$")
HELD_RE = re.compile(r"^K14-0[1-7]$")


def _rows() -> dict[str, dict[str, str]]:
    assert BATCH.exists(), "docs/build/reports/copy-batches/batch-16.md is missing"
    rows: dict[str, dict[str, str]] = {}
    for line in BATCH.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        rid, page, text, sha, status = m.groups()
        assert rid not in rows, f"duplicate row id {rid}"
        rows[rid] = {"page": page, "text": text, "sha256": sha, "status": status}
    return rows


def _web_src_text() -> str:
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in WEB_SRC.rglob("*")
        if p.is_file() and p.suffix in {".astro", ".ts", ".tsx"}
    )


def test_batch_16_file_exists_and_has_rows() -> None:
    assert _rows(), "batch-16.md has no parseable rows"


def test_every_row_sha_matches_its_sentence() -> None:
    for rid, row in _rows().items():
        actual = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        assert actual == row["sha256"], f"{rid}: sha256 does not match the text"


def test_status_vocabulary_and_held_rows_pending() -> None:
    rows = _rows()
    assert any(HELD_RE.match(rid) for rid in rows), "no held K14-* rows found"
    for rid, row in rows.items():
        assert row["status"] in {"pending", "confirmed"}, f"{rid}: bad status"
        if HELD_RE.match(rid):
            assert row["status"] == "pending", (
                f"{rid}: held lines stay pending until the operator confirms"
            )
            assert row["page"] == "held", f"{rid}: held rows bind no page — got {row['page']}"


def test_held_k14_lines_never_ship() -> None:
    """D-K14-1 [C-4]: the sub-head, About paragraph, why-it-exists line and the
    four 'is not' lines ship ONLY after verbatim confirmation — an unconfirmed
    line inside a fixture build is a hard failure, never silently shipped."""
    src = _web_src_text()
    for rid, row in _rows().items():
        if not HELD_RE.match(rid):
            continue
        # Compare on the longest distinctive clause so markup wrapping can't
        # hide a shipped line.
        for clause in re.split(r"(?<=[.!?])\s+", row["text"]):
            probe = clause.strip()
            if len(probe) >= 20:
                assert probe not in src, f"{rid}: held K14 line ships in web/src — {probe!r}"


def test_tagline_ships_confirmed() -> None:
    """D-K14-1's answered half: the tagline ships, recorded confirmed."""
    row = _rows().get("K14-00")
    assert row is not None and row["status"] == "confirmed"
    assert row["text"] == "Public surveillance, traced to the documents."


def test_no_who_runs_sig_section_or_placeholder() -> None:
    """D-K14-7 [C-5]: 'Omit until I write it' — a 'who runs SIG' section or a
    placeholder for one is a hard failure."""
    src = _web_src_text().lower()
    for banned in (
        "who runs sig",
        "who runs the",
        "maintained by a single independent maintainer with ai agents",
    ):
        assert banned not in src, f"D-K14-7: banned 'who runs SIG' wording found — {banned!r}"


def test_every_binding_cites_a_batch_row() -> None:
    rows = _rows()
    # Prior batches' rows shared by reference (JD-06 lives in batch-01).
    prior = set()
    for other in (ROOT / "docs/build/reports/copy-batches").glob("batch-*.md"):
        if other == BATCH:
            continue
        for line in other.read_text(encoding="utf-8").splitlines():
            m = ROW_RE.match(line)
            if m:
                prior.add(m.group(1))
    src = "\n".join(p.read_text(encoding="utf-8") for p in PAGES)
    for rid in re.findall(r'data-copy="([A-Z0-9]+-\d+(?:\s+[A-Z0-9]+-\d+)*)"', src):
        for token in rid.split():
            assert token in rows or token in prior, f"data-copy cites {token} — no copy-batch row"


def test_every_non_held_row_is_bound() -> None:
    rows = _rows()
    page_src = "\n".join(p.read_text(encoding="utf-8") for p in PAGES)
    lib_src = "\n".join(p.read_text(encoding="utf-8") for p in LIBS)
    for rid in rows:
        if HELD_RE.match(rid) or rid == "K14-00":
            continue
        bound = rid in page_src or f"copy: {rid}" in lib_src
        assert bound, f"batch-16 row {rid} is bound to no rendered element or lib comment"


def test_binding_sources_exist() -> None:
    for p in PAGES + LIBS:
        assert p.exists(), p
