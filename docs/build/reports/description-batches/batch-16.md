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
| D16-01 | dot_511_fl | `Florida 511 (FL511) camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Florida Department of Transportation (FL511)`. | 0891787cb5656d7149a936ed83cf0dccff5def59d23ee5afeea9061488116a31 | pending |
| D16-02 | dot_511_ga | `GDOT 511 cameras (ArcGIS registry)` — a government portal source published by `Georgia Department of Transportation, rbagby_gema`. | 86d732d554972fa36f91118e2b6c7547763ece677bf189bf754f8686b6f2a58a | pending |
| D16-03 | dot_511_gb | `data.gov.uk CKAN package_search — CCTV (56 datasets)` — a government portal source published by `data.gov.uk (UK Government, per-dataset publishers)`. | e0487c85d9c53bb6e8499fdb4bf7d98090a3ecb9d0758eb84f72ded7c93a777b | pending |
| D16-04 | dot_511_ia | `Iowa DOT traffic cameras (ArcGIS registry)` — a government portal source published by `Iowa Department of Transportation`. | 45d6845a26d1fbedb7e72781622bcd0ee72fc731da333051400b604590f80076 | pending |
| D16-05 | dot_511_id | `Closed-Circuit Television (CCTV) (ITD IntelligentTransportationSystems layer 0)` — a government portal source published by `Idaho Transportation Department (ArcGIS Enterprise gisp.itd.idaho.gov, owner ITDGISdata)`. | 6244d07f8621d599324b367ea6fa4db3a43825041a678c417724a1f21ce0ccf1 | pending |
| D16-06 | dot_511_il | `IDOT Illinois Gateway traffic cameras (ArcGIS registry)` — a government portal source published by `Illinois Department of Transportation`. | 78aa288f53d6ffae3ade280eb895c01f38286576639e2331efd00df1ca6756c4 | pending |
| D16-07 | dot_511_ky | `KYTC traffic cameras (ArcGIS registry)` — a government portal source published by `Kentucky Transportation Cabinet`. | cf5babec1bc98f2a2924e060c0ea6597ea6e6a57c6cf085a812da36934113975 | pending |
| D16-08 | dot_511_la | `LDOTD traffic cameras (ArcGIS registry)` — a government portal source published by `Louisiana Department of Transportation and Development`. | 4a8782eae577798dcbba128a2ef25675acb0dde4125d6f34ae08c57b9bddc9ec | pending |
| D16-09 | dot_511_md | `MD SHA CHART traffic cameras (ArcGIS registry)` — a government portal source published by `Maryland DOT SHA / CHART`. | 787094955cb8820619bdf9ee340b9d80024c9f7b56083bcbde0d094c057b4fbd | pending |
| D16-10 | dot_511_mi | `MiDrive Cameras` — a government portal source published by `Michigan Department of Transportation (via ArcGIS Online, owner MDOT_GIS)`. | 1dee23f8a5ff60a8a53a2c7ce8aa3d56de62f3967340caf0fdfd957dfeaf8b49 | pending |
| D16-11 | dot_511_mo | `MoDOT traffic cameras (ArcGIS registry)` — a government portal source published by `Missouri Department of Transportation`. | 7ac10e9693f68bdb0d41d2350fdc8bee6f253203beca51b5a8784cf1b7b6686d | pending |
| D16-12 | dot_511_nc | `NCDOT_Cameras` — a government portal source published by `North Carolina Department of Transportation (ArcGIS Online org NuWFvHYDMVmmxMeM, which hosts GISUnit.NCDOT.GOV items)`. | 634ae9248cf8494be80bf52f23fecd5359fea615e1ee94539086f273b229dc21 | pending |
| D16-13 | dot_511_newengland | `New England 511 camera API — Iteris/IBI-511 tri-state keyed feed (ME/NH/VT)` — a government portal source published by `New England 511 (ME/NH/VT tri-state coalition)`. | 00bb27d2b7b8978f7d553f2363f1708916e51fb3127203a7b8ee274571951176 | pending |
| D16-14 | dot_511_nm | `Statewide CCTV View` — a government portal source published by `NMDOT ITS CCTV inventory per item snippet (ArcGIS Online org short-name "ITS511", owner douglas.geusz_ITS511, org identi`. | b96f19b6ce8ea794a59374e6a2161c411ea00f7b847c51e844af34290c868821 | pending |
| D16-15 | dot_511_nv | `ITS_ATM - Existing Devices (NDOT Statewide ITS ATM Masterplan, layer 3)` — a government portal source published by `Nevada Department of Transportation (ArcGIS Online owner OpenData_NDOT)`. | 24523a060af9fb19d5409ae93d569e842df7bd80157692c976ff0decc10bff11 | pending |
| D16-16 | dot_511_nvroads | `NV Roads 511 camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Nevada Department of Transportation (NV Roads / 511)`. | 52212cfe0e06b562f9b4f5bc84a0bd66362e4edef43d9dada8cc63476c3d5471 | pending |
| D16-17 | dot_511_ny | `511NY camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `New York State Department of Transportation (511NY)`. | df5c5adb8b3a453c9714c4424149723d79387f61c82ab4272029a7c5ad9e7df1 | pending |
| D16-18 | dot_511_oh | `OHGO public camera API — ODOT keyed feed` — a government portal source published by `Ohio Department of Transportation (OHGO)`. | de2ca98ff945756f682a53acebaec62dd06aae8d92d3dcb8738226aeac9ea4cd | pending |
| D16-19 | dot_511_or | `ODOT TripCheck cameras (ArcGIS registry)` — a government portal source published by `Oregon Department of Transportation (TripCheck)`. | 6e99560b5309ed70c337fcf797dc94b1f5146cb8e99406645a1b13974e990d97 | pending |
| D16-20 | dot_511_pa | `511PA camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Pennsylvania Department of Transportation (511PA)`. | aa041d8367fbdb0a151b143985611f187ef0c107bc248fcf7be304c692cb63b7 | pending |
| D16-21 | dot_511_tx | `TxDOT CCTV locations (ArcGIS registry)` — a government portal source published by `Texas Department of Transportation`. | c2e891266298d80baa7c4c64ac2312e33cf3caf2b8434495de70ab7d100d3f75 | pending |
| D16-22 | dot_511_ut | `UDOT Live View cameras (ArcGIS registry)` — a government portal source published by `Utah Department of Transportation`. | 6369548347cc3b790cecb58822691fd3abfe4ba860f1e23454a924b4334ac435 | pending |
| D16-23 | dot_511_vt | `ITS - DeviceList (DeviceLocDetail)` — a government portal source published by `Vermont Agency of Transportation, Operations & Safety Bureau ITS group (via ArcGIS Online, owner OSB_VTrans)`. | 9e0851452f6f2fceff639fab92e4fc0e36b47ec504691e6fe2caf712963fb4f3 | pending |
| D16-24 | dot_511_wa | `WSDOT travel information cameras (+ KC/WSDOT layer)` — a government portal source published by `King County / WSDOT, Washington State Department of Transportation`. | c17945e00781e2627fd4119ed300f70b7141a82660219c803c436a1960401d02 | pending |
| D16-25 | dot_511_wi | `511WI camera API — Iteris/IBI-511 keyed feed` — a government portal source published by `Wisconsin Department of Transportation (511WI)`. | ddfb8cb1cdb77c204f4732eacac372b97022069de1dcb527c78074ac7cc847ba | pending |

## Confirmation log

(none yet)
