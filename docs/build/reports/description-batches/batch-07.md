# Description batch 07 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D07-01 | camreg_lawrence_ks | Lawrence KS traffic cameras (ArcGIS registry) — a government portal source published by City of Lawrence, Kansas. | c3fce0b444f8b34bba0330e250d3ee5b261ba7b07410dc9b45f9593cc3ee7327 | pending |
| D07-02 | camreg_leon_county_fl_overwatch_viewer | Leon County Sheriff's Office Overwatch Viewer (VIGILANT Fixed LPRs; public access cameras) — a government portal source published by Tallahassee-Leon County GIS for Leon County Sheriff's Office, FL (via ArcGIS Online). | 72823d306a66ccec7c40600995e6212d9f4e9176609531d323ef6e5248a15388 | pending |
| D07-03 | camreg_leon_fl | Leon County traffic cameras (COT ArcGIS registry) — a government portal source published by Leon County / City of Tallahassee (cotinter.leoncountyfl.gov). | c7ae90c0bbbdc4616843eab31d02fe13a2a51472533e310365143280d33ecd3b | pending |
| D07-04 | camreg_lexington_ky | Lexington traffic camera locations (LFUCG ArcGIS registry) — a government portal source published by Lexington-Fayette Urban County Government (LFUCG). | 0c89486586d12d07ea33e789924da894243786fddfe042af4029c9c56dedd096 | pending |
| D07-05 | camreg_lisburn_gb | Lisburn & Castlereagh CCTV cameras (ArcGIS registry) — a government portal source published by Lisburn and Castlereagh City Council. | f15134345ce60672ba88f12433583f505f4543a99abe9d889c41d30c34a757ab | pending |
| D07-06 | camreg_lojic_ky | Jefferson County KY traffic web cameras (LOJIC/KYTC ArcGIS registry) — a government portal source published by LOJIC — Louisville/Jefferson County Information Consortium. | f3d546c1a21b8c0c32987a0bc3796faa403d9153303eab7c93bbf0b24391fc71 | pending |
| D07-07 | camreg_lpd_flock | Active Flock camera locations (LPDGIS ArcGIS registry) — a government portal source published by ArcGIS community-published ALPR camera registry. | da526c41aaa0c2e04d50943302fb632e37fb9a9f8447c35377b407c00dd2b35b | pending |
| D07-08 | camreg_ma_massachusetts_capital | Massachusetts Capital Investment Plan FY2025-2029 - line S027 Municipal Body-Worn Camera Grant Program (EO Public Safety — a government portal source published by Commonwealth of Massachusetts, Executive Office for Administration and Finance (Capital budget). | 282e7ff790decb059f06da0e9d4d7af1e0f092176b19e2b89a6e06a4fda05a1a | pending |
| D07-09 | camreg_manhattan_ks | Manhattan KS traffic cameras (ArcGIS registry) — a government portal source published by City of Manhattan, Kansas. | c2d0dd58eee5a11c1d01c28481c75af2eeeb66e134be31f48a9f33a37639bf56 | pending |
| D07-10 | camreg_marble_falls_tx_flock_locations | Flock Locations (City of Marble Falls, TX) — a government portal source published by City of Marble Falls, TX (via ArcGIS Online). | 77b0a753414556ca6e6d8b6af3f05e41a254f7b8fe4999087efd5d5e82f89641 | pending |
| D07-11 | camreg_mark43 | CCTV cameras (mark43 ArcGIS registry) — a government portal source published by ArcGIS community-published CCTV registry. | 744099dbb818cae4f26bfe2254171d25246ae88baa571f681707070f6af805c8 | pending |
| D07-12 | camreg_massdot_ma | MassDOT CCTV cameras (ArcGIS registry) — a government portal source published by Massachusetts Department of Transportation. | 6bd33f4b4b2cbce4bf0a9c55a79999f4bfb5e0f6202f47ad3644f6ffa6404edf | pending |
| D07-13 | camreg_mbrc_au | Moreton Bay CCTV cameras (ArcGIS registry) — a government portal source published by Moreton Bay Regional Council, Queensland. | 5239a3a5ca4ee48b4813e764fa9ef0bf67df6926905ec173b2878867071aa46f | pending |
| D07-14 | camreg_mctx_tx | Montgomery County TX live cameras (ArcGIS registry) — a government portal source published by Montgomery County, Texas. | a5ad66839355fa6c61af49eada30c19d5baf5583c8c813e63a21ebf7f3b6e068 | pending |
| D07-15 | camreg_md_opendata | Maryland traffic cameras (Socrata open-data mirror) — a government portal source published by Maryland Department of Transportation / CHART; opendata.maryland.gov. | 526dfec7148db824f35586f2de4fd085af64a2688670d4256a8f91e6211e87a2 | pending |
| D07-16 | camreg_medford_or_ate | Red Light_Speed Camera (City of Medford, OR) — a government portal source published by City of Medford, OR (via ArcGIS Online). | b3e18065c66df52409ce7a8e871007bcf9a81f8b4823f8a0acfef7b022810b24 | pending |
| D07-17 | camreg_medford_or_drone_deployments_fs | Drone Deployments FS — a government portal source published by City of Medford, OR (via ArcGIS Online). | 3525749d5d50a86f89a69f105d8f5dae2d5985010b5653d2674d8e17e455eac6 | pending |
| D07-18 | camreg_mi_detroit_dpd_shotspotter | DPD ShotSpotter Incident Records — a government portal source published by City of Detroit / Detroit Police Department (via ArcGIS Online, data.detroitmi.gov). | 12017e1630acd84ae0ad107206bceb7fb976d2b690286f2859b18c6199a2dd5f | pending |
| D07-19 | camreg_milford_ct_flocklprcam | FlockLPRCam (Milford, CT) — a government portal source published by "Milford" org (extent Milford, CT; via ArcGIS Online). | 7d92f5976f94cf3acbd2fd85aa4fc4ba5399d7e35fb04d5997c2e2db978da5c5 | pending |
| D07-20 | camreg_mndot_mn | MnDOT traffic cameras (ArcGIS republish layer) — a government portal source published by Minnesota Department of Transportation (republished layer). | 88e668a9ad3b8516b0da0ece961ef5281b9fc2de842e72d2e3c79b5f628dd854 | pending |
| D07-21 | camreg_monmap_mn | Mongolia camera locations (monmap ArcGIS registry) — a government portal source published by Mongolian mapping community publisher. | 6e6c3333f7cf223f53be01ed8e9535bba8f5ece174f1bc39910266d17a323832 | pending |
| D07-22 | camreg_montgomery_md_ate | Montgomery County (MD) automated enforcement — Socrata violation aggregates + MCPD SpeedCameras_2024 layer — a government portal source published by Montgomery County, MD, Department of Police (data.montgomerycountymd.gov Socrata + county ArcGIS Online org). | ba9058e8ac0f555d90657d571f68a416185a86a4a721472d9315c0fb4f0a391c | pending |
| D07-23 | camreg_mueller_de | German camera positions (ArcGIS registry) — a government portal source published by German community-published camera registry. | b23529a4c8bb47fda9cb0e23703d3b083dab145130239e6b50ef10aea64e3570 | pending |
| D07-24 | camreg_nashville_tn | Nashville license-plate-reader camera locations (ArcGIS registry) — a government portal source published by Metropolitan Government of Nashville and Davidson County. | ec31debde615ae405da176c75d974be7d65e08fb77972b2707f49701d89f0d72 | pending |
| D07-25 | camreg_ne_lincoln_traffic_cameras | Traffic_Cameras / Traffic Operations - Public Monitoring Cameras (City of Lincoln) — a government portal source published by City of Lincoln, NE Traffic Operations (via Lincoln-Lancaster County ArcGIS Online org wpJGOi6N4Rq5cqFv). | 2e657763093e94fe29207ff5387d1aa38cfe682d5c3265c9319cfd7d3e359de4 | pending |

## Confirmation log

(none yet)
