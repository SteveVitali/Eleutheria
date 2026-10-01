# SIG Round 11 — the next-phase plan

> **DRAFT — pending S4 adversarial reviews and S5 operator ratification (GATE-P).** Nothing in this document is a
> decision until the operator ratifies it verbatim at S5. Recommendations are the agent's; every decision is the
> operator's. Text marked *agent-drafted* ships only after the operator confirms it word for word (META_PLAN §2).
> This is not legal advice (P4).

- **Row:** S3 of `META_PLAN.md` (Stage P, synthesis). **Drafted:** 2026-10-01T01:13:07Z → see footer (`date -u`), by
  Claude Code (Opus 5.5) in the planning worktree `~/Eleutheria-next-phase`, branch
  `claude/next-phase-planning`, HEAD `9262a959`. Chain tip: `b051732c` (`devin/p33-8-agent-docs-refresh`, PR #190).
- **Read-only (P3, P10).** This row writes only this file. No control file, spec, ADR, manifest, LEDGER, register or
  production system was touched, and nothing was committed. No external request was made (P16). No secret appears
  here (P14); the operator's e-mail address is written only as "the operator's address".
- **Evidence class.** `inference` from the cited planning artifacts, except counts, which are the mechanical outputs of
  those artifacts' own checkers (S1a `check_catalog.py`, S1b `tools/check_dispositions.py`, S2's plan builder). Every
  path below is relative to `PD = docs/build/planning/2026-09-30-next-phase/` unless it starts with `docs/`, a package
  name or `~`.
- **Synthesis inputs (P1: read for this row, in the sections this plan cites):** `META_PLAN.md` §1–§5, §7, §7.1, §8–§11
  and Appendices A–C; `feedback/OPERATOR_FEEDBACK.md` (U-001…U-015, whole); `design/S2-round-structure.md` (whole) +
  `data/round11_plan.csv` (all 333 rows, by script); `data/ticket_catalog.csv` (by script) + `research/S1a-ticket-catalog.md`
  (whole); `universe/DISPOSITIONS.md` (whole) + `universe/UNIVERSE_DISPOSED.csv` (by script); `design/S1c-decision-catalog.md`
  §0–§9 + `data/decision_catalog.csv` (selected rows); `design/D3-product-direction.md` (whole); K13 §0, §5, §6, §8–§11;
  L3 §0, §2, §6–§8; I8 §0, §9, §11; J3 §0; G2 §0; G3 §0, §10; B3 §1; B4 §0, §5; E2 §0, §6; K0 §0; H1 §1–§3; H2 §0;
  B5 §0, §6; B1 §1, §8; F2a §1–§3; F2b §1–§2; G1 §0, §4; B6 §0; B7 §0; `findings/REGISTER.md` (summary + S0/S1 table) and
  `findings/FINDINGS.csv` (counts); `baseline/BASELINE.md`, `baseline/TRACK0_RECORD.md` §0.5; `review/REVIEW_SYNTHESIS.md`
  (RI-01…06 rows); spec headings and id families in `docs/2_canonical_design_spec.md` (by grep).
- **Precedence.** Where inputs disagree, the later synthesis row wins (S2 over S1a/S1b/S1c; L3 over F4/F2b; S1c/S1b over
  E2/F2b for post-D1 answers). Every disagreement this draft had to settle is listed in **Appendix B** for S4.

---

## 0. The plan on one page

**Round 11 makes SIG show, correct and open up the evidence it already holds, while growing US-wide vendor coverage
from high-quality origins** (D3 §0). It runs as **one round, one manifest, one LEDGER and one `orchestrate-build`
loop**, cut into four gated sub-rounds and a short tail (S2 §0, §3.3; U-012 "follow the existing patterns").

