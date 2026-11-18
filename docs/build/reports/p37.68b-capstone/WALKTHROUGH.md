<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# P37.68b — operator walkthrough packet: journalist journeys J1–J5

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

**Journeys in this packet:** J1–J5 (the journalist family — row b of the
four-way CAP-01 split). A1–A4 ride P37.68a's packet; O1–O4 ride
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
5. Timebox per K13 §8: J1 ~5 min · J2 ~10 min · J3 ~3 min · J4 ~3 min ·
   J5 ~5 min.

## J1 — defend a headline figure (5 min)

- **All four cells:** from a place dossier (the A–Z directory's Texas row
  is the fixture corpus's example; any dossier will do) — open a figure:
  its caption carries the unit and denominator ("…of N published
  records"), the "**Not a census**" wording, and the release id; its
  evidence row links definition / source / provenance (and honestly marks
  the kinds this build cannot show, e.g. "record list — no release is
  bound"); the breakdown anchor resolves on the page. Then *Downloads* →
  a rows download.
- **Pass (K13 §8):** unit, denominator, "not a census", as-of, release
  id, Provisional where due; rows in ≤ 3 clicks; ≤ 2 actions to evidence.

## J2 — "Who supplies ALPRs to Texas agencies, and who can access the data?" (10 min)

- **JS on (1440 + 390 px):** type `tex` into the header/home typeahead →
  Texas comes first → the Texas dossier → *See connections →* opens the
  graph view scoped to the place; pick the **Supply** overview, then the
  **Access** overview — nodes named, edges dated or typed "undated",
  each naming its source; historical edges marked, never present-tense.
- **JS off (1440 + 390 px):** the GET search form contract; the A–Z
  directory reaches the dossier; the same facts live on the static
  `/graphs/` overviews — the access drill-down (e.g.
  `/graphs/access/usa/tx/`) lists every edge with date-or-"undated",
  state and source — and the entity pages the edge rows link.
- **Pass (K13 §8):** every node named, every edge dated or "undated"
  with currency and source, evidence ≤ 2 actions, historical never
  present-tense; same facts JS-off via `/graphs/` and entity pages.

## J3 — is this figure disputed? (3 min)

- **All four cells:** a dossier carrying the **≠** contested marker →
  one click on "All disagreements for <place> →" → the place page shows
  every kind section (recorded contradictions, within-source coordinate
  conflicts, declared-vs-located, co-located) — records or typed
  absences. From `/disagreements/` the recorded contradiction shows
  **both sides** — each with its source, observed/recorded dates and a
  claim-page link.
- **Pass (K13 §8):** the ≠ marker in raspberry with both sides one
  click away; typed kinds kept apart (a coordinate conflict is never
  smoothed into a "disagreement").

## J4 — cite it durably (3 min)

- **All four cells:** *Cite* on a dossier → the block records the as-of
  world/belief pair and the ruleset; the permalink carries
  `?as_of_world=…&as_of_belief=…&ruleset=…`. Where the release binds no
  immutable snapshot the interim sentence says "an immutable citable
  copy is not yet published" — never the "reproducible" phrase over a
  non-pinned URL. The legacy `?as_of_world=` URL resolves or answers
  404/409.
- **Pass (K13 §8):** the pinned `/s/<pub>/…` URL returns identical bytes
  after the next release — **the durable half rides ACT-24 (HG-11)** and
  cannot pass before it (K13 §7.4); the legacy selector URL resolves or
  answers 404/409.

## J5 — what changed since the last release? (5 min)

- **All four cells:** `/changes/` → the release pair with world/belief
  dates → "**The world changed**" (what sources report changed on their
  own side) and "**SIG's records changed**" (what SIG's records now say
  differently — SIG learning, re-resolution or re-minting, never
  automatically a world change) kept apart → the feed directory → per
  place and per source `.atom` feeds + the OPML bundle (feeds exist even
  at zero entries).
- **Pass (K13 §8):** a changes page and feeds per place and source;
  "SIG learned" vs "world changed" separated. The **real ≥ 2-release
  diff** (CF-13) needs the promoted release *and* its activated
  predecessor — the fixture pair is synthetic.

## Record (operator fills — never agent-written)

| journey | 1440 JS | 1440 no-JS | 390 JS | 390 no-JS | time | notes |
|---|---|---|---|---|---|---|
| J1 | | | | | | |
| J2 | | | | | | |
| J3 | | | | | | |
| J4 | | | | | | |
| J5 | | | | | | |

Verdict line (operator's own words): ______________________________________

Recorded as: `operator walkthrough (maintainer, not independent)` — TS-22.
