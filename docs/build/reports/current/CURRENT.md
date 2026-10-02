# SIG current build state — deterministic projection (advisory)

> **Authority:** `docs/build/LEDGER.md` CURRENT STATE + the DEFERRALS.md
> compatibility cells remain the control authority. This view is derived from
> the hashed `input-manifest/1` (`manifest.json`); it never writes control
> state. Shadow mode — the single-writer protocol is `D-R10-MEMORY-1` → P32.8.
> input_commit: `87a1ffe12e40ea059b7b834363f102a8552ac9e3` · inputs hashed: 925 · wall-clock receipt: `receipt.json`

## Control (advisory read of LEDGER.md)

- projectStatus `IN_PROGRESS` · round `11` · nextTicket `P34.4` · lastCompleted `P34.3`
- chainTip `r11/P34.3-ops-data-protection` · returnPass `P21.5, P31.4, P32.18, P32.19, P32.20, P32.21, P32.22, P32.23a, P32.25, P34.3` · updatedAt `2026-10-02T05:28:09Z`

## Obligations

- 132 obligations · **71 owed** (67 OPEN, 4 PARTIAL) · 61 terminal
- 132 events (0 transitions beyond anchors) · 15 status conflicts reconciled by recorded events · 8 documented in `reconciliations.json`

- `obligations` → see [obligations.md](obligations.md) (complete — 71 rows)

## Known inconsistencies (preserved, never synthesized)

- none — every P32.1 baseline conflict is either reconciled by a recorded event interpretation (old values preserved on the anchor) or documented in `reconciliations.json`; anything new would appear here and fail `verify`

## Evidence domains — recorded evidence only

