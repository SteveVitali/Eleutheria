#!/usr/bin/env python3
"""Generate docs/build/reports/RIGHTS_REVIEW_INDEX.md from the live registry.

P21.1 created the index; P37.6 (ADR-235) regenerated the generator: the packet
column now follows each row's recorded ``review_packet`` field (per-source
packets and batch annexes alike), the stale "gate skipped" prose is computed
from the registry, and the regenerate pointer names this file (the retired
``.agents/scratch/`` path is gone). Read-only — nothing is flipped.
"""

from __future__ import annotations

import pathlib

from connectors.loader import is_loadable
from connectors.registry import sources
from connectors.review import flip_ready, is_flip_ready
from policy.rights import is_undetermined

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/build/reports/RIGHTS_REVIEW_INDEX.md"
RIGHTS_DIR = ROOT / "docs/build/reports/rights"
REPORTS_REL = "docs/build/reports/"

OKC_MIN = {
    "okc_procurement",
    "okc_council",
    "okcpd_policy",
    "ok_statute",
    "osm_overpass",
    "deflock_repo",
}
OKC_ALL = OKC_MIN | {"journalrecord", "oklahoman"}


def packet_path(sid: str, review_packet: str) -> str:
    if review_packet:
        rel = review_packet.removeprefix(REPORTS_REL)
        return f"[{review_packet}]({rel})"
    p = RIGHTS_DIR / f"{sid}.md"
    if p.exists():
        return f"[docs/build/reports/rights/{sid}.md](rights/{sid}.md)"
    return "— (no packet recorded)"


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
    packets = sorted(
        p.relative_to(RIGHTS_DIR).with_suffix("").as_posix()
        for p in RIGHTS_DIR.rglob("*.md")
        if p.stem != "_TEMPLATE"
    )

    lines: list[str] = []
    lines.append(
        "# RIGHTS_REVIEW_INDEX — every registered source's rights/compact/custody/gate state"
    )
    lines.append("")
    lines.append(
        "One row per registered source (SIG-LIC-001, SIG-INGEST-023/038). **Rights "
        "state**, **compact status**, and **custody posture** are read from "
        "`connectors/src/connectors/data/sources.toml`; **gate** and **flip-ready** are "
        "computed by `connectors.review` / `connectors.loader`. The **packet** column "
        "follows each row's recorded `review_packet` field — a per-source packet or a "
        "batch annex (`docs/build/reports/rights/annex/<batch>/<id>.md`); "
        "`— (no packet recorded)` marks a row whose review was never recorded in a "
        "packet. `⭐` marks the OKC minimum set (critical-path step 4). Counts are "
        "reproduced from `uv run sig-connectors validate` — do not hand-edit; "
        "regenerate."
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
        f"**Flip state this regeneration (computed):** {len(permitted)} sources carry a recorded "
        f"operator flip (`ingestion_permitted=true` — each under a recorded gate "
        f"disposition, the `FLIPPED <date> (<gate>)` marker in its notes). "
        f"{len(ready)} source(s) are flip-ready — every gate field green except the "
        f"flag itself, awaiting only the operator's HG-03 line: "
        + ", ".join(f"`{s.id}`" for s in ready)
        + f". {len(undetermined)} rows carry rights `UNDETERMINED` and fail the export "
        "gate closed until a reviewer resolves them. See "
        "`docs/build/reports/STAGE0_OUTREACH_RECORD.md` for the compact/outreach state."
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
    lines.append(
        "| ⭐ | source id | rights (SPDX) | compact | custody | flip-ready | gate | packet |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in srcs:
        star = "⭐" if s.id in OKC_MIN else ("·" if s.id in OKC_ALL else "")
        spdx = "UNDETERMINED" if is_undetermined(s.rights) else s.rights.spdx
        fr = "yes" if is_flip_ready(s) else ""
        lines.append(
            f"| {star} | `{s.id}` | {spdx} | {s.compact_status.value} | {s.custody_posture.value} "
            f"| {fr} | {gate_state(s)} | {packet_path(s.id, s.review_packet)} |"
        )
    lines.append("")
    lines.append(
        f"_Packets present: {len(packets)} under `docs/build/reports/rights/` (excludes "
        "`_TEMPLATE.md`; includes the `annex/` batch packets)._ "
        "Regenerate: `python3 docs/build/tools/gen_rights_index.py`."
    )
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({len(srcs)} source rows, {len(packets)} packets)")


if __name__ == "__main__":
    main()
