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
| D18-01 | grant_al_adeca_psn | `Alabama ADECA newsroom - Governor's Project Safe Neighborhoods grant announcements naming grantees for license plate rea` — a government portal source published by `Alabama Department of Economic and Community Affairs (ADECA)`. | c01c61bf9b98c054022d8ddf04c68bed67f801892fcf0c5f82f95ca1a72caf68 | pending |
| D18-02 | grant_ca_bscc_ort | `California BSCC Organized Retail Theft (ORT) Prevention Grant Program: project summaries, grantee map, quarterly and ann` — a government portal source published by `California Board of State and Community Corrections`. | c549394fb2727439c4b6433fa29b02fbd2d36df7dce24c8f4f249ac21a44364a | pending |
| D18-03 | grant_fl_senate_lfir | `Florida Legislature - Local Funding Initiative Requests (LFIR), per-project state-budget requests (e.g. FY2024-25 S3177 ` — a government portal source published by `The Florida Senate (Local Funding Initiative Request forms, by fiscal year)`. | ac26fcde1ff7783841bbcb25c45002d2a6f90a76e1d71790886080dcf3e29fb2 | pending |
| D18-04 | grant_il_illinois_gata_csfa | `Illinois GATA CSFA 569-00-3496 ILETSB Law Enforcement Camera Grant - Award List` — a government portal source published by `Illinois Law Enforcement Training and Standards Board via Illinois GOMB GATA Catalog of State Financial Assistance`. | d0320babd2f760e2a7bfca9c0d63025cc71c5d3d9e3f825f90036b4d81c018c7 | pending |
| D18-05 | grant_ma_massachusetts_law_enforcement | `Massachusetts Law Enforcement Body-Worn Camera Program (EOPSS Office of Grants and Research) award announcements` — a government portal source published by `Commonwealth of Massachusetts, EOPSS Office of Grants and Research`. | f953fde7362f181226111ef0bc8c624db609bc8729297f4d0bc5dde49bbdcba1 | pending |
| D18-06 | grant_nj_oag_bwc | `New Jersey OAG SFY21 Body-Worn Camera Grant Program - Program Administration and Guidelines ($57,500,000)` — a government portal source published by `State of New Jersey, Department of Law and Public Safety, Office of the Attorney General`. | 881dc11a8e7be529bec64ed12def3949628e7bc8800656e8247b2272cf058750 | pending |
| D18-07 | grant_oh_ohio_criminal_justice | `Ohio Office of Criminal Justice Services Body-Worn Camera Grant Program (annual RFP and award rounds)` — a government portal source published by `Ohio Department of Public Safety, Office of Criminal Justice Services`. | 08a4a9083c8ba219e2abd4599437695f26cb528bf6f9100d2bf4c00634652c84 | pending |
| D18-08 | grant_ok_dac_jag_lle | `Oklahoma JAG-LLE local equipment funding` — a government portal source published by `Oklahoma District Attorneys Council (JAG-LLE)`. | 4a473b850ce141a1ce0a371c411ee0b221e60931f5ada9fb8dd51737925356cf | pending |
| D18-09 | grant_ok_safe_oklahoma_grant | `Safe Oklahoma Grant program awards and reports discovery` — a government portal source published by `Oklahoma Attorney General's office (Safe Oklahoma grant)`. | 61907911da3df5ebfdebe7be6e1bf959f033043a414b5fba0246b3fd73e06aeb | pending |
| D18-10 | grant_tx_txdmv_mvcpa | `Texas DMV Motor Vehicle Crime Prevention Authority (MVCPA) grantees and FY2026 grant listing` — a government portal source published by `Texas Department of Motor Vehicles, Motor Vehicle Crime Prevention Authority`. | 373a2c0ae41a24c85e8c9dfd02355b5b24a607e959e6a6416d73d5601dd94b5f | pending |
| D18-11 | grant_us_doj_cops_technology | `DOJ COPS technology/equipment award documents` — a government portal source published by `U.S. DOJ Office of Community Oriented Policing Services (COPS)`. | 41bec365328894851bc9bb3981b1525b513cb92b91250b392ccefb653d8788ae | pending |
| D18-12 | gsa | `GSA` — a government portal source. | 0afb22c1d632893ec11f30ab901d40d5c43afca501b353f1f1bc6dd7425ca721 | pending |
| D18-13 | guardian_flock_cameras | `Guardian, Flock cameras (2026-08-20)` — a news publisher source. | f04ab5d82a82752d61de5269e8f9d2b81a72cb6ab1f750497bc1a5025dcb951d | pending |
| D18-14 | have_i_been_flocked | `Have I Been Flocked` — an upstream project source. | 1049f27c8af39a3e15f16fab63ab8df70ff9c1888af8ee78cbc6c8cf91cd1ad5 | pending |
| D18-15 | hgacbuy | `HGACBuy` — a government portal source. | cfa2012d73f64eba59ff8bcd9127f41efd3366b506974883102c6aa24bf9ab1c | pending |
| D18-16 | hibf_audit_log_guide | `HIBF audit-log guide` — an upstream project source. | 481cff44ff202fbe2c2c7f53d4cc3f94790997bf6b7dd4d4f21381064076fe46 | pending |
| D18-17 | hibf_methodology | `HIBF methodology hub` — an upstream project source. | 6faa3dfcc29ec1b4fbee0f6425657bcd8a37edc1e8e98e58731a3b3c9ab4a43e | pending |
| D18-18 | internet_archive_wayback | `Internet Archive Wayback` — an upstream project source. | 4b0fc24c43db45ca71250ed5cd6439e0e81129937cb44c34cdd18e7b16db9c3e | pending |
| D18-19 | iqm2 | `IQM2` — a government portal source. | cfcec0931c47d98ddd052ef0acc03ad4f4aef3be9b3b65668249a40d1b6fade5 | pending |
| D18-20 | journalrecord | `The Journal Record (Oklahoma City)` — a news publisher source. | dd19d586a9b38b78175649787f2b21e07d2c47715fe73c1c6ddd37ab246fe5b4 | pending |
| D18-21 | justfoia | `JustFOIA` — a records channel source. | 87421efbf0bbdf6eb10c4085fb46da4948b2c320346af3edcc3a0fbd2c4902fd | pending |
| D18-22 | la_city_clerk_cfms | `LA City Clerk Connect (CFMS) — Los Angeles City legislative file management` — a records channel source. | 41dc16c0034fb2356e7f347ff8e9602e26152a6d5790443cba9b75d8ed481d25 | pending |
| D18-23 | la_quadrature_du_net | `La Quadrature du Net` — a news publisher source. | 3c68460d16a67d3ecc94c3de1f4dcdd3e76977709edd044dfc3a386d927127b3 | pending |
| D18-24 | leaic_crosswalk | `LEAIC crosswalk (ICPSR study 35158)` — an academic source. | d006ad537cf6a1d96952da2fea48c29f7fdffe8df8f5935381203d7c4d82e8eb | pending |
| D18-25 | legis_ca_gov_code_53166 | `California Government Code § 53166 - cellular communications interception technology usage and privacy policies and acqu` — a government portal source published by `California Legislature`. | cffb53f818186330b6fb9da138aa06fb144943652838d72a7e59de6d690f2514 | pending |

## Confirmation log

(none yet)
