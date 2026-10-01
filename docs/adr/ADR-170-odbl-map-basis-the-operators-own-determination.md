# ADR-170: ODbL map basis — the operator's own determination (no counsel, no document); the per-compartment map kept

- **Status:** Accepted
- **Phase:** Round 11 / Stage B, T1 (seed; `NEXT_PHASE_PLAN.md` §7 row 170)
- **Ticket:** SEED-11
  (Stage-B unit SEED-11c; run ledger `docs/build/runs/SEED-11c.md`)
- **Date:** 2026-10-01 — decided by the operator at GATE-P: A-4 (member Q-E2-14) at 2026-10-01T04:03:25Z (log round 3);
  the C-3 sentence at 2026-10-01T04:54:19Z (log round 19)
- **Written:** 2026-10-01T07:42:45Z (`date -u`; Claude Code, Opus 5.5, Stage-B sub-agent)
- **Base:** `r11/seed` tip `f66b2450`
- **Decision owner:** the operator (GATE-P). This ADR records the decision.
- **Relation to landed ADRs:** none named by §7 for this ADR. ADR-106's basis statement is what this ADR re-records; the
  `Qualified by` status line on ADR-086/ADR-106 is §7's assignment to ADR-167 (appended by SEED-11d). ADR-106's
  Decisions 1–5 (as amended by ADR-118, which retired `/map/points.json`) are unchanged.
- **Related:** ADR-011 (the ODbL posture, Strategy B), ADR-048, ADR-096 §1 (superseded by ADR-106), ADR-106, ADR-118,
  ADR-156 (public map v2 with a self-hosted OSM basemap; provisional, written by P35.52), ADR-167 (counsel basis and
  label text), ADR-182 (WV-07); SIG-EXPORT-005/006, SIG-LIC-004a/005/006/009, SIG-GEO-013; RISK-P0-01; DEFERRALS
  D-P30.3-COUNSEL, D-LEGAL.1-1; plan rows P34.21a/b (attribution defect + publish-time attribution gate + re-export
  and republish #2), P34.16 (public-repo honesty corrections). `PD` =
  `docs/build/planning/2026-09-30-next-phase/`: `PD/NEXT_PHASE_PLAN.md` §4.2 A-4, §4.5 C-3, §5.10, §7;
  `PD/design/E2-governance-options.md` E2-13 and E2-05; `PD/reviews/S4-truth-safety.md` TS-09;
  `PD/research/F3-backlog.md` §5.4 (NEW-8); `PD/data/decision_catalog.csv` row Q-E2-14.

## Context

SIG-EXPORT-005, SIG-LIC-004a and SIG-LIC-006 require OpenStreetMap-derived data to ship as its own ODbL compartment so
that share-alike never reaches the whole export. ADR-106 (P30.3, 2026-09-24) made the share-alike compartments public as
**separate, attributed** downloads (ODbL `osm_physical` beside the CC-BY `sig_graph`), kept mixed-licence artifacts
private, and treated the public site as an ODbL **Produced Work** (4.4(b)) drawing on every layer, with
"© OpenStreetMap contributors (ODbL)" on the map. ADR-118 then retired the combined `/map/points.json`: tile archives are
per compartment.

ADR-106 rested on the operator's answer of 2026-09-24, *"counsel says it's okay and we can publish it all together."*,
which it described as an **operator-reported** counsel clearance with no dated written opinion on file
(`D-P30.3-COUNSEL`). The Stage-P review (E1-13/E2-13) found the map still one produced work drawing every compartment on
that basis alone. The operator has since said that "counsel" so far was the operator and there is no counsel (U-013,
2026-09-30T21:58:23Z), and adopted at GATE-P the C-3 sentence that the 2026-09-16 and 09-24 "counsel" determinations were
their own (recorded by ADR-167). S4's TS-09 ruled that neither "operator-reported counsel" nor "clearance" may survive as
a description of this basis. F3 NEW-8 lists ADR-011 and ADR-106 among the thirteen ADRs whose counsel-conditioned revisit
clauses cannot fire while there is no counsel.

The operator was asked A-4 — adopt the disclosed single-maintainer, no-counsel posture, including "DB-right / ODbL bases
as operator determinations with guardrails" — whose member Q-E2-14 read: *ODbL residual: one map over all compartments
on an operator-reported clearance (ADR-106)*, options a) accept by ADR · b) counsel (ruled out) · c) keep the
per-compartment map; new ADR records the clearance as operator-reported with no document.

## Decision

1. **The per-compartment map is kept** (A-4, *"Adopt disclosed posture (Recommended)"*, 2026-10-01T04:03:25Z; Q-E2-14
   **c**, as recommended). OSM-derived data stays in its own ODbL compartment and download, never merged into the CC-BY
   graph or any other compartment; tiles stay one archive per compartment; mixed-licence files stay restricted build
   inputs; the public site is the produced work and carries the OSM attribution in every rendering context
   (SIG-GEO-013). ADR-106's mechanism is unchanged.
2. **The basis is re-recorded as the operator's own determination — no counsel, no document.** ADR-106's "operator-
   reported counsel clearance" is, on the operator's C-3 words, the operator's own 2026-09-24 determination. From this
   ADR on, no SIG record, page or export describes the map's ODbL basis as counsel-cleared, counsel-approved or a
   "clearance"; it is described as **the operator's own determination (no counsel)**, with the label text ADR-167 fixes
   once the operator confirms it verbatim in a copy batch.
