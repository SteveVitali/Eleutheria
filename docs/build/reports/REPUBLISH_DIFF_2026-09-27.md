# Republish diff — re-materialized spine re-export vs the 2026-09-24 launch surface

> **What this is.** The P31.16 (SURFACE.3) pre-gate diff: the national re-export
> `sig-2026-09-27-ce480ab1` — built from the re-materialized hosted spine in one
> `REPEATABLE READ READ ONLY` snapshot — compared field-by-field against
> `docs/build/reports/LAUNCH_RECORD_2026-09-24.md` (`sig-2026-09-24-bd01cb94`).
> **Nothing in this export is published.** It lives only in the private
> restricted bucket. The run pauses here for **HG-11** operator sign-off; the
> publish half (publish, `sig-web` roll, `/map/points.json` retirement, deferral
> flips, R8-1 close) is the RETURN PASS.
>
> Every figure is a named-denominator count at a stated as-of time over an
> append-only spine. None is a population total (§3.1, §32 / SIG-METRIC-008).

## 0. Provenance of both sides

| | launch record | this re-export |
|---|---|---|
| release | `sig-2026-09-24-bd01cb94` | `sig-2026-09-27-ce480ab1` |
| content key | `bd01cb9418b2dfb4…a85082` | `ce480ab1134c178964aaac492395bc78ace7ee01357b2c6f2a1887700c9682c2` |
| as_of snapshot / belief | 2026-09-24 | 2026-09-27 |
| ruleset | `p27.3/1.0.0` | `p27.3/1.0.0` |
| built by | `sig-export-tl4mx` (15:41→15:51Z) | `sig-export-sv49f` (00:53→01:03Z) |
| image | — | `sig-api:export-61701df303c3` pinned `sha256:1cccde1acb63c12f3275c2c730b0e9896e31e5cb21313a1c669856c56ec835bf` |
| snapshot | one `REPEATABLE READ READ ONLY` | one `REPEATABLE READ READ ONLY` |
| location | published (public) | `gs://zeta-medley-508121-u7-sig-restricted/exports/national/2026-09-27T005153Z/` — **private** (anonymous GET → 403; nothing written to `…-sig-public` or `…-sig-web`) |

**Export watermark (spine at snapshot):** **2,423,200 claims** (latest claim
`sys_period` 2026-09-26T10:06:54Z; `pg_stat` upd/del on `claim` = 0/0 —
insert-only), 249,811 entities, camera-site materialization = run 7 of
`camera_site_run`. Launch watermark was 2,304,784 claims / ~247,061 entities —
**+118,416 claims** landed between the two exports (the scheduled Wave-B
connectors kept running, append-only, between launch and this snapshot).

## 1. Headline-number diff (the surfaces that change)

| metric | 2026-09-24 launch | 2026-09-27 re-export | delta |
|---|---|---|---|
| resolved sites (headline) | **227,998** (from 230,330 observation-level records; dedup ratio 0.010) | **223,901** (from 232,625 observation-level records; dedup ratio 0.038) | **−4,097 sites** (−1.8 %), +2,295 records |
| map tier-0 points | 225,105 (`/map/points.json`, 17.1 MB) | 232,625 (`web/map.json`, 59.9 MB — **restricted**, mixed licence) | +7,520 |
| public compartment site rows | 234,699 | 236,994 | +2,295 |
| relationship edges on the surface | **0** (empty state, D-P30.2-2) | **130** `configured_access` edges (131 nodes) | +130 — **new** |
| accountability links | **0** | **200** `accountability_link:has_vendor` derived facts | +200 — **new** |
| contradictions kept visible | 1 open of 1 (OKC 299-vs-190) | **2 open of 2** | +1 |
| reconciliation ratios | 116 | 124 | +8 |
| provenance completeness | 2,280,784 of 2,280,784 published tier-0 claims | **2,423,200 of 2,423,200** | +142,416 of +142,416 |
| negative space (class-scoped `not_researched`) | not emitted (pre-P31.9) | **1,042,395** absence rows (+256 other coverage rows = 1,042,652 `coverage_record`) | **new surface** |
| research queue | 1 task (`conflicting_retention`) | **243,761** tasks | +243,760 — **new surface** |
| freshness | all 178 sources `not-recorded` (D-P30.3-1) | all **178** sources carry real `last_successful_run` / `last_content_change` timestamps | **fixed in the artifact** |
| map tiles | single-z0 placeholder PMTiles (D-P30.3-2) | **12** per-compartment PMTiles z0–z14 built by pinned tippecanoe 2.79.0 | **fixed in the artifact** |
| analytics | not emitted (D-P30.3-3) | `web/analytics/{density_bins,centrality,decision_point,provenance,queue_meta}.json` | **new surface** |
| artifacts | 128 public | **134** in restricted (nothing public) | — |

