# Traceability matrix

Every executable requirement each Phase-0 ticket satisfies, mapped to where it
lives and the automated test that fails if it is removed (SIG-ENG-004). This is
the ticket-scoped view; the full Appendix A matrix is maintained in
`docs/research/_meta/OUTLINE_TRACE.md`. Sections are grouped by ticket
(P00.2 first, then P00.3 below).

# P00.2 — executable policy and the decision record

## Crawler conduct (§26)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-036 (eight operative rules; robots/content-signal) | `policy/crawler.py`, `data/crawler_conduct.toml` | `test_policy_crawler.py` |
| SIG-INGEST-037 (no-circumvention as legal posture) | `policy.crawler.assert_no_circumvention` | `test_policy_crawler.py::test_circumvention_techniques_are_rejected` |

## Licensing (§42)

| Requirement | Where | Test |
|---|---|---|
| SIG-LIC-001 (rights-record shape) | `policy/rights.py::RightsRecord` | `test_policy_licensing.py` |
| SIG-LIC-003 (redistributable separate, not derived) | `RightsRecord.redistributable`; `assert_export_permitted` | `test_..._redistributable_is_a_separate_boolean...` |
| SIG-LIC-004 (UNDETERMINED fails export gate closed) | `policy.licensing.assert_export_permitted` | `test_..._undetermined_fails_export_gate_closed` |
| SIG-LIC-004a (N-compartment model, data not code) | `data/licenses.toml`; `policy.licensing` | `test_..._compartments_are_data_not_code` |
| SIG-LIC-004b (ai_training_permitted first-class) | `RightsRecord.ai_training_permitted` | `test_policy_licensing.py` |
| SIG-LIC-004c (ai-train=no not routed to training) | `policy.licensing.assert_training_allowed` | `test_..._training_gate_blocks_non_permitted_content` |
| SIG-LIC-005 (SIG's own licences) | `data/licenses.toml`; `LICENSE` | `test_..._sig_own_licence_compartments_present` |
| SIG-LIC-006 (ODbL Strategy B) | ADR-011; `data/licenses.toml` (osm_physical) | `test_policy_adrs.py`; `test_..._two_share_alike_regimes...` |
| SIG-LIC-009a (silently-travelling share-alike → stricter) | `policy.licensing.effective_license` | `test_..._silently_travelling_share_alike...` |
| SIG-LIC-010 (export licence computed; build fails on incompat.) | `policy.licensing.compute_export_license` | `test_..._deliberate_cross_compartment_merge_fails_the_build` |
| SIG-LIC-011 (pass obligations downstream) | rights record carries attribution/provenance per source | `test_policy_licensing.py` |

## Publication (§43, §19.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-PUB-002/003 (categorical exclusions) | `policy/publication.py`, `data/exclusions.toml` | `test_..._categorically_excluded_data_cannot_be_stored` |
| SIG-PUB-003a/b/c (de-pseudonymisation prohibition) | `policy.publication.hash_operator_identifier`, `assert_no_operator_join` | `test_..._operator_joinable_surface_is_forbidden` |
| SIG-PUB-004 (C1–C5 matrix) | `policy/sensitivity.py`, `data/sensitivity.toml` | `test_..._each_class_produces_specified_precision` |
| SIG-PUB-005 (residential demotion; leak veto) | `policy.sensitivity.demote_for_residential_parcel`, `requires_human_review` | `test_..._residential_parcel_demotes_to_c3` |
| SIG-PUB-007 (five-prong officer test) | `policy/officer.py` | `test_policy_officer.py` |
| SIG-PUB-008 (two-reviewer concurrence recorded) | `policy.officer.evaluate_officer_naming` | `test_..._missing_second_reviewer_rejects` |
| SIG-PUB-009/010 (home address / audit rows out of test) | `evaluate_officer_naming` carve-outs | `test_..._home_address_is_outside_the_test_entirely` |
| SIG-PUB-011/013 (candidate never published on residential parcel) | `policy.sensitivity.candidate_publishable` | `test_..._candidate_on_residential_parcel_is_never_published` |
| SIG-GEO-009 (deterministic offset, no jitter) | `policy.sensitivity.deterministic_offset` | `test_..._obfuscation_offset_is_deterministic_not_random`; property test |
| SIG-PUB-017 (jurisdiction-conditional) | `policy.publication.publication_permitted`, `data/jurisdictions.toml` | `test_..._jurisdiction_conditional_publication` |

## Threat model (§44)

| Requirement | Where | Test |
|---|---|---|
| SIG-SEC-001 (versioned artifact; every row maps to a requirement id) | `policy/threat_model.py`, `data/threat_model.toml` | `test_policy_threat_model.py` |

## Decision record (§15.5) & stack

| Requirement | Where | Test |
|---|---|---|
| SIG-STORE-006 (ADR-001…012 recorded) | `docs/adr/` | `test_policy_adrs.py::test_all_required_adrs_exist` |
| SIG-STORE-007 (every ADR names a revisit trigger) | `docs/adr/` | `test_..._every_adr_names_a_revisit_trigger` |
| SIG-INGEST-020 (Dagster) | ADR-016 | `test_policy_adrs.py` |
| SIG-ENG-014 (policy is real, tested code) | `policy/` package | `test_policy_package.py` + all policy tests |

---

# P00.3 — Governance, takedown, and contributor safety

The two load-bearing distinctions (corrections preserve history; suppression is
not deletion) are executable and tested; the remaining governance requirements
are prose policy under `docs/governance/`, each with a presence/link/verbatim
test where it is deterministically checkable.

## Takedown, corrections & suppression (§45)

| Requirement | Where | Test |
|---|---|---|
| SIG-GOV-001 (intake channel; categories) | `data/takedown.toml` `[intake]`; `governance.intake_categories` | `test_governance_policy.py::test_intake_categories_cover_the_required_kinds` |
| SIG-GOV-002 (intake needs no identity, save legal standing) | `governance.identity_required_for` | `test_..._intake_does_not_require_identity_by_default` |
| SIG-GOV-003 (SLAs; privacy/safety prioritised above all) | `data/takedown.toml`; `governance.intake_categories` | `test_..._sla_prioritises_privacy_and_safety` |
| SIG-GOV-004 (outcomes incl. refuse-with-reasoning) | `data/takedown.toml` `[[outcomes]]`; `governance.permitted_outcomes` | `test_..._permitted_outcomes_include_refusal` |
| SIG-GOV-005 (correction = new assertion; as_of_belief preserved) | `policy.governance.BeliefLog.correct`/`value_as_of_belief` | `test_..._correction_preserves_prior_belief`; `test_..._correction_is_a_new_assertion_not_a_deletion` |
| SIG-GOV-006 (public corrections log) | `docs/governance/takedown-corrections-suppression.md` | `test_governance_docs.py::test_takedown_doc_covers_suppression_and_corrections` |
| SIG-GOV-007 (suppression distinct from deletion; sealed tier) | `policy.governance.BeliefLog.suppress`/`public_value_as_of_belief` | `test_..._suppression_is_distinct_from_deletion` |
| SIG-GOV-008 (true deletion: two-person auth; tombstone) | `policy.governance.BeliefLog.delete` | `test_..._deletion_requires_two_person_auth_and_leaves_tombstone` |
| SIG-GOV-009 (governance-mode Object Lock rationale) | `docs/governance/takedown-corrections-suppression.md` | `test_governance_docs.py::test_takedown_doc_covers_suppression_and_corrections` |
| SIG-GOV-010 (dispute response published alongside) | `docs/governance/takedown-corrections-suppression.md` | `test_governance_docs.py` (published+linked) |
| SIG-GOV-011 (transparency report by category × outcome incl. refusals) | `data/takedown.toml` `[transparency_report]`; `governance.transparency_report_shape` | `test_..._transparency_report_groups_category_by_outcome_including_refusals` |

## Governance & Code of Conduct (§46.2, §46.4–46.5)

| Requirement | Where | Test |
|---|---|---|
| SIG-GOV-014 (decision-making, CoC w/ enforcement, dispute res) | `docs/governance/governance-and-code-of-conduct.md` | `test_governance_docs.py` (published+linked) |
| SIG-GOV-015 (editorial board distinct from maintainers) | `docs/governance/governance-and-code-of-conduct.md` | `test_governance_docs.py` (published+linked) |
| SIG-GOV-016 (capture resistance incl. funding policy) | `docs/governance/governance-and-code-of-conduct.md` | `test_governance_docs.py` (published+linked) |
| SIG-GOV-021 (degraded-mode-tested posture; documented here) | `docs/governance/governance-and-code-of-conduct.md` | `test_governance_docs.py` (published+linked) |

## Anti-misuse statement (§46.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-GOV-019 (honest anti-misuse statement, verbatim first-class page) | `docs/governance/anti-misuse-statement.md` | `test_governance_docs.py::test_anti_misuse_statement_published_verbatim` |

## Contributor safety (§34.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-CONTRIB-005 (PII minimisation window; what is not stored) | `docs/governance/contributor-safety.md` | `test_governance_docs.py::test_contributor_safety_documents_pseudonymity_and_pii_window` |
| SIG-CONTRIB-006 (pseudonymity incl. trusted-reviewer) | `docs/governance/contributor-safety.md` | `test_..._contributor_safety_documents_pseudonymity_and_pii_window` |
| SIG-CONTRIB-007 (know-your-rights; no trespass/interfere) | `docs/governance/contributor-safety.md` | `test_..._contributor_safety_documents_pseudonymity_and_pii_window` |
| SIG-CONTRIB-008 (detained/arrested/harassed policy) | `docs/governance/contributor-safety.md` | `test_..._contributor_safety_documents_pseudonymity_and_pii_window` |

---

# P00.4 — Seeded source registry

The source registry is executable data (SIG-ENG-001): every §22.6 / §22.3 source
is a row in `connectors/src/connectors/data/sources.toml`, loaded and validated
by `connectors.registry`; the local-group and partner registries live in
`data/local_groups.toml` (`connectors.ecosystem`); the ingestion gate is
`connectors.loader`. Rights records reuse P00.2's `policy.rights.RightsRecord`
and its export gate (`policy.licensing`).

## Registry schema & seed (§22.1, §22.6, §10.3.1)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-023 (registry row minimum fields) | `connectors.registry.SourceRecord`; `data/sources.toml` | `test_source_registry.py::test_every_source_carries_the_minimum_fields` |
| SIG-INGEST-038 (every §22.6 row seeded) | `data/sources.toml` | `test_..._named_seed_row_is_registered`, `test_..._registry_is_non_trivially_seeded` |
| SIG-INGEST-026 (§22.3 additions incl. cooperative vehicles, agenda/records platforms) | `data/sources.toml` | `test_..._section_22_3_addition_is_registered` |
| REQ-R1-14 / SIG-TASK-014 (DeFlock canonical host `deflock.org`, not `deflock.me`) | `data/sources.toml` `[sources.deflock]` | `test_..._deflock_canonical_host_is_org_not_me` |

## Rights per source (§42.1, SIG-LIC-*)

| Requirement | Where | Test |
|---|---|---|
| SIG-LIC-001 (rights record populated or explicitly UNDETERMINED) | `registry._rights_from_row` → `policy.rights.RightsRecord` | `test_..._rights_are_populated_or_explicitly_undetermined` |
| SIG-INGEST-024 / SIG-LIC-003 (`redistributable` separately reviewed, not derived) | `registry._rights_from_row` (fail-closed default) | `test_..._redistributable_is_never_derived_from_the_licence_string` |
| SIG-LIC-004 (UNDETERMINED fails the export gate closed) | `policy.licensing.assert_export_permitted` over registry rights | `test_registry_export_gate.py::test_undetermined_registry_row_fails_the_export_gate_closed` |
| SIG-INGEST-048b (AGPL / no-licence hazards) | `data/sources.toml` (`sm_alpr`, `deflock_app_repo`, `ringmast4r_flock`) | `test_..._agpl_projects_are_marked_non_derivative_licence_hazards`, `test_..._unlicensed_projects_are_undetermined...` |

## Compact & the ingestion gate (§22.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-027 (`compact_status` closed vocab incl. `no_response`) | `registry.CompactStatus` | `test_..._compact_status_is_the_closed_vocabulary_including_no_response` |
| SIG-INGEST-028 / SIG-CHART-032 (connector refuses to run when `ingestion_permitted` false) | `connectors.loader.assert_ingestion_permitted` / `run_connector` | `test_ingestion_gate.py::test_connector_refuses_to_run_when_ingestion_not_permitted` |
| SIG-INGEST-028 (`ingestion_permitted` defaults false) | `registry.SourceRecord.ingestion_permitted` | `test_..._ingestion_permitted_defaults_false_across_the_seed` |

## Eyes on Flock & the ecosystem registries (§22.5, §22.6 H)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-030 (Eyes on Flock Stage-0 outreach outcome recorded — Phase 11 blocker) | `data/sources.toml` `[sources.eyes_on_flock]` | `test_..._eyes_on_flock_outreach_outcome_is_recorded` |
| SIG-INGEST-039 / SIG-TASK-014 (local-group registry seeded incl. `eyesoffcr.org`) | `data/local_groups.toml`; `connectors.ecosystem.local_groups` | `test_local_group_registry.py::test_local_group_registry_exists_and_is_seeded` |
| SIG-INGEST-039a (unlocated groups not silently dropped) | `data/local_groups.toml` (`deflock_idaho`, `monterey_park_organizers`) | `test_..._unlocated_groups_are_registered_as_a_coverage_fact` |
| SIG-INGEST-039b (FlockReporter disappeared, `disappeared_observed_at`) | `data/local_groups.toml` `[groups.flockreporter]` | `test_..._flockreporter_directory_is_disappeared_with_observation_date` |
| SIG-INGEST-040 (national partners registered with contacts) | `data/local_groups.toml` `[partners.*]`; `connectors.ecosystem.partners` | `test_..._national_partners_registered_with_contacts` |

# P01.1 — Ontology as code + vocabularies

The single LinkML source (`ontology/src/ontology/schema/`) plus the versioned
vocabulary term lists (`ontology/vocab/`) generate every downstream form; the
generator is `ontology/src/ontology/generate.py`, driven by `sig-ontology generate`
and gated by `make verify-gen`. Committed artifacts live under `ontology/generated/`.

## Single source and the generation gate (§20.1, SIG-STORE-034, SIG-ENG-016)

| Requirement | Where | Test |
|---|---|---|
| SIG-STORE-034 (one LinkML source → SQL DDL, JSON Schema, OWL/SHACL, Pydantic, docs) | `ontology.generate` (LinkML gen-* drivers); `ontology/generated/{sql,jsonschema,owl,shacl,pydantic,docs}` | `test_generation_gate.py::test_every_downstream_form_is_committed` |
| SIG-ENG-016 / AC1 (CI fails if committed ≠ fresh generation) | `ontology.generate.generate(check=True)`; `make verify-gen` | `test_generation_gate.py::test_committed_artifacts_match_a_fresh_generation` |

## Entities and edges (§11, §12)

| Requirement | Where | Test |
|---|---|---|
| §11 entity catalog incl. [NEW] (SIG-ONTO-010/014/029/033, §11.14/§11.19) | `schema/entities.yaml` | `test_schema_structure.py::test_every_section_11_entity_is_a_class`, `::test_new_entities_are_present` |
| SIG-ONTO-041 (edges directed, typed from a closed catalog, time-bounded, evidenced, perspectival) | `schema/edges.yaml` (`Edge`, `EdgeType`) | `test_schema_structure.py::test_edge_type_is_a_closed_catalog_with_every_section_12_edge`, `::test_edges_carry_universal_requirements` |
| SIG-ONTO-045/050 (no stored `integrates_with`; no undifferentiated `shares_with`) | `schema/edges.yaml` `EdgeType` (prohibited absent) | `test_schema_structure.py::test_prohibited_edges_are_absent` |
| §0.7 / N1 / N4 / SIG-ONTO-037 (no plate/trip/per-person column) | `schema/*.yaml` (absence) | `test_schema_structure.py::test_no_plate_trip_or_per_person_slot_exists` |
| §11.3 / SIG-ONTO-014/015/016 (Person tightly constrained; required public-interest basis + human review) | `schema/entities.yaml` `Person` | `test_schema_structure.py::test_person_is_tightly_constrained` |
| SIG-ONTO-049 (sharing never reduced to `shares_with`; direction/scope/kind required) | `schema/edges.yaml` `AccessRelationship` | `generalization/test_generalization.py::test_access_relationship_requires_direction_scope_and_kind` |

## Controlled vocabularies as SKOS (§13, §20.2)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-052/052a (14 domains / 36 families / 104 technologies, asserted vs artifact) | `vocab/technology.yaml`; `generated/registry/vocab_summary.json` | `test_vocabularies.py::test_technology_counts_are_14_36_104` |
| SIG-ONTO-020/054 / AC4 (every family has an `-unspecified` leaf) | `vocab/technology.yaml` | `test_vocabularies.py::test_every_family_has_an_unspecified_leaf` |
| SIG-ONTO-056 (each technology: distinguishing criterion, evidence signature, salience) | `vocab/technology.yaml` | `test_vocabularies.py::test_every_technology_carries_criterion_signature_and_salience` |
| SIG-ONTO-023/024/060 (~45 `verb.object.scope` capabilities incl. export/onward-disclosure) | `vocab/capability.yaml` | `test_vocabularies.py::test_capability_vocabulary_shape` |
| SIG-ONTO-022/053/055 / AC5 (no vendor name in any identifier; stable lowercase-hyphenated slugs) | `schema/*.yaml`, `vocab/*.yaml` | `test_schema_structure.py::test_no_vendor_name_in_any_schema_identifier`, `test_vocabularies.py::test_no_vendor_name_in_any_vocab_slug` |
| §13.3/§13.4/§13.5 as SKOS (evidence/epistemics, four lifecycle tracks, org/acquisition/role enums) | `ontology.generate.build_structural_skos`; `generated/skos/structural.nt` | `test_vocabularies.py::test_structural_vocabularies_are_published_as_skos` |
| SIG-STORE-035 / AC6 (versioned SKOS schemes at stable per-version IRIs) | `ontology.generate` SKOS builders; `generated/skos/*.nt` | `test_vocabularies.py::test_vocabularies_publish_at_stable_per_version_iris` |
| SIG-ONTO-068/069 (i18n: country-namespaced enums; BCP-47 labels) | `schema/common.yaml` (`bcp47`, namespaced enums), `name_lang` slots | `test_schema_structure.py` (enum presence); `test_vocabularies.py` |

## Predicate registry (§13.6)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-066/067 / AC3 (every predicate: volatility class + half-life, resolution strategy, directness row) | `vocab/predicates.yaml`; `generated/registry/predicate_registry.json` | `test_predicate_registry.py::test_every_predicate_has_volatility_strategy_and_directness_row` |
| SIG-RECON-010 (recency must not break IMMUTABLE/GLACIAL ties) | `vocab/predicates.yaml` | `test_predicate_registry.py::test_immutable_and_glacial_predicates_use_non_recency_strategies` |
| SIG-RECON-012 / §12.4 (contested facts never resolved) | `vocab/predicates.yaml` (`asset_data_controller`) | `test_predicate_registry.py::test_contested_facts_are_never_resolved` |

## Generalization conformance suite (§5.2, SIG-CHART-027/028)

| Requirement | Where | Test |
|---|---|---|
| SIG-CHART-028 / AC2 (acoustic sensor; capability with no asset; reference database; commercial data-access; integration hub — all expressible) | `tests/ontology/generalization/`; generated Pydantic models | `generalization/test_generalization.py` (five scenarios) |

## Crosswalks (§20.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-STORE-039/040, SIG-ONTO-058 (many-to-many external crosswalks with SKOS mapping relation + `lossy` flag) | `vocab/crosswalks.yaml`; `generated/skos/crosswalks.nt` | `test_generation_gate.py::test_every_downstream_form_is_committed` (`skos/crosswalks.nt`) |

# P02.1 — The bitemporal claim spine

The physical schema lives in `db/` as sqitch changes (deploy/revert/verify) and is
exercised against a real PostgreSQL 18 + PostGIS instance in `tests/db/`
(testcontainers stands up the engine and applies the sqitch plan; SIG-STORE-024).

## Canonical schema (§16)

| Requirement | Where | Test |
|---|---|---|
| SIG-STORE-008 / AC (entity tables hold identity only) | `db/deploy/entity.sql`, `db/deploy/domain_entities.sql` | `test_schema_integrity.py::test_entity_tables_hold_no_duplicate_predicate_columns` |
| SIG-STORE-009 / AC2 (no entity column duplicates a registered predicate) | `db/deploy/domain_entities.sql`; predicate registry from P01.1 | `test_schema_integrity.py::test_entity_tables_hold_no_duplicate_predicate_columns` |
| SIG-STORE-010 (UUIDv7 primary keys via `uuidv7()`) | `db/deploy/entity.sql`, `db/deploy/claim.sql`, … | deploy applies on PG18 (`conftest.sig_database`); ADR-022 |
| SIG-STORE-011 / AC1 (append-only enforced in the DB; generated guard column list) | `db/deploy/claim_append_only.sql` | `test_append_only.py::test_update_of_a_value_column_is_rejected`, `::test_guard_column_list_matches_the_live_schema` |
| SIG-STORE-012 (no DELETE for app roles on append-only tables) | `db/deploy/access_control.sql` (REVOKE DELETE) | `test_append_only.py::test_delete_is_rejected` (trigger, defence-in-depth) |
| SIG-STORE-013 (sys_period lower immutable; upper set only on correction) | `db/deploy/claim_append_only.sql` | `test_append_only.py::test_sys_period_lower_bound_is_immutable`, `::test_closing_sys_period_is_permitted` |
| SIG-STORE-014/016 / AC4 (resolution is a stored decision record; non-overlap by exclusion constraint, not app code) | `db/deploy/resolution.sql` (`resolution_no_overlap` GiST EXCLUDE) | `test_resolution_exclusion.py::test_overlapping_current_resolutions_are_rejected`, `::test_exclusion_is_a_database_constraint` |
| SIG-STORE-015 (`unresolved_conflict` is a publishable outcome) | `db/deploy/resolution.sql` (`contradiction_state`) | `verify/resolution.sql`; column present |
| SIG-STORE-017/019 (resolver/ruleset versions independent; human override first-class) | `db/deploy/resolution.sql` | `verify/resolution.sql` |
| SIG-STORE-020 / AC3 (corrections close sys_period + new claim with revises_claim; prior belief preserved) | `db/deploy/claim.sql` (`claim_correction_reasoned`) | `test_corrections.py::test_correction_preserves_prior_belief`, `::test_correction_requires_a_reason` |
| SIG-STORE-023 / AC5 (restrictive RLS by tier; public role no BYPASSRLS; export row_security=off fails loud) | `db/deploy/access_control.sql`, ADR-012 | `test_rls.py::test_tier_visibility_per_role`, `::test_public_role_holds_no_bypassrls`, `::test_export_role_fails_loudly_with_row_security_off` |
| SIG-STORE-024 (RLS policy tests CI-blocking, every role × tier) | `.github/workflows/ci.yml` (`SIG_REQUIRE_DB_TESTS`) | `test_rls.py::test_tier_visibility_per_role[*]` |
| SIG-STORE-026 / AC6 (no plate-capable column anywhere) | schema (absence, by construction) | `test_schema_integrity.py::test_no_plate_capable_column_anywhere` |
| SIG-STORE-041 (physical migrations managed with sqitch, deploy/revert/verify) | `db/sqitch.plan`, `db/deploy/`, `db/revert/`, `db/verify/` | `conftest.sig_database` (sqitch deploy); `db/verify/*` |
| SIG-STORE-047 / §C.7 (forbidden columns/tables never exist) | schema (absence) | `test_schema_integrity.py::test_no_per_search_sighting_or_trip_table`, `::test_person_has_no_address_column`, `::test_claim_has_no_stored_currency_column`, `::test_integrates_with_edge_value_is_forbidden` |
| SIG-ONTO-001/002 (six-layer model; L4 inference a separate schema) | `db/deploy/inference_schema.sql` (`inference.*`) | `verify/inference_schema.sql` |

# P02.2 — The OCFL evidence store

The write-once evidence layer lives in the new `evidence/` package (ADR-023): the
content-addressing codec, the OCFL 1.1 writer/reader, the S3/Object-Lock backend,
the storage-tier model, the WACZ capture pipeline, redaction, disappearance, and
ingest-run reproducibility. The byte-level schema (dedup blob registry,
`source_uri` uniqueness, redaction guard, audited access log) is a new sqitch
change `db/deploy/evidence_store.sql`, exercised against a real PG18 in
`tests/db/test_evidence_store.py`.

## Content addressing (§17.2)

| Requirement | Where | Test |
|---|---|---|
| SIG-EVID-002 (digests stored as multihash, base32-lowercase) | `evidence/digest.py::multihash` | `test_digest.py::test_multihash_is_base32_lowercase_multibase`, `::test_decoded_multihash_matches_reference_multiformats_encoding` |
| SIG-EVID-003 (interop digest SHA-256/512; BLAKE3 additionally for fixity) | `evidence.digest` (`INTEROP_ALGOS`, `blake3_hex`) | `test_digest.py::test_interop_digest_must_be_sha2_not_blake3`, `::test_blake3_fixity_is_hex_and_stable` |
| SIG-EVID-004 (dedup by digest; `(content_digest, source_uri)` unique; 1 blob / N rows) | `db/deploy/evidence_store.sql` (`evidence_blob` PK); `evidence.store` | `tests/db/test_evidence_store.py::test_source_uri_dedup_key_is_unique`, `::test_unchanged_page_yields_one_blob_but_many_capture_rows`; `test_ocfl.py::test_unchanged_bytes_dedup_to_one_blob_many_versions`; `test_store.py::test_refetch_of_unchanged_bytes_dedups_blobs` |

## OCFL layout (§17.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-EVID-005 / AC1 (OCFL 1.1 root; 1 object/stream, 1 version/capture; sha512 manifest + BLAKE3 fixity; readable without SIG code) | `evidence/ocfl.py` | `test_ocfl.py::test_object_readable_without_sig_code`, `::test_fixity_block_records_blake3`, `::test_storage_root_declares_ocfl_and_layout` |
| SIG-EVID-006 (versioning enabled + governance-mode Object Lock, never compliance; documented retention) | `evidence/storage.py` (`governance_object_lock_configuration`, `S3ObjectStore.ensure_bucket`) | `test_storage.py::test_object_lock_config_is_governance_not_compliance`, `::test_compliance_mode_is_rejected`, `::test_ensure_bucket_enables_versioning_and_governance_lock` |

## Web captures (§17.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-EVID-007 (captures stored as WACZ 1.1.1, not screenshots/PDF alone) | `evidence/capture.py::build_wacz` | `test_capture.py::test_wacz_is_a_valid_1_1_1_package` |
| SIG-EVID-008 / AC4 (JS artifact → WACZ + screenshot + payload + raw HTML, each a capture row, one artifact) | `evidence.capture.capture_set`; `evidence.store.EvidenceStore.store_capture_set` | `test_capture.py::test_js_artifact_full_capture_set`; `test_store.py::test_capture_set_becomes_n_rows_under_one_object` |

## Storage tiers (§17.5)

| Requirement | Where | Test |
|---|---|---|
| SIG-EVID-009 (every capture carries public/restricted/sealed) | `evidence.tiers.StorageTier`; `db/deploy/evidence.sql` (CHECK) | `test_tiers.py::test_audited_tiers` |
| SIG-EVID-010 / AC2 (sealed → metadata-only public representation) | `evidence.tiers.public_representation` | `test_tiers.py::test_sealed_exposes_metadata_only`, `::test_restricted_redacts_the_excerpt_but_keeps_metadata` |
| SIG-EVID-011 / AC5 (redaction = new capture with `parent_capture_id`; method + version recorded; original never edited) | `evidence/redaction.py`; `db/deploy/evidence_store.sql` (`evidence_capture_redaction_versioned`) | `test_redaction.py`; `tests/db/test_evidence_store.py::test_redaction_is_a_new_capture_with_parent_and_version`, `::test_redaction_without_version_is_rejected` |
| SIG-EVID-012 (restricted/sealed byte access logged w/ requester+purpose+timestamp; access log has own retention) | `evidence/access_log.py`; `db/deploy/evidence_store.sql` (`evidence_access_log`) | `test_access_log.py`; `tests/db/test_evidence_store.py::test_access_log_only_records_restricted_and_sealed` |

## Disappearance and link rot (§17.6)

| Requirement | Where | Test |
|---|---|---|
| SIG-EVID-013 / AC6 (disappearance event on artifact; never delete artifact/captures/claims) | `evidence/disappearance.py`; `db/deploy/access_control.sql` (REVOKE DELETE) | `test_disappearance.py::test_disappearance_is_an_event_not_a_delete`; `tests/db/test_evidence_store.py::test_disappearance_is_an_update_not_a_delete`, `::test_ingest_run_grant_forbids_delete_on_evidence` |
| SIG-EVID-014 (disappearance generates a §33.2 research task; distinct UI state) | `evidence.disappearance.disappearance_task` | `test_disappearance.py::test_disappearance_generates_a_research_task` |
| SIG-EVID-015 (link-rot sweep on a volatility-proportional cadence; Wayback for permitted public artifacts) | `evidence.disappearance` (`sweep_cadence_days`, `wayback_save_url`) | `test_disappearance.py::test_sweep_cadence_is_proportional_to_volatility`, `::test_wayback_save_url` |

## Reproducibility (§17.7)

| Requirement | Where | Test |
|---|---|---|
| SIG-EVID-016 (every claim references an `ingest_run` recording connector/commit/ruleset/vocab/digests/params/env) | `evidence/ingest_run.py::IngestRun`; `db/deploy/rights_sources_lineage.sql` (`ingest_run`) | `test_ingest_run.py::test_ingest_run_records_the_reproducibility_fields` |
| SIG-EVID-017 (re-run over pinned digests → byte-identical tuples modulo `claim_id`/`sys_period`) | `evidence.ingest_run.canonical_claim_tuple`; deterministic packaging (`evidence.capture.build_wacz`) | `test_ingest_run.py::test_reproducibility_modulo_claim_id_and_sys_period`; `test_capture.py::test_wacz_packaging_is_deterministic` |
| SIG-EVID-018 (ingestion runs LC_ALL=C / TZ=UTC; no wall-clock in derived values) | `evidence.ingest_run.deterministic_environment` / `assert_deterministic_environment` | `test_ingest_run.py::test_deterministic_environment_is_lc_all_c_tz_utc`, `::test_non_deterministic_environment_is_rejected` |

# P02.3 — Temporal semantics and provenance

Time and provenance become queryable: EDTF Level 1 with a pinned deterministic
envelope (`db/src/db/edtf.py`), the two as-of query axes and the four absence
states (`db/src/db/temporal.py`, `db/src/db/absence.py`), the eight temporal
invariants as pipeline data-quality checks (`db/src/db/invariants.py`), an
additive `temporally_unanchored` flag plus the `claim_as_of`/`resolution_as_of`
SQL functions (`db/deploy/temporal_invariants.sql`), and PROV-O export over the
P02.2 `ingest_run` lineage (`exports/src/exports/provo.py`). ADR-024/025.

## EDTF encoding and the envelope (§9.3, §16.7)

| Requirement | Where | Test |
|---|---|---|
| SIG-TIME-006 / SIG-STORE-021 (EDTF L1; pinned, versioned, deterministic envelope; widening in `ruleset_version`) | `db.edtf.derive_envelope`, `db.edtf.ENVELOPE_RULESET_VERSION`; ADR-024 | `tests/unit/test_edtf.py::test_spec_16_7_table_envelopes`, `::test_envelope_is_deterministic`, `::test_round_trip_canonical`, `::test_unknown_ruleset_is_refused` |
| SIG-STORE-022 (MUST NOT sharpen "early 2025" to `2025-01-01`) | `db.edtf.derive_envelope` | `tests/unit/test_edtf.py::test_early_2025_is_not_sharpened_to_jan_1` |
| SIG-TIME-004 (each bound carries a closed-vocabulary kind) | `db.temporal.ValidBoundKind`, `db.temporal.ObservedAtKind` | `tests/unit/test_temporal_semantics.py::test_ongoing_and_unknown_are_distinguished`, `::test_before_and_after_bounds_render_distinctly` |

## Kinds and ongoing rendering (§9.3, P12)

| Requirement | Where | Test |
|---|---|---|
| SIG-TIME-005 / AC2 (`ongoing` ≠ "true now"; rendered with the observation date; `ongoing` ≠ `unknown`) | `db.temporal.render_valid_bound`, `db.temporal.assert_conformant_rendering` | `tests/unit/test_temporal_semantics.py::test_ongoing_is_rendered_with_the_observation_date`, `::test_currently_phrasing_is_non_conformant`, `::test_ongoing_without_an_observation_date_is_refused` |

## As-of query semantics (§9.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-TIME-007 (two independent as-of axes with explicit defaults; world=today, belief=now) | `db.temporal.AsOf`; `db/deploy/temporal_invariants.sql` (`claim_as_of`, `resolution_as_of`) | `tests/unit/test_temporal_semantics.py::test_defaults_are_explicit_world_today_belief_now`, `::test_where_predicate_filters_both_axes` |
| SIG-TIME-008/009 / AC4 (the fourth belief-pinned form; correction returns the old value at a prior belief) | `claim_as_of` SQL function | `tests/db/test_as_of.py::test_claim_as_of_belief_returns_prior_belief`, `::test_claim_as_of_world_filters_valid_time`; `tests/unit/test_temporal_semantics.py::test_the_four_questions` |
| SIG-TIME-016 (only T1 and T5 are as-of axes; T2 is an ordering scalar) | `db.temporal.AsOf` (world→valid_period, belief→sys_period) | `tests/unit/test_temporal_semantics.py::test_where_predicate_filters_both_axes` |

## Absence states (§9.5)

| Requirement | Where | Test |
|---|---|---|
| SIG-TIME-010 / AC5 (four distinct states; encoding maps to coverage_record + resolution) | `db.absence.AbsenceState`, `coverage_kind_for`, `state_from_coverage_kind` | `tests/unit/test_absence.py::test_all_four_states_render_distinguishably`, `::test_coverage_kinds_match_the_schema_vocabulary`, `::test_unresolved_is_not_a_coverage_record` |
| SIG-TIME-011 (`NO_EVIDENCE_FOUND` names the sources searched) | `db.absence.render_absence` | `tests/unit/test_absence.py::test_no_evidence_found_requires_the_sources_searched` |
| SIG-TIME-012 (`NOT_RESEARCHED` renders distinguishably from `NO_EVIDENCE_FOUND`) | `db.absence.render_absence` | `tests/unit/test_absence.py::test_not_researched_differs_from_no_evidence_found` |

## Temporal invariants (§9.6)

| Requirement | Where | Test |
|---|---|---|
| SIG-TIME-013 / AC1 (TI-1..TI-8 as DB constraints or run-failing DQ checks) | `db.invariants` (check_ti1..8, `check_all`); `db/deploy/temporal_invariants.sql` (`claim_unanchored_reasoned` for TI-8); P02.1 `claim_observed_not_future` (TI-5), `resolution_no_overlap` (TI-6); ADR-025 | `tests/property/test_temporal_invariants.py` (TI-1..TI-8); `tests/db/test_as_of.py::test_temporally_unanchored_requires_a_reason` |
| SIG-TIME-014 (L1 contradiction is legal; only L3 must be consistent — TI-6) | `db.invariants.check_ti6` (mutually-exclusive predicates only) | `tests/property/test_temporal_invariants.py::test_ti6_detects_overlap_of_exclusive_predicates` |

## PROV-O lineage export (§21.6)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-015 (every claim traceable to its `ingest_run`) | `exports.provo` (claim→run/extraction wiring); P02.1 `claim.ingest_run_id` | `tests/exports/test_provo.py::test_wiring_edges_use_prov_vocabulary` |
| SIG-INGEST-016 / AC6 (lineage maps onto PROV-O; captures/claims=Entity, runs/extractions=Activity, connectors/curators/sources=Agent, `revises_claim`=`prov:wasRevisionOf`; export validates) | `exports.provo.build_prov_graph`, `validate_prov_graph`, `export_lineage` | `tests/exports/test_provo.py::test_captures_and_claims_are_entities`, `::test_runs_and_extractions_are_activities`, `::test_connectors_curators_sources_are_agents`, `::test_revises_claim_maps_to_was_revision_of`, `::test_export_validates`, `::test_validation_rejects_a_disjoint_class_conflict` |

# P03.1 — Jurisdiction and Organization registries

Stable identity before anything is counted (Phase 3, first half): the identity
substrate in the `resolution/` package over the physical registry tables already
shipped in P02 (App C.4 `jurisdiction` / `organization` / `organization_relation`
/ `entity_identifier`). The seven-value `OrganizationRelationType` and the
`GeometryPrecision` vocabularies are added to the LinkML source of truth (§20.1)
and regenerated. `normalize_org_name()`, the crosswalk, the deterministic cascade,
and public `sig:` minting are P03.2 and are deliberately absent here.

## Jurisdiction registry and temporal geometry (§11.1, SIG-ONTO-010/011)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-010 (first-class jurisdiction; overlapping self-referential hierarchy; pluggable code systems; MultiPolygon + boundary_source) | `resolution.jurisdiction.JurisdictionRecord` (`parents` tuple = overlap), `resolution.jurisdiction.build_jurisdiction`; `db/deploy/domain_entities.sql` (`jurisdiction`) | `tests/resolution/test_jurisdiction.py::test_overlapping_parents_are_permitted`, `::test_geoid_identifiers_are_validated_against_the_level` |
| SIG-ONTO-011 (jurisdiction geometry is temporally versioned; as-of differs from today) | `resolution.jurisdiction.BoundaryVersion`, `JurisdictionRecord.boundary_as_of`; `db/deploy/domain_entities.sql` (`jurisdiction.boundary_valid`) | `tests/resolution/test_jurisdiction.py::test_boundary_as_of_returns_the_version_in_force`, `tests/db/test_identity_registry.py::test_jurisdiction_boundary_is_temporally_versioned` |
| SIG-IDENT-005 (GEOIDs fixed-width strings + explicit level; 7-char is ambiguous) | `resolution.geoid.validate_geoid`, `GEOID_WIDTHS`, `geoid_levels_for_width` | `tests/resolution/test_geoid.py::test_valid_fixed_width_geoids_pass`, `::test_seven_char_geoid_is_ambiguous_without_a_level`, `::test_wrong_width_for_level_is_rejected`, `::test_missing_level_is_rejected`; `tests/db/test_identity_registry.py::test_jurisdiction_requires_an_explicit_level` |

## Organization registry (§11.2, SIG-ONTO-012/013, SIG-IDENT-006/010)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-012 (single entity for all actors; vendor is a role, not a subtype) | `resolution.identity.Organization` (one class; `organization_class` is a value, vendor never a subtype) | `tests/resolution/test_identity.py::test_two_axes_are_independent`, `tests/resolution/test_vocab_conformance.py::test_two_axes_are_grounded_in_the_ontology_vocabularies` |
| SIG-IDENT-006 (identifiers are SETS of (scheme,value), never single columns) | `resolution.identity.Identifier`, `identifier_set`; `db/deploy/domain_entities.sql` (`entity_identifier` PK) | `tests/resolution/test_identity.py::test_identifiers_are_a_deduplicating_set`, `::test_identifier_requires_scheme_and_value`; `tests/db/test_identity_registry.py::test_identifiers_are_a_set_per_entity` |
| SIG-IDENT-010 (two independent axes: organization_class × operating_relationship) | `resolution.identity.TwoAxisClassification`, `classify` (class∈OrganizationType, relationship∈Role) | `tests/resolution/test_identity.py::test_two_axes_are_independent`, `::test_two_axes_require_both`; `tests/resolution/test_vocab_conformance.py::test_two_axes_are_grounded_in_the_ontology_vocabularies` |
| SIG-IDENT-018 (status vocab active\|inactive\|withdrawn\|suppressed; withdrawn≠suppressed) | `resolution.identity.OrgStatus`; `db/deploy/domain_entities.sql` (`organization.status`) | `tests/resolution/test_identity.py::test_status_vocabulary`; `tests/db/test_identity_registry.py::test_status_vocabulary_values_persist` |

## Municipality / department split and colon-name parsing (SIG-IDENT-009/011)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-009 (municipality and its police department are distinct orgs joined by parent_of) | `resolution.temporal_identity.municipality_department_pair` | `tests/resolution/test_temporal_identity.py::test_municipality_and_department_are_distinct_joined_by_parent_of`, `::test_municipality_department_pair_requires_distinct_entities`; `tests/db/test_identity_registry.py::test_municipality_and_department_are_distinct_joined_by_parent_of` |
| SIG-IDENT-011 (colon agency name → parent + local unit; parent materialized) | `resolution.identity.parse_agency_name`, `AgencyName` | `tests/resolution/test_identity.py::test_colon_name_splits_into_parent_and_unit`, `::test_name_without_colon_has_no_parent`, `::test_dangling_colon_is_not_a_parent_split` |

## Surrogate identity and publication review (§14.4, SIG-IDENT-012, SIG-ONTO-013)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-012 (surrogate with immutable identity_basis of the six named fields) | `resolution.identity.IdentityBasis` (frozen), `mint_surrogate`; `db/deploy/domain_entities.sql` (`organization.identity_basis` jsonb) | `tests/resolution/test_identity.py::test_identity_basis_is_immutable_with_six_fields`, `::test_surrogate_minting_is_deterministic_and_routes_private_bodies_to_review`; `tests/db/test_identity_registry.py::test_surrogate_identity_basis_round_trips` |
| SIG-ONTO-013 (surrogate-only small private body routed through §43.4 publication review) | `resolution.identity.requires_publication_review`, `mint_surrogate`; `organization.publication_review_required` | `tests/resolution/test_identity.py::test_publication_review_routing_rule`, `::test_organization_to_row_maps_class_to_type_and_carries_basis` |

## Geometry precision guard (SIG-IDENT-004)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-004 (agency centroid stored as `organization_centroid_or_unknown`; barred from point-in-polygon and address use) | `resolution.geometry_precision.GeometryPrecision`, `assert_point_in_polygon_usable`, `assert_usable_as_address` | `tests/resolution/test_geometry_precision.py::test_agency_centroid_is_rejected_for_point_in_polygon`, `::test_agency_centroid_is_rejected_as_an_address`, `::test_real_precisions_are_usable` |

## Temporal identity: the reified relation and rename-is-not-succession (§14.5, SIG-IDENT-016/017/019)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-016 (reified, bitemporal OrganizationRelation; seven-value vocabulary; valid + txn time) | `resolution.temporal_identity.OrganizationRelationType`, `OrganizationRelation`; ontology `OrganizationRelationType` enum; `db/deploy/domain_entities.sql` (`organization_relation`) | `tests/resolution/test_temporal_identity.py::test_relation_vocabulary_is_exactly_seven_values`, `::test_relation_carries_valid_time_and_serialises`, `::test_relation_rejects_a_self_loop_and_coerces_a_string_type`; `tests/resolution/test_vocab_conformance.py::test_organization_relation_type_matches_the_ontology`; `tests/db/test_identity_registry.py::test_all_seven_relation_types_are_storable`, `::test_municipality_and_department_are_distinct_joined_by_parent_of` |
| SIG-IDENT-017 (a pure rename → new version + dated alias; NO succession relation; NO new identifier) | `resolution.temporal_identity.rename_organization`, `RenameResult` | `tests/resolution/test_temporal_identity.py::test_rename_produces_no_succession_and_no_new_identifier`, `::test_identifiers_survive_a_rename_unchanged` |
| SIG-IDENT-019 (five succession fixtures pass) | `resolution.temporal_identity.absorb`/`merge`/`split`/`rename_organization`/`acquire` + `transfer_product_vendor` | `tests/resolution/test_temporal_identity.py::test_absorb_fixture`, `::test_merge_fixture`, `::test_split_fixture`, `::test_rename_produces_no_succession_and_no_new_identifier`, `::test_acquire_fixture_transfers_product_ownership` |

## Registry-ingest guard (SIG-IDENT-008)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-008 (zero-record ingest fails the run; absent distinguished from not-observed) | `resolution.registry_ingest.assert_registry_records_present`, `classify_zero`, `ZeroRecordIngest` (reuses `db.absence`) | `tests/resolution/test_registry_ingest.py::test_zero_record_ingest_fails_the_run`, `::test_absent_is_distinguished_from_not_observed`, `::test_not_observed_zero_must_name_the_sources_searched`, `::test_nonzero_ingest_returns_the_count` |

## Vocabulary as code (§20.1, ADR-007)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-068 (namespaced vocabularies; class axis in OrganizationType, relationship axis in Role) + single-source-of-truth for the two new enums | `ontology/src/ontology/schema/common.yaml` (`OrganizationRelationType`, `GeometryPrecision`); regenerated `ontology/generated/**` | `tests/resolution/test_vocab_conformance.py::test_organization_relation_type_matches_the_ontology`, `::test_geometry_precision_matches_the_ontology`; `tests/ontology/test_generation_gate.py` (`make verify-gen`) |

# P03.2 — Deterministic entity resolution

## Identifier crosswalk and per-class canonical schemes (§14.2, SIG-IDENT-001/002/003/007)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-001 (every class has a designated canonical identifier scheme; else a surrogate) | `resolution.crosswalk.canonical_scheme_for`, `SchemeResolution`; `data/canonical_schemes.toml` | `tests/resolution/test_crosswalk.py::test_us_le_class_is_ori`, `::test_representative_classes_map_to_their_schemes`, `::test_class_with_no_external_scheme_takes_a_surrogate`, `::test_exact_class_match_beats_prefix` |
| SIG-IDENT-002 (ORI validated by `^[A-Z0-9]{9}$`, never positional; UCR↔USPS table incl NB→NE, GM→GU) | `resolution.ori.validate_ori`, `ORI_PATTERN`, `ucr_to_usps`, `usps_to_ucr`, `ucr_usps_divergences`; `data/ucr_usps.toml` | `tests/resolution/test_ori.py::test_valid_ori_is_nine_alnum`, `::test_validation_does_not_consult_the_state_prefix`, `::test_ucr_usps_divergences_include_the_mandated_pairs`, `::test_ucr_to_usps_translates_divergent_and_passes_through_identical` |
| SIG-IDENT-003 (ORI with alphabetic 9th char flagged civil/applicant; not auto-linked without a 2nd source) | `resolution.ori.is_civil_ori`; `resolution.cascade._tier0` (civil ORI refused as sole basis) | `tests/resolution/test_ori.py::test_alphabetic_ninth_char_is_flagged_civil`, `::test_numeric_ninth_char_is_not_civil`; `tests/resolution/test_cascade.py::test_civil_ori_alone_does_not_auto_link_at_tier0`, `::test_civil_ori_with_a_second_shared_id_still_auto_links` |
| SIG-IDENT-007 (Wikidata recorded but not depended on for US LE; strong for vendors) | `resolution.crosswalk.wikidata_reliable_for` | `tests/resolution/test_crosswalk.py::test_wikidata_is_not_reliable_for_us_le_but_is_for_vendors` |

## Name normalisation (§14.6, SIG-IDENT-022)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-022 (`normalize_org_name()` pure/deterministic/versioned + committed vectors in CI; sheriff collapse; acronyms by exact lookup only, never fuzzy) | `resolution.normalize.normalize_org_name`, `resolve_acronym`, `NORMALIZE_RULESET_VERSION`; `data/normalize_rules.toml`, `data/acronym_alias.toml`, `data/normalize_vectors.toml` | `tests/resolution/test_normalize.py::test_every_committed_vector_holds`, `::test_is_deterministic_and_idempotent`, `::test_sheriff_office_and_department_collapse_to_one_suffix`, `::test_similar_initials_are_not_fuzzy_merged`, `::test_acronym_lookup_is_whole_string_not_substring` |

## Deterministic cascade tiers 0–3 and address keys (§14.6/§14.4, SIG-IDENT-020/025/013/015)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-020 (six-tier cascade, deterministic first; tiers 0–3 auto-write) | `resolution.cascade.resolve`, `Candidate`, `MatchResult`, `CascadeContext`; `data/cascade_rules.toml` | `tests/resolution/test_cascade.py::test_tier0_exact_shared_ori_auto_writes`, `::test_tier1_established_crosswalk_auto_writes`, `::test_tier2_name_state_class_auto_writes`, `::test_tier3a_shared_gov_domain_auto_writes`, `::test_tier3b_k1_plus_name_auto_writes`, `::test_tier0_precedes_lower_tiers` |
| SIG-IDENT-025 (every match records `match_tier` + `match_evidence`) | `resolution.cascade.MatchResult` (`match_tier`, `tier_label`, `match_evidence`) | `tests/resolution/test_cascade.py` (`_assert_auto_write` asserts both on every tier) |
| SIG-IDENT-013 (address keys K1–K4; K1/K2 may match, K3/K4 blocking-only, never identity evidence) | `resolution.address.AddressKeys`, `IDENTITY_KEYS`, `BLOCKING_ONLY_KEYS`, `assert_identity_usable`, `build_address_keys`; `resolution.cascade._tier3b` (K1 only) | `tests/resolution/test_address.py::test_blocking_only_keys_are_refused_as_identity_evidence`, `::test_build_partitions_keys_into_identity_and_blocking`; `tests/resolution/test_cascade.py::test_tier3b_uses_only_k1_never_a_blocking_key` |
| SIG-IDENT-015 (vendor-portal slugs parsed by a versioned grammar + denylist; hypothesis, never identity) | `resolution.slug.parse_slug`, `SlugHypothesis`, `is_denied_slug`, `SLUG_GRAMMAR_VERSION`; `data/slug_grammar.toml` | `tests/resolution/test_slug.py::test_slug_parses_by_grammar_into_a_hypothesis`, `::test_denylisted_test_tenants_never_parse_to_a_body`, `::test_contains_denylist_marker_is_denied` |

## Public identifiers and stability (§14.8, SIG-IDENT-031/032)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-031 (mint `sig:<type>:<uuidv7>`, dereferenceable at `/id/<type>/<uuid>` with content negotiation) | `resolution.public_id.uuid7`, `mint`, `parse`, `dereference_url`, `negotiate` | `tests/resolution/test_public_id.py::test_uuid7_has_version_7_and_is_time_ordered`, `::test_mint_produces_sig_type_uuidv7_form`, `::test_dereference_url_uses_the_id_path`, `::test_content_negotiation_covers_html_jsonld_rdf` |
| SIG-IDENT-032 (stable across split/merge; `redirects_to`/`split_into` + tombstones; never silently reassigned) | `resolution.public_id.PublicIdRegistry` (`split`, `merge`, `resolve`), `Tombstone`, `MergeSplitEvent`, `Resolution` | `tests/resolution/test_public_id.py::test_public_ids_survive_a_simulated_cluster_split`, `::test_split_never_reassigns_the_source_id`, `::test_a_tombstoned_id_cannot_be_re_registered`, `::test_merge_preserves_the_survivor_and_redirects_the_rest`, `::test_resolve_follows_a_chain_of_merges_to_the_final_survivor` |

## Crosswalk exports behind the licence gate (§14.8, SIG-IDENT-033/034)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-033 (SIG↔external identifier crosswalk export) | `resolution.crosswalk.build_sig_external_crosswalk`, `CrosswalkRow`, `export_crosswalk` (→ `policy.licensing.assert_export_permitted`) | `tests/resolution/test_crosswalk.py::test_sig_external_crosswalk_is_deterministic_and_sorted`, `::test_crosswalk_publishes_when_all_rights_permit`, `::test_crosswalk_fails_closed_on_a_non_redistributable_source` |
| SIG-IDENT-034 (public `ORI9 → Census GEOID` crosswalk, subject to the licence gate) | `resolution.crosswalk.build_ori_geoid_crosswalk` (validates both sides), `export_crosswalk` | `tests/resolution/test_crosswalk.py::test_ori_geoid_crosswalk_validates_both_sides`, `::test_ori_geoid_crosswalk_rejects_a_malformed_ori`, `::test_ori_geoid_crosswalk_rejects_a_malformed_geoid` |

# P04.1 — the connector framework

The reusable eight-stage substrate (§21) every source adapter plugs into. No
source-specific connector is written here (OSM/Atlas are P04.2/P04.3); the
framework is exercised end-to-end by a toy connector in `tests/connectors/`.

## The eight-stage interface (§21.1, SIG-INGEST-001/002/003)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-001 (eight stages, separately addressable/retryable, each content-addressed) | `connectors.stages` (`Stage`, `STAGE_ORDER`, `StageArtifact`, `ArtifactStore`, `content_digest`, `Connector`); `connectors.pipeline.run_stage` | `tests/connectors/test_stages.py::test_the_eight_stages_are_named_and_ordered`, `::test_artifact_store_addresses_and_retries_stages`; `tests/connectors/test_pipeline.py::test_stages_are_separately_runnable_and_idempotent` |
| SIG-INGEST-002 (fetch() the only egress; post-capture stages pure; replay network-isolated) | `connectors.stages.may_egress`/`POST_CAPTURE_STAGES`; `connectors.isolation.network_isolated`; `connectors.pipeline.run_post_capture` | `tests/connectors/test_stages.py::test_fetch_is_the_only_egress_stage`; `tests/connectors/test_isolation.py`; `tests/connectors/test_pipeline.py::test_egress_after_capture_fails_the_run` |
| SIG-INGEST-003 (stage idempotency modulo generated ids/timestamps) | `connectors.stages.content_digest`; `evidence.ingest_run.canonical_claim_tuple` | `tests/connectors/test_stages.py::test_content_addressing_is_deterministic_and_order_independent`; `tests/connectors/test_pipeline.py::test_stages_are_separately_runnable_and_idempotent` |

## Source disappearance as data (§21.4, SIG-INGEST-009/010)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-009 (404/removal/challenge is a first-class event row, not an exception) | `connectors.disappearance` (`failing_status_for_http`, `failing_status_for_error`, `note_disappearance`); `connectors.pipeline._fetch_or_disappear` (reuses `evidence.disappearance`) | `tests/connectors/test_connector_disappearance.py`; `tests/connectors/test_pipeline.py::test_404_records_a_disappearance_not_an_exception`, `::test_persistent_challenge_records_a_disappearance` |
| SIG-INGEST-010 (disappearance generates a research task) | `connectors.disappearance.note_disappearance` (→ `evidence.disappearance.disappearance_task`) | `tests/connectors/test_connector_disappearance.py::test_note_disappearance_produces_event_and_task` |

## Politeness and access (§21.5, SIG-INGEST-011/012/013)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-011 (shared rate-limiter + robots layer; per-host budgets; contact UA; connectors hold no HTTP client) | `connectors.net` (`PoliteFetcher`, `RateLimiter`, `user_agent`); connectors fetch through `RunContext.fetcher` only | `tests/connectors/test_net.py::test_user_agent_carries_a_contact_url`, `::test_rate_limiter_enforces_a_per_host_minimum_interval`, `::test_robots_crawl_delay_pins_the_host_budget` |
| SIG-INGEST-012 (robots.txt unretrievable ⇒ refuse to run) | `connectors.net.PoliteFetcher._ensure_robots` (→ `policy.crawler.robots_permits`) | `tests/connectors/test_net.py::test_unretrievable_robots_refuses_to_run` |
| SIG-INGEST-013 (no challenge-defeating crawler) | `connectors.net` (`ChallengeEncountered`, construction-time `policy.crawler.assert_no_circumvention`) | `tests/connectors/test_net.py::test_bot_challenge_is_surfaced_never_defeated`, `::test_circumvention_technique_is_rejected_at_construction` |

## The connector-loader gate (§21.5/§22.4/§42.4, SIG-INGEST-014/028, SIG-LIC-010)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-014 (loader checks ingestion_permitted + custody_posture + compact_status before any fetch; refuses when absent/unresolved) | `connectors.loader.assert_loadable`, `compact_permits_ingestion`, `custody_permits_fetch`; `connectors.pipeline.run` (gate up front) | `tests/connectors/test_loader_gate.py`; `tests/connectors/test_pipeline.py::test_gate_refuses_before_any_fetch` |
| SIG-INGEST-028 (pipeline refuses a connector whose compact denies ingestion) | `connectors.loader.assert_ingestion_permitted` / `assert_loadable` | `tests/connectors/test_loader_gate.py::test_gate_refuses_when_ingestion_not_permitted`, `::test_gate_refuses_when_compact_denies`; `tests/unit/test_ingestion_gate.py` |
| SIG-LIC-010 (export licence computed per compartment; build fails on incompatibility) | `connectors.loader.assert_export_compatible` (→ `policy.licensing.compute_export_license`); `connectors.cli export-check` | `tests/connectors/test_loader_gate.py::test_export_of_compatible_compartment_computes_a_licence`, `::test_export_mixing_incompatible_compartments_fails_the_build`; `tests/connectors/test_cli.py::test_export_check_passes_on_the_seeded_registry` |

## Backfill, replay, shadow mode, lineage (§21.6/§21.7, SIG-INGEST-015/016/017/018/019/021)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-015 (every claim traceable to its ingest_run) | `connectors.lineage.build_lineage`; `evidence.ingest_run.IngestRun` | `tests/connectors/test_lineage.py::test_build_lineage_assembles_the_run` |
| SIG-INGEST-016 (lineage maps onto PROV-O) | `connectors.lineage.build_lineage` (→ `exports.provo.build_prov_graph`/`export_lineage`) | `tests/connectors/test_lineage.py::test_lineage_maps_onto_prov_o` |
| SIG-INGEST-017 (re-run extraction over archived captures → new claim set, old preserved) | `connectors.replay.replay`, `replay_fingerprint` | `tests/connectors/test_replay.py::test_replay_over_pinned_captures_is_byte_identical` |
| SIG-INGEST-018 (replay against archived snapshots only, network-isolated) | `connectors.replay.replay` (via `connectors.pipeline.run_post_capture` under `network_isolated`) | `tests/connectors/test_replay.py::test_replay_is_network_isolated`, `::test_replay_never_asserts` |
| SIG-INGEST-019 (shadow mode diffs new vs current, reports delta before asserting) | `connectors.replay.shadow_replay`, `diff_claim_sets`, `ShadowDiff` | `tests/connectors/test_replay.py::test_shadow_replay_reports_delta_without_asserting`, `::test_diff_claim_sets_ignores_generated_columns` |
| SIG-INGEST-021 (every stage runnable as a plain CLI; orchestrator import confined to orchestration/) | `connectors.cli` (`stages`/`gate`/`export-check`), `connectors.stages.register`; `connectors.pipeline` imports no orchestrator | `tests/connectors/test_cli.py`; `tests/unit/test_cli_convention.py`; `tests/unit/test_import_boundary.py` |

# P04.2 — the `osm` connector

The first real source adapter on the P04.1 framework (§23.2): surveillance
physical assets from OpenStreetMap, landing in the physically separate ODbL asset
layer (§42.3). Decision record: ADR-027.

## Tag vocabulary and normalization (§23.2, SIG-INGEST-045)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-045 (consume the four surveillance keys + wider §23.2 vocab; split `;` multi-values as unordered sets; cross-key normalize; a surveillance-bearing key/value outside the allowlist → unmapped value + research task) | `connectors.osm` (`normalize`, `split_multivalue`, `map_surveillance_type`, `map_mobility`, `is_surveillance_bearing_key`, `unmapped_tag_task`); versioned `data/osm_tag_vocab.toml` | `tests/connectors/test_osm.py::test_all_four_surveillance_keys_are_normalized_and_mobility_inferred`, `::test_semicolon_multivalue_is_split_as_an_unordered_set`, `::test_unallowlisted_surveillance_key_becomes_unmapped_value_plus_task`, `::test_unmapped_surveillance_type_value_records_a_task`, `::test_non_camera_surveillance_types_are_in_scope` |
| SIG-INGEST-045 (vocabulary is versioned data, not code — §20 migrations) | `connectors.osm.vocab`/`vocab_version`; `data/osm_tag_vocab.toml` (`version`) | `tests/connectors/test_osm.py::test_vocabulary_is_versioned` |
| Handles nodes, ways **and** relations (§23.2, SIG-GEO-003) | `connectors.osm.OSMConnector.extract`; `geometry_descriptor` | `tests/connectors/test_osm.py::test_handles_nodes_ways_relations_and_preserves_id_and_version` |

## Keying and edit-detection (SIG-INGEST-045b / 045f)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-045b/045f (key on `(osm_type, osm_id, version)`; id-space scoped subject; preserve id AND version so a later OSM edit is detectable — REQ-R1-01) | `connectors.osm` (`ElementRef`, `ElementVersionRef`, `element_version_ref`); `physical_asset_rows` (version preserved) | `tests/connectors/test_osm.py::test_subject_id_is_id_space_scoped`, `::test_handles_nodes_ways_relations_and_preserves_id_and_version` |

## `first_observed` from element history (SIG-INGEST-045a / 045c)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-045a (first_observed = version where surveillance tags first appeared, walked from history; never the creation timestamp) | `connectors.osm.first_observed_from_history`, `history_versions`, `OSMConnector.resolve_first_observed`/`_extract_history` | `tests/connectors/test_osm.py::test_first_observed_is_walked_from_history_not_creation`, `::test_first_observed_flows_through_the_pipeline`, `::test_first_observed_none_when_never_surveillance`, `::test_snapshot_asset_first_observed_is_never_the_creation_timestamp` |

## Deletion via snapshot diffing (SIG-INGEST-045g)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-045g (deletion detected by snapshot diff; *deleted from OSM* is a mapping event, kept distinct from *removed from street* — a world event) | `connectors.osm` (`snapshot_diff`, `SnapshotDiff.deletion_events`, `DELETED_FROM_OSM_PREDICATE` vs `REMOVED_FROM_STREET_PREDICATE`) | `tests/connectors/test_osm.py::test_deletion_is_detected_by_snapshot_diff_as_a_mapping_event`, `::test_snapshot_diff_does_not_treat_a_persisting_element_as_gone` |

## Mapper-identity discard + Overpass etiquette (SIG-INGEST-045e / 045d/h/i/j)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-045e (discard OSM `user`/`uid` at ingest, never store/expose; retain `changeset`) | `connectors.osm.strip_mapper_identity`; `OSMConnector.extract` (mapper keys dropped) | `tests/connectors/test_osm.py::test_strip_mapper_identity_drops_user_and_uid_keeps_changeset`, `::test_no_output_row_ever_carries_user_or_uid` |
| SIG-INGEST-045d (descriptive contact-carrying UA; no spaces in tag-value filters) | shared `connectors.net.PoliteFetcher` UA; `connectors.osm.build_overpass_query` (client-side filtering) | `tests/connectors/test_osm.py::test_fetch_carries_a_descriptive_user_agent`, `::test_overpass_query_respects_etiquette` |
| SIG-INGEST-045h (Overpass quotas; 429 → back off, 504 → shrink) | `connectors.osm.overpass_status_action`, `build_overpass_query` (`[timeout]/[maxsize]`), quota constants | `tests/connectors/test_osm.py::test_overpass_status_actions`, `::test_overpass_query_respects_etiquette` |
| SIG-INGEST-045i (PBF for bulk, tiled Overpass for increments; no worldwide bbox-stitching) | `connectors.osm.acquisition_mode`, `build_overpass_query` (`BulkStitchingForbidden`) | `tests/connectors/test_osm.py::test_unbounded_query_is_refused_as_bulk_stitching` |
| SIG-INGEST-045j (never another project's self-hosted Overpass without permission) | `connectors.osm.assert_own_or_public_instance` | `tests/connectors/test_osm.py::test_only_public_or_permitted_overpass_instances_are_used` |

## ODbL landing + fixtures/canary (SIG-ONTO-007, SIG-LIC-006, SIG-PARSE-007/008)

| Requirement | Where | Test |
|---|---|---|
| SIG-LIC-006 / SIG-ONTO-007 (output lands in the separate ODbL asset layer; an export mixing it with the CC-BY graph fails) | `connectors.osm` (`_stamp` → `ODBL_LICENSE`/`ODBL_COMPARTMENT`, `physical_asset_rows`); export gate `policy.licensing.compute_export_license` / `connectors.loader.assert_export_compatible` | `tests/connectors/test_osm.py::test_every_output_row_is_stamped_into_the_odbl_compartment`, `::test_export_mixing_osm_with_the_cc_by_graph_fails`, `::test_osm_sources_share_one_compatible_compartment` |
| SIG-PARSE-007 (committed fixtures) | `tests/connectors/fixtures/osm/*.json` (Overpass snapshot, element history, deletion snapshot) | driven throughout `tests/connectors/test_osm.py` |
| SIG-PARSE-008 (a canary alerts on structural drift) | `connectors.osm.canary_findings` | `tests/connectors/test_osm.py::test_canary_passes_on_the_committed_fixture`, `::test_canary_flags_structural_drift` |
| SIG-INGEST-021 (connector self-registers on the plug-in seam; visible in the CLI) | `connectors.osm.OSMConnector` (`@register`); imported by `connectors.__init__` | `tests/connectors/test_osm.py::test_osm_connector_is_registered`; `tests/connectors/test_cli.py::test_list_connectors_includes_the_osm_connector` |

# P04.3 — the `atlas` connector

The second real source adapter on the P04.1 framework (§23.3), of deliberately
different shape from `osm`: agency-level **adoption** from the EFF Atlas of
Surveillance, writing a single predicate — `deployment_exists` — at family-level
technology granularity into the CC-BY-4.0 SIG graph compartment. All
source-specific logic is pure and fixture-driven; no live fetch runs in CI. See
ADR-028.

## `deployment_exists` at family granularity + the predicate allowlist (§23.3, SIG-INGEST-033)

| Requirement | Where | Test |
|---|---|---|
| §23.3 (writes `deployment_exists` at **family-level** technology granularity; Atlas category → SIG family, seeded from the `eff_atlas` crosswalk, carrying the SKOS relation + `lossy` provenance — SIG-STORE-039/040, SIG-ONTO-058) | `connectors.atlas` (`category_mapping`, `AtlasConnector._deployment_row`); versioned `data/atlas_vocab.toml` (`[categories]`) | `tests/connectors/test_atlas.py::test_only_deployment_exists_is_written_at_family_granularity`, `::test_category_maps_to_a_sig_family` |
| SIG-INGEST-033 (predicate allowlist enforced as a schema gate; MUST NOT write device counts, coordinates, configuration, current status) | `connectors.atlas` (`predicate_allowlist`, `assert_predicate_allowed`, `PredicateNotAllowed`, `forbidden_predicate_genres`); `data/atlas_vocab.toml` (`predicate_allowlist`, `forbidden_predicate_genres`) | `tests/connectors/test_atlas.py::test_predicate_allowlist_refuses_counts_coordinates_config_status`, `::test_no_claim_row_writes_any_other_predicate` |
| §23.3 vocabulary is versioned data, not code (§20 migrations) | `connectors.atlas.vocab`/`vocab_version`/`atlas_version`; `data/atlas_vocab.toml` | `tests/connectors/test_atlas.py::test_vocabulary_is_versioned` |
| §23.3 unmapped category → research task, never a guessed family | `connectors.atlas` (`AtlasConnector._unmapped_row`, `unmapped_category_task`) | `tests/connectors/test_atlas.py::test_unmapped_category_files_a_research_task_and_writes_no_deployment`, `::test_unmapped_category_task_shape` |

## Agency-id keying + surrogate routing (SIG-INGEST-034)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-034 (key on the Atlas agency identifier; ORI-shaped → canonical `us.fbi.ori`, non-ORI-shaped → `atlas.agency_name` surrogate path feeding P03.2's crosswalk; never resolve entities itself) | `connectors.atlas` (`agency_identity`, `AgencyIdentity`, `ORI_SCHEME`/`ATLAS_AGENCY_SCHEME`); `link()` inherited identity default; ORI shape via `resolution.ori.is_valid_ori` | `tests/connectors/test_atlas.py::test_ori_shaped_agency_routes_to_the_canonical_path`, `::test_non_ori_shaped_agency_routes_to_the_surrogate_path`, `::test_agency_routing_flows_through_the_pipeline`, `::test_connector_does_not_resolve_entities_itself` |

## Attribution + vocabulary version + supersession (§23.3, AC1/AC5)

| Requirement | Where | Test |
|---|---|---|
| §23.3 (preserve the Atlas's own source attribution **and** the recorded Atlas vocabulary version on every row) | `connectors.atlas._stamp` (`source_attribution`, `atlas_version`); `AtlasConnector.extract` (`attribution_links`) | `tests/connectors/test_atlas.py::test_rows_preserve_atlas_source_attribution_and_vocabulary_version` |
| §23.3 (later evidence supersedes/temporally qualifies via the resolver, never by overwrite — append-only, P1–P3) | `connectors.atlas` (rows carry no `is_current`/authoritative flag; `raw_value` preserved); resolver-side supersession is P08.x | `tests/connectors/test_atlas.py::test_rows_are_append_only_with_no_current_value_flag` |
| CC-BY-4.0 landing in the SIG graph compartment (§42.2, SIG-LIC-010) | `connectors.atlas._stamp` (`CC_BY_LICENSE`/`SIG_GRAPH_COMPARTMENT`); `policy/data/licenses.toml` (`compartments.sig_graph`) | `tests/connectors/test_atlas.py::test_rows_land_in_the_cc_by_sig_graph_compartment` |

## Evidence-genre preservation (§23.3, OL-2D-AT-02)

| Requirement | Where | Test |
|---|---|---|
| §23.3 (nine methodology components; carry the producing component where the upstream records it, else record the granularity loss rather than guess a tier) | `connectors.atlas` (`evidence_genres`, `normalize_evidence_genre`, `AtlasConnector._resolve_genre`, `_genre_column`); `data/atlas_vocab.toml` (`[evidence_genres]`, `evidence_genre_columns`) | `tests/connectors/test_atlas.py::test_genre_is_a_granularity_loss_when_the_feed_records_no_component`, `::test_genre_is_carried_when_the_feed_records_the_component`, `::test_the_nine_methodology_genres_are_named` |

## Category retirement, not a world change (SIG-ONTO-059)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-059 (a retired Atlas category is recorded as a **category retirement** — a vocabulary event keyed on the Atlas version — never a deployment and never the world event of a deployment ending) | `connectors.atlas` (`category_retirement_record`, `is_retired_category`, `retired_categories`, `CATEGORY_RETIRED_PREDICATE` vs `DEPLOYMENT_ENDED_PREDICATE`); `data/atlas_vocab.toml` (`[retired]`) | `tests/connectors/test_atlas.py::test_retired_category_is_recorded_as_a_category_retirement`, `::test_retired_category_helpers` |

## Fixtures, canary, registration, reproducibility (SIG-PARSE-007/008, SIG-INGEST-021/003)

| Requirement | Where | Test |
|---|---|---|
| SIG-PARSE-007 (committed fixtures) | `tests/connectors/fixtures/atlas/*.csv` (adoption feed; feed with a methodology component) | driven throughout `tests/connectors/test_atlas.py` |
| SIG-PARSE-008 (a canary alerts on structural drift) | `connectors.atlas.canary_findings`, `parse_csv` | `tests/connectors/test_atlas.py::test_canary_passes_on_the_committed_fixture`, `::test_canary_flags_structural_drift` |
| SIG-INGEST-021 (connector self-registers on the plug-in seam; visible in the CLI) | `connectors.atlas.AtlasConnector` (`@register`); imported by `connectors.__init__` | `tests/connectors/test_atlas.py::test_atlas_connector_is_registered`; `tests/connectors/test_cli.py::test_list_connectors_includes_the_atlas_connector` |
| SIG-INGEST-003 (post-capture stages are pure; replay/shadow reproducibility) | `connectors.atlas` (`normalize` carries no wall-clock; `category_retirement_record` keyed on version, not time) | `tests/connectors/test_atlas.py::test_claim_set_is_reproducible_across_runs` |

# P05.1 — Probabilistic entity resolution (tiers 4–5, the §14.7 quality gates)

P05.1 adds the probabilistic top of the cascade as pure, tested library code plus
versioned data (mirroring the P03.2 deterministic cascade; connectors/ER are not
DB-wired yet — ADR-029). Tiers 4–5 create `PROPOSED` proposals for review and never
auto-write; the review-queue persistence and curation UI are P05.2.

## Splink matcher + tiers 4–6 (SIG-IDENT-020/021/025)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-020 (tiers 4 probabilistic + 5 weak-signal create `PROPOSED` claims → review, never auto-write; tier 6 persists no per-pair record) | `resolution.probabilistic` (`ProbabilisticMatcher._tier_for`, `ProbabilisticMatch.disposition="review"`, `PROPOSED`, `proposed`); `data/splink_model.toml` (`[thresholds]` `tier4_review`/`tier5_weak`) | `tests/resolution/test_probabilistic.py::test_every_probabilistic_match_is_proposed_never_auto_write`, `::test_tier6_below_threshold_persists_no_record`, `::test_tier_boundaries_are_data_driven`; `tests/resolution/test_er_run.py::test_composition_auto_writes_deterministic_and_proposes_probabilistic` |
| SIG-IDENT-021 (Splink 4 on a DuckDB backend; AGPL/proprietary excluded) | `resolution.probabilistic.ProbabilisticMatcher.match` (`DuckDBAPI`, `Linker`); `resolution/pyproject.toml` (`splink>=4`, `duckdb`); ADR-029 | `tests/resolution/test_probabilistic.py::test_evidence_names_the_splink_duckdb_matcher`, `::test_matching_is_deterministic` |
| SIG-IDENT-025 (every match records `match_tier`, `match_evidence`; probabilistic → match weight **and** its per-comparison decomposition) | `resolution.probabilistic` (`ProbabilisticMatch.match_weight`/`decomposition`, `ComparisonContribution`, `match_evidence["decomposition"]`); fully-specified m/u model `data/splink_model.toml` | `tests/resolution/test_probabilistic.py::test_every_match_records_tier_evidence_weight_and_decomposition`, `::test_decomposition_is_mirrored_in_evidence_json`, `::test_strong_name_match_reaches_tier4_with_explainable_weight` |

## Sized blocking (SIG-IDENT-023/024)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-023 (blocking rules sized before use, rejected above a documented comparison ceiling; suffix-alone / state-alone prohibited) | `resolution.blocking` (`size_blocking_rule`, `validate_blocking_rule`, `blocked_pairs`, `BlockingContext`, `BlockingRuleRejected`); `data/blocking_rules.toml` (`comparison_ceiling`, `prohibited_sole_keys`) | `tests/resolution/test_blocking.py::test_size_counts_exact_within_block_pairs`, `::test_oversized_rule_is_rejected`, `::test_sole_low_cardinality_key_is_prohibited`, `::test_blocked_pairs_aborts_if_any_rule_is_prohibited`; `tests/resolution/test_probabilistic.py::test_oversized_blocking_aborts_the_match` |
| SIG-IDENT-024 (trigram may power candidate search but never a decision score) | `resolution.blocking` (`trigrams`, `method="trigram"`); `resolution.probabilistic.assert_no_trigram_decision` | `tests/resolution/test_blocking.py::test_trigram_generates_candidates`; `tests/resolution/test_probabilistic.py::test_trigram_decision_score_is_rejected`, `::test_shipped_model_uses_no_trigram_decision_score`, `::test_jaro_winkler_is_allowed_as_a_decision_score` |

## Gold set + frozen holdout (SIG-IDENT-027)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-027 (stratified blocked-pair sampling across weight bands; double adjudication reporting Cohen's κ; three-value label vocabulary; written adjudication rules; frozen holdout; versioned data with per-label provenance) | `resolution.gold_set` (`stratified_sample`, `GoldLabel`, `cohens_kappa`, `adjudicated_label`, `Adjudication`, `GoldSet`/`holdout`/`relabel`, `adjudication_rules`, `build_gold_set`); `data/gold_set_rules.toml` (`labels`, `[[band]]`, `holdout_fraction`, `adjudication_rules`) | `tests/resolution/test_gold_set.py::test_label_vocabulary_is_exactly_three_values`, `::test_stratified_sample_covers_every_band_and_caps_per_band`, `::test_kappa_is_below_one_on_disagreement`, `::test_gold_set_is_versioned_and_carries_provenance`, `::test_holdout_is_a_frozen_fraction`, `::test_frozen_holdout_pair_cannot_be_relabelled` |

## Quality gates + cluster-shape alerts (SIG-IDENT-028/029)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-028 (pairwise P/R/F1 at each tier boundary + B-cubed cluster P/R on the holdout; auto-write tiers demoted to review on a holdout-precision breach) | `resolution.quality_gates` (`metrics_at_tier_boundaries`, `pairwise_metrics`, `bcubed`, `demote_auto_write_tiers`, `DemotionDecision`, `AUTO_WRITE_TIERS`); floor `data/splink_model.toml` (`auto_write_precision_threshold`) | `tests/resolution/test_quality_gates.py::test_metrics_reported_at_each_tier_boundary`, `::test_bcubed_penalises_a_bad_merge`, `::test_bcubed_penalises_a_bad_split`, `::test_auto_write_tier_demoted_when_precision_below_threshold`, `::test_only_auto_write_tiers_are_demotable` |
| SIG-IDENT-029 (cluster-shape alerts: oversized PD/sheriff cluster; single-bridge join of substantial components) | `resolution.quality_gates` (`cluster_shape_alerts`, `ClusterShapeAlert`, `ClusterShapeContext`, `_bridges`); `data/quality_gates.toml` (`max_le_cluster_size`, `substantial_component_size`, `le_classes`) | `tests/resolution/test_quality_gates.py::test_oversized_law_enforcement_cluster_is_flagged`, `::test_single_bridge_join_of_substantial_components_is_flagged`, `::test_densely_connected_cluster_has_no_bridge_alert`, `::test_bridge_to_a_singleton_is_not_substantial` |
| SIG-IDENT-032 (public identifiers stable across split/merge; surviving id preserved, retired id → redirect/tombstone, never silently reassigned) | `resolution.er_run.stabilise_cluster_change` routing through `resolution.public_id.PublicIdRegistry` (`merge`/`split`/`resolve`) | `tests/resolution/test_er_run.py::test_merge_preserves_survivor_and_redirects_the_retired_id`, `::test_split_tombstones_source_into_minted_successors`, `::test_split_without_a_minter_is_refused` |

## ER as a distinct, re-runnable pipeline stage (SIG-RECON-001/002)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-001 (ER runs as a distinct stage between `normalize()` and `load()`, with its own run record, quality report, and rollback path) | `resolution.er_run` (`ERRun`/`to_row`/`completed`/`rolled_back`, `ERQualityReport`, `ERResult`, `stage_between`, `run_entity_resolution`) | `tests/resolution/test_er_run.py::test_stage_runs_between_normalize_and_load`, `::test_run_record_enforces_deterministic_environment`, `::test_run_record_row_has_versions_and_status`, `::test_completed_and_rolled_back_status_transitions`, `::test_report_records_blocking_sizes_and_passes_gate` |
| SIG-RECON-002 (re-runnable over historical claims without destroying prior clustering; a re-cluster produces new `same_as` assertions with a new ruleset version, never silently moving claims) | `resolution.er_run` (`recluster`, `ERRun.rerun`, `cluster_same_as`) | `tests/resolution/test_er_run.py::test_rerun_requires_a_new_ruleset_version`, `::test_rerun_chains_to_previous_and_flags_rerun`, `::test_recluster_produces_new_run_without_touching_the_prior_result`, `::test_cluster_same_as_emits_star_relations` |

## CLI (SIG-ENG-013)

| Requirement | Where | Test |
|---|---|---|
| SIG-ENG-013 (the probabilistic stage is a plain CLI: `er-match` prints PROPOSED proposals with weights; `block-size` sizes an equijoin rule) | `resolution.cli` (`er-match`, `block-size` subcommands) | `tests/resolution/test_cli_er.py::test_er_match_prints_proposals`, `::test_block_size_accepts_a_selective_rule`, `::test_block_size_rejects_state_alone`, `::test_er_match_on_no_matches_is_graceful` |

# P05.2 — Curation UI and review queue (the LLM boundary + the review path)

P05.2 adds the internal review queue + curation contract (`resolution.review_queue`) and
the model-assisted-extraction scaffolding — the LLM boundary (`parsing.extraction`) — as
pure, tested library code plus versioned data and a plain CLI. Model output reaches only
the review queue at R6/`PROPOSED`, never the graph; the curation UI is the CLI and the
JSON-serialisable queue (the persistence P05.1 deferred); the web surface is P15.x. See
ADR-030.

## Model-assisted extraction scaffolding (SIG-LLM-001/002/003)

| Requirement | Where | Test |
|---|---|---|
| SIG-LLM-001 (models MAY propose candidate structured claims / review rationales, for the human queue only) | `parsing.extraction` (`ExtractedClaim`, `run_extraction` → proposals; `resolution.review_queue.ReviewDecision.rationale` is a note, never authority) | `tests/parsing/test_extraction.py::test_available_model_returns_proposed_claims`; `tests/resolution/test_review_queue.py::test_model_extraction_item_is_model_assisted_and_logs_provenance_on_decision` |
| SIG-LLM-002 (models MUST NOT write to the graph or be a self-standing claim; output only to the queue) | `parsing.extraction.ExtractedClaim.writes_to_graph` (always False); `resolution.review_queue.ReviewQueue` (no graph-write method; only `enqueue`/`decide`) | `tests/parsing/test_extraction.py::test_extracted_claim_is_r6_and_proposed_and_never_writes_to_graph`; `tests/resolution/test_review_queue.py::test_queue_has_no_graph_write_path` |
| SIG-LLM-003 (every extraction records `model_id`, `prompt_version`, deterministic parameters; validates output against a schema) | `parsing.extraction` (`ModelExtraction`, `deterministic_parameters`, `validate_output`); `data/extraction_schema.toml` (`[deterministic_parameters]`, `[schema.*]`) | `tests/parsing/test_extraction.py::test_extraction_records_model_prompt_and_deterministic_parameters`, `::test_extraction_without_its_provenance_is_rejected`, `::test_schema_validation_rejects_a_missing_claim_field`, `::test_schema_validation_rejects_a_span_missing_its_locator` |

## Source-span guardrail (SIG-LLM-004, SIG-PARSE-003)

| Requirement | Where | Test |
|---|---|---|
| SIG-LLM-004 / SIG-PARSE-003 (every model-extracted claim carries a source span; a span not present in the capture is rejected) | `parsing.extraction` (`SourceSpan`, `validate_span`, `extract_claims`) | `tests/parsing/test_extraction.py::test_span_present_in_the_capture_is_accepted`, `::test_span_text_not_in_the_capture_is_rejected`, `::test_span_offsets_beyond_the_capture_are_rejected`, `::test_span_without_text_or_locator_is_rejected`, `::test_extract_rejects_the_whole_batch_when_one_span_is_unlocatable`; `tests/parsing/test_cli_extraction.py::test_extract_rejects_a_hallucinated_span` |

## R6 + PROPOSED, never to the graph (SIG-LLM-005)

| Requirement | Where | Test |
|---|---|---|
| SIG-LLM-005 (model-extracted claims are R6 and enter as `PROPOSED`) | `parsing.extraction.ExtractedClaim` (`source_reliability=R6`, `claim_status=PROPOSED`, both enforced in `__post_init__`) | `tests/parsing/test_extraction.py::test_extracted_claim_is_r6_and_proposed_and_never_writes_to_graph`, `::test_a_claim_at_a_lowered_standard_cannot_be_constructed` |

## Sampling + gold-accuracy demotion (SIG-LLM-006)

| Requirement | Where | Test |
|---|---|---|
| SIG-LLM-006 (per-extraction-type review sampling rate; gold-set accuracy measured; demotion to human-only on breach) | `parsing.extraction` (`ExtractionTypePolicy`, `load_policies`, `should_sample_for_review`, `measure_accuracy`, `evaluate_demotion`); `data/extraction_schema.toml` (`[[extraction_type]]`) | `tests/parsing/test_extraction.py::test_policies_are_loaded_per_extraction_type`, `::test_accuracy_below_the_floor_demotes_to_human_only`, `::test_accuracy_at_or_above_the_floor_does_not_demote`, `::test_a_passing_measurement_does_not_repromote_a_demoted_type`, `::test_measure_accuracy_counts_matches_against_gold`, `::test_sampling_is_deterministic_and_total_when_demoted`; `tests/parsing/test_cli_extraction.py::test_sampling_reports_demotion` |

## Graceful degradation (SIG-LLM-007)

| Requirement | Where | Test |
|---|---|---|
| SIG-LLM-007 (model unavailable → work queues, does not fail; no lowered-standard claim emitted) | `parsing.extraction` (`run_extraction`, `ExtractionOutcome`, `MODEL_UNAVAILABLE`, `ModelClient`) | `tests/parsing/test_extraction.py::test_unavailable_model_queues_the_work_and_emits_no_claim`, `::test_available_model_with_a_hallucinated_span_still_rejects` |

## Review queue + confidence explanation (SIG-IDENT-025/026, §27)

| Requirement | Where | Test |
|---|---|---|
| SIG-IDENT-025 (the per-comparison confidence explanation for each proposed match is surfaced in the review UI; a reviewer accepts/rejects) | `resolution.review_queue` (`review_item_from_match`, `ConfidenceFactor`, `surface_confidence_explanation`, `ReviewQueue.decide`); `resolution.cli` (`review list`/`show`/`decide`) | `tests/resolution/test_review_queue.py::test_match_item_carries_the_per_comparison_decomposition`, `::test_surface_confidence_explanation_shows_the_decomposition`, `::test_reviewer_can_accept_a_proposed_match`, `::test_reviewer_can_reject_a_proposed_match`; `tests/resolution/test_cli_review.py::test_enqueue_list_and_decide_flow` |
| SIG-IDENT-026 (LLMs may generate review rationales but MUST NOT write to the graph; model id + prompt version logged with each human decision) | `resolution.review_queue` (`ReviewItem.model_assisted`, `ReviewQueue.decide` copies `model_id`/`prompt_version` onto the `ReviewDecision`; no graph-write path) | `tests/resolution/test_review_queue.py::test_model_extraction_item_is_model_assisted_and_logs_provenance_on_decision`, `::test_a_model_assisted_item_missing_provenance_cannot_be_decided`, `::test_a_deterministic_er_match_decision_is_not_model_assisted`, `::test_queue_has_no_graph_write_path` |
| SIG-RECON-001 (the ER review path: decisions are append-only, an item is not re-decided) | `resolution.review_queue.ReviewQueue` (`decide` moves pending→decided, appends decision; refuses re-decide/duplicate) | `tests/resolution/test_review_queue.py::test_decisions_are_append_only_an_item_is_not_re_decided`, `::test_deciding_an_unknown_item_raises`, `::test_enqueue_rejects_a_duplicate_id`, `::test_queue_round_trips_through_json_dict` |

## CLI (SIG-ENG-013)

| Requirement | Where | Test |
|---|---|---|
| SIG-ENG-013 (the LLM-extraction stage and the curation surface are plain CLIs: `sig-parsing extract`/`sampling`; `sig-resolution review enqueue`/`list`/`show`/`decide`) | `parsing.cli` (`extract`, `sampling`); `resolution.cli` (`review` subcommands) | `tests/parsing/test_cli_extraction.py::test_extract_prints_proposed_claims`, `::test_sampling_lists_policies`; `tests/resolution/test_cli_review.py::test_enqueue_list_and_decide_flow`, `::test_decide_on_a_missing_item_reports_and_exits_nonzero` |

# P06.1 — Vertical slice: one jurisdiction end-to-end (Oklahoma City / OKCPD Flock)

The slice carries one real jurisdiction from evidence to a rendered dossier and
executes J-1. Requirement stamps below; the hardness precondition is declared in
`docs/slice/P06.1_hardness_precondition.md` (before the slice) and the
retrospective in `docs/slice/P06.1_retrospective.md` (HARD GATE §54, SIG-ENG-034).

## The J-1 acceptance query (SIG-CHART-009/010)

| Requirement | Where | Test |
|---|---|---|
| SIG-CHART-009 (J-1 has an executable acceptance query under `tests/acceptance/queries/`, run in CI) | `tests/acceptance/queries/test_j1_journalists_traversal.py`; `tests/acceptance/okc_slice.py` (`build_slice`, `j1_traversal`) | `tests/acceptance/queries/test_j1_journalists_traversal.py::test_j1_executes_end_to_end` |
| SIG-CHART-010 (every returned material fact carries a resolvable evidence ref; a coverage statement accompanies the result) | `okc_slice.material_facts`; `exports.dossier` (`what_we_dont_know`, `incompleteness_banner`) | `::test_every_material_fact_resolves_to_a_document_at_a_locator`, `::test_result_carries_a_coverage_and_incompleteness_statement` |

## Camera-count reconciliation (§29.1)

| Requirement | Where | Test |
|---|---|---|
| SIG-EPIS-021 (composed weight `W` from the published ordinal table) | `reconcile.weight.weight_class` | `tests/reconcile/test_weight.py::test_appendix_d2_worked_example_reproduces_exact_weight_classes`, `::test_base_reliability_maps_to_published_classes`, `::test_d5_and_c4_downgrades_floor_at_w1` |
| SIG-RECON-008 (currency `C` derived from volatility half-life at query time) | `reconcile.weight.currency`, `half_life_days` | `tests/reconcile/test_weight.py::test_currency_bands_track_half_life`, `::test_immutable_predicate_is_always_c1` |
| SIG-RECON-026 (the count predicates are distinct and never conflated) | `reconcile.counts.reconcile_counts`; `reconcile.model.COUNT_BASES`; the six registry predicates | `tests/reconcile/test_counts.py::test_three_answers_to_three_questions_not_one`, `tests/acceptance/queries/test_j1_journalists_traversal.py::test_count_predicates_are_distinct_with_their_own_resolutions` |
| SIG-RECON-027 (`mapped_device_count` is a lower bound only) | `reconcile.counts._resolve_one_basis` (`lower_bound`) | `tests/reconcile/test_counts.py::test_okc_predicates_stay_distinct` |
| SIG-RECON-028 (refuse to compare different `count_basis`; emit `PREDICATE_CONFLATION`) | `reconcile.counts.reconcile_as_single_count` | `tests/reconcile/test_counts.py::test_conflating_contracted_and_mapped_emits_predicate_conflation`, `tests/acceptance/queries/test_j1_journalists_traversal.py::test_predicate_conflation_fires_on_deliberate_conflation` |
| SIG-RECON-029 (every predicate carries its own resolution + `unresolved_delta` + tasks; no single true count) | `reconcile.counts.reconcile_counts`, `_compute_deltas`; `reconcile.model.CountReconciliation.true_count` | `tests/reconcile/test_counts.py::test_no_single_true_count_is_emitted`, `::test_deltas_become_research_tasks` |
| SIG-ONTO-067 (new count predicates carry volatility/half-life/strategy/directness) | `ontology/vocab/predicates.yaml` (`invoiced_/mapped_/claimed_device_count`) | `tests/ontology/test_predicate_registry.py::test_every_predicate_has_volatility_strategy_and_directness_row`, `tests/reconcile/test_weight.py::test_registry_carries_all_six_count_predicates` |

## The local dossier (§39.2)

| Requirement | Where | Test |
|---|---|---|
| SIG-UI-010 (the twelve sections, in order) | `exports.dossier.SECTION_ORDER`, `Dossier.validate` | `tests/exports/test_dossier.py::test_sections_are_the_twelve_in_order`, `::test_out_of_order_sections_are_rejected` |
| SIG-UI-011 ("what we don't know" in summary + API + print) | `exports.dossier.render_json`, `render_print_html` | `tests/exports/test_dossier.py::test_what_we_dont_know_is_in_summary_and_api_and_print` |
| SIG-UI-012 (explicit incompleteness banner) | `exports.dossier.Dossier.incompleteness_banner` | `tests/exports/test_dossier.py::test_incompleteness_banner_names_count_and_absence_rule` |
| SIG-UI-013 (print/PDF path: paginated, sources, as-of + permalink on every page) | `exports.dossier.render_print_html` | `tests/exports/test_dossier.py::test_print_path_has_sources_and_asof_and_permalink_on_every_page` |
| SIG-UI-014 (every material figure expandable to its reconciliation) | `exports.dossier.Figure`, `Reconciliation`, `_figure_html` | `tests/exports/test_dossier.py::test_every_material_figure_is_expandable_to_its_reconciliation` |
| SIG-UI-015 (`unknown` rendered, not omitted) | `exports.dossier.Row.display_value` | `tests/exports/test_dossier.py::test_unknown_values_are_rendered_not_omitted` |

## The slice acceptance criteria (Phase 6, §52)

| Requirement | Where | Test |
|---|---|---|
| AC — a genuine contradiction detected + rendered without collapse | `okc_slice` (`value_disagreement`, `policy_configuration_divergence`); `exports.dossier` | `tests/acceptance/queries/test_j1_journalists_traversal.py::test_at_least_one_genuine_contradiction_rendered_without_collapse` |
| AC — hardness precondition satisfied, declared before the slice | `docs/slice/P06.1_hardness_precondition.md`; `okc_slice.build_slice` | `tests/acceptance/test_hardness_precondition.py` (all) |
| AC — a written retrospective is committed (HARD GATE §54, SIG-ENG-034) | `docs/slice/P06.1_retrospective.md` | `tests/acceptance/test_slice_artifacts.py::test_retrospective_is_committed_and_substantive` |

# P07.1 — The layered document-parsing stack (§24, the parser interface)

## Layered strategy (§24.1)

| Requirement | Where | Test |
|---|---|---|
| SIG-PARSE-001 (cheapest sufficient of seven layers; method recorded on the extraction) | `parsing/src/parsing/layers.py` (`ExtractionLayer`, `cheapest_sufficient`, `.method`); `parsing.claim.ParsedClaim.extraction_method` | `tests/parsing/test_layers.py::test_cheapest_sufficient_picks_the_least_cost_candidate`, `::test_method_strings_match_the_extraction_method_vocabulary`, `tests/parsing/test_claim.py::test_claim_records_method_and_carries_raw_value_and_locator` |
| SIG-PARSE-002 (classification runs before parsing; verdict recorded; mixed-format ZIP classified per member) | `parsing/src/parsing/classification.py` (`classify`, `classify_archive`, `ClassificationVerdict.to_row`) | `tests/parsing/test_classification.py::test_mixed_response_archive_is_classified_per_member`, `::test_encrypted_pdf_is_flagged_and_routed_to_human`, `::test_the_verdict_is_recordable` |
| SIG-PARSE-003 (mandatory locator on every claim; locator-less extraction rejected) | `parsing/src/parsing/locator.py` (`Locator`, `LocatorRequired`); `parsing.claim.ParsedClaim.__post_init__` | `tests/parsing/test_claim.py::test_a_claim_without_a_locator_is_rejected`, `tests/parsing/test_locator.py` (all) |
| SIG-PARSE-004 (`raw_value` preserved before typing, including for unparseable values, P2) | `parsing/src/parsing/claim.py` (`ParsedValue.typed`/`unparseable`, `raw_value` mandatory) | `tests/parsing/test_claim.py::test_raw_value_is_preserved_for_an_unparseable_value_round_trip`, `::test_raw_value_may_not_be_none` |

## Reason-code normalization (§24.2)

| Requirement | Where | Test |
|---|---|---|
| SIG-PARSE-005 (versioned, inspectable, reversible mapping as data; raw text retained; mapping version stamped; no history rewrite, SIG-STORE-038) | `parsing/src/parsing/reason_codes.py`; `parsing/src/parsing/data/reason_codes.toml`; `VOCABULARY_MIGRATION_METHOD` | `tests/parsing/test_reason_codes.py::test_every_canonical_code_is_reversible`, `::test_the_mapping_version_is_stamped_on_every_result`, `::test_changing_the_mapping_does_not_rewrite_history` |
| SIG-PARSE-006 (free-text vs constrained-dropdown reasons distinguished; dropdown a stronger signal) | `parsing.reason_codes.ReasonKind`, `SignalStrength`, `ReasonMapping.normalize` | `tests/parsing/test_reason_codes.py::test_free_text_and_dropdown_are_distinguished_by_signal_strength`, `::test_an_unmapped_reason_retains_its_raw_text_and_does_not_match` |

## Parser drift (§24.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-PARSE-007 (committed fixtures per parser: real input → expected output) | `parsing/src/parsing/drift.py` (`FixtureCase`, `assert_no_drift`); `tests/parsing/fixtures/records/mixed_response.zip` (+ `build_mixed_response.py`) | `tests/parsing/test_drift.py::test_committed_fixture_passes_for_an_unchanged_parser`, `::test_a_drifted_parser_fails_the_fixture_assertion`, `tests/parsing/test_classification.py::test_mixed_response_archive_is_classified_per_member` |
| SIG-PARSE-008 (nightly canary vs live sources alerts — not silently drops — on structural change; R11) | `parsing.drift` (`StructuralExpectation`, `structural_findings`, `run_canary`, `CanaryReport.alerted`); `tests/parsing/fixtures/canary/` | `tests/parsing/test_drift.py::test_canary_alerts_and_does_not_drop_on_structural_drift`, `::test_canary_is_clean_on_the_expected_shape` |

## The `parsing` CLI surface (§24, SIG-ENG-013)

| Requirement | Where | Test |
|---|---|---|
| `sig-parsing classify` (per-member for a ZIP), `layers`, `reason` (normalize + reverse) | `parsing/src/parsing/cli.py` | `tests/parsing/test_cli_parsing.py` (all) |

# P07.2 — The `records` connector and `RecordsRequest` (§23.5, §11.19)

The third source connector on the P04.1 framework (`connectors.records`, ADR-034):
MuckRock/NextRequest/DocumentCloud as a **targeted-lookup** client, the `RecordsRequest`
runtime shape, and the `no_responsive_records` → coverage bridge. The ontology schema
(`RecordsRequest`, `RecordsResponseStatus`, `RecordsPlatform`, `CoverageRecord`,
`EvidenceArtifact`) is P01.1; this ticket owns the connector runtime + the bridge.

## `records` connector + `RecordsRequest` (§23.5, §11.19)

| Requirement | Where | Test |
|---|---|---|
| §23.5 `records` connector on the P04.1 eight-stage framework, writing `RecordsRequest` entities, `EvidenceArtifact` rows, and released-document captures | `connectors/src/connectors/records.py` (`RecordsConnector`, `RecordsRequest`, `EvidenceArtifactRow`); registered in `connectors/__init__.py` | `tests/connectors/test_records.py::test_the_pipeline_ingests_a_records_request_end_to_end`, `::test_a_released_document_capture_becomes_an_evidence_artifact_linked_to_the_request`, `tests/connectors/test_cli.py::test_list_connectors_includes_the_records_connector` |
| §11.19 `RecordsRequest` predicate surface (requesting_party, target_agency, request_text, filed/response dates, response_status, statutory_basis, platform, external_id, released_documents), validated against the frozen `RecordsResponseStatus`/`RecordsPlatform` enums | `connectors.records.RecordsRequest` (`predicate_values`, `claim_rows`, `__post_init__`); `data/records_vocab.toml` (`response_statuses`, `platforms`) | `tests/connectors/test_records.py::test_response_status_vocab_matches_the_ontology_enum`, `::test_platform_vocab_matches_the_ontology_enum`, `::test_invalid_platform_is_rejected`, `::test_invalid_response_status_is_rejected`, `::test_external_id_is_required` |
| SIG-ONTO-040 — `response_status = 'no_responsive_records'` is a positive finding writing a `CoverageRecord` in the `NO_EVIDENCE_FOUND` state (naming sources searched, SIG-TIME-011), never a discarded null | `connectors.records.coverage_record_row` (reuses `db.absence` `AbsenceState.NO_EVIDENCE_FOUND`, `coverage_kind_for`, `render_absence`); `RecordsConnector._normalize_request` | `tests/connectors/test_records.py::test_no_responsive_records_writes_a_coverage_record`, `::test_no_responsive_records_flows_through_normalize`, `::test_coverage_record_must_name_the_sources_searched`, `::test_coverage_record_only_for_the_positive_finding_status`, `::test_a_fulfilled_request_writes_no_coverage_record` |
| §23.5 / R4 F4.1–F4.3 — MuckRock is api_v2 (not api_v1) with a short-lived (5-min) JWT on all data endpoints; refresh early + on 401 | `connectors.records` (`muckrock_endpoint`, `assert_muckrock_api_v2`, `MuckRockToken`, `MuckRockTokenCache`, `TokenSource`, `RecordsConnector.fetch`); `connectors.net` per-request `headers` seam | `tests/connectors/test_records.py::test_muckrock_endpoints_are_api_v2_never_v1`, `::test_muckrock_data_endpoint_requires_a_jwt`, `::test_fetch_attaches_the_bearer_jwt_to_a_muckrock_data_endpoint`, `::test_jwt_lifetime_is_five_minutes_and_effective_ttl_is_shorter`, `::test_the_jwt_cache_refreshes_before_the_token_expires`, `::test_fetch_refreshes_the_jwt_on_a_401_and_retries_once`, `::test_a_persistent_challenge_still_propagates` |
| A run record + quality report are produced per capture | `connectors.records.CaptureQualityReport`; `evidence.ingest_run.IngestRun` on `ctx.run`; `RecordsConnector._normalize_request`/`_normalize_document` | `tests/connectors/test_records.py::test_a_run_record_and_quality_report_are_produced_per_capture` |
| Every released document captured as an `EvidenceArtifact` and linked from the request via `released_documents` (calling the P07.1 parser to classify, per-member for a mixed-format ZIP) | `connectors.records` (`evidence_artifact_id`, `EvidenceArtifactRow`, `classify_released_document`, `RecordsConnector.parse`/`_normalize_document`) → `parsing.classification.classify`/`classify_archive` | `tests/connectors/test_records.py::test_released_documents_link_by_stable_artifact_id`, `::test_a_released_document_capture_becomes_an_evidence_artifact_linked_to_the_request`, `::test_a_mixed_format_zip_response_is_classified_per_member`, `::test_evidence_artifact_row_shape` |
| SIG-INGEST-036/037 — rate-limited APIs are targeted lookups only; no enumeration/crawl path (a legal posture) | `connectors.records` (`assert_targeted_lookup`, `CrawlAttempted`, `_is_enumeration_url`, `RecordsConnector.discover`/`fetch`) | `tests/connectors/test_records.py::test_crawl_mode_target_is_refused`, `::test_paginated_target_is_refused`, `::test_bare_listing_endpoint_is_refused`, `::test_specific_lookup_is_allowed`, `::test_discover_returns_only_supplied_targets_and_refuses_a_crawl` |
| SIG-INGEST-033 — predicate allowlist enforced as a hard schema gate | `connectors.records` (`predicate_allowlist`, `assert_predicate_allowed`, `PredicateNotAllowed`, `forbidden_predicate_genres`); `data/records_vocab.toml` | `tests/connectors/test_records.py::test_predicate_allowlist_is_the_records_request_surface`, `::test_writing_outside_the_allowlist_is_a_schema_error`, `::test_forbidden_genres_are_outside_the_allowlist` |
| SIG-INGEST-034 — the connector emits candidate identifiers and never resolves entities itself | `connectors.records.agency_candidate`; `RecordsRequest.claim_rows` (candidate_identifier on party predicates) | `tests/connectors/test_records.py::test_party_predicates_carry_a_candidate_identifier_not_a_resolution`, `::test_numeric_agency_routes_to_the_platform_scheme` |
| SIG-INGEST-003 — append-only load contract (claim_id + sys_period only on claim/entity rows) | `connectors.records.load_claims_for_l1` | `tests/connectors/test_records.py::test_load_adds_identity_only_to_claim_and_entity_rows` |
| SIG-INGEST-011 — auth rides the single shared egress seam (additive per-request `headers`) | `connectors/src/connectors/net.py` (`PoliteFetcher.fetch`, `Transport`/`Fetcher` `headers`); `connectors/src/connectors/stages.py` (`Fetcher`) | `tests/connectors/test_records.py::test_fetch_attaches_the_bearer_jwt_to_a_muckrock_data_endpoint`; existing `tests/connectors/test_net.py` (back-compat) |

# P07.3 — The `procurement` connector, `FundingInstrument`, and the agenda-platform tenant registry (§23.6, §11.11, §11.12)

The fourth source connector on the P04.1 framework (`connectors.procurement`, ADR-035):
cooperative purchasing vehicles, USAspending sub-awards, and agenda platforms as a
targeted-lookup client, the `Contract`/`FundingInstrument` runtime shapes, the published
agenda-platform tenant registry, and the `artifact_type` ontology vocabulary. The ontology
schema (`Contract`, `FundingInstrument`, `AcquisitionChannel`, `FundingInstrumentType`,
`ProcurementState`) is P01.1; this ticket owns the connector runtime, the tenant registry,
and the `ArtifactType` enum + SIG-INGEST-047 additions.

## `procurement` connector + `Contract`/`FundingInstrument` (§23.6, §11.11, §11.12)

| Requirement | Where | Test |
|---|---|---|
| §23.6 `procurement` connector on the P04.1 eight-stage framework, writing `Contract`, `FundingInstrument`, `acquisition_channel`, quantities, renewal terms, dated lifecycle transitions | `connectors/src/connectors/procurement.py` (`ProcurementConnector`, `Contract`, `FundingInstrument`, `LifecycleTransition`); registered in `connectors/__init__.py` | `tests/connectors/test_procurement.py::test_pipeline_ingests_a_cooperative_contract_end_to_end`, `::test_dated_lifecycle_transition_is_written`, `tests/connectors/test_cli.py::test_list_connectors_includes_the_procurement_connector` |
| SIG-ONTO-032 — `acquisition_channel` + `parent_cooperative_contract` are REQUIRED; a cooperative piggyback MUST link the ridden master award (a missing local RFP is not "no procurement evidence") | `connectors.procurement.Contract.__post_init__` (cooperative_piggyback → parent enforced), `_build_contract` (cooperative-vehicle default), `cooperative_vehicles`, `is_cooperative_vehicle` | `tests/connectors/test_procurement.py::test_cooperative_piggyback_contract_requires_parent`, `::test_cooperative_vehicle_source_defaults_to_piggyback_and_links_master`, `::test_cooperative_vehicle_without_master_award_is_a_hard_error`, `::test_all_named_cooperative_vehicles_are_registered` |
| §11.12 `FundingInstrument` — funder ≠ recipient ≠ purchaser; instrument_type / program_name / federal_award_id | `connectors.procurement.FundingInstrument` (`__post_init__` funder≠recipient, instrument_type validation, `predicate_values`, `claim_rows`) | `tests/connectors/test_procurement.py::test_subaward_becomes_funding_instrument_distinguishing_funder_from_recipient`, `::test_funder_and_recipient_must_differ`, `::test_funding_instrument_requires_both_parties`, `::test_invalid_instrument_type_is_rejected` |
| SIG-ONTO-033 — USAspending sub-awards pulled (not only prime awards) and traced to a local deployment via `federal_award_id` | `connectors.procurement.SubAward`, `funding_instrument_from_subaward`, `trace_subaward_to_deployment`, `assert_pulls_subawards`, `ProcurementConnector.discover`/`fetch`/`_normalize_subaward` | `tests/connectors/test_procurement.py::test_subaward_traces_to_deployment_via_federal_award_id`, `::test_usaspending_target_must_pull_subawards`, `::test_discover_asserts_usaspending_targets_pull_subawards`, `::test_subaward_flows_through_normalize_and_traces`, `::test_subaward_is_detected_apart_from_a_prime_contract`, `::test_pipeline_ingests_usaspending_subawards_end_to_end` |
| §22.3 / SIG-INGEST-026 — the agenda-platform tenant registry exists, is published, and the connector reads tenants from it | `connectors/src/connectors/data/agenda_tenants.toml`; `connectors.procurement.agenda_tenants`, `tenant_targets`, `agenda_registry`, `ProcurementConnector.discover` | `tests/connectors/test_procurement.py::test_agenda_tenant_registry_is_published_and_seeded`, `::test_connector_reads_tenants_from_the_registry`, `::test_tenant_targets_filter_by_platform` |
| SIG-METRIC-002a — tenant-discovery negatives retained as `NO_EVIDENCE_FOUND` coverage records (naming platforms probed, SIG-TIME-011), wired ahead of P09.1 | `connectors.procurement.tenant_discovery_negatives` (reuses `db.absence` `render_absence`/`coverage_kind_for`); `data/agenda_tenants.toml` `[negatives.*]` | `tests/connectors/test_procurement.py::test_tenant_discovery_negatives_are_retained_as_coverage` |
| SIG-INGEST-047 — `artifact_type` vocabulary carries `state_auditor_survey`, `warrant`, `procurement_aggregator_record`; the paywalled aggregator under a `LINK` custody posture | `ontology/src/ontology/schema/common.yaml` (`ArtifactType` enum), `entities.yaml` (`EvidenceArtifact.artifact_type`), `ontology/generate.py` (SKOS); `connectors.procurement` (`artifact_types`, `assert_artifact_type`, `EvidenceArtifactRow`, `_artifact_type_for_source`); `data/sources.toml` (`govspend`, LINK) | `tests/connectors/test_procurement.py::test_new_artifact_types_are_members_of_the_ontology_enum`, `::test_connector_artifact_types_are_a_subset_of_the_ontology_enum`, `::test_govspend_documents_carry_the_aggregator_artifact_type`, `::test_govspend_is_registered_under_a_link_custody_posture`; `tests/ontology/test_generation_gate.py` |
| SIG-INGEST-033 — predicate allowlist enforced as a hard schema gate | `connectors.procurement` (`predicate_allowlist`, `assert_predicate_allowed`, `PredicateNotAllowed`, `forbidden_predicate_genres`); `data/procurement_vocab.toml` | `tests/connectors/test_procurement.py::test_predicate_allowlist_is_the_contract_and_funding_surface`, `::test_writing_outside_the_allowlist_is_a_schema_error`, `::test_forbidden_genres_are_outside_the_allowlist` |
| SIG-INGEST-034 — the connector emits candidate identifiers and never resolves entities itself | `connectors.procurement.org_candidate`; `Contract.claim_rows`/`FundingInstrument.claim_rows` (candidate_identifier on party predicates) | `tests/connectors/test_procurement.py::test_party_predicates_carry_a_candidate_identifier_not_a_resolution`, `::test_funding_parties_carry_candidate_identifiers` |
| §11.11/§11.12/§13.4 vocabularies lock-stepped to the frozen ontology enums | `data/procurement_vocab.toml` (`acquisition_channels`, `funding_instrument_types`, `procurement_states`) | `tests/connectors/test_procurement.py::test_acquisition_channel_vocab_matches_the_ontology_enum`, `::test_funding_instrument_type_vocab_matches_the_ontology_enum`, `::test_procurement_state_vocab_matches_the_ontology_enum` |
| SIG-INGEST-003 — append-only load contract (claim_id + sys_period only on claim/entity rows) | `connectors.procurement.load_claims_for_l1` | `tests/connectors/test_procurement.py::test_load_adds_identity_only_to_claim_and_entity_rows` |

# P08.2 — The reconciliation workflows (§29)

The §29 per-predicate workflows layered on the P08.1 resolver (ADR-036): thin,
immutable value-object modules in `reconcile/` that emit contradictions, research
tasks, and an L4 device-attribution inference. P08.3 (§31) owns the materialized
`Contradiction` entity; P12.x (§30) owns the full L4 inference layer. §29.1
camera-count reconciliation landed in the P06.1 slice (above; SIG-RECON-026..029).

## Device attribution (§29.2)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-030 (candidate generation weighs spatial containment, distance, road-network context, adjacency, vendor match, unmapped count gaps) | `reconcile.attribution.CandidateOperator` (the six signals + `score`/`corroborating_score`), `attribute_operator` | `tests/reconcile/test_attribution.py::test_corroborated_candidate_yields_probable_l4_inference`, `::test_county_road_inside_city_does_not_default_to_containing_jurisdiction` |
| SIG-RECON-031 (output is an L4 `probable` inference; never written to `operator` as observed; never auto-pushed to OSM) | `reconcile.model.Inference` (`layer`/`is_observation`/`pushable_to_osm`/`as_observed_operator`), `reconcile.attribution._infer` | `tests/reconcile/test_attribution.py::test_corroborated_candidate_yields_probable_l4_inference`, `::test_inference_is_not_writable_as_observed_operator`, `::test_inference_is_never_auto_pushable_to_osm`; `tests/reconcile/test_model_inference.py::test_inference_is_never_auto_pushable_and_not_observable` |
| SIG-RECON-032 (the hard cases modelled, not defaulted: county road, state-police-in-city, on-behalf-of, multi-agency shared, boundary) | `reconcile.attribution.attribute_operator` (boundary/containment_only/cross_jurisdiction_road/multi_agency_shared/on_behalf_of/tie branches) | `tests/reconcile/test_attribution.py::test_containment_alone_is_not_attribution`, `::test_boundary_device_is_enqueued_not_picked`, `::test_multi_agency_shared_deployment_is_multiple_operators_not_a_conflict`, `::test_operator_on_behalf_of_names_the_role`, `::test_equally_corroborated_candidates_are_enqueued` |
| SIG-RECON-033 (promotion needs human confirmation or a D1/D2 source; a high score never self-promotes) | `reconcile.attribution.promote`, `PromotionRefused` | `tests/reconcile/test_attribution.py::test_high_score_does_not_promote_itself`, `::test_human_confirmation_promotes`, `::test_documentary_source_promotes`, `::test_weak_directness_does_not_promote` |

## Sharing-edge reconciliation (§29.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-034 (the three edge types reconciled separately; no merge) | `reconcile.sharing.ACCESS_KINDS`, `reconcile_sharing` (per-kind grouping) | `tests/reconcile/test_sharing.py::test_the_three_edge_types_are_reconciled_separately` |
| SIG-RECON-035 (asymmetry is a finding: `SHARING_ASYMMETRY` + research task, not a merge) | `reconcile.sharing.reconcile_sharing`; `reconcile.model.SHARING_ASYMMETRY` | `tests/reconcile/test_sharing.py::test_asymmetry_is_a_finding_not_a_merge`, `::test_reciprocated_edge_has_no_asymmetry` |
| SIG-RECON-036 (a single-snapshot edge carries `valid_from_kind='unknown'`; no start inferred from first observation) | `reconcile.sharing.SharingObservation.valid_from_kind`, `ReconciledEdge.valid_from_kind` | `tests/reconcile/test_sharing.py::test_single_snapshot_edge_carries_unknown_valid_from_kind`, `::test_multi_snapshot_edge_can_have_known_start` |
| SIG-RECON-037 (`observed_use` ↛ `configured_access` at L1; the inference is L4-only, labelled) | `reconcile.sharing.infer_access_from_use`, `L1InferenceForbidden` | `tests/reconcile/test_sharing.py::test_observed_use_does_not_create_configured_access_at_l1`, `::test_infer_access_rejects_non_use_edges` |

## Deployment-lifecycle reconciliation (§29.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-038 (the four tracks resolved independently) | `reconcile.lifecycle.TRACKS`, `resolve_lifecycle`, `resolve_track` | `tests/reconcile/test_lifecycle.py::test_four_tracks_are_resolved_independently` |
| SIG-RECON-039 (event-log transitions preferred over inferred) | `reconcile.lifecycle.resolve_track` (event-log-first tie stabiliser) | `tests/reconcile/test_lifecycle.py::test_event_log_transition_is_preferred_within_a_window` |
| SIG-RECON-040 (fuzzy dates ordered by EDTF envelope; overlapping ⇒ unordered-within-window) | `reconcile.lifecycle.resolve_track` (envelope-overlap window merge, reuses `db.edtf.derive_envelope`) | `tests/reconcile/test_lifecycle.py::test_distinct_dated_events_are_ordered`, `::test_overlapping_fuzzy_envelopes_are_unordered_within_window` |
| SIG-RECON-041 (vendor replacement ⇒ `replaced_by` edge rendered "vendor replaced", never "surveillance removed") | `reconcile.lifecycle.detect_vendor_replacement`, `ReplacedByEdge`, `REPLACEMENT_RENDER` | `tests/reconcile/test_lifecycle.py::test_vendor_replacement_is_rendered_as_replacement`, `::test_replacement_outside_window_is_not_detected`, `::test_replacement_requires_same_technology_family`, `::test_successor_predating_cancellation_is_not_a_replacement` |
| SIG-RECON-042 (canceled contract + installed hardware stated plainly, never smoothed) | `reconcile.lifecycle.render_lifecycle_status`, `LifecycleStatus` | `tests/reconcile/test_lifecycle.py::test_canceled_contract_with_hardware_present_is_stated_plainly`, `::test_ordinary_status_renders_both_tracks_without_a_finding` |

## Retention reconciliation (§29.5)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-043 (three retention predicates; disagreement is a finding; vendor default never populates configuration; a default change is not retroactive) | `reconcile.retention.reconcile_retention`, `populate_configured_from_vendor_default` (`VendorDefaultLeak`), `apply_vendor_default_change` | `tests/reconcile/test_retention.py::test_three_predicates_stay_distinct`, `::test_policy_versus_configured_disagreement_is_a_finding`, `::test_vendor_default_never_populates_configuration`, `::test_vendor_default_change_is_not_retroactive` |

## Policy-versus-configuration reconciliation (§29.6)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-044 (divergence is a first-class finding with both sides' evidence; never editorially collapsed; the immigration-hotlist case is expressible) | `reconcile.policy_config.reconcile_policy_configuration`, `PolicyConfigResult` (`collapse` raises); `reconcile.model.POLICY_CONFIGURATION_DIVERGENCE` | `tests/reconcile/test_policy_config.py::test_canonical_immigration_divergence_is_a_first_class_finding`, `::test_divergence_must_not_be_collapsed`, `::test_required_but_disabled_is_a_finding` |

## Snapshot-diff reconciliation (§29.7)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-045 (consecutive captures diffed at extracted-field level; per-field change events carry both values and both dates) | `reconcile.snapshot_diff.diff_captures`, `diff_series`, `FieldChangeEvent`, `Capture` | `tests/reconcile/test_snapshot_diff.py::test_modified_field_carries_both_values_and_both_dates`, `::test_added_and_removed_fields`, `::test_present_but_none_is_distinct_from_absent`, `::test_series_diffs_consecutively_in_chronological_order` |

## Additional workflows (§29.8)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-046 — cost/contract-value reconciliation (contract vs invoices vs budget vs cooperative SKU, distinct bases) | `reconcile.additional.reconcile_cost`, `COST_BASES`, `CostClaim` | `tests/reconcile/test_additional.py::test_cost_bases_stay_distinct_and_deltas_are_findings`, `::test_cost_agreement_has_no_finding` |
| SIG-RECON-046 — organization-existence reconciliation (named in a list, unknown to any registry; §14.4) | `reconcile.additional.reconcile_organization_existence`, `OrgExistenceFinding` | `tests/reconcile/test_additional.py::test_unknown_org_named_in_a_list_is_a_finding` |
| SIG-RECON-046 — capability reconciliation across disagreeing sources, respecting marketed-vs-configured (SIG-ONTO-018) | `reconcile.additional.reconcile_capability`, `CAPABILITY_KINDS`, `CapabilityClaim` | `tests/reconcile/test_additional.py::test_marketed_capability_does_not_imply_configured`, `::test_within_kind_disagreement_is_a_finding_and_stays_unresolved` |
| SIG-RECON-046 — geographic-coverage reconciliation (distinct scopes kept distinct) | `reconcile.additional.reconcile_geographic_coverage`, `CoverageClaim` | `tests/reconcile/test_additional.py::test_distinct_scopes_stay_distinct`, `::test_within_scope_disagreement_is_a_finding` |

# P08.3 — Contradiction as a first-class object (§31, §28.7)

The materialized `Contradiction` entity and its lifecycle (ADR-037): identity,
`claim_ids[]`, the five-state lifecycle, the `blocking → U7` manual brake, the
publish-not-hide projection, the byte-identical L3 rebuild gate, and the
detector→task contract. Promotes the existing `reconcile.model.Contradiction`
(additive/back-compat) and models it in pure Python aligned with
`db/deploy/graph_annotations.sql`.

## The materialized entity + lifecycle (§31)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-053 (`Contradiction` is a materialized entity: `subject_id`/`predicate_id`, `contradiction_type`, `claim_ids[]`, `severity`, `status`, resolution fields, `research_task_ids[]`, identity) | `reconcile.model.Contradiction`; `reconcile.contradiction.materialize`, `derive_contradiction_id` | `tests/reconcile/test_contradiction.py::test_entity_has_the_full_field_set_and_identity`, `::test_materialized_identity_is_content_derived_and_idempotent`, `::test_invalid_severity_and_status_are_rejected` |
| SIG-RECON-056 (`status ∈ {open, under_research, resolved, accepted_unresolvable, superseded}`; `accepted_unresolvable` a legitimate terminal state) | `reconcile.model.Contradiction.begin_research`/`resolve`/`accept_unresolvable`/`supersede`; `CONTRADICTION_STATUSES`/`OPEN_STATUSES`/`TERMINAL_STATUSES` | `tests/reconcile/test_contradiction.py::test_the_lifecycle_vocab_matches_the_spec`, `::test_open_flows_through_under_research_to_resolved`, `::test_accepted_unresolvable_is_a_legitimate_terminal_state`, `::test_illegal_transitions_are_refused` |
| SIG-RECON-054 (`severity = blocking` forces `UNRESOLVED` `U7`; the manual brake, deletes nothing) | `reconcile.contradiction.forces_unresolved`, `open_blocking_contradictions`; `reconcile.resolve.RESOLVE` (`blocking_contradiction` → `U7`) | `tests/reconcile/test_contradiction.py::test_open_blocking_contradiction_forces_unresolved_u7`, `::test_brake_only_bites_for_open_blocking_on_the_same_pair` |
| SIG-RECON-055 (`unresolved_conflict` is publishable — an open contradiction is exposed via `contradiction_state` and the API, not hidden) | `reconcile.model.Contradiction.public_state`/`public_view`; `reconcile.contradiction.publishable_view`; `reconcile.resolve._contradiction_state` | `tests/reconcile/test_contradiction.py::test_open_contradiction_is_published_as_unresolved_conflict_not_suppressed`, `::test_resolution_contradiction_state_exposes_open_conflict` |
| SIG-RECON-055 (a resolved contradiction remains visible in history; resolution sets status and does not delete) | `reconcile.model.Contradiction.resolve` (returns a new record, retains all fields) | `tests/reconcile/test_contradiction.py::test_resolution_sets_status_and_does_not_delete`, `::test_resolved_contradiction_remains_visible_in_history`, `::test_resolve_requires_note_and_actor` |
| SIG-RECON-057 (every contradiction detector emits a research task with a defined closing condition) | `reconcile.contradiction.detector_task_violations`, `assert_detector_task_contract`; linked tasks in `reconcile.resolve` (Phase 2.2/2.3), `reconcile.counts` | `tests/reconcile/test_detector_task_contract.py::test_every_detector_honours_the_detector_task_contract`, `::test_every_detector_emits_at_least_one_contradiction_on_its_fixture`; `tests/reconcile/test_contradiction.py::test_detector_task_contract_helper_flags_a_taskless_contradiction`, `::test_detector_task_contract_flags_dangling_or_empty_closing_condition` |

## Byte-identical L3 rebuild (§28.7)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-019 (resolutions recomputed on new/superseded claims, ruleset change, currency-class crossing) | `reconcile.resolve.RESOLVE` (as_of-driven currency; `input_digest` over claims + ruleset_version); `reconcile.rebuild.rebuild_resolution` | `tests/reconcile/test_rebuild.py::test_a_changed_claim_breaks_the_digest`, `::test_a_version_change_refuses_to_reproduce` |
| SIG-RECON-020 (a resolution is reproducible from `(claims + ruleset_version + resolver_version + as_of pair)`, verified by `input_digest`; CI regenerates a sample and asserts a match) | `reconcile.rebuild.verify_reproducible`, `load_sample`, `RebuildSample`; `reconcile/src/reconcile/data/l3_rebuild_sample.json` | `tests/reconcile/test_rebuild.py::test_committed_sample_regenerates_byte_identically`, `::test_sample_is_a_meaningful_multiclaim_resolution`, `::test_verify_reproducible_roundtrips_a_stored_resolution` |
| SIG-RECON-021 (resolutions are never edited in place; a new resolution supersedes the old in transaction time) | `reconcile.resolve.Resolution` (frozen) / `pin`; `reconcile.rebuild.rebuild_resolution` (returns a new record); `reconcile.model.Contradiction` lifecycle (append-only) | `tests/reconcile/test_rebuild.py::test_rebuild_returns_a_new_record_and_does_not_mutate_the_stored_one`; `tests/reconcile/test_contradiction.py::test_resolution_sets_status_and_does_not_delete` |

# P09.1 — Coverage, completeness, and negative space (§9.5, §32)

The §32 coverage-metrics layer (ADR-038): the `CoverageRecord` with required
`sources_searched[]`, discovery-probe negatives retained, the four absence kinds
rendered distinguishably in the API, published denominators on every aggregate,
per-jurisdiction coverage, provenance completeness, freshness relative to predicate
volatility, and the executable capture–recapture prohibition. Modelled as
pure-Python value objects in `inference/`, aligned with
`db/deploy/graph_annotations.sql`, reusing `db.absence` (four §9.5 states) and
`reconcile.weight.currency` (§28.3 currency) rather than re-encoding either. The read
API envelope (P14.1) and the methodology/coverage web pages (P15.5) consume these.

## The coverage record and the four absence kinds (§32.1, §9.5)

| Requirement | Where | Test |
|---|---|---|
| SIG-METRIC-001 (`CoverageRecord` shape: subject id/class, predicate, `absence_kind`, `sources_searched[]`, `searched_at`/`searched_by`, `search_method`) | `inference.coverage.CoverageRecord`; `db/deploy/graph_annotations.sql` `coverage_record` | `tests/inference/test_coverage.py::test_public_view_carries_the_full_shape`, `::test_coverage_record_requires_a_subject_identity`, `::test_unknown_absence_kind_is_rejected` |
| SIG-METRIC-002 (`sources_searched[]` **required** for `searched_not_found`; a record missing it is rejected) | `inference.coverage.CoverageRecord.__post_init__` (mirrors the DDL CHECK) | `tests/inference/test_coverage.py::test_searched_not_found_requires_sources_searched`, `::test_other_kinds_do_not_require_sources` |
| SIG-METRIC-002a (discovery-probe negatives retained as `searched_not_found`, not discarded) | `inference.coverage.probe_coverage_records` | `tests/inference/test_coverage.py::test_probe_retains_only_the_confirmed_absent_candidates`, `::test_probe_is_a_denominator_present_plus_absent_equals_candidates`, `::test_probe_rejects_a_present_id_outside_the_candidate_space`, `::test_probe_requires_named_sources` |
| SIG-TIME-010 (four absence kinds map to the §9.5 epistemic states; `not_applicable` carries none) | `inference.coverage.CoverageRecord.epistemic_state`; `db.absence.state_from_coverage_kind`, `ABSENCE_KINDS` | `tests/inference/test_coverage.py::test_epistemic_state_maps_kinds_and_not_applicable_is_stateless`; `tests/unit/test_absence.py::test_not_applicable_renders_distinguishably_and_has_no_state` |
| SIG-TIME-011 (`searched_not_found`/`NO_EVIDENCE_FOUND` MUST name the sources searched) | `db.absence.render_absence`/`render_coverage_kind`; `CoverageRecord.rendering` | `tests/unit/test_absence.py::test_render_coverage_kind_rejects_searched_not_found_without_sources`; `tests/inference/test_coverage.py::test_searched_not_found_requires_sources_searched` |
| SIG-TIME-012 (API renders the four kinds distinguishably; `not_researched` ≠ `searched_not_found`) | `inference.coverage.CoverageRecord.public_view`; `db.absence.render_coverage_kind`, `NOT_APPLICABLE_CODE` | `tests/inference/test_coverage.py::test_four_kinds_render_distinguishably_in_the_api_view`; `tests/unit/test_absence.py::test_render_coverage_kind_covers_all_four_kinds_distinguishably`, `::test_not_researched_differs_from_no_evidence_found` |

## Published denominators and per-jurisdiction coverage (§32.2, §32.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-METRIC-003 (every published aggregate carries its denominator and not-evaluable count; a bare count is not publishable) | `inference.denominators.PublishedAggregate`, `assert_denominated` | `tests/inference/test_denominators.py::test_bare_count_is_not_publishable`, `::test_published_aggregate_phrase_is_conformant`, `::test_a_numerator_cannot_exceed_its_denominator` |
| SIG-METRIC-004 (per-jurisdiction coverage: agencies known / with deployment / contract / portal evidence / mapped devices; mean evidence age; open-contradiction count; weight-class distribution) | `inference.denominators.jurisdiction_coverage`, `JurisdictionCoverage`, `AgencyCoverageInput` | `tests/inference/test_denominators.py::test_jurisdiction_coverage_denominates_every_count`, `::test_jurisdiction_coverage_mean_age_and_distribution`, `::test_jurisdiction_coverage_mean_age_is_none_when_no_dated_evidence`, `::test_jurisdiction_coverage_rejects_duplicate_agency` |

## Provenance completeness (§32.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-METRIC-005 (share of published claims with resolvable evidence, targeted at 100%; a shortfall is a defect list, not a statistic) | `inference.denominators.provenance_completeness`, `ProvenanceCompleteness` | `tests/inference/test_denominators.py::test_provenance_shortfall_is_a_defect_list_not_a_statistic`, `::test_provenance_complete_when_all_resolvable`, `::test_provenance_empty_is_trivially_complete` |

## Freshness relative to predicate volatility (§32.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-METRIC-006 (freshness measured relative to predicate volatility, not absolute days) | `inference.freshness.predicate_currency`, `is_stale_for_predicate` (delegates to `reconcile.weight.currency`, §28.3) | `tests/inference/test_freshness.py::test_same_age_yields_different_currency_by_volatility`, `::test_immutable_is_never_stale_however_old`, `::test_fast_predicate_goes_stale_past_its_window` |
| SIG-METRIC-007 (per-source freshness surface: last successful run, last content change, status, stale-count for the predicate class) | `inference.freshness.source_freshness`, `SourceFreshness` | `tests/inference/test_freshness.py::test_source_freshness_surface_counts_stale_by_predicate_class` |

## Completeness-estimation guardrails (§32.5)

| Requirement | Where | Test |
|---|---|---|
| SIG-METRIC-008 (capture–recapture population estimate prohibited — not with a caveat, not with a wide interval) | `inference.completeness.capture_recapture_population` (always raises `ProhibitedEstimateError`) | `tests/inference/test_completeness.py::test_capture_recapture_is_never_published` |
| SIG-METRIC-008a (multi-list log-linear rescue prohibited) | `inference.completeness.multi_list_log_linear_population` (always raises) | `tests/inference/test_completeness.py::test_multi_list_log_linear_is_never_published` |
| SIG-METRIC-008b (the one legitimate exception: records-derived survey recall — pre-registered, window < half-life, labelled method-recall, never extrapolated) | `inference.completeness.RecordsDerivedRecall` | `tests/inference/test_completeness.py::test_records_derived_recall_measures_the_survey_not_the_population`, `::test_records_derived_recall_must_be_pre_registered`, `::test_records_derived_recall_window_must_beat_the_half_life` |
| SIG-METRIC-009 (publish counted quantities with named denominators / bounds / ratios / measured recall — never a total) | `inference.completeness.CompletenessStatement`, `CompletenessMethod`, `assert_no_population_total` | `tests/inference/test_completeness.py::test_completeness_statement_with_a_named_denominator_is_publishable`, `::test_a_bare_number_is_not_a_publishable_completeness_figure` |
| SIG-METRIC-010 (no completeness percentage that implies it knows the denominator of reality) | `inference.completeness.CompletenessStatement.__post_init__` (rejects reality/total denominators) | `tests/inference/test_completeness.py::test_completeness_statement_rejects_a_denominator_of_reality` |

# P10.1 — The research-task engine (§33.1, §33.3–33.7)

The task-coordination **engine** (ADR-039): tasks as data with a testable closing
condition, the §33.3 lifecycle with auto-invalidation, the full disposition
vocabulary including "searched, found nothing" wired to a `CoverageRecord`,
non-exclusive expiring geographic queues, the anti-abuse rules, and the SIG-owned
local-group registry. Modelled as pure-Python value objects in `tasks/`, aligned with
`db/deploy/graph_annotations.sql`'s `research_task` row and reusing
`inference.coverage.CoverageRecord` (P09.1) for the disposition→data bridge rather than
re-encoding the §32.1 shape. The concrete detector *catalog* (§33.2) is P10.2; the
records-request path that exercises `resolved_no_evidence_exists` end-to-end is P10.3.

## The detector specification language (§33.1)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-001 (every task type declared as data with all eight fields: `task_type`, `detector`, `priority_fn`, `closing_condition`, `assignee_class`, `effort_estimate`, `dispositions[]`, `geographic_scope`) | `tasks.spec.TaskType`, `tasks.spec.Detector`, `tasks.vocabulary` (`AssigneeClass`, `Disposition`, `EffortEstimate`), `tasks.spec.GeographicScope` | `tests/tasks/test_spec.py::test_task_type_declares_all_eight_fields`, `::test_detector_and_priority_are_evaluable` |
| SIG-TASK-002 (a task type with **no testable `closing_condition`** MUST NOT register) | `tasks.spec.TaskType.has_testable_closing_condition`, `tasks.spec.TaskTypeRegistry.register` (raises `UntestableClosingConditionError`) | `tests/tasks/test_spec.py::test_untestable_closing_condition_cannot_register`, `::test_a_testable_closing_condition_registers_and_is_evaluable`, `::test_duplicate_slug_is_refused` |

## Lifecycle, auto-invalidation, dedup, claim timeout (§33.3)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-005 (`generated→triaged→claimed→in_progress→submitted→verified→closed` + `reopened`/`invalidated`) | `tasks.vocabulary.TaskStatus`, `is_legal_transition`, `tasks.lifecycle.ResearchTask` transition helpers | `tests/tasks/test_lifecycle.py::test_happy_path_traversal`, `::test_illegal_transition_is_refused` |
| SIG-TASK-006 (tasks **auto-invalidate** when their detector stops firing — evidence by another route silently closes them) | `tasks.lifecycle.TaskPool.sweep_invalidations`, `ResearchTask.detector_still_fires`/`invalidate` | `tests/tasks/test_lifecycle.py::test_auto_invalidate_when_detector_stops_firing`, `::test_a_task_whose_detector_still_fires_is_not_swept`, `::test_a_closed_task_is_not_reinvalidated` |
| SIG-TASK-007 (duplicate suppression by `(task_type, subject)`; claim timeout returns abandoned claims to the pool) | `tasks.lifecycle.TaskPool.generate` (dedup), `TaskPool.reclaim_expired`, `ResearchTask.claim_is_expired`/`release` | `tests/tasks/test_lifecycle.py::test_duplicate_suppression_by_task_type_and_subject`, `::test_different_subjects_are_distinct_tasks`, `::test_expired_claim_returns_to_the_pool` |

## Dispositions — the queue must be able to shrink (§33.4)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-008 (disposition vocabulary richer than "done": the eight §33.4 outcomes) | `tasks.vocabulary.Disposition`; `tasks.dispositions` (`RESOLVED_DISPOSITIONS`, `BLOCKED_DISPOSITIONS`) | `tests/tasks/test_dispositions.py::test_disposition_vocabulary_is_richer_than_done` |
| SIG-TASK-009 (`resolved_no_evidence_exists` writes a `CoverageRecord` with `absence_kind=searched_not_found` + sources; the only path to that disposition) | `tasks.dispositions.resolve_no_evidence_exists` (reuses `inference.coverage.CoverageRecord`); `ResearchTask.close` refuses the disposition directly | `tests/tasks/test_dispositions.py::test_resolved_no_evidence_exists_writes_a_coverage_record`, `::test_no_evidence_without_sources_is_refused_before_the_task_closes`, `::test_no_evidence_exists_is_unreachable_through_plain_close` |

## Geographic queues (§33.5)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-010 (a local group MAY claim a jurisdiction — visibility, notification, priority; **no exclusivity**) | `tasks.geographic.GeographicQueue.claim`/`has_priority`/`visible_jurisdictions`/`order_for_group` | `tests/tasks/test_geographic.py::test_claim_grants_priority_and_visibility`, `::test_claim_priority_orders_but_does_not_filter` |
| SIG-TASK-011 (claims **expire** without renewal; **any contributor** may work **any open task**) | `tasks.geographic.GeographicClaim.is_active`, `GeographicQueue.active_claims`, `tasks.geographic.any_contributor_may_work` | `tests/tasks/test_geographic.py::test_claims_expire_without_renewal`, `::test_a_claim_never_grants_exclusivity`, `::test_expired_claim_stops_boosting_order` |

## Anti-abuse (§33.6)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-012 (no volume leaderboards; recognition qualitative and tied to verified contributions) | `tasks.recognition.recognize`, `Recognition` (no score/rank field); `volume_leaderboard` (always raises `ProhibitedLeaderboardError`) | `tests/tasks/test_recognition.py::test_recognition_ignores_unverified_volume`, `::test_recognition_is_qualitative_not_a_count`, `::test_volume_leaderboard_is_an_executable_refusal` |
| SIG-TASK-013 (task generation rate-limited per subject so one badly-modelled entity cannot flood the queue) | `tasks.lifecycle.RateLimiter`, `TaskPool.generate` (per-subject budget) | `tests/tasks/test_lifecycle.py::test_rate_limiter_caps_generation_per_subject`, `::test_rate_limiter_is_a_rate_not_a_ban`, `::test_pool_refuses_to_flood_one_subject_with_task_types` |

## The SIG-owned local-group registry (§33.7)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-014 (SIG's own registry — name, jurisdiction, URL, contact, activity status, claimed queues — not dependent on an external directory) | `tasks.groups.LocalGroupRegistry`, `LocalGroup`, `ActivityStatus` | `tests/tasks/test_groups.py::test_registry_carries_every_sig_task_014_field`, `::test_registry_is_self_contained_no_external_dependency`, `::test_activity_status_update_is_immutable_per_row`, `::test_recording_a_claim_is_additive_and_idempotent` |

# P10.2 — The detector catalog (§33.2)

The concrete **task catalog** of §33.2 (ADR-040): the 34 enumerated task types, each
registered against P10.1's DSL (`tasks.spec`) with a versioned `detector` query and a
testable `closing_condition`, plus the §31 contradiction-detector→task map so every
contradiction has a route to resolution. Modelled in `tasks/catalog.py`; detectors read
the representative in-memory `Facts` keys P10.1 standardised (binding to the live graph
is downstream, RISK-P10-07). §33.2 is the count authority (34 rows). The catalog is the
data that turns the P10.1 engine into a working research-coordination queue.

## The task catalog (§33.2, SIG-TASK-003)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-003 (all 34 §33.2 task types implemented, each registered with a **testable** `closing_condition`; §33.2 is the count authority — a type that cannot express one cannot register) | `tasks.catalog.CATALOG_TASK_TYPES`, `CATALOG_SIZE` (34), `build_catalog` (registers all 34 through the SIG-TASK-002 gate) | `tests/tasks/test_tasks_catalog.py::test_catalog_has_exactly_the_34_types_of_the_count_authority`, `::test_building_the_catalog_registers_every_type`, `::test_every_catalog_type_has_a_testable_closing_condition`, `::test_every_catalog_type_declares_all_eight_fields_from_the_vocabulary` |
| Per-type detector fixtures — each detector fires on a seeded positive, stays quiet on a seeded negative, and **auto-invalidates** (through the P10.1 lifecycle) when its condition clears (SIG-TASK-006) | `tasks.catalog` detectors/closing conditions; `tasks.lifecycle.TaskPool.sweep_invalidations` | `tests/tasks/test_tasks_catalog.py::test_detector_fires_on_positive_and_is_quiet_on_negative`, `::test_closing_condition_is_open_on_positive_and_met_when_cleared`, `::test_task_auto_invalidates_when_its_condition_clears` (each parametrized over all 34 types) |

## Contradiction → task mapping (§31, SIG-TASK-004)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-004 (every §31 contradiction detector maps to a task type — detection without a route to resolution is just an alarm) | `tasks.catalog.CONTRADICTION_TASK_MAP` (keyed on the §31 `contradiction_type` vocabulary, routing each to a catalog task; many-to-one by design, ADR-040) | `tests/tasks/test_tasks_catalog.py::test_every_contradiction_type_maps_to_a_task` (keys == `reconcile.model.CONTRADICTION_TYPES`), `::test_every_mapped_task_type_is_a_registered_catalog_type` |

# P10.3 — Records-request generation (§36)

Records-request generation (ADR-041): given a research gap, emit a ready-to-file request
carrying the **correct statutory citation for the jurisdiction** from the 51-jurisdiction
records-law reference table; treat residency as operationally binding (refuse a
non-resident/unknown-residency filer in the six restricted states, route to the
jurisdiction's local filers, and record the barrier as a `not_researched` coverage fact);
version the request language and measure its success rate; gate on contributor consent;
and close a no-responsive-records reply through the P10.1 coverage-writing bridge. Modelled
in `tasks/records_request.py` with the reference table and templates as versioned data
(`tasks/data/records_law.toml`, `tasks/data/request_templates.toml`).

## Request generation with the correct statute (§36, SIG-TASK-015)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-015 (emit a ready-to-file request: target agency + records contact, the correct statutory citation for the jurisdiction, proven request language for the record type, the specific records sought) | `tasks.records_request.RecordsRequestGenerator.generate`/`_emit`, `GeneratedRecordsRequest` | `tests/tasks/test_tasks_records_request.py::test_emits_the_correct_statute_for_the_jurisdiction` (parametrized over 5 jurisdictions/record types), `::test_emitted_request_carries_the_sig_task_015_surface` |

## The 51-jurisdiction records-law reference table (§36, SIG-TASK-016)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-016 (per-jurisdiction records-law table for all 51 US jurisdictions: statute name/citation, initial response deadline, fee rules, appeal path, residency-required flag) | `tasks.records_request.records_law_table`/`RecordsLaw`/`records_law_for`, `tasks/data/records_law.toml` | `tests/tasks/test_tasks_records_law.py::test_table_covers_all_51_us_jurisdictions`, `::test_every_row_carries_all_six_reference_fields`, `::test_citations_are_distinct_per_jurisdiction`, `::test_records_law_for_unknown_jurisdiction_raises` |

## Residency handling — operationally binding (§36, SIG-TASK-016a/016b)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-016a (refuse to emit a non-resident's request in a residency-restricted jurisdiction; route the task to that jurisdiction's geographic queue / local filers; record the constraint as a coverage fact, §9.5/§32.2) | `tasks.records_request.RecordsRequestGenerator._route_residency_block`, `residency_barrier_coverage` (`not_researched`, attributed in `search_method`), `ResidencyBlock` (local filers + active claimants) | `tests/tasks/test_tasks_records_request.py::test_non_resident_in_restricted_jurisdiction_refuses_routes_and_records_coverage`, `::test_residency_barrier_coverage_is_never_searched_not_found`, `::test_residency_block_does_not_require_consent` |
| SIG-TASK-016b (unknown residency recorded as unknown and defaulting to the restrictive behaviour — route to a local filer — never assume openness) | `tasks.records_request.ResidencyStatus.UNKNOWN`, `_BLOCKED_IN_RESTRICTED` | `tests/tasks/test_tasks_records_request.py::test_unknown_residency_defaults_to_restrictive` |

## Versioned templates with measured success rates (§36, SIG-TASK-017)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-017 (request templates versioned; success rates measured; denial-producing language flagged for revision) | `tasks.records_request.TemplateLibrary`, `RequestTemplate`, `TemplateOutcomeLog`, `tasks/data/request_templates.toml` | `tests/tasks/test_tasks_templates.py::test_every_record_type_has_at_least_one_version`, `::test_success_rate_is_measured_from_recorded_outcomes`, `::test_denial_producing_language_is_flagged_for_revision`, `::test_undersampled_version_is_not_flagged`, `::test_working_language_is_not_flagged` |

## Consent gate (§36, SIG-TASK-018)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-018 (do not file on a contributor's behalf without explicit consent; make clear a filed request is a public act attributable to the filer) | `tasks.records_request.RecordsRequestGenerator._check_consent`, `Filer`, `GeneratedRecordsRequest.public_act_notice` | `tests/tasks/test_tasks_records_request.py::test_emit_without_consent_is_refused`, `::test_emit_without_public_act_acknowledgement_is_refused`, `::test_emitted_request_states_it_is_a_public_act` |

## `resolved_no_evidence_exists` → `CoverageRecord` through the records path (§36, SIG-TASK-009)

| Requirement | Where | Test |
|---|---|---|
| SIG-TASK-009 (a records request returning no responsive record writes a `CoverageRecord` — `searched_not_found` + sources searched — exercised through the records path) | `tasks.records_request.record_no_responsive_records` (reuses `tasks.dispositions.resolve_no_evidence_exists`) | `tests/tasks/test_tasks_records_request.py::test_no_responsive_records_writes_a_coverage_record` |

# P11.1 — The `flock_portal` connector (§23.4 — the portal layer via the aggregator API)

The fifth source connector on the P04.1 framework (`connectors.flock_portal`, ADR-042): the
Flock **portal layer** from the Eyes on Flock aggregator's public **CC BY-SA 4.0** JSON API,
landing in its own separable CC-BY-SA compartment, keyed on the upstream snapshot field, honouring
a challenge as a refusal, and feeding P08.2's §29.3 sharing-edge and §29.7 snapshot-diff
reconcilers (owned/tested there). All source-specific logic is pure and fixture-driven; no live
fetch runs in CI.

## Source, compartment, and the licence-compartment build guard (SIG-INGEST-035, SIG-LIC-004a)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-035 (source the portal layer from the aggregator's public CC-BY-SA-4.0 API, never the vendor; output lands in the CC-BY-SA-4.0 `portal` compartment, never the CC-BY graph) | `connectors.flock_portal` (`FlockPortalConnector`, `_stamp` → `CC_BY_SA_LICENSE`/`PORTAL_COMPARTMENT`); `policy/data/licenses.toml` (`compartments.portal`) | `tests/connectors/test_flock_portal.py::test_rows_land_in_the_cc_by_sa_portal_compartment`, `::test_portal_compartment_alone_exports_under_cc_by_sa` |
| SIG-LIC-004a (an export merging the portal compartment with the CC-BY graph fails the build) | `policy.licensing.compute_export_license`; `connectors.loader.assert_export_compatible` | `tests/connectors/test_flock_portal.py::test_export_merging_portal_with_the_cc_by_graph_fails_the_build` |

## No challenge-defeating code; a challenge is a refusal (SIG-INGEST-036/037, §26 rule 4)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-036/037 (honour a challenge/bot-management response as a refusal; no circumvention anywhere; connector holds no HTTP client of its own) | `connectors.flock_portal.FlockPortalConnector.fetch` (egress only via `ctx.fetcher`); `connectors.net.PoliteFetcher` raises `ChallengeEncountered`; `connectors.pipeline` records it as a disappearance | `tests/connectors/test_flock_portal.py::test_challenge_response_is_honoured_as_a_refusal`, `::test_the_fetcher_never_defeats_a_challenge` |

## Change detection keyed on the upstream snapshot field, not fetch time (SIG-INGEST-030c)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-030c (change detection + `observed_at` key on the upstream `data_last_updated` snapshot field, never fetch time; SIG does not poll faster than the upstream refresh) | `connectors.flock_portal` (`snapshot_field_name`, `portal_snapshot_date`, `is_poll_due`, `upstream_refresh_days`); `data/flock_portal_vocab.toml` (`snapshot_field`, `upstream_refresh_days`); the declared freshness recorded as `portal_last_updated_declared`, never trusted as `observed_at` | `tests/connectors/test_flock_portal.py::test_observed_at_is_the_upstream_snapshot_date_not_fetch_time`, `::test_declared_freshness_is_recorded_but_not_used_as_observed_at`, `::test_is_poll_due_keys_on_the_snapshot_and_respects_the_refresh_cadence` |

## Historical back-fill from archived captures (SIG-INGEST-030b)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-030b (back-fill sourced from archived captures of the API endpoint; a Wayback capture is a first-class target and its `observed_at` is the archived snapshot's own date) | `connectors.flock_portal.FlockPortalConnector.discover` (target-agnostic); `observed_at` keyed on `portal_snapshot_date` | `tests/connectors/test_flock_portal.py::test_backfill_from_an_archived_capture_keys_observed_at_on_the_snapshot` |

## `ai_training_permitted = false`, recorded and enforced (SIG-LIC-004b)

| Requirement | Where | Test |
|---|---|---|
| SIG-LIC-004b (the grant is recorded false on every row and enforced by the training gate for this source) | `connectors.flock_portal._stamp` (`ai_training_permitted = False`); `connectors.data.sources.toml` (`eyes_on_flock` omits the grant → default deny); `policy.licensing.assert_training_allowed` | `tests/connectors/test_flock_portal.py::test_ai_training_is_recorded_false_on_every_row`, `::test_ai_training_gate_refuses_this_source` |

## Portal-existence events (SIG-INGEST-035, §17.6)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-035 (a fetched portal emits `portal_exists = True`; a portal that drops out of a later snapshot emits `portal_exists = False` **and** a research task; a newly appeared portal emits an event + a "no known deployment" task) | `connectors.flock_portal` (`portal_exists_claim`, `portal_disappearance_task`, `portal_appeared_task`, `detect_portal_changes`) | `tests/connectors/test_flock_portal.py::test_portal_disappearance_produces_an_event_and_a_task`, `::test_portal_appearance_produces_an_event_and_a_no_known_deployment_task`, `::test_a_fetched_portal_emits_a_portal_exists_true_claim` |
| §17.6 (an endpoint 404 / persistent challenge is a first-class disappearance event + task) | `connectors.pipeline._fetch_or_disappear`; `connectors.disappearance` | `tests/connectors/test_flock_portal.py::test_challenge_response_is_honoured_as_a_refusal` |

## Snapshot diffing → per-field change events, via P08.2 (SIG-RECON-045)

| Requirement | Where | Test |
|---|---|---|
| SIG-RECON-045 (consecutive captures diffed at the extracted-field level → per-field change events with both values + both dates, through P08.2's reconciler — invoked, not forked) | `connectors.flock_portal` (`portal_capture`, `diff_portal_snapshots`) → `reconcile.snapshot_diff.diff_series` / `Capture` / `FieldChangeEvent` | `tests/connectors/test_flock_portal.py::test_snapshot_diff_produces_per_field_change_events_via_p08_2` |

## Portal sharing = configured access, directional, blanks-as-negatives (SIG-ONTO-042/044, SIG-RECON-034/035/036/037)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-042/044 (portal sharing lands as **configured access only**, directional, blank cells as negatives; single-snapshot edges carry `valid_from_kind='unknown'`) | `connectors.flock_portal` (`sharing_observations_for_portal`, `sharing_observations`, `reconcile_portal_sharing`, `_sharing_edge_rows`); `data/flock_portal_vocab.toml` (`[sharing]`) | `tests/connectors/test_flock_portal.py::test_sharing_edges_are_configured_access_directional_single_snapshot`, `::test_blank_sharing_cells_are_negatives_not_unknown_edges`, `::test_connector_streams_only_deterministic_edges_for_sharing` |
| SIG-RECON-034/035/036/037 (exercised here; owned/tested in P08.2) — asymmetry is a finding via the §29.3 reconciler run over the whole snapshot | `connectors.flock_portal.reconcile_portal_sharing` → `reconcile.sharing.reconcile_sharing` | `tests/connectors/test_flock_portal.py::test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler` |

## Predicate allowlist + the SIG-INGEST-031 fallbacks (§23.4, §18.1, SIG-INGEST-031)

| Requirement | Where | Test |
|---|---|---|
| §23.4 / §18.1 (predicate allowlist enforced as a schema gate; MUST NOT write contract facts, device geometry, or any per-search/per-plate row) | `connectors.flock_portal` (`predicate_allowlist`, `assert_predicate_allowed`, `PredicateNotAllowed`, `forbidden_predicate_genres`); `data/flock_portal_vocab.toml` | `tests/connectors/test_flock_portal.py::test_predicate_allowlist_and_forbidden_genres`, `::test_no_row_writes_a_predicate_outside_the_allowlist` |
| SIG-RECON-011 (the rolling usage counters are windowed, carrying their window length) | `connectors.flock_portal.field_claim` (`windowed`/`window_months`); `data/flock_portal_vocab.toml` (`window_months`, `[fields]` `windowed`) | `tests/connectors/test_flock_portal.py::test_windowed_usage_counters_carry_their_window` |
| SIG-INGEST-031 (the three fallbacks retained as named routes — records acquisition, contributor capture, partner archive; a challenge-defeating crawler is NOT a route; records-request generation itself is P10.3) | `connectors.flock_portal` (`fallback_routes`, `fallback_tasks_for_gaps`); `data/flock_portal_vocab.toml` (`[fallbacks.*]`) | `tests/connectors/test_flock_portal.py::test_the_three_fallback_routes_are_retained_and_named`, `::test_missing_aggregator_fields_route_to_the_fallbacks`, `::test_a_complete_portal_routes_to_no_fallback` |

## Fixtures, canary, registration, reproducibility, provenance (SIG-PARSE-007/008, SIG-INGEST-021/003)

| Requirement | Where | Test |
|---|---|---|
| SIG-PARSE-007 (committed fixtures) | `tests/connectors/fixtures/flock_portal/*.json` (two consecutive live snapshots + an archived Wayback capture) | driven throughout `tests/connectors/test_flock_portal.py` |
| SIG-PARSE-008 (a canary alerts on structural drift) | `connectors.flock_portal.canary_findings`, `parse_json` | `tests/connectors/test_flock_portal.py::test_canary_passes_on_the_committed_fixtures`, `::test_canary_flags_structural_drift` |
| SIG-INGEST-021 (connector self-registers on the plug-in seam; visible in the CLI) | `connectors.flock_portal.FlockPortalConnector` (`@register`); imported by `connectors.__init__` | `tests/connectors/test_flock_portal.py::test_flock_portal_connector_is_registered` |
| SIG-INGEST-003 (post-capture stages are pure; reproducible claim set — only the deterministic edges enter the stream) | `connectors.flock_portal` (`normalize` carries no wall-clock; `observed_at` keyed on the snapshot; sharing findings kept out of L1) | `tests/connectors/test_flock_portal.py::test_claim_set_is_reproducible_across_runs` |
| §23.4 (raw values preserved beside typed values; attribution + append-only, P1–P3) | `connectors.flock_portal` (`field_claim` `raw_value`/`extracted_field`; `_stamp` `source_attribution`; no `is_current`/authoritative flags) | `tests/connectors/test_flock_portal.py::test_raw_values_are_preserved_beside_typed_values`, `::test_rows_preserve_attribution_and_are_append_only`, `::test_fetch_carries_a_descriptive_user_agent` |

# P11.2 — the `audit_structural` connector

Every executable requirement P11.2 satisfies (§23.7), mapped to code and the test that fails if it
is removed (SIG-ENG-004). Requirements reconciliation *logic* exercised here is owned/tested by
P08.2 (count §29.1, sharing §29.3) — this connector produces the observations and invokes it.

## Structural aggregates only — the §18.1 per-plate bright line (SIG-INGEST-046, SIG-STORE-025/026)

| Requirement | Where | Test |
|---|---|---|
| §18.1 / SIG-STORE-025 (no per-search or per-plate row is produced anywhere; per-search rows read transiently, aggregated, dropped) | `connectors.audit_structural` (`aggregate_search_events`, `extract` consumes per-search rows), `data/audit_structural_vocab.toml` (`forbidden_output_columns`) | `tests/connectors/test_audit_structural.py::test_no_per_search_or_per_plate_row_is_produced`, `::test_aggregates_count_distinct_searches_and_carry_direction` |
| SIG-STORE-026 (the bright line is a schema property — a plate-capable row is rejected at the boundary) | `connectors.audit_structural.assert_no_per_row_output` (`PerRowLeak`); run in `normalize` | `tests/connectors/test_audit_structural.py::test_the_per_row_schema_gate_rejects_a_plate_bearing_row` |
| §11.16 / §18.4 (`UsageAggregate` shape: searching_org→source_org, month-granular period, count, scope, reason_category, coverage_period) | `connectors.audit_structural.UsageAggregate`, `period_month` | `tests/connectors/test_audit_structural.py::test_aggregates_count_distinct_searches_and_carry_direction`, `::test_redacted_and_empty_reasons_produce_distinct_aggregate_buckets` |

## The audit `Camera Count` as an independent count claim (§23.7, §29.1, SIG-RECON-026)

| Requirement | Where | Test |
|---|---|---|
| §23.7 (audit `Camera Count` lands as an independent count claim — its own `active_device_count` basis, reconciled against other counts by P08.2, never merged) | `connectors.audit_structural` (`camera_count_claim`, `camera_count_observation`, `reconcile_camera_counts`) → `reconcile.counts.reconcile_counts`; `data/audit_structural_vocab.toml` (`[camera_count]`) | `tests/connectors/test_audit_structural.py::test_camera_count_is_an_independent_active_device_count_claim`, `::test_camera_count_is_reconciled_against_other_counts_never_merged_via_p08_2`, `::test_redacted_camera_count_yields_no_fabricated_count` |

## `SharedNetworks.csv` = configured access, directional, blanks-as-negatives (SIG-ONTO-042/044, SIG-RECON-034/035/036/037)

| Requirement | Where | Test |
|---|---|---|
| SIG-ONTO-042/044 (SharedNetworks lands as configured access only, directional, blank cells as negatives; single-snapshot edges carry `valid_from_kind='unknown'`) | `connectors.audit_structural` (`sharing_observations`, `reconcile_audit_sharing`, `_sharing_edge_rows`); `data/audit_structural_vocab.toml` (`[sharing]`) | `tests/connectors/test_audit_structural.py::test_sharednetworks_edges_are_configured_access_directional_single_snapshot`, `::test_blank_sharing_cells_are_negatives_not_unknown_edges`, `::test_connector_streams_only_deterministic_edges_for_sharing` |
| SIG-RECON-034/035/036/037 (exercised here; owned/tested in P08.2) — asymmetry is a finding via the §29.3 reconciler run over the whole file | `connectors.audit_structural.reconcile_audit_sharing` → `reconcile.sharing.reconcile_sharing` | `tests/connectors/test_audit_structural.py::test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler` |

## `***` redaction distinguished from empty (SIG-INGEST-046)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-046 (`***` redaction is a distinct recorded state, never conflated with empty/missing) | `connectors.audit_structural` (`classify_cell`, `is_redacted`, `reason_category`, `redacted_cell_rows`); `data/audit_structural_vocab.toml` (`redaction_sentinel`) | `tests/connectors/test_audit_structural.py::test_classify_cell_distinguishes_redacted_from_empty_and_present`, `::test_reason_category_keeps_redacted_distinct_from_unspecified`, `::test_redacted_and_empty_reasons_produce_distinct_aggregate_buckets` |

## The four audit source types kept non-interchangeable (§23.7)

| Requirement | Where | Test |
|---|---|---|
| §23.7 (the four audit source types are recorded on every aggregate and not silently unioned) | `connectors.audit_structural` (`audit_source_types`, `assert_audit_source_type`, `UnknownAuditSourceType`; `audit_source_type` stamped on every row); `data/audit_structural_vocab.toml` (`audit_source_types`) | `tests/connectors/test_audit_structural.py::test_the_four_audit_source_types_are_the_closed_set`, `::test_every_aggregate_records_its_source_type_and_they_are_not_unioned` |
| §23.7 writes: event-log lifecycle transitions (dated, tagged by source type; §29.4 preference owned by P08.2) | `connectors.audit_structural.lifecycle_transition_rows`; `data/audit_structural_vocab.toml` (`[event_log]`) | `tests/connectors/test_audit_structural.py::test_event_log_lands_dated_lifecycle_transitions_tagged_by_source_type` |
| §23.7 "Duplicate handling" (overlapping exports deduplicated by `(source_org, searching_org, window)` before aggregation, overlap recorded); "Source-agency provenance" (every aggregate carries its export + requesting agency) | `connectors.audit_structural.deduplicate_events`; `UsageAggregate` (`requesting_agency`, `audit_export_id`) | `tests/connectors/test_audit_structural.py::test_overlapping_exports_are_deduplicated_by_window_block`, `::test_source_agency_provenance_travels_on_every_aggregate` |

## The agency-audit source, allowlist, canary, registration, reproducibility (SIG-INGEST-046a/021/003, SIG-PARSE-007/008)

| Requirement | Where | Test |
|---|---|---|
| SIG-INGEST-046a (agency primary records, not the derived HIBF export) | `connectors/data/sources.toml` (`agency_audit_export`, CC0-1.0 public record) | `tests/unit/test_source_registry.py` (registry invariants) |
| §23.7 predicate allowlist enforced as a schema gate | `connectors.audit_structural` (`predicate_allowlist`, `assert_predicate_allowed`, `PredicateNotAllowed`) | `tests/connectors/test_audit_structural.py::test_predicate_allowlist_is_enforced` |
| SIG-INGEST-021 (self-registers on the plug-in seam; visible in the CLI) | `connectors.audit_structural.AuditStructuralConnector` (`@register`); imported by `connectors.__init__` | `tests/connectors/test_audit_structural.py::test_audit_structural_connector_is_registered` |
| SIG-INGEST-003 (post-capture stages pure; reproducible claim set — only deterministic rows in the stream) | `connectors.audit_structural` (`extract`/`normalize` pure; sharing findings kept out of L1) | `tests/connectors/test_audit_structural.py::test_claim_set_is_reproducible_across_runs` |
| SIG-PARSE-007/008 (committed fixtures + a canary on structural drift) | `tests/connectors/fixtures/audit_structural/*.csv`; `connectors.audit_structural.canary_findings`, `parse_csv` | `tests/connectors/test_audit_structural.py::test_canary_passes_on_the_committed_fixtures`, `::test_canary_flags_structural_drift` |
| §23.7 (raw values preserved; source + append-only, P1–P3) | `connectors.audit_structural._stamp`, `UsageAggregate.to_row` (`raw_value`) | `tests/connectors/test_audit_structural.py::test_rows_carry_source_and_are_append_only`, `::test_fetch_carries_a_descriptive_user_agent` |
