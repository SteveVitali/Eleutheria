"""S1b completeness check: every owed/unmet/found item has exactly ONE disposition.

META_PLAN §3 P9 and §8.1. Reads `universe/UNIVERSE_DISPOSED.csv` and re-derives the expected item
set from the sources themselves (`universe/UNIVERSE.csv`, `findings/FINDINGS.csv`,
`feedback/OPERATOR_FEEDBACK.md`, `data/acquisition_plan.csv` + `data/candidates_consolidated.csv`),
then checks every disposition target against `data/ticket_catalog.csv` and
`data/decision_catalog.csv`. Standard library only; read-only.

Rules (each failure is printed and the exit code is 1):
  (a) every source item appears exactly once and nothing else appears (ids, kinds, source refs,
      group sizes); every candidate sits in exactly one acquisition-plan row, hence in exactly
      one candidate group;
  (b) every disposition is one §8.1 enum value (plus `decision`) and every reference resolves:
      cat_ids exist in the ticket catalog with a class that fits the kind, dec_ids exist in the
      decision catalog, merged-into targets exist in this file and are not themselves merged,
      and link tokens (cat ids, `gate:<dec_id>`, `interim:<cat_id>`, U-/F-/CG- ids) resolve;
  (c) every S0/S1 finding (severity read from FINDINGS.csv) resolves, after following
      merged-into, to a unit in the stage-B seed or the first Round-11 waves (`first_waves`),
      to an operator decision, to already-done evidence, or to a later-wave fix that names a
      first-wave `interim:` mitigation; later-phase only with an explicit trigger; never wontfix;
  (d) every operator ask U-003.1 ... U-003.11 resolves to at least one seed/R11 ticket;
  (e) every owed deferral (UNIVERSE effective_status OPEN or PARTIAL) has a valid disposition,
      and a later-phase one names an explicit trigger.

Run:  python3 docs/build/planning/2026-09-30-next-phase/tools/check_dispositions.py \
          [--pd DIR] [--csv FILE]
Test: uv run python -m pytest \
          docs/build/planning/2026-09-30-next-phase/tools/test_check_dispositions.py
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

PD_DEFAULT = pathlib.Path(__file__).resolve().parents[1]
COLS = [
    "item_id",
    "source_kind",
    "source_ref",
    "title",
    "severity_or_status",
    "disposition",
    "disposition_ref",
    "rationale",
    "stream",
    "links",
]
ENUM = (
    "ticket",
    "live-return-pass",
    "spec-amendment",
    "adr-waiver",
    "operator-action",
    "human-marker",
    "already-done",
    "wontfix",
    "later-phase",
    "merged-into",
    "decision",
)
CAT_PAT = re.compile(r"^(SEED-\d{2}|R11-[A-Z0-9]+(?:-[A-Za-z0-9.]+)+|OP-\d{2}|LATER-\d{2})$")
DISP_PAT = re.compile(r"^([a-z-]+)\((.+)\)$", re.S)
OWED = ("OPEN", "PARTIAL")
SEVERE = ("S0", "S1")
U003_ASKS = [f"U-003.{i}" for i in range(1, 12)]

# Units that a design row itself places in its first two waves (wave 0/1), before S2 merges the
# waves. Each block cites the design that says so; first_waves() adds S1a's own landing column,
# K13's wave column and the transitive hard prerequisites of all of them.
DESIGN_FIRST_WAVES: dict[str, tuple[str, ...]] = {
    # G2 §4: step 0 (production safety and honesty), step 1 (Round-10 schema + API), step 4
    # ("engineering from Round-11 day 1": the C4 blockers ACT-16..ACT-20)
    "G2 steps 0, 1, 4": (
        "R11-ACT-01",
        "R11-ACT-02",
        "R11-ACT-03",
        "R11-ACT-04",
        "R11-ACT-05",
        "R11-ACT-06",
        "R11-ACT-07",
        "R11-ACT-08",
        "R11-ACT-09",
        "R11-ACT-10",
        "R11-ACT-11",
        "R11-ACT-16",
        "R11-ACT-17",
        "R11-ACT-17b",
        "R11-ACT-18",
        "R11-ACT-19",
        "R11-ACT-20",
    ),
    # L3 §9 "Waves": wave 0 CONF-02; wave 1 CONF-01, CONF-03a, CONF-08
    "L3 waves 0-1": ("R11-CONF-02", "R11-CONF-01", "R11-CONF-03a", "R11-CONF-08"),
    # I8 Wave A (10-19 -> 10-23): ACQ-07 and the build tickets it depends on (ACQ-01, 02, 04-06)
    "I8 Wave A": (
        "R11-ACQ-01",
        "R11-ACQ-02",
        "R11-ACQ-04",
        "R11-ACQ-05",
        "R11-ACQ-06",
        "R11-ACQ-07",
    ),
    # F5 §4 "Suggested order" steps 1-5: PKG-02, PKG-13/01, PKG-09a, PKG-03/04/05 before G2
    # activation, and
    # PKG-06/08/10/11/07 "before the next public republish"
    "F5 order 1-5": (
        "SEED-03",
        "R11-CI-01",
        "R11-ACT-09",
        "R11-ACT-08",
        "R11-ACT-16",
        "R11-ACT-17",
        "R11-ACT-17b",
        "R11-ACT-19",
        "R11-ACT-05",
        "R11-ACT-20",
        "R11-K13-JUR-01",
        "R11-K13-JUR-02a",
        "R11-K13-JUR-02b",
        "R11-DATA-01",
        "R11-ACT-07",
        "R11-DATA-04",
        "R11-DATA-03",
        "R11-DATA-02",
    ),
}


def read_csv(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def load_catalog(pd: pathlib.Path) -> dict[str, dict]:
    return {r["cat_id"]: r for r in read_csv(pd / "data" / "ticket_catalog.csv")}


def load_decisions(pd: pathlib.Path) -> set[str]:
    return {r["dec_id"] for r in read_csv(pd / "data" / "decision_catalog.csv")}


def load_feedback_ids(pd: pathlib.Path) -> list[str]:
    """U-0nn headings plus U-0nn / U-003.n table rows in OPERATOR_FEEDBACK.md, in order, unique."""
    txt = (pd / "feedback" / "OPERATOR_FEEDBACK.md").read_text()
    ids: list[str] = []
    for m in re.finditer(r"^### (U-\d{3})\b", txt, re.M):
        ids.append(m.group(1))
    for m in re.finditer(r"^\| (U-\d{3}(?:\.(?:\d+|G|X))?) \|", txt, re.M):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def plan_group(ticket: str) -> str:
    """Candidate group id for an acquisition-plan `ticket` value.

    One group per build ticket (ACQ-nn) or per deferral trigger text.
    """
    m = re.match(r"(ACQ-\d+)", ticket)
    if m:
        return "CG-" + m.group(1)
    if ticket.startswith("none (I7 Tier 3)"):
        return "CG-TIER3"
    if ticket.startswith("G2-step5"):
        return "CG-G2-STEP5"
    if ticket.startswith("none (discovery channel"):
        return "CG-DISCOVERY-ACQ-14"
    m = re.match(r"later-phase\((.*)\)$", ticket)
    if m:
        slug = re.sub(r"[^a-z0-9]+", "-", m.group(1).lower()).strip("-")[:48].rstrip("-")
        return "CG-LATER-" + slug
    raise ValueError(f"unknown acquisition-plan ticket value: {ticket!r}")


def load_candidate_groups(pd: pathlib.Path, errors: list[str]) -> dict[str, int]:
    plan = read_csv(pd / "data" / "acquisition_plan.csv")
    cons = read_csv(pd / "data" / "candidates_consolidated.csv")
    seen: Counter[str] = Counter()
    for p in plan:
        for c in p["cand_ids"].split(";"):
            if c:
                seen[c.strip()] += 1
    expected: Counter[str] = Counter()
    for c in cons:
        for cid in c["cand_ids_merged"].split(";"):
            if cid.strip():
                expected[cid.strip()] += 1
    for c, n in seen.items():
        if n != 1:
            errors.append(f"(a) candidate {c} appears in {n} acquisition-plan rows")
    for c in expected:
        if c not in seen:
            errors.append(f"(a) consolidated candidate {c} is in no acquisition-plan row")
    for c in seen:
        if c not in expected:
            errors.append(
                f"(a) acquisition-plan candidate {c} is not in candidates_consolidated.csv"
            )
    groups: Counter[str] = Counter()
    for p in plan:
        try:
            groups[plan_group(p["ticket"])] += 1
        except ValueError as exc:
            errors.append(f"(a) {exc}")
    return dict(groups)


def first_waves(catalog: dict[str, dict], pd: pathlib.Path) -> set[str]:
    """Seed rows, S1a 'early R11' rows, K13 W0/W1 and the design-designated wave 0/1 units.

    Their transitive hard prerequisites (`depends_on`) are added too.
    """
    k13_path = pd / "data" / "k13_tickets.csv"
    k13_wave = {r["ticket_id"]: r["wave"] for r in read_csv(k13_path)} if k13_path.exists() else {}
    base: set[str] = set()
    for cid, c in catalog.items():
        where = c.get("where_it_must_land", "")
        if (
            c.get("class") == "seed"
            or where.startswith("stage-B seed")
            or where.startswith("early R11")
        ):
            base.add(cid)
        if cid.startswith("R11-K13-") and k13_wave.get(cid[len("R11-K13-") :]) in ("W0", "W1"):
            base.add(cid)
        if "wave 1" in where:
            base.add(cid)
    for units in DESIGN_FIRST_WAVES.values():
        base.update(u for u in units if u in catalog)
    out = set(base)
    stack = list(base)
    while stack:
        for dep in (d for d in catalog[stack.pop()].get("depends_on", "").split(";") if d):
            if dep in catalog and dep not in out:
                out.add(dep)
                stack.append(dep)
    return out


def parse_disposition(s: str) -> tuple[str, str] | None:
    m = DISP_PAT.match(s.strip())
    if not m:
        return None
    return m.group(1), m.group(2).strip()


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)


def check(rows: list[dict], pd: pathlib.Path) -> Result:
    res = Result()
    err = res.errors
    catalog = load_catalog(pd)
    decisions = load_decisions(pd)
    universe = read_csv(pd / "universe" / "UNIVERSE.csv")
    findings = read_csv(pd / "findings" / "FINDINGS.csv")
    feedback = load_feedback_ids(pd)
    groups = load_candidate_groups(pd, err)
    fw = first_waves(catalog, pd)

    if rows and list(rows[0].keys()) != COLS:
        err.append(f"(a) columns {list(rows[0].keys())} != {COLS}")

    # ---- (a) exactly once
    ids = Counter(r["item_id"] for r in rows)
    for i, n in ids.items():
        if n > 1:
            err.append(f"(a) {i} appears {n} times")
    by_id = {r["item_id"]: r for r in rows}
    expected: dict[str, tuple[str, str]] = {}
    for u in universe:
        expected[u["u_id"]] = (u["source_kind"], u["source_ref"])
    for f in findings:
        expected[f["f_id"]] = ("finding", f["origin_ref"])
    for i in feedback:
        expected[i] = ("feedback", f"feedback/OPERATOR_FEEDBACK.md {i}")
    for g in groups:
        expected[g] = ("candidate_group", "")
    for i, (kind, ref) in expected.items():
        r = by_id.get(i)
        if r is None:
            err.append(f"(a) source item {i} ({kind}) has no disposition row")
            continue
        if r["source_kind"] != kind:
            err.append(f"(a) {i} source_kind {r['source_kind']!r} != {kind!r}")
        if ref and r["source_ref"] != ref:
            err.append(f"(a) {i} source_ref {r['source_ref']!r} != {ref!r}")
        if kind == "candidate_group":
            m = re.match(r"n=(\d+)\b", r["severity_or_status"])
            if not m or int(m.group(1)) != groups[i]:
                err.append(f"(a) {i} size {r['severity_or_status']!r} != n={groups[i]}")
    for i in by_id:
        if i not in expected:
            err.append(f"(a) {i} is not a source item")

    # ---- (b) enum and references
    parsed: dict[str, tuple[str, str, list[str]]] = {}
    find_ids = {f["f_id"] for f in findings}
    uni_ids = {u["u_id"] for u in universe}
    for r in rows:
        i = r["item_id"]
        p = parse_disposition(r["disposition"])
        refs = [x.strip() for x in r["disposition_ref"].split(";") if x.strip()]
        if p is None:
            err.append(f"(b) {i} disposition {r['disposition']!r} is not kind(arg)")
            continue
        kind, arg = p
        parsed[i] = (kind, arg, refs)
        if kind not in ENUM:
            err.append(f"(b) {i} kind {kind!r} not in the enum")
            continue
        if not refs:
            err.append(f"(b) {i} has no disposition_ref")
            continue
        if not r["rationale"].strip():
            err.append(f"(b) {i} has no rationale")
        for x in refs:
            if CAT_PAT.match(x) and x not in catalog:
                err.append(f"(b) {i} ref {x} is not a catalog unit")
        first = refs[0]
        cls = catalog.get(first, {}).get("class")
        if kind in ("ticket", "live-return-pass", "decision", "merged-into") and arg != first:
            err.append(f"(b) {i} {kind} argument {arg!r} != first ref {first!r}")
        if kind == "ticket" and cls not in ("seed", "r11"):
            err.append(f"(b) {i} ticket ref {first} is class {cls!r}, not seed/r11")
        elif kind == "live-return-pass" and cls != "r11":
            err.append(f"(b) {i} live-return-pass ref {first} is class {cls!r}, not r11")
        elif kind == "operator-action" and cls != "operator":
            err.append(f"(b) {i} operator-action ref {first} is class {cls!r}, not operator")
        elif kind == "human-marker" and first not in catalog:
            err.append(f"(b) {i} human-marker ref {first} is not a catalog unit")
        elif kind == "spec-amendment" and first != "SEED-12":
            err.append(f"(b) {i} spec-amendment must land in SEED-12 (T1 spec_src), got {first}")
        elif kind == "adr-waiver" and first != "SEED-11":
            err.append(f"(b) {i} adr-waiver must land in SEED-11 (T1 ADRs), got {first}")
        elif kind == "decision" and first not in decisions:
            err.append(f"(b) {i} decision {first} is not in the decision catalog")
        elif kind == "later-phase":
            if len(arg) < 8 or arg.lower() in ("trigger", "later"):
                err.append(f"(b) {i} later-phase has no explicit trigger ({arg!r})")
            if CAT_PAT.match(first) and cls != "later":
                err.append(f"(b) {i} later-phase ref {first} is class {cls!r}, not later")
        elif kind in ("already-done", "wontfix") and (
            len(arg) < 3 or CAT_PAT.match(first) or first in decisions
        ):
            err.append(
                f"(b) {i} {kind} needs evidence text and an evidence ref (got {arg!r} / {first!r})"
            )
        for tok in r["links"].split():
            if tok.startswith("gate:"):
                if tok[5:] not in decisions:
                    err.append(f"(b) {i} link {tok} is not in the decision catalog")
            elif tok.startswith("interim:"):
                if tok[8:] not in catalog:
                    err.append(f"(b) {i} link {tok} is not a catalog unit")
            elif CAT_PAT.match(tok):
                if tok not in catalog:
                    err.append(f"(b) {i} link {tok} is not a catalog unit")
            elif re.match(r"^U-\d{4}$", tok):
                if tok not in uni_ids:
                    err.append(f"(b) {i} link {tok} is not a universe item")
            elif re.match(r"^F-\d{2,3}$", tok):
                if tok not in find_ids:
                    err.append(f"(b) {i} link {tok} is not a finding")
            elif re.match(r"^(CG-|U-\d{3}\b)", tok):
                if tok not in by_id:
                    err.append(f"(b) {i} link {tok} is not an item in this file")
    for i, (kind, arg, _refs) in parsed.items():
        if kind != "merged-into":
            continue
        tgt = parsed.get(arg)
        if arg == i:
            err.append(f"(b) {i} merged into itself")
        elif arg not in by_id:
            err.append(f"(b) {i} merged-into target {arg} is not an item in this file")
        elif tgt and tgt[0] == "merged-into":
            err.append(f"(b) {i} merged-into target {arg} is itself merged (no chains)")

    def final(i: str) -> tuple[str, str, list[str], str]:
        kind, arg, refs = parsed[i]
        if kind == "merged-into" and arg in parsed:
            k2, a2, r2 = parsed[arg]
            return k2, a2, r2, arg
        return kind, arg, refs, i

    # ---- (c) S0/S1 findings
    severe_ok: Counter[str] = Counter()
    sev = {f["f_id"]: f["severity"] for f in findings}
    for fid, s in sev.items():
        if s not in SEVERE or fid not in parsed:
            continue
        kind, arg, refs, at = final(fid)
        links = by_id[at]["links"].split()
        interim = [t[8:] for t in links if t.startswith("interim:") and t[8:] in fw]
        if kind == "decision":
            severe_ok["decision"] += 1
        elif kind == "already-done":
            severe_ok["already-done"] += 1
        elif kind == "wontfix":
            err.append(f"(c) {fid} ({s}) is wontfix")
        elif kind == "later-phase":
            severe_ok["later-phase(explicit trigger)"] += 1
        elif refs and refs[0] in fw:
            severe_ok["first-wave unit"] += 1
        elif kind in ("ticket", "live-return-pass") and interim:
            severe_ok["later fix + first-wave interim"] += 1
        else:
            err.append(
                f"(c) {fid} ({s}) resolves to {kind}({arg}) outside the seed/first R11 waves "
                "with no first-wave interim"
            )
    res.stats["severe"] = dict(severe_ok)

    # ---- (d) operator asks U-003.1..11
    for a in U003_ASKS:
        if a not in parsed:
            err.append(f"(d) operator ask {a} has no disposition")
            continue
        kind, arg, refs, _ = final(a)
        tickets = [x for x in refs if catalog.get(x, {}).get("class") in ("seed", "r11")]
        if kind not in ("ticket", "live-return-pass") or not tickets:
            err.append(
                f"(d) operator ask {a} resolves to {kind}({arg}), not to >=1 seed/R11 ticket"
            )

    # ---- (e) owed deferrals
    owed = [u for u in universe if u["source_kind"] == "deferral" and u["effective_status"] in OWED]
    owed_kinds: Counter[str] = Counter()
    for u in owed:
        if u["u_id"] not in parsed:
            err.append(f"(e) owed deferral {u['source_ref']} ({u['u_id']}) has no disposition")
            continue
        kind, arg, refs, _ = final(u["u_id"])
        owed_kinds[kind] += 1
        if kind == "later-phase" and len(arg) < 8:
            err.append(
                f"(e) owed deferral {u['source_ref']} is later-phase without an explicit trigger"
            )
    res.stats["owed"] = dict(owed_kinds)
    res.stats["owed_n"] = len(owed)
    res.stats["rows"] = len(rows)
    res.stats["by_kind"] = dict(Counter(r["source_kind"] for r in rows))
    res.stats["first_waves"] = len(fw)
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pd", type=pathlib.Path, default=PD_DEFAULT, help="planning directory")
    ap.add_argument(
        "--csv",
        type=pathlib.Path,
        default=None,
        help="disposed CSV (default <pd>/universe/UNIVERSE_DISPOSED.csv)",
    )
    args = ap.parse_args(argv)
    path = args.csv or args.pd / "universe" / "UNIVERSE_DISPOSED.csv"
    res = check(read_csv(path), args.pd)
    for e in res.errors:
        print("ERROR", e)
    s = res.stats
    print(f"rows {s.get('rows')} {s.get('by_kind')}; first-wave units {s.get('first_waves')}")
    print(
        f"S0/S1 resolution {s.get('severe')}; owed deferrals {s.get('owed_n')} -> {s.get('owed')}"
    )
    print(
        "check_dispositions: " + ("FAIL" if res.errors else "OK") + f" ({len(res.errors)} errors)"
    )
    return 1 if res.errors else 0


if __name__ == "__main__":
    sys.exit(main())
