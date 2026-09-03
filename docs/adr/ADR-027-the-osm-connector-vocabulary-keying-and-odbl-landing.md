# ADR-027: The `osm` connector — versioned tag vocabulary, `(type,id,version)` keying, and ODbL landing

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P04.2
- **Requirement ids:** SIG-INGEST-045, SIG-INGEST-045a, SIG-INGEST-045b, SIG-INGEST-045c, SIG-INGEST-045d, SIG-INGEST-045e, SIG-INGEST-045f, SIG-INGEST-045g, SIG-INGEST-045h, SIG-INGEST-045i, SIG-INGEST-045j, SIG-ONTO-007, SIG-LIC-006
- **Spec:** docs/2_canonical_design_spec.md §23.2 (`osm` physical assets), §8.4 (custody postures), §42.3 (ODbL Strategy B), ADR-011

## Context

P04.2 is the first real connector on the P04.1 eight-stage framework (ADR-026):
`osm` ingests `man_made=surveillance` nodes, ways and relations from
OpenStreetMap. §23.2 imposes several source-specific requirements the framework
deliberately does not: a large, evolving surveillance-tag vocabulary; a reference
key that is unambiguous across time; `first_observed` derived from element
history rather than creation; deletion detection by snapshot diffing; a
mapper-identity safety discard; Overpass etiquette; and landing in the physically
separate ODbL asset layer (§42.3). Two facts shape the design. First, the
framework carries the generic machinery (gate, isolation, capture, replay,
disappearance, lineage, licence gate) — this ticket adds only the OSM-specific
stages and pure helpers. Second, the framework has no live-DB or live-HTTP wiring
yet (ADR-026: the OCFL `CaptureStore` adapter and a real transport are still
owed), so "the ODbL table" and "Overpass quota handling" must be realised at the
layers that exist today.

## Decision

1. **The SIG-INGEST-045 tag→claim vocabulary is versioned data, not code**
   (`connectors/src/connectors/data/osm_tag_vocab.toml`, read through
   `connectors._data.load_table`, mirroring the source registry). It carries a
   `version`, the allowlisted keys and their predicates, the `;`-multi-value
   split rule, the mapper-identity discard set, the `surveillance:type`→device-kind
   map, and the `camera:type`→mobility map. Changes after P04.2 are **versioned
   migrations** (§20) — bump `version`, never silently rewrite a mapping — so a
   re-extraction under a new vocabulary is a new interpretation, never a
   destructive overwrite (SIG-INGEST-017).

2. **A surveillance-bearing key or value outside the vocabulary is recorded as an
   unmapped value _plus_ a research task** (REQ-R1-02), never dropped; the raw
   value is always preserved (P2). This keeps the vocabulary honest — new device
   kinds surface as tasks, not silent data loss — and is why the canary asserts
   response *structure*, not tag values (a new value is not drift).

3. **Keys are `(osm_type, osm_id, version)`** (`ElementVersionRef`), and the claim
   subject is id-space-scoped `osm:{type}/{id}` (`ElementRef`). A bare id is not a
   reference across time (SIG-INGEST-045b) and node/way/relation id-spaces overlap
   (SIG-INGEST-045f); the version is preserved on every asset row so a later OSM
   edit is detectable (REQ-R1-01).

4. **`first_observed` is walked from element history** (`first_observed_from_history`
   — the earliest version whose tags carry the surveillance predicate), never the
   creation timestamp (SIG-INGEST-045a). In the snapshot path, where no history
   was fetched, `first_observed` is left **`None`** (unresolved) rather than
   falling back to any element timestamp — the fallback is exactly the systematic
   temporal corruption SC-17.3 warns about.

5. **Deletion is detected by snapshot diffing** (`snapshot_diff`), and a deletion
   from OSM is emitted as a **mapping event** (`osm_element_deleted`), kept
   strictly distinct from a street-removal world event
   (`physical_removed_from_street`, which the connector never emits from a diff) —
   SIG-INGEST-045g.

6. **Mapper identity is discarded at ingest** (`strip_mapper_identity` drops
   `user`/`uid`, keeps `changeset`) — SIG-INGEST-045e, a Part VIII safety
   invariant, enforced by a test asserting no output row ever carries `user`/`uid`.

