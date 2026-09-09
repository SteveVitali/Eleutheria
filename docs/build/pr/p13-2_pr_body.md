## Summary

Implements **P13.2 — Policy, legal instruments, and policy/configuration divergence** (`docs/tickets/P13.2__policy-legal.md`).

This is a **stacked PR** on top of `devin/p13-1-accountability`.

The `Policy` / `LegalInstrument` / `ConfigurationState` entities were front-loaded by **P01.1** (LinkML ontology), and the §29.6 policy-vs-configuration divergence reconciler by **P08.2** (`reconcile.policy_config`). This ticket therefore **re-implements nothing in the schema** (the generation gate is untouched); it owns:

- **SIG-EPIS-030 general form** — `connectors.curated_index` (`CuratedSourceIndex` / `CuratedIndexEntry`): a curated bibliography held **as an index** (§10.9). `index_records()` are `index_only`; `as_claims()` raises `IndexNormalizationRefused`. This is the general form of the behaviour the P13.1 `accountability` connector's Abuse Library path relied on — that path now builds a `CuratedIndexEntry` (row shape byte-identical, fully additive).
- **The never-merged invariant** (SIG-ONTO-034) — `Policy` and `ConfigurationState` are distinct classes with disjoint predicate surfaces (schema), and distinct types at the resolution layer.
- **Acceptance tests** for the `Policy` (§11.13) and `LegalInstrument` (§11.14) predicate surfaces.
- ADR-046, a P13.2 traceability section, and a Phase-13 (P13.2) risk-register section.

## What changed

| Area | Change |
|---|---|
| `connectors/src/connectors/curated_index.py` | **NEW** — the SIG-EPIS-030 general capability (`CuratedSourceIndex`, `CuratedIndexEntry`, `IndexNormalizationRefused`). |
| `connectors/src/connectors/accountability.py` | Abuse Library path builds a `CuratedIndexEntry` (relies on the general form); emitted `index_only` row unchanged. |
| `tests/connectors/test_curated_index.py` | **NEW** — SIG-EPIS-030 acceptance tests (AC3). |
| `tests/ontology/test_schema_structure.py` | `Policy` / `LegalInstrument` predicate surfaces; `Policy` ≠ `ConfigurationState` never merged (AC2). |
| `tests/reconcile/test_policy_config.py` | `Policy`/`ConfigurationState` distinct at the resolution layer (AC2). |
| `docs/adr/ADR-046-*.md`, `docs/adr/README.md` | The P13.2 decision record. |
| `docs/traceability.md`, `docs/risk_register.md` | P13.2 traceability + Phase-13 (P13.2) risk entries. |

## Design decisions

- **No schema change / no re-implementation** of front-loaded surfaces; P13.2 lands as tests + the SIG-EPIS-030 module. See ADR-046.
- **SIG-EPIS-030 lives in `connectors/`** because holding an index *as an index* is a connector-stage behaviour (the `normalize()` stage is what would otherwise coin claims), and the seven connectors are its consumers.
- **Additive/back-compat**: the accountability connector's `index_only` advocacy-analysis evidence-link row is byte-identical; no wire name / schema contract changes.

## Verification

- `make check` (lint + format-check + typecheck + full test suite + generation gate) — **green**; the generation gate confirms `ontology/generated` and `pylock.toml` are unchanged (no schema touched).
- Targeted suites: `tests/ontology`, `tests/reconcile/test_policy_config.py`, `tests/connectors/test_curated_index.py`, `tests/connectors/test_accountability.py` — all pass.

## Acceptance criteria → evidence

| AC (P13.2) | Status | Evidence |
|---|---|---|
| Policy/configuration divergence is a rendered finding carrying both sides' evidence, never collapsed (SIG-RECON-044) | met | `tests/reconcile/test_policy_config.py::test_canonical_immigration_divergence_is_a_first_class_finding`, `::test_divergence_must_not_be_collapsed`, `::test_required_but_disabled_is_a_finding` |
| `Policy` and `ConfigurationState` are never merged (SIG-ONTO-034) — schema/resolution test | met | `tests/ontology/test_schema_structure.py::test_policy_and_configuration_state_are_never_merged`; `tests/reconcile/test_policy_config.py::test_policy_and_configuration_are_distinct_and_never_merged` |
| A curated index can be held without normalization (SIG-EPIS-030) | met | `tests/connectors/test_curated_index.py::test_a_curated_index_retains_its_entries_as_an_index`, `::test_index_records_are_index_only_never_claim_rows`, `::test_normalizing_a_curated_index_into_claims_is_refused`, `::test_the_accountability_connector_relies_on_the_general_capability` |
| `Policy` (§11.13) predicate surface (SIG-ONTO-034) | met | `tests/ontology/test_schema_structure.py::test_policy_predicate_surface` |
| `LegalInstrument` (§11.14) predicate surface + edges | met | `tests/ontology/test_schema_structure.py::test_legal_instrument_predicate_surface` |
| Phase-gate (§51.3): CI green, automated tests, ADR for deviation, traceability + risk-register updated | met | `make check` green; ADR-046; `docs/traceability.md` (P13.2); `docs/risk_register.md` (Phase 13 / P13.2, RISK-P13-10..13) |

## Out of scope (guarded)

`AccountabilityEvent` / `LegalProceeding` (P13.1); `ConfigurationState` population + the configuration-cut rule (P01.1 + config-writing connectors); public API / export surfaces over these entities (P14.1 / P14.2).

Spec: `docs/tickets/P13.2__policy-legal.md`

Generated with [Devin](https://devin.ai)
