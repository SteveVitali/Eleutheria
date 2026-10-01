# K4 — Dossier index grouped by country (operator ask U-003.4)

Row **K4** of `META_PLAN.md` §6 Stream K (owner D, depends C3, I1). Written by Claude Code (Opus 5.5) in the planning
worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `e69f3fde` at writing).
Work window (`date -u`): **2026-09-30T21:30:46Z → see footer**. `PD` = `docs/build/planning/2026-09-30-next-phase`.
Companion row: **K5** (`PD/design/K5-dossier-sources.md`). Findings: `PD/findings/incoming/K4K5.csv` (shared with K5).

> **Design only (P3/P10).** Nothing here changes production. The live reads were 7 polite GETs to
> surveillancegraph.org, a bucket listing and one manifest GET. External reads were 12 HEAD/GET requests for public-domain
> boundary files from census.gov and naciscdn.org, sent with the neutral UA `SIG-planning-K4/1 (read-only)` and no operator
> identifier (P16). Nothing here is `engineered`, `staging-verified` or `live-executed` (P5). Public copy quoted below is
> **agent-drafted** and needs the operator's verbatim confirmation. All measurements below are **recorded-execution**
> (DuckDB 1.5.5 + `spatial`, run locally over the sha-verified release copies). Anything else is labelled `code`,
> `live-read` or `inference`.

**The operator's ask (U-003.4, verbatim excerpt):** *"the "/dossier" list should be grouped by country so that US states
are grouped together under US and clearly separate from country-specific dossiers"*. The row block adds: one canonical
jurisdiction key that fixes the ID/MN/DE/CA/TH collisions, `unresolved` shown as a data-quality bucket, counts and coverage
per group, and city/county dossiers (C5: there is no city lookup).

**Inputs read.** Reused, not redone:

- META_PLAN §3 and the Stream K block (K0, K4, K5, K6).
- `feedback/OPERATOR_FEEDBACK.md` U-003.
- `review/DATA_TRUTH.md` (whole).
- `research/I1-source-coverage.md` §Summary, §3, §5, §8.
- `research/F5-eng-debt.md` PKG-06/09/10, plus `data/eng_debt.csv` ED-29…32 and ED-36.
- `design/J3-transparency-design.md` §0–§6, §10–§12.
- `design/G3-release-model.md` §0, §4, §5, §8, §11.
- `design/G2-activation.md` §5.
- `research/C5-landscape.md` §2, §6.
- `findings/FINDINGS.csv` (titles) and `findings/incoming/*.csv` (titles), read to avoid re-raising.

**Code read.**

- `exports/src/exports/{shaping.py, spine_export.py, release.py, release_pages.py, published_record.py, audit.py}`
- `web/src/pages/dossier/**`, `web/src/lib/{data.ts, dossier.ts, publication.ts}`, `web/src/components/HowWeKnowThis.astro`
- `connectors/src/connectors/{dot_511.py, data/camera_registry_targets.toml, data/dot_511_targets.toml, data/sources.toml}`
- `db/src/db/{claim_sink.py, assertion.py}`
- `ontology/vocab/predicates.yaml`
- Spec §11.1 (SIG-ONTO-010/011), §14.2 (SIG-IDENT-001…006), SIG-UI-044 and SIG-UI-048.

---

## 0. Summary

**What exists today.** `/dossier/` is a flat alphabetical list of 55 bare codes titled "Surveillance infrastructure — XX".
The export builds one "jurisdiction" per distinct value of the `camera_jurisdiction` claim (`shaping.py:1041`,
`jurisdiction = str(jur_env.value)`). The slug is that value lower-cased (`spine_export.py:1466,1585-1590`).

The connectors do emit a scheme with each value (`dot_511.py:635-640`, `candidate={"scheme","value"}`). The sink **drops**
it: `db/assertion.py:assertion_from_record` never reads `candidate_identifier`. The spine therefore stores only `ID`, and
no export can tell Idaho from Indonesia (NEW-1).

- The 55 pages mix four schemes: 79 `us.state_abbr`, 40 `iso.3166_2`, 39 `iso.3166_1_alpha2` and 65 `sig.unresolved`
  registry targets.
- Two buckets are physically mixed:
  - `ID` = 232 Idaho + 268 Indonesia records.
  - `MN` = 994 Minnesota records + 1 Mongolian record.
- 18 of the 28 US-state slugs are also ISO 3166-1 country codes (`md` = Moldova, `ga` = Gabon, `pa` = Panama …).
- `unresolved` holds **166,210 of 232,625 records (71.4%)**.

**What the data can support.** Point-in-polygon over the release's 227,335 geolocated records:

- **91.5% of `unresolved` (152,058) lies in the United States.** Every US state and DC has ≥1 located record.
- Oklahoma, "the pilot with no dossier", has 1,705 located records, 391 of them in Oklahoma City.
- Records fall in 2,482 US counties and 9,382 Census places (1,474 counties and 2,817 places with ≥10 records).
- 69 countries (NE admin-0 polygons, which list PR and VI separately) and 535 non-US first-level subdivisions have ≥1
  located record.
- **1,640 of 46,801 US-state-declared located records (3.5%) sit outside the state they declare**, e.g. 919 "CA"
  records, 838 of them in Florida, and 248 "MO" records on the Kansas side of Kansas City.
- With a 0.02° coast tolerance, about 700 records (≈0.3%) stay unplaced. The data-quality bucket shrinks from 166,210 to
  about 700 (inference, §3.6).

**The design in one paragraph.**

1. **Key.** Every jurisdiction gets **one canonical key**. It is scheme-qualified and taken from a standard:
   `iso3166-1:US`, `iso3166-2:US-CA`, `us.census.geoid.county:06037`, `us.census.geoid.place:0644000`, plus national schemes
   later. The key comes with its full identifier set (SIG-IDENT-006) and an explicit level (SIG-IDENT-005). All keys live
   in a published **jurisdiction registry** built from **Census TIGER/Line 2025** (US containment), the **Census Gazetteer
   2025** (names/GNIS) and **Natural Earth 10m** (countries and first-level subdivisions elsewhere).
2. **Placement.** Each record is placed **at export time** by a versioned, recorded rule (`placement@1`). The located point
   wins, and a declared claim that disagrees with it is disclosed on both dossiers. Suspected axis swaps, sign flips and
   null-island points fall back to the declared jurisdiction and are flagged. Records with neither a location nor a
   declaration go to a **"Not yet placed" data-quality report** with counts by reason. That report is not a jurisdiction.
3. **Index.** `/dossier/` becomes **United States → states (+ territories)** and then **Other countries → subdivisions**.
   Every row carries the same seven facts: records, located share, sources, evidence types, open questions, disagreements
   and freshness. **County and city dossiers** hang under each state.
4. **URLs.** The country segment is the ISO 3166-1 **alpha-3** code (`/dossier/usa/ca/`, `/dossier/can/on/`,
   `/dossier/idn/`). No new URL can then silently reuse an old two-letter slug. Every old slug resolves forever: 301 to its
   successor, a *split* page (`/dossier/id/`, `/dossier/mn/`), or the quality report.

**Tickets (§9): 7 keys.**

| key | title | size |
|---|---|---|
| JUR-01 | Jurisdiction registry | M |
| JUR-02 | Scheme-preserving placement | L; split into 02a (sink fix + keys) and 02b (placement engine) |
| JUR-03 | Dossiers at every level + quality report | M |
| JUR-04 | Grouped index and directories | M |
| JUR-05 | Migration and redirects | S |
| JUR-06 | Acceptance + republish | S, live |
| JUR-07 | ZIP/address lookup | S, later |

JUR-01 and JUR-02a **are** F5's PKG-06a, spelled out here (merged-into, P9). JUR-02b consumes PKG-06b's detectors. The first
immutable promotion (G2 ACT-24) must come **after** JUR-02. Otherwise the P32.13 release tree freezes the bare-code
collisions into permanent URLs (NEW-6).

**Operator decisions (§10):**

- D-K4-1: boundary-source rights (HG-03).
- D-K4-2: disputed-territory point of view.
- D-K4-3: the page threshold for city dossiers.
- D-K4-4: US territories.
- D-K4-5: the placement precedence rule.
- D-K4-6: the URL scheme.
- D-K4-7: the conservative publication profile for non-US dossiers.
- D-K4-8: corrections-log wording.

---

## 1. Ground truth

### 1.1 Release, live pages and code

