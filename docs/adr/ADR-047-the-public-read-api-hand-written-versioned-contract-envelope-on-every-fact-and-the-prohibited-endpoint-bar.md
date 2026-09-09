# ADR-047: The public read API — a hand-written, versioned contract, the resolution envelope on every fact, and the prohibited-endpoint bar

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P14.1
- **Requirement ids:** SIG-API-001, SIG-API-002, SIG-API-003, SIG-API-004, SIG-API-005, SIG-API-006, SIG-API-007, SIG-API-008, SIG-API-009, SIG-API-011, SIG-API-012, SIG-API-013 (SIG-API-010 GraphQL is a SHOULD, deliberately not taken)
- **Spec:** docs/2_canonical_design_spec.md §37 (the public API): §37.1 principles, §37.2 as-of semantics, §37.3 shape, §37.4 access tiers and anti-misuse

## Context

P14.1 owns the versioned wire contract of the public read API — the surface every
consumer (and, via the same code path, the P14.2 exports, SIG-EXPORT-003) reads SIG
through. §37 is unusually prescriptive: the API must be hand-written (never a schema
reflection), must never return a bare value (every material fact carries its full
resolution envelope), must accept and echo both as-of axes (never an implicit "latest"),
must be dereferenceable and content-negotiable at `/id/{type}/{uuid}`, must expose a
`/changes` feed, must enforce access tiers that never reach `restricted`/`sealed`, and
must NOT expose any of the four Part VIII prohibited surfaces (device-liveness, per-person
lookup, sealed bytes, over-precise coordinates).

The engines the API needs already exist and are consumed as-is:

- **the resolver** (`reconcile.resolve.RESOLVE` → `Resolution`, P08.1) — the envelope;
- **the two-axis as-of contract** (`db.temporal.AsOf`, P02.3) — explicit defaults + echo;
- **coverage** (`inference.coverage.CoverageRecord`, P09.1) — the §32.2 statement;
- **the snapshot-diff layer** (`reconcile.snapshot_diff.diff_series`, §29.7) — `/changes`;
- **coordinate sensitivity** (`policy.sensitivity.apply_tier`/`geo_tier_for`, §19.4);
- **evidence tiers** (`evidence.tiers.public_representation`, §17.5) — sealed/restricted;
- **licence + attribution** (`policy.licensing`, `policy.rights`, §42.4).

There is no in-Python fetch-by-id / query layer yet (the `db` package is a schema plus
in-memory helpers). So the API cannot be built as a thin DB wrapper.

## Decision

1. **FastAPI, hand-written models, versioned under `/v1` (SIG-API-001).** The wire
   contract is a set of authored Pydantic models (`api.models`), not a reflection of the
   storage schema; OpenAPI is generated from those models. `fastapi` + `uvicorn` are added
   as `sig-api` runtime deps; `httpx` (dev) drives the Starlette `TestClient`.
   `sig-api serve` runs the app under uvicorn over a demo store. FastAPI's DI markers
   (`Depends`/`Query`/`Header`) are call-in-default by design, so ruff's B008 is
   configured to treat exactly those three calls as immutable (`extend-immutable-calls`) —
   scoped narrowly, every other B008 case still errors.

2. **A `ReadStore` seam, not a DB coupling.** The endpoints read through a
   `ReadStore` Protocol (`api.store`) with a deterministic `InMemoryStore` implementation;
   production wires the same Protocol to Postgres later. This keeps SIG-API-001's
   "storage stays refactorable" literally true and lets the whole §37 surface be tested
   without a database. The store's one load-bearing rule is **belief-time filtering**:
   `claims_for(..., as_of_belief)` returns only claims asserted on or before the belief
   instant, which is what makes a belief-pinned request reproducible after a correction
   (SIG-API-006) — a correction is a *new* claim asserted later (append-only, P1–P3), and
   a past-belief read cannot see it.

