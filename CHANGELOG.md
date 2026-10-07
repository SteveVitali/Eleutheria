<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Post-`0.1.0` changes land here first, each entry naming its ticket and
requirement ids (G3 §9.4, SIG-REL-014). At each tag the heading becomes
`## [0.N.0] — tagged by the operator (see git show v0.N.0)` — the tag object
carries the true date, so no date is typed here — and the section ends with
"Production releases built from this range: …". A PR touching the
public-behaviour path set (`web/src/pages/**`, `web/src/layouts/**`,
`api/src/api/{routes,app,models}.py`,
`exports/src/exports/{release*,spine_export,manifest}.py`,
`ops/public_routes.toml`, `ops/disclosures.toml`, `policy/**`,
`ontology/src/**`) must add an entry here or carry a
`Changelog: none (<reason>)` commit trailer — the `docs` CI job enforces it
(`docs/build/tools/changelog_gate.py`).

### Added

- **Release-archive chrome + same-origin link crawl** (P34.34a; cites
  SIG-FIND-001/002, SIG-UI-033, SIG-UI-024, SIG-LIC-011, SIG-UI-049) — every
  exports-rendered page now carries site navigation, a `/dispute/` link, and
  the licence of the data shown; `validate_release` and `activate` crawl
  every page's same-origin `href`/`action` and refuse unresolved links
  (withdrawal 410 tombstones resolve); `record_claims` rows and claim
  anchors carry the sparse `access_kind` field via the reconciler
  vocabulary; dossiers state their provisional computed posture and link
  from release landings; zero-record landings explain themselves as
  verified-empty publications; `build_spine_export` always emits
  `web/leverage.json` (the recorded changeset feed folded in, else the
  honest zeroed ledger — never a live fetch).
- **Versioning discipline + one version source** (P34.23, SIG-REL-014) —
  every package derives `__version__` via `importlib.metadata` (no `0.0.0`
  reported anywhere); `scripts/bump_version.py` bumps all 14 pyprojects and
  `web/package.json` together (dry-run default); `resolver_version` in
  export manifests is now the `resolution` package version + `+g<commit8>`
  instead of the exports placeholder; the CHANGELOG gate joins the `docs`
  CI job; `docs/build/reports/releases/` holds the operator tag procedure,
  `TAG_TEMPLATE.md`, and the prepared `TAG_v0.1.0.md` (not tagged —
  operator action, OP-08).

### Changed

### Deprecated

### Removed

### Fixed

- **Archive link depth, zero-record validation, and the empty-tile build**
  (P34.34a) — record/evidence links in nested release routes are
  site-root-absolute (`/r/<pub>/…`), removing the depth-fragile `../../`
  forms by construction; `validate_release` no longer misreads a legitimate
  `indexed_records == 0` scope as missing (a zero-record release was
  unvalidatable); a zero-archive tile manifest no longer fails the web
  build — `/map/` states the absence honestly in export mode; and the
  journey verifier's browse needle was updated to the new link shape.
- **API honesty: scope, completeness, bytes, terms, basis, grants** (P34.25,
  S0 RI-02, SIG-SEC-011; extends SIG-REL-010) — `/v1/dossier/{scope}` and
  `/v1/coverage/{scope}` now answer a typed 404 `scope_not_available` for a
  scope the store does not hold (the arbitrary 25-subject dossier fallback is
  removed); coverage never reports `complete: true` with zero evaluated
  records; `bytes_available` is claimed only for public-tier captures recorded
  byte-bearing (`capture_classification = 'actual'`), with
  `bytes_unavailable_reason` disclosing why otherwise; the hand-seeded OKC
  fixture sources never appear in live PostgreSQL answers; `/terms` no longer
  names a nonexistent editorial board or counsel; every response carries the
  `X-SIG-Basis: live-spine` header and a `basis` body field; and the
  `sig_read_public` role is narrowed by the `public_read_allowlist` migration
  to exactly the published read surface.