| # | fact | evidence |
|---|---|---|
| K4-G1 | The release under study is `sig-2026-09-27-ce480ab1`. The manifest sha256 was `717aeb44…72d6` at 21:32:40Z, unchanged since C3. The analysis used C3's sha-verified copies of `web/dossier_index.json`, `web/dossiers.json`, `sig_graph/jurisdictions.csv` and the 12 `*/sites.parquet` (`docs/build/logs/next-phase/C3/bucket/`, gitignored). | live-read (`gcloud storage ls`, `cp` of `manifest.json`) |
| K4-G2 | `/dossier/` returned 200 (21:33:56Z, sha256 `96e38ff8…`). It lists 55 rows titled "Surveillance infrastructure — XX" plus a bare code, sorted by `localeCompare` of the code. `unresolved` appears between `TX` and `US`. `/dossier/ok/` returned 404 (21:34:03Z). `/dossier/id/` shows "498 of 500 evaluable geolocated site observations in ID" and "Sources: camreg_achd_id, camreg_indonesia_id". | live-read; `web/src/pages/dossier/index.astro:16-19` (code) |
| K4-G3 | Bucket key = the bare claim value. `shaping.py:1041`; `group_jurisdictions` (`:1127-1182`) groups on that string. `spine_export._dossiers` (`:1429-1570`) mints `slug = _slugify(value)` and `subject_label = "Surveillance infrastructure — {value}"`. Gap `subject_id` = `jurisdiction:<slug>` (`:1419, :1510`). | code |
| K4-G4 | The declared scheme is emitted and then lost. The connector emits `candidate_identifier = {scheme, value}` (`dot_511.py:570-582, 635-640`). The four schemes come from target config: 223 targets = 79 `us.state_abbr`, 40 `iso.3166_2`, 39 `iso.3166_1_alpha2`, 65 `sig.unresolved`. Each of the 183 sources has exactly one `(scheme, value)` across its targets. `db/assertion.py:450-704` (`assertion_from_record`) reads no `candidate_identifier`, and no `db/` path mentions it. **The spine holds only the bare value (NEW-1).** | code (`tomllib` counts over both target files) |
| K4-G5 | Ontology: `camera_jurisdiction` = "Admin-1/country code … as attributed by the registry target", string, GLACIAL (`predicates.yaml:2057-2066`). The spec wants a first-class `Jurisdiction` with hierarchy, pluggable code systems, temporally versioned geometry (SIG-ONTO-010/011, spec §11.1), identifiers as `(scheme, value)` sets (SIG-IDENT-006), fixed-width GEOIDs with explicit level (SIG-IDENT-005), and **no point-in-polygon on agency centroids** (SIG-IDENT-004). The `jurisdiction` table exists (`db/deploy/domain_entities.sql:12`) and is empty (`shaping.py:5-9`). | code; spec |
| K4-G6 | The web contract has `Dossier.jurisdictionCode`, which "selects the §43.8 publication adapter". It defaults to `"US"` (`dossier.ts:244-248, 313`). None of the 55 export dossiers sets it (`dossiers.json` keys: `jurisdiction, gaps, legal_regime, termination, authorization, rulesetVersion, asOf, slug, sections, subject_label, source_families`). For an unknown code the rule is no-publish (`publication.ts:36-58`). **Every non-US dossier is therefore gated under US-DEFAULT (NEW-5).** | code; release file |
| K4-G7 | The P32.13 release tree keys its per-compartment record lists on the same bare value: `release.py:556-572` writes `…/c/<comp>/jurisdiction/<jur>/<page>/`, and `published_record.py:198-201` has basis `camera_jurisdiction`. The first promoted release would make `…/jurisdiction/ID/` and a 166,210-record `…/jurisdiction/unresolved/` list immutable (NEW-6). | code |
| K4-G8 | Registry substrate: <br>• `census_gazetteer_tiger` (`sources.toml:1363`): custody MIRROR, no `ingestion_permitted`, no `[rights]`; J4 lane UNDETERMINED. <br>• `census_geocoder` (`:1374`): REFERENCE, "address→jurisdiction". <br>• `fbi_cde_agency_registry` (`:1299`): permitted, CC0. Its lat/lon are agency centroids, **never** to be used for placement (SIG-IDENT-004). <br>• `wikidata_sparql` (`:1417`): permitted, CC0. <br>• There is no Natural Earth row. | code |
| K4-G9 | Every published site row has `n_sources = 1` (232,625 of 232,625). Site files carry no temporal column. Both matter to K5 (NEW-8, NEW-9). | recorded-execution |

### 1.2 Measurements (point-in-polygon, 2026-09-30T21:39–21:52Z)

**Method.** The 12 compartment parquets were unioned and reduced to one row per `entity_id` (232,625). The coordinates of
the 227,335 `point_status = resolved` rows were joined with `ST_Intersects` against:

- NE 10m admin-0 (258 polygons, keyed on `ISO_A2_EH`)
- NE 10m admin-1 (4,596)
- Census CB 2025 500k states (56), counties (3,235) and places (32,629)

**Runtimes** (laptop): admin-0 32 s (unindexed), admin-1 1.4 s, state 4.9 s, county 1.0 s, place 0.9 s. Runtime is not a
constraint.

