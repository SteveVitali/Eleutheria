# SIG current build state — deterministic projection (advisory)

> **Authority:** `docs/build/LEDGER.md` CURRENT STATE + the DEFERRALS.md
> compatibility cells remain the control authority. This view is derived from
> the hashed `input-manifest/1` (`manifest.json`); it never writes control
> state. Shadow mode — the single-writer cutover deferral is `D-R10-MEMORY-2`
> input_commit: `8a8fb36568f9a4050852c9f6cff68f83303622ae` · inputs hashed: 1168 · wall-clock receipt: `receipt.json`

## Control (advisory read of LEDGER.md)

- projectStatus `IN_PROGRESS` · round `11` · nextTicket `P36.50` · lastCompleted `P36.49`
- chainTip `r11/P36.49-known-issues-and-issues-log` · returnPass `P21.5,P31.4,P32.18,P32.19,P32.20,P32.21,P32.22,P32.23a,P32.25,P34.3,P34.4,P34.5,P34.6,P34.17,P34.18,P34.21a,P34.21b,P34.38,P34.39b,P34.40,P34.42b,P34.43,P34.44b…` · updatedAt `2026-11-02T17:22Z`

## Obligations

- 212 obligations · **131 owed** (128 OPEN, 3 PARTIAL) · 81 terminal
- 717 events (51 transitions beyond anchors) · 15 status conflicts reconciled by recorded events · 8 documented in `reconciliations.json`

- `obligations` → see [obligations.md](obligations.md) (complete — 131 rows)

## RETURN PASS — owed live legs (generated region)

- the generated LEDGER region `### RETURN PASS — current` is the
  authority (`return_pass.py`); owed obligations in a row land there.
