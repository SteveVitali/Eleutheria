# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.23 (B-2) — the new component-kit-B public sentences are copy-batch rows.

Every ``CK-*`` row in ``batch-03.md`` must (a) hash-verify — sha256 over the
exact UTF-8 sentence, (b) be bound to a rendered ``data-copy`` attribute, and
(c) carry the sentence verbatim in its source file — and the publish gate must
read the row (pending ⇒ ``--apply`` refuses, never an "untracked" report).

The drafted sentences live in the absence chip's action label
(``epistemic.ts`` — "Help find it ›", the O4 affordance) and the callout
contract's kind labels (``callouts.ts`` — note · caution · known issue).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ops.publish import check_publishable_copy, load_copy_batch_statuses

REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_03 = REPO_ROOT / "docs/build/reports/copy-batches/batch-03.md"
WEB_SRC = REPO_ROOT / "web" / "src"

#: The source files the CK sentences are authored in (verbatim text lives in
#: the copy constants — the components render them through data-copy bindings).
_SENTENCE_SOURCES = (
    WEB_SRC / "lib" / "epistemic.ts",
    WEB_SRC / "lib" / "callouts.ts",
)


def _ck_rows() -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for line in BATCH_03.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5 or not cells[0].startswith("CK-"):
            continue
        rows.append((cells[0], cells[1], cells[2], cells[3], cells[4]))
    return rows


def test_every_ck_row_hash_verifies() -> None:
    rows = _ck_rows()
    assert rows, "no CK-* rows in batch-03 — the new sentences are untracked"
    for rid, _page, text, sha, _status in rows:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == sha, f"{rid}: sha256 mismatch — the row text drifted"


def test_every_ck_row_is_pending_until_operator_confirmed() -> None:
    for rid, _page, _text, _sha, status in _ck_rows():
        assert status == "pending", (
            f"{rid} is {status!r} — agent-drafted copy is pending until the "
            "operator confirms it verbatim (B-2)"
        )


def test_every_ck_sentence_is_in_its_source_file_verbatim() -> None:
    sources = "\n".join(p.read_text(encoding="utf-8") for p in _SENTENCE_SOURCES)
    for rid, _page, text, _sha, _status in _ck_rows():
        assert text in sources, f"{rid}: sentence not found verbatim in the source files"


def test_every_ck_id_is_bound_to_a_rendered_data_copy() -> None:
    """Each row id must reach a `data-copy` attribute — via the contract's
    `batchId` (Callout.astro renders it) or the chip's literal binding
    (AbsenceChip.astro renders `ABSENCE_HELP_BATCH_ID`)."""
    sources = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [
            *_SENTENCE_SOURCES,
            WEB_SRC / "components" / "AbsenceChip.astro",
            WEB_SRC / "components" / "Callout.astro",
        ]
    )
    for rid, _page, _text, _sha, _status in _ck_rows():
        assert f'"{rid}"' in sources, f"{rid}: not bound to any rendered element"


def test_publish_gate_reads_every_batch_not_just_earlier_ones(tmp_path: Path) -> None:
    """B-2: a pending CK row must report `pending` — the gate scans all
    `batch-*.md`, so republish refuses it rather than calling the sentence
    untracked."""
    dist = tmp_path / "dist"
    (dist / "map").mkdir(parents=True)
    (dist / "map" / "index.html").write_text('<a data-copy="CK-61">x</a>', encoding="utf-8")
    violations = check_publishable_copy(dist)
    assert violations, "a pending sentence must refuse --apply"
    assert any("CK-61" in v and "pending" in v for v in violations), violations
    assert not any("no row in the copy batch" in v for v in violations)


def test_batch_statuses_cover_all_ck_ids() -> None:
    statuses = load_copy_batch_statuses(BATCH_03)
    for rid, _page, _text, _sha, _status in _ck_rows():
        assert statuses.get(rid) == "pending", f"{rid} missing from the batch"
