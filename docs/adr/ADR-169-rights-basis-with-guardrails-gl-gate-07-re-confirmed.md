# ADR-169: Rights basis with guardrails — GL-GATE-07 re-confirmed in the operator's adopted words

- **Status:** Accepted
- **Phase:** Round 11 / Stage B, T1 (seed; `NEXT_PHASE_PLAN.md` §7 row 169)
- **Ticket:** SEED-11
  (Stage-B unit SEED-11c; run ledger `docs/build/runs/SEED-11c.md`)
- **Date:** 2026-10-01 — decided by the operator at GATE-P: A-4 and A-7 at 2026-10-01T04:03:25Z (log round 3); X3 and A-9
  at 04:07:45Z (round 4); A-22 at 04:25:48Z (round 8); B-33…B-37 at 04:46:04Z (round 16); B-38…B-41 and B-43 at
  04:49:27Z (round 17); B-41's R2a at 04:51:39Z (round 18); B-41's record clarification (S6R-02) logged in round 26
  (06:51:11Z)
- **Written:** 2026-10-01T07:42:45Z (`date -u`; Claude Code, Opus 5.5, Stage-B sub-agent)
- **Base:** `r11/seed` tip `f66b2450`
- **Decision owner:** the operator (GATE-P; HG-03 flips are theirs alone). This ADR records the decisions.
- **Relation to landed ADRs:** none named by §7 (no status line is owed on a landed ADR). It operates on the append-only
  `rights_decision` log of ADR-095 and the registry gate of ADR-021, unchanged.
- **Related:** GL-GATE-07 (`docs/build/LEDGER.md` § GATE DECISIONS, 2026-09-18) and its per-ticket invocations (P27.2,
  2026-09-22; P29.3, 2026-09-23); SIG-LIC-003/004/004a/009/010, SIG-PUB-017, HG-03; ADR-167 (counsel basis), ADR-182
  (WV-07), ADR-183 (express-terms acceptance, A-8), ADR-184 (terms-conflicted fetch envelope), ADR-185 (Part VIII screened
  lanes), ADR-187 (WV-09), ADR-188 (WV-10), ADR-173 (acquisition waves); plan rows P36.2, P36.75, P37.69a/b, P37.70,
  P34.28, P36.1a; operator actions OP-25, OP-26. `PD` = `docs/build/planning/2026-09-30-next-phase/`:
  `PD/NEXT_PHASE_PLAN.md` §4.2, §4.4, §4.9, §5.5, §6.3, §8.3, §14 R-19/R-20/R-26; `PD/feedback/RATIFICATION_LOG.md`;
  `PD/design/E2-governance-options.md` E2-11; `PD/design/I7-rights-packets.md`; `PD/design/E4-rights-packets.md`;
  `PD/reviews/S4-truth-safety.md` TS-06; `PD/reviews/S6r-closure.md` S6R-02/S6R-09/S6R-17.

## Context

**What was recorded.** GL-GATE-07, 2026-09-18 (`docs/build/LEDGER.md` § GATE DECISIONS), verbatim: *"We should ungate
the D-SOURCES.12-1 257 gated datasets and for all the 'rights review' cases we should err on the side of approving
them"*. Its execution rule: US → `LicenseRef-PublicRecord-FactualCompilation`; non-US →
`LicenseRef-OperatorAccepted-DBRight`; reviewer `maintainer (delegated)` + date; CourtListener deferred by name.

**What the Stage-P review found** (E1-11/E2-11; S4 TS-06; I7; E4): SIG-LIC-003/004 require unresolved rights to fail
closed and SIG-LIC-009 sent the EU database right to counsel, while GL-GATE-07 approved every "rights review" case on the
operator's risk acceptance; execution followed worklist membership rather than facts, and E2 counts **94 sources and
21,682 public rows** under `LicenseRef-OperatorAccepted-DBRight`. Later gates answered "under GL-GATE-07" without
looking at each new set (B5 lesson 2; TS-06). Q-19 — is GL-GATE-07 the default for new sources? — was open. I7 reduced
374 new Tier-1/Tier-2 candidates to 10 batch lines, 9 Part VIII screen lines and 35 individual rights lines; E4 set out
22 lines for the owed rows.

