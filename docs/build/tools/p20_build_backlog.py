#!/usr/bin/env python3
"""Generate BACKLOG.csv / BACKLOG.md / BACKLOG_THEMES.md and patch risk_register.md
cross-refs. Scratch tool (not committed). Deterministic; asserts every source id
appears in exactly one item. Run from repo root."""
from __future__ import annotations
import csv, io, pathlib, re, sys

ROOT = pathlib.Path("/Users/stevenvitali/Eleutheria")
BUILD = ROOT / "docs/build"
RISK = ROOT / "docs/risk_register.md"

# ---- items: (bl_id, title, type, package, blocks, landing, gate, size, status, theme, [sources]) ----
THEMES = {
    "T1": "Persistence of the annotation layer",
    "T2": "Live wiring & connectors",
    "T3": "Rights, compact & legal",
    "T4": "Publication surfaces",
    "T5": "Infra & cost",
    "T6": "Spec drift",
    "T7": "Docs hygiene",
    "T8": "Contribution-back",
    "T9": "International & Stage-5",
    "T10": "Accepted by design",
}

ITEMS = [
 ("BL-001","Human-judgement gates satisfied by tested deterministic gate","process","policy","","accepted","","S","accepted","T10",
   ["RISK-P0-05","RISK-P0-06","RISK-P5-06"]),
 ("BL-002","Foundational tech-stack/tooling ADRs — decision stands, monitor revisit trigger","process","docs","","accepted","","S","accepted","T10",
   ["ADR-001","ADR-002","ADR-003","ADR-004","ADR-005","ADR-006","ADR-007","ADR-008","ADR-009","ADR-010","ADR-011","ADR-012","ADR-013","ADR-014","ADR-016","ADR-017","ADR-019","ADR-020","ADR-021","ADR-023","ADR-024","ADR-025","ADR-029","ADR-044","ADR-045","ADR-058"]),
 ("BL-003","claim table partitioning (deferred; FK contract kept)","schema-refinement","db","","P22+","","L","open","T5",
   ["LD-F01","ADR-022"]),
 ("BL-004","Persist reconcile/inference/tasks/contradiction layer to PG (compute-on-read -> materialised)","deferred-feature","reconcile","OKC-live","P21.2","","L","open","T1",
   ["LD-V05","LD-D07","RISK-P8-09","RISK-P10-08","RISK-P10-13","RISK-P12-13","ADR-036","ADR-037","ADR-038","ADR-039","ADR-040","ADR-031","ADR-059"]),
 ("BL-005","Persist contributor system to PG (tiers/submissions/revert/anomaly)","deferred-feature","tasks","","P21.2","","M","open","T1",
   ["RISK-P16-07","LD-F10","ADR-054"]),
 ("BL-006","Persist identity registries and mint surrogate entity_id end-to-end into PG","deferred-feature","resolution","","P21.2","","M","open","T1",
   ["RISK-P3-03"]),
 ("BL-007","Wire web surfaces to the live /v1 API/exports (replace committed TS fixtures)","deferred-feature","web","OKC-live","P21.4","","L","open","T4",
   ["RISK-P15-07","RISK-P15-08","RISK-P15-13","RISK-P15-14","RISK-P15-20","RISK-P15-25","RISK-P15-26","RISK-P15-31","RISK-P15-32","LD-V08","RISK-P2-14","RISK-P9-08","RISK-P13-08","RISK-P13-09","RISK-P13-13","ADR-049","ADR-050","ADR-052","ADR-053","ADR-032","ADR-046"]),
 ("BL-008","Project bulk exports / licence compartments from a live ReadStore","deferred-feature","exports","OKC-live","P21.4","","M","open","T4",
   ["RISK-P14-08","RISK-P14-18"]),
 ("BL-009","Curation/review web UI + asset-promotion service","deferred-feature","web","","P21.6","","M","open","T4",
   ["LD-F05","LD-H04","LD-D04","ADR-030"]),
 ("BL-010","Interactive MapLibre map vs zero-JS static PMTiles (spec amendment A1)","docs-drift","web","","P20.2","","M","open","T6",
   ["ADR-051","ADR-018","LD-F09","LD-D11","RISK-P15-21"]),
 ("BL-011","ADR Appendix-F <-> docs/adr numbering reconciliation","docs-drift","docs","","P20.2","","S","open","T6",
   ["LD-X04","LD-D03"]),
 ("BL-012","Absence-kind not_researched spec wording (SIG-RECON, §32.2)","docs-drift","docs","","P20.2","","S","open","T6",
   ["LD-F14","LD-D08"]),
 ("BL-013","verify-gen / RDF-canonicalisation semantics documented (AGENTS.md gotchas)","docs-drift","docs","","accepted","","S","closed","T7",
   ["LD-X03","LD-X07"]),
 ("BL-014","Ledger hygiene + manifest/template fixes + composed-stack confirmations (P19.1/P19.2)","process","docs","","closed-by:P19.4","","S","closed","T7",
   ["LH-01","LH-02","LH-03","LH-04","LH-05","LH-06","LH-07","LH-08","LH-09","LH-10","LH-11","LH-12","LH-13","LH-14","LH-15","LD-X01","LD-X02","LD-X06","LD-X08","LD-X09","LD-X10","LD-X11"]),
 ("BL-015","DB-backed ReadStore + PgClaimSink over the PG spine","deferred-feature","api","","closed-by:P19.4","","L","closed","T2",
   ["LD-F06","LD-V06","ADR-047","RISK-P14-07","RISK-P6-07"]),
 ("BL-016","Handoff seams & composed-stack verification confirmed (P19.2/P19.3/P19.4)","process","docs","","closed-by:P19.4","","M","closed","T2",
   ["LD-V01","LD-V02","LD-V11","LD-H01","LD-H03","LD-H05","LD-H06","LD-H07","LD-H10","LD-H13","LD-F12","LD-F13","LD-F18","RISK-P11-13"]),
 ("BL-017","ER over PG + PG review queue (SIG-IDENT)","deferred-feature","resolution","","closed-by:P19.5","","L","closed","T2",
   ["LD-F04","LD-V04","RISK-P5-04","ADR-060","ADR-061"]),
 ("BL-018","Export gate honours derivative_permitted (SIG-LIC-004/010)","defect","policy","","closed-by:P19.5","","M","closed","T2",
   ["LD-F08","LD-H09"]),
 ("BL-019","Jurisdiction-conditional web render at build time (BCP-47, GDPR withholding)","deferred-feature","web","","closed-by:P19.5","","M","closed","T4",
   ["LD-V12","LD-H11"]),
 ("BL-020","inference CLI wired (coverage/access-paths/completeness/freshness)","deferred-feature","inference","","closed-by:P19.5","","S","closed","T2",
   ["LD-F15"]),
 ("BL-021","P08.1 resolver ADR-060 + risk-register section (retro, §51.3)","docs-drift","docs","","closed-by:P19.5","","S","closed","T7",
   ["LD-X05"]),
 ("BL-022","Analytics-boundary post-hoc hardening documented (ADR-044 amend)","docs-drift","db","","closed-by:P19.5","","S","closed","T7",
   ["LD-D14"]),
 ("BL-023","Live HTTP transports + OCFL CaptureStore for the connector family","deferred-feature","connectors","OKC-live","P21.3","HG-03","L","open","T2",
   ["RISK-P4-04","RISK-P4-05","RISK-P4-06","RISK-P4-10","RISK-P7-15","LD-F03","LD-V03","ADR-026","ADR-027","ADR-028","ADR-042","ADR-034","ADR-035","ADR-043"]),
 ("BL-024","Live token mint + real FETCH (MuckRock/records/procurement/flock/slice)","deferred-feature","connectors","OKC-live","P21.3","HG-09","M","open","T2",
   ["RISK-P7-10","RISK-P7-16","LD-F16","RISK-P11-05","RISK-P11-15","RISK-P13-07","RISK-P6-06"]),
 ("BL-025","Concrete extraction engines (parser layers 3-5, OCR) + model client","deferred-feature","parsing","","P21.3","","L","open","T2",
   ["RISK-P7-05","RISK-P7-11","RISK-P7-17","RISK-P5-10","LD-F17","ADR-033","RISK-P7-06"]),
 ("BL-026","Live-connector WACZ per PR + byte-identical reproducibility test (SIG-EVID-017)","deferred-feature","evidence","","P21.3","","M","open","T2",
   ["LD-F02","LD-H02","RISK-P2-09","RISK-P2-10","RISK-P11-07"]),
 ("BL-027","Persist reconcile-workflow outputs (contradictions, sharing edges, tasks, access edges)","deferred-feature","reconcile","","P21.2","","M","open","T1",
   ["RISK-P11-06","RISK-P11-14","RISK-P12-14","RISK-P10-14","RISK-P10-07","RISK-P12-06","RISK-P12-07"]),
 ("BL-028","Records-request filing/response backend (template outcome log fed live)","deferred-feature","tasks","","P22+","","M","open","T2",
   ["ADR-041","RISK-P10-18","RISK-P10-17"]),
 ("BL-029","Zenodo live deposit + object store + rendered vector tiles (PMTiles bodies)","external-dep","exports","","P21.5","HG-07","L","open","T5",
   ["RISK-P14-16","LD-V07","ADR-048","RISK-P14-17","LD-F07","LD-H08","LD-D09","ADR-015"]),
 ("BL-030","Zero-cost / degraded-but-alive keepalive tested (SIG-GOV-021)","operational-prereq","ops","","P21.5","","M","open","T5",
   ["RISK-P0-12","LD-P07"]),
 ("BL-031","API rate-limit enforcement + GraphQL (deferred SHOULDs)","deferred-feature","api","","P22+","","S","open","T4",
   ["RISK-P14-09","RISK-P14-10"]),
 ("BL-032","Per-source rights review + registry completion (flip ingestion_permitted)","rights/legal","connectors","OKC-live","P21.1","HG-03","L","open","T3",
   ["RISK-P0-19","LD-P05"]),
 ("BL-033","Stage-0 outreach / Eyes-on-Flock archival succession recorded","rights/legal","connectors","OKC-live","P21.1","HG-04","M","open","T3",
   ["RISK-P0-20","LD-P01"]),
 ("BL-034","Legal home + counsel launch prerequisites","rights/legal","docs","OKC-publish","human-gate:HG-01","HG-01","M","open","T3",
   ["LD-P02"]),
 ("BL-035","Counsel disposition: ODbL 4.4(b) derivative / know-your-rights guidance","rights/legal","docs","OKC-publish","human-gate:HG-02","HG-02","M","open","T3",
   ["RISK-P16-16","RISK-P0-11"]),
 ("BL-036","Operating governance: board, Code of Conduct, funding policy","operational-prereq","docs","OKC-publish","human-gate:HG-11","HG-11","M","open","T3",
   ["RISK-P0-10"]),
 ("BL-037","Infra accounts (Zenodo concept DOI, object store, Docker CI runner)","external-dep","ops","","human-gate:HG-07","HG-07","S","open","T5",
   ["LD-P06"]),
 ("BL-038","OSM/MapRoulette accounts + Organised-Editing activity registration","external-dep","tasks","","human-gate:HG-08","HG-08","S","open","T8",
   ["RISK-P16-13","LD-P04"]),
 ("BL-039","Live MapRoulette client + OSM changeset feed + published leverage metric","deferred-feature","tasks","","P21.7","HG-08","L","open","T8",
   ["RISK-P16-14","RISK-P16-15","LD-F11","ADR-055","RISK-P18-14","LD-V09"]),
 ("BL-040","Moderated usability study (>=5 ontology-naive contributors)","operational-prereq","docs","","P21.7","HG-10","M","open","T8",
   ["RISK-P16-06","LD-P03"]),
 ("BL-041","Contributor onboarding: jurisdiction-aware know-your-rights shown","deferred-feature","web","","P21.7","","S","open","T8",
   ["RISK-P16-08"]),
 ("BL-042","Data Driven + coarse-international + France/Belgium live connectors","deferred-feature","connectors","","P21.8","HG-03","L","open","T9",
   ["RISK-P18-04","RISK-P18-05","RISK-P18-06","RISK-P18-13","ADR-056","ADR-057"]),
 ("BL-043","Stage-5 pathway connectors persisted to the claim spine","deferred-feature","connectors","","P21.9","HG-03","L","open","T9",
   ["RISK-P17-02","RISK-P17-03","RISK-P17-08","RISK-P17-09","RISK-P17-13","RISK-P17-14","LD-H12","LD-V10"]),
 ("BL-044","Data completeness as connectors land (crosswalks, vocab, gold sets, category maps)","deferred-feature","connectors","","P21.3","","M","open","T2",
   ["RISK-P1-02","RISK-P3-02","RISK-P3-07","RISK-P3-09","RISK-P4-09","RISK-P5-05","RISK-P5-11"]),
 ("BL-045","Ruleset calibration once real data exists (volatility, directness matrix, Atlas supersession)","schema-refinement","reconcile","","P22+","","M","open","T6",
   ["RISK-P1-03","RISK-P1-04","RISK-P4-08"]),
 ("BL-046","Dereferenceable /id/<type>/<uuid> endpoint + ODbL physical_asset table (§42.3)","deferred-feature","api","","P21.4","","M","open","T4",
   ["RISK-P3-08","RISK-P4-07"]),
 ("BL-047","Schema cleanup: legacy succession slots vs reified OrganizationRelationship","schema-refinement","db","","P22+","","S","open","T6",
   ["RISK-P3-04"]),
 ("BL-048","Determinism / whole-graph audit CI jobs (resolution rebuild, TI-6/7 audit)","process","reconcile","","P22+","","M","open","T1",
   ["RISK-P2-03","RISK-P2-15"]),
 ("BL-049","Generate physical DDL from LinkML (ontology/db seam, SIG-STORE-045)","schema-refinement","db","","P22+","","L","open","T6",
   ["RISK-P2-04"]),
 ("BL-050","Recorded ADR-sanctioned spec deviations — no further action","process","docs","","accepted","","S","accepted","T10",
   ["LD-D01","LD-D02","LD-D05","LD-D06","LD-D10","LD-D12","LD-D13"]),
]

