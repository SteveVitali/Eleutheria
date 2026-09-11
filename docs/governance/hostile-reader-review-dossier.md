# Hostile-reader review — local dossier template

*Adopts docs/2_canonical_design_spec.md §41 (SIG-UI-042). This review is the recorded,
release-blocking hostile-reader review for the local-dossier template version. Its
**executable** half — the findings, their disposition, and the release gate — is data
in `web/src/lib/corrections-methodology-fixture.ts` (`HOSTILE_READER_REVIEW`) and is
enforced by `web/src/lib/editorial.ts::assertReviewReleasable` at build and in
`web/tests/unit/editorial.test.ts`. The review is rendered publicly at
`/editorial-standards/`.*

Each dossier template version receives a hostile-reader review before release
(SIG-UI-042): **two reviewers independently read a real rendered dossier adopting the
stance of the documented organization's counsel**, log every sentence they would
challenge, and sign off. The review, its findings, and their disposition are committed
alongside the template version, and **release is blocked until every finding is
dispositioned**.

The standard being approximated is that a police chief or vendor counsel reading their
own dossier should find it accurate, neutral, and hard to attack — the property that
makes the work usable as evidence.

## This review

| Field | Value |
|---|---|
| Template version | `resolver-ruleset-2026.07` (the version the dossier is pinned to) |
| Dossier reviewed | `/dossier/oklahoma-city/` (a real render, not a mock) |
| Reviewers | Reviewer A (counsel stance); Reviewer B (counsel stance) — two independent |
| Review date | 2026-08-19 |
| Release status | **Releasable** — every finding dispositioned |

## Findings and disposition

| id | Finding (as the documented org's counsel) | Register rule | Disposition | Resolution |
|---|---|---|---|---|
| hr-1 | "admitted to only 38 cameras" characterizes the portal report as a concession | 1 (report, don't characterize) | accepted, revised | Rewritten to "the portal reported 38 cameras on 2026-07-01" |
| hr-2 | The wrongful-stop lawsuit reads as if the misread were established fact | 2 (never state an allegation as fact) | accepted, revised | Rewritten to attribute the allegation to the complaint and note it is unadjudicated |
| hr-3 | The 31-device map figure reads as a total, not a lower bound | 5 (name uncertainty with the number) | accepted, annotated | Annotated as a lower bound in the same sentence as the number |
| hr-4 | Counsel objects to publishing the accountability event at all | — | rejected, with reason | Retained: the event is accurate and W3-sourced; a response affordance is offered instead (SIG-GOV-010) |

No finding is left open, so the template version is releasable. A future template
version requires its own review; a version whose review has an undispositioned finding
fails the build (`assertReviewReleasable`) and cannot be released.
