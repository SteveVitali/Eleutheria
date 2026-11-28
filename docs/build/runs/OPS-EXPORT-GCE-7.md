# OPS-EXPORT-GCE-7 — one-off GCE exec leg for the national export (attempt 7)

- **Spec:** `docs/tickets/493_P37.65a__final-release-cut-crawl-scrub-audit.md`
  (the fresh-export half of `D-P37.65a-1`); attempt 7 of
  `docs/build/runs/OPS-EXPORT-GCE-1.md` / `-2` / `-3` / `-4` / `-5` / `-6` —
  identical recipe, image rebuilt at the fix-merged tip.
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-export-gce-7` at `31b38567` — the merge of
  `r11/ops-export-gce-6` (attempt-6 ledgers + probes) and the blocker-10 fix
  `4802ed0e`; worktree `/private/tmp/sig-export-gce7`. Verified at leg start
  (`git merge-base --is-ancestor <c> HEAD`): `b5a3b394` (SIG-UI-111 labels),
  `f43fdbf9` (SIG-LIC-004a queue compartment), `920b9539` (tippecanoe
  EXIT_NODATA empty-emit gate), `4802ed0e` (PROV-O bound-source Agent union) —
  the image carries **all four** fixes.
- **Authorization:** operator-signed commit `8bb00c9d` (GATE DECISIONS
  `2026-11-24T18:00Z`, "Export substrate — operator decision: one-off GCE
  exec leg >=64 GiB") — a ONE-OFF export execution on a >=64 GiB GCE host
  under operator ADC, torn down after the run. Still current: same leg,
  seventh attempt.
- **Blocker-10 disposition:** attempt 6 refused at
  `provo.export_lineage` (provo.py:309 `validate_prov_graph`, invoked at
  spine_export.py:7493): `wasAttributedTo` edges are minted for EVERY bound
  `claim_binding_detail` capture, but `lineage.sources` (Agent typing) was
  built only from sites∪freshness sources — `okc_council_statement` has bound
  captures and zero surfaced rows, so its attribution target was untyped.
  `4802ed0e` unions every bound `artifact_source_id` into `source_ids`,
  restoring the docstring invariant "every source the export drew from is a
  prov:Agent".
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`, region/zone
  `us-central1`/`us-central1-a`, ADC `14stevevitali@gmail.com`
  (roles/owner); every gcloud call passed `--project` explicitly.
- **Window:** run 2026-11-25T13:37Z→16:18Z — outside the 03:00Z→06:30Z
  never-band; the Dec monthly freeze (AR-3, 12-06→12-13T12:00Z) does not
  apply. T0 (`14:08:19Z` docker run) and the exit (`16:12:28Z`) are both
  outside it. No window refusal.
- **Evidence:** `docs/build/logs/ops-export-gce-7/` (the gitignored
  subtree): `run-export-on-vm.sh`, `probe-rights.sh`, `probe-labels.sh`,
  `probe-attribution.sh` + `attribution-probe3.py`, `probe-emit-gates.sh`,
  `probe-queue-compartment.sh`, `probe-empty-tiles.sh`, and the NEW
  `probe-prov-agents.sh` + `prov-agents-probe.py` — the exact executed
  drivers beside the captures (no secrets).

## Key difference vs attempt 6 — the image carries the bound-source Agent fix + a seventh probe

Same host class, same invocation, same live spine. The image is rebuilt at
`31b38567` so `_provenance_lineage` unions every bound `artifact_source_id`
into the Agent set instead of failing closed on the first bound-but-unsurfaced
source. A seventh pre-flight (`probe-prov-agents.sh`) proves the restored
invariant **end-to-end on the real code path**: it runs the real
`EXPORT_QUERIES["claim_binding_detail"]` read (same `{PUB_ARTIFACT_GATE}` +
`{CAPTURE_SEAL_GATE}` fragments + seal post-check + `resolve_public_text`
projection `build_raw` applies), feeds all 4,807,600 live rows into the real
`_provenance_lineage` with an EMPTY dataset (worst case: zero sites/freshness
sources, so every bound source must arrive via the `4802ed0e` union), then
calls `provo.export_lineage(fmt="nt")` — the exact call that refused
attempt 6 — so `validate_prov_graph` runs for real.

