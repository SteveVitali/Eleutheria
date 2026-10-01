# SIG Round 11 — the next-phase plan

> **DRAFT — revised at S4c to close the three S4 adversarial reviews; pending S5 operator ratification (GATE-P).**
> Nothing in this document is a decision until the operator ratifies it under the GATE-P recording rule (§1.3).
> Recommendations are the agent's; every decision is the operator's. Text marked *agent-drafted* ships only after the
> operator confirms it word for word (META_PLAN §2). This is not legal advice (P4).

- **Row:** S3 of `META_PLAN.md` (Stage P, synthesis), revised by **S4c** (review closure). **Drafted (S3):**
  2026-10-01T01:13:07Z → 01:26:35Z (`date -u`) by Claude Code (Opus 5.5) in the planning worktree
  `~/Eleutheria-next-phase`, branch `claude/next-phase-planning`, from HEAD `9262a959`; the S3 row committed nothing and
  the orchestrator committed it as `c3e37654` (which also changed `META_PLAN.md`, +7 lines; TS-16). **Revised (S4c):**
  2026-10-01T02:38:06Z → see footer (`date -u`), from HEAD `3208c8e0`; every change is listed per finding in
  `reviews/REVIEW_CLOSURE.md`. Chain tip: `b051732c` (`devin/p33-8-agent-docs-refresh`, PR #190).
- **Read-only (P3, P10).** S4c wrote only this file, `data/round11_plan.csv`, `data/decision_catalog.csv`,
  `design/S1c-decision-catalog.md`, `data/ticket_catalog.csv`, `universe/UNIVERSE_DISPOSED.csv` and
  `reviews/REVIEW_CLOSURE.md` (+ gitignored scratch under `docs/build/logs/next-phase/S4c/`). No control file, spec, ADR,
  manifest, LEDGER, register or production system was touched; nothing was committed; no external request was made (P16).
  No secret appears here (P14); the operator's e-mail address is written only as "the operator's address".
- **Evidence class.** `inference` from the cited planning artifacts, except counts, which are the mechanical outputs of
  checkers: S1b `tools/check_dispositions.py` (structural validity, not truth — F-27), S2's plan builder as revised by
  S4c (`docs/build/logs/next-phase/S4c/transform_plan.py`, gitignored) and the S4c ordering check (`check_order.py`).
  Paths are relative to `PD = docs/build/planning/2026-09-30-next-phase/` unless they start with `docs/`, a package
  name or `~`.
- **Synthesis inputs (P1: read for S3, in the sections this plan cites):** `META_PLAN.md` §1–§5, §7, §7.1, §8–§11
  and Appendices A–C; `feedback/OPERATOR_FEEDBACK.md` (U-001…U-015, whole); `design/S2-round-structure.md` (whole) +
  `data/round11_plan.csv` (all rows, by script); `data/ticket_catalog.csv` (by script) + `research/S1a-ticket-catalog.md`
  (whole); `universe/DISPOSITIONS.md` (whole) + `universe/UNIVERSE_DISPOSED.csv` (by script); `design/S1c-decision-catalog.md`
  §0–§9 + `data/decision_catalog.csv` (selected rows); `design/D3-product-direction.md` (whole); K13 §0, §5, §6, §8–§11;
  L3 §0, §2, §6–§8; I8 §0, §9, §11; J3 §0; G2 §0; G3 §0, §10; B3 §1; B4 §0, §5; E2 §0, §6; K0 §0; H1 §1–§3; H2 §0;
  B5 §0, §6; B1 §1, §8; F2a §1–§3; F2b §1–§2; G1 §0, §4; B6 §0; B7 §0; `findings/REGISTER.md` (summary + S0/S1 table) and
  `findings/FINDINGS.csv` (counts); `baseline/BASELINE.md`, `baseline/TRACK0_RECORD.md` §0.5; `review/REVIEW_SYNTHESIS.md`
  (RI-01…06 rows); spec headings and id families in `docs/2_canonical_design_spec.md` (by grep). **S4c inputs:**
  `reviews/S4-truth-safety.md` (TS-01…TS-23), `reviews/S4-feasibility.md` (FEA-01…FEA-19), `reviews/S4-coverage.md`
  (COV-01…COV-17), META_PLAN §3, §7, §7.1, §11 and `feedback/OPERATOR_FEEDBACK.md`.
- **Precedence.** Where inputs disagree, the later synthesis row wins (S4c over S3; S3 over S2; S2 over S1a/S1b/S1c; L3
  over F4/F2b; S1c/S1b over E2/F2b for post-D1 answers). Every disagreement S3 settled is in **Appendix B**; every S4
  finding is closed or deferred in `reviews/REVIEW_CLOSURE.md`.

---

## 0. The plan on one page

**Round 11 makes SIG show, correct and open up the evidence it already holds, while growing US-wide vendor coverage
from high-quality origins** (D3 §0). It runs as **one round, one manifest, one LEDGER and one `orchestrate-build`
loop**, cut into four gated sub-rounds and a short tail (S2 §0, §3.3; U-012 "follow the existing patterns").

| unit | phase | chain rows | eng. runs (of which PLAN) | leg runs* | purpose | ends with |
|---|---|---|---:|---:|---|---|
| Stage-B seed | — | 20 units (not chain rows; ≈ 29 contexts) | 23.25 | — | truthful memory, guard core, operator-decision ADRs, spec families, manifest + **11A** contracts, registers | **GATE-B** |
| **11A** Safe, honest, truthful | P34 | 58 (201–258) | 55.0 (7.0) | 7.5 | S0 removals and fixes live; production protected; CI pinned and read; memory guards; Round-10 schema live; quality baseline; **PLAN-11B** writes 11B's contracts | P34.47 + **GATE-G4** |
| **11B** Correct and traceable | P35 | 84 (259–342) | 81.0 (7.0) | 11.0 | release-pinned API first; Wave A; **Wave B code + activation queued**; identity/time/geography fixes; transparency exports; release pipeline; **first model release** | P35.63 (HG-11) + P35.64 + **GATE-G5** |
| **11C** Explorable core | P36 | 72 (343–414) | 68.0 (6.0) | 3.5 | **Wave C queued**; design system; first working page per U-003 ask; core-surfaces release carrying Wave B's data | P36.72b (HG-11) + P36.73 + **GATE-G6** |
| **11D** Explored and proven | P37 | 75 (415–489) | 64.5 | 4.5 | graphs and explorer; `/quality/`; Wave D (conditional); final release; 13 journeys | P37.65b (HG-11) + P37.68a–d CAP-01 |
| **Tail** | P38 | 10 (490–499) | 7.0 | — | CAP-lite → **GATE-ACCEPT-R11** → REC → DOC → announce review → **GATE-ANNOUNCE** | — |
| **total** | P34–P38 | **299** (post-split; ticket 276 · plan 3 · capstone 11 · gate 5 · reconcile 3 · docs 1) | **275.5** (PLAN 20.0; 9.5 conditional) | **26.5** | | 5 gate markers; 20 never-pre-authorised in-ticket pauses |

\* Separately dispatched live-leg re-runs under the recommended answers (OM-19; `leg_runs` in the CSV). If OM-20 is not
adopted (S5-1's default), the 58 OM-20 rows each become an in-ticket pause: ≈ +29 leg runs.

- **Every row now fits one fresh context** (≤ 1 run; dispatch target = subagent-safe sizing, §8.5). The S3 L rows and the
  nine rows S4 found too big are split a/b(/c/d) **in the CSV**; the three PLAN rows and P34.48 are explicit fan-outs.
- **First dispatch:** row 201 = **P34.1 TC-PIN** (must land before **2026-10-19**, the GitHub `ubuntu-latest` → Ubuntu
  26 runner change; `design/H2-branch-ci.md:113`). Fallback: the seed PR pins `runs-on: ubuntu-24.04` (FEA-16).
- **S0/S1 (113 findings):** each has exactly one disposition. 109 land on seed/11A/11B units (56 owner rows; their
  prerequisite closure is 87 chain rows / 79.5 runs, all in 11A ∪ 11B, + 7 seed units); 3 rest on S5 decisions and stay
  open under their defaults (F-31 → A-4, F-191 → C-3, F-386 → A-3); 1 was already done (F-366). Several owners are
  interim mitigations or default-dependent; §9.4 lists each (COV-06). All 9 S0 ids have a live removal or fix in 11A,
  **and A-0 offers removal-only action now**.
- **The work universe** is 1,159 items with exactly one disposition each — structurally valid by the S1b checker (it
  checks shape, not truth; F-27). The operator's Wave-2, production-fix and "keep me in the loop" asks are traced in
  §9.5 (W2-1…6, PF-1…3, GM-1); T4 adds them to the checker (COV-03).
- **Human work:** no Round-11 HUMAN rows. Rows 184–187 are superseded markers; independent evaluation stays owed under
  trigger **T-EVAL-IND** (L3 §6). Agents contact no one outside the project (U-011).
- **Money:** infrastructure ≈ $95–105/mo after 11A rising to ≈ $123–133/mo after 11D, against the **$300/mo** ceiling
  (U-008); Cloudflare/registrar lines are now in the spend ledger. **Agent spend (new):** ≈ 380–450 fresh contexts ≈
  **95–270 M tokens** over the round (inference, calibrated on Stage P's ≈ 250k–600k tokens per heavy row), reported at
  every check-in; a usage limit was already hit on 09-30 (§10.4; A-2/OD-26).
- **Operator time (re-estimated, FEA-09):** ≈ **25–40 h over ≈ 24 touchpoints in ≈ 10–11 weeks**, several synchronous
  (the P34.46 slot, the P35.61 review, the Wave-C tier bump, four HG-11 sittings); by date in §11.2.
- **Calendar (inference; windows make slips cliff-shaped, not one-for-one — §8.8):** S5 in two sittings ≈ 10-01→10-03;
  seed → GATE-B ≈ 10-05→10-07 (R0); 11A ends ≈ 10-15→10-17; 11B ≈ 10-27→11-02; GATE-G6 ≈ 11-13→11-18; final release
  ≈ 11-27→12-05; tail ≈ 12-03→12-12. Wave A needs R0 ≤ ≈ 10-07, Wave B ≤ ≈ 10-12, Wave C ≤ ≈ 10-20; A-19 decides the
  trade-off in advance.
- **What S5 must decide (99 lines, collected one at a time in two sittings, §4.6):** Part A 24 (incl. **A-0 removal-only
  now** and A-19…A-23), Part B 42, Part C 13, D2 16, S5-1…S5-4. **Own-words and explicit lines cannot be answered by
  the fast path, by `continue` or by silence; their defaults are the conservative non-action** ("not done; stays owed;
  the chain continues around it"). **Thirty-one defaults descope an operator ask (26), add load (3) or stall the chain (2: A-18
  and the push choice OD-27)** — each is shown in §4.4 beside the criterion it disables.

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
| 2026-09-30T16:16Z (GATE-M) and 16:27Z | *"… keep me in the loop"* · *"I want you to just interactively collect and log my answers to the questionairre interactively in Claude one by one"* | OM-17 digests (traced **GM-1**, §9.5); S5 is collected one line at a time (§4.6; COV-17) |

### 1.2 What SIG is for (U-001, agent-drafted, **confirmed by the operator 2026-09-30T17:29:54Z**)

SIG is a public, evidence-first reconciliation layer over the surveillance-transparency ecosystem: it joins independent
public sources into one graph of what capabilities exist where, who controls and can access them, what rules and
contracts govern them, how that changed, and which evidence supports or contradicts each claim. It is built first for
**a local advocate who needs a printable, sourced dossier before a council meeting** (SIG-UI-002), with
**investigative journalists and other organizers** as co-primary audiences (U-002). Landing text: D3 §1 (agent-drafted;
confirmed or edited at S5 via C-4).

### 1.3 Authority chain and gates

`META_PLAN.md` (GATE-M signed 2026-09-30T16:16Z) → Stage-P rows (A–L, all done) → S1a/S1b/S1c/S2 → **this draft (S3)** →
S4 (≥ 3 fresh-context adversarial reviews: coverage, feasibility, truth and safety; closed in `reviews/REVIEW_CLOSURE.md`)
→ **S5 / GATE-P**: the operator ratifies this plan verbatim, every open line is answered or explicitly defaulted, the
universe check is green, and ≥ 3 reviews are closed → Stage B rows T1–T6 (Appendix A) → **GATE-B** (validators + 5/5
CI on the seed PR, orient dry-run resolves row 201, operator approval) → a fresh `orchestrate-build` session resumes.

**GATE-P recording rule (TS-01).** "The operator ratifies this plan" means: GATE-P records (1) the operator's exact
words for each packet line, logged one line at a time with its `date -u`; (2) the sha256 of the plan revision and the
packet revision shown; (3) the list of lines each answer covers. Lines marked **own-words** (OW: A-0.4, A-5, A-6's
waiver sentence, A-7's GL-GATE-07 re-ask, A-23 waivers, B-9's standing-go text, C-1, C-3, C-4, C-5, C-12, C-13, and every
ADR that carries "operator words") are answered by text the operator types, or by an agent draft the operator reproduces
or edits; either way it is stored with the sha256 of the exact text shown and labelled *"agent-drafted, adopted by the
operator at `<date -u>`"* when it began as a draft — never presented as the operator's composition. **Explicit** lines
(EX: publication, rights, Part VIII, the operator's identity, money, production authority, records) need one typed
answer each. Only **batch** lines (BT) may be answered by the fast path. Silence on an OW or EX line takes its
conservative non-action default; it is never recorded as acceptance. If the operator approves on a summary, the record
says "approved on a summary of `<sha>`" (B-4's wording for ACCEPT-R8/R10).

This plan does **not** advance `docs/build/LEDGER.md`, sign or pre-answer any gate, amend the spec, write an ADR, or
open a PR. Stage B does those things, from this plan once ratified.

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
| F-01 | backups were off; restore never drilled at scale (mitigated by Track 0.1) | P34.6 (+ P34.3) |
| F-02 | `/curate/` was public via a hand rsync (mitigated by Track 0.2) | P34.10 |
| F-03 (RI-04) | every page promises a one-click dispute channel that does not exist | P34.17 |
| F-096 (RI-05) | `/visual-language/` asserts fixture facts about real named agencies and a vendor | A-0.3 now (removal-only), else P34.17 |
| F-097, F-131 (RI-01) | personal ArcGIS account handles (and 41 e-mail-shaped owner strings) in public source/target/subject ids, one live `camera_operator` value, the repo tip and the listable `sig-public` 09-27 tree | A-0.1–A-0.3 now (removal-only), else P34.18 → P34.21 (scope widened, §5.1) |
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
| P16 operator identity | **alias first** (C-8 default): no request needing a contact string is sent until the `contact@` alias exists or the operator answers C-8; the need is stopped and recorded. Agent commit authorship is A-21 | connector config review; OM-01 trailer check |
| (new) windows | **OM-19** dated live-leg queue | acceptance rows read the queue |
| (new) autonomy | **OM-20** + OM-10 + OM-18 | GATE packets list exact row ids |

### 3.3 The operating clauses (summaries; full paste block B5 §6.1 and S2 §3.5)

OM-01 one harness + model per round, recorded in a `harness:` key and every run ledger; switches only at a boundary; **every agent commit carries a trailer naming the harness and model, and a G-check fails a Round-11 PR with an untrailered agent commit** (B5 OM-01 verbatim; TS-11) ·
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

**OM-20 (new; S4c wording) — bounded pre-authorisation.** At GATE-B and each sub-round GATE the operator *may*
pre-authorise named production mutations of the next sub-round: exact row ids, each contract's mutation, restore point,
expiry at the next GATE. **Nothing is pre-authorised on silence** (S5-1/S5-3 defaults; A-15 does not carry OM-20). **Never
pre-authorised:** HG-11/Class S promotions and republishes; **any roll that changes a public route's response** (API rolls
P35.57, P36.38, P37.20, P37.42); ING-GO; HG-03 flips; **any hosted sqitch change that alters an existing table or takes an
ACCESS EXCLUSIVE lock** (P34.46, P35.14b; new-table-only changes such as P35.32 may be listed); the bounded apply
(P35.61); **any capture run or archive write touching a Part VIII-screened family** (P37.16a/b, P37.36); irreversible
external deposits (P37.55); the Wave-C tier bump; any spend above $300/mo. A red probe, a failed restore point or a
production read that contradicts a record voids it for the affected rows. Without OM-20 the 58 OM-20 rows become
in-ticket pauses (§8.1). **Class R standing go (B-9):** expires at the next sub-round GATE or after 30 days, whichever is
first, and is void on any ratchet regression, any Part VIII screen change or any new source (TS-13).

### 3.4 Constraints the operator fixed (not re-asked)

≤ $300/mo infrastructure without an explicit go on a shown trade-off (U-008) · no humans besides the operator (U-008) ·
no contact outside the project: no outreach, recruiting, records-request sending or contribution-back posting (U-011) ·
do not block on counsel; no text may imply counsel exists (U-013) · agents never merge, retarget, tag or push `main`
(§7.1) · alerts route to the operator's address · the public dispute contact is the operator's address for now (Q-29;
an operator-accepted risk whose revisit trigger is asked again at GATE-ANNOUNCE, TS-21) · publication is never
pre-authorised, including through the live API (A-20).

---

## 4. Decisions: ratified so far, and what S5 must decide

### 4.1 Ratified (recorded verbatim in META_PLAN §7.1; re-cited, not re-asked)

| decision | answer on record | consequence in this plan |
|---|---|---|
| Q-1 meta-plan; Q-3 worktree; Q-4 Stage-P driver; Q-5 Chrome; Q-6 D1 mode | approved / as recommended | planning ran as recorded |
| Q-2 Track 0.1/0.2; PITR; Track 0.3 | backups + `/curate/` removal approved; PITR delegated and done; MapRoulette key stays stale | §2.2 |
| Q-11 / Track 0.4 | agents do not merge; Round 11 builds on the chain; the operator merges later | §12 |
| Production fixes (received before 17:10:49Z, git `e5725b7b`) | S0 hotfixes, QA-1…QA-10 and `/task/new/` pages approved in principle, specified as Round-11 tickets | 11A rows P34.3–P34.21; A-0 asks separately about the later-found handle S0s |
| Track 0.5 | minimal alerting created | §2.2; P34.4 verifies and codifies |
| Alert routing; Q-29 | the operator's address | P34.4; P34.17 dispute notice |
| U-001; U-002 | confirmed; advocate first + journalists + organizers | D3 §2 journeys |
| U-003 | Stream K; basemap wanted (reverses Round-9 Q8); zero-JS to be re-decided | §5.7; ADRs in §7 |
| Q-8 | no humans besides the operator | §11; rows 184–187 superseded |
| Q-10 / Q-23 (ceiling) | ≤ $300/mo; up to ≈ $1,000 only with an explicit go on a shown trade-off | §10.4 |
| Q-26 | "counsel" = the operator; no counsel; do not block on counsel | §5.10 |
| Q-28 | no recruiting or outreach | LATER-02/03/04 |
| Q-30 | the operator's name + address as the contact string; plan a `contact@` alias | OP-10 |
| Autonomy; launch; coverage priority | maximal autonomy with spend transparency and no outside contact; announce "when the time is right"; US-nationwide Flock/Axon/other vendors | OM-20; GATE-ANNOUNCE; I8 order |
| Q-18 landscape scan | moot (C5 ran) | — |

The labelled agent interpretations under U-002…U-015 (journalist journey primary, Stream L, K14, the $300/$1,000 rule,
no outreach, the alias, B7) are confirmed at S5 through **C-11**.

### 4.2 Part A — decide before the seed (S1c §2 as revised at S4c: **24 lines**)

Class: **OW** own words · **EX** explicit typed answer · (no Part A line is batch). No default below acts on silence.

| line | cls | decision | recommendation | default if unanswered | what the default does to this plan |
|---|---|---|---|---|---|
| **A-0** | EX ×4 | **removal-only, now** (Track-0 style; TS-04/TS-12): A-0.1 repo-tip PR removing the 41 e-mail-shaped owner strings + handle tokens from registry non-id text (operator merges); A-0.2 remove anonymous read of the `sig-public` 09-27 tree (live-fetched prefixes excluded after a read-only listing) + tombstone; A-0.3 remove `/visual-language/` and handle-bearing pages; A-0.4 history line (retention disclosed vs later operator-run rewrite; deposits wait) | **a** on all | **not done**; owed by P34.17/P34.18/P34.21 (≥ 10-13); risk recorded **unresolved** | exposure continues until ≥ 10-13; P37.55's deposit waits for A-0.4 |
| **A-1** | EX | Track-0 exception for the QA-9 restore drill (+ QA-4 TLS alert) before the 10-10 replay | **a** | no exception; risk recorded **unresolved** | drill waits for P34.6 (after the replay) |
| **A-2** | EX | what the $300 ceiling covers; budget alert + billing export now; **agent-spend envelope (OD-26)** | **a** · **yes** · state an envelope | infra-only (U-008's words); alert in P34.5; no envelope → the orchestrator sets `blockedOn` at a usage-limit event | the denial-of-wallet window stays open until P34.5 (A-0.2 closes most of it) |
| **A-3** | EX | DNS to Cloudflare (runbook P34.50 first), R2 $0-egress origin, $50/mo egress ceiling + kill switch, `contact@` routing | **a** | no DNS move; no alias | **descope + cost** (§4.4) |
| **A-4** | EX | **disclosed** single-maintainer, no-counsel posture (members Q-E2-06/07/08/09/10/13/14); MUST-weakening members go to A-23 | **a** | spec unchanged; members stay owed; false claims still removed | governance ADRs not written; GOV ids stay PARTIAL/MISSING; F-31 open |
| **A-5** | OW | robots (GL-GATE-08) re-decided in the operator's own words | **b** at minimum: every rights reservation honoured everywhere (SIG-INGEST-046c) and explicit disallows on vendor platforms (PrimeGov); any US public-body disregard only in the operator's words | **GL-GATE-08 not re-confirmed: every disallow and reservation honoured; the 103 disallowing hosts paused at their next run (P35.1b)** | **descope** (≥ 103 hosts of agenda/CCOPS/procurement evidence) |
| **A-6** | OW | evaluation: supersede 184–187, no Round-11 human rows, auto-collapse only C0–C2, **SIG-EVAL-004 WAIVED for C0–C2 in the operator's own words** | **a** | no automatic collapse; ranged "possible duplicate" counts; EVAL-004 not waived | **descope**: M-1b "not attempted"; B-26 met only with intervals |
| **A-7** | OW + EX | rights stance (Q-19; GL-GATE-07 re-asked in own words) + Tier-1 batches RB-01…07, RB-09, RG1–5, E4 B1/B5/B6, X3 | per-batch lines; **flip only members with captured, permitting terms**; "none captured" → capture first (I7 option b); E4-B1 b | nothing flips; X3 widening lands disabled | **descope**: Waves B/C activate nothing; Wave A activates nothing new |
| **A-8** | EX | withdraw 5,267 NEW-1 rows + restrict `camreg_txdot_rep_tx` (≈ 2,821): **≈ 8,088 public rows** | **yes**; I7-C1 **b** | withdraw + restrict | none (conservative removal) |
| **A-9** | EX | is SIG's use non-commercial? | **b** | b | none |
| **A-10** | EX | D-K2-1: how 969 review-flagged organisations become publishable | **a+b+c** | all withheld | **descope** (§4.4) |
| **A-11** | EX | D-K13-1: global graph as aggregated overviews + egos + `/explore/` | **a** | a (design; nothing ships without a Class S readout) | none |
| **A-12** | EX | D-K0-1: HTML-first page types replace the zero-JS rule | **a** | three islands only | **descope** (§4.4) |
| **A-13** | EX | seed contents (restore-first, correction ADR, guard core, PKG-02; D-R10-MEMORY-1 split; P34+/rows 201+) | **a** | records-only seed | **risk**: seed PR red on six pins; rows renumber +2 |
| **A-14** | EX | apply the B6 skill changes | **a** | OPERATING MODE overrides | weaker mechanical backstop |
| **A-15** | EX | execution model (Claude Code; pause rules). **Does not carry OM-20** | **a** | Claude Code; **pause at every named production mutation** unless an approved OM-20 list covers it | **load** (§4.4) |
| **A-16** | EX | gate authenticity: operator-only signing key, CI-verified; forward rule | **yes / yes** | status quo, recorded as a **disclosed risk** | LATER-15 stays later |
| **A-17** | EX | ratify D3 (order, US-first, co-primary journeys, vendor hosts never fetched, announce gate, CHART-025) | **a** | **D3's order for sequencing only; no spec amendment; no announce rule adopted on silence** | CHART-025 unamended |
| **A-18** | EX | HG-03 for boundary sources `census_gazetteer_tiger` + `natural_earth_10m` (= old B-24) | **yes** | **no** | **stall**: P35.17 → P35.19, P35.45, P35.63 wait; 7 jurisdiction S1s stay open |
| **A-19** | EX | calendar slip trade-off if R0 > ≈ 10-07 (cliff table §8.8) | **a**: let waves slip to their next windows | a (nothing dropped) | later dates |
| **A-20** | EX | may structural spine writes change live-spine API answers before HG-11? | **b**: no — P35.57 first in 11B (its own go at G4), structural writes wait | **b** | one more go; P34.45's ER re-run moves to 11B |
| **A-21** | EX | agent commit authorship: distinct agent author identity vs the operator's name | **a** | b: status quo as a **disclosed risk**; OM-01 trailers enforced either way | — |
| **A-22** | EX | Eyes on Flock mirror (delegated 2026-09-16 review; vendor terms forbid bulk extraction) + D-K2-4 share lists + the Flock/Axon ceiling | **a**: keep on its CC-BY-SA-4.0 basis, delegated review disclosed, no extension | status unchanged, **no extension** (D-K2-4 no) | **descope**: 474,184 share-list edges unused (P37.25) |
| **A-23** | OW ×7 | waiver candidates WV-01…07: GOV-012/013 legal home + defence; GOV-015 board; PUB-008/HG-11 second reviewer; UI-042; GOV-001/002 intake; GOV-008 two-person deletion; LIC-009/INGEST-037 counsel clauses | the operator's words per member | **none waived**; each stays owed and is listed at GATE-ANNOUNCE | disclosure grows; no MUST is silently weakened |

### 4.3 Parts B, C and D2 (S1c §3–§5 as revised at S4c) — **not "safe defaults"**

- **Part B — 42 lines, each with a default.** The defaults are the conservative non-action, a status quo that is
  disclosed, or a design default; **nine lines (17 members) descope something the operator asked for or add load (⚠ in the
  packet; every one is in §4.4)**: B-9 (load), B-11, B-18, B-19 (four members), B-27, B-28, B-30, B-31 (three members) and
  B-44's D-K8-4/D-K4-3. Only six lines are batch (B-5, B-15, B-17, B-22, B-23, B-26); every other B line needs a typed
  answer. Load-bearing lines: **B-1** Wave-0 honesty fixes · **B-2** copy approvals in batches; only the ratified notice
  strings N-1…N-7 (§5.1) ship without per-text confirmation, until GATE-G4 (TS-18) · **B-3** re-key personal handles (old→new
  map restricted) · **B-4** record integrity: supersede `p-17b713`; GATE-G3 superseded; **ACCEPT-R8, ACCEPT-R10 and GATE-G3
  all annotated with B7's facts, no operator addendum about a past state of mind** (TS-08) · **B-5** verdict vocabulary ·
  **B-8** intake email-only until after announcement; response times published only after verbatim confirmation ·
  **B-9** release model, Class R/S, standing go **in the operator's words, expiring** · **B-11** Cloud SQL cap 40 GB,
  pre-grow 25 GB, one ING-GO per wave, scope = core + droppable Wave D, targets under flipped sources need a line
  (I8-Q4) · **B-15** GitHub settings · **B-16** planning branch local until T6, **push waits for OD-27** · **B-18** owed
  operator actions · **B-19** transparency · **B-22** 52 K-row design defaults · **B-26** dedup is an announce criterion ·
  **B-30** search memory (+$3/mo) · **B-31** maintainer checks; `/quality/` built but not published until answered ·
  **B-34** non-US database-right lines not flipped · **B-41** E4 rows (**R4a–c now "capture terms, not flipped"**, COV-07) ·
  **B-44** six Part VIII/publication K rows split out of B-22.
- **Part C — 13 confirmations** (C-1 readout provenance **OW**; C-2 harness history; C-3 the operator's own words for
  counsel, the 09-28 deferral and robots **OW**, recorded at S5's `date -u`; C-4 positioning text **OW**; C-5 who runs SIG
  on About **OW**; C-6 repo stays public; C-7 the real monthly bill; C-8 alias first; C-9 no intake secret value used;
  C-10 local DBs with L44–52; C-11 interpretations; **C-12 withdraw-instead-of-fix list OW** (COV-04); **C-13 does
  ACCEPT-R10's acceptance stand OW, dated** (TS-08)).
- **D2 — 16 reactions** (agree/disagree + priority). Default: no reaction recorded.

### 4.4 Defaults that stall, descope or add load — each beside the criterion it disables

Every success criterion in §13.2 is stated **conditionally on the recommended answers**. If a line below is left at its
default, the criterion is reported **"not attempted (default <line>)"** in P38.2's accepted-deviations list, never as
MET, and GATE-ACCEPT-R11 lists it. The last column is mechanically checked (`acts_on_silence = no` for every OW/EX
default; `docs/build/logs/next-phase/S4c/check_silence.py`, folded into the S1b checker at T4).

| # | default (line → member) | kind | criterion or ask it disables | rows affected | acts on silence? |
|---|---|---|---|---|---|
| S1 | **A-18** → "no" | **stall** | correctness: no mixed-scheme dossiers; `unresolved` not a dossier; every state + DC has a dossier; first model release | P35.17, P35.19, P35.45, P35.63 and everything after | no |
| S2 | **B-16 / OD-27** → no answer | **stall** | GATE-B: the seed branch cannot be pushed, so no seed PR | T6, GATE-B | no |
| 1 | **A-7** → nothing flips; per-member terms capture | descope | coverage: 154 Tier-1/widening candidates live or dispositioned; 40/51 states + DC; 28/29 classes | P36.4–P36.12, P37.2 | no |
| 2 | **A-7 / I7-X3 + B-11 / I8-Q4** → widening not confirmed | descope | Wave A's ≈ 18k widening claims; Flock/ALPR targets under flipped sources | P35.11 (lands disabled) | no |
| 3 | **A-5** → GL-GATE-08 not re-confirmed | descope | ≥ 103 disallowing hosts (102 PrimeGov + oscn.net) paused: agenda/CCOPS/procurement evidence | P35.1b, P35.8, P36.1a | no |
| 4 | **B-11 / Q-23** → 25 GB cap, Wave C waits | descope | the national ALPR layer from its origin (D3 §3(b)) | P37.2 legs stay queued | no |
| 5 | **B-11 / I8-Q5** → core only | descope | Wave D dropped: I7 projects 40 of 51 states, 13 of 36 thin cities, 28 of 29 classes (vs 46, ≈ 20–25, 29 with Tier 2); U-007 "expansion … to maximal degree" | P37.47–P37.54 | no |
| 6 | **A-12** → three islands only | descope | U-003.2/.3/.6 partly; K0 budgets criterion changes | P36.20, P36.21, P36.40, P36.57, P37.26, P37.27, P37.29, P37.61 | no |
| 7 | **A-10** → organisations withheld | descope | J2; Organizations hub; organisation labels/edges | P35.29–30, P36.41–42b, P37.22–28 | no |
| 8 | **A-3** → no DNS move | descope + cost | U-003.9/.10 downloads; J1 "rows in ≤ 3 clicks"; basemap on GCS (+$4–41/mo) | P35.5, P36.33, P36.50, P36.53, P36.68, P37.36 | no |
| 9 | **A-3 alias member (OD-04)** → no alias | descope | U-014 `contact@` alias not created; under C-8 "alias first" no contact-string request is sent | OP-10; later EDGAR/API sign-ups | no |
| 10 | **A-22 / D-K2-4** → no | descope | U-007 "rich … Flock" via the 474,184 share-list edges; the state × state access matrix | P37.25 | no |
| 11 | **A-6** → no collapse | descope | M-1b "not attempted"; B-26 met only with intervals; "the dedup is published" with intervals only | P35.46–47, P37.44 | no |
| 12 | **B-30 / D-K3-5** → no | descope | U-003.3 search v2 API stays staged | P36.38, P36.71 | no |
| 13 | **B-19 / D-J3-6** → no snapshots | descope | J4 "cite it durably"; permalinks never pin (F-07/F-099) | P36.66b | no |
| 14 | **B-19 / D-J3-11** → no status lane | descope | ingestion heartbeat on `/status/` | P36.43 built, not scheduled | no |
| 15 | **B-19 / D-J3-1** → no raw bytes | descope | Wave-2 "download the raw data" (W2-5); U-003.9 | P37.36 built, not exposed | no |
| 16 | **B-19 / D-J3-2** → no run logs | descope | Wave-2 "see ingestion logs/metrics/timestamps" (W2-6); U-003.9 "ingestion metrics and metadata"; U-003.10 "ingestion history" | P35.33, P36.43, P36.46, P36.47, P36.48, P36.69 | no |
| 17 | **B-27 / D3-Q4** → no peer links | descope | accepted K12b idea I-24; the §3.1 invariant "peers are linked, not rebuilt" | dossier template (P36.55) | no |
| 18 | **B-28 / D-K3-7** → agent writes the held-out set | descope | U-003.3's "held-out ≥ 80 % top-3" measured on an agent-authored set (labelled) | P36.32 | no (labelled) |
| 19 | **B-31 / Q-L3-3** → no OPCHECK | descope | the disclosed maintainer check per Class S release (U-006 confidence) | P35.49 | no |
| 20 | **B-31 / Q-L3-5** → `/quality/` not published | descope | §13.2 #2 "`/quality/` live with every check"; S2 11D exit 5 | P37.45 | no |
| 21 | **B-31 / Q-L3-6** → C0/C1 only | descope | C2 collapse off | P35.46 | no |
| 22 | **B-18 / D-SOURCES.7-2** → keys not registered | descope | keyed US 511 cameras (U-007 coverage) | P37.12 dropped (OP-13) | no |
| 23 | **B-44 / D-K8-4** → `/evidence/` empty state | descope | U-003.8 shows nothing until real captures bind | P36.60 | no |
| 24 | **B-44 / D-K4-3** → state/country pages only | descope | O1 "who runs what in my county or city"; county/place dossiers | P36.34, P35.45 | no |
| 25 | **C-12** → not accepted | descope (disclosed) | U-003 "everything advertised should actually work": six withdrawn features reported "withdrawn, not accepted" | P36.72a, P37.68d, GATE-ACCEPT-R11 | no |
| 26 | **C-5** → About omits "who runs SIG" | load | GATE-ANNOUNCE item "About text written by the operator" | P36.64, GATE-ANNOUNCE | no |
| 27 | **A-4 / A-23** → spec unchanged, nothing waived | descope | outcome 4: governance contradictions stay owed (F-31 open) and are listed at GATE-ANNOUNCE | SEED-11/12, GATE-ANNOUNCE | no |
| 28 | **S5-1 (OM-20 not adopted) + A-15** | load | ≈ 58 more in-ticket pauses (≈ +29 leg runs) | every OM-20 row | no |
| 29 | **D-G3-3 (B-9)** → no standing go | load | every release Class S; P36.70 cannot rehearse a Class R | P36.70, cadence cuts | no |
| — | **A-13** → records-only seed | risk | seed CI green; numbering | SEED-02/03 become P34.0a/b | no |
| — | **A-0 / A-1** → not done | risk (unresolved, not accepted) | exposure until ≥ 10-13; no drill before the 10-10 replay | P34.17/18/21; P34.6 | no |
| — | **A-19 / OD-26** → slip / no envelope | calendar | dates per the cliff table; pauses at usage-limit events | all | no |

**Chain edges into operator or later rows (COV-02):** P35.38 → OP-11 is now **soft** (only if Q-E2-03 = a; SAFE-06 moves the
contact without a purchase; F-184 rehomed to P35.38); P34.27 → OP-18 is soft (only C-13's dated answer); P37.12 → OP-13 is
a conditional row recorded as dropped under its default (row 22). No other chain row depends on an operator or later row.

### 4.5 New S5 lines (S5-1…S5-4), each with a default (COV-09)

| line | decision | recommendation | default if unanswered |
|---|---|---|---|
| **S5-1** | ratify **OM-19** and **OM-20** as written in §3.3 (S4c wording) | ratify both | **OM-19 adopted** (it only queues and pauses); **OM-20 not adopted**: nothing pre-authorised, every named mutation an in-ticket pause |
| **S5-2** | ratify the **check-in GATE packet** (budget · publication · rights · OM-20 list · status); **`continue` answers only batch lines**; every OW/EX line in a packet (publication, rights, Part VIII, identity, money, OM-20 list) needs its own verbatim line; **descoping defaults are listed first**; the OM-20 list is never approved by `continue` (TS-01, TS-02, FEA-09) | ratify | ratified as written (it only narrows what `continue` answers) |
| **S5-3** | the **GATE-B OM-20 list for 11A** (exact rows; expiry at GATE-G4): P34.3, P34.4, P34.5, P34.6 (drill clone), P34.21a (attribution backfill), P34.24b (clone rehearsal), P34.40 (dark LB/nginx), P34.42a/b (IAM), P34.43 (execution host + logins), P34.44b (nightly quality job), P34.49 (Part VIII sealing). **Excluded (in-ticket gos):** P34.17, P34.21b, P34.46; P34.45's ER re-run (A-20, FEA-19) | approve verbatim | **none**: each named mutation is an in-ticket pause (≈ 13 in 11A) |
| **S5-4** | confirm **CF-06** (US-first: ACQ-23a/b leave the round; Wave C US + territories). CF-15 (RI-01 rides republish #2) is **replaced** by A-0 and B-3 (TS-04) | confirm | US-first adopted for sequencing (it expands nothing); RI-01 timing follows A-0 |

### 4.6 How S5 is collected (COV-17, FEA-09)

The operator asked (2026-09-30T16:27Z) for answers to be collected *"interactively … in Claude one by one"*. S5 is
therefore asked **one line at a time**, each answer logged verbatim with its `date -u`, in **two sittings**: sitting 1 =
Part A + S5-1…S5-4 (≈ 1.5–2.5 h; A-0 and A-1 first because they are time-critical); sitting 2 = Parts B, C and D2
(≈ 1.5–2.5 h). A batch (BT) line may be answered together with other BT lines; OW and EX lines never. GATE-P is recorded
after sitting 2 under the §1.3 rule. A-0's members, if answered "a", are executed by the planning orchestrator as
Track-0-style actions, each with its own go, pre-state, restore point and probe (META_PLAN §6 Track 0).

---

## 5. Themes (problem → evidence → design → requirements → rows → acceptance)

Runs per theme are chain-row totals from the post-split `data/round11_plan.csv` mapped to S1a's `theme` column (275.5 in
all after S4c: UX core 62.0 · transparency 29.0 · sources 28.5 · data correctness 24.5 · release/ops 23.5 · safety and
honesty 20.0 · PLAN contract authoring 20.0 · Round-10 activation 19.0 · UX explore 17.5 · memory truth 11.5 ·
acceptance/tail rows 8.0 · debt 5.5 · governance 4.5 · CI 2.0). The row/run counts in the §5.x headings below are S3's
pre-split figures, kept for traceability; the CSV is authoritative.
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
  and the P34.19 withdrawal → **republish #1** P34.17 → handle re-key P34.18 + evidence empty-state truth P34.20 →
  **attribution re-export + publish-time attribution gate + republish #2** P34.21a/b (hosted backfill ≥ 2026-10-13T12:00Z).
  API honesty code P34.25 deploys with P34.46 (≥ 10-14). Operations: P34.3 data protection (incl. bucket versioning — the
  restore point for both republishes, `live:P34.3`), P34.4 alerts that reach a human (+ TLS-expiry alert), P34.5 budget
  alert at $300 + billing export + a spend ledger that includes Cloudflare/registrar lines, P34.6 restore drill at scale,
  P34.49 **Part VIII at-rest audit** (TS-07), P34.50 DNS cut-over runbook (FEA-08). Later safety rows: P35.3
  production-truth probes; P35.28 officer-naming gate (default deny) and P36.15 redaction pipeline and **P35.66 residential
  demotion** — all three now land **before** Wave B's activation P36.12 (TS-07); P35.38 identity base and crawler contact.
- **A-0, removal-only now (TS-04, TS-12).** If the operator answers A-0 = a, the planning orchestrator runs each member
  as a Track-0 action with its own go before Round 11 starts: A-0.1 repo-tip PR (non-id registry text; the operator
  merges); A-0.2 anonymous read of the `sig-public` 09-27 tree removed (prefixes the live site fetches excluded after a
  read-only listing) + tombstone note; A-0.3 `/visual-language/` and handle-bearing pages removed. If unanswered,
  nothing is removed now and the exposure is recorded as **unresolved** until P34.17/P34.18/P34.21.
- **Republish #1 (P34.17) ships only text true of the 09-27 data (TS-03).** It introduces no claim that is not yet true.

  **Table R1 — exactly what republish #1 removes or changes**

  | # | removal or change | finding(s) | new text (all confirmed verbatim or from N-1…N-7) |
  |---|---|---|---|
  | R1.1 | fixture two-reviewer "Releasable" review on `/editorial-standards/` removed | F-183 (S0), F-107, F-198, F-201 | N-1 |
  | R1.2 | every "one-click dispute" / "anonymous" promise removed; dispute page names the operator's address | F-03 (S0), F-098 | operator-confirmed dispute notice; response times only if OD-08 is confirmed |
  | R1.3 | `/visual-language/` fixture facts removed (if A-0.3 did not already) | F-096 (S0) | none |
  | R1.4 | "human-verified" holdout claims and P/R/F1 1.000 removed | F-06, F-108, F-133, F-192 | the past-tense text below; **no `/quality/` link** (it exists only at P37.45) |
  | R1.5 | "editorial board" and "counsel" wording on site pages removed | F-185, F-189 (site part) | N-1 where a process is described |
  | R1.6 | "reproducible" dropped; "permalink" → "link" until `/s/` pins exist (C6 QW-5, owner P34.11) | F-07, F-099, F-390, F-399 (wording only) | none |
  | R1.7 | site-wide totals shown as dossier figures removed from "How we know this" | F-05, F-109, F-132 | none |
  | R1.8 | pages and list entries of the P34.19 withdrawn sources removed (≈ 8,088 rows with the TxDOT restriction) | J4 NEW-1 | N-3 |
  | R1.9 | `demo_*` task pages stripped | §7.1 PF-3 | none |
  | R1.10 | `/status/` notice for what stays wrong until P34.46 | F-130 (S0), F-189 (API terms) | N-7 |

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
  | misattribution to "DeFlock community map"; 61,603 rows with required attribution empty; map credits "SIG contributors" (F-387 S0, F-111, F-138, F-186, F-405, F-531) | republish #2 (P34.21b, ≥ 10-13T12:00Z backfill) | A-0.2 removes anonymous access to the misattributed downloads; republish #1 replaces wrong per-source credits with N-4 |
  | personal handles in ids, tiles and one `camera_operator` value (F-097/F-131 S0) | P34.18 → P34.21b (`camera_operator` fully in P35.26) | A-0.1–A-0.3 if answered; else unresolved |
  | API dossier endpoint returns 25 unrelated subjects; `/terms` names a board and counsel (F-130 S0, F-189) | P34.46 (≥ 10-14) | N-7 on `/status/`; no API hotfix (B-7) unless step 1 slips past ~10-21 |
  | the 5,267 forbidden-terms/NC/ND/demo rows in downloads and tiles | P34.21b re-export | pages/list entries leave in republish #1 (R1.8); A-0.2 covers downloads |
  | unpinned permalinks (F-07/F-099/F-390/F-399) | real pinning P36.66b (11C), under D-J3-6 | wording fixed in republish #1 (R1.6) |
- **Requirements.** SIG-OPS-001…004 (restore drill, survivability, route allow-list, single publish path), SIG-OPS-006
  (alert delivery), SIG-OPS-009 (cost truth), DRAFT-OPS-2 (fixture sentinels), the G2 §6 claim rules; SIG-PUB-002/004/005/013
  (at-rest audit, residential demotion); SIG-PUB-008 and SIG-UI-042 are waiver candidates (A-23), never silently amended.
  See §6.
- **Acceptance (11A exit, live layer, P34.47).** Every S0 has a live removal or fix: restore drilled with timing and
  deletion protection on; publish path refuses `/curate/` and an absence probe confirms; honest dispute notice; fixture
  pages removed; API honest (P34.46); attribution correct in downloads, API and map behind a publish-time gate. **RI-01
  closes only when** a crawl of the site, the API, the tiles, the `sig-public` listing and the repo tip finds 0 entries
  of the handle list (kept gitignored at `docs/build/logs/next-phase/C3/personal_like_ids.txt`) in source ids, target
  ids, subject/claim/permalink ids, `camera_operator` values and tile properties (TS-04). A test alert has been received;
  the $300 budget alert and billing export are live. A live probe finds 0 instances of the full L3 §4.5 not-claimable
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
  - *Skills (out of repo, operator-applied):* B6's 25 proposals; Tier A before Stage B, Tier B-must before row 201
    (OP-01…OP-04; A-14).
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
  exact bounds; agent review in two blind contexts, labelled and never gating (P35.48); a disclosed, non-independent,
  blind-first **maintainer check (OPCHECK)** by the operator per Class-S release (P35.49; OP-17; B-31); independent human
  evaluation **not planned** — owed under T-EVAL-IND (§11). The honest evaluation posture lands as code in 11A and its ER
  re-run runs in early 11B after P35.57 (A-20); the public posture text ships in republish #1 only in its past-tense form,
  and the present-tense merge sentence ships with P35.63 (TS-03, TS-14). Public
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
  100 %; dossier counts ≤ 1.02× lineage roots (or ranged intervals if A-6 defaults) [up to 2.25×]; contradiction recall 1.0
  on the synthetic set; byte binding 100 % for sources re-run in P35.61 [0/2.78 M]. Round: CONF-14 (P37.67) re-measures L2
  on the final release; every L3 target met or each miss names its fixing row; **M-1b: under A-6 = a, a sampled lower
  bound per declared namespace is reported as measured (no certification figure is claimed — "0.98" is L3's forbidden
  certification number); under A-6's default nothing is collapsed, so M-1b is "not attempted (default A-6)"** (TS-10);
  `/quality/` live with every check, failing and ratchet checks shown (B-31; under Q-L3-5's default it is built, not
  published). Byte binding covers sources re-run in P35.61; **the ≈ 2.78 M legacy claim–evidence links stay zero-byte
  under the insert-only spine and are labelled "capture not bound" (F-522 residual; COV-06).**

### 5.5 Sources and coverage — Stream I (33 rows, 27.5 runs; US-nationwide Flock/Axon focus)

- **Problem.** Material blind spots: Flock only via one mirror (≈ 23 % of networks), Axon/Fusus/RTCC nothing, 22 states
  without a dossier, ATE/drones/FRT/forensics thin, the national OSM ALPR layer only as a stale republished copy.
- **Evidence.** I1 (14 blind spots), I2 search protocol, I3–I6 + I9a/b (logged queries, saturation), I7 (694 consolidated
  candidates; Part VIII preflight; rights lanes), I8 (acquisition plan, `data/acquisition_plan.csv`); F-329, F-330, F-366,
  F-374, I8 NEW-1…8; U-007.
- **Design (I8, scoped by D3 and CF-06).**
  - *Rules:* availability is never rights clearance; every activation follows its HG-03 line and a verbatim **ING-GO per
    wave**; a Tier-1 batch flips only members whose terms are **captured verbatim** and permit it ("none captured" stays
    gated; A-7, TS-06); **no Flock or Axon fact whose only provenance is a vendor host *or a mirror of one*** — such facts
    come from agency pages, procurement records and statutory reports (A-17/D3-Q3; I7-C4; A-22 decides the existing
    Eyes on Flock mirror); robots and rights reservations per A-5 (default: honoured everywhere); Part VIII-flagged
    candidates stay metadata-only unless screened (B-32), and **the residential demotion (P35.66), officer-naming gate
    (P35.28) and redaction (P36.15) land before Wave B activates, and the B-32 screen lanes S4/S6/S7 are implemented and
    verified before their families activate** (TS-07); non-US database-right lines are not flipped
    this round (B-34; E4-R4a–c now "capture terms", COV-07); express "do not redistribute" terms are withdrawn (A-8).
  - **The ceiling the terms impose (TS-06).** Flock's portal and API terms forbid bulk extraction and Axon's forbid
    robots, spiders or page-scrapes. So Flock and Axon coverage can lawfully go as deep as agencies, procurement records,
    council matters and statutory reports disclose — and no deeper. Flock's own customer, sharing and audit data and Axon
    Fusus/Community Connect stay dark. **Axon facts are thin by design** (federal awards via USAspending/BWC ALN 16.835 in
    P35.9, RTCC/Fusus council matters, programme-level PCAM counts); the operator weighs this at A-17/A-22.
  - *Enablers first (P35.6–7):* acquisition plumbing and harness with I8's preconditions — the reviewed ArcGIS rate applied,
    a second cadence batch round, new triggers created disabled, the 63 truncated source ids fixed, aggregation for ATE
    violations — then registry label fixes M1–M7. The scheduler of record and cron lint (P35.1) precede them (CF-09).
  - **Wave A** (widening, 43 of 46 units, ≈ 18k claims): Legistar keyword-filtered paged matter pass, USAspending/CROL
    vocabulary, the 2026 state ALPR statute seed (P35.8–10) → activation P35.11 (live 2026-10-19→10-23, 14:00–20:00Z).
  - **Wave B** (Tier 1, 108 candidates, ≈ 89 new registry rows, ≈ 250k claims) — **re-sequenced into 11B (FEA-02)**:
    robots/opt-out register and rights-reservation state before any new host is fetched (P36.1a; the crawler text P36.1b
    follows in 11C); ATE concept (P36.3); eight family tickets (P36.4–P36.11, P36.9 split a/b); then P35.28, P36.15, P35.66;
    then activation **P36.12, dispatched in 11B with ING-GO-B collected at GATE-G4**, its legs run from the OM-19 queue
    2026-10-26→11-05 (one family a day; the small ACQ-11 and ACQ-15 may share a day). The edge from Wave A (P35.11) is a
    **sequence** edge (one manual job at a time), not `live:`. **Wave-B data publishes in P36.72b's Class S release**
    (≥ 11-13T12:00Z), which becomes the second activated release — no separate Wave-B release cut. The owed rights batch
    P36.2 moves to 11C.
  - **Wave C:** OSM becomes the **origin** of the national ALPR layer — code P37.1 and activation P37.2 now sit at the
    head of **11C** (FEA-02), ING-GO-C + Q-23 collected at GATE-G5, so the legs (pre-grow → tier bump after its go → run →
    24 h soak → revert) are queued before GATE-G6 for 2026-11-16→11-20, US and territories only; Wave-B's new monthly crons
    are set to fire after 11-20 (FEA-15). P37.2's edge to P36.12 is sequence-only.
  - **Wave D (conditional, I8-Q5):** eight Tier-2 family rows P37.47–53 + activation P37.54 (windows 11-23→12-04 and
    12-14→12-18; droppable as a whole). ACQ-23a/b (international portals, OGC WFS) leave the round (LATER-09).
  - *Source ops:* SAM.gov sweep resumes (P37.11); keyed US 511 wiring after key registration (P37.12, conditional on OP-13);
    registry completeness + recurring discovery sweep (P37.13); statute-seeded records leads (P37.14); scheduled parser
    canary (P37.15); closeout P37.66.
  - *Capacity:* ≈ 1.5 M new claims (≈ 3.8 GB; OSM ≈ 74 %); autoresize cap 40 GB, pre-grow to 25 GB before Wave C
    (≈ +$1.70/mo); permanent scale-up only on a named trigger (LATER-08).
- **Requirements.** SIG-INGEST-037 amendment + §26 rule 7 opt-out register + SIG-INGEST-046c reservation refusal (A-5;
  P36.1); SIG-CONF-D09 upstream reconciliation; SIG-CHART-025 amended to US-nationwide multi-vendor breadth with per-class
  and per-geography quality labels (A-17).
- **Acceptance (P37.66 ACQ-28, live).** The national ALPR layer comes from its origin; every US state and DC has a
  dossier; **OSM ALPR, Eyes on Flock (as A-22 decides) and Atlas vendor data reach place and entity pages (D3 §3(b),
  restored; COV-05)**; all 154 Tier-1 and widening candidates are live or dispositioned; 40 of 51 states + DC and 28 of 29
  technology classes verified live; 11–12 of the 14 I1 blind spots moved. **Flock / Axon / other vendors trace (COV-05):**

  | vendor | rows | acceptance threshold (I8 §9 projections; agency, procurement and statutory origins only) |
  |---|---|---|
  | Flock | P35.8 (Legistar matters), P35.9 (awards), P36.5 (agency ALPR/Flock layers incl. FDOT inventory 407 + removal ledger 523), P36.8–P36.9b (statutory operator lists: WA AGO 76 agencies, MN BCA, NE/VT/IL reports), P36.11, P37.1–P37.2 (national ALPR origin, 154,814 objects), P37.25 (share lists only if A-22 = b) | agency-origin layers for 14 agencies in 11 states; Legistar Flock matters in ≥ 8 cities; the national layer from its origin; every Flock entity link dated and sourced |
  | Axon (thin by design) | P35.9 (USAspending recipient slice, BWC ALN 16.835), P35.8 + P36.11 (RTCC/Fusus council matters: Columbus, Louisville, Detroit), P36.7 (programme registers) | Axon present as an entity with dated, sourced agency links from federal awards and council matters in ≥ 3 cities; no vendor-host fact |
  | Motorola/Vigilant and others | P35.8, P35.9, P36.5, P36.7, P36.10 | each with dated, sourced agency links |

  P37.66 reports per-vendor agency counts by state. **Stays dark by design or terms** (I8 §9): Flock's own customer, sharing and audit
  data; Axon Fusus/Community Connect; MS, WY, MT, AS, MP, tribal nations; EDGAR; records and court corpora; all
  person-level data.

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
  301s to `/sources/`. The repo is public, so commit hashes are shown (C-6).
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
- **Design (K13; K0 page types if A-12 = a).** Header: **Places · Explore (Map, Graph, Search, Disagreements) ·
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
  rather than fixed this round** (the operator accepts or rejects the list at C-12): one-click dispute (honest notice +
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
  on an **agent-authored** held-out set" unless the operator writes it (OP-21; TS-20); K0 budgets and axe pass on real
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
  **V1–V15** (V15 = L3's graph quality); Class R (standing go, routine) vs **Class S** (candidate-specific signed readout,
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
- **Acceptance.** 11A exit 5: G2 step 1 live, after the 10-10 replay was read back. 11B opens with **P35.57** (API
  release parity, its own go collected at G4) so no 11B structural spine write changes a public API answer before HG-11
  (A-20 = b); 11B exit 1: P35.63 promoted (§5.8). Research dossiers become public only after live captures (B-7), and those
  captures (P37.16a/b) require the per-family Part VIII sign and depend on P35.31's capture-tier fix (TS-07).

### 5.10 Governance and records (5 rows, 4.5 runs; plus seed ADRs and records)

- **Problem.** Spec MUSTs contradict operator decisions; public and repo text implies an editorial board, counsel and
  independent review that do not exist; consequential records rest on tentative words.
- **Evidence.** F-31, F-185, F-189, F-190, F-191, F-195, F-199, F-471; E1 (contradictions), E2 (22 memos + A-1), E3
  (human-work options), E4 (22 rights decisions); U-011, U-013; B5 §4.
- **Design.** The A-4 posture package (disclosed single maintainer, no counsel) by ADRs (§7); any MUST it weakens is a
  waiver candidate decided in the operator's own words at A-23 (TS-05); repo honesty corrections (governance doc,
  `sources.toml` "counsel" reviewer values → "the operator's own determination (no counsel)") (P34.16) — **P34.16 has no
  live stage, so public `main` keeps the false governance text until the operator merges; the OP-08 merge sitting is a
  safety item, not only housekeeping (TS-09)**; ADR-086 and ADR-106 get appended `Qualified by ADR-167 (<date -u>)` status
  lines at T1; ADR-167 and every release manifest carry E2's label text once the operator confirms it verbatim: *"No
  lawyer's written opinion has been obtained; nothing here states that this publication has been cleared by counsel."*
  (E2:569-571; agent-drafted); robots/opt-out register
  and crawler policy text (P36.1); registry rights-record hygiene (P37.6); a **public editorial decision log** under interim
  single-maintainer authority (P37.7); legal-demand posture + published counts, warrant canary declined (P37.8; SIG-SEC-003).
  Records (seed): the C-3 confirmations in the operator's own words, recorded at S5's `date -u` as present statements
  ("I now confirm …"), never as 09-16/09-28 decisions (TS-19; a G4 lint test); ACCEPT-R8, ACCEPT-R10 and GATE-G3 annotated
  with B7's facts (B-4, TS-08); the restored GATE DECISIONS block annotated (SEED-06); the go-live spec records GL-GATE-06…08
  only as dated, annotated records — blanket, delegated or tentative as the case is — unless the operator re-decides them in
  their own words (Q-E2-19; TS-06, TS-08).
- **Requirements.** SIG-PUB-008 stands (nobody named); **waiver candidates (A-23, own words each, else owed):**
  SIG-GOV-012/013, SIG-GOV-015, the HG-11 second-reviewer role, SIG-UI-042, SIG-GOV-001/002, SIG-GOV-008, the counsel
  clauses of SIG-LIC-009/SIG-INGEST-037; non-weakening amendments: SIG-SEC-003, SIG-LIC-004 + HG-03 text, SIG-INGEST-037/§26
  opt-out register, SIG-CONTRIB-012/013/030a (timing → later-phase), SIG-CHART-025 (only if A-17 = a).
- **Acceptance.** 0 counsel/board/independent-review claims without basis (11A live probe and P38.1); every governance
  ADR carries the operator's words where the decision is theirs; `/editorial-standards/` reads "not yet performed".

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
`BUILD.sh`, from this ratified plan (OM-03).

### 6.3 Amended existing ids and sections

| id / section | amendment | source |
|---|---|---|
| SIG-ENG-031 | phase completion requires green PR checks (incl. data quality); the coverage matrix is the traceability matrix; risk register per round | DRAFT-ENG-5 |
| SIG-ENG-039 | ADR index fields and superseded status; `check_spec_src.py` in `make docs-check` and CI | DRAFT-ENG-4; F-32 |
| SIG-ENG-004 | align the DoD with §8.3 → N/A-RATIONALE | F2a |
| SIG-INGEST-004; SIG-ONTO-060 | binding-version clause (NEW-7); scope list | F2a |
| §42.3 | physical ODbL table → export-boundary compartments | RISK-P4-07 |
| SIG-EXPORT-012, SIG-RECON-058 | drop ADR-092 compute-on-read (superseded by ADR-099/101) | F-34 |
| Appendix F | missing row for ADR-072 | APPENDIX-F-01 |
| SIG-EVAL-004 | waiver note → the derivation-not-identity ADR (C0–C2 only) | L3 §7; A-6 |
| SIG-IDENT-028; §55.9; SIG-EVAL-005/006/007 | census-driven auto-demotion for copy tiers; Round-11 disposition paragraph replacing the H4/P32.22a/H5/P32.23 path with T-EVAL-IND; owner re-home notes | L3 §7 |
| SIG-PUB-008 | stands; note: nobody is named; web gate default-deny. The HG-11 second-reviewer role is a waiver candidate (WV-03), not an amendment | A-4 (Q-E2-06); E2 H-9; A-23 |
| SIG-GOV-012/013/015 | **waiver candidates, not amendments** (TS-05): interim individual legal home (WV-01); interim single-maintainer editorial authority + public decision log (WV-02); each only in the operator's own words, else owed | A-23 |
| SIG-SEC-003 | demand-response posture + published counts; canary declined | A-4 |
| SIG-LIC-004/009 + HG-03 text | the rights basis the operator states, with guardrails (per-member terms capture; express prohibitions withdrawn; NC facts-only). Dropping LIC-009's counsel clause is a waiver candidate (WV-07) | A-4 (Q-E2-13); A-7…A-9; A-23 |
| SIG-INGEST-037, §26 rule 7, SIG-INGEST-046c | robots per A-5's answer in the operator's own words (default: disallows and reservations honoured everywhere); opt-out register; reservation refusal; dropping INGEST-037's counsel clause is WV-07 | A-5; A-23 |
| SIG-CONTRIB-012/012a/013/030a, SIG-GOV-024, SIG-CHART-033 | outreach timing: owed later-phase obligation, trigger "operator authorises outside contact" | Q-E2-12 a; U-011 |
| SIG-CHART-025 | US-nationwide multi-vendor/multi-technology breadth with per-class and per-geography quality labels — **only if A-17 = a** (default: unamended) | A-17 |
| SIG-UI-042 | the G2 H-1 gate move is a waiver candidate (WV-04); until answered the open findings ship as known issues and the move is an accepted-deviation candidate | A-23 |
| SIG-UI-036, SIG-UI-050 (+ `AGENTS.md` gotcha 6, `web/AGENTS.md` gotcha 1) | zero-JS-on-content-pages → HTML-first page types (only if A-12 = a; K0 §7 text) | A-12 |
| SIG-UI-044 | chrome wording budget | D-K14-6 (B-22) |
| SIG-METRIC-007, SIG-EVID-009, SIG-UI-035, SIG-EXPORT-002 | transparency amendments | J3 §11 |
| §55 landed-status text; Appendix G | true dates for the Round-10 events (B1 §5.3) via one new App-G row | B1; ADR in §7 |

### 6.4 Verdict vocabulary (B-5; F2b §2; applied by T4)

`MET` · `MET-DIFFERENTLY(ADR|RISK)` · **`MET-ENGINEERED(D-id…)`** (engineering done; a live, operator or human leg owed in
an OPEN/PARTIAL DEFERRALS row) · `PARTIAL` · `MISSING` · `AT-RISK-INTEGRATION` · **`WAIVED(ADR)`** (operator's words,
risk accepted, compensating controls, revisit trigger) · `N/A-RATIONALE`. Four additive matrix columns:
`required_domain`, `achieved_domain`, `owed_legs`, `accepted_scope`. `check_coverage_matrix.py` enforces the grammar and
the cross-checks (no MET with an owed leg; MET-ENGINEERED only with an open leg; WAIVED only with an accepted ADR and no
open leg; routing to a landed ticket is an error; expected counts derived from the spec, no pinned 715). Every verdict
change is written as a `coverage-assessment/1` event. Acceptance packets report the **two-sum headline** per status
layer (MEM-10's contract), never "N MET" alone.

### 6.5 Waivers — and what is deliberately *not* waived (rewritten at S4c, TS-05)

A spec amendment that removes or weakens a MUST **is a waiver** (T4 adds this rule to the S1b checker). Every waiver needs
the operator's own words, compensating controls and a revisit trigger, recorded as `WAIVED(ADR-nnn)`; anything not waived
stays owed and is listed on GATE-ANNOUNCE's "spec MUSTs unmet at launch" list, which the operator signs verbatim.

| candidate | S5 line | what the plan does instead of meeting it | default |
|---|---|---|---|
| SIG-EVAL-004 lower bound, **C0–C2 tiers only** | A-6 (OW) | derivation, not identity (ADR-153); example sentence: *"I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes."* (agent-drafted) | not waived; no automatic collapse |
| SIG-GOV-012/013: legal home + defence resources before launch | WV-01 (OW) | interim individual home, disclosed (ADR-165) | owed; listed at GATE-ANNOUNCE |
| SIG-GOV-015: editorial board | WV-02 (OW) | interim single-maintainer authority + public decision log (ADR-164) | owed; listed |
| SIG-PUB-008 / go-live HG-11: two reviewer roles + written concurrence | WV-03 (OW) | each Class S readout is the operator's sole decision, disclosed (ADR-163) | owed; each readout discloses it |
| SIG-UI-042: release blocked until every finding is dispositioned | WV-04 (OW) | G2 H-1 moves the gate; open findings ship as known issues | owed; accepted-deviation candidate |
| SIG-GOV-001/002: one-click intake; no submitter identification | WV-05 (OW) | e-mail-only intake to the operator's address until after the announcement (B-8) | owed; listed |
| SIG-GOV-008: two-person authorisation for true deletion | WV-06 (OW) | withdrawal only; no true deletion | owed (withdrawal only) |
| counsel clauses of SIG-LIC-009 and SIG-INGEST-037 | WV-07 (OW) | the operator's own recorded determinations (no counsel); robots per A-5 | owed (LATER-05) |

- **One risk row closes by ADR:** RISK-P0-06 via the collection-conduct ADR restating SIG-INGEST-037's legal posture
  (S1b's single `adr-waiver` item) — written only with the operator's A-5 words.
- **Not waived; stay owed with a trigger:** SIG-EVAL-001/002/005/007 and SIG-IDENT-027/028's independent legs, SIG-DOS-002's
  independent checks (T-EVAL-IND); SIG-UI-001 usability (LATER-02); SIG-CONTRIB-012/012a/013, SIG-GOV-024, SIG-CHART-033
  (LATER-04; F2b had proposed WAIVED — Appendix B); a counsel opinion (LATER-05; a new OPEN row). D-R10-HUMAN-1 is never
  waived.

### 6.6 Coverage re-verdicts T4 applies (summary)

- **F2b (55 gated/reduced-scope ids):** 12 MET → MET-ENGINEERED (TRUST-004/007/008/009/010, FIND-006/007, DOS-002…005,
  ACQ-004); EVAL-003/004 and PUB-008 → AT-RISK-INTEGRATION (then superseded by L3: EVAL-003 → MET, EVAL-004 → WAIVED
  scoped); GOV-022, EVID-019 → MET-ENGINEERED; GOV-013/015 → MISSING; the outreach five → owed later-phase (not WAIVED).
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
/ `Extended by ADR-nnn (<date -u>)` status line** (COV-14). ADRs marked † exist only if the Part-A line is answered as
recommended. **One owner per ADR (FEA-06, COV-08):** the *author* column is either SEED-11 (decisions that record an S5
answer or bind the whole round; written in Stage B) or the chain row that implements the decision (engineering ADRs, which
quote the GATE-P answer verbatim where an S5 line is involved). No other row writes an ADR on the same decision; rows that
merely implement one say "implements ADR-nnn".

| # (prov.) | author | title | one-line decision | S5 line | source |
|---|---|---|---|---|---|
| 146 | SEED-11 | Correcting recorded dates that were not taken from a clock | truth source = `date -u`; corrections append-only via one register and this ADR (no footers on landed ADRs); sqitch lines never edited; candidate `p-17b713` superseded; restored rows annotated (SEED-06); a CI guard rejects new future-dated records | A-13, B-4 | B1 §8 (amended by CF-02) |
| 147 | SEED-11 | Gate-record integrity and readout authorship | verbatim operator words; agent-drafted text labelled and sha256-confirmed; no proxy signatures; hedged words are not decisions; the GATE-P recording rule (§1.3); ACCEPT-R8/R10 and GATE-G3 annotated with B7's facts; C-13 dated | A-16, B-4, C-1, C-3, C-13 | E2-17/18/X1; B2; B5 OM-07…09 |
| 148 | SEED-11 | Build memory v2.1: ledger contract and enforced append-only | ≤ 12 KiB head, value-only CURRENT STATE with `harness:`; guard core in CI; D-R10-MEMORY-1 split (option C) superseding ADR-126/127's cutover statements; closeout journal stays shadow (P34.30 implements; writes no ADR) | A-13 | B3, B4 |
| 149 | SEED-11 | Round-11 operating model | one harness (Claude Code); CI at every boundary; layered status; OM-19 (S4c wording) and OM-20 (class-based never-list); four gated sub-rounds; check-in packet; agent author identity per A-21 | A-15, A-21, S5-1/2 | B5 §6; S2 §3 |
| 150 | SEED-11 | Coverage verdict vocabulary | MET-ENGINEERED and WAIVED(ADR), four columns, checker cross-checks; "an amendment that weakens a MUST is a waiver" | B-5 | F2b §2 |
| 151 | **P34.1** | Toolchain pin and CI truth | Node 24 LTS, uv pin, `ubuntu-24.04`; head-bound check-runs; flake allow-list (one re-run); CI-unavailable needs a verbatim waiver; tests assert invariants | B-15 | H2; CF-01 |
| 152 | SEED-11 | Confidence without independent review | confidence by construction + mechanical suite; agent and maintainer evidence never gates; independent evaluation owed under T-EVAL-IND; rows 184–187 superseded | A-6 | ADR-L3-A |
| 153 | SEED-11 | Derivation, not identity | ruleset v3: auto-collapse only C0–C2 copies, census-verified; possible duplicates with intervals; **SIG-EVAL-004 WAIVED for C0–C2 only in the operator's words** (else not waived); supersedes ADR-105 §5, amends ADR-099 §3 | A-6 | ADR-L3-B |
| 154 | SEED-11 | Graph-quality suite as a ratcheted release gate | 27 checks, enforce/ratchet/report; V15 = 0 ratchet regressions + 0 enforce failures (FEA-11); loosening a baseline needs a new ADR | A-6 | ADR-L3-C |
| 155† | SEED-11 | HTML-first page types | T0/T1/T2/T3 registry with CI budgets; supersedes ADR-091 §3–4 and ADR-097 §2–3/§6, extends ADR-134 | A-12 | K0 §6 |
| 156 | **P35.52** | Public map v2 | self-hosted OSM basemap (reverses Round-9 Q8 on U-003.1's words; supersedes ADR-118 §2); count-conserving overlay tiles; Natural Earth place names | (answered) + B-23 | K1 MAP-00 |
| 157 | **P36.27** | Static figure kit and dossier visualisations | one server-side figure kit; inline SVG; downloadable SVGs under their own policy | B-22 | K6; K13 |
| 158 | SEED-11 | Graph exploration as aggregated overviews | overviews ≤ 3,000 nodes + egos + `/explore/`; descriptive only | A-11 | K0, K2, K13 |
| 159† | SEED-11 | Organisation publication | registry-matched organisations auto-allowed; operator degree-ordered review; person-name screen always runs; extends ADR-124 | A-10 | K2 D-K2-1 |
| 160 | **P35.17** | Structured jurisdiction scheme and placement | ISO 3166-2 registry, boundary pack, `lookup@1`/`placement@1`; `unresolved` is a report; revisits ADR-079/122 | A-18 | K4; F5 PKG-06 |
| 161 | **P35.12** | Release model v2 | content-addressed identity + `sig-YYYY-MM-DD.N`; descriptor v2 (extends ADR-132, merges J3 fields); Class R/S with an **expiring** standing go in the operator's words; cadence with suppression; 15-min withdrawal; pipeline signing key; operator-only tags. P34.22 fixes dates only; P36.66b implements | B-9, B-10, B-20 | G3 |
| 162† | SEED-11 | Transparency and distribution | export-time static artifacts; source-keyed rights lanes; fail-closed scrub; status lane; zero-egress R2 host with $50 ceiling, R2 operations ceiling and kill switch; raw bytes for raw-ok sources only; `/s/<pub>/` snapshots | A-3, B-19 | J3; J4 |
| 163† | SEED-11 | Single-maintainer publication posture | SIG-PUB-008 stands; nobody named; gate default-deny; the second-reviewer role WAIVED only per WV-03 | A-4, A-23 | E2-01 |
| 164† | SEED-11 | Interim editorial authority and public decision log | disclosed; GOV-015 WAIVED only per WV-02 | A-4, A-23 | E2-03 |
| 165† | SEED-11 | Interim legal home | individual, disclosed; revisit on announcement, first legal demand, funding or a second maintainer; GOV-012/013 WAIVED only per WV-01 | A-4, A-23 | E2-04 |
| 166† | SEED-11 | Legal-demand posture | written posture + published counts; canary declined | A-4 | E2-10 |
| 167† | SEED-11 | Counsel basis | past "counsel" determinations re-recorded as **the operator's own determinations (no counsel)**; E2's label text (confirmed verbatim) in every artifact; qualifies ADR-086/106 (status lines) | A-4, C-3 | E2-05; U-013 |
| 168 | SEED-11 | Collection conduct | robots **per A-5 in the operator's own words** (default: disallows and reservations honoured everywhere); opt-out register; reservation refusal; `robots_policy` semantics superseding ADR-088's clause; UA/contact to surveillancegraph.org | A-5, B-6 | E2-06/07/08 |
| 169† | SEED-11 | Rights basis with guardrails | **per-member terms captured verbatim** before any flip ("GL-GATE-07 recognised" dropped; GL-GATE-07 re-asked in own words); express prohibitions withdrawn; NC facts-only; non-US database-right lines not flipped; no Flock/Axon fact from a vendor host or a mirror of one; tribal data deferred | A-4, A-7…A-9, A-22, B-32…B-39 | E2-11; I7; TS-06 |
| 170† | SEED-11 | ODbL map basis | ADR-106's basis recorded as **the operator's own determination (no counsel, no document)**; per-compartment map kept | A-4 | E2-13 |
| 171 | SEED-11 | Outreach timing | outreach, records-request sending, recruiting, contribution-back → owed later-phase, trigger "operator authorises outside contact" | B-6 | E2-09; U-011 |
| 172 | SEED-11 | Product direction and scope | D3 order; US-nationwide breadth (CHART-025 only if A-17 = a); co-primary journeys; D3 §5 announce gate | A-17 | D3; E2-20 |
| 173 | SEED-11 | Acquisition waves and capacity | one ING-GO per wave; US-first; cap 40 GB, pre-grow, temporary tier bumps; Wave B code in 11B, Wave C queued from 11C | B-11, S5-4 | I8 §7 |
| 174 | **P35.1a** | Scheduler of record | Cloud Scheduler + daily live-diff + cron lint; GitHub `reingest` retired; **supersedes ADR-016's scheduler clause and ADR-076's scheduling path** | — (engineering) | G1-09; OPS-03 |
| 175 | **P34.6** | Production data protection and restore drills | deletion protection, retain-on-delete, quarterly drill at scale, monthly logical export; qualifies ADR-081 | A-1 | G1-03/04 |
| 176 | **P36.13** | API exposure posture | enforced rate limits; optional Cloud Armor (observability itself is SIG-OPS-006, no ADR) | B-30 | OPS-06 |
| 177 | **P37.3** | Evidence retention | 365-day unlocked retention (takedowns stay possible); writers cannot delete | B-14 | G1-RET; COV-14 |
| 178 | **P34.18** | Public identifier re-key | personal-handle ids renamed with a restricted old→new map and append-only aliases; "identifier changed" pages | B-3, A-0 | DR-C6-01; COV-14 |

**Also at T1 (records, not new decisions):** appended status lines on ADR-015, ADR-016 (scheduler clause, by ADR-174),
ADR-058 §3, ADR-075, ADR-092, ADR-096 §1, ADR-086/106 (`Qualified by ADR-167`), ADR-081 (`Qualified by ADR-175`),
ADR-099 §3 (`Amended by ADR-153`), ADR-124 (`Extended by ADR-159`), ADR-132 (`Extended by ADR-161`), ADR-134 (`Extended
by ADR-155`), ADR-079/122 (`Revisited by ADR-160`), and every ADR superseded above; recorded evaluations of the fired
revisit triggers (F3 §5.1); `ADR_TRIGGERS.csv` (SEED-15) with one row per revisit trigger, **including Q-29's
operator-accepted-risk revisit** (COV-14). Ticket-authored ADRs append their own status lines in the same PR. A Part-A
"no" that leaves a landed rule unchanged needs no ADR; one that changes a landed rule gets its own ADR. **SEED-11 writes
23 ADRs; ten move to their owning tickets** (FEA-01, FEA-06).

---

## 8. Ticket plan (`data/round11_plan.csv` is authoritative; 371 rows: 299 chain rows, 4 markers, 20 seed, 24 operator, 24 later)

The CSV is now **post-split** and carries three new columns: `uses` (references that are not ownership, COV-13),
`leg_runs` and `live_legs` (the live-leg structure of every multi-leg row, FEA-04/FEA-05). Ids are kept from S3 for
traceability even where a row moved sub-round (e.g. P36.12 now sits in 11B); final ids are assigned by T3 (11A) and the
PLAN rows (11B–11D). Every number below is regenerated from the CSV (`docs/build/logs/next-phase/S4c/check_order.py`).

### 8.1 Shape and counts

| sub-round | rows | kinds | eng. runs (PLAN) | leg runs | prod./publish rows | OM-20 rows | never-pre-authorised pauses |
|---|---|---|---:|---:|---:|---:|---|
| 11A P34 | 201–258 (58) | 55 tickets, PLAN-11B, acceptance P34.47, GATE-G4 | 55.0 (7.0) | 7.5 | 22 | 15 | P34.17, P34.21b, P34.46 |
| 11B P35 | 259–342 (84) | 81 tickets, PLAN-11C, acceptance P35.64, GATE-G5 | 81.0 (7.0) | 11.0 | 28 | 21 | P35.57, P35.11*, P35.14b, P36.12*, P35.61, P35.63 |
| 11C P36 | 343–414 (72) | 69 tickets, PLAN-11D, acceptance P36.73, GATE-G6 | 68.0 (6.0) | 3.5 | 17 | 8 | P37.2 (tier bump), P36.38, P36.72b, P36.70 (under B-9's default) |
| 11D P37 | 415–489 (75) | 71 tickets incl. 10 conditional (9.5 runs), CAP-01 P37.68a–d | 64.5 | 4.5 | 32 | 14 | P37.16a, P37.16b, P37.20, P37.36, P37.42, P37.55, P37.65b |
| tail P38 | 490–499 (10) | CAP.1 a/b, CAP.3, GATE-ACCEPT-R11, REC a/b/c, DOC, CAP-02, GATE-ANNOUNCE | 7.0 | — | — | — | the two gates |
| **total** | **299** | ticket 276 · plan 3 · capstone 11 · gate 5 · reconcile 3 · docs 1 · **HUMAN 0** | **275.5 (20.0)** | **26.5** | **99** | **58** | **20** + 5 gate markers |

\* in-ticket only if ING-GO-A / ING-GO-B are not given in the G4 sitting. Under S5-1's default (OM-20 not adopted) the 58
OM-20 rows also pause (≈ +29 leg runs). With OM-19, a pause queues a leg; the chain continues unless a later row needs
the leg's live result (`live:`).

**Re-split rule** (S2 §3.2, made precise at S4c): a sub-round whose *engineering* rows exceed 85 or whose engineering
runs exceed 75 (PLAN fan-outs and leg re-runs excluded) becomes two phases with an extra GATE. After S4c: 11A 57 rows /
48.0 runs; **11B 83 / 74.0 — at the edge**; 11C 71 / 62.0; 11D 75 / 64.5. To stay inside it, four non-owner rows that are
not prerequisites of P35.63 moved from 11B to 11C (P35.2, P35.21, P35.23, P36.2) and P36.1b follows them. If PLAN-11B's
Phase-4 sizing review adds splits that push 11B over, the rule fires and 11B splits at the Wave-B activation boundary with
an extra **GATE-G4b** — stated now so the extra sitting is not a surprise (FEA-04).

### 8.2 Contents in order (rows; details in §5)

- **11A:** CI first (P34.1–2) → production safety (P34.3–6) → DNS runbook (P34.50) → memory guards M1/M3/M2 (P34.7–9) →
  publish path (P34.10) → W0 copy (P34.11–15) → repo honesty (P34.16) → withdrawal (P34.19) → **republish #1** (P34.17) →
  re-key, evidence empty states (P34.18, P34.20) → **attribution backfill + republish #2** (P34.21a/b) → date truth,
  versioning (P34.22a/b–23) → sqitch hygiene (P34.24a) → API honesty (P34.25) → **clone rehearsal of the exact tip**
  (P34.24b) → allow tooling (P34.26) → memory M4–M10 (P34.27–33) → **PLAN-11B** (11B contracts + SIG-TRANSP, during the
  freeze) → 61-row re-verdict (P34.48) → C4 blockers (P34.34a/b–38) → replay read-back (P34.39a) + first-fire monitoring
  leg (P34.39b) → serving topology dark (P34.40–41) → identities, execution host (P34.42a/b–43) → **Part VIII at-rest
  audit** (P34.49) → quality baseline (P34.44a/b) → **Round-10 schema + allows + API** (P34.46) → P34.47 → GATE-G4.
- **11B:** **API release parity first** (P35.57) → honest-posture ER re-run (P34.45) → zero-egress host (P35.5) + post-DNS
  probe (P35.67) → scheduler lint (P35.1a) → Wave A (P35.6–11) → typing (P35.14a/b–15a/b) → **Wave B code** (P36.1a,
  P36.3–P36.11) → officer-naming gate, redaction, residential demotion (P35.28, P36.15, P35.66) → **Wave B activation
  queued** (P36.12) → fleet hygiene, probes, runbook (P35.1b, P35.3–4) → release identity (P35.12–13) → geometry and
  placement (P35.16–19) → numbers (P35.20a/b) → identity core (P35.22, P35.24–27) → labels and `/network/` (P35.29–30) →
  transparency exports (P35.31–35) → `withBase()` helper (P35.65) → provenance and citations (P35.36–42) → watch producer,
  dossier contributions, dossiers at every level (P35.43–45) → **dedup** (P35.46–47) → agent review + OPCHECK (P35.48–49) →
  page registry, budgets, tiles (P35.50–52) → release pipeline (P35.53–56, P35.58–60) → G2 steps 2–3 (P35.61–62) →
  **PLAN-11C** (11C contracts + K13 families) → **first model release** (P35.63) → P35.64 → GATE-G5.
- **11C:** **Wave C code + activation queued** (P37.1–2) → moved-in ops/source rows (P35.2, P35.21, P35.23, P36.1b, P36.2)
  → rate limits (P36.13) → L4 marker (P36.14) → design system + IA kit + figure kit + identifiers (P36.16–30) → search v2,
  basemap, grouped index, map, entity pages A + Organizations (P36.31–42b) → status lane, cadence (P36.43–44) → Sources &
  data (P36.45–51) → dossier sources explorer, downloads, template v2 (P36.52–57) → watch, evidence, research queue
  (P36.58–63) → Home/About/onboarding (P36.64–65) → snapshots (P36.66a/b) and changes (P36.67) → per-source versions
  (P36.68–69) → search activation (P36.71) → **core-surfaces release ACC-PLACES, carrying Wave B's data** (P36.72a/b) →
  second-release acceptance (P36.70) → **PLAN-11D** → P36.73 → GATE-G6.
- **11D:** evidence store, security baseline, ingestion hardening (P37.3–5b) → governance pages and rights hygiene
  (P37.6–8) → lifecycle, promotion gate (P37.9–10) → source-ops tail (P37.11–15) → dossier live captures (P37.16a/b) → map
  work (P37.17–20) → access, entity pages B, overviews, explorer (P37.21–27) → dossier networks, in-place map (P37.28–29) →
  watch (P37.30–34) → queue campaigns (P37.35) → raw archive, claim viewer v2 (P37.36–37) → disagreements, quality basis,
  changes, API parity, search export (P37.38–43) → mechanical evaluation, `/quality/`, organisation identity (P37.44–46b) →
  Wave D conditional (P37.47–54) → deposits, WACZ (P37.55–56) → projection rebuild, schema conformance (P37.57a/b–58) →
  intake dark/conditional (P37.59) → visual regression, T1 enhancements, contribution path (P37.60–62) → map and explore
  acceptance (P37.63–64) → **final release TX-16** (P37.65a/b) → coverage closeout, Stream-L re-measure (P37.66–67) →
  **CAP-01 journeys** (P37.68a advocate · b journalist · c organizer · d per-ask checks, ROUTES.csv, operator packet).
- **Tail:** §13.

### 8.3 Gates, pauses and operator touchpoints

- **Five gate markers:** GATE-G4 (row 258), GATE-G5 (342), GATE-G6 (414), GATE-ACCEPT-R11 (493), GATE-ANNOUNCE (499).
  HUMAN-H6…H8 stay reserved for the T-EVAL-IND segment. Each check-in GATE follows its acceptance row so the evidence is on
  screen; the packet is S5-2's (descoping defaults first; `continue` answers only batch lines).
- **Twenty never-pre-authorised in-ticket pauses** (§8.1) plus, under S5-1's default, the 58 OM-20 rows. The operator's
  touchpoints are listed by date in §11.2 (≈ 24, several synchronous).
- **HG-03 / ING-GO lines** are collected in the preceding packet: ING-GO-A **and ING-GO-B** at GATE-G4 (FEA-02),
  ING-GO-C + Q-23 at GATE-G5, ING-GO-D + I8-Q5 at GATE-G6. An unanswered rights line never flips a source (rows land with
  `ingestion_permitted=false`; activation skips them).

### 8.4 Live stages and calendar windows (S2 §5.1 as revised; UTC)

| window | event | constraint on the plan |
|---|---|---|
| 10-01 → 10-21 (06:09Z), peel-on 10-29T12:00Z | 32–33 first fires of existing triggers (S2/I8 say 32; S3 said 33 — FEA-13) | P34.39b reads them back as a **non-blocking** monitoring leg |
| **10-06 00:00Z → 10-13 12:00Z** | AR-3 batch window; **10-10 03:35Z** OSM replay | no hosted DB write, schema change or job roll; republishes allowed outside 03:00–10:00Z; PLAN-11B runs here |
| ≥ 10-10 after the replay | D-P31.4-1 read-back (P34.39a) | prerequisite of P34.46 |
| **≥ 10-14 14:00Z** | Round-10 schema deploy (P34.46) + 48 h soak | gates P35.11 and P35.61 |
| **before 10-19 00:00Z** | `ubuntu-latest` → Ubuntu 26 (GitHub runner notice) | P34.1 must have landed, else the seed PR pins `ubuntu-24.04` |
| **10-19 → 10-23**, 14:00–20:00Z | Wave A legs (P35.11) | ING-GO-A at G4; widened existing triggers paused for the wave or the roll after legistar's 10-20T05:00Z fire (FEA-14) |
| **10-26 → 11-05**, one family/day | Wave B legs (P36.12, dispatched in 11B) | ING-GO-B at G4; no release cut; data publishes in P36.72b |
| **11-06 → 11-13 12:00Z** | AR-3 | no release cut; P36.72b ≥ 11-13 12:00Z |
| 11-16 (Mon) 14:00Z | first weekday cadence slot | suppressed after P36.72b's Class S promotion (≤ 14 days) |
| **11-16 → 11-20** | Wave C legs (P37.2, dispatched in 11C) | ING-GO-C + Q-23 at G5; tier-bump go when the leg is due; Wave-B r11 crons paused |
| ≈ 11-22 | managed-cert renewal read (P35.67 leg 2; cert expires 12-22) | alert on failure |
| **11-23 → 12-04, 12-14 → 12-18** | Wave D (conditional, P37.54) | second-window sources ship in the 2027-01-15 cut |
| **12-06 → 12-13 12:00Z** | AR-3 | P37.65a/b cut before 12-06 or after 12-13 12:00Z |
| 12-15 (Tue) | cadence slot | suppressed if P37.65b promoted on or after 12-01 |

Tokens in `window_constraints`: **AR-2** on-demand backup + pre-state capture before any hosted write (and a bucket pre-copy
or versioned restore point before any bucket write; FEA-07); **AR-3** none of the three windows, never 03:00–06:30Z
daily, preferred 14:00–20:00Z weekdays; **AR-4** clock-guarded read-backs; **PUB** republishes outside 03:00–10:00Z.
Engineering runs ahead of the windows; windowed legs wait in the OM-19 queue and run from the leg-runner backstop when the
chain is not moving (FEA-05).

### 8.5 Sizing, the context ceiling and what Stage B writes

- **Dispatch target and ceiling (FEA-04):** `dispatchTarget` is recorded in CURRENT STATE (T5) as **subagent-safe sizing
  even if dispatch is headless**: every chain row's working set stays well under half of one fresh context
  (decompose-spec rule 1); S = 0.5, M = 1.0 run; **no chain row exceeds 1.0 run** except the explicit fan-outs (PLAN-11B 7.0,
  PLAN-11C 7.0, PLAN-11D 6.0, P34.48 1.5), each executed as ≤ 1-run contexts with named seams. The orchestrator warns on a
  dispatch/sizing mismatch (orchestrate-build §0).
- **Splits done in the CSV (FEA-04):** the 16 S3 L rows (P34.21, .22, .24, .34, .42; P35.1, .14, .15, .20; P36.1; P37.4,
  .5, .16, .46, .57; P38.3) and the nine rows S4 found too big (P34.44, P36.9, P36.42, P36.66, P36.72, P37.65, P37.68 ×4,
  P38.1, P38.3 ×3) plus P34.39 a/b (FEA-03). T3 no longer splits; the PLAN rows' Phase-4 sizing reviews re-check 11B–11D.
- **Multi-leg rows (FEA-04/05):** every row with a window, an in-ticket go or a ride on a later release carries its leg
  structure in `live_legs` and its re-run cost in `leg_runs` (e.g. P35.61 "3: audit + plan | operator review 1–4 h |
  apply + freeze", P36.12 "8–9 family-day legs", P37.2 "5: pre-grow | tier bump | run | soak | revert").
- **What Stage B writes (FEA-01):** SEED-13 writes manifest rows for **all** 299 chain rows (mechanical from the CSV), full
  contracts **only for 11A and PLAN-11B**, `Kind: skeleton` contracts for 11B–11D rows, the GATE markers and the
  `## Human prerequisites` section. **11B, 11C and 11D contracts are authored at each sub-round boundary by the PLAN rows**
  (`decompose-spec mode=extend` against this ratified CSV, dispatched by the orchestrator as ordinary chain rows: PLAN-11B
  in 11A's freeze, PLAN-11C before GATE-G5, PLAN-11D before GATE-G6), so each GATE's OM-20 list cites written contracts.
- **A-13 fallback:** if the seed is records-only, SEED-02/03 become P34.0a/P34.0b at rows 201–202 and everything shifts +2.
- Every live-stage contract gets a `Live window:` header, an OM-14 mutation list and its live-leg re-run prompt;
  live-result edges are marked `live:`.
- The contract template gains a `harness:` header (CF-04) and B5's ticket-contract block (B5 §6.2).

### 8.6 Rows 184–187 and Round-10 return passes

- **184 HUMAN-H4, 185 P32.22a, 186 HUMAN-H5, 187 P32.23** stay as existing manifest rows, never dispatched, with tokens
  appended byte-for-byte (L3 §6.3): 184 `superseded-by(T-EVAL-IND segment: EV1, HUMAN-H6, HUMAN-H7)` · 185 `…EV-F` · 186
  `…HUMAN-H8` · 187 `superseded-by(CONF-02 = P34.45, CONF-09 = P37.44; decision leg: T-EVAL-IND segment EV-D, EV-R)`.
  A dispatch amendment (L3 §6.3 item 1) supersedes the old "a resume re-enters at row 184" sentence. Validator V2 skips
  them; if the validator change is unwanted, use `deferred(D-R10-HUMAN-1; T-EVAL-IND)`. `nextTicket` is never a HUMAN marker.
- **Re-homed return passes:** row 183 → P35.61 (ACT-14) · 188 → P35.62 (ACT-15) · 191 → P35.63 (ACT-24) · 179–182 →
  P37.16 (ACT-22) · D-P32.16-1 → P37.59 (ACT-23, conditional). The GATE-G3 signature (row 190) does not transfer.

### 8.7 Non-chain units

- **Seed (20 units, 23.25 runs, ≈ 29 contexts of ≤ 1 run):** SEED-00…19 (Appendix A maps them to T1–T6). Re-scoped at S4c
  (FEA-01): SEED-11 writes only the 23 operator-decision/round-binding ADRs; SEED-12 writes MEM/ENG/OPS/SEC/REL/CONF;
  SEED-13 writes manifest + 11A contracts + skeletons; SEED-14 drops the 61-row re-verdict (now P34.48) and gains the
  LATER/later-phase register entries (COV-10). Each unit's `notes` name its contexts and seams.
- **Operator actions (24, OP-01…OP-24):** §11. OP-24 schedules the leg-runner backstop (FEA-05); OP-18 is now only C-13's
  dated answer (TS-08); OP-09 depends on the P34.50 runbook (FEA-08).
- **Later (24 units, 27.0 runs):** LATER-01…22 + R11-ACQ-23a/b, each with a trigger (§15), all recorded in the registers
  by SEED-14 (COV-10).

### 8.8 Critical paths and calendar cliffs

- **Calendar (binding):** GATE-P → seed → GATE-B → P34.1 (≤ 10-19) → P34.39a (after 10-10) → **P34.46 (≥ 10-14)** →
  GATE-G4 → P35.57 → Wave A legs (10-19→23) → Wave B code → **Wave B legs (10-26→11-05)** → 11B chains → **P35.63** →
  GATE-G5 → P37.1–2 → **Wave C legs (11-16→20)** → **P36.72b (≥ 11-13)** → GATE-G6 → **P37.65b (outside 12-06→13)** →
  P37.68a–d → P38 → GATE-ANNOUNCE.
- **Runs:** inside 11B three chains converge on P35.63 (JUR-01→02a→02b→DSRC-01→JUR-03; CONF-03a→03b→04→07a→07b;
  REL-01→…→REL-06); the Wave B block (≈ 15.5 runs) now precedes them, which delays P35.63 by ≈ 1.5–2.5 days (inference).
- **Decision path:** A-18 (old B-24) before P35.17, or the jurisdiction chain and P35.63 stall; OD-27 before T6, or the
  seed PR cannot be pushed.
- **DAG check (S4c):** 299 chain rows, contiguous 201–499; every `depends_on` token resolves; 0 rows before a dependency
  (hard, `(S2)`, `live:`, sequence and soft edges all counted); acyclic; no 11A/11B row depends on a later sub-round
  (`docs/build/logs/next-phase/S4c/check_order.py`).
- **Expected timeline (inference; 6–10 runs a day incl. CI waits; operator answers within a day):** S5 ≈ 10-01→10-03;
  seed → GATE-B (R0) ≈ 10-05→10-07; GATE-G4 ≈ 10-15→10-17; Wave B code done ≈ 10-19→10-22; GATE-G5 ≈ 10-27→11-02;
  GATE-G6 ≈ 11-13→11-18; P37.65b ≈ 11-27→12-05; tail ≈ 12-03→12-12. About 10–11 weeks from R0.
- **Cliffs, not one-for-one slips (FEA-12).** Monthly freezes (days 6–13) and "one manual job at a time" quantise slips:

  | first dispatch R0 | 11A end / G4 | Wave A (10-19→23) | Wave B (10-26→11-05) | Wave C (11-16→20) | final release P37.65b | tail |
  |---|---|---|---|---|---|---|
  | ≤ 10-07 | 10-15…10-17 | in window | in window | in window | 11-27…12-05 | 12-03…12-12 |
  | 10-08…10-12 | 10-17…10-21 | partial; remainder → 10-26…10-30, sharing Wave B's days | squeezed; spill → 11-16 week (collides with C) | in window or → 11-23…12-04 | 12-03…12-05 or ≥ 12-13T12:00Z | mid–late December |
  | 10-13…10-20 | ≥ 10-21 | → 10-26…10-30 | → 11-16…11-20 (Wave C → 11-23…12-04) | → 11-23…12-04 | ≥ 12-13T12:00Z | late December |
  | > 10-20 | ≥ 10-28 | → November windows | → late November | → December | January 2027 | January 2027 |

  **Latest R0 that keeps each wave in its window:** Wave A ≈ 10-07, Wave B ≈ 10-12, Wave C ≈ 10-20 (inference at the slow
  end of 6–10 runs a day). A-19 records the operator's trade-off in advance; at GATE-G4 the orchestrator re-projects the
  calendar and the agent spend from 11A's measured runs a day and pauses rather than silently stretching (FEA-10).

---

## 9. Obligation mapping (S1b: `universe/UNIVERSE_DISPOSED.csv`; `tools/check_dispositions.py` → structurally valid, 0 errors after S4c — it checks shape, not truth, F-27)

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

**Rule (c) switch (S2 §2.2):** S1b provisionally defined "first waves" from the catalog; T4 switches the check (and rule
(a)'s catalog view, COV-13) to read `sub_round ∈ {11A, 11B}` from `data/round11_plan.csv`. Result at S4c (scratch check
emulating the switch): the 56 S0/S1 owner rows and their prerequisite closure — **87 chain rows / 79.5 runs (11A 42, 11B 45)
+ 7 seed units** — sit entirely in 11A ∪ 11B; nothing in the closure moved out of 11B.

### 9.2 Every owed deferral (36 = 32 OPEN + 4 PARTIAL)

| disposition | deferral → landing |
|---|---|
| **ticket (9)** | D-FEDERAL.1-1 → P37.11 · D-P32.10a-1, D-P32.16a-1 → P34.24 · D-P32.16-1 → P37.59 (conditional; Q-27/B-8) · D-R10-MEMORY-1 → P34.30 (split, option C) · D-R10-SOURCES-1 → P34.38 (+ P37.16) · D-SOURCES.7-1, D-SOURCES.9-1, D-SOURCES.9-4 → P36.2 (rights flip/decline batch; E4 R3, R5, R6 lines; now in 11C) · **D-P32.16-1 → P37.59 is expected to remain OPEN in Round 11** under B-8's recommended answer and U-008 (no named moderation owner or reviewer rotation; COV-15) |
| **live-return-pass (9)** | D-P21.5-1 (PARTIAL) → P37.55 + OP-19 (closes only if B-6/Q-E2-23, B-21 and A-0.4 are answered; under their defaults it stays PARTIAL — COV-15) · D-P31.4-1 → P34.39 · D-P32.18-1, D-P32.19-1, D-P32.20-1, D-P32.21-1 → P37.16 (HG-03, E4-B1) · D-P32.23a-1 → P35.62 · D-R10-LIVE-1 → P35.61 · D-R10-PUBLISH-1 → P35.63 |
| **later-phase (9)** | D-P21.7-1 → LATER-03 · D-P30.2b-2, D-R6.1-EVAL, D-R10-HUMAN-1 → LATER-01 (T-EVAL-IND) · D-R7.1-AUTH → LATER-06 · D-R7.2-SEND → LATER-04 · D-R10-USERS-1 → LATER-02 · D-SOURCES.8-2 → LATER-10 · D-SOURCES.9-3 → LATER-17 |
| **decision (7)** | **D-SOURCES.8-1 (PARTIAL) → E4-R4a (B-41: R4a–c capture terms, not flipped — consistent with B-34 and US-first; the three non-US rows wait for trigger "operator expands non-US coverage", LATER-09/10; Bellevue declined under A-9; COV-07)** · D-JURIS.2-1 (PARTIAL) → E4-R1 (B-41: close, eID leg WONTFIX) · D-P30.2b-1 → B-18 (merged into the maintainer check, P35.49; else OP-16) · D-P32.3-1 → B-18 (folded into A-10 + P37.46; else OP-15) · D-SOURCES.2-2 → E4-R2a (B-41: decline) · D-SOURCES.7-2 → B-18 (register US 511 keys, OP-13 → P37.12) · D-SOURCES.9-2 → E4-S2 (B-43: WONTFIX) |
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

109 land on a seed or 11A/11B unit (108 tickets + F-522's live-return-pass); 3 rest on S5 decisions and **stay open under
their defaults** (F-31 → A-4; F-191 → C-3; F-386 → A-3, with TX-11 at P35.5); 1 was already done (F-366, I8's own
correction). None is later-phase or wontfix. **Not every owner is a full fix** (COV-06): the table lists each S0/S1 whose
owner is an interim mitigation, depends on a default, or whose final fix lands later.

| finding(s) | sev. | owner (S0/S1 unit) | fix kind | final fixing row | default that leaves it open |
|---|---|---|---|---|---|
| F-097, F-131 (handles) | S0 | P34.18 → P34.21b; A-0 | fixed live in 11A (scope widened); interim A-0 | P34.21b (+ P35.26 for the `camera_operator` value) | A-0 → removal waits to ≥ 10-13 |
| F-387 (misattribution) | S0 | P34.21a/b | fixed in republish #2; interim N-4 + A-0.2 | P34.21b | A-0 → downloads stay readable to ≥ 10-13 |
| F-130 (API 25 subjects) | S0 | P34.25 → P34.46 | fixed ≥ 10-14; interim N-7 | P34.46 | — |
| F-07, F-099, F-390, F-399 (permalinks) | S1 | P35.42 (TX-13a) + P34.11 wording | **interim** (honest wording, release id on every page) | P36.66b (11C) | **B-19/D-J3-6 → snapshots never published, so links never pin** |
| F-103 (bulk/API/terms unlinked) | S1 | P34.13 | partial (terms linked) | P36.50 (11C) | **A-3 → no public download links** |
| F-386 (bulk release unreachable) | S1 | decision D-J3-4 (A-3) | default-dependent | P35.5 + P36.50 | **A-3 → stays unreachable** |
| F-452; F-106/F-420 labels | S1 | P34.26; P35.30 | partial (non-organisation labels fixed) | P36.41–P36.42b, P37.22–28 | **A-10 → all organisations withheld** |
| F-522 (0 of 2.78 M bindings reach bytes) | S1 | P35.61 (live-return-pass) | partial: only sources re-run in P35.61 | P35.61 | the ≈ 2.78 M legacy links stay zero-byte (insert-only spine), labelled "capture not bound" |
| F-27 (validators check structure) | S1 | **SEED-02** (+ P34.9 no-vacuous-pass) | fixed by construction (rehomed from SEED-18) | P34.9 | — |
| F-184 (hijackable contact domain) | S1 | **P35.38** (rehomed from OP-11) | fixed without a purchase | P35.38 | — (OP-11 optional) |
| F-31 (spec contradicts decisions) | S1 | decision Q-7 (A-4) | default-dependent | SEED-11/12 | **A-4/A-23 → stays open (owed, listed at GATE-ANNOUNCE)** |
| F-191 (backward confirmations) | S1 | decision OD-12 (C-3) | default-dependent | SEED-08 | **C-3 → not recorded** |
| F-506, F-507, F-511, F-518…F-521 (L1/L2 correctness) | S1 | P35.24–27, P35.46–47 | pulled forward into 11B; interim P34.44b ratchet | 11B rows | A-6 (no collapse) for F-518/F-519 |
| F-512 (inferential tiers auto-written) | S1 | P34.45 (now first in 11B, after P35.57) | fixed in 11B; publication with P35.63 | P35.63 | A-20 = a would let it land in 11A |

### 9.5 Every operator feedback item

| item | disposition → landing |
|---|---|
| U-001 | ticket → P36.64 (Home/About; landing text C-4) |
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
| U-014 | operator-action → OP-10 (`contact@surveillancegraph.org` alias) |
| U-015 | already-done → B7: attribution high-confidence for 477 of the 480 chain commits; the S0 surface "medium, unknown"; the model behind `swe-2-high` unknown (TS-17); confirmed or corrected at C-2 |

**Asks recorded only in META_PLAN §7.1 (COV-03).** They are not yet universe items because the S1b checker builds its
feedback set from `OPERATOR_FEEDBACK.md` only; T4 adds them to the universe and extends rule (d) to them. Traced now:

| id | operator, verbatim (META_PLAN §7.1) | disposition → rows |
|---|---|---|
| W2-1 | *"configure them for ingestion and ingest them into prod"* | ticket → P35.6–P35.11 (Wave A), P36.1a–P36.12 (Wave B), P37.1–P37.2 (Wave C), P37.54 (Wave D, conditional) |
| W2-2 | *"making the data itself easily exportable"* | ticket → P35.5, P36.50, P36.53, P36.68, P37.43 |
| W2-3 | *"explore each third party source"* | ticket → P36.45–P36.49, P36.69 |
| W2-4 | *"link to the ground truth"* | ticket → P35.35, P35.36 (`upstream_href`) |
| W2-5 | *"download the raw data"* | ticket → P37.36 + P36.50; **descoped under B-19/D-J3-1's default (§4.4 row 15)** |
| W2-6 | *"see ingestion logs/metrics/timestamps"* | ticket → P35.32–P35.34, P36.43, P36.46; **descoped under B-19/D-J3-2's default (§4.4 row 16)** |
| PF-1 | S0 hotfixes approved in principle (attribution takedown, `/editorial-standards/` fixture review, `/dispute/` notice) | ticket → P34.17, P34.21a/b |
| PF-2 | G1 quick actions QA-1…QA-10 | ticket → P34.3–P34.6 (R11-ACT-01…04) |
| PF-3 | `/task/new/` demo pages | ticket → P34.17 (R1.9; via F-278) |
| GM-1 | *"keep me in the loop"* | OM-17 digests at every check-in (SEED-17) |

### 9.6 Candidates and decision-dependent items

- **65 candidate groups (694 candidates):** ticket 13 (Waves A–C families), later-phase 43 (LATER-09 long tail, 389
  candidates), decision 8 (the Wave-D groups, I8-Q5), merged-into 1. Tier 3 (259) is not acquired.
- **41 decision-dependent items** wait on 24 S1c ids (S1b §4); their final kind is fixed when the operator answers at S5,
  and T4 records it.

---

## 10. Ops track

### 10.1 Already done before the round (Track 0, operator-approved)

Automated backups + PITR and an on-demand backup (0.1); `/curate/` removed (0.2); minimal alerting to the operator's
address — e-mail channel, uptime checks on the site and API `/health`, alert policies for failed job executions (excluding
the broken `sig-probe`), `sig-pg` disk > 85 % and both uptime checks (0.5). **Not done:** restore drill, deletion
protection, budget alert, TLS-expiry alert, probe re-roll (A-1/A-2 ask whether any of these run before Round 11).

### 10.2 Ops rows in the round

| row | what | live stage / window |
|---|---|---|
| P34.3 | data protection: deletion protection + retain-on-delete (QA-1), maintenance window (QA-2), versioning + noncurrent lifecycle (QA-6), `sig-web` bucket non-public (QA-7), disk cap | production write; outside AR-3 for `sig-pg` patches |
| P34.4 | alerts that reach a human: verify and extend Track 0.5; TLS expiry; `SIG-ALERT` log alert; `sig-probe` re-roll (QA-5); disable the GitHub `reingest` schedule (QA-8) | production write |
| P34.5 | cost guard: budget alert at $300, billing export, monthly spend ledger (U-011) | production write (billing admin; OP-12) |
| P34.6 | restore drill at scale into an isolated clone with RTO/RPO; restore-point procedure; monthly logical export | production write (separate instance) |
| P34.10 | one allow-listed publish path; never deletes release trees | code; first used by P34.17 |
| P34.49 | Part VIII at-rest audit: scan the evidence store for I7 S1–S9 classes and F-406 bytes (OSM `user`/`uid`, Eyes on Flock search reasons, ArcGIS attributes); seal or suppress per SIG-GOV-007; counts only (TS-07) | read-only scan + restricted-tier move (OM-20 list) |
| P34.50 | DNS cut-over runbook + zone inventory for OP-09: LB hostnames DNS-only (grey cloud) so the Google-managed cert (expires 2026-12-22) keeps renewing; R2 on a subdomain; TTL lowered 48 h ahead; DNSSEC DS handled at the registrar; rollback = revert nameservers; mail check (FEA-08) | read-only |
| P34.39a/b | 10-10 OSM replay read-back (D-P31.4-1; prerequisite of P34.46) / first-fire wave to 10-21 + peel-on 10-29 as a non-blocking monitoring leg | read-only; clock-guarded |
| P34.40–41 | serving topology (LB path rules for `/v1/*`, `/intake/*`; registry mount; nginx roll) dark; withdrawal-barrier bytes | production write (dark) |
| P34.42–43 | least-privilege runtime identities (remove project Editor); execution host for hosted return passes; read-only `sig_audit` login | production write |
| P35.1 | scheduler of record + daily live-diff + cron lint + fleet hygiene (79 triggers; cruft jobs) | production write |
| P35.2 | alerting as code; probe targets out of the image; escalation | production write |
| P35.3 | production-truth probes + fixture-sentinel scan (G10) | read-only probes |
| P35.4 | ops runbook (`docs/ops/RUNBOOK.md`) + stale ops doc fixes (README "≈$0/$9") | docs |
| P35.5 | zero-egress distribution host; $50/mo egress ceiling + kill switch; R2 Class-B operations ceiling + alert (FEA-18) | production write (R2 via Cloudflare if A-3 = a) |
| P35.67 | post-DNS cut-over probe: TLS, managed-cert renewal status, every route, mail; second leg ≈ 11-22 (cert renewal window) | read-only legs after OP-09 |
| P36.13 | API exposure: enforced rate limits (search 30/min) + optional Cloud Armor (+$6) | production write |
| P36.43–44 | status lane (6-hourly `status/**` writer); release cadence automation | production write |
| P37.3 | evidence-store hardening + off-instance copies | production write |
| P37.4a/b | security baseline: scanning, SBOM, signing, audited restricted-byte access, audit logs (+≈ $5) with a Data Access exclusion filter and a log-volume alert (FEA-18) | production write |
| P37.15 | scheduled parser canary | production write |

All production writes follow OM-14 (contract-named mutation, scripted path, pre-state capture, restore point, rollback
command, run-ledger entry) and AR-2/AR-3. They need no per-row go **only** if the operator approved, verbatim, an OM-20
list naming the row; otherwise each is an in-ticket pause. The class-based never-list (§3.3) always pauses.

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

### 10.4 Money (S2 §9; S1a §6; inference until C-7 / P34.5 give measured numbers)

| after | delta | main items (USD/mo) | projected total |
|---|---:|---|---:|
| baseline | — | Cloud SQL ≈ 52–54, LB ≈ 18, `sig-api` min-1 ≈ 7–10, jobs ≈ 3–9 (G1 list-price estimate, unverified) | ≈ 90–100 |
| 11A | +4.90 | quality job 2, alerts 1, Round-10 API 1, logical export 0.5, data protection 0.3, cost guard 0.1 | ≈ 95–105 |
| 11B | +1.19 | zero-egress host 1, Wave A 0.5, release bucket/staging 0.5, …; Artifact Registry cleanup −1 | ≈ 96–106 |
| 11C | +14.70 | optional Cloud Armor 6, release cadence 4, Wave B 2.5, basemap on R2 2, status lane 0.2 | ≈ 111–121 |
| 11D | +11.90 | security baseline 5, Wave C 2.2, conditional intake 2, conditional Wave D 1.5, evidence store 0.5, … | **≈ 123–133** (+≈ 1 domain) |

- **Scenarios:** no DNS move (A-3 = b) → ≈ $127–174 and no public download links; B-30 = a → +$3; defaults that remove
  cost: no Wave D −1.5, no intake −2, no Cloud Armor −6; later: permanent Cloud SQL tier +$49 (LATER-08), savings −$47
  (LATER-19).
- **One-off:** restore drills ≈ $0.15–0.40 each; Wave-C tier bump ≈ $3; Class S release object writes ≈ $2.5 each (≈ 6 →
  ≈ $15); `sig-project.org` ≈ $10–20/yr; optional hardware key ≈ $25–55; paid data $0 (B-12).
- **Over-$300 approvals needed: none planned.** Watch list read at every check-in: denial of wallet on the world-readable
  `sig-public` until P35.5's kill switch (≈ $120/day at 1 TB/day; P34.5's alert sees but does not stop it); search API
  abuse before P36.13 (≈ $140/mo worst case); download egress if A-3 = b and links were exposed (blocked by P36.50's
  default); LATER-08. If the measured baseline is well above G1's estimate, GATE-G4 re-projects the round before 11B.
- **Unmeasured lines (FEA-18):** P37.4's Data Access audit-log volume (exclusion filter + alert), R2 Class-B operations
  under a request flood (ceiling in P35.5), and the Wave-C pre-grow (one-way). C-7 now and P34.5 in 11A's first days.
- **Agent (build) spend** is outside the $300 infrastructure ceiling (A-2 a) and is **estimated now** (FEA-10; inference):

  | item | contexts | basis |
  |---|---:|---|
  | Stage-B seed | ≈ 29 | 20 units, each split into ≤ 1-run contexts |
  | chain engineering rows | ≈ 290 | 294 non-gate rows, minus the 3 PLAN rows and P34.48 counted as fan-outs |
  | PLAN-11B/11C/11D + P34.48 fan-outs | ≈ 22 | 7 + 7 + 6 + 2 |
  | live-leg re-runs | ≈ 40 (≈ 26.5 runs); ≈ 100 if OM-20 is not adopted | `leg_runs`; OM-19 |
  | re-runs after red CI, splits found late, orchestrator boundary work | ≈ +5–10 % | Round 10 executed no live legs, so it is not a base rate (B5 §3.2) |
  | **total** | **≈ 380–450 fresh contexts** | |

  **Calibration:** this planning session's heavy rows measured ≈ 250k–600k tokens each (orchestrator observation; the
  usage limit was hit at ≈ 19:10Z on 09-30 with planning subagents). Applying that range to every context gives **≈ 95 M
  (380 × 250k) to ≈ 270 M (450 × 600k) tokens** for the round — ≈ 9–27 M tokens a week over ≈ 10–11 weeks. Light S rows
  will sit below the range, so the low end is the likelier one; no dollar figure is given because it depends on the
  operator's plan. **Throughput the calendar needs:** ≈ 6–10 runs a day, every day (S2 §5.4). **The operator states an
  envelope at A-2/OD-26**; without one, the orchestrator sets `blockedOn` at the first usage-limit event rather than
  silently stretching the calendar. **Per-check-in spend report (OM-17 digest and the GATE packet's budget part):** runs
  and leg runs dispatched since the last check-in; tokens per run (from the harness's per-session usage) with the
  median and maximum; cumulative tokens; the projection to round end at the measured rate; usage-limit events; harness
  and model. At GATE-G4 the orchestrator re-projects calendar and spend from 11A's measured runs a day. No new paid model
  service or second model family without an explicit go (B-31; LATER-18). "Not measured" is a valid line; no figure is
  invented.

### 10.5 Operator-accepted risks carried by ops

MapRoulette key unrotated (rotation before any contribution-back use; LATER-03) · the operator's personal address as the
public dispute contact until the `contact@` alias exists (Q-29; revisit when volume or exposure grows) · no counsel
(U-013; exposure recorded by the governance ADRs, not removed).

---

## 11. Human-work plan (operator-only)

### 11.1 Principle

There are no humans on the project besides the operator (U-008), and no one outside the project is contacted (U-011).
Agents never perform, simulate or stand in for human work: no agent label counts as a human label, no agent signs, and
model agreement is never ground truth (P4; OM-08). **Round 11 seeds no HUMAN rows.** The operator's own work is either a
prerequisite with a due point (listed in the manifest's `## Human prerequisites` section and in the preceding check-in
packet) or a gate item — never a chain row a ticket silently waits on.

### 11.2 Operator actions and touchpoints by date (OP-01…OP-24; re-estimated at S4c, FEA-09; inference)

| when (expected) | touchpoint | sync? | est. time |
|---|---|---|---|
| 10-01 → 10-02 | **S5 sitting 1**: Part A (24 lines, several in own words) + S5-1…S5-4, one line at a time | yes (chat) | 1.5–2.5 h |
| 10-02 → 10-03 | **S5 sitting 2**: Parts B (42), C (13), D2 (16) | yes (chat) | 1.5–2.5 h |
| right after sitting 1 | A-0 gos (3 removal actions) + merge the A-0.1 PR; A-1 drill go | short | 0.5 h |
| Stage B (≈ 10-03 → 10-07) | OP-01 skills Tier A · OP-05 GitHub stack ruleset · OP-07 project variable + usage alert · OP-24 leg-runner schedule · OD-27 push choice already answered · GATE-B | — | 1.5–2 h |
| before row 201 | OP-02 skills Tier B-must (OP-03 if possible) | — | 0.5 h |
| ≈ 10-08 → 10-10 | republish #1 go + copy batch (N-strings already ratified) | — | 0.5–1 h |
| ≥ 10-13 | republish #2 go; OP-12 billing admin | — | 0.5 h |
| **10-14/10-15, 14:00–20:00Z** | **P34.46 schema slot (operator present)** | **yes** | 1–2 h |
| by GATE-G4 | OP-09 DNS move from the P34.50 runbook (OP-11 optional) | yes (registrar) | 0.5–1 h |
| ≈ 10-15 → 10-17 | **GATE-G4 sitting**: ING-GO-A, ING-GO-B, P35.57 API-roll go, the 11B OM-20 list, budget/spend report | yes | 1–1.5 h |
| ≈ 10-20 → 10-26 | P35.14b sqitch go; OP-14 top-50 organisation review (1–2 h, before P36.41) | — | 1.5–2.5 h |
| ≈ 10-24 → 10-28 | **P35.61 bounded-apply plan review** (within 1–3 working days of the leg) | **yes** | 1–4 h |
| ≈ 10-27 → 11-02 | **P35.63 HG-11 readout + OPCHECK** and **GATE-G5** (ING-GO-C + Q-23, 11C OM-20 list) in one sitting | yes | 2–3 h |
| by GATE-G5 | OP-10 alias (after OP-09) · OP-20 signing key (if B-20 = a) · OP-21 relevance set (if B-28 = a) | — | 0.5–1.5 h |
| 11-13 → 11-18 | **P36.72b HG-11 readout + OPCHECK**, P36.70 (Class S under B-9's default), P36.38 API go, **GATE-G6** | yes | 2.5–4 h |
| **11-16 → 11-20** | **Wave-C tier-bump go when the leg is due** | **yes** | 0.25 h |
| ≈ 11-20 → 12-02 | P37.16a/b Part VIII signs (4 families) · P37.20/P37.42/P37.36 gos · P37.55 deposit go · OP-13 keys (conditional) | — | 1.5–2 h |
| ≈ 11-27 → 12-05 | **P37.65b final HG-11 readout + OPCHECK**; OP-19 Zenodo publish | yes | 2–3 h |
| ≈ 12-01 → 12-08 | OP-22: operator walkthroughs of 13 journeys (maintainer, not independent), "beautiful" gallery, About text (C-5) | — | 3–5 h |
| ≈ 12-03 → 12-12 | **GATE-ACCEPT-R11** (sign the accepted-deviations list verbatim) · **GATE-ANNOUNCE** (MUSTs-unmet list, Q-29 revisit, announcement copy) | yes | 1.5–2.5 h |
| any time | OP-08 bottom-up merge sitting #141–#190 — **a safety item** (public `main` keeps false governance text until merged, TS-09); optional per-sub-round merges after each GATE (FEA-17) → then OP-06 | — | 1–2 h + optional |
| every check-in | read the OM-17 digest (spend line included) | — | 0.25 h × ≈ 8 |

**Total ≈ 25–40 h over ≈ 24 touchpoints in ≈ 10–11 weeks**, with eight synchronous slots in bold. If OM-20 is not adopted,
≈ 58 more short in-ticket gos add ≈ 4–6 h. Folded/superseded: OP-15 (into OP-14 + P37.46), OP-16 (into P35.49). OP-18 is
now only the C-13 dated answer, asked at S5.

### 11.3 What is waived, deferred or owed — and the trigger that reopens it

| obligation | Round-11 posture | trigger |
|---|---|---|
| independent human evaluation (SIG-EVAL-001/002/005/007, IDENT-027/028; D-R10-HUMAN-1, D-R6.1-EVAL, D-P30.2b-2; rows 184–187) | **owed, non-blocking, never waived**; Round 11 measures, discloses and labels PROVISIONAL | **T-EVAL-IND** |
| SIG-EVAL-004 lower bound | **waived for C0–C2 only, if A-6 is answered in the operator's words**; otherwise owed | T-EVAL-IND; a proposal to auto-write an inferential tier; GQ-23 failing twice in a quarter; M-1b < 0.98 |
| hostile-reader second reviewer (SIG-UI-042; waiver candidate WV-04), dossier independent check (SIG-DOS-002) | owed unless WV-04 is waived in the operator's words; `/editorial-standards/` says "not yet performed"; the operator may serve as one disclosed reader | T-EVAL-IND |
| usability study on the live site (D-R10-USERS-1, SIG-UI-001) | owed | LATER-02: participants available and contact authorised |
| outreach, records-request sending, recruiting (D-R7.2-SEND, CONTRIB-012/012a/013, GOV-024, CHART-033) | owed later-phase by ADR | LATER-04: the operator revisits U-011 |
| contribution-back to OSM/MapRoulette (D-P21.7-1) | owed later-phase | LATER-03 |
| counsel opinion | not sought; a new OPEN row records it | LATER-05: the operator obtains counsel |

**T-EVAL-IND fires** only when all three are recorded in GATE DECISIONS with evidence (L3 §6.5): (a) the operator states,
in their own words, that at least two people independent of the project are available to label, and authorises that
contact as an explicit exception to U-011; (b) the "frame-affecting set" has landed — CP-1, CP-2, CP-4, CP-5, CP-6 plus
the Stream-I camera ingests (L3 §2; in this plan P35.22, P35.24, P35.25, P35.16–19, P35.15 and Waves A–C); (c) the Q-24 aim
is recorded (certify one tier at n = 149, or measure
only at n ≈ 100). On firing, `decompose-spec mode=extend` seeds **EV1** (reviewer surface + evaluation database, ≈ +$10/mo)
→ **HUMAN-H6** pilot → **EV-F** freeze → **HUMAN-H8** confirmatory → **EV-D** → **EV-R**; **HUMAN-H7** once dossier live
passes exist (LATER-01, 6 runs).

**What the operator does personally, disclosed as not independent:** the blind-first OPCHECK per Class-S release
(≈ 20–40 min; B-31), operational accept/reject decisions on possible duplicates (not evaluation labels; SIG-EVAL-002), the
D-K2-1 organisation review, the relevance set, copy confirmations and walkthroughs. None of these is ever reported as
independent review; wherever an operator walkthrough is counted it is written "operator walkthrough (maintainer, not
independent)" (TS-22).

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
  (OM-01, CI-checked) and, if A-21 = a, a distinct agent author identity; pushes use the operator's account.
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
  by the round's end ≈ 330 stacked PRs (#141–#190 + ≈ 280 Round-11 PRs incl. live-leg PRs); the operator may merge each
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
  planning branch's history, so the honest options are (OD-27): **(a)** publish as recorded, or **(b)** carry the
  planning files into `r11/seed` as one new commit with the address replaced, keeping the full planning history in the
  operator's private backup (OP-23) — a recorded deviation from "planning commits reach the chain unchanged". **No
  default action: the T6 push waits for the answer** (a GATE-B stall, §4.4 S2).

---

## 13. Round tail and acceptance

### 13.1 Sub-round acceptance rows (P34.47, P35.64, P36.73; S; read-only)

Each reads live state (§10.3), records a `probe-run/1` record and an acceptance note reporting the **highest layer reached
per row**, and drafts the GATE packet (agent-drafted, labelled; descoping defaults listed first). It cannot pass with an
unexplained red, a ratchet regression, a pending seed transition (11A), or a **due** leg that has not run (earliest time
passed, go held, not run); a leg whose window extends past the GATE (e.g. P34.39b to 10-29) is listed and carried
(FEA-03). It also reads the managed-certificate status and the spend report (§10.4). The exit lists are §5's
acceptance bullets and S2 §4.1–§4.4.

### 13.2 Round-level success criteria (P38.1a/b checks each on the final release; conditional on the recommended answers, §4.4)

1. **Features and UX (U-007a; D3 §3a):** all 13 journeys pass the agent walkthrough (`agent-verified`) and the operator
   walkthrough (maintainer, not independent); U-003.1–.11 pass their K-row acceptance live; every route advertised on the
   09-27 release works or shows an honest notice (ROUTES.csv; C-12); 0 UUID-only labels and 0 undated edges; every figure
   reaches its evidence in ≤ 2 clicks or says why; search covers 55 jurisdictions, 20 cities and the top 25 vendor and agency
   names; K0 budgets and accessibility pass on real data.
2. **Correctness and comprehensiveness (U-007b; D3 §3b):** L3's round targets hold on the final release (CONF-14; §5.4)
   or each miss names its fixing row; M-1b reported as measured per declared namespace (no certification figure) or "not
   attempted (default A-6)"; `/quality/` live with failing and ratchet checks shown; the coverage targets of §5.5 **including
   D3 §3(b) — OSM ALPR, Eyes on Flock (as A-22 decides) and Atlas vendor data reach place and entity pages — and the
   per-vendor Flock/Axon thresholds** (COV-05).
3. **Clarity (U-007c; D3 §3c):** §5.7's clarity list; "beautiful" is the operator's call (B-29).
4. **Honesty:** 0 S0 open; 0 status words unbound to recorded state; 0 claims from the full L3 §4.5 not-claimable list;
   PROVISIONAL on every unevaluated figure; disclosure ships in the same publish as exposure; **every landing-copy clause
   is bound to a measured check (GQ id) with a probe-run record ≤ 24 h old at the publish that ships it, or ships in its
   conditional form** (e.g. "Every claim links to the record of how SIG obtained it; links to the source documents
   themselves are being added") (TS-10).
5. **The spec tells the truth (META_PLAN §1 outcome 4; COV-16):** 0 spec MUSTs contradicted by a recorded operator decision
   without an ADR, an operator-worded waiver (A-23) or an owed row; F-31 closed or owed with its trigger.
6. **Build truth:** every boundary read head-bound CI; 0 G1 and 0 G2 violations; every due live leg executed in its window
   or re-scheduled with a date; every production statement cites a probe ≤ 24 h old; no proxy signature; every agent commit
   trailered; ≤ 1 orchestrator close-repair.
7. **Cost:** measured monthly infrastructure (GCP + Cloudflare + domains) ≤ $300 every month; the 100× traffic projection
   ≤ $300 or approved; agent spend reported each check-in against the A-2/OD-26 envelope.

A criterion disabled by a default is reported "not attempted (default <line>)", never MET.

### 13.3 The 13 acceptance journeys (D3 §2; K13 §8; walked cold from `/` at 390 and 1440 px)

| persona | journeys (budget) |
|---|---|
| local advocate, council meeting in 6 days (≤ 10 min) | **A1** type "Oklahoma City" (1 min, ≤ 3 clicks) · **A2** what is deployed, who runs and approved it, next decision (+3) · **A3** print a council brief (+2) · **A4** know what to bring (+3) |
| investigative journalist | **J1** defend a headline figure (5) · **J2** "who supplies ALPRs to Texas agencies, and who can access the data?" (10) · **J3** is this figure disputed? (3) · **J4** cite it durably (3) · **J5** what changed since the last release? (5) |
| organizers | **O1** who runs what in my county or city (3) · **O2** who decides and when; subscribe (2) · **O3** a local list without the map (2) · **O4** act on a gap (3) |

A journey passes within its budget with no wrong-conclusion risk and every fact carrying a source, an as-of date and a
release id. The agent walkthrough is recorded `agent-verified`, never "user-tested"; the operator walks each too
(OP-22), recorded "operator walkthrough (maintainer, not independent)" (TS-22).

### 13.4 The tail (P38, rows 490–499, 7.0 runs; S2 §4.5 as split at S4c)

| row | what | size |
|---|---|---|
| P38.1a/b | **CAP.1 (CAP-lite)**: independent gap analysis of landed rows against the Round-11 requirements — a: 11A + 11B, b: 11C + 11D + composed live verification with CI for every open PR, probe-run records ≤ 24 h old, two-sum headline per status layer | M + M |
| P38.2 | **CAP.3**: close small in-scope gaps; everything else becomes a DEFERRALS row with a trigger; the **accepted-deviations list**, including **every descope caused by a decision default** (§4.4) and every C-12 withdrawal | S |
| GATE-ACCEPT-R11 | the operator signs the accepted-deviations list verbatim (HG-14 domain) | — |
| P38.3a/b/c | **REC**: `reconcile-build` a: backlog + readiness, b: spec reconciliation, c: integration plan for ≈ 330 stacked PRs (operator merge legs sized here) | M + M + M |
| P38.4 | **DOC**: `refresh-repo-docs` then `agent-docs`; every production statement cites a probe-run record | M |
| P38.5 | **CAP-02**: announce-readiness review against D3 §5 | S |
| GATE-ANNOUNCE | the operator's decision; never automatic; agents contact no one; the announcement itself is LATER-22 | — |

Compared with Round 10's nine-row tail that read nothing live: 10 rows, 7.0 runs, live reads by construction; stream
acceptances (TX-16, ACQ-28, CONF-14, CAP-01) are ordinary 11D rows that measure.

### 13.5 Ready to announce (GATE-ANNOUNCE checklist; D3 §5, S2 §8.3)

The operator's own test, *"I would send this to a journalist today"* · every S0 closed live and status words bound to
recorded state · all 13 journeys pass the agent walkthrough and the operator walkthrough (maintainer, not independent) ·
D3 §3(b) holds live · **every landing-copy clause bound to a measured check ≤ 24 h old or in its conditional form**
(TS-10) · **the "spec MUSTs unmet at launch" list signed verbatim** — at least SIG-GOV-001/002/008/012/013/015, SIG-UI-042,
the HG-11 second-reviewer role and every other A-23 member not waived (TS-05) · **Q-29 revisited: keep the personal
address as the public contact, or require the `contact@` alias (OP-10) before announcing** (privacy-harm reports,
SIG-GOV-003; TS-21) · attribution gate and Part VIII screens
green, forbidden-terms sources withdrawn · pinned citation and release id on every page · zero-egress serving with the
kill switch and budget alert tested · cost at 100× traffic ≤ $300 or approved · backups, a drilled restore and alerts ·
the dispute e-mail discloses single-maintainer response times · §1 text, a known-issues page and PROVISIONAL disclosures
live · **the dedup is published** (B-26) · the gallery signed (B-29) · the About text written by the operator (C-5) · the
operator confirms the announcement copy. If GATE-ANNOUNCE is unanswered, SIG is not announced.

---

## 14. Risks

| # | risk | mitigation |
|---|---|---|
| R-1 | **Live legs never run** (Round 10's "prepared, not executed", queued) | OM-19 runs due legs at every boundary, on their own `r11/<id>-live-<n>` branches; no GATE while a leg is *due*; the OP-24 leg-runner backstop runs held-go legs while the chain is paused and alerts on a due leg it cannot run; "engineered" never reported as "live" |
| R-2 | **Defaults stall or silently descope** (31 in §4.4, incl. two stalls) | no OW/EX default acts on silence (checked); each default shown beside its criterion; descoping defaults listed first in every packet; `continue` answers batch lines only; P38.2 lists every default-caused descope for GATE-ACCEPT-R11 |
| R-3 | **Scale** (299 post-split chain rows; CAP-01 fans in ≈ 110 rows) | four gated sub-rounds; every row ≤ 1 run; contracts written per sub-round by PLAN rows with a Phase-4 sizing review; re-split rule (11B at its edge; GATE-G4b named in advance) |
| R-4 | **Operator load and approval fatigue** (S5 alone carries 99 lines over 346 decision ids; ≈ 25–40 h over ≈ 24 touchpoints) | S5 in two sittings, one line at a time; the fast path only for batch lines; descoping defaults listed first; OM-20 (if adopted); the N-1…N-7 notice allowance; readouts from P35.60's generator; cadence cuts suppressed within 14 days of a Class S promotion and moved to weekdays; weekday 14:00–20:00Z slots |
| R-5 | **Hosted-write accidents** (L44 rewrites `claim_evidence` under an exclusive lock; re-keying; Wave C ≈ 1.1 M claims on 1 vCPU) | AR-2 restore points (incl. bucket versioning before republishes); P34.6 drill first; P34.24b rehearses the exact deploy set; P34.46's numeric go/no-go; class-based never-list; AR-3; temporary tier bump; one manual job at a time |
| R-6 | **Denial of wallet** before P35.5 | P34.3 makes `sig-web` non-public; P34.5 alert; P35.5 early in 11B; measured spend at every check-in |
| R-7 | **UX outruns the data** (K13 R-1) | all Stream-L S1 fixes in 11B before new surfaces; capability binding; "records" wording until the dedup; CAP-01 checks wrong-conclusion risk |
| R-8 | **Calendar slip** — cliff-shaped, not one-for-one (§8.8) | Wave B code moved into 11B and Wave C into 11C, gos collected a GATE earlier; A-19 decides the trade-off in advance; G4 re-projects; Wave D droppable |
| R-9 | **CI unavailable or flaky** | P34.2 flake allow-list and one re-run; "CI unavailable" → `blockedOn` + verbatim, time-boxed waiver only |
| R-10 | **Rights or legal exposure without counsel** (vendor terms, vendor mirrors, database right, Part VIII) | per-batch HG-03 lines with per-member captured terms and "not flipped" defaults; no Flock/Axon fact from a vendor host or a mirror of one (A-22); robots and reservations honoured by default (A-5); Part VIII at-rest audit (P34.49) and residential demotion (P35.66); officer-naming gate (P35.28) before entity pages; redaction (P36.15) before the evidence hub and raw archive; US-first; withdrawal barrier + dispute channel as remedies |
| R-11 | **The public repo** publishes planning notes, the operator's address and redacted Part VIII findings on first push | B-16 (local until T6); SEED-00 + pre-push scan; the operator's redaction choice (§12) |
| R-12 | **Harness/model switch or usage limits mid-round** (≈ 95–270 M tokens estimated; a limit was already hit on 09-30) | OM-01/A-15: one harness, switches only at boundaries; the A-2/OD-26 envelope; `blockedOn` at a usage-limit event; per-check-in spend report; G4 re-projection |
| R-13 | **Stage B under-sized** (was: ≈ 31 ADRs + ≈ 250 draft ids + ≈ 277 contracts in 10 runs) | re-scoped (FEA-01): SEED-11 writes 23 ADRs, SEED-12 six families, SEED-13 only 11A contracts + skeletons; 11B–11D contracts and the TRANSP/K13 families move to PLAN rows; every seed unit split into ≤ 1-run contexts |
| R-14 | **Cost baseline is unverified** (G1 list-price ≈ $90–100 vs README "≈ $0/$9") | C-7 now; P34.5 billing export; GATE-G4 re-projects if the measured baseline differs materially |
| R-15 | **Baseline drift during S4/S5** (operator merges, scheduler first fires, the 10-10 replay) | the A1 delta re-runs before T6 (SEED-01); P34.39a reads the replay back; dates from the clock, never from the latest record (AR-4) |
| R-16 | **DNS move breaks TLS or routes** (Google-managed cert expires 2026-12-22; renewal fails if LB hostnames are proxied) | P34.50 runbook (DNS-only LB records, TTL step-down, DNSSEC handling, rollback); P35.67 probes after the move and ≈ 11-22; TLS-expiry alert at 21 days |
| R-17 | **Personal data stays public while the round runs** (handles in the repo tip, the listable bucket, ids; history) | A-0 removal-only actions now; RI-01 acceptance covers repo + bucket + all id kinds + values; A-0.4 history line before any deposit |

---

## 15. Explicitly deferred (each with its trigger)

| unit | what | trigger | runs · $/mo |
|---|---|---|---|
| LATER-01 | T-EVAL-IND segment (EV1, H6, EV-F, H8, EV-D, EV-R; H7) | T-EVAL-IND (§11.3) | 6 · +10 |
| LATER-02 | usability study on the live site | participants available and contact authorised (Q-28 reversed) | 1 |
| LATER-03 | contribution-back to OSM/MapRoulette | the operator opts into contribution-back and outside contact | 1 |
| LATER-04 | outreach, records-request sending, recruiting | the operator revisits U-011 | 1 |
| LATER-05 | counsel packet and written opinion | the operator obtains counsel (≈ $0 pro bono … ≈ $3.5k–10.5k paid) | 0.5 |
| LATER-06 | authenticated contributor accounts (D-R7.1-AUTH) | demand beyond the vetted curator set + moderation/safety plan + threat model | 2 |
| LATER-07 | know-your-rights content (BL-041) | an intake/onboarding surface opens | 0.5 |
| LATER-08 | Cloud SQL permanent scale-up and HA | sustained CPU/latency or disk past ADR-022's threshold | 0.5 · +49 |
| LATER-09 | acquisition long tail: Tier-2 remainder (130), Tier 3, EDGAR, courts, OCDS, paid data, tribal/territory channels; **R11-ACQ-23a/b** international portals and OGC WFS | per-family triggers (I8 §6.3); EDGAR after the alias; paid data needs Q-21 > $0; ACQ-23a/b when the operator revisits US-first and answers B-34 "a" | 2 (+2) |
| LATER-10 | non-US keyed traffic APIs (QLD, NSW) | non-US expansion decided and keys registered | 1 |
| LATER-11 | OCR / model-assisted parsing | an admitted source needs OCR (SIG-LLM-001) | 1 |
| LATER-12 | claim-text/entity-scoped search, ZIP lookup, deferred K12b ideas (I-15 comparison, I-20 embeddable cards, I-29 Flock portal view; I-24 agreement markers, I-27 per-place question pages) | CAP-01 passes and the item is prioritised | 1 |
| LATER-13 | closeout-journal cutover | parallel dispatch, a multi-worktree build or a second harness writing memory | 1 |
| LATER-14 | whole-LEDGER rotation per round | LEDGER > 1 MiB | 0.5 |
| LATER-15 | operator-only signing key for gate signatures (G4c) | the operator adopts Q-B4-2 (**A-16 recommends doing so now** — Appendix B) | 0.5 |
| LATER-16 | whole-graph canvas (> 3,000 labelled nodes) | a single view needs > 3,000 labelled nodes | 2 |
| LATER-17 | OpenGov procurement source | a documented public endpoint with reviewable terms | 1 |
| LATER-18 | second model family for agent review | the operator answers Q-L3-4 yes | 0.5 |
| LATER-19 | cost reductions (scheduler consolidation, min-instances 0, Cloud SQL CUD) | spend approaches the ceiling or the operator asks | 1 · −47 |
| LATER-20 | legacy bucket retirement | 90 days after P35.59 (dark cutover); `sig-public` root frozen until downloads move | 0.5 |
| LATER-21 | CI runners to Ubuntu 26 | after TC-PIN, before 24.04 end of support | 0.5 |
| LATER-22 | Round-11 announcement and public launch | CAP-02 passes and the operator says go | 0 |

**Recorded, not just listed (COV-10):** SEED-14 writes every LATER unit above and R11-ACQ-23a/b, and every one of the 153
`later-phase` universe items, into a committed register — a DEFERRALS row (or a BL row for backlog items) with its trigger
and, where time-bound, its date (LATER-21: before the 24.04 runner's end of support; LATER-20: 90 days after P35.59) —
generated by a committed script from `universe/UNIVERSE_DISPOSED.csv`, with `ADR_TRIGGERS.csv` cross-references for the 56
trigger-type items; `check_backlog` / the obligation checks verify the counts (24 units; 153 items). LATER-15 closes early
if A-16 = yes (T3 adds the CI verification to P34.28 and an operator setup item). The three non-US D-SOURCES.8-1 rows wait
under LATER-09/10 (trigger: the operator expands non-US coverage).

Also deferred, outside the catalog: the 45 quiet ADR revisit triggers (watched through `ADR_TRIGGERS.csv`); GraphQL
(RISK-P14-10, on consumer demand); a contradiction to an Atlas row (RISK-P4-08); the next technology-vocabulary version
(SIG-ONTO-057a); Tier 3 (259 candidates) is not acquired at all.

---

## Appendix A — Stage-B translation checklist (exact artifacts T1–T6 must produce)

Stage B starts only after GATE-P is recorded under the §1.3 rule. Every artifact is append-only where it touches a
protected record (OM-13), dated from `date -u`, and committed on `r11/seed`. Catalog units in brackets (S1a); est. runs
from `data/round11_plan.csv` (seed total 23.25 runs in ≈ 29 contexts of ≤ 1 run; each unit's `notes` name its seams).
**Re-scoped at S4c (FEA-01):** Stage B writes the seed, the operator-decision ADRs, six requirement families, the manifest
for every row and **full contracts only for 11A and PLAN-11B**; 11B–11D contracts are written by the PLAN rows.

**T0 — before GATE-P (planning orchestrator) [SEED-00, 0.5]**
- [ ] META_PLAN §11: one appended, dated correction entry naming each late-stamped change-log line (F-074), and a
      refreshed CURRENT STATE block.
- [ ] Forward-fix the credential-shaped `SIG_INTAKE_*` literal in the two committed planning notes; `make scan-secrets`
      and `test_secret_scan_real_tree_is_clean` pass on the planning tree.
- [ ] If A-0 = a: run A-0.1–A-0.3 as Track-0 actions (each with its own go, pre-state, restore point and probe) and record
      them in `baseline/TRACK0_RECORD.md`; record A-0.4's answer.

**T1 — Spec amendments and ADRs [SEED-11 3.0 = 3 contexts, SEED-12 3.0 = 3 contexts]**
- [ ] `docs/research/_meta/spec_src/96c_partXII_s56_round11.md` (new; name proposed): Part XII, §56 Round-11 contract
      extension with the **MEM, ENG, OPS, SEC, REL and CONF** families under final ids (TRANSP → PLAN-11B, K13 → PLAN-11C);
      T1 records the draft-id → final-id map and de-duplicates draft ids listed under two families.
- [ ] Amendments of §6.3 in their owning `spec_src` section files; one new **Appendix G.7** row set
      (`99c_appG_corrections.md`) incl. the §55 true dates; **Appendix F** rows for every new ADR (`99a_appF_adr.md`);
      family table updated for newly opened prefixes.
- [ ] `BUILD.sh` regenerates `docs/2_canonical_design_spec.md`; `check_spec_src.py` green; new ids append-only; R10-A6
      untouched.
- [ ] `docs/3_sig_golive_spec.md`: goal 5, GL-GATE-01/02/05, gate register, GL-GATE-06…08 (E2-18; ADR-145 pattern).
- [ ] `docs/adr/ADR-146…` — **only the 23 ADRs whose §7 author is SEED-11**, template header, the operator's words where
      the decision is theirs (EVAL-004 waiver, A-23 waivers, counsel basis, robots, standing go), each stored with the
      sha256 of the text shown and the "agent-drafted, adopted by the operator" label where applicable; `## Revisit
      trigger` in each. The ten engineering ADRs are written by their owning tickets.
- [ ] Appended `Superseded by ADR-nnn (<date -u>)` status lines on every superseded landed ADR (incl. ADR-015, 058 §3,
      075, 092, 096 §1, 091 §3–4, 097 §2–3/§6 if A-12 = a, 105 §5, 118 §2, 126/127 cutover statements, 088's clause) and the
      `Qualified by` / `Amended by` / `Extended by` lines of §7 (incl. ADR-086/106 → ADR-167); recorded evaluations of the
      fired revisit triggers (F3 §5.1). No other landed-ADR edit. (ADR-016/076 lines are appended by P35.1a with ADR-174.)
- [ ] ADR index regenerated (`build-memory adr-index`).
- [ ] If A-12 = a: `AGENTS.md` gotcha 6 and `web/AGENTS.md` gotcha 1 replacement text (K0 §7.1–7.2).

**T2 — Build-memory repair seed [SEED-01…10, SEED-16; 7.75 runs]**
- [ ] SEED-01 C0 preflight: the operator's go for control-ledger edits recorded; A1 delta re-run; `<PRE>` pinned.
- [ ] SEED-02 guard core: `docs/build/tools/memory_guard.py` (G1 diff mode, G2 core, G4a/G4b), policies under
      `docs/build/tools/record_policy/`, `make docs-check-memory/-spec/-matrix`, a memory-guard step in the PR-triggered
      `docs` job, pytest collecting `docs/build/tools/test_*.py`, `ci_boundary.py` (G3a). (The `push` trigger is P34.1's,
      CF-01.)
- [ ] SEED-03 the six living-record pin conversions (PKG-02).
- [ ] SEED-04 `docs/build/reports/memory-repair/`: `README.md`, `date_corrections.csv` (promoted from `data/date_drift.csv`),
      `append_only_register.csv`, `pending_transitions` (CF-03).
- [ ] SEED-05 `PHASE LOG INDEX — Rounds 1–10` (hash-anchored CSV) and a `PHASE LOG — Round 11` section as the only
      append target.
- [ ] SEED-06 **restore the 53 GATE DECISIONS rows deleted by `c2055d96` first**, from `c2055d96^`, then append a dated
      annotation table of every restored row that is clock-false, blanket/delegated or a counsel claim (TS-08);
      `date_corrections.csv` extended to the restored block; G1 gains a restored-dates-vs-`git blame` mode.
- [ ] SEED-07 DATE CORRECTION entries in LEDGER and BUILD_INDEX.
- [ ] SEED-08 correction records elsewhere: DEFERRALS correction section; manifest Plan-extension correction lines;
      runs/pr/CAPSTONE addenda; `CORRECTION.md` in the committed fixture-run directories; **annotations with B7's facts on
      ACCEPT-R8, ACCEPT-R10 and GATE-G3 — no operator addendum describing a past state of mind**; C-13's answer recorded with
      its own `date -u` (TS-08); the `p-17b713` supersession record — **no footers on landed ADRs** (CF-02).
- [ ] SEED-09 BUILD_INDEX index repairs (rows 190/195, PR fills, seq 170a, not-landed note).
- [ ] SEED-10 archive LEDGER lines 1–54 byte-for-byte under `reports/memory-repair/` with a sha256 pointer; slim head
      ≤ 12 KiB; status PAUSED.
- [ ] SEED-16 RETURN PASS superseding note + `RETURN PASS — current` regenerated from `OPERATIONAL_READINESS.md §(f3)` and
      the S1b dispositions; no 184–187 ids.

**T3 — Manifest rows and contracts [SEED-13 4.0 = 4 contexts: manifest + skeletons | 11A rows 201–220 | 221–240 | 241–258 + PLAN-11B]**
- [ ] `docs/tickets/00_MANIFEST.md`: Round-11 dispatch amendment + banner (P34 11A "Safe, honest, truthful" · P35 11B
      "Correct and traceable" · P36 11C "Explorable core" · P37 11D "Explored and proven" · P38 tail); **rows 201–499 from
      `data/round11_plan.csv` as they stand (already split; +2 only under the A-13 fallback)**; gate rows without `.n`;
      one appended `## Plan extensions` line naming PLAN-11B/11C/11D as the later contract authors; a `## Human
      prerequisites` section listing OP-01…OP-24 with due points; the L3 §6.3 dispatch amendment and the 184–187
      gate-cell tokens; HG-05 as an operator-owned integration disposition.
- [ ] **Full contracts only for the 58 11A rows and PLAN-11B** from `_TEMPLATE.md` (+ `harness:` header + B5 §6.2 block):
      `Run:` line, `live_verification`, `Live window:` and the live-leg re-run prompt where windowed, OM-14 mutation list,
      `live:` edges, requirement ids, acceptance stated at its layer, the OM-20 status of the row. **`Kind: skeleton`
      contracts for every 11B–11D and tail row**, each naming the PLAN row that completes it.
- [ ] Contract notes on 184–187; "Superseded — not executed" sections on `HUMAN-H4.md` / `HUMAN-H5.md`; no H6/H7 files.
- [ ] Requirement → ticket index; a fresh-context decompose-spec Phase-4 sizing review of 11A.

**T4 — Register mapping and validators [SEED-14 2.0, SEED-15 1.0]**
- [ ] `docs/tickets/DEFERRALS.md`: appended annotations for all 36 owed rows per §9.2; new OPEN rows (counsel opinion,
      SEC-003 owner, second reviewer/board trigger, ADR-124 allow row, the D-rows MET-ENGINEERED verdicts need, every A-23
      member left unwaived); **every LATER unit and every later-phase universe item recorded with its trigger and date by a
      committed generator script (COV-10)**; token transitions only queued (CF-03).
- [ ] `docs/build/BACKLOG.csv/.md`: closures with evidence, splits, new rows from BL-059 (incl. the EVAL-004 waiver
      revisit row), RISK duplicate-id renames, RISK-P21-03 route.
- [ ] `docs/build/COVERAGE_MATRIX.csv`: verdict vocabulary + `required_domain`/`achieved_domain`/`owed_legs`/
      `accepted_scope`; F2a/F2b/L3 deltas (§6.6) with Appendix B's corrections; each change a `coverage-assessment/1` event.
      (The 61-row re-verdict is P34.48.)
- [ ] `check_coverage_matrix.py` grammar + cross-checks + spec-derived counts (incl. "an amendment that weakens a MUST is
      a waiver"); `check_backlog.py` open-home rule; new `ADR_TRIGGERS.csv` (incl. Q-29's revisit); validator V2 skips
      superseded manifest rows (COV-14); `tools/check_dispositions.py`: rules (a) and (c) read `data/round11_plan.csv`
      (`sub_round ∈ {11A, 11B}`; the S2/S4c units become visible, COV-13), rule (d) extended to W2-1…6, PF-1…3 and GM-1
      (added to the universe; COV-03), and the S4c `acts_on_silence` rule folded in from the scratch `check_silence.py`
      (TS-02).

**T5 — LEDGER seed and resume prompt [SEED-17 1.0]**
- [ ] CURRENT STATE (values only, ≤ 3 KiB): `round: 11`, `nextTicket: 201` (P34.1; P34.0a under the A-13 fallback),
      `chainTip` / base per §12, `dispatchTarget`, **`harness:`** (CF-04, A-15), `blockedOn`, `returnPass`, `updatedAt`
      from `date -u`; status PAUSED until C10.
- [ ] OPERATING MODE — Round 11: OM-01…OM-20 (§3.3, S4c wording incl. OM-01's trailer rule and the class-based never-list),
      H2 §7 paste blocks (G3a gate, flake rule), G2 §2 activation rules, P16 "alias first" contact rule, the D-P31.4-1
      clock guard, the `git merge-base --is-ancestor origin/main <chainTip>` boundary record (COV-14), the agent author
      identity (A-21), `dispatchTarget = subagent-safe sizing`, B6 §5.3 overrides if skills are deferred.
- [ ] The leg-runner backstop prompt (OM-19; scheduled by the operator as OP-24).
- [ ] GATE DECISIONS rows for GATE-M and GATE-P, verbatim with the `date -u` of receipt.
- [ ] Stale-token scan of the head = 0; every path named in the head exists.

**T6 — Validation, dry-run and handoff [SEED-18 0.5, SEED-19 0.5]**
- [ ] Projection regenerated and verified; every validator green (existing + guard core + new checkers); A1 delta re-run.
- [ ] Pre-push scan (B-16) and the operator's **OD-27** answer applied (§12; no push without it); OP-05 settings applied;
      push `r11/seed`; seed PR to `devin/p33-8-agent-docs-refresh` **5/5 green** on its head. If row 201 cannot land
      before 2026-10-19, the seed PR pins `runs-on: ubuntu-24.04` (FEA-16).
- [ ] Read-only `orchestrate-build` orient dry-run resolves **row 201 = P34.1 TC-PIN**.
- [ ] `PD/HANDOFF.md` with the exact resume prompt (harness, model, worktree, branch, first row, OPERATING MODE pointer).
- [ ] **GATE-B** recorded verbatim, with the 11A OM-20 list exactly as S5-3 was answered (none under its default); C10 flips
      the LEDGER to IN_PROGRESS.

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

---

## Appendix C — Evidence index (where each part of this plan comes from)

Notes named below without a section number (E3, F3, F5, J4, K1–K12, I1–I7) were read through the synthesis rows that
cite them (S1a, S1b, S1c, S2, K13, L3, I8), not re-read whole for this row.

| plan section | primary evidence |
|---|---|
| §0, §8 | `design/S2-round-structure.md`; `data/round11_plan.csv` |
| §1, §4.1 | `META_PLAN.md` §7.1; `feedback/OPERATOR_FEEDBACK.md` |
| §2 | `baseline/BASELINE.md`, `baseline/TRACK0_RECORD.md`; `findings/REGISTER.md`; `review/REVIEW_SYNTHESIS.md`; L2 |
| §3 | `META_PLAN.md` §3; `research/B5-orchestration-retro.md` §6; S2 §3.5 |
| §4.2–§4.5 | `design/S1c-decision-catalog.md` §2–§9; `data/decision_catalog.csv`; S2 §7.3, §11 |
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

*End of draft. S3 written 2026-10-01T01:13:07Z → 01:26:35Z; revised at S4c 2026-10-01T02:38:06Z → 2026-10-01T02:55:12Z (`date -u`).
The three S4 reviews are closed in `reviews/REVIEW_CLOSURE.md`. Next: S5 / GATE-P (two sittings, one line at a time).*
