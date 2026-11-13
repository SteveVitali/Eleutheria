# Description batch 13 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D13-01 | ccops_baltimore | `CCOPS Baltimore — surveillance ordinance disclosures` — a government mandated disclosure source. | d324aa54e9a1af923fd82d812f84aaeafe4062f66d95d4e9982b6f346a3b96d8 | pending |
| D13-02 | ccops_berkeley | `CCOPS Berkeley — Surveillance Technology Use ordinance disclosures` — a government mandated disclosure source. | 83eb683cea1327fc28abc81ece9184863c136f49210591f4b89b6289857968c7 | pending |
| D13-03 | ccops_boston | `CCOPS Boston — surveillance oversight ordinance disclosures` — a government mandated disclosure source. | 8b2b24923d60ac54a4c78c8c857ad47eb6f49d7175b70ba2a1daf0d9e242afaa | pending |
| D13-04 | ccops_ca_calistoga_police_department | `Calistoga Police Department Voluntary Security Camera Registry` — a government portal source published by `City of Calistoga, CA Police Department`. | 6e02fdd1b98cf8548a7fdd3106c54c44f75efe200270bc45c28ca143025a1f36 | pending |
| D13-05 | ccops_ca_pinole_police_department | `Pinole Police Department Security Camera Registry` — a government portal source published by `City of Pinole, CA Police Department`. | bf14f4109edbebecfc8879b94ffddaa31ebbecf29e62b3942b128ac1f69bc77c | pending |
| D13-06 | ccops_ca_san_diego_privacy_advisory | `San Diego Privacy Advisory Board recommendations` — a government portal source published by `City of San Diego Privacy Advisory Board`. | d45a2b908ecf683f4871e4c0ba8ea6b5ff7c0912bcfb48652871e630a24515b3 | pending |
| D13-07 | ccops_ca_san_diego_sunshine_act_goods | `San Diego Sunshine Act goods/services contracts` — a government portal source published by `City of San Diego (Purchasing / contracts)`. | 29d47497706aa9c2d3e00c8d3b0d31ca6935b4041e2cbde415b19040b19ae42d | pending |
| D13-08 | ccops_cambridge | `CCOPS Cambridge MA — surveillance oversight ordinance disclosures` — a government mandated disclosure source. | a761fcdf2c99295fd838f2ea8234ca6f63dfcbba8c8ed14b79f27b4fc16daa29 | pending |
| D13-09 | ccops_columbia_mo | `City of Columbia MO: 2025 Annual Surveillance Technology Report (Law Enforcement Surveillance Oversight Ordinance)` — a government mandated disclosure source published by `City of Columbia, MO (Columbia Police Department)`. | 4513b5f8d0ba2ec2ba791be337c50c10aaac7169a744b7491e94794486bb74f4 | pending |
| D13-10 | ccops_davis | `CCOPS Davis — surveillance technology ordinance disclosures` — a government mandated disclosure source. | dcb90434d8acaf05b525f8abef6e76675935cbeee00b15da85f95fb0a533c497 | pending |
| D13-11 | ccops_dayton_oh | `City of Dayton OH: Surveillance Technology (annual reports, use policies, notifications)` — a government mandated disclosure source published by `City of Dayton, OH (Dayton Police Department)`. | 9455066a6d1eae354547f057872ce90d69550be47d02ca82bb98831822620dbc | pending |
| D13-12 | ccops_gb_eng_barnet_traffic_cctv | `Traffic CCTV contract` — a government portal source published by `London Borough of Barnet`. | 7081c8d3bed0a132c14081734d7608908ddceca7c0c28e562e90e5a3ac1e4423 | pending |
| D13-13 | ccops_grand_rapids | `CCOPS Grand Rapids — surveillance ordinance disclosures` — a government mandated disclosure source. | 3d833efa5d88e5f8efd3956b6c3531e290b0da659f39cddd227d5e0451569d37 | pending |
| D13-14 | ccops_hi_honolulu_police_department | `Honolulu Police Department policy - Automated License Plate Reader` — a government portal source published by `Honolulu Police Department`. | 989a007efb4ef7cb508e0707926bfabe6e742b4221d5bbed3c1013420a3ae5a4 | pending |
| D13-15 | ccops_il_chicago_oig_shotspotter | `Chicago OIG ShotSpotter evaluation and follow-up` — a government portal source published by `Chicago Office of Inspector General`. | ebabe01055021b4255e19ed453a609dffc64a430c06dbc3ad9730b5dcf9a592d | pending |
| D13-16 | ccops_iso_au_privacy_commissioner | `Privacy Commissioner publishes updated guidance on facial recognition in retail spaces` — a government portal source published by `Office of the Australian Information Commissioner`. | dc2fe71d6d8f5520e07b838f95a9a1cf470ca243a6c377b8fcd5ac82b3fe4eea | pending |
| D13-17 | ccops_it_tn_trento_provvedimento_dell_11 | `Provvedimento dell'11 gennaio 2024 [9977020] (Comune di Trento — Marvel/Protector/Precrisis)` — a government portal source published by `Garante per la protezione dei dati personali (Italy)`. | d0c55ab9b71b2608049b36633e6ca512ab93aa37b2ec6e57ffabcf940033113d | pending |
| D13-18 | ccops_mi_wayne_county_commission | `Wayne County Commission — committee meeting pages (incl. Public Safety, Judiciary & Homeland Security)` — a government portal source published by `Wayne County Commission, Michigan (Granicus OpenCities CMS)`. | a31eb4a4ad1a7f31d914358e19e0754924096315c36d8088fa9177846936c8ec | pending |
| D13-19 | ccops_mn_dayton_police_department | `Dayton (MN) Police Department Resident Camera Registry` — a government portal source published by `City of Dayton, MN Police Department`. | fb7240472b59ec63e51df5960b24494d23b6349063004f64f8496c0b12397d80 | pending |
| D13-20 | ccops_mo_st_louis_fy21_spi_shotspotter | `FY21 - SPI ShotSpotter Expansion Evaluation - Final Report (St. Louis Metropolitan Police Department)` — an academic source published by `Southern Illinois University Edwardsville (with SLMPD), BJA-funded`. | 30363ee7178ab8fdaecb057e989676695aacd9b2c260c6a18c2be02093734fc3 | pending |
| D13-21 | ccops_nashville | `CCOPS Nashville — Metro surveillance ordinance disclosures` — a government mandated disclosure source. | c37410d8a4ca9e4074617766ef7ee51e050fe9bebcc937a1c58ac315f020eef6 | pending |
| D13-22 | ccops_nc_charlotte_mecklenburg_police | `Charlotte-Mecklenburg Police Department - Interactive Directives Guide (compiled directives PDF)` — a government portal source published by `City of Charlotte, NC (Charlotte-Mecklenburg Police Department)`. | cb96e7320055f4fbd3562f6aa5a114e7895d9ef70b056962f35fa94ce5b454ee | pending |
| D13-23 | ccops_nc_elizabeth_city_police | `Elizabeth City (NC) Police Department memorandum 'AXON Enterprise, Inc. Purchased FUSUS' (2024-10-11) - Intelligence Cen` — a government portal source published by `City of Elizabeth City, NC Police Department`. | b284d77e33e718fd6cc7749861aec16dc5a37f44748f25f1f613523046ad03f6 | pending |
| D13-24 | ccops_ny_new_york_nyc_comptroller | `NYC Comptroller surveillance procurement and audits` — a government portal source published by `NYC Comptroller`. | 926921187de27f50002eb069b58da5b0b080a465d9486a910c77c98ac2ba63cb | pending |
| D13-25 | ccops_nyc_post | `NYC POST Act impact & use policies (42 per-technology PDFs)` — a government mandated disclosure source. | decd47c3153cc8b493a727b7f68c4f6e8116b868ab7b5be46e47c22893212134 | pending |

## Confirmation log

(none yet)
