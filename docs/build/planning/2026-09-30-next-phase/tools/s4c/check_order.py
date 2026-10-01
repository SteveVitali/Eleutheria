"""S4c ordering / DAG re-check of data/round11_plan.csv (scratch; gitignored).

Checks:
  1. chain rows 201.. are contiguous, unique, and in sub-round order 11A < 11B < 11C < 11D < tail;
  2. every depends_on token resolves (chain row, seed, operator, later, or an annotated drop);
  3. no chain row appears before a chain-row dependency (hard, (S2), (S4c), live:, sequence and
     soft edges all counted as ordering edges);
  4. the dependency graph over all rows is acyclic;
  5. no 11A/11B row depends on a later sub-round;
  6. every operator gate default that is a publication/rights/Part VIII/production mutation does
     not pre-authorise on silence (no 'default a): no per-step go' phrasing left);
and prints totals by sub-round (rows, kinds, est_runs, leg_runs, production-touching rows,
in-ticket pauses).
"""

from __future__ import annotations

import csv
import pathlib
import re
import sys
from collections import Counter, defaultdict

PD = pathlib.Path(__file__).resolve().parents[2]  # PD; copied from docs/build/logs/next-phase/S4c at S6
rows = list(csv.DictReader((PD / "data" / "round11_plan.csv").open()))
by = {r["id"]: r for r in rows}
CHAIN_SUBS = ["11A", "11B", "11C", "11D", "11D-tail"]
chain = [r for r in rows if r["sub_round"] in CHAIN_SUBS]
errors: list[str] = []

# 1
nums = [int(r["row"]) for r in chain]
if nums != list(range(201, 201 + len(chain))):
    errors.append("chain rows are not contiguous 201..")
subidx = [CHAIN_SUBS.index(r["sub_round"]) for r in chain]
if subidx != sorted(subidx):
    errors.append("sub-rounds out of order")
pos = {r["id"]: int(r["row"]) for r in chain}


def parse(tok: str) -> tuple[str, str] | None:
    tok = tok.strip()
    if not tok:
        return None
    if "->dropped" in tok:
        return ("drop", tok)
    m = re.match(r"^(live:)?([A-Za-z0-9.\-]+?)(\(.*\))?$", tok)
    if not m:
        return ("bad", tok)
    return ("live" if m.group(1) else "hard", m.group(2))


edges = defaultdict(list)
for r in rows:
    for tok in r["depends_on"].split(";"):
        p = parse(tok)
        if p is None or p[0] == "drop":
            continue
        if p[0] == "bad":
            errors.append(f"{r['id']}: unparseable dep {tok!r}")
            continue
        d = p[1]
        if d not in by:
            # catalog ids on later rows (e.g. R11-CONF-09) are acceptable for 'later' kind
            if r["kind"] == "later" and d.startswith("R11-"):
                continue
            errors.append(f"{r['id']}: dep {d} does not resolve to a plan row")
            continue
        edges[r["id"]].append((d, p[0]))
        # 3
        if r["id"] in pos and d in pos and pos[d] >= pos[r["id"]]:
            errors.append(f"order: {r['id']} (row {pos[r['id']]}) before its dependency {d} (row {pos[d]})")
        # 5
        if r["id"] in pos and d in pos:
            if CHAIN_SUBS.index(by[d]["sub_round"]) > CHAIN_SUBS.index(r["sub_round"]):
                errors.append(f"{r['id']} depends on a later sub-round row {d}")

# 4 cycles
color: dict[str, int] = {}


def dfs(u: str, stack: list[str]) -> None:
    color[u] = 1
    for v, _ in edges.get(u, []):
        if color.get(v) == 1:
            errors.append("cycle: " + " -> ".join(stack + [u, v]))
        elif color.get(v) is None:
            dfs(v, stack + [u])
    color[u] = 2


sys.setrecursionlimit(10000)
for r in rows:
    if r["id"] not in color:
        dfs(r["id"], [])

# 6
for r in rows:
    if re.search(r"default a\): no per-step go", r["operator_gate"]):
        errors.append(f"{r['id']}: OM-20 cell still pre-authorises on A-15's default")

# totals
def f(x: str) -> float:
    try:
        return float(x)
    except ValueError:
        return 0.0


tot = defaultdict(lambda: Counter())
for r in chain:
    s = r["sub_round"]
    t = tot[s]
    t["rows"] += 1
    t["kind:" + r["kind"]] += 1
    t["runs"] += f(r["est_runs"])
    t["leg_runs"] += f(r["leg_runs"])
    if r["kind"] == "plan":
        t["plan_runs"] += f(r["est_runs"])
    if r["live_stage"] not in ("none", "read-only", "") and not r["live_stage"].startswith(("none", "read-only")):
        t["prod_or_publish"] += 1
    if "named mutation -> OM-20" in r["operator_gate"]:
        t["om20_rows"] += 1
    if "IN-TICKET PAUSE" in r["operator_gate"] and "NOT pre-authorised = IN-TICKET PAUSE" not in r["operator_gate"].split("·")[0]:
        t["pauses"] += 1
    if "conditional" in r["notes"]:
        t["cond_runs"] += f(r["est_runs"])

print("sub-round | rows | kinds | eng runs (plan runs) | leg runs | prod/publish rows | OM-20 rows | in-ticket pauses")
G = Counter()
for s in CHAIN_SUBS:
    t = tot[s]
    kinds = {k[5:]: v for k, v in t.items() if k.startswith("kind:")}
    print(f"{s} | {t['rows']} | {kinds} | {t['runs']:.1f} ({t['plan_runs']:.1f}) | {t['leg_runs']:.1f} | {t['prod_or_publish']} | {t['om20_rows']} | {t['pauses']}")
    for k, v in t.items():
        G[k] += v
print(f"TOTAL | {G['rows']} | eng runs {G['runs']:.1f} (plan {G['plan_runs']:.1f}; conditional {G['cond_runs']:.1f}) | leg runs {G['leg_runs']:.1f} | prod/publish {G['prod_or_publish']} | OM-20 rows {G['om20_rows']} | pauses {G['pauses']}")
seed = [r for r in rows if r["kind"] == "seed"]
print(f"seed units {len(seed)} runs {sum(f(r['est_runs']) for r in seed):.2f}; operator {sum(1 for r in rows if r['kind']=='operator')}; later {sum(1 for r in rows if r['kind']=='later')} runs {sum(f(r['est_runs']) for r in rows if r['kind']=='later'):.1f}; markers {sum(1 for r in rows if r['kind']=='marker')}")
big = [r["id"] for r in chain if f(r["est_runs"]) > 1.0 and r["kind"] != "plan" and r["id"] != "P34.48"]
print("rows > 1.0 run (excluding fan-out PLAN rows/P34.48):", big)
gates = [(r["id"], r["row"]) for r in chain if r["kind"] == "gate"]
print("gates:", gates)
print("errors:", len(errors))
for e in errors:
    print("ERROR", e)
sys.exit(1 if errors else 0)
