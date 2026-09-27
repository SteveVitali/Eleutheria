# Six-stream research ledger

This is a planning-round research ledger under committed build memory. It does not replace or advance `docs/build/LEDGER.md`.

## Current state

- Status: COMPLETE — research/design/contracts; active-chain integration in progress after P31.19 (see integration receipt)
- Base: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e`
- Next: finish the verified PR/checkout handoff in integration/2026-09-26-after-p31-19.md, then P32.1
- Implementation dispatched: no
- Active checkout touched: no

## Workstreams

| ID | Concern | Owner | Status | Artifact |
|---|---|---|---|---|
| S1 | Evidence, semantics, temporal integrity, publication | technical researcher | COMPLETE | research/S1-evidence-integrity.md |
| S2 | Complete local dossiers and acceptance portfolio | source researcher | COMPLETE | research/S2-local-dossiers.md |
| S3 | Human adjudication and statistical evaluation | evaluation researcher | COMPLETE | research/S3-human-evaluation.md |
| S4 | Public discovery, citation, correction and explorer | product researcher | COMPLETE | research/S4-public-product.md |
| S5 | Gap-driven source discovery and onboarding | source researcher | COMPLETE | research/S5-source-strategy.md |
| S6 | Current-state memory and orchestrator reliability | root | COMPLETE | research/S6-build-memory.md |
| X1 | Shared decisions, amendments, dependency graph, contracts | root | COMPLETE | DESIGN.md; REQUIREMENTS.csv; PLAN.json |
| X2 | Independent adversarial review and closure | fresh reviewers | COMPLETE | reviews/ |
| X3 | Validation and handoff prepared; active-chain import pending | root | READY FOR IMPORT | VALIDATION.md; HANDOFF.md |

## Decision register

| ID | Decision | Basis | Status |
|---|---|---|---|
| Q1 | Use an isolated worktree and preserve the active ledger until a safe handoff | operator explicitly identified another active session | APPLIED |
| Q2 | Preserve existing source-rights, publication and human-review gates | root AGENTS and prior operator scope | BINDING |
| Q3 | Design human review with no invented reviewer availability or completed labels | independent ground truth does not yet exist | BINDING |
| Q4 | Reuse existing P31 work; add delta contracts with explicit seam owners | avoid conflicting implementation chains | COMPLETE |

## Change log

- 2026-09-25: Seeded from the operator's six-stream request in the isolated planning worktree. Read root instructions, active deferrals and current execution state. Identified a hardcoded spec-builder output path that must be fixed before isolated regeneration.

- 2026-09-25: Completed six research reports and 27-candidate inventory; authored DESIGN and strict ownership/dependency maps.
- 2026-09-25: Four independent review artifacts exposed hash-cycle, temporal-candidate, withdrawal/rollback, closeout, semantic mapping, correction application and evaluation-sampling seams; corrected them in the design and actual contracts, with bounded follow-up closure checks.
- 2026-09-25: Final decomposition: 40 rows (161–200), 38 new obligations (715 total), full nine-row tail, four pending human/gate readouts, six explicit OPEN prerequisites. Added H4 development → candidate/frame freeze → H5 final adjudication to prevent selection-biased evaluation.
- 2026-09-25: Canonical §55 generated through source builder; exact spec/coverage/backlog and plan checks pass. Full make check: 4,218 passed, six documented skips. Current-state LEDGER and BUILD_INDEX unchanged; no active-checkout intervention. See VALIDATION.md for final detector results/limits.

- 2026-09-25: Operator requested a one-instruction future integration after P31.12–P31.19. Added INTEGRATION_RUNBOOK.md, read-only preflight and regression tests; parameterized the new manifest block’s sequence bounds. Import remains pending the explicit clean pause. Source series includes foundation fdc7758 plus this preparation; active execution memory remains untouched.

- 2026-09-27 UTC: Operator paused after P31.19 and authorized integration. Pinned paused tip `08d87c4`, imported both source commits into an isolated child branch, reconciled ADR-120/BL-058/rows 161–200 and preserved current execution evidence. Added explicit closure acceptance for the two otherwise-unscheduled API seams and appended the existing ACCEPT-R8 signature correction. Validation and PR evidence follow in the integration receipt.
