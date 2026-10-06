# I7: HG-03 rights-decision packets for the new source candidates

Row **I7** of `META_PLAN.md` (Stage P), companion to `research/I7-candidates.md` and `data/candidates_consolidated.csv`.
Written 2026-09-30 (`date -u` 21:37:14Z) by Claude Code (Opus 5.5), planning HEAD `8e25b48e`. Read-only: nothing was flipped,
no registry, ledger, queue or packet file was edited, and every proposed registry row stays `ingestion_permitted = false`.

> **Not legal advice (P4).** These packets set out captured facts, options and recorded precedents. Every decision is the
> operator's under **HG-03**; the agent decides nothing. "Precedent-consistent" means only "matches what an earlier recorded
> decision did with the same class of facts". Part VIII screens are a separate gate from rights: a rights line never
> clears a Part VIII flag.

**Standing rule (GL-GATE-07, 2026-09-18, verbatim as recorded in E4):** *"We should ungate the D-SOURCES.12-1 257 gated
datasets and for all the 'rights review' cases we should err on the side of approving them"*; execution rule US →
`LicenseRef-PublicRecord-FactualCompilation`, non-US → `LicenseRef-OperatorAccepted-DBRight`, reviewer a role and never a
name. **Q-19** (META_PLAN §7) is still open: whether GL-GATE-07 is the default for new sources. The recommendation recorded
there — per-batch packets with GL-GATE-07 as the default, anything Part-VIII-flagged decided individually — is the shape of
this document.

**Coverage vocabulary** (E4): **EXECUTED** (already flipped; nothing owed) · **PRECEDENT** (the facts match a row the rule's
execution already flipped; one line confirms) · **ARGUABLE** (the words reach it, no execution applied it to these facts) ·
**NOT COVERED** (terms affirmatively restrictive, deferred by name, or not a rights question).

**Scope.** 694 unique candidates (`data/candidates_consolidated.csv`). Tier 3 (259) requests no acquisition decision, the
widening group W (46) is configuration under sources already flipped, and 15 Tier-2 rows map onto existing E4 lines (B1/B2/B6
queue rows, R4a Edmonton, R6a/S2 vendor procurement platforms; SRC-027 is E4 B3 and Tier 3). That leaves **374 Tier-1/Tier-2
candidates** that need an HG-03 line before Round 11 can register them; this document reduces them to **10 batch lines, 9 Part
VIII screen lines and 35 individual rights lines**, plus Q-30, 11 conflict lines and 4 confirmations (§1).

---

## 1. Decision table — answer one line per row (e.g. `RB-01: a`, `S4: b`, `N3: c`)

### 1.1 Batch lines (rights)

