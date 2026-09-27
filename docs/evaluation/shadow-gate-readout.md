<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Shadow confidence-gate readout — P32.10 (SIG-EVAL-003/004, ADR-129)

The **evaluation half** of the campaign machinery: what runs *after* a
custodian unseals a campaign, and — critically — what it may and may not
decide in this build.

## What it is

`resolution/evaluator.py` + `data/eval_confidence.toml` (`eval-confidence/1`)
compute the preregistered auto-write gate against released reference labels:

- **Four separate estimands**, each with its named frame, weights,
  numerator/denominator and an honest `measured | partial | unavailable`
  state: auto-positive precision, candidate recall (never from a
  candidate-only frame), whole-cluster quality (never from a pair-only
  frame), and labelability.
- **Design-matched inference**: exact Clopper–Pearson only under a declared
  independent/equal-probability frame with a recorded independence basis;
  exact hypergeometric inversion for finite SRS/stratified/grouped designs;
  enriched strata are diagnostics, never certification evidence. Correlated
  or enriched samples can never select the iid method.
- **Preregistered gate**: one hypothesis per (tier, scope), Bonferroni
  family α = 0.05, strict-precision lower bound ≥ 0.98, fixed
  `stopping_rule = 'fixed'`, `scheduled_analyses = 1`. Missing labels stay
  in the denominator; `insufficient_evidence` and `unresolved` are
  non-successes; sealed units block.

## What it is not — the shadow boundary

`mode` is **`shadow`**. The gate's verdicts and per-tier recommendations
are *reported*; `applied` is always empty:

- No tier is promoted — certification requires the measured post-HUMAN-H5
  P32.23 decision (new ADR + `operational` release + nonzero sample —
  `evaluator.activate_policy` enforces all three and currently always
  refuses).
- No tier is demoted by installing the evaluator — the explicitly
  PROVISIONAL production policy
  (`camera_sites.decide_auto_write_tiers` + the P28-era metrics) is
  untouched; a pre-campaign safety demotion would be a separate explicit
  operational decision.
- Historical point-gate numbers ride the report as labelled
  `historical_point_gate` rows — history, never eligibility evidence.

## Reading a report

`sig-resolution eval gate --dsn … --campaign-id … --design design.json
[--tiers tiers.json] [--format md]` prints the report:

- `gates[]` — per hypothesis: strict counts, `point_strict`, `lower_bound`,
  `method`, `verdict` (`certified | not_certified | incomplete |
  not_applicable | invalid`), `reasons`, and `recommended_disposition`
  (`certify` / `retain_provisional` / `review_only_fail_safe`), always
  `applied: false`.
- `estimands` — the four rows above; an `unavailable_reason` names exactly
  why a frame cannot speak (e.g. `candidate_only_frame`,
  `no_reference_clusters`).
- `design_problems` — structural reasons the design cannot drive inference
  (`correlated_units_in_iid_frame`, `optional_stopping_rule`,
  `multiplicity_alpha_exceeded`, …).
- `report_digest` — sha256 over the whole payload; identical inputs give an
  identical digest.

## The numbers that matter (pinned by tests)

| family | α per hypothesis | all-success n needed for bound ≥ 0.98 |
|---|---|---|
| one prespecified tier | 0.05 | **149** (148 fails) |
| two prespecified tiers (Bonferroni) | 0.025 each | **183** (182 fails) |
| the old 70/70 holdout | 0.05 | bound ≈ **0.958** — can never certify |

A zero-error, unresolved, sealed, contaminated or digested-out design never
passes — `incomplete`, `not_certified` or `invalid`, with `reasons` listed.
