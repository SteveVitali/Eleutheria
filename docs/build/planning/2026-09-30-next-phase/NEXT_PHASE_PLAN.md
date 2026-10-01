# SIG Round 11 — the next-phase plan

> **CANONICAL for Round 11 — GATE-P passed 2026-10-01T05:03:05Z.** The operator answered all 99 packet lines in 23
> interactive rounds (2026-10-01T03:41:19Z → 05:03:05Z); the verbatim answers and the labelled agent interpretations are in
> `feedback/RATIFICATION_LOG.md`, committed as `de0b3591`. S6 folded every answer into this plan and its data
> (2026-10-01T05:55:53Z, `date -u`); `design/S6-ratification-applied.md` lists each change. Where this plan and the log disagree,
> the log wins and S6r records the fix. Recommendations were the agent's; every decision below is the operator's, and
> 27 lines differ from the recommendation (§4.6). Text marked *agent-drafted* ships only after the operator confirms it
> word for word (B-2). This is not legal advice (P4).

- **Row:** S3 of `META_PLAN.md` (Stage P, synthesis), revised by **S4c** (review closure), ratified at **S5 / GATE-P**, and
  made canonical by **S6** (this revision). **Drafted (S3):** 2026-10-01T01:13:07Z → 01:26:35Z (`date -u`) by Claude Code
  (Opus 5.5) in the planning worktree `~/Eleutheria-next-phase`, branch `claude/next-phase-planning`, from HEAD `9262a959`;
  the orchestrator committed it as `c3e37654`. **Revised (S4c):** 2026-10-01T02:38:06Z → 02:55:12Z from HEAD `3208c8e0`
  (`reviews/REVIEW_CLOSURE.md`); committed as `e5936f96`, unchanged through GATE-P (`de0b3591`; sha256 of the plan shown at
  S5: `3e7e8970…cfeb8`). **Applied (S6):** 2026-10-01T05:55:53Z from HEAD `43f82494`. Chain tip: `b051732c`
  (`devin/p33-8-agent-docs-refresh`, PR #190).
- **Read-only (P3, P10).** S6 wrote only this file, `data/round11_plan.csv`, `data/ticket_catalog.csv`,
  `data/decision_catalog.csv` (new columns `operator_answer`, `answered_at`) and `design/S6-ratification-applied.md`. No
  control file, spec, ADR, manifest, LEDGER, register or production system was touched; nothing was committed; no external
  request was made (P16). No secret appears here (P14); the operator's e-mail address is written only as "the operator's
  address".
- **Evidence class.** `inference` from the cited planning artifacts and the ratification log, except counts, which are the
  mechanical outputs of checkers re-run at S6: the S4c ordering check (`docs/build/logs/next-phase/S4c/check_order.py`,
  gitignored), `check_silence.py` and `check_trace.py`, and S1b's `tools/check_dispositions.py` (structural validity, not
  truth — F-27). Paths are relative to `PD = docs/build/planning/2026-09-30-next-phase/` unless they start with `docs/`, a
  package name or `~`.
- **Synthesis inputs (P1):** as listed for S3 and S4c (`META_PLAN.md` §1–§5, §7, §7.1, §8–§11; `feedback/OPERATOR_FEEDBACK.md`;
  `design/S2-round-structure.md`; `data/round11_plan.csv`; `data/ticket_catalog.csv`; `research/S1a-ticket-catalog.md`;
  `universe/`; `design/S1c-decision-catalog.md` + `data/decision_catalog.csv`; D3, K13, L3, I8, J3, G2, G3, B3, B4, E2, K0,
  H1, H2, B5, B1, F2a, F2b, G1, B6, B7; `findings/`; `baseline/`; `review/REVIEW_SYNTHESIS.md`; the three S4 reviews). **S6
  inputs:** `feedback/RATIFICATION_LOG.md` (whole), META_PLAN §3, §6 (S6 row) and §9, the S1c packet tables and member
  appendix, I8 §0/§7.4/§8/§9, K0 §6, K2 (D-K2-4), and the spec clauses SIG-INGEST-036/037/046c, SIG-PUB-002/003/003a,
  SIG-GOV-001/002/008/012/013/015/017, SIG-LIC-009 and SIG-UI-042 (by grep).
- **Precedence.** The ratification log over everything below it; S6 over S4c; S4c over S3; S3 over S2; S2 over
  S1a/S1b/S1c; L3 over F4/F2b. Every disagreement S3 settled is in **Appendix B**; every S4 finding is closed in
  `reviews/REVIEW_CLOSURE.md`; every S6 change is in `design/S6-ratification-applied.md`.

---

## 0. The plan on one page

**Round 11 makes SIG show, correct and open up the evidence it already holds, while growing US-wide vendor coverage
from high-quality origins** (D3 §0, ratified at A-17 with one edit: vendor-hosted public pages are fetched). It runs as
**one round, one manifest, one LEDGER and one `orchestrate-build` loop**, cut into four gated sub-rounds and a short tail
(S2 §0, §3.3; U-012), executed by **Devin Desktop (`swe-2-high`, 256k context)** and closed by a **post-round deep
review by Claude Code (Opus 5.5, xhigh)** (A-15).

| unit | phase | chain rows | eng. runs (of which PLAN) | leg runs* | purpose | ends with |
|---|---|---|---:|---:|---|---|
| Stage-B seed | — | 20 units (not chain rows; ≈ 30 contexts) | 24.25 | — | truthful memory, guard core, 30 operator-decision ADRs, spec families, manifest + **11A** contracts, registers | **GATE-B** |
| **11A** Safe, honest, truthful | P34 | 59 (201–259) | 56.0 (7.0) | 8.5 | the deferred Track-0 items first (handles, bucket tree, `/visual-language/`, drill, TLS alert, budget alert); S0 removals and fixes live; CI pinned and read; memory guards; Round-10 schema live; quality baseline; honest-posture ER re-run; **PLAN-11B** | P34.47 + **GATE-G4** |
| **11B** Correct and traceable | P35 | 83 (260–342) | 81.0 (7.0) | 11.0 | Wave A; **Wave B code (incl. the direct Flock transparency-portal connector) + activation queued**; identity/time/geography fixes; transparency exports; release pipeline; **first model release** | P35.63 (HG-11) + P35.64 + **GATE-G5** |
| **11C** Explorable core | P36 | 77 (343–419) | 72.5 (6.0) | 4.0 | **Wave C queued (US-first, non-US kept)**; Flock share-list claims; Axon Connect, DocumentCloud and Sourcewell/OMNIA connectors; design system; first working page per U-003 ask; core-surfaces release carrying Wave B's data | P36.72b (HG-11) + P36.73 + **GATE-G6** |
| **11D** Explored and proven | P37 | 80 (420–499) | 69.0 | 5.0 | graphs and explorer; `/quality/`; **Wave D (in scope) incl. international portals and AU keyed APIs**; single-operator deletion path; "My location"; final release; 13 journeys | P37.65b (HG-11) + P37.68a–d CAP-01 |
| **Tail** | P38 | 10 (500–509) | 7.0 | — | CAP-lite → **GATE-ACCEPT-R11** → REC → DOC → announce review → **GATE-ANNOUNCE** | — |
| **total** | P34–P38 | **309** (ticket 286 · plan 3 · capstone 11 · gate 5 · reconcile 3 · docs 1) | **285.5** (PLAN 20.0; 1.0 conditional) | **28.5** | | 5 gate markers; 19 never-pre-authorised in-ticket pauses (+2 conditional) |
| Post-round | — | 1 unit, not a chain row | ≈ 8 (8–12 Claude Code contexts) | — | deep review of the whole round, read-only | findings register + next-round planning input |

\* Separately dispatched live-leg re-runs (OM-19; `leg_runs` in the CSV). OM-20 is ratified and the 11A list approved
(S5-3), so the 13 listed 11A rows need no per-row go.

- **Executor and sizing (A-15).** Devin Desktop runs every Round-11 ticket; it pauses only at HG gates (HG-03 lines,
  HG-11/Class S readouts), one ING-GO per acquisition wave, spend above the ceiling, red CI (`blockedOn`) and production
  mutations not on an approved OM-20 list; one digest per wave with a spend line. There is no in-round second harness: the
  mechanical guards (B4 guard core, B6 controls, CI) are the in-round independent check. Every ticket's Load list +
  working set must fit the 256k window with headroom (**target ≤ ~150k tokens loaded**); ten rows look oversized and are
  split at T3 or at their PLAN row's sizing review (§8.5). Harness and model are recorded per ticket in CURRENT STATE and
  in commit trailers, enforced in CI because commits keep the operator's name as author (OM-01, A-21).
- **First dispatch:** row 201 = **P34.1 TC-PIN** (must land before **2026-10-19**, the GitHub `ubuntu-latest` → Ubuntu
  26 runner change; `design/H2-branch-ci.md:113`). Fallback: the seed PR pins `runs-on: ubuntu-24.04` (FEA-16).
- **No Track-0 production change now** (A-0.1–A-0.3, A-1, A-2a). The personal handles at the repo tip, the listable
  `sig-public` 09-27 tree, `/visual-language/` and the undrilled restore stay **unresolved, operator-deferred exposures**
  (not accepted risks) until their early-11A owners land: P34.18, P34.21b (first leg), P34.17, P34.6, P34.4, P34.5.
- **S0/S1 (113 findings):** each has exactly one disposition. 109 land on seed/11A/11B units; the 3 that rested on S5
  decisions are now decided (F-31 → A-4 + the seven A-23 waivers; F-191 → C-3 recorded; F-386 → A-3 yes); 1 was already
  done (F-366). §9.4 lists the interim and partial fixes.
- **Rights and collection posture (the operator's choices).** GL-GATE-07 and GL-GATE-08 are re-confirmed; the ≈8,088
  express-terms rows stay public under a recorded acceptance; vendor-hosted public pages (Flock portals, Axon Fusus
  Connect pages), DocumentCloud/MuckRock and Sourcewell/OMNIA are fetched despite their terms inside one envelope (public,
  unauthenticated pages only; no logins, keys or circumvention; rate-limited; terms captured verbatim; exposure disclosed;
  Part VIII screen on every byte); non-US acquisition is kept (N1–N21 flip). §14 records the risks these choices accept.
- **Governance.** Disclosed single maintainer, no counsel (A-4); all seven waiver candidates WV-01…WV-07 waived in the
  operator's adopted words, each an ADR with compensating controls and a revisit trigger (§6.5); no human check this
  round — readouts and `/quality/` say "no human check performed" (B-31).
- **Money:** infrastructure ≈ $95–105/mo after 11A, ≈ $90–100 after 11B (scheduler consolidation −$7), ≈ $102–112 after
  11C and ≈ $112–122 after 11D (inference; §10.4), against the **$300/mo** ceiling, which covers infrastructure only
  (A-2). **Agent usage** is reported per wave, with a pause at any usage-limit event and no fixed cap: ≈ 400–480 Devin
  Desktop contexts (≈ 100–290 M tokens; inference) plus ≈ 8–12 Claude Code contexts for the post-round review.
- **Operator time:** ≈ **23–40 h over ≈ 21 touchpoints (plus the wave digests) in ≈ 10–11 weeks** after GATE-P (S5 itself took ≈ 1.5 h); eight
  synchronous slots; by date in §11.2. Removed by the operator's answers: OPCHECKs, the top-50 organisation review, the
  query set, the dossier "clears", any response-time duty. Added: HG-03 flip lists per wave, the gate-signing key,
  standing-go renewals.
- **Calendar (inference; windows make slips cliff-shaped — §8.8):** S5 done 10-01; seed → GATE-B ≈ 10-03→10-07 (R0);
  11A ends ≈ 10-15→10-17; 11B ≈ 10-27→11-02; GATE-G6 ≈ 11-13→11-18; final release ≈ 11-27→12-05; tail ≈ 12-03→12-12;
  then the post-round review. A-19 = a: if R0 slips past ≈ 10-07, waves slip to their next windows.
- **What remains for the operator to decide in the round** is only what the rows raise themselves: ING-GOs, each wave's
  HG-03 flip list, the 11B–11D OM-20 lists, Class R standing-go renewals, HG-11 readouts, in-ticket gos, copy batches and
  the two closing gates — plus the two unwaived MUSTs S6 found in conflict with answers (SIG-GOV-003's published SLAs vs
  B-8; SIG-INGEST-036 rule 6 vs fetching DocumentCloud/MuckRock; §14 R-31, R-18). Every other open line was answered at
  GATE-P (§4).

---

## 1. Brief and authority

### 1.1 What the operator asked for (verbatim, with `date -u` of receipt; full text in `feedback/OPERATOR_FEEDBACK.md` and META_PLAN §7.1)

| when (UTC) | operator, verbatim (excerpt) | what it set |
|---|---|---|
| 2026-09-30T16:16Z (GATE-M) | *"I approve the meta-plan. … And don't merge the PR chain, we'll just build off of it and I'll handle merging later."* | Stage P; Round 11 stacks on #190; the operator merges later |
| 2026-09-30, Wave 2 | *"… do an extremely careful, rigorous, and comprehensive search and review of additional datasets we might be missing and to configure them for ingestion and ingest them into prod. … making the data itself easily exportable … explore each third party source, link to the ground truth, download the raw data, and see ingestion logs/metrics/timestamps …"* | Streams I and J; new sources ingested **in the Round-11 build**; traced as **W2-1…W2-6** (§9.5) |
| 2026-09-30, received before 17:10:49Z (git `e5725b7b`; the "18:2xZ" stamp was false, F-074; META_PLAN §11 correction) | *"I want to do all of what you are suggesting, but this work should be planned/specified in the next round of tickets, not done now."* | S0 hotfixes and QA-1…QA-10 become Round-11 tickets (traced **PF-1…PF-3**, §9.5); alerts route to the operator's address. It answered the suggestions then on the table; the personal-handle S0s were found later, so A-0 asks about them (TS-04, TS-12) |
| 2026-09-30T21:28:52Z (U-003; feedback record — META_PLAN §7.1 stamps the same answer 21:29:45Z, an unexplained 53 s difference recorded in Appendix B row 21) | eleven numbered asks (map, network labels and global graph(s), search, grouped dossiers, sources per dossier, embedded visuals, watch QA, evidence, sortable sources with downloads, source pages, research queue) plus *"… the site be more user friendly and have richer, more interactive, searchable, traversable, inspectable … functionality"* and *"think and research and reason carefully about perhaps breaking with our no-JS constraints"* | Stream K; basemap reverses Round-9 Q8; the zero-JS rule is re-decided |
| 2026-09-30T21:58:23Z (U-005) | *"journalists need to be able to really truly explore the knowledge graph … always with full explicit transparent evidence/lineage"* | journalist journeys are primary |
| U-006 | *"I'm not that confident because I haven't done a deep audit of the mechanism by which disparate sources … are synthesized into a deduplicated knowledge graph"* | Stream L |
| U-007 | *"feature richness …, correctness and comprehensiveness of the knowledge graph data itself …, and generally it just needs to be better at making itself … clear to the user … the focus is on rich, US nationwide data on Flock and Axon and likely other vendors"* | the three outcomes (§13.2); US-nationwide vendor focus |
| U-008 | *"ideally we can keep monthly compute/storage/hosting/etc. costs below $300/mo … always check with me before proceeding with increased spend above $300/mo; … assume we have no humans on our team other than me augmented by agents"* | $300 ceiling; no human rows |
| U-009 | *"we will announce surveillancegraph.org publicly without holding back when the time is right."* | GATE-ANNOUNCE, never automatic |
| U-011 | *"agents should have maximal autonomy but budgets on money spent should always be made clear … and no one should be contacted outside the project."* | autonomy with spend transparency; no outreach |
| U-012 | *"previous builds worked pretty well so we can follow the existing patterns."* | one round, existing loop and gates |
| U-013 | *"\"counsel\" so far is just me …, we don't have counsel and for now we should just err on the side of not blocking on counsel decisions."* | no counsel-implying text; counsel-dependent MUSTs → waiver or later |
| 2026-10-01T00:09:20Z (Track 0.5) | approval of minimal alerting to the operator's address | alert channel, 2 uptime checks, 4 policies live |
| 2026-09-30T16:16Z (GATE-M) and 16:27Z | *"… keep me in the loop"* · *"I want you to just interactively collect and log my answers to the questionairre interactively in Claude one by one"* | OM-17 digests (traced **GM-1**, §9.5); S5 was collected interactively in 23 rounds (§4.7; COV-17) |

### 1.2 What SIG is for (U-001, agent-drafted, **confirmed by the operator 2026-09-30T17:29:54Z**)

SIG is a public, evidence-first reconciliation layer over the surveillance-transparency ecosystem: it joins independent
public sources into one graph of what capabilities exist where, who controls and can access them, what rules and
contracts govern them, how that changed, and which evidence supports or contradicts each claim. It is built first for
**a local advocate who needs a printable, sourced dossier before a council meeting** (SIG-UI-002), with
**investigative journalists and other organizers** as co-primary audiences (U-002). Landing text: D3 §1 (agent-drafted);
the tagline ratified at C-4 is *"Public surveillance, traced to the documents."*, and the rest of K14 §2.1's copy is
confirmed verbatim in copy batch #1 (B-2).

### 1.3 Authority chain and gates

`META_PLAN.md` (GATE-M signed 2026-09-30T16:16Z) → Stage-P rows (A–L, all done) → S1a/S1b/S1c/S2 → S3 draft → S4 (three
fresh-context adversarial reviews: coverage, feasibility, truth and safety; closed in `reviews/REVIEW_CLOSURE.md`) →
**S5 / GATE-P, passed 2026-10-01T05:03:05Z** (`feedback/RATIFICATION_LOG.md`, commit `de0b3591`) → **S6** (this
revision; canonical) → **S6r** (one fresh-context consistency review of this plan against the log; findings closed before
Stage B) → Stage B rows T0–T6 (Appendix A) → **GATE-B** (validators + 5/5 CI on the seed PR, orient dry-run in Devin
Desktop resolves row 201, operator approval) → the Devin Desktop `orchestrate-build` session resumes.

**How GATE-P was recorded (TS-01).** The operator asked (2026-10-01T03:34:09Z) to be asked interactively, with the issue,
the recommendation and the other options for each decision. The answers came in 23 rounds; each round's answers are
logged verbatim with the round's `date -u`, and every agent interpretation is labelled as such. Own-words lines (A-5's
option text, A-6's waiver sentence, A-7's GL-GATE-07 text, the seven A-23 waivers, B-9's standing go, C-3, C-12) were
answered by selecting an agent-drafted text; the log labels each one *"agent-drafted, adopted by the operator"* with its
time, and never as the operator's own composition. Two parts of the S4c recording rule were not met during the sitting
and are closed by S6 from the record: (2) the sha256 of the plan and packet revisions shown — both were unchanged from
`e5936f96` to `de0b3591` (plan `3e7e8970…cfeb8`, packet `ebeaca7c…69f1`, computed from git at S6); and the sha256 of each
adopted sentence, computed at S6 from the log's text (`design/S6-ratification-applied.md` §5). The operator's standing
instruction of 2026-09-30 (*"Then after that you can synthesize and proceed as you see fit"*) is recorded as the GATE-P
go: the agent synthesizes and proceeds to Stage B without a further plan sign-off; Stage B's own human items (HG lines,
operator-only actions, GATE-B) still pause.

This plan does **not** advance `docs/build/LEDGER.md`, sign or pre-answer any gate, amend the spec, write an ADR, or open
a PR. Stage B does those things, from this plan.

---

## 2. Baseline (what is live, what is broken)

### 2.1 What is live (A1 freeze 2026-09-30T16:31:55Z, `baseline/BASELINE.md`; live-read)

- **Public release** `sig-2026-09-27-ce480ab1` (132 artifacts, 1.05 GB, 12 compartments) behind the global LB at
  surveillancegraph.org. Content pages ship 0 `<script>`; three islands (`/map/`, `/network/`, `/search/`).
  No release id or commit in served HTML (F-11). `resolver_version = 0.0.0`; not belief-pinned (G3 NEW-1…3).
- **Runtime:** Cloud Run `sig-web`, `sig-api` (min 1), `sig-alerts` (on `:latest`, F-12); 88 Cloud Run jobs (all
  digest-pinned); 79 Cloud Scheduler jobs, 32 firing for the first time 10-01…10-21 (S2/I8; S3 said 33 — FEA-13), the OSM monthly replay at
  **2026-10-10T03:35Z** (D-P31.4-1).
- **Spine:** Cloud SQL `sig-pg` `db-custom-1-3840`, 15 GB SSD (≈ 6.4 GB used), autoresize unlimited, deletion
  protection **off**; ≈ 2.42 M claims (headline 2,423,200).
- **Repository:** `origin/main` = `b7c9e2e3` (tree = P31.4). 49 open PRs #141–#190 (minus #148), stacked; **16 red**
  (13 on `composed`+`web` from a lockfile drift; #165/#179/#185 on `python` from tests that pin living records); #190 is
  5/5 green on `b051732c`. The repository is **public** (`gh repo view`, S1c §0).
- **Build memory:** LEDGER 679 KB (CURRENT STATE 123 KB of PRIOR chains; `nextTicket: HUMAN-H4`); 97 deferrals / 36 owed
  (32 OPEN + 4 PARTIAL); 715 coverage rows / 69 not-MET; 58 BL rows / 32 open; 144 ADR files (ADR-001…145, 064 skipped).

### 2.2 Changes since the freeze (Track 0, `baseline/TRACK0_RECORD.md`)

| item | state | open remainder |
|---|---|---|
| 0.1 backups + PITR | automated backups (05:00Z, 7 retained) and PITR **on**; on-demand backup taken | deletion protection, retain-on-delete, maintenance window, **restore drill at scale** (P34.3, P34.6) |
| 0.2 `/curate/` | removed; 404 on both origins | the durable publish-path fix (P34.10) |
| 0.3 MapRoulette key | stays unrotated (**operator-accepted risk**) | carried by G1; rotation before any contribution-back use (LATER-03) |
| 0.5 minimal alerting | e-mail channel, 2 uptime checks, 4 alert policies (job failures excl. `sig-probe`, disk > 85 %, two uptime) | TLS expiry, `SIG-ALERT` log alert, `sig-probe` re-roll, alerts as code (P34.4, P35.2); budget alert (P34.5) |

### 2.3 What is broken

**S0 — active harm now (9 finding ids = 6 product issues RI-01…RI-06 + 2 production items now mitigated)**
(`findings/REGISTER.md`; `review/REVIEW_SYNTHESIS.md` §2):

| finding(s) | problem | owner row |
|---|---|---|
| F-01 | backups were off; restore never drilled at scale (mitigated by Track 0.1; no drill before Round 11 — A-1) | P34.6 (+ P34.3), early 11A |
| F-02 | `/curate/` was public via a hand rsync (mitigated by Track 0.2) | P34.10 |
| F-03 (RI-04) | every page promises a one-click dispute channel that does not exist | P34.17 |
| F-096 (RI-05) | `/visual-language/` asserts fixture facts about real named agencies and a vendor | P34.17 republish #1 (A-0.3 = wait; unresolved, operator-deferred until then) |
| F-097, F-131 (RI-01) | personal ArcGIS account handles (and 41 e-mail-shaped owner strings) in public source/target/subject ids, one live `camera_operator` value, the repo tip and the listable `sig-public` 09-27 tree | P34.18 (repo tip, ids) → P34.21b (bucket tree first leg, republish #2); A-0 = wait, so unresolved and operator-deferred until then (scope widened, §5.1) |
| F-130 (RI-02) | API dossier endpoint returns the same 25 unrelated subjects for every scope | P34.25 → P34.46 |
| F-183 (RI-06) | `/editorial-standards/` shows a fixture two-reviewer "Releasable" review | P34.17 |
| F-387 (RI-03) | downloads and API credit third-party CC-BY data to "DeFlock community map" | P34.21 |

**S1 — 104 findings that break a core task or the truth of the record**, grouped:
- *Public claims outrun the record:* "human-verified" holdout (F-06/F-108/F-133); site-wide totals on every dossier
  (F-05/F-109/F-132); unpinned "permalinks" (F-07/F-099/F-390/F-399); research dossiers built on undisclosed stand-ins
  (F-152/F-16); governance doc asserts an editorial board (F-189); "counsel" records with no counsel (F-185, U-013).
- *The graph is not what it looks like* (L1/L2): **5,278 camera ids each hold several distinct cameras**; 13.5 % of
  points have another source's point within 25 m vs 3.75 % merged; **74 % name the publisher as operator**; **77.4 % of
  `traffic_camera` subjects are ALPR, police CCTV or enforcement**; 98.8 % of edges undated; 562 axis swaps; 2,370 points
  > 25 km outside their dossier; 91.5 % of "unresolved" lies inside a US state; **0 of 2.78 M claim–evidence links reach
  captured bytes**; every multi-claim resolution "uncontested" (F-504…F-531).
- *Build memory is not a safe resume point:* 595 records / 2,283 dated occurrences carry dates that did not happen
  (F-21, B1); 53 append-only GATE DECISIONS rows deleted (F-22); validators pass on all of it (F-27); readouts written
  after one-line approvals (F-29); gates used as a throughput device (F-36). This planning round repeated the date drift:
  24 late stamps in 17 commits (F-074; TS-14).
- *Verification stopped at the repository boundary:* CI never read at a ticket boundary (F-20); 16 red PRs.
- *Operations run blind:* every workload holds `roles/editor` (F-272); `sig-probe` failing since 09-27 (F-273); buckets
  unversioned (F-275).
- *Coverage:* Flock only via one mirror; Axon/Fusus/RTCC nothing; 22 states without a dossier; the national OSM ALPR
  layer only as a stale copy (I1, I3, I8; D2-10).
- *Usability:* C2's agent walkthroughs succeeded at 5 of 31 tasks (journalist 0/3, organizer 0/6); the map shows dots
  with no basemap and drops 99.97 % of sites at z3 (F-104/F-414); `/network/` shows 131 UUIDs (F-106/F-420).

**Round-10 machinery is not live** (F-14, F-15): no `/releases/`, release search, research dossiers or intake; the
GATE-G3-signed candidate `p-17b713…` holds 0 records and carries a future date (F-051, F-161).

---

## 3. Principles and invariants

### 3.1 Product invariants (unchanged; D3 §6, `AGENTS.md`)

Evidence-first claims with provenance; the claim spine is insert-only (corrections are new claims); the fail-closed
ingestion gate and HG-03 flips stay the operator's; Part VIII (no plate or person data, the officer-naming gate,
aggregates only for audit data, no evasion help); contradictions stay visible; absences are typed; SIG is not a census;
the printed and cited record stays complete, script-free and citable; peers are linked, not rebuilt; the ODbL
compartment stays separate. Every new surface must fit these.

### 3.2 Planning principles carried into the build

P1–P16 bound Stage P (META_PLAN §3). In Round 11 they become operating clauses in the LEDGER's OPERATING MODE (T5),
written from B5 §6.1 (OM-01…OM-18) and S2 §3.5 (OM-19, OM-20):

| META_PLAN principle | Round-11 operating clause(s) | mechanical backstop |
|---|---|---|
| P1 evidence discipline | OM-06 layered status; OM-17 reporting | G7 verdict cross-checks; DRAFT-MEM-7 (live claims cite probes) |
| P2 clock discipline | OM-04 clock | G1 `record-dates` (seed guard core) |
| P3 production read-only | OM-14 production only through a ticket; **OM-20** bounded pre-authorisation | contract mutation list; probe-run records |
| P4 no fabricated human work | OM-08 no proxy signatures; OM-11 human work scheduled | G4 readout authorship; SIG-CONF-D01/D02/D10 drafts |
| P5 status layers | OM-06 | MET-ENGINEERED / WAIVED grammar (G7) |
| P6 independence | OM-03 planning only from a reviewed plan | CAP.1 is an independent gap analysis |
| P7 append-only | OM-13 append-only enforced by CI | G2 `append-only` |
| P8 unanchored input | OM-09 tentative ≠ decision; OM-07 verbatim record | G4 hedge/delegation lint |
| P9 exactly one disposition | OM-11; T4 mapping | `check_dispositions.py`, `check_backlog`, coverage checker |
| P10 control ledger untouched | OM-02 close discipline | G5 `ledger-contract` |
| P11 CI truth | OM-05 CI gate at every boundary | G3 `ci-boundary` (head-bound check-runs) |
| P12 sized for one context | OM-16 size and tail | T3 sizing review; re-split rule (§8.5) |
| P13 never read the whole LEDGER | OM-17; slim head ≤ 12 KiB | G5 orient budget |
| P14 no secrets | OM-17 (`exposed: yes` stops the chain) | `make scan-secrets` in CI |
| P15 reproducible conservative source research | OM-14 for every hosted ingest; ING-GO per wave | I8 first-run safety; Part VIII preflight |
| P16 operator identity | **alias first** (C-8, ratified): no request needing a contact string (EDGAR, 511/QLD/NSW key sign-ups) is sent until the `contact@` alias exists; the need is stopped and recorded. Commits keep the operator's name as author (A-21), so the harness/model trailer is the only harness record | connector config review; OM-01 trailer check in CI |
| (new) windows | **OM-19** dated live-leg queue | acceptance rows read the queue |
| (new) autonomy | **OM-20** (ratified; 11A list approved at GATE-P) + OM-10 + OM-18; A-15 pause rules | GATE packets list exact row ids |

### 3.3 The operating clauses (summaries; full paste block B5 §6.1 and S2 §3.5)

OM-01 one harness + model per round — **Devin Desktop, `swe-2-high`** (A-15) — recorded in a `harness:` key, CURRENT STATE and every run ledger; switches only at a boundary; **every agent commit carries a trailer naming the harness and model, and a G-check fails a Round-11 PR with an untrailered agent commit** (B5 OM-01 verbatim; TS-11; required because commits keep the operator's name as author, A-21) ·
OM-02 the worker closes its own ticket in one commit after the PR exists; two orchestrator repairs in a round → `blockedOn` ·
OM-03 rows enter only from a reviewed plan (`decompose-spec mode=extend`) · OM-04 every date from `date -u` or git/GitHub
time; never a "chain date" · OM-05 read the PR's head-bound checks after push; red/missing → `blockedOn` · OM-06 every
status names its layer (engineered · fixture-verified · staging-verified · live-executed · public · human-completed) ·
OM-07 gate records quote the operator verbatim; agent text confirmed against its sha256 prefix · OM-08 no proxy
signatures; a past "counsel" determination is recorded as **the operator's own determination (no counsel)** (U-013; TS-09) · OM-09 hedged words get a yes/no question · OM-10 no
unbounded pre-answers · OM-11 human work is scheduled with an owner or deferred with a trigger, never silently ·
OM-12 `blockedOn` is used · OM-13 protected regions only gain lines · OM-14 no production mutation outside a ticket that
names it · OM-15 tests assert invariants, never living records · OM-16 size budget (default 3,000 changed lines) and a
tail that reads live state · OM-17 boundary lines + an operator digest with merges read from GitHub · OM-18 stop and ask;
**silence is never consent**.

**OM-19 (new; S4c wording) — windows and the live-leg queue.** A contract whose live stage has a window or a named go
carries a `Live window:` header and names its live-leg re-run prompt. Outside the window or without the go, the ticket
lands engineering and staging; the live leg goes into RETURN PASS with its window, go id and re-run line; the chain
continues. At every boundary the orchestrator compares `date -u` and live scheduler state with the queue and re-runs due
legs before dispatching. A row that needs a queued leg's **live result** (`live:` edge) waits. **A GATE is not presented
while a leg is *due*** — its earliest time has passed, its go is held, and it has not run. A leg whose window extends past
the GATE is listed in the packet and carried (FEA-03). **Execution mechanics (FEA-05):** a leg runs on its own branch
`r11/<id>-live-<n>`, created from the current chain tip, with one PR (base = the tip branch) and a head-bound CI read; the
next ticket stacks on it. Legs whose go is already held run even while the chain waits at a GATE, a `blockedOn` or a
usage-limit stop. **Backstop:** a scheduled headless leg-runner (OP-24; prompt written by SEED-17) fires at each window's
opening and close and every 6 h inside a window; it takes the chain lock, runs only legs whose go is held, and alerts the
operator (through the P34.4 channel) when a due leg cannot run.

**OM-20 (S4c wording; ratified at GATE-P, S5-1) — bounded pre-authorisation.** At GATE-B and each sub-round GATE the
operator *may* pre-authorise named production mutations of the next sub-round: exact row ids, each contract's mutation,
restore point, expiry at the next GATE. **Nothing is pre-authorised on silence.** **The 11A list was approved at GATE-P
(S5-3, 2026-10-01T04:28:49Z) verbatim plus P34.45's ER re-run, expiring at GATE-G4:** P34.3, P34.4, P34.5, P34.6 (drill
clone), P34.21a (attribution backfill), P34.24b (clone rehearsal), P34.40 (dark LB/nginx), P34.42a/b (IAM), P34.43
(execution host + logins), P34.44b (nightly quality job), P34.49 (Part VIII sealing), P34.45 (ER re-run; A-20 = a). **Never
pre-authorised:** HG-11/Class S promotions and republishes; **any roll that changes a public route's response** (API rolls
P35.57, P36.38, P37.20, P37.42); ING-GO; HG-03 flips (each executed by the operator, OP-26); **any hosted sqitch change that alters an existing table or takes an
ACCESS EXCLUSIVE lock** (P34.46, P35.14b; new-table-only changes such as P35.32 may be listed); the bounded apply
(P35.61); **any capture run or archive write touching a Part VIII-screened family** (P37.16a/b, P37.36); irreversible
external deposits (P37.55); the Wave-C tier bump; any spend above $300/mo; **any WV-06 true deletion** (P37.71). A red probe, a failed restore point or a
production read that contradicts a record voids it for the affected rows. A row not on an approved list pauses in-ticket
(§8.1: 57 OM-20 rows, 13 of them pre-authorised for 11A). **Class R standing go (B-9):** expires at the next sub-round GATE or after 30 days, whichever is
first, and is void on any ratchet regression, any Part VIII screen change or any new source (TS-13); it is renewed at each
sub-round GATE and never by `continue`. **A-20 = a:** a structural spine write may change a live-spine API answer before
HG-11, disclosed by the basis label on every response and a `/status/` notice; it still needs its OM-20 listing or an
in-ticket go.

