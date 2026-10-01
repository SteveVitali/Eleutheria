# I1 — Current source-coverage map

Row **I1** of `META_PLAN.md` §6 (Stream I, Stage P). Read-only. Captures ran 2026-09-30T16:43:45Z → 17:08Z
(`date -u`). Author: Claude Code (Opus 5.5) in the planning worktree `claude/next-phase-planning`. Outputs:
this note, `data/source_coverage.csv` (369 rows: 342 registry + 27 acquisition-queue candidates) and
`findings/incoming/I1.csv` (NEW-1…NEW-9). Raw captures and the three scratch scripts live under
`docs/build/logs/next-phase/I1/` (gitignored). Evidence classes follow P1: `code` · `recorded-execution` ·
`live-read` · `operator-statement` · `inference`. Every coverage cell below says which one it rests on.

## Summary

- **Registry:** 342 sources; 236 `ingestion_permitted=true`. Status against hosted evidence: **218 ingested-live**
  (178 camera-registry/DOT site sources + 40 others), **19 permitted-not-ingested**, **101 gated**, **4 refused**,
  plus **27 candidates** in `acquisition_queue.toml`.
- **Hosted data is dominated by one data shape.** 178 of the 218 live sources are camera-registry layers
  (236,994 published site rows; 154,528 of them are one OSM-derived ALPR layer). All other technology classes
  reach the product through a handful of national sources, above all the EFF Atlas (one NGO dataset, loaded once
  on 2026-09-15).
- **What the public can see per place is narrower than what is ingested.** Jurisdiction pages come only from
  geolocated registry sources. 22 states, including Oklahoma (the pilot), have no dossier. The Atlas, Eyes on
  Flock, OpenStates, CCOPS, agenda and procurement claims never reach a jurisdiction page (NEW-4). Some pages
  that do exist are wrong: the jurisdiction codes collide (NEW-1) and some coordinates or labels are wrong (NEW-2).
- **Vendor channels:** Flock comes only through one community mirror (1,528 portals against the mirror's own
  estimate of 6,634 networks). No Axon/Fusus, Motorola/Vigilant, SoundThinking, Genetec, Rekor, drone-vendor or
  Clearview channel is ingested. The vendor field in the Atlas is not turned into claims (NEW-6, NEW-7).
- **Zero-channel classes:** social-media monitoring, mobile forensics and US school surveillance (NEW-8).

## 1. Method

**Inputs read (all at planning HEAD, byte-identical to chain tip `b051732c` for these paths):**
`connectors/src/connectors/data/sources.toml` (7,534 lines, 342 `[sources.*]` rows, parsed with `tomllib`),
`live_targets.toml` (235 source keys), `camera_registry_targets.toml` (223 targets), `dot_511_targets.toml` (14),
`live_dispositions.toml` (104 rows), `runner.CONNECTOR_FOR_SOURCE` (238 rows; 238 + 104 = 342, completeness
holds), `ops/cadence.toml` (70 source jobs + 8 batches covering 151 camreg sources),
`tasks/src/tasks/data/acquisition_queue.toml` (27 candidates, `acq-seed/1`), `agenda_tenants.toml` (793 tenants),
`state_alpr_statute_seed.toml` (16 states), `ontology/vocab/technology.yaml` (14 domains / 36 families / 104
technologies), `docs/build/reports/SOURCE_LIVE_OPS_MATRIX.md` (a 121-source snapshot from 2026-09-16; historical
only), `docs/build/reports/live_runs/*.json` (90 records), the catalog-sweep reports, and six-streams
`research/S5-source-strategy.md`.

**Hosted evidence (read-only):**
- The public export `manifest.json`: sha256 `717aeb44…72d6`, release `sig-2026-09-27-ce480ab1`, the same as the A1
  baseline. I also read its `sig_graph/{freshness,coverage,jurisdictions,sites,sharing_edges}.csv`, the
  `web/{freshness,coverage,dossier_index,dossiers,evidence,network}.json` files, and every compartment's
  `sites.csv` (11 compartments, 236,994 rows).
- 387 GCS run rows under `gs://zeta-medley-508121-u7-sig-restricted/ops/runs/`, from 208 source prefixes. I read
  them with `gcloud storage ls` and `cat` only.
- `gcloud scheduler jobs list`: 79 jobs.
- Live pages: `/data-freshness/`, `/dossier/`, `/dossier/{de,id,mn}/`, `/coverage-metrics/`, `/network/`.
- API `/v1/coverage/{okc,national,us}`, `/v1/search` and `/v1/entity`.

Every request was a polite single GET.

**Upstream re-reads (one GET each, public):**
- The EFF Atlas `download.csv`: 15,135 rows, sha256 `dcbf8bc1…`.
- Eyes on Flock `GET /api/v1/data`: 1,528 portals, sha256 `eccb336a…`. It holds audit search-reason fields
  (Part VIII). They were not copied into any artifact.
- Census Vintage 2024 `sub-est2024.csv`, used for the city ranking.
- Census `cb_2023_us_state_20m.kml`, for state polygons.
- The 2024 Gazetteer place and county files.

**Status rules.**
- `ingested-live` means hosted claims exist, shown by at least one of these: a GCS run row with
  `claims_added > 0`; rows in a public export; or a committed run ledger / live-run record of a hosted commit,
  corroborated by a public `evidence.json` artifact where one exists.
- `permitted-not-ingested` means `ingestion_permitted=true` and none of the above. Reference rows and runs that
  recorded 0 claims both fall here.
- `gated` means `ingestion_permitted` is false or absent.
- `refused` means the registry itself records a decision not to ingest: no lawful access, a leak-provenance veto,
  a do-not-ingest rule, or a wrong project.
- `candidate` means a row in `acquisition_queue.toml`.

**Classification.** Each row gets one or more of 22 plain classes; the mapping to the ontology is in §2. The
publisher type uses the §8.6 vocabulary. Geography is written unambiguously: `US-XX`, `US-XX:City`, `ISO:CC` for
country-level registry codes, ISO 3166-2 subdivisions, `INTL` or `EU/EEA`. Camera-registry rows are classified
by rule from their name and target agency. The other 164 rows are classified by hand, row by row. Where a
source's hosted points fall outside its declared state or country, the geography column also carries
`(pts:…)` from my own point-in-polygon test. That test is inference.

**Denominators.**
- All 50 states + DC.
- The 100 most populous US incorporated places: U.S. Census Bureau, *Vintage 2024 Population Estimates*,
  `SUB-EST2024` (SUMLEV 162, `POPESTIMATE2024`), from
  <https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/cities/totals/sub-est2024.csv>, retrieved
  2026-09-30T16:52:13Z.
- Counties were not tabulated. The circle approximation used for cities is too coarse for counties; this is left
  to I5.

**How local coverage was computed.** "≥1 ingested source with local claims" is the union of four things:
- **T1**, the published jurisdiction index (live-read);
- **T2**, hosted site coordinates placed in states by point-in-polygon, and in cities within a circle of the
  place's Gazetteer land area around its internal point (inference over live-read coordinates);
- **T3**, hosted non-site sources, attributed to places from their upstream bytes: Atlas City/State, Eyes on
  Flock city/state, OpenStates jurisdictions with matched bills in GCS run rows, the NCSL statute seed, agenda
  tenants actually fetched (Legistar verified tenants; PrimeGov hosts in the 2026-09-19 run record;
  CivicClerk/eScribe tenants with matched documents in run rows), and the city-scoped CCOPS, procurement-portal
  and OKC sources (inference: upstream re-read used as a proxy for claims whose hosted load is recorded);
- nothing else. National-only sources (USAspending, SAM, Congress, GAO, DHS, FEMA) do not count as local.

The OSM-derived layer is counted as ALPR. About 151,700 of its 154,528 points come from ALPR republishes; the
published export has no technology field (NEW-9).

## 2. Counts

### 2.1 By status

| status | registry rows | queue rows | total |
|---|---|---|---|
| ingested-live | 218 | 0 | 218 |
| permitted-not-ingested | 19 | 0 | 19 |
| gated | 101 | 0 | 101 |
| refused | 4 | 0 | 4 |
| candidate | 0 | 27 | 27 |
| **total** | 342 | 27 | 369 |

Among the 218 ingested-live sources:
- **Licences:** 94 `LicenseRef-OperatorAccepted-DBRight`, 60 `LicenseRef-PublicRecord-FactualCompilation`,
  28 CC0-1.0, 8 CC-BY-4.0, 8 `LicenseRef-DerivedFacts-Citations`, 6 OGL-3.0, 5 ODbL-1.0, and 9 others (code:
  `sources.toml` `[rights]`).
- **Publishers:** 57 have publisher type `other`. These are unidentified or community ArcGIS publishers (see E1
  NEW-13 on the licence basis applied to them).

### 2.2 By technology class × status (a source can carry several classes)

| code | class | ingested-live | permitted-not-ingested | gated | refused | candidate | total |
|---|---|---|---|---|---|---|---|
| ALPR | fixed ALPR | 24 | 7 | 39 | 2 | 8 | 80 |
| mALPR | mobile ALPR | 1 | 0 | 0 | 0 | 0 | 1 |
| SHARE | ALPR sharing network | 2 | 1 | 12 | 2 | 1 | 18 |
| RTCC | RTCC/camera integration | 3 | 0 | 1 | 0 | 0 | 4 |
| PREG | private camera registry | 2 | 0 | 2 | 0 | 0 | 4 |
| DOT | traffic/DOT cameras | 83 | 0 | 4 | 0 | 0 | 87 |
| CCTV | CCTV registries | 98 | 5 | 20 | 0 | 2 | 125 |
| UAS | drones/DFR | 7 | 1 | 8 | 0 | 2 | 18 |
| GSD | gunshot detection | 7 | 1 | 7 | 1 | 1 | 17 |
| FRT | face recognition | 10 | 3 | 11 | 0 | 1 | 25 |
| CSS | cell-site simulator | 1 | 1 | 1 | 0 | 0 | 3 |
| SMM | social-media monitoring | 0 | 0 | 0 | 0 | 0 | 0 |
| FOR | forensics | 0 | 1 | 0 | 0 | 0 | 1 |
| VA | video analytics | 1 | 0 | 4 | 0 | 1 | 6 |
| SCH | school surveillance | 2 | 0 | 0 | 0 | 0 | 2 |
| DB | data broker | 3 | 0 | 0 | 0 | 1 | 4 |
| BWC | body-worn/evidence platform | 1 | 0 | 0 | 0 | 0 | 1 |
| FUS | fusion center | 4 | 0 | 1 | 0 | 0 | 5 |
| PROC | procurement/contracts (multi-class) | 15 | 2 | 32 | 0 | 10 | 59 |
| LEG | legislation/policy | 17 | 2 | 25 | 0 | 12 | 56 |
| ACC | accountability/oversight | 11 | 1 | 15 | 0 | 12 | 39 |
| OTH | other | 4 | 8 | 10 | 0 | 1 | 23 |

