# BACKLOG — the one normalized post-build backlog (P20.1)

Grouped by `landing`. Machine-readable form: `BACKLOG.csv`; themes: `BACKLOG_THEMES.md`;
the id space (`BL-nnn`) and the `landing` enum are owned by P20.1. Every RISK deferred row,
every ADR revisit trigger, and every LD row appears in exactly one item's `sources`
(validated by `docs/build/tools/check_backlog.py`). Later tickets set `status=closed`
when they retire an item. A reviewer resolves any deferred RISK row's fate in <=2 hops:
RISK -> `-> BL-nnn` in `docs/risk_register.md` -> the item's landing here.

## closed-by:P19.4

- **BL-014** — Ledger hygiene + manifest/template fixes + composed-stack confirmations (P19.1/P19.2) · _process_ · S · status=closed
  - sources: LH-01 LH-02 LH-03 LH-04 LH-05 LH-06 LH-07 LH-08 LH-09 LH-10 LH-11 LH-12 LH-13 LH-14 LH-15 LD-X01 LD-X02 LD-X06 LD-X08 LD-X09 LD-X10 LD-X11
- **BL-015** — DB-backed ReadStore + PgClaimSink over the PG spine · _deferred-feature_ · L · status=closed
  - sources: LD-F06 LD-V06 ADR-047 RISK-P14-07 RISK-P6-07
- **BL-016** — Handoff seams & composed-stack verification confirmed (P19.2/P19.3/P19.4) · _process_ · M · status=closed
  - sources: LD-V01 LD-V02 LD-V11 LD-H01 LD-H03 LD-H05 LD-H06 LD-H07 LD-H10 LD-H13 LD-F12 LD-F13 LD-F18 RISK-P11-13

## closed-by:P19.5

- **BL-017** — ER over PG + PG review queue (SIG-IDENT) · _deferred-feature_ · L · status=closed
  - sources: LD-F04 LD-V04 RISK-P5-04 ADR-060 ADR-061
- **BL-018** — Export gate honours derivative_permitted (SIG-LIC-004/010) · _defect_ · M · status=closed
  - sources: LD-F08 LD-H09
- **BL-019** — Jurisdiction-conditional web render at build time (BCP-47, GDPR withholding) · _deferred-feature_ · M · status=closed
  - sources: LD-V12 LD-H11
- **BL-020** — inference CLI wired (coverage/access-paths/completeness/freshness) · _deferred-feature_ · S · status=closed
  - sources: LD-F15
- **BL-021** — P08.1 resolver ADR-060 + risk-register section (retro, §51.3) · _docs-drift_ · S · status=closed
  - sources: LD-X05
- **BL-022** — Analytics-boundary post-hoc hardening documented (ADR-044 amend) · _docs-drift_ · S · status=closed
  - sources: LD-D14

## accepted

- **BL-001** — Human-judgement gates satisfied by tested deterministic gate · _process_ · S · status=accepted
  - sources: RISK-P0-05 RISK-P0-06 RISK-P5-06
- **BL-002** — Foundational tech-stack/tooling ADRs — decision stands, monitor revisit trigger · _process_ · S · status=accepted
  - sources: ADR-001 ADR-002 ADR-003 ADR-004 ADR-005 ADR-006 ADR-007 ADR-008 ADR-009 ADR-010 ADR-011 ADR-012 ADR-013 ADR-014 ADR-016 ADR-017 ADR-019 ADR-020 ADR-021 ADR-023 ADR-024 ADR-025 ADR-029 ADR-044 ADR-045 ADR-058
- **BL-013** — verify-gen / RDF-canonicalisation semantics documented (AGENTS.md gotchas) · _docs-drift_ · S · status=closed
  - sources: LD-X03 LD-X07
- **BL-050** — Recorded ADR-sanctioned spec deviations — no further action · _process_ · S · status=accepted
  - sources: LD-D01 LD-D02 LD-D05 LD-D06 LD-D10 LD-D12 LD-D13

## P20.2

- **BL-010** — Interactive MapLibre map vs zero-JS static PMTiles (spec amendment A1) · _docs-drift_ · M · status=open
  - sources: ADR-051 ADR-018 LD-F09 LD-D11 RISK-P15-21
- **BL-011** — ADR Appendix-F <-> docs/adr numbering reconciliation · _docs-drift_ · S · status=open
  - sources: LD-X04 LD-D03
- **BL-012** — Absence-kind not_researched spec wording (SIG-RECON, §32.2) · _docs-drift_ · S · status=open
  - sources: LD-F14 LD-D08

## P21.1

- **BL-032** — Per-source rights review + registry completion (flip ingestion_permitted) · _rights/legal_ · L · status=open · gate HG-03
  - sources: RISK-P0-19 LD-P05
- **BL-033** — Stage-0 outreach / Eyes-on-Flock archival succession recorded · _rights/legal_ · M · status=open · gate HG-04
  - sources: RISK-P0-20 LD-P01

## P21.2