| domain | latest recorded evidence | assessments |
|---|---|---|
| fixture | mapped: 8 accountability sources wired (P31.12/13, shadow diff=0); e (fixture+implementation · recorded 2026-09-26) | — |
| implementation | discovered: **339** registered `[sources.*]` + **27** researched candida (implementation · 2026-09-27 · `sources.toml`, `source-candid); reviewed: rights blocks + disposition artifacts per source (`p293_disp (implementation · 2026-09-27); permitted: **236** `ingestion_permitted = true` (of 339) (implementation · 2026-09-27 · counted from `sources.toml`) | SIG-CHART-033=MISSING (2026-10-01); SIG-CONF-002=MISSING (2026-10-01); SIG-CONF-003=MISSING (2026-10-01); SIG-CONF-006=MISSING (2026-10-01); SIG-CONF-007=MISSING (2026-10-01); SIG-CONF-008=MISSING (2026-10-01); SIG-CONF-014=MISSING (2026-10-01); SIG-CONTRIB-012=MISSING (2026-10-01); SIG-CONTRIB-012a=MISSING (2026-10-01); SIG-CONTRIB-013=PARTIAL (2026-10-01); SIG-CONTRIB-019=PARTIAL (2026-10-01); SIG-ENG-002=PARTIAL (2026-10-01); SIG-ENG-004=N/A-RATIONALE (2026-10-01); SIG-ENG-005=PARTIAL (2026-10-01); SIG-ENG-034=MET (2026-10-01); SIG-ENG-040=MISSING (2026-10-01); SIG-ENG-041=MISSING (2026-10-01); SIG-ENG-042=MISSING (2026-10-01); SIG-ENG-043=MISSING (2026-10-01); SIG-ENG-044=MISSING (2026-10-01); SIG-ENG-046=MISSING (2026-10-01); SIG-ENG-046=MET-ENGINEERED(D-P34.1-1) (2026-10-01); SIG-EPIS-012=MET (2026-10-01); SIG-EPIS-018=MET (2026-10-01); SIG-EPIS-022=MET (2026-10-01); SIG-GEO-002=PARTIAL (2026-10-01); SIG-GEO-005=PARTIAL (2026-10-01); SIG-GEO-007=N/A-RATIONALE (2026-10-01); SIG-GOV-021=MET (2026-10-01); SIG-GOV-023=MET (2026-10-01); SIG-GOV-024=PARTIAL (2026-10-01); SIG-IDENT-027=PARTIAL (2026-10-01); SIG-IDENT-028=PARTIAL (2026-10-01); SIG-INGEST-004=PARTIAL (2026-10-01); SIG-INGEST-005=PARTIAL (2026-10-01); SIG-INGEST-006=PARTIAL (2026-10-01); SIG-INGEST-007=MET (2026-10-01); SIG-INGEST-008=PARTIAL (2026-10-01); SIG-INGEST-010=PARTIAL (2026-10-01); SIG-INGEST-025a=PARTIAL (2026-10-01); SIG-INGEST-025b=PARTIAL (2026-10-01); SIG-INGEST-025c=PARTIAL (2026-10-01); SIG-INGEST-041=PARTIAL (2026-10-01); SIG-INGEST-048=PARTIAL (2026-10-01); SIG-LIC-006=PARTIAL (2026-10-01); SIG-LIC-009=WAIVED(ADR-182) (2026-10-01); SIG-MEM-001=MET (2026-10-14); SIG-MEM-002=MET (2026-10-14); SIG-MEM-002=PARTIAL (2026-10-01); SIG-MEM-003=MISSING (2026-10-14); SIG-MEM-004=MISSING (2026-10-14); SIG-MEM-004=MET (2026-09-28); SIG-MEM-005=MISSING (2026-10-01); SIG-MEM-006=MISSING (2026-10-01); SIG-MEM-007=MISSING (2026-10-01); SIG-MEM-007=MET-ENGINEERED(D-P34.2-2) (2026-10-02); SIG-MEM-008=MISSING (2026-10-01); SIG-MEM-009=MISSING (2026-10-01); SIG-MEM-010=MISSING (2026-10-01); SIG-MEM-011=MISSING (2026-10-01); SIG-MEM-012=MISSING (2026-10-01); SIG-ONTO-001=PARTIAL (2026-10-01); SIG-ONTO-005=MET (2026-10-01); SIG-ONTO-028=PARTIAL (2026-10-01); SIG-ONTO-035=PARTIAL (2026-10-01); SIG-ONTO-051=PARTIAL (2026-10-01); SIG-ONTO-054=MET (2026-10-01); SIG-ONTO-055=PARTIAL (2026-10-01); SIG-ONTO-057=PARTIAL (2026-10-01); SIG-ONTO-057a=PARTIAL (2026-10-01); SIG-ONTO-060=PARTIAL (2026-10-01); SIG-PUB-014=MET (2026-10-01); SIG-PUB-014b=MET (2026-10-01); SIG-RECON-052=PARTIAL (2026-10-01); SIG-REL-014=MISSING (2026-10-01); SIG-STORE-004=PARTIAL (2026-10-01); SIG-STORE-005=PARTIAL (2026-10-01); SIG-STORE-037=PARTIAL (2026-10-01); SIG-STORE-044=PARTIAL (2026-10-01); SIG-STORE-045=PARTIAL (2026-10-01); SIG-UI-010=MET (2026-10-01); SIG-UI-038=MET (2026-10-01); SIG-UI-040=MET-DIFFERENTLY(ADR-108;ADR-133) (2026-10-01); SIG-UI-040=MET-DIFFERENTLY (2026-10-01); SIG-UI-047=MET (2026-10-01) |
| composed-db | — | SIG-ENG-045=MISSING (2026-10-01); SIG-PUB-012=PARTIAL (2026-10-01); SIG-STORE-011=WAIVED(ADR-189) (2026-10-01); SIG-STORE-013=MET (2026-10-01) |
| hosted | captured: OCFL-backed captures behind every landed claim; per-job coun (hosted · recorded 2026-09-26 (P31.12/13 run ledgers)); extracted: 2,074,963 admissible claims on the hosted spine (after P30.2 (hosted · recorded 2026-09-24 (P30.2a run)); linked: 1,872,344 envelopes → 227,998 resolved sites (from 230,330 o (hosted · recorded 2026-09-24/25) | SIG-ACQ-004=MET-ENGINEERED(D-P32.21-1) (2026-10-01); SIG-CHART-017=PARTIAL (2026-10-01); SIG-CONF-009=MISSING (2026-10-01); SIG-CONF-013=MISSING (2026-10-01); SIG-ENG-024=AT-RISK-INTEGRATION (2026-10-01); SIG-EPIS-009=PARTIAL (2026-10-01); SIG-EPIS-029=PARTIAL (2026-10-01); SIG-EVAL-004=WAIVED(ADR-153) (2026-10-01); SIG-EVID-001=PARTIAL (2026-10-01); SIG-EVID-019=MET-ENGINEERED(D-P21.5-1;D-R11-ARCHIVE-1) (2026-10-01); SIG-GOV-008=WAIVED(ADR-181) (2026-10-01); SIG-GOV-022=MET-ENGINEERED(D-P21.5-1;D-R11-ARCHIVE-1) (2026-10-01); SIG-INGEST-035=WAIVED(ADR-188) (2026-10-01); SIG-INGEST-036=WAIVED(ADR-187) (2026-10-01); SIG-INGEST-037=WAIVED(ADR-182) (2026-10-01); SIG-INGEST-046b=MET (2026-10-01); SIG-INGEST-046c=MISSING (2026-10-01); SIG-OPS-001=MISSING (2026-10-01); SIG-OPS-002=MISSING (2026-10-01); SIG-OPS-003=MISSING (2026-10-01); SIG-OPS-004=MISSING (2026-10-01); SIG-OPS-005=MISSING (2026-10-01); SIG-OPS-006=MISSING (2026-10-01); SIG-OPS-007=MISSING (2026-10-01); SIG-OPS-008=MISSING (2026-10-01); SIG-OPS-009=MISSING (2026-10-01); SIG-OPS-010=MISSING (2026-10-01); SIG-OPS-011=MISSING (2026-10-01); SIG-OPS-012=MISSING (2026-10-01); SIG-RECON-018=AT-RISK-INTEGRATION (2026-10-01); SIG-SEC-005=PARTIAL (2026-10-01); SIG-SEC-006=PARTIAL (2026-10-01); SIG-SEC-007=MISSING (2026-10-01); SIG-SEC-008=MISSING (2026-10-01); SIG-SEC-009=MISSING (2026-10-01); SIG-SEC-010=MISSING (2026-10-01); SIG-SEC-011=MISSING (2026-10-01); SIG-STORE-048=MISSING (2026-10-01); SIG-TRUST-004=MET-ENGINEERED(D-P32.3-1) (2026-10-01); SIG-TRUST-007=MET-ENGINEERED(D-R10-LIVE-1) (2026-10-01); SIG-TRUST-008=MET-ENGINEERED(D-R10-LIVE-1) (2026-10-01) |
| public | published: national surface live: export `sig-2026-09-27-ce480ab1` publ (public · recorded 2026-09-27 (P31.16 publish half)) | SIG-CHART-019=PARTIAL (2026-10-01); SIG-CHART-034=PARTIAL (2026-10-01); SIG-CONF-001=MISSING (2026-10-01); SIG-CONF-004=MISSING (2026-10-01); SIG-CONF-005=MISSING (2026-10-01); SIG-CONF-010=MISSING (2026-10-01); SIG-CONF-011=MISSING (2026-10-01); SIG-CONF-012=MISSING (2026-10-01); SIG-DOS-002=MET-ENGINEERED(D-R10-HUMAN-1) (2026-10-01); SIG-DOS-003=MET-ENGINEERED(D-P32.18-1;D-R10-SOURCES-1;D-R10-HUMAN-1) (2026-10-01); SIG-DOS-004=MET-ENGINEERED(D-P32.19-1;D-R10-SOURCES-1;D-R10-HUMAN-1) (2026-10-01); SIG-DOS-005=MET-ENGINEERED(D-P32.20-1;D-R10-SOURCES-1;D-R10-HUMAN-1) (2026-10-01); SIG-EVAL-001=PARTIAL (2026-10-01); SIG-EVAL-002=PARTIAL (2026-10-01); SIG-EVAL-003=AT-RISK-INTEGRATION (2026-10-01); SIG-EVAL-005=MISSING (2026-10-01); SIG-EVAL-006=MISSING (2026-10-01); SIG-EVAL-007=MISSING (2026-10-01); SIG-FIND-006=MET-ENGINEERED(D-P32.16-1;D-R10-PUBLISH-1) (2026-10-01); SIG-FIND-007=MET-ENGINEERED(D-R10-USERS-1;D-P32.23a-1;D-R10-PUBLISH-1) (2026-10-01); SIG-GOV-001=WAIVED(ADR-180) (2026-10-01); SIG-GOV-002=WAIVED(ADR-180) (2026-10-01); SIG-GOV-003=WAIVED(ADR-186) (2026-10-01); SIG-GOV-012=WAIVED(ADR-165) (2026-10-01); SIG-GOV-013=WAIVED(ADR-165) (2026-10-01); SIG-GOV-015=WAIVED(ADR-164) (2026-10-01); SIG-GOV-016=PARTIAL (2026-10-01); SIG-IDENT-030=PARTIAL (2026-10-01); SIG-LIC-012=PARTIAL (2026-10-01); SIG-ONTO-064=PARTIAL (2026-10-01); SIG-ONTO-065=PARTIAL (2026-10-01); SIG-PUB-007=AT-RISK-INTEGRATION (2026-10-01); SIG-PUB-008=WAIVED(ADR-163) (2026-10-01); SIG-PUB-015=PARTIAL (2026-10-01); SIG-PUB-016=MISSING (2026-10-01); SIG-RECON-039=PARTIAL (2026-10-01); SIG-RECON-040=AT-RISK-INTEGRATION (2026-10-01); SIG-REL-001=MISSING (2026-10-01); SIG-REL-002=MISSING (2026-10-01); SIG-REL-003=MISSING (2026-10-01); SIG-REL-004=MISSING (2026-10-01); SIG-REL-005=MISSING (2026-10-01); SIG-REL-006=MISSING (2026-10-01); SIG-REL-007=MISSING (2026-10-01); SIG-REL-008=MISSING (2026-10-01); SIG-REL-009=MISSING (2026-10-01); SIG-REL-010=MISSING (2026-10-01); SIG-REL-011=MISSING (2026-10-01); SIG-REL-012=MISSING (2026-10-01); SIG-REL-013=MISSING (2026-10-01); SIG-REL-015=MISSING (2026-10-01); SIG-SEC-003=MISSING (2026-10-01); SIG-TRUST-009=MET-ENGINEERED(D-R10-PUBLISH-1;D-P32.23a-1;D-R10-LIVE-1;D-P32.16-1) (2026-10-01); SIG-TRUST-010=MET-ENGINEERED(D-R10-HUMAN-1;D-P32.23a-1) (2026-10-01); SIG-UI-001=PARTIAL (2026-10-01); SIG-UI-022=WAIVED(ADR-190) (2026-10-01); SIG-UI-042=WAIVED(ADR-179) (2026-10-01) |

## Source funnel (recorded baseline, domain-labelled)

| unit | recorded value | domain · date · evidence |
|---|---|---|
| discovered | **339** registered `[sources.*]` + **27** researched candidates | implementation · 2026-09-27 · `sources.toml`, `source-candidates.csv` |
| reviewed | rights blocks + disposition artifacts per source (`p293_dispositions.json` valid | implementation · 2026-09-27 |
| permitted | **236** `ingestion_permitted = true` (of 339) | implementation · 2026-09-27 · counted from `sources.toml` |
| mapped | 8 accountability sources wired (P31.12/13, shadow diff=0); earlier classes per t | fixture+implementation · recorded 2026-09-26 |
| captured | OCFL-backed captures behind every landed claim; per-job counts recorded per run  | hosted · recorded 2026-09-26 (P31.12/13 run ledgers) |
| extracted | 2,074,963 admissible claims on the hosted spine (after P30.2a materialization) | hosted · recorded 2026-09-24 (P30.2a run) |
| linked | 1,872,344 envelopes → 227,998 resolved sites (from 230,330 obs-level records, de | hosted · recorded 2026-09-24/25 |
| published | national surface live: export `sig-2026-09-27-ce480ab1` published to `…-sig-publ | public · recorded 2026-09-27 (P31.16 publish half) |

## Releases (recorded)

- public release: national surface live: export `sig-2026-09-27-ce480ab1` published to `…-sig-public`, `sig-web` rolled `sha256:d8244804…`, 12 z0–z14 tiles, 1
- database run ids: not recorded in projection inputs — hosted-domain facts are recorded evidence only (never measured by this offline tool)

## Coverage — scoped assessments + historical CSV

- `coverage` spilled across 2 pages (complete): [coverage-1.md](coverage-1.md) [coverage-2.md](coverage-2.md)

## Governing ADRs

| ADR | scope | file |
|---|---|---|
| ADR-073 | build-memory v2 — docs/build/ is the committed memory root; LEDGER.md holds the  | docs/adr/ADR-073-build-memory-committed-under-docs-build-scratch-retired.md |
| ADR-119 | P30.4 leak-scope policy — governs what a closeout/report may contain (referenced | docs/adr/ADR-119-project-id-leak-check-scoped-to-code-and-config.md |
| ADR-120 | the Round-10 six-stream program + the memory extension this projection serves (S | docs/adr/ADR-120-six-stream-integrity-investigation-and-memory-extension.md |
| ADR-125 | evidence-audit/1 + recovery-plan/1 — the offline audit/dry-run contracts the mem | docs/adr/ADR-125-legacy-evidence-audit-and-recovery-plan-contract.md |
| ADR-126 | obligation-event/1 + coverage-assessment/1 + current-projection/1 + input-manife | docs/adr/ADR-126-obligation-events-and-current-projection.md |

## Reading this view

- owed obligations are never dropped: if the table exceeds the view budget it
  moves to `obligations-N.md` link-out pages (still complete, same columns).
- `verify` recomputes every input digest; a changed input is reported stale.
- deferred work context: `docs/tickets/DEFERRALS.md` remains the register; this
  projection reproduces its leading cells via the event chains it validates.

