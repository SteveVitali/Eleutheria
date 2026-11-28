# OPS-EXPORT-GCE-6 — one-off GCE exec leg for the national export (attempt 6)

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (the fresh-export half of `D-P37.65a-1`); attempt 6 of
  `docs/build/runs/OPS-EXPORT-GCE-1.md` / `-2` / `-3` / `-4` / `-5` — identical
  recipe, image rebuilt at the fix-merged tip.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-gce-6` at `8ef72965` — a merge of
  `r11/ops-export-gce-5` (attempt-5 ledgers + probes) and
  `r11/ops-siglic004a-fix` (`920b9539`); worktree `/tmp/sig-export-gce6`.
  Verified at leg start (`git merge-base --is-ancestor <c> 8ef72965`):
  `b5a3b394` (SIG-UI-111 labels), `f43fdbf9` (SIG-LIC-004a queue
  compartment), `920b9539` (tippecanoe EXIT_NODATA empty-emit gate) — the
  image carries **all three** fixes.
- **Authorization:** operator-signed commit `8bb00c9d` (GATE DECISIONS
  `2026-11-24T18:00Z`, "Export substrate — operator decision: one-off GCE
  exec leg >=64 GiB") — a ONE-OFF export execution on a >=64 GiB GCE host
  under operator ADC, torn down after the run. Still current: same leg,
  sixth attempt.
- **Blocker-9 disposition:** attempt 5 refused at
  `render_compartment_sites_pmtiles` (tiles.py:1782, invoked at
  spine_export.py:7457): the `derived_facts` compartment's `sites.geojson`
  emits zero located features (its document/statute/inventory sources carry
  `geometry:null`), tippecanoe exits 110 (`EXIT_NODATA`) on a zero-feature
  FeatureCollection, and `check=True` raised. `920b9539` gates the
  tippecanoe invocation on a non-empty emit
  (`if tippecanoe_available() and emit_features:`): an empty collection
  takes the pure-python path, which already declares the layer + licence
  for empty collections (the committed empty-archive contract) — the tiles
  index then shows the compartment honestly at `points:0`.
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`, region/zone
  `us-central1`/`us-central1-a`, ADC `14stevevitali@gmail.com`
  (roles/owner); every gcloud call passed `--project` explicitly.
- **Window:** run 2026-11-25T11:07Z→13:31Z — outside the 03:00Z→06:30Z
  never-band; the Dec monthly freeze does not apply. T0 (`11:16:10Z`) and
  the in-run refusal (`~13:23:4xZ`) are both outside it. No window refusal.
- **Evidence:** `docs/build/logs/ops-export-gce-6/` (the gitignored
  subtree): `run-export-on-vm.sh`, `probe-rights.sh`, `probe-labels.sh`,
  `probe-attribution.sh` + `attribution-probe3.py`, `probe-emit-gates.sh`,
  `probe-queue-compartment.sh`, and the NEW `probe-empty-tiles.sh` — the
  exact executed drivers beside the captures (no secrets).

## Key difference vs attempt 5 — the image carries the empty-emit tile gate

Same host class, same invocation, same live spine. The image is rebuilt at
`8ef72965` so the P35.52 per-compartment `sig.map-tiles/2` emit skips
tippecanoe on an empty FeatureCollection instead of dying on its
`EXIT_NODATA`. A sixth pre-flight (`probe-empty-tiles.sh`) exercises that
exact path **in the container where tippecanoe is really on PATH** —
stronger than the committed test's monkeypatch — plus the never-yet-run
tippecanoe success path on a located collection and the SIG-TRANSP-016
path gate on the first-emitted `web/tiles/*-sites.*.pmtiles` family.

## Remaining unexercised gates (static scan past :7457, this leg)

`derived_facts` was the **first** compartment rendered in attempt 5 — no
archive, index entry, or anything past `subprocess.run` has ever executed
in a real build. What the tail still holds after this leg's probe coverage:

- `annotate_pmtiles` / `check_tile_sizes` / `tippecanoe_version` on the
  tippecanoe path — **now probe-covered** (the located-emit half of
  `probe-empty-tiles.sh` ran them for real on the VM image).
- `check_tile_sizes` → `TileSizeLimitExceeded` — data-driven loud gate on
  stored tile bytes; a per-record point tile is far under the limit, and
  the same check runs on the pure-python path (probe-covered on the empty
  archive). Not independently replicable on real data short of the build.
- `provo.export_lineage` → `ProvValidationError` (provo.py:281–315) —
  PROV-O typing checks over `_provenance_lineage` output built from real
  `claim_binding_detail`; not cheaply replicable (needs the full
  build_raw). Untested tail, exercised for the first time this run.
