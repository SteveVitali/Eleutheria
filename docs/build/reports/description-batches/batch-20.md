# Description batch 20 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D20-01 | osm_element_history | OSM element history — an upstream project source. | be6a58fb6f7d413d6dd2b36e829ce32943155a9efc9906c31d66241d920b3587 | pending |
| D20-02 | osm_overpass | OSM Overpass API — an upstream project source. | 23c606385a76332bc82562e7c9b8a1a83b53f6bfde7759748756b69d7d94a4d3 | pending |
| D20-03 | osm_replication | OSM replication diffs — an upstream project source. | e2c3d649475415f1eff9fd49dac002ffc3b1f519fb2da747fa4134f3e0cecfb7 | pending |
| D20-04 | osm_surveillance_tagging | OSM surveillance tagging (Tag:man_made=surveillance) — an upstream project source. | 4e0bf823de06b4e26f7be82ef4c31726e77f8c86642a59aa2ef6504cd2400c9d | pending |
| D20-05 | osm_taginfo | OSM taginfo API — an upstream project source. | 2c595a925bb43717d8553824bbe9861860cf9c43547cbd08ab8e52670c14ba77 | pending |
| D20-06 | osmf_licence_guidelines | OSMF Licence Community Guidelines — an upstream project source. | 8dc5aeb6a9dc272c090a02fd2c5965d93b6fb1f02e86c16b69af6443abf037d5 | pending |
| D20-07 | panopti_ca | resistanceisliberty/panopti.ca — an upstream project source. | 4716c7b642e7185d2d63674324cc33c64ec165c4eca9e32f50ac64a8d00ddfbc | pending |
| D20-08 | panopticity | PanoptiCity — a community source. | 163fbd5e27980824945aea97281ff4cf7e75b74d3b112250ed4a78d411b61daa | pending |
| D20-09 | pathways_acoustic_drone_location | Acoustic / drone / commercial-location procurement & policy (Stage-5 pathway) — a government portal source. | d2be8ef41f7e433b1820f6cac0358aaeb5ea4fead00978d8a5ed5cdff61a5cf0 | pending |
| D20-10 | pathways_fr_css_forensics | FR / cell-site-simulator / mobile-forensics procurement & policy (Stage-5 pathway) — a government portal source. | 1bbc9f0d1c2d90b0d4cb3c5936070e6fab81bd5c219f809cb7b3fddc4017e03f | pending |
| D20-11 | pathways_rtcc_federation | Municipal RTCC / private-camera federation disclosures (Stage-5 pathway) — a government portal source. | 5b4615f5b9314737ac28f41089d978cd5000b503458229a2471dd87fac3d9469 | pending |
| D20-12 | periscope_s2g | Periscope S2G — eBid procurement portals — a government portal source. | bcedf8ee4fc7aec3d6cd7aef8a5bb01a8b960afd9ff9fe21eb08988c5a5eaffc | pending |
| D20-13 | planetbids | PlanetBids — public agency procurement portals — a government portal source. | 6d74707a01b080380040f62ada74ce331e285f32e977f0dcb139a7104adef254 | pending |
| D20-14 | policy_albuquerque_nm_apd | APD Standard Operating Procedures (incl. SOP 1-22 Automated License Plate Reader Program) — a government portal source published by Albuquerque Police Department. | b8e78fa2e22912c2cff763327b188689e5e93d25d56793d330054bf19b8d11c4 | pending |
| D20-15 | policy_anaheim_ca_pd_policy_manual | Anaheim PD Policy Manual (Lexipol) — a government portal source published by Anaheim Police Department (Lexipol-licensed manual). | 248ed7695b339405af26fd47526ff43f95d333fb06558624a251dd140bccb4b9 | pending |
| D20-16 | policy_bangor_me_pd | Bangor Police Department General Order 2-59 'Unmanned Aerial Systems' (effective 2025-10-05) — a government portal source published by City of Bangor, ME (Police Department). | 266353b0c33fd120d8d5193274e8362cff61e1594771ec4253acfff6191a2486 | pending |
| D20-17 | policy_chicago_il_oemc_link_your | Chicago OEMC - Link Your Cameras (Private Sector Camera Initiative) — a government portal source published by City of Chicago Office of Emergency Management and Communications. | 8da1305d164bec6fd708bfb170bd676c51e5676f9742ece2fb83ca89bdba722e | pending |
| D20-18 | policy_houston_tx_hpd | Houston Police Department General Orders — a government portal source published by Houston Police Department. | c93c05a513adbd7162ce334fc8c118c6a2ffe3db57fbed112ab95bbccf813b74 | pending |
| D20-19 | policy_lafayette_in_camera_registration | Lafayette Police Department camera registration (via CityProtect/CrimeReports) — a government portal source published by City of Lafayette, IN Police Department. | f58722323abb244b9558be3346157e911166e6aea32e530655f8f524978942ed | pending |
| D20-20 | policy_little_rock_ar_pd | Little Rock Police Department General Order G.O. 332 'Small Unmanned Aircraft Systems' (2025-09-17; PowerDMS public port — a government portal source published by City of Little Rock, AR (Police Department; via PowerDMS public portal). | ebe24b96e3d64c170ae7a1b2f41a130a5342574b55dfcfcb5853ea59fdac7e37 | pending |
| D20-21 | policy_maricopa_county_az_mcso_policies | MCSO Policies (Critical, Detention, Enforcement, General Policies and Procedures) — a government portal source published by Maricopa County Sheriff's Office. | 63cbf97b5ab979132df87409f435aaa6f89cd07d67b1880da64002adb60a1ba8 | pending |
| D20-22 | policy_norman_ok_alpr_policy_amendment | Norman police ALPR policy and amendment discovery — a government portal source published by City of Norman / Norman Police Department. | ccaed53ac6d3874c9ad1fa1d3a4facc2d2e4d860b8c95b60ffee23fd61709ad0 | pending |
| D20-23 | policy_ok_oklahoma_dac_uved | Oklahoma DAC UVED program and authority chain — a government portal source published by Oklahoma District Attorneys Council (DAC — UVED program). | 7536775034ea73b495ac363cbeee894219dcd71d1fb9994200ad39eedaba3703 | pending |
| D20-24 | policy_onslow_nc_schools | Onslow County Schools (NC) - 'Gaggle Safety Management' page (Cybersecurity at OCS) — a government mandated disclosure source published by Onslow County Schools, NC. | 27367fccc483a00ab111204380176bc5732ea385cba742fe85463c77083c9842 | pending |
| D20-25 | policy_orange_county_ca_sheriff | Policy 610 Cellular Site Simulator Usage and Privacy - Orange County Sheriff-Coroner Department — a government portal source published by Orange County Sheriff-Coroner Department, CA. | 23d70a32a5f9cd2465b0a15ad5a558ab162f8c54a347fe725ff36aecc05b50b5 | pending |

## Confirmation log

(none yet)
