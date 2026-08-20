# R3 — EFF Atlas of Surveillance, the EFF Data Library, and the accountability/incident layer

**Workstream:** R3
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (research agent R3)
**Outline sections covered:** §2 Layer D (EFF Atlas, EFF Data Driven / Data Driven 2, EFF Street-Level Surveillance), §2 Layer E (ACLU Get the Flock Out; the ALPR Accountability Atlas and ALPR Abuse Library moved to R2), §4 / §7 (technology taxonomy — the Atlas↔SLS crosswalk), §5 (organisation model), §5.3 (other global datasets), §10.1C (Phase 1C — EFF Atlas), §10.1G (Phase 1G — accountability events), §13 (PII, withdrawal, archival policy), §15.1 (local surveillance dossier — corrected), §15.4 (procurement / renewal watch), §19 (community contribution), §21 (priority source registry). **New source classes added that the outline does not contain:** CCOPS / surveillance-ordinance inventories, state-level ALPR reporting mandates, and academic FOIA data deposits.
**Outline questions answered:** Q6 (machine-readable interfaces beyond CSV), Q15 (licences — answered here for the Atlas, the EFF Data Library, Data Driven 1/2, Street-Level Surveillance, ACLU material, CCOPS disclosures and the Monahan deposit), Q31/Q32 (mirroring, correction and takedown — answered with the CalECPA and ACLU-stingray precedents), Q34 (can the Atlas consume deployment corrections)
**Confidence in this file overall:** high for F1.x–F3.27 and F3.30/F3.32 (all independently retrieved); **medium** for the agent-relayed lines in F3.29, F3.31 and F3.33, which are flagged inline and in OQ-R3-12
**Revision:** Part 1–2 (F1.x, F2.x) written 2026-08-20; **Part 3 completion pass (F3.x, Open questions, Spec requirements) appended 2026-08-20** after the original run was terminated mid-write

---

## Scope note and reading order

Everything below was retrieved live on 2026-08-20 unless a finding explicitly says
otherwise. Every URL recorded under **Evidence** is the URL that actually returned the
content described; where the outline's URL failed or redirected, both are recorded.

Findings are grouped:

- **F1.x** — EFF Atlas of Surveillance (site, CSV, vocabularies, methodology, license, API)
- **F2.x** — EFF Data Library (complete enumeration + retrievability)
- **F3.x** — EFF Data Driven / Data Driven 2 (the Vigilant/LEARN layer)
- **F4.x** — EFF Street-Level Surveillance taxonomy and the Atlas↔SLS crosswalk
- **F5.x** — ALPR Accountability Atlas (schema, epistemic vocabulary, API, license)
- **F6.x** — ALPR Abuse Library / Kansas Watch
- **F7.x** — ACLU (Get the Flock Out toolkit; cell-site simulator map)
- **F8.x** — CCOPS surveillance-ordinance inventories (**the largest outline gap**)
- **F9.x** — Adjacent sources the outline missed entirely
- Then: source-access matrix, open questions, `REQ-R3-nn` spec requirements.

---

# F1 — EFF Atlas of Surveillance

### F1.1 — The Atlas bulk CSV is at `/download.csv`, not the URL the Atlas's own map page advertises

**Claim:** The working bulk-download endpoint is `https://www.atlasofsurveillance.org/download.csv`; the URL linked from the Atlas's own map page (`/downloads/atlas-of-surveillance.csv`) returns HTTP 404.
**Status:** VERIFIED
**Evidence:**
- `https://www.atlasofsurveillance.org/download.csv` → HTTP 200, `content-type: text/csv`, 8,579,798 bytes, `content-disposition: attachment; filename="Atlas of Surveillance-20260820.csv"`.
- `https://atlasofsurveillance.org/downloads/atlas-of-surveillance.csv` (the `href` on `/atlas`, the map page, behind the words "download a CSV file containing all the data here") → HTTP 404, 12,871-byte HTML error page.
- The Data Library page (`/data-library`) links the correct `https://atlasofsurveillance.org/download.csv`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Pin the connector to `/download.csv`. Do not scrape the map page for the download link. Add a connector health check that fails loudly if the CSV endpoint stops returning `text/csv`.
**Outline delta:** EXTENDS §2 Layer D and §21 — the outline lists only the three human-facing pages and never names a data endpoint. It also never warns that Atlas's own advertised download link is broken.

---

### F1.2 — Atlas row count, column set, and update date

**Claim:** As of 2026-08-20 the Atlas CSV contains **15,185 rows** across **28 columns**, with a stated last-update date of **Aug 12, 2026**.
**Status:** VERIFIED
**Evidence:** `https://www.atlasofsurveillance.org/download.csv` parsed with `csv.DictReader` → 15,185 data rows. Header row, verbatim and in order:

```
AOSNUMBER, NEWAOSNUMBER (ORI9), City, County, State, Agency, Type of LEA, Summary,
Type of Juris, Technology, TECH ABV, Vendor,
Link 1, Link 1 Snapshot, Link 1 Source, Link 1 Type, Link 1 Date,
Link 2, Link 2 Snapshot, Link 2 Source, Link 2 Type, Link 2 Date,
Link 3, Link 3 Snapshot, Link 3 Source, Link 3 Type, Link 3 Date,
Other Links
```

`https://www.atlasofsurveillance.org/methodology` states verbatim: *"The Atlas of Surveillance data was last updated on Aug 12, 2026."* The same sentence appears on `/about`. `/about` also says: *"we have amassed more than 15,000 datapoints in 6,000-plus jurisdictions"*, and `/atlas` says *"Explore 15,000 datapoints"*.
**Retrieved:** 2026-08-20
**Implication for the spec:** 15,185 rows is the Phase-1C import volume. `AOSNUMBER` is unique across all 15,185 rows and is the stable natural key for an Atlas claim.
**Outline delta:** CONFIRMS §2 Layer D's "As of August 12, 2026" date — the outline's research pass was accurate and the Atlas has not been refreshed in the eight days since.

---

### F1.3 — Four declared columns are 100% empty in the public CSV

**Claim:** `TECH ABV`, `Link 1/2/3 Snapshot`, `Link 1/2/3 Type`, and `Other Links` appear in the header but contain **zero** non-blank values in all 15,185 rows.
**Status:** VERIFIED
**Evidence:** Per-column non-blank counts computed over the full CSV:

| Column | Non-blank | % |
|---|---:|---:|
| `Link 1` | 15,184 | 100.0% |
| `Link 1 Source` | 15,158 | 99.8% |
| `Link 1 Date` | 13,278 | 87.4% |
| `Link 2` | 7,551 | 49.7% |
| `Link 3` | 3,625 | 23.9% |
| `Summary` | 15,185 | 100.0% |
| `City` | 15,180 | 100.0% |
| `County` | 15,040 | 99.0% |
| `Vendor` | 7,972 | 52.5% |
| `TECH ABV` | **0** | 0% |
| `Link 1 Snapshot` | **0** | 0% |
| `Link 1 Type` | **0** | 0% |
| `Other Links` | **0** | 0% |

**Retrieved:** 2026-08-20
**Implication for the spec:** SIG cannot rely on Atlas for (a) archived snapshots of its own citations or (b) a source-type classification. SIG must do its own archival (§13.4, §10) and its own source-type labelling. Ingestion should assert-and-alert if these columns ever become populated (that would be a material upstream upgrade).
**Outline delta:** EXTENDS §2 Layer D — a materially important limitation the outline does not record. The outline says Atlas provides "a precedent for evidence-reviewed surveillance research"; in the *published* data the evidence-typing and archival fields are hollow.

---

### F1.4 — The canonical Atlas technology vocabulary is 12 categories; the CSV contains a 13th value that is a data-entry error

**Claim:** The Atlas's controlled technology vocabulary has exactly **12** members, confirmed independently by the search UI's filter slugs; the CSV contains a 13th spurious value (`FRT`, 6 rows) produced by column misalignment.
**Status:** VERIFIED
**Evidence:**

Value counts of the `Technology` column over all 15,185 rows, plus distinct `(State, Agency)` pairs per technology:

| Technology (verbatim) | Rows | Distinct agencies |
|---|---:|---:|
| Body-worn Cameras | 5,469 | 5,462 |
| Automated License Plate Readers | 4,145 | 4,133 |
| Drones | 1,828 | 1,828 |
| Third-party Investigative Platforms | 1,062 | 1,039 |
| Face Recognition | 980 | 957 |
| Camera Registry | 756 | 755 |
| Gunshot Detection | 248 | 248 |
| Real-Time Crime Center | 242 | 242 |
| Predictive Policing | 200 | 200 |
| Video Analytics | 85 | 85 |
| Cell-site Simulator | 83 | 83 |
| Fusion Center | 81 | 81 |
| **`FRT`** *(error)* | **6** | 6 |
| **Total** | **15,185** | |

The 12 canonical slugs are confirmed by the checkbox names in the search form at
`https://www.atlasofsurveillance.org/search`:

```
technologies[automated-license-plate-readers]
technologies[body-worn-cameras]
technologies[camera-registry]
technologies[cell-site-simulator]
technologies[drones]
technologies[face-recognition]
technologies[fusion-center]
technologies[gunshot-detection]
technologies[predictive-policing]
technologies[real-time-crime-center]
technologies[third-party-investigative-platforms]
technologies[video-analytics]
```

There is no `frt` filter. The 6 `FRT` rows also carry `Type of Juris = "Face Recognition"` and are the same 6 rows that produce the junk `State` values below — i.e. a shifted-column defect, not a real category.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's technology ontology needs exactly 12 Atlas source-vocabulary terms plus an explicit `ATLAS_MALFORMED` quarantine bucket. The mapping table required by §10.1C should be keyed on the **slug**, not the display label, because the display label is what drifts.
**Outline delta:** EXTENDS §10.1C. The outline asks for a mapping between "Atlas technology categories" and SIG's ontology but never enumerates them; this is the enumeration, with counts, plus the warning that one apparent category is a defect.

---

### F1.5 — A second, finer-grained technology/vendor vocabulary is hidden inside the `NEWAOSNUMBER (ORI9)` identifier

**Claim:** The last three characters of `NEWAOSNUMBER (ORI9)` encode a technology-or-product code that is **strictly finer** than the `Technology` column, and decodes to specific vendors for the two broadest categories.
**Status:** VERIFIED
**Evidence:** The identifier is `<ORI7 or agency code><counter><3-char code>`; all 15,185 values are distinct; 8,225 distinct 7-character prefixes. Cross-tabulating the 3-char suffix against `Technology` and `Vendor`:

| Suffix | Rows | Technology | Decoded vendor/product (from the `Vendor` column) |
|---|---:|---|---|
| `BWC` | 5,467 | Body-worn Cameras | (generic) |
| `LPR` | 4,144 | Automated License Plate Readers | (generic) |
| `UAV` | 1,827 | Drones | (generic) |
| `FRT` | 893 | Face Recognition | (generic; 538 blank vendor, 230 Idemia, 40 LACRIS, 39 Clearview AI, 19 DataWorks Plus) |
| `PCT` | 763 | Third-party Investigative Platforms | SoundThinking (CrimeTracer) — 762/763 |
| `0CR`…`9CR` | 756 | Camera Registry | (generic; leading digit is a per-agency dedup counter) |
| `GDT` | 248 | Gunshot Detection | (generic) |
| `TCC` | 241 | Real-Time Crime Center | (generic) |
| `ACC` | 206 | Third-party Investigative Platforms | LexisNexis / LexisNexis Risk Solutions (Accurint) — 206/206 |
| `RPO` | 200 | Predictive Policing | (generic) |
| `CSS` | 83 | Cell-site Simulator | (generic) |
| `0VA`…`9VA` | 85 | Video Analytics | (generic) |
| `0FC`…`9FC` | 81 | Fusion Center | (generic) |
| `TCV` | 29 | Face Recognition | Clearview AI — 29/29 |
| `IDM` | 27 | Face Recognition | Idemia — 27/27 |
| `PCL` | 25 | Third-party Investigative Platforms | Thomson Reuters (CLEAR) — 25/25 |
| `OXP` | 23 | Third-party Investigative Platforms | TransUnion (TLOxp) — 23/23 |
| `PPL` | 13 | Third-party Investigative Platforms | Penlink — 13/13 |
| `RIS` | 9 | Face Recognition | LACRIS — 9/9 |
| `DWP` | 8 | Face Recognition | DataWorks Plus — 8/8 |
| `KPN` | 7 | Third-party Investigative Platforms | Skopenow — 7/7 |
| `PCI` | 7 | Third-party Investigative Platforms | Chorus Intelligence — 7/7 |
| `PIP` | 5 | Third-party Investigative Platforms | Penlink / Whooster / LexisNexis (mixed) |
| `RGR` | 4 | Third-party Investigative Platforms | Peregrine — 4/4 |
| `LMN` | 3 | Face Recognition | LexisNexis — 3/3 |
| `HOO` | 3 | Third-party Investigative Platforms | Whooster — 3/3 |
| `TVS` | 3 | Face Recognition | Vigilant Solutions — 3/3 |
| `PSD` | 2 | Third-party Investigative Platforms | ShadowDragon — 2/2 |
| `DTM` | 2 | Third-party Investigative Platforms | Dataminr — 2/2 |
| `CAI` | 2 | Face Recognition | Clearview AI — 2/2 |
| `ECS` | 1 | Third-party Investigative Platforms | Echosec — 1/1 |
| `PNH` | 1 | Third-party Investigative Platforms | "Nighhawks" *(sic)* — 1/1 |
| `AVG` | 1 | Face Recognition | Avigilon |
| `BCI` | 1 | Face Recognition | ND Bureau of Criminal Investigation |
| `NXT` | 1 | Face Recognition | FACESNXT |
| `TOO` | 1 | Face Recognition | Oosto |
| `NAP`, `DMV` | 2 | Face Recognition | (blank vendor) |
| `000`, `100`, `201`, `400`, `876`, `0BW`, `BWT` | 9 | (malformed) | — |

**Retrieved:** 2026-08-20
**Implication for the spec:** The ORI9 suffix is a *free* second-order product signal. SIG should parse it into a `source_product_code` field on the Atlas claim, use it to disambiguate `Third-party Investigative Platforms` (which is otherwise a useless bucket spanning CrimeTracer, Accurint, CLEAR, TLOxp, Penlink, Skopenow, Peregrine, ShadowDragon, Dataminr, Echosec, Whooster, Chorus), and use it to resolve `Face Recognition` rows to a vendor even when `Vendor` is blank (538 of 980 FR rows have no vendor string).
**Outline delta:** EXTENDS §2 Layer D, §4.7, §8.3 — an entirely unrecorded structured signal. §4.7's "Atlas facial-recognition deployments" becomes far more usable once the suffix is parsed.

---

### F1.6 — `Type of Juris` and `Type of LEA` are free-text with long tails and known contamination

**Claim:** Neither jurisdiction-type nor agency-type is a clean controlled vocabulary; `Type of Juris` has 28 distinct values (including 6 rows contaminated with the value `Face Recognition`), `Type of LEA` has 55 distinct values with case/spelling duplicates.
**Status:** VERIFIED
**Evidence:**

**`Type of Juris` — complete value set with counts (28 distinct):**

```
10,749  Municipal          140  Tribal            6  Special District     2  Police
 3,226  County              97  Regional          6  Health System        2  Harbor
   438  University          46  Judicial District 6  Face Recognition*    2  Water District
   297  Statewide           43  Parish            5  Transit              1  Housing Authority
                            37  School District   5  Territory            1  Hospital
                            21  Federal           5  Railroad             1  Conservation
                            20  Airport           4  Port                 1  Forest
                            16  State             7  Parks                1  Multiple
```
`*` = column-shift defect (same 6 rows as `Technology = FRT`).

Note `Statewide` (297) and `State` (16) are semantic duplicates; `Parks` (7) vs `Forest`/`Conservation`; `Municipal` vs the two rows valued `Police`.

**`Type of LEA` — 55 distinct.** Head: `Police` 11,577; `Sheriff` 3,006; `State Police/Highway Patrol` 133; `District Attorney` 100; `Fusion Center` 88; `DMV` 36; `Prosecutor's Office` 32; `Parking Enforcement` 21; `Corrections` 18; `Court` 18; `Customs and Border Protection` 17; `Prosecutor` 13; `Park Rangers` 12; `Constables` 11; `State-Local Partnership` 10. Tail contains explicit duplicates that differ only in case/spelling: `DIstrict Attorney` (3) vs `District Attorney` (100); `State Police` (4) / `State police` (1) / `State Patrol` (1) vs `State Police/Highway Patrol` (133); `Parks` (4) vs `Park Rangers` (12) vs `Park Ranger` (1) vs `Rangers` (1); `Transit` (1) vs `Transit Police` (3); `Prosecutor` (13) vs `Prosecutor's Office` (32).

**`State` — 58 distinct**, i.e. 50 states + DC + PR + VI + GU + 4 junk values: `Police` (4), `Sheriff` (2), `NB` (2), `PS` (1).
**Retrieved:** 2026-08-20
**Implication for the spec:** Atlas org typing must go through a SIG-maintained normalization map with an explicit review queue, not a direct copy. §8.1 Organization typing cannot be sourced from Atlas verbatim. The junk `State` values must hard-fail geocoding rather than silently produce a null-state organization.
**Outline delta:** EXTENDS §6.1 and §10.1C — the outline treats Atlas as a clean seed ("Atlas should seed our agency/deployment layer"); it needs a normalization stage first.

---

### F1.7 — `Vendor` is free text with 346 distinct strings, multi-valued, and case-inconsistent

**Claim:** 7,972 of 15,185 rows (52.5%) have a vendor; those contain 346 distinct strings including comma-joined multi-vendor values and case variants of the same company.
**Status:** VERIFIED
**Evidence:** Top values: `Flock Safety` 2,746; `Axon` 899; `SoundThinking` 797; `DJI` 660; `Idemia` 257; `Motorola Solutions` 220; `CRIMEWATCH` 173; `WatchGuard` 162; `Fusus` 156; `LexisNexis` 137; `ShotSpotter` 124; `IBM` 98; `Wolfcom` 91; `Coreforce` 76; `LexisNexis Risk Solutions` 75; `Clearview AI` 70; `Motorola` 59; `Geolitica` 52; `LACRIS` 49; `ELSAG` 33; `BriefCam` 32; `Rekor Systems` 28; `DataWorks Plus` 27; `Vigilant Solutions` 127.

Observed defects: `ShotSpotter` (124) vs `Shotspotter` (10) vs `SoundThinking` (797) — three strings, one company through a rename; `WatchGuard` (162) vs `Watchguard` (14); `Motorola Solutions` (220) vs `Motorola` (59); `LexisNexis` (137) vs `LexisNexis Risk Solutions` (75); `Rekor Systems` (28) vs `Rekor` (6); `Chorus Intelligence` (6) vs `Chorus Intellegence` (1). Multi-valued cells appear as `"Autel, DJI"` (14), `"Flock Safety, Motorola Solutions"` (11), `"DJI, Autel Robotics"` (8), `"Vigilant Solutions, Flock Safety"` (5), `"Vigilant Solutions, Dataworks"` (1).
**Retrieved:** 2026-08-20
**Implication for the spec:** The Atlas connector must split on `,` into candidate vendor mentions, and vendor resolution must be alias-aware **and rename-aware over time** (ShotSpotter→SoundThinking is a corporate rename, so the two names are the same Vendor node at different validity intervals — exactly the §9.2 observation-time/validity-time distinction).
**Outline delta:** EXTENDS §8.2 and §6.1. The outline's vendor list (§4) assumes clean vendor identity; Atlas supplies 346 raw strings for roughly 60 real companies.

---

### F1.8 — Atlas evidence links: 26,304 URLs across 4,221 domains, dominated by DocumentCloud and MuckRock

**Claim:** Atlas rows carry 26,304 citation URLs; the single largest source domains are DocumentCloud (3,827), MuckRock (1,163), web.archive.org (839), and — significantly — `transparency.flocksafety.com` (504).
**Status:** VERIFIED
**Evidence:** Parsing `Link 1`/`Link 2`/`Link 3` from all rows: 26,304 http(s) URLs, 4,221 distinct netlocs. Top 20:

```
3827 www.documentcloud.org      407 www.mass.gov
1163 www.muckrock.com           405 www.michigan.gov
 838 web.archive.org            393 www.prnewswire.com
 822 www.facebook.com           387 github.com
 807 dronecenter.bard.edu       357 www.njoag.gov
 638 www.srtbwc.com             350 www.globenewswire.com
 561 www.google.com             342 governor.ohio.gov
 504 transparency.flocksafety.com  334 www.newsobserver.com
                                320 wrnjradio.com
                                261 www.ptb.illinois.gov
                                261 dps.mn.gov
                                258 www.doj.state.wi.us
```

Of the 387 GitHub links, **339** point to `https://github.com/mcclatchy-southeast/private_eyes` and 48 to `https://github.com/kevincollier/Stingray`. All 504 `transparency.flocksafety.com` links sit on `Automated License Plate Readers` rows, e.g. `https://transparency.flocksafety.com/euclid-oh-pd`, `.../alameda-ca-pd`, `.../atherton-ca-pd`.
**Retrieved:** 2026-08-20
**Implication for the spec:**
1. Atlas is a **ready-made agency→Flock-portal-slug crosswalk for 504 agencies**, joinable to SIG's Layer B without any new scraping. Extract it in Phase 1C and hand it to the Flock-portal connector as seed identity.
2. 4,990 of Atlas's links (DocumentCloud + MuckRock) are already primary-record handles — Phase 1C and Phase 1F share a join key.
3. Atlas retains 839 `web.archive.org` links even though the dedicated `Link N Snapshot` columns are empty — snapshots live inline in `Link N`, so the parser must detect Wayback URLs in the link fields and normalize them to `(original_url, snapshot_timestamp)`.
**Outline delta:** EXTENDS §2 Layer D, §10.1C, §10.1D, §10.1F. None of this cross-layer joinability is in the outline; it materially changes ingestion sequencing (Atlas should be imported *before or with* the Flock portal ecosystem, not after).

---

### F1.9 — The Atlas "not a complete inventory" statement, verbatim

**Claim:** The Atlas methodology page states its incompleteness explicitly, in language SIG's negative-claims doctrine can cite directly.
**Status:** VERIFIED
**Evidence:** `https://www.atlasofsurveillance.org/methodology`, section "The Limitations", verbatim:

> "Open-source intelligence and crowd-sourcing come with their limitations. First, the information is only as good as the source: sometimes government agencies withhold information and sometimes journalists misinterpret information. It's possible that while there is information about a technology being adopted, the technology was later abandoned, and no reporters wrote about it. With thousands of data points to go through, it is impossible to exhaustively fact-check each one, despite the multiple reviews by students and staff. In particular, documenting the use of face recognition has proven challenging because of the changing policy landscape that has resulted in local governments abruptly freezing or abolishing the use of biometric identification software.
>
> **The Atlas should not be interpreted as an inventory of every technology in use. It only represents what our team documented after a year and a half of research.**
>
> In short, the Atlas of Surveillance serves as a resource, a tool, and just one way to understand the growth of surveillance technology in our communities. We hope that it will be the starting point for many other research projects to come."

`/about` reinforces: *"Although we have amassed more than 15,000 datapoints in 6,000-plus jurisdictions, our research only reveals the tip of the iceberg…"*
And `/atlas` (map page): *"If an area has no markers, it may mean it hasn't been researched yet."*
**Retrieved:** 2026-08-20
**Implication for the spec:** §9.4 (negative claims) gets a concrete, quotable upstream basis. SIG must carry a per-source `completeness_claim` field whose Atlas value is `NOT_AN_INVENTORY`, and the UI must never render "not in Atlas" as "does not exist". The second EFF sentence — *"the technology was later abandoned, and no reporters wrote about it"* — is a direct statement that Atlas rows have **no end-date semantics**, which is exactly §19.12 ("installed is not active").
**Outline delta:** CONFIRMS §2 Layer D and §9.4, with the exact wording the outline paraphrased.

---

### F1.10 — Atlas rows carry no coordinates; the map is a third-party ArcGIS embed built by automated geocoding that EFF itself flags as error-prone

**Claim:** The CSV has no latitude/longitude columns; mapping is done downstream by an automated geocoder whose errors EFF publicly disclaims, and the map is served from arcgis.com.
**Status:** VERIFIED
**Evidence:** No coordinate columns in the 28-column header (F1.2). `/methodology` states verbatim: *"Please note that points are placed on the map using an automated system and, like all automated systems, it makes mistakes. However, those mapping errors do not impact the text search."* `/atlas` states: *"This map will serve content from arcgis.com, a third-party host… The map requires use of Javascript and is subject to the ArcGIS Privacy Policy."* `/about` credits *"Maps powered by Esri."*
**Retrieved:** 2026-08-20
**Implication for the spec:** Atlas contributes **organization-level** claims only — never a `PhysicalAsset` (§8.6) and never a coordinate. SIG must geocode from `City`/`County`/`State` itself and stamp the result with `geocode_method` + `geocode_confidence`. Do not attempt to scrape the Esri layer for coordinates: they are derived, disclaimed, and not EFF's data.
**Outline delta:** EXTENDS §8.5/§8.6 and §13.3 — the outline never says Atlas is coordinate-free, which is the single most important thing about how it slots into the model.

---

### F1.11 — Machine-readable interfaces beyond the CSV (answers Q6)

**Claim:** Beyond `/download.csv`, the Atlas exposes (a) server-side filter parameters on the CSV endpoint and (b) exactly one JSON endpoint, a location autocomplete. There is **no** general JSON/REST API, no GeoJSON, no sitemap of records, and no official code/data repository.
**Status:** VERIFIED
**Evidence:**
- **Filtered CSV — location:** `https://www.atlasofsurveillance.org/download.csv?location=Berkeley%2C+CA` → HTTP 200, 31,217 bytes, 56 data rows, identical 28-column header.
- **Filtered CSV — technology:** `https://www.atlasofsurveillance.org/download.csv?technologies%5Bcell-site-simulator%5D=on` → HTTP 200, 83 rows, all `Technology = Cell-site Simulator`. Parameter names match the search-form checkboxes in F1.4. A `sort` parameter also exists (`agency_asc`, `city_asc`, `county_asc`, `state_asc`, `technology_asc`, `vendor_asc`).
- **JSON endpoint:** `https://www.atlasofsurveillance.org/search-locations.json?term=berkeley` → HTTP 200, `application/json`, a flat array of location and agency strings:
  `["Berkeley, CA","Berkeley, IL","Berkeley, MO","Berkeley Heights, NJ",…,"Berkeley Police Department, CA","University of California Berkeley Police Department, CA"]`.
  Discovered from `data-source="/search-locations"` on `/search` plus `source: $(this).data('source') + '.json'` in `/assets/application/search-….js`.
