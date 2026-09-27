# Independent product and build-memory architecture challenge

Date: 2026-09-25. Review target: the initial 117-line `DESIGN.md` and 74-line `research/S6-build-memory.md`, before the complete ticket/PLAN synthesis. This is a design review, not an executed test or a review of final amended files. Only the assigned review and the reviewer's own S4 research contract were changed; no active checkout, implementation, service, ledger or external skill was modified.

Severity: **P1** = resolve before dispatching the affected implementation; **P2** = make explicit in its contract/acceptance before closing that ticket. These are not claims that the running production system already exhibits a newly proposed failure.

## Findings

### P1 — The publication hash can depend on itself

**Evidence:** `DESIGN.md:77–79` derives the release ID from a manifest of final artifact digests, while IDs appear in record URLs. The original S4 proposal made the cycle explicit: `PublishedRecord.publication_id` and its immutable hrefs were themselves emitted into artifacts whose hashes determined `publication_id`.

**Failure:** render with ID X → artifact bytes determine ID Y → render with Y changes the bytes again. Excluding the ID field from the outer manifest does not exclude it from hashed HTML/JSON/index bytes. A SHA-256 fixed point is not a viable build step. Generation-time timestamps are another source of accidental nondeterminism.

**Correction:** adopt two named layers: (1) a pre-render publication namespace from canonical ID-free admitted-projection roots plus all interpretation/renderer/config inputs; (2) a final artifact-integrity manifest digest. The external activation/catalog record binds the namespace to exactly one integrity manifest. Do not embed the final manifest digest back into an artifact it hashes. Refuse a second different manifest for an activated namespace. Execution timestamps belong in an activation receipt; an intentionally rendered timestamp must be a fixed descriptor input. An alternative is fully ID-free, relative-link artifact bytes with a content-addressed outer manifest, but it would require changing the proposed JSON/citation contract explicitly.

**Required test:** the same descriptor rendered twice produces identical artifacts and integrity digest; changing renderer input yields a new namespace; mutating any artifact under the old namespace makes activation fail. Assert that the dependency DAG of hashed/embedded fields is acyclic.

**Review action already taken:** corrected this issue in the owned S4 `Publication identity` contract. Root DESIGN/spec/ticket wording still needs alignment. This was also a defect in the reviewer's first design, not only the root synthesis.

### P1 — “Latest eligible occurrence” needs a source-lineage key or it can erase disagreement

**Evidence:** `DESIGN.md:73` takes subject/predicate plus temporal context and selects “the latest eligible occurrence.” `DESIGN.md:65,69` otherwise preserves contradictory evidence. S1 `research/S1-evidence-integrity.md:226–228` distinguishes source sightings, current selection and observation history. The existing `resolution/src/resolution/camera_sites_pg.py:77` uses `DISTINCT ON (c.subject_id, c.predicate_id)`, making an overly broad implementation a credible risk.

**Failure:** two independent sources concurrently report different operators/counts/locations. A selector keyed only by entity and predicate treats the newest source as superseding the other and can silently eliminate a genuine contradiction. Independently selecting latitude and longitude can also create a location never observed together.

**Correction:** specify an eligibility **set** and the supersession/occurrence key. Select the latest establishing sighting within an explicit source assertion/source-record lineage; retain all concurrently eligible claims from independent lineages. Resolve or abstain only in the versioned resolver layer. Coordinate and other coupled fields stay bound to one source-record occurrence. Define how a source's revised record supersedes its previous assertion without making an unrelated source disappear.

**Required test:** same-source same-day A→B→A selects final A, while an independent source's current C remains a competing candidate; earlier belief excludes later sightings; coordinate pairs remain from one occurrence. Conformance vectors must assert retained candidate sets, not only a winning scalar.

### P1 — Rollback and immutable access need the same current suppression barrier

**Evidence:** `DESIGN.md:79` permits tombstones; `:103` says rollback reselects an earlier immutable release. S1 `:327–328` explicitly requires historical requests to respect current suppression, and S4's withdrawal section extends this to indexes, archives and caches. The root summary does not make that precedence explicit at rollback/activation.

**Failure:** reverting to an older release whose bytes contain a subsequently withheld name/location restores the exposure. Removing a record page alone does not remove snippets, facets, PMTiles, compressed downloads, the bucket origin, or a still-open immutable search index. Copying a release-local suppression summary cannot express restrictions learned later.

