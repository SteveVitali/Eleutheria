#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.16 (SOURCES.15) — the GL-GATE-07 rights-batch generator.

Reads the reviewed catalog-sweep artifact
(``docs/build/reports/catalog_sweep_2026-09-18_reviewed.json``), classifies each
of the 257 gated camera-registry rows + ``camreg_stalbert_ab``, and emits every
artifact the ticket requires:

* a disposition plan (``--plan`` prints it; ``--plan-json`` writes the committed
  per-row record under ``docs/build/reports/``);
* ``sources.toml`` — flips for the gated sources the artifact maps onto (10
  ``camreg_*`` + 4 ``dot_511_*`` whose registered target endpoint IS an artifact
  row) + ``camreg_stalbert_ab``, plus new registry rows for the remaining
  publishers (never flipped for the non-conforming rows — see NON_TARGET);
* ``camera_registry_targets.toml`` — ``[[targets]]`` rows for conforming rows,
  ``[[enumerated]]`` rows for covered-by-existing endpoints and non-targets
  (honest negative outcomes, never force-fit, never silently dropped);
* ``live_targets.toml`` — ``dot_511_targets`` rows for new sources;
* ``runner.py`` — CONNECTOR_FOR_SOURCE entries (a generated P26.16 block);
* ``api_allowlist.toml`` — the new ArcGIS service hosts + portal hosts;
* ``dot_511_vocab.toml`` — the observed id-field aliases the new layers need
  (OID/FID2/OBJECTID_12/F__OBJECTID/CEVI_OID/ObjectId2/REC_ID) —
  vocab_version bump;
* ``licenses.toml`` — the two GL-GATE-07 licence rows + their compartments;
* ``ops/cadence.toml`` — ``[[batches]]`` rows (the sig-ingest-camreg-batch-*
  jobs + monthly schedulers; each batch member still writes its own run row);
* ``docs/build/reports/rights/GL-GATE-07-batch.md`` — the batch rights packet —
  and one annex per source under ``docs/build/reports/rights/annex/p2616/``.

