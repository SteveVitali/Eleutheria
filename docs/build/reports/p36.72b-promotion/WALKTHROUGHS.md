<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P36.72b — core-surfaces walkthrough record (agent-verified)

**Row:** 416 / ACC-PLACES b-half · **Branch:**
`r11/P36.72b-core-surfaces-walkthroughs-and-promotion` · **Harness:**
devin-desktop/swe-2-high/subagent · **Recorded:** 2026-11-05 (`date -u`)

**Label — always carried:** **`agent-verified`** (P4 honesty — K13 §8's
contract: these are *agent walkthroughs at acceptance*, never user research;
the operator's own cold walk is the GATE-G6 sitting's, and the
promoted-release cold walk at 390 px + 1440 px is the verify leg's —
`D-P36.71-1` leg 5).

## What this record is

The K13 §8 capstone journeys this row owns — **A1 A2 A3 A4 O1 O3 O4 J1** —
walked over the fixture corpus by the landed e2e walkthrough spec
(`web/tests/e2e/acceptance-walkthroughs.spec.ts`, P36.72a) and re-run fresh
for this record. Each journey's pass contract is quoted from K13 §8; the
walked path and measured verdict are this run's. Every fact on the walked
surfaces carries a source, an as-of and a release id — the sweep asserts it,
the record reports it.

| field | value |
|---|---|
| corpus | the committed web fixtures (`SIG_DATA_SOURCE=fixtures`, `SIG_BUILD_INTERNAL=1` build so the internal surfaces walk too) |
| runner | `npx playwright test acceptance-walkthroughs` (chromium project, against the built `dist/` under `astro preview`) |
| result | **9/9 passed** — 2026-11-05, ~6 s over the built site |
| verdict | **PASS — agent-verified** over the fixture corpus |

## Journeys

| id | journey (K13 §8 pass contract) | path walked | verdict |
|---|---|---|---|
| **A1** | type "Oklahoma City", reach its place dossier in ≤ 3 clicks; no-JS GET works | `/` hero typeahead → "Oklahoma City" option → `/dossier/usa/ok/oklahoma-city-4064000/`; the no-JS path: `GET /search/?q=…` + `/dossier/a-z/o/` index link | PASS — agent-verified |
| **A2** | what is deployed, who runs and approved it, next decision — sourced values or typed absences | the OKC dossier: At-a-glance sourced figures → `dsrc-top-sources` names the contributing sources → Next decisions heading present (items or a typed absence, never a guessed date) | PASS — agent-verified |
| **A3** | print for a council member — brief + locator + as-of/release id/permalink/licence on the page | `/dossier/usa/ok/` → `print/` link → `council-brief`, `brief-locator`, `print-permalink`, `print-terms`, `print-runhead` all render | PASS — agent-verified |
| **A4** | know what to bring; act on what we don't know — documents resolve; the draft is downloadable; SIG sends nothing | `/dossier/usa/ok/print/` `brief-documents*` blocks → gap link → `/task/T-…/` closing condition + request draft (`draft-download` resolves 200) + `draft-never-sent` marker | PASS — agent-verified |
| **O1** | who runs what in my county — named agencies, technology classes and counts, each sourced or a typed absence | `/dossier/usa/tx/harris-county-48201/` rollup + `dsrc-top-sources`; `…/sites/` list renders rows (`sites-count`, `site-row` > 0) | PASS — agent-verified |
| **O3** | a local list without the map — no-JS list with CSV, licence and attribution per compartment | `/dossier/usa/ok/oklahoma-city-4064000/sites/` rows + `sites-licence-line` + compartment name + `sites-csv` href answers 200; **zero `<script>` inside `main`** | PASS — agent-verified |
| **O4** | act on a gap — plain-language task, closing condition, request template, where to send results | absence-chip link from the dossier → `/task/T-…/` `task-page` + `task-closing` + `task-how-to-act` (the operator-named channel block) | PASS — agent-verified |
| **J1** | defend a headline figure — unit/denominator/as-of/release id; breakdown + recomputing rows in ≤ 2 actions | `/coverage-metrics/` first `<Figure>` → `data-figure-link="source"` artifact answers 200; `#breakdown` anchor resolves in-page; `page-stamp` carries the as-of + release | PASS — agent-verified |

## Honest scope

- **Fixture corpus, not the promoted release.** These walks measure the
  committed fixture build. The promoted-release cold walk (390 px +
  1440 px, fresh context) is a verify leg of the post-promotion packet —
  `D-P36.71-1` leg 5 covers A1/J2; the remaining journeys' promoted-release
  re-walk rides the same sitting's verify pass.
- **J2/J3/J4/J5/O2 are not this row's.** J2 is P36.71's; J3/J5 need
  surfaces that land later in W3 (disagreements, changes); J4 needs
  TX-13b/ACT-24 under the promoted release; O2 needs the watch feeds'
  promoted state. Recorded, never claimed (SIG-ENG-042).
- **Never user research.** "Agent-verified" is the whole label — no
  participant claim, no usability finding, no proxy for the operator's own
  walkthrough.
