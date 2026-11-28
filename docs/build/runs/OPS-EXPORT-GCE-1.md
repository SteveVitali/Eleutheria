# OPS-EXPORT-GCE-1 — one-off GCE exec leg for the national export

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (the fresh-export half of `D-P37.65a-1`); continuation of
  `docs/build/runs/OPS-EXPORT-LIVE-1.md` §leg-3 (Blocker 4 — Cloud Run job
  ceiling 8vCPU/32GiB, five OOM/refused executions, zero objects).
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-gce-1` @ `8bb00c9d` (worktree
  `/private/tmp/sig-export-gce`).
- **Authorization:** operator-signed commit `8bb00c9d` (GATE DECISIONS
  `2026-11-24T18:00Z`, "GCE exec leg (fastest)") — a ONE-OFF export execution
  on a ≥64 GiB GCE host under operator ADC, torn down after the run; then
  `export.sh --apply fetch` + the `D-P37.65a-1` re-cut under the existing
  signed gos (`d3c72f51` "Run the export" / `99018e1b` "Authorize now").
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`, region/zone
  `us-central1`/`us-central1-a`, ADC `14stevevitali@gmail.com` (roles/owner);
  every gcloud call passed `--project` explicitly.
- **Window:** run 2026-11-24T19:13Z→20:51Z — outside AR-3 (03:00Z→06:30Z);
  the Dec monthly freeze does not apply. No window refusal hit.
- **Evidence:** `docs/build/logs/ops-export-gce-1/` (the gitignored subtree;
  `run-export-on-vm.sh` is the exact executed driver kept beside the captures
  — it carries no secret; the VM-recreate + run recipe is restated in
  "Resume path" below).

## Verdict

