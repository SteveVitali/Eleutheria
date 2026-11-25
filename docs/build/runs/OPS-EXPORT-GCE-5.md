# OPS-EXPORT-GCE-5 — one-off GCE exec leg for the national export (attempt 5)

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (the fresh-export half of `D-P37.65a-1`); attempt 5 of
  `docs/build/runs/OPS-EXPORT-GCE-1.md` / `-2` / `-3` / `-4` — identical
  recipe, image rebuilt at the fix-merged tip.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-gce-5` at `0fa885c0` — a merge of
  `r11/ops-export-gce-4` (probe scripts + ledgers) and
  `r11/ops-siglic004a-fix` (`f43fdbf9`); worktree `/tmp/sig-export-gce5`.
  Verified at leg start:
  `git merge-base --is-ancestor b5a3b394 0fa885c0` → true (SIG-UI-111) and
  `git merge-base --is-ancestor f43fdbf9 0fa885c0` → true (SIG-LIC-004a) —
  the image carries **both** fixes.
- **Authorization:** operator-signed commit `8bb00c9d` (GATE DECISIONS
  `2026-11-24T18:00Z`, "Export substrate — operator decision: one-off GCE
  exec leg >=64 GiB") — a ONE-OFF export execution on a >=64 GiB GCE host
  under operator ADC, torn down after the run. Still current: same leg,
  fifth attempt.
- **Blocker-8 disposition:** attempt 4 refused at
  `compartment_for_license` (SIG-LIC-004a — the queue-v2 task-shard SPDX
  `AND` union `LicenseRef-DerivedFacts-Citations AND
  LicenseRef-PublicRecord-FactualCompilation` has no single-licence
  compartment; the `or _WEB_COMPARTMENT` fallback was dead code).
  `f43fdbf9` extracts `_queue_shard_compartment` (spine_export.py:2221,
  call site :6578): single-licence unions file in that licence's real
  compartment; an unmapped licence (any `AND` union — compartments are
  single-licence by construction) files in `web`, the ADR-106 §4 documented
  posture. The fail-closed gate itself is untouched —
  `compartment_for_license` still raises on an unmapped licence.
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`, region/zone
  `us-central1`/`us-central1-a`, ADC `14stevevitali@gmail.com`
  (roles/owner); every gcloud call passed `--project` explicitly.
- **Window:** run 2026-11-25T08:41Z→11:02Z — outside the 03:00Z→06:30Z
  never-band; the Dec monthly freeze does not apply. T0 (`08:48:49Z`) and
  the in-run refusal (`10:52:08Z`) are both outside it. No window refusal.
- **Evidence:** `docs/build/logs/ops-export-gce-5/` (the gitignored
  subtree): `run-export-on-vm.sh`, `probe-rights.sh`, `probe-labels.sh`,
  `probe-attribution.sh` + `attribution-probe3.py`, `probe-emit-gates.sh`,
  and the NEW `probe-queue-compartment.sh` — the exact executed drivers
  beside the captures (no secrets).

## Key difference vs attempt 4 — the image carries `_queue_shard_compartment`

Same host class, same invocation, same live spine (the `D-E2-12-BACKFILL`
corrections remain). The image is rebuilt at `0fa885c0` so the P36.58
queue-v2 emit routes its mixed-union licence label through the new
`_queue_shard_compartment` helper instead of bare
`compartment_for_license`. A fifth pre-flight
(`probe-queue-compartment.sh`) was added to exercise exactly that path on
the live spine's licence set before spending the ~96-minute build.

## Remaining unexercised gates (static scan, this leg)

Every `compartment_for_license` call site was audited after the fix:

- `spine_export.py:1663` (slice licence computation), `:1986` (placement
  slots), `:5642` (`_label_registry` label_comps), `:5989` (site-slice
  licences), `:6029` (sig compartment), `:6277` (dossier-visuals, already
  try/except→"unknown") — all **single-licence per-record** calls, all
  exercised in attempt 4 or covered by the emit-gates/labels probes.
- `bundle.py:231` (crosswalk compartment), `compartments.py:181`
  (`place_table`) — inside `build_bundle`, which **completed** in
  attempt 4.
- `:2233` — the new `_queue_shard_compartment` wrapper itself.

Fail-closed calls **past** the attempt-4 refusal point (never yet
exercised in a real build):

- `CR.assert_documented` for `record_claims` (:6772), `statements`
  (:6807), `labels` (:6843), `source_licence_table` (:7097) — the
  SIG-TRANSP-016 emitted-column gate. Column sets are writer-code
  determined; a local check confirms all four resources are registered.
