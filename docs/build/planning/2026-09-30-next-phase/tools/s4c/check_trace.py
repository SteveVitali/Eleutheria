"""S4c: every row id cited in PLAN §9.5's W2/PF/GM table and §4.4 exists in round11_plan.csv (COV-03, COV-01)."""
import csv, pathlib, re, sys
PD = pathlib.Path(__file__).resolve().parents[2]  # PD; copied from docs/build/logs/next-phase/S4c at S6
ids = {r["id"] for r in csv.DictReader((PD / "data" / "round11_plan.csv").open())}
txt = (PD / "NEXT_PHASE_PLAN.md").read_text()
sec = txt[txt.index("**Asks recorded only in META_PLAN §7.1"):txt.index("### 9.6")] + txt[txt.index("### 4.4"):txt.index("### 4.5")]
err = []
for m in re.finditer(r"\bP3[4-8]\.\d+[a-d]?\b", sec):
    tok = m.group(0)
    if tok not in ids and not any(i.startswith(tok) for i in ids):
        err.append(tok)
for r in re.findall(r"(P3[4-8]\.\d+)[–-]P?(3[4-8]\.)?(\d+)", sec):
    pass
print("cited ids checked; missing:", sorted(set(err)))
sys.exit(1 if err else 0)
