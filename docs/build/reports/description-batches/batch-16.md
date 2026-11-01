# Description batch 16 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D16-01 | dot_511_ut | UDOT Live View cameras (ArcGIS registry) — a government portal source published by Utah Department of Transportation. | 3a491fca1ef9cfec4f128f25907a3789d6a480fa3443ae4854bcb04d6d61d2ba | pending |
| D16-02 | dot_511_vt | ITS - DeviceList (DeviceLocDetail) — a government portal source published by Vermont Agency of Transportation, Operations & Safety Bureau ITS group (via ArcGIS Online, owner OSB_VTrans). | 7a27a3463aa77cecadf798c43447a7b75ebc70326c79d2774f724bb32d77b45f | pending |
| D16-03 | dot_511_wa | WSDOT travel information cameras (+ KC/WSDOT layer) — a government portal source published by King County / WSDOT; Washington State Department of Transportation. | 615ab2b5b88c0f7b71df0441ec75cea98b7572306b3d107dd6bdb00f7ab04039 | pending |
| D16-04 | dot_511_wv | CCTV_WVDOH (WVDOT Assets MapServer layer 22) — a government portal source published by West Virginia Department of Transportation, Division of Highways (WVDOT GIS server). | fdf78b4e0b93a0841d59a59083ff9458d779c9f352b61586294444b4f9089f72 | pending |
| D16-05 | drivers_against_flock | Drivers Against Flock — a community source. | 2ccd13e5be10f01cdd9677806f035c5a86c312e67e583c8e06b51287ca4cdf61 | pending |
| D16-06 | eff_atlas_of_surveillance | EFF Atlas of Surveillance — an upstream project source. | 61b7975cb75e2ef065b924f6ed8c04ba64f76094e847d64d435ba571e9437dc9 | pending |
| D16-07 | eff_copyright | EFF copyright — an upstream project source. | 958376aa74fb18a98d3821f28c0cdc191bd75190080273234d576a7ed3f1db10 | pending |
| D16-08 | eff_data_driven | EFF Data Driven (2018 release) — an upstream project source. | edb52b93c46f2e56a9192e4d8ac3381828d927805341b881ed48f97a3a3ccfa0 | pending |
| D16-09 | eff_street_level_surveillance | EFF Street-Level Surveillance — an upstream project source. | 2e81ce24a5fe9e56a9ed8592b16f833a8f9321bcc4e1b1f162ea8ead092459b0 | pending |
| D16-10 | equalis_group | Equalis Group — a government portal source. | 5aa970c194eb3441266e5f3217d4d865b206b450d75da3fc7585bf17b3f77af7 | pending |
| D16-11 | escribe | eScribe — a government portal source. | ed7c4bc2645b676989a8468191a4026081275f40880b8154f00d5fde80f9ee0f | pending |
| D16-12 | eyes_off_cedar_rapids | Eyes Off Cedar Rapids — a community source. | ca1b340781c0f48d29448babd04e77b1c00e940c9b584c1c02102144128acb6f | pending |
| D16-13 | eyes_off_eugene | eyes-off/eugene-oregon — an upstream project source. | 5db52497ee4a48d44d72883cd484c1089b140a71b44d9ad7201bd6d558ef332b | pending |
| D16-14 | eyes_on_flock | Eyes on Flock — an upstream project source. | ab93a624f017efbeddb00e36a1ffe131978ddef6845445b0edfc7f511c47252c | pending |
| D16-15 | eyes_on_flock_description | Eyes on Flock description (Reddit) — a news publisher source. | ae257bc9b662ee3b5ab9b212cd1808e4ada21161389337e0706b82b30d7b6877 | pending |
| D16-16 | faa_drone_waivers | FAA drone waivers — a government portal source. | cd941ab38fc106da5e30ad09e34c45323b2be7192094dd459a9fa8391f9a376c | pending |
| D16-17 | facial_recognition_world_map | Facial Recognition World Map — a community source. | f897bae066916eea47e78de95a725c5cfc580c1c5b908606b9721aea5ba14a15 | pending |
| D16-18 | fbi_cde_agency_registry | FBI CDE agency registry — a government portal source. | 4e0cb967fb3d1a5896450c0bb274106df6016950b2946ae8712958676b7dd2ac | pending |
| D16-19 | fema_hsgp_allocations | FEMA Homeland Security Grant Program (HSGP/UASI) allocations — federal grant funding to fusion centers and RTCCs — a government portal source. | a5679d41e0499f8bea9c70a4e18c20a8ef6f9dd376af77e0f5fe728b6c05ff8e | pending |
| D16-20 | flock_ajith_fyi | flock.ajith.fyi — a community source. | f0203fcd8887b6b89e00d4152445f146089af3dbb094cccb798d699a96c09bc9 | pending |
| D16-21 | flock_api_terms | Flock API & Integration Terms — a vendor site source. | 244aac7c7a5c65e24e78aa1817152facc30fcda8e3a0bc9c61b4edf51a9038f7 | pending |
| D16-22 | flock_finder | Flock Finder — a community source. | 50caec5b0c45528177473148a5140cc506790e90e3c6dea3dc53eca753c79807 | pending |
| D16-23 | flock_transparency_portals | Flock transparency portals — a vendor site source. | c738e1e75b66fc3deb4eceab101b95b3c1daca005969e4f2c649cfffa8b984fc | pending |
| D16-24 | flock_you | Flock-You — a community source. | ae2dbaba66c4cce7ccb40401282daec8c4b656e67d0e27501b5700639c9dad55 | pending |
| D16-25 | flockhopper3_deflock_data | flockhopper3/deflock-data (NOT DeFlock) — an upstream project source. | c422013a1e6fb16bbe94804a1af453fc0745fc3c153c752110d2666702a5c628 | pending |

## Confirmation log

(none yet)
