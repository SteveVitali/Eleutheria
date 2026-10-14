# ADR-204 — The quality-check registry schema, the outcome vocabulary, and the ruleset diff (P34.44a)

- Date: 2026-10-08
- Status: accepted
- Ticket: P34.44a (Round 11 / P34, row 255 — ADR-154 decision 1's registry +
  decision 2's ratchet rules, engineered; SIG-CONF-006/007, B4 G11)
- Base: `r11/P34.49-part-viii-at-rest-audit`
- Related: ADR-154 (the suite decision this row implements — it named the
  registry, the modes, the "ratchets move only toward thresholds" rule and
  the fixing-row flip), ADR-202 (the `sig_audit` read-only posture the M
  checks connect under), SIG-CONF-001 (the basis-class vocabulary),
  SIG-CONF-003 (only mechanical checks gate), SIG-ENG-042 (no vacuous
  pass), SIG-CONF-013 (the probe-run audit record)

## Context

ADR-154 decided *that* the suite exists and *what* its modes mean. Four
mechanical questions it left open needed pinning in this row:

1. **Where the registry's vocabulary lives.** A TOML row's `placement`,
   `mode`, `basis_class`, `direction` and `threshold` must be closed sets a
   validator can refuse, or "a change is reviewed like a ruleset" is
   unenforceable.
2. **What a check outcome is.** ADR-154 names pass/fail semantics but a
   spine that cannot yet evaluate a check (a missing seam) and a check
   that evaluated zero items are both honest non-results that must never
   read as green.
3. **How the ratchet's rules apply to the registry itself.** "Baselines
   move only toward thresholds" and "a check flips to `enforce` only in
   its fixing row" need an executable diff, not prose — the diff is what
   a reviewer or CI consults when the file changes.
4. **Which checks have evaluators today.** The seed spine lacks the
   collapse/lineage/replay seams several checks measure; the harness must
   say so as `not_evaluable`, not fail the run on absent machinery nor
   silently pass.

## Decision

- **`sig.quality-checks/1` is the registry schema** — the versioned,
  reviewed ruleset at `exports/src/exports/data/quality_checks.toml`.
  Every `[[check]]` carries `id`, `statement`, `population`,
  `placement[]`, `mode`, `direction`, `threshold`, `baseline`,
  `unit`, `basis_class`, `fixing[]`, `from`, `note`. `load_registry`
  validates before parsing and refuses a gating `mode` on a B3/B4 basis
  (SIG-CONF-003, mechanical), an unknown `fixing` row, or a missing
  required field.
- **The outcome vocabulary is `pass | fail | not_evaluable |
  unbaselined`.** `not_evaluable` carries a mandatory reason and names
  the seam's owner; `unbaselined` is a ratchet check whose baseline is
  `pending` (recorded, never gating — P34.44b's baseline run sets it).
  A check with `evaluated = 0` is `fail` (SIG-ENG-042, B4 G11 — no
  vacuous pass).
- **`sig.quality-report/1`** is the per-run record (placement, target,
  registry digest, per-check offered/evaluated/measured/baseline/
  threshold/outcome, totals, summary) and **`sig.probe-run/1`** wraps it
  in the established probe envelope (SIG-CONF-013's shape); **`sig.
  quality-gate/1`** is the release-V15 verdict record (`run_release_gate`
  — standalone now, joins V15 with P35.58; a `not_evaluable` enforce
  check fails closed).
- **The ruleset diff is executable** — `diff_registry(old, new, ticket,
  adr_ids)` enforces: a baseline moves only toward its check's
  `direction`-relative threshold (establishing a `pending` baseline is
  always legal); erasing or loosening a baseline, loosening a threshold,
  weakening a mode, or removing a check each require a cited new-ADR id;
  a `ratchet→enforce` flip is legal only when the landing `ticket` is one
  of the check's `fixing` rows, and never for a non-gating basis.
- **Unwired seams are named, not hidden** — `ops.quality.SEAM_DEFERRALS`
  records each registered check whose evaluation seam does not exist yet
  (GQ-02/06/08/09/10/12/16/17/19/20/23/25/26) with the fixing row that
  lands it; the runner reports them `not_evaluable`.

## Consequences

- The suite's wire contract is closed and reviewable: any change to the
  registry diff's rules or the outcome vocabulary is a new ADR, not an
  edit.
- `sig-exports quality validate` + `sig-exports quality diff` make the
  rules checkable by a human, a script or CI before a registry change
  merges; `sig-ops quality run`/`gate` are the read-only harness and the
  V15 hook.
- Pending baselines and seam deferrals are first-class record fields, so
  the P34.44b baseline run and the fixing rows have explicit slots to
  fill — nothing invents a pass.
- The harness's implemented evaluators today are the M/P/R spine and file
  scans (GQ-03/05/07/11/13/14/15/18/21/24/27); everything else is a named
  deferral, not an absent check.

## Alternatives considered

- **Fail `not_evaluable` checks outright** — rejected: it conflates "the
  spine failed the check" with "the check could not run", which the
  Class-S classifier and reviewers must distinguish; a not-evaluable
  *enforce* check still fails the release gate closed.
- **Baselines as a separate ledger file** — rejected: the registry is the
  one reviewed ruleset; splitting the baseline column out would make the
  diff's toward-threshold rule span two files and two reviews.
- **Zero-evaluated as `not_evaluable`** — rejected: SIG-ENG-042/B4 G11
  require the loud failure; an evaluator that could not run has
  `not_evaluable` for exactly that case, while "ran and saw nothing" is a
  measured vacuum that must not pass.

## Revisit trigger

- A check needs an outcome the four-value vocabulary cannot express (e.g.
  a waived enforce) — the vocabulary is closed; widening it is a new ADR.
- P34.44b's baseline run measures a check whose registry `baseline`
  placeholder was wrong in kind (not merely in value) — the diff accepts
  the correction but the placeholder policy is re-examined.
- A non-mechanical basis class is proposed for a gating mode — SIG-CONF-003
  forbids it today; any change is an amendment to that requirement and a
  new ADR, never a validator edit.
- The registry needs fields beyond `sig.quality-checks/1` (e.g. a per-check
  sampling policy) — the schema versions to `/2`, and `load_registry`
  keeps reading `/1` (additive, back-compat).

### Trigger evaluation

- P34.44a (row 255, 2026-10-08): the ADR authored its own trigger; quiet
  at authoring — no trigger condition obtains (no outcome beyond the
  four, baselines are placeholders by design, no B3/B4 gate proposal, the
  schema is `/1`).
