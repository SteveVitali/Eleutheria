# CAPSTONE VERIFICATION — `sig-postbuild` (composed end-to-end, final)

**Branch:** `devin/sig-postbuild-capstone` (stacked on `devin/p22-2-agent-docs-refresh`, base commit
`bb5b1cc`). **Docker:** 29.1.3, `docker info` reachable. **Date:** 2026-09-09.

This is the FINAL composed verification of the whole chain: two scoped integrity gaps closed, then the
entire build exercised as one unit (spine → export → web → acceptance). Append-only throughout; the
signed `CAPSTONE_CLOSURE.md §(b)` table and every ADR body are unchanged (addenda only). Nothing was
merged, tagged, or pushed to `main`; no source was flipped to `ingestion_permitted=true`; no human gate
was ticked.

---

## (a) Gap-closure summary — gap → change → checker result

### MATRIX-INT-01 — two invalid-enum rows in `docs/build/COVERAGE_MATRIX.csv`

| id | was (invalid) | now | reasoning |
|---|---|---|---|
| `SIG-STORE-003` | `verdict=COVERED` (not in the enum) | `verdict=MET`, `routing=—`, evidence + `tests` now cite `tests/ops/test_degraded.py` | §15.2 requires "start, ingest, resolve, serve with **zero non-PostGIS extensions**". That property is proven by the zero-cost degraded rebuild + the monthly-keepalive fail-loud test (`tests/ops/test_degraded.py`, SIG-GOV-021, LD-P07). A test-cited pass ⇒ **MET**, not a deviation. |
| `SIG-UI-047` | `class=deferred(A1-ticked)` (not in the enum), `verdict=MISSING` | `class=deviated(ADR)`, `verdict=MET-DIFFERENTLY`, `routing=P20.2:spec` | Same already-accepted zero-JS static-map decision recorded in the signed §(b) table as `SIG-UI-038` (A1 ticked → zero-JS static PMTiles map is the conforming default; MapLibre island not built by decision, ADR-051/ADR-067). Recorded consistently under its second fold-back id. |

**Checker result — `python3 docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv` → exit 0:**

```
L1 cross-check: 98 seed ids OK
671 rows OK
```

**MET-DIFFERENTLY count reconciliation:** before **76** → after **77**. Only `SIG-UI-047` crosses
`MISSING → MET-DIFFERENTLY` (+1); `SIG-STORE-003` becomes `MET` (not MET-DIFFERENTLY), so it adds
nothing. `MISSING` moves 10 → 9. Because the new row is the *same* already-signed zero-JS-map deviation
under a second fold-back id (no new class of deviation), the signed `CAPSTONE_CLOSURE.md §(b)` table
(76 rows) was **not** rewritten; a dated **append-only addendum** `### (b) Addendum — 2026, sig-postbuild
capstone verification` records the 76 → 77 move and its reason. Operator HG-14 acceptance of Family 2
(zero-JS static map, ADR-051, `P20.2:spec`) already covers it.

### APPENDIX-F-01 — ADR-072 missing from Appendix F

`python3 docs/build/tools/check_spec_src.py` reported **exactly one** problem first:
`ADR files absent from Appendix F: ['ADR-072']`. Re-verified ADR-063…071 all already have Appendix F
rows; **ADR-064 is a skipped number** (no `docs/adr/ADR-064*.md` file exists, and it has no row — which
is consistent, so nothing to add there). Fix was minimal and exactly what the checker flagged:

- edited the **source** `docs/research/_meta/spec_src/99a_appF_adr.md`, appending one `| ADR-072 | … | P22.2 |`
  row (documentation-freshness gates; never edited `docs/2_canonical_design_spec.md` directly);
- ran `sh docs/research/_meta/spec_src/BUILD.sh` to regenerate the canonical spec (byte-identical repro);
- committed both the source and the regenerated spec (the spec diff is exactly the one new row).

**Checker result — `python3 docs/build/tools/check_spec_src.py` → exit 0:**

```
check_spec_src: OK
  BUILD.sh reproduction: byte-identical (564953 bytes)
  Appendix F: 71 ADRs, equal to the docs/adr/ file set
  requirement ids: 671 (= 668 + 3 fold-backs)
  no duplicate / malformed / reserved ids; reference closure holds
```

