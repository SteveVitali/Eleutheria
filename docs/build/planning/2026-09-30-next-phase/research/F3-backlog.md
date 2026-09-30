# F3: Backlog triage, with the ADR revisit triggers and deferred RISK rows through their BACKLOG homes

> **Row:** F3 (META_PLAN §6.F), R, depends A3. **Authored:** 2026-09-30 between 17:00:55Z and 17:23:59Z (`date -u`)
> by Claude Code (Opus 5.5) in the planning worktree on `claude/next-phase-planning`.
> **Scope (orchestrator):** the 32 open and 4 accepted BACKLOG rows; the 144 ADR revisit triggers and 62 deferred RISK
> rows, grouped by their BL home; and homes for the not-MET requirement ids that have none.
> **Outputs:** this note, `data/backlog_triage.csv` (303 rows) and `findings/incoming/F3.csv` (NEW-1…NEW-11).
> **Read-only:** no control file was edited (P10). The LEDGER was read only through `grep` and `sed -n` slices (P13).
> Production was touched only by unauthenticated GETs against the public API (P3). Verdicts are proposals: F2a/F2b set
> requirement verdicts, S1 sets the final dispositions, and T4 applies them.

## 1. Summary

| population | n | result |
|---|---|---|
| BACKLOG open | 32 | **10 closed-by-later-round** · **3 superseded** (BL-034, 035, 053) · **19 still-open** |
| BACKLOG accepted | 4 | **2 accepted** (BL-002, 050; rationale verified) · **1 superseded** (BL-010) · **1 re-opened as still-open** (BL-001) |
| deferred RISK rows (universe) | 62 | 21 closed-by-later-round · 4 superseded · 1 accepted · 36 still-open (re-homed); plus the unrouted RISK-P21-03, now live |
| ADR revisit triggers | 144 | **68 fired** (42 with no recorded answer, 26 already answered by a later ADR or ticket) · 5 superseded · 71 quiet |
| not-MET requirement ids with no live home | 58 (+2) | all 60 get a proposed home theme (§6). The +2 are SIG-INGEST-006/007, whose only home (BL-023) closes |

Nothing here is `already-done` by assertion alone. Each closed row cites a commit, ticket, file:line, or a
recorded or live read.

**Evidence classes used:** `code` (grep and read of the tree at `b051732c`), `recorded-execution` (DEFERRALS,
BUILD_INDEX, run ledgers, baseline.json), `live-read` (three public API GETs at 17:07:54Z, 17:18:07Z and
17:18:11Z, plus `gh repo view` at 17:05Z), and `inference` where labelled.

## 2. Proposed Round-11 homes (theme codes used throughout)

These are proposals for S2/S3. They map onto the META_PLAN streams.

| code | theme | feeds from |
|---|---|---|
| **R11-TRUTH** | build-truth and memory repair (LEDGER, validators, event log, spec-checker in CI) | B1–B6, T2 |
| **R11-GOV** | governance, counsel substitution, and spec truth (ADR waivers and spec amendments) | E1, E2, T1 |
| **R11-HUMAN** | human evaluation and usability (the S3 spine, gold set, sessions) | F4, E3 |
| **R11-OPS** | production activation and ops hardening (backups, observability, scheduler of record, API exposure, capacity, intake) | G1, G2, G3 |
| **R11-RECORD** | public-record correctness (jurisdiction keys, fixture content on live pages, redaction, dossier shape) | C1–C6 |
| **R11-SOURCES** | source discovery, rights, and acquisition (owed rights and credential rows, CCOPS breadth, OCR if needed) | I1–I8, E4 |
| **R11-TRANSPARENCY** | data transparency, export, and archival (downloads, attribution, IRIs, Zenodo, SWH, WACZ) | J1–J4 |
| **R11-DATAMODEL** | data quality and taxonomy completeness (crosswalks, technology classes, volatility, geo overlap) | I8, C3 |
| **R11-DEBT** | engineering debt and verification (sqitch, schema cleanup, whole-graph audits, id-linked tests) | F5, H2 |
| **OPERATOR-QUEUE** | operator actions with no engineering residue (HG-08, sending records requests) | D, Track 0 |
| **LATER-PHASE** | trigger-gated items that are not Round-11 work | S1 |
| **ADR-TRIGGER-REGISTER** | one proposed monitor home for the quiet triggers, replacing the BL-002/056/057/058 umbrella homes (NEW-3) | S1, T4 |

## 3. BACKLOG rows (36)

### 3.1 Closed by a later round (10): evidence

