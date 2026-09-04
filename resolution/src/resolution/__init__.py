# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `resolution` package: the identity substrate (§11.1-11.3, §14).

This package owns *stable identity before anything is counted* (Phase 3): the
Jurisdiction registry with temporally-versioned geometry (:mod:`resolution.jurisdiction`),
the Organization registry — identifiers-as-sets, the two classification axes, the
surrogate identity basis, and agency-name parsing (:mod:`resolution.identity`),
the reified bitemporal temporal-identity relations and the rule that a rename is
not a succession (:mod:`resolution.temporal_identity`), fixed-width GEOID
validation (:mod:`resolution.geoid`), the agency-centroid geometry guard
(:mod:`resolution.geometry_precision`), and the zero-record ingest guard
(:mod:`resolution.registry_ingest`).

P03.2 adds the deterministic, explainable half of entity resolution on top of that
substrate: the versioned name normaliser (:mod:`resolution.normalize`), ORI
validation and the UCR↔USPS table (:mod:`resolution.ori`), the per-class canonical
scheme registry and crosswalk exports (:mod:`resolution.crosswalk`), the tiered
address keys (:mod:`resolution.address`), vendor-portal slug parsing
(:mod:`resolution.slug`), the deterministic cascade tiers 0–3
(:mod:`resolution.cascade`), and public ``sig:`` identifier minting with the
split/merge stability contract (:mod:`resolution.public_id`).

P05.1 adds the probabilistic top of the cascade and the §14.7 quality gates: the
Splink 4 / DuckDB matcher and tiers 4–5 that create PROPOSED review proposals
(:mod:`resolution.probabilistic`), sized blocking (:mod:`resolution.blocking`), the
gold set with double adjudication and a frozen holdout (:mod:`resolution.gold_set`),
the pairwise/B-cubed metrics with auto-write demotion and cluster-shape alerts
(:mod:`resolution.quality_gates`), and the re-runnable ER pipeline stage that composes
the six tiers, records its run, and keeps public identifiers stable across cluster
change (:mod:`resolution.er_run`).

P05.2 adds the internal review queue and curation contract (:mod:`resolution.review_queue`,
§14.6/§25/§27): a human accepts/rejects each tier-4/5 PROPOSED match with its
per-comparison confidence explanation surfaced inline (SIG-IDENT-025), and adjudicates the
model-assisted extractions from the upstream ``parsing`` stage — logging ``model_id`` and
``prompt_version`` with every decision on model output (SIG-IDENT-026). Nothing in the
queue writes to the graph; LLM output reaches only the queue (SIG-LLM-002).
"""

__version__ = "0.0.0"