---

## (b) Composed end-to-end evidence — the whole build as one unit

| step | command | result |
|---|---|---|
| CI-mirrored gate | `make check` | **2718 passed, 1 skipped, 0 failed, 0 xfailed** (72.6s). lint / format-check / mypy (211 files) / verify-gen all green. The 1 skip is `tests/acceptance/queries/test_acceptance_live_api.py` (needs a running API — exercised live by `run_okc.sh` below). |
| claim-spine DB | `make test-db` (`SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db`) | **120 passed** over a real PG18+PostGIS testcontainer (`postgis/postgis:18-3.6`). |
| composed stack | `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra` | **16 passed, 0 skipped, 0 xfailed.** No xfail markers remain in `tests/e2e`. |
| — S8 / LD-V08 | `… tests/e2e/test_composed_stack.py -v -k s8` | S8 **RAN** (did not skip — `web/node_modules` present): `test_s8_web_build_emits_dossier_route` **PASSED**, `test_s8_web_build_renders_from_export_bytes` **PASSED** (LD-V08 CROSSED — dossier renders from EXPORT bytes, not fixtures), `test_s8_web_build_consumes_rendered_tiles` **PASSED**. Astro build is genuinely fast (~0.7s, 50 pages) — the fast pass is a real build, not a no-op. |
| first jurisdiction | `SIG_OKC_TEARDOWN=1 sh docs/build/tools/run_okc.sh` | **Completed 8/8 end-to-end** over the composed fixture DB — no live fetch, no source flipped (connectors ran `--mode shadow`, HG-03-pending recorded). Web built FROM the export (`SIG_DATA_SOURCE=export`, 50 pages). 299-vs-190 contradiction rendered from the export: `contradiction_state=unresolved_conflict`, values `[299, 190]`, both shown with evidence. Acceptance JSON written (see below). Clean teardown (`docker compose down -v`; no containers/host procs remain). |
| coverage integrity | `python3 docs/build/tools/check_coverage_matrix.py …` | **exit 0** (`671 rows OK`). |
| spec-source integrity | `python3 docs/build/tools/check_spec_src.py` | **exit 0** (`check_spec_src: OK`). |
| backlog integrity | `python3 docs/build/tools/check_backlog.py` | **exit 1 — PRE-EXISTING RED**, unrelated to the two gaps (see §(f)). |

**OKC acceptance JSON** (`docs/build/okc/acceptance_2026-09-09.json`, regenerated byte-identically):
`summary = {passed: 2, blocked: 11, failed: 0, total: 13, fixture_subset_all_pass: true, j1_status: pass}`.
J-1 (journalist traversal) **pass** — 12 hops `city → police_agency → deployment → contract →
contracted_cameras → mapped_devices → sharing_relationships → network_searches → retention_settings →
policy → related_litigation → replacement_vendor`, 5 source families. **0 failed.** The 11 "blocked"
Q-rows are queries that need green live sources (none are flipped by design; blocked ≠ failed) — this is
the expected shadow-mode fixture-subset behaviour, and the fixture subset all pass.

---

## (c) Consciously ACCEPTED sound deviations (recorded, not "fixed")

These are documented, sound alternatives — not gaps:

1. **P21.2 compute-on-read shrink (A5).** Annotation tables exist and a compute-on-read fallback serves
   dispositions; no separate `annotations rebuild` step (ADR-059; `run_okc.sh` step 5/8 records this).
2. **Zero-JS static map / no MapLibre island (A1, SIG-UI-047 / SIG-UI-038, ADR-051/067).** The served
   `/map/` is a zero-JS static PMTiles surface with a tabular equivalent; the MapLibre island is not
   built by decision. Keeps the zero-JS + perf gates green (`P20.2:spec`).
3. **P17-FLIP `SIG-INGEST-049*` deferred (P22+/backlog).** The CCOPS / government-mandated-disclosure
   *class* is deferred; the P17 pathway ingestion itself IS built + tested (ADR-071, `pathways`
   connector, `tests/connectors/test_pathway_coverage.py`).
