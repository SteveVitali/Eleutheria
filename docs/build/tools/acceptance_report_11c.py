#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""acceptance_report_11c.py — the P36.73 11C acceptance note (plan S2 §4.3;
SIG-MEM-011; contract docs/tickets/419_P36.73__sub-round-11c-acceptance.md).

Generates and checks ``docs/build/reports/acceptance/11C.md``: one line per
11C chain row (manifest rows 344–420 — the contract's sub-round, the two
banners "part 1, Wave C (rows 344–345)" and "part 2, to GATE-G6 (rows
346–420)") reporting the **highest layer the row really reached** — never
above the vocabulary its BUILD_INDEX evidence cell records — plus the 11C
exit items (S2 §4.3, verbatim as measured on the promoted release), the
open-issues list (the 11C-scoped DEFERRALS rows' committed lead tokens +
recorded incidents) and the due-leg evaluation of the live-leg queue.

Layer discipline is the 11A/11B tools': a row's reported layer is the
highest status-layer token present in its index evidence cell's head; rows
whose live leg is queued report their landed layer and name the queued
leg — an engineered or fixture result is never dressed as live/public.
Exit items evaluate honestly: record-checkable items are evaluated from
committed evidence at the record layer; items needing the promoted
release report ``queued`` with the legs that will evaluate them.

Two 11C deltas on the 11B machinery:

* the expired-go rule covers every expiry whose gate is **signed** — the
  11A list's S5-3/GB-Q4 (GATE-G4, signed 2026-10-09) and the 11B list's
  GATE-G5 (signed 2026-10-25) — so an ``expires GATE-G4``/``expires
  GATE-G5`` go classifies ``awaiting_go`` (the re-asking default recorded
  at those gates), while the 11C list's ``expires: GATE-G6`` stays held
  until the G6 answer is recorded; and
* the open-issues list is derived, not enumerated: every DEFERRALS row
  whose id scopes to an 11C ticket (``D-P36.*``) plus the named carried
  rows — a queued leg is listed, never smoothed.

Commands:
    generate [--root PATH] [--record PATH] [--at ISO] [--reads PATH] [--out PATH]
    check    [--root PATH] [--note PATH]

``generate`` embeds sha256 digests of its inputs and the evaluation instant;
``check`` validates the structural invariants (every 11C row exactly once,
valid layer words, no row above its evidence, every exit item verdicted,
the queue + open-issues sections present). Stdlib + acceptance_report(_11b).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

from acceptance_report import (
    CHAIN_ROW_RE,
    IDX_ROW_RE,
    ISO_RE,
    LAYER_RANK,
    LAYERS,
    TICKET_FILE_RE,
    VERDICT_WORDS,
    _digest,
    _iso,
    _pending_transitions,
    _short_evidence,
    evaluate_legs,
    highest_layer,
    index_rows,
    load_map,
)
from acceptance_report_11b import _earliest_instant, _quote, deferral_status

SUBROUND = (344, 420)  # the contract's sub-round — rows 344–420 (GATE-G6 = 420)
NOTE_REL = "docs/build/reports/acceptance/11C.md"
RECORD_REL = "docs/build/reports/acceptance/11C-probe-run.json"
MAP_REL = "docs/build/tools/record_policy/return_pass.toml"
INDEX_REL = "docs/build/BUILD_INDEX.md"
MANIFEST_REL = "docs/tickets/00_MANIFEST.md"
DEFERRALS_REL = "docs/tickets/DEFERRALS.md"
G6_READOUT_REL = "docs/build/readouts/GATE-G6.md"
G5_READOUT_REL = "docs/build/readouts/GATE-G5.md"
G4_READOUT_REL = "docs/build/readouts/GATE-G4.md"
PLAN11D_REL = "docs/build/runs/PLAN-11D.md"
WALKTHROUGHS_REL = "docs/build/reports/p36.72b-promotion/WALKTHROUGHS.md"
ACCEPTANCE_72A_REL = "docs/build/reports/p36.72a-acceptance/READOUT.md"
OWN_LEG = "P36.73-sweep-packet"
RERUN = (
    "implement-spec "
    "spec=docs/tickets/419_P36.73__sub-round-11c-acceptance.md "
    "live_verification=true"
)

