# ADR-116 — Human review decisions into camera-site clustering, and evidenced duplicate-target lineage (the design's ADR-R9-HUMANER)

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.11 (`docs/tickets/P31.11__review-decisions-into-clustering.md`) — Round 9 `DEEPEN.7`. Closes deferral **D-P30.2b-3**; advances (does not close) **D-P30.2b-1**.
- **Date:** 2026-10-02
- **Related:** ADR-105 (the camera-site ER pipeline and its hard constraints — this ADR amends
  constraint (a) with ONE evidenced exception), ADR-099 (the measured eval loop — human edges are
  outside it, deliberately), ADR-110 (the identity guard; it left `er_match:identity_duplicate:*`
  decision semantics to this ADR), ADR-103 (`sig_materialize`), spec §14.6–14.7
  (SIG-IDENT-020/024/025/026/027/028/029), SIG-IDENT-032 (public-id lifecycle), §27
  (SIG-RECON-001/002); deferrals **D-P30.2b-1** (OPEN — the Round-10 verify), **D-R6.1-EVAL**
  (OPEN); backlog home **BL-057**.

## Context

P30.2b routed 11,625 camera-site proposals to `review_item`, and P31.10 built the review
surface (the sampler, the campaign tag, the curation read) — but nothing *consumed* the
append-only `review_decision` rows: `review_pg.py` deliberately "records a decision; it has no
path that mutates the graph". A curator's accept had no way to become a merge, a reject had no
way to forbid one, and constraint (a) forbade merging two records of one source even when the
second record was provably the same published row (a source republishing its own layer under a
second ArcGIS target — the `camreg_ucsd` case of D-P30.2b-3).

The ticket is explicitly re-scoped: the run consumes whatever decisions **exist** — on hosted
today that is expected to be **zero** camera-site decisions — and must be proven correct with
zero, not gated on a review campaign (the Round-10 campaign and the hosted verification of real
accepted decisions belong to D-P30.2b-1).

## Decision

1. **The fold.** Each camera-site run reads the append-only history — every
   `er_match:camera_site*` review item (proposals `camera_site:`, gold-disputed items
   `camera_site_disputed:`, and the new routed-back `camera_site_conflict:` family) binds a
   pair via its immutable `payload.left`/`right`; every `review_decision` row on those items is
   a vote. `fold_human_verdicts` folds the history to **one verdict per pair**: an item's
   verdict is `accept` iff every decision on it accepts, `reject` iff every decision rejects,
   else `conflict`; a pair's verdict is its **most recently decided** item's verdict — so a
   clean adjudication on a routed-back item supersedes an earlier conflicted proposal — and a
   timestamp tie between disagreeing items is itself a conflict, never a coin-flip. Items with
   no decisions produce no verdict ("no decision → stays proposed"; the schema has no `unsure`
   value and P31.10 writes nothing for it). A verdict over a pair absent from the run's records
   is counted (`unmatched_pairs`) and recorded nowhere.
2. **Semantics.** `accept` is a human `same_as` edge — disposition `human_accept`,
   `decided_by` the curator — applied under the **same hard constraints** as an automatic edge.
   `reject` is a recorded hard cannot-link — disposition `human_reject`,
   `relation_type = 'cannot_link'` — and the pair never clusters (also not by a duplicate-target
   edge on the same pair: the verdict is decided first). `conflict` stays `proposed`
   (reason `human_conflict`) and is routed back to review under a
   `er_match:camera_site_conflict:` item carrying the disagreeing history. An accepted edge
   that would violate a constraint — constraint (a) same-source, the recorded incompatible
   device classes, the span/size bounds — is **recorded `refused`** with the constraint named
   in `disposition_reason` and never applied (recorded and refused, never silently merged).
   Soft conflicts (b) are what review exists to decide: a human accept **may** apply across
   them. Cluster-shape alerts demote *automatic* edges of an alerted cluster, never a human
   accept — the human already reviewed that pair.
3. **Precedence.** A pair with any human verdict takes the human outcome whatever the
   automatic tier would have said — the verdicts are applied to the union-find **before** the
   automatic edges. The precedence is semantic, not "latest decision wins": a curator's reject
   beats a measured auto-write tier; a later automatic re-assessment never overrides a decision.
   Human edges are **outside the measured eval loop** (ADR-099): a human verdict is a decision
   recorded by an accountable reviewer (SIG-IDENT-026), not a candidate the holdout scores — the
   eval measures the automatic tiers, and the human counts are reported in the run summary.
4. **Zero-decision equivalence (test-pinned).** With no votes the fold yields no verdicts, no
   tier-0 edges change, and the run is byte-identical to the pre-wiring pipeline — same
   decisions, same clusters, and the same `run_key` (the verdict list is a `run_key` input; the
   empty list is the pre-wiring value).
5. **P31.3 identity decisions stay separate.** `er_match:identity_duplicate:*` items are a
   different queue with different pair semantics (entity-identity, not site geometry); they are
   excluded from the camera-site item prefix and never reach this fold. Identity-triage accepts
   record `same_as` through `PgReviewQueue`/`organization_relation` as ADR-110 already does.
