# S3 — Independent human reference labels and defensible resolution evaluation

Date: 2026-09-25. Research/design only. Baseline: 0e57e6461d6a5db2e8e0042464750ce2ea65db5e in the isolated codex/sig-six-stream-research worktree; P31.8 implementation is present, later P31 tooling is contractual. Revalidate against the accepted P31 integration tip before implementation. This document neither supplies human labels nor changes the current auto-write rules, disclosure, or orchestrator state.

## 1. Decision summary

Build the protocol, label storage, blinded evidence view, sampling manifest and evaluator first. Run a human campaign only when independent reviewers and an adjudicator are actually available. Then record a measured rules/publication decision in a new ADR. These are three distinct deliverables; successful tooling cannot close a human-evaluation obligation.

The recommended design has five core boundaries:

1. Operational accept/reject decisions change clustering. Reference labels answer whether two records represent the same defined object. They are separate append-only records; an operational rejection is not necessarily evidence that two devices differ.
2. Two independent humans assess identical evidence packets, blind to model outputs and each other's labels. A third resolves disagreements where possible; uncertainty remains a recorded outcome.
3. Training, development and final evaluation are split by dependent record/entity neighborhoods and source lineage before labels are exposed to rule authors. The final holdout is sealed. Tune on training/development only, freeze rules, and evaluate once.
4. Auto-positive precision, candidate-generation recall, and final-cluster quality have different sampling frames and denominators. A queue of uncertain candidate pairs measures none of these for the whole graph by itself.
5. A proposed 0.98 gate uses a preregistered lower confidence bound with multiplicity control and a fixed stopping rule, not a point estimate. Missing, disputed or insufficient-evidence outcomes cannot silently leave the denominator. The population to which the bound applies must be explicit.

The immediate success criterion is an independently reproducible evaluation packet and an honest readiness state. No reviewers were recruited, contacted or invented for this research.

## 2. Evidence and source register

Classes: C = inspected pinned code/contract; R = committed historical report, not rerun; W = primary research or official methodological documentation read 2026-09-25; X = bounded pure arithmetic; I = proposed design. Only the two assigned research documents have been written by this stream. No hosted reads/writes, connector runs, service tests, model annotation, messages or paid work occurred.

### Repository evidence

| ID | Source / anchors | Supported finding |
|---|---|---|
| R1 C/R | docs/adr/ADR-105-geospatial-camera-site-entity-resolution.md §5 and Consequences | Current camera-2 holdout is agent/maintainer-verified, LLM comparison is disclosed; 70/70 and 69/70 gate by point estimate with minimum 50; human evaluation remains provisional. |
| R2 C | resolution/src/resolution/camera_sites.py:1025 TierMeasurement; :1053 measure_tiers; :1087 decide_auto_write_tiers; data/camera_site_rules.toml:173–183 | Wilson bounds are reported but not used for promotion; explicit NEI counts against strict precision; absent labels are skipped by measure_tiers. |
| R3 C | resolution/src/resolution/gold_set.py GoldLabel/Adjudication/GoldSet; :260 _freeze_holdout; :268 build_gold_set | Existing three-way vocabulary, provenance and immutable holdout machinery; generic split samples pair IDs rather than dependency groups. |
| R4 C | resolution/src/resolution/eval_loop.py _gold_partitions/tier_precisions_on_holdout; quality_gates.py | Generic evaluator uses labeled match/non-match pairs and omits disputed/unlabeled outcomes; it is not a design-weighted human certification evaluator. Camera strict behavior is different and must not be conflated. |
| R5 C | docs/tickets/P31.10__camera-site-review-surface.md Goal/In scope/AC; db/deploy/review_queue.sql:37–49 | Planned operational UI exposes matcher tier/score, writes accept/reject and leaves unsure pending without a decision. Default ~400 is tooling for a later campaign, not a completed campaign. |
| R6 C | docs/tickets/P31.11__review-decisions-into-clustering.md | Accept/reject becomes human same_as/cannot-link; zero decisions must be valid; operational conflicts and hard constraints retain precedence. |
| R7 C | docs/build/reports/round9-drafts/P31.18__resolution-eval-from-first-principles.md; docs/tickets/DEFERRALS.md D-R6.1-EVAL, D-P30.2b-1/-2 | Human campaign and rules v3 remain future work. Draft wording about retuning against a human holdout needs precise replacement; historical ADR bodies stay unchanged. |
| R8 C/R | docs/build/reports/P28.1_resolution_eval.md; camera_site_gold.json; ADR-099 | Existing reported evaluations and learning artifacts are useful training/baseline evidence, not independent human truth. |
| R9 I/C | research/S1-evidence-integrity.md in this planning directory | Exact capture packets, observation context and lineage are prerequisites for reliable labels. Unavailable evidence must be visible to evaluators. |

