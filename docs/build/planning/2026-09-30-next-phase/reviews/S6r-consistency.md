# S6r — fresh-context consistency review of the canonical Round-11 plan

- **Row:** S6r of `META_PLAN.md` §6 (S6 block, `META_PLAN.md:801-806`). **Written:** 2026-10-01T06:47:32Z (`date -u`, same command
  that wrote this stamp) by Claude Code (Opus 5.5) in a fresh context. Adversarial reviewer; did not author the plan.
- **Scope:** read-only. This file is the only output. Nothing committed. No external request, no production
  command. The operator's e-mail address is written nowhere ("the operator's address").
- **Ground truth:** `feedback/RATIFICATION_LOG.md` (rounds 1–25 + closing table). **Under review:** `NEXT_PHASE_PLAN.md`
  (CANONICAL, S6b), `data/round11_plan.csv` (385 rows), `data/ticket_catalog.csv` (329), `data/decision_catalog.csv`
  (350 ids), `design/S6-ratification-applied.md` (incl. S6b addendum). **Also read:** `design/S1c-decision-catalog.md`,
  `META_PLAN.md` §2, §3, §6, §9, §11, the S4 reviews + `REVIEW_CLOSURE.md` (closed items not re-raised), spec MUSTs
  by grep, `docs/build/LEDGER.md:160-173` (GL-GATE-08), `connectors/src/connectors/{net.py,data/sources.toml,flock_portal.py}`,
  `~/agent-skills/skills/build-memory/layout.md`, `research/B6-skill-proposals.md`.
- **Checks run (read-only, `PYTHONDONTWRITEBYTECODE=1`):** `tools/s4c/check_order.py` → errors 0 (309 rows, 285.5 runs,
  legs 28.5, prod/publish 101, OM-20 57, "pauses 33"); `tools/s4c/check_silence.py` → OK; `tools/s4c/check_trace.py` →
  missing []; `tools/check_dispositions.py` → OK (0 errors). Plus scripted cross-checks of the three CSVs (row/kind/run
  totals, empty answers, stale phrases, ADR numbers).
- **Path convention:** paths relative to `PD = docs/build/planning/2026-09-30-next-phase/` unless they start with
  `docs/`, a package name or `~`. `plan:N` = `NEXT_PHASE_PLAN.md` line N; `log:N` = `feedback/RATIFICATION_LOG.md`;
  `spec:N` = `docs/2_canonical_design_spec.md`; `csv:N` = file line of `data/round11_plan.csv`; `dec:N` = file line of
  `data/decision_catalog.csv`.

**Severity scale.** **S0** — executing the plan as written would breach an operator decision or an unwaived safety MUST
irreversibly. **S1** — misstates an operator decision, leaves an unwaived MUST silently in conflict with an answer, or
will make Stage B / GATE-B fail; fix before Stage B. **S2** — inconsistency or gap that would mislead the executor;
cheap to fix, may be carried into the named Stage-B row. **S3** — bookkeeping, labelling, wording.

**Verdict.** The plan is a faithful and unusually careful application of the log: all 350 decision ids carry an answer
(0 blank), `answered_at` uses the log's 24 round stamps, every one of the 27 closing-table deviations and all four
round-24/25 lines are reflected, totals reconcile across §0/§8/§10/§11 and the CSVs, ADR-146…187 are unique and
contiguous, and the DAG/disposition checkers are green. **No S0.** Six S1 findings remain: one more unflagged MUST
conflict of the same class S6 sent to round 24 (SIG-INGEST-035 vs A-17's vendor fetch), one HG-03 flip that rests
on an agent reading rather than the selected option (E4-R4b), the WV-06 deletion path written as an exception to
SIG-STORE-011, crawler-identity prerequisites ordered after the first new-host activations (and the A-17 envelope's
"P16 contact string" dropped), and two Stage-B checklist gaps that would fail GATE-B (the T0/T0b obligations; the
CURRENT STATE key set).

---

## 1. Fidelity (lens 1)

### S6R-01 · S1 · A-17's direct Flock-portal fetch collides with unwaived SIG-INGEST-035 (never flagged, never asked)

- **Evidence.**
  - spec:4199-4202: *"**SIG-INGEST-035 (MUST).** This connector MUST source the portal layer from the aggregator's public
    CC BY-SA 4.0 API (§22.5, SC-18), and MUST NOT attempt direct capture from the vendor, whose every path returns a bot
    challenge (F2.1). Output MUST land in the CC BY-SA 4.0 compartment (SIG-LIC-004a), never merged into the CC-BY graph."*
  - spec:3518: *"SIG-INGEST-013 (MUST NOT). SIG MUST NOT operate a crawler that defeats a bot-management challenge on any source."*
  - csv:89 (row 288, P36.74): *"Flock transparency-portal connector: direct fetch of agency portals on Flock's host (A-17 D3-Q3 b)"*.
  - `connectors/src/connectors/data/sources.toml:322-332` (`[sources.flock_transparency_portals]`): `access_method = "none_lawful"`,
    *"403 on all paths — NO lawful automated access (F2.1). ToS forbids bulk extraction."*; `design/I2-source-search-protocol.md:98-99`:
    *"`flock_transparency_portals` is registry-**refused**"*.
  - "INGEST-035" occurs **0 times** in the plan, the three CSVs, `design/S6-ratification-applied.md` (whose §6 flag list,
    lines 176-209, covers GOV-003, INGEST-036 r6, 046c, PUB-002, GOV-017, INGEST-037 only) and the S1c packet. The packet
    presented D3-Q3's only cost as *"Some Flock/Axon depth stays dark"* (`design/S1c-decision-catalog.md:340-341`); the
    operator chose *"Ratify; fetch vendor pages"* (log:112).
- **Why it matters.** Same class as S6 flags 1–2, which the orchestrator correctly put to the operator (round 24). The
  plan's own rule (plan:1096, *"A spec amendment that removes or weakens a MUST is a waiver"*) means P36.74 cannot be
  built on A-17 alone. Feasibility too: if F2.1 still holds, rule 4 / INGEST-013 make every portal fetch a refusal, so
  §5.5's Flock-depth narrative (plan:760-767) and the Flock acceptance row (plan:814, "portal facts for every reachable
  transparency portal (I3: 917 portals)") rest on an untested assumption.
- **Fix.** Add one line to a round-26 batch: *waive SIG-INGEST-035's "MUST NOT attempt direct capture from the vendor"
  clause for Flock transparency portals (own words → WV-10 / ADR-188), or keep P36.74 dark (aggregator only)*. Either
  way: P36.74's contract starts with a single-request reachability probe from production egress; a challenge/403 is
  recorded as a refusal and the connector lands dark (INGEST-013, rule 4 unwaived); §5.5, §13.2 #2 and the vendor trace
  table condition Flock-portal thresholds on reachability; ADR-184 and §6.3/§6.5 cite INGEST-035; R-18 updated. The
  clause's compartment half binds regardless (S6R-12).

### S6R-02 · S1 · E4-R4b (`camreg_hk_hk`) is recorded as a flip although the operator selected "As listed" (= capture terms, not flipped)

- **Evidence.**
  - log:306: B-41 options *"As listed (Recommended) · As listed, R3 flip · As listed, R3 decline"*; answer *"As listed, R3
    flip"*; the question notes only *"(R3 rec. updated after A-8)"*.
  - `design/S1c-decision-catalog.md:448` (B-41 as listed): *"**R4a–c capture terms, not flipped** (consistent with B-34 and
    US-first; COV-07)"*; `:635` E4-R4b: *"**b** (S4c) — capture the terms; not flipped this round"*.
  - log:311-312 (labelled interpretation): *"R4b a"*; dec:135 E4-R4b `operator_answer`: *"a — flip camreg_hk_hk on the
    non-US basis (non-US kept by S5-4, B-34)"*; plan:454 *"R4b flip"*; plan:1467 *"R4b flip"*. `camreg_hk_hk` is not one of
    B-34's N1–N21 (dec: I7-N1…N21 are Barnet … Braunschweig). The closing deviation table (log:439) lists only R2a/R3.
  - Same drift, smaller: dec:134 E4-R4a *"capture the City of Edmonton terms and flip if they permit"* — the listed text
    was "capture first" and I7-C11 a says *"decide R4a … once the body is captured"* (a later operator line, not a pre-decided flip).
