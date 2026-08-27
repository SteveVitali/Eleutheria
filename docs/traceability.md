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
