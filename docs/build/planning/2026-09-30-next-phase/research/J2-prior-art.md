# J2 — Prior art and standards for SIG's transparency and export surface

- **Row:** J2 (Stream J, research) · **Written:** 2026-09-30 (research window 2026-09-30T16:44:43Z – 16:56:30Z, `date -u`)
- **Worktree HEAD at start:** `c7c773e8`
- **Feeds:** J3 (transparency and export design). J1 (current exposure inventory) and J4 (redistribution matrix)
  own SIG-internal facts. This note looks only at external prior art and standards, plus a ≤10-GET look at the live site.
- **Query log (P15):** `data/query_log_J2.csv`: 118 logged queries (103 WebFetch, 15 WebSearch), 93 with ≥1 hit kept.
  Every citation below is a `[Qnnn]` reference that resolves to the URL fetched under that query id (§9). A search
  engine's summary is never cited as evidence. Only pages that were actually fetched are cited.
- **Evidence classes (P1):** everything in §§1–3 is `live-read` (fetched 2026-09-30). The pattern catalog, standards
  recommendations, pitfalls and open questions (§§4–7) are `inference` built on those reads and labelled as such.
- **Status vocabulary (P5):** nothing here is engineered or verified for SIG. These are design inputs only.

---

## 0. Summary

**Top patterns (inference):**

1. **Source page** in the style of OpenSanctions plus Transitland. It shows the publisher and upstream URL, the
   declared and observed cadence, *last processed* and *last changed* as separate fields, counts, an issues link,
   version-addressed downloads, and a capture-history table keyed by content hash. Raw bytes are downloadable only when
   the licence allows redistribution.
2. **Per-value record provenance** in the style of the OpenSanctions entity page and statement model. Each value lists
   its sources with first-seen and last-changed dates, a link to the original, a "raw data explorer" and the
   "equivalent API request". Wikidata's reference properties (stated in, reference URL, retrieved, archive URL) are a
   good vocabulary for it.
3. **Public ingestion status** in the style of the OpenSanctions `/issues/` page and OpenAddresses job records:
   per-run status, the pinned source-definition commit, counts, and a warnings/errors log per run.
4. **Immutable releases with a changelog and machine-readable metadata**: Overture release notes plus the GERS
   changelog, OpenSanctions `index.json` with checksums and deltas, and OWID-style bundles that ship data, metadata
   and a README together.

**Standards to adopt (inference):** a SHA-256 manifest (low effort) plus a detached signature with minisign (low) or
Sigstore (medium). Frictionless Data Package v2 for each bundle (low). A DCAT 3 / DCAT-US 3 catalog (low to medium).
schema.org `Dataset` (low technically, but it collides with the zero-JS gate; see §7 Q1). A PROV-O export of
claim → capture → source (medium). Zenodo/DataCite DOIs with concept and version DOIs (low to medium, gated). An
SPDX identifier plus Transitland-style redistribution flags on each source (low). CSVW can wait.

**Pitfalls:**
- Republishing "public" records that contain plate numbers or search reasons (HaveIBeenFlocked).
- Redistributing raw bytes the licence does not allow. Transitland blocks this; OWID warns that third-party data
  keeps its providers' terms.
- Egress: requester-pays buckets refuse anonymous downloads, while OSM relies on sponsored hosting, torrents and mirrors.
- Stale or empty metadata. ProPublica's Data Store is archived, and SIG's own volatility class is "unknown" for all
  178 sources.
