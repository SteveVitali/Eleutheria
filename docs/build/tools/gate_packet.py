#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""gate_packet.py — draft the GATE-G4 readout's agent packet (P34.47; S5-2).

Writes ``docs/build/readouts/GATE-G4.md`` per row 260's contract and the
readout template: the packet is agent-drafted, sha256-labelled, composed
*before* the operator answers (ADR-147; P34.28's authorship rules), every
line carries its non-action ``Default:``, and the lines ``continue`` can
answer are marked ``batch`` — the OM-20 list, rights, money and own-words
lines all need their own verbatim answer (S5-2, ADR-149 §6).

The drafter fills the computed facts from committed records: the spend
ledger month-to-date, the RETURN PASS queue (legs still queued, the 11A
S5-3 pre-authorisations expiring at this gate) and the acceptance note's
per-row status pointer. It signs nothing and decides nothing.

Commands: ``draft`` (write the readout) · ``check`` (structural invariants:
Status PENDING, sha256 re-computes over the agent-drafted block body, all
six parts present, every numbered line carries a Default marker).
Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import sys
import tomllib
from pathlib import Path

READOUT_REL = "docs/build/readouts/GATE-G4.md"
MAP_REL = "docs/build/tools/record_policy/return_pass.toml"
SPEND_REL = "docs/build/reports/spend/spend_ledger.csv"
USAGE_REL = "docs/build/reports/spend/agent_usage.csv"
NOTE_REL = "docs/build/reports/acceptance/11A.md"
TICKET_REL = "docs/tickets/260_GATE-G4__11a-check-in.md"

BEGIN = "<!-- agent-drafted:begin sha256={sha} -->"
END = "<!-- agent-drafted:end -->"

#: The 19 candidate 11B OM-20 rows + the never-list, verbatim from row 260.
OM20_CANDIDATES = (
    "P35.5, P35.1a, P35.14a, P35.15a, P35.15b, P35.1b, P35.16, P35.17, "
    "P35.22, P35.24, P35.25, P35.26, P35.27, P35.32, P35.41, P35.46, "
    "P35.53, P35.59, P35.62"
)
OM20_NEVER = (
    "P35.57, P35.11, P35.14b, P36.12, P35.61, P35.63 and every HG-03 flip "
    "(incl. P35.17's boundary flip)"
)

#: The Class R standing-go text adopted at GATE-P (B-9; sha256 e4e24975b854…).
CLASS_R_TEXT = (
    "Agents may promote a Class R release built from the same signed code "
    "whose diff stays within bounds (records −2%…+15%, no compartment "
    "<−5% or >+50%, no source loses >20%), with all checks green and no "
    "waivers; this go expires at the next sub-round gate or after 30 "
    "days, and is void on any ratchet regression, Part VIII screen change "
    "or new source."
)


def _spend_summary(root: Path) -> list[str]:
    path = root / SPEND_REL
    if not path.is_file():
        return ["spend ledger absent — the live billing read is queued"]
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    if not rows:
        return ["spend ledger has no rows"]
    latest = rows[-1]
    summary = "; ".join(
        f"{k}={v}" for k, v in latest.items() if k and v and k.lower() != "notes"
    )
    return [
        f"committed spend ledger ({len(rows)} rows): latest — "
        f"{summary[:300]}",
    ]


def _map_state(root: Path) -> tuple[list[str], list[str]]:
    """(queued leg ids, 11A S5-3 pre-authorised row ids)."""
    data = tomllib.loads((root / MAP_REL).read_text(encoding="utf-8"))
    legs: list[str] = []
    preauth: list[str] = []
    for row in data.get("row", []):
        for leg in row.get("legs", []):
            legs.append(f"{leg.get('id')} ({row.get('key')})")
            if "S5-3" in str(leg.get("go", "")) and row.get("key") not in preauth:
                preauth.append(str(row.get("key")))
    return legs, preauth


def packet_body(root: Path) -> str:
    """The agent-drafted packet — the six S5-2 parts, defaults first."""
    legs, preauth = _map_state(root)
    spend = _spend_summary(root)
    usage = root / USAGE_REL
    usage_line = (
        f"agent usage ledger: {usage.name} present ({len(usage.read_text(encoding='utf-8').splitlines()) - 1} rows) — reported, not capped (A-2b)"
        if usage.is_file()
        else "agent usage ledger absent"
    )

    return f"""\
**Agent-drafted GATE-G4 packet** — composed by P34.47 before the operator
answers; every default is non-action; ``continue`` answers **batch** lines
only; rights/money/OM-20/own-words lines each need a verbatim answer;
silence = pause (OM-18).

**1. Budget** — *(status lines: batch)*

- Infra month-to-date + forecast vs the $300/mo ceiling — **{'; '.join(spend)}**. *Default: none (status; information only).* **batch**
- {usage_line}. *Default: none.* **batch**
- Lines exceeding the ceiling needing a verbatim money answer: none identified at draft time. *Default: none.* **batch**

**2. Publication** — *(verbatim lines)*

- What 11A published: republish #1 and republish #2 — each under its own verbatim in-ticket go, quoted not re-asked; at draft time both legs remain queued (see the queue) — **nothing has republished yet**. *Default: none (status).* **batch**
- 11B plans P35.63 — the first model release under a signed HG-11 readout ("single maintainer, no second reviewer"; "no human check performed"), with its date window and new route families. *Default: none (status).* **batch**
- **P35.57 API-roll go** — its own verbatim line (a roll that changes a public route's response is never pre-authorised); P35.57 is an improvement, not a gate — the 11B structural spine writes do not wait for it (A-20 = a). *Default: P35.57 pauses in-ticket (non-action).*

**3. Rights** — *(verbatim lines)*

- **ING-GO-A** — Wave A legs 2026-10-19 → 10-23, 14:00–20:00Z (P35.11; future-ok: scheduled: the contract's Wave-A window instants) with the operator's Wave A HG-03 flip list (OP-26; flips are operator-executed — one OP-25-signed commit or a signed GATE DECISIONS row naming each source id). *Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them.*
- **ING-GO-B** — Wave B legs 10-26 → 11-05, one family a day (P36.12; future-ok: scheduled: the contract's Wave-B window) with the Wave B flip list (FEA-02). *Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false`.*
- A-7/B-32 Part VIII screen lanes due in 11B — disclosed, not asked (B-42's agent clear is disclosed, never asked). *Default: none.* **batch**
- Carried, not asked unless ready: E4-R6a BidNet (terms captured by P34.38; due at GATE-G6 at the latest, S6R-28). *Default: none.* **batch**

**4. The 11B OM-20 list** — *(an OM-20 line: approved only by its own verbatim line, never by `continue`)*

- Candidates (the 19 OM-20 rows of 11B, exact ids): {OM20_CANDIDATES} — each with its contract's mutation, restore point and rollback quoted by the PLAN-11B contracts (row 239); expiry: the next sub-round GATE (GATE-G5, or GATE-G4b if the re-split rule fires). *Default: nothing pre-authorised — each named mutation pauses in-ticket.*
- Never on any list: {OM20_NEVER}. *Default: none.* **batch**
- 11A legs whose S5-3 pre-authorisation expires at this gate unrun (from the RETURN PASS map at draft time): {('; '.join(sorted(preauth))) if preauth else 'none'} — re-listed by row id or left to an in-ticket go. *Default: each re-asks in-ticket.*

**5. Class R standing-go renewal (B-9)** — *(verbatim line; never renewed by `continue`)*

- The operator's adopted text (adopted 2026-10-01T04:35:53Z — retro: the B-9 answer record, planning RATIFICATION_LOG round 12 / decision catalog; sha256 `e4e24975b854…`): "{CLASS_R_TEXT}" — renewed verbatim or not; it expires at the next sub-round gate or after 30 days, whichever is first; void on any ratchet regression, Part VIII screen change or new source. *Default: it lapses → every release is Class S.*

**6. Status** — *(information only; batch)*

- Per-row layered status: `docs/build/reports/acceptance/11A.md` (P34.47's acceptance note; the live sweep is queued — see the note). *Default: none.* **batch**
- Live-leg queue at draft time ({len(legs)} legs): {'; '.join(legs)}. *Default: none.* **batch**
- CI incidents, anomalies, operator-side merges read from GitHub at the sitting. *Default: none.* **batch**
- Managed certificate expires 2026-12-22 (live status read at the sweep). *Default: none.* **batch**
- RI-01 and the isolation probe repeated at this GATE (plan §8.5). *Default: none.* **batch**
- B-2's notice allowance (N-1…N-7 by sha256) ends here — every later sentence needs per-text confirmation. *Default: none.* **batch**
- Whether PLAN-11B's sizing review fired the 11B re-split rule (>85 engineering rows or >75 runs → GATE-G4b at the Wave-B activation boundary, S6R-15). *Default: none.* **batch**
- For the record: the REVIEW-R11 → GATE-ANNOUNCE rule (fix rows appended after row 510 + a new GATE-ANNOUNCE row + row 510 `superseded-by(row <n>)`; S6-F3, S6R-19). *Default: none.* **batch**

**Carried questions (only if not already answered at GATE-B)** — *(verbatim lines)*

- OP-24 (the leg-runner backstop, "decide by GATE-G4"): launchd → headless Devin CLI (needs `devin auth login`), operator-run at window opens, or no backstop; first windows open ≥ 2026-10-13. *Default: no backstop recorded.*
- Whether fallback mode B (headless Devin) is verified (`devin auth login` + a live `--agent-cmd` run). *Default: reported as not verified.*
"""


def render_readout(packet: str) -> str:
    sha = hashlib.sha256(packet.encode("utf-8")).hexdigest()
    return f"""# GATE-G4 — pending readout

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/260_GATE-G4__11a-check-in.md`.
Decision domain: the 11A check-in — budget, publication, rights (ING-GO-A/B
+ flip lists), the 11B OM-20 list, the Class R standing-go renewal — and
nothing else; each line's default is non-action.

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] The packet presented is P34.47's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due.
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted.
- [ ] The 11B OM-20 list (if any) names exact row ids with expiry; the Class R renewal (if given) is quoted with its expiry; ING-GO-A/B and the flip lists are recorded as answered or defaulted.
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 261 only after the answer.

## Packet (agent-drafted)

{BEGIN.format(sha=sha)}
{packet}{END}

## Signature

<!-- Appended only at signing, by the commit that moves Status:. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | GATE-G4
Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:{sha[:12]}
Signed by: repository operator. Recorded by devin-desktop/swe-2-high/subagent, which does not sign.
"""


def check(text: str) -> list[str]:
    """Structural invariants of the committed readout."""
    v: list[str] = []
    if "Status: PENDING" not in text:
        v.append("Status: PENDING absent — a signed/edited readout fails")
    m = re.search(r"<!-- agent-drafted:begin sha256=([0-9a-f]{64}) -->\n(.*?)<!-- agent-drafted:end -->", text, re.S)
    if not m:
        v.append("agent-drafted block absent")
    else:
        body = m.group(2)
        actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if actual != m.group(1):
            v.append(f"agent-drafted sha256 mismatch: {m.group(1)[:12]} != {actual[:12]}")
        for part in ("1. Budget", "2. Publication", "3. Rights", "4. The 11B OM-20 list", "5. Class R", "6. Status"):
            if part not in body:
                v.append(f"packet part missing: {part}")
        bullets = [ln for ln in body.splitlines() if ln.startswith("- ")]
        for ln in bullets:
            if "Default:" not in ln:
                v.append(f"packet line lacks Default: {ln[:60]}")
        if "Agent-drafted" not in body:
            v.append("packet not labelled agent-drafted")
    if "an agent must not\nsign or assume silence is approval" not in text:
        v.append("guard sentence absent")
    return v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gate_packet.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="write the GATE-G4 readout draft")
    d.add_argument("--root", default=".")
    d.add_argument("--out", default=None)
    c = sub.add_parser("check", help="structural invariants of the committed readout")
    c.add_argument("--root", default=".")
    c.add_argument("--file", default=None)
    args = ap.parse_args(argv)
    root = Path(args.root)

    if args.cmd == "check":
        path = Path(args.file) if args.file else root / READOUT_REL
        if not path.is_file():
            print(f"check: {path} absent", file=sys.stderr)
            return 3
        violations = check(path.read_text(encoding="utf-8"))
        for x in violations:
            print(f"check: {x}", file=sys.stderr)
        print("check: ok" if not violations else f"check: {len(violations)} violations")
        return 0 if not violations else 1

    packet = packet_body(root)
    text = render_readout(packet)
    out = Path(args.out) if args.out else root / READOUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(packet.encode("utf-8")).hexdigest()
    print(f"gate_packet: drafted {out}; packet sha256 {sha}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
