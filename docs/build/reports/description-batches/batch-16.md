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
| D16-01 | dot_511_newengland | `New England 511 camera API — Iteris/IBI-511 tri-state keyed feed (ME/NH/VT)` — a government portal source published by `New England 511 (ME/NH/VT tri-state coalition)`. | 00bb27d2b7b8978f7d553f2363f1708916e51fb3127203a7b8ee274571951176 | pending |
| D16-02 | dot_511_nm | `Statewide CCTV View` — a government portal source published by `NMDOT ITS CCTV inventory per item snippet (ArcGIS Online org short-name "ITS511", owner douglas.geusz_ITS511, org identi`. | b96f19b6ce8ea794a59374e6a2161c411ea00f7b847c51e844af34290c868821 | pending |
| D16-03 | dot_511_nv | `ITS_ATM - Existing Devices (NDOT Statewide ITS ATM Masterplan, layer 3)` — a government portal source published by `Nevada Department of Transportation (ArcGIS Online owner OpenData_NDOT)`. | 24523a060af9fb19d5409ae93d569e842df7bd80157692c976ff0decc10bff11 | pending |
| D16-04 | dot_511_nvroads | `NV Roads 511 camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Nevada Department of Transportation (NV Roads / 511)`. | 52212cfe0e06b562f9b4f5bc84a0bd66362e4edef43d9dada8cc63476c3d5471 | pending |
| D16-05 | dot_511_ny | `511NY camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `New York State Department of Transportation (511NY)`. | df5c5adb8b3a453c9714c4424149723d79387f61c82ab4272029a7c5ad9e7df1 | pending |
| D16-06 | dot_511_oh | `OHGO public camera API — ODOT keyed feed` — a government portal source published by `Ohio Department of Transportation (OHGO)`. | de2ca98ff945756f682a53acebaec62dd06aae8d92d3dcb8738226aeac9ea4cd | pending |
| D16-07 | dot_511_or | `ODOT TripCheck cameras (ArcGIS registry)` — a government portal source published by `Oregon Department of Transportation (TripCheck)`. | 6e99560b5309ed70c337fcf797dc94b1f5146cb8e99406645a1b13974e990d97 | pending |
| D16-08 | dot_511_pa | `511PA camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Pennsylvania Department of Transportation (511PA)`. | aa041d8367fbdb0a151b143985611f187ef0c107bc248fcf7be304c692cb63b7 | pending |
| D16-09 | dot_511_tx | `TxDOT CCTV locations (ArcGIS registry)` — a government portal source published by `Texas Department of Transportation`. | c2e891266298d80baa7c4c64ac2312e33cf3caf2b8434495de70ab7d100d3f75 | pending |
| D16-10 | dot_511_ut | `UDOT Live View cameras (ArcGIS registry)` — a government portal source published by `Utah Department of Transportation`. | 6369548347cc3b790cecb58822691fd3abfe4ba860f1e23454a924b4334ac435 | pending |
| D16-11 | dot_511_vt | `ITS - DeviceList (DeviceLocDetail)` — a government portal source published by `Vermont Agency of Transportation, Operations & Safety Bureau ITS group (via ArcGIS Online, owner OSB_VTrans)`. | 9e0851452f6f2fceff639fab92e4fc0e36b47ec504691e6fe2caf712963fb4f3 | pending |
| D16-12 | dot_511_wa | `WSDOT travel information cameras (+ KC/WSDOT layer)` — a government portal source published by `King County / WSDOT, Washington State Department of Transportation`. | c17945e00781e2627fd4119ed300f70b7141a82660219c803c436a1960401d02 | pending |
| D16-13 | dot_511_wi | `511WI camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Wisconsin Department of Transportation (511WI)`. | ddfb8cb1cdb77c204f4732eacac372b97022069de1dcb527c78074ac7cc847ba | pending |
| D16-14 | dot_511_wv | `CCTV_WVDOH (WVDOT Assets MapServer layer 22)` — a government portal source published by `West Virginia Department of Transportation, Division of Highways (WVDOT GIS server)`. | 1c8407c4aafbea5e07c930af802229ab5a64a5560657b13c143535fcfd72af32 | pending |
| D16-15 | drivers_against_flock | `Drivers Against Flock` — a community source. | fd7573be7d21f6bc5ca8fbe926afed28eb7d536596b8d841000302188e428247 | pending |
| D16-16 | eff_atlas_of_surveillance | `EFF Atlas of Surveillance` — an upstream project source. | a3842988aed92afa19526d4cf4de428e9299b4d78aa5ea1158eb89c3d51f1822 | pending |
| D16-17 | eff_copyright | `EFF copyright` — an upstream project source. | ed2e59e8e1f9a4dadbc14cf0b327b64a339ea29d464ac99aff7a0eb8348e442c | pending |
| D16-18 | eff_data_driven | `EFF Data Driven (2018 release)` — an upstream project source. | d04a02be49531dd98d52a6ee2b9dec94b5ca494a021efd15669c9e1f042a4409 | pending |
| D16-19 | eff_street_level_surveillance | `EFF Street-Level Surveillance` — an upstream project source. | 46b2e19cd2868671f301d99d6f5e7db60f5cd0081e6c6925ba6f0b8881aa5e2c | pending |
| D16-20 | equalis_group | `Equalis Group` — a government portal source. | bd50ac96e7d6d3d5f012525b49efb8157e3fef0f00061f04a736c7369c2182b9 | pending |
| D16-21 | escribe | `eScribe` — a government portal source. | f54d37b176959b464e6bd44342d498dd1c64a99c67088844e456746aeb6cb943 | pending |
| D16-22 | eyes_off_cedar_rapids | `Eyes Off Cedar Rapids` — a community source. | 0edb8cf0016e2f5258a962a5e47e883b66ff90e2dfb4cc77d25c26aceabb19c7 | pending |
| D16-23 | eyes_off_eugene | `eyes-off/eugene-oregon` — an upstream project source. | 16e1550ef672590c0a3112bf4469353b1189823dffeb7dc60e66d25b07fd9bdf | pending |
| D16-24 | eyes_on_flock | `Eyes on Flock` — an upstream project source. | 784ce233dc1bec655588a308e031fd234f319d1c2cfa358498c395edcc72ed41 | pending |
| D16-25 | eyes_on_flock_description | `Eyes on Flock description (Reddit)` — a news publisher source. | 6734a36e10db8bcee4a06ca341d853b28cfa1e6d8f764c30f6166c0178e71791 | pending |

## Confirmation log

(none yet)
