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
| D11-01 | camreg_und_010 | `Camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 67c4078dd94e1885fca65f275ca3956aab655b6a440c284924f2dc58a1a6bfb7 | pending |
| D11-02 | camreg_und_011 | `Camera point registry (UNSW ArcGIS layer)` — a government portal source published by `University-community-published camera registry`. | 53bf21ae95d48ef21ff60e1080186723d925cb797e445927a62edb8819962ab5 | pending |
| D11-03 | camreg_und_012 | `Camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 67c4078dd94e1885fca65f275ca3956aab655b6a440c284924f2dc58a1a6bfb7 | pending |
| D11-04 | camreg_und_013 | `Traffic cameras (ArcGIS layer)` — a government portal source published by `ArcGIS community-published traffic-camera registry`. | 0b695defe957a0a0567d9a4e900db7467aada10c29ce52f8e29f4bbea96f3233 | pending |
| D11-05 | camreg_und_014 | `CCTV camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dcd083499eb4a031cd626021c81cd6214e82991b1aa9cc36e0805e6bdb8bc5c0 | pending |
| D11-06 | camreg_und_015 | `Camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 67c4078dd94e1885fca65f275ca3956aab655b6a440c284924f2dc58a1a6bfb7 | pending |
| D11-07 | camreg_und_016 | `University security cameras public view (ArcGIS registry)` — a government portal source published by `University-community-published camera registry`. | 92b4ccbbfd4667d4b996584a9d92afea0119630f6ab94523993f99d1dac02da2 | pending |
| D11-08 | camreg_und_017 | `Public-safety / ALPR cameras view (ArcGIS registry)` — a government portal source published by `ArcGIS community-published camera registry`. | 871c4b3ad045f99f5ac857b5d55f1816eff222b78c110a1999938fdab2b7323f | pending |
| D11-09 | camreg_und_018 | `CCTV camera registries (ArcGIS layers)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dec060e471e136274937670061294aa0de6b6a3a2907a715e37dbd9026f4847a | pending |
| D11-10 | camreg_und_019 | `CCTV camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dcd083499eb4a031cd626021c81cd6214e82991b1aa9cc36e0805e6bdb8bc5c0 | pending |
| D11-11 | camreg_und_020 | `Cameras registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | eac7fa0e34da488732fb700168f4c39626dfb3b6e5d4cb6bb4accc3202c6ec52 | pending |
| D11-12 | camreg_und_021 | `CCTV_S camera registry (UCP/UFR ArcGIS layer)` — a government portal source published by `University-community-published CCTV registry`. | ef36239d2d1ee6f83ef38f321decb9984bb334da623903bffd2d811b09409ccf | pending |
| D11-13 | camreg_und_022 | `BPD surveillance cameras (ArcGIS registry)` — a government portal source published by `ArcGIS community-published camera registry`. | 2015c7cc5ab8948902de75f346485aedc0d4fedb512b789d686e120b356d389c | pending |
| D11-14 | camreg_und_023 | `Cameras registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | eac7fa0e34da488732fb700168f4c39626dfb3b6e5d4cb6bb4accc3202c6ec52 | pending |
| D11-15 | camreg_und_024 | `Replacement CCTV system camera locations (ArcGIS registry)` — a government portal source published by `ArcGIS community-published CCTV registry`. | 0b8c40a31c985de3cab716e8c6719762e4764abf63f7a4d73dd80fd7ae17b637 | pending |
| D11-16 | camreg_und_025 | `Camera intersections registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | db5d87fe4d1cbc2cf5af8141e7f7e8661153c199137199ea40a06fc974343dbd | pending |
| D11-17 | camreg_und_026 | `CCTV camera registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | dcd083499eb4a031cd626021c81cd6214e82991b1aa9cc36e0805e6bdb8bc5c0 | pending |
| D11-18 | camreg_und_027 | `Camera locations (ArcGIS registry)` — a government portal source published by `ArcGIS community-published camera registry`. | f59d2b3060ba81c1ee7249d90cb46adf0dc849af9ccc3c78d25870edb5491b1d | pending |
| D11-19 | camreg_und_028 | `CCTV phase-1 registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published CCTV registry`. | 5ea121589b80bc89137ce7e3b68dacd0ff025ef8002b000ca7a8749bb7e6f60f | pending |
| D11-20 | camreg_und_029 | `CAMERA_3 registry (ArcGIS layer)` — a government portal source published by `ArcGIS community-published camera registry`. | 1ca9eb37e26ba9df38ca57cc57f533f3d8eb05a20daea0bf73d8ad8ef2da0632 | pending |
| D11-21 | camreg_univmb_mb | `Winnipeg-area surveillance cameras (UnivMB ArcGIS registry)` — a government portal source published by `University of Manitoba (republished municipal layers)`. | c3d26a159c87e04cd0cf4dba6c44524db150986e4b183d370c2ead63d1d0e9a6 | pending |
| D11-22 | camreg_uofmd_md | `Maryland CCTV camera layer (UofMD ArcGIS registry)` — a government portal source published by `University of Maryland (republished layer)`. | 56aa0311d42dda771e2159086467be98d4bd0df2859185a49ed44f8cd4da0788 | pending |
| D11-23 | camreg_us_agency_drone_flight | `Agency police drone flight-log / usage feature services on ArcGIS Online` — a government portal source published by `Various municipal police departments (ArcGIS Online orgs)`. | f58b227b37ad537514b6a2797461d5f859480e0669777eca2cbe5facf285f6d9 | pending |
| D11-24 | camreg_us_agency_published_flock | `Agency-published Flock / LPR location layers on ArcGIS Online (family)` — a government portal source published by `Multiple US agencies (via ArcGIS Online / Hub)`. | 6e44f317f9028b2c786c4e6b5d1370a09850b06bba1d2daf19a32df64cea8014 | pending |
| D11-25 | camreg_us_ate_camera_location_and_per | `ATE camera-location and per-camera aggregate datasets on US open-data portals (Socrata Discovery + ArcGIS Hub)` — a government portal source published by `multiple US cities/counties (via Socrata and ArcGIS Online)`. | 24c204124a2b7ebb017b967e9a86d154c9a0a39dae5fee474072ad601c94eb70 | pending |

## Confirmation log

(none yet)