**Ontology mapping** (`ontology/vocab/technology.yaml`; the vocabulary has no vendor terms):

| Plain class | Ontology term |
|---|---|
| fixed ALPR | `surveillance-vehicle/alpr/alpr-fixed` |
| mobile ALPR | `…/alpr-mobile` |
| ALPR sharing network | the `alpr` family plus the sharing predicates `configured_sharing_partner`, `national_lookup_enabled` |
| RTCC/camera integration | `integration-platform/rtcc`, `federation-hub` |
| private camera registry | `surveillance-video/private-camera-integration/private-camera-registry` |
| traffic/DOT cameras | `surveillance-video/fixed-camera` (`camera-fixed-cctv` or `camera-ptz`). The vocabulary has no automated-traffic-enforcement technology. |
| CCTV registries | `fixed-camera/camera-fixed-cctv` |
| drones/DFR | `robotics-aerial/uas` (`uas-general`, `drone-as-first-responder`) |
| gunshot detection | `acoustic/gunshot-detection` |
| face recognition | `biometric-id/face-recognition` |
| cell-site simulator | `comms-intercept/cell-site-simulator` |
| social-media monitoring | `analytics-inference/osint-monitoring/social-media-monitoring` |
| forensics | `device-forensics/mobile-forensics` |
| video analytics | `surveillance-video/video-analytics` |
| school surveillance | `facility-screening/school-surveillance` |
| data broker | `data-acquisition/*` and `integration-platform/investigative-platform` |
| body-worn/evidence platform | `body-worn-video/*` |
| fusion center | an organisation, not a technology in the vocabulary |
| procurement, legislation, accountability | channels, not technologies |
| other | `analytics-inference/predictive-policing` and substrates |

### 2.3 By publisher type × status

| publisher_type | ingested-live | permitted-not-ingested | gated | refused | candidate | total |
|---|---|---|---|---|---|---|
| gov-open-data | 107 | 0 | 12 | 0 | 4 | 123 |
| other | 57 | 1 | 4 | 0 | 1 | 63 |
| procurement | 8 | 1 | 17 | 0 | 5 | 31 |
| ngo | 5 | 1 | 23 | 0 | 0 | 29 |
| crowdsourced | 3 | 11 | 11 | 2 | 0 | 27 |
| academic | 17 | 1 | 2 | 0 | 0 | 20 |
| ccops-report | 5 | 1 | 8 | 0 | 6 | 20 |
| statutory-report | 4 | 1 | 3 | 0 | 6 | 14 |
| agenda | 4 | 1 | 7 | 0 | 1 | 13 |
| records-release | 2 | 1 | 7 | 0 | 1 | 11 |
| journalism | 0 | 0 | 4 | 1 | 0 | 5 |
| legislation | 5 | 0 | 0 | 0 | 0 | 5 |
| grant | 1 | 0 | 0 | 0 | 3 | 4 |
| vendor-portal | 0 | 0 | 2 | 1 | 0 | 3 |
| court | 0 | 0 | 1 | 0 | 0 | 1 |

### 2.4 By geography (registry + queue rows; coarse bucket of the geography column)

| bucket | ingested-live | permitted-not-ingested | gated | refused | candidate | total |
|---|---|---|---|---|---|---|
| US (national, state or local) | 159 | 8 | 85 | 4 | 26 | 282 |
| single non-US country / subdivision | 55 | 2 | 13 | 0 | 1 | 71 |
| multi-country / global | 3 | 9 | 3 | 0 | 0 | 15 |
| EU/EEA | 1 | 0 | 0 | 0 | 0 | 1 |

### 2.5 The 40 non-site ingested sources (hosted evidence)

The full list is in `data/source_coverage.csv`, `hosted_claims_evidence` column. The largest:
- **Legislation.** `openstates`: 13,690 claims added over 8 runs, with matched bills in 40 states + PR.
  `congress_gov`: 79,000 over 4 runs.
- **Agendas.** `primegov`: 231,885 in the largest run (110 hosts, robots disregarded under the ADR-083/088
  basis). `legistar`: 36,257 (about 302 tenant indexes). `escribe`: 16,204 (15 tenants). `civicclerk`: 5,311
  (27 tenants).
- **Procurement.** `ted_eu`: 69,546. `usaspending`: 38,837. Four city procurement portals: about 5,000 each.
- **Physical layer.** `eyes_on_flock`: 11,976 claims per weekly run. `eff_atlas_of_surveillance`: 15,187 claims,
  one load on 2026-09-15 (P25.3). Its monthly scheduler has never attempted a run; the first is due
  2026-10-02.
- **FBI CDE.** `fbi_cde_agency_registry`: 5,111 claims (2026-09-17; LEDGER.md:402). It has no public evidence
  artifact and its quarterly job has never run.
- **Thin documentary sources:** `ccops_seattle` (5 claims), `ccops_nyc_post` (94), `ccops_oakland` (46),
  `ccops_cambridge` (42), `ccops_somerville` (72), `okcpd_policy` (3), `ok_statute` (3), `pathways_*` (4 and 3),
  `gao/dhs_oig/dhs_fusion/uk_scc` (7–10 each), `muckrock` (6; WAF-403 since), `osm_element_history` (1).

`claims_added` counts what each run emitted. Re-runs are idempotent, so the Σ values in the CSV overstate the
number of unique claims (recorded-execution).

## 3. US state coverage (50 + DC)

Column key:
- **Pub. dossier obs (src):** the published jurisdiction-index count and the number of sources behind it
  (live-read). Marked cells are contaminated (NEW-1, NEW-2): **DE**¹ is 24 German cameras; **ID**¹ includes 268
  Indonesian sites; **MN**¹ includes a Mongolian registry; **GA**² includes 3 Mongolian points; **CA**²
  includes 828 Florida cameras; **IL**³ and **FL**³ exclude 2,936 and 1,964 sites that have no geometry (NEW-3).
- **Official site srcs DOT/CCTV/ALPR:** government or community camera-registry sources with hosted points inside
  the state (T2; OSM excluded).
- **OSM-DeFlock pts:** hosted `camreg_osm_surveillance` points inside the state.
- **Atlas rows / classes:** from the 2026-09-30 upstream CSV. The hosted load of 2026-09-15 had 15,187 claims
  (T3).
- **Flock portals (cams):** Eyes on Flock portals and their stated camera totals (T3).
- **State leg. srcs:** OpenStates bills matched in run rows, and the NCSL seed.
- **Agenda tenants:** fetched agenda tenants (T3).
- **Classes covered:** codes as in §2.2.
- **Big-9:** ALPR, DOT, CCTV, UAS, GSD, FRT, BWC, RTCC, PREG.

