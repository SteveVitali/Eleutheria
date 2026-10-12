# ADR-208 — Programme-aggregate predicates, the multi-measure slice, and the PSA × month deviation (P36.7)

- Date: 2026-10-12
- Status: accepted
- Ticket: P36.7 (Round 11 / P36, row 280 — ACQ-11; the Wave-B batch
  `r11-procurement-01` procurement and programme registers)
- Base: `r11/P36.6-automated-traffic-enforcement-layers`
- Related: P35.9 (the portal `where` support and the P8-6 natural-person
  recipient screen this row consumes), P36.6 (the `arcgis_outstatistics` /
  `socrata_aggregate` transports and `enforcement_count`), P36.12 (the
  Wave-B activation — flips and live legs, deliberately not this ticket),
  SIG-INGEST-033 (the closed predicate allowlist), Part VIII S-lines
  (P8-4 programme-level-only, P8-6 natural-person payees), ADR-207 (the
  registered-predicate pattern this decision follows)

## Context

P36.7 registers three ACQ-11 surfaces. Two landed against the published
schemas exactly as designed (Cook County's awarded-contracts register as
bounded vendor/description `where` slices; Washington DES's contract-sales
register as vendor + exact contract-number slices behind a public-entity
customer allowlist). The third — DC OVSJG's private security-camera rebate
register — could not: the I8 §5.4 design table describes "ward × year
counts", but the committed catalog-sweep evidence for layer 33
(`a024d0ab1e76436796563750a95f6254`) enumerates **no `WARD` or `YEAR`
columns**. The published schema is `PSA, RECEIVED, UNDERREVIEW, APPROVED,
DECLINED, REBATEFUND, CAMERAFOUNDED, MONTH_YEAR, GIS_ID, CREATED, EDITED,
OBJECTID` — one row per Police Service Area × month carrying six per-status
count columns. Asserting ward/year columns would fabricate fields the
register does not publish (§3.1).

Two further gaps surfaced at emit time:

- `enforcement_count` is the wrong predicate for the rebate table: its
  registered definition is enforcement-outcome counts (warnings/
  violations), and a rebate programme's RECEIVED/APPROVED/DECLINED
  application statuses are programme outcomes, not enforcement events.
- The P36.6 aggregate transport reads exactly one published measure column
  (`aggregate_count_field`); the rebate table publishes six measures on one
  group row, and collapsing them to a single "count" would drop five
  published series — or worse, label them all with one name.

## Decision

1. **Two registered predicates** (registry predicates 283–284):

   - `programme_area` — the published programme-area aggregate subject
     assertion (the register's own row for one grouping column; `string`,
     `single`, `IMMUTABLE`/`infinite`/`authoritative_source_wins`;
     `camera_registry` D1, `connector_run` D3, all other genres D6). Its
     subject is the published area bucket — never a camera device, a
     geometry, a registrant, a name, or an address.
   - `programme_count` — the operator-published aggregate count of
     programme outcomes for a programme-area subject over a declared
     period (`integer`, `multi`, `object_kind: literal`,
     `VOLATILE`/6mo/`interval_union`; `camera_registry` D2, `connector_run`
     D3, all other genres D6). A claim carries `period`, `measure`, and —
     on a multi-measure slice — `series` naming the published measure
     column verbatim. Aggregate rows only: never a per-registrant, name,
     address, location, plate, or device record.

   Both join the `dot_511` connector's predicate allowlist — no other
   connector emits them, and no camera predicate (`traffic_camera`,
   `camera_external_ref`, `camera_jurisdiction`, `camera_operator`) may be
   stamped on a programme subject.

2. **`aggregate_subject_kind` on the aggregate spec** — closed vocabulary
   `camera_site` (default, the P36.6 shape unchanged) | `programme_area`.
   A `programme_area` subject mints `programme_area:<source>:<target>:<key>`
   entity rows under the `programme_area` record kind and emits
   `programme_count` claims — never a `traffic_camera` subject or an
   `enforcement_count` claim.

3. **`aggregate_count_fields` (plural) beside `aggregate_count_field`** —
   a multi-measure slice declares the reviewed list of published measure
   columns; the transports emit one statistic/`$select` term per column
   aliased `count_<field>` (single-measure keeps the canonical `count`
   alias), and each group row fans out into one `programme_count` claim
   per column with `series` set to the column name. A multi-measure slice
   may not combine with `verbatim` count function or a discriminator
   (one series dimension per claim); declaring both singular and plural
   forms is a registry error — all fail closed.

