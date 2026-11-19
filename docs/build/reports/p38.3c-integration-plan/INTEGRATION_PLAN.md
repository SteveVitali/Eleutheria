<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# ROUND-11 INTEGRATION PLAN — the remaining merge legs + how the open obligations integrate (P38.3c, row 507)

*Agent record (labelled): written by Devin, harness `devin-desktop/swe-2-high/subagent`,
Round-11 chain row 507 (`live_verification=false`, read-only — no production mutation, no
live leg, no gate tick, no operator signature). Every date is `date -u` (2026-11-19) or a
cited git/GitHub time.*

**This ticket (P38.3c) merges nothing, tags nothing, and does not touch `main` or any
branch.** It produces the read-only inspection and the *ordering* the operator runs to
finish integrating the chain and to integrate the obligations that stay open after it.
Every command in §(d) and every leg in §(f) is **reviewable but unexecuted** by this
ticket; the only commands actually run for this document are the read-only `gh pr
list/view`, `gh run list`, `git` inspection and `docs/build/tools/merge_dryrun.sh`
invocations recorded in §(i).

This plan supersedes `docs/build/reports/p33.6-integration-plan/INTEGRATION_PLAN.md`
(P33.6, row 198, written when the open stack was #112–#187) for the current stack. The
P33.6 procedure still applies verbatim — its merge-order rule (§(b) there), its
prescribed conflict resolutions (all three absorbed), its rollback shape and its
post-integration gate are carried forward and restated here. `docs/build/INTEGRATION_PLAN.md`
(P20.3) remains the dated v0.1.0-era record; **no tag and no GitHub release are part of
this plan** — HG-05 stays the operator's separate deferred milestone.

- **Inspection date:** 2026-11-19 UTC (`date -u` 18:19Z at write)
- **`origin/main` at inspection:** `1d090e7908e9fa775081092615d71cd557705c2f`
  ("Merge pull request #537" — P38.3a, merged 2026-11-19T11:53Z by GitHub time)
- **Chain tip at inspection:** `625253bc` on `r11/P38.3c-round11-integration-plan`
  (this row's dispatch boundary-confirm) — forked at `ae638ca0` (PR #538's head)
- **Ticket:** `docs/tickets/507_P38.3c__round11-integration-plan.md` ·
  `implement-spec spec=docs/tickets/507_P38.3c__round11-integration-plan.md live_verification=false`

---

## (a) The PR graph at inspection time — the ≈ 325-PR stack is already integrated

The plan cell sizes "the ≈ 325 stacked PRs (#155–#190 + ≈ 290 Round-11 PRs)". **At this
read that stack no longer exists as open work — the operator integrated it
progressively** (the OP-08 bottom-up pattern, which the HG-05 skip allowed):

- **#155–#190: 36/36 merged** (#155 merged 2026-10-02T07:27:56Z … #190
  2026-10-06T12:15:59Z, GitHub times).
- **#191–#537: 317/347 merged.** The 30 numbers in that range that never merged are
  **closed-not-merged** — superseded v2 branches, rolled-back live-leg branches and
  withdrawn record heads, none carrying unlanded content the chain lacks: #194, #206,
  #212, #215, #222, #244, #247, #248, #249, #254, #260, #292, #294, #297, #301, #305,
  #310, #311, #330, #333, #344, #353, #388, #394, #413, #414, #417, #513, #515, #516.
  (Each was verified `state: CLOSED, mergedAt: null` via `gh pr list --state closed`.)
- **Open at read: exactly 1 — PR #538** (`r11/P38.3b-round11-spec-reconciliation` →
  `main`, head `ae638ca0`, `MERGEABLE` / `mergeStateStatus: UNSTABLE` — its head run
  44584900104 was in flight at the read; its prior head `96437104` went `ci: pass`
  5/5 head-bound on run 44573176771).
- **Merge fidelity verified:** `tree(merge #537 @ 1d090e79)` ==
  `tree(#537 head)` = `011daaf773be956ddee5a3daa531e7e2fc76bc54` — the operator's
  merge commits land each PR's head tree exactly; nothing was absorbed or dropped in
  transit (the same invariant P33.6 verified at its boundary).

