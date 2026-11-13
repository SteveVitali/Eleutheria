# Description batch 14 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D14-01 | ccops_oh_cincinnati_police_department | `Cincinnati Police Department - voluntary community camera registry (Axon Fusus 'Real-Time Crime Center in the Cloud')` — a government portal source published by `City of Cincinnati, OH Police Department`. | 0af702d43b18bcd542c8221cf3f00d76615b73e661958e60927dccc39e28c9d2 | pending |
| D14-02 | ccops_ok_oklahoma_city_okc_flock_council | `OKC Flock council amendment policy packet` — a government portal source published by `City of Oklahoma City`. | 56610974836db5019837d90010e5417be92b9f05925392b43c0e339abbaf267f | pending |
| D14-03 | ccops_ok_tulsa_flock_policies | `Tulsa Flock policies integration and executed contract search` — a government portal source published by `City of Tulsa / Tulsa Police Department`. | 3434867d935b42a63c34571bb972bf32d419c6f0c00e3710b5803663a2bd6a7b | pending |
| D14-04 | ccops_ordinance_disclosures | `Municipal surveillance-ordinance (CCOPS) disclosures` — a government mandated disclosure source. | eea7c23bbe45f8dbc56e20d4730e36a3c04a02434dd6d91b6e3e58815828657f | pending |
| D14-05 | ccops_ri_narragansett_police_camera | `Narragansett Police camera registry programme - 'Polaris - CameraKit - FAQs' (Dec 2022)` — a government portal source published by `Town of Narragansett, RI Police Department`. | 85cd79438e7f78c1b0075d953e169b607782244f9fada88389bbafda5d98c17e | pending |
| D14-06 | ccops_san_diego_ca | `San Diego technology inventory and annual reports` — a government portal source published by `City of San Diego (SDPD)`. | 6056961987f135b0024405ebb9e3e2d7818365255ab68b734786b7e597bb2abb | pending |
| D14-07 | ccops_san_francisco_bay_ca | `BART surveillance reports policies and public decisions` — a government portal source published by `San Francisco Bay Area Rapid Transit District (BART)`. | 8ccad47215e2a96caa9210de3b3365edea23aad5e72da2507b27404f2ce64f3e | pending |
| D14-08 | ccops_san_jose_ca | `San Jose privacy decisions and algorithm register` — a government portal source published by `City of San José (Digital Privacy / IT)`. | a6df7e1d2d982457410015510ad1a3c840cb6131c199dc1f1c06cb1720978acb | pending |
| D14-09 | ccops_santa_clara_county_ca | `Santa Clara County surveillance impact and oversight` — a government portal source published by `Santa Clara County (privacy/oversight office)`. | 5e4a660e6575e9231b9f2aa650591cd5d475ec3de0c353df750e23eceb7c8d91 | pending |
| D14-10 | ccops_seattle | `Seattle Surveillance Ordinance disclosures (SMC 14.18 — Master List, SIRs, quarterly determination reports)` — a government mandated disclosure source. | 530a237be974bf06dcce5cf8e27bdc9a92990caca7983802440cf9352894cb80 | pending |
| D14-11 | ccops_sf | `San Francisco Chapter 19B biannual surveillance technology inventory` — a government mandated disclosure source. | 15f5dbddc78f7019513b0bc97cd8572da5869baeca892cbec4597219402fefa7 | pending |
| D14-12 | ccops_si_085_novo_mesto_evidenca_o | `Evidenca o izvajanju videonadzora na javnih površinah v Mestni občini Novo mesto` — a government portal source published by `Mestna občina Novo mesto`. | 4fbdd0a47b663fc4f020b6f97fd3b581e47a660bddb504f1e02da1480cfc235b | pending |
| D14-13 | ccops_somerville | `CCOPS Somerville — surveillance oversight disclosures` — a government mandated disclosure source. | 1c5f719c4b20df0c6ba6b4dd5812fedbe538aabd8135e79853413147a25cdec4 | pending |
| D14-14 | ccops_st_louis_mo | `City of St. Louis: Police Department Surveillance Technology Reports (Ordinance 71842, Executive Order 78)` — a government mandated disclosure source published by `Metropolitan St. Louis Police Department / City of St. Louis, MO`. | e02fb4c22ed5abbaa4f5483daff16ab4e17e99b028310b76f3d615efdf4a009e | pending |
| D14-15 | census_gazetteer_tiger | `Census Gazetteer / TIGER` — a government portal source. | 42842eead67fb5979a149903841de19a1e42c6aefd44e2090d0c8ccd9cd55e01 | pending |
| D14-16 | census_geocoder | `Census Geocoder` — a government portal source. | 73fbdb213051147d7df9f7d7773a5992f776aca9e00445a1d9ccef20ff5d118c | pending |
| D14-17 | census_of_governments | `Census of Governments` — a government portal source. | 38bb6efc9afbd6e9f4f985fad55f63dbe46663437dc4c45afd0cf9d77880bbc3 | pending |
| D14-18 | civicclerk | `CivicClerk` — a government portal source. | 807a07a75d4a6fe3b3fa079873cf47b53babb0af983ab1db7ad30774076d966c | pending |
| D14-19 | civicplus | `CivicPlus` — a government portal source. | f440d5378d660f3996f6bfa1a95de18ca15648d51d10ab9bf9890d5af6d85cbf | pending |
| D14-20 | congress_gov | `Congress.gov API (Library of Congress)` — a government portal source. | de314fe6b67ecf516631ae8167c90498098328ef97d9c3a23b741cf5a03892fa | pending |
| D14-21 | courtlistener_recap | `CourtListener / RECAP` — a court system source. | d37705b7d1693bb6df9e9796eca610031658392e51c8ade6f91d947a90bdb271 | pending |
| D14-22 | datalib_aaron_swartz_day | `Aaron Swartz Day Police Surveillance Project (crowdsourced public-records campaign corpus)` — a community source published by `Aaron Swartz Day and International Hackathon`. | e3c7a56be10728129ebe88c714778e7444c89190e09babd97f0f162a5a9a253d | pending |
| D14-23 | datalib_atlas_border_communities | `Atlas of Surveillance: Border Communities (EFF — surveillance in the 23 US counties on the Mexico border)` — an upstream project source published by `Electronic Frontier Foundation`. | b7d9a9178a311032ff155554a8acfbbe60a8453775c034c019354102fccb8f55 | pending |
| D14-24 | datalib_clearview_ai_table | `Clearview AI Table (BuzzFeed News — entities whose employees ran Clearview facial-recognition searches)` — a news publisher source published by `BuzzFeed News`. | bd384a1807b6de1a17bd6576935787c093da2547a74ceb2b2caadababfc12526 | pending |
| D14-25 | datalib_federally_funded_bwc | `Federally Funded Body-Worn Cameras (EFF-compiled — DOJ/BJA grant-recipient agencies)` — an upstream project source published by `Electronic Frontier Foundation (upstream: US DOJ Bureau of Justice Assistance)`. | 56148884aa20f316ab9e6f0ab8a5e83f83669e01954894f6ca3d5f41039c413b | pending |

## Confirmation log

(none yet)