7. **OSM output lands in the ODbL compartment at the connector layer.** Every
   emitted row is stamped `license=ODbL-1.0` / `compartment=osm_physical` /
   `source_id=osm_overpass`, and `physical_asset_rows()` projects the normalized
   claims onto the separate ODbL asset layer keyed by element (§42.3, ADR-011,
   SIG-LIC-006). Separation is *enforced* by the existing licence gate:
   `policy.licensing.compute_export_license` raises on any attempt to merge the
   OSM ODbL layer with the CC-BY-4.0 SIG graph (SIG-LIC-010), which a test drives.

8. **Overpass etiquette that the shared layer does not model lives in the
   connector as pure helpers** (`build_overpass_query` with no-space tag filters
   and `[timeout]/[maxsize]`; `overpass_status_action` mapping 429→back-off,
   504→shrink; `acquisition_mode` PBF-for-bulk vs tiled-Overpass-for-increments;
   `assert_own_or_public_instance`) — SIG-INGEST-045d/h/i/j. The descriptive,
   contact-carrying User-Agent is provided by the shared `PoliteFetcher`
   (SIG-INGEST-045d), so a browser spoof (which the public instance answers with
   HTTP 406) is structurally impossible.

## Consequences

The connector is small: it implements `discover/fetch/parse/extract/normalize`
plus `load`, and inherits the gate, isolation, capture, replay, shadow mode,
disappearance handling, and lineage from the framework. The vocabulary is
reviewable and evolvable as a data change. Two debts are explicit and deferred,
not hidden:

- **Live 429/504 handling is not yet wired through the shared fetcher.** The
  framework's `PoliteFetcher` classifies 429/403/401 as `ChallengeEncountered`
  (→ a disappearance datum). For Overpass, 429 means *slot exhaustion — back off
  in time* (SIG-INGEST-045h), not a bot challenge. The connector provides the
  correct semantics as pure helpers today; reconciling the shared layer (so a
  live 429 backs off and polls `/api/status` rather than recording a
  disappearance) is deferred to the live-transport ticket that also lands the
  OCFL `CaptureStore` adapter (ADR-026).

- **The ODbL "physically separate table" is realised at the connector layer**
  (compartment stamping + `physical_asset_rows` projection + the export gate),
  because connectors are not DB-wired yet. The DB `physical_asset` table
  (Appendix C.4) currently carries the OSM columns inline and is not itself split
  by compartment; making the stored table physically separate per §42.3 is a
  DB/ontology concern recorded in the risk register (RISK-P4-02), out of scope
  for a connector ticket.

## Alternatives considered

- **Vocabulary as Python literals** — rejected: it makes every mapping change a
  code change and defeats the §20 versioned-migration model; data-with-a-version
  matches the source registry and licence compartments (SIG-ENG-001).
- **Keying on `osm_id` alone** — rejected: SIG-INGEST-045b/045f — id-spaces
  overlap and a bare id is not a stable reference across time.
- **Deriving `first_observed` from the creation timestamp when history is absent**
  — rejected: SIG-INGEST-045a / SC-17.3; the fallback is the corruption. Leaving
  it unresolved (`None`) until a history walk is faithful.
- **Emitting a street-removal claim on an OSM deletion** — rejected:
  SIG-INGEST-045g — a mapper's cleanup is not a decommissioning.
- **Changing the shared `PoliteFetcher` to special-case Overpass 429/504 now** —
  rejected: that is framework surgery (out of scope for P04.2, which owns the
  connector, not the framework — ADR-026), and there is no live transport to
  exercise it against yet; recorded as a deferral instead.

## Revisit trigger

The live HTTP transport + OCFL `CaptureStore` adapter land and let 429/504 be
handled in the shared layer (retiring the connector-local helpers); or the DB
gains a physically separate ODbL asset table per §42.3 (superseding the
connector-layer compartment realisation); or OSM introduces a surveillance
tagging scheme change large enough that the vocabulary needs a structural
migration rather than an additive one.
