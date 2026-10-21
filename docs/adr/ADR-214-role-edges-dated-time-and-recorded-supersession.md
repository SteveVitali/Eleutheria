# ADR-214 — Role edges, honest time, and recorded supersession (P35.26)

- Date: 2026-10-18
- Status: accepted
- Ticket: P35.26 (Round 11 / P35 sub-round 11B, manifest row `R11-L3-CP7`,
  ticket 305 — the L3-confidence-program's CP-7 + CONF-06; owned finding
  **F-521**; cites **SIG-TRUST-003**, **SIG-ONTO-028**, SIG-ONTO-029/030/032,
  SIG-EPIS-029, GQ-07/GQ-15)
- Base: `r11/P35.25-declared-lineage-namespaces-independence`
- Related: ADR-122 (the role taxonomy this decision materializes),
  ADR-112 (entity-ref surfaces provenance roles never mint), ADR-104 /
  ADR-R9-RESIGHT (claim-level observation-time bases — unchanged),
  ADR-213 (the declared-lineage rows the succession model consumes),
  ADR-146 (the materialization layer's append discipline).

## Context

The graph's who-does-what edges lied in two ways (F-521):

1. **Publisher read as operator.** The EFF Data Driven release and the
   OSM element set *publish* lists of cameras; nothing in either source
   evidences that the publisher *operates* a camera. The emitters and the
   schema gave the publisher label an operational path, so a dataset's
   publisher could materialize as the operator of the things it lists —
   the SIG-TRUST-003 conflation.
2. **Time was fabricated.** The sharing-edge materializer's undated
   fallback wrote `1970-01-01` as an edge's lower bound and observation
   time — every undated edge read as epoch-asserted (the GQ-15 defect
   class), and there was no vocabulary for "no evidenced date".

The `entity_role` table existed only as the spec-§C.5 sketch: a composite
natural primary key `(entity_id, actor_id, role, valid_period)`, `actor_id`
NOT NULL, no temporal-kind vocabulary, no succession link, no writer and
no reader — zero rows in every deployed environment.

## Decision

### `entity_role` reshaped into the real role-edge table

Sqitch `role_edges` reshapes the never-written sketch (safe because no
deployed row exists):

- **Surrogate `entity_role_id` primary key.** The composite natural key
  cannot hold the explicit-unknown marker — `operator_unknown` is a
  first-class row whose `actor_id` is NULL by construction, and a primary
  key column cannot be NULL. Natural uniqueness moves to `input_digest`
  (partial unique index — the `relationship`/`entity_type_decision`
  posture).
- **Temporal columns mirroring `relationship`/`claim`:** `valid_period`,
  `valid_from_kind`/`valid_to_kind`, `observed_at`, `asserted_by`,
  `sys_period` (belief time).
- **Succession columns:** `supersedes` (self-FK) +
  `superseded_by_claim` (FK to `claim`) — the recorded edge succession
  of SIG-EPIS-029.
- **Closed role CHECK** — `db.organization_roles.EDGE_ROLE_VOCABULARY`
  is the list of truth: the fourteen `OrganizationRole` enum members ∪
  the fourteen §12.4 names the spec spells differently (`purchaser`,
  `platform_provider`, `installer`, `data_controller`, `data_processor`,
  `accessor_read`, `searcher`, `alert_recipient`) ∪ `maintainer` ∪ the
  `operator_unknown` marker. `actor_id` NULL only for `operator_unknown`.

### `undated` is a first-class bound kind; epoch-zero is rejected at write

The edge bound-kind vocabulary gains `undated` — the explicit marker for
"the evidence carries no date". An undated claim materializes an
UNBOUNDED `valid_period` with `valid_from_kind='undated'` and NULL
`observed_at`. `NOT VALID` CHECKs on `entity_role` and `relationship`
reject a `1970-01-01` lower bound or `observed_at` at write — binding
new writes immediately while pre-existing hosted rows (if any) wait the
named VALIDATE follow-up (the `entity_typing_mobility_check` posture).
`undated` is an *edge-level* kind: claims keep their existing `unknown`
bound-kind vocabulary — the marker records the materializer's judgement
about the assembled edge, not a new claim shape.

### Provenance roles can never edge

`ROLE_OF_PREDICATE` gains `published_by`/`listed_by`/
`published_by_source` (→ `PUBLISHER`) and `maintainer`/`maintained_by`
(→ `MAINTAINER`). Only predicates whose role is in `ENTITY_REF_ROLES`
produce edges; provenance-role claims (`camera_registry_publisher`,
`published_by`, …) are literal provenance and never mint a role edge —
enforced in `_read_role_claims`, not by trusting claim shape: even a
misshapen provenance claim carrying an `object_entity` cannot edge.

### The explicit-unknown operator state (SIG-ONTO-028)

`operator_absent` claims materialize `operator_unknown` rows — actor
NULL, evidenced by the absence claim. The marker claims the *operator
slot* (`role_slot` maps `operator` and `operator_unknown` to the same
slot), so the slot always carries exactly one current reading per
lineage: a later operator claim supersedes the marker; a later absence
claim supersedes an operator edge. `operator_state()` distinguishes
`operator` / `operator_unknown` / `not_asserted` — evidenced-absence is
never the same reading as never-asked.

### Recorded supersession, three succession kinds

A role edge's succession is derivable and recorded, never an in-place
edit:

- **Within-lineage state change** (`claim_lineage.source_id`, ADR-213 —
  a claim with no lineage row is its own lineage): a later *distinct*
  state in the same lineage closes the earlier episode's valid upper
  bound at the later claim's evidenced date and names it in
  `superseded_by_claim`; the succeeding edge links via `supersedes`.
- **Explicit correction:** a claim's `revises_claim`/`retraction_of`
  closes the episode its target evidenced — cross-lineage, at the
  corrector's date. A "correction" older than its target corrects
  nothing.
- **Belief supersession:** a live row whose logical edge
  `(entity, actor, role, superseded_by_claim)` is re-derived with a
  different `input_digest` (a changed evidence set or temporal input)
  is sys_period-closed and the new version links it; a live row the
  desired set no longer produces is closed stale.

Cross-lineage *concurrent* disagreement stays concurrent — both edges
live, never silently reconciled (§3.1). Open same-state episodes merge
across lineages into one corroborated edge; closed episodes stay
per-lineage rows.

The one sanctioned mutation is the `sys_period` close, performed by the
SECURITY DEFINER `close_superseded_entity_roles` /
`close_superseded_relationships` (the `close_superseded_resolutions`
pattern): callers keep an INSERT-only posture on the edge tables and
`sig_materialize` holds only EXECUTE on the closures plus SELECT+INSERT
on `entity_role`. `relationship` gains `supersedes` and the same
supersession path.

### `vocab_published_by`

A separate INSERT-only change registers `published_by` in
`vocab_predicate` + its `directness_matrix` row (GLACIAL 10y,
max_support) — the closed sink resolves the first publisher claim from
the queued EFF/OSM re-ingest legs instead of quarantining it.

## Consequences

- `entity_role` is off the §37 public read surface (same posture as
  `relationship`): `sig_materialize` reads+writes; no public grant.
- The resolver's `observation_time()` sentinel (ADR-104's undated ⇒
  historical ordering rule) is unchanged — it is an ordering input to
  `latest_observation_wins`, never a stored edge bound; edge bounds are
  now structurally incapable of carrying it.
- The GQ-15 epoch-start detector remains as the guard for pre-existing
  hosted rows while the NOT VALID constraints await validation; new
  writes cannot create one.
- `sig-reconcile materialize-role-edges` defaults to dry-run; `--apply`
  writes. The hosted rematerialize + EFF/OSM re-ingest are queued live
  legs under the OM-20 conditional (GATE-G4 §4, 2026-10-09T17:32Z).

## Revisit trigger

Revisit when a subject needs *several* concurrent operational actors
modelled as one slot state (the slot model serializes per lineage and
merges open states across lineages — adequate while each state is one
actor or the unknown marker), when a second absence predicate beyond
`operator_absent` is registered (extend `ABSENCE_PREDICATES` +
`UNKNOWN_STATE_FOR_ROLE` and the CHECK in one change), or when the
NOT VALID constraints are validated on hosted (a named follow-up change,
not an edit here).