So the merge legs this row sizes are the **tail**, not 325: #538 plus the three rows
still to produce PRs (this row 507, P38.4 row 508, P38.5 row 509) plus the
gate-marker records that ride the chain tip (row 510, GATE-ANNOUNCE — the operator's
signed readout lands on the chain and merges with a subsequent PR's ancestry, the
`ede12a67`/GATE-ACCEPT-R11 precedent: gate rows open no branch and no PR of their own).

Local `main` is stale (`2f4e9e57`, far behind `origin/main` — the same pre-existing
housekeeping fact P33.6 recorded, still true); the operator must use
`origin/main`/`git pull --ff-only`, never the stale local ref.

## (b) The remaining merge legs — sized and ordered

Merge strictly in ascending PR/row order; each tail PR is stacked base = previous
row's branch (H2 PR-1), so GitHub auto-retargets a PR to `main` when its predecessor
merges — the #535→#538 retargets all happened that way.

| leg | PR / record | content | size at write | precondition |
|---|---|---|---|---|
| **M1** | #538 (P38.3b, row 506) | spec reconciliation report + ADR-253 + 3 unticked proposals + `D-P38.3b-1` | +1,698/−7 · 22 files, docs only | head-bound CI green on `ae638ca0` (owed at the next boundary read; its `96437104` head already read pass 5/5) |
| **M2** | this row's PR (P38.3c, row 507) | this plan + the closeout records | bounded by M (≤3,000 changed lines) | head-bound CI green on the closeout-precursor head |
| **M3** | P38.4's PR (row 508, docs refresh) | repo-docs + agent-docs refresh; every production claim cites a probe-run record | ≤3,000 (M) | M2 merged/dispatched; its own green head-bound read |
| **M4** | P38.5's PR (row 509, announce-readiness review) | the GATE-ANNOUNCE packet (D3 §5 checklist, MUSTs-unmet register, REVIEW-R11 dispositions surface, outreach-owed list) | ≤1,500 (S) | M3; REVIEW-R11's register exists to cite (it runs after P38.4 — §f6) |
| **M5** | GATE-ANNOUNCE records (row 510) | operator-signed `readouts/GATE-ANNOUNCE.md` + GATE DECISIONS rows on the chain tip | no PR of its own | only sits when §(f6)'s preconditions hold — never before REVIEW-R11's S0/S1 are fixed or dispositioned |

Conflict expectation: **none predicted.** `merge_dryrun.sh` at this read: Pass A —
#538 merges cleanly onto `origin/main`; Pass B — bottom-up accumulation clean, final
tree == #538's head tree `740638306d5578230b1b8be2d11003e556ab6bf1`. Every tail head
descends from its predecessor's tip, so each merge is a clean `--no-ff` merge commit.
The load-bearing shared files (`DEFERRALS.md`, `LEDGER.md`, `BUILD_INDEX.md`,
`README.md`, `COVERAGE_MATRIX.csv`, `events.jsonl`, `sqitch.plan`) only conflict if
the operator merges out of order or a head diverges mid-sitting — the same five-file
rule P33.6 §(b) recorded: order is semantically load-bearing, never cosmetic. The
P33.6 conflict table is fully absorbed (all three prescribed resolutions landed);
no new conflict step is predicted. If a merge conflicts anyway: STOP — the
inspection is stale; re-run the dry-run.

## (c) Operator merge procedure — copy-pasteable (bottom-up merge commits)

> Nothing in this block was run by P38.3c. `main` is pushed only by the operator.

```bash
# 0. Fresh state + dry-run proof (must print RESULT: all N open PRs merge clean).
git fetch origin
git checkout main && git pull --ff-only origin main
sh docs/build/tools/merge_dryrun.sh        # read-only; compares against origin/main

# 1. Merge every open PR in ascending number order, keeping branches.
#    Retarget each PR's base to main explicitly right before merging it
#    (tail PRs stack base=previous-branch; auto-retarget also fires on the
#    predecessor's merge — the explicit edit makes the intent visible).
for n in $(gh pr list --state open --json number --jq 'sort_by(.number)[].number'); do
  gh pr edit "$n" --base main
  gh pr merge "$n" --merge --delete-branch=false || {
    echo "PR #$n needs manual conflict resolution — STOP, re-run the dry-run."
    break
  }
done
```

