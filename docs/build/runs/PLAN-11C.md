# PLAN-11C — Contracts for 11C rows + the K13 UX requirement families

<!-- BM-RUN-01: Harness = the exact PR-trailer string. Started/Closed = UTC
     `date -u` at branch start / when the last acceptance criterion is
     satisfied. The OM gap table is the ticket's operating checklist.
     This run ledger is shared by the twelve contexts C1–C12 of row 340;
     each context appends its own section and its own Started/Closed. C12
     closes the ledger — no `Closed:` header line before then. -->

Harness: devin-desktop/swe-2-high/subagent
Started: 2026-10-24T22:55Z (`date -u` at context start; branch
`r11/PLAN-11C-contracts-for-11c-and-k13-families` at `da2cea19` on
`r11/P35.62-round10-production-candidate`)
PR: (to be opened at the C1 push; base `r11/P35.62-round10-production-candidate`)

## Spec / Base / Branch / Config

- Spec: `docs/tickets/340_PLAN-11C__contracts-for-11c-and-k13-families.md`
  (manifest row 340 — Round 11, `decompose-spec mode=extend`, twelve
  contexts C1–C12 over rows 344–420; each context ≤ 8 rows).
- Base: `r11/P35.62-round10-production-candidate` @ `da2cea19`
  (orchestrator boundary-confirm commit)
- Branch: `r11/PLAN-11C-contracts-for-11c-and-k13-families` (shared;
  one PR for the whole row). PR base = the base branch (PR-1).
- Config: `decompose-spec mode=extend`; `live_verification=false` — this
  row writes contracts and spec text; it executes no 11C row, mutates no
  production and ticks no gate.
- Dispatch note: the twelve contexts are executed in order by the
  orchestrator's dispatched sub-agent sessions, each treating its batch
  as a fresh scope. Each context's section below records its own
  `Started:`/`Closed:` and token figures.
- Requirement ids (from the contract): **written here** — the K13 UX
  families (plan §6.2, spec §56.8); **owner confirmed** — SIG-OPS-007 →
  P35.2 (the §56 `Owner:` line as written); **cited** — SIG-ENG-003
  (spec changes through `spec_src` + `BUILD.sh`), SIG-ENG-041 (MISSING
  rows and routing; owner SEED-15).

## Deferrals read

Read `docs/tickets/DEFERRALS.md` first (AGENTS.md gotcha 8). Rows naming
surfaces this plan row touches:

- `D-R11-OSMUID-1` (F) — the OSM `user`/`uid` capture-side fix; P37.1
  (row 344) is the row that captures OSM data going forward — its
  contract names the placement.
- `D-R11-LATER-04` (P) — LATER-04 outreach/records-request/recruiting
  register; every connector/acquisition contract lists the ADR-171
  Stage-0 set as owed, never satisfied.
- `D-SOURCES.7-1` (OPEN), `D-SOURCES.8-1` (PARTIAL), `D-SOURCES.9-1`
  (OPEN), `D-SOURCES.9-4` (OPEN) — the HG-03 rights rows P36.2 (row
  350) carries; the operator executes the flips (OP-26).
- `D-P32.3-1` (OPEN) — the `partner-name-audit` identity-disposition
  row P35.21 (row 347) serves.
- Rows carried from PLAN-11B's C13 hand-offs (the IND-TRIBAL members
  `AP-T2-201`/`AP-T2-210` if the S8 screened lane's wave lands in 11C,
  and any `D-R11-OSMUID-1` placement) — dispositioned at C12.
- No OPEN/PARTIAL row is closed by this planning row; no row's lead
  token changes, so no obligation-event transitions are owed.

## Contexts

### C1 — 2026-10-24 (rows 344–346 + the K13 UX requirement families)

Started: 2026-10-24T22:55Z · Closed: (open while C1 works)
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverables 1, 2-in-part, 3):