| row | title (short) | closed by | evidence |
|---|---|---|---|
| BL-006 | identity registries into PG | P26.2 `f7f8600a`, P31.3 `700bc1a2` | `agency_registry` connector; `fbi_cde_agency_registry` permitted and scheduled (`ops/cadence.toml:307`, "verified live 2026-09-16"); `entity_identity_key` guard (ADR-110). Census and IPEDS registries remain unpermitted: Stream-I candidates, not residue |
| BL-008 | exports from a live ReadStore | P27.4 `93f04c51`, P30.3, P31.16 | `exports.spine_export.run_spine_export`; P30.3 exported from the materialized spine (`LEDGER.md:136`); live manifest `sig-2026-09-27-ce480ab1` with 132 artifacts (baseline) |
| BL-023 | live HTTP transports and the OCFL CaptureStore | P21.3 `305f94d5`, P25.1–P25.8 | D-P21.3-1 and D-LIVE.1a-1 DONE 2026-09-16; 78 sources in `ops/cadence.toml`; 45 of 79 scheduler triggers have fired (baseline) |
| BL-024 | live token mint and real fetch | P25.7, P25.9, P26.4, P26.5 | Secret Manager bindings on hosted jobs (`ops/cadence.toml:125` muckrock refresh; `:320` sam_gov "keyed live since P26.4"); `eyes_on_flock` scheduled (`:299`). The MuckRock API challenges GCP egress: an external residue |
| BL-028 | records-request backend | P25.9, P29.2 | D-META.1-2 DONE: `tasks/src/tasks/request_outcomes.py` plus `sig-tasks records-outcomes`; P29.2 detector→request drafts. Residue: D-R7.2-SEND (operator) and RISK-P10-17 (R11-GOV) |
| BL-037 | infra accounts and host | P24.1, P25.x, P25.8 | D-ACCT.1-1, D-DEPLOY.1-1 and D-OBS.1-1 DONE; Cloud SQL and Cloud Run live. The Zenodo concept-DOI leg moves to BL-029 |
| BL-042 | Data Driven, coarse-international, and FR/BE connectors | P24.6, P25.5 `7b52f2b4`, P26.x | decp_fr, raa_prefectures, madada, eff_data_driven, carnegie, frwm and aspi are all permitted and scheduled (`ops/cadence.toml:103,111,145,161,217,225,233`). Residue: D-JURIS.2-1 (Belgian eID) and RISK-P18-04 → R11-SOURCES |
| BL-045 | ruleset calibration on real data | P25.9, P30.2a | `docs/build/reports/2026-09-16_ruleset_calibration.md` (defaults hold); genre gap closed by ADR-104. Residue: multi-epoch volatility (RISK-P1-04) → R11-DATAMODEL |
| BL-046 | dereferenceable `/id` endpoint | P14.1 `d6630899`, P19.4 `4682f9d2` | `api/src/api/app.py:126`; `PgReadStore.resolve_id`; live OpenAPI lists the route, and GET returns Turtle with 200 at 17:18:11Z. The row was already stale when P20.1 created it. Residue: the IRIs use the `https://sig.example/id/` placeholder (**NEW-6**). The ODbL physical table (RISK-P4-07) is superseded by export-boundary compartments |
| BL-056 | P27 public-launch umbrella | P27.1–P27.10, P30.3, P31.14–P31.16 | BUILD_INDEX seq 117–126; cut-over 2026-09-24; republish 2026-09-27; all 8 linked deferrals DONE. Its 13 ADR triggers move to the register |

### 3.2 Superseded (4)

| row | superseded by | consequence |
|---|---|---|
| BL-010 (accepted) | ADR-097 / P27.9 `MapIsland.tsx` (`3d3eeb75`, 2026-09-22) and ADR-118 / P31.15 live PMTiles (`REPUBLISH_LIVE_2026-09-27.md:79-80`) | Close the row. The SIG-UI-038/047 matrix notes ("MapLibre island NOT built") are stale (F2) |
| BL-034 | HG-01 personal legal home (D-P21.4-1, 2026-09-15); operator-adopted drafted analyses instead of counsel (D-LEGAL.1-1, 2026-09-16) | `adr-waiver` or `spec-amendment(SIG-GOV-012)`, R11-GOV (E1 F-31) |
| BL-035 | operator attestation instead of a counsel opinion (D-P30.3-COUNSEL DONE 2026-09-24; ADR-106) | `adr-waiver`, R11-GOV. E3 Q-26 asks who gave the ADR-086/106 determinations |
| BL-053 | the national surface (ADR-090; 55 dossier slugs) replaced one-jurisdiction-at-a-time onboarding | The recorded couplings are still live. ILIKE filters remain at `api/src/api/store_pg.py:204` and `reconcile/src/reconcile/materialize.py:265,787`. Code collisions: ID = Idaho + Indonesia and MN = Minnesota + Mongolia (F-44, I1 NEW-1). → ticket in R11-RECORD (structured jurisdiction key) |

### 3.3 Accepted rows

- **BL-002** (27 foundational ADRs) stays accepted: 21 decisions stand with quiet triggers. The exceptions are
  listed in §5: ADR-016 fired, ADR-058 §3 is superseded, ADR-012/021/073 have likely fired, and ADR-006's Object
  Lock is unrealized in production (G1 NEW-4, a drift rather than a trigger).