## Remaining unexercised gates (static scan past :7493, this leg)

Attempt 6 refused at :7493 (`export_lineage` nt). What the tail still holds
after this leg's probe coverage:

- `provenance_jsonld` (:7494–7496) — `export_lineage(fmt="json-ld")` over the
  SAME lineage object → the same `validate_prov_graph` — probe-covered (probe
  7 validated that graph).
- `exclusions` dict (:7499–7514) — pure dict assembly over `site_exclusions` +
  `withdrawn_claims`; no raises.
- `_extended_manifest` (:7516) → `CR.assert_path_documented` (:7748) over
  every artifact path — the one remaining fail-closed raise
  (`UnregisteredResourceError`, column_registry.py:565). Probe-covered for the
  tile path family (probe 6) and the pre-:7493 artifact families were all
  exercised in attempt 6's run; deterministic per emitted path family.
  `by-source/` paths are documented-by-pattern (skipped by design, :7750).
- `SpineExport.write_to` (:1163) → `_sbom.emit_sbom` +
  `downloads.write_integrity_files` — honest-degradation tails (SBOM renders
  from committed `pylock.toml` which rides the image; SHA256SUMS always
  writes; minisign only when `SIG_RELEASE_MINISIGN_SECRET` is provisioned —
  it is not set here, so the export honestly ships unsigned). No fail-closed
  raises.
- `summary()` (:1214) — dict assembly over the built manifest/exclusions.
- Everything at or before :7493 — all six prior probes' gates plus the PROV-O
  emit — passed in the real build last attempt or is probe-covered now.

## Verdict

