# SIG current build state — deterministic projection (advisory)

> **Authority:** `docs/build/LEDGER.md` CURRENT STATE + the DEFERRALS.md
> compatibility cells remain the control authority. This view is derived from
> the hashed `input-manifest/1` (`manifest.json`); it never writes control
> state. Shadow mode — the single-writer cutover deferral is `D-R10-MEMORY-2`
> input_commit: `f3c7c6abf4140df45d5feff82e5e2cb337f7c48a` · inputs hashed: 1268 · wall-clock receipt: `receipt.json`

## Control (advisory read of LEDGER.md)

- projectStatus `IN_PROGRESS` · round `11` · nextTicket `P37.51` · lastCompleted `P37.50`
- chainTip `r11/P37.50-agenda-platforms-v2` · returnPass `P21.5,P31.4,P32.18,P32.19,P32.20,P32.21,P32.22,P32.23a,P32.25,P34.3,P34.4,P34.5,P34.6,P34.17,P34.18,P34.21a,P34.21b,P34.38,P34.39b,P34.40,P34.42b,P34.43,P34.44b…` · updatedAt `2026-11-13T10:55Z`

## Obligations

- 241 obligations · **157 owed** (154 OPEN, 3 PARTIAL) · 84 terminal
- 756 events (59 transitions beyond anchors) · 15 status conflicts reconciled by recorded events · 8 documented in `reconciliations.json`

- `obligations` → see [obligations.md](obligations.md) (complete — 157 rows)

## RETURN PASS — owed live legs (generated region)

- the generated LEDGER region `### RETURN PASS — current` is the
  authority (`return_pass.py`); owed obligations in a row land there.
