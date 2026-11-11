<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.33 — watch lane `live` leg packet (`prepared_not_executed`)

**Status:** `prepared_not_executed` (OM-19) — the `hosted` environment is
absent in this run context (no `SIG_GCP_PROJECT`, no ADC, no pinned image
digest, no recorded authorisation). The engineering + machinery + this
packet landed; the named mutation queues here.

**Re-run (verbatim):**
`implement-spec spec=docs/tickets/457_P37.33__watch-lane-and-cadence.md live_verification=true`
— resumes at the job create + trigger create; the publish code ships either way.

## The named mutation (OM-20, GATE-G6 §4 — expires GATE-ACCEPT-R11)

`D-K7-2 [B-22] = the lane` carried verbatim. GATE-G6 §4 dated
2026-11-05T15:20Z names P37.33 verbatim among the 15 11D OM-20 rows —
operator selection "Approve all 15 (rec.)".

`ops/gcp/watch-publish.sh --apply`:

1. `gcloud run jobs deploy sig-watch-publish --image <@sha256:…> --region
   us-central1 --service-account $SIG_WATCH_SA_EMAIL
   --no-allow-unauthenticated` (the pinned-digest image, P31.4/ADR-111 —
   never a mutable tag; least-privilege ACT-13 identity — read-only on the
   publishable watch rows + the web bucket's watch/ prefix; no spine
   write, no release tree).
2. `gcloud scheduler jobs create http sig-sched-watch-publish --schedule
   '30 7 * * *' --time-zone=Etc/UTC …` — daily, after the agenda dailies'
   05:0x fires (SIG-WATCH-008 within-24h).
3. `gcloud run jobs add-iam-policy-binding sig-watch-publish …
   roles/run.invoker` for the scheduler SA.
4. Flip `ops/cadence.toml`'s `[[maintenance]]` `watch-publish` row to
   `state = "enabled"` **in the same re-run commit** so live-diff's
   declared-vs-live report stays clean; the daily agenda /
   twice-weekly sam_gov ingest cadence binds at the declaration-bundle
   republish (`SIG_OPS_DECLARED_GCS`).

**Window:** `AR-3 + AR-2` — never inside 03:00–06:30Z or the monthly batch
window (day 6 00:00Z → day 13 12:00Z); the script exits 42 (queued).

**Restore point (GATE-G6 verbatim):** `lane job paused` — pause
`sig-sched-watch-publish`, then `gcloud run jobs delete sig-watch-publish`
(definition removal).

## What landed (the non-production half)

- `ops/src/ops/watch_lane.py` — `sig.watch-lane/1` builder +
  `sig.watch-heartbeat/1` (`watch/state.json`), the `watch/watch.json`
  payload twin, `watch/index.html` + `watch/place/<path>/index.html` +
  `watch/item/<handle>/index.html` zero-JS emitters (upper_bound never a
  "deadline", coverage statement on every place, two clocks labelled),
  `watch/archive/<YYYY-MM-DD>.json` (append-only, refuse-on-drift); the
  S-1 secret gate + no-`<script>` gate abort the whole publish set.
- `ops/src/ops/watch_publish.py` + `sig-ops watch-publish` — `emit`
  renders the file set from a `sig/watch/2` payload at `--lane-time`;
  `--apply` pushes watch/** through the watch-scoped publish leg
  (`ops/public_routes_watch.toml`; deletes only lane-owned paths —
  never `watch/archive/**`, never the web build's facet/history/
  pagination/citations/feed files).
- `ops/cadence.toml` — legistar/primegov/civicclerk/escribe monthly →
  daily (staggered 05:0x UTC), sam_gov weekly → twice-weekly
  (`0 5 * * 1,4`); `[[maintenance]]` `watch-publish` declared PAUSED.
- `policy/freshness.py` — `twice-weekly`/`twice_weekly` nominal interval
  (3.5 d) so the freshness verdict stays evaluable.
- `ops/gcp/watch-publish.sh` — the leg driver (`--check` prints the plan
  offline; `--apply` is window + env gated → exit 42 queued).

## Verification

`tests/ops/test_watch_lane.py` (15 tests) + `test_watch_publish_leg.py`
(6): payload fail-closed parse (schema/kind/dup-handle), the lane doc +
heartbeat two-clocks shape, the emitted file set (state/lane/payload/
index/place/item/archive), upper_bound-never-deadline + contested marker +
withheld-upstream named absence, empty-place coverage statement, the
append-only archive refusal, the lane-owned delete scope (facets/feeds/
citations/archive never deleted), the scoped allow-list file, the CLI
emit + queued `--apply` (exit 42), and the script's offline posture.