| St | Pub. dossier obs (src) | Official site srcs DOT/CCTV/ALPR | OSM-DeFlock pts | Atlas rows | Atlas classes | Flock portals (cams) | State leg. srcs | Agenda tenants | Ingested srcs w/ local evidence | Classes covered (n) | Missing of big-9 | Flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AL | 556 (1) | 2/0/0 | 3,005 | 244 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 9 (135) | OpenStates | 6 | 8 | 16: ALPR SHARE RTCC PREG DOT UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | CCTV | — |
| AK | 0 (0) | 1/1/0 | 16 | 23 | UAS FRT CSS BWC FUS | 0 (0) | OpenStates | 6 | 6 | 10: ALPR DOT CCTV UAS FRT CSS BWC FUS PROC LEG | GSD RTCC PREG | no Flock portal (EoF); Atlas thin (23 rows) |
| AZ | 526 (1) | 3/0/2 | 2,685 | 194 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 24 (544) | OpenStates | 9 | 11 | 16: ALPR SHARE RTCC PREG DOT UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | CCTV | — |
| AR | 0 (0) | 0/0/0 | 1,043 | 100 | ALPR RTCC PREG UAS GSD FRT VA BWC FUS | 19 (607) | NCSL | 2 | 6 | 12: ALPR SHARE RTCC PREG UAS GSD FRT VA BWC FUS PROC LEG | DOT CCTV | no official site registry |
| CA | 6,139 (4)² | 4/3/2 | 22,785 | 1085 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 221 (12,854) | OpenStates+NCSL | 98 | 19 | 18: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG ACC OTH | — | — |
| CO | 14 (1) | 2/0/1 | 2,967 | 381 | ALPR RTCC PREG UAS GSD FRT VA DB BWC FUS OTH | 44 (685) | OpenStates+NCSL | 13 | 10 | 15: ALPR SHARE RTCC PREG DOT UAS GSD FRT VA DB BWC FUS PROC LEG OTH | CCTV | — |
| CT | 0 (0) | 1/0/0 | 1,006 | 175 | ALPR RTCC PREG UAS GSD VA DB BWC FUS | 26 (254) | OpenStates | 2 | 6 | 13: ALPR SHARE RTCC PREG DOT UAS GSD VA DB BWC FUS PROC LEG | CCTV FRT | — |
| DE | 24 (1)¹ | 0/0/0 | 407 | 33 | ALPR RTCC PREG UAS GSD FRT CSS BWC FUS | 4 (42) | — | 1 | 4 | 12: ALPR SHARE RTCC PREG UAS GSD FRT CSS BWC FUS PROC LEG | DOT CCTV | no official site registry; Atlas thin (33 rows) |
| DC | 1,591 (3) | 3/1/0 | 98 | 10 | ALPR PREG UAS GSD FRT CSS VA BWC FUS | 0 (0) | — | 0 | 6 | 11: ALPR PREG DOT CCTV UAS GSD FRT CSS VA BWC FUS | RTCC | no Flock portal (EoF); no legislation claims; Atlas thin (10 rows) |
| FL | 8,001 (4)³ | 7/1/1 | 10,007 | 944 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 26 (434) | NCSL | 32 | 16 | 17: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | — | — |
| GA | 7,049 (2)² | 1/1/0 | 10,263 | 532 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 51 (2,794) | NCSL | 7 | 8 | 17: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | — | — |
| HI | 252 (1) | 1/0/0 | 70 | 16 | ALPR RTCC PREG UAS FRT BWC FUS | 0 (0) | — | 1 | 4 | 10: ALPR RTCC PREG DOT UAS FRT BWC FUS PROC LEG | CCTV GSD | no Flock portal (EoF); Atlas thin (16 rows) |
| ID | 498 (2)¹ | 3/0/0 | 443 | 62 | ALPR PREG UAS GSD BWC FUS | 7 (210) | OpenStates | 0 | 7 | 9: ALPR SHARE PREG DOT UAS GSD BWC FUS LEG | CCTV FRT RTCC | — |
| IL | 573 (2)³ | 4/3/0 | 8,000 | 862 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 101 (1,794) | OpenStates | 10 | 12 | 17: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | — | — |
| IN | 0 (0) | 2/1/0 | 3,923 | 410 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 44 (641) | OpenStates | 2 | 9 | 17: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | — | — |
| IA | 1,858 (3) | 2/1/0 | 998 | 94 | ALPR PREG UAS FRT CSS DB BWC FUS | 36 (604) | OpenStates | 3 | 8 | 13: ALPR SHARE PREG DOT CCTV UAS FRT CSS DB BWC FUS PROC LEG | GSD RTCC | — |
| KS | 97 (2) | 4/0/0 | 2,325 | 134 | ALPR RTCC PREG UAS GSD FRT VA BWC FUS OTH | 24 (417) | OpenStates | 2 | 9 | 14: ALPR SHARE RTCC PREG DOT UAS GSD FRT VA BWC FUS PROC LEG OTH | CCTV | — |
| KY | 839 (3) | 3/0/0 | 2,090 | 137 | ALPR RTCC PREG UAS GSD FRT VA BWC FUS OTH | 18 (470) | — | 1 | 7 | 14: ALPR SHARE RTCC PREG DOT UAS GSD FRT VA BWC FUS PROC LEG OTH | CCTV | — |
| LA | 1,054 (6) | 6/1/0 | 2,195 | 188 | ALPR RTCC PREG UAS GSD FRT CSS DB BWC FUS OTH | 4 (74) | OpenStates | 4 | 13 | 16: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS DB BWC FUS PROC LEG OTH | — | — |
| ME | 0 (0) | 0/0/0 | 62 | 110 | ALPR UAS FRT DB BWC FUS OTH | 3 (4) | OpenStates+NCSL | 0 | 5 | 9: ALPR SHARE UAS FRT DB BWC FUS LEG OTH | DOT CCTV GSD RTCC PREG | no official site registry |
| MD | 2,752 (7) | 7/4/0 | 950 | 155 | ALPR RTCC PREG UAS GSD FRT CSS DB BWC FUS OTH | 8 (98) | OpenStates+NCSL | 5 | 17 | 16: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS DB BWC FUS PROC LEG OTH | — | — |
| MA | 845 (1) | 1/0/0 | 1,296 | 628 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 29 (240) | OpenStates | 8 | 10 | 18: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG ACC OTH | — | — |
| MI | 0 (0) | 0/0/0 | 4,286 | 715 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 35 (653) | OpenStates | 4 | 6 | 15: ALPR SHARE RTCC PREG UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | DOT CCTV | no official site registry |
| MN | 994 (3)¹ | 2/0/0 | 1,478 | 427 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 54 (516) | NCSL | 8 | 8 | 16: ALPR SHARE RTCC PREG DOT UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | CCTV | — |
| MS | 0 (0) | 0/0/0 | 1,026 | 142 | ALPR RTCC PREG UAS GSD FRT DB BWC FUS | 2 (83) | — | 0 | 3 | 10: ALPR SHARE RTCC PREG UAS GSD FRT DB BWC FUS | DOT CCTV | no official site registry; no legislation claims |
| MO | 1,107 (2) | 3/1/0 | 3,497 | 246 | ALPR RTCC PREG UAS GSD FRT CSS DB BWC FUS OTH | 45 (764) | OpenStates | 4 | 11 | 16: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS DB BWC FUS PROC LEG OTH | — | — |
| MT | 0 (0) | 1/0/0 | 61 | 31 | ALPR PREG UAS FRT BWC FUS | 0 (0) | OpenStates+NCSL | 0 | 5 | 8: ALPR PREG DOT UAS FRT BWC FUS LEG | CCTV GSD RTCC | no Flock portal (EoF); Atlas thin (31 rows) |
| NE | 0 (0) | 1/0/0 | 595 | 103 | ALPR RTCC UAS GSD FRT DB BWC FUS | 16 (201) | OpenStates+NCSL | 1 | 7 | 12: ALPR SHARE RTCC DOT UAS GSD FRT DB BWC FUS PROC LEG | CCTV PREG | — |
| NV | 0 (0) | 3/0/0 | 859 | 80 | ALPR RTCC PREG UAS GSD FRT CSS VA BWC FUS | 7 (367) | OpenStates | 2 | 9 | 14: ALPR SHARE RTCC PREG DOT UAS GSD FRT CSS VA BWC FUS PROC LEG | CCTV | — |
| NH | 0 (0) | 0/0/0 | 88 | 63 | ALPR RTCC PREG UAS DB BWC FUS | 0 (0) | OpenStates+NCSL | 0 | 4 | 8: ALPR RTCC PREG UAS DB BWC FUS LEG | DOT CCTV GSD FRT | no official site registry; no Flock portal (EoF) |
| NJ | 0 (0) | 1/1/0 | 1,827 | 1049 | ALPR RTCC PREG UAS GSD FRT VA DB BWC FUS OTH | 6 (87) | OpenStates | 3 | 8 | 16: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT VA DB BWC FUS PROC LEG OTH | — | — |
| NM | 0 (0) | 0/0/1 | 973 | 100 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS | 2 (53) | OpenStates | 3 | 6 | 14: ALPR SHARE RTCC PREG UAS GSD FRT CSS VA DB BWC FUS PROC LEG | DOT CCTV | — |
| NY | 585 (3) | 2/2/0 | 4,521 | 319 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 20 (339) | OpenStates | 5 | 12 | 18: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG ACC OTH | — | — |
| NC | 44 (2) | 2/0/0 | 3,726 | 303 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 76 (1,441) | OpenStates+NCSL | 10 | 8 | 16: ALPR SHARE RTCC PREG DOT UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | CCTV | — |
| ND | 0 (0) | 1/0/0 | 161 | 59 | ALPR RTCC PREG UAS FRT BWC FUS | 2 (69) | — | 0 | 4 | 9: ALPR SHARE RTCC PREG DOT UAS FRT BWC FUS | CCTV GSD | no legislation claims |
| OH | 0 (0) | 1/0/0 | 7,376 | 833 | ALPR RTCC PREG UAS GSD FRT VA DB BWC FUS | 140 (2,305) | OpenStates | 6 | 7 | 14: ALPR SHARE RTCC PREG DOT UAS GSD FRT VA DB BWC FUS PROC LEG | CCTV | — |
| OK | 0 (0) | 1/0/0 | 1,713 | 178 | ALPR RTCC PREG UAS FRT CSS DB BWC FUS OTH | 14 (112) | NCSL+ok_statute | 1 | 9 | 15: ALPR SHARE RTCC PREG DOT CCTV UAS FRT CSS DB BWC FUS PROC LEG OTH | GSD | — |
| OR | 1,419 (4) | 4/1/1 | 564 | 127 | ALPR PREG UAS FRT BWC FUS | 12 (69) | OpenStates | 3 | 12 | 11: ALPR SHARE PREG DOT CCTV UAS FRT BWC FUS PROC LEG | GSD RTCC | — |
| PA | 1,249 (1) | 3/2/0 | 2,896 | 453 | ALPR RTCC PREG UAS GSD FRT CSS DB BWC FUS OTH | 4 (26) | OpenStates | 2 | 10 | 16: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS DB BWC FUS PROC LEG OTH | — | — |
| RI | 0 (0) | 0/0/0 | 358 | 75 | ALPR RTCC PREG UAS DB BWC FUS | 17 (232) | OpenStates | 0 | 4 | 9: ALPR SHARE RTCC PREG UAS DB BWC FUS LEG | DOT CCTV GSD FRT | no official site registry |
| SC | 0 (0) | 0/1/0 | 1,983 | 376 | ALPR RTCC PREG UAS GSD FRT DB BWC FUS | 29 (383) | OpenStates | 3 | 8 | 13: ALPR SHARE RTCC PREG CCTV UAS GSD FRT DB BWC FUS PROC LEG | DOT | — |
| SD | 234 (1) | 2/1/0 | 194 | 56 | ALPR UAS FRT BWC FUS | 4 (68) | OpenStates | 4 | 7 | 10: ALPR SHARE DOT CCTV UAS FRT BWC FUS PROC LEG | GSD RTCC PREG | — |
| TN | 190 (2) | 1/1/1 | 3,635 | 677 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 18 (446) | OpenStates+NCSL | 4 | 9 | 17: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | — | — |
| TX | 3,994 (4) | 3/0/3 | 17,288 | 909 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 102 (3,959) | OpenStates | 30 | 14 | 16: ALPR SHARE RTCC PREG DOT UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | CCTV | — |
| UT | 1,469 (1) | 1/0/0 | 1,112 | 96 | ALPR RTCC PREG UAS FRT CSS DB BWC FUS OTH | 8 (166) | NCSL | 5 | 7 | 14: ALPR SHARE RTCC PREG DOT UAS FRT CSS DB BWC FUS PROC LEG OTH | CCTV GSD | — |
| VT | 0 (0) | 0/0/0 | 27 | 16 | UAS BWC FUS | 0 (0) | OpenStates+NCSL | 0 | 4 | 5: ALPR UAS BWC FUS LEG | DOT CCTV GSD FRT RTCC PREG | no official site registry; no Flock portal (EoF); Atlas thin (16 rows) |
| VA | 383 (1) | 4/0/0 | 3,871 | 347 | ALPR RTCC PREG UAS GSD FRT CSS DB BWC FUS OTH | 113 (2,864) | OpenStates | 6 | 11 | 15: ALPR SHARE RTCC PREG DOT UAS GSD FRT CSS DB BWC FUS PROC LEG OTH | CCTV | — |
| WA | 2,755 (4) | 8/0/0 | 2,344 | 226 | ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 50 (777) | OpenStates | 13 | 16 | 18: ALPR SHARE RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS PROC LEG ACC OTH | — | — |
| WV | 0 (0) | 0/0/0 | 250 | 52 | ALPR PREG UAS FRT BWC FUS | 1 (20) | OpenStates | 0 | 4 | 8: ALPR SHARE PREG UAS FRT BWC FUS LEG | DOT CCTV GSD RTCC | no official site registry |
| WI | 0 (0) | 2/0/0 | 2,652 | 495 | ALPR PREG UAS GSD FRT CSS VA DB BWC FUS OTH | 51 (570) | OpenStates | 7 | 7 | 15: ALPR SHARE PREG DOT UAS GSD FRT CSS VA DB BWC FUS PROC LEG OTH | CCTV RTCC | — |
| WY | 0 (0) | 0/0/0 | 95 | 38 | ALPR PREG UAS DB BWC FUS | 2 (28) | OpenStates | 1 | 5 | 9: ALPR SHARE PREG UAS DB BWC FUS PROC LEG | DOT CCTV GSD FRT RTCC | no official site registry; Atlas thin (38 rows) |

