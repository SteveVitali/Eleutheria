## Summary
Implements **P01.1 — Ontology as code** (`docs/tickets/P01.1__ontology-as-code.md`; canonical spec §8/§11/§12/§13/§20). One **LinkML source of truth** (ADR-007) plus versioned **vocabulary term lists** generate every downstream form; the whole thing is gated so committed artifacts are byte-identical to a fresh generation.

Toolchain: the **full LinkML toolchain** (per operator decision) — `linkml` drives JSON Schema, OWL, SHACL, Pydantic, SQL DDL, and docs; RDF is emitted as canonical sorted N-Triples and set-ordered output is pinned (`PYTHONHASHSEED=0`) so the SIG-ENG-016 gate is deterministic.

## What changed
- **`ontology/src/ontology/schema/`** — LinkML source: `common.yaml` (types, universal temporal/provenance slots, §13.3/§13.4/§12.4 structural enums), `entities.yaml` (all §11 entities incl. the six `[NEW]`), `edges.yaml` (§12 closed edge catalog; prohibited edges absent), `sig.yaml` (entry).
- **`ontology/vocab/`** — SKOS/registry source: `technology.yaml` (14/36/104, every family with an `-unspecified` leaf, each tech with distinguishing criterion + evidence signature + salience), `capability.yaml` (45 `verb.object.scope` terms incl. export/onward-disclosure + negative governance), `predicates.yaml` (53 predicates, each with volatility+half-life, resolution strategy, and a directness row), `crosswalks.yaml`.
- **`ontology/src/ontology/generate.py`** + `cli.py` — the generators + `sig-ontology generate [--check]`.
- **`ontology/generated/`** — committed artifacts: `jsonschema/`, `pydantic/`, `sql/`, `owl/`, `shacl/`, `skos/{technology,capability,predicate,structural,crosswalks}.nt`, `registry/{predicate_registry,vocab_summary}.json`, `docs/`.
- **`Makefile`** — `gen`/`gen-ontology`/`verify-gen` wired (deterministic).
- **`tests/ontology/`** — schema structure, vocabularies, predicate registry, the generation gate, and the **generalization conformance suite** (SIG-CHART-028).
- Docs: `docs/traceability.md` and `docs/risk_register.md` updated (retires the ontology-churn risk).

## Design decisions
- **LinkML is the single source**; the large open vocabularies (technology tree, capability grammar) live as term lists in `ontology/vocab/` (§13) and bind to slots by IRI, so the 14/36/104 counts have exactly one home. Structural enums (§13.3/§13.4/§13.5) are authored once as LinkML enums and generated to SKOS.
- **Determinism**: RDF → canonical sorted N-Triples; LinkML source-metadata disabled; `CREATE INDEX` runs sorted; `PYTHONHASHSEED=0` pinned in `make gen`.
- **No vendor name in any identifier** (P7): enforced by tests over schema identifiers and vocab slugs (vendor names may still appear in a technology's *evidence-signature* strings, which are evidence, not identifiers).

## Verification
`make check` green: ruff, ruff-format, mypy (57 files), pytest (**380 passed**, incl. 43 new ontology tests), and `make verify-gen` (committed artifacts == fresh generation).

### Acceptance criteria → evidence
| AC | Evidence |
|---|---|
| CI fails if committed artifacts ≠ fresh generation | `make verify-gen`; `test_generation_gate.py::test_committed_artifacts_match_a_fresh_generation` |
| Generalization suite (acoustic sensor; capability w/ no asset; reference DB; commercial data-access; integration hub) | `tests/ontology/generalization/test_generalization.py` (5 scenarios, generated Pydantic instances) |
| Every predicate has volatility, strategy, directness row (SIG-ONTO-067) | `test_predicate_registry.py::test_every_predicate_has_volatility_strategy_and_directness_row` |
| Every technology family has an `-unspecified` leaf | `test_vocabularies.py::test_every_family_has_an_unspecified_leaf` |
| No vendor name in any schema identifier | `test_schema_structure.py::test_no_vendor_name_in_any_schema_identifier`, `test_vocabularies.py::test_no_vendor_name_in_any_vocab_slug` |
| Vocabularies publish at stable per-version IRIs | `test_vocabularies.py::test_vocabularies_publish_at_stable_per_version_iris` |
| Counts 14/36/104 + ~45 capabilities asserted vs artifact | `test_vocabularies.py::test_technology_counts_are_14_36_104`, `::test_capability_vocabulary_shape` |
| Phase-gate §51.3 (CI green incl. gen gate; requirement IDs; retires ontology churn) | `make check`; this PR; `docs/risk_register.md` (RISK-P1-01) |

## Requirement IDs
SIG-CHART-027/028; SIG-ONTO-010…069; SIG-STORE-034…040; SIG-RECON-008…012; SIG-ENG-016.

## Spec
`docs/tickets/P01.1__ontology-as-code.md` → `docs/2_canonical_design_spec.md` §8, §11, §12, §13, §20.

Generated with [Devin](https://devin.ai)

