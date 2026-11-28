# OPS-EXPORT-GCE-4 — one-off GCE exec leg for the national export (attempt 4)

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (the fresh-export half of `D-P37.65a-1`); attempt 4 of
  `docs/build/runs/OPS-EXPORT-GCE-1.md` / `-2` / `-3` — identical recipe,
  image rebuilt at the `r11/ops-export-gce-3` tip.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-gce-4` forked at `49551c43`
  (`r11/ops-export-gce-3` tip; worktree `/tmp/sig-export-gce4`).
  `git merge-base --is-ancestor b5a3b394 49551c43` → true, and
  `git diff b5a3b394..49551c43` is the attempt-3 ledger doc only — the
  image's code content is byte-identical to the `b5a3b394` SIG-UI-111 fix.
- **Authorization:** operator-signed commit `8bb00c9d` (GATE DECISIONS
  `2026-11-24T18:00Z`, "Export substrate — operator decision: one-off GCE
  exec leg >=64 GiB") — a ONE-OFF export execution on a >=64 GiB GCE host
  under operator ADC, torn down after the run. Still current: same leg,
  fourth attempt.
- **Blocker-7 disposition:** attempt 3 refused at `assert_attribution_rows`
  (E2-12 / ADR-194 — three `rights_record` rows with `attribution_text=NULL`,
  34 source/record pairs). `D-E2-12-BACKFILL` is DONE
  (`r11/ops-e212-backfill` tip `9b5bdb35`, PR #560): 34 `rights_decision`
  redirects + 3 corrected `rights_record` rows, INSERT-only, read-back
  green. The image needs **no** e212-branch code — the backfill is
  spine-side data; the export resolves it through the recorded
  `COALESCE(ld.rights_id, c.rights_id)` chain.
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`, region/zone
  `us-central1`/`us-central1-a`, ADC `14stevevitali@gmail.com`
  (roles/owner); every gcloud call passed `--project` explicitly.
- **Window:** run 2026-11-25T06:48Z→08:35Z — outside the 03:00Z→06:30Z
  never-band; the Dec monthly freeze does not apply. T0 (`06:56:02Z`) and
  the in-run refusal (`08:32:22Z`) are both outside it. No window refusal.
- **Evidence:** `docs/build/logs/ops-export-gce-4/` (the gitignored
  subtree): `run-export-on-vm.sh`, `probe-rights.sh`, `probe-labels.sh`,
  `attribution-probe3.py` + the NEW `probe-attribution.sh` wrapper and the
  NEW `probe-emit-gates.sh` — the exact executed drivers beside the
  captures (no secrets).

## Key difference vs attempt 3 — the spine now carries the E2-12 backfill

Same host, same image class (code == `b5a3b394`), same invocation. The
live spine now carries the `D-E2-12-BACKFILL` corrections, so the
pre-flight set was run **in full** before the ~96-minute build — the point
of this attempt — and a fourth probe (`probe-emit-gates.sh`) was added to
exercise the remaining `build_bundle`-path fail-closed calls
(`compute_export_license` → `compartment_for_license` per effective
record, an `assert_separated` replica, and a `row_rights` E2-12 replica).

## Verdict

