# Description batch 18 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D18-01 | grant_us_doj_cops_technology | `DOJ COPS technology/equipment award documents` — a government portal source published by `U.S. DOJ Office of Community Oriented Policing Services (COPS)`. | 41bec365328894851bc9bb3981b1525b513cb92b91250b392ccefb653d8788ae | pending |
| D18-02 | gsa | `GSA` — a government portal source. | 0afb22c1d632893ec11f30ab901d40d5c43afca501b353f1f1bc6dd7425ca721 | pending |
| D18-03 | guardian_flock_cameras | `Guardian, Flock cameras (2026-08-20)` — a news publisher source. | f04ab5d82a82752d61de5269e8f9d2b81a72cb6ab1f750497bc1a5025dcb951d | pending |
| D18-04 | have_i_been_flocked | `Have I Been Flocked` — an upstream project source. | 1049f27c8af39a3e15f16fab63ab8df70ff9c1888af8ee78cbc6c8cf91cd1ad5 | pending |
| D18-05 | hgacbuy | `HGACBuy` — a government portal source. | cfa2012d73f64eba59ff8bcd9127f41efd3366b506974883102c6aa24bf9ab1c | pending |
| D18-06 | hibf_audit_log_guide | `HIBF audit-log guide` — an upstream project source. | 481cff44ff202fbe2c2c7f53d4cc3f94790997bf6b7dd4d4f21381064076fe46 | pending |
| D18-07 | hibf_methodology | `HIBF methodology hub` — an upstream project source. | 6faa3dfcc29ec1b4fbee0f6425657bcd8a37edc1e8e98e58731a3b3c9ab4a43e | pending |
| D18-08 | internet_archive_wayback | `Internet Archive Wayback` — an upstream project source. | 4b0fc24c43db45ca71250ed5cd6439e0e81129937cb44c34cdd18e7b16db9c3e | pending |
| D18-09 | iqm2 | `IQM2` — a government portal source. | cfcec0931c47d98ddd052ef0acc03ad4f4aef3be9b3b65668249a40d1b6fade5 | pending |
| D18-10 | journalrecord | `The Journal Record (Oklahoma City)` — a news publisher source. | dd19d586a9b38b78175649787f2b21e07d2c47715fe73c1c6ddd37ab246fe5b4 | pending |
| D18-11 | justfoia | `JustFOIA` — a records channel source. | 87421efbf0bbdf6eb10c4085fb46da4948b2c320346af3edcc3a0fbd2c4902fd | pending |
| D18-12 | la_city_clerk_cfms | `LA City Clerk Connect (CFMS) — Los Angeles City legislative file management` — a records channel source. | 41dc16c0034fb2356e7f347ff8e9602e26152a6d5790443cba9b75d8ed481d25 | pending |
| D18-13 | la_quadrature_du_net | `La Quadrature du Net` — a news publisher source. | 3c68460d16a67d3ecc94c3de1f4dcdd3e76977709edd044dfc3a386d927127b3 | pending |
| D18-14 | leaic_crosswalk | `LEAIC crosswalk (ICPSR study 35158)` — an academic source. | d006ad537cf6a1d96952da2fea48c29f7fdffe8df8f5935381203d7c4d82e8eb | pending |
| D18-15 | legis_ca_gov_code_53166 | `California Government Code § 53166 - cellular communications interception technology usage and privacy policies and acqu` — a government portal source published by `California Legislature`. | cffb53f818186330b6fb9da138aa06fb144943652838d72a7e59de6d690f2514 | pending |
| D18-16 | legis_gu_governor | `Governor of Guam press release: 'Bill for GPD Security Cameras now Law' (Bill 132-35, the Governor's alternative to Bill` — a government portal source published by `Office of the Governor of Guam`. | cf56bc7627125b3dafadcfde3481e4330a47fc9e17ab6d9c1cf707878dc6e42a | pending |
| D18-17 | legis_ie_rs_general_scheme | `L&RS General Scheme Briefing Paper: Garda Síochána (Recording Devices) (Amendment) Bill` — a government portal source published by `Houses of the Oireachtas Library & Research Service`. | 1ade9cd2718ee0f811995781bdaba359c59d9b44b7e4b5272ab4e416d22ecabc | pending |
| D18-18 | legis_pr_pc0489_ley_del | `PC0489 — Ley del Programa de Vigilancia, Prevención y Protección de Menores (supervisión electrónica como condición de f` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 44dfb90456b34f796fe90fbba3e76d703371b9c5e073fe97d79e6a71e2c09755 | pending |
| D18-19 | legis_pr_pc0560_plan_de | `PC0560 — Plan de Vigilancia de las Costas, Puertos y Aeropuertos` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 67417ea83386241d712e0883ec9151686db9b92b369cc432573e2e59aff44113 | pending |
| D18-20 | legis_pr_rc0740_investigaci_sobre | `RC0740 — investigación sobre cámaras de vigilancia o monitoreo de tránsito en semáforos y el Sistema de Monitoreo de Sem` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 864894ac6d959a73701055809a765825120c9f844151d1544b3ef21bb7839b81 | pending |
| D18-21 | legis_pr_rc0787_resoluci_de | `RC0787 — Resolución de la Cámara: investigación sobre cámaras y sistemas de vigilancia con reconocimiento facial, biomét` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 46d2561053da262ca2f20a1c7602ce10c3aac8aedd3b719608a41a99febdbf75 | pending |
| D18-22 | legis_pr_rcs0198_resoluci_conjunta | `RCS0198 — Resolución Conjunta del Senado: requisito de cámaras de seguridad (videovigilancia) para licencias de venta de` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | 6ee9f56f8b42fd5a95b2f3a64e52ccc3797f2880633ceacbeadf392a01b82f39 | pending |
| D18-23 | legis_pr_rs0604_resoluci_del | `RS0604 — Resolución del Senado: investigación sobre cámaras y sistemas de vigilancia con reconocimiento facial, biométri` — a government portal source published by `Asamblea Legislativa de Puerto Rico (via SUTRA)`. | ce6a5f7500cd23c063995e0dede6851861546868b88880bf370044991096268e | pending |
| D18-24 | legis_pr_sistema_nico_de | `Sistema Único de Trámite Legislativo (SUTRA)` — a government portal source published by `Asamblea Legislativa de Puerto Rico — Oficina de Servicios Legislativos (host oslpr.org, attribution inferred)`. | bfee4ea00a54435485724134a53465366c3c9599e1ab9b261d044146e016af6e | pending |
| D18-25 | legis_tribal_tohono_oodham_notice | `Tohono O'odham Legislative Branch — public-hearing notice: Border Patrol LGDS + Automated Surveillance Tower proposals (Domestic Affairs Committee, 2025-11-19)` — a government portal source published by `Tohono O'odham Nation, Legislative Branch (Domestic Affairs Committee)`. | 70d9b52e9e2b3641cd80b44e470b254140785e83936919aa50a5aaa1a975514f | pending |

## Confirmation log

(none yet)
