# J4 — Redistribution and feasibility matrix

Row **J4** of `META_PLAN.md` §6 Stream J (owner R/D, depends J1, I1). Written 2026-09-30 by Claude Code (Opus 5.5)
in the planning worktree (`claude/next-phase-planning`). Work window (`date -u`): **2026-09-30T17:22:13Z →
17:48:27Z**. Outputs:

- this note;
- `data/redistribution.csv` — 345 rows: the 342 registry sources plus 3 unregistered seed source ids that the live API serves;
- `findings/incoming/J4.csv` — NEW-1…NEW-7.

**This is not legal advice.** Every lane is a classification made from recorded licence and terms evidence. Where
that evidence is thin, the row says so. The lanes are inputs for J3 and for the operator's HG-03/HG-02 decisions;
they are not rights clearances (P4, P15).

**Evidence classes (P1).**
- `code`: file:line at planning HEAD. The cited paths are byte-identical to chain tip `b051732c`
  (`git diff --stat b051732c HEAD` over `connectors/ docs/build/reports/ exports/ db/ ops/ policy/` is empty).
- `recorded-execution`: committed sweep and run records, and I1's local copies of GCS run rows.
- `live-read`: bucket listings, 3 public-bucket GETs and 10 API GETs.
- `inference`: labelled wherever it is used.

---

## 0. Summary

**Raw-bytes lanes** (the per-source status of the original captured bytes; derived facts are covered separately):

| scope | raw-ok | derived-only | link-only | restricted | unknown | total |
|---|---|---|---|---|---|---|
| ingested-live (I1) | 42 | 167 | 0 | 8 | 1 | 218 |
| permitted-not-ingested | 12 | 5 | 0 | 2 | 0 | 19 |
| **live + permitted (task scope)** | **54** | **172** | **0** | **10** | **1** | **237** |
| gated | 2 | 0 | 45 | 8 | 46 | 101 |
| refused | 0 | 0 | 0 | 4 | 0 | 4 |
| unregistered seed ids served live | 0 | 0 | 0 | 0 | 3 | 3 |
| **all rows** | **56** | **172** | **45** | **22** | **50** | **345** |

- **Most sources are `derived-only`.** The registry records 147 of the 237 in-scope sources under two SIG-made
  bases: 90 `LicenseRef-OperatorAccepted-DBRight` and 57 `LicenseRef-PublicRecord-FactualCompilation`. Both
  cover publishing facts, not the upstream bytes. Another 12 are CC0 *labels* that SIG recorded, not upstream
  dedications (NEW-7).
- **The public site rows fall into lanes as follows.** Of the 236,994 rows in today's downloads:
  - 166,990 come from `raw-ok` sources. 154,528 of those are the single ODbL OSM layer.
  - 64,737 come from `derived-only` sources.
  - **5,110 come from sources whose own captured terms forbid redistribution** (NEW-1).
- **Attribution.** 21 of the 27 live sources whose licence requires attribution fail it (17) or meet it only
  partly (4). Counting every live source against its licence or SIG's own per-row promise, 171 of 218 fail
  (NEW-3; J1 NEW-2/3).
- **Raw bytes that actually exist.** The OCFL store holds 73.4 MB of capture bytes from 45 sources. By lane:
  35.0 MB `raw-ok` (35 sources), 21.9 MB `derived-only`, and 16.5 MB `restricted` (Eyes on Flock). Only 349 of
  6,144 recorded capture digests have bytes (NEW-5).
- **Cost** (§38.5, SIG-EXPORT-008). Downloads are served straight from GCS at internet egress rates, with no CDN,
  and the bucket can be listed anonymously (J1 NEW-1/12). A full release is 1.05 GB, about **$0.13 per
  download**. Monthly egress:

  | scenario | on GCS | via Cloud CDN | via R2 |
  |---|---|---|---|
  | low uptake | ≈ $13 | — | $0 egress |
  | medium uptake | ≈ $128 | — | $0 egress |
  | §38.5-scale uptake | ≈ $600 | ≈ $430 | $0 egress |
  | one looping scraper | ≈ $2,800 | — | $0 egress |

  Storage is under $2 a month at any plausible size.
- **Logs.** Run rows can be published after the scrub rules in §8 (S-1…S-14). No secrets, IP addresses or internal
  paths were found in the 387 run rows. The exposure is in:
  - free-text exception details;
  - document URLs;
  - the `robots_disregarded` events, whose disclosure is an operator decision;
  - capture headers.
- **Part VIII.**
  - Raw bytes keep data that ingest discards: OSM `user`/`uid`, Eyes on Flock free-text search reasons, and
    every ArcGIS attribute (NEW-4).
  - A person-named seed source id is live (NEW-6).
  - Nine rules (P8-1…P8-9, §9) set what each class may expose.

---

## 1. Method

**Inputs (read-only).**

Registry and rights evidence:
- `connectors/src/connectors/data/sources.toml`: 342 rows, parsed with `tomllib`. Per row: `custody_posture`,
  `[rights]` (`spdx`, `attribution`, `redistributable`, `derivative_permitted`, `terms_url`), `notes`,
  `ingestion_permitted`.
- `docs/build/reports/rights/*.md`: 106 per-source packets, plus 153 `annex/p2616` and 8 `annex/p293` annexes,
  `GL-GATE-07-batch.md` and `PROPOSED_DISPOSITIONS.md`.
- `RIGHTS_REVIEW_INDEX.md`. It is stale: it records 115 sources and 0 permitted (P21.1), so it was used only as
  history.
- `catalog_sweep_2026-09-18_reviewed.json`: 3,257 datasets with `licence_verbatim`. It was joined to
  `camera_registry_targets.toml` by endpoint or Socrata id; 215 of 223 targets matched.
- `policy/src/policy/data/licenses.toml` (compartments).
- Status per source from I1: `data/source_coverage.csv`.

