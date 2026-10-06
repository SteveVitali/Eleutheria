<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# ROUND-10 INTEGRATION PLAN — merging the open PR stack onto `main` (P33.6, row 198)

**This ticket (P33.6) merges nothing, tags nothing, and does not touch `main` or any
branch.** It produces the read-only inspection and the *procedure* the operator runs to
integrate the open PR stack after the chain completes (row 200, P33.8). Every command in
§(e)–§(f) is **reviewable but unexecuted** by this ticket; the only commands actually run
for this document are the read-only `gh pr list/view`, `git` inspection, and
`docs/build/tools/merge_dryrun.sh` invocations recorded in §(i).

This plan supersedes `docs/build/INTEGRATION_PLAN.md` (P20.3, written when the open stack
was #27–#53) for the current stack. The P20.3 document remains the dated record of the
v0.1.0-era procedure; its strategy analysis (§(c) there) still applies and is extended
here. **No tag and no GitHub release are part of this plan** — REL.1/HG-05 remains the
operator's separate, deferred milestone (readout `docs/build/readouts/GATE-G1.md`,
SKIPPED-BY-OPERATOR 2026-09-10; the operator has since integrated PRs #20–#111
progressively, which that milestone permitted).

- **Inspection date:** 2026-09-28 UTC
- **Chain tip at inspection:** `bf98abb5f5e423721131b948a7fc41c0722623dd` (PR #187,
  P33.5) — plus this ticket's own PR on top once opened
- **Ticket:** `docs/tickets/198_P33.6__round10-integration-plan.md` ·
  `implement-spec spec=docs/tickets/198_P33.6__round10-integration-plan.md live_verification=false`

---

## (a) The PR graph at inspection time

