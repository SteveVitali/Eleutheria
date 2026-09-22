<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# SIG v0.1.0 — release notes (draft; tag cut by the operator)

> **Status.** These notes are **drafted** by ticket P20.3. **No tag exists yet** and nothing is
> deployed. The operator cuts the `v0.1.0` tag and GitHub release **after** integrating the stack,
> using the copy-pasteable procedure in [`INTEGRATION_PLAN.md` §(d)](./INTEGRATION_PLAN.md). This
> file is the `--notes-file` that procedure references.

`v0.1.0` is the **first tagged snapshot** of the Surveillance Infrastructure Graph (SIG): the full
specification-driven build of the evidence-first, append-only graph of public surveillance
infrastructure — the 46-ticket phased build (Phases 0–18) plus the 8-ticket post-build capstone,
reconciliation and release-readiness chain (Phases 19–20). It is a **buildable, fully-tested
reference implementation**, not a running service.

## What this release is — and is not (defining standard §3.1)

**It is:** every §47 package built and unit/integration/DB/e2e-tested; `make check` green
(**2418 passed, 1 xfailed**); the claim spine wired over real PostgreSQL 18 + PostGIS; the OCFL
evidence store; the read API over the PG store; export licence-compartment computation; the zero-JS
Astro web shell; the connector framework with nine connectors; the executable policy/governance
package; the full canonical spec (671 requirement ids) and its traceability.

**It is NOT live, and the release says so plainly (no synthetic certainty about readiness):**

- **Nothing is deployed.** There is no Dockerfile/compose/deployment manifest in the repo, no object
  store, no CDN, no Zenodo deposit, no running API or host. Everything runs locally or in CI
  (`OPERATIONAL_READINESS.md §(e)`).
- **No source has been fetched live.** All nine connectors are fixture-tested only; the source
  registry has **109 sources, 87 `UNDETERMINED`, 0 `ingestion_permitted`, 0 loadable** — every first
  fetch is gated behind a per-source rights review (HG-03) that has not happened (`SCOPING_NUMBERS §(ii)`).
- **No jurisdiction is published.** The Oklahoma City first-jurisdiction slice needs 6 new registry
  rows + rights packets + a live run + a host (Phase 21, gates HG-01/02/03/04/06/11/12).
- **One known `xfail`:** `tests/e2e` carries a single expected failure, `LD-V08` (the web surface
  reads committed fixtures, not the live `/v1` API) — routed to **P21.4**.
- **MAY-level / deferred surfaces are unbuilt by design:** the interactive MapLibre map island
  (`SIG-UI-047` → P21.5), PG persistence of contradiction/coverage/task objects (A5 → P21.2), and the
  web curation surface (A6 → P21.6). Conforming today; tracked in `BACKLOG.csv` (BL-051) and
  `RISK-P20-02`.

## Licence posture (SIG-LIC-005 / §42; see `LICENSE`)

SIG is **not** a single-licence project. Code is **Apache-2.0**; SIG-original graph data is
**CC-BY-4.0**; OSM-derived physical assets are **ODbL-1.0** in a physically separate compartment;
the Eyes-on-Flock–derived portal layer is **CC-BY-SA-4.0** in its own compartment; documentation is
**CC-BY-4.0**; ontology/vocabularies are **CC0-1.0**. Each source and evidence artifact carries a
separately-reviewed rights record; a source with unresolved rights is `UNDETERMINED` and fails the
export gate closed (SIG-LIC-004). Export licences are computed per compartment and the build fails on
incompatibility (SIG-LIC-010). Items referred to counsel before launch (SIG-LIC-009) are listed in
`docs/risk_register.md`.

## Capstone verdict (from `CAPSTONE_CLOSURE.md`)

- Whole-spec coverage matrix over **671** requirement ids (`COVERAGE_MATRIX.csv`).
- **76** `MET-DIFFERENTLY` rows are **ACCEPTED deviations**, operator-signed (HG-14, 2026-09-08),
  **0 rejected** — each a requirement met by a documented, sound alternative, never a silently
  loosened requirement.