| leg | verdict |
|---|---|
| prestate `instances list` | 0 items (`01-prestate.txt`) |
| `sig-export` Cloud Run job prestate | gen 10, 4cpu/16Gi, `Ready=True`, digest `…7dd590e8` (`00-job-prestate.txt`) |
| VM create `sig-export-gce-4` | **DONE** — `e2-highmem-8` (8 vCPU / 64,313 MiB observed) + 32 GiB swap safety net, Debian 12, 200 GB pd-balanced, SA `sig-export-rt` (scopes: cloud-platform), external IP 34.122.27.156 (`02-create.txt`, `03-poststate-instances.txt`) |
| image | **DONE** — fresh local amd64 `docker build` of `49551c43` (code == `b5a3b394`, ~10 min); local image id `sha256:22da3547c072…`, saved-tarball config `sha256:c7481bd4e1b2b9c51133ae816b550256dc4b6e466ba564bab745a9ef18ca4e52` == VM loaded image id; OCI `revision` label reads back `49551c438a40ee895658437ffdc65643307ffd86` on the VM; tagged `sig-api-export:gce4-49551c43` (`04-image-build.log`, `05-image-transfer.txt`, `06-image-id-chain.txt`) |
| cloud-sql-proxy + secret + DB | **OK** — proxy v2.18.3 on `127.0.0.1:5432` under the VM SA; `sig-pg-password` fetched via Secret Manager REST (env-only) |
| pre-flight 1 — licence gate | **PASS** — `probe-rights.sh`: 232 distinct effective rows, every record inside the registry (`decp_fr` effective `etalab-2.0`) (`07-rights-probe.txt`) |
| pre-flight 2 — E2-12 attribution | **PASS — 0 violations** — `attribution-probe3.py` replica over 223 distinct effective (source → rights_record) pairs; the `D-E2-12-BACKFILL` corrections resolve on the live spine (`08-attribution-probe.txt`) |
| pre-flight 3 — emit gates (NEW) | **PASS** — `probe-emit-gates.sh`: every effective record computes a licence that maps to a compartment; 14 compartments each licence-pure (`assert_separated` replica); 0 `row_rights` E2-12 violations; 1 licence-refused record (drops to exclusions — not a build fail) (`09-emit-gates-probe.txt`) |
| pre-flight 4 — SIG-UI-111 labels | **PASS** — `probe-labels.sh` (the real `_label_registry` + `freeze_hashes` + `check_unique_labels` chain, one RR/RO snapshot): 260,822 entities in 112.4 s; both incident `dot_511_wa` cameras emit their tier-0 `camera_name` labels; 207,322 `#`-disambiguated, 2,995 withheld (`10-labels-probe.txt`) |
| `python -m exports build --from-spine` (as-of `2026-11-25T06:55:58Z` → `exports/national/2026-11-25T065558Z/`) | **REFUSED — exit 1 at `compartment_for_license` (SIG-LIC-004a)** after ~96.3 min (docker run 06:56:02Z → 08:32:22Z). **The licence gate, the SIG-UI-111 label gate, and the E2-12 attribution gate ALL passed end-to-end inside the real build** — `build_bundle` (`spine_export.py:6019`) completed; the refusal landed LATER, at the P36.58 queue-v2 task-shard licence label (`spine_export.py:6561`). Memory plateaued **47.53 GiB container** / host `mem_used` peak 49,918 MB; swap untouched. **Zero files, zero objects** (`09-export-run-log.txt`, `10-mem-series.txt`) |
| upload → `gs://…-sig-restricted/exports/national/<as-of>/` | **not run** — no export output exists; prefix verified absent (`12-bucket-poststate.txt`) |
| `export.sh --apply fetch` / `D-P37.65a-1` re-cut | **not run** — no fresh export; `web/evaluation.json` presence unverifiable |
| teardown | **DONE** — `sig-export-gce-4` deleted 08:34:1xZ; poststate `instances list` = 0 items; 0 orphaned `sig-export-gce*` disks (`13-teardown.txt`) |
| `sig-export` Cloud Run job poststate | **unchanged** — gen 10, `Ready=True`, digest `…7dd590e8` (prestate == poststate, `14-job-poststate.txt`) |

`D-P37.65a-1` remains **OPEN**; this leg ended at an honest STOP — no
export exists to rsync, fetch, or re-cut.

## What this leg proved

1. **Every previously-refusing gate now passes end-to-end in the real
   build.** Attempt-1's licence gate (passed since attempt 2), attempt-2's
   `check_unique_labels` (passed since attempt 3), and attempt-3's
   `assert_attribution_rows` (E2-12 — first real-build pass this run, after
   the `D-E2-12-BACKFILL` corrections): all cleared, and `build_bundle`
   emitted its in-memory tables. The run got ~15 min *past* attempt 3's
   refusal point.
2. **The E2-12 backfill held in the real path** — the read-only replica
   predicted 0 violations and the build's real `enrich_rows` agreed.
3. **Blocker 8 is a FOURTH distinct gate failure — and a different
   *class*.** Blockers 5/7 were hosted-spine rights-record defects; this
   is a **code/registry-side** defect: a legal SPDX conjunction label with
   no compartment routing. See below.