**`origin/main` = `3b913c6ff147a1fa63d3356be87d5fc9446b4455`** ("Merge pull request #111"
— P26.19). The open stack does not sit on `main` directly; its effective fork commit is
**`5b7fed0e63b6e9d5ff8848e8e3bcbd3b536e891c`** ("docs(build): record PR #111 for P26.19" —
the *head* of PR #111's branch), and critically:

```
tree(origin/main @ 3b913c6f) == tree(5b7fed0e) == d5b230f7ca68126f3280e5ebc2788412b3e7d520
```

`main` has moved since the stack forked — but only by merge commits (PRs #20…#111, the
operator's progressive integration) that add **zero net tree change** over the fork point.
**`main` has NOT diverged content-wise from the stack's base.** Every merge against `main`
in this stack is therefore guaranteed content-clean *at the merge-base level*; the only
real conflicts are the intra-stack divergences in §(c).

Local `main` is stale (`2f4e9e5`, 44 commits behind `origin/main` — a pre-existing
housekeeping fact first recorded in BUILD_INDEX §A.1); the operator must use
`origin/main`/`git pull --ff-only` before integrating, never the stale local ref.

**75 open PRs** (#112–#187; #148 is already MERGED — the P25 live-ops round-base import —
and is absent from the open set). No drafts. GitHub mergeable status: all `MERGEABLE`
except **#113 and #117 = CONFLICTING** (they diverged from their own stacked bases — see
§(c)). The full ordered inventory, bottom to top:

| PR | head branch | base branch | head SHA | diffstat |
|---|---|---|---|---|
| #112 | `devin/p27-1-public-surface-audit` | `devin/p27-launch-planning` | `b2be264591` | +2763/−4 / 14 files |
| #113 | `devin/p27-2-maximize-publishable-scope` | `devin/p27-1-public-surface-audit` | `70137cef7e` | +3065/−159 / 32 files |
| #114 | `devin/p27-3-export-data-shaping` | `devin/p27-2-maximize-publishable-scope` | `96f1e7a59b` | +9822/−11 / 25 files |
| #115 | `devin/p27-4-spine-backed-export-bundle` | `devin/p27-3-export-data-shaping` | `70d7bdb9ea` | +2193/−52 / 15 files |
| #116 | `devin/p27-5-web-data-layer-wiring` | `devin/p27-4-spine-backed-export-bundle` | `4664bb24dd` | +991/−39 / 30 files |
| #117 | `devin/p27-6-ia-redesign-landing` | `devin/p27-5-web-data-layer-wiring` | `3be415cd09` | +1263/−281 / 33 files |
| #118 | `devin/p27-7-empty-states-and-polish` | `devin/p27-6-ia-redesign-landing` | `f249fb383f` | +1151/−93 / 37 files |
| #119 | `devin/p27-8-deploy-and-public-cutover` | `devin/p27-7-empty-states-and-polish` | `2500c5b12d` | +1083/−11 / 20 files |
| #120 | `devin/p27-9-interactive-islands` | `devin/p27-8-deploy-and-public-cutover` | `639b870d8e` | +2491/−32 / 30 files |
| #121 | `devin/p27-10-domain-cutover-surveillancegraph` | `devin/p27-9-interactive-islands` | `ca1c2529ba` | +809/−33 / 18 files |
| #122 | `devin/p28-1-entity-resolution-at-scale` | `devin/round6-7-seed` | `b69f40e2a2` | +2206/−26 / 23 files |
| #123 | `devin/p28-2-sharing-relationship-network` | `devin/p28-1-entity-resolution-at-scale` | `0c0e244325` | +1422/−24 / 17 files |
| #124 | `devin/p28-3-contradictions-reconciliation` | `devin/p28-2-sharing-relationship-network` | `ef9a96fe68` | +1239/−25 / 15 files |
| #125 | `devin/p28-4-honest-coverage` | `devin/p28-3-contradictions-reconciliation` | `79dee1b75e` | +1527/−23 / 19 files |
| #126 | `devin/p28-5-refresh-surface-materialized-graph` | `devin/p28-4-honest-coverage` | `400f67be17` | +1125/−47 / 13 files |
| #127 | `devin/p28-6-accountability-linkage` | `devin/p28-5-refresh-surface-materialized-graph` | `a671a85a87` | +1899/−46 / 18 files |
| #128 | `devin/p29-1-contributor-identity-and-ops` | `devin/p28-6-accountability-linkage` | `215d695e41` | +1349/−110 / 20 files |
| #129 | `devin/p29-2-detector-records-request-loop` | `devin/p29-1-contributor-identity-and-ops` | `1462ddc746` | +1761/−27 / 25 files |
| #130 | `devin/p29-3-targeted-source-breadth` | `devin/p29-2-detector-records-request-loop` | `3015937c1e` | +1111/−45 / 22 files |
| #131 | `devin/p30-1-osm-land-and-settled-reaudit` | `devin/p30-golive-seed` | `9b353af35d` | +683/−140 / 22 files |
| #132 | `devin/p30-2-hosted-round6-materialization` | `devin/p30-1-osm-land-and-settled-reaudit` | `83cd666805` | +1168/−40 / 31 files |
| #133 | `devin/p30-2a-camera-predicate-registry` | `devin/p30-2-hosted-round6-materialization` | `84597f1d4c` | +5827/−138 / 38 files |
| #134 | `devin/p30-2b-geospatial-camera-site-resolution` | `devin/p30-2a-camera-predicate-registry` | `889997df67` | +30506/−116 / 39 files |
| #135 | `devin/p30-3-national-export-and-public-cutover` | `devin/p30-2b-geospatial-camera-site-resolution` | `065d8aa0ff` | +2006/−181 / 43 files |
| #136 | `devin/p30-4-post-launch-closeout` | `devin/p30-3-national-export-and-public-cutover` | `df7b127817` | +704/−15 / 14 files |
| #137 | `devin/p31-1-api-db-resilience-and-bounded-search` | `devin/round9-seed` | `b6b84fcc79` | +2065/−74 / 32 files |
| #138 | `devin/p31-2-ingest-run-completion-and-freshness` | `devin/p31-1-api-db-resilience-and-bounded-search` | `0746fc1c66` | +2343/−58 / 33 files |
| #139 | `devin/p31-3-sink-identity-guard-and-batched-writes` | `devin/p31-2-ingest-run-completion-and-freshness` | `ffccd244ea` | +2798/−148 / 31 files |
| #140 | `devin/p31-4-incremental-restart-and-osm-replay-readiness` | `devin/p31-3-sink-identity-guard-and-batched-writes` | `1378296866` | +3329/−54 / 36 files |
| #141 | `devin/p31-5-entity-ref-claims-procurement` | `devin/round9-waveb-seed` | `fa0d67a8c0` | +5273/−52 / 45 files |
| #142 | `devin/p31-6-access-edges-and-hosted-link-materialization` | `devin/p31-5-entity-ref-claims-procurement` | `fd35e7b227` | +2142/−49 / 36 files |
| #143 | `devin/p31-7-claim-re-sightings` | `devin/p31-6-access-edges-and-hosted-link-materialization` | `a14869fd68` | +3014/−43 / 28 files |
| #144 | `devin/p31-8-predicate-registry-legislation-portal` | `devin/p31-7-claim-re-sightings` | `e3b7a5e097` | +9908/−228 / 15 files |
| #145 | `devin/p31-9-negative-space-peer-classes` | `devin/p31-8-predicate-registry-legislation-portal` | `3357f8e7e1` | +1094/−77 / 19 files |
| #146 | `devin/p31-10-camera-site-review-surface` | `devin/p31-9-negative-space-peer-classes` | `4dc4c80a94` | +2325/−19 / 17 files |
| #147 | `devin/p31-11-review-decisions-into-clustering` | `devin/p31-10-camera-site-review-surface` | `cbc0a53628` | +2751/−117 / 24 files |
| #149 | `devin/p31-12-accountability-breadth-federal-uk` | `devin/p31-11-review-decisions-into-clustering` | `b660d1aaff` | +2032/−35 / 25 files |
| #150 | `devin/p31-13-accountability-breadth-ccops-fema` | `devin/p31-12-accountability-breadth-federal-uk` | `401f6faa37` | +4316/−94 / 29 files |
| #151 | `devin/p31-14-presentation-analytics-from-export` | `devin/p31-13-accountability-breadth-ccops-fema` | `5e7de92111` | +2249/−85 / 25 files |
| #152 | `devin/p31-15-vector-tiles-and-compression` | `devin/p31-14-presentation-analytics-from-export` | `61701df303` | +2361/−622 / 36 files |
| #153 | `devin/p31-16-rematerialize-reexport-republish` | `devin/p31-15-vector-tiles-and-compression` | `4cc7e13ca3` | +884/−33 / 12 files |
| #154 | `devin/p31-19-round9-closeout` | `devin/p31-16-rematerialize-reexport-republish` | `08d87c4dc2` | +550/−17 / 14 files |
| #155 | `codex/round10-seed-after-p31-19` | `devin/p31-19-round9-closeout` | `c8d72cc329` | +8001/−35 / 96 files |
| #156 | `devin/p32-1-baseline-and-memory-audit` | `codex/round10-seed-after-p31-19` | `ebd34ce10e` | +2175/−13 / 13 files |
| #157 | `devin/p32-2-typed-claims-and-capture-bindings` | `devin/p32-1-baseline-and-memory-audit` | `5677495a56` | +14046/−482 / 133 files |
| #158 | `devin/p32-3-roles-counts-and-organization-identity` | `devin/p32-2-typed-claims-and-capture-bindings` | `348764c445` | +4308/−314 / 70 files |
| #159 | `devin/p32-4-shared-temporal-read-contract` | `devin/p32-3-roles-counts-and-organization-identity` | `03ac3b0664` | +2897/−327 / 35 files |
| #160 | `devin/p32-5-publication-dispositions-and-filtering` | `devin/p32-4-shared-temporal-read-contract` | `616b889c19` | +2262/−68 / 27 files |
| #161 | `devin/p32-6-legacy-evidence-audit-and-recovery-plan` | `devin/p32-5-publication-dispositions-and-filtering` | `c8d2856e72` | +8596/−68 / 109 files |
| #162 | `devin/p32-7-memory-events-and-current-projection` | `devin/p32-6-legacy-evidence-audit-and-recovery-plan` | `778a5e2e85` | +14211/−29 / 26 files |
| #163 | `devin/p32-8-memory-concurrency-and-recovery` | `devin/p32-7-memory-events-and-current-projection` | `5713f5dd2a` | +2734/−111 / 25 files |
| #164 | `devin/p32-9-human-evaluation-protocol-and-packets` | `devin/p32-8-memory-concurrency-and-recovery` | `c31380fbad` | +5160/−30 / 31 files |
| #165 | `devin/p32-10-resolution-evaluator-and-confidence-gates` | `devin/p32-9-human-evaluation-protocol-and-packets` | `42bb286af6` | +3628/−13 / 21 files |
| #166 | `devin/p32-10a-disposition-single-clock-authority` | `devin/p32-10-resolution-evaluator-and-confidence-gates` | `e8f8764d53` | +1021/−419 / 18 files |
| #167 | `devin/p32-11-gap-driven-source-discovery` | `devin/p32-10a-disposition-single-clock-authority` | `30d401dc98` | +6431/−984 / 52 files |
| #168 | `devin/p32-12-dossier-document-adapters` | `devin/p32-11-gap-driven-source-discovery` | `8ec2bcfb69` | +3925/−13 / 38 files |
| #169 | `devin/p32-13-immutable-releases-and-records` | `devin/p32-12-dossier-document-adapters` | `9ae9b26fb5` | +4785/−25 / 36 files |
| #170 | `devin/p32-14-full-corpus-release-search` | `devin/p32-13-immutable-releases-and-records` | `3c9ea94941` | +4171/−816 / 28 files |
| #171 | `devin/p32-15-coordinated-investigation-workspace` | `devin/p32-14-full-corpus-release-search` | `4dd5a038fe` | +2970/−190 / 38 files |
| #172 | `devin/p32-16-anonymous-correction-intake` | `devin/p32-15-coordinated-investigation-workspace` | `0669f65d70` | +5503/−16 / 33 files |
| #173 | `devin/p32-16-reviewed-correction-application` | `devin/p32-16-anonymous-correction-intake` | `5f80ba1995` | +3954/−33 / 27 files |
| #174 | `devin/p32-17-dossier-schema-completion` | `devin/p32-16-reviewed-correction-application` | `2c588cd653` | +4441/−81 / 30 files |
| #175 | `devin/p32-18-okc-evidence-dossier` | `devin/p32-17-dossier-schema-completion` | `0f2e0711a6` | +10737/−78 / 26 files |
| #176 | `devin/p32-19-tulsa-evidence-dossier` | `devin/p32-18-okc-evidence-dossier` | `3e26a2dc9c` | +5679/−12 / 22 files |
| #177 | `devin/p32-20-san-diego-evidence-dossier` | `devin/p32-19-tulsa-evidence-dossier` | `5efe4b9dca` | +10301/−74 / 25 files |
| #178 | `devin/p32-21-acquisition-pilot` | `devin/p32-20-san-diego-evidence-dossier` | `10547fff20` | +6270/−9 / 21 files |
| #179 | `devin/p32-22-bounded-recovery` | `devin/p32-21-acquisition-pilot` | `a33cd6ec33` | +7905/−12 / 40 files |
| #180 | `devin/p32-23a-release-candidate` | `devin/p32-22-bounded-recovery` | `22b773f8e6` | +13192/−73 / 73 files |
| #181 | `devin/p32-24-investigation-journey-verification` | `devin/p32-23a-release-candidate` | `95c8a73f47` | +14169/−84 / 474 files |
| #182 | `devin/p32-25-accepted-release-verification` | `devin/p32-24-investigation-journey-verification` | `e4bd612e69` | +18130/−765 / 677 files |
| #183 | `devin/p33-1-round10-gap-analysis` | `devin/p32-25-accepted-release-verification` | `ad0bd843b1` | +1750/−673 / 14 files |
| #184 | `devin/p33-2-composed-verification` | `devin/p33-1-round10-gap-analysis` | `d76c22eb64` | +3394/−30 / 130 files |
| #185 | `devin/p33-3-capstone-closure` | `devin/p33-2-composed-verification` | `4127dbf3ac` | +696/−45 / 12 files |
| #186 | `devin/p33-4-backlog-readiness` | `devin/p33-3-capstone-closure` | `a711333d9a` | +448/−13 / 7 files |
| #187 | `devin/p33-5-spec-reconciliation` | `devin/p33-4-backlog-readiness` | `bf98abb5f5` | +613/−51 / 18 files |

**Plus the tail PRs this ticket and its successors open:** P33.6 (this ticket →
`devin/p33-6-integration-plan`, stacked on `devin/p33-5-spec-reconciliation`), P33.7 (row
199, repo-docs refresh) and P33.8 (row 200, agent-docs refresh + memory-chain close). The
stack keeps growing until row 200 — **integrate only after the chain completes**, and
re-run the dry-run at that moment (§(e) step 0).

**Base branches that are not PR heads** (seed branches; their commits ride in transitively
as ancestors of the next PR's head — verified: each is an ancestor of the chain tip):
`devin/p27-launch-planning` (`a6a2b566`, bases #112), `devin/round6-7-seed` (bases #122),
`devin/p30-golive-seed` (bases #131), `devin/round9-seed` (bases #137),
`devin/round9-waveb-seed` (bases #141). `codex/round10-seed-after-p31-19` is both #155's
head and #156's base. Because every open PR head descends from the fork commit, merging the
heads lands every seed commit's content automatically — no separate seed merge is needed.

---

## (b) Merge-order dependencies (why order matters)

The stack is a *linear chain*: each PR's tree was built on its predecessor's tip. Five
shared, append-mostly files make **merge order semantically load-bearing**, not merely
conventional:

| File | Touches in chain | Why order matters |
|---|---|---|
| `docs/tickets/DEFERRALS.md` | 86 commits | every closeout appends/annotates rows; same-line cell edits at the tail |
| `docs/build/LEDGER.md` | 120 commits | `CURRENT STATE` keys are rewritten in place each closeout (each child edits the parent's values) |
| `docs/build/BUILD_INDEX.md` | 85 commits | one appended row per ticket |
| `docs/build/BACKLOG.{csv,md}`, `docs/adr/README.md`, `docs/2_canonical_design_spec.md`, `docs/research/_meta/spec_src/` | ~50 commits each | regenerated artifacts + spec source edits layered in order |
| `db/sqitch.plan` | 26 commits / **+27 lines, −0** | pure EOF appends — deploy order *is* line order; out-of-order merge would interleave migration order |

Merging **strictly in ascending PR number** (the order above) preserves every one of
these. Out-of-order merging is *not* just a conflict risk — it could silently corrupt
`sqitch.plan` deploy order or the LEDGER's state keys. Do not reorder.

---

## (c) Chain-integrity findings — the real conflicts

**Twelve head branches each carry exactly one pushed tip commit that no child PR was
stacked on.** A fix commit was appended to an already-stacked branch after its child
forked, leaving the child descending from the *pre-fix* tip:

| PR (head branch) | out-of-chain tip commit | content | merge-base with chain |
|---|---|---|---|
| #112 `p27-1` | `b2be2645` | `docs/tickets/DEFERRALS.md`: D-P27.1-1 status cell gains `(cites BL-056)` | `6982830b` |
| #116 `p27-5` | `4664bb24` | `docs/tickets/DEFERRALS.md`: D-P27.5-1 status cell gains `(cites BL-056)` | `b6ca7658` |
| #120 `p27-9` | `639b870d` | `web/package-lock.json` regen (npm 10) | `ddf3ad29` |
| #121 `p27-10` | `ca1c2529` | `web/package-lock.json` regen (npm 10) | `c6efd78b` |
| #122 `p28-1` | `b69f40e2` | `web/package-lock.json` regen (npm 10) | `e5b9cd14` |
| #123 `p28-2` | `0c0e2443` | `web/package-lock.json` regen (npm 10) | `e8dfc9f1` |
| #124 `p28-3` | `ef9a96fe` | `web/package-lock.json` regen (npm 10) | `82029bc1` |
| #125 `p28-4` | `79dee1b7` | `web/package-lock.json` regen (npm 10) | `58f90b03` |
| #126 `p28-5` | `400f67be` | `web/package-lock.json` regen (npm 10) | `48c78145` |
| #127 `p28-6` | `a671a85a` | `web/package-lock.json` regen (npm 10) | `0bf4f5c5` |
| #128 `p29-1` | `215d695e` | `web/package-lock.json` regen (npm 10) | `eccbd0a2` |
| #130 `p29-3` | `3015937c` | `web/package-lock.json` regen (npm 10) | `3addc79f` |

Mitigating facts verified in this inspection:

- **The ten `package-lock.json` regens are byte-identical to each other** (`git diff
  639b870d ca1c2529 … 3015937c` — empty). Both sides of each affected merge therefore make
  the *same* change — clean, which is why GitHub reports those PRs `MERGEABLE`.
- **Both DEFERRALS cell edits were already re-applied inside the chain** — the current
  file carries `(cites BL-056)` on both rows (plus later sweep annotations). Merging with
  the resolution "take the incoming PR's file" preserves the annotation.
- **PR #155's head regenerated `web/package-lock.json` differently** (`d6c562e5`,
  `@types/node` 26.6.2 → 26.6.3 in two nested entries — a 30-line diff vs the npm-10
  regen). The Round-10 chain's CI ran on the newer lockfile, so #155's version is the
  authoritative one going forward.

**Conflict simulation result** (bottom-up accumulation of the 75 current heads onto
`origin/main`, detached throwaway worktree, resolution = "take the incoming file" at each
conflict): conflicts at exactly **#113, #117 (`docs/tickets/DEFERRALS.md`) and #155
(`web/package-lock.json`)** — and the final accumulated tree is **byte-identical to
PR #187's head tree** (`51dcab808665dc64ce2fc4ba34f2cc3b6cf0760b`). The twelve fix
commits contribute zero net tree content; the chain already contains their effects.

> Caveat: the exact set of DEFERRALS conflict steps can shift depending on how the #113
> resolution is written (a naive union-merge can leave the file's tail in a state that
> re-conflicts at later append-boundary steps — observed at #114/#131/#141/#151 under a
> pure `merge-file --union` simulation). The prescribed resolution below — *take the
> incoming PR's file* — absorbs the divergence completely at the first conflict and is
> what produces the tree-identical result. If an unexpected step conflicts anyway, resolve
> the same way after eyeballing the file.

`merge_dryrun.sh` over the current stack (75 open PRs): **Pass A — every head merges
cleanly onto `origin/main` independently** (near-vacuous here: `main`'s tree equals the
fork tree, so each side is the only mover); **Pass B — bottom-up accumulation STOPS at the
first conflict (#113, `docs/tickets/DEFERRALS.md`)**, exit 1. The script's "expect 1
worktree" footnote is stale — other agents' worktrees legitimately exist; ignore the
count, read only the conflict table.

---

## (d) Gates and preconditions for the operator

Integration is itself a human/operator action (mergePolicy: NONE during the chain; HG-05
deferred per `readouts/GATE-G1.md`). Before running §(e):

1. **Chain complete** — rows 198–200 landed as PRs (this ticket's PR + P33.7 + P33.8) OR
   the operator explicitly chooses to integrate at the P33.6 boundary; either way the
   procedure is identical, only the top PR number changes.
2. **No gate is signed by merging.** Publication (`D-R10-PUBLISH-1`), source rights
   (HG-03), the human-evaluation spine, and every OPEN `DEFERRALS.md` row remain owed
   after integration — §(g) carries them forward.
3. **Environment:** clean checkout, `gh` authenticated, Docker running (post-merge
   `make test-db`/`tests/e2e`), Node/npm 10 for the web gate.
4. **Re-run the dry-run first** — the inspection above is a dated snapshot; new PRs or
   force-updated heads invalidate it.

---

## (e) The operator's procedure — copy-pasteable (bottom-up merge commits)

> Nothing in this block was run by P33.6. `main` is pushed only by the operator.

```bash
# 0. Fresh state + dry-run proof (must print RESULT: all N open PRs merge clean OR stop
#    only at the documented conflict steps below).
git fetch origin
git checkout main && git pull --ff-only origin main
sh docs/build/tools/merge_dryrun.sh        # read-only; compares against origin/main

# 1. Merge every open PR in ascending number order, keeping branches.
#    Retarget each PR's base to main explicitly right before merging it
#    (branches are never deleted, so GitHub does not auto-retarget).
for n in $(gh pr list --state open --json number --jq 'sort_by(.number)[].number'); do
  gh pr edit "$n" --base main
  gh pr merge "$n" --merge --delete-branch=false || {
    echo "PR #$n needs manual conflict resolution — see the conflict table and STOP."
    break
  }
done
```

**Conflict steps and their prescribed resolution.** When `gh pr merge` refuses
(`mergeStateStatus: CONFLICTING`), land that PR's head locally — the merge commit makes
GitHub mark the PR merged once pushed:

```bash
# For a conflicting PR <N> with head branch <H>:
git checkout main && git pull --ff-only origin main
git merge --no-ff "origin/<H>"          # conflicts — expected at exactly the steps below
```

| step (merge into `main`) | conflicted file | resolution |
|---|---|---|
| PR #113 (`devin/p27-2-maximize-publishable-scope`) | `docs/tickets/DEFERRALS.md` | `git checkout --theirs docs/tickets/DEFERRALS.md` — verified: the incoming file at `70137cef` already carries the `(cites BL-056)` annotations; then eyeball the tail rows |
| PR #117 (`devin/p27-6-ia-redesign-landing`) | `docs/tickets/DEFERRALS.md` | same — `git checkout --theirs docs/tickets/DEFERRALS.md` |
| PR #155 (`codex/round10-seed-after-p31-19`) | `web/package-lock.json` | `git checkout --theirs web/package-lock.json` — the Round-10 chain's lockfile (`@types/node` 26.6.3) is authoritative; verify with `npm --prefix web ci` |

```bash
git add -A && git commit                # completes the merge commit
git push origin main
# Optional belt-and-braces check after each resolution:
git diff "$(git rev-parse 'HEAD^2')^{tree}" 'HEAD^{tree}' -- <conflicted-file>   # expect empty

# Then resume: re-run the same ascending loop — `gh pr list --state open` picks up
# exactly the not-yet-merged remainder (GitHub marks the resolved PR merged on push).
```

If a merge conflicts on a file **not** in the table above: STOP — the inspection is stale;
re-run the dry-run and reconcile before continuing.

**Verification cadence:**

- After each conflict resolution (only those steps): `make check` once before pushing —
  a resolution error must never reach `main`.
- After the last PR merges, the full post-integration gate in §(h).
- Per-segment pause (optional): the five seed boundaries (#121→#122, #130→#131,
  #136→#137, #140→#141, #154→#155) are natural review checkpoints; CI on `main` runs
  `ci.yml` per push.

---

## (f) Rollback

Merges are `--no-ff` merge commits on `main`; undo is **revert, never reset/force-push**
(append-only, P1–P3):

```bash
# before pushing a bad in-progress merge:
git merge --abort

# after a pushed merge, newest merge first (each revert applies cleanly in reverse):
git log --first-parent --merges --oneline origin/main      # find the merge commits
git revert -m 1 <merge-commit-sha>
git push origin main
```

- Revert **in reverse merge order** (the topmost landed merge first).
- A mid-run halt is also safe: stop the loop; `main` is simply integrated up to the last
  merged PR and the remaining stack stays valid (each remaining PR's head still descends
  from the integrated prefix).
- **Withdrawal invariant (SIG-TRUST-006):** public access withdrawals apply even to
  historical releases and to rollback — reverting a merge must never re-expose a
  withdrawn artifact; the policy-controlled tombstone is the rollback path for published
  bytes, not byte deletion.
- Branches are never deleted (`--delete-branch=false`); re-integrating a reverted PR is a
  normal re-merge of the same head.

## (g) Post-integration operator actions — the owed register carries forward

Merging the stack changes **no** obligation's status. The full register lives in
`docs/tickets/DEFERRALS.md` (36 owed rows: 32 OPEN + 4 PARTIAL) with concrete RETURN PASS
commands in `docs/build/OPERATIONAL_READINESS.md` §(f3). Integration does not discharge,
sign, or bypass any of them. The Round-10-scoped obligations the operator keeps:

| obligation | owner of the next action | what it is |
|---|---|---|
| `D-R10-HUMAN-1` / `D-R6.1-EVAL` | human | the deferred S3 spine: re-enter at manifest row 184 — HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 (real reviewers, real labels; the evaluator stays `mode=shadow` until then) |
| `D-R10-LIVE-1` | hosted | hosted bounded recovery + snapshot freeze + production candidate (`prepared_not_executed` packet: `reports/p32.22-bounded-recovery/LIVE_RETURN_PASS.json`) |
| `D-P32.23a-1` | hosted | production release-candidate build on the frozen hosted spine (`reports/p32.23a-release-candidate/LIVE_RETURN_PASS.json`, `prepared_not_executed`) |
| `D-R10-PUBLISH-1` | human/public | **production exposure** — GATE-G3's signed scope covered only the bounded staging publication (ADR-144); a public release needs the full SIG-TRUST-009 criterion set |
| `D-R10-MEMORY-1` | human | single-writer closeout cutover — apply `contract/patch/1..3` per `docs/build/tools/CLOSEOUT_WRITER_PROTOCOL.md` at an operator-approved boundary |
| `D-R10-USERS-1` | human | independent usability sessions (`USABILITY_TASK_PROTOCOL.md`; nothing simulated counts) |
| `D-R10-SOURCES-1` | human→hosted | per-target HG-03 rights review + Part VIII preflight, then the four `prepared_not_executed` dossier/pilot passes: `D-P32.18-1`, `D-P32.19-1`, `D-P32.20-1`, `D-P32.21-1` |
| `D-P32.3-1` | human | reviewer session over `partner-name-audit` output — recorded dispositions for every legacy `sig.org.name` key |
| `D-P32.10a-1` | maintainer decision | `sqitch verify` whole-plan repair shape (the `=27` facet count vs 28 deployed facets) |
| `D-P32.16a-1` | maintainer decision | `sqitch revert` whole-plan repair shape (`revert/extensions.sql:7` postgis dependents) |
| `D-P32.16-1` | operator | intake receiver operating prerequisites (owner/staffing/retention/secrets/log-exclusions) before `[intake].operational=true` |
| `SIG-MEM-004` | engineering | scheduled chain work — **P33.8** (manifest row 200); lands *before* integration if the chain completes |
| carried-forward pre-R10 rows (18) | per row | HG-09 tokens, HG-08 MapRoulette/OE, source-rights lanes, federal sweep quota, P31-era return passes — each row's own `how to verify` cell + §(f3) command |

Also preserved verbatim: no agent ticks `HG-*`, flips `ingestion_permitted`, publishes,
deploys, or spends — integration changes none of that.

## (h) What to verify on `main` afterwards

```bash
git pull --ff-only origin main
# The tree-equality invariant — the strongest single check that integration was faithful:
git rev-parse 'HEAD^{tree}'            # == tree of the top merged PR's head
gh pr list --state open                # expect: none left (or only intentionally-open)
git merge-base --is-ancestor <top-head-branch> origin/main && echo ANCESTOR

make check                                             # full gate on the integrated tree
SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db          # Docker: claim spine
SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra     # Docker: composed stack
npm --prefix web run check                             # web gate (lockfile resolution step's proof)
python3 docs/build/tools/check_spec_src.py             # spec reproduction byte-identical
python3 docs/build/tools/check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv
python3 docs/build/tools/check_backlog.py && python3 docs/build/tools/build_backlog_md.py --check
python3 docs/build/tools/audit_current_state.py        # 0 errors (baseline conflicts documented)
make docs-check && bash scripts/docs/check-build-memory.sh .
uv run sig-ops composed-verify                          # the landed composed proof on main
```

Then confirm `main`'s CI run is green: `gh run list --branch main --limit 1` →
`gh run view <id>` (`ci.yml` triggers on push to main).

## (i) How this inspection was produced (reproduce)

```bash
gh pr list --state open --json number,baseRefName,headRefName,headRefOid,additions,deletions,changedFiles,isDraft,mergeable --limit 100
git merge-base origin/main HEAD                       # → 5b7fed0e
git rev-parse '3b913c6f^{tree}' '5b7fed0e^{tree}'     # → identical: d5b230f7…
gh pr view 113 --json mergeable                       # CONFLICTING (and #117)
git merge-base --is-ancestor <each head> HEAD         # 11 out-of-chain tip commits found
sh docs/build/tools/merge_dryrun.sh                   # Pass A clean; Pass B stops at #113
# + a detached-worktree bottom-up accumulation with --theirs resolution at each conflict
#   → conflicts at #113/#117 (DEFERRALS.md) + #155 (package-lock.json);
#     final accumulated tree == PR #187 head tree (51dcab80…)
```

All operations were read-only against every real ref: `git fetch` (remote-tracking refs
only), throwaway detached worktrees under `/tmp` (removed), `gh pr list/view`. No merge,
tag, push to `main`, branch deletion, or force-push was performed.
