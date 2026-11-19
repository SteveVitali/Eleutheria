# GATE-ACCEPT-R11 — pending readout (P38.2's acceptance-packet draft)

<!-- Agent-drafted packet for the HG-14 domain (P38.2, row 503). Signing rules
     — enforced by `memory_guard.py` and, for origin, by `check_gate_signatures.py`:
       - the guard sentence below stays permanently;
       - signing may ONLY move `Status:` from PENDING to one of {SIGNED, PASSED,
         SKIPPED-BY-OPERATOR, NOT-PASSABLE} and append a `## Signature` block —
         nothing else is edited, no checkbox is ticked;
       - the decision line quotes the operator's exact words and equals the
         `answer (verbatim)` of the named GATE DECISIONS row (ADR-147 rule 1);
       - hedge / question / conditional is not a decision (G4a);
       - agent-written text sits inside a labelled `agent-drafted` block whose
         sha256 the operator confirmed in words recorded as a GATE DECISIONS
         `confirmation` row;
       - an agent never signs and never assumes silence is approval; the commit
         that signs verifies against the committed `allowed_signers` (OP-25,
         G4c — while the key is outstanding the check fails closed). -->

Status: PENDING. No approval, human work or publication is asserted.

Contract: `docs/tickets/504_GATE-ACCEPT-R11__round11-acceptance.md`.
Decision domain: **HG-14** — the Round-11 accepted-deviations list signature
(the operator signs this list verbatim, accepts it with amended lines, or
pauses). Drafted by P38.2 (manifest row 503); its sha256 is recorded in
`docs/build/runs/P38.2.md` and the PR body before the sitting (ADR-147).

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] `operator signs the accepted-deviations list verbatim (HG-14 domain); never guessed past` — the plan cell, verbatim; the signature never ticks this box

## Answers and defaults

Answers: `accept` (the list is signed verbatim) · `accept with <lines>` (a
line's wording amended in the operator's own words) · `pause`. **Each line's
default if unanswered is recorded non-acceptance — never consent (OM-18).**
Silence on the whole packet = pause.

## 1. The accepted-deviations list (HG-14 domain)

Built per line from `data/decision_catalog.csv` (`recommendation` ≠
`operator_answer`; S6R-21, S6R-25), carrying the eleven waivers WV-01…WV-11,
WV-12 (SB-1, adopted in the same sitting family and registered as G.7 R11-W13 —
listed for completeness), A-6's SIG-EVAL-004 waiver (ADR-153), the C-12
withdrawals, and the §4.6 descopes and accepted risks. Every deviation is
reported as decided — none as a defect. No "not attempted (default …)" line
remains (every catalog line was answered).

### 1a. Waivers — spec MUST clauses waived in the operator's own adopted words (spec Appendix G.7, R11-W1…W13)

