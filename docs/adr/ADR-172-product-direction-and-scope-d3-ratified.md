# ADR-172: Product direction and scope — D3 ratified with vendor pages fetched; the announce gate

- **Status:** Accepted
- **Phase:** Round 11 / Stage B, T1 (seed; `NEXT_PHASE_PLAN.md` §7 row 172)
- **Ticket:** SEED-11
  (Stage-B unit SEED-11c; run ledger `docs/build/runs/SEED-11c.md`)
- **Date:** 2026-10-01 — decided by the operator at GATE-P: A-17 at 2026-10-01T04:16:29Z (log round 6); C-4 at
  2026-10-01T04:56:11Z (log round 20); S6-F3 at 2026-10-01T06:05:22Z (log round 24)
- **Written:** 2026-10-01T07:42:45Z (`date -u`; Claude Code, Opus 5.5, Stage-B sub-agent)
- **Base:** `r11/seed` tip `f66b2450`
- **Decision owner:** the operator (GATE-P). This ADR records the decision.
- **Relation to landed ADRs:** none named by §7.
- **Related:** `PD/design/D3-product-direction.md` (the ratified memo; `PD` = `docs/build/planning/2026-09-30-next-phase/`);
  U-001…U-015 (`PD/feedback/OPERATOR_FEEDBACK.md`); SIG-CHART-025; E1-20/E2-20; ADR-149 (operating model, REVIEW-R11),
  ADR-155 (HTML-first page types), ADR-168 (robots), ADR-173 (acquisition), ADR-180/ADR-186 (intake, handling
  priority), ADR-183 (express-terms acceptance), ADR-184 (terms-conflicted fetch envelope), ADR-185 (Part VIII lanes),
  ADR-188 (WV-10, Flock portals probe-only); `PD/NEXT_PHASE_PLAN.md` §4.2 A-17, §4.5 C-4, §4.8 S6-F3, §5.5, §13.2–§13.5,
  §14 R-18, §15 LATER-22; `PD/data/decision_catalog.csv` rows D3-Q1, D3-Q3, D3-Q5, Q-E2-22, D-K14-1, S6-F3.

## Context

D3 (written 2026-09-30T22:03Z as an agent draft for operator ratification) set Round 11's direction from the operator's
feedback U-001…U-015: *make SIG show, correct and open up the evidence it already holds, while growing US-wide vendor
coverage from high-quality origins* — safety and honesty first, then correctness, then exploration, with source growth
in parallel. It defined the audiences and 13 acceptance journeys (§2), success criteria for U-007's three outcomes
(§3), the round's scope and constraints (§4), a "ready to announce" checklist (§5, for U-009 *"when the time is right"*),
the principles to preserve (§6), and five open questions (§7).

Separately, SIG-CHART-025 requires the first release to be "narrowly excellent at U.S. ALPR infrastructure", while the
live release is national and international across camera types (E1-20/E2-20, Q-E2-22).

The operator was asked A-17, "ratify D3 direction": *Ratify as drafted (Recommended)* · *Ratify; fetch vendor pages* ·
*Ratify; allow preview share* · *Exploration before correctness*. "As drafted" carried D3-Q3's recommendation **a**
(Flock/Axon facts only from agency pages, procurement records, statutory reports and already-ingested mirrors — never
fetched from vendor hosts, whose terms forbid automated extraction). Later: C-4 asked for the home tagline; S6-F3 asked
whether the post-round Claude Code review (REVIEW-R11) gates the announcement.

## Decision

1. **D3 is Round 11's product direction**, ratified with one edit (A-17, *"Ratify; fetch vendor pages"*,
   2026-10-01T04:16:29Z). The operator chose this **against the recommendation**: they declined *"Ratify as drafted
   (Recommended)"*, i.e. D3-Q3 **a** (never fetch from vendor hosts), and chose D3-Q3 **b**. D3-Q1 = yes, D3-Q5 = a and
   Q-E2-22 = a, each as recommended.
