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
| D16-01 | dot_511_ut | `UDOT Live View cameras (ArcGIS registry)` — a government portal source published by `Utah Department of Transportation`. | 6369548347cc3b790cecb58822691fd3abfe4ba860f1e23454a924b4334ac435 | pending |
| D16-02 | dot_511_vt | `ITS - DeviceList (DeviceLocDetail)` — a government portal source published by `Vermont Agency of Transportation, Operations & Safety Bureau ITS group (via ArcGIS Online, owner OSB_VTrans)`. | 9e0851452f6f2fceff639fab92e4fc0e36b47ec504691e6fe2caf712963fb4f3 | pending |
| D16-03 | dot_511_wa | `WSDOT travel information cameras (+ KC/WSDOT layer)` — a government portal source published by `King County / WSDOT, Washington State Department of Transportation`. | c17945e00781e2627fd4119ed300f70b7141a82660219c803c436a1960401d02 | pending |
| D16-04 | dot_511_wv | `CCTV_WVDOH (WVDOT Assets MapServer layer 22)` — a government portal source published by `West Virginia Department of Transportation, Division of Highways (WVDOT GIS server)`. | 1c8407c4aafbea5e07c930af802229ab5a64a5560657b13c143535fcfd72af32 | pending |
| D16-05 | drivers_against_flock | `Drivers Against Flock` — a community source. | fd7573be7d21f6bc5ca8fbe926afed28eb7d536596b8d841000302188e428247 | pending |
| D16-06 | eff_atlas_of_surveillance | `EFF Atlas of Surveillance` — an upstream project source. | a3842988aed92afa19526d4cf4de428e9299b4d78aa5ea1158eb89c3d51f1822 | pending |
| D16-07 | eff_copyright | `EFF copyright` — an upstream project source. | ed2e59e8e1f9a4dadbc14cf0b327b64a339ea29d464ac99aff7a0eb8348e442c | pending |
| D16-08 | eff_data_driven | `EFF Data Driven (2018 release)` — an upstream project source. | d04a02be49531dd98d52a6ee2b9dec94b5ca494a021efd15669c9e1f042a4409 | pending |
| D16-09 | eff_street_level_surveillance | `EFF Street-Level Surveillance` — an upstream project source. | 46b2e19cd2868671f301d99d6f5e7db60f5cd0081e6c6925ba6f0b8881aa5e2c | pending |
| D16-10 | equalis_group | `Equalis Group` — a government portal source. | bd50ac96e7d6d3d5f012525b49efb8157e3fef0f00061f04a736c7369c2182b9 | pending |
| D16-11 | escribe | `eScribe` — a government portal source. | f54d37b176959b464e6bd44342d498dd1c64a99c67088844e456746aeb6cb943 | pending |
| D16-12 | eyes_off_cedar_rapids | `Eyes Off Cedar Rapids` — a community source. | 0edb8cf0016e2f5258a962a5e47e883b66ff90e2dfb4cc77d25c26aceabb19c7 | pending |
| D16-13 | eyes_off_eugene | `eyes-off/eugene-oregon` — an upstream project source. | 16e1550ef672590c0a3112bf4469353b1189823dffeb7dc60e66d25b07fd9bdf | pending |
| D16-14 | eyes_on_flock | `Eyes on Flock` — an upstream project source. | 784ce233dc1bec655588a308e031fd234f319d1c2cfa358498c395edcc72ed41 | pending |
| D16-15 | eyes_on_flock_description | `Eyes on Flock description (Reddit)` — a news publisher source. | 6734a36e10db8bcee4a06ca341d853b28cfa1e6d8f764c30f6166c0178e71791 | pending |
| D16-16 | faa_drone_waivers | `FAA drone waivers` — a government portal source. | 476d930d4527820ecd86ce57259f450b243d04d05c998458768d0d05cad82a69 | pending |
| D16-17 | facial_recognition_world_map | `Facial Recognition World Map` — a community source. | b7aaf2d0d8aa765d78329506ac141ad3d6a53ea837ec3f7a834ece0dd82950cb | pending |
| D16-18 | fbi_cde_agency_registry | `FBI CDE agency registry` — a government portal source. | 8f4e2ae96e9c18b165de552b721ccd2d48312d39a9faf3520e2cbacf3e3b6368 | pending |
| D16-19 | fema_hsgp_allocations | `FEMA Homeland Security Grant Program (HSGP/UASI) allocations — federal grant funding to fusion centers and RTCCs` — a government portal source. | 9fa75f4f6dd20a9f42b02af901ad190be38740aaae8ecad85e90fe6fc40e4f25 | pending |
| D16-20 | flock_ajith_fyi | `flock.ajith.fyi` — a community source. | 8754a7d58516f5157708e70201fa7e9c7ec2262e6935697a0fcd5b02e13e489d | pending |
| D16-21 | flock_api_terms | `Flock API & Integration Terms` — a vendor site source. | 90e8d7d96703039820d3543f06613fef3190fdfc2114dca4d82a19f43ffdca44 | pending |
| D16-22 | flock_finder | `Flock Finder` — a community source. | 90afa64a5d5116270a82791adef7ea3af4389cb52894982b8f4c366cd743ff90 | pending |
| D16-23 | flock_transparency_portals | `Flock transparency portals` — a vendor site source. | 7d65ca80ee10c47f0935652700d18539d9013d1230caa3c3aaef8b04f63f8cde | pending |
| D16-24 | flock_you | `Flock-You` — a community source. | dedef1aa67d9342e0e05517056e8782bba0016b19342a7199ba16297aa547841 | pending |
| D16-25 | flockhopper3_deflock_data | `flockhopper3/deflock-data (NOT DeFlock)` — an upstream project source. | 4aaeb9e9af344f8ba430645196d808bf3001dbb4f3f0135f33909516224acb4d | pending |

## Confirmation log

(none yet)
