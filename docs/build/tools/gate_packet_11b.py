#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""gate_packet_11b.py — draft the GATE-G5 readout's agent packet (P35.64;
S2 §3.6; contract docs/tickets/343_GATE-G5__11b-check-in.md).

Writes ``docs/build/readouts/GATE-G5.md`` per row 343's contract and the
readout template: the packet is agent-drafted, sha256-labelled, composed
*before* the operator answers (ADR-147; P34.28's authorship rules), every
line carries its non-action ``Default:``, and the lines ``continue`` can
answer are marked ``batch`` — the OM-20 list, rights, money and own-words
lines all need their own verbatim answer (S5-2, ADR-149 §6). Silence is
never consent (OM-18).

The drafter fills the computed facts from committed records: the spend
ledger month-to-date and the recorded cost lines, the RETURN PASS queue
(legs still queued, the 11B pre-authorisations expiring at this gate),
the acceptance note's per-row status pointer, and PLAN-11C's draft 11C
OM-20 list — quoted verbatim, never re-derived and never approved here.
It signs nothing and decides nothing.

Commands: ``draft`` (write the readout) · ``check`` (structural invariants:
Status PENDING, sha256 re-computes over the agent-drafted block body, all
six parts present, every ``- `` line carries a Default marker, the guard
sentence and the recorded drifts are present). Stdlib only.
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

READOUT_REL = "docs/build/readouts/GATE-G5.md"
MAP_REL = "docs/build/tools/record_policy/return_pass.toml"
SPEND_REL = "docs/build/reports/spend/spend_ledger.csv"
USAGE_REL = "docs/build/reports/spend/agent_usage.csv"
NOTE_REL = "docs/build/reports/acceptance/11B.md"
TICKET_REL = "docs/tickets/343_GATE-G5__11b-check-in.md"

BEGIN = "<!-- agent-drafted:begin sha256={sha} -->"
END = "<!-- agent-drafted:end -->"

#: PLAN-11C's draft 11C OM-20 list (docs/build/runs/PLAN-11C.md "Draft 11C
#: OM-20 list for GATE-G5") — quoted verbatim, never approved here.
OM20_11C_TABLE = """\
| row | id | mutation (contract header) | restore point |
|---|---|---|---|
| 346 | P35.2 | alerting-as-code roll: uptime checks, alert policies, notification-channel binding, log retention/restricted sink, `ops/probes/`+`ops/runs/` bucket versioning, `sig-probe` job rebuild | committed IaC text + recorded pre-state describes |
| 348 | P35.23 | restricted-bucket write of screened corpus slices + committed digests | digest list + bucket versioning |
| 351 | P36.76 | Axon Connect: screen records + page hashes + registry-row appends (single recorded GETs of public registration pages) | appended set's record; leg B is the operator's act |
| 352 | P36.77 | DocumentCloud/MuckRock: unauthenticated public-page GETs + registry appends + redacted-rendition records | appended set's record; activation stays operator's |
| 353 | P36.78 | Sourcewell/OMNIA: public-page GETs + appends + terms captures + redacted renditions | appended set's record; leg B operator's |
| 354 | P36.13 | rate-limit enforcement flip on the hosted deployment (defined → enforced, gate-pending) | prior deployment revision |
| 371 | P36.79 | restricted-bucket object write — the sealed relevance set's bytes | bucket versioning + committed sha256 |
| 374 | P36.33 | R2 host create (basemap host provisioning) | re-creatable from `basemap.lock.json` + JUR-01's pack |
| 385 | P36.75 | append-only claim write on the hosted spine (organisation-level Flock share-list claims, gate-pending) | additive — the written set's digest list |
| 386 | P36.43 | scheduler job create (status lane) | job-definition removal |
| 387 | P36.44 | scheduler job create (monthly cut + weekly materialize) | job-definition removal |
| 389 | P36.46 | append-only history backfill on the hosted spine (gate-pending) | appended set's digest list |
| 412 | P36.68 | mirror writes — content-addressed extract pushes + versions.json | content-addressed objects + index diff |"""

OM20_NEVER = (
    "P37.2's tier bump, P36.38 (an API roll that changes a public route's "
    "response), P36.72b's HG-11 readout, every HG-03 flip, and P36.70 if "
    "the standing go has lapsed — the never-pre-authorised classes of "
    "plan §3.3"
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

#: The GATE-G4-approved OM-20 11B list (19 rows; expiry: this GATE) — the
#: "any 11B leg whose pre-authorisation expires here unrun" set reads the
#: queued legs of these rows plus any go naming `expires next GATE` /
#: `expires GATE-G5`.
OM20_11B_ROWS = {
    "P35.5", "P35.1a", "P35.14a", "P35.15a", "P35.15b", "P35.1b", "P35.16",
    "P35.17", "P35.22", "P35.24", "P35.25", "P35.26", "P35.27", "P35.32",
    "P35.41", "P35.46", "P35.53", "P35.59", "P35.62",
}
EXPIRING_GO_RE = re.compile(r"expires (next GATE|GATE-G5)", re.IGNORECASE)


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
    """(queued leg ids, expiring-at-G5 unrun row/leg ids)."""
    data = tomllib.loads((root / MAP_REL).read_text(encoding="utf-8"))
    legs: list[str] = []
    expiring: list[str] = []
    for row in data.get("row", []):
        key = str(row.get("key"))
        for leg in row.get("legs", []):
            lid = str(leg.get("id"))
            legs.append(f"{lid} ({key})")
            go = str(leg.get("go", ""))
            if key in OM20_11B_ROWS or EXPIRING_GO_RE.search(go):
                if lid not in expiring:
                    expiring.append(f"{lid} ({key})")
    return legs, expiring


def packet_body(root: Path) -> str:
    """The agent-drafted packet — the six S2 §3.6 parts, defaults first."""
    legs, expiring = _map_state(root)
    spend = _spend_summary(root)
    usage = root / USAGE_REL
    usage_line = (
        f"agent usage ledger: {usage.name} present "
        f"({len(usage.read_text(encoding='utf-8').splitlines()) - 1} rows) — "
        "reported, not capped (A-2b)"
        if usage.is_file()
        else "agent usage ledger absent"
    )

    return f"""\
**Agent-drafted GATE-G5 packet** — composed by P35.64 before the operator
answers; every default is non-action; ``continue`` answers **batch** lines
only; own-words, publication, rights, Part VIII, identity, money and OM-20
lines each need a verbatim answer; silence = pause (OM-18), never consent.

**1. Budget** — *(status lines: batch)*

- Infra month-to-date + forecast vs the $300/mo ceiling — **{'; '.join(spend)}**. *Default: none (status; information only).* **batch**
- {usage_line}. *Default: none.* **batch**
- The recorded 11B/11C cost lines (committed rows, estimates/inferences — never measured billing): ≈ $0.1/mo release storage, ≈ $0.04/mo candidate, the Wave-C ≈ $2.2/mo projection at the S1a upper end, Cloudflare/R2 (the $50.00/mo hard ceiling is a ceiling line, not measured spend) and registrar/domains (operator-linked billing evidence pending). *Default: none.* **batch**
- The 11C projection against $300 stands well under the ceiling at draft time; any line that would exceed it is a money line needing its own verbatim answer — none identified at draft time. *Default: none.* **batch**

**2. Publication** — *(verbatim lines)*

- What 11B published: P35.63 — the first model release under its own signed, candidate-specific HG-11 readout ("single maintainer, no second reviewer"; "no human check performed"), quoted not re-asked. At draft time both of P35.63's legs remain **queued** (`prepared_not_executed`; the promotion awaits the signature — the old GATE-G3 signature is superseded, not transferred): **nothing has been promoted, hosted, deployed or published**. *Default: none (status).* **batch**
- 11C plans P36.72b — the core-surfaces release under its own Class S readout (its cell names the same sitting as GATE-G6) — and P36.70 — the second-release acceptance running under the Class R standing go if it is still valid. Publication lines are never pre-authorised. *Default: none (status).* **batch**

**3. Rights** — *(verbatim lines)*

- **ING-GO-C** — Wave C legs window 2026-11-16 → 11-20 (P37.2; earliest 10-26 if P37.1, PKG-07 and Q-23 are early; the tier-bump go is P37.2's own in-ticket pause, not this list's) with the **Wave-C/vendor HG-03 flip list** (OP-26) naming the sources whose rows land in 11C. *Default: the wave's legs pause in-ticket; rows land with `ingestion_permitted = false` and activation skips them.*
- Flips are executed by the operator — one commit signed with the OP-25 key, or a signed GATE DECISIONS row naming each source id (S6R-17; SIG-SEC-010; P34.28's check). *Default: no flips.*
- A-7 lines due in 11C — the Part VIII screen lanes the 11C contracts name; each a rights line with its own verbatim answer, never batch. *Default: each pauses in-ticket.*
- **Title/note recorded, not resolved:** the plan row's title carries `ING-GO-B` while its S4c note reads `collects ING-GO-C for Wave C (P37.2 legs 11-16 -> 11-20), A-7 lines due in 11C` — this packet drafts the note's content and records the title token verbatim; ING-GO-B itself was GATE-G4's Wave-B line. *Default: none (status).* **batch**
- Q-23 (a), A-10 (no review) and I8-Q5 (a) were answered at GATE-P — recorded, not re-asked. *Default: none.* **batch**

**4. The 11C OM-20 list** — *(an OM-20 line: approved only by its own verbatim line, never by `continue`)*

- PLAN-11C's draft (row 340's run ledger — built only from written `Production mutations` headers; each entry is approve-verbatim or nothing; `expires: GATE-G6`, or an inserted gate if the 11C re-split rule fires) — the list below is the ask itself, approved only by its own verbatim line, never by `continue`. *Default: nothing pre-authorised — each named mutation pauses in-ticket.*

{OM20_11C_TABLE}

- 13 rows vs §8.1's recorded count of 10 — the plan anticipated "any further row a written `Production mutations` header names"; the four beyond its named nine are P36.76, P36.77, P36.78 and P36.43. Recorded as the drift it is, never resolved here. *Default: none.* **batch**
- Never on any list: {OM20_NEVER}. *Default: none.* **batch**
- 11B legs whose GATE-G4 pre-authorisation expires at this gate unrun (from the RETURN PASS map at draft time — the 19-row OM-20 11B list's queued legs + every go naming `expires next GATE`/`expires GATE-G5`): {('; '.join(sorted(expiring))) if expiring else 'none'} — re-listed by row id or left to an in-ticket go. *Default: each re-asks in-ticket (nothing pre-authorised — each named mutation pauses in-ticket).*

**5. Class R standing-go renewal (B-9)** — *(verbatim line; never renewed by `continue`)*

- The operator's adopted text (agent-drafted, adopted by the operator at 2026-10-01T04:35:53Z — retro: the B-9 answer record, GATE-P's GATE DECISIONS row; sha256 `e4e24975b854…`): "{CLASS_R_TEXT}" — renewed verbatim or not; it expires at the next sub-round GATE or after 30 days, whichever is first; it is void on any ratchet regression, Part VIII screen change or new source (TS-13); a renewal is recorded as a GATE DECISIONS `kind: pre-authorization` row. *Default: it lapses → every release is Class S, and P36.70's first Class R promotion becomes an in-ticket pause.*

**6. Status** — *(information only; batch)*

- Per-row layered status: `docs/build/reports/acceptance/11B.md` (P35.64's acceptance note; the live sweep is queued — the promoted release does not exist — see the note). *Default: none.* **batch**
- Live-leg queue at draft time ({len(legs)} legs): {'; '.join(legs)}. *Default: none.* **batch**
- Carried 11B legs: P35.61's apply leg (its go was never given — listed, carried); legs whose window extends past this GATE are listed and carried; P35.11's Wave-A window 10-19 → 10-23 elapsed unrun (verbatim-go awaited) — recorded, never smoothed. *Default: none.* **batch**
- CI incidents: NIGHTLY-RED-1 — the scheduled `nightly.yml` runs on `main` failed 2026-10-07 → 10-20 (14 runs; the owed observation of `D-P34.7-1`/`D-P34.2-2`; repair routed separately). Anomalies and operator-side merges read from GitHub at the sitting. *Default: none.* **batch**
- The D-K2-1 top-50 organisation review (OP-14, ≈ 1–2 h of the operator's time) — due by this sitting; its outcome is reported or carried, never performed by a row. *Default: carried.* **batch**
- Whether PLAN-11C's Phase-4 review fired the 11C re-split rule (> 85 engineering rows or > 75 engineering runs → an inserted gate): 11C stood at 76 / 66.5 at S6c — the rule did not fire at draft time. *Default: none.* **batch**
- The launch-unmet MUSTs list (`D-R11-LATER-04` — the ADR-171 Stage-0 set SIG-CHART-033, SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013, SIG-GOV-024): owed, unmet at launch — carried to GATE-ANNOUNCE's spec-MUSTs list, recorded, never implied satisfied. *Default: none.* **batch**
- The isolation probe repeated at this GATE (plan §8.5) — the orchestrator's work, reported here. *Default: none.* **batch**
""" + "\n"


def render_readout(packet: str) -> str:
    sha = hashlib.sha256(packet.encode("utf-8")).hexdigest()
    return f"""# GATE-G5 — pending readout

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/343_GATE-G5__11b-check-in.md`.
Decision domain: the 11B check-in — budget, publication, rights (ING-GO-C
for Wave C + the Wave-C/vendor HG-03 flip list + the A-7 lines due in
11C), the 11C OM-20 list as drafted by PLAN-11C, the Class R standing-go
renewal — and nothing else; each line's default is non-action.

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] The packet presented is P35.64's draft (sha256 matches) and every line shows its default; it was not presented while a leg was due.
- [ ] The operator's answer is recorded verbatim with `date -u` in GATE DECISIONS and the readout; each OM-20, rights, money and own-words line has its own verbatim answer or is recorded as defaulted.
- [ ] The 11C OM-20 list (if any) names exact row ids with `expires: GATE-G6`; the Class R renewal (if given) is quoted with its expiry; ING-GO-C and the Wave-C/vendor flip list are recorded as answered or defaulted.
- [ ] Records: GATE DECISIONS rows and the readout only gain lines (`python3 docs/build/tools/memory_guard.py all --staged` green before the record commit); the PHASE LOG pause/resume entry written; the LEDGER advanced to row 344 only after the answer.

## Packet (agent-drafted)

{BEGIN.format(sha=sha)}
{packet}{END}

## Signature

<!-- Appended only at signing, by the commit that moves Status:. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | GATE-G5
Operator confirmation (verbatim, <date -u>): "<words>" — covers agent-drafted sha256:{sha[:12]}
Signed by: repository operator. Recorded by devin-desktop/swe-2-high/subagent, which does not sign.
"""


def check(text: str) -> list[str]:
    """Structural invariants of the committed readout."""
    v: list[str] = []
    if "Status: PENDING" not in text:
        v.append("Status: PENDING absent — a signed/edited readout fails")
    m = re.search(
        r"<!-- agent-drafted:begin sha256=([0-9a-f]{64}) -->\n(.*?)<!-- agent-drafted:end -->",
        text,
        re.S,
    )
    if not m:
        v.append("agent-drafted block absent")
    else:
        body = m.group(2)
        actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if actual != m.group(1):
            v.append(
                f"agent-drafted sha256 mismatch: {m.group(1)[:12]} != {actual[:12]}"
            )
        for part in (
            "1. Budget",
            "2. Publication",
            "3. Rights",
            "4. The 11C OM-20 list",
            "5. Class R",
            "6. Status",
        ):
            if part not in body:
                v.append(f"packet part missing: {part}")
        for ln in body.splitlines():
            if ln.startswith("- ") and "Default:" not in ln:
                v.append(f"packet line lacks Default: {ln[:60]}")
        if "Agent-drafted" not in body:
            v.append("packet not labelled agent-drafted")
        for required in (
            "ING-GO-C",
            "e4e24975b854",
            "expires: GATE-G6",
            "D-K2-1",
            "76 / 66.5",
            "ING-GO-B",
        ):
            if required not in body:
                v.append(f"required packet content absent: {required}")
        if "P35.64's draft" not in text:
            v.append("criterion's drafter line absent")
    if "an agent must not\nsign or assume silence is approval" not in text:
        v.append("guard sentence absent")
    return v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gate_packet_11b.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft", help="write the GATE-G5 readout draft")
    d.add_argument("--root", default=".")
    d.add_argument("--out", default=None)
    c = sub.add_parser(
        "check", help="structural invariants of the committed readout"
    )
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
        print(
            "check: ok" if not violations else f"check: {len(violations)} violations"
        )
        return 0 if not violations else 1

    packet = packet_body(root)
    text = render_readout(packet)
    out = Path(args.out) if args.out else root / READOUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(packet.encode("utf-8")).hexdigest()
    print(f"gate_packet_11b: drafted {out}; packet sha256 {sha}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