**Correction:** activation and rollback both evaluate the **current** access-withdrawal registry/policy against the candidate release. Make the suppression barrier independent of the selected release's historical epistemic context. If the old artifact cannot be safely filtered, deny the whole affected partition/artifact and retain a safe tombstone; never rewrite bytes under its identity. Name one withdrawal owner and enumerate both public origins, CDN/cache representations, compression variants, downloaded index handles and archived bundles in its blast-radius contract. A rollback pointer is not authorization to serve every old artifact.

**Required test:** publish R1, withhold a record in R2, attempt rollback to R1, and verify denial through record HTML/JSON, search/facets, tiles and bundle URLs on every operator-controlled public origin. Old citations must not show replacement values. No promise is made to recall third-party downloads.

### P1 — A lock plus ledger-file CAS does not make existing closeout atomic or cross-worktree safe

**Evidence:** S6 `:48` says one orchestrator owns control writes, with a lock keyed by git common directory and ledger path; `:50` makes closeout idempotent; `:67–68` promises unchanged controls after failed CAS and exactly-once recovery. The actual `/Users/stevenvitali/.claude/skills/implement-spec/SKILL.md:441–461` assigns closeout to the worker, and `/Users/stevenvitali/.claude/skills/orchestrate-build/SKILL.md:192–202` makes the orchestrator confirm or repair it. These are competing write entry points unless both adopt the protocol.

**Failure cases:**

- An absolute worktree ledger path yields different locks for the same chain. Even a shared lock only serializes writers: a stale worktree can still pass a CAS against its own stale ledger after the first writer exits.
- A process can update BUILD_INDEX or append an event and then fail a ledger CAS. Multiple ordinary file replacements are not a transaction.
- A PR can be created before the response is durably recorded. A recovery key that requires the missing PR identity cannot itself prevent creating a duplicate.
- A worker using the installed skill can bypass a new repository-only writer, leaving the hardened validator with an unsupported partial transition.

**Correction:** name the **single build-chain authority**, distinct from the currently executing agent, and require every worker/orchestrator repair path to use the same writer. Use a stable chain identifier, normalized repo-relative ledger path and authoritative expected chain head, not merely a private worktree's file digest. Specify an operation ID before external PR creation from ticket/implementation/base/schema inputs; attach PR identity later and reconcile an uncertain creation by exact head/base identity before retry. Define a prepared→external-result-known→memory-committed→acknowledged closeout state machine. The authoritative memory transition should be one validated Git commit/tree (or a journal with an explicit committed marker), with next dispatch prohibited until that commit is accepted; do not claim arbitrary uncommitted files are atomically readable. A failed precondition must occur before writes, or restore only this operation's journaled changes without touching concurrent user work.

**Required test:** two worktrees from the same old tip race; only one can advance the authoritative chain. Inject failure before/after remote PR success and at each local file/commit boundary. Worker closeout and orchestrator repair converge to one accepted operation; readers never interpret a partially written tree as completed. Run this against the actual installed/local-vendored entry points, not only a helper unit test.

**Scope control:** no distributed coordinator is needed. Explicitly support the current single-host/single-authoritative-chain workflow and reject unsupported writers/hosts. Any patch to global skills is a separate, operator-reviewed integration action; planning does not authorize changing the actively running Claude workflow.

### P2 — The projection lacks an acyclic input set and a stable timestamp contract

**Evidence:** S6 `:26` calls the view deterministic while including source git commit and generated-at; `:34` says the renderer fails on conflicting statements, while `:28–34` requires a useful view of known inconsistencies; `:69` requires freshness against input hashes. New event records and generated outputs both live beneath `docs/build/reports/`.

**Failure:** globbing that subtree includes the previous output and makes the next output stale by construction. Recording the commit containing the projection inside the projection similarly creates a self-reference. A wall-clock generated-at field causes needless diffs on every rerun. Failing without a diagnostic snapshot removes precisely the current-state aid needed during a conflict.

**Correction:** enumerate source files explicitly and exclude generated `reports/current/**` and transient validation artifacts. Record the **input** commit plus dirty-input digests; never promise the enclosing future commit's hash. Separate a deterministic projection payload from an optional generation receipt, or accept an explicit timestamp argument excluded from semantic freshness. Emit machine diagnostics and a bounded “conflicted/incomplete” report on semantic conflict, with nonzero exit; never synthesize a confident current answer. Committed spill pages must be generated from the same input manifest and carry that identity.

