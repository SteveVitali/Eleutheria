# RELEASE-STAGE-THROUGHPUT — the D-P37.65a-3 fix leg (release stage at national scale)

- **Obligation:** `D-P37.65a-3` (kind F — `docs/tickets/DEFERRALS.md`,
  created 2026-11-25 by the `D-P37.65a-1` re-cut leg; the row is carried
  verbatim into this branch — its `e0` anchor's `row_sha256`
  `fceb898c79e79db441dc20a3b708a44259ae98f64c58686fd1257237ff5b8677` is the
  same bytes `r11/P37.65a-live-2` records).
- **Harness:** devin-desktop/swe-2-high/subagent
- **Base / branch:** `origin/r11/P38.3c-round11-integration-plan-2`
  (`ac52d33e`) → `r11/ops-release-stage-throughput`
- **Config:** engineering dispatch — **no live legs executed**, no live GCS
  mutation, no ADC/`SIG_GCP_PROJECT` in this context. The registry `LOCK`
  held `{verb:"stage", acquired 2026-11-25T19:41:59Z}` is honest residue of
  the measured death — not touched; the resume path handles it on the next
  live leg (a `stage` verb refuses `lock-held` until the operator's
  `--break-lock <reason>`, exactly the recorded contract).
- **Gate:** none — code + fixture/fake verification only.

## The bound defect (verbatim from the deferral)

`verb_stage` ran a serial `store.insert` + `lock.refresh()` (a full
`registry_state_digest` = 5 `read`s + the lock probe) **per object**, and
every GCS call resolved a fresh token via `gcloud auth application-default
print-access-token` — measured 5–6 s wall each (gcloud 583.0.0), ~40–60
s/object total: 8 objects in ~9.6 min ≈ **0.014 obj/s** → the
462,497-object `r/`+`releases/` plan projects to ~380 days. A token call
exceeding the 15 s timeout was a hard unhandled `GcsError` — the verb died
mid-plan at 8/462,497 leaving the LOCK held (traceback:
`docs/build/logs/p37.65a-live-1/11-stage.txt`, on `r11/P37.65a-live-2`).

## What landed — three fixes, one file each

**`ops/src/ops/gcs.py` — cached token + bounded retry.**