**What the operator was asked.** A-4 (the governance stance, incl. Q-E2-13 "GL-GATE-07 blanket approval vs fail-closed
rights review and the database right"); A-7 ("rights rule for Tier-1 flips (GL-GATE-07 re-decided in the operator's
words)": *Flip only captured terms (Recommended)* · *Re-confirm GL-GATE-07* · *Nothing flips yet*); X3; A-9; A-22;
B-33…B-41 (the I7/E4 lines, several with recommendations updated mid-session after earlier answers changed their
premise).

## Decision

1. **The operator-accepted rights basis is recognised with guardrails** (A-4, *"Adopt disclosed posture
   (Recommended)"*, 2026-10-01T04:03:25Z; Q-E2-13 **c**, as recommended). It is a **distinct, disclosed basis**, recorded
   as the operator's own determination (no counsel — ADR-167), never presented as evidenced rights or as counsel-cleared.
   Guardrails, from Q-E2-13 c as answered: the Part VIII preflight runs (a rights line never clears a Part VIII flag);
   express terms are decided individually (A-8 → ADR-183, A-9, B-39 → ADR-184); non-US rows publish under SIG-PUB-017's
   jurisdiction-conditional rule; a rights-holder objection triggers withdrawal by new claim through the withdrawal
   barrier (P34.41; 15-minute technical withdrawal). SIG-LIC-009's counsel-referral clause is waived by WV-07 (ADR-182);
   its risk-register clause stands (§14 R-19, R-20). The SIG-LIC-004 + HG-03 text amendment that recognises this basis
   is SEED-12's `spec_src` work (plan §6.3).
2. **GL-GATE-07 is re-confirmed** (A-7, *"Re-confirm GL-GATE-07"*, 2026-10-01T04:03:25Z), in the adopted words *"US
   public records and open-licence sources flip batch-wide under precedent, erring on the side of approving."* The
   operator chose this **against the recommendation**: they declined *"Flip only captured terms (Recommended)"* (Q-19 /
   S4c: GL-GATE-07 re-asked in their own words, with every Tier-1 batch carrying captured terms per member and members
   whose terms are "none captured" staying `ingestion_permitted=false` until captured — I7 option **b**). Consequences:
   - Tier-1 batches **RB-01…RB-07 and RB-09** (with RG1–RG5) take I7 option **a** (flip batch-wide on the precedent
     shown in each batch packet).
   - **E4-B1 = a:** GL-GATE-07 (US) applied batch-wide to all three lanes of the 23 new D-R10-SOURCES-1 targets — the
     S4c recommendation (*b — decide per target after terms are captured*) is the one declined.
   - Part-VIII-flagged members still need their screen line (B-32 → ADR-185); express prohibitions follow A-8/A-9/B-39.
3. **Widening configurations (X3)** (*"Confirm (Recommended)"*, 2026-10-01T04:07:45Z): the 46 widening configurations
   inherit their parent source's rights decision; no new HG-03 line; the Part VIII screen still applies. Targets added
   under an already-flipped source are configuration (I8-Q4, B-11; ADR-173).
4. **Commercial status (A-9)** (*"May be commercial (Recommended)"*, 2026-10-01T04:07:45Z): SIG's use is or may be
   commercial, so **new** non-commercial sources are facts + pointers only; E4-R4d (`camreg_bellevue_wa`) is declined;
   IT2, IT3, IT5 and IT6 take the facts-only pointer. The ≈8,088 already-public express-terms rows, including the three
   live non-commercial ones, stay under A-8's acceptance (ADR-183).
5. **Share-alike and territories (B-33)** (*"SA compartment; territories=US (Recommended)"*, 2026-10-01T04:46:04Z;
   recommendation updated after A-7): RB-06b flips into a **share-alike compartment** (the §42.3 amendment is SEED-12's);
   RB-08's territorial public records (Puerto Rico SUTRA measures, the USVI legislature) are treated **as US** under
   GL-GATE-07.
6. **Non-US database right, N1–N21 (B-34)** (*"Flip under precedent (Recommended)"*, 2026-10-01T04:46:04Z;
   recommendation updated after S5-4): each flips on the non-US `LicenseRef-OperatorAccepted-DBRight` precedent, express
   prohibitions excluded, published under SIG-PUB-017 (P37.69a/b; ADR-173). Accepted risk §14 R-20.
7. **Restricted terms, IT1–IT7 (B-35)** (*"IT7 full fetch"*, 2026-10-01T04:46:04Z — **against the recommendation**
   *"IT7 program facts only (Recommended)"*): IT1 b, IT2/3/5/6 b (A-9), IT4 c, IT7 a. IT7 (Axon Fusus "Connect <Place>"
   pages) is fetched in full under ADR-184's envelope with every byte through the Part VIII screen (ADR-185); private
   registrants are never stored in public output or published.
8. **Terms not captured and tribal publishers (B-36 + B-37)** (*"Capture IU; TR facts+cite (Recommended)"*,
   2026-10-01T04:46:04Z; recommendation updated after B-32): IU1–IU5 terms are captured in P36.2, then each gets a new
   HG-03 line (GATE-G6 packet at the latest); TR1–TR2 are facts + citations under the S8 screen (no
   tribal-data-governance rule; §14 R-26; ADR-185).
9. **SEC EDGAR, P1–P4 (B-38)** (*"As stated (Recommended)"*, 2026-10-01T04:49:27Z): a facts-only basis is recorded;
   ingestion stays later-phase (LATER-09); the first request waits for the `contact@` alias (C-8).
10. **Conflicts (B-39)** (*"Also fetch DocCloud/Sourcewell"*, 2026-10-01T04:49:27Z — **against the recommendation**
    *"As stated (Recommended)"*, which was link-only for DocumentCloud/MuckRock and contract-id pointers for
    Sourcewell/OMNIA): C2 and C3 are fetched despite their anti-automation terms inside ADR-184's envelope (rule 6 for
    DocumentCloud/MuckRock waived by WV-09, ADR-187); C4 per A-17 (ADR-172/ADR-184; Flock portals probe-only, ADR-188);
    C5 b (accept the Chicago and Albuquerque revocation clauses — city portals, already flipped — and decline the
    OpenFEMA API route; the FEMA pages stay the funding source); C7 a (SDPC facts from district-side pages only); C8 b
    (CourtListener bulk deferred with R2b); C9 a (the statute seed refreshed from legislature origins); C11 a (decide
    E4-R4a on the OGL-Edmonton basis once the terms body is captured).
11. **Confirmations (B-40 + B-43)** (*"Confirm all (Recommended)"*, 2026-10-01T04:49:27Z): X1 (the 19 Tier-3 candidates
    whose captured terms prohibit stay declined; pointers only), X2 (the 26 Part VIII blocks are existence/metadata
    only), X4 (registry label corrections M1–M7 approved); E4 S1–S5 and F1's D-P21.3-2 status corrections (SEED-14).
12. **The E4 rows (B-41)** (*"As listed, R3 flip"*, 2026-10-01T04:49:27Z — **against the recommendation** *"As listed
    (Recommended)"*), with R2a re-asked because B-41's listing (decline) conflicted with B-39 (fetch) and answered
    *"Fetch, screened (Recommended)"* (2026-10-01T04:51:39Z):
    - R1 close (rights DONE; the Belgian eID leg WONTFIX); **R2a flip `documentcloud`** (public documents only, Part VIII
      screen on every byte, link to the uploader's page; activation after its HG-03 flip, ADR-184/ADR-187); R2b decline
      `courtlistener_recap`;
    - **R3 flip `dot_511_tx`** under GL-GATE-07 (US) — the operator declined the presented recommendation *"I recommend
      finding a TxDOT-owned layer first rather than a second republish"*;
    - **R4a** decided on the OGL-Edmonton basis after the terms body is captured (I7-C11 a); if the captured terms are
      not OGL-Edmonton, a new HG-03 line rides the GATE-G6 packet; **R4b flip `camreg_hk_hk`** on the non-US basis; R4c
      via the QLDTraffic API (P37.70; keys under B-18); R4d decline (A-9); R5 flip `procportal_chicago_il`; R6a capture
      the `bidnetdirect.com` terms, then a new line; R6b close `periscope_s2g` as superseded.
    - **Record clarification (S6R-02), quoted from the log's round 26:** B-41's text as presented listed *"R4a Edmonton
      on OGL-Edmonton; R4b Hong Kong flip"*, so R4b = flip and R4a = decided on the OGL-Edmonton basis are the
      operator's answers as presented (S6R-02 closed as not drift). The decision catalog's `recommendation` cell for
      E4-R4a/E4-R4b carries an earlier S4c draft ("b — capture the terms; NOT flipped this round"); this ADR records the
      answer to the text as presented.
13. **The Eyes on Flock mirror (A-22)** (*"Keep + use share lists (Recommended)"*, 2026-10-01T04:25:48Z; recommendation
    updated after A-17; OD-24 b): `eyes_on_flock` stays live on its CC-BY-SA-4.0 basis; its share lists become
    organisation-level claims after the Part VIII screen (P36.75) in the **CC BY-SA 4.0 compartment**, never merged into
    the CC-BY graph (S6R-12); and the `eyes_on_flock` **rights record and source page disclose that its 2026-09-16 review
    was delegated** (S6R-09; executed by P36.75).
14. **Who flips, and how (OP-26; S6R-17).** No agent flips a source. The agent prepares each wave's flip patch on
    `r11/<wave>-flips`; the operator applies it in **one commit signed with the OP-25 key**, or signs a GATE DECISIONS
    row naming each source id; P34.28's G4c check fails any `ingestion_permitted` false → true transition not covered by
    an operator-signed commit or record. Flip lists ride the wave gates (Waves A/B at GATE-G4, C at GATE-G5, D — N1–N21,
    ACQ-23a/b, DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08 — at GATE-G6). A row whose flip has not
    been executed lands with `ingestion_permitted=false` and activation skips it. The reviewer field records a role,
    never a name.

### Not decided here

A-8's express-terms acceptance (ADR-183); the terms-conflicted fetch envelope (ADR-184); the Part VIII screened lanes
(ADR-185); WV-07, WV-09 and WV-10 (ADR-182, ADR-187, ADR-188); the counsel basis and label text (ADR-167); A-18's flips of
`census_gazetteer_tiger` and `natural_earth_10m` (P35.17 / ADR-160). **Agent observation (labelled):** Q-E2-13's option c
also named re-deciding the out-of-rule and counsel-flagged rows individually (e.g. `camreg_und_001`,
`camreg_calgary_ab`, Lexington, MD iMAP); after A-7 and A-8 the plan schedules no individual re-decision row for them
(no such row in `PD/data/round11_plan.csv`), so they stay published under this basis and its withdrawal-on-objection
guardrail. Raised for the orchestrator, not decided here.

## Operator words recorded (verbatim)

sha256 = `printf '%s' '<text between the quote marks>' | shasum -a 256` (UTF-8), computed by SEED-11c when writing this
ADR (after the fact, by the method S6 used).

| line | time (log) | words | label | sha256 |
|---|---|---|---|---|
| GL-GATE-07 (2026-09-18) | LEDGER § GATE DECISIONS | *"We should ungate the D-SOURCES.12-1 257 gated datasets and for all the 'rights review' cases we should err on the side of approving them"* | the operator's own words | `2f8e0f37eb00c8d3ea63e5b7ddeb2d4124bf1dd2d2f0df1f631b584bcc903835` |
| A-4 | 2026-10-01T04:03:25Z | *"Adopt disclosed posture (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:03:25Z | `8509460b2536605180168be29f10318fbc6122f2b26c582d4f7dd4dd623ce626` |
| A-7 (selected option) | 2026-10-01T04:03:25Z | *"Re-confirm GL-GATE-07"* | option label selected by the operator (against the recommendation) | `dacea820668758915b61559b900f73984703fd99e9906ecd3dd360aa8f433559` |
| A-7 (adopted option text) | 2026-10-01T04:03:25Z | *"US public records and open-licence sources flip batch-wide under precedent, erring on the side of approving."* | agent-drafted, adopted by the operator at 2026-10-01T04:03:25Z | `1bfedde5feac422142dae546369a04c6653ba6ab5d9edf12391dacbb3ddae241` |
| X3 | 2026-10-01T04:07:45Z | *"Confirm (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:07:45Z | `dfda3970c6eb4cd5c4955ada2005e30f42609cf0c083cbd4f94de1431b23b9b6` |
| A-9 | 2026-10-01T04:07:45Z | *"May be commercial (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:07:45Z | `9ea4affaed2e9fafcd14ac427b25a5151e2a9757d07986a5b27ff77743d295ed` |
| A-22 | 2026-10-01T04:25:48Z | *"Keep + use share lists (Recommended)"* | agent-drafted option (recommendation updated mid-session), adopted by the operator at 2026-10-01T04:25:48Z | `c22738ea7d3b60ddc521b44137ffa024ec708e59f0ca5c597e1f5571dd02ba96` |
| B-33 | 2026-10-01T04:46:04Z | *"SA compartment; territories=US (Recommended)"* | agent-drafted option (updated after A-7), adopted by the operator at 2026-10-01T04:46:04Z | `eedc88d5bd432fd3354b9b19c7acd513d5a0eb0a162d91fec03c460641a50214` |
| B-34 | 2026-10-01T04:46:04Z | *"Flip under precedent (Recommended)"* | agent-drafted option (updated after S5-4), adopted by the operator at 2026-10-01T04:46:04Z | `680e93cebaa134ad486c74f923c571c85b654985798d2fc3af84858a77275e46` |
| B-35 | 2026-10-01T04:46:04Z | *"IT7 full fetch"* | option label selected by the operator (against the recommendation) | `351482c77dde1b10875a671aea3271128845f98a26b667836b42a774a795c828` |
| B-36 + B-37 | 2026-10-01T04:46:04Z | *"Capture IU; TR facts+cite (Recommended)"* | agent-drafted option (updated after B-32), adopted by the operator at 2026-10-01T04:46:04Z | `ca49487eedd4c0a8978cf64404f92eb1a7676d61094c53dee260ba861265719a` |
| B-38 | 2026-10-01T04:49:27Z | *"As stated (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:49:27Z | `dda51782d3e72cf3c6621a079580c2bd3b6a17225db0b2406c08b5ec9fe52706` |
| B-39 | 2026-10-01T04:49:27Z | *"Also fetch DocCloud/Sourcewell"* | option label selected by the operator (against the recommendation) | `a1f985b0cd21061ef274fd8c402f72e35042858145197df1202ce085546e2cfc` |
| B-40 + B-43 | 2026-10-01T04:49:27Z | *"Confirm all (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:49:27Z | `c7f2fc828715c3a9c2ee6458d12e1eae0085197ba3ec2e3c7e17f93ff0a481d5` |
| B-41 | 2026-10-01T04:49:27Z | *"As listed, R3 flip"* | option label selected by the operator (against the recommendation) | `2f8dcb97f7f2721f5dd76410565e58591595410ea366f8decaea3fa0f7e73fe8` |
| B-41 R2a vs B-39 | 2026-10-01T04:51:39Z | *"Fetch, screened (Recommended)"* | agent-drafted option, adopted by the operator at 2026-10-01T04:51:39Z | `5750b9a46bd0c500c0424a6376e3808ace6304c4c8045a6a6baaf1c166627f70` |
| B-41 text as presented (S6R-02) | round 17 (quoted in round 26) | *"B-41. Pending source rights rows, updated for your answers. R1 Belgian eID leg: close (WONTFIX). R2a DocumentCloud / R2b CourtListener RECAP: decline. R3 dot_511_tx (a second TxDOT republish): since you kept the first (A-8), I recommend finding a TxDOT-owned layer first rather than a second republish. R4a Edmonton on OGL-Edmonton; R4b Hong Kong flip; R4c QLDC via the QLDTraffic API (CC-BY, now that you'll register AU keys). R4d Bellevue: decline (non-commercial, A-9). R5 Chicago procurement portal: flip. R6a BidNet: capture terms first; R6b Periscope: superseded."* | agent-drafted question text the operator answered (not the operator's words) | `6633a335146f29d1b6bdd7760969073ce1b0c372680d8e1279bfa4cc9099d61b` |

## Consequences

- Tier-1, widening, territorial and N-line sources become activatable wave by wave — only after the operator executes
  each flip (OP-26) and gives the wave's ING-GO (ADR-173).
- **Accepted risks:** the EU/UK database right on N1–N21 (§14 R-20); express-terms rows kept public and the open 046c
  question about their captured metadata (§14 R-19; ADR-183, P36.1a); tribal sources ingested as facts + citations
  without a tribal-data-governance rule (§14 R-26). Batch-wide flips over members whose terms were not captured are the
  operator's chosen risk (A-7), disclosed on the source pages with the basis.
- **Disclosure:** every source page and export shows its basis (`LicenseRef-PublicRecord-FactualCompilation`,
  `LicenseRef-OperatorAccepted-DBRight`, a verbatim open licence, or derived facts + citations), labelled as the
  operator's determination, never counsel-cleared (ADR-167).
- **Remedy:** withdrawal by new claim (append-only), reaching every alias within 15 minutes through the withdrawal
  barrier; true deletion only for material SIG must not hold at all (ADR-181/ADR-189).
- Rights lines raised during the round (any 046c case from P36.1a; IU1–IU5 after P36.2; E4-R4a if Edmonton's terms are
  not OGL-Edmonton; E4-R6a) ride the next GATE packet (S6R-28).

## Alternatives considered

- **Flip only captured terms** (A-7 recommendation; Q-19 S4c; I7 option b) — declined by the operator.
- **Nothing flips yet** (A-7) — declined.
- **Revert all 94 operator-accepted sources to UNDETERMINED** (Q-E2-13 b) — not chosen; it would remove 21,682 public rows
  and a map layer and cost 47–188 h of review (E2-11).
- **IT7 program facts only; link-only DocumentCloud; Sourcewell/OMNIA pointers; TxDOT-owned layer first** — the
  recommendations the operator declined at B-35, B-39 and B-41.

## Revisit trigger

- A **rights-holder or licensor objection**, a takedown request, or a **legal demand** naming a flipped source
  (withdrawal first; then a new rights decision row and, where the basis changes, a new ADR).
- **Counsel is obtained** (LATER-05) and gives an opinion on the database-right or share-alike bases.
- **A new jurisdiction class** not covered by these lines (e.g. a sovereign tribal publisher beyond TR1–TR2, a new
  territory or country) — decided per line, never by stretching GL-GATE-07.
- P36.1a finds that an express-terms row's captured metadata is an **affirmative reservation** (SIG-INGEST-046c), or a
  captured term turns out to be an **express prohibition** on a batch-flipped member.
- A **terms change** on a fetched platform (DocumentCloud/MuckRock, Sourcewell/OMNIA, Axon, Flock) or the Eyes on Flock
  aggregator changing its licence or stopping publication.
- The operator revokes or narrows GL-GATE-07 (a new gate decision and a new ADR).

## Status updates

- 2026-10-03 (P34.18 / ADR-178, S0 RI-01): a handle-bearing source identifier
  quoted in this ADR's body was re-keyed to its neutral id under the Part VIII
  personal-data protection re-key; the recorded decision is unchanged. Git
  history retains the original string — see the P34.18 correction note
  (`docs/governance/identifier-rekey-note.md`).
