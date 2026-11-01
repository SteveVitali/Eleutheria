# Description batch 05 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D05-01 | camreg_fl511_fl | FL511/FDOT traffic cameras (ArcGIS republish layers) — a government portal source published by Florida Department of Transportation (republished layers). | 6bdde3d51135dd4f992a5c0d4cbc00a8e9519b37346101a7cd722497019f9c37 | pending |
| D05-02 | camreg_fl_broward_county_us_palm_beach | D4 - Camera Survey (FDOT District 4 ROW camera inventory form) — a government portal source published by Florida Department of Transportation, District 4 (via ArcGIS Online). | af8df5c24a0d75c471d0fb2927c5791e83be2c6d6d59e696d2c7334aa9288676 | pending |
| D05-03 | camreg_forwardalliance | CCTV camera registry (forwardalliance ArcGIS layer) — a government portal source published by ArcGIS community-published CCTV registry. | 51304a6c6b66ecf504344ea4ed416b2bd4daaca794ba767f7cf9f73be62120c5 | pending |
| D05-04 | camreg_fr_92_grand_paris_seine_ouest_vid | Vidéoprotection — a government portal source published by Grand Paris Seine Ouest (établissement public territorial). | e08c4da564f88f86db1415a9b2fdeeb8b85f96e44ed819b6965264c1d502250c | pending |
| D05-05 | camreg_friendswood_tx | Friendswood Flock Safety ALPR camera locations (ArcGIS registry) — a government portal source published by City of Friendswood, Texas. | 1f918b7bef341910eb75fac5b6d396b73147f925eacc0f3896dba8fc49b015cd | pending |
| D05-06 | camreg_ga_brookhaven_flock_camera | Flock_Camera_Locations_Sep_2023 (City of Brookhaven, GA) — a government portal source published by City of Brookhaven, GA (via ArcGIS Online). | 4729d2e5df3eb0606e2c56c5f3e014d50937105d42d11404ac658188df1d5a2f | pending |
| D05-07 | camreg_ga_flock_cameras_asof | FLOCK_CAMERAS_ASOF_20240318 (CCSO, west Georgia; org unresolved) — a government portal source published by "CCSO" county sheriff's office (org name private; extent in west Georgia) (via ArcGIS Online). | 63f979c72fb97a35ba970f6281de032b1634d4df8ba694f2ea0280e6318e2366 | pending |
| D05-08 | camreg_ga_peachtree_corners_flock_camera | Flock_Camera_Location (City of Peachtree Corners, GA) — a government portal source published by City of Peachtree Corners, GA (via ArcGIS Online). | 481fcbe656d4953111b8bb88d82f3ba985c9501c9bf7935d6db729ef6a53c14f | pending |
| D05-09 | camreg_ga_savannah_flock_camera | Flock_Camera_Locations2 (Savannah Police Department) — a government portal source published by Savannah Police Department, GA (via ArcGIS Online). | 82ec712a61437178b085222c81ebfbbded13370566d16fd1cb41a5f91ffc3609 | pending |
| D05-10 | camreg_gainesville_fl | Gainesville traffic cameras (ArcGIS registry) — a government portal source published by City of Gainesville, Florida. | 486ce3bc95a45cc2a1a2f4a1d6cc15dab68efd5116dfde40a7a014bbad304f85 | pending |
| D05-11 | camreg_gastonia_nc_flock_condor_cameras | City of Gastonia NC Flock layers: Condor Cameras, LPR, Flock OS integration layers — a government portal source published by City of Gastonia, NC (via ArcGIS Online). | ac627b87abc2d726f3ba3215c1370edd84e8cfb44d1f1375d3b2094ffbbee1fd | pending |
| D05-12 | camreg_gb_eng_barnet_cctv_camera | CCTV camera locations — a government portal source published by London Borough of Barnet. | 7ec0e53ecb3b664673976d4824faca20d1257201278b09dcb1afea77f8da9bb8 | pending |
| D05-13 | camreg_gb_eng_barnet_cctv_traffic | CCTV Traffic Enforcement - camera locations — a government portal source published by London Borough of Barnet. | b8c631b0b86f811070650e2d00522ac33f137be185695219f6df301109a491ac | pending |
| D05-14 | camreg_gb_eng_brist_cctv_cameras | Council CCTV cameras — a government portal source published by Bristol City Council. | b190df9f9201b99db9370eda2c00f74556f03491b1720ba78c5168d05370adff | pending |
| D05-15 | camreg_gb_eng_ipswich_cctv_camera | CCTV Camera Locations in Ipswich — a government portal source published by Ipswich Borough Council. | e47c4eb5e526ce34650d91fadcf4a83873c61d5759094488fcf95d30f995b055 | pending |
| D05-16 | camreg_gb_eng_leice_cctv_cameras | CCTV Cameras — a government portal source published by Leicester City Council. | 621eb1fcb7e6ed4e01a2b8ec46b2cde8e176ef0d5506e00e39d06840c74769ca | pending |
| D05-17 | camreg_gb_eng_mansf_cctv_cameras | CCTV Cameras — a government portal source published by Mansfield District Council. | 3b47c526eeacdc65ee1b88aa3c43d024c0aed8f511ea936ec7a49ae3531c0bf8 | pending |
| D05-18 | camreg_gb_eng_north_cctv_cameras | CCTV cameras — a government portal source published by North Somerset Council. | 52731ddc77137cec075ff00ac039ddbe91a407884590861c3ce1b35c25719402 | pending |
| D05-19 | camreg_gb_eng_runny_cctv_cameras | CCTV Cameras — a government portal source published by Runnymede Borough Council. | ee24a382d29b8730365c13cb074d00453d323e570687ae19a1c94362f3d9e086 | pending |
| D05-20 | camreg_gb_eng_south_skdc_cctv | SKDC CCTV — a government portal source published by South Kesteven District Council. | c5b08da64551c37de4a51f07ddaa2aceeb3daf7ba3a1d043f25d7a9b72acfd92 | pending |
| D05-21 | camreg_gb_eng_traff_trafford_cctv | Trafford Council - CCTV — a government portal source published by Trafford Council. | a64914ac2e50e8e584ebaeb256b1497cec459a8720a3fbdd82bbfa05e0529fe5 | pending |
| D05-22 | camreg_gb_sct_clackmannanshire_cctv | Clackmannanshire - CCTV Cameras — a government portal source published by Clackmannanshire Council (via SpatialData.gov.scot). | 3a0f294631e38e4fad3a0505500f55bd98c8cc614820261bc22da1255093529d | pending |
| D05-23 | camreg_gb_sct_edinburgh_public_cctv | Public CCTV locations - City of Edinburgh — a government portal source published by City of Edinburgh Council (via SpatialData.gov.scot). | 1057c369347bf5e870682d9cd1ef61f4bef200419bd6b059631f1f9d1d17e055 | pending |
| D05-24 | camreg_gedling_gb | Gedling CCTV locations (ArcGIS registry) — a government portal source published by Gedling Borough Council. | 2bc1c1bcb4a91d090ddd7a7b769a460f59f95bd072ce362218705fe0ac763854 | pending |
| D05-25 | camreg_gistel_be | Gistel camera locations (ArcGIS registry) — a government portal source published by Gistel municipal camera registry (m.decraemer publisher). | a7372295a254def359d18d34b42dfd531e9e79718344b6b66ac4d2abd0bbc81b | pending |

## Confirmation log

(none yet)
