## Summary
Makes time and provenance **queryable** on the P02.1/P02.2 spine (spec `docs/tickets/P02.3__temporal-provenance.md`, canonical §9, §10, §16.7, §21.6): EDTF encoding with a pinned deterministic envelope, the two as-of axes, the four absence states, the eight temporal invariants, and PROV-O export over the ingest-run lineage — so a citation is reproducible and imprecise dates stay imprecise.

- **EDTF Level 1 + pinned envelope** (`db/src/db/edtf.py`): a deterministic `tstzrange` envelope derivation whose widening rules are the single pinned `ENVELOPE_RULESET_VERSION` an `ingest_run` stamps. "early 2025" (`2025-03~`) → `[2025-01-01, 2025-06-01)`, never `2025-01-01`. (SIG-STORE-021/022, SIG-TIME-006; ADR-024)
- **Bound kinds + ongoing rendering** (`db/src/db/temporal.py`): `valid_to_kind='ongoing'` is rendered with its observation date attached and never as "currently". (SIG-TIME-004/005)
- **As-of query contract**: `claim_as_of` / `resolution_as_of` SQL functions (the shared read-path filter over `valid_period` and `sys_period`) + a Python `AsOf` predicate builder, incl. the fourth belief-pinned form that reproduces a corrected-away value. (SIG-TIME-007/008/009/016; ADR-025)
- **Four absence states** (`db/src/db/absence.py`): `NOT_RESEARCHED` / `NO_EVIDENCE_FOUND` / `EVIDENCE_OF_ABSENCE` / `UNRESOLVED`, distinguishably encoded (→ `coverage_record` / `resolution`) and rendered. (SIG-TIME-010/011/012)
- **Temporal invariants TI-1..TI-8** (`db/src/db/invariants.py`): run-failing pipeline data-quality checks with Hypothesis property tests, plus an additive `temporally_unanchored` flag (+reason) for TI-8. (SIG-TIME-013/014; ADR-025)
- **PROV-O export** (`exports/src/exports/provo.py`, `sig-exports provo`): captures/claims=`prov:Entity`, runs/extractions=`prov:Activity`, connectors/curators/sources=`prov:Agent`, `revises_claim`=`prov:wasRevisionOf`; validated + deterministic serialisation. (SIG-INGEST-015/016)

## What changed
- `db/`: new sqitch change `temporal_invariants` (additive `claim.temporally_unanchored`+reason added to the append-only guard list; `claim_as_of`/`resolution_as_of` functions); new modules `edtf.py`, `temporal.py`, `absence.py`, `invariants.py`.
- `exports/`: `provo.py` + `provo_io.py`; first real CLI sub-command (`provo`); `rdflib` dependency (already present via `ontology`).
- `docs/`: ADR-024, ADR-025 (+ index); traceability P02.3 section; risk register P02.3 (Risk 3 final part retired).
- Tests: `tests/unit/test_edtf.py`, `test_temporal_semantics.py`, `test_absence.py`; `tests/property/test_temporal_invariants.py`; `tests/exports/test_provo.py`; `tests/db/test_as_of.py`.

## Design decisions
- **ADR-024** — in-repo, stdlib-only, version-pinned EDTF envelope (no maintained deterministic Level 1 lib with a versionable widening policy).
- **ADR-025** — invariants as pipeline data-quality checks (complementing the P02.1 physical constraints) and as-of as SQL functions + Python builder, both explicitly permitted by SIG-TIME-013.
- `clock_timestamp()` (not `now()`) as the as-of "latest" default, so "latest belief" is the newest committed claim even inside a long transaction.

## Verification
- `make check` green (twice): ruff lint+format, mypy (76 files), **587 tests**, `verify-gen` clean.
- Live PostgreSQL 18 (testcontainers): `tests/db/test_as_of.py` — a belief-pinned query returns the pre-correction value (25) while current belief returns the corrected one (225); `as_of_world` filters by valid time; the `temporally_unanchored` CHECK fires.
- Live CLI: `python -m exports provo <lineage.json>` emits a valid PROV-O document with the full SIG-INGEST-016 mapping; the no-arg help path still exits 0 (SIG-ENG-013).

### Acceptance criteria → evidence
| AC | Evidence |
|---|---|
| Property tests over TI-1..TI-8 pass (SIG-TIME-013) | `tests/property/test_temporal_invariants.py` (Hypothesis; each invariant holds + fires) |
| `valid_to_kind` ongoing vs unknown, surfaced with observation date (SIG-TIME-004/005) | `tests/unit/test_temporal_semantics.py::test_ongoing_is_rendered_with_the_observation_date`, `::test_currently_phrasing_is_non_conformant` |
| EDTF round-trips; envelope deterministic; "early 2025" ≠ `2025-01-01` (SIG-STORE-021/022) | `tests/unit/test_edtf.py::test_spec_16_7_table_envelopes`, `::test_early_2025_is_not_sharpened_to_jan_1`, `::test_envelope_is_deterministic` |
| §16.6 correction holds at query time: `as_of_belief` before correction returns old value (SIG-TIME-009) | `tests/db/test_as_of.py::test_claim_as_of_belief_returns_prior_belief` (live PG) |
| Four absence states distinguishable; `NOT_RESEARCHED` ≠ `NO_EVIDENCE_FOUND` (SIG-TIME-010/012) | `tests/unit/test_absence.py::test_all_four_states_render_distinguishably`, `::test_not_researched_differs_from_no_evidence_found` |
| PROV-O export validates + maps captures/claims/runs/agents (SIG-INGEST-016) | `tests/exports/test_provo.py` (Entity/Activity/Agent, `wasRevisionOf`, validation) |
| Phase-gate §51.3 (CI green incl DQ checks; new reqs tested; ADRs; traceability; risk register) | `make check` green; ADR-024/025; `docs/traceability.md` P02.3; `docs/risk_register.md` P02.3 |

## Requirement IDs
SIG-TIME-004/005/006/007/008/009/010/011/012/013/014/016, SIG-STORE-021/022, SIG-INGEST-015/016.

## Out of scope (confirmed not done)
Physical claim/resolution DDL, append-only, RLS (P02.1); OCFL store, capture pipeline, `ingest_run` recording (P02.2); observation→validity interval conversion (resolution layer, P08.1/§28).

Implements `docs/tickets/P02.3__temporal-provenance.md`.

Generated with [Devin](https://devin.ai)
