# Readout — HUMAN-H3 (ACCT.1 / GL-ACCT-01) — Accounts, credentials, hosting

- **Chain row:** P23.4 · **Kind:** human marker · **Gate register:** HG-07, HG-08, HG-09, HG-12
- **Ticket:** `docs/tickets/P23.4__accounts-credentials-hosting.md`
- **Dispositioned:** 2026-09-10 by orchestrate-build (applying pre-recorded GL-GATE-04; secrets never in any file — `provided: yes/no` only)

## Verdict: RECORDED — host answered (GL-GATE-04); all credentials `provided: no`

| item | gate | provided |
|---|---|---|
| Zenodo (sandbox + prod) account | HG-07 | **no** |
| S3-compatible object store + optional Software Heritage token | HG-07 | **no** |
| MapRoulette API key + registered OSM Organised-Editing page | HG-08 | **no** |
| API tokens `SIG_MUCKROCK_TOKEN`/`SIG_DATA_GOV_KEY`/`SIG_OVERPASS_ENDPOINT`/`SIG_CIVICCLERK_BASE` | HG-09 | **no** |
| Real host target on GCP `$SIG_GCP_PROJECT` + Secret Manager | HG-12 / GL-GATE-04 | **no** (host *choice* answered) |
| `SIG_GCP_PROJECT` exported in run shell / Secret Manager | HG-12 / GL-GATE-04 / D3 | **no** |

**Host choice pre-answered (GL-GATE-04):** GCP project `$SIG_GCP_PROJECT` (name `eleutheria`),
zero/low-cost design (SIG-STORE-003); DEPLOY.1 (P24.1) picks Cloud SQL vs `e2-micro` GCE in its
ADR. The GCP `apply` is separately gated on operator `gcloud` ADC in the run shell.

## Env names the re-runs need (not values)
`SIG_ZENODO_SANDBOX_TOKEN`, `SIG_OBJECT_STORE_URL/KEY/SECRET`, `SIG_SWH_TOKEN` (optional),
`SIG_MAPROULETTE_API_KEY`, `SIG_OSM_OE_PAGE`, `SIG_MUCKROCK_TOKEN`, `SIG_DATA_GOV_KEY`,
`SIG_OVERPASS_ENDPOINT`, `SIG_CIVICCLERK_BASE`, `SIG_GCP_PROJECT` + `gcloud` ADC.

## What would pass it
Operator provisions the accounts, exports each `SIG_*` env var / `gcloud` ADC in the re-run shell,
and flips each row to `provided: yes`. `check-build-memory.sh` confirms no token literal in any file.

## Consequence recorded
Every credentialed re-run (P21.3/P21.4/P21.5/P21.7/P21.8/P21.9) and the P24.1 GCP `apply` stays
PREPARE-ONLY → RETURN PASS / gate-pending. DEFERRALS `D-P21.3-2`(HG-09), `D-P21.5-1`(HG-07),
`D-P21.7-1`(HG-08), `D-ACCT.1-1`(HG-12) remain OPEN.

## Addendum — DATE CORRECTION (SEED-08, appended 2026-10-01T08:21:03Z; ADR-146; append-only)

- *Agent record (labelled): written by Claude Code, harness `claude-code/claude-opus-5-5/subagent`, Round-11 Stage-B unit SEED-08.* The text above is unchanged; this changes no status.
- **DC-RO-05.** Line 5's disposition date is a Round-3 "chain date": recorded 2026-09-10 → true 2026-09-13T19:40:01Z (retro: the writing commit `eb72be5f`; `docs/build/runs/P21.5.md` line 23: "Environment clock read 2026-09-13; chain date for this re-run = 2026-09-10"). Register rec 1023.
- **Harness and model (B7 §3 S4).** The disposition was written in the Devin CLI session `polydactyl-author` with model `claude-opus-4-8-medium` (retro: B7 §1–§3). It applied the pre-recorded GL-GATE-04 answer, not an answer given at this gate's pause. The annotation of the restored GATE DECISIONS block in `docs/build/LEDGER.md` (SEED-06) classes this gate's restored entry R40 as clock-false and delegated.
