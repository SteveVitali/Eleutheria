# S1c — Operator decision catalog (one-sitting ratification packet)

Row **S1c** of `META_PLAN.md` (Stage P, synthesis). Written 2026-09-30T23:49:00Z (`date -u`) by Claude Code (Opus 5.5)
in the planning worktree `/Users/stevenvitali/Eleutheria-next-phase`, branch `claude/next-phase-planning`, HEAD
`f55d64c3`. Read-only. This row writes only this file and `data/decision_catalog.csv` (one row per decision, 323 rows).

> **Not legal advice (P4).** Where an option carries legal or safety exposure, this packet describes it in plain words.
> It does not say what the law requires. **Recommendations are the agent's. Every decision is the operator's.** Wording
> marked *agent-drafted* ships only after the operator confirms it verbatim (META_PLAN §2). Nothing here pre-answers a
> gate.

**Inputs read:**
- META_PLAN §3, §7, §7.1, §11;
- `feedback/OPERATOR_FEEDBACK.md` (U-001…U-015);
- design notes E2, E4, I7, K0–K14 (their decision tables), K13, D3, F4, L3, B3, B4, G2, G3, H2, I8, J3;
- research notes B1, B6, B7, E1, F1, G1, J4;
- `findings/REGISTER.md`, `review/REVIEW_SYNTHESIS.md`, `data/review_themes.csv`, `data/owed_register_adjudication.csv`;
- one live read: `gh repo view` → `visibility: PUBLIC`.

---

## 0. How to use this packet

**Time budget: about 45 minutes in one sitting.**

| part | what it is | lines | time |
|---|---|---:|---:|
| **A** | Decide before the Round-11 seed. Few lines, high impact, one of them time-critical (A-1). | 17 | ~22 min |
| **B** | Batch approvals, each with a default. Most lines are "as recommended". The fast path is one sentence. | 43 | ~10 min |
| **C** | Informational confirmations: facts the agent found, and texts only you can confirm. | 11 | ~5 min |
| **D2** | One reaction to the 16 most consequential findings: agree/disagree and priority. | 16 | ~6 min |

**How to answer.** One line each: `A-1: a` · `A-4: a except Q-E2-08` · `B: all as recommended except B-13: b` ·
`C-4: confirm` · `D2-05: agree P1`. Where a line bundles several decision ids, "as recommended" answers every member.
The CSV has the member-level options for anyone who wants to answer one id differently.

**Fast path** (agent-drafted; say it, edit it, or answer line by line): *"Part A as recommended. Part B as recommended.
Part C confirmed. D2: agree with all, priorities as proposed."*

**Defaults.** Every line has a *default if unanswered*. It is the conservative option, so the build never stalls on
silence and never acts without an answer. Where the default is "wait for a go" (ING-GO, Class S readouts, HG-11), the
waiting is itself the gate. An unanswered rights line never flips a source: code tickets land those rows with
`ingestion_permitted=false`, and activation skips them (I8 §8).

**Constraints you already fixed, which this packet does not re-ask** (§1):
- ≤ $300/mo without your go;
- no humans besides you;
- no outside contact;
- don't block on counsel;
- the PR chain is not merged by agents.

Options that would break one of these are marked **unavailable**. E2 and F4 were written before D1, so several of their
recommendations changed after U-008, U-011 and U-013. Each changed line says so.

**Counts.**
- Open decision ids: **323**, de-duplicated. A 68 · B 228 · C 11 · D2 16.
- They fold into **87 packet lines**: A 17 · B 43 · C 11 · D2 16.
- Rights lines: E4 22, I7 78 (incl. RG1–5, P1–P4, and C10, which Q-30 already answers).
- K-row design decisions: 84 open across K0–K14 (D-K1-1 is answered).
- A further **23 rows (≈37 ids) are already answered** and are cited, not re-asked (§1).

---

## 1. Already answered — not re-asked

| item | answer on record | where |
|---|---|---|
| Q-1…Q-6 (meta-plan, Track 0.1/0.2, worktree, harness for Stage P, Chrome, D1 format) | approved / answered | §7.1 (GATE-M) |
| Q-11, Track 0.4 (merge the chain?) | agents don't merge; Round 11 builds on the chain; you merge later | §7.1 |
| Track 0.3 MapRoulette key | stays unrotated (accepted risk) | §7.1 follow-up |
| PITR | delegated; enabled | §7.1; TRACK0_RECORD |
| S0 hotfixes + G1 QA-1…QA-10 + `/task/new/` pages | approved in principle, specified as Round-11 tickets, not executed now | §7.1 production-fix decision (A-1 asks only about **timing**) |
| Alert routing (G1 §7 Q2) | your address | §7.1 |
| Q-8 human work | no humans besides you (U-008) | §7.1 D1 table |
| Q-10 / Q-23 cost ceiling | ≤ $300/mo; up to ~$1,000 only with your explicit go on a shown trade-off (U-008). A-2 asks only what the ceiling *covers*; B-11 asks the disk cap | §7.1 |
| Q-26 who gave the "counsel" answers | you; there is no counsel; don't block on counsel (U-013) | §7.1 |
| Q-28 recruiting; outreach; records-request sending; contribution-back | no: "no one should be contacted outside the project" (U-011). This also answers D-R7.2-SEND, D-P21.7-1, HG-08 posting, E4 R1c/R2b-b/R4d-b and I7 "seek consent" options | §7.1; U-011 |
| Q-29 public dispute contact | your personal address, for now | §7.1 |
| Q-30 project contact string | your name + address; plan a `contact@` alias (U-014). OD-04 asks whether to create the alias first | §7.1; P16 amendment |
| Q-20 known-missing sources | US-nationwide Flock, Axon and other vendors; high-quality sources (U-007) | §7.1 |
| Q-18 landscape scan | moot: C5 ran time-boxed | §11 |
| U-001 "what SIG is for" | confirmed | OPERATOR_FEEDBACK |
| Q-D1-02 audiences | advocate first + journalists + organizers (U-002) | §7.1 |
| Basemap (D-K1-1; reverses Round-9 Q8) | yes: you asked for a real map (U-003.1). ADR at T1 | §7.1 U-003 table |
| Launch | announce "when the time is right" (U-009); D3-Q5 sets the gate | §7.1 |
| Autonomy principle | maximal agent autonomy, with money transparency and no outside contact (U-011). A-15 sets the mechanics | §7.1 |
| Stream I/J/K/L scope | added at your request | §7.1 |
| Q-B5-1/2/3 (who ran Round 10, readout timing, the P31.5 pause) | answered by B7 from session records. C-1/C-2 ask you to confirm the recorded facts; B-4 records the true times (Q-B1-2) | B7 §0 |
| Q-B1-1 (read-only sqitch query on hosted `sig-pg`) | not an operator decision: within the clarified P3 read-only scope; S1b/T2 runs it | META_PLAN §11 A2 entry |
| D-R10-USERS-1, D-R6.1-EVAL, D-P30.2b-2 (human markers) | no participants or labellers (U-008/U-011); they stay owed on trigger T-EVAL-IND, dispositioned through A-6 | L3 §6 |

---

## 2. Part A — decide before the Round-11 seed

Answer each line with a letter or "yes/no". Details for each line follow the table. "$/mo" = the monthly cost
difference versus doing nothing (inference unless marked).

