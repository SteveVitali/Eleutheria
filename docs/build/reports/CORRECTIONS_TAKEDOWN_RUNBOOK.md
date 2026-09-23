# Corrections / takedown operator runbook (§36/§45, ADR-100)

**Owner:** SIG operator (the vetted maintainer set). **Scope:** how the operator
processes a report received through the anonymous, no-account public `/dispute`
channel into append-only records and, where warranted, an append-only correction
claim — without ever requiring the reporter to identify themselves.

This runbook is the *operational how-to*. The *policy* (SLAs, permitted outcomes,
the distinctions) is `docs/governance/takedown-corrections-suppression.md`; the
*executable primitives* are `policy/src/policy/governance.py` (the append-only
`BeliefLog`) and `policy/src/policy/corrections_intake.py` (the intake ops loop);
the *public page* is `web/src/pages/dispute.astro`.

## The identity-minimization contract (ADR-100, Part VIII §0.7)

- The `/dispute` channel is **anonymous and no-account**. **Never** require the
  reporter to identify themselves (SIG-GOV-002). The one exception is a **legal
  demand that needs standing** — and even then the intake accepts the submission;
  the standing check happens when you *act on* it, not at intake.
- Store **no PII** about a reporter. `DisputeSubmission` has no name/email/IP field;
  the only optional personal datum is a `contact` the reporter *chose* to give for a
  legal demand. Do not solicit more.
- Reporter is a pseudonymous label at most (`"anonymous"` by default).

## Reference: what the channel accepts

Run `uv run python -m policy corrections` for the live vocabulary. Summary:

- **Categories** (SIG-GOV-001, priority-ordered): `privacy_harm`, `security_concern`
  (both prioritized **above all others**, SIG-GOV-003), then `factual_error`,
  `legal_demand` (may require standing), `copyright_claim`.
- **Outcomes** (SIG-GOV-004): `correct`, `annotate`, `suppress`, `delete`, `refuse`.
  **Refusal is a real, exercisable outcome** and MUST carry published reasoning — a
  process that cannot say no is a heckler's veto.

## Procedure

1. **Record the submission (append-only).**
   ```python
   from datetime import UTC, datetime
   from policy.corrections_intake import CorrectionsIntake
   intake = CorrectionsIntake()  # compose a persisted BeliefLog in a real run
   intake.submit(
       submission_id="d-2026-09-23-001",
       category="factual_error",           # must be a known category
       subject="agency:okcpd",             # the disputed subject/claim id
       description="operator is Motorola, not Flock",
       at=datetime.now(UTC),
       # reporter defaults to "anonymous"; DO NOT add identity you were not given
   )
   ```
   Unknown category → refused (`IntakeError`). No identity is ever demanded.

2. **Triage by published priority (SIG-GOV-003).** Handle `privacy_harm` /
   `security_concern` **before** factual corrections. Honor the published SLAs
   (`policy/src/policy/data/takedown.toml`).

3. **Dispose (append-only, with a reason + your operator actor id).**
   - **`correct`** — the claim is wrong. This writes an **append-only correction
     claim**: the prior value is preserved and still resolves at its belief-time
     (SIG-GOV-005) — never an overwrite.
     ```python
     intake.dispose(
         submission_id="d-2026-09-23-001", outcome="correct",
         reason="procurement contract OKC-2026-0142 shows Motorola",
         at=datetime.now(UTC), actor="operator-1",
         subject="agency:okcpd", corrected_value="Motorola",
     )
     ```
   - **`annotate`** — attach a response alongside an accurate claim (SIG-GOV-010).
   - **`suppress`** — remove from public surfaces, retain internally under seal
     (`BeliefLog.suppress`, SIG-GOV-007). Distinct from deletion.
   - **`delete`** — reserved for material SIG must not hold at all; **two distinct
     authorizers** required, leaves a content-free tombstone (`BeliefLog.delete`,
     SIG-GOV-008).
   - **`refuse`** — decline **with published reasoning** (SIG-GOV-004). A reasonless
     disposition — even a refusal — is rejected (`IntakeError`).

4. **Publish the transparency report (SIG-GOV-011).** `intake.transparency_report()`
   returns counts by category and by outcome **including refusals**. Refusals are
   counted like every other outcome; a report that hides them is not one.

## Invariants (never relax)

- Append-only: a change of decision is a **new** disposition row, never a mutation;
  a correction is a **new** assertion, never an edit or delete of the prior value.
- No forced identity, no reporter PII (ADR-100, Part VIII §0.7).
- Refusal stays a real option; every disposition carries a reason and your actor id.
- Suppression ≠ deletion; true deletion needs two authorizers + a tombstone.
