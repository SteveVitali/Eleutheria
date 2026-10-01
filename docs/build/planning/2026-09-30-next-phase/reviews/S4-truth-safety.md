# S4 — Adversarial review: truth, safety and governance

- **Row:** S4 (lens: truth, safety and governance) of `META_PLAN.md` Stage P. **Artifact under review:** `NEXT_PHASE_PLAN.md`
  (DRAFT, S3) at planning HEAD `c3e37654`, branch `claude/next-phase-planning` (local; no upstream).
- **Reviewer:** Claude Code (Opus 5.5), fresh context, not the author of S3 or its inputs (P6). Written
  2026-10-01T01:39:35Z (`date -u`). Read-only: this row writes only this file; nothing was committed, no control file,
  spec, ADR or production system was touched, no external request was made (P3, P10, P16). The operator's e-mail address is
  never written here; it is "the operator's address".
- **Method.** The plan was read whole. It was tested against META_PLAN §2–§3 (P1–P16) and §7.1;
  `feedback/OPERATOR_FEEDBACK.md` (U-001…U-015); E1, E2, B1, B2, B5, B7, L1, L2, L3, J4, I7, I8, D3, S1c, S2, G2, G3, K1;
  `data/round11_plan.csv`, `data/ticket_catalog.csv`, `universe/UNIVERSE_DISPOSED.csv`, `findings/FINDINGS.csv`; spec Part VIII
  (§42–§46, `docs/2_canonical_design_spec.md:6043-6607`); and repo files (`connectors/.../sources.toml`,
  `camera_registry_targets.toml`, `docs/adr/ADR-086…`). Three read-only helper contexts gathered citations on rights, records
  and public claims; every load-bearing citation below was re-checked by this reviewer.
- **Evidence classes:** `code` (repo/plan text, `path:line`), `recorded-execution` (git), `inference` (labelled).
  Paths are relative to `PD = docs/build/planning/2026-09-30-next-phase/` unless they start with `docs/`, a package name or
  `~`. "PLAN:n" means `NEXT_PHASE_PLAN.md` line n; "CSV:row" means `data/round11_plan.csv` by chain row id.

---

## Verdict

**Ratifiable with fixes. It must not reach GATE-P until the four BLOCKERs below are fixed and closed in `reviews/REVIEW_CLOSURE.md`.**

The plan is honest about most of what it inherits, and it is careful in its own words. It does not fabricate human work
(PLAN:1092-1138). It keeps independent evaluation owed rather than waived (PLAN:1118). It never pre-authorises publication,
HG-03 or ING-GO by name (PLAN:236-239). It withdraws forbidden-terms rows by default (PLAN:287). And it keeps vendor hosts
dark (PLAN:482-484).

Where it fails, it repeats the Round 1–10 failures it was written to stop:
- **The ratification mechanics.** An agent-drafted one-line "fast path", and defaults that act on silence, would again let
  the agent decide for the operator. That covers rights, robots, the operator's identity, production authority and dozens
  of public-surface choices.
- **The honesty wave.** It ships a new public sentence that is not yet true.
- **The Part VIII S0.** The personal-handle exposure is scoped so that "closed live" can be declared while the handles stay
  public in the repo, in the listable release bucket and in other id fields.

These are bounded text-and-ordering fixes, not a redesign, so the verdict is not "not ratifiable".

| severity | count | ids |
|---|---:|---|
| BLOCKER | 4 | TS-01 … TS-04 |
| MAJOR | 10 | TS-05 … TS-14 |
| MINOR | 9 | TS-15 … TS-23 |

---

## BLOCKERS

### TS-01 — Ratification by an agent-drafted one-liner can again substitute for the operator's own words

**Problem.** S5 asks the operator to answer 87 packet lines. Those lines fold 323 decision ids, plus S5-1…S5-4 (PLAN:60,
:337-346, :1102). The S1c packet the plan adopts offers an **agent-drafted fast path**: *"Part A as recommended. Part B as
recommended. Part C confirmed. D2: agree with all, priorities as proposed."* (`design/S1c-decision-catalog.md:37`). It adds
that "as recommended" answers every member of a bundled line (S1c:33-35).

That one sentence would answer lines whose whole point is the operator's **own words**:
- A-6, the SIG-EVAL-004 waiver "in the operator's own words". The plan supplies the agent's example sentence (PLAN:285,
  :733-735).
- C-3, "Your own words" for counsel, for the 09-28 deferral and for robots (S1c:372).
- C-1, readout provenance.
- C-4, the public landing copy, which is agent-drafted.
- C-5, About.
- A-5, robots.
- B-9, a first-person standing-go text the agent drafted (`design/G3-release-model.md:451-456`).

The check-in packets repeat the pattern: `continue` "is a complete answer: every line inside takes its own default"
(`design/S2-round-structure.md:304-306`).

This is the mechanism behind the Round-10 failures:
- ACCEPT-R8, "please sign … for me or whatever".
- GATE-G3, "I sign/accept. Please proceed".
- ACCEPT-R10, "oik looks good, proceed", on agent summaries, with the signed texts composed 32 s and 51 s *after* approval
  (`research/B5-orchestration-retro.md:262`; `research/B7-harness-attribution.md:75`; S1c:370).

The plan's own operating clauses forbid it: OM-07 verbatim, OM-08 no proxy signatures, OM-09 hedged words, OM-18 "silence is
never consent" (PLAN:219-226). META_PLAN §2 says "no gate is pre-answered or guessed past". The plan never says how these
clauses bind S5 itself. "The operator ratifies this plan verbatim" (PLAN:99) is undefined for a 1,443-line document plus a
333-row CSV.