| unit | phase | chain rows | est. runs | purpose | ends with |
|---|---|---|---:|---|---|
| Stage-B seed | — | 20 units (not chain rows) | 23.2 | truthful memory, guard core, ADRs, spec, manifest, registers | **GATE-B** |
| **11A** Safe, honest, truthful | P34 | 48 (201–248) | 44.0 | every S0 closed live; production protected; CI pinned and read; memory guards; Round-10 schema live; quality baseline | P34.47 + **GATE-G4** |
| **11B** Correct and traceable | P35 | 65 (249–313) | 62.5 | identity/time/geography fixes; transparency exports; release pipeline; Wave A; **first model release** | P35.63 (HG-11) + P35.64 + **GATE-G5** |
| **11C** Explorable core | P36 | 74 (314–387) | 65.0 | Wave B; design system; a working page for every U-003 ask; core-surfaces release | P36.72 (HG-11) + P36.73 + **GATE-G6** |
| **11D** Explored and proven | P37 | 68 (388–455) | 62.0 | Wave C (+ conditional D); graphs and explorer; `/quality/`; final release; 13 journeys | P37.65 (HG-11) + P37.68 CAP-01 |
| **Tail** | P38 | 7 (456–462) | 5.0 | CAP-lite → **GATE-ACCEPT-R11** → REC → DOC → announce review → **GATE-ANNOUNCE** | — |
| **total** | P34–P38 | **262** (≈ 277 after T3's a/b splits) | **238.5** (229.0 without 9.5 conditional runs) | | 5 gate markers, 11 in-ticket pauses |

- **First dispatch:** row 201 = **P34.1 TC-PIN** (toolchain pin; must land before **2026-10-19**, when
  `ubuntu-latest` moves to Ubuntu 26).
- **Every S0/S1 finding** (113) has exactly one owner, and the 76 owner units plus their prerequisites (78 runs) all sit in
  11A ∪ 11B (S2 §2.2, §12). All 9 S0 findings are closed **live** in 11A.
- **The work universe** is 1,159 items with exactly one disposition each, 0 errors (S1b; §9 below).
- **Human work:** no Round-11 HUMAN rows. Rows 184–187 are superseded markers; independent evaluation stays owed under
  trigger **T-EVAL-IND** (L3 §6). Agents contact no one outside the project (U-011).
- **Money:** projected infrastructure ≈ $95–105/mo after 11A, rising to ≈ $123–133/mo after 11D, against the **$300/mo**
  ceiling (U-008). Nothing planned needs an over-$300 approval. Agent spend is reported separately each sub-round (§10.4).
- **Operator time:** ≈ 12–18 h over ≈ 9–10 weeks, batched into about five sittings (S2 §7.4).
- **Calendar (inference, slips one-for-one with the seed date R0):** seed ≈ 10-03→10-06; 11A ends ≈ 10-15→10-17; 11B ≈
  10-27→10-30; GATE-G6 ≈ 11-13→11-16; 11D ≈ 12-02→12-05; tail ≈ 12-05→12-10 (S2 §5.4).
- **What S5 must decide:** the S1c packet (87 lines; Part A 17 → **18 with B-24 promoted**), plus OM-19/OM-20 and the
  GATE-B pre-authorisation list (§4.5). **Nine defaults quietly descope operator asks** and one stalls the critical path;
  each is shown beside the criterion it disables (§4.4).

---

## 1. Brief and authority

### 1.1 What the operator asked for (verbatim, with `date -u` of receipt; full text in `feedback/OPERATOR_FEEDBACK.md` and META_PLAN §7.1)

| when (UTC) | operator, verbatim (excerpt) | what it set |
|---|---|---|
| 2026-09-30T16:16Z (GATE-M) | *"I approve the meta-plan. … And don't merge the PR chain, we'll just build off of it and I'll handle merging later."* | Stage P; Round 11 stacks on #190; the operator merges later |
| 2026-09-30, Wave 2 | *"… do an extremely careful, rigorous, and comprehensive search and review of additional datasets we might be missing and to configure them for ingestion and ingest them into prod. … making the data itself easily exportable … explore each third party source, link to the ground truth, download the raw data, and see ingestion logs/metrics/timestamps …"* | Streams I and J; new sources ingested **in the Round-11 build** |
| 2026-09-30T18:2xZ (stamp as recorded; see F-074) | *"I want to do all of what you are suggesting, but this work should be planned/specified in the next round of tickets, not done now."* | S0 hotfixes and QA-1…QA-10 become Round-11 tickets; alerts route to the operator's address |
| 2026-09-30T21:28:52Z (U-003) | eleven numbered asks (map, network labels and global graph(s), search, grouped dossiers, sources per dossier, embedded visuals, watch QA, evidence, sortable sources with downloads, source pages, research queue) plus *"… the site be more user friendly and have richer, more interactive, searchable, traversable, inspectable … functionality"* and *"think and research and reason carefully about perhaps breaking with our no-JS constraints"* | Stream K; basemap reverses Round-9 Q8; the zero-JS rule is re-decided |
| 2026-09-30T21:58:23Z (U-005) | *"journalists need to be able to really truly explore the knowledge graph … always with full explicit transparent evidence/lineage"* | journalist journeys are primary |
| U-006 | *"I'm not that confident because I haven't done a deep audit of the mechanism by which disparate sources … are synthesized into a deduplicated knowledge graph"* | Stream L |
| U-007 | *"feature richness …, correctness and comprehensiveness of the knowledge graph data itself …, and generally it just needs to be better at making itself … clear to the user … the focus is on rich, US nationwide data on Flock and Axon and likely other vendors"* | the three outcomes (§13.2); US-nationwide vendor focus |
| U-008 | *"ideally we can keep monthly compute/storage/hosting/etc. costs below $300/mo … always check with me before proceeding with increased spend above $300/mo; … assume we have no humans on our team other than me augmented by agents"* | $300 ceiling; no human rows |
| U-009 | *"we will announce surveillancegraph.org publicly without holding back when the time is right."* | GATE-ANNOUNCE, never automatic |
| U-011 | *"agents should have maximal autonomy but budgets on money spent should always be made clear … and no one should be contacted outside the project."* | autonomy with spend transparency; no outreach |
| U-012 | *"previous builds worked pretty well so we can follow the existing patterns."* | one round, existing loop and gates |
| U-013 | *"\"counsel\" so far is just me …, we don't have counsel and for now we should just err on the side of not blocking on counsel decisions."* | no counsel-implying text; counsel-dependent MUSTs → waiver or later |
| 2026-10-01T00:09:20Z (Track 0.5) | approval of minimal alerting to the operator's address | alert channel, 2 uptime checks, 4 policies live |

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

This plan does **not** advance `docs/build/LEDGER.md`, sign or pre-answer any gate, amend the spec, write an ADR, or
open a PR. Stage B does those things, from this plan once ratified.

---

## 2. Baseline (what is live, what is broken)

### 2.1 What is live (A1 freeze 2026-09-30T16:31:55Z, `baseline/BASELINE.md`; live-read)

- **Public release** `sig-2026-09-27-ce480ab1` (132 artifacts, 1.05 GB, 12 compartments) behind the global LB at
  surveillancegraph.org. Content pages ship 0 `<script>`; three islands (`/map/`, `/network/`, `/search/`).
  No release id or commit in served HTML (F-11). `resolver_version = 0.0.0`; not belief-pinned (G3 NEW-1…3).
- **Runtime:** Cloud Run `sig-web`, `sig-api` (min 1), `sig-alerts` (on `:latest`, F-12); 88 Cloud Run jobs (all
  digest-pinned); 79 Cloud Scheduler jobs, 33 firing for the first time 10-01…10-21, the OSM monthly replay at
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
| F-096 (RI-05) | `/visual-language/` asserts fixture facts about real named agencies and a vendor | P34.17 |
| F-097, F-131 (RI-01) | personal ArcGIS account handles inside public source ids | P34.18 → P34.21 |
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
  after one-line approvals (F-29); gates used as a throughput device (F-36). This planning round repeated the date drift
  once (F-074).
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
| P16 operator identity | contact string = the operator's name + address until the `contact@` alias exists (U-014; C-8 asks "alias first") | connector config review |
| (new) windows | **OM-19** dated live-leg queue | acceptance rows read the queue |
| (new) autonomy | **OM-20** + OM-10 + OM-18 | GATE packets list exact row ids |

### 3.3 The operating clauses (summaries; full paste block B5 §6.1 and S2 §3.5)

OM-01 one harness + model per round, recorded in a `harness:` key and every run ledger; switches only at a boundary ·
OM-02 the worker closes its own ticket in one commit after the PR exists; two orchestrator repairs in a round → `blockedOn` ·
OM-03 rows enter only from a reviewed plan (`decompose-spec mode=extend`) · OM-04 every date from `date -u` or git/GitHub
time; never a "chain date" · OM-05 read the PR's head-bound checks after push; red/missing → `blockedOn` · OM-06 every
status names its layer (engineered · fixture-verified · staging-verified · live-executed · public · human-completed) ·
OM-07 gate records quote the operator verbatim; agent text confirmed against its sha256 prefix · OM-08 no proxy
signatures; operator-reported counsel is `operator-reported` · OM-09 hedged words get a yes/no question · OM-10 no
unbounded pre-answers · OM-11 human work is scheduled with an owner or deferred with a trigger, never silently ·
OM-12 `blockedOn` is used · OM-13 protected regions only gain lines · OM-14 no production mutation outside a ticket that
names it · OM-15 tests assert invariants, never living records · OM-16 size budget (default 3,000 changed lines) and a
tail that reads live state · OM-17 boundary lines + an operator digest with merges read from GitHub · OM-18 stop and ask;
**silence is never consent**.

**OM-19 (new) — windows and the live-leg queue.** A contract whose live stage has a window or a named go carries a
`Live window:` header. Outside the window or without the go, the ticket lands engineering and staging; the live leg goes
into RETURN PASS with its window, go id and re-run line; the chain continues. At every boundary the orchestrator compares
`date -u` and live scheduler state with the queue and re-runs due legs before dispatching. A row that needs a queued leg's
**live result** (`live:` edge) waits. No GATE packet is presented while an opened window's leg is unexecuted.

**OM-20 (new) — bounded pre-authorisation.** At GATE-B and each sub-round GATE the operator may pre-authorise the named
production mutations of the next sub-round: exact row ids, each contract's mutation, restore point, expiry at the next
GATE. **Never pre-authorised:** HG-11/Class S promotions and republishes, ING-GO, HG-03 flips, the spine schema change
(P34.46), the bounded apply (P35.61), the Wave-C tier bump, any spend above $300/mo. A red probe, a failed restore point or
a production read that contradicts a record voids it for the affected rows. Without OM-20, about 84 production-touching
rows become in-ticket pauses (S2 §7.1).

### 3.4 Constraints the operator fixed (not re-asked)

≤ $300/mo infrastructure without an explicit go on a shown trade-off (U-008) · no humans besides the operator (U-008) ·
no contact outside the project: no outreach, recruiting, records-request sending or contribution-back posting (U-011) ·
do not block on counsel; no text may imply counsel exists (U-013) · agents never merge, retarget, tag or push `main`
(§7.1) · alerts route to the operator's address · the public dispute contact is the operator's address for now (Q-29;
an operator-accepted risk with a revisit trigger) · publication is never pre-authorised.

---

## 4. Decisions: ratified so far, and what S5 must decide

### 4.1 Ratified (recorded verbatim in META_PLAN §7.1; re-cited, not re-asked)

| decision | answer on record | consequence in this plan |
|---|---|---|
| Q-1 meta-plan; Q-3 worktree; Q-4 Stage-P driver; Q-5 Chrome; Q-6 D1 mode | approved / as recommended | planning ran as recorded |
| Q-2 Track 0.1/0.2; PITR; Track 0.3 | backups + `/curate/` removal approved; PITR delegated and done; MapRoulette key stays stale | §2.2 |
| Q-11 / Track 0.4 | agents do not merge; Round 11 builds on the chain; the operator merges later | §12 |
| Production fixes (18:2xZ) | S0 hotfixes, QA-1…QA-10 and `/task/new/` pages approved in principle, specified as Round-11 tickets | 11A rows P34.3–P34.21 |
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

### 4.2 Part A — decide before the seed (S1c §2, amended by S2: **18 lines**)

| line | decision | recommendation | default if unanswered | what the default does to this plan |
|---|---|---|---|---|
| **A-1** | Track-0 exception for QA-3/QA-4/QA-9 before the first-fire wave and the 10-10 replay | **a** — now reduced by Track 0.5 to the **QA-9 restore drill before 10-10** (and QA-4's TLS alert) | no exception; risk accepted | drill waits for P34.6 (after the replay) |
| **A-2** | what the $300 ceiling covers; budget alert + billing export now | **a**: infrastructure only, agent spend reported separately · **yes**, now | infra-only; alert in P34.5 | the denial-of-wallet window stays open until P34.5 |
| **A-3** | DNS to Cloudflare for an R2 $0-egress origin; $50/mo egress ceiling + kill switch; `contact@` routing | **a** | no DNS move | **descope + cost** (§4.4) |
| **A-4** | governance posture package: disclosed single-maintainer, no-counsel (members Q-E2-06/07/08/09/10/13/14) | **a** | spec unchanged; members stay owed; false claims still removed | governance ADRs not written; GOV ids stay PARTIAL/MISSING |
| **A-5** | robots (GL-GATE-08) | **b**: honour explicit disallows and TDM reservations on non-US hosts; keep the disregard for US public bodies | GL-GATE-08 stands; opt-out register and reservation refusal built either way | none on the chain |
| **A-6** | evaluation: supersede 184–187, no Round-11 human rows, auto-collapse only C0–C2, **SIG-EVAL-004 WAIVED(ADR) for C0–C2 in the operator's own words** | **a** | no automatic collapse at all; ranged "possible duplicate" counts | P35.46–47 publish intervals only; B-26 announce criterion still holdable |
| **A-7** | rights stance (Q-19) + Tier-1 batches RB-01…07, RB-09, RG1–5, E4 B1/B5/B6, X3 | **a** | nothing flips | **descope**: Waves B/C activate nothing |
| **A-8** | withdraw 5,267 rows whose own terms forbid redistribution / are NC/ND / "demo"; restrict `camreg_txdot_rep_tx` | **yes**; I7-C1 **b** | withdraw + restrict | none (conservative) |
| **A-9** | is SIG's use non-commercial? | **b** "is or may be commercial" → NC sources are facts-only pointers | b | none |
| **A-10** | D-K2-1: how the 969 review-flagged organisations become publishable | **a+b+c**: operator top-50 review (≈ 1–2 h) + ADR auto-allowing registry-matched organisations + the rest withheld with typed absence | all withheld | **descope** (§4.4) |
| **A-11** | D-K13-1: the "global graph" as aggregated overview graphs (≤ 3,000 nodes each) + entity egos + `/explore/` | **a** | a | none |
| **A-12** | D-K0-1: HTML-first page types replace the zero-JS rule | **a** | three islands only | **descope** (§4.4) |
| **A-13** | seed contents (restore-first, correction ADR, guard core, PKG-02; D-R10-MEMORY-1 split; P34+/rows 201+) | **a** | records-only seed | **risk**: seed PR red on six pins; rows renumber +2 (CF-01) |
| **A-14** | apply the B6 skill changes (Tier A before Stage B; Tier B-must before first dispatch) | **a** | OPERATING MODE overrides (B6 §5.3) | none on rows; weaker mechanical backstop |
| **A-15** | execution model: Claude Code for the whole round; pause rules; one digest + spend line per check-in | **a** | same | — |
| **A-16** | gate authenticity: an operator-only signing key for gate commits, verified in CI; tentative words never recorded as decisions | **yes / yes** | verbatim quotes + clock stamps only | LATER-15 stays later |
| **A-17** | ratify D3: order, US-first, co-primary journeys (advocate wins conflicts), Flock/Axon facts never fetched from vendor hosts, D3 §5 as the announce gate, CHART-025 amended | **a** | a | — |
| **A-18 (= B-24, promoted by S2)** | HG-03 for boundary sources `census_gazetteer_tiger` + `natural_earth_10m` (public domain), after terms capture (D-K4-1) | **yes** | **no** | **stall**: P35.17 cannot capture boundaries → P35.19, P35.45 and the first model release P35.63 wait; 7 jurisdiction S1s stay open |

### 4.3 Parts B, C and D2 (S1c §3–§5)

- **Part B — 42 batch lines with safe defaults** (B-24 moved to Part A). Load-bearing lines for this plan: **B-1** Wave-0
  honesty fixes · **B-2** copy approvals in batches, with removal-only corrections and "not yet performed / not operating"
  notices allowed without per-text confirmation · **B-3** re-key personal handles (old→new map restricted) · **B-4**
  record integrity (supersede `p-17b713`; GATE-G3 superseded; ACCEPT-R8/R10 annotated) · **B-5** verdict vocabulary ·
  **B-8** intake email-only until after announcement, published response times (72 h safety takedowns; 7/30 days other) ·
  **B-9** release model incl. Class R/S standing-go text · **B-11** Cloud SQL cap 40 GB, pre-grow 25 GB, one ING-GO per
  wave, scope = core + droppable Wave D · **B-15** GitHub settings · **B-16** keep the planning branch local until T6 ·
  **B-18** owed operator actions · **B-19** transparency defaults · **B-26** dedup is an announce criterion · **B-30**
  search memory (+$3/mo) · **B-31** maintainer checks per Class-S release · **B-34** non-US database-right lines not
  flipped · **B-41…B-43** E4 rights rows and status corrections.
- **Part C — 11 confirmations** (C-1 readout provenance; C-2 harness history; C-3 the operator's own words for counsel,
  the human-review deferral and robots; C-4 positioning text; C-5 who runs SIG on About; C-6 repo stays public; **C-7 the
  real monthly bill**; C-8 alias first; C-9 no intake secret value used; C-10 local DBs with L44–52; C-11 interpretations).
- **D2 — 16 reactions** (agree/disagree + priority) to the most consequential findings (S1c §5). D2 is folded into S5.

### 4.4 Defaults that stall or descope (S2 §7.3) — shown beside the criterion each disables

Every success criterion in §13.2 is stated **conditionally on the recommended answers**. If a line below is left at its
default, the criterion is reported as **"not attempted (default <line>)"** in P38.2's accepted-deviations list, never as
MET.

| # | default | kind | criterion it disables (§13.2) | rows affected |
|---|---|---|---|---|
| — | **A-18/B-24** → "no" | **stall** | correctness: no mixed-scheme dossiers; `unresolved` not a dossier; every state + DC has a dossier; first model release | P35.17, P35.19, P35.45, P35.63 and everything after |
| 1 | **B-11 / Q-23** → 25 GB cap, Wave C waits | descope | coverage: the national ALPR layer from its origin (D3 §3(b)) | P37.2 queued |
| 2 | **A-7** → nothing flips | descope | coverage: 154 Tier-1/widening candidates live or dispositioned; 40/51 states + DC; 28/29 technology classes | P36.4–P36.12 (9 rows) |
| 3 | **A-12** → three islands only | descope | U-003.2/.3/.6 only partly met; K0 budgets criterion changes | P36.20, P36.21, P36.40, P36.57, P37.26, P37.27, P37.29, P37.61 (8) |
| 4 | **A-10** → organisations withheld | descope | J2 journey; Organizations hub; organisation labels/edges | P35.29–30, P36.41–42, P37.22–28 (11) |
| 5 | **A-3** → no DNS move | descope + cost | U-003.9/.10 downloads; J1 "rows in ≤ 3 clicks"; basemap on GCS (+$4–41/mo) | P35.5, P36.33, P36.50, P36.53, P36.68, P37.36 (6) |
| 6 | **B-30 (D-K3-5)** → no | descope | U-003.3 search v2 API stays staged | P36.38, P36.71 |
| 7 | **B-19 / D-J3-6** → no snapshots | descope | J4 "cite it durably" | P36.66 |
| 8 | **B-19 / D-J3-11** → no status lane | descope | ingestion heartbeat on `/status/` | P36.43 built, not scheduled |
| 9 | **B-19 / D-J3-1** → no raw bytes | descope | raw downloads (U-003.9 "download the raw data") | P37.36 built, not exposed |
| — | **A-13** → records-only seed | risk | seed CI green; numbering | SEED-02/03 become P34.0a/b |
| — | **D-G3-3 (B-9)** → no standing go | load | more signatures; P36.70 cannot rehearse Class R | every release Class S |

### 4.5 New S5 lines this draft adds (from S2 §11)

- **S5-1:** ratify **OM-19** and **OM-20** as written in §3.3.
- **S5-2:** ratify the **check-in GATE packet** (S2 §3.6: budget · publication · rights · OM-20 list · status-for-
  information; answers `continue` / `continue with <lines>` / `pause`).
- **S5-3:** the **GATE-B pre-authorisation list for 11A** (OM-20): P34.3–P34.6 (QA actions, budget, drill clone),
  P34.21's attribution backfill leg, P34.24 (clone rehearsal), P34.40 (LB/nginx, dark), P34.42–P34.45 (IAM, execution
  host and logins, nightly quality job, ER re-run). Republishes P34.17/P34.21 and the schema change P34.46 stay in-ticket gos.
- **S5-4:** confirm **CF-06** (US-first: ACQ-23a/b leave the round; Wave C US + territories) and **CF-15** (RI-01 rides
  republish #2 ≈ 5–7 days after republish #1) — each reversible via A-17 or B-3 "RI-01 first".

---

## 5. Themes (problem → evidence → design → requirements → rows → acceptance)

Runs per theme are chain-row totals from `data/round11_plan.csv` mapped to S1a's `theme` column (238.5 in all: UX core
56.5 · sources 27.5 · transparency 26.5 · data correctness 23.5 · release/ops 22.0 · Round-10 activation 19.0 · safety
and honesty 18.0 · UX explore 17.5 · memory truth 10.0 · acceptance/tail rows 6.0 · debt 5.5 · governance 4.5 · CI 2.0).
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
  → **republish #1** P34.17 (honest dispute notice naming the operator's address and single-maintainer response times;
  `/editorial-standards/` "not yet performed"; "human-verified" removed); handle re-key with append-only aliases P34.18
  and forbidden-terms withdrawal P34.19 + evidence empty-state truth P34.20 → **attribution re-export + publish-time
  attribution gate + republish #2** P34.21 (first slot after the AR-3 window closes 2026-10-13T12:00Z). API honesty code
  P34.25 ("scope not available" until P35.57 serves real scope). Operations: P34.3 data protection (QA-1/2/6/7, bucket
  versioning, `sig-web` non-public), P34.4 alerts that reach a human (verifies Track 0.5; QA-5 probe re-roll; QA-8), P34.5
  budget alert at $300 + billing export + visible spend ledger, P34.6 restore drill at scale. Later safety rows: P35.3
  production-truth probes + fixture-sentinel scan; P35.28 officer-naming gate (default deny); P35.38 identity base and
  crawler contact truth; P36.15 redaction pipeline (before the evidence hub and raw archive).