COLUMNS = ["bl_id","title","type","sources","req_ids","package","blocks","landing","gate","size","status"]

# req_ids per item (light, from cited spec ids); optional
REQ = {
 "BL-004":"SIG-EPIS-018 SIG-RECON-039/040","BL-005":"SIG-CONTRIB","BL-006":"SIG-IDENT-020/025",
 "BL-007":"SIG-PUB-007 SIG-UI-010","BL-008":"SIG-INGEST-016 SIG-LIC-010","BL-009":"SIG-PUB-012",
 "BL-010":"SIG-UI-038","BL-015":"SIG-API-001/002","BL-017":"SIG-IDENT-020/021/025/026",
 "BL-018":"SIG-LIC-004/010","BL-023":"SIG-INGEST-001","BL-030":"SIG-GOV-021","BL-032":"SIG-LIC-001 SIG-INGEST-038",
 "BL-033":"SIG-CONTRIB-012/012a","BL-042":"SIG-INGEST-043 SIG-INGEST-049","BL-043":"SIG-INGEST",
}


def build():
    seen = {}
    rows = []
    for (bl,title,typ,pkg,blocks,landing,gate,size,status,theme,srcs) in ITEMS:
        for s in srcs:
            if s in seen:
                sys.exit(f"DUPLICATE source {s} in {bl} and {seen[s]}")
            seen[s] = bl
        rows.append(dict(bl_id=bl,title=title,type=typ,sources=" ".join(srcs),
                         req_ids=REQ.get(bl,""),package=pkg,blocks=blocks,
                         landing=landing,gate=gate,size=size,status=status))
    return rows