**Fix (plan text, before S5):**
1. Add to §1.3/§4 a **GATE-P recording rule**:
   - Lines marked **own-words** are A-5, A-6 (waiver sentence), A-16, B-9 (standing-go text), C-1, C-3, C-4, C-5, and any
     ADR the plan says carries "operator words" (PLAN:1316-1317).
   - The fast path and "as recommended" cannot answer an own-words line.
   - Each own-words line is answered by text the operator types, or by an agent draft that the operator reproduces or
     edits. Either way it is stored with the sha256 of the exact text shown and labelled *"agent-drafted, adopted by the
     operator at `<date -u>`"*. It is never presented as the operator's composition.
2. Define "ratified verbatim":
   - GATE-P records the operator's exact words, the sha256 of the plan revision and packet revision shown, and the list of
     lines each answer covers.
   - If the operator approves on a summary, the record says "approved on a summary of `<sha>`", which is B-4's own
     wording for ACCEPT-R8/R10.
3. In S5-2, `continue` must not answer any own-words, publication, rights, Part VIII, identity or OM-20 line (see TS-02).

### TS-02 — Defaults-if-unanswered that act, so the agent decides for the operator on rights, identity, publication surfaces and production authority

**Problem.** S1c promises that "every line has a default if unanswered. It is the conservative option, so the build never …
acts without an answer" (S1c:40-43). The plan inherits these defaults. Several of them act:

| line | default if unanswered | what it decides | evidence |
|---|---|---|---|
| **A-5** robots | "GL-GATE-08 stands as recorded". The plan's copy (PLAN:284) drops S1c's clause "no new robots-disallowed hosts" | Continued crawling of 103 hosts whose robots.txt explicitly disallows SIG: 102 PrimeGov municipal hosts on one vendor platform, plus `oscn.net`. The basis is tentative words, *"I also wonder if we should disregard robots.txt-gated sources…"*, which B5 classes as "tentative words recorded as a decision" | S1c:105; E2:604-607; E1:290-295; B5:263, :424 |
| **C-8** contact string | "U-014 as recorded" | Connectors that need a contact string send the operator's **personal name and address** to third parties. F-344 shows this already happened once, at EDGAR | S1c:377; PLAN:209; UNIVERSE_DISPOSED.csv (F-344) |
| **A-15** execution model | "same as rec." A-15 says agents pause only at "unnamed production mutations" | **49 chain rows** carry "named mutation (A-15 [A-15] -> default a): no per-step go". The 49 include the 5,278-subject re-key (P35.24, whose catalog contract said "operator go (hosted re-key run)"), lineage rematerialisation (P35.25), derivation collapse (P35.46), evidence-store off-instance copies (P37.3), dossier live captures (P37.16) and the raw-archive write (P37.36). This contradicts S2:264, "When nothing is pre-authorised … each named mutation becomes an in-ticket pause", and OM-18 | S1c:115; CSV P34.3…P37.56 (`grep -c` = 49); `data/ticket_catalog.csv` R11-CONF-03b |
| **B-22** | "as recommended", 58 K-row design decisions | Includes Part VIII and publication choices: D-K1-7 "My location" button (see SIG-GOV-017, which bans an "is a camera watching me right now" surface); D-K7-6 agenda titles that may name people; D-K8-1 excerpt quotation; D-K8-4 showing the 255 synthetic run-record artifacts; D-K1-6 single-source sites shown by default; D-K4-3 2,482 county pages | S1c:341, :663-720; spec `:6544-6552` |
| **A-17** | "a" (ratify) | Amends SIG-CHART-025 (the spec charter) and fixes D3 §5 as the announce gate on silence | S1c:117; PLAN:296, :714 |
| **C-3** | "U-013 wording used" | U-013 is about counsel. Used as the answer to item (3), robots, it records words the operator never said about robots | S1c:372; U-013 |
| OM-20 list in a check-in | unspecified under `continue` | A one-word `continue` may be read as approving the next 13–26 pre-authorised rows | S2:296, :304-306 |

This is precisely the question the lens asks: does a default amount to the agent deciding for the operator on publication,
rights or Part VIII? For A-5, C-8, B-22 and A-15 it does.

**Fix:**
1. Rewrite each default to "no action; the dependent rows wait":
   - **A-5:** honour every explicit disallow and every rights reservation until the operator answers in their own words.
     Stop fetching the 103 disallowing hosts. This keeps the conduct within SIG-INGEST-037/046c.
   - **C-8:** "alias first". No request that needs a contact string is sent until the `contact@` alias exists or the
     operator answers. Restore P16's original "stop and record".
   - **A-15:** "pause at every named production mutation unless an OM-20 list approved verbatim covers it". Rewrite the 49
     CSV notes from "default a: no per-step go" to "in-ticket pause unless listed in an approved OM-20 list".
   - **B-22:** "none accepted; each K row waits". At minimum, split out D-K1-7, D-K7-6, D-K8-1, D-K8-4 and D-K1-6 as
     explicit lines. D-K1-7 also needs a written SIG-GOV-017 analysis.
   - **A-17:** "D3 order adopted for sequencing only; no spec amendment".
   - **C-3:** "not recorded; the record says the operator has not given own words".
2. Add to §4.4 a column "acts on silence? (must be no)" and a mechanical check in S1b's checker. The check: every default
   whose kind is publish, rights, Part VIII, identity disclosure or production mutation must be `wait`.
3. Make S5-2 explicit: under `continue`, the OM-20 list is **not** approved. It needs its own verbatim line.

