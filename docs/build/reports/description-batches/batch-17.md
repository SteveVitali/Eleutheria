# Description batch 17 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D17-01 | flockreporter | FlockReporter — a community source. | 7e8b45bd680d17b710cc3b39f3d9193152ac55985580cafc907cacd9c7359fc4 | pending |
| D17-02 | foiaxpress | FOIAXpress — a records channel source. | 223b3aa9b28596d6dd6ddcf0500cd1be9b8b5a8092d25c2f32f5b26a3710075d | pending |
| D17-03 | footnote4a | Footnote4a — a community source. | 27b4333519be33977ef3983522e2ea23b1782ba0a9ba2363f3c5dd08c1da4a1d | pending |
| D17-04 | future_statutory_disclosure_2027 | State statutory disclosure — first reports due 2027-04-01 — a government portal source. | dafb23d08a329306881550accef64b119ff8cec3ba4ec7cef92553e231a27ba5 | pending |
| D17-05 | future_statutory_disclosure_al | Alabama LPR Registry duties — Ala. Admin. Code 265-X-6 — a government portal source. | 6cee9f8b0e441dfce3511e8368b5a5decdbc8ef2817333f385646daa2693edc1 | pending |
| D17-06 | future_statutory_disclosure_ar | Arkansas LPR statistics compilation — 12 CAR 150-103(f) — a government portal source. | f488f6c5d22cb02be385542e4ccd6925a685b6b12756c442920ca03bc085c022 | pending |
| D17-07 | future_statutory_disclosure_mn | Minnesota NW Metro RTCC report — HF 3198 (2025-26), contingent — a government portal source. | 44d5b9f3de9c43e8e04f808c6efe364b2384e74bee2fd486a53d0c92fe2186fd | pending |
| D17-08 | future_statutory_disclosure_nm | New Mexico ALPR agency reports to DPS — SB 40 (2026) §A — a government portal source. | c808424e3f6910ee62f3731b775d4ea5ca1bfa4109f2ade6c46418ac94de11ef | pending |
| D17-09 | future_statutory_disclosure_ut | Utah facial-recognition annual reports — Utah Code 77-23e-106 — a government portal source. | 43c2ee30279c935c76063f00ec7d31f826e1645c71ef9fa9d9b4228bbd5834c0 | pending |
| D17-10 | future_statutory_disclosure_va | Virginia ALPR statutory disclosures — Va. Code § 2.2-5517(I/J/K) — a government portal source. | 417a581f88f33cfefc5f4de9b176caccaffdf27b6ef0f29c6b1bab38516ef252 | pending |
| D17-11 | gao_surveillance_reports | U.S. Government Accountability Office — surveillance-technology oversight reports (facial recognition, ALPR, DHS grant programs) — a government portal source. | c9dad36721ec9ff700e50c5558c4f1012db551c6973f5e2441e7e6b0f63aab72 | pending |
| D17-12 | gleif | GLEIF golden copy — a government portal source. | 5cd93b748b0870164c851b47b6a3adab6cd9eba7dd37e475a7fd3202823bfb09 | pending |
| D17-13 | govqa | GovQA — a records channel source. | bba8cf85219a42f6778e8db4077e720228079cb7044b94a0cf91e9fbe4baed09 | pending |
| D17-14 | govspend | GovSpend — a commercial source. | 18a654aeaa07facd8bdb4f5001248c4baa877ea0a3a8be196150a9a1e84d88ef | pending |
| D17-15 | granicus | Granicus — a government portal source. | bbb41bbaea3e341be45334871e5be27d718cd62b1d3844ce0eb03df28d022f6a | pending |
| D17-16 | grant_al_adeca_psn | Alabama ADECA newsroom - Governor's Project Safe Neighborhoods grant announcements naming grantees for license plate rea — a government portal source published by Alabama Department of Economic and Community Affairs (ADECA). | 45e3b6c89b56aaff2460fe60717ff1e2c63fb2ccd0dc97f61a3a8733a35e30f8 | pending |
| D17-17 | grant_ca_bscc_ort | California BSCC Organized Retail Theft (ORT) Prevention Grant Program: project summaries, grantee map, quarterly and ann — a government portal source published by California Board of State and Community Corrections. | d1b8e7295b1cac9104346b942019ec7219af3e2115765a707904ecbc13bebbb0 | pending |
| D17-18 | grant_fl_senate_lfir | Florida Legislature - Local Funding Initiative Requests (LFIR), per-project state-budget requests (e.g. FY2024-25 S3177  — a government portal source published by The Florida Senate (Local Funding Initiative Request forms, by fiscal year). | a3facc96be82f2446c82fefd5c85b4a3adfe6db7be8acdc31c7e0e989cd3ddde | pending |
| D17-19 | grant_il_illinois_gata_csfa | Illinois GATA CSFA 569-00-3496 ILETSB Law Enforcement Camera Grant - Award List — a government portal source published by Illinois Law Enforcement Training and Standards Board via Illinois GOMB GATA Catalog of State Financial Assistance. | d1ad8c679934b6b309b3253eddba4a083e571ccb9d5df08a325873222c2d6958 | pending |
| D17-20 | grant_ma_massachusetts_law_enforcement | Massachusetts Law Enforcement Body-Worn Camera Program (EOPSS Office of Grants and Research) award announcements — a government portal source published by Commonwealth of Massachusetts, EOPSS Office of Grants and Research. | c7651bb71c8fd6e10d6bafbc58f6b50eb04550e88a436e309b98d38a5dc3f63d | pending |
| D17-21 | grant_nj_oag_bwc | New Jersey OAG SFY21 Body-Worn Camera Grant Program - Program Administration and Guidelines ($57,500,000) — a government portal source published by State of New Jersey, Department of Law and Public Safety, Office of the Attorney General. | 48dfa2c39e16b37a6b2d5e8e1ffa55816050d4c4eee7289e577a5f6038e874da | pending |
| D17-22 | grant_oh_ohio_criminal_justice | Ohio Office of Criminal Justice Services Body-Worn Camera Grant Program (annual RFP and award rounds) — a government portal source published by Ohio Department of Public Safety, Office of Criminal Justice Services. | f54528642b90803b6f7e3790d2dd9eedc3e02adc030d3bfaed73f9e574b1d24c | pending |
| D17-23 | grant_ok_dac_jag_lle | Oklahoma JAG-LLE local equipment funding — a government portal source published by Oklahoma District Attorneys Council (JAG-LLE). | a74d62061019daadbea0c7b78000b5153945da2bbbd5060dac62f4e118f26fef | pending |
| D17-24 | grant_ok_safe_oklahoma_grant | Safe Oklahoma Grant program awards and reports discovery — a government portal source published by Oklahoma Attorney General's office (Safe Oklahoma grant). | 22b692c9a6ca788c8f15ba76b38f1af2dbf6127a759342c30a0f18630495cc95 | pending |
| D17-25 | grant_tx_txdmv_mvcpa | Texas DMV Motor Vehicle Crime Prevention Authority (MVCPA) grantees and FY2026 grant listing — a government portal source published by Texas Department of Motor Vehicles, Motor Vehicle Crime Prevention Authority. | 78cb1473ef61f1990511fa94127fead7a52fb68c7d94e9956cd7b95b7215c846 | pending |

## Confirmation log

(none yet)