def write_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    (BUILD/"BACKLOG.csv").write_text(buf.getvalue())


def write_md(rows):
    order = ["closed-by:P19.4","closed-by:P19.5","accepted","P20.2","P21.1","P21.2","P21.3","P21.4","P21.5","P21.6","P21.7","P21.8","P21.9","human-gate:HG-01","human-gate:HG-02","human-gate:HG-07","human-gate:HG-08","human-gate:HG-11","P22+"]
    itemmap = {i[0]: i for i in ITEMS}
    out = ["# BACKLOG — the one normalized post-build backlog (P20.1)","",
      "Grouped by `landing`. Machine-readable form: `BACKLOG.csv`; themes: `BACKLOG_THEMES.md`;",
      "the id space (`BL-nnn`) and the `landing` enum are owned by P20.1. Every RISK deferred row,",
      "every ADR revisit trigger, and every LD row appears in exactly one item's `sources`",
      "(validated by `docs/build/tools/check_backlog.py`). Later tickets set `status=closed`",
      "when they retire an item. A reviewer resolves any deferred RISK row's fate in <=2 hops:",
      "RISK -> `-> BL-nnn` in `docs/risk_register.md` -> the item's landing here.",""]
    for land in order:
        group = [r for r in rows if r["landing"] == land]
        if not group:
            continue
        out.append(f"## {land}")
        out.append("")
        for r in group:
            it = itemmap[r["bl_id"]]
            gate = f" · gate {r['gate']}" if r["gate"] else ""
            out.append(f"- **{r['bl_id']}** — {r['title']} · _{r['type']}_ · {r['size']} · status={r['status']}{gate}")
            out.append(f"  - sources: {r['sources']}")
        out.append("")
    # P22+ dedicated section (AC): explicit unscheduled list
    p22 = [r for r in rows if r["landing"] == "P22+"]
    out.append("## P22+ unscheduled (recorded, no P21 ticket owns these)")
    out.append("")
    out.append("Recorded per the ticket: unscheduled work with `type` and `size` filled, awaiting a later planning pass to cut `P22.x` tickets. Not guessed into an existing ticket.")
    out.append("")
    for r in p22:
        out.append(f"- **{r['bl_id']}** — {r['title']} · _{r['type']}_ · {r['size']} · sources: {r['sources']}")
    out.append("")
    (BUILD/"BACKLOG.md").write_text("\n".join(out))


