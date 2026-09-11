# Contributor onboarding — moderated usability study

*Adopts docs/2_canonical_design_spec.md §34.2 (SIG-CONTRIB-003). Before the
contributor system is declared complete, a moderated usability study MUST be run
with at least five participants who have no prior knowledge of the ontology,
measuring the time from the landing page to their first accepted contribution.
The **median MUST be at or under ten minutes**, and the protocol and results MUST
be published. This study is **re-run on any change to the contribution flow.***

The measured result is machine-checked: the as-run participant data lives in
`tasks/src/tasks/data/usability_study.toml`, and the harness in
`tasks/src/tasks/onboarding.py` recomputes the median over the ontology-naïve
cohort and re-asserts the gate (`tests/tasks/test_tasks_onboarding.py`). Swapping
the data for a new session's measurements re-checks the requirement automatically.

## Protocol

- **Recruitment.** At least five participants with **no prior knowledge of the
  SIG ontology** (ontology-naïve). SIG-experienced people may participate as
  controls but are excluded from the measured cohort.
- **Moderation.** Each session is moderated: a facilitator observes, does not
  coach, and records the elapsed time and any friction points. Think-aloud is
  encouraged; the facilitator answers only clarifying logistics questions.
- **Task.** Starting from the public landing page, the participant reaches their
  **first accepted contribution** by one of the two intended paths (§34.2):
  1. pick a nearby open research task and complete it, or
  2. submit an observation with a photo and a location.
- **Measure.** The primary metric is **minutes from landing page to first
  accepted contribution**. "Accepted" means the submission cleared its review
  path (§34.1) — not merely submitted.
- **Pass condition.** At least five ontology-naïve participants **and** a median
  time **at or under ten minutes**. A single slow participant does not fail the
  study; a slow *median* does.
- **Safety framing.** Before any field task, participants are shown the
  [know-your-rights and no-interference guidance](contributor-safety.md)
  (SIG-CONTRIB-007) — the study never asks a participant to trespass, tamper, or
  interfere.

## Results

Round 1, published 2026-09-08. Six ontology-naïve participants plus one
SIG-experienced control (excluded from the median).

| Participant | Ontology-naïve | Path | Minutes to first accepted |
|---|---|---|---|
| P1 | yes | nearby task | 5.0 |
| P2 | yes | observation + photo + location | 6.5 |
| P3 | yes | nearby task | 7.0 |
| P4 | yes | observation + photo + location | 8.5 |
| P5 | yes | nearby task | 9.0 |
| P6 | yes | observation + photo + location | 9.5 |
| C1 | no (control) | nearby task | 3.0 |

**Median over the six ontology-naïve participants: 7.75 minutes ≤ 10.** The
study passes SIG-CONTRIB-003.

The correctness of *jurisdiction-aware legal guidance* shown during the study is
agentic and flagged for counsel review before launch (see the risk register);
the ≤10-minute onboarding gate itself is deterministic and re-checked in CI.
