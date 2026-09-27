# Independent adversarial review of the six-stream execution plan

Date: 2026-09-25. Review target: `BRIEF.md`, `DESIGN.md`, and `PLAN.json`, including the root planner's in-flight amendments for withdrawal, build-memory authority, and dossier review. Read-only repository inspection; no tests, services, commits, or active-checkout operations. This review writes only this file in the isolated planning worktree.

I formed the sequencing, field-contract, withdrawal, and stale-worktree findings before reading `reviews/product-memory-review.md`. I then read that earlier review and re-read the amended PLAN. The earlier review's hash-cycle and broad temporal-selector defects are corrected. Its withdrawal and memory concerns now have concrete PLAN acceptance clauses; they are not counted again as unresolved findings below.

**Verdict: revise before dispatch.** Four concrete contract/dependency gaps remain in the inspected PLAN. P1 means the affected execution chain should not dispatch unchanged; P2 means the named ticket contract needs the correction before implementation/closure. These are planning defects, not claims of demonstrated live incidents.

## F1 — P1: The approved public candidate can predate the human rules decision

**Exact items:** `PLAN.json` P32.22, P32.23, P32.24, GATE-G3 and P32.25; `DESIGN.md` release identity and rollout contracts.

P32.22 stages the immutable unpublished release candidate. HUMAN-H4 follows P32.22. P32.23 then permits rule changes, tier demotion, rules activation, and actual human operational decisions propagating through P31.11. P32.24 tests “one staged release,” GATE-G3 reviews the candidate, and P32.25 publishes exactly that accepted candidate. No item owns re-materializing the final outputs after P32.23 changes their interpretation. The candidate's namespace correctly pins its old ruleset, so updating only its evaluation disclosure would also violate the immutable-byte contract.

**Failure case:** P32.22 contains an automatic cluster. HUMAN-H4 supplies contrary labels and P32.23 demotes the tier or rejects the pair. P32.24 still verifies the old staged candidate. GATE-G3 can see a passed evaluation readout beside artifacts that retain the pre-decision cluster. The same issue affects human semantic corrections to dossier assertions.

**Correction and owner:** retain P32.22 as bounded recovery plus an explicitly provisional candidate. Add a separate, bounded final-candidate ticket after P32.23, before P32.24. It must depend on the released-record/search/workspace/intake producers, the completed dossier outputs, and the applied human dispositions. It owns final resolution/materialization/export/index/tile/page production, cross-artifact reconciliation, and a new immutable candidate identity. P32.24 consumes that exact candidate; GATE-G3 approves its descriptor and integrity digest; P32.25 deploys those digests. Do not silently re-open P32.22 or mutate its existing candidate.

**Required acceptance:** intentionally cause a human decision or eligibility demotion to alter a cluster/dossier after the P32.22 candidate. The final candidate must have the new rules/disposition watermark and changed namespace/content; the old candidate cannot satisfy P32.24/GATE-G3. Any change after portfolio verification invalidates that verification and returns to the finalizer. A failed/inconclusive human assessment may produce a truthful provisional candidate, but cannot silently reuse the earlier decision state.

This split has a coherent landing: the finalizer applies already-built producers and verifies one immutable object set. It avoids making the evaluation ticket also own the entire public export pipeline.

## F2 — P2: Campaign tooling and the actual frozen campaign lack a sequencing boundary

**Exact items:** P32.9, P32.22, HUMAN-H4, P32.23; requirements SIG-EVAL-001 and SIG-EVAL-006.

P32.9 delivers immutable preregistration, splits and sealed holdout identifiers before P32.22's provenance/semantic recovery and rematerialization. HUMAN-H4 correctly waits for P32.22, but only says to complete “the preregistered campaign”; no item explicitly instantiates and freezes the production sampling frame after those changes. SIG-EVAL-006 itself says extraction-semantic or input-mix drift triggers reassessment. A technically valid sample from the earlier corpus cannot silently certify the repaired corpus or its newly formed components.

