# Ratification log (S5 / GATE-P)

Collected interactively in the Claude Code planning session at the operator's request (verbatim, 2026-10-01T03:34:09Z):
*"Please interactively raise all the input you need from me so that for each decision, you describe the issue and give your
recommendation and other options, and I will select for each my choice or write in a custom response. Then after that you can
synthesize and proceed as you see fit"*

Each entry records: packet line / decision id, the question as presented (summary), the options offered, and the operator's
answer **verbatim** (selected option label or custom text) with a `date -u` stamp. Agent interpretation, where needed, is
labelled separately. Source of lines: `feedback/RATIFICATION_ANSWERS.md` / `design/S1c-decision-catalog.md`.

## Round 1 — A-0 time-critical removals (answered 2026-10-01T03:41:19Z)

| line | id | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|---|
| A-0.1 | OD-17 | remove 41 e-mail-shaped ArcGIS owner strings + personal handles from non-id text of `camera_registry_targets.toml` at the public repo tip now, via agent PR the operator merges | Yes, now (Recommended) · No, wait for P34.18 | **No, wait for P34.18** |
| A-0.2 | OD-18 | remove anonymous read/list on the 09-27 release tree in sig-public now (live-fetched prefixes excluded after a read-only check; tombstone; reversible) | Yes, now (Recommended) · No, wait for P34.21 | **No, wait for P34.21** |
| A-0.3 | OD-19 | remove `/visual-language/` (fixture facts about OKC PD / Oklahoma County Sheriff / Flock) and pages whose URL/title embeds a personal handle now | Yes, now (Recommended) · No, wait for republish | **No, wait for republish** |
| A-0.4 | OD-20 | git history retains the strings on ~96 remote branches; agents never rewrite history | Accept and disclose (Recommended) · Reserve a later rewrite | **Accept and disclose (Recommended)** |

*Agent interpretation (labelled):* no Track-0 production or repo-tip change is made for OD-17/18/19; each exposure is carried
into Round 11 as an **unresolved, operator-deferred exposure** (not accepted risk) owned by P34.18 / P34.21 / republish #1–#2,
and those tickets must land early in 11A. OD-20: history retained and disclosed in the P34.18 correction note; archive deposits
of history are unblocked once that note lands.

## Round 2 — A-1, A-2, A-3 (answered 2026-10-01T03:53:59Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-1 | Track-0 exception now for QA-9 restore drill + TLS-expiry alert | Drill + TLS alert now (Recommended) · All ten QA items now · None now; ticket it | **None now; ticket it** |
| A-2a | what the $300/mo ceiling covers; budget alert + billing export now | Infra only + alert now (Recommended) · Infra only; alert later · Everything incl. agents | **Infra only; alert later** |
| A-2b | agent-spend envelope | Report + pause on limit (Recommended) · Fixed cap per month | **Report + pause on limit (Recommended)** |
| A-3 | DNS to Cloudflare + R2 $0-egress origin + $50/mo egress kill switch + contact@ alias | Yes, all three (Recommended) · No DNS move · Alias + ceiling only | **Yes, all three (Recommended)** |

*Agent interpretation (labelled):* A-1 → no production change now; QA-9 + TLS alert become early-11A tickets; the first-run
wave (10-01…10-21) proceeds with existing backups/PITR + Track-0.5 alerting; risk recorded **unresolved, operator-deferred**.
A-2 → ceiling = infrastructure only; budget alert + billing export stay ticket P34.5 (early 11A); agent usage reported per
wave in every digest, orchestrator pauses and asks at any usage-limit event (no fixed $ cap). A-3 → P34.50 runbook, then the
operator switches nameservers; R2 origin, egress ceiling + kill switch and contact@ routing are 11A/11B tickets.

