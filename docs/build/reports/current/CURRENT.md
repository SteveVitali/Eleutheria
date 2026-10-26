# SIG current build state — deterministic projection (advisory)

> **Authority:** `docs/build/LEDGER.md` CURRENT STATE + the DEFERRALS.md
> compatibility cells remain the control authority. This view is derived from
> the hashed `input-manifest/1` (`manifest.json`); it never writes control
> state. Shadow mode — the single-writer cutover deferral is `D-R10-MEMORY-2`
> input_commit: `c37a4009c1eb49d875f462deca82958e29783d81` · inputs hashed: 1114 · wall-clock receipt: `receipt.json`

## Control (advisory read of LEDGER.md)

- projectStatus `IN_PROGRESS` · round `11` · nextTicket `P36.1b` · lastCompleted `P35.23`
- chainTip `r11/P35.23-real-data-regression-corpus` · returnPass `P21.5,P31.4,P32.18,P32.19,P32.20,P32.21,P32.22,P32.23a,P32.25,P34.3,P34.4,P34.5,P34.6,P34.17,P34.18,P34.21a,P34.21b,P34.38,P34.39b,P34.40,P34.42b,P34.43,P34.44b…` · updatedAt `2026-10-26T19:40Z`

## Obligations

- 195 obligations · **114 owed** (111 OPEN, 3 PARTIAL) · 81 terminal
- 694 events (45 transitions beyond anchors) · 15 status conflicts reconciled by recorded events · 8 documented in `reconciliations.json`

- `obligations` → see [obligations.md](obligations.md) (complete — 114 rows)

## RETURN PASS — owed live legs (generated region)

- the generated LEDGER region `### RETURN PASS — current` is the
  authority (`return_pass.py`); owed obligations in a row land there.