- **BL-050** (7 LD-D deviations) stays accepted. Its LD-D01 contradicts open BL-049 (**NEW-10**).
- **BL-001** is **re-opened**. The deterministic-gate rationale holds only for RISK-P0-05. RISK-P0-06's gate was
  removed by GL-GATE-08/ADR-088 (robots never enforced). RISK-P5-06's human judgement is owed, not met: D-R6.1-EVAL
  and D-R10-HUMAN-1 are OPEN, and the adjudicator is rule code (`resolution/src/resolution/adjudicator.py:19`;
  E1 NEW-10). Proposed split: P0-05 stays accepted; P0-06 → R11-GOV (`adr-waiver(ADR-088)`); P5-06 → R11-HUMAN.

### 3.4 Still open (20), re-homed by proposed Round-11 theme

| theme | rows | what remains, with evidence |
|---|---|---|
| **R11-GOV** | BL-001 (P0-06 part), BL-036 | Governance under the sole-maintainer posture: SIG-GOV-015/016 are PARTIAL, and the governance doc claims a board exists (E1 NEW-7) |
| **R11-HUMAN** | BL-001 (P5-06 part), BL-040 | No usability study has run. Merge with D-R10-USERS-1 (E3 NEW-5) |
| **R11-OPS** | BL-031, BL-041, BL-025 (canary part) | BL-031: the public API is unauthenticated and sends no rate-limit headers (GET at 17:07Z); limits exist only as metadata (`api/src/api/tiers.py:31-34`). BL-041: no KYR content anywhere, and no onboarding surface to put it on until intake opens (Q-27). BL-025: no scheduled parser canary |
| **R11-SOURCES** | BL-054, BL-055, BL-025 (OCR/model part) | BL-054: 6 CCOPS sources live, 6 registered rows not permitted, and ADR-080 (b) fired unevaluated. BL-055: a 10-deferral umbrella; close it and re-home each deferral (F1; E4 NEW-1/2/3 stale cells) |
| **R11-TRANSPARENCY** | BL-026, BL-029 | BL-026: live WACZ is never used (`--wacz` appears in no job). BL-029: only the sandbox DOI 10.5072/zenodo.603732 exists; there is no production deposit, and the SWH blocker is gone because the repo is **PUBLIC** (E1 NEW-14) |
| **R11-DATAMODEL** | BL-044 | Crosswalk, taxonomy and gold-set content debts. I1 NEW-9 (everything typed `traffic_camera`) shows the gap is live |
| **R11-DEBT** | BL-047, BL-048, BL-049 | `SuccessionKind` is still in the ontology. There is no whole-graph TI-6/TI-7 or rebuild audit over a real spine. Generated SQL goes unused (prefer `adr-waiver`, per NEW-10) |
| **R11-TRUTH** | BL-051 | RISK-P20-02's surfaces all landed; its compensating control `check_spec_src.py` runs in no CI job, Makefile target, or collected test (F-32) |
| **OPERATOR-QUEUE** | BL-038 → `merged-into` BL-039, BL-039 | HG-08: rotate the key, register the OE page, set `registered=true`, then push and pull (D-P21.7-1) |
| **LATER-PHASE** | BL-003 | ADR-022 has not fired (disk 6.42 of 15 GB). Absorb RISK-P21-03 (**NEW-7**) |
| **split** | BL-057, BL-058 | Close both umbrellas. BL-057's 6 owed rows go to R11-HUMAN (D-R6.1-EVAL, D-P30.2b-1), R11-DATAMODEL (D-P30.2b-2), R11-OPS (D-P31.4-1, 2026-10-10), LATER-PHASE (D-R7.1-AUTH) and OPERATOR-QUEUE (D-R7.2-SEND). BL-058's 20 owed rows go to R11-HUMAN, R11-OPS, R11-SOURCES, R11-TRUTH and R11-DEBT (per-row list in the CSV). Move their 43 ADR triggers to the register |

## 4. Deferred RISK rows (62 in the universe, plus RISK-P21-03)

**Closed by later rounds (21):** RISK-P1-03, P2-10, P3-03, P3-08, P4-04, P4-05, P4-06, P4-10, P7-10, P7-15, P7-16,
P10-18, P11-05, P14-08, P14-17, P14-18, P15-21, P16-14, P18-05, P18-06, P18-13. The evidence for each is in the CSV;
for example, P4-04 is `capture_ocfl.py` (`305f94d5`) and P14-17 is the live PMTiles range 206
(`REPUBLISH_LIVE_2026-09-27.md:80`).

**Accepted (1):** RISK-P0-05. **Superseded (4):** RISK-P0-06 (ADR-088), P0-11 and P16-16 (counsel replaced by
operator drafts and attestation), and P4-07 (export-boundary compartments).

