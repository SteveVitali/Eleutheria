# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.73 — the 11C acceptance note generator/checker invariants.

Never a living record: the tests run over synthetic manifest/index/
DEFERRALS/map fixtures — the note's layer honesty (a row never reports
above its BUILD_INDEX evidence), the every-row-once rule, the exit-item
verdict grammar, the suppressed-record citation and the derived P36.*
open-issues set.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_report_11c as ar  # noqa: E402


MANIFEST = """\
# manifest
## The chain

### Round 11 — P36 11C "Explorable core" · part 1, Wave C (rows 344–345) · spec: Part XII (§56)

| # | Ticket file | Phase | Kind | Lane | Scope | Gate |
|---|---|---|---|---|---|---|
| 344 | `344_P37.1__osm-camera-site-origin.md` | 36 | ticket | C | x | none |
| 345 | `345_P37.2__wave-c-osm-national-alpr-layer.md` | 36 | ticket | C | x | none |

### Round 11 — P36 11C "Explorable core" · part 2, to GATE-G6 (rows 346–420) · spec: Part XII (§56)

| # | Ticket file | Phase | Kind | Lane | Scope | Gate |
|---|---|---|---|---|---|---|
| 346 | `346_P35.2__alerting-as-code-and-escalation.md` | 36 | ticket | C | x | none |
| 419 | `419_P36.73__sub-round-11c-acceptance.md` | 36 | capstone | C | x | none |
| 420 | `420_GATE-G6__11c-check-in.md` | 36 | gate | A | x | gate |
| 421 | `421_P37.3__evidence-store-hardening.md` | 37 | ticket | C | x | none |

## After
"""

INDEX = """\
| seq | ticket | kind | branch | pr | base | landed | adr | obligations | status | paths | harness |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 344 | P37.1 | ticket | b | #1 | x | 2026-11-01 | — | — | engineered + fixture-verified (`live_verification=false`) | p | h |
| 346 | P35.2 | ticket | b | #2 | x | 2026-11-01 | — | — | engineered + fixture-verified + live-read ran (`live_verification=true`) | p | h |
"""

DEFERRALS = """\
| id | kind | item | why | unblocked | verify | proxy | status |
|---|---|---|---|---|---|---|---|
| D-P36.72b-1 | V | x | y | z | w | p | OPEN — created 2026-11-05 by P36.72b |
| D-P36.64-1 | V | x | y | z | w | p | OPEN — created 2026-11-04 by P36.64 |
| D-P36.56-2 | V | x | y | z | w | p | DONE 2026-11-04 (P36.64) |
| D-R11-RIGHTS-1 | P | x | y | z | w | p | OPEN 2026-10-01 |
| D-P21.7-1 | V | x | y | z | w | p | OPEN |
"""

MAP = {
    "row": [
        {
            "key": "P36.72b",
            "legs": [
                {
                    "id": "P36.72b-promote",
                    "earliest": "after the operator's HG-11 signed readout",
                    "go": "operator: the signed readout",
                }
            ],
        },
        {
            "key": "P36.12",
            "legs": [
                {
                    "id": "P36.12-l0-wave-open",
                    "earliest": "2026-10-26 — window",
                    "go": "verbatim-go: ING-GO-B",
                }
            ],
        },
    ]
}

SUPPRESSED = {
    "version": "sig.probe-run/1",
    "generated_at": "2026-11-05T13:00:00Z",
    "overall": "suppressed",
    "suppressed": "p36_72b_promotion: queued",
    "rerun_prompt": "implement-spec spec=docs/tickets/419_P36.73__sub-round-11c-acceptance.md live_verification=true",
}


def test_manifest_rows_scope_344_420():
    rows = ar.manifest_rows(MANIFEST)
    seqs = [r["seq"] for r in rows]
    assert seqs == ["344", "345", "346", "419", "420"]
    assert rows[-1]["ticket"] == "GATE-G6"


def test_p36_deferral_ids_derives_the_11c_set():
    ids = ar.p36_deferral_ids(DEFERRALS)
    assert ids == ["D-P36.72b-1", "D-P36.64-1", "D-P36.56-2"]
    assert "D-R11-RIGHTS-1" not in ids  # carried, not derived


