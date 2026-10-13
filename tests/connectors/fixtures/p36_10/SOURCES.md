# Fixture provenance — `tests/connectors/fixtures/p36_10/` (P36.10 / R11-ACQ-14)

Every file in this directory is a **synthetic reconstruction** of the reviewed
upstream surface it models — written from the acquisition research notes
(I4/I5/I6/I9a/I9b candidates in
`docs/build/planning/2026-09-30-next-phase/research/` and the acquisition plan
rows `AP-T1-*`), never a re-hosted upstream capture (P8-2: documents are never
re-hosted; the connectors emit derived facts + the upstream link). Where the
upstream document is a PDF, the fixture carries the reviewed text-extract shape
(`*.txt`) — in a live acquisition the original would be captured upstream and
its sha256 recorded on the artifact row; the committed fixture stands in for
the extraction layer only (§5.0). The `agency_policy_*.json` envelopes are the
document connector's structured capture shape: the `§`-headed clause text is
synthetic but every clause `value` is a reviewed verbatim literal from the
research record. No live fetch was performed; all sixteen registry rows stay
`ingestion_permitted=false` (HG-03 RB-03 `a`; the two CSS-policy rows RB-07 `a`
— facts and citations only — pending the operator's OP-26 Wave-B flip under
ING-GO-B, P36.12).

## The CCOPS-reports lane (`government_mandated_disclosure`)

| fixture | models | upstream surface (reviewed) |
|---|---|---|
| `columbia_mo_report.txt` | `ccops_columbia_mo` filing | `https://www.como.gov/police/surveillance-technology-report-2025/` — the 2025 annual surveillance technology report under the Law Enforcement Surveillance Oversight Ordinance (I6-C018, live-read F024): the verbatim "required to document and publicly report its use of surveillance technology" literal is carried; the `Date:`/`Retention:`/`Sharing:` fields + technology list are the reviewed filing shape |
| `st_louis_mo_index.html` | `ccops_st_louis_mo` index | `https://www.stlouis-mo.gov/government/departments/public-safety/police/documents/surveillance-reports.cfm` — the SLMPD surveillance-reports documents page (I6-C016): Ordinance 71842 / Executive Order 78 annual-report links; a staff-directory link exercises the anchor screen, an off-host link the same-host rule |
| `st_louis_mo_report.txt` | an SLMPD annual-report filing | the `Annual Report STU 2025` filing shape (I6-C016): the filing's own `Date:`/`Technology:`/`Retention:` fields — aggregate counts only |
| `dayton_oh_index.html` | `ccops_dayton_oh` index | `https://www.daytonohio.gov/1172/Surveillance-Technology` — the CivicPlus surveillance-technology page (I6-C017): the `/Archive.aspx?ADID=` document pattern + the `surveillance`/`use polic` scope terms admit the annual-report and use-policy links; a commission-minutes archive link exercises the scope screen |
| `dayton_oh_report.txt` | a Dayton annual-report filing | the annual surveillance technology report shape (I6-C017): `Date:`/`Technology:` fields at the department-aggregate level |
| `anchorage_ao_2023_78.txt` | `ccops_anchorage_ak` filing | `https://www.muni.org/Departments/Assembly/Documents/AO%202023-78.pdf` — AO 2023-78 amending AMC ch. 3.102 'Municipal Use of Surveillance Technologies' to add a body-worn-camera policy requirement (I9b-C088, live-read F115): the title literal is verbatim; a `Date:` field stands in for the reading date the aggregate row needs |
| `austin_trust_resolution.txt` | `ccops_austin_tx` filing | `https://services.austintexas.gov/edims/document.cfm?id=466941` — the TRUST Act resolution, File ID 26-1072, Council 2026-02-05 (I9a-C022, live-read F032): the verbatim directive to return with an ordinance "to regulate the adoption, acquisition, deployment, use, and review of surveillance technology" |

## The district self-disclosure lane (`government_mandated_disclosure`)

