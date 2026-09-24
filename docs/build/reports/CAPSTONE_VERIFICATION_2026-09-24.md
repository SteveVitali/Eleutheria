# CAPSTONE VERIFICATION — whole build after the national launch (P30.4 / GO-LIVE.4), 2026-09-24

**Branch:** `devin/p30-4-post-launch-closeout`, stacked on `devin/p30-3-national-export-and-public-cutover` @
`065d8aa`. **Docker:** 29.1.3 (daemon reachable). **Date:** 2026-09-24. The format follows the round-1
`CAPSTONE_VERIFICATION.md`, which is left unchanged.

This is the final composed verification of the whole chain (rows 1–141), run as one unit after the public
launch: the local composed build (spine → export → web → acceptance, over a real PG18+PostGIS container) plus
the hosted system that is actually live. Nothing was merged, tagged or pushed to `main`. There were no spine
writes: every hosted statement ran as `sig` in a read-only session. No source was flipped and no human gate
was ticked.

## 1. Local composed verification (the build as one unit)

| check | command | result |
|---|---|---|
| full gate, DB tests fail-loud | `SIG_REQUIRE_DB_TESTS=1 make check` (lint → format-check → typecheck → test → verify-gen) | **exit 0**: ruff clean, format clean, mypy clean; **3,923 passed / 3 skipped / 0 failed** (139.5 s, first run); re-run on the final tree after all P30.4 edits: **3,924 passed / 3 skipped / 0 failed** (+1 = the ADR-107 parametrized ADR-policy test); `verify-gen` clean (`pylock.toml` + `ontology/generated` unchanged) |
| claim-spine DB suite | `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db` | **209 passed / 0 failed** (PG18+PostGIS testcontainer) |
| composed e2e | `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -rxXs` | **16 passed / 0 failed / 0 xfailed / 0 xpassed**. No seam is left as an `LD-` xfail, and no assertion was loosened or xfail flipped by this ticket. |
| web gate | `npm --prefix web run check` (typecheck → unit → build → licences → e2e) | **exit 0**: 23 files / **210 unit** passed; build + licence check green; **246 Playwright e2e** passed (incl. WCAG 2.2 AA + zero-JS content pages) |
| coverage matrix | `uv run python docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv` | **677 rows OK** (exit 0). Verdicts: MET 529 · MET-DIFFERENTLY 77 · PARTIAL 52 · MISSING 7 · AT-RISK-INTEGRATION 5 · N/A-RATIONALE 7 |
| build-memory + docs | `make docs-check` (repo docs + agent docs + build-memory) | green; 1 pre-existing warning (BM-ADR-04: the canonical `DECISION_MEMO.md` has no ADR appendix; also present at the base) |
| backlog / spec / ADRs | `check_backlog.py`, `build_backlog_md.py --check`, `check_spec_src.py`, `tests/unit/test_policy_adrs.py` | green (deferral homes 39/39; 677 requirement ids; 108 ADR-policy tests) |

**The 3 skips** are all env-gated: the live-API acceptance path (`SIG_STAGING_API_URL` unset; run by
`run_okc.sh`) and the two secrets leak checks (`SIG_GCP_PROJECT` / `SIG_*` unset).

**Armed leak check (honest red):** with `SIG_GCP_PROJECT` set, `tests/connectors/test_secrets.py::test_gcp_project_id_is_env_resolved_not_committed`
**fails**. The real project id is committed literally in 45 tracked files at the base (build-memory run
ledgers, PR bodies, LEDGER, BUILD_INDEX, ADR-098, DEFERRALS). This problem predates P30.4, and P30.4 added
no new occurrence. It is recorded as **D-P30.4-4** (it needs a policy decision) rather than fixed by
rewriting append-only history.

## 2. Hosted verification (the live system)