**What the state table shows** (inference over the cells above):
- **Most multi-class coverage rests on one source.** Take the ten non-camera technology classes (UAS, BWC,
  FRT, GSD, CSS, RTCC, PREG, DB, FUS, VA). In 49 states at least 5 of them, and in 38 states at least 7, come
  *only* from the EFF Atlas: one NGO compilation, loaded once, with City/State kept as context rather than
  claims. A second source for any of these classes exists only in CA, MA, NY and WA, through CCOPS filings
  (FRT/GSD/UAS). The median state has 8 distinct ingested sources with local evidence.
- **No official site registry ingested:** AR, DE, ME, MI, MS, NH, RI, VT, WV, WY. No DOT/511 layer: those 10
  plus NM and SC. TX's statewide `dot_511_tx` is gated (rights UNDETERMINED); TX DOT points arrive only through
  a third-party republish (`camreg_txdot_rep_tx`).
- **No Flock portal in the mirror:** AK, DC, HI, MT, NH, VT.
- **No state legislation claims:** DE, DC, HI, KY, MS, ND (OpenStates queries returned empty or unmatched).
- **Weakest states** (≤4 distinct ingested sources): MS (3), DE, HI, NH, ND, RI, VT, WV (4 each).

## 4. The 100 largest US cities

Column key:
- **Official site srcs (in radius):** camera-registry sources with hosted points within the city's land-area
  circle (T2, inference). Circles overlap neighbours, for example `lojic_ky` in Cincinnati.
- **Atlas:** rows whose City+State match.
- **Flock portal:** Eyes on Flock slug and stated cameras.
- **Agenda:** the fetched agenda platform.
- **City-scoped srcs:** registry sources scoped to that city.
- **Srcs:** the number of distinct ingested sources with local evidence.