Classification data is reviewed constants, not inference: NON_TARGET names the
rows whose content is not a public camera *registry* (person-level records —
ALPR reads, registrant PII, patrol logs, citizen reports — are outside
GL-GATE-07's camera-registry scope and outside Part VIII entirely; ecological
"surveillance" / pipe-CCTV / geocoder / program-directory rows are not
surveillance-camera registries). COVERED names rows whose endpoint is already a
registered target (dedupe — the covering source is named). WIRE names each
remaining row's source + target ids; SOURCES carries each new source's reviewed
jurisdiction (``us.state_abbr`` / ``iso.3166_2`` / ``iso.3166_1_alpha2`` /
``sig.unresolved``) — the licence basis follows the gate rule: US →
``LicenseRef-PublicRecord-FactualCompilation``, anything else (unresolved
included — never assert a public-record basis we can't establish) →
``LicenseRef-OperatorAccepted-DBRight``, and OSM-derived mirror rows →
``ODbL-1.0`` (their content IS the ODbL corpus).

Run ``--plan`` first; ``--apply`` writes the repo changes idempotently.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[3]
ARTIFACT = REPO / "docs/build/reports/catalog_sweep_2026-09-18_reviewed.json"
SOURCES_TOML = REPO / "connectors/src/connectors/data/sources.toml"
TARGETS_TOML = REPO / "connectors/src/connectors/data/camera_registry_targets.toml"
LIVE_TARGETS_TOML = REPO / "connectors/src/connectors/data/live_targets.toml"
API_ALLOWLIST_TOML = REPO / "connectors/src/connectors/data/api_allowlist.toml"
VOCAB_TOML = REPO / "connectors/src/connectors/data/dot_511_vocab.toml"
LICENSES_TOML = REPO / "policy/src/policy/data/licenses.toml"
CADENCE_TOML = REPO / "ops/cadence.toml"
RUNNER_PY = REPO / "connectors/src/connectors/runner.py"
RIGHTS_DIR = REPO / "docs/build/reports/rights"
ANNEX_DIR = RIGHTS_DIR / "annex/p2616"
PLAN_JSON = REPO / "docs/build/reports/p2616_dispositions.json"

REVIEW_DATE = "2026-09-18"
REVIEWER = "maintainer (delegated)"
GATE = "GL-GATE-07"
LIC_US = "LicenseRef-PublicRecord-FactualCompilation"
LIC_NONUS = "LicenseRef-OperatorAccepted-DBRight"
LIC_ODBL = "ODbL-1.0"

# ---------------------------------------------------------------------------
# Reviewed non-target set — NON_TARGET key → (status, reason). These rows
# matched the sweep's camera_registry *shape* but their observed fields show
# content that is NOT a public camera registry. GL-GATE-07 approves
# camera-registry rows; person-level records are outside that approval (and
# Part VIII is absolute) — the row is dispositioned and enumerated, never
# flipped and never wired to a live target.
# ---------------------------------------------------------------------------

NON_TARGET: dict[str, tuple[str, str]] = {
    # --- person-level / per-record content (Part VIII — never ingested) ------
    "horizon_city_axon": (
        "excluded_content",
        "layer fields are ALPR *reads* (read_record_id, owner_firstname/"
        "owner_lastname, badge_id, vehicle_name, timestamp, hotlist_name/"
        "offense_category, review_status, vehicle_attributes) — per-person/"
        "per-vehicle records, not a camera registry; outside GL-GATE-07 scope "
        "and inside Part VIII's absolute prohibition",
    ),
    "camera_registration_form": (
        "excluded_content",
        "registrant records (primary/alt contact names, home/cell phone, "
        "email, business) — person-level registration data, not a camera "
        "registry",
    ),
    "community_surveillance_program": (
        "excluded_content",
        "camera-program registrants (first_name/last_name/address/phone/"
        "email/submitter) — person-level registration data",
    ),
    "wilmington_cameras": (
        "excluded_content",
        "install records (USER_First_Name/Last_Name/Phone_Number/Address/"
        "Serial_Number/Installation_Date) — person-level data",
    ),
    "arlo_residential": (
        "excluded_content",
        "residential Arlo install appointments (USER_Street_Address/"
        "USER_Scheduled_Appointment_Date/USER_Camera_Serial_Number) — "
        "household-level records, not a public camera registry",
    ),
    "mobile_surveillance": (
        "excluded_content",
        "patrol/incident log (PatrolID, OfficerID, VehicleID, IncidentID, "
        "shift timestamps) — officer/operational records, not camera "
        "locations",
    ),
    "cctv_citizen_problems": (
        "excluded_content",
        "citizen problem reports (pocfullname/pocphone/pocemail/userid/"
        "numvotes/resolution) — reporter contact data, not a camera registry",
    ),
    "surveillance_submission_form": (
        "excluded_content",
        "tick-surveillance citizen submission form (yourEmail/Address/"
        "TickSpecies/selectHabitat…) — reporter PII + ecological content; "
        "keyword-matched 'surveillance', not a camera registry",
    ),
    "traffic_cameras_map_feedback": (
        "excluded_content",
        "map feedback form (name/email_address/phone_number/"
        "preferred_contact_method) — respondent PII",
    ),
    "surveillance_results": (
        "excluded_content",
        "wildlife-disease survey results (species, symptoms, "
        "phone_number_353) — reporter contact + ecological records",
    ),
    "smart_camera_survey": (
        "excluded_content",
        "survey/participant records (participantname, university, results) — "
        "not a camera registry",
    ),
    "surveillance_operation_results": (
        "excluded_content",
        "operations log (type_of_service, pilot_on_duty, briefing, "
        "date_and_time) — staff/operational records",
    ),
    "surveillance_implementation_results": (
        "excluded_content",
        "install-survey form results (type_of_camera, project_site, "
        "total_memory_card_utilized) — project records, not a camera registry",
    ),
    # --- wrong domain — not a surveillance-camera registry -------------------
    "shearwater_surveillance": (
        "non_target_domain",
        "avian-disease surveillance reports (NumberAffected, samples, lab "
        "results, staff names) — epidemiological, not cameras",
    ),
    "wnv_2019_surveillance": (
        "non_target_domain",
        "West Nile virus mosquito-pool surveillance (WNV_Pos, pool counts) — "
        "epidemiological, not cameras",
    ),
    "game_camera": (
        "non_target_domain",
        "wildlife game-camera records (Number_of_Black_Bears/Deer…) — "
        "ecological monitoring, not surveillance infrastructure",
    ),
    "wildlife_camera": (
        "non_target_domain",
        "wildlife camera sites — ecological monitoring, not surveillance "
        "infrastructure",
    ),
    "camera_faunique": (
        "non_target_domain",
        "'caméra faunique' — wildlife camera traps (ecological), not "
        "surveillance infrastructure",
    ),
    "camera_trap": (
        "non_target_domain",
        "WWF wildlife camera-trap stations (Stations/Traps/baseline fields) — "
        "ecological monitoring",
    ),
    "zerwelin_camera": (
        "non_target_domain",
        "WWF camera-trap sites (Hersteller manufacturer field) — ecological "
        "monitoring",
    ),
    "barsdorf_camera": (
        "non_target_domain",
        "WWF camera-trap sites — ecological monitoring",
    ),
    "sage_points_surveillance": (
        "non_target_domain",
        "GPS waypoint/track records (ele/magvar/hdop/dgpsid) — field-survey "
        "waypoints, not a camera registry",
    ),
    "cctv_cleaning": (
        "non_target_domain",
        "sewer-CCTV cleaning log (camera_cleaned/date_and_time) — pipe-"
        "inspection operations, not surveillance cameras",
    ),
    "cctv_defects": (
        "non_target_domain",
        "pipe-defect observations (PACP_Code/StructDefect/RepairID) — sewer "
        "inspection, not surveillance cameras",
    ),
    "cctv_results": (
        "non_target_domain",
        "pipe-inspection condition records (PACP_Code/Clock_At/Grade) — sewer "
        "CCTV, not surveillance cameras",
    ),
    "cctv_data_pvd": (
        "non_target_domain",
        "Providence DPW sewer-CCTV inspections (PACP_Code/InspectionID/"
        "ImageLink) — pipe inspections, not surveillance cameras",
    ),
    "smith_drain_cctv": (
        "non_target_domain",
        "drain-CCTV observations (FaultCodeID/MpegLocation/Photo_Link) — "
        "sewer inspection, not surveillance cameras",
    ),
    "cctv_tcrsd": (
        "non_target_domain",
        "sewer-district CCTV video inspections (videoDesc/insp_date/"
        "hyperlink) — pipe inspection records, not surveillance cameras",
    ),
    "cctv_pnts_foxchapel": (
        "non_target_domain",
        "Fox Chapel Authority sewer-CCTV pipe points (PIPE segment fields) — "
        "pipe-inspection asset records, not surveillance cameras",
    ),
    "cctv_points_scott": (
        "non_target_domain",
        "Scott Township sewer-CCTV inspection points (PIPE/Defect fields) — "
        "pipe inspection, not surveillance cameras",
    ),
    "atlas_of_surveillance_fiu": (
        "non_target_domain",
        "agency-technology adoption records (AOSNUMBER/Agency/Technology/"
        "Vendor/Link_*), not camera locations — and the same dataset is "
        "already live as eff_atlas_of_surveillance (CC-BY-4.0)",
    ),
    "surveillance_technologies_ucla": (
        "non_target_domain",
        "agency-technology inventory rows (AOSNUMBER/Agency/Technology/"
        "Vendor/Links) — deployments by agency, not camera locations",
    ),
    "alpr_deployment_ucla": (
        "non_target_domain",
        "agency-level ALPR technology deployment records (UCLA "
        "research-compiled), not camera locations",
    ),
    "camera_geocoded_jp": (
        "non_target_domain",
        "geocoder output layer (Loc_name/Match_addr/USER_住所…) — geocoded "
        "addresses, not a camera registry",
    ),
    "core_compstat_partners": (
        "non_target_domain",
        "program-partner directory (Place_addr/Phone/CPTED fields) — partner "
        "organisations, not camera locations",
    ),
    "traffic_camera_analysis": (
        "non_target_domain",
        "road-condition observation records (estado_pavimento/densidade_"
        "trafego/acidente_visivel) — field observations, not a camera "
        "registry",
    ),
    "sites_surveillance_air": (
        "non_target_domain",
        "French environmental/air-quality monitoring sites (typologie/"
        "equipement/code_commune) — 'surveillance' is air monitoring, not "
        "cameras",
    ),
    "cctv_poles": (
        "non_target_domain",
        "CCTV mounting-pole asset inventory (assetnum/unitcost/Height/Width) "
        "— support assets, not camera records",
    ),
    "mdus_cctv_check": (
        "non_target_domain",
        "per-dwelling-block audit rows (UPRN/Block/Number_of_Dwellings/"
        "CCTV flag) — building survey, not a camera registry",
    ),
    "photo_points_hanks": (
        "non_target_domain",
        "'HanksPhotoPoints' field-photo points, not a camera registry",
    ),
    "static_camera_benthic": (
        "non_target_domain",
        "USFSP benthic static-camera stations (camera_id + depth + image "
        "fields) — underwater ecological monitoring, not surveillance "
        "infrastructure",
    ),
}

# (owner, title-prefix) → NON_TARGET key — the reviewed binding.
_NON_TARGET_BY_OWNER_TITLE: dict[tuple[str, str], str] = {
    ("MediaProgram_Maassive", "Horizon City Axon ALPR"): "horizon_city_axon",
    ("shouyi", "Camera Registration Form"): "camera_registration_form",
    ("bbeattie_CWB", "Community Surveillance Program"): "community_surveillance_program",
    ("helpuser", "Wilmington - Cameras"): "wilmington_cameras",
    ("helpuser", "Arlo Residential"): "arlo_residential",
    ("a.zulqarnain", "Mobile Surveillance"): "mobile_surveillance",
    ("nizam99pol", "CCTV"): "cctv_citizen_problems",
    ("ukgisca7", "Surveillance Submission Form"): "surveillance_submission_form",
    ("dave_fullerton", "Traffic Cameras Map Feedback"): "traffic_cameras_map_feedback",
    ("guy.mcgrath@ucd.ie_UCDIrelandEU", "Surveillance_results"): "surveillance_results",
    ("Pannamon", "Smart_Camera"): "smart_camera_survey",
    ("OriginTech", "Surveillance Operation"): "surveillance_operation_results",
    ("OriginTech", "Surveillance Implementation"): "surveillance_implementation_results",
    ("DPI.LLS_Field", "Shearwater_surveillance"): "shearwater_surveillance",
    ("Manitoba_Government", "WNV_2019_Surveillance"): "wnv_2019_surveillance",
    ("5e52fd52_abe5_4a7e_9d93_5c7e4756131e_wvstudentmaps", "Game Camera"): "game_camera",
    ("rb81850_USG", "Wildlife Camera"): "wildlife_camera",
    ("cimetiereonline", "Camera faunique"): "camera_faunique",
    ("Phong.DoanNN@wwf.org.vn_panda", "Camera Trap"): "camera_trap",
    ("WWF_Globil", "zerwelin_camera"): "zerwelin_camera",
    ("felipe.costa@wwf.de_panda", "barsdorf_camera"): "barsdorf_camera",
    ("M.BERNIER_ccgl", "SAGE Points surveillance"): "sage_points_surveillance",
    ("j.jelenic@unsw.edu.au", "CCTV Cleaning"): "cctv_cleaning",
    ("wbajek_LSSE", "CCTV Defects"): "cctv_defects",
    ("spicergroup", "CCTV Results"): "cctv_results",
    ("PVD_DPWGIS", "CCTV Data"): "cctv_data_pvd",
    ("icdc_Admin", "Smith_Drain_CCTV_Observations"): "smith_drain_cctv",
    ("aforrest@tcrsd.org", "CCTV"): "cctv_tcrsd",
    ("FoxChapelAC", "CCTV PNTS"): "cctv_pnts_foxchapel",
    ("scotttownship", "CCTV_Points"): "cctv_points_scott",
    ("ecrum008_FIUGIS", "Atlas of Surveillance"): "atlas_of_surveillance_fiu",
    ("sslee133@ucla.edu_gisucla", "Surveillance Technologies"): "surveillance_technologies_ucla",
    ("ivandelgado@ucla.edu_gisucla", "CA Automated License Plate Reader"): "alpr_deployment_ucla",
    ("arakawakaryu2", "camera"): "camera_geocoded_jp",
    ("jra_umich", "Surveillance: CORE/CompStat Partners"): "core_compstat_partners",
    ("alexandre.ferreira", "Traffic Camera Analysis Data"): "traffic_camera_analysis",
    ("Qualitair", "sites_surveillance"): "sites_surveillance_air",
    ("gvanmaren_3dgis", "CCTV_poles"): "cctv_poles",
    ("mark.newman1", "MDUs_CCTV_Check"): "mdus_cctv_check",
    ("gsp130blo69", "Camera Locations"): "photo_points_hanks",
    ("usfsp_gsal", "static_camera"): "static_camera_benthic",
}

# ---------------------------------------------------------------------------
# Flipped sources — gated registry rows whose registered target endpoint IS a
# reviewed artifact row (or, for camreg_stalbert_ab, named by the gate). Value
# is the GL-GATE-07 licence basis.
# ---------------------------------------------------------------------------
FLIP_SOURCES: dict[str, str] = {
    "camreg_chicago_il": LIC_US,
    "camreg_honolulu_hi": LIC_US,
    "camreg_md_opendata": LIC_US,
    "camreg_arlington_va": LIC_US,
    "camreg_seattle_wa": LIC_US,
    "camreg_lexington_ky": LIC_US,
    "camreg_calgary_ab": LIC_NONUS,
    "camreg_york_on": LIC_NONUS,
    "camreg_nzta_nz": LIC_NONUS,
    "camreg_donegal_ie": LIC_NONUS,
    "camreg_stalbert_ab": LIC_NONUS,
    "dot_511_ga": LIC_US,
    "dot_511_al": LIC_US,
    "dot_511_la": LIC_US,
    "dot_511_md": LIC_US,
}

# ---------------------------------------------------------------------------
# COVERED — artifact rows whose exact endpoint (same layer_url / same resource
# id / same arcgis item) is already a registered [[targets]] row, or which are
# a same-content republish mirror of a registered publisher's data. Recorded as
# enumerated outcomes naming the covering registration; no new target.
# ---------------------------------------------------------------------------
COVERED: dict[str, str] = {
    # --- exact endpoint matches ------------------------------------------
    "dv2f-necx": "camreg_calgary_ab:calgary_ab_intersection_cameras",
    "k7p9-kppz": "camreg_calgary_ab:calgary_ab_traffic_cameras",
    "4i42-qv3h": "camreg_chicago_il:chicago_il_speed_cameras",
    "thvf-6diy": "camreg_chicago_il:chicago_il_redlight_cameras",
    "cat5-2v98": "camreg_honolulu_hi:honolulu_hi_traffic_cameras",
    "hua3-qc8n": "camreg_md_opendata:md_opendata_traffic_cameras",
    "21d54438d8f8409d8bc6db8207cfaace": "dot_511_md:md_chart_cameras",
    "1e3fb7169cd74127b9c1707258a6e6e9": "dot_511_or:or_tripcheck_cameras",
    "893d8a697d7f418f87392fb1222f5b95": "camreg_nzta_nz:nzta_nz_traffic_cameras",
    "adf1e7bd0338404196dc0d552aa6c79b": "camreg_ottawa_on:ottawa_on_redlight_cameras",
    "ba9ab09442924a11acfb30a8053e09ae": "dot_511_or:or_tripcheck_cameras",
    "d3f7dae59eba45459bd9ba6a37f6ba56": "dot_511_ut:ut_udot_live_view_cameras",
    "d709c922c64b4c389afac3fb21d481fb": "camreg_ottawa_on:ottawa_on_ase_cameras",
    "f3879db110b84473b4e3d669157c6a39": "camreg_seattle_wa:seattle_wa_atsc_cameras",
    "f39ae8c4f2374fd5801c03035419966d": "camreg_nzta_nz:nzta_nz_traffic_cameras",
    "10415997f18b4aa09a9b5076a801f93d": "camreg_arlington_va:arlington_va_traffic_cameras",
    "9bc68bf40be84180bfc36a307fe7b0a7": "dot_511_ga:ga_gdot_511_cameras",
    "d220ce31999448659626afe990ca1328": "camreg_lexington_ky:lexington_ky_traffic_cameras",
    "d54ae7413feb45de9c87cb73de38fc64": "dot_511_la:la_dotd_traffic_cameras",
    "00715d24d2bf42e5abc1fab8a08d45eb": "dot_511_ky:ky_kytc_traffic_cameras",
    "15e57299bcd740c0b107be610d99a9ab": "camreg_donegal_ie:donegal_ie_traffic_cameras",
    "38774183927d423488f9e2e707a6eca5": "dot_511_mo:mo_modot_traffic_cameras",
    "76cca231f72f446f9735b6e912c04cd0": "dot_511_al:al_aldot_traffic_cameras",
    "993d92e5270d407f8ef94cbbf7501ee0": "camreg_peel_on:peel_on_redlight_cameras",
    "a30c307c24524130845a7c6095e58997": "camreg_york_on:york_on_traffic_cameras",
    # --- same-content republish mirrors ------------------------------------
    # WSDOT republish layers (dot_511_wa already serves the WSDOT feed).
    "fabdbd0c36bd49c5b73446683f359e42": "dot_511_wa",
    "d735d0308f1942b6980bd16ae5e59592": "dot_511_wa",
    # Calgary ArcGIS republish mirrors (camreg_calgary_ab serves the Socrata
    # datasets — flipped this batch).
    "62dff351746849809c3cf1a5ef264787": "camreg_calgary_ab",
    "5eaf2647182c4d4ba948a2098908e52a": "camreg_calgary_ab",
    "cfcbae84fbdf4c2c99d681114b47358e": "camreg_calgary_ab",
    "52d1670493e146bf8f417ed632bba14c": "camreg_calgary_ab",
    # DC MPD CCTV schema mirror (camreg_washington_dc serves the DCGIS layer).
    "c81a35ca38c84ae59976451fa12eb76f": "camreg_washington_dc",
    # Austin legacy ATD ArcGIS layer — superseded by the Socrata dataset.
    "52f2b5e51b9a4b5e918b0be5646f27b2": "camreg_austin_tx",
    # mike.kissane is the identical Leon County layer_url as the cakee row.
    "e90b2e0a7e2047aeb8ecb6d1ba87bdda": "camreg_leon_fl",
}

# ---------------------------------------------------------------------------
# New sources. key → (name, agency, state, scheme, licence). `licence` is
# derived by the gate rule (us.state_abbr → LIC_US; ODBL_SOURCES → ODbL-1.0;
# everything else → LIC_NONUS) — the column is asserted, not trusted.
# ---------------------------------------------------------------------------
# source_id → (name, agency, state, scheme)
SOURCES: dict[str, tuple[str, str, str, str]] = {
    # --- US municipal / county / state (us.state_abbr → public-record basis)
    "camreg_achd_id": (
        "Ada County Highway District traffic cameras (ArcGIS registry)",
        "Ada County Highway District, Idaho",
        "ID", "us.state_abbr",
    ),
    "camreg_chattanooga_tn": (
        "Chattanooga public-safety cameras (CHATTGIS ArcGIS registry)",
        "Chattanooga-area GIS publisher (CHATTGIS)",
        "TN", "us.state_abbr",
    ),
    "camreg_dc_dot_dc": (
        "Washington DC traffic-camera ArcGIS republish layers",
        "District of Columbia (DDOT camera registries, republished layers)",
        "DC", "us.state_abbr",
    ),
    "camreg_caloes_ca": (
        "CalOES California webcams (ArcGIS registry)",
        "California Governor's Office of Emergency Services",
        "CA", "us.state_abbr",
    ),
    "camreg_carver_mn": (
        "Carver County traffic cameras (ArcGIS registry)",
        "Carver County, Minnesota",
        "MN", "us.state_abbr",
    ),
    "camreg_raleigh_nc": (
        "Raleigh traffic cameras (ArcGIS registry)",
        "City of Raleigh, North Carolina",
        "NC", "us.state_abbr",
    ),
    "camreg_nashville_tn": (
        "Nashville license-plate-reader camera locations (ArcGIS registry)",
        "Metropolitan Government of Nashville and Davidson County",
        "TN", "us.state_abbr",
    ),
    "camreg_dubuque_ia": (
        "Dubuque public camera locations (ArcGIS registry)",
        "City of Dubuque, Iowa",
        "IA", "us.state_abbr",
    ),
    "camreg_ebrgis_la": (
        "East Baton Rouge traffic cameras (EBRGIS ArcGIS registry)",
        "City of Baton Rouge / East Baton Rouge Parish",
        "LA", "us.state_abbr",
    ),
    "camreg_friendswood_tx": (
        "Friendswood Flock Safety ALPR camera locations (ArcGIS registry)",
        "City of Friendswood, Texas",
        "TX", "us.state_abbr",
    ),
    "camreg_mctx_tx": (
        "Montgomery County TX live cameras (ArcGIS registry)",
        "Montgomery County, Texas",
        "TX", "us.state_abbr",
    ),
    "camreg_keizer_or": (
        "Keizer traffic and graffiti cameras (ArcGIS registry)",
        "City of Keizer, Oregon",
        "OR", "us.state_abbr",
    ),
    "camreg_gmh_emc_ga": (
        "Georgia EMC CCTV cameras (ArcGIS registry)",
        "Georgia EMC (GMH_GA_emc publisher)",
        "GA", "us.state_abbr",
    ),
    "camreg_kirkland_wa": (
        "Kirkland traffic cameras (ArcGIS registry)",
        "City of Kirkland, Washington",
        "WA", "us.state_abbr",
    ),
    "camreg_redmond_wa": (
        "Redmond traffic cameras (ArcGIS registry)",
        "City of Redmond, Washington",
        "WA", "us.state_abbr",
    ),
    "camreg_lojic_ky": (
        "Jefferson County KY traffic web cameras (LOJIC/KYTC ArcGIS registry)",
        "LOJIC — Louisville/Jefferson County Information Consortium",
        "KY", "us.state_abbr",
    ),
    "camreg_azdot_az": (
        "Arizona DOT CCTV cameras (ArcGIS registry)",
        "Arizona Department of Transportation (ADOT publisher account)",
        "AZ", "us.state_abbr",
    ),
    "camreg_gainesville_fl": (
        "Gainesville traffic cameras (ArcGIS registry)",
        "City of Gainesville, Florida",
        "FL", "us.state_abbr",
    ),
    "camreg_denver_co": (
        "Denver automated license-plate-reader camera locations (ArcGIS registry)",
        "City and County of Denver",
        "CO", "us.state_abbr",
    ),
    "camreg_penndot_pa": (
        "PennDOT CCTV cameras (ArcGIS registry)",
        "Pennsylvania Department of Transportation (publisher account)",
        "PA", "us.state_abbr",
    ),
    "camreg_mndot_mn": (
        "MnDOT traffic cameras (ArcGIS republish layer)",
        "Minnesota Department of Transportation (republished layer)",
        "MN", "us.state_abbr",
    ),
    "camreg_kcmo_mo": (
        "Kansas City traffic camera locations (ArcGIS registry)",
        "Kansas City, Missouri",
        "MO", "us.state_abbr",
    ),
    "camreg_lawrence_ks": (
        "Lawrence KS traffic cameras (ArcGIS registry)",
        "City of Lawrence, Kansas",
        "KS", "us.state_abbr",
    ),
    "camreg_nola_safety_la": (
        "New Orleans traffic safety cameras (ArcGIS registry)",
        "City of New Orleans",
        "LA", "us.state_abbr",
    ),
    "camreg_sarasota_fl": (
        "Sarasota County traffic cameras (Cartegraph ArcGIS registry)",
        "Sarasota County, Florida",
        "FL", "us.state_abbr",
    ),
    "camreg_txdot_rep_tx": (
        "Texas DOT traffic cameras (ArcGIS republish layer)",
        "Texas Department of Transportation (republished layer)",
        "TX", "us.state_abbr",
    ),
    "camreg_fl511_fl": (
        "FL511/FDOT traffic cameras (ArcGIS republish layers)",
        "Florida Department of Transportation (republished layers)",
        "FL", "us.state_abbr",
    ),
    "camreg_salisbury_nc": (
        "Salisbury NC traffic cameras (ArcGIS registry)",
        "City of Salisbury, North Carolina",
        "NC", "us.state_abbr",
    ),
    "camreg_nyc_weltia_ny": (
        "New York City traffic cameras (ArcGIS republish layer)",
        "New York City (republished layer)",
        "NY", "us.state_abbr",
    ),
    "camreg_nyc_jgrayson_ny": (
        "NYCDOT traffic cameras (ArcGIS republish layer)",
        "New York City Department of Transportation (republished layer)",
        "NY", "us.state_abbr",
    ),
    "camreg_leon_fl": (
        "Leon County traffic cameras (COT ArcGIS registry)",
        "Leon County / City of Tallahassee (cotinter.leoncountyfl.gov)",
        "FL", "us.state_abbr",
    ),
    "camreg_massdot_ma": (
        "MassDOT CCTV cameras (ArcGIS registry)",
        "Massachusetts Department of Transportation",
        "MA", "us.state_abbr",
    ),
    "camreg_umbc_md": (
        "Maryland camera locations (UMBC ArcGIS registry)",
        "University of Maryland, Baltimore County (republished state layer)",
        "MD", "us.state_abbr",
    ),
    "camreg_uofmd_md": (
        "Maryland CCTV camera layer (UofMD ArcGIS registry)",
        "University of Maryland (republished layer)",
        "MD", "us.state_abbr",
    ),
    "camreg_baltimore_atves_md": (
        "Baltimore ATVES speed/red-light cameras (ArcGIS registry)",
        "City of Baltimore (baltimore_city ArcGIS org)",
        "MD", "us.state_abbr",
    ),
    "camreg_brea_ca": (
        "Brea PD camera locations and inventory (ArcGIS registry)",
        "City of Brea, California",
        "CA", "us.state_abbr",
    ),
    "camreg_palmdesert_ca": (
        "Palm Desert license-plate-recognition camera locations (ArcGIS registry)",
        "City of Palm Desert, California",
        "CA", "us.state_abbr",
    ),
    "camreg_trafficops_ca": (
        "California highway CCTV cameras (TrafficOps.GIS ArcGIS registry)",
        "California traffic-operations publisher (Postmile schema)",
        "CA", "us.state_abbr",
    ),
    "camreg_portland_or": (
        "Portland ITS cameras (portlandmaps ArcGIS registry)",
        "City of Portland, Oregon",
        "OR", "us.state_abbr",
    ),
    "camreg_jcfd3_or": (
        "Jackson County OR RoxyAnn camera (ArcGIS registry)",
        "Jackson County Fire District 3, Oregon",
        "OR", "us.state_abbr",
    ),
    "camreg_bettendorf_ia": (
        "Bettendorf traffic control / stop-light cameras (ArcGIS registry)",
        "City of Bettendorf, Iowa",
        "IA", "us.state_abbr",
    ),
    "camreg_manhattan_ks": (
        "Manhattan KS traffic cameras (ArcGIS registry)",
        "City of Manhattan, Kansas",
        "KS", "us.state_abbr",
    ),
    "camreg_tulane_la": (
        "New Orleans CCTV cameras (Tulane ArcGIS registry)",
        "Tulane University (republished municipal layer)",
        "LA", "us.state_abbr",
    ),
    "camreg_trpa_us": (
        "Lake Tahoe SMART traffic cameras (TRPA ArcGIS registry)",
        "Tahoe Regional Planning Agency (bi-state compact)",
        "US", "iso.3166_1_alpha2",
    ),
    "camreg_stanford_us": (
        "US-nationwide surveillance-tower / ALPR-checkpoint research layers (Stanford)",
        "Stanford University research-compiled camera locations",
        "US", "iso.3166_1_alpha2",
    ),
    "camreg_jmh_us": (
        "MPD Flock camera locations (ArcGIS registry)",
        "US municipal police department (jmh_com publisher)",
        "US", "iso.3166_1_alpha2",
    ),
    "camreg_pgcounty_md": (
        "Prince George's County speed/red-light cameras (Socrata registry)",
        "Prince George's County, Maryland (PGPD)",
        "MD", "us.state_abbr",
    ),
    # --- Canada (iso.3166_2 → operator-accepted DB-right basis) --------------
    "camreg_vancouver_bc": (
        "Vancouver web cameras (ArcGIS registry)",
        "City of Vancouver, British Columbia",
        "CA-BC", "iso.3166_2",
    ),
    "camreg_surrey_bc": (
        "Surrey traffic cameras (ArcGIS registry)",
        "City of Surrey, British Columbia",
        "CA-BC", "iso.3166_2",
    ),
    "camreg_caledon_on": (
        "Caledon CCTV locations (ArcGIS registry)",
        "Town of Caledon, Ontario",
        "CA-ON", "iso.3166_2",
    ),
    "camreg_toronto_on": (
        "Toronto camera locations (ArcGIS republish layer)",
        "City of Toronto (republished layer)",
        "CA-ON", "iso.3166_2",
    ),
    "camreg_univmb_mb": (
        "Winnipeg-area surveillance cameras (UnivMB ArcGIS registry)",
        "University of Manitoba (republished municipal layers)",
        "CA-MB", "iso.3166_2",
    ),
    # --- United Kingdom (iso.3166_2 / iso.3166_1_alpha2 → DB-right basis) ----
    "camreg_camberwell_au": (
        "Camberwell-area CCTV cameras (ArcGIS registry)",
        "Camberwell Grammar School GIS org (community-published layer)",
        "AU-VIC", "iso.3166_2",
    ),
    "camreg_eastdun_gb": (
        "East Dunbartonshire CCTV cameras (ArcGIS registry)",
        "East Dunbartonshire Council",
        "GB-SCT", "iso.3166_2",
    ),
    "camreg_durham_gb": (
        "Durham County traffic web cameras (ArcGIS registry)",
        "Durham County Council",
        "GB-ENG", "iso.3166_2",
    ),
    "camreg_essex_gb": (
        "Essex safety cameras public view (ArcGIS registry)",
        "Essex County Council / Essex Safety Camera Partnership",
        "GB-ENG", "iso.3166_2",
    ),
    "camreg_bedford_gb": (
        "Bedford external CCTV cameras (ArcGIS registry)",
        "Bedford Borough Council",
        "GB-ENG", "iso.3166_2",
    ),
    "camreg_plymouth_gb": (
        "Plymouth traffic cameras (ArcGIS registry)",
        "Plymouth City Council",
        "GB-ENG", "iso.3166_2",
    ),
    "camreg_dover_gb": (
        "Dover CCTV cameras (ArcGIS registry)",
        "Dover District Council",
        "GB-ENG", "iso.3166_2",
    ),
    "camreg_guildford_gb": (
        "Guildford CCTV cameras (ArcGIS registry)",
        "Guildford (rgsguildford publisher)",
        "GB-ENG", "iso.3166_2",
    ),
    "camreg_gedling_gb": (
        "Gedling CCTV locations (ArcGIS registry)",
        "Gedling Borough Council",
        "GB-ENG", "iso.3166_2",
    ),
    "camreg_lisburn_gb": (
        "Lisburn & Castlereagh CCTV cameras (ArcGIS registry)",
        "Lisburn and Castlereagh City Council",
        "GB-NIR", "iso.3166_2",
    ),
    "camreg_esriukpolice_gb": (
        "UK police CCTV locations (Esri UK police ArcGIS registry)",
        "Esri UK police demonstration org (community-published layer)",
        "GB", "iso.3166_1_alpha2",
    ),
    # --- Other identified jurisdictions (iso.3166_1_alpha2) ------------------
    "camreg_wellington_nz": (
        "Wellington City CCTV cameras (ArcGIS registry)",
        "Wellington City Council",
        "NZ", "iso.3166_1_alpha2",
    ),
    "camreg_mbrc_au": (
        "Moreton Bay CCTV cameras (ArcGIS registry)",
        "Moreton Bay Regional Council, Queensland",
        "AU-QLD", "iso.3166_2",
    ),
    "camreg_ukm_my": (
        "UKM CCTV management system (ArcGIS registry)",
        "Universiti Kebangsaan Malaysia (community-published layer)",
        "MY", "iso.3166_1_alpha2",
    ),
    "camreg_bouhan_jp": (
        "Japanese bouhan (security) camera locations (ArcGIS registry)",
        "Japanese community-published camera registry",
        "JP", "iso.3166_1_alpha2",
    ),
    "camreg_monmap_mn": (
        "Mongolia camera locations (monmap ArcGIS registry)",
        "Mongolian mapping community publisher",
        "MN", "iso.3166_1_alpha2",
    ),
    "camreg_ramallah_ps": (
        "Ramallah surveillance camera network (ArcGIS registry)",
        "Ramallah municipal camera registry (community-published layer)",
        "PS", "iso.3166_1_alpha2",
    ),
    "camreg_riyadh_sa": (
        "Riyadh camera-control registry (ArcGIS registry)",
        "Riyadh municipal camera registry (rematalriyadh publisher)",
        "SA", "iso.3166_1_alpha2",
    ),
    "camreg_bangla_bd": (
        "Bangladesh camera locations (ArcGIS registry)",
        "Bangladesh community-published camera registry",
        "BD", "iso.3166_1_alpha2",
    ),
    "camreg_gistel_be": (
        "Gistel camera locations (ArcGIS registry)",
        "Gistel municipal camera registry (m.decraemer publisher)",
        "BE", "iso.3166_1_alpha2",
    ),
    "camreg_mueller_de": (
        "German camera positions (ArcGIS registry)",
        "German community-published camera registry",
        "DE", "iso.3166_1_alpha2",
    ),
    "camreg_oosgis_nl": (
        "Dutch camera registry (OOS GIS, CEVI schema)",
        "Dutch municipal camera registry (oosgis publisher)",
        "NL", "iso.3166_1_alpha2",
    ),
    "camreg_apram_pt": (
        "Madeira CCTV cameras (APRAM ArcGIS registry)",
        "APRAM — Agência Regional para o Ambiente, Portugal",
        "PT", "iso.3166_1_alpha2",
    ),
    "camreg_polyu_hk": (
        "Hong Kong CCTV camera layers (esrichina.hk ArcGIS registry)",
        "Hong Kong PolyU/police CCTV layers (community-published)",
        "HK", "iso.3166_1_alpha2",
    ),
    "camreg_thailand_th": (
        "Thailand CCTV camera layers (ArcGIS registry)",
        "Thai municipal/community camera registries",
        "TH", "iso.3166_1_alpha2",
    ),
    "camreg_indonesia_id": (
        "Indonesia CCTV camera layers (ArcGIS registry)",
        "Indonesian community/municipal camera registries",
        "ID", "iso.3166_1_alpha2",
    ),
    # --- OSM-derived mirror rows (ODbL-1.0 — the ODbL compartment) -----------
    "camreg_osm_surveillance": (
        "OSM-derived surveillance-camera layers (DeFlock/OSM exports)",
        "OpenStreetMap contributors (republished man_made=surveillance nodes)",
        "unresolved", "sig.unresolved",
    ),
    # --- unresolved jurisdiction — operator-accepted DB-right basis ----------
    "camreg_arc_1975641302": (
        "CCTV locations registry (ArcGIS, anonymous publisher)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_sensenet": (
        "Camera view registry (SenseNet ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_freese_dm": (
        "ITS CCTV camera layer (Freese DM ArcGIS registry)",
        "ArcGIS community-published ITS camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_amber_kh": (
        "Traffic monitoring cameras (ArcGIS registry)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_colgis": (
        "Traffic cameras view (COLGIS ArcGIS registry)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_camilo_schools": (
        "CCTV locations (GIS-for-schools ArcGIS registry)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_infraestructura": (
        "CCTV proyectado registry (ArcGIS, Spanish schema)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_infocemosa": (
        "CCTV point registry (Infocemosa ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_keshan": (
        "Camera registry (KeshanMoodley ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_lpd_flock": (
        "Active Flock camera locations (LPDGIS ArcGIS registry)",
        "ArcGIS community-published ALPR camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_langan": (
        "Camera registry (Langan ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_nurnazihah": (
        "CCTV camera registries (NURNAZIHAH ArcGIS layers)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_sweeney": (
        "Replacement CCTV system camera locations (ArcGIS registry)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_wim_camera": (
        "WIM camera locations (ArcGIS registry)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_pipeline_sec": (
        "Traffic/security camera registry (ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_aikner": (
        "Traffic cameras (aikner_mrrigis ArcGIS registry)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_bargabos": (
        "CCTV camera registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_yorku": (
        "Camera locations (YorkU ArcGIS registry)",
        "York University community-published camera layer",
        "unresolved", "sig.unresolved",
    ),
    "camreg_cclemire": (
        "Public-safety cameras view (ArcGIS registry)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_whatley": (
        "Camera locations (ArcGIS registry)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_cphang": (
        "Surveillance sites (ArcGIS registry)",
        "ArcGIS community-published surveillance-site registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_cwarcgis": (
        "Camera registry (cwarcgis ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_duganmeyer": (
        "Flock ALPR locations (UA GIS ArcGIS registry)",
        "University-community-published ALPR camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_mark43": (
        "CCTV cameras (mark43 ArcGIS registry)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_esri_dash": (
        "Traffic cameras (Esri dashboard-publisher ArcGIS layer)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_firemedic": (
        "Traffic camera registry (ArcGIS layer)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_forwardalliance": (
        "CCTV camera registry (forwardalliance ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_cotgeo": (
        "Geospatial traffic camera registry (ArcGIS layer)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_helberg": (
        "Camera registry (ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_ira": (
        "CCTV camera registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_jelenic": (
        "Camera point registry (UNSW ArcGIS layer)",
        "University-community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_lenhardt": (
        "University security cameras public view (ArcGIS registry)",
        "University-community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_schellinger": (
        "BPD surveillance cameras (ArcGIS registry)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_kunying": (
        "CCTV camera registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_uchicago": (
        "Security camera registry (UChicago ArcGIS layer)",
        "University-community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_smart_sky": (
        "Camera registry (Smart Sky ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_oem_camera": (
        "Potential camera and gauge locations (OEM ArcGIS registry)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_mhebert": (
        "Public-safety / ALPR cameras view (ArcGIS registry)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_nitro": (
        "Camera feeds registry (ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_rjcoleman": (
        "Cameras registry (ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_ruslan": (
        "CCTV_S camera registry (UCP/UFR ArcGIS layer)",
        "University-community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_kosman": (
        "Traffic cameras (ArcGIS layer)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_sfoss": (
        "Cameras registry (sfoss_solutions ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_squan": (
        "Stephen camera registry (ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_tblose": (
        "Camera intersections registry (ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_olsson": (
        "CCTV camera registry (olsson ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_townofws": (
        "ASE camera locations (Town of WS ArcGIS registry)",
        "ArcGIS community-published enforcement-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_ucsd": (
        "Traffic camera registry (UCSD Online ArcGIS layers)",
        "University-community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_vidya": (
        "CCTV camera registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_yazid": (
        "CCTV phase-1 registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_yline": (
        "CCTV camera registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_zyinger": (
        "CAMERA_3 registry (ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_avctransport": (
        "Surveillance 2026 registry (avctransport ArcGIS layer)",
        "ArcGIS community-published camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_webappfme": (
        "Traffic cameras tour points (ArcGIS layer)",
        "ArcGIS community-published traffic-camera registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_cheicylia": (
        "CCTV camera registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_fifia": (
        "CCTV_ camera registry (ArcGIS layer)",
        "ArcGIS community-published CCTV registry",
        "unresolved", "sig.unresolved",
    ),
    "camreg_gvanmaren": (
        "CCTV cameras asset registry (3D-GIS ArcGIS layer)",
        "ArcGIS community-published CCTV asset registry",
        "unresolved", "sig.unresolved",
    ),
}

# Sources whose content is an OSM export (osm_id/man_made fields observed) —
# the corpus is ODbL-1.0 regardless of the gate split.
ODBL_SOURCES = {"camreg_osm_surveillance"}

# ---------------------------------------------------------------------------
# WIRE — artifact_id → (source_id, target_id). Every remaining gated row lands
# here: a conforming camera-registry row gets a registered, rights-reviewed,
# ingestion-permitted source and a connector-wired target.
# ---------------------------------------------------------------------------
WIRE: dict[str, tuple[str, str]] = {
    "a8471041aee14916bbe50401da5a9d40": ("camreg_arc_1975641302", "arc1975641302_cctv_locations"),
    "31aed70b2053498dbe4ec44dc0728801": ("camreg_camberwell_au", "camberwell_au_cctv"),
    "8614054b26e54f588f7a55094f2fe4f0": ("camreg_camberwell_au", "camberwell_au_cctv_eff"),
    "7b3c9de533e544a397882b3ac62dcb9f": ("camreg_achd_id", "achd_id_traffic_cameras"),
    "bb665114837146769fe7103082d4fb98": ("camreg_chattanooga_tn", "chattanooga_tn_safety_cameras"),
    "d330e05d63504e6c9e03c1c3664e6051": ("camreg_chattanooga_tn", "chattanooga_tn_safety_cameras_2"),
    "2244c0706b4a4ea68c02cd1711d2ddf3": ("camreg_dc_dot_dc", "dc_dot_adminmodelle_cameras"),
    "cbe1f0e312994a21ae16ad8f841caf8d": ("camreg_dc_dot_dc", "dc_dot_firefly_cameras"),
    "be2ba9cae16c4a01b6dfb0ebcfcd4199": ("camreg_dc_dot_dc", "dc_dot_dfiorent_cameras"),
    "99799a7e7e164f229cec271da18165ae": ("camreg_sensenet", "sensenet_camera_view"),
    "d6d80e7f82884caaaeea1e0eed5d595b": ("camreg_freese_dm", "freese_dm_its_cctv"),
    "a69da35b0c7f404890ba318f57d56349": ("camreg_ukm_my", "ukm_my_cctv"),
    "f9efbc77cd404122899fc9f93c1f0741": ("camreg_amber_kh", "amber_kh_trmc"),
    "1cb8e713aaf346cd86a1d59a1ae78709": ("camreg_eastdun_gb", "eastdun_gb_cctv"),
    "5b4040338d704693994d5682ab2747c5": ("camreg_caloes_ca", "caloes_ca_webcams"),
    "bbf9cb2ff4fb4cf6a2cdabdbe6e810e6": ("camreg_colgis", "colgis_traffic_cameras"),
    "a426098dc7584c98b815c985ea76a632": ("camreg_camilo_schools", "camilo_schools_cctv"),
    "9667d52f9c014ba29e576a519af6b409": ("camreg_carver_mn", "carver_mn_traffic_cameras"),
    "f4859c702ed54fd69b416ae91de3b1fd": ("camreg_vancouver_bc", "vancouver_bc_webcameras"),
    "9f4a2984d9044a8099411ebfd18cba81": ("camreg_raleigh_nc", "raleigh_nc_cameras"),
    "da60121904964a28a01ca13dbd9cb226": ("camreg_nashville_tn", "nashville_tn_lpr_cameras"),
    "90e7ab7aed3c4cf6a61ed75cd4e5e286": ("camreg_wellington_nz", "wellington_nz_cctv"),
    "f695ac83407147a7b3b0d345888c4b9d": ("camreg_wellington_nz", "wellington_nz_cctv_locations"),
    "55213f82bc5a47c2b5483c5627c4730f": ("camreg_dubuque_ia", "dubuque_ia_public_cameras"),
    "8599d93543124bafb012b007c403aaa7": ("camreg_durham_gb", "durham_gb_traffic_cameras"),
    "c686a8a6b41342b7bc4011d16e75f61c": ("camreg_ebrgis_la", "ebrgis_la_traffic_cameras"),
    "d23db5da905b43798391379c0bd2f4a2": ("camreg_essex_gb", "essex_gb_safety_cameras"),
    "248d8ce7280c4d48b3d91d1c870fc1da": ("camreg_friendswood_tx", "friendswood_tx_flock_alpr"),
    "bb2aa42539864062b55011c67510cfe2": ("camreg_mctx_tx", "mctx_tx_live_cameras"),
    "9338737e5f6b4deda9d90d120f16c32c": ("camreg_keizer_or", "keizer_or_cameras"),
    "d5e2555c03574fbe93e300c404a38813": ("camreg_gmh_emc_ga", "gmh_emc_ga_cctv"),
    "b55c7017a4ae4a3e96d204f90f93fce2": ("camreg_bedford_gb", "bedford_gb_cctv"),
    "5a0e181639a94a08bfaee91492450431": ("camreg_infraestructura", "infraestructura_cctv_proyectado"),
    "fc73440e889f4e33b0a57d7c9158a70c": ("camreg_infocemosa", "infocemosa_cctv_point"),
    "7fc8ba9051684d0aabc228038758c10b": ("camreg_kirkland_wa", "kirkland_wa_traffic_cameras"),
    "269df31cafd9463abfd46ecd24162ef6": ("camreg_txdot_rep_tx", "txdot_rep_tx_cameras"),
    "55f2d14f468c4d35b1870bf8469b2c96": ("camreg_redmond_wa", "redmond_wa_traffic_cameras"),
    "3a72754fa9004f9ca5774bb23c6f3504": ("camreg_keshan", "keshan_camera_rev3"),
    "c2201ec5ea4a4b9c8ae02f6b681f91e5": ("camreg_lojic_ky", "lojic_ky_traffic_cameras"),
    "5d2bd8ccc5f74ea7b7574f126cacd1cc": ("camreg_lpd_flock", "lpd_flock_cameras"),
    "98fa8eeae92946dbadb62b821e756522": ("camreg_langan", "langan_camera"),
    "32b4a83b129646ad985081f5ba654696": ("camreg_nurnazihah", "nurnazihah_cctv"),
    "d930ff08f1364a979016fda955d51842": ("camreg_nurnazihah", "nurnazihah_cctv_pg"),
    "de3248c897b645c6a825c6c56b42b6c5": ("camreg_sweeney", "sweeney_cctv_replacement"),
    "a0a6e71d55804d249535831ec98b4db0": ("camreg_wim_camera", "wim_camera"),
    "a817a48983f144e0943cf1d3fee15c08": ("camreg_nzta_nz", "nzta_nz_cameras_layer"),
    "bfd6920167a6491786a6a8729fa53e42": ("camreg_nzta_nz", "nzta_nz_eaglegis_cameras"),
    "1aabbfa5e68146248db058e2752641f8": ("camreg_nzta_nz", "nzta_nz_harleyp_cameras"),
    "0ebee47dfb7b4f529a8b618c88997a27": ("camreg_pipeline_sec", "pipeline_sec_cameras"),
    "d55477395f4c41ad8288d45df8c3f00e": ("camreg_plymouth_gb", "plymouth_gb_traffic_cameras"),
    "1cdab839cdaa4e789ca155a8d6323cab": ("camreg_esriukpolice_gb", "esriukpolice_gb_cctv"),
    "ec493f52acd64bc1b9e75b2dbc5fb696": ("camreg_azdot_az", "azdot_az_cctv"),
    "24da916fb36f44e9afd0bab4c527204d": ("camreg_jcfd3_or", "jcfd3_or_roxyann_camera"),
    "dda63ffcc4bf44f8b3dd5845a54e2e86": ("camreg_gainesville_fl", "gainesville_fl_traffic_cameras"),
    "94b17026e83d49d58b41fd75933166db": ("camreg_surrey_bc", "surrey_bc_traffic_cameras"),
    "541a1e1581e34e15ab63d057a869977b": ("camreg_denver_co", "denver_co_alpr_cameras"),
    "df45f0840d8640efbdfed569f0033e8c": ("camreg_monmap_mn", "monmap_mn_camera"),
    "20c6386650414867ad1fa29027164750": ("camreg_webappfme", "webappfme_traffic_cameras"),
    "9e90790daf7e4f0592da37a1bda10417": ("camreg_nyc_weltia_ny", "nyc_weltia_ny_traffic_cameras"),
    "509475945f494a37bcbeefee139a6ecc": ("camreg_aikner", "aikner_traffic_cameras"),
    "8ebed01d37c9486fae407a8e6623e8f4": ("camreg_bargabos", "bargabos_cctv_camera"),
    "10e0013f57d045cebc794610150a6dc4": ("camreg_yorku", "yorku_camera"),
    "eb7a4722e25f4fefaf49e0e2e42a40c8": ("camreg_dover_gb", "dover_gb_cctv"),
    "307dfd0020554c28959706d40ea0ba90": ("camreg_fl511_fl", "fl511_fl_akeddell_cameras"),
    "ef4667361e43428a808d4e12e55f7408": ("camreg_fl511_fl", "fl511_fl_rydl_cameras"),
    "0d71f303829e4639a08b8f1bc3f9b047": ("camreg_fl511_fl", "fl511_fl_fdot_cameras"),
    "992729c4ef72407584a2cbb52bbf1dcf": ("camreg_osm_surveillance", "osm_surveillance_cctv_london"),
    "e7cc29c2f5dc495ab6e1f0daebef0ce4": ("camreg_osm_surveillance", "osm_surveillance_alpr_nationwide"),
    "d6267b54848f483bad8c529b529611ba": ("camreg_osm_surveillance", "osm_surveillance_deflock"),
    "618fac79c077407890d52d2bf10ec538": ("camreg_osm_surveillance", "osm_surveillance_ucp_osm"),
    "62b42119ac304517b1583ee29c77f03e": ("camreg_osm_surveillance", "osm_surveillance_ucp_amini"),
    "27f49b788f074fc5a34086c7d7191959": ("camreg_osm_surveillance", "osm_surveillance_thailand"),
    "0fca25174cba4605938cac79c3331640": ("camreg_mndot_mn", "mndot_mn_traffic_cameras"),
    "077b66ab35dd48de97fedf0abbf4a03b": ("camreg_toronto_on", "toronto_on_camera"),
    "878088e6668148f587038c616099692d": ("camreg_indonesia_id", "indonesia_id_persebaran_cctv"),
    "494ab2925bc84464ab3b32ea8b972e94": ("camreg_indonesia_id", "indonesia_id_aryadigireg_cctv"),
    "0977f811c1ab494b9a1c31614fda7863": ("camreg_indonesia_id", "indonesia_id_cctv_fix"),
    "17ac8ac9282b477d8756970f920052b3": ("camreg_indonesia_id", "indonesia_id_tmc_bekasi"),
    "99884d9a56194dc793fbe9ff2502cc9b": ("camreg_indonesia_id", "indonesia_id_cctv_gunungagung"),
    "9f3167a3bc37417fb100169b60406ea4": ("camreg_indonesia_id", "indonesia_id_cctv_gudang"),
    "bb857cf90a454a5b98c043dce0b99ba4": ("camreg_indonesia_id", "indonesia_id_cctv"),
    "c6d7a160f907418caaa84c6fd3eebd48": ("camreg_indonesia_id", "indonesia_id_cctv_pelabuhan"),
    "cc134f6b2d574205870e356ce985d78a": ("camreg_indonesia_id", "indonesia_id_cctv_2"),
    "7d7654bc257f40d0aa7aebf71ae971b8": ("camreg_cheicylia", "cheicylia_cctv"),
    "d03b77e0286d4d82b76c76de32c36b27": ("camreg_fifia", "fifia_cctv"),
    "48a727929e6f4350b71be361d5002d4c": ("camreg_avctransport", "avctransport_surveillance_2026"),
    "ada7ca58962b4ab48ccd6853a893fc31": ("camreg_mueller_de", "mueller_de_camera_positionen"),
    "02625f728f714c78a5b3ad6aa06695b3": ("camreg_baltimore_atves_md", "baltimore_md_atves_speed_fixed"),
    "34506a54ef124f2c9062e707a96bd74a": ("camreg_baltimore_atves_md", "baltimore_md_atves_commercial"),
    "6c9b08a2bb6c40df94e4dec6f2e02cd8": ("camreg_baltimore_atves_md", "baltimore_md_atves_redlight"),
    "ebf52af4f690414e916190255850aaca": ("camreg_baltimore_atves_md", "baltimore_md_atves_speed_portable"),
    "3c232823551e496a95d70a9a6f9cb87f": ("camreg_umbc_md", "umbc_md_camera_locations"),
    "1562517848d94a4ba6f10bf3e2a64665": ("camreg_leon_fl", "leon_fl_traffic_cameras"),
    "aa12417a64b04fcbb07e67435c84086d": ("camreg_cclemire", "cclemire_safety_cameras"),
    "498f44acc19145b98f5f180d0451774c": ("camreg_kcmo_mo", "kcmo_mo_traffic_cameras"),
    "c83d85929ead4c01b1d684594391cf09": ("camreg_portland_or", "portland_or_its_cameras"),
    "b28ca74f76ad4b7cb31d380f7679c49f": ("camreg_whatley", "whatley_camera_locations"),
    "9cdb054f4f334d9485991625973f437a": ("dot_511_ut", "ut_udot_cctv_layer"),
    "81d052e49e5c4ac8972506a6740adb03": ("camreg_cphang", "cphang_surveillance_sites"),
    "cdf8cc99704d441fae13608702a6a74d": ("camreg_tulane_la", "tulane_la_cctv_cameras"),
    "46b1e00b2b2c494c805a0743c5e723a1": ("camreg_cwarcgis", "cwarcgis_camera"),
    "afab7c664cf14139a8384e752c083143": ("camreg_lisburn_gb", "lisburn_gb_cctv"),
    "3a3p-zwvz": ("camreg_pgcounty_md", "pgcounty_md_redlight_cameras"),
    "mnkf-cu5c": ("camreg_pgcounty_md", "pgcounty_md_speed_cameras"),
    "4z3c-43ce": ("camreg_md_opendata", "md_opendata_traffic_cameras_4z3c"),
    "e153fe4453104b11b8a5a17599bd8478": ("camreg_sarasota_fl", "sarasota_fl_traffic_cameras"),
    "1396d889c2734c57a93184470a11c7f4": ("camreg_duganmeyer", "duganmeyer_flock_alprs"),
    "350fa8a11b8b4ba8adcf8b2b3f88ea62": ("camreg_uofmd_md", "uofmd_md_cctv"),
    "a86fc3d9aa4b4f579f826055af93d1dc": ("camreg_nola_safety_la", "nola_safety_la_cameras"),
    "7b5888a0ea584bd2a0a6e7aa33d70eb8": ("camreg_mark43", "mark43_cctv"),
    "57d50a7d46b148f88bb721d8e06a3211": ("camreg_esri_dash", "esri_dash_traffic_cameras"),
    "145823e4fd4846da98599e8bf5b5980c": ("camreg_smart_sky", "smart_sky_camera"),
    "2dfd6bae23ac4ae9b3e24112a82c2277": ("camreg_gistel_be", "gistel_be_camera"),
    "409faf7a03d840aab1d13412ad42925b": ("camreg_manhattan_ks", "manhattan_ks_traffic_cameras"),
    "4ffcd943366f46649cbd58e476afb3d3": ("camreg_massdot_ma", "massdot_ma_cctv"),
    "bc2f36369f9e4137872afefcdc62735d": ("camreg_oem_camera", "oem_camera_gauge_locations"),
    "4a1feaa5dd214d0287aee6467c2da3c7": ("camreg_trpa_us", "trpa_us_smart_cameras"),
    "cbe977542c984003bbc99856219de1e5": ("camreg_trafficops_ca", "trafficops_ca_d5_cctv"),
    "22be1b5f269b441ba5f4963c4f4ac665": ("camreg_mhebert", "mhebert_safety_alpr_view"),
    "d7cbf7e7cf724a9581b15058ee6f1453": ("camreg_mbrc_au", "mbrc_au_cctv_cameras"),
    "e61f3ed7f7ab4aef9d295395621292c2": ("camreg_oosgis_nl", "oosgis_nl_camera"),
    "45f4d8efb35c442f9fdaa50273b177bf": ("camreg_nitro", "nitro_camera_feeds"),
    "6f7185fd39d34ccb95a9545f778ed43c": ("camreg_riyadh_sa", "riyadh_sa_camera_control"),
    "4e1c6cf7573948ef885ecd262d5d262b": ("camreg_guildford_gb", "guildford_gb_cctv2015"),
    "871da848d25940e890d811ee20280f79": ("camreg_rjcoleman", "rjcoleman_cameras"),
    "188b6ca940a14029a0aceb1aad25e553": ("camreg_polyu_hk", "polyu_hk_cctv"),
    "ec5a347fc84547e3aa52a9fd71f104d9": ("camreg_polyu_hk", "polyu_hk_police_cctv"),
    "e4ebd2812c4b472c8f4ef60eef4f84b9": ("camreg_apram_pt", "apram_pt_cctv"),
    "776c96fa7597423da691513f9fa05a66": ("camreg_ruslan", "ruslan_cctv_s"),
    "e19e8d52e59240e4931c5ebb723533af": ("camreg_univmb_mb", "univmb_mb_visible_cameras"),
    "f748506cb3ea4ddf829a75e5ba1335f1": ("camreg_univmb_mb", "univmb_mb_surveillance_cameras"),
    "234686a8453d406bab8f1a2ab5870ce5": ("camreg_kosman", "kosman_traffic_cameras"),
    "460290f9870d4d8692048a87221f2080": ("camreg_sfoss", "sfoss_cameras"),
    "e0c87d29871a47588b37428608bcee6b": ("camreg_thailand_th", "thailand_th_sikhio_cctv"),
    "55f462a67d464524afd16ff5e60db0f4": ("camreg_thailand_th", "thailand_th_highway_cctv"),
    "9d11508207a347d7a3c6a3372278418c": ("camreg_thailand_th", "thailand_th_gispraksa_cctv"),
    "92e8dadae27246e1b69b1f98e3906191": ("camreg_thailand_th", "thailand_th_warroom_cctv"),
    "efbcd59267ac48ba9440905d7e9fe946": ("camreg_thailand_th", "thailand_th_warroom_map_cctv"),
    "25a5a95fcbd645d0b5cfe08522209591": ("camreg_kunying", "kunying_cctv"),
    "959ee82bc06f4f79a387866e14762348": ("camreg_squan", "squan_stephen_camera"),
    "f222cfc603e7484295b8daa67b77a850": ("dot_511_ky", "ky_kytc_ext_cameras"),
    "98f20bb967e44216ba521a707236763e": ("dot_511_ga", "ga_gdot_live_cameras"),
    "119f3f9304f94b74af62f20798d3c52d": ("camreg_gvanmaren", "gvanmaren_cctv_cameras"),
    "a1b558f7ea3f4a459d24ee92654f5e6e": ("camreg_stanford_us", "stanford_us_alpr_checkpoints"),
    "e3b39af538fd42ac88fd756cccbad853": ("camreg_stanford_us", "stanford_us_surveillance_towers"),
    "9487d6220db7407fa37272a4e178298a": ("camreg_salisbury_nc", "salisbury_nc_traffic_cameras"),
    "2938f76af301480f8f153958a2aadf2f": ("camreg_uchicago", "uchicago_security_camera"),
    "825d7725a7a040f6ae6e15978bdf4bb9": ("camreg_thailand_th", "thailand_th_traffic_enforcement"),
    "f4b3928a3f504467b3827b8658544c63": ("camreg_ramallah_ps", "ramallah_ps_cameras"),
    "900bea850d98407ead83b9b0ec392a2a": ("camreg_nyc_jgrayson_ny", "nyc_jgrayson_nycdot_cameras"),
    "bbc1c81f2821455080177b684e9fa7fb": ("camreg_brea_ca", "brea_ca_camera_locations"),
    "f774c086e4c54a44ba2fe5b2c32fa6fd": ("camreg_brea_ca", "brea_ca_camera_switch_inventory"),
    "398a99c974704bebb1008c3e9daa20b9": ("camreg_brea_ca", "brea_ca_lpr_cameras"),
    "801975c11c5a4958a8352556a7d117ec": ("camreg_brea_ca", "brea_ca_lpr"),
    "a1373bba67a444878af07c52c65a5e91": ("camreg_jmh_us", "jmh_us_mpd_flock"),
    "d2dad98935c9481f97141ec963d5b582": ("camreg_palmdesert_ca", "palmdesert_ca_lpr"),
    "68589ded0afc49d494e7a209b50c0483": ("camreg_penndot_pa", "penndot_pa_cctv"),
    "38ad4086df4e4ba285792c207fc37da4": ("camreg_jelenic", "jelenic_camera_point"),
    "22d52fc22ec440a78813debcf2d1c21a": ("camreg_lenhardt", "lenhardt_security_cameras"),
    "9740206173524c11a0800d2f4aa31196": ("camreg_bouhan_jp", "bouhan_jp_camera"),
    "c56aedd0f83f4515ad641eac5e975b93": ("camreg_caledon_on", "caledon_on_cctv"),
    "fbb79a6d3cf94464a6b657a59e8cedf1": ("camreg_schellinger", "schellinger_bpd_cameras"),
    "a606368f7caa4ae2bc5de4599c27d416": ("camreg_trafficops_ca", "trafficops_ca_hs_cctv"),
    "63a8783964ca4fafa891bd38cb10deac": ("camreg_firemedic", "firemedic_traffic_camera"),
    "fe8ee8d36eb34bc6bdd49c3e447f5ffb": ("camreg_forwardalliance", "forwardalliance_cctv"),
    "634b19920c7e45c092455134055b9335": ("camreg_cotgeo", "cotgeo_traffic_camera"),
    "9fa192edd1bb4040a842f4ac908c3f00": ("camreg_gedling_gb", "gedling_gb_cctv_locations"),
    "e8c0a78e50084eb782607ce02c38501e": ("camreg_lawrence_ks", "lawrence_ks_traffic_cameras"),
    "0fa13d7ceac549e5869f30800d2b2a2c": ("camreg_helberg", "helberg_camera"),
    "4fc65d41686c4b5c84f7b466738c4ad5": ("camreg_ira", "ira_cctv"),
    "5269969b5f784cd2a2a519ccdc10149b": ("camreg_bettendorf_ia", "bettendorf_ia_traffic_cameras"),
    "bce5d44e878d4d71b5895a89ecfac9c7": ("camreg_vidya", "vidya_cctv"),
    "b01d7c8ddd614d9785435b458037bfc0": ("camreg_ucsd", "ucsd_traffic_camera_wfl"),
    "f2f32627862a4238b680464819db587b": ("camreg_ucsd", "ucsd_traffic_camera"),
    "4d528bdf8dab4956885c527b41732ae4": ("camreg_yazid", "yazid_cctv_phase1"),
    "1aa6eddd4bab4e35b2f8b3f66d9f1977": ("camreg_yline", "yline_cctv_camera"),
    "718e480ad69e466fbebf3b11c0684f9e": ("camreg_zyinger", "zyinger_camera_3"),
    "106e6ceef3c14fb6bceddeb07eb5d8a5": ("camreg_olsson", "olsson_cctv"),
    "c41e80757b5c49cbbf805492cd282166": ("camreg_townofws", "townofws_ase_cameras"),
    "650c53bb6fb24aa1aecba07847f1e2fb": ("camreg_tblose", "tblose_camera_intersections"),
    "5590d73396564488b5d627079be0ee5a": ("camreg_bangla_bd", "bangla_bd_camera"),
}

# dot_511_targets.toml — flipped dot_511_* sources keep their gated target rows
# here; the apply pass annotates licence + rights_note on them.
DOT511_TARGETS_TOML = REPO / "connectors/src/connectors/data/dot_511_targets.toml"

# Existing already-green sources that may carry NEW wired targets (republish
# layers under the agency source rather than a duplicate registry source).
# key → (agency, state, scheme) used on the generated target rows.
EXTRA_TARGET_SOURCES = {
    "dot_511_ut": ("Utah Department of Transportation", "UT", "us.state_abbr"),
    "dot_511_ky": ("Kentucky Transportation Cabinet", "KY", "us.state_abbr"),
}

# Sources that are flipped but do NOT get cadence-batch members (they keep no
# live_targets wiring of their own is FALSE — all flipped sources already carry
# live_targets rows). All flipped + new sources are scheduled via [[batches]].

# New observed id-field aliases the P26.16 layers need (vocab_version bump).
NEW_ID_ALIASES = [
    "OID", "FID2", "OBJECTID_12", "F__OBJECTID", "CEVI_OID", "ObjectId2",
    "REC_ID", "GLOBAL_ID",
]
# Network/person-sensitive field names observed on batch layers — recorded on
# the entity's `excluded_fields` (never emitted) instead of silently ignored:
# device IPs/MACs/serials, stream URIs, officer + editor names (Part VIII).
NEW_MEDIA_NAMES = [
    "ip_address", "ipaddress", "camera_ip_address_2", "cameraipaddress",
    "controlip", "switchip", "multisnsrip", "ptz_ip", "mac_address",
    "macaddress", "serialnumber", "serialnumberhousing", "serial_no",
    "encoderpath", "rtsp", "rtsp_uri", "rtmpt", "firmwareversion",
    "officer", "creator", "editor", "addedby", "modifiedby",
    "created_user", "last_edited_user", "enteredby", "lastmodifiedby",
    "lasteditor",
]
NEW_VOCAB_VERSION = "2026.09.18.3"

# --- data model --------------------------------------------------------------

@dataclass(frozen=True)
class Row:
    id: str
    title: str
    owner: str
    kind: str            # "arcgis_query" | "socrata_rows"
    url: str             # layer_url or resource endpoint
    portal: str
    permalink: str
    count: int
    oid_field: str
    attribution: str


@dataclass(frozen=True)
class Disposition:
    row: Row
    action: str          # "wired" | "covered" | "non_target"
    source_id: str = ""
    target_id: str = ""
    licence: str = ""
    note: str = ""       # covering target / non-target reason
    status: str = ""     # enumerated status for covered/non_target


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return s[:40] or "row"


def load_rows() -> list[Row]:
    doc = json.loads(ARTIFACT.read_text())
    out: list[Row] = []
    for r in doc["datasets"]:
        if r.get("shape") != "camera_registry" or r.get("spdx"):
            continue
        kind = r.get("resource_kind") or ""
        url = r.get("layer_url") or r.get("endpoint") or ""
        out.append(
            Row(
                id=r["id"],
                title=str(r.get("title") or ""),
                owner=str(r.get("owner") or r.get("portal") or ""),
                kind=kind,
                url=url,
                portal=str(r.get("portal") or ""),
                permalink=str(r.get("permalink") or ""),
                count=int(r.get("observed_count") or 0),
                oid_field=str(r.get("object_id_field") or ""),
                attribution=str(r.get("attribution") or ""),
            )
        )
    return out


def source_licence(source_id: str) -> str:
    if source_id in FLIP_SOURCES:
        return FLIP_SOURCES[source_id]
    if source_id in EXTRA_TARGET_SOURCES:
        return LIC_US
    if source_id in ODBL_SOURCES:
        return LIC_ODBL
    scheme = SOURCES[source_id][3]
    return LIC_US if scheme == "us.state_abbr" or SOURCES[source_id][2] == "US" else LIC_NONUS


def classify(rows: list[Row]) -> list[Disposition]:
    """Classify every gated row; fail loudly on anything unclassified."""
    out: list[Disposition] = []
    unclassified: list[str] = []
    for row in rows:
        rid = row.id
        if rid in WIRE:
            source_id, target_id = WIRE[rid]
            if source_id not in SOURCES and source_id not in FLIP_SOURCES and source_id not in EXTRA_TARGET_SOURCES:
                raise SystemExit(f"WIRE row {rid} names unknown source {source_id!r}")
            out.append(
                Disposition(row=row, action="wired", source_id=source_id,
                            target_id=target_id, licence=source_licence(source_id))
            )
            continue
        if rid in COVERED:
            out.append(
                Disposition(row=row, action="covered", note=COVERED[rid],
                            status="covered_by_registered")
            )
            continue
        nt = next(
            (k for (o, t), k in _NON_TARGET_BY_OWNER_TITLE.items()
             if row.owner == o and row.title.startswith(t)),
            None,
        )
        if nt:
            status, reason = NON_TARGET[nt]
            out.append(Disposition(row=row, action="non_target", note=reason,
                                   status=status, source_id=nt))
            continue
        unclassified.append(f"{rid} ({row.owner} | {row.title})")
    if unclassified:
        raise SystemExit(
            "UNCLASSIFIED gated rows — add a WIRE / COVERED / NON_TARGET "
            "binding:\n  " + "\n  ".join(unclassified)
        )
    return out


# --- artifact writers ---------------------------------------------------------

def _toml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _flip_source_block(text: str, source_id: str, licence: str, packet: str) -> str:
    """Flip one [sources.<id>] block (and its .rights subtable) in place."""
    pat = re.compile(
        rf"(\[sources\.{re.escape(source_id)}\]\n)(.*?)"
        rf"(?=\n\[(?!sources\.{re.escape(source_id)}\.rights\])|\Z)",
        re.S,
    )
    m = pat.search(text)
    if not m:
        raise SystemExit(f"flip target {source_id}: no [sources.{source_id}] block")
    head, body = m.group(1), m.group(2)
    if "ingestion_permitted = true" in body:
        return text  # already flipped — idempotent

    rights_pat = re.compile(rf"\[sources\.{re.escape(source_id)}\.rights\]\n.*", re.S)
    rm = rights_pat.search(body)
    rights_block = rm.group(0) if rm else ""
    main = body[: rm.start()] if rm else body

    main = main.replace(
        'compact_status = "not_contacted"', 'compact_status = "public_terms_only"'
    )
    old_notes = ""
    nm = re.search(r'^notes = "(.*)"$', main, re.M)
    if nm:
        old_notes = nm.group(1)
        main = main[: nm.start()] + "notes = __P2616_NOTES__" + main[nm.end():]
    new_notes = (
        f"P26.16 (SOURCES.15): FLIPPED {REVIEW_DATE} under {GATE} — operator "
        f"blanket approval of the gated catalog-sweep remainder (LEDGER GATE "
        f"DECISIONS). Basis: {licence}. Prior gate note: {old_notes}"
    )
    main = main.replace("notes = __P2616_NOTES__", "notes = " + _toml_str(new_notes))
    if "ingestion_permitted" not in main:
        main = re.sub(
            r"^(last_verified = .*)$",
            "\\1\n"
            "ingestion_permitted = true\n"
            f'rights_reviewed_by = "{REVIEWER}"\n'
            f"rights_reviewed_on = {REVIEW_DATE}\n"
            f'review_packet = "{packet}"',
            main,
            count=1,
            flags=re.M,
        )
    # Preserve an existing terms_url (e.g. St. Albert's licence page).
    old_terms = ""
    tm = re.search(r'^terms_url = "(.*)"$', rights_block, re.M)
    if tm:
        old_terms = f'terms_url = "{tm.group(1)}"\n'
    rights = (
        f"[sources.{source_id}.rights]\n"
        f'spdx = "{licence}"\n'
        f'attribution = {_toml_str("camera registry — " + GATE + " basis")}\n'
        "redistributable = true\n"
        "derivative_permitted = true\n"
        f"{old_terms}"
        f"retrieval_date = {REVIEW_DATE}\n"
    )
    new_body = main + rights
    return text[: m.start()] + head + new_body + text[m.end():]


def _source_block(source_id: str, spec: tuple[str, str, str, str], licence: str,
                  homepage: str) -> str:
    name, agency, state, scheme = spec
    note = (
        f"P26.16 (SOURCES.15) catalog-sweep rights batch. FLIPPED "
        f"{REVIEW_DATE} ({GATE}): {licence} — "
        + (
            "US state/municipal portal rows are public records; facts are not "
            "copyrightable (factual compilation)."
            if licence == LIC_US
            else "operator-accepted database-right risk on the non-US/"
            "unresolved-jurisdiction factual compilation (GL-GATE-07)."
            if licence == LIC_NONUS
            else "OSM-derived surveillance nodes — ODbL corpus (separate "
            "compartment, §42.3)."
        )
        + f" Jurisdiction scheme {scheme} ({state})."
    )
    return f"""
[sources.{source_id}]
name = {_toml_str(name)}
source_kind = "government_portal"
homepage_url = {_toml_str(homepage)}
default_tier = "R1"
custody_posture = "MIRROR"
compact_status = "public_terms_only"
robots_policy = "honor"
access_method = "rest_api (arcgis feature layer / socrata /resource query — registry rows only)"
auth_model = "none"
cadence = "monthly"
verified = true
last_verified = {REVIEW_DATE}
ingestion_permitted = true
rights_reviewed_by = "{REVIEWER}"
rights_reviewed_on = {REVIEW_DATE}
review_packet = "docs/build/reports/rights/annex/p2616/{source_id}.md"
notes = {_toml_str(note)}
[sources.{source_id}.rights]
spdx = "{licence}"
attribution = {_toml_str(agency + " camera registry")}
redistributable = true
derivative_permitted = true
terms_url = {_toml_str(homepage)}
retrieval_date = {REVIEW_DATE}
"""


def _target_block(d: Disposition) -> str:
    r = d.row
    if d.source_id in SOURCES:
        name, agency, state, scheme = SOURCES[d.source_id]
    elif d.source_id in EXTRA_TARGET_SOURCES:
        agency, state, scheme = EXTRA_TARGET_SOURCES[d.source_id]
    else:
        agency, state, scheme = r.attribution or r.owner, "", ""
    platform = "socrata" if r.kind == "socrata_rows" else "arcgis"
    oid = f'object_id_field = "{r.oid_field}"\n' if r.oid_field else ""
    note = (
        f"{platform.title()} item {r.id} {r.title!r} (owner {r.owner}, "
        f"{r.count} rows observed {REVIEW_DATE}). FLIPPED ({GATE}): "
        f"{d.licence}."
    )
    state_line = f'state = "{state}"\n' if state else ""
    scheme_line = f'jurisdiction_scheme = "{scheme}"\n' if scheme else ""
    return f"""
[[targets]]
id = "{d.target_id}"
source_id = "{d.source_id}"
kind = "{r.kind}"
platform = "{platform}"
url = "{r.url}"
layer_url = "{r.url}"
agency = {_toml_str(agency)}
{state_line}{scheme_line}observed_count = {r.count}
verified = {REVIEW_DATE}
{oid}license_spdx = "{d.licence}"
notes = {_toml_str(note)}
"""


def _enumerated_block(d: Disposition) -> str:
    r = d.row
    eid = f"p2616_{_slug(r.title)[:28]}_{r.id[:8]}"
    platform = "socrata" if r.kind == "socrata_rows" else "arcgis"
    if d.action == "covered":
        note = (
            f"GL-GATE-07 disposition: covered — this endpoint is already a "
            f"registered target ({d.note}); no duplicate wiring."
        )
    else:
        note = f"GL-GATE-07 disposition: {d.note}"
    return f"""
[[enumerated]]
id = "{eid}"
platform = "{platform}"
url = "{r.url}"
agency = {_toml_str(r.attribution or r.owner)}
status = "{d.status}"
verified = {REVIEW_DATE}
notes = {_toml_str(note)}
"""


def _rewrite_targets_license(text: str, flipped: dict[str, str]) -> str:
    """Add license_spdx + flip annotation to targets of flipped sources."""
    blocks = re.split(r"(?=\[\[targets\]\])", text)
    out = []
    for b in blocks:
        m = re.search(r'source_id = "([^"]+)"', b)
        if m and m.group(1) in flipped and b.startswith("[[targets]]"):
            lic = flipped[m.group(1)]
            if "license_spdx" not in b:
                # insert license_spdx before notes
                if re.search(r"^notes = ", b, re.M):
                    b = re.sub(r"^notes = ", f'license_spdx = "{lic}"\nnotes = ', b, count=1, flags=re.M)
                else:
                    b = b.rstrip() + f'\nlicense_spdx = "{lic}"\n'
            # annotate the notes with the flip
            def _note(mm: re.Match) -> str:
                inner = mm.group(1)
                if "GL-GATE-07" in inner:
                    return mm.group(0)
                return f'notes = "{inner} FLIPPED {REVIEW_DATE} ({GATE})."'
            b = re.sub(r'^notes = "(.*)"$', _note, b, count=1, flags=re.M)
        out.append(b)
    return "".join(out)


def _rewrite_dot511_targets(text: str) -> str:
    """Annotate flipped dot_511 sources' gated target rows."""
    flipped = {k: v for k, v in FLIP_SOURCES.items() if k.startswith("dot_511_")}
    blocks = re.split(r"(?=\[\[targets\]\])", text)
    out = []
    for b in blocks:
        m = re.search(r'source_id = "([^"]+)"', b)
        if m and m.group(1) in flipped and "[[targets]]" in b:
            lic = flipped[m.group(1)]
            b = b.replace('license_spdx = "CC0-1.0"', f'license_spdx = "{lic}"')
            def _rn(mm: re.Match) -> str:
                inner = mm.group(1)
                if "GL-GATE-07" in inner:
                    return mm.group(0)
                return f'rights_note = "{inner} FLIPPED {REVIEW_DATE} under {GATE} ({lic})."'
            b = re.sub(r'^rights_note = "(.*)"$', _rn, b, count=1, flags=re.M)
        out.append(b)
    return "".join(out)


def _new_hosts(dispositions: list[Disposition]) -> list[tuple[str, str]]:
    """(host, endpoint_prefix) pairs the new targets need allow-listed."""
    existing = API_ALLOWLIST_TOML.read_text()
    have = set(re.findall(r'host = "([^"]+)"', existing))
    pairs: dict[str, str] = {}
    for d in dispositions:
        if d.action != "wired":
            continue
        host = urlparse(d.row.url).netloc.lower()
        if not host or host in have or host in pairs:
            continue
        path = urlparse(d.row.url).path
        m = re.match(r"(.*?/rest/)", path)
        prefix = m.group(1) if m else "/"
        if host.startswith("services") and host.endswith("arcgis.com"):
            prefix = "/"
        pairs[host] = prefix
    return sorted(pairs.items())


def _batches(all_sources: list[str], per_batch_targets: dict[str, int]) -> list[list[str]]:
    """Group sources into ~26-dataset batches (whole sources, alphabetical)."""
    batches: list[list[str]] = [[]]
    count = 0
    for s in sorted(all_sources):
        if count + per_batch_targets.get(s, 1) > 26 and batches[-1]:
            batches.append([])
            count = 0
        batches[-1].append(s)
        count += per_batch_targets.get(s, 1)
    return batches


# --- plan / apply -------------------------------------------------------------

def _plan_rows(dispositions: list[Disposition]) -> dict:
    return {
        "generated": REVIEW_DATE,
        "gate": GATE,
        "reviewer": REVIEWER,
        "licence_rule": {"us": LIC_US, "non_us_or_unresolved": LIC_NONUS, "osm_derived": LIC_ODBL},
        "counts": {
            "gated_rows": len(dispositions),
            "wired": sum(1 for d in dispositions if d.action == "wired"),
            "covered": sum(1 for d in dispositions if d.action == "covered"),
            "non_target": sum(1 for d in dispositions if d.action == "non_target"),
            "flipped_sources": len(FLIP_SOURCES),
            "new_sources": len({d.source_id for d in dispositions if d.source_id in SOURCES}),
        },
        "rows": [
            {
                "id": d.row.id, "title": d.row.title, "owner": d.row.owner,
                "portal": d.row.portal, "kind": d.row.kind, "url": d.row.url,
                "observed_count": d.row.count, "disposition": d.action,
                "source_id": d.source_id, "target_id": d.target_id,
                "licence": d.licence, "status": d.status, "note": d.note,
            }
            for d in dispositions
        ],
    }


def cmd_plan(dispositions: list[Disposition]) -> None:
    p = _plan_rows(dispositions)
    c = p["counts"]
    print(f"P26.16 {GATE} rights-batch plan — {c['gated_rows']} gated rows "
          f"(+ camreg_stalbert_ab flip)")
    print(f"  wired targets : {c['wired']}")
    print(f"  covered       : {c['covered']} (endpoint already registered)")
    print(f"  non_target    : {c['non_target']} (honest negative outcomes)")
    print(f"  source flips  : {c['flipped_sources']} (incl. stalbert)")
    print(f"  new sources   : {c['new_sources']}")
    print()
    for d in dispositions:
        tag = {"wired": "WIRE ", "covered": "COVER", "non_target": "NTARG"}[d.action]
        dest = d.target_id or d.note.split(":")[0] or d.source_id
        print(f"  {tag} {d.row.id[:12]:12s} {d.row.owner[:28]:28s} "
              f"{d.row.title[:38]:38s} -> {dest}")


def apply(dispositions: list[Disposition]) -> None:
    wired = [d for d in dispositions if d.action == "wired"]
    new_source_ids = sorted({d.source_id for d in wired if d.source_id in SOURCES})

    # 1. sources.toml — flips then appended new source rows.
    text = SOURCES_TOML.read_text()
    for sid, lic in FLIP_SOURCES.items():
        text = _flip_source_block(text, sid, lic,
                                  f"docs/build/reports/rights/annex/p2616/{sid}.md")
    marker = "# --- P26.16 (SOURCES.15) — GL-GATE-07 rights batch (generated) ---"
    if marker not in text:
        home = {}
        for d in wired:
            home.setdefault(d.source_id, d.row.permalink or d.row.url)
        chunk = "\n# ---------------------------------------------------------------------------\n" + marker[2:] + "\n# " + "Generated by docs/build/tools/p2616_batch.py — do not hand-edit.\n# ---------------------------------------------------------------------------\n"
        for sid in new_source_ids:
            chunk += _source_block(sid, SOURCES[sid], source_licence(sid), home.get(sid, ""))
        text = text.rstrip() + "\n" + chunk
    SOURCES_TOML.write_text(text)

    # 2. camera_registry_targets.toml — license_spdx on flipped targets, new
    #    [[targets]] before the enumerated section, [[enumerated]] appended.
    ttext = TARGETS_TOML.read_text()
    ttext = _rewrite_targets_license(ttext, {k: v for k, v in FLIP_SOURCES.items() if k.startswith("camreg")})
    if "p2616_" not in ttext and "P26.16 (SOURCES.15)" not in ttext:
        enum_anchor = re.search(r"# -{10,}\n# Enumerated", ttext)
        new_targets = "\n# --------------------------------------------------------------------------\n# P26.16 (SOURCES.15) — GL-GATE-07 rights batch (generated).\n# --------------------------------------------------------------------------\n"
        for d in wired:
            new_targets += _target_block(d)
        enum_rows = ""
        for d in dispositions:
            if d.action != "wired":
                enum_rows += _enumerated_block(d)
        if enum_anchor:
            ttext = ttext[: enum_anchor.start()] + new_targets.lstrip("\n") + "\n" + ttext[enum_anchor.start():]
        else:
            ttext = ttext.rstrip() + "\n" + new_targets
        ttext = ttext.rstrip() + "\n" + enum_rows
    TARGETS_TOML.write_text(ttext)

    # 3. dot_511_targets.toml — annotate flipped dot_511 target rows.
    dtext = DOT511_TARGETS_TOML.read_text()
    if "GL-GATE-07" not in dtext:
        dtext = _rewrite_dot511_targets(dtext)
    DOT511_TARGETS_TOML.write_text(dtext)

    # 4. live_targets.toml — one dot_511_targets row per new source.
    ltext = LIVE_TARGETS_TOML.read_text()
    if "P26.16" not in ltext:
        ltext = ltext.rstrip() + (
            "\n\n# --- P26.16 (SOURCES.15): GL-GATE-07 rights batch -------------\n"
            "# Same \"dot_511_targets\" kind — the flipped/registered catalog-sweep\n"
            "# registries (docs/build/reports/p2616_dispositions.json).\n"
        )
        for sid in new_source_ids:
            ltext += f"\n[{sid}]\nkind = \"dot_511_targets\"\n"
    LIVE_TARGETS_TOML.write_text(ltext)

    # 5. runner.py — generated CONNECTOR_FOR_SOURCE block.
    rtext = RUNNER_PY.read_text()
    gen_begin = "    # --- P26.16 (SOURCES.15) generated block — regenerated by p2616_batch.py"
    gen_end = "    # --- end P26.16 generated block ---"
    block = gen_begin + "\n" + "".join(
        f'    "{sid}": "dot_511",\n' for sid in new_source_ids
    ) + gen_end + "\n"
    if gen_begin in rtext:
        rtext = re.sub(
            re.escape(gen_begin) + r".*?" + re.escape(gen_end) + "\n",
            block, rtext, flags=re.S,
        )
    else:
        anchor = '    "camreg_puertogaitan_co": "dot_511",\n'
        rtext = rtext.replace(anchor, anchor + block, 1)
    RUNNER_PY.write_text(rtext)

    # 6. api_allowlist.toml — new fetch hosts.
    atext = API_ALLOWLIST_TOML.read_text()
    hosts = _new_hosts(dispositions)
    if "P26.16" not in atext and hosts:
        atext = atext.rstrip() + (
            "\n\n# --- P26.16 (SOURCES.15): GL-GATE-07 rights batch -------------\n"
            "# ArcGIS `/arcgis/rest/…/query` (+ publisher-hosted variants) and the\n"
            "# Socrata `/resource/<id>.json` rows API — the same documented\n"
            "# programmatic surfaces as the earlier batches. Registry rows only.\n"
        )
        for host, prefix in hosts:
            atext += (
                "\n[[api_host]]\n"
                f'host = "{host}"\n'
                f'endpoint_prefix = "{prefix}"\n'
                'tos_basis = "Documented REST query API for the publicly published camera-registry layer (GL-GATE-07 batch)."\n'
                "rate_limit_per_min = 5\n"
                "counsel_reviewed = false\n"
            )
    API_ALLOWLIST_TOML.write_text(atext)

    # 7. dot_511_vocab.toml — id-field aliases + version bump.
    vtext = VOCAB_TOML.read_text()
    if NEW_VOCAB_VERSION not in vtext:
        vtext = vtext.replace(
            'vocab_version = "2026.09.18.2"',
            f'vocab_version = "{NEW_VOCAB_VERSION}"',
        )
        alias_line = (
            "  # P26.16: observed id fields on the GL-GATE-07 batch layers.\n  "
            + ", ".join(f'"{a}"' for a in NEW_ID_ALIASES)
            + ",\n"
        )
        vtext = vtext.replace('  ":id",\n]', alias_line + '  ":id",\n]', 1)
        # Extend media_field_names with the sensitive-field exclusions.
        mnames = ", ".join(f'"{n}"' for n in NEW_MEDIA_NAMES)
        anchor = '  "image_file", "stream_url", "cam_url",\n]'
        if anchor not in vtext:
            raise SystemExit("media_field_names anchor not found in vocab")
        vtext = vtext.replace(
            anchor,
            '  "image_file", "stream_url", "cam_url",\n'
            "  # P26.16: device network fields + officer/editor person names on\n"
            "  # batch layers — recorded on excluded_fields, never emitted.\n"
            "  " + mnames + ",\n]",
            1,
        )
        # version-history comment
        vtext = vtext.replace(
            '# 2026.09.18.2 (P26.13 / SOURCES.12)',
            f'# {NEW_VOCAB_VERSION} (P26.16 / SOURCES.15): GL-GATE-07 batch — added\n'
            '# the observed id-field aliases (OID/FID2/OBJECTID_12/F__OBJECTID/\n'
            '# CEVI_OID/ObjectId2/REC_ID/GLOBAL_ID) and media-blocklist names for\n'
            '# device IPs/MACs/serials, stream URIs, and officer/editor name\n'
            '# fields observed on batch layers (recorded excluded, never emitted).\n'
            '# Additive only.\n'
            '# 2026.09.18.2 (P26.13 / SOURCES.12)',
            1,
        )
    VOCAB_TOML.write_text(vtext)

    # 8. licenses.toml — the two GL-GATE-07 expressions + compartments.
    lic = LICENSES_TOML.read_text()
    if "LicenseRef-PublicRecord-FactualCompilation" not in lic:
        lic = lic.rstrip() + f"""

# --- P26.16 (SOURCES.15) licences ---------------------------------------------
# LicenseRef-PublicRecord-FactualCompilation — the GL-GATE-07 basis for the US
# rows of the gated catalog-sweep remainder: municipal/state camera-registry
# rows are public records, and a factual compilation's facts are not
# copyrightable (Feist). Recorded under its own expression — self-relicensable
# only — so the basis stays visible and these sources cannot silently fold
# into the permissive CC-BY graph (the LicenseRef-DerivedFacts precedent).
[licenses."LicenseRef-PublicRecord-FactualCompilation"]
kind = "data"
share_alike = false
attribution_required = true
relicensable_to = ["LicenseRef-PublicRecord-FactualCompilation"]

# LicenseRef-OperatorAccepted-DBRight — the GL-GATE-07 basis for the non-US
# (and unresolved-jurisdiction) rows: the operator explicitly accepts the sui
# generis database-right risk on EU/UK/AU factual compilations (LEDGER GATE
# DECISIONS, 2026-09-18). Self-relicensable only.
[licenses."LicenseRef-OperatorAccepted-DBRight"]
kind = "data"
share_alike = false
attribution_required = true
relicensable_to = ["LicenseRef-OperatorAccepted-DBRight"]

# --- P26.16 (SOURCES.15) compartments -----------------------------------------
[compartments.public_record]
license = "LicenseRef-PublicRecord-FactualCompilation"
description = "US public-record camera registries — facts not copyrightable (GL-GATE-07)"
source = "US state and municipal portals"

[compartments.operator_accepted]
license = "LicenseRef-OperatorAccepted-DBRight"
description = "Non-US / unresolved-jurisdiction camera registries — operator-accepted database-right basis (GL-GATE-07)"
source = "non-US municipal and community portals"
"""
    LICENSES_TOML.write_text(lic)

    # 9. ops/cadence.toml — [[batches]] rows for every flipped + new source.
    ctext = CADENCE_TOML.read_text()
    if "[[batches]]" not in ctext:
        per_source_targets: dict[str, int] = {}
        for d in wired:
            per_source_targets[d.source_id] = per_source_targets.get(d.source_id, 0) + 1
        scheduled = list(FLIP_SOURCES) + new_source_ids
        batches = _batches(scheduled, per_source_targets)
        ctext = ctext.rstrip() + (
            "\n\n# --- P26.16 (SOURCES.15): GL-GATE-07 rights-batch cadence ------\n"
            "# The flipped + newly-registered camera-registry sources run as\n"
            "# grouped sig-ingest-camreg-batch-* jobs (~26 registry endpoints\n"
            "# each); every member source still appends its own ops/runs row.\n"
            "# `scheduled-ingest --batch <id>` iterates `members` in order.\n"
        )
        for i, members in enumerate(batches, 1):
            bid = f"camreg-batch-{i:02d}"
            cron = f"{(i*7)%60} 3 {5+i} * *"
            ntargets = sum(per_source_targets.get(s, 1) for s in members)
            ctext += (
                f"\n[[batches]]\n"
                f'id = "{bid}"\n'
                f'cadence = "monthly"\n'
                f'cron = "{cron}"\n'
                f'job = "sig-ingest-{bid}"\n'
                f'scheduler = "sig-sched-{bid}"\n'
                f"members = [{', '.join(json.dumps(m) for m in members)}]\n"
                f'note = "GL-GATE-07 batch {i}/{len(batches)}: {ntargets} target(s) across {len(members)} source(s)."\n'
            )
    CADENCE_TOML.write_text(ctext)

    # 10. rights packet + annexes.
    _write_rights_packet(dispositions)

    # 11. committed per-row plan.
    PLAN_JSON.write_text(json.dumps(_plan_rows(dispositions), indent=2) + "\n")


def _write_rights_packet(dispositions: list[Disposition]) -> None:
    ANNEX_DIR.mkdir(parents=True, exist_ok=True)
    by_source: dict[str, list[Disposition]] = {}
    for d in dispositions:
        if d.action == "wired":
            by_source.setdefault(d.source_id, []).append(d)
    for sid in FLIP_SOURCES:
        by_source.setdefault(sid, [])
    for sid, ds in sorted(by_source.items()):
        lic = source_licence(sid)
        rows_md = "\n".join(
            f"| `{d.row.id}` | {d.row.title} | {d.row.url} | {d.row.count} |"
            for d in ds
        ) or "| — | (pre-registered gated targets) | — | — |"
        (ANNEX_DIR / f"{sid}.md").write_text(
            f"# Rights annex — `{sid}` (P26.16 / {GATE})\n\n"
            f"- **Licence basis:** `{lic}`\n"
            f"- **Reviewer:** {REVIEWER} — **date:** {REVIEW_DATE}\n"
            f"- **Gate:** {GATE} — operator blanket approval of the gated "
            f"catalog-sweep remainder (LEDGER GATE DECISIONS).\n\n"
            f"| artifact row | title | endpoint | rows observed |\n|---|---|---|---|\n"
            f"{rows_md}\n"
        )
    packet = RIGHTS_DIR / "GL-GATE-07-batch.md"
    counts = _plan_rows(dispositions)["counts"]
    packet.write_text(
        f"# {GATE} batch rights packet — P26.16 (SOURCES.15)\n\n"
        f"**Decision:** operator blanket approval of the 257 gated "
        f"camera-registry rows in `catalog_sweep_2026-09-18_reviewed.json` plus "
        f"`camreg_stalbert_ab` (LEDGER GATE DECISIONS, 2026-09-18).\n\n"
        f"**Licence rule:** US-jurisdiction rows → "
        f"`{LIC_US}` (facts are not copyrightable; municipal portals publish "
        f"as public records). Non-US and unresolved-jurisdiction rows → "
        f"`{LIC_NONUS}` (operator's explicit risk acceptance). OSM-derived "
        f"mirror rows → `ODbL-1.0`.\n\n"
        f"**Reviewer:** {REVIEWER} — **date:** {REVIEW_DATE}.\n\n"
        f"## Counts\n\n"
        f"- wired targets: {counts['wired']}\n"
        f"- covered (already-registered endpoint): {counts['covered']}\n"
        f"- non-target (excluded content / wrong domain): {counts['non_target']}\n"
        f"- source flips: {counts['flipped_sources']}\n"
        f"- new sources: {counts['new_sources']}\n\n"
        f"Per-source annexes live under `rights/annex/p2616/`; the machine-"
        f"readable disposition record is `docs/build/reports/"
        f"p2616_dispositions.json`. Non-target rows are enumerated negative "
        f"outcomes in `camera_registry_targets.toml` — never wired, never "
        f"dropped.\n"
    )


def main(argv: list[str]) -> int:
    rows = load_rows()
    if len(rows) != 257:
        raise SystemExit(f"expected 257 gated rows, artifact yields {len(rows)}")
    dispositions = classify(rows)
    if "--plan-json" in argv:
        PLAN_JSON.write_text(json.dumps(_plan_rows(dispositions), indent=2) + "\n")
        print(f"wrote {PLAN_JSON}")
        return 0
    if "--apply" in argv:
        apply(dispositions)
        print("applied — run `sig-connectors validate` + `make check`.")
        return 0
    cmd_plan(dispositions)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