| # | waiver | clause waived · scope | operator's words (line, time, sha256 prefix) | ADR | default if unanswered |
|---|---|---|---|---|---|
| 1 | WV-01 (R11-W5) | SIG-GOV-012/013 legal-home clauses, "for now" — an individual legal home, disclosed | "I waive SIG-GOV-012/013 for now: SIG's legal home is me as an individual, disclosed on the site, revisited at announcement, a first legal demand, funding, or a second maintainer." (A-23, 2026-10-01T04:28:49Z, `b9dc5a9128ac…`; agent-drafted, adopted by selection) | ADR-165 | not accepted — clause unwaived |
| 2 | WV-02 (R11-W6) | SIG-GOV-015's editorial board — interim single-maintainer authority + public decision log | "I waive SIG-GOV-015's editorial board: I hold interim single-maintainer editorial authority, and every naming/sensitivity decision goes in a public decision log." (A-23, 04:28:49Z, `bee2cd2b1501…`) | ADR-164 | not accepted |
| 3 | WV-03 (R11-W7) | the HG-11 second-reviewer role, for Round-11 releases; SIG-PUB-008's naming concurrence stands | "I waive the second-reviewer role (SIG-PUB-008 / HG-11) for Round-11 releases; each readout states 'single maintainer, no second reviewer'." (A-23, 04:28:49Z, `44644f6bd6ff…`) | ADR-163 | not accepted |
| 4 | WV-04 (R11-W8) | SIG-UI-042's release block; the hostile-reader review stays owed, recorded "not yet performed" | "I waive SIG-UI-042's release block: releases may ship with the hostile-reader review recorded truthfully as 'not yet performed' and any findings listed as known issues." (A-23, 04:28:49Z, `2a0339a96d57…`) | ADR-179 | not accepted |
| 5 | WV-05 (R11-W2) | SIG-GOV-001's one-click clause + all of SIG-GOV-002, for Round 11 — e-mail intake, senders disclose their address | "I waive one-click, unidentified intake (SIG-GOV-001/002) for Round 11: corrections come by e-mail, and the site says plainly that senders disclose their address." (A-23, 04:28:49Z, `bf1f65d5aaa1…`) | ADR-180 | not accepted |
| 6 | WV-06 (R11-W4) | SIG-GOV-008's two-person clause only; scope and tombstone clauses stand | "I waive two-person authorisation for true deletion (SIG-GOV-008): I alone may authorise a deletion, publicly logged with its reason." (A-23, 04:28:49Z, `dbf7a851e9d5…`) | ADR-181 | not accepted |
| 7 | WV-07 (R11-W9) | the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037 | "I waive the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037; rights decisions rest on my recorded determinations, labelled as such." (A-23, 04:28:49Z, `c5a71e9d7fd9…`) | ADR-182 | not accepted |
| 8 | WV-08 (R11-W3) | SIG-GOV-003's response-time SLAs; the handling priority is published without times | "I waive GOV-003's response-time SLAs; SIG publishes its handling priority without time commitments." (S6-F1, 2026-10-01T06:05:22Z, `806faae385d9…`) | ADR-186 | not accepted |
| 9 | WV-09 (R11-W10) | SIG-INGEST-036 rule 6 "ask first", for DocumentCloud/MuckRock only; rules 1–5, 7, 8 bind | "I waive crawler rule 6 (ask first) for DocumentCloud/MuckRock; SIG fetches public pages only, gently, and honours any opt-out immediately." (S6-F2, 06:05:22Z, `94f061234c41…`) | ADR-187 | not accepted |
| 10 | WV-10 (R11-W11) | SIG-INGEST-035's no-direct-capture clause, for Flock transparency portals, probe-only | "I waive INGEST-035's no-direct-capture clause; SIG may fetch Flock portal pages only when served without a challenge, and stops on any challenge." (S6R-01, 2026-10-01T06:51:11Z, `82487f7b3f0d…`) | ADR-188 | not accepted |
| 11 | WV-11 (R11-W12) | SIG-STORE-011 append-only, for one operator-only purge function only (SIG-GOV-008 scope) | "I approve one operator-only purge function as the sole exception to SIG-STORE-011, limited to material SIG must not hold (GOV-008), leaving a tombstone and a public log entry." (S6R-03, 06:51:11Z, `04e7b77f8db7…`) | ADR-189 | not accepted |
| 12 | WV-12 (R11-W13) | SIG-UI-022's default-view clause — the explorer may open on an aggregated overview, every node drilling to its ego view, no-JS parity; "not a global graph" stands | (SB-1, round 27, 2026-10-01T13:46:58Z, `1ce44d4df7f6…` — the plan's S6c enumeration predates this line; listed because G.7 registers it, same waiver class) | ADR-190 | not accepted |
| 13 | A-6 (R11-W1) | SIG-EVAL-004's preregistered 0.98 lower-bound clause, for derivation tiers C0–C2 only; inferential tiers stay review-only (met fail-safe) | "I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes." (A-6, 2026-10-01T04:03:25Z, `03c0a79ef3b8…`; ADR-L3-B = ADR-153) | ADR-153 | not accepted |

### 1b. Descopes and withdrawals — chosen, reported as decided (§4.6)