| # | City | St | Pop 2024 | Official site srcs (in radius) | OSM-DeFlock pts | Atlas rows: classes | Flock portal (cams) | Agenda | City-scoped srcs | Srcs | Classes (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | New York | NY | 8,478,072 | aikner, nyc_jgrayson_ny, nyc_weltia_ny | 1,002 | 10: ALPR RTCC UAS GSD FRT CSS VA BWC OTH | — | — | ccops_nyc_post, procportal_nyc_ny | 7 | 14: ALPR RTCC DOT CCTV UAS GSD FRT CSS VA BWC PROC LEG ACC OTH |
| 2 | Los Angeles | CA | 3,878,704 | caloes_ca, trafficops_ca | 941 | 30: ALPR RTCC PREG UAS FRT CSS VA DB BWC OTH | — | primegov | — | 5 | 13: ALPR RTCC PREG DOT UAS FRT CSS VA DB BWC PROC LEG OTH |
| 3 | Chicago | IL | 2,721,308 | chicago_il, uchicago, dot:il | 960 | 24: ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS | — | — | — | 5 | 13: ALPR RTCC PREG DOT CCTV UAS GSD FRT CSS VA DB BWC FUS |
| 4 | Houston | TX | 2,390,125 | txdot_rep_tx | 2,632 | 29: ALPR RTCC PREG UAS GSD FRT CSS VA DB BWC FUS OTH | — | — | — | 3 | 13: ALPR RTCC PREG DOT UAS GSD FRT CSS VA DB BWC FUS OTH |
| 5 | Phoenix | AZ | 1,673,164 | azdot_az, firemedic | 497 | 13: ALPR RTCC UAS FRT CSS BWC FUS | — | legistar | — | 5 | 10: ALPR RTCC DOT UAS FRT CSS BWC FUS PROC LEG |
| 6 | Philadelphia | PA | 1,573,916 | nitro, oem_camera, penndot_pa, ucsd | 78 | 7: ALPR RTCC UAS CSS DB BWC FUS | — | — | — | 6 | 9: ALPR RTCC DOT CCTV UAS CSS DB BWC FUS |
| 7 | San Antonio | TX | 1,526,656 | txdot_rep_tx | 416 | 11: ALPR PREG UAS FRT BWC FUS | — | legistar, primegov | — | 5 | 9: ALPR PREG DOT UAS FRT BWC FUS PROC LEG |
| 8 | San Diego | CA | 1,404,452 | caloes_ca, trafficops_ca | 663 | 26: ALPR PREG UAS GSD CSS DB BWC FUS | san-diego-ca-pd (500) | — | — | 5 | 10: ALPR SHARE PREG DOT UAS GSD CSS DB BWC FUS |
| 9 | Dallas | TX | 1,326,087 | txdot_rep_tx | 847 | 15: ALPR RTCC PREG UAS FRT VA DB BWC FUS OTH | dallas-tx-pd (694) | legistar | — | 5 | 14: ALPR SHARE RTCC PREG DOT UAS FRT VA DB BWC FUS PROC LEG OTH |
| 10 | Jacksonville | FL | 1,009,833 | fl511_fl | 314 | 12: ALPR RTCC PREG UAS GSD FRT CSS BWC | — | legistar | — | 4 | 11: ALPR RTCC PREG DOT UAS GSD FRT CSS BWC PROC LEG |
| 11 | Fort Worth | TX | 1,008,106 | txdot_rep_tx | 517 | 12: ALPR RTCC PREG UAS GSD CSS BWC FUS | — | legistar | — | 4 | 11: ALPR RTCC PREG DOT UAS GSD CSS BWC FUS PROC LEG |
| 12 | San Jose | CA | 997,368 | caloes_ca | 784 | 11: ALPR PREG UAS FRT CSS BWC | san-jose-ca-pd (516) | — | — | 4 | 8: ALPR SHARE PREG DOT UAS FRT CSS BWC |
| 13 | Austin | TX | 993,588 | austin_tx, txdot_rep_tx | 308 | 22: ALPR RTCC PREG UAS FRT CSS DB BWC FUS | austin-tx-pd (?) | legistar | procportal_austin_tx | 7 | 13: ALPR SHARE RTCC PREG DOT UAS FRT CSS DB BWC FUS PROC LEG |
| 14 | Charlotte | NC | 943,476 | — | 273 | 8: ALPR RTCC PREG UAS CSS DB BWC | — | — | — | 2 | 7: ALPR RTCC PREG UAS CSS DB BWC |
| 15 | Columbus | OH | 933,263 | — | 500 | 21: ALPR RTCC UAS GSD FRT BWC FUS | columbus-oh-pd (?) | legistar | — | 4 | 10: ALPR SHARE RTCC UAS GSD FRT BWC FUS PROC LEG |
| 16 | Indianapolis | IN | 891,484 | — | 655 | 25: ALPR RTCC PREG UAS GSD FRT CSS BWC FUS OTH | — | — | — | 2 | 10: ALPR RTCC PREG UAS GSD FRT CSS BWC FUS OTH |
| 17 | San Francisco | CA | 827,526 | — | 0 | 15: ALPR RTCC PREG UAS GSD FRT DB BWC FUS OTH | san-francisco-ca-pd (483) | legistar | procportal_sf_ca | 4 | 13: ALPR SHARE RTCC PREG UAS GSD FRT DB BWC FUS PROC LEG OTH |
| 18 | Seattle | WA | 780,995 | seattle_wa, dot:wa | 50 | 11: ALPR RTCC PREG UAS FRT BWC FUS | — | legistar | ccops_seattle | 6 | 13: ALPR RTCC PREG DOT CCTV UAS GSD FRT BWC FUS PROC LEG ACC |
| 19 | Denver | CO | 729,019 | denver_co | 390 | 15: ALPR RTCC UAS GSD VA DB BWC | denver-co-pd (?) | legistar | — | 5 | 10: ALPR SHARE RTCC UAS GSD VA DB BWC PROC LEG |
| 20 | Oklahoma City | OK | 712,919 | — | 598 | 12: ALPR RTCC PREG UAS FRT CSS DB BWC FUS | — | — | okcpd_policy, osm_overpass | 4 | 11: ALPR RTCC PREG CCTV UAS FRT CSS DB BWC FUS LEG |
| 21 | Nashville | TN | 704,963 | nashville_tn | 307 | 16: ALPR PREG UAS GSD FRT DB BWC FUS OTH | — | — | — | 3 | 9: ALPR PREG UAS GSD FRT DB BWC FUS OTH |
| 22 | Washington | DC | 702,250 | arlington_va, dc_dot_dc, washington_dc, dot:dc | 122 | 8: ALPR PREG GSD FRT CSS VA BWC FUS | — | — | — | 6 | 10: ALPR PREG DOT CCTV GSD FRT CSS VA BWC FUS |
| 23 | El Paso | TX | 681,723 | stanford_us, txdot_rep_tx | 160 | 8: ALPR PREG UAS CSS BWC FUS | el-paso-tx-pd (150) | legistar | — | 6 | 10: ALPR SHARE PREG DOT UAS CSS BWC FUS PROC LEG |
| 24 | Las Vegas | NV | 678,922 | — | 152 | 12: ALPR RTCC PREG UAS GSD FRT CSS BWC FUS | — | primegov | — | 3 | 11: ALPR RTCC PREG UAS GSD FRT CSS BWC FUS PROC LEG |
| 25 | Boston | MA | 673,458 | massdot_ma | 54 | 11: ALPR UAS GSD FRT CSS DB BWC FUS | — | legistar | — | 4 | 11: ALPR DOT UAS GSD FRT CSS DB BWC FUS PROC LEG |
| 26 | Detroit | MI | 645,705 | — | 575 | 15: ALPR RTCC UAS GSD FRT VA BWC FUS | — | legistar | — | 3 | 10: ALPR RTCC UAS GSD FRT VA BWC FUS PROC LEG |
| 27 | Louisville | KY | 640,796 | lojic_ky, dot:ky | 504 | 12: ALPR RTCC PREG UAS GSD FRT BWC OTH | — | — | — | 4 | 9: ALPR RTCC PREG DOT UAS GSD FRT BWC OTH |
| 28 | Portland | OR | 635,749 | portland_or, dot:or, dot:wa | 76 | 5: ALPR PREG UAS BWC | — | — | — | 5 | 5: ALPR PREG DOT UAS BWC |
| 29 | Memphis | TN | 610,919 | — | 491 | 15: ALPR RTCC PREG UAS GSD CSS DB BWC OTH | — | — | — | 2 | 9: ALPR RTCC PREG UAS GSD CSS DB BWC OTH |
| 30 | Baltimore | MD | 568,271 | baltimore_atves_md, baltimore_md, esri_dash, md_opendata, dot:md | 47 | 12: ALPR RTCC PREG GSD CSS DB BWC | — | legistar | — | 8 | 11: ALPR RTCC PREG DOT CCTV GSD CSS DB BWC PROC LEG |
| 31 | Milwaukee | WI | 563,531 | — | 200 | 10: ALPR PREG UAS GSD CSS BWC FUS | milwaukee-wi-pd (38) | legistar | — | 4 | 10: ALPR SHARE PREG UAS GSD CSS BWC FUS PROC LEG |
| 32 | Albuquerque | NM | 560,326 | — | 350 | 13: ALPR RTCC PREG UAS GSD FRT CSS BWC | — | legistar | — | 3 | 10: ALPR RTCC PREG UAS GSD FRT CSS BWC PROC LEG |
| 33 | Tucson | AZ | 554,013 | azdot_az, duganmeyer, firemedic | 241 | 8: ALPR RTCC PREG UAS CSS BWC | tucson-az-pd (?) | — | — | 6 | 8: ALPR SHARE RTCC PREG DOT UAS CSS BWC |
| 34 | Fresno | CA | 550,105 | caloes_ca, trafficops_ca | 150 | 9: ALPR RTCC UAS GSD BWC OTH | — | legistar | — | 5 | 9: ALPR RTCC DOT UAS GSD BWC PROC LEG OTH |
| 35 | Sacramento | CA | 535,798 | caloes_ca | 250 | 19: ALPR RTCC UAS GSD FRT CSS VA DB BWC FUS | — | legistar | — | 4 | 13: ALPR RTCC DOT UAS GSD FRT CSS VA DB BWC FUS PROC LEG |
| 36 | Atlanta | GA | 520,070 | dot:ga | 575 | 30: ALPR RTCC PREG UAS GSD FRT DB BWC FUS OTH | — | legistar | — | 4 | 13: ALPR RTCC PREG DOT UAS GSD FRT DB BWC FUS PROC LEG OTH |
| 37 | Mesa | AZ | 517,151 | azdot_az, firemedic | 123 | 6: ALPR RTCC UAS DB BWC OTH | — | legistar | — | 5 | 9: ALPR RTCC DOT UAS DB BWC PROC LEG OTH |
| 38 | Kansas City | MO | 516,032 | kcmo_mo, dot:mo | 854 | 9: ALPR PREG UAS GSD CSS DB BWC FUS OTH | — | legistar | procportal_kcmo_mo | 6 | 12: ALPR PREG DOT UAS GSD CSS DB BWC FUS PROC LEG OTH |
| 39 | Raleigh | NC | 499,825 | raleigh_nc | 129 | 12: ALPR UAS FRT CSS BWC FUS | raleigh-nc-pd (29) | — | — | 4 | 8: ALPR SHARE DOT UAS FRT CSS BWC FUS |
| 40 | Colorado Springs | CO | 493,554 | — | 196 | 10: ALPR RTCC PREG UAS DB BWC | colorado-springs-co-pd (?) | legistar | — | 4 | 9: ALPR SHARE RTCC PREG UAS DB BWC PROC LEG |
| 41 | Omaha | NE | 489,265 | — | 75 | 12: ALPR RTCC UAS GSD DB BWC | — | — | — | 2 | 6: ALPR RTCC UAS GSD DB BWC |
| 42 | Miami | FL | 487,014 | fl511_fl, mhebert | 100 | 16: ALPR PREG UAS GSD FRT CSS DB BWC FUS | miami-fl-pd (40) | — | — | 5 | 11: ALPR SHARE PREG DOT UAS GSD FRT CSS DB BWC FUS |
| 43 | Virginia Beach | VA | 454,808 | — | 148 | 8: ALPR RTCC PREG UAS GSD DB BWC | virginia-beach-va-pd (94) | — | — | 3 | 8: ALPR SHARE RTCC PREG UAS GSD DB BWC |
| 44 | Long Beach | CA | 450,901 | caloes_ca, trafficops_ca | 71 | 9: ALPR RTCC PREG UAS FRT CSS BWC | — | legistar, primegov | — | 6 | 10: ALPR RTCC PREG DOT UAS FRT CSS BWC PROC LEG |
| 45 | Oakland | CA | 443,554 | caloes_ca, trafficops_ca | 819 | 12: ALPR PREG UAS GSD CSS DB BWC | oakland-ca-pd (293) | legistar | ccops_oakland | 7 | 14: ALPR SHARE PREG DOT CCTV UAS GSD FRT CSS DB BWC PROC LEG ACC |
| 46 | Minneapolis | MN | 428,579 | carver_mn, mndot_mn | 118 | 18: ALPR RTCC PREG UAS GSD FRT CSS VA BWC OTH | — | — | — | 4 | 11: ALPR RTCC PREG DOT UAS GSD FRT CSS VA BWC OTH |
| 47 | Bakersfield | CA | 417,468 | caloes_ca | 217 | 10: ALPR PREG UAS GSD CSS BWC | bakersfield-ca-pd (462) | — | — | 4 | 8: ALPR SHARE PREG DOT UAS GSD CSS BWC |
| 48 | Tulsa | OK | 415,154 | — | 360 | 6: ALPR RTCC DB BWC | tulsa-ok-pd (?) | — | — | 3 | 5: ALPR SHARE RTCC DB BWC |
| 49 | Tampa | FL | 414,547 | fl511_fl | 73 | 14: ALPR RTCC PREG UAS GSD FRT BWC | — | — | — | 3 | 8: ALPR RTCC PREG DOT UAS GSD FRT BWC |
| 50 | Arlington | TX | 403,672 | txdot_rep_tx | 216 | 7: ALPR RTCC UAS VA BWC | arlington-tx-pd (134) | — | — | 4 | 7: ALPR SHARE RTCC DOT UAS VA BWC |
| 51 | Aurora | CO | 403,130 | denver_co | 202 | 8: ALPR RTCC UAS FRT DB BWC | aurora-co-pd (121) | legistar | — | 5 | 9: ALPR SHARE RTCC UAS FRT DB BWC PROC LEG |
| 52 | Wichita | KS | 400,991 | — | 378 | 6: ALPR UAS GSD FRT BWC | wichita-ks-pd (191) | — | — | 3 | 6: ALPR SHARE UAS GSD FRT BWC |
| 53 | Cleveland | OH | 365,379 | — | 272 | 15: ALPR RTCC PREG UAS DB BWC FUS | — | legistar | — | 3 | 9: ALPR RTCC PREG UAS DB BWC FUS PROC LEG |
| 54 | New Orleans | LA | 362,701 | freese_dm, nola_la, nola_safety_la, dot:la | 30 | 9: ALPR RTCC PREG UAS FRT BWC | — | — | — | 6 | 7: ALPR RTCC PREG DOT UAS FRT BWC |
| 55 | Henderson | NV | 350,039 | caloes_ca | 78 | 4: ALPR PREG UAS BWC | — | — | — | 3 | 5: ALPR PREG DOT UAS BWC |
| 56 | Honolulu | HI | 344,967 | honolulu_hi | 10 | 8: ALPR RTCC PREG UAS FRT BWC FUS | — | — | — | 3 | 8: ALPR RTCC PREG DOT UAS FRT BWC FUS |
| 57 | Anaheim | CA | 344,561 | caloes_ca | 65 | 7: ALPR PREG UAS FRT CSS DB BWC | — | — | — | 3 | 8: ALPR PREG DOT UAS FRT CSS DB BWC |
| 58 | Orlando | FL | 334,854 | cclemire, fl511_fl, trafficops_ca | 54 | 24: ALPR RTCC PREG UAS FRT DB BWC FUS OTH | — | — | — | 5 | 11: ALPR RTCC PREG DOT CCTV UAS FRT DB BWC FUS OTH |
| 59 | Lexington | KY | 329,437 | lexington_ky, lojic_ky, dot:ky | 277 | 7: ALPR RTCC PREG UAS FRT BWC | — | — | — | 5 | 7: ALPR RTCC PREG DOT UAS FRT BWC |
| 60 | Stockton | CA | 324,975 | caloes_ca | 132 | 6: ALPR PREG UAS GSD BWC OTH | stockton-ca-pd (147) | legistar | — | 5 | 10: ALPR SHARE PREG DOT UAS GSD BWC PROC LEG OTH |
| 61 | Riverside | CA | 323,757 | caloes_ca, trafficops_ca | 227 | 13: ALPR UAS FRT CSS DB BWC | — | legistar | — | 5 | 9: ALPR DOT UAS FRT CSS DB BWC PROC LEG |
| 62 | Irvine | CA | 318,683 | caloes_ca | 393 | 6: ALPR RTCC PREG UAS BWC | — | — | — | 3 | 6: ALPR RTCC PREG DOT UAS BWC |
| 63 | Corpus Christi | TX | 317,317 | txdot_rep_tx | 5 | 8: ALPR UAS BWC | — | legistar | — | 4 | 6: ALPR DOT UAS BWC PROC LEG |
| 64 | Newark | NJ | 317,303 | aikner | 15 | 13: ALPR RTCC UAS GSD BWC | — | — | — | 3 | 6: ALPR RTCC DOT UAS GSD BWC |
| 65 | Santa Ana | CA | 316,184 | caloes_ca, trafficops_ca | 43 | 9: ALPR PREG FRT CSS DB BWC FUS | santa-ana-ca-pd (24) | — | — | 5 | 9: ALPR SHARE PREG DOT FRT CSS DB BWC FUS |
| 66 | Cincinnati | OH | 314,915 | lojic_ky, dot:ky | 103 | 18: ALPR RTCC PREG UAS GSD BWC FUS | — | — | — | 4 | 8: ALPR RTCC PREG DOT UAS GSD BWC FUS |
| 67 | Pittsburgh | PA | 307,668 | penndot_pa, ucsd | 234 | 17: ALPR RTCC UAS GSD FRT BWC FUS | — | legistar | — | 5 | 10: ALPR RTCC DOT UAS GSD FRT BWC FUS PROC LEG |
| 68 | St. Paul | MN | 307,465 | carver_mn | 29 | 24: ALPR UAS FRT CSS VA DB BWC FUS | — | — | — | 3 | 9: ALPR DOT UAS FRT CSS VA DB BWC FUS |
| 69 | Greensboro | NC | 307,381 | — | 43 | 8: ALPR RTCC PREG UAS DB BWC | greensboro-nc-pd (4) | — | — | 3 | 7: ALPR SHARE RTCC PREG UAS DB BWC |
| 70 | Jersey City | NJ | 302,824 | — | 25 | 6: ALPR BWC | — | — | — | 2 | 2: ALPR BWC |
| 71 | Durham | NC | 301,870 | — | 57 | 5: ALPR GSD FRT BWC OTH | — | — | — | 2 | 5: ALPR GSD FRT BWC OTH |
| 72 | Lincoln | NE | 300,619 | — | 65 | 11: ALPR UAS FRT DB BWC FUS | — | — | — | 2 | 6: ALPR UAS FRT DB BWC FUS |
| 73 | North Las Vegas | NV | 294,034 | — | 33 | 2: ALPR BWC | — | — | — | 2 | 2: ALPR BWC |
| 74 | Plano | TX | 293,286 | txdot_rep_tx | 218 | 6: ALPR RTCC PREG UAS FRT BWC | — | — | — | 3 | 7: ALPR RTCC PREG DOT UAS FRT BWC |
| 75 | Anchorage | AK | 289,600 | — | 12 | 6: UAS FRT CSS BWC FUS | — | — | — | 2 | 6: ALPR UAS FRT CSS BWC FUS |
| 76 | Gilbert | AZ | 288,790 | azdot_az, firemedic | 84 | 3: ALPR UAS BWC | — | — | — | 4 | 4: ALPR DOT UAS BWC |
| 77 | Madison | WI | 285,300 | — | 35 | 13: ALPR UAS FRT BWC FUS OTH | — | legistar | — | 3 | 8: ALPR UAS FRT BWC FUS PROC LEG OTH |
| 78 | Reno | NV | 281,714 | caloes_ca | 124 | 12: ALPR RTCC PREG UAS GSD VA BWC | reno-nv-pd (29) | — | — | 4 | 9: ALPR SHARE RTCC PREG DOT UAS GSD VA BWC |
| 79 | Chandler | AZ | 281,231 | azdot_az, firemedic | 102 | 5: ALPR RTCC UAS BWC OTH | — | — | — | 4 | 6: ALPR RTCC DOT UAS BWC OTH |
| 80 | St. Louis | MO | 279,695 | olsson, dot:mo | 196 | 15: ALPR RTCC PREG UAS GSD CSS BWC FUS | — | — | — | 4 | 10: ALPR RTCC PREG DOT CCTV UAS GSD CSS BWC FUS |
| 81 | Chula Vista | CA | 278,546 | caloes_ca, trafficops_ca | 155 | 5: ALPR RTCC UAS DB BWC | chula-vista-ca-pd (150) | legistar | — | 6 | 9: ALPR SHARE RTCC DOT UAS DB BWC PROC LEG |
| 82 | Buffalo | NY | 276,617 | schellinger | 105 | 11: ALPR RTCC PREG UAS CSS DB BWC | — | civicclerk | — | 4 | 10: ALPR RTCC PREG CCTV UAS CSS DB BWC PROC LEG |
| 83 | Fort Wayne | IN | 273,203 | — | 100 | 3: ALPR UAS BWC | fort-wayne-in-pd (40) | civicclerk | — | 4 | 6: ALPR SHARE UAS BWC PROC LEG |
| 84 | Lubbock | TX | 272,086 | txdot_rep_tx | 188 | 7: ALPR PREG UAS BWC | lubbock-tx-pd (103) | — | — | 4 | 6: ALPR SHARE PREG DOT UAS BWC |
| 85 | St. Petersburg | FL | 267,102 | fl511_fl | 68 | 5: ALPR UAS FRT BWC | — | — | — | 3 | 5: ALPR DOT UAS FRT BWC |
| 86 | Toledo | OH | 265,638 | — | 187 | 7: ALPR RTCC PREG UAS GSD BWC | toledo-oh-pd (115) | legistar | — | 4 | 9: ALPR SHARE RTCC PREG UAS GSD BWC PROC LEG |
| 87 | Laredo | TX | 261,260 | stanford_us, txdot_rep_tx | 106 | 10: ALPR RTCC UAS FRT BWC | laredo-tx-pd (?) | — | — | 5 | 7: ALPR SHARE RTCC DOT UAS FRT BWC |
| 88 | Port St. Lucie | FL | 258,575 | fl511_fl | 110 | 4: ALPR UAS FRT BWC | — | legistar | — | 4 | 7: ALPR DOT UAS FRT BWC PROC LEG |
| 89 | Glendale | AZ | 258,143 | azdot_az, firemedic | 61 | 8: ALPR RTCC UAS GSD FRT VA BWC OTH | — | legistar | — | 5 | 11: ALPR RTCC DOT UAS GSD FRT VA BWC PROC LEG OTH |
| 90 | Irving | TX | 258,060 | txdot_rep_tx | 113 | 4: ALPR RTCC UAS FRT | irving-tx-pd (39) | — | — | 4 | 6: ALPR SHARE RTCC DOT UAS FRT |
| 91 | Winston-Salem | NC | 255,769 | — | 36 | 12: ALPR RTCC PREG UAS GSD BWC | — | legistar | — | 3 | 8: ALPR RTCC PREG UAS GSD BWC PROC LEG |
| 92 | Chesapeake | VA | 254,997 | — | 135 | 6: ALPR RTCC PREG UAS GSD BWC | chesapeake-va-pd (67) | — | — | 3 | 7: ALPR SHARE RTCC PREG UAS GSD BWC |
| 93 | Garland | TX | 250,431 | txdot_rep_tx | 93 | 3: ALPR UAS BWC | garland-tx-pd (61) | civicclerk | — | 5 | 7: ALPR SHARE DOT UAS BWC PROC LEG |
| 94 | Scottsdale | AZ | 246,170 | azdot_az, firemedic | 64 | 8: ALPR RTCC PREG UAS CSS DB BWC | — | — | — | 4 | 8: ALPR RTCC PREG DOT UAS CSS DB BWC |
| 95 | Boise | ID | 237,963 | achd_id | 9 | 4: ALPR UAS BWC | — | — | — | 3 | 4: ALPR DOT UAS BWC |
| 96 | Hialeah | FL | 235,388 | fl511_fl | 24 | 3: UAS FRT DB | — | — | — | 3 | 5: ALPR DOT UAS FRT DB |
| 97 | Frisco | TX | 235,208 | — | 160 | 2: ALPR PREG | frisco-tx-pd (130) | — | — | 3 | 3: ALPR SHARE PREG |
| 98 | Richmond | VA | 233,655 | — | 184 | 11: ALPR RTCC UAS GSD CSS BWC FUS | richmond-va-pd (103) | legistar | — | 4 | 10: ALPR SHARE RTCC UAS GSD CSS BWC FUS PROC LEG |
| 99 | Cape Coral | FL | 233,025 | — | 56 | 4: ALPR FRT DB BWC | — | — | — | 2 | 4: ALPR FRT DB BWC |
| 100 | Norfolk | VA | 231,105 | — | 170 | 6: ALPR RTCC PREG GSD BWC | norfolk-va-pd (175) | — | — | 3 | 6: ALPR SHARE RTCC PREG GSD BWC |

