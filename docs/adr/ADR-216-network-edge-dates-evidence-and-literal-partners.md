# ADR-216 — Honest network edges: dates, evidence, literal partners, degree (P35.30)

- Date: 2026-10-19
- Status: accepted
- Ticket: P35.30 (Round 11 / P35 sub-round 11B, manifest row
  `R11-K13-GX-02`, row 308 — K2 §7 H-1…H-4, K13 §7.1 W1; cites **A-10** (the
  operator's recorded answer, gate answer `b + c`), ADR-159, ADR-215,
  SIG-EXPORT-D21 (draft), SIG-INGEST-043c, SIG-TIME-012-class honesty,
  SIG-IDENT-030, SIG-UI-037/050)
- Base: `r11/P35.29-shared-labels-slugs-hashes`
- Related: ADR-215 (the shared `sig.entity-label/1` registry every node
  label now reads), ADR-101 (the materialized-graph seam the network
  surface refreshes from), ADR-092 (the compute-on-read fallback the same
  emitter now serves), ADR-124 (the shared eligibility selector edges
  honour), ADR-213 (the declared-independence classes `support` derives
  from), ADR-214 (the dated relationship rows `observed_at`/`valid_to`
  read), ADR-155/ADR-097 (the island architecture the richer JSON rides —
  unchanged).

## Context

Before this row the public `network.json` — on both the materialized and
the compute-on-read paths — emitted thin edges: `{from, to, access_kind,
relation, evidence_count: 1, evidence: [one claim]}` with `relation` set to
the raw predicate slot name on the compute-on-read path and
`support: "WEAKLY_SUPPORTED"` as a constant. K2 §7 names the defects the
surface had:

- **H-2** — an edge carried no date, no source and no named claim set, so
  the page could not say *when* a relationship was evidenced or *by whom*.
- **H-3** — ended or undated edges rendered indistinguishable from current
  ones; the page asserted present-tense relationships the evidence does
  not support (§3.1).
- **H-4** — `sharing_partner_degree` claims ("shared with N partners") are
  partner *counts*: emitted as edges they would draw a relationship to a
  number (SIG-INGEST-043c).
- **Literal partners** — source-stated partner names that never resolved
  to an entity (the materializer's `skipped_unmapped` class) were dropped
  silently; the page could not show what the sources actually said.
- **Labels** — pre-P35.29 leftovers let a raw entity/source id reach a
  node label; P35.30 completes the rewiring so every node label is the
  registry's.

## Decision

### One emitter for both paths

`_emit_network_edge` in `exports/spine_export.py` is the single edge
serializer; the materialized path and the compute-on-read fallback both
feed it, so the additive contract fields cannot drift between paths
(ADR-101/092 parity is structural, not a convention). Publishable
entity-ref claims with no materialized row still emit — the claim is
publishable; only the reconciled row is missing.

### Every edge carries its evidence, named

Each emitted edge carries, additively: `relation`/`predicate` in words
(the claim predicates unslugged — never a raw slot name), `direction`,
`observed_at` + `date_kind` (`"observed"`/`"undated"`), the valid-period
kind fields and `valid_to`, `source`/`sources` as **display names**
(never raw source ids), `currency`, `historical`, `support`,
`evidence_count`, and `evidence`/`claim_ids` — the full backing claim set,
not a count.

### Dates are honest classes, never epochs

`observed_at` normalizes to an ISO date; the pre-P35.26 epoch-zero
placeholder `1970-01-01` folds to `undated` (SIG-TIME-012-class honesty —
the spine-side repair is L3 CONF-06's, out of scope here). `date_kind`
makes the undated state first-class: an edge with no evidenced date is
*marked* undated, never shown a synthetic date.

### Support derives from declared independence — never a constant

`support` is computed over the backing claim set's `claim_lineage`
`independence_class` (ADR-213): two or more *distinct declared* classes →
`STRONGLY_SUPPORTED`; any evidenced claim → `WEAKLY_SUPPORTED`;
`unclassified`/undeclared lineage is never corroboration; `CONFIRMED` is
never emitted at this layer. The `claim_lineage` read is guarded
(`to_regclass`) — a pre-P35.25 spine degrades to the honest floor.

### Currency is snapshot-pinned, not wall-clock

`currency` derives via `reconcile.weight.currency` from each claim's
predicate half-life/volatility and the earliest evidenced observation date
against the **export's `as_of` snapshot date** — the emitted class is
reproducible from the release bytes. An undated edge carries the K2 §5.3
fifth class `UNDATED`; an unregistered predicate carries `null` — honest
absence, never a guessed class. The worst class across the edge's distinct
predicates wins (conservative roll-up).

### Historical marking is structural

`historical = (valid_to bound) or (currency == "HISTORICAL")`. The web
`edgeTemporal` helper classifies `current|historical|undated`; non-current
edges are excluded from the default "current" edge lists, visibly marked
(`[historical — ended <date>]` / `[undated]`), and drawn faded — in the
static page *and* the island identically (SIG-UI-037 parity — the list is
the source of truth).

### Literal partners join — person-screened first

A `partner_ref` that is not an entity id is a source-stated literal (the
K2 §2 literal twin). It emits a partner node labelled with the literal
text — but only after the Part VIII `natural_person_signal` screen runs
over the literal **before** any label, node or slug is derived (§3.4 R-8).
A person-shaped literal, or a literal the shared derivation cannot label,
withholds the whole edge — the raw text is never a node id and never a
label. Edges touching a registry-withheld entity drop whole.

### Degree is a node attribute

`sharing_partner_degree` claims never reach the edge set. They attach to
the subject node as `degree` + `degree_claim_ids`/`degree_observed_at`
(the count carries its own provenance, §3.1) and render as the "Recorded
partner counts" block — a fact about the entity, never a drawable
relationship. `analytics._typed_access_edges` shares the exclusion through
`shaping.SHARING_DEGREE_PREDICATES` so the centrality focus degree counts
exactly what `network.json` draws.

### The materialized read gains its temporal columns

`reconcile.materialize.read_materialized_edges` additionally selects
`observed_at` and `upper(valid_period)` (`valid_to`) — additive columns on
the read seam; live-row filtering (`upper_inf(sys_period)`) is unchanged.

## Consequences

- `network.json` is additive-superset: pre-P35.30 consumers parse
  unchanged; the `public_surface_contracts.schema.json` records the new
  optional fields and the `UNDATED` currency class.
- No new JavaScript: the richer rendering rides the existing island inside
  its ADR-097 ceiling; the no-JS list carries every emitted fact.
- A literal partner that survives the person screen is emitted
  source-stated (its `label_basis` says so); it is not claimed as a
  resolved entity — SIG-IDENT-030's abstention holds.
- The relationship row's single `evidence_claim` column is superseded in
  the *output* by the rejoined publishable claim set; the row itself is
  unchanged (append-only).

## Revisit trigger

Revisit when the L3 CONF-06 row repairs epoch-zero dates at the spine (the
export-side fold can then assert absence rather than repair), when the
relationship table persists the full claim set (the rejoin by
(from,to,kind) can be retired), or when a literal partner gains a
reconciled entity twin (the literal node merges into the entity node).
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->
