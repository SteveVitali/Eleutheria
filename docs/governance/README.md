# SIG governance and safety policies

This directory is SIG's **prose governance record** — the adopted policies that
govern how the project handles harm, decides contested questions, states its
purpose honestly, and protects the people who contribute to it. These are the
policy documents required by Phase 0 (§52, "Adopted policy documents") and the
universal phase gate (§51.3).

The *executable* halves of these policies live as tested code, not prose:

- The **suppression** and **corrections-preserve-history** primitives that the
  takedown policy depends on are implemented in `policy/src/policy/governance.py`
  and tested in `tests/unit/test_governance_policy.py` (SIG-GOV-005/007/008).
- The pipeline rules — licence gate, coordinate matrix, officer-naming test,
  crawler conduct, threat model — are in the `policy/` package (owned by P00.2).

To change a requirement, amend the canonical spec
(`docs/2_canonical_design_spec.md`) via an ADR (SIG-ENG-003) — these documents
adopt the spec's policy, they do not redefine it.

## The policies

| Policy | Covers | Spec | Requirement ids |
|---|---|---|---|
| [Takedown, corrections & suppression](takedown-corrections-suppression.md) | intake, SLAs, corrections that preserve history, suppression vs deletion, disputes, transparency reporting | §45 | SIG-GOV-001…011 |
| [Governance & Code of Conduct](governance-and-code-of-conduct.md) | decision-making, editorial board, capture resistance, continuity/succession posture | §46.2, §46.4–46.5 | SIG-GOV-014…016, SIG-GOV-021 |
| [Anti-misuse statement](anti-misuse-statement.md) | the dual-use tension, stated honestly and in public | §46.3 | SIG-GOV-019 |
| [Contributor safety](contributor-safety.md) | PII minimisation, pseudonymity, know-your-rights, the detained-contributor policy | §34.3 | SIG-CONTRIB-005…008 |