- `CR.assert_path_documented` (:7750) over every artifact path —
  `UnregisteredResourceError` on a row-bearing path with no resource.
  Locally verified: every path family the tail emits resolves
  (`{comp}/record_claims.jsonl`, `{comp}/statements.jsonl`,
  `labels/{comp}.jsonl`, `{comp}/sites.geojson`,
  `web/tiles/*-sites.*.pmtiles` → `sites`, `transparency/*.jsonl`,
  `transparency/sources/<id>/executions.jsonl`, `web/entity/**`,
  `web/graph/**`) or is document-exempt (`.gz`, `.json`, `.ttl`,
  `web/tasks/**/*.jsonl.gz`, `by-source/**`, `by-dossier/**`).
- `mech_eval_lint_errors` (:7142) and `quality_page_lint_errors` (:7165) —
  data-driven self-lints, not cheaply replicable.
- `DownloadError` in `emit_source_slice`/`emit_dossier_slice`
  (SIG-TRANSP-015 attribution-payload completeness, HG-03 E4
  permitted-source check) — internally consistent derivations over the
  same `rows_by_compartment`/`_compartment_attribution` inputs; the
  substantive data gate (E2-12) is probe-covered (0 violations).
- `attribution_txt` empty-payload refusal (:169 in downloads.py) — same
  E2-12 class, probe-covered.

## Verdict

| leg | verdict |
|---|---|
| prestate `instances list` | 0 items (`01-prestate.txt`) |
| `sig-export` Cloud Run job prestate | gen 10, 4cpu/16Gi, `Ready=True`, digest `…7dd590e8` (`00-job-prestate.txt`) |
| VM create `sig-export-gce-5` | **DONE** — `e2-highmem-8` (8 vCPU / 64,313 MiB) + 32 GiB swap safety net, Debian 12, 200 GB pd-balanced, SA `sig-export-rt` (scopes: cloud-platform), external IP 34.172.143.79 (`02-create.txt`, `03-poststate-instances.txt`) |
| image | **DONE** — fresh local amd64 `docker build` of `0fa885c0` (carries BOTH `b5a3b394` SIG-UI-111 and `f43fdbf9` SIG-LIC-004a, ~8 min); local image id `sha256:e40181634836…`, saved-tarball config `sha256:f17236236dcf9af4bd289eba3ac3214fc6defad2aed28b9b7d7b7f6bd6e35290` == VM loaded image id; OCI `revision` label reads back `0fa885c0f7dfd9f6332c64705c99487b3852a2a5` on the VM; tagged `sig-api-export:gce5-0fa885c0` (`04-image-build.log`, `05-image-transfer.txt`, `06-image-id-chain.txt`) |
| cloud-sql-proxy + secret + DB | **OK** — proxy v2.18.3 on `127.0.0.1:5432` under the VM SA; `sig-pg-password` fetched via Secret Manager REST (env-only) |
| pre-flight 1 — licence gate | **PASS** — `probe-rights.sh`: 232 distinct effective rows, every record inside the registry (`decp_fr` effective `etalab-2.0`) (`07-rights-probe.txt`) |
| pre-flight 2 — E2-12 attribution | **PASS — 0 violations** — `attribution-probe3.py` replica over 223 distinct effective (source → rights_record) pairs (`08-attribution-probe.txt`) |
| pre-flight 3 — emit gates | **PASS** — `probe-emit-gates.sh`: every effective record computes a licence that maps to a compartment; 14 compartments each licence-pure (`assert_separated` replica); 0 `row_rights` E2-12 violations; 1 licence-refused record (drops to exclusions — not a build fail) (`09-emit-gates-probe.txt`) |
| pre-flight 4 — queue compartment (NEW) | **PASS** — `probe-queue-compartment.sh`: the exact attempt-4 union `LicenseRef-DerivedFacts-Citations AND LicenseRef-PublicRecord-FactualCompilation` → `_queue_shard_compartment` returns `web` (no raise); the 14-member all-effective licence union → `web`; each single licence routes to its real compartment (`CC-BY-4.0`→`sig_graph`, `ODbL-1.0`→`osm_physical`, …); bare `compartment_for_license` still raises on the union — the fail-closed gate is untouched (`09b-queue-compartment-probe.txt`) |
| pre-flight 5 — SIG-UI-111 labels | **PASS** — `probe-labels.sh` (the real `_label_registry` + `freeze_hashes` + `check_unique_labels` chain, one RR/RO snapshot): 260,822 entities in 113.6 s; both incident `dot_511_wa` cameras emit their tier-0 `camera_name` labels; 207,322 `#`-disambiguated, 2,995 withheld (`10-labels-probe.txt`) |
| `python -m exports build --from-spine` (as-of `2026-11-25T08:48:47Z` → `exports/national/2026-11-25T084847Z/`) | **REFUSED — exit 1 at the per-compartment PMTiles render (tippecanoe `EXIT_NODATA` 110)** after ~123.3 min (docker run 08:48:49Z → 10:52:08Z). **The SIG-LIC-004a fix HELD end-to-end** — the build passed the attempt-4 refusal point (:6578, ~96 min) and ran the entire never-before-reached emit tail (~6,000 lines: record_claims/statements/labels streams, downloads, dossier + by-source slices, transparency, mech/quality lints) before refusing on the `derived_facts` compartment's tile archive — its emit has **zero located features** (every slice row is `geometry: null`; `_merged_records` skips them all), and tippecanoe exits `EXIT_NODATA` on a zero-feature FeatureCollection. Peaks: **50.7 GiB container** / host `mem_used` 53,136 MB; swap untouched. **Zero files, zero objects** (`09-export-run-log.txt`, `10-mem-series.txt`, `11-blocker9-diagnosis.txt`) |
| upload → `gs://…-sig-restricted/exports/national/<as-of>/` | **not run** — no export output exists; prefix verified absent (`12-bucket-poststate.txt`) |
| `export.sh --apply fetch` / `D-P37.65a-1` re-cut | **not run** — no fresh export; `web/evaluation.json` presence unverifiable |
| teardown | **DONE** — `sig-export-gce-5` deleted 11:01:4xZ; poststate `instances list` = 0 items; 0 orphaned `sig-export-gce*` disks (`13-teardown.txt`) |
| `sig-export` Cloud Run job poststate | **unchanged** — gen 10, `Ready=True`, digest `…7dd590e8` (prestate == poststate, `14-job-poststate.txt`) |