- **No record JSON:** `https://www.atlasofsurveillance.org/search.json?...` returns `text/html` (the Rails HTML view), not JSON.
- **No robots-listed record sitemap; no map data endpoint.** `/assets/application/maps-….js` (682 bytes) contains no data URLs at all — it only toggles an iframe.
- **No official repo:** enumerated all 100 most-recently-updated repos in `https://api.github.com/orgs/EFForg/repos` — no Atlas repo (nearest relatives: `spot_the_surveillance`, `rayhunter`). GitHub code search for "atlas of surveillance" returns only third-party class projects.
- **Cache/versioning headers on `/download.csv`:** `cache-control: max-age=300, public, stale-while-revalidate=30`; `etag: W/"ee42384d49aaf750a3cb417cccd8f427"`; served via Fastly (`x-served-by: cache-nyc-…`); `content-disposition` filename embeds the request date (`Atlas of Surveillance-20260820.csv`), **not** the data date.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Answer to Q6: CSV plus server-side filters, plus one location-autocomplete JSON endpoint. Nothing else.** The connector should (1) poll the weak `ETag` on `/download.csv` to detect changes cheaply, (2) parallelize by `technologies[...]` when doing partial refreshes, (3) **not** trust the `content-disposition` date as a data version — parse `/methodology` for the "last updated on …" string and store that as the source's `data_as_of`, and (4) content-address each full snapshot (§10, Q25) because there is no upstream version identifier.
**Outline delta:** ANSWERS Q6 and EXTENDS §21. The outline assumed there might be "stable machine-readable interfaces beyond CSV"; there are two, both minor, and neither returns records as JSON.

---

### F1.12 — Atlas licence: CC BY 4.0, with a redistribution caveat that matters for imported third-party datasets

**Claim:** The Atlas is licensed CC BY 4.0 via EFF's site-wide copyright policy, but that policy explicitly excludes material not original to EFF — which covers a large share of the Atlas, because much of it is aggregated from other people's datasets.
**Status:** VERIFIED
**Evidence:** Every Atlas page footer carries a link labelled `CC-by` → `https://www.eff.org/copyright`. That page states verbatim:

> "**Creative Commons** — Any and all original material on the EFF website may be freely distributed at will under the [Creative Commons Attribution 4.0 International License (CC-BY)](https://creativecommons.org/licenses/by/4.0/), unless otherwise noted. **All material that is not original to EFF may require permission from the copyright holder to redistribute.**
>
> You do NOT have to ask permission to post original EFF material on a mailing list or newsgroup, to use an EFF logo as a pointer to us on your web site, or to reprint an EFF statement in a newspaper article. Permission to do such things is explicitly granted. Please do not write to us asking for permission, as this wastes our time and yours.
>
> If you redistribute something you got from the EFF site, it is appreciated if you make it known where the file originated, so people can get more info or updated versions."

The Atlas methodology page's "Data Aggregation" section makes the caveat operative: *"we began collecting these public datasets from journalists, other non-profits, government entities, and sometimes surveillance vendors themselves. We then converted this data to match the Atlas of Surveillance format."* Concretely, the `Link 1 Source` counts show aggregated third-party corpora inside the Atlas: `Center for the Study of the Drone at Bard College` (756 rows), `Small, Rural, and Tribal Body-Worn Camera microgrant grantee list` (216), `Justice & Security Strategies` (194), `CRIMEWATCH` (173), plus large state-government imports (Michigan State Police 414, New Jersey State Police 398, Wisconsin DOJ 254, Illinois LETSB 250).
**Status of terms:** seen directly, quoted above — not inferred.
**Retrieved:** 2026-08-20
**Implication for the spec:** §14.2 must record for Atlas: `license = CC-BY-4.0`; `license_url = https://www.eff.org/copyright`; `attribution_required = true` (attribute "Atlas of Surveillance, a project of the Electronic Frontier Foundation and the Reynolds School of Journalism at the University of Nevada, Reno"); `redistribution = permitted for EFF-original material only`; `caveat = third-party-derived rows may carry upstream rights`. Practically: SIG can redistribute the **factual claim + the citation** freely (facts are uncopyrightable and the compilation is CC BY), but must not republish verbatim third-party `Summary` text wholesale without recording the upstream source. Store `Link 1 Source` as a first-class provenance field precisely so the third-party-origin rows are identifiable later.
**Outline delta:** ANSWERS Q15 for Atlas; EXTENDS §14.2. The outline says "historically CC BY" without the "not original to EFF" carve-out, which is the part that actually constrains SIG.

---

### F1.13 — Atlas corrections and contributions: three documented channels (answers Q34)

**Claim:** Yes — Atlas has a documented, currently-live channel for corrections, new datapoints, and whole datasets, all routed through `aos@eff.org`, plus a volunteer research pipeline (Report Back) and an explicit request *not* to send camera coordinates.
**Status:** VERIFIED
**Evidence:**

`https://www.atlasofsurveillance.org/methodology`, "Updates and Corrections", verbatim:
> "Should you identify data that needs to be corrected or updated, please email **aos@eff.org**. We will be adding to and updating the database periodically."

`https://www.atlasofsurveillance.org/collaborate`, verbatim, four channels:
> "**Volunteer** — We are always looking for volunteers to do small research tasks to help build out this dataset. Whether you've got 30 minutes or 30 hours to contribute, please fill out this form to get started: https://join.eff.org/atlas/
>
> **Submit a Datapoint** — Did you find a document about a specific police department's technology that isn't in our dataset? Are you a journalist who recently wrote an article you'd like added to the Atlas of Surveillance? Please submit to us directly at aos@eff.org. **Please do not send us the coordinates of individual surveillance cameras or automated license plate readers. You may consider sending that data to DeFlock.me.**
>
> **Educators** — The Atlas of Surveillance project's Report Back tool is a handy homework assignment or extra credit project… If you're an instructor who would like to integrate Atlas of Surveillance into your class, please email aos@eff.org.
>
> **Share a Dataset** — Many of the datapoints in the Atlas of Surveillance originated in existing datasets compiled by other researchers, such as Bard College's public safety drone data. If you have a dataset that you'd like to contribute to this project, please email us at aos@eff.org."

`https://www.atlasofsurveillance.org/about` repeats the coordinate exclusion: *"(Please do not send us the individual locations of surveillance cameras or automated license plate readers. That data may be better suited for DeFlock.me.)"* — and `/about` links `deflock.org` directly.

The Report Back tool is live at `https://reportback.eff.org/` (HTTP 200). It is gated by an email + **Group Code** (obtained from `aos@eff.org` or an instructor) and offers optional filters. **The technology filter currently offers only three values — `BODY-WORN CAMERAS`, `CAMERA REGISTRY`, `DRONES`** — plus a state filter with ~55 values (which itself contains duplicate encodings, e.g. both `VA` and `VIRGINIA`, both `WA` and `WASHINGTON`). `https://join.eff.org/atlas/` returns HTTP 200.

`/methodology` describes the workflow verbatim: *"When a user visits Report Back, they are assigned a small research task consisting of a particular location and a technology (e.g. body-worn cameras and the Tulsa Police Department). The researcher then spends 20-30 minutes looking for news articles, press releases, meeting minutes or other online documentation, and logs their research in our database. A large number of these assignments are based on leads generated by GovSpend's database of government procurement records. As of February 2025, more than 1,300 students and volunteers have contributed research to the project. Each line of data was then double-checked by multiple interns from the University of Nevada, Reno and EFF staff."*
**Retrieved:** 2026-08-20
**Implication for the spec:**
- **Answer to Q34: yes.** The channel is `aos@eff.org` for both individual corrections and whole datasets. It is human/email-mediated — there is no API, no issue tracker, no pull-request path. SIG's upstream-contribution workflow (§18) must therefore batch corrections into a human-readable digest (agency, technology, claim, citation, what's wrong) rather than attempt programmatic submission, and must expect asynchronous, unacknowledged application.
- **"Share a Dataset" is the strategically important one**: it is an explicit invitation for SIG to contribute a derived dataset upstream, which is a much higher-leverage relationship than row-level corrections.
- **The division of labour is already drawn for us**: Atlas explicitly refuses device coordinates and points contributors at DeFlock. SIG's §18 posture should mirror this exactly — device geometry flows to OSM/DeFlock, agency-level adoption claims flow to Atlas. Do not propose the reverse.
- The Report Back technology filter (BWC / Camera Registry / Drones only) tells us where Atlas is actively growing; SIG's reconciliation queue for those three technologies will churn fastest.
**Outline delta:** ANSWERS Q34; EXTENDS §18. The outline asks the question and does not answer it. It also does not record the coordinate-exclusion rule, which is a direct constraint on the SIG↔Atlas interface.

---

### F1.14 — Atlas glossary vs. Atlas data: two mismatches

**Claim:** The public glossary defines 14 terms, one of which (`Ring/Neighbors Partnership`) has **no rows** in the current dataset, and omits `Third-party Investigative Platforms`, which has 1,062 rows.
**Status:** VERIFIED
**Evidence:** `https://www.atlasofsurveillance.org/glossary` table of contents, in order: Automated License Plate Reader (ALPR); Body-Worn Camera (BWC); Camera Registry; Cell-Site Simulator (CSS); Crowdsourcing; Drone (UAV); Face Recognition (FR); Fusion Center; Gunshot Detection; Open-Source Intelligence; Predictive Policing; Real-Time Crime Center (RTCC); Ring/Neighbors Partnership; Video Analytics/Computer Vision. (Two of the fourteen — Crowdsourcing, Open-Source Intelligence — are method terms, not technologies.) Cross-referencing F1.4: no `Ring/Neighbors` value exists in the `Technology` column; `Third-party Investigative Platforms` (1,062 rows) has no glossary entry.

Two glossary definitions are load-bearing for SIG's ontology and are quoted:
> **Camera Registry** — "Some law enforcement agencies ask residents and businesses to voluntarily provide information about the security cameras they have installed on their properties. This is usually called a camera registry, and it is often integrated into other software packages, such as Motorola Solutions' CityProtect suite."
> **Real-Time Crime Center** — "Real-Time Crime Centers are hubs where police ingest and analyze surveillance, intelligence, and data from a number of sources in real-time… **Unlike fusion centers, RTCCs tend to be focused on local level activities and a broader range of criminal investigations.**"

**Retrieved:** 2026-08-20
**Implication for the spec:** The Ring/Neighbors partnership layer has been **retired from the Atlas dataset** while its glossary entry survives — so SIG cannot get Ring partnerships from Atlas and must treat the Data Library's Ring entry as historical only (see F2.5). The Camera Registry definition confirms it is a `DataSystem`/`AccessRelationship` construct (residents' cameras registered to an agency), **not** a `PhysicalAsset` the agency owns — an important modelling distinction for §8.6 vs §8.7. The RTCC/Fusion Center distinction is the vocabulary SIG should adopt for §4.10.
**Outline delta:** CORRECTS §2 Layer D's implication that Ring/Neighbors partnerships are available through Atlas — they are not in the current data. EXTENDS §8.6/§8.7.

---

### F1.15 — Atlas concentration: one row per agency-technology, so it is an adoption index, not a deployment inventory

**Claim:** Atlas is effectively one claim per (agency, technology) pair: 15,185 rows over 9,525 distinct `(State, Agency)` pairs and 7,776 distinct agency-name strings, with 6,073 agencies having exactly one row and a maximum of 11.
**Status:** VERIFIED
**Evidence:** Distinct `AOSNUMBER` = 15,185 (no duplicates). Distinct `(State, Agency)` = 9,525. Distinct `Agency` strings = 7,776 (i.e. ~1,749 agency names collide across states — "Springfield Police Department" etc.). Distinct 7-character ORI prefixes = 8,225. Agencies with a single row: 6,073. Highest row counts: Broward County Sheriff's Office (FL) 11; Miami-Dade Sheriff's Office (FL) 10; Houston Police Department (TX) 10. Per-technology distinct-agency counts (F1.4) are within 0.5% of row counts for every category except Third-party Investigative Platforms (1,062 rows / 1,039 agencies) and Face Recognition (980 / 957).
**Retrieved:** 2026-08-20
**Implication for the spec:** Atlas maps cleanly onto SIG's `Deployment` node (§8.5) at *capability* granularity with no camera counts, no contract, no dates beyond a citation date, and no lifecycle state. It never conflicts with device-level sources; it can only ever confirm or fail to mention. Reconciliation with DeFlock/HIBF is therefore **one-directional**: Atlas can raise "there should be devices here" tasks (§12 "Missing physical devices"), but device data can never contradict an Atlas row, only supersede its currency. Agency-name collisions across states mean entity resolution must key on `(ORI7, state)`, never on name.
**Outline delta:** EXTENDS §8.5, §11, §12.

---

# F2 — The EFF Data Library: complete enumeration

### F2.1 — The Data Library has 42 entries; the outline's list names 15 of them

**Claim:** `https://www.atlasofsurveillance.org/data-library` lists **42 distinct dataset/project entries**. The outline's §2 Layer D bullet list names 15 (and §21's short list names 10), missing 27 — several of which are more directly useful to SIG than the ones named.
**Status:** VERIFIED
**Evidence:** Full HTML of `/data-library` retrieved (55,205 bytes) and every `<a>` extracted with its href. The complete table is F2.2 below. Entries the outline never mentions include: **Surveillance Watch**, **Archivo de la Vigilancia**, **DeFlock**, **Surveillance under Surveillance**, **Prison Policy Initiative Correctional Contracts Library**, **National Police Funding Database**, **Equipped for War (California AB 481 military-equipment inventories)**, **California SB 978 policy-manual corpus**, **CalECPA electronic search warrants**, **Brennan Center social-media-policy directory**, **GAO-21-526 federal FRT survey**, and five state/federal body-camera grant datasets.
**Retrieved:** 2026-08-20
**Implication for the spec:** The Stage-5 backlog (§17 Stage 5) should be seeded from the 42-row table below, not from the outline's 15.
**Outline delta:** CORRECTS §2 Layer D and §21 — the outline's Data Library enumeration is 36% complete.

---

### F2.2 — The complete Data Library table (SIG Stage-5 ingestion backlog)

Legend for **Live?**: ✅ retrieved 2026-08-20 with the URL shown · ⚠️ reachable but degraded/blocked/JS-only · ❌ dead or redirected away from the resource.

| # | Entry (Atlas label) | Publisher | Atlas "Last Updated" | Coverage | Direct data URL that worked | Format | Live? | Licence (as observed) |
|---:|---|---|---|---|---|---|:--:|---|
| 1 | Atlas of Surveillance | EFF | Regularly (data as of 2026-08-12) | 15,185 US agency-technology claims | `https://atlasofsurveillance.org/download.csv` | CSV, 8.58 MB | ✅ | CC BY 4.0 (`eff.org/copyright`), third-party caveat |
| 2 | Atlas of Surveillance: Border Communities | EFF | 2020-01-10 | 23 US counties on the Mexico border; local/state/federal | `https://www.eff.org/files/2020/01/10/aos-bordercounties_-_01.10.2020.csv` | CSV, 151 KB, **207 rows** | ✅ | CC BY 4.0 (EFF) |
| 3 | Who Has Your Face? | EFF | 2020-03-19 | 50 states + DC DMVs + TSA/passport/federal-job; FR & image-sharing matrix | `https://whohasyourface.org/press/who-has-your-face-agency-sharing-3-10-2020.csv` | CSV, 8.8 KB, matrix (55 agency columns × 66 rows) | ✅ | CC BY 4.0 (EFF) |
| 4 | Public Safety Drones | Bard College, Center for the Study of the Drone | 2020-03 (3rd ed.) | US LE + fire agencies with drone programs | report `https://dronecenter.bard.edu/projects/public-safety-drones-project/public-safety-drones-3rd-edition/` ; map `https://www.google.com/maps/d/u/0/viewer?mid=1zcTdAkQB_gqVX383oQcyujM7Nd85rquH` | HTML report + Google My Maps | ✅ | not stated — **must confirm before redistribution** |
| 5 | Ring/Neighbors Partnerships | Ring Inc. | "Regularly" (stale) | LE partnership map + video-request counts | `https://www.google.com/maps/d/u/0/viewer?mid=1eYVDPh5itXq5acDT9b0BVeQwmESBa4cB` | Google My Maps | ⚠️ map loads; source blog post `blog.ring.com/2019/08/28/…` 200 but the underlying Ring Active Agency Map programme is defunct | vendor-published, no licence |
| 6 | Mapping China's Tech Giants | ASPI International Cyber Policy Centre | Ongoing | Chinese tech-company overseas infrastructure incl. smart cities / AI | `https://docs.google.com/spreadsheets/d/1QY2zt02oRour9a5hrK64_Ienszh2FgOmMwAODH4uXIw/gviz/tq?tqx=out:csv` (**3,021 rows**, 1.78 MB) | CSV via Google Sheets gviz | ⚠️ CSV ✅; the project site `chinatechmap.aspi.org.au` **403s** (Cloudflare) | ASPI terms not retrievable (site 403) |
| 7 | Cell-site Simulators | Kevin Collier (journalist) | 2017-04-11 | US agencies with CSS | `https://github.com/kevincollier/Stingray` | GitHub repo | ✅ | repo licence not checked at file level |
| 8 | The Facial Recognition World Map | Surfshark | (blank) | Country-level FR adoption | `https://docs.google.com/spreadsheets/d/157mTA67QAMxb0N4e7tO755r9uw2wsaT1z2rcCO1hPIU/edit` | Google Sheet | ✅ | vendor marketing research; no licence stated |
| 9 | AI Global Surveillance Index | Carnegie Endowment / Steven Feldstein | 2019-09-17 | 176 countries | `https://data.mendeley.com/datasets/386s7f9d25/1` | Mendeley Data | ✅ | **CC BY 4.0** (stated on the Mendeley record) |
| 10 | Federally Funded Body-Worn Cameras | US DOJ Bureau of Justice Assistance (scraped by EFF) | 2020 | BJA BWC grantees | `https://www.eff.org/document/bureau-justice-assistance-body-worn-camera-program-data` | EFF document node | ✅ | CC BY 4.0 (EFF compilation) over US-gov PD source |
| 11 | Wiretap Reports | US Courts | Annually | Federal+state intercept orders, 1997– | `https://www.uscourts.gov/data-news/reports/statistical-reports/wiretap-reports` (**Atlas link `…/statistics-reports/analysis-reports/wiretap-reports` now redirects here**) | HTML + annual tables | ✅ | US Government work — public domain |
| 12 | Aaron Swartz Day Police Surveillance Project | Aaron Swartz Day / Int'l Hackathon | 2020-09-17 | CA-centric surveillance PRA responses | `https://www.aaronswartzday.org/asdpsp-alldocs-dec2019/` | HTML index of documents | ✅ | not stated |
| 13 | California Automated License Plate Readers | California State Auditor (obtained by EFF via CPRA) | 2020-02-13 | Every CA LE agency surveyed on ALPR | `https://www.eff.org/files/2020/10/29/response_l.1.7_alpr_survey_final_responses_analysis_.xlsx` | XLSX, 234 KB | ✅ | EFF: *"raw data obtained by EFF through a CPRA request and has not been altered"* — CA public record |
| 14 | Electronic Search Warrant Notifications (CalECPA) | California DOJ | 2023-02-09 | CalECPA search-warrant disclosures 2016–2022 | **withdrawn** — `https://www.eff.org/document/calecpa-disclosures-2016-2022` now hosts no files | — | ❌ (see F2.6) | CA public record; EFF ceased hosting |
| 15 | Data Driven — ALPR Data | EFF + MuckRock | 2020-01-28 | 200 Vigilant-using agencies, 2016–17 | `https://www.eff.org/files/2020/01/28/alpr_2016-2017_update.zip` | ZIP → 2 CSV + 1 XLSX + field-description CSV | ✅ | CC BY 4.0 (EFF) |
| 16 | Mass Extraction — Mobile Device Forensic Tools | Upturn | 2020-10-21 | US agencies with MDFTs (Cellebrite etc.) | **`https://upturn.org/work/mass-extraction/`** (Atlas link `upturn.org/reports/2020/mass-extraction/` is a JS/meta redirect stub, 478 bytes) | HTML report + appendices | ⚠️ link rot | Upturn terms not checked |
| 17 | New Jersey Statewide Body-Worn Camera Survey | NJ Office of the Attorney General | 2020-09 | NJ agencies, by county | PDF `https://www.nj.gov/oag/newsreleases20/2020-BWC-Survey_FULL.pdf` (495 KB) ; scraped XLSX `https://www.eff.org/document/new-jersey-body-worn-camera-survey-2020` | PDF + XLSX | ✅ | NJ public record / EFF scrape |
| 18 | Wisconsin LE Employee Recording Devices Survey | Wisconsin DOJ | 2021-01-21 | WI UCR-registered agencies, BWC + dash | Atlas link `https://www.doj.state.wi.us/sites/default/files/news-media/1.21.21_BodyCam_AgencyResponses.pdf` → **soft-404, serves the WI DOJ homepage as HTML** | (PDF) | ❌ | WI public record |
| 19 | U.S. College Campus Police Surveillance | EFF | 2021-03-03 | 251 campus LE agencies | `https://www.eff.org/files/2021/03/09/scholars_unders_surveillance_dataset_03-03-2021.csv` | CSV, 119 KB, **251 rows** | ✅ | CC BY 4.0 (EFF) |
| 20 | Electronic Monitoring Hotspot Map | MediaJustice (Challenging E-Carceration) | 2021-03-19 | US electronic-monitoring hotspots | Atlas link `https://mediajustice.org/electronic-monitoring-hotspots/` → **redirects to `mediajustice.org/` homepage** | (map) | ❌ | — |
| 21 | Clearview AI Table | BuzzFeed News | 2021-04-06 | US taxpayer-funded entities that ran ≥1 Clearview search as of Feb 2020 | `https://www.buzzfeednews.com/article/ryanmac/facial-recognition-local-police-clearview-ai-table` | HTML searchable table (JS) | ⚠️ page 200; no export endpoint found | BuzzFeed editorial — **all rights reserved; link, do not copy** |
| 22 | Data Driven 2: California Dragnet | EFF | 2021-04-22 | 89 CA agencies, 2018–2020 | `https://www.eff.org/files/2021/04/22/data_driven_2_california_dragnet_04.22.2021.xlsx` | XLSX, 164 KB, 7 sheets incl. a data dictionary | ✅ | CC BY 4.0 (EFF) |
| 23 | California LE Agencies' Policy Documents (SB 978) | EFF | 2021-04-26 | Links to 458 CA agency policy manuals | `https://purl.stanford.edu/yf700bp8218` | CSV via Stanford Digital Repository | ✅ | **Public Domain** (stated on the PURL record) |
| 24 | Small Rural Tribal Body Worn Camera Program | DOJ BJA / srtbwc.com | 2021-12-29 | Every SRT BWC micro-grantee | `https://www.srtbwc.com/micro-grantees-data-download/` (+ searchable table `/meet-our-grantees/`) | XLS + PDF | ✅ | federal grant programme site |
| 25 | Massachusetts 2021 BWC grant awards | Commonwealth of MA | 2021-12-31 | 64 municipalities, >$4M | `https://www.mass.gov/news/baker-polito-administration-awards-municipalities-over-4-million-for-police-body-worn-cameras` | HTML press release | ⚠️ **403 to scripted clients** (needs browser-like session) | MA public record |
| 26 | Ohio 2022 BWC grant awards | Ohio Governor's Office | 2022-01-24 | 109 OH agencies, >$4.7M | `https://governor.ohio.gov/media/news-and-media/governor-dewine-awards-body-worn-camera-grants-to-100-law-enforcement-agencies-01242022` | HTML press release | ✅ | OH public record |
| 27 | 2020 Use of Unmanned Aerial Vehicles (MN Legislative Report) | Minnesota BCA / DPS | 2021-06-15 | Every MN agency drone use, count, cost, reason | Atlas link `https://dps.mn.gov/divisions/bca/Documents/legislative-report-2020-unmanned-aerial-vehicles.pdf` → **HTTP 404** | (PDF) | ❌ | MN public record (statutorily mandated annual report — see F9.7) |
| 28 | Registered Public Safety UAS Program Map | DRONERESPONDERS | 2022-04-03 | Global registered public-safety drone programmes: location, start date, agency type, #pilots, #drones | `https://droneresponders.maps.arcgis.com/apps/webappviewer/index.html?id=a84c95f4951345269f6fab330846d3de` | ArcGIS web app | ⚠️ 200 but JS-only; a FeatureServer likely exists behind it (not enumerated) | not stated |
| 29 | BJA DOJ Body-worn camera grant awards | DOJ BJA | 2022-04-03 | BWC-related awards since 2015 | `https://bja.ojp.gov/funding/awards/list?combine_awards=body-worn+camera` | HTML searchable DB | ✅ | US Government work |
| 30 | FAA Drone Registration Lookup | FAA | 2022-04-13 | Full Aircraft Registration DB (~60 MB) | `https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download/` | CSV bulk | ✅ | US Government work — public domain |
| 31 | Cities using ShotSpotter | ShotSpotter/SoundThinking | 2022-04-13 | Publicly announced ShotSpotter cities | Atlas link `https://www.shotspotter.com/cities/` → **redirects to `https://www.soundthinking.com/` homepage** | — | ❌ | vendor page (removed) |
| 32 | Smart City Technology Adoption in California | UC Berkeley "connectedgov" | 2021-03 | CA smart-city / policing tech incl. Nixle, CrimeMapping | `https://www.ocf.berkeley.edu/~connectedgov/index.php/data/` → **connection failure (no response)** | — | ❌ | — |
| 33 | Directory of Police Department Social Media Policies | Brennan Center for Justice | 2022-05-25 | 35 departments' social-media policies | `https://www.brennancenter.org/our-work/research-reports/directory-police-department-social-media-policies` | HTML | ✅ | Brennan Center terms not checked |
| 34 | South Carolina BWC Grants FY 2017-2023 | SC Dept. of Public Safety | 2022-05-13 | >260 SC agencies | XLSX `https://www.eff.org/document/south-carolina-bwc-grant-data` ; PDF `https://www.documentcloud.org/documents/23461626-…` | XLSX + PDF | ✅ | SC public record / EFF scrape |
| 35 | Current and Planned Uses of FRT by Federal Agencies | US GAO (GAO-21-526) | 2021-08 | 24 federal agencies; 18 reported FRT use; names vendors and state/local systems accessed | `https://www.gao.gov/assets/gao-21-526.pdf` | PDF | ⚠️ **403 to scripted clients**; obtainable via gao.gov UI | US Government work — public domain |
| 36 | Equipped for War — militarized policing in California (AB 481) | American Friends Service Committee | 2022-04 | CA agencies' military-equipment acquisitions, deployments, use policies | report `https://afsc.org/sites/default/files/2022_Equipped_for_wa_CA_web.pdf` (10.9 MB) ; map `https://public.tableau.com/app/profile/afscresearch/viz/…` | PDF + Tableau | ✅ | AFSC terms not checked |
| 37 | Correctional Contracts Library | Prison Policy Initiative | Periodically | Prison/jail procurement documents (comms & tech heavy) | `https://www.prisonpolicy.org/contracts/documents.html` | HTML searchable index | ✅ | PPI reprint policy applies |
| 38 | National Police Funding Database | LDF Thurgood Marshall Institute | Periodically | Federal grants, misconduct settlements, consent decrees, military-equipment transfers, staffing, demographics — by city/county/state | `https://policefundingdatabase.org/explore-the-database/` | JS dashboards + "explore the source data" pages | ⚠️ 200 but **requires JavaScript**; underlying source files enumerated on separate pages | not stated |
| 39 | Surveillance under Surveillance | (community, OSM-derived) | Hourly | Global camera/guard map from OSM | `https://sunders.uber.space/` | web map | ✅ | OSM-derived → **ODbL** (see §14.1) |
| 40 | DeFlock ALPR Map | DeFlock | (blank) | National ALPR device map | `https://deflock.me/#map=1` | web map + upstream OSM | ✅ | OSM-derived → ODbL |
| 41 | Surveillance Watch | Surveillance Watch | (blank) | **831 surveillance companies/entities** with funders, subsidiaries, affiliations, target countries, sources | `https://www.surveillancewatch.io/api/entities?limit=1000` | **JSON API** (see F9.1) | ✅ | not stated on site |
| 42 | Archivo de la Vigilancia | R3D (Mexico) | (blank) | 85 Mexican federal/state surveillance contracts, 2009–2022; searchable by keyword, jurisdiction, agency | `https://archivo.r3d.mx/` | HTML searchable archive | ✅ | **CC BY 4.0** — site footer: *"Este obra vive bajo una licencia de Creative Commons Reconocimiento 4.0 Internacional."* |