| leg | verdict |
|---|---|
| prestate `instances list` + `sig-export-gce` disks | 0 items (`00-prestates.txt`) |
| `sig-export` Cloud Run job prestate | gen 10, `Ready`, digest `…7dd590e8`, SA `sig-export-rt` (`00-prestates.txt`) |
| VM create `sig-export-gce-7` | **DONE** — `e2-highmem-8` (8 vCPU / 64,313 MiB) + 32 GiB swap safety net, Debian 12, 200 GB pd-balanced, SA `sig-export-rt` (scopes: cloud-platform), external IP 35.255.162.194 (`03-create.txt`, `04-poststate-instances.txt`) |
| image | **DONE** — fresh local amd64 `docker build --platform linux/amd64` of `31b38567` with `--build-arg SIG_CODE_COMMIT=31b38567…` (carries ALL FOUR fixes: `b5a3b394`, `f43fdbf9`, `920b9539`, `4802ed0e`); exported config `sha256:a636e3d7aef0…` == VM loaded image id; OCI `revision` label + `SIG_CODE_COMMIT` env both read back `31b3856709517ec3ef41398beaadac06a89b7b55` on the VM; tagged `sig-api-export:gce7-31b38567` (`01-image-build.log`, `06-image-transfer.txt`, `07-image-id-chain.txt`) |
| cloud-sql-proxy + secret + DB | **OK** — proxy v2.18.3 on `127.0.0.1:5432` under the VM SA; `sig-pg-password` fetched via Secret Manager REST (env-only) |
| pre-flight 6 — empty-compartment tiles | **PASS** — `probe-empty-tiles.sh` in the real image: tippecanoe v2.79.0 on PATH, `tippecanoe_available()=True`; all-`geometry:null` emit renders pure-python (416-byte archive, `points:0`); located emit takes the real tippecanoe path end-to-end; `assert_path_documented` resolves the tiles path family (`08-empty-tiles-probe.txt`) |
| pre-flight 1 — licence gate | **PASS** — `probe-rights.sh`: every effective rights record resolves inside the registry (`09-rights-probe.txt`) |
| pre-flight 2 — E2-12 attribution | **PASS — 0 violations** — `attribution-probe3.py` replica over 223 distinct effective (source → rights_record) pairs (`10-attribution-probe.txt`) |
| pre-flight 3 — emit gates | **PASS** — `probe-emit-gates.sh`: every effective record maps to a compartment; 14 compartments each licence-pure; 0 `row_rights` E2-12 violations; 1 licence-refused record (drops to exclusions — not a build fail) (`11-emit-gates-probe.txt`) |
| pre-flight 4 — queue compartment | **PASS** — `probe-queue-compartment.sh`: the attempt-4 union → `web` (no raise); the 14-member all-effective union → `web`; each single licence → its real compartment; bare `compartment_for_license` still raises on the union (`12-queue-compartment-probe.txt`) |
| pre-flight 5 — SIG-UI-111 labels | **PASS** — `probe-labels.sh` (real `_label_registry` + `freeze_hashes` + `check_unique_labels`, one RR/RO snapshot): 260,822 entities in 111.6 s; both incident `dot_511_wa` cameras emit tier-0 `camera_name` labels; 207,322 `#`-disambiguated, 2,995 withheld (`13-labels-probe.txt`) |
| pre-flight 7 — PROV-O bound-source Agent (NEW) | **PASS** — `probe-prov-agents.sh` on the real code path: 4,807,600 `claim_binding_detail` rows → 220 distinct bound `artifact_source_id`; `okc_council_statement` bound AND minted `prov:Agent`; `bound − agents = ∅`; `export_lineage(fmt="nt")` → `validate_prov_graph` **passed** — the exact attempt-6 refusal call — 1,269,898 bytes of n-triples, 688 captures (`14-prov-agents-probe.txt`, ~17min — the real binding read is heavy, not the ~5min of the other probes) |
| `python -m exports build --from-spine` (as-of `2026-11-25T14:08:17Z` → `exports/national/2026-11-25T140817Z/`) | **SUCCESS — exit rc=0 at 16:12:28Z, wall-time 124.1min** (docker run 14:08:19Z → exit 16:12:28Z). **The `4802ed0e` PROV-O fix HELD** — the build passed the attempt-6 refusal point (:7493 `export_lineage`/`validate_prov_graph`), serialised `provenance.ttl` (1,319,754 bytes — the probe's empty-dataset dry-run predicted 1,269,898; the real lineage is larger, as expected) + `provenance.jsonld`, ran the loud `exclusions` dict (0 refused slices / 0 refused rows / 0 withdrawn), `_extended_manifest` incl. `CR.assert_path_documented` over every artifact path (no `UnregisteredResourceError`), and `write_to` → `sbom.cdx.json` emitted (242,618 bytes — pylock.toml resolved) + `SHA256SUMS` (150,279 bytes; unsigned — `SIG_RELEASE_MINISIGN_SECRET` not provisioned, honest). Summary: **1,419 artifacts, 15 compartments** (incl. `metadata` + `web`), all 14 `sig.map-tiles/2` pmtiles + `web/tiles/index.json`. Output: **1,422 files, 4.3 GB**. `web/evaluation.json` parses — `sig.resolution-eval/1`, real metrics (Cohen's κ 0.714, auto-write precision floor 0.980), `provisional: true`, `deferral: D-R6.1-EVAL`. Peaks: **50.66 GiB container** / host `mem_used` 53,219 MB; swap 0 (`16-export-run-log.txt`, `17-mem-series.txt`) |
| upload → `gs://zeta-medley-508121-u7-sig-restricted/exports/national/2026-11-25T140817Z/` | **DONE** — `gcloud storage rsync -r` from the VM 16:16:22Z→16:16:4xZ @320.6MiB/s; **1,422 objects** under the prefix (== local file count); `web/evaluation.json` read back from the bucket parses OK; prefix listing shows every compartment dir + manifest/SHA256SUMS/provenance/sbom (`18-bucket-rsync.txt`, `19-bucket-poststate.txt`) |
| `export.sh --apply fetch` / `D-P37.65a-1` re-cut | **ready for the parent** — staged prefix `gs://zeta-medley-508121-u7-sig-restricted/exports/national/2026-11-25T140817Z/`; `export.sh --apply fetch` syncs `exports/national/` down for the re-cut per `99018e1b` |
| teardown | **DONE** — `sig-export-gce-7` deleted 16:17:0xZ; poststate `instances list` = 0 items; `compute disks list` = **0 orphan disks** (`20-teardown.txt`) |
| `sig-export` Cloud Run job poststate | **unchanged** — gen 10, `Ready`, digest `…7dd590e8` (prestate == poststate, `21-job-poststate.txt`) |

