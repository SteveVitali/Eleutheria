# Description batch 19 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D19-01 | leaic_crosswalk | `LEAIC crosswalk (ICPSR study 35158)` — an academic source. | d006ad537cf6a1d96952da2fea48c29f7fdffe8df8f5935381203d7c4d82e8eb | pending |
| D19-02 | legis_ca_gov_code_53166 | `California Government Code § 53166 - cellular communications interception technology usage and privacy policies and acqu` — a government portal source published by `California Legislature`. | cffb53f818186330b6fb9da138aa06fb144943652838d72a7e59de6d690f2514 | pending |
| D19-03 | legis_gu_governor | `Governor of Guam press release: 'Bill for GPD Security Cameras now Law' (Bill 132-35, the Governor's alternative to Bill` — a government portal source published by `Office of the Governor of Guam`. | cf56bc7627125b3dafadcfde3481e4330a47fc9e17ab6d9c1cf707878dc6e42a | pending |
| D19-04 | legis_ie_rs_general_scheme | `L&RS General Scheme Briefing Paper: Garda Síochána (Recording Devices) (Amendment) Bill` — a government portal source published by `Houses of the Oireachtas Library & Research Service`. | 1ade9cd2718ee0f811995781bdaba359c59d9b44b7e4b5272ab4e416d22ecabc | pending |
| D19-05 | legis_pr_pc0489_ley_del | `PC0489 — Ley del Programa de Vigilancia, Prevención y Protección de Menores (supervisión electrónica como condición de f` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 44dfb90456b34f796fe90fbba3e76d703371b9c5e073fe97d79e6a71e2c09755 | pending |
| D19-06 | legis_pr_pc0560_plan_de | `PC0560 — Plan de Vigilancia de las Costas, Puertos y Aeropuertos` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 67417ea83386241d712e0883ec9151686db9b92b369cc432573e2e59aff44113 | pending |
| D19-07 | legis_pr_rc0740_investigaci_sobre | `RC0740 — investigación sobre cámaras de vigilancia o monitoreo de tránsito en semáforos y el Sistema de Monitoreo de Sem` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 864894ac6d959a73701055809a765825120c9f844151d1544b3ef21bb7839b81 | pending |
| D19-08 | legis_pr_rc0787_resoluci_de | `RC0787 — Resolución de la Cámara: investigación sobre cámaras y sistemas de vigilancia con reconocimiento facial, biomét` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 46d2561053da262ca2f20a1c7602ce10c3aac8aedd3b719608a41a99febdbf75 | pending |
| D19-09 | legis_pr_rcs0198_resoluci_conjunta | `RCS0198 — Resolución Conjunta del Senado: requisito de cámaras de seguridad (videovigilancia) para licencias de venta de` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 6ee9f56f8b42fd5a95b2f3a64e52ccc3797f2880633ceacbeadf392a01b82f39 | pending |
| D19-10 | legis_pr_rs0604_resoluci_del | `RS0604 — Resolución del Senado: investigación sobre cámaras y sistemas de vigilancia con reconocimiento facial, biométri` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | ce6a5f7500cd23c063995e0dede6851861546868b88880bf370044991096268e | pending |
| D19-11 | legis_pr_sistema_nico_de | `Sistema Único de Trámite Legislativo (SUTRA)` — a government portal source published by `Asamblea Legislativa de Puerto Rico — Oficina de Servicios Legislativos (host oslpr.org, attribution inferred)`. | bfee4ea00a54435485724134a53465366c3c9599e1ab9b261d044146e016af6e | pending |
| D19-12 | legis_tribal_tohono_oodham_notice | `Tohono O'odham Legislative Branch — public-hearing notice: Border Patrol LGDS + Automated Surveillance Tower proposals (Domestic Affairs Committee, 2025-11-19)` — a government portal source published by `Tohono O'odham Nation, Legislative Branch (Domestic Affairs Committee)`. | 70d9b52e9e2b3641cd80b44e470b254140785e83936919aa50a5aaa1a975514f | pending |
| D19-13 | legis_us_dhs_sorn_plate_data | `DHS System of Records Notices referencing license-plate-reader data (Federal Register document pages)` — a government mandated disclosure source published by `U.S. Department of Homeland Security (ICE, CBP) via the Federal Register`. | 29b3a3aaea95a8b4b905c540b7ff6b6ac800ac2485a47d5cd013fc2839e56729 | pending |
| D19-14 | legis_us_federal_register_api | `Federal Register API (documents search: notices, rules, SORNs)` — a government portal source published by `Office of the Federal Register (NARA) / GPO`. | 191f80c9c04093b129577018642eec9eefd60fb64903c32b0946f1d9991fa8b5 | pending |
| D19-15 | legis_vi_legislature_virgin_islands | `Legislature of the U.S. Virgin Islands press release: 'Committee advances bill to provide automatic license plate reader` — a government portal source published by `Legislature of the Virgin Islands (34th Legislature)`. | 6cbbe7d27e6523531e766d52947ef1f67e8d64bb6491299673cb602ce1af854e | pending |
| D19-16 | legistar | `Legistar InSite API` — a government portal source. | 464bcaa5ea573d257b34fdae6666f3008aa3a8a949d963d5969f67d7127b3124 | pending |
| D19-17 | madada | `Ma Dada (FR CADA public-records platform)` — a records channel source. | ee9a0c3956e14bc662acc82983e984b24002f24aabacf85f7e990e7eca5822c9 | pending |
| D19-18 | monahan_grounding_the_flock | `Monahan, "Grounding the Flock" (2026)` — an academic source. | c42ce3c21a8974d08113f9675c05986734c037226af7265ebe23695bf7d8b828 | pending |
| D19-19 | muckrock | `MuckRock` — a records channel source. | 4cde184ff3fc51e576db797943e848cfe58fdde3b7238020d9274df8521a3885 | pending |
| D19-20 | muckrock_public | `MuckRock public request pages` — a records channel source. | a8640e5f93c85408144046542adfc444031f891f6dd25e6a2c80d4f6f5f11589 | pending |
| D19-21 | naspo_valuepoint | `NASPO ValuePoint` — a government portal source. | 7b80d9bfedc37ca660422a776e4efee7f98214acd2338b9068ef935d35e7566f | pending |
| D19-22 | natural_earth_10m | `Natural Earth 10m (admin-0/admin-1 boundaries)` — an upstream project source. | cdd9c40418b09d956e70280bfbcc910dcb149c83ecf2bebd0212a7e986c37eb6 | pending |
| D19-23 | nces_ipeds_ntd_cms | `NCES / IPEDS / NTD / CMS` — a government portal source. | 9975abe2a824037040f4eafc1798b1822796e16fe61ebc29bf7c5aea1c844911 | pending |
| D19-24 | nextrequest | `NextRequest` — a records channel source. | e649baa957350fafaead422b9c8f40f08b6437a64f6a077764b530c9b870880f | pending |
| D19-25 | novusagenda | `NovusAgenda` — a government portal source. | cf4374dfd9b644a5513646e24c33a5602c8e922c9d70884338a696b8363a3c4d | pending |

## Confirmation log

(none yet)
