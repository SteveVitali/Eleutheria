# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21b (B-2) — the republish-#2 sentences are copy-batch rows.

``SL-20`` (the dated attribution-correction note on ``/sources/``) and
``TB-01`` (the sig-public tombstone text) live in ``batch-02.md``: each row
must hash-verify (sha256 over the exact UTF-8 sentence — ``{correctedOn}`` in
SL-20 is the injected-data placeholder, matching the sources.astro binding),
stay ``pending`` until the operator confirms it verbatim, and be bound to the
code that renders/ships it — SL-20 to a ``data-copy="SL-20"`` element, TB-01
to the ``--tombstone-id`` path in ``ops/gcp/public-gate.sh``. A pending row
refuses ``publish-web --apply`` — the republish cannot ship an unconfirmed
sentence.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ops.publish import check_publishable_copy, load_copy_batch_statuses

REPO_ROOT = Path(__file__).resolve().parents[2]
BATCH_02 = REPO_ROOT / "docs/build/reports/copy-batches/batch-02.md"
SOURCES_ASTRO = REPO_ROOT / "web" / "src" / "pages" / "sources.astro"
PUBLIC_GATE = REPO_ROOT / "ops" / "gcp" / "public-gate.sh"

IDS = ("SL-20", "TB-01")


def _rows() -> dict[str, tuple[str, str, str, str]]:
    out: dict[str, tuple[str, str, str, str]] = {}
    for line in BATCH_02.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = cells[1:-1] if cells and cells[0] == "" else cells
        if len(cells) != 5:
            continue
        rid = cells[0]
        if rid in IDS:
            out[rid] = (cells[1], cells[2], cells[3], cells[4])
    return out


def test_both_rows_exist_and_hash_verify() -> None:
    rows = _rows()
    for rid in IDS:
        assert rid in rows, f"{rid}: no copy-batch row — the sentence is untracked"
        _page, text, sha, _status = rows[rid]
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert digest == sha, f"{rid}: sha256 mismatch — the row text drifted"


def test_both_rows_pending_until_operator_confirmed() -> None:
    for rid, (_page, _text, _sha, status) in _rows().items():
        assert status == "pending", (
            f"{rid} is {status!r} — agent-drafted copy is pending until the "
            "operator confirms it verbatim (B-2)"
        )


def test_sl20_sentence_is_verbatim_in_sources_astro() -> None:
    page, text, _sha, _status = _rows()["SL-20"]
    assert page == "/sources/"
    # the rendered sentence is split across lines; {correctedOn} is the
    # injected-data placeholder the artifact supplies (never drafted copy).
    flat = re.sub(r"\s+", " ", SOURCES_ASTRO.read_text(encoding="utf-8"))
    assert text in flat, "SL-20: the batch text is not verbatim in sources.astro"
    assert 'data-copy="SL-20"' in flat
    # the note renders ONLY behind the export's correction artifact
    assert "corrections !== null" in flat
    assert "correctedOn" in flat


def test_tb01_is_wired_to_the_tombstone_flow() -> None:
    page, _text, _sha, _status = _rows()["TB-01"]
    assert "sig-public" in page or "object" in page
    script = PUBLIC_GATE.read_text(encoding="utf-8")
    assert "--tombstone-id" in script
    # the apply path reads the row's status — a pending sentence never ships
    assert "confirmed" in script


def test_pending_sl20_refuses_publish(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    (dist / "sources").mkdir(parents=True)
    (dist / "sources" / "index.html").write_text('<p data-copy="SL-20">x</p>', encoding="utf-8")
    violations = check_publishable_copy(dist)
    assert violations, "a pending SL-20 must refuse --apply"
    assert any("SL-20" in v and "pending" in v for v in violations), violations


def test_batch_statuses_cover_both_ids() -> None:
    statuses = load_copy_batch_statuses(BATCH_02)
    for rid in IDS:
        assert statuses.get(rid) == "pending", f"{rid} missing from the batch"
