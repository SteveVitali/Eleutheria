# ADR-207 — The ATE technology family and the declared geometry kind (P36.3)

- Date: 2026-10-11
- Status: accepted
- Ticket: P36.3 (Round 11 / P36, row 276 — ACQ-03; the Round-11 wave-B
  acquisition plan's automated-traffic-enforcement prerequisite)
- Base: `r11/P35.15b-technology-backfill`
- Related: SIG-ONTO-019/020/022/052/052a/056 (the technology-hierarchy rules
  the family lands under), SIG-GEO-003 (the asset model MUST NOT assume point
  geometry), P35.14a (the closed claim-sink vocabulary the new predicate and
  enum member are registered through), P36.4 (emits
  `geometry_kind="area"` for programme-area rows), P36.6 (the ATE layers —
  ACQ-10's 15 rows), P36.12 (hosted `enforcement_count` registration —
  deliberately not this ticket)

## Context

The Round-11 wave-B acquisition plan carries 15 automated-traffic-enforcement
targets (ACQ-10) with rights and access evidence already in hand, but the
technology vocabulary had no concept for them. The two candidate homes were
both wrong:

- `traffic_camera` was retired by P35.14a — a blanket deprecated type that
  conflated traffic-monitoring cameras with enforcement programmes. Emitting
  ATE records under it would resurrect the conflation the retirement
  corrected and would violate the emit-side rule that retired terms are
  never stamped.
- The `alpr` family is wrong too: a red-light camera is not an ALPR
  deployment — it photographs violators on a signal state, reads the plate
  only for the citation path, and the programme is typically a separate
  vendor contract and ordinance from the agency's plate-reader network.

ATE therefore needs its own family under `surveillance-vehicle`, and the
five enforcement distinctions the evidence discriminates need leaves.

Independently, P36.4's official camera layers found that several publishers
publish their cameras as **programme areas or zones, not device points** —
and P36.6's ATE rows are zone-shaped by nature. SIG-GEO-003 already forbids
assuming point geometry, but nothing in the vocabulary let a record *declare*
its geometry shape, so the closed claim sink (P35.14a) would quarantine a
`geometry_kind="area"` emit as an unregistered predicate id.

## Decision

1. **`ate` family under `surveillance-vehicle`** — label "Automated traffic
   enforcement" — with six active leaves, each carrying the SIG-ONTO-056
   triple (distinguishing criterion, evidence signature, salience) and a
   family-prefixed, non-vendor, lowercase-hyphenated slug (SIG-ONTO-022):

   - `ate-red-light` — citation triggered by entering/crossing against a red
     signal.
   - `ate-speed` — citation triggered by measured speed over the limit
     (fixed-site or average-speed).
   - `ate-bus-lane` — citation for unauthorised use of a bus/transit-only lane.
   - `ate-school-bus-stop-arm` — citation for passing a school bus with its
     stop arm deployed.
   - `ate-work-zone` — automated speed enforcement inside a work/construction
     zone.
   - `ate-unspecified` — the SIG-ONTO-020 coarse leaf for evidence that names
     the family but not the discriminator ("automated enforcement",
     "photo enforcement", "traffic safety camera").

   Canonical counts move to **14 domains / 37 families / 110 active
   technologies** (SIG-ONTO-052 amended in `spec_src`, manifest recorded).

2. **`GeometryKind` enum in `common.yaml`** — `point` (a device point),
   `line` (an enforced route/corridor segment), `area` (a zone or programme
   area). Slot-value enum alongside `GeometryPrecision`, not a §13.3/4/5
   SKOS scheme.

3. **`geometry_kind` predicate in `predicates.yaml`** (registry predicate
   281) — `string` datatype, `single` cardinality, `object_kind: literal`
   default, `SLOW`/2y/`authoritative_source_wins`; directness assessed
   `camera_registry` D1 (the record's own published shape is the registry's
   own fact), `connector_run` D3, all other genres D6 — so P36.4's
   `geometry_kind="area"` emit and P36.6's zone rows pass the closed sink.

## Consequences

- **Additive only.** No existing term, slug, predicate, or count changes;
  retired leaves stay resolvable under their `retired/` IRIs. The generated
  artifacts (`make gen`) and the canonical spec (`spec_src` + `BUILD.sh`)
  move together — the count change has exactly one authored home
  (`ontology/vocab/technology.yaml`) and every derived surface asserts it
  (SIG-ONTO-052a).
- **ACQ-10 unblocked.** P36.6 can type ATE records with the five subtype
  slugs, never `traffic_camera`; zone-shaped rows declare
  `geometry_kind="area"` alongside a `technology` claim.
- **P36.4 unblocked.** Programme-area rows declare `geometry_kind="area"`
  through the registered predicate; an area-shaped record is never flattened
  to a device point (SIG-GEO-003).
- **`enforcement_count` stays deferred.** The aggregate predicate is P36.6's
  ontology edit and P36.12's hosted registration — deliberately absent here.
- **`derived_geometry.geometry_kind` (Appendix C DDL) is a different,
  internal column** for derivation kinds (`fov_cone`, `coverage_estimate`,
  `road_snap`) — not a claim predicate and not this vocabulary. The
  predicate id `geometry_kind` is the ticket's contracted emit name; the two
  namespaces (claim predicates vs. inference-table columns) do not collide.

## Alternatives considered

- **Reuse `traffic_camera`.** Rejected — retired by P35.14a precisely
  because it conflated monitoring and enforcement; stamping it on ATE
  records would re-create the defect and violate the retired-term emit ban.
- **Fold ATE into `alpr` as `alpr-*` leaves.** Rejected — the enforcement
  programmes are evidence-discriminated differently (signal/speed/stop-arm
  triggers, separate statutes and vendor contracts); the discriminator test
  (SIG-ONTO-022) fails.
- **A separate `surveillance-enforcement` domain.** Rejected — enforcement
  is a vehicle-surveillance programme family; a domain per enforcement
  statute would explode the 14-domain axis for no rollup benefit.
- **Name the predicate `record_geometry_kind`.** Rejected — the ticket
  contract and P36.4's emit fix `geometry_kind`; the Appendix-C column
  lives in a different namespace.
- **`zone` instead of `area` as the enum member.** Rejected — P36.4's
  contracted emit is `geometry_kind="area"`, and `area` also covers
  non-zone programme polygons (SIG-GEO-004's operating-area case).

## Revisit trigger

- A landed ATE layer needs an enforcement mode outside the five leaves
  (e.g. automated weigh-station or toll-violation enforcement) — add a leaf,
  never repurpose `ate-unspecified`.
- A registry publishes a declared shape outside `point`/`line`/`area`
  (e.g. a volume or a named-jurisdiction reference) — extend `GeometryKind`.
- `enforcement_count` lands (P36.6/P36.12) and its assessment changes the
  `geometry_kind` directness row — reassess then, not before.
