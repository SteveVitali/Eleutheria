# ADR-185: Part VIII screened lanes without a human clear (S1–S9 incl. S8 tribal; agent-cleared dossier families, disclosed)

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round-11 Stage B, T1 — unit SEED-11d)
- **Requirement ids:** SIG-PUB-002, SIG-PUB-003, SIG-PUB-003a, SIG-PUB-004, SIG-PUB-007, SIG-PUB-008, SIG-PUB-011…014, SIG-PUB-014a, SIG-STORE-025, SIG-GOV-007, SIG-GOV-017 — applied, none amended or waived
- **Spec:** docs/2_canonical_design_spec.md Part VIII — §43 (SIG-PUB-002 at line 6238, SIG-PUB-003 at 6249, SIG-PUB-003a at 6257, SIG-PUB-004 at 6293, SIG-PUB-011 at 6335, SIG-PUB-014a at 6356), §45.4 (SIG-GOV-007), §46 (SIG-GOV-017 at 6546–6548); §18 SIG-STORE-025 at 3186 (as built at `71e8bc83`; sources `docs/research/_meta/spec_src/90_partVIII_s42to43_lic_pub.md`, `91_partVIII_s44to46_sec_gov.md`)
- **Decision:** the operator's answers to B-32 (2026-10-01T04:43:37Z), B-35 and B-36 + B-37 (04:46:04Z), B-42 and B-44 (04:51:39Z) — `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md`, rounds 15, 16 and 18
- **Plan:** `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §4.4 (B-32, B-35, B-37, B-42, B-44), §5.5 ("Part VIII still binds"), §6.3 (SIG-PUB-002/003/003a and SIG-GOV-017 rows), §7 row 185, §14 R-23/R-26/R-27
- **Related:** ADR-184 (the fetch envelope whose rule 7 is this ADR's persistence rule), ADR-181 / ADR-189 (purge of sealed SIG-PUB-002 material), ADR-152 (confidence without independent review), ADR-163 (PUB-008 posture); I7 §1.2 S-lines, E4-B2…B4, J4 P8-3…P8-8
- **Recorded:** 2026-10-01T07:45:36Z (`date -u`) by Claude Code (Opus 5.5), Stage-B sub-agent SEED-11d. Everything in this record except the quoted operator words is agent-drafted.

## Context

I7 found Part VIII hazards across the Round-11 candidate sources and grouped them into nine screen lines, S1–S9, each
with a "screened lane" that emits only what Part VIII allows (I7 §1.2; J4 P8-3…P8-8). E4-B2 recommended that a
Round-11 ticket run the Part VIII screen on the five Round-10 dossier families and that the operator sign "clear" for
each (the P27.2 class-level precedent). B-31 and Q-8 leave no human to check anything but the operator, and the
operator chose not to clear the families personally. New connectors fetching terms-conflicted pages (ADR-184) also
needed one rule for applying SIG-PUB-002 before anything is persisted (S6R-11).

## Decision

### The operator's words (verbatim, with the log's round times)

| line | answer, verbatim | time (`date -u`) |
|---|---|---|
| B-32 (S1–S9 screens) | "Include S8 screened lane" — chosen over the recommendation (S8 metadata-only) | 2026-10-01T04:43:37Z |
| B-35 (IT7 Axon Connect) | "IT7 full fetch" | 2026-10-01T04:46:04Z |
| B-36 + B-37 (IU1–IU5; TR1–TR2) | "Capture IU; TR facts+cite (Recommended)" | 2026-10-01T04:46:04Z |
| B-42 (Round-10 dossier families) | "Agent clears, disclosed" — chosen over the recommendation (operator clears) | 2026-10-01T04:51:39Z |
| B-44 part 1 | "'My location' map button, Agenda titles if screened (Recommended), Short excerpts if permitted (Recommended)" | 2026-10-01T04:51:39Z |
| B-44 part 2 | "Show run-record artifacts (Recommended), Single-source sites shown (Recommended), County + place pages (Recommended)" | 2026-10-01T04:51:39Z |

These are selected option labels, not own-words sentences; `data/decision_catalog.csv` records each member decision
(I7-S1…S9, I7-TR1/TR2, E4-B2…B4, D-K1-7, D-K7-6, D-K8-1) with its `operator_answer` and `answered_at`.

### 1. The screened lanes (I7 S1–S9; B-32 = a for every line, S8 included)

| line | members | lane: only this is emitted |
|---|---|---|
| S1 private-camera registrants | 24 | programme-level facts only; no registrant location, name or count below programme level (SIG-PUB-004 C3) |
| S2 field allow-list | 4 | never request editor-tracking / operator / pilot fields; redacted re-serialisation only |
| S3 aggregate-only | 7 | institution-level counts, never rows (SIG-STORE-025); the CourtListener member deferred (I7-C8 b) |
| S4 residential / RF | 13 | coarsened or aggregated; never a public point layer (SIG-PUB-011…014) |
| S5 officer names | 11 | the §43.4 naming gate; no names from audit rows; names suppressed (SIG-PUB-008 stands, default deny) |
| S6 free text | 16 | the SIG-PUB-014a pre-publication excerpt screen; facts only |
| S7 incidental private names | 30 | extraction-time redaction |
| S8 tribal sovereignty | 2 | the Part VIII-screened lane, **without** a tribal-data-governance rule and with no outside contact (the operator's choice; plan §14 R-26) |
| S9 row-specific | 3 | the row's own screen (family members, same-org hazard layers, signature blocks) |

TR1–TR2 (Tribal Leaders Directory; a Tohono O'odham legislative notice) are cited as facts + citations under the S8
screen (B-37 → I7-TR1/TR2 c). Counts are I7's (decision catalog, I7-S1…S9).

### 2. Dossier families cleared by the agent, disclosed (B-42)

A Round-11 ticket runs the Part VIII screen on each Round-10 dossier family and the agent clears it; there is no
operator "clear" (E4-B2). Every readout and source page that relies on it says **"cleared by agent screen, no human
review"**. The SRC-027 network-audit workbooks stay metadata-only permanently (E4-B3), and the San Diego PAB
recommendation gets one bounded retry (E4-B4).

### 3. B-44's Part VIII rows

- Agenda item titles that may name people: the verbatim title only when the person-name screen passes, otherwise the
  matter number + the matched term (D-K7-6).
- Excerpts in claim views: a locator always; an excerpt of ≤ 300 characters only where the source's recorded terms
  permit quotation (D-K8-1), and always through the S6 screen.
- "My location" (D-K1-7, approved over the recommendation): SIG-GOV-017 is **not waived**, so row **P37.72** writes a
  GOV-017 analysis first and builds only a map-pan control (browser-only geolocation after a click, never sent to SIG;
  no "cameras near you" list, count, alert or proximity notice); if the analysis finds it cannot comply, the ticket
  pauses and returns the question to the operator (plan §14 R-27).

### 4. One persistence rule for the terms-conflicted connectors (S6R-11)

For P36.74, P36.76, P36.77 and P36.78: SIG-PUB-002 material (private-person names, home addresses, personal
identifiers) is redacted **in memory** before anything is persisted; the store keeps a redacted rendition + the
upstream URL + the sha256 of the original, or — where a document cannot be reliably redacted — only that pointer and
the screened facts. Existing bytes that the Part VIII at-rest audit (**P34.49**) finds are sealed (restricted tier,
protective, SIG-GOV-007) and listed, counts only, for the operator's purge decision under WV-06/WV-11 (ADR-181,
ADR-189).

### 5. Ordering

The residential demotion (P35.66), the officer-naming gate (P35.28), the redaction pipeline (P36.15) and the at-rest
audit (P34.49) land before Wave B activates and before the new connectors fetch (TS-07; their `depends_on` edges in
`data/round11_plan.csv`).

### What is and is not waived

No Part VIII MUST is amended or waived; this ADR applies them. The human "clear" replaced in §2 was a process precedent
(P27.2; E4-B2 option a), not a spec MUST — agent reading, labelled. If a requirement is found that demands human review
of a Part VIII screen, removing that review is a waiver and goes back to the operator for their words (plan §6.5: an
amendment that weakens a MUST is a waiver).

## Consequences

- No human checks the screens this round (plan §14 R-23). The mechanical screens, their tests and the disclosure are
  the only control; a reader-reported exposure is the signal they missed something.
- Two tribal sources are ingested without a tribal-data-governance rule (R-26).
- T4 records the risks and BACKLOG rows; SEED-15's `ADR_TRIGGERS.csv` carries this trigger.

## Alternatives considered

- **S8 metadata-only (the recommendation)** or **all lanes metadata-only** — not chosen.
- **Operator signs "clear" per family (E4-B2 a, the recommendation)** — not chosen.
- **Keep the families `not_assessed` (E4-B2 b)** — their live stage would stay blocked.

## Revisit trigger

Revisit — by a new ADR — when any of these happens:

- a Part VIII exposure the screens missed is reported or found (withdraw first, then revisit);
- a tribal Nation objects, or a tribal-data-governance rule is adopted (R-26);
- the SIG-GOV-017 analysis for "My location" concludes (R-27);
- an independent reviewer becomes available (T-EVAL-IND);
- a new source family brings a Part VIII hazard outside S1–S9.
