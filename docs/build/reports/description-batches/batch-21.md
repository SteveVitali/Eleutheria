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
| D21-01 | policy_pasadena_ca_pd | Pasadena Police Department Policy 620 Cellular Site Simulator Usage and Privacy (City Council agenda 2024-01-22, item 8, — a government portal source published by City of Pasadena, CA (City Council agenda). | 85223f85980eac49444fb49fee82fdae018cecf5db430a2aa5a60c2c16e04514 | pending |
| D21-02 | policy_pflugerville_tx_isd | Pflugerville ISD (TX) - 'Gaggle' page (Safety & Emergency Management programs) — a government mandated disclosure source published by Pflugerville Independent School District, TX. | 6ae98745820c226c99fb9c4a6a552018b3157902dcb311973f2db2c8b8b9eb68 | pending |
| D21-03 | policy_st_cloud_mn_isd742 | St. Cloud Area School District (ISD 742) - 'Securly' parent page: Securly Home parent portal on district-issued devices — a government mandated disclosure source published by St. Cloud Area School District ISD 742, MN. | 8abf8de1d498486a1ec16b45ca6f73e56eb186802248f105c4ffb804b4993578 | pending |
| D21-04 | policy_us_private_camera_registry | Police private-camera registry programme pages (municipal 'Camera Registry' / 'SafeCam' / 'CamerEyes' pages) - family — a government portal source published by Municipal police departments (many; CivicPlus/CivicEngage and other city CMS pages). | bd7227e5065422b4e47e97d7d037be00b751deb98cf23f6809280af658fcafd7 | pending |
| D21-05 | policy_whitesboro_ny_csd | Whitesboro Central School District (NY) - 'Lightspeed Alert' page (Information and Instructional Technology) — a government mandated disclosure source published by Whitesboro Central School District, NY. | 8888a436a4248349d3bc8d78ae62425185c61ebfb803681ab91c419ac08abc1f | pending |
| D21-06 | policy_zionsville_in_camera_registry | Zionsville Police Department Camera Registry (Polaris cameraregistry.net) — a government portal source published by Town of Zionsville, IN Police Department. | 30e819d2caf71003ded084443de50efb0548ebdd24629850b54c665afc294830 | pending |
| D21-07 | powerdms_public_portals | PowerDMS public policy portals — a records channel source. | 09ed87a76e5336bcb6ce8c91e4c6e4470e8cac2233866d8e963300208015bc63 | pending |
| D21-08 | primegov | PrimeGov — a government portal source. | 10fce94ae54548cde8b6dcbd8ef9bd770f356c4afb66c95eb40f30aa32e11742 | pending |
| D21-09 | private_eyes | mcclatchy-southeast/private_eyes — a news publisher source. | 00de93894a95fa0d1c785852b658fdbcd2dc9956d7df7d645d4e82cd0149f274 | pending |
| D21-10 | procportal_austin_tx | City of Austin — Socrata 'Contracts' dataset — a government portal source. | 40a9273385a9687d4719095c733a76abece3833d3ba815cf41e31efaa4153100 | pending |
| D21-11 | procportal_chicago_il | City of Chicago — Socrata 'Contracts' dataset — a government portal source. | ec3e0f14f9f913a2c7e286a6814c3bcef4cb7ffe9f7f436c161fa0f0e272a916 | pending |
| D21-12 | procportal_cook_il_awards | Cook County Procurement — Awarded Contracts & Amendments (Socrata qh8j-6k63) — a government portal source published by Cook County, IL Office of the Chief Procurement Officer (Socrata). | 4b1680a94610ef07933183d098efd40a1cb634a97a8c2cb1c75815a98f144d46 | pending |
| D21-13 | procportal_davie_fl_purchasing | Town of Davie Notice of Intent to Award a Sole Source Procurement NTSS-2018-026: Cellebrite Universal Mobile Phone Foren — a government portal source published by Town of Davie, FL (Purchasing). | e2c0191a5b716fef56d0729e440096baac6f2412e5be6e837472ff845faa7c5c | pending |
| D21-14 | procportal_fl_florida_buy_cooperative | Florida Buy (PAEC) State Cooperative Purchasing Program - GAGGLE.NET, INC. contract (award letter, interlocal agreement, — a government portal source published by Panhandle Area Educational Consortium (PAEC), Florida Buy. | 163b867efa3c82b4d29aca52070fd62c30aa151d01263008c7b3b98833a0c983 | pending |
| D21-15 | procportal_forsyth_nc_purchasing | RFP2449 Real-Time Intelligence Center Enterprise Solution — a government portal source published by Winston-Salem / Forsyth County Purchasing Division for Forsyth County Sheriff's Office. | 0f368a635425d121ac7b36c4fd35d0cb262998adaa97431f6eba2a86a26705bd | pending |
| D21-16 | procportal_kcmo_mo | Kansas City, MO — Socrata 'List of KCMO City Contracts' dataset — a government portal source. | 0d92da7b2e45d4e15ee08358d56729a61814187b3876d4ac2be7ffc8bcf6ee54 | pending |
| D21-17 | procportal_ny_northeastern_regional | Northeastern Regional Information Center (NERIC, Capital Region BOCES) - Gaggle service page — a government portal source published by NERIC (Capital Region BOCES regional information center, NY). | 58053507ec702d2dedecabcbef8a8fe67a0fea39f8572d13ebf5111409176a45 | pending |
| D21-18 | procportal_nyc_ny | City of New York — Socrata 'City Record Online' dataset — a government portal source. | ccc493057d39bf95d723c59b7c67ada91749d741bd7107eff17bb309760a2078 | pending |
| D21-19 | procportal_ok_oklahoma_omes_statewide | Oklahoma OMES statewide contracts and solicitations — a government portal source published by Oklahoma Office of Management and Enterprise Services (OMES). | 9f6f9b2cd67c853b3621d02f238a17fef9607545450fee9b414426726a963fb2 | pending |
| D21-20 | procportal_pr_consulta_del_registro | Consulta del Registro de Contratos (Oficina de la Contralora de Puerto Rico) — a government portal source published by Oficina de la Contralora de Puerto Rico (OCPR). | 82252d2024936c135fb772c3e61c470f9e423482be8e64df18b816178db6db4c | pending |
| D21-21 | procportal_sf_ca | City and County of San Francisco — Socrata 'Supplier Contracts' dataset — a government portal source. | 39b43798b228905801f10ff6842d662715eba903d5cb56b917433075648ddf5c | pending |
| D21-22 | procportal_tx_texas_dir_cooperative | Texas DIR Cooperative Contracts vendor sales data (VSR FY2026 + ARCHIVE FY2010-2025) and customer list — a government portal source published by Texas Department of Information Resources (via data.texas.gov / Socrata). | 9f3370691a06e081d94e9f635e05bb04f810b05cd321861bd2287746446a1c7c | pending |
| D21-23 | procportal_us_naspo_valuepoint_portfolio | NASPO ValuePoint portfolio: Public Safety/Law Enforcement Video Products, Services & Solutions (2023-2028) — a government portal source published by NASPO ValuePoint (lead state: Oklahoma). | 59233fe982b0d1ac993952d81ead8a552f84339a68d9a4fca75e390b040586a2 | pending |
| D21-24 | procportal_wa_des_contract_sales | Washington DES Statewide Contract (Master Contract) Sales Data by Customer, Contract, Vendor (n8q6-4twj) — a government portal source published by Washington State Department of Enterprise Services (via data.wa.gov). | 7aa882f8da100fa438a41282915a2171d4c69873fc107804d6f1ced301af6559 | pending |
| D21-25 | procportal_wa_wsipc_rfp_24 | WSIPC RFP 24-01 Student Safety Solutions - Gaggle cooperative contract (Washington K-12) — a government portal source published by WSIPC (Washington School Information Processing Cooperative). | a32c84f8fd15ee1445d298a62ba582ead5fa1c9fa62f8698e7a2d7fd23637c0e | pending |

## Confirmation log

(none yet)