2. **Vendor-hosted public pages are fetched (D3-Q3 b).** Flock, Axon and other vendor transparency pages may be fetched
   inside the engineering envelope the agent recorded with the answer (log round 6, labelled interpretation): public,
   unauthenticated pages only; no logins, API keys or circumvention of access controls; rate-limited; the project's
   contact string (an owned explanation URL, never the operator's personal identifiers — ADR-168); robots per GL-GATE-08
   (ADR-168); terms text captured verbatim and the exposure disclosed; the Part VIII screen on every byte. ADR-184 is that
   envelope's record and ADR-185 the screen's; after round 26, **Flock's own portals are probe-only** (WV-10, ADR-188).
   The exposure of fetching against vendor anti-automation terms is the operator's accepted risk (§14 R-18).
3. **Audiences and journeys (D3-Q1 = yes).** The local advocate stays the design centre and wins conflicts over register
   and print; investigative journalists and organizers are co-primary, and their journeys gate the capstone equally. The
   13 journeys (A1–A4, J1–J5, O1–O4; D3 §2, plan §13.3) are walked cold from `/` at 390 and 1440 px by a fresh-context
   agent (recorded `agent-verified`, never "user-tested") and by the operator (recorded "operator walkthrough
   (maintainer, not independent)").
4. **SIG-CHART-025 is amended (Q-E2-22 = a):** from "narrowly excellent at U.S. ALPR" to **US-nationwide
   multi-vendor / multi-technology breadth with per-class and per-geography quality labels**, so breadth is never read as
   depth. Coverage priority stays US-nationwide Flock, Axon and other vendors (U-007). The amendment text is SEED-12's
   `spec_src` work and the coverage re-verdict is T4's; plan §5.10 classes it as a non-weakening amendment.
5. **Tagline (C-4):** *"Public surveillance, traced to the documents."* (2026-10-01T04:56:11Z). The operator chose this
   **against the recommendation**: they declined *"The evidence behind public surveillance, place by place."* (D-K14-1).
   The rest of the positioning copy named in the answer (the sub-head, About paragraph, why-it-exists line and four "is
   not" lines) goes to copy batch #1 for verbatim confirmation (B-2); this ADR confirms none of that copy, nor D3 §1's
   landing text, verbatim. No "who runs SIG" section ships until the operator writes it (C-5).
6. **The announce gate (D3-Q5 = a; S6-F3).** D3 §5's checklist — as restated and updated in plan §13.5 — is the gate for
   announcing SIG; there is **no earlier "preview" share**. GATE-ANNOUNCE also **waits for REVIEW-R11** (the Claude Code,
   Opus 5.5, xhigh-effort deep review run after the final release and P38.4) **and for each of its S0/S1 findings to be
   fixed** (by plan-extension rows run under the chain's rules) **or dispositioned by the operator**; S2/S3 findings feed
   the next round (S6-F3, *"S0/S1 must be dispositioned (Recommended)"*, 2026-10-01T06:05:22Z, as recommended).
   GATE-ANNOUNCE is the operator's decision and is never automatic; if it is unanswered, SIG is not announced; agents
   contact no one; the announcement itself (LATER-22) is the operator's to post.
7. **Where a later GATE-P answer changed a D3 clause, the later answer governs** (agent reconciliation, labelled; each
   change is the cited answer's, not this ADR's):
   - D3 §4 "non-US dossiers are corrected but not expanded" and "international data" under *Later* → **S5-4 "Keep non-US
     acquisition"**: non-US acquisition stays in the round, US-first for priority (ADR-173).
   - D3 §4 "tribal-keyed data" under *Later* → **B-32**: the two S8 tribal members are ingested through their screened
     lane (ADR-185).
   - D3 §4 "withdrawing forbidden-terms sources" and §5 "forbidden-terms sources are withdrawn" → **A-8**: the ≈8,088
     express-terms rows stay, disclosed with their captured terms and the operator-accepted basis (ADR-183; §13.5).
   - D3 §5 "The dispute email discloses single-maintainer response times" → **B-8, WV-05, WV-08**: no response time is
     promised; the page states that senders disclose their address and publishes the handling priority (ADR-180,
     ADR-186; §13.5).
   - D3 §4 "intake dark unless Q2 says otherwise" → **B-8**: e-mail-only intake until after the announcement.
   - D3 §3(b) "I7's projected reach … 40 of 51 states plus DC, and 28 of 29 technology classes" → with Wave D in scope
     (**B-11**, I8-Q5 a), plan §5.5 targets I7's Tier-2 projection (46 of 51 states + DC, 29 of 29 classes; core-only
     floor 40 and 28 — inference).
   - D3's Flock/Axon limits ("never from vendor hosts") → **D3-Q3 b** above.
8. **What D3 keeps (§6), unchanged:** every fact evidenced and every claim with provenance; contradictions visible;
   absences typed; no totals and no census claim; Part VIII (no plate or person data, institutions only under the
   officer-naming gate, audit data only as aggregates, no evasion instructions, no user location shared with third
   parties); the printed and cited record complete, script-free and citable (HTML-first page types, ADR-155);
   precision kept with a plain-language layer added; a neutral register; peers linked, not rebuilt; append-only data,
   the ingestion gate, and HG-03 flips owned by the operator. The cost ceiling (≤ $300/mo without the operator's go)
   and maximal agent autonomy with a visible spend ledger stand (U-008, U-011).

## Operator words recorded (verbatim)

sha256 = `printf '%s' '<text between the quote marks>' | shasum -a 256` (UTF-8), computed by SEED-11c when writing this
ADR (after the fact, by the method S6 used).

| line | time (log) | words | label | sha256 |
|---|---|---|---|---|
| A-17 | 2026-10-01T04:16:29Z | *"Ratify; fetch vendor pages"* | option label selected by the operator (against the recommendation) | `f7630a36ebb22ba4c5c0ba7c2d107f2d0a2131164f7acb78c6b3ac4f8054d6a0` |
| C-4 (selected option) | 2026-10-01T04:56:11Z | *"…traced to the documents"* | option label selected by the operator (against the recommendation) | `de96d3ec04018f00c6a7f2681b07ab14a933b15ac4a21cee5038e6ef86d940b8` |
| C-4 (adopted tagline) | 2026-10-01T04:56:11Z | *"Public surveillance, traced to the documents."* | agent-drafted, adopted by the operator at 2026-10-01T04:56:11Z | `e997a77e482bcd29e294ee9008c8eb7d69fad00ec3a24a6b61b48c3010786f6e` |
| S6-F3 | 2026-10-01T06:05:22Z | *"S0/S1 must be dispositioned (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T06:05:22Z | `1ecfa568575ad44f0a10031c4930a3752af5d57ed01f580aaa915dfc6fed0ccd` |

D3-Q1 (yes), D3-Q5 (a) and Q-E2-22 (a) were answered by the A-17 selection; their recorded answers are in
`PD/data/decision_catalog.csv` with `answered_at` 2026-10-01T04:16:29Z.

## Consequences

- Added work from D3-Q3 b: the vendor and terms-conflicted connectors (P36.74 probe-only, P36.76 Axon Connect; with
  B-39, P36.77 and P36.78), each inside ADR-184's envelope and ADR-185's screen.
- Every coverage surface labels quality per technology class and geography; per-vendor Flock/Axon thresholds are in plan
  §5.5 and checked by P37.66 and P38.1a/b.
- The round's success criteria (§13.2) and the announce checklist (§13.5) are stated as chosen; a criterion the operator
  descoped at GATE-P is reported as decided, never as MET and never as a defect.
- No announcement happens until GATE-ANNOUNCE — after REVIEW-R11 — is answered by the operator.

## Alternatives considered

- **Ratify as drafted** (recommended; D3-Q3 a, never fetch vendor hosts) — declined by the operator; it would have left
  Flock and Axon's own published data dark.
- **Ratify; allow preview share** — declined; no earlier share labelled "preview" (D3-Q5 a).
- **Exploration before correctness** — declined; the order stays safety → correctness → exploration.
- **Reaffirm the U.S.-ALPR-only wedge, or keep breadth with international as-is** (Q-E2-22 b/c) — declined in favour of
  the amended, labelled breadth.
- **REVIEW-R11 advisory only** (S6-F3 b) — declined.

## Revisit trigger

- **REVIEW-R11 completes**: its S0/S1 findings are fixed or dispositioned before GATE-ANNOUNCE; its S2/S3 findings and
  this direction are re-planned for the next round.
- **GATE-ANNOUNCE is answered** (either way), or LATER-22's conditions are met — the direction is revisited for the
  post-announcement round.
- A **vendor's objection, block, cease-and-desist or terms change** affecting vendor-page fetching (§14 R-18; ADR-184's
  and ADR-188's triggers).
- A journey that cannot pass on real data within the round, or a per-class quality label showing that breadth is being
  read as depth.
- The operator changes the tagline, the positioning copy or the coverage priority (U-007).
