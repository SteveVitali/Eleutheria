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
| D01-01 | aclu_cell_site_simulators | ACLU cell-site simulators — an upstream project source. | a07e954597905986355c93a5e628173f789279ffd783176e8c4ef7bb24904afe | pending |
| D01-02 | aclu_flock_toolkit | ACLU Get the Flock Out toolkit — an upstream project source. | e82e362c0589d93aef2523ac46e4eb7d745426cc71af54d2e6107847ed4adcc3 | pending |
| D01-03 | agency_audit_export | Agency Flock audit export (public record) — a records channel source. | 4962dcb85390b541e9e43ffff812ae86809a7299a1531ba563473bf9c4855fe9 | pending |
| D01-04 | agenda_az_maricopa_county_board_of | Maricopa County Board of Supervisors — AgendaOnline (Clerk of the Board) — a government portal source published by Maricopa County Clerk of the Board (hosted on databankcloud.com). | b32ef3c29b1a66e9c78ea70c0b41c6fdb300e89c2ebe497ba697db336c638f5d | pending |
| D01-05 | agenda_bexar_county_tx_agenda_center | Agenda Center — Bexar County, TX (CivicEngage) — a government portal source published by Bexar County, Texas (via CivicPlus CivicEngage). | a2155debfb82f2a9eb71a809e2f62d4208de0c9d85b39fdbae8053b15e7607d7 | pending |
| D01-06 | agenda_des_moines_ia_council | City of Des Moines IA council communication 26-235 (2026-06-29) - Motorola Solutions License Plate Recognition software  — a government portal source published by City of Des Moines, IA (City Council communications). | 69f7fcd8af40e9d1ef2a2ea645e056650ab9e581912e1d7f2c819d4705169553 | pending |
| D01-07 | agenda_durham_nc_agenda_center | Agenda Center - Durham, NC (CivicEngage) — a government portal source published by City of Durham, NC. | f32047aa80a8b71ceaee40aa6ac5a83d4087575f7505031aa588422a94b8e1dc | pending |
| D01-08 | agenda_frisco_tx_onbase_agenda_online | Frisco OnBase Agenda Online — a government portal source published by City of Frisco, TX. | ca447363d8dd70650a788499abb6c7cca3b4b34876edc94f818f2d9631d041a3 | pending |
| D01-09 | agenda_haskell_ar_council | City of Haskell AR Resolution No. 19-2025 - contract with Flock Safety for License Plate Reader cameras (4 LPR + 2 Flex  — a government portal source published by City of Haskell, AR City Council. | a618c13e111914ac487e8941ac915b7c5683fc5929b94658c0f9cb756e37c914 | pending |
| D01-10 | agenda_hialeah_fl_agenda_center | Agenda Center - Hialeah, FL (CivicEngage) — a government portal source published by City of Hialeah, FL. | 0e24b6b2023840f0af9ab3b0a5072aeae87cab854f02739490325e13b5a38d27 | pending |
| D01-11 | agenda_jasper_sc_council | Jasper County Council special called meeting agenda e-packet 2024-06-28 (Sheriff purchase of Cellebrite electronic evide — a government portal source published by Jasper County, SC (County Council). | 609c3efe7a8cb0ae2ae29af9972a56a8dad45ef0d437509aab029675aabb81be | pending |
| D01-12 | agenda_jersey_city_nj_digital_agenda | Jersey City Digital Agenda (Municipal Council portal) — a government portal source published by City of Jersey City, NJ Municipal Council. | f6ef017fae64422b95a5d29beedeb59ea0cde73b360b21ed8dfc1ea81e9b5719 | pending |
| D01-13 | agenda_nd_fargo_city_commission_agendas | Fargo City Commission Agendas & Minutes — a government portal source published by City of Fargo, ND. | a4b23cf49cf2def51155392c2dee07fe0c0823c312a53e122f0b768777922a1d | pending |
| D01-14 | agenda_savannah_ga_2023_05_25 | Savannah City Council 2023-05-25 item 17: Authorize the City Manager to Execute a Contract for PLX PenLink Software from — a government portal source published by City of Savannah, GA (City Council, Agenda Plus). | 106f3b8f38e207d670ff593967da09afd379b54509a290704cee7854d6952bc6 | pending |
| D01-15 | agenda_tampa_fl_onbase_agenda_online | Tampa City Council OnBase Agenda Online — a government portal source published by City of Tampa, FL. | 2290e7b783d32284c2ef0d238d4f4a101b13399cccdd21cecde0c5272180675f | pending |
| D01-16 | agenda_tx_dallas_county_commissioners | Dallas County Commissioners Court — Court Agenda / Agendas and Actions (CivicWeb portal) — a government portal source published by Dallas County Commissioners Court. | 1d3fea50ce18c53e95128e358c6db678fc24ae0033e4acb484035a567eb5bdb0 | pending |
| D01-17 | agenda_us_agency_fusus_real | Agency Fusus / real-time crime centre deployment memos, council presentations and launch notices (Axon Fusus customers)  — a government portal source published by Municipal police departments and councils (many); this member hosted by Enlace Latino NC. | ff2e0b4dcce181d578b0d6df8b67f8eabb2cee229c3f05c1ba3ec2b1ee50f105 | pending |
| D01-18 | alpr_abuse_library | ALPR Abuse Library — an upstream project source. | 3429ada88255d5bf3af2355f8da55184f3ec87b1db472bf3d50b39bef2f5b506 | pending |
| D01-19 | alpr_accountability_atlas | ALPR Accountability Atlas — an upstream project source. | 873e1541b1b6d5bb7480a0ea78143c7d636e2dd2f99eb66998ca9e11f0dcd51d | pending |
| D01-20 | alpr_watch | ALPR Watch — an upstream project source. | 42f7cc76dbd9ba43a21899765005ed771f4d23c9fff2ea25ddcf853676774570 | pending |
| D01-21 | alpr_watch_code | ALPR Watch code (GitLab) — an upstream project source. | f78528b61818c495a2dd33dbdfd26be4fae2e4d0b6350ca5f2767ada12538233 | pending |
| D01-22 | alpr_watch_dashboard | ALPR Watch FOIA dashboard (Superset) — an upstream project source. | e54c62844761483f77d21b0b4556484e3da49b4add8dc0a1fbca78a3ea22c8e5 | pending |
| D01-23 | alpr_watch_foia_method | ALPR Watch Flock FOIA method — an upstream project source. | 356a7a5bde9474ddc60ab0223e9c49e5e6c231504138f82372d0818d8dd2576c | pending |
| D01-24 | amsterdam_camerakaart | Amsterdam cameraregister — municipal camera map open data — a government portal source. | b77fd8ab4d473e4d0414f3e58f6828b0a759155d5d20a8929c17b1110d557a14 | pending |
| D01-25 | aspi_mapping_chinas_tech_giants | Mapping China's Tech Giants (ASPI) — an academic source. | e484e52dcc4d4bfc05534b8204ce77af83cf3d10d82e8faa4ca986242b0c1b03 | pending |

## Confirmation log

(none yet)
