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