Verification cadence: `gh run list --branch main --limit 1` → `gh run view <id>`
after each merge (`ci.yml` runs on push to `main`); the tree-equality check
`git rev-parse 'HEAD^{tree}' 'HEAD^2^{tree}'` on each merge commit should read
identical trees — that is the merge-fidelity invariant §(a) verified on #537.

## (d) Rollback

Merges are `--no-ff` merge commits on `main`; undo is **revert, never
reset/force-push** (append-only, P1–P3):

```bash
git merge --abort                       # before pushing a bad in-progress merge
git log --first-parent --merges --oneline origin/main
git revert -m 1 <merge-commit-sha>      # newest merge first; each reverts cleanly
git push origin main
```

A mid-run halt is safe: `main` is simply integrated up to the last merged PR and the
remaining stack stays valid. **Withdrawal invariant (SIG-TRUST-006):** reverting a
merge must never re-expose a withdrawn artifact — the policy-controlled tombstone is
the rollback path for published bytes, not byte deletion. Branches are never deleted.

## (e) What integration does not discharge — nothing signed by merging

Merging the tail changes **no** obligation's status. The register is
`docs/tickets/DEFERRALS.md` (281 rows at this read: **196 owed** — 193 OPEN + 3 rows
PARTIAL-deferred) with the full `owner:`/`trigger:` table at
`docs/build/reports/p38.3a-round11-backlog.md` and the readiness statement at
`docs/build/OPERATIONAL_READINESS.md` §(g). GATE-ACCEPT-R11 is **SIGNED**
2026-11-19T06:55Z ("I accept the readouts. Please continue" verbatim; record commit
`ede12a67`, operator-signed) — the signature accepted the packet **as presented**; it
discharged no debt and is never re-decided here.

## (f) The obligation-integration ordering — what integrates after the merge

Every leg below is recorded `prepared_not_executed` or OPEN; `owner:`/`trigger:` are
quoted from each row's DEFERRALS `unblocked by` cell or `return_pass.toml` map row.
The ordering is a record of dependencies, never a schedule — windows are each row's
own; nothing is re-decided.

### (f1) The promote chain spine — gates every post-round exit

Two release lineages share the same machinery (`sig-ops release …`, the
`sig.promotion-approval/1` approval object, `release verify --mode S|P`):

**Lineage A — the first model release (P35.x).** The Round-10 candidate chain that
predates Round 11's tail; every prerequisite leg is itself queued:

| order | leg | owner | trigger (as recorded) |
|---|---|---|---|
| A0 | `live:P34.46` + 48 h soak · `live:P34.43` L1+L2 | OM-19 leg-runner / operator | each its own map row's window + go |
| A1 | `P35.61-live-pass` (audit→pause→apply→+0→freeze — `D-R10-LIVE-1`) | operator go naming `--authority` | after A0, weekday 14:00–20:00Z slot |
| A2 | `live:P35.53` release-infra apply | **DONE 2026-11-18** (OP-24; packet `reports/p35.53-release-infra-apply/`) | — |
| A3 | `P35.59-dark-cutover` (release-layout web cutover) | leg-runner | after A2 + `live:P34.40`-L2; its GATE-G4/G5 pre-authorisation **expired** — see §(f5) |
| A4 | `P35.62-staging-candidate` (the staged candidate) | leg-runner | after A1+A3+A2; same expired-authority posture |
| A5 | `P35.63-dispatch-stage-verify-readout` (staged cut → class_s → readout draft) | operator's in-slot go | after A4 |
| A6 | `P35.63-promote-under-hg11` | operator's verbatim signed HG-11 candidate readout + go | after A5 + the signed readout object exists under `registry/approvals/` |
| A7 | `P35.64-sweep-packet` (11B acceptance sweep) | leg-runner, read-only | after A6 — the promoted first release must exist |

