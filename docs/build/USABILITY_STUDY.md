# Contributor onboarding usability study — build record (P21.7)

- **Spec:** §34.2, §36.7 (SIG-CONTRIB-003; the P16.1 AC7 usability ids).
- **Protocol (authoritative):** [`docs/governance/contributor-onboarding-usability-study.md`](../governance/contributor-onboarding-usability-study.md).
- **Gate:** HG-10 (≥5 naïve participants scheduled). **Unticked** ⇒ protocol +
  instrumentation land; this results section states *not yet run*.

## Protocol (landed, runnable)

The moderated protocol is finalised and re-runnable: recruit **≥5 ontology-naïve
participants** (roles only — no names in the repo), moderate each session (observe,
do not coach), and measure **minutes from the landing page to the first accepted
contribution** by one of the two §34.2 paths (nearby task, or observation + photo +
location). **Pass condition:** ≥5 naïve participants **and** a median **≤ 10
minutes** (SIG-CONTRIB-003, the P16.1 AC7 success criterion). Consent text retaining
**no personal data** is in the protocol doc. The machine-checked gate lives in
`tasks.onboarding.UsabilityStudy.meets_requirements` over
`tasks/src/tasks/data/usability_study.toml`; swapping in the real session's rows
re-checks the gate in CI (`tests/tasks/test_tasks_onboarding.py`).

## Instrumentation (landed) — opt-in, aggregate-only timing

The live L0 form (`/curate/submit/`) carries an **opt-in** timing field. On opt-in,
the server folds one elapsed-minutes measurement into
`tasks.onboarding.OnboardingTimingAggregate` — a bucketed histogram yielding a
**count + median only**. Privacy properties, each test-pinned:

- **No per-user rows.** The elapsed time is never written to the append-only
  submission row (`tests/api/test_curation_onboarding_timing.py::test_elapsed_time_never_written_to_the_submission_row`).
- **No identity / name / role** is stored — the aggregate holds only a
  `bucket → count` histogram (`tests/tasks/test_tasks_onboarding_timing.py`).
- **Aggregate-only read.** `GET /v1/curation/onboarding-timing` returns just
  `{count, median_minutes}` (Part VIII §0.7).

## Success criterion (documented — P16.1 AC7)

Median landing → first-accepted-contribution time **≤ 10 minutes** across **≥ 5**
ontology-naïve participants. Both the moderated-study gate and the field-timing
aggregate re-check against this same threshold (`MEDIAN_TARGET_MINUTES = 10.0`).

## Results

**Not yet run — gate pending HG-10.**

The moderated study with real ontology-naïve participants has not been conducted:
scheduling naïve humans is an agentic act (HG-10) not performed this run. No
aggregate field timing has been collected against a live deployment either, so
there is **no `n` and no median** to report. The illustrative rows in
`usability_study.toml` demonstrate the gate mechanism only and are **not** a result
(see the protocol doc's Results section). When HG-10 clears:

1. run the moderated protocol, record the per-session minutes as role-only rows in
   `usability_study.toml`, and let CI re-check the ≤10-minute median;
2. record the real aggregate (`count`, `median_minutes`) from the opt-in field
   instrumentation here;
3. record any **onboarding changes made from the findings** in this section.

No participant-identifying data is stored anywhere in the repository.
