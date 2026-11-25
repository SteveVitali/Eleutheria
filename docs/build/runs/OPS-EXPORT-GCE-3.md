# OPS-EXPORT-GCE-3 — one-off GCE exec leg for the national export (attempt 3)

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (the fresh-export half of `D-P37.65a-1`); attempt 3 of
  `docs/build/runs/OPS-EXPORT-GCE-1.md` / `OPS-EXPORT-GCE-2.md` — identical
  recipe, image rebuilt at the label-fix tip.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-gce-3` forked at `b5a3b394`
  (`r11/ops-label-collision-fix` tip — the SIG-UI-111 fix; worktree
  `/tmp/sig-export-gce3`).
- **Authorization:** operator-signed commit `8bb00c9d` (GATE DECISIONS
  `2026-11-24T18:00Z`, "Export substrate — operator decision: one-off GCE
  exec leg >=64 GiB") — a ONE-OFF export execution on a >=64 GiB GCE host
  under operator ADC, torn down after the run. Still current: same leg,
  new attempt.
- **Blocker-6 disposition:** attempt 2 refused at `check_unique_labels`
  (SIG-UI-111 — two `dot_511_wa` cameras sharing display label
  `surveillance camera in iso3166-2:US-WA #tyvj`). Fix `b5a3b394` on
  `r11/ops-label-collision-fix` (PR #558): `resolve_disambiguators`
  step-3 hash extension (the slug-registry freeze rule) +
  `natural_person_signal` terminal-position person-token fix (a leading
  `SR ` is a State Route, not a "Sr" suffix — the bug that dropped both
  cameras' `camera_name` candidates). This leg's image carries that commit.
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`, region/zone
  `us-central1`/`us-central1-a`, ADC `14stevevitali@gmail.com` (roles/owner);
  every gcloud call passed `--project` explicitly.
- **Window:** run 2026-11-25T01:30Z→03:07Z — outside AR-3 (03:00Z→06:30Z);
  the Dec monthly freeze does not apply. T0 (`01:36:18Z`) precedes the
  window; the in-run refusal at 02:57Z precedes it too. No window refusal.
- **Evidence:** `docs/build/logs/ops-export-gce-3/` (the gitignored subtree;
  `run-export-on-vm.sh` + `probe-rights.sh` + the NEW `probe-labels.sh` +
  the three `attribution-probe*.py` read-only probes are the exact executed
  drivers, kept beside the captures — no secrets).

## Key difference vs attempts 1/2 — the image carries the fix

Attempts 1/2 transferred the pinned `sig-api@sha256:7dd590e8…` — which
predates the label fix. This leg **built a fresh image from the worktree
tip `b5a3b394`** locally: the same `docker build -f ops/Dockerfile` the
`export.sh image` Cloud Build step runs, with `--platform linux/amd64`
(local host is darwin/arm64) and
`--build-arg SIG_CODE_COMMIT=b5a3b3943baf29a80c66a651b2d10440d1eb98c5`
(the P35.13 revision label the deploy build stamps — it reads back off
the loaded image on the VM). Build context: extracted `git archive HEAD`
of the worktree — the same clean tree Cloud Build receives. Transfer via
`docker save | ssh docker load` under operator ADC — `sig-export-rt` holds
no artifactregistry grant (declared posture, attempt-1 mechanism); no AR
objects were created, no tag pushed.

## Verdict

| leg | verdict |
|---|---|
| prestate `instances list` | 0 items (`01-prestate.txt`) |
| `sig-export` Cloud Run job prestate | gen 10, 4cpu/16Gi, `Ready=True`, digest `…7dd590e8` (`00-job-prestate.txt`) |
| VM create `sig-export-gce-3` | **DONE** — `e2-highmem-8` (8 vCPU / 64,313 MiB observed) + 32 GiB swap safety net, Debian 12, 200 GB pd-balanced, SA `sig-export-rt` (scopes: cloud-platform), external IP 136.115.131.241 (`02-create.txt`, `03-poststate-instances.txt`) |
| image | **DONE** — fresh local amd64 `docker build` of `b5a3b394` (~10 min); local image id `sha256:bba69c45239e…`, saved-tarball config `sha256:9ee85c118555d2a653bc48941838d9bd7efdcbd0fb5af50919327f4052c633c2` == VM loaded image id; OCI `revision` label reads back `b5a3b3943baf29a80c66a651b2d10440d1eb98c5` on the VM; tagged `sig-api-export:gce3-b5a3b394`. **Digest differs from `7dd590e8` as required** (`05-image-transfer.txt`, `06-image-id-chain.txt`) |
| cloud-sql-proxy + secret + DB | **OK** — proxy v2.18.3 on `127.0.0.1:5432` under the VM SA; `sig-pg-password` fetched via Secret Manager REST (env-only) |
| licence-gate pre-flight | **PASS** — `probe-rights.sh` (effective-rights resolution + real `compute_export_license` over all 232 distinct records): `decp_fr` effective `etalab-2.0` over 60,319 claims; every effective record inside the registry (`07-rights-probe.txt`) |
| **label-gate pre-flight (NEW)** | **PASS** — `probe-labels.sh` ran the REAL `_label_registry` + `freeze_hashes` + `check_unique_labels` chain (`spine_export.py:5918-5928` verbatim) over the live spine inside one `REPEATABLE READ READ ONLY` snapshot: 260,819 entities in 131.6 s. Both incident cameras emit their tier-0 `camera_name` labels — `01a0b0d1…` → `'SR 167 at MP 21.3: 84th Ave S'`, `01a0b0e6…` → `'SR 16 at MP 7.5: TNB EB East Anchorage'` — distinct; 207,322 labels carry `#` disambiguators; 2,995 withheld (`08-labels-probe.txt`) |
| `python -m exports build --from-spine` (as-of `2026-11-25T01:36:16Z` → `exports/national/2026-11-25T013616Z/`) | **REFUSED — exit 1 at `assert_attribution_rows` (E2-12 / ADR-194)** after ~81.7 min (docker run 01:36:18Z → 02:57:58Z). The licence gate passed (`label_facts` completed); **the SIG-UI-111 label gate passed** (`check_unique_labels` at `spine_export.py:5928` cleared — the fix works end-to-end in the real path); the refusal landed in the EMIT phase at `build_bundle` → `enrich_rows` (`spine_export.py:6019` → `compartments.py:382`→`347`). Memory plateaued **47.34 GiB container** / host `mem_used` peak 49,642 MB; swap untouched. **Zero files, zero objects** (`09-export-run-log.txt`, `10-mem-series.txt`). |
| upload → `gs://…-sig-restricted/exports/national/<as-of>/` | **not run** — no export output exists; prefix verified absent (`12-bucket-poststate.txt`) |
| `export.sh --apply fetch` / `D-P37.65a-1` re-cut | **not run** — no fresh export; `web/evaluation.json` presence unverifiable (nothing produced) |
| teardown | **DONE** — `sig-export-gce-3` deleted 03:06:1xZ; poststate `instances list` = 0 items; 0 orphaned `sig-export-gce*` disks (`13-teardown.txt`) |
| `sig-export` Cloud Run job poststate | **unchanged** — gen 10, `Ready=True`, digest `…7dd590e8` (prestate == poststate, `14-job-poststate.txt`) |

`D-P37.65a-1` remains **OPEN**; this leg ended at an honest STOP — no export
exists to rsync, fetch, or re-cut.

## What this leg proved

1. **The SIG-UI-111 fix works in the real export path.** Attempt 2 refused
   at `spine_export.py:5928` (`check_unique_labels`); this run — same
   queries, same spine state class — cleared that exact call and every
   emit gate up to `build_bundle`'s `enrich_rows`. The pre-flight's
   prediction held: both `dot_511_wa` cameras emit `camera_name` labels
   (the `natural_person_signal` fix), and the step-3 hash extension means
   the display-disambiguator can no longer ship a duplicate.
2. **Blocker 7 is a THIRD distinct spine-data gate failure** — same defect
   *class* as Blocker 5 (`decp_fr`): a hosted-spine `rights_record` that
   diverges from the declared registry — but a different gate (E2-12 row
   attribution, at emit, inside `build_bundle`) and a different column
   (`attribution_text`, not `spdx_expression`). See below.
3. **Substrate re-confirmed a third time:** e2-highmem-8 suffices;
   47.34 GiB container / 49,642 MB host, swap 0 — statistically the same
   plateau as attempts 1/2 (46.39/47.35).
4. **`probe-labels.sh` is a second reusable pre-flight** — the full
   label-gate chain in ~2 min instead of ~80, verified against the real
   outcome (predicted PASS, the real build PASSED the label gate).

## Blocker 7 — CURRENT (hosted spine carries rights rows with empty attribution_text)

`assert_attribution_rows` (`exports/compartments.py:347`, invoked from
`enrich_rows` inside `build_bundle` at `spine_export.py:6019`) refused the
build:

```
exports.compartments.AttributionGateError: export gate refused table 'sites':
3029 row(s) carry attribution_required=true with empty attribution
(E2-12 / ADR-194 — the row names no upstream to credit):
  camreg_und_001 (row 14436) … (first 20 violations all camreg_und_001)
```

What the read-only probes found (`11-attribution-probe.txt`):

- `camreg_und_001` is a **projected** source id — the raw spine
  `ea.source_id` is a P34.18-suppressed personal handle; the committed
  alias table keys it by digest `sha256:d2876a49…` → `camreg_und_001`.
  One suppressed raw source_id on the spine digests to it (469 claims).
- Its effective `rights_record` is **`01a0b868-dca5-7e8b-958c-46b4fdd4c454`**:
  `spdx='LicenseRef-OperatorAccepted-DBRight'`, **`attribution_text=NULL`**,
  `redistributable=yes`, `terms_url=NULL` — **zero** `rights_decision`
  rows ever landed for it. The licence declares
  `attribution_required=true`, so `downstream_obligations` emits
  `attribution=''` → the E2-12 gate fires. `sources.toml
  [sources.camreg_und_001.rights]` itself declares a non-empty
  `attribution` (`"ArcGIS community-published traffic-camera registry
  camera registry"`) + `terms_url` — the spine record diverges from the
  declared registry (the recorded identifier/attribution defect class
  ADR-194/P34.21a already diagnosed; the review evidence even notes
  `attribution: rows attribution='' (n-empty)`).
- **Blast radius is larger than the first 20 named rows.** Replaying
  `downstream_obligations` over every distinct effective
  (source → rights_record) pair on the live spine finds **34 pairs**
  the same gate would refuse — all riding just **three** defective
  `rights_record` rows, each `attribution_text=NULL` under an
  attribution-required licence:
  - `01a0b868-dca5-7e8b-958c-46b4fdd4c454`
    (`LicenseRef-OperatorAccepted-DBRight`) — 29 suppressed `camreg_und_*`
    sources (~87k claims incl. `camreg_und_023` 57,530 / `camreg_und_008`
    5,874 / `camreg_und_019` 5,408 / `camreg_und_018` 4,746);
  - `01a0b868-776e-72ca-b1c2-18411c3ff7b3`
    (`LicenseRef-PublicRecord-FactualCompilation`) — `camreg_us_ny_001`
    (1,544), `camreg_us_ny_002` (1,720), `dot_511_ky` (3,239),
    `dot_511_ut` (11,496);
  - `01a0b98a-c001-7a19-bc54-349f5f508efe` (`LicenseRef-StAlbert-ODL-1.0`)
    — `camreg_stalbert_ab` (720).

The designed correction is the same **D-P34.21a-class INSERT-only
backfill** (`sig-db attribution-corrections --apply` — new `rights_record`
rows carrying the declared attribution text + `rights_decision` redirects
per (source, prior_rights_id) pair; the export's
`COALESCE(ld.rights_id, c.rights_id)` then resolves the corrected record).
That is a production spine mutation outside this leg's signed scope — the
D-P34.21a chain's own legs carry the pre-authorizations and pre-states
(the `D-P34.21a-1` run `P34.21a-live-3.md` is the recipe). **STOP,
recorded, not improvised.**

**Resume path (operator / next leg):** (1) operator go for an
attribution-corrections artifact covering the three defective records
(the probe names them + their (source → record) pairs verbatim; the
registry's declared attribution strings are in `sources.toml`); (2)
re-stand a VM — the whole recipe is recorded (`run-export-on-vm.sh`;
the `b5a3b394` image can be rebuilt in ~10 min from the same worktree or
re-exported; `probe-rights.sh` + `probe-labels.sh` run the two cheap
gates first); (3) same docker run → `gcloud storage rsync` `/export-out`
up → `export.sh --apply fetch` → re-cut per `99018e1b`. A third cheap
pre-flight can replicate this blocker exactly — `downstream_obligations`
per effective record + the `attribution_required`/`empty` check is the
`attribution-probe3.py` middle section.

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 01:30:22 | `gcloud compute instances create sig-export-gce-3` (e2-highmem-8, debian-12, 200 GB, SA `sig-export-rt`, scopes cloud-platform, label `purpose=sig-export-gce-3`) | 0 instances → RUNNING (`02-create.txt`, `03-poststate-instances.txt`) |
| 01:30→01:32 | VM setup (no GCP mutation): `docker.io` + `jq` apt; `cloud-sql-proxy` v2.18.3 binary (`05-vm-setup.txt`) | — |
| 01:31→01:32 | image `docker save` → ssh `docker load` → `sig-api-export:gce3-b5a3b394` | image absent on VM → present (id `9ee85c118555…`) (`05-image-transfer.txt`, `06-image-id-chain.txt`) |
| 01:33:0x→01:33:4x | read-only licence-gate pre-flight probe (`probe-rights.sh`) | no DB mutation |
| 01:33:4x→01:36:0x | read-only label-gate pre-flight probe (`probe-labels.sh`, one RR/RO snapshot) | no DB mutation |
| 01:36:18→02:57:58 | `docker run sig-export-build` — `python -m exports build --from-spine --dsn postgresql://sig:…@127.0.0.1:5432/sig --as-of 2026-11-25T01:36:16Z --environment production --out /out/exports/national/2026-11-25T013616Z` (`PGOPTIONS=--work_mem=2GB`, `PYTHONMALLOC=malloc`, `MALLOC_TRIM_THRESHOLD_=65536`) | container created → **refused rc=1** (`AttributionGateError`, E2-12); 0 files local, 0 objects remote |
| ~02:59→03:05 | read-only spine probes (suppressed-source digest match, effective records, blast radius; password env-only) | no DB mutation |
| 03:06:1x | `gcloud compute instances delete sig-export-gce-3` | RUNNING → **absent**; `instances list` = 0 items; 0 orphan disks |

Unchanged: `sig-export` job (gen 10 declared shape, `Ready`, digest
`…7dd590e8`), bucket policy, IAM, firewall, authorized-networks (the
proxy path needed none), `registry/` (`latest.json` untouched — no export
produced), sources.toml, the alias table.

## Notes for the record

- **Executing identity:** the VM ran as `sig-export-rt` (its three declared
  bindings — `roles/cloudsql.client`, `secretAccessor` on `sig-pg-password`,
  `storage.objectUser` on `…-sig-restricted` — exercised green).
  `iam.serviceAccountUser` permitted under the operator ADC (owner). The
  image was built locally under the operator's Docker Desktop — no
  artifactregistry grant needed, no AR mutation made (declared posture
  respected). No IAM change was made.
- The vm-setup capture carries one cosmetic noise line: an ad-hoc md5
  probe printed `FAILED` before `cloud-sql-proxy --version` verified the
  binary — the recipe is byte-identical to attempt 2's otherwise.
- **Why neither pre-flight caught Blocker 7:** `probe-rights.sh` runs
  `compute_export_license`/`export_refusal_reason` per effective record —
  the licence-compatibility gate (`spdx` inside the registry); the
  `attribution_text` emptiness is a different, later check (E2-12 row
  enrichment at emit). `probe-labels.sh` exercises the label path only.
  The recorded `attribution-probe3.py` fragment (distinct effective
  records → `downstream_obligations` → `attribution_required && empty`)
  is the cheap third pre-flight for the next attempt — ~30 s against the
  live spine.
- Attempt-2 carry-forwards unchanged: same host shape, same env knobs,
  same failure-before-write posture (0 files, 0 objects — the refusal
  lands before any emit; the `sites` table rows that failed are in-memory
  serialisation candidates, never bytes written).
- Stage-serialization bound (~0.37 obj/s ⇒ ~14.7 days for ~475k objects)
  still stands for the re-cut's `stage` step whenever an export lands.