4. **Substrate confirmed a fourth time:** e2-highmem-8 suffices; 47.53 GiB
   container / 49,918 MB host, swap 0 — same plateau as attempts 1–3
   (46.39/47.35/47.34).
5. **The four-probe pre-flight set is reusable** — the whole gate battery
   (~3.5 min) predicted the build's gate outcomes correctly for every gate
   it covered. Blocker 8 sits at a call site no probe replicated (see
   "why the probes didn't catch it").

## Blocker 8 — CURRENT (queue-shard mixed-licence conjunction has no compartment)

`compartment_for_license` (`exports/compartments.py:161`, invoked at
`spine_export.py:6561` in the P36.58 task-export v2 emit) refused the
build:

```
policy.licensing.LicenseIncompatibilityError: computed licence
'LicenseRef-DerivedFacts-Citations AND LicenseRef-PublicRecord-FactualCompilation'
has no export compartment in licenses.toml (add a [compartments.*] data row
— SIG-LIC-004a).
```

Mechanics (`11-blocker8-diagnosis.txt`):

- `_queue_license = surface_license(_queue_subject_licences)` — the union
  of `slices.licences_by_subject` over every `queue_v2` card's subject.
  `surface_license` (spine_export.py:2205) returns the single id for a
  one-licence set, else a **sorted SPDX `AND` expression** — a legal
  licence label for a mixed-licence web artifact (ADR-106).
- The queue-card subject set spans both
  `LicenseRef-DerivedFacts-Citations` (8 effective sources —
  `carnegie_ai_gsi`, `ccops_nyc_post`, `ccops_seattle`,
  `facial_recognition_world_map`, `madada`,
  `pathways_acoustic_drone_location`, `pathways_rtcc_federation`,
  `state_alpr_statute_inventory`) and
  `LicenseRef-PublicRecord-FactualCompilation` (~60 effective sources —
  the `camreg_*`/`ccops_*`/`dot_511_*` registries). The conjunction is
  deterministic for this spine.
- The call site reads
  `C.compartment_for_license(_queue_license, None, registry) or _WEB_COMPARTMENT`
  — the author plainly intended a no-compartment licence to fall back to
  the `web` artifact compartment. But `compartment_for_license`
  **raises** `LicenseIncompatibilityError` on any unmapped licence
  (SIG-LIC-004a); it never returns falsy, so the `or` fallback is dead
  code. Contrast the dossier-visuals caller at `spine_export.py:6263-6266`
  which wraps the same function in `try/except → "unknown"`.
- Compartments are single-licence by construction (`licenses.toml`
  `[compartments.*]` — 14 rows, one licence each); no AND-expression can
  ever map. **Every** run whose queue subjects span 2+ licences refuses
  here — not spine-state-dependent the way blockers 5/7 were.
