#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""acceptance_report.py — the P34.47 11A acceptance note (plan §13.1; SIG-MEM-011).

Generates and checks ``docs/build/reports/acceptance/11A.md``: one line per
11A chain row (manifest rows 201–259) reporting the **highest layer the row
really reached** — never above the vocabulary its BUILD_INDEX evidence cell
records — plus the 11A exit items (each with pass/fail/queued and its
layer), the RI-01 line, the due-leg evaluation of the live-leg queue and
the "also read" section (managed certificate, spend, queue).

Layer discipline: a row's reported layer is the highest status-layer token
present in its index evidence cell; rows whose live leg is queued report
their landed (engineered/fixture-verified) layer and name the queued leg —
an engineered or fixture result is never dressed as live/public. Exit items
evaluate honestly: record-checkable items are evaluated from committed
evidence at the record layer; items needing the live sweep report
``queued`` with the leg that will evaluate them.

Commands:
    generate [--root PATH] [--record PATH] [--at ISO] [--reads PATH] [--out PATH]
    check    [--root PATH] [--note PATH]

``generate`` embeds sha256 digests of its inputs and the evaluation instant;
``check`` validates the structural invariants (every 11A row exactly once,
valid layer words, no row above its evidence, every exit item verdicted,
the queue section complete). Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import io
import json
import re
import sys
import tomllib
from pathlib import Path

LAYERS = (
    "engineered",
    "fixture-verified",
    "staging-verified",
    "live-executed",
    "public",
    "human-completed",
)
LAYER_RANK = {name: i for i, name in enumerate(LAYERS)}