- Composed end-to-end suite (`tests/e2e`) over real PG18+PostGIS/OCFL/API/exports/web: **0 failed,
  1 xfailed** (`LD-V08` → P21.4).
- The remaining non-MET rows are routed to explicit Phase-21 tickets (`CAPSTONE_CLOSURE.md §(c)`).

## What's in the stack (54 tickets — the 46 build + 8 post-build one-liners)

Full order and scope: `docs/tickets/00_MANIFEST.md`. Requirement-id → ticket map:
`docs/build/COVERAGE_MATRIX.csv`.

### Phase 0 — Foundations
- **P00.1** uv monorepo, frozen §47 package layout, CI, licence headers.
- **P00.2** Executable crawler/licence/publication/threat policy as tested code + ADR-001…020.
- **P00.3** Prose governance: takedown/corrections/suppression, CoC, anti-misuse, contributor safety.
- **P00.4** Source registry seeded; rights records, SPDX, `ingestion_permitted` fail-closed gate.

### Phase 1 — Ontology
- **P01.1** LinkML ontology + SKOS vocabularies + deterministic generators + generalization suite.

### Phase 2 — Claim spine, evidence, time
- **P02.1** Claim/evidence schema L0–L3, append-only, resolution table, RLS.
- **P02.2** OCFL evidence store, content addressing, capture pipeline, sealed tiers.
- **P02.3** EDTF, as-of functions, temporal invariants, PROV-O lineage.

### Phase 3 — Identity & ER
- **P03.1** Jurisdiction + organization registries, geometry, temporal identity.
- **P03.2** Crosswalk, `normalize_org_name`, cascade tiers 0–3, public-ID lifecycle.

### Phase 4 — Connector framework & first connectors
- **P04.1** Eight-stage connector framework, rate-limit/robots, licence gate, replay, shadow mode.
- **P04.2** `osm` connector + separate ODbL asset table.
- **P04.3** `atlas` (EFF Atlas of Surveillance) connector.

### Phase 5 — Probabilistic ER & curation
- **P05.1** Splink matcher, blocking, gold set, tiers 4–5 to review, cluster alerts.
- **P05.2** Curation/review queue (CLI + JSONL) + LLM-to-review scaffolding.

### Phase 6 — Vertical slice (hard gate)
- **P06.1** One jurisdiction end-to-end (J-1) + committed retrospective.

### Phase 7 — Parsing & acquisition
- **P07.1** Parsing stack, locators, file classification, canary drift defences.
- **P07.2** Records connectors + `RecordsRequest`.
- **P07.3** Procurement + cooperative/federal sub-awards + `FundingInstrument` + agenda registry.

### Phase 8 — Resolution & reconciliation
- **P08.1** Deterministic `RESOLVE`, ruleset-as-data, four axes, rationales, ambiguity test.
- **P08.2** The §29 reconciliation workflows (owns §29.3/§29.7 sharing + snapshot logic).
- **P08.3** `Contradiction` as a first-class object + lifecycle.

### Phase 9 — Coverage
- **P09.1** Coverage, completeness, negative space; capture–recapture prohibition.

### Phase 10 — Research tasks
- **P10.1** Detector DSL, task lifecycle, dispositions, geo queues, anti-abuse, registry.
- **P10.2** The §33.2 catalog of 34 detectors + contradiction→task map.
- **P10.3** Records-request generation + 51-jurisdiction statute templates + consent gate.

### Phase 11 — Flock portal layer
- **P11.1** `flock_portal` connector (CC-BY-SA compartment, snapshot diff, backfill, fallbacks).
- **P11.2** `audit_structural` connector (aggregates-only, Camera Count, SharedNetworks).

### Phase 12 — Usage & inference
- **P12.1** Usage aggregates + analytics boundary + small-cell suppression.
- **P12.2** Access edges (three types) + access-path closure.

