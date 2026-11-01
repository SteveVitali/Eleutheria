# Description batch 12 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D12-01 | camreg_us_body_worn_camera | Body Worn Camera Resources (OJP/BJA BWC Toolkit resource library dataset) — a government portal source published by U.S. DOJ Office of Justice Programs (Socrata domain priv-data.ojp.usdoj.gov). | b66cfb350cddd5a02f5a746c696bda431d6a018db730111f3d872deefab2c58c | pending |
| D12-02 | camreg_us_municipal_contract_expenditure | Municipal contract / expenditure registers on Socrata as ALPR procurement evidence (family) — a government portal source published by Multiple US cities/counties (Socrata). | 353ba6a9d9244db281faeb42acddb698064db3d298085b88f85dab653bf7f9fe | pending |
| D12-03 | camreg_us_nces_school_survey_on_crime | NCES School Survey on Crime and Safety (SSOCS) public-use data files — a government portal source published by National Center for Education Statistics (IES, US Dept of Education). | e9d17f4b9700682a7c207ecfc48a5bb2b80493e256107895e26f2453f0c66a54 | pending |
| D12-04 | camreg_us_ny_001 | NYCDOT traffic cameras (ArcGIS republish layer) — a government portal source published by New York City Department of Transportation (republished layer). | 71fb65342b3b4c73fe65a41479fd07cc1787e87559198c9d892c89ef0e3d4e93 | pending |
| D12-05 | camreg_us_ny_002 | New York City traffic cameras (ArcGIS republish layer) — a government portal source published by New York City (republished layer). | 36e9b4a07c9f4942783716413230d7c5606306a1accf6174f61d680252e18a2c | pending |
| D12-06 | camreg_us_socrata_hosted_vendor | Socrata-hosted government vendor-payment / open-checkbook datasets (family) — a government portal source published by multiple state and local governments (via Socrata/Tyler Data & Insights). | 7ceaca36413ca5b0e6b7a635628be4566983720545a96984a0a5a14a7138926b | pending |
| D12-07 | camreg_va_pittsylvania_county_stationary | Stationary LPR (Pittsylvania County, VA) — a government portal source published by Pittsylvania County, VA (via ArcGIS Online). | 1a69a796c7ee50b6a707a8886bdc62983e80b21a77e7d9c643d584f933de90e0 | pending |
| D12-08 | camreg_va_prince_william_county | Community Safety Cameras (Prince William County, VA) — a government portal source published by Prince William County, VA (via ArcGIS Online). | 7fdf4a037b74d28f55759f644dbeb39bdab48a7cfbd1217e0df45179f76669a3 | pending |
| D12-09 | camreg_vancouver_bc | Vancouver web cameras (ArcGIS registry) — a government portal source published by City of Vancouver, British Columbia. | 5e35a94a3c1d4f40449895545981588cb6b698c95ccb7a40a69ffbd3aff3ecce | pending |
| D12-10 | camreg_wa_washington_state_open | Washington State Open Checkbook - vendor payments (fiscal.wa.gov) — a government portal source published by Washington State Legislature LEAP Committee + Office of Financial Management. | a8b68307ef9996a0a743e8cea00ae7d34c2997afa040cd8c8a8f8846ab79b3b3 | pending |
| D12-11 | camreg_washington_dc | Washington DC CCTV street cameras (DCGIS ArcGIS registry) — a government portal source published by District of Columbia (DCGIS / OCTO). | b55da645d5dc93584b3d3962cc528e824863b15fb1aa0e68734228578db02c20 | pending |
| D12-12 | camreg_webappfme | Traffic cameras tour points (ArcGIS layer) — a government portal source published by ArcGIS community-published traffic-camera registry. | c000a35d0b5037aa3c1f11e9ee129d59eb5bd10d01f938b89170ad600dd8ed38 | pending |
| D12-13 | camreg_wellington_nz | Wellington City CCTV cameras (ArcGIS registry) — a government portal source published by Wellington City Council. | c6e142d63ceab8a6fe6644f58b2c76d733238d762c3a158eb1ee343bdfd4b567 | pending |
| D12-14 | camreg_wim_camera | WIM camera locations (ArcGIS registry) — a government portal source published by ArcGIS community-published camera registry. | 6e9ae4a5a9f795af8ee34f92169e2549ca4f3bdafd49a01f5c6b2c11ac5d13f0 | pending |
| D12-15 | camreg_winnipeg_mb | Winnipeg traffic signal cameras (Socrata open-data registry) — a government portal source published by City of Winnipeg Public Works. | 9f0447cef5c4bc6d5c1a0840c7a9b368851d18e9470e95a5008003ebc7bb188e | pending |
| D12-16 | camreg_yline | CCTV camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 7a08ab242f0b0a7fc0625c1c4ea42ea3110c16b1700fdf86cd60b5e06b8f945a | pending |
| D12-17 | camreg_york_gb | City of York CCTV cameras (ArcGIS registry) — a government portal source published by City of York Council. | 21a359015b86b73b8848a7b15fb6ebd4b1c384634e8e5085a85c8b4ed389af8e | pending |
| D12-18 | camreg_york_on | York Region traffic + red-light cameras (ArcGIS registry) — a government portal source published by Regional Municipality of York. | d78fa668becdba7da606ce840dd8ecf13aa0f1a5993f59f9e5daf5ccfbd1455a | pending |
| D12-19 | camreg_yorku | Camera locations (YorkU ArcGIS registry) — a government portal source published by York University community-published camera layer. | afb35e6efd145bf710db2c48f21b8f0ee569720dbe87e67d51db1776614560f0 | pending |
| D12-20 | carnegie_ai_gsi | AI Global Surveillance Index (Carnegie) — an academic source. | 265e5cb631c3dd0bc30a279531069a0abbcf588768ace7087d072e74b02752f3 | pending |
| D12-21 | ccops_anchorage_ak | Anchorage Municipal Code chapter 3.102 'Municipal Use of Surveillance Technologies' - AO 2023-78 amending it to require  — a government mandated disclosure source published by Municipality of Anchorage, AK (Assembly; Assembly Counsel's Office). | 25ee8298882f1db98838364dbb59d96d6131435445ca1acb2a576d732ae61d34 | pending |
| D12-22 | ccops_austin_tx | City of Austin TX - Transparent and Responsible Use of Surveillance Technology (TRUST) Act resolution (File ID 26-1072,  — a government mandated disclosure source published by City of Austin, TX City Council. | 86b80f4f10edf1acda0481c87d64b9bc0257689f0b4d2a572a442d36861f8c2f | pending |
| D12-23 | ccops_baltimore | CCOPS Baltimore — surveillance ordinance disclosures — a government mandated disclosure source. | d6b9b719c74fd0fd2cd81726f979eda66d01fd462a3f81e157caccc2e113b356 | pending |
| D12-24 | ccops_berkeley | CCOPS Berkeley — Surveillance Technology Use ordinance disclosures — a government mandated disclosure source. | dd72da6a9d0276a347df2d00c53dbdc6119e2db9617e6dd619c2d8bf756cb5d2 | pending |
| D12-25 | ccops_boston | CCOPS Boston — surveillance oversight ordinance disclosures — a government mandated disclosure source. | 58becd374ca3ef7f1a7013f85a1aea1f3691b94417ba74a706dd73201acc7ff6 | pending |

## Confirmation log

(none yet)
