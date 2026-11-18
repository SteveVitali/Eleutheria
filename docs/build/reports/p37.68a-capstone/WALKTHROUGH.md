<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.68a — operator walkthrough packet: advocate journeys A1–A4

**Status:** REQUESTED — never simulated. This packet is the agent-prepared
input to the **operator's own walkthrough** (OP-22; recorded
`operator walkthrough (maintainer, not independent)` — TS-22). Nothing on
this page is a result; the operator's walk is the only walkthrough that
counts, and it lands in the operator's own record.

**When:** the live window is `on the promoted P37.65 release; 390 px + 1440
px` (the plan cell, verbatim). The promoted release does not exist yet —
`D-P37.65b-1` (the promote leg) is QUEUED behind the operator's HG-11
readout. This packet is staged so the walk can start the moment the
release promotes.

**Journeys in this packet:** A1–A4 (the advocate family — row a of the
four-way CAP-01 split). J1–J5 ride P37.68b's packet; O1–O4 ride
P37.68c's; the U-003.1…11 per-ask checks, budgets, axe and ROUTES.csv
re-check ride P37.68d's.

**Labels:** every agent journey result is recorded `agent-verified` — it
is a machine walkthrough, never user research and never "user-tested"
(P4, SIG-UI-077/078).

## Setup (operator)

1. The promoted release origin: `<promoted-origin>` — the URL P37.65b's
   promote leg publishes (fill in at walk time; never guessed).
2. Viewports: **1440 px** and **390 px** browser widths (any tool —
   responsive-design mode is fine).
3. JavaScript **on** for the primary legs; **off** for the legs marked
   "no-JS allowed" below (browser site settings or dev-tools toggle).
4. A fresh, cold start at `/` for each journey — walked like a reader,
   not an operator who knows the routes.
5. Timebox per K13 §8: A1 ~1 min · A2 +3 min · A3 +2 min · A4 +3 min.

## A1 — type "Oklahoma City", reach its place dossier (≤ 3 clicks)

- **JS on (1440 + 390 px):** from `/`, type `okla` into the hero search →
  the first suggestion names Oklahoma City → select it → land on the
  place dossier (`/dossier/…`, heading names Oklahoma City). Repeat from
  the header search on a dossier page — the same place must come first
  (UXR-24).
- **JS off (1440 + 390 px):** the hero search is a plain `GET` form to
  `/search/` (the no-JS contract); the A–Z directory
  (`/dossier/a-z/o/`) links the Oklahoma City dossier — the named no-JS
  place-lookup equivalent.
- **Pass (K13 §8):** named place first, homonyms carry their parents;
  the same result from header, home, index and map; the no-JS GET works.

## A2 — what is deployed, who runs and approved it, next decision (+3 min)

- **All four cells:** from the Oklahoma City dossier — *At a glance*
  answers with sourced values ("records" wording, never a census claim);
  *Where this comes from* names the contributing sources and the
  single-source share; *Next decisions* shows an item or a typed absence
  — never a guessed date.
- **Pass (K13 §8):** each answer a sourced value or a typed absence
  naming what closes it; "records" wording; single-source share visible.

## A3 — print for a council member (+2 min)

- **All four cells:** from the dossier (or its parent jurisdiction
  dossier — the Print action lives where the brief is offered) → the
  print route serves a page-1 council brief with a locator; as-of,
  release id, permalink and licence on the page; greyscale-safe.
- **Pass (K13 §8):** page 1 council brief with locator; map leads page 2;
  as-of, release id, permalink, licence on every page.

## A4 — know what to bring (+3 min)

- **All four cells:** the print brief's *documents to bring* block
  resolves (list or typed absence); the dossier's *What we don't know*
  section reaches the research queue → a records-request task → the
  request draft downloads (`.draft.txt`).
- **Pass (K13 §8):** document list resolves; the draft is downloadable;
  "SIG sends nothing" is stated on the task.

## Record (operator fills — never agent-written)

| journey | 1440 JS | 1440 no-JS | 390 JS | 390 no-JS | time | notes |
|---|---|---|---|---|---|---|
| A1 | | | | | | |
| A2 | | | | | | |
| A3 | | | | | | |
| A4 | | | | | | |

Verdict line (operator's own words): ______________________________________

Recorded as: `operator walkthrough (maintainer, not independent)` — TS-22.
