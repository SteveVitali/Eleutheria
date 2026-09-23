#!/usr/bin/env python3
"""Generate docs/build/RIGHTS_REVIEW_INDEX.md from the live registry (P21.1, scratch)."""

from __future__ import annotations

import pathlib

from connectors.loader import is_loadable
from connectors.registry import sources
from connectors.review import flip_ready, has_rights_block, is_flip_ready
from policy.rights import is_undetermined

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/build/RIGHTS_REVIEW_INDEX.md"
RIGHTS_DIR = ROOT / "docs/build/rights"

OKC_MIN = {"okc_procurement", "okc_council", "okcpd_policy", "ok_statute", "osm_overpass", "deflock_repo"}
OKC_ALL = OKC_MIN | {"journalrecord", "oklahoman"}


def packet_path(sid: str) -> str:
    p = RIGHTS_DIR / f"{sid}.md"
    if p.exists():
        return f"[docs/build/rights/{sid}.md](rights/{sid}.md)"
    return "— (P22+ backlog)"


def gate_state(rec) -> str:
    if is_loadable(rec):
        return "LOADABLE"
    if is_flip_ready(rec):
        return "flip-ready"
    return "REFUSED"


def main() -> None:
    srcs = sources()
    undetermined = [s for s in srcs if is_undetermined(s.rights)]
    permitted = [s for s in srcs if s.ingestion_permitted]
    loadable = [s for s in srcs if is_loadable(s)]
    ready = flip_ready(srcs)
    packets = sorted(p.stem for p in RIGHTS_DIR.glob("*.md") if p.stem != "_TEMPLATE")

    lines: list[str] = []
    lines.append("# RIGHTS_REVIEW_INDEX — every registered source's rights/compact/custody/gate state (P21.1)")
    lines.append("")
    lines.append(
        "One row per registered source (SIG-LIC-001, SIG-INGEST-023/038). **Rights state**, "
        "**compact status**, and **custody posture** are read from "
        "`connectors/src/connectors/data/sources.toml`; **gate** and **flip-ready** are computed by "
        "`connectors.review` / `connectors.loader`. A **packet** column links the rights-review packet "
        "for the 27 sources on the critical path (`docs/build/rights/<id>.md`); the rest are P22+ "
        "backlog. `⭐` marks the OKC minimum set (critical-path step 4). Counts are reproduced from "
        "`uv run sig-connectors validate` — do not hand-edit; regenerate."
    )
    lines.append("")
    lines.append("## Counts (from `sig-connectors validate`)")
    lines.append("")
    lines.append("```")
    lines.append(f"registered sources: {len(srcs)}")
    lines.append(f"  rights UNDETERMINED (export gate fails closed): {len(undetermined)}")
    lines.append(f"  ingestion_permitted=true: {len(permitted)}")
    lines.append(f"  loadable now (permitted + compact + custody): {len(loadable)}")
    lines.append(f"  flip-ready (rights + compact + custody, flag false): {len(ready)}")
    lines.append("```")
    lines.append("")
    lines.append(
        "**Gate skipped this run (HG-03/HG-04 = SKIP):** nothing was flipped, so `loadable now: 0`. "
        "The 18 flip-ready sources are unblockable by an operator flip + recorded review metadata; the "
        "6 OKC rows + `usaspending` + `deflock` + `civicclerk` are UNDETERMINED pending review. See "
        "`docs/build/STAGE0_OUTREACH_RECORD.md` for the compact/outreach state."
    )
    lines.append("")
    lines.append("## OKC minimum set (critical-path step 4)")
    lines.append("")
    lines.append(
        "`⭐` " + ", ".join(f"`{s}`" for s in sorted(OKC_MIN)) + " — government records (R1/R2) + "
        "the ODbL/community OSM route. News rows (`journalrecord`, `oklahoman`) are LINK-posture "
        "candidates (link out, never re-host)."
    )
    lines.append("")
    lines.append("## All sources")
    lines.append("")
    lines.append("| ⭐ | source id | rights (SPDX) | compact | custody | flip-ready | gate | packet |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in srcs:
        star = "⭐" if s.id in OKC_MIN else ("·" if s.id in OKC_ALL else "")
        spdx = "UNDETERMINED" if is_undetermined(s.rights) else s.rights.spdx
        fr = "yes" if is_flip_ready(s) else ""
        lines.append(
            f"| {star} | `{s.id}` | {spdx} | {s.compact_status.value} | {s.custody_posture.value} "
            f"| {fr} | {gate_state(s)} | {packet_path(s.id)} |"
        )
    lines.append("")
    lines.append(f"_Packets present: {len(packets)} (excludes `_TEMPLATE.md`)._ "
                 "Regenerate: `python .agents/scratch/tools/gen_rights_index.py`.")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({len(srcs)} source rows, {len(packets)} packets)")


if __name__ == "__main__":
    main()
