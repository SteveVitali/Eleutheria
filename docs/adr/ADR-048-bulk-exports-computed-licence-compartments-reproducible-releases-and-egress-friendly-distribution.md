# ADR-048: Bulk exports — computed-licence compartments, reproducible releases, Zenodo concept/version DOIs, and egress-friendly distribution

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P14.2
- **Requirement ids:** SIG-EXPORT-001, SIG-EXPORT-002, SIG-EXPORT-003, SIG-EXPORT-004, SIG-EXPORT-005, SIG-EXPORT-006, SIG-EXPORT-007, SIG-EXPORT-008, SIG-EXPORT-009, SIG-EXPORT-010, SIG-EXPORT-011, SIG-LIC-009a, SIG-LIC-010, SIG-LIC-011
- **Spec:** docs/2_canonical_design_spec.md §38 (exports and dataset publication) and §42.4 (export-time licence computation)

## Context

P14.2 owns the bulk-export layer: versioned multi-format artifacts whose licence is
*computed* from constituent rights, with the ODbL asset layer shipped separately from the
CC-BY graph, per-row rights provenance, the crosswalk export, a Zenodo deposit with
concept + version DOIs, and egress-friendly distribution. It owns the export
manifest/versioning contract that the Phase-15 download surfaces reference.

The licence math already existed and is reused as-is, not re-implemented: `policy.licensing`
(`compute_export_license`, `assert_export_permitted`, `downstream_obligations`,
`effective_license`, the `licenses.toml` N-compartment registry — SIG-LIC-004/004a/010/011)
and `resolution.crosswalk` (`build_sig_external_crosswalk` / `export_crosswalk`,
SIG-IDENT-033). The ODbL physical-asset rows come from `connectors.osm.physical_asset_rows`
(stamped `ODbL-1.0` / `osm_physical`). A hard constraint shaped the design: `api` and
`connectors` both depend on `sig-exports`, so **exports must not import `api`** — SIG-EXPORT-003's
"same code path the API uses" is therefore realised through the shared lower-level modules
(`policy.licensing`, `resolution.crosswalk`) that the API also calls, not through a coupling.

## Decision

1. **A release is a pure function of a `BuildSpec` (SIG-EXPORT-003).** `exports.manifest.BuildSpec`
   captures exactly the four reproducibility inputs §38.1 names — the two-axis as-of cut, the
   ruleset version, the resolver version — and derives a deterministic `release_id` (the Zenodo
   *version* identity) and a stable `concept_id` (the *concept* identity). `build_bundle` is a pure
   function: the same spec + tables produce byte-identical artifacts. This makes "a hand-built
   export is a different dataset wearing the same name" structurally detectable.

2. **The compartment is computed from the rights record, never hard-coded (SIG-LIC-004a).**
   `exports.compartments.place_table` computes each table's licence with `compute_export_license`
   and maps it to the `licenses.toml` compartment declaring that licence. An incompatible mix in
   one file raises `LicenseIncompatibilityError` and **fails the build** (SIG-EXPORT-004/SIG-LIC-010);
   a CI test drives a deliberate ODbL+CC-BY merge through it and asserts the failure. Because each
   table computes to one licence and each licence maps to one compartment directory, the ODbL layer
   and the CC-BY graph are physically separate files by construction (SIG-EXPORT-005).

3. **Silently-travelling share-alike fails closed (SIG-LIC-009a).** `effective_license` now returns
   an `upstream_license` both when it is a *known* share-alike regime **and** when it is unresolvable
   (not in the registry), so an unknown upstream forces the build to fail rather than laundering an
   obligation SIG cannot vouch for — "default to the stricter regime, not the declared one."

4. **Every row carries its rights provenance (SIG-EXPORT-006/SIG-LIC-011).** `enrich_rows` stamps each
   row with `downstream_obligations(...)` — the same function the read API uses for a collection's
   attribution (SIG-API-004) — so a consumer can determine any fact's licence without re-deriving the
   chain, and the export and API pass identical obligations.