**Still open, re-homed:**

| home | n | RISK rows |
|---|---|---|
| R11-SOURCES | 9 | P5-10, P6-06 (→ `merged-into` D-P32.18-1), P7-05, P7-11, P7-17, P11-07, P11-15, P13-07 (→ with D-SOURCES.2-2), P18-04 |
| R11-DATAMODEL | 6 | P1-02, P1-04, P3-02, P3-07, P3-09, P4-09 |
| R11-GOV | 6 | P0-06, P0-10, P0-11, P4-07, P10-17, P16-16 |
| R11-HUMAN | 4 | P5-05, P5-06, P5-11, P16-06 |
| R11-DEBT | 4 | P2-03, P2-04, P2-15, P3-04 |
| R11-OPS | 3 (+1) | P7-06, P14-09, P16-08, plus **RISK-P21-03** (unrouted, precondition fired, NEW-7) |
| LATER-PHASE | 3 | P4-08, P14-10 (GraphQL), P18-14 |
| R11-TRANSPARENCY | 2 | P2-09, P14-16 |
| OPERATOR-QUEUE | 2 | P16-13, P16-15 |
| R11-TRUTH | 1 | P20-02 |

(The superseded rows are listed under their R11-GOV home above.)

## 5. ADR revisit triggers (144), by BL home

| BL home | ADRs | fired, unanswered | fired, answered | superseded | quiet |
|---|---|---|---|---|---|
| BL-002 (accepted) | 27 | 4 | 1 | 1 | 21 |
| BL-003 | 1 | 0 | 0 | 0 | 1 |
| BL-004 (closed) | 7 | 5 | 2 | 0 | 0 |
| BL-005 (closed) | 1 | 1 | 0 | 0 | 0 |
| BL-007 (closed) | 7 | 3 | 4 | 0 | 0 |
| BL-009 (closed) | 2 | 0 | 2 | 0 | 0 |
| BL-010 (accepted) | 2 | 0 | 1 | 0 | 1 |
| BL-015 / 017 / 043 (closed) | 4 | 0 | 4 | 0 | 0 |
| BL-023 | 10 | 6 | 3 | 0 | 1 |
| BL-025 / 028 | 2 | 1 | 1 | 0 | 0 |
| BL-029 | 3 | 2 | 0 | 1 | 0 |
| BL-032 (closed) | 1 | 1 | 0 | 0 | 0 |
| BL-037 | 3 | 2 | 0 | 1 | 0 |
| BL-039 | 2 | 0 | 0 | 0 | 2 |
| BL-042 | 3 | 1 | 2 | 0 | 0 |
| BL-048 / 052 (closed) | 2 | 0 | 0 | 0 | 2 |
| BL-051 | 1 | 1 | 0 | 0 | 0 |
| BL-053 | 2 | 1 | 0 | 0 | 1 |
| BL-054 | 1 | 1 | 0 | 0 | 0 |
| BL-055 | 7 | 0 | 1 | 0 | 6 |
| BL-056 | 13 | 2 | 2 | 2 | 7 |
| BL-057 | 17 | 5 | 3 | 0 | 9 |
| BL-058 | 26 | 6 | 0 | 0 | 20 |
| **total** | **144** | **42** | **26** | **5** | **71** |

Nine closed BL rows home 23 triggers (**NEW-3**).

### 5.1 Fired or likely fired, with no recorded answer: need a new ADR or a ticket (26)