`D-P37.65a-1` remains **OPEN**; this leg ended at an honest STOP — no
export exists to rsync, fetch, or re-cut.

## What this leg proved

1. **`f43fdbf9` held end-to-end.** The licence gate, SIG-UI-111 label
   gate, E2-12 attribution gate, emit-gates set, **and** the new
   `_queue_shard_compartment` path all passed in the real build — the run
   went ~27 min *past* attempt 4's refusal point, deeper than any prior
   attempt has ever reached.
2. **All five pre-flights predicted their gates correctly again** — the
   new `probe-queue-compartment.sh` exercised the exact call site on the
   live licence set (`AND` union → `web`, singles → real compartments,
   bare gate still raises) before the ~2-hour build spent anything.
3. **Blocker 9 is a FIFTH distinct gate failure — same class as
   blocker 8 (code-side, deterministic).** tippecanoe `EXIT_NODATA` is
   uncaught in `render_compartment_sites_pmtiles`; an all-unlocated
   compartment has no honest-absence path. See
   `11-blocker9-diagnosis.txt` for the full mechanism + fix classes
   (catch rc=110 → skip + record absence / pure-Python empty archive /
   gate on emit feature count; plus propagate `e.stderr` — the swallowed
   "Did not read any valid geometries" would have named this without a
   diagnosis step).
4. **Substrate confirmed a fifth time:** e2-highmem-8 suffices —
   50.7 GiB container / 53,136 MB host peak, swap 0. The emit tail is
   heavier than the ~47.5 GiB shape plateau; still within the 64 GiB
   envelope + swap net.

## Blocker 9 — CURRENT (all-unlocated compartment → tippecanoe EXIT_NODATA)

`render_compartment_sites_pmtiles` (`tiles.py:1782`, invoked at
`spine_export.py:7457` in the P35.52 per-compartment `sig.map-tiles/2`
emit) refused the build. The `derived_facts` compartment's
`sites.geojson` emits zero located features — the compartment's sources
(`carnegie_ai_gsi`, `ccops_nyc_post`, `ccops_seattle`,
`facial_recognition_world_map`, `madada`, `pathways_*`,
`state_alpr_statute_inventory`) are document/statute/inventory records
with no located points — `_merged_records` drops every `geometry: null`
feature, tippecanoe reads zero valid geometries and exits 110
(`EXIT_NODATA`), and `subprocess.run(check=True)` converts it to a build
refusal. Verified exactly: the same image's tippecanoe on an empty
FeatureCollection prints "Did not read any valid geometries" and exits
110. tippecanoe's stderr was captured but `CalledProcessError.__str__`
omits it — the reason was recovered from the exit code.

