# OPS-EXPORT-GCE-2 — one-off GCE exec leg for the national export (attempt 2)

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (the fresh-export half of `D-P37.65a-1`); attempt 2 of
  `docs/build/runs/OPS-EXPORT-GCE-1.md` — identical recipe, corrected spine.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-gce-2` forked at `6a9f512a`
  (attempt-1 tip; worktree `/tmp/sig-export-gce2`).
- **Authorization:** operator-signed commit `8bb00c9d` (GATE DECISIONS
  `2026-11-24T18:00Z`, "Export substrate — operator decision: one-off GCE
  exec leg >=64 GiB") — a ONE-OFF export execution on a >=64 GiB GCE host
  under operator ADC, torn down after the run.
- **Blocker-5 disposition:** attempt 1 refused at
  `policy.licensing.compute_export_license` on `decp_fr`'s pre-ADR-194
  `LicenceOuverte-2.0`. `D-P34.21a-1` is **DONE** 2026-11-24 (run ledger
  `runs/P34.21a-live-3.md`, PR #556): the INSERT-only rights backfill landed
  on the hosted spine (`n_tup_upd`/`n_tup_del` +0) and `decp_fr`'s effective
  record now resolves `etalab-2.0`.
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`, region/zone
  `us-central1`/`us-central1-a`, ADC `14stevevitali@gmail.com` (roles/owner);
  every gcloud call passed `--project` explicitly.
- **Window:** run 2026-11-24T23:40Z→2026-11-25T01:13Z — outside AR-3
  (03:00Z→06:30Z); the Dec monthly freeze does not apply. No window refusal.
- **Evidence:** `docs/build/logs/ops-export-gce-2/` (the gitignored subtree;
  `run-export-on-vm.sh` + `probe-rights.sh` are the exact executed drivers,
  kept beside the captures — no secrets).

## Verdict

| leg | verdict |
|---|---|
| prestate `instances list` | 0 items (`01-prestate.txt`) |
| `sig-export` Cloud Run job prestate | gen 10, 4cpu/16Gi, `Ready=True`, digest `…7dd590e8` (`00-job-prestate.txt`) |
| VM create `sig-export-gce-2` | **DONE** — `e2-highmem-8` (8 vCPU / 64,313 MiB observed) + 32 GiB swap safety net, Debian 12, 200 GB pd-balanced, SA `sig-export-rt` (scopes: cloud-platform), external IP 136.113.74.12 (`02-create.txt`, `03-poststate-instances.txt`) |
| image | **DONE** — same pinned `sig-api@sha256:7dd590e8dfcc7b3f55ce4dea01cd8b05896a22c7f99ac9914d1fb1a7055db185` pulled under operator ADC, transferred `docker save \| ssh docker load`; digest→config chain proven: manifest `7dd590e8…` → config/image-id `300aafc5c6a8…` == VM image id, tagged `sig-api-export:pinned-7dd590e8` (`04-image-pull-local.txt`, `05-image-transfer.txt`, `06-image-id-chain.txt`) |
| cloud-sql-proxy + secret + DB | **OK** — proxy v2.18.3 on `127.0.0.1:5432` under the VM SA; `sig-pg-password` fetched via Secret Manager REST (env-only) |
| licence-gate pre-flight | **PASS** — `probe-rights.sh` resolved every source's effective rights record through the same `latest_decision` + `claim_source` CTEs the export's `label_facts` uses and ran the real `compute_export_license`/`export_refusal_reason` on each distinct record (232 rows): `decp_fr` effective `etalab-2.0` over 60,319 claims; every effective record resolves inside the registry (`07-rights-probe.txt`) |
| `python -m exports build --from-spine` (as-of `2026-11-24T23:45:33Z` → `exports/national/2026-11-24T234533Z/`) | **REFUSED — exit 1 at `check_unique_labels` (SIG-UI-111)** after ~81.1 min (docker run 23:45:41Z → 01:06:45Z). The licence gate **passed** (`_label_registry` line 5918 completed — Blocker 5 is gone); the refusal landed one step later at line 5928 — see Blocker 6. Memory plateaued **47.35 GiB container** / host `mem_used` peak 49,645 MB; swap untouched. **Zero files, zero objects.** |
| upload → `gs://…-sig-restricted/exports/national/<as-of>/` | **not run** — no export output exists; prefix verified absent (`12-bucket-poststate.txt`) |
| `export.sh --apply fetch` / `D-P37.65a-1` re-cut | **not run** — no fresh export; `web/evaluation.json` presence unverifiable (nothing produced) |
| teardown | **DONE** — `sig-export-gce-2` deleted 01:12:48Z; poststate `instances list` = 0 items; boot disk deleted with the instance; no orphaned `sig-export-gce*` disks (`13-teardown.txt`, `14-job-poststate.txt`) |
| `sig-export` Cloud Run job poststate | **unchanged** — gen 10, `Ready=True` (prestate == poststate) |

