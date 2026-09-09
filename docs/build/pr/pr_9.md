## Summary

Implements **P03.1 — Jurisdiction and Organization identity registries** (`docs/tickets/P03.1__identity-registries.md`), the first half of Phase 3: *stable identity before anything is counted*. Spec: `docs/2_canonical_design_spec.md` §11.1–11.3, §14.2–14.5, §16, App C.4.

The physical registry tables (`jurisdiction`, `organization`, `organization_relation`, `entity_identifier`) shipped verbatim in P02 (App C.4). This PR adds the **identity substrate** on top of them, in the `resolution/` package, as pure, tested domain logic — plus the two controlled vocabularies §14 mandates, added to the LinkML source of truth and regenerated.

Out of scope (P03.2 / P05, deliberately absent): `normalize_org_name()`, the identifier crosswalk, the deterministic cascade, public `sig:` minting, probabilistic ER, and any `Person` creation.

## What changed

- **`resolution/geoid.py`** — fixed-width Census GEOID validation with an explicit level (SIG-IDENT-005); a 7-char value is shared by four levels, so the level is required.
- **`resolution/geometry_precision.py`** — `GeometryPrecision` + the agency-centroid guard: `organization_centroid_or_unknown` is barred from point-in-polygon and address use, and travels stored with its geometry (`LocatedPoint`) (SIG-IDENT-004).
- **`resolution/identity.py`** — identifiers as sets of `(scheme,value)` (006); the two independent axes `organization_class × Role` (010); `OrgStatus` (018); the immutable six-field `IdentityBasis` + idempotent surrogate minting + publication-review routing (012, ONTO-013); colon agency-name parsing (011).
- **`resolution/jurisdiction.py`** — overlapping self-referential hierarchy, pluggable code systems, and temporally-versioned geometry via `boundary_as_of` (ONTO-010/011).
- **`resolution/temporal_identity.py`** — reified, bitemporal `OrganizationRelation` with the seven-value vocabulary (016); `rename_organization` = new version + dated alias, provably **no** succession relation and **no** new identifier (017); the five worked succession fixtures — absorb / merge / split / rename / vendor-acquire — and the municipality↔department `parent_of` pair (009, 019).
- **`resolution/registry_ingest.py`** — a zero-record ingest fails the run and distinguishes absent from not-observed, reusing the P02.3 four-state absence model (008).
- **`resolution/cli.py`** — real sub-commands (`geoid`, `agency-name`, `relation-types`) while keeping the SIG-ENG-013 help path.
- **`ontology/src/ontology/schema/common.yaml`** (+ regenerated `ontology/generated/**`) — new `OrganizationRelationType` (7 values) and `GeometryPrecision` enums (ADR-007 single source of truth).
- **`docs/traceability.md`, `docs/risk_register.md`** — phase-gate updates.

## Design decisions

- **No schema change / no CHECK constraints added.** The canonical App C.4 DDL already exists and deliberately uses free-text `relation_type`/`status` columns; vocabulary is enforced in the ontology + `resolution/`, not by a CHECK the spec omits. `geometry_precision` is not a column in the canonical DDL (it is a precision tag on the geometry claim), so none was added.
- **`operating_relationship` reuses the fourteen-role `Role` vocabulary** rather than minting a competing enum — "purchaser but not operator" is a role over a deployment.
- **No design deviation**, so no new ADR (recorded in the risk register).

## Verification

- `SIG_REQUIRE_DB_TESTS=1 make check` → **green**: ruff lint + format-check, mypy (all packages), full pytest suite **672 passed** (baseline 587 + 85 new), and `make verify-gen` clean (regenerated ontology artifacts match).
- New tests: `tests/resolution/{test_geoid,test_geometry_precision,test_identity,test_jurisdiction,test_temporal_identity,test_registry_ingest,test_vocab_conformance}.py` and `tests/db/test_identity_registry.py` (exercises the real PG18+PostGIS registry tables via testcontainers).
- An independent fresh-context review confirmed every requirement ID is correctly implemented and behaviour-asserted.

## Acceptance criteria → evidence

| Ticket AC (req id) | Evidence |
|---|---|
| GEOIDs fixed-width + explicit level (IDENT-005) | `resolution.geoid.validate_geoid`; `test_geoid.py` (7-char ambiguity, wrong-width/missing-level rejected); `test_identity_registry.py::test_jurisdiction_requires_an_explicit_level` |
| Municipality ≠ police dept, joined by parent_of (IDENT-009) | `temporal_identity.municipality_department_pair`; `test_temporal_identity.py::test_municipality_and_department_are_distinct_joined_by_parent_of`; `test_identity_registry.py` (physical) |
| Five succession fixtures; rename → no succession, no new id (IDENT-016/017/019) | `absorb`/`merge`/`split`/`rename_organization`/`acquire`; `test_temporal_identity.py::{test_absorb_fixture,test_merge_fixture,test_split_fixture,test_rename_produces_no_succession_and_no_new_identifier,test_acquire_fixture_transfers_product_ownership}` |
| Agency centroids rejected for PIP; precision stored (IDENT-004) | `resolution.geometry_precision` (`assert_point_in_polygon_usable`, `assert_usable_as_address`, `LocatedPoint`); `test_geometry_precision.py` |
| Zero-record ingest fails run; absent ≠ not observed (IDENT-008) | `resolution.registry_ingest`; `test_registry_ingest.py` |
| Jurisdiction geometry temporally versioned (ONTO-011) | `resolution.jurisdiction.boundary_as_of`; `test_jurisdiction.py::test_boundary_as_of_returns_the_version_in_force`; `test_identity_registry.py::test_jurisdiction_boundary_is_temporally_versioned` |
| Identifiers as sets (IDENT-006); two axes (IDENT-010); status vocab (IDENT-018); surrogate basis (IDENT-012); colon parse (IDENT-011); single-entity org (ONTO-012); surrogate review (ONTO-013) | `resolution.identity`; `test_identity.py`, `test_vocab_conformance.py` |
| Phase-gate: CI green + tests; ADRs for deviations; traceability + risk register updated | `make check` green; `docs/traceability.md` (P03.1 section) + `docs/risk_register.md` (Phase 3 / P03.1); no deviation → no new ADR |

Implements `docs/tickets/P03.1__identity-registries.md`. Stacked on `devin/p02-3-temporal-provenance`.

Generated with [Devin](https://devin.ai)