Hosted evidence:
- Public release `sig-2026-09-27-ce480ab1`. `manifest.json` sha256 `717aeb44…` is still the A1 baseline.
- `LICENCES.json` (sha256 `893362ca…`) and `web/evidence.json` (`3df209d5…`), fetched 17:34:30Z.
- I1's local copies of every compartment's `sites.csv` (gitignored `docs/build/logs/next-phase/I1/`).

Bucket listings (`gcloud storage ls -l -r` / `du`, 17:27:23–17:40:35Z; **no restricted object was downloaded**):
- `-sig-restricted/evidence/**`: 5,328 objects, 79,411,154 B.
- `-sig-restricted/ops/**`: 447 objects, 7,071,437 B.
- `-sig-restricted/exports/`: 2,957,881,480 B.
- the restricted bucket as a whole: 3,148,581,057 B.
- `-sig-public`: 134 objects, 1,048,922,180 B.
- `-sig-web`: 51,483,763 B.

Run records: I1's local copy of the 387 GCS run rows (`runs_concat.txt`, 7,023,343 B). J4 used it to:
- join capture digests to OCFL object ids (digest ∈ object id, 349/350 matched);
- inventory fields;
- pattern-scan for scrub hazards. The scan reports **counts only**; no value was copied.

Eyes on Flock: I1's local copy of the public `GET /api/v1/data` response. It is byte-identical in size
(16,498,233 B) to the stored OCFL capture. J4 read only its key structure and pattern counts.

Live API: 10 × `GET /v1/search?q=…&limit=5|10`, 17:34:47–17:42:17Z, UA `SIG-planning-J4/1.0`, reading the
`license.obligations` attribution per source.

**Classification rules.** The first match wins. The implementation is a scratch script; each CSV row's `note` names
the rule that fired.

| # | condition | lane |
|---|---|---|
| R-0 | source id not in the registry but served live (seed) | `unknown` |
| R-1 | I1 status `refused` (registry do-not-ingest decision) | `restricted` |
| R-2 | captured upstream item terms restrict redistribution, commercial use, derivatives or use outside the publisher (regex over `licence_verbatim`, each hit read by hand) | `restricted` ("Demo purposes only" → `unknown`) |
| R-3 | registry `redistributable = false` | `restricted` |
| R-4 | a Part VIII hazard in the raw bytes that no field-drop can cure (P8-1 audit material, P8-2 released records, P8-4 private registrants) | `restricted` |
| R-5 | no `[rights]` block (UNDETERMINED; SIG-LIC-004 fails closed) | `link-only` if custody `LINK`, else `unknown` |
| R-6 | custody `LINK` | `link-only` |
| R-7 | custody `DERIVE` or SPDX `LicenseRef-DerivedFacts-Citations` (recorded decision: upstream bytes never re-hosted) | `derived-only` |
| R-8 | `LicenseRef-PublicRecord-FactualCompilation`: the licence covers facts, not the bytes, and state/municipal copyright varies | `derived-only` |
| R-9 | `LicenseRef-OperatorAccepted-DBRight`: a verbatim copy is the whole-database reutilisation the sui generis right targets | `derived-only` |
| R-10 | packet-limited sources: `eff_data_driven` (aggregate only), `raa_prefectures` (ODbL covers the index, not the arrêté PDFs) | `derived-only` |
| R-11 | CC0 recorded by SIG as a *label* (13 rows: municipal public-record argument or a no-warranty disclaimer; NEW-7) | `derived-only` |
| R-12 | US federal work (17 U.S.C. §105), or an explicit upstream open licence or dedication (CC0/PD/PDDL stated upstream, CC-BY*, CC-BY-SA*, ODbL, OGL-UK/Canada, Ottawa/Peel ODL, Licence Ouverte, MIT/AGPL for code) | `raw-ok` (attribution and share-alike noted; P8 field screens still apply) |

**Qualifications on the lanes.**
- **`raw-ok` means the licence permits redistribution, not that bytes may ship verbatim.**
  - Every `raw-ok` source still passes the P8 byte screen (§9).
  - Where that screen removes fields, the publishable artefact is a **redacted re-serialisation** recorded as a
    new capture (SIG-PUB-015), never the stored bytes.
  - `raw-ok` sources whose custody is `REFERENCE` also need a recorded custody-posture change (SIG-ONTO-007)
    before SIG serves their bytes. The CSV notes each one.
- **The attribution verdict (`current_attribution_ok`)** is read in this order:
  - the per-row `rights_attribution` / `rights_attribution_required` / `rights_terms_url` in the public `sites.csv`;
  - else the live API obligation;
  - else inference from the per-SPDX rights dedupe (`db/src/db/claim_sink.py:949-973`, J1 NEW-2). These rows are
    labelled "inference" in the CSV.
  - The `/map/` island attributes every compartment generically (E1-12), so **no** source is correctly
    attributed on the map surface. That applies to all rows and is not repeated per row.
- **Raw-bytes estimates.** Stored bytes come from the OCFL join. Per-snapshot estimates for site sources are
  rows × 150–700 B, from the interquartile-to-high range of the 25 registry sources with stored captures
  (median 250 B/row). They are inference.

**Web reads (logged per P15; prices change, so re-verify before committing money).**

| id | tool | query / URL | time (UTC) | kept |
|---|---|---|---|---|
| WQ1 | WebFetch | cloud.google.com/storage/pricing | 17:39:38 | 0 (page truncated) |
| WQ2 | WebFetch | developers.cloudflare.com/r2/pricing/ | 17:39:38 | R2 prices (primary) |
| WQ3 | WebSearch | "Google Cloud Storage internet data transfer pricing per GB 0-1 TB North America premium tier 2026" | ~17:40 | nops.io, eon.io summaries (secondary) |
| WQ4 | WebFetch | cloud.google.com/cdn/pricing | ~17:40 | 0 (truncated) |
| WQ5 | WebFetch | help.zenodo.org/docs/deposit/upload-files/ | ~17:40 | 0 (404) |
| WQ6 | WebFetch | cloud.google.com/vpc/network-pricing | ~17:41 | 0 (truncated) |
| WQ7 | WebSearch | "Cloud CDN pricing cache egress per GB North America \"cache fill\" 2026" | ~17:41 | blog.cdnsun.com, egresscost.com (secondary) |
| WQ8 | WebSearch | "Zenodo maximum file size per record 50 GB 100 files limit" | ~17:41 | support.zenodo.org FAQ |