- `CR.assert_path_documented` (spine_export.py:7750) over every artifact
  path in `_extended_manifest` — **probe-covered** for the new
  `web/tiles/derived_facts-sites.<sha>.pmtiles` family (resolves to
  `sites`) and `web/tiles/index.json` (document-exempt, `None`); the
  attempt-5 ledger verified every other emitted path family.
- `SpineExport.write_to` → `_sbom.emit_sbom` +
  `downloads.write_integrity_files` — honest-degradation tails (SBOM
  skips honestly when no lock resolves; SHA256SUMS always writes; signing
  only when `SIG_RELEASE_MINISIGN_SECRET` is provisioned — it is not set
  here, so the export honestly ships unsigned). No fail-closed raises.
- `_queue_shard_compartment`, `CR.assert_documented` ×4,
  `mech_eval_lint_errors` / `quality_page_lint_errors`,
  `emit_source_slice` / `emit_dossier_slice` `DownloadError`s,
  `attribution_txt` empty-payload refusal — all at or **before** the
  attempt-5 refusal point; all passed in the real build last attempt or
  are probe-covered.

## Verdict

| leg | verdict |
|---|---|
| prestate `instances list` | 0 items (`01-prestate.txt`) |
| `sig-export` Cloud Run job prestate | 4cpu/16Gi, digest `…7dd590e8`, SA `sig-export-rt` (`00-job-prestate.txt`) |
| VM create `sig-export-gce-6` | **DONE** — `e2-highmem-8` (8 vCPU / 64,313 MiB) + 32 GiB swap safety net, Debian 12, 200 GB pd-balanced, SA `sig-export-rt` (scopes: cloud-platform), external IP 34.122.27.156 (`02-create.txt`, `03-poststate-instances.txt`) |
| image | **DONE** — fresh local amd64 `docker build` of `8ef72965` with `--build-arg SIG_CODE_COMMIT=8ef72965…` (carries ALL THREE fixes: `b5a3b394` SIG-UI-111, `f43fdbf9` SIG-LIC-004a, `920b9539` tippecanoe-empty-emit); local manifest `sha256:09c5edb0f7d5…`, config `sha256:5a29185cb3dc…` == VM loaded image id; OCI `revision` label reads back `8ef72965528b77a0d340227d05ff710da4dae34c` on the VM; tagged `sig-api-export:gce6-8ef72965` (`04-image-build.log`, `05-image-transfer.txt`, `06-image-id-chain.txt`) |
| cloud-sql-proxy + secret + DB | **OK** — proxy v2.18.3 on `127.0.0.1:5432` under the VM SA; `sig-pg-password` fetched via Secret Manager REST (env-only) |
| pre-flight 1 — licence gate | **PASS** — `probe-rights.sh`: 232 distinct effective rows, every record inside the registry (`decp_fr` effective `etalab-2.0`) (`07-rights-probe.txt`) |
| pre-flight 2 — E2-12 attribution | **PASS — 0 violations** — `attribution-probe3.py` replica over 223 distinct effective (source → rights_record) pairs (`08-attribution-probe.txt`) |
| pre-flight 3 — emit gates | **PASS** — `probe-emit-gates.sh`: every effective record computes a licence that maps to a compartment; 14 compartments each licence-pure; 0 `row_rights` E2-12 violations; 1 licence-refused record (drops to exclusions — not a build fail) (`09-emit-gates-probe.txt`) |
| pre-flight 4 — queue compartment | **PASS** — `probe-queue-compartment.sh`: the attempt-4 union `LicenseRef-DerivedFacts-Citations AND LicenseRef-PublicRecord-FactualCompilation` → `web` (no raise); the 14-member all-effective union → `web`; each single licence → its real compartment; bare `compartment_for_license` still raises on the union (`09b-queue-compartment-probe.txt`) |
| pre-flight 5 — SIG-UI-111 labels | **PASS** — `probe-labels.sh` (real `_label_registry` + `freeze_hashes` + `check_unique_labels`, one RR/RO snapshot): 260,822 entities in 114.3 s; both incident `dot_511_wa` cameras emit tier-0 `camera_name` labels; 207,322 `#`-disambiguated, 2,995 withheld (`10-labels-probe.txt`) |
| pre-flight 6 — empty-compartment tiles (NEW) | **PASS** — `probe-empty-tiles.sh` in the real image: tippecanoe v2.79.0 **on PATH** and `tippecanoe_available()=True`; an all-`geometry:null` `derived_facts` emit renders **pure-python** (416-byte real PMTiles archive, `sites` layer + `LicenseRef-DerivedFacts-Citations` declared, `points:0`) — tippecanoe never invoked, no rc=110; `tiles_index_entry` records `points:0`; `assert_path_documented` maps `web/tiles/derived_facts-sites.<sha>.pmtiles` → `sites` and `web/tiles/index.json` → document-exempt; a 2-point located emit takes the **real tippecanoe path** end-to-end (`annotate_pmtiles` + `check_tile_sizes` + `tippecanoe_version`) — 4,932-byte archive (`07-empty-tiles-probe.txt`) |
| `python -m exports build --from-spine` (as-of `2026-11-25T11:16:05Z` → `exports/national/2026-11-25T111605Z/`) | **REFUSED — exit 1 at the PROV-O lineage serialisation (`ProvValidationError`)** after ~131.9 min (docker run 11:16:10Z → 13:28:04Z; traceback raised ~13:23:4xZ, ~4.5min interpreter teardown). **The 920b9539 tile fix HELD end-to-end** — the build passed the attempt-5 refusal point (:7457, ~123min), completed the whole per-compartment `sig.map-tiles/2` loop (derived_facts rendered empty→pure-python, no rc=110), then refused ~36 source-lines deeper at :7493 in `provo.export_lineage` → `validate_prov_graph`: `prov:wasAttributedTo must relate an Entity to an Agent: prov/capture/01a0a5da-… → prov/source/okc_council_statement`. The named row: a capture attributed to a source that produced **zero published sites and zero freshness rows** in this export — `lineage.sources` (Agent typing) is built only from sites∪freshness while `lineage.captures` covers every bound `evidence_capture`; the untyped `wasAttributedTo` target fails the Entity→Agent check. Peaks: **50.78 GiB container** / host `mem_used` 53,202 MB; swap untouched. **Zero files, zero objects** (`09-export-run-log.txt`, `10-mem-series.txt`, `11-blocker10-diagnosis.txt`) |
| upload → `gs://…-sig-restricted/exports/national/<as-of>/` | **not run** — no export output exists; prefix verified absent (`12-bucket-poststate.txt`) |
| `export.sh --apply fetch` / `D-P37.65a-1` re-cut | **not run** — no fresh export; `web/evaluation.json` presence unverifiable |
| teardown | **DONE** — `sig-export-gce-6` deleted 13:31:24Z; poststate `instances list` = 0 items; 0 orphaned `sig-export-gce*` disks (`13-teardown.txt`) |
| `sig-export` Cloud Run job poststate | **unchanged** — gen 10, `Ready`, digest `…7dd590e8` (prestate == poststate, `14-job-poststate.txt`) |

