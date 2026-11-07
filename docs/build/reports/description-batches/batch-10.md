# Description batch 10 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D10-01 | camreg_suffolk_ny_red_light | `TPVA Red Light Camera Locations 2015 (Suffolk County, NY Traffic and Parking Violations Agency, SCOpenData)` — a government portal source published by `Suffolk County, NY (SCOpenData via ArcGIS Online)`. | 2ceff8ab864cab5f8ca1872aaeb7cb158a7739ca7321a508312308813fcb5c52 | pending |
| D10-02 | camreg_surrey_bc | `Surrey traffic cameras (ArcGIS registry)` — a government portal source published by `City of Surrey, British Columbia`. | 3ecee6dd5a152b577e62ed81c5481a719010c8fe6ef1fb3486c0ba6d42d0ade9 | pending |
| D10-03 | camreg_tacoma_wa_ate | `Automated Enforcement Locations (Tacoma)` — a government portal source published by `City of Tacoma, Public Works (ArcGIS Online, owner IT.DataCurator)`. | c9a043608a918e191f7ae968f3069c167bae847c33083b45fe6381299e323dcf | pending |
| D10-04 | camreg_temecula_ca_flock_wfl1 | `Flock_WFL1 (City of Temecula, CA)` — a government portal source published by `City of Temecula, CA (staff account, via ArcGIS Online)`. | d8891d8b72f7ad93d1d90aabea40a9fffa4a45cdcba8ba7627796eb532572b3b | pending |
| D10-05 | camreg_thailand_th | `Thailand CCTV camera layers (ArcGIS registry)` — a government portal source published by `Thai municipal/community camera registries`. | 7b95a7dc61d56981e8b5e8f29df3e5ce2ec77eb0510845675a72f88ec1a1ba4d | pending |
| D10-06 | camreg_thomasville_ga_flock_location | `FLOCK_Location (City of Thomasville, GA)` — a government portal source published by `City of Thomasville, GA (org name via ArcGIS portal self record)`. | f7999391f7514c3240e82675c1e8ae4faca6116bdda7baa14ee807712d1860cd | pending |
| D10-07 | camreg_toronto_on | `Toronto camera locations (ArcGIS republish layer)` — a government portal source published by `City of Toronto (republished layer)`. | c71f9878db859a88db3430602973aeb7381664756138160bc1eb879814e66ef8 | pending |
| D10-08 | camreg_townofws | `ASE camera locations (Town of WS ArcGIS registry)` — a government portal source published by `ArcGIS community-published enforcement-camera registry`. | 4a8fe6fecf2803e46b90385dc2b354b25ad36aa6cfebe432883b34d2f0086eb4 | pending |
| D10-09 | camreg_trafficops_ca | `California highway CCTV cameras (TrafficOps.GIS ArcGIS registry)` — a government portal source published by `California traffic-operations publisher (Postmile schema)`. | b9d3072b9b7c379e456dee408057e734d4697f14f708dec25e6ecd52151bd6b9 | pending |
| D10-10 | camreg_tribal_all_leaders_directory | `Tribal Leaders Directory (BIA Branch of Geospatial Support, ArcGIS FeatureServer)` — a government portal source published by `Bureau of Indian Affairs, Branch of Geospatial Support (via ArcGIS Online)`. | 45d26475ba19ec848295b929fe96da7a4f0c4b723a9e76dd14ebd69799406117 | pending |
| D10-11 | camreg_trpa_us | `Lake Tahoe SMART traffic cameras (TRPA ArcGIS registry)` — a government portal source published by `Tahoe Regional Planning Agency (bi-state compact)`. | 31aacce3cae12c7411e2a3e47cb9779e6614962900ed10fb1af4d13f4df64188 | pending |
| D10-12 | camreg_tulane_la | `New Orleans CCTV cameras (Tulane ArcGIS registry)` — a government portal source published by `Tulane University (republished municipal layer)`. | e86a68a758c01ee40705748e0417a31819c2c78294bcee70b10a7656a377ac79 | pending |
| D10-13 | camreg_txdot_rep_tx | `Texas DOT traffic cameras (ArcGIS republish layer)` — a government portal source published by `Texas Department of Transportation (republished layer)`. | 63a279243e6eb1e0bb155c4cdb53ebfa105ff908719513f2d894cb3433dbaf7f | pending |
| D10-14 | camreg_ua_18_korosten | `Дані про місцезнаходження камер відеоспостереження, що перебувають у комунальній власності Коростенської міської територ` — a government portal source published by `Korosten City Council`. | 956bc96a856a48b9cc46aac3ab89c8184df1350be8861343b7e47562dbff7dcb | pending |
| D10-15 | camreg_uchicago | `Security camera registry (UChicago ArcGIS layer)` — a government portal source published by `University-community-published camera registry`. | dca4ce8c807e3118ac18b968933c46441174008b8f9ce9014fd66f57fa3529c4 | pending |
| D10-16 | camreg_ucsd | `Traffic camera registry (UCSD Online ArcGIS layers)` — a government portal source published by `University-community-published traffic-camera registry`. | b011297f8e24ea5ee7f393d9de460902ac252bd20c23b9d4d1f1fadbd131b69c | pending |
| D10-17 | camreg_ukm_my | `UKM CCTV management system (ArcGIS registry)` — a government portal source published by `Universiti Kebangsaan Malaysia (community-published layer)`. | 7204ad652d5f8d325680a28f353c0fc720e890aa1705e378a652e0be18dbe4e6 | pending |
| D10-18 | camreg_umbc_md | `Maryland camera locations (UMBC ArcGIS registry)` — a government portal source published by `University of Maryland, Baltimore County (republished state layer)`. | 312dd3524531f5a06475d7fed012e8ffe0e780463c4770d004a375aab5fc8553 | pending |
| D10-19 | camreg_und_001 | `Traffic cameras (ArcGIS registry)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | 5ab836ba91904245444a85b8603895c4390ec19c938da9184f8d262cf7ffc382 | pending |
| D10-20 | camreg_und_002 | `CCTV camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dcd083499eb4a031cd626021c81cd6214e82991b1aa9cc36e0805e6bdb8bc5c0 | pending |
| D10-21 | camreg_und_003 | `Public-safety cameras view (ArcGIS registry)` — a government portal source published by `ArcGIS community-published camera registry`. | 4a0526fd469d16f51b0d42f74fa1d6726c2c28fe841c4618e360251bda6d6bfa | pending |
| D10-22 | camreg_und_004 | `CCTV camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dcd083499eb4a031cd626021c81cd6214e82991b1aa9cc36e0805e6bdb8bc5c0 | pending |
| D10-23 | camreg_und_005 | `Surveillance sites (ArcGIS registry)` — a government portal source published by `ArcGIS community-published surveillance-site registry`. | 6f4c2921d39637f617f104d27ab146992b141f7a82920873a3c73bcbf1912d6d | pending |
| D10-24 | camreg_und_006 | `Flock ALPR locations (UA GIS ArcGIS registry)` — a government portal source published by `University-community-published ALPR camera registry`. | 3ae04bb125f26766704c1973287f2136655de3f5ea5f055583350a0a874649d3 | pending |
| D10-25 | camreg_und_007 | `CCTV_ camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | f9204611faadbc3e0755ecfed743766b6298c676fcb879a5a4f2a649aef1a58c | pending |

## Confirmation log

(none yet)
