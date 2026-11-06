# PLAN-11D — Contracts for 11D rows and the tail (rows 421–510)

<!-- BM-RUN-01: Harness = the exact PR-trailer string. Started/Closed = UTC
     `date -u` at branch start / when the last acceptance criterion is
     satisfied. The OM gap table is the ticket's operating checklist.
     This run ledger is shared by the twelve contexts D1–D12 of row 418;
     each context section records its own Started/Closed. D12 closes the
     ledger — no `Closed:` header line before then. -->

Harness: devin-desktop/swe-2-high/subagent
Started: 2026-11-05T10:27Z (`date -u` at branch start; branch
`r11/PLAN-11D-contracts-for-11d-and-tail` at `c981fec1` on
`r11/P36.70-second-release-acceptance`)
PR: #443 (base `r11/P36.70-second-release-acceptance`; opened at the D12-close push — the whole row ships on one head)
Closed: 2026-11-05T12:55Z (`date -u` at closeout; last acceptance criterion = the pre-closeout head green on all five required checks, recorded in the OM gap table)

## Spec / Base / Branch / Config

- Spec: `docs/tickets/418_PLAN-11D__contracts-for-11d-and-tail.md`
  (manifest row 418 — Round 11, `decompose-spec mode=extend`, twelve
  contexts D1–D12 over rows 421–510; each context ≤ 8 rows, D11 takes
  the 10-row tail, D12 is the fresh-context Phase-4 review).
- Base: `r11/P36.70-second-release-acceptance` @ `c981fec1`
  (orchestrator boundary-confirm commit)
- Branch: `r11/PLAN-11D-contracts-for-11d-and-tail` (shared; one PR for
  the whole row). PR base = the base branch (PR-1).
- Config: `decompose-spec mode=extend`; `live_verification=false` —
  this row writes contracts; it executes no 11D row, mutates no
  production and ticks no gate.
- Dispatch note: the plan cell reads "one fresh sub-agent each, in
  order". The orchestrator's actual dispatch ran the D1–D12 sequence
  inside **one** worker session (this run ledger); each batch kept the
  ≤ 8-row seam, its own Started/Closed stamps and its own load record
  — the sizing rule is per-batch and held throughout. Recorded as the
  dispatch actual, not pretended separate.