| leg | verdict |
|---|---|
| prestate `instances list` | 0 items |
| VM create `sig-export-gce-1` | **DONE** — `e2-highmem-8` (8 vCPU / 64,313 MiB observed) + 32 GiB swap safety net, Debian 12, 200 GB pd-balanced, ephemeral external IP (SSH only), SA `sig-export-rt` (scopes: cloud-platform) |
| image | **DONE** — pinned `sig-api@sha256:7dd590e8dfcc7b3f55ce4dea01cd8b05896a22c7f99ac9914d1fb1a7055db185` (== `export-4741345e4fb3`, the same build the Cloud Run job runs). `sig-export-rt` holds **no** artifactregistry grant (declared posture — Cloud Run's service agent pulls, never the job SA), so the image was pulled under operator ADC locally and transferred `docker save \| ssh docker load`; digest→config chain proven (`manifest 7dd590e8…` → config `300aafc5c6a8…` == VM image id, `06-image-id-chain.txt`) |
| cloud-sql-proxy + secret + DB | **OK** — proxy v2.18.3 on `127.0.0.1:5432` under the VM SA; `sig-pg-password` fetched via Secret Manager REST (env-only, 40-byte payload); `sig` read session connected |
| `python -m exports build --from-spine` (as-of `2026-11-24T19:19:52Z` → `exports/national/2026-11-24T191952Z/`) | **REFUSED — exit 1 at the licence gate** after ~80.5 min (fetch ~30 min; in-memory build plateaued **46.39 GiB container** / host `mem_used` peak 48,752 MB; swap untouched): `LicenseIncompatibilityError: source 'decp_fr' declares licence 'LicenceOuverte-2.0', which is not in the compartment registry (licenses.toml)` — see Blocker 5. **Zero files, zero objects** — the refusal lands before any write. |
| upload → `gs://…-sig-restricted/exports/national/<as-of>/` | **not run** — no export output exists; prefix verified absent |
| `export.sh --apply fetch` | **not run** — no fresh `exports/national/<as-of>/` exists |
| re-cut (cut → build → sites → stage → `verify --mode S`) | **not run** — same upstream blocker; registry untouched |
| teardown | **DONE** — `sig-export-gce-1` deleted 20:50:5xZ; poststate `instances list` = 0 items; boot disk deleted with the instance; nothing else detached |
| `sig-export` Cloud Run job | **unchanged** — gen 10, 4cpu/16Gi, `Ready=True`, digest `…7dd590e8` (prestate == poststate verbatim) |

`D-P37.65a-1` remains **OPEN**.

## What this leg measured (the substrate question is ANSWERED)

The in-memory `sig-exports build --from-spine` over the settled spine
(2,928,254 claims / 4,783,704 claim_evidence / 260,819 entities, per leg-3's
probe) peaks at **~46.4–47 GiB** resident — the fetch result sets plus the
shaped dataset held simultaneously, exactly the all-in-memory design the
P30.3 estimate ("several GB") under-predicted. Both 32 GiB Cloud Run OOMs
were ~10–15 GiB short, in the shaping phase. **An e2-highmem-8 (64 GiB)
substrate is sufficient** — the failure mode moves cleanly off memory: the
build ran the full fetch + shape to completion and failed on the licence
gate. `PGOPTIONS=--work_mem=2GB` + `PYTHONMALLOC=malloc` +
`MALLOC_TRIM_THRESHOLD_=65536` carried from leg-3 verbatim; the heavy
`claim_source` DISTINCT-ON CTE ran without the ~63 GB temp spill.

Wall-clock: docker run `19:19:56Z → 20:40:30Z` (~80.6 min) — fetch ≈30 min,
shape+labels ≈50 min to the refusal. A clean re-run would continue past the
label registry into emit/upload — same order of duration.

## Blocker 5 — CURRENT (hosted spine carries a pre-normalisation licence id)

`decp_fr`'s **effective** `rights_record` on the hosted spine
(`rights_decision` `01a0ca5b…` → `rights_id` `01a0ca59…`, HG-03 decision
2026-09-22) carries `spdx_expression='LicenceOuverte-2.0'` — the recorded
identifier defect ADR-194/P34.21a already diagnosed. The compartment
registry (`policy/data/licenses.toml`) names the canonical `etalab-2.0`
only; `compute_export_license` fails **closed** — a licence absent from the
registry is a hard refusal, correctly honoured (no workaround exists or was
attempted; there is no skip/exclude flag by design).

The designed correction is **OPEN deferral `D-P34.21a-1`** — the L1 hosted
backfill `sig-db attribution-corrections --dsn <sig-pg> --corrections
docs/build/reports/rights/p34_21a_corrections.json --apply` (INSERT-only
`rights_record` + `rights_decision` rows; the export's
`COALESCE(ld.rights_id, c.rights_id)` effective-rights resolution then
returns `etalab-2.0`). **Its S5-3 pre-authorisation expired at GATE-G4**
(both G4 and G5 have sat — LEDGER `S5-3 listing expired GATE-G4`) and the
row's own trigger needs `live:P34.3`, an AR-2 backup + pre-state capture,
and a `probe-run/1` ≤ 24 h — a fresh verbatim go plus its own leg's
pre-states. That is a production spine mutation outside this leg's signed
scope → **STOP, recorded, not improvised.** Same root class hits the Cloud
Run job identically — the licence gate binds in `build`, not the substrate.

**Resume path (operator / next leg):** (1) operator go for the
`D-P34.21a-1` apply (S5-3 expired — needs verbatim re-authorisation) with
its recorded pre-states; (2) re-stand a VM — the whole recipe is recorded
(`run-export-on-vm.sh`; `gcloud compute instances create sig-export-gce-1
--machine-type e2-highmem-8 …`; image already in AR under
`export-4741345e4fb3`/`7dd590e8` — transfer path in `04–06-*.txt`, ~5 min);
(3) same docker run → `gcloud storage rsync` `/export-out` up →
`export.sh --apply fetch` (SIG_EXPORT_AS_OF set) → re-cut per `99018e1b`.

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 19:13:5x | `gcloud compute instances create sig-export-gce-1` (e2-highmem-8, debian-12, 200 GB, SA `sig-export-rt`, scopes cloud-platform, label `purpose=sig-export-gce-1`) | 0 instances → RUNNING (`02-create.txt`, `03-poststate-instances.txt`) |
| 19:16→19:2x | VM setup (no GCP mutation): `docker.io` + `jq` apt; `cloud-sql-proxy` v2.18.3 binary; 32 GiB swapfile | — |
| 19:15→19:20 | image pulled locally under operator ADC; `docker save` → ssh `docker load` → tagged `sig-api-export:pinned-7dd590e8` | image absent on VM → present (id `300aafc5c6a8…`) |
| 19:19:55 | `cloud-sql-proxy` up on `127.0.0.1:5432` (VM SA via metadata) | — |
| 19:19:56→20:40:30 | `docker run sig-export-build` — `python -m exports build --from-spine --dsn postgresql://sig:…@127.0.0.1:5432/sig --as-of 2026-11-24T19:19:52Z --environment production --out /out/exports/national/2026-11-24T191952Z` | container created → **refused rc=1** (`LicenseIncompatibilityError`, `decp_fr`); 0 files local, 0 objects remote |
| 20:4x | read-only spine probes (`rights_record`/`rights_decision` columns + decp_fr rows; `SET default_transaction_read_only=on`, password env-only) | no DB mutation |
| 20:50:5x | `gcloud compute instances delete sig-export-gce-1` | RUNNING → **absent**; `instances list` = 0 items |

Unchanged: `sig-export` job (gen 10 declared shape), `registry/`
(`latest.json` absent; no new events; `labels.json` untouched — not read
this leg, nothing wrote it), no firewall/IAM/bucket-policy change, no
authorized-networks change (the proxy path needed none — `sig-pg` is public
IP + proxy auth).

## Notes for the record

- **Executing identity:** the VM ran as `sig-export-rt` (its three declared
  bindings — `roles/cloudsql.client`, `secretAccessor` on `sig-pg-password`,
  `storage.objectUser` on `…-sig-restricted` — were all exercised green).
  `iam.serviceAccountUser` was permitted under the operator ADC (owner).
  The **image pull** alone used operator ADC transitively (the job SA holds
  no artifactregistry grant by declaration); recorded per the leg's
  instruction. No IAM change was made.
- The first launch attempt (19:19:13Z) self-refused on a script defect
  (`swapon`/`/var/log` write paths as the unprivileged user) **before** the
  proxy or DB opened — driver fixed (`/tmp` paths, `sudo swapon`), same
  command shape; both attempts' evidence kept (`07-asof.txt`,
  `08-asof-retry.txt`).
- `D-P37.65a-1` chain unchanged: the stale `2026-09-27` export is still the
  newest `exports/national/` prefix; `web/evaluation.json` presence was
  **not** verified (nothing to verify — no fresh export).
- Carry-forward from OPS-EXPORT-LIVE-1: the stage serialization bound
  (~0.37 obj/s ⇒ ~14.7 days for ~475k objects) still stands for the re-cut's
  `stage` step whenever an export does land.
