#!/usr/bin/env python3
"""Scratch: enumerate all backlog source ids (deterministic). Not committed."""
import re
import pathlib

ROOT = pathlib.Path("/Users/stevenvitali/Eleutheria")
RISK = ROOT / "docs/risk_register.md"
LD = ROOT / "docs/build/LEDGER_DEFERRALS.md"
ADR_DIR = ROOT / "docs/adr"

DEFERRED_RE = re.compile(r"Deferred|Out of scope|Scaffolded|Unverifiable|not-fully-closed|Bounded", re.I)


def risk_deferred_ids():
    ids = []
    in_deferred = False
    for line in RISK.read_text().splitlines():
        if line.startswith("### "):
            in_deferred = DEFERRED_RE.search(line) is not None
            continue
        if line.startswith("## "):
            in_deferred = False
            continue
        if in_deferred and line.startswith("|"):
            m = re.match(r"\|\s*\**\s*(RISK-[A-Za-z0-9-]+)", line)
            if m:
                ids.append(m.group(1))
    return ids


def ld_ids():
    ids = []
    for line in LD.read_text().splitlines():
        m = re.match(r"\|\s*(L[DH]-[A-Za-z0-9]+)\s*\|", line)
        if m:
            ids.append(m.group(1))
    return ids


def adr_ids():
    ids = []
    for p in sorted(ADR_DIR.glob("ADR-*.md")):
        txt = p.read_text()
        if "## Revisit trigger" in txt:
            m = re.match(r"(ADR-\d+)", p.name)
            ids.append(m.group(1))
    return ids


r = risk_deferred_ids()
l = ld_ids()
a = adr_ids()
print("RISK deferred rows:", len(r))
# dupes?
from collections import Counter
rc = Counter(r)
print("RISK dups:", {k: v for k, v in rc.items() if v > 1})
print("LD rows:", len(l))
lc = Counter(l)
print("LD dups:", {k: v for k, v in lc.items() if v > 1})
print("ADR revisit:", len(a))
print()
print("RISK:", " ".join(r))
print()
print("LD:", " ".join(l))
print()
print("ADR:", " ".join(a))
