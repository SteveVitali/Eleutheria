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
| D17-01 | flockreporter | `FlockReporter` — a community source. | 8e1d7f5718ed0a9a80a057e45b9547436b7bb6f57fd0005f5a2fd7bfd7068dae | pending |
| D17-02 | foiaxpress | `FOIAXpress` — a records channel source. | b59891a6989959ee1fb9f694c41cd611e2bbc7547ccb5dfabc27214af0e04f62 | pending |
| D17-03 | footnote4a | `Footnote4a` — a community source. | 7fce7c9491eb7a5744e35cfb4848a271a4905b1ae2947ce53dbe3471fc2e4114 | pending |
| D17-04 | future_statutory_disclosure_2027 | `State statutory disclosure — first reports due 2027-04-01` — a government portal source. | 14c3c28dd9c88d6b3143b81916d2f72403a103f46e7e039e0bbbd48127bb481c | pending |
| D17-05 | future_statutory_disclosure_al | `Alabama LPR Registry duties — Ala. Admin. Code 265-X-6` — a government portal source. | a2ffea832da53b75b9ef21eeb87a32965ee83bd1bd4b70035ae4077a4f0e8e30 | pending |
| D17-06 | future_statutory_disclosure_ar | `Arkansas LPR statistics compilation — 12 CAR 150-103(f)` — a government portal source. | f48a35bda75065bdf6bed7a93f31006fb589689bd7eff7e63846e77ace57ac33 | pending |
| D17-07 | future_statutory_disclosure_mn | `Minnesota NW Metro RTCC report — HF 3198 (2025-26), contingent` — a government portal source. | 43a14c31a0bb23f9bb6994f5063471a162a6b9cd641bd6c54b14e240e5510214 | pending |
| D17-08 | future_statutory_disclosure_nm | `New Mexico ALPR agency reports to DPS — SB 40 (2026) §A` — a government portal source. | edb72d45e8b43c2dbab3967292b41d79481d62d1fe41370de52b8dd527568ae8 | pending |
| D17-09 | future_statutory_disclosure_ut | `Utah facial-recognition annual reports — Utah Code 77-23e-106` — a government portal source. | a751a56c9ee3ae59874f19de78ff6d07ca5b4e28c808c1deb6411d3c54b877e0 | pending |
| D17-10 | future_statutory_disclosure_va | `Virginia ALPR statutory disclosures — Va. Code § 2.2-5517(I/J/K)` — a government portal source. | ca8093b3574e9d5e4015cb98b60dcb3d6a844139907e9b0b3c2500952ddc25ba | pending |
| D17-11 | gao_surveillance_reports | `U.S. Government Accountability Office — surveillance-technology oversight reports (facial recognition, ALPR, DHS grant programs)` — a government portal source. | 912e4955fb8419d97ae763073a6256691f7f02b9d5c8b7aab3d1d11688390978 | pending |
| D17-12 | gleif | `GLEIF golden copy` — a government portal source. | bbe62ba191a573518e49366e64c03bee7a1fa893720363521f5d5c0376a6196a | pending |
| D17-13 | govqa | `GovQA` — a records channel source. | f19e05f691393481d5a4f933035f5b8278ce955ea6055600b08f4c46657af431 | pending |
| D17-14 | govspend | `GovSpend` — a commercial source. | d3780e22801bfc857a76d63e43e4fecf1519cda67c66b8b9a1b203be7d56bfd9 | pending |
| D17-15 | granicus | `Granicus` — a government portal source. | 6783e44f4d6f8d12aaf1cffcc094284972c5b5280773dc775fc3e39e0167fa97 | pending |
| D17-16 | grant_al_adeca_psn | `Alabama ADECA newsroom - Governor's Project Safe Neighborhoods grant announcements naming grantees for license plate rea` — a government portal source published by `Alabama Department of Economic and Community Affairs (ADECA)`. | c01c61bf9b98c054022d8ddf04c68bed67f801892fcf0c5f82f95ca1a72caf68 | pending |
| D17-17 | grant_ca_bscc_ort | `California BSCC Organized Retail Theft (ORT) Prevention Grant Program: project summaries, grantee map, quarterly and ann` — a government portal source published by `California Board of State and Community Corrections`. | c549394fb2727439c4b6433fa29b02fbd2d36df7dce24c8f4f249ac21a44364a | pending |
| D17-18 | grant_fl_senate_lfir | `Florida Legislature - Local Funding Initiative Requests (LFIR), per-project state-budget requests (e.g. FY2024-25 S3177 ` — a government portal source published by `The Florida Senate (Local Funding Initiative Request forms, by fiscal year)`. | ac26fcde1ff7783841bbcb25c45002d2a6f90a76e1d71790886080dcf3e29fb2 | pending |
| D17-19 | grant_il_illinois_gata_csfa | `Illinois GATA CSFA 569-00-3496 ILETSB Law Enforcement Camera Grant - Award List` — a government portal source published by `Illinois Law Enforcement Training and Standards Board via Illinois GOMB GATA Catalog of State Financial Assistance`. | d0320babd2f760e2a7bfca9c0d63025cc71c5d3d9e3f825f90036b4d81c018c7 | pending |
| D17-20 | grant_ma_massachusetts_law_enforcement | `Massachusetts Law Enforcement Body-Worn Camera Program (EOPSS Office of Grants and Research) award announcements` — a government portal source published by `Commonwealth of Massachusetts, EOPSS Office of Grants and Research`. | f953fde7362f181226111ef0bc8c624db609bc8729297f4d0bc5dde49bbdcba1 | pending |
| D17-21 | grant_nj_oag_bwc | `New Jersey OAG SFY21 Body-Worn Camera Grant Program - Program Administration and Guidelines ($57,500,000)` — a government portal source published by `State of New Jersey, Department of Law and Public Safety, Office of the Attorney General`. | 881dc11a8e7be529bec64ed12def3949628e7bc8800656e8247b2272cf058750 | pending |
| D17-22 | grant_oh_ohio_criminal_justice | `Ohio Office of Criminal Justice Services Body-Worn Camera Grant Program (annual RFP and award rounds)` — a government portal source published by `Ohio Department of Public Safety, Office of Criminal Justice Services`. | 08a4a9083c8ba219e2abd4599437695f26cb528bf6f9100d2bf4c00634652c84 | pending |
| D17-23 | grant_ok_dac_jag_lle | `Oklahoma JAG-LLE local equipment funding` — a government portal source published by `Oklahoma District Attorneys Council (JAG-LLE)`. | 4a473b850ce141a1ce0a371c411ee0b221e60931f5ada9fb8dd51737925356cf | pending |
| D17-24 | grant_ok_safe_oklahoma_grant | `Safe Oklahoma Grant program awards and reports discovery` — a government portal source published by `Oklahoma Attorney General's office (Safe Oklahoma grant)`. | 61907911da3df5ebfdebe7be6e1bf959f033043a414b5fba0246b3fd73e06aeb | pending |
| D17-25 | grant_tx_txdmv_mvcpa | `Texas DMV Motor Vehicle Crime Prevention Authority (MVCPA) grantees and FY2026 grant listing` — a government portal source published by `Texas Department of Motor Vehicles, Motor Vehicle Crime Prevention Authority`. | 373a2c0ae41a24c85e8c9dfd02355b5b24a607e959e6a6416d73d5601dd94b5f | pending |

## Confirmation log

(none yet)