### TS-03 — The honesty republish (P34.17) ships a new false public claim

**Problem.** P34.17 ships the H-4 wording "already shipped in P34.17 (H-4)" (CSV P34.45 notes). That wording is L3 §5.3:
*"SIG no longer uses these labels to decide merges. It merges only records that are copies of one upstream record, which is
checked automatically on every release (see [Quality](/quality/))."* (`design/L3-confidence-program.md:602-610`).

When P34.17 publishes, none of this is true of the data on screen:
- The live figure "223,901 resolved sites" rests on "8,724 merges including agent-gated inferential tiers" (L3:535).
- L3 required that "the live posture changes first, in wave 0 (CONF-02)" (L3:536).
- The plan places that ER re-run, P34.45, *after* P34.17. Its publication "rides the next republish/release", which is
  P35.63 in 11B (CSV P34.45; PLAN:455, :829).
- The derivation census does not exist until P35.46.
- `/quality/` does not exist until P37.45 (11D), so the link is dead for about seven weeks.

The plan's own §5.1 calls this wave the removal of false claims (PLAN:357-383). PLAN:455's "Honest evaluation posture ships
in 11A" therefore overstates.

**Fix:**
1. Republish #1 ships only text true of the 09-27 data. Agent-drafted example: *"Matching quality: development evidence
   only. 540 record pairs … were labelled by an AI model … No person labelled them. The records on this site were matched
   by rules that were partly tuned on those labels; SIG is changing them so that only copies of one upstream record are
   merged."*
2. No link to `/quality/` until P37.45. The present-tense merge sentence moves to the first publication after P34.45's ER
   re-run.
3. Add a CSV edge "P34.45 publication → the H-4 present-tense sentence".
4. Generally: any republish that changes a status sentence must cite the probe-run record proving it true (DRAFT-MEM-7,
   PLAN:682), and the 11A live probe checks it.

### TS-04 — The Part VIII S0 (personal handles, RI-01) is scoped too narrowly to be "closed live", and its recommended timing keeps it public longer than needed

**Problem.** RI-01 (F-097/F-131) is personal ArcGIS account handles in public identifiers. One token is "an individual's
email-derived username" (`findings/FINDINGS.csv` F-131). These are "personal identifiers unrelated to institutional
conduct", which SIG-PUB-002 excludes from every tier (spec `:6236-6250`).

The owning row renames ~31 `camreg_*` **source ids** with an alias map. Its acceptance is "no personal handle in any public
id, export or page" (`data/ticket_catalog.csv` R11-SAFE-01). It leaves out:
- **The public repository.** `connectors/src/connectors/data/camera_registry_targets.toml` holds the handle tokens and
  **41 e-mail-shaped ArcGIS owner strings**, e.g. the notes at :849, :1059 and an `agency =` value at :3921. The same 41
  strings are on `origin/main`, where the file was last touched by `c54994ed`. The file is on 96 remote branches, and git
  history keeps them.
  The repository is public (PLAN:122). P37.55 plans an **irreversible** Software Heritage deposit of that history.
- **The public bucket.** The 09-27 release lives in the world-readable, anonymously listable `sig-public`
  (`design/J3-transparency-design.md:100`; F-387 cites `gs://…-sig-public/sig_graph/sites.*`). The plan freezes that root
  until LATER-20, "90 days after P35.59" (PLAN:1285). P34.10 "never deletes release trees" (CSV P34.10).
- **Other id and value fields.** Handles also appear in **target ids** (`research/L2-graph-quality.md:20-21`), and target
  ids are embedded in subject ids (`traffic_camera:<source>:<target>:<ref>`, F-370). One handle is a live
  `camera_operator` **value** (L2:285-286), which the plan fixes only in P35.26 (11B).

**Timing.** The operator's "planned … not done now" decision was received **before 17:10:49Z**
(`META_PLAN.md:1227`, correcting "18:2xZ"). The handle findings were raised at 17:01:57Z (code) and 17:46:42Z (live), and
B-1 calls them "the two S0s outside §7.1's list" (S1c:320). So the operator has never been asked whether to remove them now.
The plan nonetheless recommends CF-15: the rename rides republish #2, ≥ 2026-10-13T12:00Z, "≈ 5–7 days after republish #1"
(PLAN:345-346). G2 had proposed a web-only **display alias** in republish #1 (`design/G2-activation.md:180`).

AR-3 already exempts emergency takedowns (G2:105). The Track 0.2 precedent shows a removal-only bucket-prefix action takes
a minute. RI-05 (`/visual-language/` fixture facts about Oklahoma City PD, Flock and the Oklahoma County Sheriff) is in the
same position.

**Fix:**
1. Add a Part-A line (**A-0, time-critical, asked; no default action**). It offers a Track-0 removal-only exception now:
   - remove the `/visual-language/` prefix, as was done for `/curate/`;
   - hide handle-bearing source/target ids and the handle `camera_operator` value on web pages through a display filter
     in a copy-only republish.

   There is no default: the line must be answered, and silence is never recorded as the operator accepting the risk.
2. Recommend "RI-01 first" (B-3) over CF-15.
3. Widen R11-SAFE-01's scope and acceptance:
   - source ids, target ids, subject/claim/permalink ids, `camera_operator` values and tile properties;
   - every anonymously readable object in `sig-public`, including the 09-27 tree: withdraw, or replace with a tombstone
     manifest per G3's withdrawal model, now and not after LATER-20;
   - the repo's working tree: registry notes reduced to neutral ids. Records the planning context needs move to a
     gitignored or restricted location.
