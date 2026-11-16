# Description batch 21 — agent-drafted source descriptions awaiting operator verbatim confirmation

<!-- P36.45 (R11-K13-UX10-1; D-J3-12 / OD-07 a — 'batches of ~25 confirmed verbatim; description pending review until then'). Append-only: a status change is recorded in the confirmation log below with a `date -u` stamp; rows are never deleted. -->

## Convention

One row per agent-drafted per-source description — the **source** id,
the exact **text** as it will render, its **sha256** (UTF-8, no trailing
newline), and a **status** (`pending` · `confirmed`). Only `confirmed`
descriptions may land on the registry `description` field — the
publish-matrix lint fails a declared description whose sha256 matches
no confirmed row here. An unconfirmed source publishes
`description_pending_review`.

## Rows

| id | source | text | sha256 | status |
|---|---|---|---|---|
| D21-01 | osm_taginfo | `OSM taginfo API` — an upstream project source. | 07562b8574f77625b01ce4820760e145b240f07d5d5eec8827ea6f2857e96432 | pending |
| D21-02 | osmf_licence_guidelines | `OSMF Licence Community Guidelines` — an upstream project source. | 73fe3408749dbadd8302455ef4b03e8bf76b00c4d3b46eb89f22d684d9db6ddc | pending |
| D21-03 | panopti_ca | `resistanceisliberty/panopti.ca` — an upstream project source. | fb5840b70986acbd1b6f9717f73dd7f59f8a566435dd0d4f184dd71e43682bc2 | pending |
| D21-04 | panopticity | `PanoptiCity` — a community source. | fdde29c29b768b037fd31ad46a88ec78a74ffd39517048c1c0bf6f4b610039e7 | pending |
| D21-05 | pathways_acoustic_drone_location | `Acoustic / drone / commercial-location procurement & policy (Stage-5 pathway)` — a government portal source. | 5426d4e0003902fdaa838aa0cadde19eaa5607402da3d683f41ae0745d906d81 | pending |
| D21-06 | pathways_fr_css_forensics | `FR / cell-site-simulator / mobile-forensics procurement & policy (Stage-5 pathway)` — a government portal source. | 80eeb79c9aeaed30495a7ae6017fb11421ff3fd33a98153d4edd7c320c28cb10 | pending |
| D21-07 | pathways_rtcc_federation | `Municipal RTCC / private-camera federation disclosures (Stage-5 pathway)` — a government portal source. | addc092eab60e908d2ed050f9b704fc0ccacdbcba450db01e4bbfa8612b6b33a | pending |
| D21-08 | periscope_s2g | `Periscope S2G — eBid procurement portals` — a government portal source. | 02ab0b31ae04cb3227d0f6d70dc2ad352ab69128fca2693a33ebc44564a98d4a | pending |
| D21-09 | planetbids | `PlanetBids — public agency procurement portals` — a government portal source. | 3b602467e31c03ba769bd2d567cc9a23ecf25b36a7f6f2a5a56eec64fca3e93b | pending |
| D21-10 | policy_albuquerque_nm_apd | `APD Standard Operating Procedures (incl. SOP 1-22 Automated License Plate Reader Program)` — a government portal source published by `Albuquerque Police Department`. | c987bca36275e741c3cb482e4f893e37370d2e11e16be95bdc6700fb47dc285a | pending |
| D21-11 | policy_anaheim_ca_pd_policy_manual | `Anaheim PD Policy Manual (Lexipol)` — a government portal source published by `Anaheim Police Department (Lexipol-licensed manual)`. | 0c07d149ff16a2664248e5ba33f9a241c4da2929dea6de7fc0930b25e450e8b2 | pending |
| D21-12 | policy_bangor_me_pd | `Bangor Police Department General Order 2-59 'Unmanned Aerial Systems' (effective 2025-10-05)` — a government portal source published by `City of Bangor, ME (Police Department)`. | a4e57e61ade55197030d610cfe8039b309d097f99819f48739d018a88d42c949 | pending |
| D21-13 | policy_chicago_il_oemc_link_your | `Chicago OEMC - Link Your Cameras (Private Sector Camera Initiative)` — a government portal source published by `City of Chicago Office of Emergency Management and Communications`. | 02d149ac2a10cde9a2ebb67b5cf6c7617b5c5ca87e77fa5faa46439dd64f1804 | pending |
| D21-14 | policy_houston_tx_hpd | `Houston Police Department General Orders` — a government portal source published by `Houston Police Department`. | 830482c64ef6daa3d4278e5f4028f7fa7c47fb1d6d303b7e64c76038a6769975 | pending |
| D21-15 | policy_lafayette_in_camera_registration | `Lafayette Police Department camera registration (via CityProtect/CrimeReports)` — a government portal source published by `City of Lafayette, IN Police Department`. | de73e0b2a2e13e812881ff4b823ea74725a4b1bda4f6bf3e9d3dbe64bd188aec | pending |
| D21-16 | policy_little_rock_ar_pd | `Little Rock Police Department General Order G.O. 332 'Small Unmanned Aircraft Systems' (2025-09-17, PowerDMS public port` — a government portal source published by `City of Little Rock, AR (Police Department, via PowerDMS public portal)`. | 440c186f7b87ce1d86a5ff158d05417f067891693dd8e782d5f81f2f46ac0a44 | pending |
| D21-17 | policy_maricopa_county_az_mcso_policies | `MCSO Policies (Critical, Detention, Enforcement, General Policies and Procedures)` — a government portal source published by `Maricopa County Sheriff's Office`. | eb191f53005dd7e28e8c9a71bea7abca04e3fc17228d8cdfac1491ea9a7bd628 | pending |
| D21-18 | policy_norman_ok_alpr_policy_amendment | `Norman police ALPR policy and amendment discovery` — a government portal source published by `City of Norman / Norman Police Department`. | 397e558b33701fb7bee7914c51bd6178c58a66ddc1ff8beff1f0939bdd1d67a0 | pending |
| D21-19 | policy_ok_oklahoma_dac_uved | `Oklahoma DAC UVED program and authority chain` — a government portal source published by `Oklahoma District Attorneys Council (DAC — UVED program)`. | 08851e295b3843608f48826759cbf24ec8aa8356441dfcf277f48176f88c851b | pending |
| D21-20 | policy_onslow_nc_schools | `Onslow County Schools (NC) - 'Gaggle Safety Management' page (Cybersecurity at OCS)` — a government mandated disclosure source published by `Onslow County Schools, NC`. | bd61289677139660ce281b9604395954320d00bd3f7283f0d04fcbb11c4e5cb3 | pending |
| D21-21 | policy_orange_county_ca_sheriff | `Policy 610 Cellular Site Simulator Usage and Privacy - Orange County Sheriff-Coroner Department` — a government portal source published by `Orange County Sheriff-Coroner Department, CA`. | 1c1de70de4b711634232e9a601b34e15b608d4e5759d9d93781a0866b372b0b5 | pending |
| D21-22 | policy_pasadena_ca_pd | `Pasadena Police Department Policy 620 Cellular Site Simulator Usage and Privacy (City Council agenda 2024-01-22, item 8,` — a government portal source published by `City of Pasadena, CA (City Council agenda)`. | 07e756144dd779e55e85d1060185d4b690697e94a5d868731b6e941be38de044 | pending |
| D21-23 | policy_pflugerville_tx_isd | `Pflugerville ISD (TX) - 'Gaggle' page (Safety & Emergency Management programs)` — a government mandated disclosure source published by `Pflugerville Independent School District, TX`. | 36a4e2c0e18549af469dbd2343b604b0d4fae67aa565be245ba91d0e8f7c3b16 | pending |
| D21-24 | policy_st_cloud_mn_isd742 | `St. Cloud Area School District (ISD 742) - 'Securly' parent page: Securly Home parent portal on district-issued devices` — a government mandated disclosure source published by `St. Cloud Area School District ISD 742, MN`. | 3a4f6f511b29081a5093cc71b724e79399308717557796dd311839319d6d2e5c | pending |
| D21-25 | policy_us_private_camera_registry | `Police private-camera registry programme pages (municipal 'Camera Registry' / 'SafeCam' / 'CamerEyes' pages) - family` — a government portal source published by `Municipal police departments (many, CivicPlus/CivicEngage and other city CMS pages)`. | 46b86a5e7697cff25ca58df31b3c18ea398f58a3a4d8667cbe4e87083d4ed83e | pending |

## Confirmation log

(none yet)
