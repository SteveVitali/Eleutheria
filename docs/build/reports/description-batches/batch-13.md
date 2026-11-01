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
| D13-01 | ccops_ca_calistoga_police_department | Calistoga Police Department Voluntary Security Camera Registry — a government portal source published by City of Calistoga, CA Police Department. | c17e84497f78c4dbdb6572d95fd66b354ce99e04b199ac45ff2521021153765e | pending |
| D13-02 | ccops_ca_pinole_police_department | Pinole Police Department Security Camera Registry — a government portal source published by City of Pinole, CA Police Department. | 416f4f588ba7709fe36e34f1667be3f86894bc8a25f7ac401941db02e08a04a5 | pending |
| D13-03 | ccops_ca_san_diego_privacy_advisory | San Diego Privacy Advisory Board recommendations — a government portal source published by City of San Diego Privacy Advisory Board. | 6491efacdb02627dfea73da775685fe889974ab0797ff1d15e227c230e1efef8 | pending |
| D13-04 | ccops_ca_san_diego_sunshine_act_goods | San Diego Sunshine Act goods/services contracts — a government portal source published by City of San Diego (Purchasing / contracts). | 3012a7a6fa113caa3ed994e5a2aaaff951e87fefc1960647d5e7c2897b9e693b | pending |
| D13-05 | ccops_cambridge | CCOPS Cambridge MA — surveillance oversight ordinance disclosures — a government mandated disclosure source. | 15c43f5b2d9cfb885ecbc3f25b45edd11fc4342a1468d87af4713bb298044955 | pending |
| D13-06 | ccops_columbia_mo | City of Columbia MO: 2025 Annual Surveillance Technology Report (Law Enforcement Surveillance Oversight Ordinance) — a government mandated disclosure source published by City of Columbia, MO (Columbia Police Department). | 400842641d267fccc6a59def1ff0b7e6817b6b51b37caa08a0a0c1040dd86189 | pending |
| D13-07 | ccops_davis | CCOPS Davis — surveillance technology ordinance disclosures — a government mandated disclosure source. | a05e69124606987a9ac45d70446c530cf7e8dcf9d89ea88a514ddfb26ccc9c90 | pending |
| D13-08 | ccops_dayton_oh | City of Dayton OH: Surveillance Technology (annual reports, use policies, notifications) — a government mandated disclosure source published by City of Dayton, OH (Dayton Police Department). | 65623e52899ddc83c523fb36f6c7a01cc1103c8bd37d0341d02db81c6a5bb48e | pending |
| D13-09 | ccops_gb_eng_barnet_traffic_cctv | Traffic CCTV contract — a government portal source published by London Borough of Barnet. | a79855c4f97af32c1f5d6749075ba84d9a4796d0bc75f10e9e75b5ce96c98c10 | pending |
| D13-10 | ccops_grand_rapids | CCOPS Grand Rapids — surveillance ordinance disclosures — a government mandated disclosure source. | 3698c8b4cb34624087ecd3f189b92dae7bf62648cb811cb77f216a2b7cc767df | pending |
| D13-11 | ccops_hi_honolulu_police_department | Honolulu Police Department policy - Automated License Plate Reader — a government portal source published by Honolulu Police Department. | 52492c3e156a9ad26c24073c80184885aad4371ba3980729e53d59d046ee6260 | pending |
| D13-12 | ccops_il_chicago_oig_shotspotter | Chicago OIG ShotSpotter evaluation and follow-up — a government portal source published by Chicago Office of Inspector General. | e63947977276a205ed7cc72736df994d5ba345f12b84a2f36b07374b6a2bd787 | pending |
| D13-13 | ccops_iso_au_privacy_commissioner | Privacy Commissioner publishes updated guidance on facial recognition in retail spaces — a government portal source published by Office of the Australian Information Commissioner. | 35de4199a7d36e144a48eb06ad313e11326f54f5a786789342e9ab79fbcb078d | pending |
| D13-14 | ccops_it_tn_trento_provvedimento_dell_11 | Provvedimento dell'11 gennaio 2024 [9977020] (Comune di Trento — Marvel/Protector/Precrisis) — a government portal source published by Garante per la protezione dei dati personali (Italy). | 7bbe0fdc687b42a2e5f968955aded1f93d3a2def955ea7b51788adce6d882ce6 | pending |
| D13-15 | ccops_mi_wayne_county_commission | Wayne County Commission — committee meeting pages (incl. Public Safety, Judiciary & Homeland Security) — a government portal source published by Wayne County Commission, Michigan (Granicus OpenCities CMS). | 5512658f7ea5f0754a8fbdf5ea67bd0d2dbe8b0a0a6b9ff6a12d6b7c39ae7f99 | pending |
| D13-16 | ccops_mn_dayton_police_department | Dayton (MN) Police Department Resident Camera Registry — a government portal source published by City of Dayton, MN Police Department. | 7defbac7f07332170247d30445962abebe3e11f080c65e40e4da4ade72e470df | pending |
| D13-17 | ccops_mo_st_louis_fy21_spi_shotspotter | FY21 - SPI ShotSpotter Expansion Evaluation - Final Report (St. Louis Metropolitan Police Department) — an academic source published by Southern Illinois University Edwardsville (with SLMPD), BJA-funded. | 671f43ee43a6e01b4d68239b00d18a8de7d28273c19936e0f435cdf1cef37f6c | pending |
| D13-18 | ccops_nashville | CCOPS Nashville — Metro surveillance ordinance disclosures — a government mandated disclosure source. | 3ea2aefd73b8834aac1140bf368ee40bda8bd96aaa6cb5db270a36d7b40930d2 | pending |
| D13-19 | ccops_nc_charlotte_mecklenburg_police | Charlotte-Mecklenburg Police Department - Interactive Directives Guide (compiled directives PDF) — a government portal source published by City of Charlotte, NC (Charlotte-Mecklenburg Police Department). | c80e2f9d26bdee92526dee9c6b365f61fcff7c933845e92d788b25a0d9077f33 | pending |
| D13-20 | ccops_nc_elizabeth_city_police | Elizabeth City (NC) Police Department memorandum 'AXON Enterprise, Inc. Purchased FUSUS' (2024-10-11) - Intelligence Cen — a government portal source published by City of Elizabeth City, NC Police Department. | b57751be97b2e08582a9bea00e6cb0c3093e0c0d903b3490538a7f7cc5a9c5b3 | pending |
| D13-21 | ccops_ny_new_york_nyc_comptroller | NYC Comptroller surveillance procurement and audits — a government portal source published by NYC Comptroller. | 93e364609a9bd319e257bbfbcbe60695e26b0cc6d10feb8e223829c1005bf3c6 | pending |
| D13-22 | ccops_nyc_post | NYC POST Act impact & use policies (42 per-technology PDFs) — a government mandated disclosure source. | b311d9e878b364609328e8e775148a39a53e76b69f0cc6f572ceec08ed9b49e9 | pending |
| D13-23 | ccops_oakland | CCOPS Oakland — Privacy Advisory Commission surveillance disclosures — a government mandated disclosure source. | 0f27bff8b1d6f948b4b768cf9b0ebc90014ba27e487614766755d40cb56a2d2d | pending |
| D13-24 | ccops_oh_cincinnati_police_department | Cincinnati Police Department - voluntary community camera registry (Axon Fusus 'Real-Time Crime Center in the Cloud') — a government portal source published by City of Cincinnati, OH Police Department. | d69271de954bff8d24a537c3397f484fa9f7e995c0be25dc3112fcb3821644a6 | pending |
| D13-25 | ccops_ok_oklahoma_city_okc_flock_council | OKC Flock council amendment policy packet — a government portal source published by City of Oklahoma City. | 245f48d3f126d4a4c790ea15e98c08712eb578e8484cc0940e0e5913a3b6214d | pending |

## Confirmation log

(none yet)
