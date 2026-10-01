"""S4c 'acts on silence' check over data/decision_catalog.csv (scratch; T4 folds it into the S1b checker).

Rule (TS-02, TS-01): every decision whose answer_class is own-words or explicit (publication, rights,
Part VIII, identity, money, production authority, waivers, records) must have acts_on_silence = no.
Batch lines may adopt their recommendation on silence only if they are design/process lines with no
publication, rights, Part VIII, identity, money or production effect (recorded in the column text).
Also: no default still says 'operator-accepted' risk on silence; known acting phrases are absent.
"""

from __future__ import annotations

import csv
import pathlib
import re
import sys
from collections import Counter

PD = pathlib.Path(__file__).resolve().parents[2]  # PD; copied from docs/build/logs/next-phase/S4c at S6
rows = list(csv.DictReader((PD / "data" / "decision_catalog.csv").open()))
err = []
ACTING = [
    r"recorded as operator-accepted",
    r"^U-014 as recorded$",
    r"^record U-013 wording",
    r"passing checks only shown",
    r"placeholder 'a single independent maintainer'",
    r"GL-GATE-08 stands as recorded",
]
for r in rows:
    cls = r["answer_class"]
    if cls not in ("own-words", "explicit", "batch"):
        err.append(f"{r['dec_id']}: answer_class {cls!r}")
    if cls in ("own-words", "explicit") and r["acts_on_silence"] != "no":
        err.append(f"{r['dec_id']}: {cls} line acts on silence")
    if cls == "batch" and r["acts_on_silence"].startswith("yes") and "no publication" not in r["acts_on_silence"]:
        err.append(f"{r['dec_id']}: batch line acts on silence without the design-only declaration")
    for pat in ACTING:
        if re.search(pat, r["default_if_unanswered"]):
            err.append(f"{r['dec_id']}: acting default text remains ({pat})")
    if r["packet_line"].startswith(("A-", "C-", "S5-")) and cls == "batch":
        err.append(f"{r['dec_id']}: Part A/C/S5 line marked batch")
print("answer classes:", dict(Counter(r["answer_class"] for r in rows)))
print("packet lines:", len({r["packet_line"] for r in rows}), dict(Counter(r["packet_line"].split("-")[0] for r in {r["packet_line"]: r for r in rows}.values())))
print("acts_on_silence:", dict(Counter(r["acts_on_silence"][:3] for r in rows)))
for e in err:
    print("ERROR", e)
print("check_silence:", "FAIL" if err else "OK", f"({len(err)} errors)")
sys.exit(1 if err else 0)