---

## 2. Lane definitions (for J3's UI and export gating)

| lane | may publish | never publish | UI treatment (PC-9, J2) |
|---|---|---|---|
| `raw-ok` | derived rows + the original bytes (or a P8-redacted re-serialisation) with the required notice, and share-alike terms where they apply | bytes failing the P8 screen | "Download original" + hash, size, retrieved_at, upstream URL |
| `derived-only` | SIG's derived rows/claims with per-row rights; capture **metadata** (hash, size, time, upstream URL) | the captured bytes | "View at source" link; no byte download |
| `link-only` | citation and capture status | derived rows beyond the citation; bytes | link only |
| `restricted` | existence, lane, and reason class; aggregates where a recorded decision allows them | bytes; for NEW-1 rows, arguably the derived rows too (Q-J4-2) | "Not redistributable — reason: terms / Part VIII" |
| `unknown` | nothing beyond registry metadata | everything else | "Rights not reviewed" |

---

## 3. Counts

### 3.1 In-scope sources (237) by recorded licence × lane

| licence (registry SPDX) | raw-ok | derived-only | restricted | unknown |
|---|---|---|---|---|
| LicenseRef-OperatorAccepted-DBRight | — | 90 | 3 (NEW-1) | 1 (`camreg_und_023`) |
| LicenseRef-PublicRecord-FactualCompilation | — | 57 | 3 (NEW-1) | — |
| CC0-1.0 | 20 | 12 (SIG labels, NEW-7) | 1 (`agency_audit_export`) | — |
| ODbL-1.0 | 11 | 1 (`raa_prefectures`) | — | — |
| LicenseRef-DerivedFacts-Citations | — | 11 | 1 (`declarationcamera_be`) | — |
| CC-BY-4.0 | 7 | 1 (`eff_data_driven`) | — | — |
| OGL-3.0 | 6 | — | — | — |
| CC-BY-SA-4.0 | 1 (`camreg_puertogaitan_co`) | — | 1 (`eyes_on_flock`) | — |
| MIT 2 · AGPL-3.0 1 · LicenceOuverte-2.0 1 · CC-BY-SA-2.0 1 · OGL-Canada-2.0 1 · CC-BY-3.0 1 · Ottawa ODL 1 · Peel ODL 1 | 9 | — | — | — |
| LicenseRef-MuckRock-API-ToS | — | — | 1 | — |
| **total** | **54** | **172** | **10** | **1** |

