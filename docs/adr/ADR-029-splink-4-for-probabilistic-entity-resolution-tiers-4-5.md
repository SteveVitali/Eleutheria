# ADR-029: Splink 4 on DuckDB for the probabilistic ER tiers 4–5, as a fully-specified deterministic model

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P05.1
- **Requirement ids:** SIG-IDENT-020, SIG-IDENT-021, SIG-IDENT-023, SIG-IDENT-024, SIG-IDENT-025, SIG-IDENT-027, SIG-IDENT-028, SIG-IDENT-029, SIG-IDENT-032, SIG-RECON-001, SIG-RECON-002
- **Spec:** docs/2_canonical_design_spec.md §14.6 (the six-tier cascade), §14.7 (quality gates), §14.8 (public-identifier stability), §27 (the ER pipeline stage); ADR-005 (resolution as a stored decision record), ADR-010 (the DuckDB analytics boundary), ADR-025 (invariants as data-quality checks)
- **Appendix F note:** the canonical spec's Appendix F index lists this decision as its logical "ADR-016 (Splink 4 for probabilistic ER)". The repository's ADR-016 was already taken by the Dagster orchestration decision; ADRs are immutable and numbered in landing order (SIG-ENG-003), so the Splink decision lands here as ADR-029. Same decision, different sequence number.

## Context

P05.1 owns the probabilistic top of the resolution cascade — tiers 4 (probabilistic)
and 5 (weak-signal), each of which MUST create `PROPOSED` claims routed to human
review and MUST NEVER auto-write (SIG-IDENT-020) — plus the §14.7 quality gates that
everything downstream (network analytics, P06.1) is forbidden to ship before
(SIG-IDENT-030 / SIG-RECON-003). The deterministic tiers 0–3 already exist as a pure
library (P03.2, `resolution.cascade`); connectors are not yet DB-wired (ADR-026), so —
as with the `osm`/`atlas` connectors — this ticket realises the probabilistic tier at
**the layers that exist today**: pure, tested library code plus versioned data, not a
live claim-table writer. The review-queue persistence and curation UI are P05.2.

SIG-IDENT-021 names the matcher: **Splink 4 (MIT) on a DuckDB backend**; AGPL and
proprietary matchers are excluded by SIG-STORE-002. The open question this ADR settles
is *how* to use Splink such that the output is deterministic, explainable, and
reproducible — a learned/EM-trained model that produces different weights run to run
would violate the defining standard's "no synthetic certainty" and make a match weight
undefendable to a journalist.

## Decision

1. **Splink 4 on DuckDB is the probabilistic matcher** (SIG-IDENT-021), added to
   `resolution`'s dependencies and driven through a **lazy import** so the rest of the
   `resolution` package (and its light CLI paths) do not pay Splink/DuckDB/pandas import
   cost. `resolution.probabilistic.ProbabilisticMatcher` builds a DuckDB `Linker`,
   predicts over sized-blocked candidate pairs, and maps each scored pair onto a tier.

2. **The model is fully-specified, versioned data — not a trained artifact**
   (`resolution/src/resolution/data/splink_model.toml`, read through the repo's
   `@cache` + `tomllib` convention). Every comparison level carries its own `m` and `u`
   probability, so the Fellegi–Sunter **match weight and its per-comparison Bayes-factor
   decomposition are deterministic** — no expectation-maximisation runs at match time,
   and the same input always produces the same weight. This is the §28.1 "rule-based and
   explainable, ruleset-as-data" principle applied to the probabilistic tier, and it is
   what makes SIG-IDENT-025's "match weight + per-comparison decomposition" real and
   diffable. Changing the model is a versioned migration (bump `version`).

3. **Tiers are match-weight bands, and both 4 and 5 are PROPOSED → review, never
   auto-write** (SIG-IDENT-020). Weight ≥ `tier4_review` → tier 4; `tier5_weak` ≤ weight
   < `tier4_review` → tier 5; below `tier5_weak` → tier 6, **discarded with no per-pair
   record**. Every `ProbabilisticMatch` carries `disposition="review"` and an evidence
   block stamped `claim_status="PROPOSED"`.

4. **Blocking is sized before use; trigram is candidate-search only**
   (`resolution.blocking`). Every blocking rule is sized against a documented comparison
   ceiling and rejected if oversized; blocking on suffix alone or state alone is
   prohibited (SIG-IDENT-023). Trigram similarity may generate candidate blocks but
   `assert_no_trigram_decision` rejects any model whose comparison `sql_condition` uses
   trigram/q-gram set similarity (or the pg_trgm `%` operator) as a decision score;
   edit-distance measures (Jaro-Winkler) remain allowed (SIG-IDENT-024).

