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
| D12-01 | camreg_uofmd_md | `Maryland CCTV camera layer (UofMD ArcGIS registry)` — a government portal source published by `University of Maryland (republished layer)`. | 56aa0311d42dda771e2159086467be98d4bd0df2859185a49ed44f8cd4da0788 | pending |
| D12-02 | camreg_us_agency_drone_flight | `Agency police drone flight-log / usage feature services on ArcGIS Online` — a government portal source published by `Various municipal police departments (ArcGIS Online orgs)`. | f58b227b37ad537514b6a2797461d5f859480e0669777eca2cbe5facf285f6d9 | pending |
| D12-03 | camreg_us_agency_published_flock | `Agency-published Flock / LPR location layers on ArcGIS Online (family)` — a government portal source published by `Multiple US agencies (via ArcGIS Online / Hub)`. | 6e44f317f9028b2c786c4e6b5d1370a09850b06bba1d2daf19a32df64cea8014 | pending |
| D12-04 | camreg_us_ate_camera_location_and_per | `ATE camera-location and per-camera aggregate datasets on US open-data portals (Socrata Discovery + ArcGIS Hub)` — a government portal source published by `multiple US cities/counties (via Socrata and ArcGIS Online)`. | 24c204124a2b7ebb017b967e9a86d154c9a0a39dae5fee474072ad601c94eb70 | pending |
| D12-05 | camreg_us_body_worn_camera | `Body Worn Camera Resources (OJP/BJA BWC Toolkit resource library dataset)` — a government portal source published by `U.S. DOJ Office of Justice Programs (Socrata domain priv-data.ojp.usdoj.gov)`. | 053895d5b54183b4d2f4925093ff5f0f452bef6ef1f9d2e376e995c5b3c899be | pending |
| D12-06 | camreg_us_municipal_contract_expenditure | `Municipal contract / expenditure registers on Socrata as ALPR procurement evidence (family)` — a government portal source published by `Multiple US cities/counties (Socrata)`. | bb93a9ec85a6e1cae85b1864e2fa5598b069e33322f48e4c9881fcdddfa97a14 | pending |
| D12-07 | camreg_us_nces_school_survey_on_crime | `NCES School Survey on Crime and Safety (SSOCS) public-use data files` — a government portal source published by `National Center for Education Statistics (IES, US Dept of Education)`. | dfd402cb7cac26800ef2894bd018f9f505197006c41374d3fb452e6a39333f14 | pending |
| D12-08 | camreg_us_ny_001 | `NYCDOT traffic cameras (ArcGIS republish layer)` — a government portal source published by `New York City Department of Transportation (republished layer)`. | b53790679eb5214c464457cbe93edf4a221f63a24c019d6275668a286d7289cb | pending |
| D12-09 | camreg_us_ny_002 | `New York City traffic cameras (ArcGIS republish layer)` — a government portal source published by `New York City (republished layer)`. | 44753b007acc98b7c9126fae7f04f7751499a6092d3b4a8f1eed4f1f920937e2 | pending |
| D12-10 | camreg_us_socrata_hosted_vendor | `Socrata-hosted government vendor-payment / open-checkbook datasets (family)` — a government portal source published by `multiple state and local governments (via Socrata/Tyler Data & Insights)`. | d8e012b96cccabd6b6eed8343865d2678091481df87e6b71f9c6d3130425c6fa | pending |
| D12-11 | camreg_va_pittsylvania_county_stationary | `Stationary LPR (Pittsylvania County, VA)` — a government portal source published by `Pittsylvania County, VA (via ArcGIS Online)`. | 63709646b89587fd802a06bff7165a00f771e499279e5d68b01f9c1bb9f0765c | pending |
| D12-12 | camreg_va_prince_william_county | `Community Safety Cameras (Prince William County, VA)` — a government portal source published by `Prince William County, VA (via ArcGIS Online)`. | 9d5d87a93ec3081617a7ab4ce8531fba8a424815bcaf9fae895417362cd5f391 | pending |
| D12-13 | camreg_vancouver_bc | `Vancouver web cameras (ArcGIS registry)` — a government portal source published by `City of Vancouver, British Columbia`. | 1cb3375ca84fc8e00cdefcbf974a555f53c51c288cfc65614642018e95c19e0b | pending |
| D12-14 | camreg_wa_washington_state_open | `Washington State Open Checkbook - vendor payments (fiscal.wa.gov)` — a government portal source published by `Washington State Legislature LEAP Committee + Office of Financial Management`. | 05af8aa32756ad158f2b42e2408c8689ffc690c98e4e8bd6077f0b41dd433b00 | pending |
| D12-15 | camreg_washington_dc | `Washington DC CCTV street cameras (DCGIS ArcGIS registry)` — a government portal source published by `District of Columbia (DCGIS / OCTO)`. | 22c79e9f5e1b886e357a2fa2acf96e2b6088ce14c55486b67579ebb7a4a45b74 | pending |
| D12-16 | camreg_webappfme | `Traffic cameras tour points (ArcGIS layer)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | c8034fe1a395b3d02d7a495c59c0eadca0817d8f6d06740c85e1c3ab384e1140 | pending |
| D12-17 | camreg_wellington_nz | `Wellington City CCTV cameras (ArcGIS registry)` — a government portal source published by `Wellington City Council`. | 5859e73143fc8c95cbcc18c6076814cef7faa706be6936163999b5e1e34d910f | pending |
| D12-18 | camreg_wim_camera | `WIM camera locations (ArcGIS registry)` — a government portal source published by `ArcGIS community-published camera registry`. | b1c19b65f32ac52e4d9f90622754a9b4504840013ef6df92fd25cd6a76d6a926 | pending |
| D12-19 | camreg_winnipeg_mb | `Winnipeg traffic signal cameras (Socrata open-data registry)` — a government portal source published by `City of Winnipeg Public Works`. | 2a38d4822811bda2c74edc8ef0f1d75f76e82cfac87ce484d1d6813d64343dcc | pending |
| D12-20 | camreg_yline | `CCTV camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dcd083499eb4a031cd626021c81cd6214e82991b1aa9cc36e0805e6bdb8bc5c0 | pending |
| D12-21 | camreg_york_gb | `City of York CCTV cameras (ArcGIS registry)` — a government portal source published by `City of York Council`. | f164cbac9d2253b758649feae2f86bc41d23f14f5b765becdc66c1d621793e90 | pending |
| D12-22 | camreg_york_on | `York Region traffic + red-light cameras (ArcGIS registry)` — a government portal source published by `Regional Municipality of York`. | 3b0960f2f32c5ba808689f92db37d965a57b9f6145e81df17915eabe7d56e35b | pending |
| D12-23 | camreg_yorku | `Camera locations (YorkU ArcGIS registry)` — a government portal source published by `York University community-published camera layer`. | 3f9e47909e578f15e04fa378972f08d330783941de3db9f090ce106c58a336c1 | pending |
| D12-24 | carnegie_ai_gsi | `AI Global Surveillance Index (Carnegie)` — an academic source. | cd4bbb23699070e50c423341c7caf57354f003d1f936c66f3bfa0a02cedafd7a | pending |
| D12-25 | ccops_anchorage_ak | `Anchorage Municipal Code chapter 3.102 'Municipal Use of Surveillance Technologies' - AO 2023-78 amending it to require ` — a government mandated disclosure source published by `Municipality of Anchorage, AK (Assembly, Assembly Counsel's Office)`. | 3319ecdd7ddee431ed5a4e4ca172c33a0dcd0f9ba04fe006838c775b831b28ca | pending |

## Confirmation log

(none yet)