**Retrieved:** all rows 2026-08-20.
**Implication for the spec:** Six of 42 entries (14%) are already dead links, and two more are blocked to non-browser clients. Any SIG ingestion plan that treats the Data Library as a live index will silently lose 14% of it. Every Stage-5 connector must record `last_successful_fetch` and open a research task on failure (§12 "Stale evidence"). Also: EFF itself does not archive its own Data Library targets, so SIG should snapshot each of these into its own content-addressed store on first successful fetch (§10, Q25).
**Outline delta:** CORRECTS §2 Layer D, §4.7, §5.3, §21 — provides the enumeration those sections gesture at, plus the liveness truth.

---

### F2.3 — Two Data Library datasets carry technology vocabularies broader than the main Atlas

**Claim:** The Border Communities and Campus Police datasets use technology values that the main Atlas vocabulary does not contain, including the entire border-surveillance stack.
**Status:** VERIFIED
**Evidence:**

**Border Communities** (`aos-bordercounties_-_01.10.2020.csv`, 207 rows) — column `Technology Type`, complete value set:
```
Body-worn Cameras 50 | Automated License Plate Readers 34 | Drones 23 | Camera Network 14 |
Mobile Surveillance Vehicle 14 | Remote Video Surveillance Systems 7 | Spy Plane 7 |
Tethered Aerostat Radar System 6 | Integrated Fixed Towers 6 | Ring/Neighbors 5 |
Automated License Plate Readers/Surveillance Trailer 5 | Iris scanning 4 | Tactical Aerostat 4 |
Cell-site Simulators 3 | Face recognition 3 | Camera Registry 2 | Unattended Ground Sensors 2 |
Face Recognition 2 | Fusion Center 2 | Gunshot detection 2 | Surveillance Towers 2 |
Starchase 1 | Artificial Intelligence 1 | Real-Time Crime Centers 1 | Smart Streetlights 1 |
Surveillance Trailer 1 | Automated License Plate Readers/Camera Network 1 | Pole Cameras 1 |
Predictive Policing 1 | Lidar 1 | Camera Networks/Real-Time Crime Centers 1
```
Its schema differs from the main Atlas too: `Ref no., Agency, City, County, State, LEA Type, Jurisdiction Type, Technology Type, Vendor, Summary, Primary Link, Archived Primary Link, Document Type, Source, Document Date, Additional Link #1..#3, Archived Additional Link #1..#3`. **`Archived Primary Link` is populated in 204 of 207 rows** (web.archive.org URLs), and `Document Type` is populated.

**Campus Police** (`scholars_unders_surveillance_dataset_03-03-2021.csv`, 251 rows) — `Technology`: Body-worn Cameras 152; Automated License Plate Readers 49; **Social Media Monitoring 21**; Drones 10; Gunshot Detection 8; Face Recognition 6; Camera Registry 3; Video Analytics 2. `Social Media Monitoring` is not in the main Atlas vocabulary. Its `Link 1 Type` column **is** populated: News article 90; University information 28; Government information 27; Annual report 21; Policy 15; Social media 14; Academic report 10; University website 10; Press release 9; Vendor information 8; Public Records 6; Meeting documents 4; Vendor website 1; Correspondence 1; Government Website 1; Job posting 1; Nonprofit report 1; "Not really sure" 1.
**Retrieved:** 2026-08-20
**Implication for the spec:**
1. SIG's technology ontology must accommodate ~13 border/aerial technologies (Integrated Fixed Towers, Tethered/Tactical Aerostat, Remote Video Surveillance Systems, Unattended Ground Sensors, Spy Plane, Mobile Surveillance Vehicle, Surveillance Trailer, Surveillance Towers, Pole Cameras, Smart Streetlights, Iris scanning, StarChase, Lidar) plus `Social Media Monitoring` — none of which the current Atlas vocabulary supplies. §4 of the outline covers none of them.
2. The Campus `Link 1 Type` values are the *intended* vocabulary for the empty `Link N Type` column in the main CSV. SIG's own source-type vocabulary should be a cleaned superset of these plus the Border `Document Type` values (New Article/News Article, Public Records, Government Document, Info on a government website, Policy/procedure document, Government Report, Company website or promotional materials, Court Records, Social Media, Press Release, Job Posting, Academic Report, Research document).
3. The Border dataset proves EFF once systematically captured Wayback snapshots per citation. SIG should do what Atlas stopped doing.
**Outline delta:** EXTENDS §4 and §8.4 substantially — the outline's technology coverage stops at the twelve mainstream categories plus a handful of §4 subsections; the border stack is absent.

---

### F2.4 — Who Has Your Face? is a matrix, not a row-per-claim table

**Claim:** WHYF's CSV is a 55-column × ~66-row **agency × capability matrix** marked with `X`, not a normalized dataset.
**Status:** VERIFIED
**Evidence:** `https://whohasyourface.org/press/who-has-your-face-agency-sharing-3-10-2020.csv` (8,795 bytes). Header row is a blank first cell followed by 55 agency names: `TSA PreCheck, Federal Job, U.S. Passport or Visa, Alabama Motor Vehicle Division, … Wyoming Department of Transportation`. Row labels are capabilities/relationships: `Uses Facial Recognition`, `FBI FACE Services Unit`, etc., with `X` marking membership.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is exactly §4.7's "reference databases" object. Ingestion requires a transpose into `(agency, relationship_type, counterparty)` triples. Concretely it yields `AccessRelationship` edges of the form *FBI FACE Services Unit → can query → \<state DMV image database\>* — i.e. the outline's §4.7 diagram (`agency → can query → FR system → searches against → image/reference database`) instantiated for ~50 states. It is 2020 data and must be time-boxed accordingly.
**Outline delta:** CONFIRMS §4.7 and supplies the concrete shape; EXTENDS §8.8 (`AccessRelationship`) with a real worked example.

---

### F2.5 — The Ring/Neighbors dataset is historical only

**Claim:** Ring/Neighbors partnership data is no longer maintained anywhere in the EFF ecosystem: the glossary entry survives, the Data Library entry still points at a 2019 Ring blog post and a Google My Map, and there are **zero** Ring rows in the Atlas CSV.
**Status:** VERIFIED
**Evidence:** `Technology` value counts (F1.4) contain no Ring value. Data Library entry #5 links `https://blog.ring.com/2019/08/28/working-together-for-safer-neighborhoods-introducing-the-neighbors-active-law-enforcement-map/` (HTTP 200, a 2019 announcement) and `https://www.google.com/maps/d/u/0/viewer?mid=1eYVDPh5itXq5acDT9b0BVeQwmESBa4cB` (HTTP 200, a Google My Map). The Atlas glossary still defines "Ring/Neighbors Partnership" and asserts *"Ring has signed agreements with more than 1,300 law enforcement agencies."* Border Communities retains 5 `Ring/Neighbors` rows from 2020.
**Retrieved:** 2026-08-20
**Implication for the spec:** Treat Ring partnerships as a **closed historical layer** with a hard validity end. If SIG ingests them, every edge must be stamped `valid_to ≈ 2024` (when Ring retired the Request-for-Assistance mechanism) and flagged `source_no_longer_maintained`. Do not build a live Ring connector.
**Outline delta:** CORRECTS §2 Layer D — the outline lists "historical Ring/Neighbors partnerships" as a Data Library asset without noting there is no retrievable structured dataset behind it, only a 2019 blog post and a My Map.

---

### F2.6 — CalECPA: EFF withdrew a dataset after an under-redaction incident — a directly applicable precedent for SIG's §13 policy

**Claim:** EFF published California DOJ CalECPA search-warrant data, then twice modified and finally withdrew it after the state agency admitted it had failed to redact potentially personal information.
**Status:** VERIFIED
**Evidence:** `https://www.eff.org/document/calecpa-disclosures-2016-2022` — the page now contains **no attached files** and carries three stacked notices, verbatim:

> "**Update April 10, 2023:** EFF has decided to no longer host this data, since the regularly updated data is now available on the Open Justice website."
>
> "**Update, Feb. 8, 2023:** The California Department of Justice has provided EFF with updated search warrant data for 2020, 2021, and 2022, with personal information redacted. We have uploaded the data below accordingly. An agency spokesperson said via email, 'We are currently reviewing our procedures and we will follow up once the datasets are live on OpenJustice…'"
>
> "**Update, Feb 1, 2023:** Out of an abundance of caution, EFF has *temporarily* replaced the CalECPA disclosure data from 2020-2022 with new versions that do not include the 'nature of investigation' and 'facts giving rise to the emergency' columns. Following our publication of the data, the California Department of Justice (CADOJ) contacted [and] alerted us that staff had failed to properly redact potentially personal information from these fields."

The page also documents the underlying transparency failure: *"the CADOJ is supposed to publish this data online and update it regularly. However, CADOJ took the data down in summer 2022 and as of February 2023 has still not posted it online."* `https://openjustice.doj.ca.gov/` returns HTTP 200.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the canonical worked example for §13.4 and §13.2 and for Q31/Q32:
- A government-provided "public record" can contain unredacted personal data. **Republishing it is the mistake**, and the republisher — not the agency — absorbs the consequence.
- SIG must therefore have (a) a pre-publication PII screen on any free-text field originating from records requests, (b) the ability to *replace a published artifact in place with a column-reduced version* while preserving the claim, and (c) a documented takedown/correction path (Q32) that can go all the way to un-hosting.
- It also validates the "link, don't mirror" default for high-risk record sets, with mirroring reserved for cases where the upstream is demonstrably unstable — noting that here the upstream *was* unstable (down from summer 2022) which is precisely why EFF mirrored in the first place. The resolution is: **mirror privately, publish metadata publicly** (§13.4, Q31).
**Outline delta:** EXTENDS §13.4 and answers part of Q31/Q32 with a real precedent rather than a hypothetical. The outline lists this dataset by name (via "state policy datasets") without knowing its history.

---

# Part 3 — Completion pass (2026-08-20)

*Sections C, D, G and H of the original brief, written after the initial run was terminated.
Findings continue as F3.x. Note: the ALPR Accountability Atlas and ALPR Abuse Library are covered
in R2's completion pass, not here.*

The scope note at the top of this file sketched a grouping (F3 = Data Driven, F4 = SLS, F5/F6 =
ALPR Accountability Atlas / Abuse Library, F7 = ACLU, F8 = CCOPS, F9 = adjacent). That plan is
superseded: F5/F6 moved to R2, and this pass uses a single flat `F3.x` sequence. The mapping is:

| Brief section | Findings |
|---|---|
| C — EFF Data Driven / Data Driven 2 | F3.1 – F3.8 |
| D — EFF Street-Level Surveillance | F3.9 – F3.13 |
| G — ACLU | F3.14 – F3.18 |
| H — CCOPS and surveillance-ordinance inventories | F3.19 – F3.27 |
| State-level ALPR reporting mandates | F3.28 – F3.31 |
| Monahan (2026) and adjacent projects | F3.32 – F3.33 |

---

## C — EFF Data Driven / Data Driven 2 (the Vigilant/LEARN layer)

### F3.1 — Data Driven 1 is **still retrievable in 2026**, as a single ZIP at a stable EFF URL

**Claim:** The 2018 EFF/MuckRock "Data Driven" dataset has not link-rotted; it downloads today as a 44,608-byte ZIP containing a CSV, an XLSX, and two documentation CSVs.
**Status:** VERIFIED
**Evidence:** The outline's URL `https://www.eff.org/deeplinks/2018/11/eff-and-muckrock-release-records-and-data-200-law-enforcement-agencies-automated` returns HTTP 200 but contains **exactly one** substantive outbound link — to `https://www.eff.org/pages/automated-license-plate-reader-dataset`. That hub page (HTTP 200) is the real project root and links five subpages:

| Page | URL | What it holds |
|---|---|---|
| Hub | `https://www.eff.org/pages/automated-license-plate-reader-dataset` | narrative + "UPDATE April 22, 2021: We have released Data Driven 2" |
| Download | `https://www.eff.org/pages/download-alpr-dataset` | **the ZIP** + changelog |
| Explore | `https://www.eff.org/pages/explore-alpr` | full HTML table of all 200 agencies (190 KB) |
| Caveats | `https://www.eff.org/pages/caveat-data` | data-quality statement + correction address |
| Methodology | `https://www.eff.org/pages/understanding-source-documents` | how to read a LEARN Data Sharing / Hit Ratio Report |
| Findings | `https://www.eff.org/pages/what-we-learned` | headline numbers |

The bulk file: `https://www.eff.org/files/2020/01/28/alpr_2016-2017_update.zip` → **HTTP 200, 44,608 bytes, `application/zip`**, containing:

```
ALPR 2016-2017 UPDATE/EFF-MuckRock 2016-2017 ALPR DATA.csv
ALPR 2016-2017 UPDATE/EFF-MuckRock 2016-2017 ALPR DATA.xlsx
ALPR 2016-2017 UPDATE/EFF-MuckRock 2016-2017 ALPR DATA - Field Descriptions.csv
ALPR 2016-2017 UPDATE/EFF-MuckRock 2016-2017 ALPR DATA - Definitions.csv
```

The download page carries a verbatim changelog — the dataset has been corrected four times:

> "Updated Jan. 28, 2020 to fix Clayton Police Department, MO. Updated Nov. 20, 2018 to adjust Lafayette Police Department state information. Updated Nov. 15, 2018 to adjust Hawthorne Police Department and Buffalo Police Department totals, to fix a data entry error with Millburn Police Department, and to recategorize Coral Springs as a Florida city."

**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's Data Driven connector should point at the **ZIP**, not at the Deeplinks post the outline cites. The file has been static since 2020-01-28, so a `Last-Modified`/hash poll is sufficient — no scraping. Because the dataset is versioned by filename date (`2020/01/28/`), a new correction would produce a *new* URL; the connector must therefore re-scrape `/pages/download-alpr-dataset` for the current ZIP href rather than hard-coding the path.
**Outline delta:** CORRECTS §2 Layer D. The outline gives only the Deeplinks URL, which is a dead end containing no data links; it never names the ZIP, and it does not know the project has six pages and a four-entry changelog.

---

### F3.2 — Data Driven 1 schema, row count, and coverage — real numbers

**Claim:** The DD1 CSV is exactly 200 data rows × 20 columns, one row per agency, covering 23 states plus one federal entry, and its column set is a *sharing-and-volume* schema, not a deployment schema.
**Status:** VERIFIED
**Evidence:** Parsed `EFF-MuckRock 2016-2017 ALPR DATA.csv` directly (201 raw rows incl. header; **200** data rows; **200** distinct agency names; 20 columns).

Verbatim header:

```
A. Agency | B. State | C. Direct Sharing | D. NVLS
E1. 2016 Detections | E2. 2016 Hits | F1. 2017 Detections | F2. 2017 Hits
G1. 2016-2017 Detections | G2. 2016-2017 Hits
H. All Time Detections | H2. All Time Hits
R1. Data Sharing Link | R2. 2016 Hit Ratio Report | R3. 2017 Hit Ratio Report
R4. 2016 Detection Report | R5. 2016 Hit Report | R6. 2017 Detection Report
R7. 2017 Hit Report | R8. Combined Detection/Hit Data
```

State distribution — **24 distinct `State` values = 23 states + `US`**: CA 74, TX 35, GA 31, IL 9, FL 8, MO 5, OH 4, NY 4, IN 4, NJ 3, CO 3, WA 3, LA 2, AZ 2, OR 2, CT 2, MN 2, PA 1, MD 1, IA 1, AL 1, MI 1, KS 1, **US 1** (U.S. Forest Service). This reproduces EFF's "173 agencies from 23 states and the federal government" exactly, and means the `State` column is **not** a pure US-state enum — it carries one federal sentinel. The Field Descriptions CSV defines each column; `D. NVLS` is defined verbatim as:

> "National Vehicle Location Service (sometimes referred to as the National Vehicle Locator System) is a pool of data shared among hundreds of agencies, the identities of which are not disclosed. A "Y" in this field indicates the agency is sending its data to the NVLS pool."

Column-level facts I measured:

| Column | Non-null | Sum / distribution |
|---|---:|---|
| C. Direct Sharing | 185 | min 0, **median 68, mean 160.2, max 851**, total 29,642 agency-to-agency links |
| D. NVLS | 132 | `Y` 130, `N` 1, `Not Provided` 1, blank 68 |
| G1. 2016-2017 Detections | 169 | **2,541,566,055** |
| G2. 2016-2017 Hits | 170 | **11,384,164** |
| E1/E2 (2016) | 132/131 | 898,831,603 det / 3,324,143 hits |
| F1/F2 (2017) | 154/154 | 1,635,660,535 det / 7,999,522 hits |
| H/H2 (All Time) | 3/4 | 3,144,529 / 16,782 |

Missing-data sentinels are a **controlled vocabulary of three tokens**, documented in the Definitions CSV: `n/a` (70 occurrences — "documents that would not exist due to the circumstances of the agency"), `Not Provided` (208 — "an agency failed to provide records"), `Data Incomplete`. Two further free-text values appear as cross-references: `See Austin Police Department` (6) and `See: Cincinnati Police Department` (6) — regional-system agencies whose numbers are reported under a parent.

The Field Descriptions CSV header does **not** match the data CSV header: it says `F2.2017 Hits`, `G1. Combined Detections`, `G2.Combined Hits`, `H1. All Time Detections` where the data says `F2. 2017 Hits`, `G1. 2016-2017 Detections`, `G2. 2016-2017 Hits`, `H. All Time Detections`.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) Join key is `(Agency, State)` free text — the same entity-resolution problem as the Atlas (R5). (b) `Not Provided` / `n/a` / `Data Incomplete` must map to SIG's *distinct* epistemic states — "agency refused", "not applicable", "agency supplied but incomplete" are three different claims and collapsing them to NULL destroys the transparency signal. (c) The `See <other agency>` rows are **aliasing edges**, not nulls. (d) Do not join the documentation CSV on header name; it drifts.
**Outline delta:** EXTENDS §2 Layer D — the outline says the project documented "billions of plate observations; hundreds of participating agencies" without a schema, a row count, or the sentinel vocabulary.

---

### F3.3 — The headline findings, with the numbers recomputed from the file

**Claim:** EFF's public claims (200 agencies, 2.5 billion scans, 99.5% non-suspect, ~160 sharing partners on average) all reproduce from the CSV; one of them is stated two different ways on two different EFF pages.
**Status:** VERIFIED
**Evidence:** EFF's own text, verbatim from `https://www.eff.org/pages/automated-license-plate-reader-dataset`:

> "Today we are releasing records obtained from 200 agencies, accounting for more than 2.5-billion license plate scans in 2016 and 2017. … the information shows that **99.5% of the license plates scanned were not under suspicion at the time** the vehicles' plates were collected. On average, agencies are sharing data with a minimum of **160 other agencies** through Vigilant Solutions' LEARN system, though many agencies are sharing data with over **800 separate entities**."

But `https://www.eff.org/pages/what-we-learned` scopes it differently:

> "Our research shows that **173 agencies from 23 states and the federal government** accounted for roughly 2.5-billion license plate scans in 2016 and 2017. The remaining **27 agencies refused to turn over reports** on how much data they collected."

My recomputation from the CSV: detections 2,541,566,055; hits 11,384,164 → **hit rate 0.448%**, i.e. **99.552% of scans matched no hotlist**. Max `Direct Sharing` = 851 (Austin PD is 817). Mean 160.2 exactly matches EFF's "minimum of 160". 200 rows exist but only ~169–173 carry volume data — hence the 200-vs-173 discrepancy, which is a *refusal* signal, not a data gap.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG should carry both denominators. "27 agencies refused" is itself an accountability claim of the same class as the ALPR Accountability Atlas's records, and the graph should be able to represent *refusal to disclose* as a first-class edge (`agency —[refused_disclosure]→ record_request`), because it is the only place non-response is visible.
**Outline delta:** EXTENDS §2 Layer D and §10.1G. The outline lists "very high proportions of non-watchlisted scans" qualitatively; the number is 99.552% for DD1 (and 99.948% for DD2, F3.6).

---

### F3.4 — How Vigilant/LEARN sharing actually worked, mechanically

**Claim:** LEARN sharing is a four-way matrix per agency (detections out, detections in, hot lists out, hot lists in) plus an opaque national pool (NVLS); the DD1 CSV flattens this to a **single integer** and therefore cannot reconstruct the sharing graph.
**Status:** VERIFIED
**Evidence:** `https://www.eff.org/pages/understanding-source-documents`, verbatim:

> "The Data Sharing Report is composed of four distinct sections: 1) Who the agency is sharing with; 2) Who is sharing data with the agency, 3) Who the agency is sharing hot lists with, and 4) Who is sharing hot lists with the agency. … At the very bottom of this section, you will find whether the agency shares its data with NVLS (identified as NVLS and Shared NVLS)."

> "The information on the left is the name of the agency, whereas the information on the right is the name of the hot list."

> "The Hit Ratio Report shows how many license plates an agency scanned and how many of those plates were attached to a hot list. It generally includes a pie chart… For example, the above Brentwood Police Department document shows that only 0.1% of the license plates captured were relevant to an investigation."

EFF also documents that Vigilant marketed this as trivially easy — quoting Vigilant's own materials: *"Joining the largest law enforcement LPR sharing network is as easy as adding a friend on your favorite social media platform."* And on NVLS, from `/pages/explore-alpr`: *"even if an agency shows it is only sharing directly with a few agencies, if NVLS is checked, then it actually is sharing with hundreds through the pooled data."*

The methodology page also records that the record-request strategy was itself built on a leaked artifact: *"We provided each agency with a guide to producing these records straight from the user manual, which had been obtained through open records law by Mike Katz-Lacabe of the Center for Human Rights and Privacy."*
**Retrieved:** 2026-08-20
**Implication for the spec:** This is a direct structural precedent for SIG's Flock sharing model. Three requirements fall out:
1. Sharing must be modelled with **direction and kind**: `{detections, hotlists} × {outbound, inbound}` — four edge types, not one. Vigilant's own report format proves agencies distinguish them, and Flock's `SharedNetworks` model has the same shape.
2. **Pooled/opaque sharing needs its own node type.** NVLS is an edge to an unenumerable set. SIG must be able to say "shares with an undisclosed pool of ~N" without inventing member edges. Modelling NVLS as 130 dangling edges or as zero edges are both wrong.
3. The **degree is recoverable but the edge list is not** from the published CSV — the counterparty names exist only inside the DocumentCloud PDFs. See F3.5.
**Outline delta:** EXTENDS §2 Layer D substantially. The outline says only "sharing relationships through Vigilant's LEARN ecosystem"; it does not know the four-way structure or the NVLS opacity problem, both of which change the data model.

---

### F3.5 — The DD1 evidence layer is machine-inaccessible: DocumentCloud and MuckRock both 403 to non-browser clients