Each page is an undated living self-disclosure — `period_from_capture` makes
the capture date the honest covered period; the page's vendor/product literals
mint `inventory_entry` claims only (never student data, never a deployment
fact). The I9b-C040 family list is the discovery channel: no registry row.

| fixture | models | upstream surface (reviewed) |
|---|---|---|
| `st_cloud_securly.html` | `policy_st_cloud_mn_isd742` page | `https://tech.isd742.org/parent-connect/securly` — the ISD 742 'Securly' parent page (I9b-C030, live-read F048): the verbatim "DOES NOT actively monitor student internet searches or flagged activities via Securly … a service provided to families at no cost for district-issued devices" statement — flags route to parents, an operating-mode qualifier the claim text carries verbatim |
| `onslow_gaggle.html` | `policy_onslow_nc_schools` page | `https://www.onslow.k12.nc.us/departments/instructional-technology/cybersecurity-at-ocs/gaggle-safety-management` — the 'Gaggle Safety Management' page under Cybersecurity at OCS (I9b-C041, live-read F061) |
| `pflugerville_gaggle.html` | `policy_pflugerville_tx_isd` page | `https://www.pfisd.net/programs/safety-emergency-mgmt/gaggle` — the 'Gaggle' page under Safety & Emergency Management (I9b-C042, live-read F063) |
| `whitesboro_lightspeed.html` | `policy_whitesboro_ny_csd` page | `https://www.wboro.org/departments/information-and-instructional-technology/lightspeed-alert` — the 'Lightspeed Alert' page (I9b-C043, live-read F064): the product literal is "Lightspeed Alert"; the reviewed vendor pin is Lightspeed Systems |

## The `agency_policy` seats (`document_page` / clause-literal path)

Each `agency_policy_*.json` is the connector's document envelope: a
`policy_clauses` document whose `§`-headed text carries the reviewed literals
the clause locator addresses; the `clauses` rows are the reviewed
clause→predicate map (the same data the `document_page` live targets carry
inline — `live_targets.toml`).

