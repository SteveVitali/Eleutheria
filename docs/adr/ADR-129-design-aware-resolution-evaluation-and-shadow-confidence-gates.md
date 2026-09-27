# ADR-129 — Design-aware resolution evaluation and the shadow confidence gate (P32.10)

- Date: 2026-10-18
- Status: accepted (engineering; the confidence policy ships `mode='shadow'` — computed and reported, never applied; `D-R10-HUMAN-1` stays open, zero human participation is claimed or required)
- Ticket: P32.10 (Round 10 / S3, row 170; requirements SIG-EVAL-003, SIG-EVAL-004; annotates `D-R6.1-EVAL` — advanced, still OPEN; `D-R10-HUMAN-1`, `D-P30.2b-1`, `D-P30.2b-2` — OPEN)
- Base: the P32.9 closeout tip (`devin/p32-9-human-evaluation-protocol-and-packets`, PR #164)

## Context

SIG-EVAL-003 requires resolution evaluation to report **separate estimands
with explicit frames**: auto-positive precision, candidate-generation recall
and final-cluster quality each speak for a different population with their
own inclusion probabilities, weights, denominators and an honest unavailable
state — never a pooled number. SIG-EVAL-004 requires the auto-write
eligibility gate to be a **preregistered simultaneous lower confidence
bound** over strict precision, with family-wide alpha allocation, a fixed
stopping rule, and strict handling of missing/insufficient labels — where
exact/binomial inference is reserved for an actually justified independent
frame and correlated/enriched designs route to design-aware alternatives or
inconclusive states.

The landed predecessor state cannot produce that gate:

- `camera_sites.measure_tiers` counts only pairs with a label — an absent
  label *vanishes* from the denominator, and `decide_auto_write_tiers` is a
  point-estimate demotion, not a preregistered confidence rule (both stay as
  historical behaviour).
- The 70/70-era holdout was agent/maintainer-labelled (a Cohen's κ
  agreement measure), not human ground truth — and even at n=70 all-success
  the exact one-sided 95% bound is ≈0.958, below the 0.98 floor.
- The S3 research enumerates the unsafe patterns this must refuse: optional
  stopping/peeking, sealed-test reuse after exposure, candidate-only
  "recall", treating correlated/enriched samples as iid, and inventing
  singleton truth for unlabeled cluster entities.

## Decision

**A pure, deterministic `resolution/evaluator.py` + a versioned
`data/eval_confidence.toml` shipping `mode='shadow'`, wired to the P32.9
released-label surface — the gate is computed and reported, and applies
nothing until the measured post-HUMAN-H5 P32.23 decision.**

### Estimands (SIG-EVAL-003) — separate frames, never pooled

`evaluate()` reports four estimands, each an `EstimandReport` carrying
numerator, denominator, rows, the named population and an explicit
`measured | partial | unavailable` state:

- **auto_positive_precision** — strict share of sampled auto-positive edges
  verified `same`, per (tier, scope, stratum) rows with every non-success
  category counted.
- **candidate_recall** — fraction of *independently referenced* same pairs
  the candidate generator offered. A frame drawn only from the matcher's own
  candidates reports `unavailable / candidate_only_frame` — it can never
  observe blocking false negatives. Undecided reference units stay visible
  and enter the strict lower-bound denominator.
- **cluster_quality** — pairwise + B-cubed over entities with independent
  reference-cluster membership. A pair-only sample reports
  `unavailable / no_reference_clusters`; unlabeled entities stay in the
  coverage denominator and are never invented as truth singletons.
- **labelability** — the decisive (same/different) share per stratum;
  insufficient/unresolved/missing stay counted. A report, never a gate
  shortcut.

### Inference follows the declared design (SIG-EVAL-004)

- `clopper_pearson_lower` (exact one-sided binomial inversion, stdlib only)
  is available **only** under a declared `independent_bernoulli` design —
  which additionally requires `equal_probability`, item-level
  `independent_unit`, a non-empty recorded `independence_basis`, and no
  shared dependency group among certifying units. Any failure lists a
  design problem and the iid method is refused — correlated/enriched
  samples can never select it.
- Finite frames (`finite_srs`, `stratified_srs`, `grouped_psu`) use
  `hypergeometric_lower_bound` — exact inversion whose randomness is the
  *sampling design*, so correlated content is legitimate. Multi-cell
  hypotheses combine cell bounds via `Σ_c W_c L_c` with declared population
  weights and Bonferroni alpha across the sampled cells; an unmeasured
  nonempty cell contributes exactly 0. Enriched strata are diagnostics —
  reported, excluded from the gate, never silently pooled.
- **Strict outcomes**: only an adjudicated human `same` on an intact packet
  is a success. `different`, `insufficient_evidence`, `unresolved`, `missing`
  and still-sealed units all stay in the denominator; missing anything →
  the campaign is `incomplete` and cannot certify.
- The gate requires **all** of: human provenance (agent/LLM/synthetic can
  never certify; `llm_agreement` is supplementary reporting only), verified
  manifest, no contamination, frozen candidate/ruleset digests matching, no
  sealed units, complete accounting, a fixed single-analysis stopping rule
  (interim looks, a second analysis or an early stop → `not_certified` /
  `incomplete`), a computable design-matched bound, and bound ≥ 0.98. A
  reused/exposed test set and a zero-sample frame fail by construction; an
  empty deployment frame is `not_applicable`, never a pass.

### Shadow policy, history, and materialization

- `data/eval_confidence.toml` ships `mode='shadow'`, `family_alpha=0.05`,
  `threshold=0.98`, `alpha_allocation='bonferroni'`,
  `stopping_rule='fixed'`, `activation_authority='P32.23-measured-decision'`.
  Every report carries `applied=()`; recommendations (`certify` /
  `retain_provisional` / `review_only_fail_safe`) are report fields —
  adopting a fail-safe demotion is a separate explicit operational
  decision, not an effect of installing the evaluator. `activate_policy`
  refuses on `zero_sample`, `no_operational_release`,
  `no_measured_decision`, and `policy_shadow_mode` — this build cannot arm
  the gate.
- `human_eval_pg.eval_units_from_campaign` materializes `EvalUnit`s from
  samples joined to the **released** label/adjudication views only: the
  current adjudication wins; else the two-independent-label consensus
  (disagreement/insufficient → `unresolved`); else `missing` — with
  `sealed=True` when sealed_final labels are still invisible and
  `packet_ok=False` on a stale packet digest. `run_shadow_evaluation`
  recomputes the manifest live, evaluates, and returns the report.
  `sig-resolution eval gate` prints the JSON/markdown report.
- `HistoricalMetric` carries the legacy point-gate numbers into the report
  labelled `historical_point_gate` — history, never eligibility evidence.
  `camera_sites.decide_auto_write_tiers` and the P28-era metrics are
  untouched.

## Consequences

- The 0.98 gate is now pinned arithmetic, not prose: one prespecified iid
  tier at family α=0.05 needs 149/149 all-success (148 fails); a two-tier
  Bonferroni family needs 183/183 at α=0.025 (182 fails); n=70 all-success
  peaks at ≈0.958 — so the old 70/70 cannot certify even if it were human.
- The report is deterministic: identical input ⇒ identical `report_digest`.
- **Nothing is promoted or demoted by this change.** The PROVISIONAL
  production policy keeps its current posture; the shadow gate must first
  be armed by the measured P32.23 ADR + an `operational` release.
- `D-R6.1-EVAL` is *advanced* — the provisional point-gate's replacement is
  now preregistered machinery awaiting real human evidence — and stays OPEN
  until HUMAN-H5 produces it.

## Alternatives considered

- **Extend `camera_sites` in place.** Rejected: `measure_tiers` silently
  drops absent labels and the tier decision is a point gate; retrofitting
  strict denominators into it would silently change historical behaviour —
  a new module keeps both surfaces honest.
- **Wilson/normal approximations or an "effective sample size" heuristic.**
  Rejected: the ticket and research require *exact* inference matched to
  the declared design — CP only under a justified iid frame, hypergeometric
  under finite sampling; a heuristic ESS manufactures precision the design
  does not support.
- **Sequential/alpha-spending monitoring for early certification.**
  Rejected: unpreregistered optional stopping is exactly the failure mode
  EVAL-A6 bans. The design accepts `stopping_rule='fixed'` and
  `scheduled_analyses=1` only; an early stop may be recorded for futility
  but yields `incomplete`, never a pass.
- **A separate eval-kind column carrying "enriched" on the sample.**
  Rejected: the stratum spec already declares `enriched`; duplicating it on
  the unit invites divergence — the design owns the declaration.

## Revisit trigger

Revisit when: HUMAN-H5 produces the first measured labelled campaign (the
shadow report is re-run against real reference labels and its arithmetic is
re-verified); P32.23 takes the measured decision (arming requires the new
ADR + operational release + nonzero sample — `activate_policy` enforces all
three); a sequential monitoring method is proposed (requires its own
preregistered alpha-spending ADR — the fixed rule stays the default); or
the 0.98 floor/family alpha are re-negotiated (a `eval-confidence/N` bump +
new design digest ⇒ new preregistration).