- **Release-search states tell the truth** (P34.36; cites SIG-FIND-003,
  SIG-UI-040, SIG-UI-050; owns S1 F-154 at the fixture layer) — the
  released-corpus search's empty page now asserts only that no released
  record in the compartment matches (the "recorded absence" claim is
  removed); HTML clients get a real HTML error page for every error status
  (`format=html` or `Accept: text/html`, including a search-scoped 422 for
  malformed parameters) while JSON clients keep the `{detail, code}`
  contract; `eligible_records` and `excluded_records_by_reason` now count
  records the current policy withholds at access time (the `denied` hook
  carries the public-safe reason category; `indexed_records` stays the
  pinned index truth); the no-JS pager names the actual `limit`, drops the
  duplicated browse sentence, and humanises display labels while wire
  values stay raw; non-record compartments (`metadata`, `web`,
  `web_mixed`, `code`, `ontology`) answer 404 `compartment_not_searchable`
  instead of a readiness 503, and `build_release` fails closed if one ever
  carries `sites.jsonl`; a zero-record release reports completeness
  `not_evaluable` instead of `complete`.

### Security

## [0.1.0] — unreleased (REL.1 marker skipped-by-operator; the current integration plan has no tag step — `docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md`)

First tagged snapshot of the Surveillance Infrastructure Graph (SIG): the complete
specification-driven build (Phases 0–18), the post-build capstone, reconciliation and
release-readiness chain (Phases 19–20), and the Phase-21 operationalization chain that runs the
system as composed local staging (Phases 21.1–21.9). Full detail:
[`docs/build/reports/RELEASE_NOTES_v0.1.0.md`](./docs/build/reports/RELEASE_NOTES_v0.1.0.md).

> **Post-Phase-21 chain (rows 67–198, dated history — see `docs/build/BUILD_INDEX.md`).** The chain
> continued through go-live and Round 10: the GCP deployment executed 2026-09-15
> (`docs/build/reports/GCP_DEPLOYMENT.md`, ADR-081); HG-01 was satisfied at an interim posture and
> HG-11 was granted 2026-09-27, so the public surface is **live at https://surveillancegraph.org**
> (launch record 2026-09-24; republish 2026-09-27 over a ~2.4M-claim spine — green-reviewed sources
> were fetched live); the national publish, hosted materialization, partner registries and the
> research-queue/records flows landed in P25–P31. **Round 10 (P32/P33)** added typed assertions +
> actual-capture bindings, the shared bitemporal contract, immutable `r/<publication>` release
> namespaces + compartmented FTS5 search, the coordinated workspace, durable anonymous intake
> (built; `operational=false` — answers `503 receiver_not_operating`), the three dossier packets
> (`mechanical_complete`, `review.status=not_run`), the shadow evaluator + preregistered human-eval
> campaign tooling (deferred spine — no human labels), the provisional-ruleset release candidate
> (**staging-only**; production exposure `D-R10-PUBLISH-1` remains OPEN), and the build-memory
> v2 projections/closeout machinery. GATE-ACCEPT signed 2026-09-28 accepting the register as
> presented: **36 owed obligations + `SIG-MEM-004`** remain — see `docs/tickets/DEFERRALS.md` and
> `docs/build/OPERATIONAL_READINESS.md` §(f).

