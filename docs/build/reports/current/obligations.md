# link-out: obligations (page 1/1)

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
| D-P30.2b-1 | OPEN | engineering + reviewers | **Round 10** (human review campaign → P31.18); engineering half landed | an accepted proposal appears as an `auto_write`-equivalent human edge in the next run's clusters (N drops by one), a rejected one never clusters; `camera_site_r… |
| D-P30.2b-2 | OPEN | engineering | **Round 10** (with the P31.18 evaluation refresh) | a rules-v3 soft conflict for name-level device-kind/place disagreement; measured on a new frozen holdout; tier 3g precision re-measured ≥ 0.98 |
| D-P31.4-1 | OPEN | scheduled (cron) | automatic at the 2026-10-10T03:35Z cron; verify per the row's exact command (run rows + `ingest_run_completion`, ≈ 12–15 min expected) | the batch-05 run rows under `gs://…-sig-restricted/ops/runs/camreg_osm_surveillance/2026-10-10/` show `outcome` ok/partial, `fetches` 158 (or fewer only with `r… |
| D-R10-HUMAN-1 | OPEN | HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 | HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 | Signed HUMAN-H4 development/dossier and HUMAN-H5 confirmatory readouts; frozen-candidate-specific sample/label digests; blind/adjudication records; dossier rubr… |
| D-R10-SOURCES-1 | OPEN | P32.18–21 | P32.18 | Per-target green registry/rights basis; actual captured digests; measured acquisition funnel under the prescribed family/document/protocol caps |
| D-R10-LIVE-1 | OPEN | P32.22/P32.23a | P32.22 → P32.23a | Before/after inventories, occurrence/disposition lineage, resource measurements, restart/+0 checks and consistent final release manifest |
| D-R10-PUBLISH-1 | OPEN | operator | GATE-G3 → P32.25 | Signed candidate-specific readout; approved artifact digests; safe origin/cache rollback and unauthenticated public checks |
| D-R10-MEMORY-1 | OPEN | P32.8 | P32.8 | Both worker closeout and orchestrator repair use one authoritative-chain protocol; stale-worktree/uncertain-PR/crash tests and cutover commit recorded |
| D-R10-USERS-1 | OPEN | P32.24 | P32.24 | Frozen-release task results with actual numerator/denominator, uncertainty/comprehension failures and accessibility session; no simulated agents counted as user… |
| D-P32.3-1 | OPEN | operator | BL-058 | every `sig.org.name` key in `entity_identifier` has a recorded disposition (`same_as`/`distinct` decision rows or an accepted "keep" record); the report's `spli… |
| D-P32.10a-1 | OPEN | engineering | P32.5 | `sqitch verify` over a fully deployed container exits 0 (today: `ERROR: division by zero` at `verify/shared_temporal_contract.sql:30`, `count(*)=28`) |
| D-P32.16-1 | OPEN | operator | GATE-G3 | `ops/config.toml [intake]` carries `operational=true`, a named owner and `staffed=true` in a reviewed change; the packet's §7 exclusions are enumerated on file;… |
| D-P32.16a-1 | OPEN | engineering | P32.16a | `sqitch revert` over a fully deployed container exits 0 (today: `ERROR: cannot drop extension postgis because other objects depend on it` at `revert/extensions.… |
| D-P32.18-1 | OPEN | operator | BL-058 | per-target green registry/rights basis; captured digests recorded against the reviewed URLs; a rebuilt `sig.dossier-packet/1` whose fact-to-capture ledger binds… |
| D-P32.19-1 | OPEN | operator | BL-058 | per-target green registry/rights basis; captured digests recorded against the reviewed URLs; a rebuilt `sig.dossier-packet/1` whose fact-to-capture ledger binds… |
| D-P32.20-1 | OPEN | operator | BL-058 | per-target green registry/rights basis; captured digests recorded against the reviewed URLs; a rebuilt `sig.dossier-packet/1` whose fact-to-capture ledger binds… |
| D-P32.21-1 | OPEN | operator | BL-058 | per-target green registry/rights basis; captured digests recorded against the reviewed URLs; the funnel's capture/extraction/link stages populated from real cap… |
| D-P32.23a-1 | OPEN | operator | P32.23 | `LIVE_RETURN_PASS.json`'s command sequence runs over the hosted DSN; the produced `CANDIDATE_MANIFEST.json` validates (frame check `consistent`, `materializatio… |
| D-R11-SEC003-1 | OPEN | engineering | P37.8 | the posture and the counts are published with an as-of date, stating that the text is not legal advice and has not been reviewed by counsel (ADR-167); then an o… |
| D-R11-ADR124-1 | OPEN | engineering | P34.26 → P34.46 → P37.46a | allow rows exist for every registry-matched organisation, each naming its ADR-159 basis, and the API serves `pending_publication_review` for every other flagged… |
| D-R11-ARCHIVE-1 | OPEN | operator | P37.55 → P35.5 → P35.63 | a production Zenodo version DOI under the concept DOI with the digest manifest (a `docs/build/reports/DEPOSITS.md` production row), and a mirror outside GCS ser… |
| D-R11-GOV017-1 | OPEN | engineering | P37.72 | the analysis is committed with its result: a pass ships the control as approved; a fail records the pause and the operator's answer; then a transition citing it |
| D-R11-RIGHTS-1 | OPEN | operator | P36.2 | each source's terms captured verbatim, its HG-03 line answered by the operator, and `sources.toml` recording the outcome; then a transition citing them |
| D-R11-OSMUID-1 | OPEN | engineering | P34.49 | an Overpass capture taken after the fix holds no `user`/`uid` (a byte-level test on a fresh capture) and the query no longer requests them; then a transition ci… |
| D-R11-LATER-01 | OPEN | operator | P30.2b → HUMAN-H4 → HUMAN-H5 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-02 | OPEN | operator | BL-040 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-03 | OPEN | operator | P21.7 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-04 | OPEN | operator | BL-028 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-05 | OPEN | operator | BL-035 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-06 | OPEN | operator | BL-057 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-07 | OPEN | engineering | BL-041 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-08 | OPEN | engineering | BL-003 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-09 | OPEN | engineering | BL-055 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-11 | OPEN | engineering | BL-025 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-12 | OPEN | engineering | BL-056 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-13 | OPEN | engineering | BL-058 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-14 | OPEN | engineering | BL-014 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-16 | OPEN | engineering | BL-056 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-17 | OPEN | engineering | BL-055 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-18 | OPEN | operator | GATE-P | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-19 | OPEN | operator | P35.1b | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-20 | OPEN | engineering | P35.59 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-21 | OPEN | engineering | BL-002 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LATER-22 | OPEN | operator | BL-056 | the trigger is recorded as fired (a dated GATE DECISIONS row or the measured fact) → decompose-spec mode=extend seeds the unit's rows; the row closes only by an… |
| D-R11-LIC006-1 | OPEN | engineering | BL-046 | a landed row whose new sqitch change stores ODbL-compartment physical-asset records in a physically separate table, with a test that no CC-BY table holds them; … |
| D-P34.1-1 | OPEN | engineering | P38.1 | every `CI` workflow run on `main` after the merge shows a non-`cancelled` conclusion (`gh run list --branch main --workflow CI` / the check-runs API); P38.1's a… |
| D-P34.2-1 | OPEN | engineering | BL-084 | `scripts/ci/npm_audit_gate.sh --full` green with the entries REMOVED (the gate already notes when an entry covers no current finding); `npm --prefix web audit -… |
| D-P34.2-2 | OPEN | engineering | P38.1a | `python3 docs/build/tools/verify_recorded_ci.py --all` green in a nightly run record; P38.1a's audit names this row |
| D-P35.38a-1 | OPEN | operator | P34.17 | every `/data-collection/` row in `docs/build/reports/copy-batches/batch-01.md` reads `confirmed` with the operator's verbatim words and a `date -u` stamp in the… |
| D-P34.3-1 | OPEN | engineering | P34.3 | re-run `implement-spec spec=docs/tickets/204_P34.3__ops-data-protection.md live_verification=true` (the contract's re-run line), equivalently `ops/gcp/protect.s… |

← back: CURRENT.md
