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
| D07-01 | camreg_lambeth_gb | `Lambeth parking CCTV cameras (ArcGIS registry)` — a government portal source published by `London Borough of Lambeth`. | 38ef91bd6e76e01bfbab27bea8342c8ea6d71d987599831b3ead7a477928042e | pending |
| D07-02 | camreg_lawrence_ks | `Lawrence KS traffic cameras (ArcGIS registry)` — a government portal source published by `City of Lawrence, Kansas`. | a157afbf88d09c35b52d48be7161dceeab732e89aedc4306127de766316ffad5 | pending |
| D07-03 | camreg_leon_county_fl_overwatch_viewer | `Leon County Sheriff's Office Overwatch Viewer (VIGILANT Fixed LPRs, public access cameras)` — a government portal source published by `Tallahassee-Leon County GIS for Leon County Sheriff's Office, FL (via ArcGIS Online)`. | 20716350c966bbeeadcc6862811ed274be52ee5ed73882923931a1c453132919 | pending |
| D07-04 | camreg_leon_fl | `Leon County traffic cameras (COT ArcGIS registry)` — a government portal source published by `Leon County / City of Tallahassee (cotinter.leoncountyfl.gov)`. | 636b69abfdd866fc9dd3b7ff7f77d19aca6a73140e28f4501c307979ac1d8434 | pending |
| D07-05 | camreg_lexington_ky | `Lexington traffic camera locations (LFUCG ArcGIS registry)` — a government portal source published by `Lexington-Fayette Urban County Government (LFUCG)`. | f460d7c64db64af46d29bb78d0c4c080d6d8169dbd106230f6ca13a5b3d976a1 | pending |
| D07-06 | camreg_lisburn_gb | `Lisburn & Castlereagh CCTV cameras (ArcGIS registry)` — a government portal source published by `Lisburn and Castlereagh City Council`. | 9a78567909146bdd2b2f233c9107d5804fa1dc7f46013085c056188a4dc475d3 | pending |
| D07-07 | camreg_lojic_ky | `Jefferson County KY traffic web cameras (LOJIC/KYTC ArcGIS registry)` — a government portal source published by `LOJIC — Louisville/Jefferson County Information Consortium`. | ae4b43d5e9d414db8ac17d8cd77f42e032124db2018a1266ec64b5073900d0d0 | pending |
| D07-08 | camreg_lpd_flock | `Active Flock camera locations (LPDGIS ArcGIS registry)` — a government portal source published by `ArcGIS community-published ALPR camera registry`. | 550663dc744d5b68acbb9eb7dc8997cd97ecdf03969f553a9a3fbf953168a16b | pending |
| D07-09 | camreg_ma_massachusetts_capital | `Massachusetts Capital Investment Plan FY2025-2029 - line S027 Municipal Body-Worn Camera Grant Program (EO Public Safety` — a government portal source published by `Commonwealth of Massachusetts, Executive Office for Administration and Finance (Capital budget)`. | 2aa3ca3abaf8b65d5f1d16d692078c1e3757eb89d072c67ff5f5e3f4e84fb8ee | pending |
| D07-10 | camreg_manhattan_ks | `Manhattan KS traffic cameras (ArcGIS registry)` — a government portal source published by `City of Manhattan, Kansas`. | 71b194ce959c1b650974b1edb82c98ae864a513810498460e93cc2e4a853e7a1 | pending |
| D07-11 | camreg_marble_falls_tx_flock_locations | `Flock Locations (City of Marble Falls, TX)` — a government portal source published by `City of Marble Falls, TX (via ArcGIS Online)`. | 60c374c3ca30a32d63b24e510246d8086f9a2fa8468fcadac2d4f839a3d7ddf9 | pending |
| D07-12 | camreg_mark43 | `CCTV cameras (mark43 ArcGIS registry)` — a government portal source published by `ArcGIS community-published CCTV registry`. | 5d6aef749bba49c54fc973bb65c42c000d0a5bfa38556e3e94982432d0c8e547 | pending |
| D07-13 | camreg_massdot_ma | `MassDOT CCTV cameras (ArcGIS registry)` — a government portal source published by `Massachusetts Department of Transportation`. | 1b5557263041981438edb2216996de1a48f3513a1aef53b9c67ab7b0a9bcc989 | pending |
| D07-14 | camreg_mbrc_au | `Moreton Bay CCTV cameras (ArcGIS registry)` — a government portal source published by `Moreton Bay Regional Council, Queensland`. | 0151fd737708311e1d3f21486e66b203641164aabf790a24b57c6b37b4c0f059 | pending |
| D07-15 | camreg_mctx_tx | `Montgomery County TX live cameras (ArcGIS registry)` — a government portal source published by `Montgomery County, Texas`. | f2ba40e87f681c71959a99e03f759f1bd1dc2d1b8032019dbf8d398a23345742 | pending |
| D07-16 | camreg_md_opendata | `Maryland traffic cameras (Socrata open-data mirror)` — a government portal source published by `Maryland Department of Transportation / CHART, opendata.maryland.gov`. | 6c25d9fb82356b8429d7b414c76b0ffb4919a1424b634a0e06305f66f577beda | pending |
| D07-17 | camreg_medford_or_ate | `Red Light_Speed Camera (City of Medford, OR)` — a government portal source published by `City of Medford, OR (via ArcGIS Online)`. | 58c78365408cd244610ca2d68c2c221e6f5e86a03e43ddaccc76a9ba93486cb1 | pending |
| D07-18 | camreg_medford_or_drone_deployments_fs | `Drone Deployments FS` — a government portal source published by `City of Medford, OR (via ArcGIS Online)`. | 0fd455470696d52fea8d1778c8e2e91132c17df5346409c27795fb2e54a3059b | pending |
| D07-19 | camreg_mi_detroit_dpd_shotspotter | `DPD ShotSpotter Incident Records` — a government portal source published by `City of Detroit / Detroit Police Department (via ArcGIS Online, data.detroitmi.gov)`. | 4b353921328bab8f3cdd392c5695ee5cf3475905ea2257d30da6f5e01ab34d05 | pending |
| D07-20 | camreg_milford_ct_flocklprcam | `FlockLPRCam (Milford, CT)` — a government portal source published by `"Milford" org (extent Milford, CT, via ArcGIS Online)`. | 74651ee21118c6cffee1463fdee06d7a799bac8c2af8ea7b068df145a4745dc0 | pending |
| D07-21 | camreg_mndot_mn | `MnDOT traffic cameras (ArcGIS republish layer)` — a government portal source published by `Minnesota Department of Transportation (republished layer)`. | bfb6c79597a8f285530da8ae3ed2fb73cfdc4f85f422db65f33eb1a55f26cd22 | pending |
| D07-22 | camreg_monmap_mn | `Mongolia camera locations (monmap ArcGIS registry)` — a government portal source published by `Mongolian mapping community publisher`. | a70d6b86422230bf7dd17675ae28b25f74ff6bc8b86c197444a0f78c2d9cede5 | pending |
| D07-23 | camreg_montgomery_md_ate | `Montgomery County (MD) automated enforcement — Socrata violation aggregates + MCPD SpeedCameras_2024 layer` — a government portal source published by `Montgomery County, MD, Department of Police (data.montgomerycountymd.gov Socrata + county ArcGIS Online org)`. | cf7d07f40cef6e45301f34c48595856eec327aa0cd6cc0b183009d3d376ba874 | pending |
| D07-24 | camreg_mueller_de | `German camera positions (ArcGIS registry)` — a government portal source published by `German community-published camera registry`. | 54af1572160377efe3c3891284631438a6ac995f410343fb8775bacc23e46700 | pending |
| D07-25 | camreg_nashville_tn | `Nashville license-plate-reader camera locations (ArcGIS registry)` — a government portal source published by `Metropolitan Government of Nashville and Davidson County`. | 65b32262d464c3864e31ad6a6083e314c1b36b834886a78c4d6ee8a1fcbf4e0d | pending |

## Confirmation log

(none yet)
