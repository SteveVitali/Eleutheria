## Summary
Implements **P10.3 — Records-request generation** (canonical §36), turning a detected research gap into a ready-to-file public-records request. Built on the P10.1 task engine and the P09.1 coverage model; owns the 51-jurisdiction records-law reference table and the residency-routing contract.

Spec: `docs/tickets/P10.3__records-request-gen.md` (§36; SIG-TASK-015/016/016a/016b/017/018, SIG-TASK-009).

- **Emit with the correct statute (SIG-TASK-015)** — `RecordsRequestGenerator` emits target agency + records contact, the jurisdiction's correct statutory citation (looked up, never guessed), proven per-record-type language, and the specific records sought.
- **51-jurisdiction reference table (SIG-TASK-016)** — `tasks/data/records_law.toml`: statute name/citation, response deadline, fee rules, appeal path, residency flag for all 50 states + DC.
- **Residency is operationally binding (SIG-TASK-016a/016b)** — in the six restricted states (AL, AR, DE, KY, TN, VA) a non-resident/unknown-residency filer is **refused**, routed to the jurisdiction's local filers (the local-group registry becomes load-bearing), and the barrier is recorded as a `not_researched` coverage fact — **never** `searched_not_found`, so thin coverage reads as a legal barrier, not an absence (§32.2). Unknown residency defaults to restrictive.
- **Versioned templates + measured success rates (SIG-TASK-017)** — `TemplateLibrary` (versioned language) + `TemplateOutcomeLog` (measured rate, denial-producing language flagged for revision with a min-sample guard).
- **Consent (SIG-TASK-018)** — no emit without explicit consent + public-act acknowledgement; every request carries a public-act notice.
- **`resolved_no_evidence_exists` → `CoverageRecord` (SIG-TASK-009)** — `record_no_responsive_records` reuses `tasks.dispositions.resolve_no_evidence_exists`.

## What changed
- `tasks/src/tasks/records_request.py` — the generator, reference-table model, residency routing, templates + outcome log, consent gate, coverage bridge.
- `tasks/src/tasks/_data.py`, `tasks/src/tasks/data/{records_law,request_templates}.toml` — versioned data (SIG-ENG-001).
- `tests/tasks/test_tasks_{records_law,records_request,templates}.py` — 34 new tests.
- Docs: `ADR-041`, ADR index, traceability matrix, risk register (RISK-P10-15..18).

## Design decisions
- Residency barrier → `not_researched` (attributed via `search_method`), not a new `absence_kind` (P09.1's four-kind vocabulary is a frozen contract) and not `searched_not_found` (§32.2). See ADR-041.
- "Route to the geographic queue" = a routing **decision** (`ResidencyBlock` naming local filers + active claimants); P10.1's `GeographicQueue` is a claims/ordering coordinator, not a task container. Applying it through the live pool is downstream.
- Reference table and templates are versioned data, not code. Operational-detail fields (deadline/fee/appeal) are honest seed values pending counsel review (RISK-P10-17); `citation` and `residency_required` are load-bearing and asserted.

## Acceptance criteria → evidence
| AC | Evidence |
|---|---|
| Emitted citation matches the 51-jurisdiction table | `test_tasks_records_request.py::test_emits_the_correct_statute_for_the_jurisdiction` (5 jurisdictions), `::test_emitted_request_carries_the_sig_task_015_surface` |
| Residency-restricted + non-resident → refuses, routes, records coverage fact | `::test_non_resident_in_restricted_jurisdiction_refuses_routes_and_records_coverage`, `::test_residency_barrier_coverage_is_never_searched_not_found`, `::test_unknown_residency_defaults_to_restrictive` |
| `resolved_no_evidence_exists` writes a `CoverageRecord` (searched_not_found + sources) | `::test_no_responsive_records_writes_a_coverage_record` |
| Phase-gate: tests for new reqs, ADR, traceability + risk register updated | ADR-041; traceability P10.3 section; RISK-P10-15..18; new test suites |

## Test plan
- [x] `tests/tasks` + new suites (34 new tests) green
- [x] Full suite: 1709 passed
- [x] `ruff check` + `ruff format --check` clean (all packages + tests)
- [x] `mypy` clean (147 source files)

Generated with [Devin](https://devin.ai)
