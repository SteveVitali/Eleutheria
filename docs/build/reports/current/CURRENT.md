# SIG current build state — deterministic projection (advisory)

> **Authority:** `docs/build/LEDGER.md` CURRENT STATE + the DEFERRALS.md
> compatibility cells remain the control authority. This view is derived from
> the hashed `input-manifest/1` (`manifest.json`); it never writes control
> state. Shadow mode — the single-writer protocol is `D-R10-MEMORY-1` → P32.8.
> input_commit: `b132bbbb8e36951fb5f3a8ec8a392cbb6449fc99` · inputs hashed: 506 · wall-clock receipt: `receipt.json`

## Control (advisory read of LEDGER.md)

- projectStatus `IN-PROGRESS` · round `10` · nextTicket `P32.11` · lastCompleted `P32.10a`
- chainTip `devin/p32-10a-disposition-single-clock-authority` · returnPass `P31.16(**DONE 2026-09-27 — HG-11 granted by the operator (sign-off commit `81957c2`) + the publish half landed: `REPUBLISH_LIVE_2026-09-27.md`; public partition…` · updatedAt `2026-09-27 — P32.10a (row 170.5/170a) DONE: PR`

## Obligations

- 90 obligations · **37 owed** (32 OPEN, 5 PARTIAL) · 53 terminal
- 90 events (0 transitions beyond anchors) · 7 status conflicts reconciled by recorded events · 8 documented in `reconciliations.json`