#: Gos whose recorded pre-authorisation expired at a **signed** gate —
#: the 11A list (S5-3/GB-Q4/`expires GATE-G4`, GATE-G4 signed) and the 11B
#: list's re-listed legs (`expires GATE-G5`, GATE-G5 signed). The 11C
#: list's `expires: GATE-G6` stays in force until the G6 answer.
EXPIRED_GO_RE = re.compile(
    r"S5-3|GB-Q4|11A list|expires GATE-G4|11B list|expires GATE-G5", re.IGNORECASE
)

#: Rows the open-issues section carries beyond the derived D-P36.* set —
#: the rights rows the 11C work feeds, the launch-unmet MUSTs list, and
#: the sources/credential rows the 11C exits name.
CARRIED_IDS = (
    "D-R11-RIGHTS-1",
    "D-R11-LATER-04",
    "D-SOURCES.8-1",
    "D-P35.38a-1",
)


def manifest_rows(manifest_text: str) -> list[dict]:
    """The chain rows of sub-round 11C — sequence cells 344…420."""
    rows: list[dict] = []
    in_chain = False
    for line in manifest_text.splitlines():
        if line.startswith("## The chain"):
            in_chain = True
            continue
        if in_chain and line.startswith("## ") and not line.startswith("## The chain"):
            break
        if not in_chain:
            continue
        m = CHAIN_ROW_RE.match(line)
        if not m:
            continue
        seq, file_cell = m.group(1), m.group(2)
        if not re.fullmatch(r"\d+", seq):
            continue
        n = int(seq)
        if not (SUBROUND[0] <= n <= SUBROUND[1]):
            continue
        tf = TICKET_FILE_RE.search(file_cell)
        ticket = tf.group(2) if tf else file_cell.strip().split()[-1]
        rows.append({"seq": seq, "ticket": ticket, "file": file_cell.strip()})
    return rows


def evaluate_legs_11c(
    map_data: dict, now: _dt.datetime, gates_signed: bool
) -> dict[str, list[dict]]:
    """The 11B due evaluation with the 11C expired-go rule.

    A leg whose go names a pre-authorisation whose gate has signed and
    whose expiry has passed classifies ``awaiting_go`` — the re-asking
    default recorded at that gate applies (never ``due`` on a clock
    alone). ``window_opened`` stays a view over every state.
    """
    legs = evaluate_legs(map_data, now)
    if gates_signed:
        for state in ("due", "conditional", "waiting", "indeterminate"):
            moved = [x for x in legs[state] if EXPIRED_GO_RE.search(x["go"])]
            legs[state] = [x for x in legs[state] if x not in moved]
            for x in moved:
                x["expired"] = True
            legs["awaiting_go"] += moved
    opened: list[dict] = []
    for state in legs:
        if state == "window_opened":
            continue
        for x in legs[state]:
            inst = _earliest_instant(x["earliest"])
            if inst is not None and inst <= now:
                opened.append({**x, "state": state})
    legs["window_opened"] = opened
    return legs


def _gate_signed(root: Path, rel: str) -> bool:
    """The readout carries Status: SIGNED — the record, never assumed."""
    path = root / rel
    if not path.is_file():
        return False
    return "Status: SIGNED" in path.read_text(encoding="utf-8", errors="replace")


def p36_deferral_ids(deferrals_text: str) -> list[str]:
    """The derived open-issues set — every DEFERRALS row id scoping to an
    11C ticket (``D-P36.*``), in file order."""
    ids: list[str] = []
    for line in deferrals_text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 1 and re.fullmatch(r"D-P36\.[A-Za-z0-9.\-]+", cells[1] or ""):
            ids.append(cells[1])
    return ids


# ---------------------------------------------------------------------------
# Exit items — S2 §4.3 verbatim, as measured on the promoted release.
# ---------------------------------------------------------------------------

ASK_TABLE = (
    "U-003.1 basemap and map shell · U-003.2 entity pages A and "
    "Organizations · U-003.3 search v2 · U-003.4 country-grouped dossier "
    "index · U-003.5 dossier sources explorer · U-003.7 watch pages · "
    "U-003.8 evidence hub · U-003.9 sortable sources table with downloads "
    "and ground-truth links · U-003.10 source pages · U-003.11 research "
    "queue with human-readable handles"
)