**Claim:** All 463 source-document links in the DD1 CSV point at DocumentCloud, and DocumentCloud, MuckRock, and the project-level search URLs all return **HTTP 403** to a scripted client with a browser UA.
**Status:** VERIFIED (as INACCESSIBLE for the underlying documents)
**Evidence:** Link-domain census of the DD1 CSV: `www.documentcloud.org` **463**, `www.eff.org` **2** (`/document/kings-point-police-department-alpr-statistics`, `/document/montebello-police-department-alpr-detectionhit-data-2016-2017`). Liveness tests, all with `Mozilla/5.0 … Chrome/126` UA:

| URL | Result |
|---|---|
| `https://www.documentcloud.org/documents/4432161-Data-Sharing-Report-Austin-Police-Department.html` | redirects to `https://embed.documentcloud.org/documents/4432161-…/` → **HTTP 403** |
| `https://www.documentcloud.org/search/projectid:38044-ALPR-Data-Sharing-2018` | redirects to `/projects/38044-ALPR-Data-Sharing-2018/` → **HTTP 403** |
| `https://www.muckrock.com/foi/list/?page=1&per_page=100&q=vigilant&user=3647` | **HTTP 403** |

Note the two DocumentCloud project IDs are recoverable and stable: **38044** ("ALPR Data Sharing 2018") and **38217** ("ALPR Hit Ratio 2018").

I also tested the DocumentCloud **API** directly, unauthenticated: `https://api.www.documentcloud.org/api/documents/4432161/`, `…/api/projects/38044/` and `…/api/documents/search/?q=project:38044` all return a **Cloudflare interstitial** (`<title>Attention Required! | Cloudflare</title>`), not JSON. The block is bot-protection at the edge, not a 404 — so an authenticated client with a registered token may succeed, but no unauthenticated path works.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG can ingest the *aggregate* DD1 table today but **cannot** programmatically ingest the underlying Data Sharing Reports that contain the counterparty names — which is exactly the layer needed to build a Vigilant sharing graph. Options, in order of cost: (a) register for a DocumentCloud API token and retry `api.www.documentcloud.org` with authentication — unauthenticated access is Cloudflare-blocked, so a token is a hard prerequisite, not an optimisation; (b) treat the 463 URLs as *evidence citations only*, storing the URL and the project id without fetching; (c) manual/assisted extraction of the ~200 Data Sharing Report PDFs as a one-off Stage-5 project. Do **not** design a connector that assumes these PDFs are fetchable.
**Outline delta:** EXTENDS §2 Layer D and §21. The outline treats Data Driven as a "priority ingestion source" without noting that its most valuable layer sits behind a 403.

---

### F3.6 — Data Driven 2 is also retrievable — a 7-sheet XLSX, 89 California agencies, with a **Flock column already in it**

**Claim:** DD2 downloads today as a single XLSX with seven sheets, a self-documenting Fields sheet, 89 agency rows, and — notably — two columns dedicated to Flock Safety's 30-day retention limit, five years before SIG.
**Status:** VERIFIED
**Evidence:** The outline's implied DD2 Deeplinks URL (`/deeplinks/2019/07/data-driven-2-…`) **404s**. The live article is `https://www.eff.org/deeplinks/2021/04/data-driven-2-california-dragnet-new-dataset-shows-scale-vehicle-surveillance` (HTTP 200), which links `https://www.eff.org/document/data-driven-2-california-dragnet-data-set`, which serves:

`https://www.eff.org/files/2021/04/22/data_driven_2_california_dragnet_04.22.2021.xlsx` → **HTTP 200, 164,079 bytes**, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

Seven sheets, extracted from `xl/workbook.xml`:

| # | Sheet | Non-empty data rows |
|---|---|---:|
| 1 | `Main Sheet wFormulas` | **89** |
| 2 | `Top 15 LEAs ScansVMT` | 14 |
| 3 | `LEAs 2018-2019 Hit Ratio ` | **64** (63 agencies + 1 embedded totals row) |
| 4 | `LEAS IrregularIncomplete Hit Ra` | 25 |
| 5 | `Useful Links` | 4 |
| 6 | `Notes` | 13 |
| 7 | `Fields` | 26 (the data dictionary) |

The `Fields` sheet is a genuine machine-readable data dictionary with columns `Column | Field | Type of Data | Source | Format | Formula | Formula in plain language | What/Why | Other`. The 25 fields:

| Col | Field | Type | Source |
|---|---|---|---|
| A | 0. Notes | Text | "Notes from Dave" — marks rows where sources disagree or are suspect |
| B | 1. CPRA Link | URL | MuckRock |
| C | 2. EFF Ref | Alphanumeric | `CAALPR000` etc., autogenerated sequential |
| D | 3. Agency | Text | formal agency name |
| E | 4a. Hit Ratio (Percent that are hits) | Numerical | PRAs |
| F | 5a. Avg License Plate Scans Per 100 Vehicle Miles Travelled | Numerical | PRAs + CalTrans VMT |
| G | 5b. Avg Vehicle Miles Traveled Per Single ALPR Scan | Numerical | PRAs + CalTrans VMT |
| H / I / J | 6. City / 7. County / 8. State | Text | "Always CA" |
| K–N | 9a/9b/10a/10b. 2018 & 2019 Detections & Hits | Numerical | PRAs |
| O / P | 11a/11b. 2020 Detections / Hits | Numerical | only from requests filed in 2021 |
| Q / R | 12a/12b. 2018-2020 detections / hits | Numerical | "Some agencies did not break up data by year" |
| **S / T** | **13a. 30 Day Scans (Flock) / 13b. 30 Day Hits (Flock)** | Numerical | *"Agencies that use flock can only provide data on last 30 days"* |
| U | 14. Average Daily Scans | Numerical | PRAs |
| V–X | 15a/15b/15c. Daily VMT 2018 / 2019 / average | Numerical | CalTrans |
| Y | 16. Data Sharing Report? | Y/N | "Usually just Y or blank" |

Measured coverage: 89 distinct agencies, 24 distinct counties, state always `CA`; `Data Sharing Report?` = `Y` 83, `N` 1, blank 5. Only **one** agency has Flock 30-day figures populated (2,957,671 scans / 2,012 hits).
**Retrieved:** 2026-08-20
**Implication for the spec:** Three things.
1. **DD2 is a schema donor, not just a dataset.** Its `Fields` sheet is close to the per-claim provenance record SIG needs: field, type, *source*, formula, plain-language explanation. SIG's own field dictionary should carry the same "Formula in plain language" column — it is what makes a derived metric auditable by a non-technical advocate.
2. **The Flock 30-day column is the earliest documented instance of the exact retention-driven measurement problem SIG faces.** EFF hit it in 2021: Flock agencies cannot answer "how many scans last year", only "how many in the last 30 days". Any SIG metric that mixes Vigilant annual totals with Flock 30-day windows is comparing incommensurable quantities. SIG must attach an explicit `observation_window` to every usage-volume claim and refuse to sum across windows.
3. `2. EFF Ref` (`CAALPR###`) is a **project-local stable identifier** — evidence that even a 89-row hand-built dataset needed its own ID space. Reinforces R5's case for SIG-minted stable ids.
**Outline delta:** CORRECTS §2 Layer D (the outline's DD2 URL is dead) and EXTENDS it substantially — the outline knows DD2 exists but not that it is an XLSX, not that it has a published field dictionary, and not that it already contains Flock-specific columns.

---

### F3.7 — DD2 headline numbers, recomputed, plus EFF's own coverage caveat

**Claim:** DD2's "99.9% not related to an investigation" reproduces as **99.948%**; but DD2's 89 agencies are a small minority of California ALPR users, and EFF says so.
**Status:** VERIFIED
**Evidence:** From the article, verbatim:

> "In 2019 alone, just **82 agencies collected more than 1 billion license plate scans** using ALPRs. Yet, **99.9% of this surveillance data was not actively related to an investigation** when it was collected."

> "The dataset covers **89 agencies** from all corners of the state. However, the data was not always presented by the agencies in a uniform manner. **Only 63 agencies provided comprehensive and separated data for both 2018 and 2019.** … **(Note: More than 250 agencies use ALPR in California).**"

> "Tiburon Police stockpile about 7.7-million license plate scans annually, and yet only .01% or 1 in 10,000 of those records were related to a crime or other public safety interest when they were collected. The data is retained for a year."

My recomputation from the XLSX:

| Quantity | Value |
|---|---|
| 2019 detections, main sheet, n=82 agencies | **1,034,856,161** (matches "just 82 agencies … more than 1 billion") |
| 2018 detections, n=75 | 722,179,324 |
| 2020 detections, n=27 | 257,403,442 |
| Clean-cohort (sheet 3, 63 agencies, totals row excluded) detections | **1,681,232,745** |
| Clean-cohort hits | **873,788** |
| Hit rate | **0.0520%** → **99.948% matched no hotlist** |

Data-quality artefact worth recording: **sheet 3 contains an embedded totals row with a blank `EFF Ref`** (704,137,688 / 977,095,057 / 1,680,206,504). A naive `SUM` over that sheet double-counts and yields 3.36 billion instead of 1.68 billion. Sheet 4 (`Irregular/Incomplete`) carries free-text quality notes per row, e.g. *"Note: 2019 data is lower than expected for a full year of data collection"*, *"Note: Not including hit ratio because originating data may be inaccurate"*, *"Note: Only 2018 ALPR data provided. Only using 2018 VMT."*
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) **Never ingest an analyst spreadsheet without detecting totals rows** — a blank identifier column is the cheap detector; make it a validator in the Stage-2 loader. (b) Sheet 4's per-row notes are exactly SIG's `data_quality_note` field and should be preserved verbatim, not summarised. (c) The 89-of-250+ ratio is the ceiling on what a records-request dataset represents; SIG must display coverage as a fraction of a known universe wherever the source states one, so that "89 agencies" is never read as "the ALPR landscape".
**Outline delta:** EXTENDS §2 Layer D and §13.1 (uncertainty display).

---

### F3.8 — Licence, correction channel, and EFF's own statement that the authoritative dataset is Vigilant's

**Claim:** Both Data Driven datasets are covered by EFF's site-wide CC BY 4.0 grant with a non-EFF-material carve-out; the correction channel is a named individual's email; and EFF explicitly states that no accurate dataset can exist without vendor disclosure.
**Status:** VERIFIED
**Evidence:** `https://www.eff.org/copyright`, verbatim:

> "Any and all original material on the EFF website may be freely distributed at will under the **Creative Commons Attribution 4.0 International License (CC-BY)**, unless otherwise noted. **All material that is not original to EFF may require permission from the copyright holder to redistribute.** … If you redistribute something you got from the EFF site, it is appreciated if you make it known where the file originated."

Neither `/pages/download-alpr-dataset` nor the DD2 document page carries a dataset-specific licence notice, so the site-wide grant applies by default — with the same carve-out already flagged for the Atlas in **F1.12**. Materially: the *compiled tables* are EFF's original work (CC BY 4.0); the *linked agency records* on DocumentCloud are government records EFF did not author.

Correction channel — `https://www.eff.org/pages/caveat-data`, verbatim:

> "Analyzing ALPR data is an imperfect science, and we intend to update this dataset as inconsistencies are identified. **If you encounter an issue, please email Dave Maass at dm@eff.org** … the law enforcement agencies we surveyed sometimes appeared not to fully understand how their systems worked and consequently provided inaccurate, incomplete, or unclear data. … law enforcement agencies sometimes provided documents that were difficult to read or interpret, creating a greater potential for human error during the manual data entry into our dataset."

And the key epistemic statement, verbatim from the same page:

> "**To our knowledge, there is only one entity capable of disclosing a comprehensive dataset that would near perfect accuracy: Vigilant Solutions itself.** We urge the company to publish this data, which would not only save our time, but also the time of every law enforcement agency staff member who must process our public records request."

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) Attribution string for both datasets: *"EFF and MuckRock, Data Driven / Data Driven 2, CC BY 4.0"*, with the source-document links attributed to the originating agency, not EFF. (b) The correction channel is a **personal email, not a form or an issue tracker** — SIG cannot automate corrections upstream to Data Driven; the round-trip is manual and should be modelled as such in the §13 correction workflow (contrast the Atlas's three channels in F1.13). (c) EFF's Vigilant statement is the strongest available third-party articulation of SIG's own thesis: the vendor holds the ground truth and every civil-society dataset is a costly reconstruction. It belongs in SIG's framing and in the epistemic-status vocabulary — SIG's claims about sharing are *reconstructed from disclosure*, never authoritative.
**Outline delta:** EXTENDS §13.4 / Q15 / Q34. Q15 is now answered for Data Driven as well as the Atlas.

---

## D — EFF Street-Level Surveillance: the second taxonomy

### F3.9 — SLS is a separate site with exactly **16** technology explainers; `eff.org/issues/street-level-surveillance` is a redirect

**Claim:** The outline's URL for SLS 301-redirects to `https://sls.eff.org/`, a standalone Rails application whose complete technology vocabulary is 16 terms, mirrored in Spanish at `/es/`.
**Status:** VERIFIED
**Evidence:** `https://www.eff.org/issues/street-level-surveillance` → HTTP 200 with `url_effective = https://sls.eff.org/` (identical 26,560-byte body). Every `/technologies/<slug>` link on the homepage, all confirmed HTTP 200:

| # | Slug | Page title |
|---|---|---|
| 1 | `automated-license-plate-readers-alprs` | Automated License Plate Readers |
| 2 | `biometric-surveillance` | Biometric Surveillance |
| 3 | `body-worn-cameras` | Body-Worn Cameras |
| 4 | `cell-site-simulators-imsi-catchers` | Cell-Site Simulators / IMSI Catchers |
| 5 | `community-surveillance-apps` | Community Surveillance Apps |
| 6 | `drones-and-robots` | Drones and Robots |
| 7 | `electronic-monitoring` | Electronic Monitoring |
| 8 | `face-recognition` | Face Recognition |
| 9 | `forensic-extraction-tools` | Forensic Extraction Tools |
| 10 | `gunshot-detection` | Gunshot Detection |
| 11 | `police-access-to-iot-devices` | Police Access to IoT Devices |
| 12 | `police-databases` | Police Databases |
| 13 | `predictive-policing` | Predictive Policing |
| 14 | `real-time-location-tracking` | Real-Time Location Tracking |
| 15 | `social-media-monitoring` | Social Media Monitoring |
| 16 | `surveillance-camera-networks` | Surveillance Camera Networks |

`https://sls.eff.org/articles` renders the same 16 slugs (it is an index alias, not additional content). `https://sls.eff.org/es/` (HTTP 200) exposes 16 `/es/technologies/…` links — the taxonomy is fully translated, one-to-one.

Most pages follow a fixed rubric: *How it works · What kinds of data it collects · How law enforcement uses it · **Who sells it** · Threats posed · EFF's work · EFF legal cases · Suggested additional reading*. Two do not: `biometric-surveillance` is a container page with sub-technology sections (**DNA Collection and Searches**, **Tattoo Recognition**, **Iris recognition**), and `police-databases` is organised by *system tier* (**Federal Law Enforcement Networks**, **Nlets**, **State and Local Police Databases**, **Gang Databases**, **Commercial Databases**) rather than by the rubric.
**Retrieved:** 2026-08-20
**Implication for the spec:** SLS is a **second EFF-controlled technology vocabulary of 16 terms that does not equal the Atlas's 12** (F1.4). SIG's technology ontology must carry both as source vocabularies with independent mappings, because SLS terms are what advocates, journalists and city ordinances actually use, while Atlas terms are what the Atlas data is keyed on. The slug is the stable key on both sides.
**Outline delta:** EXTENDS §2 Layer D and §4 (taxonomy). The outline never mentions SLS at all; it is a materially different vocabulary from the same publisher.

---

### F3.10 — The Atlas ↔ SLS crosswalk

**Claim:** Of the Atlas's 12 categories, **6 are exact matches** to an SLS technology, **5 are narrower or broader** than an SLS technology, and **1 (Fusion Center) has no SLS page at all**; in the reverse direction, **5 SLS technologies have no Atlas equivalent whatsoever** and 3 more are broader or narrower than the nearest Atlas category.
**Status:** VERIFIED
**Evidence:** Built by reading all 16 SLS pages in full and comparing against the 12 Atlas slugs enumerated in **F1.4**. SKOS-style mapping labels; "narrowMatch" means *the Atlas term is narrower than the SLS term*.

| Atlas category (F1.4) | Atlas rows | SLS technology | Mapping | Basis |
|---|---:|---|---|---|
| Automated License Plate Readers | 4,145 | Automated License Plate Readers | **exactMatch** | identical definition; both name Vigilant, Flock, Motorola |
| Body-worn Cameras | 5,469 | Body-Worn Cameras | **exactMatch** | identical |
| Cell-site Simulator | 83 | Cell-Site Simulators / IMSI Catchers | **exactMatch** | SLS adds the "Stingray" alias explicitly |
| Face Recognition | 980 | Face Recognition | **exactMatch** | identical; SLS also nests it under Biometric Surveillance |
| Gunshot Detection | 248 | Gunshot Detection | **exactMatch** | SLS titles the section "Acoustic Gunshot Detection" |
| Predictive Policing | 200 | Predictive Policing | **exactMatch** | identical |
| Drones | 1,828 | Drones and Robots | **narrowMatch** | SLS covers ground/patrol robots and submersibles; the Atlas category is aerial-only |
| Camera Registry | 756 | Surveillance Camera Networks | **narrowMatch** | SLS treats registries ("sometimes called *SafeCam*") as one sub-section of camera networks |
| Real-Time Crime Center | 242 | Surveillance Camera Networks | **narrowMatch** | SLS has an "Real-Time Crime Centers (RTCC)" H-level section, not a top-level page; names Fusus explicitly |
| Video Analytics | 85 | Surveillance Camera Networks | **narrowMatch** | SLS: *"Face recognition, however, is only one form of video analytics deployed with surveillance cameras. BriefCam, for example…"* — inside the camera-networks page |
| Third-party Investigative Platforms | 1,062 | Police Databases | **broadMatch** | SLS's "Commercial Databases" section covers the same vendors; SLS's category is wider (it also includes CJIS/Nlets/gang databases which the Atlas does not track) |
| **Fusion Center** | **81** | *(none)* | **no equivalent** | "fusion center" appears only as prose inside `police-databases` and `social-media-monitoring`; there is no SLS explainer for the institution |

Reverse direction — **SLS technologies the Atlas does not cover, or covers only partially**. Five (marked **no equivalent**) have no Atlas category at all:

| SLS technology | Nearest Atlas category | Mapping | Note |
|---|---|---|---|
| Biometric Surveillance (DNA, tattoo, iris, gait) | Face Recognition | **broadMatch** | Atlas tracks only the face modality; DNA/iris/tattoo are untracked |
| Community Surveillance Apps (Citizen, Nextdoor, neighbourhood apps) | *(none)* | **no equivalent** | closest historical Atlas concept was Ring/Neighbors, which is dead (**F2.5**) |
| Electronic Monitoring (ankle monitors) | *(none)* | **no equivalent** | |
| Forensic Extraction Tools (Cellebrite, GrayKey) | *(none)* | **no equivalent** | but SF and Seattle inventories both track it (F3.19, F3.20) |
| Police Access to IoT Devices | *(none)* | **no equivalent** | |
| Police Databases (federal networks, Nlets, gang databases) | Third-party Investigative Platforms | **narrowMatch** | Atlas covers only the commercial-vendor slice |
| Real-Time Location Tracking (CSLI, ad-tech location purchases) | Cell-site Simulator | **relatedMatch** | different mechanism, same harm class |
| Surveillance Camera Networks | Camera Registry / RTCC / Video Analytics | **broadMatch** | one SLS term subsumes three Atlas terms |

**Retrieved:** 2026-08-20
**Implication for the spec:** Concretely, SIG's technology ontology should be **SLS-shaped with Atlas categories as narrower children**, not the reverse:
- `surveillance_camera_network` becomes a parent with `camera_registry`, `real_time_crime_center`, `video_analytics` as children — which also fixes the Atlas's own problem that RTCCs and camera registries are separate rows about the same programme.
- `biometric_surveillance` becomes a parent of `face_recognition`, with `dna`, `iris`, `tattoo`, `gait` as siblings that currently have zero Atlas rows — SIG can carry them as declared-but-unpopulated so that a future source can fill them without a schema migration.
- `fusion_center` must be retained as a SIG-level concept even though SLS lacks a page, because 81 Atlas rows depend on it. This is the one place where the Atlas vocabulary is *richer* than SLS.
- The five SLS technologies with no Atlas equivalent, plus the three partial gaps, are the honest statement of what the Atlas-derived layer of SIG **cannot see**, and should be surfaced in the dossier's `missing_evidence` section as "technology classes not covered by any ingested source".
**Outline delta:** EXTENDS §4 / §10.1C. The outline asks for an Atlas→SIG mapping table but does not know a second EFF vocabulary exists, and therefore does not anticipate that the two disagree on granularity in both directions.

---

### F3.11 — SLS pages carry per-technology vendor rosters, which are a usable seed for the vendor ontology

**Claim:** 12 of the 16 SLS pages contain a "Who Sells It" section naming specific vendors; this is prose, not data, but it is EFF-curated and technology-scoped.
**Status:** PARTIALLY VERIFIED
**Evidence:** The rubric heading "Who Sells …" appears on 12 pages (`body-worn-cameras`, `cell-site-simulators-imsi-catchers`, `community-surveillance-apps`, `drones-and-robots`, `electronic-monitoring`, `face-recognition`, `forensic-extraction-tools`, `gunshot-detection`, `police-access-to-iot-devices`, `predictive-policing`, `real-time-location-tracking`, `social-media-monitoring`) plus ALPR. Sample content, verbatim from `face-recognition`:

> "**Clearview AI** is one such popular platform commonly used by law enforcement. Its database of more than 30 million photos, which is based on images scraped from a variety of online and public locations, is one of the most extensive known to be used. **MorphoTrust**, a subsidiary of **Idemia** (formerly known as OT-Morpho or Safran), is another large vendor…"

The camera-networks page names **BriefCam** and **Fusus** with deployment examples ("In Atlanta, Memphis, Orlando, and dozens of other locations…"). The ALPR page names Flock and Vigilant. I did not extract every vendor mention across all pages — the sections are narrative, with vendor names inline and often as hyperlinks, so a complete roster requires NER or manual reading. **Status is PARTIALLY VERIFIED because I confirmed the structure exists and sampled it, but did not enumerate every vendor.**

There is **no machine-readable interface**: no JSON, no CSV, no sitemap-driven API. `sls.eff.org` is a Rails app serving HTML; the only stable machine handle is the 16 slugs.
**Retrieved:** 2026-08-20
**Implication for the spec:** Treat SLS as a **vocabulary and prose reference, not a dataset**. Two concrete uses: (1) seed the `technology → known_vendors` relation in SIG's ontology from the "Who Sells" sections, tagged `source=SLS, extraction=manual`; (2) use the SLS explainer URL as the canonical human-readable definition link on every SIG technology page, in both English and Spanish (`/es/technologies/<slug>` exists for all 16), which gives SIG bilingual technology glossaries for free under CC BY.
**Outline delta:** EXTENDS §7 (vendor/technology taxonomy) and §15 — the outline has no bilingual glossary strategy and SLS supplies one at zero cost.

---

### F3.12 — SLS licence

**Claim:** SLS content falls under EFF's site-wide CC BY 4.0 grant; the SLS footer links `https://www.eff.org/copyright` directly.
**Status:** VERIFIED
**Evidence:** `sls.eff.org` footer contains `href="https://www.eff.org/copyright"`, which is the CC BY 4.0 statement quoted verbatim in **F3.8**. No SLS-specific licence override was found on the homepage or on any of the 16 technology pages. The same "material not original to EFF may require permission" carve-out applies — relevant because SLS pages embed third-party photographs with their own credits (e.g. *"A fixed ALPR and a mobile ALPR. Credit: Mike Katz-Lacabe (CC BY)"*).
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG may reuse SLS definitions and translations with attribution. **Do not** mirror SLS images — they carry independent credits and licences.
**Outline delta:** EXTENDS Q15.

---

### F3.13 — SLS ↔ Atlas is a one-way link: the Atlas is advertised from SLS, but SLS categories are not used in Atlas data

**Claim:** EFF cross-links the two projects in the UI but has not reconciled their vocabularies; the Atlas CSV contains no SLS term and SLS contains no Atlas row counts.
**Status:** VERIFIED
**Evidence:** `sls.eff.org` links `https://atlasofsurveillance.org/` from its homepage nav. The Atlas hub `https://www.eff.org/pages/atlas-surveillance` is linked from the EFF global nav alongside "Street Level Surveillance". But the Atlas `Technology` column's 12 values (F1.4) share only 6 exact strings with the 16 SLS titles, and the Atlas glossary (F1.14) defines terms — e.g. "Ring/Neighbors Partnership" — that have no SLS page, while SLS defines 8 technologies with no Atlas category (F3.10).
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG cannot delegate the crosswalk to EFF — it does not exist upstream. The mapping in F3.10 is SIG's to own and maintain, and it should be published as a versioned artifact (a `technology_crosswalk.csv` with `sig_term, atlas_slug, sls_slug, mapping_type, note`) so that downstream users and EFF itself can review it. This is also a plausible upstream contribution back to EFF.
**Outline delta:** EXTENDS §10.1C and §19 (community contribution).

---

## G — ACLU

### F3.14 — "Get the Flock Out" toolkit: complete component inventory

**Claim:** The ACLU toolkit is a five-section organising guide, not a dataset; its components are a discovery guide, a diagnostic question list, three model legal instruments, a sample constituent email, and a coalition-building guide.
**Status:** VERIFIED
**Evidence:** `https://www.aclu.org/get-the-flock-out-toolkit` — HTTP 200, 62,714 bytes. Section headings verbatim, in order:

1. **Who is this toolkit for?**
2. **Find out if Flock or other ALPR companies are in your neighborhood**
   - 2a. *Finding ALPR Cameras in Your Community*
   - 2b. *Find Out if Your City is Considering Installing ALPR Cameras*
   - 2c. *Questions to Keep In Mind*
3. **Ask your representatives to pass the ACLU's model bill regulating ALPRs**
4. **Build a local movement**
5. **Make some noise** (`#GetTheFlockOut`, social graphics)

Plus a "Sign Up For Our Local Advocacy Series" mailing-list capture and links to the parent campaign `https://www.aclu.org/campaigns-initiatives/get-the-flock-out` and to `https://www.aclu.org/news/tracking-alpr-cameras`.

The three model legal instruments, each a distinct URL:

| Instrument | URL |
|---|---|
| Model ALPR privacy bill (state) | `https://www.aclu.org/documents/automatic-license-plate-reader-privacy-model-bill` |
| Model ALPR privacy bill (local) | `https://www.aclu.org/documents/local-automatic-license-plate-reader-privacy-model-bill` |
| **Model resolution for local Flock contract cancellation** | `https://www.aclu.org/documents/model-resolution-for-local-flock-contract-cancellation` |

The four substantive policy asks, verbatim:

> "Limiting data retention to hours or days, not weeks or a month or more"
> "Limiting data sharing by prohibiting sharing with or providing access to any other government entity unless they have a warrant for a felony crime that is recognized under local/state law"
> "Limiting usage to felony investigations, missing persons cases, identifying unregistered/uninsured vehicles, and certain limited non-enforcement scenarios, like electronic toll collection"
> "Requiring annual usage reporting and placing limits on the availability of ALPR data via open records requests so it cannot be used for troublesome purposes like stalking or embarrassing a person for entertainment value"

**Retrieved:** 2026-08-20
**Implication for the spec:** The toolkit is SIG's **user-story document**. It is not ingestible, but it defines the task the flagship dossier must complete. Note the last policy ask in particular: the ACLU wants ALPR data itself restricted from open-records release — a direct constraint on what SIG should ever mirror (reinforces **F2.6** / §13.4).
**Outline delta:** EXTENDS §15.1 — the outline names the toolkit as a Layer E source without inventorying it, and treats it as data when it is a specification of user need.

---

### F3.15 — The toolkit names SIG's entire federation, unprompted

**Claim:** The ACLU's "how to find out if there are cameras near you" section independently lists six of the projects the outline treats as SIG's source layers, plus ten ALPR vendors — validating the federation thesis and giving SIG a vendor watchlist.
**Status:** VERIFIED
**Evidence:** Verbatim from the toolkit:

> "ACLU affiliates in Washington, **Iowa**, **Oregon**, and **Rhode Island** have maps showing where ALPR cameras have been installed in their states. **Deflock.org** has a crowdsourced map showing exact locations of ALPR cameras. **Have I Been Flocked?** has a list of public audits of law enforcement agencies' use of Flock cameras. … The Electronic Frontier Foundation's **"Atlas of Surveillance"** is a searchable database and map… **Flock Safety has "transparency portals"** with barebones information… You can also check this **crowdsourced list of Flock transparency portals**. … **ALPR.watch** has a crowdsourced map of local government meetings where ALPR cameras will be on the agenda."

The affiliate-map URLs are concrete and previously unregistered by the outline: ACLU-WA `https://www.aclu-wa.org/news/its-time-to-regulate-flock-cameras-and-alprs-with-the-driver-privacy-act/`, ACLU-IA `https://www.aclu-ia.org/campaigns-initiatives/stopsurveillance/`, ACLU-OR (an **Infogram** embed: `https://infogram.com/1p9ynv7kjjz9z7u71n1yvwwnkyf3jmrl7jk`), ACLU-RI (a **PDF slide deck**: `https://www.riaclu.org/app/uploads/2026/02/SlideDeck_webinar_260209.pdf`). Also `https://deflock.org/groups` for local organising groups and `https://haveibeenflocked.com/news/transparency-portals` for the portal list.

The vendor list, verbatim:

> "…an ALPR company like **Flock Safety, Axon, Vigilant Solutions (a subsidiary of Motorola Solutions), Genetec, PlateSmart, Innova Systems, Rekor, ELSAG, Perceptics, or Jenoptik**."

And the discovery tactic SIG's procurement watch should automate:

> "Check past city council meeting agendas and minutes. Consideration of ALPR contracts could be in the **'consent agenda'** section. Look for keywords like 'automated license plate reader' or the acronym 'ALPR'."

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The ten-vendor list is a ready-made seed for SIG's vendor-neutral ALPR model — it extends the outline's six-vendor tree (Flock, Vigilant, Rekor, Axon, Genetec, other) with **PlateSmart, Innova Systems, ELSAG, Perceptics, Jenoptik**. (b) The **consent-agenda** tactic is a concrete, automatable signal: consent agendas are where ALPR contracts pass without debate, and a keyword monitor over municipal agenda documents is the highest-value procurement-watch feature (§15.4). (c) Four state ACLU affiliate maps exist and are each in a **different, non-machine-readable format** (news page, campaign page, Infogram embed, PDF deck) — a good illustration of why affiliate-level data cannot be a programmatic source class.
**Outline delta:** EXTENDS §2/§21 (vendor list, four new affiliate sources) and §15.4 (consent-agenda monitoring is a named tactic, not an invention).

---

### F3.16 — The advocate's derived field list, and what §15.1's dossier is missing

**Claim:** The toolkit's "Questions to Keep In Mind" plus its action steps yield a 17-field requirement list; **§15.1's dossier covers 11 of them and omits 6**, three of which are the fields that actually determine whether an advocate can act.
**Status:** VERIFIED
**Evidence:** The toolkit's diagnostic questions, verbatim:

> "What specific problem does your community want to address? Does mass surveillance actually fix the issue…? Does your city have an ALPR contract? If so, can you get a copy? **When does the contract end?** How many ALPR cameras are in use in your city? Where are they located? **Are they in areas that seem to target particular groups of people?** (Low-income neighborhoods, immigrants, people of color, etc.) How much is your city paying for ALPRs? **Did the city council approve the use of ALPRs?** How long does your city retain its ALPR data and does it share it with others? **What restrictions are there on police searching the ALPR database…? Is a warrant required? Did your city council vote on the ALPR contract? Was it part of their consent agenda? Was there public education about it?** … Has the city or the police department publicly reported on how ALPRs have been used in your city?"

Mapped against §15.1's declared output list (*technologies deployed; vendors; status; device counts; physical map; contracts; annual cost; retention; data sharing; inbound/outbound access; audit coverage; policy; incidents/litigation; historical timeline; missing evidence*):

| Advocate need (derived) | §15.1 field | Covered? |
|---|---|---|
| What technology, which vendor | technologies deployed; vendors | ✅ |
| How many cameras | device counts | ✅ |
| Where they are | physical map | ✅ |
| Contract exists / copy of it | contracts | ✅ |
| How much is the city paying | annual cost | ✅ |
| Retention period | retention | ✅ |
| Who the data is shared with | data sharing; inbound/outbound access | ✅ |
| Has the agency publicly reported usage | audit coverage | ✅ (partly) |
| Search restrictions / warrant requirement | policy | ✅ (subsumed) |
| Prior incidents / litigation | incidents/litigation | ✅ |
| What is unknown | missing evidence | ✅ |
| **1. Authorization provenance** — did council vote? on the consent agenda? was there public education? which body approved it, on what date, by what vote? | — | ❌ **missing** |
| **2. Contract termination mechanics** — not just *expires*, but auto-renewal, notice window, termination-for-convenience clause, and the next decision date | contracts (expiry only) | ❌ **missing** |
| **3. Applicable legal regime + available lever** — does this state have an ALPR statute? does this city have a CCOPS ordinance? which model bill applies here? | — | ❌ **missing** |
| **4. Peer precedent** — which comparable jurisdictions cancelled, when, and on what argument | — | ❌ missing |
| **5. Siting equity** — are cameras concentrated in low-income / immigrant / majority-POC areas? | physical map (geometry only) | ❌ missing |
| **6. Claimed justification and its evidence** — what problem did the agency say this solves, and is there efficacy evidence? | — | ❌ missing |

**Retrieved:** 2026-08-20
**Implication for the spec:** Add six fields to §15.1. The three that matter most, in priority order:

1. **`authorization` block** — `{approving_body, decision_date, vote_tally, was_consent_agenda: bool, public_comment_held: bool, agenda_url, minutes_url}`. This is the single highest-value addition: it converts the dossier from a description into a **procedural handle**. "Approved on the consent agenda with no public comment" is the argument that wins cancellations, and it is fully derivable from municipal agenda systems (Legistar, Granicus, IQM2, CivicClerk — all of which SIG will already be scraping for §15.4).
2. **`termination` block** — `{expires, auto_renews: bool, notice_period_days, termination_for_convenience: bool, next_decision_date}`. An advocate cannot act on `expires: 2027-04-02` alone; if the contract auto-renews with 60 days' notice, the actionable date is **2027-02-01**, and that is the date the dossier should surface. Appendix B's `contracts.expires` is necessary but not sufficient.
3. **`legal_regime` block** — `{state_alpr_statute, local_surveillance_ordinance, ordinance_requires_council_approval: bool, applicable_model_bill}`. Without this the dossier tells a Nashville advocate and a Houston advocate the same thing, when the Nashville advocate has an ordinance to invoke and the Houston advocate does not. F3.19–F3.27 supply the ordinance side of this; F3.28–F3.31 supply the state side.

The remaining three (`peer_precedent`, `siting_equity`, `claimed_justification`) should be added but can be Stage-6+; note that `siting_equity` carries real methodological and ethical risk (it is a demographic inference over camera geometry) and should be gated by §13's review.
**Outline delta:** **CORRECTS §15.1** — the outline's dossier field list is incomplete against its own stated user. This is the highest-value correction in this file.

---

### F3.17 — The ACLU cell-site simulator map is **dead**: removed from the live site between Nov 2024 and Jan 2025

**Claim:** "Stingray Tracking Devices: Who's Got Them?" now returns HTTP 404 at every known URL; it survives only in the Internet Archive, and its content was last updated in **November 2018**.
**Status:** INACCESSIBLE (live) / VERIFIED (archived)
**Evidence:** Live probes, all with a browser UA:

| URL | Result |
|---|---|
| `https://www.aclu.org/issues/privacy-technology/surveillance-technologies/stingray-tracking-devices` | **HTTP 200** — an issue landing page that still *advertises* the map |
| `https://www.aclu.org/issues/privacy-technology/surveillance-technologies/stingray-tracking-devices-whos-got-them` | **HTTP 404** |
| `https://www.aclu.org/map/stingray-tracking-devices-whos-got-them` | **HTTP 404** (redirects to the above) |
| `https://www.aclu.org/news/privacy-technology/stingray-tracking-devices-whos-got-them` | **HTTP 404** |

The live issue page still renders the teaser text — *"Last updated December 14, 2018 [Updated November 2018] The map below tracks what we know… The ACLU has identified 75 agencies in 27 states…"* — with a link to a 404. **The map is advertised but gone.**

Wayback CDX for the map URL shows continuous HTTP 200 snapshots from **2017-08-28 through 2024-11-02**, then continuous HTTP 404 from **2025-01-14 through 2026-08-13**. Removal therefore occurred between 2024-11-02 and 2025-01-14, consistent with ACLU's Drupal→WordPress site migration (the live pages are now WordPress; the archived ones are Drupal).

Archived content retrieved from `https://web.archive.org/web/20241102151113id_/https://www.aclu.org/issues/privacy-technology/surveillance-technologies/stingray-tracking-devices-whos-got-them` (HTTP 200, 85,628 bytes). Its structure and coverage:

- A US choropleth with a "Show map data" accordion listing **all 51 jurisdictions** (50 states + DC), each with one of four statuses: `Local police have cell site simulators` (9), `State police have cell site simulators` (6), `Local and state police have cell site simulators` (13), `Police use of cell site simulators unknown` (**23**). That is **28 jurisdictions with confirmed use** = 27 states + DC, matching the stated "75 agencies in 27 states and the District of Columbia".
- Per state, a bulleted list of named agencies each with an inline citation, e.g. *"Los Angeles Police Department: 'LAPD Spy Device Taps Your Cell Phone' (LA Weekly)"*, *"Ventura County Sheriff (Center for Human Rights and Privacy)"*, *"Delaware State Police (FOIA Response to Mike Katz-Lacabe)"*.
- A trailing list of **14 federal agencies**: FBI, DEA, US Secret Service, ICE, US Marshals Service, ATF, IRS, US Army, US Navy, US Marine Corps, US National Guard, US Special Operations Command, NSA, CBP.
- The ACLU's own limitation statement, verbatim: *"because many agencies continue to shroud their purchase and use of stingrays in secrecy, this map dramatically underrepresents the actual use of stingrays by law enforcement agencies nationwide."*

**No machine-readable form exists** — no JSON, CSV or GeoJSON is referenced in the archived page; the map data is Drupal-rendered HTML. **No licence statement** appears on the archived page; ACLU's site-wide terms are at `https://www.aclu.org/user-agreement` and are **not** an open licence (unlike EFF's CC BY).
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) Do **not** register this as a live source. If SIG wants cell-site-simulator coverage, the ingestible artefact is a **one-time parse of a Wayback snapshot** of a 2018-vintage dataset, and every resulting claim must carry `valid_as_of: 2018-11`, `source_status: withdrawn`, `retrieved_from: web.archive.org`. (b) It is worth doing anyway: the Atlas has only **83** cell-site-simulator rows (F1.4) against ACLU's 75 state/local agencies plus 14 federal — the two sets almost certainly differ, and the ACLU set carries per-agency citations the Atlas lacks. (c) Licence is **unclear and not open** — SIG should link rather than mirror, or seek permission. (d) This is a second worked example, alongside CalECPA (**F2.6**) and Ring (**F2.5**), of a civil-society dataset silently disappearing. Three out of three of the historical datasets examined in this workstream have decayed. That is the empirical basis for SIG's archival policy: **snapshot on first ingest, always**.
**Outline delta:** **CORRECTS §2 Layer E / §21** — the outline lists the ACLU stingray map as a source; it is a dead link on a live page.

