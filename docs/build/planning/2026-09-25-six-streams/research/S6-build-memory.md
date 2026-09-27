# S6 — Build memory as a reliable current-state interface

Research date: 2026-09-25. Baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`. Evidence class: repository inspection; no orchestrator execution, ledger advancement, or active-checkout mutation. This design extends build-memory v2 (ADR-073); it does not replace it with another workflow engine.

## What the existing system gets right

The canonical spec states obligations; ADRs record decisions and revisit conditions; tickets delimit landable work; the manifest supplies order; the main ledger is the resumable execution pointer and gate record; per-ticket run ledgers preserve evidence and remaining obligations; BUILD_INDEX is the landed-ticket catalogue; DEFERRALS is the outstanding-obligation register; BACKLOG supplies longer-term homes; the coverage matrix relates normative obligations to evidence. These are different views of different facts, not interchangeable summaries. `orchestrate-build` resumes CURRENT STATE, delegates one contract, validates closeout, handles checkpoints, and resumes gate-pending work through RETURN PASS. `implement-spec` has a code/PR commit followed by a closeout-memory commit. Capstone and reconciliation tails deliberately separate independent audit, execution checks, operator acceptance, and documentation reconciliation.

The system's strengths are durable recovery, explicit external gates, and preservation of disagreement/history. A compact current projection should exploit those strengths. Deleting historical narrative or replacing it with an optimistic dashboard would make the system less trustworthy.

## Findings and their limits

| Finding | Inspected evidence | Consequence | Confidence |
|---|---|---|---|
| Context volume is large enough to obscure current obligations | baseline.json records LEDGER 382,423 bytes, DEFERRALS 227,821, BUILD_INDEX 173,244, manifest 89,358 at this snapshot | An agent needs a bounded orientation view plus precise links, not another repeated narrative | measured file sizes; not a measured model-error rate |
| Some operative instructions are stale | root/web AGENTS zero-JS-only wording versus ADR-097 public map/network/search islands; README deployment posture versus recorded launch | A compliant agent can take an obsolete rule literally | direct conflict; nearest-file precedence does not resolve chronology by itself |
| Current status and appended history can disagree mechanically | `check_backlog.py:deferral_homes` parses the first word of the last cell; historical rows append DONE narrative after OPEN (examples D-P31.1-2, D-P31.3-1) | Readers and parsers can reach different owed-work sets | code-level parsing result; individual closures must be checked against run evidence before reconciliation |
| Coverage is a dated assessment but is easy to read as timeless | 677-row COVERAGE_MATRIX and earlier P19/P21 routing; later hosted/public seams have advanced | MET must mean a stated scope at a stated revision, not universal live correctness | design gap; no claim every historical verdict is wrong |
| Validator checks are mostly structural | `scripts/docs/check-build-memory.sh` legacy filenames map to sequence 0; next-ticket and unresolved spec coverage paths include warning-only branches | Green layout is not proof of semantic closure or complete requirement ownership | inspected implementation; adversarial fixture tests are required before changing enforcement |
| Validator report path is shared across worktrees | script writes `/tmp/build-memory-check.json` | Concurrent validation can overwrite the report another agent reads | definite path collision; no observed lost decision |
| The spec builder crosses checkout boundaries | `spec_src/BUILD.sh` originally sets ROOT to the active worktree's absolute path | Running it in an isolated checkout can overwrite another agent's spec | confirmed code; this planning change makes root resolution relative to the script |
| Two-phase closeout has a recoverable ambiguity | implement-spec commit/PR precedes index/run closeout | Crash recovery must distinguish landed implementation from completed bookkeeping | workflow analysis; not evidence of a current crash |

## Proposed current-state projection

Keep `LEDGER.md` CURRENT STATE as the sole execution control state. Add a deterministic, read-only projection under `docs/build/reports/current/` with a small JSON record and a human Markdown view. Projection inputs are explicit paths plus SHA-256 digests, source git commit, generated-at timestamp, schema version, and parser version. Output includes:

- active ticket, last completed, round, pending gate and RETURN PASS identifiers;
- outstanding obligations with owner, phase, dependency, exact verification action and one backlog home;
- implementation / fixture / composed-DB / hosted / public evidence separately, including last verified revision and time;
- source funnel counts with named units: discovered, reviewed, permitted, mapped, captured, extracted, linked, published;
- current public release id versus current database run ids; stale or absent evidence is explicit;
- ADR decisions that currently govern public islands, source rights, runtime composition, evaluation posture, and memory layout, each linked to the supersession chain;
- known inconsistencies that prevent a single current answer. The renderer fails rather than silently choosing a preferred prose statement.

Default Markdown budget: 250 lines / 20 KiB, with link-outs. Oversize is a test failure with ranked spill pages, not truncation that drops obligations. This is an orientation budget, not a cap on the underlying history or on mandatory per-ticket loading. The projection is advisory to humans and agents; it never advances nextTicket, records a gate, closes a deferral, or substitutes for the ticket's Load list. Projection output must say when it is stale relative to its source digests.

## Obligation events and transition rules

Use one append-only event record per obligation transition under the existing `docs/build/reports/` subtree; retain DEFERRALS as the human register and compatibility surface. Each event has `event_id`, `obligation_id`, `expected_previous_event`, `from_status`, `to_status`, `ticket_id`, `owner`, `evidence_refs`, `observed_at`, `recorded_at`, `source_commit`, `reason`, and `backlog_home`. Valid terminal dispositions remain DONE, WONTFIX, ACCEPTED-SKELETON; these are different meanings. A DONE transition requires verification evidence of the relevant domain. An operator acceptance is a gate record with its actual authority, never inferred from elapsed time or ticket completion.

Migration performs a one-time explicit reconciliation: enumerate raw parser status and prose closure claims, inspect linked run evidence, and append a migration event recording the chosen interpretation. Ambiguous rows remain OPEN with an owner. Historical rows are not rewritten to conceal their earlier state. A minimal compatibility status-cell update is allowed only with the appended event and old value recorded, following existing DEFERRALS rules; otherwise old and new parsers would diverge indefinitely. The new checker rejects a current status not supported by the event chain, duplicate event ids, missing predecessor, cycles, two transitions from the same predecessor, and nonexistent evidence references. No heuristic such as "last occurrence of DONE wins" is permitted.

Coverage assessments are separately versioned events: requirement id, verdict, scope/domain, code revision, test or readout, limitations, assessor, and assessed-at. Preserve the old CSV rows as the historical assessment; generate a current view from the latest non-conflicting assessment per requirement and domain. A fixture pass cannot silently supersede a hosted failure, nor can a hosted pass establish public publication. New normative requirements enter the existing CSV as MISSING, routed to one owner; design artifacts are not implementation evidence.

## Concurrent writers and crash recovery

One orchestrator coordinates control-state writes per build chain. Its explicitly delegated implement-spec closeout worker is a writer under the same lock and expected-state preconditions; delegation does not create a second independent control authority. A planner can write an isolated worktree, but integration requires a ticket boundary and a comparison against the latest chain tip. Introduce optimistic preconditions for the ledger writer (`expected_next_ticket`, `expected_last_completed`, `expected_control_digest`) and a scoped advisory lock keyed to the git common directory plus ledger path. The implementation must document filesystem/host limitations; a PID alone is not proof that a lock is stale across hosts. Readers need no lock. A stale lock is surfaced with recovery instructions and never removed merely because a timeout elapsed.

Closeout reconciliation keys an operation to ticket id, implementation commit, PR identity, and closeout schema version. Re-running the same operation is a no-op. Missing memory after a known implementation commit produces a repair proposal and verifies its evidence; it does not rerun implementation or mark DONE from a PR title. Reject a second different implementation identity for the same closeout unless a new recorded attempt explains it. Failure injection covers every boundary between implementation, PR creation, run ledger, BUILD_INDEX, DEFERRALS and control-state advancement.

Validator JSON goes to a caller-provided path or a unique temporary path printed in stdout. Structured diagnostic records carry check id, severity, file, obligation id and evidence. Process exit status must agree with the record. A report includes the checked input digest and must not be reused for another revision. Preserve upstream vendoring provenance: coordinate an upstream skill change or clearly document a local patch, never label modified detection logic as byte-identical vendoring.

## Proposed landable units

1. **Memory parser and reconciliation report:** strict parsing of the current formats, adversarial fixtures, stale-doc conflict inventory, explicit unresolved migration decisions. No control writes.
2. **Obligation/coverage events and current projection:** schemas, migration with evidence, deterministic views and freshness/size assertions, current-source-funnel definition.
3. **Closeout concurrency and recovery:** isolated report destinations, compare-and-swap preconditions, scoped writer lock, idempotent reconciliation and crash-boundary tests. Update workflow documentation and upstream/local-vendor attribution.
4. **Final documentation refresh:** after implementation, regenerate current views, refresh README/root/package agent guidance from actual code and ADRs, check every declared command, preserve historical build-memory records. This belongs to the round's DOC1/DOC2 tail, not an early promise that future behavior already exists.

## Acceptance and failure experiments

- Two worktrees validate concurrently and receive distinct reports carrying the correct revision.
- An OPEN-first/DONE-later row yields a conflict until an evidence-backed reconciliation event exists.
- A missing Docker daemon is reported as unavailable; it cannot become a green composed-domain assessment.
- A duplicate or orphan requirement owner and a forward dependency fail the checker on legacy and new filenames alike.
- A failed control-state compare-and-swap leaves every control file unchanged.
- A crash after each closeout stage followed by resume produces one index row, one transition chain and the correct next ticket, with no duplicate PR creation.
- Stale generated current docs are detected from input hashes; build logs remain ignored and no secret is copied into a projection.
- Changing a historical ADR body or claim record is never a migration mechanism.

## Open decisions and deliberate non-goals

The exact lock backend follows the current single-host runtime; multi-host orchestration needs a separate design before support is claimed. Human review of ambiguous historical closure remains required. This stream does not replace all skills, migrate to a hosted task tracker, or make agent memory a new production Python package. The frozen package layout remains intact. The planning handoff provides dependency/requirement validation immediately; broader writer hardening is future implementation.

## Review corrections incorporated into the final design

The first architecture review identified four implementation details that are binding for S6:

1. Before a validated cutover commit, events/projections run in shadow mode and the existing DEFERRALS writer remains authoritative. At cutover, each obligation gets one migration anchor with original raw digest/evidence; a single writer transactionally maintains event heads and compatibility cells. Do not invent historical transitions. Coverage assessments use explicit supersedes/domain/revision keys; incomparable concurrent heads are conflicts. Every worker and orchestrator repair entry point must adopt the writer before enforcement. Global skill patches require the operator’s approved ticket-boundary integration; until then report readiness and keep D-R10-MEMORY-1 OPEN.
2. The writer lock is keyed to stable build-chain id plus git common directory and repository-relative ledger path. It compares an authoritative expected chain head, not merely the stale worktree’s own file. Define operation id before remote PR creation from ticket/implementation/base/schema; attach remote identity afterward and reconcile uncertain creation by exact head/base before retry. State machine: prepared → external-result-known → memory-committed → acknowledged. One validated git tree/commit is the authoritative memory transition; next dispatch is prohibited before acknowledgment. Ordinary uncommitted file replacements are not an atomic transaction.
3. Enumerate projection input files; exclude generated current views, validation receipts and the future commit containing output. Record input commit plus dirty source hashes. Keep optional wall-clock generation receipts outside the deterministic semantic payload. A conflict produces a useful bounded conflicted/incomplete report and nonzero exit, never a confident synthesized answer or no diagnostics.
4. Test two stale worktrees racing, ambiguous PR creation, worker closeout versus orchestrator repair, legacy-only rows during migration, and failure at each commit boundary. A helper-only test is insufficient evidence that an installed skill uses it; actual integration remains a separately verified obligation.