- Append the K13 UX set (UXR-01…38 new requirements; UXR-A01…A13
  adoption rows promoting the K-series draft families to final ids) to
  `spec_src`, de-duplicated against existing ids and the landed
  SIG-TRANSP-001…043 / SIG-CONF-001/005/011 ids; register new prefixes
  in §0.3; rebuild via `BUILD.sh`; `check_spec_src.py` baselines +
  Appendix G row; committed draft→final map
  (`docs/build/reports/plan-11c/K13_id_map.csv`); one MISSING
  coverage-matrix row + one `coverage-assessment/1` event per new id,
  routed to an unlanded chain row.
- Full contracts for rows 344 (P37.1 OSM camera-site origin), 345
  (P37.2 Wave C national ALPR layer — ING-GO-C verbatim, tier-bump
  never pre-authorised) and 346 (P35.2 alerts/availability —
  re-confirms SIG-OPS-006/007's owner lines).

Files written: (filled at C1 close)
Verification: (filled at C1 close)
Dispositions: (filled at C1 close)

### C2 — (rows 347–354)

Started: — · Closed: —

Scope: rights/connector block — P35.21 (partner-name audit), P35.23
(regression corpus), P36.1b (crawler/robots text), P36.2 (rights batch
incl. the T3 out-of-rule re-decision fold), P36.76/77/78 (Axon,
DocumentCloud, Sourcewell/OMNIA connectors — deliverable 7a
outreach-owed applies), P36.13 (rate limits, OM-20).

### C3 — (rows 355–362)

Scope: L4 marker (P36.14) + design system / chrome / component kits
(P36.16…P36.22); the K13 families must already exist.

### C4 — (rows 363–370)

Scope: component kit B, copy lints, brand, print v2, figure kits,
identifier module, graph export (P36.23…P36.30).

### C5 — (rows 371–378)

Scope: P36.79 held-out relevance set (OM-20, B-28 b), search index and
engine (P36.31/32), basemap host (P36.33, OM-20), dossier index,
redirects, no-JS map, map app (P36.34…P36.37).

### C6 — (rows 379–386)

Scope: API search roll (P36.38 — never pre-authorised), no-JS search,
typeahead, entity pages A + Organizations (P36.41/42a/42b), Flock
share-list claims (P36.75, OM-20), status scheduler (P36.43, OM-20).

### C7 — (rows 387–394)

Scope: release cadence scheduler (P36.44, OM-20), publish matrix,
run-log backfill (P36.46, OM-20), source pages A/B, source index,
issues log, downloads center, evidence anchors.

### C8 — (rows 395–402)

Scope: dossier sources explorer, downloads, template v2, scoped
search, task export (P36.52…P36.59).

### C9 — (rows 403–410)

Scope: watch pages, evidence hub, queue pages, request drafts,
home/About, onboarding, site snapshots a/b (P36.60…P36.66b — already
T3 splits under TX-13b; contracts, never re-splits).

### C10 — (rows 411–418)

Scope: changes page, extracts mirror writes (P36.68, OM-20), source
page B, search acceptance (P36.71), core-surfaces acceptance pair
P36.72a/b (b carries HG-11 Class S — never pre-authorised),
second-release acceptance (P36.70 — Class R conditional), PLAN-11D
(plan-kind contract modelled on row 340's).

### C11 — (rows 419–420)

Scope: P36.73 capstone (live-read sweep + GATE-G6 packet) and the
GATE-G6 gate marker (guard sentence; collects ING-GO-D, the Wave-D
flip list, the 11D OM-20 list, the standing-go renewal); requirement
index regeneration.

### C12 — (Phase-4 sizing review)

Scope: fresh-context review of all 77 contracts — fragmented
decisions, overflow risk (Load ≤ ~150k by the higher of ÷3/÷4),
orphan seams, coverage (every §56 id with an 11C owner + every new
K13-family id maps to exactly one row), ordering (no forward
`depends`), over-factoring; the 11C re-split decision with counts
(§8.1: 76 engineering rows / 66.5 runs at S6c); the watch/flag set
(P36.64 watch-list row, P36.2 fold); the draft 11C OM-20 list for
GATE-G5; the 11C outreach-owed list; the carried placements.