- **Why it matters.** An HG-03 rights flip (operator-only, never pre-authorised) presented as decided at GATE-P; OP-26
  flip lists are "GATE-P-decided rows", so it would reach the operator pre-labelled as already chosen.
- **Fix.** E4-R4b → *b: capture the data.gov.hk T&C; not flipped this round; a new HG-03 line after capture* (like
  IU1–IU5) in plan §4.4, §9.2, dec:135, ADR-169's scope and the T4 DEFERRALS annotation; E4-R4a → *capture, then a new
  operator line*. If the agent believes S5-4/B-34 was meant to reach R4b, ask it in the round-26 batch instead.

### S6R-08 · S2 · A-5 is applied to "new hosts" — wider than the log's labelled reading

- **Evidence.** Adopted option text (log:51): *"Keep disregarding on all 122 hosts incl. PrimeGov; conflicts with
  SIG-INGEST-046c for reservations."* Log interpretation (log:59): *"GL-GATE-08 stands for robots.txt disallows on the 122
  hosts (incl. PrimeGov)"*. Plan:390: *"robots disallows stay disregarded on the 122 hosts incl. PrimeGov **and on new
  hosts**"*; R-21 plan:1918 *"plus new hosts; A-5"*; csv P36.1a/P36.1b gates *"(the 122 hosts incl. PrimeGov, and new
  hosts)"*; D3-Q3/I7-C2/I7-C3 answers *"robots per GL-GATE-08"* for vendor/platform hosts. GL-GATE-08 as recorded
  (`docs/build/LEDGER.md:166-169`): *"operator decision: **disregard robots entirely**"*.
- **Why it matters.** "As is" plausibly carries GL-GATE-08's global scope, but the plan states the wider scope as the
  consequence of the answer while the log (which the plan says wins, plan:9-10) reads it narrower. ADR-168 (T1,
  append-only) will freeze one of the two.
- **Fix.** ADR-168 and §4.2 cite GL-GATE-08's recorded text as the basis for new hosts and label "applies to new
  hosts, incl. vendor/platform hosts" as the agent's reading — or add a yes/no to the round-26 batch. Align the log's
  interpretation and the plan.

### S6R-09 · S2 · A-22's "09-16 review disclosed as delegated" has no owning row

- **Evidence.** log:162-163 *"…after a §43.2a / Part VIII screen; the 09-16 review disclosed as delegated."*; dec:332
  OD-24 *"b — keep the Eyes on Flock mirror live on its CC-BY-SA-4.0 basis, the 09-16 review disclosed as delegated"*.
  "delegated" appears nowhere in the plan; in the CSVs only in unrelated rows (P34.28 lint, SEED-06).
- **Fix.** Add to P36.75 (or P35.35 registry metadata / P36.47 source pages) and ADR-169: the `eyes_on_flock` rights
  record and source page state that the 2026-09-16 review was delegated.

### S6R-21 · S3 · "27 lines differ from the recommendation" mixes three categories

- **Evidence.** log:414-444 has 27 rows, but row 1 is three lines (A-0.1/2/3); C-5 had no recommendation (log:355); the
  last row is five lines that **matched** recommendations updated mid-session; A-8's wording round (log:89, rec *"Keep; NC
  rows facts-only"* → *"Keep everything as is"*) and A-15's second custom answer (log:138) are not separate rows. Plan:11, :479.