## Mutations performed (exact receipts)

| utc | mutation | prestate → poststate |
|---|---|---|
| 13:41:07 | `gcloud compute instances create sig-export-gce-7` (e2-highmem-8, debian-12, 200 GB, SA `sig-export-rt`, scopes cloud-platform, label `purpose=sig-export-gce-7`) | 0 instances → RUNNING (`03-create.txt`, `04-poststate-instances.txt`) |
| 13:41:23→13:42 | VM setup (no GCP mutation): `docker.io` + `jq` apt; `cloud-sql-proxy` v2.18.3 binary (`05-vm-setup.txt`) | — |
| 13:41:50→13:42:44 | image `docker save` → ssh `docker load` → `sig-api-export:gce7-31b38567` | image absent on VM → present (config `a636e3d7aef0…`) (`06-image-transfer.txt`, `07-image-id-chain.txt`) |
| 13:43:28 | read-only tile pre-flight (`probe-empty-tiles.sh`, no DB) | no DB mutation — **PASS** |
| 13:43:39 | read-only licence-gate pre-flight (`probe-rights.sh`) | no DB mutation — **PASS** |
| 13:44:31 | read-only E2-12 pre-flight (`probe-attribution.sh` → `attribution-probe3.py`) | no DB mutation — **PASS, 0 violations** |
| 13:44:5x | read-only emit-gates pre-flight (`probe-emit-gates.sh`) | no DB mutation — **PASS** |
| 13:45:2x | read-only queue-compartment pre-flight (`probe-queue-compartment.sh`) | no DB mutation — **PASS** |
| 13:45:5x→13:48 | read-only label-gate pre-flight (`probe-labels.sh`, one RR/RO snapshot) | no DB mutation — **PASS** |
| 13:48:33→14:05:5x | read-only PROV-O pre-flight (`probe-prov-agents.sh`, NEW — one RR/RO snapshot, 4.8M binding rows) | no DB mutation — **PASS** |
| 14:08:19→16:12:28 | `docker run sig-export-build` — `python -m exports build --from-spine --dsn postgresql://sig:…@127.0.0.1:5432/sig --as-of 2026-11-25T14:08:17Z --environment production --out /out/exports/national/2026-11-25T140817Z` (`PGOPTIONS=--work_mem=2GB`, `PYTHONMALLOC=malloc`, `MALLOC_TRIM_THRESHOLD_=65536`) | container created → **rc=0**; 1,422 files / 4.3 GB local |
| 16:16:22→16:16:4x | `gcloud storage rsync -r /export-out/…/2026-11-25T140817Z gs://…-sig-restricted/exports/national/2026-11-25T140817Z/` | prefix absent → **1,422 objects** @320.6MiB/s (`18-bucket-rsync.txt`, `19-bucket-poststate.txt`) |
| 16:17:0x | `gcloud compute instances delete sig-export-gce-7` | RUNNING → **absent**; `instances list` = 0 items; 0 orphan disks (`20-teardown.txt`) |