## 2. The alarming row, stated plainly

**Resolved-site count went DOWN: 227,998 → 223,901 (−4,097, −1.8 %)** while the
observation-level record count went UP (230,330 → 232,625, +2,295) and the dedup
ratio rose 0.010 → 0.038. This is a **clustering revision**, not data loss:

- the launch number came from camera-site run `camsite:13bedfe7…` (run 6 lineage);
  the re-export reflects run 7, a fresh re-clustering over the larger claim set
  (2,304,784 → 2,423,200 claims);
- the new run auto-wrote **8,724 same-device merges** (only tiers whose measured
  holdout precision cleared the published floor) and merged more observations
  per site — hence fewer, denser clusters;
- **33,907** proposed merges still await human review and are not counted;
  0 reviewer rejects, 0 hard-constraint refusals;
- resolution still rests on the **PROVISIONAL** eval (LLM-bootstrapped gold set;
  **D-R6.1-EVAL OPEN**) — the surface disclosure stays verbatim, and the honest
  framing is that the site count is a moving named-denominator number, not a
  population total (SIG-METRIC-008).

Read-back truth check: `camera_site_match` rows 207,499 → 252,512 (+45,013 —
the run's appended match rows; append-only, the old run's rows are untouched).

## 3. New surfaces vs launch (all in the restricted export only)

| surface | launch | re-export |
|---|---|---|
| `web/network.json` | empty state (0 edges) | **130** `configured_access` edges, 131 nodes, all `WEAKLY_SUPPORTED`, each citing evidence claims |
| `sig_graph/sharing_edges.*` | — | **632** claim-level sharing edges (260 `configured_access` + 372 `unclassified`), 5 serialisations |
| `web/research_queue.json` | 1 task | **243,761** tasks (coverage_hole 243,035 · missing_contract 595 · sharing_snapshot_stale 130 · conflicting_retention 1); 0 drafts, 0 sent |
| `web/coverage.json` + `sig_graph/coverage.*` | 116 ratios + counters | **127** metric rows (124 `reconciliation_ratio` + 3 `counted_quantity`) |
| `web/freshness.json` + `sig_graph/freshness.*` | 178 × `not-recorded` | 178 real dated rows (driven by the appended `ingest_run_completion` spine — the P31.2/ADR-109 engine now feeding the surface) |
| `web/dossiers.json` + `dossier_index.json` | — | 55 jurisdiction dossier index entries |
| `web/evidence.json` | — | 255 evidence-artifact references |
| `web/analytics/` (P31.14 family) | not emitted | density_bins (H3 res-3, in `web_mixed` — mixed licence), centrality, decision_point, provenance (W4..W0 tiers), queue_meta |
| `web/tiles/*-sites.pmtiles` | single-z0 | 12 per-compartment z0–z14 archives |
| `web/watch.json` / `web/corrections.json` / `web/leverage.json` | — | emitted (watch + corrections honestly empty; leverage counts 0) |

## 4. Edge + link examples (for the HG-11 review)

- **Edges:** 130 rows, all `access_kind = configured_access`, direction
  `a_to_b`, each `WEAKLY_SUPPORTED` with `evidence_count ≥ 1`. Example: an
  operator entity → `Vigilant Solutions (LEARN)` organisation, evidenced by the
  entity-ref claims landed at P31.6 (ADR-112/113; 33,133 `object_entity`
  claims).
- **Accountability links:** 200 `inference.derived_fact` rows, predicate
  `accountability_link:has_vendor`, rule `accountability_linkage/§13`, each
  naming a vendor organisation and citing its establishing claim ids.