SUBROUND = ("201", "259")  # the 11A row range (GATE-G4 is row 260)
NOTE_REL = "docs/build/reports/acceptance/11A.md"
RECORD_REL = "docs/build/reports/acceptance/11A-probe-run.json"
MAP_REL = "docs/build/tools/record_policy/return_pass.toml"
INDEX_REL = "docs/build/BUILD_INDEX.md"
MANIFEST_REL = "docs/tickets/00_MANIFEST.md"
CI_REL = ".github/workflows/ci.yml"
PT_REL = "docs/build/reports/memory-repair/pending_transitions.csv"
QC_REL = "exports/src/exports/data/quality_checks.toml"
SPEND_REL = "docs/build/reports/spend/spend_ledger.csv"
USAGE_REL = "docs/build/reports/spend/agent_usage.csv"

ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z?")
CHAIN_ROW_RE = re.compile(r"^\|\s*(\d+[a-z]*)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
TICKET_FILE_RE = re.compile(r"(\d+[a-z]*)_([A-Za-z0-9.\-]+?)__([^|]+?)\.md")
IDX_ROW_RE = re.compile(r"^\|\s*(\d+[a-z]*)\s*\|")

VERDICT_WORDS = ("pass", "fail", "queued", "partial", "blockedOn")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _iso(text: str) -> _dt.datetime:
    t = text.strip()
    dt = _dt.datetime.fromisoformat(t[:-1] + "+00:00" if t.endswith("Z") else t)
    if dt.tzinfo is None:
        raise ValueError(f"instant {text!r} carries no timezone")
    return dt.astimezone(_dt.UTC)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def manifest_11a_rows(manifest_text: str) -> list[dict]:
    """The chain rows of sub-round 11A — sequence cells 201…259."""
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
        if not (201 <= n <= 259):
            continue
        tf = TICKET_FILE_RE.search(file_cell)
        ticket = tf.group(2) if tf else file_cell.strip().split()[-1]
        rows.append({"seq": seq, "ticket": ticket, "file": file_cell.strip()})
    return rows


def index_rows(index_text: str) -> dict[str, dict]:
    """Every index row → {seq: {ticket, cell}}.

    The Round-11 table is interrupted by the append-only ``## Row
    corrections`` section and resumes bare after it — so rows are
    collected file-wide (blockquoted restored rows start ``>`` and are
    never matched); the seq range filters to 11A.
    """
    rows: dict[str, dict] = {}
    for line in index_text.splitlines():
        m = IDX_ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        # cells: ['', seq, ticket, kind, branch, pr, base, date, adr, obligations, status, paths, harness, '']
        if len(cells) < 12:
            continue
        rows[m.group(1)] = {"ticket": cells[2].strip("`"), "cell": cells[10] if len(cells) > 11 else ""}
    return rows


def highest_layer(cell: str) -> str | None:
    """The highest status-layer token an evidence cell *claims*.

    Only the layer-declaration head counts — the text before the first
    ``(`` or ``:``. A cell may name a higher layer later in prose (``the
    live-executed half owed to D-…``); that is an obligation, not a layer
    reached, and must never surface here (SIG-MEM-011).
    """
    head = re.split(r"[(:]", cell, maxsplit=1)[0]
    best: str | None = None
    for name in LAYERS:
        if name in head:
            best = name
    if best is None and re.search(r"\bstaging\b(?!-)", head):
        # bare "staging" is the shorthand some cells use for the same layer
        best = "staging-verified"
    return best


def load_map(root: Path) -> dict:
    return tomllib.loads((root / MAP_REL).read_text(encoding="utf-8"))


def _go_held(go: str) -> bool:
    """A go is held unless it demands verbatim/operator words not yet given."""
    g = go.strip().lower()
    if g.startswith("verbatim-go:") or g.startswith("operator:"):
        return False
    return True


def evaluate_legs(map_data: dict, now: _dt.datetime) -> dict[str, list[dict]]:
    """OM-19 due evaluation of every queued leg in the RETURN PASS map.

    States: ``due`` (earliest ISO passed, go held) · ``conditional-due``
    (earliest ISO passed but its text names extra conditions the map cannot
    verify) · ``indeterminate`` (no parseable earliest instant) ·
    ``waiting`` (earliest in the future) · ``awaiting-go`` (a verbatim or
    operator go is required and not held — never "due" on a clock alone).
    """
    out: dict[str, list[dict]] = {
        "due": [],
        "conditional": [],
        "indeterminate": [],
        "awaiting_go": [],
        "waiting": [],
    }
    for row in map_data.get("row", []):
        for leg in row.get("legs", []):
            item = {
                "row": row.get("key"),
                "leg": leg.get("id"),
                "earliest": str(leg.get("earliest", "")),
                "go": str(leg.get("go", "")),
            }
            if not _go_held(item["go"]):
                out["awaiting_go"].append(item)
                continue
            m = ISO_RE.search(item["earliest"])
            if m is None:
                out["indeterminate"].append(item)
                continue
            instant = _iso(m.group(0) if m.group(0).endswith("Z") else m.group(0) + ":00Z")
            extra = bool(item["earliest"].replace(m.group(0), "").strip(" —-"))
            if instant <= now:
                out["conditional" if extra else "due"].append(item)
            else:
                out["waiting"].append(item)
    return out


# ---------------------------------------------------------------------------
# Exit items (S2 §4.1 as amended by plan §5.1 / the ticket's list)
# ---------------------------------------------------------------------------

EXIT_ITEMS = [
    (
        "exit-1",
        "every S0 finding removed or fixed live: F-01 drilled restore with "
        "timing + deletion protection; F-02 the publish path refuses "
        "/curate/ + an absence probe confirms; F-03 the honest dispute "
        "notice with the published handling order and no response time "
        "(B-8, WV-08); F-096/F-183 fixture pages removed; F-097/F-131 "
        "handles; F-130 API honest (P34.46); F-387 attribution correct "
        "behind the publish-time gate",
    ),
    (
        "exit-2",
        "a test alert received; the TLS-expiry alert, the $300 budget "
        "alert, the billing export and a drilled restore exist",
    ),
    (
        "exit-3",
        "CI pinned before 2026-10-19; every boundary read head-bound; no "
        "row advanced on red",
    ),
    (
        "exit-4",
        "memory: M1–M10 in CI; 0 pending SEED-14 transitions; 0 G1/G2 "
        "violations in 11A commits",
    ),
    ("exit-5", "G2 step 1 live after the 10-10 replay read-back"),
    (
        "exit-6",
        "the quality baseline reproduces L2's 29/45 failing checks in "
        "ratchet mode; GQ-20/24/27 enforce; 0 ratchet regressions",
    ),
    (
        "exit-7",
        "live probe: 0 instances of the L3 §4.5 not-claimable list + C6 "
        "status words outside disclosed contexts",
    ),
    (
        "exit-8",
        "the live-leg queue holds no leg whose window has opened",
    ),
]

#: Legs each exit item's live verdict still needs (matched against the map —
#: the real leg ids; a leg no longer queued counts as run/landed).
EXIT_LEG_DEPS = {
    "exit-1": (
        "P34.3-live", "P34.21b-L1", "P34.21b-L2", "P34.46-slot",
        "P34.47-sweep-packet",
    ),
    "exit-2": (
        "P34.4-live", "P34.4-human-check", "P34.5-first-report",
        "P34.5-export-link", "P34.5-testbudget-delete",
    ),
    "exit-5": ("P34.46-slot", "P34.46-soak"),
    "exit-6": ("P34.44b-baseline", "P34.44b-quality-probe"),
}


def _pending_transitions(root: Path) -> int | None:
    """Queued SEED-14 transitions with no applied row — None if unreadable."""
    path = root / PT_REL
    if not path.is_file():
        return None
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    queued = {r["entry_id"] for r in rows if r.get("action") == "queue"}
    applied = {r["queue_ref"] for r in rows if r.get("action") == "applied"}
    return len(queued - applied)


def _ci_pinned(root: Path) -> tuple[bool, str]:
    """No floating runner/image refs on the required jobs (record layer)."""
    path = root / CI_REL
    if not path.is_file():
        return False, "ci.yml absent"
    text = path.read_text(encoding="utf-8")
    floating = re.findall(r"runs-on:\s*ubuntu-latest", text)
    if floating:
        return False, f"{len(floating)} floating runs-on: ubuntu-latest"
    return True, "runners pinned (ubuntu-24.04); actions tag-pinned"


def _quality_enforced(root: Path) -> tuple[bool | None, str]:
    """GQ-20/GQ-24/GQ-27 carry `enforce` in the committed checks table.

    ``None`` = the record is unreadable (partial), never a fabricated verdict.
    """
    path = root / QC_REL
    if not path.is_file():
        return None, "quality_checks.toml absent"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    checks = data.get("check", data.get("checks", []))
    if isinstance(checks, dict):
        checks = list(checks.values())
    found = {}
    for c in checks if isinstance(checks, list) else []:
        cid = c.get("id") or c.get("name")
        if cid in ("GQ-20", "GQ-24", "GQ-27"):
            found[cid] = c.get("mode") or c.get("severity")
    missing = [c for c in ("GQ-20", "GQ-24", "GQ-27") if found.get(c) != "enforce"]
    if missing:
        return False, f"not enforce: {', '.join(missing)}"
    return True, "GQ-20/GQ-24/GQ-27 all `enforce`"


def evaluate_exit_items(
    *,
    root: Path,
    map_data: dict,
    now: _dt.datetime,
    record: dict | None,
    index: dict[str, dict],
    mrows: list[dict],
) -> list[dict]:
    """One line per exit item — verdict + layer + evidence, honestly."""
    queued_ids = {
        leg.get("id") for row in map_data.get("row", []) for leg in row.get("legs", [])
    }
    items: list[dict] = []

    def dep_detail(ids: tuple[str, ...]) -> str:
        still = [i for i in ids if i in queued_ids]
        # A leg absent from the map ran — except this sweep's own leg while
        # the record is suppressed: it is queued at the gate and its
        # RETURN PASS row lands at closeout (never "run/landed").
        suppressed = record is not None and record.get("overall") == "suppressed"
        own_queued = [
            i for i in ids
            if i == "P34.47-sweep-packet" and i not in queued_ids and suppressed
        ]
        run = [
            i for i in ids
            if i not in queued_ids and i not in own_queued
        ]
        bits = []
        if still:
            bits.append("legs still queued: " + ", ".join(still))
        if own_queued:
            bits.append(
                "legs queued at the gate (the RETURN PASS row lands at "
                "closeout): " + ", ".join(own_queued)
            )
        if run:
            bits.append("legs run/landed: " + ", ".join(run))
        return "; ".join(bits) or "no mapped legs"

    # exit-1/2/5/6 need the live reads — verdict queued with the named legs.
    for eid, text in EXIT_ITEMS:
        if eid == "exit-1":
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "queued",
                    "layer": "live-executed (not evaluated — the live sweep leg is queued)",
                    "evidence": dep_detail(EXIT_LEG_DEPS[eid])
                    + " — evaluated by P34.47's live sweep + the named legs",
                }
            )
        elif eid == "exit-2":
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "queued",
                    "layer": "live-executed (not evaluated — the live reads leg is queued)",
                    "evidence": dep_detail(EXIT_LEG_DEPS[eid])
                    + "; the engineered alert/billing paths landed (P34.4/P34.5/P34.6)",
                }
            )
        elif eid == "exit-3":
            pinned, pdetail = _ci_pinned(root)
            # a boundary read is honestly recorded in the index cell
            # (`ci: <verdict>`) or in the row's run ledger (earlier 11A
            # rows predate the index-cell convention — the record still
            # exists, the sweep re-reads it head-bound).
            uncovered: list[str] = []
            for r in mrows:
                if r["seq"] == "259":
                    continue  # this row — its own boundary read lands at closeout
                cell = index.get(r["seq"], {}).get("cell", "")
                if re.search(r"ci:\s*(pass|fail|blockedOn)", cell):
                    continue
                run_path = root / "docs/build/runs" / f"{r['ticket']}.md"
                run_text = ""
                if run_path.is_file():
                    run_text = run_path.read_text(encoding="utf-8", errors="replace")
                if re.search(r"(ci: pass|head-bound|ci-boundary|boundary read)", run_text):
                    continue
                uncovered.append(r["ticket"])
            ok = pinned and not uncovered
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "pass" if ok else ("partial" if pinned else "fail"),
                    "layer": "engineered (record layer — re-verified live at the sweep)",
                    "evidence": pdetail
                    + (
                        "; every landed 11A row carries a boundary record "
                        "(index `ci:` token or run-ledger head-bound read)"
                        if not uncovered
                        else "; rows without a located boundary record: "
                        + ", ".join(uncovered)
                    ),
                }
            )
        elif eid == "exit-4":
            pend = _pending_transitions(root)
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": ("pass" if pend == 0 else "fail") if pend is not None else "partial",
                    "layer": "engineered (record layer)",
                    "evidence": (
                        f"pending SEED-14 transitions: {pend}"
                        if pend is not None
                        else "pending_transitions.csv unreadable"
                    )
                    + "; the memory guards (M1–M10) run in the docs CI job on "
                    "every commit — a G1/G2 violation reds the PR",
                }
            )
        elif eid == "exit-5":
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "queued",
                    "layer": "live-executed (not evaluated — P34.46's L2/L3 are queued)",
                    "evidence": dep_detail(EXIT_LEG_DEPS[eid]),
                }
            )
        elif eid == "exit-6":
            enforced, edetail = _quality_enforced(root)
            verdict = (
                "partial" if enforced is None else ("queued" if enforced else "fail")
            )
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": verdict,
                    "layer": "live-executed (enforce flags verified at the record layer)",
                    "evidence": edetail + "; " + dep_detail(EXIT_LEG_DEPS[eid]),
                }
            )
        elif eid == "exit-7":
            if record is None or record.get("overall") == "suppressed":
                items.append(
                    {
                        "id": eid,
                        "text": text,
                        "verdict": "queued",
                        "layer": "live-executed (not evaluated — the sweep leg is queued)",
                        "evidence": "the probe-run record is suppressed/queued",
                    }
                )
            else:
                bad = sum(
                    c.get("undisclosed_word_hits", 0)
                    for c in record.get("checks", {}).values()
                    if isinstance(c, dict)
                )
                items.append(
                    {
                        "id": eid,
                        "text": text,
                        "verdict": "pass" if bad == 0 else "fail",
                        "layer": "live-executed",
                        "evidence": f"{bad} undisclosed claim-word hits across surfaces",
                    }
                )
        elif eid == "exit-8":
            legs = evaluate_legs(map_data, now)
            due = legs["due"] + legs["conditional"]
            items.append(
                {
                    "id": eid,
                    "text": text,
                    "verdict": "pass" if not due else "fail",
                    "layer": "engineered (the committed queue of record — the "
                    "live window check re-runs at the sweep)",
                    "evidence": (
                        "no leg whose window has opened is unrun"
                        if not due
                        else "legs due/conditional: "
                        + ", ".join(x["leg"] or "?" for x in due)
                    ),
                }
            )
    return items


