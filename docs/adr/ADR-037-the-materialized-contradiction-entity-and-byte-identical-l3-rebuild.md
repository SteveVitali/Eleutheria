# ADR-037: The materialized Contradiction entity, its lifecycle, and the byte-identical L3 rebuild

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P08.3
- **Requirement ids:** SIG-RECON-053, SIG-RECON-054, SIG-RECON-055, SIG-RECON-056, SIG-RECON-057, SIG-RECON-019, SIG-RECON-020, SIG-RECON-021
- **Spec:** docs/2_canonical_design_spec.md §31 (contradiction as a first-class object), §28.7 (recomputation, versioning, immutability); §28.2 (the emit phase), §16.4 (`contradiction_state`)

## Context

P08.3 makes `Contradiction` a first-class materialized entity with a lifecycle
(§31): an open contradiction publishes as `unresolved_conflict`; a `blocking` one
forces `UNRESOLVED` (`U7`); resolution sets status without deleting; and a full L3
rebuild is byte-identical from `(claims + ruleset_version + resolver_version +
as_of pair)`, verified by the stored `input_digest` (§28.7). Three structural
questions had to be settled, given the P08.1/P08.2 precedent (ADR-031/036) that
the `reconcile` package ships thin, pure-Python value-object modules that do **not**
persist to Postgres, and RISK-P8-09 which explicitly assigns this entity + lifecycle
to P08.3.

1. **One contradiction type, or two?** The resolver (Phase 2.2/2.3) and every §29
   workflow already emit `reconcile.model.Contradiction`. §31 requires a richer
   entity (identity, `claim_ids[]`, `severity`, a five-state lifecycle, resolution
   fields, `research_task_ids[]`).

2. **Where does the entity live — Postgres, or a Python entity aligned with the
   DDL?** The `contradiction` table already exists (`db/deploy/graph_annotations.sql`).

3. **What does "byte-identical L3 rebuild" verify against, and how does CI gate it?**

## Decision

1. **Promote the existing `reconcile.model.Contradiction`** into the materialized
   entity rather than introducing a second type. Added, all optional with
   today's-behavior defaults (additive/back-compat): `contradiction_id` (identity,
   §3.1), `claim_ids[]`, and the resolution fields `resolution_note`/`resolved_by`/
   `resolved_at`. `severity`/`status` already existed. The append-only lifecycle
   lives as **transition methods on the frozen dataclass** (`begin_research`,
   `resolve`, `accept_unresolvable`, `supersede`) that each return a *new* record —
   a contradiction is never edited in place and resolving it never deletes it
   (SIG-RECON-021/055). Status is validated against the five §31 states, with
   `accepted_unresolvable` a legitimate terminal state (SIG-RECON-056). Orchestration
   around the entity (materialization with a content-derived identity, the U7 brake,
   the publish projection, the detector→task conformance check) lives in a new
   `reconcile.contradiction` module.

2. **Model the entity in pure Python, aligned with `graph_annotations.contradiction`;
   do not add Postgres persistence here.** This continues the ADR-031/036 precedent
   (the whole `reconcile` layer models stored shapes without a live database) and
   keeps a single owner of the lifecycle semantics. Persisting the entity onto the
   existing table is a downstream wiring step (the read API is P14.1); the field set
   and lifecycle this ticket fixes are the contract that wiring implements.

3. **Verify the byte-identical rebuild in-process against the resolver.** `RESOLVE()`
   is already deterministic — its `decision_key()` excludes wall-clock `computed_at`,
   and its `input_digest` is `hash(ruleset_version + sorted claim ids + content
   hashes)` (SIG-RECON-020). `reconcile.rebuild.verify_reproducible` reruns the
   resolver over the same inputs and asserts the fresh `input_digest` **and** full
   decision key match; a version mismatch is refused as `NonReproducible` (a
   superseding recompute, not a reproduction). A committed sample
   (`reconcile/src/reconcile/data/l3_rebuild_sample.json`) plus a CI test
   (`tests/reconcile/test_rebuild.py`) regenerate and assert the match
   (SIG-RECON-020 / SIG-STORE-018).

4. **Enforce the detector→task contract uniformly (SIG-RECON-057).** Every emitted
   contradiction must link a research task with a non-empty closing condition. To
   make the *whole* system conformant — not just the §29 workflows — the resolver's
   Phase-2 guards (`value_domain_mismatch`, `predicate_conflation`) now emit a
   research task too, with a **deterministic, content-derived** task id so the
   resolution record stays byte-identical on rebuild. `reconcile.contradiction.
   detector_task_violations` is the mechanical check `tests/reconcile/
   test_detector_task_contract.py` runs over every detector's output.

## Consequences

`Contradiction` is now a single, first-class, addressable entity used identically by
the resolver and every §29 workflow: it has stable identity, carries the disagreeing
claims, publishes open conflicts (never hides them), forces `UNRESOLVED` when a
curator marks it `blocking`, and preserves history when resolved. The reproducibility
contract is mechanically gated: any change to the ruleset, the resolver, or a
sample's claims that alters an `input_digest` fails CI until the sample is
regenerated deliberately. Because the resolver now emits deterministic research tasks
for its Phase-2 contradictions, `Resolution` gained an additive `tasks` field and
`CountResolution` likewise — no existing wire name, id, or default changed.

## Alternatives considered

- **A separate `MaterializedContradiction` type** (rejected: two types modelling one
  concept, plus a mapping layer, for no benefit; the existing type already carried
  `severity`/`status` and every call-site uses keyword args, so promotion is
  back-compat).
- **Persisting to the `contradiction` table now** (rejected: it would fork the
  reconcile layer's pure-Python precedent and pre-empt the P14.1 read-API surface;
  the lifecycle semantics, not the storage plumbing, are what §31 pins).
- **Leaving the resolver's Phase-2 contradictions taskless and scoping the
  detector→task contract to the §29 workflows** (rejected: SIG-RECON-057 says
  *every* detector; a uniform contract is stronger and only cost a deterministic
  task id).
- **Random task ids for the resolver's contradictions** (rejected: they would make
  the resolution record non-reproducible, violating SIG-RECON-020).

## Revisit trigger

Revisit when P14.1 lands the public read API (the `publishable_view` projection is
wired to the endpoint) and when the `contradiction`/`research_task` tables are
written for real (the Python entity is persisted or superseded by an ORM/row shape).
Also revisit if the `input_digest` definition changes (the committed rebuild sample
must be regenerated) or if a new contradiction detector is added (it must satisfy the
detector→task contract and appear in `test_detector_task_contract.py`).
