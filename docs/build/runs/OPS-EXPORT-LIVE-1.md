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
| `export.sh --apply job` | **REFUSED (IAM)** — see below. The template still updated to the new pinned digest but the job is `Ready=False` (`SecretsAccessCheckFailed`). |
| `export.sh --apply run` / `fetch` | **not run — blocked upstream.** No fresh `exports/national/<as-of>/` exists. |
| cleanup: break stale `registry/LOCK` | **DONE** — via `release cut --apply --break-lock "<reason>"`; reason recorded into the versioned lock chain; `registry/LOCK` absent poststate. |
| stranded label `sig-2026-11-20.1` | **left recorded-not-deleted** — `labels.json` byte-identical pre/post. |
| `release cut` | **journaled** — event `registry/events/000005-20261120T091438-cut-root.json`, T0 `2026-11-20T09:14:38Z`, `host_clock.ok=true` (skew 0.214 s). The event's declared legs (`restore-point`, `materialize`, `export run`, `fetch`) did **not** run — the export leg is blocked; a follow-on attempt re-cuts (journal is append-only). |
| `release build → sites → stage → verify --mode S` | **not run** — no fresh export exists; re-running `build` over the stale `2026-09-27` export would only re-produce the dead-on-arrival candidate. No mutation made. |

`D-P37.65a-1` remains **OPEN**.

## The blocker (verbatim refuse + diagnosis)

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
shape, but the job is `Ready=False`, `reason=SecretsAccessCheckFailed`.

Wider drift found (all read-only probes, no mutation): `sig-export-rt` holds
**none** of its declared bindings:

| declared (ops/iam_identities.toml / `sig-ops iam plan --leg jobs`) | live |
|---|---|
| step 14: `roles/cloudsql.client` (project) | **absent** — the only `-rt` project grant is `sig-api-rt`'s |
| step 25: `roles/storage.objectCreator` on `…-sig-restricted` | **absent** — bucket policy carries only legacy + the conditioned `sig-release-rt` viewer on `exports/` |
| step 29: `roles/secretmanager.secretAccessor` on `sig-pg-password` (`consumers` line 443) | **absent** — the secret grants only `default-compute` + `sig-api-rt` |

So the deploy refusal is the **first** of three denials the run leg would hit
(secret fetch at container start; then Cloud SQL socket connect; then the
`exports/national/<as-of>/` create). The declared state is already correct —
this is live-vs-declared **drift**, i.e. the `iam-job-identities.sh` bindings
block for the job-class SAs is unapplied or was reverted. Per the run rules —
*the export refusing on missing IAM/secrets outside the enumerated actions →
STOP, do not broaden scope* — no binding was added.

**Resume path (for the operator / next leg):** restore the declared bindings
via the windowed `ops/gcp/iam-job-identities.sh` leg (or the verbatim
`gcloud secrets add-iam-policy-binding sig-pg-password --member=serviceAccount:sig-export-rt@… --role=roles/secretmanager.secretAccessor`
plus steps 14 + 25), then re-run `export.sh --apply job` (idempotent re-pin —
the template already carries `export-1bc1a1298da8` but is `Ready=False`),
`run`, `fetch`, then the release-cut chain with a fresh `cut` (T0 must share
the export's day for a same-day label).

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 09:07:20→09:11:41 | Cloud Build `7c43ada1` → image `sig-api:export-1bc1a1298da8` digest `…e9bf33e0` pushed to Artifact Registry | image absent → present |
| 09:13:15 | `gcloud run jobs deploy sig-export` (from `export.sh --apply job`) — **reported failed**, but the job template generation advanced (observedGeneration 6): image `…1cccde1a` → `…e9bf33e0`, `Ready=False`/`SecretsAccessCheckFailed` | see above |
| 09:14:38 | `registry/LOCK` broken via `release cut --apply --break-lock` — fresh lock (gen `1795166125113684`) carried `broke_lock` with the recorded reason verbatim, then released on clean exit | `registry/LOCK` held (verb=stage, 06:48:17Z) → **absent**; break chain survives in the versioned noncurrent generations |
| 09:14:38 | `registry/events/000005-20261120T091438-cut-root.json` inserted (create-if-absent, `sig.release-event/1`, verb=cut, outcome=recorded) | events 000000–000004 → 000000–000005 |

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
