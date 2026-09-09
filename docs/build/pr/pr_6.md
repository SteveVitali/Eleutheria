Implements ticket **P02.1** — the relational core that makes every defining-standard invariant *physically enforceable*. Authored against the normative DDL of `docs/2_canonical_design_spec.md` §16 + Appendix C, as **sqitch** migrations in `db/`. Stacked on `devin/p01-1-ontology-as-code`.

## Summary
- Physical **L0–L3 claim/evidence/resolution spine** + domain entity/edge/annotation tables + the L4 `inference` schema, on PostgreSQL 18 + PostGIS with `uuidv7()` PKs (ADR-001).
- **Append-only** claim table enforced in the DB (§16.3): a trigger forbids `DELETE` and permits only closing `sys_period`, driven by a **schema-generated** mutable-column guard list; app roles hold no `DELETE` (SIG-STORE-011/012/013).
- **Resolution** as a stored decision record with a **GiST exclusion constraint** guaranteeing at most one current value per `(subject, predicate, valid instant)` — in the database, not application code (SIG-STORE-014/016).
- **Sensitivity-tier RLS** (§16.8, ADR-012): restrictive policies; public role holds no `BYPASSRLS`; export role with `row_security=off` **fails loudly** (SIG-STORE-023/024).
- **Schema-integrity guards**: entity tables hold no predicate-duplicating columns (SIG-STORE-009); no plate-capable column and the other §C.7 absences (SIG-STORE-026/047).

## What changed
- `db/` — sqitch project (`sqitch.conf`, `sqitch.plan`, 16 changes × deploy/revert/verify), `db/README.md`, `psycopg` dep.
- `tests/db/` — a real-Postgres harness (testcontainers spins up PG18+PostGIS and applies this sqitch plan) + AC tests.
- `.github/workflows/ci.yml` — DB tests run blocking (`SIG_REQUIRE_DB_TESTS=1`); `Makefile` `test-db` target.
- `docs/adr/ADR-022` (partitioning deferral), `docs/traceability.md`, `docs/risk_register.md` (Phase 2).

## Design decisions
- **sqitch is run from its official Docker image** on a shared network, so local dev and CI need only Docker (no host Perl); it is genuinely `sqitch deploy` (SIG-STORE-041).
- **Exclusion constraint, not native `PERIOD/WITHOUT OVERLAPS`.** The ticket in-scope wording mentions native temporal primitives, but the normative §16 DDL and AC4 both mandate `tstzrange` + GiST `EXCLUDE`, and PG18 ships no temporal primary keys — implemented per the normative DDL.
- **`claim` is not physically partitioned** — see ADR-022. Partitioning by nullable `observed_at` is incompatible with `claim_id` being the single-column FK target the whole schema depends on; no AC needs it.

## Verification
- Live: PostgreSQL **18.6** + PostGIS **3.6.4** via testcontainers; sqitch `deploy` + `verify` both clean across all 16 changes.
- `make check` green: lint, format, typecheck, tests (**25** DB tests + existing suite), `verify-gen`.

### Acceptance criteria → evidence
| AC | Requirement | Evidence |
|---|---|---|
| AC1 | UPDATE/DELETE on `claim` rejected except closing `sys_period` | `tests/db/test_append_only.py` (update/delete blocked; sys_period close ok; lower-bound immutable; already-closed rejected) + role-DELETE revocation |
| AC2 | Entity tables contain no attribute columns | `test_schema_integrity.py::test_entity_tables_hold_no_duplicate_predicate_columns` (vs the generated predicate registry; cached/typing allowlist per SIG-STORE-046) |
| AC3 | §16.6 correction: `as_of_belief` before the correction returns the old value | `test_corrections.py::test_correction_preserves_prior_belief` (prior=25, current=225, both rows retained) |
| AC4 | Resolution overlap prevented by exclusion constraint, not app code | `test_resolution_exclusion.py` (overlap rejected; `contype='x'`; superseded row frees the window) |
| AC5 | RLS tests pass for every role × tier (visibility + non-visibility) | `test_rls.py` (3 read roles × tiers; no `BYPASSRLS`; export fails loud; forced RLS) |
| AC6 | No plate-capable column — schema test | `test_schema_integrity.py::test_no_plate_capable_column_anywhere` (SIG-STORE-026) |
| AC7 | Phase gate §51.3: CI green incl. schema/data-quality; requirement IDs; retires Risk 3 (part) | `make check` green; requirement IDs in `docs/traceability.md`; Risk 3 (part) in `docs/risk_register.md` |

**Requirement IDs:** SIG-STORE-008/009/010/011/012/013/014/015/016/017/019/020/023/024/026/041/046/047; SIG-ONTO-001/002/003. Retires **Risk 3** (a claim/temporal model that cannot express contradiction) in part.

**Out of scope (confirmed not done):** OCFL bytes / capture pipeline (P02.2); EDTF envelope + as-of query functions + PROV-O export (P02.3 — columns/hooks only here); resolver *write* logic (P08.1 — table + constraints only here).

Spec: `docs/tickets/P02.1__claim-spine.md`; `docs/2_canonical_design_spec.md` §16, Appendix C.

Generated with [Devin](https://devin.ai)

