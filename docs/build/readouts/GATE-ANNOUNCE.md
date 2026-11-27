# GATE-ANNOUNCE — pending readout (P38.5's announce-readiness packet)

<!-- Agent-drafted packet for the U-009 domain (P38.5, manifest row 509). Signing rules
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

Status: PENDING. No approval, human work, publication or announcement is asserted.

Contract: `docs/tickets/510_GATE-ANNOUNCE__announce-decision.md`.
Packet drafted by: **P38.5** (manifest row 509, `docs/tickets/509_P38.5__announce-readiness-review.md`)
— agent-drafted by `devin-desktop/swe-2-high/subagent`, 2026-11-23 (`date -u`).
Decision domain: **U-009** — the operator decides whether SIG is ready to announce
on the D3 §5 checklist (D3-Q5 [A-17] = a: "D3 §5's checklist is the announce gate; no
earlier preview", 2026-10-01T04:16:29Z). The announcement itself is LATER-22, the
operator's act outside this chain; **this packet decides nothing and announces
nothing, and no one is contacted (U-009, U-011).**

An operator or authorized human record supplies the decision; an agent must not
sign or assume silence is approval.

## Criterion (verbatim)

- [ ] `U-009 operator decision on the D3 §5 checklist; never auto; agents contact no one; the announcement itself is LATER-22 · S6-F3 answered 'S0/S1 must be dispositioned' (2026-10-01T06:05:22Z): not answered until REVIEW-R11 has finished and each of its S0/S1 findings is fixed (plan-extension row under the chain's rules) or dispositioned by the operator; S2/S3 findings feed the next round's planning · waiver triggers at the announcement (S6R-18): a keep/lift answer for WV-01, WV-03 ('for Round-11 releases'), WV-04, WV-05 ('for Round 11') and WV-08, beside Q-29 · re-anchoring (S6R-19): if REVIEW-R11 S0/S1 fixes need rows, decompose-spec mode=extend appends them after this row and then a new GATE-ANNOUNCE row; this row gets the appended token superseded-by(row <n>) (as rows 184-187); no row is renumbered` — **the plan cell, verbatim; the signature never ticks this box.**

## Answers and defaults

Answers: `ready` / `not ready` — plus, verbatim, each own-words line: the five
waiver keep/lifts (§3), the Q-29 revisit (§3), the MUSTs-unmet signature (§2),
and each D3 §5 checklist line (§1). **Each line's default if unanswered is its
recorded default — never consent (OM-18).** Silence on the whole packet = pause;
`continue` answers nothing here; hedged words get a yes/no question (OM-09).

The gate cell carried verbatim (P38.5's contract, quoted not re-decided):
`U-009 · D3-Q5 [A-17] = a: D3 §5 is the gate, no early preview · D-K14-9 [B-29] = yes`
— D3-Q5 answered "a — D3 §5's checklist is the announce gate; no earlier preview"
(2026-10-01T04:16:29Z); D-K14-9 answered "yes — operator 'beautiful' gallery
sign-off before announcing" (2026-10-01T04:43:37Z).

## Preconditions read at packet time (the gate does not sit until all hold)

- **This packet exists** — agent-drafted, labelled; its sha256 is recorded in
  `docs/build/runs/P38.5.md` and the P38.5 PR body before it is shown (ADR-147).
- **REVIEW-R11 has finished** — its register stands at
  `docs/build/reports/review-r11/FINDINGS.md` on branch `r11/ops-review-r11`
  (PR #547, open at packet time): **0 S0 · 1 S1 · 3 S2 · 2 nit**. S6-F3 is met
  only when the **one S1 is fixed or dispositioned by the operator — at packet
  time its disposition is PENDING** (§4). Until then this gate is not answered.
- **No leg is due** (OM-19) — every owed leg is `prepared_not_executed` with its
  go and window named in `docs/build/reports/p38.3a-round11-backlog.md`; no OPEN
  deferral scopes itself to this gate unrecorded.

---

## 1. The D3 §5 checklist state

Each readiness line of `design/D3-product-direction.md` §5 with its recorded
evidence and its default. **Checklist lines are own-words lines — each needs its
own verbatim answer at the sitting; none is answered by this packet.** Where the
recorded state diverges from the line's literal text, the divergence is shown,
never smoothed.

| # | checklist line (D3 §5) | recorded state at packet time | default if unanswered |
|---|---|---|---|
| 1 | "I would send this to a journalist today" (the operator's test, inverse of U-005) | the operator's own judgement — no evidence substitutes; the packet presents the state below for that judgement | not ready — unanswered is non-action |
| 2 | Every S0 is closed live, and every status word is bound to recorded state | REVIEW-R11 found **0 S0** (register §3). Status words: `check_live_claims` corpus green — 109 claims, 0 violations, all grandfathered (the newest committed `sig.probe-run/1` is 2026-11-16T09:42:48Z, outside the 24 h freshness window — **no fresh production-state assertion is cited anywhere in this packet**); the tail probe sweep is red pre-tail (S2-1: 5 probes unrecorded, 6 stale, 2 vacuous — §6). "Closed live" cannot be asserted — the live layer is `prepared_not_executed` | not met as written — bounded state presented |
| 3 | All 13 journeys pass both walkthroughs (agent and operator) | agent-verified legs: fixture green in their dispatches (A1–A4 20 passed/4 by-design skips; J1–J5 22/2; O1–O4 16/0; consolidated per-ask 52/0, all over the 515-route publishable-fixtures build); the promoted-release legs are `prepared_not_executed` (`D-P37.68a-1`/`b-1`/`c-1`/`d-1` — the promoted P37.65 release does not exist). Operator walkthroughs: `D-P37.68a-2`/`b-2`/`c-2`/`d-2` OPEN — the packets are committed, the record tables blank | not met as written — both halves owed |
| 4 | The §3(b) correctness criteria hold live | engineered-side evidence landed (the placement engine P35.19, acceptance rows P37.63/P37.64/P37.66/P37.67); "hold live" rides the promoted release — the public layer of the composed two-sum is **0** | not assertable live — queued behind the promote chain |
| 5 | The attribution gate and the Part VIII screens are green, and forbidden-terms sources are withdrawn | attribution re-export: the P37.61a republish applied 2026-11-16T10:00Z — post-verify all three audit items absent (`/visual-language/` 404 on both origins, `task/new/` 404 + 78 objects deleted, the fabricated review + false promise strings 0-hit; `runs/P37.61a.md`). Part VIII screens: agent-cleared, disclosed (B-42 "Agent clears, disclosed"; residential demotion P35.66, officer-naming gate P35.28, redaction P36.15). **"Forbidden-terms sources are withdrawn" diverges from the decided state:** Q-J4-2 answered b — "Keep all, accept risk" (2026-10-01T04:07:45Z): the ≈8,088 express-terms rows stay public with captured terms + accepted basis disclosed (A-8); no withdrawal | the divergence is presented, not re-decided — the operator reads the line against A-8 |
| 6 | Every page shows a pinned citation and its release id | citation machinery shipped (TX-13a; pinned `/s/<pub>/` durable half rides ACT-24 — HG-11, queued); the current public surface predates it — not assertable live | not assertable live — queued behind the promote chain |
| 7 | Zero-egress serving is live, and the kill switch and budget alert have been tested | machinery landed (P35.5: `PushLimits`, non-listable origin assertion, $50 hard ceiling + warn/alarm, R2 kill-switch runbook); the R2-mirror live leg `P35.5-r2-mirror` is QUEUED — blocked on OP-09 (`D-P34.50-1` OPEN) + R2 credentials (HG-09), its GATE-G5 pre-authorisation expired at GATE-G6. Budget alert: the $0.01 test budget was created live; the operator's e-mail receipt confirmation is `D-P34.5-1` OPEN; the billing export holds no rows (`D-P34.5-2` OPEN) | not met as written — queued, each go named |
| 8 | Cost at 100× traffic stays within $300/mo, or the operator has approved more | committed spend ledger bound: GCP $100 estimate vs $300 (33%), pending rows named (`cost-ledger` reads at the P37.68 dispatches); no measured 100× figure exists — the cost-read legs are `prepared_not_executed` on the promoted release and the billing export holds no rows | estimate presented as estimate — the measured read is owed |
| 9 | Backups, a drilled restore and operator alerts are in place | PITR restore drill ran live green 2026-10-02 (`D-P34.6-1` DONE — RTO 1069.2 s, 10/10 parity); owed: the monthly logical export, lifecycle rules, seed relabel, fullrestore drill (`D-P34.6-2…-5` OPEN, each needs a verbatim go); the post-schema-deploy drill `D-P34.6-6` stays owed — the schema deploy clean-failed (§6) so its trigger has not fired. Alerts: the SIG-ALERT/TLS-expiry policy leg `D-P34.4-1` OPEN (window-queued); the operator's e-mail receipt `D-P34.4-2` OPEN; the alerting-as-code roll `D-P35.2-1` OPEN | partially held — the drill is real; the queued legs are named |
| 10 | The dispute email discloses single-maintainer response times | the dispute page publishes the handling priority with **no** response-time commitment (WV-08/ADR-186 — the SLA clause is waived; "SIG promises no response time" verified live on the post-publish read 2026-11-16) | met as recorded — the waived form is the published form |
| 11 | The §1 text, a known-issues page and the PROVISIONAL disclosures are live | engineered in the release tree (W0/W1/W2 copy batches, `/quality/`, PROVISIONAL disclosures); "live" rides the promoted release — public layer 0 | not assertable live — queued behind the promote chain |
| 12 | The operator has confirmed the announcement copy and posts it. Agents contact no one | the operator's own act at and after the sitting (U-009, LATER-22); nothing is drafted, sent or posted by any agent | unanswered is non-action — SIG is not announced |

**K14 §7 supplementary checklist** (UXK14-12's record; the same defaults apply):
about/glossary/methodology "In brief" pages engineered (live rides promote);
tokens light+dark with contrast tests + axe green at fixture; reflow 320 px and
reduced-motion projects green at fixture; brand/print sets landed (the council
brief page-1 check rides the promoted bundle); visual-regression baselines land
with `check:visual`/`test:visual` — the **operator's "beautiful" gallery
sign-off (D-K14-9) is owed, never agent-signed** (P4); the About page states the
maintainer model + review status (D-K14-7 — "who runs SIG" omitted until the
operator writes it); the fresh-agent orientation check is recorded
`agent-verified`, never user-tested.

## 2. The 'spec MUSTs unmet at launch' register (TS-05 — signed verbatim at the sitting)

Bounded by the adopted waivers: after all eleven (WV-01…WV-11, plus WV-12 and
A-6's SIG-EVAL-004 clause) the register lists only items owed for other reasons —
it no longer names SIG-GOV-003, SIG-INGEST-036 rule 6, SIG-INGEST-035's
no-direct-capture clause or SIG-STORE-011. Each line cites its committed verdict
(`docs/build/COVERAGE_MATRIX.csv` at this packet's commit) and its home.

| # | requirement | committed verdict | what is owed at launch | home / trigger |
|---|---|---|---|---|
| 1 | SIG-EVAL-001 (§55.4 preregistered evaluation) | MET-ENGINEERED(D-R10-HUMAN-1) | the real-human evaluation campaign — engineering closed; human participation owed | `D-R10-HUMAN-1` · trigger T-EVAL-IND (LATER-01, BL-088) |
| 2 | SIG-EVAL-002 (independent labelling) | PARTIAL | the reviewer-isolated labelling machinery landed; zero human labels — campaign awaits humans | BL-088 · T-EVAL-IND |
| 3 | SIG-EVAL-005 | MISSING | owner P32.23 deferred wholesale with the S3 human-eval spine (operator decision; true date 2026-09-28 per the recorded date correction) | BL-088 · T-EVAL-IND |
| 4 | SIG-EVAL-007 | MISSING | owner P32.22a deferred wholesale with the S3 spine; the candidate-specific frame follows development | BL-088 · T-EVAL-IND |
| 5 | SIG-DOS-002 (§55.3 dossier rubric) | MET-ENGINEERED(D-R10-HUMAN-1) | the fail-closed release-validation machinery landed; `pilot_complete` requires a completed independent review the machinery never fabricates | `D-R10-HUMAN-1` · T-EVAL-IND |
| 6 | SIG-UI-001 (§39 usability) | PARTIAL | the moderated ≥5 naïve-participant study — protocol + opt-in aggregate-only instrumentation landed; the study is not run (HG-10) | BL-040 · `D-R10-USERS-1` |
| 7 | SIG-CHART-033 (federation compact) | MISSING | Stage-0 outreach — owed later-phase, **not waived** (ADR-171) | BL-082 · "the operator authorises outside contact" |
| 8 | SIG-CONTRIB-012 (Stage-0 MUST) | MISSING | same — §5 below | BL-082 · same trigger |
| 9 | SIG-CONTRIB-012a (opening offer SHOULD) | MISSING | same | BL-082 · same trigger |
| 10 | SIG-CONTRIB-013 (archival-succession offer) | PARTIAL | carried in the letter template; owed with the outreach act | BL-082 · same trigger |
| 11 | SIG-GOV-024 (succession/sustainability) | PARTIAL | mirrors + SWH machinery built (P21.5); the live deposit leg stays owed (`D-P21.5-1` + `D-R11-ARCHIVE-1`) | BL-082 · same trigger |
| 12 | SIG-PUB-003d (private exposure channel) | PARTIAL | raising an exposure privately with an ecosystem project is outside contact — operator-gated (ADR-171, U-011) | BL-082 · same trigger |
| 13 | The express-terms exposure (§14 R-19) | — | ≈8,088 captured-terms rows stay public under the operator's accepted basis (A-8, 2026-10-01T04:07:45Z); SIG-INGEST-046c's affirmative-reservation refusal stays PARTIAL and unwaived — any 046c case returns to the operator | BL-086 · a rights-holder objection or takedown |
| 14 | ~~"My location" vs SIG-GOV-017 (§14 R-27)~~ | MET | **closed, not owed** — the GOV-017 analysis landed (P37.72); the prohibited surfaces are enforced structurally (`api/prohibitions.py` contract test); map-pan only, nothing leaves the browser | — |

**Register totals (coverage two-sum at this packet's commit):**
`coverage two-sum: engineering closed = 896 · requirement satisfied = 650`
(646 MET + 4 MET-DIFFERENTLY + 246 MET-ENGINEERED(D-…) = 896; satisfied =
MET + MET-DIFFERENTLY = 650; 16 WAIVED · 73 open verdicts each routed · 9
N/A-RATIONALE — `check_coverage_matrix` green, 994 rows). The public layer of
the composed two-sum is **0** — no release is promoted.

**The six ids this row owns the re-verdict on** (P38.3b §4 — the landed-route
rule leaves them with the announce-readiness review; the packet records their
state, it does not re-verdict a living register): `SIG-MEM-007`
MET-ENGINEERED(`D-P34.2-2` — the nightly `--all` sweep has no green run while
NIGHTLY-RED-1 stands) · `SIG-ENG-046` MET-ENGINEERED(`D-P34.1-1` — the
cancelled-push observation is exercisable; the audit's call, recorded not
decided) · `SIG-CHART-006` + `SIG-CHART-021` PARTIAL (the demonstrable
all-13-answerability / all-8-goals debts carry past the signed acceptance
packet) · `SIG-ENG-025` PARTIAL (the standing quarterly cost-scale review is
`D-P38.3a-1`, owner the operator/maintainer, first owed at the 2027-Q1
boundary) · `SIG-CONF-012` PARTIAL (the remaining claim-probe verification —
newest committed probe 2026-11-16 is stale; two sweep producers are vacuous).

## 3. The waiver keep/lift lines (S6R-18) and the Q-29 revisit (TS-21)

A keep/lift answer for each waiver whose trigger fires at the announcement or
whose scope ends with Round 11 — each its own verbatim line; `continue` answers
nothing. The waiver texts are quoted from the signed GATE-ACCEPT-R11 list (§1a),
which the operator signed 2026-11-19T06:55Z (retro: the signed
`GATE-ACCEPT-R11` readout's Signature block).

| # | line | the adopted waiver (operator's recorded words, sha256 prefix) | the keep/lift question at announcement |
|---|---|---|---|
| 1 | **WV-01** (R11-W5, ADR-165) | "I waive SIG-GOV-012/013 for now: SIG's legal home is me as an individual, disclosed on the site, revisited at announcement, a first legal demand, funding, or a second maintainer." (`b9dc5a9128ac…`) | **the trigger is this sitting** — keep the individual legal home or lift the waiver? |
| 2 | **WV-03** (R11-W7, ADR-163) | "I waive the second-reviewer role (SIG-PUB-008 / HG-11) for Round-11 releases; each readout states 'single maintainer, no second reviewer'." (`44644f6bd6ff…`) | scope ends with Round-11 releases — keep (extend to the announced release) or lift (a second reviewer is required)? |
| 3 | **WV-04** (R11-W8, ADR-179) | "I waive SIG-UI-042's release block: releases may ship with the hostile-reader review recorded truthfully as 'not yet performed' and any findings listed as known issues." (`2a0339a96d57…`) | keep — the announced release ships with the review recorded 'not yet performed' — or lift? |
| 4 | **WV-05** (R11-W2, ADR-180) | "I waive one-click, unidentified intake (SIG-GOV-001/002) for Round 11: corrections come by e-mail, and the site says plainly that senders disclose their address." (`bf1f65d5aaa1…`) | scope "for Round 11" — keep e-mail intake at announcement (the Round-12 posture needs its own record) or lift? |
| 5 | **WV-08** (R11-W3, ADR-186) | "I waive GOV-003's response-time SLAs; SIG publishes its handling priority without time commitments." (`806faae385d9…`) | keep — the site announces with no published response times — or lift? |
| 6 | **Q-29** (TS-21) | the dispute/intake contact is the operator's personal address (Q-27/B-8: "e-mail-only intake (the operator's address until contact@ exists) until after the announcement", 2026-10-01T04:35:53Z — retro: `decision_catalog.csv` Q-27); OD-04 decided the `contact@surveillancegraph.org` alias — OP-10 creates it after OP-09's DNS switch, owed under `D-P34.50-1` OPEN — **the alias does not exist at packet time** | **keep the personal address as the public contact, or require the `contact@` alias before announcing?** — its own verbatim line |

## 4. The REVIEW-R11 findings register and the S0/S1 dispositions (S6-F3)

The register: `docs/build/reports/review-r11/FINDINGS.md`, branch
`r11/ops-review-r11`, PR #547 (open at packet time, reviewed at `58d81274` —
the P38.4 tip; merge-base `2f4e9e57`, ~3,778 commits, ~8,873 files).
**Provenance, preserved verbatim (honesty note):** the manifest note specs the
review as "Claude Code, Opus 5.5, xhigh" (`00_MANIFEST.md` REVIEW-R11 row, A-15);
the operator elected a Devin review worker — the register is an **agent-drafted
review by `devin-desktop/swe-2-high/subagent`**, not the specced Opus review.

Register summary: **0 S0 · 1 S1 · 3 S2 · 2 nit.** S6-F3 gates this sitting on
the S0/S1 set only; S2/S3 findings feed the next round's planning (information
lines).

| finding | severity | the finding (summary of the register's own text) | disposition at packet time |
|---|---|---|---|
| **S1-1** — an uncovered `decision` gate record stands at HEAD (ING-GO-B) | S1 | `docs/build/LEDGER.md:325` — the ING-GO-B `decision` row committed unsigned (`6df21fce`, 2026-10-15 — retro: REVIEW-R11 `FINDINGS.md` S1-1; `check_gate_signatures` flags it in every containing range; a pushed commit cannot be retro-covered). The same decision substance stands `G`-signed at LEDGER:316; the go + the #299 waiver were re-recorded as G4c-exempt `confirmation` rows LEDGER:326–327; the waived red was knowingly merged; the Wave-B window already ran. Register's proposed dispositions: **(a)** a signed `waiver`/`decision` row re-recording the go + merge waiver under the OP-25 key, or **(b)** accept-with-reason citing LEDGER:316 + 326–327 + the exercised window | **PENDING — the operator's disposition does not exist at packet time** (no signed row naming this finding is committed; cited, never fabricated). S6-F3 is unmet until it lands — the gate does not sit |
| **S2-1** — tail probe sweep red pre-P38.5; two committed probe records vacuous | S2 | `check_round_close.py check --round-tail 2026-10-01` → 13 problems: no records for `route-allowlist`, `release-record`, `live-config-drift`, `monitoring-liveness`, `conf-gen-regression`; six stale (>24 h); `api-release-parity` + `number-truth` evaluated nothing (all-skipped — G11 fails a vacuous record at the tail). Proposed: defer-with-trigger — the tail re-run is contract work; the two producers must actually measure | information for the next round's planning — the re-run is owed and named |
| **S2-2** — `nightly.yml` red ≥43 consecutive runs | S2 | the owed observation of `D-P34.7-1`/`D-P34.2-2`; `oracle-unexpected` at `e8dfcb76` + `depaudit`/`npm` legs; repair operator-routed (PR #543 open — §6). Proposed: accept-with-reason or fix row | information — a standing red scheduled job, recorded verbatim |
| **S2-3** — obligation-ledger warnings: volatile + stale evidence refs | S2/nit | `obligation_events.py check` green with 14 warnings — six event refs + eight coverage refs cite gitignored `docs/build/logs/**`; five superseded-row refs no longer resolve. Proposed: accept-with-reason or a small fix row re-citing committed paths | information — non-blocking at this gate |
| **nit-1** — `evidence_capture` in-place backfill UPDATE | nit | `db/deploy/claim_assertion_bindings.sql` backfills the new `capture_classification` column — disclosed, outside the claim spine's guard list, provable-only | information |
| **nit-2** — curation token `resolve` dict lookup / demo-token posture | nit | non-constant-time lookup (theoretical timing channel); demo tokens stripped only when `dsn_backed`; the surface stays loopback + `SIG_CURATION_ENABLED`-gated | information |

**Re-anchoring (S6R-19):** no fix row has been appended for S1-1 at packet time;
if a fix row is needed it lands after row 510 by `decompose-spec mode=extend`,
then a new GATE-ANNOUNCE row, and row 510 gains `superseded-by(row <n>)`. No row
is renumbered.

## 5. The outreach-owed list's final form (ADR-171 — owed, never implied satisfied)

Stage-0 outreach changes from a pre-connector precondition to an **owed
later-phase obligation** — `D-R11-LATER-04` — whose trigger is "the operator
authorises outside contact" (Q-E2-12 = a, 2026-10-01T04:33:54Z; U-011 — no one is
contacted
outside the project). The same timing governs records-request sending
(`D-R7.2-SEND`), recruiting (Q-28 = no) and contribution-back. **No outreach
has been performed; no contact is made by this packet or this gate.**

`docs/build/reports/STAGE0_OUTREACH_RECORD.md` as it stands — 19
federation-compact project rows, every `date_sent` `—`, outcomes as recorded:

| outcome | count | projects |
|---|---|---|
| `public_terms_only` | 8 | OpenStreetMap/OSMF · DeFlock · Eyes on Flock · EFF Atlas · EFF Data Driven · MuckRock · DocumentCloud · Flock Finder |
| `not_contacted` | 10 | Have I Been Flocked · ALPR Watch · ALPR Accountability Atlas · ALPR Abuse Library/Kansas Watch · Drivers Against Flock · Flock-You · Local DeFlock/Eyes Off groups · Technopolice/LQDN · Surveillance under Surveillance · PanoptiCity |
| `no_response` | 1 | FlockReporter (DNS ceased 2026-07-28…08-20, SIG-INGEST-039b — a recorded posture, not outreach) |

The 11C + 11D acquisition/connector rows carry the Stage-0 set as owed-unmet
(manifest outreach notes; no contract stamps it satisfied). HG-04 is recorded
SKIPPED-BY-OPERATOR (`D-P21.1-2` WONTFIX 2026-09-16 — the operator elected to
skip Stage-0 outreach; the MUSTs stay owed under ADR-171/LATER-04, never
relabelled satisfied). Requirement rows 7–12 of §2 name the owed ids.

## 6. Status (information only; batch — nothing to answer)

Recorded at packet time (`date -u` 2026-11-23); every production assertion is
bounded — newest committed `sig.probe-run/1` is 2026-11-16, outside the 24 h
freshness convention, so the lines below cite *records*, never fresh state.

- **Chain state:** rows 201–508 landed; BUILD_INDEX rows 1–508; `projectStatus:
  IN_PROGRESS`. Composed two-sum (P38.1a/b re-reads): engineered 302/302 ·
  fixture 255 · staging 15 + artifact/seal classes · live-executed 12 rows with
  ≥1 recorded live leg · **public 0** · human 4 sittings (GATE-G4/G5/G6 +
  GATE-ACCEPT-R11 — the acceptance list SIGNED 2026-11-19T06:55Z, retro: the
  readout's Signature block).
- **Hosted-spine schema deploy — clean-failed, queued for re-deploy:**
  `OPS-SPINE-SCHEMA-DEPLOY` applied 19/41 pending changes then failed on
  `closed_vocabulary` verify (`division by zero` — 133 production
  `vocab_predicate` rows carry `skos_concept_iri IS NULL`; insert-only change
  cannot backfill); sqitch reverted all 19 — poststate == prestate (39
  deployed). Owed: a new append-only sqitch change + a PITR-clone rehearsal
  before re-deploy; the vocabulary fix rides PR #544 (5/5 recorded, awaiting
  merge at packet time). The post-schema-deploy restore drill `D-P34.6-6`
  stays un-triggered.
- **Export / re-cut chain — queued behind the deploy:** the newest authorised
  national export (2026-09-27) predates the `web/*` artifact set; a fresh
  `export.sh --apply` run is authorised ("Run the export", 2026-11-20T07:22Z)
  and its IAM is declared-synced (`sig-export-rt` `objectUser`, job Ready);
  `run`/`fetch`/re-cut stay blocked on the schema re-deploy.
- **Release registry — partial stage + orphan cut event, honestly recorded:**
  the halted 2026-11-20 release-cut leg left a stale `registry/LOCK` (broken
  with a recorded reason under the same sitting's go) and a stranded label
  `sig-2026-11-20.1` — left recorded, no wider change.
- **Promote chain:** `D-P35.53-1` DONE 2026-11-18; `D-P37.65a-1`'s two legs
  authorised ("Authorize now" 2026-11-20T00:15Z — release-cut + live-crawl)
  and blocked behind the export leg; `D-P37.65b-1` OPEN — the promote runs only
  on the operator-signed `sig.promotion-approval/1` (HG-11 readout owed, never
  pre-authorised); every post-promote leg `prepared_not_executed`.
- **Wave-C `P37.2-l1…l5`:** L2 GREEN — `sig-pg` runs `db-custom-2-7680` (the
  L2 go "Bump the tier", 2026-11-20T06:45Z); L3 admitted (gate GO 08:48Z), the
  scoped `secretAccessor` grants applied, then execution-blocked — all 12
  declared keyed secrets absent (`sig-us511-*-key` ×10, `sig-qldtraffic-key`,
  `sig-nsw-live-key`; operator "I'll create them now" 18:20Z; 0/12 verified at
  last read, LEDGER 2026-11-20T18:20Z); the strict window
  <2026-11-21T00:00Z elapsed — **L3 and L5 (the tier revert) queue for
  reauthorization**, recorded consequence, never a silent miss.
- **`nightly.yml` — NIGHTLY-RED-1:** ≥43 consecutive completed failures at the
  last recorded read (2026-11-19, `oracle-unexpected` at `e8dfcb76`); the
  replay machinery fires and reports honestly — the verify condition is unmet;
  owed under `D-P34.7-1`/`D-P34.2-2` (OPEN); repair PR #543 open as a draft
  (web legs resolved at last record).
- **Probe records:** newest `sig.probe-run/1` 2026-11-16T09:42:48Z
  (`p37.61a-harm-republish-post`, `overall=fail` — it honestly recorded
  pre-apply harm 18 min before the republish; the same leg's post-verify showed
  the items resolved). **Stale** under the tail sweep convention;
  `api-release-parity` + `number-truth` are committed vacuous all-skipped
  records (S2-1); five sweep probes hold no record.
- **Deferral register:** `return_pass.py check` green at packet commit — 281
  obligations, 196 owed, each in exactly one home; `obligation_events.py check`
  green (797 events, 515 assessments, 14 warnings — S2-3); the P38.3a register
  holds the 195-owed audited snapshot with every owner/trigger.
- **Operator-side merges (read from GitHub at packet time):** the stack merged
  through **#541** (`main`, merged 2026-11-23T22:41:59Z — the previously
  standing draft flag on the P38.3c PR is discharged); PRs **#540, #542, #543
  open as drafts**, **#544, #545, #546, #547 open** at packet time; merge is the
  operator's, never this row's.
- **Anomalies recorded, not smoothed:** S1-1 (§4); the two vacuous probe
  records; the GAP-RP-1 disposition executed on draft PR #542
  (`D-P38.2-1:e1` OPEN→DONE + the fresh `[[row.legs]]` entries under the
  operator's "Fresh go for the legs" answer, 2026-11-20T00:15Z — **unmerged at
  packet time; the deferral cell still leads OPEN at this tip**);
  `VISUAL-MAP-LIGHT-1`/`DARK-1` and `LH-LCP-MARGINAL-1` stay operator-owned
  allow-list calls (unlisted); `DIGEST-LINT-1` digests stay uncommitted pending
  an owner decision; the intake receiver stays non-operational by design
  (`503 receiver_not_operating`; its dark deploy queued under `D-P37.59-1`).
- **Not presented while a leg is due (OM-19):** no leg is *due* — every owed
  leg is `prepared_not_executed` with its go named; the lapsed Wave-C window
  and the stalled deploy chain are recorded consequences, surfaced, never
  hidden.

## Signature

<!-- Appended only at signing, by the commit that moves Status:. Fields:
     `received` is `date -u` when the operator's words arrived; `<channel>` is
     how (e.g. chat); the GATE DECISIONS row line names the exact LEDGER row —
     its date and gate must resolve to one row and the quote equals its answer.
     Delete the agent-drafted block if none is appended. -->