| ADR | what fired (evidence) | proposed disposition → home |
|---|---|---|
| **ADR-016** + **ADR-076** | Dagster was never deployed. The scheduler of record is Cloud Scheduler (79 triggers) plus 88 Cloud Run jobs (baseline). GitHub `reingest.yml` failed 6 of 6 runs on main, 09-25…09-30 ("--sink pg requires --dsn"; A1 NEW-2, F-41, F-39) | one new ADR superseding both; retire the workflow (G1 QA-8) → R11-OPS |
| **ADR-081** | Go-public ran without the `v0.2.0` tag (A3 NEW-3). "Managed backups replace the drill" was untrue until Track 0 enabled backups and PITR on 2026-09-30 (F-01). The only restore drill used the 5-claim seed (G1 NEW-14). Deletion protection is off (F-42) | new ADR or amendment, plus a restore drill at scale → R11-OPS |
| **ADR-077** | The hosted stack is live and a real notifier exists (P25.8), but alerts reach no human and the probe has been red 14 times running since 09-27 (G1 NEW-2). `observability.yml` measures nothing (G1 NEW-3) | new ADR (observability posture) plus tickets → R11-OPS |
| **ADR-090** | The read API is publicly invokable: unauthenticated, no rate-limit headers, 18 routes (live-read 17:07Z) | new ADR (API exposure posture) plus BL-031 → R11-OPS |
| **ADR-098** (likely) | Cost: the list price is about $90–100/mo, including about $18 for the HTTPS LB, against a README figure of "≈ $0/mo" (G1 NEW-11). Whether the trigger fires depends on the Q-10 ceiling | decide at Q-10 → R11-OPS |
| **ADR-107** (prospective) | Round 11 plans large new-source lands and a republish (operator scope addition, §7.1); the 10-10 replay is pending | capacity plan (Q-23) → R11-OPS |
| **ADR-114** (prospective) | Disk is at 6.42 of 15 GB (43%) against the 50%-in-12-months threshold, and new ingest is planned | capacity plan → R11-OPS |
| **ADR-111** (d) | 3 Cloud Run jobs run the tag-only image `curl:8.10.1` (baseline `image_counts`), and `sig-alerts` runs on `:latest` (G1-11) | pin every workload by digest → R11-OPS |
| **ADR-101** (likely) | The site has been frozen at 09-27 while the spine ingests daily, with no republish cadence (G1 NEW-13) | republish-cadence ticket (G3) → R11-OPS |
| **ADR-132** (likely) | Public bucket origins bypass the nginx deny map: `sig-web` is allUsers-readable (G1 NEW-5) and bulk data is served straight from GCS (J1 NEW-12) | decide before release namespaces deploy, plus an ADR → R11-OPS |
| **ADR-120** | Three clauses are currently true: intake staffing is absent (D-P32.16-1), the gate is likely inconclusive at an affordable budget (E3 NEW-8), and the withdrawal barrier has an origin gap | record per-clause decisions → R11-HUMAN, R11-OPS |
| **ADR-012** (likely) | `sig_read_public` has blanket SELECT, which reaches `evidence_access_log` and `review_decision` (J1 NEW-9) | security ticket; verify RLS against grants → R11-OPS |
| **ADR-079** | Later jurisdictions arrived through the national surface. The ILIKE filters remain, and jurisdiction codes collide (F-44, I1 NEW-1) | ticket plus a new ADR (structured jurisdiction scheme) → R11-RECORD |
| **ADR-122** (likely) | Count-scope jurisdiction is an unscoped token (same evidence) | ticket → R11-RECORD |
| **ADR-052**, **ADR-053** | The DB-wired API exists, but live pages still show fixture or empty content: `/evidence/` claim views are empty (J1 NEW-4), demo `/task/new/` pages are public (G1 NEW-7), and editorial-standards is a fixture (E1 NEW-1) | ticket → R11-RECORD |
| **ADR-105** (likely) | Overlapping DeFlock/OSM ArcGIS republishes (I1 NEW-5) and axis swaps (I1 NEW-2) change the overlap shape | re-measure the tiers → R11-DATAMODEL |
| **ADR-130** (d) | The operator directed that new sources be configured and ingested into production in Round 11 (§7.1) | live stage under the ADR-130 queue → R11-SOURCES |
| **ADR-021** (likely) | A single 7,534-line `sources.toml` holds 342 sources, with rights-field drift (E4 NEW-10, B1 NEW-5) | partition or validate the registry, plus an ADR → R11-SOURCES |
| **ADR-063** | HG-03 was answered and the packet set widened to 342, but `RIGHTS_REVIEW_INDEX.md` was never regenerated (E4 NEW-6) | ticket → R11-SOURCES |
| **ADR-067** | The sandbox credential arrived, the tiler was outgrown (→ ADR-118), and A1 was de facto unticked (→ ADR-097). The production Zenodo deposit and SWH are still owed, and the repo is now PUBLIC | ticket → R11-TRANSPARENCY |
| **ADR-062** | "Revisit at the next planning pass": that pass is this one. SIG-ENG-039 is not enforced in CI (F-32) | ticket → R11-TRUTH / T1 |
| **ADR-073** (likely) | `LEDGER.md` is 679 KB and cannot be read in one context (P13). The largest report is 5,112,144 B, 97.5% of the 5 MiB flag | B3 repair → R11-TRUTH |
| **ADR-126** (likely) | Status is still hand-edited in DEFERRALS; 97 anchors and 0 transitions (F-26); anchored at 10-21 (B1 NEW-7) | ticket → R11-TRUTH |
| **ADR-145** | New spec↔landed drift found (F-31, F-34, E1 NEW-6) | spec amendments following the ADR-145 pattern → R11-GOV / T1 |

**Fired, needing only a recorded evaluation (16):**

- ADR-027, 028, 034, 035 and 042: live transport landed, and §26 was amended without the named counsel.
- ADR-036–040: annotation persistence arrived through P28.3, P28.4 and P29.2, re-arming the P21.2 "not fired" notes.
- ADR-041: the records backend landed (P25.9).
- ADR-046: the Policy surfaces landed.
- ADR-048: partly answered; the production deposit is owed.
- ADR-054: an intake submission store exists (P32.16).
- ADR-070: Data Driven and the coarse trio are live.
- ADR-080 (b): P31.13 added 3 CCOPS jurisdictions (`26d5ceee`), and `docs/build/runs/P31.13.md` records no evaluation.