- **Negative space:** 1,042,395 `not_researched` absence rows — the
  class-scoped `(entity_type, connector)` peer-class rule of P31.9/ADR-115, not
  the obsolete ~26.7 M unscoped estimate; plus 223 reconciliation-ratio and
  2 counted-with-denominator coverage records beside them.

## 5. Materializer +0 evidence (every step run twice on the pinned digest)

Image: `sig-api:materialize-61701df303c3` @
`sha256:e0674d95d56560e065857cbde45ad270c4177fa7b5fca5fbd3a2fb592170e268`
(Cloud Build `e3d0c317…`). Every step ran as a `sig-materialize` Cloud Run job
execution next to Cloud SQL as `sig_materialize`, in the prescribed order, each
re-run for +0:

| step | pass 1 (execution) | result | +0 re-run (execution) | +0 result |
|---|---|---|---|---|
| resolution | `sig-materialize-2dhh2` (→17:59Z) | considered 1,977,905 groups; inserted 0 (already settled); resolved 1,976,555 / unresolved 1,350 | `sig-materialize-9g7gz` (→19:42Z) | inserted **0**, skipped_existing 1,977,905 — **+0** |
| camera-sites | `sig-materialize-clsx4` (→19:59Z) | inserted **45,013** new match rows + run row (the 7th run; scheduled-ingest drift since run 6) | `sig-materialize-qrh24` (→20:22Z) | inserted **0**, skipped_existing 45,013 — **+0** |
| edges | `sig-materialize-v62fb` (→20:27Z) | considered 33,133 claims; reconciled 130; inserted 0 | `sig-materialize-th86h` (→20:32Z) | inserted **0**, skipped_existing 130 — **+0** |
| contradictions | `sig-materialize-ng9m8` (→20:41Z) | detected 2; inserted **1** (a second `value_disagreement` from new evidence — honest non-zero, NOT called +0) | `sig-materialize-67bq6` (→20:52Z) | inserted **0**, skipped_existing 2 — **+0** |
| coverage | `sig-materialize-7cl98` (→22:01Z) | considered 1,042,395 absences + 125 metrics; inserted **7,076** | `sig-materialize-xtmgf` (→23:06Z) | inserted **0**, skipped_existing 1,042,520 — **+0** |
| accountability | `sig-materialize-xjzbw` (→23:17Z) | 200 links derived; inserted 0 | `sig-materialize-gxh6b` (→23:24Z) | inserted **0**, skipped_existing 200 — **+0** |
| detect | `sig-materialize-hlmv2` (→23:57Z) | generated 243,761 tasks; wrote 243,760 (1 pre-existing) | `sig-materialize-x92sk` (→00:28Z) | written **0**, skipped_existing 243,761 — **+0** |
| run-completions (ADR-109) | `sig-materialize-wdm2l` (→00:37Z) | rows_read 355, matched 301, appended 0, already_present 301, skipped_live 31, unmatched 23 (reasons listed) | `sig-materialize-sczl9` (→00:44Z) | identical — appended **0**, already_present 301 — **+0** |

Read-back table counts after the batch: `resolution` 2,134,055 ·
`camera_site_match` 252,512 (7 runs) · `relationship` 130 · `contradiction` 2 ·
`coverage_record` 1,042,652 (1,042,395 `not_researched`) ·
`inference.derived_fact` 200 · `research_task` 243,761 · `claim` 2,423,200
(unchanged through the batch — no ingest raced the materializers;
`pg_stat` upd/del on `claim` 0/0).

## 6. Tier restart + `sig-api` ride-through (D-P30.4-1 regression check)

- **A real instance restart happened.** Following the ADR-102 pattern, `sig-pg`
  was scaled `db-custom-1-3840` → `db-custom-2-8192` at 2026-09-26T15:52Z to
  make the materializer batch tractable (first resolution pass measured
  ~255 groups/s on 1-3840 → ~2 h+; P31.13 measured the same). The UPDATE
  operation ran 15:52:05 → 16:01:17Z (postmaster start ~15:59:00Z) — a genuine
  Cloud SQL restart, the first real exercise of the instance-restart path.