---

### F3.18 — ACLU licensing posture differs materially from EFF's

**Claim:** Unlike EFF (CC BY 4.0 site-wide), the ACLU publishes no open licence for its content, maps, or model bills; reuse permission must be inferred or sought.
**Status:** PARTIALLY VERIFIED
**Evidence:** Neither `https://www.aclu.org/get-the-flock-out-toolkit` nor `https://www.aclu.org/community-control-over-police-surveillance` nor the archived stingray map carries a Creative Commons mark or any reuse grant. The site footer links `/user-agreement`, `/privacy-statement` and `/accessibility`; there is no `/copyright` equivalent to EFF's. **I did not fetch and read the full user agreement text**, so this is PARTIALLY VERIFIED: I confirmed the *absence* of an open licence on the source pages, not the precise terms of the agreement.
**Retrieved:** 2026-08-20
**Implication for the spec:** ACLU material is **link-only** by default in SIG. Model bills may be quoted as legal instruments (facts about the law are not copyrightable, and model bills are published to be copied), but toolkit prose, maps and graphics must not be mirrored without asking. Where SIG wants ACLU-derived structure (e.g. the CCOPS jurisdiction list in F3.19), SIG should re-derive it from primary municipal sources rather than copying ACLU's compilation.
**Outline delta:** EXTENDS Q15 — the outline's licensing question is scoped to Atlas/Accountability Atlas/HIBF and does not consider that the ACLU sources have no open licence at all.

---

## H — CCOPS and surveillance-ordinance inventories

### F3.19 — There are **26** CCOPS jurisdictions, and the authoritative list is published only as a **JPEG**

**Claim:** The ACLU maintains the canonical count (26 jurisdictions, ~18 million people) but publishes the jurisdiction list exclusively as a raster image; there is no CSV, no API, and no HTML list anywhere in the ACLU CCOPS resource library.
**Status:** VERIFIED
**Evidence:** `https://www.aclu.org/community-control-over-police-surveillance` (HTTP 200; `https://www.aclu.org/issues/privacy-technology/surveillance-technologies/community-control-over-police-surveillance` redirects here). Verbatim:

> "The effort's principal objective is to pass CCOPS laws that ensure local residents, through their city council representatives, are empowered to decide if and how surveillance technologies are used… To date, **CCOPS laws have been adopted in 26 jurisdictions** from coast to coast, where they serve to protect and empower **nearly 18 million people**. In 2019, the nation's first municipal ban on the use of facial recognition technology came as a part of a CCOPS law in San Francisco, and in 2020, the nation's largest city and police force – New York City – adopted a CCOPS law."

The page section `id="existing-ccops-laws-national-map"` — titled "Existing CCOPS Laws: National Map" — contains **no list, no table and no interactive map**. Its only asset is:

`https://assets.aclu.org/live/uploads/2024/11/2800x1400_CCOPS_2024_B-11212024-lrg-text-resized.jpg` (HTTP 200, 1,059,687 bytes, 2800×1400 JPEG).

I downloaded and read the image. The 26 labelled jurisdictions:

| State | Jurisdictions |
|---|---|
| CA (8) | Berkeley, **BART System** *(a transit district, not a city)*, Davis, Oakland, Palo Alto, San Diego, San Francisco, **Santa Clara County** *(a county)* |
| MA (7) | Boston, Cambridge, Lawrence, Medford, Newburyport, Northampton, Somerville |
| MI (2) | Detroit, Grand Rapids |
| MO (2) | Columbia, St. Louis |
| OH (2) | Dayton, Yellow Springs |
| NY (1) | New York |
| PA (1) | Pittsburgh |
| TN (1) | Nashville |
| WA (1) | Seattle |
| WI (1) | Madison |

The ACLU CCOPS resource library (`https://www.aclu.org/documents/community-control-over-police-surveillance-resource-library`, HTTP 200, document date **July 20, 2020**) contains 20 links — model bill, guiding principles, blog posts, press coverage, ACLU-NorCal's campaign guide PDF — and **no jurisdiction list, no ordinance texts, and no inventory links**. EFF has no equivalent page: `https://www.eff.org/issues/community-control-over-police-surveillance` returns HTTP 200 but renders the generic Issues index, not a CCOPS page.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) SIG must **maintain its own CCOPS jurisdiction register** — a small hand-curated table of ~26 rows with `jurisdiction, state, ordinance_citation, effective_date, inventory_url, inventory_format, oversight_body`. There is no upstream to sync from. 26 rows is a tractable manual asset with a long half-life. (b) Note two entries are **not cities**: BART (a transit district) and Santa Clara County — SIG's jurisdiction model must accommodate special districts and counties, not just municipalities. (c) The list is dated November 2024 and the page text is older still (it still frames urgency around the 2016 election); treat 26 as a **lower bound** and re-verify. (d) Coverage: 18M of ~335M US residents ≈ **5.4% of the population**, and 26 of roughly 18,000 US law-enforcement agencies ≈ **0.14% of agencies**.
**Outline delta:** **EXTENDS §2 — the outline never mentions CCOPS at all.** This is the source class SIG's spec claims and the outline does not describe.

---

### F3.20 — Seattle: a Master List, per-technology Surveillance Impact Reports, and **quarterly** acquisition-determination reports — all PDF

**Claim:** Seattle runs the most complete CCOPS regime in the country and publishes on a genuinely current cadence (Q2 2026 report is up), but every artefact is a PDF and nothing appears on Seattle's open-data portal.
**Status:** VERIFIED
**Evidence:** The outline-era URL `https://www.seattle.gov/tech/initiatives/privacy/surveillance-technologies` now 301s to `https://www.seattle.gov/tech/data-privacy/surveillance-technology/surveillance-technologies-under-review`. The hub is `https://www.seattle.gov/tech/data-privacy/surveillance-technology` (HTTP 200).

**(1) Master List** — `https://www.seattle.gov/documents/Departments/Tech/Surveillance/ML%20Updates/2025%20Revised%20Master%20List%20of%20Surveillance%20Technologies%20September%202025.pdf` → HTTP 200, 413,531 bytes, **15-page PDF**, revised **September 2025**. Contents:

> "The Seattle City Council passed SMC 14.18 known as the 'Surveillance Ordinance', to provide greater transparency… which took effect on September 1, 2017… requirements that include: surveillance technology review and approval by City Council before acquisition, Council review and approval via ordinance for existing technologies, and reporting about surveillance technology use and community impact."

As of September 2025 the list contains **14 technologies across 2 departments** — SDOT 1, SPD 13 — down from 28 after a 2024 deprecation/reclassification pass. Per-row fields: `Department | Technology | SIR Council Bill | Description`. The 14:

| Group | Dept | Technology | Council Bill |
|---|---|---|---|
| 1 | SDOT | Closed Circuit Television "Traffic Cameras" | CB 119519 (9/23/19) |
| 2 | SPD | Automated License Plate Recognition (ALPR) | CB 120025 (4/19/21), materially updated by CB 120778 (6/18/24) |
| 2 | SPD | Parking Enforcement Systems | CB 120026 (4/19/21) |
| 3 | SPD | Forward Looking Infrared Real-time video (FLIR) | CB 120053 (5/24/21) → CB 120518 (3/14/23) |
| 3 | SPD | Situational Awareness Cameras Without Recording | CB 120054 (5/24/21) |
| 4A | SPD | Callyo | CB 120753 (4/16/24) |
| 4A | SPD | Audio Recording Systems | CB 120307 (5/17/22) |
| 4B | SPD | Camera Systems – Images or Non-Auditory Video | CB 120499 (2/28/23) |
| 4B | SPD | Tracking devices | CB 120504 (2/28/23) → CB 120994 (6/17/25) |
| 4B | SPD | Remotely Operated Vehicles (ROVs) | CB 120503 (2/28/23) |
| 4B | SPD | Computer, cellphone and mobile device extraction tools | CB 120501 (2/28/23) |
| 4B | SPD | Hostage Negotiation Throw Phone | CB 120754 (4/16/24) |
| 2024 | SPD | **Real-Time Crime Center software (RTCC)** | CB 120845 (10/8/24) → CB 121053 (9/9/25) |
| 2024 | SPD | **Closed-Circuit Television Camera Systems (CCTV)** | CB 120844 (10/8/24) → CB 121052 (9/9/25) |

The Master List also documents **removals** with reasons — a genuine deprecation ledger. Notably *"SDOT | License Plate Readers | CB 119519 | This technology has been deprecated"*, and eleven others removed as "does not meet the surveillance definition" (911 Logging Recorder, Computer-Aided Dispatch, IBM i2 iBase, GeoTime, Coplogic, Maltego, Crash Data Retrieval Tools, binoculars, …).

**(2) Surveillance Impact Reports.** Register: `https://www.seattle.gov/tech/data-privacy/surveillance-technology/adopted-surveillance-impact-report-register`. Sample retrieved: `https://www.seattle.gov/documents/Departments/Tech/Surveillance/2024%20SIR/TACPP/2024%20CCTV%20SIR%20FINAL.pdf` → HTTP 200, 757,535 bytes, **40 pages**. Each SIR is a **fixed 50-field questionnaire**, which is the single most dossier-relevant schema found anywhere in this workstream:

| SIR section | Fields |
|---|---|
| 1.0 Abstract | 1.1 purpose; 1.2 why created/updated |
| 2.0 Project/Technology Overview | 2.1 benefits; **2.2 data or research demonstrating anticipated benefits**; 2.3 technology description; 2.4 mission relation; 2.5 who deploys it |
| 3.0 Use Governance | 3.1 pre-use process; **3.2 legal standards/conditions before use**; 3.3 policies and training |
| 4.0 Data Collection and Use | 4.1 what is collected; 4.2 minimisation; 4.3 how/when/by whom deployed; 4.4 frequency; **4.5 permanence of installation**; **4.6 is the device visible; what markings**; 4.7 who can access; 4.8 third-party operation; 4.9 acceptable access reasons; 4.10 safeguards |
| 5.0 Data Storage, Retention and Deletion | 5.1 storage; 5.2 audit-for-compliance mechanism; 5.3 destruction of improperly collected data |
| 6.0 Data Sharing and Accuracy | **6.1 which entities inside and external to the City are data-sharing partners**; 6.2 necessity; 6.3 restrictions on non-City use; 6.4 information-sharing-agreement approval; 6.5 accuracy checks; 6.6 individual access/correction |
| 7.0 Legal Obligations, Risks, Compliance | 7.1 legal authority; 7.2 privacy training; 7.3 identified privacy risks; 7.4 chilling-effect concerns |
| 8.0 Monitoring and Enforcement | 8.1 disclosure record; 8.2 auditing measures |
| Fiscal Impact | 1.1 **initial acquisition costs**; 1.2 **ongoing operating costs incl. maintenance**; 1.3 cost-savings potential; **1.4 subsidies or free products offered by the vendor** |
| Racial Equity Toolkit | 1.2 civil-liberties impacts; 1.3 racial/ethnic bias risks; **1.4 where in the City the technology is used or deployed**; 1.5 disparate impact of data-sharing decisions; 1.6 disparate impact of retention decisions; 1.7 unintended consequences |
| Public Outreach | 2.1 organisations personally invited; 2.1 scheduled public meetings; 3.1–3.5 public-comment analysis by question; 4.1 response to concerns; **5.1 metrics reported annually to the CTO** |
| References | other government references; academics/consultants; white papers |

**(2b) What a filled SIR actually contains — and where it is empty.** I retrieved the ALPR SIR
(`https://www.seattle.gov/documents/Departments/Tech/Surveillance/Material%20Update%20Docs/ALPR/2023%20SIR%20Fleet-Wide%20ALPR%20with%20Change%20Markup.pdf`,
HTTP 200, 421,901 bytes, 32 pages) and read the dossier-relevant fields. Verbatim:

> **5.1** "All data collected from the ALPR system is stored, maintained, and managed in a CJIS certified evidence retention platform. Retention is automated, such that unless a record is identified as being related to a criminal investigation and exported in support of that investigation, **all ALPR data is deleted after 90 days**. No backup data is captured or retained."

> **5.2** "SPD's Audit Unit can conduct an audit of any SPD system at any time. In addition, the Office of Inspector General can access all data and audit for compliance at any time. SPD conducts periodic reviews of audit logs and they are available for review at any time by the **Seattle Intelligence Ordinance Auditor**…"

> **6.1** "**SPD has no data sharing partners for ALPR.** No person, outside of SPD, has direct access to the PIPS system or the data while it resides in the system… Data may be shared with outside entities in connection with criminal prosecutions: • Seattle City Attorney's Office • King County Prosecuting Attorney's Office • King County Department of Public Defense • Private Defense Attorneys • Seattle Municipal Court • King County Superior Court…"