| line | batch | n (T1/T2) | GL-GATE-07 | options | precedent-consistent | new facts first? |
|---|---|---|---|---|---|---|
| **RB-01** | US agency GIS/open-data layers (Flock/LPR/CCTV/ATE/PCAM aggregates on ArcGIS, Socrata, CKAN) | 38 (32/6) | PRECEDENT: P26.16 `camreg_*` flips, incl. items with licence "none" (`camreg_txdot_rep_tx`) and portal terms uncaptured (`camreg_chicago_il`) | **a** flip all under GL-GATE-07 US · **b** per target after an org-level terms capture · **c** defer | a | no |
| **RB-02** | US state DOT / state camera layers (DE, VT, WV, MI, NC …) | 8 (5/3) | PRECEDENT: `dot_511_la/ga/al/md` flipped 2026-09-18 and live | **a** flip under GL-GATE-07 US · **b** per target · **c** defer | a | no |
| **RB-03** | US statutory, oversight, CCOPS and policy documents (state reports, AG registries, CCOPS reports, police policies) | 57 (41/16) | PRECEDENT: P29.3 CCOPS flips (`ccops_oakland`, `_cambridge`, `_somerville` → PublicRecord), `okcpd_policy`, ADR-085 derived-facts basis (`ccops_seattle`) | **a** flip, PublicRecord-FactualCompilation · **a′** flip, DerivedFacts-Citations where only facts + citations are emitted · **b** per target · **c** defer | a or a′ | no |
| **RB-04** | US agenda, procurement, grant and records documents outside the live platforms | 38 (13/25) | PRECEDENT: `okc_council`, `okc_procurement`, the `procportal_*` flips, `legistar` (US local public records) | **a** flip under GL-GATE-07 US · **b** per target · **c** defer | a | no |
| **RB-05** | US federal works (DHS privacy documents, DOJ, CBP, Federal Register, courts, OMB) | 17 (6/11) | PRECEDENT: `usaspending`, `gao_surveillance_reports`, `dhs_oig_reports`, `fema_hsgp_allocations` (17 U.S.C. §105 → CC0-1.0); DOJ (I7-F033) and CBP (I7-F070) state public domain | **a** flip, CC0-1.0 · **b** per target · **c** defer | a | no |
| **RB-06** | explicit open licence or public-domain statement (CC-BY, CC0/"Public Domain" metadata, OGL, OGL-Canada, Etalab, NLOD, Auteurswet art. 11, WTSC's copy/distribute statement) | 46 (9/37) | PRECEDENT: GL-GATE-06 flips on verbatim licence metadata (`procportal_nyc_ny` "Public Domain" → CC0-1.0; the OGL UK rows) | **a** flip on the verbatim licence · **b** per target · **c** defer | a | for OGL-Canada rows, read the dataset record (site terms are non-commercial, IT-lines) |
| **RB-06b** | share-alike licences (CC-BY-SA, ODbL) | 4 (all Part VIII-flagged; decide with S-lines) | PRECEDENT + a compartment decision (§42.3; `osm_physical`, the CC-BY-SA `portal` compartment, J4 NEW-2) | **a** flip into a share-alike compartment · **b** facts only · **c** defer | a | no |
| **RB-07** | journalism, NGO and academic publications: facts + citations only | 15 (2/13) | PRECEDENT: P27.2 `state_alpr_statute_inventory` (NCSL, a private nonprofit → DerivedFacts-Citations), `pathways_*`, `carnegie_ai_gsi` | **a** flip, DerivedFacts-Citations (never re-host) · **b** per target · **c** defer | a | no |
| **RB-08** | territorial public records (Puerto Rico SUTRA measures, USVI legislature) | 8 (0/8) | ARGUABLE: GL-GATE-07's "US" wording reaches territories, but no territorial row was ever flipped (NEW-6). Guam's own public-domain statement (I7-F032) moved I9b-C093 to RB-06 | **a** treat territories as US under GL-GATE-07 · **b** capture each territory's terms first · **c** decline | none | b is available (SUTRA and legvi.org terms not captured) |
| **RB-09** | existing gated registry rows that a candidate matches (flip the row) | 4 (0/4) + 1 flagged | PRECEDENT per row: `dhs_fusion_centers` (federal §105), `ccops_boston`/`ccops_berkeley` (P29.3 CCOPS), `aclu_cell_site_simulators` (facts + citations) | **a** flip each existing row (E4 §2 recipe) · **b** keep gated | a | no |

Members of every batch are listed in §6 (appendix). Part-VIII-flagged candidates in a batch are **not** flipped by the
batch line alone: they need their screen line (§1.2) as well.

### 1.2 Part VIII screen lines (decided individually, per Q-19)

110 Tier-2 candidates carry a flag. Each is assigned to one screen class by its most restrictive flag; the members are listed
by name. Answer **a** to approve ingesting only the screened lane for the listed members, **b** to keep them metadata-only
(they move to Tier 3), or name the members to exclude.

| screen class (decision line) | n | members (cand id: short name) |
|---|---|---|
| S1 private-camera registrants: programme-level facts only; no registrant location, name or count below programme level (SIG-PUB-004 C3; J4 P8-4) | 24 | I5-C101: Project Green Light Locations; I3-C005: Flock_Camera_Locations2 (Savannah Poli…; I3-C008: Flock_Location_Data view (East Baton R…; I3-C009: FLOCK_CAMERAS_ASOF_20240318 (CCSO, wes…; I3-C011: City of Gastonia NC Flock layers: Cond…; I3-C006: Flock_Camera_Locations_Sep_2023 (City …; I4-C009: Vermont Law Enforcement Agency Drone U…; I3-C001: Agency-published Flock / LPR location …; I4-C016: Agency police drone flight-log / usage…; I9a-C038: Agency Fusus / real-time crime centre …; I4-C017: Police Drone Flights; I4-C018: Peoria Police Department Drone Usage; I4-C019: Drone Deployments FS; I9a-C001: Police private-camera registry program…; I3-C070: Eye on Surveillance - New Orleans surv…; I9a-C021: Cincinnati Police Department - volunta…; I9a-C004: Lafayette Police Department camera reg…; I9a-C005: Zionsville Police Department Camera Re…; I9a-C006: Narragansett Police camera registry pr…; I9a-C007: Calistoga Police Department Voluntary …; I9a-C008: Pinole Police Department Security Came…; I9a-C009: Dayton (MN) Police Department Resident…; I9a-C003: Axon Fusus agency-hosted 'Connect <Pla…; I3-C089: Chicago OEMC - Link Your Cameras (Priv… |
| S2 field allowlist: never request editor-tracking/operator/pilot fields; redacted re-serialisation only (J4 P8-5) | 4 | I3-C004: D4 - Camera Survey (FDOT District 4 RO…; I5-C104: Shotspotter and Metrocams_WFL1 (layers…; I5-C014: ITS_ATM - Existing Devices (NDOT State…; I4-C001: Part 107 Waivers Issued |
| S3 aggregate-only: publish institution-level counts; never rows (SIG-STORE-025) | 7 | I4-C057: Automated School Bus Camera Violations; I4-C050: ATE camera-location and per-camera agg…; I6-C038: CourtListener bulk data files (case la…; I4-C163: Upturn - Mass Extraction (2020), Appen…; I4-C281: ICE 287(g) monthly encounter reports (…; I9b-C047: City of Lincoln/Lancaster County, NE M…; I4-C209: EFF Red Flag Machine — GoGuardian reco… |
| S4 residential/RF: coarsen or aggregate; never a public point layer (SIG-PUB-011..014) | 13 | I5-C102: DPD ShotSpotter Incident Records; I5-C103: Detroit Street View CCTV Cameras; I3-C080: MPD Cameras Public View v2 (DC Metropo…; I3-C083: Security Camera Locations (City of San…; I9b-C050: Texas Government Code 423.008 biennial…; I9b-C052: San Antonio Police Department Helicopt…; I5-C105: Cleveland Police UAS Drone Transparenc…; I4-C307: Oakland Police Department Shotspotter …; I5-C220: Corona Camera Locations_WFL1; I4-C084: Violence Reduction - Shotspotter Alert…; I5-C219: ACCPD New Flock Camera Analysis Locati…; I5-C332: Department of Justice and Attorney-Gen…; I9b-C064: Duke Wilson Center for Science and Jus… |
| S5 officer names in institutional roles: §43.4 naming gate; no names from audit rows | 11 | I4-C086: Wiretap Appendix Tables A-1 (U.S. Dist…; I3-C040: Minnesota Legislative Reference Librar…; I4-C273: Maine Information and Analysis Center …; I4-C079: Teeter Report - Review of Contracts an…; I4-C012: California AB 481 military equipment u…; I4-C161: Placer County, CA Board of Supervisors…; I5-C028: Delaware State Police 2022 Annual Repo…; I5-C033: Providence Police Department 2023 Annu…; I4-C158: Jefferson County, MO Council - Bill 24…; I5-C225: Tribal Leaders Directory; I4-C157: Grayshift LLC quote Q-17510-1 to White… |
| S6 free text: SIG-PUB-014a pre-publication excerpt screen; facts only | 16 | I6-C025: Treasury SLFRF quarterly Project and E…; I6-C009: State of CT: Open Expenditures - Ledge…; I3-C027: Flock Expansion Map (Brazoria-area sta…; I4-C087: California Electronic Interceptions Re…; I9b-C051: Texas Parks and Wildlife Department La…; I4-C155: Maine DAFS Procurement Services - Proc…; I4-C308: Portland City Auditor — Audit Services…; I5-C100: Exhibit 1-3 - First/Second/Third ALPR …; I5-C338: Completed Access to Information Reques…; I5-C362: FragDenStaat request search API; I9b-C026: Utah Public Notice Website (utah.gov/p…; I4-C160: Miami-Dade County BCC - designated pur…; I9b-C073: DHS FOIA release: 'DHS Operational Use…; I4-C077: Agenda Report: Authorize the City Mana…; I4-C088: Authorize the City Manager to Execute …; I5-C339: FYI.org.nz — OIA requests to New Zeala… |
| S7 incidental private names (minutes, POs, contacts): extraction-time redaction (J4 P8-3/P8-6) | 30 | I6-C007: Texas DIR Cooperative Contracts vendor…; I3-C078: City of Mesa AZ - City Expenditures: p…; I4-C164: Socrata-hosted government vendor-payme…; I5-C226: Consulta del Registro de Contratos (Of…; I6-C008: Delaware Checkbook Expenditure Details…; I4-C156: Washington State Open Checkbook - vend…; I6-C014: City of Madison WI: Annual Surveillanc…; I9b-C090: City of Memphis quarterly financial pr…; I6-C015: City of Detroit: Community Input Over …; I9b-C013: Ingham County Board of Commissioners R…; I9b-C015: Manitowoc County Public Safety Committ…; I9b-C081: Spokane City Council Public Safety & C…; I4-C165: City of Chicago - Payments (s4vu-giwb); I9b-C035: District of Columbia Public Schools ne…; I9b-C063: Muscatine Police Department Automated …; I5-C364: SECOP II - Procesos de Contratación; I9b-C021: Boone County Purchasing memo: Amendmen…; I9b-C027: School Board of Clay County (FL) 2023-…; I9b-C029: Kentucky Department of Education - KET…; I9a-C035: Agency-hosted agenda attachments evide…; I9b-C025: City of La Vista council packet 2017-1…; I6-C039: Caselaw Access Project static bulk (st…; I4-C168: Citizen Lab - Virtue or Vice? A First …; I9b-C024: City of San Diego Purchasing - purchas…; I5-C334: Search Government Contracts over $10,0…; I9b-C044: City of St. Petersburg (FL) - Meetings…; I9b-C045: City of Virginia Beach (VA) City Clerk…; SRC-024: DLA LESO 1033 equipment holdings/trans…; I5-C224: Harris County renews contract for law …; I4-C166: Brennan Center - Map: Social Media Mon… |
| S8 tribal sovereignty: tribal-data-governance decision first | 2 | I5-C237: Coordinated Tribal Assistance Solicita…; I9b-C095: Tohono O'odham Legislative Branch - No… |
| S9 row-specific screen (family members, same-org hazard layers, signature blocks; see the row notes) | 3 | I4-C065: Additional US agency ATE items on ArcG…; SRC-004: San Diego Sunshine Act goods/services …; I3-C022: GardenCity_Flock_Cameras (Garden City,… |

Notes. S1 includes the Flock layers whose columns name private operators (Savannah, Brookhaven, East Baton Rouge, Gastonia,
"CCSO"): the screened lane is agency-operated cameras only, with private-operator rows reduced to a programme count. S2 keeps
the first attempt's re-verdicts (I5-C104, I5-C014 block → flagged under an `outFields` allowlist; I4-C001 block → flagged under
a column-drop screen) — answer **b** here to restore the block. S3 includes CourtListener bulk (party names; C8 below).

### 1.3 Individual rights lines

**Non-US database right (21 lines, N1…N21).** GL-GATE-07's non-US execution (`LicenseRef-OperatorAccepted-DBRight`) is the
precedent for each (e.g. `uk_surveillance_camera_commissioner`, the Calgary/York/Donegal/NZTA camera flips); each is listed
because Q-19 asks for non-US rights individually. Jurisdiction-conditional publication (SIG-PUB-017) applies to all of them.

| line | I7 id | cand | candidate | country | terms captured (verbatim excerpt or NONE) | tier | options |
|---|---|---|---|---|---|---|---|
| N1 | I7-U207 | I5-C319 | Traffic CCTV contract | GB-ENG:Barnet | CKAN license_id=None | 2 | a flip DBRight · b capture terms first · c decline |
| N2 | I7-U216 | I9b-C017 | NT Quotations and Tenders Online NS25-0080: Provis… | ISO:AU;AU-NT | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N3 | I7-U266 | I5-C328 | Security Camera | AU-TAS:Hobart | CKAN license_id=other (Other) | 2 | a flip DBRight · b capture terms first · c decline |
| N4 | I7-U301 | I5-C362 | FragDenStaat request search API | ISO:DE | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N5 | I7-U320 | I5-C311 | CCTV Cameras | GB-ENG:Leicester | CKAN license_id=None | 2 | a flip DBRight · b capture terms first · c decline |
| N6 | I7-U323 | I5-C317 | CCTV camera locations | GB-ENG:Barnet | CKAN license_id=None | 2 | a flip DBRight · b capture terms first · c decline |
| N7 | I7-U324 | I5-C318 | CCTV Traffic Enforcement - camera locations | GB-ENG:Barnet | CKAN license_id=None | 2 | a flip DBRight · b capture terms first · c decline |
| N8 | I7-U325 | I5-C320 | Council CCTV cameras | GB-ENG:Bristol | CKAN license_id=None | 2 | a flip DBRight · b capture terms first · c decline |
| N9 | I7-U326 | I5-C323 | Public CCTV locations - City of Edinburgh | GB-SCT:Edinburgh | CKAN license_id=None | 2 | a flip DBRight · b capture terms first · c decline |
| N10 | I7-U329 | I5-C327 | Closed Circuit Television (CCTV) Location | AU-VIC:Geelong | CKAN license_id=other-open (Other (Open)) | 2 | a flip DBRight · b capture terms first · c decline |
| N11 | I7-U330 | I5-C329 | Street safety cameras | AU-NSW:Sydney | CKAN license_id=notspecified (notspecified) | 2 | a flip DBRight · b capture terms first · c decline |
| N12 | I7-U331 | I5-C331 | Emergency Services - Closed Circuit Television Cam… | AU-TAS | CKAN license_id=notspecified | 2 | a flip DBRight · b capture terms first · c decline |
| N13 | I7-U333 | I5-C347 | Provvedimento dell'11 gennaio 2024 [9977020] (Comu… | IT-TN:Trento | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N14 | I7-U338 | I5-C359 | Дані про місцезнаходження камер відеоспостереження… | UA-18:Korosten | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N15 | I7-U356 | I5-C303 | Joint assurance review: retrospective facial searc… | GB-SCT | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N16 | I7-U374 | I5-C321 | Clackmannanshire - CCTV Cameras | GB-SCT:Clackmannan… | CKAN license_id=None | 2 | a flip DBRight · b capture terms first · c decline |
| N17 | I7-U380 | I5-C354 | Evidenca o izvajanju videonadzora na javnih površi… | SI-085:Novo mesto | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N18 | I7-U411 | I5-C306 | L&RS General Scheme Briefing Paper: Garda Síochána… | ISO:IE | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N19 | I7-U412 | I5-C361 | Gobierto Contratación — licitación ALC0230 (Illesc… | ES-TO:Illescas | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N20 | I7-U419 | I5-C339 | FYI.org.nz — OIA requests to New Zealand Police (e… | ISO:NZ | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |
| N21 | I7-U430 | I5-C357 | Videoüberwachung in der Stadt Braunschweig | DE-NI:Braunschweig | NONE-FOUND | 2 | a flip DBRight · b capture terms first · c decline |

**Restricted or conditional terms (IT lines).** Captured terms carry a non-commercial clause, an agreement or a condition
that GL-GATE-07's execution never covered.

| line | I7 id | cand | candidate | tier | terms captured (verbatim excerpt) / basis | GL-GATE-07 | options |
|---|---|---|---|---|---|---|---|
| IT1 | I7-U161 | I6-C027 | OpenFEMA: Non-Disaster and Assistance to Firefight… | 2 | OpenFEMA Terms and Conditions (I7-F004): "FEMA may rescind your use of the data if FEMA believes that it does not serve the public interest. You agree you will cease using the data and destroy any copy you may have if requested by FEMA." and "you agr | ARGUABLE (not a redistribution prohibition, but a destroy-on-request c… | a flip (accept the condition) · b facts-only pointer · c decline |
| IT2 | I7-U184 | I4-C063 | Speed Safety Cameras (Bellevue) | 2 | Disclaimer: The information on this map is a geographic representation derived from the City of Bellevue Geographic Information System. The City of Bellevue does not guarantee that the information on this map is accurate or complete. This map is provided on an… | ARGUABLE (express non-commercial clause on the same publisher — decide… | a flip (accept the condition) · b facts-only pointer · c decline |
| IT3 | I7-U219 | I9b-C101 | PSPC collaborative procurement - 'Service request … | 2 | …: "Unless otherwise specified you may reproduce the materials in whole or in part for non-commercial purposes, and in any format, without charge or further permission" and "Unless otherwise specified, you may not reproduce materials on this site, in  | ARGUABLE (non-commercial clause; decide with E4 R4d) | a flip (accept the condition) · b facts-only pointer · c decline |
| IT4 | I7-U299 | I5-C337 | GETS - Government Electronic Tenders Service | 2 | …e deemed to have accepted the terms of this Agreement." and users warrant they "will keep confidential all Confidential Information, login information and all information identified as being commercially sensitive that you access from GETS and will n | ARGUABLE (agreement terms bind any user; public notices vs confidentia… | a flip (accept the condition) · b facts-only pointer · c decline |
| IT5 | I7-U316 | I5-C112 | Honolulu Police Department policy - Automated Lice… | 2 | Honolulu Police Department disclaimer: "Commercial use of any document or image contained on these web pages is prohibited." Footer: "Copyright © 2026 The Honolulu Police Department. All rights reserved." (I7-F020) | ARGUABLE (express non-commercial clause; decide with E4 R4d: is SIG's … | a flip (accept the condition) · b facts-only pointer · c decline |
| IT6 | I7-U318 | I5-C304 | Special report to Parliament: Police use of Facial… | 2 | OPC Canada terms: "Unless otherwise specified, you may reproduce the materials in whole or in part and in any format for non-commercial purposes, without charge or further permission" (I7-F034) | ARGUABLE (non-commercial clause; decide with E4 R4d) | a flip (accept the condition) · b facts-only pointer · c decline |
| IT7 | I7-U396 | I9a-C003 | Axon Fusus agency-hosted 'Connect <Place>' camera … | 2 | prohibits: automated access on Axon properties (Axon ToS captured by I3: no robots, spiders or page-scrape) - agency subdomains are Axon white-label sites — NONE-FOUND(checked: /privacy-faqs/) | NOT COVERED (captured Axon terms prohibit automated access; decide wit… | a flip (accept the condition) · b facts-only pointer · c decline |

**Terms not captured (IU lines).** Vendor, aggregator or platform terms were not captured; the row's facts are usable only as
citations until they are.

| line | I7 id | cand | candidate | tier | terms captured (verbatim excerpt) / basis | GL-GATE-07 | options |
|---|---|---|---|---|---|---|---|
| IU1 | I7-U232 | I9a-C040 | Leonardo (ELSAG) 'Procurement Contracts' page - st… | 2 | vendor/aggregator terms not captured or not reviewed — NONE-FOUND(checked: page; only a Data Privacy Policy link) | ARGUABLE (terms not captured — new facts first) | a capture terms first (Round 11) · b facts + citation only now · c decline |
| IU2 | I7-U283 | I4-C159 | Carahsoft - Cellebrite government contract vehicle… | 2 | vendor/aggregator terms not captured or not reviewed — NONE-FOUND(checked: carahsoft.com/cellebrite/contracts) | ARGUABLE (terms not captured — new facts first) | a capture terms first (Round 11) · b facts + citation only now · c decline |
| IU3 | I7-U310 | I4-C262 | Google - Geofence Warrants by Jurisdiction, 2018 t… | 2 | Google Terms of Service: "Some of our services include content that belongs to Google … You may use Google’s content as allowed by these terms and any service-specific additional terms , but we retain any intellectual property rights that we have in our conten… | ARGUABLE (terms not captured — new facts first) | a capture terms first (Round 11) · b facts + citation only now · c decline |
| IU4 | I7-U363 | I9b-C080 | SoundThinking press releases - named customer rene… | 2 | vendor/aggregator terms not captured or not reviewed — NONE-FOUND(checked I7-F062;I7-F075 https://www.soundthinking.com/ + /terms-of-use: landing page links only a privacy policy; guessed terms path HTTP 404) | ARGUABLE (terms not captured — new facts first) | a capture terms first (Round 11) · b facts + citation only now · c decline |
| IU5 | I7-U425 | I3-C065 | FlockRadar - map of disclosed ALPR / Flock deploym… | 2 | code AGPL-3.0 (README badge); data licence not stated | ARGUABLE (terms not captured — new facts first) | a capture terms first (Round 11) · b facts + citation only now · c decline |

**Tribal governance (TR lines).** NEW-6: neither GL-GATE-07 basis reaches a sovereign tribal publisher or tribal-keyed
geography.

| line | I7 id | cand | candidate | tier | terms captured (verbatim excerpt) / basis | GL-GATE-07 | options |
|---|---|---|---|---|---|---|---|
| TR1 | I7-U355 | I5-C225 | Tribal Leaders Directory | 2 | No warranty is made by the Bureau of Indian Affairs (BIA) for the use of the data for purposes not intended by the BIA. This GIS Dataset may contain errors. There is no impact on the legal status of the land areas depicted herein and no impact on land ownershi… | PRECEDENT (federal §105 → CC0-1.0: usaspending, gao_surveillance_repor… | a defer until a tribal-data-governance rule exists · b ask the Nation (outreach, Q-28 class) · c facts + citation only |
| TR2 | I7-U364 | I9b-C095 | Tohono O'odham Legislative Branch - Notice of publ… | 2 | tribal sovereign publisher - the US public-record basis (state/municipal records law) does not apply — NONE-FOUND(checked: document only) | NOT COVERED (tribal nation; GL-GATE-07 execution never reached a sover… | a defer until a tribal-data-governance rule exists · b ask the Nation (outreach, Q-28 class) · c facts + citation only |

**Existing gated registry rows (RG lines; the members of RB-09).**

| line | I7 id | cand | candidate | tier | terms captured (verbatim excerpt) / basis | GL-GATE-07 | options |
|---|---|---|---|---|---|---|---|
| RG1 | I7-U370 | I4-C270 | DHS Fusion Center Locations and Contact Informatio… | 2 | federal work (17 U.S.C. §105; inference) — NONE-FOUND(checked: https://www.dhs.gov/fusion-center-locations-and-contact-information) | PRECEDENT (federal §105 → CC0-1.0: usaspending, gao_surveillance_repor… | a flip the existing row (flip recipe, E4 §2) · b keep gated |
| RG2 | I7-U424 | SRC-020 | Boston annual surveillance report and supplements | 2 | US state/local/territorial public record — NONE-FOUND(queue: terms not captured at S5) | PRECEDENT (GL-GATE-07 US → LicenseRef-PublicRecord-FactualCompilation:… | a flip the existing row (flip recipe, E4 §2) · b keep gated |
| RG3 | I7-U426 | I4-C001 | Part 107 Waivers Issued | 2 | federal work (17 U.S.C. §105; inference) — NONE-FOUND(checked: https://www.faa.gov/uas/commercial_operators/part_107_waivers/waivers_issued; faa.gov host stopped at F004) | PRECEDENT (federal §105 → CC0-1.0: usaspending, gao_surveillance_repor… | a flip the existing row (flip recipe, E4 §2) · b keep gated |
| RG4 | I7-U427 | I4-C123 | Stingray Tracking Devices: Who's Got Them? (ACLU m… | 2 | ©-only (expression reserved; no operative prohibition on facts) — NONE-FOUND(checked: https://www.aclu.org/issues/privacy-technology/surveillance-technologies/stingray-tracking-devices) | PRECEDENT (facts + citations only → LicenseRef-DerivedFacts-Citations:… | a flip the existing row (flip recipe, E4 §2) · b keep gated |
| RG5 | I7-U435 | SRC-019 | Berkeley surveillance annual reports policies MOUs | 2 | US state/local/territorial public record — NONE-FOUND(queue: terms not captured at S5) | PRECEDENT (GL-GATE-07 US → LicenseRef-PublicRecord-FactualCompilation:… | a flip the existing row (flip recipe, E4 §2) · b keep gated |

**Blocked on the contact string (P16 / Q-30).** Not a rights question: SEC EDGAR requires a declared contact user-agent, and
P16 forbids sending the operator's identity. One line: **Q-30: approve a project contact string (e.g. a project alias) —
yes / no.** Until then these rows stay Tier 2.

| line | I7 id | cand | candidate | tier | terms captured (verbatim excerpt) / basis | GL-GATE-07 | options |
|---|---|---|---|---|---|---|---|
| P1 | I7-U171 | I4-C304 | Verra Mobility Corp — Form 10-K for fiscal 2025 (a… | 2 | SEC public filings (vendor-authored text; facts only) — NONE-FOUND(checked: https://www.sec.gov/Archives/edgar/data/1682745/000119312526067293/) | ARGUABLE (no SEC-filing precedent; facts-only extraction) | blocked on Q-30; no rights line until a contact string is approved |
| P2 | I7-U186 | I4-C153 | Cellebrite DI Ltd. SEC filings (Form 20-F annual r… | 2 | SEC public filings (vendor-authored text; facts only) — NONE-FOUND(checked: efts.sec.gov search JSON; sec.gov cele-20251231.htm; sec.gov ea026501001ex99-1_cellebrite.htm) | ARGUABLE (no SEC-filing precedent; facts-only extraction) | blocked on Q-30; no rights line until a contact string is approved |
| P3 | I7-U231 | I6-C043 | SEC EDGAR full-text search (efts) - multi-vendor s… | 2 | SEC public filings (vendor-authored text; facts only) — NONE-FOUND(checked: API response) | ARGUABLE (no SEC-filing precedent; facts-only extraction) | blocked on Q-30; no rights line until a contact string is approved |
| P4 | I7-U343 | I4-C082 | SoundThinking, Inc. (formerly ShotSpotter, Inc.) F… | 2 | SEC public filings (vendor-authored text; facts only) — NONE-FOUND(checked: F055) | ARGUABLE (no SEC-filing precedent; facts-only extraction) | blocked on Q-30; no rights line until a contact string is approved |

### 1.4 Confirmations (default recorded; answer only to change it)

| line | what | default |
|---|---|---|
| **X1** | the 19 Tier-3 candidates whose captured terms affirmatively prohibit (§3.7) stay declined; facts from them are used only as pointers to origins | keep declined |
| **X2** | the 26 Part VIII blocks (§3.8) are recorded as existence/metadata only, never ingested | confirm |
| **X3** | the 46 W configurations need no new HG-03 line: each runs under an already-flipped or rights-resolved source (`legistar`, `usaspending`, `osm_overpass`, `procportal_nyc_ny`, the P27.2-resolved statute seed) | confirm |
| **X4** | registry and tenant label corrections M1–M7 (§5) go into a Round-11 correction ticket (engineering, not rights) | approve |

### 1.5 Tally

| kind | lines |
|---|---|
| batch lines (RB-01…RB-09 incl. RB-06b) | 10 |
| Part VIII screen lines (S1…S9) | 9 |
| individual rights lines: N1…N21, IT1…IT7, IU1…IU5, TR1…TR2 | 35 (the 5 RG rows are RB-09's members; RB-09 decides them unless per-row answers are given) |
| Q-30 (contact string) | 1 |
| conflicts (§4) | 11 |
| confirmations (§1.4) | 4 |

Precedent-consistent answers exist for all ten batch lines except RB-08. A one-line answer that applies the Q-19
recommendation would read: *"RB-01…RB-07, RB-09: a; RB-06b: a; RB-08: b; S1–S9: a; N-lines: a; IT/IU/TR: per line;
X1–X4: confirm"* — the operator may of course answer otherwise.

---

## 2. Conventions: what a decision records, and how it is verified

Unchanged from E4 §2 (the flip recipe, the decline recipe, and the verification commands), with two additions:

- **New rows first.** A candidate with `proposed_registry_action = new-source` has no registry row yet. The Round-11 ticket adds
  the row from the CSV's proposed fields (`proposed_source_id`, `proposed_name`, `proposed_publisher`, `proposed_licence`,
  `proposed_cadence`) with `ingestion_permitted = false`, then applies the flip recipe only if the operator's line says so.
  The loader also needs `compact_status` in {permission_granted, permission_granted_conditional, public_terms_only,
  partnership_active} and a `custody_posture` in {MIRROR, DERIVE, REFERENCE} (`connectors/loader.py:94-116`; E4 NEW-11).
- **Screened lanes are recorded.** A Part VIII **a** answer records the screen class (S1…S9) in the row's notes and in the
  Round-11 ticket's Part VIII preflight, and the connector emits only the screened lane (J4 §9 rules P8-3…P8-8).

Verify per source, exactly as E4: `uv run sig-connectors review-status --source <id>`, `gate --source <id>`, `validate`,
`export-check`, and `run --source <id> --mode live` no longer exiting 3.

---

## 3. Batch packets (facts per batch)

### 3.1 RB-01 — US agency GIS/open-data layers
- **Facts.** 38 layers from city, county, sheriff and state agencies on ArcGIS Online, Socrata and CKAN. Most record
  `licenseInfo` empty (`NONE-FOUND(checked: ArcGIS item licenseInfo …)` in the row). Cook County's register carries a Socrata
  "Public Domain" licence (I7-F006; it sits in RB-06). Chicago's portal terms (I7-F001) carry a revocation condition (C5).
- **Lineage.** Agency origin shown for every member; three layers without an agency organisation were moved to Tier 2 for a
  verification step and are not in this batch (NEW-5).
- **Precedent.** P26.16 flipped 257 catalog-sweep rows under GL-GATE-07 on the same fact pattern (E4 R3 cites
  `camreg_txdot_rep_tx`, licence "none", flipped and live).
- **Raw vs derived (J4).** `derived-only`; raw bytes only as a field-allowlisted re-serialisation (P8-5).

### 3.2 RB-02 — US state DOT / state camera layers
- **Facts.** DelDOT FirstMap (copyrightText "DelDOT"), VTrans ITS device list, WVDOH (I7-F017: disclaimer only, no licence
  clause), MDOT MiDrive, NCDOT (org misclassified as a non-state mirror, I5 NEW-5), NM "ITS511" (authority unverified, Tier 2).
- **Precedent.** `dot_511_la/ga/al/md` (P26.16) and `dot_511_ky/ut/or/wa/dc/mo` (CC0 or PD metadata).
- **Part VIII.** P8-7: never proxy, capture or thumbnail imagery.

### 3.3 RB-03 — US statutory, oversight, CCOPS and policy documents
- **Facts.** State statutory reports (NE, VT, IL, MN, MD, ME, HI, PA, FL, WA), AG registries (WA AGO 76 agencies, I9a-C036; the
  AGO page links only a privacy notice, I7-F025), CCOPS-type reports and ordinances (Columbia MO, St. Louis, Dayton, Anchorage,
  Austin), police policies (Houston, Albuquerque, Bangor, Little Rock, Charlotte), district student-monitoring pages. Captured
  site terms add no restriction beyond footers ("All rights reserved", I7-F018, F050, F065; MSP terms I7-F067).
- **Precedent.** P29.3 flipped municipal CCOPS reports and a UK body under GL-GATE-07 (`rights/p293_dispositions.json`);
  `okcpd_policy` was flipped as government records (GL-GATE-03).
- **Raw vs derived.** `derived-only`; excerpts pass the SIG-PUB-014a screen (P8-2).

### 3.4 RB-04 — US agenda, procurement, grant and records documents
- **Facts.** Tier 1: the WA DES master-contract sales register, single council resolutions and memos (Haskell AR, Des Moines,
  Jasper County SC, Davie FL, the Forsyth County RTCC RFP), the Detroit PD weekly FR report, and state grant programme documents
  (TxDMV MVCPA, CA BSCC, FL LFIR, AL ADECA, NJ OAG BWC, SRC-009). Tier 2: agenda portals that need a new connector (Fargo, Jersey
  City, Durham, Hialeah, Frisco, Tampa, Omaha, Anchorage, Memphis and five large county boards), cooperative K-12 contracts
  (Florida Buy, NERIC) and state BWC grant documents. BidNet Direct and Bonfire storefronts are not in this batch: they ride with
  E4 R6a/S2. Utah Legislature terms add an attribution condition for commercial use (I7-F047).
- **Precedent.** `okc_council`, `okc_procurement`, the `procportal_*` flips.

### 3.5 RB-05 — US federal works
- **Facts.** DHS privacy-document indexes and PIAs (I4-C167, C259, C260, C261, C269; DHS policy page I7-F008), DOJ (I7-F033: "in
  the public domain and may be copied and distributed without permission"), CBP (I7-F070: "in the public domain and may be
  reproduced, published or otherwise used"), the Federal Register, US Courts tables, the OMB AI use-case inventory, ICE 287(g)
  (I7-F003: "may be distributed or copied").
- **Precedent.** 17 U.S.C. §105 → CC0-1.0 (`usaspending`, `gao_surveillance_reports`, `dhs_oig_reports`, `fema_hsgp_allocations`).

### 3.6 RB-06 / RB-06b / RB-07 / RB-08
- **RB-06** members carry the licence verbatim in their row or in an I7 capture: DC GIS CC-BY-4.0, Montgomery County and Cook
  County "Public Domain", Suffolk County CC-BY-4.0, GOV.UK OGL (I7-F024), CNIL CC-BY-ND 4.0 FR for texts (I7-F027; images are
  CC-BY-NC-ND), NL official publications free to re-use under Auteurswet art. 11 (I7-F078) and the NL algorithm register's
  re-use statement (I7-F036), WTSC (I7-F073), Guam (I7-F032).
- **RB-06b** members are all Part-VIII-flagged: Detroit street-view CCTV (CC-BY-SA), the Cleveland UAS dashboard (ODbL), the
  Socrata checkbook family (I4-C164; per-portal licences) and Colombia's SECOP II; the compartment decision rides with their
  S-lines.
- **RB-07** members are facts-only: The Frontier allows republication with a byline (I7-F029), the UW terms prohibit
  reproduction of expression (I7-F046), WSIPC's fair-use statement (I7-F030).
- **RB-08** members: seven Puerto Rico SUTRA measures and the USVI legislature release; no territorial terms were captured.

### 3.7 Tier-3 candidates whose captured terms prohibit (X1)

| line | I7 id | cand | candidate | registry | prohibition (captured) | tier | options |
|---|---|---|---|---|---|---|---|
| T1 | I7-U440 | I6-C002 | OMNIA Partners supplier page: Flock Safety (publ… | related:omnia_partners |  automated access / scraping | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T2 | I7-U441 | I9b-C036 | OMNIA Partners - Gaggle supplier page and public… | related:omnia_partners |  scraping/crawling/compiling (OMNIA site terms, same site as I6-C002) | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T3 | I7-U442 | I5-C008 | Existing_ITS_Device_Service_view (TxDOT_ITS_Devi… | related:dot_511_tx |  redistribution without written consent | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T4 | I7-U464 | I5-C300 | Emergent technologies proactive information rele… | new |  reproduction/distribution without permission | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T5 | I7-U477 | I5-C301 | Police use of Automatic Number Plate Recognition… | new |  reproduction/distribution without permission | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T6 | I7-U478 | I6-C001 | Sourcewell cooperative contract 101223-AXN (Axon… | same-as:sourcewell |  automated access / scraping | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T7 | I7-U521 | I3-C085 | HAZARD: RegisteredCameraLocations (Town of Flowe… | new | (row researcher: bytes prohibited-by-terms) | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T8 | I7-U523 | I3-C047 | CrimeWatch agency Camera Registry web forms (e.g… | new |  automated access | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T9 | I7-U524 | I3-C086 | Police private-camera registration programmes ev… | related:camreg_osm_surveillance | (row researcher: bytes prohibited-by-terms) | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T10 | I7-U550 | I5-C217 | Maricopa County Regional GIS | new |  internal-use-only; external distribution needs written authorization | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T11 | I7-U553 | I5-C400 | MDOTtraffic (Mississippi DOT traveler map; camer… | new |  non-commercial, revocable use only | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T12 | I7-U563 | I3-C062 | Axon Community Connect - community listing (Regi… | same-as:axon_community_connect |  automated access / scraping | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T13 | I7-U569 | I5-C012 | IDrive Arkansas Traffic Camera Terms of Use | new |  image rights reserved; embedding prohibited | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T14 | I7-U572 | I5-C302 | OIA - Number of ANPR cameras (IR-01-22-37568) | new |  reproduction/distribution without permission | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T15 | I7-U581 | I3-C090 | Flock Safety community camera-registration pages… | related:flock_api_terms |  bulk extraction / scraping of Flock’s website or APIs (I7-F012) | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T16 | I7-U583 | I4-C200 | SDPC Resource Registry — District Agreements Lis… | new |  member-only access; no onward availability | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T17 | I7-U644 | I6-C031 | MuckRock (requests, projects, API v1) | same-as:muckrock |  data mining / extraction tools | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T18 | I7-U645 | I6-C032 | Pittsboro Police Department 'Flock Safety shared… | related:documentcloud |  data mining / extraction tools | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |
| T19 | I7-U667 | I3-C068 | Michigan Flock transparency archive (Cantica-Sys… | related:flock_transparency_portals | (row researcher: bytes prohibited-by-terms) | 3 | a keep declined (pointer/facts-only) · b seek written consent · c flip despite terms |

### 3.8 Part VIII blocks (X2)

| I7 id | cand | candidate | flags | what may be used |
|---|---|---|---|---|
| I7-U443 | I3-C031 | MO License Plate Reader (LPR) Success Stories survey (Missou… | private-person-name;person-level-enforcement;officer-name | existence/metadata only |
| I7-U444 | I3-C032 | New ALPR Location Request (Cuyahoga County OEM Survey123) | private-person-name | existence/metadata only |
| I7-U445 | I3-C036 | HAZARD: publicly readable ArcGIS layers holding ALPR plate r… | plate-level;per-search-audit;person-level-enforcement;free-text-narrative | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U459 | I3-C037 | All license plate reader data (ALPR) - Oakland per-read data… | plate-level | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U472 | I4-C059 | MTA Bus Automated Camera Enforcement Violations: Beginning O… | plate-level (vehicle_id column: per-vehicle identifier, reversible-derivative risk);person… | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U521 | I3-C085 | HAZARD: RegisteredCameraLocations (Town of Flower Mound, TX)… | home-address;private-person-name;private-registrant-location;operator-identifier | existence/metadata only |
| I7-U524 | I3-C086 | Police private-camera registration programmes evidenced by A… | private-registrant-location;private-person-name;home-address | existence/metadata only |
| I7-U525 | I4-C015 | UAV Flight Log | operator-identifier(FAA pilot certificate number column);home-address(Street Address (Area… | existence/metadata only |
| I7-U528 | I4-C277 | NOPD Body Worn Camera Metadata | residential-intersection;free-text-narrative;operator-identifier(suspected: evidence_id/id… | existence/metadata only |
| I7-U564 | I4-C060 | Traffic Camera Citations | person-level-enforcement (recipient_zip_code/recipient_city/recipient_state + notice_numbe… | existence/metadata only |
| I7-U566 | I4-C169 | ACLU of Northern California - Geofeedia records from Califor… | private-person-name;free-text-narrative | existence/metadata only |
| I7-U610 | I9b-C076 | Brennan Center - DC Metropolitan Police Department Social Me… | free-text-narrative;private-person-name;person-level-enforcement | existence/metadata only |
| I7-U631 | I4-C213 | Florida Statutes §1001.212 — Office of Safe Schools (Florida… | minor-data (Portal integrates social-media posts, DCF/DJJ/FDLE records, FortifyFL tips — p… | existence/metadata only |
| I7-U632 | I4-C220 | Gaggle response letter to Senators Warren, Markey and Blumen… | minor-data (quotes redacted student alert excerpts);private-person-name (school staff name… | existence/metadata only |
| I7-U639 | I4-C101 | Facial Recognition Report - annual judicial report of FR war… | officer-name;per-search-audit | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U648 | I3-C028 | Municipal GIS feeds built for Flock integration (FlockOS add… | officer-name;free-text-narrative | existence/metadata only |
| I7-U650 | I5-C108 | v2. Community Camera Partnership (Survey123 form service) | private-registrant-location;home-address | existence/metadata only |
| I7-U651 | I5-C109 | HPD C.A.P.T.U.R.E Program (web map) | private-registrant-location;home-address | existence/metadata only |
| I7-U656 | I9a-C002 | Polaris 'CameraKit' camera-registry platform (polaris.camera… | private-registrant-location;home-address;private-person-name | existence/metadata only |
| I7-U662 | I4-C106 | 25 MRSA §6001 facial surveillance - public-record de-identif… | per-search-audit;officer-name | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U666 | I3-C064 | FlockWatch corpus (rhowardstone/flockwatch-data) - 99.4M ALP… | per-search-audit;officer-name;plate-level;free-text-narrative;operator-identifier | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U667 | I3-C068 | Michigan Flock transparency archive (Cantica-Systems/mi-floc… | per-search-audit;operator-identifier;free-text-narrative | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U680 | I9b-C072 | Schools use AI to monitor kids, hoping to prevent violence. … | minor-data;free-text-narrative | existence/metadata only |
| I7-U686 | I4-C029 | FAA Aircraft Registry (N-number inquiry / releasable aircraf… | home-address(registrant addresses for individual owners);private-person-name | existence/metadata only |
| I7-U693 | I9a-C045 | Wausau Pilot & Review 'Watch Ledger' - Wisconsin statewide A… | plate-level;per-search-audit;operator-identifier | existence/metadata only; aggregate lane only if the publisher aggregates |
| I7-U694 | SRC-027 | San Diego ALPR network audit metadata and safe aggregate fea… | license_plate;personal_identifier | existence/metadata only; aggregate lane only if the publisher aggregates |

---

## 4. Conflicts (decide individually)

| line | conflict | facts (captured) | options | precedent-consistent |
|---|---|---|---|---|
| **C1** | **TxDOT origin terms vs the flipped `camreg_txdot_rep_tx`** (I5 NEW-3; E4 R3) | TxDOT's org-standard `licenseInfo` on its own items (I5-C008): *"Distribution of this content to third parties without TxDOT's written consent is strictly prohibited"* and *"may not be used for commercial purposes or resold"*. `camreg_txdot_rep_tx`, a third-party republish of TxDOT camera points, was flipped under GL-GATE-07 on 2026-09-18 and is live; `dot_511_tx` (another personal-account republish) is E4 R3 | **a** keep the flip; publish derived facts only and quote the TxDOT clause in the row notes (J4 Q-J4-2) · **b** restrict `camreg_txdot_rep_tx` pending TxDOT consent (a new rights decision; append-only) · **c** seek TxDOT written consent | none (GL-GATE-07 recorded DB-right risk, not an express prohibition, J4 §4) |
| **C2** | **DocumentCloud / MuckRock "no data mining"** | `documentcloud` declined 2026-09-17 (E4 R2a): MuckRock ToS excludes *"data mining, robots, or similar data gathering and extraction tools"*. Candidates hosted there (I4-C264 Fog Data Science records, I6-C032 Pittsboro Flock sharing lists, I4-C004 FAA COA list on MuckRock; I4-C119 WHYF derived from DocumentCloud) | **a** link-only; acquire each origin agency's release instead · **b** named-document review one by one (E4 R2a option c) | a |
| **C3** | **Sourcewell and OMNIA prohibit robots and reproduction** vs registry rows `sourcewell` ("Dominant acquisition channel") and `omnia_partners` | Sourcewell (I6-C001): *"You may not reproduce, distribute … Use automated tools such as robots or spiders to access or copy content."* OMNIA (I6-C002, I9b-C036): *"you shall not: (a) use any robot, spider … for the purpose of 'scraping,' 'crawling,' harvesting"* | **a** contract-id pointers only; acquire purchases from agency-side records (checkbooks, agendas, state sales registers) · **b** seek permission · **c** decline both rows | a (I6 Q3) |
| **C4** | **Vendor platform terms** | Axon ToS (no robots, spiders or page-scrape; I3-C062, I9a-C003 Fusus Connect white-label sites), CrimeWatch (*"Use any automated system … without our prior written consent"*, I3-C047), Flock API terms (*"extract, scrape, or export data in bulk"*, I3-C090, I7-F012) | **a** programme facts only from the agencies' own pages; no fetch from vendor hosts · **b** seek vendor permission · **c** decline | a |
| **C5** | **Revocation / destroy-on-request** (NEW-3) | Chicago (I7-F001) and Albuquerque (I7-F021): *"The City may require a user of this data to terminate any and all display, distribution or other use"*; OpenFEMA (I7-F004): *"destroy any copy you may have if requested by FEMA"* — against an insert-only spine and immutable releases | **a** accept, with a withdrawal-by-new-claim policy (suppress from future releases; history kept) · **b** accept Chicago/ABQ (city portals, already flipped) but decline the OpenFEMA API route (FEMA pages stay the funding source) · **c** decline all three | none |
| **C6** | **Non-commercial clauses** (NEW-2; E4 R4d) | Bellevue (*"Any commercial use or sale of this map … is prohibited"*), Honolulu PD (I7-F020), Canada.ca (I7-F026), OPC Canada (I7-F034), CNIL images (I7-F027); plus the live J4 NEW-1 rows (Keizer, TRPA CC BY-NC, Cal OES NC-ND) | one operator statement: **a** SIG's use and exports are non-commercial (then flip) · **b** they are, or may be, commercial (then decline or seek permission) | none (R4d) |
| **C7** | **SDPC registry is member-only** (I4-C200) | *"You are allowed access to the Registry because you are an employee, official or agent of an existing member of SDPC"*; *"You may not … make the Registry available to … anyone other than Users"* | **a** facts only from district-side pages · **b** partnership · **c** decline | a |
| **C8** | **CourtListener bulk vs the deferred `courtlistener_recap`** (I6 NEW-1; E4 R2b) | Bulk files: *"free of known copyright restrictions"* (Public Domain Mark); GL-GATE-07 defers CourtListener by name ("FLP agreement stays OPEN") | **a** a new per-source basis (PDM) for the bulk route only, S3 screen for party names · **b** keep deferred with R2b | none |
| **C9** | **NCSL inventory vs statutes at origin** | P27.2 recorded NCSL as a private nonprofit (DerivedFacts-Citations); the 2026 refresh (W) cites the legislature origins instead, which are public records | **a** refresh the seed from origins (W, X3) · **b** keep the frozen seed | a |
| **C10** | **SEC EDGAR contact string vs P16** | EDGAR requires a declared contact user-agent; P16 forbids the operator's identity (I4 NEW-11 incident; I9a NEW-4) | Q-30 | — |
| **C11** | **Edmonton basis** (E4 R4a) | The City's terms page is titled *"Open Government Licence - Edmonton"* (I7-F011; body JS-rendered), while the registry records no licence for `camreg_edmonton_ab`; I4-C066 is the same dataset | **a** decide R4a on the OGL-Edmonton basis once the body is captured · **b** keep R4a's DB-right option | E4 R4a a |

---

## 5. Registry and tenant label corrections (engineering; one approval line X4)

| line | where | defect | correction | raised by |
|---|---|---|---|---|
| M1 | `agenda_tenants.toml [tenants.charlotte_ia]` | `jurisdiction = "City of Charlotte, IA"` for tenant `charlottenc` | Charlotte, NC (14th-largest US city) | I5 NEW-1 |
| M2 | `agenda_tenants.toml [tenants.san_bernardino_ca]` (Legistar) | labelled City of San Bernardino; the tenant serves the San Bernardino **County** Board of Supervisors (a separate PrimeGov tenant of the same name is also labelled City — verify which is the city) | San Bernardino County, CA | I5 NEW-2 |
| M3 | `agenda_tenants.toml [tenants.concord_ca]` | tenant `concordnh` labelled Concord, CA | Concord, NH (tier-A state) | I5 NEW-4 |
| M4 | `agenda_tenants.toml [tenants.newark]`, `[tenants.clark]` | "unresolved" | Newark, NJ; Clark County, NV | I5 NEW-4 |
| M5 | `agenda_tenants.toml [tenants.carrollton_ga]` | tenant `carrolltontx` labelled Carrollton, GA | Carrollton, TX | I3 NEW-3 |
| M6 | NCDOT ArcGIS org `NuWFvHYDMVmmxMeM` | classified as a non-state "runneals" account | NCDOT (state origin) | I5 NEW-5 |
| M7 | `sources.toml [sources.faa_drone_waivers]` | homepage points at the generic faa.gov UAS page; DFR authorizations are Part 91.113 waivers | point at the Part 107 and Part 91.113 waiver tables | I4 NEW-7 |
| (M8) | candidates I9b-C002, I4-C066 | recorded `new`; they are `procportal_nyc_ny` and `camreg_edmonton_ab` | none in the registry; dedupe on dataset ids (I8) | I7 NEW-1 |

---

## 6. Appendix — batch members

Each table lists the batch's members with the proposed registry row from the CSV (`proposed_source_id`, proposed licence) and
the terms evidence. Tier-2 members also need the blocker in their `tier_reason` resolved; the rights line does not do that.

### RB-01 US agency GIS/open-data layers

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U003 | I5-C005 | Traffic Devices - Red Light Signals (DE_Boundary_and_Po… | Delaware Department of Transportation (D… | 1 | `camreg_de_traffic_devices_red` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U005 | I3-C084 | Private Security Camera Rebate Program and Voucher Prog… | District of Columbia Office of Victim Se… | 1 | `camreg_dc_private_security_camera` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U012 | I3-C002 | D3 Flock Camera Data (FDOT District 3 Safety Informatio… | Florida Department of Transportation, Di… | 1 | `camreg_fl_d3_flock_camera` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U013 | I3-C003 | FLOCK removal status layer (FDOT) | Florida Department of Transportation (vi… | 1 | `camreg_fl_flock_removal_status` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U014 | I3-C007 | Flock (City of Pueblo, CO) | City of Pueblo, CO (via ArcGIS Online) | 1 | `camreg_pueblo_co_flock` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U015 | I3-C012 | LPR_Cameras (City of Rocky Mount, NC) | City of Rocky Mount, NC (via ArcGIS Onli… | 1 | `camreg_rocky_mount_nc_lpr_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U016 | I3-C014 | Flock Cameras - Public (City of Shelbyville, TN) | City of Shelbyville, TN (via ArcGIS Onli… | 1 | `camreg_shelbyville_tn_flock_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U017 | I3-C015 | Flock_WFL1 (City of Temecula, CA) | City of Temecula, CA (staff account, via… | 1 | `camreg_temecula_ca_flock_wfl1` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U018 | I3-C017 | Flock Locations (City of Marble Falls, TX) | City of Marble Falls, TX (via ArcGIS Onl… | 1 | `camreg_marble_falls_tx_flock_locations` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U019 | I3-C019 | Community Safety Cameras (Prince William County, VA) | Prince William County, VA (via ArcGIS On… | 1 | `camreg_prince_william_cou_va_community_safet` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U020 | I3-C020 | FlockLPRCam (Milford, CT) | "Milford" org (extent Milford, CT; via A… | 1 | `camreg_milford_ct_flocklprcam` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U021 | I3-C023 | LPR Cameras (City of Elgin, IL) | City of Elgin, IL (via ArcGIS Online) | 1 | `camreg_elgin_il_lpr_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U022 | I3-C024 | LPR Cameras (City of South Fulton, GA) | City of South Fulton, GA (via ArcGIS Onl… | 1 | `camreg_south_fulton_ga_lpr_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U023 | I3-C025 | Stationary LPR (Pittsylvania County, VA) | Pittsylvania County, VA (via ArcGIS Onli… | 1 | `camreg_pittsylvania_count_va_stationary_lpr` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U024 | I3-C026 | LPR_Cameras (City of Alabaster, AL staff account) | City of Alabaster, AL (city-staff accoun… | 1 | `camreg_alabaster_al_lpr_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U026 | I4-C053 | Speed Camera Violations | City of Chicago, Department of Transport… | 1 | `camreg_chicago_il_speed_camera_violations` | LicenseRef-PublicRecord-FactualCompila… | I7 capture (first attempt) |
| I7-U027 | I4-C054 | Red Light Camera Violations | City of Chicago, Department of Transport… | 1 | `camreg_chicago_il_red_light_camera` | LicenseRef-PublicRecord-FactualCompila… | I7 capture (first attempt) |
| I7-U028 | I4-C058 | MTA Bus Automated Camera Enforced Routes: Beginning Oct… | Metropolitan Transportation Authority (N… | 1 | `camreg_new_york_city_ny_mta_bus_automated` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U029 | I4-C061 | Automated Enforcement Locations (Tacoma) | City of Tacoma, Public Works (ArcGIS Onl… | 1 | `camreg_tacoma_wa_automated_enforcement_locat` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U030 | I4-C062 | SpeedCameras_2024 (MCPD Speed camera Locations as of Au… | Montgomery County (MD) Police Department… | 1 | `camreg_montgomery_county_md_speedcameras_202` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U031 | I4-C064 | SchZoneHighligh (school zones where automated enforceme… | Howard County, MD (Socrata) | 1 | `camreg_howard_county_md_schzonehighligh` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U036 | I9b-C084 | Red Light Cameras and Direction (City of Lakeland, FL A… | City of Lakeland, FL (via ArcGIS Online) | 1 | `camreg_lakeland_fl_red_light_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U037 | I3-C010 | FLOCK_Location (City of Thomasville, GA) | City of Thomasville, GA (org name via Ar… | 1 | `camreg_thomasville_ga_flock_location` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U038 | I3-C013 | Leon County Sheriff's Office Overwatch Viewer (VIGILANT… | Tallahassee-Leon County GIS for Leon Cou… | 1 | `camreg_leon_county_fl_overwatch_viewer` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U039 | I3-C018 | Flock_Camera_Location (City of Peachtree Corners, GA) | City of Peachtree Corners, GA (via ArcGI… | 1 | `camreg_peachtree_corners_ga_flock_camera_loc` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U044 | I5-C107 | Traffic_Cameras / Traffic Operations - Public Monitorin… | City of Lincoln, NE Traffic Operations (… | 1 | `camreg_lincoln_ne_traffic_cameras_traffic` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U056 | I5-C106 | Parks_Cameras (City of Omaha-maintained cameras; Colleg… | Douglas-Omaha GIS (DOGIS) for City of Om… | 1 | `camreg_omaha_ne_parks_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U068 | I9b-C082 | Red Light_Speed Camera (City of Medford, OR ArcGIS orga… | City of Medford, OR (via ArcGIS Online) | 1 | `camreg_medford_or_red_light_speed` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U070 | I3-C082 | Hyattsville CCTV Camera Program 2024 | City of Hyattsville, MD (cohgis) | 1 | `camreg_hyattsville_md_cctv_camera_2024` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U075 | I5-C015 | Approximate Speed Safety Camera Locations Public | Connecticut Department of Transportation… | 1 | `camreg_ct_approximate_speed_safety` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U086 | I3-C079 | Police HALO Cameras (Denver Police Department) | City and County of Denver (geospatialDEN… | 1 | `camreg_denver_co_halo_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U087 | I3-C081 | Seattle Police Department CCTV Pilot Areas | City of Seattle (SPD GIS) | 1 | `camreg_seattle_wa_cctv_pilot_areas` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U162 | I3-C016 | flock (City of Jeffersonville, IN) | City of Jeffersonville, IN (staff accoun… | 2 | `camreg_jeffersonville_in_flock` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U163 | I3-C021 | Flock camera locations / Flock Camera Map (Monterey Par… | City of Monterey Park, CA (two city-staf… | 2 | `camreg_monterey_park_ca_flock_camera_locatio` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U169 | I4-C171 | New Jersey YourMoney - Agency Purchasing (ubnu-tqu7) | State of New Jersey, Treasury - Division… | 2 | `camreg_nj_new_jersey_yourmoney` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U173 | I5-C040 | Park Cameras (City of Santa Fe park camera locations) | City of Santa Fe, NM Parks (layer publis… | 2 | `camreg_santa_fe_nm_park_cameras` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U178 | I9b-C048 | City of St. Petersburg, Florida - ArcGIS Online organis… | City of St. Petersburg, FL (GIS) | 2 | `camreg_st_petersburg_fl_florida_arcgis_onlin` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U311 | I4-C275 | ArcGIS-hosted fusion-centre layers (Alabama GeoHub dire… | CA Governor's Office of Emergency Servic… | 2 | `camreg_us_arcgis_hosted_fusion` | LicenseRef-PublicRecord-FactualCompila… | none captured |

### RB-02 US state DOT/state GIS camera layers

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U002 | I5-C003 | Traffic Devices - CAMERA (DE_Boundary_and_Point layer 2… | Delaware Department of Transportation (D… | 1 | `dot_511_de` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U007 | I5-C001 | ITS - DeviceList (DeviceLocDetail) | Vermont Agency of Transportation, Operat… | 1 | `dot_511_vt` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U008 | I5-C009 | CCTV_WVDOH (WVDOT Assets MapServer layer 22) | West Virginia Department of Transportati… | 1 | `dot_511_wv` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F017 |
| I7-U011 | I5-C002 | MiDrive Cameras | Michigan Department of Transportation (v… | 1 | `dot_511_mi` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U090 | I5-C017 | NCDOT_Cameras | North Carolina Department of Transportat… | 1 | `dot_511_nc` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U157 | I5-C010 | CCTV_WVPA (WVDOT Assets MapServer layer 23) | West Virginia Parkways Authority cameras… | 2 | `dot_511_wv_2` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F017 |
| I7-U172 | I5-C006 | Statewide CCTV View | NMDOT ITS CCTV inventory per item snippe… | 2 | `dot_511_nm` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U259 | I5-C018 | Closed-Circuit Television (CCTV) (ITD IntelligentTransp… | Idaho Transportation Department (ArcGIS … | 2 | `dot_511_id` | LicenseRef-PublicRecord-FactualCompila… | row-captured |

### RB-03 US statutory/oversight/policy documents

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U032 | I4-C103 | Facial Recognition Technology - Arvada Police Departmen… | City of Arvada, CO (CivicPlus site) | 1 | `statrep_arvada_co_facial_recognition_technol` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F068 |
| I7-U033 | I6-C018 | City of Columbia MO: 2025 Annual Surveillance Technolog… | City of Columbia, MO (Columbia Police De… | 1 | `ccops_columbia_mo` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U034 | I9b-C053 | Annual Report of the Department of Public Safety on Mai… | Maine Department of Public Safety (repor… | 1 | `statrep_me_safety_maine_law` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F053 |
| I7-U035 | I9b-C078 | Hawai'i Judiciary report under HRS 803-47(b) - applicat… | Hawai'i State Judiciary (communication t… | 1 | `statrep_hi_hawai_judiciary_under` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F052 |
| I7-U040 | I3-C039 | Agencies that use License Plate Readers (LPR) - Minneso… | Minnesota Department of Public Safety, B… | 1 | `statrep_mn_agencies_that_use` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F064;I7-F071 |
| I7-U041 | I4-C100 | Facial Recognition / WaTech (Technology Services Board … | Washington Technology Solutions (WaTech)… | 1 | `statrep_wa_facial_recognition_watech` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U042 | I4-C102 | Colorado agency facial recognition accountability repor… | Colorado state and local agencies using … | 1 | `statrep_co_colorado_agency_facial` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F068 |
| I7-U043 | I4-C274 | Delaware Information and Analysis Center (DIAC) Privacy… | Delaware Information and Analysis Center… | 1 | `statrep_de_delaware_information_analysis` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U045 | I6-C040 | Virginia Reports to the General Assembly (RGA) - publis… | Virginia Division of Legislative Automat… | 1 | `statrep_va_virginia_general_assembly` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U046 | I9a-C036 | Washington Attorney General's Office - Automated Licens… | Washington State Office of the Attorney … | 1 | `statrep_wa_washington_attorney_general` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F025 |
| I7-U049 | I3-C042 | Virginia State Police - ALPR Reporting Requirements (v2… | Virginia Department of State Police, CJI… | 1 | `statrep_va_virginia_alpr_reporting` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U050 | I3-C043 | Virginia State Crime Commission - Law Enforcement Use o… | Virginia State Crime Commission | 1 | `statrep_va_virginia_crime_commission` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U057 | I6-C016 | City of St. Louis: Police Department Surveillance Techn… | Metropolitan St. Louis Police Department… | 1 | `ccops_st_louis_mo` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U058 | I6-C017 | City of Dayton OH: Surveillance Technology (annual repo… | City of Dayton, OH (Dayton Police Depart… | 1 | `ccops_dayton_oh` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F022 |
| I7-U061 | I9a-C011 | Nebraska Crime Commission - Automatic License Plate Rea… | Nebraska Commission on Law Enforcement a… | 1 | `statrep_ne_nebraska_crime_commission` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U062 | I9a-C012 | Vermont Department of Public Safety - annual report on … | Vermont Department of Public Safety (dep… | 1 | `statrep_vt_vermont_safety_automated` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F018 |
| I7-U064 | I9b-C056 | Florida Department of Highway Safety and Motor Vehicles… | Florida Department of Highway Safety and… | 1 | `statrep_fl_florida_highway_safety` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F065 |
| I7-U065 | I9b-C057 | Pennsylvania Work Zone Speed Safety Camera (WZSSC) Prog… | Pennsylvania Department of Transportatio… | 1 | `statrep_pa_pennsylvania_work_zone` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F050 |
| I7-U066 | I9b-C065 | Maryland Department of State Police - Report Required b… | Maryland Department of State Police | 1 | `statrep_md_maryland_required_chapters` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F067 |
| I7-U067 | I9b-C077 | Minnesota State Court Administrator - Report to Legisla… | Minnesota Judicial Branch, State Court A… | 1 | `statrep_mn_minnesota_court_administrator` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F054 |
| I7-U069 | I9b-C088 | Anchorage Municipal Code chapter 3.102 'Municipal Use o… | Municipality of Anchorage, AK (Assembly;… | 1 | `ccops_anchorage_ak` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F058 |
| I7-U077 | I9a-C047 | Maryland Department of Legislative Services Library - M… | Maryland General Assembly, Department of… | 1 | `statrep_md_maryland_legislative_library` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F055 |
| I7-U080 | I4-C069 | 2024-2025 Automated Traffic Safety Camera Program Annua… | City of Seattle, Seattle Department of T… | 1 | `statrep_seattle_wa_2024_2025_automated` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U081 | I9a-C019 | Illinois State Police - Automated License Plate Reader … | Illinois State Police, Division of Crimi… | 1 | `statrep_il_illinois_automated_license` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F048;I7-F072 |
| I7-U085 | I9b-C068 | Arizona HB 2574 (56th Legislature, 2nd Regular Session,… | Arizona House of Representatives (bill s… | 1 | `legis_az_arizona_hb_2574` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U088 | I4-C005 | Unmanned Aerial Vehicle (UAV) annual reports (Minn. Sta… | Minnesota Department of Public Safety, B… | 1 | `statrep_mn_unmanned_aerial_vehicle` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F064;I7-F071 |
| I7-U089 | I4-C006 | Illinois Freedom From Drone Surveillance Act annual rep… | Illinois Criminal Justice Information Au… | 1 | `statrep_il_illinois_freedom_from` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U092 | I9a-C042 | City of Austin Office of the City Auditor - 'APD Licens… | City of Austin, TX Office of the City Au… | 1 | `statrep_austin_tx_auditor_apd_license` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U093 | SRC-012 | Seattle OIG annual surveillance usage reviews | Seattle Office of Inspector General (OIG… | 1 | `statrep_seattle_wa_oig_surveillance_usage` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U094 | I4-C120 | California Government Code § 53166 - cellular communica… | California Legislature | 1 | `legis_ca_california_code_53166` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U095 | I9a-C022 | City of Austin TX - Transparent and Responsible Use of … | City of Austin, TX City Council | 1 | `ccops_austin_tx` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U096 | I9b-C040 | District student-monitoring self-disclosure pages (scho… | US school districts (each district is th… | 1 | `policy_us_district_student_monitoring` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U097 | I9b-C069 | New York Senate Bill S7037 (2025): 'social media monito… | New York State Senate | 1 | `legis_ny_new_york_senate` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U101 | I9b-C030 | St. Cloud Area School District (ISD 742) - 'Securly' pa… | St. Cloud Area School District ISD 742, … | 1 | `policy_st_cloud_mn_area_school_district` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U102 | I9b-C041 | Onslow County Schools (NC) - 'Gaggle Safety Management'… | Onslow County Schools, NC | 1 | `policy_onslow_county_nc_schools_gaggle_safet` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U103 | I9b-C042 | Pflugerville ISD (TX) - 'Gaggle' page (Safety & Emergen… | Pflugerville Independent School District… | 1 | `policy_pflugerville_tx_isd_gaggle_page` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U104 | I9b-C043 | Whitesboro Central School District (NY) - 'Lightspeed A… | Whitesboro Central School District, NY | 1 | `policy_whitesboro_ny_central_school_district` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U105 | I9b-C108 | Bangor Police Department General Order 2-59 'Unmanned A… | City of Bangor, ME (Police Department) | 1 | `policy_bangor_me_general_order_59` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U106 | I5-C110 | Houston Police Department General Orders | Houston Police Department | 1 | `policy_houston_tx_general_orders` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U107 | I5-C111 | APD Standard Operating Procedures (incl. SOP 1-22 Autom… | Albuquerque Police Department | 1 | `policy_albuquerque_nm_apd_standard_operating` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F021 |
| I7-U108 | I9b-C109 | Little Rock Police Department General Order G.O. 332 'S… | City of Little Rock, AR (Police Departme… | 1 | `policy_little_rock_ar_general_order_332` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U210 | I9a-C013 | Utah agency ALPR policies posted under Utah Code 41-6a-… | Utah law-enforcement agencies (e.g. Utah… | 2 | `statrep_ut_utah_agency_alpr` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U211 | I9a-C014 | California SB 34 ALPR usage and privacy policies posted… | California ALPR operators/end-users (pol… | 2 | `statrep_ca_california_sb_34` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U313 | I5-C013 | iDriveCCTV_20260707_v2 (ARDOT I-30 project CCTV snapsho… | Garver (engineering consultant) ArcGIS O… | 2 | `policy_ar_idrivecctv_20260707` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U340 | SRC-015 | NYC DOI OIG-NYPD surveillance oversight | NYC Department of Investigation — OIG-NY… | 2 | `statrep_new_york_ny_nyc_doi_oig` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F039 |
| I7-U359 | I9a-C027 | Florida DOT memorandum EOM26-01 (2026-08-31) - removal … | Florida Department of Transportation | 2 | `legis_fl_florida_dot_memorandum` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U366 | SRC-016 | NYC Comptroller surveillance procurement and audits | NYC Comptroller | 2 | `statrep_new_york_ny_nyc_comptroller_surveill` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F039 |
| I7-U390 | I9b-C087 | Charlotte-Mecklenburg Police Department - Interactive D… | City of Charlotte, NC (Charlotte-Mecklen… | 2 | `policy_charlotte_nc_mecklenburg_interactive` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U393 | I4-C311 | SFPD Department General Order 6.21 — Investigative Soci… | San Francisco Police Department | 2 | `policy_san_francisco_ca_sfpd_general_order` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U404 | I9a-C039 | Elizabeth City (NC) Police Department memorandum 'AXON … | City of Elizabeth City, NC Police Depart… | 2 | `policy_elizabeth_city_nc_memorandum_axon_ent` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U406 | SRC-017 | Chicago OIG ShotSpotter evaluation and follow-up | Chicago Office of Inspector General | 2 | `statrep_chicago_il_oig_shotspotter_evaluatio` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U407 | SRC-018 | BART surveillance reports policies and public decisions | San Francisco Bay Area Rapid Transit Dis… | 2 | `ccops_san_francisco_bay_ca` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U410 | I4-C312 | Michigan State Police Official Order No. 07-09 — Celleb… | Michigan State Police (via PowerDMS publ… | 2 | `policy_mi_michigan_official_order` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U414 | SRC-013 | San Jose privacy decisions and algorithm register | City of San José (Digital Privacy / IT) | 2 | `ccops_san_jose_ca` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U415 | SRC-021 | Santa Clara County surveillance impact and oversight | Santa Clara County (privacy/oversight of… | 2 | `ccops_santa_clara_county_ca` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U418 | I5-C221 | MCSO Policies (Critical, Detention, Enforcement, Genera… | Maricopa County Sheriff's Office | 2 | `policy_maricopa_county_az_mcso_policies` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U423 | SRC-014 | Norman police ALPR policy and amendment discovery | City of Norman / Norman Police Departmen… | 2 | `policy_norman_ok_alpr_policy_amendment` | LicenseRef-PublicRecord-FactualCompila… | none captured |

### RB-04 US agenda/procurement/grant/records documents

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U004 | I6-C010 | Washington DES Statewide Contract (Master Contract) Sal… | Washington State Department of Enterpris… | 1 | `procportal_wa_washington_des_statewide` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U047 | I9a-C052 | City of Haskell AR Resolution No. 19-2025 - contract wi… | City of Haskell, AR City Council | 1 | `agenda_haskell_ar_resolution_no_19` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U053 | I4-C108 | Detroit Police Department Weekly Report on Facial Recog… | City of Detroit, MI - Detroit Police Dep… | 1 | `agenda_detroit_mi_weekly_facial_recognition` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F023 |
| I7-U059 | I6-C028 | Texas DMV Motor Vehicle Crime Prevention Authority (MVC… | Texas Department of Motor Vehicles, Moto… | 1 | `grant_tx_texas_dmv_motor` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U060 | I6-C029 | California BSCC Organized Retail Theft (ORT) Prevention… | California Board of State and Community … | 1 | `grant_ca_california_bscc_organized` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U063 | I9a-C043 | Florida Legislature - Local Funding Initiative Requests… | The Florida Senate (Local Funding Initia… | 1 | `grant_fl_florida_legislature_local` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F074 |
| I7-U076 | I9a-C041 | Alabama ADECA newsroom - Governor's Project Safe Neighb… | Alabama Department of Economic and Commu… | 1 | `grant_al_alabama_adeca_newsroom` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F019 |
| I7-U078 | I9b-C058 | New Jersey OAG SFY21 Body-Worn Camera Grant Program - P… | State of New Jersey, Department of Law a… | 1 | `grant_nj_new_jersey_oag` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U082 | I9a-C034 | City of Des Moines IA council communication 26-235 (202… | City of Des Moines, IA (City Council com… | 1 | `agenda_des_moines_ia_communication_26_235` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U083 | I9b-C003 | Jasper County Council special called meeting agenda e-p… | Jasper County, SC (County Council) | 1 | `agenda_jasper_county_sc_special_called_meeti` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U084 | I9b-C004 | Town of Davie Notice of Intent to Award a Sole Source P… | Town of Davie, FL (Purchasing) | 1 | `procportal_davie_fl_notice_intent_award` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U091 | I5-C135 | RFP2449 Real-Time Intelligence Center Enterprise Soluti… | Winston-Salem / Forsyth County Purchasin… | 1 | `procportal_forsyth_county_nc_rfp2449_real_ti` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U099 | SRC-009 | Oklahoma JAG-LLE local equipment funding | Oklahoma District Attorneys Council (JAG… | 1 | `grant_ok_oklahoma_jag_lle` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U155 | I3-C076 | Municipal contract / expenditure registers on Socrata a… | Multiple US cities/counties (Socrata) | 2 | `procportal_us_contract_expenditure_registers` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U189 | I5-C042 | Fargo City Commission Agendas & Minutes | City of Fargo, ND | 2 | `agenda_fargo_nd_commission_agendas_minutes` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F040 |
| I7-U190 | I5-C124 | Jersey City Digital Agenda (Municipal Council portal) | City of Jersey City, NJ Municipal Counci… | 2 | `agenda_jersey_city_nj_digital_agenda` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U191 | I5-C125 | Agenda Center - Durham, NC (CivicEngage) | City of Durham, NC | 2 | `agenda_durham_nc_agenda_center` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F041 |
| I7-U192 | I5-C126 | Agenda Center - Hialeah, FL (CivicEngage) | City of Hialeah, FL | 2 | `agenda_hialeah_fl_agenda_center` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U193 | I5-C127 | Frisco OnBase Agenda Online | City of Frisco, TX | 2 | `agenda_frisco_tx_onbase_agenda_online` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U194 | I5-C128 | Tampa City Council OnBase Agenda Online | City of Tampa, FL | 2 | `agenda_tampa_fl_onbase_agenda_online` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U196 | I9b-C006 | Florida Buy (PAEC) State Cooperative Purchasing Program… | Panhandle Area Educational Consortium (P… | 2 | `procportal_fl_florida_buy_cooperative` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U197 | I9b-C070 | Massachusetts Capital Investment Plan FY2025-2029 - lin… | Commonwealth of Massachusetts, Executive… | 2 | `grant_ma_massachusetts_capital_investment` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U215 | I9b-C016 | Savannah City Council 2023-05-25 item 17: Authorize the… | City of Savannah, GA (City Council, Agen… | 2 | `agenda_savannah_ga_2023_05_25` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U217 | I9b-C037 | Northeastern Regional Information Center (NERIC, Capita… | NERIC (Capital Region BOCES regional inf… | 2 | `procportal_ny_northeastern_regional_informat` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U243 | I4-C252 | Illinois GATA CSFA 569-00-3496 ILETSB Law Enforcement C… | Illinois Law Enforcement Training and St… | 2 | `grant_il_illinois_gata_csfa` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U260 | I5-C115 | Board of Police Commissioners (BOPC) | City of Detroit Board of Police Commissi… | 2 | `agenda_detroit_mi_commissioners` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F023 |
| I7-U261 | I5-C129 | Omaha City Clerk - City Council agendas | City of Omaha, NE City Clerk | 2 | `agenda_omaha_ne_clerk_agendas` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U262 | I5-C130 | Anchorage Assembly - Meetings | Municipality of Anchorage Assembly | 2 | `agenda_anchorage_ak_assembly_meetings` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F058 |
| I7-U263 | I5-C131 | Memphis City Council meeting agenda | City of Memphis, TN City Council | 2 | `agenda_memphis_tn_meeting_agenda` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U284 | I4-C253 | Ohio Office of Criminal Justice Services Body-Worn Came… | Ohio Department of Public Safety, Office… | 2 | `grant_oh_ohio_criminal_justice` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U285 | I4-C255 | Massachusetts Law Enforcement Body-Worn Camera Program … | Commonwealth of Massachusetts, EOPSS Off… | 2 | `grant_ma_massachusetts_law_enforcement` | LicenseRef-PublicRecord-FactualCompila… | row-captured |
| I7-U290 | I5-C208 | Wayne County Commission — committee meeting pages (incl… | Wayne County Commission, Michigan (Grani… | 2 | `agenda_wayne_county_mi_commission_committee` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U348 | I5-C202 | Maricopa County Board of Supervisors — AgendaOnline (Cl… | Maricopa County Clerk of the Board (host… | 2 | `agenda_maricopa_county_az_supervisors_agenda` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U349 | I5-C203 | Board of Supervisors Meeting Agendas / Orange County Bo… | County of Orange, Clerk of the Board | 2 | `agenda_orange_county_ca_supervisors_meeting` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F042 |
| I7-U350 | I5-C204 | Miami-Dade County Legislative Hub (govaction) — BCC age… | Miami-Dade County Clerk / Board of Count… | 2 | `agenda_miami_dade_county_fl_legislative_hub` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F038 |
| I7-U351 | I5-C205 | Dallas County Commissioners Court — Court Agenda / Agen… | Dallas County Commissioners Court | 2 | `agenda_dallas_county_tx_commissioners_court` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U352 | I5-C207 | Agenda Center — Bexar County, TX (CivicEngage) | Bexar County, Texas (via CivicPlus Civic… | 2 | `agenda_bexar_county_tx_agenda_center` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U399 | SRC-008 | Safe Oklahoma Grant program awards and reports discover… | Oklahoma Attorney General's office (Safe… | 2 | `grant_ok_safe_oklahoma_grant` | LicenseRef-PublicRecord-FactualCompila… | none captured |

### RB-05 US federal works

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U054 | I4-C167 | DHS Privacy Impact Assessments hub - operational social… | U.S. Department of Homeland Security, Pr… | 1 | `statrep_us_dhs_privacy_impact` | CC0-1.0 | none captured |
| I7-U055 | I4-C259 | DHS component privacy compliance document indexes (Priv… | U.S. Department of Homeland Security, Pr… | 1 | `statrep_us_dhs_component_privacy` | CC0-1.0 | none captured |
| I7-U073 | I4-C261 | DHS/OBIM/PIA-004 Homeland Advanced Recognition Technolo… | U.S. Department of Homeland Security, Of… | 1 | `statrep_us_dhs_obim_pia` | CC0-1.0 | none captured |
| I7-U074 | I4-C269 | DHS/CBP Border Surveillance Systems (BSS) - compliance … | U.S. Department of Homeland Security / U… | 1 | `statrep_us_dhs_cbp_border` | CC0-1.0 | none captured |
| I7-U079 | I3-C072 | DHS System of Records Notices referencing license plate… | U.S. Department of Homeland Security (IC… | 1 | `legis_us_dhs_system_records` | CC0-1.0 | none captured |
| I7-U100 | I4-C260 | DHS/CBP/PIA-080 CBP Commercial Telemetry Data Evaluatio… | U.S. Department of Homeland Security / U… | 1 | `statrep_us_dhs_cbp_pia` | CC0-1.0 | none captured |
| I7-U156 | I4-C085 | Wiretap Report (annual, 18 U.S.C. §2519) - summary tabl… | Administrative Office of the U.S. Courts | 2 | `statrep_us_wiretap_summary_tables` | CC0-1.0 | none captured |
| I7-U160 | I6-C024 | Federal Register API (documents search: notices, rules,… | Office of the Federal Register (NARA) / … | 2 | `legis_us_federal_register_api` | CC0-1.0 | none captured |
| I7-U165 | I6-C036 | 2024 Federal Agency AI Use Case Inventory (consolidated… | Office of Management and Budget (via Git… | 2 | `statrep_us_2024_federal_agency` | CC0-1.0 | none captured |
| I7-U170 | I4-C280 | ICE 287(g) Participating Agencies (XLSX) | U.S. Immigration and Customs Enforcement… | 2 | `statrep_us_ice_287_participating` | CC0-1.0 | I7 capture (first attempt) |
| I7-U188 | I4-C211 | NCES School Survey on Crime and Safety (SSOCS) public-u… | National Center for Education Statistics… | 2 | `opendata_us_nces_school_survey` | CC0-1.0 | row-captured |
| I7-U224 | I4-C115 | DHS AI Use Case Inventory (2025) | U.S. Department of Homeland Security (Of… | 2 | `statrep_us_dhs_ai_use` | CC0-1.0 | none captured |
| I7-U241 | I4-C027 | FAA restricted-area rulemakings for CBP tethered aerost… | Federal Aviation Administration (via Fed… | 2 | `legis_south_padre_island_tx_faa_restricted_a` | CC0-1.0 | none captured |
| I7-U244 | I4-C276 | Body Worn Camera Resources (OJP/BJA BWC Toolkit resourc… | U.S. DOJ Office of Justice Programs (Soc… | 2 | `camreg_us_body_worn_camera` | CC0-1.0 | none captured |
| I7-U272 | I9a-C044 | US House Community Project Funding (CPF) request disclo… | US House of Representatives Member offic… | 2 | `grant_us_house_community_project` | CC0-1.0 | none captured |
| I7-U391 | SRC-022 | DOJ COPS technology/equipment award documents | U.S. DOJ Office of Community Oriented Po… | 2 | `grant_us_doj_cops_technology` | CC0-1.0 | I7 capture I7-F033 |
| I7-U398 | I9b-C111 | CBP national media release: 'CBP Completes Simplified A… | US Customs and Border Protection | 2 | `policy_us_cbp_national_media` | CC0-1.0 | I7 capture I7-F070 |

### RB-06 explicit open licence / PD dedication

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U001 | I3-C077 | Cook County Procurement - Awarded Contracts & Amendment… | Cook County, IL Office of the Chief Proc… | 1 | `procportal_cook_county_il_procurement_awarde` | CC0-1.0 | I7 capture (first attempt) |
| I7-U006 | I4-C052 | Automated Safety Cameras (ASC) Violation Count By Month | District of Columbia, District Departmen… | 1 | `camreg_dc_automated_safety_cameras_2` | CC-BY-4.0 | row-captured |
| I7-U009 | I4-C055 | Automated Speed Enforcement Violations | Montgomery County, MD, Department of Pol… | 1 | `camreg_montgomery_county_md_automated_speed` | CC0-1.0 | row-captured |
| I7-U010 | I4-C056 | Automated Red Light Violations | Montgomery County, MD, Department of Pol… | 1 | `camreg_montgomery_county_md_automated_red_li` | CC0-1.0 | row-captured |
| I7-U025 | I4-C051 | Automated Safety Cameras (ASC) | District of Columbia, District Departmen… | 1 | `camreg_dc_automated_safety_cameras` | CC-BY-4.0 | row-captured |
| I7-U048 | I9b-C083 | TPVA Red Light Camera Locations 2015 (Suffolk County, N… | Suffolk County, NY (SCOpenData via ArcGI… | 1 | `camreg_suffolk_county_ny_tpva_red_light` | CC-BY-4.0 | row-captured |
| I7-U051 | I4-C067 | 2026 Automated Safety Enforcement Report (Report to the… | Washington Traffic Safety Commission (wi… | 1 | `statrep_wa_2026_automated_safety` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F073 |
| I7-U052 | I4-C068 | WA city/county annual automated traffic safety camera r… | 29 WA cities operating programs (per WTS… | 1 | `statrep_wa_automated_traffic_safety` | LicenseRef-PublicRecord-FactualCompila… | I7 capture I7-F073 |
| I7-U098 | I9b-C093 | Governor of Guam press release: 'Bill for GPD Security … | Office of the Governor of Guam | 1 | `legis_gu_governor_guam_press` | CC0-1.0 | I7 capture I7-F032 |
| I7-U166 | I9b-C102 | Home Office - 'Live facial recognition in Immigration E… | UK Home Office (Immigration Enforcement)… | 2 | `statrep_gb_home_live_facial` | OGL-3.0 | I7 capture I7-F024 |
| I7-U248 | I5-C335 | Contracts Finder OCDS Search API | Crown Commercial Service / Cabinet Offic… | 2 | `procportal_gb_eng_contracts_finder_ocds` | OGL-3.0 | row-captured |
| I7-U249 | I5-C336 | AusTender OCDS API (findByDates) | Department of Finance (AusTender) | 2 | `procportal_au_austender_ocds_api` | CC-BY-4.0 | row-captured |
| I7-U258 | I5-C016 | Snow Plow Camera Images - Nebraska DOT | Nebraska Department of Transportation da… | 2 | `dot_511_ne` | CC-BY-4.0 | row-captured |
| I7-U264 | I5-C313 | CCTV cameras | North Somerset Council | 2 | `camreg_gb_eng_north_cctv_cameras` | OGL-3.0 | row-captured |
| I7-U265 | I5-C325 | CCTV Camera Register | Townsville City Council | 2 | `camreg_au_qld_towns_cctv_camera_register` | CC-BY-4.0 | row-captured |
| I7-U267 | I5-C330 | Security Cameras | City of Perth | 2 | `camreg_au_wa_perth_security_cameras` | CC-BY-4.0 | row-captured |
| I7-U268 | I5-C345 | UK Parliament Written Questions and Answers API | UK Parliament (House of Commons / House … | 2 | `legis_gb_uk_parliament_written` | LicenseRef-Open-Parliament-Licence | I7 capture (first attempt) |
| I7-U269 | I5-C348 | data.europa.eu search API — multilingual CCTV/video-sur… | Publications Office of the EU (data.euro… | 2 | `opendata_eu_eea_europa_search_api` | LicenseRef-per-dataset | row-captured |
| I7-U278 | I9b-C110 | Staatscourant - 'Cameraplan ANPR Politie' under article… | Nationale Politie (Netherlands), publish… | 2 | `statrep_nl_staatscourant_cameraplan_anpr` | CC0-1.0 | I7 capture I7-F078 |
| I7-U297 | I5-C305 | Privacy Commissioner publishes updated guidance on faci… | Office of the Australian Information Com… | 2 | `statrep_au_privacy_commissioner_publishes` | CC-BY-4.0 | row-captured |
| I7-U298 | I5-C307 | Enforcement action (ICO register of enforcement notices… | Information Commissioner's Office (UK) | 2 | `statrep_gb_enforcement_action` | OGL-3.0 | row-captured |
| I7-U302 | I5-C363 | Algoritmeregister van de Nederlandse overheid | Rijksoverheid (Ministry of the Interior,… | 2 | `statrep_nl_algoritmeregister_van_de` | CC0-1.0 | I7 capture I7-F036 |
| I7-U305 | I9b-C100 | CanadaBuys tender and award notices (federal procuremen… | Public Services and Procurement Canada (… | 2 | `procportal_ca_canadabuys_tender_award` | OGL-Canada-2.0 | I7 capture I7-F026 |
| I7-U306 | I9b-C103 | CNIL - 'Utilisation de BriefCam et d'autres logiciels d… | Commission nationale de l'informatique e… | 2 | `statrep_fr_cnil_utilisation_de` | CC-BY-ND-4.0 | I7 capture I7-F027 |
| I7-U319 | I5-C310 | data.gov.uk CKAN package_search — CCTV (56 datasets) | data.gov.uk (UK Government; per-dataset … | 2 | `dot_511_gb` | OGL-3.0 | row-captured |
| I7-U321 | I5-C314 | CCTV Cameras | Mansfield District Council | 2 | `camreg_gb_eng_mansf_cctv_cameras` | CC-BY-4.0 | row-captured |
| I7-U322 | I5-C316 | Trafford Council - CCTV | Trafford Council | 2 | `camreg_gb_eng_traff_trafford_cctv` | OGL-3.0 | row-captured |
| I7-U327 | I5-C324 | data.gov.au CKAN package_search — CCTV (164 hits) | data.gov.au (Australian Government; per-… | 2 | `camreg_au_ckan_package_search` | CC-BY-4.0 | row-captured |
| I7-U328 | I5-C326 | Ballarat CCTV Cameras | City of Ballarat | 2 | `camreg_au_vic_balla_ballarat_cctv_cameras` | CC-BY-4.0 | row-captured |
| I7-U332 | I5-C333 | Traffic Poles with CCTV DCC | Dublin City Council (via data.gov.ie / S… | 2 | `camreg_ie_d_dublin_traffic_poles_with` | CC-BY-4.0 | row-captured |
| I7-U334 | I5-C349 | Cámaras de videovigilancia en la vía pública de Madrid | Ayuntamiento de Madrid (Policía Municipa… | 2 | `opendata_es_md_madrid_maras_de_videovigilanc` | CC-BY-4.0 | row-captured |
| I7-U335 | I5-C353 | Videosorveglianza urbana | Comune di Messina | 2 | `opendata_it_me_messin_videosorveglianza_urba` | CC-BY-4.0 | row-captured |
| I7-U336 | I5-C355 | Vidéoprotection | Grand Paris Seine Ouest (établissement p… | 2 | `opendata_fr_92_grand_vid_oprotection` | LicenceOuverte-2.0 | row-captured |
| I7-U337 | I5-C356 | Sistema de Videovigilância Bairro Alto | Município de Lisboa | 2 | `opendata_pt_11_lisboa_sistema_de_videovigil` | CC0-1.0 | row-captured |
| I7-U357 | I5-C360 | Videonadzor na javnih površinah na območju Občine Kočev… | Občina Kočevje (via podatki.gov.si) | 2 | `camreg_si_048_ko_ev_videonadzor_na_javnih` | CC-BY-4.0 | row-captured |
| I7-U367 | I3-C063 | KSUALPRS flock-sharing-data - normalized Flock network-… | KSUALPRS (civic project) via GitHub | 2 | `ngo_us_ksualprs_flock_sharing` | CC0-1.0 | row-captured |
| I7-U372 | I5-C312 | CCTV Cameras | Runnymede Borough Council | 2 | `camreg_gb_eng_runny_cctv_cameras` | OGL-3.0 | row-captured |
| I7-U373 | I5-C315 | SKDC CCTV | South Kesteven District Council | 2 | `camreg_gb_eng_south_skdc_cctv` | OGL-3.0 | row-captured |
| I7-U375 | I5-C322 | CCTV Camera Locations in Ipswich | Ipswich Borough Council | 2 | `camreg_gb_eng_ipswi_cctv_camera_locations` | CC-BY-4.0 | row-captured |
| I7-U377 | I5-C344 | CCTV Annual Report June 2026 (Sevenoaks District Counci… | Sevenoaks District Council | 2 | `statrep_gb_eng_seven_cctv_june_2026` | OGL-3.0 | none captured |
| I7-U378 | I5-C350 | Videoüberwachung im öffentlichen Raum | Kantonspolizei Bern (via Amt für Geoinfo… | 2 | `opendata_ch_be_video_berwachung_im` | LicenseRef-opendata.swiss-terms_open | row-captured |
| I7-U379 | I5-C352 | Sites sous vidéosurveillance | République et Canton du Jura (Service du… | 2 | `opendata_ch_ju_sites_sous_vid` | LicenseRef-opendata.swiss-terms_by | row-captured |
| I7-U401 | I4-C119 | Who Has Your Face? - resources and agency-sharing CSV (… | Electronic Frontier Foundation | 2 | `ngo_us_who_has_your` | CC-BY-4.0 | row-captured |
| I7-U408 | SRC-026 | UK Algorithmic Transparency Recording Standard public-s… | UK Government (GOV.UK — Algorithmic Tran… | 2 | `statrep_gb_uk_algorithmic_transparency` | OGL-3.0 | I7 capture I7-F024 |
| I7-U429 | I5-C351 | Videoüberwachungsgeräte | Stadt Bern (Direktion für Sicherheit, Um… | 2 | `opendata_ch_be_bern_video_berwachungsger_te` | LicenseRef-opendata.swiss-terms_open | row-captured |
| I7-U431 | I5-C358 | Webkamera | Statens vegvesen (Norwegian Public Roads… | 2 | `opendata_no_webkamera` | NLOD-2.0 | row-captured |

### RB-07 journalism/NGO/academic/©-only facts + citations

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U071 | I4-C109 | Policy 610 Cellular Site Simulator Usage and Privacy - … | Orange County Sheriff-Coroner Department… | 1 | `statrep_orange_county_ca_policy_610_cellular` | LicenseRef-DerivedFacts-Citations | row-captured |
| I7-U072 | I4-C110 | Pasadena Police Department Policy 620 Cellular Site Sim… | City of Pasadena, CA (City Council agend… | 1 | `agenda_pasadena_ca_policy_620_cellular` | LicenseRef-DerivedFacts-Citations | row-captured |
| I7-U212 | I9b-C005 | WSIPC RFP 24-01 Student Safety Solutions - Gaggle coope… | WSIPC (Washington School Information Pro… | 2 | `procportal_wa_wsipc_rfp_24` | LicenseRef-DerivedFacts-Citations | I7 capture I7-F030 |
| I7-U230 | I6-C004 | NASPO ValuePoint portfolio: Public Safety/Law Enforceme… | NASPO ValuePoint (lead state: Oklahoma) | 2 | `procportal_us_naspo_valuepoint_portfolio` | LicenseRef-DerivedFacts-Citations | row-captured |
| I7-U286 | I4-C263 | Apple Transparency Report - Report CSVs (government and… | Apple Inc. | 2 | `vendor_us_apple_transparency_csvs` | LicenseRef-DerivedFacts-Citations | row-captured |
| I7-U371 | I5-C113 | Anaheim PD Policy Manual (Lexipol) | Anaheim Police Department (Lexipol-licen… | 2 | `policy_anaheim_ca_pd_policy_manual` | LicenseRef-DerivedFacts-Citations | row-captured |
| I7-U397 | I9b-C092 | Tulsa police won't share the locations of more than 200… | The Frontier (nonprofit investigative jo… | 2 | `news_tulsa_ok_won_share_locations` | LicenseRef-DerivedFacts-Citations | I7 capture I7-F029 |
| I7-U403 | I6-C033 | IIHS: U.S. red light camera communities (and sibling sp… | Insurance Institute for Highway Safety | 2 | `ngo_us_iihs_red_light` | LicenseRef-DerivedFacts-Citations | row-captured |
| I7-U409 | I4-C081 | FY21 - SPI ShotSpotter Expansion Evaluation - Final Rep… | Southern Illinois University Edwardsvill… | 2 | `academic_st_louis_mo_fy21_spi_shotspotter` | LicenseRef-DerivedFacts-Citations | none captured |
| I7-U413 | I9a-C046 | University of Washington Center for Human Rights - 'Lea… | University of Washington Center for Huma… | 2 | `academic_wa_university_washington_center` | LicenseRef-DerivedFacts-Citations | I7 capture I7-F046 |
| I7-U420 | I5-C365 | O Panóptico — Monitor do reconhecimento facial no Brasi… | Centro de Estudos de Segurança e Cidadan… | 2 | `ngo_br_pan_ptico_monitor` | LicenseRef-DerivedFacts-Citations | none captured |
| I7-U421 | I5-C366 | Panoptic Tracker — Facial Recognition Systems in India | Internet Freedom Foundation (Project Pan… | 2 | `ngo_in_panoptic_tracker_facial` | LicenseRef-DerivedFacts-Citations | none captured |
| I7-U422 | I9b-C075 | Immigration Policy Tracking Project - policy entries wi… | Immigration Policy Tracking Project (aca… | 2 | `ngo_us_immigration_policy_tracking` | LicenseRef-DerivedFacts-Citations | none captured |
| I7-U432 | I3-C066 | Texas Surveillance Contract Watch (tx-surveillance-watc… | StickyHashTr33 (civic project) via GitHu… | 2 | `ngo_tx_texas_surveillance_contract` | LicenseRef-DerivedFacts-Citations | none captured |
| I7-U434 | I4-C310 | Electronic Monitoring Fees: A 50-State Survey of the Co… | Fines and Fees Justice Center | 2 | `ngo_us_electronic_monitoring_fees` | LicenseRef-DerivedFacts-Citations | none captured |

### RB-08 territorial public records

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U246 | I5-C227 | Sistema Único de Trámite Legislativo (SUTRA) | Asamblea Legislativa de Puerto Rico — Of… | 2 | `legis_pr_sistema_nico_de` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U277 | I9b-C094 | Legislature of the U.S. Virgin Islands press release: '… | Legislature of the Virgin Islands (34th … | 2 | `legis_vi_legislature_virgin_islands` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U291 | I5-C228 | RC0787 — Resolución de la Cámara: investigación sobre c… | Asamblea Legislativa de Puerto Rico (via… | 2 | `legis_pr_rc0787_resoluci_de` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U292 | I5-C229 | RS0604 — Resolución del Senado: investigación sobre cám… | Asamblea Legislativa de Puerto Rico (via… | 2 | `legis_pr_rs0604_resoluci_del` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U293 | I5-C230 | RC0740 — investigación sobre cámaras de vigilancia o mo… | Asamblea Legislativa de Puerto Rico (via… | 2 | `legis_pr_rc0740_investigaci_sobre` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U294 | I5-C231 | RCS0198 — Resolución Conjunta del Senado: requisito de … | Asamblea Legislativa de Puerto Rico (via… | 2 | `legis_pr_rcs0198_resoluci_conjunta` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U295 | I5-C232 | PC0560 — Plan de Vigilancia de las Costas, Puertos y Ae… | Asamblea Legislativa de Puerto Rico (via… | 2 | `legis_pr_pc0560_plan_de` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U296 | I5-C233 | PC0489 — Ley del Programa de Vigilancia, Prevención y P… | Asamblea Legislativa de Puerto Rico (via… | 2 | `legis_pr_pc0489_ley_del` | LicenseRef-PublicRecord-FactualCompila… | none captured |

### RB-09 existing gated registry rows (flip)

| I7 id | cand | candidate | publisher | tier | proposed source_id | licence (proposed) | terms evidence |
|---|---|---|---|---|---|---|---|
| I7-U370 | I4-C270 | DHS Fusion Center Locations and Contact Information | U.S. Department of Homeland Security, Of… | 2 | `dhs_fusion_centers` | CC0-1.0 | none captured |
| I7-U424 | SRC-020 | Boston annual surveillance report and supplements | City of Boston | 2 | `ccops_boston` | LicenseRef-PublicRecord-FactualCompila… | none captured |
| I7-U427 | I4-C123 | Stingray Tracking Devices: Who's Got Them? (ACLU map) | American Civil Liberties Union | 2 | `aclu_cell_site_simulators` | LicenseRef-DerivedFacts-Citations | none captured |
| I7-U435 | SRC-019 | Berkeley surveillance annual reports policies MOUs | City of Berkeley | 2 | `ccops_berkeley` | LicenseRef-PublicRecord-FactualCompila… | none captured |

### Part-VIII-flagged members by underlying batch (decide with the S-lines in §1.2)

| underlying batch | members |
|---|---|
| RB-01 | I4-C065, I5-C101, I3-C004, I3-C005, I3-C008, I3-C009, I3-C011, I4-C156, I3-C006, I5-C102, I5-C104, I3-C027, I4-C165, I3-C001, I3-C080, I3-C083, I4-C016, I4-C017, I4-C018, I4-C019, I5-C220, I3-C022, I4-C084, I5-C219, I9b-C047 |
| RB-02 | I5-C014 |
| RB-03 | I6-C014, I6-C015, I3-C040, I4-C009, I4-C273, I9b-C063, I4-C087, I9b-C050, I9b-C051, I9b-C052, I4-C308, I5-C100, I6-C039, I4-C012, I5-C028, I5-C033, I9a-C001, I4-C158, I9a-C021, I9a-C004, I9a-C005, I9a-C006, I9a-C007, I9a-C008, I9a-C009, I3-C089 |
| RB-04 | I6-C007, I3-C078, I9b-C090, I9b-C013, I9b-C015, I9b-C081, I9b-C035, I9b-C021, I9b-C027, I9b-C029, I4-C079, I9a-C035, I9a-C038, I9b-C025, I4-C155, I4-C161, I9b-C024, I9b-C026, I4-C157, I4-C160, I9b-C044, I9b-C045, I4-C077, I4-C088 |
| RB-05 | I4-C086, I6-C025, I5-C237, I4-C281, I9b-C073, SRC-024 |
| RB-06 | I6-C008, I4-C057, I6-C009, I4-C050, I5-C338, I6-C038, I4-C307, I5-C334, I5-C332, I4-C209 |
| RB-06b | I4-C164, I5-C103, I5-C364, I5-C105 |
| RB-07 | I4-C168, I3-C070, I4-C163, I9b-C064, I5-C224, I4-C166 |
| RB-08 | I5-C226 |
| RB-09 | I4-C001 |

### E4 cross-references (not re-packeted)

| I7 id | cand | candidate | E4 line | I7 new fact |
|---|---|---|---|---|
| I7-U185 | I4-C066 | Edmonton photo-enforcement datasets (ISD locations, pho… | E4 (R4a camreg_edmonton_ab; new fact: ToU titled OGL-Edmonton) | I7-F011: Edmonton ToU page is titled "Open Government Licence - Edmonton" — new fact for E4 R4a / I7 registry re-check: 7fnd-72gr = camreg_edmonton_ab… |
| I7-U199 | SRC-002 | Tulsa Flock policies integration and executed contract … | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered |
| I7-U200 | SRC-003 | San Diego technology inventory and annual reports | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered |
| I7-U201 | SRC-004 | San Diego Sunshine Act goods/services contracts | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered |
| I7-U220 | SRC-007 | Oklahoma DAC UVED program and authority chain | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered |
| I7-U227 | I5-C132 | BidNet Direct storefront - City of Hialeah | E4 (R6a bidnet_direct / S2 bonfire: vendor procurement platforms; terms capture owed) | terms checked, none found by I7 (I7-F028) |
| I7-U228 | I5-C133 | BidNet Direct storefront - City of Winston-Salem and Fo… | E4 (R6a bidnet_direct / S2 bonfire: vendor procurement platforms; terms capture owed) | terms checked, none found by I7 (I7-F028) |
| I7-U229 | I5-C134 | BidNet Direct storefront - City of Jersey City | E4 (R6a bidnet_direct / S2 bonfire: vendor procurement platforms; terms capture owed) | terms checked, none found by I7 (I7-F028) |
| I7-U235 | SRC-001 | OKC Flock council amendment policy packet | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered / terms checked, none found by I7 (I7-F043) |
| I7-U236 | SRC-006 | Oklahoma OMES statewide contracts and solicitations | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered |
| I7-U237 | SRC-011 | California State Auditor ALPR audit survey and follow-u… | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered |
| I7-U245 | I4-C315 | City of West Palm Beach RFP 25.26.200 SS — Speed Detect… | E4 (R6a bidnet_direct / S2 bonfire: vendor procurement platforms; terms capture owed) |  |
| I7-U354 | I5-C223 | Maricopa County Procurement Services — BidNet Direct st… | E4 (R6a bidnet_direct / S2 bonfire: vendor procurement platforms; terms capture owed) | terms checked, none found by I7 (I7-F028) |
| I7-U365 | SRC-005 | San Diego Privacy Advisory Board recommendations | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) | E4-covered |
| I7-U394 | I5-C222 | Harris County Purchasing Department — Bonfire portal | E4 (R6a bidnet_direct / S2 bonfire: vendor procurement platforms; terms capture owed) |  |
| I7-U694 | SRC-027 | San Diego ALPR network audit metadata and safe aggregat… | E4 (already packeted: D-R10-SOURCES-1 B1/B2/B3/B6) |  |