- `CachingTokenProvider` (new, the default `GcsBucket.token_provider` via
  `field(default_factory=…)`): resolves the access token ONCE and reuses it
  until near expiry — `SIG_GCS_ACCESS_TOKEN` trusted for the process, the
  metadata server's `expires_in` honoured with a 60 s margin, a gcloud ADC
  token cached 45 min (Google's ~1 h lifetime, refreshed early). Resolution
  itself bounded-retries (3 attempts, small backoff) so one slow/hung
  `gcloud` call is a retry, never the mid-plan hard exit — then the
  caller's honest `GcsError`, unchanged in kind. Thread-safe: the insert
  pool shares it.
- `GcsBucket._call` (the one request path every verb method now routes
  through): bounded retry on transport errors / throttling / 5xx
  (`_TRANSIENT_STATUSES = {408,429,500,502,503,504}`); a 401 calls the
  provider's `invalidate()` and re-resolves once; a 412 precondition still
  raises `GcsPreconditionFailed` un-retried; a 404 still returns `None` on
  `get_object_meta` / `GcsError "HTTP 404"` on `get_object` (the
  `GcsStore.read` contract). Injected `token_provider=`/`opener=` fakes keep
  per-call semantics — every existing test passes untouched.

**`ops/src/ops/release_pipeline.py` — amortised heartbeat + bounded pool.**

- `verb_stage` inserts through a `ThreadPoolExecutor` of width `--workers`
  (default `STAGE_WORKERS = 16`; `workers=1` keeps the serial shape). The
  pool is chunk-submitted (4× width) so a worker refusal propagates with at
  most a chunk in flight — the inserted objects stay (resume contract), the
  lock stays held, nothing half-writes.
- `lock.refresh()` is now a **heartbeat** — every `STAGE_LOCK_REFRESH_N =
  512` objects or `STAGE_LOCK_REFRESH_S = 60 s`, whichever first —
  instead of per object. `lock.release()` still re-checks the digest at
  close, so a drifted registry is refused no later than release (pinned by
  `test_drift_mid_run_still_refuses_at_release`).
- `Store.details(prefix)` (new, both stores): one paged
  name→`{md5Hash,size}` listing per namespace is the resume parity basis —
  `_stage_one` decides identical-byte skip / name collision from it, so a
  resume pays ~4 listings + the missing objects' inserts instead of a
  POST+stat pair per object. A store without `details` falls back to the
  old POST→412→stat path. `stage_workers` is recorded on the `staged`
  journal event.

**`ops/src/ops/cli.py`** — `release stage` gains `--workers` and
`--lock-refresh-s` (defaults from the module constants; never a new
defaulting decision — the CLI passes them through).

## Verification

- `uv run pytest tests/ops/test_release_pipeline.py` — **24/24 green**
  (the pinned lock/namespace/collision-resume contracts unchanged).
- `uv run pytest tests/ops/test_release_stage_throughput.py` — **22/22
  new pins**: token reuse within TTL (1 resolution over 5 calls), TTL/metadata
  expiry re-resolution, transient-resolution bounded retry, `invalidate()`,
  5xx/transport retry, bounded fail-closed, no 4xx/412 retry, 401→invalidate→
  re-resolve once; parallel stage/resume/collision; heartbeat amortisation
  (11 registry reads for 40 objects vs the old 211, 36 on the count
  interval); drift refused at release; resume via listing (0 stat, 2 inserts
  — lock + journal); the `staged` event's `stage_workers`.
- `uv run ruff check` + `ruff format --check` — clean on touched files.
- `uv run mypy -p ops` — clean.

## The owed rate benchmark — measured, honestly labelled a projection

`_LatentStore` (in `tests/ops/test_release_stage_throughput.py`) bills
**150 ms per remote-shaped call** — the order of a real GCS JSON-API
round trip — over a 2,000-object built tree, `verb_stage --apply` for real:

| path | measured obj/s | 462,497 objects in |
|---|---|---|
| serial `workers=1` (fixed path) | **6.2** | ~20.7 h |
| `workers=16` (the default) | **75.5** | **~1.70 h** |
| `workers=32` | **126.7** | ~1.01 h |
| resume, `workers=16` (all identical) | **235.4** | ~0.55 h |

vs the live-measured **0.014 obj/s** baseline (≈380 days): the default
pool is ~5,400×, and even the serial shape is ~440× — the dominant cost
was the per-call token subprocess, not the writes. The numbers are a
*projection* (constant 150 ms/call, tiny bodies): real GCS latency varies
and object bytes add upload time, but the per-object call count — the
defect — is what's fixed: ~1 call/object staged, ~0/object resumed, one
digest per ~512 objects/60 s instead of 6+ calls/object. The live
`--apply` re-leg under `D-P37.65a-1`'s window is the cell's own
confirmation; it could not run here (no ADC/`SIG_GCP_PROJECT`, the
registry bucket is the operator's).

## Refusal matrix — unchanged

name-collision (listing-decided or 412→stat), lock-held, stale-generation
(at heartbeat or release), empty-plan, no-registry, dry-run default — all
pinned paths untouched; `release stage` still writes only under `--apply`.

## Residual for the next live leg

`D-P37.65a-3` stays **PARTIAL** (event `D-P37.65a-3:e1`): the machinery is
landed and fixture/fake-verified at a rate that completes the plan inside
a run window, but the verify cell's own words are "over a national-scale
built tree" — the live `release stage --apply` against
`gs://…-sig-release` (with `--break-lock <reason>` for the held
`{verb:stage, 2026-11-25T19:41:59Z}` residue) runs with the `D-P37.65a-1`
re-cut under operator ADC. `--workers 32` is the suggested starting width.