- **`sig-api` rode through with NO recycle.** The service stayed on the same
  serving revision `sig-api-00011-wic` (created 2026-09-25T14:55Z — predates the
  restart, still `latestReady` + 100 % traffic after). The DB-backed
  `/v1/coverage/national` answered 200 at every ~30 s probe across the window;
  `pg_stat_activity` showed the `sig-api` backends re-established ~4 s after
  postmaster start (the P31.1 reconnect fix). The request log for
  15:50–16:15Z shows **41 × 200 and exactly 1 × 503** — a single transient
  `/health` blip at 15:58:57Z during the cutover, recovered within seconds.
- **Verdict:** the instance-restart path is now really exercised and `sig-api`
  did not need a recycle — **D-P30.4-1 stays DONE, no regression, not
  reopened.** (Prior proof was the operator-approved backend-kill drill; this
  adds the full-instance-restart observation.)
- **Cost note:** `sig-pg` remains at `db-custom-2-8192` through the pause —
  the publish half (or the operator) should return it to the ADR-107 steady
  state `db-custom-1-3840` after the gate, as the run ledger records.

## 7. Freshness change (D-P30.3-1 export half)

Launch: all 178 sources printed `not-recorded` because every `ingest_run` row
was open (`finished_at` NULL). Re-export: all **178** freshness rows carry real
`last_successful_run` ISO timestamps (177 with `last_content_change`), sourced
from the appended `ingest_run_completion` spine (343 completion rows; the P31.2
backfill's 301 matches plus live completions since). The engine half was DONE at
P31.2; this is the first export that carries it — the public page still shows
`not-recorded` until the publish half, so **D-P30.3-1 stays OPEN**.

## 8. Compartments, licences, separation (unchanged invariants, re-verified)

- 12 data compartments + `metadata` + `web` + `web_mixed`, each artifact with
  exactly one licence; `assert_separated` ran inside the build (the exporter
  refuses mixed-compartment writes — proven at P30.3 by a real refusal).
- Mixed-licence artifacts are tagged AND-licences and stay out of public reach:
  `web/map.json` (59.9 MB, all-12-licence AND-tag) and
  `web/analytics/density_bins.json` land under the restricted path — in this
  run **everything** is restricted anyway.
- `exclusions.json`: `refused_rows 0`, `refused_slices 0` — the fail-closed
  gate had nothing to refuse this snapshot.
- Restricted privacy verified: anonymous GET on the new prefix → **403**;
  `gcloud storage ls` on `…-sig-public/exports/national/` shows **no 2026-09-27
  objects** — zero bytes published.

## 9. Deferral dispositions (annotated, none flipped by this run)

| deferral | state after this run |
|---|---|
| D-P30.2-2 (edges/links surface) | export half now carries 130 edges + 200 links — **stays OPEN** until publish |
| D-P30.3-1 (freshness) | export carries real dates — **stays OPEN** until the page serves them |
| D-P30.3-2 (tiles/compression) | export carries 12 z0–z14 PMTiles — **stays OPEN** until the live map draws them + `sig-web` rolls |
| D-P30.3-3 (analytics) | export carries the analytics family — **stays OPEN** until the pages serve them |
| D-P30.4-1 (API reconnect) | instance-restart path exercised; rode through — **stays DONE** |
| D-P31.5-2 (publication_review_required) | export honours it; org labels unchanged — stays OPEN pending publish |
| D-R6.1-EVAL | **OPEN** — provisional-eval disclosure carried verbatim |
| R8-1 (`/map/points.json` deviation) | **ENDING, not closed** — live object untouched; closes at the publish half |

## 10. STOP LINE — HG-11

Done here: measure/plan, full re-materialization (7 steps + run-completions,
each +0-verified), one read-only national snapshot export, this diff summary.

**Not done (explicitly deferred to the post-HG-11 RETURN PASS):** publishing any
object, rolling `sig-web`, retiring live `/map/points.json` (still 200, 17.1 MB,
verified untouched), flipping the surface-half deferrals, closing R8-1, ticking
HG-11. The public surface is byte-for-byte what the launch record describes —
verified 200 on both origins throughout this run.
