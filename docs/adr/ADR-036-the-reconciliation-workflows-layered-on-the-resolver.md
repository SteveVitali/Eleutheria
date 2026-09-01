# ADR-036: The §29 reconciliation workflows as value-object modules layered on the resolver

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P08.2
- **Requirement ids:** SIG-RECON-030, SIG-RECON-031, SIG-RECON-032, SIG-RECON-033, SIG-RECON-034, SIG-RECON-035, SIG-RECON-036, SIG-RECON-037, SIG-RECON-038, SIG-RECON-039, SIG-RECON-040, SIG-RECON-041, SIG-RECON-042, SIG-RECON-043, SIG-RECON-044, SIG-RECON-045, SIG-RECON-046
- **Spec:** docs/2_canonical_design_spec.md §29 (§29.2–§29.8); §28 (the resolver, P08.1); §30 (the L4 inference layer, P12.x)

## Context

P08.2 adds the §29 per-predicate reconciliation workflows on top of the P08.1
`RESOLVE()` resolver: device attribution, sharing-edge, deployment-lifecycle,
retention, policy-vs-configuration, snapshot-diff, and the §29.8 additional
workflows. Two structural questions had to be settled:

1. **Where do the workflow outputs live?** These workflows *emit* contradictions,
   research tasks, and an L4 device-attribution inference. But P08.3 (§31) owns the
   materialized `Contradiction` entity and its lifecycle, and P12.x (§30) owns the
   full L4 inference layer and its persistence (`inference.derived_fact` already
   exists as DDL). This ticket must not pre-empt either.

2. **How are fuzzy-dated lifecycle events ordered?** SIG-RECON-040 requires EDTF
   *envelope* ordering. The canonical, deterministic envelope derivation already
   exists — `db.edtf.derive_envelope` (ADR-024) — but the `reconcile` package did
   not depend on `sig-db`.

## Decision

1. Implement each §29 workflow as a **thin, immutable value-object module** in the
   existing `reconcile/` package (`attribution.py`, `sharing.py`, `lifecycle.py`,
   `retention.py`, `policy_config.py`, `snapshot_diff.py`, `additional.py`),
   following the `counts.py` / ADR-031 precedent. They return in-memory frozen
   dataclasses (`Contradiction`, `ResearchTask`, `Inference`, and per-workflow
   result objects); they **do not persist**. The materialized `Contradiction`
   entity is P08.3; the L4 inference layer/persistence is P12.x. The workflow
   *contracts* this ticket owns — the `SHARING_ASYMMETRY`/`replaced_by` renderings
   and the per-field snapshot-diff event shape — are the stable surface downstream
   tickets consume.

2. Add a shared L4 `Inference` value object to `reconcile.model`, aligned with the
   `inference.derived_fact` columns, whose invariants are enforced by the type:
   `layer` is always `"L4"`, `is_observation` is always `False`, `pushable_to_osm`
   is always `False`, and `as_observed_operator()` raises (SIG-RECON-031). Promotion
   to asserted requires a human confirmer or a `D1`/`D2` source (SIG-RECON-033); a
   high inference score never promotes itself.

3. Add `sig-db` as a workspace dependency of `reconcile` and **reuse**
   `db.edtf.derive_envelope` for lifecycle ordering, rather than duplicating the
   EDTF envelope ruleset. A single source of truth for the envelope derivation
   (ADR-024) is worth the dependency edge; `db.edtf` is pure (no database
   connection at import), so no runtime coupling to Postgres is introduced.

4. Model the three §29.5 retention predicates (`policy_written_retention_days`,
   `configured_retention_days`, `vendor_default_retention_days`) as local string
   keys within the retention workflow. `policy_written_retention_days` is not yet a
   registered predicate in `ontology/vocab/predicates.yaml` (it appears only in the
   spec text); because this workflow keeps the three distinct and does **not** run
   them through the registry-driven `RESOLVE()` weighting, no registry change is
   required here.

## Consequences

The politically consequential distinctions §29 exists to protect are made
mechanical and testable: attribution is an L4 `probable` inference that cannot be
written as observed or pushed to OSM; sharing asymmetry is a `SHARING_ASYMMETRY`
finding plus a research task, never a merge; vendor replacement renders as "vendor
replaced," never "surveillance removed"; a canceled contract coexisting with
installed hardware is stated plainly; policy-vs-configuration divergence carries
both sides' evidence and cannot be collapsed. The snapshot-diff event shape and the
sharing/lifecycle edge renderings become the contract P11.1 (portal) and P12.2
(access edges + closure) build on, so those tickets extend this reconciler rather
than forking it. The workflows remain intentionally partial where the spec defers:
persistence, the contradiction lifecycle, and the full L4 layer are downstream.

## Alternatives considered

- **Persisting contradictions/inferences here** (rejected: P08.3 and P12.x own
  those entities and their lifecycles; materializing them now would create two
  competing owners of the same tables).
- **Duplicating a minimal EDTF-envelope derivation inside `reconcile`** to avoid the
  `sig-db` dependency (rejected: it would fork the ADR-024 ruleset and risk silent
  divergence between two envelope implementations — exactly the kind of hidden
  inconsistency §3.1 forbids).
- **Registering `policy_written_retention_days` in the ontology now** (rejected:
  out of this ticket's scope; the retention workflow does not need registry
  epistemics because it keeps the predicates distinct rather than weighing them).

## Revisit trigger

Revisit when P08.3 lands the materialized `Contradiction` entity and P12.x lands
the L4 inference layer: at that point the value objects here are wired to their
persisted forms (or superseded by them), and the device-attribution `Inference`
is promoted onto `inference.derived_fact`. Also revisit if a §29 workflow needs
registry-driven weighting (e.g. retention resolved through `RESOLVE()`), which
would require registering `policy_written_retention_days` as a predicate.