6. **Duplicate-target lineage (closes D-P30.2b-3).** `infer_duplicate_targets` groups records
   of ONE source that are provably the same published row: **row-identical** (the whole
   projected row equal — normalised ref, coordinate pair, name, roadway, direction, operator,
   jurisdiction, type — AND carrying an identifying field, so content-free stubs never group),
   or **proven duplicate targets** (the two records' targets, parsed from their
   `sig.connector.subject` values, are proven duplicate because the captures their claims cite
   share a `content_digest` — byte-identical fetched content — AND the records share the same
   normalised upstream reference). Group members count as ONE effective record under
   constraint (a) — the union-find's same-source test, the one-to-one neighbour counts, and the
   `same_source_cluster` alert all compare effective identities `(source, group-root)` — and
   each non-root member gets a recorded tier-0 `duplicate_target_of` decision
   (`auto_write`; tier 0 is outside the measured candidate tiers because the merge is evidence,
   never a statistical call). Two records of one source with different rows — different
   references, different names — remain genuinely distinct devices and never merge: the
   exception exists only with that evidence.
7. **Schema (sqitch `camera_site_human_decisions`).** Additive only: the `camera_site_match`
   `disposition` CHECK widens to `auto_write | proposed | human_accept | human_reject |
   refused`, `relation_type` admits `cannot_link`, and `sig_materialize` gains `SELECT` on
   `review_decision` (it already had `INSERT` for the curation path). No UPDATE/DELETE anywhere;
   the revert refuses loudly if human-decision rows exist (reverting the CHECK would falsify
   append-only history).
8. **Run accounting and the export.** `camera_site_run.summary.human_review` records the
   folded verdict counts (accepts / rejects / conflicts / unmatched pairs), the applied and
   refused accept edges, the cannot-link count, how many resolved clusters carry a human edge,
   and `proposed_awaiting_review`; `duplicate_target_groups`/`_records` record the lineage.
   Public ids are stable: a cluster's id stays the smallest member subject id, and a re-run
   over unchanged inputs is +0 (test-pinned). The export's resolved-site seam unions
   `auto_write` + `human_accept` edges; the metric counts both and discloses the proposals
   still awaiting review, the cannot-links and the refusals — named denominator and
   `is_population_total = false` unchanged.
9. **What this ADR does NOT do.** It does not run a review campaign, does not create decisions,
   and does not verify real accepted decisions clustering on hosted — that verify is the
   Round-10 item recorded on D-P30.2b-1. Hosted this run consumes **zero** decisions by design;
   the zero-decision equivalence and the duplicate-target delta are the measured evidence.

## Consequences

- A curator's accept lands in the next materialization as a recorded `human_accept` edge —
  attributable (`decided_by`), constraint-checked, and counted in the run summary; a reject is
  a durable `cannot_link` the pair can never merge around.
- The eval's integrity is preserved: human edges are not scored by the holdout and do not
  change which tiers auto-write; the summary reports both populations separately.
- The `camreg_ucsd`-class duplication — one row republished under two targets of one source —
  merges on evidence only; the metric's N falls by exactly the duplicate records, disclosed as
  `duplicate_target_*` counts. Distinct devices at one point (the common pole/intersection
  case) are untouched.
- Hosted, today: expected zero human verdicts — the run must equal the pre-wiring run apart
  from measured duplicate-target merges; +0 on re-run.

## Alternatives considered

- **Apply decisions inside `PgReviewQueue.decide`** (write the graph at decision time).
  Rejected: review must stay a recording surface (SIG-IDENT-026); making the *run* consume the
  append-only history keeps decisions reproducible, re-clusterable and idempotent — the same
  posture as every other materializer.
- **Latest single decision wins at pair level.** Rejected: it would let one later click
  silently erase a disagreement. The fold preserves the history: consistent repeated accepts
  hold; accept-then-reject is a `conflict` routed back, not a silent flip.
- **Auto-apply accepts without constraint checks.** Rejected: constraint (a) exists because a
  source can list two devices at one point; a misread accept must be recordable *and* refused.
- **Merge duplicate targets at ingest** (one subject per row). Rejected: the historical rows
  and their identifiers already exist (SIG-IDENT-032 stability); a decision layer records the
  lineage without rewriting ingest.
- **Treat duplicate-target pairs as ordinary tier-1 candidates.** Rejected: the merge is not a
  probabilistic same-device judgement — it is proven one-row lineage; scoring it on the holdout
  would either auto-write it unconditionally or bury a fact of capture identity.

## Revisit trigger

Revisit when any of: (a) the Round-10 review campaign produces real decisions — verify real
accepted decisions clustering on hosted and re-measure (D-P30.2b-1, with P31.18); (b) a curator
rejects a pair the duplicate-target evidence merged, or accepts what a constraint refused, often
enough to suggest the evidence or the constraint is wrong; (c) a source republishes under targets
whose bytes differ trivially per fetch (the identical-digest test then misses real duplicates —
widen to canonical row fingerprints); (d) conflict items accumulate unanswered (the routed-back
family needs its own adjudication path or quorum rule); (e) a second ER domain wants the same
fold — lift `fold_human_verdicts` into the shared review layer; (f) SIG-IDENT-032 public ids ever
need run-independent stability beyond "smallest member subject id".
