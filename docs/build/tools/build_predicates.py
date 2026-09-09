from __future__ import annotations
import pathlib, yaml
GENRES=["executed_contract","invoice","portal_snapshot","council_minutes","agency_policy","osm_node_set","audit_log","news_article","vendor_default_page"]
DEFAULT={"executed_contract":"D3","invoice":"D3","portal_snapshot":"D3","council_minutes":"D3","agency_policy":"D3","osm_node_set":"D6","audit_log":"D4","news_article":"D3","vendor_default_page":"D5"}
# published §10.5 rows keyed by predicate
MATRIX={
 "contract_signed_date":{"executed_contract":"D1","invoice":"D3","portal_snapshot":"D6","council_minutes":"D2","agency_policy":"D6","osm_node_set":"D6","audit_log":"D6","news_article":"D3","vendor_default_page":"D6"},
 "contracted_device_count":{"executed_contract":"D1","invoice":"D2","portal_snapshot":"D5","council_minutes":"D2","agency_policy":"D6","osm_node_set":"D5","audit_log":"D6","news_article":"D3","vendor_default_page":"D6"},
 "active_device_count":{"executed_contract":"D5","invoice":"D4","portal_snapshot":"D1","council_minutes":"D4","agency_policy":"D6","osm_node_set":"D3","audit_log":"D4","news_article":"D3","vendor_default_page":"D6"},
 "configured_retention_days":{"executed_contract":"D4","invoice":"D6","portal_snapshot":"D1","council_minutes":"D3","agency_policy":"D2","osm_node_set":"D6","audit_log":"D6","news_article":"D3","vendor_default_page":"D5"},
 "configured_sharing_partner_set":{"executed_contract":"D6","invoice":"D6","portal_snapshot":"D1","council_minutes":"D4","agency_policy":"D3","osm_node_set":"D6","audit_log":"D4","news_article":"D3","vendor_default_page":"D6"},
}
IMM="IMMUTABLE"; GLA="GLACIAL"; SLO="SLOW"; MOD="MODERATE"; FAS="FAST"; VOL="VOLATILE"
AUTH="authoritative_source_wins"; LAT="latest_observation_wins"; MAX="max_support"; UNI="interval_union"; NEV="never_resolve"
INF="infinite"
# (slug, volatility, half_life, strategy, datatype, cardinality, definition)
P=[
 ("contract_signed_date",IMM,INF,AUTH,"edtf","single","Date a contract was signed."),
 ("contract_value",IMM,INF,AUTH,"decimal","single","Monetary value of a contract."),
 ("contracted_device_count",IMM,INF,AUTH,"integer","single","Device quantity specified by a contract."),
 ("contract_start_date",IMM,INF,AUTH,"edtf","single","Contract term start."),
 ("contract_end_date",IMM,INF,AUTH,"edtf","single","Contract term end."),
 ("statutory_citation",IMM,INF,AUTH,"string","single","Citation of a legal instrument."),
 ("funding_amount",IMM,INF,AUTH,"decimal","single","Amount of a funding instrument."),
 ("funding_program_name",IMM,INF,AUTH,"string","single","Named funding program (e.g. Byrne JAG)."),
 ("federal_award_id",IMM,INF,AUTH,"string","single","USAspending award/sub-award id."),
 ("event_epistemic_status",IMM,INF,MAX,"EpistemicStatus","single","Epistemic status of an accountability event."),
 ("organization_legal_name",GLA,"10y",MAX,"string","multi","Legal name of an organization (a claim)."),
 ("organization_jurisdiction",GLA,"10y",MAX,"uriorcurie","single","Jurisdiction an organization serves."),
 ("organization_ori",GLA,"10y",AUTH,"string","multi","FBI ORI9 identifier."),
 ("organization_type",GLA,"10y",MAX,"OrganizationType","single","Organization type."),
 ("product_vendor",GLA,"5y",MAX,"uriorcurie","single","Vendor of a product."),
 ("product_capabilities",GLA,"5y",MAX,"capability_code","multi","Marketing-level product capabilities (defeasible)."),
 ("product_status",MOD,"12mo",LAT,"ProductStatus","single","Product lifecycle status."),
 ("implements_technology",GLA,"5y",MAX,"technology_code","multi","Technology implemented by a product."),
 ("jurisdiction_parent",GLA,"10y",MAX,"uriorcurie","multi","Parent jurisdiction."),
 ("jurisdiction_boundary",SLO,"2y",LAT,"geometry_wkt","single","Jurisdiction boundary geometry (temporally versioned)."),
 ("deployment_exists",SLO,"3y",MAX,"boolean","single","Whether a deployment exists."),
 ("asset_operator",SLO,"3y",MAX,"uriorcurie","single","Operator attribution for an asset."),
 ("fixed_asset_location",SLO,"2y",LAT,"geometry_wkt","single","Location of a fixed asset."),
 ("written_policy_value",SLO,"2y",MAX,"string","single","A value stated in a written policy."),
 ("policy_enforcement_mechanism",SLO,"2y",MAX,"EnforcementMechanism","single","Policy enforcement mechanism."),
 ("offense_category_filter",SLO,"2y",LAT,"string","multi","Configured offence-category filter."),
 ("audit_case_code_required",SLO,"2y",LAT,"boolean","single","Whether a case code is required for audit."),
 ("data_system_scope",SLO,"2y",MAX,"SystemScope","single","Scope of a data system."),
 ("holds_data_collected_by",SLO,"2y",MAX,"uriorcurie","multi","Custodian-vs-collector relationship."),
 ("role_assignment",SLO,"3y",MAX,"Role","multi","Assignment of one of the fourteen roles."),
 ("candidate_location_estimate",SLO,"2y",LAT,"geometry_wkt","single","Estimated location of a candidate asset."),
 ("asset_exists_at_location",MOD,"12mo",MAX,"boolean","single","Whether an asset exists at a location."),
 ("procurement_state",MOD,"12mo",LAT,"ProcurementState","single","Deployment procurement track state."),
 ("authorization_state",MOD,"12mo",LAT,"AuthorizationState","single","Deployment authorization track state."),
 ("configured_retention_days",MOD,"9mo",LAT,"duration_iso","single","Configured retention (duration or bucket)."),
 ("vendor_default_retention",MOD,"9mo",MAX,"duration_iso","single","Vendor default retention (inference basis only)."),
 ("data_system_retention",MOD,"9mo",LAT,"duration_iso","single","Retention configured on a data system."),
 ("proceeding_posture",MOD,"12mo",LAT,"ProceedingPosture","single","Legal proceeding posture."),
 ("records_response_status",MOD,"12mo",LAT,"RecordsResponseStatus","single","Records-request response status."),
 ("candidate_promotion_status",MOD,"12mo",LAT,"PromotionStatus","single","Candidate-asset promotion status."),
 ("integration_edge_active",MOD,"12mo",LAT,"boolean","single","Whether an integration edge is active."),
 ("operational_state",FAS,"6mo",LAT,"OperationalState","single","Deployment operational track state."),
 ("active_device_count",FAS,"6mo",LAT,"integer","single","Currently active device count."),
 ("installed_device_count",FAS,"6mo",LAT,"integer","single","Installed device count."),
 ("configured_sharing_partner_set",FAS,"4mo",LAT,"uriorcurie","multi","Configured sharing partners (directional)."),
 ("configured_access_edge",FAS,"4mo",LAT,"boolean","single","Configured-access sharing edge state."),
 ("state_lookup_enabled",VOL,"2mo",LAT,"boolean","single","State lookup toggle."),
 ("national_lookup_enabled",VOL,"2mo",LAT,"boolean","single","National lookup toggle."),
 ("federal_sharing_enabled",VOL,"2mo",LAT,"boolean","single","Federal sharing toggle."),
 ("subscribed_hotlist_topic",VOL,"2mo",LAT,"string","multi","Subscribed hotlist topics."),
 ("windowed_search_count",VOL,"1mo",UNI,"integer","single","Windowed usage count (indexed, not stale — SIG-RECON-011)."),
 ("observed_use_edge",VOL,"1mo",UNI,"boolean","single","Observed-use sharing edge (windowed)."),
 ("asset_data_controller",MOD,"12mo",NEV,"uriorcurie","single","Contested data-controller assertion — recorded, not adjudicated (§12.4)."),
]
BASE="https://ontology.sig-project.org/vocab/predicate/1.0.0/"
rows=[]
for slug,vol,hl,strat,dt,card,defn in P:
    d=dict(DEFAULT); d.update(MATRIX.get(slug,{}))
    rows.append({"predicate_id":slug,"vocab_version":"1.0.0","value_datatype":dt,"cardinality":card,
                 "definition":defn,"skos_concept_iri":BASE+slug,"volatility_class":vol,"half_life":hl,
                 "resolution_strategy":strat,"directness":d})
ids=[r["predicate_id"] for r in rows]
assert len(ids)==len(set(ids)), "dup predicate"
doc={"scheme":"predicate","title":"SIG predicate registry (\u00a713.6)","version":"1.0.0",
     "artifact_genres":GENRES,"count":len(rows),"predicates":rows}
header=("# SPDX-License-Identifier: Apache-2.0\n# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation\n# carry per-artifact licences \u2014 see LICENSE and docs/2_canonical_design_spec.md \u00a742.\n#\n# The predicate registry (\u00a713.6, SIG-ONTO-066/067) \u2014 source of truth. A predicate\n# MUST NOT be added without a volatility class + half-life (\u00a728.3), a resolution\n# strategy (\u00a728.4), and its row in the directness matrix (\u00a710.5): a predicate with\n# none of those cannot be resolved, only guessed at. The directness rows carry the\n# published \u00a710.5 values for the matrix predicates and a conservative default\n# elsewhere; the full (genre \u00d7 predicate) matrix is completed in the reconcile\n# ruleset (P08), which consumes this registry.\n")
pathlib.Path("ontology/vocab/predicates.yaml").write_text(header+yaml.safe_dump(doc,sort_keys=False,allow_unicode=True,width=100))
print("predicates:",len(rows))