5. **Seven deterministic format writers + a checksummed manifest (SIG-EXPORT-001).** `exports.formats`
   is a pure `rows -> bytes` writer registry for Parquet (DuckDB), CSV, JSONL, JSON-LD/RDF, SQLite,
   GeoJSON, and PMTiles. Text formats are byte-stable by construction; the binary formats carry no
   wall-clock state (gzip mtimes pinned to 0) so they are byte-identical for a fixed toolchain version.
   Tabular resources ship inside a Frictionless Data Package and evidence inside an RO-Crate — disjoint
   sets (SIG-EXPORT-002).

6. **The crosswalk is its own most-permissive, prominent artifact (SIG-EXPORT-007).** Built via the
   canonical `resolution.crosswalk` builder + its licence gate and published under
   `most_permissive_license` (added to `policy.licensing` so all licence math stays there), under a
   top-level `crosswalk/` path separate from the dataset compartments.

7. **Zenodo deposit with two DOIs; evidence bytes excluded (SIG-EXPORT-002).** `exports.zenodo` deposits
   over a `ZenodoTransport` seam (a deterministic `FakeZenodoTransport` for tests/offline, the HTTP
   client wired in production, mirroring the API's `ReadStore` seam). Evidence *bytes* are excluded by
   size; the **digest manifest** is deposited in their place so a citation still pins the exact bytes.

8. **Distribution is egress-first (SIG-EXPORT-008/009).** `exports.distribution.assert_low_egress` fails
   a build that targets a metered-egress provider ("success is the failure mode"), and the largest
   artifacts get deterministic BitTorrent-v2 magnet + IPFS CIDv1 references derived from their SHA-256.
   The plan is wired into `build_bundle` and the `sig-exports build --store` CLI.

9. **The six downstream classes are validated design targets (SIG-EXPORT-010/011).** `exports.downstream`
   encodes the §38.4 classes as data; `build_bundle` enforces that the ODbL device layer and the CC-BY
   graph are separate serving artifacts, and `Bundle.validate_portfolio` asserts all six classes are
   served by the export portfolio plus the surrounding surfaces.

## Consequences

- **Scope stays inside P14.2.** No change to the read API / envelope / as-of semantics (P14.1); no web
  surfaces (Phase 15); no new rights-record modelling or ingestion-time licence gate (P00.4) — the
  export layer only *consumes* rights records at export time. The one shared-code change is additive:
  a new `policy.licensing.most_permissive_license`, and `effective_license` made stricter on an
  *unresolvable* upstream (no registered source sets `upstream_license`, so no existing behaviour
  changes).
- **PMTiles ships as a valid v3 archive carrying the ODbL layer as metadata; rendered vector tiles
  are deferred (a deliberate deviation).** Producing real MVT tiles is a tippecanoe-class build step
  and belongs with the map **surface** (Phase 15); the PMTiles *archive* is a database distribution
  (not a Produced Work), so it stays ODbL-1.0. The route/privacy class's *data* need is fully served
  by the real, complete **GeoJSON** of the ODbL layer that ships alongside; the PMTiles file is a
  spec-valid container whose tile bodies are filled when the tiler lands.
- **`derivative_permitted` is not added to the export gate.** SIG-LIC-004 gates on `redistributable`
  + `UNDETERMINED`; whether a non-derivative source may enter a derivative export is a policy question
  owned by P00.4's rights model, not something this ticket expands unilaterally on the shared gate the
  API also uses.
- **Reproducibility is keyed on the toolchain, not asserted across versions.** DuckDB stamps its version
  into Parquet metadata, so a DuckDB upgrade is a new build — which is the honest contract for a binary
  format, and why the byte-identical guarantee is stated per fixed toolchain.

## Revisit trigger

Revisit when the map surface (Phase 15) lands, to fill the PMTiles tile bodies with real rendered vector
tiles (and confirm the ODbL container licence still holds), and when the production `ReadStore` is wired
to Postgres, to confirm the export projections reproduce the API envelope via the same resolver path
(SIG-EXPORT-003) against real storage. Revisit if a new incompatible licence regime enters the corpus
(it must be a `licenses.toml` data row, never a schema/code change), if the real Zenodo HTTP transport is
wired (it must satisfy the same concept/version-DOI + digest-manifest contract the `FakeZenodoTransport`
encodes), or if `derivative_permitted` is decided to gate the export (which must change `policy.licensing`
centrally, with the API's collection-licence behaviour re-verified).