| # | decision | rec. | if unanswered | $/mo · exposure | answer |
|---|---|---|---|---|---|
| **A-1** | **Time-critical.** Track-0 exception now for QA-3 (alert channel), QA-4 (uptime/TLS checks) and QA-9 (PITR restore drill), before the 10-01…10-21 first-fire wave and the 10-10T03:35Z OSM replay | **a**: QA-3/4/9 only | no production change; risk recorded as accepted | ≈$0/mo + ≈$0.15–0.40 one-off; additive only | |
| **A-2** | What the $300/mo ceiling covers. Will you create the QA-10 budget alert and billing export now? | **a**: infra only; agent spend reported at every checkpoint · **yes**, now | infra-only ceiling; budget alert as a Wave-0 step | $0 | |
| **A-3** | Q-31: move DNS to Cloudflare for a $0-egress R2 origin (basemap, tiles, downloads, snapshots); egress ceiling $50/mo with kill switch; `contact@` alias via email routing | **a**: yes, all three | no DNS change; GCS basemap; downloads stay unlinked; no alias | R2 ≈$2–13 vs GCS ≈$6–43 + download egress; one-time registrar work | |
| **A-4** | Governance stance (Q-7): adopt the disclosed **single-maintainer, no-counsel** posture package by ADR (PUB-008 stands and no one is named; interim editorial authority + public decision log; interim individual legal home; publication on your recorded risk acceptance, labelled; SEC-003 posture + counts; DB-right basis with guardrails; ODbL map basis recorded as operator-reported) | **a**: adopt all | spec unchanged; false claims still removed; members stay owed | $0; exposure recorded, not removed | |
| **A-5** | Robots (GL-GATE-08): 125 disregarded fetches on 122 hosts (102 PrimeGov municipal hosts, oscn.net, 5 gouv.fr hosts). Re-confirm, narrow or re-gate. Build the opt-out register and reservation refusal either way | **b**: narrow (honour explicit disallows and TDM reservations on non-US hosts; keep the disregard for US public bodies) | GL-GATE-08 stands as recorded; no new robots-disallowed hosts; controls still built | $0; coverage vs blocking/complaint risk | |
| **A-6** | Evaluation (Q-L3-1/2): supersede rows 184–187 with no Round-11 human rows; auto-collapse only mechanically proven copies (C0–C2); **SIG-EVAL-004 WAIVED(ADR-L3-B) for C0–C2, in your own words**; the other EVAL MUSTs stay owed | **a**: yes | no automatic collapse at all; "possible duplicate" ranged counts; EVAL-004 AT-RISK | $0 (no evaluation DB) | |
| **A-7** | Rights stance (Q-19) + **Tier-1 batches**: RB-01…RB-07 and RB-09 (with RG1–5), E4 B1/B5/B6 (Round-10 dossier targets), X3 (46 widening configs) | **a** on all | nothing flips; rows land `ingestion_permitted=false` | +$4–6/mo acquisition (I8); GL-GATE-07-class exposure | |
| **A-8** | Withdraw the "NEW-1" rows (5,267 public rows whose own terms forbid redistribution, are NC/ND, or say "demo"), and restrict the live `camreg_txdot_rep_tx` (TxDOT's origin terms forbid third-party distribution) | **yes**; I7-C1 **b** | withdraw + restrict (the conservative action) | $0; removes the clearest live rights exposure | |
| **A-9** | One statement: are SIG's use and exports **non-commercial**? (Governs Bellevue, Honolulu PD, OPC/Canada.ca, CNIL images, and the live Keizer / TRPA / Cal OES NC rows) | **b**: "is or may be commercial" → NC sources are facts-only pointers | b | $0; avoids an argument SIG cannot settle without counsel | |
| **A-10** | D-K2-1: how the 969 review-flagged organisations become publishable (today every organisation label and all 42,488 organisation edges would be withheld) | **a+b+c**: you review the top 50 by degree (unlocks 96.5 % of edges; ~1–2 h, estimate) + an ADR auto-allowing registry-matched organisations + the rest withheld with typed absence | all withheld; the Organizations section is hidden | $0; your time | |
| **A-11** | D-K13-1: the "global graph" you asked for (U-003.2) is delivered as **aggregated overview graphs** (types, supply, access, funding, operators, governance, adoption; ≤ 3,000 nodes each) + entity ego graphs + `/explore/`, with descriptive views only (no rankings) until evaluation exists | **a**: yes | a (spec-conforming) | ≈$0–5 | |
| **A-12** | D-K0-1: replace the zero-JS-on-content-pages rule with **HTML-first page types**. Records/print 0 JS; content ≤ 20 KiB enhancement; map ≤ 360 KiB; explorer ≤ 120 KiB; search ≤ 60 KiB; every URL shows the same facts without JS | **a**: adopt (new ADR superseding ADR-068/091/097/134) | current rule stands: three islands only | +$5–40 (overlaps K1/K3) | |
| **A-13** | Seed contents (Q-14, Q-B4-1, Q-17): B3 C0–C10 with the deleted GATE DECISIONS rows **restored first**, the date-correction ADR, the ~700-line guard core and F5 PKG-02, so the seed is green; D-R10-MEMORY-1 **split** (B3 option C); Round 11 = P34+/rows 201+ | **a**: yes to all | records-only seed; D-R10-MEMORY-1 stays OPEN in shadow | $0 | |
| **A-14** | Q-13: apply the B6 skill changes (out-of-repo, user-global skills). Tier A before Stage B; Tier B-must before the first dispatch | **a**: yes | no skill edits; OPERATING MODE overrides instead (B6 §5.3) | $0 cash; agent time | |
| **A-15** | Execution model (Q-16, Q-15): Claude Code for the whole round, harness recorded, switches only at boundaries. Agents pause only at HG/Class-S gates, ING-GO per wave, spend over the ceiling, red CI, or unnamed production mutations. One digest + spend line per wave | **a**: yes | same as rec. | agent spend on your plan (unmeasured) | |
| **A-16** | Gate authenticity (Q-B4-2 + forward rule): an operator-only signing key for gate signatures, verified in CI; tentative words are never recorded as decisions; agent text confirmed verbatim | **yes** / **yes** | status quo (verbatim quotes + clock stamps) | $0 (optional hardware key ≈$25–55 one-off) | |
| **A-17** | Ratify D3: order safety/honesty → correctness → exploration, with Streams I and L in parallel; US-nationwide first. Co-primary journeys gate the capstone equally, the advocate winning conflicts. Flock/Axon facts **never fetched from vendor hosts**. D3 §5 is the announce gate (no early preview). CHART-025 amended to multi-vendor breadth with quality labels | **a**: ratify | a | $0 | |

### A-line details

**A-1 — Track-0 exception (OD-01).**
- **Facts.**
  - 33 of 79 schedules fire for the first time 10-01…10-21, including 12 jobs that have never executed.
  - `sig-probe` has failed every sweep since 09-27. 28 critical alerts went only to a log (G1-02, G1-08).
  - Every QA item is approved in principle but specified as a Round-11 ticket (§7.1). If Round 11 starts after ~10-08,
    the wave runs unwatched (G2 NEW-7).
- **Options.**
  - **a** exception for QA-3, QA-4 and QA-9 only. These are additive. The drill creates and deletes a *separate*
    instance.
  - **b** all ten QA items. Adds patches to `sig-pg`, the `sig-probe` roll and bucket IAM before any ticket exists.
  - **c** no exception, with the risk accepted.
- **Consequence of c.** A failed first-run job or a bad replay could go unnoticed until someone looks.
- **Unblocks:** G2 ACT-02/04; I8 ACQ-07's precondition.
- **Timing.** Today is 2026-09-30. The value of this line decays daily.

**A-2 — Money (OD-02, OD-03).**
- **Current estimate.** Infrastructure is ≈$90–100/mo. This is a list-price estimate, and the README says "≈$0/$9"
  (G1 §3.8).
- **Round-11 designs.** They add ≈$10–60/mo, overlapping (§6). Projected total ≈$100–160/mo.
- **Agent spend.** The planning session hit an account usage limit at ≈19:10Z, which shows agent spend is real and
  unmeasured. Under **(b)** (one $300 ceiling for everything) nearly every ticket would need an over-ceiling approval.
  **(a)** keeps the ceiling meaningful and reports agent spend separately.
- **Budget alert.** No budget or billing export exists, and a bot pulling from the world-readable bucket could cost
  ≈$120/day. So **yes to QA-10 now** (≈15 min as billing admin). It changes no production data.

**A-3 — DNS move (Q-31, D-J3-4, OD-04; carries D-K1-2, D-K0-4).**
- **Cost comparison.**
  - R2 via Cloudflare DNS: basemap ≈$2/mo now, ≈$3 at 10k sessions, ≈$13 at 100k. Downloads ≈$0 egress.
  - GCS: ≈$6/$43, plus download egress of ≈$13–600/mo (≈$2.8k worst case, J4).
- **Cut-over risk.** You replicate the zone's records at Cloudflare, then switch nameservers at Squarespace. The
  registrar does not change. A mis-copied record briefly breaks web or mail.
- **Other effects.**
  - The same move gives Cloudflare Email Routing for `contact@surveillancegraph.org` (inference: free with Cloudflare
    DNS). It keeps your personal address out of EDGAR and API sign-up logs (P16).
  - The $50/mo egress ceiling with an automatic kill switch bounds the worst case either way.
- **If you answer no:** the basemap goes on GCS behind the budget alert, and public download links wait for a $0-egress
  host (U-003.9/.10 are then only partly met).

**A-4 — Governance posture package (Q-7; members Q-E2-06/07/08/09/10/13/14).**

E2 recommended hybrids built on recruiting a second reviewer, an external hostile reader, a counsel opinion and outreach.
U-008, U-011 and U-013 remove all four. The package takes the honest remainder:

| member | recommended answer (member line) |
|---|---|
| Q-E2-06 PUB-008 | stands unamended; no named individual is published; web gate fixed to default-deny (H-9); MET-ENGINEERED |
| Q-E2-07 board | correct the governance doc and API terms now; ADR: interim single-maintainer editorial authority + public decision log |
| Q-E2-08 legal home | ADR: individual home as an interim, disclosed posture; revisit on announcement, first legal demand, funding or a second maintainer |
| Q-E2-09 SEC-003 | written demand-response posture + published legal-demand counts; warrant canary declined |
| Q-E2-10 counsel | publication rests on your recorded risk acceptance, labelled in every artifact; "counsel" records re-recorded as operator determinations; ADR-086/106 qualified |
| Q-E2-13 DB right | recognise the operator-accepted basis by ADR, **with guardrails**: express terms decided individually (A-8/A-9), Part VIII preflight, jurisdiction-conditional publication, withdrawal on objection |
| Q-E2-14 ODbL | keep the per-compartment map; ADR records ADR-106's clearance as operator-reported, with no document |

- **Exposure, plainly.** Publication, robots, database right and ODbL decisions all rest on one individual's judgement
  with no legal review on file. The package *records* that exposure; it does not remove it. The withdrawal barrier
  (G3 §8.3) and the dispute channel are the remedies if a rights holder objects.
- **Default c:** the spec stays as it is, the members stay owed, and the false public claims are still removed (B-1).

**A-5 — Robots (Q-E2-11).**
- **Options.**
  - **a** re-confirm as is.
  - **b** narrow: honour explicit `disallowed` and TDM/Article-4 reservations on non-US hosts, and keep the disregard
    for US public-body hosts.
  - **c** obey robots.txt everywhere. This loses ≥ 103 hosts of agenda, CCOPS and procurement evidence.
- **Why b.** D3 does not expand non-US coverage, so (b) costs almost nothing. It also removes the case where EU
  reservations have legal effect.
- **US exposure, plainly.** Municipal hosts or PrimeGov (shared vendor infrastructure) may block SIG or complain.
- **Built either way.** The rule-7 opt-out register and the SIG-INGEST-046c reservation refusal are MUSTs that were
  never waived. Public run logs disclose the disregard as host + count (B-19).
- **Carried by this answer:** Q-E2-02 (crawler text) and E4 S2.

**A-6 — Evaluation (Q-L3-1, Q-L3-2; answers Q-24, Q-25, Q-E2-15, Q-F4-1/2/3).**
- **Why rows 184–187 go.** They cannot re-enter as written (F4 §3). F4's Option B needs external labellers.
- **What L3 adopts.** Posture C, now:
  - no human rows;
  - D-R10-HUMAN-1 OPEN and non-blocking with trigger T-EVAL-IND;
  - **derivation, not identity**: only mechanically proven copies of one upstream record merge automatically (C0–C2);
  - every inferential merge stays review-only;
  - counts are published as intervals.
- **Verdicts.** EVAL-001 MET-ENGINEERED · 002/005/007 owed · 003/006 MET · 004 WAIVED(ADR-L3-B, C0–C2).
- **What the site may never claim:** "human-verified", "certified", or any cross-source camera-match precision figure.
- **Q-24:** no certification attempt. **Q-25:** you hold only the disclosed maintainer-check seat (B-31).
- **Your words are required** for the EVAL-004 waiver. Answer, for example: *"I accept derivation, not identity, and
  waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes."*

**A-7 — Rights stance + Tier 1 (Q-19 and its members).**
- **What "a" does.** It applies GL-GATE-07 precedent batch-wide to the Tier-1 families:
  - US agency layers;
  - state DOT layers;
  - statutory/CCOPS/policy documents;
  - agenda/procurement/grant documents;
  - federal works (CC0);
  - explicit open licences;
  - journalism/NGO facts + citations;
  - existing gated rows RG1–5;
  - the Round-10 dossier targets, after the URL-reconciliation ticket.
- **What it does not do.** Part-VIII-flagged members still need their S-line (B-32). Express prohibitions are A-8/A-9
  and B-39.
- **Unblocks:** I8 ACQ-08…15 (≈89 registry rows, ≈250k claims) and G2 step 5.
- Member lines are in the appendix.

**A-8 — Express-terms withdrawals (Q-J4-2 = D-J3-5; I7-C1).**
- **Why withdraw.** GL-GATE-07 accepted database-right risk. It never accepted a publisher's express "do not
  redistribute".
- **Withdrawal.**
  - Removes 5,267 public rows. Source pages say "withdrawn from publication pending rights review".
  - The spine keeps its history (append-only).
- **TxDOT.** Consent is unavailable (U-011). So the republished copy leaves public output, and E4 R3 (`dot_511_tx`,
  another TxDOT republish) is declined.

**A-9 — Non-commercial statement (I7-C6; governs E4 R4d, I7 IT2/3/5/6).**
- **Why this is hard to assert.** SIG publishes bulk data under licences that let anyone reuse it commercially, and
  "non-commercial" is judged by the publisher, not by SIG's intent.
- **(b)** keeps NC publishers as cited facts and pointers. The three live NC rows join A-8's withdrawal.
- **(a)** would need an NC compartment kept out of permissive downloads.

**A-10 — Organisations (D-K2-1; carries the ADR-124 allow list).**
- **Why a review is needed.** Organisations are public institutions. The review exists to catch person names and
  mislabels.
- **The work.** 50 reviews in degree order unlock 96.5 % of edges, using the allow tool (G2 ACT-10) once it is built.
  An ADR auto-allows organisations matched to the Census of Governments, a SAM UEI or a Wikidata QID. The person-name
  screen always runs.
- **If you answer no:** U-003.2's entity pages, network labels and organisation search ship as "pending publication
  review".
- **Folded in:** D-P32.3-1 (B-18).

**A-11 — Global graph (D-K13-1; D-K0-6, D-K2-2).**
- **Why not one national graph.** No peer renders a useful 10^5-node graph, and renderers top out around 10^3–10^4
  labelled nodes. 83 % of SIG's nodes have no edges today, so a national node-link view would be a scatter of isolated
  points.
- **What you get instead.**
  - Aggregated overviews, including a state × state Flock access matrix once D-K2-4 lands.
  - Per-entity egos.
  - `/explore/`, with the same facts available without JS.
- **Revisit trigger:** a single view needs > 3,000 labelled nodes.

**A-12 — JavaScript architecture (D-K0-1).**
- **Why.** You asked to "think and research and reason carefully about perhaps breaking with our no-JS constraints"
  (U-003.2). K0's answer: page types with CI-enforced budgets.
- **What stays zero-JS:**
  - printed and cited records;
  - no-JS fallbacks on every URL;
  - Preact instead of React (D-K0-2).
- **What changes.** AGENTS.md gotcha 6 and ADR-068/091/097/134 are superseded by a new ADR at T1.
- **If you answer no:** most of U-003.1/.2/.3/.9 stays limited to today's three islands.

**A-13 — Seed contents (Q-14, Q-B4-1, OD-05, OD-06, Q-17).**
- **Why the seed carries code.** Without the guard core and the six test-pin conversions, the seed PR is red on CI
  (B4 §6.1, F5 PKG-02).
- **Restore first.** Six of the 53 deleted GATE DECISIONS rows exist nowhere else, so they are restored before the
  LEDGER head is restructured.
- **Memory split (B3 option C).**
  - Obligation events are repaired, then enforced by CI.
  - The projection stays as an advisory orient view.
  - The closeout journal stays shadow until a trigger: parallel dispatch, a multi-worktree build, or a second harness.

**A-14 — Skill changes (Q-13).**
- **What they are.** 25 proposals. 13 are "must apply":
  - **Tier A**, before Stage B: SK-13/14/17/18/19/20/22.
  - **Tier B-must**, before the first dispatch: SK-01/02/03/06/09/10.
- **Why they matter.** They are the mechanical controls that would have stopped the chain at four red boundaries and
  caught 502 future-dated records.
- **Scope.** The edits are to your user-global skills, so they affect every project that uses them.

**A-15 — Execution model (Q-16, Q-15).**
- **What B7 found.** The worst Round-10 record failures ran under Devin CLI (`swe-2-high`): the forward date ratchet,
  the 53-row deletion and the after-the-fact readouts. But every harness failed somewhere (B5).
- **Why Claude Code anyway.** The B6 skills and B4 guards target it, and planning ran here. The guards, not the
  harness, carry the safety.
- **Your load:**
  - one digest per wave with a spend line;
  - gate lines;
  - four ING-GOs (B-11);
  - about six Class-S readouts (B-9).

**A-16 — Gate authenticity (Q-B4-2, Q-E2-21).**
- **Why a key.** Agents commit and run `gh` with your identity, so any in-repo approval can be produced by an agent.
  B7 found both Round-10 signed readouts were written 32 s and 51 s *after* your approvals.
- **The control.** A key that agent sessions never load, used only for gate-signature commits and verified in CI. It
  is the only mechanical proof of origin.
- **Cost.** About 30 min of setup, then about 1 min per signature, a handful per round.

**A-17 — Direction (D3-DIR, D3-Q1, D3-Q3, D3-Q5, Q-E2-22).**
- **Why this order.** Correctness comes before exploration so that new maps and graphs do not amplify known errors:
  wrong jurisdictions, duplicates and undated edges (L2).
- **What D3-Q3 costs.** Some Flock/Axon depth stays dark: I8 lists "Flock/Axon's own data" as dark. That is the price
  of not fetching from vendor hosts whose terms prohibit automated access.
- **What D3-Q5 means.** The announcement waits for D3 §5's checklist, starting with your own test: "I would send this
  to a journalist today" (the inverse of U-005).

---

## 3. Part B — batch approvals with defaults

"Rec." is the recommended answer for every member id listed. The appendix lists the member-level rights and K lines.
The fast path "B: all as recommended" answers every line.

| # | decision | members (CSV ids) | rec. | if unanswered | answer |
|---|---|---|---|---|---|
| **B-1** | Wave-0 honesty fixes: E2 H-1…H-9, K13 UXW0-1…6, C6 QW-1…15, and the fixture/status-word publish guard. Also the two S0s outside §7.1's list: `/visual-language/` test facts about OKC PD/Flock, and personal ArcGIS handles in source ids | E2-HFIX, G2-S0X | approve all | removals of false claims ship (§7.1); new wording waits for B-2 | |
| **B-2** | Copy approvals: agent-drafted texts in batches of ~25, confirmed verbatim per republish, "pending review" until then. **Agents may ship removal-only corrections and "not yet performed / not operating" notices without per-text confirmation** | OD-07, D-J3-12, D-K10-1, D-K10-4, D-K9-4, D-K5-2, D-K4-8 | a | b (no allowance) | |
| **B-3** | Re-key public source ids that embed personal handles. Old URLs get a neutral "identifier changed" page. The old→new map stays restricted (a public redirect would republish the handles) | DR-C6-01 | a | a | |
| **B-4** | Record integrity: supersede the fixture candidate `p-17b713` (no re-sign); GATE-G3 superseded; **ACCEPT-R10/R8 annotated "approved on an agent summary; full text composed after"** rather than re-confirmed; go-live spec amended and supersessions appended; date corrections by appended amendment; B7's true times | Q-12, Q-E2-18, Q-E2-19, Q-E2-20, Q-B1-2 | as stated | same (corrections are append-only) | |
| **B-5** | Verdict vocabulary (MET · MET-DIFFERENTLY(ADR) · MET-ENGINEERED · PARTIAL · MISSING · AT-RISK-INTEGRATION · WAIVED(ADR) · N/A-RATIONALE), the +4 matrix columns, and re-verdicts of scoped and boilerplate rows | Q-E2-17 | a | a | |
| **B-6** | Residual E2 lines: `/editorial-standards/` shows "not yet performed" and UI-042 stays owed; crawler text follows A-5; register `sig-project.org` (≈$10–20/yr) and move the UA to surveillancegraph.org; attribution handled as a defect with a publish gate; Stage-0 outreach becomes later-phase (U-011); the usability study becomes later-phase; SWH deposit after a history scan (repo is public) | E2-RESID, Q-E2-01/02/03/04/12/16/23 | as stated | no purchase; no deposit; otherwise the same | |
| **B-7** | Round-10 surfaces at G2 step 7: archive + pinned citations + release search first; research dossiers only after live captures; intake only if B-8 opens it. **No API hotfix** for C3 NEW-1 unless step 1 slips past ~10-21 (disclosed meanwhile) | Q-9, G2-HOTFIX | a / a | a / a | |
| **B-8** | Intake stays **email-only** (your address) until after the announcement; `/intake/` shows "not operating". Published response times (agent-drafted): **Part VIII/safety takedowns within 72 h; other corrections acknowledged within 7 days, answered within 30**. Task pages name the same address | Q-27, OD-08, D-K11-4 | a | email-only; task pages say "reporting opens with the intake form" | |
| **B-9** | G3 release model: identity v2 + label `sig-YYYY-MM-DD.N`; **Class R/S rule** with the standing-go text for Class R (confirm the §7.3 text verbatim); monthly on the 15th at 14:00Z, early at ≥ 10 % net and ≥ 14 days, 35-day alert; auto-rollback; 15-min withdrawal SLA; private staging services | D-G3-1/2/3/4/8/9/10 | yes | every release Class S | |
| **B-10** | Releases from unmerged stack commits (as today); you tag `v0.1.0` after the #190 sitting; legacy buckets retired per G3 | D-G3-5/6/7 | yes | no tags; buckets unchanged | |
| **B-11** | Cloud SQL autoresize **cap 40 GB** (unlimited today), pre-grow to 25 GB before Wave C, temporary tier bump for the OSM run; OSM monthly; **one ING-GO per acquisition wave (4 lines)**; targets under already-flipped sources treated as configuration; scope = core + droppable Wave D | Q-23, I8-Q2/Q3/Q4/Q5 | as stated | 25 GB cap and Wave C waits; core only | |
| **B-12** | Paid data sources: $0 | Q-21 | $0 | $0 | |
| **B-13** | Cost trims: consolidate 79 scheduler triggers into one dispatcher (−$7/mo). Keep the LB (G3 path routing needs it) and min-instances 1. Revisit a Cloud SQL CUD after 3 measured bills | G1-TRIM | a | no trims | |
| **B-14** | Evidence retention: 365 days minimum, **unlocked** (takedowns stay possible) | G1-RET | a | status quo | |
| **B-15** | GitHub settings (**you** do them): S-1 `main` ruleset after the merge sitting; S-2 `r11/**` no-force-push before the seed push; S-3 merge commits only, no branch deletion on merge; S-4 `SIG_GCP_PROJECT` variable; S-5 billing check + Actions alert; S-7 optional. Pre-#190 reds don't block Round 11; branch prefix `r11/`; one allow-listed flake re-run per head | H2-SET, Q-B4-3, Q-H2-1/3/4 | as stated | nothing changed; flakes → `blockedOn` | |
| **B-16** | Keep `claude/next-phase-planning` **local** until T6. The repo is public, so the first push publishes the planning notes, including your address and redacted Part VIII findings. Scan for secrets, personal identifiers and Part VIII content before pushing. A private off-disk backup is optional | Q-H2-6 | a | a | |
| **B-17** | `nextTicket` = the first Round-11 row (N1). HG-05 gets an operator-owned integration disposition, not a new D-row | B3-NEXT, B3-HG05 | a / a | a / a | |
| **B-18** | Owed operator actions: register the free **US 511 API keys** (~30 min; yes); QLD/NSW keys (no: non-US not expanded); D-P30.2b-1 curation → merged into the L3 maintainer check (saves 2–8 h); D-P32.3-1 legacy org keys → folded into A-10 + CONF-13 (saves up to ~40 h) | D-SOURCES.7-2, D-SOURCES.8-2, D-P30.2b-1, D-P32.3-1 | as stated | stay OPEN | |
| **B-19** | Transparency (Q-22): raw bytes for **raw-ok sources only**, after the Part VIII byte screen; J4's derived-only default; scrubbed run logs disclosing robots as host + count; commit hashes shown (repo is public); `/s/<pub>/` snapshots; JSON-LD as linked files; prior releases as manifests + disclosure, not bytes; status lane every 6 h, refused sources as counts; review packets linked after a per-packet check | D-J3-1/2/3/6/7/10/11/13, Q-J4-7 | yes | nothing new published | |
| **B-20** | Signing: a **pipeline key** in Secret Manager signs release manifests (disclosed as the pipeline's signature); your key (A-16) signs gate records. J3's "operator-held key on every manifest" would put you in every Class-R release | D-J3-8 | a | sha256 only | |
| **B-21** | Zenodo DOIs (irreversible): openly licensed compartments only, after the attribution fix, run by you | D-J3-9 | yes | none | |
| **B-22** | Accept the remaining **58 K-row design recommendations** as written (appendix) | K-BATCH | a | as recommended | |
| **B-23** | Non-US place names: Natural Earth (public domain) now for map and search; GeoNames only if too thin. This resolves the K1/K3 disagreement K13 left open | OD-09 (D-K1-5, D-K3-3) | a | a | |
| **B-24** | HG-03 for boundaries: `census_gazetteer_tiger` (public domain) + `natural_earth_10m`, after the terms capture. This is the foundation for placing 166k "unresolved" records | D-K4-1 | yes | JUR-01 blocked | |
| **B-25** | Flock share lists (474,184 edges already held via the Eyes on Flock mirror) become organisation-level access claims after a Part VIII screen | D-K2-4 | yes | no | |
| **B-26** | Publishing the dedup is an **announce criterion**; until then the site says "records" | D-K13-4 | yes | yes | |
| **B-27** | A neutral "Other public resources" block on dossiers (Atlas, Eyes on Flock, DeFlock, ACLU, alpr.watch), with no avoidance routing or plate lookup; links to official agenda portals | D3-Q4, D-K7-3 | yes | no peer links | |
| **B-28** | You write the ≥ 40-query held-out search relevance set (~30 min) | D-K3-7 | a | a separate agent writes it, labelled | |
| **B-29** | "Beautiful" gallery sign-off by you before the announcement (~30–60 min); the spec published as a page per release | D-K14-9, D-K14-8 | yes | yes / no | |
| **B-30** | `sig-api` 512 MiB → 1 GiB for release search (**+$3/mo**); search rate limit 30/min | D-K3-5, D-K3-6 | yes | old search stays | |
| **B-31** | Maintainer checks per Class-S release (~20–40 min each); **no** second model family (avoids new spend and a new provider); failing quality checks shown publicly on `/quality/`; C2 collapse enabled | Q-L3-3/4/5/6 | as stated | no checks; no; passing checks only; C0/C1 only | |
| **B-32** | I7 Part VIII screens S1–S9: ingest only the screened lane. S5 is ingested with names suppressed (PUB-008); **S8 tribal stays metadata-only** | I7-S1…S9 | a (S8: b) | metadata-only | |
| **B-33** | RB-06b share-alike (a, share-alike compartment); RB-08 US territories (b, capture terms first) | I7-RB-06b, RB-08 | a / b | not flipped | |
| **B-34** | **N1–N21 non-US database-right lines: not flipped this round** (b: capture terms if Wave D international runs). This departs from GL-GATE-07 precedent because D3 does not expand non-US coverage and no counsel reviews the database right | I7-N1…N21 | b | not flipped | |
| **B-35** | Restricted terms IT1–IT7: facts-only pointers (IT4 GETS declined; IT7 Axon never fetched) | I7-IT1…7 | b (IT4: c) | not flipped | |
| **B-36** | Terms not captured IU1–IU5: capture in Round 11, then a line | I7-IU1…5 | a | facts + citation only | |
| **B-37** | Tribal TR1–TR2: defer until a tribal-data-governance rule exists (asking the Nation is outside contact) | I7-TR1/2 | a | a | |
| **B-38** | SEC EDGAR P1–P4: facts-only basis; ingestion later-phase; the first request only after the `contact@` alias exists | I7-P1…4 | a | defer | |
| **B-39** | Conflicts: DocumentCloud/MuckRock link-only; Sourcewell/OMNIA pointers only; vendor platforms never fetched; revocation clauses accepted for Chicago/ABQ but OpenFEMA API declined; SDPC facts from district pages; **CourtListener bulk stays deferred**; statute seed refreshed from origins; Edmonton decided on OGL-Edmonton | I7-C2/3/4/5/7/8/9/11 (C10 answered by Q-30) | as stated | pointer-only / deferred | |
| **B-40** | Confirmations: X1 prohibited Tier-3 stays declined; X2 Part VIII blocks stay metadata-only; X4 label corrections M1–M7 in ACQ-02 | I7-X1/X2/X4 | confirm | confirm | |
| **B-41** | E4 rights rows: R1 close (eID leg WONTFIX); R2a/R2b decline; **R3 decline** (TxDOT); R4a–c flip (closing an owed row); **R4d decline** (follows A-9); R5 flip; R6a capture terms first; R6b superseded | E4-R1…R6b | as stated | not flipped | |
| **B-42** | E4 Round-10 dossier lines: B2 Part VIII screen + your "clear" per family; B3 SRC-027 metadata-only for good; B4 one bounded retry + byte-bound exception | E4-B2/B3/B4 | a | not assessed | |
| **B-43** | Status corrections: E4 S1 (D-SOURCES.12-1 → DONE), S2 bonfire WONTFIX, S3 later-phase, S4 → PARTIAL, S5 moot; F1 D-P21.3-2 → DONE | E4-S1…S5, F1-P21.3-2 | as stated | unchanged | |

---

## 4. Part C — informational confirmations

| # | what the agent found or drafted | ids | rec. | if unanswered | answer |
|---|---|---|---|---|---|
| **C-1** | **Readout provenance.** You approved GATE-G3 (2026-09-28T03:49:14Z) and ACCEPT-R10 (18:46:46Z) on agent summaries shown 40 min and 11.5 h earlier. The signed texts were composed 32 s and 51 s *after* the approvals. None was given on 2026-10-19. The correction ADR records this as fact | OD-10 | confirm | recorded as B7 found | |
| **C-2** | **Harness attribution.** Round 1→P27.3 Devin CLI; P27.4→P31.5 Claude Code; P31.6→P33.8 (140 commits) one Devin session, `swe-2-high` only; Round-10 import Codex. Was "Pause after P31.5" a planned hand-over? (It coincided to the minute) | OD-11 | confirm; say yes/no on intent | intent "unknown" | |
| **C-3** | **Your own words** for: (1) the 2026-09-16/24 "counsel" determinations were yours (U-013); (2) "let's defer all the human review steps and proceed" (09-28T01:15:49Z) was your deferral of the human legs; (3) robots, as A-5 | OD-12 | confirm | U-013 wording used | |
| **C-4** | **Positioning** (agent-drafted, K14 §2.1 + D3 §1). Tagline *"The evidence behind public surveillance, place by place."* The 45-word sentence, the About paragraph, "why it exists", and the four "what SIG is not" lines. Alternates: *"Public surveillance, traced to the documents."* / *"Who watches, who shares, who decides — sourced."* | D-K14-1 | confirm or edit verbatim | current copy minus false claims | |
| **C-5** | **About page: who runs SIG.** Your name, or "a single independent maintainer". The public repo and the Q-29 address already name you. You write this text; agents only draft | D-K14-7 | your choice | "a single independent maintainer" placeholder | |
| **C-6** | **The repository is PUBLIC** (live read). J3, J4 and K14 assumed it was private. Confirm it stays public: this simplifies B-19/B-29, re-opens SWH (B-6) and makes B-16 matter | OD-13 | stays public | no change | |
| **C-7** | **Cost truth.** What did the last GCP invoice show? G1's ≈$90–100/mo is a list-price inference | OD-14 | state the number | estimate kept, labelled inference | |
| **C-8** | Under U-014, connectors that need a contact string (EDGAR User-Agent, API sign-ups) would send your name + address. Confirm "alias first" (A-3/OD-04) | OD-15 | alias first | U-014 as recorded | |
| **C-9** | The `SIG_INTAKE_*_SECRET` lines in two planning notes were a generator command, not a value, and were reworded. Confirm no such value was used in any deployed or staging config | Q-H2-2 | confirm | treated as resolved | |
| **C-10** | Does any persistent local DB (`sig-ops up` volume, `.codex/worktrees`) hold Round-10 sqitch changes L44–52? | Q-B1-4 | answer if known | "unknown"; never re-stamp | |
| **C-11** | Confirm the labelled agent interpretations under U-002…U-015. These are: the journalist exploration journey as primary; Stream L; K14; the $300/$1,000 rule; no outreach, recruiting, records-request sending or contribution-back; the alias; B7 | OD-16 | confirm | cited as interpretations | |

---

## 5. D2 — one reaction to the most consequential findings

Mark each line **agree / disagree / unsure** and a priority. **P1** = Wave 0–1 (safety, honesty, correctness).
**P2** = this round. **P3** = later. Sources: `findings/REGISTER.md` S0/S1 and `review/REVIEW_SYNTHESIS.md` themes
TH-01…TH-16, plus Stream L and B.

| # | finding / theme | sev. | evidence | proposed response | agree? | priority |
|---|---|---|---|---|---|---|
| **D2-01** | Rights and attribution are broken at publish time. Downloads and the API credit third-party CC-BY rows (Iowa DOT, DC, Gold Coast) and EFF Atlas rows to "DeFlock community map". Personal ArcGIS handles appear in public source ids | S0 | F-387, F-097, F-131; TH-02 | Wave 0 attribution defect + publish gate + re-key | | |
| **D2-02** | Fixtures and unbound status words are shown as real: a fixture two-reviewer review, test facts about OKC PD/Flock, and a "human-verified holdout" that is LLM-bootstrapped | S0 | F-183, F-096, F-06; TH-01 | Wave 0 republish + fixture/status-word guard | | |
| **D2-03** | Every page promises a one-click dispute channel that does not exist | S0 | F-03; TH-13 | honest notice + your address; intake later | | |
| **D2-04** | The API dossier endpoint returns the same 25 placeholder subjects for every scope. Bulk data, API and terms are linked nowhere | S0 | F-130, F-103; TH-07 | Round-10 API (G2 step 1); downloads behind $0 egress | | |
| **D2-05** | **SIG has no deduplicated graph.** The same camera is counted once per publisher. Dossier counts are up to 2.25× inflated. 13.5 % of points have another source's point within 25 m, vs 3.75 % merged | S1 | L1 §0, L2 | CONF-07a/b + intervals (A-6, B-26) | | |
| **D2-06** | Evidence is not bound to bytes: 0 of 2.78M claim–evidence links reach captured bytes; `/evidence/` is empty because the exporter hard-codes an empty list; 0/255 evidence items carry an upstream URL | S1 | L2, K8, J1 | capture binding; K8 EV-01…03; TX-08 | | |
| **D2-07** | Jurisdiction and geometry are wrong at scale. 91.5 % of "unresolved" is inside the US. Idaho+Indonesia and Minnesota+Mongolia share dossiers. There are 562 axis swaps, and Oklahoma has no dossier | S1 | F-04, F-44, K4, L2; TH-04 | Wave 1 JUR-01…07 (B-24) | | |
| **D2-08** | 82.8 % of entities have no label, so UUIDs are shown. Every subject is typed `deployment`. 77 % of `traffic_camera` subjects are ALPR, police CCTV or enforcement by their own source | S1 | K0, K2, L1, L2 | GX-01, PKG-07, PKG-11 | | |
| **D2-09** | The only relations are 130 EFF sharing edges from 2016–17, stamped 2020. 98.8 % of edges are undated. 474,184 Flock share-list edges sit ingested but unused | S1 | L1, L2, K2, I3 | CONF-06; D-K2-4 (B-25) | | |
| **D2-10** | Coverage: Flock only via one mirror (~23 % of networks); Axon, Fusus and RTCC nothing; 22 states without dossiers; the national OSM ALPR origin (154,814 objects) ingested only as a stale 132,689-object copy | S1 | I1, I3, I8 | Stream I Waves A–D (A-7) | | |
| **D2-11** | Operations run blind. The probe has failed since 09-27, and its alerts go only to a log. Every workload has `roles/editor`. Buckets are unversioned, so the "WORM" claim is false. Cost is ≈$90–100/mo vs the documented "≈$0/$9" | S1 | G1-01…10 | QA-1…10 (A-1), per-workload SAs | | |
| **D2-12** | Build memory is not a safe resume point. 595 records / 2,283 dated occurrences carry dates that did not happen. 53 GATE DECISIONS rows were deleted. The ledger is 679 KB | S1 | B1, B2, B3 | seed (A-13) + guards + skills (A-14) | | |
| **D2-13** | Gates became a throughput device. 35/76 gate records were answered at a pause, `blockedOn` was never set, and the Round-10 readouts were written after the approvals | S1 | B5, B7, F-36 | A-15/A-16 | | |
| **D2-14** | "MET" does not mean met. 86 of the 89 spec ids cited by live failures read MET. The boilerplate MET-DIFFERENTLY rows fail 7/13 samples | S1 | C6 §4, F2b | verdict vocabulary (B-5) | | |
| **D2-15** | The audiences are not served yet. 5 of 31 tasks succeeded; journalist 0/3; organizer 0/6. SIG's unclaimed niche is cost + decision date, disagreement between sources, and a printable cited brief | S1 | C2, C5 | D3 direction; K13 capstone | | |
| **D2-16** | The map's dots vanish because tiles use tippecanoe's default point dropping: 0.03 % of sites at z3. No test covers production tiles | S1 | K1, F-104 | early "honest map now" slice (D-K1-8) | | |

---

## 6. Money: what each answer costs (monthly unless noted; inference unless marked)

| item | recommended answer | cost | alternative |
|---|---|---|---|
| Baseline today (G1, list-price estimate) | — | ≈ $90–100 | C-7 replaces it with the real bill |
| A-1 QA-3/4/9 exception | a | ≈ $0 + ≈ $0.15–0.40 one-off | — |
| A-3 R2 origin (basemap, tiles, downloads, snapshots) | a | ≈ $2–13 (10k→100k sessions); egress ≈ $0; ceiling $50 | GCS ≈ $6–43 + download egress ≈ $13–600 (≈ $2.8k worst case) |
| A-12 page-type JS serving (K0; overlaps K1/K3) | a | + $5–40 | $0 (U-003 asks unmet) |
| A-7 / B-11 acquisition (I8) incl. disk cap | a | + $4–6; ≈ $5–10 one-off; permanent DB scale-up + $49 only on a named trigger | — |
| B-9 releases (G3) | yes | ≈ $2.5 per release (≈ $2.5–5) + staging ≈ $0 | — |
| B-30 search memory | yes | + $3 | — |
| A-6 / B-31 quality suite (L3) | a | ≤ $5 | a second model family would add metered spend |
| K6 figures, K9/K10 version history | — | < $1; ≈ $0 on R2 | — |
| B-6 `sig-project.org` | a | ≈ $10–20 per year | $0 |
| B-13 scheduler consolidation | a | − $7 | − $18 (LB), − $7–10 (min-instances) at a functional cost |
| A-16 hardware key (optional) | — | ≈ $25–55 one-off | passphrase SSH key $0 |
| **Projected infra total** | | **≈ $100–160/mo**, under $300 | — |
| Agent/model spend | A-2 a | **not measured**; reported per wave | — |

Nothing recommended here needs an over-$300 approval. The only paths that approach it are: download egress without
R2 (A-3 "no" plus public downloads), search abuse without rate limits (≈$140/mo worst case, B-30), and a permanent DB
scale-up.

---

## 7. Operator work outside the sitting (only if you answer as recommended)

| when | what | time |
|---|---|---|
| today / before 10-10 | watch the A-1 exception land (the agent executes under your go) | ~5 min |
| now | QA-10 budget + billing export (A-2) | ~15 min |
| before Round 11 | DNS cut-over at Squarespace → Cloudflare; `contact@` routing (A-3) | ~30–60 min |
| before Round 11 | register `sig-project.org` (B-6); GitHub S-3/S-4/S-5 (B-15); US 511 API keys (B-18) | ~45 min |
| before Round 11 | signing-key setup (A-16) | ~30 min |
| after ACT-10 lands | top-50 organisation review (A-10) | ~1–2 h (estimate) |
| early Round 11 | held-out search queries (B-28) | ~30 min |
| each republish | copy batch approvals (B-2) | ~15–30 min |
| each acquisition wave | one ING-GO line (B-11) | ~1 min × 4 |
| each Class-S release | readout + maintainer check (B-9, B-31) | ~30–60 min × ~6 |
| after the #141–#190 merge sitting | S-1 ruleset; tag `v0.1.0` (B-10, B-15) | ~10 min |
| before the announcement | gallery sign-off (B-29); About text (C-5) | ~1 h |

---

## 8. How the answers interact

- **A-4 → A-5, A-7, A-8, A-9, B-19.** The guardrails in Q-E2-13 are what keep A-7's batch approvals from reaching
  express prohibitions (A-8/A-9) and Part VIII rows (B-32).
- **A-9 → B-35, B-41.** If you answer "non-commercial" (a), IT2/IT5 and E4 R4d can flip. B-35 and B-41 then change to
  "a", and an NC compartment is needed (J3).
- **A-3 → OD-04 → B-38, C-8.** The alias is free only with Cloudflare DNS (inference). Without it, EDGAR and API
  sign-ups use your personal address, per U-014.
- **A-6 → B-26, B-31, A-11.** The dedup that B-26 makes an announce criterion exists only if A-6 permits C0–C2
  collapse. Without it, counts stay "records" with ranged "possible duplicates".
- **A-10 → A-11, B-25.** The access overview and the Flock matrix need publishable organisations.
- **A-12 → A-11, B-22.** Most K-batch items assume page types. If A-12 = b, B-22 shrinks to what fits the three
  islands.
- **A-13 + A-14 + A-16 → T2/T5/T6.** Stage B cannot write the seed until these are answered or defaulted.
- **A-1** is independent and time-bound. Answer it even if nothing else is answered today.

---

## 9. Coverage, method and limits

- **Sources of the 323 ids.**
  - Q-7…Q-31 still open: Q-7, 9, 12, 13, 14, 15, 16, 17, 19, 21, 23 (disk cap), 24, 25, 27, 31.
  - E2 Q-E2-01…23.
  - E4's 22 lines and I7's 78 lines.
  - D-K0…D-K14 (84 open).
  - D3 Q1–Q5 + direction.
  - F4 Q-F4-1…3 (superseded) and L3 Q-L3-1…6.
  - G2 §9 items, G3 D-G3-1…10, J3 D-J3-1…13 (with J4 Q-J4-1…8 as aliases), H2 S-1…S-7 and Q-H2-1…6.
  - B4 Q-B4-1…3, B1 Q-B1-2/4, B3 §8 items, B6 Q-13.
  - G1 §7, I8 §11, F1 operator-action rows, C6's new re-key decision.
  - 16 OD-nn items that had no id, plus bundle ids (E2-HFIX, E2-RESID, K-BATCH, D3-DIR, H2-SET) and source-local ids
    (G2-S0X, G2-HOTFIX, G2-ADR124, I8-Q2…Q5, G1-TRIM, G1-RET, B3-NEXT, B3-HG05, DR-C6-01, F1-P21.3-2).
- **Dropped as answered:** 23 rows (≈37 ids), listed in §1 with their answers.
- **Duplicates merged**, each into one owner id; the other ids are kept as aliases in `source_refs`:
  - Q-22a = Q-J4-1 = D-J3-1;
  - Q-J4-2 = D-J3-5;
  - Q-J4-3 = D-J3-4;
  - Q-E2-05 split between Q-29 (answered) and OD-08;
  - D-K1-2 = D-K0-4 = Q-31;
  - D-K1-5 vs D-K3-3 → OD-09;
  - D-K7-3 = D3-Q4;
  - Q-F4-* → Q-L3-*;
  - Q-24/Q-25 answered through A-6;
  - Q-B4-3 = Q-H2-5.
- **Recommendations that changed from the source note because of D1 answers:**
  - E2-01/02/04/05/06/09/10/14 (no recruiting, no counsel packet);
  - F4 Option B → L3 posture C;
  - E4 R1c/R2b-b/R4d-b and I7 "seek consent" options → unavailable.
- **Judgement calls to check.**
  - B-34: non-US N-lines are recommended against the GL-GATE-07 precedent.
  - A-9 and B-20 are recommended against J3's "operator-held key on every manifest".
  - B-2 adds an autonomy allowance the verbatim rule does not have today.
- **Limits.**
  - Costs are design estimates (inference). None was read from billing.
  - Operator-time figures are estimates.
  - Rights facts are quoted from E4/I7. No terms were re-fetched in this row.
  - The rights appendix was generated from the E4/I7 tables by a scratch script (not committed), so it quotes them
    verbatim.

---

## Appendix — member-level lines (generated from `data/decision_catalog.csv`)

Answer by exception. Every line not named takes its packet line's answer.

#### B-41…B-43 — E4 lines (existing gated rows, status corrections) (19 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| E4-R1 | HG-03 D-JURIS.2-1 — declarationcamera_be (Belgian-eID leg only): which option? (GL-GATE-07: n/a (rights already decided 2026-09-15)) | a close: rights scope DONE + eID leg WONTFIX, skipped by operator · b keep as an HG-04 operator-credential row (not a rights row) · c pursue eID/outreach | **a** — Close: rights DONE; the Belgian-eID leg is WONTFIX (no eID holder; outreach class skipped before). Option c needs outside contact (U-011). | |
| E4-R2a | HG-03 D-SOURCES.2-2 — documentcloud: which option? (GL-GATE-07: NOT COVERED (P26.16: "GL-GATE-07's camera-registry basis does not reach it")) | a decline → WONTFIX · b flip despite the ToS anti-extraction clause · c seek an affirmative DocumentCloud API grant or review named documents one by one | **a** — ToS forbids extraction; decline recorded 2026-09-17; option c's named-document review stays possible later. | |
| E4-R2b | HG-03 D-SOURCES.2-2 — courtlistener_recap: which option? (GL-GATE-07: NOT COVERED (deferred by name in GL-GATE-07)) | a decline → WONTFIX · b approach FLP's partnership/commercial tier (agreement + token, HG-09) · c accept the membership terms and hold a token (packet: SIG looks ineligible as written) | **a** — Options b/c need an FLP agreement or membership SIG looks ineligible for; b is outside contact (U-011). | |
| E4-R3 | HG-03 D-SOURCES.7-1 — dot_511_tx (the sole remainder, see S4): which option? (GL-GATE-07: PRECEDENT (camreg_txdot_rep_tx: a personal-account ArcGIS item with licence "none", flipped and live)) | a flip under GL-GATE-07 (US) · b decline as redundant with camreg_txdot_rep_tx · c find a TxDOT-owned layer first | **b** — A second personal-account republish of TxDOT data; with I7-C1 restricting the first, flipping this one would repeat the express-terms conflict. | |
| E4-R4a | HG-03 D-SOURCES.8-1 — camreg_edmonton_ab (CA): which option? (GL-GATE-07: PRECEDENT (Calgary/York: Canadian, no grant → DBRight)) | a flip, non-US basis · b capture the City of Edmonton ToU first · c decline | **a** — Closes an existing owed row (D-SOURCES.8-1); decide on the OGL-Edmonton basis once the terms body is captured (I7-C11). | |
| E4-R4b | HG-03 D-SOURCES.8-1 — camreg_hk_hk (HK): which option? (GL-GATE-07: PRECEDENT (camreg_polyu_hk: HK, licence "none" → DBRight, live)) | a flip, non-US basis · b capture the data.gov.hk T&C first · c decline | **a** — Precedent (camreg_polyu_hk); closes the owed row. | |
| E4-R4c | HG-03 D-SOURCES.8-1 — camreg_qldc_au (AU): which option? (GL-GATE-07: PRECEDENT (Donegal/NZTA: non-grant wording → DBRight)) | a flip, non-US basis · b use the QLDTraffic API (CC-BY per CKAN; key = HG-09) instead · c decline | **a** — Precedent (Donegal/NZTA); closes the owed row. | |
| E4-R4d | HG-03 D-SOURCES.8-1 — camreg_bellevue_wa (US): which option? (GL-GATE-07: ARGUABLE (express non-commercial clause; closest precedent: Lexington's indemnify-and-defend clause was flipped)) | a flip under GL-GATE-07 (US) · b ask the City of Bellevue for written authorization · c decline | **c** — Follows A-9 (I7-C6): if SIG's use may be commercial, the express NC clause means decline/facts-only; option b needs outside contact. | |
| E4-R5 | HG-03 D-SOURCES.9-1 — procportal_chicago_il: which option? (GL-GATE-07: PRECEDENT (camreg_chicago_il: same data.cityofchicago.org portal, terms uncaptured, flipped)) | a flip under GL-GATE-07 (US) · b capture the Chicago ToU first · c decline | **a** — Same portal as the flipped camreg_chicago_il. | |
| E4-R6a | HG-03 D-SOURCES.9-4 — bidnet_direct: which option? (GL-GATE-07: ARGUABLE (no vendor-platform procurement portal has ever been flipped)) | a capture bidnetdirect.com terms, then decide · b flip under GL-GATE-07 now · c decline | **a** — Capture bidnetdirect.com terms in Round 11, then decide (never flipped a vendor platform blind). | |
| E4-R6b | HG-03 D-SOURCES.9-4 — periscope_s2g: which option? (GL-GATE-07: ARGUABLE) | a close as superseded by bidnet_direct (WONTFIX) · b review with R6a | **a** — The row itself calls it superseded. | |
| E4-B2 | HG-03 D-R10-SOURCES-1 — Part VIII preflight for 5 families (all not_assessed): which option? (GL-GATE-07: NOT COVERED (Part VIII, not rights)) | a a Round-11 ticket screens + the operator signs clear in one line per family · b keep not_assessed (the live stage stays blocked) | **a** — A Round-11 ticket screens; the operator signs 'clear' per family (P27.2 precedent). | |
| E4-B3 | HG-03 D-P32.20-1 — SRC-027 network-audit workbooks: which option? (GL-GATE-07: NOT COVERED (prohibited_until_review: plates, persons, queries)) | a keep it metadata-only permanently: record the workbook path rejected · b commission an aggregate-only design · c leave it prohibited_until_review (owed) | **a** — SRC-027 workbooks hold plates/persons/queries; the dossier does not depend on them. | |
| E4-B4 | HG-03 D-P32.20-1 — SD PAB recommendation (~16 MB) + ALPR Use Policy (recorded 403): which option? (GL-GATE-07: n/a (method, not rights)) | a approve a per-target byte-bound exception + one bounded retry; outcomes recorded honestly · b record both as honest refusals; the recommendation stays proposed · c drop both | **a** — One bounded retry and a byte-bound exception are not circumvention; outcomes recorded honestly. | |
| E4-S1 | HG-03 D-SOURCES.12-1 — (status): which option? (GL-GATE-07: EXECUTED) | a approve PARTIAL → DONE (2026-09-26, P31.13) · b → WONTFIX for the 68 unrecoverable rows, re-armed on an infrastructure change · c keep PARTIAL | **a** — Executed 2026-09-26 (P31.13). | |
| E4-S2 | HG-03 D-SOURCES.9-2 — bonfire (status + decision): which option? (GL-GATE-07: ARGUABLE) | a re-scope from robots wall to rights + engineering, capture terms, decide later · b decline → WONTFIX (2 tenants, no parser) · c keep as is | **b** — 2 tenants, no parser, login-walled (F1: wontfix, re-arm via Stream I). | |
| E4-S3 | HG-03 D-SOURCES.9-3 — opengov_procurement (status): which option? (GL-GATE-07: NOT COVERED (WAF challenge; SIG-INGEST-013 still binds)) | a later-phase(trigger: documented public endpoint + reviewable terms) · b WONTFIX, re-armed on the same trigger · c keep OPEN | **a** — Later-phase with trigger: documented public endpoint + reviewable terms. | |
| E4-S4 | HG-03 D-SOURCES.7-1 — (status): which option? (GL-GATE-07: EXECUTED for 4 of 5) | a approve OPEN → PARTIAL (4/5 flipped 2026-09-18; remainder dot_511_tx = R3) · b keep OPEN | **a** — 4 of 5 flipped; remainder is R3. | |
| E4-S5 | HG-03 D-JURIS.2-1 — (register placement): which option? (GL-GATE-07: n/a) | a move it out of the "Rights/reviewer" lane into "Operator credentials/outreach" (Appendix B, OPERATIONAL_READINESS §(f3)); moot if R1 = a · b leave it | **a** — Moot once R1 = a. | |

#### A-7 members — Tier-1 batch lines and confirmations (answered by A-7) (17 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| E4-B1 | HG-03 D-R10-SOURCES-1 — rights basis for the 23 new targets in §4 (3 dossier families + 2 pilot families; 3 lanes each): which option? (GL-GATE-07: PRECEDENT (P29.3 applied it to municipal CCOPS reports; Q-19 proposes it as the default)) | a apply GL-GATE-07 (US) to all three lanes, batch-wide · b decide per target after terms are captured · c defer the live stage | **a** — In A-7: GL-GATE-07 US basis for the 23 dossier/pilot targets, after the URL reconciliation ticket. | |
| E4-B5 | HG-03 D-R10-SOURCES-1 — 4 targets already on green sources (OSCN §7-606.1 ×2, ops manual §5-118, purchasing index): which option? (GL-GATE-07: EXECUTED (GL-GATE-03, 2026-09-10)) | a confirm that no re-approval is needed (the row says so itself) · b re-review anyway | **a** — Already executed under GL-GATE-03. | |
| E4-B6 | HG-03 D-P32.21-1 — registry rows for SRC-006/007/011 (registered_source: null): which option? (GL-GATE-07: follows B1) | a Round 11 adds 3 rows (OMES, DAC, CA State Auditor) on the B1 basis · b add the rows gated only · c drop the incremental families (dossier families only) | **a** — In A-7: follows B1. | |
| I7-RB-01 | HG-03 batch RB-01: US agency GIS/open-data layers (Flock/LPR/CCTV/ATE/PCAM aggregates on ArcGIS, Socrata, CKAN) (n=38 (32/6)) | a flip all under GL-GATE-07 US · b per target after an org-level terms capture · c defer | **a** — Precedent-consistent per I7 (PRECEDENT: P26.16 camreg_* flips, incl. items with licence "none" (camreg_txdot_rep_tx) and portal terms uncaptured (camreg_chicago_il)); Part-VIII-flagged members still need their S-line. | |
| I7-RB-02 | HG-03 batch RB-02: US state DOT / state camera layers (DE, VT, WV, MI, NC …) (n=8 (5/3)) | a flip under GL-GATE-07 US · b per target · c defer | **a** — Precedent-consistent per I7 (PRECEDENT: dot_511_la/ga/al/md flipped 2026-09-18 and live); Part-VIII-flagged members still need their S-line. | |
| I7-RB-03 | HG-03 batch RB-03: US statutory, oversight, CCOPS and policy documents (state reports, AG registries, CCOPS reports, police policies) (n=57 (41/16)) | a flip, PublicRecord-FactualCompilation · a′ flip, DerivedFacts-Citations where only facts + citations are emitted · b per target · c defer | **a (a′ where only facts + citations are emitted)** — Precedent-consistent per I7 (PRECEDENT: P29.3 CCOPS flips (ccops_oakland, _cambridge, _somerville → PublicRecord), okcpd_policy, ADR-085 derived-facts basis (ccops_seattle)); Part-VIII-flagged members still need their S-line. | |
| I7-RB-04 | HG-03 batch RB-04: US agenda, procurement, grant and records documents outside the live platforms (n=38 (13/25)) | a flip under GL-GATE-07 US · b per target · c defer | **a** — Precedent-consistent per I7 (PRECEDENT: okc_council, okc_procurement, the procportal_* flips, legistar (US local public records)); Part-VIII-flagged members still need their S-line. | |
| I7-RB-05 | HG-03 batch RB-05: US federal works (DHS privacy documents, DOJ, CBP, Federal Register, courts, OMB) (n=17 (6/11)) | a flip, CC0-1.0 · b per target · c defer | **a** — Precedent-consistent per I7 (PRECEDENT: usaspending, gao_surveillance_reports, dhs_oig_reports, fema_hsgp_allocations (17 U.S.C. §105 → CC0-1.0); DOJ (I7-F033) and CBP (I7-F070) state publi); Part-VIII-flagged members still need their S-line. | |
| I7-RB-06 | HG-03 batch RB-06: explicit open licence or public-domain statement (CC-BY, CC0/"Public Domain" metadata, OGL, OGL-Canada, Etalab, NLOD, Auteurswet art. 11, WTSC's copy/distribute statement) (n=46 (9/37)) | a flip on the verbatim licence · b per target · c defer | **a (flip on the verbatim licence)** — Precedent-consistent per I7 (PRECEDENT: GL-GATE-06 flips on verbatim licence metadata (procportal_nyc_ny "Public Domain" → CC0-1.0; the OGL UK rows)); Part-VIII-flagged members still need their S-line. | |
| I7-RB-07 | HG-03 batch RB-07: journalism, NGO and academic publications: facts + citations only (n=15 (2/13)) | a flip, DerivedFacts-Citations (never re-host) · b per target · c defer | **a** — Precedent-consistent per I7 (PRECEDENT: P27.2 state_alpr_statute_inventory (NCSL, a private nonprofit → DerivedFacts-Citations), pathways_*, carnegie_ai_gsi); Part-VIII-flagged members still need their S-line. | |
| I7-RB-09 | HG-03 batch RB-09: existing gated registry rows that a candidate matches (flip the row) (n=4 (0/4) + 1 flagged) | a flip each existing row (E4 §2 recipe) · b keep gated | **a** — Precedent-consistent per I7 (PRECEDENT per row: dhs_fusion_centers (federal §105), ccops_boston/ccops_berkeley (P29.3 CCOPS), aclu_cell_site_simulators (facts + citations)); Part-VIII-flagged members still need their S-line. | |
| I7-RG1 | Rights line RG1: DHS Fusion Center Locations and Contact Informatio… (GL-GATE-07: PRECEDENT (federal §105 → CC0-1.0: usaspending, gao_surveillance_repor…) | a flip the existing row (flip recipe, E4 §2) · b keep gated | **a** — Federal work (§105) precedent; member of RB-09. | |
| I7-RG2 | Rights line RG2: Boston annual surveillance report and supplements (GL-GATE-07: PRECEDENT (GL-GATE-07 US → LicenseRef-PublicRecord-FactualCompilation:…) | a flip the existing row (flip recipe, E4 §2) · b keep gated | **a** — CCOPS precedent; member of RB-09. | |
| I7-RG3 | Rights line RG3: Part 107 Waivers Issued (GL-GATE-07: PRECEDENT (federal §105 → CC0-1.0: usaspending, gao_surveillance_repor…) | a flip the existing row (flip recipe, E4 §2) · b keep gated | **a** — Federal work precedent; member of RB-09. | |
| I7-RG4 | Rights line RG4: Stingray Tracking Devices: Who's Got Them? (ACLU m… (GL-GATE-07: PRECEDENT (facts + citations only → LicenseRef-DerivedFacts-Citations:…) | a flip the existing row (flip recipe, E4 §2) · b keep gated | **a** — Facts + citations precedent; member of RB-09. | |
| I7-RG5 | Rights line RG5: Berkeley surveillance annual reports policies MOUs (GL-GATE-07: PRECEDENT (GL-GATE-07 US → LicenseRef-PublicRecord-FactualCompilation:…) | a flip the existing row (flip recipe, E4 §2) · b keep gated | **a** — CCOPS precedent; member of RB-09. | |
| I7-X3 | Confirmation X3: the 46 widening configurations need no new HG-03 line (run under already-flipped or rights-resolved sources). | confirm / change | **confirm** — Default recorded by I7; answer only to change it. | |

#### B-33 — I7 remaining batch lines (2 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| I7-RB-06b | HG-03 batch RB-06b: share-alike licences (CC-BY-SA, ODbL) (n=4 (all Part VIII-flagged; decide with S-lines)) | a flip into a share-alike compartment · b facts only · c defer | **a (share-alike compartment; rides with the S-lines of its flagged members)** — Precedent-consistent per I7 (PRECEDENT + a compartment decision (§42.3; osm_physical, the CC-BY-SA portal compartment, J4 NEW-2)); Part-VIII-flagged members still need their S-line. | |
| I7-RB-08 | HG-03 batch RB-08: territorial public records (Puerto Rico SUTRA measures, USVI legislature) (n=8 (0/8)) | a treat territories as US under GL-GATE-07 · b capture each territory's terms first · c decline | **b (capture territorial terms first)** — Precedent-consistent per I7 (ARGUABLE: GL-GATE-07's "US" wording reaches territories, but no territorial row was ever flipped (NEW-6). Guam's own public-domain statement (I7-F032) moved I9b); Part-VIII-flagged members still need their S-line. | |

#### B-32 — I7 Part VIII screen lines (9 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| I7-S1 | Part VIII screen line S1: private-camera registrants: programme-level facts only; no registrant location, name or count below programme level (SIG-PUB-004 C3; J4 P8-4) (24 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S2 | Part VIII screen line S2: field allowlist: never request editor-tracking/operator/pilot fields; redacted re-serialisation only (J4 P8-5) (4 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S3 | Part VIII screen line S3: aggregate-only: publish institution-level counts; never rows (SIG-STORE-025) (7 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a (CourtListener member follows I7-C8)** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S4 | Part VIII screen line S4: residential/RF: coarsen or aggregate; never a public point layer (SIG-PUB-011..014) (13 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S5 | Part VIII screen line S5: officer names in institutional roles: §43.4 naming gate; no names from audit rows (11 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a (names suppressed under PUB-008, A-4)** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S6 | Part VIII screen line S6: free text: SIG-PUB-014a pre-publication excerpt screen; facts only (16 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S7 | Part VIII screen line S7: incidental private names (minutes, POs, contacts): extraction-time redaction (J4 P8-3/P8-6) (30 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S8 | Part VIII screen line S8: tribal sovereignty: tribal-data-governance decision first (2 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **b (metadata-only until a tribal-data-governance rule exists; matches TR lines)** — The screen is the Part VIII control; a rights line never clears it (I7). | |
| I7-S9 | Part VIII screen line S9: row-specific screen (family members, same-org hazard layers, signature blocks; see the row notes) (3 members) — ingest only the screened lane? | a) approve the screened lane for the listed members · b) keep them metadata-only (move to Tier 3) · or name members to exclude | **a** — The screen is the Part VIII control; a rights line never clears it (I7). | |

#### B-34 — I7 non-US database-right lines (21 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| I7-N1 | Non-US database-right line N1: Traffic CCTV contract (GB-ENG:Barnet; terms: CKAN license_id=None) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N2 | Non-US database-right line N2: NT Quotations and Tenders Online NS25-0080: Provis… (ISO:AU;AU-NT; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N3 | Non-US database-right line N3: Security Camera (AU-TAS:Hobart; terms: CKAN license_id=other (Other)) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N4 | Non-US database-right line N4: FragDenStaat request search API (ISO:DE; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N5 | Non-US database-right line N5: CCTV Cameras (GB-ENG:Leicester; terms: CKAN license_id=None) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N6 | Non-US database-right line N6: CCTV camera locations (GB-ENG:Barnet; terms: CKAN license_id=None) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N7 | Non-US database-right line N7: CCTV Traffic Enforcement - camera locations (GB-ENG:Barnet; terms: CKAN license_id=None) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N8 | Non-US database-right line N8: Council CCTV cameras (GB-ENG:Bristol; terms: CKAN license_id=None) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N9 | Non-US database-right line N9: Public CCTV locations - City of Edinburgh (GB-SCT:Edinburgh; terms: CKAN license_id=None) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N10 | Non-US database-right line N10: Closed Circuit Television (CCTV) Location (AU-VIC:Geelong; terms: CKAN license_id=other-open (Other (Open))) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N11 | Non-US database-right line N11: Street safety cameras (AU-NSW:Sydney; terms: CKAN license_id=notspecified (notspecified)) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N12 | Non-US database-right line N12: Emergency Services - Closed Circuit Television Cam… (AU-TAS; terms: CKAN license_id=notspecified) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N13 | Non-US database-right line N13: Provvedimento dell'11 gennaio 2024 [9977020] (Comu… (IT-TN:Trento; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N14 | Non-US database-right line N14: Дані про місцезнаходження камер відеоспостереження… (UA-18:Korosten; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N15 | Non-US database-right line N15: Joint assurance review: retrospective facial searc… (GB-SCT; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N16 | Non-US database-right line N16: Clackmannanshire - CCTV Cameras (GB-SCT:Clackmannan…; terms: CKAN license_id=None) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N17 | Non-US database-right line N17: Evidenca o izvajanju videonadzora na javnih površi… (SI-085:Novo mesto; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N18 | Non-US database-right line N18: L&RS General Scheme Briefing Paper: Garda Síochána… (ISO:IE; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N19 | Non-US database-right line N19: Gobierto Contratación — licitación ALC0230 (Illesc… (ES-TO:Illescas; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N20 | Non-US database-right line N20: FYI.org.nz — OIA requests to New Zealand Police (e… (ISO:NZ; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |
| I7-N21 | Non-US database-right line N21: Videoüberwachung in der Stadt Braunschweig (DE-NI:Braunschweig; terms: NONE-FOUND) | a flip DBRight · b capture terms first · c decline | **b** — Precedent would allow a (DBRight), but D3 does not expand non-US coverage and no counsel reviews the database right (U-013); capture terms only if Wave D international runs. | |

#### B-35…B-37 — I7 restricted-terms, terms-not-captured and tribal lines (14 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| I7-IT1 | Rights line IT1: OpenFEMA: Non-Disaster and Assistance to Firefight… (GL-GATE-07: ARGUABLE (not a redistribution prohibition, but a destroy-on-request c…) | a flip (accept the condition) · b facts-only pointer · c decline | **b** — Destroy-on-request conflicts with an insert-only spine; FEMA pages stay the funding source (with I7-C5 b). | |
| I7-IT2 | Rights line IT2: Speed Safety Cameras (Bellevue) (GL-GATE-07: ARGUABLE (express non-commercial clause on the same publisher — decide…) | a flip (accept the condition) · b facts-only pointer · c decline | **b** — Follows A-9: express NC clause and SIG may be commercial → facts-only pointer. | |
| I7-IT3 | Rights line IT3: PSPC collaborative procurement - 'Service request … (GL-GATE-07: ARGUABLE (non-commercial clause; decide with E4 R4d)) | a flip (accept the condition) · b facts-only pointer · c decline | **b** — Non-US NC clause; facts-only pointer. | |
| I7-IT4 | Rights line IT4: GETS - Government Electronic Tenders Service (GL-GATE-07: ARGUABLE (agreement terms bind any user; public notices vs confidentia…) | a flip (accept the condition) · b facts-only pointer · c decline | **c** — GETS agreement binds any user to confidentiality terms; non-US; decline. | |
| I7-IT5 | Rights line IT5: Honolulu Police Department policy - Automated Lice… (GL-GATE-07: ARGUABLE (express non-commercial clause; decide with E4 R4d: is SIG's …) | a flip (accept the condition) · b facts-only pointer · c decline | **b** — Policy facts + citation only (NC clause, A-9). | |
| I7-IT6 | Rights line IT6: Special report to Parliament: Police use of Facial… (GL-GATE-07: ARGUABLE (non-commercial clause; decide with E4 R4d)) | a flip (accept the condition) · b facts-only pointer · c decline | **b** — Non-US NC clause; facts-only pointer. | |
| I7-IT7 | Rights line IT7: Axon Fusus agency-hosted 'Connect <Place>' camera … (GL-GATE-07: NOT COVERED (captured Axon terms prohibit automated access; decide wit…) | a flip (accept the condition) · b facts-only pointer · c decline | **b** — Axon terms prohibit automated access: citation/pointer only, never fetched from Axon hosts (I7-C4 a, D3-Q3). | |
| I7-IU1 | Rights line IU1: Leonardo (ELSAG) 'Procurement Contracts' page - st… (GL-GATE-07: ARGUABLE (terms not captured — new facts first)) | a capture terms first (Round 11) · b facts + citation only now · c decline | **a** — Capture terms in Round 11, then a line; facts + citation meanwhile. | |
| I7-IU2 | Rights line IU2: Carahsoft - Cellebrite government contract vehicle… (GL-GATE-07: ARGUABLE (terms not captured — new facts first)) | a capture terms first (Round 11) · b facts + citation only now · c decline | **a** — Capture terms in Round 11, then a line. | |
| I7-IU3 | Rights line IU3: Google - Geofence Warrants by Jurisdiction, 2018 t… (GL-GATE-07: ARGUABLE (terms not captured — new facts first)) | a capture terms first (Round 11) · b facts + citation only now · c decline | **a** — Capture terms in Round 11, then a line. | |
| I7-IU4 | Rights line IU4: SoundThinking press releases - named customer rene… (GL-GATE-07: ARGUABLE (terms not captured — new facts first)) | a capture terms first (Round 11) · b facts + citation only now · c decline | **a** — Capture terms in Round 11, then a line. | |
| I7-IU5 | Rights line IU5: FlockRadar - map of disclosed ALPR / Flock deploym… (GL-GATE-07: ARGUABLE (terms not captured — new facts first)) | a capture terms first (Round 11) · b facts + citation only now · c decline | **a** — Capture the data licence (code is AGPL-3.0) in Round 11, then a line. | |
| I7-TR1 | Rights line TR1: Tribal Leaders Directory (GL-GATE-07: PRECEDENT (federal §105 → CC0-1.0: usaspending, gao_surveillance_repor…) | a defer until a tribal-data-governance rule exists · b ask the Nation (outreach, Q-28 class) · c facts + citation only | **a** — Defer until a tribal-data-governance rule exists; b is outside contact (U-011). | |
| I7-TR2 | Rights line TR2: Tohono O'odham Legislative Branch - Notice of publ… (GL-GATE-07: NOT COVERED (tribal nation; GL-GATE-07 execution never reached a sover…) | a defer until a tribal-data-governance rule exists · b ask the Nation (outreach, Q-28 class) · c facts + citation only | **a** — Defer until a tribal-data-governance rule exists; b is outside contact (U-011). | |

#### B-38 — I7 SEC EDGAR lines (4 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| I7-P1 | SEC EDGAR line P1: Verra Mobility Corp — Form 10-K for fiscal 2025 (a… — now that Q-30 is answered (U-014), approve a facts-only basis? | a) facts-only (LicenseRef-DerivedFacts-Citations; vendor-authored text not re-hosted); first request only after the contact@ alias exists (OD-04) · b) defer to a later round (I8) · c) decline | **a (rights) with ingestion later-phase per I8** — SEC filings are public; I8 schedules EDGAR for a later round; the alias keeps the personal address out of SEC request logs. | |
| I7-P2 | SEC EDGAR line P2: Cellebrite DI Ltd. SEC filings (Form 20-F annual r… — now that Q-30 is answered (U-014), approve a facts-only basis? | a) facts-only (LicenseRef-DerivedFacts-Citations; vendor-authored text not re-hosted); first request only after the contact@ alias exists (OD-04) · b) defer to a later round (I8) · c) decline | **a (rights) with ingestion later-phase per I8** — SEC filings are public; I8 schedules EDGAR for a later round; the alias keeps the personal address out of SEC request logs. | |
| I7-P3 | SEC EDGAR line P3: SEC EDGAR full-text search (efts) - multi-vendor s… — now that Q-30 is answered (U-014), approve a facts-only basis? | a) facts-only (LicenseRef-DerivedFacts-Citations; vendor-authored text not re-hosted); first request only after the contact@ alias exists (OD-04) · b) defer to a later round (I8) · c) decline | **a (rights) with ingestion later-phase per I8** — SEC filings are public; I8 schedules EDGAR for a later round; the alias keeps the personal address out of SEC request logs. | |
| I7-P4 | SEC EDGAR line P4: SoundThinking, Inc. (formerly ShotSpotter, Inc.) F… — now that Q-30 is answered (U-014), approve a facts-only basis? | a) facts-only (LicenseRef-DerivedFacts-Citations; vendor-authored text not re-hosted); first request only after the contact@ alias exists (OD-04) · b) defer to a later round (I8) · c) decline | **a (rights) with ingestion later-phase per I8** — SEC filings are public; I8 schedules EDGAR for a later round; the alias keeps the personal address out of SEC request logs. | |

#### B-39 — I7 conflicts (C1 and C6 are Part A) (9 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| I7-C2 | Conflict C2: DocumentCloud / MuckRock "no data mining" | a link-only; acquire each origin agency's release instead · b named-document review one by one (E4 R2a option c) | **a** — Link-only; acquire each origin agency's release instead. | |
| I7-C3 | Conflict C3: Sourcewell and OMNIA prohibit robots and reproduction vs registry rows sourcewell ("Dominant acquisition channel") and omnia_partners | a contract-id pointers only; acquire purchases from agency-side records (checkbooks, agendas, state sales registers) · b seek permission · c decline both rows | **a** — Contract-id pointers only; purchases from agency-side records. | |
| I7-C4 | Conflict C4: Vendor platform terms | a programme facts only from the agencies' own pages; no fetch from vendor hosts · b seek vendor permission · c decline | **a** — Programme facts from agencies' own pages; never fetch vendor hosts (D3-Q3). | |
| I7-C5 | Conflict C5: Revocation / destroy-on-request (NEW-3) | a accept, with a withdrawal-by-new-claim policy (suppress from future releases; history kept) · b accept Chicago/ABQ (city portals, already flipped) but decline the OpenFEMA API route (FEMA pages stay the funding source) · c decline all three | **b** — Chicago/ABQ city portals (already flipped) accepted with a withdrawal-by-new-claim policy; OpenFEMA API route declined (IT1 b). | |
| I7-C7 | Conflict C7: SDPC registry is member-only (I4-C200) | a facts only from district-side pages · b partnership · c decline | **a** — Facts only from district-side pages; partnership is outside contact. | |
| I7-C8 | Conflict C8: CourtListener bulk vs the deferred courtlistener_recap (I6 NEW-1; E4 R2b) | a a new per-source basis (PDM) for the bulk route only, S3 screen for party names · b keep deferred with R2b | **b** — Keep CourtListener deferred (courts dark this round per I8; party names are Part VIII-heavy). | |
| I7-C9 | Conflict C9: NCSL inventory vs statutes at origin | a refresh the seed from origins (W, X3) · b keep the frozen seed | **a** — Refresh the statute seed from legislature origins (W, X3). | |
| I7-C10 | Conflict C10: SEC EDGAR contact string vs P16 | Q-30 | **answered** — Q-30 answered by U-014; see I7-P1…P4 and OD-04. | |
| I7-C11 | Conflict C11: Edmonton basis (E4 R4a) | a decide R4a on the OGL-Edmonton basis once the body is captured · b keep R4a's DB-right option | **a** — Decide E4 R4a on the OGL-Edmonton basis once the body is captured. | |

#### B-40 — I7 confirmations (3 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| I7-X1 | Confirmation X1: the 19 Tier-3 candidates whose captured terms prohibit (T1–T19) stay declined; facts only as pointers to origins. | confirm / change | **confirm** — Default recorded by I7; answer only to change it. | |
| I7-X2 | Confirmation X2: the 26 Part VIII blocks are existence/metadata only, never ingested. | confirm / change | **confirm** — Default recorded by I7; answer only to change it. | |
| I7-X4 | Confirmation X4: registry and tenant label corrections M1–M7 go into a Round-11 correction ticket (ACQ-02). | confirm / change | **approve** — Default recorded by I7; answer only to change it. | |

#### B-22 — K-row design recommendations accepted by K-BATCH (58 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| D-K0-2 | Replace React with Preact on public surfaces | as recommended / other | **Yes (−60 KB gzip per T2 page; same API shape)** | |
| D-K0-3 | Put the rounded map viewport in URLs (at=) | as recommended / other | **Yes, with the precision rule (§4.5)** | |
| D-K0-5 | Treat application/ld+json blocks as data (allowed on T1), leaving the "whether" to J3 D-J3-7 | as recommended / other | **Yes** | |
| D-K1-3 | Basemap extent and refresh: planet z0–15 (R2) or z0–14 (GCS); twice-yearly manual refresh | as recommended / other | **as stated** | |
| D-K1-4 | Coverage semantics: (a) counts in single-source cells are shown with a "1 source" label, not suppressed; (b) crowdsourced global sources do not count as "SIG has looked" | as recommended / other | **Yes to both** | |
| D-K1-6 | Symbol semantics: filled = corroborated, hollow = single source, double ring = contested; single-source sites shown by default | as recommended / other | **Yes** | |
| D-K1-7 | "My location" button (browser-only geolocation after a click; never sent to SIG) | as recommended / other | **Yes** | |
| D-K1-8 | Ship an early "honest map now" slice (MAP-01a + basemap in today's island) before the full app rewrite | as recommended / other | **Yes if the rewrite is more than ~2 weeks away** | |
| D-K2-3 | Degree-only sharing data | as recommended / other | **node attribute sentences only (SIG-INGEST-043c); confirm** | |
| D-K2-5 | Supply relevance | as recommended / other | **exclude unclassified procurement from O1; show it on buyer pages as "not classified"** | |
| D-K2-6 | URL scheme and page waves | as recommended / other | **adopt §3.3 and waves E1 → E2 → E3** | |
| D-K2-7 | "Possibly the same" wording for unresolved same-name entities | as recommended / other | **adopt H-8's text; never merge or add counts** | |
| D-K3-1 | Adopt release search v2 (federated FTS5 behind the release-pinned API + static catalog typeahead shards); no hosted engine, no Pagefind, no live-spine search on the site | as recommended / other | **Yes** | |
| D-K3-2 | Alias governance: aliases are reviewed data rows with a cited expansion; expansion only, never a characterization or relationship | as recommended / other | **Yes** | |
| D-K3-4 | Query logging | as recommended / other | **None; aggregate counters only** | |
| D-K4-2 | Disputed-territory point of view (TW, PS, HK, XK, EH, Crimea) | as recommended / other | **ISO 3166-1 as published; XK labelled user-assigned; neutral names; one standing note** | |
| D-K4-3 | Which sub-state dossiers get pages | as recommended / other | **all counties with ≥1 record (2,482); places with ≥10 records (2,817) + any place with non-site evidence; non-US admin-1 with ≥10 (218)** | |
| D-K4-4 | US territories: under the United States or as countries | as recommended / other | **under US (Census state-equivalents), with ISO 3166-1 aliases** | |
| D-K4-5 | Placement precedence placement@1 (located wins; R3 repair heuristics fall back to declared) | as recommended / other | **adopt; revisit when first-class Jurisdiction entities land** | |
| D-K4-6 | URL scheme (alpha-3 country segment; name-GEOID slugs) | as recommended / other | **adopt; keep /dossier/ as the index root** | |
| D-K4-7 | Publication profile for dossiers in countries without an adapter | as recommended / other | **conservative (no public-employee names) until an adapter exists (SIG-PUB-017)** | |
| D-K5-1 | Which dossier levels get materialised download files | as recommended / other | **country + admin-1 materialised; county/place via key columns + recipe (+ optional rate-limited API)** | |
| D-K5-3 | Show sources that no longer contribute (withdrawn, disappeared, not re-asserted) | as recommended / other | **yes, as "previously contributed" with dates and reason, below the table** | |
| D-K5-4 | Merge PKG-10's per-dossier provenance into DSRC-01 | as recommended / other | **yes (one owner)** | |
| D-K6-1 | Default composition: the map in "At a glance", network figures in their sections, scoped search in the Explore bar, all static and printable | as recommended / other | **Yes** | |
| D-K6-2 | The interactive map loads in place only on click, on desktop; phones navigate to /map/; no automatic loading on scroll | as recommended / other | **Yes (keeps dossiers T1; K0 §4.3)** | |
| D-K6-3 | Network figures are static (≤ 40 nodes, grouping only, no ranking); no in-page graph explorer; expansion in /explore/ | as recommended / other | **Yes** | |
| D-K6-4 | Static binning rule (areas ≥ 12 px across; points only at z ≥ 10 and ≤ 1,000 records), and ask K1 to tune its band table to the same rule | as recommended / other | **Yes** | |
| D-K6-5 | "Download figure (SVG)" only for country and admin-1 dossiers in Round 11 | as recommended / other | **Yes (≈ 1.7k objects vs ≈ 28k)** | |
| D-K6-6 | Print: locator on page 1 (council brief); the map leads page 2 | as recommended / other | **Yes** | |
| D-K6-7 | One legend lexicon: hollow = one source (map); line pattern = access kind; currency = muted ink + words; no "hollow" in network figures (NEW-2) | as recommended / other | **Yes (with D-K14-5)** | |
| D-K7-1 | Which decision kinds are in v1? | as recommended / other | **solicitations + agenda items + contracts with end_date (as contract_expiry); renewals as data allows; bills and grants in v1.1** | |
| D-K7-2 | Daily watch lane between releases (G3 publish-class status extended to watch/), or watch-only-at-release? | as recommended / other | **the lane; release-only cannot serve agenda alerts** | |
| D-K7-4 | Lead-time windows (§5.2) | as recommended / other | **as proposed; revisit after 2 months of data** | |
| D-K7-5 | Generate feeds for every place (valid but empty) or only for places with items? | as recommended / other | **every place, so subscribers can come early** | |
| D-K7-6 | Title policy for agenda items that may name people | as recommended / other | **verbatim title only when the person-name screen passes; otherwise matter number + matched term** | |
| D-K8-1 | May claim views quote an excerpt from derived-only sources, and how long? | as recommended / other | **a locator always; an excerpt of ≤300 characters only where the source's recorded terms permit quotation (J4 per-source evidence); otherwise none. Needs E/J4 input; not legal advice** | |
| D-K8-2 | Claim-view scope and cap | as recommended / other | **document genres with actual_capture; cap 20k per release; overflow count disclosed** | |
| D-K8-3 | Are /evidence/artifact/<handle>/ pages latest-view aliases of the release anchors, or separate pages? | as recommended / other | **aliases (one template, one data path); citations always go to /r/<pub>/…** | |
| D-K8-4 | Show the 255 synthetic "run record" artifacts before activation, or hide /evidence/ until real captures are bound? | as recommended / other | **show them with honest labels. They are what every claim points to today, and hiding them repeats the blank page** | |
| D-K9-1 | Between releases, offer per-source "interim" extracts of newly ingested data (would need the publication, attribution and scrub gates in the status lane)? | as recommended / other | **No. "Latest" = latest release; use G3's early-cut trigger instead** | |
| D-K9-2 | Per-source history before Round 11: (a) manifest-only entries (D-J3-10); (b) re-derive per-source slices from the 3 restricted snapshots with corrected attribution, labelled "re-derived"; (c) omit | as recommended / other | **(a) — the snapshots carry NEW-1 rows and wrong attribution** | |
| D-K9-3 | Rename: nav label "Sources", canonical /sources/, /data-freshness/ 301s | as recommended / other | **Yes** | |
| D-K10-2 | Entity-browse cap (10 pages / 1,000 rows per source) | as recommended / other | **Yes; larger sources use the download, API and K3 search** | |
| D-K10-3 | Show review_packet links (packets live in the repo) | as recommended / other | **Per D-J3-13: basis/role/date now, packet text per packet after review** | |
| D-K11-1 | Are per-object field gaps (≈243k, OSM and DOT) research tasks? | as recommended / other | **no. Show OSM-field gaps as campaigns (routed to MapRoulette under HG-08 later). Show DOT-registry field gaps as coverage metrics only (there is nothing to research)** | |
| D-K11-2 | Approve the handle grammar (§3) for tasks, campaigns, watch items and evidence artifacts | as recommended / other | **approve; K13 aligns it with K2's entity labels** | |
| D-K11-3 | Publish records-request drafts (statute + SIG template) on public task pages? | as recommended / other | **yes: statutes are public law, the templates are SIG's own text, no requester data, never sent** | |
| D-K11-5 | Are curation-lane tasks (ER pairs, vocabulary) public? | as recommended / other | **counts only; the work stays in the loopback curation app** | |
| D-K11-6 | Jurisdiction claiming (SIG-TASK-010/011) needs identity. Defer? | as recommended / other | **defer; v1 shows "anyone may work this task"** | |
| D-K13-2 | Navigation: six sections; Watch top-level; Open questions and "How sure is SIG?" under About; Disagreements under Explore (C-31) | as recommended / other | **Yes** | |
| D-K13-3 | Map technology in one data hue until PKG-07 typing is live (C-02, with D-K14-5) | as recommended / other | **Yes** | |
| D-K13-5 | New route names: /disagreements/, /changes/, /entity/ hub; retire /task/new/ (410) and never build /site/ or /map/place/ | as recommended / other | **Yes** | |
| D-K14-2 | The name stays "Surveillance Infrastructure Graph (SIG)" at surveillancegraph.org; logo direction: a node-link glyph with one dashed edge | as recommended / other | **yes** | |
| D-K14-3 | Typeface: Public Sans Variable (26.2 KiB, OFL) vs the system stack (0 KiB) | as recommended / other | **Public Sans: one consistent identity across operating systems for less than a sixth of the T1 budget** | |
| D-K14-4 | Dark mode follows the OS setting only (no toggle, no stored preference) in Round 11 | as recommended / other | **yes** | |
| D-K14-5 | Palette change: support moves to a slate ramp; contested and unresolved share raspberry (no red); amber means provisional; blue means links and data; categorical data uses one hue plus shapes. Approve the lexicon labels (§3.4, including "Stated absent") | as recommended / other | **yes** | |
| D-K14-6 | Amend SIG-UI-044 to "full on record pages, a one-line summary one action away elsewhere"; the compact cite and dispute forms (SIG-UI-033/035 substance unchanged); the golden place(s) for onboarding (with C5 Q-C5-2 / D3 §4) | as recommended / other | **yes; golden place per D3** | |

#### Routed K-row items (answered by the packet line named) (11 lines)

| line | decision | options | rec. — why | answer |
|---|---|---|---|---|
| D-K10-1 | Approve the §6 disclosure texts verbatim (GL-GATE-07, outside-rule, terms-conflict, counsel caveat, date correction, gated/refused) | see OD-07 | **Approve or edit; they ship via ops/disclosures.toml** — merged into OD-07 | |
| D-K10-4 | Publish SIG's reliability class (default_tier) with its justification per source | see OD-07 | **Yes, after the operator reviews the justification texts in batches** — merged into OD-07 | |
| D-K9-4 | Confirm the lifecycle state names and the header sentence (§3.3, agent-drafted) | see OD-07 | **Confirm or edit verbatim** — merged into OD-07 | |
| D-K5-2 | Wording for "first/last seen by SIG" vs "source-reported date" | see OD-07 | **adopt K5-P3 labels; approve the agent-drafted glossary text verbatim** — merged into OD-07 | |
| D-K4-8 | Corrections-log wording for merged, mislabelled and re-placed pages | see OD-07 | **approve agent drafts verbatim** — merged into OD-07 | |
| D-K1-2 | Host the basemap on R2 (needs moving the surveillancegraph.org DNS zone from Squarespace to Cloudflare's free plan, which J3 TX-11 also needs; ≈ $3/mo at 10k sessions, ≈ $13 at 100k) or on a same-origin GCS bucket (no DNS change; ≈ $6 / ≈ $43; needs the budget alert) | see Q-31 | **R2 with the DNS move, if you are comfortable moving DNS; otherwise GCS now and R2 with TX-11** — merged into Q-31 | |
| D-K0-4 | Host tiles and basemap on the zero-egress origin (R2) shared with J3 TX-11, or on GCS behind the LB | see Q-31 | **R2 once J3 TX-11 exists; GCS acceptable below ~10k sessions/month (≈ $2–3)** — merged into Q-31 | |
| D-K1-5 | Non-US place names: GeoNames cities15000 (CC BY 4.0, attribution) or Natural Earth populated places (public domain, fewer names) | see OD-09 | **GeoNames (better recall; attribution is cheap)** — merged into OD-09 | |
| D-K3-3 | City layer for non-US places: Natural Earth populated places (public domain) now; GeoNames cities15000 (CC BY 4.0, needs attribution) only if NE proves too thin | see OD-09 | **NE now (an HG-03-style rights check alongside D-K4-1)** — merged into OD-09 | |
| D-K7-3 | May place pages with no monitoring link to official portals and peer alert services (alpr.watch, C5 L4/Q-C5-4)? | see D3-Q4 | **link to official agenda portals always; peer services per C5's link policy** — merged into D3-Q4 | |
| D-J3-12 | Approval flow for per-source descriptions and known-issue texts (agent drafts in batches of ~25; operator confirms verbatim; pages show description_pending_review until then). | see OD-07 | **see OD-07** — merged into OD-07 | |