4. **The DC rebate target groups PSA × MONTH_YEAR** — the area × period
   surface the design intends, over the columns the layer actually
   publishes; the deviation from "ward × year" is recorded on the target
   row's `notes` and here. Layer 34 (the voucher programme) is a separate
   hub item (`dca42fbb30d14674a2eac69494928a74`) and is deliberately not a
   target.

5. **Procurement lane extensions** (all committed tenant/vocab data, all
   fail-closed):

   - `required_field` + `required_values` — a tenant's reviewed row-scope
     restriction folded server-side into every slice's `$where` AND
     enforced client-side at extract (the authoritative pass). WA DES
     admits only the reviewed public-entity `customer_type` values; a
     missing, empty or unlisted value counts `excluded` on the index row —
     never silently kept.
   - `exact_fields` on `[portal_where]` — per-term equality clauses
     (`upper(<field>) = '<TERM>'`) for identifier columns; WA DES's seven
     reviewed contract numbers (`05720`, `02315`, `06316`, `04220`,
     `06913`, `00318`, `02702`) surface reseller rows whose vendor name
     matches no vocabulary literal. The exact match IS the reviewed term
     evidence and needs no verbatim scan.
   - `composite_id_fields` — the published row key joined verbatim
     (WA DES: `contract_number|customer_name|vendor_name`) so a bare
     contract number never collapses distinct sales onto one subject; a
     partial key falls back to the row digest, never a half-key.
   - `rows_window = false` — a tenant whose reviewed surface IS the where
     filter expands no generic recency slice (an unfiltered window would
     emit unscoped register rows the plan never reviewed).
   - **P8-6 on portal sellers** — a vendor/payee carrying the identity
     layer's affirmative `natural_person_signal` emits no `seller` claim;
     the drop is recorded as `seller_dropped` on the notice row (the
     ambiguity refusals never drop — an ambiguous name keeps its text
     claim and merely mints no entity).

## Consequences

- **Additive only.** The single-measure `aggregate_count_field` path,
  `enforcement_count`, and every existing portal tenant expand and emit
  exactly as before; the new spec keys default off/absent. The NYC CROL
  tenant's expansion is unchanged (it still emits its rows window).
- **All three rows stay gated** (`ingestion_permitted=false`); the
  fixtures prove the emit shape, and the loader gate refuses any live
  fetch until the operator's OP-26 Wave-B flip under ING-GO-B (P36.12).
- **Programme-level by construction.** The rebate lane requests
  `returnGeometry=false`, selects no registrant/name/address column (none
  exist), and emits only `programme_area` × `programme_count` — a
  per-registrant or device row cannot be constructed from the surface.
- **Generated artifacts regenerate.** `ontology/generated` moves with the
  two new predicates (`make gen`); the ADR index row regenerates via
  `build-memory adr-index`.

## Alternatives considered

- **Emit the rebate rows under `enforcement_count`.** Rejected — the
  predicate's registered definition is enforcement outcomes; rebate
  application statuses are not enforcement events, and stamping them so
  would conflate a subsidy register with an enforcement programme (the
  same class of mistyping F-329/ADR-207 corrected on the camera side).
- **Reuse `agency_registry_entry` for the subject row.** Rejected — the
  subject is a programme-area aggregate group, not an agency registry
  entry; the mint shape (`subject_id`, `external_id`, `technology`,
  publisher) needed its own named record kind.
- **Synthesise ward/year columns** from PSA or MONTH_YEAR values.
  Rejected outright — fabrication (§3.1); the published PSA × MONTH_YEAR
  surface is asserted verbatim instead.
- **One collapsed `count` measure across the six status columns.**
  Rejected — it would drop five published series or mislabel them; the
  multi-measure fan-out keeps every published measure under its own
  `series` name.
- **Admit WA DES rows with missing `customer_type`.** Rejected — the
  reviewed surface is public-entity customers only; fail-closed exclusion
  with a recorded count is the honest outcome.
- **Keep the ACQ-01 generated source ids.** Rejected — the ticket
  contract names the I8 design ids (`procportal_cook_il_awards`,
  `procportal_wa_des_contract_sales`, `camreg_dc_ovsjg_camera_rebate`);
  the generated rows are replaced in place with the replacement recorded
  in `notes`.

## Revisit trigger

- Layer 33 republishes with `WARD`/`YEAR` columns (or the ward-level
  surface the design text described) — add a target row, never silently
  re-key the existing one's subjects.
- A second programme register needs a different subject granularity
  (e.g. programme-wide rather than area-grouped) — extend
  `aggregate_subject_kind`, never overload `programme_area`.
- A multi-measure slice needs a discriminator column — split the surfaces
  per the decision above, or extend the spec deliberately.
- `enforcement_count`'s assessment changes and the two count predicates
  need a shared rollup — reassess directness then, not before.
