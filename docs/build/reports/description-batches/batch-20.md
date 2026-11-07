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
| D20-01 | ok_dac_uved | `Oklahoma District Attorneys Council — UVED program pages + OSCN statute (SRC-007)` — a government portal source. | 6d7794f620369ee702c87c11e8f805067c3b93d36a7bca84e5cca8f7c50b16fb | pending |
| D20-02 | ok_omes_contracts | `Oklahoma OMES — statewide contracts + solicitation channel (SRC-006)` — a government portal source. | 7fd283cbfc4254d26da041c1a7e9c92f2f197f31503c4c254659cc8723418c0c | pending |
| D20-03 | ok_statute | `Oklahoma statutes (47 O.S. §7-606.1 et seq.)` — a government portal source. | 72c2e049419e1d3738d52cdfc1c0c911c895a9cdd4e44342c3b9876fbf71634d | pending |
| D20-04 | okc_council | `Oklahoma City Council — agendas & minutes (CivicClerk)` — a government portal source. | f6488639354c10d1a8e411b066d94fd8c4d854d2f1a32e25c78f902419afedd3 | pending |
| D20-05 | okc_procurement | `City of Oklahoma City — procurement / contracts` — a government portal source. | d44377f3341e39332ccc60ac1d6ebaeac4a9a691e2ee865ded11a55a37e1c384 | pending |
| D20-06 | okcpd_policy | `Oklahoma City Police Department — policy (Operations Manual)` — a government portal source. | 82898cdfff552a3c67e95c2faffcfc8c848b8be3bf71cafc93b0ba71a8007385 | pending |
| D20-07 | oklahoman | `The Oklahoman (oklahoman.com)` — a news publisher source. | 5455c971e6efb05256dd03cec3d4541e76bb1110c1648eb2ec236daafef88163 | pending |
| D20-08 | omnia_partners | `OMNIA Partners` — a government portal source. | 0640c2458b7d39495ab8c887999d91f4faca79f2590fc6d12c50119bed2b2b14 | pending |
| D20-09 | opengov_procurement | `OpenGov Procurement — public agency solicitation portals` — a government portal source. | 768b13f13325ddd9da238efcc049de76416f3521bd0a0d33228bc1d37feb734d | pending |
| D20-10 | openstates | `OpenStates` — a government portal source. | f4266e2ccb812c2a068d7dad877d0cf0b3684755b955d0a6435771ca659e7462 | pending |
| D20-11 | osm_automated_edits_coc | `OSM Automated Edits code of conduct` — an upstream project source. | 0cc05818441a35cc176ec92ee26e22274cee0bead7f31105b3a79d467eb98040 | pending |
| D20-12 | osm_copyright | `OSM copyright / licence` — an upstream project source. | a3074a8c79c1d2769dd5e5a34a1efeeb0d8ba93bd6ee6b720bd411103efef5bf | pending |
| D20-13 | osm_element_history | `OSM element history` — an upstream project source. | 712a9bbfcc2b29e802a08eefa617d0dd5dd7edddde8b7011fe9d4a54a7c10414 | pending |
| D20-14 | osm_overpass | `OSM Overpass API` — an upstream project source. | dbd09997496078ebacf5e4a54a99cd33621fc44be0b93ac8711f10c0f6eed377 | pending |
| D20-15 | osm_replication | `OSM replication diffs` — an upstream project source. | f1e7943a5d7a7010a238fbfe712319e53e363616facfdd6e59a956995fd2dc40 | pending |
| D20-16 | osm_surveillance_tagging | `OSM surveillance tagging (Tag:man_made=surveillance)` — an upstream project source. | 79799ac440d14ce0875580301fbd38f261a58b4fc4e3515ae64f2d2c2400ae09 | pending |
| D20-17 | osm_taginfo | `OSM taginfo API` — an upstream project source. | 07562b8574f77625b01ce4820760e145b240f07d5d5eec8827ea6f2857e96432 | pending |
| D20-18 | osmf_licence_guidelines | `OSMF Licence Community Guidelines` — an upstream project source. | 73fe3408749dbadd8302455ef4b03e8bf76b00c4d3b46eb89f22d684d9db6ddc | pending |
| D20-19 | panopti_ca | `resistanceisliberty/panopti.ca` — an upstream project source. | fb5840b70986acbd1b6f9717f73dd7f59f8a566435dd0d4f184dd71e43682bc2 | pending |
| D20-20 | panopticity | `PanoptiCity` — a community source. | fdde29c29b768b037fd31ad46a88ec78a74ffd39517048c1c0bf6f4b610039e7 | pending |
| D20-21 | pathways_acoustic_drone_location | `Acoustic / drone / commercial-location procurement & policy (Stage-5 pathway)` — a government portal source. | 5426d4e0003902fdaa838aa0cadde19eaa5607402da3d683f41ae0745d906d81 | pending |
| D20-22 | pathways_fr_css_forensics | `FR / cell-site-simulator / mobile-forensics procurement & policy (Stage-5 pathway)` — a government portal source. | 80eeb79c9aeaed30495a7ae6017fb11421ff3fd33a98153d4edd7c320c28cb10 | pending |
| D20-23 | pathways_rtcc_federation | `Municipal RTCC / private-camera federation disclosures (Stage-5 pathway)` — a government portal source. | addc092eab60e908d2ed050f9b704fc0ccacdbcba450db01e4bbfa8612b6b33a | pending |
| D20-24 | periscope_s2g | `Periscope S2G — eBid procurement portals` — a government portal source. | 02ab0b31ae04cb3227d0f6d70dc2ad352ab69128fca2693a33ebc44564a98d4a | pending |
| D20-25 | planetbids | `PlanetBids — public agency procurement portals` — a government portal source. | 3b602467e31c03ba769bd2d567cc9a23ecf25b36a7f6f2a5a56eec64fca3e93b | pending |

## Confirmation log

(none yet)
