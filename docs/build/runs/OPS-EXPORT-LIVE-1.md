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

## Blocker 2 — CURRENT (declaration gap: the mount needs `storage.objects.list`)

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

Unchanged: `registry/labels.json` (stranded `sig-2026-11-20.1` allocation
untouched), `registry/catalog.json` (`{"publications":[]}`), `staged/` (262
objects: the prior leg's partial `r/p-846b3554…/` + the two 2026-11-18
fixture `p-0bf8b897` rows — resume-safe), `registry/latest.json` still
absent. Nothing published, activated, or promoted.

## Standing constraint carried forward (unchanged from P37.65a-live-1)

`release stage` is strictly serial (`store.insert` + `lock.refresh()` per
object, `release_pipeline.py:826-839`); measured ~0.37 objects/s on the prior
leg ⇒ ~14.7 days for ~475k objects, longer with the `v/`/`s/` trees. A stage
was not started — it exceeds any sane session bound. When the export unblocks
and the re-cut reaches `stage`, the same bound applies unless the stage path
gains a batch/parallel mode.