- **Cloud SQL scale-down (ADR-107):** `sig-pg` `db-custom-2-8192` → **`db-custom-1-3840`**, patched `--quiet`
  17:04:04Z → `RUNNABLE` 17:09:02Z. Read-latency probe before/after: point reads unchanged (54–108 ms, mostly
  round-trip time); full scans 3.2 → 3.4 s and 3.5 → 3.9 s.
- **`sig-api` after the restart:** every DB-backed endpoint returned 500 (`/v1/coverage/national`, `/v1/crosswalk`, `/v1/contradiction`; `/v1/changes`
  makes no query and stayed 200), because the connection was stale (**D-P30.4-1**).
  It was recycled on its pinned digest (`sig-api-00004-jdj`, `sha256:cc680111…`) and is now green. A brief
  (~1–2 min) revision `sig-api-00003-ffl` served the newer `:latest` image before the digest was re-pinned
  (ADR-107 §5).
- **`probe-hosted`** (17:12:19Z): **7 of 7 ok**: `sig-api-root`, `sig-api-coverage-okc`, `sig-web-root`,
  `sig-public-{okc,france,national}-manifest`, `sig-pg-cloudsql`. Web-only runs against both origins
  (surveillancegraph.org and run.app) were also green.
- **Public site:** both origins 200. Headline *"227998 resolved sites (from 230330 observation-level
  records; dedup ratio 0.010)"* + the PROVISIONAL disclosure; 0 `<script>` on `/`; `/map/points.json` 200
  (17,143,416 B); `www` → 301 apex; DoH apex → `136.81.80.102`; TLS valid to 2026-12-22, `sig-web-cert`
  ACTIVE. The site served 200 during the DB restart (`/dossier/ps/` at 17:04:58Z), and `sig-web` logged no
  5xx.