- Share-alike applies to 15 in-scope sources: 12 ODbL, 2 CC-BY-SA-4.0 and 1 CC-BY-SA-2.0.
- **The 42 live `raw-ok` sources:**
  - Legislation and procurement: federal works (usaspending, sam_gov, fbi_cde, congress_gov); openstates; ted_eu;
    decp_fr; the 4 city procurement portals.
  - Federal oversight reports: gao, dhs_oig, dhs_fusion, fema_hsgp.
  - EFF Atlas (CC-BY-4.0, with the SC-09 third-party caveat).
  - `ok_statute`.
  - 3 DOT feeds (IA, IL, DC).
  - 19 camera registries with an explicit upstream open licence (including Rochester PD's ODbL).
  - `osm_overpass`, `osm_element_history`, `camreg_osm_surveillance`.
- **The 12 permitted-but-not-ingested `raw-ok` rows** are the OSM policy/reference corpus, code repositories
  (`deflock_repo` MIT, `deflock_app_repo` AGPL, `flock_finder` MIT), `gleif`, `wikidata_sparql` and
  `sous_surveillance_osm_import`.

### 3.2 Public download rows by lane (release `sig-2026-09-27-ce480ab1`, 236,994 site rows)

| lane of the row's source | rows | note |
|---|---|---|
| raw-ok | 166,990 | 154,528 from `camreg_osm_surveillance` (ODbL) |
| derived-only | 64,737 | 54 public-record sources 33,853 · 89 DB-right sources 20,877 · 5 SIG-labelled CC0 DOT feeds 10,007 |
| restricted | **5,110** | NEW-1: Cal OES 4,342 · UKM 386 · Toronto `cotgeo` 336 · Keizer 25 · TRPA 15 · Ramallah 6 |
| unknown | 157 | `camreg_und_023` ("Demo purposes only") |

### 3.3 Gated and refused (cheap pass; 105 rows)

- 45 are `link-only` (custody `LINK`, no rights block) and 46 are `unknown` (no rights block).
- 8 are `restricted`:
  - `documentcloud` (released-record PII);
  - `sm_alpr` and `eyes_off_eugene` (search-audit archives);
  - 5 rows whose rights block records `redistributable = false`: `dot_511_tx` (personal-account item) and
    `camreg_edmonton_ab`, `camreg_bellevue_wa`, `camreg_qldc_au`, `camreg_hk_hk`.
- 2 are `raw-ok` on licence only, and stay not permitted: `panopti_ca` and `private_eyes` (MIT).
- The 4 refused rows are `restricted`, including `wired_shotspotter_leak` under the leak-provenance veto
  (SIG-PUB-005).

---

## 4. Determinations that need attention

1. **Captured terms forbid what SIG publishes (NEW-1, S1).** Seven registry sources:
   - **Ramallah:** "Redistribution, reproduction, or modification of the data without prior written permission …
     is prohibited".
   - **UKM Malaysia:** "for UKM security and JPP use only".
   - **Keizer, OR:** "Distribution, sale and/or resale is prohibited".
   - **TRPA:** "CC BY-NC".
   - **Cal OES:** ALERTCalifornia data under CC BY-NC-ND 4.0, "may not be … used to create derivative products".
   - **Toronto `cotgeo`:** "Cannot be re-sold. Resource provider must be contacted to get access".
   - **`camreg_und_023`:** "Demo purposes only".

   The registry was flipped under GL-GATE-07 with `redistributable = true`, and 5,267 rows are public. GL-GATE-07
   records acceptance of *database-right* risk; it does not record acceptance of express licence prohibitions
   (inference). J4 classes their raw bytes `restricted` and flags the derived rows for Q-J4-2.
2. **Compartment licence ≠ source licence (NEW-2, S2).**
   - The CC-BY-SA-4.0 `portal` compartment is described as "Eyes on Flock-derived", but holds 10,054 rows from
     9 CC0-registry sources plus Puerto Gaitán, and no Eyes on Flock rows.
   - `camreg_stalbert_ab` is recorded as DB-right but exported under the St Albert ODL.
   - Because of this, the per-source raw lane cannot be read off the compartment. J3 must key raw gating on the
     **source**, not the compartment.
3. **Licence labels versus upstream grants (NEW-7, S2).**
   - 13 CC0 rows are SIG labels (e.g. the agenda platforms; DOT feeds whose upstream text is only a no-warranty
     disclaimer). They sit in `derived-only` until reviewed.
   - Three rows are understated against their upstream licence: Vancouver and Peel declare "CC BY", and St Albert
     declares an ODL. A review could lift them to `raw-ok` (Q-J4-7).
   - `madada`'s notes say `redistributable=false` while its rights block says true.
4. **Part VIII overrides licence for three live or permitted sources** (the fourth overridden row,
   `declarationcamera_be`, is a private-registrant case, P8-4):
   - `eyes_on_flock`: CC-BY-SA would allow raw, but the capture holds 500 free-text search reasons.
   - `agency_audit_export`: audit CSVs.
   - `muckrock`: released records, plus `redistributable=false`.
5. **Seed fixtures served live (NEW-6).** `okc_council_statement`, `okc-contract-c241032` and `osm` are not in the registry, and
   `deflock` is gated with no rights block. The live API serves them with CC-BY-4.0/ODbL obligations, and
   `web/evidence.json` lists them. One of the ids is a police official's surname.

---

## 5. Attribution: required versus shipped

**What each licence family requires.** The CSV `attribution_required_text` gives the exact string per source.

| family | required | what SIG ships today (live-read) |
|---|---|---|
| CC-BY-4.0 / 3.0 | creator credit + licence link + change notice | ACT, Sioux Falls and Baltimore are correct. Iowa DOT, DC and Gold Coast say "DeFlock community map". The EFF Atlas in the API says "DeFlock community map". EFF Data Driven sharing edges say "© The SIG project — CC-BY-4.0". `LICENCES.json` calls all of `sig_graph` "© The SIG project" although it carries 5 third-party CC-BY sources. |
| CC-BY-SA-4.0 / 2.0 | credit + same-licence adaptations | Eyes on Flock (API): empty. Puerto Gaitán (50 rows): empty. IL DOT (3,000 rows): empty. |
| ODbL-1.0 | ODbL notice + licence reference; share-alike for derived databases | The OSM layer carries "© OpenStreetMap contributors, ODbL 1.0" with an empty `terms_url`, so it is partial. Rochester PD (177 rows) and the French prefectures (API) are **misattributed to OpenStreetMap**. |
| OGL-3.0 / OGL-Canada / Ottawa ODL / Peel ODL | the OGL attribution statement | Sheffield, Winnipeg and Ottawa are correct. Nottingham, York, Glasgow, North Ayrshire, Lambeth (1,368 rows) and Peel (37 rows) are **empty**. |
| Licence Ouverte 2.0 | producer + date of last update | `decp_fr`: partial (inference; sink-created rights rows carry no terms URL or date) |
| CC0 / US federal | nothing (courtesy credit) | the API carries its own text for `legistar`, `okcpd_policy` and `ok_statute`. `dot_511_ky`/`ut` rows claim attribution is required but carry none (partial). |
| PublicRecord / DB-right (SIG bases) | no licence notice; **SIG promises per-row source attribution** (`LICENCES.json`, SIG-EXPORT-006) | 61,603 rows are empty (J1 NEW-3). All 154 live sources fail SIG's own promise. |

**Census, 218 live sources:** y 33 · partial 14 · n 171.
- Attribution-licensed subset (27 sources): n 17 · partial 4 · y 6.
- Camera registries (166 sources): n 156 · y 9 · partial 1.

The root cause is the per-SPDX rights dedupe (J1). The added misattributions come from compartment-level defaults:
the `osm_physical` credit, the `sig_graph` "© The SIG project" credit, and the `sharing_edges` rights stamp.
**J3 must render attribution from the per-source registry text, never from the rights-record join.**

---

## 6. Volumes

**Current stores (live-read listings):**

| store | bytes | objects | notes |
|---|---|---|---|
| public bulk release | 1,048,876,904 (manifest) | 132 artifacts | osm_physical 562 MB · public_record 154 MB · web/ 145 MB (`research_queue.json` alone 144 MB) · operator_accepted 86 MB · portal 51 MB. By format: geojson 193 MB, jsonld 192 MB, jsonl 186 MB, json 145 MB, sqlite 116 MB, csv 114 MB, pmtiles 66 MB, parquet 36 MB |
| restricted release history | 2,957,881,480 | 3 snapshots (09-24 ×2, 09-27) | the only prior releases (J1 NEW-5) |
| OCFL raw captures | 73,432,699 capture bytes (79,411,154 incl. inventories) | 350 objects | 45 sources; by lane: raw-ok 34,949,343 B (35 sources) · derived-only 21,876,516 B (9) · restricted 16,498,233 B (1) |
| run rows | 7,023,338 | 387 rows, 208 sources | plus probes 48,099 B / 60 objects |
| P32.13 release tree (built, undeployed) | ≈2.0 GB | 475,112 files | DEFERRALS.md:583 |

**Per source** (CSV `raw_bytes_estimate`, `derived_rows`):
- **Largest stored raw captures:**
  - `eyes_on_flock` 16.5 MB (one weekly snapshot);
  - `ccops_oakland` 14.9 MB (report PDFs);
  - `congress_gov` 13.4 MB (78 of 230 captures);
  - `camreg_osm_surveillance` 6.4 MB (30 of 158 slices).
- **Derived site slices:** median 137 rows ≈ 0.55 MB across all 7 formats (≈ 4 KB/row) or ≈ 66 KB as CSV; p90
  1,128 rows ≈ 4.5 MB; max 154,528 rows (562 MB).
- **Non-site sources** (legislation, agendas, procurement: 40 sources) have no bulk-file presence at all. Their
  claims reach the public only through the API, and the CSV gives max-per-run claim counts.

**Expected growth** (inference, labelled):
- *Derived release size.* It scales with rows at ≈ 3.8 KB/row across all formats, excluding `web/`. Each
  +100,000 site rows adds ≈ +0.4 GB per release. Stream I intends to add sources, so doubling the rows reaches
  §38.5's "2 GB export".
- *Raw captures.*
  - Observed: +73.4 MB in the 7 days 2026-09-24…09-30. That includes a 250-capture, 18.4 MB backfill on 09-29;
    retention has been 100% since 09-25.
  - If every live source kept every run (monthly camera-registry sweeps ≈ 46–92 MB including the OSM layer;
    weekly Eyes on Flock ≈ 66 MB/month; congress.gov ≈ 10 MB/run; agenda indexes unknown), raw growth is ≈
    **0.2–1.5 GB/month** before content-address dedup.
- *Release history.* If published immutably: +1.05 GB per release, ≈ 55 GB/year at a weekly cadence.

---

## 7. Cost model

**Prices** (web-read 2026-09-30; GCS and CDN figures are from secondary summaries WQ3/WQ7, so confirm on the
billing console):
- **GCS internet egress, Premium tier, North America:** $0.12/GB for 0–1 TB, $0.11/GB for 1–10 TB, $0.08/GB above
  10 TB.
- **Cloud CDN cache egress (NA):** $0.08/GB for the first 10 TB, then $0.055/GB to 150 TB. Cache fill is
  $0.01/GB; lookups are $0.0075 per 10k.
- **Cloudflare R2** (primary, WQ2): egress free; storage $0.015/GB-month; Class B $0.36 per million; free tier
  10 GB-month and 10M Class B.
- **Zenodo:** free, 50 GB and 100 files per record (WQ8).
- **GCS Standard storage:** ≈ $0.02/GB-month (inference, not verified this row). Storage is immaterial at SIG's
  size.

**Unit costs on today's setup** (GCS direct, first tier):

| unit | size | per download | notes |
|---|---|---|---|
| (a) derived per-source slice | median 0.55 MB · p90 4.5 MB · max 562 MB | $0.00007 · $0.0005 · $0.067 | CSV-only is ≈ 8× smaller |
| (b) raw capture (raw-ok set) | ≈ 35 MB total today; 0.1–16 MB per capture | ≤ $0.004 for the whole raw-ok archive | raw is small; cost risk is negligible, rights and Part VIII risk are not |
| (c) full release bundle | 1.05 GB | **$0.126** (CDN $0.084 · R2 $0) | parquet + CSV only ≈ 150 MB → $0.018 |

**Monthly scenarios** (bundle + slices + raw; GiB/GB conflated; inference):

| scenario | traffic | GB/month | GCS direct | Cloud CDN | R2 |
|---|---|---|---|---|---|
| low | 100 bundles, 2k slices, 500 raw | ≈ 107 | ≈ $13 | ≈ $9 | ≈ $0 |
| medium | 1k bundles, 20k slices, 5k raw | ≈ 1,066 | ≈ $128 | ≈ $85 | ≈ $0 |
| §38.5-scale | 5k bundles, 100k slices, 20k raw | ≈ 5,325 | ≈ $596 | ≈ $426 | ≈ $0 |
| abuse | one scraper looping the bundle at 1 TB/day | ≈ 30,720 | **≈ $2,775** | ≈ $1,945 | ≈ $0 (Class B ops ≪ free tier) |

§38.5's point holds: **egress, not storage, is the cost**, and today nothing caps it. The public bucket is served
straight from `storage.googleapis.com`: no CDN, no backend bucket, anonymously listable (J1 NEW-1/12).

**Cost controls** (recommendation; operator decides Q-J4-3):

1. **Zero-egress distribution host.** Put a zero-egress mirror in front of downloads: R2, through the existing
   unused `exports/src/exports/push.py` S3/R2 path. Source Cooperative or AWS Open Data sponsorship are the
   alternatives (J2). GCS stays the origin of record. This is the only control that makes the abuse row cheap,
   and it is what SIG-EXPORT-008 asks for.
2. **Rule out requester-pays.** It blocks anonymous download (J2 Q094) and so contradicts the transparency goal.
3. **Make the bucket non-listable.** Publish a signed catalog (`catalog.json` / `manifest.json`) instead of relying
   on bucket listing, and use immutable versioned paths (`/releases/<id>/…`) with long `Cache-Control`, so a CDN
   or R2 can cache them.
4. **Compact formats first.** Default downloads should be parquet + `csv.gz` per compartment. Ship
   geojson/jsonld/jsonl compressed or on demand. Keep `web/research_queue.json` (144 MB) out of downloads or gzip
   it. Cap files at ≈ 250 MB (split `osm_physical`).
5. **Offload big and immutable artifacts.**
   - *Zenodo:* a version DOI per release for eligible compartments (≤ 50 GB/record). This is gated by the
     withdrawal decision (Q-J4-6).
   - *Torrent:* web-seeded from R2 for artifacts over 100 MB (SIG-EXPORT-009).
6. **Throttling:** a per-IP concurrency cap (Wikimedia uses 3, per J2) and WAF rate limits on the R2 or CDN
   front. Rate limits on the load balancer do not apply while downloads bypass it.
7. **Kill switch:** a billing budget alert plus an egress-bytes alert (G1 QA-10), with a documented step (point
   the download links at the mirror only, or make the bucket private).
8. **Raw captures:** serve per capture by content address, with a size cap. No "all raw" zip except for the
   `raw-ok` set, which is ≈ 35 MB today.

---

## 8. Ingestion logs: what may be public

**Field verdicts.** P = publish as is; T = publish after the named transform; N = never.

| store | field | verdict |
|---|---|---|
| GCS run row | `ingest_run_id`, `kind`, `mode`, `outcome`, `exit_code`, `claims_added`, `duration_seconds`, `started_at`, `source` | P |
| | `capture_digests[]` | P (hash). Link to bytes only for `raw-ok` after the P8 screen. |
| | `detail`, `refusal_reason` | T: S-4 error class + count. Today: 45 non-empty `detail` values, including a DB driver error, a named DB check constraint, filesystem errors and replay notes. |
| `fetch_record` | `connector`, `logical_run` (as id), `fetches`, `claim_count`, `quota_reached`, `budget_reached`, `sweep_*`, `content_drift`, `politeness_refusal` | P |
| | `robots_decisions[{host,outcome,robots_url,status}]` (2,831) | P, aggregated per host |
| | `robots_disregarded[{host,url,verdict}]` (234: primegov 220, escribe 12, ok_statute 2) | operator decision, Q-J4-4 (recommend P as host + count + GL-GATE-08 reference) |
| | `refusals[{detail,id,observed_at,refusal,url}]` (378) | T: class + host + time. Drop `detail` (it embeds the crawler UA/contact string). |
| | `rate_limit_events[]` (13) | T: status + wait + host |
| | `disappearances[{artifact_id,failing_status,observed_at}]` (378) | P, subject to withdrawal (S-9) |
| | `document_outcomes[{url,matched_terms,outcome,platform,tenant_id,capture_digest,…}]` (8,043) | T: outcome and matched-term counts. URL only for documents whose claims passed the publication gate (S-6). Tenant id P. |
| | `urls`, `status_codes`, `byte_counts` (always empty today; J1 NEW-6) | T when filled: S-1/S-6 on URLs; status and bytes P |
| DB `ingest_run` | `run_id`, connector name/version, ruleset/vocab versions, `input_digests`, `started_at` | P |
| | `code_commit` | Q-J4-5 (the repo is private, E1-21) |
| | `parameters.run_record_uri` | N (internal `gs://…-sig-restricted` path); opaque id instead |
| | `environment` | N |
| DB `ingest_run_completion` | `status`, `finished_at`, `claims_considered` / `inserted` / `duplicate`, `recorded_at` | P. These are already granted to `sig_read_public`. |
| | `detail` | T (S-4) |
| DB `ingest_run_capture` | `state`, `capture_digest`, `media_type`, `byte_size`, `retrieved_at` (full timestamp), `records` | P |
| | `source_uri` | T (S-1, S-6) |
| | OCFL ids | opaque |
| DB `evidence_capture` | `capture_classification` (synthetic vs actual, J1 NEW-4), `http_status`, `redaction_method` / `redaction_version`, `storage_tier` | P |
| OCFL `metadata.json` | `digest`, `byte_size`, `media_type`, `retrieved_at` | P |
| | `source_uri` | T |
| | `headers` (stored in full, `capture_ocfl.py:107-109`) | T: allowlist (S-14) |
| `assertion_quarantine` | counts by reason class | T. `payload` is N. |
| `rights_decision` | `basis`, `decided_at`, reviewer **role**, `terms_url` | P. `review_packet` text needs a decision (packets live in the private repo). |
| `evidence_access_log` (requester, purpose) | — | **N** (SIG-EVID-012). Revoke the blanket grant (J1 NEW-9). |
| `ops/probes` | — | T: uptime/latency aggregates only; no probe targets. |
| Cloud Logging | — | N. Raw logs hold `gs://` and container paths (J1). |

**Scrub rules.**

- **S-1 Credentials — fail closed.** Strip query parameters matching
  `(api_?key|apikey|key|token|access_token|auth|sig|signature|secret|password|session|jwt|code)` from every URL.
  Drop `Authorization`, `X-Api-Key`, `Cookie`, `Set-Cookie` and `Proxy-Authorization`. **Block the publish** if any
  value looks like a secret (`eyJ…` JWT, `AKIA…`, ≥ 32 hex characters after `key=`, `Bearer …`).
  - Baseline: 0 credential query parameters, 0 bearer tokens and 0 passwords in 387 run rows.
  - Policy already keeps keys in headers (`live_targets.toml:434-436`), but no generic scrubber exists.
- **S-2 Internal locations.** Replace `gs://…-sig-restricted/…`, container and home paths, service-account
  emails, instance names and job-execution names with opaque ids. Baseline: none in the run rows (0 matches);
  present in Cloud Logging and `ingest_run.parameters` (J1).
- **S-3 Environment.** Never publish `ingest_run.environment`, environment variables or runtime configuration.
- **S-4 Error text → closed vocabulary.** Examples: `db_connection_lost`, `storage_error`, `read_timeout`,
  `constraint_violation`, `robots_unavailable`, `robots_disallow`, `politeness_refusal`, `quota_reached`,
  `content_drift`, `disappearance`, `upstream_http_<code>`. Publish class + count, never exception text, SQL or
  constraint names.
- **S-5 IP addresses.** Drop any IP. Baseline: 0. The 72 dotted-quad hits in refusal details were RFC 9309 section
  numbers.
- **S-6 Upstream URLs.** The host is always publishable. The full URL (after S-1) is publishable only if the
  source's lane is `raw-ok` or `derived-only` **and** the document or record passed the publication gate.
  Otherwise publish host + a hash of the path. Filenames of agenda and records documents can carry person names.
- **S-7 Personal data.** No person names, emails or phone numbers in any log field. Reviewers appear by role only
  (Part VIII §0.7). No requester identity. The crawler contact is the project's, not a person's.
- **S-8 Free text from records.** No excerpts, search reasons or snippets (SIG-PUB-014a). `matched_terms` are
  vocabulary ids and are OK.
- **S-9 Withdrawal.** Log rows that reference a withdrawn claim, capture or artifact show a tombstone id
  (`publication_disposition` + `apply_withdrawals`).
- **S-10 Timestamps.** Full ISO-8601 UTC everywhere. Fix the date-only `retrieved_at` (J1).
- **S-11 Gated and refused sources.** Show registry status and the reason class, never runs or probe details.
- **S-12 Build-time, explicit columns.** The log surface is emitted by the export from explicit-column views. Never
  serve it live through the blanket `sig_read_public` grant (J1 NEW-9).
- **S-13 Robots.** Disclosure of `robots_disregarded` per Q-J4-4. Obeyed, disallowed and unavailable outcomes are
  always publishable.
- **S-14 Capture headers.** Allowlist `Content-Type`, `Content-Length`, `ETag`, `Last-Modified` and `Date`. Drop
  cookies, `Server`, `Via`, `X-*`, `CF-*` and request ids.

The CSV `log_exposure_ok` column sets the level per source:
- 197 sources: `y-scrubbed`.
- 7: `y-scrubbed` with URLs only for gate-passed documents.
- 3: `y-scrubbed` pending the robots-disclosure decision.
- 1: counts only (`eyes_on_flock`).
- 137: nothing to show.

---

## 9. Part VIII rules by source class

| rule | class and sources | what raw bytes and logs could expose | rule |
|---|---|---|---|
| **P8-1** | Audit and search-audit material: `eyes_on_flock` (`summary.top_search_reasons`, 500 free-text keys; heuristic 7 case-number-like and 3 plate-like tokens), `agency_audit_export`, gated `eyes_off_eugene` and `sm_alpr`, the HIBF corpora, and the `eff_data_driven` raw release | search reasons, plates, operator identifiers; joinable to rosters (SIG-PUB-003a/b) | **Raw never public.** Keep it in the restricted/sealed tier. Publish institutional aggregates only (§43.6). Hash operator ids at ingest. "Already public" is no justification (SIG-PUB-003c). Run logs: counts only. |
| **P8-2** | Records and documents: `muckrock`, `documentcloud`, the `ccops_*` reports, OKC documents, `raa_prefectures` arrêtés (they name applicants; inference), `pathways_*`, `madada` request text, `eff_atlas` free-text `Summary` | names of private persons, officers, complainants; personal data in free text | No re-hosting. Link upstream. Every excerpt passes the SIG-PUB-014a screen, and redaction is a new capture (SIG-PUB-015/016). Names only through §43.4 (five prongs + two reviewers). Jurisdiction-conditional for EU/FR sources (SIG-PUB-017). |
| **P8-3** | Agenda and legislative indexes: `legistar`, `primegov`, `escribe`, `civicclerk`, `okc_council` | matter and item titles naming private persons (claims, appointments, public comment) | Raw JSON is never republished verbatim. Derived facts + upstream link. Legislators named as bill sponsors (`openstates`, `congress_gov`) are official conduct, so those raw bytes stay `raw-ok`. |
| **P8-4** | Private-registrant programs: `declarationcamera_be`, plus 3 non-target layers already enumerated with registrant names, addresses and phones (`camera_registry_targets.toml:3915,4221,4383`) | households; C3 | Never captured or published; no location (SIG-PUB-004 C3). Keep the existing exclusions. |
| **P8-5** | Camera registries (ArcGIS/Socrata; `outFields=*`, `dot_511.py:132`) | editor-tracking usernames (`created_user`/`last_edited_user` observed on `camreg_nola_la`), contact or owner fields; exact coordinates where the derived layer reduced precision | Publish raw only as a **field-allowlisted re-serialisation** (id, geometry, label, type, status, agency, install date) recorded as a redacted capture. A source with any non-C1 asset (SIG-PUB-004/005) gets no raw download, because raw would undo the precision reduction. |
| **P8-6** | Procurement: `sam_gov` (contracting-officer contacts; inference from the API schema), `usaspending` (recipients who are natural persons), `ted_eu` (contact points), `decp_fr` (sole-trader holders under GDPR), `procportal_*` and `okc_procurement` (vendor contacts) | names, emails and phones of natural persons | Drop natural-person contact fields and sole-trader identifiers before any raw publication. Jurisdiction-conditional (SIG-PUB-017). |
| **P8-7** | DOT 511 feeds | raw JSON links live camera imagery (plates and faces in view) | Never proxy, capture or thumbnail imagery. Upstream links are optional. |
| **P8-8** | OSM-derived: `osm_overpass` (`out meta`), `osm_element_history`, `osm_replication`, `sous_surveillance_osm_import`, `camreg_osm_surveillance` | mapper `user`/`uid` (SIG-INGEST-045e: MUST NOT be stored or exposed) | Strip before capture: query `out tags center` plus version-only metadata, or scrub pre-OCFL (NEW-4). Any raw re-serialisation drops `user`/`uid` and keeps `changeset`. |
| **P8-9** | Seed and fixture material: `okc_council_statement`, `okc-contract-c241032`, `osm`, `deflock` (NEW-6) | a person-named source id; unreviewed claims | Rename to institutional ids. Seeded claims pass rights + naming review or leave the public spine. |

The CSV column `part_viii_flags` carries the class per source. 34 in-scope sources carry a substantive flag; another
19 carry only the ArcGIS field screen and 12 only the DOT imagery rule.

---

## 10. Decisions the operator must make (feed Q-22)

| id | question | recommendation |
|---|---|---|
| **Q-J4-1** (Q-22a) | Publish raw captured bytes where the licence permits? | **Yes, for `raw-ok` sources only, after the P8 byte screen.** Serve redacted re-serialisations for P8-5/6/8. Everything else shows hash, size, time and upstream link. Start with the 35 `raw-ok` sources that have stored bytes (≈ 35 MB). |
| **Q-J4-2** | The NEW-1 sources (5,267 public rows whose captured terms forbid redistribution, NC/ND, or say demo): withdraw from public downloads pending HG-03 re-review, or record an explicit acceptance of express-term risk? | Withdraw in the first Round-11 wave and re-review. GL-GATE-07 accepted DB-right risk, not these terms. |
| **Q-J4-3** (Q-10) | Distribution host and egress ceiling | An R2 (or AWS ODP / Source Cooperative) mirror, a non-listable bucket, compact default formats, a budget + egress alert with a kill switch, and a monthly egress ceiling (e.g. $50). |
| **Q-J4-4** (Q-22b) | Publish scrubbed run logs, including the 234 `robots_disregarded` events (GL-GATE-08)? | Yes to scrubbed logs (S-1…S-14). Disclose robots disregard as host + count + policy reference, because hiding it would misstate conduct. The risk is vendor blocking. |
| **Q-J4-5** | Pinned connector commits in public logs, given the repo is private | Publish connector version + commit hash now. Decide separately whether connector definitions become public (E1-21). |
| **Q-J4-6** | Zenodo/DOI deposits of release bundles (irreversible), and which compartments | Only the openly licensed compartments (CC-BY/CC-BY-SA/ODbL/OGL/ODL), and only after the attribution fixes (NEW-3). Never `operator_accepted` or `public_record`. |
| **Q-J4-7** | Accept J4's `derived-only` default for the 13 SIG-labelled CC0 rows and the 147 factual-compilation/DB-right rows, or commission rights review to lift sources (Vancouver and Peel "CC BY", St Albert ODL first)? | Accept the default and review on request. |
| **Q-J4-8** | Publish prior releases (restricted 09-24 snapshots) as immutable public history? | Yes, but only after the NEW-1 removals and attribution fixes, since they carry the same defects. |

---

## 11. Findings (`findings/incoming/J4.csv`)

| id | title | sev |
|---|---|---|
| NEW-1 | Six live registry sources whose captured item terms forbid redistribution, commercial use or derivatives are recorded `redistributable=true` and published (5,110 rows), plus one "Demo purposes only" source (157 rows) | S1 |
| NEW-2 | The CC-BY-SA-4.0 `portal` compartment, described as "Eyes on Flock-derived", holds 10,054 rows from 9 CC0 sources and 1 CC-BY-SA source and no Eyes on Flock data | S2 |
| NEW-3 | Attribution census: 21 of 27 attribution-licensed live sources fail it or meet it only partly. New misattributions: Rochester PD → OSM, French prefectures → OSM, EFF Data Driven edges → "© The SIG project", Eyes on Flock empty | S1 |
| NEW-4 | Raw OCFL captures keep what ingest discards: OSM `user`/`uid` (SIG-INGEST-045e), Eyes on Flock free-text search reasons, all ArcGIS attributes | S2 (S0 if raw ships unscreened) |
| NEW-5 | Only 349 of 6,144 recorded capture digests have bytes. 163 of 208 run-row sources have no raw bytes to offer. | S2 |
| NEW-6 | The live API and `evidence.json` serve 4 seed fixture sources with no rights review, one named after a police official | S2 |
| NEW-7 | 13 CC0 rows are SIG labels, not upstream grants, and 4 rows disagree with the upstream licence SIG captured | S2 |

Related earlier findings, not re-raised here:
- J1 NEW-1 (downloads unlinked), NEW-2/3 (attribution root cause), NEW-4 (synthetic evidence), NEW-5 (as-of),
  NEW-9 (blanket grant), NEW-12 (no CDN);
- E1-11 (GL-GATE-07) and E1-12 (attribution);
- C3 NEW-1 (seed ids in `/v1/dossier`).

---

## 12. Caveats and limits

- **Licence evidence dates.** Upstream licence text comes from SIG's own sweep of 2026-09-18. Upstream terms may
  have changed since. Eight camera-registry targets did not join to a sweep record.
- **Field lists.** The ArcGIS items in the sweep carry no field lists, so editor and contact fields are confirmed
  only where Socrata columns were captured (1 source). The rest is inference.
- **Inferred API attributions.** For `ted_eu`, `decp_fr`, the DerivedFacts rows, `osm_overpass` and
  `osm_element_history`, the API attribution is inferred, not read.
- **Raw-byte estimates** for sources with no stored bytes are inference. The Eyes on Flock scan is heuristic
  (patterns only; no value was copied into any artifact).
- **Prices** for GCS and Cloud CDN come from secondary summaries because the primary pages truncated. R2 and Zenodo
  figures are from primary or official sources.
- **I1 local copies.** J4 used run rows and the Eyes on Flock response that I1 had already read under its own
  read-only mandate. J4 downloaded no restricted object (listings only), wrote nothing to production, and made no
  change to `sources.toml`.

## Appendix — reproduction

```
gcloud storage ls -l -r 'gs://zeta-medley-508121-u7-sig-restricted/evidence/**'
gcloud storage ls -l    'gs://zeta-medley-508121-u7-sig-restricted/ops/**'
gcloud storage du -s    gs://zeta-medley-508121-u7-sig-restricted/{exports,rollback,web,ops}/ gs://zeta-medley-508121-u7-sig-web
gcloud storage ls -l    'gs://zeta-medley-508121-u7-sig-public/**'
curl https://storage.googleapis.com/zeta-medley-508121-u7-sig-public/{manifest.json,LICENCES.json,web/evidence.json}
curl 'https://sig-api-e5ctyx36jq-uc.a.run.app/v1/search?q={flock,portland,seattle,oakland,paris}&limit=5'
curl 'https://sig-api-e5ctyx36jq-uc.a.run.app/v1/search?q={sheriff,frontex,prefecture,lyon,police}&limit=10'
```

Joins:
- OCFL object id `sig%3acapture%3a<multihash>` ↔ run-row `capture_digests`.
- `camera_registry_targets.toml` `url`/`layer_url` ↔ `catalog_sweep_2026-09-18_reviewed.json` `endpoint`.
- Public `sites.csv` grouped by `source_id` → rows and `rights_attribution`.