- Showing unverified crowdsourced data as fact (the DeFlock/OSM "mass panic" thread).
- Relying on MD5/SHA-1 alone.
- Silently stripping provenance from convenience dumps (Wikidata's "truthy" dumps carry no references).

---

## 1. SIG context observed (live-read, 8 GETs of the public site)

| Observation | Evidence |
|---|---|
| Nav exposes Map/Network/Search/Dossiers/Watch/Evidence, Methodology, Coverage, Data Freshness, Research Queue, Corrections; home cites "178 tracked sources", 255 artifacts, 2,423,200 published tier-0 claims | [Q001] |
| `/data-freshness/` per-source table: Source id · Last successful run · Last content change · Status · Stale entities · Volatility class — **volatility class "unknown" for all 178 sources**; some rows show last content change "not recorded" | [Q002] |
| `/evidence/` states "SIG has published no claims whose full evidence view is available for this build" | [Q003] |
| Dossiers show the source as a bare registry id (e.g. `camreg_azdot_az`), offer `/dossier/az.json` and a print/PDF, and a belief-pinned permalink with ruleset `p27.3/1.0.0` | [Q005], [Q007] |
| `/downloads/` → 404; `/manifest.json` at site root → 404 (a release manifest may exist elsewhere — J1 owns the inventory) | [Q006], [Q008] |
| Methodology/evidence pages cite "218 independent sources" while home/freshness cite 178 tracked sources — two different source counts on public pages (may be different definitions; *inference*, hand to J1/C) | [Q001], [Q003], [Q004] |

So SIG already has the start of three patterns: a freshness table that separates *last run* from *last content
change*, belief-pinned citations, and per-dossier JSON. What is missing is the source page, the record provenance
panel and the download center (*inference*; J1 is authoritative).

---

## 2. Project-by-project findings

The questions asked of each project are: can a user go from a source to its records, reach the original, download
raw and derived data, and see when and how the data was updated and what failed? How is provenance shown at record
level? How are licences handled? How are logs and metrics presented? What goes wrong?

### 2.1 OpenSanctions (closest overall exemplar)

- **Source page.** The `us_ofac_sdn` page shows:
  - the publisher (OFAC, US Treasury) and the source URL;
  - update frequency "daily · On the hour, every 2 hours";
  - *Last processed* "2026-09-30 16:10:01" with version `20260930161001-kvf`, and *Last changed* as a separate
    field;
  - the date coverage started (2015-12-05) and entity/target counts (72,604 / 20,414);
  - collections membership;
  - downloads in six formats (FtM JSON, names.txt, Senzing, **source XML**, nested JSON, simple CSV);
  - the licence (CC BY-NC 4.0). [Q009]
- **Version-addressed artifacts.** Every download link carries the version id
  (`data.opensanctions.org/artifacts/us_ofac_sdn/20260930161001-kvf/entities.ftm.json`). The page also links the
  upstream `sdn_advanced.xml`, the GitHub code, a statistics page and delta docs. [Q013] **The upstream raw file is
  republished for each version as `source.xml`.** That is the "raw bytes" download pattern, observed here for a US
  government public-domain source. [Q013]
- **Machine-readable metadata.** `index.json` separates `updated_at`, `last_change` and `last_export`, and carries:
  - `issue_count`, `issue_levels`, `issues_url`, `statistics_url`, `delta_url`;
  - a `coverage.schedule` cron (`0 */2 * * *`);
  - resources with `checksum`, `mime_type` and `size`.

  The checksum is a 40-hex digest, which is SHA-1 length (*inference*). No licence field was returned in the fetch.
  [Q015]
- **Deltas.** ADD/MOD/DEL line-JSON with the "last 100 versions" indexed. No delta is published when a version has
  no changes. Consumers must fully reload if they fall behind the index. The docs warn that de-duplication "may cause
  entities to change their identifier". [Q016]
- **Run statistics.** A per-dataset statistics page compares entity counts across recent runs (Sep 23 → Sep 30).
  [Q017]
- **Public issues log.** `/issues/` is introduced with "Below is an overview of all parsing and processing issues that
  appeared while importing the data." It shows warning and error counts per dataset, grouped into active, deprecated
  and KYB enrichment datasets. For example, EGRUL shows 4,221 warnings and 936 errors, with links to past runs.
  [Q020] Each dataset page links a version-addressed `issues.json`. The issue rows load from JSON, so our fetcher saw
  only the page shell. [Q021]
- **Record-level provenance.** The model is statement-based. Each value carries `dataset`, `first_seen`,
  `last_seen`, `original_value` and `canonical_id`, with a nightly bulk `statements.csv` and a web statement explorer.
  [Q014] The entity page shows:
  - each property value attributed to its sources (e.g. a birth date with "19 sources");
  - a "Data sources" section;
  - *First seen*, *Last change* and *Last processed*;
  - "Source link" entries to originals;
  - "For experts: raw data explorer";
  - an **"Equivalent request"** showing the API call. [Q022]
- **Data dictionary.** It is generated from the FollowTheMoney model, and the same information is published "in the
  JSON model file". [Q105]
- **Licence handling.** CC BY-NC 4.0, plus paid screening and reseller licences. The licensing page does not say how
  upstream source licences are handled. [Q012] Dataset-level files contain "only information sourced from that
  specific dataset", without cross-source enrichment. [Q011]
- **Failure modes seen.**
  - The `/changelog/` link on the dataset page returned 404. [Q013], [Q019]
  - The issues detail is JS-loaded, so no-JS readers and archivers cannot see it. [Q021]
  - The NC licence is a commercial-sustainability choice that SIG, as a public-interest record, need not copy
    (*inference*).

### 2.2 OpenStreetMap

- **Licence and attribution.**
  - ODbL, with the attribution notice varying by medium. Share-alike reads: "If you alter or build upon our data, you
    may distribute the result only under the same license."
  - A "Contributors" wiki page lists third-party sources, and a disclaimer says inclusion "does not imply that the
    original data provider endorses OpenStreetMap". [Q023]
  - For downloads, the notices go "in a location (such as a relevant directory) where users would be likely to look
    for it", such as a README or the metadata. [Q028]
  - The Collective Database guideline limits share-alike to "the parts containing or derived from OSM-data". But
    merging proprietary data with OSM "by removing any duplicate objects" creates a derivative database. [Q027] That
    is directly relevant to SIG's ODbL compartment and to entity resolution across compartments (*inference*).
- **Bulk data.**
  - A weekly full planet in XML (166 GB) and PBF (88 GB), with MD5 checksums, torrents, and a recommendation to use
    third-party regional extracts (Geofabrik, BBBike). [Q025]
  - planet.openstreetmap.org now redirects to an OSMF S3 bucket. [Q107] It is listed on the AWS Registry of Open
    Data, with eu-central-1 as primary, us-west-2 as a replica, and SNS new-file notifications. [Q110]
- **Update feed.**
  - Minute, hour and day replication diffs (osmChange), each with a `state.txt` that holds `sequenceNumber` and
    `timestamp`. [Q024]
  - The live minutely state read `sequenceNumber=7309165` and `timestamp=2026-09-30T16:53:01Z`. That is a trivially
    cheap, machine-readable freshness heartbeat. [Q108]
- **Edit-level provenance.**
  - Changesets record the user, timestamp, bounding box, `comment`, `created_by` and a `source=*` tag, and they have
    public discussion threads. [Q026]
  - Every API response embeds `copyright`, `attribution` and `license` attributes. [Q106]
  - Provenance is per edit session rather than per value. The source tag is a free-text convention (*inference*).
- **Withdrawal.** Reverting is not enough for licence-incompatible data; it "must actually be redacted". Redacted
  history renders as "Version 3 of this node cannot be shown as it has been redacted. Please see Redaction 6 for
  details." [Q114] That is a model for tombstones in an append-only record (*inference*).

### 2.3 Wikidata

- **Per-statement references:** `stated in` (P248), `reference URL` (P854), `retrieved` (P813) and `archive URL`
  (P1065). The principle is "most statements should indicate where the data comes from". [Q029]
- **Dumps:**
  - weekly JSON and RDF dumps, under CC0, with daily incremental dumps and torrents;
  - **"truthy" dumps contain only best-rank values, with no qualifiers or references**;
  - the docs warn against the XML dumps. [Q030]
- **Criticism:**
  - "50% of all statements as of July 2016 are unreferenced". About 34% of references point to other Wikimedia
    projects, which Wikidata's own policy does not accept. [Q033]
  - A 2025 study (RQSS) scores average referencing quality at 0.58/1, with weak completeness and verifiability, even
    though more than 73% of statements carry provenance metadata. [Q032]
  - The lesson is that having a reference field is not the same as having good provenance, and that convenience dumps
    which strip references break the chain (*inference*).

### 2.4 Our World in Data

- **Chart "Sources & processing".**
  - Each source is listed with its retrieved date (e.g. HMD retrieved 2025-10-22), next to a processing narrative
    that says which source wins for which years.
  - *Last updated*, **Next expected update** and *Managed by* fields.
  - A citation line ending "with major processing by Our World in Data".
  - A ZIP download containing CSV, JSON metadata and documentation. [Q034]
- **Chart API.** Each grapher slug serves `.csv` (full or filtered), `.metadata.json` (with `lastUpdated`,
  `nextUpdate` and citations) and `.zip` (CSV, metadata and a README). [Q035]
- **Public ETL.** The staged pipeline (snapshot → meadow → garden → grapher) has public code. [Q036] Origin
  metadata fields are `producer`, `url_main`, `url_download`, `date_accessed`, `date_published`, `license`
  (name + url) and `version_producer`. [Q038] That is a ready-made field list for SIG's source record (*inference*).
- **Licence.** OWID-produced data is CC BY, but "Most of the data … comes from third-party providers … and is subject
  to the license terms of those providers." [Q037]

### 2.5 Transitland (added: best source-page and capture-history exemplar)

- Each feed URL is checked "approximately once per hour". A new feed version is created only when the content
  changes, keyed by the SHA-1 of the archive. [Q070]
- The feed page shows *Last Fetch*, a licence summary, and a versions table with *Added*, *SHA1*, *Earliest date*,
  *Latest date* and a download. Metadata is edited through a public GitHub repository (Transitland Atlas). [Q072]
- Each source feed carries machine-readable licence fields: `spdx_identifier`, `url`, `use_without_attribution`,
  `create_derived_products`, `commercial_use_allowed`, `share_alike_optional`, `attribution_text` and
  **`redistribution_allowed`**. "If this parameter is set to no, Transitland will not allow downloading of feed
  versions." [Q071]
- Historic versions need a paid or complementary plan. Only the latest version is open to all. [Q070] This is a
  cost-control lever, and a transparency cost (*inference*).

### 2.6 OpenAddresses (added: best ingestion-run exemplar)

- The per-source data API lists each layer with `updated`, `job`, output flags (`validated`, `pmtiles`, `preview`)
  and `size`. [Q075]
- Each job record carries:
  - `status: "Success"` and `created`;
  - **the source definition pinned to a git commit** (`raw.githubusercontent.com/…/5ef8b85e…/sources/us/ca/san_francisco.json`);
  - the count (388,613), bounds, licence (PDDL 1.0), a `loglink`, a run id and the version. [Q077]
- "All data is openly licensed. Most sources only require attribution." [Q076]
- The batch UI itself is a JS app and was INACCESSIBLE to the fetcher. [Q073]

### 2.7 Overture Maps (added: best multi-licence release exemplar)

- **Licence per theme.** Base, Buildings, Divisions and Transportation are ODbL ("© OpenStreetMap contributors");
  Places is CDLA-Permissive-2.0; Addresses is per country (mostly CC BY 4.0); a NOTICE.txt ships for Apache-licensed
  input. [Q097] This is the closest analogue to SIG's licence compartments (*inference*).
- **Record-level `sources`.** Each entry lists `dataset`, `record_id`, `update_time` and `confidence`. [Q102]
- **Release notes.** Each release has a release id (`2026-05-20.0`) and a schema version (`v1.17.0`), per-theme
  changes, **deprecations with a removal month**, and the S3 and Azure release paths. [Q103]
- **GERS changelog.** Each release gets Parquet files of ID-level `added` / `removed` / `data_changed` /
  `unchanged`, with `columns_changed`. "sources and confidence are never compared", to avoid noise. [Q104]

### 2.8 OpenCorporates

- The API docs say: "we're obsessive about provenance of data – it not only gives confidence in the data by showing
  the source, and how fresh it is, it also allows errors to be tracked down and fixed".
  - Its provenance object has `source_url`, `source_type` (external/internal/induction), `confidence` (0–100),
    `actor_type` (bot/user), `log_message` and `created_at`.
  - Company responses carry `source.retrieved_at`, `url`, `publisher` and **`terms`** (the upstream licence, e.g.
    OGL). [Q043]
- `/info/our-data` now redirects to `/pricing/`. [Q041]

### 2.9 ProPublica Data Store

- Listings show the source, release date, date range covered, number of rows, topic, related stories, terms, and
  downloads with file sizes. [Q040]
- The store is **archived**: "None of the datasets provided by ProPublica on this page are actively updated." [Q040]
  An explicit archival notice beats silent staleness (*inference*).

### 2.10 EFF Atlas of Surveillance (peer)

- **Sources.** Crowdsourced research by more than 1,300 students and volunteers, plus aggregated third-party
  datasets. "Each line of data was then double-checked by multiple interns … and EFF staff." [Q045]
- **Stated limitations.** "the information is only as good as the source". Corrections go by email. [Q045]
- **Data library.** CSV, XLSX, PDF files and Google Sheets. Update cadence ranges from "Regularly" to fixed dates.
  Everything is CC-BY. There is **no central data dictionary**, and few entries include per-record source columns
  (fetcher summary, not a verbatim quote). [Q046]
- A search for external criticism found nothing relevant. [Q118]
- **What SIG can beat:** a per-record source link, a data dictionary and explicit update timestamps (*inference*).

### 2.11 DeFlock (peer) and the OSM "unverified cameras" episode

- **What DeFlock is.** It is an OSM editor for ALPRs that tags changesets with `created_by=DeFlock …` and maps
  `surveillance:type=ALPR`. [Q050] It reads OSM through Overpass and caches points and tiles in Cloudflare R2. The
  code is MIT-licensed. The README documents **no export and no refresh cadence**. [Q053] deflock.org is
  JS-rendered and was INACCESSIBLE. [Q049]
- **Failure mode.** An OSM community thread dated 2026-08-17 reports that unverified camera nodes from brand-new
  accounts "have been the subject of mass hysteria in several community facebook groups and subreddits". One example
  is "45 supposed Flock cameras in Poland, many in extra-dubious locations".
  - Proposed fixes: "trust labels (verified vs unverified)" and disclaimers that the data "is community OSM data, not
    vendor or agency sourced". [Q051]
  - This is the strongest peer argument for showing SIG's epistemic tier and review status wherever a record is
    rendered (*inference*).

### 2.12 HaveIBeenFlocked (cautionary)

- A site republished police **audit logs** obtained through public records requests that agencies had failed to
  redact. They held 2.3 million plates, tens of millions of searches, and search reasons such as "protest".
- Flock tried to have it taken down, and Cloudflare declined. [Q052]
- This is the direct Part VIII hazard for any "download the raw bytes" feature. A document can be lawfully public
  and still unfit for SIG to republish (*inference*).

### 2.13 MuckRock / DocumentCloud (partially INACCESSIBLE)

- MuckRock's request list returned 403 [Q054], and the DocumentCloud FAQ returned a JS shell or 403 [Q056], [Q058].
- From the API reference:
  - access is `public`, `private` or `organization` per document;
  - the **original PDF** (`pdf_url`) and the **extracted text** (`full_text_url`) are separate first-class URLs;
  - there are `source` and `published_url` fields. [Q059]
- The pattern is to publish the original and the extraction side by side, with an access level on each document
  (*inference*).

### 2.14 data.gov / CKAN

- A CKAN dataset page shows *Dataset First Published*, *Dataset Last Updated*, **Catalog Last Checked**, the
  identifier, landing page, licence (ODbL here) and resources in six formats, and links a **raw harvest record**.
  [Q063]
- **DCAT-US 1.1** makes these fields required: `title`, `description`, `keyword`, `modified`, `publisher`,
  `contactPoint`, `identifier` and `accessLevel`.
  - `accessLevel` takes `public`, `restricted public` or `non-public`.
  - `accrualPeriodicity` uses ISO 8601 (e.g. `R/P1Y`).
  - Agencies publish a `data.json` catalog. [Q062]
- **DCAT-US 3** is a profile of DCAT 3. It adds:
  - `DatasetSeries`, and `DataService` as a first-class object;
  - `hasQualityMeasurement` in place of free-text `dataQuality`;
  - `wasGeneratedBy`, `checksum`, and structured access and use restrictions;
  - JSON Schema 2020-12. [Q065]

### 2.15 Wikimedia dumps (status-page exemplar)

- `backup-index.html` lists each wiki's dump job with a completion timestamp and status ("Dump complete"), for
  example "2026-09-09 19:36:12 wikidatawiki: Dump complete".
- It states its capacity limits openly: "we are capping the number of per-ip connections to 3". [Q099]

### 2.16 Not assessed (INACCESSIBLE)

- Police Data Accessibility Project: the site is a JS shell [Q066], and search returned only press coverage [Q069].
- Surveillance Watch: JS shell. [Q074]
- OpenAddresses batch UI: JS shell; its API was used instead. [Q073]

### 2.17 Capability matrix (live-read, ✓ = observed; — = not observed in what was fetched)

| Capability | OpenSanctions | OSM | Wikidata | OWID | Transitland | OpenAddr. | Overture | AoS | DeFlock |
|---|---|---|---|---|---|---|---|---|---|
| Source page with publisher + upstream URL | ✓ [Q009] | contributors page [Q023] | — | ✓ per chart [Q034] | ✓ [Q072] | source def [Q077] | per theme [Q097] | — | — |
| Last-run vs last-change distinguished | ✓ [Q015] | state.txt [Q108] | — | last/next update [Q034] | last fetch + versions [Q072] | updated [Q075] | release id [Q103] | — | — |
| Per-value / per-record provenance | ✓ [Q014], [Q022] | per changeset [Q026] | ✓ [Q029] | per chart [Q034] | per version [Q072] | per job [Q077] | ✓ [Q102] | few [Q046] | — |
| Raw upstream bytes downloadable | ✓ source.xml [Q013] | n/a | n/a | — | ✓ if licence allows [Q071] | — | — | — | — |
| Content hash per artifact | ✓ [Q015] | MD5 [Q025] | — | — | SHA-1 [Q070] | — | — | — | — |
| Deltas / changelog | ✓ [Q016] | diffs [Q024] | incr. [Q030] | — | versions [Q072] | — | ✓ [Q104] | — | — |
| Public run errors / warnings | ✓ [Q020] | — | — | — | — | status + loglink [Q077] | — | — | — |
| Licence per source, machine-readable | — (not in index.json) [Q015] | API attrs [Q106] | CC0 [Q030] | origin.license [Q038] | ✓ SPDX + flags [Q071] | ✓ [Q077] | per theme [Q097] | CC-BY [Q046] | — |
| Data dictionary from a model | ✓ [Q105] | — | — | README [Q035] | — | — | schema ver. [Q103] | ✗ [Q046] | — |

---

## 3. Standards (live-read facts)

| Standard | What it gives SIG | Key facts read |
|---|---|---|
| **W3C DCAT 3** (Rec. 2024-08-22) | Catalog / Dataset / Distribution / DataService / **DatasetSeries** / CatalogRecord; `downloadURL` vs `accessURL`; `license` vs `rights` vs `accessRights`; versioning (`dcat:version`, `previousVersion`, `hasVersion`, `hasCurrentVersion`, `versionNotes`); `spdx:checksum`; `prov:qualifiedAttribution` | [Q078] |
| **DCAT-US 3** (profile of DCAT 3) | US-federal profile; dataset series; `hasQualityMeasurement`; `wasGeneratedBy`; `checksum`; structured Access/Use restrictions; JSON Schema 2020-12. DCAT-US 1.1 `accessLevel` enumeration (`public`/`restricted public`/`non-public`) maps onto SIG compartments | [Q065], [Q062] |
| **schema.org `Dataset`** + Google Dataset Search | Required `name`, `description` (50–5000 chars); recommended `license` (versioned URL), `distribution`→`DataDownload{contentUrl, encodingFormat}`, `temporalCoverage`, `spatialCoverage`, `variableMeasured`, `identifier`, `version`; Google also accepts **DCAT** and **CSVW (beta)**; JSON-LD preferred | [Q079]; relevant extra props `isBasedOn`, `sdDatePublished`, `creditText`, `conditionsOfAccess`, `correction`, `measurementTechnique` [Q088] |
| **Frictionless Data Package v2** | `datapackage.json` with `resources` (required), `licenses`, `sources`, `version` (SemVer), `created`; per-resource `path`, `bytes`, `mediatype`, `hash` (MD5 default; other algorithms by prefix e.g. `sha256:`), per-resource `licenses`/`sources`, Table Schema | [Q080], [Q083] |
| **CSV on the Web** (Recs Dec 2015) | `<file>.csv-metadata.json`; columns with `datatype`, `required`, `primaryKey`, `foreignKeys`; `aboutUrl`/`propertyUrl`/`valueUrl` for RDF conversion | [Q081] |
| **W3C PROV-O** (Rec. 2013-04-30) | Entity/Activity/Agent; `wasDerivedFrom`, **`hadPrimarySource`**, `wasQuotedFrom`, `wasGeneratedBy`, `generatedAtTime`, `invalidatedAtTime`; **`prov:Bundle`** = provenance of provenance | [Q082] |
| **Checksums** | NIST retires SHA-1 for all applications by 2030-12-31; SHA-2/SHA-3 are the replacements — so OSM's MD5, Transitland's SHA-1 and OpenSanctions' 40-hex digests are integrity-only legacy choices (*inference*) | [Q113] |
| **minisign** | Ed25519; `minisign -Sm file -t '<trusted comment>'`; verify with published key `-Vm -P`; trusted comments are signed (prevents downgrade); signify-compatible | [Q085] |
| **Sigstore cosign** | `cosign sign-blob <file> --bundle bundle.sigstore.json`; keyless (OIDC identity) or key-based; bundle holds signature + certificate + transparency-log inclusion proof | [Q084] |
| **GitHub artifact attestations** | `actions/attest` with `id-token: write`, `attestations: write`; verify with `gh attestation verify`; docs show binaries/images — arbitrary data files not explicitly covered | [Q116] |
| **Zenodo / DataCite DOIs** | A DOI per published upload, reservable pre-publication [Q086]; **concept DOI** (all versions) vs **version DOI** [Q089]; GitHub integration mints a DOI per GitHub release (public repos only) [Q090]; DataCite `relationType` `IsDerivedFrom`, `IsNewVersionOf`, `IsPartOf`, `IsObsoletedBy`, `IsCompiledBy` [Q117] |
| **Transitland licence fields** (de-facto schema, not a standard) | SPDX id + `redistribution_allowed` / `create_derived_products` / `commercial_use_allowed` / `share_alike_optional` / `use_without_attribution` / `attribution_text` | [Q071] |

---

## 4. Pattern catalog for SIG (inference, built on §§2–3)

Each entry gives the best exemplar and why, what SIG should take from it, and the SIG-specific constraints.

### PC-1 Source index (`/sources/`)
- **Best exemplar:** the OpenSanctions `/issues/` overview [Q020]. It covers every source on one page with
  warning/error counts, grouped by lifecycle (active / deprecated / enrichment). It is a health view, not only a
  catalogue.
- **Runner-up:** data.gov search results, which show publisher, formats and last-updated per row. [Q060]
- **What SIG should take:**
  - A static table, one row per registry source: id, human name, publisher, jurisdiction, technology class,
    licence (SPDX), redistribution lane (J4), declared cadence, last run, last content change, status, open issues,
    claim count.
  - Group rows by lifecycle: ingesting / gated (`ingestion_permitted=false`) / retired.
  - Replace bare ids such as `camreg_azdot_az` with the human name and a link, on dossiers too.
  - Offer zero-JS facets as pre-rendered pages per state and technology, not client filtering.
- **Why:** SIG already tracks run and change times on `/data-freshness/` [Q002]. The index adds rights and
  navigation.

### PC-2 Source page (`/sources/<id>/`)
- **Best exemplars:**
  - OpenSanctions dataset page [Q009], [Q013] for its field set and version-addressed downloads;
  - Transitland feed page [Q072], [Q071] for a capture-history table keyed by content hash, with downloads gated by
    a machine-readable redistribution flag;
  - OWID [Q034], [Q038] for "Next expected update" and the origin field list.
- **What SIG should take:**
  - **Upstream:** publisher, upstream URLs, and the terms and licence *verbatim*, from the rights-review record.
  - **Cadence:** declared cadence (DCAT `accrualPeriodicity`) and observed cadence, plus *last successful run*,
    *last content change* and *next expected check*.
  - **Capture history:** captured-at, sha256, bytes, changed or unchanged, and a download only if the lane is
    `raw-ok`; otherwise hash plus upstream link.
  - **Run log:** see PC-6.
  - **Coverage:** geography and technology counts, sample records, and known issues.
  - **Corrections:** a correction and dispute link.
  - **Machine-readable twin:** `/sources/<id>/index.json`, shaped like the OpenSanctions `index.json` [Q015].

### PC-3 Record provenance panel
- **Best exemplars:**
  - OpenSanctions entity page [Q022] with the statement model [Q014]: values attributed per source, first seen /
    last change, source links, a raw explorer, and the "equivalent request";
  - Wikidata reference vocabulary [Q029];
  - OpenCorporates provenance, including `terms` and `confidence` [Q043];
  - Overture `sources[]` with `record_id` [Q102].
- **What SIG should take:** for each claim, show the source, then the capture (`retrieved_at`, sha256, OCFL object
  id), then the upstream URL.
  - **"View original":** the archived capture if the lane is `raw-ok`; otherwise the upstream link plus an archive
    URL if one exists.
  - **Claim history:** extraction method and version, first seen / last seen, review status and epistemic tier,
    contradicting claims, and supersession history.
  - **Links:** "equivalent API request", and a PROV-JSON-LD link.
- **Why:** SIG claims are already per value and append-only, so this is presentation rather than new modelling.
  `/evidence/` currently publishes no full evidence view [Q003] (J1 to confirm why).

### PC-4 Download center (`/data/`)
- **Best exemplars:**
  - OpenSanctions [Q009], [Q013], [Q015], [Q016]: files per source and per collection, several formats,
    version-addressed immutable URLs plus a `latest` alias, checksums and sizes in `index.json`, ADD/MOD/DEL deltas;
  - OWID `.zip` bundles of CSV, metadata and README [Q035];
  - OSM for scale: torrents, mirrors, third-party extracts, sponsored hosting [Q025], [Q110].
- **What SIG should take:**
  - A download matrix by compartment × release × (whole, or per source/state slice).
  - Every bundle carries `datapackage.json`, `README` with licence and attribution (per the OSM guideline [Q028]),
    `SHA256SUMS` plus a signature, and a data-dictionary link.
  - Deltas between releases.
  - API parity: every file is also reachable through `/v1/export`.

### PC-5 Release and changelog (`/releases/<id>/`)
- **Best exemplars:**
  - Overture release notes: release id, schema version, per-theme changes, deprecations with removal dates [Q103];
  - the GERS ID-level changelog [Q104];
  - Zenodo concept and version DOIs [Q089].
- **What SIG should take:**
  - A human changelog: sources added, retired or failed; claim counts added, superseded or withdrawn per source;
    ontology/schema version; ruleset version (`p27.3/1.0.0` already appears on pages [Q004]).
  - A machine changelog: an ID-level Parquet or CSV like GERS.
  - Deprecation notices with dates.
  - A version DOI per release and one concept DOI.

### PC-6 Ingestion status and run log (`/data-freshness/` → per-run pages)
- **Best exemplars:**
  - OpenSanctions `/issues/` [Q020], [Q021]: warnings and errors per source and per version, as JSON;
  - OpenAddresses job record [Q077]: status, **source definition pinned to a commit**, counts, bounds, licence,
    log link;
  - Wikimedia dump status [Q099]: job timestamps and capacity limits stated openly;
  - OSM `state.txt` [Q108]: a one-file heartbeat.
- **What SIG should take:**
  - Per run: run id, mode, start and end, connector commit, fetched / parsed / claims added / duplicate / rejected,
    and scrubbed warning and error classes with counts.
  - A `runs.json` for each source, and a site-wide `state.txt`-style heartbeat.
  - Render server-side so it works with zero JS. OpenSanctions' JS-loaded issue rows are the anti-pattern [Q021].
  - Fill in the currently "unknown" volatility class [Q002].

### PC-7 Data dictionary (`/data/dictionary/`)
- **Best exemplar:** OpenSanctions reference generated from the FtM model, "also available in the JSON model file"
  [Q105].
- **Counter-example:** Atlas of Surveillance, which has no central dictionary [Q046].
- **What SIG should take:** generate it from the LinkML ontology, which is already the single source of truth. Emit
  HTML, a Table Schema for each CSV, and optionally CSVW.

### PC-8 Machine-readable metadata
- **Best exemplars:** OpenSanctions `index.json` [Q015], OWID `.metadata.json` [Q035], and the CKAN raw harvest
  record [Q063].
- **What SIG should take:** one metadata model, emitted as:
  - `catalog.jsonld` (DCAT 3);
  - `data.json` (DCAT-US, optional);
  - `datapackage.json` per bundle;
  - schema.org `Dataset` (subject to §7 Q1).

### PC-9 Licence-gated raw archive
- **Best exemplar:** Transitland `redistribution_allowed=no` → no downloads [Q071].
- **Also:** OpenSanctions republishes upstream `source.xml` for a public-domain source [Q013].
- **What SIG should take:** J4's lanes (`raw-ok` · `derived-only` · `link-only` · `restricted`) drive the UI and the
  export. Non-`raw-ok` captures show the hash, size and timestamps only.

### PC-10 Trust labels
- **Best exemplars:** the DeFlock/OSM thread's "verified vs unverified" proposal [Q051], OpenCorporates `confidence`
  [Q043], and Overture `confidence` [Q102].
- **What SIG should take:** show the epistemic tier and review state next to every rendered record, map point and
  download row, including crowdsourced-origin flags.

### PC-11 Tombstones and redaction
- **Best exemplars:** the OSM redaction message [Q114] and OpenSanctions `DEL` operations [Q016].
- **What SIG should take:** a withdrawn record gets a tombstone page with its reason class and date, not a silent 404.
  Deltas carry the withdrawal.

---

## 5. Standards SIG should adopt (inference; effort = rough engineering effort, not calendar)

| # | Standard | Use in SIG | Effort | Recommendation |
|---|---|---|---|---|
| S-1 | SHA-256 `SHA256SUMS` + per-file hash in manifests | every release file and capture listing; replaces MD5/SHA-1-style integrity [Q113] | **low** | adopt now |
| S-2 | Detached signature over the manifest: **minisign** [Q085] (key in env per HG-09) *or* **cosign keyless** in CI [Q084] | authenticity of releases, not just integrity | low (minisign) / med (cosign) | adopt one; operator picks key custody |
| S-3 | **Frictionless Data Package v2** + Table Schema [Q080], [Q083] | `datapackage.json` per bundle with per-resource `licenses`, `sources`, `hash: "sha256:…"` | **low** | adopt now |
| S-4 | **DCAT 3** catalog (JSON-LD) [Q078]; DCAT-US 3 fields where cheap [Q065] | site-wide `catalog.jsonld`; `DatasetSeries` = SIG releases; `accessRights` per compartment | low–med | adopt |
| S-5 | **schema.org `Dataset`** JSON-LD [Q079], [Q088] | discoverability in Google Dataset Search; `isBasedOn`, `creditText`, `conditionsOfAccess`, `correction` fit SIG well | low (code) / **med** (zero-JS gate ADR, §7 Q1) | adopt, subject to the gate decision |
| S-6 | **PROV-O** (JSON-LD) [Q082] | per-record provenance export: claim `wasDerivedFrom` capture, capture `hadPrimarySource` upstream, `generatedAtTime`; release as `prov:Bundle` | **med** | adopt for the API + evidence pages; LinkML can generate the mapping (*inference*) |
| S-7 | **Zenodo/DataCite DOIs** (concept + version) [Q089], [Q117] | citable releases; complements belief-pinned permalinks | low–med + **gate** (deposits are effectively permanent; publication gates) | adopt for public compartments only, after operator go |
| S-8 | **SPDX id + Transitland-style redistribution flags** [Q071] | per-source rights record → J4 lanes → UI/export gating | **low** | adopt |
| S-9 | **CSVW** [Q081] | alternative to Table Schema; Google beta support [Q079] | low–med | defer (Data Package covers it) |
| S-10 | GitHub artifact attestations [Q116] | build provenance for the export job | med | optional; arbitrary-file support not confirmed |

---

## 6. Pitfalls to avoid (inference, each anchored in a read)

1. **Leaking restricted data through "raw" downloads or logs.** HaveIBeenFlocked shows that public-records releases
   can carry plates and search reasons [Q052].
   - Every raw capture, log excerpt and issue message needs a Part VIII scrub. That covers plates, persons, officer
     names, search reasons, internal paths, secrets and IPs.
   - Capture bytes default to *not* downloadable.
   - Availability is never rights clearance (P15).
2. **Licence violations when redistributing bytes.** Upstream terms survive republication [Q037]. Transitland builds
   the block into the data model [Q071].
   - ODbL share-alike reaches derived databases, including de-duplication merges [Q027].
   - Attribution must travel inside each bundle [Q028].
   - Mixing ODbL-derived resolution into non-ODbL bundles is the likeliest SIG trap (*inference*).
3. **Egress cost versus openness.**
   - Requester Pays moves egress costs to downloaders but **blocks anonymous access** [Q094]. That is incompatible
     with public downloads.
   - OSM uses sponsored S3 hosting plus torrents and mirrors [Q025], [Q110]. The AWS Open Data Sponsorship covers
     storage and sharing for eligible datasets [Q092]. Source Cooperative is a nonprofit alternative, with pricing
     still to be announced [Q093].
   - Wikimedia caps each IP at 3 connections [Q099]. Transitland paywalls historic versions [Q070].
   - SIG needs a volume estimate (J4) and a hosting decision before promising "download everything".
4. **Stale metadata.**
   - ProPublica's store is archived [Q040]. OpenSanctions' changelog link 404s [Q013], [Q019]. OpenCorporates' data
     page redirects to pricing [Q041].
   - A study of more than 260 portals and 1.1M datasets documents systemic metadata-quality and retrievability
     problems [Q115].
   - SIG's volatility class is "unknown" for every source [Q002].
   - Fix: generate all metadata from run records. Show *last checked* separately from *last changed*, as data.gov
     does [Q063]. Mark archived or retired sources explicitly.
5. **Crowdsourced data shown as fact** [Q051]. Trust labels are needed everywhere a record renders, including map
   tiles and CSV columns.
6. **Provenance stripped in convenience exports.** Wikidata's "truthy" dumps drop references [Q030]. Reference
   presence is not reference quality [Q032], [Q033]. Every SIG derived file should carry at least `source_id`,
   `capture_sha256` and `retrieved_at` columns.
7. **Weak hashes as security claims.** MD5 and SHA-1 give integrity only [Q113]. Pair SHA-256 with a signature (S-2).
8. **Identifier churn.** OpenSanctions IDs change under de-duplication [Q016]. Overture needed a changelog for this
   [Q104]. SIG's re-resolution will need stable public IDs plus an ID-level changelog.
9. **JS-only transparency surfaces.** OpenSanctions issue rows, the OpenAddresses batch UI, DeFlock, PDAP and
   Surveillance Watch were all unreadable to a plain fetcher [Q021], [Q073], [Q049], [Q066], [Q074]. SIG's zero-JS
   rule is an advantage here. Keep run logs and issues statically rendered.
10. **Irreversible distribution versus withdrawal.** Downloaded files and DOI deposits cannot be recalled. OSM needed
    a redaction mechanism [Q114]. Gate what enters an immutable release before it ships.

---

## 7. Open questions for J3 (design)

1. **JSON-LD versus the zero-JS gate.** schema.org and DCAT on-page markup uses `<script type="application/ld+json">`
   [Q079]. SIG's public content pages must have **no `<script>` tags** (repo `AGENTS.md`, Gotcha 6). The options are:
   - exempt non-executable data blocks from the check (needs an ADR);
   - publish JSON-LD only as linked `catalog.jsonld` / `index.json` files;
   - or rely on Google's DCAT support [Q079].
2. **Where do downloads live, and who pays egress?** The options are the static host, the GCS bucket, AWS ODP or
   Source Cooperative [Q092], [Q093]. Is there a size cap per file? Torrents?
3. **Do downloads track immutable releases, the live spine, or both?** OpenSanctions does both: a `latest` alias and
   versioned artifacts [Q013], [Q015]. What is SIG's release cadence against its daily runs?
4. **Which digest?** It should match whatever SIG's OCFL store and `manifest` already use (J1 to confirm). Signing
   tool and key custody (S-2) is an operator decision under HG-09.
5. **DOIs.** Zenodo's GitHub integration fires on GitHub releases [Q090], but SIG agents never tag or push `main`.
   Should deposits be manual and operator-run? And which compartments may be deposited, given withdrawal?
6. **Raw-bytes granularity.** Per capture, or per source snapshot? What does a `restricted` or `link-only` capture
   show: hash only, or hash plus size and timestamps?
7. **Run-log scrub rules.** What fields, error-message classes and paths are publishable (J4 input)? Are failed
   *gated* sources (`ingestion_permitted=false`) shown at all?
8. **"No change" runs.** Should SIG record a capture only on change, like Transitland [Q070], or log every run and
   mark it unchanged (SIG already separates run from change [Q002])?
9. **Stable public identifiers and an ID-level changelog** across re-resolution, in the style of GERS [Q104].
10. **Declared cadence.** Should each source carry a declared cadence and a "next expected check" (OWID [Q034], DCAT
    `accrualPeriodicity` [Q062])? That would replace "volatility class: unknown" [Q002].
11. **Trust labels.** How are the epistemic tier and review state shown on map tiles and in CSV columns [Q051]? How
    are crowdsourced or OSM-derived claims flagged?
12. **Statement-level export.** Should SIG publish a `statements.csv` equivalent (one row per claim with
    source/capture/time) alongside entity-level files, as OpenSanctions does [Q014]?
13. **ODbL boundary.** Does any SIG resolution step merge ODbL and non-ODbL records into one entity, making a
    derivative database under the Collective Database guideline [Q027]? If so, which bundle inherits share-alike?
14. **"Equivalent API request" on every page** [Q022]. Is `/v1/export` parity a hard requirement or best-effort?
15. **Two public source counts** (178 vs 218) [Q001], [Q003]. Reconcile the definitions before a source index goes
    live.

---

## 8. Limitations

- **INACCESSIBLE:** MuckRock request list (403) [Q054]; DocumentCloud FAQ (JS or 403) [Q056], [Q058]; deflock.org
  (JS) [Q049]; PDAP (JS) [Q066]; Surveillance Watch (JS) [Q074]; OpenAddresses batch UI (JS) [Q073].
- **Errors:** Transitland feed-versions concept page (404) [Q067]; data.gov new-style dataset URL (404) [Q061];
  Overture `release/latest` and `release-notes` (404) [Q098], [Q101]; OpenSanctions `/changelog/` (404) [Q019];
  OpenSanctions terms FAQ (navigation only) [Q096].
- The fetcher summarises pages through a small model. Quoted strings were requested verbatim, but they were not
  independently re-checked against raw HTML. Treat counts and dates as `live-read` at the stated time.
- **Not covered:** no licence or legal analysis is given (P4). The OpenSanctions NC-licence debate was seen only in
  search snippets [Q095] and is not cited as fact. There is no external criticism of Atlas of Surveillance [Q118].

---

## 9. References (query id → URL fetched; full log in `data/query_log_J2.csv`)

| id | tool | query or URL | run_at (UTC) | kept |
|---|---|---|---|---|
| Q001 | WebFetch | https://surveillancegraph.org/ | 2026-09-30T16:44:43Z | 1 |
| Q002 | WebFetch | https://surveillancegraph.org/data-freshness/ | 2026-09-30T16:44:43Z | 1 |
| Q003 | WebFetch | https://surveillancegraph.org/evidence/ | 2026-09-30T16:44:43Z | 1 |
| Q004 | WebFetch | https://surveillancegraph.org/methodology/ | 2026-09-30T16:44:43Z | 1 |
| Q005 | WebFetch | https://surveillancegraph.org/dossier/ | 2026-09-30T16:44:43Z | 1 |
| Q006 | WebFetch | https://surveillancegraph.org/downloads/ | 2026-09-30T16:44:43Z | 0 |
| Q007 | WebFetch | https://surveillancegraph.org/dossier/az/ | 2026-09-30T16:44:43Z | 1 |
| Q008 | WebFetch | https://surveillancegraph.org/manifest.json | 2026-09-30T16:44:43Z | 0 |
| Q009 | WebFetch | https://www.opensanctions.org/datasets/us_ofac_sdn/ | 2026-09-30T16:45:24Z | 1 |
| Q010 | WebFetch | https://www.opensanctions.org/datasets/us_ofac_sdn/issues/ | 2026-09-30T16:45:24Z | 0 |
| Q011 | WebFetch | https://www.opensanctions.org/docs/bulk/ | 2026-09-30T16:45:24Z | 1 |
| Q012 | WebFetch | https://www.opensanctions.org/licensing/ | 2026-09-30T16:45:24Z | 1 |
| Q013 | WebFetch | https://www.opensanctions.org/datasets/us_ofac_sdn/ | 2026-09-30T16:45:24Z | 1 |
| Q014 | WebFetch | https://www.opensanctions.org/docs/statements/ | 2026-09-30T16:45:24Z | 1 |
| Q015 | WebFetch | https://data.opensanctions.org/datasets/latest/us_ofac_sdn/index.json | 2026-09-30T16:45:24Z | 1 |
| Q016 | WebFetch | https://www.opensanctions.org/docs/bulk/delta/ | 2026-09-30T16:45:24Z | 1 |
| Q017 | WebFetch | https://www.opensanctions.org/datasets/us_ofac_sdn/statistics/ | 2026-09-30T16:45:24Z | 1 |
| Q018 | WebSearch | opensanctions.org dataset "issues" warnings errors crawler page | 2026-09-30T16:45:24Z | 3 |
| Q019 | WebFetch | https://www.opensanctions.org/changelog/ | 2026-09-30T16:45:24Z | 0 |
| Q020 | WebFetch | https://www.opensanctions.org/issues/ | 2026-09-30T16:45:24Z | 1 |
| Q021 | WebFetch | https://www.opensanctions.org/issues/ua_war_sanctions | 2026-09-30T16:45:24Z | 1 |
| Q022 | WebFetch | https://www.opensanctions.org/entities/Q7747/ | 2026-09-30T16:46:18Z | 1 |
| Q023 | WebFetch | https://www.openstreetmap.org/copyright | 2026-09-30T16:46:38Z | 1 |
| Q024 | WebFetch | https://wiki.openstreetmap.org/wiki/Planet.osm/diffs | 2026-09-30T16:46:38Z | 1 |
| Q025 | WebFetch | https://planet.openstreetmap.org/ | 2026-09-30T16:46:38Z | 1 |
| Q026 | WebFetch | https://wiki.openstreetmap.org/wiki/Changeset | 2026-09-30T16:46:38Z | 1 |
| Q027 | WebFetch | https://osmfoundation.org/wiki/Licence/Community_Guidelines/Collective_Database_Guideline_Guideline | 2026-09-30T16:46:38Z | 1 |
| Q028 | WebFetch | https://osmfoundation.org/wiki/Licence/Attribution_Guidelines | 2026-09-30T16:46:38Z | 1 |
| Q029 | WebFetch | https://www.wikidata.org/wiki/Help:Sources | 2026-09-30T16:47:04Z | 1 |
| Q030 | WebFetch | https://www.wikidata.org/wiki/Wikidata:Database_download | 2026-09-30T16:47:04Z | 1 |
| Q031 | WebSearch | Wikidata references quality study proportion of statements unreferenced "imported from Wikimedia project" | 2026-09-30T16:47:04Z | 2 |
| Q032 | WebFetch | https://researchportal.hw.ac.uk/en/publications/rqss-referencing-quality-scoring-system-for-wikidata/ | 2026-09-30T16:47:04Z | 1 |
| Q033 | WebFetch | https://meta.wikimedia.org/wiki/Grants:Project/Finding_References_and_Sources_for_Wikidata | 2026-09-30T16:47:04Z | 1 |
| Q034 | WebFetch | https://ourworldindata.org/grapher/life-expectancy | 2026-09-30T16:47:32Z | 1 |
| Q035 | WebFetch | https://docs.owid.io/projects/etl/api/chart-api/ | 2026-09-30T16:47:32Z | 1 |
| Q036 | WebFetch | https://docs.owid.io/projects/etl/architecture/ | 2026-09-30T16:47:53Z | 1 |
| Q037 | WebFetch | https://ourworldindata.org/faqs | 2026-09-30T16:47:53Z | 1 |
| Q038 | WebFetch | https://docs.owid.io/projects/etl/architecture/metadata/reference/ | 2026-09-30T16:47:53Z | 1 |
| Q039 | WebFetch | https://www.propublica.org/datastore/ | 2026-09-30T16:48:03Z | 0 |
| Q040 | WebFetch | https://projects.propublica.org/datastore/ | 2026-09-30T16:48:03Z | 1 |
| Q041 | WebFetch | https://opencorporates.com/info/our-data | 2026-09-30T16:48:03Z | 0 |
| Q042 | WebSearch | OpenCorporates provenance every piece of data source URL retrieved date company page | 2026-09-30T16:48:03Z | 1 |
| Q043 | WebFetch | https://api.opencorporates.com/documentation/API-Reference | 2026-09-30T16:48:22Z | 1 |
| Q044 | WebFetch | https://atlasofsurveillance.org/ | 2026-09-30T16:48:33Z | 1 |
| Q045 | WebFetch | https://atlasofsurveillance.org/methodology | 2026-09-30T16:48:33Z | 1 |
| Q046 | WebFetch | https://atlasofsurveillance.org/data-library | 2026-09-30T16:48:33Z | 1 |
| Q047 | WebFetch | https://deflock.me/ | 2026-09-30T16:48:33Z | 0 |
| Q048 | WebSearch | DeFlock ALPR map OpenStreetMap data source methodology criticism accuracy | 2026-09-30T16:48:33Z | 4 |
| Q049 | WebFetch | https://deflock.org/ | 2026-09-30T16:48:33Z | 0 |
| Q050 | WebFetch | https://wiki.openstreetmap.org/wiki/Deflock | 2026-09-30T16:48:33Z | 1 |
| Q051 | WebFetch | https://community.openstreetmap.org/t/unverified-flock-cameras-causing-mass-panic/146534 | 2026-09-30T16:48:33Z | 1 |
| Q052 | WebFetch | https://san.com/cc/flock-threatens-website-hosting-license-plate-data-accidentally-leaked-by-cops/ | 2026-09-30T16:48:33Z | 1 |
| Q053 | WebFetch | https://github.com/FoggedLens/deflock | 2026-09-30T16:49:19Z | 1 |
| Q054 | WebFetch | https://www.muckrock.com/foi/list/ | 2026-09-30T16:49:31Z | 0 |
| Q055 | WebFetch | https://www.documentcloud.org/help/faq/ | 2026-09-30T16:49:31Z | 0 |
| Q056 | WebFetch | https://help.muckrock.com/Frequently-Asked-Questions-19ef889269638193975edda45199e14e | 2026-09-30T16:49:31Z | 0 |
| Q057 | WebSearch | DocumentCloud access levels public private organization redaction original PDF text download API | 2026-09-30T16:49:31Z | 1 |
| Q058 | WebFetch | https://next.www.documentcloud.org/help/faq | 2026-09-30T16:49:46Z | 0 |
| Q059 | WebFetch | https://documentcloud.readthedocs.io/en/latest/documents.html | 2026-09-30T16:49:46Z | 1 |
| Q060 | WebFetch | https://catalog.data.gov/dataset/?q=license+plate+reader | 2026-09-30T16:49:46Z | 1 |
| Q061 | WebFetch | https://data.gov/dataset/electric-vehicle-population-data | 2026-09-30T16:49:46Z | 0 |
| Q062 | WebFetch | https://resources.data.gov/resources/dcat-us/ | 2026-09-30T16:49:46Z | 1 |
| Q063 | WebFetch | https://catalog.data.gov/dataset/electric-vehicle-population-data | 2026-09-30T16:50:17Z | 1 |
| Q064 | WebSearch | DCAT-US 3.0 specification released GSA data.gov | 2026-09-30T16:50:17Z | 1 |
| Q065 | WebFetch | https://resources.data.gov/resources/dcat-us3/ | 2026-09-30T16:50:17Z | 1 |
| Q066 | WebFetch | https://pdap.io/ | 2026-09-30T16:50:31Z | 0 |
| Q067 | WebFetch | https://www.transit.land/documentation/concepts/feed-versions | 2026-09-30T16:50:31Z | 0 |
| Q068 | WebSearch | Transitland feed version sha1 fetched_at archived redistribution license "redistribution_allowed" | 2026-09-30T16:50:31Z | 3 |
| Q069 | WebSearch | Police Data Accessibility Project data sources database fields record type access type update frequency docs | 2026-09-30T16:50:31Z | 0 |
| Q070 | WebFetch | https://www.transit.land/documentation/concepts/static-gtfs-feed-versions | 2026-09-30T16:50:53Z | 1 |
| Q071 | WebFetch | https://www.transit.land/documentation/concepts/source-feeds/ | 2026-09-30T16:50:53Z | 1 |
| Q072 | WebFetch | https://www.transit.land/onestop-id/f-9q9-bart | 2026-09-30T16:50:53Z | 1 |
| Q073 | WebFetch | https://batch.openaddresses.io/data | 2026-09-30T16:51:06Z | 0 |
| Q074 | WebFetch | https://www.surveillancewatch.io/ | 2026-09-30T16:51:06Z | 0 |
| Q075 | WebFetch | https://batch.openaddresses.io/api/data?source=us/ca/san_francisco | 2026-09-30T16:51:06Z | 1 |
| Q076 | WebFetch | https://openaddresses.io/ | 2026-09-30T16:51:06Z | 1 |
| Q077 | WebFetch | https://batch.openaddresses.io/api/job/920578 | 2026-09-30T16:51:22Z | 1 |
| Q078 | WebFetch | https://www.w3.org/TR/vocab-dcat-3/ | 2026-09-30T16:51:30Z | 1 |
| Q079 | WebFetch | https://developers.google.com/search/docs/appearance/structured-data/dataset | 2026-09-30T16:51:30Z | 1 |
| Q080 | WebFetch | https://datapackage.org/standard/data-package/ | 2026-09-30T16:51:30Z | 1 |
| Q081 | WebFetch | https://www.w3.org/TR/tabular-data-primer/ | 2026-09-30T16:51:30Z | 1 |
| Q082 | WebFetch | https://www.w3.org/TR/prov-o/ | 2026-09-30T16:51:30Z | 1 |
| Q083 | WebFetch | https://datapackage.org/standard/data-resource/ | 2026-09-30T16:51:53Z | 1 |
| Q084 | WebFetch | https://docs.sigstore.dev/cosign/signing/signing_with_blobs/ | 2026-09-30T16:51:53Z | 1 |
| Q085 | WebFetch | https://jedisct1.github.io/minisign/ | 2026-09-30T16:51:53Z | 1 |
| Q086 | WebFetch | https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/ | 2026-09-30T16:51:53Z | 1 |
| Q087 | WebSearch | Zenodo concept DOI version DOI "all versions" help new version record | 2026-09-30T16:51:53Z | 1 |
| Q088 | WebFetch | https://schema.org/Dataset | 2026-09-30T16:51:53Z | 1 |
| Q089 | WebFetch | https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning | 2026-09-30T16:52:14Z | 1 |
| Q090 | WebFetch | https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content | 2026-09-30T16:52:14Z | 1 |
| Q091 | WebFetch | https://cloud.google.com/storage/docs/requester-pays | 2026-09-30T16:52:25Z | 0 |
| Q092 | WebFetch | https://aws.amazon.com/opendata/open-data-sponsorship-program/ | 2026-09-30T16:52:25Z | 1 |
| Q093 | WebFetch | https://source.coop/ | 2026-09-30T16:52:25Z | 1 |
| Q094 | WebFetch | https://docs.cloud.google.com/storage/docs/requester-pays | 2026-09-30T16:52:46Z | 1 |
| Q095 | WebSearch | OpenSanctions licence criticism non-commercial "CC BY-NC" open data community debate | 2026-09-30T16:52:46Z | 0 |
| Q096 | WebFetch | https://www.opensanctions.org/faq/37/terms | 2026-09-30T16:52:46Z | 0 |
| Q097 | WebFetch | https://docs.overturemaps.org/attribution/ | 2026-09-30T16:52:58Z | 1 |
| Q098 | WebFetch | https://docs.overturemaps.org/release/latest/ | 2026-09-30T16:52:58Z | 0 |
| Q099 | WebFetch | https://dumps.wikimedia.org/backup-index.html | 2026-09-30T16:52:58Z | 1 |
| Q100 | WebSearch | Overture Maps release notes changelog "sources" property record_id dataset schema docs.overturemaps.org | 2026-09-30T16:52:58Z | 3 |
| Q101 | WebFetch | https://docs.overturemaps.org/release-notes/ | 2026-09-30T16:53:17Z | 0 |
| Q102 | WebFetch | https://docs.overturemaps.org/blog/2024-07-22.0/ | 2026-09-30T16:53:17Z | 1 |
| Q103 | WebFetch | https://docs.overturemaps.org/blog/2026/05/20/release-notes/ | 2026-09-30T16:53:17Z | 1 |
| Q104 | WebFetch | https://docs.overturemaps.org/gers/changelog/ | 2026-09-30T16:53:17Z | 1 |
| Q105 | WebFetch | https://www.opensanctions.org/reference/ | 2026-09-30T16:53:35Z | 1 |
| Q106 | WebFetch | https://www.openstreetmap.org/api/0.6/changeset/1 | 2026-09-30T16:53:35Z | 1 |
| Q107 | WebFetch | https://planet.openstreetmap.org/replication/minute/state.txt | 2026-09-30T16:53:35Z | 0 |
| Q108 | WebFetch | https://osm-planet-eu-central-1.s3.dualstack.eu-central-1.amazonaws.com/planet/replication/minute/state.txt | 2026-09-30T16:53:54Z | 1 |
| Q109 | WebSearch | OpenStreetMap planet files hosted AWS open data sponsorship S3 osm-planet mirror bandwidth | 2026-09-30T16:53:54Z | 1 |
| Q110 | WebFetch | https://registry.opendata.aws/osm/ | 2026-09-30T16:53:54Z | 1 |
| Q111 | WebSearch | OpenStreetMap redaction API hidden versions history dumps licence violation Data Working Group | 2026-09-30T16:54:11Z | 1 |
| Q112 | WebSearch | Open Data Portal Watch metadata quality CKAN portals outdated metadata study | 2026-09-30T16:54:11Z | 1 |
| Q113 | WebFetch | https://csrc.nist.gov/news/2022/nist-transitioning-away-from-sha-1-for-all-apps | 2026-09-30T16:54:11Z | 1 |
| Q114 | WebFetch | https://osmfoundation.org/wiki/Data_Working_Group | 2026-09-30T16:54:22Z | 1 |
| Q115 | WebFetch | https://research.wu.ac.at/en/publications/automated-quality-assessment-of-metadata-across-open-data-portals-3/ | 2026-09-30T16:54:22Z | 1 |
| Q116 | WebFetch | https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds | 2026-09-30T16:54:36Z | 1 |
| Q117 | WebFetch | https://datacite-metadata-schema.readthedocs.io/en/4.5/appendices/appendix-1/relationType/ | 2026-09-30T16:54:36Z | 1 |
| Q118 | WebSearch | "Atlas of Surveillance" data accuracy criticism outdated entries limitations researchers | 2026-09-30T16:54:36Z | 0 |

<!-- link definitions: WebFetch rows only; WebSearch ids render as plain text (a search is not a source) -->
[Q001]: https://surveillancegraph.org/
[Q002]: https://surveillancegraph.org/data-freshness/
[Q003]: https://surveillancegraph.org/evidence/
[Q004]: https://surveillancegraph.org/methodology/
[Q005]: https://surveillancegraph.org/dossier/
[Q006]: https://surveillancegraph.org/downloads/
[Q007]: https://surveillancegraph.org/dossier/az/
[Q008]: https://surveillancegraph.org/manifest.json
[Q009]: https://www.opensanctions.org/datasets/us_ofac_sdn/
[Q010]: https://www.opensanctions.org/datasets/us_ofac_sdn/issues/
[Q011]: https://www.opensanctions.org/docs/bulk/
[Q012]: https://www.opensanctions.org/licensing/
[Q013]: https://www.opensanctions.org/datasets/us_ofac_sdn/
[Q014]: https://www.opensanctions.org/docs/statements/
[Q015]: https://data.opensanctions.org/datasets/latest/us_ofac_sdn/index.json
[Q016]: https://www.opensanctions.org/docs/bulk/delta/
[Q017]: https://www.opensanctions.org/datasets/us_ofac_sdn/statistics/
[Q019]: https://www.opensanctions.org/changelog/
[Q020]: https://www.opensanctions.org/issues/
[Q021]: https://www.opensanctions.org/issues/ua_war_sanctions
[Q022]: https://www.opensanctions.org/entities/Q7747/
[Q023]: https://www.openstreetmap.org/copyright
[Q024]: https://wiki.openstreetmap.org/wiki/Planet.osm/diffs
[Q025]: https://planet.openstreetmap.org/
[Q026]: https://wiki.openstreetmap.org/wiki/Changeset
[Q027]: https://osmfoundation.org/wiki/Licence/Community_Guidelines/Collective_Database_Guideline_Guideline
[Q028]: https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
[Q029]: https://www.wikidata.org/wiki/Help:Sources
[Q030]: https://www.wikidata.org/wiki/Wikidata:Database_download
[Q032]: https://researchportal.hw.ac.uk/en/publications/rqss-referencing-quality-scoring-system-for-wikidata/
[Q033]: https://meta.wikimedia.org/wiki/Grants:Project/Finding_References_and_Sources_for_Wikidata
[Q034]: https://ourworldindata.org/grapher/life-expectancy
[Q035]: https://docs.owid.io/projects/etl/api/chart-api/
[Q036]: https://docs.owid.io/projects/etl/architecture/
[Q037]: https://ourworldindata.org/faqs
[Q038]: https://docs.owid.io/projects/etl/architecture/metadata/reference/
[Q039]: https://www.propublica.org/datastore/
[Q040]: https://projects.propublica.org/datastore/
[Q041]: https://opencorporates.com/info/our-data
[Q043]: https://api.opencorporates.com/documentation/API-Reference
[Q044]: https://atlasofsurveillance.org/
[Q045]: https://atlasofsurveillance.org/methodology
[Q046]: https://atlasofsurveillance.org/data-library
[Q047]: https://deflock.me/
[Q049]: https://deflock.org/
[Q050]: https://wiki.openstreetmap.org/wiki/Deflock
[Q051]: https://community.openstreetmap.org/t/unverified-flock-cameras-causing-mass-panic/146534
[Q052]: https://san.com/cc/flock-threatens-website-hosting-license-plate-data-accidentally-leaked-by-cops/
[Q053]: https://github.com/FoggedLens/deflock
[Q054]: https://www.muckrock.com/foi/list/
[Q055]: https://www.documentcloud.org/help/faq/
[Q056]: https://help.muckrock.com/Frequently-Asked-Questions-19ef889269638193975edda45199e14e
[Q058]: https://next.www.documentcloud.org/help/faq
[Q059]: https://documentcloud.readthedocs.io/en/latest/documents.html
[Q060]: https://catalog.data.gov/dataset/?q=license+plate+reader
[Q061]: https://data.gov/dataset/electric-vehicle-population-data
[Q062]: https://resources.data.gov/resources/dcat-us/
[Q063]: https://catalog.data.gov/dataset/electric-vehicle-population-data
[Q065]: https://resources.data.gov/resources/dcat-us3/
[Q066]: https://pdap.io/
[Q067]: https://www.transit.land/documentation/concepts/feed-versions
[Q070]: https://www.transit.land/documentation/concepts/static-gtfs-feed-versions
[Q071]: https://www.transit.land/documentation/concepts/source-feeds/
[Q072]: https://www.transit.land/onestop-id/f-9q9-bart
[Q073]: https://batch.openaddresses.io/data
[Q074]: https://www.surveillancewatch.io/
[Q075]: https://batch.openaddresses.io/api/data?source=us/ca/san_francisco
[Q076]: https://openaddresses.io/
[Q077]: https://batch.openaddresses.io/api/job/920578
[Q078]: https://www.w3.org/TR/vocab-dcat-3/
[Q079]: https://developers.google.com/search/docs/appearance/structured-data/dataset
[Q080]: https://datapackage.org/standard/data-package/
[Q081]: https://www.w3.org/TR/tabular-data-primer/
[Q082]: https://www.w3.org/TR/prov-o/
[Q083]: https://datapackage.org/standard/data-resource/
[Q084]: https://docs.sigstore.dev/cosign/signing/signing_with_blobs/
[Q085]: https://jedisct1.github.io/minisign/
[Q086]: https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/
[Q088]: https://schema.org/Dataset
[Q089]: https://support.zenodo.org/help/en-gb/1-upload-deposit/97-what-is-doi-versioning
[Q090]: https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content
[Q091]: https://cloud.google.com/storage/docs/requester-pays
[Q092]: https://aws.amazon.com/opendata/open-data-sponsorship-program/
[Q093]: https://source.coop/
[Q094]: https://docs.cloud.google.com/storage/docs/requester-pays
[Q096]: https://www.opensanctions.org/faq/37/terms
[Q097]: https://docs.overturemaps.org/attribution/
[Q098]: https://docs.overturemaps.org/release/latest/
[Q099]: https://dumps.wikimedia.org/backup-index.html
[Q101]: https://docs.overturemaps.org/release-notes/
[Q102]: https://docs.overturemaps.org/blog/2024-07-22.0/
[Q103]: https://docs.overturemaps.org/blog/2026/05/20/release-notes/
[Q104]: https://docs.overturemaps.org/gers/changelog/
[Q105]: https://www.opensanctions.org/reference/
[Q106]: https://www.openstreetmap.org/api/0.6/changeset/1
[Q107]: https://planet.openstreetmap.org/replication/minute/state.txt
[Q108]: https://osm-planet-eu-central-1.s3.dualstack.eu-central-1.amazonaws.com/planet/replication/minute/state.txt
[Q110]: https://registry.opendata.aws/osm/
[Q113]: https://csrc.nist.gov/news/2022/nist-transitioning-away-from-sha-1-for-all-apps
[Q114]: https://osmfoundation.org/wiki/Data_Working_Group
[Q115]: https://research.wu.ac.at/en/publications/automated-quality-assessment-of-metadata-across-open-data-portals-3/
[Q116]: https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds
[Q117]: https://datacite-metadata-schema.readthedocs.io/en/4.5/appendices/appendix-1/relationType/
