# Independent review: S3 evaluation and S1 evidence integrity

Reviewed 2026-09-25 in the isolated planning worktree. Scope: `DESIGN.md`, `PLAN.json`, S1/S3 research, ADR-105, P31.10/P31.11 contracts, and selected persistence/evaluation/materialization code. These are planning-contract findings, not claims that the proposed implementation has already failed. Plan edits were occurring concurrently; anchors below use ticket IDs and quoted obligations rather than unstable line numbers.

## Findings

### ER-1 — P1: explicitly own the transition from the existing point gate to the human gate

**Evidence.** P32.10 implements “fail-safe per-tier demotion”; P32.22 depends on it and performs production activation/rematerialization; HUMAN-H4 comes afterwards; P32.23 then owns measured rules activation. S3 §12 says the new gate “remains inactive until measured ADR authority,” but neither P32.10 nor P32.22 carries that activation condition. The existing `resolution/src/resolution/camera_sites.py::decide_auto_write_tiers` directly gates each run using point precision and sample size; ADR-105 §5 authorizes that provisional behavior. It is not already a certificate consumer.

**Consequence.** Deploying P32.10 at P32.22 can either switch all tiers to an unmeasured new gate before HUMAN-H4, or silently keep using the old point gate while presenting the new eligibility contract as active. A snapshot result also must not become a perpetual certificate for new pairs/source mixes merely because the rules version is unchanged.

**Correction.** Make P32.10 explicitly shadow-only until a recorded activation decision. Assign P32.22 an explicit legacy/provisional or review-only operating mode, with its authority and disclosure. P32.23 must own a versioned activation artifact that binds protocol, rules, population/frame, label watermark, evaluation result and allowed scope. Runtime must reject reuse outside that scope and emit a structured provisional/review-only disposition. Add an integration acceptance case for P32.22 before any human label and for a changed deployment frame after a scoped pass. This clarifies activation; it does not ask this review to choose a new policy.

### ER-2 — P1: disambiguate baseline assessment, tuning and final unsealing

**Evidence.** P32.23 says “consume the signed sealed campaign, assess existing rules before any change, and tune only on training/calibration data if warranted,” followed by evaluating a new candidate on the untouched holdout. S3 §5 correctly requires rules authors to receive only training/development labels until freeze and the final result to be unsealed once. S3 §8 correctly prohibits selecting a threshold on final results.

**Consequence.** The ticket can be read as assessing the existing rules on final labels, deciding from that result whether a change is warranted, then certifying the changed rules on those same labels. Tuning parameter values on training alone does not undo a model-selection decision prompted by the final result.

**Correction.** State that the pre-change assessment and decision to tune use training/development only. Freeze the candidate and all confirmatory comparisons before any final result is exposed. If baseline and candidate are both evaluated at final unsealing, preregister that comparison/decision family and do not select an unregistered follow-on candidate. A failed final result requires new untouched dependency groups for a subsequent tuned version. Assign custody/release authority and acceptance checks to P32.9/HUMAN-H4/P32.23 explicitly.

### ER-3 — P2: give the independent-label physical schema and isolation tests a ticket owner

**Evidence.** P32.9 promises to persist labels separately from operational decisions, but its paths name resolution/API code and a historical draft; it contains no explicit DB migration, schema-inventory ADR, access-control or import/correction contract. S3 §6 calls for a durable campaign/sample/reference-label log and DB-assigned knowledge times, and §11 requires real-PG isolation and append-only tests. Existing `db/deploy/review_queue.sql` supports only accept/reject decisions; its reviewer field and decision vocabulary do not implement campaign membership, independent rounds, attestations, immutable probabilities or sealed-label custody. The existing generic gold set is a pure object/file contract, not this storage layer.

**Correction.** Assign P32.9 the additive sqitch deploy/revert/verify and necessary ontology decision, with `db/`, relevant generated-schema source, and tests in scope. Specify ownership of campaign/sample/packet/label/attestation and superseding-label records, immutable inclusion accounting, idempotent import, label watermark and access roles. Test direct storage/API access, not only hidden UI fields: reviewers must not read other initial votes or model-only manifest fields, rule authors must not obtain sealed labels, and neither label import nor evaluation may create operational decisions.

### ER-4 — P2: explicitly rebuild/freeze the campaign frame after integrity recovery

**Evidence.** P32.9 prepares immutable preregistration and sealed sample IDs using P32.2/P32.3, without depending on P32.4/P32.5. P32.22 subsequently repairs semantic/provenance state and rematerializes; HUMAN-H4 consumes the prepared campaign after P32.22. S3 §7/§8 defines precision over a frozen eligible edge population and §10 requires a frame date; no ticket currently explicitly owns the post-recovery frame reconciliation.