**Correction and owner:** state that P32.9 builds and fixture-tests campaign tooling/protocol only. HUMAN-H4's entry packet must be instantiated by that tooling against the pinned post-P32.22 corpus, source-lineage map, component frame and candidate ruleset. Name the engineering preparation owner explicitly, even if it is a bounded entry action attached to HUMAN-H4. Record input and sample digests, split decisions and preregistration before any labels are visible. Existing human labels may be retained as history/training only under their recorded eligibility; do not silently move them into a fresh holdout.

**Required acceptance:** changing recovery inputs, connected components, extraction semantics or candidate rules after frame preparation invalidates the campaign for the changed population before reviewer dispatch. The final evaluation identifies both the actually labeled snapshot and the publication candidate's applicable population. Late operational accept/reject application does not accidentally train on the sealed test set.

HUMAN-H4 may remain the honest blocking marker. The correction is an explicit entry dependency, not permission to fabricate reviewer completion or to skip the gate.

## F3 — P2: The document adapters precede the only dossier schema owner, while material semantic fields have no explicit canonical mapping owner

**Exact items:** P32.2, P32.3, P32.12 and P32.17; `research/S2-local-dossiers.md` “Passport and assertion contract” and “Trace and extraction design”; `ontology/src/ontology/schema/entities.yaml` Contract/Policy/LegalInstrument.

P32.12 must emit legal/operational status, effective dates and exceptions before P32.17 defines the dossier answer schema. P32.2 preserves generic qualifier fields; P32.3 owns role mapping, count comparability and organization identity. Neither explicitly owns the field-to-ontology mapping that the research leaves undecided. Existing Contract fields include amount, signed/start/end dates and amendment relations, but do not by themselves distinguish a spending ceiling from payment or council approval from complete execution. A JSON qualifier bag can preserve text without establishing interoperable semantics.

The missing decisions are concrete: lifecycle events and their evidence; announcement versus observed operation; amount type/currency/period; actor/modal force/object/condition/exception; governing instrument and attachment precedence; typed program grouping and measurement scope; research absence state versus canonical `AbsenceKind`. These affect parser output, comparison, historical selection and public sentences, so consumers cannot safely invent them independently.

**Correction and owner:** make a pre-adapter semantic-contract deliverable owned by P32.3 (or a small separate schema/mapping ticket after P32.2). It produces a versioned field dictionary and an explicit mapping table: existing predicate/type, typed qualifier, derived view/research record, or required additive ontology extension. Each field specifies cardinality, unknown/not-applicable treatment, valid/recorded timing, allowed states, and validator. P32.12 and P32.17 both depend on and consume it. P32.17 still owns presentation/question completion, not the earlier canonical encoding. Amend ontology source and generate only where the mapping requires it.

**Required acceptance:** round-trip a ceiling versus payment, vendor-signed versus fully-executed agreement, announced future retention versus observed configured retention, and a clause with a material exception. A later world date alone must not promote “announced” to “observed operational.” Unsupported material semantics must preserve an explicitly limited literal or abstain; they cannot be dropped to satisfy a simpler predicate. Existing claim IDs, digest interpretation, citations and older-reader compatibility remain explicit.

This also narrows sizing: the semantic contract is independently reviewable before adapter implementation. P32.3 presently combines role mapping, count semantics and identity repair; a distinct contract landing is safer than allowing P32.12 to discover incompatible representations while coding three source families.

## F4 — P2: Durable intake stops at moderation without owning the authorized correction application seam

**Exact items:** P32.16 and P32.24; SIG-FIND-006/007; `research/S4-public-product.md` §8 “Applying outcomes”; `policy/src/policy/corrections_intake.py:120`, `:205`; `api/src/api/curation.py` disposition routes.

P32.16 proves submission→restart→receipt→authorized moderation. P32.24 repeats receipt-to-moderation. P32.5 owns canonical disposition and selection policy, but none of these items explicitly joins an approved intake decision to a validated canonical correction and then to applied/published receipt state. The existing intake model uses in-memory lists and `BeliefLog`; the inspected curation routes do not supply a durable intake-to-claim correction bridge. Therefore the named end-to-end correction journey can pass while every report remains merely queued.

