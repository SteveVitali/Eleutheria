#!/usr/bin/env python3
"""SEED-13e: after a contract's Load list or body is edited, re-derive its Load figures — the contract's own entry
(= its file size), the header `Load (token-counted…)` line and the `Token count` line — iterating to a fixed point.
Counter `utf8-bytes÷3 | ÷4` (floor), the entry figures being the `N B` numbers after each entry's last ` — `.
Usage: fix_load_totals.py <contract.md> [...]   (stdlib; edits only the named files)"""
from __future__ import annotations

import pathlib
import re
import sys

NUM = re.compile(r"(\d[\d,]*) B(?![A-Za-z])")


def fmt(n: int) -> str:
    return f"{n:,}"


def total(text: str) -> int:
    sec = re.search(r"^## Load[^\n]*\n(.*?)(?=^## )", text, re.S | re.M)
    tot = 0
    for ln in (sec.group(1) if sec else "").splitlines():
        if ln.startswith("- "):
            tot += sum(int(x.replace(",", "")) for x in NUM.findall(ln.rsplit(" — ", 1)[-1]))
    return tot


def fix(p: pathlib.Path) -> tuple[int, int]:
    self_re = re.compile(r"^(- `docs/tickets/" + re.escape(p.name) + r"` — this contract — )([\d,]+) B$", re.M)
    for _ in range(10):
        t = p.read_text(encoding="utf-8")
        size = len(t.encode("utf-8"))
        t2 = self_re.sub(lambda m: m.group(1) + fmt(size) + " B", t, count=1)
        tot = total(t2)
        t2 = re.sub(r"(\*\*Load \(token-counted[^*]*\*\*\s*)[\d,]+ B → ≈ [\d,]+ tokens \(bytes÷3\) · ≈ [\d,]+ \(bytes÷4\)",
                    lambda m: f"{m.group(1)}{fmt(tot)} B → ≈ {fmt(tot // 3)} tokens (bytes÷3) · ≈ {fmt(tot // 4)} (bytes÷4)",
                    t2, count=1)
        t2 = re.sub(r"(\*\*Token count \(counter[^\n]*?\*\*\s*)[\d,]+ B → ≈ [\d,]+ \(÷3\) · ≈ [\d,]+ \(÷4\)",
                    lambda m: f"{m.group(1)}{fmt(tot)} B → ≈ {fmt(tot // 3)} (÷3) · ≈ {fmt(tot // 4)} (÷4)",
                    t2, count=1)
        if t2 == t:
            return size, tot
        p.write_text(t2, encoding="utf-8")
    raise SystemExit(f"{p.name}: no fixed point")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        size, tot = fix(pathlib.Path(a))
        print(f"{pathlib.Path(a).name}: contract {size:,} B; Load {tot:,} B → ≈ {tot // 3:,} (÷3) · ≈ {tot // 4:,} (÷4)")