**Consequence.** Repairs to coordinates, identities, lineage, publication eligibility or evidence availability can change frame membership and labels after preparation. An otherwise valid old-frame estimate cannot be silently presented as an assessment of the repaired release candidate. Replacing only the newly difficult sample items would also bias the sample.

**Correction.** Keep early P32.9 packets as tooling/pilot output. At the P32.22→HUMAN-H4 boundary, name the owner who fixes the actual temporal/semantic/publication snapshot, verifies dependency groups and freezes the final frame, probabilities, packet digests and candidate predictions. If the old frame is deliberately retained, report and enforce that narrower scope. Changed frames require a new complete draw/version before labels; unavailable selected items remain in accounting.

### ER-5 — P2: promote the occurrence and recurring-run invariants into concrete acceptance contracts

**Evidence.** S1 §4.2 requires bindings with DB-recorded knowledge time and multiple locators, and §4.3 requires an execution completion even when a prior input state recurs. P32.2 tests two *different* captures in one run but not identical bytes acquired twice; P32.4 tests A→B→A values but does not explicitly require an existing-result completion reference. Existing `claim_evidence` has primary key `(claim_id, capture_id, role)` and no `recorded_at`. Existing `camera_sites_pg.py:324–327` ignores a reused `run_key`, while its reader at line 375 selects the latest stored completion. ADR-105 explicitly records the recurring-input limitation.

**Consequence.** A digest/head-sidecar implementation can satisfy the abbreviated ticket tests while conflating two acquisitions of identical bytes. A value selector can also pass while the public “latest completed run” still points at B after a return to an already-computed A.

**Correction.** P32.2 should own immutable occurrence identity/version, binding knowledge time, and multiple-locator cardinality, including identical bytes at distinct retrieval times/URIs and late binding of old bytes. P32.4 should explicitly own an additive per-execution completion/reference contract (or an equivalent proven selector), testing exact A-result reuse after B while preserving result idempotence. Include real-PG past-belief and export-reader checks. If landed P31 already solves either seam, P32.1 should record that evidence and retain regression ownership.

### ER-6 — P2: the integrity audit’s semantic denominator can exclude unresolved cases

**Evidence.** S1 §6 defines semantic fidelity as supported adjudicated claims divided by “sampled claims adjudicated,” while the preceding paragraph calls a finding unresolved whenever a necessary evidentiary step cannot be established. P32.6 only requires audit denominators to reconcile. This is weaker than S3’s explicit rule that missing/insufficient outcomes remain adverse or inconclusive for certification.

**Consequence.** An audit of 400 claims with only 40 completed, supported adjudications can report 100% semantic fidelity while 360 unresolved claims disappear from that metric. A conditional statistic is permissible, but cannot substantiate corpus support/reproducibility without its completion denominator and uncertainty.

**Correction.** Require weighted totals for every original sampled unit and outcome, labelability/completion, conditional fidelity explicitly labeled as such, and an all-sampled verified-support yield or unresolved best/worst bounds. Missing, restricted and packet-failure cases cannot be replaced or excluded to improve an acceptance result. Assign this to P32.6 and the P32.22 audit report; targeted cases remain a separate set.

## Checks that did not produce findings

- The all-success independent-binomial examples are correct: the one-sided lower limit is `alpha**(1/n)`; 149 at alpha .05 and 183 per tier at alpha .025 clear .98. They are explicitly best-case examples, not a universal 400-item budget or power calculation.
- S3 correctly distinguishes finite-population SRS/hypergeometric inference from independent-event/binomial inference. Shared content does not alone invalidate a true finite-population SRS; clustered sampling needs its actual design. Preserve this distinction when implementing P32.10’s abbreviated “exact/binomial” wording.
- S3 correctly separates pair precision, blocker recall and cluster quality; candidate-only truth is not whole-corpus recall. The current ADR-105 70/70 and 69/70 figures are disclosed point-gate history, not independent human certificates.
- Independent humans, agents, reference labels, operational accept/reject and public correction submissions are appropriately separated in the research. P31.10/P31.11 must not be treated as completed human evaluation merely because their engineering works.

## Review limits

Read-only inspection plus this review file only; no tests, service runs, hosted reads/writes, live acquisition, deployment or external messaging. No new web evidence was necessary. Statistical identities were checked analytically; numerical estimator code was not executed. This review did not measure actual label independence, holdout overlap, historical evidence availability, publication exposure or the final accepted P31 behavior. Those remain explicitly owned implementation/audit work. Historical ADR bodies and active checkout state were not modified.

## Bounded closure recheck — 2026-09-25

Read the amended PLAN/DESIGN, S1 denominator appendix, relevant rendered P32 tickets, HUMAN-H4, HANDOFF, REQUIREMENTS ownership rows and canonical §55 source. This recheck addresses ER-1–ER-6 only and does not certify implementation. No tests or live actions were run.