| measure | value |
|---|---|
| records / geolocated / site-observation claims | 232,625 / 227,335 / 843,697 |
| geolocated inside an NE country polygon | 224,262 (98.65%) |
| … not in any country; of these (0,0) | 3,073 (15 at (0,0)) |
| inside a Census state/territory · county · place | 200,222 · 200,222 · 157,444 (78.6% of US-located) |
| US-located outside any place (unincorporated, not in a CDP) | 42,778 |
| records on a county or place boundary (double hits) | 1 county, 2 place → a tie-break rule is needed (§3.3) |
| `unresolved` by located country | US 152,058 · GB 3,377 · TW 1,825 · BE 1,378 · MY 747 · FR 579 · CA 567 · IT 486 · ES 485 · AU 438 · (none) 1,548 · no geometry 68 |
| `unresolved` records with no country polygon: distance to nearest | 827 within 0.02° (coast generalisation) · 89 within 0.2° · 564 more than 1° away (bad coordinates) |
| US-state-declared located records outside the declared state (the Indonesian source excluded) | **1,640 of 46,801**: another state 1,387, another country 60, no polygon 193 (≈2/3 of those within 2 km of the declared state's shoreline-clipped edge) |
| … largest | CA 919 in other states (FL 838, per C3/I1) · MO 248 (Kansas City, KS side) · WA 63 · OR 53 · IA 34 · KY 29 · DC 20 · MN 7 (WI) |
| ISO buckets, located vs declared | BD 447 → Singapore · NL 54 → Belgium · TH 182 outside Thailand · NZ 202 outside NZ (sign/axis errors) · GB-ENG 569 no polygon (Nottingham axis swap) · AU-QLD 257 no polygon · "US" 629 → AZ/TX/CA/NM/NV/OR + Mexico |
| US states + DC with ≥1 located record | **51 of 51** (+ PR 166, VI 66; GU, AS, MP 0) |
| … resting on a single source | 13 states: AR, CT, DE, ME, MI, MS, ND, NH, OK, RI, VT, WV, WY (+ PR, VI) |
| largest states after placement | CA 28,334 (11 sources) · TX 21,611 (7) · FL 18,903 (9; + 1,964 FL-declared ungeolocated) · GA 17,383 (3) · IL 9,417 (8) · OH 7,425 (2) |
| counties with ≥1 / ≥10 / ≥50 / ≥100 / ≥1,000 records | 2,482 / 1,474 / 634 / 383 / 28 (top: Harris TX 5,032, 3 sources; Los Angeles 4,153; Cook 3,970) |
| places with ≥1 / ≥10 / ≥50 / ≥100 / ≥1,000 | 9,382 / 2,817 / 609 / 237 / 9 (top: Houston 3,113; Chicago 2,246; Washington 1,665; New York 1,649; Austin 1,433) |
| max sources in one county / place | 8 (Prince George's MD) / 7 |
| pilot cities | Oklahoma City 391 (1 source) · Tulsa 331 (1) · Austin 1,433 (3) · Seattle 805 (3) · Oakland 1,099 (3) · San Diego 926 (4) · Kansas City MO 742 (3) · Charlotte 290 (1) |
| non-US admin-1 units with ≥1 / ≥10 records | 535 / 218 |
| (key, source) pairs: country/state · county · place | 350 · 3,567 · 12,193 |
| USPS codes that are also ISO 3166-1 alpha-2 (from NE `ISO_A2_EH`) | **26 of 51**: AL AZ AR CA CO DE GA ID IL IN KY LA ME MD MA MN MS MO MT NE NC PA SC SD TN VA. Of these, **18 are live dossier slugs**. |

**Natural Earth quirks that change results** (all measured):

- `ISO_A2 = -99` for France, Norway and Kosovo, among 22 features. `ISO_A2_EH` repairs all but 13 minor territories.
- Taiwan has `ISO_A2 = CN-TW` and `ISO_A2_EH = TW`. This is a point-of-view choice, so SIG needs its own policy (D-K4-2).
- NE admin-1 for GB is 232 local-authority units, not the ISO 3166-2 countries. The `geonunit` field gives England
  (152 units), Scotland (32), Wales (22) and Northern Ireland (26).
- 13 admin-1 units have no ISO code.

---

## 2. Design principles (binding on every JUR ticket)

- **K4-P1 One key, from a standard, with its scheme.** A jurisdiction is never keyed on a bare code. The key names its
  scheme, and the registry carries every other identifier as a `(scheme, value)` pair (SIG-IDENT-006).
- **K4-P2 Place by evidence, record the rule.** Placement is a derivation from two kinds of evidence: the record's point
  claims and the boundary captures. The ruleset is versioned. Each record carries its `placement_basis` and a check state.
  The boundary vintage and digest are inputs to the release descriptor. It is compute-on-read at export (ADR-092): nothing
  is written back to the spine, except the sink fix (JUR-02a), which only stops dropping data connectors already emit.
- **K4-P3 Disagreement is shown, never resolved silently.** If the declared jurisdiction and the located one disagree, both
  dossiers say so, with counts by source (§3.1 "contradictions stay visible").
- **K4-P4 Unplaced is a quality state, not a place.** It never counts toward "jurisdictions". It is reported with reasons,
  counts, sources and a way to help.
- **K4-P5 URLs are forever.** A published dossier URL never changes meaning. It resolves to its successor, a split page, or
  the quality report, and the slug history is append-only.
- **K4-P6 Names first, codes second.** Titles are names ("California, United States"). The code and scheme are secondary
  metadata ("US-CA · ISO 3166-2").
- **K4-P7 No-JS baseline for everything.** Every interactive element has a zero-JS form, and the enhanced form names its JS
  dependency (K0 re-decides the budget). Pages stay ≤150 KiB transferred at baseline.
- **K4-P8 The key drives policy.** The country key selects the §43.8 publication adapter. A country without an adapter
  gets the conservative profile (Part VIII §0.7: may only withhold).

---

## 3. The canonical jurisdiction key

### 3.1 Scheme

| level (`jurisdiction_type`, §11.1) | canonical key (`jkey`) | examples | other identifiers carried (SIG-IDENT-006) | source of truth |
|---|---|---|---|---|
| `country` | `iso3166-1:<A2>` | `iso3166-1:US`, `iso3166-1:ID`, `iso3166-1:DE`, `iso3166-1:TW` | `iso3166-1-a3:<A3>`, `iso3166-1-num:<NNN>`, `wikidata.qid` | ISO 3166-1 list (verified against NE `ISO_A2_EH`/`ADM0_A3`) |
| `state_province` (admin-1) | `iso3166-2:<A2>-<sub>` | `iso3166-2:US-CA`, `iso3166-2:US-DC`, `iso3166-2:CA-ON`, `iso3166-2:GB-ENG`, `iso3166-2:AU-ACT`, `iso3166-2:CO-MET`, `iso3166-2:TH-10` | `us.census.geoid.state:06`, `us.usps:CA`, `us.fips.state:06`, `ne.adm1_code`, `wikidata.qid` | ISO 3166-2; Census for US; NE `iso_3166_2` (GB via `geonunit`) |
| `county` (US, incl. parishes, boroughs, independent cities) | `us.census.geoid.county:<SSCCC>` (5-digit, fixed width) | `us.census.geoid.county:06037` | `us.gnis`/ANSI, `us.fips.county`, `wikidata.qid` | TIGER/Line 2025 county + Gazetteer 2025 |
| `municipality` (US incorporated place or CDP) | `us.census.geoid.place:<SSPPPPP>` (7-digit) | `us.census.geoid.place:0644000` | `us.gnis`/ANSI, `wikidata.qid`; Census LSAD (city, town, village, CDP) | TIGER/Line 2025 place + Gazetteer 2025 |
| non-US admin-2 / municipality (later round) | `<national scheme>:<code>` | `ca.statcan.csd:3520005`, `gb.ons.lad:E08000025`, `au.abs.lga:…`, `fr.insee.com:75056`, `de.ags:05315000` | per spec §11.1 list | national open datasets (§4.3) |

**Rules.**

- Codes are stored fixed-width, with an explicit level (SIG-IDENT-005). A 7-digit GEOID is never read without its level.
- US territories (PR, VI, GU, AS, MP) are keyed `iso3166-2:US-PR` … under `iso3166-1:US`, with the ISO 3166-1 codes
  (`PR` …) as aliases. The Census treats them as state equivalents. D-K4-4 confirms.
- Where ISO 3166-2 publishes two tiers, the first is used, e.g. GB countries rather than GB council areas, and BE regions
  rather than BE provinces. The registry records the tier chosen per country.
- Disputed territories follow D-K4-2. Recommendation: ISO 3166-1 codes as ISO publishes them (TW, PS, HK, EH); `XK` for
  Kosovo, labelled "user-assigned code"; neutral names; one standing note on the index. SIG never takes NE's default
  point of view silently (§1.2, Natural Earth quirks).
- **Display slug** (derived, one per key):
  - country = lower-case alpha-3
  - admin-1 = lower-case ISO 3166-2 suffix
  - county/place = `<Census NAMELSAD slug>-<GEOID>`, e.g. `los-angeles-county-06037`, `los-angeles-city-0644000`

  Resulting paths:

  | level | path |
  |---|---|
  | country | `/dossier/usa/`, `/dossier/idn/`, `/dossier/twn/` |
  | admin-1 | `/dossier/usa/ca/`, `/dossier/can/on/`, `/dossier/gbr/eng/`, `/dossier/tha/10/` |
  | county | `/dossier/usa/ca/los-angeles-county-06037/` |
  | place | `/dossier/usa/ca/los-angeles-city-0644000/` |

  The GEOID is authoritative. The name part is cosmetic, and a renamed place keeps working through the slug history (§8).
- **Why alpha-3 in the path** (D-K4-6). Every live flat slug is 2 letters, `xx-yyy`, or `unresolved`. Alpha-3 country
  segments therefore cannot collide with any URL already printed or cited. A `/dossier/<alpha-2>/` country page would
  silently turn 18 cited state dossiers (`/dossier/md/` …) into foreign countries. Alternative considered: name slugs
  (`/dossier/united-states/georgia/`). They are friendlier, but names change (Swaziland → Eswatini) and translate, so
  they are kept as titles only.

### 3.2 Deriving the key from claims and coordinates

The **declared** jurisdiction comes from the `camera_jurisdiction` claim. Its scheme is mapped to the key family as
follows:

| scheme | key |
|---|---|
| `us.state_abbr:XX` | `iso3166-2:US-XX` |
| `iso.3166_1_alpha2:XX` | `iso3166-1:XX` |
| `iso.3166_2:XX-YY` | `iso3166-2:XX-YY` |
| `sig.unresolved` | none |

- **New claims** carry the scheme into the spine (JUR-02a sink fix). It is stored in `value_json {scheme, value}` so the
  text value and the digest stay unchanged. The alternative, a `qualifiers` entry, is decided at T1.
- **Legacy claims** get the scheme from the source's target config: 1:1 per source today (K4-G4). The config file's
  sha256 is recorded, and the basis is labelled `declared_scheme_from_config`.

The **located** jurisdiction comes from the resolved point (the shaping envelope; conflicted points are not used) by
point-in-polygon against the registry's boundaries:

- country: NE admin-0
- admin-1: NE admin-1, or Census for the US
- US county and place: TIGER/Line

Exclusions and data paths:

- Points whose `geometry_precision` is `organization_centroid_or_unknown`, or whose source is an agency registry, are
  **never** placed by location (SIG-IDENT-004).
- **Non-site claims** are placed by **name → key lookup** against the registry gazetteer (§5.4): Atlas rows, Eyes on
  Flock portals, OpenStates bills, CCOPS, agendas, procurement buyers. That attribution work is owned by **I8**
  (I1 blind spot #3), which uses K4's lookup contract.

### 3.3 Placement ruleset `placement@1` (versioned; D-K4-5 ratifies)

Evaluated per record in order. The first rule that matches wins.

| # | condition | placed at | `placement_basis` | `placement_check` |
|---|---|---|---|---|
| R1 | the point is (0,0) or out of range | — (point rejected; continue at R5) | — | `null_island` / `invalid_point` |
| R2 | point inside a registry boundary (TIGER for US; NE + 0.02° tolerance elsewhere) **and** consistent with the declared value (declared absent, or equal, or an ancestor) | the full located chain: country → admin-1 → county → place | `point_in_polygon` | `consistent` |
| R3 | declared present; the point lies outside it; the swapped `(lat,lon)` or sign-flipped variant lies **inside** the declared boundary | declared level only; the point is withheld from maps and county/place counts | `declared` | `axis_swap_suspected` / `sign_flip_suspected` |
| R4 | declared present; the point is inside another unit and R3 does not apply | located chain | `point_in_polygon` | `outside_declared` (same country) / `outside_declared_country` |
| R5 | no usable point (none, rejected, or envelope `conflicted`) and declared with a known scheme | declared level only | `declared` | `no_point` / `coordinates_conflicted` / `point_rejected:<R1 reason>` |
| R6 | point in no boundary beyond tolerance, and nothing declared | unplaced | — | `outside_all_boundaries` |
| R7 | no point and nothing declared (`sig.unresolved`, missing, or a legacy value with no scheme) | unplaced | — | `no_location_evidence` |
| R8 | a non-site claim whose name did not match (I8) | unplaced | — | `name_unmatched` / `name_ambiguous` |

**Tie-breaks.** A point on a shared boundary goes to the lowest GEOID or code and gets check `on_boundary`. There was 1
such county hit and 2 place hits in this release.

**Partial depth.** A point in a country whose admin-1 boundaries are not loaded is placed at country level. Its sub-levels
are `not_evaluated`, which is not the same as unplaced.

**Why "located wins" (R4).** Every observed cross-country disagreement is a wrong *label*, not a wrong point: BD →
Singapore, NL → Belgium, the GA source in Mongolia, and the CA source in Florida (I1 NEW-2, inference). Borders between
states are real operational facts, e.g. MoDOT cameras on the Kansas side. R3 catches the wrong-*point* cases: the
Nottingham swap and the GA/NZ sign flips. Anything R4 moves across a country border is also listed for review (a JUR-03
quality task), and upstream corrections go through PKG-06b as new claims.

### 3.4 Declared and located both stay visible

Each dossier carries two numbers per source:

- **"declared here, located elsewhere: n"**, with the destinations linked
- **"located here, declared elsewhere: n"**

The record-level `jurisdiction` block in the release extends `published_record.py:198-201` to:

```
{ id, jkey, chain[], basis, check, declared:{scheme,value}|null, boundary_vintage }
```

### 3.5 Temporal versioning (SIG-ONTO-011)

- Round 11 uses one vintage per release (TIGER 2025 = boundaries as of 2025-01-01; NE v5.1). The vintage is shown on
  every dossier ("boundaries: US Census TIGER/Line 2025").
- An annexation after the vintage is a known limit, disclosed in a note.
- Per-observation-date boundaries come with the first-class `Jurisdiction` entities (§11.1). **Revisit trigger:** when
  `jurisdiction` rows are written to the spine, or when two boundary vintages are live at once.

### 3.6 Expected effect on today's numbers (inference from §1.2)

| bucket today | after `placement@1` |
|---|---|
| `unresolved` 166,210 (71.4%) | ≈ 700 unplaced (≈0.3%). The rest are located: 152k in the US, the others in 60+ countries. |
| 32 US state/DC dossiers | 51 state + DC dossiers + PR and VI. 13 states rest on one source, and the index says so. |
| `ID` 500 mixed | Idaho 232 (+ OSM points located in ID → 691) and Indonesia (Indonesian source + OSM → 381 located) |
| `MN` 995 mixed | Minnesota 2,465 located; the 1 Mongolian record, which has no geometry, is placed at country level `iso3166-1:MN` |
| `CA` 6,139 | California 28,334 located. 838 → Florida and 81 → other states, shown on both dossiers. |
| `BD` 447, `NL` 54 | Singapore 432 / Belgium (merged into Belgium's 1,451). The old slugs become split/correction pages. |

---

## 4. Boundary data

### 4.1 Choice

| role | dataset | licence (as published; **rights = HG-03**) | measured size (21:37–21:43Z) | why |
|---|---|---|---|---|
| US containment | **Census TIGER/Line 2025** — `tl_2025_us_state`, `tl_2025_us_county`, `tl_2025_<ss>_place` ×56 | US Government work, no copyright (17 U.S.C. §105); registry row `census_gazetteer_tiger` exists but is gated | state 9.96 MB; county 84.0 MB; place CA 9.9 MB (total over 56 files not measured; inference ≈150–250 MB) | full resolution, **not clipped to shoreline** (water areas included), so coastal, pier and bridge cameras place correctly. The clipped 500k files left 193 US-declared points in no polygon, ≈2/3 within 2 km. |
| US display + fast fallback | Census Cartographic Boundary 2025 500k — state / county / place / cousub | same | 3.2 / 11.8 / 23.1 / 40.4 MB | generalised geometry for K1/K6 maps and dossier locator thumbnails |
| US names, codes, internal points | Census Gazetteer 2025 — places / counties (national) | same | 1.21 MB / 0.14 MB | GEOID, ANSI/GNIS ids, official names, internal point, land/water area. Feeds names, search (K3) and centroids. |
| Non-US country + admin-1 | **Natural Earth 10m** admin-0 countries + admin-1 states/provinces (v5.1, Last-Modified 2022-05-13) | public domain per Natural Earth's terms (terms text not captured by this row; capture at onboarding, P15) | 4.93 MB / 14.91 MB | global, coded (`ISO_A2_EH`, `iso_3166_2`), stable. Quirks handled in code: -99 codes, the Taiwan POV, GB via `geonunit` (§1.2). |
| Optional name enrichment (non-US cities → admin-1) | NE 10m populated places (public domain) or GeoNames cities (CC BY 4.0, attribution) | as stated; unverified | not measured | "Canberra" → AU-ACT for search (C2 NEW-10; K3) |

**Rejected.**

- **GADM**: licence forbids commercial use and redistribution. Incompatible with open compartments.
- **OSM administrative boundaries**: ODbL share-alike. Deriving placement for non-ODbL compartments from ODbL boundaries
  raises the §42.3 derivative-database question.
- **geoBoundaries**: CC BY 4.0 for gbOpen, with per-country licence variation. Viable later for non-US admin-2, not
  needed for admin-1.
- **Census geocoder API at build time**: one request per point, a network dependency in the export, and it is US-only.

### 4.2 Evidence handling

The boundary files are **evidence**:

- Onboarded as registry sources: `census_tiger_2025`, re-using or renaming `census_gazetteer_tiger`, and a new
  `natural_earth_10m`. Both stay `ingestion_permitted=false` until the operator's HG-03 decision (D-K4-1).
- Captured into OCFL, with bytes and digests.
- Converted once per vintage into a GeoParquet **boundary pack**, stored in the restricted export inputs.
- Hashed into descriptor v2 as `boundaries_root`. This joins REL-01's ADR (G3 §3.2): one more intentional input, the same
  ADR.

The derived **jurisdiction registry** (keys, names, identifiers, level, parents, bbox, internal point, vintage) is a SIG
metadata file (CC-BY-4.0) that attributes its upstreams. Polygons are published only as simplified display tiles (K1/K6),
under the upstream terms.

### 4.3 Later (non-US sub-national, not Round 11 unless D-K4-3 widens scope)

Named only, not verified by this row:

- Statistics Canada (OGL-Canada 2.0): Canada 3,469 located
- ONS Open Geography (OGL-UK-3.0): UK 5,138
- ABS ASGS (CC BY 4.0): Australia 3,026
- IGN/INSEE (Etalab 2.0)
- BKG VG250 (dl-de/by-2-0)

Each needs its own rights row and HG-03.

### 4.4 Runtime

The placement engine is a new `exports/placement.py`. It runs DuckDB `spatial`, bundled into the export image at a pinned
version (no runtime `INSTALL`; the planning run downloaded it into a scratch directory). `duckdb>=1.0.0` is already an
`exports` dependency (`exports/pyproject.toml:41`). The alternative is PostGIS in the spine once `jurisdiction` rows exist.

Cost estimates, all inference:

- Export-time placement: under 2 minutes for about 230k points (measured joins took 40 s in total on a laptop, most of
  it unindexed admin-0).
- Boundary pack: about 300 MB of restricted inputs per vintage.
- Registry file: about 4 MB, 13k entries.

---

## 5. What the index and each dossier show

### 5.1 Index structure (`/dossier/`)

```
Dossiers                                                       [release label · as of · cite]
  How to read this index · what "records" means · "not listed ≠ nothing there" (SIG-UI-048)
  [ Find a place: ______ (Go) ]   A–Z of all places · Browse on the map · Research dossiers (reviewed) →

  ▸ United States — 200,222 records · 100 sources · 51 states + DC · 2,482 counties · 9,382 places   → /dossier/usa/
      table: State | Records (located %) | Sources | Evidence types | Open questions | Disagreements | Newest run | Counties · Places
      50 states + DC (A–Z; alt sort routes) · Territories: PR, VI (records) · GU, AS, MP ("no published records yet")
  ▸ Other countries — 66 countries with records                                               (A–Z by English name)
      Australia  3,026 · 8 sources         → ACT 1,288 · Queensland 1,227 · New South Wales 378 · Victoria 104 · …
      Belgium    1,451 · 3 sources
      Canada     3,469 · 20 sources         → Ontario 1,534 · Manitoba 795 · British Columbia 785 · Alberta 354 · …
      Thailand   2,075 · 2 sources          → "22 provinces →"  (≤12 subdivisions inline; otherwise a link)
      …
  ▸ Not yet placed — ≈700 records (data quality; not a jurisdiction)                            → /dossier/unplaced/
      by reason: outside all boundaries 564 · no location evidence 68 · …
  How we know this (index scope) · Methodology · Dispute
```

- **Grouping.** The US comes first, per the operator's ask and the design centre. Then come other countries A–Z. Each
  country row nests its first-level subdivisions.
- **Order.** Alphabetical by name is the baseline. Pre-rendered GET sort routes
  (`/dossier/sort/{records|sources|freshness|disagreements}/`) follow the `/data-freshness/[...sort]` pattern.
- **Budget.** About 150 rows × ≈600 B ≈ 90 KB HTML, which is ≤150 KiB. If the budget fails, subdivisions collapse into
  `<details>` elements (zero JS).
- **Machine twin.** `/dossier/index.json` (`sig.dossier-index/2`): hierarchical, one object per key with the row fields
  below plus `children[]`.

### 5.2 Row fields (index rows and each dossier's header strip)

| field | definition (shown as a footnote; named definitions, J3 §4.1 style) | source artifact |
|---|---|---|
| Place | name + ", " + parent name; secondary: code, scheme, level (e.g. "US-CA · ISO 3166-2 · state") | registry |
| Records | "published observation-level records placed here" (never "devices"; SIG-RECON-058), denominated: `28,334 records` | `dossier_index.json` |
| Located | "`n` of `N` placed by their own coordinates"; the rest are placed by declared jurisdiction | placement counts |
| Sources | "sources with published claims placed here" + the top 3 names (linked, never bare ids) | K5 artifact |
| Evidence types | present/absent per class: camera registries · legislation · procurement · policy · agendas · CCOPS/accountability. Absent = "—" with absence kind. Today only registries reach dossiers; the others arrive with I8. | K5 artifact |
| Technology | ALPR / CCTV / traffic … once PKG-07 types records; until then `not typed yet` (never "traffic camera" for all) | PKG-07 |
| Open questions | count of fields rendered "unknown", with absence kinds (DR-C3-06) | dossier gaps |
| Disagreements | coordinate conflicts (same source) · declared elsewhere / located here · cross-source contradictions | placement + K5 |
| Freshness | newest and oldest last successful run among its sources (J3 freshness function); release as-of | J3 `runs.jsonl` / freshness |
| Children | "58 counties · 1,012 places with records" | registry + placement |
| Links | dossier · print · JSON · map (bbox) · downloads (K5, after gates) | — |

### 5.3 Dossier levels and pages (city/county dossiers)

| level | pages | contents beyond the §39.2 sections | today's data |
|---|---|---|---|
| country | 67 (US + 66 others; PR/VI placed under US, D-K4-4) | subdivisions table; records placed only at country level; "declared elsewhere" | all located records; country-declared sources |
| admin-1 | 51 US + DC + PR, VI; non-US: all with ≥10 records (218) or inline only (D-K4-3) | counties table, places A–Z (paged ≤200 rows), placement disagreements | registry + OSM/DeFlock points; FL/IL conflicted records at state level |
| US county | **2,482** (≥1 record); or 1,474 at ≥10 | places within, unincorporated count, sources | points only (agency/county claims arrive with I8) |
| US place | **2,817** (≥10 records) + every place with non-site evidence (agenda tenants: 42; CCOPS; city-scoped sources: 7; research-dossier cities) | parents (county/ies, state) | points; city documents once I8 attributes them |

- **Places with 1–9 records** (6,565) get no page. They are listed with counts in their county's and state's place
  tables and deep-link to the map. D-K4-3 can lower the threshold.
- **Printing.** The dossier page itself prints via `@media print`, so county and place levels need no `/print/` route.
  `/print/` is kept for country and admin-1 levels, where live print URLs exist.

**Build size** (inference): about 5.6k dossiers × (HTML + JSON + the K5 explorer page) ≈ 17k files. At J3's rate of
"+≤5 min per ≈3k pages", the Astro build grows by 10–30 min (G3 §5.2 build stage). JUR-03 measures it (P32.13
`measure_build` pattern).

**Generation.**

1. `group_jurisdictions` becomes `group_by_key(sites, registry)`.
2. It rolls each record up its whole chain, so a parent total = the sum of its children + the records placed only at the
   parent level.
3. `_dossiers` takes `(jkey, level, name, chain)`.
4. It sets `jurisdictionCode` = the country A2 (K4-P8).
5. It sets the gap `subject_id = jurisdiction:<jkey>`.
6. `dossiers.json` is split into one file per dossier (`web/dossiers/<slug-path>.json`). Today's monolith is 129 KB for
   55; at 5.6k dossiers it would be about 13–25 MB.

### 5.4 Gazetteer lookup contract (for I8, K3, JUR-07)

`jurisdiction.lookup(name, *, level=None, within=None) -> [candidate{jkey, name, level, score, basis}]`

- Exact official name, then alternate names (Gazetteer, NE `name_*`, ISO names), within a parent context.
- A match that is ambiguous without a parent (e.g. "Springfield") returns more than one candidate, and I8 records
  `name_ambiguous` rather than guessing.
- The rules are versioned (`lookup@1`) and applied at export, the same posture as placement.

### 5.5 "Not yet placed" (`/dossier/unplaced/`)

- **Header** (agent-drafted): "These records are published, but SIG cannot yet say which jurisdiction they belong to.
  This is a data-quality list, not a place."
- **Table by reason** (R1/R6/R7/R8 vocabulary): records, sources (linked), share, what would fix it, and a link to the
  research-queue tasks (K11) or the known issue (J3 TX-06).
- **Per source**: top reasons.
- **Downloads**: the unplaced slice, per compartment (K5, after gates).
- **Link** to `/corrections/` for re-keyed pages.
- The page is excluded from jurisdiction counts, from "55 jurisdictions"-style copy (C3 NEW-14), and from the search
  facet "place".

---

## 6. Navigation

Every element below lists its no-JS baseline, its enhanced version, and the JS it needs. K0 decides whether the enhanced
column ships.

| element | no-JS baseline | enhanced | JS dependency |
|---|---|---|---|
| Browse hierarchy | nested lists/tables; `<details>` for long subdivision lists; breadcrumbs `Dossiers › United States › California › Los Angeles County` on every dossier | — | none |
| A–Z directory | `/dossier/a-z/<letter>/`: every key with ≥1 record, name + parent + level + records; paged ≤200 | — | none |
| Sort / filter the index | pre-rendered GET sort routes; single-dimension facet routes `/dossier/by/{evidence-type|single-source|level}/<value>/` | live text filter + multi-column sort over `index.json` | small island, ≈≤10 KB JS + ≈60 KB gz data; K0 budget |
| Search box | `<form method="get" action="/search/">` with `kind=place` (K3's no-JS target: the release-pinned FTS5 form, P32.14) | type-ahead over a lazy-loaded place index (13k names + alternates ≈ 0.8 MB raw / ≈0.2 MB gz, fetched on focus) | island; K3 + K0 |
| Map entry | each row links `/map/?bbox=<w,s,e,n>` (K1 defines the parameter) and a static SVG locator thumbnail per dossier (K6) | the map opens framed on the jurisdiction with its boundary drawn | K1 map island (MapLibre); K6 embed |
| "Places near me" / ZIP (JUR-07, later) | GET form to an API redirect route `/v1/place?zip=…` → 302 to the place/county dossier (ZCTA↔place/county relationship files, Census, public domain); `census_geocoder` for addresses (REFERENCE) | browser geolocation → nearest place | server route (no client JS for the baseline); geolocation needs JS + consent; Part VIII: no logging of queried addresses (the §44.5 posture) |

Reachability AC: every dossier ≤3 clicks from `/dossier/` without JS (country → state → county/place, or A–Z).

---

## 7. Where the key flows (one key everywhere)

| surface | change | owner |
|---|---|---|
| shaping / sites files | add `jurisdiction_key`, `jurisdiction_chain`, `placement_basis`, `placement_check`, `declared_scheme`, `declared_value`, `boundary_vintage` columns; keep `jurisdiction` for back-compat, labelled "declared (legacy)" in the data dictionary | JUR-02b; TX-10a (dictionary) |
| release tree `/r/<pub>/c/<comp>/jurisdiction/<slug-path>/` | keyed by display slug path; `unplaced/` instead of `unresolved/`; land before ACT-24 (NEW-6) | JUR-03 |
| dossier JSON twin + API `/v1/dossier/{scope}` | scope accepts `jkey`, slug path, or legacy slug (via history → 301/300); unknown → 404; release-backed (G3 REL-05) | PKG-09a / REL-05 consume the registry + history |
| J3 source pages | geography facets and "Contribution to dossiers" use keys and names | TX-05 (consumes) |
| research queue | gap/task `subject_id` `jurisdiction:<slug>` → `jurisdiction:<jkey>`; legacy task ids mapped | JUR-03; K11 |
| search (K3) | registry names + alternates indexed; `kind=place` facet | K3 |
| map (K1) / embeds (K6) | bbox, internal point, display boundaries | K1, K6 |
| publication policy | `jurisdictionCode` from the country key; conservative profile for countries without an adapter | JUR-03 (+ E2 for adapters) |
| G3 verification V9 | "jurisdiction–coordinate sanity" becomes: 0 records placed by point with `null_island`/`*_suspected`; per-key counts recompute from the sites files + registry + boundary pack | REL-04b consumes JUR-02 checks |
| rights | records placed in the US that were published under the non-US database-right basis → an E-stream re-review list (NEW-4) | JUR-03 emits the list; E4 decides |

---

## 8. Migration from today's 55 pages

### 8.1 Slug map (applies to `/dossier/<old>/`, `/dossier/<old>/print/`, `/dossier/<old>.json`)

| old slugs | count | new target | HTTP (after REL-03b) | static fallback (before REL-09) |
|---|---|---|---|---|
| US states that keep one referent: `al az ca co dc fl ga hi ia il ks ky la ma md mo nc ny or pa sd tn tx ut va wa` | 26 | `/dossier/usa/<st>/` | 301 | redirect stub |
| `id`, `mn` (merged places) | 2 | **split page**: "Until release `<label>` this page combined Idaho (US) and Indonesia. They are now separate:" + two links + a corrections link | 300 where the host supports a body, else 200 `noindex` | static split page |
| ISO 3166-2: `au-act au-qld au-vic ca-ab ca-bc ca-mb ca-on co-met gb-eng gb-nir gb-sct ie-dl` | 12 | `/dossier/<a3>/<sub>/` | 301 | stub |
| ISO 3166-1 with a stable referent: `be de gb hk jp my nz ps pt sa th` | 11 | `/dossier/<a3>/` | 301 | stub |
| ISO 3166-1 whose records were mislabelled: `bd` (→ Singapore), `nl` (→ Belgium) | 2 | **correction page** naming where the records are now + a link to the would-be country page if one exists | 200 `noindex` | static page |
| `us` | 1 | `/dossier/usa/` (scope note: "this page used to show only country-level registry records") | 301 | stub |
| `unresolved` | 1 | `/dossier/unplaced/` (note: "most records formerly here are now placed by location") | 301 | stub |

**Partial moves** (CA → FL 838; TH → HK; GA sign flips) are not redirects. The successor page carries a dated correction
note ("N records previously shown under California are located in Florida"), linked to `/corrections/`.

### 8.2 Mechanism

1. **Slug history.** The exporter emits `web/jurisdiction_slug_history.json`: an append-only list of
   `{slug, first_release, last_release, successor: jkey | [jkeys] | "unplaced", kind: moved|split|corrected}`. It is seeded
   with the 55 rows above and carried forward from every promoted release's registry (G3 `registry/`), so any slug ever
   published resolves.
2. **Phase 1, static (works on today's bucket-root serving).** The Astro build emits, for each historical slug:
   - a zero-JS redirect stub (`<meta http-equiv="refresh" content="0; url=…">`, `<link rel="canonical">`, a visible link,
     and the release stamp), or
   - the split or correction page.

   A 0-second meta refresh is not a WCAG timing failure (F41 targets delayed refresh).
3. **Phase 2, edge.** REL-03b's generation writer gains `redirects.conf` (`location = /dossier/md/ { return 301 …; }`),
   generated from the slug history per config generation. It sits beside `withdrawn.conf`, `selectors.conf` and
   `labels.conf`. The stubs stay as fallback.
4. **Legacy citations.** The 55 pages and their PDFs print "Belief-pinned permalink … `?as_of_world=2026-09-27&…`".
   G3's legacy floor (§8.2) is only a rollback tree, and an unmatched selector returns 404. **This must change (NEW-7).**
   REL-09 imports the 09-27 site as an addressable, immutable snapshot (e.g. `/s/legacy-20260927/…`, J3 TX-13b's `/s/`
   pattern). `selectors.conf` then maps `?as_of_world=2026-09-27` on an old dossier path to that snapshot, which shows the
   original content with a banner: "This is the page as published on 2026-09-27; it contained errors since corrected:
   <link>" (agent-drafted).
5. **Corrections log.** One public entry per class: merged places (ID, MN; F-44), mislabelled records (BD, NL, CA → FL,
   TH → HK), and the re-placement of `unresolved`. D-K4-8 approves the verbatim text.
6. **Sitemap and search.** Only canonical URLs go in `/sitemap.xml`. The release's FTS5 index is rebuilt per release
   (P32.14). Old slugs are indexed as aliases and resolve to the new dossier.
7. **Verification.** A new check extends G3 V5 (link crawl): every slug in the union of all promoted releases' dossier
   indexes, and every legacy print and JSON alias, resolves (200 / 301 / 300) in the latest view. No old slug ever
   returns 404 or serves a different place.

### 8.3 Sequencing

```
PKG-01/02 ─► JUR-01 ─► JUR-02a (sink fix; hosted: new claims only) ─► JUR-02b ─► JUR-03 ─► JUR-04 ─► JUR-05 ─► JUR-06
                ▲ D-K4-1 (HG-03)            ▲ PKG-06b detectors (optional)   ▲ K5 DSRC-01  ▲ K0/K1/K3   ▲ REL-03b/09
                                                                              must precede G2 ACT-24 (NEW-6)
```

---

## 9. Round-11 ticket outline

Sizes follow J3 §12: **S** ≈ half a fresh-context run, **M** one run, **L** split a/b. "Live" means a production stage that
needs an operator go.

| key | title | size | scope (one line) | depends (F5 PKG / G3 REL / G2 ACT / J3 TX / K) | live / gate |
|---|---|---|---|---|---|
| **JUR-01** | Jurisdiction registry + boundary pack | M | registry rows for the boundary sources; OCFL capture; GeoParquet boundary pack; `jurisdictions` registry (keys, identifiers, levels, parents, bbox, internal point, names + alternates); Gazetteer lookup `lookup@1`; `boundaries_root` into descriptor v2 | **= PKG-06a (part 1)**; D-K4-1 (HG-03), D-K4-2, D-K4-4; REL-01 (descriptor v2 ADR carries the new input) | hosted capture after HG-03 — op go |
| **JUR-02a** | Keep the declared scheme | S | `assertion_from_record` persists `candidate_identifier` (as `value_json`); shaping reads it; legacy claims get `declared_scheme_from_config@<sha>`; regression: no bucket mixes schemes | **= PKG-06a (part 2)**; PKG-01 (sqitch CI, if a column is needed); hosted effect via the next ingest | none (code); visible after republish |
| **JUR-02b** | Placement engine `placement@1` | M | `exports/placement.py` (DuckDB spatial, pinned); rules R1–R8; tie-break; per-record placement columns + record `jurisdiction` block; quality reasons; fixtures: Nottingham swap, CA→FL, ID/Indonesia, MN/Mongolia, GA/NZ sign flips, (0,0), MO/KS border, coast tolerance | JUR-01, JUR-02a; consumes PKG-06b detectors if landed (else flags only); coordinates PKG-06b corrections | — |
| **JUR-03** | Dossiers at every level + quality report | M | `group_by_key` roll-ups; country/admin-1/county/place dossiers; split per-dossier JSON; `jurisdictionCode` + conservative profile; gap `subject_id` re-key; `index.json` v2; `unplaced` report; release-tree jurisdiction lists by key (before ACT-24); US-located DBRight list for E4; build-time measurement | JUR-02b; K5 DSRC-01 (sources/figures per dossier, same run); PKG-10 (per-dossier provenance → merged into DSRC-01); PKG-09a/REL-05 read the registry | republish rides the next release |
| **JUR-04** | Grouped index + directories + navigation | M | `/dossier/` grouped (US → states; other countries → subdivisions; unplaced block); sort/facet GET routes; A–Z; breadcrumbs; state county/place tables; search form; map links; row definitions; budgets | JUR-03; K3 (search target), K1 (bbox param), K6 (locator); TX-13a (cite), REL-02 (stamp); **enhanced** filter/type-ahead only after K0 | via release |
| **JUR-05** | Migration: slug history, stubs, split/correction pages, redirects | S | history file; static stubs; the ID/MN split pages and BD/NL correction pages; corrections entries (D-K4-8); `redirects.conf` generator hook; the V5 "every historical slug resolves" check | JUR-04; REL-03b (edge 301s); **REL-09 must make the 09-27 site an addressable snapshot** (NEW-7); TX-13b selectors | Class S release |
| **JUR-06** | Acceptance + republish | S | crawl (§11 ATs), budgets, number-truth recompute of per-key counts from the bulk files + registry + boundary pack (extends DR-C3-15), agent journey walkthroughs (**not user research**, P4) | all above; G3 cut → promote (Class S, HG-11 semantics if with ACT-24) | **live** — op go |
| JUR-07 | ZIP / address → dossier (later wave) | S | API redirect route; ZCTA relationship files; no query logging | JUR-03; REL-05; E2 (privacy note) | API roll — op go |

**Exactly-one ownership (P9).**

- PKG-06a := JUR-01 + JUR-02a.
- PKG-06b keeps connector-side axis-order/null-island detectors, target corrections as new claims, the IDOT/FL511
  conflict investigation, and one row per entity in the portal files.
- The placement-time checks are JUR-02b's.
- The per-dossier "How we know this" part of PKG-10 moves to K5 DSRC-01.
- Non-site attribution belongs to I8.
- The API scope resolution belongs to PKG-09a/REL-05.
- Edge redirects belong to REL-03b (generator hook from JUR-05).

---

## 10. Operator decisions needed

| id | question | recommendation | feeds |
|---|---|---|---|
| **D-K4-1** (HG-03) | Rights for the boundary sources: flip `census_gazetteer_tiger` (public domain, 17 U.S.C. §105) and add `natural_earth_10m` (public domain) to `ingestion_permitted=true` | Yes, both, after the terms text is captured (P15) | JUR-01 |
| D-K4-2 | Disputed-territory point of view (TW, PS, HK, XK, EH, Crimea) | ISO 3166-1 as published; `XK` labelled user-assigned; neutral names; one standing note | JUR-01, JUR-04 |
| D-K4-3 | Which sub-state dossiers get pages | all counties with ≥1 record (2,482); places with ≥10 records (2,817) + any place with non-site evidence; non-US admin-1 with ≥10 (218) | JUR-03, build size |
| D-K4-4 | US territories: under the United States or as countries | under US (Census state-equivalents), with ISO 3166-1 aliases | JUR-01 |
| D-K4-5 | Placement precedence `placement@1` (located wins; R3 repair heuristics fall back to declared) | adopt; revisit when first-class `Jurisdiction` entities land | JUR-02b |
| D-K4-6 | URL scheme (alpha-3 country segment; name-GEOID slugs) | adopt; keep `/dossier/` as the index root | JUR-04, JUR-05 |
| D-K4-7 | Publication profile for dossiers in countries without an adapter | conservative (no public-employee names) until an adapter exists (SIG-PUB-017) | JUR-03 |
| D-K4-8 | Corrections-log wording for merged, mislabelled and re-placed pages | approve agent drafts verbatim | JUR-05 |

---

## 11. Draft requirements and acceptance tests

Ids are provisional (`SIG-JUR-Dnn`). T1 numbers them or folds them into SIG-IDENT, SIG-UI and SIG-EXPORT.

| id | requirement (draft spec text) | acceptance test |
|---|---|---|
| SIG-JUR-D01 | Every published jurisdiction MUST be identified by exactly one scheme-qualified canonical key drawn from ISO 3166-1, ISO 3166-2, US Census GEOID with an explicit level, or a named national scheme. It MUST carry its other identifiers as `(scheme, value)` pairs in a published jurisdiction registry. | registry schema validates; GEOIDs fixed-width with level (SIG-IDENT-005); no two dossiers share a key; the `ID`/`MN` fixtures yield two keys each |
| SIG-JUR-D02 | A jurisdiction claim MUST keep its declared scheme from connector to spine to export. No export MAY group, slug or label on a bare code. | sink test: `candidate_identifier` round-trips; release test: every record's declared scheme is compatible with its key family ("no bucket mixes schemes"); grep test: no `_slugify(<bare value>)` on jurisdictions |
| SIG-JUR-D03 | Each published record MUST carry its placement: key chain, basis, check and boundary vintage. These are derived by a versioned ruleset from its point claims and from boundary datasets held as captured evidence. Boundary digests MUST be inputs to the release descriptor. | recompute every placement from the sites files + registry + boundary pack = 0 diffs; `boundaries_root` present in `sig.publication-descriptor/2` |
| SIG-JUR-D04 | A record whose located and declared jurisdictions disagree MUST be counted where it is located and disclosed on both dossiers with per-source counts. Points at (0,0) or suspected of axis swap or sign flip MUST NOT be placed, mapped or counted by their coordinates. | fixtures: Nottingham swap → declared GB-ENG with `axis_swap_suspected`, not on the map; CA→FL records on Florida's dossier and in California's "declared here, located elsewhere"; 0 records with `null_island` placed by point |
| SIG-JUR-D05 | Records without a placement MUST appear in a data-quality report with counts per reason (closed vocabulary) and per source. They MUST NOT be listed, counted or labelled as a jurisdiction. | the index jurisdiction count excludes it; Σ reasons = unplaced total; a crawl finds no "jurisdiction"/"dossier" wording on the report |
| SIG-JUR-D06 | The dossier index MUST group US states (and territories) under the United States, separately from other countries and their subdivisions. Each row MUST show name, code with scheme, level, records, located share, sources, evidence types, open questions, disagreements, freshness and children, each with a named definition. | HTML test: `/dossier/` has sections "United States", "Other countries", "Not yet placed" in that order; the row set equals the registry keys with ≥1 record at country/admin-1 level; each row's numbers equal its dossier JSON (parity) |
| SIG-JUR-D07 | SIG MUST publish county and place dossiers under each state for the thresholds the operator sets. A parent's total MUST equal the sum of its children plus records placed only at the parent level. | roll-up test over the release; page counts match D-K4-3; breadcrumbs resolve |
| SIG-JUR-D08 | Dossier titles MUST be human-readable names. Codes and schemes MUST be secondary. | crawl: no dossier `<h1>` equals a bare code; every row shows a name |
| SIG-JUR-D09 | Every dossier URL ever published (including print and JSON aliases) MUST resolve permanently to its successor, a split page listing its successors, or the data-quality report. A URL MUST NOT change to denote a different place. | V5 extension over the union of promoted releases' slugs: 0 × 404; `/dossier/md/` → Maryland, never Moldova; `/dossier/id/` lists Idaho and Indonesia |
| SIG-JUR-D10 | The dossier's publication regime MUST be derived from its country key. Countries without an adapter MUST use the conservative profile. | no export dossier lacks `jurisdictionCode`; a fixture DE dossier with a public-employee-name row renders "withheld" |
| SIG-JUR-D11 | Every dossier MUST be reachable without JavaScript within three clicks of `/dossier/`, via the hierarchy or an A–Z directory. A search form and a map entry MUST exist with no-JS baselines. | no-JS crawl depth ≤3; `/dossier/` and every directory: 0 `<script>` at baseline, ≤150 KiB |
| SIG-JUR-D12 | Legacy "as-of" permalinks printed on published dossiers MUST resolve to the content as originally published, with a correction banner where the content was later corrected. | `/dossier/id/?as_of_world=2026-09-27&…` → the 2026-09-27 snapshot page + banner (live probe after REL-09/JUR-05) |

**Acceptance journeys** (agent walkthroughs for JUR-06; never counted as user research, P4):

- **Advocate, Oklahoma City (design centre).** `/dossier/` → United States → Oklahoma → Oklahoma City in 3 clicks. It
  shows 391 records, 1 source (named), "evidence types: camera registries only", open questions, and the print view.
- **Journalist.** Opens an old citation of `/dossier/id/`, reaches the split page, then the Idaho dossier, and reads the
  corrections entry.
- **Organizer, Harris County.** Finds the county from the Texas table, sees 5,032 records from 3 sources, opens the K5
  explorer and downloads the county slice (after the K5 gates).
- **Researcher.** Opens `/dossier/unplaced/`, sees reasons and counts, and follows a reason to the research-queue tasks.

---

## 12. Risks

| id | risk | mitigation |
|---|---|---|
| R-K4-1 | Numbers move sharply (CA 6,139 → 28,334; `unresolved` 71.4% → ≈0.3%), so earlier citations look wrong | release changelog (TX-14) + corrections entries + legacy snapshot (D12) + "records" wording, never "devices" |
| R-K4-2 | Single-source states look "covered" (13 states rest on the OSM/DeFlock ALPR layer) | Sources and Evidence types are in every row; single-source facet route; honest note on the dossier |
| R-K4-3 | Boundary generalisation or shoreline clipping misplaces coastal points | TIGER (unclipped) for US containment; 0.02° tolerance elsewhere with check `within_tolerance`; vintage disclosed |
| R-K4-4 | Disputed territories become a political statement | D-K4-2; neutral names; ISO as published; one standing note |
| R-K4-5 | Page count and build time (≈17k files) | thresholds (D-K4-3); print via CSS; measurement in JUR-03; paged directories |
| R-K4-6 | ODbL records dominate most state dossiers (146,732 of 200,222 US-located records are in `osm_physical`) | per-compartment attribution on every dossier; downloads per compartment (K5) |
| R-K4-7 | Re-keying surfaces rights inconsistencies (NEW-4) before E4 has decided | JUR-03 emits the list; E4/E2 decide; no automatic rights change |
| R-K4-8 | Shipping ACT-24 before JUR-02 freezes bare-code URLs in immutable release namespaces (NEW-6) | ordering constraint recorded for S2; if unavoidable, the release tree's jurisdiction lists get slug-history aliases |
| R-K4-9 | The `census_geocoder` or ZIP route becomes a location-tracking surface | JUR-07 is later; no query logging; E2 review |

---

## 13. Interfaces

- **F5:** PKG-06a (merged here), PKG-06b (detectors and corrections), PKG-09a (API scopes), PKG-10 (per-dossier provenance
  → K5).
- **G3:**
  - REL-01: `boundaries_root` in descriptor v2.
  - REL-02: stamp.
  - REL-03b: `redirects.conf`.
  - REL-04b: V9 uses placement checks.
  - REL-05: release-backed dossier scopes.
  - REL-09: the legacy snapshot must be addressable (NEW-7).
  - Class S: the route set changes.
- **G2:** ACT-24 ordering (NEW-6); ACT-08 placeholder purge.
- **J3:** TX-05 facets and "Contribution to dossiers"; TX-09 `<Figure>`; TX-10a data dictionary for the new columns;
  TX-13 citations; TX-14 changelog.
- **I-stream:** I8 non-site attribution through `lookup@1`; new sources get placement checks at onboarding.
- **K:** K1 (bbox, boundaries layer), K3 (names index, "Canberra"), K5 (sources per dossier), K6 (per-dossier map), K11
  (task re-key), K13 (IA).
- **E:** E4/E2 for NEW-4 and for publication adapters (D-K4-7).

---

## 14. New findings (`findings/incoming/K4K5.csv`)

| id | title (short) | sev |
|---|---|---|
| NEW-1 | The connector's jurisdiction scheme is dropped at the sink (`assertion_from_record` ignores `candidate_identifier`), so the spine stores bare codes and no export can separate Idaho from Indonesia from claims alone (refines ED-29's root cause) | S2 |
| NEW-2 | Point-in-polygon places 91.5% of the `unresolved` bucket (152,058 of 166,210) in the US and gives every state + DC ≥1 located record, Oklahoma 1,705 (OKC 391). The "22 states without a dossier" is a keying artefact for site data (refines F-320 / I1 NEW-4) | S1 |
| NEW-3 | Polygon QA refines C3 NEW-6: 1,640 of 46,801 US-state-declared located records sit outside their declared state (CA 919, MO 248 on the Kansas side, WA 63, OR 53, IA 34, KY 29, DC 20), plus 193 in no polygon | S2 |
| NEW-4 | 6,462 records from 28 sources published under the non-US database-right basis (`operator_accepted`) are located inside US states (extends E1 NEW-13) | S2 |
| NEW-5 | Export dossiers never set `jurisdictionCode`, so every non-US dossier is gated under the US-DEFAULT publication adapter instead of the conservative unknown-jurisdiction rule (latent) | S2 |
| NEW-6 | The P32.13 release tree keys its jurisdiction record lists on the bare code, so the first promotion would freeze the ID/MN collisions and a 166,210-record `unresolved` list into immutable, citable URLs (latent) | S2 |
| NEW-7 | The 55 dossiers' printed "belief-pinned" permalinks have no addressable snapshot in the G3 plan (the legacy floor is rollback-only; unmatched selectors → 404), so re-keying breaks cited content | S2 |

K5 adds NEW-8 and NEW-9 (see K5 §14). Related, not re-raised: F-04, F-44, F-101, F-131, F-139, F-317, F-318, F-319, F-320;
C3 NEW-3/6/14; C5-G2; ED-29…32; J3 NEW-1; G3 NEW-2/6.

---

## 15. Limits

- No spine query (P3). Measurements are over the 2026-09-27 release files (manifest unchanged at 21:32:40Z). The live
  spine had drifted to ≈2.51 M claims at C3's read.
- Boundary joins used the **clipped** Census 500k files and NE 10m, not TIGER/Line. Coastal "no polygon" counts are
  therefore upper bounds, and the tolerance analysis is approximate.
- The downloaded boundary files, the DuckDB database and the per-query outputs are in this session's scratchpad (not
  committed; the row may write only three files). The Appendix reproduces them.
- The TIGER place total size, the geoBoundaries and national-dataset terms, and Natural Earth's terms text were not read.
  Licences are stated as published, with HG-03 pending (P15: availability is not rights clearance).
- Build-time and file-size projections are inference, to be measured in JUR-03.
- The absence of a `candidate_identifier` persistence path is shown by code reading and grep over `db/`, `connectors/`,
  `exports/` and `resolution/`. The hosted spine was not inspected.

## Appendix — reproduction

```
# release copies (sha-verified by C3): docs/build/logs/next-phase/C3/bucket/{web,sig_graph,parquet}
# boundaries (public domain):
#   https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_{state,county,place}_500k.zip
#   https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_{0_countries,1_states_provinces}.zip
# duckdb (worktree .venv, 1.5.5):  INSTALL spatial; LOAD spatial;
CREATE TABLE s AS SELECT *, '<comp>' comp FROM '<comp>.parquet' UNION ALL …;            -- 12 compartments, 236,994 rows
CREATE TABLE e AS SELECT entity_id, any_value(jurisdiction) j, any_value(point_status) ps,
       max(n_observation_claims) nc, max(n_sources) ns, any_value(geometry) g, any_value(source_id) src
       FROM s GROUP BY entity_id;                                                         -- 232,625
CREATE TABLE p AS SELECT entity_id, ST_Point(json_extract(g,'$.coordinates[0]')::DOUBLE,
       json_extract(g,'$.coordinates[1]')::DOUBLE) geom FROM e WHERE g IS NOT NULL;       -- 227,335
CREATE TABLE a0 AS SELECT ISO_A2_EH iso2eh, ADM0_A3 a3, geom FROM ST_Read('ne_10m_admin_0_countries.shp');
-- likewise a1 (iso_3166_2), st (STUSPS), co (GEOID, NAMELSAD), pl (GEOID, NAMELSAD)
CREATE TABLE m_st AS SELECT p.entity_id, b.usps FROM p JOIN st b ON ST_Intersects(b.geom, p.geom);  -- per layer
-- declared-vs-located: join e.j to src_scheme (camera_registry_targets.toml + dot_511_targets.toml, source_id → (scheme,value))
```

Work window closed **2026-09-30T22:02:52Z** (`date -u`; K4 and K5 written in the same window).
