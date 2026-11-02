<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P36.43 — status lane `live` leg packet (`prepared_not_executed`)

**Status:** `prepared_not_executed` (OM-19) — the `hosted` environment is
absent in this run context (no `SIG_GCP_PROJECT`, no ADC, no pinned image
digest, no recorded authorisation). The engineering + machinery + this
packet landed; the named mutation queues here.

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/386_P36.43__status-lane.md live_verification=true`
— resumes at the job create; the publish code ships either way.

## The named mutation (OM-20, GATE-G5 §4 — expires GATE-G6)

`ops/gcp/status-publish.sh --apply`:

1. `gcloud run jobs deploy sig-status-publish --image <@sha256:…> --region
   us-central1 --service-account $SIG_STATUS_SA_EMAIL
   --no-allow-unauthenticated` (the pinned-digest image, P31.4/ADR-111 —
   never a mutable tag; least-privilege ACT-13 identity, read-only
   `v_transparency_*` views + the scheduler list).
2. `gcloud scheduler jobs create http sig-sched-status-publish --schedule
   '12 */6 * * *' --time-zone=Etc/UTC …` — every 6 h (D-J3-11 = yes).
3. `gcloud run jobs add-iam-policy-binding sig-status-publish … roles/run.invoker`
   for the scheduler SA.
4. Commit `ops/cadence.toml`'s status row **in the same re-run commit** so
   `live-diff`'s undeclared-trigger report stays clean.

**Window:** `AR-3 + AR-2` — never inside 03:00–06:30Z or the monthly batch
window (day 6 00:00Z → day 13 12:00Z); the script exits 42 (queued).

**Restore point:** `gcloud scheduler jobs delete sig-sched-status-publish`
then `gcloud run jobs delete sig-status-publish` (definition removal).

## What landed (the non-production half)

- `ops/src/ops/status_lane.py` — `sig.status-lane/1` builder +
  `sig.status-heartbeat/1` (`status/state.json`), per-source
  `sig.status-source/1`, `status/archive/<YYYY-MM-DD>.json` (append-only),
  and the zero-JS `index.html` / `sources/index.html` / `issues/index.html`
  emitters; the S-1 secret gate aborts the whole publish set.
- `ops/src/ops/status_publish.py` + `sig-ops status-publish` —
  `emit` renders the file set from `runs.jsonl` + `sources.json`;
  `--apply` pushes status/** through the status-scoped publish leg
  (`ops/public_routes_status.toml`; `status/archive/**` never deleted; the
  site tree never touched).
- `web/src/lib/status-lane.ts` + `web/src/components/SourceStatusRow.astro`
  (K9 C-12's shared row component at the status clock) +
  `web/src/pages/status/sources/index.astro` and the `/status/` lane
  sections — T1, zero-JS, gated/refused/withdrawn as counts only.
- `ops/gcp/status-publish.sh` — the leg driver (`--check` prints the plan
  offline; `--apply` is window + env gated → exit 42 queued).

## Verification

`tests/ops/test_status_lane.py` (22 tests) + `test_status_publish_leg.py`
(3) + `tests/unit/test_p36_43_copy_batch.py` (3) +
`web/tests/unit/status-lane.test.ts` (6): heartbeat shape, window counts,
verdict-at-status-time + next-run-DAY granularity, counts-only for
count-only states, robots host+count+GL-GATE-08, drift-flag states, the
append-only archive, the secret-gate abort, zero-`<script>` HTML, the
scoped publish plan + apply over a fake bucket, deterministic emit.