| obligation | status | owner | landing | how to verify |
|---|---|---|---|---|
| D-P21.3-2 | OPEN | operator | operator action; no engineering work remains | no live fetch; no-token-literal test passes |
| D-P21.5-1 | PARTIAL | operator | operator action (repo-visibility decision for the SWH save-now leg; HG-07 for any future credentialed leg) | free paths (tiles/.torrent/degraded/SWH-save) real; credentialed steps dry-run/stub tested. **Proxy-now re-verified 2026-09-10 by the INFRA.1 (GL-INFRA-01) re-r… |
| D-P21.7-1 | OPEN | operator | operator action, then the one-step re-run in `docs/build/CONTRIBUTION_BACK_LIVE.md` | **proxy-now re-verified 2026-09-10 by the CONTRIB.1 (GL-CONTRIB-01) re-run (`devin/p21-7-contrib-rerun`, base `devin/p21-5-infra-rerun`, prepare-only)** on the … |
| D-JURIS.2-1 | PARTIAL | operator | operator act | `sig-connectors review-status --source <id>` shows all five gate fields True; `sig-connectors run --source <id> --mode live` stops refusing exit 3 and writes a … |
| D-SOURCES.2-2 | OPEN | operator | operator decision (decline is a valid close) | a flip (or a recorded decline) with review metadata; then `run --mode live` stops refusing exit 3 |
| D-SOURCES.7-1 | OPEN | reviewer | reviewer decision | `sig-connectors gate --source dot_511_<st>` goes green after a recorded flip; `run --mode live` then produces captures instead of exit 3 |
| D-SOURCES.7-2 | OPEN | operator | operator action | a keyed live run produces captures + claims; the `[[enumerated]]` rows can graduate to `[[targets]]` for states still lacking an open layer |
| D-SOURCES.8-1 | PARTIAL | reviewer | reviewer decision | `sig-connectors gate --source camreg_<id>` goes green after a recorded flip; `run --mode live` then produces captures instead of exit 3 |
| D-SOURCES.8-2 | OPEN | operator | operator action | a keyed live run produces captures + claims; the `[[enumerated]]` rows can graduate to `[[targets]]` |
| D-SOURCES.9-1 | OPEN | reviewer | reviewer action | `sig-connectors gate --source procportal_chicago_il` goes green after a recorded flip; `run --mode live` then produces captures instead of exit 3 |
| D-SOURCES.9-2 | OPEN | reviewer + external | reviewer decision (HG-03), then an ingest run | a live run fetches a tenant portal index instead of the recorded politeness refusal |
| D-SOURCES.9-3 | OPEN | external | a documented public endpoint appears + reviewable terms; then HG-03 | a live run fetches a portal index instead of the recorded challenge disappearance |
| D-SOURCES.9-4 | OPEN | reviewer | reviewer action | `sig-connectors gate --source bidnet_direct` goes green after a recorded flip; `run --mode live` then produces captures instead of exit 3 |
| D-SOURCES.12-1 | PARTIAL | engineering | BL-055, no chain row | `sig-connectors gate --source camreg_stalbert_ab` goes green after a recorded flip; the reviewed artifact's gated rows are the enumerable worklist (`spdx=null` … |
| D-FEDERAL.1-1 | OPEN | scheduled | the `sig-sched-sam-gov` cron (automatic), then a +0 re-run check | GCS run row under `gs://…-sig-restricted/ops/runs/sam_gov/2026-09-19/` shows `outcome=ok` with `claims_added` for the widened sweep; hosted `claim` delta for `p… |
| D-R6.1-EVAL | OPEN | maintainer + reviewers | **Round 10**: the human review campaign → P31.18 re-derivation | after P28.1 lands: re-`build_gold_set` from the live loop's human decisions → re-freeze a versioned holdout → re-measure P/R/F1 + B-cubed + LLM-vs-human κ on th… |
| D-R7.1-AUTH | OPEN | operator | operator decision | when unblocked: author a NEW ADR + ticket for external-IdP OAuth (pseudonymous subject id + tier only; no passwords/PII) behind anti-poisoning + the safety plan… |
| D-R7.2-SEND | OPEN | operator | operator action; never automatic | when unblocked: a consenting `Filer` (`consent_granted=True`, `acknowledged_public_act=True`, residency-valid) is bound and `tasks.records_request.RecordsReques… |
| D-P30.1-2 | OPEN | engineering | BL-057, no chain row | an interrupted large-source run, restarted, issues no fetch for pages already captured and inserts only the uncommitted tail, reaching the same final count as a… |
| D-P30.2a-1 | OPEN | engineering | BL-057, no chain row | `make gen` + `make verify-gen` clean; re-run the inventory (`docs/build/reports/p30.2a-hosted/`) → claims with a directness row rise; `ops/gcp/materialize.sh --… |
| D-P30.2a-2 | OPEN | engineering | BL-057, no chain row | a re-ingest of an unchanged registry adds `claim_evidence` rows (+0 claims); a fixture A → B → A resolves to A; the resolution re-run records the new dating bas… |
| D-P30.2b-1 | OPEN | engineering + reviewers | **Round 10** (human review campaign → P31.18); engineering half landed | an accepted proposal appears as an `auto_write`-equivalent human edge in the next run's clusters (N drops by one), a rejected one never clusters; `camera_site_r… |
| D-P30.2b-2 | OPEN | engineering | **Round 10** (with the P31.18 evaluation refresh) | a rules-v3 soft conflict for name-level device-kind/place disagreement; measured on a new frozen holdout; tier 3g precision re-measured ≥ 0.98 |
| D-P30.3-1 | PARTIAL | engineering | BL-056, no chain row | re-run the national export → `web/freshness.json` rows carry ISO dates; `/data-freshness/` shows them, no `not-recorded` for sources with a completed run |
| D-P30.3-2 | OPEN | engineering | BL-056, no chain row | the per-compartment archives carry z0–z14; the island layers them instead of `points.json`; `/map/points.json` compressed |
| D-P30.3-3 | OPEN | engineering | BL-056, no chain row | the export writes `web/presentation/*.json`; the pages render them in export mode |
| D-P31.1-2 | OPEN | engineering (chain seam) | P31.4 | a `gs://…-sig-restricted/ops/probes/…` sweep row with `service = sig-api-health`, `ok = true` |
| D-P31.3-1 | OPEN | engineering | P31.4 | P31.4's run ledger records the claims/min and round trips per claim for a pass that inserts `N > 0` new claims on the hosted spine, then the +0 re-run |
| D-P31.4-1 | OPEN | scheduled (cron) | automatic at the 2026-10-10T03:35Z cron; verify per the row's exact command (run rows + `ingest_run_completion`, ≈ 12–15 min expected) | the batch-05 run rows under `gs://…-sig-restricted/ops/runs/camreg_osm_surveillance/2026-10-10/` show `outcome` ok/partial, `fetches` 158 (or fewer only with `r… |
| D-R10-HUMAN-1 | OPEN | HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 | HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 | Signed HUMAN-H4 development/dossier and HUMAN-H5 confirmatory readouts; frozen-candidate-specific sample/label digests; blind/adjudication records; dossier rubr… |
| D-R10-SOURCES-1 | OPEN | P32.18–21 | P32.18 | Per-target green registry/rights basis; actual captured digests; measured acquisition funnel under the prescribed family/document/protocol caps |
| D-R10-LIVE-1 | OPEN | P32.22/P32.23a | P32.22 → P32.23a | Before/after inventories, occurrence/disposition lineage, resource measurements, restart/+0 checks and consistent final release manifest |
| D-R10-PUBLISH-1 | OPEN | operator | GATE-G3 → P32.25 | Signed candidate-specific readout; approved artifact digests; safe origin/cache rollback and unauthenticated public checks |
| D-R10-MEMORY-1 | OPEN | P32.8 | P32.8 | Both worker closeout and orchestrator repair use one authoritative-chain protocol; stale-worktree/uncertain-PR/crash tests and cutover commit recorded |
| D-R10-USERS-1 | OPEN | P32.24 | P32.24 | Frozen-release task results with actual numerator/denominator, uncertainty/comprehension failures and accessibility session; no simulated agents counted as user… |
| D-P32.3-1 | OPEN | operator | BL-058 | every `sig.org.name` key in `entity_identifier` has a recorded disposition (`same_as`/`distinct` decision rows or an accepted "keep" record); the report's `spli… |
| D-P32.10a-1 | OPEN | engineering | P32.5 | `sqitch verify` over a fully deployed container exits 0 (today: `ERROR: division by zero` at `verify/shared_temporal_contract.sql:30`, `count(*)=28`) |
## Known inconsistencies (preserved, never synthesized)