5. **The gold set is stratified, double-adjudicated, and has a frozen holdout**
   (`resolution.gold_set`, SIG-IDENT-027): stratified blocked-pair sampling across
   weight bands; a three-value label vocabulary (`match` / `non_match` /
   `not_enough_information`); Cohen's κ between two adjudicators; per-label provenance;
   and a frozen holdout partition that is immutable — relabelling a holdout pair raises.

6. **Quality gates run per ER run and can demote an auto-write tier**
   (`resolution.quality_gates`, SIG-IDENT-028/029): pairwise precision/recall/F1 at each
   tier boundary and B-cubed cluster precision/recall on the holdout; an auto-write tier
   whose holdout precision falls below the published floor
   (`auto_write_precision_threshold`) is **demoted to review**; and cluster-shape alerts
   fire on the bad-merge signatures — an oversized law-enforcement cluster, or two
   substantial components joined by a single bridge edge.

7. **ER is a distinct, re-runnable pipeline stage** (`resolution.er_run`,
   SIG-RECON-001/002): an `ERRun` record (resolver/model/ruleset versions, code commit,
   input digests, a deterministic `LC_ALL=C`/`TZ=UTC` environment) with a rollback
   status and its own `ERQualityReport`; it runs strictly between `normalize()` and
   `load()`. A re-cluster (`recluster`) runs under a **new ruleset version** and emits
   **new `same_as` assertions** without mutating the prior run's — append-only history.
   Cluster-shape changes across runs are routed through
   `resolution.public_id.PublicIdRegistry` (`stabilise_cluster_change`) so a surviving
   public identifier is preserved and a retired one becomes a redirect/tombstone, never
   silently reassigned (SIG-IDENT-032).

## Consequences

The probabilistic tier is now a deterministic, explainable, fully-tested library the
review queue (P05.2) and the network-analytics gate (P06.1) can build on: a reviewer
sees a match weight decomposed into per-comparison Bayes factors, and the auto-write
demotion + cluster-shape alerts are the §14.7 gates SIG-IDENT-030 requires before any
centrality surface ships. Costs and deferrals, stated rather than hidden:

- **A heavier dependency footprint.** Splink pulls DuckDB, pandas, numpy, sqlglot,
  altair, and igraph into the `resolution` runtime. mypy cannot consume their stubs
  under the project's 3.11 target (numpy's stubs use 3.12-only syntax), so a
  `follow_imports = "skip"` override treats them as `Any`; our own ER code stays fully
  type-checked. The lock export (`pylock.toml`) and SBOM grow accordingly.
- **No live claim-table write path.** Like the connectors (ADR-026/027/028), the ER
  stage produces `PROPOSED` proposals, `same_as` relations, and a run record as
  in-memory value objects with `to_row()` shapes; wiring them to the `claim`/`resolution`
  tables and the review queue is P05.2/P08.x. The append-only, versioned, provenance-
  carrying shapes that make that wiring faithful are established here.
- **The model's m/u are seeded by judgement, not trained.** The committed values are
  reasonable priors for organisation matching, not EM-fitted estimates; the gold set and
  holdout exist precisely to measure and, via the demotion gate, to bound the risk of a
  mis-specified model. Refitting is a versioned model migration, never a silent change.

## Alternatives considered

- **A learned / EM-trained Splink model** — rejected: non-deterministic run to run and
  its weights are not defensible as a stated rule (§28.1, SIG-RECON-004). A
  fully-specified m/u model gives the same Fellegi–Sunter math with reproducible,
  explainable output.
- **A hand-rolled probabilistic scorer** — rejected: SIG-IDENT-021 names Splink 4
  specifically, and re-implementing Fellegi–Sunter + clustering would be less tested and
  less interoperable than the MIT-licensed standard tool.
- **Auto-writing high-weight probabilistic matches** — rejected outright: SIG-IDENT-020
  forbids it. A probabilistic tier may only propose; nothing uncertain writes itself
  (the Phase-5 goal, §52).
- **Trigram similarity as a decision score** — rejected: SIG-IDENT-024. Trigram powers
  candidate search only; the decision score is the model's match weight, guarded by
  `assert_no_trigram_decision`.
- **Storing the Splink model as native JSON / Python literals** — rejected for the same
  reason as the connector vocabularies (ADR-027/028): it would defeat the §20 versioned-
  migration model and the diffable "ruleset-as-data" principle (SIG-ENG-001, §28.1).

## Revisit trigger

Holdout precision for an auto-write tier cannot reach the published
`auto_write_precision_threshold` even after model refinement (the demotion gate fires
persistently), indicating the deterministic tiers themselves need revision; or the gold
set grows large enough to justify EM-estimated `u` values (with the determinism/
explainability trade-off re-examined); or Splink 4's API or licence changes, or a DuckDB
scaling limit is hit at national record volume such that the backend must change; or the
review queue / claim-table write path (P05.2) lands and needs a firmer contract from the
ER stage than "in-memory proposals + run record with `to_row()`".