**Lineage B — the core-surfaces + final release (P36/P37).** The spine the backlog
register names (`§3`): `D-P36.72b-1 → D-P37.65a-1 → D-P37.65b-1 →` post-promote set.

| order | leg | owner | trigger (as recorded) |
|---|---|---|---|
| B0 | staged candidate + the operator-signed `sig.promotion-approval/1` `kind=signed_readout` under `registry/approvals/` naming the candidate pub | **operator** (HG-11; GATE-G6 §2 answered "Approve the promote (rec.)" 2026-11-05T15:20Z — the decision is recorded, the signed readout object and the candidate are still owed) | the GATE-G6 sitting's packet (`reports/p36.72b-promotion/`); window live `expected >= 2026-11-13T12:00Z`, never inside AR-3 windows |
| B1 | `D-P36.72b-1` — core-surfaces Class S promote + `release verify --mode P` | OM-19 leg-runner or operator | B0 + `SIG_RELEASE_REGISTRY` + ADC/`SIG_GCP_PROJECT` + digest-pinned images; `implement-spec spec=docs/tickets/416_P36.72b__… live_verification=true` |
| B2 | `D-P37.65a-1` — final release cut + live crawl + scrub (`release cut → build → sites → stage`; `release verify --mode S`) | OM-19 leg-runner or operator | `D-P35.53-1` (DONE) + project ADC/`SIG_GCP_PROJECT`; **never inside AR-3 windows 12-06 → 12-13T12:00Z**; `…/493_P37.65a__… live_verification=true` |
| B3 | `D-P37.65b-1` — final HG-11 readout + promote | OM-19 leg-runner or operator | the operator's verbatim go at the HG-11 readout + signed `sig.promotion-approval/1` naming the candidate + the B2 staged candidate; `…/494_P37.65b__… live_verification=true`. Recorded verbatim: "No verbatim go exists" (`runs/P37.65b.md`) — the 2026-11-18 apply go named `D-P35.53-1`'s ADC scope, not an HG-11 promote go |
| B4 | post-promote legs — all read the **promoted** release | OM-19 leg-runner or operator | after B3, inside each row's window |

**B4 — the post-promote set** (each `prepared_not_executed`, owner: the OM-19
leg-runner or the operator unless named):

| leg | what it is | extra preconditions |
|---|---|---|
| `D-P37.63-1` | map-acceptance live legs (`live-journeys`/`live-lhci`/`live-tiles`) + K1 MAP-07 `cost-7d` | cost leg at promotion +7 d |
| `D-P37.64-1` | explore-acceptance `live-verify` (K13 §8 capstone journeys at real scale, D20 crawl, DV-parity) | `AR-3 + AR-2` window |
| `D-P37.67-1` | live L2 re-measure over the promoted release (`sig-ops quality baseline` + `apply-baselines` → `streaml_acceptance.json` re-verdict) | `live:P34.43` audit handle, `AR-3 + AR-2` |
| `D-P37.68a-1`/`b-1`/`c-1`/`d-1` | promoted-release capstone legs A1–A4 / J1–J5 / O1–O4 / consolidated+per-ask+routes+budgets/axe, each `SIG_CAPSTONE_BASE_URL=<promoted-origin>` | J4's durable half rides ACT-24 (HG-11); J5's diff needs the activated predecessor; `cost-read` needs billing rows (`D-P34.5-2`); O3's attribution rides ACT-07 |
| `D-P37.68a-2`/`b-2`/`c-2`/`d-2` | the OP-22 operator walkthroughs (maintainer, not independent) | **operator** — the packets `reports/p37.68*/WALKTHROUGH.md` are committed and requested; promoted release must exist |
| `D-P36.71-1` | post-promotion search-acceptance battery (dev ≥ 0.90, held-out ≥ 0.80, staging p95, cost, A1/J2 cold walk) | after B1's promote; the staging leg needs `D-P36.38-1` (v2 roll — never pre-authorised, verbatim go owed); the sealed leg needs `D-P36.79-1` (held-out object write — expired-authority posture, §f5) |
| `D-P36.70-1` | second-release acceptance rehearsal (REL-11, four timed legs) | after B1's promote; Class S under the operator-authority records (the standing go's G6 expiry was recorded at the GATE-G6 sitting) |
| `D-P35.64` sweep | 11B acceptance sweep | after A6's promote |
| `D-P36.73` sweep | 11C acceptance sweep + G6 packet refresh | after B1's promote |