**Correction and owner:** split the already broad P32.16 into receiver/storage and a dependent private moderation/application landing, or add an explicitly bounded application deliverable with its own acceptance. The application half consumes P32.5's disposition contract and owns proposed→approved→applied→published/refused state, authority checks, canonical evidence/claim validation, transaction/idempotency key, safe response, and linkage to the resulting released correction. Public receiver credentials remain unable to perform these actions. No notification, new reviewer authority or publication approval is inferred.

**Required acceptance:** submit a synthetic permitted report, restart, have an authorized reviewer approve a fully evidenced correction, crash before and after canonical append, and resume. Exactly one correction/disposition is appended; receipt state never says applied before the write or published before an approved release. Missing correction fields cannot append a success event. Refusal and suppression retain their distinct authority and safe public output. P32.24 must exercise this seam offline; production exposure remains separately gated.

## Gate and RETURN PASS closure

The division between tested engineering and actual live/human outcomes is sound, but the amended contracts must preserve it at these new boundaries. P32.18–P32.21 may land tools/packets with OPEN RETURN PASS work. Their landed ticket status is not evidence that rights-cleared dossier captures, measured live acquisition, the >=28/36 dossier rubric, or human semantic review happened.

HUMAN-H4 entry and the final-candidate ticket should check named artifact/readiness predicates, not only predecessor ticket completion: actual post-recovery snapshot, reviewable evidence packs, source/evidence-use approvals for any captures, and applicable open obligations. A fixture-only predecessor can support further fixture engineering, but cannot supply production evidence or satisfy the final portfolio. GATE-G3's blocker list must name the missing stage and exact return owner; it must not rely on a free-form “required-for-publication” label assigned only at the end. Declined rights, unavailable reviewers and failed dossier completeness remain legitimate blockers, with independent engineering free to finish.

## What is robust in the amended plan

- The isolated planning branch does not advance the active orchestrator. P32.1 revalidates the eventual P31 tip rather than treating this snapshot as future fact. P31 source, tile and calendar ownership is preserved.
- Typed assertions, real capture occurrence/version/locator bindings, explicit replay timing, legacy classification, and append-only dispositions address the actual evidence seam. The plan does not promise that missing historical bytes can be reacquired retrospectively.
- Temporal selection now retains concurrent independent candidates and atomic coordinates. It distinguishes world time from knowledge time and avoids claim-ID ordering.
- Release identity now has an acyclic two-stage hash contract. Current withdrawal is explicitly tested against old-release rollback across record/search/tile/archive/compressed-origin paths. This addresses the previously identified privacy failure; implementation must preserve the stated breadth.
- Rights, sensitivity and identity-review restrictions apply before public projection, including derived surfaces. Search stays release-scoped and compartmented. The receiver has its own durable restricted store and privilege boundary.
- Memory changes now include an authoritative chain ref, pre-PR operation identity, commit-level transaction, stale-worktree race test, shadow migration and a single cutover writer. This addresses the specific flaw where a stale worktree could pass a CAS against its own obsolete ledger. The operator-reviewed skill-entry-point cutover remains a real integration condition.
- The updated dossier rubric and separate human semantic review prevent software conformance or camera pair labels from masquerading as completed local research. Failed/inconclusive resolution evidence remains provisional rather than forcing a favorable decision.

## Review limits and recheck

No code counterexample above was executed. Repository files were read only in the isolated worktree. No external sources were consulted because this review assesses the committed design and execution graph, not the truth of the cities' legal or operational facts.

After the four corrections, regenerate the ticket/requirement maps and recheck the graph: P32.9 tooling → P32.22 repaired corpus → frozen HUMAN-H4 entry packet → signed human work → P32.23 rules/dispositions → final candidate → P32.24 exact-digest portfolio → GATE-G3 → P32.25 exact-digest publication. The semantic field contract precedes all pilot adapters and dossier consumers; the private intake application seam precedes portfolio verification. Recheck current restrictions at publication and rollback independently of that historical data DAG.

## Final bounded follow-up — 2026-09-25

**Closure verdict: F1–F4 are addressed in the final planning contracts. No remaining P1 or new P2 blocker found within this review's scope.** This closes the design findings, not their future implementation, human, live or publication obligations.