EXIT_ITEMS = [
    (
        "exit-1",
        "Wave B is live: each Tier-1 source is live or dispositioned by its "
        "line; the second activated release (P36.12) is promoted; P36.70 "
        "has measured the rollback and withdrawal timings",
    ),
    (
        "exit-2",
        "P36.72 is promoted under HG-11, and every operator ask has a "
        "working page passing its K-row acceptance (" + ASK_TABLE + ")",
    ),
    (
        "exit-3",
        "Journeys A1, A2, A3, A4, J1, O1, O3 and O4 pass the agent "
        "walkthrough at 390 and 1440 px, recorded `agent-verified`",
    ),
    (
        "exit-4",
        "Search resolves 55 jurisdictions, 20 cities and the top 25 vendor "
        "and agency names",
    ),
    (
        "exit-5",
        "K0 budgets and axe pass on real data, and the facet-conformance "
        "harness is green",
    ),
    (
        "exit-6",
        "API rate limits are enforced, and the kill switch and budget "
        "alert have been tested; measured infra ≤ $300",
    ),
]

#: Every exit item is measured on the promoted release or its staged
#: service — each reports queued with the legs that evaluate it, never a
#: fabricated live pass.
LIVE_MEASURED = {f"exit-{i}" for i in range(1, 7)}

PROMO_LEG = "P36.72b-promote"
WAVE_B_ROW = "P36.12"
REHEARSAL_LEG = "P36.70-rehearsal"
SEARCH_LEG = "P36.71-acceptance-verify"
RATELIMIT_LEG = "P36.13-enforcement-flip"


def evaluate_exit_items(
    *,
    root: Path,
    map_data: dict,
    now: _dt.datetime,
    record: dict | None,
    legs: dict,
) -> list[dict]:
    """One line per exit item — verdict + layer + evidence, honestly."""
    queued_ids = {
        leg.get("id")
        for row in map_data.get("row", [])
        for leg in row.get("legs", [])
    }
    wave_b_ids = sorted(x for x in queued_ids if x.startswith("P36.12-"))
    suppressed = record is None or record.get("overall") == "suppressed"
    own_state = (
        "queued at the gate (its RETURN PASS row lands at closeout)"
        if suppressed
        else "ran"
    )
    items: list[dict] = []

    def queued_item(eid: str, text: str, extra: str) -> dict:
        return {
            "id": eid,
            "text": text,
            "verdict": "queued",
            "layer": "live-executed (not evaluated — measured on the "
            "promoted release; the sweep leg is queued)",
            "evidence": extra,
        }

    for eid, text in EXIT_ITEMS:
        if eid == "exit-1":
            items.append(
                queued_item(
                    eid,
                    text,
                    "legs still queued: "
                    + (", ".join(wave_b_ids) if wave_b_ids else "no P36.12 legs")
                    + f"; {PROMO_LEG}, {REHEARSAL_LEG} — the Wave-B window's "
                    "family days + the second activated release's promote + "
                    "the rehearsal's measured timings are evaluated on the "
                    "hosted run, never claimed",
                )
            )
        elif eid == "exit-2":
            items.append(
                queued_item(
                    eid,
                    text,
                    f"leg still queued: {PROMO_LEG} — the promote awaits the "
                    "operator's signed HG-11 Class S readout at the GATE-G6 "
                    "sitting (never pre-authorised); the U-003 ask pages are "
                    "read by the 11C sweep over the promoted release; the "
                    "K-row per-ask checks are P36.72a's fixture battery "
                    "(PASS, fixture-verified) + P37.68d's deferred packet",
                )
            )
        elif eid == "exit-3":
            wt = (root / WALKTHROUGHS_REL).is_file()
            items.append(
                queued_item(
                    eid,
                    text,
                    f"legs still queued: {PROMO_LEG}, {OWN_LEG} ({own_state}) "
                    "— the walkthroughs re-measure on the promoted release; "
                    + (
                        f"`{WALKTHROUGHS_REL}` records 9/9 agent-verified "
                        "over the fixture corpus (fixture-verified, never a "
                        "live claim)"
                        if wt
                        else "the walkthrough record is absent"
                    ),
                )
            )
        elif eid == "exit-4":
            items.append(
                queued_item(
                    eid,
                    text,
                    "legs still queued: D-P36.71-1's post-promotion verify "
                    f"legs, {PROMO_LEG} — the 55/20/25 resolution counts are "
                    "measured on the promoted release's index by "
                    "`sig-exports search-acceptance --enforce`, never now",
                )
            )
        elif eid == "exit-5":
            items.append(
                queued_item(
                    eid,
                    text,
                    f"legs still queued: {PROMO_LEG}, {OWN_LEG} ({own_state}) "
                    "— budgets + axe re-measure on the promoted release's "
                    "real data; the fixture-corpus battery is green "
                    "(P36.72a) and the two recorded measured_gaps "
                    "(D-P36.64-1/-2) are listed below, bounded + loud, "
                    "never smoothed",
                )
            )
        elif eid == "exit-6":
            items.append(
                queued_item(
                    eid,
                    text,
                    "legs still queued: the P36.13 rate-limit enforcement "
                    "flip (D-P36.13-1 — never pre-authorised beyond its "
                    "GATE-G5 naming; the sweep's rate-limit leg reads the "
                    "headers once enforcement lands) — the kill-switch and "
                    "budget-alert test and the measured-vs-$300 read are "
                    "evaluated on the hosted deployment, never claimed; "
                    "the committed spend ledger stays estimates, not "
                    "measured billing",
                )
            )
    return items


