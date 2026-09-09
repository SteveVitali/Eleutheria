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

## Consent (no personal data retained)

Before a session, each participant is read and agrees to this consent:

> *You are helping test how easy it is to make a first contribution to SIG. We
> record only how many minutes the task takes and where you got stuck — never your
> name, and never anything that identifies you. Nothing you enter is tied to you.
> You may stop at any time and your partial timing is discarded. SIG keeps only an
> aggregate (a count and a median across participants), not your individual time.*

No participant-identifying data is stored anywhere in the repository: participants
are referred to by role-free sequence ids (P1, P2, …) only, and the field
instrumentation is aggregate-only (below).

## Instrumentation — opt-in, aggregate-only field timing (SIG-CONTRIB-003, Part VIII §0.7)

Beyond the moderated sessions, the live L0 form (`/curate/submit/`) carries an
**opt-in** timing field: a newcomer may check a box and enter the minutes since the
landing page. When (and only when) they opt in, the server folds that one number
into `tasks.onboarding.OnboardingTimingAggregate` — a **bucketed histogram** from
which a count and median are computed. **No per-user row, no identity, no handle or
role is stored** — the elapsed time is *never* written to the append-only submission
row (verified by `tests/api/test_curation_onboarding_timing.py`). The aggregate
record (`count` + `median_minutes` only) is exposed at
`GET /v1/curation/onboarding-timing`. This lets the ≤10-minute gate be re-checked
from real usage without retaining who contributed or when.

## Results

**Status: not yet run — gate pending HG-10** (see
[`docs/build/USABILITY_STUDY.md`](../build/USABILITY_STUDY.md), the authoritative
record). The moderated study with ≥5 real ontology-naïve participants has **not**
been conducted: scheduling naïve participants is an agentic act requiring humans
(HG-10). The protocol, the machine-checked ≤10-minute gate, and the aggregate-only
instrumentation are all landed and re-runnable; the results below are **illustrative
harness data** (`tasks/src/tasks/data/usability_study.toml`) that demonstrate the
gate mechanism, **not** a completed study. They are replaced with the real session's
measurements when HG-10 clears.

_Illustrative harness data — six ontology-naïve sequence ids plus one
SIG-experienced control (excluded from the median):_

| Participant | Ontology-naïve | Path | Minutes to first accepted |
|---|---|---|---|
| P1 | yes | nearby task | 5.0 |
| P2 | yes | observation + photo + location | 6.5 |
| P3 | yes | nearby task | 7.0 |
| P4 | yes | observation + photo + location | 8.5 |
| P5 | yes | nearby task | 9.0 |
| P6 | yes | observation + photo + location | 9.5 |
| C1 | no (control) | nearby task | 3.0 |

**Illustrative median over the six sequence ids: 7.75 minutes ≤ 10** — this
demonstrates that the harness computes and gates the median correctly; it is **not**
a real result. The authoritative status is *not yet run — gate pending HG-10*.

The correctness of *jurisdiction-aware legal guidance* shown during the study is
agentic and flagged for counsel review before launch (see the risk register);
the ≤10-minute onboarding gate itself is deterministic and re-checked in CI, so
swapping in the real session's measurements re-checks SIG-CONTRIB-003 automatically.