Reviewed PLAN SHA-256: `1091512cb26fb2e58b844f8858676d7b8f199ea170f3e2104406cb5f8cc05161`; DESIGN SHA-256: `0acb9f089553aa1fb2deb9c61ee3163ff0a7be02c184508c7c4991e5fdfe3063`. I checked the amended source records against the rendered affected tickets, §55 source and generated canonical paragraphs, REQUIREMENTS, ADR-115, HANDOFF, REVIEW_CLOSURE and the appended Round-10 deferral rows. No product runtime, service or test suite was executed; the dependency check only parsed planning files in memory.

| Finding | Material closure evidence |
|---|---|
| F1: pre-evaluation public candidate | P32.22 now produces only the frozen repaired input snapshot/audit preview. New **P32.23a**, sequence 186, depends on P32.23 and every required downstream producer through explicit/transitive dependencies; it rebuilds graph, dossiers, records, indexes, tiles and analytics with one evaluation/ruleset/snapshot identity. P32.24 depends on P32.23a; GATE-G3 depends on both; P32.25 publishes only the approved bytes. **SIG-TRUST-010** is present in generated canonical §55 and has exactly one owner, P32.23a. Changed evaluation-relevant inputs stop for reassessment. |
| F2: final campaign frame | P32.9 explicitly forbids drawing/freezing the final confirmatory sample. HUMAN-H4's first deliverable instantiates it from the actual P32.22 frozen snapshot using P32.9 tooling, checks sample/split/denominator digests before packet distribution, and excludes pilot labels from the holdout. P32.23 freezes its candidate/hypothesis family before one final unsealing. H4 remains an actual blocking human marker. |
| F3: semantic schema before adapters | P32.2 now owns the field-to-existing-LinkML/DB mapping for lifecycle/execution, monetary fields, roles, modality, exceptions and applicability before adapters. P32.12 explicitly consumes that mapping and P32.3 semantics, owns the frozen source-to-predicate/qualifier/dossier crosswalk, and stops for a scoped amendment when a required field is unmapped. P32.17 now also depends on P32.12. Bounded protocol/document limits make the adapter landing concrete. |
| F4: receipt-to-canonical application | New **P32.16a**, sequence 177, owns the restricted validated application bridge, authority/policy checks, operation identity, append audit and applied/publication receipt linkage. Its crash/retry and rejection acceptance is explicit. P32.24 now exercises an approved synthetic proposal through that bridge to one canonical disposition and staged public correction while denying receiver mutation authority. **SIG-FIND-008** exists in generated §55 and is owned only by P32.16a. |

The static graph check found **38 rendered contracts, sequences 161–198, and 37 uniquely owned requirements**, all still `MISSING`. Every in-plan dependency points backward in sequence, all external predecessors occur in the manifest, every contract file exists, and its declared dependencies appear in the rendered contract. There is no forward edge or dependency cycle in the checked extension. The corrected evaluation/publication path and the semantic/application prerequisites are materially closed, not merely renumbered.

RETURN PASS remains separate from gate satisfaction. Rendered markers explicitly say engineering closure with OPEN return work does not satisfy their exit criteria. `D-R10-HUMAN-1`, `D-R10-SOURCES-1`, `D-R10-LIVE-1`, `D-R10-PUBLISH-1` and `D-R10-MEMORY-1` retain their real live/human/cutover conditions. GATE-G3 requires the actual dossier rubric/semantic review or an explicit reduced publication scope that cannot claim pilot completion. Those are valid pending execution conditions, not unresolved planning defects.

Concurrent P31 work and the calendar deadline remain protected: HANDOFF retains the original checkout and ledger, waits for a clean ticket boundary, reconciles concurrent ADR/backlog/sequence/spec changes, and forbids P32 dispatch before P31.19. ADR-115 is explicitly a snapshot-relative allocation with precise collision handling. P32.22 and SIG-TRUST-008 preserve the reserved **2026-10-10** replay obligation; no advance completion or early rerun is implied. This follow-up did not inspect or modify the active checkout.