`D-P37.65a-1` remains **OPEN**; this leg ended at an honest STOP — no
export exists to rsync, fetch, or re-cut.

## What this leg proved

1. **`920b9539` held end-to-end.** The licence gate, SIG-UI-111 label
   gate, E2-12 attribution gate, emit-gates set, `_queue_shard_compartment`,
   **and** the new empty-emit tile gate all passed in the real build — the
   run went ~4.5 min / ~36 source-lines *past* attempt 5's refusal point,
   deeper than any prior attempt has ever reached; the whole tile loop
   completed, including the all-unlocated `derived_facts` compartment.
2. **All six pre-flights predicted their gates correctly again** — the new
   `probe-empty-tiles.sh` exercised the exact call site in the real image
   with tippecanoe on PATH (empty → pure-python at points:0; located → the
   real tippecanoe path end-to-end) before the ~2.2-hour build spent
   anything.
3. **Blocker 10 is a SIXTH distinct gate failure — same class as
   blockers 8/9 (code-side, deterministic).** `ProvValidationError` on
   `wasAttributedTo` is uncaught because `lineage.sources` under-covers the
   capture edge set: every bound `evidence_capture` gets an attribution
   edge, but only sites∪freshness sources get the `prov:Agent` typing.
   `okc_council_statement` has bound captures and zero surfaced claims.
   See `11-blocker10-diagnosis.txt` for the full mechanism + fix classes
   (union `source_ids` with `artifact_source_id` — restoring the intended
   "every source the export drew from is an Agent" invariant; the capture
   edge already asserts it).
4. **`validate_prov_graph` did its job** — first real exercise of the
   PROV-O emit, and the fail-closed typing check caught a malformed
   export rather than shipping an invalid `provenance.ttl`.
5. **Substrate confirmed a sixth time:** e2-highmem-8 suffices —
   50.78 GiB container / 53,202 MB host peak, swap 0.

## Blocker 10 — CURRENT (capture→source attribution edge to an untyped node)

