# SIG current build state — deterministic projection (advisory)

> **Authority:** `docs/build/LEDGER.md` CURRENT STATE + the DEFERRALS.md
> compatibility cells remain the control authority. This view is derived from
> the hashed `input-manifest/1` (`manifest.json`); it never writes control
> state. Shadow mode — the single-writer cutover deferral is `D-R10-MEMORY-2`
> input_commit: `a3e0e0b08d4b78bf507ddfa3a5d32412af44bce8` · inputs hashed: 1196 · wall-clock receipt: `receipt.json`

## Control (advisory read of LEDGER.md)

- projectStatus `IN_PROGRESS` · round `11` · nextTicket `GATE-G6` · lastCompleted `P36.73`
- chainTip `r11/P36.73-sub-round-11c-acceptance` · returnPass `P21.5,P31.4,P32.18,P32.19,P32.20,P32.21,P32.22,P32.23a,P32.25,P34.3,P34.4,P34.5,P34.6,P34.17,P34.18,P34.21a,P34.21b,P34.38,P34.39b,P34.40,P34.42b,P34.43,P34.44b…` · updatedAt `2026-11-05T14:42Z`

## Obligations

- 221 obligations · **138 owed** (135 OPEN, 3 PARTIAL) · 83 terminal
- 730 events (54 transitions beyond anchors) · 15 status conflicts reconciled by recorded events · 8 documented in `reconciliations.json`