**What the city table shows:**
- **Official camera registries:** at least one in 69 cities. None in 31, including Charlotte, Columbus,
  Indianapolis, San Francisco, Oklahoma City, Las Vegas, Detroit, Memphis, Milwaukee, Albuquerque, Tulsa and
  Cleveland.
- **Flock portal (mirror):** 35 cities. Absent in 65, including NYC, LA, Chicago, Houston and Philadelphia. Some
  of these genuinely use Flock; others don't. The mirror can't tell the two apart.
- **Fetched agenda tenant:** 42 cities.
- **City-scoped documentary source:** 7 cities (NYC, Austin, San Francisco, Seattle, Oklahoma City, Kansas City,
  Oakland).
- **OSM/DeFlock ALPR points:** all 100 cities except San Francisco.
- **Per city:** a median of 4 distinct ingested sources and 9 classes. 36 cities have ≤3 sources.
- **Classes present in 0 of 100 cities:** SMM, FOR, SCH. Present in ≤3: ACC. CCTV (police/public CCTV) appears
  in 11 cities.
- **Oklahoma City** (the S2 pilot, rank 20): 4 sources (Atlas, OSM, `okcpd_policy`, `osm_overpass`). There is no
  Flock portal in the mirror, no fetched agenda tenant (`okc_council`/CivicClerk is unverified), and no public
  dossier (NEW-4).