- Fix class (operator/next leg's decision, NOT improvised this leg):
  either route AND-expressions to the `web` compartment at :6561 (the
  try/except the neighbouring caller already models) or add a
  `licenses.toml` compartment for the conjunction. A code fix needs a
  new image; a `licenses.toml` row is repo data — both are ordinary
  commits, no gate record needed.

**Why the probes didn't catch it:** the emit-gates probe exercises
`compartment_for_license` per *effective record* — the conjunction exists
only at the *union across queue subjects*, one call-site layer above.
Replicating `_queue_subject_licences` needs `queue_v2` (the `_research_queue`
rows rekeyed through `contribution_plan`) + `licences_by_subject` — most of
the ~50-min shape pipeline, not a cheap probe. A cheaper sufficient check
for a next attempt: the distinct effective-licence set has >1 member **and**
the :6561 call site computes `compartment_for_license(surface_license(set))`
with no conjunction handling — i.e., a *static* check on the emit path,
which this leg's diagnosis file now records.

**Resume path (operator / next leg):** (1) fix :6561 (AND → `web`
compartment, or a conjunction-aware `compartment_for_license` — decide
which; ordinary commit on a fix branch like `b5a3b394`'s); (2) re-stand a
VM — the recipe is unchanged (`run-export-on-vm.sh`; rebuild the image at
the fix tip ~10 min; run the four probes first — all still pass this
spine); (3) same docker run → `gcloud storage rsync` `/export-out` up →
`export.sh --apply fetch` → re-cut per `99018e1b`. No spine mutation is
involved in this blocker.

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 06:49:46 | `gcloud compute instances create sig-export-gce-4` (e2-highmem-8, debian-12, 200 GB, SA `sig-export-rt`, scopes cloud-platform, label `purpose=sig-export-gce-4`) | 0 instances → RUNNING (`02-create.txt`, `03-poststate-instances.txt`) |
| 06:50→06:51 | VM setup (no GCP mutation): `docker.io` + `jq` apt; `cloud-sql-proxy` v2.18.3 binary (`05-vm-setup.txt`) | — |
| 06:50→06:51 | image `docker save` → ssh `docker load` → `sig-api-export:gce4-49551c43` | image absent on VM → present (id `c7481bd4e1b2…`) (`05-image-transfer.txt`, `06-image-id-chain.txt`) |
| 06:51→06:52 | read-only licence-gate pre-flight (`probe-rights.sh`) | no DB mutation — **PASS** |
| 06:52→06:53 | read-only E2-12 pre-flight (`probe-attribution.sh` → `attribution-probe3.py`) | no DB mutation — **PASS, 0 violations** |
| 06:53 | read-only emit-gates pre-flight (`probe-emit-gates.sh`) | no DB mutation — **PASS** |
| 06:53→06:55 | read-only label-gate pre-flight (`probe-labels.sh`, one RR/RO snapshot) | no DB mutation — **PASS** |
| 06:56:02→08:32:22 | `docker run sig-export-build` — `python -m exports build --from-spine --dsn postgresql://sig:…@127.0.0.1:5432/sig --as-of 2026-11-25T06:55:58Z --environment production --out /out/exports/national/2026-11-25T065558Z` (`PGOPTIONS=--work_mem=2GB`, `PYTHONMALLOC=malloc`, `MALLOC_TRIM_THRESHOLD_=65536`) | container created → **refused rc=1** (`LicenseIncompatibilityError`, SIG-LIC-004a at `spine_export.py:6561`); 0 files local, 0 objects remote |
| 08:33→08:34 | read-only diagnosis capture (source-licence lists from probe output; bucket prefix check) | no DB mutation |
| 08:34:1x | `gcloud compute instances delete sig-export-gce-4` | RUNNING → **absent**; `instances list` = 0 items; 0 orphan disks |

Unchanged: `sig-export` job (gen 10 declared shape, `Ready`, digest
`…7dd590e8`), bucket policy, IAM, firewall, authorized-networks,
`registry/` (`latest.json` untouched — no export produced),
`sources.toml`, the alias table, `licenses.toml`.

## Notes for the record

- **Executing identity:** the VM ran as `sig-export-rt` (its three declared
  bindings — `roles/cloudsql.client`, `secretAccessor` on `sig-pg-password`,
  `storage.objectUser` on `…-sig-restricted` — exercised green).
  `iam.serviceAccountUser` permitted under the operator ADC (owner). The
  image was built locally under the operator's Docker Desktop — no
  artifactregistry grant needed, no AR mutation made (declared posture
  respected). No IAM change was made.
- The attempt-3 tag `gce3-b5a3b394` was indeed reaped locally; the rebuild
  from `git archive HEAD` of the worktree tip reproduced the same content
  class (image id differs — new build — but `git diff
  b5a3b394..49551c43` is docs-only so the code path is the one the
  attempt-3 run exercised past the label gate).
- Duration decomposition: fetch ≈30 min, shape+labels ≈50 min,
  `build_bundle` + emit ≈16 min to the refusal — consistent with
  attempt 3's shape.
- Stage-serialization bound (~0.37 obj/s ⇒ ~14.7 days for ~475k objects)
  still stands for the re-cut's `stage` step whenever an export lands.
- The new `probe-emit-gates.sh` is kept with the run evidence — it
  complements the other three pre-flights for the next attempt.