`D-P37.65a-1` remains **OPEN**; this leg ended at an honest STOP — no export
exists to rsync, fetch, or re-cut.

## What this leg measured / proved

1. **The licence gate is UNBLOCKED end-to-end.** Attempt 1 refused at
   `spine_export.py:5918` inside `_label_registry` → `compute_export_license`
   on `decp_fr LicenceOuverte-2.0`. This run cleared that exact call —
   `decp_fr` effective `etalab-2.0` (pre-flight + the build running past
   line 5918 to line 5928 prove it). `D-P34.21a-1`'s INSERT-only backfill is
   confirmed working in the real export path, not just on a probe.
2. **Substrate re-confirmed:** e2-highmem-8 suffices; peak 47.35 GiB
   container / 49,645 MB host, swap 0 — ~1 GiB above attempt 1's 46.39 GiB
   plateau (same queries, slightly different as-of bound).
3. **Pre-flight probe is now a reusable recipe** — a ~15 s read-only check
   that runs the real licence gate over every effective record, before
   spending the ~80 min fetch+shape.

## Blocker 6 — CURRENT (SIG-UI-111 duplicate display label)

`check_unique_labels` (`policy/slug_history.py:219`, invoked at
`spine_export.py:5928`) refused the build:

```
ValueError: SIG-UI-111: duplicate display label
'surveillance camera in iso3166-2:US-WA #tyvj' within kind 'site'
(entities 01a0b0d1-462b-70bf-b40e-880db02b6161 and 01a0b0e6-03bb-7486-a807-47e73838e324)
```

What the read-only probe found (`11-dup-label-probe.txt`):

- Both are `entity_type='deployment'` subjects of source **`dot_511_wa`**:
  `traffic_camera:dot_511_wa:wa_wsdot_travel_cameras:1180`
  ("SR 167 at MP 21.3: 84th Ave S", 47.3987,-122.2275) and
  `…:9957` ("SR 16 at MP 7.5: TNB EB East Anchorage", 47.2642,-122.5462) —
  **two genuinely distinct cameras**, created 2026-09-17 ~23 min apart.
- Both emitted the same label from the **derived** candidate
  `{tech_words} camera in {place}` = "surveillance camera in
  iso3166-2:US-WA" — i.e. `field_text("camera_name")` yielded nothing usable
  for either entity even though tier-0 `camera_name` claims exist on both.
  Whether the claims failed `label_facts`' `{PUB_CLAIM_GATE}`
  (`claim_eligible_sql` — claim/entity dispositions) or never populated
  `fields` is the first thing the owning ticket must determine.
- The §3.4 disambiguation chain then failed at its last step: place_hint
  identical (same jurisdiction), source_hint identical (same source), and
  `#{hash4(entity_id)}` — documented as "always can" separate a group —
  **collided**: `entity_hash(01a0b0d1…)[:4]` = `tyvj` and
  `entity_hash(01a0b0e6…)[:4]` = `tyvj` (verified independently —
  `tyvjdr9` vs `tyvjwn5`; a sha256 top-20-bit prefix collision, statistically
  expected at ~260k-entity scale: hash4 is a 20-bit space, the birthday
  bound predicts tens of thousands of colliding pairs).
