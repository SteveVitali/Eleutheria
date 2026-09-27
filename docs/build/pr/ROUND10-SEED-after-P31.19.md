# Seed Round 10 after P31.19 and repair clean CI installs

P31.19 exhausted the active manifest while the six-stream design was still isolated on an older planning branch. This PR imports the complete reviewed planning series onto the exact completed P31.19 tip, adds 40 ordered rows (161–200), and makes the existing orchestrator resume at P32.1 / round 10 without SETUP or replaying P31 work.

The program covers evidence/semantic/temporal integrity, three local dossiers, independent human evaluation, released search/citations/corrections, gap-driven source acquisition and reliable build memory. Canonical §55 adds 38 explicitly MISSING obligations with one owner each, backed by six research reports, the design, source inventory, reviewed contracts and the full nine-row tail. This PR does not implement those features or satisfy their human/source/publication gates.

- Reconciles the planning ADR as **ADR-120** while retaining all landed ADR-115–119 decisions, current P31 spec changes and historical coverage/backlog/deferral evidence. BL-058 and sequence 161–200 remain available.
- Preserves P31.19 as lastCompleted, all completed BUILD_INDEX rows, original stack root, existing gate decisions and RETURN PASS. The actual new chain tip is the next worker's base. H4 → P32.22a → H5 → P32.23 replaces the historical unscheduled “Round 10/P31.18” wording; no dropped ticket is resurrected.
- Gives the remaining unknown-predicate serving and annotation-watermark seams explicit acceptance in P32.2/P32.4; P32.5 already owns pending-organization publication eligibility. P32.1 verifies the fresh baseline before dispatch.
- Appends a correction to P31.19's stale unsigned-ACCEPT-R8 statement: the operator signature already exists in `0a715fc`. No gate is signed again; the four new markers stay PENDING.
- Repairs the inherited npm-ci failures by completing `web/package-lock.json`: four missing transitive/peer entries, no changed existing package versions or package.json pins. This is the sole non-documentation change; app code, CI workflow, deployed services and source permissions are unchanged.

Requirement traceability: SIG-ENG-003 / SIG-ENG-039 for the new decision and regenerated canonical source/index; new §55 ids and their future owners are in `docs/build/planning/2026-09-25-six-streams/REQUIREMENTS.csv`. Their implementation verdicts remain MISSING.

Source commits: `fdc775837b2808b23a9af690c427deec5ede0a5d` and `240129cd674bd74a1c5a652f8c16e4759a455584`. Base: `devin/p31-19-round9-closeout` at `08d87c4dc22d4c7c505aa19fe28bcf36e84cfe7a` (PR #154). The operation does not merge/tag/push main or change earlier PRs.

## Validation

- Plan/preflight regressions: 13 passed; spec-source regressions: 8 passed; exact plan/render, 715-row coverage, 119-ADR appendix and backlog/mirror checks pass.
- `make docs-check`: zero broken references and zero build-memory violations/warnings.
- Independent read-only integration review found no blockers (recorded in the planning package).
- Preservation assertions: all landed ADR bodies, signed ACCEPT-R8, BUILD_INDEX, prior coverage/backlog/deferral bytes and retained control fields unchanged.
- Clean npm install passes under CI's Node 22.23.2/npm 10.9.8. Web typecheck, 222 unit tests, static build and 228-production-dependency licence check pass; 246 browser/no-JS/accessibility tests pass on an isolated local port. The standard port was occupied and its existing service was not stopped/reused.
- Lighthouse performance/accessibility/resource budgets pass on all eight configured URLs under CI’s Node/npm versions.
- Full `make check` with `SIG_REQUIRE_DB_TESTS=1`: **4,404 passed, 3 skipped**, clean Ruff/format/mypy/generated artifacts. Skips are live API and two credential-environment checks; DB and composed web tests ran.

The committed import receipt and exact resume procedure are `docs/build/planning/2026-09-25-six-streams/integration/2026-09-26-after-p31-19.md` and `INTEGRATION_RUNBOOK.md`. Final handoff requires original-checkout fingerprint revalidation and checkout HEAD equal to the pushed PR head. Raw logs stay ignored.