## Round 3 — A-4…A-7 (answered 2026-10-01T04:03:25Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-4 | governance stance: disclosed single-maintainer, no-counsel posture (PUB-008 stands; interim editorial authority + public decision log; interim individual legal home; SEC-003 demand posture + counts; counsel records re-labelled as operator determinations; DB-right / ODbL bases as operator determinations with guardrails) | Adopt disclosed posture (Recommended) · Keep spec as is | **Adopt disclosed posture (Recommended)** |
| A-5 | robots rule (GL-GATE-08 re-decided in the operator's words) | Honour vendor/reservations; US gov ok (Recommended) · Obey robots.txt everywhere · Re-confirm GL-GATE-08 as is | **Re-confirm GL-GATE-08 as is** |
| A-6 | evaluation: supersede rows 184–187; auto-merge only C0–C2; waive SIG-EVAL-004 lower bound for C0–C2 | Adopt waiver sentence (Recommended) · No waiver | **Adopt waiver sentence (Recommended)** |
| A-7 | rights rule for Tier-1 flips (GL-GATE-07 re-decided in the operator's words) | Flip only captured terms (Recommended) · Re-confirm GL-GATE-07 · Nothing flips yet | **Re-confirm GL-GATE-07** |

Words adopted by selection (recorded as agent-drafted option text, adopted by the operator):
- A-5: option "Re-confirm GL-GATE-08 as is" — *"Keep disregarding on all 122 hosts incl. PrimeGov; conflicts with SIG-INGEST-046c for reservations. Not recommended."* (the operator chose it over the recommendation).
- A-6 waiver sentence: *"I accept derivation, not identity, and waive SIG-EVAL-004's lower-bound clause for C0–C2 as ADR-L3-B describes."*
- A-7: option "Re-confirm GL-GATE-07" — *"US public records and open-licence sources flip batch-wide under precedent, erring on the side of approving."*

*Agent interpretation (labelled):*
- A-4 → ADRs at Stage B for each member (PUB-008 unamended; interim editorial authority + decision log; interim legal home
  with revisit triggers; SEC-003 posture; counsel records re-recorded as operator determinations; DB-right basis with
  guardrails; ODbL map basis as operator-reported). MUSTs it weakens are decided at A-23.
- A-5 → GL-GATE-08 stands for **robots.txt disallows** on the 122 hosts (incl. PrimeGov), disclosed as host + count in public
  run logs (B-19). It does not by itself waive SIG-INGEST-046c (explicit TDM / rights reservations MUST be honoured as a
  refusal) or the rule-7 opt-out register; those remain built unless waived at A-23. Disallow ≠ reservation: a host that
  publishes an explicit reservation is refused under 046c even though its robots disallow is disregarded.
- A-6 → ADR-L3-B; rows 184–187 superseded; D-R10-HUMAN-1 OPEN non-blocking (trigger T-EVAL-IND); no "human-verified" /
  "certified" / camera-match-precision claims.
- A-7 → GL-GATE-07 re-confirmed: Tier-1 batches RB-01…07 and RB-09 (RG1–5) take I7's option **a**; E4-B1 takes **a**
  (GL-GATE-07 batch-wide for the 23 new US targets); Part-VIII-flagged members still need their S-line (B-32); express
  prohibitions remain A-8/A-9/B-39; RB-06b/RB-08 remain B-33.

## Round 4 — X3, A-8, A-9, A-10 (answered 2026-10-01T04:07:45Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-7/X3 | 46 widening configs inherit their parent source's rights decision (no new HG-03 line) | Confirm (Recommended) · Review each | **Confirm (Recommended)** |
| A-8 | withdraw ≈8,088 public rows (5,267 express-prohibition / NC / ND / "demo" rows + ≈2,821 `camreg_txdot_rep_tx`) | Withdraw all ≈8,088 (Recommended) · Withdraw 5,267; keep TxDOT · Keep all, accept risk | **Keep all, accept risk** |
| A-9 | is SIG's use non-commercial? | May be commercial (Recommended) · Non-commercial | **May be commercial (Recommended)** |
| A-10 | how the 969 review-flagged organisations become publishable | All three (Recommended) · Auto-allow + absence only · Withhold all | **Auto-allow + absence only** |

*Agent interpretation (labelled):* X3 → widening configs enabled under the parent's basis (Part-VIII screen still applies).
A-8 → no withdrawal; an explicit acceptance of express-terms risk is recorded (wording confirmed in round 5 because A-8 and
A-9 overlap on the live non-commercial rows). A-9 → "is or may be commercial": NC sources are facts + pointers only; E4-R4d
(`camreg_bellevue_wa`) declined. A-10 → no operator review queue; an ADR auto-allows organisations matched to the Census
of Governments, a SAM UEI or a Wikidata QID (person-name screen always runs); every other organisation shows a typed
"not yet reviewed" state; the top-50 allow tool is not built for the operator (it may still exist as the ADR's mechanism).

## Round 5 — A-8 wording, A-11, A-12, A-13 (answered 2026-10-01T04:09:43Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-8 (wording) | which acceptance sentence is recorded (overlap with A-9 on 3 live NC rows) | Keep; NC rows facts-only (Recommended) · Keep everything as is | **Keep everything as is** |
| A-11 | "global graph" form | Overviews + egos (Recommended) · Also a full national graph · Egos only | **Overviews + egos (Recommended)** |
| A-12 | JS architecture | HTML-first page types (Recommended) · Keep three islands | **HTML-first page types (Recommended)** |
| A-13 | seed contents | Full seed (Recommended) · Records-only seed | **Full seed (Recommended)** |

Words adopted by selection — A-8 express-terms acceptance (agent-drafted, adopted by the operator): *"I accept the
express-terms risk for all ≈8,088 currently public rows, including the non-commercial ones; A-9 applies to new sources only."*

*Agent interpretation (labelled):* A-8 → no withdrawal; ADR records the acceptance verbatim; the ≈8,088 rows (incl.
`camreg_txdot_rep_tx` and the 3 live NC rows) stay public; A-9's facts-only rule governs **new** NC sources only. E4-R3
(`dot_511_tx`) was declined *because* I7-C1 restricted the first TxDOT republish; with that restriction not adopted, E4-R3 is
re-asked in Part B rather than auto-declined. A-11 → ADR at T1 (aggregated overviews ≤ 3,000 nodes + egos + `/explore/`;
revisit trigger > 3,000 labelled nodes). A-12 → new ADR at T1 superseding ADR-068/091/097/134 + AGENTS.md gotcha 6; K0
budgets; Preact (D-K0-2). A-13 → seed = restore-first + correction ADR + guard core + PKG-02 pins + D-R10-MEMORY-1 split
(B3 option C); rows 201+, phases P34+.

## Round 6 — A-14…A-17 (answered 2026-10-01T04:16:29Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-14 | apply the 25 B6 skill changes to the user-global skills | All, staged (Recommended) · 13 musts only · None; override in-repo | **All, staged (Recommended)** |
| A-15 | execution harness + pause rules | Claude Code, gate pauses (Recommended) · Claude Code, pause each ticket · Devin CLI · Codex or mixed | **custom:** *"We will drive most of the execution with Devin Desktop using their new SWE-2 High model (256k context window)"* |
| A-16 | operator-only signing key for gate commits + forward rule on tentative words | Key + forward rule (Recommended) · Forward rule only · Neither | **Key + forward rule (Recommended)** |
| A-17 | ratify D3 direction | Ratify as drafted (Recommended) · Ratify; fetch vendor pages · Ratify; allow preview share · Exploration before correctness | **Ratify; fetch vendor pages** |

*Agent fact-check (read-only, 2026-10-01T04:16:29Z):* Devin CLI's session store (`~/.local/share/devin/cli/sessions.db`, opened `mode=ro`)
shows Round-10 sessions reading skills from `~/.claude/skills/*/SKILL.md` (symlinks into `~/agent-skills`), e.g. 2,285
references to `implement-spec/SKILL.md`. So the A-14 skill edits reach Devin CLI too. Whether **Devin Desktop** loads the same
path is not yet verified; Stage B's orient dry-run must run in Devin Desktop and confirm it.

*Agent interpretation (labelled):*
- A-15 → executor = Devin Desktop, model `swe-2-high` (256k context), for most of the round; follow-ups in round 7 cover
  pause rules and what "most" leaves to other harnesses. Consequences carried into Stage B: (i) every ticket's Load list +
  expected working set must fit a 256k window with headroom (target ≤ ~150k tokens loaded; oversized tickets split);
  (ii) harness + model recorded per ticket in CURRENT STATE and commit trailers (OM-01), since B7 attributes the
  Round-10 record failures to this same model; (iii) the B4 guard core and B6 Tier A/B-must controls are mechanical
  (CI/hooks), so they bind whatever harness runs.
- A-16 → G4c key: passphrase- or hardware-backed, **never loaded into an ssh-agent that a Devin/Claude session can reach**,
  verified in CI against a committed `allowed_signers`; forward rule adopted (Q-E2-21 yes).
- A-17 → D3 ratified with one edit: D3-Q3 → **b** (fetch vendor-hosted Flock/Axon transparency pages). Engineering envelope
  the agent will apply (not a re-decision): public, unauthenticated pages only; no logins, API keys, or circumvention of
  access controls; rate-limited; P16 contact string; terms text captured verbatim and the exposure disclosed. D3-Q1 yes,
  D3-Q5 a (§5 checklist is the announce gate, no preview), Q-E2-22 a (CHART-025 amended to US-nationwide multi-vendor).

## Round 7 — A-15 follow-ups, A-18 (answered 2026-10-01T04:21:56Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-15 (pauses) | when agents stop and wait | Gate pauses + wave digest (Recommended) · Pause after every ticket · Gate pauses + weekly digest | **Gate pauses + wave digest (Recommended)** |
| A-15 (rest of execution) | what runs outside Devin Desktop | Claude Code audits gates (Recommended) · Claude Code for hard tickets · Devin for everything | **custom:** *"How about Devin for everything and Claude Code can do a deep review after the entire thing, similar to what we did here where Claude Code with high-powered Opus 5.5 xhigh discovered issues from Devin over a many-dozen-ticket build"* |
| A-18 | HG-03 for `census_gazetteer_tiger` + `natural_earth_10m` after terms capture | Yes, flip both (Recommended) · No | **Yes, flip both (Recommended)** |

*Agent interpretation (labelled):* A-15 final → Devin Desktop (`swe-2-high`) executes every Round-11 ticket; pauses only at
HG gates (HG-03 lines, HG-11/Class-S readouts), one ING-GO per acquisition wave, spend above the ceiling, red CI (blockedOn),
and production mutations not on an operator-approved OM-20 list; one digest per wave with a spend line. No in-round
second harness: the mechanical guards (B4 guard core, B6 controls, CI) are the in-round independent check. A **post-round
deep review** by Claude Code (Opus 5.5, xhigh effort), modelled on this Stage-P review, is added as the round's closing
unit (after the final release, before any next-round planning). A-18 → the operator flips both rows (HG-03) once the terms
text is captured; P35.17 stays on the critical path.

## Round 8 — A-19…A-22 (answered 2026-10-01T04:25:48Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-19 | calendar slip trade-off if first dispatch > ≈10-07 | Let waves slip (Recommended) · Protect the end date · Pause and re-plan | **Let waves slip (Recommended)** |
| A-20 | may structural spine writes change live-API answers before a Class-S readout? | No; release-pin API first (Recommended) · Yes, with labels | **Yes, with labels** |
| A-21 | distinct agent author identity for Round-11 commits | Distinct agent author (Recommended) · Keep my name | **Keep my name** |
| A-22 | Eyes on Flock mirror (rec. updated to b after A-17) | Keep + use share lists (Recommended) · Keep, no extension · Suspend pending my review | **Keep + use share lists (Recommended)** |

*Agent interpretation (labelled):* A-19 → OD-21 **a** (cliff table, plan §8.8). A-20 → OD-22 **a**: structural writes may
change live-spine API answers before HG-11, disclosed by every response's basis label + a `/status/` notice; P35.57 is no
longer a precondition for P34.45 / 11B structural writes (it stays in the round as an improvement, not a gate). A-21 →
OD-23 **b**: operator name stays as commit author; disclosed risk; harness/model trailers enforced in CI (OM-01) — required
now that Devin Desktop is the executor. A-22 → OD-24 **b** + D-K2-4 **yes**: share lists become organisation-level
`configured_access` claims after a §43.2a / Part VIII screen; the 09-16 review disclosed as delegated.

## Round 9 — A-23 waivers, S5-1/S5-3, S5-4 (answered 2026-10-01T04:28:49Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-23 part 1 (multi-select: tick = waive) | WV-01 · WV-02 · WV-03 · WV-07 | each with its drafted sentence | **WV-01 legal home (Recommended), WV-02 editorial board (Recommended), WV-03 second reviewer (Recommended), WV-07 counsel clauses (Recommended)** |
| A-23 part 2 (multi-select: tick = waive) | WV-04 · WV-05 · WV-06 | each with its drafted sentence; rec. waive 04+05, keep 06 owed | **WV-04 hostile-reader block (Recommended), WV-05 anonymous intake (Recommended), WV-06 two-person deletion** |
| S5-1 + S5-3 | ratify OM-19 + OM-20; the 11A OM-20 list | Both + list as proposed (Recommended) · Both + list + P34.45 · OM-19 only · Neither | **Both + list + P34.45** |
| S5-4 | US-first (ACQ-23a/b leave the round; Wave C US + territories) | Confirm US-first (Recommended) · Keep non-US acquisition | **Keep non-US acquisition** |

Waiver sentences adopted by selection (agent-drafted, adopted by the operator; one ADR each with compensating controls +
revisit trigger):
- **WV-01** *"I waive SIG-GOV-012/013 for now: SIG's legal home is me as an individual, disclosed on the site, revisited at announcement, a first legal demand, funding, or a second maintainer."*
- **WV-02** *"I waive SIG-GOV-015's editorial board: I hold interim single-maintainer editorial authority, and every naming/sensitivity decision goes in a public decision log."*
- **WV-03** *"I waive the second-reviewer role (SIG-PUB-008 / HG-11) for Round-11 releases; each readout states 'single maintainer, no second reviewer'."*
- **WV-04** *"I waive SIG-UI-042's release block: releases may ship with the hostile-reader review recorded truthfully as 'not yet performed' and any findings listed as known issues."*
- **WV-05** *"I waive one-click, unidentified intake (SIG-GOV-001/002) for Round 11: corrections come by e-mail, and the site says plainly that senders disclose their address."*
- **WV-06** *"I waive two-person authorisation for true deletion (SIG-GOV-008): I alone may authorise a deletion, publicly logged with its reason."* (operator chose this over the recommendation to keep it owed)
- **WV-07** *"I waive the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037; rights decisions rest on my recorded determinations, labelled as such."*

*Agent interpretation (labelled):* all seven waiver candidates are waived → GATE-ANNOUNCE's "spec MUSTs unmet at launch"
list holds only items owed for other reasons (e.g. EVAL-002/005/007). WV-06 → a single-operator true-deletion path exists
(operator-authorised, publicly logged, reason recorded); it is still never pre-authorised under OM-20 and never run by an
agent without the operator's in-ticket go; the claim spine's insert-only rule is unchanged for every other path, and the
deletion mechanism itself is a ticketed design (deletion of evidence bytes / tombstoning) that must keep the audit record.
S5-1 → OM-19 and OM-20 ratified (S4c wording, class-based never-list). S5-3 → the 11A OM-20 list approved verbatim **plus
P34.45's entity-resolution re-run** (consistent with A-20 = a); expiry at GATE-G4. S5-4 → CF-06 **not** confirmed: ACQ-23a/b
stay in Round 11 and Wave C keeps its non-US members; the US-first ordering still holds for priority (Flock/Axon US-nationwide
first, U-007).

## Round 10 — B-1…B-4 (answered 2026-10-01T04:32:16Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-1 | Wave-0 honesty fixes (E2 H-1…H-9, K13 UXW0-1…6, C6 QW-1…15) + fixture/status-word publish guard | Approve all (Recommended) · Removals only | **Approve all (Recommended)** |
| B-2 | copy approvals: batches of ~25 confirmed verbatim; N-1…N-7 by sha256 until GATE-G4 | Batches + notice allowance (Recommended) · Batches, no allowance · Agents publish; I review after | **Batches + notice allowance (Recommended)** |
| B-3 | re-key handle-bearing source ids; neutral "identifier changed" page; map restricted | Re-key, map restricted (Recommended) · Re-key with public redirects | **Re-key, map restricted (Recommended)** |
| B-4 | record integrity (supersede p-17b713 + GATE-G3; annotate ACCEPT-R8/R10 + GATE-G3 with B7 facts; no past-state addendum; appended date corrections; go-live spec amended) | As stated (Recommended) · Annotate only | **As stated (Recommended)** |

*Agent interpretation (labelled):* B-1 includes the A-0 items (`/visual-language/`, handle-bearing pages/ids) as Wave-0
tickets. B-2 → OD-07 a. B-3 → DR-C6-01 a. B-4 → Q-12, Q-E2-18/19/20, Q-B1-2 as stated.

## Round 11 — BT batch, B-15, B-6, B-7 (answered 2026-10-01T04:33:54Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-5, B-17, B-22, B-23, B-26 (BT) | verdict vocabulary; nextTicket + HG-05 disposition; 52 K-row design recs; Natural Earth non-US names; dedup as announce criterion ("records" until then) | Accept all five (Recommended) · Accept, with exceptions | **Accept all five (Recommended)** |
| B-15 | GitHub settings S-1…S-5 (operator); pre-#190 reds don't block; `r11/` prefix; one flake re-run per head | As stated (Recommended) · Skip the settings | **As stated (Recommended)** |
| B-6 | residual E2 lines incl. registering sig-project.org + moving the UA; SWH after history scan | As stated (Recommended) · Move UA, don't buy domain · As stated, no SWH deposit | **Move UA, don't buy domain** |
| B-7 | Round-10 surfaces order; no API hotfix unless step 1 slips past ~10-21 | As stated (Recommended) · Hotfix API now-ish | **As stated (Recommended)** |

*Agent interpretation (labelled):* B-6 → UA moves to surveillancegraph.org; `sig-project.org` not purchased (residual
squatting risk recorded; every remaining reference to it is removed from code and docs); Q-E2-01 now reads with WV-04
waived; Q-E2-02 follows A-5 (GL-GATE-08 as is); Q-E2-12 a, Q-E2-16 yes, Q-E2-23 a (scan then SWH deposit; A-0.4 disclosed).

## Round 12 — B-8…B-11 (answered 2026-10-01T04:35:53Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-8 | intake e-mail-only until after announcement; published response times | Email + these times (Recommended) · Email, no time promises · Email + looser times | **Email, no time promises** |
| B-9 | G3 release model + Class R standing go (operator's words) | Adopt + standing go (Recommended) · Adopt; every release Class S | **Adopt + standing go (Recommended)** |
| B-10 | releases from unmerged stack commits; operator tags v0.1.0 after the #190 sitting; legacy buckets retired | Yes (Recommended) · No tags; keep buckets | **Yes (Recommended)** |
| B-11 | Cloud SQL cap 40 GB, pre-grow 25 GB, temporary tier bump for OSM; OSM monthly; 4 wave ING-GOs; targets under flipped sources = configuration; core + Wave D | As stated (Recommended) · Lower cap (25 GB) · No cap | **As stated (Recommended)** |

Class R standing go adopted by selection (agent-drafted, adopted by the operator): *"Agents may promote a Class R release
built from the same signed code whose diff stays within bounds (records −2%…+15%, no compartment <−5% or >+50%, no source
loses >20%), with all checks green and no waivers; this go expires at the next sub-round gate or after 30 days, and is void
on any ratchet regression, Part VIII screen change or new source."*

*Agent interpretation (labelled):* B-8 → Q-27/OD-08/D-K11-4: e-mail-only intake (operator address until the contact@ alias
exists), `/intake/` "not operating", **no response-time commitment published**; task pages name the same address. B-9 →
D-G3-1/2/3/4/8/9/10 yes; the standing go needs renewal at each sub-round GATE (it is never answered by `continue`). B-10 →
D-G3-5/6/7 yes. B-11 → Q-23 + I8-Q2…Q5 as stated (Wave D in scope per A-19).

## Round 13 — B-12/13/14, B-16, B-18, B-19 (answered 2026-10-01T04:39:45Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-12/13/14 | $0 paid data; scheduler consolidation (−$7/mo), keep LB + min-instances 1, CUD after 3 bills; evidence retention ≥365 d unlocked | Accept all three (Recommended) · Accept, with exceptions | **Accept all three (Recommended)** |
| B-16 | planning branch local until T6 + scans; private off-disk backup; OD-27 | Local + backup; push at T6 (Recommended) · Local; push redacted at T6 · Push now | **Local + backup; push at T6 (Recommended)** |
| B-18 | US 511 keys + QLD/NSW keys (rec. updated after S5-4); fold D-P30.2b-1 and D-P32.3-1 | US + AU keys, fold rest (Recommended) · US keys only · No keys | **US + AU keys, fold rest (Recommended)** |
| B-19 | transparency package (raw-ok bytes after Part VIII screen; scrubbed run logs; snapshots; JSON-LD; prior releases as manifests; 6-h status lane; review packets) | Yes, as stated (Recommended) · Also keep prior release bytes · Nothing new published | **Yes, as stated (Recommended)** |

*Agent interpretation (labelled):* B-16 → Q-H2-6 a + c; OD-27 **a** (publish as recorded at T6, after the secret / personal-
identifier / Part VIII scans); the agent creates a git bundle for the operator to store privately. B-18 → D-SOURCES.7-2 a,
D-SOURCES.8-2 **a** (changed from the packet's b because S5-4 kept non-US acquisition); keys entered by the operator into
Secret Manager (HG-09), never in files. B-19 → D-J3-1/2/3/6/7/10/11/13 + Q-J4-7 yes.

## Round 14 — B-20, B-21, B-27, B-28 (answered 2026-10-01T04:41:11Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-20 | release-manifest signing | Pipeline key + your gate key (Recommended) · My key on every manifest · sha256 only | **Pipeline key + your gate key (Recommended)** |
| B-21 | Zenodo DOIs (irreversible) | Yes, as stated (Recommended) · No DOIs this round | **Yes, as stated (Recommended)** |
| B-27 | neutral "Other public resources" block + official agenda portal links | Yes (Recommended) · Official portals only | **Yes (Recommended)** |
| B-28 | who writes the ≥40-query held-out search set | I write it (Recommended) · Separate agent, labelled | **Separate agent, labelled** |

*Agent interpretation (labelled):* B-20 → D-J3-8 a. B-21 → D-J3-9 yes (operator-run, open compartments only, after the
attribution fix). B-27 → D3-Q4 yes, D-K7-3 as recommended. B-28 → D-K3-7 **b**: a separate agent context writes the set,
labelled *"agent-authored held-out set; not independent"*; it is written before, and never visible to, the contexts that
tune search.

## Round 15 — B-29…B-32 (answered 2026-10-01T04:43:37Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-29 | operator "beautiful" gallery sign-off before announcing; spec published per release | Both (Recommended) · Gallery only · Spec page only | **Both (Recommended)** |
| B-30 | sig-api 512 MiB → 1 GiB (+$3/mo); search rate limit 30/min | Yes (Recommended) · No | **Yes (Recommended)** |
| B-31 | per-Class-S maintainer check; no in-round second model family; public `/quality/`; C2 enabled | As stated (Recommended) · No maintainer check · C0/C1 only | **No maintainer check** |
| B-32 | Part VIII screens S1–S9: screened lanes; S5 names suppressed; S8 tribal metadata-only | Screened lanes; S8 metadata (Recommended) · All metadata-only · Include S8 screened lane | **Include S8 screened lane** |

*Agent interpretation (labelled):* B-29 → D-K14-9 yes, D-K14-8 yes. B-30 → D-K3-5/6 yes. B-31 → Q-L3-3 **c** (no
operator maintainer check; every Class-S readout and `/quality/` say "no human check performed"), Q-L3-4 no in-round
second family (post-round Claude Code deep review per A-15), Q-L3-5 yes, Q-L3-6 a (C2 enabled). Knock-ons: Q-25's
"maintainer-check seat" is vacated; D-P30.2b-1 (curation), which B-18 folded into the maintainer check, has no fold target —
it stays OPEN, non-blocking, trigger T-EVAL-IND (same as D-R10-HUMAN-1). B-32 → I7-S1…S9 **a, including S8**: the two tribal
members ingest their Part VIII-screened lane without a tribal-data-governance rule (the screen itself still applies; no
outside contact). B-37 is re-asked for consistency.

## Round 16 — B-33…B-37 (answered 2026-10-01T04:46:04Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-33 | RB-06b share-alike compartment; RB-08 US territories (rec. updated to "territories = US" after A-7) | SA compartment; territories=US (Recommended) · SA compartment; capture terms · Neither flips | **SA compartment; territories=US (Recommended)** |
| B-34 | N1–N21 non-US database-right lines (rec. updated to flip after S5-4) | Flip under precedent (Recommended) · Capture terms, then decide · Not flipped this round | **Flip under precedent (Recommended)** |
| B-35 | IT1–IT7 restricted terms; IT7 Axon Fusus Connect pages under A-17 | IT7 program facts only (Recommended) · IT7 facts-only pointer · IT7 full fetch | **IT7 full fetch** |
| B-36 + B-37 | IU1–IU5 capture terms then decide; TR1–TR2 (rec. updated to facts + citations after B-32) | Capture IU; TR facts+cite (Recommended) · Capture IU; defer TR · IU facts+cite now; TR facts+cite | **Capture IU; TR facts+cite (Recommended)** |

*Agent interpretation (labelled):* B-33 → I7-RB-06b a, I7-RB-08 **a**. B-34 → I7-N1…N21 **a** (non-US DB-right basis per
the live precedents; express prohibitions excluded); this un-gates R11-ACQ-23a/b (S5-4). B-35 → IT1 b, IT2/3/5/6 b (A-9),
IT4 c, **IT7 a**: Axon Fusus "Connect <Place>" pages fetched in full under A-17, every byte through the Part VIII screen
before storage or publication — private registrants (resident/business names, addresses, contact data, camera
locations at private residences) are never stored in public output and never published (Part VIII + SIG-PUB-002 are not
waived). B-36 → I7-IU1…5 a. B-37 → I7-TR1/2 **c** (facts + citations under the S8 screen).

## Round 17 — B-38…B-41, B-43 (answered 2026-10-01T04:49:27Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-38 | SEC EDGAR P1–P4: facts-only basis; ingestion later-phase; alias first | As stated (Recommended) · Ingest this round · Decline | **As stated (Recommended)** |
| B-39 | terms conflicts C2/C3/C4/C5/C7/C8/C9/C11 (C4 updated per A-17) | As stated (Recommended) · Also fetch DocCloud/Sourcewell | **Also fetch DocCloud/Sourcewell** |
| B-40 + B-43 | confirmations X1/X2/X4; E4 S1–S5 + F1 D-P21.3-2 status corrections | Confirm all (Recommended) · Confirm, with exceptions | **Confirm all (Recommended)** |
| B-41 | E4 rights rows R1…R6b (R3 rec. updated after A-8) | As listed (Recommended) · As listed, R3 flip · As listed, R3 decline | **As listed, R3 flip** |

*Agent interpretation (labelled):* B-38 → I7-P1…P4 a. B-39 → C2 and C3 take the "fetch despite terms" reading: DocumentCloud /
MuckRock and Sourcewell / OMNIA are fetched like A-17's vendor pages (public, unauthenticated pages only; no logins or
access-control circumvention; rate-limited; robots per GL-GATE-08; Part VIII screen on every byte); C4 per A-17; C5 b; C7 a;
C8 b (CourtListener bulk deferred); C9 a; C11 a. B-41 → R1 a, R2b a (decline), **R3 a (flip `dot_511_tx` under GL-GATE-07)**,
R4a decided on OGL-Edmonton (C11), R4b a, R4c b (QLDTraffic API), R4d c (A-9), R5 a, R6a a, R6b a. **Conflict:** B-41's "as
listed" includes R2a = decline DocumentCloud, while B-39 says fetch it — re-asked in round 18.

## Round 18 — R2a conflict, B-42, B-44 (answered 2026-10-01T04:51:39Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| B-41 R2a vs B-39 | DocumentCloud: fetch (B-39) or decline (B-41 as listed)? | Fetch, screened (Recommended) · Link-only after all | **Fetch, screened (Recommended)** |
| B-42 | Round-10 dossier families: Part VIII screen + operator "clear"; SRC-027 metadata-only; one bounded retry | As stated (Recommended) · Agent clears, disclosed | **Agent clears, disclosed** |
| B-44 part 1 (tick = approve) | "My location" button · agenda titles if screened · short excerpts if permitted | rec: tick 2nd + 3rd only | **'My location' map button, Agenda titles if screened (Recommended), Short excerpts if permitted (Recommended)** |
| B-44 part 2 (tick = approve) | run-record artifacts shown · single-source sites shown · county + place pages | rec: tick all three | **Show run-record artifacts (Recommended), Single-source sites shown (Recommended), County + place pages (Recommended)** |

*Agent interpretation (labelled):* R2a → E4-R2a **b** (flip `documentcloud`: public documents only, Part VIII screen on every
byte, link to the uploader's page). B-42 → E4-B2: Part VIII screen per family, **no operator "clear"**; readouts state
"cleared by agent screen, no human review"; B3 a; B4 a. B-44 → D-K7-6, D-K8-1, D-K8-4, D-K1-6, D-K4-3 as recommended;
**D-K1-7 "My location" approved** (operator chose it over the recommendation). SIG-GOV-017 (MUST NOT build an "is a camera
watching me right now" surface) is not waived by this answer, so the ticket builds the button as a **map-pan control only**
(browser-only geolocation after a click, never sent to SIG, no "cameras near you" list, count, alert or proximity
notification) and starts with a written SIG-GOV-017 analysis; if that analysis finds the button cannot comply, the
ticket pauses and returns the question (waive GOV-017 for it, or drop it) to the operator.

## Round 19 — S5-2, C-1, C-2, C-3 (answered 2026-10-01T04:54:19Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| S5-2 | check-in GATE packet; `continue` answers only batch lines | Ratify (Recommended) · Ratify; 'continue' = all recs | **Ratify (Recommended)** |
| C-1 | readout provenance (GATE-G3 03:49:14Z, ACCEPT-R10 18:46:46Z; readouts composed 32 s / 51 s after; nothing on 2026-10-19) | Confirm (Recommended) · Don't recall; record B7's evidence · Dispute | **Confirm (Recommended)** |
| C-2 | harness attribution; was "Pause after P31.5" a planned hand-over? | Confirm; planned hand-over · Confirm; not planned · Confirm; don't remember | **Confirm; planned hand-over** |
| C-3 | own words: (1) counsel determinations were the operator's; (2) the 09-28 deferral of human legs | Adopt both sentences (Recommended) · Adopt (1) only · Neither | **Adopt both sentences (Recommended)** |

C-3 sentence adopted by selection (agent-drafted, adopted by the operator at 2026-10-01T04:54:19Z): *"The 'counsel' determinations of
2026-09-16 and 09-24 were my own; there was no counsel. My 09-28 message 'let's defer all the human review steps and
proceed' was my decision to defer the human review legs."* — recorded with today's date, never as a 09-16/24/28 statement.

*Agent interpretation (labelled):* OD-10 confirmed; OD-11 confirmed, intent = planned hand-over to Devin CLI at P31.5→P31.6;
OD-12 items (1) and (2) recorded as above, item (3) = A-5.

## Round 20 — C-4…C-7 (answered 2026-10-01T04:56:11Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| C-4 | home tagline (rest of K14 §2.1 copy goes to copy batch #1) | …place by place (Recommended) · …traced to the documents · Who watches… — sourced | **…traced to the documents** |
| C-5 | About "who runs SIG" | 'A single independent maintainer' · My name · Omit until I write it | **Omit until I write it** |
| C-6 | repo stays public | Stays public (Recommended) · Make it private | **Stays public (Recommended)** |
| C-7 | last GCP invoice amount | Don't know; keep estimate · I'll check and tell you | **Don't know; keep estimate** |

*Agent interpretation (labelled):* C-4 → D-K14-1 tagline = *"Public surveillance, traced to the documents."*; the sub-head,
About paragraph, why-it-exists line and four "is not" lines go to copy batch #1 for verbatim confirmation (B-2). C-5 →
D-K14-7: the "who runs SIG" section is omitted (no placeholder about the operator ships) until the operator writes it.
C-6 → OD-13 stays public. C-7 → OD-14: ≈$90–100/mo kept, labelled inference, until P34.5's billing export measures it.

## Round 21 — C-8…C-11 (answered 2026-10-01T04:59:05Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| C-8 | contact-string requests wait for the contact@ alias | Alias first (Recommended) · Use my gmail now | **Alias first (Recommended)** |
| C-9 | no `SIG_INTAKE_*_SECRET` value from the notes was used in any deployed/staging config | Confirm · Not sure; check it | **Confirm** |
| C-10 | inspect the stopped local container `sig-p332-db` for sqitch L44–52 | Let me inspect it (Recommended) · Leave as unknown | **Let me inspect it (Recommended)** |
| C-11 | confirm the labelled interpretations under U-002…U-015 | Confirm all (Recommended) · Confirm, with exceptions | **Confirm all (Recommended)** |

*Agent interpretation (labelled):* C-8 → OD-15 alias first: no request needing a contact string (EDGAR, 511 / QLD / NSW key
sign-ups) is sent until contact@surveillancegraph.org exists (P16 "stop and record"). C-9 → Q-H2-2 resolved by the
operator. C-11 → OD-16 confirmed.

### C-10 inspection result (operator-approved, local only, 2026-10-01T04:59:41Z)

- Container `sig-p332-db` (`postgis/postgis:18-3.6`, created 2026-09-28T05:41:12Z, last stopped 2026-09-30T20:49:54Z,
  state before inspection: Exited (255)). Started locally, queried read-only (`sqitch.changes`), stopped again (state after:
  Exited (0)). No production contact; nothing written.
- Its registry holds **48 changes, deployed 2026-09-28T05:42:14Z…05:42:33Z**, including all nine plan lines **L44–52**
  (`claim_assertion_bindings` … `recovery_apply`) with the plan's future-dated `planned_at` values (2026-10-03…10-19T21:00Z,
  one 09-27T14:00Z) baked into their change ids (e.g. `recovery_apply` = `d39b1f96…`).
- **Answer to C-10 / Q-B1-4: yes.** At least one persistent local database holds L44–52 as stamped. It is a disposable P33.2
  test container, not an authority, but re-stamping L44–52 in the plan would change their change ids and orphan it (and any
  similar DB). This confirms B1's "do not edit L44–52" rule: the date correction stays an appended amendment (B-4). The
  `.codex/worktrees` checkouts hold no Postgres data directory.

## Round 22–23 — C-12, C-13, D2-01…D2-16 (answered 2026-10-01T05:03:05Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| C-12 | accept the withdraw-instead-of-fix list (one-click dispute, `/intake/`, `/contribution-back/`, `/curate/`, `/task/new/` demos, research-queue "send") | Accept the list (Recommended) · Make some work | **Accept the list (Recommended)** |
| C-13 | does ACCEPT-R10's "34 MET" still stand? (dated today) | Superseded (Recommended) · Still stands · Withdrawn | **Superseded (Recommended)** |
| D2-01…04 (tick = agree at shown priority) | S0 findings | — | **01 (P1), 02 (P1), 03 (P1), 04 (P1)** — all ticked |
| D2-05…08 | S1 findings | — | **05 (P1), 06 (P2), 07 (P1), 08 (P1)** — all ticked |
| D2-09…12 | S1 findings | — | **09 (P2), 10 (P2), 11 (P1), 12 (P1)** — all ticked |
| D2-13…16 | S1 findings | — | **13 (P1), 14 (P2), 15 (P2), 16 (P1)** — all ticked |

C-12 sentence adopted by selection: *"I accept that these features are withdrawn or labelled this round rather than made to
work."* C-13 recorded at 2026-10-01T05:03:05Z: ACCEPT-R10 stands as history, **superseded** by the Round-11 re-verdicts (B-5); never recorded
as a 09-27/28 statement.

---

## Closing — S5 complete; GATE-P

All 99 packet lines (A-0…A-23, S5-1…S5-4, B-1…B-44 less the moved B-24/B-25, C-1…C-13, D2-01…D2-16) have an operator answer,
collected interactively in 23 rounds, 2026-10-01T05:03:05Z. The operator's standing instruction for what follows (verbatim, msg of
2026-09-30): *"Then after that you can synthesize and proceed as you see fit"* — recorded as the **GATE-P go**: the agent
synthesizes these answers into NEXT_PHASE_PLAN.md (canonical) and proceeds to Stage B (T0–T6) without a further plan
sign-off; Stage B's own human items (HG lines, operator-only actions) still pause.

### Where the operator chose differently from the recommendation (27 lines; each changes the plan)

| line | recommendation | operator's choice | plan consequence |
|---|---|---|---|
| A-0.1/2/3 | remove now (Track 0) | wait for P34.18 / P34.21 / republish | early-11A tickets; exposure "unresolved, operator-deferred" |
| A-1 | restore drill + TLS alert now | none now; ticket | QA-9 + TLS alert are 11A tickets |
| A-2a | budget alert now | later (P34.5) | P34.5 early in 11A |
| A-5 | narrow robots | GL-GATE-08 as is | 122 hosts' disallows disregarded; 046c reservations still honoured unless waived |
| A-7 | flip only captured terms | GL-GATE-07 re-confirmed | Tier-1 batches flip batch-wide (Part VIII S-lines still apply) |
| A-8 | withdraw ≈8,088 rows | keep all, accept risk | no withdrawal; acceptance ADR |
| A-10 | top-50 review + auto-allow + absence | auto-allow + absence only | no operator review queue |
| A-15 | Claude Code; gate audits | Devin Desktop (swe-2-high, 256k) for everything; post-round Claude Code deep review | 256k ticket sizing; post-round review unit |
| A-17 (D3-Q3) | never fetch vendor hosts | fetch vendor pages | vendor-page connectors (public pages only) |
| A-20 | release-pin API first | structural writes may change live API, labelled | P35.57 not a gate |
| A-21 | distinct agent author | keep operator name | trailers enforced in CI |
| A-23 WV-06 | keep owed | waived | single-operator deletion path, logged |
| S5-3 | list as proposed | + P34.45 ER re-run | on the 11A OM-20 list |
| S5-4 | US-first | keep non-US acquisition | ACQ-23a/b back in the round |
| B-6 | buy sig-project.org | move UA, don't buy | residual squatting risk recorded |
| B-8 | publish response times | no time promises | none published |
| B-28 | operator writes query set | separate agent, labelled | agent-authored set |
| B-31 | per-release maintainer check | none | readouts say "no human check" |
| B-32 | S8 metadata-only | S8 screened lane included | tribal sources screened + ingested |
| B-35 IT7 | program facts only | full fetch (Part VIII-screened) | Axon Connect connector |
| B-39 | link-only DocCloud / pointers Sourcewell | fetch despite terms | three more connectors |
| B-41 R2a/R3 | decline / TxDOT-owned layer | fetch DocCloud / flip dot_511_tx | two more flips |
| B-42 | operator clears families | agent clears, disclosed | no operator clear |
| B-44 D-K1-7 | no "My location" button | approved | GOV-017 analysis + map-pan-only build |
| C-4 | "…place by place." | "Public surveillance, traced to the documents." | tagline |
| C-5 | (choice) | omit until written | no "who runs SIG" section |
| B-18 / B-33 / B-34 / B-36-37 / A-22 | recs updated mid-session after A-7/A-17/B-32/S5-4 answers | updated recs accepted | AU keys; territories = US; N1–N21 flip; TR facts+cite; share lists used |


## Round 24 — follow-ups from S6 (answered 2026-10-01T06:05:22Z)

S6 (`design/S6-ratification-applied.md`) found two answers that conflict with spec MUSTs not covered by a waiver, and one open
gating question.

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| S6-F1 | SIG-GOV-003 (published SLAs by category, privacy/safety first) vs B-8 (no time promises) | Priority order, no times (Recommended) · Keep owed · Publish SLAs after all | **Priority order, no times (Recommended)** |
| S6-F2 | SIG-INGEST-036 rule 6 ("ask first" for small civil-society projects) vs B-39/R2a (fetch DocumentCloud/MuckRock) + no outside contact | Waive rule 6 for these (Recommended) · Link-only after all | **Waive rule 6 for these (Recommended)** |
| S6-F3 | does the post-round Claude Code review (REVIEW-R11) gate the announcement? | S0/S1 must be dispositioned (Recommended) · Advisory only | **S0/S1 must be dispositioned (Recommended)** |

Sentences adopted by selection (agent-drafted, adopted by the operator):
- **S6-F1 (WV-08):** *"I waive GOV-003's response-time SLAs; SIG publishes its handling priority without time commitments."*
- **S6-F2 (WV-09):** *"I waive crawler rule 6 (ask first) for DocumentCloud/MuckRock; SIG fetches public pages only, gently, and honours any opt-out immediately."*

*Agent interpretation (labelled):* S6-F1 → new waiver WV-08: the corrections page publishes the handling order
(privacy-harm and safety first, then factual corrections, then other) with no time commitment; GOV-003's priority clause is
MET-DIFFERENTLY, its SLA clause WAIVED(ADR). S6-F2 → new waiver WV-09 scoped to DocumentCloud/MuckRock only (P36.77 may
activate after its HG-03 flip); rules 3, 4 and 7 still bind. S6-F3 → REVIEW-R11's S0/S1 findings must each be fixed or
dispositioned by the operator before GATE-ANNOUNCE; S2/S3 findings feed the next round.

**On "own words by selection" (S6 flag 7).** The operator set this format at S5 (*"I will select for each my choice or write
in a custom response"*), and every own-words line offered a custom-text option. Selecting a drafted sentence is therefore
recorded as the operator adopting it as their words; the log labels each as "agent-drafted, adopted by the operator". The
plan/packet sha256 values S6 computed afterwards are labelled as computed after the fact.

## Round 25 — Devin Desktop dispatch mode (answered 2026-10-01T06:14:06Z)

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| A-15 (dispatch) | how Devin Desktop runs tickets in fresh contexts | Orchestrator + sub-agents (Recommended) · Manual tier, one session per ticket · Headless Devin command | **Orchestrator + sub-agents (Recommended)** |

*Agent interpretation (labelled):* LEDGER `dispatchTarget: subagent`; one Devin Desktop orchestrator session (`swe-2-high`)
runs orchestrate-build and dispatches each ticket to a fresh sub-agent; CI is read at every boundary (SK-01); harness + model
recorded per ticket (SK-04/SK-10). The **first Round-11 ticket carries an acceptance check that the sub-agent context is
fresh** (e.g. the sub-agent cannot see a nonce planted only in the orchestrator's context, and its run ledger records its own
start), because B7 could not verify Round 10's per-ticket isolation; if the check fails, the orchestrator pauses and the
operator falls back to the manual tier (`drive-build.sh --print-prompt`). HANDOFF documents both.

## Round 26 — follow-ups from S6r (answered 2026-10-01T06:51:11Z)

S6r (`reviews/S6r-consistency.md`) raised three items that need the operator (S6R-01, S6R-03, S6R-08).

| line | question (summary) | options offered | operator answer (verbatim) |
|---|---|---|---|
| S6R-01 (A-17) | SIG-INGEST-035 forbids direct capture from Flock (every portal path returns a bot challenge); rule 4 (no circumvention) unwaived | Keep Flock via aggregator (Recommended) · Waive 035; probe without circumventing | **Waive 035; probe without circumventing** |
| S6R-03 (WV-06) | deletion vs SIG-GOV-008 scope + SIG-STORE-011 append-only claim table | Narrow purge exception (Recommended) · No spine deletion | **Narrow purge exception (Recommended)** |
| S6R-08 (A-5) | does GL-GATE-08 "as is" cover new hosts? | All hosts, as ADR-088 (Recommended) · Only the 122 hosts | **All hosts, as ADR-088 (Recommended)** |

Sentences adopted by selection (agent-drafted, adopted by the operator):
- **WV-10 (S6R-01):** *"I waive INGEST-035's no-direct-capture clause; SIG may fetch Flock portal pages only when served without a challenge, and stops on any challenge."*
- **WV-11 (S6R-03):** *"I approve one operator-only purge function as the sole exception to SIG-STORE-011, limited to material SIG must not hold (GOV-008), leaving a tombstone and a public log entry."*

*Agent interpretation (labelled):* S6R-01 → P36.74 becomes a **probe-only** connector: it requests Flock portal pages
gently; any bot challenge / 403 / interstitial ends the attempt and is recorded (no challenge-solving, header spoofing,
proxy rotation or browser automation to defeat bot management — rule 4 and INGEST-037's anti-circumvention posture stand);
expected yield today ≈ 0; the Eyes on Flock aggregator remains the Flock portal source; output lands in the CC BY-SA
compartment (SIG-LIC-004a stands). S6R-03 → P37.71 implements a single DB-enforced, operator-only purge function as the
sole exception to SIG-STORE-011; scope limited to GOV-008 "material SIG must not hold at all"; tombstone (category + date,
never content) + public log; never on an OM-20 list; each use needs the operator's in-ticket go. S6R-08 → GL-GATE-08 applies
to every host per ADR-088 (disallows recorded as `robots_disregarded`, disclosed as host + count); 046c reservations and
rule-7 opt-outs honoured everywhere.

### Record clarification (S6R-02): B-41 as presented

S6R-02 read E4-R4b's flip as an agent interpretation. The B-41 question the operator answered listed the rows explicitly;
its text as presented (2026-10-01, round 17) was: *"B-41. Pending source rights rows, updated for your answers. R1 Belgian
eID leg: close (WONTFIX). R2a DocumentCloud / R2b CourtListener RECAP: decline. R3 dot_511_tx (a second TxDOT republish):
since you kept the first (A-8), I recommend finding a TxDOT-owned layer first rather than a second republish. R4a Edmonton on
OGL-Edmonton; R4b Hong Kong flip; R4c QLDC via the QLDTraffic API (CC-BY, now that you'll register AU keys). R4d Bellevue:
decline (non-commercial, A-9). R5 Chicago procurement portal: flip. R6a BidNet: capture terms first; R6b Periscope:
superseded."* The operator chose **"As listed, R3 flip"**, so R4b = flip and R4a = decided on the OGL-Edmonton basis are the
operator's answers as presented (R2a later changed to fetch in round 18).