| ticket | obligations | re-run line |
|---|---|---|
| P21.5 | D-P21.5-1 | chain 482 **P37.55** (11D, after P34.21b) (#61 — prepare-only re-run row 76, #76) |
| P31.4 | D-P31.4-1 | chain 247 **P34.39a** (11A — leg ran 2026-10-14 `fail` → `deferral-row`; a `P34.39a-live-2` re-read rides call); verify = D-P31.4-1 command; P34.39b carries fir… |
| P32.18 | D-P32.18-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.18-okc-dossier/LIVE_RETURN_PASS.json` |
| P32.19 | D-P32.19-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.19-tulsa-dossier/LIVE_RETURN_PASS.json` |
| P32.20 | D-P32.20-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.20-san-diego-dossier/LIVE_RETURN_PASS.json` |
| P32.21 | D-P32.21-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.21-acquisition-pilot/ACQ_PILOT_RETURN_PASS.json` |
| P32.22 | `D-R10-LIVE-1` | chain 338 **P35.61** (11B — ≥48 h after P34.46, post-11B writes); packet `docs/build/reports/p32.22-bounded-recovery/LIVE_RETURN_PASS.json` |
| P32.23a | D-P32.23a-1 | chain 339 **P35.62** (after P35.61); packet `docs/build/reports/p32.23a-release-candidate/LIVE_RETURN_PASS.json` |
| P32.25 | D-R10-PUBLISH-1 | chain 341 **P35.63** (after P35.62); rollback cases `reports/p32.25-accepted-release-verification/LIVE_RETURN_PASS.json` |
| — | HG-05 (old P23.1 row; no deferral) | none — operator action, not in `returnPass` |
| P34.3 | D-P34.3-1 | `r11/P34.3-live-<n>` dispatch or `implement-spec spec=docs/tickets/204_P34.3__ops-data-protection.md live_verification=true` |
| P34.4 | D-P34.4-1 D-P34.4-2 | `r11/P34.4-live-<n>` dispatch or `implement-spec spec=docs/tickets/205_P34.4__alerts-that-reach-a-human.md live_verification=true` |
| P34.5 | D-P34.5-1 D-P34.5-2 D-P34.5-3 | -3: `implement-spec spec=docs/tickets/206_P34.5__cost-guard-budget-alert-billing-export.md live_verification=true` once exportcheck ≥1 row; -1: `cost-guard.sh -… |
| P34.6 | D-P34.6-2 D-P34.6-3 D-P34.6-4 D-P34.6-5 D-P34.6-6 | `logical-export.sh --apply export|lifecycle|relabel --go "…"`; `restore-drill.sh --apply fullrestore --go "…"`; -6: the drill re-run after P34.46's schema-chang… |
| P34.50 | D-P34.50-1 | none — operator action; **P35.67** (row 263) is verifying probe row |
| P34.17 | D-P34.17-1 | `implement-spec spec=docs/tickets/220_P34.17__web-honesty-wave-and-republish-1.md live_verification=true` (L2 `publish-web --apply` over `sig-2026-09-27-ce480ab… |
| P34.18 | D-P34.18-1 | `implement-spec spec=docs/tickets/221_P34.18__personal-handle-source-id-rename.md live_verification=true` (L2 insert-only rename + `sig-restricted` map + counts… |
| P34.21a | D-P34.21a-1 | `implement-spec spec=docs/tickets/223_P34.21a__attribution-gate-sink-rights-and-backfill.md live_verification=true` (L1 attribution-corrections dry-run→apply→re… |
| P34.21b | D-P34.21b-1 D-P34.21b-2 | `implement-spec spec=docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md live_verification=true` |
| P34.38 | BidNet terms-capture leg (works the E4-R6a answer; rights decision keeps its row-350 home) — now rides row 350's queue | `implement-spec spec=docs/tickets/246_P34.38__sources-pilot-prep-and-registry-rows.md live_verification=true` (BidNet terms; P36.2 line supersedes) |
| P34.39b | three monitoring legs (first-fire wave + `camreg_peel_on`) | `implement-spec spec=docs/tickets/248_P34.39b__first-fire-read-backs.md live_verification=true` |
| P36.2 | D-P36.2-1 | `implement-spec spec=docs/tickets/350_P36.2__rights-flip-decline-batch-and-terms-capture.md live_verification=true` |
| P34.40 | dark serving-topology roll — L1 `sig-web` digest roll, L2 `/v1/*` URL-map → `sig-api`; halves landed | `implement-spec spec=docs/tickets/249_P34.40__serving-topology-dark.md live_verification=true` (L1, then L2) |
| P34.42b | jobs IAM leg (F-272 jobs + `roles/editor` removal); `live`-1 stopped at 88/100; `live`-2 on `live:P35.1a1` poststate | `implement-spec spec=docs/tickets/252_P34.42b__least-privilege-job-identities-remove-editor.md live_verification=true` |
| P34.43 | L1 exec-host + `sig_audit` legs + L2 `sig_recovery` login (SIG-CONF-013); halves landed | `implement-spec spec=docs/tickets/253_P34.43__execution-host-and-least-privilege-db-logins.md live_verification=true` |
| P34.49 | L1 read-only scan + L2 protective-seal leg (F-406, I7 S1–S9, SIG-PUB-002; ADR-203 deny set) — halves landed | `implement-spec spec=docs/tickets/254_P34.49__part-viii-at-rest-audit.md live_verification=true` (L1 scan, then L2 seal) |
| P34.44b | L1 `sig-quality-probe` job+trigger + L2 baseline run + `apply-baselines` write | `implement-spec spec=docs/tickets/256_P34.44b__quality-baseline-run-and-nightly-probe.md live_verification=true` |
| P34.45 | append-only camera-site ER re-run (ruleset 3-interim) on P34.43 host (OM-20 listed; ADR-153/206) | `implement-spec spec=docs/tickets/257_P34.45__honest-evaluation-posture.md live_verification=true` |
| P34.46 | L2 deploy slot (schema roll + ADR-159 + `sig-api` roll + `/status/` + trigger pause/resume) + L3 48 h soak | `implement-spec spec=docs/tickets/258_P34.46__round10-schema-allows-and-api-roll.md live_verification=true` |
| P34.47 | 11A sweep + G4 packet leg: read-only crawl + counts + packet; `acceptance-sweep` → `sig.probe-run/1` | `implement-spec spec=docs/tickets/259_P34.47__sub-round-11a-acceptance.md live_verification=true` (sweep + packet) |
| P35.57 | API-roll leg: mount promoted release's registry on `sig-api`, roll, verify `/v1/health` | `implement-spec spec=docs/tickets/261_P35.57__api-release-parity.md live_verification=true` (mount+roll+verify) |
| P35.5 | R2-mirror leg: bucket + non-listable CDN, content-hash keys, immutable Cache-Control, $0 egress; limits/kill-switch landed | `implement-spec spec=docs/tickets/262_P35.5__zero-egress-distribution-host.md live_verification=true` (R2 push + origin-enable) |
| P35.67 | L1 post-cutover probe post-OP-09 + L2 cert read ≈ 2026-11-22; read-only; landed | `implement-spec spec=docs/tickets/263_P35.67__post-dns-cutover-probe.md live_verification=true` |
| P35.1a | write leg: reconcile Scheduler from cadence.toml (inert triggers + declared bundle) + `live`-diff; `live-1` stopped OM-18; P34.42b first | `implement-spec spec=docs/tickets/264_P35.1a__scheduler-of-record-live-diff-cron-lint.md live_verification=true` |
| P35.1a1 | declared-job seed leg (row 287a): 12 declared-absent jobs on default-compute + `sig-scheduler` run.invoker + paused triggers | `implement-spec spec=docs/tickets/287a_P35.1a1__seed-declared-jobs-paused.md live_verification=true` |
| P35.11 | Wave-A: L1 roll+seed+3-source ingest; L2 `+0` reruns; L3 resume+reconcile; S8 stays ingestion=false pending OP-26 | L2 |
| P35.14a | `hosted`: `sqitch deploy closed_vocabulary` (INSERT-only — 280 predicates + 5,600 directness + CHECK) + verify + read-back | `implement-spec spec=docs/tickets/272_P35.14a__vocabulary-conformance-closed-vocabulary.md live_verification=true` |
| P35.14b | `hosted` `sqitch deploy entity_typing_mobility_check` (ACCESS EXCLUSIVE) + INSERT (+0) + read-back | `implement-spec spec=docs/tickets/273_P35.14b__entity-typing-and-hosted-check-constraint.md live_verification=true` |
| P35.15a | `hosted`: INSERT-only `technology` vocab registration (`closed_vocabulary`) + read-back; backfill = P35.15b | `implement-spec spec=docs/tickets/274_P35.15a__technology-typing-slug-and-facets.md live_verification=true` |
| P35.15b | `hosted`: INSERT-only `technology` backfill on `sig-pg` (dry → apply → +0); no UPDATE/DELETE | `implement-spec spec=docs/tickets/275_P35.15b__technology-backfill.md live_verification=true` |
| P36.12 | Wave-B L0→L10 (family days → probe → materialize+delta+resume); `doj_ctas_awards` never | … |
| P35.1b | fleet-hygiene sweep (`fleet-sweep.sh --apply all`): prestate → cron reconciles + roll + name-checked deletes → `sig-alerts` | `implement-spec spec=docs/tickets/291_P35.1b__fleet-hygiene.md live_verification=true` |
| P35.1c | dispatcher-consolidation (`--apply all`): prestate → `sig-sched-due` + hourly trigger → 89 `[[retire_triggers]]` retire → proof | `implement-spec spec=docs/tickets/291a_P35.1c__dispatcher-consolidation.md live_verification=true` |
| P35.16 | `hosted` correction-write: `geometry-corrections --apply` — append-only INSERTs, 7 F-322 groups | `implement-spec spec=docs/tickets/296_P35.16__geometry-defects-at-ingest.md live_verification=true` |
| P35.17 | `hosted` boundary-source capture: OCFL tiger+natural_earth (append-only) → `live` pack + registry | `implement-spec spec=docs/tickets/297_P35.17__jurisdiction-registry-and-boundary-pack.md live_verification=true` |
| P35.24 | `hosted`: `sig-db subject-rekey --apply` (append-only; count re-derived) + `/status/` notice (A-20) | `implement-spec spec=docs/tickets/303_P35.24__truthful-subject-keys-and-re-keying.md live_verification=true` |
| P35.25 | L1 merge · L2 `lineage-rematerialize --apply` + `/status/` notice (A-20) · L3 every-claim `id_namespace` | nothing until re-run; rollback forward-only |
| P35.26 | L1 merge · L2 EFF+OSM role-aware re-ingest (OSM in-ODbL; pre-state counts) · L3 edge rematerialize — 1970 at zero | `implement-spec spec=docs/tickets/305_P35.26__roles-and-time-backend.md live_verification=true` |
| P35.41 | connector-image roll: rebuild+redeploy image carrying `records_digest`, upstream marks + capture-mark headers | `implement-spec spec=docs/tickets/320_P35.41__freshness-semantics-v2.md live_verification=true` |
| P35.53 | D-P35.53-1 | `SIG_RELEASE_AUTHOR=$(git config user.name) bash ops/gcp/release-infra.sh --apply all` or `implement-spec spec=docs/tickets/331_P35.53__release-pipeline-and-sta… |
| P35.59 | dark cutover (`web-cutover.sh --apply all`): prestate → staged/v floor import → `conf/0`+carry → `sig-web` roll → `route-compare` | `SIG_CUTOVER_GO=<authority-name> ops/gcp/web-cutover.sh --apply all` or `implement-spec spec=docs/tickets/336_P35.59__dark-cutover-to-release-layout.md live_ver… |
| P35.61 | `live` half of P32.22's recovery deferral (audit → pause → apply → +0 → freeze); packet `reports/p35.61-live-pass/` | `implement-spec spec=docs/tickets/338_P35.61__round10-live-pass-audit-apply-freeze.md live_verification=true` (`D-R10-LIVE-1` OPEN) |
| P35.62 | `release-candidate` over `frozen_unpublished` → +0 → export → stage+IAM → web build + DR-C4-01 crawl; packet `reports/p35.62-production-candidate/` | `implement-spec spec=docs/tickets/339_P35.62__round10-production-candidate.md live_verification=true` |
| P35.63 | release-exposure leg (home P32.25): staged cut → `class_s` → HG-11 readout → promote; packet `reports/p35.63-first-model-release/` | `implement-spec spec=docs/tickets/341_P35.63__first-model-release-to-production.md live_verification=true` (L2 resume) |
| P35.64 | 11B sweep + G5 packet: read-only crawl + counts + packet refresh; `acceptance-sweep-11b` → `sig.probe-run/1` + tools | `implement-spec spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md live_verification=true` |
| P37.2 | Wave-C L1→L5 (pre-grow → tier bump → national run → 24 h soak → revert); packet `reports/p37.2-wave-c/` | … |
| P35.2 | D-P35.2-1 | `implement-spec spec=docs/tickets/346_P35.2__alerting-as-code-and-escalation.md live_verification=true` |
| P35.21 | D-P35.21-1 | `implement-spec spec=docs/tickets/347_P35.21__partner-name-audit-run.md live_verification=true` |
| P35.23 | D-P35.23-1 | `implement-spec spec=docs/tickets/348_P35.23__real-data-regression-corpus.md live_verification=true` |
| P36.76 | D-P36.76-1 D-P36.76-2 | `implement-spec spec=docs/tickets/351_P36.76__axon-connect-connector.md live_verification=true` |
| P36.77 | D-P36.77-1 D-P36.77-2 | `implement-spec spec=docs/tickets/352_P36.77__documentcloud-muckrock-connector.md live_verification=true` |
| P36.78 | D-P36.78-1 D-P36.78-2 | `implement-spec spec=docs/tickets/353_P36.78__sourcewell-omnia-contract-pages.md live_verification=true` |
| P36.13 | D-P36.13-1 | `implement-spec spec=docs/tickets/354_P36.13__api-rate-limits.md live_verification=true` |
| P36.79 | D-P36.79-1 | `implement-spec spec=docs/tickets/371_P36.79__held-out-search-relevance-set.md live_verification=true` |
| P36.33 | D-P36.33-1 | `implement-spec spec=docs/tickets/374_P36.33__basemap-pipeline-and-host.md live_verification=true` |
| P36.38 | D-P36.38-1 | `implement-spec spec=docs/tickets/379_P36.38__search-api-serving-v2.md live_verification=true` |
| P36.75 | D-P36.75-1 | `implement-spec spec=docs/tickets/385_P36.75__flock-share-lists-configured-access.md live_verification=true` |
| P36.43 | D-P36.43-1 | `implement-spec spec=docs/tickets/386_P36.43__status-lane.md live_verification=true` |
| P36.44 | D-P36.44-1 | `implement-spec spec=docs/tickets/387_P36.44__release-cadence-automation.md live_verification=true` |
| P36.46 | D-P36.46-1 | `implement-spec spec=docs/tickets/389_P36.46__execution-keyed-ingestion-history.md live_verification=true` |
| P36.71 | D-P36.71-1 | `implement-spec spec=docs/tickets/414_P36.71__search-acceptance-and-activation.md live_verification=true` |
| P36.72b | D-P36.72b-1 | `implement-spec spec=docs/tickets/416_P36.72b__core-surfaces-walkthroughs-and-promotion.md live_verification=true` |
| P36.73 | 11C sweep + G6 packet refresh: read-only promoted crawl + packet re-draft; `acceptance-sweep-11c` → `sig.probe-run/1` | `implement-spec spec=docs/tickets/419_P36.73__sub-round-11c-acceptance.md live_verification=true` |
| P37.3 | D-P37.3-1 | `implement-spec spec=docs/tickets/421_P37.3__evidence-store-hardening.md live_verification=true` |
| P37.4a | D-P37.4a-1 | `implement-spec spec=docs/tickets/422_P37.4a__security-baseline-scan-sbom-signing.md live_verification=true` |
| P37.4b | D-P37.4b-1 | `implement-spec spec=docs/tickets/423_P37.4b__security-baseline-restricted-access-audit-logs.md live_verification=true` |
| P37.71 | D-P37.71-1 | `implement-spec spec=docs/tickets/429_P37.71__single-operator-deletion-and-purge-function.md live_verification=true` |
| P37.11 | D-P37.11-1 | `implement-spec spec=docs/tickets/432_P37.11__sam-gov-sweep-resume.md live_verification=true` |
| P37.12 | D-P37.12-1 | `implement-spec spec=docs/tickets/433_P37.12__keyed-us-511-wiring.md live_verification=true` |
| P37.70 | D-P37.70-1 | `implement-spec spec=docs/tickets/434_P37.70__keyed-au-traffic-camera-apis.md live_verification=true` |
| P37.13 | D-P37.13-1 | the next `sig.discovery-sweep/1` run or acq ticket — `discovery-sweep/2026-11-07/candidates.csv` |
| P37.14 | D-P37.14-1 | a data-review ticket or exports consumer of `publishable` — `ADR-240` revisit trigger (b) |
| P37.15 | queued leg | `implement-spec spec=docs/tickets/437_P37.15__scheduled-parser-canary.md live_verification=true` |
| P37.20 | D-P37.20-1 | implement-spec spec=docs/tickets/444_P37.20__release-pinned-bbox-api.md live_verification=true |
| P37.36 | raw-ok archive write (raw/index.json; P8 screen; new-capture reserialisation) + push + rehearsal | `implement-spec spec=docs/tickets/460_P37.36__raw-archive.md live_verification=true` (archive write + push + rehearsal) |
| P37.42 | D-P37.42-1 | implement-spec spec=docs/tickets/466_P37.42__api-parity.md live_verification=true |

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