**Fired and already answered (26):**

| answered by a later ADR | ADRs |
|---|---|
| ADR-099 or ADR-105 | ADR-029, 060, 061 |
| ADR-068 or ADR-050 | ADR-030, 032 |
| P08 | ADR-031 |
| ADR-071 or ADR-074 | ADR-033 |
| ADR-059 | ADR-047 |
| ADR-091, ADR-097 or ADR-118 | ADR-049, 051 |
| ADR-090 | ADR-050 |
| ADR-079 or ADR-084 | ADR-056, 057 |
| ADR-101 | ADR-059 |
| ADR-081 | ADR-066 |
| ADR-100 | ADR-068 |
| ADR-088 | ADR-082 |
| ADR-107 | ADR-102 |
| ADR-105, ADR-112 or ADR-114 | ADR-104 |
| ADR-111 | ADR-026 |

| answered by landed work | ADRs |
|---|---|
| P25.x | ADR-065 |
| P25.5 | ADR-071 |
| P25.8 | ADR-074 |
| P31.x | ADR-103 |
| P31.16 | ADR-106 (the mixed `points.json` was accepted, then retired), ADR-117 |

Two rows carry a residue. ADR-104 (e), volatility recalibration, is still pending (→ R11-DATAMODEL). ADR-106's public
compartments ship with empty attribution (E1 NEW-4, J1 NEW-3; → R11-TRANSPARENCY).

### 5.2 Superseded (5): none is marked superseded anywhere (NEW-4)

| ADR | superseded by | note |
|---|---|---|
| ADR-015 | ADR-081 | GCS in practice; no CDN (J1 NEW-12) |
| ADR-058 §3 | ADR-073 | |
| ADR-075 | ADR-081 | |
| ADR-092 | ADR-099 / ADR-101 | SIG-EXPORT-012 and SIG-RECON-058 still describe it (F-34) |
| ADR-096 §1 | ADR-106 | Fired on the operator's word on 2026-09-24: *"counsel says it's okay and we can publish it all together"* (`LEDGER.md:137`). The operator's "together" was implemented as one public map plus licence-separated downloads. Merging ODbL into the CC-BY graph "is NOT authorized by this answer" |

### 5.3 The triggers the orchestrator named

| ADR | status |
|---|---|
| ADR-092 | Superseded (§5.2) |
| ADR-016 | Fired (§5.1) |
| ADR-081 | Fired: backups are now actually enabled (09-30), but the restore at scale, deletion protection and the `v0.2.0` tag are open |
| ADR-087 | Quiet |
| ADR-088 | Quiet. No egress-IP block has been recorded since 09-19; the opengov Cloudflare wall was probed 09-18 (D-SOURCES.9-3), before the decision. The counsel clause is dormant |
| ADR-096 | Superseded by ADR-106 |
| ADR-098 | Likely fired, subject to Q-10 |
| ADR-107 | Prospectively fired. The current tier matches the ADR (`db-custom-1-3840`) |
| ADR-111 | Fired on clause (d). Note that ADR-111's text covers *jobs*; `sig-alerts` is a *service*, so G1's proposal to extend the rule to services is needed |

### 5.4 Counsel-dormant triggers (NEW-8)

Thirteen ADRs have counsel-conditioned clauses that cannot fire, because counsel was replaced by operator-adopted
drafts and attestation: ADR-011, 034, 035, 041, 042, 055, 083, 084, 085, 086, 088, 094 and 106. E2 should re-state
them as operator-attestation events, or engage real counsel.

## 6. Not-MET requirement ids with no home: count reconciliation and homes

**Counts by method** (69 not-MET: 54 PARTIAL, 10 MISSING, 5 AT-RISK-INTEGRATION; the orchestrator's reference
count was 55):