def test_exit_items_all_queued_while_the_promote_is_queued(tmp_path):
    items = ar.evaluate_exit_items(
        root=tmp_path,
        map_data=MAP,
        now=ar._iso("2026-11-05T13:00:00Z"),
        record=SUPPRESSED,
        legs={"due": []},
    )
    assert len(items) == len(ar.EXIT_ITEMS) == 6
    assert all(i["verdict"] == "queued" for i in items)
    e1 = items[0]["evidence"]
    assert "P36.12-l0-wave-open" in e1 and "P36.72b-promote" in e1


def test_expired_go_moves_to_awaiting_go():
    data = {
        "row": [
            {
                "key": "P35.5",
                "legs": [
                    {
                        "id": "P35.5-r2-mirror",
                        "earliest": "2026-10-20T14:00:00Z",
                        "go": "pre-authorised: S5-3 (11A list; expires GATE-G4)",
                    },
                    {
                        "id": "P35.5-other",
                        "earliest": "2026-10-20T14:00:00Z",
                        "go": "pre-authorised: the 11C list (expires GATE-G6)",
                    },
                ],
            }
        ]
    }
    legs = ar.evaluate_legs_11c(data, ar._iso("2026-11-05T13:00:00Z"), True)
    assert [x["leg"] for x in legs["awaiting_go"]] == ["P35.5-r2-mirror"]
    # the 11C go stays held — due, not awaiting
    assert [x["leg"] for x in legs["due"]] == ["P35.5-other"]


def test_render_note_shape(tmp_path):
    # minimal committed-record reads the renderer touches
    (tmp_path / "docs/build/readouts").mkdir(parents=True)
    (tmp_path / "docs/build/readouts/GATE-G4.md").write_text(
        "Status: SIGNED", encoding="utf-8"
    )
    (tmp_path / "docs/build/readouts/GATE-G5.md").write_text(
        "Status: SIGNED", encoding="utf-8"
    )
    text = ar.render(
        root=tmp_path,
        index_text=INDEX,
        manifest_text=MANIFEST,
        deferrals_text=DEFERRALS,
        map_data=MAP,
        record=SUPPRESSED,
        evaluated_at="2026-11-05T13:00:00Z",
        reads=None,
    )
    assert "# Sub-round 11C acceptance" in text
    assert "## Per-row highest layer (chain rows 344–420)" in text
    assert "suppressed" in text
    assert "P36.72b-promote" in text
    # a row with no index entry reports engineered + named, never dressed up
    assert "| 345 | P37.2 | engineered |" in text
    assert "| 344 | P37.1 | fixture-verified |" in text


def test_check_catches_a_row_above_its_evidence():
    note = """\
# x
## 11C exit items
| exit-1 | queued | l | e |
| exit-2 | queued | l | e |
| exit-3 | queued | l | e |
| exit-4 | queued | l | e |
| exit-5 | queued | l | e |
| exit-6 | queued | l | e |
## Per-row highest layer
| 344 | P37.1 | live-executed | e |
| 345 | P37.2 | engineered | e |
| 346 | P35.2 | fixture-verified | e |
| 419 | P36.73 | engineered | e |
| 420 | GATE-G6 | engineered | e |
## Open issues
## Live-leg queue — window has opened
"""
    v = ar.check(note_text=note, manifest_text=MANIFEST, index_text=INDEX)
    assert any("above its evidence" in x for x in v)


def test_check_green_on_the_generated_shape(tmp_path):
    (tmp_path / "docs/build/readouts").mkdir(parents=True)
    text = ar.render(
        root=tmp_path,
        index_text=INDEX,
        manifest_text=MANIFEST,
        deferrals_text=DEFERRALS,
        map_data=MAP,
        record=SUPPRESSED,
        evaluated_at="2026-11-05T13:00:00Z",
        reads=None,
    )
    v = ar.check(note_text=text, manifest_text=MANIFEST, index_text=INDEX)
    assert v == []