- **Fix.** Reword to "27 table rows (≈ 29 lines)"; P38.2 / GATE-ACCEPT-R11 build the accepted-deviations list per line
  from `decision_catalog.csv` (`recommendation` ≠ `operator_answer`), not from the closing table.

### S6R-22 · S3 · Adopted sentences not always labelled as adopted

- **Evidence.** §1.3's own-words list (plan:165-168) omits A-8's acceptance sentence; §4.2 A-8 (plan:393) and §4.5 C-12
  (plan:473) quote the adopted sentences without the *"agent-drafted, adopted by the operator"* label; the log's round-24
  paragraph "On own words by selection" (log:468-471) is agent reasoning, unlabelled. The §0 "Rights and collection
  posture (the operator's choices)" bullet (plan:91-95) puts the agent's engineering envelope under the operator's choices.
- **Fix.** Add the label at each site; label the log paragraph as agent interpretation; say "the agent's envelope" in §0.

## 2. Internal consistency (lens 2)

### S6R-10 · S2 · Stage B's harness is never stated; seed contexts counted as Devin; the OM-01 trailer rule as written conflicts with the seed PR

- **Evidence.** Stage B runs under the planning orchestrator dispatching fresh subagents (`META_PLAN.md:1022-1043`, Claude
  Code). Plan:1645-1651 counts *"Stage-B seed ≈ 30"* inside *"**Devin Desktop total** ≈ 400–480"*. OM-01 (plan:291): *"one
  harness + model per round — Devin Desktop … a G-check fails a Round-11 PR with an untrailered agent commit"*; §13.2 #6
  (plan:1837-1838) *"every agent commit trailered with harness and model (Devin Desktop / `swe-2-high`)"*. The seed PR's
  range `b051732c..r11/seed` contains the 90 planning commits (`git rev-list --count`), trailered only
  `Co-Authored-By: Claude Opus 5.5`; operator commits (OP-25 `allowed_signers`, OP-26 flips, gate records) carry no harness
  trailer by design (A-21). B4's guard range is the PR's base…head (`design/B4-verification.md:212`). The planning round's
  own 24 late stamps (F-074, plan:238-239) sit in that range too.
- **Fix.** State Stage B's harness (Claude Code / Opus 5.5) in §0, §8.7 and the Appendix A header, recorded as a
  harness segment with a switch at GATE-B → row 201 (SK-04). Split §10.4: ≈ 370–450 Devin Desktop + ≈ 30 Claude Code
  (Stage B) + 8–12 Claude Code (REVIEW-R11). SEED-02 defines the trailer grammar: any recognised harness trailer passes
  (incl. the existing `Co-Authored-By: Claude Opus 5.5`), operator commits are identified by the OP-25 signature (or
  `Harness: operator`). Reword §13.2 #6 to "each agent commit names its actual harness and model; chain rows 201–509:
  Devin Desktop / swe-2-high". Confirm `record_policy` keeps G1 off `docs/build/planning/**`, or register F-074's
  stamps in `date_corrections.csv`, so the seed PR's own `docs` job is green (GATE-B needs 5/5).

### S6R-15 · S2 · The 11B re-split rule will very likely fire; GATE-G4b is not budgeted

- **Evidence.** plan:1233-1237: *"11B 82 / 74.0 — still at the edge … If PLAN-11B's sizing review adds splits that push 11B
  over, the rule fires and 11B splits … with an extra GATE-G4b"* (threshold 75 runs). S6 itself flagged four 11B rows for
  splitting (P35.61, P35.63, P36.12, P35.1b; plan:1342-1347; csv notes "S6: looks oversized"). 1.0 run of headroom.
- **Fix.** Either pre-split now and add GATE-G4b to the CSV, §8.3, §8.8 and §11.2 (≈ 1–1.5 h sitting; Wave-B leg timing),
  or ask the operator for a one-line threshold change; at minimum count G4b as a likely touchpoint in §0/§11.2.

### S6R-20 · S2 · P34.45's `live_legs` still encodes A-20 = b

- **Evidence.** csv:57 (row 256) `live_legs`: *"1: ER re-run after P35.57 is live (A-20 b) or after the go"* — while its gate
  says *"A-20 [OD-22] = a … no wait for P35.57"* and it is on the S5-3 pre-authorised list. T3 writes 11A contracts from this CSV.
- **Fix.** *"1: ER re-run on the P34.43 host under the S5-3 pre-authorisation (A-20 = a; basis label + `/status/` notice)"*.

### S6R-23 · S3 · Stale cells and text

- SEED-00 (csv:315) title *"…before GATE-P"*; gate *"Q-H2-2 (rotate the value if it was ever real); Q-B4-5"* — C-9 answered
  "Confirm" (log:368) and `Q-B4-5` is not an id in the decision catalog.
- Appendix A T0 (plan:1988) *"in progress at S6"*; OP-03/OP-04 (csv:359-360) *"early in the round"* — but T0b is done and
  T0c is applying the remaining 12 proposals before Stage B (`META_PLAN.md:1776-1785`). The round-25 dispatch rule relies on
  SK-04 (harness key), which the plan still places in Tier B-should "early in the round".
- P38.2 notes *"(PLAN §4.3)"* → §4.6; P38.3c *"~330 stacked PRs"* vs §12 *"≈ 340"*.
- §9.2 later-phase row *"D-SOURCES.8-2 → LATER-10"* (plan:1466) although LATER-10 is `moved` → P37.70 (B-18).
- dec:35 D-K0-1 answer *"new ADR superseding ADR-068/091/097/134"* vs ADR-155's K0 §6 scope (plan:1162; App B row 27);
  dec:42 Q-16 *"closes the round"* and dec:127 Q-L3-4 *"outside the round"* (S6b open item 4); WV-07's `options` text
  cites *"ADR-167/168/169"* vs §7 ADR-182.
- **Fix.** Update the cells; leave history in `notes` but not in structured columns.

### S6R-24 · S3 · §7 "Also at T1" asks T1 to append status lines for ADRs that tickets write later

- **Evidence.** plan:1197-1200 lists `Qualified by ADR-175` (P34.6), `Extended by ADR-161` (P35.12), `Revisited by ADR-160`
  (P35.17) as T1 work, while plan:1202 says *"Ticket-authored ADRs append their own status lines in the same PR"* and App A
  T1 (plan:2015) excepts only ADR-016/076. App A T1 (plan:2013) supersedes *"118 §2"*, which §7 never names.
- **Fix.** Move those three lines to their owning tickets; reconcile ADR-118 §2 (name the superseding ADR in §7 or drop).

### S6R-25 · S3 · Count and terminology nits

- §8 heading *"4 markers"* (rows 184–187) beside *"Five gate markers"* (plan:1286) — say "4 superseded R10 markers".
- *"19 never-pre-authorised in-ticket pauses"* vs `check_order.py` *"pauses 33"* (it also counts conditional OM-20 cells);
  note the definitional difference in §8.1.
- *"eight synchronous slots"* (plan:105, :1717) but §11.2 marks ten rows "yes" (GATE-ACCEPT-R11, GATE-ANNOUNCE unbolded).
- App A T3 (plan:2053) *"the 59 11A rows and PLAN-11B"* double-counts (PLAN-11B is row 238).
- P38.2's accepted-deviations list names *"the nine waivers (WV-01…WV-09)"* but omits A-6's EVAL-004 waiver (ADR-153).

### S6R-26 · S3 · Baseline drift recorded in META_PLAN not carried into the plan

- **Evidence.** `META_PLAN.md:1758-1760` (05:08:27Z): `origin/main` = `00f67f4b`, #141–#154 merged, 36 PRs open; plan:196,
  :1713, :1776 still say *"49 open PRs #141–#190"* and OP-08 = *"#141–#190"*.
- **Fix.** SEED-01's delta re-run will catch it; restate OP-08's scope (#155–#190) and H1's merge start in §12/§11.2.

## 3. Spec and safety (lens 3)

### S6R-03 · S1 · The WV-06 deletion path is written as an exception to unwaived SIG-STORE-011, and GOV-008's scope clause is dropped

- **Evidence.**
  - spec:2822-2823: *"**SIG-STORE-011 (MUST).** The claim table MUST be append-only, enforced in the database, not by
    convention."* (its trigger raises on `DELETE`). AGENTS.md "Forbidden: … writing `UPDATE`/`DELETE` against the claim spine".
  - spec:6497-6499: *"True deletion MUST be reserved for material SIG must not hold at all, MUST require two-person
    authorization, and MUST leave a tombstone…"*. WV-06 (log:181) waives only the two-person clause.
  - csv:229 (row 428, P37.71) gate: *"…the insert-only claim-spine rule is unchanged **for every other path**"* — reads as
    an exception for this path; its notes reconcile retention and OCFL but say nothing about claim rows.
  - plan:1068 (§6.3 GOV-008) and plan:1109 (§6.5 WV-06) omit the "reserved for material SIG must not hold at all" clause;
    plan:1118-1122 ("Not waived and binding") does not list SIG-STORE-011.
  - The log's own reading is narrower (log:186-188: *"the deletion mechanism itself is a ticketed design (deletion of
    evidence bytes / tombstoning)"*).
- **Fix.** In ADR-181 (T1), §6.3, §6.5 and P37.71's gate: *the deletion path never UPDATEs or DELETEs claim-table rows
  (SIG-STORE-011 stands; its DB trigger unchanged); it removes evidence bytes, restricted objects and derived
  artifacts, and withholds claims through the append-only disposition registry (ADR-124) with a tombstone; true deletion
  is reserved for material SIG must not hold at all (GOV-008 clause stands); the public log records a reason category,
  never content. If the design finds a claim row itself holds such material, the ticket pauses and asks the operator.*
  Add SIG-STORE-011 and GOV-008's scope clause to §6.5's "not waived" list.

### S6R-04 · S1 · Crawler identity and conduct prerequisites land after the first new-host activations; the A-17 envelope lost its "P16 contact string"

- **Evidence.**
  - spec:4472-4475: *"SIG MUST adopt and publish a Crawler Conduct Policy binding on every connector … 1. **Identify.** A
    descriptive UA with a contact URL and an explanation page."*; spec:4491 rule 7 *"Honor opt-out immediately"*.
  - `connectors/src/connectors/net.py:61`: `DEFAULT_CONTACT_URL = "https://sig-project.org/data-collection"` — the domain
    B-6 chose not to buy (log:212, :216); dec Q-E2-03 consequence: *"b: $0, exposure window until the image rebuild"*.
    No crawler-policy or data-collection page exists under `web/src` (`git ls-files` grep: none).
  - Chain order: P35.11 Wave A activation (csv:70, row 269; deps `P35.7…P34.46`, no P35.38, no P36.1a) and P36.12 Wave B
    incl. the Flock-portal family (csv:90, row 289; no P35.38) precede P35.38 *"Identity base + crawler contact truth"*
    (csv:117, row 316; deps only `P34.25`) and P36.1b *"crawler conduct text"* (csv:149, row 348, 11C). Plan:750 says the
    opt-out register and 046c refusal are *"built first (P36.1a)"*, but P36.1a (row 274) follows P35.11.
  - log:128-130 (A-17 envelope): *"public, unauthenticated pages only; no logins, API keys, or circumvention of access
    controls; rate-limited; **P16 contact string**; terms text captured verbatim and the exposure disclosed"*. Plan:753-756,
    ADR-184 (plan:1191), R-18 (plan:1915) and dec D3-Q3 / I7-C2 / I7-C3 replace it with *"robots per GL-GATE-08"*.
- **Why it matters.** Waves A and B — including vendor portals fetched against their terms (R-18) — would name an
  unowned, squattable domain as the contact (F-184, R-29), with no published policy page, so opt-outs (rule 7; WV-09's
  compensating control) cannot reach SIG. The plan drops an element of the log's envelope.
- **Fix.** (1) Restore the envelope element in ADR-184, §5.5, R-18 and the catalog cells: *identify per rule 1 with the
  project UA and an owned contact URL + explanation page on surveillancegraph.org; never the operator's personal
  identifiers (P16); e-mail contact only via `contact@` after OP-10 (C-8)*. (2) Move P35.38 (UA slice at least) to the head
  of 11B and add hard edges P35.38 → P35.11, P36.12, P36.74, P36.76–78, P37.2, P37.54; move P36.1a ahead of P35.11 (or
  add the edge); split a minimal published crawler-conduct/explanation page out of P36.1b ahead of P35.11. Re-run
  `check_order.py`.

### S6R-11 · S2 · SIG-PUB-002 is applied before persistence for Axon Connect but not for DocumentCloud/Sourcewell document bytes

- **Evidence.** spec:6238 *"SIG MUST NOT store, in any tier …"*; spec:6244 *"Home addresses of officers or private individuals
  | **Categorical. No balancing test applies**"*. App B row 28 (plan:2150) adopts the "any tier" reading for P36.76;
  §6.3 (plan:1077) lists only *"(P36.74, P36.76)"*; §10.4 (plan:1635) *"DocumentCloud document bytes in the evidence store"*;
  csv:152 P36.77 *"Part VIII screen on every byte"* without a persistence rule.
- **Fix.** One rule in ADR-185/§6.3 for P36.76–78: redact before persisting (store a redacted rendition + upstream URL +
  sha256 of the original), or record why sealed restricted-tier storage satisfies PUB-002 and apply that reading
  uniformly (P34.49, P36.76). P36.77 should use DocumentCloud's documented unauthenticated API (rule 5, spec:4488).

### S6R-12 · S2 · Licence compartment for share-list claims and vendor-page facts is unspecified

- **Evidence.** spec:4201-4202 (portal-layer output *"never merged into the CC-BY graph"*); spec:6077 LIC-004a (N-compartment);
  spec:6204 LIC-009a (share-alike travels); spec:6214 LIC-010 (build fails on incompatibility). csv:185 P36.75 and csv:249
  P37.25 (state × state Flock-sharing overview) name no compartment; OD-24 keeps the mirror *"on its CC-BY-SA-4.0 basis"*;
  ADR-184 (plan:1191) gives terms-conflicted vendor/platform facts no rights record or compartment.
- **Fix.** P36.75 claims stay in the CC BY-SA portal compartment; P37.25 builds the overview per compartment or publishes it
  in the SA compartment with SA attribution; ADR-184 assigns a rights record/compartment to the terms-conflicted lane, so
  LIC-010's gate does not fail late in 11C/11D.

### S6R-17 · S2 · How the operator "executes" OP-26 flips is undefined

- **Evidence.** csv:384 OP-26 *"executed by the operator per wave (agents prepare each flip list; the operator's verbatim
  line flips)"*; AGENTS.md "Never … flip a source to `ingestion_permitted=true` — operator action"; branch policy
  plan:1758-1764; G4c signing (P34.28, OP-25).