### Phase 13 — Accountability, policy & legal
- **P13.1** `AccountabilityEvent` + `LegalProceeding` + `epistemic_status` + connector.
- **P13.2** `Policy` + `LegalInstrument` + policy/config divergence reconciler.

### Phase 14 — Delivery: API & exports
- **P14.1** Read API, resolution envelope, as-of, dereferenceable IDs, `/changes`.
- **P14.2** Exports + licence computation + ODbL split + crosswalk + Zenodo interface.

### Phase 15 — Web surfaces
- **P15.1** Astro shell + epistemic visual language + a11y/no-JS + citation.
- **P15.2** Local dossier + print/PDF + "what we don't know".
- **P15.3** Infrastructure map (zero-JS static PMTiles) + network explorer honest-rendering rules.
- **P15.4** Procurement/renewal watch + evidence recommender + evidence viewer.
- **P15.5** Research queue + corrections log + methodology/coverage + editorial-standards gate.

### Phase 16 — Contributors
- **P16.1** Contributor system (tiers, safety, L0 entry, revert, anti-poisoning).
- **P16.2** Contribution-back (OSM human-mediated suggestion workflow, organised-editing, hashtag).

### Phase 17 — Broader technology federation
- **P17.1** Private-camera federation + RTCC integration.
- **P17.2** Facial recognition + cell-site simulators + mobile forensics.
- **P17.3** Gunshot detection + drones + commercial location data.

### Phase 18 — International
- **P18.1** Jurisdiction-adapter framework + i18n + jurisdiction-conditional publication.
- **P18.2** France/Belgium connectors + OSM-import study.

### Phases 19–20 — Post-build capstone, reconciliation & release readiness (8 tickets)
- **P19.1** Commit tickets + planning artifacts to `docs/build/`; unify scratch; AGENTS.md; ADR-058.
- **P19.2** Independent 671-row `COVERAGE_MATRIX.csv` verdicts + seam hunt + routing (no code).
- **P19.3** Composed end-to-end suite (`tests/e2e`) over real PG18/OCFL/API/exports/web + retros.
- **P19.4** `PgClaimSink`, `PgReadStore`, ER + review queue over PG; flips xfails LD-F06b/F06/F04.
- **P19.5** `derivative_permitted` export gate, jurisdiction-conditional web render, `inference` CLI,
  remaining gap closure; `CAPSTONE_CLOSURE.md` + the ACCEPTED list.
- **P20.1** One normalized `BACKLOG.csv/.md` + `OPERATIONAL_READINESS.md` with the OKC critical path.
- **P20.2** `TICKET_VS_SPEC.md`; ADR dispositions; Appendix F/G fixes; the eight HG-13 amendments +
  three fold-backs (671 ids); ADR-062.
- **P20.3** *(this ticket)* `merge_dryrun.sh` + `INTEGRATION_PLAN.md`; `CI_STATUS.md`; version bump to
  `0.1.0`; these release notes; README/CHANGELOG/CONTRIBUTING refresh. **Merges nothing.**

## Verification at the tagged commit

- `make check` → **2418 passed, 1 xfailed** (lint + format + mypy + pytest + verify-gen).
- `make test-db` (Docker) → **114** claim-spine tests on PostgreSQL 18 + PostGIS.
- `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e` → **0 failed, 1 xfailed** (`LD-V08` → P21.4).
- `sh docs/build/tools/merge_dryrun.sh` → all open PRs merge clean; bottom-up tree matches the top PR.

## Provenance & integrity

- Append-only history (P1–P3): no branch was rewritten; the `4493b14` P12.1 hardening commit that
  landed on P14.1's branch (LD-D14) is preserved and its ADR-044 note was added in P19.5.
- The SBOM (`sbom.cdx.json`, CycloneDX) is regenerated by the operator at tag time
  (`make sbom`) and attached to the release.
