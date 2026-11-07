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
| D21-01 | policy_albuquerque_nm_apd | `APD Standard Operating Procedures (incl. SOP 1-22 Automated License Plate Reader Program)` — a government portal source published by `Albuquerque Police Department`. | c987bca36275e741c3cb482e4f893e37370d2e11e16be95bdc6700fb47dc285a | pending |
| D21-02 | policy_anaheim_ca_pd_policy_manual | `Anaheim PD Policy Manual (Lexipol)` — a government portal source published by `Anaheim Police Department (Lexipol-licensed manual)`. | 0c07d149ff16a2664248e5ba33f9a241c4da2929dea6de7fc0930b25e450e8b2 | pending |
| D21-03 | policy_bangor_me_pd | `Bangor Police Department General Order 2-59 'Unmanned Aerial Systems' (effective 2025-10-05)` — a government portal source published by `City of Bangor, ME (Police Department)`. | a4e57e61ade55197030d610cfe8039b309d097f99819f48739d018a88d42c949 | pending |
| D21-04 | policy_chicago_il_oemc_link_your | `Chicago OEMC - Link Your Cameras (Private Sector Camera Initiative)` — a government portal source published by `City of Chicago Office of Emergency Management and Communications`. | 02d149ac2a10cde9a2ebb67b5cf6c7617b5c5ca87e77fa5faa46439dd64f1804 | pending |
| D21-05 | policy_houston_tx_hpd | `Houston Police Department General Orders` — a government portal source published by `Houston Police Department`. | 830482c64ef6daa3d4278e5f4028f7fa7c47fb1d6d303b7e64c76038a6769975 | pending |
| D21-06 | policy_lafayette_in_camera_registration | `Lafayette Police Department camera registration (via CityProtect/CrimeReports)` — a government portal source published by `City of Lafayette, IN Police Department`. | de73e0b2a2e13e812881ff4b823ea74725a4b1bda4f6bf3e9d3dbe64bd188aec | pending |
| D21-07 | policy_little_rock_ar_pd | `Little Rock Police Department General Order G.O. 332 'Small Unmanned Aircraft Systems' (2025-09-17, PowerDMS public port` — a government portal source published by `City of Little Rock, AR (Police Department, via PowerDMS public portal)`. | 440c186f7b87ce1d86a5ff158d05417f067891693dd8e782d5f81f2f46ac0a44 | pending |
| D21-08 | policy_maricopa_county_az_mcso_policies | `MCSO Policies (Critical, Detention, Enforcement, General Policies and Procedures)` — a government portal source published by `Maricopa County Sheriff's Office`. | eb191f53005dd7e28e8c9a71bea7abca04e3fc17228d8cdfac1491ea9a7bd628 | pending |
| D21-09 | policy_norman_ok_alpr_policy_amendment | `Norman police ALPR policy and amendment discovery` — a government portal source published by `City of Norman / Norman Police Department`. | 397e558b33701fb7bee7914c51bd6178c58a66ddc1ff8beff1f0939bdd1d67a0 | pending |
| D21-10 | policy_ok_oklahoma_dac_uved | `Oklahoma DAC UVED program and authority chain` — a government portal source published by `Oklahoma District Attorneys Council (DAC — UVED program)`. | 08851e295b3843608f48826759cbf24ec8aa8356441dfcf277f48176f88c851b | pending |
| D21-11 | policy_onslow_nc_schools | `Onslow County Schools (NC) - 'Gaggle Safety Management' page (Cybersecurity at OCS)` — a government mandated disclosure source published by `Onslow County Schools, NC`. | bd61289677139660ce281b9604395954320d00bd3f7283f0d04fcbb11c4e5cb3 | pending |
| D21-12 | policy_orange_county_ca_sheriff | `Policy 610 Cellular Site Simulator Usage and Privacy - Orange County Sheriff-Coroner Department` — a government portal source published by `Orange County Sheriff-Coroner Department, CA`. | 1c1de70de4b711634232e9a601b34e15b608d4e5759d9d93781a0866b372b0b5 | pending |
| D21-13 | policy_pasadena_ca_pd | `Pasadena Police Department Policy 620 Cellular Site Simulator Usage and Privacy (City Council agenda 2024-01-22, item 8,` — a government portal source published by `City of Pasadena, CA (City Council agenda)`. | 07e756144dd779e55e85d1060185d4b690697e94a5d868731b6e941be38de044 | pending |
| D21-14 | policy_pflugerville_tx_isd | `Pflugerville ISD (TX) - 'Gaggle' page (Safety & Emergency Management programs)` — a government mandated disclosure source published by `Pflugerville Independent School District, TX`. | 36a4e2c0e18549af469dbd2343b604b0d4fae67aa565be245ba91d0e8f7c3b16 | pending |
| D21-15 | policy_st_cloud_mn_isd742 | `St. Cloud Area School District (ISD 742) - 'Securly' parent page: Securly Home parent portal on district-issued devices` — a government mandated disclosure source published by `St. Cloud Area School District ISD 742, MN`. | 3a4f6f511b29081a5093cc71b724e79399308717557796dd311839319d6d2e5c | pending |
| D21-16 | policy_us_private_camera_registry | `Police private-camera registry programme pages (municipal 'Camera Registry' / 'SafeCam' / 'CamerEyes' pages) - family` — a government portal source published by `Municipal police departments (many, CivicPlus/CivicEngage and other city CMS pages)`. | 46b86a5e7697cff25ca58df31b3c18ea398f58a3a4d8667cbe4e87083d4ed83e | pending |
| D21-17 | policy_whitesboro_ny_csd | `Whitesboro Central School District (NY) - 'Lightspeed Alert' page (Information and Instructional Technology)` — a government mandated disclosure source published by `Whitesboro Central School District, NY`. | 57eeb3340ddb881bd64e9181c3c8cab039af5653d1276cddc0eac3539f5cd296 | pending |
| D21-18 | policy_zionsville_in_camera_registry | `Zionsville Police Department Camera Registry (Polaris cameraregistry.net)` — a government portal source published by `Town of Zionsville, IN Police Department`. | 8db57334c5752795475b0ef46111ea0311a2d3bfd065b3b4353e9dfdcf49cf06 | pending |
| D21-19 | powerdms_public_portals | `PowerDMS public policy portals` — a records channel source. | 5f518f500fdf15ab3c412573180909de1551ec93bd67a4cf493a16910d306164 | pending |
| D21-20 | primegov | `PrimeGov` — a government portal source. | d95175202b778254f301d836d9d802881d5301242e633356e904071cb4568212 | pending |
| D21-21 | private_eyes | `mcclatchy-southeast/private_eyes` — a news publisher source. | d2f0ca7e732eab3371b8ffd428f8b412c47d8fe418454d62ee955af2826d8a64 | pending |
| D21-22 | procportal_austin_tx | `City of Austin — Socrata 'Contracts' dataset` — a government portal source. | 40796100c1aaf3a566b0ff60141e272bd3fd7b590860b40aaefc6f3e7e7b172b | pending |
| D21-23 | procportal_chicago_il | `City of Chicago — Socrata 'Contracts' dataset` — a government portal source. | 9c6d4d4c08af6b3ee64b1bfc47f0d74a0f2174ddc54e3b5bd22720e17da487fb | pending |
| D21-24 | procportal_cook_il_awards | `Cook County Procurement — Awarded Contracts & Amendments (Socrata qh8j-6k63)` — a government portal source published by `Cook County, IL Office of the Chief Procurement Officer (Socrata)`. | 188dac4a2a401f13b892f8b93dec47ce35501563ab10b25be954ad623fe7ab6a | pending |
| D21-25 | procportal_davie_fl_purchasing | `Town of Davie Notice of Intent to Award a Sole Source Procurement NTSS-2018-026: Cellebrite Universal Mobile Phone Foren` — a government portal source published by `Town of Davie, FL (Purchasing)`. | c4732cfe619c8bd4ae91491072d745e5d8dbbe30f0dae60ba2661da44c3412e9 | pending |

## Confirmation log

(none yet)