- **Fix.** T5 OPERATING MODE: the agent prepares the patch on `r11/<wave>-flips`; the operator applies it in a commit signed
  with the OP-25 key (or signs a GATE DECISIONS row naming each source id); a CI check fails any `ingestion_permitted`
  false→true transition not covered by an operator-signed record. Keep "≈ 0.25 h per wave" only if it is one signed commit.

### S6R-18 · S2 · Four waiver triggers fire at the announcement, but GATE-ANNOUNCE treats the waivers as covering launch

- **Evidence.** Triggers: WV-01 *"announcement, …"* (plan:1104), WV-04 *"GATE-ANNOUNCE"* (:1107), WV-05 *"announcement; …"*
  (:1108), WV-08 *"the announcement (GATE-ANNOUNCE)"* (:1111); WV-03 is scoped *"for Round-11 releases"* (log:178) and WV-05
  *"for Round 11"* (log:180). §13.5 (plan:1879-1881): *"after the nine waivers … it holds only items owed for other
  reasons"*. DRAFT-ENG-6: *"fired triggers an answer before round close"* (plan:1034).
- **Fix.** The GATE-ANNOUNCE row and §13.5 list WV-01/03/04/05/08 for an explicit keep/lift answer beside Q-29.

### S6R-29 · S3 · B-6's "remove every reference" reaches published identifiers

