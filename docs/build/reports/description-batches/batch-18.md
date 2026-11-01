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
| D18-01 | grant_us_doj_cops_technology | DOJ COPS technology/equipment award documents — a government portal source published by U.S. DOJ Office of Community Oriented Policing Services (COPS). | cb7ee722ab58927203d51b2ca65784da3189dd0b2d75501606248e4913befc68 | pending |
| D18-02 | gsa | GSA — a government portal source. | ef2a7e4ac82118b50640421916d5b8a97ea4bebc3d69467ee3471fefbc5d74a4 | pending |
| D18-03 | guardian_flock_cameras | Guardian, Flock cameras (2026-08-20) — a news publisher source. | 8e8d6e3e2e12b1ac70bd2d54db05c140be0ce9ec677ed1b96fee8a3ec41d38d3 | pending |
| D18-04 | have_i_been_flocked | Have I Been Flocked — an upstream project source. | deb36af52137d3a9fb038c2adf1b7e05c11dde0651d34c78aa4f9ae2b7fa43b3 | pending |
| D18-05 | hgacbuy | HGACBuy — a government portal source. | d4ee48fd148bf90f74b47cc4515a8ce41ab53dbbf68cda2b942e8d62ad20f726 | pending |
| D18-06 | hibf_audit_log_guide | HIBF audit-log guide — an upstream project source. | 693f0baa490e13bbdfeabb8addcc2090381fcda5352c2036453a6500b7461063 | pending |
| D18-07 | hibf_methodology | HIBF methodology hub — an upstream project source. | c8bf6006c04738efe52a8e90daaa095a1bf51bf64f9fb822ac47178391264aa0 | pending |
| D18-08 | internet_archive_wayback | Internet Archive Wayback — an upstream project source. | 6e8ac89a6720401e18901520f5f919f6f7a459bb7b0c1088e8602f7afd8ac360 | pending |
| D18-09 | iqm2 | IQM2 — a government portal source. | 57b9d01073748a32af0b141b4f02b8f0eb064caf502dcef20fa4ffd332a3bd6c | pending |
| D18-10 | journalrecord | The Journal Record (Oklahoma City) — a news publisher source. | b6c140b5225b5a01f80c1a8a46878fa05380d208b1fd64be844ae8269e1cadd7 | pending |
| D18-11 | justfoia | JustFOIA — a records channel source. | ae7af113d288967ce6a321526af88da0ba56b8089bc42fd91fc32dac8a852161 | pending |
| D18-12 | la_city_clerk_cfms | LA City Clerk Connect (CFMS) — Los Angeles City legislative file management — a records channel source. | 201123b1c81ca064a40f68e544f91a188dad5e5eda32c0a2148279f61028c4bd | pending |
| D18-13 | la_quadrature_du_net | La Quadrature du Net — a news publisher source. | e0b058ccd208121147bd5a7002864e902b1023b118a0595954d95c78aa09aa07 | pending |
| D18-14 | leaic_crosswalk | LEAIC crosswalk (ICPSR study 35158) — an academic source. | 5dd8a1ab8f8a6544850ddd2e0e214d3892e2883a4d47b040a1abc7a0d072991e | pending |
| D18-15 | legis_ca_gov_code_53166 | California Government Code § 53166 - cellular communications interception technology usage and privacy policies and acqu — a government portal source published by California Legislature. | 1462289f7b4d94a35552615d0a34548ad952b01bdccd6f47ab09121d9a97a531 | pending |
| D18-16 | legis_gu_governor | Governor of Guam press release: 'Bill for GPD Security Cameras now Law' (Bill 132-35, the Governor's alternative to Bill — a government portal source published by Office of the Governor of Guam. | cfbec2bf02d27cc871a397f5420874fa5ea528adc33671690d85e26c34ec6f39 | pending |
| D18-17 | legis_ie_rs_general_scheme | L&RS General Scheme Briefing Paper: Garda Síochána (Recording Devices) (Amendment) Bill — a government portal source published by Houses of the Oireachtas Library & Research Service. | e4603061c3476c83823a66be9c7cb78caadf246c802ced8268af201e534b63dd | pending |
| D18-18 | legis_pr_pc0489_ley_del | PC0489 — Ley del Programa de Vigilancia, Prevención y Protección de Menores (supervisión electrónica como condición de f — a government portal source published by Asamblea Legislativa de Puerto Rico (via SUTRA). | 2e0b30393dd6ce965d6d53d05ece312ab1bcd2ac61ada91185dce1b7c2347f70 | pending |
| D18-19 | legis_pr_pc0560_plan_de | PC0560 — Plan de Vigilancia de las Costas, Puertos y Aeropuertos — a government portal source published by Asamblea Legislativa de Puerto Rico (via SUTRA). | 7fb284c42edd77500182bc8392aa61b9a81d6b2465fb8883182209c0f9dda557 | pending |
| D18-20 | legis_pr_rc0740_investigaci_sobre | RC0740 — investigación sobre cámaras de vigilancia o monitoreo de tránsito en semáforos y el Sistema de Monitoreo de Sem — a government portal source published by Asamblea Legislativa de Puerto Rico (via SUTRA). | cd47217accaf7a0ae60a9698067605492f73428fde89f569040a0965c19705a7 | pending |
| D18-21 | legis_pr_rc0787_resoluci_de | RC0787 — Resolución de la Cámara: investigación sobre cámaras y sistemas de vigilancia con reconocimiento facial, biomét — a government portal source published by Asamblea Legislativa de Puerto Rico (via SUTRA). | cdd80f0ed527e6e7911197458ad9e63660fc29cf4df2986a44f6875cc1ff046f | pending |
| D18-22 | legis_pr_rcs0198_resoluci_conjunta | RCS0198 — Resolución Conjunta del Senado: requisito de cámaras de seguridad (videovigilancia) para licencias de venta de — a government portal source published by Asamblea Legislativa de Puerto Rico (via SUTRA). | 296af3fdfe643e127a067f340cf36305d146055aff606ea21a3398b93193b263 | pending |
| D18-23 | legis_pr_rs0604_resoluci_del | RS0604 — Resolución del Senado: investigación sobre cámaras y sistemas de vigilancia con reconocimiento facial, biométri — a government portal source published by Asamblea Legislativa de Puerto Rico (via SUTRA). | 720a43c4bcc370ab77bd4fcfd49ed01b3be02d12b792a603cc81d65cb747e204 | pending |
| D18-24 | legis_pr_sistema_nico_de | Sistema Único de Trámite Legislativo (SUTRA) — a government portal source published by Asamblea Legislativa de Puerto Rico — Oficina de Servicios Legislativos (host oslpr.org; attribution inferred). | c47e11e4ed06e32a872057148404e6ab5dcf05eb9a6dca9567aebd9431858b00 | pending |
| D18-25 | legis_tribal_tohono_oodham_notice | Tohono O'odham Legislative Branch — public-hearing notice: Border Patrol LGDS + Automated Surveillance Tower proposals (Domestic Affairs Committee, 2025-11-19) — a government portal source published by Tohono O'odham Nation, Legislative Branch (Domestic Affairs Committee). | e94f216da72f7fad3098fe515bb4044534fdc956944e0d71eec7bb959afa0ffc | pending |

## Confirmation log

(none yet)