`validate_prov_graph` (provo.py:309, invoked via `export_lineage` at
spine_export.py:7493) refused the build. `_provenance_lineage`
(spine_export.py:8002-8006) mints `prov:Agent` types only for sources in
`sites.source_ids ∪ freshness.source_id`; the capture loop mints
`wasAttributedTo` edges for **every** bound `evidence_capture`'s
`artifact_source_id`. `okc_council_statement` has bound captures but zero
published sites/freshness rows — its attribution target is untyped, so
`_kind` → `None` ≠ `Agent` and the graph fails validation. Deterministic:
every build on this spine hits it.

**Why the probes didn't catch it:** the PROV-O graph needs the full
`claim_binding_detail` + shaped dataset — materialised only ~127min into a
real build. A sufficient cheap check for a future attempt: does every
distinct `artifact_source_id` in `claim_binding_detail` appear in the
export's source set (a set-difference spine query — probeable read-only).

**Resume path (operator / next leg):** (1) fix the lineage source set per
`11-blocker10-diagnosis.txt` fix classes (ordinary commit on a fix branch
like `920b9539`'s — union `source_ids` with `artifact_source_id`, plus a
test pinning a capture whose source surfaces nowhere); (2) re-stand a VM —
recipe unchanged, all six probes still pass this spine; (3) same docker
run → `gcloud storage rsync` `/export-out` up → `export.sh --apply fetch`
→ re-cut per `99018e1b`. No spine mutation is involved in this blocker.

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 11:07:28 | `gcloud compute instances create sig-export-gce-6` (e2-highmem-8, debian-12, 200 GB, SA `sig-export-rt`, scopes cloud-platform, label `purpose=sig-export-gce-6`) | 0 instances → RUNNING (`02-create.txt`, `03-poststate-instances.txt`) |
| 11:08:15→11:09 | VM setup (no GCP mutation): `docker.io` + `jq` apt; `cloud-sql-proxy` v2.18.3 binary (`05-vm-setup.txt`) | — |
| 11:09:27→11:10:45 | image `docker save` → ssh `docker load` → `sig-api-export:gce6-8ef72965` | image absent on VM → present (config `5a29185cb3dc…`) (`05-image-transfer.txt`, `06-image-id-chain.txt`) |
| 11:10:5x | read-only tile pre-flight (`probe-empty-tiles.sh`, NEW — no DB) | no DB mutation — **PASS** |
| 11:11:1x | read-only licence-gate pre-flight (`probe-rights.sh`) | no DB mutation — **PASS** |
| 11:12:0x | read-only E2-12 pre-flight (`probe-attribution.sh` → `attribution-probe3.py`) | no DB mutation — **PASS, 0 violations** |
| 11:12:5x | read-only emit-gates pre-flight (`probe-emit-gates.sh`) | no DB mutation — **PASS** |
| 11:13:2x | read-only queue-compartment pre-flight (`probe-queue-compartment.sh`) | no DB mutation — **PASS** |
| 11:13:5x→11:15 | read-only label-gate pre-flight (`probe-labels.sh`, one RR/RO snapshot) | no DB mutation — **PASS** |
| 11:16:10→13:28:04 | `docker run sig-export-build` — `python -m exports build --from-spine --dsn postgresql://sig:…@127.0.0.1:5432/sig --as-of 2026-11-25T11:16:05Z --environment production --out /out/exports/national/2026-11-25T111605Z` (`PGOPTIONS=--work_mem=2GB`, `PYTHONMALLOC=malloc`, `MALLOC_TRIM_THRESHOLD_=65536`) | container created → **refused rc=1** (`ProvValidationError` at `spine_export.py:7493` → `provo.py:309`, `wasAttributedTo` Entity→Agent on `okc_council_statement`); 0 files local, 0 objects remote |
| 13:30:5x | read-only bucket-prefix check (exports/national/2026-11-25T111605Z/ absent) + mem-series capture | no mutation |
| 13:31:0x→13:31:2x | `gcloud compute instances delete sig-export-gce-6` | RUNNING → **absent**; `instances list` = 0 items; 0 orphan disks |

Unchanged: `sig-export` job (declared shape, digest `…7dd590e8`), bucket
policy, IAM, firewall, authorized-networks, `registry/` (`latest.json`
untouched — this leg does not re-cut), `sources.toml`, the alias table,
`licenses.toml`.

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
  kill it — same posture as attempt 5.
- The new `probe-empty-tiles.sh` is kept with the run evidence — it
  exercises the exact call site that ended attempt 5, in the real image
  with tippecanoe on PATH, plus the never-yet-run tippecanoe success
  path and the SIG-TRANSP-016 path gate on the new tiles path family.