**Required test:** two renders from identical input bytes produce identical semantic output; committing the output alone does not make it stale; a real source change does. A contradictory obligation emits a conflict report and nonzero status without dropping other owed obligations.

### P2 — Event migration needs one authoritative status and a declared compatibility cutover

**Evidence:** S6 `:40–44` adds obligation events, keeps DEFERRALS as a compatibility register and adds separate coverage assessment events; `:42` allows minimal cell updates. Existing `docs/tickets/DEFERRALS.md:12–25` tells every worker to append/flip the human register, and `docs/build/tools/check_backlog.py:125–146` reads status from the final cell. S6 rejects divergence but does not identify the writer or activation checkpoint that prevents old workers from immediately reintroducing it.

**Failure:** hand-maintained DEFERRALS, event chains and generated current projections become three writable interpretations. An old worker can append a legitimate deferral with no event and make the new checker fail; an event-only writer can hide debt from current tools. Coverage “latest” is also undefined across concurrent revisions without an explicit supersession relation, even if timestamps are present.

**Correction:** make the event chain authoritative **only after** a validated migration/cutover commit; generate or transactionally update the compatibility status cells through one writer. Before that commit, run the new parser/report in shadow mode and do not partially enforce events. Represent every legacy obligation with a migration anchor plus raw-source digest/evidence, not hundreds of invented historical transition events. Preserve ambiguous rows as OPEN. Coverage assessments need explicit supersedes and input revision/domain keys; reject conflicting incomparable heads rather than sort wall-clock timestamps. Update all applicable workflow entry points at the same activation boundary, with legacy readers tested until retirement.

**Required test:** a legacy-only row, event-only transition, divergent cell and concurrent assessment are all visible and fail clearly after activation; no canonical obligation disappears during migration. A new worker can open and close one deferral without hand-editing three representations.

### P2 — Public dynamic features need explicit deploy gates and a bounded resource decision, not an implicit static-site extension

**Evidence:** `DESIGN.md:83–89` selects complete released search and a public correction receiver; `:101,117` preserves resource/human gates. S4 quantifies hundreds of thousands of static record objects, a candidate FTS5 index, dynamic no-JS search HTML, a restricted expirable intake store and a staffed review queue. These are proposals with benchmark/authority decisions, not existing hosting capabilities.

**Failure:** a ticket can appear complete by wiring current search, accepting a report only in memory, exposing loopback curation, or assuming unlimited static build/storage cost. HG-11 alone should not be treated as approval of the receiver's retention/logging identity model, source permissions or reviewer authority. “Anonymous” is misleading if infrastructure retains identifying request metadata.

**Correction:** the final owner contracts should explicitly incorporate S4's bounded benchmarks and staged failure semantics. Keep released search read-only; keep the receiver's durable write store/credentials separate from the claim spine and curator. Require operator ratification of deployment, logging/retention and a named staffed queue before its endpoint is publicly enabled. Defer full SPA/accounts/new basemap. Benchmark complete static records/index serving on the approved infrastructure first; if it fails, stop for the documented deterministic HTML/archive alternative rather than relax discovery coverage or spend implicitly. Preserve operator rights and publication gates independently.

**Required test:** 230k eligible records/14 compartments/8 readers exercise the proposed search budgets; every admissible record is addressable beyond position 500; unavailable search gives an honest error plus complete static browse. A correction acknowledgment requires a durable commit and survives restart; reviewer/application failure does not claim resolution/publication. No endpoint can invoke curator or claim writes from public credentials.

## Recommended synthesis changes

1. Fix the hash DAG and temporal selection key in the canonical contracts before ticket prose spreads the ambiguity.
2. Make current suppression an activation/rollback invariant with one cross-artifact owner.
3. Specify closeout as a small, explicit commit/journal protocol used by both worker and orchestrator; scope it to one host/chain.
4. Land S6 parser/report improvements before event enforcement; make input manifests deterministic and status authority explicit.
5. Keep the product architecture at existing islands plus complete records/search and separately gated intake. The design should not grow a full SPA, search cluster, task tracker or distributed workflow engine to solve these problems.

No final plan/ticket verdict is given here: those artifacts were still being assembled. Re-review their concrete dependency edges and acceptance clauses against these findings before dispatch.