- **Evidence.** The B-6 question was about the crawler contact URL (dec Q-E2-03); P35.38 also sets *"IRI base =
  surveillancegraph.org"*; `sig-project.org` is the base of ontology and export IRIs (`ontology/generated/pydantic/sig_models.py:74`,
  `exports/src/exports/formats.py:103`, `exports/src/exports/provo.py:33`, `docs/build/tools/build_predicates.py:72`).
- **Fix.** Split P35.38: a small UA/contact slice (moves early, S6R-04) and an IRI-base slice with its own ADR/compat
  note for already-published identifiers (`make gen`, generated-artifact churn).

### S6R-30 · S3 · P34.49 vs the never-list class

- **Evidence.** S5-3 pre-authorises P34.49 *"Part VIII sealing"*; the ratified never-list includes *"any capture run or archive
  write touching a Part VIII-screened family"* (plan:325-326).
- **Fix.** State that P34.49's restricted-tier move is protective (removes from publishable tiers) and outside that class.

## 4. Feasibility for Devin Desktop (lens 4)

### S6R-13 · S2 · The fresh-context isolation check is under-specified and sits on a deadline row

- **Evidence.** plan:1335-1338 and :675-678 (*"a nonce planted only in the orchestrator's context must be invisible to the
  sub-agent, and the sub-agent's run ledger must record its own start"*); `design/S6-ratification-applied.md:297-298` (*"follow
  only the log's example; T3 writes them"*); P34.1 must land before 2026-10-19T00:00Z (plan:81).
- **Gaps.** No positive control (an absent nonce also passes if the probe never ran); no rule that keeps the nonce off disk,
  env, git and Devin's persistent Knowledge/memory; no audit trail of who judged it; no check that the sub-agent ran
  `swe-2-high` (the trailer must name the model actually used); one-shot only; a failure blocks P34.1's acceptance.
- **Fix.** (1) T6 runs a throwaway probe dispatch before row 201; P34.1 repeats it, so the 10-19 deadline never hinges on
  it. (2) Protocol: the orchestrator generates a nonce with `openssl rand -hex 16`, commits only its sha256 in the boundary
  record, never writes it to a file, env var, git or Knowledge, and keeps it out of the dispatch prompt; the prompt carries a
  second, positive-control token the sub-agent must echo; the sub-agent reports its initial context sources, any 32-hex
  token it holds, its own `date -u` start (later than the dispatch record) and its harness/model; pass = token echoed, nonce
  absent, start and model recorded; the nonce is revealed in the record afterwards. (3) Repeat a cheap probe at each
  sub-round GATE and after any orchestrator restart. Label *"a sub-agent cannot compact"* (plan:77, :1329) as inference
  from Claude Code's skill semantics and verify it at T6.

### S6R-14 · S2 · The oversized-row list misses several rows

- **Evidence.** §8.5 (plan:1342-1347) names ten rows + three watches. Not flagged: P38.4 (csv:308; `refresh-repo-docs` *then*
  `agent-docs`, two whole-repo skills in one 1.0-run row); P38.3a/P38.3c (csv:305, :307; reconcile-build over
  `DEFERRALS.md` 339 KB, `BUILD_INDEX.md` 295 KB, `COVERAGE_MATRIX.csv` 202 KB / 716 lines); P34.17 (csv:20; eleven R1
  items, two publish legs, probes); P34.18 (csv:21; re-key across ids, tiles, registry, repo tip + correction note);
  P36.64 (csv:207; K14 81 KB + D3 + copy); P37.66 (csv:295; per-vendor, per-state closeout); PLAN-11C's K13-family
  contexts (csv:140; K0–K14 inputs 37–110 KB each); SEED-14. (Inference — nothing is token-counted yet.)
- **Fix.** Add them to §8.5's watch list and the T3/PLAN Phase-4 token-count review.

### S6R-16 · S2 · Operator load omits recurring copy batches and prices the fallback at zero

- **Evidence.** B-2 (log:199): batches of ~25 confirmed verbatim; N-1…N-7 only until GATE-G4. §11.2 budgets only *"copy
  batch #1"* (plan:1694); 14 CSV rows carry verbatim-confirmation gates (P34.11–P34.17, P34.19, P34.25, P36.45, P36.47,
  P36.49, P36.64, P37.8) plus every new 11C/11D surface. plan:1722-1723: the manual-tier fallback *"would add substantial
  operator time that this total does not include"* (≈ 300 operator-started sessions).
