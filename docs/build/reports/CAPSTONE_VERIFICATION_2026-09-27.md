# CAPSTONE VERIFICATION — whole build after Round 9 (P31.19 / CLOSE.1), 2026-09-27

**Branch:** `devin/p31-19-round9-closeout`, stacked on `devin/p31-16-rematerialize-reexport-republish` @
`4cc7e13`. **Docker:** 29.1.3 (daemon reachable, so the DB/e2e suites really ran — `SIG_REQUIRE_DB_TESTS=1`).
**Date:** 2026-09-27. The format follows `CAPSTONE_VERIFICATION_2026-09-24.md`, which is left unchanged.

This is the whole-build capstone the Round-9 closeout owes: the local composed build over a real
PG18+PostGIS container, the coverage matrix, the build-memory layout check, a read-only live
re-verification of the public-surface closures Round 9 landed, and the `projectStatus` evaluation under
BM-TAIL-03. Nothing was merged, tagged or pushed to `main`. There were no spine writes (the live probes
are public GETs; the operator's ADC was not used). No source was flipped and no human gate was ticked.

## 1. Local composed verification (the build as one unit)

| check | command | result |
|---|---|---|
| full gate | `make check` (lint → format-check → typecheck → test → verify-gen) | **exit 0**: ruff clean, format clean, mypy clean (259 source files); **4,403 passed / 3 skipped / 0 failed** (218.97 s); `verify-gen` clean (`pylock.toml` + `ontology/generated` byte-identical after regen) |
| claim-spine DB suite, fail-loud | `make test-db` = `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db` | **280 passed / 0 failed** (70.22 s; PG18+PostGIS testcontainer) |
| composed e2e, fail-loud | `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -rxXs` | **16 passed / 0 failed / 0 xfailed / 0 xpassed** (20.86 s). No seam is left as an `LD-` xfail, and no assertion was loosened or xfail flipped by this ticket. |
| coverage matrix | `uv run python docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv` | **677 rows OK** (exit 0) |
| armed leak check (ADR-119) | `SIG_GCP_PROJECT=zeta-medley-508121-u7 uv run pytest tests/connectors/test_secrets.py` | **4 passed / 1 skipped / 0 failed** — zero occurrences of the literal id in the code+config scope; the one skip is `test_no_exported_secret_value_in_any_tracked_file` (no `SIG_*` credential env exported). Negative control: the id occurs in **74** tracked files, all under the deliberately-exempt `docs/` build memory — the 71 present at the base untouched (no redaction) + 3 doc-only evidence records this ticket wrote (ADR-119's consequence note allows doc copies). |
| ADR / spec / backlog | `check_spec_src.py`, `tests/unit/test_policy_adrs.py`, `check_backlog.py` + `build_backlog_md.py --check` | green — BUILD.sh reproduction byte-identical; Appendix F **118 ADRs = the docs/adr file set**; 677 requirement ids; 118/118 revisit triggers; `test_policy_adrs.py` 123 passed; deferral homes 36/36; 0 duplicate sources |
| build-memory | `bash scripts/docs/check-build-memory.sh .` | exit 0 (see the run ledger — re-run on the final tree) |

**The 3 skips** in `make check` are all env-gated: the live-API acceptance path (`SIG_STAGING_API_URL`
unset) and the two secrets checks (`SIG_GCP_PROJECT` / `SIG_*` unset when unarmed — the armed run above
passed).

## 2. Live re-verification of the Round-9 public-surface closures (read-only, no ADC)

| probe (2026-09-27) | result | confirms |
|---|---|---|
| `GET https://surveillancegraph.org/` | **200**, 85,844 B; headline *"223901 resolved sites (from 232625 observation-level records; dedup ratio 0.038)"* + **"provisional eval"** disclosure | D-R6.5-SURFACE stays DONE; PROVISIONAL disclosure intact |
| `GET /map/points.json` | **404** (146 B) | D-P30.3-2 public half stays DONE; **R8-1 stays CLOSED** |
| `GET /data-freshness/` | **200**, 80,321 B; 3 `not-recorded` tokens (the legend + `camreg_camilo_schools`' honest `last_content_change` gap — the shape P31.16 recorded) | D-P30.3-1 stays DONE (178/178 real dates) |
| `GET /network/` | **200**, 358,510 B | D-P30.2-2 public half stays DONE (130 edges + accountability links) |
| `GET /tiles/sig_graph-sites.pmtiles` with `Range: bytes=0-99` | **206** | D-P30.3-2 tiles half stays DONE (z0–z14 per-compartment archives serving) |

The remaining Round-9 closures are verified from the append-only record each closing ticket left (its
dated live evidence + verify commands): D-P30.4-1/-2 (P31.1), D-P30.1-1 + D-P30.4-3 (P31.3), D-P30.1-2 +
D-P31.1-2 (P31.4), D-P30.2a-1 (P31.5+P31.8), D-P30.2a-2 (P31.7), D-P30.2-1 (P31.9), D-P30.2b-3 (P31.11),
D-R7.3-BREADTH + the D-SOURCES.12-1 engineering remainder (P31.12+P31.13), D-P27.5-1 (P31.14), D-P30.3-3
(P31.14+P31.16), D-P30.3-1/-2 + D-P30.2-2 (P31.15/16 engineering + P31.16 publish). Every one is DONE
with its evidence recorded in `docs/tickets/DEFERRALS.md`; none is reopened.

## 3. Honestly OPEN after Round 9 (nothing swept silently)

- **Round-10 owned:** `D-R6.1-EVAL` (first-principles re-derivation needs human ground truth — 0 hosted
  review decisions; the PROVISIONAL disclosure is unchanged and verified live), `D-P30.2b-1` (engineering
  halves landed P31.10/P31.11; closure needs real human decisions), `D-P30.2b-2` (needs a fresh human
  holdout). Owner + landing: the Round-10 human review campaign → P31.18 re-derivation.
- **Scheduled:** `D-P31.4-1` — the 2026-10-10 `sig-sched-camreg-batch-05` replay has not happened (this
  ticket ran 2026-09-27); the row stays OPEN with its exact verify command. `D-FEDERAL.1-1` (SAM.gov
  paged tail — the cron continues).
- **Swept engineering (BL-057, no chain row):** `D-P31.1-1` (~10 s annotation watermark), `D-P31.1-3`
  (whole-entity 404 on an unregistered predicate — registry half DONE at P31.8), `D-P31.5-2` (needs the
  mootness ADR or a read-surface gate).
- **Operator/reviewer/external gates:** the 14 HG-gated rows in `DEFERRALS.md` § "P31.19 sweep" — **24
  OPEN/PARTIAL rows** total, each naming owner + precise blocker + landing.
- **Consciously skipped / moved:** P31.17 (row 158) was **dropped** by the operator 2026-09-25; P31.18
  (row 159) is **Round-10** work.

## 4. `projectStatus` under BM-TAIL-03

The four-part rule, evaluated on the P31.19 tip:

1. **GATE-ACCEPT-style readout signed:** **no.** `docs/build/readouts/ACCEPT-R8.md` remains **pending the
   operator's signature** (an agent never signs). This alone blocks `DONE`.
2. **Every chain row landed or consciously skipped:** **yes.** Rows 142–157 landed (P31.1–P31.16);
   row 158 (P31.17) is **consciously skipped** (dropped by the operator 2026-09-25 — the ticket's own
   contract counts a drop as a skip); row 159 (P31.18) is **moved to Round 10**; row 160 is this row.
3. **BUILD_INDEX complete:** **yes** — this ticket adds row 160.
4. **No OPEN deferral without a landing:** **met only under the loose reading.** Every OPEN row names a
   precise blocker + landing in the P31.19 sweep, but `D-R6.1-EVAL`, `D-P30.2b-1`, `D-P30.2b-2` land on a
   **not-yet-seeded Round-10** campaign, and `D-P31.1-1`/`D-P31.1-3`/`D-P31.5-2` land on `BL-057` with no
   chain row. The ticket states it plainly: **a not-yet-seeded Round-10 landing does not satisfy
   BM-TAIL-03** — a landing that exists only as a named future round is a blocker, not a landing.

→ **`projectStatus` stays `IN-PROGRESS`.** Conditions 1 and 4 fail. Round 9 is closed honestly: every
scheduled closure verified, the leak-check policy landed (D-P30.4-4 → DONE), the 10-10 replay recorded as
OPEN, and the Round-10 items are owned, not closed. `DONE` becomes available when the operator signs
ACCEPT-R8 and a Round-10 planning seed schedules (or consciously closes) the remaining owned rows.

## 5. Not done (operator actions; none is a build block)

- Sign (or send back) `docs/build/readouts/ACCEPT-R8.md`.
- Set the `vars.SIG_GCP_PROJECT` repo variable to arm the CI leak-check step (it skips when unset — never
  a false red; ADR-119).
- Seed Round 10 (the human review campaign → P31.18) when ready.
- After the 2026-10-10T03:35Z cron: run the `D-P31.4-1` verify (executions list + the
  `ops/runs/camreg_osm_surveillance/2026-10-10/` run row + `ingest_run_completion`).
- Integrate the PR stack per `docs/build/INTEGRATION_PLAN.md` (no agent merges/tags/pushes `main`).
