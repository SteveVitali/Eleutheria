<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P37.65b — journalist / researcher / skeptic journey re-runs (`agent-verified`)

The TX-16 re-run the plan cell names — `re-run of the journalist /
researcher / skeptic journeys (agent walkthrough, not user research,
P4/P5)` (J3 §12, verbatim). Every journey below is a **labelled agent
walkthrough** over the emitted fixture build, re-run fresh on
**2026-11-18** — recorded `agent-verified`, never user research (K13 P4;
the operator's own walkthrough rides the CAP-01 capstone on the promoted
release).

The corpus: `SIG_BUILD_INTERNAL=1 npm run build` → **528 pages / 530
classified routes** (`page-types.json`, `dataSource: "fixtures"`), served
by `astro preview`; Playwright `chromium` project.

## Persona → journey map (the re-run set, each leg's landed spec)

The TX-16 catalog cell names `J1;J4`; the b-half re-runs every persona
lane the published surface walks, mapped to the specs that own them:

| persona | journeys | spec (landed owner) |
|---|---|---|
| **journalist** | J1 defend a headline figure · J2 the Texas supply/access walk · J-2 edge→evidence ≤2 actions · VJ-3 access figure → entity → explorer → cite · VJ-5 source breakdown sums → show-on-map · J5 what changed since the last release | `transparency-acceptance.spec.ts` (P37.65a) · `acceptance-explore-journeys.spec.ts` (P37.64) · `changes.spec.ts` (P37.40) |
| **researcher** | J4 cite it durably (deterministic half) · J-5 the downloads recompute the page | `transparency-acceptance.spec.ts` (P37.65a) · `acceptance-explore-journeys.spec.ts` (P37.64) |
| **skeptic** | J3 is this figure disputed (`/disagreements/` three kinds + dossier hand-off) · how sure is SIG (`/quality/` — CONF-12) · methodology / coverage-metrics / data-freshness · the public corrections log + dispute path · open questions (`/research-queue/`) | `disagreements.spec.ts` (P37.38) · `quality.spec.ts` (P37.45) · `corrections-methodology.spec.ts` · `research-queue.spec.ts` (P36.61/63) |

J4's **durable-pin half** — the pinned `/s/<pub>/` URL returning identical
bytes after the next release — is a property of the staged candidate, not
the fixture dist; it rides `D-P37.65a-1`'s `live-crawl` leg and is recorded
here as owed, never claimed (the same split P37.65a's packet records).

## Measured results (fresh runs, 2026-11-18 — never restated from prior runs)

| spec | command | result |
|---|---|---|
| `tests/e2e/transparency-acceptance.spec.ts` | `npx playwright test … --project=chromium` | **4/4 passed** (1.9 s) — J1 figure→recomputing bytes ≤2 actions + pointer/breakdown non-vacuous; J4 deterministic half: exactly one cite mode per cite-carrying route + the "reproducible" wording never beside an unpinned copy |
| `tests/e2e/acceptance-explore-journeys.spec.ts` | `npx playwright test … --project=chromium` | **15/15 passed** (3.6 s) — J-1…J-6 + VJ-1…VJ-6 + the K13 §8 capstone legs incl. J-1 journalist, J-5 researcher, VJ-3/VJ-5 journalist; axe WCAG 2.2 AA in interaction states |
| `tests/e2e/changes.spec.ts` | `npx playwright test … --project=chromium` | **11/11 passed** — `/changes/` hub + per-place/per-source Atom feeds + "SIG learned" vs "world changed" (J5) |
| `tests/e2e/disagreements.spec.ts` | `npx playwright test … --project=chromium` | **8/8 passed** — the ≠ hub, a place's three typed kinds kept apart, the dossier→place hand-off (J3, the skeptic's dispute walk) |
| `tests/e2e/quality.spec.ts` | `npx playwright test … --project=chromium` | **4/4 passed** — every registered check with its state (failing + ratchet shown), "no human check performed" verbatim, the who-checked-what basis row `none`, the duplicates anchor + probe lane (CONF-12 / SIG-CONF-011) |
| `tests/e2e/corrections-methodology.spec.ts` | `npx playwright test … --project=chromium` | **532/532 passed** (19.7 s) — research queue, the public corrections log, the dispute/correction path ("Not operating yet."), methodology + coverage-metrics + the mechanical-evaluation disclosure |
| `tests/e2e/research-queue.spec.ts` | `npx playwright test … --project=chromium` | **25/25 passed** (1.3 s) — open questions, task cards, records-request drafts, honest absences |

**Total: 599/599 passed** — zero failures, zero skips claimed as passes;
the whole suite ran end-to-end on this dispatch's build.

## Disposition notes

- Every pass above is **fixture-layer**: the emitted fixture corpus, not
  the staged release candidate and not the promoted site (SIG-ENG-042 —
  the layer reached is the layer recorded). The promoted-release walk is
  the post-promotion verify legs (`D-P37.63-1`, `D-P37.64-1`) and the
  CAP-01 capstone on the promoted release.
- The specs are the landed journey batteries — this row re-ran them and
  recorded the measure; no journey was rewritten to fit this ticket.
