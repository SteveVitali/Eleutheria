# SCOPING_NUMBERS — the facts needed to write precise ACs for P19.2–P21.x (step B′, ledger §5.1)

- **Produced:** 2026-09-08, planning-only session (ledger `.agents/scratch/NEXT-PHASE_planning-ledger_20260908.md` §4.8 / §5.1 row B′). Checkout `devin/p18-2-france-belgium` @ `1baf05f`; working tree clean except untracked `.devinignore`. Nothing committed; no tests run; no code changed.
- **Rule:** every number below carries the command (or script) that produced it. Where a number could not be established it says so. Companion: `SCOPING_ID_LISTS.md` (the id lists behind §(i)).
- **Scripts (throwaway, `/tmp/sig-scope/`):** `count_refs.py` (id reference counts with range expansion), `rights_counts.py` (registry posture). Both are reproducible from the commands quoted inline; P19.2 should re-derive rather than trust these files.

---

## (i) Requirement-id coverage — how many of the 668 ids are referenced where

**Universe.** `grep -oE '\*\*SIG-[A-Z]+-[0-9]+[a-z]? \((MUST|SHOULD|MAY|RATIONALE)' docs/2_canonical_design_spec.md | sort -u` → **668 defined ids** (646 MUST · 13 SHOULD · 2 MAY · 7 RATIONALE). Raw distinct `SIG-*` tokens in the spec = 672; the 4 extra (`SIG-ENG-006/009/028/029`) are the spec's own *reserved-but-unassigned* ids (spec L84) — not requirements. By prefix: INGEST 83, ONTO 72, RECON 57, UI 51, STORE 47, ENG 36, CHART 35, IDENT 34, CONTRIB 34, EPIS 30, GOV 24, PUB 23, TASK 20, LIC 19, EVID 19, TIME 16, METRIC 14, GEO 13, API 13, EXPORT 11, PARSE 8, LLM 7, SEC 6.

**Method caveat that changes the numbers.** Range notation (`SIG-GOV-001…011`, `SIG-UI-010..015`, `SIG-RECON-034–037`) is used 122× in PR bodies, 84× in ADRs, 237× in `tests/`, 454× in source, 134× in tickets, 101× in traceability. Exact-token grep therefore *undercounts*; the table gives the range-expanded number (script `count_refs.py`, regex `SIG-([A-Z]+)-(\d{3})([a-z]?)(?:\.\.\.?|…|–|—|-)(\d{3})`, ranges ≤120 wide) with the exact-only number in brackets.

| Evidence class | Source of text | Defined ids referenced (range-expanded) | exact-only |
|---|---|---|---|
| PR bodies #1–#46 | `gh pr view N --json body` (46 files, 235 KB) | **364** | 292 |
| ADRs | `docs/adr/ADR-*.md` (57 files) | **358** | 348 |
| Python tests | `tests/**` | **375** | 363 |
| Web tests | `web/tests/**` (vitest + playwright) | **64** (49 of the 51 `SIG-UI-*` ids appear somewhere in `web/`) | — |
| **tests ∪ web/tests** | | **415** → **253 ids appear in no test file** (INGEST 37, ONTO 32, CHART 28, ENG 27, EPIS 26, STORE 19, PUB 15, GOV 14, CONTRIB 9, GEO 9, LIC 8, TIME 7, UI 6, SEC 5, EVID 3, RECON 3, API 2, METRIC 2, IDENT 1) | 305 untested |
| Package source | 14 workspace members + `web/` + `Makefile`, `pyproject.toml`, `.github/` | **500** | 491 |
| `docs/traceability.md` | | **421** → 247 ids never claimed there | 421 |
| Ticket files | `docs/tickets/P*.md` (47) | **418** → **250 ids were never assigned to any ticket** (ONTO 44, INGEST 39, STORE 30, CHART 28, EPIS 25, ENG 19, RECON 17, IDENT 10, GEO 9, GOV 8, TIME 7, EVID 6, CONTRIB 3, UI 2, EXPORT 2, METRIC 1) | 372 |
| Risk register | `docs/risk_register.md` | **232** | 232 |
| **Union (PR ∪ ADR ∪ tests ∪ src)** | | **545** → **123 ids in none of the four implementation-side classes** | 141 |
| **Union (all seven classes)** | | **570** → **98 ids referenced nowhere at all** | 121 |