Unchanged: `sig-export` job (declared shape, digest `…7dd590e8`), bucket
policy, IAM, firewall, authorized-networks, `registry/` (`latest.json`
untouched — this leg does not re-cut), `sources.toml`, the alias table,
`licenses.toml`.

## What this leg proved

1. **`4802ed0e` held end-to-end — blocker 10 is CLOSED.** The build passed
   `spine_export.py:7493` (`export_lineage` → `validate_prov_graph`), the
   exact call that refused attempt 6, and serialised a real
   `provenance.ttl` (1.32 MB nt + the JSON-LD twin). Every bound source —
   including `okc_council_statement`, bound-but-unsurfaced — was minted a
   `prov:Agent`, so no `wasAttributedTo` edge targeted an untyped node.
   Probe 7 proved the same invariant on the live 4.8M-row binding set
   pre-flight, on the real code path, in the real image.
2. **All seven pre-flights predicted their gates.** Six reused probes plus
   the new set-difference/lineage probe — every one passed, and the build
   confirmed them: licence gate, E2-12 attribution, emit compartments,
   queue-shard union, SIG-UI-111 labels, empty-emit tiles, bound-source
   Agents. The full export pipeline has now run green end-to-end for the
   first time in this chain (attempts 1–6 each surfaced one deterministic
   gate deeper; this leg surfaced none — the tail held).
3. **The whole post-`:7493` tail ran for real for the first time:**
   `exclusions` (0/0/0), `_extended_manifest` + `CR.assert_path_documented`
   over all 1,419 artifacts, `write_to` → `sbom.cdx.json` (pylock resolved,
   242,618 bytes) + `SHA256SUMS` (150,279 bytes, unsigned — honest absence
   of `SIG_RELEASE_MINISIGN_SECRET`), and `summary()` (1,419 artifacts / 15
   compartments). No remaining never-exercised gate exists in the
   `build --from-spine` path.
4. **Objects exist.** 1,422 files / 4.3 GB under
   `gs://zeta-medley-508121-u7-sig-restricted/exports/national/2026-11-25T140817Z/`
   — `web/evaluation.json` reads back clean (`sig.resolution-eval/1`,
   provisional, deferral `D-R6.1-EVAL`). `D-P37.65a-1`'s fresh-export half
   now has real bytes to `export.sh --apply fetch` and re-cut on.
5. **Substrate confirmed a seventh time:** e2-highmem-8 suffices —
   50.66 GiB container / 53,219 MB host peak, swap 0.

## Notes for the record

- **Executing identity:** the VM ran as `sig-export-rt` (its three declared
  bindings — `roles/cloudsql.client`, `secretAccessor` on `sig-pg-password`,
  `storage.objectUser` on `…-sig-restricted` — all exercised green:
  proxy + secret for the build, `storage rsync` for the upload).
  `iam.serviceAccountUser` permitted under the operator ADC (owner). The
  image was built locally under the operator's Docker Desktop — no
  artifactregistry grant needed, no AR mutation made. No IAM change was made.
- The build ran detached on the VM (script stdout → `/tmp/export-run.log`,
  memory series `/tmp/export-mem.log` at 30 s cadence) so an ssh drop could
  not kill it — same posture as attempts 5–6.
- The new `probe-prov-agents.sh` + `prov-agents-probe.py` are kept with the
  run evidence — they exercise the exact `EXPORT_QUERIES["claim_binding_detail"]`
  read + `_provenance_lineage` + `export_lineage`/`validate_prov_graph` call
  chain that ended attempt 6, in the real image, against the live spine
  (read-only, RR/RO snapshot). Caveat for future runs: the probe is heavier
  than its siblings (~17 min — it materialises all 4.8M binding rows and
  the full prov graph; the other probes are ~seconds-to-2min each).
- `D-P37.65a-1` stays OPEN until the parent runs `export.sh --apply fetch`
  and the re-cut verifies — this leg delivered the objects; the
  ledger/spec-side closeout is the parent's.