- none — every P32.1 baseline conflict is either reconciled by a recorded event interpretation (old values preserved on the anchor) or documented in `reconciliations.json`; anything new would appear here and fail `verify`

## Evidence domains — recorded evidence only

| domain | latest recorded evidence | assessments |
|---|---|---|
| fixture | mapped: 8 accountability sources wired (P31.12/13, shadow diff=0); e (fixture+implementation · recorded 2026-09-26) | — |
| implementation | discovered: **339** registered `[sources.*]` + **27** researched candida (implementation · 2026-09-27 · `sources.toml`, `source-candid); reviewed: rights blocks + disposition artifacts per source (`p293_disp (implementation · 2026-09-27); permitted: **236** `ingestion_permitted = true` (of 339) (implementation · 2026-09-27 · counted from `sources.toml`) | SIG-MEM-001=MET (2026-10-14); SIG-MEM-002=MET (2026-10-14); SIG-MEM-003=MISSING (2026-10-14); SIG-MEM-004=MISSING (2026-10-14) |
| composed-db | — | — |
| hosted | captured: OCFL-backed captures behind every landed claim; per-job coun (hosted · recorded 2026-09-26 (P31.12/13 run ledgers)); extracted: 2,074,963 admissible claims on the hosted spine (after P30.2 (hosted · recorded 2026-09-24 (P30.2a run)); linked: 1,872,344 envelopes → 227,998 resolved sites (from 230,330 o (hosted · recorded 2026-09-24/25) | — |
| public | published: national surface live: export `sig-2026-09-27-ce480ab1` publ (public · recorded 2026-09-27 (P31.16 publish half)) | — |

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

| requirement | domain | verdict | assessed_at | supersedes |
|---|---|---|---|---|
| SIG-MEM-001 | implementation | MET | 2026-10-14 | — |
| SIG-MEM-002 | implementation | MET | 2026-10-14 | — |
| SIG-MEM-003 | implementation | MISSING | 2026-10-14 | — |
| SIG-MEM-004 | implementation | MISSING | 2026-10-14 | — |
- historical CSV: 715 dated rows in `docs/build/COVERAGE_MATRIX.csv` (labelled `historical/csv`, preserved verbatim)

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

