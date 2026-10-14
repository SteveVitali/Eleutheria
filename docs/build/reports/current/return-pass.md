# link-out: return-pass (page 1/1)

- the generated LEDGER region `### RETURN PASS — current` is the
  authority (`return_pass.py`); owed obligations in a row land there.
| ticket | obligations | re-run line |
|---|---|---|
| P21.5 | D-P21.5-1 (PARTIAL) | chain row 482 **P37.55** (11D, after P34.21b) · landed as row 59 (PR #61; prepare-only re-run row 76, PR #76) |
| P31.4 | D-P31.4-1 | chain row 247 **P34.39a** (11A, clock-guarded; prerequisite of P34.46); verify = the D-P31.4-1 command in DEFERRALS; P34.39b (row 248) carries the first-fire re… |
| P32.18 | D-P32.18-1 | chain rows 438 **P37.16a** and 439 **P37.16b** (11D; the four captures are split by family across the two rows, fixed by the PLAN-11D contracts); packet `docs/b… |
| P32.19 | D-P32.19-1 | chain rows 438 **P37.16a** and 439 **P37.16b** (11D; the four captures are split by family across the two rows, fixed by the PLAN-11D contracts); packet `docs/b… |
| P32.20 | D-P32.20-1 | chain rows 438 **P37.16a** and 439 **P37.16b** (11D; the four captures are split by family across the two rows, fixed by the PLAN-11D contracts); packet `docs/b… |
| P32.21 | D-P32.21-1 | chain rows 438 **P37.16a** and 439 **P37.16b** (11D; the four captures are split by family across the two rows, fixed by the PLAN-11D contracts); packet `docs/b… |
| P32.22 | D-R10-LIVE-1 | chain row 338 **P35.61** (11B; >= 48 h after P34.46, after the 11B spine writes); packet `docs/build/reports/p32.22-bounded-recovery/LIVE_RETURN_PASS.json` · la… |
| P32.23a | D-P32.23a-1 | chain row 339 **P35.62** (after P35.61); packet `docs/build/reports/p32.23a-release-candidate/LIVE_RETURN_PASS.json` · landed as row 188 (PR #180) |
| P32.25 | D-R10-PUBLISH-1 | chain row 341 **P35.63** (after P35.62); rollback cases `docs/build/reports/p32.25-accepted-release-verification/LIVE_RETURN_PASS.json` · landed as row 191 (PR … |
| — | HG-05 (old P23.1 row; no deferral) | none — operator action, not in `returnPass` |
| P34.3 | D-P34.3-1 | the OM-19 `r11/P34.3-live-<n>` dispatch, or `implement-spec spec=docs/tickets/204_P34.3__ops-data-protection.md live_verification=true` — `protect.sh --apply` t… |
| P34.4 | D-P34.4-1 · D-P34.4-2 | the OM-19 `r11/P34.4-live-<n>` dispatch, or `implement-spec spec=docs/tickets/205_P34.4__alerts-that-reach-a-human.md live_verification=true` — `alerts.sh --app… |
| P34.5 | D-P34.5-1 · D-P34.5-2 · D-P34.5-3 | -3: `implement-spec spec=docs/tickets/206_P34.5__cost-guard-budget-alert-billing-export.md live_verification=true` once `exportcheck` reads ≥1 row; -1: `cost-gu… |
| P34.6 | D-P34.6-2 · D-P34.6-3 · D-P34.6-4 · D-P34.6-5 · D-P34.6-6 | `logical-export.sh --apply export|lifecycle|relabel --go "…"`; `restore-drill.sh --apply fullrestore --go "…"`; -6: the drill re-run after P34.46's schema-chang… |
| P34.50 | D-P34.50-1 | none — operator action; **P35.67** (row 263) is the verifying probe row · landed as row 208 (PR #201) |
| P34.17 | D-P34.17-1 | `implement-spec spec=docs/tickets/220_P34.17__web-honesty-wave-and-republish-1.md live_verification=true` (scope limited to the L2 republish — `sig-ops publish-… |
| P34.18 | D-P34.18-1 | `implement-spec spec=docs/tickets/221_P34.18__personal-handle-source-id-rename.md live_verification=true` (scope limited to leg L2 — the insert-only hosted rena… |
| P34.21a | D-P34.21a-1 | `implement-spec spec=docs/tickets/223_P34.21a__attribution-gate-sink-rights-and-backfill.md live_verification=true` (scope: leg L1 only, on `r11/P34.21a-live-1`… |
| P34.21b | D-P34.21b-1 · D-P34.21b-2 | -1: `implement-spec spec=docs/tickets/224_P34.21b__attribution-re-export-and-republish-2.md live_verification=true` (scope: leg L1 only, on `r11/P34.21b-live-1`… |
| P34.38 | the queued BidNet terms-capture leg (no deferral id of its own — it works the recorded E4-R6a answer; the rights decision keeps its manifest home at row 350) | `implement-spec spec=docs/tickets/246_P34.38__sources-pilot-prep-and-registry-rows.md live_verification=true` (scope: the BidNet terms capture only) · landed as… |
| P34.39a | the queued live read-back verdict for the obligation homed on the P31.4 row above (this row carries the clock-guarded leg only); the pinned image predates P31.7… | `implement-spec spec=docs/tickets/247_P34.39a__osm-replay-read-back.md live_verification=true` · landed as row 247 (PR #245; command + fixtures + baseline shipp… |
| P34.39b | the three queued monitoring legs for the scheduled-ingest first-fire wave and the `camreg_peel_on` first fire (the fleet table, the named reads, the routing row… | `implement-spec spec=docs/tickets/248_P34.39b__first-fire-read-backs.md live_verification=true` (scope: one leg per run — L1, then L2, then L3) · landed as row … |
| P34.40 | the two queued production legs of the dark serving-topology roll (L1 the `sig-web` nginx roll by pinned digest, L2 the `/v1/*` URL-map step onto `sig-api`); the… | `implement-spec spec=docs/tickets/249_P34.40__serving-topology-dark.md live_verification=true` (scope: one leg per run — L1, then L2) · landed as row 249 (PR #2… |
| P34.42a | the queued IAM leg (G1-01/F-272 services half): create `sig-api-rt`/`sig-web-rt`/`sig-alerts-rt`, the least-privilege bindings + `sig-pg-password` access, one s… | `implement-spec spec=docs/tickets/251_P34.42a__least-privilege-service-identities.md live_verification=true` (scope: the IAM leg only) · landed as row 251 (PR #… |

← back: CURRENT.md