- **BL-004** — Persist reconcile/inference/tasks/contradiction layer to PG (compute-on-read -> materialised) · _deferred-feature_ · L · status=open
  - sources: LD-V05 LD-D07 RISK-P8-09 RISK-P10-08 RISK-P10-13 RISK-P12-13 ADR-036 ADR-037 ADR-038 ADR-039 ADR-040 ADR-031 ADR-059
- **BL-005** — Persist contributor system to PG (tiers/submissions/revert/anomaly) · _deferred-feature_ · M · status=open
  - sources: RISK-P16-07 LD-F10 ADR-054
- **BL-006** — Persist identity registries and mint surrogate entity_id end-to-end into PG · _deferred-feature_ · M · status=open
  - sources: RISK-P3-03
- **BL-027** — Persist reconcile-workflow outputs (contradictions, sharing edges, tasks, access edges) · _deferred-feature_ · M · status=open
  - sources: RISK-P11-06 RISK-P11-14 RISK-P12-14 RISK-P10-14 RISK-P10-07 RISK-P12-06 RISK-P12-07

## P21.3

- **BL-023** — Live HTTP transports + OCFL CaptureStore for the connector family · _deferred-feature_ · L · status=open · gate HG-03
  - sources: RISK-P4-04 RISK-P4-05 RISK-P4-06 RISK-P4-10 RISK-P7-15 LD-F03 LD-V03 ADR-026 ADR-027 ADR-028 ADR-042 ADR-034 ADR-035 ADR-043
- **BL-024** — Live token mint + real FETCH (MuckRock/records/procurement/flock/slice) · _deferred-feature_ · M · status=open · gate HG-09
  - sources: RISK-P7-10 RISK-P7-16 LD-F16 RISK-P11-05 RISK-P11-15 RISK-P13-07 RISK-P6-06
- **BL-025** — Concrete extraction engines (parser layers 3-5, OCR) + model client · _deferred-feature_ · L · status=open
  - sources: RISK-P7-05 RISK-P7-11 RISK-P7-17 RISK-P5-10 LD-F17 ADR-033 RISK-P7-06
- **BL-026** — Live-connector WACZ per PR + byte-identical reproducibility test (SIG-EVID-017) · _deferred-feature_ · M · status=open
  - sources: LD-F02 LD-H02 RISK-P2-09 RISK-P2-10 RISK-P11-07
- **BL-044** — Data completeness as connectors land (crosswalks, vocab, gold sets, category maps) · _deferred-feature_ · M · status=open
  - sources: RISK-P1-02 RISK-P3-02 RISK-P3-07 RISK-P3-09 RISK-P4-09 RISK-P5-05 RISK-P5-11

## P21.4

- **BL-007** — Wire web surfaces to the live /v1 API/exports (replace committed TS fixtures) · _deferred-feature_ · L · status=open
  - sources: RISK-P15-07 RISK-P15-08 RISK-P15-13 RISK-P15-14 RISK-P15-20 RISK-P15-25 RISK-P15-26 RISK-P15-31 RISK-P15-32 LD-V08 RISK-P2-14 RISK-P9-08 RISK-P13-08 RISK-P13-09 RISK-P13-13 ADR-049 ADR-050 ADR-052 ADR-053 ADR-032 ADR-046
- **BL-008** — Project bulk exports / licence compartments from a live ReadStore · _deferred-feature_ · M · status=open
  - sources: RISK-P14-08 RISK-P14-18
- **BL-046** — Dereferenceable /id/<type>/<uuid> endpoint + ODbL physical_asset table (§42.3) · _deferred-feature_ · M · status=open
  - sources: RISK-P3-08 RISK-P4-07

## P21.5

- **BL-029** — Zenodo live deposit + object store + rendered vector tiles (PMTiles bodies) · _external-dep_ · L · status=open · gate HG-07
  - sources: RISK-P14-16 LD-V07 ADR-048 RISK-P14-17 LD-F07 LD-H08 LD-D09 ADR-015
- **BL-030** — Zero-cost / degraded-but-alive keepalive tested (SIG-GOV-021) · _operational-prereq_ · M · status=open
  - sources: RISK-P0-12 LD-P07

## P21.6

- **BL-009** — Curation/review web UI + asset-promotion service · _deferred-feature_ · M · status=open
  - sources: LD-F05 LD-H04 LD-D04 ADR-030

## P21.7

- **BL-039** — Live MapRoulette client + OSM changeset feed + published leverage metric · _deferred-feature_ · L · status=open · gate HG-08
  - sources: RISK-P16-14 RISK-P16-15 LD-F11 ADR-055 RISK-P18-14 LD-V09
- **BL-040** — Moderated usability study (>=5 ontology-naive contributors) · _operational-prereq_ · M · status=open · gate HG-10
  - sources: RISK-P16-06 LD-P03

## P21.8

- **BL-042** — Data Driven + coarse-international + France/Belgium live connectors · _deferred-feature_ · L · status=open · gate HG-03
  - sources: RISK-P18-04 RISK-P18-05 RISK-P18-06 RISK-P18-13 ADR-056 ADR-057

