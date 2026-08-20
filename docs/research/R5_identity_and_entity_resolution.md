# R5 — Canonical Identity and Entity Resolution

**Workstream:** R5
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (research agent R5)
**Outline sections covered:** §6.1, §8.1, §10.1A (Phase 1A), §11.2, §19.6, §20
**Outline questions answered:** Q9, Q10, Q11, Q12, Q27, Q28, Q29, Q37
**Confidence in this file overall:** high

---

## 0. Headline recommendations

Stated up front so the design agent can skim. Every claim below is backed by a numbered
finding with a fetched URL.

| Decision | Recommendation | Finding |
|---|---|---|
| Best canonical U.S. LE agency identifier | **ORI9** (FBI CJIS 9-char Originating Agency Identifier), obtained from the **FBI Crime Data Explorer `agency/byStateAbbr/{ST}` API** on api.usa.gov (free key), reconciled against the **LEAIC** crosswalk for ORI↔FIPS | F5.1, F5.9 |
| Second-best / fallback | **EFF Atlas `NEWAOSNUMBER (ORI9)` column** — Atlas *already* publishes ORI9 for every row and mints `XX%07d` surrogates where no ORI exists | F5.11 |
| Jurisdiction identity | **Census GEOID** (state 2 / county 5 / place 7 / cousub 10 / tract 11 / block 15), joined to **GNIS feature_id** via Census `ANSICODE` — verified 32,332/32,333 join rate | F5.18, F5.22 |
| ER stack | **Splink 4 (MIT) on DuckDB** for probabilistic scoring + **PostgreSQL `pg_trgm`/`fuzzystrmatch`** for blocking and online lookup; deterministic cascade in SQL; **no Senzing** ($58.5k/yr at 10M records) | F5.33, F5.38, F5.39 |
| Public ID scheme | `sig:org:01J8...` — prefixed, typed, **UUIDv7-derived Crockford-base32 surrogate with an ISO/IEC 7064 check character**, dereferenceable at `https://id.<sigdomain>/org/<id>`, with tombstones + 301/303 redirects on merge | F5.45, F5.46, F5.47 |
| Temporal identity | **ROR + RiC-O hybrid**: immutable surrogate ID, `status ∈ {active, inactive, withdrawn}`, plus valid-time-qualified `succeeded_by` / `merged_into` / `split_into` / `same_as` edges modelled as first-class n-ary relation records | F5.41, F5.43 |

**The single most important empirical result in this file:** on the FBI agency
universe, a normalized agency name **alone** is ambiguous for 31.26% of agencies, but
`(normalized_name, state)` is ambiguous for only **0.02%**, and
`(normalized_name, state, county)` is **100% unique**. That is the quantitative
justification for the deterministic tier boundaries in §D.3.

---

# A. U.S. law-enforcement agency identity (Q9, Q10)

## A.1 ORI — the FBI CJIS Originating Agency Identifier

### F5.1 — The FBI Crime Data Explorer publishes a machine-readable ORI + agency registry, free, no registration required to test

**Claim:** `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{STATE}` returns a
county-keyed JSON object of law-enforcement agencies with exactly ten fields including
ORI9, agency name, agency type, county, and lat/lon; it works with the public
`DEMO_KEY` and returns 17,891 agencies across the 44 jurisdictions successfully
retrieved.
**Status:** VERIFIED
**Evidence:**
- `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/DE?API_KEY=DEMO_KEY` → HTTP 200.
  Both `API_KEY=` and `api_key=` query parameters work.
- Downloaded all 51 state/DC responses; 44 succeeded before the DEMO_KEY daily quota
  was exhausted (see F5.2). Parsed result:
  - **17,891 agency rows, 17,891 distinct ORIs, zero duplicates.**
  - **All ORIs are exactly 9 characters.**
  - Exact field set (present on 100% of rows):
    `ori, counties, is_nibrs, latitude, longitude, state_abbr, state_name, agency_name, agency_type_name, nibrs_start_date`
  - `is_nibrs = true` for 14,867 / 17,891 (83.1%).
  - `agency_type_name` distribution:
    `City 10,537 | County 2,807 | Other State Agency 1,356 | Other 1,227 | State Police 938 | University or College 884 | Tribal 142`
- Response shape is `{"<COUNTY NAME>": [ {agency}, ... ], ...}` — the top-level keys are
  **county names, not FIPS codes**, and a single agency's `counties` value can be a
  multi-county string.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the primary connector for Phase 1A. It is a
per-state pull (51+ calls, or 56 including territories), trivially incremental, and
requires no scraping. The response must be flattened county-key → row, and the
county-name key must be re-coded to a FIPS county code by a separate join (the API does
not provide FIPS).
**Outline delta:** EXTENDS §10.1A — the outline lists "ORI identifiers where available"
as a vague "identity aid". It is in fact a complete, free, structured national API. It
should be the *first* connector built, not an aid.

### F5.2 — DEMO_KEY on the CDE endpoint is limited to 10 concurrent-window requests; a real key is free and gives 1,000/hr

**Claim:** api.data.gov's documented DEMO_KEY limits are 30 req/IP/hour and 50
req/IP/day; the CDE service returns `x-ratelimit-limit: 10`. A registered key is free
and gives 1,000 req/hr by default.
**Status:** VERIFIED
**Evidence:**
- `https://api.data.gov/docs/developer-manual/` (fetched, HTTP 200): "Hourly Limit:
  1,000 requests per hour"; "The rate limits for the DEMO_KEY are: Hourly Limit: 30
  requests per IP address per hour. Daily Limit: 50 requests per IP address per day."
  Key may be passed as `X-Api-Key` header, `api_key` query param, or HTTP Basic
  username.
- Live response headers from
  `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/NJ?API_KEY=DEMO_KEY` after
  quota exhaustion: `x-ratelimit-limit: 10`, `x-ratelimit-remaining: 0`, body
  `{"error":{"code":"OVER_RATE_LIMIT", ...}}`.
- Signup: `https://api.data.gov/signup/` (HTTP 200 but a JS-rendered form — the form
  itself was not machine-readable). Registration is free, requires name + email, and
  issues a 40-character key.
**Retrieved:** 2026-08-20
**Implication for the spec:** The connector MUST accept an `API_DATA_GOV_KEY`
environment variable and MUST handle HTTP 429 with `Retry-After`/hourly backoff. Do not
ship DEMO_KEY in production. At 1,000/hr a full 56-jurisdiction refresh is one minute of
budget; a nightly refresh is trivially affordable.
**Outline delta:** EXTENDS §10.1A — adds an operational constraint the outline does not
mention.

### F5.3 — CDE coverage could not be verified for 7 jurisdictions; the 17,891 figure is a floor, not the national total

**Claim:** NJ, NM, OK, RI, UT, WA and WY were not retrieved before the DEMO_KEY daily
quota was exhausted; their agency counts are unknown from direct observation.
**Status:** PARTIALLY VERIFIED
**Evidence:** All seven returned HTTP 429 `OVER_RATE_LIMIT` on both the initial parallel
burst and a later retry. Indirect evidence that these states *do* have CDE ORIs: the EFF
Atlas ORI9 column contains 973 NJ-prefixed, 192 WA, 145 OK, 90 UT, 86 NM, 72 RI and 36
WY ORIs in the canonical `SSCCCNNNN` form (F5.11).
**Retrieved:** 2026-08-20
**Implication for the spec:** Publish agency counts only after a full-quota run with a
registered key. The ingestion job MUST assert per-state non-empty results and fail loudly
rather than silently recording a state as having zero agencies — a silent 429 is
indistinguishable from "this state has no agencies" if the parser is naive. This is a
real bug class: the first pass of this very research made that mistake.
**Outline delta:** EXTENDS §9.4 (negative claims) — "state X has no agencies" derived
from a rate-limited API is a false negative claim; the connector must distinguish
`absent` from `not observed`.

### F5.4 — ORI structure: 9 characters, but the state prefix is the *UCR* state code, which differs from USPS for at least Nebraska and Guam

**Claim:** ORI9 is `[UCR state code (2)][agency code (7)]`; the dominant pattern is
`AA9999999` where positions 3–5 are a UCR county code and positions 6–7 an agency
sequence, terminated by `00`. Nebraska agencies use the prefix **NB**, not NE.
**Status:** VERIFIED
**Evidence:**
- Empirical pattern census over 17,891 ORIs (letters→`A`, digits→`9`):
  `AA9999999 16,019 | AA999999A 479 | AA999AA99 428 | AAAAA9999 378 | AA999AA9A 184 | AA999A99A 140 | AA9999A99 90 | AAAA99999 87 | AA999A999 31 | AA9999A9A 21 | AAAAA999A 16 | AAAA9999A 9`
- Terminal 2 characters: `00` for 16,893; `0X` 643; `9E` 169; then a long tail.
- **Prefix ≠ `state_abbr` for exactly one state in the retrieved data: Nebraska
  (`state_abbr = NE`, ORI prefix = `NB`), 287 agencies.** No other mismatch in 44
  jurisdictions.
- The CDE Angular bundle (`https://cde.ucr.cjis.gov/LATEST/webapp/main.da07c277921d8ee6.js`)
  embeds the territory list with `{"abbr":"GM","name":"Guam"}` — UCR uses **GM** where
  USPS uses GU. Territories AS, GM, MP, PR, VI are enumerated in the app.
- Non-conforming ORIs are real and common: `ILCPD0000` = Chicago Police Department,
  `GAAPD0000` = Atlanta PD, `AZDI06100`. Any regex validator of the form
  `^[A-Z]{2}\d{7}$` will reject legitimate ORIs.
- ORI semantics (per FBI/state CJIS guidance surfaced by search:
  `https://site.utah.gov/dps-tac/wp-content/uploads/sites/38/2017/10/ORI.pdf`,
  `https://www.justice.gov/tribal/page/file/1247566/dl`): 9 alphanumeric characters
  assigned by FBI CJIS; first two = state; last two positions encode agency type, with
  **law-enforcement ORIs ending `00`** and **non-law-enforcement (civil/applicant) ORIs
  ending in an alpha character**.
**Retrieved:** 2026-08-20
**Implication for the spec:**
1. ORI validation MUST be `^[A-Z0-9]{9}$`, not a state-prefix + digits pattern.
2. A `ucr_state_code ↔ usps_state_code` lookup table is a required reference dimension.
   Do not assume `ori[0:2]` is a USPS code.
3. The 9th character is a *type* discriminator — an ORI ending in `00` is an operational
   LE agency; one ending in an alpha is likely a civil/applicant-fingerprinting ORI and
   MUST NOT be treated as a surveillance-operating agency without corroboration.
**Outline delta:** EXTENDS §8.1 — the outline field list says only "ORI / government
identifiers"; it must be typed and validated, and the UCR/USPS state-code divergence is
a silent-corruption hazard.

### F5.5 — CDE latitude/longitude are frequently parent-organization centroids, not agency addresses

**Claim:** 14.2% of CDE agencies have null coordinates and 44.4% share their exact
coordinate pair with at least one other agency; the shared coordinates are the parent
department's headquarters, not the reporting unit's location.
**Status:** VERIFIED
**Evidence:** Over the 17,891 rows: 2,540 rows (14.2%) have `latitude = null`. Counting
distinct `(lat, lon)` pairs, **44.36% of agencies sit at a coordinate shared by more
than one agency.** The single most-repeated coordinate, `(30.423128, -84.28066)`
(Tallahassee, FL), is assigned to **62 agencies, all of which are "Division of
Alcoholic Beverages and Tobacco: <County> County"** — i.e. 62 county field offices all
pinned to the state agency HQ. Runners-up: `(37.798763, -122.24971)` ×46,
`(38.34613, -81.63015)` ×45.
**Retrieved:** 2026-08-20
**Implication for the spec:** CDE coordinates MUST NOT be used as the agency's address
or for spatial joins to jurisdiction boundaries. Store them as a low-confidence
`approximate_location` claim with `source = FBI CDE` and an explicit
`geometry_precision = organization_centroid_or_unknown` flag. Agency-to-jurisdiction
assignment must come from the LEAIC FIPS crosswalk or from name parsing + Census
Geocoder on a real street address, never from these points.
**Outline delta:** CORRECTS §11.2 — the outline's device-attribution workflow proposes
"location within jurisdiction X" reasoning. If the agency's own location is a state
capitol centroid, naive point-in-polygon attribution will assign devices to the wrong
agency. Jurisdiction attribution must use boundary polygons, not agency points.

### F5.6 — CDE agency names are FBI-normalized and diverge from agencies' legal self-names

**Claim:** The CDE name field is a canonical form imposed by the UCR program: all 2,765
sheriff agencies are rendered "…Sheriff's Office" and none as "Sheriff's Department",
even where the legal name is "Department"; abbreviations (PD, Dept., Twp) never appear.
**Status:** VERIFIED
**Evidence:** Regex census over 17,891 names:
- ends "Police Department" 10,451; ends "Sheriff's Office" 2,765; ends
  "Sheriff's Department" **0**.
- occurrences of `\bPD\b` **0**; `\bDept\b` **0**; `\bTwp\b` **0**; `\bDPS\b` **0**;
  `Police Dept` **0**; non-ASCII characters **0**.
- `City of` appears in **2** names; `Town of` in **2**. The FBI strips the governmental
  prefix.
- `CA0190000 = "Los Angeles County Sheriff's Office"` — the agency's own legal and
  operational name is *Los Angeles County Sheriff's Department* (LASD).
- 3,086 names (17.2%) contain a colon, encoding a two-level hierarchy
  `Parent: Child`. Most frequent left-hand sides:
  `State Police (463) | Highway Patrol (276) | Independent School District (251) | State Patrol (152) | State Park Rangers (116) | Department of Natural Resources (102) | Bureau of Forestry (68) | Union Pacific Railroad (54) | State Fire Marshal (54)`.
- 563 names contain "Township"; 314 "Constable"; 330 "School District"; 557
  "University"; 136 "Marshal"; 291 "Village".