**Why the probes didn't catch it:** the failure needs the real
`<comp>/sites.geojson` (a `build_bundle` output — the ~96-min mark) *and*
the compartment's located-vs-unlocated split; the emit-gates probe stops
at licence/compartment routing. A sufficient cheap check for a future
attempt: does every compartment's slice carry ≥1 located row (else the
tile path must handle the empty emit).

**Resume path (operator / next leg):** (1) fix the tile emit for the
zero-feature case per `11-blocker9-diagnosis.txt` fix classes (ordinary
commit on a fix branch like `f43fdbf9`'s); (2) re-stand a VM — recipe
unchanged, all five probes still pass this spine; (3) same docker run →
`gcloud storage rsync` `/export-out` up → `export.sh --apply fetch` →
re-cut per `99018e1b`. No spine mutation is involved in this blocker.

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 08:41:54 | `gcloud compute instances create sig-export-gce-5` (e2-highmem-8, debian-12, 200 GB, SA `sig-export-rt`, scopes cloud-platform, label `purpose=sig-export-gce-5`) | 0 instances → RUNNING (`02-create.txt`, `03-poststate-instances.txt`) |
| 08:42→08:43 | VM setup (no GCP mutation): `docker.io` + `jq` apt; `cloud-sql-proxy` v2.18.3 binary (`05-vm-setup.txt`) | — |
| 08:42→08:43 | image `docker save` → ssh `docker load` → `sig-api-export:gce5-0fa885c0` | image absent on VM → present (id `f17236236dcf…`) (`05-image-transfer.txt`, `06-image-id-chain.txt`) |
| 08:44 | read-only licence-gate pre-flight (`probe-rights.sh`) | no DB mutation — **PASS** |
| 08:44→08:45 | read-only E2-12 pre-flight (`probe-attribution.sh` → `attribution-probe3.py`) | no DB mutation — **PASS, 0 violations** |
| 08:45 | read-only emit-gates pre-flight (`probe-emit-gates.sh`) | no DB mutation — **PASS** |
| 08:45→08:46 | read-only queue-compartment pre-flight (`probe-queue-compartment.sh`, NEW) | no DB mutation — **PASS** |
| 08:46→08:48 | read-only label-gate pre-flight (`probe-labels.sh`, one RR/RO snapshot) | no DB mutation — **PASS** |
| 08:48:49→10:52:08 | `docker run sig-export-build` — `python -m exports build --from-spine --dsn postgresql://sig:…@127.0.0.1:5432/sig --as-of 2026-11-25T08:48:47Z --environment production --out /out/exports/national/2026-11-25T084847Z` (`PGOPTIONS=--work_mem=2GB`, `PYTHONMALLOC=malloc`, `MALLOC_TRIM_THRESHOLD_=65536`) | container created → **refused rc=1** (`CalledProcessError`, tippecanoe `EXIT_NODATA` 110 at `spine_export.py:7457` → `tiles.py:1782`); 0 files local, 0 objects remote |
| 10:56→11:01 | read-only diagnosis capture (tippecanoe EXIT_NODATA reproduction on an empty FeatureCollection — rc=110 verbatim; bucket prefix check) | no DB mutation |
| 11:01:2x→11:01:4x | `gcloud compute instances delete sig-export-gce-5` | RUNNING → **absent**; `instances list` = 0 items; 0 orphan disks |

Unchanged: `sig-export` job (gen 10 declared shape, `Ready`, digest
`…7dd590e8`), bucket policy, IAM, firewall, authorized-networks,
`registry/` (`latest.json` untouched — this leg does not re-cut),
`sources.toml`, the alias table, `licenses.toml`.

## Notes for the record

- **Executing identity:** the VM runs as `sig-export-rt` (its three
  declared bindings — `roles/cloudsql.client`, `secretAccessor` on
  `sig-pg-password`, `storage.objectUser` on `…-sig-restricted` —
  exercised green in pre-flight). `iam.serviceAccountUser` permitted
  under the operator ADC (owner). The image was built locally under the
  operator's Docker Desktop — no artifactregistry grant needed, no AR
  mutation made. No IAM change was made.
- The build runs detached (`nohup` on the VM → `/tmp/export-run.log`,
  memory series `/tmp/export-mem.log` 30 s cadence) so an ssh drop cannot
  kill it — a deviation from attempt 4's attached run in mechanism only;
  the docker invocation is byte-identical bar the image tag, as-of, and
  note string.
- The new `probe-queue-compartment.sh` is kept with the run evidence —
  it exercises the exact call site that ended attempt 4, on the live
  spine's real licence set.