## P21.9

- **BL-043** — Stage-5 pathway connectors persisted to the claim spine · _deferred-feature_ · L · status=open · gate HG-03
  - sources: RISK-P17-02 RISK-P17-03 RISK-P17-08 RISK-P17-09 RISK-P17-13 RISK-P17-14 LD-H12 LD-V10

## human-gate:HG-01

- **BL-034** — Legal home + counsel launch prerequisites · _rights/legal_ · M · status=open · gate HG-01
  - sources: LD-P02

## human-gate:HG-02

- **BL-035** — Counsel disposition: ODbL 4.4(b) derivative / know-your-rights guidance · _rights/legal_ · M · status=open · gate HG-02
  - sources: RISK-P16-16 RISK-P0-11

## human-gate:HG-07

- **BL-037** — Infra accounts (Zenodo concept DOI, object store, Docker CI runner) · _external-dep_ · S · status=open · gate HG-07
  - sources: LD-P06

## human-gate:HG-08

- **BL-038** — OSM/MapRoulette accounts + Organised-Editing activity registration · _external-dep_ · S · status=open · gate HG-08
  - sources: RISK-P16-13 LD-P04

## human-gate:HG-11

- **BL-036** — Operating governance: board, Code of Conduct, funding policy · _operational-prereq_ · M · status=open · gate HG-11
  - sources: RISK-P0-10

## P22+

- **BL-003** — claim table partitioning (deferred; FK contract kept) · _schema-refinement_ · L · status=open
  - sources: LD-F01 ADR-022
- **BL-028** — Records-request filing/response backend (template outcome log fed live) · _deferred-feature_ · M · status=open
  - sources: ADR-041 RISK-P10-18 RISK-P10-17
- **BL-031** — API rate-limit enforcement + GraphQL (deferred SHOULDs) · _deferred-feature_ · S · status=open
  - sources: RISK-P14-09 RISK-P14-10
- **BL-045** — Ruleset calibration once real data exists (volatility, directness matrix, Atlas supersession) · _schema-refinement_ · M · status=open
  - sources: RISK-P1-03 RISK-P1-04 RISK-P4-08
- **BL-047** — Schema cleanup: legacy succession slots vs reified OrganizationRelationship · _schema-refinement_ · S · status=open
  - sources: RISK-P3-04
- **BL-048** — Determinism / whole-graph audit CI jobs (resolution rebuild, TI-6/7 audit) · _process_ · M · status=open
  - sources: RISK-P2-03 RISK-P2-15
- **BL-049** — Generate physical DDL from LinkML (ontology/db seam, SIG-STORE-045) · _schema-refinement_ · L · status=open
  - sources: RISK-P2-04
- **BL-041** — Contributor onboarding: jurisdiction-aware know-your-rights shown (out of scope P21.7 — separate follow-up) · _deferred-feature_ · S · status=open
  - sources: RISK-P16-08
- **BL-052** — pyproject.toml description reads "skeleton" for five fully-built packages — package metadata contradicts the shipped code · _docs-drift_ · S · status=open
  - sources: ADR-072

## P22+ unscheduled (recorded, no P21 ticket owns these)

Recorded per the ticket: unscheduled work with `type` and `size` filled, awaiting a later planning pass to cut `P22.x` tickets. Not guessed into an existing ticket.

- **BL-003** — claim table partitioning (deferred; FK contract kept) · _schema-refinement_ · L · sources: LD-F01 ADR-022
- **BL-028** — Records-request filing/response backend (template outcome log fed live) · _deferred-feature_ · M · sources: ADR-041 RISK-P10-18 RISK-P10-17
- **BL-031** — API rate-limit enforcement + GraphQL (deferred SHOULDs) · _deferred-feature_ · S · sources: RISK-P14-09 RISK-P14-10
- **BL-045** — Ruleset calibration once real data exists (volatility, directness matrix, Atlas supersession) · _schema-refinement_ · M · sources: RISK-P1-03 RISK-P1-04 RISK-P4-08
- **BL-047** — Schema cleanup: legacy succession slots vs reified OrganizationRelationship · _schema-refinement_ · S · sources: RISK-P3-04
- **BL-048** — Determinism / whole-graph audit CI jobs (resolution rebuild, TI-6/7 audit) · _process_ · M · sources: RISK-P2-03 RISK-P2-15
- **BL-049** — Generate physical DDL from LinkML (ontology/db seam, SIG-STORE-045) · _schema-refinement_ · L · sources: RISK-P2-04
- **BL-041** — Contributor onboarding: jurisdiction-aware know-your-rights shown (out of scope P21.7 — separate follow-up) · _deferred-feature_ · S · sources: RISK-P16-08
- **BL-052** — pyproject.toml description reads "skeleton" for five fully-built packages — package metadata contradicts the shipped code · _docs-drift_ · S · sources: ADR-072