### 3.4 Constraints the operator fixed (not re-asked)

≤ $300/mo **infrastructure** without an explicit go on a shown trade-off (U-008; A-2: agent usage is reported, not
capped, with a pause at any usage-limit event) · no humans besides the operator (U-008) · no contact outside the
project: no outreach, recruiting, records-request sending or contribution-back posting (U-011) · do not block on
counsel; no text may imply counsel exists (U-013; the counsel clauses are waived, WV-07) · agents never merge,
retarget, tag or push `main` (§7.1) · alerts route to the operator's address · the public dispute and intake contact
is the operator's address until the `contact@` alias exists (Q-29, WV-05; revisited at GATE-ANNOUNCE, TS-21) · no
response time is promised (B-8) · publication is never pre-authorised; a live-API answer may change before HG-11 only
with its basis label and the `/status/` notice (A-20) · Devin Desktop executes the round; Claude Code reviews it
afterwards (A-15).

---

## 4. Decisions ratified at GATE-P

Every line below was answered by the operator on 2026-10-01 (times are the log's round stamps, `date -u`). "Answer"
quotes the selected option or summarises a custom answer; the full text, the options offered and the labelled
interpretations are in `feedback/RATIFICATION_LOG.md`, and each of the 346 member decisions now carries its
`operator_answer` and `answered_at` in `data/decision_catalog.csv`. **Bold** answers differ from the recommendation.

### 4.1 Ratified before S5 (recorded verbatim in META_PLAN §7.1; unchanged)

| decision | answer on record | consequence in this plan |
|---|---|---|
| Q-1 meta-plan; Q-3 worktree; Q-4 Stage-P driver; Q-5 Chrome; Q-6 D1 mode | approved / as recommended | planning ran as recorded |
| Q-2 Track 0.1/0.2; PITR; Track 0.3 | backups + `/curate/` removal approved; PITR delegated and done; MapRoulette key stays stale | §2.2 |
| Q-11 / Track 0.4 | agents do not merge; Round 11 builds on the chain; the operator merges later | §12 |
| Production fixes (received before 17:10:49Z, git `e5725b7b`) | S0 hotfixes, QA-1…QA-10 and `/task/new/` pages approved in principle, specified as Round-11 tickets | 11A rows P34.3–P34.21 |
| Track 0.5 | minimal alerting created | §2.2; P34.4 verifies and codifies |
| Alert routing; Q-29 | the operator's address | P34.4; P34.17 dispute notice |
| U-001; U-002 | confirmed; advocate first + journalists + organizers | D3 §2 journeys |
| U-003 | Stream K; basemap wanted (reverses Round-9 Q8); zero-JS re-decided (A-12) | §5.7; ADRs in §7 |
| Q-8 | no humans besides the operator | §11; rows 184–187 superseded |
| Q-10 / Q-23 (ceiling) | ≤ $300/mo; up to ≈ $1,000 only with an explicit go on a shown trade-off | §10.4 |
| Q-26 | "counsel" = the operator; no counsel; do not block on counsel | §5.10 |
| Q-28 | no recruiting or outreach | LATER-02/03/04 |
| Q-30 | the operator's name + address as the contact string; plan a `contact@` alias (now: alias first, C-8) | OP-10 |
| Autonomy; launch; coverage priority | maximal autonomy with spend transparency and no outside contact; announce "when the time is right"; US-nationwide Flock/Axon/other vendors | OM-20; GATE-ANNOUNCE; I8 order |
| Q-18 landscape scan | moot (C5 ran) | — |

The labelled agent interpretations under U-002…U-015 were confirmed at GATE-P (C-11, 04:59:05Z).

### 4.2 Part A (24 lines)

| line | operator's answer (time) | consequence in this plan |
|---|---|---|
| A-0.1 / A-0.2 / A-0.3 | **"No, wait for P34.18" · "No, wait for P34.21" · "No, wait for republish"** (03:41:19Z) | no Track-0 change; the exposures are **unresolved, operator-deferred**; owners land early in 11A: P34.18 (repo-tip strings), P34.21b first leg (anonymous read/list on the 09-27 tree), P34.17 (`/visual-language/` + handle-bearing pages) |
| A-0.4 | "Accept and disclose" | history retained (agents never rewrite it), disclosed in P34.18's correction note; P37.55's deposits of history follow the history scan |
| A-1 | **"None now; ticket it"** (03:53:59Z) | QA-9 drill (P34.6) and TLS-expiry alert (P34.4) are early-11A tickets; the first-fire wave runs on backups/PITR + Track 0.5 alerting; risk unresolved, operator-deferred |
| A-2 | **"Infra only; alert later"** · "Report + pause on limit" | the $300 ceiling covers infrastructure only; budget alert + billing export in P34.5 (early 11A); agent usage reported per wave; the orchestrator pauses and asks at any usage-limit event (no $ cap) |
| A-3 | "Yes, all three" | P34.50 runbook → the operator switches nameservers (OP-09) → R2 $0-egress origin with a $50/mo egress ceiling + kill switch (P35.5) → `contact@` alias (OP-10) |
| A-4 | "Adopt disclosed posture" (04:03:25Z) | posture ADRs 163–167, 170; the MUSTs it weakens were waived at A-23 |
| A-5 | **"Re-confirm GL-GATE-08 as is"** (option text adopted by selection) | robots disallows stay disregarded on the 122 hosts incl. PrimeGov and on new hosts, disclosed as host + count (B-19); SIG-INGEST-046c reservation refusal and the rule-7 opt-out register are still built (P36.1a/b); P35.1b pauses no host |
| A-6 | "Adopt waiver sentence" | ADR-153: C0–C2 auto-collapse; SIG-EVAL-004's lower bound waived for C0–C2 only; rows 184–187 superseded; no "human-verified", "certified" or camera-match-precision claim |
| A-7 | **"Re-confirm GL-GATE-07"** (adopted text: *"US public records and open-licence sources flip batch-wide under precedent, erring on the side of approving."*); X3 "Confirm" (04:07:45Z) | Tier-1 batches RB-01…07, RB-09/RG1–5 and E4-B1 flip batch-wide (option a); Part VIII S-lines still apply; the 46 widening configurations are enabled under their parent's basis |
| A-8 | **"Keep all, accept risk"**; wording **"Keep everything as is"** (04:09:43Z): *"I accept the express-terms risk for all ≈8,088 currently public rows, including the non-commercial ones; A-9 applies to new sources only."* | no withdrawal and no TxDOT restriction; P34.19 re-scoped to a disclosure (captured terms + the operator-accepted basis on pages and files); ADR-183 |
| A-9 | "May be commercial" | new non-commercial sources are facts + pointers only; E4-R4d declined; the 3 live NC rows stay (A-8) |
| A-10 | **"Auto-allow + absence only"** | ADR-159: organisations matched to the Census of Governments, a SAM UEI or a Wikidata QID are publishable (person-name screen always runs); the rest show a typed "not yet reviewed"; **no operator top-50 review** (OP-14 dropped) |
| A-11 | "Overviews + egos" (04:09:43Z) | ADR-158; incl. the state × state Flock-sharing overview (A-22) |
| A-12 | "HTML-first page types" | ADR-155 (supersedes the named-island rule of ADR-091/097, extends ADR-134; ADR-068's `/curate/` unchanged — K0 §6) |
| A-13 | "Full seed" | the seed as planned; no P34.0a fallback |
| A-14 | "All, staged" (04:16:29Z) | Tier A (SK-13/14/17/18/19/20/22) at T0, Tier B-must (SK-01/02/03/06/09/10) before the first dispatch, the rest early in the round |
| A-15 | **custom: Devin Desktop, `swe-2-high` (256k), "Devin for everything"; Claude Code deep review "after the entire thing"**; pauses "Gate pauses + wave digest" (04:16:29Z, 04:21:56Z) | §0 executor bullet; §8.5 sizing (≤ ~150k tokens loaded); OM-01 trailers; REVIEW-R11 closing unit; no in-round second harness |
| A-16 | "Key + forward rule" | OP-25 operator-only key; P34.28 verifies gate signatures in CI; LATER-15 closes |
| A-17 | **"Ratify; fetch vendor pages"** (D3-Q3 b; D3-Q1 yes, D3-Q5 a, Q-E2-22 a) | ADR-172 + ADR-184 envelope; P36.74 Flock portals; P36.76 Axon Connect (with B-35); CHART-025 amended |
| A-18 | "Yes, flip both" (04:21:56Z) | P35.17 captures the terms; the operator flips `census_gazetteer_tiger` + `natural_earth_10m` (OP-26); P35.17 stays on the critical path |
| A-19 | "Let waves slip" (04:25:48Z) | the cliff table (§8.8) stands; nothing is dropped |
| A-20 | **"Yes, with labels"** | structural spine writes may change live-API answers before HG-11, disclosed by a basis label on every response (P34.25) and a `/status/` notice; P34.45 returns to 11A; P35.57 is an improvement, not a gate |
| A-21 | **"Keep my name"** | the operator stays the commit author; harness/model trailers are enforced in CI (OM-01) |
| A-22 | "Keep + use share lists" (recommendation updated mid-session) | P36.75 turns the 474,184 share-list edges into organisation-level claims after the Part VIII screen |
| A-23 | WV-01, WV-02, WV-03, WV-04, WV-05 and **WV-06** all waived (04:28:49Z) | seven waiver ADRs (§6.5, §7); GATE-ANNOUNCE's "unmet at launch" list shrinks; WV-06 → P37.71 deletion path |

### 4.3 S5 lines (S5-1…S5-4)

| line | operator's answer (time) | consequence |
|---|---|---|
| S5-1 | "Both + list + P34.45" (04:28:49Z; answers S5-1 and S5-3) | OM-19 and OM-20 ratified in their S4c wording (§3.3) |
| S5-2 | "Ratify" (04:54:19Z) | the check-in packet; `continue` answers only batch lines |
| S5-3 | **the 11A list approved verbatim plus P34.45's ER re-run**; expiry at GATE-G4 | 13 pre-authorised 11A rows: P34.3, P34.4, P34.5, P34.6 (drill clone), P34.21a, P34.24b, P34.40, P34.42a/b, P34.43, P34.44b, P34.49, P34.45 (ER re-run); P34.18, P34.24a and P34.44a stay in-ticket gos |
| S5-4 | **"Keep non-US acquisition"** | CF-06 not confirmed: ACQ-23a/b return as P37.69a/b; Wave C keeps its non-US objects; AU keyed APIs (P37.70, B-18); US-first ordering kept for priority (Flock/Axon US-nationwide first, U-007) |

### 4.4 Part B (42 lines)

| line | operator's answer (time) | consequence |
|---|---|---|
| B-1 | "Approve all" (04:32:16Z) | Wave-0 honesty fixes + the fixture/status-word publish guard; the two extra S0s in Wave 0 |
| B-2 | "Batches + notice allowance" | copy in batches of ~25 confirmed verbatim; N-1…N-7 ship by sha256 until GATE-G4 |
| B-3 | "Re-key, map restricted" | P34.18; neutral "identifier changed" page; old→new map restricted |
| B-4 | "As stated" | `p-17b713` and GATE-G3 superseded; ACCEPT-R8/R10 and GATE-G3 annotated with B7's facts; no past-state addendum |
| B-5, B-17, B-22, B-23, B-26 | "Accept all five" (04:33:54Z) | verdict vocabulary; `nextTicket` = N1, HG-05 operator-owned; the 52 K-row recommendations; Natural Earth names; dedup is an announce criterion ("records" until then) |
| B-6 | **"Move UA, don't buy domain"** | UA/contact → surveillancegraph.org (P35.38); `sig-project.org` not bought — every remaining reference removed, residual squatting risk recorded (R-29); SWH deposit after the history scan; outreach owed later |
| B-7 | "As stated" | archive + pinned citations + release search first; no API hotfix unless step 1 slips past ~10-21 |
| B-8 | **"Email, no time promises"** (04:35:53Z) | e-mail-only intake until after the announcement; `/intake/` "not operating"; **no response time is published**; task pages name the same address |
| B-9 | "Adopt + standing go" (standing-go text adopted by selection) | G3 model; Class R standing go, renewed at each sub-round GATE (never by `continue`) |
| B-10 | "Yes" | releases from unmerged stack commits; the operator tags v0.1.0 after the #190 sitting; legacy buckets retired per G3 |
| B-11 | "As stated" | 40 GB cap, pre-grow 25 GB, temporary tier bump; OSM monthly; one ING-GO per wave; targets under flipped sources = configuration; **Wave D in scope** |
| B-12/13/14 | "Accept all three" (04:39:45Z) | $0 paid data; scheduler consolidation (−$7/mo, P35.1b), LB and min-instances 1 kept, CUD after 3 bills; evidence retention ≥ 365 days, unlocked |
| B-15 | "As stated" (04:33:54Z) | operator GitHub settings S-1…S-5; pre-#190 reds don't block; `r11/` prefix; one flake re-run per head |
| B-16 | "Local + backup; push at T6" (04:39:45Z) | branch local until T6 + scans; OD-27 = a (publish as recorded); the agent makes a git bundle the operator stores privately (OP-23) |
| B-18 | "US + AU keys, fold rest" (recommendation updated after S5-4) | the operator registers US 511 + QLDTraffic/NSW keys after the alias (OP-13); D-P32.3-1 folds into A-10 + P37.46; **D-P30.2b-1 has no fold target after B-31: OPEN, non-blocking (T-EVAL-IND)** |
| B-19 | "Yes, as stated" | raw-ok bytes after the Part VIII screen; scrubbed run logs; snapshots; JSON-LD files; prior releases as manifests; 6-h status lane; review packets |
| B-20 | "Pipeline key + your gate key" (04:41:11Z) | pipeline minisign key (OP-20) signs manifests; the operator's key (OP-25) signs gate records |
| B-21 | "Yes, as stated" | operator-run Zenodo DOIs (OP-19), open compartments only, after the attribution fix |
| B-27 | "Yes" | neutral "Other public resources" block (P36.55); official agenda portal links |
| B-28 | **"Separate agent, labelled"** | P36.79: a separate agent context writes the held-out set, labelled *"agent-authored held-out set; not independent"*, sealed from the tuning contexts; OP-21 dropped |
| B-29 | "Both" (04:43:37Z) | operator gallery sign-off before announcing; the spec published per release |
| B-30 | "Yes" | `sig-api` 1 GiB (+$3/mo); search 30/min; no Cloud Armor now |
| B-31 | **"No maintainer check"** | no OPCHECK; every Class-S readout and `/quality/` say "no human check performed"; public `/quality/` incl. failing checks; C2 enabled; no in-round second model family; P35.49, OP-16, OP-17 dropped |
| B-32 | **"Include S8 screened lane"** | S1–S9 ingested through screened lanes, **including the two S8 tribal members** (no tribal-data-governance rule; R-26) |
| B-33 | "SA compartment; territories = US" (04:46:04Z; rec. updated after A-7) | RB-06b → share-alike compartment; RB-08 territories flip as US |
| B-34 | "Flip under precedent" (rec. updated after S5-4) | N1–N21 flip on the non-US database-right basis (express prohibitions excluded) → P37.69a/b |
| B-35 | **"IT7 full fetch"** | IT1 b, IT2/3/5/6 b, IT4 c; **IT7: Axon Fusus Connect pages fetched in full, every byte screened, private registrants never stored or published** (P36.76) |
| B-36 + B-37 | "Capture IU; TR facts+cite" (rec. updated after B-32) | IU1–IU5 terms captured (P36.2), then a line; TR1–TR2 facts + citations under the S8 screen |
| B-38 | "As stated" (04:49:27Z) | EDGAR facts-only basis; ingestion later (LATER-09); first request only after the alias |
| B-39 | **"Also fetch DocCloud/Sourcewell"** | DocumentCloud/MuckRock (P36.77) and Sourcewell/OMNIA (P36.78) fetched under ADR-184's envelope; C4 per A-17; C5 b; C7 a; C8 b (CourtListener bulk deferred); C9 a; C11 a |
| B-40 + B-43 | "Confirm all" | X1, X2 confirmed, X4 approved; E4 S1–S5 and F1 D-P21.3-2 status corrections (SEED-14) |
| B-41 | **"As listed, R3 flip"**; R2a re-asked → **"Fetch, screened"** (04:51:39Z) | R1 close; **R2a flip `documentcloud`**; R2b decline; **R3 flip `dot_511_tx`**; R4a OGL-Edmonton after capture; R4b flip; R4c QLDTraffic API (P37.70); R4d decline; R5 flip; R6a capture terms; R6b close (P36.2) |
| B-42 | **"Agent clears, disclosed"** (04:51:39Z) | the agent clears each Round-10 dossier family after the Part VIII screen; readouts say "cleared by agent screen, no human review"; SRC-027 metadata-only; one bounded retry |
| B-44 | D-K7-6, D-K8-1, D-K8-4, D-K1-6, D-K4-3 as recommended; **D-K1-7 "My location" approved** | P37.72 builds a map-pan-only control after a written SIG-GOV-017 analysis; if it cannot comply, the ticket pauses and returns the question |

### 4.5 Part C (13 lines) and D2 (16 reactions)

| line | operator's answer (time) | consequence |
|---|---|---|
| C-1 | "Confirm" (04:54:19Z) | ADR-146/147 record the readout provenance as fact |
| C-2 | "Confirm; planned hand-over" | the "Pause after P31.5" was a planned hand-over to Devin CLI at P31.5→P31.6 |
| C-3 | "Adopt both sentences" (adopted 04:54:19Z): *"The 'counsel' determinations of 2026-09-16 and 09-24 were my own; there was no counsel. My 09-28 message 'let's defer all the human review steps and proceed' was my decision to defer the human review legs."* | recorded with today's date, never as a 09-16/24/28 statement (SEED-08); item (3) robots = A-5 |
| C-4 | **"…traced to the documents"** (04:56:11Z) | tagline *"Public surveillance, traced to the documents."*; the rest of K14 §2.1 copy goes to copy batch #1 |
| C-5 | "Omit until I write it" | no "who runs SIG" section or placeholder ships until the operator writes it |
| C-6 | "Stays public" | commit hashes shown; B-16 scans before the first push |
| C-7 | "Don't know; keep estimate" | ≈ $90–100/mo stays a labelled inference until P34.5's billing export measures it |
| C-8 | "Alias first" (04:59:05Z) | no request needing a contact string (EDGAR, 511/QLD/NSW key sign-ups) before `contact@` exists |
| C-9 | "Confirm" | no `SIG_INTAKE_*_SECRET` value from the notes was used in any deployed/staging config |
| C-10 | "Let me inspect it" → inspected (04:59:41Z) | the stopped local container `sig-p332-db` holds sqitch L44–52 as stamped: **never re-stamp**; date corrections only by appended amendment (B-4) |
| C-11 | "Confirm all" | the U-002…U-015 interpretations stand |
| C-12 | "Accept the list" (05:03:05Z): *"I accept that these features are withdrawn or labelled this round rather than made to work."* | one-click dispute, `/intake/`, `/contribution-back/`, `/curate/`, `/task/new/` demos and research-queue "send" are withdrawn or labelled, accepted |
| C-13 | "Superseded" (05:03:05Z) | ACCEPT-R10 stands as history, superseded by the Round-11 re-verdicts (B-5); OP-18 done |
| D2-01…16 | all agreed at the shown priority (05:03:05Z) | P1: 01–05, 07, 08, 11, 12, 13, 16; P2: 06, 09, 10, 14, 15 — matches the plan's ordering |

### 4.6 Where the operator chose differently — what is now in force

The 27 lines where the operator's answer differs from the recommendation (log, closing table) change the plan as
follows. None of S4c's 31 "defaults" applies any more: every line was answered, so P38.2 lists no "not attempted
(default …)" line. What the round carries instead:

- **Descoped or withdrawn by choice (reported as decided, not as defects):** the A-0/A-1 Track-0 actions (now early-11A
  tickets); the operator's top-50 organisation review (A-10); any human check of quality or dossiers (B-31, B-42); an
  operator-written query set (B-28); published response times (B-8); the `sig-project.org` purchase (B-6); the "who runs
  SIG" text until the operator writes it (C-5); the six C-12 withdrawals.
- **Added load (agent work):** the vendor and terms-conflicted connectors P36.74, P36.76, P36.77, P36.78, the share-list
  claims P36.75, non-US acquisition P37.69a/b and P37.70, the deletion path P37.71, "My location" P37.72, the agent-written
  held-out set P36.79, the G4c CI verification in P34.28, and the post-round review — **+10.5 chain runs (net +10.0
  after P35.49 is dropped) + ≈ 8 review contexts**.
- **Added load (operator):** HG-03 flip lists per wave (OP-26), the gate-signing key (OP-25), AU key registrations (OP-13),
  Class R standing-go renewals at each sub-round GATE.
- **Risks accepted by these choices** — express terms kept, vendor and platform terms fetched against, robots disregarded,
  the EU/UK database right on N1–N21, a single maintainer with all seven waivers, no human checks, the executor B7 tied to
  Round-10's record failures, live API answers changing before readouts, "My location" against GOV-017, tribal data
  without a governance rule, the unbought domain, the deferred Track-0 exposures, and two unwaived MUSTs that collide with answers (SIG-GOV-003 with B-8; SIG-INGEST-036 rule 6 with B-39) — are R-18…R-31 in §14, each with mitigation and trigger.
- **Recording gaps found at S6** (§1.3): the GATE-P record lacked the plan/packet sha256 and the sha256 of the adopted
  sentences; S6 computed both from the record and labels them as computed afterwards.

### 4.7 How S5 was collected (historical)

The operator asked (2026-09-30T16:27Z) for answers to be collected interactively, one decision at a time; at
2026-10-01T03:34:09Z they asked for each decision's issue, recommendation and options. S5 ran in one sitting of 23 rounds
(03:41:19Z → 05:03:05Z), plus the operator-approved local C-10 inspection (04:59:41Z). Five recommendations were updated
mid-session after earlier answers changed their premise (B-18, B-33, B-34, B-36/37, A-22) and the operator accepted the
updated ones; one conflict (B-41's R2a vs B-39) was re-asked and resolved in round 18.

---

## 5. Themes (problem → evidence → design → requirements → rows → acceptance)

Runs per theme are chain-row totals from the post-S6 `data/round11_plan.csv` mapped to S1a's `theme` column (285.5 in
all after S6: UX core 62.5 · sources 36.5 · transparency 29.0 · data correctness 24.0 · release/ops 23.5 · safety and
honesty 20.0 · PLAN contract authoring 20.0 · Round-10 activation 19.0 · UX explore 18.0 · memory truth 12.0 ·
acceptance/tail rows 8.0 · governance 5.5 · debt 5.5 · CI 2.0). The row/run counts in the §5.x headings below are S3's
pre-split figures, kept for traceability (§5.5 and §5.10 give S6's); the CSV is authoritative.
"Acceptance" is always written at the layer it must reach (OM-06).

### 5.1 Safety and honesty (21 rows, 18.0 runs; 11A 14.0)

- **Problem.** Production was unprotected and the public site makes claims the record does not support: fixture reviews,
  "human-verified", "one-click dispute", "editorial board", "counsel", wrong attribution, personal handles in ids, and an
  API that answers every scope with the same 25 subjects.
- **Evidence.** S0 F-01, F-02, F-03, F-096, F-097, F-130, F-131, F-183, F-387; S1 F-06, F-098, F-107, F-108, F-133, F-185,
  F-186, F-189, F-192, F-198, F-201, F-273, F-275, F-277, F-285, F-403, F-405; TH-01/TH-02/TH-13 (`review/REVIEW_SYNTHESIS.md`);
  E2 §0.1 H-1…H-9; G1 §0 risks 1–6; U-013.
- **Design.** G2 step 0 + E2 H-fixes + K13 W0. One allow-listed publish path that cannot ship `/curate/` or delete release
  trees (P34.10) comes before any republish. Content rows precede the republish that ships them (CF-12): W0 copy P34.11–15
  and the P34.19 express-terms disclosure (A-8: no withdrawal) → **republish #1** P34.17 (also removes `/visual-language/`
  and the handle-bearing pages, A-0.3) → handle re-key incl. the repo-tip strings P34.18 + evidence empty-state truth
  P34.20 → **attribution re-export + publish-time attribution gate + bucket-tree access removal + republish #2**
  P34.21a/b (the bucket leg first; hosted backfill ≥ 2026-10-13T12:00Z).
  API honesty code P34.25 deploys with P34.46 (≥ 10-14). Operations: P34.3 data protection (incl. bucket versioning — the
  restore point for both republishes, `live:P34.3`), P34.4 alerts that reach a human (+ TLS-expiry alert), P34.5 budget
  alert at $300 + billing export + a spend ledger that includes Cloudflare/registrar lines, P34.6 restore drill at scale,
  P34.49 **Part VIII at-rest audit** (TS-07), P34.50 DNS cut-over runbook (FEA-08). Later safety rows: P35.3
  production-truth probes; P35.28 officer-naming gate (default deny) and P36.15 redaction pipeline and **P35.66 residential
  demotion** — all three now land **before** Wave B's activation P36.12 (TS-07); P35.38 identity base and crawler contact.
- **A-0 answered "wait" (03:41:19Z; TS-04, TS-12).** No Track-0 action ran. The exposures are recorded as **unresolved,
  operator-deferred** (not accepted) and owned by early-11A tickets: A-0.1 → P34.18 removes the 41 e-mail-shaped owner
  strings and handle tokens from the registry's non-id text (on the r11 branch at once; on public `main` only when the
  operator merges, OP-08); A-0.2 → P34.21b's first leg removes anonymous read/list of the `sig-public` 09-27 tree
  (prefixes the live site fetches excluded after a read-only listing; tombstone note), on its own go and allowed inside
  AR-3 outside 03:00–10:00Z; A-0.3 → P34.17's republish #1 removes `/visual-language/` and the handle-bearing pages
  (N-6). A-0.4 = accept and disclose: P34.18's correction note discloses the retained git history.
- **Republish #1 (P34.17) ships only text true of the 09-27 data (TS-03).** It introduces no claim that is not yet true.

  **Table R1 — exactly what republish #1 removes or changes**

  | # | removal or change | finding(s) | new text (all confirmed verbatim or from N-1…N-7) |
  |---|---|---|---|
  | R1.1 | fixture two-reviewer "Releasable" review on `/editorial-standards/` removed | F-183 (S0), F-107, F-198, F-201 | N-1 |
  | R1.2 | every "one-click dispute" / "anonymous" promise removed; dispute page names the operator's address, promises no response time (B-8) and says senders disclose their address (WV-05) | F-03 (S0), F-098 | operator-confirmed dispute notice (copy batch #1) |
  | R1.3 | `/visual-language/` fixture facts removed (A-0.3 = wait for this republish) | F-096 (S0) | none |
  | R1.4 | "human-verified" holdout claims and P/R/F1 1.000 removed | F-06, F-108, F-133, F-192 | the past-tense text below; **no `/quality/` link** (it exists only at P37.45) |
  | R1.5 | "editorial board" and "counsel" wording on site pages removed | F-185, F-189 (site part) | N-1 where a process is described |
  | R1.6 | "reproducible" dropped; "permalink" → "link" until `/s/` pins exist (C6 QW-5, owner P34.11) | F-07, F-099, F-390, F-399 (wording only) | none |
  | R1.7 | site-wide totals shown as dossier figures removed from "How we know this" | F-05, F-109, F-132 | none |
  | R1.8 | (S4c: withdrawn sources removed) — **dropped, A-8 = keep all**: the express-terms sources' pages and list entries show their captured terms and the operator-accepted basis instead (P34.19, ADR-183) | J4 NEW-1, F-403 | disclosure text (copy batch #1) |
  | R1.9 | `demo_*` task pages stripped | §7.1 PF-3 | none |
  | R1.10 | `/status/` notice for what stays wrong until P34.46, and the A-20 notice that live-API answers may change before the next Class S release | F-130 (S0), F-189 (API terms); A-20 | N-7 + the A-20 notice (copy batch #1) |
  | R1.11 | every page whose URL or title embeds a personal handle removed until P34.21b republishes it re-keyed (A-0.3) | F-097, F-131 (S0) | N-6 |

  Holdout text (agent-drafted, from TS-03; ships only if confirmed verbatim): *"Matching quality: development evidence
  only. 540 record pairs … were labelled by an AI model … No person labelled them. The records on this site were matched
  by rules that were partly tuned on those labels; SIG is changing them so that only copies of one upstream record are
  merged."* (Every number is re-checked against L3 before the text is shown.) The present-tense sentence *"SIG … merges only records that are copies of one upstream record …"* ships only
  with **P35.63**, after P34.45's ER re-run and the derivation census make it true (a CSV edge P34.45 → P35.63), with a
  probe-run record ≤ 24 h old (DRAFT-MEM-7). Every republish that changes a status sentence cites such a record.

  **Notice strings N-1…N-7** (agent-drafted; ratified once at S5 through B-2 by their sha256 — prefix shown; only these
  ship without per-text confirmation, and only until GATE-G4; TS-18): N-1 "Not yet performed." `7775ea0502c9` · N-2
  "Not operating yet." `05f182b52808` · N-3 "Withdrawn from publication pending a rights review." `c85a9ae463fe` · N-4
  "Attribution for this source is being corrected; see the source's own terms." `6ee2dd66e288` · N-5 "This identifier
  has changed." `4f628b89a266` · N-6 "This page has been removed while a correction is made." `6acec2f14d71` · N-7 "The
  API's dossier and terms responses are known to be wrong and are being corrected." `34ae2bba9a73`.

  **Table R2 — S0/S1 claims still live after republish #1, and their interim treatment (TS-12)**

  | claim | stays until | interim |
  |---|---|---|
  | misattribution to "DeFlock community map"; 61,603 rows with required attribution empty; map credits "SIG contributors" (F-387 S0, F-111, F-138, F-186, F-405, F-531) | republish #2 (P34.21b, ≥ 10-13T12:00Z backfill) | P34.21b's first leg removes anonymous access to the misattributed downloads; republish #1 replaces wrong per-source credits with N-4 |
  | personal handles in ids, tiles and one `camera_operator` value (F-097/F-131 S0) | P34.18 → P34.21b (`camera_operator` fully in P35.26) | handle-bearing pages removed in republish #1 (R1.11); otherwise unresolved, operator-deferred (A-0) |
  | API dossier endpoint returns 25 unrelated subjects; `/terms` names a board and counsel (F-130 S0, F-189) | P34.46 (≥ 10-14) | N-7 on `/status/`; no API hotfix (B-7) unless step 1 slips past ~10-21 |
  | the ≈8,088 express-terms rows in downloads and tiles | stay (A-8) | captured terms + the operator-accepted basis disclosed on pages (P34.17) and in every file's ATTRIBUTION (P34.21b) |
  | unpinned permalinks (F-07/F-099/F-390/F-399) | real pinning P36.66b (11C), under D-J3-6 | wording fixed in republish #1 (R1.6) |
- **Requirements.** SIG-OPS-001…004 (restore drill, survivability, route allow-list, single publish path), SIG-OPS-006
  (alert delivery), SIG-OPS-009 (cost truth), DRAFT-OPS-2 (fixture sentinels), the G2 §6 claim rules; SIG-PUB-002/004/005/013
  (at-rest audit, residential demotion); SIG-PUB-008's second-reviewer role and SIG-UI-042's release block are WAIVED by ADR (WV-03, WV-04).
  See §6.
- **Acceptance (11A exit, live layer, P34.47).** Every S0 has a live removal or fix: restore drilled with timing and
  deletion protection on; publish path refuses `/curate/` and an absence probe confirms; honest dispute notice; fixture
  pages removed; API honest (P34.46); attribution correct in downloads, API and map behind a publish-time gate. **RI-01
  closes only when** a crawl of the site, the API, the tiles, the `sig-public` listing and the repo tip finds 0 entries
  of the handle list (kept gitignored at `docs/build/logs/next-phase/C3/personal_like_ids.txt`) in source ids, target
  ids, subject/claim/permalink ids, `camera_operator` values and tile properties (TS-04). A test alert has been received; the
  TLS-expiry alert, the $300 budget alert, the billing export and a drilled restore exist (the deferred A-1/A-2a items). A live probe finds 0 instances of the full L3 §4.5 not-claimable
  list and C6's status words — "human-verified", "independently reviewed", "certified", "counsel", "editorial board",
  "one-click", "anonymous", "reproducible", "Reviewed", "Releasable", "complete" — outside disclosed contexts (TS-10).

### 5.2 Build-memory truth and verification (11 rows, 10.0 runs, all 11A; plus most of the seed)

- **Problem.** The resume point is not true: future-dated records, deleted append-only history, a 679 KB ledger whose
  orient costs ≈ 32k tokens and resolves a deferred HUMAN row, validators that check structure but not truth, and readouts
  composed after one-line approvals.
- **Evidence.** F-21…F-29, F-36, F-050…F-053, F-057, F-074; B1 (595 rows / 2,283 occurrences; 37 correction rows);
  B2 (42 losses in 24 commits); B3 §1; B4 §0 replays (G1 would have failed 70 commits; G3 would have stopped the chain at 4
  boundaries); B5 lessons 1–5; B7 (Round 10 ran in one Devin CLI session; readouts committed 32 s and 51 s after approvals).
- **Design.**
  - *Seed (Stage B, before any orchestrator resumes):* planning-ledger truth fixes (SEED-00); preflight with the A1 delta
    (SEED-01); the **guard core** (SEED-02: G1 record-dates in diff mode, G2 append-only core, G4 gate-table and guard
    sentence, G7 wiring, the G3a CI-boundary script) and the six living-record pin conversions (SEED-03) so the seed PR is
    green; `reports/memory-repair/` with `date_corrections.csv` and `append_only_register.csv` (SEED-04); **restore the 53
    deleted GATE DECISIONS rows first** (SEED-06), followed by an appended, dated annotation table of every restored row
    that is clock-false (e.g. rows dated 2026-09-10 but committed 09-13T19:40Z), a blanket or delegated decision
    (GL-GATE-01…06) or a counsel claim, with B1/B5/E1 references; `date_corrections.csv` is extended to the restored block
    and G1 gains a mode that checks restored dates against `git blame` (TS-08); date corrections in LEDGER/BUILD_INDEX (SEED-07) and elsewhere
    (SEED-08, **without** footers on landed ADRs — CF-02; ACCEPT-R8, ACCEPT-R10 and GATE-G3 all annotated with B7's facts; **no
    operator addendum describing a past state of mind**; the forward question "does ACCEPT-R10's acceptance stand?" is C-13,
    recorded with its own `date -u` — TS-08); BUILD_INDEX index repairs (SEED-09); archive the LEDGER head
    byte-for-byte and write a slim head ≤ 12 KiB (SEED-10); RETURN PASS superseding note (SEED-16); Round-11 CURRENT STATE
    with a `harness:` key and the OPERATING MODE (SEED-17).
  - *11A memory rows:* M1 full append-only modes + replay oracle (P34.7) → M3 obligation-event repair, which applies the
    seed's queued `pending_transitions` (P34.8; CF-03) → M2 ledger-contract validator + no-vacuous-pass (P34.9); date truth
    in code and fixtures (P34.22); remaining B2 restorations under M1 (P34.27); readout authorship rules (P34.28); RETURN
    PASS generator (P34.29); D-R10-MEMORY-1 split, option C (P34.30); living-record test lint (P34.31); ADR index generator
    with superseded status and the trigger register (P34.32); round-close record checks and the capstone two-sum
    contract (P34.33).
  - *Skills (out of repo):* B6's 25 proposals, all adopted (A-14 "All, staged"): Tier A at T0, Tier B-must before row
    201, the rest early in the round (OP-01…OP-04). They reach Devin CLI through `~/.claude/skills` (verified); Devin
    Desktop's skill path is verified at T6.
- **Requirements.** DRAFT-MEM-1…7 (clock-true records, append-only proven per change, CI truth at every boundary, gate
  records, readout authorship, ledger contract, live claims cite probes) → SIG-MEM-005…011; DRAFT-ENG-1/2/3/6 → new
  SIG-ENG ids; DRAFT-ENG-4/5 amend SIG-ENG-039/031 (§6).
- **Acceptance.** GATE-B: all validators green, seed PR 5/5 green, orient dry-run resolves row 201, LEDGER head ≤ 12 KiB,
  stale-token scan 0. 11A exit: M1–M10 run in CI; 0 pending seed transitions; 0 G1 (future-dated) and 0 G2 (append-only)
  violations in 11A commits. Round: ≤ 1 orchestrator close-repair (OM-02); no proxy signature.

### 5.3 CI and toolchain (2 rows, 2.0 runs; plus SEED-02/03 and operator settings)

- **Problem.** The chain never read CI; 16 PRs went red under later work; the runner image changes on 2026-10-19.
- **Evidence.** F-18, F-19, F-20; H1 (bottom-up merge conflict-free; transient red on `main` after #165/#179/#185); H2
  NEW-1…NEW-12 (unbound `gh pr checks`; 40 CI starts lost 09-17→22 unrecorded; Lighthouse flake).
- **Design (H2).** **P34.1 TC-PIN** (row 201): Node 24 LTS (`.nvmrc`, `engines`, `packageManager`, `engine-strict`) with one
  recorded lockfile regeneration; uv `required-version`; `runs-on: ubuntu-24.04`; `pipefail`; the `docs` job on push;
  `cancel-in-progress` for PRs only; `make ci-local`. **P34.2 TC-TRUTH:** the recorded-CI verifier, external-state delta,
  committed `ci_flakes.toml` (one re-run per head for allow-listed flakes only), advisory gate. Boundary gate G3a reads
  **head-bound** check-runs (`commits/<sha>/check-runs`), polls 60 s, 5-min grace, 45-min deadline; any failure, cancel,
  skip, missing or unknown → `blockedOn`. "CI unavailable" is never green: it needs a verbatim, time-boxed operator waiver
  and a later `ci-owed` sweep. Workers never close on red.
- **Requirements.** DRAFT-MEM-3 (CI truth at every boundary); DRAFT-ENG-3 (validator gates).
- **Acceptance.** P34.1 landed before 2026-10-19T00:00Z; every boundary in the round read head-bound CI and no row
  advanced on red (P38.1 audits this). The 16 pre-#190 reds are merge-readiness items for the operator, not Round-11
  blocks (Q-H2-1 reading of OM-05; B-15).

### 5.4 Data correctness and confidence — Stream L (22 rows, 23.5 runs; 11B 16.5) + placement rows

- **Problem.** The copying layer is faithful; the **synthesis** is not, and the operator has not been able to audit it
  (U-006). No independent humans exist to evaluate it (U-008/U-011).
- **Evidence.** L1 (17 invariants; weakest seams at identity, export shaping, independence, schema mapping, evaluation),
  L2 (45 metrics, 29 failing; the numbers in §2.3), F-504…F-531, F-208, F-262; D2-05…D2-09.
- **Design (L3).** *Correctness by construction first*, in order: CP-0 measurement substrate (quality harness, L2 baseline,
  read-only `sig_audit` login: P34.43, P34.44) → CP-1 truthful claim identity (P35.22) → CP-2 subject keys with append-only
  re-keying of the 5,278 collided subjects (P35.24) → CP-4 declared lineage, id namespaces and independence (P35.25);
  then CP-3 vocabulary and entity typing (P35.14), CP-6 technology typing (P35.15), CP-5 geometry (P35.16) and placement
  (JUR-01 → 02a → 02b, P35.17–19), CP-7 roles and time (P35.26), CP-9 resolver input truth (P35.27), CP-10 organisation
  identity (P37.46), CP-8 evidence bound to real bytes (the P35.61 live pass). **The graph-quality suite** (`sig.quality-
  suite/1`): 27 checks (L1 17 + L2 14 → 23 deduplicated + 4), each `enforce`, `ratchet` or `report`; only mechanical checks
  gate; ratchet = no regression past L2's baseline, flipped to `enforce` by the fixing ticket; runs at ingest, nightly
  spine probe, release check **V15**, and PR tests over a real-data regression corpus (P35.23); ≤ $5/mo. **Auto-write
  policy "derivation, not identity"** (A-6): collapse only mechanically proven copies of one upstream record (C0 duplicate
  target, C1 same id in a declared namespace and lineage, C2 bijective exact position in a measured mirror lineage),
  census-verified every run; every inferential match is published as a **possible duplicate** with basis and distance, and
  counts become **intervals** (P35.46–47). **Evaluation without independent humans:** mechanical census and samples with
  exact bounds; agent review in two blind contexts, labelled and never gating (P35.48); **no maintainer check** — the operator chose
  none (B-31), so every Class-S readout and `/quality/` say "no human check performed" (P35.49, OP-16 and OP-17 dropped);
  independent human evaluation **not planned** — owed under T-EVAL-IND (§11). The honest evaluation posture and its ER
  re-run land in 11A (P34.45, on the S5-3 OM-20 list; A-20 = a: its live-API effect is labelled); the public posture text
  ships in republish #1 only in its past-tense form, and the present-tense merge sentence ships with P35.63 (TS-03, TS-14). Public
  disclosure: `/quality/` from a release-bound `quality.json` (P37.45); per-record basis block (QB-01, P37.39); mechanical
  evaluation report (P37.44); re-measure L2 on the final release (P37.67).
- **Not claimable anywhere — L3 §4.5 in full (TS-10):** "human-verified", "independently reviewed", "certified"; any
  cross-source camera-match precision figure; 0.98 certification; completeness ("complete", "every"); model agreement as
  accuracy; organisation identity and "N agencies" counts beyond what the crosswalk proves; candidate recall; camera
  existence or operation (SIG records claims about cameras, not that a camera exists or operates); capture–recapture
  totals; maintainer independence; centrality, rankings or "most connected" claims. The 11A probe (P34.47) and P38.1a/b
  check the whole list.
- **Requirements.** SIG-CONF-001…014 (drafts D01–D14: basis classes, segregated agent labels, only mechanical checks gate,
  derivation not identity, no auto-written inference, check registry, ratchet discipline, real-data corpus, upstream
  reconciliation, maintainer checks, `/quality/`, mechanical estimands labelled, least-privilege audit path, declared
  lineage); amendments to SIG-EVAL-004 (waiver note), SIG-IDENT-028, §55.9; owner notes on EVAL-005/006/007.
- **Acceptance.** **P35.63's gate is ratchet-based (FEA-11): 0 ratchet regressions and 0 failures on checks that landed
  rows have flipped to `enforce`; any residual miss is a known-issue line in the readout, not a block.** The absolute
  targets below are **round targets**, re-measured at CONF-14 (P37.67) on the final release (L2 baseline in brackets): 0 subject-key collisions
  [5,278]; 0 1970 edges and every edge dated or "undated" [98.8 % undated]; 0 publisher-as-operator [74.2 %]; technology on
  100 % of site rows [77.4 % mistyped]; 0 axis swaps / 0 null-island points [562/14]; 0 undisclosed out-of-polygon points
  [2,370 > 25 km]; `unresolved` is not a dossier; 0 mixed-scheme dossiers; exact claim repeats ≤ 1 %; derivation census
  100 %; dossier counts ≤ 1.02× lineage roots [up to 2.25×]; contradiction recall 1.0
  on the synthetic set; byte binding 100 % for sources re-run in P35.61 [0/2.78 M]. Round: CONF-14 (P37.67) re-measures L2
  on the final release; every L3 target met or each miss names its fixing row; **M-1b: A-6 = a, so a sampled lower
  bound per declared namespace is reported as measured (no certification figure is claimed — "0.98" is L3's forbidden
  certification number)** (TS-10); `/quality/` live with every check, failing and ratchet checks shown, stating "no human
  check performed" (B-31). Byte binding covers sources re-run in P35.61; **the ≈ 2.78 M legacy claim–evidence links stay zero-byte
  under the insert-only spine and are labelled "capture not bound" (F-522 residual; COV-06).**

### 5.5 Sources and coverage — Stream I (US-nationwide Flock/Axon focus; non-US kept)

- **Problem.** Material blind spots: Flock only via one mirror (≈ 23 % of networks), Axon/Fusus/RTCC nothing, 22 states
  without a dossier, ATE/drones/FRT/forensics thin, the national OSM ALPR layer only as a stale republished copy.
- **Evidence.** I1 (14 blind spots), I2 search protocol, I3–I6 + I9a/b (logged queries, saturation), I7 (694 consolidated
  candidates; Part VIII preflight; rights lanes), I8 (acquisition plan, `data/acquisition_plan.csv`); F-329, F-330, F-366,
  F-374, I8 NEW-1…8; U-007.
- **Design (I8, scoped by D3 as ratified and by the GATE-P rights answers).**
  - *Rules.* Availability is never rights clearance; every activation follows its HG-03 line and a verbatim **ING-GO per
    wave** (B-11), and **the operator executes each wave's flip list** (OP-26). **GL-GATE-07 is re-confirmed** in the
    operator's adopted words (A-7): US public-record and open-licence Tier-1 batches flip batch-wide under precedent
    (RB-01…07, RB-09/RG1–5; E4-B1 a); RB-06b goes to a share-alike compartment and RB-08 territories count as US (B-33);
    the non-US database-right lines N1–N21 flip under the live precedents, express prohibitions excluded (B-34); the 46
    widening configurations inherit their parent's basis (X3). **Part VIII still binds:** S1–S9 members are ingested only
    through their screened lanes, including the two S8 tribal members (B-32), TR1–TR2 as facts + citations (B-37), the
    agent clears each screened family and the readout says so (B-42), and the residential demotion (P35.66),
    officer-naming gate (P35.28) and redaction (P36.15) land before Wave B activates (TS-07). **Robots:** GL-GATE-08 is
    re-confirmed as is (A-5) — disallows are disregarded and disclosed as host + count; the rule-7 opt-out register and the
    SIG-INGEST-046c reservation refusal are built first (P36.1a) and refuse any host that publishes an explicit reservation.
    **Terms-conflicted public pages are fetched** (A-17 D3-Q3 b; B-35 IT7; B-39 C2/C3; E4-R2a b): Flock transparency
    portals (P36.74), Axon Fusus "Connect <Place>" pages (P36.76), DocumentCloud/MuckRock (P36.77) and Sourcewell/OMNIA
    contract pages (P36.78), all inside **ADR-184's envelope** — public, unauthenticated pages only; no logins, API keys or
    access-control circumvention; rate-limited; robots per GL-GATE-08; terms text captured verbatim and the exposure
    disclosed; the Part VIII screen on every byte; SIG-PUB-002 material (private-person names, home addresses) redacted
    before anything is persisted. **Express terms:** the ≈8,088 live rows stay (A-8, ADR-183); new non-commercial sources
    are facts + pointers only (A-9); IT1–IT6 are facts-only pointers or declined; IU1–IU5 terms are captured in P36.2, then
    a line (B-36); EDGAR gets a facts-only basis but ingestion stays later, first request only after the alias (B-38).
  - **Flock and Axon depth (replaces S4c's "ceiling the terms impose", TS-06).** With D3-Q3 = b, Flock and Axon coverage
    is no longer limited to agency, procurement, council and statutory origins: the direct portal connector gives
    per-agency Flock retention, camera counts, aggregate search counts and shared-with lists; the Eyes on Flock share lists
    become organisation-level `configured_access` claims (P36.75; A-22 b) that feed the state × state Flock-sharing
    overview (A-11); Axon Fusus Connect pages give programme-level registry facts and counts. **Still dark by design:**
    anything behind a login or key; person-level fields; search reasons, case numbers and audit rows (Part VIII,
    SIG-PUB-003a); private Connect registrants (SIG-PUB-002). The legal exposure of fetching against the vendors'
    anti-automation terms is the operator's accepted risk (R-18).
  - *Enablers first (P35.6–7):* acquisition plumbing and harness with I8's preconditions — the reviewed ArcGIS rate applied,
    a second cadence batch round, new triggers created disabled, the 63 truncated source ids fixed, aggregation for ATE
    violations — then registry label fixes M1–M7. The scheduler of record and cron lint (P35.1) precede them (CF-09).
  - **Wave A** (widening, 43 of 46 units, ≈ 18k claims): Legistar keyword-filtered paged matter pass, USAspending/CROL
    vocabulary, the 2026 state ALPR statute seed refreshed from origins (C9 a) (P35.8–10) → activation P35.11 (live
    2026-10-19→10-23, 14:00–20:00Z).
  - **Wave B** (Tier 1, 108 candidates, ≈ 89 new registry rows, ≈ 250k claims, **plus the direct Flock transparency-portal
    family**, P36.74) — in 11B (FEA-02): robots/opt-out register and reservation state first (P36.1a; the crawler text
    P36.1b follows in 11C); ATE concept (P36.3); eight family tickets (P36.4–P36.11, P36.9 split a/b) and P36.74; then
    P35.28, P36.15, P35.66; then activation **P36.12, dispatched in 11B with ING-GO-B and the Wave-B flip list collected
    at GATE-G4**, its legs run from the OM-19 queue 2026-10-26→11-05 (one family a day; ACQ-11 and ACQ-15 may share).
    Wave-B data publishes in P36.72b's Class S release (≥ 11-13T12:00Z). The owed rights batch and terms capture P36.2
    sits in 11C.
  - **Wave C:** OSM becomes the **origin** of the national ALPR layer — code P37.1 and activation P37.2 at the head of
    **11C**, ING-GO-C collected at GATE-G5 (Q-23 = a); legs (pre-grow → tier bump after its go → run → 24 h soak → revert)
    queued for 2026-11-16→11-20. **US-first ordering, non-US kept (S5-4; CF-06 not confirmed):** the national run keeps
    its non-US objects, so I8's ≈ 1.11 M-claim Wave-C figure is again the planning figure. Wave-B's new monthly crons fire
    after 11-20 (FEA-15).
  - **Wave D (in scope, I8-Q5 = a):** eight Tier-2 rows P37.47–53, the international portals and OGC WFS family
    **P37.69a/b** (ACQ-23a/b; N1–N21) and activation P37.54, whose first window also activates the Axon Connect,
    DocumentCloud and Sourcewell/OMNIA connectors (P36.76–78). Windows 11-23→12-04 and 12-14→12-18 hold ≈ 12 family-days
    against ≈ 13 weekdays (inference — tight); second-window sources ship in the 2027-01-15 cut, and A-19 lets an overflow
    slip.
  - *Source ops:* SAM.gov sweep resumes (P37.11); keyed US 511 (P37.12) and AU QLDTraffic/NSW (P37.70) after the operator
    registers keys once `contact@` exists (B-18, C-8); registry completeness + recurring discovery sweep (P37.13);
    statute-seeded records leads (P37.14); scheduled parser canary (P37.15); rights batch + terms capture (P36.2);
    closeout P37.66.
  - *Capacity (re-checked at S6 for the non-US scope):* I8's figures apply again — ≈ 1.5 M new claims (≈ 3.8 GB at
    ≈ 2.55 KB per claim; Wave C ≈ 1.11 M incl. non-US) plus organic growth → 11–17 GB at year end; the share-list claims and
    vendor-page connectors add an estimated ≈ 0.5–0.6 M claims (≈ 1.3–1.5 GB; inference — the share lists hold 474,184
    edges, portal facts are small) → **≈ 12–19 GB, inside B-11's 40 GB cap and the 25 GB pre-grow**. No permanent scale-up
    is planned (LATER-08 trigger unchanged).
- **Requirements.** SIG-INGEST-036 rule 7 opt-out register + SIG-INGEST-046c reservation refusal (P36.1); the
  SIG-INGEST-037 counsel clause waived (WV-07) and the terms-conflicted fetching recorded by ADR (ADR-184); SIG-CONF-D09
  upstream reconciliation; **SIG-CHART-025 amended** to US-nationwide multi-vendor breadth with per-class and
  per-geography quality labels (A-17, Q-E2-22 a); SIG-PUB-017 jurisdiction-conditional publication for non-US rows.
- **Acceptance (P37.66 ACQ-28, live).** The national ALPR layer comes from its origin; every US state and DC has a
  dossier; **OSM ALPR, Eyes on Flock (incl. the share lists as claims) and Atlas vendor data reach place and entity
  pages (D3 §3(b); COV-05)**; all Tier-1 and widening candidates are live or dispositioned; with Wave D in scope the targets
  are I7's Tier-2 projection — **46 of 51 states + DC, ≈ 20–25 of 36 thin cities, 29 of 29 technology classes** (core-only
  floor: 40, 13, 28; inference) — and camera layers in up to 10 countries (I8 §9 #11); 11–12 of the 14 I1 blind spots
  moved. **Flock / Axon / other vendors trace (COV-05):**

  | vendor | rows | acceptance threshold |
  |---|---|---|
  | Flock | P35.8 (Legistar matters), P35.9 (awards), P36.5 (agency ALPR/Flock layers incl. FDOT inventory 407 + removal ledger 523), P36.8–P36.9b (statutory operator lists), P36.11, **P36.74 (direct transparency portals)**, **P36.75 (share lists as claims)**, P37.1–P37.2 (national ALPR origin, 154,814 objects), P37.25 (state × state sharing overview) | portal facts for every reachable transparency portal (I3: 917 portals), each with captured terms and a fetch record; share lists at organisation level only; agency-origin layers for 14 agencies in 11 states; Legistar Flock matters in ≥ 8 cities; the national layer from its origin; every Flock entity link dated and sourced |
  | Axon | P35.9 (USAspending, BWC ALN 16.835), P35.8 + P36.11 (RTCC/Fusus council matters), P36.7 (programme registers), **P36.76 (Fusus Connect pages)** | Axon present as an entity with dated, sourced agency links in ≥ 3 cities; programme-level Connect facts for every reachable agency page; 0 registrant bytes in any tier |
  | Motorola/Vigilant and others | P35.8, P35.9, P36.5, P36.7, P36.10, **P36.77 (DocumentCloud documents)**, **P36.78 (Sourcewell/OMNIA contracts)** | each with dated, sourced agency links |

  P37.66 reports per-vendor agency counts by state. **Stays dark by design or terms:** anything behind a login or key;
  person-level data, search reasons and audit rows; private Connect registrants; EDGAR (later); CourtListener bulk; MS, WY,
  MT, AS, MP (I8 §9); tribal nations beyond the two screened S8 members.

### 5.6 Transparency and export — Stream J (30 rows, 26.5 runs)

- **Problem.** A checksummed 1.05 GB licence-separated release exists that nothing links to; 0 of 255 public evidence
  items carry an upstream URL; no source index, per-source pages, run logs or downloads; permalinks do not pin.
- **Evidence.** J1 (exposure inventory), J2 (prior art), J4 (redistribution matrix, `data/redistribution.csv`), J3;
  F-07, F-099, F-102, F-103, F-110, F-386, F-389, F-390, F-399, F-400, F-405, F-431; U-003.8–.10; D2-04, D2-06.
- **Design (J3 as amended by K9/K10 and adopted by K13).** Every transparency surface is a **static artifact made at
  export time** from one read-only spine snapshot plus scrubbed run records, bound into the immutable release. New moving
  parts are only: an append-only `ingest_run_report` table (P35.32), a 6-hourly **status lane** job writing only
  `status/**` (P36.43; B-19), and a **zero-egress distribution host** with a $50/mo egress ceiling and kill switch (P35.5;
  A-3). Rights are keyed on the **source** (J4 lanes); attribution is rendered from the registry; every log field passes a
  fail-closed scrub (P35.31). Rows: run/capture/issue export (P35.33), registry lanes and metadata (P35.35), statements
  files + `upstream_href` + the provenance panel (P35.36), figure → evidence pointers (P35.37), data dictionary (P35.39),
  source universe and freshness v2 (P35.40–41), citation block + release id on every page (P35.42); publish matrix,
  execution-keyed ingestion history, source pages A/B, sortable sources table, known issues, downloads center, evidence
  anchors (P36.45–51, P36.69); site snapshots `/s/<pub>/` and the `withBase` refactor (P36.66), changelog and
  `/v1/changes` (P36.67), per-source extracts and version index (P36.68); raw archive for raw-ok sources only after the
  Part VIII byte screen (P37.36; B-19), source changelog (P37.41), API parity (P37.42), archival deposits and WACZ
  (P37.55–56; Zenodo publish is operator-run, OP-19), transparency acceptance + HG-11 readout (P37.65). `/data-freshness/`
  301s to `/sources/`. The repo is public, so commit hashes are shown (C-6). B-19 was answered "yes" on every member;
  the express-terms rows are not withdrawn (D-J3-5 = b): each file's ATTRIBUTION states their captured terms and the
  operator-accepted basis (ADR-183).
- **Requirements.** SIG-TRANSP-001…043 (J3 D01–D25 + K9/K10 D26–D43 via UXR-A10); amendments to SIG-METRIC-007,
  SIG-EVID-009, SIG-UI-035, SIG-EXPORT-002; SIG-REL-D08/D09.
- **Acceptance.** P37.65: J1 (figure → rows in ≤ 3 clicks), J4 (pinned URL returns identical bytes after the next
  release) and J5 (changes per place, source and entity) pass on a real diff of ≥ 2 activated releases (CF-13); U-003.9
  and U-003.10 pass their K-row live checks (§5.7); V8 attribution and V12 scrub green.

### 5.7 UX and product — Stream K (UX core 65 rows / 56.5 runs; UX explore 20 rows / 17.5 runs)

- **Problem.** The site is technically precise (U-004) but confusing and verbose (U-005); none of the U-003 asks works
  as a user expects; C2's agent walkthroughs passed 5 of 31 tasks.
- **Evidence.** U-003.1…U-003.11, U-003.G, U-004, U-005, U-007; C1–C4, C6 (RI-01…RI-60), K0–K12b, K14; F-104, F-105,
  F-106, F-414, F-420…F-422, F-431, F-452, F-469, F-481.
- **Design (K13; K0 page types, A-12 = a).** Header: **Places · Explore (Map, Graph, Search, Disagreements) ·
  Organizations · Watch · Sources & data · About** + search. Page types: **T0** records/print/feeds/dispute (no script) ·
  **T1** content (≤ 20 KiB enhancement; JS-off text equals JS-on text) · **T2** exactly three app-like surfaces (`/map/`
  ≤ 360 KiB, `/explore/` ≤ 120 KiB, `/search/` ≤ 60 KiB; URL state, server-rendered first paint, a no-JS equivalent) ·
  T3 `/curate/**` never published. One lexicon (hollow = single source; line pattern = access kind only; raspberry =
  disagreement; amber = provisional; hatch = absence); one search stack; one URL-state contract (`sig.workspace-state/2`);
  one redirect generator; shared modules with one owner each. Foundations land before pages (P35.50–52 registry, budgets,
  tile retention; P36.16–30 tokens, lexicon, chrome, CSP, enhancement kit, component kits, copy lints, brand, print v2,
  figure kit, entity URL keys). Correctness rows in 11B precede every new surface (K13 R-1: the UX must not outrun the
  data).
- **U-003's headline clause traced (COV-04).** *"A first-time user of SIG should be able to do all of the things
  currently advertised / attempted on the current surveillancegraph.org deployment but the functionality should actually
  work"* → P36.72a and P37.68d run a `review/ROUTES.csv`-driven check: every route advertised on the 2026-09-27 release
  either passes a user-expectation check or shows an honest notice naming its decision or LATER trigger. **Withdrawn
  rather than fixed this round** (accepted by the operator at C-12, 05:03:05Z): one-click dispute (honest notice +
  e-mail), `/intake/` (dark, B-8), `/contribution-back/` (LATER-03), `/curate/` (removed), `/task/new/` demo pages
  (stripped), research-queue "send" (drafts only).
- **Every U-003 ask traced** (rows from `data/round11_plan.csv`; live checks from K13 §5.1, run at P36.72a/b / P37.63–64 /
  P37.68a–d):

  | ask | rows | live check (summary) | journeys |
  |---|---|---|---|
  | U-003.1 map with a real basemap | P34.15 (W0 honesty), P35.52 tile retention, P36.27, P36.33 basemap host, P36.36 no-JS map, P36.37 shell, P37.17–20, P37.29, P37.63 | self-hosted basemap; every located record at every zoom (tile verifier 0 missing); "Oklahoma City" frames the city; no-JS `/map/` ≤ 100 KiB | A1, O1, O3 |
  | U-003.2 readable labels, entity pages, global graph(s) | P34.15, P35.29–30, P36.29–30, P36.41–42, P37.21–28, P37.39, P37.64 | 0 UUID labels (crawl); Vigilant Solutions (LEARN) named with a page; every edge dated or "undated"; overviews O0–O5 navigable; ≤ 2 actions to evidence | J2, J3, O1 |
  | U-003.3 flexible search | P36.31–32, P36.34, P36.38–40, P36.56, P36.71, P37.19, P37.43 | held-out ≥ 80 % top-3 (dev ≥ 90 %); 0 misleading top hits; works with JS off | A1, J2 |
  | U-003.4 dossiers grouped by country | P34.14, P35.17–19, P35.45, P36.34–35, P36.72 | United States → states; other countries → subdivisions; "Not yet placed"; `/dossier/id/` split | A1, O1 |
  | U-003.5 which sources contributed what, when | P35.36–37, P35.44, P36.52–53, P36.69, P37.39 | "from 11 sources" → breakdown summing to the figure → source page → last run | J1, A2 |
  | U-003.6 embedded map/network visuals + search on dossiers | P36.27–28, P36.54–57, P37.28–29 | Figure 1 on every located dossier, printable; map activates on click; network figures or a typed empty state | A2, A3, O1 |
  | U-003.7 `/watch` QA | P34.20, P35.43, P36.59, P37.30–34 | producer fills `watch.json`; feeds validate (RFC 5545, RSS, JSON Feed); empty states name the cause | O2, A2 |
  | U-003.8 `/evidence` shows nothing | P34.20, P35.36, P36.51, P36.60, P37.36–37 | every publishable artifact listed with honest binding states | J1, J3, A4 |
  | U-003.9 sortable sources table, downloads, versions, metrics, ground truth | P35.5, P35.32–33, P35.35, P35.39–41, P36.48, P36.50, P36.68, P37.61 | `/sources/` 342 rows sortable without JS; latest extract + version index per published source; homepage and terms links | O3, J1 |
  | U-003.10 per-source detail pages | P36.43, P36.45–47, P36.49, P36.69, P37.36, P37.41–42 | metadata, rights record, conduct, execution-keyed history, captures with hashes, per-file downloads, changelog | J1, J5 |
  | U-003.11 research queue usable | P34.12, P36.58, P36.61–63, P37.32, P37.35, P37.62 | UUID URL → 301 → human-readable handle titled with the agency; ≤ 50 cards/page; request drafts (SIG sends nothing) | O4, A4 |
  | U-003.G friendlier, richer, traversable, inspectable | P34.11, P34.13, P35.42, P35.50–51, P36.16–26, P36.64–67, P37.38, P37.40, P37.60–61, P37.65, P37.68, P38.5 | ≤ 6 nav sections; every figure ≤ 2 actions to evidence; disagreements and changes pages live | all 13 |
  | U-003.X agent's own ideas | — (K12a + K12b; 32 ideas: 29 accepted, 3 deferred — K13 §5.2) | already done as planning work | — |

  U-001 → P36.64 (Home/About/How it works) · U-002 → P37.68 (CAP-01) · U-004 → P36.17 (precise sections kept byte-for-byte
  behind "In brief") · U-005 → P35.36–37, P35.42, P36.17, P36.24, P36.40, P36.51, P36.66, P37.26–27, P37.40 · U-007 →
  P36.64, P37.66–68.
- **Requirements.** K13's 51 rows (`data/k13_requirements.csv`): UXR-01…38 and the 13 adopted families UXR-A01…A13
  (§6.2).
- **Acceptance.** P36.72a/b (ACC-PLACES, HG-11) closes **U-003.3, .4, .5 and .9** and the first page of every other ask
  (COV-11); U-003.1/.2/.6/.7/.8/.10/.11 close at P37.63, P37.64 and P37.68a–d;
  journeys A1–A4, J1, O1, O3, O4 pass the agent walkthrough at 390 and 1440 px (`agent-verified`); search resolves 55
  jurisdictions, 20 cities and the top 25 vendor and agency names; search relevance is reported as "held-out ≥ 80 % top-3
  on an **agent-authored held-out set; not independent**" (B-28; written by P36.79 and sealed from the tuning contexts;
  TS-20); K0 budgets and axe pass on real
  data. P37.63–64 (map; entity/graph/figures). P37.68a–d CAP-01: all 13 journeys pass the agent walkthrough
  (`agent-verified`) and the **operator walkthrough (maintainer, not independent)** (TS-22). Clarity (D3 §3(c)):
  §1 above the fold; home ≤ 5 screens at 390 px with ≤ 6 figures; 0 internal ids in prose; K14 design system + dark mode on
  every template; a "start here" path per persona; a fresh agent can say what SIG is in 2 minutes; "beautiful" is the
  operator's call (B-29 gallery).

### 5.8 Release and ops (21 rows, 22.0 runs)

- **Problem.** The live release id is not content-addressed or belief-pinned; versions are `0.0.0`; a web redeploy can
  erase release trees; live nginx cannot honour withdrawals; no cadence; operations have no scheduler of record, no
  runbook, no least privilege.
- **Evidence.** G3 NEW-1…6; G1 risks G1-01…17; F-07, F-11, F-12, F-272; C4 NEW-9/10.
- **Design (G3).** Release = content-addressed `p-<sha256(descriptor v2)>` + immutable label `sig-YYYY-MM-DD.N`; one
  command family `sig-ops release cut → build → stage → verify → promote` under one lock; a **private release bucket** and
  private staging origins; promotion by **metadata only** (new config generation + digest-pinned roll); verification
  **V1–V15** (V15 = L3's graph quality); Class R (the standing go in the operator's adopted words, B-9, renewed at each sub-round GATE) vs **Class S** (candidate-specific signed readout,
  HG-11); cadence monthly on the first weekday on/after the 15th at 14:00Z, **suppressed when a Class S promotion landed within 14
days** (FEA-09), early at ≥ 10 % net and ≥ 14 days, alert at 35 days; automatic rollback;
  15-minute withdrawal on every alias with tombstones; a pipeline signing key for manifests (B-20); semver tags on `main`
  by the operator only. Rows: REL-10 versioning (P34.23); REL-01 identity v2 + clock guards (P35.12); REL-02 provenance
  stamp and `release.json` (P35.13); REL-03a/b pipeline, private bucket, templated nginx, config generations
  (P35.53–54); REL-08 rollback/withdrawal/purge (P35.55); REL-04a/b verification suites + auto-rollback (P35.56, P35.58);
  REL-05 API release parity (P35.57); REL-09 dark cutover (P35.59); REL-06 classifier, standing go, readout generator
  (P35.60); REL-07 cadence automation (P36.44); REL-11 second-release acceptance (P36.70, now after P36.72b on the second activated
release). The Class R standing go expires (§3.3). **Ops (G1):** P34.39a 10-10 replay read-back + P34.39b first-fire
  monitoring leg (non-blocking); P34.42 least-privilege identities; P35.1a/b scheduler of record + live-diff + cron lint (ADR-174 supersedes ADR-016's scheduler clause and
  ADR-076's scheduling path);
  P35.2 alerting as code; P35.4 runbook; P36.13 API rate limits + optional Cloud Armor; P37.3 evidence-store hardening +
  off-instance copies; P37.4 security baseline. Detail in §10.
- **Requirements.** SIG-REL-001…014 (G3 §10 D01–D14); SIG-OPS-001…012, SIG-SEC-007…009, SIG-STORE-048 (G1 §4 + B4
  DRAFT-OPS-1/2).
- **Acceptance.** P35.63 promoted under a signed HG-11 readout with V1–V14 green, V15 at "0 ratchet regressions + 0
  enforce failures" (FEA-11) and 0 waivers, live rollback rehearsal
  done, nginx honours withdrawals; P36.70 measures rollback and withdrawal timings on the second release; every page shows
  release label, as-of, commit and build time.

### 5.9 Round-10 activation (16 rows, 19.0 runs; G2)

- **Problem.** No Round-10 surface is deployed; the GATE-G3-signed candidate is a 0-record fixture with a future date;
  seven Round-10 return passes were prepared, not executed.
- **Evidence.** F-14, F-15, F-16, F-051, F-152…F-161; G2 §0; D-R10-LIVE-1, D-P32.23a-1, D-R10-PUBLISH-1, D-P32.18…21-1,
  D-P32.16-1, D-R10-SOURCES-1.
- **Design (G2 steps 0–8 → rows).** Step 0 = §5.1 + sqitch hygiene with a round-trip CI (P34.24a) and an **L44–52 clone
  rehearsal of the exact plan tip, after P34.25 adds its `sig_read_public` grants change** (P34.24b; FEA-07). Step 1:
  ADR-124 allow tooling and the flagged-organisation census (P34.26) → **Round-10 schema (sqitch L44–52) + ADR-124 allows
  + Round-10 API roll** (P34.46; ≥ 2026-10-14T14:00Z after the 10-10 read-back P34.39a; 48 h soak; in-ticket go; operator
  available in the slot). **P34.46 go/no-go (FEA-07):** the rehearsed ACCESS EXCLUSIVE lock on `claim_evidence` must be
  ≤ 20 min and ≤ 2× the P34.24b measurement; disk headroom ≥ 2× the table size; `lock_timeout` set; the sqitch plan diff
  against the rehearsed tip = 0 (otherwise P34.46 first re-rehearses on a fresh clone); a `/status/` and API maintenance
  notice for the slot; spine-writing scheduler jobs paused for the slot (the contract lists them); no tier bump. Over any
  threshold → stop, record the measurement, and ask the operator (a longer announced window or defer). Step 2: execution host + least-privilege logins (P34.43) → D-R10-LIVE-1
  hosted audit → bounded apply with recorded `--authority` scope → freeze (P35.61, row 183's pass). Step 3: production
  candidate with true dates (P35.62, row 188's pass). Step 4 (engineering from day 1): release-archive correctness and
  export-mode build (P34.34), research-dossier disclosure (P34.35), release-search states (P34.36), intake defects
  (P34.37), serving topology dark (P34.40), withdrawal-barrier bytes (P34.41). Step 5: D-R10-SOURCES-1 prep (P34.38) →
  dossier live captures under HG-03 (P37.16, rows 179–182). Step 6: intake operation stays **dark** and conditional
  (P37.59; B-8 email-only). Step 7: **first model release** D-R10-PUBLISH-1 (P35.63, row 191's pass) — the old GATE-G3
  signature is superseded, **not transferred**. Step 8: D-R10-MEMORY-1 split (P34.30).
- **Acceptance.** 11A exit 5: G2 step 1 live, after the 10-10 replay was read back. **P35.57** (API release parity, its
  own go collected at G4) stays at the head of 11B as an improvement; under A-20 = a the 11B structural spine writes may
  change live API answers before HG-11, disclosed by the basis label and the `/status/` notice; 11B exit 1: P35.63 promoted
  (§5.8). Research dossiers become public only after live captures (B-7); those captures (P37.16a/b) are cleared per
  family by the agent's Part VIII screen, disclosed as "cleared by agent screen, no human review" (B-42), and depend on
  P35.31's capture-tier fix (TS-07).

### 5.10 Governance and records (5.5 runs after S6; plus seed ADRs and records)

- **Problem.** Spec MUSTs contradict operator decisions; public and repo text implies an editorial board, counsel and
  independent review that do not exist; consequential records rest on tentative words.
- **Evidence.** F-31, F-185, F-189, F-190, F-191, F-195, F-199, F-471; E1 (contradictions), E2 (22 memos + A-1), E3
  (human-work options), E4 (22 rights decisions); U-011, U-013; B5 §4.
- **Design (as ratified).** The A-4 posture package (disclosed single maintainer, no counsel) by ADRs 163–167 and 170
  (§7); **all seven waiver candidates waived in the operator's adopted words** (A-23), each an ADR with compensating
  controls and a revisit trigger (§6.5); repo honesty corrections (governance doc, `sources.toml` "counsel" reviewer values
  → "the operator's own determination (no counsel)") (P34.16) — **P34.16 has no live stage, so public `main` keeps the
  false governance text until the operator merges; the OP-08 merge sitting is a safety item (TS-09)**; ADR-086 and ADR-106
  get appended `Qualified by ADR-167 (<date -u>)` status lines at T1; ADR-167 and every release manifest carry E2's label
  text once the operator confirms it verbatim in a copy batch: *"No lawyer's written opinion has been obtained; nothing
  here states that this publication has been cleared by counsel."* (E2:569-571; agent-drafted); robots/opt-out register and
  crawler policy text (P36.1); registry rights-record hygiene (P37.6); a **public editorial decision log** under interim
  single-maintainer authority, which also logs every WV-06 deletion (P37.7); legal-demand posture + published counts,
  warrant canary declined (P37.8; SIG-SEC-003); the **single-operator true-deletion path** (P37.71, WV-06): design first,
  never on an OM-20 list, never run by an agent without the operator's in-ticket go, every use publicly logged with its
  reason and a tombstone (category + date, never content). Records (seed): the C-3 sentence adopted at GATE-P recorded as
  a present statement dated 2026-10-01T04:54:19Z, never as a 09-16/09-28 decision (TS-19; a G4 lint test); C-13's
  "superseded" (05:03:05Z); ACCEPT-R8, ACCEPT-R10 and GATE-G3 annotated with B7's facts (B-4, TS-08); C-2's planned
  hand-over; the restored GATE DECISIONS block annotated (SEED-06); the go-live spec records GL-GATE-06…08 as dated,
  annotated records **and GL-GATE-07/08 as re-confirmed at GATE-P in the operator's adopted words** (A-5, A-7; Q-E2-19).
- **Requirements.** SIG-PUB-008 stands (nobody named; default-deny); **WAIVED (ADR) at A-23:** SIG-GOV-012/013 (WV-01),
  SIG-GOV-015 (WV-02), the HG-11/PUB-008 second-reviewer role (WV-03), SIG-UI-042's release block (WV-04),
  SIG-GOV-001/002 (WV-05), SIG-GOV-008's two-person authorisation (WV-06; its tombstone clause stands), the counsel
  clauses of SIG-LIC-009/SIG-INGEST-037 (WV-07); non-weakening amendments: SIG-SEC-003, SIG-LIC-004 + HG-03 text, §26 rule 7
  opt-out register, SIG-CONTRIB-012/013/030a (timing → later-phase), SIG-CHART-025 (A-17).
- **Acceptance.** 0 counsel/board/independent-review claims without basis (11A live probe and P38.1); every governance ADR
  carries the operator's adopted words where the decision is theirs, labelled "agent-drafted, adopted by the operator";
  `/editorial-standards/` reads "not yet performed"; every readout states "single maintainer, no second reviewer" and
  "no human check performed"; the deletion path exists and has never run without a logged go.

### 5.11 Engineering debt (4 rows, 5.5 runs; plus debt folded into owning rows)

- **Problem / evidence.** F5 (13 PKG packages, `data/eng_debt.csv`), F3 (`data/backlog_triage.csv`: 32 open BL rows,
  several already satisfied), F2a (34 claimed-but-untested ids), F-32, F-39.
- **Design.** Most debt rides its owning ticket (S1a §3.2 splits PKG-01…13 across ACT-05/09/16/17/17b, JUR-01/02a/02b,
  DATA-01…04, CONF-04, TX-14, CI-01, SEED-02/15, OPS-02/03). Standalone: run telemetry per-fetch fields (P35.34);
  ingestion framework hardening + disappearance events + unwired-function scan (P37.5); projection rebuild CI +
  layer-direction test + whole-graph audits (P37.57); generated-vs-deployed schema conformance (P37.58; SIG-STORE-045,
  BL-049).
- **Acceptance.** F2a's 28 PARTIAL "claimed" ids each have an id-linked test or a named home; P37.57–58 green in CI.

---

## 6. Requirement changes (drafts; numbering and final wording are T1's)

### 6.1 Where the changes land

- **A new Part XII, §56 "Round-11 contract extension"**, following §55's pattern (Part XI, `96b_partXI_s55_six_streams.md`),
  as a new `spec_src` file (proposed name `96c_partXII_s56_round11.md`), rebuilt by `BUILD.sh`; new ids are append-only.
- **Amendments** to existing sections (§6.3), each an append-only note or a re-worded clause recorded in **Appendix G
  (new G.7 "Round-11 corrections and extensions")**; R10-A6 is not edited.
- **Appendix F** rows for every new ADR (§7); the ADR index is regenerated, never hand-edited.
- **Go-live spec** (`docs/3_sig_golive_spec.md`, hand-edited, unvalidated today, F-35): goal 5, GL-GATE-01/02/05, the gate
  register, and GL-GATE-06…08 (which today exist only in the LEDGER) reconciled following ADR-145's pattern (E2-18).
- The family table at spec line 117 gains the families T1 opens (`SIG-OPS-*` is reserved there "for future use").

### 6.2 New requirement families (draft ids → proposed families; one-line summaries)

| proposed family | drafts (source) | summary of the draft text |
|---|---|---|
| SIG-MEM-005…011 | DRAFT-MEM-1…7 (B4 §5) | recorded dates come from the clock and are never later than their commit; protected regions change only by append, placeholder fill, annotation or archived replacement; CI read at every boundary, red → `blockedOn`; gate records verbatim, dated at or after the pause, hedged words never decisions; permanent readout guard sentence, agent text labelled; ledger orient budget and value-only CURRENT STATE; any statement of production state cites a probe-run record ≤ 24 h old |
| SIG-ENG (new ids) | DRAFT-ENG-1/2/3/6 (B4 §5) | tests assert invariants, never living records; verdict grammar + cross-checks against obligations; every validator runs in `make docs-check` and CI and fails on vacuous passes; every ADR revisit trigger has a register row and fired triggers an answer before round close |
| SIG-OPS-001…012 | G1 §4 + DRAFT-OPS-1/2 | quarterly restore drill at scale into an isolated instance; deletion protection, retain-on-delete, maintenance window, monthly logical export; public route allow-list; single publish path with a release record; daily live-config reconciliation and cron lint; alerts reach a human within 1 h; SLOs (SHOULD); republish at least monthly; measured cost vs a ceiling; runbooks (SHOULD); probe placement and probe-run records; fixture-sentinel scans |
| SIG-SEC-007…009, SIG-STORE-048 | G1 §4 | no basic roles on workloads; digest pinning for services too; secret lifecycle (SHOULD); hosted evidence immutable (retention or versioning ≥ 90 days; writers cannot delete; "WORM" only when true) |
| SIG-REL-001…014 | G3 §10 D01–D14 | content-addressed release id + `sig-YYYY-MM-DD.N`; descriptor v2 binds snapshot, commit, versions, gates, evaluation status; clock-true release dates; public bytes change only through the release tool; promotion metadata-only; V1–V14 on private staging + post-promote checks with auto-rollback; snapshot containment; stamp and `X-SIG-Release` on every page/response; API release parity; monthly cadence; Class S unless Class R is proven; rollback re-applies withdrawals; 15-min withdrawal; one version source and operator-placed semver tags |
| SIG-CONF-001…014 | L3 §7 D01–D14 | basis class on every quality statement; agent labels segregated; only mechanical checks gate; derivation, not identity; no auto-written identity inference without independent evaluation; check registry; ratchet discipline; real-data regression corpus; upstream count reconciliation; maintainer checks disclosed, blind-first, verbatim; public `/quality/` + per-record basis; mechanical estimands labelled; least-privilege audit path; declared lineage (SHOULD) |
| SIG-TRANSP-001…043 | J3 §11 D01–D25; K9/K10 D26–D43 (UXR-A10) | static, release-bound transparency artifacts; source-keyed rights lanes; fail-closed scrub; source index and pages; execution-keyed run history; figure → evidence; provenance panel with honest binding states; downloads center with integrity, licences and attribution per file; egress controls; status lane; issues log; site snapshots; changelog and id diffs |
| K13 UX set | UXR-01…38 (36 MUST, 2 SHOULD) + UXR-A01…A13 adopting SIG-UI-D01–D10 (K0), SIG-UI-DM01–09/SIG-GEO-DM10 (K1), SIG-UI-D20–D34 + SIG-EXPORT-D20/21 (K2), SIG-SRCH-D01–D14 (K3), SIG-JUR-D01–D12 (K4), SIG-DSRC-D01–D09 (K5), SIG-UI-DV01–DV12 (K6), SIG-WATCH-D01–D10 (K7), SIG-EVUI-D01–D10 (K8), SIG-TRANSP-D26–D43 (J3/K9/K10), SIG-RQ-D01–D10 (K11), DR-K14 (K14), SIG-CONF-D01/D05/D11 (L3) | navigation ≤ 6 sections and capability binding; every figure ≤ 2 actions to evidence; no UUID labels; one lexicon; one URL-state contract; one redirect generator; page types and budgets; no-JS parity; typed absences; single-source shares visible; "records" wording until the dedup ships |

T1 de-duplicates against existing ids (for example SIG-REL-D09 refines the release-id clause of SIG-OPS-004, and
SIG-REL-D11 merges with SIG-OPS-008's triggers) **and against draft ids listed under two families** (SIG-TRANSP-D26–D43
appear under TRANSP and the K13 set; SIG-CONF-D01/D05/D11 under CONF and K13; COV-14). **Who writes which family
(FEA-01):** SEED-12 writes MEM, ENG, OPS, SEC, REL and CONF (+ the §6.3 amendments, App F/G.7, the go-live spec);
**PLAN-11B** appends SIG-TRANSP (the 11B transparency rows cite it); **PLAN-11C** appends the K13 UX families and decides
whether they become new prefixes or fold into SIG-UI. Every append is an append-only `spec_src` change rebuilt by
`BUILD.sh`, from this ratified plan (OM-03). SIG-CONF-D10 (maintainer checks) is written as "disclosed when
performed"; Round 11 performs none (B-31), and SIG-CONF-D02 segregates the agent labels it does produce.

### 6.3 Amended existing ids and sections

| id / section | amendment | source |
|---|---|---|
| SIG-ENG-031 | phase completion requires green PR checks (incl. data quality); the coverage matrix is the traceability matrix; risk register per round | DRAFT-ENG-5 |
| SIG-ENG-039 | ADR index fields and superseded status; `check_spec_src.py` in `make docs-check` and CI | DRAFT-ENG-4; F-32 |
| SIG-ENG-004 | align the DoD with §8.3 → N/A-RATIONALE | F2a |
| SIG-INGEST-004; SIG-ONTO-060 | binding-version clause (NEW-7); scope list | F2a |
| §42.3 | physical ODbL table → export-boundary compartments; a share-alike compartment for RB-06b (B-33) | RISK-P4-07; B-33 |
| SIG-EXPORT-012, SIG-RECON-058 | drop ADR-092 compute-on-read (superseded by ADR-099/101) | F-34 |
| Appendix F | missing row for ADR-072 | APPENDIX-F-01 |
| SIG-EVAL-004 | **WAIVED for C0–C2 only** → ADR-153 (the operator's adopted sentence) | L3 §7; A-6 |
| SIG-IDENT-028; §55.9; SIG-EVAL-005/006/007 | census-driven auto-demotion for copy tiers; Round-11 disposition paragraph replacing the H4/P32.22a/H5/P32.23 path with T-EVAL-IND; owner re-home notes | L3 §7 |
| SIG-PUB-008 | stands; nobody is named; web gate default-deny; **the HG-11 second-reviewer role is WAIVED for Round-11 releases** (WV-03 → ADR-163) | A-4; A-23 |
| SIG-GOV-012/013/015 | **WAIVED (ADR):** interim individual legal home (WV-01 → ADR-165); interim single-maintainer editorial authority + public decision log (WV-02 → ADR-164) | A-23 |
| SIG-GOV-001/002 | **WAIVED for Round 11 (ADR-180):** e-mail-only intake; the site says senders disclose their address; no response time promised (B-8) | A-23 WV-05 |
| SIG-GOV-003 | **not waived, and in conflict with B-8** ("Email, no time promises"): the MUST requires published SLAs by category with privacy-harm and safety claims first. Flagged at S6, not resolved: it stays owed and is listed at GATE-ANNOUNCE until the operator waives it for Round 11 or approves SLA text (§14 R-31) | B-8; S6 flag |
| SIG-GOV-008 | **two-person authorisation WAIVED (ADR-181):** the operator alone authorises a true deletion, publicly logged with its reason; the tombstone clause stands; mechanism P37.71 | A-23 WV-06 |
| SIG-SEC-003 | demand-response posture + published counts; canary declined | A-4 |
| SIG-LIC-004/009 + HG-03 text | the rights basis the operator states (GL-GATE-07 re-confirmed; express-terms rows accepted; new NC sources facts-only; non-US DB-right flips); **LIC-009's counsel-referral clause WAIVED (WV-07 → ADR-182)**; its risk-register clause stands (R-19, R-20) | A-4; A-7…A-9; B-34; A-23 |
| SIG-INGEST-036 (§26), SIG-INGEST-037, SIG-INGEST-046c | robots per GL-GATE-08 as re-confirmed (A-5; rule 2 already records `robots_disregarded`); rule 7 opt-out register; 046c reservation refusal built; **INGEST-037's counsel clause WAIVED (WV-07)** and the terms-conflicted fetching recorded by ADR-184; **rule 6 ("ask first" for small civil-society projects) is not waived and conflicts with fetching DocumentCloud/MuckRock without contact under U-011 — flagged, not resolved (§14 R-18; S6 note §6)** | A-5; A-17; B-39; A-23 |
| SIG-CONTRIB-012/012a/013/030a, SIG-GOV-024, SIG-CHART-033 | outreach timing: owed later-phase obligation, trigger "operator authorises outside contact" | Q-E2-12 a; U-011 |
| SIG-CHART-025 | **amended:** US-nationwide multi-vendor/multi-technology breadth with per-class and per-geography quality labels | A-17 (Q-E2-22 a) |
| SIG-UI-042 | **release block WAIVED (WV-04 → ADR-179):** releases ship with the hostile-reader review recorded "not yet performed" and findings listed as known issues | A-23 |
| SIG-UI-036, SIG-UI-050 (+ `AGENTS.md` gotcha 6, `web/AGENTS.md` gotcha 1) | zero-JS-on-content-pages → HTML-first page types (K0 §7 text; ADR-155) | A-12 |
| SIG-GOV-017 | **not amended, not waived.** The approved "My location" control (D-K1-7) is built only as a map-pan control after a written GOV-017 analysis (P37.72); a failing analysis returns the question to the operator | B-44 |
| SIG-PUB-002/003/003a | **not amended.** Applied before persistence in the Axon Connect and Flock portal connectors (P36.74, P36.76) | B-35; A-17 |
| SIG-UI-044 | chrome wording budget | D-K14-6 (B-22) |
| SIG-METRIC-007, SIG-EVID-009, SIG-UI-035, SIG-EXPORT-002 | transparency amendments | J3 §11 |
| §55 landed-status text; Appendix G | true dates for the Round-10 events (B1 §5.3) via one new App-G row; sqitch L44–52 never re-stamped (C-10) | B1; C-10; ADR in §7 |

### 6.4 Verdict vocabulary (B-5; F2b §2; applied by T4)

`MET` · `MET-DIFFERENTLY(ADR|RISK)` · **`MET-ENGINEERED(D-id…)`** (engineering done; a live, operator or human leg owed in
an OPEN/PARTIAL DEFERRALS row) · `PARTIAL` · `MISSING` · `AT-RISK-INTEGRATION` · **`WAIVED(ADR)`** (operator's words,
risk accepted, compensating controls, revisit trigger) · `N/A-RATIONALE`. Four additive matrix columns:
`required_domain`, `achieved_domain`, `owed_legs`, `accepted_scope`. `check_coverage_matrix.py` enforces the grammar and
the cross-checks (no MET with an owed leg; MET-ENGINEERED only with an open leg; WAIVED only with an accepted ADR and no
open leg; routing to a landed ticket is an error; expected counts derived from the spec, no pinned 715). Every verdict
change is written as a `coverage-assessment/1` event. Acceptance packets report the **two-sum headline** per status
layer (MEM-10's contract), never "N MET" alone. ACCEPT-R10's "34 MET" stands as history, superseded by these
re-verdicts (C-13).

### 6.5 Waivers adopted at GATE-P — and what is deliberately *not* waived

A spec amendment that removes or weakens a MUST **is a waiver** (T4 adds this rule to the S1b checker). Every waiver
below was adopted by the operator selecting the agent-drafted sentence shown (labelled "agent-drafted, adopted by the
operator", 2026-10-01T04:03:25Z for A-6 and 04:28:49Z for A-23), and becomes `WAIVED(ADR-nnn)` with compensating controls
and a revisit trigger. GATE-ANNOUNCE's "spec MUSTs unmet at launch" list now holds only items owed for other reasons.

| waived | adopted sentence (abridged; full text in the log) | ADR | compensating controls | revisit trigger |
|---|---|---|---|---|
| SIG-EVAL-004 lower bound, **C0–C2 only** (A-6) | "I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 …" | 153 | census-verified copies only; inferential matches published as possible duplicates with intervals; no certification claim | T-EVAL-IND; a proposal to auto-write an inferential tier; GQ-23 failing twice in a quarter |
| SIG-GOV-012/013 legal home + defence before launch (WV-01) | "… SIG's legal home is me as an individual, disclosed on the site …" | 165 | disclosure on About/terms; public legal-defence resources listed | announcement, a first legal demand, funding or a second maintainer |
| SIG-GOV-015 editorial board (WV-02) | "… interim single-maintainer editorial authority, and every naming/sensitivity decision goes in a public decision log." | 164 | P37.7 decision log; officer-naming gate default-deny (P35.28) | a second maintainer or a naming decision contested publicly |
| SIG-PUB-008 / HG-11 second reviewer (WV-03) | "… each readout states 'single maintainer, no second reviewer'." | 163 | the sentence in every Class S readout; nobody named | a second reviewer becomes available (T-EVAL-IND) |
| SIG-UI-042 release block (WV-04) | "… hostile-reader review recorded truthfully as 'not yet performed' and any findings listed as known issues." | 179 | `/editorial-standards/` says "not yet performed"; known-issues page | a hostile reader becomes available; GATE-ANNOUNCE |
| SIG-GOV-001/002 one-click, unidentified intake (WV-05) | "… corrections come by e-mail, and the site says plainly that senders disclose their address." | 180 | the notice text; no response time promised (B-8); Part VIII takedowns honoured by the operator | announcement; a privacy-harm report |
| SIG-GOV-008 two-person deletion (WV-06; operator chose it over "keep owed") | "I alone may authorise a deletion, publicly logged with its reason." | 181 | P37.71: in-ticket go only, never OM-20, never agent-initiated; public log + tombstone; audit record kept | a second maintainer; any contested deletion |
| counsel clauses of SIG-LIC-009 and SIG-INGEST-037 (WV-07) | "… rights decisions rest on my recorded determinations, labelled as such." | 182 | E2's label text on every artifact; LIC-009 risk-register clause kept | counsel obtained (LATER-05); a first legal demand |

- **One risk row closes by ADR:** RISK-P0-06 via the collection-conduct ADR (ADR-168) restating SIG-INGEST-037's legal
  posture in the operator's A-5 words.
- **Not waived; stay owed with a trigger:** SIG-EVAL-001/002/005/007 and SIG-IDENT-027/028's independent legs, SIG-DOS-002's
  independent checks (T-EVAL-IND); SIG-UI-001 usability (LATER-02); SIG-CONTRIB-012/012a/013, SIG-GOV-024, SIG-CHART-033
  (LATER-04); D-R10-HUMAN-1 and D-P30.2b-1 (T-EVAL-IND). **Not waived and binding on the operator's new choices:**
  SIG-GOV-017 ("My location", P37.72), SIG-PUB-002/003/003a (Axon Connect and Flock portals), SIG-INGEST-036 rule 6
  (DocumentCloud/MuckRock — the open contradiction in §14 R-18), SIG-GOV-003's published SLAs (the open
  contradiction with B-8, §14 R-31) and SIG-INGEST-046c (reservations refused; whether any express-terms row's captured
  licence metadata is itself a machine-readable reservation is open — §14 R-19).

### 6.6 Coverage re-verdicts T4 applies (summary)

- **F2b (55 gated/reduced-scope ids):** 12 MET → MET-ENGINEERED (TRUST-004/007/008/009/010, FIND-006/007, DOS-002…005,
  ACQ-004); EVAL-003/004 and PUB-008 → AT-RISK-INTEGRATION (then superseded by L3: EVAL-003 → MET, EVAL-004 → WAIVED
  scoped); GOV-022, EVID-019 → MET-ENGINEERED; GOV-013/015 → WAIVED(ADR-165/164) (WV-01/02); the outreach five → owed later-phase (not WAIVED).
  The 14 MET-ENGINEERED verdicts need their D-rows opened first.
- **F2a (49 engineering/"claimed" ids):** UI-010, EPIS-018, INGEST-046b, ONTO-054, INGEST-007, STORE-013, ENG-034 → MET;
  UI-040 → MET-DIFFERENTLY(ADR-108; ADR-133); GEO-007, ENG-004 → N/A-RATIONALE; 30+ PARTIAL with a concrete test/build home.
- **L3:** EVAL-001 → MET-ENGINEERED; EVAL-003, EVAL-006 → MET (after CONF-09/12); EVAL-002 PARTIAL; EVAL-005/007 MISSING
  (owed); IDENT-030 MET by abstention; EPIS-029 and RECON-018 → MET when GQ-11/12 pass live.
- **61 unsampled boilerplate MET-DIFFERENTLY rows** are re-verdicted row by row in **P34.48** (11A; moved out of SEED-14
  because it is investigation, not transcription — FEA-01; their true state is unknown until then, F-238).

---

## 7. ADR list (from ADR-146; numbers provisional — assigned in ratification order; each carries `## Revisit trigger`)

Landed ADR bodies are never edited (CF-02; SIG-ENG-003). A superseded ADR gets only an appended `Superseded by ADR-nnn
(<date -u>)` status line; **an ADR that a new ADR amends, qualifies or extends gets an appended `Amended by` / `Qualified by`
/ `Extended by ADR-nnn (<date -u>)` status line** (COV-14). Every Part-A line was answered, so every ADR that S4c marked †
(conditional) now exists. **One owner per ADR (FEA-06, COV-08):** the *author* column is either SEED-11 (decisions that
record a GATE-P answer or bind the whole round; written in Stage B) or the chain row that implements the decision
(engineering ADRs, which quote the GATE-P answer verbatim where an S5 line is involved). An ADR that records adopted
words stores the text as logged with its sha256 and the label *"agent-drafted, adopted by the operator at <time>"*.

| # (prov.) | author | title | one-line decision | S5 line | source |
|---|---|---|---|---|---|
| 146 | SEED-11 | Correcting recorded dates that were not taken from a clock | truth source = `date -u`; corrections append-only via one register and this ADR (no footers on landed ADRs); sqitch lines L44–52 never edited — a local DB holds them as stamped (C-10); candidate `p-17b713` superseded; restored rows annotated (SEED-06); a CI guard rejects new future-dated records | A-13, B-4, C-10 | B1 §8 (amended by CF-02) |
| 147 | SEED-11 | Gate-record integrity and readout authorship | verbatim operator words; adopted agent drafts labelled and sha256-recorded; no proxy signatures; hedged words are not decisions (forward rule); the GATE-P record and its two gaps closed from git (§1.3); ACCEPT-R8/R10 and GATE-G3 annotated with B7's facts; C-1 confirmed; C-13 superseded | A-16, B-4, C-1, C-3, C-13 | E2-17/18/X1; B2; B5 OM-07…09 |
| 148 | SEED-11 | Build memory v2.1: ledger contract and enforced append-only | ≤ 12 KiB head, value-only CURRENT STATE with `harness:`; guard core in CI; D-R10-MEMORY-1 split (option C) superseding ADR-126/127's cutover statements; closeout journal stays shadow | A-13 | B3, B4 |
| 149 | SEED-11 | Round-11 operating model | **Devin Desktop, `swe-2-high` (256k), for every row; no in-round second harness; post-round Claude Code (Opus 5.5, xhigh) deep review**; pauses = HG gates, one ING-GO per wave, spend above the ceiling, red CI, mutations off an approved OM-20 list; one digest per wave with a spend line; agent usage reported, pause at any usage-limit event (A-2); OM-19 + OM-20 with the 11A list (S5-3); **live API answers may change before HG-11, labelled (A-20)**; the operator's name stays commit author, trailers CI-enforced (A-21) | A-2, A-15, A-20, A-21, S5-1/2/3 | B5 §6; S2 §3 |
| 150 | SEED-11 | Coverage verdict vocabulary | MET-ENGINEERED and WAIVED(ADR), four columns, checker cross-checks; "an amendment that weakens a MUST is a waiver"; ACCEPT-R10 superseded by the re-verdicts | B-5, C-13 | F2b §2 |
| 151 | **P34.1** | Toolchain pin and CI truth | Node 24 LTS, uv pin, `ubuntu-24.04`; head-bound check-runs; flake allow-list (one re-run); CI-unavailable needs a verbatim waiver; tests assert invariants | B-15 | H2; CF-01 |
| 152 | SEED-11 | Confidence without independent review | confidence by construction + mechanical suite; agent evidence never gates; **no human check this round — every Class S readout and `/quality/` say "no human check performed"**; independent evaluation owed under T-EVAL-IND (D-R10-HUMAN-1, D-P30.2b-1); rows 184–187 superseded | A-6, B-31 | ADR-L3-A |
| 153 | SEED-11 | Derivation, not identity | ruleset v3: auto-collapse only C0–C2 copies (C2 enabled, B-31), census-verified; possible duplicates with intervals; **SIG-EVAL-004 WAIVED for C0–C2 in the operator's adopted sentence**; supersedes ADR-105 §5, amends ADR-099 §3 | A-6, B-31 | ADR-L3-B |
| 154 | SEED-11 | Graph-quality suite as a ratcheted release gate | 27 checks, enforce/ratchet/report; V15 = 0 ratchet regressions + 0 enforce failures (FEA-11); loosening a baseline needs a new ADR | A-6 | ADR-L3-C |
| 155 | SEED-11 | HTML-first page types | T0/T1/T2/T3 registry with CI budgets; supersedes the named-island rule of ADR-091 §3–4 and ADR-097 §2–3/§6, extends ADR-134, leaves ADR-068 (`/curate/**`) unchanged (K0 §6) | A-12 | K0 §6 |
| 156 | **P35.52** | Public map v2 | self-hosted OSM basemap on R2 (A-3); count-conserving overlay tiles; Natural Earth place names; single-source sites shown (D-K1-6) | (answered) + B-23, B-44 | K1 MAP-00 |
| 157 | **P36.27** | Static figure kit and dossier visualisations | one server-side figure kit; inline SVG; downloadable SVGs under their own policy | B-22 | K6; K13 |
| 158 | SEED-11 | Graph exploration as aggregated overviews | overviews ≤ 3,000 nodes + egos + `/explore/`; descriptive only; incl. the state × state Flock-sharing overview from share-list claims | A-11, A-22 | K0, K2, K13 |
| 159 | SEED-11 | Organisation publication | **registry auto-allow** (Census of Governments, SAM UEI, Wikidata QID; person-name screen always runs; basis shown) + a typed "not yet reviewed" state for every other organisation; **no operator review queue**; legacy org keys folded in (D-P32.3-1); extends ADR-124 | A-10, B-18 | K2 D-K2-1 |
| 160 | **P35.17** | Structured jurisdiction scheme and placement | ISO 3166-2 registry, boundary pack (flipped by the operator, A-18), `lookup@1`/`placement@1`; `unresolved` is a report; revisits ADR-079/122 | A-18 | K4; F5 PKG-06 |
| 161 | **P35.12** | Release model v2 | content-addressed identity + `sig-YYYY-MM-DD.N`; descriptor v2; Class R/S with the **standing go in the operator's adopted words**, expiring at the next sub-round GATE or 30 days and renewed at each GATE; cadence with suppression; 15-min withdrawal; pipeline signing key; operator-only tags | B-9, B-10, B-20 | G3 |
| 162 | SEED-11 | Transparency and distribution | export-time static artifacts; source-keyed rights lanes; fail-closed scrub; status lane; zero-egress R2 host with $50 ceiling, R2 operations ceiling and kill switch; raw bytes for raw-ok sources only; `/s/<pub>/` snapshots | A-3, B-19 | J3; J4 |
| 163 | SEED-11 | Single-maintainer publication posture | SIG-PUB-008 stands; nobody named; gate default-deny; **the second-reviewer role WAIVED (WV-03)** | A-4, A-23 | E2-01 |
| 164 | SEED-11 | Interim editorial authority and public decision log | disclosed; **GOV-015 WAIVED (WV-02)**; the log also records every WV-06 deletion | A-4, A-23 | E2-03 |
| 165 | SEED-11 | Interim legal home | individual, disclosed; **GOV-012/013 WAIVED (WV-01)**; revisit at announcement, a first legal demand, funding or a second maintainer | A-4, A-23 | E2-04 |
| 166 | SEED-11 | Legal-demand posture | written posture + published counts; canary declined | A-4 | E2-10 |
| 167 | SEED-11 | Counsel basis | past "counsel" determinations re-recorded as **the operator's own determinations (no counsel)**, with the C-3 sentence; E2's label text (confirmed verbatim) in every artifact; qualifies ADR-086/106 | A-4, C-3 | E2-05; U-013 |
| 168 | SEED-11 | Collection conduct | **GL-GATE-08 re-confirmed as is** in the adopted option text (disallows disregarded, disclosed as host + count); rule-7 opt-out register; 046c reservation refusal; UA/contact to surveillancegraph.org, `sig-project.org` not bought; extends ADR-088 | A-5, B-6 | E2-06/07/08 |
| 169 | SEED-11 | Rights basis with guardrails | **GL-GATE-07 re-confirmed in the operator's adopted words** (Tier-1 batch-wide flips); new NC sources facts-only (A-9); non-US DB-right flips N1–N21 (B-34); RB-06b share-alike, RB-08 territories = US (B-33); IU terms captured then decided; E4 R-lines as answered; flips executed by the operator per wave | A-4, A-7…A-9, B-33…B-41 | E2-11; I7 |
| 170 | SEED-11 | ODbL map basis | ADR-106's basis recorded as **the operator's own determination (no counsel, no document)**; per-compartment map kept | A-4 | E2-13 |
| 171 | SEED-11 | Outreach timing | outreach, records-request sending, recruiting, contribution-back → owed later-phase, trigger "operator authorises outside contact" | B-6 | E2-09; U-011 |
| 172 | SEED-11 | Product direction and scope | D3 ratified with **D3-Q3 = b (vendor-hosted public pages fetched)**; CHART-025 amended; co-primary journeys; D3 §5 announce gate; tagline *"Public surveillance, traced to the documents."* | A-17, C-4 | D3; E2-20 |
| 173 | SEED-11 | Acquisition waves and capacity | one ING-GO per wave + the operator's flip list; **US-first ordering with non-US kept**; cap 40 GB, pre-grow, temporary tier bumps; Wave D in scope; US + AU keys after the alias | B-11, B-18, S5-4 | I8 §7 |
| 174 | **P35.1a** | Scheduler of record | Cloud Scheduler + daily live-diff + cron lint; scheduler consolidation (B-13, in P35.1b); GitHub `reingest` retired; supersedes ADR-016's scheduler clause and ADR-076's scheduling path | B-13 | G1-09; OPS-03 |
| 175 | **P34.6** | Production data protection and restore drills | deletion protection, retain-on-delete, quarterly drill at scale, monthly logical export; qualifies ADR-081 | A-1 | G1-03/04 |
| 176 | **P36.13** | API exposure posture | enforced rate limits (search 30/min); no Cloud Armor now | B-30 | OPS-06 |
| 177 | **P37.3** | Evidence retention | 365-day unlocked retention (takedowns and WV-06 deletions stay possible); writers cannot delete | B-14 | G1-RET; COV-14 |
| 178 | **P34.18** | Public identifier re-key | personal-handle ids renamed with a restricted old→new map and append-only aliases; "identifier changed" pages; the correction note discloses the retained git history | B-3, A-0 | DR-C6-01; COV-14 |
| 179 | SEED-11 | **WV-04 — SIG-UI-042 release block waived** | releases ship with the hostile-reader review recorded "not yet performed" and findings as known issues | A-23 | S1c WV-04 |
| 180 | SEED-11 | **WV-05 — e-mail-only intake** | GOV-001/002 waived for Round 11; the site says senders disclose their address; no response time promised | A-23, B-8 | S1c WV-05 |
| 181 | SEED-11 | **WV-06 — single-operator true deletion** | the operator alone authorises, publicly logged with its reason; tombstone (category + date); never OM-20; never agent-initiated; mechanism P37.71 keeps the audit record | A-23 | S1c WV-06; SIG-GOV-008 |
| 182 | SEED-11 | **WV-07 — counsel-review clauses waived** | LIC-009/INGEST-037 counsel clauses waived; rights decisions rest on the operator's recorded determinations, labelled; LIC-009's risk-register clause kept | A-23 | S1c WV-07; E2-05 |
| 183 | SEED-11 | **Express-terms acceptance** | the operator's adopted sentence (A-8); ≈8,088 rows stay public; captured terms + basis disclosed on pages and in files; withdrawal on a rights-holder objection | A-8, A-9 | J4 NEW-1; I7-C1 |
| 184 | SEED-11 | **Terms-conflicted public pages: fetch envelope** | Flock portals, Axon Connect, DocumentCloud/MuckRock, Sourcewell/OMNIA fetched despite anti-automation terms inside the envelope (public pages only; no logins, keys or circumvention; rate-limited; terms captured; exposure disclosed; Part VIII screen); records the INGEST-037 deviation (counsel clause waived) and the open INGEST-036 rule-6 conflict | A-17, B-35, B-39, B-41 | D3; I7-C2/C3/C4 |
| 185 | SEED-11 | **Part VIII screened lanes without a human clear** | S1–S9 screened lanes incl. S8 tribal; the agent clears dossier families (disclosed); B-44's Part VIII rows; SIG-PUB-002 applied before persistence | B-32, B-35, B-42, B-44 | I7 S-lines; E4-B2 |

**Also at T1 (records, not new decisions):** appended status lines on ADR-015, ADR-016 (scheduler clause, by ADR-174),
ADR-058 §3, ADR-075, ADR-092, ADR-096 §1, ADR-086/106 (`Qualified by ADR-167`), ADR-081 (`Qualified by ADR-175`),
ADR-088 (`Extended by ADR-168`), ADR-099 §3 (`Amended by ADR-153`), ADR-124 (`Extended by ADR-159`), ADR-132 (`Extended by
ADR-161`), ADR-134 (`Extended by ADR-155`), ADR-091 §3–4 and ADR-097 §2–3/§6 (`Superseded by ADR-155`), ADR-079/122
(`Revisited by ADR-160`), and every ADR superseded above; recorded evaluations of the fired revisit triggers (F3 §5.1);
`ADR_TRIGGERS.csv` (SEED-15) with one row per revisit trigger, **including Q-29's operator-accepted-risk revisit and the
seven waiver triggers** (COV-14). Ticket-authored ADRs append their own status lines in the same PR. **SEED-11 writes 30
ADRs (146–150, 152–155, 158, 159, 162–173, 179–185); ten move to their owning tickets** (FEA-01, FEA-06).

---

## 8. Ticket plan (`data/round11_plan.csv` is authoritative; 385 rows: 309 chain rows, 4 markers, 20 seed, 19 operator, 20 later, 1 post-round review, 12 dropped/moved/done)

The CSV is post-split and carries `uses`, `leg_runs` and `live_legs` (COV-13, FEA-04/05). S6 kept every id (rows only
renumbered): new rows got new ids in the scheme (P36.74–P36.79, P37.69a/b–P37.72, OP-25, OP-26, REVIEW-R11), each with a
`notes` entry "S6: …"; dropped, moved and done units stay as rows with `kind` = `dropped` / `moved` / `done` so every
reference still resolves (no chain row depends on one). Every `operator_gate` cell now states the GATE-P answer instead
of a default. Final ids are assigned by T3 (11A) and the PLAN rows (11B–11D). Every number below is regenerated from the
CSV by the S4c ordering check, re-run at S6 (`docs/build/logs/next-phase/S4c/check_order.py`: 0 errors).

### 8.1 Shape and counts

| sub-round | rows | kinds | eng. runs (PLAN) | leg runs | prod./publish rows | OM-20 rows | never-pre-authorised in-ticket pauses |
|---|---|---|---:|---:|---:|---:|---|
| 11A P34 | 201–259 (59) | 56 tickets, PLAN-11B, acceptance P34.47, GATE-G4 | 56.0 (7.0) | 8.5 | 23 | 13, all **pre-authorised** (S5-3) | P34.17, P34.21b (two gos: bucket access, republish #2), P34.46 · plus in-ticket gos for named mutations not on the S5-3 list: P34.18, P34.24a, P34.44a |
| 11B P35 | 260–342 (83) | 80 tickets, PLAN-11C, acceptance P35.64, GATE-G5 | 81.0 (7.0) | 11.0 | 26 | 19 | P35.57, P35.11*, P35.14b, P36.12*, P35.61, P35.63 · plus the operator's HG-03 flip at P35.17 (OP-26) |
| 11C P36 | 343–419 (77) | 74 tickets, PLAN-11D, acceptance P36.73, GATE-G6 | 72.5 (6.0) | 4.0 | 19 | 10 | P37.2 (tier bump), P36.38, P36.72b · P36.70 only if the Class R standing go has lapsed |
| 11D P37 | 420–499 (80) | 76 tickets incl. 1 conditional (P37.59, dark; 1.0 run), CAP-01 P37.68a–d | 69.0 | 5.0 | 33 | 15 | P37.16a, P37.16b, P37.20, P37.36, P37.42, P37.55, P37.65b · P37.72 only if its GOV-017 analysis fails |
| tail P38 | 500–509 (10) | CAP.1 a/b, CAP.3, GATE-ACCEPT-R11, REC a/b/c, DOC, CAP-02, GATE-ANNOUNCE | 7.0 | — | — | — | the two gates |
| **total** | **309** | ticket 286 · plan 3 · capstone 11 · gate 5 · reconcile 3 · docs 1 · **HUMAN 0** | **285.5 (20.0)** | **28.5** | **101** | **57** | **19** (+2 conditional) + 5 gate markers |
| post-round | — | REVIEW-R11 (Claude Code; not a chain row) | ≈ 8 | — | — | — | — |

\* in-ticket only if ING-GO-A / ING-GO-B are not given in the G4 sitting. With OM-19, a pause queues a leg; the chain
continues unless a later row needs the leg's live result (`live:`). The 11B–11D OM-20 rows are pre-authorised only if the
operator approves a list naming them at GATE-G4/G5/G6; otherwise each is an in-ticket pause.

**Re-split rule** (S2 §3.2, made precise at S4c): a sub-round whose *engineering* rows exceed 85 or whose engineering runs
exceed 75 (PLAN fan-outs and leg re-runs excluded) becomes two phases with an extra GATE. After S6: 11A 58 rows / 49.0
runs; **11B 82 / 74.0 — still at the edge** (P34.45 left for 11A and P35.49 was dropped, which paid for the Flock portal
connector P36.74); 11C 76 / 66.5; 11D 80 / 69.0. If PLAN-11B's sizing review adds splits that push 11B over, the rule
fires and 11B splits at the Wave-B activation boundary with an extra **GATE-G4b** (FEA-04).

### 8.2 Contents in order (rows; details in §5)

- **11A:** CI first (P34.1–2) → production safety: data protection, alerts incl. the TLS-expiry alert, budget alert +
  billing export, restore drill (P34.3–6; the deferred A-1/A-2a items) → DNS runbook (P34.50) → memory guards M1/M3/M2
  (P34.7–9) → publish path (P34.10) → W0 copy (P34.11–15) → repo honesty (P34.16) → express-terms disclosure (P34.19) →
  **republish #1** (P34.17: `/visual-language/` and handle-bearing pages removed) → re-key incl. the repo-tip strings,
  evidence empty states (P34.18, P34.20) → **attribution backfill + bucket-tree access removal + republish #2**
  (P34.21a/b) → date truth, versioning (P34.22a/b–23) → sqitch hygiene (P34.24a) → API honesty + basis label (P34.25) →
  clone rehearsal of the exact tip (P34.24b) → allow tooling (P34.26) → memory M4–M10 incl. the G4c signature check
  (P34.27–33) → **PLAN-11B** → 61-row re-verdict (P34.48) → C4 blockers (P34.34a/b–38) → replay read-back (P34.39a) +
  first-fire leg (P34.39b) → serving topology dark (P34.40–41) → identities, execution host (P34.42a/b–43) → Part VIII
  at-rest audit (P34.49) → quality baseline (P34.44a/b) → **honest-posture ER re-run (P34.45; A-20 = a)** → **Round-10
  schema + allows + API** (P34.46) → P34.47 → GATE-G4.
- **11B:** API release parity (P35.57; an improvement, no longer a gate) → zero-egress host (P35.5) + post-DNS probe
  (P35.67) → scheduler lint (P35.1a) → Wave A (P35.6–11) → typing (P35.14a/b–15a/b) → **Wave B code** (P36.1a,
  P36.3–P36.11) → officer-naming gate, redaction, residential demotion (P35.28, P36.15, P35.66) → **direct Flock portal
  connector (P36.74)** → **Wave B activation queued** (P36.12) → fleet hygiene + scheduler consolidation, probes, runbook
  (P35.1b, P35.3–4) → release identity (P35.12–13) → geometry and placement incl. the boundary flips (P35.16–19) → numbers
  (P35.20a/b) → identity core (P35.22, P35.24–27) → labels and `/network/` (P35.29–30) → transparency exports (P35.31–35) →
  `withBase()` helper (P35.65) → provenance and citations (P35.36–42) → watch producer, dossier contributions, dossiers at
  every level (P35.43–45) → **dedup** (P35.46–47) → agent review lane (P35.48) → page registry, budgets, tiles (P35.50–52) →
  release pipeline (P35.53–56, P35.58–60) → G2 steps 2–3 (P35.61–62) → **PLAN-11C** → **first model release** (P35.63) →
  P35.64 → GATE-G5.
- **11C:** **Wave C code + activation queued** (P37.1–2; non-US kept) → moved-in ops/source rows (P35.2, P35.21, P35.23,
  P36.1b, P36.2 incl. terms capture) → **Axon Connect, DocumentCloud and Sourcewell/OMNIA connectors** (P36.76–78) → rate
  limits (P36.13) → L4 marker (P36.14) → design system + IA kit + figure kit + identifiers (P36.16–30) → **agent-written
  held-out search set** (P36.79) → search v2, basemap, grouped index, map, entity pages A + Organizations (P36.31–42b) →
  **Flock share-list claims** (P36.75) → status lane, cadence (P36.43–44) → Sources & data (P36.45–51) → dossier sources
  explorer, downloads, template v2 (P36.52–57) → watch, evidence, research queue (P36.58–63) → Home/About/onboarding
  (P36.64–65) → snapshots (P36.66a/b) and changes (P36.67) → per-source versions (P36.68–69) → search activation (P36.71) →
  **core-surfaces release ACC-PLACES, carrying Wave B's data** (P36.72a/b) → second-release acceptance (P36.70) →
  **PLAN-11D** → P36.73 → GATE-G6.
- **11D:** evidence store, security baseline, ingestion hardening (P37.3–5b) → governance pages and rights hygiene
  (P37.6–8) → **single-operator deletion path** (P37.71) → lifecycle, promotion gate (P37.9–10) → source-ops tail incl.
  keyed US 511 and **AU QLDTraffic/NSW** (P37.11–12, P37.70, P37.13–15) → dossier live captures (P37.16a/b) → map work incl.
  **"My location"** (P37.17–18, P37.72, P37.19–20) → access, entity pages B, overviews incl. the Flock-sharing overview,
  explorer (P37.21–27) → dossier networks, in-place map (P37.28–29) → watch (P37.30–34) → queue campaigns (P37.35) → raw
  archive, claim viewer v2 (P37.36–37) → disagreements, quality basis, changes, API parity, search export (P37.38–43) →
  mechanical evaluation, `/quality/`, organisation identity (P37.44–46b) → **Wave D** (P37.47–53, **P37.69a/b**,
  activation P37.54) → deposits, WACZ (P37.55–56) → projection rebuild, schema conformance (P37.57a/b–58) → intake
  dark/conditional (P37.59) → visual regression, T1 enhancements, contribution path (P37.60–62) → map and explore
  acceptance (P37.63–64) → **final release TX-16** (P37.65a/b) → coverage closeout, Stream-L re-measure (P37.66–67) →
  **CAP-01 journeys** (P37.68a–d).
- **Tail:** §13. **Post-round:** REVIEW-R11 (§13.4).

### 8.3 Gates, pauses and operator touchpoints

- **Five gate markers:** GATE-G4 (row 259), GATE-G5 (342), GATE-G6 (419), GATE-ACCEPT-R11 (503), GATE-ANNOUNCE (509).
  HUMAN-H6…H8 stay reserved for the T-EVAL-IND segment. Each check-in GATE follows its acceptance row; the packet is
  S5-2's (`continue` answers only batch lines). After GATE-P a packet carries only what the rows raise: ING-GOs, the
  wave's HG-03 flip list (OP-26), the next sub-round's OM-20 list, the Class R standing-go renewal (B-9), the spend report.
- **Nineteen never-pre-authorised in-ticket pauses** (§8.1) plus two conditional ones and the three 11A in-ticket gos
  for mutations not on the S5-3 list. The operator's touchpoints are listed by date in §11.2 (≈ 21 plus the wave digests, eight synchronous).
- **HG-03 / ING-GO lines:** ING-GO-A **and ING-GO-B** with the Wave A/B flip lists at GATE-G4 (FEA-02); ING-GO-C with the
  Wave-C list at GATE-G5; ING-GO-D with the Wave-D list (N1–N21, ACQ-23a/b, DocumentCloud, Sourcewell/OMNIA, Axon Connect,
  RB-06b, RB-08) at GATE-G6; the A-18 boundary flip inside P35.17. A row whose flip has not been executed lands with
  `ingestion_permitted=false` and activation skips it.

### 8.4 Live stages and calendar windows (S2 §5.1 as revised; UTC)

| window | event | constraint on the plan |
|---|---|---|
| 10-01 → 10-21 (06:09Z), peel-on 10-29T12:00Z | 32–33 first fires of existing triggers (S2/I8 say 32; S3 said 33 — FEA-13) | P34.39b reads them back as a **non-blocking** monitoring leg; no Track-0 drill or TLS alert precedes them (A-1) |
| **10-06 00:00Z → 10-13 12:00Z** | AR-3 batch window; **10-10 03:35Z** OSM replay | no hosted DB write, schema change or job roll; republishes and bucket-IAM legs allowed outside 03:00–10:00Z; PLAN-11B runs here |
| ≥ 10-10 after the replay | D-P31.4-1 read-back (P34.39a) | prerequisite of P34.46 |
| **≥ 10-14 14:00Z** | Round-10 schema deploy (P34.46) + 48 h soak | gates P35.11 and P35.61 |
| **before 10-19 00:00Z** | `ubuntu-latest` → Ubuntu 26 (GitHub runner notice) | P34.1 must have landed, else the seed PR pins `ubuntu-24.04` |
| **10-19 → 10-23**, 14:00–20:00Z | Wave A legs (P35.11) | ING-GO-A at G4; widened existing triggers paused for the wave or the roll after legistar's 10-20T05:00Z fire (FEA-14) |
| **10-26 → 11-05**, one family/day | Wave B legs (P36.12, incl. the Flock portal family) | ING-GO-B + flip list at G4; no release cut; data publishes in P36.72b |
| **11-06 → 11-13 12:00Z** | AR-3 | no release cut; P36.72b ≥ 11-13 12:00Z |
| 11-16 (Mon) 14:00Z | first weekday cadence slot | suppressed after P36.72b's Class S promotion (≤ 14 days) |
| **11-16 → 11-20** | Wave C legs (P37.2, dispatched in 11C; non-US objects included) | ING-GO-C at G5; tier-bump go when the leg is due; Wave-B r11 crons paused |
| ≈ 11-22 | managed-cert renewal read (P35.67 leg 2; cert expires 12-22) | alert on failure |
| **11-23 → 12-04, 12-14 → 12-18** | Wave D (P37.54; incl. ACQ-23a/b, Axon Connect, DocumentCloud, Sourcewell/OMNIA) | ≈ 12 family-days in ≈ 13 weekdays (tight); second-window sources ship in the 2027-01-15 cut |
| **12-06 → 12-13 12:00Z** | AR-3 | P37.65a/b cut before 12-06 or after 12-13 12:00Z |
| 12-15 (Tue) | cadence slot | suppressed if P37.65b promoted on or after 12-01 |

Tokens in `window_constraints`: **AR-2** on-demand backup + pre-state capture before any hosted write (and a bucket
pre-copy or versioned restore point before any bucket write; FEA-07); **AR-3** none of the three windows, never
03:00–06:30Z daily, preferred 14:00–20:00Z weekdays; **AR-4** clock-guarded read-backs; **PUB** republishes outside
03:00–10:00Z. Engineering runs ahead of the windows; windowed legs wait in the OM-19 queue and run from the leg-runner
backstop when the chain is not moving (FEA-05).

### 8.5 Sizing for Devin Desktop's 256k window, and what Stage B writes

- **The context ceiling (A-15).** Every row runs in Devin Desktop with `swe-2-high` and a **256k-token window**. A
  ticket's Load list plus its expected working set (code read, test output, CI logs) must fit with headroom: **target ≤
  ~150k tokens loaded**. `dispatchTarget` in CURRENT STATE (T5) records this; S = 0.5, M = 1.0 run; no chain row exceeds
  1.0 run except the explicit fan-outs (PLAN-11B 7.0, PLAN-11C 7.0, PLAN-11D 6.0, P34.48 1.5), each executed as ≤ 1-run
  contexts with named seams. Nothing here is measured yet: T3 measures each 11A contract's Load list with a token count,
  and each PLAN row's Phase-4 review does so for its sub-round.
- **Rows that look oversized — split at T3 (11A) or at the PLAN row's sizing review:** P34.46 (sqitch L44–52 + allows +
  API roll + go/no-go protocol), P35.61 (hosted audit + bounded apply + freeze), P35.63 (first model release; 21
  prerequisites), P36.12 (Wave B activation, ten family legs), P36.72a (crawl, parity and number truth over 13
  prerequisites), P37.65a (final cut + live crawl + scrub audit), P37.68d (every per-ask check, ROUTES.csv, budgets, axe,
  cost), P38.1a/P38.1b (whole-round gap analysis) and P38.3b (spec reconciliation); also watch P35.1b (fleet hygiene +
  scheduler consolidation) and P36.2 (rights batch + terms capture), whose scopes grew at S6, and the seed units SEED-11/12/13.
  Splitting them is expected to add ≈ 10–20 contexts (§10.4).
- **Splits already in the CSV (FEA-04):** the 16 S3 L rows and the nine rows S4 found too big plus P34.39 a/b (FEA-03).
- **Multi-leg rows (FEA-04/05):** every row with a window, an in-ticket go or a ride on a later release carries its leg
  structure in `live_legs` and its re-run cost in `leg_runs` (e.g. P34.21b "2: bucket-access removal | republish #2",
  P35.61 "3: audit + plan | operator review 1–4 h | apply + freeze", P36.12 "9–10 family-day legs", P37.2 "5: pre-grow |
  tier bump | run | soak | revert").
- **What Stage B writes (FEA-01):** SEED-13 writes manifest rows for **all 309** chain rows (mechanical from the CSV),
  full contracts **only for 11A (59 rows) and PLAN-11B**, `Kind: skeleton` contracts for 11B–11D rows, the GATE markers
  and the `## Human prerequisites` section. **11B, 11C and 11D contracts are authored at each sub-round boundary by the
  PLAN rows** (`decompose-spec mode=extend` against this CSV), so each GATE's OM-20 list cites written contracts.
- Every live-stage contract gets a `Live window:` header, an OM-14 mutation list and its live-leg re-run prompt;
  live-result edges are marked `live:`.
- The contract template gains a `harness:` header (CF-04: `Devin Desktop / swe-2-high`) and B5's ticket-contract block
  (B5 §6.2).
- **Skills reach the executor only if Devin Desktop loads them.** Devin CLI was verified (read-only session store,
  2026-10-01T04:16:29Z) to read `~/.claude/skills/*/SKILL.md` (symlinks into `~/agent-skills`); **whether Devin Desktop
  reads the same path is unverified** — T6's orient dry-run runs in Devin Desktop and confirms it (Appendix A). If it does
  not, T5's OPERATING MODE carries the B6 overrides and the Tier A/B-must template content is hand-applied (SEED-13).

### 8.6 Rows 184–187 and Round-10 return passes

- **184 HUMAN-H4, 185 P32.22a, 186 HUMAN-H5, 187 P32.23** stay as existing manifest rows, never dispatched, with tokens
  appended byte-for-byte (L3 §6.3): 184 `superseded-by(T-EVAL-IND segment: EV1, HUMAN-H6, HUMAN-H7)` · 185 `…EV-F` · 186
  `…HUMAN-H8` · 187 `superseded-by(CONF-02 = P34.45, CONF-09 = P37.44; decision leg: T-EVAL-IND segment EV-D, EV-R)`.
  A dispatch amendment (L3 §6.3 item 1) supersedes the old "a resume re-enters at row 184" sentence. Validator V2 skips
  them; if the validator change is unwanted, use `deferred(D-R10-HUMAN-1; T-EVAL-IND)`. `nextTicket` is never a HUMAN marker.
- **Re-homed return passes:** row 183 → P35.61 (ACT-14) · 188 → P35.62 (ACT-15) · 191 → P35.63 (ACT-24) · 179–182 →
  P37.16 (ACT-22) · D-P32.16-1 → P37.59 (ACT-23, conditional). The GATE-G3 signature (row 190) does not transfer.

### 8.7 Non-chain units

- **Seed (20 units, 24.25 runs, ≈ 30 contexts of ≤ 1 run):** SEED-00…19 (Appendix A maps them to T0–T6). SEED-11 now
  writes 30 ADRs in 4 contexts (+1.0 run at S6); SEED-12 writes MEM/ENG/OPS/SEC/REL/CONF; SEED-13 writes the manifest + 11A
  contracts + skeletons; SEED-14 writes the register entries incl. the S6 changes.
- **Operator actions (19 active):** OP-01…OP-10, OP-12, OP-13 (US + AU keys), OP-19, OP-20, OP-22, OP-23, OP-24, **OP-25**
  (gate-signing key) and **OP-26** (HG-03 flips per wave); §11. Dropped at S6: OP-11 (no domain purchase), OP-14 (no top-50
  review), OP-15 (folded into the auto-allow ADR + P37.46), OP-16 (D-P30.2b-1 stays OPEN), OP-17 (no OPCHECK), OP-21
  (agent-written query set); OP-18 done at GATE-P (C-13).
- **Later (20 units, 23.5 runs):** LATER-01…09, 11…14, 16…22, each with a trigger (§15). Moved into the round at S6:
  LATER-10 → P37.70, LATER-15 → P34.28 + OP-25, R11-ACQ-23a/b → P37.69a/b.
- **Post-round (1 unit):** REVIEW-R11, the Claude Code deep review (§13.4).

### 8.8 Critical paths and calendar cliffs

- **Calendar (binding):** GATE-P (done) → seed → GATE-B → P34.1 (≤ 10-19) → P34.39a (after 10-10) → **P34.46 (≥ 10-14)** →
  GATE-G4 → Wave A legs (10-19→23) → Wave B code incl. P36.74 → **Wave B legs (10-26→11-05)** → 11B chains → **P35.63** →
  GATE-G5 → P37.1–2 → **Wave C legs (11-16→20)** → **P36.72b (≥ 11-13)** → GATE-G6 → Wave D (11-23→12-04) → **P37.65b
  (outside 12-06→13)** → P37.68a–d → P38 → GATE-ANNOUNCE → REVIEW-R11.
- **Runs:** inside 11B three chains converge on P35.63 (JUR-01→02a→02b→DSRC-01→JUR-03; CONF-03a→03b→04→07a→07b;
  REL-01→…→REL-06); the Wave B block (≈ 16.5 runs incl. P36.74) precedes them (inference: P35.63 ≈ 2–3 days later than
  with no Wave B block). P35.57 no longer heads the structural chain (A-20 = a).
- **Decision path:** none left from S5. In-round, the A-18 boundary flip (operator, inside P35.17) stays on the critical
  path; OD-27 = a, so the T6 push needs only the scans.
- **DAG check (S6 re-run):** 309 chain rows, contiguous 201–509; every `depends_on` token resolves; 0 rows before a
  dependency (hard, `(S2)`, `live:`, sequence and soft edges all counted); acyclic; no 11A/11B row depends on a later
  sub-round; no active row depends on a dropped, moved or done unit.
- **Expected timeline (inference; 6–10 runs a day incl. CI waits; operator answers within a day):** seed → GATE-B (R0)
  ≈ 10-03→10-07; GATE-G4 ≈ 10-15→10-17; Wave B code done ≈ 10-19→10-22; GATE-G5 ≈ 10-27→11-02; GATE-G6 ≈ 11-13→11-18;
  P37.65b ≈ 11-27→12-05; tail ≈ 12-03→12-12; then REVIEW-R11. About 10–11 weeks from R0 — the +10.0 runs S6 added are ≈ 1–2
  days at that rate.
- **Cliffs, not one-for-one slips (FEA-12).** Monthly freezes (days 6–13) and "one manual job at a time" quantise slips:

  | first dispatch R0 | 11A end / G4 | Wave A (10-19→23) | Wave B (10-26→11-05) | Wave C (11-16→20) | final release P37.65b | tail |
  |---|---|---|---|---|---|---|
  | ≤ 10-07 | 10-15…10-17 | in window | in window | in window | 11-27…12-05 | 12-03…12-12 |
  | 10-08…10-12 | 10-17…10-21 | partial; remainder → 10-26…10-30, sharing Wave B's days | squeezed; spill → 11-16 week (collides with C) | in window or → 11-23…12-04 | 12-03…12-05 or ≥ 12-13T12:00Z | mid–late December |
  | 10-13…10-20 | ≥ 10-21 | → 10-26…10-30 | → 11-16…11-20 (Wave C → 11-23…12-04) | → 11-23…12-04 | ≥ 12-13T12:00Z | late December |
  | > 10-20 | ≥ 10-28 | → November windows | → late November | → December | January 2027 | January 2027 |

  **Latest R0 that keeps each wave in its window:** Wave A ≈ 10-07, Wave B ≈ 10-12, Wave C ≈ 10-20 (inference at the slow
  end of 6–10 runs a day). **A-19 = a:** waves slip to their next windows; nothing is dropped. At GATE-G4 the orchestrator
  re-projects calendar and agent usage from 11A's measured runs a day and pauses rather than silently stretching (FEA-10).

---

## 9. Obligation mapping (S1b: `universe/UNIVERSE_DISPOSED.csv`; `tools/check_dispositions.py` → structurally valid, 0 errors after S4c and again after S6 — it checks shape, not truth, F-27)

### 9.1 Totals

**1,159 items, exactly one disposition each:** 528 universe items (97 deferrals, 161 requirement rows, 36 backlog, 62 risk,
144 ADR triggers, 19 return passes, 2 readouts, 6 manifest rows, 1 ledger finding) + 538 findings (F-01…F-538) + 28
feedback items + 65 candidate groups covering all 694 consolidated candidates.

| disposition | count | | disposition | count |
|---|---:|---|---|---:|
| ticket | 739 | | merged-into | 24 |
| already-done | 146 | | wontfix | 14 |
| later-phase (trigger named) | 153 | | operator-action | 7 |
| decision (S1c id) | 42 | | spec-amendment (→ SEED-12) | 7 |
| live-return-pass | 26 | | adr-waiver (→ SEED-11) | 1 |
| human-marker | **0** | | | |

Ticket-like primary landings: first waves 542, other Round-11 units 224, operator units 7. 292 of 317 catalog units are
referenced; the 25 orphans are process/acceptance units each justified by its design row (S1b §7).

S4c changes (COV-02, COV-06, COV-07): F-184 operator-action(OP-11) → ticket(R11-SAFE-06 = P35.38); F-27 SEED-18 →
SEED-02 (+ P34.9 link); D-SOURCES.8-1 ticket(P36.2) → decision(E4-R4a), hence operator-action 8 → 7 and decision 41 → 42.
**S6 changed no universe disposition** (S6 writes only the plan and the three data CSVs): the 42 `decision(…)` items and the
41 decision-dependent items now have answers in `data/decision_catalog.csv` (`operator_answer`), and T4 re-dispositions
them (e.g. D-SOURCES.7-2/8-2 → P37.12/P37.70, D-SOURCES.2-2 → P36.77, D-P30.2b-1 → LATER-01). Dropped catalog units stay in
`data/ticket_catalog.csv` marked `dropped (S6: …)` so every reference resolves; the S1b checker stays green (§9 heading).

**Rule (c) switch (S2 §2.2):** S1b provisionally defined "first waves" from the catalog; T4 switches the check (and rule
(a)'s catalog view, COV-13) to read `sub_round ∈ {11A, 11B}` from `data/round11_plan.csv`. Result at S4c (scratch check
emulating the switch): the 56 S0/S1 owner rows and their prerequisite closure — **87 chain rows / 79.5 runs (11A 42, 11B 45)
+ 7 seed units** — sit entirely in 11A ∪ 11B; nothing in the closure moved out of 11B.

### 9.2 Every owed deferral (36 = 32 OPEN + 4 PARTIAL)

| disposition | deferral → landing |
|---|---|
| **ticket (9)** | D-FEDERAL.1-1 → P37.11 · D-P32.10a-1, D-P32.16a-1 → P34.24 · D-P32.16-1 → P37.59 (conditional; B-8 = e-mail-only) · D-R10-MEMORY-1 → P34.30 (split, option C) · D-R10-SOURCES-1 → P34.38 (+ P37.16) · D-SOURCES.7-1, D-SOURCES.9-1, D-SOURCES.9-4 → P36.2 (E4-R3 flip, R5 flip, R6a capture / R6b close; 11C) · **D-P32.16-1 → P37.59 remains OPEN in Round 11** (B-8: intake stays dark; U-008; COV-15) |
| **live-return-pass (9)** | D-P21.5-1 (PARTIAL) → P37.55 + OP-19 (B-6/Q-E2-23 = a, B-21 = yes and A-0.4 = a were all answered, so it can close in 11D) · D-P31.4-1 → P34.39 · D-P32.18-1, D-P32.19-1, D-P32.20-1, D-P32.21-1 → P37.16 (HG-03, E4-B1) · D-P32.23a-1 → P35.62 · D-R10-LIVE-1 → P35.61 · D-R10-PUBLISH-1 → P35.63 |
| **later-phase (9)** | D-P21.7-1 → LATER-03 · D-P30.2b-2, D-R6.1-EVAL, D-R10-HUMAN-1 → LATER-01 (T-EVAL-IND) · D-R7.1-AUTH → LATER-06 · D-R7.2-SEND → LATER-04 · D-R10-USERS-1 → LATER-02 · D-SOURCES.8-2 → LATER-10 · D-SOURCES.9-3 → LATER-17 |
| **decision (7) — all answered at GATE-P** | D-SOURCES.8-1 (PARTIAL) → E4-R4a…d (B-41: R4a OGL-Edmonton after capture, R4b flip, R4c QLDTraffic API → P37.70, R4d decline under A-9; non-US kept, S5-4) · D-JURIS.2-1 (PARTIAL) → E4-R1 (close, eID leg WONTFIX) · D-P30.2b-1 → B-18 fold into the maintainer check, **which B-31 removed: stays OPEN, non-blocking, T-EVAL-IND (LATER-01)** · D-P32.3-1 → B-18 (folded into ADR-159's auto-allow + P37.46; no operator review) · D-SOURCES.2-2 → E4-R2a **flip `documentcloud`** (P36.77) + R2b decline · D-SOURCES.7-2 → B-18 (US 511 keys, OP-13 → P37.12) · D-SOURCES.9-2 → E4-S2 (WONTFIX) |
| **already-done (2)** | D-P21.3-2 (hosted jobs already use every credential; F1 → DONE via B-43) · D-SOURCES.12-1 (PARTIAL; P26.16 + D-SOURCES.17-1 + catalog sweep 0/68; E4 S1 → DONE) |

Every status change above is written by **SEED-14 as appended annotation text only**; lead-token transitions are queued
in `reports/memory-repair/pending_transitions` and applied by P34.8 through the repaired obligation-event tool (CF-03).
The 11A exit requires 0 pending.

### 9.3 Requirements, backlog, risks, ADR triggers

- **161 requirement rows** (the 69 not-MET + reduced-scope, cited-deferral and sampled rows): ticket 109, live-return-pass
  8, already-done 17, later-phase 12, wontfix 8 (7 N/A-RATIONALE + GEO-007), spec-amendment 3, decision 4.
- **36 backlog rows:** ticket 17, already-done 11, later-phase 4, decision 3, merged-into 1. New BL rows start at BL-059.
- **62 risk rows:** ticket 18, already-done 20, later-phase 11, merged-into 7, decision 4, spec-amendment 1, adr-waiver 1.
- **144 ADR revisit triggers:** ticket 54, live-return-pass 6, already-done 26, spec-amendment 2, later-phase 56 (45 quiet
  triggers watched through the new `ADR_TRIGGERS.csv`).
- **19 return passes:** already-done 11, merged-into 7, operator-action 1 (the #141–#190 merge sitting, OP-08).

### 9.4 S0/S1 findings (113)

109 land on a seed or 11A/11B unit (108 tickets + F-522's live-return-pass); 3 rested on S5 decisions, **now answered**
(F-31 → A-4 + the seven A-23 waivers, closed by ADR; F-191 → C-3, recorded; F-386 → A-3 = yes, fixed by P35.5 + P36.50); 1 was already done (F-366, I8's own
correction). None is later-phase or wontfix. **Not every owner is a full fix** (COV-06): the table lists each S0/S1 whose
owner is an interim mitigation, depends on a GATE-P answer, or whose final fix lands later.

| finding(s) | sev. | owner (S0/S1 unit) | fix kind | final fixing row | GATE-P answer that shapes it |
|---|---|---|---|---|---|
| F-097, F-131 (handles) | S0 | P34.18 → P34.21b | fixed live in 11A (scope widened); handle pages leave in republish #1 | P34.21b (+ P35.26 for the `camera_operator` value) | A-0 = wait: unresolved, operator-deferred until P34.17/P34.18/P34.21b |
| F-387 (misattribution) | S0 | P34.21a/b | fixed in republish #2; interim N-4 + P34.21b's bucket leg | P34.21b | A-0.2 = wait: the 09-27 downloads stay readable until P34.21b's first leg |
| F-130 (API 25 subjects) | S0 | P34.25 → P34.46 | fixed ≥ 10-14; interim N-7 | P34.46 | — |
| F-07, F-099, F-390, F-399 (permalinks) | S1 | P35.42 (TX-13a) + P34.11 wording | **interim** (honest wording, release id on every page) | P36.66b (11C) | D-J3-6 = yes: `/s/<pub>/` snapshots pin them |
| F-103 (bulk/API/terms unlinked) | S1 | P34.13 | partial (terms linked) | P36.50 (11C) | A-3 = yes: download links from the R2 host |
| F-386 (bulk release unreachable) | S1 | decision D-J3-4 (A-3) | answered a | P35.5 + P36.50 | A-3 = yes (R2 + $50 egress ceiling) |
| F-452; F-106/F-420 labels | S1 | P34.26; P35.30 | partial (non-organisation labels fixed) | P36.41–P36.42b, P37.22–28 | A-10 = b + c: registry-matched organisations labelled; the rest "not yet reviewed" |
| F-522 (0 of 2.78 M bindings reach bytes) | S1 | P35.61 (live-return-pass) | partial: only sources re-run in P35.61 | P35.61 | the ≈ 2.78 M legacy links stay zero-byte (insert-only spine), labelled "capture not bound" |
| F-27 (validators check structure) | S1 | **SEED-02** (+ P34.9 no-vacuous-pass) | fixed by construction (rehomed from SEED-18) | P34.9 | — |
| F-184 (hijackable contact domain) | S1 | **P35.38** (rehomed from OP-11) | fixed without a purchase | P35.38 | B-6: no purchase; OP-11 dropped |
| F-31 (spec contradicts decisions) | S1 | decision Q-7 (A-4) | answered a + seven waivers | SEED-11/12 | A-4 + A-23: closed by the waiver ADRs; S6's flagged contradictions (R-18, R-27) carried |
| F-191 (backward confirmations) | S1 | decision OD-12 (C-3) | answered (sentence adopted) | SEED-08 | C-3 recorded with its 2026-10-01 time |
| F-506, F-507, F-511, F-518…F-521 (L1/L2 correctness) | S1 | P35.24–27, P35.46–47 | pulled forward into 11B; interim P34.44b ratchet | 11B rows | A-6 = a: C0–C2 collapse (C2 enabled, B-31) |
| F-512 (inferential tiers auto-written) | S1 | P34.45 (back in 11A; ER re-run on the S5-3 list) | fixed in 11A; publication with P35.63 | P35.63 | A-20 = a: lands in 11A, its live-API effect labelled |

### 9.5 Every operator feedback item

| item | disposition → landing |
|---|---|
| U-001 | ticket → P36.64 (Home/About; tagline ratified at C-4) |
| U-002 | ticket → P37.68 (CAP-01: co-primary journeys) |
| U-003 | merged into U-003.G; its headline clause ("everything currently advertised … should actually work") is traced in §5.7 (ROUTES.csv check at P36.72a/P37.68d) and C-12 (COV-04) |
| U-003.1 … U-003.11, U-003.G | tickets → the rows in §5.7's table (first owners: P36.33, P35.29, P36.31, P36.34, P36.52, P36.54, P35.43, P36.60, P36.48, P36.47, P36.58, P36.18) |
| U-003.X | already-done → K12a + K12b; 32 ideas dispositioned (K13 §5.2) |
| U-004 | ticket → P36.17 (lexicon; precise sections kept byte-for-byte) |
| U-005 | ticket → P35.36 (+ P35.37, P35.42, P36.17, P36.24, P36.40, P36.51, P36.66, P37.26–27, P37.40) |
| U-006 | ticket → P34.44 (+ P35.22, P35.24, P35.25, P35.46, P35.47, P37.67) |
| U-007 | ticket → P37.68 (+ P37.67, P37.66, P36.64) |
| U-008 | ticket → P34.5 (budget alert, billing export, spend ledger) |
| U-009 | later-phase → LATER-22 (announcement after CAP-02 and the operator's go) |
| U-010 | already-done ("nothing to note"; no obligation) |
| U-011 | ticket → SEED-17 (OPERATING MODE: autonomy, spend transparency, no outside contact) |
| U-012 | ticket → SEED-13 (one round in the existing patterns) |
| U-013 | ticket → P34.16 (repo honesty; counsel wording) |
| U-014 | operator-action → OP-10 (`contact@surveillancegraph.org` alias; alias first, C-8) |
| U-015 | already-done → B7: attribution high-confidence for 477 of the 480 chain commits; the S0 surface "medium, unknown"; the model behind `swe-2-high` unknown (TS-17); confirmed at C-2 (the P31.5→P31.6 hand-over was planned) |

**Asks recorded only in META_PLAN §7.1 (COV-03).** They are not yet universe items because the S1b checker builds its
feedback set from `OPERATOR_FEEDBACK.md` only; T4 adds them to the universe and extends rule (d) to them. Traced now:

| id | operator, verbatim (META_PLAN §7.1) | disposition → rows |
|---|---|---|
| W2-1 | *"configure them for ingestion and ingest them into prod"* | ticket → P35.6–P35.11 (Wave A), P36.1a–P36.12 + P36.74 (Wave B), P37.1–P37.2 (Wave C), P36.75–78, P37.69a/b, P37.70 and P37.54 (Wave D, in scope) |
| W2-2 | *"making the data itself easily exportable"* | ticket → P35.5, P36.50, P36.53, P36.68, P37.43 |
| W2-3 | *"explore each third party source"* | ticket → P36.45–P36.49, P36.69 |
| W2-4 | *"link to the ground truth"* | ticket → P35.35, P35.36 (`upstream_href`) |
| W2-5 | *"download the raw data"* | ticket → P37.36 + P36.50 (D-J3-1 = yes: raw-ok sources after the Part VIII byte screen) |
| W2-6 | *"see ingestion logs/metrics/timestamps"* | ticket → P35.32–P35.34, P36.43, P36.46 (D-J3-2 = yes: scrubbed run logs published) |
| PF-1 | S0 hotfixes approved in principle (attribution takedown, `/editorial-standards/` fixture review, `/dispute/` notice) | ticket → P34.17, P34.21a/b |
| PF-2 | G1 quick actions QA-1…QA-10 | ticket → P34.3–P34.6 (R11-ACT-01…04) |
| PF-3 | `/task/new/` demo pages | ticket → P34.17 (R1.9; via F-278) |
| GM-1 | *"keep me in the loop"* | OM-17 digests at every check-in (SEED-17) |

### 9.6 Candidates and decision-dependent items

- **65 candidate groups (694 candidates):** ticket 13 (Waves A–C families), later-phase 43 (LATER-09 long tail, 389
  candidates), decision 8 (the Wave-D groups — I8-Q5 = a, so they become tickets at T4), merged-into 1. Tier 3 (259) is not
  acquired. With S5-4 the non-US groups that S4c had moved to LATER-09 (ACQ-23a/b) come back into the round (P37.69a/b).
- **41 decision-dependent items** waited on 24 S1c ids (S1b §4); all 24 were answered at GATE-P, and T4 records each final
  kind from `data/decision_catalog.csv`'s `operator_answer`.

---

## 10. Ops track

### 10.1 Already done before the round (Track 0, operator-approved)

Automated backups + PITR and an on-demand backup (0.1); `/curate/` removed (0.2); minimal alerting to the operator's
address — e-mail channel, uptime checks on the site and API `/health`, alert policies for failed job executions (excluding
the broken `sig-probe`), `sig-pg` disk > 85 % and both uptime checks (0.5). **Not done:** restore drill, deletion
protection, budget alert, TLS-expiry alert, probe re-roll — and none runs before Round 11 (A-1 "None now; ticket it", A-2
"alert later"): each is an early-11A ticket, and the gap until then is unresolved, operator-deferred (R-28).

### 10.2 Ops rows in the round

| row | what | live stage / window |
|---|---|---|
| P34.3 | data protection: deletion protection + retain-on-delete (QA-1), maintenance window (QA-2), versioning + noncurrent lifecycle (QA-6), `sig-web` bucket non-public (QA-7), disk cap | production write; outside AR-3 for `sig-pg` patches |
| P34.4 | alerts that reach a human: verify and extend Track 0.5; TLS expiry (A-1: not done before the round); `SIG-ALERT` log alert; `sig-probe` re-roll (QA-5); disable the GitHub `reingest` schedule (QA-8) | production write (OM-20, S5-3) |
| P34.5 | cost guard: budget alert at $300, billing export, monthly spend ledger incl. Cloudflare/R2 and agent-usage lines (U-011; A-2 "alert later") | production write (billing admin; OP-12; OM-20, S5-3) |
| P34.6 | restore drill at scale into an isolated clone with RTO/RPO; restore-point procedure; monthly logical export (A-1: the drill not done before the round) | production write (separate instance; OM-20, S5-3) |
| P34.10 | one allow-listed publish path; never deletes release trees | code; first used by P34.17 |
| P34.49 | Part VIII at-rest audit: scan the evidence store for I7 S1–S9 classes and F-406 bytes (OSM `user`/`uid`, Eyes on Flock search reasons, ArcGIS attributes); seal or suppress per SIG-GOV-007; counts only (TS-07) | read-only scan + restricted-tier move (OM-20 list) |
| P34.50 | DNS cut-over runbook + zone inventory for OP-09: LB hostnames DNS-only (grey cloud) so the Google-managed cert (expires 2026-12-22) keeps renewing; R2 on a subdomain; TTL lowered 48 h ahead; DNSSEC DS handled at the registrar; rollback = revert nameservers; mail check (FEA-08) | read-only |
| P34.39a/b | 10-10 OSM replay read-back (D-P31.4-1; prerequisite of P34.46) / first-fire wave to 10-21 + peel-on 10-29 as a non-blocking monitoring leg | read-only; clock-guarded |
| P34.40–41 | serving topology (LB path rules for `/v1/*`, `/intake/*`; registry mount; nginx roll) dark; withdrawal-barrier bytes | production write (dark) |
| P34.42–43 | least-privilege runtime identities (remove project Editor); execution host for hosted return passes; read-only `sig_audit` login | production write |
| P35.1 | scheduler of record + daily live-diff + cron lint + fleet hygiene (79 triggers; cruft jobs) + the scheduler consolidation into one dispatcher (B-13, −$7/mo); no robots-disallowing host is paused (A-5) | production write |
| P35.2 | alerting as code; probe targets out of the image; escalation | production write |
| P35.3 | production-truth probes + fixture-sentinel scan (G10) | read-only probes |
| P35.4 | ops runbook (`docs/ops/RUNBOOK.md`) + stale ops doc fixes (README "≈$0/$9") | docs |
| P35.5 | zero-egress distribution host; $50/mo egress ceiling + kill switch; R2 Class-B operations ceiling + alert (FEA-18) | production write (R2 via Cloudflare; A-3 = a) |
| P35.67 | post-DNS cut-over probe: TLS, managed-cert renewal status, every route, mail; second leg ≈ 11-22 (cert renewal window) | read-only legs after OP-09 |
| P36.13 | API exposure: enforced rate limits (search 30/min, burst 10); no Cloud Armor now (D-K3-6) | production write |
| P36.43–44 | status lane (6-hourly `status/**` writer); release cadence automation | production write |
| P37.3 | evidence-store hardening + off-instance copies | production write |
| P37.4a/b | security baseline: scanning, SBOM, signing, audited restricted-byte access, audit logs (+≈ $5) with a Data Access exclusion filter and a log-volume alert (FEA-18) | production write |
| P37.15 | scheduled parser canary | production write |
| P36.75, P37.70 | Flock share-list claims (append-only spine write); AU keyed APIs (after the operator's key registration) | production write (OM-20 G5/G6 lists or in-ticket gos) |
| P37.71 | single-operator true-deletion mechanism (WV-06); executes nothing by itself | code; each use = an operator in-ticket go, never OM-20 |

All production writes follow OM-14 (contract-named mutation, scripted path, pre-state capture, restore point, rollback
command, run-ledger entry) and AR-2/AR-3. They need no per-row go **only** if the operator approved, verbatim, an OM-20
list naming the row — for 11A that list was approved at GATE-P (S5-3) — otherwise each is an in-ticket pause. The class-based never-list (§3.3) always pauses.

**The DNS move (OP-09) is the highest-blast-radius change in the plan (FEA-08).** It runs only from P34.50's runbook; the
LB hostnames stay DNS-only so Google's load-balancer authorisation keeps seeing the LB IP and the managed certificate keeps
renewing before 2026-12-22; P35.67 probes TLS, certificate status, every route and mail after the move and again ≈ 11-22;
P34.4's TLS-expiry alert fires at 21 days. Cloudflare/R2, the registrar and domains sit outside the GCP budget alert, so
P34.5's spend ledger reads them each check-in, and P35.5 adds an R2 operations ceiling next to the $50 egress ceiling.

### 10.3 Monitoring the round itself

Each acceptance row (P34.47, P35.64, P36.73) and P38.1 writes a `probe-run/1` record: head-bound CI for every PR of the
sub-round with flake re-runs; `sig-ops probe-hosted` and G10 probes; backups and PITR; scheduler live-diff; present/
absent route probes; the quality suite (ratchet regressions = 0); layer reached per row; the live-leg queue; new
deferrals and obligation events; the spend line; merges the operator made (read from GitHub). No acceptance statement
about production may cite a probe older than 24 h.

### 10.4 Money (S2 §9; S1a §6; inference until P34.5 gives measured numbers — C-7: the operator does not know the last invoice)

The $300/mo ceiling covers **infrastructure only** (GCP, Cloudflare, domains, paid APIs; A-2). Re-projected at S6 from
S4c's per-sub-round lines with the GATE-P answers applied (all inference on G1's unverified list-price baseline):

| after | delta | main items (USD/mo) | projected total |
|---|---:|---|---:|
| baseline | — | Cloud SQL ≈ 52–54, LB ≈ 18, `sig-api` min-1 ≈ 7–10, jobs ≈ 3–9 (G1 list-price estimate, unverified) | ≈ 90–100 |
| 11A | +4.90 | quality job 2, alerts 1, Round-10 API 1, logical export 0.5, data protection 0.3, cost guard 0.1 | ≈ 95–105 |
| 11B | −5.31 | zero-egress host 1, Wave A 0.5, release bucket/staging 0.5, Flock portal connector 0.5, …; Artifact Registry cleanup −1; **scheduler consolidation −7** (B-13) | ≈ 90–100 |
| 11C | +12.70 | release cadence 4, **`sig-api` 1 GiB +3** (B-30), Wave B 2.5, basemap on R2 2, Axon Connect / DocumentCloud / Sourcewell-OMNIA connectors ≈ 1, status lane 0.2; **no Cloud Armor (−6 vs S4c)** | ≈ 102–112 |
| 11D | +10.10 | security baseline 5, Wave C 2.2 (incl. the 25 GB pre-grow), Wave D 1.5 (in scope; incl. ACQ-23a/b), AU keyed APIs 0.2, evidence store 0.5, …; **intake stays dark (−2 vs S4c)** | **≈ 112–122** |

- **Removed at S6:** the `sig-project.org` registration (≈ $10–20/yr; B-6), Cloud Armor (−$6; D-K3-6), the conditional
  intake service (−$2; B-8). **Added:** search memory (+$3; B-30), the vendor/terms-conflicted connectors and AU APIs
  (≈ +$1.7; storage of non-US objects and share-list claims sits inside the one-way 25 GB pre-grow already counted in
  Wave C). **Later:** Cloud SQL CUD after 3 measured bills (≈ −$12; LATER-19); permanent Cloud SQL tier +$49 only on its
  trigger (LATER-08).
- **One-off:** restore drills ≈ $0.15–0.40 each; Wave-C tier bump ≈ $3; Class S release object writes ≈ $2.5 each (≈ 6 →
  ≈ $15); optional hardware key for OP-25 ≈ $25–55; paid data $0 (B-12).
- **Over-$300 approvals needed: none planned.** Watch list read in every digest: denial of wallet on the world-readable
  `sig-public` tree until P34.21b's first leg (anonymous access removed) and P35.5's kill switch (≈ $120/day at 1 TB/day;
  P34.5's alert sees but does not stop it — and P34.5 lands only in 11A, A-2a); search API abuse before P36.13 (≈ $140/mo
  worst case, no Cloud Armor); DocumentCloud document bytes in the evidence store (unmeasured; P36.77 measures);
  LATER-08. If the measured baseline is well above G1's estimate, GATE-G4 re-projects the round before 11B.
- **Unmeasured lines (FEA-18):** P37.4's Data Access audit-log volume (exclusion filter + alert), R2 Class-B operations
  under a request flood (ceiling in P35.5), the Wave-C pre-grow (one-way), the evidence bytes of the new document
  connectors. P34.5 measures the baseline in 11A's first days.
- **Agent usage** is outside the infrastructure ceiling and has **no fixed cap** (A-2): every wave digest reports it, and
  the orchestrator **pauses and asks at any usage-limit event**. Estimated now (inference):

  | item | contexts | basis |
  |---|---:|---|
  | Stage-B seed | ≈ 30 | 20 units, each split into ≤ 1-run contexts (SEED-11 now 4) |
  | chain engineering rows | ≈ 300 | 304 non-gate rows, minus the 3 PLAN rows and P34.48 counted as fan-outs |
  | PLAN-11B/11C/11D + P34.48 fan-outs | ≈ 22 | 7 + 7 + 6 + 2 |
  | live-leg re-runs | ≈ 43 (≈ 28.5 runs) | `leg_runs`; OM-19 |
  | splits for the 256k window | ≈ +10–20 | the rows in §8.5 and any T3/PLAN review finds |
  | re-runs after red CI, late splits, orchestrator boundary work | ≈ +5–10 % | Round 10 executed no live legs, so it is not a base rate (B5 §3.2) |
  | **Devin Desktop total** | **≈ 400–480 fresh contexts** | |
  | post-round review (Claude Code, Opus 5.5, xhigh) | ≈ 8–12 | REVIEW-R11; modelled on Stage P's review rows |

  **Calibration:** this planning session's heavy rows measured ≈ 250k–600k tokens each (orchestrator observation; a
  usage limit was hit at ≈ 19:10Z on 09-30). Applied to every Devin context that gives **≈ 100 M (400 × 250k) to ≈ 290 M
  (480 × 600k) tokens** over ≈ 10–11 weeks — an upper bound in practice, because the 256k window caps what one context can
  hold and light S rows sit far below it; Devin's own usage unit may differ, and the digest reports whatever per-session
  usage figure the harness exposes ("not measured" is a valid line; no figure is invented). **Per-wave digest (OM-17 and
  the GATE packet's budget part):** runs and leg runs dispatched; usage per run (median, maximum); cumulative usage; the
  projection to round end at the measured rate; usage-limit events; harness and model. No new paid model service or
  second model family in the round (B-31; LATER-18); the post-round review runs on the operator's existing Claude Code
  access.

### 10.5 Risks carried by ops (operator-accepted or operator-deferred)

MapRoulette key unrotated (rotation before any contribution-back use; LATER-03) · the operator's personal address as the
public dispute and intake contact until the `contact@` alias exists (Q-29; WV-05) · no counsel (U-013; WV-07) · **the
deferred Track-0 items** — no restore drill and no TLS-expiry alert before the first-fire wave and the 10-10 replay, no
budget alert until P34.5, the listable 09-27 tree until P34.21b — recorded as **unresolved, operator-deferred** (A-1, A-2a,
A-0.2), not as accepted risk (R-28).

---

## 11. Human-work plan (operator-only)

### 11.1 Principle

There are no humans on the project besides the operator (U-008), and no one outside the project is contacted (U-011).
Agents never perform, simulate or stand in for human work: no agent label counts as a human label, no agent signs, and
model agreement is never ground truth (P4; OM-08). **Round 11 seeds no HUMAN rows, and by the operator's choice it has no
human checks** (B-31, B-42): no OPCHECK, no operator "clear" of Part VIII families, no operator-written query set — each
place where one would appear says so ("no human check performed"; "cleared by agent screen, no human review";
"agent-authored held-out set; not independent"). The operator's own work is either a prerequisite with a due point
(listed in the manifest's `## Human prerequisites` section and in the preceding check-in packet) or a gate item — never a
chain row a ticket silently waits on.

### 11.2 Operator actions and touchpoints by date (OP-01…OP-26; re-estimated at S6; inference)

| when (expected) | touchpoint | sync? | est. time |
|---|---|---|---|
| 2026-10-01 (done) | **S5 / GATE-P**: 99 lines in 23 rounds, 03:41:19Z → 05:03:05Z, + the C-10 local inspection | yes (chat) | ≈ 1.5 h (spent) |
| T0 → Stage B (≈ 10-01 → 10-07) | OP-01 Tier A skills (applied at T0) · OP-05 GitHub stack ruleset + merge settings · OP-07 project variable, billing check, usage alert · OP-23 store the git bundle privately · OP-24 leg-runner schedule · **OP-25 gate-signing key + allowed_signers** · **GATE-B** | — | 2–3 h |
| before row 201 | OP-02 skills Tier B-must (OP-03/04 early in the round) | — | 0.5 h |
| ≈ 10-08 → 10-10 | republish #1 go + **copy batch #1** (tagline + K14 copy, express-terms disclosure, WV-05 intake text, A-20 basis label / status notice; N-strings already ratified) | — | 1–1.5 h |
| early 11A | OP-12 billing admin (P34.5) · in-ticket gos for P34.18, P34.24a, P34.44a · P34.21b's bucket-access go | — | 0.5–0.75 h |
| by GATE-G4 | **OP-09 switch nameservers** from the P34.50 runbook · OP-10 `contact@` alias right after | yes (registrar) | 0.75–1.25 h |
| ≥ 10-13 | republish #2 go | — | 0.25–0.5 h |
| **10-14/10-15, 14:00–20:00Z** | **P34.46 schema slot (operator present)** | **yes** | 1–2 h |
| ≈ 10-15 → 10-17 | **GATE-G4 sitting**: ING-GO-A, ING-GO-B, the Wave A/B HG-03 flip lists (**OP-26**), P35.57 API-roll go, the 11B OM-20 list, **Class R standing-go renewal**, spend report | **yes** | 1–1.5 h |
| after OP-10 | **OP-13 key registrations** (US 511 + QLDTraffic + NSW; Secret Manager) | — | 0.5–1 h |
| ≈ 10-20 → 10-26 | P35.17 boundary flip (A-18, OP-26) · P35.14b sqitch go | — | 0.25–0.5 h |
| ≈ 10-24 → 10-28 | **P35.61 bounded-apply plan review** (within 1–3 working days of the leg) | **yes** | 1–4 h |
| ≈ 10-27 → 11-02 | **P35.63 HG-11 readout** (no OPCHECK) and **GATE-G5** (ING-GO-C, Wave-C/vendor flip list, 11C OM-20 list, standing-go renewal) in one sitting | **yes** | 1.5–2.5 h |
| by GATE-G5 | OP-20 pipeline signing key | — | 0.25–0.5 h |
| 11-13 → 11-18 | **P36.72b HG-11 readout**, P36.38 API go, **GATE-G6** (ING-GO-D + the Wave-D flip list incl. N1–N21, ACQ-23, DocumentCloud, Sourcewell/OMNIA, Axon Connect, RB-06b, RB-08; 11D OM-20 list; standing-go renewal) | **yes** | 2–3 h |
| **11-16 → 11-20** | **Wave-C tier-bump go when the leg is due** | **yes** | 0.25 h |
| ≈ 11-20 → 12-02 | P37.16a/b capture-run gos (no Part VIII "clear": the agent clears, B-42) · P37.20/P37.42/P37.36 gos · P37.55 deposit go · P37.72's GOV-017 question only if the analysis fails | — | 1–1.5 h |
| ≈ 11-27 → 12-05 | **P37.65b final HG-11 readout** (no OPCHECK); OP-19 Zenodo DOI deposits | **yes** | 1.5–2.5 h |
| ≈ 12-01 → 12-08 | OP-22: operator walkthroughs of the 13 journeys (maintainer, not independent), "beautiful" gallery sign-off; the "who runs SIG" text only if the operator chooses to write it (C-5) | — | 3–5 h |
| ≈ 12-03 → 12-12 | **GATE-ACCEPT-R11** (sign the accepted-deviations list verbatim) · **GATE-ANNOUNCE** (MUSTs-unmet list, Q-29 revisit, announcement copy) | yes | 1.5–2.5 h |
| any time | OP-08 bottom-up merge sitting #141–#190 + the v0.1.0 tag — **a safety item** (public `main` keeps false governance text and the repo-tip handle strings until merged, TS-09); optional per-sub-round merges after each GATE (FEA-17) → then OP-06 | — | 1–2 h + optional |
| every wave | read the digest (spend and agent-usage lines) | — | 0.25 h × ≈ 8–10 |
| after the round | read REVIEW-R11's findings register | — | 0.5–1 h |
| only if needed | a WV-06 deletion go (P37.71's mechanism); a usage-limit pause decision | — | as needed |

**Total ≈ 23–40 h over ≈ 21 touchpoints (plus ≈ 8–10 wave digests) in ≈ 10–11 weeks after GATE-P**, eight synchronous slots in bold. Removed at S6:
three OPCHECKs (≈ 1–2 h), the top-50 organisation review (1–2 h), the query set (0.5 h), the four dossier-family Part VIII
"clears", any response-time duty, the domain purchase. Added: OP-25, OP-26 (≈ 0.25 h per wave), AU key registrations, the
standing-go renewals inside each GATE sitting, reading the post-round review.

### 11.3 What is waived, deferred or owed — and the trigger that reopens it

| obligation | Round-11 posture | trigger |
|---|---|---|
| independent human evaluation (SIG-EVAL-001/002/005/007, IDENT-027/028; D-R10-HUMAN-1, D-R6.1-EVAL, D-P30.2b-2, D-P30.2b-1; rows 184–187) | **owed, non-blocking, never waived**; Round 11 measures, discloses and labels PROVISIONAL; "no human check performed" | **T-EVAL-IND** |
| SIG-EVAL-004 lower bound | **WAIVED for C0–C2 only** (A-6, ADR-153) | T-EVAL-IND; a proposal to auto-write an inferential tier; GQ-23 failing twice in a quarter |
| hostile-reader review (SIG-UI-042) | **release block WAIVED** (WV-04, ADR-179); `/editorial-standards/` says "not yet performed"; findings listed as known issues | a hostile reader becomes available; GATE-ANNOUNCE |
| dossier independent check (SIG-DOS-002) | owed | T-EVAL-IND |
| second reviewer, editorial board, legal home, one-click intake, two-person deletion, counsel clauses | **WAIVED** (WV-01/02/03/05/06/07; §6.5) | each waiver's trigger (§6.5) |
| usability study on the live site (D-R10-USERS-1, SIG-UI-001) | owed | LATER-02: participants available and contact authorised |
| outreach, records-request sending, recruiting (D-R7.2-SEND, CONTRIB-012/012a/013, GOV-024, CHART-033) | owed later-phase by ADR | LATER-04: the operator revisits U-011 |
| contribution-back to OSM/MapRoulette (D-P21.7-1) | owed later-phase | LATER-03 |
| counsel opinion | not sought and, with WV-07, not owed by the spec | LATER-05: the operator obtains counsel |

**T-EVAL-IND fires** only when all three are recorded in GATE DECISIONS with evidence (L3 §6.5): (a) the operator states,
in their own words, that at least two people independent of the project are available to label, and authorises that
contact as an explicit exception to U-011; (b) the "frame-affecting set" has landed — CP-1, CP-2, CP-4, CP-5, CP-6 plus
the Stream-I camera ingests (L3 §2; in this plan P35.22, P35.24, P35.25, P35.16–19, P35.15 and Waves A–C); (c) the Q-24
aim is recorded (certify one tier at n = 149, or measure only at n ≈ 100). On firing, `decompose-spec mode=extend` seeds
**EV1** (reviewer surface + evaluation database, ≈ +$10/mo) → **HUMAN-H6** pilot → **EV-F** freeze → **HUMAN-H8**
confirmatory → **EV-D** → **EV-R**; **HUMAN-H7** once dossier live passes exist (LATER-01, 6 runs).

**What the operator does personally, disclosed as not independent:** copy confirmations, gos and readouts, HG-03 flips,
key and DNS steps, the gallery sign-off and the journey walkthroughs. None of these is ever reported as independent review;
wherever an operator walkthrough is counted it is written "operator walkthrough (maintainer, not independent)" (TS-22).

---

## 12. Integration and branch policy (H1, H2; §7.1 Q-11)

- **Stack on #190.** At GATE-P a branch **`r11/seed`** is created at the head of `claude/next-phase-planning` (which forks
  from `b051732c`, #190's head); Stage B commits on top of it; T6 pushes it and opens the **seed PR** with base
  `devin/p33-8-agent-docs-refresh`. Planning commits reach the chain unchanged (no squash, cherry-pick or rewrite).
- **One ticket, one branch, one PR**, branch prefix `r11/`, each PR's base = the previous ticket's branch. Agents never
  merge, retarget, rebase, force-push, tag, or merge `main` into a stack branch, and never push to a branch once a
  successor exists. **A live leg run days later gets its own branch `r11/<id>-live-<n>`** from the current chain tip, one
  PR (base = the tip branch) carrying its run-ledger entry, `probe-run/1` record and DEFERRALS/obligation transition, and
  a head-bound CI read; the next ticket stacks on it (OM-19; FEA-05). **Agent commits** carry the harness/model trailer
  (OM-01, CI-checked) and keep the operator's name as author (A-21 = b, a disclosed risk), so the trailer is the only
  record of which harness wrote a commit; pushes use the operator's account.
- **The operator merges later** (OP-08; H1 §2–§4). H1's simulation: a bottom-up merge `main`@#140 → #190 has zero
  conflicts in 49 steps and ends tree-identical to #190 (`64a23cd7…`), with `main` keeping its lockfile blob; expect a
  transient red on `main` for one step after each of #165/#179/#185. The merge loop must be **bounded at #190** (`TOP=190`
  or an explicit list) so it never sweeps Round-11 PRs, including an unratified seed, into `main` (H1 NEW-5). B1's
  corrections cannot land before #143 without rewriting history; H1 recommends **not** gating the merge on them — if the
  operator wants `main` never to show uncorrected dates without the correction beside them, merge #143–#190 and the seed
  PR in one sitting. If the operator commits to `main` or a pre-#190 branch again, the fix is mirrored into the Round-11
  stack tip, and the orchestrator records `git merge-base --is-ancestor origin/main <chainTip>` at each boundary. After the
  sitting: the `main` ruleset with the five required checks (OP-06) and an optional `v0.1.0` tag by the operator (B-10).
  Releases are built from unmerged stack commits until then (B-10). **The merge sitting is a safety item** (TS-09):
  public `main` keeps the false governance/counsel text until P34.16's correction is merged. **Integration debt (FEA-17):**
  by the round's end ≈ 340 stacked PRs (#141–#190 + ≈ 290 Round-11 PRs incl. live-leg PRs); the operator may merge each
  sub-round's stack after its GATE (agents still never merge), and P38.3c sizes the integration plan separately. The
  orchestrator records `git merge-base --is-ancestor origin/main <chainTip>` at each boundary — an OPERATING MODE line T5
  writes (COV-14).
- **CI policy:** every Round-11 PR passes all five `ci.yml` jobs (python, docs, composed, security, web) on its current
  head; local-only green is written `locally-green`; the 16 pre-#190 reds are merge-readiness items, not Round-11 blocks;
  clock-dependent latent reds and seed-introduced reds still block (H2 §3.3). Repository settings are operator actions
  (OP-05 before the seed push, OP-06 after the sitting, OP-07 before row 201); no CODEOWNERS.
- **Public-repo push policy (B-16).** The repository is public, so the first push publishes this planning directory.
  Keep `claude/next-phase-planning` **local until T6**. Before the push: SEED-00 removes the credential-shaped literal from
  two planning notes by a forward fix; scan for secrets (`make scan-secrets`), personal identifiers and Part VIII content.
  **The operator's address appears verbatim in three planning files** (META_PLAN §7.1, `baseline/TRACK0_RECORD.md`,
  `feedback/OPERATOR_FEEDBACK.md`), inside verbatim operator quotes, **and it is already public in the author metadata of
  the public repository's commits** (478 of 480 Round 1–10 commits and this planning branch are authored with the
  operator's identity; TS-11) as well as the Q-29 dispute contact. An appended correction cannot remove it from the
  planning branch's history. **OD-27 = a (GATE-P, 04:39:45Z): publish as recorded** at T6, after the secret,
  personal-identifier and Part VIII scans; the agent makes a git bundle the operator stores privately (B-16 c, OP-23).
  Planning commits reach the chain unchanged.

---

## 13. Round tail and acceptance

### 13.1 Sub-round acceptance rows (P34.47, P35.64, P36.73; S; read-only)

Each reads live state (§10.3), records a `probe-run/1` record and an acceptance note reporting the **highest layer reached
per row**, and drafts the GATE packet (agent-drafted, labelled; any line with a non-action default listed first). It cannot pass with an
unexplained red, a ratchet regression, a pending seed transition (11A), or a **due** leg that has not run (earliest time
passed, go held, not run); a leg whose window extends past the GATE (e.g. P34.39b to 10-29) is listed and carried
(FEA-03). It also reads the managed-certificate status and the spend report (§10.4). The exit lists are §5's
acceptance bullets and S2 §4.1–§4.4.

### 13.2 Round-level success criteria (P38.1a/b checks each on the final release)

Every line was answered at GATE-P, so these criteria are no longer conditional on recommendations; where the operator
chose a descope, the criterion is stated as chosen.

1. **Features and UX (U-007a; D3 §3a):** all 13 journeys pass the agent walkthrough (`agent-verified`) and the operator
   walkthrough (maintainer, not independent); U-003.1–.11 pass their K-row acceptance live; every route advertised on the
   09-27 release works or shows an honest notice — the six C-12 withdrawals are accepted (ROUTES.csv); 0 UUID-only labels
   and 0 undated edges; every figure reaches its evidence in ≤ 2 clicks or says why; search covers 55 jurisdictions, 20
   cities and the top 25 vendor and agency names, with relevance reported on the **agent-authored held-out set** (B-28);
   K0 budgets and accessibility pass on real data; "My location" either ships as a map-pan-only control or its GOV-017
   question went back to the operator.
2. **Correctness and comprehensiveness (U-007b; D3 §3b):** L3's round targets hold on the final release (CONF-14; §5.4)
   or each miss names its fixing row; M-1b reported as measured per declared namespace (no certification figure);
   `/quality/` live with failing and ratchet checks shown and "no human check performed" stated; the coverage targets of
   §5.5 **including D3 §3(b) — OSM ALPR, Eyes on Flock (share lists as claims) and Atlas vendor data reach place and entity
   pages — the per-vendor Flock/Axon thresholds (incl. direct portals and Connect pages) and Wave D's Tier-2 projection**.
3. **Clarity (U-007c; D3 §3c):** §5.7's clarity list; the tagline *"Public surveillance, traced to the documents."*;
   "beautiful" is the operator's call (B-29 gallery).
4. **Honesty:** 0 S0 open; 0 status words unbound to recorded state; 0 claims from the full L3 §4.5 not-claimable list;
   PROVISIONAL on every unevaluated figure; disclosure ships in the same publish as exposure — incl. the express-terms
   basis (ADR-183), the robots disregard as host + count, the terms-conflicted fetching (ADR-184), "single maintainer, no
   second reviewer" and "no human check performed"; **every landing-copy clause is bound to a measured check (GQ id) with
   a probe-run record ≤ 24 h old at the publish that ships it, or ships in its conditional form** (TS-10).
5. **The spec tells the truth (META_PLAN §1 outcome 4; COV-16):** 0 spec MUSTs contradicted by a recorded operator decision
   without an ADR, an adopted waiver (A-6, A-23) or an owed row; F-31 closed by the waiver ADRs; the open contradictions
   S6 flagged (§14 R-18 rule 6, R-19 046c, R-27 GOV-017, R-31 GOV-003) each resolved or carried with a trigger.
6. **Build truth:** every boundary read head-bound CI; 0 G1 and 0 G2 violations; every due live leg executed in its window
   or re-scheduled with a date; every production statement cites a probe ≤ 24 h old; no proxy signature; every agent commit
   trailered with harness and model (Devin Desktop / `swe-2-high`); ≤ 1 orchestrator close-repair.
7. **Cost:** measured monthly infrastructure (GCP + Cloudflare + domains) ≤ $300 every month; the 100× traffic projection
   ≤ $300 or approved; agent usage reported in every wave digest, every usage-limit event followed by a pause and a
   question.

A criterion the operator descoped at GATE-P is reported as decided (with its line), never as MET and never as a defect.

### 13.3 The 13 acceptance journeys (D3 §2; K13 §8; walked cold from `/` at 390 and 1440 px)

| persona | journeys (budget) |
|---|---|
| local advocate, council meeting in 6 days (≤ 10 min) | **A1** type "Oklahoma City" (1 min, ≤ 3 clicks) · **A2** what is deployed, who runs and approved it, next decision (+3) · **A3** print a council brief (+2) · **A4** know what to bring (+3) |
| investigative journalist | **J1** defend a headline figure (5) · **J2** "who supplies ALPRs to Texas agencies, and who can access the data?" (10) · **J3** is this figure disputed? (3) · **J4** cite it durably (3) · **J5** what changed since the last release? (5) |
| organizers | **O1** who runs what in my county or city (3) · **O2** who decides and when; subscribe (2) · **O3** a local list without the map (2) · **O4** act on a gap (3) |

A journey passes within its budget with no wrong-conclusion risk and every fact carrying a source, an as-of date and a
release id. The agent walkthrough is recorded `agent-verified`, never "user-tested"; the operator walks each too
(OP-22), recorded "operator walkthrough (maintainer, not independent)" (TS-22).

### 13.4 The tail (P38, rows 500–509, 7.0 runs) and the post-round review

| row | what | size |
|---|---|---|
| P38.1a/b | **CAP.1 (CAP-lite)**: independent gap analysis of landed rows against the Round-11 requirements — a: 11A + 11B, b: 11C + 11D + composed live verification with CI for every open PR, probe-run records ≤ 24 h old, two-sum headline per status layer (both flagged for a 256k split, §8.5) | M + M |
| P38.2 | **CAP.3**: close small in-scope gaps; everything else becomes a DEFERRALS row with a trigger; the **accepted-deviations list** — the descopes and accepted risks the operator chose at GATE-P (§4.6), the C-12 withdrawals and the seven waivers | S |
| GATE-ACCEPT-R11 | the operator signs the accepted-deviations list verbatim (HG-14 domain) | — |
| P38.3a/b/c | **REC**: `reconcile-build` a: backlog + readiness, b: spec reconciliation, c: integration plan for ≈ 340 stacked PRs (operator merge legs sized here) | M + M + M |
| P38.4 | **DOC**: `refresh-repo-docs` then `agent-docs`; every production statement cites a probe-run record | M |
| P38.5 | **CAP-02**: announce-readiness review against D3 §5 | S |
| GATE-ANNOUNCE | the operator's decision; never automatic; agents contact no one; the announcement itself is LATER-22 | — |
| **REVIEW-R11** (post-round, not a chain row) | **deep review by Claude Code (Opus 5.5, xhigh effort)**, modelled on this Stage-P review: read-only over code, build memory, CI and live state after the final release and P38.4; output = a findings register (S0–S3 with evidence classes) and a next-round planning input; ≈ 8–12 contexts sized by its own meta-plan (A-15) | ≈ 8 |

Compared with Round 10's nine-row tail that read nothing live: 10 rows, 7.0 runs, live reads by construction, and a
second harness only after the round (no in-round second harness, A-15). Stream acceptances (TX-16, ACQ-28, CONF-14,
CAP-01) are ordinary 11D rows that measure.

### 13.5 Ready to announce (GATE-ANNOUNCE checklist; D3 §5, S2 §8.3)

The operator's own test, *"I would send this to a journalist today"* · every S0 closed live and status words bound to
recorded state · all 13 journeys pass the agent walkthrough and the operator walkthrough (maintainer, not independent) ·
D3 §3(b) holds live · **every landing-copy clause bound to a measured check ≤ 24 h old or in its conditional form**
(TS-10) · **the "spec MUSTs unmet at launch" list signed verbatim** — after the seven A-23 waivers it holds only items owed
for other reasons (SIG-EVAL-001/002/005/007, SIG-DOS-002, SIG-UI-001, the outreach MUSTs, SIG-GOV-003's published SLAs
unless waived) and any open contradiction S6 flagged (§14 R-18, R-19, R-27, R-31) · **Q-29 revisited: keep the personal address as the public contact, or require the `contact@`
alias (OP-10) before announcing** (privacy-harm reports, SIG-GOV-003; TS-21) · attribution gate and Part VIII screens
green; the express-terms rows disclosed with their captured terms and the operator-accepted basis (A-8) · pinned citation
and release id on every page · zero-egress serving with the kill switch and budget alert tested · cost at 100× traffic
≤ $300 or approved · backups, a drilled restore and alerts · the dispute and intake page states that senders disclose their
address and that **no response time is promised** (B-8, WV-05) · §1 text, a known-issues page and PROVISIONAL disclosures
live · **the dedup is published** (B-26) · the gallery signed (B-29) · the "who runs SIG" section either written by the
operator or omitted (C-5) · REVIEW-R11's findings read if it has finished (the operator may wait for it) · the operator
confirms the announcement copy. If GATE-ANNOUNCE is unanswered, SIG is not announced.

---

## 14. Risks

| # | risk | mitigation | trigger to revisit |
|---|---|---|---|
| R-1 | **Live legs never run** (Round 10's "prepared, not executed", queued) | OM-19 runs due legs at every boundary, on their own `r11/<id>-live-<n>` branches; no GATE while a leg is *due*; the OP-24 leg-runner backstop runs held-go legs while the chain is paused and alerts on a due leg it cannot run; "engineered" never reported as "live" | a due leg unrun at a boundary |
| R-2 | **Answered lines drift back into defaults** (the S4c defaults no longer apply) | every `operator_gate` cell and the decision catalog carry the GATE-P answer (S6); `continue` answers batch lines only; P38.2 lists operator-chosen descopes as decided, never as "not attempted" | S6r finds a stale default |
| R-3 | **Scale** (309 chain rows; CAP-01 fans in ≈ 117 rows) | four gated sub-rounds; every row ≤ 1 run; contracts per sub-round by PLAN rows with a Phase-4 sizing review; re-split rule (11B at its edge; GATE-G4b named in advance) | a sub-round over 85 rows / 75 runs |
| R-4 | **Operator load and approval fatigue** (≈ 23–40 h over ≈ 21 touchpoints) | the human checks the operator removed; OM-20 lists; the N-1…N-7 allowance; readouts from P35.60's generator; flip lists batched per wave; weekday 14:00–20:00Z slots | a GATE sitting runs over 3 h |
| R-5 | **Hosted-write accidents** (L44 rewrites `claim_evidence` under an exclusive lock; re-keying; Wave C ≈ 1.1 M claims on 1 vCPU; share-list claims) | AR-2 restore points; P34.6 drill first; P34.24b rehearses the exact deploy set; P34.46's numeric go/no-go; class-based never-list; AR-3; temporary tier bump; one manual job at a time | a failed restore point or an over-threshold rehearsal |
| R-6 | **Denial of wallet** before P34.21b's first leg and P35.5 (the bucket tree stays listable; no budget alert until P34.5) | P34.3 makes `sig-web` non-public; P34.21b removes anonymous access early in 11A; P34.5 alert; P35.5 early in 11B; usage in every digest | egress above the watch line |
| R-7 | **UX outruns the data** (K13 R-1) | all Stream-L S1 fixes in 11B before new surfaces; capability binding; "records" wording until the dedup; CAP-01 checks wrong-conclusion risk | a CAP-01 wrong-conclusion finding |
| R-8 | **Calendar slip** — cliff-shaped (§8.8); S6 added ≈ 10 runs and a tighter Wave D | A-19 = a: waves slip to their next windows; G4 re-projects; overflow Wave D sources ship in the 2027-01-15 cut | R0 later than ≈ 10-07 |
| R-9 | **CI unavailable or flaky** | P34.2 flake allow-list and one re-run; "CI unavailable" → `blockedOn` + verbatim, time-boxed waiver only | two flake re-runs on one head |
| R-10 | **Rights or legal exposure without counsel** (vendor terms, mirrors, database right, Part VIII) — now chosen, see R-18…R-21 | per-wave HG-03 lists executed by the operator; Part VIII at-rest audit (P34.49), residential demotion (P35.66), officer-naming gate (P35.28), redaction (P36.15) before new hosts; withdrawal barrier + dispute channel as remedies | any legal demand (SEC-003 posture, ADR-166) |
| R-11 | **The public repo** publishes planning notes, the operator's address and redacted Part VIII findings on first push | B-16: local until T6; SEED-00 + pre-push scans; OD-27 = a publishes as recorded; the private git bundle (OP-23) | a scan hit |
| R-12 | **Usage limits mid-round** (≈ 100–290 M tokens estimated; a limit was already hit on 09-30) | A-2: usage in every digest; the orchestrator pauses and asks at any usage-limit event (no fixed cap); G4 re-projection | a usage-limit event |
| R-13 | **Stage B under-sized** (30 ADRs, six families, 59 contracts + 309 manifest rows) | SEED-11 now 4 contexts; 11B–11D contracts and the TRANSP/K13 families move to PLAN rows; each seed unit split to ≤ ~150k tokens loaded | a seed context over the target |
| R-14 | **Cost baseline is unverified** (G1 list-price ≈ $90–100 vs README "≈ $0/$9"; C-7: invoice unknown) | P34.5 billing export early in 11A; GATE-G4 re-projects if the measured baseline differs materially | the first measured bill |
| R-15 | **Baseline drift during Stage B** (operator merges, first fires, the 10-10 replay) | the A1 delta re-runs before T6 (SEED-01); P34.39a reads the replay back; dates from the clock (AR-4) | an unexplained delta |
| R-16 | **DNS move breaks TLS or routes** (Google-managed cert expires 2026-12-22) | P34.50 runbook (DNS-only LB records, TTL step-down, DNSSEC handling, rollback); P35.67 probes after the move and ≈ 11-22; TLS-expiry alert at 21 days (P34.4) | a failed post-move probe |
| R-17 | **Personal data stays public while the round runs** (handles at the repo tip, the listable bucket, ids; history) | early-11A owners (P34.17, P34.18, P34.21b); RI-01 acceptance covers repo + bucket + all id kinds + values; history disclosed (A-0.4) | P34.47's crawl finds a handle |
| **R-18** | **Fetching vendor- and platform-hosted pages against their anti-automation terms** (Flock, Axon Fusus Connect, DocumentCloud/MuckRock, Sourcewell/OMNIA; A-17, B-35, B-39, E4-R2a) — breach-of-terms or access claims; an IP block; and **SIG-INGEST-036 rule 6 ("ask first" for small civil-society projects) is not waived while U-011 forbids contact, so fetching DocumentCloud/MuckRock without asking conflicts with a MUST** (flagged, not resolved) | ADR-184 envelope (public, unauthenticated pages only; no logins, keys or circumvention; rate limits; terms captured verbatim; exposure disclosed; Part VIII screen); immediate stop and record on any block or demand; withdrawal-by-new-claim; the rule-6 conflict goes to the operator before P36.77 activates (waive rule 6 for it, authorise contact, or keep it dark) | a cease-and-desist, an access block, a ToS change, or the operator's rule-6 answer |
| **R-19** | **Express-terms rows kept public** (≈8,088 rows incl. TxDOT and 3 NC rows; A-8) — and, open: if any row's captured licence metadata is an affirmative machine-readable reservation, SIG-INGEST-046c (not waived) requires refusal | ADR-183 with the operator's sentence; captured terms + basis disclosed on pages and in files; withdrawal on objection (P34.41 barrier, ≤ 15 min); P36.1a classifies the captured metadata and returns any 046c case to the operator | a rights-holder objection or takedown |
| **R-20** | **EU/UK database right on N1–N21** (B-34; SIG-LIC-009's counsel clause waived, WV-07) | precedent basis recorded per row; express prohibitions excluded; SIG-PUB-017 jurisdiction-conditional publication; LIC-009 risk-register entry kept | an objection from a non-US publisher; counsel obtained |
| **R-21** | **Robots disallows disregarded** (122 hosts incl. 102 PrimeGov, plus new hosts; A-5) | disclosed as host + count in run logs (B-19); 046c reservations refused; rule-7 opt-out honoured at once; conservative rate limits | an opt-out, a reservation or a block |
| **R-22** | **Single maintainer with all seven waivers** (no legal home, board, second reviewer, hostile reader, anonymous intake, two-person deletion or counsel) | each waiver's compensating controls (§6.5); public decision log; every readout says "single maintainer, no second reviewer" | each waiver's trigger; announcement |
| **R-23** | **No human checks** (no OPCHECK, agent-cleared Part VIII families, agent-written query set; B-31, B-42, B-28) | mechanical census and ratchets gate; agent lanes labelled and never gating; every surface says "no human check performed" / "cleared by agent screen" / "agent-authored"; T-EVAL-IND owed | a reader-reported error the checks missed; T-EVAL-IND |
| **R-24** | **The executor is the model B7 associates with Round-10's record failures** (`swe-2-high`; A-15), with the operator's name as author (A-21) | mechanical guards bind any harness (B4 guard core, G1–G4 checks, head-bound CI, OM-01 trailers CI-enforced, OM-02 close discipline); one digest per wave; the post-round Claude Code deep review; no in-round second harness to catch what CI cannot | a G1/G2 violation, an untrailered commit or a close-repair |
| **R-25** | **Live API answers change before Class S readouts** (A-20; P34.45's ER re-run, 11B structural writes) | basis label on every response (P34.25) + `/status/` notice; P35.57 still lands; OM-20 lists name each write | a reader cites a changed answer |
| **R-26** | **Tribal data ingested without a tribal-data-governance rule** (two S8 members; B-32; TR1–TR2 facts + citations) | Part VIII screen; facts + citations only; no outside contact; withdrawal on objection | a Nation's objection; a governance rule adopted |
| **R-27** | **"My location" vs SIG-GOV-017** (MUST NOT build an "is a camera watching me right now" surface; not waived) | P37.72 writes the GOV-017 analysis first; map-pan only; no location leaves the browser; no proximity output; a failing analysis pauses and returns the question | the analysis result |
| **R-28** | **Deferred Track-0 exposures** (handles, bucket tree, `/visual-language/`, no drill or TLS alert before 10-10, no budget alert) — unresolved, operator-deferred | early-11A owners (P34.4–P34.6, P34.17, P34.18, P34.21b); RI-01 crawl at P34.47 | a first-fire failure or an exposure report before the owners land |
| **R-29** | **`sig-project.org` not bought** (residual squatting of a domain old UA strings and docs named; B-6) | P35.38 removes every reference; the UA names surveillancegraph.org | the domain is registered by a third party |
| **R-31** | **SIG-GOV-003 (published SLAs by category, privacy-harm and safety first) vs B-8 "no time promises"** — an unwaived MUST in conflict with an answer (S6 flag) | the dispute notice states the address and that senders disclose it (WV-05); the conflict is put to the operator (waive GOV-003 for Round 11, or approve SLA text in a copy batch); until then GOV-003 is listed unmet at GATE-ANNOUNCE | the operator's answer; announcement |
| **R-30** | **Devin Desktop tooling unverified** (whether it loads `~/.claude/skills`; scheduled sessions for the leg-runner; the 256k window under real Load lists) | T6 dry-run in Devin Desktop; §8.5 sizing; OP-24 falls back to Devin CLI headless with the same model, recorded (OM-01) | the T6 dry-run result |

---

## 15. Explicitly deferred (each with its trigger)

| unit | what | trigger | runs · $/mo |
|---|---|---|---|
| LATER-01 | T-EVAL-IND segment (EV1, H6, EV-F, H8, EV-D, EV-R; H7); also closes D-P30.2b-1 | T-EVAL-IND (§11.3) | 6 · +10 |
| LATER-02 | usability study on the live site | participants available and contact authorised (Q-28 reversed) | 1 |
| LATER-03 | contribution-back to OSM/MapRoulette | the operator opts into contribution-back and outside contact | 1 |
| LATER-04 | outreach, records-request sending, recruiting | the operator revisits U-011 | 1 |
| LATER-05 | counsel packet and written opinion (optional: WV-07 waived the counsel clauses) | the operator obtains counsel (≈ $0 pro bono … ≈ $3.5k–10.5k paid) | 0.5 |
| LATER-06 | authenticated contributor accounts (D-R7.1-AUTH) | demand beyond the vetted curator set + moderation/safety plan + threat model | 2 |
| LATER-07 | know-your-rights content (BL-041) | an intake/onboarding surface opens | 0.5 |
| LATER-08 | Cloud SQL permanent scale-up and HA | sustained CPU/latency or disk past ADR-022's threshold | 0.5 · +49 |
| LATER-09 | acquisition long tail: Tier-2 remainder (130), Tier 3, EDGAR (facts-only basis decided; first request after the alias), CourtListener bulk, OCDS, paid data | per-family triggers (I8 §6.3); paid data needs Q-21 > $0 | 2 |
| LATER-11 | OCR / model-assisted parsing | an admitted source needs OCR (SIG-LLM-001) | 1 |
| LATER-12 | claim-text/entity-scoped search, ZIP lookup, deferred K12b ideas (I-15, I-20, I-29 Flock portal view; I-24, I-27) | CAP-01 passes and the item is prioritised | 1 |
| LATER-13 | closeout-journal cutover | parallel dispatch, a multi-worktree build or a second harness writing memory | 1 |
| LATER-14 | whole-LEDGER rotation per round | LEDGER > 1 MiB | 0.5 |
| LATER-16 | whole-graph canvas (> 3,000 labelled nodes) | a single view needs > 3,000 labelled nodes | 2 |
| LATER-17 | OpenGov procurement source | a documented public endpoint with reviewable terms | 1 |
| LATER-18 | second model family for agent review | the operator revisits Q-L3-4 (answered "no" at GATE-P) | 0.5 |
| LATER-19 | Cloud SQL CUD (the scheduler consolidation moved into P35.1b) | 3 measured bills (G1-TRIM d) | 1 · −12 |
| LATER-20 | legacy bucket retirement | 90 days after P35.59 (dark cutover); `sig-public` root frozen until downloads move | 0.5 |
| LATER-21 | CI runners to Ubuntu 26 | after TC-PIN, before 24.04 end of support | 0.5 |
| LATER-22 | Round-11 announcement and public launch | CAP-02 passes and the operator says go | 0 |

**Moved into Round 11 at S6:** LATER-10 (non-US keyed APIs → P37.70; B-18, S5-4), LATER-15 (operator-only gate-signing
key → P34.28 + OP-25; A-16), R11-ACQ-23a/b (international portals and OGC WFS → P37.69a/b; S5-4). The tribal and
territory channels LATER-09 held are in the round too (B-32 S8, B-33 RB-08).

**Recorded, not just listed (COV-10):** SEED-14 writes every LATER unit above and every one of the 153 `later-phase`
universe items into a committed register — a DEFERRALS row (or a BL row for backlog items) with its trigger and, where
time-bound, its date (LATER-21: before the 24.04 runner's end of support; LATER-20: 90 days after P35.59) — generated by
a committed script from `universe/UNIVERSE_DISPOSED.csv`, with `ADR_TRIGGERS.csv` cross-references for the 56
trigger-type items; `check_backlog` / the obligation checks verify the counts (20 units; 153 items, less those T4
re-dispositions into the round from `decision_catalog.csv`'s `operator_answer`).

Also deferred, outside the catalog: the 45 quiet ADR revisit triggers (watched through `ADR_TRIGGERS.csv`); GraphQL
(RISK-P14-10, on consumer demand); a contradiction to an Atlas row (RISK-P4-08); the next technology-vocabulary version
(SIG-ONTO-057a); Tier 3 (259 candidates) is not acquired at all.

---

## Appendix A — Stage-B translation checklist (exact artifacts T0–T6 must produce)

GATE-P was recorded (§1.3), so Stage B starts after S6r. Every artifact is append-only where it touches a protected
record (OM-13), dated from `date -u`, and committed on `r11/seed`. Catalog units in brackets (S1a); est. runs from
`data/round11_plan.csv` (seed total 24.25 runs in ≈ 30 contexts, each ≤ ~150k tokens loaded so it also fits Devin
Desktop's window; each unit's `notes` name its seams). Stage B writes the seed, the 30 operator-decision ADRs, six
requirement families, the manifest for every row and **full contracts only for 11A and PLAN-11B**; 11B–11D contracts are
written by the PLAN rows.

**T0 — planning orchestrator, before Stage B [SEED-00, 0.5]**
- [ ] META_PLAN §11: one appended, dated correction entry naming each late-stamped change-log line (F-074), and a
      refreshed CURRENT STATE block.
- [ ] Forward-fix the credential-shaped `SIG_INTAKE_*` literal in the two committed planning notes (C-9: no value was ever
      used); `make scan-secrets` and `test_secret_scan_real_tree_is_clean` pass on the planning tree.
- [ ] A-14 Tier A skill changes (SK-13/14/17/18/19/20/22) applied to the user-global skills (OP-01; in progress at S6).
- [ ] **No Track-0 actions** (A-0.1–A-0.3, A-1 and A-2a were answered "wait"/"ticket it"): record in
      `baseline/TRACK0_RECORD.md` that the exposures are unresolved, operator-deferred, with their 11A owners; record
      A-0.4 = accept and disclose.
- [ ] Make the git bundle of the planning branch for the operator's private backup (B-16 c; OP-23).

**T1 — Spec amendments and ADRs [SEED-11 4.0 = 4 contexts, SEED-12 3.0 = 3 contexts]**
- [ ] `docs/research/_meta/spec_src/96c_partXII_s56_round11.md` (new; name proposed): Part XII, §56 Round-11 contract
      extension with the **MEM, ENG, OPS, SEC, REL and CONF** families under final ids (TRANSP → PLAN-11B, K13 → PLAN-11C);
      T1 records the draft-id → final-id map and de-duplicates draft ids listed under two families.
- [ ] Amendments of §6.3 in their owning `spec_src` section files — **incl. the waiver notes for SIG-EVAL-004 (C0–C2),
      SIG-GOV-001/002/008/012/013/015, SIG-PUB-008's second-reviewer role, SIG-UI-042, and the counsel clauses of
      SIG-LIC-009/SIG-INGEST-037, and the CHART-025 and UI-036/050 amendments**; one new **Appendix G.7** row set
      (`99c_appG_corrections.md`) incl. the §55 true dates; **Appendix F** rows for every new ADR (`99a_appF_adr.md`);
      family table updated for newly opened prefixes.
- [ ] `BUILD.sh` regenerates `docs/2_canonical_design_spec.md`; `check_spec_src.py` green; new ids append-only; R10-A6
      untouched.
- [ ] `docs/3_sig_golive_spec.md`: goal 5, GL-GATE-01/02/05, gate register, GL-GATE-06…08 (E2-18; ADR-145 pattern), with
      **GL-GATE-07 and GL-GATE-08 recorded as re-confirmed at GATE-P in the operator's adopted words** (A-5, A-7).
- [ ] `docs/adr/ADR-146…` — **the 30 ADRs whose §7 author is SEED-11**, template header, the operator's adopted words where
      the decision is theirs (EVAL-004 waiver, the seven A-23 waivers, GL-GATE-07/08 texts, express-terms acceptance, the
      Class R standing go, C-3), each stored with its sha256 and the label "agent-drafted, adopted by the operator at
      <time>"; `## Revisit trigger` in each. The ten engineering ADRs are written by their owning tickets.
- [ ] Appended `Superseded by ADR-nnn (<date -u>)` status lines on every superseded landed ADR (incl. ADR-015, 058 §3,
      075, 092, 096 §1, 091 §3–4, 097 §2–3/§6, 105 §5, 118 §2, 126/127 cutover statements) and the `Qualified by` /
      `Amended by` / `Extended by` lines of §7 (incl. ADR-086/106 → ADR-167, ADR-088 → ADR-168); recorded evaluations of the
      fired revisit triggers (F3 §5.1). No other landed-ADR edit. (ADR-016/076 lines are appended by P35.1a with ADR-174.)
- [ ] ADR index regenerated (`build-memory adr-index`).
- [ ] `AGENTS.md` gotcha 6 and `web/AGENTS.md` gotcha 1 replacement text (K0 §7.1–7.2; A-12 = a).

**T2 — Build-memory repair seed [SEED-01…10, SEED-16; 7.75 runs]**
- [ ] SEED-01 C0 preflight: the operator's go for control-ledger edits recorded; A1 delta re-run; `<PRE>` pinned.
- [ ] SEED-02 guard core: `docs/build/tools/memory_guard.py` (G1 diff mode, G2 core, G4a/G4b), policies under
      `docs/build/tools/record_policy/`, `make docs-check-memory/-spec/-matrix`, a memory-guard step in the PR-triggered
      `docs` job, pytest collecting `docs/build/tools/test_*.py`, `ci_boundary.py` (G3a), the OM-01 trailer check (A-21).
      (The `push` trigger is P34.1's, CF-01.)
- [ ] SEED-03 the six living-record pin conversions (PKG-02).
- [ ] SEED-04 `docs/build/reports/memory-repair/`: `README.md`, `date_corrections.csv` (promoted from `data/date_drift.csv`),
      `append_only_register.csv`, `pending_transitions` (CF-03).
- [ ] SEED-05 `PHASE LOG INDEX — Rounds 1–10` (hash-anchored CSV) and a `PHASE LOG — Round 11` section as the only
      append target.
- [ ] SEED-06 **restore the 53 GATE DECISIONS rows deleted by `c2055d96` first**, from `c2055d96^`, then append a dated
      annotation table of every restored row that is clock-false, blanket/delegated or a counsel claim (TS-08);
      `date_corrections.csv` extended to the restored block; G1 gains a restored-dates-vs-`git blame` mode.
- [ ] SEED-07 DATE CORRECTION entries in LEDGER and BUILD_INDEX (sqitch L44–52 never re-stamped — C-10).
- [ ] SEED-08 correction records elsewhere: DEFERRALS correction section; manifest Plan-extension correction lines;
      runs/pr/CAPSTONE addenda; `CORRECTION.md` in the committed fixture-run directories; **annotations with B7's facts on
      ACCEPT-R8, ACCEPT-R10 and GATE-G3 — no operator addendum describing a past state of mind**; the C-3 sentence and
      C-13's "superseded" recorded with their GATE-P times (TS-08, TS-19); C-2's planned hand-over; the `p-17b713`
      supersession record — **no footers on landed ADRs** (CF-02).
- [ ] SEED-09 BUILD_INDEX index repairs (rows 190/195, PR fills, seq 170a, not-landed note).
- [ ] SEED-10 archive LEDGER lines 1–54 byte-for-byte under `reports/memory-repair/` with a sha256 pointer; slim head
      ≤ 12 KiB; status PAUSED.
- [ ] SEED-16 RETURN PASS superseding note + `RETURN PASS — current` regenerated from `OPERATIONAL_READINESS.md §(f3)` and
      the S1b dispositions; no 184–187 ids.

**T3 — Manifest rows and contracts [SEED-13 4.0 = 4 contexts: manifest + skeletons | 11A rows 201–220 | 221–240 | 241–259 + PLAN-11B]**
- [ ] `docs/tickets/00_MANIFEST.md`: Round-11 dispatch amendment + banner (P34 11A "Safe, honest, truthful" · P35 11B
      "Correct and traceable" · P36 11C "Explorable core" · P37 11D "Explored and proven" · P38 tail); **rows 201–509 from
      `data/round11_plan.csv` as they stand**; gate rows without `.n`; one appended `## Plan extensions` line naming
      PLAN-11B/11C/11D as the later contract authors; a `## Human prerequisites` section listing OP-01…OP-10, OP-12, OP-13,
      OP-19, OP-20, OP-22…OP-26 with due points; the L3 §6.3 dispatch amendment and the 184–187 gate-cell tokens; HG-05 as
      an operator-owned integration disposition; REVIEW-R11 named as the post-round closing unit (not a manifest row).
- [ ] **Full contracts only for the 59 11A rows and PLAN-11B** from `_TEMPLATE.md` (+ `harness: Devin Desktop /
      swe-2-high` header + B5 §6.2 block): `Run:` line, `live_verification`, `Live window:` and the live-leg re-run prompt
      where windowed, OM-14 mutation list, `live:` edges, requirement ids, acceptance stated at its layer, the OM-20 status
      of the row (the 13 rows of the S5-3 list pre-authorised). **Every 11A contract's Load list is token-counted; any
      contract over ~150k tokens loaded is split** (A-15; P34.46 first). **`Kind: skeleton` contracts for every 11B–11D and
      tail row**, each naming the PLAN row that completes it.
- [ ] Contract notes on 184–187; "Superseded — not executed" sections on `HUMAN-H4.md` / `HUMAN-H5.md`; no H6/H7 files.
- [ ] Requirement → ticket index; a fresh-context decompose-spec Phase-4 sizing review of 11A against the 256k window.

**T4 — Register mapping and validators [SEED-14 2.0, SEED-15 1.0]**
- [ ] `docs/tickets/DEFERRALS.md`: appended annotations for all 36 owed rows per §9.2 (as answered: D-SOURCES.7-2 and
      8-2 → tickets P37.12/P37.70; D-SOURCES.8-1 → P36.2; D-SOURCES.2-2 → P36.77; D-P30.2b-1 → LATER-01 / T-EVAL-IND;
      D-P32.3-1 → ADR-159 + P37.46); new OPEN rows (SEC-003 owner, the ADR-124 allow row, the D-rows MET-ENGINEERED verdicts
      need, the open S6 contradictions R-18 rule 6 and R-27 GOV-017); **every LATER unit and every later-phase universe item
      recorded with its trigger and date by a committed generator script (COV-10)**; token transitions only queued (CF-03).
- [ ] `docs/build/BACKLOG.csv/.md`: closures with evidence, splits, new rows from BL-059 (incl. the EVAL-004 waiver
      revisit row and one revisit row per A-23 waiver), RISK duplicate-id renames, RISK-P21-03 route; risk rows R-18…R-30.
- [ ] `docs/build/COVERAGE_MATRIX.csv`: verdict vocabulary + `required_domain`/`achieved_domain`/`owed_legs`/
      `accepted_scope`; F2a/F2b/L3 deltas (§6.6) with Appendix B's corrections; **WAIVED(ADR) for every MUST waived at GATE-P (A-6 and the seven A-23 waivers)**;
      each change a `coverage-assessment/1` event. (The 61-row re-verdict is P34.48.)
- [ ] `check_coverage_matrix.py` grammar + cross-checks + spec-derived counts (incl. "an amendment that weakens a MUST is
      a waiver"); `check_backlog.py` open-home rule; new `ADR_TRIGGERS.csv` (incl. Q-29's revisit and the seven waiver
      triggers); validator V2 skips superseded manifest rows (COV-14); `tools/check_dispositions.py`: rules (a) and (c) read
      `data/round11_plan.csv` (`sub_round ∈ {11A, 11B}`; the S2/S4c/S6 units become visible, COV-13), rule (d) extended to
      W2-1…6, PF-1…3 and GM-1 (added to the universe; COV-03), the S4c `acts_on_silence` rule folded in from the scratch
      `check_silence.py` (TS-02), and **the 41 decision-dependent universe items re-dispositioned from
      `decision_catalog.csv`'s `operator_answer`** (§9.6).

**T5 — LEDGER seed and resume prompt [SEED-17 1.0]**
- [ ] CURRENT STATE (values only, ≤ 3 KiB): `round: 11`, `nextTicket: 201` (P34.1), `chainTip` / base per §12,
      `dispatchTarget` (≤ ~150k tokens loaded in a 256k window), **`harness: Devin Desktop`**, **`model: swe-2-high`** (CF-04,
      A-15), `blockedOn`, `returnPass`, `updatedAt` from `date -u`; status PAUSED until C10.
- [ ] OPERATING MODE — Round 11: OM-01…OM-20 (§3.3, S4c wording incl. OM-01's trailer rule and the class-based never-list),
      the **11A OM-20 list approved at GATE-P (S5-3) with its expiry at GATE-G4**, the A-15 pause rules and the per-wave
      digest with a spend and agent-usage line (A-2), A-20's live-API disclosure rule, H2 §7 paste blocks (G3a gate, flake
      rule), G2 §2 activation rules, P16 "alias first" (C-8), the D-P31.4-1 clock guard, the `git merge-base --is-ancestor
      origin/main <chainTip>` boundary record (COV-14), commit authorship = the operator's name with CI-enforced trailers
      (A-21), the Class R standing-go text and its renewal rule (B-9), B6 §5.3 overrides only if the T6 check finds Devin
      Desktop does not load the skills.
- [ ] The leg-runner backstop prompt (OM-19; scheduled by the operator as OP-24, in Devin Desktop or Devin CLI headless with
      the same model — recorded).
- [ ] GATE DECISIONS rows for GATE-M and GATE-P, verbatim with their times, citing `feedback/RATIFICATION_LOG.md` and
      `de0b3591`.
- [ ] Stale-token scan of the head = 0; every path named in the head exists.

**T6 — Validation, dry-run and handoff [SEED-18 0.5, SEED-19 0.5]**
- [ ] Projection regenerated and verified; every validator green (existing + guard core + new checkers); A1 delta re-run.
- [ ] Pre-push scans (secrets, personal identifiers, Part VIII; B-16) and **OD-27 = a** (publish as recorded); OP-05
      settings applied; push `r11/seed`; seed PR to `devin/p33-8-agent-docs-refresh` **5/5 green** on its head. If row 201
      cannot land before 2026-10-19, the seed PR pins `runs-on: ubuntu-24.04` (FEA-16).
- [ ] **Read-only `orchestrate-build` orient dry-run in Devin Desktop** resolves **row 201 = P34.1 TC-PIN**, and records
      **whether Devin Desktop loads the skills from `~/.claude/skills`** (Devin CLI does; Desktop unverified) and whether
      it can run scheduled sessions for OP-24.
- [ ] `PD/HANDOFF.md` with the exact resume prompt (harness Devin Desktop, model `swe-2-high`, worktree, branch, first
      row, OPERATING MODE pointer, the 256k sizing rule).
- [ ] **GATE-B** recorded verbatim, with the 11A OM-20 list as approved at GATE-P (S5-3); C10 flips the LEDGER to
      IN_PROGRESS.

---

## Appendix B — Input inconsistencies this draft had to resolve (for S4)

| # | inconsistency | resolution in this draft |
|---|---|---|
| 1 | B1 §8's correction-ADR draft ("ADRs get an appended correction footer") and SEED-08's scope (33 ADR footers) vs S2 CF-02 (landed ADR bodies frozen; no footers) | CF-02 wins: corrections live only in the register + ADR-146; T1 rewrites B1 clause 2; SEED-08 drops the footers |
| 2 | F2b proposes **WAIVED(ADR)** for SIG-CONTRIB-012/012a/013, SIG-GOV-024, SIG-CHART-033 (outreach) vs S1c B-6 / Q-E2-12 a and S1b (owed later-phase, LATER-04) | owed later-phase by an outreach-timing ADR; **not** WAIVED. Only one requirement waiver remains (EVAL-004, C0–C2) |
| 3 | F2b: EVAL-006 MISSING→MISSING; EVAL-003/004 → AT-RISK-INTEGRATION vs L3: EVAL-006 and EVAL-003 → MET (after CONF-09/12), EVAL-004 → WAIVED scoped | L3 (later row) wins |
| 4 | S1c A-1 (written before Track 0.5) asks for QA-3/QA-4/QA-9 now; Track 0.5 already did most of QA-3/4 | A-1 shown as reduced to the QA-9 drill (+ TLS alert) before 2026-10-10; its value decays daily |
| 5 | S1c Part A = 17 lines / Part B = 43; S2 promotes B-24 | Part A 18 (A-18 = B-24), Part B 42; plus S5-1…S5-4 added by this draft |
| 6 | S1a: R11 252 units / 234.5 runs, later 22 / 25.0 vs `round11_plan.csv` at S3: chain 238.5 runs, later 24 / 27.0 (after S4c: 299 post-split rows, 275.5 runs incl. 20.0 PLAN) | difference = ACQ-23a/b moved to later (CF-06) and S2's 12 acceptance/gate/tail rows (6.0 runs) |
| 7 | Cost: S1c ≈ $100–160/mo (overlapping design estimates) vs S1a ≈ $124–134 vs S2 ≈ $123–133 after 11D | S2's per-sub-round figures used; all rest on G1's unverified baseline (C-7, P34.5) |
| 8 | SEED-02 scope adds the `docs` job `push` trigger vs CF-01 (P34.1 owns it) | CF-01 |
| 9 | A-16 recommends an operator-only gate-signing key **now**, but the catalog keeps it as LATER-15 (trigger "operator adopts Q-B4-2") and S2 places no row for its CI verification | if A-16 = yes, T3 adds the CI verification to P34.28 (MEM-07, readout rules) and an OP item (≈ 30 min); LATER-15 then closes. **S4 feasibility should confirm** |
| 10 | D3 says "the six S0s"; the register has 9 S0 ids | 6 product issues (RI-01…06) + F-01/F-02 (production, mitigated by Track 0); F-097/F-131 are one issue |
| 11 | I8 Waves C/D include non-US scope (AU via OSM; ACQ-23a/b ≤ 10 countries) vs D3 US-first | CF-06: Wave C US + territories; ACQ-23a/b → LATER-09; I8's ≈ 1.11 M Wave-C claims is now an upper bound |
| 12 | Counts of misdated ADR dates: F-21 "20 ADR `Date:` headers", B1 ADR draft "25", B1 table "33 ADR rows (headers + body mentions)" | ADR-146 cites the register's counts rather than restating one |
| 13 | J3 assumed a private repository (D-J3-3); the repository is public (S1c live read) | B-19: commit hashes shown; G3 NEW-5 (release trees committed to the public repo) gains weight; §12 push policy |
| 14 | META_PLAN CURRENT STATE is stale (`nextUnit: WAVE-6-PREP`, `updatedAt 18:56:01Z`) and §7.1 records a decision as "18:2xZ" in a commit made at 17:10:49Z | SEED-00 (F-074) |
| 15 | The planning directory is dated 2026-09-30; S2 onward and this draft were written on 2026-10-01 UTC | dates follow the clock (P2) |
| 16 | S2's table shows 11D ending at P37.65/P37.68 with no 11D acceptance row or check-in GATE | P38.1 (CAP.1) is 11D's live-read acceptance; GATE-ACCEPT-R11 follows. **S4 should confirm** no GATE-G7 is wanted |
| 17 | U-014 approves the operator's name + address as the contact string (P16 amended), while C-8 recommends "alias first" and OP-10 is due only by GATE-G5 (after the DNS move); P35.38 moves the crawler contact to surveillancegraph.org | until OP-10 exists, connectors use the project URL where a URL suffices; the address is sent only where a service requires an e-mail and C-8 is answered. **S4 truth/safety lens** |
| 18 | SEED-11's scope (from S1a) names ≈ 20 ADR topics; §7 lists 31 provisional ADRs (E2's separate posture ADRs, G1's ops ADRs, the jurisdiction ADR) at 3.0 runs | kept one-decision-one-ADR (T1 rule); size risk recorded as R-13 |
| 19 | S1b's provisional "first waves" (133 catalog units) vs S2's 11A ∪ 11B | S2: rule (c) reads `sub_round ∈ {11A, 11B}`; 19 non-owner K13 W1 units moved to 11C |
| 20 | E2 recommended staffing (second reviewer, external hostile reader, counsel opinion, outreach) | superseded by U-008/U-011/U-013 (S1c §9; CF-08): no Round-11 staffing rows |
| 21 | U-003's receipt is stamped 21:28:52Z in `feedback/OPERATOR_FEEDBACK.md` and 21:29:45Z in META_PLAN §7.1 (COV-12) | both are recorded; the feedback record is cited; the 53 s difference is unexplained and left as found |
| 22 | S2/S3 resolutions that S4 overturned: Wave B code after GATE-G5 (FEA-02); OM-19's "opened window" wording (FEA-03); full contracts for ≈ 277 rows in Stage B (FEA-01); CF-15 (TS-04); "exactly one waiver" (TS-05); A-15 carrying OM-20 (COV-09) | each closed at S4c; see `reviews/REVIEW_CLOSURE.md` |
| 23 | Appendix B row 9 asked S4 feasibility to confirm the A-16 key work; row 16 asked whether a GATE-G7 is wanted | A-16 = yes adds the CI verification to P34.28 and an operator setup item (LATER-15 closes); no GATE-G7: P38.1a/b is 11D's live-read acceptance and GATE-ACCEPT-R11 follows (no reviewer asked for one) |
| 24 | (S6) B-41's "as listed" included R2a = decline DocumentCloud while B-39 said fetch it | re-asked in round 18; the operator answered "Fetch, screened" (E4-R2a b) |
| 25 | (S6) A-8 and A-9 overlap on the 3 live NC rows | round 5's wording: A-8 keeps everything as is; A-9 governs new sources only |
| 26 | (S6) B-18 folded D-P30.2b-1 into the maintainer check, which B-31 then removed; Q-25's seat likewise | D-P30.2b-1 stays OPEN, non-blocking (T-EVAL-IND, LATER-01); the operator holds no evaluation seat |
| 27 | (S6) the log's A-12 shorthand "superseding ADR-068/091/097/134" vs K0 §6 (supersedes ADR-091 §3–4 and ADR-097 §2–3/§6, extends ADR-134, leaves ADR-068 unchanged) | K0 §6's precise clauses kept (the decision is D-K0-1 a, "supersede the three-island rule"); flagged for S6r |
| 28 | (S6) the interpretation of IT7 says private registrants are "never stored in public output"; SIG-PUB-002 forbids storing home addresses and incidental private names in **any** tier | PUB-002 applied: P36.76 redacts before anything is persisted (flagged in `design/S6-ratification-applied.md`) |

---

## Appendix C — Evidence index (where each part of this plan comes from)

Notes named below without a section number (E3, F3, F5, J4, K1–K12, I1–I7) were read through the synthesis rows that
cite them (S1a, S1b, S1c, S2, K13, L3, I8), not re-read whole for this row.

| plan section | primary evidence |
|---|---|
| §0, §8 | `design/S2-round-structure.md`; `data/round11_plan.csv` |
| §1, §4.1 | `META_PLAN.md` §7.1; `feedback/OPERATOR_FEEDBACK.md` |
| §4.2–§4.7 (and every "= answer" in §5–§15) | `feedback/RATIFICATION_LOG.md` (GATE-P; commit `de0b3591`); `data/decision_catalog.csv` (`operator_answer`, `answered_at`); `design/S6-ratification-applied.md` |
| §2 | `baseline/BASELINE.md`, `baseline/TRACK0_RECORD.md`; `findings/REGISTER.md`; `review/REVIEW_SYNTHESIS.md`; L2 |
| §3 | `META_PLAN.md` §3; `research/B5-orchestration-retro.md` §6; S2 §3.5 |
| §4 (the questions as asked) | `design/S1c-decision-catalog.md` §2–§9 and appendix; `data/decision_catalog.csv`; S2 §7.3, §11 |
| §5 | D3; K13 (+ `data/k13_requirements.csv`, `data/k13_tickets.csv`); L3; L1/L2; I8 (+ `data/acquisition_plan.csv`); J3/J4; G1; G2; G3; B1–B4, B7; E2; F2a/F2b; F5 |
| §6 | B4 §5; G1 §4; G3 §10; J3 §11; L3 §7; K0 §7, §9; K13 §6; E2 §6; F2a; F2b §2 |
| §7 | B1 §8; L3 §8; K0 §6; K1; K6; E2 §6; G3; J3; G1; H2; B3; B4 |
| §9 | `universe/DISPOSITIONS.md`; `universe/UNIVERSE_DISPOSED.csv`; `tools/check_dispositions.py` |
| §10 | G1; S2 §9; S1a §6; `baseline/TRACK0_RECORD.md` |
| §11 | L3 §4.4, §6.5; S1c §7; S2 §7.4 (E3 figures as quoted by L3 and S1c) |
| §12 | `design/H1-integration.md`; `design/H2-branch-ci.md`; S1c B-15/B-16 |
| §13 | S2 §3.5, §4, §8; D3 §2, §5; K13 §8 |
| §14 | S2 §10; K13 §11; I8; G2 §8 |
| §15 | `data/ticket_catalog.csv` (LATER-01…22); S1b §5.2; K13 §5.2 |

---

## Change notes

| revision | when (`date -u`) | what changed |
|---|---|---|
| S3 draft | 2026-10-01T01:13:07Z → 01:26:35Z | first synthesis (committed `c3e37654`) |
| S4c revision | 2026-10-01T02:38:06Z → 02:55:12Z | closed the three S4 reviews (`reviews/REVIEW_CLOSURE.md`; committed `e5936f96`) |
| GATE-P | 2026-10-01T03:41:19Z → 05:03:05Z | 99 lines answered in 23 rounds (`feedback/RATIFICATION_LOG.md`; committed `de0b3591`) |
| **S6 revision** | 2026-10-01T05:55:53Z | status → CANONICAL; §4 rewritten as the ratified decisions (Parts A, S5, B, C, D2) with the 27 deviations and the recording gaps; §0, §1.3, §3, §5.1/5.2/5.4/5.5/5.6/5.7/5.9/5.10, §6.3–§6.5, §7 (30 SEED-11 ADRs: +179–185), §8 (309 rows, 285.5 runs, 256k sizing, oversized rows), §9, §10 (money, ops), §11 (operator load), §12, §13 (criteria no longer conditional; post-round review; GATE-ANNOUNCE), §14 (R-18…R-31), §15 and Appendix A updated; Appendix B rows 24–28; CSVs: 11 chain rows + OP-25, OP-26 and REVIEW-R11 added, 1 chain row dropped (P35.49), 6 operator rows dropped, OP-18 done, 4 later rows moved in, P34.45 moved to 11A, every operator_gate default replaced by its answer; `decision_catalog.csv` gains `operator_answer` + `answered_at` for all 346 ids. Details: `design/S6-ratification-applied.md` |

*Canonical for Round 11. S3 written 2026-10-01T01:13:07Z → 01:26:35Z; revised at S4c 2026-10-01T02:38:06Z → 02:55:12Z;
ratified at GATE-P 2026-10-01T05:03:05Z; applied at S6 2026-10-01T05:55:53Z (`date -u`). Next: S6r (one fresh-context consistency
review), then Stage B (T0–T6).*
