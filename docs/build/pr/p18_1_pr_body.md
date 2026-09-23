## Summary

P18.1 **owns the jurisdiction adapter framework** that P18.2 (France/Belgium) is the first consumer of. The data model is international from the beginning (SIG-CHART-029) and carries **no US-shaped assumption** (SIG-CHART-030, §5.3): a new country plugs in the five things onboarding needs — code system, organization types, legal instruments, records-request vocabulary, publication rules — as data, and a machine-checked checklist proves it needs no `us.*`-only code path.

Implements SIG-CHART-029, SIG-CHART-030, SIG-ONTO-068, SIG-ONTO-069, SIG-PUB-017, SIG-ENG-036, SIG-INGEST-042, realising the §11.1 `Jurisdiction`, §11.2 `Organization`, §11.14 `LegalInstrument` surfaces. Spec: `docs/tickets/P18.1__international-framework.md`; design `docs/2_canonical_design_spec.md` §5.3, §13.7–13.8, §43.8, §52 Phase 18.

Stacked on `devin/p17-3-broader-acoustic-drone-loc`.

## What changed

- **Ontology (SIG-ONTO-068):** the four internationalised enums in `ontology/src/ontology/schema/common.yaml` gain a country-neutral **abstract parent** and national `<cc>.*` children linked via LinkML permissible-value `is_a` — `OrganizationType` (`law_enforcement`/`government` parents + `fr`/`uk`/`de` children), `JurisdictionType` (`fr`/`uk`/`de` levels), `LegalInstrumentType` (`fr.arrete_prefectoral`, `fr.cnil_decision`, `uk`/`eu`/`de`), `AcquisitionMethod` (`records_request` parent). **No `us.*` value is added.** `generate.py` publishes `is_a` as `skos:broader`.
- **Ontology (SIG-ONTO-069):** `Jurisdiction`/`Organization` gain a repeatable `transliteration_scheme` qualifier alongside repeatable BCP-47 `name_lang`.
- **Policy (SIG-CHART-029/030, SIG-PUB-017):** new `policy/src/policy/jurisdiction.py` — `JurisdictionAdapter`, the checklist (`adapter_checklist`/`validate_adapter`), and an airtight `assert_no_us_shaped_assumption` gate (bans `us.*` across **all five** slots incl. code systems; requires own-namespace for country-scoped vocab). Adapters are data (`data/jurisdiction_adapters.toml`: US/FR/UK); `sig-policy jurisdiction` validates them. `adapter_publication_permitted` keeps publication conditional on subject + record-origin jurisdiction; `FR` added to `jurisdictions.toml`.
- **Connectors (SIG-ENG-036/SIG-INGEST-042):** new `connectors/src/connectors/coarse_international.py` — `coarse_claim` stamps explicit country/vendor granularity and `assert_not_disaggregated` refuses agency-level disaggregation. The three §22.7 datasets (Carnegie AI GSI, Facial Recognition World Map, ASPI Mapping China's Tech Giants) registered LINK-posture / `ingestion_permitted = false`.
- **Phase gate:** ADR-056, `docs/traceability.md` (P18.1), `docs/risk_register.md` (Phase 18 — P18.1).

## Design decisions

- **`is_a` for the namespace hierarchy** rather than a naming convention: the abstract-parent relation becomes real `skos:broader`, so cross-country rollups ("any law-enforcement org, any country") are expressible, and "shared abstract parent per concept" is machine-checked.
- **Additive, not restructuring:** no pre-existing permissible value, wire name, or slot is removed/renamed (SIG-ENG-003 back-compat); new slots are optional. `Organization.canonical_name` stays a single-valued claim per §11.2/SIG-ONTO-003 (multilingual org names ride `alias` + `name_lang`); the parallel-slot label shape mirrors the spec's predicate tables — recorded as a deviation in ADR-056.
- **Coarse layer is claim-shape + guard, not a live fetch connector** — the datasets are LINK/UNDETERMINED pending rights review (§22.7); the anti-disaggregation guard holds the moment a connector is wired (P18.2+).

## Verification

- `make check` green: **2322 passed**, lint/format/typecheck clean, `verify-gen` byte-clean (committed generated artifacts equal a fresh deterministic generation).
- New tests: `tests/ontology/test_i18n.py`, `tests/unit/test_jurisdiction_adapter.py`, `tests/connectors/test_coarse_international.py`, plus existing `tests/unit/test_policy_publication.py`.
- Live: `uv run python -m policy jurisdiction` → US/FR/UK OK, 11/11 checklist items each.

### Acceptance criteria → evidence

| AC | Status | Evidence |
|---|---|---|
| Adapter checklist satisfied, **no US-shaped assumption** (SIG-CHART-029/030) | met | `policy.jurisdiction.validate_adapter` + `assert_no_us_shaped_assumption`; `test_non_us_adapter_has_no_us_shaped_code_path`, `test_a_us_term…`/`test_a_us_code_scheme…`/`test_a_foreign_non_us_namespace…_is_rejected` |
| Org + legal-instrument types under a national namespace, **not by widening a US enum**, shared abstract parent (SIG-ONTO-068) | met | `common.yaml` national children + `is_a`; `test_every_non_us_national_child_has_a_shared_abstract_parent`, `test_no_us_enum_was_widened` (frozen us.* set), `test_us_law_enforcement_types_share_the_international_abstract_parent` |
| Multilingual BCP-47 labels render/round-trip (SIG-ONTO-069) | met | `entities.yaml` `name_lang`+`transliteration_scheme`; `test_label_bearing_entity_has_bcp47_and_transliteration_slots`, `test_multilingual_labels_round_trip_and_render` |
| Jurisdiction-conditional publication, subject + origin, different outcomes (SIG-PUB-017) | met | `adapter_publication_permitted`; `test_publication_is_jurisdiction_conditional_across_adapters` (FR-GDPR redacts vs US-DEFAULT publishes) |
| Coarse datasets explicit granularity, **no agency disaggregation** (SIG-ENG-036/INGEST-042) | met | `coarse_international.coarse_claim`/`assert_not_disaggregated`; `test_agency_level_disaggregation_is_refused` (country + vendor × every disaggregated kind) |
| Non-US records vocab incl. `no_equivalent_available` (§52) | met | `fr.cada`/`uk.foi`; `test_non_us_records_request_vocabulary_is_used`, `test_no_equivalent_available_is_a_valid_records_regime_declaration` |
| Phase gate §51.3 | met | ADR-056; traceability P18.1; risk Phase 18; `make check` green |

## Out of scope (P18.2)
France/Belgium connectors, prefectural-order → LegalInstrument, national procurement → Contract, the ~12,000-camera OSM import study.

Generated with [Devin](https://devin.ai)
