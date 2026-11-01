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
| D19-01 | legis_us_dhs_sorn_plate_data | DHS System of Records Notices referencing license-plate-reader data (Federal Register document pages) — a government mandated disclosure source published by U.S. Department of Homeland Security (ICE, CBP) via the Federal Register. | 7c3217d819c25ed8b01cb2b6191ad8036751f8f25415e686549ae15ecb29897f | pending |
| D19-02 | legis_us_federal_register_api | Federal Register API (documents search: notices, rules, SORNs) — a government portal source published by Office of the Federal Register (NARA) / GPO. | aab5d32a457abda32d6f4a797fb680c8d1f0a69dc2b0c1546f98081224f42d30 | pending |
| D19-03 | legis_vi_legislature_virgin_islands | Legislature of the U.S. Virgin Islands press release: 'Committee advances bill to provide automatic license plate reader — a government portal source published by Legislature of the Virgin Islands (34th Legislature). | f3bfb7f266ffb4d2c2ba35733259c4c84db06bffc176a537c631f1457b1d2ec2 | pending |
| D19-04 | legistar | Legistar InSite API — a government portal source. | 87c5583d459d20920edcc6a1cd5db62a3316e0d8ec79ccd4c745ade1c1e9a823 | pending |
| D19-05 | madada | Ma Dada (FR CADA public-records platform) — a records channel source. | c6823dc8dd3a1e939115c264e2509bb4d73fd4c9038cf4d531419ad546934b70 | pending |
| D19-06 | monahan_grounding_the_flock | Monahan, "Grounding the Flock" (2026) — an academic source. | fcabb618e680b6acfa6189d4f1b207f6c4fa691f2d6eb21a2318a2d4d336aa7e | pending |
| D19-07 | muckrock | MuckRock — a records channel source. | c2f3d043b206459a17ffa176b13053fc16d55d95896d70aa059f6f799b25a982 | pending |
| D19-08 | muckrock_public | MuckRock public request pages — a records channel source. | a1d4e11a92770f8244513014d03d122b06cd284af854d9aad711985907078f52 | pending |
| D19-09 | naspo_valuepoint | NASPO ValuePoint — a government portal source. | f77b00f3ef813048eb579ddeabc77a9b617a75add8cc4ca658e8852f924fe67e | pending |
| D19-10 | natural_earth_10m | Natural Earth 10m (admin-0/admin-1 boundaries) — an upstream project source. | f16f70878295f0402eb2a4ec85db0368dde5f7c714b2494206bdd1ca0ea0a1a7 | pending |
| D19-11 | nces_ipeds_ntd_cms | NCES / IPEDS / NTD / CMS — a government portal source. | 682c91eef5404cbe72dcfb63bcf5b540946adafc3f38e3647fa9021adfa88b32 | pending |
| D19-12 | nextrequest | NextRequest — a records channel source. | 005b65b41160456b1ada4a2f015c1712a1dcfd6fde626f29e43b13c0c00e2726 | pending |
| D19-13 | novusagenda | NovusAgenda — a government portal source. | fe7263cde25d00a09d467e4c96c54c98b5a194be38c2d8b04a5b60cbfcf212a9 | pending |
| D19-14 | ok_dac_uved | Oklahoma District Attorneys Council — UVED program pages + OSCN statute (SRC-007) — a government portal source. | 5cb8125b8e9684035fc0145e9fae7476df06f74a1bfcdb7ebaefe92338df2a45 | pending |
| D19-15 | ok_omes_contracts | Oklahoma OMES — statewide contracts + solicitation channel (SRC-006) — a government portal source. | 14565e6f862811f0afebc95eed2de4aeb61c009ee1dd9222816739c06f9aec4a | pending |
| D19-16 | ok_statute | Oklahoma statutes (47 O.S. §7-606.1 et seq.) — a government portal source. | 73cae8fa995eb17a311bcab52290bb98a0403f59e8612b9174469afd87c16bea | pending |
| D19-17 | okc_council | Oklahoma City Council — agendas & minutes (CivicClerk) — a government portal source. | 16fc80173610ae557f0981ba58c9f7c2b7499c5f082e2c796d3dbebfc7fdeec6 | pending |
| D19-18 | okc_procurement | City of Oklahoma City — procurement / contracts — a government portal source. | 1b8ad725cdf6a7bd09f8cff9fd42f73039ef26bcf1d624c223f47a98e6f2f79a | pending |
| D19-19 | okcpd_policy | Oklahoma City Police Department — policy (Operations Manual) — a government portal source. | 57a77e8c9e8629f931f4b651b0295f83d7fb15e8aa1ad73c3a573656de52934d | pending |
| D19-20 | oklahoman | The Oklahoman (oklahoman.com) — a news publisher source. | dd0b1c1fa0b391c67b599f59bb31bb10c2b2c5270e1c223c5679a9379dad473f | pending |
| D19-21 | omnia_partners | OMNIA Partners — a government portal source. | e29e7fd6b67fe1bfffa52851274d9ecf59fedc13cd555df7009bcf760ccedd81 | pending |
| D19-22 | opengov_procurement | OpenGov Procurement — public agency solicitation portals — a government portal source. | 438ed29ba817d9c4bf5a5090171b6c412a5a952e45c15985a2e40f105bcb39f8 | pending |
| D19-23 | openstates | OpenStates — a government portal source. | ab5473116ac332d656088c782435ddfce75e192e8c5a7db3f8af5712fee976a0 | pending |
| D19-24 | osm_automated_edits_coc | OSM Automated Edits code of conduct — an upstream project source. | b332ba7eef3eeab7867c381264696a38120bc32a4d0b36c9ba9ac6833a5139de | pending |
| D19-25 | osm_copyright | OSM copyright / licence — an upstream project source. | f0039361558d641091981356c64c5c43ba8ff7208d96035f4e6be57f47e57941 | pending |

## Confirmation log

(none yet)