- `obligations` → see [obligations.md](obligations.md) (complete — 138 rows)

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
| P34.3 | D-P34.3-1 | the OM-19 `r11/P34.3-live-<n>` dispatch or `implement-spec spec=docs/tickets/204_P34.3__ops-data-protection.md live_verification=true` (#197) |
| P34.4 | D-P34.4-1 · D-P34.4-2 | the OM-19 `r11/P34.4-live-<n>` dispatch or `implement-spec spec=docs/tickets/205_P34.4__alerts-that-reach-a-human.md live_verification=true` (#198) |
| P34.5 | D-P34.5-1 · D-P34.5-2 · D-P34.5-3 | -3: `implement-spec spec=docs/tickets/206_P34.5__cost-guard-budget-alert-billing-export.md live_verification=true` once `exportcheck` reads ≥1 row; -1: `cost-gu… |
| P34.6 | D-P34.6-2 · D-P34.6-3 · D-P34.6-4 · D-P34.6-5 · D-P34.6-6 | `logical-export.sh --apply export|lifecycle|relabel --go "…"`; `restore-drill.sh --apply fullrestore --go "…"`; -6: the drill re-run after P34.46's schema-chang… |
| P34.50 | D-P34.50-1 | none — operator action; **P35.67** (row 263) is the verifying probe row (#201) |
| P34.17 | D-P34.17-1 | `implement-spec spec=docs/tickets/220_P34.17__web-honesty-wave-and-republish-1.md live_verification=true` (L2 `publish-web --apply` over `sig-2026-09-27-ce480ab… |
| P34.18 | D-P34.18-1 | `implement-spec spec=docs/tickets/221_P34.18__personal-handle-source-id-rename.md live_verification=true` (L2 insert-only rename + `sig-restricted` map + counts… |
| P34.21a | D-P34.21a-1 | `implement-spec spec=docs/tickets/223_P34.21a__attribution-gate-sink-rights-and-backfill.md live_verification=true` (L1 attribution-corrections dry-run→apply→re… |
| P34.21b | D-P34.21b-1 · D-P34.21b-2 | `implement-spec spec=docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md live_verification=true` (L1 public-gate prestate→apply→verify; L2 export… |
| P34.38 | queued BidNet terms-capture leg (works the E4-R6a answer; rights decision keeps its row-350 home) — now rides row 350's queue | `implement-spec spec=docs/tickets/246_P34.38__sources-pilot-prep-and-registry-rows.md live_verification=true` (BidNet terms capture; superseded by the P36.2 re-… |
| P34.39b | the three queued monitoring legs (first-fire wave + `camreg_peel_on`) | `implement-spec spec=docs/tickets/248_P34.39b__first-fire-read-backs.md live_verification=true` (#246) |
| P36.2 | queued D-P36.2-1 — the 12 P36.2 terms captures (IU1–IU5, Edmonton OGL, BidNet, 5 folded-set) | `implement-spec spec=docs/tickets/350_P36.2__rights-flip-decline-batch-and-terms-capture.md live_verification=true` |
| P34.40 | two queued legs of the dark serving-topology roll (L1 `sig-web` pinned-digest roll, L2 `/v1/*` URL-map → `sig-api`); halves landed | `implement-spec spec=docs/tickets/249_P34.40__serving-topology-dark.md live_verification=true` (L1, then L2) (#250) |
| P34.42b | queued jobs IAM leg (G1-01/F-272 jobs + `roles/editor` removal); live-1 stopped at the 100/88 read; live-2 queued on P35.1a1's poststate | `implement-spec spec=docs/tickets/252_P34.42b__least-privilege-job-identities-remove-editor.md live_verification=true` (#253; `live-1` stopped OM-18) · next `r1… |
| P34.43 | queued L1 exec-host + `sig_audit` legs and L2 `sig_recovery` login (SIG-CONF-013); halves landed | `implement-spec spec=docs/tickets/253_P34.43__execution-host-and-least-privilege-db-logins.md live_verification=true` (#255) |
| P34.49 | queued L1 read-only scan + L2 protective-seal leg (F-406, I7 S1–S9, SIG-PUB-002; ADR-203 deny set) — halves landed | `implement-spec spec=docs/tickets/254_P34.49__part-viii-at-rest-audit.md live_verification=true` (L1 scan, then L2 seal) |
| P34.44b | queued L1 `sig-quality-probe` job+trigger + L2 baseline run + `apply-baselines` write | `implement-spec spec=docs/tickets/256_P34.44b__quality-baseline-run-and-nightly-probe.md live_verification=true` (job+trigger, then baseline) |
| P34.45 | queued append-only camera-site ER re-run (ruleset 3-interim) on P34.43 host (OM-20 listed; ADR-153/206) | `implement-spec spec=docs/tickets/257_P34.45__honest-evaluation-posture.md live_verification=true` (ER re-run leg) |
| P34.46 | queued L2 deploy slot (schema roll + ADR-159 dispositions + `sig-api` roll + `/status/` notice + trigger pause/resume) + L3 48 h soak | `implement-spec spec=docs/tickets/258_P34.46__round10-schema-allows-and-api-roll.md live_verification=true` (#261) |
| P34.47 | queued 11A acceptance sweep + GATE-G4 packet leg (§13.1): read-only crawl of site/API/tiles/`sig-public` + counts + packet refresh; `acceptance-sweep` → `sig.pr… | `implement-spec spec=docs/tickets/259_P34.47__sub-round-11a-acceptance.md live_verification=true` (sweep + packet) |
| P35.57 | queued API-roll leg: mount promoted release's registry on `sig-api` (`SIG_RELEASE_REGISTRY`), roll, verify `/v1/health` names the release | `implement-spec spec=docs/tickets/261_P35.57__api-release-parity.md live_verification=true` (mount+roll+verify) (#263) |
| P35.5 | queued R2-mirror leg: bucket + non-listable CDN, content-hash keys, immutable Cache-Control, $0 egress; limits/kill-switch landed | `implement-spec spec=docs/tickets/262_P35.5__zero-egress-distribution-host.md live_verification=true` (R2 push + origin-enable) |
| P35.67 | queued L1 post-cutover checklist (`sig-ops post-cutover-probe --leg l1`) post-OP-09 + L2 cert-renewal read ≈ 2026-11-22; read-only OM-14; probe verb + checklist… | `implement-spec spec=docs/tickets/263_P35.67__post-dns-cutover-probe.md live_verification=true` (#265) |
| P35.1a | queued write leg: reconcile Cloud Scheduler from ops/cadence.toml (inert PAUSED triggers + declared-bundle publish) + live-diff; `live-1` stopped OM-18; P34.42b… | `implement-spec spec=docs/tickets/264_P35.1a__scheduler-of-record-live-diff-cron-lint.md live_verification=true` (#266) |
| P35.1a1 | queued declared-job seed leg (row 287a): 12 declared-absent jobs on default-compute + `sig-scheduler` run.invoker + paused triggers | `implement-spec spec=docs/tickets/287a_P35.1a1__seed-declared-jobs-paused.md live_verification=true` (#296 — leg queued, production untouched) |
| P35.11 | queued Wave-A: L1 digest roll + seed load + legistar → usa_spending → procportal_nyc_ny; L2 `claims_added == 0` reruns; L3 resume post-green; S8 stays `ingestio… | L2 |
| P35.14a | queued hosted write: `sqitch deploy closed_vocabulary` (INSERT-only — 280 predicates + 5,600 directness + CHECK) + verify + read-back | `implement-spec spec=docs/tickets/272_P35.14a__vocabulary-conformance-closed-vocabulary.md live_verification=true` (#274) |
| P35.14b | queued `hosted` leg: `sqitch deploy entity_typing_mobility_check` (ACCESS EXCLUSIVE, `lock_timeout`) + typed-identity INSERT (+0); verify + read-back | `implement-spec spec=docs/tickets/273_P35.14b__entity-typing-and-hosted-check-constraint.md live_verification=true` (#275) |
| P35.15a | queued `hosted` write: INSERT-only `technology` vocab registration (`vocab_predicate` via `closed_vocabulary`) + missing rows + read-back; backfill is P35.15b | `implement-spec spec=docs/tickets/274_P35.15a__technology-typing-slug-and-facets.md live_verification=true` (#276) |
| P35.15b | queued `hosted` write: INSERT-only `technology` backfill on `sig-pg` (dry → apply → `+0`); claims link EXISTING captures; no UPDATE/DELETE | `implement-spec spec=docs/tickets/275_P35.15b__technology-backfill.md live_verification=true` (#277) |
| P36.12 | queued Wave-B L0→L10 (open → family days + `+0` → 917-portal probe → materialize+delta+resume); `doj_ctas_awards` never; missed leg reported | … |
| P35.1b | queued fleet-hygiene sweep (`ops/gcp/fleet-sweep.sh --apply all`): prestate + AR-2 → 4 cron reconciles → exit-64 guard roll → 6 `[[retired_jobs]]` deletes → AR … | `implement-spec spec=docs/tickets/291_P35.1b__fleet-hygiene.md live_verification=true` (#302) |
| P35.1c | queued dispatcher-consolidation (`--apply all`): prestate → `sig-sched-due` + hourly trigger + bindings → verify → 89 `[[retire_triggers]]` deletes → proof | `implement-spec spec=docs/tickets/291a_P35.1c__dispatcher-consolidation.md live_verification=true` (#303) |
| P35.16 | queued hosted correction-write: `sig-connectors geometry-corrections --dsn <hosted> --apply` — append-only INSERTs for the 7 F-322 groups + read-back | `implement-spec spec=docs/tickets/296_P35.16__geometry-defects-at-ingest.md live_verification=true` (#309) |
| P35.17 | queued hosted boundary-source capture: OCFL `census_gazetteer_tiger` + `natural_earth_10m` (append-only digests) → live pack + registry + `boundaries_root` | `implement-spec spec=docs/tickets/297_P35.17__jurisdiction-registry-and-boundary-pack.md live_verification=true` (#310) |
| P35.24 | queued hosted legs: `sig-db subject-rekey --dsn <hosted> --apply` (append-only; count re-derived) + `/status/` basis notice (S6 A-20) + collision artifact | `implement-spec spec=docs/tickets/303_P35.24__truthful-subject-keys-and-re-keying.md live_verification=true` (#318) |
| P35.25 | L1 merge · L2 `lineage-rematerialize --apply` + `/status/` notice (A-20) · L3 every-claim `id_namespace` | nothing until re-run; rollback forward-only |
| P35.26 | L1 merge · L2 EFF+OSM role-aware re-ingest (OSM in-ODbL; pre-state counts) · L3 edge rematerialize — 1970 at zero | `implement-spec spec=docs/tickets/305_P35.26__roles-and-time-backend.md live_verification=true` (#320) |
| P35.41 | queued connector-image roll: rebuild+redeploy the image carrying `records_digest`, upstream marks + capture-mark headers | `implement-spec spec=docs/tickets/320_P35.41__freshness-semantics-v2.md live_verification=true` (#338) |
| P35.53 | D-P35.53-1 | `SIG_RELEASE_AUTHOR="$(git config user.name)" bash ops/gcp/release-infra.sh --apply all` or `implement-spec spec=docs/tickets/331_P35.53__release-pipeline-and-s… |
| P35.59 | queued dark cutover (`web-cutover.sh --apply all`): AR-2 prestate → `staged/v/legacy-<YYYYMMDD>/` floor import → `conf/0`+carry → `sig-web` roll → `route-compar… | `SIG_CUTOVER_GO=<authority-name> ops/gcp/web-cutover.sh --apply all` or `implement-spec spec=docs/tickets/336_P35.59__dark-cutover-to-release-layout.md live_ver… |
| P35.61 | queued live half of P32.22's recovery deferral (audit+plan → pause → `recovery-apply` → +0 → freeze unpublished); packet `reports/p35.61-live-pass/` | `implement-spec spec=docs/tickets/338_P35.61__round10-live-pass-audit-apply-freeze.md live_verification=true` (`D-R10-LIVE-1` OPEN) |
| P35.62 | queued `release-candidate` over `frozen_unpublished` → +0 rematerialize → export → stage + IAM origins → web build + DR-C4-01 crawl; packet `reports/p35.62-prod… | queued `implement-spec spec=docs/tickets/339_P35.62__round10-production-candidate.md live_verification=true` |
| P35.63 | queued release-exposure leg (home P32.25): staged cut → `class_s` → HG-11 readout → promote — signed readout + go only, packet `reports/p35.63-first-model-relea… | queued `implement-spec spec=docs/tickets/341_P35.63__first-model-release-to-production.md live_verification=true` (resumes at L2's promote) (#362) |
| P35.64 | queued 11B acceptance sweep + GATE-G5 packet: read-only crawl of promoted release/API/`sig-public`/`sig-registry` + counts + packet refresh; `acceptance-sweep-1… | `implement-spec spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md live_verification=true` (#363) |
| P37.2 | Wave-C L1→L5 (pre-grow → tier bump → national run → 24 h soak → revert); packet `reports/p37.2-wave-c/` | … |
| P35.2 | D-P35.2-1 | `implement-spec spec=docs/tickets/346_P35.2__alerting-as-code-and-escalation.md live_verification=true` |
| P35.21 | D-P35.21-1 | `implement-spec spec=docs/tickets/347_P35.21__partner-name-audit-run.md live_verification=true` |
| P35.23 | D-P35.23-1 | `implement-spec spec=docs/tickets/348_P35.23__real-data-regression-corpus.md live_verification=true` |
| P36.76 | queued D-P36.76-1 — 12 leg-A bounded GETs (6 registration + 6 `/:8443` screens); D-P36.76-2 — leg B, operator's first-wire | `implement-spec spec=docs/tickets/351_P36.76__axon-connect-connector.md live_verification=true` |
| P36.77 | queued D-P36.77-1 — 11 leg-A GETs (4 api_document + 3 api_project + 2 DocumentCloud + ToS + /foi/); D-P36.77-2 — leg B, operator's first-wire act | `implement-spec spec=docs/tickets/352_P36.77__documentcloud-muckrock-connector.md live_verification=true` |
| P36.78 | queued D-P36.78-1 — 5 leg-A GETs (Sourcewell + OMNIA contract/terms pages); D-P36.78-2 — leg B, operator's first-wire act | `implement-spec spec=docs/tickets/353_P36.78__sourcewell-omnia-contract-pages.md live_verification=true` |
| P36.13 | queued D-P36.13-1 — the hosted-enforcement flip on `sig-api` (env `SIG_API_RATE_LIMIT=enforce` + hops 2; prestate describe = restore point) | `implement-spec spec=docs/tickets/354_P36.13__api-rate-limits.md live_verification=true` |
| P36.79 | queued D-P36.79-1 — restricted-bucket object write of the sealed held-out relevance set (read-back digest verify; restore = bucket versioning + committed sha256… | `implement-spec spec=docs/tickets/371_P36.79__held-out-search-relevance-set.md live_verification=true` |
| P36.33 | queued D-P36.33-1 — R2 basemap host create (bucket sig-basemap + CORS/Range/immutable + domain tiles.surveillancegraph.org + first upload); restorable from base… | `implement-spec spec=docs/tickets/374_P36.33__basemap-pipeline-and-host.md live_verification=true` |
| P36.38 | queued D-P36.38-1 — the v2-search API roll (`--memory 1Gi` + `SIG_API_SEARCH_V2=on`) | `implement-spec spec=docs/tickets/379_P36.38__search-api-serving-v2.md live_verification=true` |
| P36.75 | queued D-P36.75-1 — `hosted` append-only `configured_access` claim write (org-level `configured_sharing_partner`); restore = claim-set digest list | `implement-spec spec=docs/tickets/385_P36.75__flock-share-lists-configured-access.md live_verification=true` |
| P36.43 | queued D-P36.43-1 — the `sig-status-publish` job create + `sig-sched-status-publish` 6h trigger + invoker binding; restore = delete trigger then job | `implement-spec spec=docs/tickets/386_P36.43__status-lane.md live_verification=true` |
| P36.44 | queued D-P36.44-1 — the `sig-sched-release-cut` + `sig-sched-materialize` Cloud Scheduler trigger creates; restore = delete both triggers | `implement-spec spec=docs/tickets/387_P36.44__release-cadence-automation.md live_verification=true` |
| P36.46 | queued D-P36.46-1 — `hosted` report backfill (INSERT-only, +0; restore = appended-set digests) | `implement-spec spec=docs/tickets/389_P36.46__execution-keyed-ingestion-history.md live_verification=true` |
| P36.71 | queued D-P36.71-1 — post-promotion search-acceptance verify legs (real-release --enforce run, staging p95 at 1 vCPU, budgets+Lighthouse+axe, cost readout, A1/J2… | `implement-spec spec=docs/tickets/414_P36.71__search-acceptance-and-activation.md live_verification=true` |
| P36.72b | queued D-P36.72b-1 — core-surfaces Class S promote (`release promote --class class_s --approval <signed-readout>` + P-mode verify); restore = `release rollback`… | `implement-spec spec=docs/tickets/416_P36.72b__core-surfaces-walkthroughs-and-promotion.md live_verification=true` |
| P36.73 | queued 11C acceptance sweep + GATE-G6 packet refresh: read-only crawl of the promoted core-surfaces release/routes/budgets/labels/changelog/mirrors + the packet… | `implement-spec spec=docs/tickets/419_P36.73__sub-round-11c-acceptance.md live_verification=true` (#444) |

## Known inconsistencies (preserved, never synthesized)

- none — every P32.1 baseline conflict is either reconciled by a recorded event interpretation (old values preserved on the anchor) or documented in `reconciliations.json`; anything new would appear here and fail `verify`

## Evidence domains — recorded evidence only

- `domains` → see [domains.md](domains.md) (complete — 5 rows)

## Source funnel (recorded baseline, domain-labelled)

- `funnel` → see [funnel.md](funnel.md) (complete — 8 rows)

## Releases (recorded)

- public release: `national surface live: export `sig-2026-09-27-ce480ab1` published to `…-sig-public`, `sig-web` rolled `sha256:d8244804…`, 12 z0–z14 tiles, 1`
- database run ids: not recorded in projection inputs — hosted-domain facts are recorded evidence only (never measured by this offline tool)

## Coverage — scoped assessments + historical CSV

- `coverage` spilled across 5 pages (complete): [coverage-1.md](coverage-1.md) [coverage-2.md](coverage-2.md) [coverage-3.md](coverage-3.md) [coverage-4.md](coverage-4.md) [coverage-5.md](coverage-5.md)

## Governing ADRs

- `adrs` → see [adrs.md](adrs.md) (complete — 5 rows)

## Reading this view

- owed obligations are never dropped: if the table exceeds the view budget it
  moves to `obligations-N.md` link-out pages (still complete, same columns).
- `verify` recomputes every input digest; a changed input is reported stale.
- deferred work context: `docs/tickets/DEFERRALS.md` remains the register; this
  projection reproduces its leading cells via the event chains it validates.