4. Give the operator a decision line on git history: rewrite, or accept and disclose. P37.55's SWH deposit and any Zenodo
   package wait on that answer.
5. The 11A acceptance probe crawls site, API, tiles, `sig-public` listings and the repo tip for the handle list kept in
   `docs/build/logs/next-phase/C3/personal_like_ids.txt` (gitignored).

---

## MAJORS

### TS-05 — "Exactly one requirement waiver" is not true: several MUSTs are relaxed by "amendment" or operated waiver, and the announce gate omits them

**Problem.** PLAN:733 says only SIG-EVAL-004 (C0–C2) is waived, and that SIG-PUB-008 "stands". But:

| requirement | what the plan does instead |
|---|---|
| SIG-GOV-012/013: legal home and legal-defence resources **before public launch** (spec `:6521-6530`) | Rewritten to "interim individual legal home" (PLAN:709; ADR-165 PLAN:785). Its revisit trigger is "on announcement", yet GATE-ANNOUNCE (PLAN:1228-1236) does not ask it |
| SIG-GOV-015: an editorial board for officer naming and **sensitivity classifications**, "not … whoever happens to hold commit access" (spec `:6537-6542`) | Amended to "interim single-maintainer editorial authority" (ADR-164) |
| Go-live HG-11 "two reviewer roles + written concurrence (SIG-PUB-008)" (`research/E1-contradictions.md:72-95`) | Every Class-S "HG-11 readout" in the round is the operator's sole decision. G3 says this "claims nothing about reviewer independence" (G3:430-432), but the plan lists no waiver |
| SIG-UI-042 "Release is blocked until every finding is dispositioned" (spec `:5997-6001`) | G2 H-1 "move[s] the SIG-UI-042 gate so a truthful record does not fail the build" (G2:180), and dossier releases continue. That is "waived, not satisfied" again (E1-01) |
| SIG-GOV-001/002: one-click intake; no submitter identification (spec `:6460-6467`) | Intake is e-mail-only to the operator's personal address until after the announcement (B-8; P37.59 default). A sender must disclose an e-mail address, so GOV-002 is unmet at launch |
| SIG-GOV-008: true deletion needs two-person authorisation (spec `:6492-6495`) | Not mentioned; unmeetable with one human |
| SIG-LIC-009 / SIG-INGEST-037 counsel clauses | Amended to "operator-accepted rights basis" and "robots narrowed" (PLAN:711-712) |

The universe check cannot see these because they are classed as "spec-amendment", not "adr-waiver".

**Fix:**
1. Re-class each row above as `WAIVED(ADR)`, with the operator's words, compensating controls and a revisit trigger, or
   keep it `owed` with a trigger. §6.5 then lists them all.
2. The `check_dispositions.py` rule: a spec amendment that removes or weakens a MUST is a waiver.
3. Add to GATE-ANNOUNCE (PLAN:1228-1236) a "spec MUSTs unmet at launch" list the operator signs verbatim. It covers at least
   GOV-001/002/008/012/013/015, UI-042, the HG-11 two-reviewer role and the Q-29 revisit (TS-21).

### TS-06 — Blanket rights rules are re-applied, and the mirror of a terms-forbidden vendor portal escapes the "never from vendor hosts" rule

**Problem.**

**(a) GL-GATE-07.** It exists only in the LEDGER, recorded as *"We should ungate the … 257 … err on the side of
approving"*, in the same commit (`c2055d96`) that deleted the 53 GATE DECISIONS rows (`research/B2-append-only.md:145`).
- **ADR-169** makes it a spec rights basis: "GL-GATE-07 recognised for Tier-1 families" (PLAN:789, :711).
- **A-7** recommends "**a** on all" Tier-1 batches (PLAN:287). For RB-01 (38 US agency layers) that is I7 option **a**,
  "flip all under GL-GATE-07 US", with "new facts first? **no**" (`design/I7-rights-packets.md:37`). Most members have
  terms "none captured", and the cited precedent is `camreg_txdot_rep_tx`, the row A-8 now restricts.
- **E2's guardrails are missing:** "terms captured verbatim per source", and re-deciding the out-of-rule rows
  (`design/E2-governance-options.md:687-718`).
- B5 lesson 2 names this exact failure: "Each later gate answered 'under GL-GATE-07' instead of looking at the new set"
  (B5:284).

**(b) Robots.** A-5 recommendation **b** keeps fetching US hosts that explicitly disallow SIG, including the PrimeGov
**vendor** platform (E2:604-607, :1103).
- It limits rights-reservation refusals to "non-US hosts".
- SIG-INGEST-046c says an affirmative reservation "MUST be honoured as a refusal", with no jurisdiction limit (spec `:4285`).

**(c) Flock and Axon.** Flock's portals are vendor-hosted, and "ToS forbids bulk extraction". The Flock API terms forbid
"extract, scrape, or export data in bulk" (`connectors/src/connectors/data/sources.toml:321-333`; I7:319). Axon's terms say
"no robots, spiders or page-scrape" (`research/I3-alpr-networks.md:312`).

`eyes_on_flock` is a `MIRROR` of those portals. It has `ingestion_permitted = true`, is "FLIPPED 2026-09-16 (GL-GATE-06
blanket disposition)", and its `rights_reviewed_by = "maintainer (delegated)"` (sources.toml:345-366). It already supplies
474,184 sharing edges (I3:92-93). The plan extends it: B-25 (S1c:344) and I8:547/633.

