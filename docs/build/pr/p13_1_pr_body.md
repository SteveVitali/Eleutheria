## Summary
Brings accountability into the graph as first-class, **epistemically-honest** records, per the P13.1 ticket (canonical §§11.17–11.18, §23.8, §13.3). Stacked on `devin/p12-2-network-inference`.

- **`epistemic_status` — required and preserved end to end (SIG-ONTO-038).** REQUIRED at write (rejected if absent), carried **verbatim** from the upstream where provided (raw kept beside the typed vocabulary term), emitted under the ontology's registered `event_epistemic_status` predicate so it survives `RESOLVE()` unchanged, and never flattened to "X happened".
- **Six-source-class evidence links (SIG-ONTO-039).** New `SourceClass` enum (the six OL-2E-AL-03 classes) + an index-aligned `source_classes` slot on `AccountabilityEvent`; every evidence link records its class, so an advocacy-only claim is distinguishable from a court-record claim.
- **The `accountability` connector (§23.8).** On the P04.1 eight-stage framework: consumes the Accountability Atlas's **five** artifacts (issue-record CSV, source-index CSV, GeoJSON, data dictionary, research archive), the **Abuse Library** (as an index, never normalized to facts — OL-2E-AL-02), and **CourtListener/RECAP** as **targeted-lookup only** (§22.2). Crosswalks the upstream record categories (never adopts them wholesale), with a predicate allowlist as a hard schema gate (Policy/LegalInstrument are P13.2 — refused here).
- **Render guard (`exports.accountability`).** An event's verb is governed by its epistemic status; `assert_not_flattened` refuses to render an `alleged`/`disputed`/`retracted` event as a confirmed fact (OL-2E-AA-05).

Requirement IDs: **SIG-ONTO-038, SIG-ONTO-039**, §11.18 `LegalProceeding`, §23.8 `accountability` connector; SIG-INGEST-033/034/036/037 realized at the ingest boundary.

## What changed
- `ontology/schema/common.yaml` (`SourceClass`), `entities.yaml` (`AccountabilityEvent.source_classes`); regenerated `ontology/generated/**` (deterministic).
- `connectors/src/connectors/accountability.py` + `data/accountability_vocab.toml`; registered in `connectors/__init__.py`.
- `exports/src/exports/accountability.py` (render guard).
- Tests: `tests/connectors/test_accountability.py`, `tests/exports/test_accountability_render.py`, `tests/reconcile/test_resolve.py` (+preservation), `tests/ontology/test_schema_structure.py` (+SourceClass/slot).
- `docs/traceability.md` + `docs/risk_register.md` (P13.1 sections).

## Design decisions
- **No ADR:** implements the canonical design directly (crosswalk mirrors the `atlas` connector; targeted-lookup mirrors `records`; predicate allowlist is the standard connector gate). No deviation.
- Connector vocabularies mirror the frozen ontology enums with lock-step tests (drift fails CI).
- `source_classes` is a **new optional** slot — additive/back-compat; no prior wire name or enum changed.

## Verification
- `ruff check` + `ruff format --check`: clean (connectors, exports, tests).
- `mypy -p connectors -p exports -p ontology`: no issues.
- `pytest tests/connectors tests/exports tests/reconcile tests/ontology tests/unit tests/acceptance`: **1137 passed**.
- Ontology generation deterministic (two consecutive gens byte-identical; working tree == fresh gen, so `make verify-gen` passes post-merge).

### Acceptance criteria → evidence
| AC | Evidence |
|---|---|
| `epistemic_status` required + preserved end to end | `test_accountability::test_epistemic_status_is_required_on_write`, `::test_epistemic_status_is_preserved_verbatim_on_the_claim_rows`, `::test_an_upstream_epistemic_label_is_normalized_but_kept_verbatim`; `test_resolve::test_event_epistemic_status_is_preserved_verbatim_through_resolution` |
| An allegation never renders with a factual verb | `test_accountability_render::test_the_three_named_non_factual_statuses_never_render_as_a_bare_fact`, `::test_the_guard_rejects_an_allegation_phrased_as_a_fact`, `::test_the_guard_requires_the_epistemic_qualifier_on_the_surface` |
| Incidents link to all six source classes with the class recorded; advocacy-only distinguishable from court-record | `test_accountability::test_an_incident_links_to_all_six_source_classes_with_the_class_recorded`, `::test_advocacy_only_claim_is_distinguishable_from_a_court_record_claim`; `test_schema_structure::test_source_class_is_the_six_ol_2e_al_03_classes` |
| Phase-gate: tests + traceability + risk register; ADR if deviation | new automated tests for every requirement; `docs/traceability.md` + `docs/risk_register.md` P13.1 sections; no deviation ⇒ no ADR |

Implements `docs/tickets/P13.1__accountability.md`.

Generated with [Devin](https://devin.ai)