> **Fiscal Impact 1.4** "Current or potential sources of funding including subsidies or free products offered by vendors or governmental entities: **Seattle Police Foundation Grant**"

Two caveats that matter for extraction. First, **the Fiscal Impact tables 1.1 and 1.2 are unfilled
templates** in this document — the rows `Direct initial acquisition cost`, `Professional services
for acquisition`, `Annual maintenance and licensing`, `Department overhead` are present with no
values, and 1.3 still reads *"Respond to question 1.3 here"*. The schema being mandated does not
mean the field is populated. Second, the running page header inside this ALPR SIR reads
**"Hostage Negotiation Throw Phone"** — a template copy-paste defect in the city's own filing,
which means page-header text is unreliable as a document-identity signal during extraction.

**(3) Quarterly determination reports** — the live cadence. `https://www.seattle.gov/tech/data-privacy/surveillance-technology/reports` lists quarterly reports from 2017 Q4 through **2026 Q2**, unbroken. Retrieved `.../CTO%20Quarterly%20Reports/2026/Q2_2026_Surveillance%20Technology%20Determination%20Report.pdf` → HTTP 200, 1,810,503 bytes, **260 pages**. Verbatim:

> "The Privacy Office received **105 total requests for privacy reviews during Q2 of 2026**. 104 technologies and projects were applicable for this report. **One of the technologies reviewed during Q2 of 2026 was determined to be a surveillance technology**, requiring a new Surveillance Impact Report (SIR). Thirteen technologies were identified as technologies falling under existing SIRs, or that met the ordinance-defined exemption criteria."

Also published annually: **Surveillance Technology Community Equity Impact Assessment and Policy Guidance Reports**, 2019 through **2025**, unbroken.

**Machine-readability check:** the Socrata catalogue at `data.seattle.gov` returns **one** result for `q=surveillance` — an unrelated public-records-request dataset (`6qkn-8xvw`). Seattle publishes **nothing** about surveillance technology on its open-data portal.
**Retrieved:** 2026-08-20
**Implication for the spec:** Three concrete consequences.
1. **The SIR is the field list SIG's dossier should converge on.** It already contains, as mandated government disclosure: retention, named sharing partners, initial and operating cost, *vendor subsidies/free products*, deployment locations, visibility/signage, audit mechanism, legal authority, and annual metrics. §15.1 should be reviewed field-by-field against this schema. Note especially **Fiscal Impact 1.4 (free products offered by the vendor)** — the exact mechanism by which Flock and Fusus seed deployments, and which in Seattle's ALPR filing resolves to a **private police-foundation grant** — and **4.6 (markings/signage)**, which is directly checkable against OSM-mapped physical assets (Layer A). But note that mandated ≠ populated: Seattle's ALPR SIR leaves the acquisition and operating-cost tables blank, so SIG must distinguish `field_absent` from `field_present_but_empty` from `field_answered`.
2. **The Q-report is a procurement-watch feed.** 105 privacy reviews per quarter, each with a determination — this is Seattle telling SIG, on a 30-day statutory lag, everything the city considered acquiring. It is the single richest §15.4 input found, and it is a 260-page PDF.
3. **Extraction is PDF-parsing, not API consumption.** URL patterns are stable enough to enumerate (`/documents/Departments/Tech/Surveillance/CTO%20Quarterly%20Reports/<year>/…`) but filenames are inconsistent across years; the reports index page must be scraped for hrefs.
**Outline delta:** EXTENDS §15.1, §15.4 and §21 with an entire source class the outline omits.

---

### F3.21 — San Francisco: a **biannual citywide** inventory covering every department, with its own technology-category vocabulary

**Claim:** SF's Chapter 19B inventory is broader than any other CCOPS regime — it covers all city departments, not just police — and it publishes a compliance breakdown showing **26% of surveillance technologies in use have no approved policy**.
**Status:** VERIFIED
**Evidence:** `https://www.sf.gov/surveillance-technology-inventory` (HTTP 200). Current report: `https://media.api.sf.gov/documents/March_2_2026_Biannual_Surveillance_Technology_Inventory_Report.pdf` → HTTP 200, 300,198 bytes, **11-page PDF**, dated **March 2, 2026**, covering 2025-09-02 → 2026-03-01. Verbatim:

> "The San Francisco Administrative Code via Chapter 19B: Acquisition of Surveillance Technology requires the Committee on Information Technology (COIT) staff to maintain an inventory of all surveillance technologies that departments plan to buy or are using, and to publish a biannual report on the inventory's status. The Biannual Surveillance Technology Inventory Report includes **the name of each technology in the inventory, a general technology category description, the department using or planning to use the technology, and information about where that technology is in the policy creation and approval process**."

> "As of March 1, 2026, **66%** of surveillance technologies in use or in the process of being procured have a surveillance technology policy approved by the Board of Supervisors, **7%** have a draft policy that has been reviewed by the COIT Privacy and Surveillance Advisory Board, **1%** is represented by technologies seeking to be procured… and **26% are surveillance technologies currently in use without a policy**."

Four appendices, each a table:

| Appendix | Contents | Columns |
|---|---|---|
| A | BOS-approved — **93 technologies / 58 policies** | Technology Category, Department Name, Technology Name, BOS Approval Date |
| B | Draft policy reviewed by PSAB — **10 technologies / 8 policies / 5 departments** | Technology Category, Technology Name, Department, PSAB Recommendation Date |
| C | Seeking procurement or in SFPD pilot — **1** (Video Analytics with AI, SFPD) | Technology Category, Technology Name, Department |
| D | **In use without an approved policy — 37 technologies / 9 departments** | Technology Category, Technology Name, Department |

SF's **technology-category vocabulary**, as observed in the document: `ALPR`, `Automated License Plate Reader`, `Audio Recorder`, `Audio Recorder/ Video Recorder`, `Biometric Processing Software and/or System`, `Camera`, `Data Analytics Software`, `Data Forensics Software`, `Drone`, `Local Area Network`, `Location Management System`, `Network Server`, `RFID/Toll Reader`, `Social Media Monitoring Software`, `Weapons Detection System`. **`ALPR` and `Automated License Plate Reader` appear as two distinct category strings in the same table** — SFMTA's transit-only-lane enforcement cameras are categorised `ALPR` while five other entries use the long form.

Substantively interesting rows: SFMTA transit-only lane enforcement (TOLE) cameras and automated speed enforcement cameras are classified as surveillance technology; **Hootsuite, Meltwater, Sprout Social, Buffer, TweetDeck and Archive Social are inventoried as "Social Media Monitoring Software"** across ~30 departments under a single multi-departmental policy approved 12/12/2023; Appendix D includes `Cellebrite Inseyets`, `Cogent ABIS`, `DataWorksPlus`, `CellHawk` and `Penlink` at SFPD, all in use without policy.

Appendix C documents a **2024 ballot-measure change to the regime**, verbatim:

> "the ordinance includes a specific provision allowing the Police Department—and only the Police Department—to conduct a **one-year pilot period** for new surveillance technologies before obtaining final policy approval. This pilot provision was added through a **voter-approved ballot measure in March 2024**."

**Machine-readability check:** `data.sfgov.org` Socrata catalogue returns **zero** surveillance-inventory datasets.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) SF is the best evidence that a surveillance inventory should be **citywide, not police-only** — SIG's organisation model must attach deployments to arbitrary agencies (libraries, museums, transit, airports, public health), not just LEAs. (b) The `in use without an approved policy` count (37, 26%) is a **compliance-gap metric** SIG should surface directly in the dossier: "your city has an ordinance and is not complying with it" is an actionable finding. (c) SF supplies a **third technology vocabulary**, disjoint from both Atlas (12) and SLS (16), and internally inconsistent. Every jurisdiction will supply its own; SIG's crosswalk must be n-way, not 2-way, and must tolerate intra-source inconsistency. (d) The March-2024 pilot carve-out means "no approved policy" no longer implies "unlawful" for SFPD — jurisdiction-specific legal nuance that a naive compliance metric would get wrong.
**Outline delta:** EXTENDS §5 (organisation model), §7 (taxonomy), §15.1.

---

### F3.22 — Boston: an annual per-technology report whose field schema is almost exactly SIG's dossier

**Claim:** Boston's Annual Surveillance Report answers nine numbered questions for each of ~20 technologies across six departments — and those nine questions map nearly one-to-one onto §15.1.
**Status:** VERIFIED
**Evidence:** `https://www.boston.gov/departments/mayors-office/bostons-use-surveillance-technology` (HTTP 200, page footer "Last updated: 7/17/26"). Report: `https://www.boston.gov/sites/default/files/file/2025/07/2024%20City%20of%20Boston%20Annual%20Surveillance%20Report.pdf` → HTTP 200, 1,701,773 bytes, **87 pages**.

Per-technology field schema, extracted verbatim from the numbered headings:

| # | Field | Ordinance wording (verbatim, §1) |
|---|---|---|
| 1 | **Description** | *"A description of how [the] Surveillance Technology has been used, including whether it captured images, sound, or other information regarding members of the public who are not suspected of engaging in unlawful conduct."* |
| 2 | **Data Sharing** | |
| 3 | **Complaints** | |
| 4 | **Audits** | |
| 5 | **Effectiveness** | |
| 6 | **Public Records Requests** | |
| 7 | **Cost** | |
| 8 | **Impact on Communities** | |
| 9 | **Agreements** | |

Technologies covered (from the table of contents): Camera and Video Management Systems (BPD; and separately BMPS/Parks/Boston Public Schools), Shooter Detection System (BMPS), Audio and Video Devices — Recording / Non-Recording / Covert (BPD), **Automated License Plate Recognition System**, Body Worn Cameras, Cell-Site Simulator, Crime Laboratory Unit, Electronic Intercept & Analysis System ("Wire Room"), Firearms Analysis Unit, Forensic Examination Hardware and Software, **Associative Violence Information System (formerly Gang Assessment Database)**, GPS Tracking Units, Latent Print Unit, Gunshot Detection (SoundThinking ShotSpotter), Software and Databases, Specialty Cameras (Night Vision, Thermal, Infrared, X-Ray), Unmanned Aerial Systems, Vehicles Equipped with Surveillance Technology, and Critical Infrastructure Monitoring Systems (Office of Emergency Management).

The report also states retention inline, e.g. verbatim: *"Captured video footage is kept for 30 days then automatically overwritten. However, in specific cases, video footage may be kept for a longer period of time. For example, downloaded video footage that becomes part of a BPD Investigation may be kept indefinitely."* And the ALPR section documents individual uses as numbered case narratives (`1. Fugitive Investigation`, `2. Shooting Investigation`, `3. Larceny Incident`, `4. B&E of MV Investigation`, `5. Homicide Investigation`, …).

**Cadence problem:** the ordinance requires the Mayor to file annually **by February 1**. As of **2026-08-20**, the most recent report posted is the **2024** report (published July 2025); the 2025 report is not on the page. The 2023 report (published July 2024) shows the same ~5-month lag. So the real cadence is *annual, roughly 5–6 months late*.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) Boston's nine fields — description, sharing, complaints, audits, **effectiveness**, public-records requests, cost, community impact, agreements — should be adopted as SIG's per-technology dossier spine, because they are what a CCOPS ordinance actually compels an agency to answer, and therefore what SIG can hope to fill from primary sources. **`Effectiveness` and `Complaints` are not in §15.1** and are exactly the fields the ACLU toolkit asks advocates to raise (F3.16, gap 6). (b) The 5–6 month statutory lag must be modelled: SIG's freshness display should compare `mandated_due_date` against `actually_published_date` and expose the delta — a late report is itself an accountability finding. (c) Boston is the counter-example to "police-only": Boston Public Schools appears in the camera inventory.
**Outline delta:** EXTENDS §15.1 with two named fields (`effectiveness`, `complaints`) and §13.1 with the mandated-vs-actual freshness comparison.

---

### F3.23 — Oakland: per-technology annual reports carrying **real usage counts** — the CCOPS analogue of Data Driven

**Claim:** Oakland's OMC 9.64 annual reports contain the same scan/hit quantities EFF had to FOIA for, published as a matter of course — but oaklandca.gov blocks scripted access, and the practical archive is a third-party mirror.
**Status:** VERIFIED
**Evidence:** `https://www.oaklandca.gov/Government/Boards-Commissions/Privacy-Advisory-Commission` → **HTTP 403** to a browser-UA curl (Cloudflare-style block); `https://www.oaklandca.gov/files/assets/.../2-5-2026-privacy-advisory-commission-meeting-agenda-packet.pdf` → **HTTP 403** likewise. The accessible mirror is Oakland Privacy, a local advocacy group: `https://oaklandprivacy.org/oak-advisory-commission/` (HTTP 200, 88,978 bytes), which hosts PAC documents directly.

Retrieved `https://oaklandprivacy.org/wp-content/uploads/2021/05/ALPR-Annual-Report-2020.pdf` → HTTP 200, 252,727 bytes, 6 pages. Verbatim:

> "Oakland Municipal Code (OMC) 9.64.040: Surveillance Technology 'Oversight following City Council approval' requires that for each approved surveillance technology item, city staff must present a written annual surveillance report for Privacy Advisory Commission (PAC). After review by the Privacy Advisory Commission, city staff shall submit the annual surveillance report to the City Council. The PAC shall recommend to the City Council that: • The benefits to the community of the surveillance technology outweigh the costs and that civil liberties and civil rights are safeguarded. • That use of the surveillance technology cease; or • Propose modifications to the corresponding surveillance use policy that will resolve the concerns."

And the data itself, verbatim:

> "Table 1 shows the total scans by month – the total license plate photographs made and stored each month (**2,591,990 total for the year**). Table 1 also shows the number of times the vehicle-based systems had a match ('hit') with a California Department of Justice (CA DOJ) database (**4,150 total for 2020**). OPD's very outdated ALPR system **can no longer quantify individual queries or perform any audit functions, as the software is no longer supported from the original vendor.**"

Also retrieved `https://oaklandprivacy.org/wp-content/uploads/2021/01/OPD-Surveillance-Technologies-with-Priority-List-123120.pdf` (HTTP 200, 3 pages) — a triage table with columns `Item | Description | Use Policy and Impact Report | Priority for bringing to PAC | Estimated Date to Bring to PAC | Annual Report`, covering ALPR, BWC, Cell Site Simulator, Cellphone Data Extraction Equipment, DNA Typing Technology, FLIR Camera (Boat / Helicopter / Portable Observation Tower), and more. It even preserves an editorial comment in the PDF: *"Commented [SB1]: Confirm this is FLIR tech"*.

Oakland's mandated annual-report fields, per the ordinance and reproduced in each report, include *"whether and how often data acquired through surveillance technology was shared with outside entities, including the name of recipient entities and types of data disclosed"* and *"identification of the race of each person subject to the technology's use"*.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) **Oakland's annual reports are a usage-data source, not merely an inventory.** 2,591,990 scans / 4,150 hits for 2020 is exactly the DD1/DD2 measurement, obtained without a records request. If ~26 CCOPS jurisdictions each publish this annually, SIG gets a small but *recurring, free* usage panel. (b) The Oakland ordinance requires **naming recipient entities** — i.e. the sharing edge list that Vigilant's Data Sharing Reports contain and the DD1 CSV does not (F3.4/F3.5). CCOPS annual reports are therefore a partial substitute for the 403-blocked DocumentCloud layer. (c) `oaklandca.gov` 403s to scripted clients: SIG's fetcher needs a documented policy for WAF-blocked government sites (respect the block; record `INACCESSIBLE`; prefer the advocacy mirror; never spoof aggressively). (d) OPD's admission that its system "can no longer quantify individual queries or perform any audit functions" is a first-class SIG claim — `audit_capability: none, self_reported` — and is precisely the kind of fact the dossier's `audit coverage` field exists to hold.
**Outline delta:** EXTENDS §10.1G and §15.1 — the outline's "audit coverage" field is conceived around Flock transparency portals; CCOPS annual reports are a second, independent source for it.

---

### F3.24 — New York City POST Act: 42 impact-and-use policies with a stable URL pattern — the most scrapable CCOPS artefact found

**Claim:** NYPD publishes 42 per-technology impact-and-use policies as PDFs on a consistent path, 40 of them redated 2026-02-04, each covering ten declared subject areas.
**Status:** VERIFIED
**Evidence:** `https://www.nyc.gov/site/nypd/about/about-nypd/policy/post-act.page` (HTTP 200, 45,752 bytes). **42 distinct PDFs** under `/assets/nypd/downloads/pdf/public_information/post-final/`; **40** carry the date token `2.4.26`, one is `4.11.23` (situational-awareness-cameras), one is `3-3-26` (transaction-intercept-tool). Technologies include: CALEA, CCTV Systems, Cell-Site Simulators, Criminal Group Database, Cryptocurrency Analysis Tools, Data Analysis Tools, Digital Cameras, Digital Fingerprint Scanning Devices, Digital Forensic Access Tools, **Domain Awareness System**, Drone Detection Systems, Electronic Record Management Systems, Facial Recognition, GPS Tracking Devices, Internet Attribution Management, **Iris Recognition**, License Plate Readers, Manned Aircraft Systems, Media Aggregation Services, Mobile X-Ray Technology, Portable Electronics Devices, Projectile GPS Tracking Device, Remote Control Robots (Submersible / Throwbots / Tactical), ShotSpotter, Situational Awareness Cameras, Social Network Analysis Tools, Thermographic Cameras, Unmanned Aircraft Systems, Transaction Intercept Tool.

The declared field schema, verbatim from the page:

> "The impact and use policies provide details of: 1) the capabilities of the Department's surveillance technologies, 2) the rules regulating the use of the technologies, 3) protections against unauthorized access of the technologies or related data, 4) **surveillance technologies data retention policies**, 5) public access to surveillance technologies data, 6) **external entity access to surveillance technologies data**, 7) Department trainings, 8) **internal audit and oversight mechanisms**, 9) health and safety reporting, and 10) **potential disparate impacts**."

**Retrieved:** 2026-08-20
**Implication for the spec:** NYPD alone accounts for a materially larger share of US policing than most of the other 25 CCOPS jurisdictions combined, and its 42 policies are the closest thing to a machine-enumerable CCOPS corpus: a single index page, a single directory, consistent filenames, and a synchronised revision date (2026-02-04) that acts as a version stamp. If SIG builds exactly one CCOPS connector, build it here. Fields 4, 6, 8 and 10 populate `retention`, `data sharing / outbound access`, `audit coverage` and the equity context respectively.
**Outline delta:** EXTENDS §21 — NYC POST Act is unregistered in the outline despite being the largest single-agency surveillance disclosure regime in the US.

---

### F3.25 — Cambridge, Madison, Nashville: the ordinance exists, the *inventory* does not (as a published artefact)

**Claim:** In three of the 26 CCOPS jurisdictions there is no standing inventory page at all; disclosure happens as individual items in the city-council legislative record.
**Status:** PARTIALLY VERIFIED
**Evidence:**
- **Cambridge MA** — ordinance is Municipal Code **Chapter 2.128, Surveillance Technology Ordinance** (`https://library.municode.com/ma/cambridge/codes/code_of_ordinances?nodeId=TIT2ADPE_CH2.128SUTEOR`). Disclosure vehicle is a **Surveillance Technology Impact Report (STIR)** transmitted by the City Manager to Council as a numbered communication, surfacing in the Granicus/IQM2 legislative record (e.g. `https://cambridgema.iqm2.com/Citizens/Detail_LegiFile.aspx?ID=24865`). Probed `https://www.cambridgema.gov/departments/informationtechnology/surveillancetechnology` and `https://www.cambridgema.gov/surveillance` — both **HTTP 404**. There is no standing inventory URL. Cambridge also *disapproved* continued ShotSpotter use under §2.128.060(C), which means the ordinance produces **negative** deployment facts SIG must be able to record.
- **Madison WI** — General Ordinance **23.63 "Use of Surveillance Technology"** and **23.64 banning facial recognition** (`https://library.municode.com/wi/madison/codes/code_of_ordinances?nodeId=COORMAWIVOIICH20--31_CH23OFAGPUPO_23.63USSUTE` and `…_23.64BAUSFASUTE`). Departments file an annual review to the Common Council Office, which compiles an Annual Surveillance Technology Report and transmits it by resolution. The city's own surveillance-adjacent page, `https://www.cityofmadison.com/information-technology/privacy-security/cameras` (HTTP 200), describes the Camera Management Lifecycle Program and links the two ordinances but **publishes no inventory**. `https://www.cityofmadison.com/police/surveillance` → **HTTP 404**.
- **Nashville TN** — ordinance BL2017-646, codified at Metro Code **13.08.080** ("Deployment of surveillance or electronic data collection devices"); Council approval required. Disclosure appears as Legistar items (e.g. `https://nashville.legistar.com/LegislationDetail.aspx?ID=8154627`) and one-off informational reports such as the **FUSUS** update `https://www.nashville.gov/sites/default/files/2024-11/NCRB-FUSUS-2024-Informational-Report-Update-RS2024-792-ADA.pdf`. No standing inventory page located.

**Status is PARTIALLY VERIFIED**: I confirmed the ordinances exist and that the obvious inventory URLs 404, but I did not exhaustively crawl each city's legislative system, so a standing inventory could exist at an unguessed path.
**Retrieved:** 2026-08-20
**Implication for the spec:** For roughly half the CCOPS jurisdictions the ingestion target is **the municipal legislative system, not a city web page** — Legistar, Granicus, IQM2, CivicClerk, Municode. This is good news, because those systems are consistent, keyword-searchable, and already the right target for §15.4's procurement watch and for the `authorization` block proposed in **F3.16**. One connector per legislative platform (~4 platforms) covers far more jurisdictions than one connector per city. Cambridge's ShotSpotter disapproval also proves SIG needs a `deployment_prohibited` / `technology_rejected` claim type, not just `deployed`.
**Outline delta:** EXTENDS §15.4 — reframes municipal-agenda scraping from "nice to have" into the primary CCOPS ingestion mechanism.

---

### F3.26 — No CCOPS jurisdiction publishes its inventory in a machine-readable format

**Claim:** Across every jurisdiction examined, the output format is PDF (or HTML prose, or a JPEG); zero surveillance inventories appear on any city open-data portal.
**Status:** VERIFIED
**Evidence:** Format census over what I actually retrieved:

| Jurisdiction | Artefact | Format | Cadence (observed) | Machine-readable? |
|---|---|---|---|---|
| ACLU (national list) | CCOPS jurisdiction map | **JPEG** | last revised 2024-11 | **no** |
| Seattle | Master List | PDF, 15pp | revised 2021-03, 2021-08, 2024-09, **2025-09** | no |
| Seattle | Surveillance Impact Reports | PDF, ~40pp each | per technology, ad hoc | no |
| Seattle | CTO Quarterly Determination Report | PDF, 260pp | **quarterly, current to 2026 Q2** | no |
| Seattle | Equity Impact Assessment | PDF | annual, 2019–2025 | no |
| San Francisco | Biannual Inventory Report | PDF, 11pp | **biannual, current to 2026-03-02** | no |
| Boston | Annual Surveillance Report | PDF, 87pp | annual, ~5–6 months late; latest = 2024 | no |
| Oakland | per-technology Annual Reports | PDF | annual per technology | no |
| New York City | 42 POST Act impact/use policies | PDF | revised en bloc 2026-02-04 | no |
| Cambridge / Madison / Nashville | STIRs / council resolutions | PDF inside legislative systems | per item | no |

Portal checks: Socrata catalogue API on `data.seattle.gov` for `q=surveillance` → 1 unrelated result. `data.sfgov.org` → 1 unrelated result. Neither city exposes a surveillance-technology dataset.
**Retrieved:** 2026-08-20
**Implication for the spec:** Every CCOPS connector is a **document pipeline**, not a data pipeline: fetch → snapshot → PDF-to-text → structured extraction (LLM-assisted, with the source PDF page retained as evidence) → human review. This is the same machinery §10 already specifies for procurement records (R4), so the marginal cost is low — but the throughput and error profile are those of document extraction, and every extracted field must carry a page-level citation into the archived PDF.
**Outline delta:** EXTENDS §10 and §11 — confirms CCOPS belongs in the records/document pipeline, not the structured-connector pipeline.

---

### F3.27 — Honest verdict on CCOPS as a source class

**Claim:** CCOPS is a **manual-to-semi-automated, depth-not-breadth** source class: 26 jurisdictions covering ~5% of the US population and ~0.14% of US law-enforcement agencies, but supplying field-level depth no other source has, for several of the largest and most-copied police departments.
**Status:** VERIFIED (as an assessment grounded in F3.19–F3.26)
**Evidence:** Synthesis of the above. The case *for*:
- The disclosures contain **exactly the fields SIG's dossier needs and cannot otherwise get**: named sharing partners (Oakland, Seattle SIR 6.1, NYPD field 6), acquisition and operating cost plus vendor freebies (Seattle Fiscal Impact 1.1–1.4), retention (all), audit mechanisms (all), deployment locations (Seattle RET 1.4), signage/visibility (Seattle PIA 4.6), effectiveness and complaints (Boston 3 and 5), and real usage counts (Oakland).
- Several regimes are **genuinely current**: Seattle 2026 Q2, SF 2026-03-02, NYPD 2026-02-04.
- Coverage is skewed towards the agencies that matter most for diffusion: NYPD, SFPD, SPD, BPD, Detroit, Boston.
- SF proves the disclosures also reveal **non-compliance** (26% in use without policy) — a finding class unavailable anywhere else.

The case *against*:
- **26 jurisdictions.** ~18M of ~335M people (5.4%); ~26 of ~18,000 agencies (0.14%). It will never be a national picture.
- **Zero machine-readable outputs.** No API, no CSV, no open-data-portal presence anywhere.
- **No upstream registry.** The canonical list is a JPEG on an ACLU page dated 2024-11.
- **Heterogeneous**: three different technology vocabularies observed (Seattle group-based, SF category-based, NYPD per-technology), different cadences (quarterly / biannual / annual), different scopes (police-only vs citywide), and different publication venues (dedicated site vs legislative record).
- **Late**: Boston runs 5–6 months past its statutory deadline.
- **Actively blocked** in at least one case (oaklandca.gov 403).

