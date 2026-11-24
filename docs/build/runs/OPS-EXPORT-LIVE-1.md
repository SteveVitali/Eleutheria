# OPS-EXPORT-LIVE-1 — fresh national export + D-P37.65a-1 release-cut re-run

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (manifest row 493); the fresh-export + re-cut leg under the operator's
  round-11 integration plan — second live attempt of `D-P37.65a-1` (kind V).
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-live-1` @ `1bc1a129` (isolated worktree
  `/private/tmp/sig-export-live`).
- **Authorizations:**
  - GATE DECISIONS row `2026-11-20T07:22Z` "Run the export" (operator-signed,
    commit `d3c72f51` on `r11/P38.3c-round11-integration-plan-2`): one
    `ops/gcp/export.sh --apply` sequence (image → job → run → fetch) producing
    a fresh `exports/national/<as-of>/` in the restricted bucket carrying the
    current `web/*` artifact set; cleanup of the release-cut leg's own
    leftovers in `gs://zeta-medley-508121-u7-sig-release` — break the stale
    `registry/LOCK` (verb=stage, acquired 2026-11-20T06:48:17Z by the halted
    P37.65a-live-1 stage) via the designed `--break-lock <reason>`; the
    stranded label allocation `sig-2026-11-20.1` stays recorded-not-deleted.
  - The existing signed "Authorize now" (commit `99018e1b`, GATE DECISIONS
    row `2026-11-20T00:15Z`): re-run the D-P37.65a-1 release-cut legs —
    `sig-ops release` cut → build → sites → stage into
    `$SIG_RELEASE_REGISTRY`, then `release verify --mode S` over the staged
    candidate. Scope unchanged: release-cut + live-crawl ONLY; the promote
    stays paused (needs the operator-signed `sig.promotion-approval/1`).
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`,
  `SIG_RELEASE_REGISTRY=gs://zeta-medley-508121-u7-sig-release`, region
  `us-central1`, ADC `stevevitali@gmail.com`; every gcloud call passed
  `--project` explicitly.
- **Window:** run 2026-11-20T09:04Z→09:17Z — outside the AR-3 daily
  restricted window (03:00Z→06:30Z); the monthly freeze (12-06→12-13T12:00Z)
  does not apply. No window refusal was hit.
- **Prior leg:** `docs/build/runs/P37.65a-live-1.md` (branch
  `r11/P37.65a-live-1`, read-only). Its candidate `p-846b3554…` is
  dead-on-arrival (export `2026-09-27` predates the `web/*` artifact set);
  its staged objects are resume-safe residue — not deleted.
- **Evidence:** `docs/build/logs/ops-export-live-1/` (gitignored subtree).

## Verdict

| leg | verdict |
|---|---|
| `export.sh --check all` | plan OK |
| `export.sh --apply image` | **DONE** — `sig-api:export-1bc1a1298da8`, digest `sha256:e9bf33e01b927214592db9a8e7997ba4576952e804e438acee59a21a8dd5799a`, Cloud Build `7c43ada1-1bec-493b-9c34-ea775170c8ca` SUCCESS 4m21s |
| `export.sh --apply job` | **REFUSED (IAM)** — first attempt; see "Resumed leg" (the bindings landed at 16:00Z and the re-pin went `Ready=True`). The template still updated to the new pinned digest but the job was `Ready=False` (`SecretsAccessCheckFailed`). |
| `export.sh --apply run` / `fetch` | **attempted in the resumed leg — `run` refused at the gcsfuse mount (Blocker 2); `fetch` not reached.** No fresh `exports/national/<as-of>/` exists. |
| cleanup: break stale `registry/LOCK` | **DONE** — via `release cut --apply --break-lock "<reason>"`; reason recorded into the versioned lock chain; `registry/LOCK` absent poststate. |
| stranded label `sig-2026-11-20.1` | **left recorded-not-deleted** — `labels.json` byte-identical pre/post. |
| `release cut` | **journaled** — event `registry/events/000005-20261120T091438-cut-root.json`, T0 `2026-11-20T09:14:38Z`, `host_clock.ok=true` (skew 0.214 s). The event's declared legs (`restore-point`, `materialize`, `export run`, `fetch`) did **not** run — the export leg is blocked; a follow-on attempt re-cuts (journal is append-only). |
| `release build → sites → stage → verify --mode S` | **not run** — no fresh export exists; re-running `build` over the stale `2026-09-27` export would only re-produce the dead-on-arrival candidate. No mutation made. |

`D-P37.65a-1` remains **OPEN**.

---

## Resumed leg — 2026-11-20T15:59Z→16:09Z (gate cleared by `b4bbae0e`)

The operator's signed `"Yes — include export SA"` (commit `b4bbae0e`, GATE
DECISIONS `2026-11-20T09:40Z`) extended the scoped-grants go to
`sig-export-rt`'s three declared bindings. Applied verbatim + receipts:

| binding | before | after (receipt) |
|---|---|---|
| `roles/cloudsql.client` (project) → `sig-export-rt` | members `default-compute`, `sig-api-rt` | **added** — policy etag `BwZgt1WXcN4=`; member now listed (`07-bind-cloudsql.txt`, `09-iam-poststate.txt`) |
| `roles/storage.objectCreator` on `…-sig-restricted` → `sig-export-rt` | no `objectCreator` binding | **added** — `--condition=None` (the declared binding is unconditional; gcloud required the explicit flag non-interactively — recorded refuse + retry verbatim in `08-bind-bucket-secret.txt`); etag `CAU=` |
| `roles/secretmanager.secretAccessor` on `sig-pg-password` → `sig-export-rt` | members `default-compute`, `sig-api-rt` | **added** — etag `BwZgt1ZRxd4=`; member now listed |

No wider IAM change was made.

| leg | verdict |
|---|---|
| `export.sh --apply image` (re-run — the tag derives from `HEAD`, which moved to `c7a2b53e` on the ledger commit) | **DONE** — `sig-api:export-c7a2b53edf7e`, digest `sha256:bddfef084d3ba27fb92cd675241361812415a860e312b5a59e74273af913e357`, build `00f9dc32-0ac4-4ced-9c0a-bc80675b2f03` SUCCESS 3m7s (`10-image-rebuild.txt`) |
| `export.sh --apply job` | **DONE** — `sig-export` deployed on `…@sha256:bddfef084d…`, `Ready=True` (the secret-access check now passes) |
| `export.sh --apply run` (`SIG_EXPORT_AS_OF=2026-11-20T16:04:19Z` → `exports/national/2026-11-20T160419Z/`) | **REFUSED — declaration gap.** Execution `sig-export-dpwsm` failed at the gcsfuse mount (~100 s): `PermissionDenied … sig-export-rt does not have storage.objects.list access … Permission 'storage.objects.list' denied on …-sig-restricted` (`12-run-poststate.txt`, execution logs). Zero objects written under the prefix. |
| `fetch` / re-cut `build → sites → stage → verify --mode S` | **not run** — no fresh export exists. |

## Blocker 1 — RESOLVED at 16:00Z (the IAM bindings)

`export.sh --apply job` → `gcloud run jobs deploy sig-export …` refused
(`03-job.txt`, 09:13:15Z):

```
ERROR: (gcloud.run.jobs.deploy) spec.template.spec.containers[0].env[3].value_from.secret_key_ref.name:
Permission denied on secret: projects/873541617837/secrets/sig-pg-password/versions/latest
for Revision service account sig-export-rt@zeta-medley-508121-u7.iam.gserviceaccount.com.
The service account used must be granted the 'Secret Manager Secret Accessor' role
(roles/secretmanager.secretAccessor) at the secret, project or higher level.
```

Poststate read (`status.conditions`, observedGeneration 6): the job template
**did** update to `sig-api@sha256:e9bf33e0…` with the declared env/volume/SA
shape, but the job was `Ready=False`, `reason=SecretsAccessCheckFailed`.

Wider drift found (all read-only probes, no mutation): `sig-export-rt` held
**none** of its declared bindings — all three were **absent** live vs
`ops/iam_identities.toml` / `sig-ops iam plan --leg jobs` (steps 14, 25, 29).

→ **Resolved by the resumed leg:** the operator's `b4bbae0e` go authorized the
three verbatim bindings; all three applied + receipt-verified (see above).

## Resumed leg 2 — 2026-11-20T17:55Z→17:57Z (declaration gap cleared by `4c75c68e`)

The operator's `"objectUser on the bucket"` (signed commit `4c75c68e`, GATE
DECISIONS `2026-11-20T16:30Z`) authorized amending the declaration + applying
the binding:

1. **Declaration amended + committed** — `ops/iam_identities.toml`:
   `sig-export-rt` on `sig-restricted` `objectCreator` → `objectUser`, with
   the reason + `4c75c68e` cited in the block comment (commit `32b2255e` on
   this branch). `sig-ops iam plan --leg jobs` step 25 re-renders as
   `objectUser`.
2. **Binding applied verbatim** (`13-bind-objectuser.txt`) —
   `add-iam-policy-binding … --role=roles/storage.objectUser --condition=None`
   (etag `CAY=`); then the now-undeclared `objectCreator` **removed**
   (`--all`, etag `CAc=`) — the declared=live convention flags a live grant
   the TOML no longer declares (`iam_identities.py:1534` "undeclared bucket
   role on a runtime SA"). Final state: exactly `objectUser` for
   `sig-export-rt` on the bucket.
3. **`export.sh --apply run`** — `SIG_EXPORT_AS_OF=2026-11-20T17:56:21Z` →
   prefix `exports/national/2026-11-20T175621Z/`. Execution `sig-export-qjhg8`:
   **mount OK** (objectUser fixed it — `GetStorageLayout` + mount logged
   clean), **secret fetch OK**, **Cloud SQL connect OK** — then the export
   crashed inside the spine read:

   ```
   File "/app/exports/src/exports/shaping.py", line 2484, in fetch_shaping_raw
   psycopg.errors.UndefinedColumn: column ce.bound_at does not exist
   LINE 1: ...ource_id, ce.capture_id, ec.retrieved_at, ce.bound_a...
   ```

   `failedCount:1`, exit 1, 17:57:06Z. **Zero objects** under the prefix.

## Blocker 3 — CURRENT (hosted spine schema behind the image)

`claim_evidence.bound_at` is added by sqitch change
`claim_assertion_bindings` (P32.2, plan line 44, 2026-10-03). The HEAD
`fetch_shaping_raw` queries read it directly (the `shaping_claims` /
eligible-occurrence SQL). The hosted `sig-pg` spine predates that change —
it is **at least ~40 committed sqitch changes behind** the schema the current
export image expects (every change after `claim_assertion_bindings` in
`db/sqitch.plan`: `shared_temporal_contract`, `publication_dispositions`,
`transparency_views`, `claim_sightings`, `camera_site_derivation`, …). The
September export succeeded because its image matched the then-deployed
schema; the live spine has not received the Round-11 schema chain.

The fix is a **hosted-schema deploy** (`sqitch deploy` of the missing chain
on `sig-pg`) — a production DDL migration, outside the signed scope of this
leg (IAM bindings + `export.sh` actions only). **STOP** — recorded, not
improvised.

**Resume path (operator / next leg):** deploy the missing sqitch chain to the
hosted spine under its own authorization, then `export.sh --apply run`
(the job is `Ready=True` on `export-c7a2b53edf7e`/`bddfef084d…`, IAM now
declared-synced) → `fetch` → fresh `cut` → `build → sites → stage → verify
--mode S`.

## Blocker 2 — RESOLVED at 17:56Z (the mount's missing `storage.objects.list`)

_(Resolution: the `4c75c68e` "objectUser on the bucket" decision — declaration
amended at `32b2255e`, binding applied + undeclared `objectCreator` removed;
the next execution mounted cleanly. Original record below.)_

`export.sh --apply run` executed `sig-export-dpwsm` (created 16:05:21Z,
failed 16:06:04Z — `failedCount:1`, "exit code: 0 / Unknown error" at the
Cloud Run layer). The execution log shows the gcsfuse volume mount itself
refused before any write:

```
mountWithStorageHandle: fs.NewServer: create file system: SetUpBucket:
BucketHandle: storageLayout call failed: GetStorageLayout for
"projects/_/buckets/zeta-medley-508121-u7-sig-restricted/storageLayout" failed
… rpc error: code = PermissionDenied desc =
sig-export-rt@… does not have storage.objects.list access to the Google Cloud
Storage bucket. Permission 'storage.objects.list' denied on resource
'//storage.googleapis.com/projects/_/buckets/zeta-medley-508121-u7-sig-restricted'
```

**Diagnosis — a declaration gap, not more drift.** `ops/iam_identities.toml`
grants `sig-export-rt` exactly one bucket binding:
`roles/storage.objectCreator` on `sig-restricted` ("create only"). The rebuilt
job's gcsfuse `3.13.0` mount (EnableHns + `GetStorageLayout` handshake +
implicit-dirs listing) needs `storage.objects.list` — which `objectCreator`
does not carry. The declared grant set is insufficient for the job's declared
mount; fixing it is a **declaration amendment** (a fourth binding — e.g.
`roles/storage.objectUser`, or `legacyBucketReader` alongside `objectCreator`
as the `sig-probe-rt` row precedents) plus its own OM-20 go — the
`D-P34.42a-1` precedent routes that call to the operator, never the agent.
Adding any binding beyond the three enumerated in `b4bbae0e` is outside the
signed scope → **STOP**, recorded, not improvised.

(Why the 2026-09-24/27 executions succeeded: not established — either the job
then ran a different runtime identity/posture or an older gcsfuse skipped the
`GetStorageLayout` call. Recorded, not asserted.)

**Resume path (for the operator / next leg):** amend
`ops/iam_identities.toml` so `sig-export-rt` can list+create on the
restricted bucket (operator decision on the declared shape), apply the
binding, then `export.sh --apply run` (job is already `Ready=True` on
`export-c7a2b53edf7e`/`bddfef084d…`) → `fetch` → the release-cut chain with a
fresh `cut`.

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 09:07:20→09:11:41 | Cloud Build `7c43ada1` → image `sig-api:export-1bc1a1298da8` digest `…e9bf33e0` pushed to Artifact Registry | image absent → present |
| 09:13:15 | `gcloud run jobs deploy sig-export` (from `export.sh --apply job`) — **reported failed**, but the job template generation advanced (observedGeneration 6): image `…1cccde1a` → `…e9bf33e0`, `Ready=False`/`SecretsAccessCheckFailed` | see above |
| 09:14:38 | `registry/LOCK` broken via `release cut --apply --break-lock` — fresh lock (gen `1795166125113684`) carried `broke_lock` with the recorded reason verbatim, then released on clean exit | `registry/LOCK` held (verb=stage, 06:48:17Z) → **absent**; break chain survives in the versioned noncurrent generations |
| 09:14:38 | `registry/events/000005-20261120T091438-cut-root.json` inserted (create-if-absent, `sig.release-event/1`, verb=cut, outcome=recorded) | events 000000–000004 → 000000–000005 |
| 15:59:5x | `gcloud projects add-iam-policy-binding` — `roles/cloudsql.client` → `sig-export-rt` (authorized by `b4bbae0e`, declared step 14) | absent → present (etag `BwZgt1WXcN4=`) |
| 16:00:02 | `gcloud storage buckets add-iam-policy-binding …-sig-restricted --condition=None` — `roles/storage.objectCreator` → `sig-export-rt` (step 25; first attempt refused non-interactively on the conditioned policy — `--condition=None` is the verbatim unconditional form) | absent → present (etag `CAU=`) |
| 16:00:02 | `gcloud secrets add-iam-policy-binding sig-pg-password` — `roles/secretmanager.secretAccessor` → `sig-export-rt` (step 29) | absent → present (etag `BwZgt1ZRxd4=`) |
| 16:00:53→16:04:00 | Cloud Build `00f9dc32` → image `sig-api:export-c7a2b53edf7e` digest `…bddfef08` pushed (tag re-derived on the ledger commit's HEAD — the "image" action is idempotent-by-design) | image absent → present |
| 16:04:3x | `gcloud run jobs deploy sig-export` → template on `…@sha256:bddfef084d…`, `Ready=True` | `Ready=False`/`SecretsAccessCheckFailed` → `Ready=True` |
| 16:05:21→16:06:04 | `gcloud run jobs execute sig-export` → execution `sig-export-dpwsm` **failed** at the gcsfuse mount (`storage.objects.list` denied); `exports/national/2026-11-20T160419Z/` left with **zero objects** | execution created → failed; no bucket writes |
| 17:55:5x | declaration commit `32b2255e` — `ops/iam_identities.toml`: `sig-export-rt`/`sig-restricted` `objectCreator`→`objectUser` (cites `4c75c68e`) | declaration amended on `r11/ops-export-live-1` |
| 17:56:05 | `gcloud storage buckets add-iam-policy-binding …-sig-restricted --condition=None` — `roles/storage.objectUser` → `sig-export-rt` | absent → present (etag `CAY=`) |
| 17:56:16 | `gcloud storage buckets remove-iam-policy-binding …-sig-restricted --all` — `roles/storage.objectCreator` → `sig-export-rt` **removed** (declared=live sync) | present → absent (etag `CAc=`) |
| 17:56:21→17:57:06 | `gcloud run jobs execute sig-export` → execution `sig-export-qjhg8`: mount OK, secret OK, Cloud SQL OK — **failed** `UndefinedColumn: ce.bound_at` (exit 1); `exports/national/2026-11-20T175621Z/` left with **zero objects** | execution created → failed; no bucket writes |

Unchanged: `registry/labels.json` (stranded `sig-2026-11-20.1` allocation
untouched), `registry/catalog.json` (`{"publications":[]}`), `staged/` (262
objects: the prior leg's partial `r/p-846b3554…/` + the two 2026-11-18
fixture `p-0bf8b897` rows — resume-safe), `registry/latest.json` still
absent. Nothing published, activated, or promoted.

## Resumed leg 3 — 2026-11-24T14:10Z→17:16Z (schema gap closed by OPS-SPINE-SCHEMA-DEPLOY)

Under the same signed gos (`d3c72f51` "Run the export" + `99018e1b`
"Authorize now"), after `OPS-SPINE-SCHEMA-DEPLOY` attempt 2 landed all 42
pending sqitch changes on `sig-pg` (plan tip `closed_vocabulary`,
`bound_at` verified present, 14:06Z — see that ledger). Window check:
14:10Z→17:16Z — outside AR-3 (03:00Z→06:30Z) and the Dec freeze.

| leg | verdict |
|---|---|
| `export.sh --check all` | plan OK — image tag derives from HEAD `4741345e` → `sig-api:export-4741345e4fb3` (rebuild dictated: deployed `export-c7a2b53edf7e` predated the merge-forward) |
| `export.sh --apply image` | **DONE** — digest `sha256:7dd590e8dfcc7b3f55ce4dea01cd8b05896a22c7f99ac9914d1fb1a7055db185`, Cloud Build `d49b581f-8253-49da-9b25-6d3d5f466d9f` SUCCESS 3m2s (`21-image.txt`) |
| `export.sh --apply job` (4cpu/16Gi — declared shape) | **DONE** — `sig-export` on `…@sha256:7dd590e8`, `Ready=True` gen 8 (`22-job.txt`, `23-job-poststate.txt`) |
| `export.sh --apply run` ×5 | **all five executions failed — see Blocker 4.** `sig-export-rtzrn` OOM@16Gi; `sig-export-gl4bd` cancelled (doomed: work_mem-bound ~74min/query × 6 `{EFFECTIVE}` queries vs 4h timeout); `sig-export-k286p` OOM@32Gi; `sig-export-ljvft` refused exit 4 (host-clock check HTTP 429, transient → honoured + retried); `sig-export-kftm6` OOM@32Gi. **Zero objects under any prefix** (`43-prefix-poststate.txt`). |
| `export.sh --apply fetch` | **not run** — no fresh `exports/national/<as-of>/` exists. |
| release re-cut (cut → build → sites → stage → verify --mode S) | **not run** — the DOA blocker on the stale `2026-09-27` export stands; re-cutting over it would only re-produce `p-846b3554…`. Registry untouched this leg: `registry/LOCK` absent, `labels.json` byte-identical, no new events. |

### Sequence detail

1. **14:13:56Z `sig-export-rtzrn` (4cpu/16Gi)** — mount OK, secret fetch OK,
   Cloud SQL connect OK, **`bound_at` read fine** (Blocker 3 fully cleared:
   it survived ~6 min inside `fetch_shaping_raw` vs the instant
   `UndefinedColumn` crash of `qjhg8`) — then **signal 9 / "The configured
   memory limit was reached"** at 8m17s elapsed during the fetch
   (`26-run-poststate.txt`, `27-run-logs.txt`).
2. **Spec deviation 1 (recorded):** probe `--memory 32Gi` at 4cpu REFUSED
   verbatim — `For 4.0 CPU, memory must be between 2Gi and 16Gi inclusive`
   (`36-job-probe-64gi.txt` also records a 16cpu/64Gi probe refused: cpu
   must be ∈ {.08–1,1,2,4,6,8}). `ops/gcp/export.sh` parameterised:
   `SIG_EXPORT_JOB_CPU`/`SIG_EXPORT_JOB_MEMORY` (defaults = declared 4/16).
   Redeployed **8cpu/32Gi** — the platform maximum (gen 9, `28-job-32gi.txt`,
   `29-job-8cpu-32gi.txt`).
3. **14:24:05Z `sig-export-gl4bd` (8cpu/32Gi)** — the fetch ran but every
   `{EFFECTIVE}` query re-computes the `claim_source` CTE (`DISTINCT ON`
   over **4,783,704** `claim_evidence` rows) at `work_mem=4096kB`:
   `shaping_claims` alone ran ~74 min spilling ~63 GB temp on
   `db-custom-2-7680` (read-only `pg_stat_activity`/`pg_settings` probe via
   cloud-sql-proxy + `sig` read session — `PGPASSWORD` env-only). Six
   `{EFFECTIVE}` queries × ~60–75 min > the 4h task timeout ⇒ **doomed —
   cancelled** 15:41Z (`33-cancel-gl4bd.txt`). Spine size measured at the
   same probe: 2,928,254 claims / 4,783,704 claim_evidence / 260,819
   entities / 41 rights_decision.
4. **Spec deviation 2 (recorded):** `export.sh` gained
   `SIG_EXPORT_RUN_ENV` → per-execution `--update-env-vars`
   (`PGOPTIONS=--work_mem=2GB` honored by libpq — verified `SHOW work_mem`
   = `2048MB` through the proxy before use).
5. **15:41:38Z `sig-export-k286p` (32Gi + work_mem=2GB)** — fetch phase
   completed in ~20 min (heavy queries down to seconds–minutes; session
   `idle in transaction` by ~16:00Z) — then **OOM at 32 GiB ~28 min into
   the in-memory `build_shaped_dataset`** (`35-run-poststate.txt`).
6. **16:30:51Z `sig-export-ljvft`** — refused **exit 4** at the §3.3
   host-clock guard: remote `Date` header fetch got HTTP 429 from
   google.com (transient egress rate-limit; verbatim in
   `39-run-poststate.txt`). Honoured — no `--skip-host-clock-check`;
   retried 16:35Z.
7. **16:35:36Z `sig-export-kftm6`** (32Gi + work_mem=2GB +
   `PYTHONMALLOC=malloc` + `MALLOC_TRIM_THRESHOLD_=65536`) — fetch ~20
   min, **OOM at 32 GiB ~21 min into shaping** (`42-run-poststate.txt`).

## Blocker 4 — CURRENT (export in-memory build exceeds the platform ceiling)

`sig-exports build --from-spine` holds the whole shaped dataset in RAM by
design (`fetch_shaping_raw` fetchalls every query; `build_shaped_dataset`
builds the shaped graph over them — the P30.3 design assumed "several GB"
for ~2.3M claims). The settled spine is now **2,928,254 claims /
4,783,704 claim_evidence rows** (+ typed-assertion-era columns: bound_at,
sightings, lineage) — measured, the in-memory build needs **materially
more than 32 GiB** (two OOMs at the 32 GiB task limit: ~28 min and ~21
min into shaping; allocator tuning `PYTHONMALLOC=malloc` +
`MALLOC_TRIM_THRESHOLD_` did not save enough).

Every declared heavyweight substrate is a **Cloud Run job** (`export.sh`
4cpu/16Gi, `materialize.sh` 4cpu/16Gi/24h, `exec-host.sh` ephemeral job) —
the platform caps a job task at **8 vCPU / 32 GiB** (both bounds refused
verbatim by the API: `16Gi` max at 4cpu; cpu ∈ {.08–1,1,2,4,6,8}). The
local host (36 GB RAM) is marginal-to-insufficient and outside the
declared path regardless.

**This is a substrate/engineering decision, not an IAM gap — STOP,
recorded, not improvised.** Resume paths for the operator:

- a bigger declared substrate (e.g. a GCE exec-host leg with ≥48–64 GiB —
  a new declaration + its own OM-20 go), or
- an engineering ticket: a streaming/chunked export build (release the
  `raw` result sets as they are consumed instead of holding
  fetchall+dataset simultaneously), or
- operator-run export on a ≥64 GB host over cloud-sql-proxy writing to a
  staging dir, then a bucket upload leg (deviates from the declared
  in-job path — an operator call).

End state: `sig-export` job **restored to the declared shape**
(4cpu/16Gi, `Ready=True`, gen 10) on the fresh pinned digest
`…@sha256:7dd590e8` — `SIG_EXPORT_JOB_CPU`/`SIG_EXPORT_JOB_MEMORY`/
`SIG_EXPORT_RUN_ENV` exist for the next attempt (committed defaults keep
the declared shape). All five execution prefixes verified **empty** — no
bucket residue. Registry unchanged (`LOCK` absent, `labels.json`
untouched, no events this leg). `D-P37.65a-1` remains **OPEN**.

## Mutations performed this leg (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 14:10:36→14:13:38 | Cloud Build `d49b581f` → image `sig-api:export-4741345e4fb3` digest `…7dd590e8` pushed | tag absent → present |
| 14:1x | `gcloud run jobs deploy sig-export` (4cpu/16Gi) on `…@sha256:7dd590e8` | template `…bddfef08` → `…7dd590e8`, `Ready=True` gen 8 |
| 14:14→14:22 | `gcloud run jobs execute` → `sig-export-rtzrn` **failed** (OOM@16Gi, signal 9) | execution created → failed; zero objects |
| ~14:2x | probe deploy `--memory 32Gi`@4cpu | **refused** (recorded verbatim) |
| ~14:2x | probe deploy `--cpu 16 --memory 64Gi` | **refused** (recorded verbatim) |
| 14:2x | `gcloud run jobs deploy` 8cpu/32Gi on `…@sha256:7dd590e8` | limits 4/16Gi → **8/32Gi** gen 9 |
| 14:24→15:41 | `gcloud run jobs execute` → `sig-export-gl4bd` → `gcloud run jobs executions cancel --quiet` | execution created → **Cancelled** (doomed ETA > 4h timeout); zero objects |
| ~14:3x→17:1x | read-only probes only: cloud-sql-proxy on :15444 + `psycopg` `sig` session (`pg_stat_activity`, `pg_settings`, table counts, `SHOW work_mem`); PGPASSWORD env-only; proxy stopped | no DB mutation |
| 15:41→16:28 | `gcloud run jobs execute` (+`PGOPTIONS=--work_mem=2GB`) → `sig-export-k286p` **failed** (OOM@32Gi in shaping) | execution created → failed; zero objects |
| 16:30→16:32 | `gcloud run jobs execute` → `sig-export-ljvft` **refused exit 4** (host-clock 429) | execution created → refused before any read; zero objects |
| 16:35→17:16 | `gcloud run jobs execute` (work_mem + malloc tuning) → `sig-export-kftm6` **failed** (OOM@32Gi in shaping) | execution created → failed; zero objects |
| 17:2x | `gcloud run jobs deploy` 4cpu/16Gi on `…@sha256:7dd590e8` | limits 8/32Gi → **4/16Gi restored** gen 10, `Ready=True` |

Script delta this leg (on this branch, agent-authored, defaults preserve
the declared shape): `ops/gcp/export.sh` gained `SIG_EXPORT_JOB_CPU`,
`SIG_EXPORT_JOB_MEMORY`, `SIG_EXPORT_RUN_ENV` parameterisation + comments.

## Standing constraint carried forward (unchanged from P37.65a-live-1)

`release stage` is strictly serial (`store.insert` + `lock.refresh()` per
object, `release_pipeline.py:826-839`); measured ~0.37 objects/s on the prior
leg ⇒ ~14.7 days for ~475k objects, longer with the `v/`/`s/` trees. A stage
was not started — it exceeds any sane session bound. When the export unblocks
and the re-cut reaches `stage`, the same bound applies unless the stage path
gains a batch/parallel mode.