- **Spine (read-only):** claims **2,304,784** (unchanged since the export watermark); `pg_stat`
  `n_tup_upd`/`n_tup_del` = 0 on every spine table (sqitch's own `changes`/`dependencies` registry aside); claims with `object_entity` = **0**; OSM entities
  154,528; contradictions 1; coverage records 118; relationship edges 0; accountability events 0; research
  tasks 1; records_request rows 0; resolution envelopes 1,872,344; camera-site runs 2 (latest
  `camsite:13bedfe7…`, 230,330 → 227,998, κ 0.669); review items 11,625 (review decisions 0); `ingest_run`
  20 of 20 still open.

## 3. Go-live deferral verification (closed by P30.1–P30.3), re-verified live

| row | re-verification (2026-09-24, read-only) | verdict |
|---|---|---|
| D-SOURCES.17-1 | 154,528 `traffic_camera:camreg_osm_surveillance:%` identifiers; claims 2,304,784 ⊇ the 1,214,682 OSM land | DONE, confirmed |
| D-P27.1-1 | settled audit committed (`PUBLIC_SURFACE_AUDIT.md`, `snapshot_status: settled`) | DONE, confirmed |
| D-R6.2-EDGES | `relationship` = 0 rows, as P30.2 recorded (the input gap is D-P30.2-2) | DONE (materializer ran; 0 is the honest result) |
| D-R6.3-CONTRADICTIONS | `contradiction` = 1 (OKC 299 vs 190), shown live | DONE, confirmed |
| D-R6.4-COVERAGE | `coverage_record` = 118 (117 + the COVERAGE-RESOLVED-01 re-measure) | DONE, confirmed |
| D-R6.5-SURFACE | live headline + `coverage.json` materialized numbers on both origins | DONE, confirmed |
| D-R6.6-ACCOUNTABILITY | `accountability_event` = 0, as recorded (D-P30.2-2) | DONE (materializer ran; 0 is the honest result) |
| D-R7.2-DETECTORS | `research_task` = 1; `records_request` = 0 (nothing sent) | DONE, confirmed |
| D-P27.4-1 | public `manifest.json` release `sig-2026-09-24-bd01cb94`, 128 artifacts, `LICENCES.json` 14 single-licence compartments | DONE, confirmed |
| D-P27.8-1 | both origins serve the national release; `probe-hosted` green | DONE, confirmed |
| D-P30.2-3 | `resolution` = 1,872,344; `camera_site_run` `camsite:13bedfe7…` = 227,998 of 230,330 | DONE, confirmed |

All eleven are still DONE. None was reopened.

## 4. The remaining OPEN rows and `projectStatus` (BM-TAIL-03)

Every OPEN/PARTIAL row now names an owner, a precise blocker and a landing (`DEFERRALS.md` § "P30.4 sweep").
- **Still open by design:** D-R7.2-SEND (operator-gated; nothing sent), D-P21.7-1 (HG-08; `registered=false`,
  push refused exit 3), D-P30.3-COUNSEL (no written opinion), D-R6.1-EVAL (first-principles half).
- **D-R7.3-BREADTH** was **not run**. All 8 sources have no `CONNECTOR_FOR_SOURCE` entry (verified; the live
  run stops with "no connector known" before any socket). Wiring them is new connector code, and the hosted
  land is a spine write; neither is closeout work. It stays OPEN with that single, exact blocker.
- **New:** D-P30.4-1 (API reconnect), D-P30.4-2 (bounded search), D-P30.4-3 (entity-creation race, from
  ENTITY-RACE-01), D-P30.4-4 (armed leak check).

**BM-TAIL-03 evaluation**, for `projectStatus: DONE`. This uses the four-part rule in the build-memory layout
(BM-TAIL-03). The contract paraphrases condition 3 more loosely ("a landing *or a precise recorded
blocker*"), and the result is the same under either reading, because condition 4 fails on its own:

1. **The GATE-ACCEPT-style readout is signed: no.** `docs/build/readouts/ACCEPT-R8.md` is prepared and is
   **pending the operator's signature**. This alone blocks `DONE`.
2. Every chain row landed or consciously skipped: **yes** once P30.4 lands. Row 87 (P24.9 GATE-ACCEPT, a
   marker recorded on 2026-09-13) had no BUILD_INDEX row, so the P30.4 close commit adds a retro row.
3. BUILD_INDEX complete: **yes** after the close commit's rows 87 (retro) and 139.
4. No OPEN deferral without a landing: **met only under the loose reading.** Every OPEN row names a precise
   blocker (the sweep). But **19 engineering rows** (D-SOURCES.12-1, D-P27.5-1, D-R7.3-BREADTH,
   D-P30.1-1/-2, D-P30.2-1/-2, D-P30.2a-1/-2, D-P30.2b-1/-2/-3, D-P30.3-1/-2/-3, D-P30.4-1/-2/-3/-4) land only
   on a backlog home: BL-055 (landing `P25.1`, already past), BL-056 (`P27+`) or BL-057 (`P28+`). No
   scheduled chain row owns them. D-P30.4-4 also needs an operator policy decision first. Under the strict
   rule ("a landing"), condition 4 fails too.

→ **`projectStatus` stays `IN-PROGRESS`.** The rule is not met: condition 1 fails outright, and condition 4 fails under the strict reading. P30.4 does not sign
anything for the operator and does not flip an OPEN row to DONE. The GO-LIVE tail is complete
(`nextTicket` = the manifest-exhausted sentinel). What remains is either operator action or a new planning
round that schedules the engineering backlog.

## 5. ACCEPTED deviations (for operator sign-off)

See `docs/build/readouts/ACCEPT-R8.md`: R8-1 the combined `/map/points.json` (already operator-accepted
2026-09-24); R8-2 ADR-102 (the temporary scale-up, now ended); R8-3 ADR-103 (in-GCP least-privilege
materialization); R8-4 ADR-104 (camera predicate registry choices); R8-5 ADR-105 (geospatial ER, κ 0.669
< 0.70, LLM as suggester only, PROVISIONAL); R8-6 ADR-106 (share-alike publication on operator-reported
counsel clearance); R8-7 ADR-107 (steady-state `db-custom-1-3840`, new). The coverage matrix
`MET-DIFFERENTLY` count is unchanged at 77.