So the plan's rule that Flock facts "come only from agency pages, procurement records and statutory reports, never from
vendor hosts" (PLAN:482-484) is not what the plan does. Laundering vendor-portal data through a third-party mirror is not
covered by "never fetched", and R-10 (PLAN:1253) is silent on mirrors.

The operator's US-nationwide Flock/Axon priority (U-007) creates pressure in exactly this direction. The plan should say
plainly how deep Flock/Axon coverage can lawfully go (D3:218 hints at it) rather than leave it to a mirror.

**Fix:**
1. ADR-169 drops "GL-GATE-07 recognised". Each Tier-1 batch line carries captured terms per member (I7 option **b**). Members
   with "none captured" stay `ingestion_permitted=false` until captured.
2. GL-GATE-07 and GL-GATE-08 are re-asked in the operator's own words (OM-09) before any extension.
3. A-5 conforms to SIG-INGEST-046c: reservations are honoured everywhere. Recommend honouring explicit disallows on vendor
   platforms (PrimeGov) at minimum.
4. State the vendor rule as "no Flock/Axon fact whose only provenance is a vendor host **or a mirror of one**". Re-decide
   `eyes_on_flock` and B-25 as an explicit rights line, quoting Flock's terms and Eyes on Flock's CC-BY-SA-4.0 basis, and
   name the delegated 2026-09-16 review as such.
5. Add a §5.5 sentence on the coverage ceiling the terms impose on Flock and Axon. The acceptance "Flock, Axon …
   exist as entities with dated, sourced agency links" (PLAN:508-509) must then be met from agency, procurement and
   statutory origins only.

### TS-07 — Part VIII at rest and screen ordering: stored person-level bytes, an unwired residential demotion, and activation before redaction

**Problem.**
1. **Residential demotion is not wired**, and no row owns it. I8: "The residential demotion exists but is not wired … owed
   anyway, because the same exposure ships today through the ArcGIS republish" (`design/I8-acquisition-design.md:157`,
   :381-382). `policy/src/policy/sensitivity.py:57` has no non-test caller. "residential", "coarsen" and "PUB-005" appear
   in no row of `data/round11_plan.csv` or `data/ticket_catalog.csv`. All 227,335 published points are `full_precision`
   (`design/K1-map.md:419`). SIG-PUB-004/005/013 (automatic C3 demotion on residential-parcel intersection; never publish a
   residential candidate) are MUSTs (spec `:6291-6311`, `:6343-6345`). Wave C makes OSM the national ALPR origin
   (≈ 154k objects), and Wave B adds camera "registers".
2. **Stored Part VIII bytes.** Raw OCFL captures keep "OSM `user`/`uid`, Eyes on Flock free-text search reasons, all ArcGIS
   attributes" (`research/J4-redistribution-matrix.md:519`; F-406). SIG-PUB-002 says "MUST NOT store, in any tier"
   (spec `:6236`), and SIG-PUB-003a/b forbid holding audit operator ids or per-search rows. F-406 is routed only to the
   **publication** row P37.36. Meanwhile P37.3 makes **off-instance copies** of the evidence store, which multiplies the
   stored copies.
3. **Activation before redaction and capture-tier fixes.**
   - Wave B activation P36.12 (records genres: statutory disclosures, CCOPS, council, procurement) comes before the
     redaction pipeline P36.15, and P36.12's dependencies name neither P36.15 nor the naming gate P35.28 (CSV P36.12).
   - The capture writer "hard-codes storage_tier='public'" (F-400). Its fix, P35.31, is not a dependency of P35.61 or
     P37.16, the rows that write actual captures (CSV P35.61 deps: P34.46; P34.22; P34.43; P34.6; P35.46; P35.15).

**Fix:**
1. Add an 11A row "Part VIII at-rest audit". It scans the evidence store for the I7 S1–S9 classes, seals or suppresses per
   SIG-GOV-007, and records counts. P37.3 copies exclude, or separately encrypt, sealed material.
2. Add an 11B row wiring the residential demotion (SIG-PUB-005/013) before P36.12 and P37.2.
3. Add hard edges: P35.31 → P35.61 and P37.16; P36.15 and P35.28 → P36.12. The B-32 screen lanes S4/S6/S7 must be
   implemented and verified before their families activate.

### TS-08 — Record corrections are internally inconsistent, and the restoration can reintroduce false dates

**Problem.**
- **Re-confirm or annotate.** E2-17 recommended that ACCEPT-R8/R10 be "re-confirmed … against their exact text" (E2:893-902).
  B-4 instead "annotated … rather than re-confirmed" (S1c:323). SEED-08 then plans "operator-confirmed addenda for the signed
  GATE-G3 and ACCEPT-R10 readouts (OP-18)" (PLAN:1339-1340). That **omits ACCEPT-R8**, and it has the operator confirm,
  after the fact, agent-drafted claims about what they saw: the original pattern again.
- **Unasked question.** No line asks whether ACCEPT-R10's "34 MET" acceptance still stands, which B5 says decides
  re-confirmation versus supersession.
- **SEED-06 restores false dates.** It restores the 53 deleted rows "byte-for-byte" from `c2055d96^` (PLAN:1335), under the
  caption "Nothing below is re-decided" (B2:225-232). The block includes rows dated "2026-09-10" that were committed
  2026-09-13T19:40Z (B1 row 2, the Round-3 "chain date"). They are not in `date_drift.csv`, which is keyed to HEAD lines, and
  the G1 guard rejects only *future* dates. The block also includes GL-GATE-01…05 "delegated … to Devin's judgement", the
  GL-GATE-06 blanket rule, and "APPROVED by counsel (operator-reported)".