def write_themes(rows):
    itemmap = {i[0]: i for i in ITEMS}
    theme_of = {i[0]: i[9] for i in ITEMS}
    out = ["# BACKLOG_THEMES — <=10 themes over the backlog (P20.1)","",
      "Each `BL-` id appears in exactly one theme (validated by `check_backlog.py`). The",
      "\"retired by\" column names the ticket that closes most of the theme.",""]
    retirer = {
      "T1":"P21.2","T2":"P21.3","T3":"P21.1 (+ human gates)","T4":"P21.4","T5":"P21.5",
      "T6":"P20.2","T7":"P19.1/P19.5 (done)","T8":"P21.7","T9":"P21.8/P21.9","T10":"— (accepted)"}
    for tid, tname in THEMES.items():
        members = [r for r in rows if theme_of[r["bl_id"]] == tid]
        out.append(f"## {tid} — {tname}")
        out.append(f"- **retired mostly by:** {retirer[tid]}")
        out.append(f"- **bl_ids:** {', '.join(r['bl_id'] for r in members)}")
        out.append("")
    (BUILD/"BACKLOG_THEMES.md").write_text("\n".join(out))


def patch_risk(rows):
    # map RISK id -> bl_id
    risk_to_bl = {}
    for r in rows:
        for s in r["sources"].split():
            if s.startswith("RISK-"):
                risk_to_bl[s] = r["bl_id"]
    lines = RISK.read_text().splitlines(keepends=True)
    DEFERRED = re.compile(r"Deferred|Out of scope|Scaffolded|Unverifiable|not-fully-closed|Bounded", re.I)
    in_def = False
    patched = 0
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if stripped.startswith("### "):
            in_def = DEFERRED.search(stripped) is not None
            continue
        if stripped.startswith("## "):
            in_def = False
            continue
        if in_def and stripped.startswith("|"):
            m = re.match(r"(\|\s*)(RISK-[A-Za-z0-9-]+)(\s*)(\|.*)$", stripped)
            if m and m.group(2) in risk_to_bl and "→ BL-" not in stripped:
                bl = risk_to_bl[m.group(2)]
                lines[i] = f"{m.group(1)}{m.group(2)} → {bl}{m.group(3)}{m.group(4)}\n"
                patched += 1
    RISK.write_text("".join(lines))
    return patched, len(risk_to_bl)


rows = build()
# coverage assertion
seen = {}
for r in rows:
    for s in r["sources"].split():
        seen[s] = r["bl_id"]
print("total sources mapped:", len(seen))
risk = [s for s in seen if s.startswith("RISK-")]
ld = [s for s in seen if re.match(r"L[DH]-", s)]
adr = [s for s in seen if s.startswith("ADR-")]
print(f"RISK {len(risk)} / LD {len(ld)} / ADR {len(adr)}")
write_csv(rows); write_md(rows); write_themes(rows)
p, tot = patch_risk(rows)
print(f"risk rows patched: {p} (distinct RISK ids: {tot})")
print("bl count:", len(rows))
