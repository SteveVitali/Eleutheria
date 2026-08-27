# Traceability matrix — P00.2 (executable policy and the decision record)

Every executable requirement this ticket satisfies, mapped to where it lives and
the automated test that fails if it is removed (SIG-ENG-004). This is the
ticket-scoped view; the full Appendix A matrix is maintained in
`docs/research/_meta/OUTLINE_TRACE.md`.

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
