# Description batch 18 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D18-01 | future_statutory_disclosure_al | `Alabama LPR Registry duties — Ala. Admin. Code 265-X-6` — a government portal source. | a2ffea832da53b75b9ef21eeb87a32965ee83bd1bd4b70035ae4077a4f0e8e30 | pending |
| D18-02 | future_statutory_disclosure_ar | `Arkansas LPR statistics compilation — 12 CAR 150-103(f)` — a government portal source. | f48a35bda75065bdf6bed7a93f31006fb589689bd7eff7e63846e77ace57ac33 | pending |
| D18-03 | future_statutory_disclosure_mn | `Minnesota NW Metro RTCC report — HF 3198 (2025-26), contingent` — a government portal source. | 43a14c31a0bb23f9bb6994f5063471a162a6b9cd641bd6c54b14e240e5510214 | pending |
| D18-04 | future_statutory_disclosure_nm | `New Mexico ALPR agency reports to DPS — SB 40 (2026) §A` — a government portal source. | edb72d45e8b43c2dbab3967292b41d79481d62d1fe41370de52b8dd527568ae8 | pending |
| D18-05 | future_statutory_disclosure_ut | `Utah facial-recognition annual reports — Utah Code 77-23e-106` — a government portal source. | a751a56c9ee3ae59874f19de78ff6d07ca5b4e28c808c1deb6411d3c54b877e0 | pending |
| D18-06 | future_statutory_disclosure_va | `Virginia ALPR statutory disclosures — Va. Code § 2.2-5517(I/J/K)` — a government portal source. | ca8093b3574e9d5e4015cb98b60dcb3d6a844139907e9b0b3c2500952ddc25ba | pending |
| D18-07 | gao_surveillance_reports | `U.S. Government Accountability Office — surveillance-technology oversight reports (facial recognition, ALPR, DHS grant programs)` — a government portal source. | 912e4955fb8419d97ae763073a6256691f7f02b9d5c8b7aab3d1d11688390978 | pending |
| D18-08 | gleif | `GLEIF golden copy` — a government portal source. | bbe62ba191a573518e49366e64c03bee7a1fa893720363521f5d5c0376a6196a | pending |
| D18-09 | govqa | `GovQA` — a records channel source. | f19e05f691393481d5a4f933035f5b8278ce955ea6055600b08f4c46657af431 | pending |
| D18-10 | govspend | `GovSpend` — a commercial source. | d3780e22801bfc857a76d63e43e4fecf1519cda67c66b8b9a1b203be7d56bfd9 | pending |
| D18-11 | granicus | `Granicus` — a government portal source. | 6783e44f4d6f8d12aaf1cffcc094284972c5b5280773dc775fc3e39e0167fa97 | pending |
| D18-12 | grant_al_adeca_psn | `Alabama ADECA newsroom - Governor's Project Safe Neighborhoods grant announcements naming grantees for license plate rea` — a government portal source published by `Alabama Department of Economic and Community Affairs (ADECA)`. | c01c61bf9b98c054022d8ddf04c68bed67f801892fcf0c5f82f95ca1a72caf68 | pending |
| D18-13 | grant_ca_bscc_ort | `California BSCC Organized Retail Theft (ORT) Prevention Grant Program: project summaries, grantee map, quarterly and ann` — a government portal source published by `California Board of State and Community Corrections`. | c549394fb2727439c4b6433fa29b02fbd2d36df7dce24c8f4f249ac21a44364a | pending |
| D18-14 | grant_fl_senate_lfir | `Florida Legislature - Local Funding Initiative Requests (LFIR), per-project state-budget requests (e.g. FY2024-25 S3177 ` — a government portal source published by `The Florida Senate (Local Funding Initiative Request forms, by fiscal year)`. | ac26fcde1ff7783841bbcb25c45002d2a6f90a76e1d71790886080dcf3e29fb2 | pending |
| D18-15 | grant_il_illinois_gata_csfa | `Illinois GATA CSFA 569-00-3496 ILETSB Law Enforcement Camera Grant - Award List` — a government portal source published by `Illinois Law Enforcement Training and Standards Board via Illinois GOMB GATA Catalog of State Financial Assistance`. | d0320babd2f760e2a7bfca9c0d63025cc71c5d3d9e3f825f90036b4d81c018c7 | pending |
| D18-16 | grant_ma_massachusetts_law_enforcement | `Massachusetts Law Enforcement Body-Worn Camera Program (EOPSS Office of Grants and Research) award announcements` — a government portal source published by `Commonwealth of Massachusetts, EOPSS Office of Grants and Research`. | f953fde7362f181226111ef0bc8c624db609bc8729297f4d0bc5dde49bbdcba1 | pending |
| D18-17 | grant_nj_oag_bwc | `New Jersey OAG SFY21 Body-Worn Camera Grant Program - Program Administration and Guidelines ($57,500,000)` — a government portal source published by `State of New Jersey, Department of Law and Public Safety, Office of the Attorney General`. | 881dc11a8e7be529bec64ed12def3949628e7bc8800656e8247b2272cf058750 | pending |
| D18-18 | grant_oh_ohio_criminal_justice | `Ohio Office of Criminal Justice Services Body-Worn Camera Grant Program (annual RFP and award rounds)` — a government portal source published by `Ohio Department of Public Safety, Office of Criminal Justice Services`. | 08a4a9083c8ba219e2abd4599437695f26cb528bf6f9100d2bf4c00634652c84 | pending |
| D18-19 | grant_ok_dac_jag_lle | `Oklahoma JAG-LLE local equipment funding` — a government portal source published by `Oklahoma District Attorneys Council (JAG-LLE)`. | 4a473b850ce141a1ce0a371c411ee0b221e60931f5ada9fb8dd51737925356cf | pending |
| D18-20 | grant_ok_safe_oklahoma_grant | `Safe Oklahoma Grant program awards and reports discovery` — a government portal source published by `Oklahoma Attorney General's office (Safe Oklahoma grant)`. | 61907911da3df5ebfdebe7be6e1bf959f033043a414b5fba0246b3fd73e06aeb | pending |
| D18-21 | grant_tx_txdmv_mvcpa | `Texas DMV Motor Vehicle Crime Prevention Authority (MVCPA) grantees and FY2026 grant listing` — a government portal source published by `Texas Department of Motor Vehicles, Motor Vehicle Crime Prevention Authority`. | 373a2c0ae41a24c85e8c9dfd02355b5b24a607e959e6a6416d73d5601dd94b5f | pending |
| D18-22 | grant_us_doj_cops_technology | `DOJ COPS technology/equipment award documents` — a government portal source published by `U.S. DOJ Office of Community Oriented Policing Services (COPS)`. | 41bec365328894851bc9bb3981b1525b513cb92b91250b392ccefb653d8788ae | pending |
| D18-23 | gsa | `GSA` — a government portal source. | 0afb22c1d632893ec11f30ab901d40d5c43afca501b353f1f1bc6dd7425ca721 | pending |
| D18-24 | guardian_flock_cameras | `Guardian, Flock cameras (2026-08-20)` — a news publisher source. | f04ab5d82a82752d61de5269e8f9d2b81a72cb6ab1f750497bc1a5025dcb951d | pending |
| D18-25 | have_i_been_flocked | `Have I Been Flocked` — an upstream project source. | 1049f27c8af39a3e15f16fab63ab8df70ff9c1888af8ee78cbc6c8cf91cd1ad5 | pending |

## Confirmation log

(none yet)