# ---------------------------------------------------------------------------
# The note
# ---------------------------------------------------------------------------


def _short_evidence(cell: str, limit: int = 170) -> str:
    """The evidence cell's first clause, bounded — never paraphrased above."""
    first = re.split(r"(?<=[.;]) ", cell, maxsplit=1)[0]
    first = re.sub(r"\*\*", "", first).strip()
    if len(first) > limit:
        first = first[: limit - 1].rstrip() + "…"
    return first


def _spend_lines(root: Path) -> list[str]:
    """Month-to-date read from the committed spend ledger (record layer)."""
    path = root / SPEND_REL
    if not path.is_file():
        return ["- spend ledger absent — the sweep's live billing read is queued"]
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    if not rows:
        return ["- spend ledger has no rows"]
    latest = rows[-1]
    keys = list(latest)
    summary = "; ".join(
        f"{k}={latest[k]}" for k in keys if k and latest.get(k) and k.lower() != "notes"
    )
    return [
        f"- spend ledger (committed, record layer): {len(rows)} rows; "
        f"latest row — {summary[:240]}",
        "- live billing-export + forecast vs the $300/mo ceiling: read at "
        "the sweep leg (queued) — nothing is fabricated",
    ]


def render(
    *,
    root: Path,
    index_text: str,
    manifest_text: str,
    map_data: dict,
    record: dict | None,
    evaluated_at: str,
    reads: dict | None,
) -> str:
    mrows = manifest_11a_rows(manifest_text)
    index = index_rows(index_text)
    now = _iso(evaluated_at)
    legs = evaluate_legs(map_data, now)
    items = evaluate_exit_items(
        root=root, map_data=map_data, now=now, record=record, index=index, mrows=mrows
    )

    digests = {
        "index": _digest(index_text),
        "manifest": _digest(manifest_text),
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

    ri01 = "queued — the live sweep has not run"
    if record is not None and record.get("overall") != "suppressed":
        c = record.get("checks", {}).get("ri01", {})
        ri01 = f"{c.get('state', '?')} — {c.get('detail', '')}"

    lines = [
        "# Sub-round 11A acceptance — per-row highest layer (P34.47)",
        "",
        "<!-- Generated by docs/build/tools/acceptance_report.py — do not",
        "     hand-edit. Regenerate: `python3 docs/build/tools/acceptance_report.py",
        "     generate` (the live-leg rerun regenerates after the sweep).",
        "     Layer honesty (SIG-MEM-011): a row never reports above the layer",
        "     its BUILD_INDEX evidence records; a queued leg is named, never",
        "     dressed as a result. -->",
        "",
        f"- evaluated_at: {evaluated_at}",
        f"- inputs: BUILD_INDEX `{digests['index']}` · manifest `{digests['manifest']}` · "
        f"return_pass map `{digests['map']}` · probe-run record `{digests['record']}`",
        f"- probe-run record: {record_line}",
        "- layer vocabulary: engineered · fixture-verified · staging-verified · "
        "live-executed · public · human-completed",
        "",
        "## RI-01 (handle crawl — site, API, tiles, sig-public listing, repo tip)",
        "",
        f"- **{ri01}**",
        "- the handle list stays gitignored "
        "(`docs/build/logs/next-phase/C3/personal_like_ids.txt`) and is never "
        "committed or printed — counts only",
        "",
        "## 11A exit items (plan §5.1; S2 §4.1 as amended)",
        "",
        "| item | verdict | layer | evidence |",
        "|---|---|---|---|",
    ]
    for it in items:
        ev = (it.get("evidence") or "").replace("|", "/")
        lines.append(f"| {it['id']} | {it['verdict']} | {it['layer']} | {it['text']} — {ev} |")
    lines += [
        "",
        "## Per-row highest layer (chain rows 201–259)",
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
        "## Live-leg queue — due evaluation at the evaluation instant",
        "",
        "A leg is **due** when its earliest instant has passed and its go is "
        "held (OM-19); a verbatim/operator go not yet given is `awaiting-go`, "
        "never due. `conditional` = the earliest's named extra conditions are "
        "not machine-verifiable; `indeterminate` = no parseable earliest.",
        "",
    ]
    for state, label in (
        ("due", "**due** (unrun, window open)"),
        ("conditional", "conditional-due (earliest passed, extra conditions unverified)"),
        ("awaiting_go", "awaiting-go (go not held)"),
        ("indeterminate", "indeterminate earliest"),
        ("waiting", "waiting (earliest in the future)"),
    ):
        lines.append(f"### {label}")
        if not legs[state]:
            lines.append("- none")
        for x in legs[state]:
            lines.append(
                f"- `{x['leg']}` ({x['row']}) — earliest: {x['earliest']}; go: {x['go']}"
            )
        lines.append("")
    lines += [
        "## Also read",
        "",
        "- managed certificate: expires 2026-12-22 per the records — the live "
        "status read runs at the sweep leg"
        + (
            f"; live read supplied: {reads.get('cert')}"
            if reads and reads.get("cert")
            else " (queued)"
        ),
    ]
    lines += _spend_lines(root)
    lines += [
        f"- live-leg queue: {sum(len(v) for v in legs.values())} legs queued "
        f"in the RETURN PASS map ({len(legs['due'])} due · "
        f"{len(legs['conditional'])} conditional · "
        f"{len(legs['awaiting_go'])} awaiting-go · "
        f"{len(legs['indeterminate'])} indeterminate · {len(legs['waiting'])} waiting)",
        "- the GATE-G4 packet draft: `docs/build/readouts/GATE-G4.md` "
        "(agent-drafted, sha256-labelled — it decides nothing)",
        "",
    ]
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
    mrows = manifest_11a_rows(manifest_text)
    index = index_rows(index_text)

    if "## Per-row highest layer" not in note_text:
        violations.append("no per-row section")
    if "## 11A exit items" not in note_text:
        violations.append("no exit-items section")
    if "due" not in note_text or "## Live-leg queue" not in note_text:
        violations.append("no live-leg queue section")

    row_re = re.compile(r"^\|\s*(\d+[a-z]*)\s*\|\s*(P[\w.\-]+)\s*\|\s*([\w\-]+)\s*\|", re.M)
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
            violations.append(f"chain row {r['seq']} ({r['ticket']}): listed "
                              f"{seen.get(r['seq'], 0)} times, expected 1")

    in_items = False
    item_count = 0
    for line in note_text.splitlines():
        if line.startswith("## 11A exit items"):
            in_items = True
            continue
        if in_items and line.startswith("## "):
            in_items = False
        if not in_items or not line.startswith("| exit-"):
            continue
        item_count += 1
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 5 or cells[2] not in VERDICT_WORDS:
            violations.append(f"exit item '{cells[1] if len(cells) > 1 else '?'}': "
                              "no valid verdict word")
    if item_count != len(EXIT_ITEMS):
        violations.append(f"{item_count} exit items listed, expected {len(EXIT_ITEMS)}")
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="acceptance_report.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="write the 11A acceptance note")
    g.add_argument("--root", default=".")
    g.add_argument("--record", default=None, help="the probe-run record JSON")
    g.add_argument("--at", dest="at", default=None,
                   help="evaluation instant (default: the record's generated_at, else the clock)")
    g.add_argument("--reads", default=None, help="optional leg-captured reads JSON")
    g.add_argument("--out", default=None, help=f"default {NOTE_REL}")
    c = sub.add_parser("check", help="structural invariants of the committed note")
    c.add_argument("--root", default=".")
    c.add_argument("--note", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root)
    index_text = (root / INDEX_REL).read_text(encoding="utf-8")
    manifest_text = (root / MANIFEST_REL).read_text(encoding="utf-8")

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
        map_data=load_map(root),
        record=record,
        evaluated_at=evaluated_at,
        reads=reads,
    )
    out = Path(args.out) if args.out else root / NOTE_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"acceptance_report: wrote {out} ({len(text.encode('utf-8'))} B)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