- `check_unique_labels` correctly fails closed; `resolve_disambiguators`'s
  guarantee does not hold at real scale. The fix belongs to the
  label/slug machinery (e.g. a hash-length extension loop like
  `slug_history.resolve_hash_collisions` already performs for URLs, or a
  longer display tie-break) plus the upstream question of why the
  `camera_name` candidates lost — **recorded for the corrections chain, not
  improvised.**

**Resume path (operator / next leg):** same one-shot recipe —
`run-export-on-vm.sh` + `probe-rights.sh` ride in this leg's evidence dir;
image transfer ~5 min; the whole VM stands in ~10 min. Blocker 6 needs a
code/labeling decision first (the display-label tie-break is not a spine
data fix — it is in `policy/labels.py` + `policy/slug_history.py`).

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 23:40:46 | `gcloud compute instances create sig-export-gce-2` (e2-highmem-8, debian-12, 200 GB, SA `sig-export-rt`, scopes cloud-platform, label `purpose=sig-export-gce-2`) | 0 instances → RUNNING (`02-create.txt`, `03-poststate-instances.txt`) |
| 23:41→23:42 | VM setup (no GCP mutation): `docker.io` + `jq` apt; `cloud-sql-proxy` v2.18.3 (`05-vm-setup.txt`) | — |
| 23:41→23:42 | image pulled locally under operator ADC; `docker save` → ssh `docker load` → tagged `sig-api-export:pinned-7dd590e8` | image absent on VM → present (id `300aafc5c6a8…`) |
| 23:44:32→23:44:49 | read-only licence-gate pre-flight probe (`SET default_transaction_read_only=on`, password env-only) | no DB mutation |
| 23:45:41→01:06:45 | `docker run sig-export-build` — `python -m exports build --from-spine --dsn postgresql://sig:…@127.0.0.1:5432/sig --as-of 2026-11-24T23:45:33Z --environment production --out /out/exports/national/2026-11-24T234533Z` (`PGOPTIONS=--work_mem=2GB`, `PYTHONMALLOC=malloc`, `MALLOC_TRIM_THRESHOLD_=65536`) | container created → **refused rc=1** (`SIG-UI-111` at `check_unique_labels`); 0 files local, 0 objects remote |
| ~01:08→01:11 | read-only duplicate-label probes (entity/identifier/claims reads, password env-only) | no DB mutation |
| 01:12:48 | `gcloud compute instances delete sig-export-gce-2` | RUNNING → **absent**; `instances list` = 0 items; 0 orphan disks |

Unchanged: `sig-export` job (gen 10 declared shape, `Ready`), bucket policy,
IAM, firewall, authorized-networks (proxy path needed none), `registry/`
(latest.json untouched — no export produced).

## Notes for the record

- **Executing identity:** the VM ran as `sig-export-rt` (its three declared
  bindings — `roles/cloudsql.client`, `secretAccessor` on `sig-pg-password`,
  `storage.objectUser` on `…-sig-restricted`). `iam.serviceAccountUser`
  permitted under the operator ADC (owner). The image pull alone used
  operator ADC transitively (the job SA holds no artifactregistry grant by
  declaration — attempt-1 posture repeated). No IAM change made.
- Pre-flight probe v1 mis-joined `claim_source` as a table (it is the
  `db.occurrences.claim_source_cte` CTE); v2 composes the same CTE verbatim.
  Read-only both times.
- Attempt-1 carry-forwards unchanged: same pinned image/digest, same env
  knobs, same host shape, same failure-before-write posture (0 files, 0
  objects — the refusals land before any emit).
- Stage-serialization bound (~0.37 obj/s ⇒ ~14.7 days for ~475k objects)
  still stands for the re-cut's `stage` step whenever an export lands.
