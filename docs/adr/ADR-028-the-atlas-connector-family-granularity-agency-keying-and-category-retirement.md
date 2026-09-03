# ADR-028: The `atlas` connector — family-level `deployment_exists`, agency-id keying, and category-retirement-as-not-a-world-change

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P04.3
- **Requirement ids:** SIG-ONTO-059, SIG-INGEST-033, SIG-INGEST-034, SIG-STORE-039, SIG-STORE-040, SIG-ONTO-058, SIG-PARSE-007, SIG-PARSE-008, SIG-INGEST-021, §23.3
- **Spec:** docs/2_canonical_design_spec.md §23.3 (`atlas` agency adoption), §13.1 (technology domain→family→technology), §20.3 (crosswalks), §42.2 (export compartments), ADR-026 (the framework), ADR-027 (the `osm` connector)

## Context

P04.3 is the second real connector on the P04.1 eight-stage framework (ADR-026),
and is deliberately of a **different shape** from `osm` (ADR-027): where `osm`
lands device-level physical assets in a separate ODbL layer, `atlas` lands
**agency-level adoption** claims in the CC-BY-4.0 SIG graph. §23.3 imposes several
source-specific requirements the framework does not: a single write predicate
(`deployment_exists`) at **family-level** technology granularity; keying on the
Atlas agency identifier with a surrogate-identity fallback; a nine-genre
methodology model that must be preserved rather than flattened; and — the ticket's
headline rule — recording a **retired Atlas category as a retirement, not a world
change** (SIG-ONTO-059). As in P04.2, the framework carries the generic machinery
(gate, isolation, capture, replay, shadow, disappearance, lineage, licence gate);
this ticket adds only the Atlas-specific stages and pure helpers, and — because
connectors are not DB-wired yet (ADR-026) — realises "the deployment layer" at the
layers that exist today.

## Decision

1. **The Atlas category → SIG technology mapping is versioned data, not code**
   (`connectors/src/connectors/data/atlas_vocab.toml`, read through
   `connectors._data.load_table`, mirroring the source registry and the osm
   vocabulary). It carries a connector `vocab_version`, the observed **Atlas
   taxonomy version** (`atlas_version`, stamped on every row), the category map,
   the nine evidence genres, the retired-category ledger, and the predicate
   allowlist. Changes after P04.3 are **versioned migrations** (§20) — bump the
   version, never silently rewrite a mapping (SIG-INGEST-017).

2. **Categories map to SIG technology FAMILIES, seeded from the authoritative
   crosswalk.** Each row is seeded from the `eff_atlas` taxonomy in
   `ontology/vocab/crosswalks.yaml` (SIG-STORE-039/040) and rolled to its family
   level (§13.1); the SKOS mapping relation and `lossy` flag ride on every emitted
   claim so a query traversing a lossy crosswalk propagates it (SIG-ONTO-058). A
   category **outside** the vocabulary is recorded as an unmapped category + a
   research task — never mapped to a guessed family.

3. **The connector writes exactly one claim predicate, enforced by a hard
   allowlist gate** (`assert_predicate_allowed`, SIG-INGEST-033):
   `deployment_exists`. Device counts, coordinates, configuration and current
   status are refused at the ingestion boundary — the `D6` admissibility filter
   enforced at ingest rather than only at resolution. The out-of-scope write-set is
   named as data (`forbidden_predicate_genres`), disjoint from the allowlist.

4. **Agency-id keying emits a _candidate_ identifier and never resolves**
   (SIG-INGEST-034). An ORI-shaped agency value (validated by
   `resolution.ori.is_valid_ori` — pattern, never position) routes to the canonical
   `us.fbi.ori` scheme; every other value — the common case, since the Atlas keys
   on agency names — routes to the `atlas.agency_name` **surrogate path** that
   feeds P03.2's crosswalk. `link()` is the framework identity default: the
   connector emits candidates, the identity layer resolves them.