**Verdict:** ingest it, but as a **curated document corpus of ~30 sources**, not a programmatic feed. Recommended shape: (1) a hand-maintained 26-row jurisdiction register (F3.19); (2) **three** connectors that pay for themselves — Seattle (quarterly, richest), NYC POST (42 files, stable pattern), SF (biannual, citywide, has a compliance metric); (3) everything else via the legislative-platform scrapers already needed for §15.4. Expect ~150–200 technology-deployment records with unusually deep field coverage — roughly 1% of the Atlas's 15,185 rows by volume, but with perhaps 20× the fields per row. Its real value is as a **calibration set**: CCOPS jurisdictions are the only places where SIG can check its inferred picture against a legally compelled disclosure, which makes them the natural evaluation corpus for R13's reconciliation work.
**Retrieved:** 2026-08-20
**Implication for the spec:** Register CCOPS as source class `government_mandated_disclosure`, distinct from both `civil_society_dataset` and `vendor_portal`, with `licence: public record / no restriction`, `format: pdf`, `extraction: document_pipeline`, `coverage: 26 jurisdictions`, and an explicit note that its highest use is **evaluation and calibration**, not coverage.
**Outline delta:** **EXTENDS §2 and §21 with a source class the outline omits entirely**, and CONFIRMS the spec's decision to claim it — with the caveat that it must be scoped as depth, not breadth.

---
## State-level ALPR reporting mandates

*Note on provenance: this block was researched by a delegated agent whose successive reports
contradicted each other about what it had verified. I therefore re-fetched every load-bearing URL
and re-derived every number below myself; only independently confirmed facts are stated as
VERIFIED, and where I did not re-check something it is marked as such.*

### F3.28 — NCSL's ALPR statute table is the only national inventory of state ALPR law, and it has been frozen since **February 2022**

