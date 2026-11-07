# Description batch 22 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D22-01 | procportal_fl_florida_buy_cooperative | `Florida Buy (PAEC) State Cooperative Purchasing Program - GAGGLE.NET, INC. contract (award letter, interlocal agreement,` — a government portal source published by `Panhandle Area Educational Consortium (PAEC), Florida Buy`. | 9a097e4f50ae7c74be09126b3ec6635acc94bea10ffc550f7ebf7f3c8faddddf | pending |
| D22-02 | procportal_forsyth_nc_purchasing | `RFP2449 Real-Time Intelligence Center Enterprise Solution` — a government portal source published by `Winston-Salem / Forsyth County Purchasing Division for Forsyth County Sheriff's Office`. | bc943806ead6d24973779693aeec9b1ed565bf0866b6fae590622b74f1513a3c | pending |
| D22-03 | procportal_kcmo_mo | `Kansas City, MO — Socrata 'List of KCMO City Contracts' dataset` — a government portal source. | d4fb7fc60f0bddd9debf8c75244a38343f3602d29572035138782e0882637e42 | pending |
| D22-04 | procportal_ny_northeastern_regional | `Northeastern Regional Information Center (NERIC, Capital Region BOCES) - Gaggle service page` — a government portal source published by `NERIC (Capital Region BOCES regional information center, NY)`. | b424f6ce1e70888586ae088b433d28b9a6845adbb2d8a36d86df8ea797d4da01 | pending |
| D22-05 | procportal_nyc_ny | `City of New York — Socrata 'City Record Online' dataset` — a government portal source. | 6abf632d61549e0ccce4fb982c64f94d6b31f90f6816341e3e1c9d11054113e2 | pending |
| D22-06 | procportal_ok_oklahoma_omes_statewide | `Oklahoma OMES statewide contracts and solicitations` — a government portal source published by `Oklahoma Office of Management and Enterprise Services (OMES)`. | e5630bb72d30ab05d0cdf9ee362208e45d3c64dff98eceb9dbe7a2b3dbc9e8e9 | pending |
| D22-07 | procportal_pr_consulta_del_registro | `Consulta del Registro de Contratos (Oficina de la Contralora de Puerto Rico)` — a government portal source published by `Oficina de la Contralora de Puerto Rico (OCPR)`. | 97731ba3232e739d35bdbe2cfb8917ce184d9ed3f20475e7528bf220e8b666b0 | pending |
| D22-08 | procportal_sf_ca | `City and County of San Francisco — Socrata 'Supplier Contracts' dataset` — a government portal source. | e8799c4302b3ba737760e6a109ad23bbbb1336e95a58457aa69e9340e4aa24c8 | pending |
| D22-09 | procportal_tx_texas_dir_cooperative | `Texas DIR Cooperative Contracts vendor sales data (VSR FY2026 + ARCHIVE FY2010-2025) and customer list` — a government portal source published by `Texas Department of Information Resources (via data.texas.gov / Socrata)`. | 3ca423bcc0167d871edb97219c121654296c9c25736e937431d79739142ac5c3 | pending |
| D22-10 | procportal_us_naspo_valuepoint_portfolio | `NASPO ValuePoint portfolio: Public Safety/Law Enforcement Video Products, Services & Solutions (2023-2028)` — a government portal source published by `NASPO ValuePoint (lead state: Oklahoma)`. | 133faf7816965a59dd6ab3b2b74f02a1626b409612034e41a6c1f015d28e0db3 | pending |
| D22-11 | procportal_wa_des_contract_sales | `Washington DES Statewide Contract (Master Contract) Sales Data by Customer, Contract, Vendor (n8q6-4twj)` — a government portal source published by `Washington State Department of Enterprise Services (via data.wa.gov)`. | 68d6fd306edbb4a0ae304786784a2469d1ecba7a35ae252a1b44f950b164180e | pending |
| D22-12 | procportal_wa_wsipc_rfp_24 | `WSIPC RFP 24-01 Student Safety Solutions - Gaggle cooperative contract (Washington K-12)` — a government portal source published by `WSIPC (Washington School Information Processing Cooperative)`. | 4f715348fba06fedc956adfb7c4d0de270d15db1819956e8d906e18183792e0f | pending |
| D22-13 | publicpurchase | `PublicPurchase — public agency bid portal` — a government portal source. | 2c6210fcb12ca7f3b11f0267f154dc927593c679007a7c13554ee7d49bc5e51d | pending |
| D22-14 | r_flocksurveillance | `r/FlockSurveillance` — a community source. | 4fe610cbb5e99bda47e7480a9c4a0c558b65ab7dab98cec89df525a0a567cc87 | pending |
| D22-15 | raa_prefectures | `RAA des préfectures (arrêtés préfectoraux)` — a government portal source. | 04907dc2f88758d9ccaa0415ab7ebcacc2410e571b8a54dd2e4f300142929efa | pending |
| D22-16 | ringmast4r_flock | `Ringmast4r/FLOCK` — a community source. | ebacd79d5852399a379ea7c47b327a6deac7be2fddff3f88ecada6b43d157ade | pending |
| D22-17 | rotterdam_cameraregister | `Rotterdam cameraregister — municipal camera disclosures` — a government portal source. | fe2060d91d70503686b4f6149515ed98ad969de7d0730dd3d9e07fcbe376d601 | pending |
| D22-18 | sam_gov | `SAM.gov` — a government portal source. | 36a49fdcbfab387104ee0de0ee49d24ba8a0baafc1ab6caacffc4473ed5bef7c | pending |
| D22-19 | sm_alpr | `none-below/sm-alpr` — an upstream project source. | 9058d70f537604d4243ae4f6b964d6239cf6f62db65355a1d2de3c583cf22f89 | pending |
| D22-20 | sourcewell | `Sourcewell` — a government portal source. | e8daa8f1fbdf4f38fd248adc2869a64779f4bad68423ff26939684d3dc04321e | pending |
| D22-21 | sous_surveillance_osm_import | `sous-surveillance.net → OSM import` — an upstream project source. | ad3372d8984401e7c876823bfdff5166fbb97f19619f0eb74cce88cb7b486531 | pending |
| D22-22 | state_alpr_statute_inventory | `State ALPR statute national inventory` — a government portal source. | 183ef3a2647e9914a03bd7a42eefe314a91cff379692accf539063a90fd541d0 | pending |
| D22-23 | state_alpr_statute_inventory_2026 | `State ALPR statute inventory — 2026 origin-verified refresh` — a government portal source. | 27dcb0ca0ce5a1547e002f2ca857acd37f673aa988031bc5a472bedc199e8e55 | pending |
| D22-24 | statrep_austin_tx_auditor | `City of Austin Office of the City Auditor - 'APD License Plate Reader Audit Report' (May 2025)` — a government mandated disclosure source published by `City of Austin, TX Office of the City Auditor`. | 5b621a19919ed18e20d6b80a6240a71fa0994e617ea5c72a08cc2fe0661d07c4 | pending |
| D22-25 | statrep_ca_california_auditor_alpr | `California State Auditor ALPR audit survey and follow-up` — a government portal source published by `California State Auditor`. | b607a475fadaba9709c17a2b84f99acf47e0c146d61375b8bce496009bb06688 | pending |

## Confirmation log

(none yet)