Adjacent owed acts the spine also waits on: `D-P35.60-1` (operator adoption of the
standing-go text + the first signed Class-S readout — every promotion is fail-closed
Class S meanwhile); `D-P36.38-1` (v2-search roll, verbatim go owed);
`D-P36.79-1` (held-out seal object); `D-P37.67-2` (11 kept-ratchet quality blocks —
engineering-routed, not promote-gated).

### (f2) `D-P38.2-1` — GAP-RP-1 (operator-owned disposition)

The four QUEUED legs recorded with no `[[row.legs]]` entry, no `returnPass:` id and
no recorded drop (`P35.22-truthful-claim-identity-live`, `P35.27-resolver-input-live`,
`P35.32-ingest-run-report-live`, the P35.46 GATE-G4-named ER-run leg). Owner: **the
operator**. Trigger: the recorded disposition — at a sitting or any earlier verbatim
GATE DECISIONS row — choosing (a) drop-with-reason per the P35.53 pattern or (b) real
`[[row.legs]]` entries under a fresh verbatim OM-20 listing. GATE-ACCEPT-R11 §1e
recorded both dispositions; the signature explicitly left the row OPEN. It integrates
whenever the operator answers — **no merge and no leg waits on it**, but
`return_pass.py check` keeps it loud until each leg has a home or a drop.

### (f3) NIGHTLY-RED-1 and its owed observations

`nightly.yml` concluded failure on every completed run at this read — **≥43
consecutive completed failures** through run 44448496659 (2026-11-19T03:01Z,
`oracle-unexpected` at `e8dfcb76`; cancelled runs don't break the count; the latest
completed run is unchanged since the P38.3a read). Repair stays operator-routed.
Until a green run lands, three verify rows cannot meet their conditions:

- `D-P34.7-1` — the replay stage fires and reports `oracle-unexpected` rows (judged
  > 0, unexpected > 0); its 0/0/0 condition unmet.
- `D-P34.2-2` — the nightly `--all` recorded-CI sweep has no green run; the
  post-merge audit leg's precondition (merges to `main`) now exists.
- `D-P34.1-1` — the literal form fails (61/100 recent `push` runs cancelled — all
  pending-superseded under `concurrency: ci-${{ github.ref }}`, never an in-progress
  cancellation; `cancel-in-progress` is `pull_request`-only). Whether the intent is
  met is the audit's call — recorded, never decided.

### (f4) Wave-C consequence and Wave-D windows

- **Wave-C `P37.2-l1…l5`** (pre-grow → tier bump → national run → 24 h soak →
  revert): unrun inside the strict ING-GO-C window **2026-11-16 → 11-20** (still open
  at this write — 11-19; L4's 48 h grace runs to 2026-11-22T00:00Z). The recorded
  OM-19 consequence: a missed leg re-windows under a **fresh go**, never a hidden
  failure and never borrowed from the ING-GO-C text (the tier-bump go is P37.2's own
  in-ticket pause). This follows the Wave-A precedent (10-19→10-23 elapsed unrun,
  recorded).
- **Wave-D `P37.54` L0→L11**: window 1 opens **2026-11-23 → 12-04**, window 2
  **2026-12-14 → 12-18** (make-up + L11); excluded: AR-3 freeze 12-06→12-13, the
  2026-12-15 release-cut day, materialize/G2 slots. Go: ING-GO-D byte-exact (GATE-G6
  `b91f8e58`) + `wave-d-gate` exit 0 + that day's OP-26 flips recorded executed —
  the Wave-D flip-list pre-approval itself expired at GATE-ACCEPT-R11 (§f5), so each
  day's flips ride the recorded mechanism, never an assumed carry.

### (f5) Authority expiries at GATE-ACCEPT-R11 — recorded, not decided

The signed sitting (2026-11-19T06:55Z) is the named expiry of:

- **GATE-G6 §4's 11D OM-20 list** (15 rows: P37.3/4a/4b/11/12/70/15/31/32/33/35/46a/
  46b/56/59) — `expires: GATE-ACCEPT-R11` → **expired**; each named mutation's unrun
  leg now re-asks under its contract (in-ticket verbatim go) — the register's
  recorded posture for `D-P37.59-1` applies to the class: "the authority's carry is
  an operator/audit call, not an agent's".