4. **S8 skipped in the CI `python` job.** CI's `python` job installs no Node; the CI `web` job builds
   web. The export→web seam (LD-V08) is proven **locally here** — S8 RAN and passed (§(b)).
5. **All HG-gated return-pass tickets await human input** (see §(d)) — recorded and routed, NOT gaps.

## (d) Human-gated return-pass items routed to the operator

None of these are code gaps; each awaits a human decision and is recorded:

| ticket | gate / decision awaited |
|---|---|
| P21.1 | Stage-0 outreach / rights-flip decisions (registry green) — **HG-03** |
| P21.3 | live connector wiring: a live fetch refuses (exit 3) until a source is green — **HG-03** |
| P21.4 | runtime composition / staging endpoints — **HG-12** |
| P21.5 | Zenodo deposit sandbox — **HG-07** (degraded mode + keepalive already built+tested) |
| P21.7 | contribution-back live push + OSM feed poll + onboarding study — **HG-08 / HG-10** |
| P21.8 | Data Driven + coarse-international live — **HG-03** |
| P21.9 | pathways connectors live — **HG-03** |
| capstone | operator signature on `CAPSTONE_CLOSURE.md §(b)` accepted deviations — **HG-14** |

## (e) Whole-build verdict

**GREEN on the assigned scope and the full composed end-to-end run.** Both integrity gaps are closed
and their checkers exit 0; `make check` (2718 passed / 0 failed / 0 xfailed), `make test-db`
(120 passed), the composed `tests/e2e` (16 passed / 0 skipped / 0 xfailed **incl. S8/LD-V08**), and the
`run_okc.sh` first-jurisdiction pipeline (contradiction rendered from export bytes, acceptance J-1 pass,
0 failed) all pass; the coverage-matrix and spec-source integrity checkers exit 0. **One pre-existing,
out-of-scope RED remains — `check_backlog` (§(f)) — routed to the operator; it is NOT fabricated green.**

## (f) Pre-existing blocker — `check_backlog` (NOT a code failure from this run)

`docs/build/BACKLOG.csv` is **byte-identical to the chain tip** (`git diff devin/p22-2-agent-docs-refresh
-- docs/build/BACKLOG.csv` is empty), so this failure predates this run and is independent of the two
gaps. `check_backlog.py` is a "docs tool invoked in the PR, **not** a `make check` step" (its own
docstring), so it went red at the tip unnoticed — RISK-P20-01 (backlog drift) materialized. The full
failure set at the tip:

- `BL-041`: `landing='P21.x'` — invalid placeholder (title says "out of scope P21.7 — separate
  follow-up"; should be `P22+`). Introduced in the P21.7 commit `2981ce8`.
- `BL-043`: `status='closed (P21.9 pathways connector; ADR-071; …)'` — the enum requires exactly
  `closed`/`open`/`accepted`; the closure provenance belongs in `landing`/`gate` (already `P21.9`/`HG-03`).
- `bl_ids in no theme: BL-052`.
- `unmapped ADR: ADR-071 ADR-072` — both carry a `## Revisit trigger` but no backlog row sources them.
- `orphan sources: DOCS_REFRESH_REPORT P22.1 RISK-P21-08 RISK-P21-09 RISK-P21-14 RISK-P21-15`.
- `double-owned sources: ADR-067 (BL-029 & BL-030); ADR-069 (BL-038 & BL-039 & BL-040)`.

This is a genuine backlog-reconciliation task (touches `BACKLOG.csv` + `BACKLOG_THEMES.md` against the
risk register / ADR revisit triggers / `LEDGER_DEFERRALS.md`) and is deliberately **out of scope** of
this two-gap capstone; two speculative one-cell enum fixes were tried and then **reverted** to keep this
PR's diff strictly scoped. **Command that closes it:** open a `P22+` backlog-reconciliation ticket that
makes `python3 docs/build/tools/check_backlog.py` exit 0 (assign `BL-052` a theme; source `ADR-071`/`072`
into rows; normalise `BL-041`/`BL-043` enums; de-orphan/de-dup the source cells). **Routed to the
operator.**
