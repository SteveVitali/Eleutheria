# Description batch 11 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D11-01 | camreg_und_010 | Camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 447ba4eeaa99001667de991bb272f1af7bba88cf5323aef75ba93ec2b8e9b6e8 | pending |
| D11-02 | camreg_und_011 | Camera point registry (UNSW ArcGIS layer) — a government portal source published by University-community-published camera registry. | f928874ae42302bf4716df53b098544278ae50aabbd635af81b5efeba5b9f242 | pending |
| D11-03 | camreg_und_012 | Camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 447ba4eeaa99001667de991bb272f1af7bba88cf5323aef75ba93ec2b8e9b6e8 | pending |
| D11-04 | camreg_und_013 | Traffic cameras (ArcGIS layer) — a government portal source published by ArcGIS community-published traffic-camera registry. | 5722317b414472ba0ce277a5f39953fad0395a8d6c736b4cac8c09a791f9ee5b | pending |
| D11-05 | camreg_und_014 | CCTV camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 7a08ab242f0b0a7fc0625c1c4ea42ea3110c16b1700fdf86cd60b5e06b8f945a | pending |
| D11-06 | camreg_und_015 | Camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 447ba4eeaa99001667de991bb272f1af7bba88cf5323aef75ba93ec2b8e9b6e8 | pending |
| D11-07 | camreg_und_016 | University security cameras public view (ArcGIS registry) — a government portal source published by University-community-published camera registry. | 92803e553e00dfe8127694cce60d6351eb3dfa2817096a911f9dc66609df434f | pending |
| D11-08 | camreg_und_017 | Public-safety / ALPR cameras view (ArcGIS registry) — a government portal source published by ArcGIS community-published camera registry. | c26f2515b32fe80bc4cc4ae5a33181f36546583c91e2a34bba48b659e65bd8e9 | pending |
| D11-09 | camreg_und_018 | CCTV camera registries (ArcGIS layers) — a government portal source published by ArcGIS community-published CCTV registry. | f1fd82b6207e6841949902ff8550afe7a1a8d1631a49a20df54b766f4d2091e3 | pending |
| D11-10 | camreg_und_019 | CCTV camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 7a08ab242f0b0a7fc0625c1c4ea42ea3110c16b1700fdf86cd60b5e06b8f945a | pending |
| D11-11 | camreg_und_020 | Cameras registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | e8f2cc9887ab19db700392791b628d8697c65a29b30983bc448ab595f7f9de7f | pending |
| D11-12 | camreg_und_021 | CCTV_S camera registry (UCP/UFR ArcGIS layer) — a government portal source published by University-community-published CCTV registry. | 65a3072ded53e64d536995586a0775e6158a39c3e914489c2dd7c66d98bad3bf | pending |
| D11-13 | camreg_und_022 | BPD surveillance cameras (ArcGIS registry) — a government portal source published by ArcGIS community-published camera registry. | 13fc342186a7fcfc4442ab9d2181fcc5b2a200947dfda94913736797c1de2aa5 | pending |
| D11-14 | camreg_und_023 | Cameras registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | e8f2cc9887ab19db700392791b628d8697c65a29b30983bc448ab595f7f9de7f | pending |
| D11-15 | camreg_und_024 | Replacement CCTV system camera locations (ArcGIS registry) — a government portal source published by ArcGIS community-published CCTV registry. | 6aba9d0da1b9bfd3364673252d22b4ea9f3e869e898b92228e5ee2b3632882d6 | pending |
| D11-16 | camreg_und_025 | Camera intersections registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 72206cd73cf48696d7e183466c7fdade88237a977d013d7dd0d534966e86db8a | pending |
| D11-17 | camreg_und_026 | CCTV camera registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 7a08ab242f0b0a7fc0625c1c4ea42ea3110c16b1700fdf86cd60b5e06b8f945a | pending |
| D11-18 | camreg_und_027 | Camera locations (ArcGIS registry) — a government portal source published by ArcGIS community-published camera registry. | bc57eca20a9b30368cb21c95d7ec2d8e0400d72ce102dc6624e64df5c500b243 | pending |
| D11-19 | camreg_und_028 | CCTV phase-1 registry (ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | ca8ac216a074040429acbf89b5186617af4aef124647218e96f19e480b2f08f0 | pending |
| D11-20 | camreg_und_029 | CAMERA_3 registry (ArcGIS layer) — a government portal source published by ArcGIS community-published camera registry. | 8a149958a3d505f49ef9a74544e3af88f8c22030b784ef837fa9a69488dd974f | pending |
| D11-21 | camreg_univmb_mb | Winnipeg-area surveillance cameras (UnivMB ArcGIS registry) — a government portal source published by University of Manitoba (republished municipal layers). | c1ea377028f911db0092e8a678a0a6e2164769821426afec592d89f7edd71f01 | pending |
| D11-22 | camreg_uofmd_md | Maryland CCTV camera layer (UofMD ArcGIS registry) — a government portal source published by University of Maryland (republished layer). | 57c6dc96e8279190b19a27dd047689983d644ae0573c99f8e409401313e46f4b | pending |
| D11-23 | camreg_us_agency_drone_flight | Agency police drone flight-log / usage feature services on ArcGIS Online — a government portal source published by Various municipal police departments (ArcGIS Online orgs). | 9ec2e3f55fff524e50bb0f45d6342bcd8d9239c862c5bd2d8139a8db296b4337 | pending |
| D11-24 | camreg_us_agency_published_flock | Agency-published Flock / LPR location layers on ArcGIS Online (family) — a government portal source published by Multiple US agencies (via ArcGIS Online / Hub). | dc185257a54dfc6cfeaa0468962f3bbd9c04309bcc3b307d1f84532a1b206d49 | pending |
| D11-25 | camreg_us_ate_camera_location_and_per | ATE camera-location and per-camera aggregate datasets on US open-data portals (Socrata Discovery + ArcGIS Hub) — a government portal source published by multiple US cities/counties (via Socrata and ArcGIS Online). | d3149581eb705285bd8cde9e47a94c59a54cc1a122e69227294d961e31e1cdc6 | pending |

## Confirmation log

(none yet)