| ticket | obligations | re-run line |
|---|---|---|
| P21.5 | D-P21.5-1 (PARTIAL) | chain 482 **P37.55** (11D, after P34.21b) (#61 — prepare-only re-run row 76, #76) |
| P31.4 | D-P31.4-1 | chain 247 **P34.39a** (11A — leg ran 2026-10-14 `fail` → `deferral-row`; a `P34.39a-live-2` re-read rides the call); verify = the D-P31.4-1 command; P34.39b car… |
| P32.18 | D-P32.18-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.18-okc-dossier/LIVE_RETURN_PASS.json` (#175) |
| P32.19 | D-P32.19-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.19-tulsa-dossier/LIVE_RETURN_PASS.json` (#176) |
| P32.20 | D-P32.20-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.20-san-diego-dossier/LIVE_RETURN_PASS.json` (#177) |
| P32.21 | D-P32.21-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.21-acquisition-pilot/ACQ_PILOT_RETURN_PASS.json` (#178… |
| P32.22 | queued D-R10-LIVE-1 | chain 338 **P35.61** (11B — ≥48 h after P34.46, post-11B writes); packet `docs/build/reports/p32.22-bounded-recovery/LIVE_RETURN_PASS.json` (#179) |
| P32.23a | queued D-P32.23a-1 | chain 339 **P35.62** (after P35.61); packet `docs/build/reports/p32.23a-release-candidate/LIVE_RETURN_PASS.json` (#180) |
| P32.25 | queued D-R10-PUBLISH-1 | chain 341 **P35.63** (after P35.62); rollback cases `reports/p32.25-accepted-release-verification/LIVE_RETURN_PASS.json` (#182) |
| — | HG-05 (old P23.1 row; no deferral) | none — operator action, not in `returnPass` |
| P34.3 | D-P34.3-1 | `implement-spec spec=docs/tickets/204_P34.3__ops-data-protection.md live_verification=true` |
| P34.4 | D-P34.4-1 · D-P34.4-2 | `implement-spec spec=docs/tickets/205_P34.4__alerts-that-reach-a-human.md live_verification=true` · none — operator action |
| P34.5 | D-P34.5-1 · D-P34.5-2 · D-P34.5-3 | `cost-guard.sh --apply testbudget-delete --fired-confirmed` · none — operator action (OP-12) · `implement-spec spec=docs/tickets/206_P34.5__cost-guard-budget-al… |
| P34.6 | D-P34.6-2 · D-P34.6-3 · D-P34.6-4 · D-P34.6-5 · D-P34.6-6 | `logical-export.sh --apply export|lifecycle|relabel --go` · `restore-drill.sh --apply fullrestore --go` · `the drill re-run after P34.46's schema-changing deplo… |
| P34.50 | D-P34.50-1 | none — operator action; **P35.67** (row 263) is the verifying probe row (#201) |
| P34.17 | D-P34.17-1 | `implement-spec spec=docs/tickets/220_P34.17__web-honesty-wave-and-republish-1.md live_verification=true` |
| P34.18 | D-P34.18-1 | `implement-spec spec=docs/tickets/221_P34.18__personal-handle-source-id-rename.md live_verification=true` |
| P34.21a | D-P34.21a-1 | `implement-spec spec=docs/tickets/223_P34.21a__attribution-gate-sink-rights-and-backfill.md live_verification=true` |
| P34.21b | D-P34.21b-1 · D-P34.21b-2 | `implement-spec spec=docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md live_verification=true` |
| P34.38 | — | `implement-spec spec=docs/tickets/246_P34.38__sources-pilot-prep-and-registry-rows.md live_verification=true` |
| P34.39b | — | `implement-spec spec=docs/tickets/248_P34.39b__first-fire-read-backs.md live_verification=true` |
| P36.2 | D-P36.2-1 | `implement-spec spec=docs/tickets/350_P36.2__rights-flip-decline-batch-and-terms-capture.md live_verification=true` |
| P34.40 | — | `implement-spec spec=docs/tickets/249_P34.40__serving-topology-dark.md live_verification=true` |
| P34.42b | — | `implement-spec spec=docs/tickets/252_P34.42b__least-privilege-job-identities-remove-editor.md live_verification=true` |
| P34.43 | — | `implement-spec spec=docs/tickets/253_P34.43__execution-host-and-least-privilege-db-logins.md live_verification=true` |
| P34.49 | — | `implement-spec spec=docs/tickets/254_P34.49__part-viii-at-rest-audit.md live_verification=true` |
| P34.44b | — | `implement-spec spec=docs/tickets/256_P34.44b__quality-baseline-run-and-nightly-probe.md live_verification=true` |
| P34.45 | — | `implement-spec spec=docs/tickets/257_P34.45__honest-evaluation-posture.md live_verification=true` |
| P34.46 | — | `implement-spec spec=docs/tickets/258_P34.46__round10-schema-allows-and-api-roll.md live_verification=true` |
| P34.47 | — | `implement-spec spec=docs/tickets/259_P34.47__sub-round-11a-acceptance.md live_verification=true` |
| P35.57 | — | `implement-spec spec=docs/tickets/261_P35.57__api-release-parity.md live_verification=true` |
| P35.5 | — | `implement-spec spec=docs/tickets/262_P35.5__zero-egress-distribution-host.md live_verification=true` |
| P35.67 | — | `implement-spec spec=docs/tickets/263_P35.67__post-dns-cutover-probe.md live_verification=true` |
| P35.1a | — | `implement-spec spec=docs/tickets/264_P35.1a__scheduler-of-record-live-diff-cron-lint.md live_verification=true` |
| P35.1a1 | — | `implement-spec spec=docs/tickets/287a_P35.1a1__seed-declared-jobs-paused.md live_verification=true` |
| P35.11 | — | `implement-spec spec=docs/tickets/271_P35.11__wave-a-activation.md live_verification=true` |
| P35.14a | — | `implement-spec spec=docs/tickets/272_P35.14a__vocabulary-conformance-closed-vocabulary.md live_verification=true` |
| P35.14b | — | `implement-spec spec=docs/tickets/273_P35.14b__entity-typing-and-hosted-check-constraint.md live_verification=true` |
| P35.15a | — | `implement-spec spec=docs/tickets/274_P35.15a__technology-typing-slug-and-facets.md live_verification=true` |
| P35.15b | — | `implement-spec spec=docs/tickets/275_P35.15b__technology-backfill.md live_verification=true` |
| P36.12 | — | `implement-spec spec=docs/tickets/290_P36.12__wave-b-activation.md live_verification=true` |
| P35.1b | — | `implement-spec spec=docs/tickets/291_P35.1b__fleet-hygiene.md live_verification=true` |
| P35.1c | — | `implement-spec spec=docs/tickets/291a_P35.1c__dispatcher-consolidation.md live_verification=true` |
| P35.16 | — | `implement-spec spec=docs/tickets/296_P35.16__geometry-defects-at-ingest.md live_verification=true` |
| P35.17 | — | `implement-spec spec=docs/tickets/297_P35.17__jurisdiction-registry-and-boundary-pack.md live_verification=true` |
| P35.24 | — | `implement-spec spec=docs/tickets/303_P35.24__truthful-subject-keys-and-re-keying.md live_verification=true` |
| P35.25 | — | `implement-spec spec=docs/tickets/304_P35.25__declared-lineage-namespaces-independence.md live_verification=true` |
| P35.26 | — | `implement-spec spec=docs/tickets/305_P35.26__roles-and-time-backend.md live_verification=true` |
| P35.41 | — | `implement-spec spec=docs/tickets/320_P35.41__freshness-semantics-v2.md live_verification=true` |
| P35.53 | D-P35.53-1 | `implement-spec spec=docs/tickets/331_P35.53__release-pipeline-and-staging-origins.md live_verification=true` |
| P35.59 | — | `implement-spec spec=docs/tickets/336_P35.59__dark-cutover-to-release-layout.md live_verification=true` |
| P35.61 | — | `implement-spec spec=docs/tickets/338_P35.61__round10-live-pass-audit-apply-freeze.md live_verification=true` |
| P35.62 | — | `implement-spec spec=docs/tickets/339_P35.62__round10-production-candidate.md live_verification=true` |
| P35.63 | — | `implement-spec spec=docs/tickets/341_P35.63__first-model-release-to-production.md live_verification=true` |
| P35.64 | — | `implement-spec spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md live_verification=true` |
| P37.2 | — | `implement-spec spec=docs/tickets/345_P37.2__wave-c-osm-national-alpr-layer.md live_verification=true` |
| P35.2 | D-P35.2-1 | `implement-spec spec=docs/tickets/346_P35.2__alerting-as-code-and-escalation.md live_verification=true` |
| P35.21 | D-P35.21-1 | `implement-spec spec=docs/tickets/347_P35.21__partner-name-audit-run.md live_verification=true` |
| P35.23 | D-P35.23-1 | `implement-spec spec=docs/tickets/348_P35.23__real-data-regression-corpus.md live_verification=true` |
| P36.76 | D-P36.76-1 · D-P36.76-2 | `implement-spec spec=docs/tickets/351_P36.76__axon-connect-connector.md live_verification=true` |
| P36.77 | D-P36.77-1 · D-P36.77-2 | `implement-spec spec=docs/tickets/352_P36.77__documentcloud-muckrock-connector.md live_verification=true` |
| P36.78 | D-P36.78-1 · D-P36.78-2 | `implement-spec spec=docs/tickets/353_P36.78__sourcewell-omnia-contract-pages.md live_verification=true` |
| P36.13 | D-P36.13-1 | `implement-spec spec=docs/tickets/354_P36.13__api-rate-limits.md live_verification=true` |
| P36.79 | D-P36.79-1 | `implement-spec spec=docs/tickets/371_P36.79__held-out-search-relevance-set.md live_verification=true` |
| P36.33 | D-P36.33-1 | `implement-spec spec=docs/tickets/374_P36.33__basemap-pipeline-and-host.md live_verification=true` |
| P36.38 | D-P36.38-1 | `implement-spec spec=docs/tickets/379_P36.38__search-api-serving-v2.md live_verification=true` |
| P36.75 | D-P36.75-1 | `implement-spec spec=docs/tickets/385_P36.75__flock-share-lists-configured-access.md live_verification=true` |
| P36.43 | D-P36.43-1 | `implement-spec spec=docs/tickets/386_P36.43__status-lane.md live_verification=true` |
| P36.44 | D-P36.44-1 | `implement-spec spec=docs/tickets/387_P36.44__release-cadence-automation.md live_verification=true` |
| P36.46 | D-P36.46-1 | `implement-spec spec=docs/tickets/389_P36.46__execution-keyed-ingestion-history.md live_verification=true` |

## Known inconsistencies (preserved, never synthesized)

- none — every P32.1 baseline conflict is either reconciled by a recorded event interpretation (old values preserved on the anchor) or documented in `reconciliations.json`; anything new would appear here and fail `verify`

## Evidence domains — recorded evidence only

- `domains` → see [domains.md](domains.md) (complete — 5 rows)

## Source funnel (recorded baseline, domain-labelled)

| unit | recorded value | domain · date · evidence |
|---|---|---|
| discovered | `**339** registered `[sources.*]` + **27** researched candidates` | `implementation · 2026-09-27 · `sources.toml`, `source-candidates.csv`` |
| reviewed | `rights blocks + disposition artifacts per source (`p293_dispositions.json` valid` | `implementation · 2026-09-27` |
| permitted | `**236** `ingestion_permitted = true` (of 339)` | `implementation · 2026-09-27 · counted from `sources.toml`` |
| mapped | `8 accountability sources wired (P31.12/13, shadow diff=0); earlier classes per t` | `fixture+implementation · recorded 2026-09-26` |
| captured | `OCFL-backed captures behind every landed claim; per-job counts recorded per run ` | `hosted · recorded 2026-09-26 (P31.12/13 run ledgers)` |
| extracted | `2,074,963 admissible claims on the hosted spine (after P30.2a materialization)` | `hosted · recorded 2026-09-24 (P30.2a run)` |
| linked | `1,872,344 envelopes → 227,998 resolved sites (from 230,330 obs-level records, de` | `hosted · recorded 2026-09-24/25` |
| published | `national surface live: export `sig-2026-09-27-ce480ab1` published to `…-sig-publ` | `public · recorded 2026-09-27 (P31.16 publish half)` |

## Releases (recorded)

- public release: `national surface live: export `sig-2026-09-27-ce480ab1` published to `…-sig-public`, `sig-web` rolled `sha256:d8244804…`, 12 z0–z14 tiles, 1`
- database run ids: not recorded in projection inputs — hosted-domain facts are recorded evidence only (never measured by this offline tool)

## Coverage — scoped assessments + historical CSV

- `coverage` spilled across 5 pages (complete): [coverage-1.md](coverage-1.md) [coverage-2.md](coverage-2.md) [coverage-3.md](coverage-3.md) [coverage-4.md](coverage-4.md) [coverage-5.md](coverage-5.md)

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