- **The Class R standing go** (GATE-G6 renewal: expires GATE-ACCEPT-R11 or
  2026-12-05, whichever first) → **expired** — every release is Class S until a
  fresh verbatim renewal (the G6 readout's own recorded default).
- **The Wave-D HG-03 flip-list pre-approval** → **expired**; OP-26 flips ride the
  recorded mechanism per source.
- Already expired earlier (GATE-G6, 2026-11-05): the GATE-G5 §4 re-authorisations of
  the 24 unrun 11C legs — GATE-G6's re-list **defaulted** ("each re-asks in-ticket —
  nothing pre-authorised"), so every unrun 11C leg needs a fresh verbatim go.

### (f6) REVIEW-R11 → GATE-ANNOUNCE ordering (plan §8.3, S6-F3, S6R-19; ADR-149)

The tail's recorded order:

1. **P38.4** (row 508 — docs refresh; every production claim cites a probe-run
   record).
2. **P38.5** (row 509 — the announce-readiness review; collects the D3 §5 checklist
   state, the REVIEW-R11 S0/S1 dispositions surface, the outreach-owed list's final
   form and the 'spec MUSTs unmet at launch' register into the packet GATE-ANNOUNCE
   reads — it decides nothing, announces nothing; U-009 binds).
3. **REVIEW-R11** — the post-round Claude Code (Opus 5.5, xhigh) deep review, a unit
   outside the chain (≈8–12 contexts): runs **after P38.4** (the plan's calendar puts
   it "after the final release" — the promote chain's landing is the honest reading
   of "final"; the review is read-only and its start is the orchestrator's/operator's
   call, never this row's) and **before GATE-ANNOUNCE**.
4. **GATE-ANNOUNCE** (row 510, gate marker — no branch, no PR): sits only when
   P38.5's packet exists (sha256 recorded pre-sitting), **each REVIEW-R11 S0/S1
   finding is fixed or dispositioned** (S6-F3 — a fix lands as a `decompose-spec
   mode=extend` row appended after row 510, then a new GATE-ANNOUNCE row; row 510
   receives the appended `superseded-by(row <n>)` token; no row is renumbered), no
   leg is *due* (OM-19), and no OPEN deferral scopes itself to the gate unrecorded.
   Answers: `ready` / `not ready` plus each own-words line (the WV-01/03/04/05/08
   keep/lifts, Q-29, the MUSTs-unmet signature). Silence = pause (OM-18). A `ready`
   answer authorises nothing by itself — the announcement is LATER-22
   (`D-R11-LATER-22`, owner: the operator; trigger: CAP-02 passes + REVIEW-R11
   S0/S1 dispositioned + the operator says go), human work outside this chain.

The promote chain (§f1) is **not** a recorded precondition of GATE-ANNOUNCE — the
gate's own contract names P38.5 + REVIEW-R11 + no-leg-due. The public-verification
count stays 0 and every post-promote leg stays owed until B1–B4 land; the packet
says so, never implies readiness.

### (f7) The Tier-2 deferral set and the statutory duty leads

`D-P37.66-1…-12` — the 130 `later-phase(…)` Tier-2 plan rows grouped under I8 §6.3's
twelve reasons (extraction-time name redaction; missing connector families; the
SIG-PUB-014a excerpt screen; I=0 mirrors; the §43.4 naming gate; S4 coarsening;
unanswered E4/Q-30/C6/C8/IT operator questions; terms captures; index surfaces;
tribal data-governance rule; singletons). Each row carries its own `owner:`/`trigger:`
— they integrate **per family** when the named stage/decision/adapter lands, never by
the merge and never in bulk. `D-P37.66-13…-15` — the six statutory duty leads (4
commenced VA/AL/AR/UT + CA survey context; NM `not_yet_due` 2027-04-01; MN contingent
on HF 3198) — owner: the operator via `D-R11-LATER-04` (sending authority) or the
named watch pass; desk research registered the leads, nothing fetched early.

## (g) What stays owed after integration — the register carries forward

Beyond the promote spine: the owed set at this read is 196 obligations (the full
`owner:`/`trigger:` table at `reports/p38.3a-round11-backlog.md` §1): every HG-03
flip and reviewer lane (`D-SOURCES.*`, `D-JURIS.2-1`), credentials (`D-P21.3-2`,
`D-P21.5-1`, `D-P21.7-1`, `D-SOURCES.7-2`/`8-2`), the intake operating packet
(`D-P32.16-1` — the receiver stays `503 receiver_not_operating`), the deferred human
spines (`D-R10-HUMAN-1`, `D-R6.1-EVAL`, `D-P30.2b-1/-2`, `D-R10-USERS-1`,
`D-R10-SOURCES-1`), the K14 gallery sign-off (`D-K14-9`), the SIG-ENG-025 quarterly
review (`D-P38.3a-1`), the proposal-apply (`D-P38.3b-1`), the `D-R11-LATER-*`
trigger-seeded set, and the watch items `VISUAL-MAP-LIGHT-1`/`DARK-1` (unlisted —
the operator's allow-list call), `LH-LCP-MARGINAL-1`, `D-P37.61d-1`, `D-P37.61e-1`
(expires 2026-11-30), `DIGEST-LINT-1`. Integration signs none of these.

## (h) What to verify on `main` afterwards

```bash
git pull --ff-only origin main
git rev-parse 'HEAD^{tree}'            # == tree of the top merged PR's head
gh pr list --state open               # expect: none left (or only intentionally-open)
git merge-base --is-ancestor <top-head-branch> origin/main && echo ANCESTOR

make check                                             # full gate on the integrated tree
SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db          # Docker: claim spine
SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra     # Docker: composed stack
npm --prefix web run check                             # web gate
python3 docs/build/tools/check_spec_src.py
python3 docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv
python3 docs/build/tools/check_backlog.py && python3 docs/build/tools/build_backlog_md.py --check
python3 docs/build/tools/return_pass.py check          # 196+ owed, each in one home
python3 docs/build/tools/obligation_events.py check
python3 docs/build/tools/check_round_close.py check
python3 docs/build/tools/check_live_claims.py corpus
bash scripts/docs/check-build-memory.sh .
make docs-check
```

Then `gh run list --branch main --limit 1` → `gh run view <id>` — `main`'s own CI
run green before the tail's next row dispatches (SIG-MEM-007's boundary read).

## (i) How this inspection was produced (reproduce)

```bash
gh pr list --state open --json number,baseRefName,headRefName,headRefOid,mergeable --limit 400
gh pr list --state merged --json number,mergedAt --limit 600        # 507 merged at read
gh pr list --state closed --json number,headRefName,title,closedAt --limit 600
git fetch origin && git rev-parse origin/main '1d090e79^{tree}' '1d090e79^2^{tree}'
git merge-base origin/main HEAD                                     # → f8f1d0dd
sh docs/build/tools/merge_dryrun.sh                                 # Pass A clean; Pass B tree==#538 head
gh run list --workflow nightly.yml --limit 20 --json databaseId,conclusion,createdAt,headSha
gh pr view 538 --json baseRefName,headRefOid,mergeable,mergeStateStatus,additions,deletions,changedFiles
```

All operations were read-only against every real ref: `git fetch` (remote-tracking
refs only), `gh pr list/view`, `gh run list`, and the dry-run's throwaway detached
worktree under `/tmp` (removed). No merge, tag, push to `main`, branch deletion or
force-push was performed.
