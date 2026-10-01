#!/usr/bin/env python3
"""SEED-13e (Round-11 Stage B, T3 close-out): the requirement -> ticket index of the 310 Round-11 contracts.

Reads (all committed or in the worktree; read-only):
  docs/tickets/<row>_<id>__<slug>.md for rows 201-510 (60 full 11A contracts + 250 skeletons)
  PD/stageB/T3_contract_map.csv           row -> file
  docs/research/_meta/spec_src/*.md       requirement definitions, the §56 Owner/Also lines (via ../s13/gen_t3.py load())
  docs/research/_meta/spec_src/99c_appG_corrections.md  Appendix G.7: waivers (G.7.2), amendments (G.7.3), not amended (G.7.5)
  docs/build/COVERAGE_MATRIX.csv at HEAD  level + pre-Round-11 owning tickets (HEAD, so a concurrent edit does not leak in)

Writes `docs/tickets/REQUIREMENT_INDEX_R11.md` (`write`, default) or verifies it is current (`check`, exit 1 when stale).
The date in the header comment is `--date` (default: `date -u +%FT%TZ` at run time); `check` ignores that line.

Roles, per contract: owner (the §56 `Owner:` line, or a contract's `Owner` bullet) · delivers (a contract's
`Satisfied`, `Met at`, `Public layer reached` or `Re-verdicted` bullet) · also (`Also`) · cited (any other bullet of
the contract's requirement section, and ids inside parentheses on an owner/also/delivers bullet) · mentioned (the id
appears elsewhere in the contract). A skeleton's roles come from its `## REQ coverage` section. Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "s13"))
import gen_t3 as G  # noqa: E402  (SEED-13a's generator: spec ids, §56 owners, id expansion)

PD = HERE.parents[2]
REPO = PD.parents[3]
TICKETS = REPO / "docs" / "tickets"
OUT = TICKETS / "REQUIREMENT_INDEX_R11.md"
MAP = PD / "stageB" / "T3_contract_map.csv"
APPG = REPO / "docs" / "research" / "_meta" / "spec_src" / "99c_appG_corrections.md"
GEN_REL = "docs/build/planning/2026-09-30-next-phase/tools/s13e/req_index.py"
RANK = {"owner": 0, "delivers": 1, "also": 2, "cited": 3, "mentioned": 4}


def ids_in(text: str, sec_of: dict) -> list[str]:
    out = []
    for x in G.expand_ids(text):
        if x in sec_of and x not in out:
            out.append(x)
    return out


def label_role(label: str) -> str | None:
    lab = label.lower()
    if lab.startswith("owners confirmed"):
        return "cited"
    if lab.startswith("owner"):
        return "owner"
    if lab.startswith("also"):
        return "also"
    if lab.startswith(("satisfied", "met at", "public layer reached", "re-verdicted")):
        return "delivers"
    if lab.startswith(("written here", "later-family")):
        return None
    return "cited"


def contract_roles(text: str, sec_of: dict) -> dict[str, str]:
    """id -> best role in this contract."""
    roles: dict[str, str] = {}

    def put(i: str, r: str) -> None:
        if i not in roles or RANK[r] < RANK[roles[i]]:
            roles[i] = r

    m = re.search(r"^## (Requirement IDs[^\n]*|REQ coverage)\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    sec = m.group(2) if m else ""
    for line in sec.splitlines():
        lm = re.match(r"^- \*\*(.+?):\*\*\s*(.*)$", line) or re.match(r"^- ([A-Z][^:]{2,80}?):\s*(.*)$", line)
        if not lm:
            continue
        role = label_role(lm.group(1))
        if role is None:
            continue
        body = lm.group(2)
        outside = re.sub(r"\([^()]*\)", " ", body)
        inside = " ".join(re.findall(r"\(([^()]*)\)", body))
        for i in ids_in(outside, sec_of):
            put(i, role)
        for i in ids_in(inside, sec_of):
            put(i, "cited")
    for i in ids_in(text, sec_of):
        put(i, "mentioned")
    return roles


def appendix_g7(sec_of: dict) -> list[dict]:
    """Rows of G.7.2 / G.7.3 / G.7.5 with their ids and ADRs."""
    text = APPG.read_text(encoding="utf-8")
    start = text.index("## G.7 ")
    g7 = text[start:]
    out = []
    part = ""
    for line in g7.splitlines():
        h = re.match(r"^### (G\.7\.\d)", line)
        if h:
            part = h.group(1)
            continue
        if not line.startswith("|") or line.startswith("|---") or part not in ("G.7.2", "G.7.3", "G.7.5"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] in ("#", "Item"):
            continue
        if part == "G.7.5":
            ids = ids_in(cells[0], sec_of)
            kind, ref, adrs = "checked, not amended — the requirement stands", "G.7.5", re.findall(r"ADR-\d{3}", line)
            auth = "—"
        else:
            ids = ids_in(cells[1], sec_of)
            ref = cells[0]
            adrs = re.findall(r"ADR-\d{3}", cells[-1])
            auth = cells[-1] if not adrs else "—"
            if part == "G.7.2":
                kind = "WAIVED (clause): " + cells[2]
            elif ref == "R11-A15":
                kind = "owed later-phase, not waived (outreach timing)"
            else:
                kind = "AMENDED (no MUST weakened)"
        for i in ids:
            out.append({"id": i, "ref": ref, "part": part, "kind": kind, "adrs": sorted(set(adrs)), "auth": auth})
    return out


def coverage_head() -> dict[str, dict]:
    raw = subprocess.run(["git", "show", "HEAD:docs/build/COVERAGE_MATRIX.csv"], cwd=REPO, capture_output=True,
                         text=True, check=True).stdout
    return {r["id"]: r for r in csv.DictReader(io.StringIO(raw))}


def level_of(i: str, cov: dict) -> str:
    if i in cov and cov[i].get("level"):
        return cov[i]["level"]
    return "—"


def short(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def build(date: str) -> str:
    D = G.load()
    sec_of = D["sec_of"]
    rows = [r for r in csv.DictReader(MAP.open(encoding="utf-8")) if int(r["row"]) >= 201]
    cov = coverage_head()
    ix: dict[str, dict[str, list[str]]] = {}
    kinds = {"full": 0, "skeleton": 0}
    rowno = {}
    for r in rows:
        p = TICKETS / r["file"]
        text = p.read_text(encoding="utf-8")
        sk = G.is_skeleton(p)
        kinds["skeleton" if sk else "full"] += 1
        rowno[r["id"]] = r["row"]
        for i, role in contract_roles(text, sec_of).items():
            ix.setdefault(i, {k: [] for k in RANK})[role].append(r["id"])
    owner56 = {k: G.expand_owner_ids(v) for k, v in D["owner"].items()}
    also56 = {k: G.expand_owner_ids(v) for k, v in D["also"].items()}
    g7 = appendix_g7(sec_of)
    g7_of: dict[str, list[dict]] = {}
    for g in g7:
        g7_of.setdefault(g["id"], []).append(g)
    chain_ids = {r["id"] for r in rows}

    def ref(t: str) -> str:
        return f"{t} ({rowno[t]})" if t in rowno else t

    def flags(i: str) -> str:
        fl = []
        for g in g7_of.get(i, []):
            fl.append(f"{g['ref']} {g['kind'].split(':')[0]}" + (f" — {', '.join(g['adrs'])}" if g["adrs"] else ""))
        return "; ".join(fl)

    L: list[str] = []
    w = L.append
    w(f"<!-- Generated {date} by {GEN_REL} (SEED-13e, Round-11 Stage B T3 close-out); regenerate, do not hand-edit. "
      "Planning, not execution evidence. -->")
    w("# Round-11 requirement → ticket index (rows 201–510)")
    w("")
    w("A companion of `00_MANIFEST.md` (its `## Requirement-ID → ticket index` points here). It maps every requirement id "
      "cited by the 310 Round-11 chain contracts — the 60 full 11A contracts and the 250 `Kind: skeleton` contracts of "
      "11B–tail — to the rows that own, deliver, extend or cite it, checks the 62 spec §56 ids against their `Owner:` lines, "
      "and lists every waived or amended id with its ADR (spec Appendix G.7). Skeleton rows name only the ids the plan row, "
      "the catalog or a Stage-B carry item gave them; **PLAN-11B, PLAN-11C and PLAN-11D extend this index** when they write "
      "their sub-round's contracts (re-run the generator; their own requirement-index deliverables point here). "
      "Requirement status stays in `docs/build/COVERAGE_MATRIX.csv` and the coverage-assessment events — nothing here is a "
      "verdict.")
    w("")
    w("**Roles.** *owner* — the spec §56 `Owner:` row or a contract's `Owner` bullet; *delivers* — a contract's "
      "`Satisfied`/`Met at`/`Public layer reached`/`Re-verdicted` bullet (part of the requirement, at the layer the "
      "contract states); *also* — §56 `Also:` or the contract's `Also` bullet; *cited* — any other requirement bullet; "
      "*mentioned* — the id appears elsewhere in the contract. Rows are written `<id> (<row>)`.")
    w("")
    n56 = len(D["owner"])
    seed_owned = sorted([k for k, v in owner56.items() if not any(o in chain_ids for o in v)], key=G.idkey)
    missing_owner_row = []
    owner_not_listed = []
    for k, v in sorted(owner56.items(), key=lambda kv: G.idkey(kv[0])):
        for o in v:
            if o.startswith("SEED-"):
                continue
            if o not in chain_ids:
                missing_owner_row.append((k, o))
            elif o not in ix.get(k, {}).get("owner", []):
                owner_not_listed.append((k, o))
    pre = sorted([i for i in ix if i not in D["owner"]], key=G.idkey)
    pre_no_r11 = [i for i in pre if not ix[i]["owner"] and not ix[i]["delivers"]]
    waived = sorted({g["id"] for g in g7 if g["part"] == "G.7.2"}, key=G.idkey)
    amended = sorted({g["id"] for g in g7 if g["part"] == "G.7.3"}, key=G.idkey)
    stands = sorted({g["id"] for g in g7 if g["part"] == "G.7.5"}, key=G.idkey)
    w("## Summary")
    w("")
    w(f"- Contracts scanned: **{len(rows)}** ({kinds['full']} full, {kinds['skeleton']} skeleton).")
    uncited56 = sorted([k for k in D["owner"] if k not in ix], key=G.idkey)
    w(f"- Distinct requirement ids cited: **{len(ix)}** — {len([i for i in ix if i in D['owner']])} of the {n56} §56 ids "
      f"and {len(pre)} ids defined before Round 11." + (f" §56 ids no contract cites: {', '.join(uncited56)} "
      "(seed-owned; see §1)." if uncited56 else ""))
    w(f"- §56 ids with **no chain-row owner**: {len(seed_owned)} — " + ", ".join(
        f"{k} (owner {', '.join(owner56[k])})" for k in seed_owned) + " — owned by Stage-B seed units, not by a "
      "Round-11 row (spec §56.1 allows a seed-unit owner); they are verdicted at T4/T6 from the seed's own evidence.")
    w(f"- §56 owner names that are not chain rows: {len(missing_owner_row)}"
      + ("" if not missing_owner_row else " — " + ", ".join(f"{k}→{o}" for k, o in missing_owner_row)) + ".")
    w(f"- §56 owner rows whose contract does not (yet) list the id as owned: {len(owner_not_listed)}"
      + ("" if not owner_not_listed else " — " + ", ".join(f"{k}→{ref(o)}" for k, o in owner_not_listed)) + ".")
    w(f"- Ids defined before Round 11 that no Round-11 row owns or delivers (cited only): {len(pre_no_r11)} — their "
      "owners are the tickets the coverage matrix names (column *matrix `owning_tickets`* in §3, read at HEAD).")
    w(f"- Appendix G.7: {len(waived)} waived ids (G.7.2), {len(amended)} amended ids (G.7.3, incl. the outreach set owed "
      f"later-phase, R11-A15), {len(stands)} ids checked and deliberately not amended (G.7.5; the requirement stands) — table §2.")
    w("")
    w("## 1. Spec §56 ids (62) — owner check")
    w("")
    w("| id | level | §56 Owner | §56 Also | owner contract lists it | other Round-11 rows | flag |")
    w("|---|---|---|---|---|---|---|")
    confirm = {"SIG-OPS-007", "SIG-SEC-008", "SIG-SEC-009", "SIG-CONF-010"}
    for k in sorted(D["owner"], key=G.idkey):
        e = ix.get(k, {r: [] for r in RANK})
        owners = owner56[k]
        listed = "seed unit" if all(o.startswith("SEED-") for o in owners) else (
            "yes" if all(o in e["owner"] for o in owners if not o.startswith("SEED-")) else "no")
        others = [f"{ref(t)} {role}" for role in ("owner", "delivers", "also", "cited", "mentioned")
                  for t in e[role] if t not in owners]
        fl = []
        if k in seed_owned:
            fl.append("no chain-row owner (seed unit)")
        if k in confirm:
            fl.append("owner was an agent assignment (T1 map 'confirm at T3/T4'); confirmed at T3 — agent reading, "
                      "the PLAN row re-confirms when it writes the contract")
        if not e["owner"] and not any(o.startswith("SEED-") for o in owners):
            fl.append("owner contract is a skeleton without an Owner line" if listed == "no" else "")
        if flags(k):
            fl.append(flags(k))
        w(f"| {k} | {level_of(k, cov)} | {', '.join(ref(o) for o in owners)} | "
          f"{', '.join(ref(o) for o in also56.get(k, [])) or '—'} | {listed} | {short('; '.join(others), 220) or '—'} | "
          f"{'; '.join(x for x in fl if x) or '—'} |")
    w("")
    w("## 2. Waived and amended ids (spec Appendix G.7) and the Round-11 rows that touch them")
    w("")
    w("A waived clause keeps its requirement text and a dated waiver note in its owning section; the coverage verdict is "
      "`WAIVED(ADR)` for the clause only (SIG-ENG-041). An amendment adds and removes no obligation; a G.7.5 item was "
      "checked and deliberately not amended (a draft that would weaken a MUST was withheld) — the requirement stands as "
      "written.")
    w("")
    w("| id | G.7 row | disposition | ADR | Round-11 rows (role) |")
    w("|---|---|---|---|---|")
    for g in sorted(g7, key=lambda x: (G.idkey(x["id"]), x["ref"])):
        e = ix.get(g["id"])
        touched = "—" if not e else short("; ".join(f"{ref(t)} {role}" for role in RANK for t in e[role]), 260)
        adr = ", ".join(g["adrs"]) or (f"none — authority: {short(g['auth'], 60)}" if g["auth"] != "—" else "—")
        w(f"| {g['id']} | {g['ref']} | {short(g['kind'], 150)} | {adr} | {touched} |")
    w("")
    w("## 3. Full index — every requirement id cited by a Round-11 contract")
    w("")
    w("| id | level | owner / delivering row(s) | also | cited / mentioned by | matrix `owning_tickets` (HEAD; cited-only ids) | G.7 |")
    w("|---|---|---|---|---|---|---|")
    for i in sorted(ix, key=G.idkey):
        e = ix[i]
        own = [ref(t) + ("" if t in owner56.get(i, []) or i not in owner56 else " (contract)") for t in e["owner"]]
        if i in owner56:
            own = [ref(o) + " (§56)" for o in owner56[i]] + [x for x in own if "(contract)" in x]
        own += [ref(t) + " (delivers)" for t in e["delivers"]]
        cites = [ref(t) for t in e["cited"]] + [ref(t) + "*" for t in e["mentioned"]]
        mo = "—"
        if i not in owner56 and not e["owner"] and not e["delivers"]:
            mo = (cov.get(i, {}).get("owning_tickets") or "—").replace(";", ", ")
        w(f"| {i} | {level_of(i, cov)} | {', '.join(own) or '—'} | {', '.join(ref(t) for t in e['also']) or '—'} | "
          f"{short(', '.join(cites), 300) or '—'} | {short(mo, 80)} | {short(flags(i), 120) or '—'} |")
    w("")
    w("`*` = mentioned outside the contract's requirement section. Ids written as later-family drafts (SIG-TRANSP-D…, "
      "UXR-…, SIG-EVUI-D…, SIG-WATCH-D…) are not requirement ids yet and are not indexed; PLAN-11B (SIG-TRANSP) and "
      "PLAN-11C (the K13 set) assign their final ids and extend this index.")
    w("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", default="write", choices=["write", "check"])
    ap.add_argument("--date", default=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    a = ap.parse_args()
    text = build(a.date)
    if a.cmd == "check":
        cur = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        strip = lambda s: "\n".join(s.splitlines()[1:])  # noqa: E731  (the first line carries the generation date)
        ok = strip(cur) == strip(text)
        print("req_index: current" if ok else "req_index: STALE — re-run `req_index.py write`")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({len(text.encode('utf-8'))} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
