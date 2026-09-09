## Summary
Seeds the source registry (§22) as **executable data** and adds the `ingestion_permitted` runtime gate every connector passes through. Implements `docs/tickets/P00.4__source-registry.md` (derived from `docs/2_canonical_design_spec.md` §22, §10.3.1, §10.4). Stacked on `devin/p00-3-governance-policies`.

- **Registry as data, not code** (`connectors/src/connectors/data/sources.toml`, 102 rows): every §22.6 A–I row plus the §22.3 additions (cooperative vehicles incl. GSA, agenda/records platforms, DHS fusion centers, FAA drone waivers, …), loaded and validated by `connectors.registry`. Each row carries the SIG-INGEST-023 minimum fields.
- **Rights per source** reuse P00.2's `policy.rights.RightsRecord`: SPDX + a **separately reviewed** `redistributable` never derived from the licence string (SIG-INGEST-024/LIC-003); unresolved sources are `UNDETERMINED` and fail the export gate closed (SIG-LIC-004).
- **`ingestion_permitted` defaults false** — a hard runtime gate (`connectors.loader`, SIG-INGEST-028), not a note.
- **`compact_status`** is the closed SIG-INGEST-027 vocabulary with `no_response` a real recorded state.
- **Eyes on Flock** Stage-0 outreach outcome recorded (SIG-INGEST-030); **DeFlock** canonical host resolved to `deflock.org` not `deflock.me` (REQ-R1-14); **local-group registry** seeded incl. `eyesoffcr.org`, unlocated groups (SIG-INGEST-039a) and the disappeared FlockReporter directory (SIG-INGEST-039b); **national partner roster** (SIG-INGEST-040).

## What changed
- `connectors/`: `registry.py`, `loader.py`, `ecosystem.py`, `_data.py`, `cli.py` (`validate`), `data/sources.toml`, `data/local_groups.toml`; now depends on `sig-policy`.
- `docs/`: ADR-021, traceability P00.4 section, risk-register Phase-0 entries.
- `tests/unit/`: `test_source_registry.py`, `test_ingestion_gate.py`, `test_registry_export_gate.py`, `test_local_group_registry.py` (86 new tests).

## Design decisions (ADR-021)
Registry lives in `connectors` (the ingestion gate is a connector-loader concern; SIG-INGEST-* are ingestion reqs); data-as-TOML matches the `policy/data/*.toml` convention; unresolved rights are `UNDETERMINED` (fail-closed) rather than a guessed licence; "public record" government sources are `UNDETERMINED` with a note (no SPDX for "public record").

## Verification
`make check` green (ruff lint + format, mypy strict, pytest, verify-gen). 330 tests pass (86 new). `python -m connectors validate` reports 102 sources / 82 UNDETERMINED / 0 permitted, 17 local groups (2 unlocated, 1 disappeared), 10 partners.

## Acceptance criteria → evidence
| AC | Evidence |
|---|---|
| `ingestion_permitted` defaults false; connector refuses to run without it (SIG-INGEST-028) | `test_ingestion_gate.py::test_connector_refuses_to_run_when_ingestion_not_permitted`, `test_source_registry.py::test_ingestion_permitted_defaults_false_across_the_seed` |
| Rights populated or explicitly `UNDETERMINED` (SIG-LIC-001) | `test_source_registry.py::test_rights_are_populated_or_explicitly_undetermined` |
| `UNDETERMINED` fails the export gate (SIG-LIC-004) | `test_registry_export_gate.py::test_undetermined_registry_row_fails_the_export_gate_closed` |
| Eyes on Flock outreach outcome recorded (SIG-INGEST-030) | `test_source_registry.py::test_eyes_on_flock_outreach_outcome_is_recorded` |
| DeFlock host `deflock.org`, not `deflock.me` (REQ-R1-14) | `test_source_registry.py::test_deflock_canonical_host_is_org_not_me` |
| Local-group registry seeded (SIG-TASK-014) | `test_local_group_registry.py::test_local_group_registry_exists_and_is_seeded` |
| Phase-gate (§51.3): CI green; new reqs tested; ADR; traceability + risk register updated | `make check`; ADR-021; `docs/traceability.md`; `docs/risk_register.md` |

Implements docs/tickets/P00.4__source-registry.md.

Generated with [Devin](https://devin.ai)