**Fix:**
1. B-4 and SEED-08 must agree. Either annotate all three (R8, R10, G3) with B7's facts and no operator addendum, or ask the
   operator a dated question now: "Does ACCEPT-R10's acceptance stand? yes / no / superseded". Record the answer with
   today's `date -u`. Never have the operator confirm text describing their 09-27/28 state of mind.
2. SEED-06 appends, after the restored block, a dated annotation table listing every restored row that is (i) clock-false,
   (ii) a blanket or delegated decision, or (iii) a counsel claim, with B1/B5/E1 references.
3. Extend `date_corrections.csv` to the restored block. Add a G1 mode that checks restored dates against `git blame`.

### TS-09 — "Counsel" residue survives in the plan's own vocabulary and in the public repo

**Problem.**
- **Plan vocabulary.**
  - OM-08 says "operator-reported counsel is `operator-reported`" (PLAN:221).
  - ADR-170 records "ADR-106's clearance … as operator-reported" (PLAN:790).
  - The operator said: *"'counsel' so far is just me …, we don't have counsel"* (U-013). Neither "operator-reported counsel"
    nor "clearance" may survive.
- **Public repo.** `docs/adr/ADR-086-hg02-counsel-resolution-…md` (filename and body: *"On 2026-09-16 counsel resolved
  HG-02"*) and ADR-106 stay public. T1's status-line list (PLAN:1318-1320) does not include them, because ADR-167 only
  "qualifies" them.
- **Label wording.** ADR-167's "labelled" does not fix the label's wording. E2 drafted it: *"No lawyer's written opinion has
  been obtained; nothing here states that this publication has been cleared by counsel."* (E2:569-571)
- **`main`.** P34.16's repo honesty fix has `live_stage` "none" (CSV P34.16), so public `main` keeps the false governance
  text until the operator's merge sitting.

**Fix:**
1. Replace the wording with "the operator's own determination (no counsel)".
2. Add `Qualified by ADR-167 (<date -u>)` status lines to ADR-086 and ADR-106. This is allowed, because status lines are
   appended, not body edits.
3. Pin E2's label text, which must be operator-confirmed, into ADR-167 and the release manifest.
4. Tell the operator (OP-08) that the public `main` stays false until merged, so the merge sitting is a safety item, not
   only housekeeping.

### TS-10 — Public copy and success criteria claim more than the plan's evidence supports at ship time

**Problem.**
- **Landing text.** D3 §1, confirmed via C-4, ships in P36.64 (11C) and is a GATE-ANNOUNCE requirement (PLAN:1234). It
  states as present fact:
  - "who operates them": 74.2 % of subjects name a publisher as operator (L2:284-285);
  - "Every claim links to its evidence": 0 of 2,782,187 bindings reach bytes (L2:312). The round target is byte binding
    only "for sources re-run in P35.61" (PLAN:469);
  - "disagreements between sources stay visible": every multi-claim value is "uncontested", and 2 contradictions are
    recorded (L2:49, :199). Contradiction recall is measured only "on the synthetic set" (PLAN:469);
  - "every gap is labelled": not true until the typed-absence rows land.

  (D3:26-33.)
- **Narrowed lists.**
  - The plan's "Not claimable" list (PLAN:458-459) keeps 5 of L3's 11 rows. It drops organisation identity and "N agencies",
    candidate recall, camera existence and operation, capture–recapture, maintainer independence, and centrality/rankings
    (L3:491-501).
  - The 11A probe checks five words (PLAN:382-383). C6 also lists "reproducible", "Reviewed", "Releasable" and "complete"
    (`review/REVIEW_SYNTHESIS.md:1270`).
- **Vacuous or weakened criteria.**
  - "M-1b lower bound ≥ 0.98" (PLAN:1190) is vacuous under the A-6 default, because nothing is collapsed and there is
    nothing to sample. Its "0.98" echoes the certification figure L3 forbids (L3:493). Separately, B-26's "the dedup is
    published" can be met with no deduplication.
  - The `/quality/` default is "passing checks only shown" (CSV P37.45; B-31 default S1c:350). That contradicts L3:575
    ("Failing and ratchet checks are shown, not hidden") and PLAN:471 ("`/quality/` live with every check"), and §4.4 does
    not list it as a descope.

**Fix:**
1. Bind each landing-copy clause to a measured check: GQ ids, with a probe-run record no more than 24 h old at the publish
   that ships it. Until a clause is true, ship the conditional form, e.g. "Every claim links to the record of how SIG
   obtained it; links to the source documents themselves are being added".
2. Restore L3 §4.5 in full in §5.4 and in the 11A and P38.1 probes.
3. Add §4.4 rows for A-6 → M-1b "not attempted", B-26 "met only with intervals", and B-31 → `/quality/` "passing-only:
   descope".

### TS-11 — Agent work is still committed under the operator's name, and the plan's identity-exposure analysis ignores it

**Problem.**
- **Authorship.** "478 of 480 non-merge commits are authored 'Steve Vitali' whatever the harness, so git authorship cannot
  attribute agent work" (B5:62-64; F-37). This planning branch continues the practice: `c3e37654`, which carries Claude's
  trailer, is authored with the operator's identity.
- **Trailers.** B5's OM-01 required "Every commit carries a trailer naming the harness" (B5:328, :400). The plan's OM-01
  summary keeps only a `harness:` key and run ledgers (PLAN:215-216).
- **No authenticity check.** L3 notes that the operator's words "reach the repo through agent sessions using their git
  identity (B4 §2.3: no repo check can prove authenticity)" (L3:447-448). A-16's default is the status quo (PLAN:295).
- **Identity exposure.** §12's B-16 analysis says the operator's address "appears verbatim in three planning files"
  (PLAN:1167-1170). It omits that every public commit's author metadata already carries it. The redaction choice is
  presented without that fact.

**Fix:**
1. OM-01 is restored verbatim. Every agent commit carries the harness/model trailer, and a G-check fails a Round-11 PR
   containing an untrailered agent commit. Ask the operator whether agent commits should use a distinct author identity.
2. A-16's recommendation stays "yes now", and its default is stated as a disclosed risk.
3. B-16 states the commit-metadata fact so that the redaction decision is informed.

### TS-12 — S1 false public claims stay live through 11A with no interim removal; the operator's "not now" is read more widely than it was given

**Problem.**
- **Permalinks.** Unpinned "permalinks" (F-07/F-099) stay until P35.42/P35.63, in 11B (CSV P35.42). C6's QW-5, "drop
  'reproducible' until pinned", has no owning row, although B-1 scopes "C6 QW-1…15" (REVIEW_SYNTHESIS:1230; S1c:320).
- **Rows live until republish #2** (≥ 10-13T12:00Z):
  - 61,603 rows with required attribution left empty (G2:61);
  - map credits to "SIG contributors" (F-111/F-138);
  - the 5,267 forbidden-terms, NC/ND and demo rows (A-8; P34.19 "publication rides P34.21").
- **API.** The `/terms` text naming an "editorial board" and "counsel" (F-189) and the false dossier API (F-130) stay until
  P34.46 (≥ 10-14T14:00Z).
- **Unused and rejected options.** AR-3 exempts emergency takedowns (G2:105), but no row uses the exemption. E2's interim
  compartment withdrawal is declined by default (E2:285-298).
- **The operator's words.** *"…this work should be planned/specified in the next round of tickets, not done now"* was
  given before 17:10:49Z about the suggestions then on the table (META_PLAN:910-911, :1227). It is not a standing refusal of
  all interim removal. Track 0.5 was later approved as an exception.

**Fix:**
1. Fold these into TS-04's A-0 line as one explicit, asked, removal-only option. Examples: drop "reproducible" and
   "permalink" wording; unlink or withdraw the 5,267 rows and the misattributed objects; change the API `/terms` text through
   a config-only roll if one exists.
2. The default is "not done; risk recorded as the operator's".
3. Give QW-5 an owner in P34.11 or P34.13.

### TS-13 — The OM-20 lists and B-9 reach publication and Part VIII despite "publication is never pre-authorised"

**Problem.**
- **Lists.** The pre-authorisation lists include public-API rolls that change what the public sees: P35.57 (API release
  parity, the real jurisdiction dossier API), P37.20 (release-pinned bbox API) and P37.42 (API parity) (CSV). They also
  include "capture runs under answered HG-03 lines", which are dossier live captures needing a Part VIII sign (P37.16;
  E4-B2), and "the raw-archive write" (P37.36) (S2:812-820). PLAN:247 says "publication is never pre-authorised".
- **B-9.** The Class-R standing go has no expiry: "I can revoke it at any time" (G3:451-456). OM-10 requires one
  (B5:363).

**Fix:**
1. Add to OM-20's never-pre-authorised list: any roll that changes a public route's response, and any capture or archive
   write touching a Part VIII-screened family.
2. Give B-9's standing go an expiry: the next sub-round GATE or 30 days, whichever is first. Add automatic voiding on any
   ratchet regression, any Part VIII screen change or any new source.

### TS-14 — Headline counts in §0 overstate closure and certainty

**Problem.**
- §0 says "Every S0/S1 finding (113) has exactly one owner, and the 76 owner units … all sit in 11A ∪ 11B" (PLAN:50-51).
  But §9.4 places three on S5 decisions (F-31 → A-4, F-191 → C-3, F-386 → A-3) and one as already done (PLAN:976-977).
  Under the defaults, F-31 and F-386 stay open.
- "0 errors" (PLAN:52) is a structural checker result, the kind F-27 warns about.
- "Honest evaluation posture ships in 11A" (PLAN:455): see TS-03.
- "This planning round repeated the date drift once" (PLAN:163): F-074 counts 24 late stamps in 17 commits.

**Fix.** Restate each with its qualifier, for example "113 have exactly one disposition; 109 land on 11A/11B units, 3 on
S5 decisions (open under their defaults), 1 already done". Write "structurally valid (checker)" rather than "0 errors". Use
"24 stamps in 17 commits".

---

## MINORS

### TS-15 — A corrected false stamp is propagated

PLAN:74 and :260 still key a ratified decision to "18:2xZ". `META_PLAN.md:1227` already corrects it to "received before
17:10:49Z (e5725b7b)". T5 copies GATE rows from this plan (PLAN:1377), so the false stamp would enter the control ledger.
This is B1 row 36's propagation pattern.

**Fix.**
- Use "before 17:10:49Z (git `e5725b7b`; F-074)".
- P34.1's 2026-10-19 deadline (PLAN:49, :872) should cite its source, the GitHub runner notice
  (`design/H2-branch-ci.md:113`), so it is not confused with the false 2026-10-19 records.

### TS-16 — The provenance header is stale

PLAN:11-12 says "nothing was committed". The draft is committed as `c3e37654`, which also changed `META_PLAN.md` (+7
lines).

**Fix.** Re-word it as "this row committed nothing; the orchestrator committed it as `c3e37654`".

### TS-17 — B7's confidence is dropped

PLAN:1001 says "all 480 chain commits attributed". B7 says attribution is "high-confidence for 477 of the 480", S0 is
"medium, surface unknown", and the model behind `swe-2-high` is unknown (B7:43-44, :157).

**Fix.** Carry the qualifiers.

### TS-18 — B-2's class permission is unbounded

"Removal-only corrections and 'not yet performed / not operating' notices without per-text confirmation" (S1c:321) has no
fixed sentence set and no expiry. The notices are new public sentences, and META_PLAN §2 says agent text ships only on
verbatim confirmation.

**Fix.** Ratify the exact notice strings once (sha256 list). Only listed strings ship without per-text confirmation, and the
permission expires at GATE-G4.

### TS-19 — C-3(2) recharacterises a past tentative statement

C-3(2) asks the operator to confirm that "let's defer all the human review steps and proceed" (09-28) *was* a deferral.

**Fix.** Record the answer as a statement made at S5's `date -u` ("I now confirm…"), never as a 09-28 decision. Add a test
in G4.

### TS-20 — The "held-out" search set can be agent-written

B-28's default is "a separate agent writes it, labelled" (S1c:347). Yet the acceptance reads "held-out ≥ 80 % top-3"
(PLAN:563), which suggests independence.

**Fix.** Label the metric "agent-authored held-out set" unless the operator writes it (OP-21).

### TS-21 — The personal address as public contact at announcement

Q-29's revisit trigger is "alias when volume or exposure grows" (META_PLAN:927). The announcement is that moment, but
§13.5 does not ask it. Privacy-harm reports, which SIG-GOV-003 prioritises, will land in a personal mailbox with only a
do-not-send notice (G2 NEW-5).

**Fix.** Add a GATE-ANNOUNCE line: "Q-29 revisited: keep the personal address, or require the alias (OP-10) before
announcing".

### TS-22 — The operator walkthrough is counted without its label

§13.2 #1 and §13.5 count "both walkthroughs (agent and operator)" as a pass criterion (PLAN:1185, :1232), without the
non-independence label that §11.3 (PLAN:1135-1138) and L3 §4.5 require.

**Fix.** Write "operator walkthrough (maintainer, not independent)" wherever it is counted.

### TS-23 — Withdrawal totals are not stated

A-8 withdraws 5,267 rows, and restricting `camreg_txdot_rep_tx` removes about 2,821 more (J4:221-222, :516). The plan never
states the combined ≈ 8,088, so the operator answers A-8 without the full public effect.

**Fix.** State both counts on the A-8 line and in P34.19's acceptance.

---

## Lens-by-lens summary

| check | result | findings |
|---|---|---|
| (1) Honesty: planned public claims vs evidence; S0 removed before new promotion | **fails** at republish #1 (a new claim), on the landing copy and in the criteria; S0 closure scope too narrow | TS-03, TS-04, TS-10, TS-12, TS-14 |
| (2) Human-work integrity | **mostly holds** (no HUMAN rows; agent labels segregated; OPCHECK disclosed). Gaps: commit authorship, the walkthrough label, the agent-written "held-out" set | TS-11, TS-20, TS-22 |
| (3) Gate integrity vs B5 | **fails**: the fast path, acting defaults, A-15's 49 rows, `continue` | TS-01, TS-02, TS-13 |
| (4) Part VIII and privacy | **fails** on handles (repo, bucket, ids), residential demotion, at-rest bytes and ordering; P16 default | TS-02, TS-04, TS-07, TS-21 |
| (5) Licensing and rights | **fails** on the GL-GATE-07 extension, robots and the Flock mirror; attribution fixes are scheduled (P34.21) | TS-06, TS-12, TS-23 |
| (6) Record integrity | **partly**: the ADR-146 approach is right, but R8 is omitted, confirmation is post hoc, the restored block keeps false dates, and a stamp is propagated | TS-08, TS-15, TS-16, TS-17 |
| (7) Governance honesty | **fails** on hidden waivers and counsel residue; the legal home is absent from the announce gate | TS-05, TS-09 |

## What holds (no change needed)

- **Human work.** No Round-11 HUMAN rows. Independent evaluation stays owed and is never waived (PLAN:1118). Agent
  walkthroughs are `agent-verified`, never "user-tested" (PLAN:1211). OPCHECK is blind-first, verbatim and labelled
  non-independent (L3 §4.4).
- **Never pre-authorised.** OM-20 keeps HG-11/Class S, ING-GO, HG-03, P34.46, P35.61 and spend above $300 out of every
  list (PLAN:236-238).
- **Conservative rights defaults.** A-8, A-9, B-32…B-39 default to no flip, or to withdrawing or restricting. An unanswered
  HG-03 line never flips a source (PLAN:861-862).
- **Officer naming.** No one is named; the gate is default-deny (P35.28; ADR-163).
- **Prior signatures.** The GATE-G3 signature is superseded, not transferred (PLAN:630, :905).
- **Push policy.** The planning branch stays local until T6, with a pre-push secret and Part VIII scan (B-16).
- **Money.** It is reported separately and never invented. Nothing planned exceeds $300/mo without a go (PLAN:1070-1078).

## Closure conditions for `reviews/REVIEW_CLOSURE.md`

- **TS-01 … TS-04** must be closed by plan text changes before S5.
- **TS-05 … TS-14** may close by plan text, or by an explicit S5 line that shows the operator the issue and its default.
- **MINORs** may close at T1–T4.

Each closure cites the changed PLAN line and, for TS-02, the re-run of S1b's checker with the new "acts on silence = no"
rule.

*End of review. Written 2026-10-01T01:39:35Z (`date -u`).*
