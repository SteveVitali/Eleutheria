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
| D19-01 | legis_us_dhs_sorn_plate_data | `DHS System of Records Notices referencing license-plate-reader data (Federal Register document pages)` — a government mandated disclosure source published by `U.S. Department of Homeland Security (ICE, CBP) via the Federal Register`. | 29b3a3aaea95a8b4b905c540b7ff6b6ac800ac2485a47d5cd013fc2839e56729 | pending |
| D19-02 | legis_us_federal_register_api | `Federal Register API (documents search: notices, rules, SORNs)` — a government portal source published by `Office of the Federal Register (NARA) / GPO`. | 191f80c9c04093b129577018642eec9eefd60fb64903c32b0946f1d9991fa8b5 | pending |
| D19-03 | legis_vi_legislature_virgin_islands | `Legislature of the U.S. Virgin Islands press release: 'Committee advances bill to provide automatic license plate reader` — a government portal source published by `Legislature of the Virgin Islands (34th Legislature)`. | 6cbbe7d27e6523531e766d52947ef1f67e8d64bb6491299673cb602ce1af854e | pending |
| D19-04 | legistar | `Legistar InSite API` — a government portal source. | 464bcaa5ea573d257b34fdae6666f3008aa3a8a949d963d5969f67d7127b3124 | pending |
| D19-05 | madada | `Ma Dada (FR CADA public-records platform)` — a records channel source. | ee9a0c3956e14bc662acc82983e984b24002f24aabacf85f7e990e7eca5822c9 | pending |
| D19-06 | monahan_grounding_the_flock | `Monahan, "Grounding the Flock" (2026)` — an academic source. | c42ce3c21a8974d08113f9675c05986734c037226af7265ebe23695bf7d8b828 | pending |
| D19-07 | muckrock | `MuckRock` — a records channel source. | 4cde184ff3fc51e576db797943e848cfe58fdde3b7238020d9274df8521a3885 | pending |
| D19-08 | muckrock_public | `MuckRock public request pages` — a records channel source. | a8640e5f93c85408144046542adfc444031f891f6dd25e6a2c80d4f6f5f11589 | pending |
| D19-09 | naspo_valuepoint | `NASPO ValuePoint` — a government portal source. | 7b80d9bfedc37ca660422a776e4efee7f98214acd2338b9068ef935d35e7566f | pending |
| D19-10 | natural_earth_10m | `Natural Earth 10m (admin-0/admin-1 boundaries)` — an upstream project source. | cdd9c40418b09d956e70280bfbcc910dcb149c83ecf2bebd0212a7e986c37eb6 | pending |
| D19-11 | nces_ipeds_ntd_cms | `NCES / IPEDS / NTD / CMS` — a government portal source. | 9975abe2a824037040f4eafc1798b1822796e16fe61ebc29bf7c5aea1c844911 | pending |
| D19-12 | nextrequest | `NextRequest` — a records channel source. | e649baa957350fafaead422b9c8f40f08b6437a64f6a077764b530c9b870880f | pending |
| D19-13 | novusagenda | `NovusAgenda` — a government portal source. | cf4374dfd9b644a5513646e24c33a5602c8e922c9d70884338a696b8363a3c4d | pending |
| D19-14 | ok_dac_uved | `Oklahoma District Attorneys Council — UVED program pages + OSCN statute (SRC-007)` — a government portal source. | 6d7794f620369ee702c87c11e8f805067c3b93d36a7bca84e5cca8f7c50b16fb | pending |
| D19-15 | ok_omes_contracts | `Oklahoma OMES — statewide contracts + solicitation channel (SRC-006)` — a government portal source. | 7fd283cbfc4254d26da041c1a7e9c92f2f197f31503c4c254659cc8723418c0c | pending |
| D19-16 | ok_statute | `Oklahoma statutes (47 O.S. §7-606.1 et seq.)` — a government portal source. | 72c2e049419e1d3738d52cdfc1c0c911c895a9cdd4e44342c3b9876fbf71634d | pending |
| D19-17 | okc_council | `Oklahoma City Council — agendas & minutes (CivicClerk)` — a government portal source. | f6488639354c10d1a8e411b066d94fd8c4d854d2f1a32e25c78f902419afedd3 | pending |
| D19-18 | okc_procurement | `City of Oklahoma City — procurement / contracts` — a government portal source. | d44377f3341e39332ccc60ac1d6ebaeac4a9a691e2ee865ded11a55a37e1c384 | pending |
| D19-19 | okcpd_policy | `Oklahoma City Police Department — policy (Operations Manual)` — a government portal source. | 82898cdfff552a3c67e95c2faffcfc8c848b8be3bf71cafc93b0ba71a8007385 | pending |
| D19-20 | oklahoman | `The Oklahoman (oklahoman.com)` — a news publisher source. | 5455c971e6efb05256dd03cec3d4541e76bb1110c1648eb2ec236daafef88163 | pending |
| D19-21 | omnia_partners | `OMNIA Partners` — a government portal source. | 0640c2458b7d39495ab8c887999d91f4faca79f2590fc6d12c50119bed2b2b14 | pending |
| D19-22 | opengov_procurement | `OpenGov Procurement — public agency solicitation portals` — a government portal source. | 768b13f13325ddd9da238efcc049de76416f3521bd0a0d33228bc1d37feb734d | pending |
| D19-23 | openstates | `OpenStates` — a government portal source. | f4266e2ccb812c2a068d7dad877d0cf0b3684755b955d0a6435771ca659e7462 | pending |
| D19-24 | osm_automated_edits_coc | `OSM Automated Edits code of conduct` — an upstream project source. | 0cc05818441a35cc176ec92ee26e22274cee0bead7f31105b3a79d467eb98040 | pending |
| D19-25 | osm_copyright | `OSM copyright / licence` — an upstream project source. | a3074a8c79c1d2769dd5e5a34a1efeeb0d8ba93bd6ee6b720bd411103efef5bf | pending |

## Confirmation log

(none yet)