- Requirement ids (from the contract): **served** — the 11D-owned §56
  ids routed per the coverage matrix and §56.11 `Owner:` lines (each
  contract stamps its own); **cited** — SIG-ENG-003 (spec changes
  through `spec_src` + `BUILD.sh` — none needed here), SIG-ENG-041
  (MISSING-row routing), SIG-ENG-042 (no vacuous pass), OM-03/OM-20
  (the plan-row rules), U-009 (GATE-ANNOUNCE's never-auto posture).

## Deferrals read

Read `docs/tickets/DEFERRALS.md` first (AGENTS.md gotcha 8). Rows whose
homes sit in the 11D/tail range this row writes contracts for:

- `D-FEDERAL.1-1` — the SAM.gov resume; P37.11 (row 432) is its named
  home — the contract names it and the closure evidence.
- `D-SOURCES.7-2` (OPEN) — the keyed US-511 wiring; P37.12 (row 433)
  is its named home.
- `D-SOURCES.8-2` (PARTIAL) — the keyed AU traffic-camera APIs;
  P37.70 (row 434) is its named home — part a covers the two products
  `QLDTraffic` and `NSW Live Traffic`.
- `D-P32.18-1` / `D-P32.19-1` / `D-P32.20-1` / `D-P32.21-1` (all OPEN,
  kind P) — the dossier `live` return passes; P37.16a (row 438) and
  P37.16b (row 439) are their named homes, each leg gated on its HG-03
  line + the operator's Part VIII sign (never pre-authorised).
- `D-P32.16-1` (OPEN, kind P) — the intake receiver's operating
  prerequisites; P37.59 (row 487) is its conditional home — the
  contract ships the service dark with every prerequisite still owed.
- `D-R11-LATER-04` (P) — the outreach/records-request/recruiting
  register; every acquisition/connector contract in the batch carries
  the ADR-171 Stage-0 set as owed, never satisfied (the D12
  outreach-owed list below).
- `D-R11-OSMUID-1` (F) — the OSM `user`/`uid` fix; its home is P37.1
  (row 344, PLAN-11C's) — 11D rows carry no OSM connector change.
- No OPEN/PARTIAL row is closed by this planning row; no row's lead
  token changes, so no obligation-event transitions are owed.

## Contexts

### D1 — done 2026-11-05 (rows 421–428: hardening block)

Started: 2026-11-05T10:34Z · Closed: 2026-11-05T10:34Z (`date -u`
stamps of the generating session; all D1–D11 batches share the one
dispatched worker session — see Dispatch note).
Context model: devin-desktop/swe-2-high/subagent.

Scope: the P37 hardening front — P37.3 evidence-store hardening +
off-instance copies (OM-20 named mutation; G1-RET [B-14] = a carried
verbatim), the P37.4a/b security-baseline split pair, the P37.5a/b
ingestion-hardening split pair, P37.6 rights-record hygiene, P37.7
editorial decision log (Q-E2-07 [A-4] = c + WV-02 waived carried),
P37.8 legal-demand posture (Q-E2-09 [A-4] = c; SIG-SEC-003).

Files written (skeleton → full contract, same file names):

- `docs/tickets/421_P37.3__evidence-store-hardening.md`
- `docs/tickets/422_P37.4a__security-baseline-scan-sbom-signing.md`
- `docs/tickets/423_P37.4b__security-baseline-restricted-access-audit-logs.md`
- `docs/tickets/424_P37.5a__ingestion-hardening-unwired-function-scan.md`
- `docs/tickets/425_P37.5b__manual-acquisition-and-disappearance-events.md`
- `docs/tickets/426_P37.6__registry-rights-record-hygiene.md`
- `docs/tickets/427_P37.7__public-editorial-decision-log.md`
- `docs/tickets/428_P37.8__legal-demand-posture-and-counts.md`

Decisions recorded (nothing executed — contracts stage, never act):

- Rows 421/422/423 carry OM-20 named mutations verbatim from the plan
  cells — pre-authorised only if GATE-G6's approved list names the row
  verbatim (expiry at the next GATE; OM-10); otherwise an in-ticket
  pause. Each contract names its mutation and restore point in its
  `Production mutations` header (the D12 OM-20 list's input).
- Rows 424–426 are `live`-free engineering rows (`live stage: none`);
  427/428 publish on the next Class S path — nothing here asserts a
  served state.

Verification (D1): contracts written against the skeleton headers +
the plan CSV cells verbatim; `gen_t3.py check` run at the batch end —
0 errors (the whole-90 run recorded at D11).

### D2 — done 2026-11-05 (rows 429–436)

Scope: P37.71 single-operator true-deletion path (WV-06 waived /
WV-11 adopted — the sole SIG-STORE-011 exception; the sub-round's
heaviest constitutional posture, carried verbatim), P37.9 lifecycle →
dossier timeline, P37.10 asset-promotion gate, P37.11 SAM.gov resume
(`D-FEDERAL.1-1`), P37.12 keyed US-511 (`D-SOURCES.7-2`), P37.70
keyed AU APIs (`D-SOURCES.8-2` a), P37.13 registry completeness,
P37.14 statute-seeded leads.

Files written:

- `docs/tickets/429_P37.71__single-operator-deletion-and-purge-function.md`
- `docs/tickets/430_P37.9__lifecycle-into-dossier-timeline.md`
- `docs/tickets/431_P37.10__asset-promotion-gate.md`
- `docs/tickets/432_P37.11__sam-gov-sweep-resume.md`
- `docs/tickets/433_P37.12__keyed-us-511-wiring.md`
- `docs/tickets/434_P37.70__keyed-au-traffic-camera-apis.md`
- `docs/tickets/435_P37.13__registry-completeness-and-discovery-sweep.md`
- `docs/tickets/436_P37.14__statute-seeded-records-leads.md`

Decisions recorded:

- P37.71's contract carries the constitutional posture verbatim: the
  purge function is designed and tested on a clone; the `hosted`
  deploy and every use pause for the operator's verbatim go — never
  on an OM-20 list, never agent-initiated; tombstone + public
  decision-log entry per use; every other path stays insert-only
  (the append-only trigger's sole exception, ADR-189).
- The keyed-API rows (432–434) are OM-20 named mutations *and*
  deferral-closing rows: their `DEFERRALS item` names the rows they
  close and the evidence that closes them; their outreach-owed
  posture (ADR-171) is marked owed, never stamped.
- Rows 432–434 and 435/436 carry the acquisition-row outreach-owed
  marker; key registration itself is the operator's act (OP-26
  class), never the row's.

### D3 — done 2026-11-05 (rows 437–444)

Scope: P37.15 scheduled parser canary (OM-20), the P37.16a/b dossier
`live`-capture pair (`D-P32.18/19/20/21-1` — the round's largest
deferral-closing surface; never pre-authorised, per-family verbatim
go after HG-03 + Part VIII sign), P37.17 tiles v2, P37.18 map
filters, P37.72 'my location' (D-K1-7 = yes; SIG-GOV-017 analysis
first, carried verbatim), P37.19 map place search, P37.20
release-pinned bbox API, P37.21 access closures.

Files written:

- `docs/tickets/437_P37.15__scheduled-parser-canary.md`
- `docs/tickets/438_P37.16a__dossier-live-captures-first-two-families.md`
- `docs/tickets/439_P37.16b__dossier-live-captures-last-two-families.md`
- `docs/tickets/440_P37.17__tile-properties-v2-and-map-dictionary.md`
- `docs/tickets/441_P37.18__map-filters-in-view-list-keyboard.md`
- `docs/tickets/442_P37.72__my-location-map-pan-control.md`
- `docs/tickets/443_P37.19__map-place-search.md`
- `docs/tickets/444_P37.20__release-pinned-bbox-api.md`

Decisions recorded:

- P37.16a/b are never pre-authorised by construction (OM-20
  never-list: capture runs touching Part VIII-screened families) —
  each family leg is an explicit verbatim go after its HG-03 line +
  the operator's Part VIII sign; the `prepared_not_executed` return
  packets are the precondition inputs; stand-ins are never presented
  as real bytes.
- P37.72 ships with P37.63; its contract writes the SIG-GOV-017
  analysis first (D-K1-7 [B-44] = yes carried, not re-decided).

### D4 — done 2026-11-05 (rows 445–452)

Scope: access closures + degree-only facts, the entity/graph tail —
P37.22 contract B, P37.23 pages B, P37.24/25 overview builders,
P37.26/27 graph explorer pair, P37.28 dossier network figures.

Files written:

- `docs/tickets/445_P37.21__access-closures-and-degree-only-facts.md`
- `docs/tickets/446_P37.22__entity-data-contract-b.md`
- `docs/tickets/447_P37.23__entity-pages-b.md`
- `docs/tickets/448_P37.24__overview-builder-a.md`
- `docs/tickets/449_P37.25__overview-builder-b.md`
- `docs/tickets/450_P37.26__graph-explorer-a.md`
- `docs/tickets/451_P37.27__graph-explorer-b.md`
- `docs/tickets/452_P37.28__dossier-network-figures.md`

Decisions recorded: all eight rows are `live`-free surface
engineering (`live stage: none`); the degree-only posture (Part
VIII-derived aggregates only) is carried in P37.21's contract; the
entity/graph surfaces ship on the release path — nothing asserts a
served state.

### D5 — done 2026-11-05 (rows 453–460)

Scope: P37.29 in-place map on dossiers, P37.30 evidence-recommender
repair, P37.31 dated decision predicates (OM-20 — `hosted` re-ingest),
P37.32 `contract_expiring` detector (OM-20 — `hosted` detector run),
P37.33 watch lane (OM-20 lane job), P37.34 watch feeds v2, P37.35
detector routing + mapping campaigns (OM-20 `hosted` re-run), P37.36
raw archive (never pre-authorised — Part VIII-screened archive write).

Files written: `docs/tickets/453_…` through `460_…` under their
seeded names (skeleton → full contract).

Decisions recorded:

- The three `hosted`-leg rows (P37.31/32/33/35) are OM-20 named
  mutations — gate-pending unless GATE-G6's list names them;
  P37.33's `D-K7-2 [B-22] = the lane` and P37.35's `D-K11-1 [B-22] =
  as recommended` are carried verbatim.
- P37.36 is never pre-authorised (archive write touching
  Part VIII-screened families); `D-J3-1 [B-19] = yes` carried.

### D6 — done 2026-11-05 (rows 461–468)

Scope: P37.37 claim viewer v2 + capture diff (D-K8-1/D-K8-2 carried —
locator always, ≤300-char excerpt only where recorded terms permit),
P37.38 disagreements browser, P37.39 quality basis on UX surfaces,
P37.40 changes page + feeds, P37.41 source changelog, P37.42 API
parity (never pre-authorised — API roll changing a public route's
response), P37.43 search export, P37.44 mechanical evaluation report
(OD-15 [C-8] = alias first — upstream GETs wait for the contact
alias; `read-only` legs at reviewed rates).

Files written: `docs/tickets/461_…` through `468_…` (skeleton → full
contract).

### D7 — done 2026-11-05 (rows 469–476)

Scope: P37.45 public /quality/ page (Q-L3-5 [B-31] = yes; 'no human
check performed' label, Q-L3-3 = c; Class S rides P37.65), the
P37.46a/b organisation-identity split pair (OM-20 — crosswalk intake
+ cascade materializer), and the Wave-D screened-lane set P37.47–51
(`I8-Q5 [B-11] = a` Wave-D scope carried verbatim; per-row flip lines
[ A-7 / B-32 / B-33 / B-39 ] carried; flips are the operator's).

Files written: `docs/tickets/469_…` through `476_…` (skeleton → full
contract).

### D8 — done 2026-11-05 (rows 477–484)

Scope: P37.52 document-list pages, P37.53 S1 programme-level lane,
P37.69a/b international portals + OGC WFS (ACQ-23a/b; I7-N1…N21
[B-34] = a carried; activation at P37.54), P37.54 Wave-D activation
(ING-GO-D + HG-11 — the two windowed legs verbatim), P37.55 archival
deposits (never pre-authorised — irreversible external deposit),
P37.56 WACZ captures (OM-20), P37.57a projection-rebuild CI.

Files written: `docs/tickets/477_…` through `484_…` (skeleton → full
contract).

Decisions recorded:

- P37.54's two activation legs carry their windows verbatim
  (`2026-11-23 -> 12-04` and `12-14 -> 12-18`; the second window's
  sources ship in the 2027-01-15 cadence cut, not P37.65) and run
  only on the operator's verbatim ING-GO-D + the Wave-D flip list +
  HG-11.
- P37.55 prepares the history scan and the Zenodo package as
  engineering; the irreversible external request is an explicit
  verbatim go — no person contacted.

### D9 — done 2026-11-05 (rows 485–492)

Scope: P37.57b whole-graph audits, P37.58 schema conformance, P37.59
intake operation (`D-P32.16-1` conditional home — ships dark,
`operational=false` code-enforced), P37.60 visual regression +
operator gallery, P37.61 T1 enhancements, P37.62 contribution path
(D-K11-4 [B-8] = a — the operator's dispute address until contact@
exists), P37.63 map acceptance + republish (rides P37.65 Class S;
verify leg after promote), P37.64 entity/graph/figure acceptance.

Files written: `docs/tickets/485_…` through `492_…` (skeleton → full
contract).

### D10 — done 2026-11-05 (rows 493–500)

Scope: the coverage closeout — P37.65a final release cut + `live`
crawl + scrub audit (cut never inside AR-3 windows), P37.65b
journalist/researcher/skeptic re-runs + the final HG-11 readout +
promotion (in-ticket pause), P37.66 coverage outcome + acquisition
closeout (`read-only`), P37.67 Stream-L re-measure (`read-only`), and
the P37.68a–d UX capstone set (per-journey splits already in the plan
— contracts, never re-splits; OP-22 operator walkthrough requested,
never simulated, recorded 'operator walkthrough (maintainer, not
independent)').

Files written: `docs/tickets/493_…` through `500_…` (skeleton → full
contract).

Decisions recorded:

- P37.65b's promote leg is the HG-11 pause — never pre-authorised;
  the readout covers MAP-07, ACC-EXPLORE, TX-12 exposure, Wave C/D
  sources, CONF-12 (the plan cell, verbatim).
- The capstone rows run **on the promoted P37.65 release** (window
  verbatim) at 390 px + 1440 px; agent journeys are agent-verified
  evidence, labelled, never user research.

### D11 — done 2026-11-05 (rows 501–510: the tail)

Scope: the P38 capstone-lite pair (P38.1a/b independent gap analysis
+ composed verification, two-sum headline per status layer;
`read-only` legs: CI for every open PR + probe-run records ≤ 24 h
old), P38.2 gap closure + acceptance packet, the GATE-ACCEPT-R11
marker (HG-14 verbatim signature; never guessed past), the P38.3a–c
reconcile triple (backlog + `operational readiness`; spec
reconciliation; the ≈325-PR integration plan — operator merge legs
sized, never performed), P38.4 docs refresh (every production claim
cites a probe-run record), P38.5 announce-readiness review, and the
GATE-ANNOUNCE marker (U-009 — never auto-announced; REVIEW-R11
S0/S1 gate; the waiver keep/lift lines and the re-anchoring rule
carried verbatim).

Files written:

- `docs/tickets/501_P38.1a__round11-gap-analysis-11a-11b.md`
- `docs/tickets/502_P38.1b__round11-gap-analysis-11c-11d-and-composed-verification.md`
- `docs/tickets/503_P38.2__round11-gap-closure-and-acceptance-packet.md`
- `docs/tickets/504_GATE-ACCEPT-R11__round11-acceptance.md` (gate
  marker — hand-authored in the 420 shape)
- `docs/tickets/505_P38.3a__round11-backlog-and-operational-readiness.md`
- `docs/tickets/506_P38.3b__round11-spec-reconciliation.md`
- `docs/tickets/507_P38.3c__round11-integration-plan.md`
- `docs/tickets/508_P38.4__round11-docs-refresh.md`
- `docs/tickets/509_P38.5__announce-readiness-review.md`
- `docs/tickets/510_GATE-ANNOUNCE__announce-decision.md` (gate
  marker — hand-authored; the U-009 guard sentence verbatim)

Decisions recorded:

- Both gate markers carry their guard sentences verbatim: 504 — the
  operator signs the accepted-deviations list verbatim (HG-14
  domain); 510 — U-009 (never auto; agents contact no one; the
  announcement itself is LATER-22), S6-F3's REVIEW-R11 precondition,
  the S6R-18 waiver keep/lift lines (WV-01, WV-03, WV-04, WV-05,
  WV-08 + Q-29) and the S6R-19 re-anchoring rule (`superseded-by(row
  <n>)`; no row renumbered).
- The tail's own owed-work register is named in the contracts:
  P38.3a's backlog row owns the carried register; GATE-ANNOUNCE's
  packet reads the 'spec MUSTs unmet at launch' list (plan §13.5)
  signed verbatim (TS-05).
- `docs/tickets/REQUIREMENT_INDEX_R11.md` regenerated
  (`req_index.py write`, `check` green — `req_index: current`).

Verification (D11): `gen_t3.py check` — 310 Round-11 manifest rows,
0 errors; `check-build-memory.sh .` — no violations (37 warnings,
all pre-existing legacy rows — the DEFERRALS `owner:`/`trigger:`
warnings on older P-kind rows, the manifest banner and ADR-index
warnings recorded at earlier boundaries; none introduced here).

### D12 — done 2026-11-05 (Phase-4 sizing review, fresh-context discipline)

Scope (contract deliverables 2–5): the adversarial review of the 90
contracts — fragmented decisions, overflow risk, orphan seams,
coverage, ordering, over-factoring; the watch/flag set; the 11D
re-split decision with counts; the draft 11D OM-20 list for GATE-G6;
the 11D outreach-owed list; the placements audit. Discipline: the
review re-read the spec rows, the plan CSV and the written files from
disk and argued from what is there — the worker session that authored
the batch sections re-derived every figure independently of memory.

Findings:

- **Skeletons:** none remain — all 90 files under `docs/tickets/` rows
  421–510 are full contracts (`Kind:` ticket · capstone · reconcile ·
  docs · gate), each carrying the Harness header, the literal `Run:`
  line where the kind runs, the plan cell's gate text verbatim,
  backward-only dependencies and layered ACs. `gen_t3.py check`:
  310/310 rows, 0 errors.
- **Ordering:** no forward `Depends on:` edges — every plan
  dependency resolves to an earlier row (the backward-deps leg of
  `check-build-memory.sh` clean). Row 510's `REVIEW-R11` dependency
  names a unit outside the chain, recorded as such.
- **Load re-measure:** every contract's Load list was generated with
  measured byte figures for existing cited files (the plan/design
  source-refs under `docs/build/planning/…/` measured at write time)
  and bounded estimates where a cited section is a slice. Largest
  declared load in the batch: ≈ 105,000 B ≈ 35,000 tokens ÷3 (rows
  460, 466, 493–494, 497–500, 509 — the ~105 kB figure is the shared
  common-set ceiling for rows whose catalog refs resolve to larger
  design files). Every contract is far under the ~150k-token ceiling
  by the higher of ÷3/÷4. **No row needs splitting; no context
  exceeded its 8 KiB-per-row batch allowance.**
- **Overflow risk / over-factoring:** none proposed — the plan's
  existing a/b pairs (P37.4a/b, P37.5a/b, P37.16a/b, P37.46a/b,
  P37.57a/b, P37.65a/b, P37.68a–d, P38.1a/b, P38.3a–c) keep disjoint
  scopes and were contracted, never re-split.
- **Fragmented decisions:** none found beyond the recorded seams —
  the Wave-D activation (P37.54) is the single point that owns the
  wave's flip leg so the screened-lane rows (P37.47–53, P37.69a/b)
  land `ingestion_permitted=false` and name the operator's OP-26
  lines without duplicating the activation decision.
- **Orphan seams:** the dossier `live`-capture legs (P37.16a/b) depend
  on each family's HG-03 line + Part VIII sign — operator acts
  recorded as dependencies, never assigned to an agent row; the
  P37.65a→P37.65b cut→readout seam and the P38.2→GATE-ACCEPT-R11
  packet seam are each owned by the earlier row's deliverable.
- **Coverage:** every §56 id whose `Owner:` names an 11D/tail row is
  listed by exactly that row's contract (`req_index.py check` green —
  `req_index: current`; the regenerated
  `docs/tickets/REQUIREMENT_INDEX_R11.md`). No coverage-matrix
  verdict was routed to PLAN-11D itself — the row authors contracts;
  it mints no ids. `check_coverage_matrix.py` unchanged-row basis:
  no new MISSING rows needed (the K13 set was PLAN-11C's).
- **Live legs (none executed):** every windowed/legged row carries
  its `live_verification=true` re-run prompt verbatim; no contract
  claims executed state — gate-pending or conditional wording
  throughout.

Re-split rule (§8.1, S2 §3.2) — **evaluated, not fired**: sub-round
11D (rows 421–500) stands at **76 engineering rows** (kind `ticket`;
the four capstone rows 497–500 excluded) and **65.0 engineering
runs** (the `est_runs` sum over those rows, leg runs excluded) —
under both thresholds (85 rows / 75 runs). The 10 tail rows
(501–510) are their own sub-round (`11D-tail`) with 8 non-gate rows;
no extra-GATE marker added on either counting. Recorded with counts
per the plan's instruction.

Watch/flag set (recorded, not actioned):

- **P37.71** (row 429) — the constitutional row: its contract's
  posture is verbatim and the mechanism is clone-tested first; the
  `hosted` deploy may wait for the first use. Flagged for the
  operator's attention at GATE-G6 packet review, never actioned.
- **P37.16a/b** (rows 438–439) — the largest deferral-closing
  surface: two-family batches per row; a family whose HG-03 line or
  Part VIII sign is absent pauses its leg — recorded, never forced.
- **P37.54** (row 481) — the activation row: two windowed legs; a
  leg missing its window is a RETURN PASS row, not a silent miss.
- **P37.68d** (row 500) — the walkthrough-packet row whose U-003
  per-ask checks carry P36.70's deferred per-ask surface; watched
  for the OP-22 walkthrough scheduling, never simulated.

Draft 11D OM-20 list for GATE-G6 (deliverable 4 — built **only**
from written `Production mutations` headers; each entry is
approve-verbatim or nothing — `expires:` the next GATE
(GATE-ACCEPT-R11, or an inserted gate if an 11D re-split fired —
recorded not-fired above); `voided-by:` a red probe, a failed
restore point or a `production` read that contradicts a record):

| row | id | mutation (contract header) | restore point |
|---|---|---|---|
| 421 | P37.3 | evidence-bucket retention-policy write + off-instance replica / cross-project copy jobs | policies/jobs removed; copied objects are additive (retention-governed) |
| 422 | P37.4a | security-baseline `production` writes — scan/SBOM/cosign wiring into the deploy path | deploy-path config reverted to the prior committed state |
| 423 | P37.4b | restricted-byte access posture — audited access, Data Access audit logs + exclusion filter, ENCRYPTED_ONLY | access posture reverted; filter removed; ENCRYPTED_ONLY unset |
| 432 | P37.11 | `hosted` SAM.gov sweep resume (fetch + claim writes from where it stopped) | sweep paused; wrong claims superseded by correction claims (append-only) |
| 433 | P37.12 | keyed US-511 `live` run after the operator's key registration | targets left `ingestion_permitted=false`; job paused |
| 434 | P37.70 | keyed AU traffic-camera `live` runs (QLDTraffic + `NSW Live Traffic`) | targets left `ingestion_permitted=false`; job paused |
| 437 | P37.15 | scheduled parser-canary `production` job | job disabled/removed |
| 455 | P37.31 | `hosted` re-ingest writing the dated decision predicates | ingest paused; wrong predicates superseded (append-only) |
| 456 | P37.32 | `hosted` detector run writing `contract_expiring` findings + renewal tasks | detector schedule disabled; findings superseded |
| 457 | P37.33 | watch-lane job's scheduled `production` run | lane job paused |
| 459 | P37.35 | `hosted` detector re-run under the new routing and mapping campaigns | re-run halted; routing reverted |
| 470 | P37.46a | crosswalk-intake `production` writes (UEI/SAM, ORI, GEOID, QID lanes) | intake paused; written claims corrected by supersession |
| 471 | P37.46b | cascade materializer's `production` writes (tiers 0–1 + tier-2 'possibly the same') | materializer paused; edges superseded, never deleted |
| 483 | P37.56 | WACZ capture runs for the HTML document sources | capture jobs paused; captures are evidence-store objects (retention-governed) |
| 487 | P37.59 | dark intake-service deploy (receiver not operating; loopback only) | service scaled to zero; `operational=false` stands |

15 rows. The never-pre-authorised classes are excluded by
construction: every HG-03 flip (P37.16a/b's per-family lines, the
Wave-D flip list OP-26), every HG-11 readout (P37.65b's promote),
the Part VIII-screened capture runs (438/439), the P37.36 archive
write, the P37.42 API roll, the P37.55 external archival deposit,
P37.71's purge deploy/uses, and every publish line (P37.45, P37.63,
P37.64, the capstones — they ride P37.65's Class S path). §8.1's
anticipated 11D list is not reconciled here — this list is what the
written headers name; recorded as the plan-vs-written drift if the
counts differ.

Outreach-owed list (11D part, ADR-171 — the Stage-0 set
SIG-CHART-033, SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013,
SIG-GOV-024 stays *owed — unmet at launch* on every
acquisition/connector-touching row; no agent contacts anyone):

- **P37.11** (432), **P37.12** (433), **P37.70** (434) — the keyed
  API unblocks (`D-FEDERAL.1-1`, `D-SOURCES.7-2`, `D-SOURCES.8-2` a).
- **P37.13** (435), **P37.14** (436) — registry completeness sweep,
  statute-seeded leads.
- **P37.16a/b** (438–439) — the dossier `live` captures (acquisition
  acts under their HG-03 + Part VIII gates).
- **P37.44** (468) — the mechanical-evaluation upstream GETs (OD-15
  [C-8] = alias first — no request sends the operator's name).
- **P37.47–53** (472–478), **P37.69a/b** (479–480), **P37.54** (481)
  — the Wave-D screened lanes, portal/WFS families and the
  activation row.
- **P37.56** (483) — the WACZ captures for HTML document sources.

19 rows; no 11D contract stamps any of the seven ids satisfied.
Carried to GATE-ANNOUNCE's 'spec MUSTs unmet at launch' list (plan
§13.5, row 510) — the final form lands in P38.5's packet.

Placements carried (deliverable 5):

- GATE-G6's collected decisions (ING-GO-D, the Wave-D flip list, the
  11D OM-20 list, the standing-go renewal) sit as quoted cells in the
  contracts that carry them — never anticipated; the contracts say
  "the operator's lines at GATE-G6", never an answer.
- `D-R11-OSMUID-1` stays with P37.1 (PLAN-11B C13's hand-off
  confirmed by PLAN-11C C12) — no 11D row owns an OSM connector
  change.
- PLAN-11C handed nothing else forward by `## Plan extensions`
  lines on this range; the tail's register names the U-003.*
  closures' final landing (P37.68d's packet) and the MUSTs-unmet
  list GATE-ANNOUNCE reads.

Split/insert activity: none — every plan row was contracted under
its seeded file name; no `## Plan extensions` line was needed and no
row was renumbered (OM-03).

Verification (D12): the checks recorded per batch plus —
`req_index.py check` (`req_index: current`),
`check-build-memory.sh .` (0 violations; the same 37 pre-existing
warnings), `memory_guard.py all --staged` (see commit record),
`check_live_claims corpus` (0 violations after the code-quote
respells recorded per line), docs gates before the commit (see
commit record).

Stale-cell repair recorded: `docs/build/README.md`'s `rows 1-N as
of` line read `rows 1-416 as of P36.72b` while BUILD_INDEX's top
landed row was 417 / P36.70 — stale by one at the dispatch tip
`c981fec1` (`test_build_readme_index_range_matches_the_index` red
at the boundary). Repaired to `rows 1-417 as of P36.70,
2026-11-05`; the line moves to 418 at this row's own closeout.

## OM gap table

One row per operating clause of the contract's B5 §6.2 / H2 §7 block;
filled per context, completed at closeout.

| clause | status | note |
|---|---|---|
| OM-01 harness/model recorded; commits trailered | ok (D1–D12) | header + every commit trailer `Harness: devin-desktop/swe-2-high/subagent`; `check_trailers --range` clean (recorded at the commit) |
| OM-04 dates from `date -u` / git / GitHub (source named) | ok (D1–D12) | header + per-context Started/Closed stamps anchored to `date -u` |
| OM-05 CI read at every boundary; red → blockedOn | ok | `ci: pass #443@4f6e88d` 5/5 head-bound (run 42016664150; web attempt-2 1h2m9s after the LH-PERF-1 LCP flake on attempt 1 — flake logged, rerun green); ancestor `#442@c981fec` python read recorded verbatim in the Boundary record |
| OM-06 every AC names its layer | ok (D1–D12) | every contract's ACs tag a layer |
| OM-14 production mutations (none this row) | n/a | none — planning row, `live_verification=false`; the drafted OM-20 list is for GATE-G6 and nothing ran |
| OM-13 protected records appended only | ok (D1–D12) | ledger/manifest/index appended; the 90 numbered skeletons are this row's own deliverable — the sanctioned skeleton→contract rewrite class (PLAN-11B/11C precedent) |
| OM-15 no test asserts a living record's current value | ok (D1–D12) | no test touched; no living cell asserted |
| OM-07/08/09 gate records verbatim | ok (D1–D12) | every contract's gate cell carries the plan row's operator words verbatim; the two gate markers carry their guard sentences; nothing decided by this row |
| OM-16 size budget | ok (D1–D12) | twelve contexts on the ≤8-row seam (D11 takes the 10-row tail per the contract's own table); every contract's Load re-measured under ~150k loaded tokens; the single-session dispatch actual recorded above |
| OM-02 closeout is one commit after the PR exists | ok | closeout commit = Closed stamp + OM gap table + boundary record + BUILD_INDEX row 418 + LEDGER advance + README row range + projection regen |
| OM-19 windows / live legs (none this row) | n/a | none for this row — the written contracts carry their own windows/legs verbatim; no leg ran or was queued by this row |
| OM-20 pre-authorisation | n/a | not an OM-20 row — it drafts the 11D list (15 rows with written `Production mutations` headers) for GATE-G6 to name; nothing pre-authorised here |
| OM-03 rows only from the ratified plan | ok | rows 421–510 are the ratified chain rows; D12 evaluated the re-split rule with counts — 76 engineering rows / 65.0 runs, under both thresholds, not fired |
| PR-1 branch from chainTip; PR base = previous branch | ok | branch from `c981fec1` on `r11/P36.70-second-release-acceptance`; PR base = that branch |
| CI-2/CI-6 pre-closeout head green | ok | `ci: pass #443@4f6e88d` — all five required checks head-bound (run 42016664150; docs 2m46s, security 37s, composed 4m20s, python 21m52s, web 1h2m9s attempt-2) |
| P11 local gate | ok (with recorded limits) | `make check` 11,106 passed / 2 skipped / 14 machine-local fails / 625 Docker-gated errors — `SIG_GCP_PROJECT` unset (fail-closed by design), `test_p34_18_aliases` ×2 (pre-existing), Docker daemon unreachable (db/e2e legs error locally, run in CI); `make docs-check` green after projection regen |
| CI-8 CI config changed | no | no workflow/toolchain change this row |

## Boundary record (post-closeout)

`ci: pass #443@4f6e88d` — 5/5 head-bound on the pre-closeout tip (run
`42016664150`: docs 2m46s, security 37s, composed 4m20s, python
21m52s, web 1h2m9s attempt-2; `logs/ci_boundary_443.json`). The
boundary read exited 3 on a **carried waived-ancestor** class (#299
precedent): `#442@c981fec` python failure on the base branch's own
head — not this head's tree; the new head itself 5/5. Web attempt-1
red was a Lighthouse LCP flake (`LH-PERF-1`; flake_log rows
443/…/web/failure + rerun-requested); attempt-2 green. Every red was
ancestor or flake, recorded verbatim; no check loosened.