5. **The nine methodology components are preserved or their loss recorded**
   (§23.3, OL-2D-AT-02). Where the feed records the producing component the
   connector normalises it onto one of the nine genres and carries it; where the
   feed records no component, records a blank, or records an unrecognised label,
   the connector marks `evidence_genre_granularity_loss=true` and assigns **no
   tier by guess** (keeping the raw label for provenance when one was present).

6. **A retired Atlas category is a vocabulary event, not a world change**
   (SIG-ONTO-059). A row tagged with a retired category (the March-2024
   Ring/Neighbors retirement) is recorded under `atlas_category_retired` with
   `event_class='vocabulary_event'` and the Atlas version at which it retired —
   **never** a `deployment_exists` claim and **never** the world event
   `deployment_ended` (which the connector never emits from a retirement). The
   retirement is keyed on the vocabulary version, not wall-clock time, so emitting
   it inside the pure `normalize` stage keeps the stage idempotent
   (SIG-INGEST-003).

7. **Atlas-derived claims land in the CC-BY-4.0 SIG graph compartment at the
   connector layer.** Every emitted row is stamped `license=CC-BY-4.0` /
   `compartment=sig_graph` / `source_id=eff_atlas_of_surveillance` and carries the
   Atlas's required source attribution (from the source's rights record) plus the
   row's own upstream links; placement is governed by the existing export gate
   (SIG-LIC-010).

## Consequences

The connector is small: it implements `discover/fetch/parse/extract/normalize`
plus `load`, and inherits the gate, isolation, capture, replay, shadow mode,
disappearance handling, and lineage from the framework. Rows are append-only and
carry the provenance a resolver needs to supersede or temporally qualify an Atlas
row later (source attribution, Atlas version, candidate identifier, links); the
connector marks nothing "current" or authoritative. Two debts are explicit and
deferred, not hidden:

- **Resolver-side supersession/reconciliation is out of scope (P08.x).** The
  connector preserves the provenance and append-only shape that make supersession
  possible; it does not itself decide when a later claim supersedes an Atlas row.

- **The category map is seeded from the crosswalk, not exhaustive.** The real
  Atlas taxonomy has more categories than the five crosswalk-seeded families here;
  the remainder are handled faithfully as unmapped categories + research tasks and
  are added by §20 versioned migration as they are reviewed, exactly as the osm
  vocabulary grows.

## Alternatives considered

- **Writing at technology (not family) granularity** — rejected: §23.3 mandates
  family-level; the crosswalk to the finer concept is `broadMatch`/`relatedMatch`
  and `lossy`, so writing the fine concept would fabricate precision
  (SIG-STORE-040).
- **Resolving the agency to an entity in the connector** — rejected:
  SIG-INGEST-034 — the connector emits candidate identifiers only.
- **Guessing an evidence tier when the component is absent** — rejected: §23.3 —
  the granularity loss must be recorded, not papered over with a synthetic tier
  (the defining standard's "no synthetic certainty").
- **Treating a retired category as a deployment ending / disappearance** —
  rejected: SIG-ONTO-059 — a vocabulary change carries negative semantics; the
  absence of a Ring data point after March 2024 is a category retirement, not a
  program ending.
- **Mapping vocabulary as Python literals** — rejected for the same reasons as
  ADR-027: it defeats the §20 versioned-migration model (SIG-ENG-001).

## Revisit trigger

The live HTTP transport + OCFL `CaptureStore` adapter land (letting `atlas` fetch
and archive real bulk exports); or the resolver's supersession/reconciliation
logic (P08.x) lands and needs a firmer contract from the connector than "append
only with full provenance"; or the EFF Atlas changes its taxonomy again (a new
retirement or a category split) such that the versioned category map needs a
structural rather than additive migration; or the connector layer gains a real
`deployment_exists` DB write path superseding the compartment-stamp realisation.