## 5. International

Coverage is local when the claims are geolocated or sub-national, and coarse when they are country-level status
claims. Country is taken from hosted coordinates where the registry label is wrong (NEW-2; inference).

| Country / area | Local (geolocated) ingested sources | National / other ingested | Notes |
|---|---|---|---|
| Canada | ~18 camreg (AB 2, BC 5, MB 2, ON 9 incl. `cotgeo`, `yorku`, `cwarcgis`, `townofws`) | — | Ottawa/Peel/St. Albert/Winnipeg in own compartments; `camreg_edmonton_ab` gated; `panopti_ca` gated |
| United Kingdom | ~17 camreg (ENG 11 + `ruslan`, `esriukpolice`; SCT 3 + `sweeney`; NIR 1) + OSM London 1,646 | `uk_surveillance_camera_commissioner` (8 claims) | Nottingham 562 + `mark43` 561 axis-swapped (NEW-2); no UK ANPR source |
| Australia | 7 (ACT, Gold Coast, Moreton Bay, Camberwell, `camilo_schools`, `jelenic` Sydney, `squan` Melbourne) | — | `camreg_qldc_au` gated |
| New Zealand | 3 (`nzta`, `wellington`, `sfoss`) | — | |
| France | OSM-derived UCP layers (~1,000 pts) | `decp_fr`, `raa_prefectures`, `madada`; TED | the only country with procurement + authorization + records channels |
| EU/EEA (~30) | — | `ted_eu` (69,546 claims/run) | per-country split not computed |
| Belgium | `gistel_be`, `oosgis_nl` (labelled NL) | — | `declarationcamera_be` permitted but eID-blocked (0 claims) |
| Germany | `mueller_de` (24, Cologne) | — | published under dossier "DE" (NEW-1) |
| Netherlands | none correctly located | — | `amsterdam_camerakaart`, `rotterdam_cameraregister` gated |
| Denmark, Austria | none | — | `denmark_politi_cctv`, `austria_vidreg` gated (statutory registers) |
| Ireland | `donegal_ie` | — | |
| Spain / Portugal / Slovakia | `infocemosa` (Madrid) / `apram_pt` (1, no geometry) / `pipeline_sec` (3) | — | |
| Colombia | `puertogaitan_co`, `infraestructura` (Medellín) | — | |
| Brazil | `smart_sky` (1) | — | |
| Thailand | `thailand_th` (2,109) + OSM 148 | — | |
| Malaysia / Singapore / Indonesia | `ukm_my`, `nurnazihah`, `yazid`, `ira`, `fifia` / `bangla_bd` (labelled BD) / `indonesia_id`, `cheicylia`, `vidya` | — | |
| Taiwan / Hong Kong / Japan / Mongolia | `forwardalliance` (1,829), `kunying` / `polyu_hk` / `bouhan_jp` (56) / `monmap_mn`, `gmh_emc_ga` (labelled GA) | — | `camreg_hk_hk` gated |
| Saudi Arabia / Israel / Palestine | `riyadh_sa` (1,128), `yline` / `helberg` (1) / `ramallah_ps` (6) | — | |
| South Africa | `keshan` (149, Durban area) | — | |
| ~75 / ~190 countries | — | `carnegie_ai_gsi` (660 claims), `facial_recognition_world_map` (202) | coarse country-level AI/FRT status only |
| China | — | coarse only; `aspi_mapping_chinas_tech_giants` permitted, WAF-403, 0 claims | |
| India, Africa (ex-ZA), rest of Latin America, Russia, Middle East (ex-SA/IL/PS) | none | coarse only | |
| US territories | PR: OSM 166 pts, Atlas 13 rows, OpenStates matched; GU 2 / VI 3 Atlas rows; AS, MP none | — | tribal nations: no source of any status |

## 6. Vendor view

"Evidence" means a registry source whose hosted claims attest deployments of that vendor. Atlas vendor counts come
from the upstream CSV, because the hosted Atlas claims don't carry the vendor (NEW-7).

| Vendor | Registry sources evidencing deployments (status) | Vendor-published channel | In registry? | Gap |
|---|---|---|---|---|
| **Flock Safety** (ALPR, Raven GSD, drones, FlockOS) | `eyes_on_flock` (ingested; 1,528 portals / 39,499 stated cameras; 45 states); `camreg_osm_surveillance` (ingested; DeFlock ALPR republish, vendor not attributed); agency-published Flock location layers `camreg_duganmeyer`, `camreg_lpd_flock`, `camreg_jmh_us`, `camreg_friendswood_tx` (ingested; about 138 points); `okcpd_policy` (ingested, 3 claims); Atlas 2,748 vendor rows (ingested, vendor not a claim); `okc_procurement` (permitted, 0 claims, WAF); `agency_audit_export` (permitted, never ingested); `dossier_okc`, `deflock`, `have_i_been_flocked`, `alpr_watch*`, `sm_alpr`, `eyes_off_eugene`, `private_eyes` (gated); SRC-001/002/014 (candidates) | per-agency transparency portals `transparency.flocksafety.com/<agency>`; the P11.1 `flock_portal` connector reads them **only through** the Eyes on Flock mirror | origin row `flock_transparency_portals` = **refused** (403 on every path; ToS forbids bulk extraction); `internet_archive_wayback` excludes `*.flocksafety.com` | the mirror covers ~23% of its own 6,634-network estimate; sharing edges are unresolved and unpublished; Raven, Aerodome/drone and FlockOS/RTCC products have no channel beyond ~100 Atlas rows; public search-audit exports (721 portals) are a Part VIII lane (search reasons) |
| **Axon** (incl. **Fusus**; BWC, Evidence.com, Fleet ALPR, DFR) | Atlas 1,077 rows (BWC 838, camera registry 156 = Fusus, RTCC 51, drones 16), ingested with the vendor not a claim; `pathways_rtcc_federation` (4 claims) | Axon Community Connect (public listing plus per-org stats; 321 communities); city Fusus registry pages | `axon_community_connect` = **gated** (REFERENCE, never ingested) | no ingested Axon or Fusus channel; Fleet in-car ALPR (mobile ALPR) has no current source |
| **Motorola Solutions / Vigilant / WatchGuard / Avigilon** | `eff_data_driven` (ingested; 2016–17 Vigilant LEARN sharing aggregates, 630 edges); Atlas 629 rows; `dossier_san_diego` (gated; SDPD Vigilant subscription) | LEARN sharing reports (agency-generated); CommandCentral community-camera registries | no current channel | LEARN sharing data is nine years old; no Motorola registry channel |
| **SoundThinking / ShotSpotter** | Atlas 935 rows (GSD 164; CrimeTracer 762); `ccops_oakland` (ingested; ShotSpotter filings); `pathways_acoustic_drone_location` (3 claims); SRC-017 Chicago OIG (candidate) | none public (sensor locations are secret) | `wired_shotspotter_leak` = **refused** (leak veto) | contracts and renewals only through agendas and procurement keywords; no customer list |
| **Genetec** (AutoVu ALPR, Security Center RTCC) | Atlas 9 rows | — | none | effectively zero |
| **Rekor** (ALPR, OpenALPR) | Atlas 37 rows | — | none | effectively zero |
| **Skydio / Brinc / DJI** (drones, DFR) | Atlas: Skydio 31, Brinc 25, DJI 748 rows; `pathways_acoustic_drone_location` (EFF page) | FAA Part 107 waivers / COAs (government, not vendor) | `faa_drone_waivers` gated; SRC-025 candidate (screening_required: personal fields) | no DFR program list; no drone procurement channel beyond USAspending/TED keyword `drone` |
| **Clearview AI** | Atlas 77 rows (FRT); `gao_surveillance_reports` (GAO-21-518, 10 claims); coarse `facial_recognition_world_map` | — | none | no customer or contract channel; no state FRT-reporting regime ingested |

## 7. Ranked blind spots, for I2's search matrix

The rank combines three things: the operator's stated targets (Flock, Axon and public-private networks, then
missing geographies, then missing technology classes); how much of the local denominator a gap leaves
unexplained; and whether an independent (non-mirror) channel exists that SIG has not touched. The evidence for
each rank is in the cited sections, findings and CSV rows.