| fixture | models | upstream surface (reviewed) |
|---|---|---|
| `agency_policy_orange_county.json` | `policy_orange_county_ca_sheriff` | `https://ocsheriff.gov/sites/ocsd/files/2023-06/Policy%20610%20Cellular%20Site%20Simulator%20Usage%20and%20Privacy.pdf` — Policy 610 (I4-C109, live-read I4-F095): § 610.1 cites Government Code section 53166 and names the authorized uses; § 610.7.2's internal annual report to the Sheriff (Lexipol-authored; facts only, RB-07) |
| `agency_policy_pasadena.json` | `policy_pasadena_ca_pd` | `https://ww2.cityofpasadena.net/2024%20Agendas/Jan_22_24/AR%208%20ATTACHMENT%20A.pdf` — Policy 620, Council agenda 2024-01-22 item 8 (I4-C110, live-read I4-F104): CPOC/IPA consultation clause + the annual report to the Chief/IPA/Public Safety Committee/City Council (Lexipol-authored; facts only, RB-07) |
| `agency_policy_ca_53166.json` | `legis_ca_gov_code_53166` | `https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=53166` — Cal. Gov. Code § 53166 (I4-C120, live-read I4-F094): the posted-usage-and-privacy-policy mandate + the acquisition-approval gate |
| `agency_policy_bangor.json` | `policy_bangor_me_pd` | `https://www.bangormaine.gov/DocumentCenter/View/4872/BPD---Policy--for-Unmanned-Aerial-Systems-PDF` — G.O. 2-59 'Unmanned Aerial Systems' (I9b-C108, live-read F137): effective 2025-10-05 |
| `agency_policy_houston.json` | `policy_houston_tx_hpd` | `https://www.houstontx.gov/police/general_orders/index.htm` — the General Orders index (I5-C110, live-read): the verbatim order titles 400-12 Surveillance Equipment, 400-28 Body Worn Cameras, 400-29 Automated License Plate Recognition (the claim value cites the order number — the title's plate phrase is a Part VIII forbidden token) |
| `agency_policy_albuquerque.json` | `policy_albuquerque_nm_apd` | `https://www.cabq.gov/police/standard-operating-procedures` — the APD SOP manual entry for SOP 1-22 'Automated License Plate Reader Program' (I5-C111, live-read): the claim cites the verbatim header 'Effective: 07/17/2023 Review: 07/17/2024 Replaces: 09/08/2021' (the title's plate phrase is a Part VIII forbidden token) |
| `agency_policy_little_rock.json` | `policy_little_rock_ar_pd` | `https://public.powerdms.com/LITTLEROCKPD/documents/2098788` — G.O. 332 'Small Unmanned Aircraft Systems' on the PowerDMS public portal (I9b-C109, live-read F138): dated 2025-09-17, replaces 2025-06-17 |

## Digests (sha256 of the committed fixture bytes)

| fixture | sha256 | bytes |
|---|---|---|
| `agency_policy_albuquerque.json` | `aad20da207a632d3bbfd083f2ce00d63fb69a01a6b24249b3b98aaac2480d411` | 1634 |
| `agency_policy_bangor.json` | `acd1a93518214c0f29ee962d345e6484054918243d1833c43e718ef80c93640c` | 1573 |
| `agency_policy_ca_53166.json` | `41b97b99770a22970f651b2e3b0325244060e28c4b220f94272d1c6b748a973f` | 2159 |
| `agency_policy_houston.json` | `a20ce983cf5f5eb4460afa8591a35faddc367fb8c40b3214132f81ed6945d27d` | 2122 |
| `agency_policy_little_rock.json` | `3c43e73f38371da77abb87b4c694f44b3cc5b2d6342c8b5c226efeb0293a881c` | 1409 |
| `agency_policy_orange_county.json` | `746eefb6d27f2923559459791e17cab97ec3a8a98d3a56954c6ba2b4e0f33892` | 2076 |
| `agency_policy_pasadena.json` | `65545e076c56399fd6176a7aa8d7f98ad07bc3de710b4a1f9008a3d3f7b8dfc9` | 2155 |
| `anchorage_ao_2023_78.txt` | `f65b90a3894e62327abf22a30bde3eeb993b9881718d0b4785d0d31200b61959` | 781 |
| `austin_trust_resolution.txt` | `90517664b602bcd3019070835ece16148090fa9c428b01e2eb1687435e7b588a` | 496 |
| `columbia_mo_report.txt` | `be07dae5e775836a3887528832920aa8ff7ac7f8c4277b5b4947c82397448f14` | 797 |
| `dayton_oh_index.html` | `ceaa911b5676bb4ed52630e00b1f4ddb18e420eea8e985069f21ccfb3026ef32` | 654 |
| `dayton_oh_report.txt` | `8813ec5fef0599ab55476c49f7204f584f317ba114250304c71572fc24ab5c3d` | 496 |
| `onslow_gaggle.html` | `11dd38e7b7f3bf85832f7909382df979a5329fd165c62ce7f0944f2dc543d457` | 304 |
| `pflugerville_gaggle.html` | `1d5db5368a8fc0c37540adc092c4bd436bd31d6975bf5a9811e4a005c9e9a03d` | 301 |
| `st_cloud_securly.html` | `30d6a9c6c03b5a5c1e88741fdb2e08235fd9906d1ea2adb605d21c3013949ca7` | 505 |
| `st_louis_mo_index.html` | `4f3e0e17a319bcaae8a133d1983f19d6f8ce4dae23096a9f1013a743ace0c718` | 862 |
| `st_louis_mo_report.txt` | `ce52a1c26255aabe4dc635843a4a06ca1438e1fd2ecbbc79ce7ee40ccebc9db8` | 573 |
| `whitesboro_lightspeed.html` | `4adac09ec2f6656d094b1500d44b39a3f6ea55fe250b5e689a413526aebc4757` | 342 |
