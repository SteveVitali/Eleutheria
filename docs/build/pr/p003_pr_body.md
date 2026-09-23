## Summary
Implements **P00.3 — Governance, takedown, and contributor-safety policies** (canonical spec §45/§46/§34.3). Adopts and publishes SIG's prose governance record, with the two load-bearing distinctions — **corrections preserve history** and **suppression is not deletion** — shipped as tested, executable primitives ahead of the claim spine (P02.1) that will enforce them in Postgres.

Stacked on `devin/p00-2-policy-as-code` (PR base).

## What changed
- **`policy/src/policy/governance.py`** — an append-only `BeliefLog` model:
  - `correct()` appends a new assertion with `revises` + `correction_reason` (never overwrites); `value_as_of_belief()` still returns the pre-correction value (SIG-GOV-005, mirrors §16.6).
  - `suppress()` flags material out of public surfaces while retaining it internally under the `sealed` tier with author + rationale (SIG-GOV-007), distinct from `delete()`.
  - `delete()` — reserved true deletion: two distinct authorizers required, leaves a tombstone (category + date, never content) (SIG-GOV-008).
- **`policy/src/policy/data/takedown.toml`** — intake categories/SLAs (privacy & safety prioritised above all), permitted outcomes incl. refuse-with-reasoning, transparency-report shape — data, not code (SIG-GOV-001..004/011). Wired into `policy validate`.
- **`docs/governance/`** — takedown/corrections/suppression, governance & Code of Conduct (editorial board, capture resistance, continuity/degraded-mode posture), the **anti-misuse statement published verbatim as a first-class page** (SIG-GOV-019), and contributor safety (PII-minimisation window, pseudonymity, know-your-rights/no-interference, detained-contributor policy). Linked from an index + the repo README.
- **`docs/traceability.md`, `docs/risk_register.md`** — P00.3 sections added for the phase gate (§51.3).

## Design decisions
- The governance primitives are modelled in-memory (not wired to a DB) because the claim spine does not exist yet — this ticket fixes the *policy* those later mechanisms implement (per the ticket's scope note). The `BeliefLog` shape deliberately mirrors the append-only claim table (no writable "current value").
- Policy tables kept as data (`takedown.toml`) to match the P00.2 convention (`data/`, not code).
- No design deviations from the spec ⇒ no new ADR required.

## Out of scope (confirmed not done)
Pipeline enforcement of these rules (later phases); the contributor *system* — tiers/onboarding/revert/anti-poisoning (P16.1); the source registry (P00.4). Pre-existing uncommitted edits to `docs/2_canonical_design_spec.md` were left untouched and unstaged.

## Verification
- `make check` → green (lint + format + mypy + pytest + verify-gen).
- `uv run pytest` → **236 passed** (23 new across `test_governance_policy.py` + `test_governance_docs.py`).
- `uv run python -m policy validate` → self-checks OK (5 intake categories, 5 outcomes).

## Acceptance criteria → evidence
| AC | Evidence |
|---|---|
| Every governance policy document published and linked | `docs/governance/*` + repo README + index; `test_governance_docs.py` (published + linked) |
| Suppression distinct from deletion; corrections preserve prior belief (as_of_belief before correction returns old value, mirrors §16.6) | `policy/governance.py`; `test_governance_policy.py::test_correction_preserves_prior_belief`, `::test_suppression_is_distinct_from_deletion`, `::test_deletion_requires_two_person_auth_and_leaves_tombstone` |
| Anti-misuse statement (SIG-GOV-019) published verbatim as a first-class page | `docs/governance/anti-misuse-statement.md`; `test_governance_docs.py::test_anti_misuse_statement_published_verbatim` |
| Contributor safety documents pseudonymity + PII-minimisation window (SIG-CONTRIB-005..008) | `docs/governance/contributor-safety.md`; `test_governance_docs.py::test_contributor_safety_documents_pseudonymity_and_pii_window` |
| Phase gate (§51.3): CI green; automated tests; traceability + risk register updated | `make check` green; `docs/traceability.md` + `docs/risk_register.md` P00.3 sections |

Requirement ids: SIG-GOV-001..011, 014, 015, 016, 019, 021; SIG-CONTRIB-005..008.

Spec: `docs/tickets/P00.3__governance-policies.md`.

Generated with [Devin](https://devin.ai)