**Claim:** The National Conference of State Legislatures still publishes a state-by-state ALPR statute table, but at a different URL than the one usually cited, in HTML only, last updated **2022-02-03** — i.e. it predates the entire Flock expansion.
**Status:** VERIFIED
**Evidence:** `https://www.ncsl.org/technology-and-communication/automated-license-plate-readers-state-statutes` → **HTTP 200, 72,617 bytes**. (The URL cited in EFF's own DD2 article, `https://www.ncsl.org/research/telecommunications-and-information-technology/state-statutes-regulating-the-use-of-automated-license-plate-readers-alpr-or-alpr-data.aspx`, is dead.) The page text reads verbatim **"Updated February 03, 2022"**.

Structure: **one HTML `<table>`, 18 `<tr>` = 1 header + 17 statute rows**, two columns: `State | Year Enacted | Law` and `Summary`. The 17 rows cover **16 states** (California appears twice — Veh. Code § 2413 in 2011 and Civ. Code §§ 1798.29/1798.90.5 in 2015): Arkansas (2013), California (2011, 2015), Colorado (2014), Florida (2014), Georgia (2018), Maine (2009), Maryland (2014), Minnesota (2015), Montana (2017), Nebraska (2018), New Hampshire (2007), North Carolina (2015), Oklahoma (2016, 2017), Tennessee (2014, 2021), Utah (2013, 2014, 2020), Vermont (2013). No CSV, no API.
**Retrieved:** 2026-08-20
**Implication for the spec:** Usable as a **one-time seed** for the `legal_regime.state_alpr_statute` field proposed in **REQ-R3-37** — it is ~10 lines of scraping — but it must be labelled `as_of: 2022-02-03` and cannot be a live feed. Virginia's 2025 statute (**F3.30**) is absent from it, which is proof the table is stale. SIG will have to maintain this itself.
**Outline delta:** EXTENDS §21 — a source class (state statutory regime) the outline does not register at all.

---

### F3.29 — California: SB 34 is **deliberately decentralised** and produces no recurring dataset; the one dataset-like artefact is a 2020 State Auditor survey of 381 agencies

**Claim:** California's ALPR statute requires agencies to publish policies on their own websites and requires no central filing, so no state ALPR registry exists; the only structured statewide ALPR dataset ever produced is a one-off, self-reported, never-repeated 2019 survey published as an HTML table by the State Auditor.
**Status:** VERIFIED
**Evidence:** The statute (Civ. Code §§ 1798.90.5–.55, added by SB 34, 2015) contains no filing or central-registry clause; the AG's own bulletin directs agencies to post on their own sites. The one structured artefact:

`https://information.auditor.ca.gov/reports/2019-118/surveys.html` → **HTTP 200, 289,476 bytes**. Report title, verbatim from the page: *"Automated License Plate Readers — To Better Protect Individuals' Privacy, Law Enforcement Must Increase Its Safeguards for the Data It Collects. Report Number: 2019-118."*

I parsed the table directly: **384 `<tr>` = 381 agency rows**, six columns — `AGENCY | USES AN ALPR SYSTEM | SHARES ALPR INFORMATION | VENDOR | POLICY | DATA RETENTION PERIOD`. Measured distributions:

| Field | Distribution |
|---|---|
| `USES AN ALPR SYSTEM` | **YES 230 / NO 151** |
| `VENDOR` | blank 152, **Vigilant 137**, PIPS 30, Other 29, `Vigilant, PIPS` 14, `PIPS, Other` 5, `Vigilant, Other` 4, Genetec 3, `Vigilant, ELSAG` 2, `Vigilant, Genetec` 2 |
| `POLICY` | YES 220 / NO 9 / blank 152 |
| `DATA RETENTION PERIOD` | blank 154, `Between 6 months and 1 year` 76, `Between 1 year and 2 years` 56, **`Less than 1 day` 30**, `Between 2 years and 5 years` 29, **`Greater than 5 years` 19**, `6 months or less` 17 |

Note the retention field is a **bucketed ordinal vocabulary**, not a number, and it overlaps inconsistently (`6 months or less` vs `Between 6 months and 1 year`). The `VENDOR` field is multi-valued with comma separation — the same shape as the Atlas `Vendor` column (**F1.7**).

The 2023 AG bulletin `https://oag.ca.gov/system/files/media/2023-dle-06.pdf` → **HTTP 200, 279,308 bytes** (Bulletin 2023-DLE-06, 27 October 2023). Per the delegated agent, it imposes **no reporting duty** and produced no compliance dataset; I confirmed the PDF exists and is the right bulletin but **did not read it in full** — treat the "no reporting duty" characterisation as PARTIALLY VERIFIED. The agent also reported (unverified by me) that OpenJustice's bundle contains no ALPR references and that `data.ca.gov` returns zero ALPR datasets; and that the auditor's own recommendation tracker records the six **Legislature-directed** recommendations as four "Legislation Proposed But Not Enacted" and two "No Action Taken" — i.e. the recurring-oversight machinery was never enacted. Also flagged and **not verified by me**: the brief's `SB 210` and `AB 1814` bill numbers do not correspond to ALPR reporting bills.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The 2020 auditor survey is worth ingesting once — 381 agencies with vendor and retention, self-reported, `valid_as_of: 2019-08`, `method: self_report`, `never_repeated: true`. It is a **historical calibration snapshot** for California, comparable in role to Data Driven. (b) It is a second demonstration that retention arrives as an **ordinal bucket, not a duration** — SIG's retention model must accept both `duration` and `bucket` representations and must not fabricate a midpoint. (c) SB 34's decentralised design is the structural reason no state ALPR feed exists: SIG would have to crawl ~230 agency websites. That is a real project, not a connector.
**Outline delta:** EXTENDS §21 and §5.3.

---

### F3.30 — Virginia § 2.2-5517 is the strongest ALPR transparency mandate in the US, it is **publicly posted**, and its field list is almost exactly SIG's schema

**Claim:** Virginia's 2025 ALPR statute (effective 2026-07-01) requires every law-enforcement agency using ALPR to report nine enumerated data items annually **and to publicly post them**, with State Police aggregating them; first agency reports are due **2027-04-01** and the first aggregate **2027-07-01**.
**Status:** VERIFIED
**Evidence:** `https://law.lis.virginia.gov/vacode/title2.2/chapter55.6/section2.2-5517/` → **HTTP 200, 46,839 bytes**, Code of Virginia Title 2.2, **Chapter 55.6, Use of Automatic License Plate Recognition Systems**, § 2.2-5517, snapshot dated 8/20/2026 on the page itself. (Note: the statute is in Title 2.2, not Title 15.2 or 52.)

Subsection I, verbatim — the mandated annual report contents:

> "A law-enforcement agency that uses a system shall report to the Department of State Police **by April 1 of each year**… on its use of the system during the preceding calendar year, which shall include the following data:
> 1. **The total number of cameras owned or leased** by an agency as part of a system at the conclusion of each calendar year, including the number of such cameras designed to be affixed inside or on a motor vehicle, permanently affixed adjacent to a highway, or temporarily affixed…;
> 2. **A list of all state and federal databases with which the system data was compared**, unless the existence of any such database itself is not public;
> 3. **The total number of times the system was queried**, including the specific purposes of the queries… and the offense types for any criminal investigation;
> 4. The race, ethnicity, age, and gender of any individual identified as a suspect and charged… as a result of a query;
> 5. **The number of motor vehicles stopped based on notifications** from the system, including the specific reasons…;
> 6. The race, ethnicity, age, and gender of the driver of any motor vehicle stopped based on a notification;
> 7. **Whether the agency allows any other law-enforcement agencies to access its system data, and if so, which other agencies have been granted such access**;
> 8. **The number of identified instances of unauthorized use of or access to the system**, including the nature and circumstances of such instances; and
> 9. The number of subpoena duces tecum, search warrants, and any other requests received from a third party for system data or audit trail data, including the identity of the entity that requested [them]…"

> "**J.** The Department of State Police shall aggregate the data provided pursuant to subsection I and report it to the Governor, the General Assembly, and the Virginia State Crime Commission **by July 1 of each year**."

> "**K.** A law-enforcement agency that uses a system **shall publicly post** the policy set forth in subsection H and the report set forth in subsection I."

The statute also defines the terms SIG needs: `"Audit trail"` (records of queries and responses, with date/time, plate queried, specific purpose, case number, and **username of the person who queried**), `"Query"`, `"Notification"`, `"System data"`, and `"Publicly post"` (*"to post on a website that is maintained by the agency or on any other website on which the agency generally posts information and that is available to the public"*). Subsection M states verbatim that *"A notification by a system for purposes set forth in subsection D does not, by itself, constitute reasonable suspicion as grounds for law enforcement to stop a vehicle."*

The collection format spec exists: `https://vsp.virginia.gov/wp-content/uploads/2026/03/ALPR-Reporting-Requirements-v2-1.pdf` → **HTTP 200, 224,307 bytes** (I confirmed retrieval; I did not read it in full).
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the **single most important forward-looking source in this workstream**, and SIG should be architected for it now:
- Item 1 gives **camera counts by mount type** — the exact quantity SIG reconciles against OSM (Layer A) and portal-reported counts.
- Item 7 gives the **named outbound sharing edge list** — the thing DD1 could not supply (**F3.5**) and Flock portals supply inconsistently.
- Item 3 gives **query volume with purpose and offense type** — directly comparable to Have I Been Flocked's audit layer.
- Item 8 gives **self-reported misuse incidents** — an accountability-event feed of the same class as the ALPR Accountability Atlas, but statutorily compelled.
- Items 4 and 6 give demographics of people stopped, which addresses the equity question §15.1 currently cannot answer (**F3.16**, gap 5) *from disclosed data rather than inference* — the safe way to do it.
- Because subsection K requires **agency-level public posting** with no central portal, the ingestion shape is a **crawl of Virginia LEA websites** plus the VSP aggregate. SIG should build the Virginia jurisdiction register and crawler skeleton before 2027-04-01 so the first reporting cycle is captured as it lands.
**Outline delta:** **EXTENDS §2, §15.1 and §21 with a major source the outline does not anticipate.** It also validates the outline's data model: Virginia independently legislated almost exactly the field set SIG proposes to build.

---

### F3.31 — Illinois, Vermont, New Hampshire, Minnesota, Maryland: real mandates, but PDF or internal-only

**Claim:** Four other states have recurring ALPR reporting duties; only Illinois publishes an unbroken current series, and no state publishes machine-readable output.
**Status:** PARTIALLY VERIFIED (Illinois and Vermont verified by me; the rest relayed with the agent's citations)

**Evidence:**

**Illinois — the only unbroken current series.** The Tamara Clayton Expressway Camera Act (605 ILCS 140) requires an annual ISP report. `https://isp.illinois.gov/StaticFiles/docs/DII/FY26%20ALPR%20Annual%20Report-signed.pdf` → **HTTP 200, 515,523 bytes, 7-page PDF**, titled *"FY26 EXPRESSWAY CAMERA ACT ANNUAL REPORT — Illinois State Police, Division of Criminal Investigation."* It publishes **camera installations by county and fiscal year**, verbatim example: *"At the end of December 2022, 289 ALPR cameras were installed in Cook County (I-90 Kennedy, I-290 Eisenhower, I-55 Stevenson, I-94 Dan Ryan, Bishop Ford, and I-57)"*, followed by per-county installation tables for Dec2022–Jun2023 (total 59), FY24 (total 50), FY25 (total 160, across 17 counties) and FY26 (Champaign 27, Cook 48, DuPage 31, Sangamon 26, St. Clair 38, Will 20, …). Funding is documented too: an initial IDOT grant, a 2022 extension to 21 more counties plus DuSable Lake Shore Drive with **$20 million** from the IDOT Road Fund, and **$7 million** appropriated in Spring 2024. The agent reports FY22–FY25 reports are also HTTP 200 at the same directory, and that the Act **sunsets 2028-07-01** (§140/90) — **not verified by me**.

**Vermont — richest statutory text, broken publication.** 23 V.S.A. § 1607(d)(1), `https://legislature.vermont.gov/statutes/section/23/015/01607` → **HTTP 200, 69,798 bytes**. DPS must report annually **on or before January 15** with: (A) total ALPR units statewide, stationary count, count submitting to the state store; (B) readings submitted per agency and in total; (C) 18-month cumulative readings held; (D) requests to the Vermont Intelligence Center for historical data. The agent probed the report series and found only **2017** and **2019** PDFs returning 200 (`legislature.vermont.gov/assets/Legislative-Reports/2019-ALPR-Report.pdf`), with 2016, 2018 and 2020–2026 all 404 — **not verified by me**, but consistent with VSP having discontinued ALPR use in 2017.

**New Hampshire** — RSA 261:75-b(XI): agencies report annually **to the Commissioner** on devices in use, matches made, matches leading to stops, matches leading to searches, and outcomes. **There is no publication clause** — mandated collection, no public artefact. *(Agent-sourced; statute URL `https://www.gencourt.state.nh.us/rsa/html/XXI/261/261-75-b.htm` reported HTTP 200; not verified by me.)*

**Minnesota** — Minn. Stat. § 13.824, `https://www.revisor.mn.gov/statutes/cite/13.824` → **HTTP 200, 76,157 bytes** (I confirmed the statute page loads). Subd. 5 requires a public log; subd. 6(b) states the audit results are public. Publication is **decentralised per agency** with no central publisher. *(Subsection content agent-sourced; not read by me.)*

**Maryland** — Pub. Safety § 3-509(e) audit results, reported at `https://dlslibrary.state.md.us/publications/Exec/MDSP/PS3-509(e)_2023.pdf` (~24 MB scanned PDF). *(Agent-sourced; not verified by me.)*

**Colorado** — C.R.S. § 24-72-113 imposes retention limits and an internal log but **no public reporting**; a 2026 bill (SB26-070) was lost. *(Agent-sourced; not verified.)* **Correction relayed:** Illinois' *Freedom From Location Surveillance Act* (725 ILCS 168) **expressly excludes** ALPR — its §5 definition of "electronic device" excludes devices used *"for toll collection, traffic enforcement, or license plate reading"* — so it is not an ALPR source. *(Agent-sourced.)* **Not checked at all:** Washington, Utah, Maine, Nebraska.
**Retrieved:** 2026-08-20
**Implication for the spec:** Register Illinois as a small **recurring PDF connector** (annual, one agency, camera counts by county — directly reconcilable with OSM ALPR nodes in Illinois) and note its 2028 sunset. Register Vermont as a **latent** mandate with a broken series. Treat New Hampshire and Minnesota as *legal facts* populating `legal_regime` rather than as data sources. The general lesson: **statutory ALPR transparency in the US produces PDFs at best, and internal reports at worst** — with Virginia (**F3.30**) as the sole prospective exception.
**Outline delta:** EXTENDS §21.

---

## Academic and adjacent sources

### F3.32 — Monahan (2026) is paywalled, but the **dataset behind it is CC0 and downloadable** — and it is the richest Flock sharing-network artefact found in this workstream

**Claim:** The article the brief names has a different title and journal than assumed, is closed-access, and cites as its own supplement a 2.08 GB CC0 deposit of FOIA'd Flock audit logs whose "network-audit" files expose the search behaviour of **hundreds of agencies nationwide** obtained from two Illinois community colleges.
**Status:** VERIFIED (metadata, licence, schema and content counts all re-derived by me)
**Evidence:** Crossref `https://api.crossref.org/works/10.1177/20501579261453519`:

| Field | Value |
|---|---|
| **Title** | **"Grounding the Flock: Confronting Police Surveillance of Mobilities"** *(not "…and the Infrastructural Politics of Vehicle Surveillance")* |
| **Journal** | **Mobile Media & Communication** (SAGE), ISSN 2050-1579 / 2050-1587 — *not* Big Data & Society |
| **Author** | Torin Monahan, UNC Chapel Hill, ORCID `0000-0002-9055-399X` |
| **Published** | 2026-05-29, online-first; no volume/issue/pages |
| **References** | 45 |
| **Crossref licence** | `https://creativecommons.org/licenses/by-nc/4.0/`, content-version `vor`, delay-in-days **0** |

Unpaywall `https://api.unpaywall.org/v2/10.1177/20501579261453519`: `is_oa: false`, `oa_status: "closed"`, `has_repository_copy: false`, `oa_locations: []`. **This directly contradicts the Crossref CC BY-NC record** — Crossref advertises an open licence with zero embargo while no free copy exists anywhere. Full text is **INACCESSIBLE**: the agent reports SAGE `/doi/`, `/doi/pdf/`, `/doi/epub/`, `/doi/reader/` all return 403 Cloudflare, as do `r.jina.ai`, ResearchGate and the UNC repository; `torinmonahan.com` links only to the paywalled reader.

**Abstract, verbatim (from the Crossref JATS record):**

> "This article explores the integration of AI-surveillance functionality into urban infrastructures to question how the monitoring of mobilities could engender vulnerabilities, particularly for minoritized or stigmatized groups in society. Focusing on the automatic license plate recognition (ALPR) system deployed in the United States by the company Flock Safety, I show how this system acts as a communicative network that exposes people to discriminatory police surveillance. I argue that the network properties of Flock's system facilitate the application of far-right policing cultures across jurisdictions, allowing for unlawful targeting of women seeking reproductive care, immigrants, and vulnerable others irrespective of state or city prohibitions against such profiling. The article concludes by reflecting on countersurveillance efforts to expose Flock's surveillance network and challenge its discriminatory policing logics."

**The dataset.** `https://dataverse.unc.edu/api/datasets/:persistentId/?persistentId=doi:10.15139/S3/KQTPLP` → HTTP 200. Metadata I read directly:

| Field | Value |
|---|---|
| Title | **Flock Audit Logs from US Institutions of Higher Education in Illinois** |
| DOI | `10.15139/S3/KQTPLP` (UNC Dataverse) |
| Author | Monahan, Torin — University of North Carolina at Chapel Hill |
| **Licence** | **CC0 1.0** (`rightsIdentifier: CC0-1.0`) — public domain |
| Version | 1.2, RELEASED **2026-07-08T21:25:25Z** |
| Files | **67** — 33 `Audit` + 34 `Network-Audit` |
| Total size | **2,079,753,348 bytes (~2.08 GB)**; network-audit files alone = 2,079,379,645 bytes (99.98%) |
| Range | monthly windows, June 2024 – October 2025; Joliet Junior College IL PD and Lincoln Land Community College IL PD |

Description, verbatim: *"Flock audit logs from US institutions of higher education in Illinois. Logs were obtained from public institutions through public-records requests filed in 2025. **License plate numbers have been redacted** to protect those subjected to police surveillance."*

I downloaded two files via `https://dataverse.unc.edu/api/access/datafile/{id}?format=original` (no auth required, HTTP 200):

- **Agency audit** (id 7559446, 19,111 bytes) — **120 records**, one org.
- **Network audit** (id 7559448, 1,909,752 bytes — the *smallest* of the 34) — **13,165 records**.

**Schema, identical in both, 13 columns:**

```
Name | Org Name | Total Networks Searched | Total Devices Searched | Time Frame |
License Plate | Reason | Case # | Filters | Search Time | Search Type | Text Prompt | Moderation
```

Content of the single smallest network-audit file, measured by me:

| Measure | Value |
|---|---|
| **Distinct `Org Name`** | **645 agencies** |
| Top orgs | Joliet IL PD 1,800; Houston TX PD 1,708; Lakeland FL PD 344; Dallas TX PD 322; Sauk Village IL PD 254; Fairfax County VA PD 242; Illinois State Police 236; Naperville IL PD 217 |
| Distinct state tokens in org names | ~38 |
| `Search Type` | `lookup` 8,557 · `search` 4,580 · `convoy` 27 · `visual` 1 |
| `Reason` (free text, top values) | `inv` 1,591 · `stolen` 874 · `wanted` 344 · `invest` 339 · `investigation` 317 · `robbery` 211 · `warrant` 191 · `STOLEN` 181 |

Other data sources cited in the article's 45 references, per the agent's extraction of the Crossref reference list (**not verified by me**): DeFlock (`deflock.me`), **EFF Street-Level Surveillance** ALPR page, a Flock patent (US 11,416,545 B1), several Flock Safety corporate blog posts, and heavy **404 Media** investigative reporting. Notably **no EFF Atlas of Surveillance citation**.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is a major, unregistered, immediately ingestible source, and it changes three things.
1. **A FOIA request to a small agency yields the whole network's behaviour.** Because Flock's "network audit" surfaces every *other* agency's searches against the host's cameras, two Illinois community colleges expose 645 agencies across ~38 states. SIG's records-request strategy (§10, R4) should explicitly target **small, FOIA-friendly agencies inside large sharing networks** rather than large agencies — the leverage is inverted from the intuition.
2. **`Search Type` is a real controlled vocabulary** (`lookup`, `search`, `convoy`, `visual`) and `convoy` in particular is a capability SIG's Flock model should represent. `Total Networks Searched` / `Total Devices Searched` quantify the reach of each individual query.
3. **`Reason` is catastrophically unnormalised free text** — `inv` / `invest` / `investigation` are the same reason, and `stolen` / `STOLEN` differ only in case. Any SIG metric over search justifications MUST normalise case and expand abbreviations, and MUST publish the normalisation map, because "what reasons do police give" is exactly the kind of claim that will be quoted.
4. **Privacy**: plates are redacted but the `Name` column contains **individual officer names**. If SIG ingests this, officer names must be treated as personal data under §13 — pseudonymise or aggregate before publication, even though the upstream licence is CC0 and imposes no such duty.
5. Licence is **CC0 1.0** — the least restrictive source in this entire workstream. Redistribution is unconditionally permitted (subject to point 4).
**Outline delta:** **EXTENDS §2 Layer C and §21 with a new source the outline does not contain**, and CORRECTS the brief's citation of the article (wrong title, wrong journal).

---

### F3.33 — Adjacent accountability projects: all alive, none holds surveillance-technology inventory data

**Claim:** The five adjacent projects the brief names are all live in 2026, but none of them carries agency→surveillance-technology inventory data; the best structured ALPR sources remain EFF (CC BY) and OpenStreetMap (ODbL).
**Status:** PARTIALLY VERIFIED (liveness re-checked by me; data-content claims relayed from the delegated agent and flagged)

**Evidence:** Liveness probes I ran myself, 2026-08-20:

| Project | URL | My result | Structured data (agent-reported, unverified by me) | Inventory data? |
|---|---|---|---|---|
| **Police Data Accessibility Project** | `https://pdap.io/` | **HTTP 200** | API requires auth; docs at `docs.pdap.io`. Agent pulled the record-types taxonomy and found **zero** matches for surveillance / ALPR / plate / camera — 5 categories, none technological | **NO — hard negative** |
| **OpenOversight** | `https://openoversight.com/` | **HTTP 200** | per-department CSV export; no API | NO — officer rosters |
| — repo | GitHub API | `lucyparsonslabs/OpenOversight` **404**; **`lucyparsons/OpenOversight` 200**; **`OrcaCollective/OpenOversight` 200** | two live repos exist; the `lucyparsonslabs` path is dead | — |
| **Citizens Police Data Project** | `https://www.policingproject.org/` *(see below)* / `cpdp.co` | `api.cpdp.co/api/v2/officers/1/` **404** on my probe | agent reports a public no-auth API plus a GitHub LFS bulk mirror (`invinst/chicago-police-data`), **no LICENSE file** | NO — complaints and officers |
| **Policing Project (NYU)** | `https://www.policingproject.org/` | **HTTP 200** | PDF only; **ALPR Policy Scorecard** at `https://alprscorecard.com/` (**HTTP 200**, 1,966 bytes — a JS shell), ~25 jurisdictions × 7 criteria embedded in a bundle | **Policy scores, not inventory**. Agent could not find any published Policing Project Flock audit — **treat as non-existent until shown otherwise** |
| **Stop LAPD Spying** | `https://stoplapdspying.org/` | **HTTP 200** | *Automating Banishment: The Surveillance and Policing of Looted Land* (2021) at `automatingbanishment.org`; agent reports 8 CSVs under `/map/data/` — **my probe of the directory returned HTTP 403** (listing disabled; individual files may still resolve) | NO — predictive policing / Operation LASER, not ALPR |
| **DeFlock** *(R1/R2 territory, noted for completeness)* | `deflock.me` | agent: **403** to all automation; `github.com/FoggedLens/deflock` **HTTP 200** via API | OSM-backed; agent ran an Overpass query for `man_made=surveillance` + `surveillance:type=ALPR` in the US and got **133,669 nodes**, ODbL | camera locations — R1's layer |

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) **Do not plan on PDAP for surveillance technology** — its taxonomy structurally excludes it; adding it would be an upstream schema change, which is a *collaboration* opportunity (§19) rather than an ingestion path. (b) Fix any outline reference to `lucyparsonslabs/OpenOversight`; the live repos are `lucyparsons/OpenOversight` and the `OrcaCollective` fork. (c) The **ALPR Policy Scorecard** (`alprscorecard.com`) is a genuinely relevant, unregistered artefact — jurisdiction × policy-criterion scores are exactly the `legal_regime` / policy-quality dimension **REQ-R3-37** needs, and it should be registered as a source even though it is a JS bundle. (d) Register the whole group as `related_project, no_ingestion` in the source registry so future passes do not re-litigate them.
**Outline delta:** EXTENDS §21 and §19 — the outline names none of these five.

---

## Open questions

**OQ-R3-01 — Can the DD1 Data Sharing Reports be extracted at all?**
The 463 DocumentCloud URLs in the DD1 CSV, and both project search pages, return HTTP 403 to a
scripted client (**F3.5**). I tested the DocumentCloud API unauthenticated
(`api.www.documentcloud.org/api/documents/…`, `/api/projects/38044/`, `/api/documents/search/`) and
all three return a Cloudflare bot interstitial. Whether an **authenticated** token unblocks project
38044/38217 is untested. Until someone tests it, SIG cannot know whether the Vigilant sharing
*edge list* (as opposed to the sharing *degree*) is recoverable. **Hedge:** design the
Vigilant layer so that `direct_sharing_count` is a first-class scalar attribute that does not
depend on edges existing; treat the edge list as an optional enrichment.

**OQ-R3-02 — Is DD1's `Direct Sharing` count directional?**
The DD1 field description says "Number of agencies listed on the Data Sharing Report or similar
document that shows who the agency is sharing ALPR data with" — singular and outbound-sounding.
But the underlying report has four sections (**F3.4**). It is unresolved whether the CSV integer
is outbound-detections-only or a merge. **Hedge:** ingest it as `sharing_partners_reported_count`
with `direction: unspecified`, never as `outbound_degree`.

**OQ-R3-03 — Is there a maintained CCOPS jurisdiction list anywhere?**
The only list found is a JPEG last revised 2024-11 (**F3.19**). Between Nov 2024 and Aug 2026,
jurisdictions may have adopted or repealed CCOPS laws. **Hedge:** SIG's register must carry
`as_of` and `verified_by` per row, and the count must be presented as "at least 26".

**OQ-R3-04 — Do Cambridge, Madison, Nashville publish standing inventories at unguessed URLs?**
I confirmed the obvious paths 404 but did not crawl their legislative systems exhaustively
(**F3.25**). **Hedge:** the legislative-platform connector approach is robust to the answer either way.

**OQ-R3-05 — What are the ACLU's actual reuse terms?**
No open licence appears on any ACLU page examined; I did not read the full user agreement
(**F3.18**). **Hedge:** link-only default for ACLU material; re-derive rather than copy.

**OQ-R3-06 — Which technology does SIG treat as canonical when Atlas and SLS disagree on granularity?**
F3.10 proposes SLS-shaped parents with Atlas children, but this is a design recommendation, not a
verified upstream fact — EFF has not reconciled the two (**F3.13**). **Hedge:** publish the crosswalk
as a versioned reviewable artifact rather than burying it in code.

**OQ-R3-07 — Can Seattle's 260-page quarterly determination reports be reliably extracted?**
The reports contain a per-request determination table across ~105 items per quarter (**F3.20**), but
I read only the first three pages. Table structure and consistency across quarters are untested.
**Hedge:** treat the first connector build as a spike; do not commit to a quarterly SLA before
validating extraction on four consecutive quarters.

**OQ-R3-08 — Is the ACLU stingray dataset worth reviving?**
It is 2018 data, withdrawn, unlicensed (**F3.17**). Whether SIG should mirror an archived copy of an
organisation's *deliberately removed* page is a §13 ethics question, not a technical one.
**Hedge:** raise with the ACLU before ingesting; the Atlas's 83 cell-site-simulator rows already
give partial coverage without the ethical question.

**OQ-R3-09 — How stale is "annual" in practice across CCOPS jurisdictions?**
Boston runs 5–6 months late (**F3.22**); Seattle is current (**F3.20**). One data point each way.
**Hedge:** compute and display `mandated_due` vs `published_at` rather than assuming a cadence.

**OQ-R3-10 — Will Virginia agencies actually publicly post?**
§ 2.2-5517(K) requires agency-level public posting with no central portal (**F3.30**). Whether
agencies comply, and in what format, is unknowable until the first cycle (agency reports due
2027-04-01, VSP aggregate 2027-07-01). **Hedge:** build the Virginia jurisdiction register and a
crawler skeleton now, but do not commit spec surfaces to Virginia data before the first cycle lands;
plan for the VSP aggregate to be the reliable artefact and agency postings to be patchy.

**OQ-R3-11 — Is Monahan's article actually CC BY-NC?**
Crossref records a `vor` licence of CC BY-NC 4.0 with zero embargo; Unpaywall reports
`is_oa: false, oa_status: closed, oa_locations: []` (**F3.32**). One of the two is wrong. This matters
only for quoting the article, not for the dataset (which is unambiguously CC0). **Hedge:** cite the
abstract (which is openly available via Crossref) and the dataset; do not reproduce article text.

**OQ-R3-12 — Several state findings rest on a single delegated pass.**
The state-mandate block (**F3.28–F3.31**) was researched by a delegated agent whose successive
reports contradicted each other about what it had verified. I re-fetched and re-derived everything
load-bearing (NCSL, the California auditor survey, Illinois FY26, Virginia § 2.2-5517, Vermont
§ 1607, Minnesota § 13.824, the Monahan metadata and dataset), but New Hampshire, Maryland,
Colorado, and the Illinois-sunset and California-recommendation-tracker details are relayed, not
verified — and Washington, Utah, Maine and Nebraska were never checked. **Hedge:** treat every
agent-relayed line in F3.29/F3.31/F3.33 as PARTIALLY VERIFIED and re-check before it becomes
load-bearing in the spec.

**OQ-R3-13 — Does a published Policing Project Flock audit exist?**
The Axon/Flock audit that is widely referred to could not be located on `policingproject.org`
(**F3.33**). **Hedge:** do not cite it; if SIG needs it, ask the Policing Project directly.

---

## Spec requirements emitted

Requirements below cover the **whole file**, F1.x through F3.x.

### Atlas ingestion and vocabulary (from F1.x)

- **REQ-R3-01** — The Atlas connector MUST fetch the bulk CSV from `https://www.atlasofsurveillance.org/download.csv`, not the URL advertised on the Atlas map page, and MUST fail loudly rather than silently falling back if that path changes. *(F1.1)*
- **REQ-R3-02** — The loader MUST validate the Atlas CSV against its declared column set on every run, and MUST treat the four permanently-empty declared columns as expected-empty rather than as ingestion failures. *(F1.3)*
- **REQ-R3-03** — SIG's Atlas source vocabulary MUST contain exactly the 12 canonical technology slugs, keyed on **slug** not display label, plus an explicit `ATLAS_MALFORMED` quarantine bucket; the 6 `FRT` rows MUST route to quarantine and MUST NOT create a 13th category. *(F1.4)*
- **REQ-R3-04** — The loader MUST parse the `NEWAOSNUMBER (ORI9)` identifier and retain the finer-grained technology/vendor vocabulary encoded in it as a secondary classification, since it is strictly more specific than the `Technology` column. *(F1.5)*
- **REQ-R3-05** — `Type of Juris`, `Type of LEA` and `Vendor` MUST be ingested as free text with a normalisation layer, never as enums; `Vendor` MUST be treated as multi-valued and case-insensitive, and its 346 observed distinct strings MUST be resolved through R5's entity-resolution path rather than string equality. *(F1.6, F1.7)*
- **REQ-R3-06** — All 26,304 Atlas evidence URLs MUST be stored as citations with their source domain; SIG MUST NOT assume any of them is fetchable, and MUST record per-URL fetch status rather than dropping unfetchable citations. *(F1.8, F3.5)*
- **REQ-R3-07** — Every SIG surface that displays Atlas-derived data MUST carry the Atlas's own "not a complete inventory" qualification, and MUST NOT present Atlas row counts as deployment counts. Atlas rows are **agency-technology adoption assertions**, one per pair. *(F1.9, F1.15)*
- **REQ-R3-08** — SIG MUST NOT ingest coordinates from the Atlas map layer; the Atlas has no coordinates of its own and its map is third-party geocoding that EFF itself flags as error-prone. Physical geometry MUST come from Layer A. *(F1.10)*
- **REQ-R3-09** — Atlas attribution MUST read "EFF Atlas of Surveillance, CC BY 4.0", and SIG MUST NOT redistribute Atlas rows that originate in third-party imported datasets without checking the upstream licence. *(F1.12)*
- **REQ-R3-10** — SIG MUST implement an outbound correction path to the Atlas via its three documented channels, and MUST record correction submissions as first-class events with their outcome. *(F1.13)*
- **REQ-R3-11** — The loader MUST detect and report divergence between the Atlas glossary and the Atlas data (currently two known mismatches) as a data-quality signal rather than silently preferring one. *(F1.14)*

### EFF Data Library (from F2.x)

- **REQ-R3-12** — The Data Library register in SIG MUST contain all 42 entries, not the outline's 15, each with `retrievability_status` re-tested on a schedule. *(F2.1, F2.2)*
- **REQ-R3-13** — Where a Data Library dataset carries a technology vocabulary broader than the main Atlas, SIG MUST preserve that source vocabulary rather than downcasting to the 12 Atlas categories. *(F2.3)*
- **REQ-R3-14** — Matrix-shaped sources (e.g. *Who Has Your Face?*) MUST be normalised to one claim per cell on ingest, with the matrix's own axis labels retained as provenance. *(F2.4)*
- **REQ-R3-15** — Ring/Neighbors data MUST be modelled as a closed historical layer with a hard `valid_to`, flagged `source_no_longer_maintained`; SIG MUST NOT build a live Ring connector. *(F2.5)*
- **REQ-R3-16** — Any free-text field originating from a records request MUST pass a pre-publication PII screen; SIG MUST support replacing a published artifact in place with a column-reduced version while preserving claim identity; and SIG MUST document a takedown path that can terminate in un-hosting. *(F2.6)*
- **REQ-R3-17** — Default posture for high-risk record sets is **mirror privately, publish metadata publicly**. Public mirroring requires an explicit per-source decision recorded in the source register. *(F2.6, F3.17)*

### EFF Data Driven / Vigilant layer (from F3.1–F3.8)

- **REQ-R3-18** — The Data Driven connector MUST resolve the current bulk ZIP by scraping `https://www.eff.org/pages/download-alpr-dataset` for the ZIP href, rather than hard-coding `…/2020/01/28/alpr_2016-2017_update.zip`, because corrections produce a new dated path. *(F3.1)*
- **REQ-R3-19** — DD1's three documented missing-data sentinels (`n/a`, `Not Provided`, `Data Incomplete`) MUST map to three distinct epistemic states in SIG and MUST NOT be collapsed to NULL; `Not Provided` specifically MUST be representable as an **agency refusal to disclose**, a first-class accountability claim. *(F3.2, F3.3)*
- **REQ-R3-20** — DD1 `See <agency>` values MUST be ingested as aliasing/parent-system edges, not as nulls. *(F3.2)*
- **REQ-R3-21** — ALPR data-sharing MUST be modelled with both direction and kind — `{detections, hotlists} × {inbound, outbound}` — because both Vigilant's LEARN reports and Flock's sharing model distinguish them. A single scalar "shares with N agencies" MUST NOT be the only representation. *(F3.4)*
- **REQ-R3-22** — SIG MUST support a **pooled/opaque sharing counterparty** node type (e.g. Vigilant NVLS) representing an edge to an unenumerable set, with a stated cardinality estimate and no fabricated member edges. *(F3.4)*
- **REQ-R3-23** — Every usage-volume claim (scans, hits, searches) MUST carry an explicit `observation_window`; SIG MUST refuse to sum or compare volumes across incommensurable windows (e.g. Vigilant annual totals vs Flock 30-day totals). *(F3.6)*
- **REQ-R3-24** — The spreadsheet loader MUST detect embedded totals rows — a populated numeric row with a blank identifier column is the canonical signature — and MUST quarantine rather than aggregate them. *(F3.7)*
- **REQ-R3-25** — Per-row data-quality notes present in a source (e.g. DD2 sheet 4) MUST be preserved verbatim on the resulting claims. *(F3.7)*
- **REQ-R3-26** — SIG's field dictionary MUST include a plain-language explanation for every derived metric, following DD2's `Formula in plain language` column, so that derived numbers are auditable by non-technical users. *(F3.6)*
- **REQ-R3-27** — Wherever a source states the size of its own universe (e.g. "89 agencies … more than 250 agencies use ALPR in California"), SIG MUST display coverage as a fraction of that universe. *(F3.7)*
- **REQ-R3-28** — Data Driven attribution MUST read "EFF and MuckRock, Data Driven / Data Driven 2, CC BY 4.0", with source documents attributed to the originating agency; the correction channel MUST be recorded as **manual, personal email** (`dm@eff.org`), not automatable. *(F3.8)*

### Technology taxonomy and the SLS crosswalk (from F3.9–F3.13)

- **REQ-R3-29** — SIG MUST carry **both** EFF vocabularies as distinct source vocabularies: Atlas (12 terms) and Street-Level Surveillance (16 terms), each keyed on slug. *(F3.9)*
- **REQ-R3-30** — SIG MUST publish a versioned, human-reviewable crosswalk artifact (`sig_term, atlas_slug, sls_slug, mapping_type ∈ {exactMatch, broadMatch, narrowMatch, relatedMatch, noEquivalent}, note`), because no upstream reconciliation exists. *(F3.10, F3.13)*
- **REQ-R3-31** — The SIG technology hierarchy MUST make `surveillance_camera_network` a parent of `camera_registry`, `real_time_crime_center` and `video_analytics`, and `biometric_surveillance` a parent of `face_recognition` with declared-but-unpopulated siblings (`dna`, `iris`, `tattoo`, `gait`). `fusion_center` MUST be retained despite having no SLS equivalent. *(F3.10)*
- **REQ-R3-32** — The dossier's `missing_evidence` section MUST enumerate technology classes for which SIG has **no ingested source** — currently at least: community surveillance apps, electronic monitoring, forensic extraction tools, police access to IoT devices, police databases beyond commercial platforms, real-time location tracking. *(F3.10)*
- **REQ-R3-33** — Each SIG technology page MUST link the canonical SLS explainer in both English (`sls.eff.org/technologies/<slug>`) and Spanish (`/es/technologies/<slug>`), under CC BY attribution; SIG MUST NOT mirror SLS images, which carry independent third-party credits. *(F3.11, F3.12)*
- **REQ-R3-34** — SIG's vendor ontology SHOULD seed `technology → known_vendors` from the SLS "Who Sells It" sections, tagged `source=SLS, extraction=manual`, and MUST include the ten ALPR vendors named by the ACLU: Flock Safety, Axon, Vigilant Solutions (Motorola Solutions), Genetec, PlateSmart, Innova Systems, Rekor, ELSAG, Perceptics, Jenoptik. *(F3.11, F3.15)*

### The local dossier (from F3.14–F3.16, F3.20–F3.24)

- **REQ-R3-35** — §15.1's dossier MUST add an `authorization` block: `{approving_body, decision_date, vote_tally, was_consent_agenda, public_comment_held, agenda_url, minutes_url}`. This is the highest-priority addition; it converts the dossier from description into a procedural handle. *(F3.16)*
- **REQ-R3-36** — §15.1's `contracts` field MUST be extended to a `termination` block: `{expires, auto_renews, notice_period_days, termination_for_convenience, next_decision_date}`, and the dossier MUST surface `next_decision_date` — not `expires` — as the actionable date. *(F3.16)*
- **REQ-R3-37** — §15.1 MUST add a `legal_regime` block: `{state_alpr_statute, local_surveillance_ordinance, ordinance_requires_council_approval, applicable_model_bill}`, so that the dossier tells an advocate which lever exists in their jurisdiction. *(F3.16, F3.19, F3.28–F3.31)*
- **REQ-R3-38** — §15.1 MUST add `effectiveness` (claimed justification and any efficacy evidence) and `complaints` (community complaints received), both of which are compelled disclosures under CCOPS regimes and neither of which is in the outline's field list. *(F3.16, F3.22)*
- **REQ-R3-39** — §15.1 SHOULD add `peer_precedent` (comparable jurisdictions that cancelled or rejected, with date and rationale). *(F3.14, F3.16)*
- **REQ-R3-40** — Any `siting_equity` analysis (demographic characterisation of camera placement) MUST be gated by §13 ethics review before implementation and MUST NOT be shipped as an unreviewed automated inference. *(F3.16)*
- **REQ-R3-41** — SIG MUST support a `technology_rejected` / `deployment_prohibited` claim type; CCOPS regimes produce negative deployment facts (e.g. Cambridge's ShotSpotter disapproval) that a deployment-only model cannot represent. *(F3.25)*
- **REQ-R3-42** — Where a source discloses an agency's *inability* to audit (e.g. Oakland's "can no longer quantify individual queries or perform any audit functions"), SIG MUST record it as a structured `audit_capability` claim, not as free-text prose. *(F3.23)*

### CCOPS and government-mandated disclosure (from F3.19–F3.27)

- **REQ-R3-43** — SIG MUST maintain a hand-curated CCOPS jurisdiction register (~26 rows: `jurisdiction, state, entity_type, ordinance_citation, effective_date, inventory_url, inventory_format, oversight_body, as_of, verified_by`), because no machine-readable upstream exists. The count MUST be displayed as "at least N". *(F3.19)*
- **REQ-R3-44** — SIG's jurisdiction model MUST accommodate non-municipal entities — transit districts (BART) and counties (Santa Clara County) both hold CCOPS laws. *(F3.19)*
- **REQ-R3-45** — SIG's organisation model MUST allow surveillance deployments to attach to **any** government agency, not only law enforcement: SF inventories libraries, museums, airports, transit, public health and elections; Boston inventories public schools. *(F3.21, F3.22)*
- **REQ-R3-72** — Extraction from mandated-disclosure documents MUST distinguish three states per field: `field_absent` (the source has no such field), `field_present_but_empty` (the mandated template was filed blank — e.g. Seattle's ALPR SIR leaves acquisition and operating cost tables unfilled), and `field_answered`. Collapsing the middle state into "unknown" hides a compliance failure. *(F3.20)*
- **REQ-R3-46** — SIG MUST register `government_mandated_disclosure` as a distinct source class with `format: pdf`, `extraction: document_pipeline`, `licence: public record`, and every extracted field MUST carry a page-level citation into an archived copy of the source PDF. *(F3.26)*
- **REQ-R3-47** — Build exactly three first-party CCOPS connectors — Seattle (quarterly, richest), NYC POST Act (42 files, stable path pattern), San Francisco (biannual, citywide, publishes a compliance metric) — and route all other jurisdictions through the municipal legislative-platform scrapers (Legistar, Granicus, IQM2, Municode) already required by §15.4. *(F3.20, F3.21, F3.24, F3.25, F3.27)*
- **REQ-R3-48** — SIG MUST compute and display a **compliance-gap metric** where a source supports it (e.g. SF's "26% of surveillance technologies in use without an approved policy"). *(F3.21)*
- **REQ-R3-49** — For every recurring mandated disclosure, SIG MUST store `mandated_due_date` alongside `published_at` and display the delta; a late statutory report is itself an accountability finding. *(F3.22)*
- **REQ-R3-50** — SIG's fetcher MUST have a documented policy for WAF-blocked government hosts: respect the block, record `INACCESSIBLE` with the exact status, prefer a documented third-party mirror (e.g. oaklandprivacy.org), and never escalate evasion. *(F3.23)*
- **REQ-R3-51** — CCOPS-derived records MUST be usable as R13's **reconciliation evaluation corpus**: where a CCOPS jurisdiction has published a legally compelled inventory, SIG MUST be able to diff its own inferred picture against it and report precision/recall. This is the primary justification for the source class. *(F3.27)*
- **REQ-R3-52** — Municipal-agenda monitoring MUST search consent-agenda sections specifically, using ALPR/vendor keyword lists; consent agendas are the documented mechanism by which ALPR contracts pass without debate. *(F3.15)*

### Archival, decay, and licence hygiene (cross-cutting)

- **REQ-R3-53** — SIG MUST snapshot every external source on first ingest and on every subsequent successful fetch. Three of the three historical civil-society datasets examined in this workstream have decayed (Ring, CalECPA, ACLU stingray map); decay is the base case, not the exception. *(F2.5, F2.6, F3.17)*
- **REQ-R3-54** — Where a source has been **deliberately withdrawn** by its publisher (ACLU stingray map; EFF CalECPA), SIG MUST NOT republish an archived copy without an explicit recorded decision under §13, even where an archived copy is technically retrievable. *(F2.6, F3.17)*
- **REQ-R3-55** — Every source in the register MUST carry: licence name, URL of the licence statement, whether the terms were **seen or inferred**, attribution string, and redistribution permission. Sources with no open licence (all ACLU material) MUST default to link-only. *(F1.12, F3.8, F3.12, F3.18)*
- **REQ-R3-56** — Claims derived from an archived snapshot MUST carry `retrieved_from: web.archive.org`, the snapshot timestamp, and `source_status: withdrawn|live`, and MUST be visually distinguished from live-sourced claims in the UI. *(F3.17)*

### State mandates, academic deposits, and adjacent projects (from F3.28–F3.33)

- **REQ-R3-57** — SIG MUST maintain a `state_alpr_statute` register seeded once from NCSL's table (17 rows / 16 states, `as_of: 2022-02-03`) and thereafter maintained in-house; the NCSL table MUST NOT be treated as current, since it predates Virginia's 2025 statute. *(F3.28)*
- **REQ-R3-58** — SIG's retention model MUST accept **both** a duration and an ordinal bucket (e.g. California's `Less than 1 day` … `Greater than 5 years`), MUST preserve the source's bucket boundaries verbatim, and MUST NOT synthesise a midpoint duration from a bucket. *(F3.29)*
- **REQ-R3-59** — The 2020 California State Auditor survey (381 agencies × 6 fields) MUST be ingested as a one-off historical snapshot stamped `valid_as_of: 2019-08`, `method: self_report`, `never_repeated: true` — never as current state. *(F3.29)*
- **REQ-R3-60** — SIG MUST build the Virginia § 2.2-5517 jurisdiction register and crawler skeleton **before 2027-04-01**, targeting agency-level public postings plus the VSP aggregate due each July 1. Its nine mandated items map directly onto SIG fields: camera counts by mount type → device counts; named agencies granted access → outbound sharing edges; query counts by purpose/offense → usage; unauthorized-access instances → accountability events; stop demographics → equity context. *(F3.30)*
- **REQ-R3-61** — Where equity/demographic context is available as **disclosed data** (Virginia items 4 and 6), SIG MUST prefer it over any inferred demographic characterisation of camera siting. *(F3.30, F3.16, REQ-R3-40)*
- **REQ-R3-62** — Register the Illinois Expressway Camera Act annual report as a recurring PDF connector (annual, one publisher, per-county camera installation counts reconcilable against OSM ALPR nodes), with an explicit note of the Act's reported 2028-07-01 sunset. *(F3.31)*
- **REQ-R3-63** — Statutes that mandate reporting **to an official rather than to the public** (New Hampshire) MUST be recorded as `legal_regime` facts, not as data sources, so that SIG never implies a public artefact exists where it does not. *(F3.31)*
- **REQ-R3-64** — SIG MUST ingest the Monahan CC0 Flock audit-log deposit (DOI `10.15139/S3/KQTPLP`, 67 files, ~2.08 GB, 13 columns) and MUST model its two file classes distinctly: `Audit` = host-agency searches, `Network-Audit` = **other agencies' searches against the host's cameras**. *(F3.32)*
- **REQ-R3-65** — SIG's records-request strategy MUST prioritise **small, FOIA-responsive agencies inside large sharing networks**, because network-audit exports expose the whole network's search behaviour: two Illinois community colleges yielded 645 agencies across ~38 states. *(F3.32)*
- **REQ-R3-66** — `Search Type` MUST be modelled as a controlled vocabulary including `lookup`, `search`, `convoy`, `visual`; `convoy` search is a distinct Flock capability SIG must be able to represent. *(F3.32)*
- **REQ-R3-67** — Free-text search-justification fields MUST be normalised (case-folding plus an abbreviation expansion map: `inv`/`invest`/`investigation`; `stolen`/`STOLEN`), and the normalisation map MUST be published alongside any aggregate over it. *(F3.32)*
- **REQ-R3-68** — Officer names appearing in audit logs MUST be treated as personal data under §13 — pseudonymised or aggregated before publication — regardless of the upstream licence permitting redistribution (the Monahan deposit is CC0 and imposes no such duty). *(F3.32)*
- **REQ-R3-69** — The source registry MUST record `related_project, no_ingestion` entries for PDAP, OpenOversight, Citizens Police Data Project, Policing Project and Stop LAPD Spying, with the reason (none carries surveillance-technology inventory data) and the corrected repo path `lucyparsons/OpenOversight` (the `lucyparsonslabs` path is 404). PDAP's record-type taxonomy containing no surveillance/ALPR type SHOULD be raised with PDAP as a §19 collaboration item rather than worked around. *(F3.33)*
- **REQ-R3-70** — Register the NYU Policing Project **ALPR Policy Scorecard** (`alprscorecard.com`, ~25 jurisdictions × 7 policy criteria) as a source for the `legal_regime` / policy-quality dimension, noting that its data is embedded in a JS bundle and requires bundle extraction rather than an API. *(F3.33)*
- **REQ-R3-71** — Every finding relayed from a delegated research pass rather than independently retrieved MUST be marked as such in the source registry with a `verification: relayed` flag, and MUST be re-verified before it becomes load-bearing in the design spec. *(F3.29, F3.31, F3.33; OQ-R3-12)*