| # | Blind spot | Kind | Evidence | I2 matrix cells to open |
|---|---|---|---|---|
| 1 | **Flock at origin and at scale**: no origin channel; one mirror covers ~23% of estimated networks; 65 of 100 cities have no portal; sharing graph unresolved | channel × ALPR/SHARE | §6; NEW-6; `flock_transparency_portals` refused | per-agency Flock evidence from agendas, procurement (Sourcewell/Omnia contracts), state ALPR policy filings, agency-published Flock layers (4 found by catalog sweep → search ArcGIS/Socrata/CKAN for "Flock"), audit-log records releases (Part VIII-screened), EoF snapshots/back-fill |
| 2 | **Axon/Fusus and other public-private camera registries and RTCC** | channel × PREG/RTCC | §6; `axon_community_connect` gated; PREG/RTCC hosted only via Atlas (756 + 242 rows) | Axon Community Connect, Fusus city registries ("Connect <City>"), Ring/Neighbors public-safety posts, Motorola CommandCentral registries, council approvals of RTCC contracts |
| 3 | **Jurisdiction attribution of what is already ingested** (Atlas, EoF, OSM ALPR, OpenStates, CCOPS, agenda, procurement) | geography (internal) | NEW-4; 22 states without a dossier; §3 | not a search cell. I8 must resolve before coverage can be measured; without it every geography gap is overstated in the product |
| 4 | **Statutory and ordinance reporting regimes**: state ALPR audit and usage reports; CCOPS annual reports (5 of ~26 ingested; SF 0 claims; Berkeley, Davis, Boston, Baltimore, Nashville and Grand Rapids gated); state FRT accountability reports | channel × LEG/ACC/all classes | §2.2 (ACC 11 ingested, 3 of 100 cities); `ccops_*` rows; NCSL seed frozen 2022-02-03 | state-by-state ALPR statute reporting clauses (audit or report duties), CCOPS jurisdictions list, FRT laws with reporting, SRC-011/012/015/017/021 |
| 5 | **Official camera and DOT registries missing in 10 states** (AR, DE, ME, MI, MS, NH, RI, VT, WV, WY) and **DOT/511 feeds** in ~25 states (TX gated) | geography × DOT/CCTV | §3 state table | state 511 / DOT ArcGIS services for each missing state; rights review for `dot_511_tx` |
| 6 | **Procurement and cooperative contracts** linking vendors to agencies: Sourcewell, NASPO, OMNIA, BuyBoard, TIPS, HGACBuy, Equalis, GSA all gated; city portals in 4 of the 100 largest cities; no state procurement | channel × PROC | §2.3 (procurement 8 ingested / 17 gated); SRC-006/010/016 | cooperative award documents per vendor (Flock, Axon, Motorola, SoundThinking, Genetec, Rekor, Skydio, Brinc); state contract registers |
| 7 | **Zero-channel technology classes**: social-media monitoring, mobile forensics, US school surveillance; no ontology term for traffic enforcement | technology | NEW-8; §2.2 | vendor names (Cellebrite, GrayKey/Magnet, Babel Street, Dataminr, Gaggle, GoGuardian, Evolv, Navigate360) × procurement, agendas, CCOPS |
| 8 | **Drones/DFR, gunshot detection, face recognition, cell-site simulators** beyond Atlas snapshots | technology | §2.2 (hosted only via Atlas plus 1–3 EFF claims); `faa_drone_waivers` gated; `aclu_cell_site_simulators` gated | FAA DFR waivers and COAs (screened), SoundThinking contracts, FRT policy and reporting, CSS agency-possession records |
| 9 | **Thin large cities**: Charlotte, Indianapolis, Memphis, Omaha, Jersey City, Durham, Lincoln, North Las Vegas, Anchorage, Cape Coral (2 sources each), plus 26 more with 3; Oklahoma City has no Flock portal and no dossier | geography | §4 city table | per-city open-data portal, agenda platform (Granicus, CivicPlus and BoardDocs are gated platforms) and CCOPS/policy search |
| 10 | **Mobile ALPR and ALPR sharing currency**: the only sharing data is the 2016–17 EFF Data Driven release; mobile ALPR has 1 source | technology × currency | §2.2 (mALPR 1); `sharing_edges.csv` | LEARN or Flock sharing reports obtained by records requests, state data-sharing MOUs, Axon Fleet deployments |
| 11 | **International**: local evidence in ~27 countries is mostly ad hoc ArcGIS layers, several mislabelled; EU statutory registers gated (DK, AT, NL cities, BE eID); no UK ANPR, Canada only partial | geography | §5; NEW-2 | national camera registers, procurement portals per country, ANPR programmes (UK NASPLE), Canadian municipal open data |
| 12 | **Records and court corpora**: MuckRock WAF-blocked (6 claims), DocumentCloud and CourtListener gated, NextRequest/GovQA gated | channel | §2.3 (records-release 2 ingested / 7 gated) | released-document corpora per vendor and technology |
| 13 | **Data brokers and investigative platforms** (LexisNexis, TransUnion/TLO, Thomson Reuters CLEAR, Fog Data Science) | technology | DB hosted only via Atlas and 1 EFF claim | procurement keywords; USAspending keyword list lacks these terms (`live_targets.toml` usaspending keywords) |
| 14 | **US territories and tribal nations** | geography | §5 last row | territorial police procurement, legislative records; tribal police agencies (BIA) |

## 8. Findings raised by this row

`findings/incoming/I1.csv`, all `proposed`:

| id | Sev | Title (short) |
|---|---|---|
| NEW-1 | S1 | ISO country codes collide with US state codes in the public jurisdiction index and dossiers (DE, ID, MN) |
| NEW-2 | S1 | Wrong coordinates or labels in at least 7 sources (axis swap; FDOT D5 published as CA; GA/BD/NL rows in Mongolia, Singapore, Belgium) |
| NEW-3 | S2 | 5,290 published sites without geometry (IL DOT 2,936 of 3,000) |
| NEW-4 | S1 | Only geolocated registry sources reach jurisdiction pages; 22 states (incl. OK) have no dossier; OSM ALPR and EoF portals carry no jurisdiction |
| NEW-5 | S2 | The national ALPR layer is ingested from two overlapping ArcGIS republishes of OSM/DeFlock, not the origin |
| NEW-6 | S2 | Flock coverage rests on one mirror (~23% of estimated networks); sharing edges unresolved and unpublished |
| NEW-7 | S2 | Vendors not modelled; the Atlas vendor field is context-only; 0 vendor entities in the API |
| NEW-8 | S2 | Zero-channel classes (SMM, forensics, US school surveillance); no ontology term for traffic enforcement |
| NEW-9 | S1 | Every camera-registry record is labelled `traffic_camera` (incl. Flock/DeFlock ALPR and police CCTV); exports have no technology field |

**Seen but already raised elsewhere, so not re-raised:**
- J1 NEW-2: the Atlas is attributed as "DeFlock community map" in API licence obligations. I re-observed it in
  `/v1/search?q=flock` at 16:52:48Z.
- E1 NEW-4 and J1 NEW-3: empty attributions. The `eyes_on_flock` entity attribution is `""` on a CC-BY-SA
  entity; observed on `/v1/entity/deployment/01a0bd32…` at 16:57Z.
- J1 NEW-7: the registry is not exported, and `/data-freshness/` lists only the 178 site sources out of 218
  ingested.
- E1 NEW-13: the database-right licence basis was applied to unresolved community registries.
- G1 NEW-13: freshness drift since the 2026-09-27 release.
- Also not raised: the `portal` compartment (CC-BY-SA-4.0) carries 10,054 CC0 DOT/municipal rows and no Eyes on
  Flock data. That is J1's lane.

## 9. Caveats (evidence class per claim)

- **Status column:** code (registry, targets, dispositions), plus recorded-execution (GCS run rows, live-run
  records, run ledgers), plus live-read (export rows, `evidence.json`). "Ingested-live" does not mean current: 34 of
  the 79 schedulers had never attempted a run as of 2026-09-30T16:51Z (`gcloud scheduler jobs list`), and the
  Atlas was loaded once (G1 NEW-8). P5 layering: this is `live-executed`, not
  `public`, for the 40 non-site sources.
- **Technology class and publisher type:** inference, by rule for 178 registry layers and by hand for 164 rows.
  Generic ArcGIS layers named "Camera registry" are classed CCTV with unverified type.
- **State and city attribution of hosted points:** inference. 8,272 OSM-derived points fall outside every US state polygon.
  That count includes the London, Paris-area and Thai republishes, plus US coastal points clipped by the 20m
  polygons. Cities are circle approximations. State and city attribution
  of the Atlas and Eyes on Flock uses upstream bytes read 2026-09-30, not hosted rows (the hosted Atlas is the
  2026-09-15 snapshot, ~15.2k rows). Agenda tenants count as local coverage when fetched; that says nothing about
  surveillance-relevant content per tenant.
- **Vendor counts:** Atlas upstream bytes (live-read). Hosted procurement `seller` values (2,788 subjects) could
  not be enumerated read-only through the API, because search matches labels only.
- **The 23% Flock ratio:** uses the mirror's own `estimated_total_networks`. It is an inference, not a census.
- **Nothing here is a rights judgement.** Availability is not clearance (P15). The 27 queue rows approve nothing.
- The API `/v1/coverage/{scope}` route serves absence records (`coverage_record`), not per-source volumes. It
  returned 0 records for `okc`, `national` and `us`, so it was not usable as volume evidence.

## Appendix — reproduction

Scratch: `docs/build/logs/next-phase/I1/`.
- `tools/geo_sites.py`: point-in-polygon and city circles.
- `tools/build_coverage.py`: writes `data/source_coverage.csv`.
- `tools/coverage_tables.py`: the state and city tables.

Run them with `uv run --offline python <script> <repo> <scratch>`. Inputs are the captures listed in §1.
