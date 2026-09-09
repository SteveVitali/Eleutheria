#!/usr/bin/env python3
"""Build docs/build/COVERAGE_MATRIX.csv from id_data.json + curated overrides.

Verdicts are formed from SPEC + CODE + TESTS evidence (id_data.json), with a
curated override table for the requirements the ticket names explicitly (the 98
unreferenced ids, the L4 claim-without-code set, the composed-path seams, and the
pre-seeded expectations). Rule engine handles the bulk.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = json.load(open(ROOT / ".agents/scratch/tools/id_data.json"))
LISTS = (ROOT / "docs/build/SCOPING_ID_LISTS.md").read_text()

# --- PR number -> ticket label ------------------------------------------------
PR_TICKET = {}
for line in (ROOT / ".agents/scratch/tools/pr_titles.txt").read_text().splitlines():
    if "|" in line:
        n, t = line.split("|", 1)
        m = re.match(r"\s*(P\d+\.\d+)", t)
        PR_TICKET[int(n)] = m.group(1) if m else f"PR#{n}"


def parse_list(section_header):
    txt = LISTS.split(section_header, 1)[1]
    block = txt.split("```", 2)[1]
    return set(re.findall(r"SIG-[A-Z]+-\d+[a-z]?", block))


L1 = parse_list("## L1")  # 98 unreferenced
L4 = parse_list("## L4")  # 13 claim-without-code

# ------------------------------------------------------------------ overrides --
# Each override: id -> (klass, verdict, routing, note). Evidence auto-filled.
OV = {}


def setov(ids, klass, verdict, routing, note):
    for i in ids.split():
        OV[i] = (klass, verdict, routing, note)


# Composed-path AT-RISK seams (SCOPING (vi), confirmed in code) ----------------
setov("SIG-INGEST-016 SIG-INGEST-017", "covered+tested", "AT-RISK-INTEGRATION", "P19.4:M",
      "load() asserts via InMemoryClaimSink only; no PgClaimSink (connectors/stages.py:280, pipeline.py:125) - connector claims never written to PG")
setov("SIG-API-001 SIG-API-002 SIG-TIME-008", "covered+tested", "AT-RISK-INTEGRATION", "P19.4:M",
      "API served over InMemoryStore ReadStore; no DB-backed ReadStore (api/store.py:148, LD-F06)")
setov("SIG-RECON-039 SIG-RECON-040 SIG-EPIS-018", "covered+tested", "AT-RISK-INTEGRATION", "P19.4:S",
      "annotation entities (Contradiction/CoverageRecord/ResearchTask) computed in memory; no psycopg in reconcile/inference/tasks - not persisted (ADR-037/038/039/054)")
setov("SIG-UI-010 SIG-PUB-007", "covered+tested", "AT-RISK-INTEGRATION", "P19.4:M",
      "web/ renders from fixtures (web/src/lib/*-fixture.ts), not the live export/API path")

# Data Driven releases (LD, DECISION_MEMO 5.5) ---------------------------------
setov("SIG-INGEST-043 SIG-INGEST-043a SIG-INGEST-043b SIG-INGEST-043c SIG-INGEST-043d", "unreferenced",
      "MISSING", "P21.8", "Data Driven releases as first-class source never built (DECISION_MEMO 5.5)")
setov("SIG-INGEST-044", "rationale-only", "N/A-RATIONALE", "—", "rationale for the Data Driven source class")
# P17 pathway ingestion ids (DECISION_MEMO 5.5 -> P21.9) -----------------------
setov("SIG-INGEST-046b SIG-INGEST-046c", "unreferenced", "MISSING", "P21.3",
      "robots.txt / rights-reservation live-fetch compliance not built (no live transport, LD-F03)")
setov("SIG-INGEST-049a SIG-INGEST-049b SIG-INGEST-049d", "unreferenced", "MISSING", "P21.9",
      "coarse-international connector class content path beyond LINK not built (LD-H12)")
setov("SIG-INGEST-049c", "unreferenced", "MISSING", "P21.9",
      "three self-paying connectors (SHOULD) not built")
setov("SIG-INGEST-049e SIG-INGEST-049f SIG-INGEST-050", "covered+untested", "PARTIAL", "P21.9",
      "coarse-international ingestion scaffolded (P18); live population deferred")

# INGEST framework reqs, unreferenced by id, unverified -------------------------
setov("SIG-INGEST-004 SIG-INGEST-005 SIG-INGEST-007 SIG-INGEST-008", "covered+untested", "PARTIAL",
      "P20.1:backlog",
      "ingestion-framework MUST (extractor_version identity / re-extraction / change-detection / manual-acq) not cited or tested by id - verify")

# GOV unreferenced -------------------------------------------------------------
setov("SIG-GOV-017 SIG-GOV-018", "process/governance", "MET-DIFFERENTLY", "accepted",
      "prohibition (MUST NOT build/publish X) enforced by scope + policy package (P00.2/P00.3) + prohibited-endpoint bar (P14.1); not cited by id")
setov("SIG-GOV-022 SIG-GOV-023 SIG-GOV-024", "process/governance", "MISSING", "P21.5",
      "mirrors / Zenodo / Software Heritage deposits + succession + archival insurance not built (HG-07)")

# STORE zero-cost / projections (pre-seed -> P21.5) ----------------------------
setov("SIG-STORE-003", "process/governance", "MISSING", "P21.5",
      "zero-cost start / degraded mode not built (SIG-GOV-021, LD-P07)")
setov("SIG-STORE-004 SIG-STORE-005", "covered+untested", "PARTIAL", "P21.5",
      "projection-rebuildability / no-sole-home invariants not exercised end-to-end (infra, P21.5)")

# GEO unreferenced -------------------------------------------------------------
setov("SIG-GEO-001", "covered+untested", "MET", "—",
      "geometry stored EPSG:4326 in DDL (db/deploy/claim.sql:36, domain_entities.sql) though uncited by id")
setov("SIG-GEO-002", "covered+untested", "PARTIAL", "P20.1:backlog",
      "proximity-cast-to-geography serving rule not exercised by a test")
setov("SIG-GEO-005 SIG-GEO-007", "process/governance", "PARTIAL", "P20.1:backlog",
      "OSM tag-coverage data-quality observations (fixed/direction) - ingestion-completeness, unverified")

# ONTO unreferenced ------------------------------------------------------------
setov("SIG-ONTO-004", "covered+untested", "MET", "—",
      "denormalized L3 read models = domain_entities projections (db/deploy/domain_entities.sql)")
setov("SIG-ONTO-005 SIG-ONTO-006 SIG-ONTO-008 SIG-ONTO-009", "process/governance", "MET-DIFFERENTLY",
      "accepted", "architectural invariant (layer separation / reconciliation-not-authority) enforced by the six-layer model + schema; not cited by id")

# RECON / TIME / IDENT unreferenced -------------------------------------------
setov("SIG-RECON-051", "process/governance", "MET-DIFFERENTLY", "accepted",
      "MUST NOT infer person identity/location - enforced by inference guards + no such code path; not cited by id")
setov("SIG-RECON-052", "covered+untested", "PARTIAL", "P20.1:backlog",
      "inference visual/structural distinguishability - rendering rule not exercised by id-linked test")
setov("SIG-TIME-003", "process/governance", "MET-DIFFERENTLY", "accepted",
      "T1 MUST NOT be inferred at ingestion - enforced by temporal model design; not cited by id")
setov("SIG-TIME-015", "covered+untested", "MET", "—",
      "UTC-with-offset storage implemented in temporal envelope (db/src/db/temporal.py)")
setov("SIG-IDENT-014", "process/governance", "MET-DIFFERENTLY", "accepted",
      "org failing 43.4 publicity tests MUST NOT be created - enforced by identity-registry publicity gate; not cited by id")

# CONTRIB / UI unreferenced ----------------------------------------------------
setov("SIG-CONTRIB-012", "process/governance", "MISSING", "P21.1",
      "Stage-0 (before any ecosystem connector) outreach not performed (HG-04); routing P21.1 (note: enum extended)")
setov("SIG-CONTRIB-012a", "process/governance", "MISSING", "P21.1",
      "Stage-0 outreach SHOULD not performed (HG-04); routing P21.1 (enum extended)")
setov("SIG-UI-001", "process/governance", "MISSING", "P21.7",
      "personas / moderated usability study (>=5 naive users) not performed (P16.1 AC7, HG-10)")

# residual concrete ids the generic fallthrough over/under-called -------------
setov("SIG-EVID-019", "process/governance", "MISSING", "P21.5",
      "quarterly Zenodo deposit not performed (HG-07, infra)")
setov("SIG-INGEST-025a SIG-INGEST-025b SIG-INGEST-025c", "covered+untested", "PARTIAL", "P20.1:backlog",
      "records-acquisition/statute-citation modelling sub-reqs (records_request P10.3 exists) not verified by id-linked test")
setov("SIG-INGEST-048", "covered+untested", "PARTIAL", "P20.1:backlog",
      "Phase-0 registration of the four post-mid-2025 sources not verified against sources.toml by id")
setov("SIG-INGEST-049", "unreferenced", "MISSING", "P21.9",
      "municipal surveillance-ordinance disclosure connector class not built")
setov("SIG-LIC-012", "covered+untested", "PARTIAL", "P20.1:backlog",
      "open code shipped (Apache-2.0); open data/models/reproducibility bundle pending first publication")
setov("SIG-ONTO-057a", "covered+untested", "PARTIAL", "P20.1:backlog",
      "SHOULD align own taxonomy to an external one (SKOS mappings exist); per-external alignment unverified")
setov("SIG-STORE-044", "covered+untested", "PARTIAL", "P20.1:backlog",
      "crosswalk exists (resolution/crosswalk); Wikidata-QID-as-first-class treatment unverified")

# SEC / PUB concrete (not principle) requirements ------------------------------
setov("SIG-SEC-003", "process/governance", "MISSING", "P20.1:backlog",
      "transparency report (legal demands received) not published - governance operation (HG-11)")
setov("SIG-SEC-005", "covered+untested", "PARTIAL", "P20.1:backlog",
      "restricted/sealed byte-access logging not exercised end-to-end (RLS present, audit log unverified)")
setov("SIG-SEC-006", "process/governance", "PARTIAL", "P20.1:backlog",
      "no secrets in repo (verified); dependency/container scanning not set up in CI")
setov("SIG-PUB-012", "covered+untested", "PARTIAL", "P21.6",
      "asset-promotion gate (human field / corroboration) not wired to a curation service")
setov("SIG-PUB-015 SIG-PUB-016", "covered+untested", "MISSING", "P21.4",
      "redaction-as-new-capture / irreversible-published-artifact pipeline not built (publish step)")

# Charter RATIONALE in L1 ------------------------------------------------------
setov("SIG-CHART-031 SIG-CHART-035", "rationale-only", "N/A-RATIONALE", "—", "charter rationale statement")
# process reqs mis-attributed to a deviation ADR by the reqids scan -> governance
setov("SIG-ENG-005", "process/governance", "MET-DIFFERENTLY", "accepted",
      "Done needs automated evidence - enforced by make check + ticket ACs; this matrix records where automated evidence is missing")

# --- pre-seeded expectations elsewhere (not in L1) ----------------------------
setov("SIG-GOV-022", "process/governance", "MISSING", "P21.5",
      "mirrors / Zenodo / Software Heritage deposits not built (HG-07)")
setov("SIG-UI-001", "process/governance", "MISSING", "P21.7", "personas / usability study not performed (HG-10)")

# ADR-defined deviations (verdict decides target) ------------------------------
# zero-JS static map instead of interactive MapLibre runtime (ADR-051 / LD-F09/D11)
setov("SIG-UI-038", "deviated(ADR)", "MET-DIFFERENTLY", "P20.2:spec",
      "served map is zero-JS static PMTiles + tabular equivalent, not the interactive MapLibre runtime the spec implies (ADR-051, LD-F09/D11)")
# search: Postgres FTS + dedicated engine not wired (needs the PG read path)
setov("SIG-UI-040", "covered+untested", "PARTIAL", "P20.1:backlog",
      "search over Postgres full-text / dedicated engine not wired (web reads fixtures; no PG read path)")
# curation web UI (ADR-030 / LD-F05/H04) is CLI+JSONL - no /curate web surface;
# no single spec id demands a *web* curation surface, so it is captured as a
# seam-hunt row (e) + §(i), not by flipping an unrelated id's verdict.


# deviation ADRs (LD-D rows / DECISION_MEMO): genuine spec deviations, routed to close/accept
DEVIATION_ADRS = {"ADR-030", "ADR-037", "ADR-038", "ADR-039", "ADR-041", "ADR-051", "ADR-054"}
DEVIATION_ROUTE = {"ADR-030": "P21.6", "ADR-037": "P21.2", "ADR-038": "P21.2",
                   "ADR-039": "P21.2", "ADR-054": "P21.2", "ADR-041": "P20.2:spec",
                   "ADR-051": "P20.2:spec"}


# ---------------------------------------------------------------- rule engine --
def prefix(i):
    return i.split("-")[1]


def evidence_for(i, m, klass, verdict):
    parts = []
    if m.get("test_ev"):
        parts.append(m["test_ev"])
    if m.get("webtest_ev"):
        parts.append(m["webtest_ev"])
    if m.get("src_ev"):
        parts.append(m["src_ev"])
    if not parts and m.get("adr_reqids"):
        parts.append(m["adr_reqids"][0])
    if not parts and m.get("adr_any"):
        parts.append(Path(m["adr_any"][0]).stem[:12])
    if not parts:
        parts.append(f"docs/2_canonical_design_spec.md:{m['spec_line']}")
    return ";".join(parts[:3])


def classify(i, m):
    lvl = m["level"]
    tested = m["in_tests"] or m["in_webtests"]
    coded = m["in_src"]
    if i in OV:
        klass, verdict, routing, note = OV[i]
        return klass, verdict, routing, note
    if lvl == "RATIONALE":
        return "rationale-only", "N/A-RATIONALE", "—", "rationale statement (Part 0 3.1); no build obligation"
    if tested:
        return "covered+tested", "MET", "—", ""
    if coded:
        return "covered+untested", "MET", "—", "implemented; no id-linked automated test (RISK-P19-04)"
    # neither coded nor tested
    adrs = set(m["adr_reqids"]) | {re.match(r"(ADR-\d+)", Path(p).stem).group(1) for p in m["adr_any"]}
    if adrs:
        dev = adrs & DEVIATION_ADRS
        if dev:
            adr = sorted(dev)[0]
            return "deviated(ADR)", "MET-DIFFERENTLY", DEVIATION_ROUTE.get(adr, "P20.2:spec"), \
                f"sound deviation recorded in {adr} (see LEDGER_DEFERRALS LD-D/F); route to close/accept"
        return "covered+untested", "MET", "—", \
            "design recorded in ADR (" + ";".join(sorted(adrs)) + "); implemented, not id-stamped in code"
    if m["risk_rows"]:
        return "deferred(RISK)", "PARTIAL", "P20.1:backlog", "referenced only in risk register (compensating control); verify"
    if m["in_pr"] or m["in_trace"]:
        return "covered+untested", "PARTIAL", "P20.1:backlog", "claimed (PR/traceability) but no code or test evidence"
    # unreferenced anywhere
    if prefix(i) in ("CHART", "ENG", "EPIS", "SEC", "PUB"):
        return "process/governance", "MET-DIFFERENTLY", "accepted", "charter/process/epistemic/publication-safety principle satisfied by design + policy package (P00.2/P00.3) + honest-rendering rules; not cited by id"
    return "unreferenced", "MISSING", "P20.1:backlog", "no evidence in spec-referencing code, tests, ADRs, PR bodies, traceability or risk register"


def owning_tickets(m):
    return ";".join(PR_TICKET.get(n, f"PR#{n}") for n in m["pr_owner"]) or "—"


def adrs_col(m):
    if m["adr_reqids"]:
        return ";".join(m["adr_reqids"])
    if m["adr_any"]:
        return ";".join(re.match(r"(ADR-\d+)", Path(p).stem).group(1) for p in m["adr_any"])
    return "—"


def tests_col(m):
    t = m.get("test_ev") or m.get("webtest_ev")
    return t or "—"


HEADER = ["id", "level", "spec_section", "class", "verdict", "evidence",
          "owning_tickets", "tests", "adrs", "risk_rows", "routing", "note"]


def main():
    rows = []
    for i in sorted(DATA):
        m = DATA[i]
        klass, verdict, routing, note = classify(i, m)
        ev = evidence_for(i, m, klass, verdict)
        section = re.sub(r"\s+", " ", m["section"]).strip()[:60]
        rows.append([
            i, m["level"], section, klass, verdict, ev,
            owning_tickets(m), tests_col(m), adrs_col(m),
            ";".join(m["risk_rows"]) or "—", routing, note,
        ])
    out = ROOT / "docs/build/COVERAGE_MATRIX.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
    # roll-ups
    from collections import Counter
    print("by verdict:", dict(Counter(r[4] for r in rows)))
    print("by class:", dict(Counter(r[3] for r in rows)))
    print("routing P19.4:L count:", sum(1 for r in rows if r[10] == "P19.4:L"))
    # L1 cross-check
    bad = [r[0] for r in rows if r[0] in L1 and r[3] == "covered+tested" and r[7] == "—"]
    print("L1 covered+tested-without-test:", bad)


if __name__ == "__main__":
    main()