- **Requirements.** SIG-OPS-001…004 (restore drill, survivability, route allow-list, single publish path), SIG-OPS-006
  (alert delivery), SIG-OPS-009 (cost truth), DRAFT-OPS-2 (fixture sentinels), the G2 §6 claim rules; amendments to
  SIG-PUB-008 (note; H-9 default-deny) and SIG-UI-042 (stays owed). See §6.
- **Acceptance (11A exit, live layer, P34.47).** All 9 S0 closed live (restore drilled with timing and deletion
  protection on; publish path refuses `/curate/` and an absence probe confirms; honest dispute notice; fixture pages
  corrected; no personal handle in any public id; API honest; attribution correct in downloads, API and map behind a
  publish-time gate). A test alert has been received; the $300 budget alert and billing export are live. A live probe finds
  0 instances of "human-verified", "counsel", "editorial board", "one-click" or "anonymous" outside disclosed contexts.

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
    deleted GATE DECISIONS rows first** (SEED-06); date corrections in LEDGER/BUILD_INDEX (SEED-07) and elsewhere
    (SEED-08, **without** footers on landed ADRs — CF-02); BUILD_INDEX index repairs (SEED-09); archive the LEDGER head
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
  evaluation **not planned** — owed under T-EVAL-IND (§11). Honest evaluation posture ships in 11A (P34.45). Public
  disclosure: `/quality/` from a release-bound `quality.json` (P37.45); per-record basis block (QB-01, P37.39); mechanical
  evaluation report (P37.44); re-measure L2 on the final release (P37.67).
- **Not claimable anywhere** (L3 §4.5): "human-verified", "independently reviewed", "certified"; any cross-source
  camera-match precision figure; 0.98 certification; completeness; model agreement as accuracy.
- **Requirements.** SIG-CONF-001…014 (drafts D01–D14: basis classes, segregated agent labels, only mechanical checks gate,
  derivation not identity, no auto-written inference, check registry, ratchet discipline, real-data corpus, upstream
  reconciliation, maintainer checks, `/quality/`, mechanical estimands labelled, least-privilege audit path, declared
  lineage); amendments to SIG-EVAL-004 (waiver note), SIG-IDENT-028, §55.9; owner notes on EVAL-005/006/007.
- **Acceptance.** At P35.63 (first model release), at `enforce` (L2 baseline in brackets): 0 subject-key collisions
  [5,278]; 0 1970 edges and every edge dated or "undated" [98.8 % undated]; 0 publisher-as-operator [74.2 %]; technology on
  100 % of site rows [77.4 % mistyped]; 0 axis swaps / 0 null-island points [562/14]; 0 undisclosed out-of-polygon points
  [2,370 > 25 km]; `unresolved` is not a dossier; 0 mixed-scheme dossiers; exact claim repeats ≤ 1 %; derivation census
  100 %; dossier counts ≤ 1.02× lineage roots (or ranged intervals if A-6 defaults) [up to 2.25×]; contradiction recall 1.0
  on the synthetic set; byte binding 100 % for sources re-run in P35.61 [0/2.78 M]. Round: CONF-14 (P37.67) re-measures L2
  on the final release; every L3 target met or each miss names its fixing row; M-1b lower bound ≥ 0.98 per declared
  namespace; `/quality/` live with every check.

### 5.5 Sources and coverage — Stream I (33 rows, 27.5 runs; US-nationwide Flock/Axon focus)

- **Problem.** Material blind spots: Flock only via one mirror (≈ 23 % of networks), Axon/Fusus/RTCC nothing, 22 states
  without a dossier, ATE/drones/FRT/forensics thin, the national OSM ALPR layer only as a stale republished copy.
- **Evidence.** I1 (14 blind spots), I2 search protocol, I3–I6 + I9a/b (logged queries, saturation), I7 (694 consolidated
  candidates; Part VIII preflight; rights lanes), I8 (acquisition plan, `data/acquisition_plan.csv`); F-329, F-330, F-366,
  F-374, I8 NEW-1…8; U-007.
- **Design (I8, scoped by D3 and CF-06).**
  - *Rules:* availability is never rights clearance; every activation follows its HG-03 line and a verbatim **ING-GO per
    wave**; **Flock and Axon facts come only from agency pages, procurement records and statutory reports, never from
    vendor hosts** (A-17/D3-Q3; I7-C4); Part VIII-flagged candidates stay metadata-only unless screened (B-32); non-US
    database-right lines are not flipped this round (B-34); express "do not redistribute" terms are withdrawn (A-8).
  - *Enablers first (P35.6–7):* acquisition plumbing and harness with I8's preconditions — the reviewed ArcGIS rate applied,
    a second cadence batch round, new triggers created disabled, the 63 truncated source ids fixed, aggregation for ATE
    violations — then registry label fixes M1–M7. The scheduler of record and cron lint (P35.1) precede them (CF-09).
  - **Wave A** (widening, 43 of 46 units, ≈ 18k claims): Legistar keyword-filtered paged matter pass, USAspending/CROL
    vocabulary, the 2026 state ALPR statute seed (P35.8–10) → activation P35.11 (live 2026-10-19→10-23, 14:00–20:00Z).
  - **Wave B** (Tier 1, 108 candidates, ≈ 89 new registry rows, ≈ 250k claims): robots/opt-out register and rights-
    reservation state before any new host is fetched (P36.1); owed rights flips (P36.2); ATE concept (P36.3); eight family
    tickets (P36.4–11: DOT/CCTV layers, agency ALPR/Flock layers incl. the FDOT inventory and removal ledger, ATE, registers,
    statutory disclosures I/II, CCOPS/policies, grants/council/procurement/bills) → activation with the second release
    P36.12 (2026-10-26→11-05, one family a day).
  - **Wave C:** OSM becomes the **origin** of the national ALPR layer (code P37.1, because widening `osm_overpass` alone
    cannot do it; live P37.2, 2026-11-16→11-20, US and territories only, with a pre-grown disk and a temporary tier bump).
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
  dossier; Flock, Axon and Motorola/Vigilant exist as entities with dated, sourced agency links; all 154 Tier-1 and
  widening candidates are live or dispositioned; 40 of 51 states + DC and 28 of 29 technology classes verified live;
  11–12 of the 14 I1 blind spots moved. **Stays dark by design or terms** (I8 §9): Flock's own customer, sharing and audit
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
- **Every U-003 ask traced** (rows from `data/round11_plan.csv`; live checks from K13 §5.1, run at P36.72 / P37.63–64 /
  P37.68):

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
- **Acceptance.** P36.72 (ACC-PLACES, HG-11): every U-003 ask above has a working page passing its K-row acceptance;
  journeys A1–A4, J1, O1, O3, O4 pass the agent walkthrough at 390 and 1440 px (`agent-verified`); search resolves 55
  jurisdictions, 20 cities and the top 25 vendor and agency names; K0 budgets and axe pass on real data. P37.63–64 (map;
  entity/graph/figures). P37.68 CAP-01: all 13 journeys pass both walkthroughs (agent and operator). Clarity (D3 §3(c)):
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
  HG-11); cadence monthly on the 15th at 14:00Z, early at ≥ 10 % net and ≥ 14 days, alert at 35 days; automatic rollback;
  15-minute withdrawal on every alias with tombstones; a pipeline signing key for manifests (B-20); semver tags on `main`
  by the operator only. Rows: REL-10 versioning (P34.23); REL-01 identity v2 + clock guards (P35.12); REL-02 provenance
  stamp and `release.json` (P35.13); REL-03a/b pipeline, private bucket, templated nginx, config generations
  (P35.53–54); REL-08 rollback/withdrawal/purge (P35.55); REL-04a/b verification suites + auto-rollback (P35.56, P35.58);
  REL-05 API release parity (P35.57); REL-09 dark cutover (P35.59); REL-06 classifier, standing go, readout generator
  (P35.60); REL-07 cadence automation (P36.44); REL-11 second-release acceptance (P36.70). **Ops (G1):** P34.39 first-fire
  wave + 10-10 replay read-backs; P34.42 least-privilege identities; P35.1 scheduler of record + live-diff + cron lint;
  P35.2 alerting as code; P35.4 runbook; P36.13 API rate limits + optional Cloud Armor; P37.3 evidence-store hardening +
  off-instance copies; P37.4 security baseline. Detail in §10.
- **Requirements.** SIG-REL-001…014 (G3 §10 D01–D14); SIG-OPS-001…012, SIG-SEC-007…009, SIG-STORE-048 (G1 §4 + B4
  DRAFT-OPS-1/2).
- **Acceptance.** P35.63 promoted under a signed HG-11 readout with V1–V15 green and 0 waivers, live rollback rehearsal
  done, nginx honours withdrawals; P36.70 measures rollback and withdrawal timings on the second release; every page shows
  release label, as-of, commit and build time.

### 5.9 Round-10 activation (16 rows, 19.0 runs; G2)

