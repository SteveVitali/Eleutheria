# ADR-115 — Peer-class negative space: declared `(entity_type, connector)` classes with declared tracked predicates (the design's ADR-R9-PEERCLASS)

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.9 (`docs/tickets/P31.9__negative-space-peer-classes.md`) — Round 9 `DEEPEN.5`. Closes deferral **D-P30.2-1**.
- **Date:** 2026-09-25
- **Related:** §32.1 (negative space), SIG-METRIC-002/008/009/010, ADR-005 (append-only), ADR-099
  (materialization posture), ADR-103 (P30.2 hosted materialization — ran coverage with
  `--no-negative-space` and opened the deferral this ADR closes), ADR-107 (`sig-pg` at
  `db-custom-1-3840`, **15 GB PD-SSD** — the disk the projection is measured against),
  SIG-ENG-001/003 (the declaration is versioned data; rule changes are ADRs).

## Context

- **The P28.4 rule was one class: `entity_type`.** `read_negative_space` unioned every
  predicate on the spine into each entity type's tracked set. On the hosted spine every
  claim subject is typed `deployment` (248,506 subjects), so the rule compared every
  traffic camera with every bill — a measured **26,696,184** would-be `not_researched`
  rows (~12× the spine), each individually meaningless (`bill_title` on a DOT camera).
  P30.2 therefore ran hosted coverage with `--no-negative-space` and opened **D-P30.2-1**.
- **The gap is real but the shape was wrong.** §32.1 requires the negative space to be
  *proportionate*: a subject is compared with peers of its class, not the global
  predicate union. The rule needed a peer class that is (a) derivable from spine data and
  (b) meaningful — the acquisition channel determines which attributes a subject can
  even have.
- **Not all of a connector's emit surface is a research gap.** Per-claim bookkeeping
  predicates (`matched_keyword`, `content_term`, `bill_matched_keyword`,
  `unmapped_surveillance_tag`) record extraction/match outcomes; their absence is not
  "not researched". Declaring them tracked would re-inflate the negative space with
  non-gaps.

## Decision

1. **The peer class is `(entity_type, ingest_run.connector_name)`.** A claim subject
   belongs to a class when its `entity.entity_type` matches the class's `entity_type`
   AND at least one of its tier-0, currently-valid claims was written by an ingest run
   whose `connector_name` the class declares (`claim.ingest_run_id →
   ingest_run.connector_name` — the lineage is already on every claim; no schema
   change). Membership may be multi-class; a member's tracked set is the UNION of the
   tracked predicates of every class it belongs to.
2. **The policy is data, not code.** `inference/src/inference/data/peer_classes.toml`
   declares, per class, the connector set and the `tracked` predicate set — seeded from
   the measured per-connector emit surface of the hosted spine (2026-09-25) MINUS the
   bookkeeping predicates above. The file is versioned (§20) and validated at load
   (`inference/peer_classes.py`: fail-loud on a malformed declaration, on a connector
   claimed by two classes of one entity type, on an empty tracked set). A predicate
   absent from a class's `tracked` is **never** negative space for that class; a
   subject whose claims come only from undeclared connectors has no declared coverage
   surface and yields no rows — an honest "not declared", never a guess.
3. **The absence vocabulary is unchanged.** Emitted rows are `not_researched` /
   `searched_by='auto'` / `search_method='inference.materialize (peer-class negative
   space)'` — the same closed `CoverageRecord` vocabulary and `input_digest` idempotency
   as before; `--no-negative-space` remains an explicit opt-out flag but is no longer
   passed by `ops/gcp/materialize.sh`.
4. **Measured before written.** Read-only measurement over the hosted spine (role
   `sig_read_public`, READ ONLY txn) reports **1,035,351** would-be `not_researched`
   rows — 25.8× smaller than the unscoped rule — committed at
   `docs/build/reports/p31.9-hosted/negative_space_would_be.json` with the per-class
   breakdown (dot_511 907,291; procurement 118,076; osm 6,548; 9 smaller classes) and a
   ≤ ~0.27 GB byte projection against the live-read 15 GB disk (~1.8 %).
5. **No metric changes.** Named-denominator counted quantities (§32.2/32.3/32.5) are
   untouched; negative-space rows carry no denominator by construction (they are
   absences, not metrics — SIG-METRIC-008 unchanged).

## Consequences

- Hosted coverage now materializes the honest negative space (~1.04M rows) — D-P30.2-1
  closes. Re-runs are +0 by `input_digest`.
- Extending coverage for a connector = a data change to `peer_classes.toml` (bump
  `version`); a new connector with no declaration produces no negative space — the
  measurement/declaration step is explicit, never accidental.
- `read_negative_space` is injectable (`peer_classes=` parameter) so tests pin the rule
  against fixture classes without touching the shipped declaration.

## Alternatives

- **Entity type alone (status quo):** measured meaningless on this spine — rejected.
- **Per-connector tracked sets inferred from "predicates this connector has ever
  claimed", computed at run time:** rejected — it silently follows emit-surface drift
  (a connector that stops emitting a predicate instantly stops reporting the gap) and
  mixes bookkeeping noise into "research". Declaration keeps the policy reviewed data.
- **A schema column (`subject.peer_class`):** rejected — redundant with the
  claim→run→connector lineage already stored; additive data file chosen instead.
- **Waiting for richer entity typing (P31.5/P28.6 organization subjects):** the key is
  already `(entity_type, connector)` so typed subjects partition naturally when they
  arrive; declaring for `deployment` only is honest now.

## Revisit trigger

- A connector ships with no declared class and its absence surface is wanted (the
  declaration must be extended — the load-time validator + the
  `measured ⇐ declared` test make the drift loud).
- Claim subjects gain non-`deployment` types at scale; re-measure per-class membership.
- A class's measured would-be rows grow past ~10 % of the spine, or total negative
  space projected bytes exceed ~50 % of the provisioned disk — re-scope the
  declaration or reconsider materializing absence at all.
- If `searched_not_found` (with `sources_searched`) is ever wanted from automated
  research passes, that is a new absence producer — a separate ADR.