> **Phase 21 — operationalization (local staging, no live sources).** SIG now runs as a composed
> system for one real jurisdiction (Oklahoma City), end-to-end, without fetching a live source: the
> `ingestion_permitted` gate stays fail-closed (HG-03 pending), so every connector run is
> fixture-backed replay/shadow. **No version bump:** this is staging, not live; go-public is gated on
> HG-01 + HG-11 (`docs/build/reports/PUBLICATION_CHECKLIST.md`), and the `0.2.0` "first public jurisdiction"
> cut-over is a later, human-gated decision. The chain (each a stacked PR):
>
> - **P21.1** (#56, ADR-063) — 27 rights-review packets + the registry `review-status`/flip rule; the 19-project Stage-0 outreach record. Nothing flipped (`loadable now: 0`).
> - **P21.2** (#58) — annotation-layer alignment tests; contradiction/coverage/task persistence ACCEPTED as compute-on-read under A5/HG-14 (shrunk, no new persistence).
> - **P21.3** (#59, ADR-065) — live connector wiring behind the gate: the `httpx` transport, the OCFL capture store, and `sig-connectors run --mode live|replay|shadow` (refuses a non-green live fetch, exit 3).
> - **P21.4** (#60, ADR-066) — runtime composition: `sig-ops up/status/down/seed` (`ops/docker-compose.yml`, PG18+PostGIS + API + static), the export-backed web data layer (`web/src/lib/data.ts`, `SIG_DATA_SOURCE=fixtures|export`), and `docs/build/tools/run_okc.sh` — the OKC dossier renders the 299-vs-190 contradiction from the export bytes (LD-V08 crossed).
> - **P21.5** (#61, ADR-067) — infrastructure: `sig-exports deposit` (Zenodo), `push` (object store/CDN, R2 with S3/CloudFront documented), `tiles` (real PMTiles), `.torrent` mirrors, `sig-ops egress-report`, and `sig-ops degraded` + the monthly keepalive (the $0-beyond-static posture). A1 ticked — no MapLibre island.
> - **P21.6** (#62, ADR-068) — the authenticated curation service (`sig-api serve-curation`, enabled only by `SIG_CURATION_ENABLED=1`, never on the public API) + the `/curate/**` progressively-enhanced web surface.
> - **P21.7** (#63, ADR-069) — contribution-back live: the MapRoulette client (dry-run without a key, sensitive tiers never pushed), the OSM changeset feed → `LeverageLedger`, the Organised Editing activity record, and opt-in aggregate-only onboarding timing.
> - **P21.8** (#64, ADR-070) — the first-class `data_driven` connector (release-as-unit-of-ingestion, per-agency aggregate rows only) and the coarse-international reference-capture path.
> - **P21.9** (#65, ADR-071) — the `pathways` connector (three per-family extractors) + the ADR-033-deferred layer-3/4 parser engines in `parsing/`, enforcing `procured` ≠ `deployed`; retires RISK-P17-03.

### Added
- **Domain model & ontology.** LinkML ontology + SKOS vocabularies + deterministic generators
  (`ontology/`); the append-only claim/evidence spine L0–L3 with RLS on PostgreSQL 18 + PostGIS
  (`db/`); the OCFL content-addressed evidence store (`evidence/`); EDTF temporal semantics, as-of
  functions, and PROV-O lineage.
- **Identity & resolution.** Jurisdiction/organization registries, deterministic and probabilistic
  entity resolution (`resolution/`), the deterministic `RESOLVE` engine and §29 reconciliation
  workflows (`reconcile/`), `Contradiction` as a first-class object, coverage/negative-space metrics
  and the research-task engine (`inference/`, `tasks/`).
- **Acquisition.** The eight-stage connector framework with rate-limit/robots, licence gate, replay
  and shadow mode (`connectors/`); twelve fixture-tested connectors (osm, atlas, flock_portal,
  audit_structural, accountability, procurement, records, france_belgium_procurement/records, and —
  added in Phase 21 — data_driven, coarse_international, pathways); the
  parsing stack (`parsing/`); the source registry with per-source rights records (fail-closed
  `ingestion_permitted` gate).
- **Delivery.** The read API with resolution envelope, as-of, dereferenceable IDs and `/changes`
  (`api/`) served over PostgreSQL; exports with per-compartment licence computation and the ODbL
  split (`exports/`); the zero-JS Astro web shell with dossier, static map, network explorer,
  watch/evidence, corrections and methodology surfaces (`web/`).
- **Governance & policy.** The executable crawler/licence/publication/threat policy package
  (`policy/`) and the prose governance/safety policies (`docs/governance/`).
- **Engineering.** uv workspace of 14 members (SIG-ENG-011/012); `make check` CI gate mirrored in
  `.github/workflows/ci.yml` (Python `python` job incl. `tests/db`; `web` job incl. e2e + a11y +
  licence + perf); PEP 751 `pylock.toml` export and CycloneDX SBOM targets.
- **Build memory & reconciliation.** `docs/build/` (planning ledger, build index, decision memo,
  coverage matrix over 671 requirement ids, capstone closure with the operator-signed 76-row
  ACCEPTED-deviations list, backlog, operational-readiness map, ticket-vs-spec reconciliation);
  Appendix F rebuilt to repository ADR numbering; ADR-001…062.
- **Release readiness (this ticket, P20.3).** `docs/build/tools/merge_dryrun.sh` (read-only merge
  dry-run), `docs/build/INTEGRATION_PLAN.md`, `docs/build/CI_STATUS.md`, version bump to `0.1.0`
  across all members, these release notes, `CITATION.cff`, `CHANGELOG.md`, `CONTRIBUTING.md`.

### Changed
- Spec reconciliation (P20.2): eight normative amendments (A1–A8) applied at `spec_src`; three
  requirement ids folded back (`SIG-UI-047`, `SIG-EVID-020`, `SIG-ENG-039`); spec id count 668 → 671.
- Capstone spine wiring (P19.4/P19.5): connector claims persist to PostgreSQL (`PgClaimSink`), the
  read API is served over PG (`PgReadStore`), entity resolution and the review queue run over PG, and
  the export gate honours `derivative_permitted`.

### Known limitations (conforming, tracked — refreshed 2026-09-28, P33.7)
- The `ingestion_permitted` gate stays **fail-closed per source**: green-reviewed sources are fetched
  live by the hosted scheduled jobs (the national publish's ~2.4M claims), while every source whose
  review record is not green still gets a refused `run --mode live` (exit 3). Sources left to review
  or unblock are the `D-SOURCES.*`/`D-JURIS.2-1`/`D-R10-SOURCES-1` rows of
  `docs/tickets/DEFERRALS.md`; publication gating is recorded in
  `docs/build/reports/PUBLICATION_CHECKLIST.md`.
- The Round-10 **provisional-policy release candidate is published to staging only**: production
  exposure (`D-R10-PUBLISH-1`), the hosted recovery/freeze (`D-R10-LIVE-1`) and the production
  candidate build (`D-P32.23a-1`) are open operator obligations. The public site currently serves the
  prior HG-11-signed national publish.
- The anonymous **correction receiver is built but not operating** (`[intake].operational=false`;
  `503 receiver_not_operating`; `D-P32.16-1`), and the independent **human-evaluation spine is
  deferred** (`D-R10-HUMAN-1`, `D-R6.1-EVAL` — no human labels exist; the evaluator runs shadow-only).
- Resolved since the capstone (Phase 21): `LD-V08` — the web now reads export bytes, not just
  committed fixtures, so the OKC dossier renders the contradiction from the export (P21.4); PG
  persistence of contradiction/coverage/task objects is ACCEPTED as compute-on-read under A5/HG-14
  (P21.2); the web curation surface shipped (A6 → P21.6). The `/map/` surface later gained an
  **opt-in MapLibre + PMTiles island** (P27.9, ADR-097; per-island budgets ADR-134/P32.15) — all
  other public content pages remain zero-JS.
- Deferred human-gated steps (not defects): the moderated onboarding usability study is landed but
  **not yet run** (HG-10 / `D-R10-USERS-1`); Zenodo/live-mirror deposits and live MapRoulette pushes
  refuse until their gates are ticked (HG-07/HG-08; `D-P21.5-1`, `D-P21.7-1`). All owed work is
  tracked in `docs/tickets/DEFERRALS.md` (36 rows + `SIG-MEM-004`) and `docs/build/BACKLOG.csv`.

[0.1.0]: https://github.com/SteveVitali/Eleutheria/releases/tag/v0.1.0
