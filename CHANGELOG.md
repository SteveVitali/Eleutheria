<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — unreleased (tag cut by the operator per `docs/build/INTEGRATION_PLAN.md`)

First tagged snapshot of the Surveillance Infrastructure Graph (SIG): the complete
specification-driven build (Phases 0–18), the post-build capstone, reconciliation and
release-readiness chain (Phases 19–20), and the Phase-21 operationalization chain that runs the
system as composed local staging (Phases 21.1–21.9). A buildable, fully-tested reference
implementation — **not a running service** (nothing deployed; no source fetched live). Full detail:
[`docs/build/RELEASE_NOTES_v0.1.0.md`](./docs/build/RELEASE_NOTES_v0.1.0.md).

> **Phase 21 — operationalization (local staging, no live sources).** SIG now runs as a composed
> system for one real jurisdiction (Oklahoma City), end-to-end, without fetching a live source: the
> `ingestion_permitted` gate stays fail-closed (HG-03 pending), so every connector run is
> fixture-backed replay/shadow. **No version bump:** this is staging, not live; go-public is gated on
> HG-01 + HG-11 (`docs/build/PUBLICATION_CHECKLIST.md`), and the `0.2.0` "first public jurisdiction"
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

### Known limitations (conforming, tracked)
- Nothing is deployed and **no source has been fetched live**: the `ingestion_permitted` gate is
  fail-closed (HG-03 pending), so all connector runs are fixture-backed replay/shadow and no
  jurisdiction is published. Go-public is gated on HG-01 (legal home) + HG-11 (operating governance)
  and the `docs/build/PUBLICATION_CHECKLIST.md`.
- Resolved since the capstone (Phase 21): `LD-V08` — the web now reads export bytes, not just
  committed fixtures, so the OKC dossier renders the contradiction from the export (P21.4); PG
  persistence of contradiction/coverage/task objects is ACCEPTED as compute-on-read under A5/HG-14
  (P21.2); the web curation surface shipped (A6 → P21.6). The interactive MapLibre map island
  (`SIG-UI-047`, A1) remains **not built by design** — the static-PMTiles serving contract stands in
  without bundling the maplibre-gl runtime (P21.5, ADR-051/067).
- Deferred human-gated steps (not defects): the moderated onboarding usability study is landed but
  **not yet run** (HG-10); Zenodo/live-mirror deposits and live MapRoulette pushes refuse until their
  gates are ticked (HG-07/HG-08). Tracked in `docs/build/BACKLOG.csv` and the Phase-21 risk register.

[0.1.0]: https://github.com/SteveVitali/Eleutheria/releases/tag/v0.1.0