3. **The value only ever leaves the API inside an envelope (SIG-API-002).**
   `api.envelope` is the single adapter from `Resolution` to `ResolutionEnvelope`;
   `RESOLUTION_ENVELOPE_FIELDS` is the one source of truth for the required §37.1 field set,
   used by both the model and the contract test. Every `/v1` read response also carries a
   coverage statement (SIG-API-003); collections carry a computed licence statement and
   entities carry upstream attribution (SIG-API-004), both reusing `policy.licensing`.

4. **Belief-pinning drives cacheability, with no wall-clock race (SIG-API-006).** A request
   is belief-pinned iff `as_of_belief` was supplied explicitly — an explicit belief is a
   fixed, reproducible assertion-time cut → `Cache-Control: public, max-age=1y, immutable`.
   A *defaulted* belief resolves to a fresh "now" on every request → `no-store`. The
   decision is purely "was belief given", so it never depends on a second wall-clock read.

5. **The prohibited-endpoint bar is structural and fail-closed (SIG-API-012).**
   `api.prohibitions` asserts at app construction (and in a contract test) that no mounted
   route path matches a prohibited surface, and the generic `/entity/{type}/{id}` route
   refuses per-person entity types (`person`, `individual`, `citizen`, …) as defence in
   depth. Sealed/restricted bytes cannot leak because captures are only ever served through
   `evidence.tiers.public_representation`; coordinates are reduced through
   `policy.sensitivity.apply_tier` at the sensitivity tier before they reach the wire.

6. **`restricted`/`sealed` captures are served as their designed public representation, not
   blocked.** SIG-EVID-009/010 defines a metadata-only public view for a sealed capture
   (existence, source, date, digest, claims — no bytes) and a redacted-excerpt view for a
   restricted one. That representation IS the tier gate for a capture; the bytes are gated
   separately and never reach this surface. This is consistent with SIG-API-012 (which
   forbids sealed *bytes*, not their existence metadata) and with SIG-API-011 (whole
   `restricted`/`sealed` *records* — entities — are refused to every tier via
   `assert_public_visibility`, which returns a generic 404 that does not confirm the tier).

## Consequences

- **Scope stays inside P14.1.** `/export` is an *index* of the bulk artifacts P14.2 builds;
  the read API computes no bulk artifact and no export licence (that is P14.2 /
  SIG-EXPORT-*). GraphQL (SIG-API-010, a SHOULD) is not added — REST is the only surface,
  which is exactly what SIG-API-010 requires when GraphQL is absent. No public web surface
  is built (Phase 15).
- **Additive, no prior contract broken.** A new package plus a new `/v1` surface; the only
  shared-file changes are the workspace lock (new deps), the api `pyproject.toml`, and the
  narrowly-scoped ruff B008 allowance. No prior ticket's wire names, IDs, or schema change,
  and the ontology generation gate is untouched (no schema edits).
- **The date-only as-of coercion follows `db.temporal` repo-wide** (a bare date resolves to
  midnight UTC), rather than the API inventing an end-of-day rule — consistency with the
  SQL `claim_as_of`/`resolution_as_of` filters matters more than local convenience.
- **The `InMemoryStore` is the test/demo backend, not production data.** The production
  `ReadStore` (Postgres-backed) is wired with orchestration, as with the connectors
  (ADR-028/029/042); nothing in this ticket persists or fetches canonical data.

## Revisit trigger

Revisit when the production `ReadStore` is wired to Postgres (orchestration phase): confirm
the belief-time filter, coordinate reduction, and tier gate hold identically against real
storage, and that the SQL `claim_as_of`/`resolution_as_of` filters produce the same
belief-pinned reproducibility the in-memory store proves. Revisit when P14.2 lands, to
confirm the exports reproduce this envelope response shape via the same code path
(SIG-EXPORT-003) and to move any bulk/export-licence computation there (never into the read
API). Revisit if a GraphQL surface (SIG-API-010) is added — it must remain a secondary
surface over the same `ReadStore`, never the only one — or if a new sensitivity tier /
prohibited surface is introduced, which must extend `policy.sensitivity` and
`api.prohibitions` rather than be special-cased in a route.
