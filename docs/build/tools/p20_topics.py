#!/usr/bin/env python3
import re, pathlib
ROOT = pathlib.Path("/Users/stevenvitali/Eleutheria")
RISK = ROOT / "docs/risk_register.md"
ADR_DIR = ROOT / "docs/adr"
DEFERRED_RE = re.compile(r"Deferred|Out of scope|Scaffolded|Unverifiable|not-fully-closed|Bounded", re.I)

in_def=False; phase=""
for line in RISK.read_text().splitlines():
    if line.startswith("## "):
        phase=line[3:].strip(); in_def=False; continue
    if line.startswith("### "):
        in_def=DEFERRED_RE.search(line) is not None; continue
    if in_def and line.startswith("|"):
        cells=[c.strip() for c in line.strip().strip("|").split("|")]
        m=re.match(r"\**\s*(RISK-[A-Za-z0-9-]+)",cells[0])
        if m and len(cells)>=2:
            topic=cells[1]
            topic=re.sub(r"\s+"," ",topic)[:110]
            print(f"{m.group(1)}\t{topic}")