- **Problem.** No Round-10 surface is deployed; the GATE-G3-signed candidate is a 0-record fixture with a future date;
  seven Round-10 return passes were prepared, not executed.
- **Evidence.** F-14, F-15, F-16, F-051, F-152…F-161; G2 §0; D-R10-LIVE-1, D-P32.23a-1, D-R10-PUBLISH-1, D-P32.18…21-1,
  D-P32.16-1, D-R10-SOURCES-1.
- **Design (G2 steps 0–8 → rows).** Step 0 = §5.1 + sqitch hygiene with a round-trip CI and an **L44–52 clone rehearsal**
  (P34.24). Step 1: ADR-124 allow tooling and the flagged-organisation census (P34.26) → **Round-10 schema (sqitch L44–52)
  + ADR-124 allows + Round-10 API roll** (P34.46; ≥ 2026-10-14T14:00Z after the 10-10 read-back P34.39; 48 h soak;
  in-ticket go; operator available in the slot). Step 2: execution host + least-privilege logins (P34.43) → D-R10-LIVE-1
  hosted audit → bounded apply with recorded `--authority` scope → freeze (P35.61, row 183's pass). Step 3: production
  candidate with true dates (P35.62, row 188's pass). Step 4 (engineering from day 1): release-archive correctness and
  export-mode build (P34.34), research-dossier disclosure (P34.35), release-search states (P34.36), intake defects
  (P34.37), serving topology dark (P34.40), withdrawal-barrier bytes (P34.41). Step 5: D-R10-SOURCES-1 prep (P34.38) →
  dossier live captures under HG-03 (P37.16, rows 179–182). Step 6: intake operation stays **dark** and conditional
  (P37.59; B-8 email-only). Step 7: **first model release** D-R10-PUBLISH-1 (P35.63, row 191's pass) — the old GATE-G3
  signature is superseded, **not transferred**. Step 8: D-R10-MEMORY-1 split (P34.30).
- **Acceptance.** 11A exit 5: G2 step 1 live, after the 10-10 replay was read back. 11B exit 1: P35.63 promoted (§5.8).
  Research dossiers become public only after live captures (B-7).

### 5.10 Governance and records (5 rows, 4.5 runs; plus seed ADRs and records)

- **Problem.** Spec MUSTs contradict operator decisions; public and repo text implies an editorial board, counsel and
  independent review that do not exist; consequential records rest on tentative words.
- **Evidence.** F-31, F-185, F-189, F-190, F-191, F-195, F-199, F-471; E1 (contradictions), E2 (22 memos + A-1), E3
  (human-work options), E4 (22 rights decisions); U-011, U-013; B5 §4.
- **Design.** The A-4 posture package (disclosed single maintainer, no counsel) by ADRs (§7); repo honesty corrections
  (governance doc, `sources.toml` "counsel" reviewer values → operator determinations) (P34.16); robots/opt-out register
  and crawler policy text (P36.1); registry rights-record hygiene (P37.6); a **public editorial decision log** under interim
  single-maintainer authority (P37.7); legal-demand posture + published counts, warrant canary declined (P37.8; SIG-SEC-003).
  Records (seed): the C-3 confirmations in the operator's own words; ACCEPT-R8/R10 annotated "approved on an agent
  summary; full text composed after" (B-4); the go-live spec reconciled following the ADR-145 pattern (GL-GATE-06…08 enter
  the go-live spec, E2-18).
- **Requirements.** Amendments: SIG-PUB-008 (stands; nobody named), SIG-GOV-012/013/015 (interim text), SIG-SEC-003,
  SIG-LIC-004/009 + HG-03, SIG-INGEST-037/§26, SIG-CONTRIB-012/013/030a (timing → later-phase), SIG-CHART-025.
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
SIG-REL-D11 merges with SIG-OPS-008's triggers) and decides whether the K-row families become new prefixes or fold into
SIG-UI.

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
| SIG-PUB-008 | stands; note: nobody is named; web gate default-deny | A-4 (Q-E2-06); E2 H-9 |
| SIG-GOV-012/013/015 | interim individual legal home; interim single-maintainer editorial authority + public decision log | A-4 |
| SIG-SEC-003 | demand-response posture + published counts; canary declined | A-4 |
| SIG-LIC-004/009 + HG-03 text | operator-accepted rights basis with guardrails | A-4 (Q-E2-13); A-7…A-9 |
| SIG-INGEST-037, §26 rule 7, SIG-INGEST-046c | robots narrowed; opt-out register; reservation refusal | A-5 |
| SIG-CONTRIB-012/012a/013/030a, SIG-GOV-024, SIG-CHART-033 | outreach timing: owed later-phase obligation, trigger "operator authorises outside contact" | Q-E2-12 a; U-011 |
| SIG-CHART-025 | US-nationwide multi-vendor/multi-technology breadth with per-class and per-geography quality labels | A-17 |
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

### 6.5 Waivers — and what is deliberately *not* waived

- **Exactly one requirement waiver is proposed:** SIG-EVAL-004's lower-bound clause, **scoped to derivation-collapse
  tiers C0–C2**, by ADR, **in the operator's own words** (A-6; e.g. *"I accept derivation, not identity, and waive
  SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes."* — agent-drafted example). D-R6.1-EVAL drops
  EVAL-004 from its legs; one new BL row carries the revisit trigger.
- **One risk row closes by ADR:** RISK-P0-06 via the collection-conduct ADR restating SIG-INGEST-037's legal posture
  (S1b's single `adr-waiver` item).
- **Not waived; stay owed with a trigger:** SIG-EVAL-001/002/005/007 and SIG-IDENT-027/028's independent legs, SIG-UI-042
  and SIG-DOS-002's independent checks (T-EVAL-IND); SIG-UI-001 usability (LATER-02); SIG-CONTRIB-012/012a/013,
  SIG-GOV-024, SIG-CHART-033 (LATER-04; F2b had proposed WAIVED — see Appendix B); a counsel opinion (LATER-05; a new OPEN
  row). SIG-PUB-008 **stands**. D-R10-HUMAN-1 is never waived.

### 6.6 Coverage re-verdicts T4 applies (summary)

- **F2b (55 gated/reduced-scope ids):** 12 MET → MET-ENGINEERED (TRUST-004/007/008/009/010, FIND-006/007, DOS-002…005,
  ACQ-004); EVAL-003/004 and PUB-008 → AT-RISK-INTEGRATION (then superseded by L3: EVAL-003 → MET, EVAL-004 → WAIVED
  scoped); GOV-022, EVID-019 → MET-ENGINEERED; GOV-013/015 → MISSING; the outreach five → owed later-phase (not WAIVED).
  The 14 MET-ENGINEERED verdicts need their D-rows opened first.
- **F2a (49 engineering/"claimed" ids):** UI-010, EPIS-018, INGEST-046b, ONTO-054, INGEST-007, STORE-013, ENG-034 → MET;
  UI-040 → MET-DIFFERENTLY(ADR-108; ADR-133); GEO-007, ENG-004 → N/A-RATIONALE; 30+ PARTIAL with a concrete test/build home.
- **L3:** EVAL-001 → MET-ENGINEERED; EVAL-003, EVAL-006 → MET (after CONF-09/12); EVAL-002 PARTIAL; EVAL-005/007 MISSING
  (owed); IDENT-030 MET by abstention; EPIS-029 and RECON-018 → MET when GQ-11/12 pass live.
- **61 unsampled boilerplate MET-DIFFERENTLY rows** are re-verdicted row by row in SEED-14 (their true state is unknown
  until then; F-238).

---

## 7. ADR list (from ADR-146; numbers provisional — T1 assigns them in ratification order; each carries `## Revisit trigger`)

Landed ADR bodies are never edited (CF-02; SIG-ENG-003). A superseded ADR gets only an appended `Superseded by` status
line. ADRs marked † exist only if the Part-A line is answered as recommended.

| # (prov.) | title | one-line decision | S5 line | source |
|---|---|---|---|---|
| 146 | Correcting recorded dates that were not taken from a clock | truth source = `date -u`; corrections are append-only via one register and this ADR (no footers on landed ADRs); sqitch lines never edited; candidate `p-17b713` superseded, not re-signed; a CI guard rejects new future-dated records | A-13, B-4 | B1 §8 (amended by CF-02) |
| 147 | Gate-record integrity and readout authorship | verbatim operator words; agent-drafted text labelled and sha256-confirmed; no proxy signatures; hedged words are not decisions; the 53 deleted GATE DECISIONS rows restored; GATE-G3 superseded (not transferred); ACCEPT-R8/R10 annotated | A-16, B-4, C-1, C-3 | E2-17/18/X1; B2; B5 OM-07…09 |
| 148 | Build memory v2.1: ledger contract and enforced append-only | ≤ 12 KiB head, value-only CURRENT STATE with `harness:`; guard core in CI; D-R10-MEMORY-1 split (option C) superseding ADR-126/127's cutover statements; closeout journal stays shadow | A-13 | B3, B4 |
| 149 | Round-11 operating model | one harness (Claude Code) for the round; CI at every boundary; layered status; OM-19 live-leg queue; OM-20 bounded pre-authorisation; four gated sub-rounds with check-in GATEs | A-15, S5-1/2 | B5 §6; S2 §3 |
| 150 | Coverage verdict vocabulary | adds MET-ENGINEERED and WAIVED(ADR), four columns, checker cross-checks | B-5 | F2b §2 |
| 151 | Toolchain pin and CI truth | Node 24 LTS, uv pin, `ubuntu-24.04`; head-bound check-runs; flake allow-list (one re-run); CI-unavailable needs a verbatim waiver; tests assert invariants (pin rewrite) | B-15 | H2; CF-01 |
| 152 | Confidence without independent review | confidence by construction + mechanical suite; basis classes; agent and maintainer evidence never gates; independent evaluation not planned, owed under T-EVAL-IND; rows 184–187 superseded | A-6 | ADR-L3-A |
| 153 | Derivation, not identity | ruleset v3: auto-collapse only C0–C2 copies, census-verified; inferential matches published as possible duplicates with intervals; **SIG-EVAL-004 WAIVED for C0–C2 (operator's words)**; supersedes ADR-105 §5, amends ADR-099 §3 | A-6 | ADR-L3-B |
| 154 | Graph-quality suite as a ratcheted release gate | 27 checks, enforce/ratchet/report; V15; ratchet regression ⇒ Class S; loosening a baseline needs a new ADR | A-6 | ADR-L3-C |
| 155† | HTML-first page types | T0/T1/T2/T3 registry with CI budgets; records and print script-free; three app-like explore surfaces with URL state and no-JS equivalents; Preact not React; supersedes ADR-091 §3–4 and ADR-097 §2–3/§6, extends ADR-134; ADR-068 unchanged | A-12 | K0 §6 |
| 156 | Public map v2 | self-hosted OSM basemap (reverses Round-9 Q8; supersedes ADR-118 §2); count-conserving per-compartment overlay tiles; Natural Earth place names | (answered) + B-23 | K1 MAP-00 |
| 157 | Static figure kit and dossier visualisations | one server-side figure kit; inline SVG styled by page classes; downloadable SVGs under their own no-script policy | B-22 | K6 VIZ-00; K13 C-07/08 |
| 158 | Graph exploration as aggregated overviews | overview graphs ≤ 3,000 nodes + entity egos + `/explore/`; descriptive only; no network analytics before the ER gates (SIG-IDENT-030) | A-11 | K0, K2, K13 D-K13-1 |
| 159† | Organisation publication | registry-matched organisations (Census of Governments, SAM UEI, Wikidata QID) auto-allowed; operator degree-ordered review; person-name screen always runs; extends ADR-124 | A-10 | K2 D-K2-1 |
| 160 | Structured jurisdiction scheme and placement | ISO 3166-2-keyed registry, boundary pack, `lookup@1`/`placement@1`; `unresolved` is a report, not a dossier; revisits ADR-079/122 | A-18 | K4; F5 PKG-06 |
| 161 | Release model v2 | content-addressed identity + `sig-YYYY-MM-DD.N`; descriptor v2 (extends ADR-132, merges J3 fields); private staging; metadata-only promotion; Class R/S with a revocable standing go; cadence; 15-min withdrawal; pipeline signing key; operator-only tags | B-9, B-10, B-20 | G3 |
| 162† | Transparency and distribution | export-time static artifacts; source-keyed rights lanes; fail-closed scrub; status lane as its own publish class; zero-egress R2 host with $50 ceiling and kill switch; raw bytes for raw-ok sources only; per-release site snapshots `/s/<pub>/`; JSON-LD as linked files | A-3, B-19 | J3; J4 |
| 163† | Single-maintainer publication posture | SIG-PUB-008 stands; no individual is named; publication gate default-deny | A-4 | E2-01 |
| 164† | Interim editorial authority and public decision log | single maintainer as interim authority, disclosed; public decision log | A-4 | E2-03 |
| 165† | Interim legal home | individual, disclosed, interim; revisit on announcement, first legal demand, funding or a second maintainer | A-4 | E2-04 |
| 166† | Legal-demand posture | written posture + published counts; warrant canary declined | A-4 | E2-10 |
| 167† | Counsel basis | past "counsel" determinations re-recorded as the operator's; publication rests on the operator's recorded risk acceptance, labelled; qualifies ADR-086/106 | A-4, C-3 | E2-05; U-013 |
| 168 | Collection conduct | robots narrowed per A-5; SIG-INGEST-037 amended; opt-out register; reservation refusal; `robots_policy` field semantics superseding ADR-088's clause; UA/contact moved to surveillancegraph.org (T1 may split into two) | A-5, B-6 | E2-06/07/08 |
| 169† | Rights basis with guardrails | GL-GATE-07 recognised for Tier-1 families; express prohibitions withdrawn; NC sources facts-only; non-US database-right lines not flipped; vendor hosts never fetched; tribal data deferred | A-4, A-7…A-9, B-32…B-39 | E2-11; I7 |
| 170† | ODbL map basis | ADR-106's clearance recorded as operator-reported, without a document; per-compartment map kept | A-4 | E2-13 |
| 171 | Outreach timing | Stage-0 outreach, records-request sending, recruiting and contribution-back become owed later-phase obligations, trigger "operator authorises outside contact" | B-6 (Q-E2-12) | E2-09; U-011 |
| 172 | Product direction and scope | D3 order; US-nationwide multi-vendor breadth with quality labels (CHART-025); co-primary journeys, advocate wins conflicts; D3 §5 announce gate | A-17 | D3; E2-20 |
| 173 | Acquisition waves and capacity | one ING-GO per wave; US-first (CF-06); autoresize cap 40 GB, pre-grow, temporary tier bumps; permanent scale-up only on a named trigger | B-11, S5-4 | I8 §7 |
| 174 | Scheduler of record | Cloud Scheduler + daily live-diff + cron lint; GitHub `reingest` retired; supersedes ADR-076's scheduling path | — (engineering) | G1-09 |
| 175 | Production data protection and restore drills | deletion protection, retain-on-delete, quarterly drill at scale, monthly logical export; qualifies ADR-081 | A-1 | G1-03/04 |
| 176 | Observability and API exposure | alerts as code to a human channel with re-notify; uptime + TLS; enforced rate limits; optional Cloud Armor | B-30 | G1-02; OPS-06 |

**Also at T1 (records, not new decisions):** appended `Superseded by` status lines on ADR-015, ADR-058 §3, ADR-075,
ADR-092, ADR-096 §1 and every ADR superseded above; recorded evaluations of the fired revisit triggers (F3 §5.1);
`ADR_TRIGGERS.csv` with one row per revisit trigger (SEED-15). A Part-A "no" that leaves a landed rule unchanged needs no
ADR; one that changes a landed rule gets its own ADR.

---

## 8. Ticket plan (`data/round11_plan.csv` is authoritative; 333 rows: 262 chain rows, 4 markers, 20 seed, 23 operator, 24 later)

### 8.1 Shape and counts

| sub-round | rows | kinds | runs | production-touching rows (OM-20 lists) | in-ticket pauses |
|---|---|---|---:|---:|---|
| 11A P34 | 201–248 (48) | 46 tickets, acceptance P34.47, GATE-G4 | 44.0 | 20 | P34.17, P34.21, P34.46 |
| 11B P35 | 249–313 (65) | 63 tickets, acceptance P35.64, GATE-G5 | 62.5 | 25 | P35.11, P35.61, P35.63 |
| 11C P36 | 314–387 (74) | 72 tickets, acceptance P36.73, GATE-G6 | 65.0 | 13 | P36.12, P36.70, P36.72 |
| 11D P37 | 388–455 (68) | 67 tickets incl. 10 conditional (9.5 runs), CAP-01 P37.68 | 62.0 | 26 | P37.2, P37.65 (ING-GO-D collected at G6) |
| tail P38 | 456–462 (7) | CAP.1, CAP.3, GATE-ACCEPT-R11, REC, DOC, CAP-02, GATE-ANNOUNCE | 5.0 | — | the two gates |
| **total** | **262** | ticket 248 · capstone 7 · gate 5 · reconcile 1 · docs 1 · **HUMAN 0** | **238.5** | **84** | **11** + 5 gate markers |

Each sub-round is ≤ 65 runs and ≤ 74 rows (1.2–1.9× Round 10's 40 rows). **Re-split rule:** a phase that exceeds 75 runs
or 85 rows after T3's splits becomes two phases with an extra GATE (S2 §3.2).

### 8.2 Contents in order (rows; details in §5)

- **11A:** CI first (P34.1–2) → production safety (P34.3–6) → memory guards M1/M3/M2 (P34.7–9) → publish path (P34.10)
  → W0 copy (P34.11–15) → repo honesty (P34.16) → **republish #1** (P34.17) → re-key, withdrawal, evidence empty states
  (P34.18–20) → **attribution re-export + republish #2** (P34.21) → date truth, versioning (P34.22–23) → sqitch hygiene +
  clone rehearsal (P34.24) → API honesty (P34.25) → allow tooling (P34.26) → memory M4–M10 (P34.27–33) → C4 blockers
  (P34.34–38) → replay read-back (P34.39) → serving topology dark (P34.40–41) → identities, execution host, `sig_audit`
  (P34.42–43) → quality baseline in ratchet mode (P34.44) → honest evaluation posture (P34.45) → **Round-10 schema +
  allows + API** (P34.46) → P34.47 → GATE-G4.
- **11B:** ops truth (P35.1–4) → zero-egress host (P35.5) → Wave A (P35.6–11) → release identity (P35.12–13) → typing and
  geometry (P35.14–16) → placement (P35.17–19) → numbers (P35.20) → partner-name audit (P35.21) → identity core
  (P35.22–27) → officer-naming gate (P35.28) → labels and `/network/` (P35.29–30) → transparency exports (P35.31–42) →
  watch producer, dossier contributions, dossiers at every level (P35.43–45) → **dedup** (P35.46–47) → agent review lane +
  OPCHECK (P35.48–49) → page registry, budgets, tile fix (P35.50–52) → release pipeline (P35.53–60) → G2 steps 2–3
  (P35.61–62) → **first model release** (P35.63) → P35.64 → GATE-G5.
- **11C:** robots/opt-out (P36.1) → owed flips (P36.2) → Wave B (P36.3–12, second release) → rate limits (P36.13) → L4
  marker, redaction (P36.14–15) → design system + IA kit + figure kit + identifiers (P36.16–30) → search v2, basemap,
  grouped index, map, entity pages A + Organizations (P36.31–42) → status lane, cadence (P36.43–44) → Sources & data
  (P36.45–51) → dossier sources explorer, downloads, template v2 (P36.52–57) → watch, evidence, research queue (P36.58–63)
  → Home/About/onboarding (P36.64–65) → snapshots and changes (P36.66–67) → per-source versions (P36.68–69) → second-
  release acceptance (P36.70) → search activation (P36.71) → **core-surfaces release ACC-PLACES** (P36.72) → P36.73 →
  GATE-G6.
- **11D:** Wave C (P37.1–2) → evidence store, security baseline, ingestion hardening (P37.3–5) → governance pages and
  rights hygiene (P37.6–8) → lifecycle, promotion gate (P37.9–10) → source-ops tail (P37.11–15) → dossier live captures
  (P37.16) → map work (P37.17–20) → access, entity pages B, overviews, explorer (P37.21–27) → dossier networks, in-place
  map (P37.28–29) → watch predicates, lane, feeds (P37.30–34) → queue campaigns (P37.35) → raw archive, claim viewer v2
  (P37.36–37) → disagreements, quality basis, changes, API parity, search export (P37.38–43) → mechanical evaluation,
  `/quality/`, organisation identity (P37.44–46) → Wave D conditional (P37.47–54) → deposits, WACZ (P37.55–56) →
  projection rebuild, schema conformance (P37.57–58) → intake dark/conditional (P37.59) → visual regression, T1
  enhancements, contribution path (P37.60–62) → map and explore acceptance (P37.63–64) → **final release TX-16**
  (P37.65) → coverage closeout, Stream-L re-measure, **CAP-01 journeys** (P37.66–68).
- **Tail:** §13.

### 8.3 Gates, pauses and operator touchpoints

- **Five gate markers:** GATE-G4 (row 248), GATE-G5 (313), GATE-G6 (387), GATE-ACCEPT-R11 (458), GATE-ANNOUNCE (462).
  HUMAN-H6…H8 stay reserved for the T-EVAL-IND segment. Each check-in GATE follows its acceptance row so the evidence is on
  screen; the packet is S2 §3.6 (S5-2).
- **Eleven in-ticket pauses** (§8.1). Batching gives about five sittings: G4 + ING-GO-A · P35.63 + G5 + ING-GO-B ·
  P36.72 + G6 + ING-GO-C/D · P37.65 + CAP-01 walkthrough + GATE-ACCEPT-R11 · GATE-ANNOUNCE.
- **HG-03 / ING-GO lines** per wave are collected in the preceding packet; an unanswered rights line never flips a
  source (rows land with `ingestion_permitted=false`; activation skips them).

### 8.4 Live stages and calendar windows (S2 §5.1; UTC; `date -u` at S2 = 2026-10-01T01:00Z)

| window | event | constraint on the plan |
|---|---|---|
| 10-01 → 10-21 | 33 first fires of existing triggers | watched; P34.39 reads them back through the queue |
| **10-06 00:00Z → 10-13 12:00Z** | AR-3 batch window; **10-10 03:35Z** OSM replay | no hosted DB write, schema change or job roll; republishes allowed outside 03:00–10:00Z |
| ≥ 10-10 after the replay | D-P31.4-1 read-back (P34.39) | prerequisite of P34.46 |
| **≥ 10-14 14:00Z** | earliest Round-10 schema deploy (P34.46) + 48 h soak | gates P35.11 and P35.61 |
| **before 10-19 00:00Z** | `ubuntu-latest` → Ubuntu 26 | P34.1 (row 201) must have landed |
| **10-19 → 10-23**, 14:00–20:00Z | Wave A (P35.11) | ING-GO-A |
| **10-26 → 11-05**, one family/day | Wave B (P36.12) | ING-GO-B; Class S |
| **11-06 → 11-13 12:00Z** | AR-3 | no release cut; P36.72 ≥ 11-13 12:00Z |
| 11-15 14:00Z | monthly cut slot | REL-07 automates after P36.44 |
| **11-16 → 11-20** | Wave C (P37.2) | ING-GO-C, Q-23, tier-bump go |
| **11-23 → 12-04, 12-14 → 12-18** | Wave D (conditional, P37.54) | second-window sources ship in the 2027-01-15 cut |
| **12-06 → 12-13 12:00Z** | AR-3 | P37.65 cut before 12-06 or after 12-13 12:00Z |

Tokens in `window_constraints`: **AR-2** on-demand backup + pre-state capture before any hosted write; **AR-3** none of
the three windows, never 03:00–06:30Z daily, preferred 14:00–20:00Z weekdays; **AR-4** clock-guarded read-backs; **PUB**
republishes outside 03:00–10:00Z. Engineering runs ahead of the windows; windowed legs wait in the OM-19 queue.

### 8.5 Sizing and T3 instructions

- Sizes S = 0.5 / M = 1 / L = 2 runs everywhere (CF-16). **T3 splits all 15 L rows a/b** (P34.21, .22, .24, .34, .42;
  P35.1, .14, .15, .20; P36.1; P37.4, .5, .16, .46, .57) → ≈ 277 rows, and checks adjacent S rows touching the same files
  for over-factoring. Row ids in this plan are **pre-split**; T3 renumbers (nothing has landed, so renumbering is free).
- **A-13 fallback:** if the seed is records-only, SEED-02/03 become P34.0a/P34.0b at rows 201–202 and everything shifts +2.
- Every live-stage contract gets a `Live window:` header and an OM-14 mutation list; live-result edges are marked `live:`.
- Full contracts for every row settled at GATE-P; `Kind: skeleton` only for the conditional rows (P37.12, P37.47–54, P37.59),
  filled after their gate lines.
- At each sub-round GATE, `decompose-spec mode=extend` re-checks the next phase's sizing (append-only Plan extensions).
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

- **Seed (20 units, 23.2 runs):** SEED-00…19 (Appendix A maps them to T1–T6). SEED-13 (T3, 4 runs) is split **T3a
  (P34–P35)** and **T3b (P36–P38)**.
- **Operator actions (23, OP-01…OP-23):** §11.
- **Later (24 units, 27.0 runs):** LATER-01…22 + R11-ACQ-23a/b, each with a trigger (§15).

### 8.8 Critical paths

- **Calendar (binding):** GATE-P → seed → GATE-B → P34.1 (≤ 10-19) → P34.39 (after 10-10) → **P34.46 (≥ 10-14)** → soak →
  P35.11 Wave A → 11B chains → **P35.63** → P36.12 Wave B → AR-3 → **P36.72 (≥ 11-13)** → P37.2 Wave C → **P37.65
  (outside 12-06→13)** → P37.68 → P38 → GATE-ANNOUNCE.
- **Runs:** S1a's longest seed→R11 chain is 21.2 runs; inside 11B three chains converge on P35.63 (JUR-01→02a→02b→
  DSRC-01→JUR-03; CONF-03a→03b→04→07a→07b; REL-01→…→REL-06).
- **Decision path:** A-18 (B-24) before P35.17, or the jurisdiction chain and P35.63 stall.
- **DAG check:** 317 catalog units, 749 hard edges, acyclic; 24 S2 sequence edges; 0 order violations (S1a §5; S2 §12).

---

## 9. Obligation mapping (S1b: `universe/UNIVERSE_DISPOSED.csv`, `tools/check_dispositions.py` → OK, 0 errors)

### 9.1 Totals

**1,159 items, exactly one disposition each:** 528 universe items (97 deferrals, 161 requirement rows, 36 backlog, 62 risk,
144 ADR triggers, 19 return passes, 2 readouts, 6 manifest rows, 1 ledger finding) + 538 findings (F-01…F-538) + 28
feedback items + 65 candidate groups covering all 694 consolidated candidates.

| disposition | count | | disposition | count |
|---|---:|---|---|---:|
| ticket | 739 | | merged-into | 24 |
| already-done | 146 | | wontfix | 14 |
| later-phase (trigger named) | 153 | | operator-action | 8 |
| decision (S1c id) | 41 | | spec-amendment (→ SEED-12) | 7 |
| live-return-pass | 26 | | adr-waiver (→ SEED-11) | 1 |
| human-marker | **0** | | | |

Ticket-like primary landings: first waves 542, other Round-11 units 224, operator units 7. 292 of 317 catalog units are
referenced; the 25 orphans are process/acceptance units each justified by its design row (S1b §7).

**Rule (c) switch (S2 §2.2):** S1b provisionally defined "first waves" from the catalog; T4 switches the check to read
`sub_round ∈ {11A, 11B}` from `data/round11_plan.csv`. Result at S2: the 76-unit S0/S1 owner closure (78 runs) is entirely
in 11A ∪ 11B; 19 non-owner K13 W1 units moved to 11C next to their consumers.

### 9.2 Every owed deferral (36 = 32 OPEN + 4 PARTIAL)

| disposition | deferral → landing |
|---|---|
| **ticket (10)** | D-FEDERAL.1-1 → P37.11 · D-P32.10a-1, D-P32.16a-1 → P34.24 · D-P32.16-1 → P37.59 (conditional; Q-27/B-8) · D-R10-MEMORY-1 → P34.30 (split, option C) · D-R10-SOURCES-1 → P34.38 (+ P37.16) · D-SOURCES.7-1, D-SOURCES.8-1 (PARTIAL), D-SOURCES.9-1, D-SOURCES.9-4 → P36.2 (rights flip/decline batch; E4 R3–R6 lines) |
| **live-return-pass (9)** | D-P21.5-1 (PARTIAL) → P37.55 + OP-19 · D-P31.4-1 → P34.39 · D-P32.18-1, D-P32.19-1, D-P32.20-1, D-P32.21-1 → P37.16 (HG-03, E4-B1) · D-P32.23a-1 → P35.62 · D-R10-LIVE-1 → P35.61 · D-R10-PUBLISH-1 → P35.63 |
| **later-phase (9)** | D-P21.7-1 → LATER-03 · D-P30.2b-2, D-R6.1-EVAL, D-R10-HUMAN-1 → LATER-01 (T-EVAL-IND) · D-R7.1-AUTH → LATER-06 · D-R7.2-SEND → LATER-04 · D-R10-USERS-1 → LATER-02 · D-SOURCES.8-2 → LATER-10 · D-SOURCES.9-3 → LATER-17 |
| **decision (6)** | D-JURIS.2-1 (PARTIAL) → E4-R1 (B-41: close, eID leg WONTFIX) · D-P30.2b-1 → B-18 (merged into the maintainer check, P35.49; else OP-16) · D-P32.3-1 → B-18 (folded into A-10 + P37.46; else OP-15) · D-SOURCES.2-2 → E4-R2a (B-41: decline) · D-SOURCES.7-2 → B-18 (register US 511 keys, OP-13 → P37.12) · D-SOURCES.9-2 → E4-S2 (B-43: WONTFIX) |
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

101 land on a seed or 11A/11B unit; 3 on an S5 decision (F-31 → A-4; F-191 → C-3; F-386 → A-3, with TX-11 at P35.5);
1 already done (F-366, I8's own correction); 8 L1/L2 correctness S1s (F-506, F-507, F-511, F-518…F-522) originally in L3
waves 2–3 are **pulled forward into 11B** (P35.24–27, P35.46–47, P35.61), with interim mitigations in 11A (P34.44
ratchet; P34.20 for F-522). None is later-phase or wontfix.

### 9.5 Every operator feedback item

| item | disposition → landing |
|---|---|
| U-001 | ticket → P36.64 (Home/About; landing text C-4) |
| U-002 | ticket → P37.68 (CAP-01: co-primary journeys) |
| U-003 | merged into U-003.G |
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
| U-015 | already-done → B7 (all 480 chain commits attributed by harness and model) |

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
| P34.39 | first-fire wave + 10-10 OSM replay read-backs (D-P31.4-1), clock-guarded | read-only; after the replay |
| P34.40–41 | serving topology (LB path rules for `/v1/*`, `/intake/*`; registry mount; nginx roll) dark; withdrawal-barrier bytes | production write (dark) |
| P34.42–43 | least-privilege runtime identities (remove project Editor); execution host for hosted return passes; read-only `sig_audit` login | production write |
| P35.1 | scheduler of record + daily live-diff + cron lint + fleet hygiene (79 triggers; cruft jobs) | production write |
| P35.2 | alerting as code; probe targets out of the image; escalation | production write |
| P35.3 | production-truth probes + fixture-sentinel scan (G10) | read-only probes |
| P35.4 | ops runbook (`docs/ops/RUNBOOK.md`) + stale ops doc fixes (README "≈$0/$9") | docs |
| P35.5 | zero-egress distribution host; $50/mo egress ceiling + kill switch | production write (R2 via Cloudflare if A-3 = a) |
| P36.13 | API exposure: enforced rate limits (search 30/min) + optional Cloud Armor (+$6) | production write |
| P36.43–44 | status lane (6-hourly `status/**` writer); release cadence automation | production write |
| P37.3 | evidence-store hardening + off-instance copies | production write |
| P37.4 | security baseline: scanning, SBOM, signing, audited restricted-byte access, audit logs (+≈ $5, log volume unmeasured) | production write |
| P37.15 | scheduled parser canary | production write |

All production writes follow OM-14 (contract-named mutation, scripted path, pre-state capture, restore point, rollback
command, run-ledger entry) and AR-2/AR-3. Under OM-20 they need no per-row go once their sub-round's list is approved.

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
- **Agent (build) spend** is outside the $300 infrastructure ceiling (A-2 a) and reported at every check-in: worker runs
  dispatched, re-runs and splits, harness and model, usage-limit events (the planning session hit one at ≈ 19:10Z on
  09-30), dollars where the operator's plan exposes them. Volume estimate: ≈ 300–330 fresh worker contexts for the round
  (≈ 262 rows + ≈ 15 splits + 15–25 live-leg re-runs + the seed). No new paid model service or second model family without
  an explicit go (B-31; LATER-18). "Not measured" is a valid line; no figure is invented.

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

### 11.2 Operator actions (OP-01…OP-23; `data/round11_plan.csv`)

| when | actions | est. time |
|---|---|---|
| S5 sitting | answer the packet (Part A 18, Part B 42, Part C 11, D2 16, S5-1…4) | ≈ 45–50 min |
| Stage B | OP-01 skills Tier A (after GATE-P, before T3/T5) · OP-18 verbatim confirmations for records (before SEED-08) · OP-05 GitHub stack ruleset + merge settings (before the T6 push) · OP-07 `SIG_GCP_PROJECT` variable, billing/usage alert (before row 201) · OP-23 optional private backup of the planning branch · GATE-B | ≈ 1.5 h |
| before row 201 | OP-02 skills Tier B-must (OP-03 Tier B-should if possible) | (agent time) |
| 11A | OP-04 skills Tier C · OP-12 cost approvals / billing admin (P34.5) · two republish gos + copy batches (B-2) · the P34.46 slot · GATE-G4 | ≈ 2–3 h |
| by GATE-G4 / 11B | OP-09 DNS move to Cloudflare (before P35.5's R2 leg and P36.33) · OP-11 register `sig-project.org` (before P35.38) · ING-GO-A · P35.61 go with `--authority` scope · **P35.63 HG-11 readout + OPCHECK** (OP-17) · OP-14 top-50 organisation review (after P34.26, before P36.41) · GATE-G5 | ≈ 3.5–5 h |
| by GATE-G5 / 11C | OP-10 `contact@` alias (after OP-09) · OP-20 release-signing key custody if B-20 = a · OP-21 held-out search relevance set (≈ 30 min, if B-28 = a) · ING-GO-B · two HG-11 readouts · GATE-G6 | ≈ 2–3 h |
| 11D + tail | OP-13 US 511 keys (conditional) · ING-GO-C/D + tier bump · final HG-11 readout · OP-19 Zenodo publish (after P37.55) · OP-22 journey walkthroughs, "beautiful" gallery, About text (C-5) · GATE-ACCEPT-R11 · GATE-ANNOUNCE | ≈ 3–5 h |
| any time | OP-08 bottom-up merge sitting #141–#190 (+ optional `v0.1.0` tag) → then OP-06 `main` ruleset with five required checks | operator's choice |
| folded / superseded | OP-15 partner-name dispositions (folded into OP-14 + P37.46 if B-18 as stated) · OP-16 camera-site curation (superseded by P35.49 if B-18 as stated) | — |

**Total ≈ 12–18 h over ≈ 9–10 weeks** (S2 §7.4; inference).

### 11.3 What is waived, deferred or owed — and the trigger that reopens it

| obligation | Round-11 posture | trigger |
|---|---|---|
| independent human evaluation (SIG-EVAL-001/002/005/007, IDENT-027/028; D-R10-HUMAN-1, D-R6.1-EVAL, D-P30.2b-2; rows 184–187) | **owed, non-blocking, never waived**; Round 11 measures, discloses and labels PROVISIONAL | **T-EVAL-IND** |
| SIG-EVAL-004 lower bound | **waived for C0–C2 only** (operator's words) | T-EVAL-IND; a proposal to auto-write an inferential tier; GQ-23 failing twice in a quarter; M-1b < 0.98 |
| hostile-reader second reviewer (SIG-UI-042), dossier independent check (SIG-DOS-002) | owed; `/editorial-standards/` says "not yet performed"; the operator may serve as one disclosed reader | T-EVAL-IND |
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
independent review.

---

## 12. Integration and branch policy (H1, H2; §7.1 Q-11)

- **Stack on #190.** At GATE-P a branch **`r11/seed`** is created at the head of `claude/next-phase-planning` (which forks
  from `b051732c`, #190's head); Stage B commits on top of it; T6 pushes it and opens the **seed PR** with base
  `devin/p33-8-agent-docs-refresh`. Planning commits reach the chain unchanged (no squash, cherry-pick or rewrite).
- **One ticket, one branch, one PR**, branch prefix `r11/`, each PR's base = the previous ticket's branch. Agents never
  merge, retarget, rebase, force-push, tag, or merge `main` into a stack branch, and never push to a branch once a
  successor exists.
- **The operator merges later** (OP-08; H1 §2–§4). H1's simulation: a bottom-up merge `main`@#140 → #190 has zero
  conflicts in 49 steps and ends tree-identical to #190 (`64a23cd7…`), with `main` keeping its lockfile blob; expect a
  transient red on `main` for one step after each of #165/#179/#185. The merge loop must be **bounded at #190** (`TOP=190`
  or an explicit list) so it never sweeps Round-11 PRs, including an unratified seed, into `main` (H1 NEW-5). B1's
  corrections cannot land before #143 without rewriting history; H1 recommends **not** gating the merge on them — if the
  operator wants `main` never to show uncorrected dates without the correction beside them, merge #143–#190 and the seed
  PR in one sitting. If the operator commits to `main` or a pre-#190 branch again, the fix is mirrored into the Round-11
  stack tip, and the orchestrator records `git merge-base --is-ancestor origin/main <chainTip>` at each boundary. After the
  sitting: the `main` ruleset with the five required checks (OP-06) and an optional `v0.1.0` tag by the operator (B-10).
  Releases are built from unmerged stack commits until then (B-10).
- **CI policy:** every Round-11 PR passes all five `ci.yml` jobs (python, docs, composed, security, web) on its current
  head; local-only green is written `locally-green`; the 16 pre-#190 reds are merge-readiness items, not Round-11 blocks;
  clock-dependent latent reds and seed-introduced reds still block (H2 §3.3). Repository settings are operator actions
  (OP-05 before the seed push, OP-06 after the sitting, OP-07 before row 201); no CODEOWNERS.
- **Public-repo push policy (B-16).** The repository is public, so the first push publishes this planning directory.
  Keep `claude/next-phase-planning` **local until T6**. Before the push: SEED-00 removes the credential-shaped literal from
  two planning notes by a forward fix; scan for secrets (`make scan-secrets`), personal identifiers and Part VIII content.
  **The operator's address appears verbatim in three planning files** (META_PLAN §7.1, `baseline/TRACK0_RECORD.md`,
  `feedback/OPERATOR_FEEDBACK.md`), inside verbatim operator quotes. The operator decides at B-16 whether those quotes
  publish as recorded (the address is already the public dispute contact under Q-29) or are redacted by an appended,
  dated correction that names what it replaces (append-only; OM-13). An optional private off-disk backup is OP-23.

---

## 13. Round tail and acceptance

### 13.1 Sub-round acceptance rows (P34.47, P35.64, P36.73; S; read-only)

Each reads live state (§10.3), records a `probe-run/1` record and an acceptance note reporting the **highest layer reached
per row**, and drafts the GATE packet (agent-drafted, labelled). It cannot pass with an unexplained red, a ratchet
regression, a pending seed transition (11A), or an opened window whose leg is unexecuted. The exit lists are §5's
acceptance bullets and S2 §4.1–§4.4.

### 13.2 Round-level success criteria (P38.1 checks each on the final release; conditional on the recommended answers, §4.4)

1. **Features and UX (U-007a; D3 §3a):** all 13 journeys pass both walkthroughs; U-003.1–.11 pass their K-row acceptance
   live; 0 UUID-only labels and 0 undated edges; every figure reaches its evidence in ≤ 2 clicks or says why; search
   covers 55 jurisdictions, 20 cities and the top 25 vendor and agency names; K0 budgets and accessibility pass on real
   data.
2. **Correctness and comprehensiveness (U-007b; D3 §3b):** L3's round targets hold on the final release (CONF-14; §5.4),
   M-1b lower bound ≥ 0.98 per declared namespace, `/quality/` live; the coverage targets of §5.5.
3. **Clarity (U-007c; D3 §3c):** §5.7's clarity list; "beautiful" is the operator's call (B-29).
4. **Honesty:** 0 S0 open; 0 status words unbound to recorded state; 0 "verified/certified/counsel/editorial board"
   claims without basis; PROVISIONAL on every unevaluated figure; disclosure ships in the same publish as exposure.
5. **Build truth:** every boundary read head-bound CI; 0 G1 and 0 G2 violations; every live leg executed in its window or
   re-scheduled with a date; every production statement cites a probe ≤ 24 h old; no proxy signature; ≤ 1 orchestrator
   close-repair.
6. **Cost:** measured monthly infrastructure ≤ $300 every month; the 100× traffic projection ≤ $300 or approved; agent
   spend reported each sub-round.

A criterion disabled by a default is reported "not attempted (default <line>)", never MET.

### 13.3 The 13 acceptance journeys (D3 §2; K13 §8; walked cold from `/` at 390 and 1440 px)

| persona | journeys (budget) |
|---|---|
| local advocate, council meeting in 6 days (≤ 10 min) | **A1** type "Oklahoma City" (1 min, ≤ 3 clicks) · **A2** what is deployed, who runs and approved it, next decision (+3) · **A3** print a council brief (+2) · **A4** know what to bring (+3) |
| investigative journalist | **J1** defend a headline figure (5) · **J2** "who supplies ALPRs to Texas agencies, and who can access the data?" (10) · **J3** is this figure disputed? (3) · **J4** cite it durably (3) · **J5** what changed since the last release? (5) |
| organizers | **O1** who runs what in my county or city (3) · **O2** who decides and when; subscribe (2) · **O3** a local list without the map (2) · **O4** act on a gap (3) |

A journey passes within its budget with no wrong-conclusion risk and every fact carrying a source, an as-of date and a
release id. The agent walkthrough is recorded `agent-verified`, never "user-tested"; the operator walks each too (OP-22).

### 13.4 The tail (P38, rows 456–462, 5.0 runs; S2 §4.5)

| row | what | size |
|---|---|---|
| P38.1 | **CAP.1 (CAP-lite)**: independent gap analysis of landed rows against the Round-11 requirements; composed live verification with CI for every open PR and probe-run records ≤ 24 h old; two-sum headline per status layer | M |
| P38.2 | **CAP.3**: close small in-scope gaps; everything else becomes a DEFERRALS row with a trigger; the **accepted-deviations list**, including **every descope caused by a decision default** | S |
| GATE-ACCEPT-R11 | the operator signs the accepted-deviations list verbatim (HG-14 domain) | — |
| P38.3 | **REC (one row)**: `reconcile-build` backlog + readiness, spec reconciliation, integration plan (T3 may split a/b) | L |
| P38.4 | **DOC (one row)**: `refresh-repo-docs` then `agent-docs`; every production statement cites a probe-run record | M |
| P38.5 | **CAP-02**: announce-readiness review against D3 §5 | S |
| GATE-ANNOUNCE | the operator's decision; never automatic; agents contact no one; the announcement itself is LATER-22 | — |

Compared with Round 10's nine-row tail that read nothing live: 7 rows, 5 runs, live reads by construction; stream
acceptances (TX-16, ACQ-28, CONF-14, CAP-01) are ordinary 11D rows that measure.

### 13.5 Ready to announce (GATE-ANNOUNCE checklist; D3 §5, S2 §8.3)

The operator's own test, *"I would send this to a journalist today"* · every S0 closed live and status words bound to
recorded state · all 13 journeys pass both walkthroughs · D3 §3(b) holds live · attribution gate and Part VIII screens
green, forbidden-terms sources withdrawn · pinned citation and release id on every page · zero-egress serving with the
kill switch and budget alert tested · cost at 100× traffic ≤ $300 or approved · backups, a drilled restore and alerts ·
the dispute e-mail discloses single-maintainer response times · §1 text, a known-issues page and PROVISIONAL disclosures
live · **the dedup is published** (B-26) · the gallery signed (B-29) · the About text written by the operator (C-5) · the
operator confirms the announcement copy. If GATE-ANNOUNCE is unanswered, SIG is not announced.

---

## 14. Risks

| # | risk | mitigation |
|---|---|---|
| R-1 | **Live legs never run** (Round 10's "prepared, not executed", queued) | OM-19 runs due legs at every boundary; no GATE packet while an opened window is unexecuted; "engineered" never reported as "live" |
| R-2 | **Defaults stall or silently descope** (A-18; the nine in §4.4) | A-18 in Part A; each default shown beside its criterion; P38.2 lists every default-caused descope for GATE-ACCEPT-R11 |
| R-3 | **Scale** (≈ 277 rows after splits; CAP-01 fans in ≈ 110 rows) | four Round-10-sized phases; sizing re-checked at each GATE; re-split rule; T3a/T3b |
| R-4 | **Operator load and approval fatigue** (S5 alone carries 88 lines over 323 decision ids) | fast path and defaults; ≈ 5 batched sittings; OM-20; B-2's removal-only allowance; readouts from P35.60's generator; weekday 14:00–20:00Z slots |
| R-5 | **Hosted-write accidents** (L44 rewrites `claim_evidence` under an exclusive lock; re-keying; Wave C ≈ 1.1 M claims on 1 vCPU) | AR-2 restore points; P34.6 drill first; P34.24 clone rehearsal; P34.46/P35.61 never pre-authorised; AR-3; temporary tier bump; one manual job at a time |
| R-6 | **Denial of wallet** before P35.5 | P34.3 makes `sig-web` non-public; P34.5 alert; P35.5 early in 11B; measured spend at every check-in |
| R-7 | **UX outruns the data** (K13 R-1) | all Stream-L S1 fixes in 11B before new surfaces; capability binding; "records" wording until the dedup; CAP-01 checks wrong-conclusion risk |
| R-8 | **Calendar slip** (R0 after ≈ 10-14 compresses Wave A behind P34.46; an outage moves a window a month) | windows are earliest dates; the queue absorbs slips; waves can each move a month; Wave D droppable |
| R-9 | **CI unavailable or flaky** | P34.2 flake allow-list and one re-run; "CI unavailable" → `blockedOn` + verbatim, time-boxed waiver only |
| R-10 | **Rights or legal exposure without counsel** (vendor terms, database right, Part VIII) | per-batch HG-03 lines with "not flipped" defaults; vendor hosts never fetched; officer-naming gate (P35.28) before entity pages; redaction (P36.15) before the evidence hub and raw archive; US-first; withdrawal barrier + dispute channel as remedies |
| R-11 | **The public repo** publishes planning notes, the operator's address and redacted Part VIII findings on first push | B-16 (local until T6); SEED-00 + pre-push scan; the operator's redaction choice (§12) |
| R-12 | **Harness/model switch or usage limits mid-round** | OM-01/A-15: one harness, switches only at boundaries with orient + validators + CI read; usage-limit events reported in the spend line |
| R-13 | **Stage B under-sized**: ≈ 31 ADRs + on the order of 250 draft requirement ids + 277 contracts in SEED-11/12/13 (3 + 3 + 4 runs) | T1 and T3 may split further (T3a/T3b already); a fresh-context sizing review before T3 (decompose-spec Phase 4) |
| R-14 | **Cost baseline is unverified** (G1 list-price ≈ $90–100 vs README "≈ $0/$9") | C-7 now; P34.5 billing export; GATE-G4 re-projects if the measured baseline differs materially |
| R-15 | **Baseline drift during S4/S5** (operator merges, scheduler first fires, the 10-10 replay) | the A1 delta re-runs before T6 (SEED-01); P34.39 reads the replay back; dates from the clock, never from the latest record (AR-4) |

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

Also deferred, outside the catalog: the 45 quiet ADR revisit triggers (watched through `ADR_TRIGGERS.csv`); GraphQL
(RISK-P14-10, on consumer demand); a contradiction to an Atlas row (RISK-P4-08); the next technology-vocabulary version
(SIG-ONTO-057a); Tier 3 (259 candidates) is not acquired at all.

---

## Appendix A — Stage-B translation checklist (exact artifacts T1–T6 must produce)

Stage B starts only after GATE-P is recorded verbatim. Every artifact is append-only where it touches a protected record
(OM-13), dated from `date -u`, and committed on `r11/seed`. Catalog units in brackets (S1a); est. runs from
`data/round11_plan.csv` (seed total 23.2).

**T0 — before GATE-P (planning orchestrator) [SEED-00, 0.5]**
- [ ] META_PLAN §11: one appended, dated correction entry naming each late-stamped change-log line (F-074), and a
      refreshed CURRENT STATE block.
- [ ] Forward-fix the credential-shaped `SIG_INTAKE_*` literal in the two committed planning notes; `make scan-secrets`
      and `test_secret_scan_real_tree_is_clean` pass on the planning tree.

**T1 — Spec amendments and ADRs [SEED-11 3.0, SEED-12 3.0]**
- [ ] `docs/research/_meta/spec_src/96c_partXII_s56_round11.md` (new; name proposed): Part XII, §56 Round-11 contract
      extension with the §6.2 families under final ids; T1 records the draft-id → final-id map.
- [ ] Amendments of §6.3 in their owning `spec_src` section files; one new **Appendix G.7** row set
      (`99c_appG_corrections.md`) incl. the §55 true dates; **Appendix F** rows for every new ADR (`99a_appF_adr.md`);
      family table updated for newly opened prefixes.
- [ ] `BUILD.sh` regenerates `docs/2_canonical_design_spec.md`; `check_spec_src.py` green; new ids append-only; R10-A6
      untouched.
- [ ] `docs/3_sig_golive_spec.md`: goal 5, GL-GATE-01/02/05, gate register, GL-GATE-06…08 (E2-18; ADR-145 pattern).
- [ ] `docs/adr/ADR-146…` — one file per ratified decision in §7, template header, operator words where the decision is
      theirs (EVAL-004 waiver; counsel basis; robots), `## Revisit trigger` in each.
- [ ] Appended `Superseded by ADR-nnn (<date -u>)` status lines on every superseded landed ADR (incl. ADR-015, 058 §3,
      075, 092, 096 §1, 091 §3–4, 097 §2–3/§6 if A-12 = a, 105 §5, 118 §2, 126/127 cutover statements, 076 scheduling
      path, 088's clause); recorded evaluations of the fired revisit triggers (F3 §5.1). No other landed-ADR edit.
- [ ] ADR index regenerated (`build-memory adr-index`).
- [ ] If A-12 = a: `AGENTS.md` gotcha 6 and `web/AGENTS.md` gotcha 1 replacement text (K0 §7.1–7.2).

**T2 — Build-memory repair seed [SEED-01…10, SEED-16; ≈ 7.25]**
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
- [ ] SEED-06 **restore the 53 GATE DECISIONS rows deleted by `c2055d96` first**, from `c2055d96^`.
- [ ] SEED-07 DATE CORRECTION entries in LEDGER and BUILD_INDEX.
- [ ] SEED-08 correction records elsewhere: DEFERRALS correction section; manifest Plan-extension correction lines;
      runs/pr/CAPSTONE addenda; `CORRECTION.md` in the committed fixture-run directories; operator-confirmed addenda for
      the signed GATE-G3 and ACCEPT-R10 readouts (OP-18); the `p-17b713` supersession record — **no footers on landed
      ADRs** (CF-02).
- [ ] SEED-09 BUILD_INDEX index repairs (rows 190/195, PR fills, seq 170a, not-landed note).
- [ ] SEED-10 archive LEDGER lines 1–54 byte-for-byte under `reports/memory-repair/` with a sha256 pointer; slim head
      ≤ 12 KiB; status PAUSED.
- [ ] SEED-16 RETURN PASS superseding note + `RETURN PASS — current` regenerated from `OPERATIONAL_READINESS.md §(f3)` and
      the S1b dispositions; no 184–187 ids.

**T3 — Manifest rows and contracts [SEED-13 4.0 → T3a P34–P35, T3b P36–P38]**
- [ ] `docs/tickets/00_MANIFEST.md`: Round-11 dispatch amendment + banner (P34 11A "Safe, honest, truthful" · P35 11B
      "Correct and traceable" · P36 11C "Explorable core" · P37 11D "Explored and proven" · P38 tail); rows 201–462 from
      `data/round11_plan.csv` (renumbered after the 15 a/b splits; +2 under the A-13 fallback); gate rows without `.n`;
      one appended `## Plan extensions` line; a `## Human prerequisites` section listing OP-01…OP-23 with due points; the
      L3 §6.3 dispatch amendment and the 184–187 gate-cell tokens; HG-05 as an operator-owned integration disposition.
- [ ] One contract per chain row from `_TEMPLATE.md` (+ `harness:` header + B5 §6.2 block): `Run:` line,
      `live_verification`, `Live window:` where windowed, OM-14 mutation list, `live:` edges, requirement ids, acceptance
      stated at its layer; `Kind: skeleton` only for P37.12, P37.47–54, P37.59.
- [ ] Contract notes on 184–187; "Superseded — not executed" sections on `HUMAN-H4.md` / `HUMAN-H5.md`; no H6/H7 files.
- [ ] Requirement → ticket index; a fresh-context decompose-spec Phase-4 sizing review (L splits; over-factoring).

**T4 — Register mapping and validators [SEED-14 2.0, SEED-15 1.0]**
- [ ] `docs/tickets/DEFERRALS.md`: appended annotations for all 36 owed rows per §9.2; new OPEN rows (counsel opinion,
      SEC-003 owner, second reviewer/board trigger, ADR-124 allow row, the D-rows MET-ENGINEERED verdicts need); token
      transitions only queued (CF-03).
- [ ] `docs/build/BACKLOG.csv/.md`: closures with evidence, splits, new rows from BL-059 (incl. the EVAL-004 waiver
      revisit row), RISK duplicate-id renames, RISK-P21-03 route.
- [ ] `docs/build/COVERAGE_MATRIX.csv`: verdict vocabulary + `required_domain`/`achieved_domain`/`owed_legs`/
      `accepted_scope`; F2a/F2b/L3 deltas (§6.6) with Appendix B's corrections; row-by-row re-verdict of the 61 unsampled
      boilerplate MET-DIFFERENTLY rows; each change a `coverage-assessment/1` event.
- [ ] `check_coverage_matrix.py` grammar + cross-checks + spec-derived counts; `check_backlog.py` open-home rule; new
      `ADR_TRIGGERS.csv`; `tools/check_dispositions.py` rule (c) switched to `sub_round ∈ {11A, 11B}`.

**T5 — LEDGER seed and resume prompt [SEED-17 1.0]**
- [ ] CURRENT STATE (values only, ≤ 3 KiB): `round: 11`, `nextTicket: 201` (P34.1; P34.0a under the A-13 fallback),
      `chainTip` / base per §12, `dispatchTarget`, **`harness:`** (CF-04, A-15), `blockedOn`, `returnPass`, `updatedAt`
      from `date -u`; status PAUSED until C10.
- [ ] OPERATING MODE — Round 11: OM-01…OM-20 (§3.3), H2 §7 paste blocks (G3a gate, flake rule), G2 §2 activation rules,
      P16 contact rule, the D-P31.4-1 clock guard, B6 §5.3 overrides if skills are deferred.
- [ ] GATE DECISIONS rows for GATE-M and GATE-P, verbatim with the `date -u` of receipt.
- [ ] Stale-token scan of the head = 0; every path named in the head exists.

**T6 — Validation, dry-run and handoff [SEED-18 0.5, SEED-19 0.5]**
- [ ] Projection regenerated and verified; every validator green (existing + guard core + new checkers); A1 delta re-run.
- [ ] Pre-push scan (B-16) and the operator's redaction choice for the three files holding the operator's address (§12);
      OP-05 settings applied; push `r11/seed`; seed PR to `devin/p33-8-agent-docs-refresh` **5/5 green** on its head.
- [ ] Read-only `orchestrate-build` orient dry-run resolves **row 201 = P34.1 TC-PIN**.
- [ ] `PD/HANDOFF.md` with the exact resume prompt (harness, model, worktree, branch, first row, OPERATING MODE pointer).
- [ ] **GATE-B** recorded verbatim, with the 11A OM-20 pre-authorisation list (S5-3); C10 flips the LEDGER to IN_PROGRESS.

---

## Appendix B — Input inconsistencies this draft had to resolve (for S4)

| # | inconsistency | resolution in this draft |
|---|---|---|
| 1 | B1 §8's correction-ADR draft ("ADRs get an appended correction footer") and SEED-08's scope (33 ADR footers) vs S2 CF-02 (landed ADR bodies frozen; no footers) | CF-02 wins: corrections live only in the register + ADR-146; T1 rewrites B1 clause 2; SEED-08 drops the footers |
| 2 | F2b proposes **WAIVED(ADR)** for SIG-CONTRIB-012/012a/013, SIG-GOV-024, SIG-CHART-033 (outreach) vs S1c B-6 / Q-E2-12 a and S1b (owed later-phase, LATER-04) | owed later-phase by an outreach-timing ADR; **not** WAIVED. Only one requirement waiver remains (EVAL-004, C0–C2) |
| 3 | F2b: EVAL-006 MISSING→MISSING; EVAL-003/004 → AT-RISK-INTEGRATION vs L3: EVAL-006 and EVAL-003 → MET (after CONF-09/12), EVAL-004 → WAIVED scoped | L3 (later row) wins |
| 4 | S1c A-1 (written before Track 0.5) asks for QA-3/QA-4/QA-9 now; Track 0.5 already did most of QA-3/4 | A-1 shown as reduced to the QA-9 drill (+ TLS alert) before 2026-10-10; its value decays daily |
| 5 | S1c Part A = 17 lines / Part B = 43; S2 promotes B-24 | Part A 18 (A-18 = B-24), Part B 42; plus S5-1…S5-4 added by this draft |
| 6 | S1a: R11 252 units / 234.5 runs, later 22 / 25.0 vs `round11_plan.csv`: chain 238.5 runs, later 24 / 27.0 | difference = ACQ-23a/b moved to later (CF-06) and S2's 12 acceptance/gate/tail rows (6.0 runs) |
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

*End of draft. Written 2026-10-01T01:13:07Z → 2026-10-01T01:26:35Z (`date -u`). Next: S4 adversarial reviews (coverage ·
feasibility · truth and safety) in fresh contexts, closed in `reviews/REVIEW_CLOSURE.md`; then S5 / GATE-P.*
