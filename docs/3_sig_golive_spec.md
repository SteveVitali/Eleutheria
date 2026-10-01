# SIG go-live & productionization — design and implementation specification

**Document:** `docs/3_sig_golive_spec.md` · **Version:** 0.2.0 · **Status:** Ratified 2026-09-09 (operator delegated the Appendix-B open questions to Devin's best judgement — see §0.1; workers may implement).
**Date:** 2026-09-09 · **Author:** Devin (for Steve Vitali)
**Amended:** 2026-10-01T14:04:39Z — v0.3.0, the Round-11 reconciliation (§0.2; the goal 5 note in §1; §2.1), recorded by Claude Code (Opus 5.5), Stage-B sub-agent SEED-12c, under the operator's B-4 answer (plan E2-18 / Q-E2-19). The ratified text is kept.
**Repo / worktree:** `~/Eleutheria` (SIG — Surveillance Infrastructure Graph)
**Derived from:** the `sig-postbuild` build (PRs #47–#68, `projectStatus: DONE`); the build ledger's `RETURN PASS`, `GATE DECISIONS`, and `OPEN FINDINGS`; `docs/build/OPERATIONAL_READINESS.md`; `docs/build/INTEGRATION_PLAN.md`; `docs/build/BACKLOG.csv`; `docs/2_canonical_design_spec.md` §§ cited per ticket.
**Requirement IDs:** `GL-<AREA>-<nn>`, append-only. Areas: `GATE`, `REL`, `GOV`, `LEGAL`, `ACCT`, `RIGHTS`, `LIVE`, `INFRA`, `CONTRIB`, `SOURCES`, `DEPLOY`, `SCHED`, `OBS`, `CI`, `META`, `JURIS`, `CCOPS`.
**Normative language:** MUST / SHOULD / MAY per RFC 2119. Prose without a keyword is rationale.
**Precondition:** ticket `EL.1` (build-memory-v2 migration) has landed, so this repo is in **build-memory v2** (`docs/build/README.md` carries `<!-- build-memory: v2 -->`, `docs/build/LEDGER.md` is the machine state, `docs/tickets/DEFERRALS.md` exists and is seeded from the RETURN PASS items). This spec is instantiated into the v2 manifest by `decompose-spec mode=extend`, **not** hand-written into the legacy chain.

---

# Part 0 — How to use this document

## The core idea: three lanes, three homes

The sig-postbuild build produced a functionally complete system that runs composed-green **over fixtures, to local staging** — nothing is live, merged, or deployed. The remaining work to reach a live, public Oklahoma City (and then scale) splits into three lanes that must **not** all be forced into `implement-spec` tickets:

| Lane | Work | Home | New contract? |
|---|---|---|---|
| **A — Human gates** | legal home, operating governance, counsel sign-off, accounts/tokens, hosting/budget, go-public | `docs/tickets/NN[a-z]_HUMAN-H<k>__*.md` / `NN[a-z]_GATE-G<k>__*.md` marker docs + the gate register (§2); readouts in `docs/build/readouts/` | No — markers, signed by the operator |
| **B — Return-pass re-runs** | re-run P21.1/P21.3/P21.4/P21.5/P21.7/P21.8/P21.9 once their gate opens | `docs/tickets/DEFERRALS.md` rows (seeded by EL.1) + the **existing** ticket files, re-run verbatim | No — re-run the same file after ticking its gate |
| **C — New code** | real deployment, scheduling, observability, CI-composed, 2nd jurisdiction, CCOPS connector, the 3 OKC document connectors | new `implement-spec` contracts (Part II Round 4 + LIVE.1's sub-work) | **Yes** — decomposed into the manifest |

**Policy (GL-META-00, MUST):** a return-pass item never gets a new ticket contract; it is a DEFERRALS row whose "re-run line" is the original ticket's `Run:` line. A human prerequisite never gets an `implement-spec` contract; it is a HUMAN/GATE marker. Only genuinely-new build work gets a new contract. This keeps the plan honest (no duplicated contracts) and matches how the sig-postbuild build actually recorded its gate-skipped tickets.

## Instantiation (after EL.1)

```
decompose-spec mode=extend spec=docs/3_sig_golive_spec.md tail=minimal
```
`extend` reads the v2 `docs/build/LEDGER.md`, `DEFERRALS.md`, and `BACKLOG.csv`, then:
1. emits the Round-3 HUMAN/GATE marker files (Lane A) and appends the gate register rows;
2. reconciles the Round-3 return-pass entries (Lane B) against the DEFERRALS rows EL.1 already seeded — adding nothing new, only cross-referencing this spec's `GL-*` ids;
3. emits full ticket contracts for Lane C (Round 4 + LIVE.1's document-connector sub-work) with `NN_<ID>__slug.md` filenames continuing the sequence after EL.1's `P23.*` tail;
4. appends `tail=minimal` closeout rows for the go-live round (a `CAP`/`REC` delta is optional — see D6);
5. writes the manifest rows, runs `check-build-memory.sh`, prints the manual floor.

Rounds are **ratified independently**: ratify Round 3 when the legal/governance path is real; ratify Round 4 when OKC is live. Do not autonomously execute an unratified round.

## §0.1 Operator decisions (delegated 2026-09-09) — baked into GATE DECISIONS at decompose time

The operator delegated the Appendix-B gates to Devin's judgement ("publish everything we want"; "flip all sources, testing the first few end-to-end first"; "use my GCP project for the host"). These are recorded as **pre-answered gate decisions** so `orchestrate-build` does not stall, with honest provenance:

- **GL-GATE-01 (HG-01 legal home) — interim posture, MUST record as interim.** SIG operates as an independent open-source project under maintainer stewardship pending a formal legal-home designation. This unblocks the artifacts; a **real legal home remains a human action before the actual public cutover** (Go-public). Not a substitute for legal counsel.
- **GL-GATE-02 (HG-02 counsel) — engineering disposition, publish-permitting, NOT a legal opinion.** Publication of the SIG graph, the OSM-derived compartment (ODbL, separate + attribution + share-alike), and the OKC dossiers is permitted, resting on the *structural* safeguards already built and tested: Part VIII (no plate/trip/per-person storage; officer-naming gate; sensitivity tiers + coordinate rules), per-compartment licences, publication tiers, honest-rendering. **Labelled in every artifact as "operator/engineering disposition pending counsel; counsel review recommended before real public exposure."**
- **GL-GATE-03 (HG-03/04 flips) — flip all, phased.** RIGHTS.1 flips the **OKC critical subset first** (`okc_procurement`, `okc_council`, `okcpd_policy`, `ok_statute`, `osm_overpass`, `deflock`), records reviewer = "maintainer (delegated)" + date + the rights basis quoted from each packet; LIVE.1→LIVE.2 run end-to-end on that subset as the test; SOURCES.1 then flips the remainder (news sources stay LINK-only per their packets; FR/BE stay design-gated false). Every flip cites its packet's redistributable/derivative/SPDX basis; no fabricated basis.
- **GL-GATE-04 (HG-12 host) — the operator's GCP project, `$SIG_GCP_PROJECT` (name `eleutheria`; the id itself is env-resolved, never committed — D3).** Zero/low-cost design (SIG-STORE-003): static site + `sig-exports` output + deposits on **GCS**; API on **Cloud Run** (scales to zero); Postgres+PostGIS on the smallest **Cloud SQL** tier *or* a single `e2-micro` GCE running the compose stack (DEPLOY.1 picks one in its ADR, keeps the other documented). Infra-as-code (gcloud + a Terraform/`ops/gcp/` module) is **written and validated** by DEPLOY.1; the actual `apply` is **gated on operator `gcloud` auth** (Application Default Credentials in the run shell) and never executed by an isolated subagent.
- **GL-GATE-05 (Go-public) — stays a deliberate human action.** The chain drives to "OKC ingested + published to a GCP **staging/private** target"; the DNS/public cutover (and the `v0.2.0` "first public jurisdiction" tag) is the operator's explicit final step.

> **Amended (Round 11, appended 2026-10-01T14:04:39Z).** GL-GATE-01, -02 and -05 above were overtaken by the 2026-09-15/16 records and are reconciled in §0.2. GL-GATE-06…08 (2026-09-16/18), recorded until now only in the LEDGER, are added there, with GL-GATE-07 and GL-GATE-08 recorded as re-confirmed at GATE-P in the operator's adopted words.

**Credentialed live actions** (real fetches HG-09, GCP `apply`, Zenodo HG-07, MapRoulette HG-08, usability study HG-10) are executed by whatever run shell holds the credentials. In an unattended subagent chain they run in **prepare + gate-pending** mode (code + config landed, RETURN PASS row written) — they are the short list of operator re-runs, not blocks.

## §0.2 Round-11 reconciliation (appended 2026-10-01T14:04:39Z) — goal 5, GL-GATE-01/02/05 and GL-GATE-06…08

**Authority.** The operator's B-4 answer "As stated (Recommended)" (2026-10-01T04:32:16Z), which carries Q-E2-19:
amend this spec to record the 2026-09-16 go-public and its waivers (plan E2-18; ADR-147 item 16). The operator's words
below are quoted verbatim from `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md` with their round
times. Where the operator adopted an agent-drafted sentence or option by selecting it, it carries the label
"agent-drafted, adopted by the operator at <time>" and its sha256 (`printf '%s' "<text>" | shasum -a 256`, prefix shown;
full values in the cited ADRs).

**Pattern (ADR-145).** This section changes no decision and removes no text. §0.1, Part I and Appendix B stay as
ratified on 2026-09-09. This section records what was done after they were written, names the Round-11 ADRs that now
govern, and adds GL-GATE-06…08, which until now existed only in the LEDGER. The GATE DECISIONS rows cited as R32–R53
are the 53 rows restored on 2026-10-01 with dated annotations (`docs/build/LEDGER.md`, SEED-06).

**What happened.** The legal home was named on 2026-09-15 as the operator, an individual maintainer (R42). The public
cut-over (Go-public, GL-GATE-05) was executed on 2026-09-16 with HG-11 skipped by the operator and the HG-02 remainder
deferred (R51). The same day, the operator filled both reviewer roles personally — SIG-PUB-008's independence "waived,
not satisfied" — and resolved the HG-02 remainder by operator-adopted drafted analyses that are explicitly not legal
advice (R52). The §0.1 preconditions — a real legal home, and the two-reviewer and counsel gates before the public
cut-over — were therefore not met when the site went public.

### GL-GATE-01 (HG-01 legal home) — as reconciled

- **Record.** The interim posture above was resolved on 2026-09-15 by naming an individual legal home (R42; annotation
  R32: "superseded in substance by R42"). It was never a formal legal entity.
- **Round 11.** SIG-GOV-012/013 are waived for now (WV-01, A-23, round 9). The sentence was agent-drafted, adopted by
  the operator at 2026-10-01T04:28:49Z, sha256 `b9dc5a9128ac…`: *"I waive SIG-GOV-012/013 for now: SIG's legal home is
  me as an individual, disclosed on the site, revisited at announcement, a first legal demand, funding, or a second
  maintainer."* → ADR-165.
- **Status of the §0.1 text.** "A real legal home remains a human action before the actual public cut-over" is past and
  recorded as not met. A formal legal home stays a revisit: at the announcement, a first legal demand, funding or a
  second maintainer.

### GL-GATE-02 (HG-02 counsel) — as reconciled

- **Record.** No counsel was ever engaged. The rows that say "APPROVED by counsel (operator-reported)" (R49, R50) record
  the operator's own determinations. The label §0.1 required ("operator/engineering disposition pending counsel; counsel
  review recommended before real public exposure") never shipped (annotation R33; E1 NEW-3), and its "before real public
  exposure" clause is past.
- **Round 11.** C-3, round 19 — agent-drafted, adopted by the operator at 2026-10-01T04:54:19Z, sha256 `1461ae213fac…`:
  *"The 'counsel' determinations of 2026-09-16 and 09-24 were my own; there was no counsel. My 09-28 message 'let's defer
  all the human review steps and proceed' was my decision to defer the human review legs."* Past "counsel" entries are
  re-recorded as **the operator's own determination (no counsel)** (ADR-167). The counsel-review clauses of SIG-LIC-009
  and SIG-INGEST-037 are waived — WV-07, A-23, round 9, agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z,
  sha256 `c5a71e9d7fd9…`: *"I waive the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037; rights decisions rest
  on my recorded determinations, labelled as such."* → ADR-182. SIG-LIC-009's risk-register clause stands.
- **The label.** The §0.1 label is replaced by ADR-167's publication-basis label on every public artifact. Its text is
  E2's agent draft, sha256 `f62f9e984c0d…`, and it is **not yet confirmed by the operator**; it ships only after
  verbatim confirmation in a copy batch (B-2).

### GL-GATE-05 (Go-public) — as reconciled

- **Record.** Executed on 2026-09-16 as a deliberate operator action (R51; annotation R36), without the two
  preconditions §0.1 and the gate register name: a real legal home (HG-01) and an independent second reviewer (HG-11).
- **Round 11.** The HG-11 second-reviewer role is waived for Round-11 releases (WV-03, A-23, round 9). The sentence was
  agent-drafted, adopted by the operator at 2026-10-01T04:28:49Z, sha256 `44644f6bd6ff…`: *"I waive the second-reviewer
  role (SIG-PUB-008 / HG-11) for Round-11 releases; each readout states 'single maintainer, no second reviewer'."*
  → ADR-163. SIG-PUB-008 itself stands, and nobody is named.
- **Next public step.** The site is live. The next public milestone is the announcement, which waits for GATE-ANNOUNCE
  (plan §13.5; ADR-172). That gate includes a keep/lift answer in the operator's words for WV-01, WV-03, WV-04, WV-05
  and WV-08.

### GL-GATE-06 (HG-03 blanket disposition, 2026-09-16) — added

- **Record (R53, annotated "blanket").** Sources whose rights block resolves to a clear public licence (CC0, CC-BY,
  CC-BY-SA, ODbL, MIT, public-records or open-API terms) are flipped to `ingestion_permitted=true` with reviewer
  "maintainer (delegated)". Sources with unresolved or undetermined terms, share-alike ambiguity beyond the named set, or
  a `not_contacted` compact posture stay `false`.
- **Status.** Stands as history. The wider GL-GATE-07 followed on 2026-09-18 (annotation R53). In Round 11, flips run
  under GL-GATE-07 as re-confirmed below.

### GL-GATE-07 (rights rule, 2026-09-18) — added, and re-confirmed at GATE-P

- **Record (LEDGER GATE DECISIONS, 2026-09-18, the operator's words as recorded):** *"We should ungate the
  D-SOURCES.12-1 257 gated datasets and for all the 'rights review' cases we should err on the side of approving
  them"*. It was executed as a blanket approval that included non-US rows, with the sui generis database-right risk
  accepted. US rows → `LicenseRef-PublicRecord-FactualCompilation`; non-US rows → `LicenseRef-OperatorAccepted-DBRight`;
  reviewer "maintainer (delegated)".
- **Re-confirmed at GATE-P (A-7, round 3, 2026-10-01T04:03:25Z).** The operator selected "Re-confirm GL-GATE-07"
  (sha256 `dacea8206687…`) over the recommendation. The adopted option text, agent-drafted and adopted by the operator at
  2026-10-01T04:03:25Z, sha256 `1bfedde5feac…`: *"US public records and open-licence sources flip batch-wide under
  precedent, erring on the side of approving."*
- **Guardrails (ADR-169).** Tier-1 batches flip batch-wide, and Part VIII screen lines still apply. New non-commercial
  sources contribute facts and pointers only (A-9). The ≈8,088 express-terms rows stay public under the operator's
  accepted risk (A-8; ADR-183). Non-US database-right flips N1–N21 follow (B-34).
- **Who flips.** The operator executes each wave's flip list (OP-26), each flip in an operator-signed commit or a GATE
  DECISIONS row (OP-25). HG-03 stays an operator action; rights decisions rest on the operator's recorded
  determinations, labelled as such (WV-07).

### GL-GATE-08 (robots, 2026-09-18) — added, and re-confirmed at GATE-P on every host

- **Record (LEDGER GATE DECISIONS, 2026-09-18, the operator's words as recorded):** *"I also wonder if we should
  disregard robots.txt-gated sources and crawl them anyway"*. The recorder read it as a decision to "disregard robots
  entirely": verdicts are probed and recorded, and never gate a fetch (ADR-088). The words themselves are a question
  (E2-X1).
- **Re-confirmed at GATE-P (A-5, round 3, 2026-10-01T04:03:25Z).** The operator selected "Re-confirm GL-GATE-08 as is"
  (sha256 `a18c15758247…`) over the recommendation. The adopted option text, agent-drafted and adopted by the operator
  at 2026-10-01T04:03:25Z, sha256 `9a8a3109c95f…`: *"Keep disregarding on all 122 hosts incl. PrimeGov; conflicts with
  SIG-INGEST-046c for reservations. Not recommended."*
- **Scope (S6R-08, round 26, 2026-10-01T06:51:11Z).** The operator chose "All hosts, as ADR-088 (Recommended)" (sha256
  `038d8bb1c184…`; agent-drafted option, adopted by the operator at 2026-10-01T06:51:11Z). GL-GATE-08 applies on every
  host per ADR-088, new hosts included → ADR-168, which extends ADR-088. Disallows are recorded as `robots_disregarded`
  and disclosed as host + count.
- **Still binding (not waived).** SIG-INGEST-046c rights reservations are refused; rule-7 opt-outs are honoured at
  once; rule 4 (no circumvention) and SIG-INGEST-013 (no challenge defeat) apply on every host.

## Reconciling the P23.x migration tail (decompose-spec instruction)

EL.1 auto-instantiated a generic migration-closeout tail `docs/tickets/P23.1…P23.7` (rows 67–73). It is redundant — PR #68's capstone already verified the composed build and the migration (PR #69) added no product code. `decompose-spec mode=extend` **removes those seven placeholder rows + files** and replaces the tail with this spec's Round 3 + Round 4 chain, ending with one minimal closeout (`tail=minimal`). `CURRENT STATE.nextTicket` is set to the first go-live ticket (REL.1 or, if the operator tags separately, RIGHTS.1's predecessor GOV.1). Historical rows 47–66 and all committed artifacts are untouched.

## Operator runbook (the sessions, in order)

0. **Ratify Round 3** (Appendix B): settle the open questions, flip Status to `Ratified <date>`.
1. **`REL.1`** (operator, any time): re-run `merge_dryrun.sh` over the open stack, merge bottom-up per `INTEGRATION_PLAN.md §(d)`, `make check` on `main`, tag `v0.1.0`, `make sbom` + release. *(May precede or follow EL.1; the stack stays valid either way.)*
2. **Lane A human work** — `GOV.1`, `LEGAL.1`, `ACCT.1`: real-world actions; record answers in `docs/build/LEDGER.md` GATE DECISIONS and sign the HUMAN/GATE markers. Secrets go into the operator's secret manager / the worker's shell env, never into any file (validator greps token shapes).
3. **Go-live re-runs** — as each gate opens, tick it and re-run the named ticket file (Lane B). Order: `RIGHTS.1` (P21.1) → `LIVE.1` (P21.3 + doc connectors) → `LIVE.2` (P21.4 → publish → Go-public → `v0.2.0`) → `INFRA.1` (P21.5) → `CONTRIB.1` (P21.7) → `SOURCES.1` (P21.8/9).
4. **Ratify Round 4** once OKC is live, then run `DEPLOY.1`, `SCHED.1`, `OBS.1`, `CI.1`, `META.1`, then `JURIS.2` and `CCOPS.1`.

Each Lane B/C session is a single `implement-spec` run on the manual floor (or `orchestrate-build` if you want the loop). `gh` authenticated, write perms for the worker.

---

# Part I — Design

## 1. Problem, goals, non-goals

**Problem.** The system is built and proven on fixtures but is inert: 0 sources flipped, no real fetch, no publication, no deployment, and ~10 human/legal/ops gates unsatisfied. The build deliberately stopped at "the system runs; going live is a human decision." This spec turns that decision into an ordered, checkable path.

**Goals.**
1. A single gate register that names every human prerequisite, who owns it, what unblocks it, and what it blocks.
2. Go OKC live end-to-end (real fetch → resolve → publish) behind the existing gates, using the tickets already built — re-run, not rewritten.
3. Productionize: real hosted infra, re-ingest cadence, observability, CI that runs the composed stack, backups + restore.
4. Prove the federation design with a second jurisdiction, and close the one genuinely-missing connector class (CCOPS).
5. Zero fabricated readiness: fixture-backed stays fixture-backed until a gate opens; secrets never enter a file; nothing publishes without the two-reviewer + counsel gates.

> **Goal 5 — as reconciled (Round 11, appended 2026-10-01T14:04:39Z; §0.2).** Publication went ahead on 2026-09-16 without the two-reviewer and counsel gates this goal names (§0.2, "What happened"). Round 11 keeps the goal's first two clauses and reads the third as follows: nothing publishes without a recorded go in the operator's words — a candidate-specific Class S readout, or the Class R standing go while it is current (B-9; plan §5.8) — and every artifact states the posture truthfully: a single maintainer with no second reviewer (WV-03, ADR-163), and the operator's own determinations with no counsel (WV-07; ADR-167, ADR-182). No artifact claims a review, a reviewer or a counsel opinion that did not happen (ADR-147, ADR-152). *This is the agent's reconciliation of goal 5 to the operator's recorded answers (labelled), not a new decision.*

**Non-goals.** No change to the built pipeline's contracts (append-only, wire names, schema). No new reconciliation/inference logic. No automated OSM edits (human-mediated only). No merging/tagging by any worker (operator, per `INTEGRATION_PLAN.md`). No third jurisdiction here (JURIS.3+ is a later round).

## 2. Gate register (Lane A)

Each row becomes a `HUMAN-H<k>` or `GATE-G<k>` marker; the operator signs it; its readout lands in `docs/build/readouts/`. `blockedOn` is never set for a pending gate — it is a DEFERRALS row.

| Gate | Requirement | What unblocks it | Owner | Blocks (GL ticket) |
|---|---|---|---|---|
| HG-05 | Integration & release | merge #47–#68 bottom-up, tag `v0.1.0` | operator | (nothing downstream strictly; milestone) |
| HG-01 | Legal home named (SIG-GOV-012) | operator names the legal entity in `docs/governance/governance-and-code-of-conduct.md` | operator/legal | LIVE.2 publish |
| HG-11 | Operating governance | two reviewer **roles** + written concurrence workflow (SIG-PUB-008) + live takedown/corrections contact | governance | LIVE.2 publish |
| HG-02 | Counsel sign-off | counsel opinion recorded for ODbL 4.4(b) (RISK-P0-01), officer-naming gate, publication tiers, Part VIII | counsel | INFRA.1 OSM export, LIVE.2 publish |
| HG-03 | Per-source rights flips | reviewer reads the 27 packets in `docs/build/reports/rights/`, sets `ingestion_permitted=true` + review metadata | reviewer | RIGHTS.1, LIVE.1, SOURCES.1 |
| HG-04 | Stage-0 outreach | perform + record outreach to the 19 compact projects (SIG-CONTRIB-012/013) | operator | RIGHTS.1, SOURCES.1 |
| HG-07 | Deposit/object-store accounts | Zenodo (sandbox+prod), S3-compatible store, optional SWH token | operator | INFRA.1 |
| HG-08 | Contribution accounts | MapRoulette API key + registered OSM Organised-Editing page | operator | CONTRIB.1 |
| HG-09 | API tokens | `SIG_MUCKROCK_TOKEN`, `SIG_DATA_GOV_KEY`, `SIG_OVERPASS_ENDPOINT`, `SIG_CIVICCLERK_BASE` | operator | LIVE.1 |
| HG-10 | Usability participants | ≥5 naïve participants scheduled (roles only) | operator | CONTRIB.1 study |
| HG-12 | Hosting/budget | a real (zero/low-cost) host + object store + PG target beyond local | operator | INFRA.1, DEPLOY.1 |
| Go-public | DNS/host cutover | operator decision after HG-01/HG-11 | operator | LIVE.2 → `v0.2.0` |

### 2.1 Gate register — Round-11 status (appended 2026-10-01T14:04:39Z; §0.2)

The register above is kept as ratified. This table records, for each gate whose state changed, what the 2026-09 record
says and its Round-11 status. Row ids R32–R53 are the restored GATE DECISIONS rows in `docs/build/LEDGER.md`.

| Gate | 2026-09 record | Round-11 status | ADR / plan |
|---|---|---|---|
| HG-01 | named on 2026-09-15: the operator, as an individual (R42) | SIG-GOV-012/013 waived for now (WV-01); the legal home is disclosed; revisited at the announcement, a first legal demand, funding or a second maintainer | ADR-165 |
| HG-11 | skipped at go-public, 2026-09-16 (R51); both roles then filled by the operator, independence "waived, not satisfied" (R52) | the second-reviewer role waived for Round-11 releases (WV-03); SIG-PUB-008 stands, nobody is named, the naming gate denies by default; each readout states "single maintainer, no second reviewer" | ADR-163 |
| HG-02 | deferred, then "resolved" by operator-adopted drafted analyses that are not legal advice (R51, R52); the "counsel" rows R49 and R50 | no counsel; past "counsel" determinations re-recorded as the operator's own (C-3); counsel-review clauses waived (WV-07); the publication-basis label replaces the GL-GATE-02 label once confirmed verbatim | ADR-167, ADR-182 |
| HG-03 | flips under GL-GATE-03, -06 and -07, reviewer "maintainer (delegated)" | flips under GL-GATE-07 as re-confirmed at GATE-P (A-7) with ADR-169's guardrails; the operator executes each wave's flip list (OP-26), each flip in an operator-signed commit or GATE DECISIONS row (OP-25); the express-terms rows accepted (A-8) | ADR-169, ADR-183 |
| HG-04 | outreach skipped by the operator, 2026-09-16 (R52) | owed later-phase with the trigger "the operator authorises outside contact"; the outreach MUSTs are not waived, and are unmet and owed wherever a connector precedes outreach | ADR-171 |
| HG-10 | usability study skipped by the operator, 2026-09-16 (R52) | owed, not waived (SIG-UI-001; LATER-02) | plan §6.5 |
| Go-public | executed 2026-09-16 (R51) without a real legal home or an independent second reviewer | the site is live; the announcement waits for GATE-ANNOUNCE | ADR-172; plan §13.5 |

HG-05, HG-07, HG-08, HG-09 and HG-12 are not changed by this reconciliation; their state is in `docs/build/LEDGER.md` and
`docs/tickets/DEFERRALS.md`.

## 3. Decisions (first principles)

- **D1 — Re-run, don't rewrite (GL-META-00).** The seven gate-skipped tickets are complete contracts; going live is ticking their gate and re-running the same file. This spec adds their `GL-*` id and points at the DEFERRALS row EL.1 seeded; it authors no duplicate contract.
- **D2 — Human gates are markers, signed, with readouts.** A gate is a pause, never a block. The register (§2) is the source of truth; markers carry the sign-off; secrets are `provided: yes/no` only.
- **D3 — Secrets via a manager/env, never a file.** `ACCT.1` provisions credentials into the operator's secret manager (or the worker's shell env at run time). `check-build-memory.sh` fails on token shapes in any committed file. The `.env*` gitignore + no-token-literal test from P21.3/P21.5 stand. **The rule covers non-public *identifiers*, not only credentials:** the GCP project id is an enumerable target in a public repository, so every document names it as `$SIG_GCP_PROJECT` and the value is resolved from the operator's environment at run time (`tests/connectors/test_secrets.py` guards the literal).
- **D4 — Zero-cost posture is the default (SIG-STORE-003).** `DEPLOY.1`/`INFRA.1` target a single small host + object store + static host; CDN/egress are templates with a live alarm; the `.torrent` + Software Heritage mirrors remain the free succession path; degraded mode + keepalive stay the $0 floor.
- **D5 — Live is proven by the same composed E2E, on real data.** `LIVE.2` re-runs `run_okc.sh` in `--mode live` for green sources; the acceptance queries (J-1, Q-1…Q-13) run against the running stack; the 299-vs-190 contradiction must survive to the published page. No metric is a single whole-set number.
- **D6 — The go-live round gets a minimal tail, not a full capstone.** EL.1 already stands up the Round-2 delta capstone (`P23.*`) over the migration. Round 3 closes with a short `REC`-style readiness delta + `GATE-ACCEPT` (operator re-signs the accepted-deviations list if it changed); a full `CAP.1–CAP.3` is only warranted if Round 4's new code is large (decide at `mode=extend` time via `tail=minimal|full`).
- **D7 — The second jurisdiction is the design's proof, not a copy.** `JURIS.2` reuses `run_okc.sh` as a template but rights-reviews its own sources and exercises the jurisdiction-adapter framework (P18.1) — it is the first real test that the federation design generalizes.

## 4. Critical path

```
                (EL.1 lands: v2 layout + DEFERRALS seeded)
                              │
        REL.1 (merge/tag v0.1.0) ──────────────┐ (milestone, non-blocking)
                              │
   GOV.1 ─┐  LEGAL.1 ─┐  ACCT.1 ─┐             │
          ▼           ▼          ▼             │
   HG-01/11        HG-02      HG-03/04/07/08/09/10/12
          └─────┬─────┴───────────┬────────────┘
                ▼                  ▼
        RIGHTS.1 (P21.1 re-run: flips + outreach)
                ▼
        LIVE.1 (P21.3 re-run + 3 OKC doc connectors) ── needs HG-03/09
                ▼
        LIVE.2 (P21.4 re-run → publish → Go-public → v0.2.0) ── needs HG-01/11/02
                ▼
   INFRA.1 (P21.5) · CONTRIB.1 (P21.7) · SOURCES.1 (P21.8/9)   [parallel once gated]
                ▼
   ───────────── ROUND 4 (ratify after OKC live) ─────────────
   DEPLOY.1 → SCHED.1 → OBS.1 → CI.1 → META.1 → JURIS.2 → CCOPS.1
```

---

# Part II — Tickets

> Round 3 IDs map to the gate register; Lane B tickets carry a **Re-run** line (the original ticket's `Run:`), not a fresh contract. Lane A/C carry full contracts. `decompose-spec mode=extend` assigns `NN_<ID>__slug.md` filenames after EL.1's `P23.*` tail.

## Round 3 — Go live for Oklahoma City

### REL.1 — Integrate & release v0.1.0 (GL-REL-01)
- **Kind:** operator action + verify · **Gate:** HG-05 · **Depends:** the open stack (#47–#68); EL.1 optional-before/after.
- **Goal:** land the whole tested machine as `v0.1.0` without changing behaviour.
- **Steps:** re-run `docs/build/tools/merge_dryrun.sh` (expect 0 conflicts); merge #47–#68 bottom-up per `INTEGRATION_PLAN.md §(d)`, retargeting each next base to `main`; `git checkout main && git pull`; `make check` green on `main`; `git tag -a v0.1.0`, `make sbom`, `gh release create v0.1.0 … sbom.cdx.json`; verify CI green on `main`.
- **Acceptance:** `git tag -l` contains `v0.1.0`; `main` CI green; `docs/build/CHANGELOG.md` `0.1.0` dated; every PR #47–#68 merged (or the delta recorded).
- **Out of scope:** any code change beyond conflict resolution.

### GOV.1 — Legal home & operating governance (GL-GOV-01, HUMAN-H_a + GATE)
- **Kind:** human + small doc · **Gate:** HG-01, HG-11.
- **Deliverables:** name the legal home in `docs/governance/governance-and-code-of-conduct.md` (SIG-GOV-012); define **two reviewer roles** + the written-concurrence workflow (`ReviewerConcurrence`, SIG-PUB-008); stand up a live takedown/corrections contact (org channel only, no personal data). Sign the marker; readout to `docs/build/readouts/`.
- **Acceptance:** governance doc names the home + the two roles + the contact; `docs/build/reports/PUBLICATION_CHECKLIST.md` HG-01/HG-11 rows tick with evidence links.

### LEGAL.1 — Counsel sign-off (GL-LEGAL-01, HUMAN-H_b)
- **Kind:** human · **Gate:** HG-02.
- **Deliverables:** recorded counsel opinions for: ODbL 4.4(b) disposition (supersede the operator's interim disposition with a real one, RISK-P0-01); officer-naming gate; publication tiers + sensitive-coordinate rules; Part VIII compliance of the published surface. Record in a governance doc + the GATE DECISIONS table (opinion summary, not the full privileged text).
- **Acceptance:** each item has a dated counsel disposition; if any tightens the interim posture, the affected `COVERAGE_MATRIX`/ADR note is updated (append-only) and INFRA.1/LIVE.2 consume it.

### ACCT.1 — Provision accounts, credentials, hosting (GL-ACCT-01, HUMAN-H_c)
- **Kind:** human/ops · **Gate:** HG-07, HG-08, HG-09, HG-12.
- **Deliverables:** create/record (as `provided: yes/no`, never values): Zenodo (sandbox + prod), S3-compatible object store + optional SWH token, MapRoulette key + registered OSM OE page, MuckRock/data.gov/Overpass/CivicClerk tokens, and a real host target. Store secrets in the operator's secret manager; document the env names each re-run needs.
- **Acceptance:** every `SIG_*` env name the re-runs need has a `provided: yes` row; `check-build-memory.sh` finds no token literal in any file.

### RIGHTS.1 — Rights review + flips + outreach (GL-RIGHTS-01, re-run P21.1)
- **Kind:** return-pass · **Gate:** HG-03, HG-04 · **Depends:** GOV.1 (reviewer roles exist).
- **Re-run:** `implement-spec spec=docs/tickets/P21.1__rights-review-and-registry-completion.md live_verification=false` after ticking HG-03/HG-04 in GATE DECISIONS.
- **Work:** reviewer decides which of the 27 packets flip to `ingestion_permitted=true` (reviewer role + date + metadata); record Stage-0 outreach outcomes into `STAGE0_OUTREACH_RECORD.md`.
- **Acceptance:** `sig-connectors review-status` shows the flipped sources fully green; `sig-connectors validate` `loadable now ≥ 1`; DEFERRALS `D-P21.1-*` closed.

### LIVE.1 — First real fetches + OKC document connectors (GL-LIVE-01, re-run P21.3 + new code)
- **Kind:** return-pass + **new code** · **Gate:** HG-03, HG-09 · **Depends:** RIGHTS.1, ACCT.1.
- **Re-run:** `implement-spec spec=docs/tickets/P21.3__live-connector-wiring.md live_verification=true` with `SIG_*` env set.
- **New code (the one real build item in Round 3):** implement the three document-connector modules P21.3 could not exercise — `okc_procurement`, `okcpd_policy`, `ok_statute` (fetch the cited PDFs/HTML from `okc_sources.json`, capture to OCFL, parse via `sig-parsing`, emit the same claims the fixtures encode; `shadow_replay` diff = 0 against fixtures). Close BL-023/024/026.
- **Acceptance:** for each green source, one live run into PG with a fetch record; captures in OCFL; idempotent re-run; the three doc connectors pass `shadow` byte-identity + a live smoke; DEFERRALS `D-P21.3-*` closed.

### LIVE.2 — OKC live ingest → publish → go public (GL-LIVE-02, re-run P21.4)
- **Kind:** return-pass · **Gate:** HG-01, HG-11, HG-02, Go-public · **Depends:** LIVE.1, GOV.1, LEGAL.1.
- **Re-run:** `implement-spec spec=docs/tickets/P21.4__first-jurisdiction-ingest-and-publish.md live_verification=true`.
- **Work:** run `run_okc.sh` in live mode over the green OKC sources; build exports + web from the export; J-1 + Q-1…Q-13 against the running stack; hostile-reader review on live pages; complete `PUBLICATION_CHECKLIST.md`; on Go-public, cut over and bump `0.2.0` "first public jurisdiction".
- **Acceptance:** the public OKC dossier serves the 299-vs-190 contradiction with both sources + dates; `/terms` + `robots.txt` served; officer-naming + publication tiers verified on live data; DEFERRALS `D-P21.4-*` closed.

### INFRA.1 — Real deposit, object store, tiles, mirrors (GL-INFRA-01, re-run P21.5)
- **Kind:** return-pass · **Gate:** HG-07, HG-12, HG-02 (ODbL export) · **Depends:** ACCT.1, LEGAL.1.
- **Re-run:** `implement-spec spec=docs/tickets/P21.5__infra-deposit-and-tiles.md live_verification=true`.
- **Work:** real Zenodo concept DOI; object-store push + CDN + **live egress alarm**; SWH save; mirror manifest. Keep the ODbL compartment separate per LEGAL.1.
- **Acceptance:** `DEPOSITS.md` carries a real (non-sandbox) DOI; egress-report reads live usage; DEFERRALS `D-P21.5-*` closed.

### CONTRIB.1 — Contribution-back live + usability study (GL-CONTRIB-01, re-run P21.7)
- **Kind:** return-pass · **Gate:** HG-08, HG-10 · **Depends:** ACCT.1, LIVE.2 (real leverage data).
- **Re-run:** `implement-spec spec=docs/tickets/P21.7__contribution-back-live.md live_verification=true`.
- **Work:** register the OE page (`registered=true`); real MapRoulette challenge + OSM changeset feed → LeverageLedger; run the ≥5-participant usability study; record results + onboarding fixes.
- **Acceptance:** a live challenge exists; the §7 metric page shows real leverage; `USABILITY_STUDY.md` reports median ≤10 min (or the finding); no OSM usernames stored; DEFERRALS `D-P21.7-*` closed.

### SOURCES.1 — Flip + fetch reviewed ecosystem/pathway sources (GL-SOURCES-01, re-run P21.8/9)
- **Kind:** return-pass · **Gate:** HG-03/HG-04 per source · **Depends:** RIGHTS.1.
- **Re-run:** `implement-spec spec=docs/tickets/P21.8__data-driven-and-coarse-international.md live_verification=true` and `…P21.9__stage5-pathway-connectors.md live_verification=true`.
- **Acceptance:** each flipped source has a live run + fetch record; INGEST-043*/pathway ids move to MET-with-live-evidence; DEFERRALS `D-P21.8-*`/`D-P21.9-*` closed.

## Round 4 — Productionize & scale (ratify after OKC is live)

### DEPLOY.1 — Real hosted deployment on GCP + backups (GL-DEPLOY-01)
- **Target:** GCP project **`$SIG_GCP_PROJECT`** (name `eleutheria`). Zero/low-cost design (SIG-STORE-003): **GCS** bucket(s) for the static site + `sig-exports` output + deposits/mirrors (public-read on the published compartment only); **Cloud Run** for the API (min-instances 0, scales to zero); Postgres+PostGIS on the smallest **Cloud SQL** tier **or** a single **`e2-micro` GCE** running the existing `ops/docker-compose.yml` (pick one in ADR-`DEPLOY`, keep the other documented). TLS via the managed cert / Cloud Run default; secrets from **Secret Manager** (never in a file).
- **Deliverables:** `ops/gcp/` infra-as-code (a Terraform module *or* idempotent `gcloud` scripts) parameterised by project id/region; a `sig-ops deploy --target gcp` path that builds + pushes the API image (Artifact Registry) and syncs `web/dist` + exports to GCS; **automated backups** (Cloud SQL automated backups or `pg_dump` + OCFL sync to a GCS backup bucket) and a **documented + tested restore drill** (rebuild the graph from backup + the Zenodo deposit); a cost note vs the GCP free tier.
- **Gate:** the infra-as-code is **written + validated** (`terraform validate` / `bash -n` / a dry-run plan) autonomously; the real `apply`/deploy is **gated on operator `gcloud` ADC** in the run shell (HG-12) — an isolated subagent lands it in prepare mode.
- **Acceptance:** `terraform validate`/plan (or the gcloud dry-run) is green; with ADC present, `sig-ops deploy --target gcp` brings up API + static + PG and the OKC dossier serves from the GCS/Cloud Run URL; a restore drill reproduces the graph; monthly cost documented against the free tier.

### SCHED.1 — Re-ingest cadence & orchestration (GL-SCHED-01)
- **Goal:** the deferred scheduling seam (P21.3 backlog): cadence-driven `sig-connectors run` per source (respecting `PoliteFetcher`/Overpass etiquette), freshness tracking, and the disappearance-detection cadence, via a minimal scheduler (cron/GitHub Actions first; Prefect/Dagster only if warranted). ADR + `RISK` for cadence vs source etiquette.
- **Acceptance:** a scheduled run re-ingests a source, produces new dated claims (never overwrites), and records freshness; a source going dark triggers a disappearance record.

### OBS.1 — Observability & alerting (GL-OBS-01)
- **Goal:** metrics/logs/alerting for the live stack; wire the egress-budget alarm (INFRA.1) to a real notifier; keepalive verification; uptime + error budgets; log retention within the zero-cost posture.
- **Acceptance:** an egress-threshold breach and a keepalive failure each fire a recorded alert; a dashboard/readout exists; no secrets in logs.

### CI.1 — CI hardening (GL-CI-01)
- **Goal:** a CI job that runs the **composed `tests/e2e` for real** (Node + Docker present, so S8/LD-V08 runs in CI, closing the P20.4 gap honestly); nightly composed run; dependency/license/secret scanning; enforce `make docs-check` + `check-build-memory.sh` on PRs.
- **Acceptance:** CI runs `SIG_REQUIRE_DB_TESTS=1` composed suite green with the web build present; a seeded secret/license violation fails CI; nightly run reports.

### META.1 — Housekeeping backlog (GL-META-01)
- **Goal:** `pyproject.toml` descriptions for the 5 packages still marked "skeleton" (BL-052); remaining docs-drift; triage the P22+ `BACKLOG.csv` rows into DEFERRALS/backlog with real landings.
- **Acceptance:** no package description says "skeleton"; `check_backlog.py` green; BL-052 closed.

### JURIS.2 — Second jurisdiction (GL-JURIS-01)
- **Goal:** the federation proof — pick the next jurisdiction, rights-review its sources (new packets, HG-03/04 per source), and run its `run_<juris>.sh` (templated from `run_okc.sh`) end-to-end through the jurisdiction-adapter framework (P18.1). Surfaces any OKC-specific assumptions.
- **Acceptance:** the second jurisdiction ingests → resolves → publishes with its own acceptance queries green; the adapter framework needed no per-jurisdiction hack (or the hacks are recorded as backlog).

### CCOPS.1 — Government-mandated-disclosure connector (GL-CCOPS-01)
- **Goal:** the one genuinely-missing connector class (SIG-INGEST-049*, the P17-FLIP deferral): a `government_mandated_disclosure` connector for municipal surveillance-ordinance (CCOPS) disclosures, through the eight-stage framework + loader gate, per-agency aggregate rows only (Part VIII), with rights packets + review.
- **Acceptance:** INGEST-049* move from PARTIAL to MET with test evidence; a CCOPS disclosure fixture ingests to typed claims; `procured≠deployed` enforced.

---

# Appendix A — Mapping to existing artifacts

| GL ticket | Existing ticket / DEFERRALS | BACKLOG / matrix ids |
|---|---|---|
| RIGHTS.1 | P21.1 · `D-P21.1-*` | packets in `docs/build/reports/rights/` |
| LIVE.1 | P21.3 · `D-P21.3-*` · BL-023/024/026 | doc-connector ids |
| LIVE.2 | P21.4 · `D-P21.4-*` | SIG-PUB-*, SIG-UI-* |
| INFRA.1 | P21.5 · `D-P21.5-*` | SIG-STORE-003/004/005, SIG-GOV-022/023/024 |
| CONTRIB.1 | P21.7 · `D-P21.7-*` · BL-041 (asset-promotion, if folded) | SIG-CONTRIB-014.. |
| SOURCES.1 | P21.8/P21.9 · `D-P21.8-*`/`D-P21.9-*` | SIG-INGEST-043* |
| META.1 | BL-052 | pyproject descriptions |
| CCOPS.1 | P17-FLIP-01 (OPEN FINDING) | SIG-INGEST-049* |

# Appendix B — Ratification answers (2026-09-09, operator-delegated)

1. **Merge timing (REL.1):** operator's call; the chain does not depend on it. Recommendation stands: tag `v0.1.0` at REL.1 (tested milestone), `v0.2.0` on first-public. **REL.1 is left as an operator step, not an autonomous ticket** (merging is an operator action per `INTEGRATION_PLAN.md`).
2. **EL.1 vs REL.1 order:** EL.1 landed first (PR #69); merge whenever. **Answered.**
3. **Legal home + counsel:** no counsel engaged; publish everything. → interim legal-home posture + engineering disposition permitting publication, both honestly labelled (see §0.1 GL-GATE-01/02). Real legal home + counsel = pre-public-cutover human action.
4. **First flips (HG-03):** yes — the four government-records sources + `osm_overpass`/`deflock` first, end-to-end, then the rest; news → LINK-only (see §0.1 GL-GATE-03). **Answered.**
5. **Host (HG-12):** GCP project `$SIG_GCP_PROJECT` (see §0.1 GL-GATE-04 + DEPLOY.1). **Answered.**
6. **Second jurisdiction (JURIS.2):** deferred to the operator at JURIS.2 time (candidate selection is a research step); the ticket ships the templating + adapter exercise regardless. **Deferred, non-blocking.**
7. **Round 4 tail:** `tail=minimal` (a readiness delta, not a fresh full capstone — PR #68 already capstoned the composed build). **Answered.**