- **53**: named in no BACKLOG row of any status, no DEFERRALS text, and no manifest text (the F-30 style of method).
- **57**: no UNIVERSE `links` at all (A3's method).
- **58, the adjudicated set**: not named by an open or accepted BL row, an owed deferral row, an unlanded manifest row
  (184–187) or its ticket contract, or a RISK row routed to an open or accepted BL.
  - This count is higher than 53 because 7 ids are named only in **closed** BL rows: CONTRIB-012 and 012a (BL-033),
    EPIS-018, RECON-039 and RECON-040 (BL-004), PUB-007 (BL-007), PUB-012 (BL-009). UI-010 is named only in closed
    BL-007 and landed manifest row 36; GOV-012 only in DONE D-P21.4-1.
- **+2**: SIG-INGEST-006/007, whose only home is BL-023 (through RISK-P4-05/06), which this row proposes to close.

That makes 60 ids to home. The 11 ids that are homed keep their homes: EVAL-001/002/005/006/007 via BL-058 and
D-R10-HUMAN-1, GOV-015/016 via RISK-P0-10 → BL-036, GOV-021 via ADR-067 and RISK-P7-06, and STORE-045 via BL-049.

**Proposed homes** (F2a/F2b set the verdicts; several are likely stale-routed and may re-verdict to MET):

| home | n | ids (SIG- omitted) |
|---|---|---|
| R11-DEBT | 24 | ONTO-001, 028, 035, 051, 054, 055, 057, 060, 064, 065; INGEST-004, 005, 006, 007, 010; EVID-001; GEO-002; STORE-004, 005, 013; CONTRIB-019 (likely MET via P29.2); EPIS-018, RECON-039, 040 (AT-RISK routing to P21.2 is stale; persisted by P28.3/P28.4/P29.2) |
| R11-GOV | 10 | CONTRIB-012, 012a, 013 (outreach declined: D-P21.1-2 WONTFIX); GOV-012, 013, 024; INGEST-046b, 046c (GL-GATE-08; E1 NEW-15); PUB-007 (five-prong test; E1 NEW-12); SEC-003 (E1 NEW-5) |
| R11-SOURCES | 6 | INGEST-008, 025a, 025b, 025c, 041, 048 |
| R11-DATAMODEL | 5 | GEO-005, GEO-007 (mobility and FOV), ONTO-057a, STORE-037, STORE-044 |
| R11-RECORD | 5 | PUB-012, PUB-015, PUB-016 (redaction pipeline), RECON-052, UI-010 (the fixture routing is stale; the web is export-mode) |
| R11-TRANSPARENCY | 4 | EVID-019, GOV-022, GOV-023 (Zenodo, SWH, mirrors, succession), LIC-012 |
| R11-OPS | 3 | SEC-005 (access-log retention; J1 NEW-9, G1 NEW-12), SEC-006 (least-privilege service accounts; G1 NEW-1), UI-040 (release FTS5 built but not deployed; F-14) |
| R11-TRUTH | 2 | ENG-004, ENG-034 (process and historical build order; candidate N/A-RATIONALE) |
| R11-HUMAN | 1 | UI-001 (personas and real tasks) |

## 7. Hygiene issues

1. **Duplicate RISK ids** (re-verified). `RISK-P5-04` heads `docs/risk_register.md:289` (→ BL-017) and `:313`.
   `RISK-P20-01` heads `:1262` and `:1451` ("(materialized)"). Both second occurrences are unrouted history rows;
   rename them, for example with an `-a` suffix (B4). No universe ref collides (A3 NEW-5).
2. **RISK-P21-03 is unrouted** (`:1341`) and cites closed BL-004. Its precondition has now fired (**NEW-7**).
   Proposed route: BL-003 plus the Round-11 capacity plan.
3. **An owed deferral is homed on a closed BL row.** D-SOURCES.2-2 → BL-032 (closed). The checker passes because it
   tests only that some BL id appears on the row (**NEW-1**).
4. **Home disagreement.** D-R7.2-SEND is BL-028 in `events.jsonl:56` but BL-057 in its status cell (**NEW-2**). The
   UNIVERSE inherits BL-028.
5. **Triggers on closed rows.** 23 ADR triggers are homed on 9 closed BL rows. `check_backlog` counts them as homed
   ("144/144") (**NEW-3**).
6. **Stale landings on open rows.** 10 open rows still land on landed tickets (P21.3, 21.4, 21.5, 21.7, 21.8,
   P25.1). Four rows land on human gates that have since been decided: HG-01 (BL-034), HG-02 (BL-035), HG-11
   (BL-036) and HG-07 (BL-037; partly decided) (**NEW-5**, refines F-33).
7. **Accepted rows contradicting reality.** BL-010 says there is no MapLibre island; one shipped in P27.9. BL-050's
   LD-D01 contradicts open BL-049 (**NEW-10**).
8. **Superseded ADRs read "Accepted"**, and the generated index has no superseded-by field (**NEW-4**).
9. **The mirror duplicates rows.** `BACKLOG.md` renders 17 rows twice, once under the landing heading and again under
   an "unscheduled" heading (**NEW-11**).
10. **Legacy rows** (carried from A3, not re-litigated):
    - 18 DEFERRALS rows use the 7-cell layout.
    - D-P27.5-1 has kind `E`.
    - BL-013 sits under `## accepted` while its status is `closed`.
    - `LD-*` ids in BL `sources` point into the Phase-A capture (`reports/LEDGER_DEFERRALS.md`), not a live register.
11. **The P33.4 sweep never re-triaged BL rows.** OPERATIONAL_READINESS §(f2) says "verified, nothing re-homed". The
    umbrella rows grew by appending ADR summaries (titles: BL-057 6.3 KB, BL-058 20.4 KB).

## 8. New findings (`findings/incoming/F3.csv`)

| id | sev | title |
|---|---|---|
| NEW-1 | S3 | An OPEN deferral (D-SOURCES.2-2) is homed on closed BL-032; `check_backlog` still reports 36/36 |
| NEW-2 | S3 | D-R7.2-SEND backlog home: `events.jsonl` BL-028 vs status cell BL-057 |
| NEW-3 | S2 | Revisit triggers fire unevaluated: 68/144 fired (42 unanswered); 23 homed on closed rows; 83 on umbrellas |
| NEW-4 | S3 | Superseded ADRs still read "Accepted"; the ADR index has no superseded-by field |
| NEW-5 | S2 | F-33 refined: 10 open BL rows satisfied, 3 superseded; BL-010 superseded; BL-001 re-opened; 10 stale landings |
| NEW-6 | S2 | The public API dereferences ids to placeholder IRIs `https://sig.example/id/…` (live 17:18:11Z) |
| NEW-7 | S3 | RISK-P21-03 is live (the annotation layer is persisted), with no route and no capacity-plan owner |
| NEW-8 | S3 | 13 ADRs carry counsel-conditioned revisit clauses that cannot fire |
| NEW-9 | S3 | D-P21.3-2's "export credentials in the run shell" blocker is obsolete: the keys are bound to hosted jobs |
| NEW-10 | S3 | Accepted BL-050/LD-D01 and open BL-049 record the same DDL deviation as both sanctioned and owed |
| NEW-11 | S3 | `BACKLOG.md` renders 17 rows twice |

## 9. Evidence log (commands, `date -u`)

| time (UTC) | command | used for |
|---|---|---|
| 17:00:55 | `date -u`; `git branch --show-current` → `claude/next-phase-planning` | header |
| 17:0x | `python3 docs/build/tools/check_backlog.py` → risk 102/102, ADR 144/144, LD 90/90, deferral homes 36/36, dupes 0 | NEW-1, NEW-3 |
| 17:05 | `gh repo view --json visibility` → PUBLIC; `gh api repos/SteveVitali/Eleutheria` → vis public, pushed 2026-09-30T02:46:38Z | BL-029, ADR-020, ADR-067 |
| 17:07:54 | `curl https://sig-api-…run.app/openapi.json` → 200, 18 paths incl. `/id/{id_type}/{uuid}` | BL-031, BL-046, ADR-090 |
| 17:07:58 | `curl -D - '…/v1/search?q=flock'` → HTTP/2 200, no rate-limit headers; `GET /` → service banner | BL-031, ADR-090 |
| 17:18:07 | `curl '…/v1/search?q=police&limit=3'` → 3 entity ids | NEW-6 |
| 17:18:11 | `curl -H 'Accept: text/turtle' '…/id/organization/01a0a5fe-db62-…'` → 200, `https://sig.example/id/…` subject | NEW-6 |
| (repo) | greps named in each CSV row: `ops/cadence.toml`, `sources.toml` (tomllib: 342 sources, 236 permitted), `db/deploy`, `api/src`, `web/src/islands`, `.github/workflows`, `Makefile`, `tests/` | BL rows |
| (repo) | `git log --diff-filter=A` for `agency_registry.py` (`f7f8600a`), `entity_identity_key.sql` (`700bc1a2`), `transports` (`305f94d5`), `web/src/islands` (`3d3eeb75`); `-S` for `run_spine_export` (`93f04c51`) and the `/id` route (`d6630899`) | closures |
| (baseline) | `baseline/baseline.json` prod.* (A1, 16:31:55Z) plus sibling-row findings A1, A3, B1, E1, E3, E4, G1, H1, I1, J1 (cited by id) | ops and trigger evidence |

The orphan computation was a Python script over COVERAGE_MATRIX, BACKLOG, DEFERRALS (owed rows by event-head status),
the 00_MANIFEST rows 184–187, their ticket contracts, and risk-register routes. It expands the id shorthand
(`/`, `…`) the way A3 does.

## 10. Limits: what was not verified

- **Unverified RISK rows.** RISK-P3-02 (whether `operating_relationship` is populated at scale) and RISK-P3-07
  (national UCR/USPS crosswalk content) are marked still-open without a DB read, because production is read-only
  and the hosted spine was not queried.
- **Unverified quiet triggers.** ADR-045 (whether L4 closure has a persistence owner) and ADR-108 (the service
  max-scale of 20 against revision max-instances of 2, versus the pool budget) are marked quiet but flagged for
  verification.
- **Prospective triggers.** "Fired" for ADR-107 and ADR-114 means the named precondition, a planned large land, is
  now in scope. Neither threshold has been crossed.
- **Scheduled but not yet run.** "Scheduled" in `ops/cadence.toml` does not prove a job has run. G1 NEW-8 records 33
  triggers that first fire 10-01 to 10-21. Closures cite scheduled jobs only where the deferral or run records show
  a live execution (P25.x, P26.x) or where scheduling was the row's whole scope.
