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
| D14-01 | ccops_ok_tulsa_flock_policies | Tulsa Flock policies integration and executed contract search — a government portal source published by City of Tulsa / Tulsa Police Department. | b6b63ec593333e748de8f89db75aecd68eca2cc7a6717886ce4fe172c7578d56 | pending |
| D14-02 | ccops_ordinance_disclosures | Municipal surveillance-ordinance (CCOPS) disclosures — a government mandated disclosure source. | d62ffa66e33a1c83f02fcb851e5177270dfcca596e379af0651a57da03f19efc | pending |
| D14-03 | ccops_ri_narragansett_police_camera | Narragansett Police camera registry programme - 'Polaris - CameraKit - FAQs' (Dec 2022) — a government portal source published by Town of Narragansett, RI Police Department. | 8ea5366bbc3242e00f757062682802793a72b17ff877453f9bb540b91ca45447 | pending |
| D14-04 | ccops_san_diego_ca | San Diego technology inventory and annual reports — a government portal source published by City of San Diego (SDPD). | f3dc0d0c1164b9a50cf55b3b16b95c6d7b460af65fa5daf5d115cb77bede232c | pending |
| D14-05 | ccops_san_francisco_bay_ca | BART surveillance reports policies and public decisions — a government portal source published by San Francisco Bay Area Rapid Transit District (BART). | ff6f9a222b73a7e9795075dcad70c3cd1b08dedb3e466d420d0b62b7e18d2938 | pending |
| D14-06 | ccops_san_jose_ca | San Jose privacy decisions and algorithm register — a government portal source published by City of San José (Digital Privacy / IT). | 17366bdb1e0a7da48720cd1cdbfe2db3bdd7849fc35d915650d5e15d56e9c5dd | pending |
| D14-07 | ccops_santa_clara_county_ca | Santa Clara County surveillance impact and oversight — a government portal source published by Santa Clara County (privacy/oversight office). | 979d25f08f226c6cc5c599e2269bc904241f9e73470eadc055e1a9ae56d3ff0f | pending |
| D14-08 | ccops_seattle | Seattle Surveillance Ordinance disclosures (SMC 14.18 — Master List, SIRs, quarterly determination reports) — a government mandated disclosure source. | 518e80dfb1fd3bdb2a3491bdf4128f457eba60559728e7dcf5dc6c5acf5b4595 | pending |
| D14-09 | ccops_sf | San Francisco Chapter 19B biannual surveillance technology inventory — a government mandated disclosure source. | 36441b06c0cf4fa7e898de7f96d3e2792315fc9c83f89152b5a8ede4c05fb7f8 | pending |
| D14-10 | ccops_si_085_novo_mesto_evidenca_o | Evidenca o izvajanju videonadzora na javnih površinah v Mestni občini Novo mesto — a government portal source published by Mestna občina Novo mesto. | eee38f690dcd1c15dd7347afa874badd5dc7c73c9e7f8a1ad8f019429343153d | pending |
| D14-11 | ccops_somerville | CCOPS Somerville — surveillance oversight disclosures — a government mandated disclosure source. | 1a9718cc3902523ad005983d249a1373ad701bbb7e97ea3165c7645cc6cc70da | pending |
| D14-12 | ccops_st_louis_mo | City of St. Louis: Police Department Surveillance Technology Reports (Ordinance 71842; Executive Order 78) — a government mandated disclosure source published by Metropolitan St. Louis Police Department / City of St. Louis, MO. | 3900cc665814c42ed89550d1edcc5b4919258d32bf967c7445df24e2bf38d43f | pending |
| D14-13 | census_gazetteer_tiger | Census Gazetteer / TIGER — a government portal source. | ee36a4b02e90a485158e116630a2a1daa0d5c50be4836382f95b66d375aa91da | pending |
| D14-14 | census_geocoder | Census Geocoder — a government portal source. | 9731ca22d673d69cb20dea6f83aa928d4830cfe94bea318dcd68dee9cfa3a2be | pending |
| D14-15 | civicclerk | CivicClerk — a government portal source. | e9a01f654ff6e4155f1ff618a2bef43ab62141a060ff53f493a5823cac6615c3 | pending |
| D14-16 | civicplus | CivicPlus — a government portal source. | cf67af5d7be10e36d63868247836c1088f06d7fbf3599390d6bcac846441ad87 | pending |
| D14-17 | congress_gov | Congress.gov API (Library of Congress) — a government portal source. | 45795b82ed5eca5a0524f891793737638ff8308a20ce775ca8deccf773769ded | pending |
| D14-18 | courtlistener_recap | CourtListener / RECAP — a court system source. | 08aab28f3661d817d233eb1fb34ca8857b644fe8a4d7a630a20fb2d043960565 | pending |
| D14-19 | declarationcamera_be | declarationcamera.be (BE national camera register) — a government portal source. | c314b038abb3917266452bfad122cd1d2f84de765ec3e82161463c1be4a33a86 | pending |
| D14-20 | decp_fr | DECP (FR procurement) — a government portal source. | 9b7c4becb0b14dfabcf85a5231ca44298c1bb72c1afbd32f23c1959846d288b7 | pending |
| D14-21 | deflock | DeFlock — an upstream project source. | 5244055d2e972458396d8a9eb36d0ded704368654882a2a267e204bdee304b2c | pending |
| D14-22 | deflock_app_repo | DeFlock — app repo (FoggedLens/deflock-app) — an upstream project source. | 638f22d6dfec836078a2aa654116e2fb97231522c77d5290711e01c224695665 | pending |
| D14-23 | deflock_repo | DeFlock — canonical repo (FoggedLens/deflock) — an upstream project source. | fcedc6783a91998e426581a411573e004003da9bb112978af52050974a916730 | pending |
| D14-24 | demandstar | DemandStar — public agency bid portal — a government portal source. | c6d22b263c3174ee1d3008d458019307f51d80f3b5844ab9b0d8266a5a2905a7 | pending |
| D14-25 | denmark_politi_cctv | Denmark National Police — official CCTV camera map — a government portal source. | 577811bc840ada3a490725f6ba1ab214a28e0e40b763603c50554a69caa9db8a | pending |

## Confirmation log

(none yet)
