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

Eight documents. **Status** is taken from each document itself: *adopted* (a first-class policy
in force), *protocol adopted; not yet run* (the procedure is fixed but its human step is gated),
*published* (a live, machine-checked page), or *template* (a recorded template/instrument a
per-instance run fills in).

| Policy | Covers | Status | Spec | Requirement ids |
|---|---|---|---|---|
| [Takedown, corrections & suppression](takedown-corrections-suppression.md) | intake, SLAs, corrections that preserve history, suppression vs deletion, disputes, transparency reporting | adopted | §45 | SIG-GOV-001…011 |
| [Governance & Code of Conduct](governance-and-code-of-conduct.md) | decision-making, editorial board, capture resistance, continuity/succession posture | adopted | §46.2, §46.4–46.5 | SIG-GOV-014…016, SIG-GOV-021 |
| [Anti-misuse statement](anti-misuse-statement.md) | the dual-use tension, stated honestly and in public | adopted | §46.3 | SIG-GOV-019 |
| [Contributor safety](contributor-safety.md) | PII minimisation, pseudonymity, know-your-rights, the detained-contributor policy | adopted | §34.3 | SIG-CONTRIB-005…008 |
| [Contributor onboarding usability study](contributor-onboarding-usability-study.md) | the moderated ≤10-minute onboarding study: protocol and published results | protocol adopted; not yet run (gate HG-10) | §34.2 | SIG-CONTRIB-003 |
| [Organised Editing activity — SIG operator attribution](organised-editing-activity.md) | the OSM Organised Editing activity page: coordinating org, changeset hashtag, goal, tools + data sources with usage conditions, metrics (task outcomes, not rankings) | published (machine-checked) | §35.2, §42.3a | SIG-CONTRIB-016d…g, SIG-LIC-007a–c |
| [Hostile-reader review — dossier template](hostile-reader-review-dossier.md) | the recorded, release-blocking hostile-reader review of the dossier template version | template | §41 | SIG-UI-042 |
| [Stage-0 outreach letter](stage0-outreach-letter.md) | the published template for first contact with every federation-compact project — addressed to an organisational channel, never a person (Part VIII §0.7); the outcome is recorded before any connector is written | template | §35.1 | SIG-CONTRIB-012/012a/013 |