| # | line (catalog) | the operator's choice (recorded words) | what it descopes | default if unanswered |
|---|---|---|---|---|
| 14 | A-0.1 (OD-17) | "no, wait for P34.18" (b) | no Track-0 registry scrub; the 41 e-mail-shaped owner strings/handle tokens wait for P34.18; exposure recorded unresolved, operator-deferred | not accepted |
| 15 | A-0.2 (OD-18) | "no, wait for P34.21" (b) | no Track-0 bucket change; anonymous read/list on the sig-public 09-27 tree waits for P34.21b's verbatim go | not accepted |
| 16 | A-0.3 (OD-19) | "no, wait for republish" (b) | /visual-language/ and the handle-bearing pages leave in republish #1 (P34.17), not in Track 0 | not accepted |
| 17 | A-1 (OD-01) | "'None now; ticket it'" (c's no-exception path) | no Track-0 exception for QA-3/4/9; the drill + TLS alert are early-11A tickets; risk unresolved, operator-deferred | not accepted |
| 18 | A-2 (OD-03 + OD-26) | "'alert later'" (b); "no envelope and no fixed $ cap" (b) | budget alert + billing export deferred to P34.5 (OP-12); agent usage reported per wave, uncapped by the $300 line | not accepted |
| 19 | A-10 (D-K2-1) | "Auto-allow + absence only" (b + c, not a) | no operator top-50 organisation review; registry auto-allow ADR + typed 'not yet reviewed' state | not accepted |
| 20 | B-28 (D-K3-7) | "Separate agent, labelled" (b) | no operator-written held-out query set; an agent context writes it, labelled 'agent-authored held-out set; not independent' | not accepted |
| 21 | B-31 (Q-L3-3) | "No maintainer check" (c) | no operator maintainer check of quality or dossiers; every Class-S readout and /quality/ say 'no human check performed' | not accepted |
| 22 | B-42 (E4-B2) | "Agent clears, disclosed" (over a) | no operator 'clear' of Part VIII screens; the agent clears per family and readouts state 'cleared by agent screen, no human review' | not accepted |
| 23 | B-8 (OD-08) | "Email, no time promises" (none of a–c) | e-mail-only intake with no published response-time commitment (WV-08 carries the SLA waiver) | not accepted |
| 24 | B-6 (Q-E2-03, via E2-RESID b) | "move the UA/contact URL; do NOT buy sig-project.org" (b) | the sig-project.org purchase descoped; residual squatting risk recorded | not accepted |
| 25 | C-4 (D-K14-1) | "edit — tagline 'Public surveillance, traced to the documents.'" | the operator's own tagline + copy batch #1 verbatim-confirmation path | not accepted |
| 26 | C-5 (D-K14-7) | "omit until the operator writes it" | no 'who runs SIG' section or placeholder ships | not accepted |
| 27 | C-7 (OD-14) | "don't know — keep the ≈$90–100/mo estimate, labelled inference" | no last-invoice figure stated; the estimate stays labelled inference until P34.5 measures it | not accepted |
| 28 | C-12 (OD-28) | "I accept that these features are withdrawn or labelled this round rather than made to work." (adopted by selection) | the six C-12 withdrawals accepted as chosen | not accepted |
| 29 | C-13 (OD-29) | "superseded — ACCEPT-R10 stands as history" | the Round-10 acceptance is superseded by the Round-11 re-verdicts (B-5) | not accepted |
| 30 | S5-4 | "change — 'Keep non-US acquisition'" | CF-06 not confirmed; R11-ACQ-23a/b + Wave-C non-US members stay in scope (added load, kept) | not accepted |

### 1c. Accepted risks — chosen against the recommendation or with exposure recorded (§4.6 → plan §14 R-18…R-32)

| # | line (catalog) | the operator's choice (recorded words) | the risk accepted | default if unanswered |
|---|---|---|---|---|
| 31 | A-8 (Q-J4-2 · D-J3-5 · I7-C1) | "'Keep all, accept risk'" (b): "I accept the express-terms risk for the captured-terms rows …" | ≈8,088 express-terms rows stay public incl. the 3 live NC rows; source pages show the captured terms + accepted basis | not accepted |
| 32 | A-17 (D3-Q3) | "b — fetch vendor-hosted transparency pages" | vendor/platform terms fetched against (Flock/Axon), under the recorded engineering envelope | not accepted |
| 33 | B-39 (I7-C2 · I7-C3 · I7-C4) | "fetch despite terms" (neither a nor b) | DocumentCloud/MuckRock, Sourcewell/OMNIA and vendor pages fetched despite terms (WV-09 scopes DocCloud/MuckRock) | not accepted |
| 34 | B-35 (I7-IT7) | "'IT7 full fetch'" (a over b) | agency-hosted Axon Fusus 'Connect <Place>' pages fetched in full under A-17's envelope | not accepted |
| 35 | A-5 (Q-E2-11 + S6R-08) | "'Re-confirm GL-GATE-08 as is'" (a over b); "All hosts, as ADR-088" | robots.txt disallows disregarded on all 122 hosts incl. PrimeGov, disclosed as host + count; 046c reservations + rule-7 opt-outs honoured | not accepted |
| 36 | B-34 (I7-N1…N21) | "flip under the non-US database-right precedent" (a; rec updated after S5-4) | the EU/UK database right borne on 21 non-US sources (express prohibitions excluded) | not accepted |
| 37 | B-41 (E4-R2a · R3 · R4a · R4b) | "Fetch, screened" / "As listed, R3 flip" / OGL-Edmonton basis / camreg_hk_hk flip | the named source flips executed on their recorded bases | not accepted |
| 38 | A-7 (Q-19 · E4-B1 · I7-RB-01…09) | "a in shape … with GL-GATE-07 re-confirmed" | batch-wide flip authority applied to the 23 new targets + RB members; Part-VIII-flagged members still need their S-line | not accepted |
| 39 | A-21 (OD-23) | "'Keep my name'" (b) | the operator's name stays commit author — a disclosed risk; harness/model trailers enforced in CI | not accepted |
| 40 | A-20 (OD-22) | "'Yes, with labels'" (a over b) | structural spine writes may change live-API answers before HG-11, disclosed by basis label + /status/ notice | not accepted |
| 41 | B-32 (I7-S8 · I7-TR1/TR2) | "'Include S8 screened lane'" (a over b) | the two tribal members ingest their Part VIII-screened lane without a tribal-data-governance rule | not accepted |
| 42 | B-23 (D-K1-5) | "Natural Earth now (OD-09 a), not GeoNames" | gazetteer recall trade-off chosen over GeoNames' better recall | not accepted |
| 43 | B-16 (Q-H2-6) | "a + c" (the conditional option taken) | the planning branch stays local until T6; a git bundle the operator stores privately | not accepted |
| 44 | S5-3 | "'Both + list + P34.45'" | P34.45's ER re-run added to the approved 11A OM-20 list (expired GATE-G4) | not accepted |
| 45 | A-15 (Q-16) | "custom (none of a–d): Devin Desktop, swe-2-high" | single executor tied to the record; no in-round second harness; REVIEW-R11 (Claude Code) runs post-release, before GATE-ANNOUNCE | not accepted |

### 1d. Scope items re-homed, split, superseded or dropped (recorded, not silent)

| # | item | the record | default if unanswered |
|---|---|---|---|
| 46 | Rows 184–187 (P32.22a, P32.23, HUMAN-H4/H5) | superseded, not executed — no independent reviewers exist and none are contacted (A-6/Q-L3-2; ADR-152); obligations stay OPEN under `D-R10-HUMAN-1`, trigger T-EVAL-IND, never closed or relabelled | not accepted |
| 47 | P35.49 | dropped by the plan delta (net +9.5 runs after the added-load inserts; S6c sizing) | not accepted |
| 48 | Inserted rows 287a P35.1a1 · 291a P35.1c · 320a P35.41a | lawful `mode=extend` splits under the round's rules | not accepted |
| 49 | Inserted rows 489a–489e P37.61a…e | lawful `mode=extend` inserts under RULINGS H-1 + E-1…E-4 (verbatim in `readouts/RULINGS-2026-11-15.md`, GATE DECISIONS 2026-11-15); P37.61a's publish apply is the round's only in-scope live-executed mutation (H-1 pre-authorised) | not accepted |
| 50 | D-P30.2b-1 | its fold target (the maintainer check) removed by B-31 — stays OPEN, non-blocking, trigger T-EVAL-IND | not accepted |
| 51 | Deferred obligations the round carries | 193 owed rows (190 OPEN + 3 PARTIAL) of 278, each with `owner:`/`trigger:` in `docs/tickets/DEFERRALS.md`; 89 RETURN PASS map rows / 116 `[[row.legs]]` legs queued (`return_pass check` green — each in exactly one home); the promote chain `D-P36.72b-1` → `D-P37.65a-1` → `D-P37.65b-1` → the post-promote leg set (`D-P37.63-1`, `D-P37.64-1`, `D-P37.67-1`, `D-P37.68a-d-1/-2`) gates the 11B/11C/11D exits and the public layer | not accepted |
| 52 | Recorded non-conformances kept | `NIGHTLY-RED-1` — `nightly.yml` red ≥40 consecutive completed runs (`oracle-unexpected` at `e8dfcb76`; repair routed by the operator, owed under `D-P34.7-1`/`D-P34.2-2`); `DIGEST-LINT-1` — digests stay uncommitted pending an owner decision; `D-P34.5-2` — billing export holds no rows (cost reads `prepared_not_executed`); watch items `VISUAL-MAP-LIGHT-1`/`VISUAL-MAP-DARK-1`/`LH-LCP-MARGINAL-1` — operator-owned allow-list calls; the carried external stack finding (#514-vs-#512 class) — operator-owned integration | not accepted |

### 1e. The anomaly carried for disposition — GAP-RP-1 (finding; the disposition is the operator's)

Four legs recorded QUEUED in run ledgers and PHASE LOG (2026-10-18/19/22) have
no `[[row.legs]]` entry in `return_pass.toml`, no `returnPass:` id, and no
recorded drop; their GATE-G4 §4 pre-authorisation expired at GATE-G5 and was
not re-authorised (GATE-G5 §4's list excludes them): `P35.22-truthful-claim-
identity-live`, `P35.27-resolver-input-live`, `P35.32-ingest-run-report-live`,
and the P35.46 GATE-G4-named ER-run leg. P38.1a §3.4 / P38.1b §4.4 name the
tracking gap; it is registered as `D-P38.2-1` (OPEN, owner: the operator).

Proposed dispositions for the operator — pick one per leg, or pause:

- **drop-with-reason (the P35.53 pattern):** a recorded drop entry in the map /
  LEDGER naming why the leg is no longer owed (e.g. it rides another row's leg,
  or its evidence need lapsed with the expired authority).
- **real RETURN PASS rows:** `[[row.legs]]` entries carrying a verbatim go —
  which needs the operator's own listing, since nothing is pre-authorised on
  silence (OM-20).

Default if unanswered: each leg stays recorded-queued outside the tracked queue
under `D-P38.2-1` (OPEN) — never silently closed.

## 2. The two-sum headline per status layer (P38.1a §2 + P38.1b §§2–3, composed rows 201–500)

305 physical rows (302 non-marker + 3 operator sittings GATE-G4/G5/G6), layer
counts non-exclusive:

| layer | round total | DEFERRED (queued, named) | UNMET |
|---|---|---|---|
| engineered | **302 / 302** | 0 | 0 |
| fixture-verified | **255** | 0 | 0 |
| staging-verified | **15** (+ artifact class: P35.61–P35.64 artifact-verified, P36.79 seal-verified) | 0 | 0 |
| live-executed | **12 rows** with ≥1 recorded live leg | 115 mapped queued legs + 4 unmappable (GAP-RP-1) + the deferral-tracked post-promote set | 0 |
| public | **0** | every publish/promote criterion — rides `P36.72b-promote` + `D-P37.65a-1 → D-P37.65b-1 → post-promote legs` | 0 |
| human-completed | **3 sittings** + recorded decisions | `D-P34.4-2`, `D-P34.5-1`, `D-P35.60-1`, `D-K14-9`, OP-22 walkthroughs `D-P37.68a-d-2`, `D-P37.61d-1`/`D-P37.61e-1`, the HG-11 promote go, OP-26 flips | 0 |

Coverage-matrix two-sum (SIG-ENG-041, at this read): engineering closed
**896** (646 MET + 4 MET-DIFFERENTLY + 246 MET-ENGINEERED) and requirement
satisfied **650** (MET + MET-DIFFERENTLY); 16 WAIVED (the G.7 register above
plus earlier accepted ADRs), 73 open verdicts (60 PARTIAL + 12 MISSING + 1
AT-RISK-INTEGRATION, each routed to an unlanded row or open backlog home), 9
N/A-RATIONALE. Reported as both sums, never "N MET" alone.

## 3. Status (information only; batch — nothing to answer)

- **Gap-closure record (this row, row 503):** the in-scope findings of
  P38.1a/P38.1b dispositioned as named — GAP-RP-1 → `D-P38.2-1` with the two
  proposed dispositions above (the operator's call); Wave-C, NIGHTLY-RED-1 and
  the promote chain surfaced below; the three open COVERAGE_MATRIX verdicts
  re-routed `P38.2 → P38.3a` (SIG-MEM-007, SIG-ENG-046) and `P38.2 → P38.5`
  (SIG-CONF-012) ahead of landing (the landed-route rule); the eight bare `—`
  PR cells on BUILD_INDEX rows 475–482 recorded as a uniformity nit (append-only
  — cells not rewritten; PR numbers live in PHASE LOG #499–#506).
- **Deferral register at close:** 193 owed of 278 (190 OPEN + 3 PARTIAL);
  `obligation_events check` green (794 events, 515 assessments, 4 pre-existing
  stale-ref warnings); `return_pass check` green (278 obligations, 193 owed,
  each in exactly one home).
- **Legs whose window extends past the sitting:** Wave-C `P37.2-l1…l5` — the
  strict ING-GO-C window ran 2026-11-16 → 11-20 and the legs were unrun at
  this read (L4's 48 h grace runs through 2026-11-22T00:00Z; a missed leg
  re-windows under OM-19 — the recorded-consequence class, never a hidden
  failure); Wave-D `P37.54` earliest 2026-11-23 (window 2 2026-12-14 — on
  schedule); `P37.59` intake legs pre-authorised under GATE-G6 §4, expiry this
  gate; `P37.55` external legs queued on the operator's verbatim go.
- **Promote chain:** `D-P35.53-1` DONE 2026-11-18 (the release-infra apply ran
  under the operator ADC); `D-P36.72b-1` OPEN (GATE-G6-approved, window live
  since 11-13T12:00Z — the signed `sig.promotion-approval/1` object + leg still
  owed); `D-P37.65a-1`/`D-P37.65b-1` OPEN (`prepared_not_executed` — the
  HG-11 go, signed readout, staged candidate and window all owed; the 11-18
  "verbatim promote go" shorthand names the `D-P35.53-1:e1` ADC go, not an
  HG-11 promote go — `runs/P37.65b.md` records "No verbatim go exists").
- **CI incidents:** `NIGHTLY-RED-1` — every completed `nightly.yml` run in the
  last 41 concluded failure (≥40 consecutive; latest 44448496659, 2026-11-19,
  same `oracle-unexpected` signature at `e8dfcb76`, plus depaudit/npm legs);
  the flake log (`reports/ci/flake_log.csv`) carries the BuildKit-429 and
  VISUAL-MAP re-run history.
- **Anomalies:** GAP-RP-1 (§1e); the eight bare `—` BUILD_INDEX PR cells
  (uniformity nit); the carried external stack finding (operator-owned
  integration, recorded verbatim, none authored by the chain).
- **Operator-side merges (read from GitHub, `date -u` 2026-11-19):** the stack
  merged through #534; PR #535 (P38.1b) OPEN awaiting merge; this row's PR
  stacks on `r11/P38.1b-…` per H2 PR-1.
- **Not presented while a leg is due (OM-19):** no leg is *due* — every owed
  leg is `prepared_not_executed` with its go named; Wave-C's strict window is
  surfaced as a recorded consequence, not a blocker.

## Signature

<!-- Appended only at signing, by the commit that moves Status:. Fields:
     `received` is `date -u` when the operator's words arrived; `<channel>` is
     how (e.g. chat); the GATE DECISIONS row line names the exact LEDGER row —
     its date and gate must resolve to one row and the quote equals its answer. -->

Operator decision (verbatim, received <date -u> via <channel>): "<exact words>"
GATE DECISIONS row: <date -u of the row> | GATE-ACCEPT-R11
<!-- agent-drafted:begin sha256=<64 hex over the block body> -->
<!-- agent-drafted:end -->
Signed by: repository operator. Recorded by devin-desktop/swe-2-high/subagent, which does not sign.