3. **What SIG may say:** "the map combines separately licensed layers; OpenStreetMap data stays under ODbL and is offered
   as its own download". What SIG may not say: that any lawyer reviewed or cleared it.
4. **The counsel packet is not sent this round** (the A-4 package's recommendation records "the counsel packet is not
   sent" — decision catalog row Q-E2-13, a fellow A-4 member; SIG-LIC-009's counsel clause is waived by WV-07, ADR-182). The ODbL produced-work and 4.4(b) questions wait for
   LATER-05 (optional; trigger: the operator obtains counsel). SIG-LIC-009's risk-register clause stands, and
   RISK-P0-01 stays in the register.
5. **Attribution is enforced at publish.** E2-13 option c's third leg — a check that the OSM compartment's downloads
   carry the share-alike notice (E2-12) — rides the publish-time attribution gate of P34.21a/b; each bundle's
   `ATTRIBUTION.txt` carries the ODbL notice for OSM-derived content (`PD/design/J3-transparency-design.md` §6.7). The
   mapping of that leg to P34.21a/b is the agent's reading of the plan, labelled as such.
6. **The basemap.** The self-hosted OpenStreetMap basemap adopted for the public map v2 (A-3/K1; ADR-156, written by
   P35.52) is ODbL-derived; it stays its own archive, never merged with SIG data, and the same produced-work reading and
   attribution duty apply. Its design is ADR-156's, not this ADR's.
7. **Record hygiene, not done here.** `D-P30.3-COUNSEL` reads `DONE 2026-09-24 — CLOSED BY OPERATOR ATTESTATION, no
   written opinion filed` in the DEFERRALS register's main table and `OPEN` in a later summary table of the same file;
   reconciling that, and annotating the row with this ADR, is T4/SEED-14's record work.

## Operator words recorded (verbatim)

sha256 = `printf '%s' '<text between the quote marks>' | shasum -a 256` (UTF-8), computed by SEED-11c when writing this
ADR (after the fact, by the method S6 used).

| line | time (log) | words | label | sha256 |
|---|---|---|---|---|
| ADR-106's basis (2026-09-24) | LEDGER § GATE DECISIONS (as quoted in ADR-106) | *"counsel says it's okay and we can publish it all together."* | the operator's own words; per C-3, the determination was the operator's own | `377ac23ee29413f1939e34a559c09cc5a1223b96670f2e478a5563168052ea93` |
| A-4 (incl. Q-E2-14 c) | 2026-10-01T04:03:25Z | *"Adopt disclosed posture (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:03:25Z | `8509460b2536605180168be29f10318fbc6122f2b26c582d4f7dd4dd623ce626` |
| C-3 | 2026-10-01T04:54:19Z | *"The 'counsel' determinations of 2026-09-16 and 09-24 were my own; there was no counsel. My 09-28 message 'let's defer all the human review steps and proceed' was my decision to defer the human review legs."* | agent-drafted, adopted by the operator at 2026-10-01T04:54:19Z (recorded with that date, never as a 09-16/09-24/09-28 statement) | `1461ae213fac4749cd26d24d1ca22de1db893686d1b0fdef88cb64c296eca6c6` |

The C-3 sentence is ADR-167's record; it is repeated here only because it is this ADR's factual basis.

## Consequences

- No behaviour changes: the map, tiles, downloads and publish guard work exactly as ADR-106/ADR-118 built them.
- Text changes: every place that calls the ODbL basis a counsel clearance is corrected (P34.16 for the repo, copy
  batches for the site), and release manifests carry ADR-167's label once confirmed.
- **Exposure, plainly (not legal advice):** an OpenStreetMap-community or OSMF objection that SIG's map or API is a
  Derivative Database rather than a Produced Work could require re-architecting the ODbL compartment's use on the site
  (decision catalog Q-E2-14 consequences).

## Alternatives considered

- **Accept by ADR without the separation guarantees restated** (Q-E2-14 a) — not chosen; c keeps the per-compartment
  design explicit.
- **Obtain counsel's written opinion now** (Q-E2-14 b) — ruled out by the operator's no-counsel posture (U-013; A-4);
  remains possible under LATER-05.
- **Keep describing the basis as "operator-reported counsel clearance"** — rejected: on the operator's C-3 words there
  was no counsel, and TS-09 retires that phrasing.

## Revisit trigger

- An **objection from the OpenStreetMap Foundation, an OSM contributor community or any share-alike licensor**, or a
  takedown request under `policy/data/takedown.toml` targeting the ODbL or a CC-BY-SA compartment (ADR-106's second
  trigger).
- **Counsel is obtained** (LATER-05) and gives an opinion on the produced-work reading or 4.4(b) — this restates
  ADR-106's counsel-conditioned trigger ("counsel's dated written opinion differs"), dormant while there is no counsel
  (F3 NEW-8), as an event that can fire.
- A render surface or download starts carrying per-record data from several compartments, or the basemap and SIG data
  are proposed to be merged into one archive.
- The operator revises the determination (a new ADR).
