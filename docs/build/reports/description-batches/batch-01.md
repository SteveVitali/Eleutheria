# Description batch 01 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D01-01 | aclu_cell_site_simulators | `ACLU cell-site simulators` — an upstream project source. | 6fce82d2abce4f344d575df0663802c454517ba7b5c530398fab8453a0c22358 | pending |
| D01-02 | aclu_flock_toolkit | `ACLU Get the Flock Out toolkit` — an upstream project source. | 55624cc417e5b90ced862310b9b15ee7d45717d570321d6239b73aa16f952663 | pending |
| D01-03 | agency_audit_export | `Agency Flock audit export (public record)` — a records channel source. | d37fe09eb69645139e4f11b81b34f06f988bc68a7f444db650a5f6279497d89e | pending |
| D01-04 | agenda_az_maricopa_county_board_of | `Maricopa County Board of Supervisors — AgendaOnline (Clerk of the Board)` — a government portal source published by `Maricopa County Clerk of the Board (hosted on databankcloud.com)`. | e0d55fda5417ed8254ec5747acaa38eff8a1e000860a3f3fae53e8378cc69b58 | pending |
| D01-05 | agenda_bexar_county_tx_agenda_center | `Agenda Center — Bexar County, TX (CivicEngage)` — a government portal source published by `Bexar County, Texas (via CivicPlus CivicEngage)`. | 2b406e67f4d348ce3549b43b311b1ce0af83e58fe46d94ceb1eff8deb338dff5 | pending |
| D01-06 | agenda_des_moines_ia_council | `City of Des Moines IA council communication 26-235 (2026-06-29) - Motorola Solutions License Plate Recognition software ` — a government portal source published by `City of Des Moines, IA (City Council communications)`. | 378d2509c51e59f8bda8e635bf79af1ac65b2013b9e5f3f3a112757b65897d6a | pending |
| D01-07 | agenda_durham_nc_agenda_center | `Agenda Center - Durham, NC (CivicEngage)` — a government portal source published by `City of Durham, NC`. | 08240e71a52d5dabd4257b9e2a57da1ffedd5e155ede637002559d6f37ad7a4c | pending |
| D01-08 | agenda_frisco_tx_onbase_agenda_online | `Frisco OnBase Agenda Online` — a government portal source published by `City of Frisco, TX`. | 85038a5886dd95ff4d7fe3ed6506248219f022fcf47a8525d8502f218ce4e3a8 | pending |
| D01-09 | agenda_haskell_ar_council | `City of Haskell AR Resolution No. 19-2025 - contract with Flock Safety for License Plate Reader cameras (4 LPR + 2 Flex ` — a government portal source published by `City of Haskell, AR City Council`. | bc2e474a54040e0bf2bab7c0c52ec3e935a7953416b09f45dbc87a42b73017d0 | pending |
| D01-10 | agenda_hialeah_fl_agenda_center | `Agenda Center - Hialeah, FL (CivicEngage)` — a government portal source published by `City of Hialeah, FL`. | d8fb8187f5046f4a7384787441fdbc4eed2aa8dbd471c6dafcafd2d854b06c9f | pending |
| D01-11 | agenda_jasper_sc_council | `Jasper County Council special called meeting agenda e-packet 2024-06-28 (Sheriff purchase of Cellebrite electronic evide` — a government portal source published by `Jasper County, SC (County Council)`. | babc2f39cbaa9eacf663afca21111b7d2f32b75bf4b4d430cb21500a53bd87aa | pending |
| D01-12 | agenda_jersey_city_nj_digital_agenda | `Jersey City Digital Agenda (Municipal Council portal)` — a government portal source published by `City of Jersey City, NJ Municipal Council`. | 27635dc9cff6c51217d5a1bd70fe1293ff61ee82ae17d610c07f7d4e583bf197 | pending |
| D01-13 | agenda_nd_fargo_city_commission_agendas | `Fargo City Commission Agendas & Minutes` — a government portal source published by `City of Fargo, ND`. | aedaad265eabda6a985be0958cdbffacd73b1af37ba24890960521f4aedc931f | pending |
| D01-14 | agenda_savannah_ga_2023_05_25 | `Savannah City Council 2023-05-25 item 17: Authorize the City Manager to Execute a Contract for PLX PenLink Software from` — a government portal source published by `City of Savannah, GA (City Council, Agenda Plus)`. | 8a473b8f275154f818f80761497ab73da21e699aed4edd3bbb1cd3cb8d134b77 | pending |
| D01-15 | agenda_tampa_fl_onbase_agenda_online | `Tampa City Council OnBase Agenda Online` — a government portal source published by `City of Tampa, FL`. | e65f87e3168cc23d538cf170dbd3c01cec2c6d4be2382850cb2571754120d186 | pending |
| D01-16 | agenda_tx_dallas_county_commissioners | `Dallas County Commissioners Court — Court Agenda / Agendas and Actions (CivicWeb portal)` — a government portal source published by `Dallas County Commissioners Court`. | 9ead5f04f0383ba1024136e474582299367e1ed197caec8f0c9a26bf43e8edc2 | pending |
| D01-17 | agenda_us_agency_fusus_real | `Agency Fusus / real-time crime centre deployment memos, council presentations and launch notices (Axon Fusus customers) ` — a government portal source published by `Municipal police departments and councils (many), this member hosted by Enlace Latino NC`. | 331d8edb7fb9ff652e4ebd0d48722e8355b8dfedb324384189beea483968ef70 | pending |
| D01-18 | agendaplus | `Agenda Plus (AgileTech)` — a government portal source. | b4f165972fa8ffd4bc31bac6d217f14d53bc5b4dfafb0b5ca9e44583fb52b288 | pending |
| D01-19 | alpr_abuse_library | `ALPR Abuse Library` — an upstream project source. | 6b4aea825986d43ff4291e429fd2aeec2326beed6d213c3afdcf45814704768e | pending |
| D01-20 | alpr_accountability_atlas | `ALPR Accountability Atlas` — an upstream project source. | 417a8d26ef509b9dde244093d23e1ac755b61558306a45b217cbd903a4b55517 | pending |
| D01-21 | alpr_watch | `ALPR Watch` — an upstream project source. | 9a5901c6a7b41877984f9d8ed13b08a1f04b6aff11e9e09db066fa0228915ebe | pending |
| D01-22 | alpr_watch_code | `ALPR Watch code (GitLab)` — an upstream project source. | 1be631bc2ce15e7c50e00062f81c8dadbc7e2c255c0407cc47d41cebe1a9d7e4 | pending |
| D01-23 | alpr_watch_dashboard | `ALPR Watch FOIA dashboard (Superset)` — an upstream project source. | 6fb03907eeb8a1cdabe029997d4ecac074ced604a29efbe0cbc2715fae0aae7d | pending |
| D01-24 | alpr_watch_foia_method | `ALPR Watch Flock FOIA method` — an upstream project source. | e8c87ed07cf17ac0998771e0548295fb7d1f39f4cb248625d66d88d4f3bd5a1a | pending |
| D01-25 | amsterdam_camerakaart | `Amsterdam cameraregister — municipal camera map open data` — a government portal source. | 93a2ba21d858befd3c194c6c7e45d0db9485451c662c76df00599c317b4731a8 | pending |

## Confirmation log

(none yet)