| ticket | obligations | re-run line |
|---|---|---|
| P21.5 | D-P21.5-1 (PARTIAL) | chain 482 **P37.55** (11D, after P34.21b) · landed 59 (PR #61 — prepare-only re-run row 76, PR #76) |
| P31.4 | D-P31.4-1 | chain 247 **P34.39a** (11A — leg ran 2026-10-14 `fail` → `deferral-row`; a `P34.39a-live-2` re-read rides the call); verify = the D-P31.4-1 command; P34.39b car… |
| P32.18 | D-P32.18-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.18-okc-dossier/LIVE_RETURN_PASS.json` · landed 179 (PR… |
| P32.19 | D-P32.19-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.19-tulsa-dossier/LIVE_RETURN_PASS.json` · landed 180 (… |
| P32.20 | D-P32.20-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.20-san-diego-dossier/LIVE_RETURN_PASS.json` · landed 1… |
| P32.21 | D-P32.21-1 | chain rows 438 **P37.16a** + 439 **P37.16b** (11D family-split, PLAN-11D); packet `docs/build/reports/p32.21-acquisition-pilot/ACQ_PILOT_RETURN_PASS.json` · lan… |
| P32.22 | queued D-R10-LIVE-1 | chain 338 **P35.61** (11B — ≥48 h after P34.46, post-11B writes); packet `docs/build/reports/p32.22-bounded-recovery/LIVE_RETURN_PASS.json` · landed 183 (PR #17… |
| P32.23a | queued D-P32.23a-1 | chain 339 **P35.62** (after P35.61); packet `docs/build/reports/p32.23a-release-candidate/LIVE_RETURN_PASS.json` · landed 188 (PR #180) |
| P32.25 | queued D-R10-PUBLISH-1 | chain 341 **P35.63** (after P35.62); rollback cases `reports/p32.25-accepted-release-verification/LIVE_RETURN_PASS.json` · landed 191 (PR #182) |
| — | HG-05 (old P23.1 row; no deferral) | none — operator action, not in `returnPass` |
| P34.3 | D-P34.3-1 | the OM-19 `r11/P34.3-live-<n>` dispatch or `implement-spec spec=docs/tickets/204_P34.3__ops-data-protection.md live_verification=true` · landed 204 (PR #197) |
| P34.4 | D-P34.4-1 · D-P34.4-2 | the OM-19 `r11/P34.4-live-<n>` dispatch or `implement-spec spec=docs/tickets/205_P34.4__alerts-that-reach-a-human.md live_verification=true` · landed 205 (PR #1… |
| P34.5 | D-P34.5-1 · D-P34.5-2 · D-P34.5-3 | -3: `implement-spec spec=docs/tickets/206_P34.5__cost-guard-budget-alert-billing-export.md live_verification=true` once `exportcheck` reads ≥1 row; -1: `cost-gu… |
| P34.6 | D-P34.6-2 · D-P34.6-3 · D-P34.6-4 · D-P34.6-5 · D-P34.6-6 | `logical-export.sh --apply export|lifecycle|relabel --go "…"`; `restore-drill.sh --apply fullrestore --go "…"`; -6: the drill re-run after P34.46's schema-chang… |
| P34.50 | D-P34.50-1 | none — operator action; **P35.67** (row 263) is the verifying probe row · landed 208 (PR #201) |
| P34.17 | D-P34.17-1 | `implement-spec spec=docs/tickets/220_P34.17__web-honesty-wave-and-republish-1.md live_verification=true` (L2 republish — `publish-web --apply` over `sig-2026-0… |
| P34.18 | D-P34.18-1 | `implement-spec spec=docs/tickets/221_P34.18__personal-handle-source-id-rename.md live_verification=true` (L2 — insert-only rename + `sig-restricted` map + coun… |
| P34.21a | D-P34.21a-1 | `implement-spec spec=docs/tickets/223_P34.21a__attribution-gate-sink-rights-and-backfill.md live_verification=true` (L1 — `attribution-corrections` dry-run → `-… |
| P34.21b | D-P34.21b-1 · D-P34.21b-2 | `implement-spec spec=docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md live_verification=true` (L1 `public-gate.sh` prestate → `--apply` → `--v… |
| P34.38 | queued BidNet terms-capture leg (works the E4-R6a answer; the rights decision keeps its row-350 home) | `implement-spec spec=docs/tickets/246_P34.38__sources-pilot-prep-and-registry-rows.md live_verification=true` (BidNet terms capture) · landed 246 (PR #243) |
| P34.39b | the three queued monitoring legs (first-fire wave + `camreg_peel_on`); obligations keep their homes — this row carries the clock-guarded legs | `implement-spec spec=docs/tickets/248_P34.39b__first-fire-read-backs.md live_verification=true` · landed 248 (PR #246) |
| P34.40 | two queued production legs of the dark serving-topology roll (L1 `sig-web` pinned-digest roll, L2 `/v1/*` URL-map onto `sig-api`); halves landed (declaration, r… | `implement-spec spec=docs/tickets/249_P34.40__serving-topology-dark.md live_verification=true` (L1, then L2) · landed 249 (PR #250) |
| P34.42b | queued jobs IAM leg (G1-01/F-272 jobs half + `roles/editor` removal; halves landed) — live-1 stopped at the 100/88 read; live-2 stays queued on P35.1a1's 100-jo… | `implement-spec spec=docs/tickets/252_P34.42b__least-privilege-job-identities-remove-editor.md live_verification=true` · landed 252 (PR #253; `live-1` stopped O… |
| P34.43 | queued L1 exec-host + `sig_audit` legs and L2 `sig_recovery` login (SIG-CONF-013); halves landed; the grant review keeps its DEFERRALS home | `implement-spec spec=docs/tickets/253_P34.43__execution-host-and-least-privilege-db-logins.md live_verification=true` · landed 253 (#255) |
| P34.49 | queued L1 read-only scan + L2 protective-seal leg (F-406, I7 S1–S9, SIG-PUB-002; ADR-203 deny set) — halves landed (screen, `at-rest`, `seal_register`, audit sc… | `implement-spec spec=docs/tickets/254_P34.49__part-viii-at-rest-audit.md live_verification=true` (L1 scan, then L2 seal) · landed 254 (legs queued exit 42) |
| P34.44b | queued L1 `sig-quality-probe` job+trigger + L2 baseline run + `apply-baselines` write; halves landed (`sig.quality-probe/1` → quality-probe.sh) | `implement-spec spec=docs/tickets/256_P34.44b__quality-baseline-run-and-nightly-probe.md live_verification=true` (job+trigger, then baseline) · landed 256 |
| P34.45 | queued append-only camera-site ER re-run (ruleset v3-interim) on the P34.43 exec host (OM-20 listed; ADR-153/206) — `er-rerun.sh` landed | `implement-spec spec=docs/tickets/257_P34.45__honest-evaluation-posture.md live_verification=true` (ER re-run leg) · landed 257 |
| P34.46 | queued L2 deploy slot (schema roll + ADR-159 dispositions + `sig-api` roll + `/status/` notice + trigger pause/resume) + L3 48 h soak; landed: r11-verify rework… | `implement-spec spec=docs/tickets/258_P34.46__round10-schema-allows-and-api-roll.md live_verification=true` · landed 258 (PR #261) |
| P34.47 | queued 11A acceptance sweep + GATE-G4 packet leg (§13.1): read-only crawl of site/API/tiles/`sig-public` + repo tip (counts only) + packet refresh at the leg; l… | `implement-spec spec=docs/tickets/259_P34.47__sub-round-11a-acceptance.md live_verification=true` (sweep + packet) · landed 259 |
| P35.57 | queued API-roll leg: mount the promoted release's registry on `sig-api` (`SIG_RELEASE_REGISTRY`), roll the image, verify `/v1/health` names the release; reads +… | `implement-spec spec=docs/tickets/261_P35.57__api-release-parity.md live_verification=true` (mount+roll+verify) · landed 261 (PR #263) |
| P35.5 | queued R2-mirror leg: R2 bucket + CDN domain (files.surveillancegraph.org non-listable), content-hash keys, immutable Cache-Control, $0 egress; landed: PushLimi… | `implement-spec spec=docs/tickets/262_P35.5__zero-egress-distribution-host.md live_verification=true` (R2 push + origin-enable) · landed 262 |
| P35.67 | queued L1 post-cutover checklist (`sig-ops post-cutover-probe --leg l1`) post-OP-09 + the L2 cert-renewal read ≈ 2026-11-22; read-only OM-14; probe verb + check… | `implement-spec spec=docs/tickets/263_P35.67__post-dns-cutover-probe.md live_verification=true` · landed 263 (PR #265) |
| P35.1a | queued production-write leg: reconcile Cloud Scheduler from ops/cadence.toml (inert PAUSED triggers + declared-bundle publish) + the in-band live-diff; `live-1`… | `implement-spec spec=docs/tickets/264_P35.1a__scheduler-of-record-live-diff-cron-lint.md live_verification=true` · landed 264 (PR #266; `live-1` stopped OM-18) … |
| P35.1a1 | queued declared-job seed leg (row 287a): create the 12 declared-absent jobs on the labelled default-compute identity + `sig-scheduler` run.invoker + paused trig… | `implement-spec spec=docs/tickets/287a_P35.1a1__seed-declared-jobs-paused.md live_verification=true` · landed 287a (PR #296 — leg queued 2026-10-14, production … |
| P35.11 | queued Wave-A sequence: L1 digest roll + `state_alpr_statute_inventory_2026` load + serial legistar → usa_spending → procportal_nyc_ny; L2 `claims_added == 0` r… | L2 |
| P35.14a | queued hosted write: `sqitch deploy closed_vocabulary` (INSERT-only — 280 predicates + 5,600 directness rows + genres/strategies + widened CHECK) + verify + rea… | `implement-spec spec=docs/tickets/272_P35.14a__vocabulary-conformance-closed-vocabulary.md live_verification=true` · landed 272 (PR #274) |
| P35.14b | queued hosted leg: `sqitch deploy entity_typing_mobility_check` (ACCESS EXCLUSIVE, `lock_timeout`) then append-only typed-identity write (`--apply`, INSERT-only… | `implement-spec spec=docs/tickets/273_P35.14b__entity-typing-and-hosted-check-constraint.md live_verification=true` · landed 273 (PR #275) |
| P35.15a | queued hosted write: INSERT-only `technology` vocabulary registration (`vocab_predicate`, via P35.14a's `closed_vocabulary`) + missing-row INSERTs + read-back; … | `implement-spec spec=docs/tickets/274_P35.15a__technology-typing-slug-and-facets.md live_verification=true` · landed 274 (PR #276) |
| P35.15b | queued hosted write: ~200k-subject INSERT-only `technology` backfill on `sig-pg` (dry-run → `--apply` → read-back `+0`); claims link EXISTING captures; no UPDAT… | `implement-spec spec=docs/tickets/275_P35.15b__technology-backfill.md live_verification=true` · landed 275 (PR #277) |
| P36.12 | Wave-B sequence L0→L10 (open → family days + `+0` → 917-portal probe → materialize+delta+resume); `doj_ctas_awards` never; missed leg reported | … |
| P35.1b | queued fleet-hygiene sweep (`ops/gcp/fleet-sweep.sh --apply all`): prestate + verified AR-2 → 4 cron reconciles → exit-64 guard roll → 6 `[[retired_jobs]]` dele… | `implement-spec spec=docs/tickets/291_P35.1b__fleet-hygiene.md live_verification=true` · landed 291 (PR #302 — queued exit-42 2026-10-16; production never touch… |
| P35.1c | queued dispatcher-consolidation leg (`ops/gcp/dispatcher-consolidation.sh --apply all`): prestate → deploy `sig-sched-due` + ONE hourly trigger + bindings → ver… | `implement-spec spec=docs/tickets/291a_P35.1c__dispatcher-consolidation.md live_verification=true` · landed 291a (PR #303 — queued; never touched production) |
| P35.16 | queued hosted correction-write: `sig-connectors geometry-corrections --dsn <hosted> --apply` — append-only defect/correction INSERTs for the 7 F-322 groups + re… | `implement-spec spec=docs/tickets/296_P35.16__geometry-defects-at-ingest.md live_verification=true` · landed 296 (PR #309 — production not touched) |
| P35.17 | queued hosted boundary-source capture: OCFL `census_gazetteer_tiger` + `natural_earth_10m` (append-only digests) → live pack + registry + real `boundaries_root` | `implement-spec spec=docs/tickets/297_P35.17__jurisdiction-registry-and-boundary-pack.md live_verification=true` · landed 297 (PR #310 — capture never run) |
| P35.24 | queued hosted legs: `sig-db subject-rekey --dsn <hosted> --apply` (append-only; count re-derived) + `/status/` basis notice (S6 A-20) + collision artifact | `implement-spec spec=docs/tickets/303_P35.24__truthful-subject-keys-and-re-keying.md live_verification=true` · landed 303 (PR #318) |
| P35.25 | L1 merge · L2 `lineage-rematerialize --apply` + `/status/` notice (A-20) · L3 every-claim `id_namespace` | nothing until the re-run; rollback forward-only |
| P35.26 | L1 merge · L2 EFF+OSM role-aware re-ingest (OSM in-ODbL; pre-state counts) · L3 edge rematerialize — 1970 at zero | `implement-spec spec=docs/tickets/305_P35.26__roles-and-time-backend.md live_verification=true` · landed 305 (PR #320) |
| P35.41 | queued connector-image roll: rebuild + redeploy the image carrying `records_digest`, upstream-declared marks + capture-mark headers | `implement-spec spec=docs/tickets/320_P35.41__freshness-semantics-v2.md live_verification=true` · landed 320 (PR #338) |
| P35.53 | D-P35.53-1 | `SIG_RELEASE_AUTHOR="$(git config user.name)" bash ops/gcp/release-infra.sh --apply all` or `implement-spec spec=docs/tickets/331_P35.53__release-pipeline-and-s… |
| P35.59 | queued dark cutover (`web-cutover.sh --apply all`): AR-2 prestate+manifest → `staged/v/legacy-<YYYYMMDD>/` floor import → `conf/0`+carry+`serving.json` retire →… | `SIG_CUTOVER_GO=<authority-name> ops/gcp/web-cutover.sh --apply all` or `implement-spec spec=docs/tickets/336_P35.59__dark-cutover-to-release-layout.md live_ver… |
| P35.61 | queued live half of P32.22's recovery deferral + F-522 (audit+plan → operator pause → bounded `recovery-apply --authority <scope>` → `+0`/rematerialize → freeze… | `implement-spec spec=docs/tickets/338_P35.61__round10-live-pass-audit-apply-freeze.md live_verification=true` · landed 338 (PR #359 — `D-R10-LIVE-1` OPEN, never… |
| P35.62 | queued live half of P32.23a's candidate deferral: `release-candidate` over a hosted `frozen_unpublished` snapshot → `+0` rematerialize → export → `release stage… | `implement-spec spec=docs/tickets/339_P35.62__round10-production-candidate.md live_verification=true` · landed 339 (PR #360 — queued, never ran) |
| P35.63 | queued release-exposure half of the publish deferral (home: P32.25): L1 staged cut → V1–V15 → classify `class_s` → agent-drafted HG-11 readout (unsigned) · L2 p… | `implement-spec spec=docs/tickets/341_P35.63__first-model-release-to-production.md live_verification=true` (resumes at L2's promote once signed — re-staged cut … |
| P35.64 | queued 11B acceptance sweep + GATE-G5 packet leg: read-only crawl of the promoted release/API/`sig-public`/`sig-registry` + ledger surface (counts only) + the p… | `implement-spec spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md live_verification=true` · landed 342 (PR #363) |
| P37.2 | Wave-C sequence L1→L5 (pre-grow → tier bump after the go → national run → 24 h soak read → revert); missed leg reported; packet `reports/p37.2-wave-c/WAVE_C_PAC… | … |
| P35.2 | D-P35.2-1 | `implement-spec spec=docs/tickets/346_P35.2__alerting-as-code-and-escalation.md live_verification=true` · landed 346 |
| P35.21 | D-P35.21-1 | `implement-spec spec=docs/tickets/347_P35.21__partner-name-audit-run.md live_verification=true` · landed 347 |
| P35.23 | D-P35.23-1 | `implement-spec spec=docs/tickets/348_P35.23__real-data-regression-corpus.md live_verification=true` · landed 348 |

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

