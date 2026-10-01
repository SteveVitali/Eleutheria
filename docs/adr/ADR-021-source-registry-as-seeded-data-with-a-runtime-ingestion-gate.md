# ADR-021: Source registry as seeded data, with a runtime ingestion gate in `connectors`

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P00.4
- **Requirement ids:** SIG-INGEST-023, SIG-INGEST-024, SIG-INGEST-027, SIG-INGEST-028, SIG-INGEST-038, SIG-LIC-001/003/004
- **Spec:** docs/2_canonical_design_spec.md §22 (§22.1–§22.6), §10.3.1, §10.4

## Context

§22 describes a source registry in prose; a registry described in prose is not
executable (SIG-ENG-001). Phase 0 must seed it with every §22.6 / §22.3 source,
each carrying rights, a custody posture, a compact status, and an
`ingestion_permitted` flag — and the pipeline must refuse to run a connector
whose row does not permit ingestion (SIG-INGEST-028). The rights model and export
gate already exist in `policy` (P00.2); this ticket populates them, it does not
re-author them.

## Decision

Seed the registry as **data, not code**: one TOML row per source in
`connectors/src/connectors/data/sources.toml` (and `local_groups.toml` for the
SIG-INGEST-039/-040 ecosystem registries), loaded and validated by
`connectors.registry` / `connectors.ecosystem`. The registry lives in the
`connectors` package because SIG-INGEST-* are ingestion requirements and the
`ingestion_permitted` gate is a *connector-loader* concern
(`connectors.loader.run_connector`); `connectors` therefore depends on
`sig-policy` and each row's rights are a `policy.rights.RightsRecord` that the
existing export gate scores unchanged.

Two postures are load-bearing: `ingestion_permitted` defaults **false** (a source
is inert until reviewed), and a source whose rights the lead research pass did not
resolve is `UNDETERMINED` + `redistributable=false` — the fail-closed default —
rather than a guessed licence (SIG-LIC-004). `redistributable` is always an
explicit reviewed field, never derived from the SPDX string (SIG-INGEST-024).

## Consequences

Adding or re-verifying a source is a reviewed data row, never a schema or code
change. Unresolved rows fail the export gate closed automatically. Phase-4
connectors load through `connectors.loader`, so the gate cannot be bypassed. The
cost is that per-source rights review and ecosystem-project discovery remain
ongoing agentic tasks (RISK-P0-19), with `UNDETERMINED` as the honest interim.

## Alternatives considered

A dedicated `registry` package (rejected — not in the fixed §47 layout, and it
would split the gate from the loader that enforces it); Python-literal seed data
(rejected — SIG-ENG-001 wants executable *data*, and TOML matches the
`policy/data/*.toml` convention); inferring `redistributable` from the licence
string (rejected — SIG-LIC-003 forbids it); a "public record" pseudo-licence for
government sources (rejected — not an SPDX expression; `UNDETERMINED` with a note
is the honest posture until reviewed).

## Revisit trigger

The §47 layout gains a dedicated ingestion/registry package; or the per-source
row needs a field the `policy.rights.RightsRecord` cannot carry; or the source
count grows past the point where a single flat TOML is maintainable and the seed
needs to be partitioned per layer.

### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): LIKELY FIRED

Evaluated at Round-11 Stage B, T1 (unit SEED-11d, 2026-10-01T07:49:22Z) from F3 §5.1
(`docs/build/planning/2026-09-30-next-phase/research/F3-backlog.md`) and the Round-11 plan
(`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`); an agent evaluation, not an operator
decision. **The trigger likely fired:** a single 7,534-line `sources.toml` holds 342 sources, with
rights-field drift (E4 NEW-10, B1 NEW-5; F3 §5.1). **Answer:** row P37.6 (registry rights-record hygiene:
index, packet decision lines, field validation). Partitioning the registry is not planned in Round 11; if
P37.6 partitions it, P37.6 records that by a new ADR. The decision above stays in force until that answer
lands; this ADR's body is unchanged (SIG-ENG-003).