# ---------------------------------------------------------------------------
# The note
# ---------------------------------------------------------------------------


def render(
    *,
    root: Path,
    index_text: str,
    manifest_text: str,
    deferrals_text: str,
    map_data: dict,
    record: dict | None,
    evaluated_at: str,
    reads: dict | None,
) -> str:
    mrows = manifest_rows(manifest_text)
    index = index_rows(index_text)
    now = _iso(evaluated_at)
    gates_signed = _gate_signed(root, G4_READOUT_REL) and _gate_signed(
        root, G5_READOUT_REL
    )
    legs = evaluate_legs_11c(map_data, now, gates_signed)
    items = evaluate_exit_items(
        root=root, map_data=map_data, now=now, record=record, legs=legs
    )
    deferral_ids = p36_deferral_ids(deferrals_text) + [
        d for d in CARRIED_IDS if d not in p36_deferral_ids(deferrals_text)
    ]

    digests = {
        "index": _digest(index_text),
        "manifest": _digest(manifest_text),
        "deferrals": _digest(deferrals_text),
        "map": _digest(json.dumps(map_data, sort_keys=True)),
        "record": _digest(json.dumps(record, sort_keys=True)) if record else "absent",
    }
    if record is None:
        record_line = "no probe-run record found — the sweep has not run"
    elif record.get("overall") == "suppressed":
        record_line = (
            f"`{RECORD_REL}` — **suppressed** (gate refusals: "
            f"{record.get('suppressed', '—')}); the live sweep is **queued** "
            f"with re-run prompt `{record.get('rerun_prompt', '')}`"
        )
    else:
        record_line = (
            f"`{RECORD_REL}` — overall `{record.get('overall')}` "
            f"generated {record.get('generated_at')}"
        )

    lines = [
        "# Sub-round 11C acceptance — per-row highest layer (P36.73)",
        "",
        "<!-- Generated by docs/build/tools/acceptance_report_11c.py — do not",
        "     hand-edit. Regenerate: `python3 docs/build/tools/acceptance_report_11c.py",
        "     generate` (the live-leg rerun regenerates only after a sweep",
        "     runs — the sweep is queued now).",
        "     Layer honesty (SIG-MEM-011): a row never reports above the layer",
        "     its BUILD_INDEX evidence records; a queued leg is named, never",
        "     dressed as a result. -->",
        "",
        f"- evaluated_at: {evaluated_at}",
        f"- inputs: BUILD_INDEX `{digests['index']}` · manifest `{digests['manifest']}` · "
        f"DEFERRALS `{digests['deferrals']}` · return_pass map `{digests['map']}` · "
        f"probe-run record `{digests['record']}`",
        f"- probe-run record: {record_line}",
        "- layer vocabulary: engineered · fixture-verified · staging-verified · "
        "live-executed · public · human-completed",
        "",
        "## 11C exit items (S2 §4.3, verbatim as measured on the promoted release)",
        "",
        "| item | verdict | layer | evidence |",
        "|---|---|---|---|",
    ]
    for it in items:
        ev = (it.get("evidence") or "").replace("|", "/")
        # the item text is the verbatim S2 §4.3 criterion — quoted as the
        # plan's words, a queued claim never asserted of the served state
        lines.append(
            f"| {it['id']} | {it['verdict']} | {it['layer']} | queued exit "
            f"item, verbatim S2 §4.3: {it['text']} — {ev} |"
        )
    lines += [
        "",
        "## Per-row highest layer (chain rows 344–420)",
        "",
        "| row | ticket | highest layer reached | evidence (first clause) |",
        "|---|---|---|---|",
    ]
    for r in mrows:
        idx = index.get(r["seq"])
        if idx is None:
            lines.append(
                f"| {r['seq']} | {r['ticket']} | engineered | **no BUILD_INDEX "
                "row — not landed at any layer** |"
            )
            continue
        layer = highest_layer(idx["cell"]) or "engineered"
        lines.append(
            f"| {r['seq']} | {r['ticket']} | {layer} | {_short_evidence(idx['cell'])} |"
        )
    lines += [
        "",
        "## Open issues (DEFERRALS lead tokens at the committed cells + "
        "recorded incidents)",
        "",
        "Each named row is reported open or closed with its evidence — a "
        "lead token changes only through a matching `obligation-event/1` "
        "transition, never here. The D-P36.* set is derived from the "
        "committed file; the carried rows are named. Every open issue "
        "stays visible and linked.",
        "",
        "| id | committed lead token | note |",
        "|---|---|---|",
    ]
    for did in deferral_ids:
        token = deferral_status(deferrals_text, did)
        note = {
            "D-P36.72b-1": "the Class S promote — the sweep's own "
            "precondition; the operator's signed HG-11 readout at the "
            "GATE-G6 sitting",
            "D-P36.70-1": "the second-release acceptance rehearsal — rides "
            "the promote (exit-1's measured timings)",
            "D-P36.71-1": "the post-promotion search-acceptance verify "
            "legs — exit-4's 55/20/25 measure",
            "D-P36.79-1": "the sealed held-out object write — the G5-named "
            "mutation still queued (exit-4's sealed read)",
            "D-P36.68-1": "the mirror writes — the sweep's mirrors leg "
            "stays skipped until `r2-public` enables",
            "D-P36.13-1": "the rate-limit enforcement flip — exit-6's "
            "enforcement evidence",
            "D-P36.64-1": "the /dossier/ totalInitialMaxBytes measured gap "
            "(bounded + loud; the T1 initial-bytes row owns it)",
            "D-P36.64-2": "the / lcpMs measured gap (bounded + loud; the "
            "same T1 row owns it)",
            "D-R11-RIGHTS-1": "the ADR-169 re-decision rows — owner P36.2 "
            "+ the operator; staged keep/decline lines recorded",
            "D-R11-LATER-04": "the ADR-171 Stage-0 set — owed, unmet at "
            "launch; the packet's status part carries it",
            "D-SOURCES.8-1": "four gated camreg rows — the Edmonton terms "
            "capture queued under D-P36.2-1",
            "D-P35.38a-1": "the probe-capture seam the Wave-C rows depend "
            "on — queued",
        }.get(did, "the 11C-scoped owed leg — its DEFERRALS row carries "
                  "owner/trigger/verify")
        lines.append(f"| `{did}` | {token} | {note} |")
    lines += [
        "| NIGHTLY-RED-1 | recorded (LEDGER OPEN FINDINGS) | the scheduled "
        "`nightly.yml` runs on `main` failed 2026-10-07 → 10-20 (14 runs) — "
        "the owed observation of `D-P34.7-1`/`D-P34.2-2`; repair routed "
        "separately, never smoothed here |",
        "| Wave-A window | anomaly — recorded | P35.11's legs' window "
        "10-19 → 10-23 elapsed unrun (the legs stay queued, verbatim-go) — "
        "listed and carried to GATE-G6, never smoothed |",
        "| `SIG_GCP_PROJECT` posture | recorded | fail-closed by design "
        "(OP-07) — hosted legs stay queued; no credentials are inferred |",
        "",
        "## Live-leg queue (all legs queued — none has run) — due "
        "evaluation at the evaluation instant",
        "",
        "A leg is **due** when its earliest instant has passed and its go is "
        "held (OM-19); a verbatim/operator go not yet given is `awaiting-go`, "
        "never due; a `pre-authorised:` go whose recorded expiry has passed "
        "(the 11A list's S5-3/GB-Q4 at the signed GATE-G4, the 11B list's "
        "GATE-G5 at its signed sitting) is awaiting-go too — the recorded "
        "re-asking default applies; the 11C list's `expires: GATE-G6` stays "
        "in force until the G6 answer is recorded. `conditional` = the "
        "earliest's named extra conditions are not machine-verifiable; "
        "`indeterminate` = no parseable earliest. Leg earliest/go cells are "
        "quoted verbatim inside code spans (their own markdown ticks render "
        "as `'`); a code-quoted cell is verbatim record text, never an "
        "assertion of its production words.",
        "",
        "### Legs whose recorded window has opened (listed, never smoothed — "
        "the contract's rule)",
        "",
    ]
    if not legs["window_opened"]:
        lines.append("- none")
    for x in legs["window_opened"]:
        lines.append(
            f"- `{x['leg']}` ({x['row']}) — earliest: {_quote(x['earliest'])}; "
            f"state: {x['state']}; go: {_quote(x['go'])}"
        )
    lines.append("")
    for state, label in (
        ("due", "**due** (unrun, window open)"),
        ("conditional", "conditional-due (earliest passed, extra conditions unverified)"),
        ("awaiting_go", "awaiting-go (go not held / lapsed)"),
        ("indeterminate", "indeterminate earliest"),
        ("waiting", "waiting (earliest in the future)"),
    ):
        lines.append(f"### {label}")
        if not legs[state]:
            lines.append("- none")
        for x in legs[state]:
            suffix = " — *pre-authorisation expired at a signed gate*" if x.get("expired") else ""
            lines.append(
                f"- `{x['leg']}` ({x['row']}) — earliest: {_quote(x['earliest'])}; "
                f"go: {_quote(x['go'])}{suffix}"
            )
        lines.append("")
    lines += [
        "## Also read",
        "",
        f"- live-leg queue: {sum(len(v) for k, v in legs.items() if k != 'window_opened')} "
        f"legs queued in the RETURN PASS map ({len(legs['due'])} due · "
        f"{len(legs['conditional'])} conditional · "
        f"{len(legs['awaiting_go'])} awaiting-go · "
        f"{len(legs['indeterminate'])} indeterminate · {len(legs['waiting'])} waiting); "
        f"{len(legs['window_opened'])} legs' recorded windows have opened",
        f"- the GATE-G6 packet draft: `{G6_READOUT_REL}` (agent-drafted, "
        "sha256-labelled — it decides nothing; GATE-G6's answers are the "
        "operator's own verbatim lines)",
        f"- the GATE-G5 record: `{G5_READOUT_REL}` (Status: SIGNED "
        "2026-10-25 — its answered lines are quoted, never re-asked)",
        f"- PLAN-11D's run ledger `{PLAN11D_REL}` — the draft 11D OM-20 "
        "list the packet cites (15 rows with written `Production "
        "mutations` headers; `expires:` the next GATE)",
        f"- the core-surfaces evidence the promote reads: "
        f"`{ACCEPTANCE_72A_REL}` (`sig.core-surfaces-acceptance/1`, PASS "
        "fixture-verified) + the agent walkthrough record "
        f"`{WALKTHROUGHS_REL}` (9/9, fixture corpus, `agent-verified`)",
    ]
    if reads:
        lines.append(
            f"- leg-captured reads supplied: {sorted(reads)} — verbatim, "
            "never fabricated"
        )
    lines += ["- the re-run prompt, verbatim: `" + RERUN + "`", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# check — the structural invariants (OM-15: never asserts a living value).
# ---------------------------------------------------------------------------


def check(
    *,
    note_text: str,
    manifest_text: str,
    index_text: str,
) -> list[str]:
    violations: list[str] = []
    mrows = manifest_rows(manifest_text)
    index = index_rows(index_text)

    if "## Per-row highest layer" not in note_text:
        violations.append("no per-row section")
    if "## 11C exit items" not in note_text:
        violations.append("no exit-items section")
    if "## Open issues" not in note_text:
        violations.append("no open-issues section")
    if "## Live-leg queue" not in note_text:
        violations.append("no live-leg queue section")
    if "window has opened" not in note_text:
        violations.append("no window-opened listing")

    row_re = re.compile(
        r"^\|\s*(\d+[a-z]*)\s*\|\s*(P[\w.\-]+|GATE-[\w.\-]+|PLAN-[\w.\-]+|SEED-[\w.\-]+)"
        r"\s*\|\s*([\w\-]+)\s*\|",
        re.M,
    )
    seen: dict[str, int] = {}
    in_rows = False
    for line in note_text.splitlines():
        if line.startswith("## Per-row highest layer"):
            in_rows = True
            continue
        if in_rows and line.startswith("## "):
            in_rows = False
        if not in_rows or not line.startswith("|"):
            continue
        m = row_re.match(line)
        if not m:
            continue
        seq, ticket, layer = m.groups()
        seen[seq] = seen.get(seq, 0) + 1
        if layer not in LAYERS:
            violations.append(f"row {seq}: unknown layer word '{layer}'")
            continue
        cell_layer = highest_layer(index.get(seq, {}).get("cell", ""))
        if cell_layer and LAYER_RANK[layer] > LAYER_RANK[cell_layer]:
            violations.append(
                f"row {seq} ({ticket}): reported '{layer}' above its evidence "
                f"('{cell_layer}')"
            )
        if ticket != index.get(seq, {}).get("ticket", ticket):
            violations.append(f"row {seq}: ticket {ticket} != index")
    for r in mrows:
        if seen.get(r["seq"], 0) != 1:
            violations.append(
                f"chain row {r['seq']} ({r['ticket']}): listed "
                f"{seen.get(r['seq'], 0)} times, expected 1"
            )

    in_items = False
    item_count = 0
    for line in note_text.splitlines():
        if line.startswith("## 11C exit items"):
            in_items = True
            continue
        if in_items and line.startswith("## "):
            in_items = False
        if not in_items or not line.startswith("| exit-"):
            continue
        item_count += 1
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 5 or cells[2] not in VERDICT_WORDS:
            violations.append(
                f"exit item '{cells[1] if len(cells) > 1 else '?'}': "
                "no valid verdict word"
            )
    if item_count != len(EXIT_ITEMS):
        violations.append(
            f"{item_count} exit items listed, expected {len(EXIT_ITEMS)}"
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="acceptance_report_11c.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="write the 11C acceptance note")
    g.add_argument("--root", default=".")
    g.add_argument("--record", default=None, help="the probe-run record JSON")
    g.add_argument(
        "--at",
        dest="at",
        default=None,
        help="evaluation instant (default: the record's generated_at, else the clock)",
    )
    g.add_argument("--reads", default=None, help="optional leg-captured reads JSON")
    g.add_argument("--out", default=None, help=f"default {NOTE_REL}")
    c = sub.add_parser("check", help="structural invariants of the committed note")
    c.add_argument("--root", default=".")
    c.add_argument("--note", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root)
    index_text = (root / INDEX_REL).read_text(encoding="utf-8")
    manifest_text = (root / MANIFEST_REL).read_text(encoding="utf-8")
    deferrals_path = root / DEFERRALS_REL
    deferrals_text = (
        deferrals_path.read_text(encoding="utf-8") if deferrals_path.is_file() else ""
    )

    if args.cmd == "check":
        note = Path(args.note) if args.note else root / NOTE_REL
        if not note.is_file():
            print(f"check: {note} absent", file=sys.stderr)
            return 3
        violations = check(
            note_text=note.read_text(encoding="utf-8"),
            manifest_text=manifest_text,
            index_text=index_text,
        )
        if violations:
            for v in violations:
                print(f"check: {v}", file=sys.stderr)
            return 1
        print("check: ok")
        return 0

    record = None
    rec_path = Path(args.record) if args.record else root / RECORD_REL
    if rec_path.is_file():
        record = json.loads(rec_path.read_text(encoding="utf-8"))
    reads = None
    if args.reads:
        reads = json.loads(Path(args.reads).read_text(encoding="utf-8"))
    evaluated_at = args.at or (record or {}).get("generated_at") or _dt.datetime.now(
        _dt.UTC
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = render(
        root=root,
        index_text=index_text,
        manifest_text=manifest_text,
        deferrals_text=deferrals_text,
        map_data=load_map(root),
        record=record,
        evaluated_at=evaluated_at,
        reads=reads,
    )
    out = Path(args.out) if args.out else root / NOTE_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(
        f"acceptance_report_11c: wrote {out} ({len(text.encode('utf-8'))} B)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