- Trailing disambiguators occur: `"Pulaski Township Police Department, Lawrence County"`.
**Retrieved:** 2026-08-20
**Implication for the spec:** The CDE name is a **registry name**, not the
**self-identified name**. `Organization` must carry at minimum:
`canonical_name` (SIG's chosen display form), `registry_name` (FBI CDE), and
`aliases[] {value, source, valid_from, valid_to}`. Matching a Flock portal slug
`la-county-ca-sd` or a contract naming "Los Angeles County Sheriff's Department" against
the CDE string will fail on exact comparison and must go through normalization (§D.2).
The colon pattern MUST be parsed into `parent_organization` + local unit — 3,086
agencies are sub-units of ~200 parent departments, and treating them as peers will
badly distort any network statistic (directly the risk §19.6 warns about).
**Outline delta:** EXTENDS §8.1 — `aliases[]` in the outline is untyped. It needs
per-alias provenance and validity, because the FBI alias and the legal alias are both
"correct" at the same time from different sources.

### F5.7 — Quantified name ambiguity: name alone is unusable; name+state is near-unique; name+state+county is unique

**Claim:** Over the FBI agency universe, normalized-name collisions affect 31.26% of
agencies nationally, 0.02% within state, and 0% within state+county.
**Status:** VERIFIED
**Evidence:** Normalization applied: NFKD → ASCII fold → lowercase → strip apostrophes →
collapse non-alphanumerics to single spaces → trim. Over 17,891 agencies:

| Key | Rows in a collision | % | Distinct colliding keys |
|---|---|---|---|
| `normalized_name` | 5,593 | **31.26%** | 1,691 |
| `(state, normalized_name)` | 4 | **0.02%** | 2 |
| `(state, county, normalized_name)` | 0 | **0.00%** | 0 |

Worst national collisions: `washington county sheriffs office` ×27,
`jefferson county sheriffs office` ×23, `jackson county sheriffs office` ×22,
`franklin county sheriffs office` ×22, `lincoln county sheriffs office` ×19. The only two
in-state collisions are `(MA, tufts university worcester)` and
`(FL, department of corrections office of the inspector general desoto county)`.
`"Phoenix Police Department"` exists in AZ, IL **and** OR.
**Retrieved:** 2026-08-20
**Implication for the spec:** This directly sets the cascade tier boundaries (§D.3).
`normalized_name + state` may auto-write; bare `normalized_name` may never auto-write.
The two known in-state collisions must be seeded as an explicit exclusion list in the
matcher's test fixtures.
**Outline delta:** EXTENDS §20 Q27 ("Which matches can be deterministic?") with a
measured answer instead of a guess.

### F5.8 — ORI does not cover non-law-enforcement entities, and there is no public authoritative full ORI issuance list

**Claim:** ORIs are issued by FBI CJIS to entities authorized to access Criminal Justice
Information, including many non-LE civil-purpose ORIs; no complete public issuance
register is published, and Flock/Fusus network participants such as HOAs, malls,
apartment complexes and private security firms will never have one.
**Status:** PARTIALLY VERIFIED
**Evidence:**
- The CDE agency endpoint is a **UCR-reporting** list, not the CJIS issuance register. It
  intrinsically covers only agencies that report (or are expected to report) crime data.
- Per state CJIS documentation surfaced by search
  (`https://site.utah.gov/dps-tac/wp-content/uploads/sites/38/2017/10/ORI.pdf`;
  `https://omnixx.dps.ms.gov/OMNIXX5/DOCUMENTS/NCIC.OP/ORI.htm`;
  `https://codes.ohio.gov/ohio-administrative-code/rule-4501:2-10-01`), ORIs are issued
  per-agency by FBI CJIS via the state CJIS Systems Agency, and civil/applicant ORIs are
  routinely issued to schools, hospitals, licensing boards and private employers for
  fingerprint-based background checks. Those ORIs end in an alpha character and are
  **not** in the UCR list.
- The historical published directory is NLETS' *ORI Directory*
  (`https://www.ojp.gov/ncjrs/virtual-library/abstracts/national-law-enforcement-telecommunications-systems-ori-originating`)
  — a law-enforcement-restricted product, not open data.
- Direct attempt to locate a bulk public ORI register on cde.ucr.cjis.gov: the downloads
  manifest at
  `https://cde.ucr.cjis.gov/LATEST/webapp/assets/JSON/downloads/downloads.json`
  (HTTP 200, 10,024 bytes) lists 8 datasets — SRS estimates, LEOKA, Law Enforcement
  Employees (`lee_1960_2025.csv`), and others — but the S3 base URL is injected at
  runtime (`https://s3-us-gov-west-1.amazonaws.com/s3_Bucket:/…` placeholder in the
  bundle) and could not be resolved without executing the app. `fbi.gov` UCR pages return
  403 to non-browser clients.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Do not make ORI the primary key of `Organization`.** ORI
is an *external identifier with partial coverage*, stored in a `sameAs`/identifier table.
Every organization gets a SIG-minted surrogate (§E). Non-LE participants in
Flock/Fusus networks get the same surrogate treatment with a different identifier stack
(§C).
**Outline delta:** CONFIRMS §20 Q10's premise and CORRECTS the §10.1A framing, which
implies ORI can serve as the backbone of the registry. It can serve as the backbone for
~18–19k LE agencies only.

## A.2 The LEAIC crosswalk — the highest-value identity artifact, and the hardest to get

### F5.9 — LEAIC (ICPSR 35158) is the definitive ORI↔FIPS↔Census-place crosswalk, is public domain, and is NOT programmatically retrievable

**Claim:** The Law Enforcement Agency Identifiers Crosswalk maps each ORI to FIPS state /
county / place codes and the Census Governments Integrated Directory government ID; it is
U.S. public domain; but every ICPSR endpoint is behind a Cloudflare JS challenge that
returns HTTP 403 to all automated clients.
**Status:** PARTIALLY VERIFIED (metadata verified; data file INACCESSIBLE)
**Evidence:**
- **Inaccessible:** every one of these returned **HTTP 403** with a Cloudflare
  "Just a moment… Enable JavaScript and cookies to continue" interstitial, from both
  `curl` with a full browser UA + cookie jar + navigation `Sec-Fetch-*` headers and from
  the WebFetch tool:
  `https://www.icpsr.umich.edu/web/NACJD/studies/35158`,
  `…/35158/summary`, `…/35158/datadocumentation`,
  `https://www.icpsr.umich.edu/icpsrweb/NACJD/studies/35158`,
  `https://www.icpsr.umich.edu/icpsrweb/ICPSR/ddi25/studies/35158`,
  `https://www.icpsr.umich.edu/web/NACJD/studies/36697` (LEAR 2016),
  `https://www.icpsr.umich.edu/web/NACJD/studies/38771` (CSLLEA 2018),
  `https://www.openicpsr.org/openicpsr/project/100707`.
- **DOI resolves**, confirming the study and version exist:
  `https://doi.org/10.3886/ICPSR35158.v2` → 301 →
  `https://www.icpsr.umich.edu/web/NACJD/studies/35158/versions/V2` (then 403).
- **Metadata verified via third parties:**
  - Stanford SearchWorks `https://searchworks.stanford.edu/view/13649499` (HTTP 200):
    "Law Enforcement Agency Identifiers Crosswalk, United States, 2012"; scope = "State
    and local police agencies, police reporting entities, and NCIC access points across
    the United States, based on the 2008 Census of State and Local Law Enforcement
    Agencies"; publication date 2015; **most recent version released 2018-09-18**;
    "Available to the general public".
  - data.gov record for the 1996 edition,
    `https://catalog.data.gov/dataset/law-enforcement-agency-identifiers-crosswalk-united-states-1996`
    (HTTP 200): publisher **Bureau of Justice Statistics**; **license "public domain",
    `http://www.usa.gov/publicdomain/label/1.0/`**; access level public; resource DOI
    `https://doi.org/10.3886/ICPSR02876.v1`; fields include "UCR originating agency
    identifier number", "agency name and mailing address", "Census Bureau's government
    identification number", "UCR state and county codes", and "Federal Information
    Processing Standards (FIPS) state, county, and place codes"; contact
    `askbjs@usdoj.gov`.
  - Harvard Dataverse metadata harvest confirms the LEAIC series and its versions:
    `doi:10.3886/ICPSR35158.V2` (published 2025-04-03), `…V1` (2024-10-20),
    plus editions 1996 (`ICPSR02876`), 2000 (`ICPSR04082`), 2005 (`ICPSR04634`). Harvard
    holds **metadata only** — `GET /api/datasets/:persistentId/?persistentId=doi:10.3886/ICPSR35158.V2`
    returned `status: ERROR` with no files.
  - ICPSR series page: `https://www.icpsr.umich.edu/web/ICPSR/series/366`.
- **Coverage year:** the 2012 edition (the latest) is built on the **2008** CSLLEA. There
  has been no LEAIC edition covering the 2018 CSLLEA.
**Retrieved:** 2026-08-20
**Implication for the spec:**
1. LEAIC is a **manual-acquisition dependency**. The spec must define a documented
   human step: log into ICPSR (free account, public-use file), download the delimited
   file, place it in a content-addressed `raw/` store, and record its DOI + version +
   SHA-256. It cannot be an automated connector.
2. Because the data are U.S. public domain, **SIG may redistribute the crosswalk**. Doing
   so — publishing a maintained, downloadable, public-domain `ORI → GEOID` table — is
   arguably the single highest-leverage public good this project can ship, and it does
   not currently exist in accessible form.
3. LEAIC is **stale (2008 vintage universe)**. Agencies created, dissolved or merged
   since 2008 are absent. It must be treated as a Tier-C source with `valid_to` semantics,
   and reconciled against the live CDE list; ORIs present in CDE but absent from LEAIC
   need FIPS assignment by a secondary method.
**Outline delta:** EXTENDS §10.1A substantially — the outline names "Census geographic
identifiers" and "ORI identifiers" as separate aids and does not mention that a
government-published crosswalk between them exists. It also CORRECTS the implicit
assumption that identity sources are fetchable: the most valuable one is not.

### F5.10 — CSLLEA / LEAR: authoritative agency rosters, infrequent, same access barrier

**Claim:** BJS's Census of State and Local Law Enforcement Agencies has been fielded only
in 1992, 1996, 2000, 2004, 2008 and 2018; the underlying master list is the Law
Enforcement Agency Roster (LEAR), a continuously-updated internal working file whose only
public release is LEAR 2016 (ICPSR 36697).
**Status:** VERIFIED (metadata); data files INACCESSIBLE
**Evidence:**
- `https://bjs.ojp.gov/data-collection/census-state-and-local-law-enforcement-agencies-csllea`
  (HTTP 200, fetched): years fielded "1992, 1996, 2000, 2004, 2008, and 2018"; the 2018
  round "mailed forms to nearly 20,000 agencies potentially operating nationwide";
  reference date 2018-06-30; statistical tables published **October 2022**; datasets
  archived at NACJD series `https://www.icpsr.umich.edu/web/NACJD/series/169`; the master
  list for 2018 came from the **BJS Law Enforcement Agency Roster (LEAR)**.
- LEAR 2016 = ICPSR 36697; CSLLEA 2018 = ICPSR 38771 (both 403, see F5.9). Per search
  results, "The LEAR is a working file that is updated as new agency information is
  received. The 2016 LEAR reflects what was deemed current as of December 2016."
- `https://bjs.ojp.gov/data-collection/law-enforcement-management-and-administrative-statistics-lemas`
  HTTP 200 — LEMAS is a *sample survey* of agency management practice, not a census, and
  is therefore useless as an identity register.
**Retrieved:** 2026-08-20
**Implication for the spec:** Cadence is **~decadal**, so CSLLEA/LEAR can never be the
live registry. Their value is (a) a second opinion on the agency universe circa 2018 for
computing CDE's coverage gaps, and (b) historical `valid_from`/`valid_to` evidence for
agencies that existed in 2008/2016/2018 and no longer appear in CDE — which is precisely
the dissolution/absorption signal §D.5 needs.
**Outline delta:** CORRECTS §10.1A — LEMAS is *not* an identity source and should not be
listed alongside census products; CSLLEA is, but at decadal cadence.

## A.3 Existing surveillance datasets already carry ORI — a significant correction

### F5.11 — EFF Atlas of Surveillance publishes ORI9 for 100% of rows and mints surrogates where no ORI exists

**Claim:** The Atlas CSV's second column is literally named `NEWAOSNUMBER (ORI9)` and
contains an ORI9 concatenated with a technology code; 81.3% of rows resolve to a current
FBI CDE ORI, and the remainder use documented surrogate schemes.
**Status:** VERIFIED
**Evidence:** Downloaded `https://atlasofsurveillance.org/download.csv` — HTTP 200,
8,579,798 bytes, `content-type: text/csv`, **15,185 data rows**, 28 columns:
```
AOSNUMBER, NEWAOSNUMBER (ORI9), City, County, State, Agency, Type of LEA, Summary,
Type of Juris, Technology, TECH ABV, Vendor, Link 1..3 (+ Snapshot/Source/Type/Date), Other Links
```
- The column is populated on **15,185 / 15,185 rows (0 blank)**.
- Structure = `ORI9` + technology suffix. Suffix census:
  `BWC 5,465 | ALPR 4,136 | UAV 1,826 | FRT 892 | TPIPCT 763 | CR 755 | GDT 248 | RTCC 240 | TPIPACC 206 | PRPO 200 | VA 85 | CSS 83`.
- Taking the first 9 characters: **9,043 distinct ORI9 candidates**, of which **7,069
  (78.2%) exactly match an ORI in the FBI CDE list retrieved in F5.1**; at the row level,
  **12,338 / 15,185 (81.3%)** resolve. The largest non-matching prefixes correspond
  exactly to the seven states not retrieved from CDE (NJ 973, WA 192, OK 145, UT 90, NM
  86, RI 72, WY 36) — so true agreement is materially higher than 78.2%.
- **Surrogate scheme:** 921 rows use `XX0000NNN` for entities with no ORI. Examples:
  `XX0000125 Burnet County Constables (TX)`, `XX0000051 Gloucester County Animal Control
  Department (VA)`, `XX0000691 Miami-Dade Corrections and Rehabilitation (FL)`. One row
  falls back to the legacy `AOSNUMBER`: `AOS015201 Virgin Islands Police Department`.
- Atlas ships its own org-type taxonomy in two columns.
  `Type of Juris`: `Municipal 10,749 | County 3,226 | University 438 | Statewide 297 | Tribal 140 | Regional 97 | Judicial District 46 | Parish 43 | School District 37 | Federal 21 | Airport 20 | State 16 | Parks 7 | Special District 6 | Health System 6`.
  `Type of LEA`: `Police 11,577 | Sheriff 3,006 | State Police/Highway Patrol 133 | District Attorney 100 | Fusion Center 88 | DMV 36 | Prosecutor's Office 32 | Parking Enforcement 21 | Corrections 18 | Court 18 | CBP 17 | Park Rangers 12 | Constables 11 | State-Local Partnership 10`.
- Data quality caveat: **45 `(State, Agency)` pairs map to more than one ORI9**
  (e.g. `TX Burnet County Constables`, `NY Poughkeepsie Police Department`,
  `CO Aurora Police Department`, `GA Savannah Police Department`) — mostly precinct-level
  splits and city/town homonyms.
**Retrieved:** 2026-08-20
**Implication for the spec:** The Atlas connector must key on `NEWAOSNUMBER[0:9]`, not on
`Agency` name. This turns Atlas ingestion (§10.1C) from a fuzzy-matching problem into a
**deterministic Tier-1 join** for 81%+ of rows. The remaining `XX…`/`AOS…` rows go
straight to the surrogate-minting path in §C. Atlas's `Type of Juris` × `Type of LEA`
cross-product is also a ready-made, real-world-tested seed for SIG's `organization_type`
vocabulary and should be adopted-then-extended rather than invented.
**Outline delta:** **CORRECTS §6.1.** The outline states that "Flock organization
identifiers may not match … EFF agency names; ORI codes" and lists these as separate,
unlinked namespaces. In fact EFF Atlas *is already ORI-keyed*, and the ORI↔Atlas link is
a solved problem. The real unsolved links are Flock-slug↔ORI and OSM-operator↔ORI.

### F5.12 — Wikidata is not a viable identity hub for U.S. law enforcement: ~1,755 agencies, and no ORI property exists

**Claim:** Wikidata contains roughly 1,755 U.S. law-enforcement agencies (≈10% of the
FBI universe), and there is **no Wikidata property for ORI**; the most common external
identifier on those items is Freebase.
**Status:** VERIFIED
**Evidence:** All queries executed against
`https://query.wikidata.org/sparql` with `Accept: application/sparql-results+json`
(HTTP 200 in every case):
- `SELECT (COUNT(DISTINCT ?x)) WHERE { ?x wdt:P31/wdt:P279* wd:Q732717 ; wdt:P17 wd:Q30 }`
  → **1,755**.
- Breakdown by direct `P31`: `law enforcement agency (Q732717) 1,164 | municipal police 212 | sheriff's office (Q96080490) 88 | federal LEA of the US 68 | office of the inspector general 50 | state agency of the US 33 | state police 22 | campus police 6`.
  (`Q87995256 "police department of the United States"` has only **2** direct instances —
  the class exists but is essentially unused.)
- External-identifier property census on that set:
  `Freebase ID (P646) 752 | X username 394 | LoC Authorities (P244) 324 | Facebook 323 | VIAF 276 | Instagram 193 | Yale LUX 188 | OSM Name Suggestion Index ID (P8253) 158 | ISNI 151 | Quora 130 | Google KG 128 | Ringgold 116 | YouTube 114 | J9U 106 | GND 44 | LinkedIn 38 | ROR ID (P6782) 26`.
  **No government identifier appears anywhere in the top 20.**
- Property search via `wbsearchentities` for "ORI" and "Originating Agency" returned no
  matching property. Confirmed present and usable are `P882` FIPS 6-4 (counties), `P774`
  FIPS 55-3 (places), `P5086`/`P5087` FIPS 5-2 (states), `P590` GNIS Feature ID, `P2483`
  NCES district ID, `P2484` NCES school ID, `P1771` IPEDS ID, `P1278` LEI, `P6782` ROR.
- Spot check `Q214126` (Los Angeles Police Department): 52 claims, none of which is a
  government agency identifier.
**Retrieved:** 2026-08-20
**Implication for the spec:** Wikidata is a **linking target, not an identity backbone**.
Store `wikidata_qid` in the `sameAs` table where it exists; never depend on it for
coverage. Conversely, this is a concrete upstream-contribution opportunity per §20 Q33:
proposing and populating a Wikidata ORI property from SIG's registry would be a
high-visibility federation win. Note also `P8253` (OSM Name Suggestion Index ID) on 158
agencies — a small but real bridge between Wikidata and OSM `operator` strings.
**Outline delta:** EXTENDS §1.2 (federation) and §20 Q33 — identifies a specific,
tractable upstream contribution, and rules Wikidata out as the primary hub.

## A.4 Corporate and vendor identity

### F5.13 — GLEIF LEI is free, CC0, bulk-downloadable, models succession natively — and does not cover small private vendors

**Claim:** GLEIF publishes 3,407,300 LEI records daily under CC0 with a free unauthenticated
API; the record schema includes `successorEntity`, `expiration.reason`, `status` and a
`eventGroups` legal-entity-event log; Axon has an LEI, Fusus (US) does not.
**Status:** VERIFIED
**Evidence:**
- Fuzzy search `https://api.gleif.org/api/v1/fuzzycompletions?field=entity.legalName&q=Axon%20Enterprise`
  → `AXON ENTERPRISE, INC.` → LEI **`549300QP2IEEGFE16681`**.
- `https://api.gleif.org/api/v1/lei-records/549300QP2IEEGFE16681` (HTTP 200) returned a
  full record including: `legalName`, `legalAddress` (registered agent, Wilmington DE),
  `headquartersAddress` (17800 N 85th St, Scottsdale AZ 85255), `registeredAt`
  `RA000602`, `registeredAs` `3337819`, `jurisdiction` `US-DE`, `legalForm` `XTIQ`,
  `status: ACTIVE`, `successorEntity: {lei: null, name: null}`, `successorEntities: []`,
  `creationDate 2001-01-05`, an `eventGroups` log
  (`{type: CHANGE_LEGAL_ADDRESS, effectiveDate: 2022-11-15, status: COMPLETED}`),
  registration metadata (`initialRegistrationDate`, `lastUpdateDate 2026-08-03`,
  `nextRenewalDate`, `managingLou`, `corroborationLevel: FULLY_CORROBORATED`), and
  **cross-identifiers: `ocid: "us_de/3337819"` (OpenCorporates), `spglobal: ["885779"]`**.
- Bulk: `https://goldencopy.gleif.org/api/v2/golden-copies/publishes?page[size]=1`
  (HTTP 200) → publish_date `2026-08-20 08:00:00`, `lei2` full file **record_count
  3,407,300**, available as CSV (476 MB zipped), JSON (886 MB), XML (854 MB), plus
  `IntraDay` delta files (11,766 records in the 08:00 delta). CDF version `LEI_3.1`.
- Lifecycle vocabulary verified live: `filter[registration.status]=RETIRED` →
  **249,910** records; `filter[entity.status]=INACTIVE` → **249,494**. Sample inactive
  records carry `eventGroups` with `{type: DISSOLUTION, effectiveDate: …}`.
- **License: CC0 1.0 Universal.** GLEIF states data are "provided under the CC0 licence,
  see CC0 1.0 Universal (CC0 1.0)"; terms at
  `https://www.gleif.org/en/meta/lei-data-terms-of-use`; open-data page
  `https://www.gleif.org/en/about/open-data` (HTTP 200). GLEIF endorsed the
  International Open Data Charter in 2016.
- **Coverage gap:** fuzzy search for "Fusus" returns only `FUSUS AS` (Norway,
  `9845003B49U76LA89E34`) and unrelated names. **Fusus, Inc. (Georgia) has no LEI.**
  Axon has **0** direct children in GLEIF Level-2 data, so the Axon→Fusus acquisition is
  *not* representable in GLEIF.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt LEI for vendors that have one (Axon, Motorola
Solutions, Genentec's parents, SoundThinking, etc. — public companies and regulated
entities), store it in `sameAs`, and **use GLEIF's schema as the model** for SIG's own
vendor lifecycle fields (§D.5). Do **not** expect LEI coverage of privately-held
surveillance vendors or of acquired subsidiaries. The Axon→Fusus case must be modelled
from SIG's own evidence (press releases, SEC filings), not from GLEIF.
**Outline delta:** EXTENDS §8.2 (Vendor) — adds a concrete, free, CC0 identifier and a
proven lifecycle schema, plus the explicit warning that it will not cover the
acquisitions the project cares about most.

### F5.14 — OpenCorporates is paywalled at £2,250/yr but has a free public-benefit tier for NGOs and journalists

**Claim:** OpenCorporates' commercial API starts at £2,250/year for 500 calls/month; a
free programme exists for investigative journalists, NGOs, universities and
anti-corruption researchers.
**Status:** VERIFIED
**Evidence:** `https://opencorporates.com/pricing` (HTTP 200, fetched):
- Essentials £2,250/yr (£225/mo) — up to 500 API calls/month, 200/day
- Starter £6,600/yr (£660/mo) — 2,500/month, 500/day
- Basic £12,000/yr (£1,200/mo) — 5,000/month, 1,000/day
- Enterprise — custom, includes bulk data delivery
- All commercial plans permit "Internal & external use."
- Public-benefit tier: "We support investigative journalists, NGOs, universities and
  anti-crime-and-corruption research groups."
`https://api.opencorporates.com/` (HTTP 200) describes >200 million companies "available
as either share-alike attribution open data or commercially". The pricing page does not
state the open-data licence name; **this is unresolved — do not assert ODbL.**
**Retrieved:** 2026-08-20
**Implication for the spec:** Budget zero for OpenCorporates in v1. Apply to the
public-benefit programme; if granted, the OCID (already present in every GLEIF record as
`attributes.ocid`, e.g. `us_de/3337819`) becomes a free bridge from LEI to state
incorporation records — which is the path to HOA and small-business identity (§C).
Record the OCID from GLEIF regardless: **it costs nothing and requires no OpenCorporates
account.**
**Outline delta:** EXTENDS §20 Q12 — supplies an actual acquisition path for private-org
identity and its cost.

### F5.15 — USAspending gives free, keyless access to SAM.gov UEIs, DUNS, aliases and parent/child structure for any federally-funded organization

**Claim:** `api.usaspending.gov` requires no key and returns, per recipient, a UEI, legacy
DUNS, an `alternate_names[]` array, parent linkage, business-type tags and an address.
**Status:** VERIFIED
**Evidence:**
- `POST https://api.usaspending.gov/api/v2/recipient/` with
  `{"keyword":"Police Department","limit":10,"order":"desc","sort":"amount"}` → HTTP 200,
  **587 matching recipients**, e.g.
  `DCJLHJL4WQ94 / 085425762 / R / LAS VEGAS METROPOLITAN POLICE DEPARTMENT`,
  `RGJ5CPK2YHK1 / 130986214 / R / SEATTLE POLICE DEPARTMENT`,
  `KMLJC669V5F5 / 054977231 / R / CITY OF NEW YORK POLICE DEPARTMENT`,
  `MBK8V5UBXNL8` appearing at both `C` (child) and `P` (parent) levels for
  `CITY OF HAWTHORNE POLICE DEPARTMENT`.
- `GET /api/v2/recipient/{id}/` returns `alternate_names` — for the sample record,
  8 alias strings including `"CA DEPT OF HEALTH SERVICES"`, `"CA ST DEPARTMENT OF HEALTH SERVICES"` —
  plus `business_types: ["government","national_government","regional_and_state_government"]`,
  `parent_uei`, `parents[]` and a structured `location`.
- `POST /api/v2/autocomplete/recipient/` for `"City of Los Angeles Police"` returns two
  near-identical registry variants — `"LOS ANGELES POLICE DEPT  CITY OF"` (two spaces)
  and `"LOS ANGELES POLICE DEPT, CITY OF"` — a live example of the exact ER problem.
- **UEI format:** 12-character alphanumeric (`JE73CDQUAPA7`, `MBK8V5UBXNL8`), replacing
  the 9-digit DUNS.
- `https://api.sam.gov/entity-information/v3/entities?api_key=DEMO_KEY&…` → **HTTP 404**
  (SAM's own Entity API requires a registered SAM key; docs at
  `https://open.gsa.gov/api/entity-api/`, HTTP 200). USAspending is the keyless path.
**Retrieved:** 2026-08-20
**Implication for the spec:** Add **UEI** to the identifier stack for every organization
class, not just vendors. It is the only identifier that spans police departments,
universities, transit agencies, hospitals and private vendors, because it is keyed on
"receives federal money" rather than on organization type. Coverage is partial (587
"Police Department" recipients vs ~18k agencies), but it is free, keyless, carries
**machine-readable aliases** — which are directly usable as ER training/blocking input —
and encodes parent/child structure that maps onto the `parent_organization` field in
§8.1.
**Outline delta:** **EXTENDS §8.1 and §10.1A with a source the outline does not mention
at all.** UEI + USAspending should be added to the Phase 1A identity aid list.

### F5.16 — Community LE-agency registries (PDAP, OpenOversight, state POST) do not currently supply usable machine-readable identity

**Claim:** PDAP's API requires authentication and its host did not resolve; OpenOversight's
public instance did not resolve; California POST publishes only an HTML directory with no
ORI, no addresses and no export.
**Status:** VERIFIED (as negative results)
**Evidence:**
- PDAP docs `https://docs.pdap.io/api/introduction` (HTTP 200) describe `/agencies`,
  `/data-sources/{id}`, `/login`, `/api-key` endpoints at
  `https://data-sources-v2.pdap.io/api`, with "the majority of API routes" requiring an
  API token or JWT, and no stated licence. Live calls to
  `https://data-sources-v2.pdap.io/api/agencies?page=1` and
  `…/api/search/search?state=Pennsylvania` returned **HTTP 000 (connection failure)**;
  `https://data-sources.pdap.io/api/search/...` returned **404**. `https://pdap.io/`
  itself is up (200).
- `https://openoversight.lucyparsonslabs.com/` → **HTTP 000 (did not resolve)**.
- `https://post.ca.gov/le-agencies` (HTTP 200, fetched): "a human-readable, alphabetical
  directory… agency names and hyperlinks to their websites"; **no ORI, no addresses, no
  agency-type classification, no downloadable file, no API**. Machine-readable requests
  must go to `WebRequest@post.ca.gov`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Do not design a v1 dependency on PDAP or OpenOversight.
Treat PDAP as a **federation partner** (§20 Q35/Q36) — reach out for a bulk agency export
and offer the SIG ORI↔GEOID crosswalk in exchange. State POST rosters are a
scraping-and-normalization project of their own, valuable mainly for agencies that are
missing from CDE and for detecting **decertified/dissolved** agencies (POST rosters drop
agencies that cease to exist, which is a dissolution signal — see §D.5).
**Outline delta:** EXTENDS §3 (decentralized ecosystem) — names concrete partners and the
concrete exchange good.

### F5.17 — ROR is excellent prior art but covers essentially no U.S. law enforcement

**Claim:** ROR contains 32,743+ organizations with rich crosswalks and an exemplary
lifecycle model, but only 93 police-related government organizations worldwide and
almost none in the U.S.
**Status:** VERIFIED
**Evidence:**
- `https://api.ror.org/v2/organizations?query=University+of+California+Berkeley` (HTTP
  200) → `https://ror.org/01an7q238`, `status: active`, alias names array,
  `relationships` of type `child`/`parent`, and
  `external_ids: [fundref(16 ids), grid: grid.47840.3f, isni: 0000 0001 2181 7878, wikidata: Q168756]`,
  plus `admin.created.date` / `admin.last_modified.date`.
- `filter=types:government&query=police` → **93 results** globally
  (`Leicestershire Police`, `Cyprus Police`, `Police Scotland`, `Federal Police of
  Brazil`, …). Not a U.S. LE registry.
- ROR locations are keyed by **GeoNames ID** (`geonames_id: 5389489` for Sacramento) with
  a denormalized `geonames_details` block.
**Retrieved:** 2026-08-20
**Implication for the spec:** Use ROR as the **design template** (see F5.41, §E) and as a
`sameAs` target for universities that operate campus police. Do not use it as an LE
registry.
**Outline delta:** EXTENDS §7.1 Goal 8 — identifies the model to copy for downstream
consumability.

---

# B. Geographic and jurisdictional identity (Q11)

## F5.18 — Census GEOID lengths and composition, verified empirically

**Claim:** GEOIDs are fixed-length left-zero-padded concatenations of parent codes, with
the following verified lengths.
**Status:** VERIFIED
**Evidence:** Live call to the Census Geocoder (F5.20) for `100 N Los Angeles St, Los
Angeles, CA`, plus the 2025 Gazetteer files (F5.19):

| Geography | GEOID | Length | Composition | Verified example |
|---|---|---|---|---|
| State | `STATE` | **2** | FIPS state | `06` = California |
| County | `COUNTY` | **5** | state(2)+county(3) | `06037` = Los Angeles County |
| County subdivision | `COUSUB` | **10** | state(2)+county(3)+cousub(5) | `0603791750` = Los Angeles CCD; `0100190171` = Autaugaville CCD |
| Place (incorporated + CDP) | `PLACE` | **7** | state(2)+place(5) | `0644000` = Los Angeles city; `0100100` = Abanda CDP |
| Census tract | `TRACT` | **11** | state(2)+county(3)+tract(6) | `06037207400`; `01001020100` |
| Census block | `BLOCK` | **15** | state(2)+county(3)+tract(6)+block(4) | `060372074001031` |
| Unified school district | `UNSD` | **7** | state(2)+LEA(5) | `0100001` = Fort Rucker School District |
| Elementary school district | `ELSD` | **7** | state(2)+LEA(5) | `0400004` = Clarkdale-Jerome Elementary District |
| School district admin area | `SDADM` | **7** | state(2)+…(5) | `5000007` = Barre Supervisory Union |

Additional geographies returned by the Geocoder for that address, each with its own
GEOID space: `Combined Statistical Areas` (`348`), `Urban Areas` (`51445`),
`119th Congressional Districts`, `2024 State Legislative Districts - Upper/Lower`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Store GEOIDs as **fixed-width strings, never integers.**
`06` must not become `6`; `0644000` must not become `644000`. Constrain each jurisdiction
row with a `CHECK (length(geoid) = expected_length_for(level))`. Store the *level*
explicitly, because a 7-character GEOID is ambiguous between `place`, `unsd`, `elsd` and
`sdadm` — three of those coexist in the same national dataset and `0400004` is a valid
ELSD and could equally be read as a place code.
**Outline delta:** EXTENDS §20 Q11 with the concrete answer and a concrete data-type
hazard.

## F5.19 — Census Gazetteer files: verified downloads, row counts, and a breaking format change between 2024 and 2025

**Claim:** The Gazetteer is a free, no-key, direct-download national reference for every
geography SIG needs; the 2025 vintage switched from **tab-delimited** to
**pipe-delimited** and added a `GEOIDFQ` column.
**Status:** VERIFIED
**Evidence:** Actually downloaded and parsed from `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/`:

| File | HTTP | Bytes (zip) | Rows | Delimiter | Columns |
|---|---|---|---|---|---|
| `2024_Gazetteer/2024_Gaz_place_national.zip` | 200 | 1,221,402 | **32,333** | TAB | `USPS GEOID ANSICODE NAME LSAD FUNCSTAT ALAND AWATER ALAND_SQMI AWATER_SQMI INTPTLAT INTPTLONG` |
| `2024_Gazetteer/2024_Gaz_counties_national.zip` | 200 | 141,679 | **3,222** | TAB | `USPS GEOID ANSICODE NAME ALAND AWATER ALAND_SQMI AWATER_SQMI INTPTLAT INTPTLONG` |
| `2025_Gazetteer/2025_Gaz_state_national.zip` | 200 | 2,863 | **52** | PIPE | `USPS GEOID GEOIDFQ NAME ALAND AWATER ALAND_SQMI AWATER_SQMI INTPTLAT INTPTLONG` |
| `2025_Gazetteer/2025_Gaz_cousubs_national.zip` | 200 | 1,478,116 | **36,427** | PIPE | + `ANSICODE FUNCSTAT` |
| `2025_Gazetteer/2025_Gaz_tracts_national.zip` | 200 | 2,332,377 | **85,396** | PIPE | `USPS GEOID GEOIDFQ ALAND AWATER … INTPTLAT INTPTLONG` |
| `2025_Gazetteer/2025_Gaz_unsd_national.zip` | 200 | 448,705 | **10,863** | PIPE | + `LOGRADE HIGRADE` |
| `2025_Gazetteer/2025_Gaz_elsd_national.zip` | 200 | 80,234 | **1,971** | PIPE | + `LOGRADE HIGRADE` |
| `2025_Gazetteer/2025_Gaz_sdadm_national.zip` | 200 | 2,674 | **52** | PIPE | + `LOGRADE HIGRADE` |

Full 2025 file list (from the directory index, HTTP 200):
`aiannh, aiannhrt, cbsa, counties, cousubs, elsd, place, scsd, sdadm, sldl, sldu, state, tracts, ua, unsd, zcta`.
`GEOIDFQ` is the fully-qualified form with summary-level prefix:
`0400000US01` (state), `0600000US0100190171` (cousub), `1400000US01001020100` (tract),
`9500000US0400004` (elsd), `9700000US0100001` (unsd), `9800000US5000007` (sdadm).
Note the 2024 URL `2024_Gaz_county_subdivisions_national.zip` **404s** — the correct stem
is `cousubs`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Pin the vintage year in the connector and **sniff the
delimiter**; a hard-coded `\t` split silently produces one giant column against 2025
files. Prefer `GEOIDFQ` as the stored jurisdiction identifier where available (see §E) —
it is self-describing about summary level and therefore removes the 7-character ambiguity
noted in F5.18. The Gazetteer gives centroids only; boundaries come from TIGER (F5.21).
**Outline delta:** EXTENDS §20 Q11 with verified artifacts, row counts and a
version-drift trap.

## F5.20 — The Census Geocoder API is free and keyless; the Census *data* API requires a key

**Claim:** `geocoding.geo.census.gov` returns full geography hierarchies for a street
address with no authentication; `api.census.gov/data/...` returns "Missing Key".
**Status:** VERIFIED
**Evidence:**
- `https://geocoding.geo.census.gov/geocoder/geographies/address?street=100+N+Los+Angeles+St&city=Los+Angeles&state=CA&benchmark=Public_AR_Current&vintage=Current_Current&format=json`
  → HTTP 200, no key, returning `tigerLine{tigerLineId, side}` plus a `geographies` object
  containing States, Counties, County Subdivisions, Incorporated Places, Census Tracts,
  2020 Census Blocks, Urban Areas, CSAs, Congressional Districts and State Legislative
  Districts — each with `GEOID`, `NAME`, `BASENAME`, `CENTLAT/CENTLON`,
  `INTPTLAT/INTPTLON`, `AREALAND/AREAWATER`, `FUNCSTAT`, `LSADC`, `MTFCC`, and the ANSI
  code (`PLACENS`, `COUNTYNS`, `COUSUBNS`, `STATENS`).
- `https://api.census.gov/data/2020/dec/pl?get=NAME&for=place:44000&in=state:06` → HTML
  page titled **"Missing Key"**.
**Retrieved:** 2026-08-20
**Implication for the spec:** Geocoding of agency/organization street addresses (from
LEAIC, IPEDS, NPPES, NTD, contracts) is a **free, unlimited, keyless** operation and
should be the standard way SIG assigns an organization to a jurisdiction GEOID.
Batch mode exists (`/geocoder/geographies/addressbatch`, 10,000 addresses per POST).
Any use of the Census *statistical* API needs a free key and must be configured
separately.
**Outline delta:** EXTENDS §10.1A — supplies the actual mechanism for
"Census geographic identifiers".

## F5.21 — TIGER/Line 2025 supplies boundary geometry for every jurisdiction class SIG needs

**Claim:** `https://www2.census.gov/geo/tiger/TIGER2025/` (HTTP 200) exposes per-layer
directories covering all required boundary types.
**Status:** VERIFIED
**Evidence:** Directory listing returned:
`ADDR, ADDRFEAT, ADDRFN, AIANNH, AITSN, ANRC, AREALM, AREAWATER, BG, CBSA, CD, COASTLINE, CONCITY, COUNTY, COUSUB, CSA, EDGES, ELSD, ESTATE, FACES, FACESAH, FACESAL, FACESMIL, FEATNAMES, INTERNATIONALBOUNDARY, LINEARWATER, METDIV, MIL, PLACE, POINTLM, PRIMARYROADS, PRISECROADS, RAILS, ROADS, SCSD, SDADM, SLDL, SLDU, STATE, SUBBARRIO, TABBLOCKSUFX, TBG, TRACT, TTRACT, UNSD, USCENSUS`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Recommended boundary stack for SIG jurisdictions:
`STATE` + `COUNTY` + `PLACE` + `COUSUB` for general-purpose government;
`UNSD`/`ELSD`/`SCSD`/`SDADM` for school districts; `AIANNH` for tribal areas; `CONCITY`
for consolidated city-counties (Nashville, Indianapolis, Louisville — which break the
naive "a place is inside a county" assumption). Note TIGER has **no layer for
special districts generally** (fire, water, transit, port, hospital districts): those
boundaries do not exist in a national federal dataset and must be sourced state by state
or left null. Load into PostGIS with the GEOID as the join key to the Gazetteer table.
**Outline delta:** EXTENDS §20 Q11 — answers the "jurisdiction *boundary* vs jurisdiction
*identity*" distinction the workstream brief raised: identity comes from
Gazetteer+GNIS, geometry from TIGER, and the two are joined by GEOID, which is stable
across both.

## F5.22 — Census `ANSICODE` is the GNIS `feature_id`; the join succeeds for 32,332 of 32,333 places

**Claim:** The Census `PLACENS`/`COUNTYNS`/`COUSUBNS`/`STATENS` "ANSI" codes are literally
USGS GNIS feature IDs, and GNIS supplies the **legal name of the governmental unit**
(feature class `Civil`) that Census renders in statistical form.
**Status:** VERIFIED
**Evidence:** Downloaded `https://prd-tnm.s3.amazonaws.com/StagedProducts/GeographicNames/DomesticNames/DomesticNames_National_Text.zip`
(HTTP 200, 38,625,422 bytes) → `Text/DomesticNames_National.txt`, **981,698 rows**,
pipe-delimited, 21 columns:
`feature_id, feature_name, feature_class, state_name, state_numeric, county_name, county_numeric, map_name, date_created, date_edited, bgn_type, bgn_authority, bgn_date, prim_lat_dms, prim_long_dms, prim_lat_dec, prim_long_dec, source_lat_dms, source_long_dms, source_lat_dec, source_long_dec`.
Feature-class census: `Stream 232,585 | Populated Place 190,921 | Reservoir 72,985 | Lake 70,348 | Summit 69,706 | Valley 69,257 | Civil 65,193 | Spring 37,490 | …`.
Direct joins:
- Census place `0644000` has `PLACENS = 02410877`; GNIS `2410877` =
  `City of Los Angeles | Civil | California | 06 | Los Angeles | 037`.
- Census county `06037`/Autauga `01001` `ANSICODE 00161526`; GNIS `161526` =
  `Autauga County | Civil | Alabama | 01`.
- Census CDP `0100100` `ANSICODE 02582661`; GNIS `2582661` =
  `Abanda Census Designated Place | Census | Alabama | 01 | Chambers | 017`.
- **Bulk verification: of the 32,333 places in the 2024 national Gazetteer, 32,332
  ANSICODEs resolve to a GNIS `feature_id` — a 99.997% join rate, 1 miss.**
**Retrieved:** 2026-08-20
**Implication for the spec:** This is a **free, high-integrity, no-key bridge** and it
solves a real naming problem. Census says `"Los Angeles city"`; GNIS says
`"City of Los Angeles"`. SIG's name-normalization rules (§D.2) need the *governmental*
form to resolve "City of X Police Department" ↔ "X Police Department", and GNIS's `Civil`
class supplies exactly that for 65,193 units. Store `gnis_feature_id` on every
jurisdiction. Note the `feature_class` distinction: `Civil` = a legally constituted
governmental unit; `Populated Place` = an inhabited locality with no necessary legal
existence; `Census` = a CDP. **Only `Civil` features have a government that can operate
a police department.**
**Outline delta:** **EXTENDS §20 Q11 with a link the outline does not contemplate.** The
outline mentions Census identifiers but not GNIS, and not that the two are already
joined.

## F5.23 — Concrete identifiers for the non-LE organization classes that appear in Flock/Fusus networks

**Claim:** Each non-LE class the outline flags has a specific, free, machine-readable
national identifier — except HOAs, private businesses and private security firms.
**Status:** VERIFIED
**Evidence:** Each tested live.

- **School districts → NCES LEAID (7 chars = 2 FIPS state + 5).** Verified via the Urban
  Institute Education Data API (free, no key):
  `https://educationdata.urban.org/api/v1/school-districts/ccd/directory/2022/?fips=6&limit=2`
  → HTTP 200, `count: 2144` for California, sample row
  `{leaid: "0600001", lea_name: "Acton-Agua Dulce Unified", state_leaid: "CA-1975309", street_mailing, city_mailing, latitude: 34.472708, longitude: -118.196768, county_code: "6037", county_name: "Los Angeles County", agency_type: 1, agency_level: 4, boundary_change_indicator, congress_district_id, cbsa, csa}`.
  NCES's own page `https://nces.ed.gov/ccd/files.asp` (HTTP 200) confirms LEAID/NCESSCH
  as the district/school identifiers but publishes no structured field spec on that page.
  **`LEAID` is identical to the Census `UNSD`/`ELSD` GEOID** (F5.18) — one identifier,
  two names.
- **Universities/colleges → IPEDS UNITID (6 digits).** Downloaded
  `https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip` (HTTP 200, 1,110,720 bytes) →
  `HD2023.csv`, **6,163 institutions**, columns include
  `UNITID, INSTNM, IALIAS, ADDR, CITY, STABBR, ZIP, FIPS, OBEREG, CHFNM, CHFTITLE, GENTELE, EIN, UEIS, OPEID, OPEFLAG, WEBADDR, …, LATITUDE, LONGITUD, COUNTYCD, C21BASIC, SECTOR`.
  Coverage in that file: **EIN on 6,163/6,163 (100%)**, **SAM UEI (`UEIS`) on 5,581/6,163
  (90.6%)**, **alias strings (`IALIAS`) on 2,204**. Sample:
  `108861 | Berkeley School of Theology | IALIAS "BST" | CA | COUNTYCD 6001 | EIN 941156250 | UEIS JKY4B68BGLN5 | OPEID 00112000 | 37.865252,-122.256149`.
  Note the file's first column header carries a **UTF-8 BOM** (`﻿UNITID`) — a real
  parsing trap.
- **Transit agencies → NTD ID.** Downloaded
  `https://data.transportation.gov/api/views/ccvf-fykn/rows.csv?accessType=DOWNLOAD`
  (HTTP 200, 1,129,936 bytes) → *2024 NTD Annual Data – Reporter Agency Information*,
  **2,916 rows**, columns:
  `NTD ID, State/Parent NTD ID, Agency Name, Division/Department, Doing Business As, Reporter Type, Reporting Module, Organization Type, Reported By NTD ID, Reported by Name, Public Sponsor, Subrecipient Type, FY End Date, Original Due Date, Address Line 1/2, P.O. Box, City, State, Zip Code (+Ext), Region, URL, FTA Recipient ID, Universal Entity ID, Service Area Sq Miles, Service Area Pop, Primary UZA UACE Code, UZA Name, Tribal Area Name`.
  **`Universal Entity ID` is the SAM.gov UEI** (`JFE1DR73YB29` for Riverside County
  Transportation Commission) — so NTD is a free NTD-ID↔UEI crosswalk, and `Doing Business
  As` is a ready-made alias column.
- **Hospitals → CMS CCN (6 chars).** `https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0?limit=1`
  → HTTP 200, `count: 5419`, sample
  `{facility_id: "010001", facility_name: "SOUTHEAST HEALTH MEDICAL CENTER", address, citytown, state, zip_code, countyparish, telephone_number, hospital_type: "Acute Care Hospitals", hospital_ownership: "Government - Hospital District or Authority", emergency_services}`.
  `facility_id` is the CCN.
- **Healthcare organizations → NPI (10 digits), with a caveat.** `https://npiregistry.cms.hhs.gov/api/?version=2.1&organization_name=Cedars-Sinai%20Medical%20Center&enumeration_type=NPI-2&limit=2`
  → HTTP 200, keyless, `result_count: 2`. **Both records are named "CEDARS-SINAI MEDICAL
  CENTER" at 8700 Beverly Blvd** with different NPIs (`1235318346` and another), different
  mailing addresses, and one carrying a nonsense country code (`UM`, "United States Minor
  Outlying Islands") on a Los Angeles address. Fields: `addresses[]`, `basic{}`,
  `taxonomies[] {code, desc, primary}`, `other_names[]`, `identifiers[]`,
  `practiceLocations[]`, `endpoints[]`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Use the per-class table in §F. Two specific rules:
1. **Prefer CCN over NPI for hospital *facility* identity.** NPI is an *enumeration*
   identifier — one legal organization routinely holds many NPIs (subparts, billing
   entities) — so NPI is many-to-one against the physical hospital that hosts a Fusus
   node. CCN is one per certified facility. Keep NPI as a secondary identifier.
2. **EIN and SAM UEI are the two cross-class glue identifiers.** IPEDS carries both;
   NTD carries UEI; USAspending carries UEI + DUNS + aliases. When a Flock network
   member is a university, hospital or transit agency, resolve through UEI/EIN before
   attempting name matching.
**Outline delta:** **EXTENDS §8.1 and §20 Q12 materially.** The outline enumerates the
organization types but gives no identifier for any of them. This supplies one per class,
with verified coverage counts.

## F5.24 — Keeping the jurisdiction model international

**Claim:** A generalizable jurisdiction identifier scheme should be a namespaced tuple
`(scheme, code)` with GeoNames as the universal fallback, because no single global
authority covers sub-national units to the depth SIG needs.
**Status:** PARTIALLY VERIFIED
**Evidence:**
- **GeoNames** `https://www.geonames.org/about.html` (HTTP 200, fetched): "over 25
  million geographical names", "over 12 million unique features whereof 4.8 million
  populated places and 16 million alternate names"; **licensed CC BY 4.0**; free
  webservices and a daily database export. The page does not state API credit limits —
  **unverified**; the free web service is known to be credit-limited per registered
  username, which must be checked before relying on it operationally. ROR already uses
  `geonames_id` as its canonical place key (F5.17), which is a strong precedent.
- **ISO 3166-1/-2**: the ISO Online Browsing Platform
  `https://www.iso.org/obp/ui/#search` returned **HTTP 403** to automated clients, and
  `https://www.iso.org/iso-3166-country-codes.html` also **403**. ISO 3166-2 subdivision
  codes are not freely bulk-downloadable from ISO; Wikidata and GeoNames are the
  practical sources. **Do not plan on an ISO feed.**
- **NUTS (EU)**: `https://gisco-services.ec.europa.eu/distribution/v2/nuts/nuts-2024-units.json`
  HTTP 200 and `…/nuts/csv/NUTS_AT_2024.csv` HTTP 200 — the 2024 NUTS vintage is freely
  downloadable as JSON and CSV from Eurostat GISCO, with boundary geometries in the same
  distribution.
- **France (INSEE)**: `https://www.insee.fr/fr/information/8377162` HTTP 200 — the Code
  Officiel Géographique (COG) is published annually; INSEE commune codes are the French
  analogue of Census place GEOIDs and are the right key for Technopolice/PanoptiCity data.
- **OSM**: boundary relations carry `admin_level`, `boundary=administrative`, `ref:*` and
  `wikidata` tags. taginfo shows a rich `ref:US*` namespace already in use
  (`ref:US:NID` 51,309; `ref:US:EIA` 10,783; `ref:us:ny:swis` 2,479; `ref:US:NPS` 367)
  but **no ORI key exists** (searched `ref:us*` and `ORI` on
  `https://taginfo.openstreetmap.org/api/4/keys/all` — no match). `operator:type` values
  are usable as a coarse org-type signal:
  `public 538,082 | private 445,463 | government 355,996 | business 24,394 | community 19,862 | religious 19,330 | university 17,770 | private_non_profit 10,885 | ngo 7,688 | council 5,196 | association 4,715 | school 4,395`.
  `man_made=surveillance` totals **558,645 objects** (557,900 nodes, 716 ways, 29
  relations).
**Retrieved:** 2026-08-20
**Implication for the spec:** Model `Jurisdiction.identifiers` as a set of
`(scheme, value)` pairs rather than a single column, with `scheme` drawn from a
controlled vocabulary: `us-census-geoid`, `us-gnis`, `iso3166-1`, `iso3166-2`,
`geonames`, `nuts`, `insee-cog`, `osm-relation`, `wikidata`. Require **GeoNames ID on
every jurisdiction** as the universal cross-country spine (following ROR), and require
Census GEOID additionally for U.S. jurisdictions. Do not attempt a single global code
system.
**Outline delta:** EXTENDS §5 (International landscape) and §20 Q11 — the outline's
international section does not address identity at all.

---

# C. Private organizations in surveillance networks (Q12)

## F5.25 — There is no national registry of HOAs, and fewer than ten states run one

**Claim:** ~365,000 HOA communities exist in the U.S. with no federal registry and no
national identifier; most are state-registered nonprofit corporations, and only a
minority of states maintain a dedicated HOA registry.
**Status:** PARTIALLY VERIFIED (secondary sources; no primary registry found because
none exists)
**Evidence:** Search across HOA registry sources returned: no federal registry; an
estimate of ~365,000 communities / 74.2 million residents; "fewer than 10 states operate a
dedicated HOA registration system with mandatory filing"; most HOAs are organized as
non-profit corporations registered with a state agency. A concrete state example exists —
Utah's `https://commerce.utah.gov/hoa/hoa-registry-search/` (returned **HTTP 403** to
automated clients; existence confirmed, contents not verified). Commercial aggregators
(First American Data & Analytics HOA Database, National HOA Authority) exist but are
proprietary.
**Retrieved:** 2026-08-20
**Implication for the spec:** HOAs, apartment complexes, malls, casinos and private
security firms **cannot be assigned an external canonical identifier**. They require
SIG-minted surrogates plus an evidence-linked identity, and they raise the sharpest
privacy question in the project (§C.4).
**Outline delta:** CONFIRMS §20 Q12's premise and supplies the missing quantification.

## C.1 The surrogate-minting design

Because no identifier exists, SIG must mint one. The design below follows the precedent
EFF Atlas already set (`XX0000NNN`, F5.11) but makes it content-derived and stable.

```
mint_org_id(candidate) -> sig_org_id

Inputs:
  candidate.raw_name            e.g. "Sunridge Estates HOA"
  candidate.org_class           e.g. "hoa"
  candidate.address_raw         e.g. "1200 Sunridge Pkwy, Frisco, TX 75035"
  candidate.jurisdiction_geoid  e.g. "4827684"  (place: Frisco city, TX)
  candidate.source_ref          e.g. flock_portal:frisco-tx-pd#shared_networks row 41

Procedure:
  1. normalized := normalize_org_name(candidate.raw_name)        # §D.2
  2. geo        := geocode(candidate.address_raw) via Census Geocoder  # F5.20
                   -> {place_geoid, county_geoid, tract_geoid, block_geoid, lat, lon}
     if no address available: geo := jurisdiction from the observing agency's portal
  3. blocking_key := (org_class, geo.place_geoid, first_token(normalized))
  4. search existing SIG orgs on blocking_key; run the cascade (§D.3)
  5. if a Tier<=3 match is found -> return existing sig_org_id, append alias + source_ref
  6. else mint a new surrogate:
        sig_org_id := "sig:org:" || uuidv7_crockford32() || check_char
        record identity_basis := {normalized_name, org_class, place_geoid,
                                  address_hash, first_seen_source_ref, first_seen_at}
     return sig_org_id
```

Two rules that matter:

- **`identity_basis` is stored, immutable and published.** It is the audit trail for why
  this surrogate exists and what would have to change for it to be merged. Without it,
  surrogates accumulate silently and no one can ever prove two of them are the same thing.
- **Address is the discriminator, not name.** "Sunridge Estates" appears in many states.
  `(normalized_name, place_geoid)` is the minimum viable key; `(normalized_name,
  block_geoid)` is preferred where a street address exists, because HOAs and apartment
  complexes are spatially compact and the Census block is a tight, free, stable spatial
  key obtainable from the keyless geocoder (F5.20).

## C.2 Org-type taxonomy

Adopt EFF Atlas's two-axis scheme (F5.11) and extend it, rather than inventing one.

```
organization_class          (what kind of thing it is — SIG-controlled, closed vocabulary)
  government.municipal            government.county          government.state
  government.federal              government.tribal          government.special_district
  law_enforcement.municipal_pd    law_enforcement.sheriff    law_enforcement.state_police
  law_enforcement.campus          law_enforcement.school_district
  law_enforcement.transit         law_enforcement.airport    law_enforcement.port
  law_enforcement.constable       law_enforcement.marshal    law_enforcement.corrections
  law_enforcement.prosecutor      law_enforcement.fusion_center
  education.k12_district          education.higher_ed
  health.hospital                 health.system
  transport.transit_agency        transport.airport_authority
  private.hoa                     private.apartment_complex  private.retail_center
  private.casino                  private.business           private.security_firm
  private.utility                 private.railroad
  nonprofit.other                 unknown

operating_relationship      (why it is in the graph)
  operates_devices | receives_data | shares_data | hosts_devices | contracts_for | unknown
```

`law_enforcement.*` and `government.*` are deliberately separate: the City of Frisco and
the Frisco Police Department are **different organizations** with a `parent_organization`
edge, because contracts are signed by the city, ORIs are held by the department, and
Flock portals are published by the department. Collapsing them destroys the
procurement-to-deployment lineage §6.7 asks for.

## C.3 Address-based disambiguation

```
address_key(addr) :=
  1. USPS-style normalize: uppercase; expand ordinals; standardize
     ST/AVE/BLVD/RD/DR/LN/CT/PKWY/HWY; strip unit designators to a separate field
  2. geocode via Census Geocoder (keyless, F5.20)
  3. emit tiered keys, most specific first:
       K1 = tigerLineId + side          (same address range segment)
       K2 = block_geoid                 (15 chars)
       K3 = tract_geoid                 (11 chars)
       K4 = place_geoid                 (7 chars)
  4. if geocoding fails, fall back to (zip5, normalized_street_number, soundex(street_name))
```

Match strength: shared `K1` is near-conclusive for a physical site; `K2` is strong;
`K3` is weak; `K4` is blocking-only and must never be treated as evidence of sameness.

## C.4 Publication policy — where the ethics bite

The workstream brief is right that this is an ethics question, and the answer must be a
rule, not a judgement call.

**Recommended rule:** SIG publishes an organization record only if the organization meets
at least one **publicity test**:

1. It holds a government identifier (ORI, GEOID, LEAID, UNITID, NTD ID, CCN, UEI); **or**
2. It is a registered legal entity findable in a public business/nonprofit registry
   (state corporate registry, IRS EIN in Publication 78 / Form 990, LEI); **or**
3. It is named as a party in a public record already published by a government body
   (contract, council agenda, transparency portal, FOIA release); **or**
4. It is a commercial premises open to the public (mall, casino, retail center, stadium).

An organization failing all four — a small HOA with no registration, named only in a
network-membership list — is published **only in aggregate**:
`"3 homeowners associations in Collin County, TX receive data from this network"`, with
the underlying records retained privately and represented publicly by
`Organization{class: private.hoa, jurisdiction: 4827684, name: null, count_only: true}`.

Rationale, stated plainly for the spec: a 40-unit HOA's "organization" is, functionally,
a list of forty households at a known set of addresses. Publishing its name plus its
Flock network membership publishes the surveillance posture of forty identifiable private
residences. That is a different act from publishing that a police department operates
cameras, and the graph model must be able to express the difference. This maps directly
onto §20 Q30/Q31 and should be cross-referenced there.

**Corollary:** the *network edge* is still publishable even when the *node* is not. The
fact that "Frisco PD shares with 14 non-governmental organizations" is a public-interest
fact about Frisco PD, and it survives suppression of the fourteen names.

## F5.26 — Flock transparency-portal slugs follow a `<place>-<state>-<type>` pattern; the site blocks automated access

**Claim:** Flock portal URLs are `https://transparency.flocksafety.com/<place-slug>-<state>-<type-suffix>`;
the site returns HTTP 403 to non-browser clients and is not in the Wayback CDX index.
**Status:** PARTIALLY VERIFIED
**Evidence:**
- `https://transparency.flocksafety.com/` , `…/dallas-tx-pd` and `…/api/agencies` all
  returned **HTTP 403** to curl with a full browser UA plus `Sec-Fetch-*` navigation
  headers, and WebFetch also returned 403.
- Wayback CDX (`http://web.archive.org/cdx/search/cdx?url=transparency.flocksafety.com*`
  and `matchType=domain`) returned **HTTP 200 with a zero-byte body** — no archived
  captures indexed.
- Slugs verified indirectly from search results:
  `https://transparency.flocksafety.com/okaloosa-county-fl-so` (Okaloosa County Sheriff's
  Office), `https://transparency.flocksafety.com/flock-pd/`,
  `https://transparency.flocksafety.com/flock-safety-sales`,
  `https://transparency.flocksafety.com/flock-safety-marketing`. Reported scale: "more
  than 1,500 agencies have published a Flock Transparency Portal."
**Retrieved:** 2026-08-20
**Implication for the spec:** Slug → organization resolution is a **parsing plus
cascade** problem, not a lookup. Parse:
```
slug_parse(slug):
  parts := slug.split('-')
  if parts[-1] in TYPE_SUFFIX:            # pd, so, sd, dps, ps, police, sheriff, pt, co
      org_type_hint := TYPE_SUFFIX[parts[-1]];  parts := parts[:-1]
  if parts[-1] is a 2-letter USPS code:
      state := parts[-1].upper();               parts := parts[:-1]
  place_slug := '-'.join(parts)           # "okaloosa-county", "dallas", "flock"
  return {place_slug, state, org_type_hint}

TYPE_SUFFIX = {pd: municipal_pd, police: municipal_pd, so: sheriff, sheriff: sheriff,
               sd: sheriff, dps: state_police|municipal_dps, ps: public_safety,
               pt: police_township, co: county}
```
Then match `(place_slug expanded, state, org_type_hint)` against the CDE registry through
the cascade. Note the `sd` ambiguity — it means *Sheriff's Department* in Flock slugs but
*School District* elsewhere; resolve by checking whether the expanded place slug ends in
"county". Note also that Flock's own internal orgs (`flock-pd`, `flock-safety-sales`) are
in the same namespace and must be excluded by a denylist. Portal access itself is a
scraping problem for another workstream (§20 Q24) — R5's contribution is the slug grammar.
**Outline delta:** EXTENDS §6.1 — the outline lists "Flock portal slugs" as an identity
aid without specifying how they resolve. They resolve only through normalization plus
cascade, and 403s make them unavailable to a plain fetcher.

---

# D. Entity resolution methodology (Q27, Q28, Q29)

## D.1 Tool survey and recommendation

### F5.27 — Splink 4 is the right probabilistic engine: MIT, DuckDB, Fellegi–Sunter, unsupervised EM, calibrated weights, strong explainability

**Claim:** Splink 4.0.16 is MIT-licensed, actively developed, runs Fellegi–Sunter with
unsupervised EM on DuckDB/Spark/Athena/SQLite/PostgreSQL, links ~1M records in ~1 minute
on a laptop and 100M+ on distributed backends, and produces calibrated match probabilities
with waterfall-chart explanations.
**Status:** VERIFIED
**Evidence:**
- `https://pypi.org/pypi/splink/json` → version **4.0.16**, `license: MIT`,
  `requires_python >=3.9,<4`.
- `gh api repos/moj-analytical-services/splink` → `license: MIT`, 2,348 stars,
  `pushed_at: 2026-08-20T14:37:26Z` (same day), not archived.
- `https://moj-analytical-services.github.io/splink/` (HTTP 200, fetched): backends
  DuckDB, PySpark, AWS Athena, SQLite, PostgreSQL; "Splink's core linkage algorithm is
  based on Fellegi-Sunter's model of record linkage"; "No training data is required, as
  models can be trained using an unsupervised approach"; "linking a million records on a
  laptop in approximately one minute"; scales to "100+ million records"; produces
  "pairwise predictions with match probabilities" plus waterfall chart, comparison viewer
  dashboard and parameter-estimate charts.
- Theory, from `https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html`
  (HTTP 200, fetched): `m` = P(observation | match); `u` = P(observation | non-match);
  λ = prior; match weight is additive in log₂ Bayes factors,
  `M = log2(λ/(1−λ)) + Σ log2(mᵢ/uᵢ)`, and
  `P(match) = 2^M / (1 + 2^M)`. **Calibration anchors: M = 0 → 50%; M = 4 → 95%;
  M = 10 → ~99.9%.**
- Blocking, from `…/topic_guides/blocking/blocking_rules.html` (HTTP 200, fetched):
  n(n−1)/2 ≈ 500 billion pairs for 1M records without blocking; multiple rules are
  OR-combined; "It's usually better to use a longer list of strict blocking rules, than a
  short list of loose blocking rules"; `count_comparisons_from_blocking_rule()` sizes the
  job before running it; non-equijoin (fuzzy) blocking conditions "execute inefficiently".
- Cluster evaluation, from `…/topic_guides/evaluation/clusters/graph_metrics.html`
  (HTTP 200, fetched): node degree, node centrality, **bridges** ("edges whose removal
  would split a cluster… can be signalers of false positives… especially when joining two
  highly connected sub-clusters"), cluster size, cluster density (edges / max possible
  edges), cluster centralisation (flagged experimental). Explicitly: "graph metrics are
  rarely definitive, especially when taken in isolation", and **no numeric thresholds are
  supplied**.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt Splink 4 on DuckDB. SIG's organization universe is
~10⁴–10⁵ entities — three to four orders of magnitude below Splink's laptop ceiling — so
runtime is a non-issue and the whole ER pass can run in CI on every ingest. The additive
log₂ match weight is the right thing to store on a `Claim` for §9.3 ("confidence should be
explainable"): the per-comparison contributions *are* the explanation, and they can be
rendered in the UI directly.
**Outline delta:** EXTENDS §9.3 — supplies the concrete, defensible confidence
representation the outline asks for but does not specify.

### F5.28 — Splink's own guidance on building labelled data is missing; SIG must define its own gold-standard protocol

**Claim:** The Splink documentation page for clerical labelling is a stub.
**Status:** VERIFIED
**Evidence:** `https://moj-analytical-services.github.io/splink/topic_guides/evaluation/labelling.html`
(HTTP 200, fetched) contains only: "This page is under construction - check back soon!"
The sitemap confirms the supporting tooling exists —
`charts/threshold_selection_tool_from_labels_table.html`, `api_docs/evaluation.html`,
`demos/tutorials/07_Evaluation.html` — but the methodology guidance does not.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG must write and own its gold-standard construction
protocol (§D.6). This is not optional; without labels the threshold in §D.3 is a guess.
**Outline delta:** EXTENDS §20 Q28 — the "review queue" the outline demands only works if
the queue's output is captured as labels and fed back.

### F5.29 — Alternative ER tools: licenses, activity, and why they lose

**Claim:** dedupe, Zingg and Python RecordLinkage are all viable open-source
alternatives with different tradeoffs; Senzing is commercially prohibitive.
**Status:** VERIFIED
**Evidence:** (`gh api repos/...` and PyPI, all fetched 2026-08-20)

| Tool | Version | License | Stars | Last push | Notes |
|---|---|---|---|---|---|
| **Splink** | 4.0.16 | **MIT** | 2,348 | 2026-08-20 | SQL-generating; DuckDB/Spark/Athena/SQLite/Postgres; unsupervised EM |
| **dedupe** | 3.0.3 | **MIT** | 4,504 | 2025-07-29 | Active-learning labeller; in-memory Python; needs human labelling up front |
| **Zingg** | 0.7.0 | **AGPL-3.0** | 1,235 | 2026-08-20 | Spark-based; ML; **AGPL is a licence hazard for a hosted public service** |
| **RecordLinkage (py)** | 0.16 | **BSD-3-Clause** | 1,060 | **2024-02-21** | pandas-based; effectively dormant (2.5 years since last push) |
| **Senzing** | — | proprietary | — | — | See below |

Senzing pricing (`https://senzing.com/pricing/`, HTTP 200, fetched): subscription priced
per Data Source Record; **10M DSRs = $58,560/year** (≈$0.0059/record/year); slider to 1B
records; "Proven in production at ~100B records"; requires up-front payment for the full
term and acceptance of the standard EULA; **no free tier stated**.
**Retrieved:** 2026-08-20
**Implication for the spec:** Splink is the pick. dedupe is a reasonable second (its
active-learning labeller is genuinely useful and could be borrowed for the review-queue
UI even if its matcher is not used). **Zingg's AGPL-3.0 is disqualifying** if SIG runs a
public web service and does not intend to AGPL the whole stack — flag this to the
licensing workstream. RecordLinkage is too dormant to depend on. Senzing costs more per
year than most of this project's likely total budget and its EULA is incompatible with an
open, reproducible pipeline.
**Outline delta:** EXTENDS §20 Q27/Q28 with a decision and its licence rationale.

### F5.30 — In-Postgres fuzzy matching covers blocking and online lookup without a second system

**Claim:** `pg_trgm` supplies indexed trigram similarity with documented default
thresholds, and is sufficient for candidate generation and interactive search.
**Status:** VERIFIED
**Evidence:** `https://www.postgresql.org/docs/current/pgtrgm.html` (HTTP 200, fetched):
functions `similarity()`, `word_similarity()`, `strict_word_similarity()`, `show_trgm()`;
operators `%` (threshold **0.3** default), `<->` distance, `<%`/`%>` (word similarity,
default **0.6**), `<<%`/`%>>` (strict word similarity, default **0.5**); GiST and GIN
operator classes (`gist_trgm_ops`, `gin_trgm_ops`) supporting similarity search, `LIKE`,
`ILIKE`, regex and equality. `fuzzystrmatch` (levenshtein, soundex, metaphone,
dmetaphone) is a separate contrib module — **its documentation was not fetched; treat the
function list as unverified.**
**Retrieved:** 2026-08-20
**Implication for the spec:** Use `pg_trgm` GIN indexes on `normalized_name` for (a) the
blocking/candidate-generation step feeding Splink and (b) the live "find this agency"
search box, which needs sub-100ms latency that a batch Splink model cannot provide.
Do **not** use `pg_trgm` similarity as a decision score — it is uncalibrated and has no
probabilistic interpretation. Candidate generation only.
**Outline delta:** EXTENDS §20 Q20 — has architectural implications for the storage
decision (a PostgreSQL/PostGIS core gets ER blocking for free).

### F5.31 — LLM-assisted matching is a 2025–2026 research frontier, not a production default

**Claim:** Current literature positions LLMs as an accuracy improvement on *hard* pairs
that still requires classical blocking for tractability and cost control.
**Status:** PARTIALLY VERIFIED (abstracts and search summaries only; two full texts were
blocked)
**Evidence:** Located but **not fully retrieved** —
`https://doi.org/10.3390/a18110723` "Efficient Record Linkage in the Age of Large Language
Models: The Critical Role of Blocking" (redirect to `mdpi.com`, then **HTTP 403**);
"Entity Matching with LLMs at Scale: Accuracy, Cost, and Reasoning Effects"
(link.springer.com, benchmarks 46 LLM configurations across 8 datasets under the ComEM
framework); "In-context Clustering-based Entity Resolution with LLMs"
(`https://dl.acm.org/doi/10.1145/3749170`); "Fine-tuning Large Language Models for Entity
Matching" (`https://arxiv.org/pdf/2409.08185`); "Adaptive Graph Refinement and Label
Propagation with LLMs for Cost-Effective Entity Resolution"
(`https://arxiv.org/pdf/2605.25814`); LinkTransformer
(`https://arxiv.org/pdf/2309.00789`). Consistent themes across abstracts: blocking remains
necessary for scalability regardless of LLM use; fine-tuned small models approach large-model
accuracy at far lower cost and carbon.
**Retrieved:** 2026-08-20
**Implication for the spec:** Use an LLM in exactly one place — as a **reviewer's
assistant on the human queue**, generating a short rationale ("these differ only by
'Department' vs 'Office'; both are in Los Angeles County; the ORI matches") that a human
approves or rejects. Never let an LLM write to the graph. Log the model ID and prompt
version alongside the human decision so the label set stays auditable and the LLM's own
error rate becomes measurable. Rationale: LLM scores are not calibrated, are not
reproducible across model versions, and would silently corrupt the very confidence
semantics §9.3 depends on.
**Outline delta:** EXTENDS §20 Q28 — gives "model-assisted matching" a bounded, safe role
rather than leaving it open.

## D.2 Name normalization for U.S. agencies — the rule set

This is designed against the observed morphology in F5.6 and F5.7, plus the Flock slug
grammar in F5.26. It is deliberately specified as a **pure, deterministic, testable
function** with an ordered pipeline, so its output can be stored, indexed and diffed.

```
FUNCTION normalize_org_name(raw: string, hints: {state?, org_class?}) -> NormalizedName

# ---------- Stage 0: split hierarchical and parenthetical structure ----------
0.1  If raw matches /^(?<parent>[^:]+):\s*(?<child>.+)$/          # 17.2% of CDE names
         emit parent_part := parent; local_part := child
     else parent_part := null; local_part := raw
0.2  Strip trailing disambiguators into a separate field:
         /,\s*(?<disambig>[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s+County)$/   # "…, Lawrence County"
         /\((?<disambig>[^)]*)\)$/
0.3  Continue the pipeline on local_part; retain parent_part and disambig as
     structured attributes, NOT as part of the normalized string.

# ---------- Stage 1: character normalization ----------
1.1  Unicode NFKC, then NFKD → strip combining marks → ASCII fold
         "Cañon City"  -> "Canon City"
         "Coeur d’Alene" -> "Coeur d'Alene"
1.2  Lowercase.
1.3  Replace typographic apostrophes (U+2019, U+02BC, U+0060) with ASCII "'".
1.4  Remove ALL apostrophes:  "sheriff's" -> "sheriffs"
     (justification: "Sheriff's" / "Sheriffs" / "Sheriffs'" all occur in the wild
      and none of the three is ever semantically distinct)
1.5  Replace "&" with " and ".
1.6  Replace "/" and "\" and "—" and "–" and "_" with " ".
1.7  Replace all remaining non-[a-z0-9 ] with " ".
1.8  Collapse runs of whitespace to one space; trim.

# ---------- Stage 2: token-level abbreviation expansion ----------
# Applied left-to-right, whole-token only. Ordering matters: longest phrase first.

2.1  PHRASE expansions (multi-token, applied before single-token):
     "co sheriff"              -> "county sheriffs office"
     "cnty sheriff"            -> "county sheriffs office"
     "dept of public safety"   -> "department of public safety"
     "dept of police"          -> "police department"
     "div of"                  -> "division of"
     "bureau of investigation" -> "bureau of investigation"      # no-op, anchors below

2.2  SUFFIX-POSITION expansions (only when the token is the LAST token):
     "pd"      -> "police department"
     "p d"     -> "police department"
     "so"      -> "sheriffs office"
     "s o"     -> "sheriffs office"
     "sd"      -> "sheriffs department"   IF preceding tokens contain "county"
                  ELSE "school district"                  # the Flock -sd ambiguity
     "dps"     -> "department of public safety"
     "cso"     -> "county sheriffs office"
     "pdept"   -> "police department"
     "police"  -> "police department"     ONLY IF org_class hint is law_enforcement
                                          AND no other suffix marker present

2.3  ANYWHERE token expansions:
     dept | dep | dpt        -> department
     depts                   -> departments
     div                     -> division
     bur                     -> bureau
     ofc | off               -> office
     twp | twsp | tsp | tp   -> township
     cnty | cty | co         -> county          # see 2.3.1
     st                      -> SEE 2.4 (ambiguous)
     mt | mtn                -> mount           # "Mt. Vernon" -> "mount vernon"
     ft                      -> fort
     pt                      -> port            # unless final token in a Flock slug
     spgs | spg              -> springs
     hts                     -> heights
     jct                     -> junction
     vlg | vill              -> village
     bch                     -> beach
     lk                      -> lake
     is | isl                -> island
     univ                    -> university
     coll                    -> college
     comm                    -> community
     isd                     -> independent school district
     usd                     -> unified school district
     csd                     -> consolidated school district
     rtcc                    -> real time crime center
     ada | da                -> district attorney            # only when standalone
     hwy                     -> highway
     pat                     -> patrol
     natl | nat              -> national
     govt | gov              -> government
     auth                    -> authority
     intl | intnl            -> international
     med                     -> medical
     ctr | cntr              -> center
     hosp                    -> hospital
     apts                    -> apartments
     hoa                     -> homeowners association
     poa                     -> property owners association
     coa                     -> condominium owners association

     2.3.1  "co" -> "county" ONLY when followed by one of
            {sheriff, sheriffs, police, pd, so, jail, constable, marshal}
            OR preceded by a known county name for hints.state.
            Otherwise "co" -> "company".        # "Acme Security Co"

2.4  "st" DISAMBIGUATION (the saint-vs-street problem):
     IF "st" is the FIRST token of local_part          -> "saint"     # "St. Louis"
     ELIF the next token is a known saint-name from SAINT_NAMES       -> "saint"
          SAINT_NAMES = {louis, paul, petersburg, cloud, charles, joseph, augustine,
                         george, john, johns, james, marys, mary, ann, anne, albans,
                         helena, matthews, peters, francis, clair, croix, tammany,
                         bernard, landry, martin, lucie, johnsbury, joe, ...}
     ELIF "st" is the LAST token or followed by a directional/number  -> "street"
     ELSE -> "saint"                                   # bias to saint in org names
     # Rationale: in ORGANIZATION names "st" is overwhelmingly Saint; "street" occurs
     # essentially only inside addresses, which are a separate field.

2.5  DIRECTIONAL normalization (expand, do not abbreviate):
     n->north  s->south  e->east  w->west
     ne->northeast  nw->northwest  se->southeast  sw->southwest
     Applied ONLY when the token is a leading token or immediately precedes a
     place-name token. Never applied to a token that is itself a known place name
     ("North Las Vegas" stays "north las vegas"; "N Ave" is address, not org).

# ---------- Stage 3: governmental-prefix canonicalization ----------
3.1  Strip leading governmental wrappers into a structured flag, not the string:
        /^(the )?(city|town|village|borough|township|county|parish|city and county) of\s+/
     "city of los angeles police department" -> gov_prefix := "city of"
                                                core := "los angeles police department"
3.2  Strip trailing governmental wrappers likewise:
        /\s+(city|town|village|borough|township)$/   when Census LSAD says so
        "los angeles city" -> "los angeles"          # Census place-name form

# ---------- Stage 4: agency-suffix canonicalization ----------
4.1  Detect and normalize the agency-type suffix into BOTH a canonical string form
     and a structured org_class:
        "police department" | "police dept" | "police" | "dept of police"
                                                  -> SUFFIX=police department
        "sheriffs office" | "sheriffs department" | "sheriffs dept" | "sheriff"
                                                  -> SUFFIX=sheriffs office
        "department of public safety" | "public safety department"
                                                  -> SUFFIX=department of public safety
        "state police" | "highway patrol" | "state patrol" | "state highway patrol"
                                                  -> SUFFIX=state police
        "marshals office" | "marshal"             -> SUFFIX=marshals office
        "constable"                               -> SUFFIX=constable
     4.1.1  CRITICAL: "sheriffs office" and "sheriffs department" MUST normalize to
            the SAME canonical suffix. FBI CDE renders every sheriff as "Office"
            (F5.6) while ~40% of sheriffs legally style themselves "Department".
            Failing to collapse these produces a false non-match on 2,765 agencies.

# ---------- Stage 5: emit ----------
RETURN NormalizedName {
   norm_full   : gov_prefix-stripped, suffix-canonicalized, space-collapsed string
                 e.g. "los angeles county sheriffs office"
   norm_core   : norm_full with the agency suffix removed
                 e.g. "los angeles county"
   norm_sorted : tokens of norm_core sorted alphabetically, space-joined
                 e.g. "angeles county los"            # order-insensitive blocking key
   suffix      : canonical agency suffix or null
   gov_prefix  : "city of" | "town of" | ... | null
   parent_part : normalized parent (from Stage 0.1) or null
   disambig    : disambiguator string or null
   soundex_core: soundex(first content token of norm_core)
   trigrams    : pg_trgm show_trgm(norm_full)         # for GIN index
}
```

**Test vectors** (each MUST be asserted in the test suite):

| Input | `norm_full` | `norm_core` | `suffix` |
|---|---|---|---|
| `Los Angeles Police Department` | `los angeles police department` | `los angeles` | `police department` |
| `LAPD` | `lapd` | `lapd` | *null* (acronym — see below) |
| `City of Los Angeles Police Dept.` | `los angeles police department` | `los angeles` | `police department` |
| `Los Angeles County Sheriff's Department` | `los angeles county sheriffs office` | `los angeles county` | `sheriffs office` |
| `Los Angeles County Sheriff's Office` | `los angeles county sheriffs office` | `los angeles county` | `sheriffs office` |
| `St. Louis Metropolitan PD` | `saint louis metropolitan police department` | `saint louis metropolitan` | `police department` |
| `Mt. Vernon Twp Police` | `mount vernon township police department` | `mount vernon township` | `police department` |
| `Cañon City PD` | `canon city police department` | `canon city` | `police department` |
| `okaloosa-county-fl-so` (slug) | `okaloosa county sheriffs office` | `okaloosa county` | `sheriffs office` |
| `frisco-tx-pd` (slug) | `frisco police department` | `frisco` | `police department` |
| `Harris County Constable: Precinct 4` | `precinct 4` (parent=`harris county constable`) | `precinct 4` | `constable` |
| `Coeur d'Alene Police Department` | `coeur dalene police department` | `coeur dalene` | `police department` |

**Acronyms are handled separately, not by normalization.** `LAPD`, `NYPD`, `LASD`,
`CHP`, `MSP` cannot be expanded by rule without a lookup. Maintain an
`acronym_alias` table (`acronym, sig_org_id, source, valid_from`) seeded from Wikidata
`P1813` (short name) and USAspending `alternate_names` (F5.15), and resolve acronyms by
**exact lookup only** — never by fuzzy match, because 3–4 letter strings trigram-match
everything.

## D.3 The deterministic-first cascade

Six tiers. Each incoming record from a source is run top-down and stops at the first tier
that fires. Every tier records `match_tier`, `match_evidence` and, for Tier 5, the Splink
match weight, on the resulting `Claim`.

```
TIER 0 — EXACT SOURCE-KEY REPLAY                                   AUTO-WRITE
  Condition: (source_system, source_native_id) already mapped in source_identity_map
  Example:   Atlas AOSNUMBER "AOS000001"; OSM node id; Flock slug seen before
  Action:    reuse the existing sig_org_id.
  Rationale: idempotent re-ingest. Must never re-run matching on a known key.
  Expected precision: 1.000 by construction.

TIER 1 — EXACT AUTHORITATIVE IDENTIFIER                            AUTO-WRITE
  Condition: exact, case-normalized match on any of
             ORI9 | LEAID | UNITID | NTD ID | CCN | UEI | LEI | GEOID(+level)
  Example:   Atlas NEWAOSNUMBER[0:9] == CDE ori  (81.3% of Atlas rows, F5.11)
  Guards:    - ORI must pass ^[A-Z0-9]{9}$ (F5.4)
             - reject ORIs whose 9th char is alphabetic UNLESS org_class is already
               known to be law_enforcement (civil/applicant ORI risk, F5.8)
             - GEOID match requires the level to match too (F5.18 ambiguity)
  Expected precision: >0.999.

TIER 2 — EXACT NORMALIZED NAME + JURISDICTION + CLASS              AUTO-WRITE
  Condition: norm_full equal AND state equal AND org_class compatible
  Measured ambiguity: 0.02% of the FBI universe (4 rows / 2 keys, F5.7)
  Guards:    - the two known in-state collisions are hard-coded to Tier 4
             - if county is available on both sides, require it to match too;
               that lifts ambiguity to 0.00% (F5.7)
  Expected precision: >0.998.

TIER 3 — AUTHORITATIVE DOMAIN OR ADDRESS MATCH                     AUTO-WRITE (narrow)
  3a. Registrable domain (eTLD+1) match on an official .gov/.us domain
      e.g. lapdonline.org, cityofchicago.org  -> requires the domain to be recorded
      on BOTH records from a Tier-A/B source (§9.1), not scraped from a footer
  3b. Address key K1 (tigerLineId + side) match AND org_class equal (F5.24, §C.3)
  Guards:    - shared-hosting domains (govoffice.com, revize.com, municipalcms.com,
               civicplus.com, wixsite.com, squarespace.com) are DENYLISTED — many
               small municipalities share a vendor domain
             - a city hall address is shared by the city, the PD and the court;
               therefore 3b requires org_class equality
  Expected precision: >0.99.

TIER 4 — HIGH-CONFIDENCE PROBABILISTIC                             REVIEW QUEUE (priority)
  Condition: Splink match weight M >= 12  (P(match) ~ 0.99976)
  Action:    create a PROPOSED same_as claim; enqueue for human review at high priority
  NEVER auto-writes. This is the outline's explicit requirement (§20 Q28).

TIER 5 — CANDIDATE PROBABILISTIC                                   REVIEW QUEUE (normal)
  Condition: 6 <= M < 12   (P(match) ~ 0.984 to 0.99976)
  Action:    enqueue for human review at normal priority.

TIER 6 — BELOW THRESHOLD                                           NO CLAIM
  Condition: M < 6
  Action:    discard the pair; record only an aggregate counter for §7.1 Goal 6
             (quantify incompleteness). Do not persist a per-pair record — at
             10^5 entities the sub-threshold pair set is the bulk of the data.
```

**Auto-write threshold justification.** M ≥ 12 corresponds to P(match) ≈ 0.99976, i.e. an
expected ~1 false merge per 4,000 auto-written pairs. Even that is deliberately **not**
auto-written, because a false merge in this graph does not produce a slightly wrong
statistic — it produces a public claim that Agency A has access to Agency B's camera
network. The asymmetry of harm between a false merge and a missed merge is severe and
one-directional, so the cascade is tuned for precision and pushes all residual risk into
human review. Tiers 0–3 auto-write because they are *deterministic*, not because they are
*confident*: their failure modes are enumerable and testable, whereas a probabilistic
score's failure modes are not.

**Review-queue mechanics.** Each queued item carries: the two records side by side; the
Splink waterfall decomposition (per-comparison log₂ contributions, F5.27); the tier that
almost fired and why it didn't; and a three-way decision — `SAME` / `DIFFERENT` /
`INSUFFICIENT_EVIDENCE`. All three outcomes are written as labels (§D.6).
`INSUFFICIENT_EVIDENCE` is a first-class outcome, not a deferral, and maps onto the
outline's §6.5 "contradiction as a first-class state".

## D.4 Blocking and candidate generation at scale

```
Blocking rules (OR-combined, per Splink's "many strict rules" guidance, F5.27):

  B1  exact(norm_full)
  B2  exact(state) AND exact(norm_core)
  B3  exact(state) AND exact(soundex_core) AND exact(suffix)
  B4  exact(county_geoid) AND exact(suffix)
  B5  exact(place_geoid)
  B6  exact(registrable_domain)
  B7  exact(norm_sorted)                       # token-order-insensitive
  B8  exact(state) AND substr(norm_core, 1, 4) # prefix block, tight because of state

Sizing:  run splink.count_comparisons_from_blocking_rule() for each rule BEFORE
         enabling it; reject any single rule producing >5e6 pairs on the org table.
Anti-rule: NEVER block on suffix alone (would emit ~10^8 pairs from
           "police department" alone) or on state alone.
Online path: pg_trgm GIN index on norm_full, `WHERE norm_full % $1 ORDER BY
             norm_full <-> $1 LIMIT 50` for interactive search (F5.30).
```

At SIG's scale (10⁴–10⁵ organizations) the entire blocked pair set is small enough that
the ER pass is a CI job, not a service. Design for that: **run ER as a reproducible batch
that emits a diff against the previous run**, so every change to the matcher produces a
reviewable changeset rather than a silent re-clustering. This is what makes the ID
stability guarantees in §E enforceable.

## D.5 Temporal identity: mergers, splits, renames, dissolutions (Q29)

### F5.32 — ROR, GLEIF and RiC-O each solve part of this; the union is the right model

**Claim:** Three mature systems independently converged on: an immutable identifier, a
lifecycle status, typed succession relations, and (in RiC-O) date-qualified n-ary relation
objects. OpenAlex is the counterexample showing what happens without them.
**Status:** VERIFIED
**Evidence:**
- **ROR** (`https://api.ror.org/v2/organizations?filter=status:withdrawn`, HTTP 200):
  **1,409 withdrawn** and **1,595 inactive** records. A withdrawn record **keeps its ID
  and gains a `successor` relationship** — e.g. `https://ror.org/05pg0e416` (withdrawn)
  → `successor: https://ror.org/038ajzz56`; `https://ror.org/036f6kk02` → `successor:
  https://ror.org/0217hsv85`. Some withdrawn records have no successor (true
  dissolutions). Status vocabulary: `active | inactive | withdrawn`. Relationship
  vocabulary (confirmed via ROR docs/search): **parent, child, related, predecessor,
  successor**. ROR's stated policy: "The identifier itself is permanent once issued…
  If your institution is renamed, restructured, merged, or split after registration, you
  request an update to the existing record… you don't get a new ROR ID."
- **GLEIF** (F5.13): `entity.status`, `entity.expiration{date, reason}`,
  `entity.successorEntity{lei, name}`, `entity.successorEntities[]` (plural — handles
  splits), `entity.creationDate`, and `entity.eventGroups[].events[]` with
  `{type, effectiveDate, recordedDate, status, validationDocuments}` — separating
  **effective date (valid time)** from **recorded date (transaction time)**, which is
  exactly the bitemporality §9.2 demands. Observed event types include
  `CHANGE_LEGAL_ADDRESS` and `DISSOLUTION`. `registration.status = RETIRED` on 249,910
  records. `eventGroups[].groupType` distinguishes `STANDALONE` from multi-event groups
  (a merger is one group of correlated events across entities).
- **RiC-O v1.1** (`https://www.ica.org/standards/RiC/ontology`, HTTP 200, fetched;
  released 2025-05-22, aligned to RiC-CM 1.0): relations
  **`hasSuccessor`/`isSuccessorOf`**, **`wasMergedInto`/`resultedFromTheMergerOf`**,
  **`wasSplitInto`/`resultedFromTheSplitOf`**, `hasOrHadCorporateBodyType`,
  `isOrWasMemberOf`; and an **`AgentTemporalRelation` class** carrying certainty and
  dates, with `relationHasDate` — i.e. relations are reified as entities so they can be
  time-bounded and sourced. RiC-CM defines 78 relations over Agent (Person, Family,
  Corporate Body, Position, Mechanism).
- **EAC-CPF**: `@cpfRelationType` vocabulary is
  `identity | hierarchical | hierarchical-parent | hierarchical-child | temporal |
  temporal-earlier | temporal-later | family | associative`
  (`http://www3.iath.virginia.edu/eac/cpf/tagLibrary/cpfTagLibrary.html`;
  `https://eac.staatsbibliothek-berlin.de/schema/taglibrary/cpfTagLibrary2019_EN.html`,
  HTTP 200). In EAC-CPF **2.0**, `<cpfRelation>` was replaced by `<targetEntity>` with
  `@targetType ∈ {person, family, corporateBody, agent}`. The
  `temporal-earlier`/`temporal-later` pair is the archival community's minimal
  succession primitive, and `identity` is its `same_as`.
- **OpenAlex — the counterexample.** The S3 snapshot no longer contains a `merged_ids`
  directory: `https://openalex.s3.amazonaws.com/?list-type=2&delimiter=/&prefix=data/merged_ids/`
  returns `KeyCount: 0`, and the only prefixes under `data/` are `jsonl/` and `parquet/`
  (22 entity types, none of them merges). Probing merged institution IDs against the API
  gave `200` for live IDs and **`404` for `I2802834376`** — **no redirect, no tombstone,
  no successor pointer.** A consumer holding a stale OpenAlex ID has no programmatic way
  to recover the surviving entity.
**Retrieved:** 2026-08-20
**Implication for the spec:** Adopt the model below. Explicitly do not copy OpenAlex.
**Outline delta:** **EXTENDS §20 Q29 and §6.3 substantially.** The outline asks "how
should aliases and mergers be represented" without proposing a model; this is the model,
grounded in three independent implementations.

### The recommended SIG temporal identity model

```
Organization                       -- the identity, never deleted, never reused
  sig_org_id            PK, immutable, minted once (§E)
  status                active | inactive | withdrawn | suppressed
                        -- active:    currently exists
                        -- inactive:  ceased to exist; record remains authoritative
                        -- withdrawn: should never have existed as a separate identity
                                      (duplicate); MUST carry a successor
                        -- suppressed: exists but not published (§C.4 policy)
  created_at            transaction time of minting
  identity_basis        JSONB, immutable (§C.1)

OrganizationVersion                -- bitemporal attribute state (§9.2)
  sig_org_id            FK
  valid_from, valid_to  VALID TIME  (when the world was like this)
  recorded_from, recorded_to  TRANSACTION TIME (when we believed it)
  canonical_name, registry_name, org_class, parent_org_id,
  jurisdiction_geoid, addresses, identifiers[]
  source_claim_ids[]    provenance for every field (§6.4)

OrganizationRelation               -- reified, following RiC-O AgentTemporalRelation
  relation_id           PK
  subject_org_id, object_org_id
  relation_type         ENUM (below)
  valid_from, valid_to  VALID TIME
  recorded_from, recorded_to
  certainty             asserted | probable | disputed
  evidence_claim_ids[]
  note

relation_type vocabulary (7 values, deliberately small):
  same_as        -- two SIG identities are one entity. Resolution: one becomes
                    `withdrawn` with a `succeeded_by` to the survivor. `same_as` is
                    the pre-resolution assertion; it is never a permanent state.
  succeeded_by   -- subject ceased; object continues its identity/function.
                    Rename, reorganization, recharter.        [RiC-O hasSuccessor]
  merged_into    -- subject ceased; its function/assets absorbed by object, which
                    pre-existed.                              [RiC-O wasMergedInto]
  split_into     -- subject ceased; two or more objects arose.
                    Emitted once per object.                  [RiC-O wasSplitInto]
  absorbed       -- subject CONTINUES to exist but took over object's function
                    (object gets `merged_into` subject). Distinguishes "the PD
                    disbanded and the county sheriff now patrols the city" from
                    "the two departments consolidated into a new one."
  parent_of      -- structural containment, not succession.   [RiC-O hierarchical]
  acquired       -- corporate: object's ownership passed to subject; BOTH may
                    continue to exist as legal entities.      [Axon -> Fusus]
```

**Worked cases, each of which the model must handle and each of which should be a
fixture in the test suite:**

1. **PD disbanded, absorbed by county sheriff.** `Cityville PD` gets
   `status = inactive`, `valid_to = 2025-06-30`, and a relation
   `Cityville PD --merged_into--> Cityville County SO` with `valid_from = 2025-07-01`.
   The sheriff also gets `--absorbed--> Cityville PD`. Cityville PD's `sig_org_id`
   remains resolvable forever; its historical deployments, contracts and portal
   snapshots stay attached to it and are **not** silently reassigned to the sheriff.
   Queries "who operates cameras in Cityville today" traverse the `merged_into` edge;
   queries "who operated cameras in Cityville in 2024" do not.
2. **Vendor acquisition: Axon → Fusus (2024).** `Fusus, Inc.` keeps
   `status = active` (it continued as a subsidiary/product line) with
   `Axon Enterprise --acquired--> Fusus` valid from the closing date. Products branded
   Fusus later re-branded to Axon get `succeeded_by` at the **Product** level, not the
   Organization level. Note GLEIF cannot represent this (F5.13: Fusus has no LEI, Axon
   has 0 GLEIF children) — SIG's evidence must be the press release and any SEC filing.
3. **Rename only.** `Sheriff's Department` → `Sheriff's Office`: this is **not** a
   succession. It is a new `OrganizationVersion` with a new `canonical_name` and the
   old name demoted to `aliases[]` with `valid_to` set. The `sig_org_id` does not change
   and no relation is emitted. Getting this wrong — treating renames as successions —
   is the most common failure mode and would double the entity count.
4. **Merger of equals into a new entity.** Both predecessors go `inactive` with
   `merged_into` pointing at a **newly minted** `sig_org_id`, which carries
   `identity_basis.predecessors = [id1, id2]`.
5. **Bad merge discovered later (a split of a SIG cluster).** The erroneously-merged
   record is **not** un-merged in place. Instead: the surviving ID keeps whichever
   constituent has the stronger identity claim; a **new** `sig_org_id` is minted for the
   extracted constituent; a `SplitEvent` is recorded; and any previously-withdrawn ID
   that pointed at the survivor is **re-pointed** to the correct target with its
   `succeeded_by` relation `valid_to`-closed and a new one opened. Consumers see a
   changed redirect target, never a 404. (This is the case OpenAlex cannot express.)

## D.6 ER evaluation and the gold-standard protocol

Because Splink's own guidance is a stub (F5.28), SIG owns this. Recommended protocol:

```
GOLD SET CONSTRUCTION

G1  Sampling frame. Draw from the BLOCKED pair set, not from all pairs — an
    unblocked random sample is ~100% trivial non-matches and measures nothing.
    Stratify by predicted match weight into 6 bands:
      M < 0 | 0-3 | 3-6 | 6-9 | 9-12 | >= 12
    Sample n=200 per band -> 1,200 pairs. Oversampling the decision boundary is
    the point: precision/recall near the threshold is what determines behaviour.

G2  Independent double adjudication. Two annotators label each pair blind to the
    model score and to each other. Report Cohen's kappa. Target kappa >= 0.85;
    below that, the LABEL DEFINITION is broken, not the annotators.

G3  Label vocabulary: SAME | DIFFERENT | INSUFFICIENT_EVIDENCE.
    INSUFFICIENT_EVIDENCE pairs are excluded from precision/recall but COUNTED and
    reported — they are the honest measure of how much of the problem is
    unresolvable from available sources, feeding §7.1 Goal 6.

G4  Adjudication rules must be written down before labelling, minimally:
    - Same ORI => SAME, always.
    - Different ORI => DIFFERENT, always (ORIs are not reused across live agencies).
    - A department and its parent municipality => DIFFERENT (§C.2).
    - A department and a named unit of it ("X PD Traffic Division") => DIFFERENT,
      linked by parent_of.
    - Pre- and post-rename of the same continuing body => SAME.
    - Predecessor and successor across a merger => DIFFERENT, linked by merged_into.
    (That last pair of rules is where annotators will disagree; it must be explicit.)

G5  Provenance. Every label stores annotator id, timestamp, model version, and the
    evidence URLs consulted. Labels are versioned data, not a spreadsheet.

G6  Freeze a HOLDOUT of 30% that is never used for threshold tuning.

METRICS REPORTED ON EVERY ER RUN (all on the holdout)
  Pairwise:   precision, recall, F1 at each tier boundary; precision-recall curve;
              the threshold-selection chart from Splink's labels table.
  Cluster:    B-cubed precision/recall (the standard for clustering ER, robust to
              cluster-size skew); cluster purity; number of clusters.
  Graph:      Splink's cluster density, node centrality, bridge count (F5.27) —
              used as ALERTS, not scores. Concretely:
                - any cluster with size > 5 for org_class in {municipal_pd, sheriff}
                  is auto-flagged (real agencies rarely have >5 source records that
                  are genuinely the same and not already Tier-1 linked)
                - any cluster whose removal-of-one-bridge would split it into two
                  components each of size >= 2 is auto-flagged
  Stability:  count of merges, splits, and redirect-target changes vs the previous
              run (§E.4). A run that changes >0.5% of public IDs' resolution
              targets must block release and require sign-off.

RELEASE GATE
  Tier 0-3 auto-write precision on holdout must be >= 0.998, or the tier is
  demoted to review-queue until fixed.
```

---

# E. The SIG public identifier scheme (Q37)

## F5.33 — ROR's identifier design is the best available template: opaque, checksummed, dereferenceable, immutable

**Claim:** ROR IDs are 9 characters — a leading zero, six Crockford base-32 characters,
and a two-digit ISO/IEC 7064 checksum — served as `https://ror.org/{id}`, permanent once
issued.
**Status:** VERIFIED
**Evidence:** ROR documentation (`https://ror.readme.io/docs/identifier`,
`https://ror.org/about/faqs/`, retrieved via search): "The unique string consists of 9
characters: a zero, 6 characters that can be either lower-case letters or integers, and 2
concluding integers. The unique string always begins with a zero so that ROR ID landing
pages such as `https://ror.org/02mhbdp94` can be easily differentiated from ROR web pages
such as `https://ror.org/about`." Encoding is **Crockford base-32** (excludes I, L, O, U);
the final 2 digits are a **ISO/IEC 7064:2003** checksum. Live IDs observed in this
research conform: `01an7q238`, `05pg0e416`, `036f6kk02`, `00pjdza24`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Copy four properties: (1) opaque, so the ID carries no
mutable semantics; (2) check-character, so typos and truncations fail loudly rather than
silently resolving to a different entity; (3) a distinguishing prefix so IDs are not
confusable with site paths; (4) Crockford base-32, which is case-insensitive and excludes
the I/L/O/U confusables.
**Outline delta:** EXTENDS §20 Q37 with a proven concrete design.

## F5.34 — W3C's persistence guidance: opaque, technology-free, subdomain-isolated URIs

**Claim:** W3C's *Cool URIs for the Semantic Web* prescribes simplicity, stability
(URIs unchanged "for years or decades"), no technology artefacts in the path, and a
dedicated subdomain to permit future migration; 303 redirects for large evolving
datasets, hash URIs for small stable vocabularies.
**Status:** VERIFIED
**Evidence:** `https://www.w3.org/TR/cooluris/` — **HTTP 403 to curl with a browser UA**,
but **successfully fetched via the WebFetch tool**, returning: the three design principles
(simplicity, stability, manageability), the recommendation to use "dedicated subdomains
(e.g. id.example.com) [to] ease future system migration", "Implementation details like
'.php' should be avoided since technologies evolve", the 303-vs-hash tradeoff ("Better for
large, evolving datasets" vs "Best for small, stable vocabularies"), content negotiation
via Accept headers with quality scores, and Tim Berners-Lee's "Cool URIs don't change".
**Retrieved:** 2026-08-20
**Implication for the spec:** Serve SIG identifiers from a dedicated `id.` subdomain with
no file extensions and no framework artefacts in the path, with content negotiation
between HTML and JSON-LD.
**Outline delta:** EXTENDS §20 Q37.

## F5.35 — UUIDv7 (RFC 9562) gives time-ordered, collision-free minting without coordination

**Claim:** RFC 9562 standardizes UUIDv7 as a 128-bit, Unix-ms-timestamp-prefixed,
random-suffixed identifier suitable for database primary keys.
**Status:** VERIFIED (document retrievable)
**Evidence:** `https://www.rfc-editor.org/rfc/rfc9562.txt` → HTTP 200. RFC 9562 obsoletes
RFC 4122 and defines UUID versions 6, 7 and 8; version 7 is the
`unix_ts_ms || rand_a || var || rand_b` layout.
**Retrieved:** 2026-08-20
**Implication for the spec:** UUIDv7 gives monotonic index locality (unlike UUIDv4) and
requires no central sequence, so multiple ingest workers can mint concurrently. Its
128-bit width is the raw material for the public ID below.

## E.1 The recommended SIG identifier

```
FORM      sig:<type>:<base32-24><check>
EXAMPLE   sig:org:0k3q7wz9m2xr4b8n5tvd7h
          sig:jur:0m1n8pqr3s5t7v9wxy2z4a
          sig:dev:0p4r6s8t0v2w4x6y8z1a3b
          sig:doc:0q5s7t9v1w3x5y7z9a2b4c

CONSTRUCTION
  1. mint uuid7 := UUIDv7()                          (RFC 9562, F5.35)
  2. take the low 120 bits                            -> 24 Crockford base-32 chars
  3. force the first character to '0'                 (ROR's disambiguation trick, F5.33)
  4. append 1 ISO/IEC 7064 MOD 37,36 check character  (F5.33)
  5. total: 25 characters, lower-case, [0-9a-hjkmnp-tv-z]

TYPE PREFIXES (closed vocabulary, one per top-level §8 entity)
  org  jur  ven  prd  tec  dep  ast  sys  acc  int  con  pol  cfg  usg  inc  evd  clm

PROPERTIES
  - Case-insensitive on input (Crockford); canonical serialization is lower-case.
  - Opaque: encodes nothing except mint time, which is not semantically load-bearing.
  - Self-validating: a single transposed or dropped character fails the check character.
  - Sortable by mint time (UUIDv7 prefix) for stable pagination and change feeds.
  - Not content-addressed. Deliberately: content-addressing an entity whose attributes
    change by design would change the ID on every correction, which is precisely the
    failure mode §E.4 exists to prevent. Content-addressing IS used, separately, for
    EvidenceArtifact blobs (§20 Q25) — a different problem with the opposite requirement.
```

**Why not a readable ID** (e.g. `sig:org:us-ca-los-angeles-pd`)? Because readable IDs
encode assertions — jurisdiction, state, agency type — that are exactly the assertions
most likely to be corrected. A department reincorporates, a city renames, a match is found
to be wrong: the readable ID becomes a lie that is now embedded in other people's
databases. ROR, ORCID, DOI, LEI and GLEIF all chose opacity for this reason. Readability
is served by a **slug alias**, not by the identifier:
`https://id.<sig>/org/us-ca-los-angeles-police-department` → **302** (temporary, because
slugs may be reassigned) → the canonical opaque URI. Slugs are unique, mutable, and
explicitly documented as non-citable.

## E.2 URI and resolution design

```
Canonical URI     https://id.<sigdomain>/org/0k3q7wz9m2xr4b8n5tvd7h
                  (dedicated subdomain, no extension — F5.34)

Content negotiation on the canonical URI:
  Accept: text/html          -> 303 -> https://<sigdomain>/org/0k3q.../   (human page)
  Accept: application/json   -> 200   JSON  representation
  Accept: application/ld+json-> 200   JSON-LD with @context mapping to schema.org
                                       GovernmentOrganization / Organization,
                                       plus owl:sameAs to Wikidata/ROR/GLEIF/GEOID
  Accept: text/turtle        -> 200   RDF

Lifecycle responses:
  active                 -> 200
  inactive               -> 200  with {"status":"inactive","valid_to":...} and any
                                  succeeded_by / merged_into links in the payload.
                                  NOT a redirect: the entity really existed and its
                                  historical claims are still about IT.
  withdrawn (duplicate)  -> 301 Moved Permanently -> Location: canonical successor URI
                                  AND a 200-able tombstone at
                                  https://id.<sig>/org/<id>/tombstone
  suppressed (§C.4)      -> 200 with a minimal record: type, class, jurisdiction,
                                  and {"suppressed": true, "reason": "privacy_policy"}
                                  -- never 404, because 404 destroys the ability of a
                                  downstream consumer to distinguish "never existed"
                                  from "deliberately not published"
  never issued           -> 404

Every response carries:  Link: <https://id.../org/<id>>; rel="canonical"
                         ETag, Last-Modified
                         Cache-Control with a short max-age (identity can change)
```

**IDs are never reused, never deleted, never recycled.** A withdrawn ID resolves forever.
This is the concrete answer to §20 Q37: it is the redirect guarantee, not the ID format,
that makes it safe for another project to link back.

## E.3 The `sameAs` crosswalk table

```sql
CREATE TABLE identifier_link (
  sig_id          text     NOT NULL,           -- sig:org:0k3q...
  scheme          text     NOT NULL,           -- controlled vocabulary, below
  value           text     NOT NULL,           -- the external identifier, verbatim
  uri             text,                        -- resolvable form, if any
  relation        text     NOT NULL            -- 'exact' | 'broader' | 'narrower' | 'related'
                     DEFAULT 'exact',
  source_claim_id text     NOT NULL,           -- provenance (§6.4)
  confidence      numeric,                     -- null for deterministic tiers
  match_tier      int      NOT NULL,           -- 0..5, from §D.3
  valid_from      date,
  valid_to        date,
  recorded_from   timestamptz NOT NULL,
  recorded_to     timestamptz,
  PRIMARY KEY (sig_id, scheme, value, recorded_from)
);

-- scheme vocabulary (all verified in this file)
--  fbi-ori9            F5.1      us-census-geoid     F5.18     us-gnis           F5.22
--  nces-leaid          F5.23     ipeds-unitid        F5.23     ntd-id            F5.23
--  cms-ccn             F5.23     npi                 F5.23     sam-uei           F5.15
--  irs-ein             F5.23     gleif-lei           F5.13     opencorporates    F5.13
--  wikidata-qid        F5.12     ror                 F5.17     geonames          F5.24
--  osm-relation / osm-node                            eff-atlas-aosnumber        F5.11
--  flock-portal-slug   F5.26     iso3166-1 / iso3166-2 / nuts / insee-cog        F5.24
```

**Published as a downloadable artifact.** Ship `sig-crosswalk.csv.gz` and
`sig-crosswalk.parquet` on a stable URL, updated on every release, containing
`(sig_id, scheme, value, relation, match_tier, valid_from, valid_to)`. This is the single
deliverable that makes §20 Q37 real: another project does not need SIG's API, only this
file, to join its data to SIG's. It is also the natural vehicle for redistributing the
public-domain ORI↔GEOID mapping (F5.9).

**Reverse resolution.** `https://id.<sig>/resolve?scheme=fbi-ori9&value=CA0194200` → 303
to the canonical org URI. This is how DeFlock, Atlas, HIBF or a local group looks up "what
is SIG's ID for the agency I already know by ORI".

## E.4 Cluster stability under merges and splits

The mechanism, stated as invariants the implementation must uphold:

```
INV-1  A sig_id, once minted and published, is never deleted and never reassigned
       to a different entity.
INV-2  Every sig_id resolves to something forever: 200 (active/inactive/suppressed),
       or 301 to its successor (withdrawn). Never 404 after first publication.
INV-3  Merging clusters A and B: the SURVIVOR is chosen by a deterministic,
       documented rule, applied in order:
         (a) the one holding an authoritative external identifier (ORI > GEOID > UEI);
             if both, the one whose identifier is of higher authority rank
         (b) the one with the earlier `created_at` (UUIDv7 makes this total and stable)
       The loser becomes `withdrawn` with `succeeded_by -> survivor`.
       Deterministic survivor selection is what makes re-running ER from scratch
       reproduce the same public IDs.
INV-4  Splitting a cluster: the survivor RETAINS the original sig_id; each extracted
       constituent gets a NEWLY MINTED sig_id. Never mint two new IDs and retire the
       original -- that breaks every existing external link.
INV-5  Re-pointing: if an already-withdrawn ID's successor is itself later split, the
       withdrawn ID's `succeeded_by` is closed (`valid_to`) and a new one opened to
       the correct target. The redirect target changes; the redirect never disappears.
INV-6  Every merge and split emits a durable, public event record:
         {event_id, event_type: merge|split|withdraw|reinstate, at, actor,
          before_ids[], after_ids[], rationale, evidence_claim_ids[]}
       published in an append-only change feed (sortable by UUIDv7, §E.1).
INV-7  ER is a reproducible batch that diffs against the previous run (§D.4). Any run
       whose diff changes the resolution target of more than 0.5% of published IDs
       blocks release pending human sign-off.
INV-8  Auto-write tiers may CREATE links. Only human review (Tier 4/5) or an explicit
       admin action may WITHDRAW a published sig_id. An automated matcher must never
       be able to retire a public identifier on its own.
```

INV-8 is the load-bearing one. It is what prevents a regression in the normalizer from
silently withdrawing a thousand public IDs overnight.

---

# F. Per-organization-class identifier table

Every row's coverage and license was checked in this session; the "Verified?" column says
how.

| Organization class | Best identifier | Format | Source (exact endpoint/file) | Coverage observed | License | Verified? |
|---|---|---|---|---|---|---|
| Municipal police dept | **ORI9** | 9 alphanum | `api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}` | 10,537 "City" agencies in 44 juris. | U.S. Gov't work / public domain (FBI UCR) — *license page 403'd, inferred from federal authorship* | ✅ downloaded, 17,891 rows |
| County sheriff | **ORI9** | 9 alphanum | same | 2,807 "County" | same | ✅ |
| State police / highway patrol | **ORI9** | 9 alphanum | same | 938 "State Police" + 1,356 "Other State Agency" | same | ✅ |
| Campus/university police | **ORI9** + **IPEDS UNITID** | 9 / 6 digits | CDE; `nces.ed.gov/ipeds/datacenter/data/HD2023.zip` | 884 CDE "University or College"; 6,163 IPEDS institutions | public domain (federal) | ✅ both downloaded |
| Tribal police | **ORI9** (+ Census AIANNH GEOID) | 9 / 4–5 | CDE; TIGER2025/AIANNH | 142 CDE "Tribal" | public domain | ✅ CDE; TIGER dir listed |
| School district police | **ORI9** + **NCES LEAID** | 9 / 7 chars | CDE; `educationdata.urban.org/api/v1/school-districts/ccd/directory/{yr}/` | 251 CDE "Independent School District:*"; 10,863 UNSD + 1,971 ELSD nationally | CCD public domain; Urban API free | ✅ both |
| Municipality / city (the government, not the PD) | **Census place GEOID** + **GNIS feature_id** | 7 / int | Gazetteer `2025_Gaz_place_national.zip`; GNIS `DomesticNames_National_Text.zip` | 32,333 places; 65,193 GNIS `Civil` features; 99.997% join | public domain (both) | ✅ downloaded, join tested |
| County | **Census county GEOID** | 5 | `2024_Gaz_counties_national.zip` | 3,222 | public domain | ✅ downloaded |
| Township / county subdivision | **Census COUSUB GEOID** | 10 | `2025_Gaz_cousubs_national.zip` | 36,427 | public domain | ✅ downloaded |
| State | **FIPS / Census GEOID** | 2 | `2025_Gaz_state_national.zip` | 52 | public domain | ✅ downloaded |
| Transit agency | **NTD ID** (+ SAM UEI in same file) | 5 digits / 12 | `data.transportation.gov/api/views/ccvf-fykn/rows.csv` | 2,916 reporters | US DOT open data | ✅ downloaded, 30 cols |
| Airport authority | **FAA LID / ICAO** (+ ORI where policed) | 3–4 / 4 | *not tested this session* | — | — | ❌ UNVERIFIED |
| Hospital (facility) | **CMS CCN** | 6 | `data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0` | 5,419 hospitals | public domain | ✅ live query |
| Healthcare org (billing entity) | **NPI (NPI-2)** | 10 digits | `npiregistry.cms.hhs.gov/api/?version=2.1` | keyless; **many-to-one vs facility** | public domain | ✅ live query, duplicate demonstrated |
| University / college | **IPEDS UNITID** | 6 digits | `nces.ed.gov/ipeds/datacenter/data/HD2023.zip` | 6,163; EIN 100%, UEI 90.6%, alias 35.8% | public domain | ✅ downloaded |
| Any federally-funded org | **SAM.gov UEI** | 12 alphanum | `api.usaspending.gov/api/v2/recipient/` (keyless) | 587 orgs matching "Police Department" | US Gov't open data | ✅ live query |
| Public/regulated company (vendor) | **GLEIF LEI** | 20 alphanum | `api.gleif.org/api/v1/lei-records`; `goldencopy.gleif.org` bulk | 3,407,300 records; 249,910 RETIRED | **CC0 1.0** | ✅ Axon record retrieved |
| Private company (vendor) | **OpenCorporates ID** (`us_de/3337819`) | jurisdiction/number | free via GLEIF `attributes.ocid`; direct API from £2,250/yr | present on Axon record | OC terms unclear; GLEIF copy is CC0 | ✅ ocid observed in GLEIF |
| Fusion center | **ORI9** if it has one, else SIG surrogate | — | CDE; Atlas `Type of LEA = Fusion Center` (88 rows) | partial | — | ✅ Atlas counts |
| Constable / marshal precinct | **ORI9** (many) or Atlas `XX…` | 9 | CDE (314 constable, 136 marshal); Atlas | partial | public domain | ✅ |
| HOA / apartment complex / mall / casino / private security | **NONE — SIG surrogate required** | `sig:org:…` | §C.1 minting | no registry exists (~365k HOAs) | n/a | ✅ absence verified |
| International jurisdiction | **GeoNames ID** + ISO 3166-1/-2 + NUTS/COG | int / codes | `geonames.org` (CC BY 4.0); GISCO NUTS 2024 JSON/CSV; INSEE COG | 12M features | CC BY 4.0 / EU open / INSEE open | ✅ GeoNames license; NUTS + INSEE reachable |
| International org (any) | **Wikidata QID** | Q + digits | `query.wikidata.org/sparql` | 1,755 US LEAs only | **CC0** | ✅ SPARQL executed |

---

## Open questions

1. **Full CDE coverage is unmeasured.** NJ, NM, OK, RI, UT, WA and WY were not retrieved
   (F5.3). The true national agency count and the true CDE↔Atlas agreement rate are both
   unknown. *Hedge:* obtain a free api.data.gov key and re-run the 56-jurisdiction pull
   (including AS, GM, MP, PR, VI) before publishing any coverage statistic. Do not quote
   17,891 as a national total.
2. **LEAIC's actual schema and row count are unverified.** Every ICPSR endpoint 403s
   (F5.9). Field names come from a data.gov description of the *1996* edition. *Hedge:*
   the spec should describe the LEAIC connector abstractly (`ORI → {fips_state,
   fips_county, fips_place, census_gov_id}`) and defer exact column names to a manual
   acquisition step, with a schema-validation gate on first load.
3. **FBI UCR's licence statement was never read.** `fbi.gov` returns 403 to automated
   clients. Public-domain status is *inferred* from federal authorship, not observed.
   *Hedge:* have a human read `https://www.fbi.gov/how-we-can-help-you/more-fbi-services-and-information/ucr`
   and record the actual terms before redistributing CDE-derived data.
4. **CDE bulk downloads are not machine-reachable.** The downloads manifest resolves but
   the S3 bucket name is injected at runtime (F5.8). If the `lee_1960_2025.csv` Law
   Enforcement Employees file contains an ORI-keyed agency master with employment counts,
   it would be a valuable second agency source. *Hedge:* capture the real S3 URL once from
   a browser session and pin it, or ask the FBI UCR program directly (`ucr@fbi.gov`).
5. **GeoNames API rate limits are unverified.** The About page states CC BY 4.0 and free
   webservices but no credit limits (F5.24). *Hedge:* use the **daily database export**,
   not the web service, so limits are irrelevant.
6. **OpenCorporates' open-data licence name is unconfirmed.** The site says "share-alike
   attribution open data" but never names ODbL (F5.14). *Hedge:* do not assume ODbL
   compatibility with the OSM licensing analysis in §20 Q13; treat as unknown until the
   public-benefit agreement is in hand.
7. **PDAP's API was unreachable and its licence unstated** (F5.16). *Hedge:* treat as a
   partnership conversation, not a connector.
8. **Flock portal access is blocked (403) and unarchived** (F5.26). The slug grammar here
   is inferred from four observed examples plus search snippets. *Hedge:* validate the
   grammar against a real slug corpus from Eyes on Flock / HIBF (workstreams covering
   §20 Q1–Q5) before hard-coding the parser; treat the `sd` suffix disambiguation as
   provisional.
9. **`fuzzystrmatch` function list is unverified** (F5.30) — only `pg_trgm` docs were
   fetched. *Hedge:* confirm `levenshtein`/`dmetaphone` availability against the target
   PostgreSQL version before depending on them.
10. **Airport-authority identifiers were not investigated.** FAA LID is the likely answer
    but was not tested. *Hedge:* mark as UNVERIFIED in the table; 20 Atlas rows are
    airport-jurisdiction, so this is low-volume.
11. **Whether SIG can lawfully redistribute the ICPSR-hosted LEAIC file** — the *data* are
    public domain per data.gov, but ICPSR imposes its own terms of use on files obtained
    through it. *Hedge:* obtain the file, read ICPSR's terms at download time, and if they
    restrict redistribution, reconstruct the crosswalk independently from CDE + Census
    Geocoder rather than redistributing ICPSR's copy.
12. **The two known in-state name collisions may not be the only ones** once NJ/NM/OK/RI/
    UT/WA/WY are added (F5.7). *Hedge:* the Tier-2 collision exclusion list must be
    *generated* from the data on each run, not hard-coded.

---

## Spec requirements emitted

**Identity sources and connectors**

- **REQ-R5-01** — The system MUST ingest the FBI CDE agency registry from
  `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}` for all 56 U.S.
  jurisdictions (50 states, DC, AS, GM, MP, PR, VI), storing all ten returned fields
  verbatim plus the county-name response key. (F5.1)
- **REQ-R5-02** — The CDE connector MUST authenticate with a registered `api.data.gov`
  key supplied by configuration, MUST NOT use `DEMO_KEY` outside development, and MUST
  treat HTTP 429 as a retryable error distinct from an empty result. (F5.2, F5.3)
- **REQ-R5-03** — Any ingest job that yields zero records for a jurisdiction MUST fail the
  run rather than persist a zero count, and MUST distinguish `absent` from `not observed`
  in the resulting claims. (F5.3)
- **REQ-R5-04** — ORI values MUST be validated against `^[A-Z0-9]{9}$` and MUST NOT be
  parsed on the assumption that positions 1–2 are a USPS state code; the system MUST
  maintain a `ucr_state_code ↔ usps_state_code` reference table containing at minimum
  `NB→NE` and `GM→GU`. (F5.4)
- **REQ-R5-05** — ORIs whose 9th character is alphabetic MUST be flagged as
  possible civil/applicant ORIs and MUST NOT be auto-linked to a surveillance-operating
  organization without a second corroborating source. (F5.4, F5.8)
- **REQ-R5-06** — CDE `latitude`/`longitude` MUST be stored with
  `geometry_precision = 'organization_centroid_or_unknown'` and MUST NOT be used for
  point-in-polygon jurisdiction assignment or as an organization address. (F5.5)
- **REQ-R5-07** — Agency names containing a colon MUST be parsed into
  `parent_organization` + local unit, and the parent MUST be materialized as its own
  Organization with a `parent_of` relation. (F5.6)
- **REQ-R5-08** — `Organization` MUST store `canonical_name`, `registry_name` and a typed
  `aliases[]` where each alias carries `{value, source, valid_from, valid_to}`. (F5.6)
- **REQ-R5-09** — The EFF Atlas connector MUST key on `NEWAOSNUMBER[0:9]` as an ORI9 and
  MUST route `XX*` and `AOS*` prefixed values to the surrogate-minting path rather than
  the ORI path. (F5.11)
- **REQ-R5-10** — The system MUST record `wikidata_qid` where available but MUST NOT
  depend on Wikidata for coverage of U.S. law-enforcement agencies. (F5.12)
- **REQ-R5-11** — Vendor organizations MUST carry `gleif_lei` and `opencorporates_ocid`
  where GLEIF supplies them, ingested from the CC0 GLEIF golden-copy files. (F5.13)
- **REQ-R5-12** — The system MUST ingest SAM.gov UEIs, DUNS and `alternate_names[]` from
  `api.usaspending.gov` (keyless) for all organization classes, and MUST use
  `alternate_names[]` as alias input to the matcher. (F5.15)
- **REQ-R5-13** — The LEAIC crosswalk MUST be modelled as a **manual-acquisition**
  dependency with a documented human procedure recording DOI, version and SHA-256; the
  build MUST NOT assume it is automatically fetchable. (F5.9)
- **REQ-R5-14** — The system MUST publish a maintained, downloadable `ORI9 → Census GEOID`
  crosswalk as a public artifact, subject to REQ-R5-40. (F5.9)

**Jurisdiction and geography**

- **REQ-R5-15** — All GEOIDs MUST be stored as fixed-width strings with a
  `CHECK (length(geoid) = expected_for(level))` constraint, and every jurisdiction row
  MUST carry an explicit `level` because 7-character GEOIDs are ambiguous across place,
  unsd, elsd and sdadm. (F5.18)
- **REQ-R5-16** — The Gazetteer connector MUST pin the vintage year and MUST sniff the
  field delimiter (2024 = TAB, 2025 = PIPE) rather than hard-coding it. (F5.19)
- **REQ-R5-17** — Address-to-jurisdiction assignment MUST use the keyless Census Geocoder
  (`geocoding.geo.census.gov`), not the keyed Census data API, and SHOULD use the batch
  endpoint for bulk loads. (F5.20)
- **REQ-R5-18** — Jurisdiction geometry MUST come from TIGER/Line (`STATE, COUNTY, PLACE,
  COUSUB, UNSD, ELSD, SCSD, SDADM, AIANNH, CONCITY`), joined to Gazetteer identity by
  GEOID. Special-district boundaries (fire, water, transit, port, hospital) MUST be
  modelled as nullable — no national source exists. (F5.21)
- **REQ-R5-19** — Every jurisdiction MUST store `gnis_feature_id` sourced from the Census
  `ANSICODE`, and the GNIS `Civil`-class legal name MUST be available to the name
  normalizer. (F5.22)
- **REQ-R5-20** — `Jurisdiction.identifiers` MUST be a set of `(scheme, value)` pairs, not
  a single column; every jurisdiction MUST carry a GeoNames ID, and U.S. jurisdictions MUST
  additionally carry a Census GEOID. (F5.24)
- **REQ-R5-21** — Per-class identifiers MUST be assigned as specified in §F, with **CCN
  preferred over NPI** for hospital facility identity and NPI retained as secondary.
  (F5.23)

**Private organizations**

- **REQ-R5-22** — Organizations with no external canonical identifier MUST receive a
  SIG-minted surrogate with a stored, immutable `identity_basis` recording
  `{normalized_name, org_class, place_geoid, address_hash, first_seen_source_ref,
  first_seen_at}`. (§C.1, F5.25)
- **REQ-R5-23** — The system MUST implement the two-axis org taxonomy
  (`organization_class` × `operating_relationship`) of §C.2, and MUST model a municipality
  and its police department as **distinct organizations** joined by `parent_of`. (§C.2)
- **REQ-R5-24** — Address disambiguation MUST emit the tiered keys K1 (tigerLine+side),
  K2 (block GEOID), K3 (tract GEOID), K4 (place GEOID); K1/K2 may support matching, K3/K4
  are blocking-only. (§C.3)
- **REQ-R5-25** — An organization that fails all four publicity tests of §C.4 MUST NOT be
  published by name; it MUST be represented publicly by an aggregate count within its
  jurisdiction, with the full record retained privately. Network edges to suppressed nodes
  MUST remain publishable in aggregate. (§C.4)
- **REQ-R5-26** — Flock portal slugs MUST be parsed by the grammar in F5.26, with the `sd`
  suffix disambiguated by whether the expanded place slug ends in "county", and with
  Flock's internal orgs (`flock-pd`, `flock-safety-*`) excluded by denylist. (F5.26)

**Entity resolution**

- **REQ-R5-27** — The probabilistic matcher MUST be Splink 4 (MIT) on a DuckDB backend.
  Zingg MUST NOT be used unless the project accepts AGPL-3.0 obligations. Senzing MUST NOT
  be used. (F5.27, F5.29)
- **REQ-R5-28** — `normalize_org_name()` MUST be implemented exactly as specified in §D.2,
  MUST be a pure deterministic function, MUST be versioned, and MUST pass all twelve test
  vectors in §D.2 in CI.
- **REQ-R5-29** — The normalizer MUST collapse "Sheriff's Office" and "Sheriff's
  Department" to a single canonical suffix. (F5.6, §D.2 rule 4.1.1)
- **REQ-R5-30** — Acronyms (LAPD, NYPD, LASD, CHP…) MUST be resolved by exact lookup
  against an `acronym_alias` table and MUST NEVER be fuzzy-matched. (§D.2)
- **REQ-R5-31** — The matcher MUST implement the six-tier cascade of §D.3. Tiers 0–3 MAY
  auto-write; Tiers 4 and 5 MUST create PROPOSED claims and enqueue human review; Tier 6
  MUST NOT persist per-pair records. (§D.3, §20 Q28)
- **REQ-R5-32** — Tier 2 (`norm_full + state + class`) MUST generate its collision
  exclusion list from the data on every run rather than hard-coding it. (F5.7)
- **REQ-R5-33** — Tier 3a domain matching MUST apply a shared-hosting denylist and MUST
  require the domain to originate from a Tier-A/B source. (§D.3)
- **REQ-R5-34** — Every match MUST record `match_tier`, `match_evidence` and, for
  probabilistic matches, the Splink match weight and its per-comparison decomposition,
  surfaced in the UI as the confidence explanation. (F5.27, §9.3)
- **REQ-R5-35** — Blocking MUST use the OR-combined rule set B1–B8 of §D.4; every rule
  MUST be sized with `count_comparisons_from_blocking_rule()` and rejected above 5×10⁶
  pairs; blocking on suffix alone or state alone MUST be prohibited. (§D.4, F5.27)
- **REQ-R5-36** — An online candidate-search path MUST exist using a `pg_trgm` GIN index
  on `norm_full`; `pg_trgm` similarity MUST NOT be used as a decision score. (F5.30)
- **REQ-R5-37** — LLMs MAY generate review rationales for the human queue but MUST NOT
  write to the graph; model id and prompt version MUST be logged with each human decision.
  (F5.31)
- **REQ-R5-38** — A gold-standard label set MUST be constructed per §D.6 (stratified
  blocked-pair sampling across six match-weight bands, double adjudication with reported
  Cohen's κ ≥ 0.85, three-value label vocabulary, written adjudication rules, 30% frozen
  holdout), and MUST be versioned data with per-label provenance. (F5.28, §D.6)
- **REQ-R5-39** — Every ER run MUST report pairwise precision/recall/F1 at each tier
  boundary and B-cubed cluster precision/recall on the holdout; auto-write tiers MUST be
  demoted to review if holdout precision falls below 0.998. (§D.6)
- **REQ-R5-40** — Cluster-shape alerts MUST fire for `municipal_pd`/`sheriff` clusters of
  size > 5 and for clusters split by a single bridge into components each of size ≥ 2.
  (F5.27, §D.6)

**Temporal identity**

- **REQ-R5-41** — `Organization.status` MUST use the vocabulary
  `active | inactive | withdrawn | suppressed` with the semantics of §D.5. (F5.32)
- **REQ-R5-42** — Organizational change MUST be modelled as reified
  `OrganizationRelation` records with valid-time and transaction-time, using the
  seven-value vocabulary `same_as | succeeded_by | merged_into | split_into | absorbed |
  parent_of | acquired`. (F5.32)
- **REQ-R5-43** — A pure rename MUST produce a new `OrganizationVersion` and an alias with
  `valid_to`, and MUST NOT produce a succession relation or a new identifier. (§D.5 case 3)
- **REQ-R5-44** — The five worked cases of §D.5 MUST each exist as a fixture in the test
  suite.
- **REQ-R5-45** — Historical claims MUST remain attached to the predecessor organization
  after a merger and MUST NOT be reassigned to the successor. Time-scoped queries MUST
  traverse succession edges only when the query's time window requires it. (§D.5 case 1)

**Public identifiers**

- **REQ-R5-46** — SIG public identifiers MUST have the form `sig:<type>:<25 chars>`,
  constructed as UUIDv7 → low 120 bits → Crockford base-32 → leading `0` → ISO/IEC 7064
  check character, with a closed type-prefix vocabulary. (F5.33, F5.35, §E.1)
- **REQ-R5-47** — Identifiers MUST be opaque. Human-readable slugs MAY exist as 302
  aliases and MUST be documented as non-citable. (§E.1)
- **REQ-R5-48** — Identifiers MUST be dereferenceable at `https://id.<sigdomain>/<type>/<id>`
  from a dedicated subdomain with no file extensions, with content negotiation across
  HTML (303), JSON, JSON-LD and Turtle. (F5.34, §E.2)
- **REQ-R5-49** — Resolution MUST follow §E.2: 200 for active/inactive/suppressed, 301 to
  the successor for withdrawn plus a 200-able tombstone endpoint, 404 only for
  never-issued IDs. A published identifier MUST NEVER return 404. (§E.2, F5.32)
- **REQ-R5-50** — Invariants INV-1 … INV-8 of §E.4 MUST be enforced, including
  deterministic survivor selection on merge, ID retention by the survivor on split, and
  the rule that only human review may withdraw a published identifier. (§E.4)
- **REQ-R5-51** — Every merge, split, withdrawal and reinstatement MUST emit a durable,
  publicly readable event record in an append-only, UUIDv7-sortable change feed. (§E.4)
- **REQ-R5-52** — An ER run whose diff changes the resolution target of more than 0.5% of
  published identifiers MUST block release pending human sign-off. (§E.4)
- **REQ-R5-53** — The `identifier_link` table of §E.3 MUST exist with the specified
  columns and controlled `scheme` vocabulary, and MUST be published as a downloadable
  `sig-crosswalk` artifact (CSV + Parquet) on a stable URL with every release. (§E.3)
- **REQ-R5-54** — A reverse-resolution endpoint
  `https://id.<sig>/resolve?scheme=<scheme>&value=<value>` MUST 303 to the canonical
  entity URI. (§E.3)
- **REQ-R5-55** — Content-addressing MUST be used for EvidenceArtifact blobs and MUST NOT
  be used for entity identifiers. (§E.1)
