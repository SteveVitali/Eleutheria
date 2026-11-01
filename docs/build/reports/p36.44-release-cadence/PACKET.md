<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P36.44 — release cadence `live` leg packet (`prepared_not_executed`)

**Status:** `prepared_not_executed` (OM-19) — the `hosted` environment is
absent in this run context (no `SIG_GCP_PROJECT`, no ADC, no scheduler
invoker identity, no recorded authorisation). The engineering + machinery +
this packet landed; the named mutations queue here.

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/387_P36.44__release-cadence-automation.md live_verification=true`
— resumes at the trigger creates; the cadence machinery ships either way.

## The named mutations (OM-20, GATE-G5 §4 — expires GATE-G6)

`ops/gcp/release-cadence.sh --apply`:

1. `gcloud scheduler jobs create http sig-sched-release-cut --schedule
   '0 14 15-17 * *' --time-zone=Etc/UTC --uri …/jobs/sig-release:run
   --http-method=POST --oauth-service-account-email=$SIG_SCHEDULER_SA_EMAIL
   --message-body '{"overrides":{"containerOverrides":[{"args":["-c","exec
   sig-ops release-cadence --apply --alert --registry
   ${SIG_RELEASE_REGISTRY_URI}"]}]}}'` — the three candidate days (the
   contract's "first weekday on/after the 15th at 14:00Z" can only ever be a
   15th/16th/17th); the job-side `sig.release-cadence/1` evaluator
   suppresses every candidate that is not the first weekday — 2026-11-16
   Mon / 2026-12-15 Tue are the window cell's literal instances.
2. `gcloud scheduler jobs create http sig-sched-materialize --schedule
   '0 8 * * 0' --time-zone=Etc/UTC --uri …/jobs/sig-materialize:run
   --http-method=POST --oauth-service-account-email=…` — weekly Sundays
   08:00 UTC (G1 §3.6 verbatim); the job's baked args run the materializer
   step so the read models lag live claims by at most 7 days (SIG-OPS-008).
3. Commit `ops/cadence.toml`'s two rows **in the same re-run commit** — the
   release-cut row plus `sig-materialize`'s `[[manual_jobs]]` note flipping
   off "no trigger by design" — so `live-diff`'s undeclared-trigger report
   stays clean.

**Window:** `AR-3 + AR-2` — never inside 03:00–06:30Z or the monthly batch
window (day 6 00:00Z → day 13 12:00Z); the script exits 42 (queued). The
`--apply` leg also refuses (exit 42) when either target job (`sig-release`
— D-P35.53-1 may still be queued; `sig-materialize`) is absent.

**Restore point:** `gcloud scheduler jobs delete sig-sched-release-cut`
then `gcloud scheduler jobs delete sig-sched-materialize` (definition
removal — the jobs themselves are untouched).

## The cadence rules the driver encodes (verbatim)

- **scheduled** — first weekday on/after the 15th at 14:00Z
  (`evaluate → decision=cut`, trigger `scheduled`);
- **suppressed** — a Class S promotion within the previous 14 days
  suppresses the scheduled cut (off the registry journal's `promoted`
  event `class` — a recorded fact, never a guess);
- **early** — net-new publishable claims ≥ 10 % of the release's published
  claims AND ≥ 14 days since the last promotion (absent delta inputs →
  `not_evaluable`, never a fabricated denominator);
- **max age** — a release older than 35 days fires the recorded
  `release-max-age` alert (severity `alarm`, the OBS.1 ledger seam); it
  cuts only when no cut is running (the journal's in-flight fold);
- **freeze** — no cut starts inside an AR-3 window: a *recorded check* in
  every `sig.release-cadence/1` (`window.ar3` names it) plus
  `release cut`'s own `assert_not_frozen` — two layers, one rule;
- **never inside AR-3** — the leg driver itself exits 42 in the windows.

## What landed (the non-production half)

- `ops/src/ops/release_cadence.py` — the shared drift evaluator
  (`sig.release-cadence/1`): `cut_day`/`scheduled_due` (first weekday
  on/after the 15th), `promotions_from_events` + `last_promotion` (Class
  S/R off the journal), `in_flight_publications` (the §3.4 fold), the
  `evaluate` decision record (scheduled / suppressed / early / max-age /
  frozen / hold / no_release), the append-only decision emit
  (`cadence/<ts>.json` + `decisions.jsonl`), and `fire_max_age_alert`
  through the recorded-alert seam (`ops.alerts` — the ledger write stands
  even when no notifier is configured). `run_release_cadence` is the
  `sig-ops release-cadence` verb: evaluate → emit → alert → journal →
  (decision=cut) `release cut`.
- `ops/src/ops/cli.py` — the `release-cadence` verb
  (`--registry`/`--facts`/`--at`/`--out`/`--alert`/`--ledger`/`--apply`/
  `--skip-host-clock-check`; exit 0 ok, 2 refusal, 6 a recorded alert).
- `ops/gcp/release-cadence.sh` — the leg driver (`--check` prints the plan
  offline; `--apply` is window + ADC + env + target-job gated → exit 42
  queued, never a partial create).

## Verification

`tests/ops/test_release_cadence.py` (23 tests) +
`test_release_cadence_leg.py` (3): the cut-day calendar (the window cell's
literal 2026-11-16 Mon / 2026-12-15 Tue instances + the Sat→17/Sun→16
slide), the 14:00Z slot bounds, the journal promotion fold + class, the
in-flight fold, the scheduled cut, the Class-S-14-day suppression (and its
expiry + Class R's non-suppression), the ≥10 %/≥14-day early trigger (and
its honest `not_evaluable`), the 35-day alert (+ the no-double-cut rule),
the recorded AR-3 freeze (cuts blocked, alerts not), `no_release`, the
append-only emit, the alert-ledger row, the fixture-registry apply
(journals cadence + cut), the script's offline plan + exit-42 queue.
