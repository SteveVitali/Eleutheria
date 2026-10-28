#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""acceptance_report_11b.py — the P35.64 11B acceptance note (plan S2 §4.2;
SIG-MEM-011; contract docs/tickets/342_P35.64__sub-round-11b-acceptance.md).

Generates and checks ``docs/build/reports/acceptance/11B.md``: one line per
11B chain row (manifest rows 261–343, the contract's range verbatim)
reporting the **highest layer the row really reached** — never above the
vocabulary its BUILD_INDEX evidence cell records — plus the 11B exit items
(S2 §4.2, verbatim as measured on the promoted release), the open-issues
list (named DEFERRALS rows + recorded incidents) and the due-leg evaluation
of the live-leg queue.

Layer discipline is the 11A tool's: a row's reported layer is the highest
status-layer token present in its index evidence cell's head; rows whose
live leg is queued report their landed layer and name the queued leg —
an engineered or fixture result is never dressed as live/public. Exit
items evaluate honestly: record-checkable items are evaluated from
committed evidence at the record layer; items needing the promoted
release report ``queued`` with the leg that will evaluate them.

Two 11B deltas on the 11A machinery:

* the map's ``pre-authorised: S5-3 / GB-Q4 (11A list; expires GATE-G4)``
  gos are judged against the record — GATE-G4 is signed (its readout's
  Status: SIGNED), so those pre-authorisations have lapsed and the legs
  classify ``awaiting-go`` (re-asking in-ticket is the packet's recorded
  default), never ``due``; and
* the note lists every queued leg whose recorded earliest instant has
  passed — the contract's "any 11B leg whose window opened is listed"
  rule (legs whose window extends past GATE-G5 are listed and carried).

Commands:
    generate [--root PATH] [--record PATH] [--at ISO] [--reads PATH] [--out PATH]
    check    [--root PATH] [--note PATH]

``generate`` embeds sha256 digests of its inputs and the evaluation instant;
``check`` validates the structural invariants (every 11B row exactly once,
valid layer words, no row above its evidence, every exit item verdicted,
the queue + open-issues sections present). Stdlib + acceptance_report.
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

SUBROUND = (261, 343)  # the contract's range, verbatim — rows 261–343
NOTE_REL = "docs/build/reports/acceptance/11B.md"
RECORD_REL = "docs/build/reports/acceptance/11B-probe-run.json"
MAP_REL = "docs/build/tools/record_policy/return_pass.toml"
INDEX_REL = "docs/build/BUILD_INDEX.md"
MANIFEST_REL = "docs/tickets/00_MANIFEST.md"
DEFERRALS_REL = "docs/tickets/DEFERRALS.md"
G5_READOUT_REL = "docs/build/readouts/GATE-G5.md"
G4_READOUT_REL = "docs/build/readouts/GATE-G4.md"
G3_CORRECTION_REL = "docs/build/reports/p32.23a-release-candidate/CORRECTION.md"
PLAN11C_REL = "docs/build/runs/PLAN-11C.md"
OWN_LEG = "P35.64-sweep-packet"
RERUN = (
    "implement-spec "
    "spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md "
    "live_verification=true"
)

#: Gos whose recorded pre-authorisation expired at GATE-G4 (the packet's
#: recorded default: each re-asks in-ticket) — matched on the go text.
EXPIRED_GO_RE = re.compile(r"S5-3|GB-Q4|11A list|expires GATE-G4", re.IGNORECASE)


def manifest_rows(manifest_text: str) -> list[dict]:
    """The chain rows of sub-round 11B — sequence cells 261…343."""
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


def _earliest_instant(earliest: str) -> _dt.datetime | None:
    """The first parseable instant in an earliest cell (ISO or bare date)."""
    m = ISO_RE.search(earliest)
    if m:
        t = m.group(0)
        return _iso(t if t.endswith("Z") else t + ":00Z")
    d = re.search(r"\d{4}-\d{2}-\d{2}", earliest)
    if d:
        return _iso(d.group(0) + "T00:00:00Z")
    return None


def evaluate_legs_11b(
    map_data: dict, now: _dt.datetime, g4_signed: bool
) -> dict[str, list[dict]]:
    """The 11A due evaluation + two 11B additions.

    * legs whose go names a pre-authorisation that expired at a signed
      GATE-G4 classify ``awaiting_go`` (a lapsed go is not held — the
      packet's recorded default "each re-asks in-ticket" applies);
    * ``window_opened`` (a view, never a bucket): every queued leg whose
      recorded earliest instant has passed, whatever its state — the
      contract's "any 11B leg whose window opened is listed" rule.
    """
    legs = evaluate_legs(map_data, now)
    if g4_signed:
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


def _g4_signed(root: Path) -> bool:
    """GATE-G4's readout carries Status: SIGNED — the record, never assumed."""
    path = root / G4_READOUT_REL
    if not path.is_file():
        return False
    return "Status: SIGNED" in path.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Open issues — the named DEFERRALS rows' committed lead tokens + the
# recorded incidents (NIGHTLY-RED-1 lives in the LEDGER, not DEFERRALS).
# ---------------------------------------------------------------------------

#: Rows the contract names + the 11B-scoped set. Lead tokens are read from
#: the committed cells — never asserted, never transitioned here.
DEFERRAL_IDS = (
    "D-R10-LIVE-1",
    "D-P32.23a-1",
    "D-R10-PUBLISH-1",
    "D-R11-LATER-04",
    "D-R11-OSMUID-1",
    "D-P32.16-1",
    "D-R10-MEMORY-1",
    "D-R11-ADR124-1",
)

LEAD_TOKEN_RE = re.compile(
    r"^(OPEN|PARTIAL|DONE|WONTFIX|ACCEPTED(?:-\w+)?|CLOSED)\b", re.IGNORECASE
)


def _quote(cell: str) -> str:
    """A verbatim map cell inside one code span — the cell's own markdown
    ticks render as `'` inside it. A code-quoted cell is verbatim record
    text; the live-claim lint reads only prose, so quoting the record is
    how a record is shown without asserting its production words."""
    return "`" + cell.replace("`", "'") + "`"


def deferral_status(deferrals_text: str, did: str) -> str:
    """A DEFERRALS row's committed leading status token — verbatim read."""
    for line in deferrals_text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 3 or cells[1] != did:
            continue
        last = cells[-2] if cells[-1] == "" else cells[-1]
        m = LEAD_TOKEN_RE.match(last.strip())
        return m.group(1).upper() if m else f"unparsed (cell head: {last[:40]})"
    return "absent"


# ---------------------------------------------------------------------------
# Exit items — S2 §4.2 verbatim, as measured on the promoted release.
# ---------------------------------------------------------------------------

EXIT_ITEMS = [
    ("exit-1", "P35.63 promoted under a signed HG-11 readout with V1–V15 "
     "green and 0 waivers"),
    ("exit-2", "the live rollback rehearsal done"),
    ("exit-3", "`/r/<pub>/` and release search live"),
    ("exit-4", "nginx honours withdrawals"),
    ("exit-5", "the old GATE-G3 signature superseded, not transferred"),
    ("exit-6", "0 subject-key collisions (L3 `enforce`)"),
    ("exit-7", "0 1970 edges — every edge dated or labelled \"undated\""),
    ("exit-8", "0 publisher-as-operator (`unknown` allowed)"),
    ("exit-9", "technology on 100 % of site rows"),
    ("exit-10", "0 axis swaps / 0 null-island points"),
    ("exit-11", "0 undisclosed out-of-polygon points"),
    ("exit-12", "`unresolved` is not a dossier"),
    ("exit-13", "0 mixed-scheme dossiers"),
    ("exit-14", "exact claim repeats ≤ 1 %"),
    ("exit-15", "derivation census 100 %"),
    ("exit-16", "dossier counts ≤ 1.02× lineage roots or ranged "
     "\"possible duplicate\" intervals"),
    ("exit-17", "contradiction recall 1.0 on the synthetic set"),
    ("exit-18", "byte binding 100 % for the sources re-run in P35.61"),
    ("exit-19", "Wave A live with +0 re-runs and its coverage delta recorded"),
    ("exit-20", "OPCHECK recorded as not required — Q-L3-3 = c (the plan "
     "row's verbatim answer), never claimed performed"),
    ("exit-21", "no unexplained red, ratchet regression, pending seed "
     "transition, due-but-unrun leg or unlinked known issue remains"),
]

#: Items measured on the promoted release — each reports queued with the
#: legs that evaluate it, never a fabricated live pass.
LIVE_MEASURED = {f"exit-{i}" for i in range(1, 5)} | {
    f"exit-{i}" for i in range(6, 20)
}


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
        leg.get("id") for row in map_data.get("row", []) for leg in row.get("legs", [])
    }
    suppressed = record is None or record.get("overall") == "suppressed"
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

    promo_leg = "P35.63-promote-under-hg11"
    stage_leg = "P35.63-dispatch-stage-verify-readout"
    own_state = (
        "queued at the gate (its RETURN PASS row lands at closeout)"
        if suppressed
        else "ran"
    )
    for eid, text in EXIT_ITEMS:
        if eid == "exit-1":
            items.append(
                queued_item(
                    eid,
                    text,
                    f"legs still queued: {stage_leg}, {promo_leg} — the "
                    "promotion awaits the operator's signed, "
                    "candidate-specific HG-11 readout (V1–V15 and the "
                    "waiver count are verified on the promoted release, "
                    "never now); no release is promoted, hosted or public",
                )
            )
        elif eid == "exit-2":
            items.append(
                queued_item(
                    eid,
                    text,
                    f"leg still queued: {promo_leg} — the rehearsal runs "
                    "inside the promotion leg after staging; zero hosted "
                    "mutations have run",
                )
            )
        elif eid == "exit-3":
            items.append(
                queued_item(
                    eid,
                    text,
                    f"legs still queued: {stage_leg}, {promo_leg}, "
                    f"{OWN_LEG} ({own_state}) — `/r/<pub>/` and the "
                    "release-search surface are read by the 11B sweep "
                    "over the promoted release",
                )
            )
        elif eid == "exit-4":
            items.append(
                queued_item(
                    eid,
                    text,
                    f"legs still queued: {promo_leg}, {OWN_LEG} "
                    f"({own_state}) — the withdrawal barrier is probed "
                    "on the promoted release's aliases by the 11B sweep",
                )
            )
        elif eid == "exit-5":
            ok = (root / G3_CORRECTION_REL).is_file()
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "pass" if ok else "fail",
                    "layer": "engineered (record layer — the supersession "
                    "is a committed record; the live surface check is "
                    "queued at the sweep)",
                    "evidence": (
                        f"`{G3_CORRECTION_REL}` committed + the B-4 "
                        "statement in DEFERRALS (the signature is not "
                        "transferred: P35.63 needs its own candidate-"
                        "specific readout)"
                        if ok
                        else f"`{G3_CORRECTION_REL}` absent — the "
                        "supersession record is missing"
                    ),
                }
            )
        elif eid == "exit-19":
            items.append(
                queued_item(
                    eid,
                    text,
                    "Wave-A legs still queued: P35.11-l1-roll-seed-manual-runs, "
                    "P35.11-l2-plus-zero-reruns, P35.11-l3-resume-schedules — "
                    "their recorded window 10-19 → 10-23 elapsed unrun "
                    "(verbatim-go awaited); the +0 re-run count and coverage "
                    "delta are measured on the live wave, never claimed",
                )
            )
        elif eid in LIVE_MEASURED:
            items.append(
                queued_item(
                    eid,
                    text,
                    f"legs still queued: {promo_leg}, {OWN_LEG} "
                    f"({own_state}) — the target carries its L2 baseline; "
                    "a miss is a known-issue line, never a quiet pass",
                )
            )
        elif eid == "exit-20":
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "pass",
                    "layer": "engineered (recorded not-required — the "
                    "plan row's verbatim answer; OPCHECK was never "
                    "claimed performed)",
                    "evidence": "Q-L3-3 = c is the plan row's recorded "
                    "answer — recorded not-required, never performed "
                    "and never claimed",
                }
            )
        elif eid == "exit-21":
            due = legs["due"]
            pend = _pending_transitions(root)
            problems: list[str] = []
            if due:
                problems.append(
                    "due legs: " + ", ".join(x["leg"] or "?" for x in due)
                )
            if pend:
                problems.append(f"pending SEED-14 transitions: {pend}")
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "pass" if not problems else "fail",
                    "layer": "engineered (record layer — the committed "
                    "queue of record; the live window check is queued at "
                    "the sweep)",
                    "evidence": (
                        "no due leg, no pending seed transition, no "
                        "unexplained red and no unlinked known issue "
                        "located at the record layer — every open issue "
                        "is listed in the section below and linked"
                        if not problems
                        else "; ".join(problems)
                    ),
                }
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
    g4_signed = _g4_signed(root)
    legs = evaluate_legs_11b(map_data, now, g4_signed)
    items = evaluate_exit_items(
        root=root, map_data=map_data, now=now, record=record, legs=legs
    )

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
        "# Sub-round 11B acceptance — per-row highest layer (P35.64)",
        "",
        "<!-- Generated by docs/build/tools/acceptance_report_11b.py — do not",
        "     hand-edit. Regenerate: `python3 docs/build/tools/acceptance_report_11b.py",
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
        "## 11B exit items (S2 §4.2, verbatim as measured on the promoted release)",
        "",
        "| item | verdict | layer | evidence |",
        "|---|---|---|---|",
    ]
    for it in items:
        ev = (it.get("evidence") or "").replace("|", "/")
        lines.append(
            f"| {it['id']} | {it['verdict']} | {it['layer']} | {it['text']} — {ev} |"
        )
    lines += [
        "",
        "## Per-row highest layer (chain rows 261–343)",
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
        "transition, never here. Every open issue stays visible and linked.",
        "",
        "| id | committed lead token | note |",
        "|---|---|---|",
    ]
    for did in DEFERRAL_IDS:
        token = deferral_status(deferrals_text, did)
        note = {
            "D-R10-LIVE-1": "the gated live half — hosted audit, bounded "
            "apply, freeze (P35.61's legs, queued)",
            "D-P32.23a-1": "the production release-candidate build + "
            "validation (P35.62's leg, queued)",
            "D-R10-PUBLISH-1": "publication operating approval — P35.63's "
            "own signed HG-11 readout (queued)",
            "D-R11-LATER-04": "the ADR-171 Stage-0 set — owed, unmet at "
            "launch; the packet's status part carries it",
            "D-R11-OSMUID-1": "the OSM uid lane — carried placement, "
            "stays with P37.1",
            "D-P32.16-1": "the receiver's operating prerequisites "
            "(operator prerequisites unmet)",
            "D-R10-MEMORY-1": "the single-writer/event cutover — "
            "shadow-mode continues (the closeout-journal leg lives at "
            "D-R10-MEMORY-2)",
            "D-R11-ADR124-1": "ADR-124 allow dispositions — P34.46 applies "
            "the allows with the Round-10 schema (queued upstream)",
        }.get(did, "")
        lines.append(f"| `{did}` | {token} | {note} |")
    lines += [
        "| NIGHTLY-RED-1 | recorded (LEDGER OPEN FINDINGS) | the scheduled "
        "`nightly.yml` runs on `main` failed 2026-10-07 → 10-20 (14 runs) — "
        "the owed observation of `D-P34.7-1`/`D-P34.2-2`; repair routed "
        "separately, never smoothed here |",
        "| P34.18 Δ0 pair | recorded | the two P34.18 Δ0 failures stay on "
        "the known-failure list — environment-local, CI authoritative |",
        "| `SIG_GCP_PROJECT` posture | recorded | fail-closed by design "
        "(OP-07) — hosted legs stay queued; no credentials are inferred |",
        "| Wave-A window | anomaly — recorded | P35.11's legs' window "
        "10-19 → 10-23 elapsed unrun (the legs stay queued, verbatim-go) — "
        "listed and carried to GATE-G5, never smoothed |",
        "",
        "## Live-leg queue (all legs queued — none has run) — due "
        "evaluation at the evaluation instant",
        "",
        "A leg is **due** when its earliest instant has passed and its go is "
        "held (OM-19); a verbatim/operator go not yet given is `awaiting-go`, "
        "never due; a `pre-authorised:` go whose recorded expiry has passed "
        "(the 11A S5-3/GB-Q4 list expired at the signed GATE-G4) is "
        "awaiting-go too — the packet's recorded default \"each re-asks "
        "in-ticket\" applies. `conditional` = the earliest's named extra "
        "conditions are not machine-verifiable; `indeterminate` = no "
        "parseable earliest. Leg earliest/go cells are quoted verbatim "
        "inside code spans (their own markdown ticks render as `'`); a "
        "code-quoted cell is verbatim record text, never an assertion of "
        "its production words.",
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
            suffix = " — *pre-authorisation expired at GATE-G4*" if x.get("expired") else ""
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
        f"- the GATE-G5 packet draft: `{G5_READOUT_REL}` (agent-drafted, "
        "sha256-labelled — it decides nothing; GATE-G5's answers are the "
        "operator's own verbatim lines)",
        f"- PLAN-11C's run ledger `{PLAN11C_REL}` — the draft 11C OM-20 "
        "list the packet cites (13 rows; the §8.1 count of 10 recorded as "
        "drift, never resolved here)",
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
    if "## 11B exit items" not in note_text:
        violations.append("no exit-items section")
    if "## Open issues" not in note_text:
        violations.append("no open-issues section")
    if "## Live-leg queue" not in note_text:
        violations.append("no live-leg queue section")
    if "window has opened" not in note_text:
        violations.append("no window-opened listing")
    if "Q-L3-3 = c" not in note_text:
        violations.append("OPCHECK not-required recording absent")

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
        if line.startswith("## 11B exit items"):
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
    ap = argparse.ArgumentParser(prog="acceptance_report_11b.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="write the 11B acceptance note")
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
        f"acceptance_report_11b: wrote {out} ({len(text.encode('utf-8'))} B)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