| Finding | Planning resolution | Evidence |
|---|---|---|
| ER-1 | Resolved at planning level | P32.10 deliverable 4 explicitly keeps the evaluator shadow/inactive; P32.22 records the existing provisional policy and any separately authorized demotion. P32.23 owns the post-human measured decision. New P32.23a regenerates all artifacts after that decision and stops on an evaluation-relevant input change. DESIGN’s final sequencing and HANDOFF agree; §55.1 now states shadow-only rollout. |
| ER-2 | Original unsealing ambiguity resolved; one related sequencing issue remains below | P32.23 deliverables 1–2 now require baseline assessment/choice from training/calibration only, a pinned candidate/hypothesis family before unsealing, one final use, and preregistered extra comparisons. The rendered contract matches. |
| ER-3 | Resolved at planning level | P32.9 explicitly owns additive campaign/sample/assignment/attestation/label/adjudication schema and migration, PG/RLS access, hashes and watermark. Its real-PG acceptance covers role isolation, supersession, denominator persistence and sealed-label isolation from clustering. The required S3 research supplies detailed schema/import semantics. |
| ER-4 | Repaired-snapshot issue resolved; candidate-frame ordering remains below | P32.9 now prepares tooling only; P32.22 freezes the repaired snapshot, and HUMAN-H4 instantiates the final campaign after it. The final release is rebuilt by P32.23a, not copied from the pre-evaluation preview. |
| ER-5 | Resolved at planning level | P32.2 explicitly tests identical bytes with two immutable acquisition occurrences; P32.4 owns per-execution completion/result references and tests exact prior-result reuse after B with idempotent retry. Both additions appear in rendered tickets; required S1 field contracts retain binding knowledge time and multiple-locator requirements. |
| ER-6 | Resolved at planning level | P32.6 now requires all-sampled semantic support with unresolved units not established, alongside conditional fidelity and yield. S1’s appended correction requires weighted/cluster-aware reporting of those distinct estimands and forbids displaying conditional fidelity alone. |

### Remaining P1 — freeze the candidate before drawing its confirmatory edge frame

The revised HUMAN-H4 still draws and completes the final campaign **before** P32.23 chooses/freezes the candidate. The S3 §7 precision estimand is the set of eligible auto-positive edges produced by the frozen rule, partitioned by its tiers. A new candidate chosen after the draw can add positives or change tier membership that had zero or different inclusion probability in the sampled baseline frame. Keeping final labels secret prevents outcome leakage but does not make that sample representative of the newly selected candidate.

Resolve this within ER-2/ER-4 by placing the development-only candidate choice/freeze checkpoint **before** HUMAN-H4’s final frame construction and draw. For example, HUMAN-H4 can first complete development/pilot work, have the authorized implementation owner freeze the candidate using development evidence only, and then instantiate and label the candidate-specific confirmatory sample; P32.23 subsequently verifies/consumes that already-frozen candidate and unseals once. Alternatively define a preregistered union frame with valid positive inclusion probability and an appropriate estimator for every candidate allowed later; the current plan does not specify that more complex design. Require a changed candidate/frame to stop before final draw or trigger a new untouched campaign, and carry the same order into PLAN, rendered contracts, DESIGN/HANDOFF and §55’s sequence.

## Final closure recheck — candidate-specific campaign split, 2026-09-25

The remaining ER-2/ER-4 P1 is **resolved at planning level**. Verified the final order and actual rendered contracts: `184_HUMAN-H4__human-development-and-dossier-review.md` supplies development labels only; `185_P32.22a__candidate-and-confirmatory-frame-freeze.md` chooses/freezes the candidate before constructing its eligible edge/tier frame and drawing the sample; `186_HUMAN-H5__blinded-confirmatory-human-campaign.md` supplies independent final labels; `187_P32.23__human-evaluation-and-rules-decision.md` consumes that exact candidate and sealed campaign once; `188_P32.23a__post-evaluation-release-candidate.md` rebuilds all artifacts after the measured decision. The frozen-rule/frame/sample identities and human gate dependencies align in PLAN, DESIGN, HANDOFF, §55 and REQUIREMENTS. SIG-EVAL-007 has the explicit P32.22a owner and changed-positive/stale-frame rejection acceptance case; SIG-EVAL-005 now prohibits post-unseal candidate reuse.

All six findings are addressed at the planning-contract level; **no substantive P1 remains within this review’s bounded scope**. One wording cleanup was reported to the author: P32.10 deliverable 4 still says “post-HUMAN-H4 decision” and should say “post-HUMAN-H5 measured P32.23 decision.” The actual P32.23 gate already requires signed HUMAN-H5, P32.22a forbids production activation, and the surrounding design preserves shadow mode until the measured decision, so this is a stale cross-reference rather than an unresolved activation design.

This closure verifies contract alignment only. It does not supply reviewers, labels, confidence certification, production authority, tests or implementation evidence. The original findings and intermediate status are retained above as review history.