**The 98 "nowhere" ids** (full list `SCOPING_ID_LISTS.md` §L1): 92 MUST, 3 SHOULD, 3 RATIONALE. By prefix: CHART 25 (`SIG-CHART-001..007, 011, 014..026, 031, 033..035` — the charter's enforceable-principle set incl. "MUST NOT be built as another surveillance map"), ENG 16 (`SIG-ENG-002, 018..027, 030, 032, 033, 037, 038` — process/practice requirements incl. §51 phase-gate rules), EPIS 16, INGEST 16 (incl. `SIG-INGEST-043/043a-d` Data Driven releases as first-class source, `SIG-INGEST-049a-d`, `SIG-INGEST-004/005/007/008`), GOV 5 (`017, 018, 022, 023, 024` — mirrors/Zenodo/Software Heritage deposits, succession), ONTO 5, GEO 4 (`001, 002, 005, 007` — EPSG:4326 storage etc.), STORE 3 (`003, 004, 005` — zero-cost start, …), CONTRIB 2 (`012, 012a` — Stage-0 before any ecosystem connector), RECON 2, TIME 2, IDENT 1, UI 1 (`SIG-UI-001` personas), PUB `003d, 012, 014, 014b, 015, 016` are in the 123 (referenced only in traceability/tickets). These are the P19.2 seed for `MISSING` / `rationale-only` / `process-not-code` classification — **not** a verdict: many CHART/ENG/EPIS ids are satisfiable by design properties or by the governance docs and simply were never cited by id.

**Other cross-cuts (P19.2 hunting lists).** 13 ids are *claimed* in traceability but appear in no test and no source (`SIG-ENG-004, ENG-034, GOV-006, GOV-009, GOV-015, GOV-016, GOV-021, INGEST-010, ONTO-001, ONTO-007, ONTO-043, STORE-006, STORE-013`); 34 ids are in tests but never claimed in traceability (traceability drift, the reverse direction); 141 ids appear in source but in no Python test. Spec §52 itself names only **21** ids in its phase text (L6656–7072) — phases are described by section, so the ticket-to-id assignment was made at decomposition (418 of 668) and the remaining 250 have never had an owner ticket.

**Spec-side traceability.** Spec Appendix A (L7118–7818) is the *outline → spec* matrix (480 obligations, 101 SIG ids cited); there is no spec-side *id → implementation* matrix. `docs/traceability.md` (1,945 lines) is the only implementation-side one and covers 421/668.

## (ii) Rights posture — `uv run sig-connectors validate` (read-only CLI, run 2026-09-08)

```
registered sources: 109
  rights UNDETERMINED (export gate fails closed): 87
  ingestion_permitted=true: 0
  loadable now (permitted + compact + custody): 0
local groups: 17 (unlocated 2, disappeared 1)
national partners: 10
connectors registry self-checks OK
```

Registry file: `connectors/src/connectors/data/sources.toml` (1,501 lines, 109 `[sources.<id>]` tables). Facts derived with `rights_counts.py` (tomllib):

| Fact | Number | How |
|---|---|---|
| Sources with a `[sources.X.rights]` block (SPDX + `redistributable` + `derivative_permitted`) | **22** | 22 `spdx =` keys |
| Sources with no rights block → `UNDETERMINED` | **87** | 109 − 22 |
| Sources with `ingestion_permitted = true` | **0** — the key is **absent from every row**; `registry.py:184` defaults it `False` (SIG-INGEST-028 fail-closed) | `grep -c ingestion_permitted sources.toml` = 0 |
| Fetch-capable posture (`MIRROR`/`REFERENCE`/`DERIVE`) **and** compact permits (`public_terms_only`/granted/partnership) **and** rights block present — i.e. only the flag flip + a recorded review stands between them and "loadable" | **18** — `osm_surveillance_tagging, osm_copyright, osmf_licence_guidelines, osm_taginfo, osm_overpass, osm_replication, osm_element_history, osm_automated_edits_coc, deflock_repo, deflock_app_repo, eyes_on_flock, agency_audit_export, eff_atlas_of_surveillance, gleif, wikidata_sparql, flock_finder, sous_surveillance_osm_import, raa_prefectures` | script |
| `custody_posture` | REFERENCE 58 · LINK 41 · MIRROR 10 (LINK = never fetch content; `loader.py:57`) | script |
| `compact_status` | public_terms_only 65 · not_contacted 43 · no_response 1 (Stage-0 outreach never recorded as granted/partnership for **any** source) | script |
| `default_tier` | R1 31 · R2 24 · R3 24 · R4 10 · R5 14 · R6 6 | script |
| `derivative_permitted=false` | 2 (`deflock_app_repo`, `sm_alpr` — AGPL, RISK-P0-18) | script |
| Registered connectors (`sig-connectors list-connectors`) | 9: accountability, atlas, audit_structural, flock_portal, france_belgium_procurement, france_belgium_records, osm, procurement, records | CLI |
| Source ids hard-coded in connector code (`source_id = "…"` in `connectors/src/connectors`, excl. `data/`) | 9: `agency_audit_export, agenda_tenant_registry (NOT in sources.toml), aspi_mapping_chinas_tech_giants, carnegie_ai_gsi, eff_atlas_of_surveillance, eyes_on_flock, facial_recognition_world_map, osm_element_history, osm_overpass`; 3 of them are `UNDETERMINED`+LINK (the coarse-international trio) | grep |
| `usaspending` (the only source ever fetched live, P07.3/PR #19, LD-X08) | REFERENCE · public_terms_only · **no rights block (UNDETERMINED)** · no `ingestion_permitted` → the live trace ran *outside* the loader gate | script |

**J-1 / OKC slice sources.** No row in `sources.toml` mentions OKC/Oklahoma. The slice fixture `tests/acceptance/fixtures/okc_sources.json` has 10 artifacts from 8 `source_id`s: `src:deflock` (→ registry `deflock_repo`, present), `src:okc-procurement`, `src:okc-council`, `src:okcpd-policy`, `src:ok-statute`, `src:journalrecord`, `src:oklahoman` — **7 of 8 slice sources are not in the source registry at all**. The CivicClerk agenda tenant for OKC exists (`connectors/src/connectors/data/agenda_tenants.toml:71-77`, "pending live verification"). Consequence for P21.x: "one real jurisdiction live" for OKC needs (a) 7 new registry rows with rights reviews, (b) the `ingestion_permitted` flips, (c) a real fetch for at least the R1/R2 rows (procurement, council, policy, statute), (d) the DeFlock/OSM route through `osm_overpass` (ODbL compartment, RISK-P0-01/02).

## (iii) Merge dry-run — PRs #20–#46 onto `origin/main` (throwaway worktree, no ref or remote touched)

- `git fetch origin` → `origin/main = 2f4e9e5` (unchanged since 2026-09-04). Open PRs: `gh pr list --state open` = 27 (#20–#46), each `baseRefName` = previous `headRefName`, #20's base = `main`. Every local branch == its `origin/` counterpart (per-branch `git rev-parse`, table in `/tmp/sig-scope/open_prs.txt` at capture; BUILD_INDEX §A.2 has the SHAs).
- **Topology:** `git merge-base origin/main devin/p08-1-resolver` = `2faf380` (P07.3's tip). *No* open branch descends from `origin/main` — the chain forks from P07.3's commit, and the 10 later merge commits on main add **no tree change** (`git diff --stat 2faf380 origin/main` is empty). First-parent distance: tip is +28 over main (27 ticket commits + hardening `4493b14`).
- **Dry-run A (independent):** `git worktree add --detach /tmp/sig-merge origin/main`; for each of the 27 branches in PR order: `git merge --no-commit --no-ff <branch>` → record `git diff --name-only --diff-filter=U` → `git merge --abort`. **Result: 27/27 rc=0, 0 conflicted files**; cumulative staged files 7 (#20) → 341 (#46).
- **Dry-run B (bottom-up accumulation):** same worktree, merges committed on the *detached* HEAD only (no branch ref), #20→#46 in order. **Result: 27/27 clean; final tree == `devin/p18-2-france-belgium^{tree}` (verified with `git rev-parse …^{tree}`).** Worktree removed (`git worktree remove --force`, `git worktree prune`); main tree afterwards: `devin/p18-2-france-belgium`, `?? .devinignore` only; `main`/`origin/main`/branch SHAs unchanged.
- **Interpretation for P20.3:** integration is mechanically trivial — merging #46 alone brings the identical tree; merging bottom-up gives 27 merge commits and per-PR review granularity. GitHub auto-retargets stacked PRs when a base branch is deleted on merge; with "create a merge commit" each is conflict-free; **squash-merge would also be conflict-free** (identical hunks both sides) but would destroy the 1-commit-per-ticket history — a strategy choice for the operator. The `ontology/generated` / `pylock.toml` "conflict magnets" of ledger §3.1 did not materialise because no one touched `main` after #19.
- **Post-merge CI evidence already exists:** every open PR's latest run is green — `gh pr checks` #20–#34: `python:pass`; #35–#46: `python:pass web:pass` (see (iv)). Last `main` run: 2026-09-04 `2f4e9e5` success.

## (iv) CI facts

| Fact | Value | Evidence |
|---|---|---|
| Workflows | one: `.github/workflows/ci.yml` (jobs `python`, `web`); triggers `push: main` + every `pull_request`; concurrency cancel-in-progress | file |
| `python` job | `make sync → lint → format-check → typecheck → test → verify-gen`; uv 0.12.6 pinned, `--frozen` lockfile | ci.yml L21–59 |
| **`tests/db` in CI** | **YES** — `make test` runs with `SIG_REQUIRE_DB_TESTS=1` + `TESTCONTAINERS_RYUK_DISABLED=true` on `ubuntu-latest` Docker; run `34273769189` (PR #46, 2026-09-08) executed 11 db files / **114 db tests** (`test_analytics 45, test_suppression 26, test_rls 7, test_evidence_store 7, test_identity_registry 7, test_append_only 6, test_schema_integrity 6, test_resolution_exclusion 4, test_as_of 3, test_corrections 2, test_reverts 1`) → **2364 passed in 90 s** | `gh run view 34273769189 --log` — **this closes LD-V11** ("tests/db not recorded for P17.x–P18.2") and corrects LD-P06's "Docker-capable CI runner" prerequisite: it already exists |
| `web` job | `npm ci → astro check → vitest (16 files / 152 tests) → astro build → check:licenses (OSI-only) → playwright e2e (**163 passed**, chromium + no-JS + axe WCAG 2.2 AA) → lhci perf budgets` | ci.yml L61–102; run log |
| Local `make check` mirror | `check: lint format-check typecheck test verify-gen`; `test-db` target exists; local Docker daemon present (`docker info` → 29.1.3) | `Makefile` L36–46 |
| Local test count (P18.2 ledger) vs CI | 2363 local / 2364 CI (one db-conditional test) | BUILD_INDEX §A.1; run log |
| Tags / releases | **0 tags**; no release; no `v0.x` anywhere | `git tag` |
| Branch protection on `main` | **none** (`gh api …/branches/main/protection` → 404 "Branch not protected") | gh |
| Repo | **PUBLIC**, default branch `main`, GitHub licence detection = "Other" (multi-licence `LICENSE`, 60 lines: code Apache-2.0; data/docs per-artifact per §42, SIG-LIC-005) | `gh repo view`; `LICENSE` |
| `.github/` extras | only `workflows/` — no dependabot, CODEOWNERS, SECURITY.md, issue templates | `ls -a .github` |
| SBOM | `sbom.cdx.json` dated **Aug 26** (25 components) — stale vs 14 workspace members; `make sbom` target exists | `ls -la`, `grep -c bom-ref` |
| Not determined | whether Playwright/`lhci` run **from live API data** (they run from fixtures per LD-V08); egress/mirror infra (ADR-015) exists nowhere in repo config | — |

## (v) Human-gate inventory (everything that needs a person, a decision, an account, or counsel)

Consolidated from `LEDGER_DEFERRALS.md` §5 (LD-P01..07), `docs/risk_register.md` Phase 0 (L6–60, RISK-P0-01..20), `docs/tickets/00_MANIFEST.md:39-41`, and the registry numbers in (ii). Each row gets a gate id `HG-nn` for the DECISION_MEMO; "kind" ∈ {decision, legal, outreach, account/infra, study, budget}.

| HG | Kind | Gate | Sources | Unblocks |
|---|---|---|---|---|
| HG-01 | legal | **Legal home** (fiscal sponsor / nonprofit) established before public launch — SIG-GOV-012 | RISK-P0-13; manifest L41; LD-P02 | any public launch (P21.x publish step) |
| HG-02 | legal | Counsel review of the four ODbL / sui-generis questions (RISK-P0-01..04) + legal-defence resources (RISK-P0-14, SIG-GOV-013) + know-your-rights guidance (RISK-P0-11) + no-circumvention posture (RISK-P0-06) | risk register L8–36 | export of OSM-derived compartment; contributor programme |
| HG-03 | legal/review | **Per-source rights review** (SIG-LIC-001, RISK-P0-19): 87 `UNDETERMINED` rows; 22 rows need the `ingestion_permitted` decision; **0 loadable today** | (ii); LD-P05; RISK-P0-15/16 | every connector's first real fetch; first 18 candidates listed in (ii) |
| HG-04 | outreach | **Stage-0 outreach** to the 19 compact projects (§35.1, SIG-CONTRIB-012/012a/013); `compact_status` is `not_contacted` 43 / `no_response` 1 / `public_terms_only` 65 — no `permission_granted`/`partnership_active` anywhere; Eyes on Flock partnership / archival-succession offer (RISK-P0-17/20) | manifest L40; LD-P01; (ii) | ecosystem connectors (osm/deflock/atlas/eyes_on_flock) beyond public-terms use |
| HG-05 | decision | **Integration strategy** for the 27 open PRs (merge-commit bottom-up vs squash vs single merge of #46) and whether to protect `main` | (iii) | P20.3 |
| HG-06 | decision | **First live jurisdiction** — OKC (J-1, P06.1) is the default; needs 7 new registry rows + reviews (ii) | `docs/slice/P06.1_hardness_precondition.md` | P21.x sequencing |
| HG-07 | account/infra | Zenodo account + concept DOI (SIG-GOV-022); object store (`cloudflare-r2:sig-bulk` named in the CLI vs ADR-015 S3/CloudFront) + CDN/egress budget; Software Heritage deposit; mirrors | LD-P06; RISK-P0-07; `SIG-GOV-022` unreferenced in code | P14.2 real deposit; P21.x publish |
| HG-08 | account | MapRoulette account + API disclosure; OSM Organised Editing registration; OSM account for contribution-back | LD-P04; RISK-P16-14/15 | P16.2 live |
| HG-09 | account | MuckRock token; api.data.gov key; other `auth_model` keys (7 sources need a key/token; 1 needs Belgian eID) | (ii) `auth_model`; LD-F16 | records + procurement live |
| HG-10 | study | Moderated usability study ≥5 naïve contributors (P16.1 AC7, SIG-UI-001 personas unreferenced) | LD-P03 | contributor launch |
| HG-11 | governance | Operate the prose governance: real editorial board, two-reviewer publication concurrence (RISK-P0-05/10), officer names | RISK-P0-05/10 | first publication |
| HG-12 | budget/infra | Hosting for the static site + API + PG18/PostGIS; zero-cost degraded mode (SIG-GOV-021, RISK-P0-12, LD-P07, `SIG-STORE-003` unreferenced) | ADR-015; risk register | P21.x |
| HG-13 | decision | Spec amendments that change normative text (P20.2) — the operator signs each `spec_src` edit + ADR (SIG-ENG-003) | ledger §2.3 | P20.2 |
| HG-14 | decision | Accept-as-designed dispositions in the capstone (P19.4 "consciously accept sound deviations") — operator sign-off on the ACCEPTED list | orchestrate-build §3 | P19.4 |

Numbers behind the gates: **87 + 22 = 109** source rows need a rights decision; **43** sources never contacted; **19** compact projects; **7** OKC slice sources unregistered; **0** tags; **0** branch protection; **0** accounts/credentials present anywhere in the repo (correct — none should be).

## (vi) Code anchors for the composed path (read-only subagent sweep, 2026-09-08; re-confirm at build time)

| Seam | Fact | Anchor |
|---|---|---|
| Connector → claim spine | The only `ClaimSink` implementation is **`InMemoryClaimSink`**; `pipeline.py` calls `ctx.claim_sink.assert_claims(...)` only when a sink is present → **connector claims have never been written to PG** (new finding; sibling of LD-F06) | `connectors/src/connectors/stages.py:269` (Protocol), `:280` (in-memory), `connectors/src/connectors/pipeline.py:125-126` |
| Replay / shadow | `replay()` / `shadow_replay()` | `connectors/src/connectors/replay.py:32,98` |
| Fetch transport | `Transport` Protocol, `PoliteFetcher` | `connectors/src/connectors/net.py:76,153` |
| Evidence store | `OcflStore`; connectors' `CaptureStore` Protocol | `evidence/src/evidence/ocfl.py:88`; `connectors/src/connectors/stages.py:190` |
| Loader gate | `assert_loadable` / `assert_ingestion_permitted` | `connectors/src/connectors/loader.py:76,93` |
| DB | `db/sqitch.plan` 18 changes; `db/deploy/graph_annotations.sql` defines `contradiction`, `coverage_record`, `research_task`; test fixtures `sig_database` / `conn`, image `postgis/postgis:18-3.6`; `_require_or_skip` | `tests/db/conftest.py:30,48-49,54,127` |
| Temporal | `AsOf.resolve/where/question` | `db/src/db/temporal.py:158-183` |
| Resolver | `RESOLVE(...)` emits value objects, no PG write | `reconcile/src/reconcile/resolve.py:21-22,291` |
| Annotation layer | `Contradiction` dataclass, `CoverageRecord`, `ResearchTask`/`TaskPool.generate`; **no psycopg/sqlalchemy import in reconcile/, inference/, tasks/** | `reconcile/src/reconcile/model.py:158`; `inference/src/inference/coverage.py:53`; `tasks/src/tasks/lifecycle.py:54,234,247` |
| ER / review | `ProbabilisticMatcher.match`; `ReviewQueue.enqueue/decide` (JSONL); CLI `review` | `resolution/src/resolution/probabilistic.py:199,257`; `review_queue.py:199,214,231`; `cli.py:90-110` |
| API | `ReadStore` Protocol (16 methods) + `InMemoryStore`; `create_app(store)`; `get_store`; 12 `/v1/*` routes + `/id/{id_type}/{uuid}` + `/terms` | `api/src/api/store.py:108,147`; `app.py:42,58,62,80`; `routes.py:59-390` |
| Exports | `sig-exports build` parser, `--zenodo-dry-run`; `ZenodoTransport`/`FakeZenodoTransport`/`deposit_release`; `write_pmtiles` (hand-rolled, no rendered tiles); parquet via DuckDB (no pyarrow); no ImportError guards | `exports/src/exports/cli.py:23,50,64`; `zenodo.py:75,88,135`; `formats.py:245` |
| Web | pages read `web/src/lib/fixtures.ts` + `*-fixture.ts`; **no `fetch(`/API/export read anywhere in `web/src`**; budgets script=0 B, total 150 KB | `web/src/lib/`, `web/lighthouserc.json:15-17`; 12 e2e specs in `web/tests/e2e/` |
| Policy | `publication_permitted`, `adapter_publication_permitted`; `python -m policy jurisdiction`; `compute_export_license`; `evaluate_officer_naming` + `ReviewerConcurrence` | `policy/src/policy/publication.py:96`; `jurisdiction.py:266`; `cli.py:32-73`; `licensing.py:111`; `officer.py:61,93` |
| Spec/ADR | 36 `spec_src/*.md` + `BUILD.sh`; ADR-057 highest; ADR header fields `Status/Date/Phase/Requirement ids`; `docs/adr/README.md` is the Appendix-F index | paths |
| Docs | `docs/traceability.md` thematic `## <theme> (§n)` headings; `docs/risk_register.md` last heading `## Phase 18 …` L1160; README has 7 sections; **no CHANGELOG.md / CONTRIBUTING.md / AGENTS.md** | paths |
| Deploy | **No Dockerfile / compose / hosting config anywhere**; `ops/` is a skeleton CLI; `orchestration/pipeline.py` is a seam with `ORCHESTRATOR_MODULES` only | `ops/src/ops/cli.py`; `orchestration/src/orchestration/pipeline.py:22` |
| Scratch | `.agents/scratch/` 8.3 MB (112 entries; 16 `*.log` = 7.3 MB), `scratch/` 88 KB (8 entries incl. `p052_live/`); `.agents/scratch` is gitignored via the `scratch/` pattern; `sbom.cdx.json` is gitignored ("per release via `make sbom`") | `.gitignore` |

## Corrections to earlier ledgers/artifacts found while scoping

1. **LD-V11 is closed by CI**, not by a future P19.3 step: `tests/db` runs on every PR with `SIG_REQUIRE_DB_TESTS=1` (114 db tests green on #46 today). P19.3 still runs them locally as its first step (cheap), but the "never recorded for P17.x–P18.2" statement is superseded.
2. **LD-P06 "Docker-capable CI runner for tests/db"** is not a prerequisite — it exists (`ubuntu-latest` daemon).
3. Ledger §2.4 "272 RISK rows" → **269 unique `RISK-P*` ids / 270 table rows** (`grep -oE 'RISK-P[0-9]+-[0-9]+[a-z]?' | sort -u`). 118 rows sit under Scaffolded/Deferred/Unverifiable headings (the backlog universe for P20.1); 11 under "Deviations recorded as ADRs"; **57 of 57 ADRs have a `## Revisit trigger`** section (P20.1 must give each a backlog id).
4. Ledger §3.1's "conflict magnets" hypothesis is **falsified** (0 conflicts, (iii)).
5. `usaspending` was fetched live in P07.3 while `UNDETERMINED` and un-permitted — the trace bypassed the loader gate (LD-X08 answered: **no**, `ingestion_permitted` was never true for it). P19.2 should record this as a process finding, not a rights violation (public-domain federal data).
6. The J-1 slice never went through the source registry (7/8 fixture sources unregistered) — a seam P19.2 must classify (SIG-INGEST-023/038 vs the P06.1 hard gate).