- **Fix.** Add "copy batches #2…#n" per sub-round to §11.2 and §0 (e.g. 4–6 × 0.5–1 h). Give the fallback a number and
  ask at GATE-B whether the third option offered in round 25 (*"Headless Devin command"*, log:477) is pre-approved as the
  second fallback, so a failed isolation check does not default to ≈ 300 manual sessions.

### S6R-27 · S3 · Unverified tooling assumptions

- T3 "token-counts" Load lists with an unspecified tokenizer (swe-2-high's is unknown) — name the counter and keep the
  ≈ 150k target as a proxy with margin. App A T6 (plan:2104-2105) pins `ubuntu-24.04` only *"if row 201 cannot land before
  2026-10-19"*, which is unknowable at T6 — pin unconditionally in the seed PR (P34.1 keeps the rest).

### S6R-28 · S3 · In-round operator decisions not named as touchpoints

- IU1–IU5 (after P36.2's terms capture), E4-R4a and E4-R6a (after capture), and P36.1a's 046c cases each need a new
  operator line; §0 (plan:114-118) and §11.2 should say which GATE packet carries them (GATE-G6 at the latest).

## 5. Stage-B readiness (lens 5)

### S6R-05 · S1 · Appendix A omits the Stage-B obligations recorded at T0/T0b

- **Evidence.** `META_PLAN.md:1767-1770` (T0): the vendored `scripts/docs/check-build-memory.sh` *"needs a three-way sync in the
  seed (else the `harness` key fails its key-order check, READOUT.md's `Status:` comment trips a false "PASSED gate"
  violation, and the guards marker is inert in CI)"*. `META_PLAN.md:1780-1784` (T0b): *"port the GATE DECISIONS `kind`/
  pre-authorization check into the vendored validator; LEDGER seed must write `projectStatus: IN_PROGRESS` (enum); SIG needs
  `docs/build/tools/ci_boundary.py` scoped to Round-11 PRs (B4 G3a) or the red open Round-10 PRs #165/#179/#185 block the
  first boundary; add `docs/build/tools/record_policy/ci_required.txt`; HANDOFF must describe the Devin Desktop manual tier
  (`drive-build.sh --print-prompt` → paste into one new `swe-2-high` session per ticket; `gh` logged in)"*.
  Appendix A: SEED-02 (plan:2021-2023) has only *"`ci_boundary.py` (G3a)"* and *"policies under
  `docs/build/tools/record_policy/`"* — no Round-11 scoping, no `ci_required.txt`, no validator sync, no `kind`/pre-
  authorization port; T6 (plan:2110-2113) has both dispatch modes but not the `gh` precondition. SK-01 reads *"every
  still-open ancestor PR in the stack"* unless a repo hook `docs/build/tools/ci_boundary.*` exists
  (`research/B6-skill-proposals.md:188-191`), so without the scoped hook the first boundary reads #165/#179/#185 and goes
  `blockedOn`, contradicting B-15 (*"pre-#190 reds do not block"*, plan:1781).
- **Fix.** Add to App A: **T2/SEED-02** — three-way sync of the vendored validator (record the upstream skill commit);
  port the GATE DECISIONS `kind` + pre-authorization (`expires:`) check (legacy and restored rows exempt); `ci_boundary.py`
  reads head-bound check-runs of the current `r11/` PR and its `r11/` ancestors only, never #141–#190;
  `record_policy/ci_required.txt` listing the five `ci.yml` jobs. **T5** — record the 11A OM-20 list as GATE DECISIONS rows
  with `kind: pre-authorization` and `expires: GATE-G4`, so SK-03 recognises them. **T6** — HANDOFF's manual tier includes
  `gh auth status` as a precondition.

### S6R-06 · S1 · T5's CURRENT STATE keys violate the layout contract the validator enforces

- **Evidence.** plan:2083-2085: *"`round: 11`, `nextTicket: 201` … `dispatchTarget: subagent` …, `harness: Devin Desktop`,
  `model: swe-2-high` …, status PAUSED until C10"*. `~/agent-skills/skills/build-memory/layout.md:127-151`: *"a fenced
  `key: value` block with **exactly these keys** (`harness` optional, and only in its slot)"*, listing `projectStatus` …
  `harness # OPTIONAL: <harness>/<model-id>/<tier> (BM-HARNESS-01)` — there is no `model` key. SK-04's format:
  `claude-code/claude-opus-5-5/subagent` (`research/B6-skill-proposals.md:383`). Contract header (plan:1360) uses
  *"Devin Desktop / swe-2-high"*.
- **Fix.** T5 writes `projectStatus: PAUSED` (exact enum; → `IN_PROGRESS` at C10), `dispatchTarget: subagent`,
  `harness: devin-desktop/swe-2-high/subagent` in its slot, and no `model:` key; the contract and run-ledger headers use
  the same string. Align §3.3 OM-01, §5.2 (plan:644), §8.5 and App A T3/T5/T6.

### S6R-07 · S2 · The C-10 "never re-stamp L44–52" rule is not on the rows most likely to break it

- **Evidence.** Present in SEED-07 (plan:2033), ADR-146 (plan:1153) and §6.3 (plan:1080). Absent from P34.22a (csv:25,
  *"whole-tree future-date literal test"*), P34.22b (csv:26, *"…regeneration"*), P34.24a (csv:28, *"Sqitch lifecycle
  hygiene"*), P34.24b and P34.46 (csv:58), and from App A T3's contract checklist (plan:2053-2058). L44–52 carry future
  `planned_at` values (2026-10-03…10-19T21:00Z) baked into their change ids (log:381-386), so a whole-tree future-date test
  run before 10-19T21:00Z will flag them.
- **Fix.** Add to those rows' gate/notes and to T3: *C-10 — never edit or re-stamp sqitch.plan L44–52; the future-date
  test allow-lists them by change id (an expiring entry, B4 G1 allow-list) with a pointer to ADR-146.*

### S6R-19 · S2 · REVIEW-R11 S0/S1 fix rows cannot precede GATE-ANNOUNCE as numbered

- **Evidence.** `design/S6-ratification-applied.md:277-280` (S6b open item 2); plan:1867 (*"fixed — by a plan-extension row …
  before GATE-ANNOUNCE"*); GATE-ANNOUNCE is row 509, the last chain row; `check_order.py` rejects a row placed before its dependency.
- **Fix.** Decide at T3, because the manifest is append-only once written: make GATE-ANNOUNCE an operator gate outside the
  201–509 chain (like REVIEW-R11), or record in the manifest's Plan-extensions line that `decompose-spec mode=extend` may
  insert fix rows before it.

---

## 6. Verified consistent (no finding)

- **Answers.** 350/350 decision ids have `operator_answer` (0 blank); `answered_at` uses exactly the log's 24 round stamps
  (03:41:19Z … 06:14:06Z). Spot-checked every A, S5, C and round-24/25 line and the B lines with options (B-6, B-8, B-11,
  B-15, B-18, B-28, B-31…B-44): all match the log apart from S6R-02.
- **Deviations.** All 27 closing-table rows are reflected in §4.2–§4.6 and the CSV gate cells: A-0 (P34.17/18/21b, unresolved
  and operator-deferred), A-1/A-2a (P34.4–P34.6), A-5, A-7, A-8 (ADR-183, P34.19 re-scoped), A-10 (OP-14 dropped), A-15
  (+ round 25), A-17, A-20 (P34.45 to 11A; P35.57 not a gate), A-21, WV-06, S5-3, S5-4 (P37.69a/b), B-6, B-8, B-28 (P36.79),
  B-31 (P35.49 dropped), B-32, B-35 IT7, B-39, B-41 R2a/R3, B-42, B-44 D-K1-7 (P37.72 + GOV-017 analysis), C-4, C-5, plus the
  five updated recommendations.
- **Rounds 24–25.** WV-08 → ADR-186 (GOV-003 clause split), WV-09 → ADR-187 (DocumentCloud/MuckRock only; rules 3/4/7 bind),
  S6-F3 (GATE-ANNOUNCE `depends_on` REVIEW-R11), A15-DISPATCH (`dispatchTarget: subagent`, P34.1 isolation check, HANDOFF
  both modes) are applied in the plan, all three CSVs and §7.
- **Totals.** CSV 385 = 309 chain + 4 markers + 20 seed + 19 operator + 20 later + 1 review + 12 dropped/moved/done;
  per-sub-round rows/runs/legs equal §0 and §8.1 (56.0 / 81.0 / 72.5 / 69.0 / 7.0 = 285.5; PLAN 20.0; legs 28.5); seed
  24.25; later 23.5; OM-20 57 (13 pre-authorised); prod/publish 101; gates at rows 259/342/419/503/509; no chain row
  > 1.0 run outside the fan-outs. Money (§0 = §10.4), operator time (23.5–41 h over 22 touchpoints recomputes from §11.2)
  and contexts (≈ 400–480, modulo S6R-10) agree.
- **ADRs.** 146–187 unique and contiguous; no collision with `docs/adr/` (ADR-001…145); 32 SEED-11 + 10 ticket ADRs; every
  ADR number cited in the plan and the CSVs resolves to its §7 meaning.
- **Waivers.** "Nine" (WV-01…09) is consistent across §0, §4.6, §5.10, §6.5, §11.3, §13.4/§13.5, R-22, App A T4 and
  P38.2's S6b note (but see S6R-25 on ADR-153).
- **Dropped units.** No active row depends on a dropped, moved or done unit (checker); the plan text refers to them only as dropped.
- **Earlier S6 flags.** App B row 28 (IT7 vs PUB-002, resolved toward the MUST) and row 27 (A-12 scope per K0 §6): agreed.
  Own-words-by-selection: acceptable under the operator's S5 format instruction (log:4-6), provided the labels are kept (S6R-22).
- **Safety constants.** No secret in the plan or CSVs; the operator's address appears only where §12 says; HG-03 flips,
  GATE-B and publication are never pre-authorised; OM-20 never-list matches S5-1; alias-first (C-8) gates OP-13 and EDGAR.

---

## 7. Summary

| severity | count | ids |
|---|---:|---|
| S0 | 0 | — |
| S1 | 6 | S6R-01, S6R-02, S6R-03, S6R-04, S6R-05, S6R-06 |
| S2 | 14 | S6R-07, S6R-08, S6R-09, S6R-10, S6R-11, S6R-12, S6R-13, S6R-14, S6R-15, S6R-16, S6R-17, S6R-18, S6R-19, S6R-20 |
| S3 | 10 | S6R-21, S6R-22, S6R-23, S6R-24, S6R-25, S6R-26, S6R-27, S6R-28, S6R-29, S6R-30 |
| **total** | **30** | |

### Must fix before Stage B

1. **S6R-01** — put SIG-INGEST-035 to the operator (round 26: waive the no-direct-capture clause for Flock portals in own
   words, or keep P36.74 dark); add the challenge-as-refusal probe to P36.74.
2. **S6R-02** — correct E4-R4b to "capture terms, not flipped" (and E4-R4a to "capture, then a new line") in the plan,
   `decision_catalog.csv` and the ADR-169/T4 scope — or ask it in the same round-26 batch.
3. **S6R-03** — rewrite the WV-06 deletion-path text (ADR-181, §6.3, §6.5, P37.71): no claim-row UPDATE/DELETE
   (SIG-STORE-011), GOV-008's scope clause stands, reason category only.
4. **S6R-04** — restore "P16 contact string" in the ADR-184 envelope; order P35.38 (UA slice), P36.1a and a minimal
   published crawler-policy page before P35.11/P36.12; add the edges; re-run `check_order.py`.
5. **S6R-05** — add the T0/T0b obligations to Appendix A (validator three-way sync, `kind`/pre-authorization port,
   Round-11-scoped `ci_boundary.py`, `ci_required.txt`, OM-20 rows as `kind: pre-authorization`, `gh` precondition).
6. **S6R-06** — fix T5's CURRENT STATE keys (`projectStatus`; `harness: devin-desktop/swe-2-high/subagent`; no `model:`).
7. **S6R-07** — carry C-10 onto P34.22a/b, P34.24a/b, P34.46 and the T3 checklist.
8. **S6R-08** — make the plan and the log say the same thing about GL-GATE-08 on new hosts (label as reading, or ask).
9. **S6R-10** — state Stage B's harness, split the context totals, and define the trailer grammar and G1 scope so the
   seed PR can be 5/5 green.
10. **S6R-20** — fix P34.45's `live_legs` (T3 writes its 11A contract from it).

### Can carry into Stage B (owner row in brackets)

- S6R-09 A-22 delegated-review disclosure [T1 ADR-169; P36.75 skeleton] · S6R-11 PUB-002 rule for P36.77/78 [T1 ADR-185]
  · S6R-12 compartments for share-list and vendor facts [T1 ADR-184/158] · S6R-13 isolation-probe protocol [T3 P34.1
  contract; T6 dry-run] · S6R-14 extra oversized rows [T3; PLAN Phase-4 reviews] · S6R-15 GATE-G4b budgeting [PLAN-11B;
  §11.2] · S6R-16 copy batches + fallback pricing [T5 digest; GATE-B packet] · S6R-17 OP-26 flip mechanism [T5
  OPERATING MODE; SEED-02] · S6R-18 waiver triggers at GATE-ANNOUNCE [T3 row 509; SEED-15 `ADR_TRIGGERS.csv`] ·
  S6R-19 fix-row placement before GATE-ANNOUNCE [T3 manifest].
- All S3 items (S6R-21…S6R-30) [the Stage-B row that writes the affected record; S6R-26 by SEED-01's delta].