### External sources, accessed 2026-09-25

| ID | Primary source | Limited application |
|---|---|---|
| W1 | [NIST exact binomial confidence limits](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm) | One-sided exact binomial bounds; small-error samples need appropriate intervals. The sample-size arithmetic below is derived here, not a NIST recommendation for SIG. |
| W2 | [How to Evaluate Entity Resolution Systems: An Entity-Centric Framework, research paper](https://arxiv.org/html/2404.05622v1) | Population-aware evaluation and reference-cluster sampling can detect under/overclustering and estimate several metrics. We adapt the principles; the paper's labeling procedure can reveal predicted clusters, whereas SIG proposes stronger blinding for its reference stage. |
| W3 | [Menestrina, Whang and Garcia-Molina, Evaluating Entity Resolution Results, PVLDB 2010](https://www.vldb.org/pvldb/vol3/R18.pdf) | Pairwise and cluster measures can rank results differently; metric choice should reflect application harm. No single F1 score settles SIG's false-merge risk. |
| W4 | [Cochrane DTA, sources of bias](https://www.cochrane.org/sites/default/files/learning_modules/DTA_modules/6.1_Sources_of_bias/story_html5.html) | Methodological analogy: selection, reference verification and outcome-aware interpretation can bias accuracy estimates; predefine thresholds and blind interpretation. This is not medical guidance or a claim that camera identity has a perfect reference standard. |
| W5 | [CDC/NCHS NHANES variance-estimation tutorial](https://wwwn.cdc.gov/nchs/nhanes/tutorials/varianceestimation.aspx) | Unequal weights, strata and sampling clusters affect uncertainty. Use a design-aware estimator; this is a statistical principle, not an instruction to use NHANES-specific weights. |
| W6 | [Statistics Canada, probability sampling](https://www150.statcan.gc.ca/n1/edu/power-pouvoir/ch13/prob/5214899-eng.htm) | Define a probability frame and selection procedure; targeted cases cannot silently stand in for a probability sample. |
| W7 | [Hypergeometric Distribution Revisited: Tail Inequalities, Confidence Bounds and Sample Sizes](https://arxiv.org/abs/2405.06722) | Finite binary populations sampled without replacement require finite-population inference rather than a reflexive independent-binomial claim. |
| W8 | [Confidence sequences for sampling without replacement](https://arxiv.org/abs/2006.04347) | Optional stopping has a separate statistical treatment. SIG's initial protocol should use a fixed sample/analysis, not implement a sequential method casually. |

Methodological proposals below are SIG-specific engineering designs, not direct requirements of these sources. No numerical human performance is inferred from a standards citation.

## 3. Corrections to earlier framing and current contracts

### What SIG already does correctly

ADR-105 explicitly discloses provisional agent labels, distinguishes LLM sensitivity figures, retires a diagnosed holdout to training, keeps NEI adverse to the camera strict gate, and declines automatic proximity-only merges. The camera gate requires minimum evidence and fails a tier with no holdout measurement. Existing gold labels already support match/non_match/not_enough_information. These are useful foundations; a claim that the project has no evaluation or silently presents agent labels as human truth would be wrong.

Its recorded 1g 70/70 and 3g 69/70 are point estimates, not evidence that each true precision is at least 0.98 with 95% confidence. ADR-105 reports two-sided Wilson lower bounds approximately 0.948 and 0.923 and remains PROVISIONAL. This design does not replace those historical numbers. It proposes a new gate decision with its own date and evaluation population.

### Gaps the next contracts must address

- P31.10's score/tier/conflict evidence is useful for operational triage but reveals the answer under assessment. A blinded reference-label mode is a separate projection and workflow, not simply a renamed campaign tag.
- Operational unsure is deliberately not persisted as a decision. Reference insufficient-evidence MUST be persisted, along with absence/noncompletion, so difficult cases do not vanish from a denominator.
- Camera measure_tiers skips label=None. The generic evaluator also conditions on decided labels. Preserve those legacy semantics for old reports; add an explicitly versioned certification evaluator over the original sampled manifest.
- Pair-level random splitting can share a record, entity neighborhood, mirrored source family or reused evidence across train and test. This is a leakage risk, not a finding that the published holdout's exact overlap has been measured here.
- P31.18 is a skeleton, not a runnable campaign. Replace its future contract with: derive rules on training/development labels; freeze rules and candidate-generation code; then evaluate on a sealed, separately sampled final human holdout. If inspected to diagnose errors, retire that holdout to training and obtain a new final set. Do not claim validation by retuning until the same holdout passes.
- Neither reviewer availability nor final campaign size/stratum composition is known. The ~400 default is a workload starting point. It cannot be a universal confidence certificate across 1g/3g/4g/5g, conflict/disputed buckets, geography and source lineages.

## 4. Define the identity question before asking humans

Use a versioned reference rubric independent of the matcher's thresholds. The current camera_site_rules.toml explicitly defines a resolved site as records of the same physical device. Therefore determine whether records refer to that same device at a compatible observation period, and state any deliberate site-level aggregation separately. A pole, intersection, facility, stream endpoint, registry row and device are not interchangeable. Changing the target to a site would require a new ontology/rules decision and revised question/count interpretation before labeling; do not blend site and device truth in one gold set.

Required outcomes:

| Label | Meaning | Minimum rationale |
|---|---|---|
| same | Positive evidence supports the same defined identity, including temporal compatibility | Cited IDs/lineage or source evidence that distinguishes a device from its neighbors; exact coordinates alone are insufficient. |
| different | Positive evidence supports distinct identities or an incompatible identity claim | Distinct simultaneously operating devices, incompatible authoritative IDs, non-overlapping object definitions, or other cited distinguishing evidence. Distance alone may be insufficient for mobile/replaced assets. |
| insufficient_evidence | Available evidence cannot decide under the rubric | Missing capture, ambiguous shared label/ref, coarse coordinates, unclear device-vs-site, temporal replacement uncertainty, or unresolved source conflict. |

Absence of an inventory entry is not by itself proof of different. A mirror can establish that records are copies of one source observation without providing independent confirmation that the real device exists. Record `reference_basis=source_record_identity|physical_identity|site_identity` and evaluate only the basis the endpoint claims. Treat device replacement and historical moves under a documented identity/time rule. A name containing different device kinds should trigger evidence review rather than a fabricated physical survey.

No person-level labels or precise coordinates beyond the curator's existing authorized tier are introduced. If protection rules remove information essential for a decision, use insufficient_evidence; do not defeat the protection to obtain a binary label.

## 5. Human independence, blinding and adjudication

### Roles and readiness

The campaign needs two actual human reviewers per item and an adjudicator for unresolved disagreement. Prefer reviewers who did not author the candidate rule or operational decision for the item. A campaign custodian controls the sealed membership and final labels; a method reviewer signs the analysis manifest. One person can perform administrative roles if separation and access limits are documented, but the same person's repeated labels are not independent humans. If these roles cannot be staffed, mark human campaign waiting; deliver engineering and leave the measured closure open.

Reviewers record pseudonymous IDs, qualification/training completion, conflicts of interest and a human-attestation event. Personal contact/employment data do not belong in the public graph. An agent cannot attest on a human's behalf. Existing authentication/tier-token practices apply; no open signup or recruitment is authorized by this design.

### Evidence packets and UI

For each sampled item prepare a digest-pinned packet containing both original observations, authorized source names and upstream IDs, observation/capture dates with uncertainty, relevant excerpt/locator, source-lineage facts, and neutral geometry at the allowed tier. Source identity is legitimate evidence and need not be hidden. Preserve raw values alongside normalized values when the normalization is part of what is being checked.

Hide matcher tier, score, predicted disposition, derived cluster membership, model/agent labels/rationale, other reviewers' labels, queue confidence text and any auto-generated summary that states a merge conclusion. Randomize left/right orientation and item order reproducibly; neutral IDs must not encode the tier. A pair's presence in a model-positive sample can itself reveal selection, so mix neutral control/development items in the interface where protocol permits and disclose residual selection awareness. Do not represent this as perfect blinding.

The reference labeler may cite additional already-authorized preserved evidence. Any newly needed acquisition follows its own gate and is recorded as a packet revision; it cannot quietly alter the sealed dataset. An adjudicator first records an independent judgment blind to the prior votes, then may inspect the disagreement and evidence to resolve it. Store both initial judgments, adjudication and reasons; never overwrite to manufacture agreement.

Two equal judgments yield a reference label subject to consistency checks. Disagreement or two insufficient-evidence judgments proceeds to adjudication. If evidence remains insufficient, keep that result. Agreement does not prove truth; audit shared assumptions and recycled source lineage. Show a three-by-three agreement table, raw agreement, category prevalence, NEI rate, disagreement rate and Cohen's kappa with appropriate uncertainty. Kappa is descriptive quality control, not a warrant to replace humans with an LLM. Do not make 0.70 a universal truth threshold.

### Training and final seal

Start with a proposed 40-item pilot outside every final-test dependency group. Reviewers label independently, discuss rubric disagreements, and improve instructions. Training may use retired agent sets, known edge cases and explicit synthetic examples, labeled as such. Track these origins; synthetic/agent labels cannot enter final human truth by relabeling the file header.

Freeze rubric, eligible evidence, protocol version, sampling frame, exclusions, analysis code, rules version and stopping plan after the pilot. Final reviewers do not discuss individual final items before independent submissions. Rules authors receive only training/development labels until the final run is frozen. The final result is unsealed once. Any subsequent inspected set is training/diagnostic evidence for future rules, not a reusable independent test.

## 6. Separate reference labels from operational decisions

Reuse GoldLabel's semantics through an adapter (`same→match`, `different→non_match`, `insufficient_evidence→not_enough_information`), but add a durable reference-label log and sample membership outside review_decision. Do not change that existing table's accept/reject constraint in place.

Proposed logical contracts, subject to a schema-inventory ADR and additive sqitch migration:

~~~json
{
  "campaign_id": "human-er-<version>",
  "protocol_digest": "sha256:...",
  "frame_snapshot": "...",
  "ruleset_digest": "...",
  "sample_id": "...",
  "pair_ids": ["left-record", "right-record"],
  "packet_digest": "sha256:...",
  "partition": "sealed_final",
  "estimand": "auto_positive_precision",
  "stratum_id": "tier1g:<sampling-stratum>",
  "dependency_group_id": "...",
  "source_lineage_ids": ["..."],
  "selection_probability": 0.025,
  "weight": 40.0,
  "draw_order": 17,
  "reference_basis": "physical_identity"
}
~~~

The internal manifest may store model strata; the reviewer projection must omit them. Draw-order/membership and original denominators are immutable. For multistage or repeated draws record the actual stage probabilities/multiplicity, not only a convenient final weight.

~~~json
{
  "sample_id": "...",
  "reviewer_id": "pseudonymous-human-id",
  "round": "independent_1",
  "label": "insufficient_evidence",
  "reason_codes": ["ambiguous_device_vs_site"],
  "evidence_refs": [{"capture_id": "...", "locator": {"kind": "row", "row": 4}}],
  "rubric_version": "...",
  "packet_digest": "sha256:...",
  "human_attestation_id": "...",
  "supersedes_label_id": null
}
~~~

Database-assigned label ID/recorded time and full history accompany this payload. `not_started`, `incomplete`, `conflict`, `adjudicated`, `withdrawn_reviewer` and packet-integrity failure are workflow states, not invented labels. Corrections append a superseding label with reason; an evaluator pins a label watermark. A corrected label after unsealing invalidates the old evaluation result and creates a new report, with contamination status explicit.

Evaluation has no write path into clustering. After evaluation is frozen, an authorized operational promotion may turn adjudicated same/different into a separate accept/reject decision with reference provenance, constrained by P31.11. An operational reject caused by policy, missing evidence or hard cluster shape does not become reference different. Insufficient_evidence never becomes reject merely to empty the queue. Sealed reference labels are inaccessible to clustering until the campaign permits operational release.

## 7. Leakage-safe sampling and the three estimands

### Split construction

Build dependency groups before splitting. At minimum connect pairs sharing a source record/upstream identity, members of the same candidate entity neighborhood, copied/mirrored observations and captures that repeat the same identity assertion. Include known temporal versions and target duplicate lineage. Keep each group in one partition. A true identity discovered later across partitions marks contamination; quarantine the affected evaluation and report its extent rather than deleting just the offending negative example.

For a claim of generalization to unseen source families, hold entire publisher/upstream-lineage families out of rule development. Mere geography separation does not isolate a shared upstream feed. For snapshot performance of existing sources, entity-neighborhood groups can be held out while source families recur; name that narrower target and report source-level dependence. A global lineage group may be too large to split usefully. Report feasibility and restrict the claim instead of breaking the group secretly. New-source/temporal stress sets are separate from probability estimates unless their selection design is specified.

| Estimand | Frame and sample | Valid conclusion / what it cannot establish |
|---|---|---|
| Auto-positive edge precision | All eligible edges that the frozen rule would automatically add, partitioned by candidate tier; random sample within each declared frame | Fraction of proposed automatic edges verified same. Does not measure missing matches or all co-clustered pairs. Include attempted/refused union distinctions explicitly. |
| Candidate-generator recall | Reference identity neighborhoods built from sampled records or bounded exhaustive regions, using search not restricted to the current blocker's candidates | Fraction of reference same pairs offered to the matcher. Labeling only blocked/queued pairs cannot observe blocking false negatives. |
| Final-cluster quality | Independently resolved reference clusters/neighborhoods, with known record/cluster inclusion probabilities and closure criteria | Pairwise and B-cubed precision/recall, overmerge/undersplit rates and identity-count bias within the covered population. One bad bridge can create many implied pairs. |

For recall/cluster work, start from probability-sampled records and independently search the authorized corpus using several broad keys/geo neighborhoods/source indices; do not show predicted clusters initially. Record the searched domain and closure evidence. After the reference partition is fixed, compare to predicted clusters. A bounded neighborhood with no defensible completeness criterion yields local recall/diagnostic evidence, not whole-corpus recall. Include singletons and same-source duplicate targets; sampling only non-singleton predicted clusters misses undermerges.

Proposed planning allocation: a 40-item pilot; then a confirmatory per-tier positive sample sized from the selected statistical model; separately 40 reference neighborhoods as an initial recall/cluster feasibility study; and a targeted challenge set of known soft conflicts, device replacements, mirrors and distant blocking misses. The 40-neighborhood study is not assumed sufficient to certify recall. Report targeted cases separately. P31.10's default400 may be a useful exploratory campaign but must not allocate 100 each to four tiers and then claim a 0.98 lower bound per tier.

## 8. Inference, weighting and a preregistered promotion rule

### State the population first

For a fixed finite snapshot with N eligible auto-positive edges and simple random sampling without replacement, the unknown labels are fixed attributes and randomness comes from sampling. Use inversion of the hypergeometric distribution for an exact lower bound on K/N (K = number of supported same edges). Correlated content among edges does not by itself invalidate true SRS finite-population inference; selecting whole groups or unequal quotas changes that design. At a full census the snapshot proportion is known, subject to human reference error. None of this certifies future runs or new source families.

For a future/exchangeable-event model, an independent Bernoulli assumption allows exact binomial limits. Shared entities, mirrors, acquisition batches and lineages can violate that assumption. Record the target and independent unit. If a grouped design is used, compute design-based uncertainty at its primary sampling unit; do not treat every intra-cluster pair as an independent trial. Many edges from one feed are not many independent source tests.

For stratified SRS within a fixed tier, use known population weights W_h=N_h/N and estimate p̂=Σ_h W_h p̂_h. Store N_h, n_h, selection probabilities and nonresponse. For unequal probability sampling use the declared design estimator, such as a ratio of Horvitz–Thompson totals, and its corresponding variance/replicate procedure. A raw average of an oversampled conflict stratum is not corpus precision. Preregister replicate weights or group-level bootstrap/jackknife/Taylor linearization as appropriate, preserve strata, and report the number of independent sampling units and degrees of freedom.

A conservative finite-stratified certification route is to derive simultaneous exact lower bounds L_h for every relevant cell, allocating family alpha across cells, then use Σ_h W_h L_h as the tier lower bound. An unobserved nonempty cell gets lower bound zero. This may require substantial sample size; it is a valid reason to narrow the scope or defer certification. Design-based normal/bootstrap intervals with zero observed errors can collapse misleadingly to 1; never use that degeneracy to pass. A heuristic effective sample size inserted into Clopper–Pearson is a planning approximation, not an exact proof for a complex design.

### Numeric implication of the proposed 0.98 rule

For n independent binomial trials with all n successes, the one-sided exact lower limit is L=alpha^(1/n). Thus n must satisfy n≥ceil(log(alpha)/log(0.98)). Pure Python standard-library arithmetic was run in this worktree with no file writes:

| Confirmatory family | Per-tier alpha | All-success n per tier | Lower bound at that n |
|---|---:|---:|---:|
| One prespecified tier | 0.05 | 149 | 0.980095 |
| Two prespecified tiers, Bonferroni family alpha 0.05 | 0.025 | 183 | 0.980044 |
| Four prespecified tiers, Bonferroni family alpha 0.05 | 0.0125 | 217 | 0.980009 |

These are best-case independent-trial floors, not campaign budgets or power guarantees. One error requires more evidence; dependence, multiple cells and cluster outcomes can require much more. At n = 70 all-success the one-sided 95% lower bound is approximately 0.9581. At n = 100 it is 0.9705. The existing ADR's reported Wilson values use a different interval convention and should not be silently replaced. With two tiers, 183 + 183 = 366 positive pairs leaves little of a 400-item budget for anything else; splitting 400 across four tiers cannot meet even the all-success bound.

Predefine the complete family of tier/scope hypotheses before opening labels; all attempted promotions count, including those that fail. Use a fixed family alpha≤0.05 and named alpha allocation (Bonferroni initially for auditability). Do not drop a failed tier from the family retrospectively, pool it into an easier tier, or select the best threshold on the final set. A formal intersection-union formulation for a single all-tiers decision can have different multiplicity properties, but the first SIG implementation should not switch formulations after seeing results.

### Proposed machine decision

`eligible_for_auto_write(tier,scope)` requires all of: human reference provenance valid; immutable packet/sampling manifest verified; no train/test contamination; fixed final rule/prediction digest; all sampled units accounted for; prespecified design and simultaneous lower bound computable; lower bound≥0.98; hard constraints and publication gates satisfied. Otherwise output `not_certified` with structured reasons. A tier with an empty deployment frame is `not_applicable`, never a performance pass.

For gating, code success as an adjudicated same on sufficient evidence. Different, unresolved conflict, insufficient_evidence and missing final labels are non-successes in a conservative verified-precision sensitivity calculation. Keep these categories separate in reporting; treating unknown as adverse does not assert factual nonidentity. Additionally require protocol completion; a partial campaign is `incomplete` and cannot certify even if a favorable lower bound could be manufactured. Preregister allowable packet corrections and replacement rules; unavailable items are not replaced until the desired result appears.

Choose a fixed final sample size and one scheduled analysis. An early stop is permitted for feasibility/futility or protection reasons but records no pass; it cannot become a sample-size adjustment based on interim successes. If a failed final result is inspected for tuning, the next version uses new independent final groups. A sequential alpha-spending/confidence-sequence approach would need its own justified protocol and tests, not repeated ordinary95% intervals.

Report point estimate, lower bound, interval method, alpha/family, finite population size or model assumption, weights, sample/missing/NEI counts, lineage/group counts, declared generalization domain and exact rule version. Keep PROVISIONAL for unmeasured domains; a scoped successful human result should not imply that all predicate families, countries, source types and future versions are validated.

## 9. Cluster impact, asymmetrical loss and drift

Alongside edge precision, report record-weighted B-cubed precision/recall, pairwise cluster precision/recall, proportion of reference clusters exactly recovered, overmerge/undersplit distribution, largest harmful bridge, and resolved-identity count error on the audited frame. Define each denominator and reference-cluster completeness. Calculate B-cubed only where the required reference membership is available; assigning every unreviewed record to its own truth singleton produces invented recall.

Present a sensitivity table over explicitly chosen false-merge:false-split costs, such as10:1 and50:1, as hypothetical policy scenarios. Do not pretend these are elicited stakeholder preferences or tune final thresholds to the scenario that wins. The measured ADR must select its actual objective before evaluating final labels. Where a harmful incorrect attribution has much greater cost, require an additional evidence/operational veto even if aggregate precision passes.

After release, track source mix, mirror coverage, coordinate precision, target changes, cluster sizes/bridges, unresolved proportion and performance on new human audits. New source families, changed rubric/normalizer/blocking rules, significant source drift or a new severe error can invalidate the relevant scope. Prior human decisions remain recorded. Repeated automated reruns on the same holdout are regression checks, not new independent evidence; periodic human audits need their own sampling/time budget and decision rule.

## 10. Workload, campaign gate and durable return path

These estimates are planning assumptions to measure in the pilot, not commitments from available reviewers:

| Work | Assumptions | Human hours |
|---|---|---:|
| Pilot/training | 40 pairs, two independent readings at8–15min, joint rubric calibration and packet QA | 20–40 |
| Example400-pair campaign | Two readings per pair at4–12min; 20–30% adjudication at8–15min; preparation/QA12–24h | 76–214 |
| Initial40-neighborhood recall/cluster study | Two readings/searches per neighborhood at15–45min plus QA6–15h | 26–75 |
| Protocol/method review | Statistical design, seal, independent reproduction and disposition meeting | 8–20 |

Combined illustrative workload is 130–349 human-hours, before extensive evidence acquisition or a larger confirmatory sample. At an explicitly hypothetical blended rate R, cost is R × hours; e.g. R = $50/h yields $6,500–$17,450. This is arithmetic, not a market quote, authorization to spend, or assumption that paid reviewers are required. A small volunteer team can spread the work over time; availability and calendar remain unknown. Pilot timing may change the budget materially.

Packet generation should be local/offline over permitted captures, deduplicated by capture digest. Proposed initial limits: 40 pilot items, one worker, ≤2GiB read; keep protected coordinates/excerpts in authorized internal storage. Final manifest records distinct bytes, item preparation failures and elapsed review time. Large O(n²) pair enumeration is unnecessary: stream eligible edge frames, indexed neighbor searches and reference-cluster memberships; keep expensive expanded searches bounded and label their coverage.

A durable human-campaign marker must name protocol/campaign/packet digests, frame date, requested roles, eligible scope, target sample design, actual completion counts, blockers, owner of the return decision, and next observable event. States should include `tooling_ready`, `awaiting_humans`, `in_progress`, `reference_locked`, `evaluated`, `incomplete`, `superseded`. Agents may prepare a ready packet; only actual human attestations advance reference completion. A waiting marker leaves D-R6.1-EVAL and the applicable D-P30.2b obligations open with precise evidence, without blocking unrelated deterministic work.

The later measured ADR accepts, narrows or declines the proposed auto-write rule using the results; threshold change is not predetermined. Hosted human-decision verification is a separate authorized run after operational promotion and must satisfy P31.11 plus its real deferral verification. A drop in site count is not proof of accuracy. Public disclosure changes require the relevant publication decision, not a successful unit test or merely reaching400 labels.

## 11. Acceptance criteria and negative tests

| ID | Deterministic or human-stage acceptance |
|---|---|
| EVAL-A1 | A reference label persists same/different/insufficient separately from operational accept/reject; operational unsure or a policy refusal cannot become a different reference label. Repeated imports are idempotent; corrections append history. |
| EVAL-A2 | Blinded UI/export contains no tier/score/predicted cluster/other vote/agent rationale, including hidden fields and IDs. Legitimate source evidence remains. Two reviewers cannot read each other's final submissions before lock. |
| EVAL-A3 | Manifest fixes all sampled IDs, probabilities, strata, population sizes, dependent groups, packet digests and partitions. Same seed+snapshot reproduces selection; changed snapshot refuses silent reuse. |
| EVAL-A4 | Shared record, mirrored target, temporal copy and known entity-neighborhood examples cannot cross train/final partitions. Post hoc discovered overlap invalidates affected certification with a recorded contamination reason. |
| EVAL-A5 | Missing, NEI, conflict and packet failures remain in accounting. Dropping them raises an evaluator error; no-label/one-item/zero-positive scopes cannot pass by NaN, zero denominator or truthy default. |
| EVAL-A6 | Exact independent-binomial tests pin148 all-success fail/149 pass for one tier and182 fail/183 pass per tier for a two-tier family at0.98. One-error cases are independently checked against a trusted implementation. Different interval conventions are labeled. |
| EVAL-A7 | Known finite populations validate hypergeometric inversion including full census and small strata. Stratified oversampling yields the design-weighted estimate, not unweighted pooled precision. Zero-error cluster bootstrap cannot return automatic certification. |
| EVAL-A8 | Grouped/unequal designs without enough variance units or a valid registered estimator return not_certified. Effective sample-size approximation cannot masquerade as an exact interval. Multiplicity covers every attempted tier/scope. |
| EVAL-A9 | Candidate-only truth cannot produce whole-corpus recall; partial reference clusters cannot produce full B-cubed. A synthetic bad bridge passes an edge-local plausibility check but visibly harms cluster metrics. |
| EVAL-A10 | Rules/packet/label digests and evaluator version pin the report. Final-label exposure followed by threshold retuning cannot reuse the same set as independent certification. Repeated peeks/changed stopping plan are flagged. |
| EVAL-H1 | Actual two-human independent labels and adjudication provenance exist for the fixed sample; method review verifies protocol departures, uncertainty and completion. An agent-generated label or duplicate human ID fails this stage. |
| EVAL-H2 | Independent evaluator reproduces the frozen report; a new ADR records actual result and scope, keeps unmeasured domains provisional and addresses active deferrals only with their required evidence. |

Test data must be clearly synthetic and excluded from production reference truth. Use real PG tests for label isolation, append-only events, access controls and import idempotence; pure tests for estimators/split algorithms. Full service/build validation belongs to the implementation ticket, not this research pass.

## 12. Candidate implementation units and proposed requirements

Root owns final IDs, sequencing, ADR allocation and spec edits. Six coherent units:

| Unit | Deliverable / dependency | Honest completion boundary |
|---|---|---|
| Reference protocol and readiness packet | Versioned identity rubric, roles, blinding/packet schema, preregistration template; uses S1 evidence contract | Engineering ready; no claim of available humans or reference labels. |
| Independent label store and blind projection | Additive reference-label/campaign tables, imports, protected evidence view, attestation/history; adapts P31.10 | Must not replace or weaken P31.10/P31.11 operational decisions. |
| Frame, dependency split and sampler | Tier-positive frames, source-lineage/entity-group split, weights, sealed manifest, recall-neighborhood sampler | Prepared sampled IDs are not evaluated truth; unavailable strata are explicit. |
| Design-aware evaluator and gate | Binomial/finite-SRS/registered stratified methods, grouped uncertainty guards, multiplicity, NEI handling, cluster metrics, reproducible reports | Deterministic correctness only; new gate remains inactive until measured ADR authority. |
| Human pilot and sealed campaign marker | Actual training, pilot budget, fixed final campaign, paired human judgments/adjudication, label lock | Human-dependent stage with waiting/incomplete path; cannot be completed by an agent or surrogate labels. |
| Measured rules decision and authorized operational verification | Training-only rules v3, frozen independent evaluation, new ADR, bounded application and disclosure decision | No automatic promise of promotion, deferral closure or removal of PROVISIONAL. |

Provisional normative ideas for root allocation:

- SIG-EVAL-REFERENCE: Reference identity labels MUST be attributable independent-human observations with an explicit insufficient-evidence outcome, separate from operational graph decisions.
- SIG-EVAL-BLIND: Final reference assessment MUST be blind to matcher predictions and other initial votes, with material blinding limitations recorded.
- SIG-EVAL-SPLIT: Training and final evaluation MUST separate dependent identity/evidence/lineage groups for the declared generalization target; exposed final data MUST NOT be reused to certify tuned rules.
- SIG-EVAL-ESTIMAND: Every metric MUST name its population, unit, inclusion probabilities, denominator, reference completeness and uncertainty method; candidate-only evaluation MUST NOT claim global recall.
- SIG-EVAL-GATE: Automatic promotion MUST satisfy the preregistered simultaneous lower-bound rule on sufficient independent human evidence; missing/uncertain outcomes MUST NOT disappear from its denominator.
- SIG-EVAL-HUMAN-GATE: Tooling, sample preparation and agent labels MUST NOT close a human-evaluation obligation; campaign completion and rule activation require their distinct recorded outcomes.

Suggested homes are spec §14.7 identity quality gates and holdout rules, §32 metrics, and §34/§39.7 reference-label versus operational review. Amend future P31.18-derived contracts through a new measured-decision ADR; preserve ADR-105 and the old holdout reports as honest history.

## 13. Unresolved facts and decisions

No human campaign has run in this pass. Actual reference accuracy, eligible frame sizes, usable independent source groups, item completion times and reviewer availability remain unknown. The choice between a finite-snapshot certificate and a future-source performance claim must be settled explicitly before sampling. The safest initial scope is a clearly named frozen deployment frame with a separate source/temporal generalization study, followed by narrower automation where evidence supports it.

The 0.98 threshold is a proposed continuation of the project's provisional target, not a statistically ordained acceptable harm rate. Statistical confidence measures sampling uncertainty under stated assumptions; it cannot eliminate systematic human reference error, missing source coverage or the semantic mistakes identified in S1. A trustworthy result therefore couples a bounded performance claim to reproducible evidence and visible unresolved cases.
