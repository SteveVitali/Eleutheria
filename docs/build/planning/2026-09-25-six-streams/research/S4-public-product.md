# S4 — Public discovery, reproducible records, and accountable contribution

Date: 2026-09-25. **Status: proposed design, not implementation or publication approval.** Research baseline: `0e57e6461d6a5db2e8e0042464750ce2ea65db5e` in the isolated planning worktree. The active Claude checkout was not changed. This report owns product design; S1 owns evidence/publication correctness, S2 the dossier portfolio, S3 evaluation, S5 acquisition priorities, and S6 current-state documentation. Candidate requirement names below are planning identifiers, not newly minted canonical `SIG-*` IDs.

## 1. Recommendation and scope

Build a useful investigation workflow on the **existing Astro content core and three React islands**. The first product increment should let someone find any published record, open that particular record, trace an assertion to an admissible capture, cite an actual immutable release, and deliver a correction to a responsible reviewer. A general SPA, accounts, collaboration, AI chat, arbitrary uploads, and a new basemap are not prerequisites and are out of this proposal.

The priority order is: (1) align public promises with functioning citation/intake mechanisms; (2) complete full-corpus discovery and specific record navigation; (3) improve comprehension and the map/list/network/evidence journey; (4) measure usefulness with the deeply researched S2 dossiers. A visually polished empty dossier or a beautiful graph without valid edges is not acceptance.

**Do not duplicate P31 work.** P31.14 owns presentation analytics producers; P31.15 owns compartment-separated z0–z14 tiles, compression and retirement of the combined point payload; P31.16 owns the Round-9 re-materialization/re-export and gated public cutover. Its operator-approved **no-basemap** choice remains in force. Rebase and re-audit after those tickets land. S4 adds discovery, records, durable released views, real intake, and comprehensible presentation; it consumes their outputs. A later Phase/Round-10 implementation should be scheduled from the actual settled chain tip, not from this research snapshot.

## 2. Revalidated findings and limits

Evidence classes: **C** = inspected code; **L** = live unauthenticated HTTP read; **H** = committed record of earlier execution; **I** = inference. No tests, builds, DB queries, cloud commands, authenticated reads, or submissions were run in this research. Live observations below were repeated at **2026-09-25T18:28:57Z** with ordinary GETs; publication may subsequently change.

| Finding | Evidence and scope | Design consequence |
|---|---|---|
| Public islands already exist | C: `docs/adr/ADR-097-public-progressive-enhancement-islands-map-graph-search.md:27–56`, `web/astro.config.mjs`, `web/src/pages/search.astro:58`. L: search/map HTML contain two script elements; homepage and NY dossier contain none. Root/web AGENTS prose describes the older curate-only exception. | Preserve the architecture; update operational documentation under S6. New routes/islands require an explicit ADR; do not silently declare every public page interactive. |
| Public search does not cover the corpus | C: `web/src/pages/search.astro:21–43`, `web/src/lib/data.ts:468–485`; site result href is `/map/`, source result href `/data-freshness/`. L: [search](https://surveillancegraph.org/search/) says **500 of 230,330 sites** (0.217%); hydrated index in first pass had 733 items = 55 dossiers + 178 sources + 500 sites. `SearchIsland.tsx:86` further displays only 100 results per group, with no paging. | Index every admissible published record; render bounded pages with a continuation; return a specific record href. A displayed cap is honest but is not complete discovery. |
| Map fallback is incomplete and unexpectedly large | C: `web/src/pages/map.astro:50–54,247–275` caps located assets, but `:289–314` enumerates all unlocated asset IDs. L: [map](https://surveillancegraph.org/map/) says **500 of 225,105 located assets**; HTML is **2,779,841 bytes**, before scripts/tiles. I: unbounded no-point rows are a likely contributor; not profiled. | Page both located and unlocated records. Every published no-point record must remain discoverable. Apply budgets to real export builds, not only small fixtures. |
| Citation query selectors are not interpreted by the public static serving path | C: `web/src/lib/citation.ts:33–40` only appends query parameters; `web/src/components/Citation.astro:34` promises reproducibility. L: [NY dossier](https://surveillancegraph.org/dossier/ny/) and the same path with `?as_of_world=2000-01-01&as_of_belief=2000-01-01&ruleset=not-a-ruleset` both returned 200, **11,111 bytes**, SHA-256 **`c5fa3bc14d7ec7b5340ddf788bc4c7035a862af08fc84beb2b8c4395936ee11e`**, displaying September 24. | A query string is not a historical implementation. Pin actual release content; legacy requests must resolve exactly or honestly report that no such released view exists. This does not establish that every API temporal route is broken; S1 audits those separately. |
| Published correction intake is not deliverable | L: [dispute](https://surveillancegraph.org/dispute/) has no form or contact link; its “Submit” section only links to the corrections log. C: `web/src/pages/dispute.astro:59–65`. `policy/src/policy/corrections_intake.py:120–123` holds submissions/dispositions in Python lists; `:159` appends in memory. `policy/cli.py` prints a reference, not a durable inbox. | Build a restricted durable receiver and reviewer handoff. Do not describe the existing policy model as hosted intake. Correct the public copy before claiming operational delivery. |
| Gap task creation is only a descriptor | C: `web/src/pages/task/new/[slug].astro:19–26` prebuilds routes; `:39–55` says “enters the queue” without a submitting operation. The detector-created hosted queue is separate. | Label a prepared task/request as prepared. Count “submitted” only after a durable accepted receipt; account for idempotent repeats separately. |
| Dossier completeness language is not supported by its fields | L: NY shows 585 observations/three registry source IDs, many blank sections and unknown governance/cost fields, but “1 unresearched field.” C: `exports/src/exports/spine_export.py:1091–1157` fills three sections, starts with one sharing gap, and assigns unknown action blocks. L first pass: map had 166,142 unresolved-jurisdiction records of 225,105 located records (~73.8%). | Derive gap indicators from a scoped question inventory. Distinguish an inventory page from a reviewed accountability dossier; S2 owns completion of the latter. Jurisdiction enrichment requires recorded S1/S2 rules, never a cosmetic label guess. |
| Live site is behind hosted engineering intentionally | L: [network](https://surveillancegraph.org/network/) and [watch](https://surveillancegraph.org/watch/) empty in first pass; homepage has **121 stat cards**, 81,020 HTML bytes, including raw predicate names. H: P31.6 records 130 edges/200 vendor links; P31.16 intentionally owns republish. | Do not open replacement tickets for data awaiting the already-scheduled release. After republish, test user questions rather than equating non-empty pages with success. |
| Existing API search is not an adequate drop-in released search | C: `api/src/api/store_pg.py:177–204` searches `entity_identifier.value ILIKE`, then fetches labels/sources; `api/src/api/routes.py:237–288` accepts an as-of context but calls `store.search(term, limit, after)` without it. `models.py:259–273` documents sparse pages after public visibility filtering. | Do not wire the browser to this endpoint while presenting it as the same frozen publication. Add an explicit released-data read contract; S1 owns repairs to live temporal/publication semantics. |
| “Independent sources” currently counts distinct source IDs | C: `web/src/lib/data.ts:530–543` makes a Set of artifact source strings. I: distinct registry IDs do not by themselves prove evidentiary independence. | Until source-lineage independence exists, label this “source collections,” not “independent sources.” S1/S5 supply lineage; S3 supplies reviewed calibration. |

The first-pass map screenshot did not conclusively establish WebGL rendering in the in-app browser; it is **not** used here as proof of a production renderer failure. The committed P30.3 report contains earlier render evidence. Future verification must distinguish actual drawn features from a hydrated empty canvas.

## 3. Primary research and what transfers

These are design references, not SIG source-ingestion or licence clearances. Inspected 2026-09-25.

| Primary source | Relevant observed pattern | Adopt / avoid |
|---|---|---|
| [Aleph dataset discovery](https://docs.aleph.occrp.org/users/search/datasets/) | Dataset listings expose description, recency, geography and types; overview counts lead to corresponding results. | Make coverage/source cards actionable filters. Avoid copying Aleph's person-centric models: SIG remains institutional/infrastructure-focused. |
| [Aleph investigation workspaces](https://docs.aleph.occrp.org/users/investigations/overview/) and [Aleph overview](https://docs.aleph.occrp.org/) | Documents, entities, diagrams and timelines form a connected investigation workflow. | Borrow navigation between evidence and relationships, not its private uploads/account/collaboration scope. |
| [OpenSanctions API guide](https://www.opensanctions.org/docs/api/) and [API reference](https://api.opensanctions.org/docs) | Distinct search, entity, adjacent-entity, and statement-level provenance surfaces. The API explains that search relevance is different from entity-match quality. | Keep relevance separate from confidence/support; link results to entity facts and statements. Dataset scoping inspires explicit source collections. SIG does not inherit OpenSanctions' data licence or personal-data scope. |
| [W3C Data on the Web Best Practices](https://www.w3.org/TR/dwbp/) | Separate identifiers for versions and a changing series; publish provenance, coverage, feedback routes and meaningful subsets. | Use content-addressed released views, complete bounded subsets and real feedback delivery. |
| [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [focus not obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum), [target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) | Keyboard and non-drag operation, understandable status, reflow and visible focus remain necessary in multi-pane interfaces. | Enforce AA plus manual assistive-technology tasks. An axe pass alone cannot establish usability or complete WCAG conformance. |
| [SQLite FTS5](https://www.sqlite.org/fts5.html), [read-only/immutable URI semantics](https://www.sqlite.org/uri.html) | An embedded full-text index can be read without a separate search cluster; immutable mode assumes the file really never changes. | Candidate release-scoped index in existing Python packages. Never open a changing network-mounted file using `immutable=1`. Benchmark before accepting the serving design. |

## 4. Proposed product decisions and upstream dependencies

**S4-D1 — One public record, multiple representations.** Define a versioned `PublishedRecord` projection once in `exports`, after publication decisions. Astro pages, search indexes, tiles, API released views and citation metadata consume that projection. There is no browser re-resolution, silent interpolation from fixtures, or fetch from a newer live entity to fill a released view.

**S4-D2 — Released and current data are explicitly different.** The reader starts at the latest approved release, whose full UTC cuts, input identity and renderer version are visible. Every opened record and query resolves to that release. Switching releases resets incompatible cursors and clearly names the change. Experimental live reads stay outside the default public journey until S1 verifies their as-of and publication behavior.

**S4-D3 — Keep the existing routes as the workspace.** `/search/` is the primary list; `/map/` and `/network/` are alternative views retaining query, release and selected record. A common React package *inside `web/`* supplies selection/filter state for these three pages. Entity/evidence/dossier pages remain no-JS HTML. No fourth island or global SPA router is required. URL back/forward behavior, plain links and progressive enhancement are acceptance requirements.

**S4-D4 — Anonymous reporting is a narrowly scoped public receiver, not public curation.** A separate `create_intake_app` process in `api/` accepts quarantined reports only. It cannot write claims, perform dispositions, fetch arbitrary URLs, access restricted evidence, mint curator tokens, or mount `/v1/curation/*`. The existing public read app remains read-only; the existing curator process remains loopback/auth gated. This public write surface needs a new ADR/Part-VIII threat review; ADR-100's inaccurate “already built” premise is corrected by an append-only follow-up, not rewriting it.

**S4-D5 — No new basemap or mixed-licence download.** Use P31.15's plain background and per-compartment archives. The UI may place independently attributed source collections next to each other only within the approved produced-work policy. Export files, SQLite indexes, result JSON, record JSON and downloadable investigation bundles remain per compartment. A multi-compartment HTML view is an explicit publication-policy decision reviewed by S1; no raw merged JSON is introduced as a convenience.

**Dependencies / stop conditions:**

- **S1:** complete publication projection, `publication_review_required` handling, rights/tier treatment, evidence byte/locator fidelity, historical metadata and suppression all block declaring S4 release representations correct. Indexed text, snippets, titles, facets and counts require the same gate as body values. A source ID or unreviewed organisation name can leak through search even if the detail page is hidden.
- **S2:** reviewed dossier scope, question inventory, legitimate deadlines, technology vocabulary and readable jurisdiction names. S4 never promises that coordinate inventory coverage is a research-complete dossier.
- **S3:** human-reviewed calibration is required before removing the PROVISIONAL resolved-site disclosure; relevance ranking is never substituted for matching confidence.
- **S5:** source lineage, evidence-family grouping, upstream licence restrictions and approved new acquisition. No new source is ingested by S4.
- **P31.14–16:** consume their landed analytics/tiles/release rather than forking producers. Implementation starts with a recorded diff against their final contracts.
- **Operator:** approval of the receiver's public exposure, staffing/SLA ownership, quarantine retention/logging choices and any hosting cost; HG-11 approval before new public assertions/flows go live. Planning can complete while these are pending, but hosted delivery cannot be marked DONE.

## 5. Three end-to-end journeys and information architecture

### Journey A — Find what is documented in a place

Reader enters a municipality, agency, identifier, or technology. Results cover all published collection records in the selected release. Filters distinguish jurisdiction, source collection, technology and record kind; “unknown jurisdiction” is selectable rather than hidden. Each result has a human label (or honestly “Unnamed site · identifier”), type, place if evidenced, record date, source, and evidence availability. Opening it provides claims and the supporting capture—not the generic map. “Show on map” selects that record if a public point exists; otherwise the list states why there is no point. A dossier link goes to the corresponding reviewed scope or labels it as a collection overview.

Success task: an unfamiliar reader finds a named record beyond the old first-500 slice and reaches its supporting source in under two minutes without staff assistance; a keyboard-only reader completes the same task. “No match in this released collection” never becomes “no surveillance exists.”

### Journey B — Explain a relationship or upcoming decision

From an agency, choose “Connections”; show its one-hop neighborhood and equivalent edge list with configured access, observed use and declared policy kept separate. Open an edge to see the establishing claims and dates. “Expand this organisation” is explicit; no global hairball or automatic unlimited graph fetch. A dossier's decision card links to a sourced contract/authorization date, notice-window calculation and evidence; the watch supplies a calendar/RSS entry only if the date is evidenced. These fields depend on S2/P31 and may remain clearly unavailable.

Success task: a reader distinguishes “allowed/configured” from “used” and cites the correct edge evidence. The interface must not invite the interpretation that graph reachability establishes actual data access.

### Journey C — Cite, question, and correct a record

“Cite” opens a no-JS release-specific permalink plus source capture ID/digest and a plain-text citation. “Report a problem” carries the public record/release reference into the intake form. The reporter chooses an existing policy category, supplies bounded text, optionally supplies public evidence references, previews what will be submitted, and receives a durable receipt. The confirmation distinguishes received, awaiting review, decided, and published. A reviewer sees the report in a restricted queue after restarting the service, then uses the existing controlled disposition path; public correction notices contain redacted reasons and supersession links. No automatic factual correction or takedown follows a report.

Success task: a no-account/no-JS report survives restart, appears in the staffed queue, can receive a reasoned disposition, and leads to a public correction *only after* required review/publication. A copied pre-correction citation continues showing its released value unless the record is legitimately withdrawn, in which case it returns a truthful tombstone rather than replacement content.

### Navigation and text wireframes

Primary navigation: **Explore · Dossiers · Decisions · About**. Explore links to the three existing views and the source/evidence catalog. Methodology, coverage, freshness, corrections and contribution details move under About; visual-language/spec references are secondary documentation. Keep a visible global “Report a problem” link. This revisits ADR-093 and requires a new ADR, not silent historical editing.

```text
HOME                                  Published 24 Sep 2026  [Release details]
What is documented about surveillance where you live?
[Place, agency, technology, or identifier________________] [Find records]
[Browse places] [Browse technologies] [Read a local dossier]

Selected research dossiers (review status + as-of, 3–5 evidence-backed examples)
Recorded infrastructure | Source collections | Most recent release
Each figure has one short denominator. [Coverage and limitations]
What changed in this release?   [Changes] [How evidence becomes a claim]
```

```text
EXPLORE   Query: Seattle   Release: R   [List] [Map] [Connections]
Filters: Place / Technology / Record type / Source collection / Missing location
Results shown 1–50 · scope and any duplicate-collection caveat · [Next]
--------------------------------------------------------------
Result list (left)                 Selected record (right)
Label · type · evidenced place     Name / type / dates / scope
Source · evidence availability     Fact / value / status / [Evidence]
...                               [Open full record] [Cite] [Report]
--------------------------------------------------------------
Map loads only on map view; default plain background, attribution per source.
On small screens: list and record are successive pages, not compressed panes.
```

```text
RECORD                              Released view R · [Latest available view]
What this record describes / unresolved identity / publication status
Facts                  Value       Supported / disputed / unknown   Evidence
Relationships (typed) / timeline / observed vs inferred / known gaps
Evidence: original publisher, capture date, locator, review and access status
[Print] [Cite release] [Download this collection's JSON] [Report a problem]
No generic site-wide provenance box standing in for record provenance.
```

The map/list/graph view state is shared, but the no-JS reader always has complete paginated lists and record/evidence links. Do not fake a working control: hide unavailable filters with a short explanation, or disable with an accessible reason; never display a decorative layer “control.”

## 6. Released identity, URLs and historical behavior

### Publication identity

Existing `exports/manifest.py:49–108` derives a data-release ID from four inputs, including date-level cuts. **Do not claim those four strings alone uniquely prove the emitted bytes.** S1 audits their temporal sufficiency. Use two explicit hash layers, because rendered records and citations embed their publication namespace: hashing those final bytes to obtain the very ID embedded in them would create an uncomputable hash cycle.

First compute `publication_id` from a canonical **pre-render publication descriptor**: digest roots of admitted, ID-free record/evidence projections (with stable record keys but no publication URLs), the data release ID, UTC cut metadata, policy snapshot identity, projection schema, renderer/code/assets/config identity, and every other input that intentionally affects rendering. Then render the artifacts with that ID. Compute a separate `manifest_sha256` over a canonical integrity manifest containing the publication descriptor digest and final artifact path/size/media-type/SHA-256 entries. The integrity manifest excludes its own digest/signature and is not embedded back into any artifact it hashes; the external catalog and final activation record carry it. Retain the existing `release_id` for compatibility. Both hashes use full SHA-256 values. This pins actual bytes without requiring a cryptographic fixed point.

Recommended path token: `p-<64 lowercase hex SHA-256>`. Example values below use `<publication_id>` placeholders, never fabricated production IDs. Once an ID is activated, exactly one final integrity manifest is accepted for that ID. Different bytes for the same pre-render descriptor are a reproducibility failure: refuse activation/overwrite, investigate the missing input or nondeterminism, and produce a new descriptor/ID if interpretation or rendering intentionally changes. Do not “fix” nondeterminism by choosing an arbitrary timestamp. Store execution timestamps in the separate activation receipt unless a fixed, declared publication timestamp is a deliberate descriptor/render input.

### Route contract

| Route | Representation / behavior |
|---|---|
| `/releases/` | Static human index of approved publications, cut times, change summaries and availability. |
| `/releases/<publication_id>/` | Static release landing, exact manifest identity and per-compartment download links. |
| `/r/<publication_id>/c/<compartment>/entity/<type>/<uuid>/` | Complete no-JS record page for this released collection. Cite this URL. |
| `/r/<publication_id>/c/<compartment>/entity/<type>/<uuid>.json` | Same record projection, only that compartment, with schema identifier. |
| `/r/<publication_id>/c/<compartment>/evidence/<artifact_id>/<capture_id>/` | Capture-specific evidence representation. No substitution of a newer capture or original-source live bytes. |
| `/r/<publication_id>/c/<compartment>/browse/<kind>/<page>/` | Complete static record listings, 50 records per page; stable order `(label_sort_key, type, id)`. Separate no-point records are included, not dumped unbounded. |
| `/r/<publication_id>/c/<compartment>/jurisdiction/<jurisdiction_id>/<page>/` | Finite prebuilt jurisdiction browse pages. All combinations of facets are not pre-generated. |
| `/r/<publication_id>/dossier/<scope_id>/` | Released dossier/collection overview; links into evidence/record compartments with their attributions. |
| `/entity/<type>/<uuid>/` | Latest identity landing, or a short-lived redirect to its latest available released representation; if multiple compartments exist, list them rather than silently merge. |
| `/search/?release=<publication_id>&q=...` | Existing search island; full-corpus no-JS form submits to the read service below. The page clearly distinguishes latest alias from pinned release. |
| `/map/?release=...&focus=<record_key>`; `/network/?release=...&focus=<record_key>` | Existing islands, same selected record. Canonical evidence citation is the immutable entity/edge page, not an unversioned viewport URL. |
| `/v1/releases/<publication_id>/compartments/<compartment>/search` | New additive released search contract, JSON or complete no-JS HTML via content negotiation. Existing `/v1/search` semantics are not changed by stealth. |

The reverse proxy maps a same-origin, explicitly named read-only search-results path to the API HTML representation for the no-JS GET form. This is a **bounded dynamic search exception**, documented in a new ADR: the record/evidence/browse archive remains static and usable if search compute is unavailable. The rendered search page uses the same record projection, filter schema and design tokens, with parity tests; it does not become a second resolver. Arbitrary query results are not promised as prebuilt static artifacts.

**Legacy citation requests:** recognise `as_of_world`, `as_of_belief`, and `ruleset` at the serving boundary, normalize them according to a documented legacy rule, and consult an explicit compatibility index built from actual preserved releases. Unique exact match → 302/303 to immutable released URL. No match → 404 with “This requested historical view is not available” and an optional link to choose releases. Multiple matches because the old tuple omitted resolver/publication details → 409 with a choice; do not guess. A historical request must never silently show latest. Invalid syntax → 400. The static object host cannot implement this on its own; the resolver path/proxy is part of the release-serving ticket.

**Old releases:** freeze bytes actually preserved, with original capture/build metadata when demonstrable; label reconstructed historical views as reconstructions and give them a new publication identity. Do not pretend today's data is yesterday's archive. Historical source/rights/sensitivity corrections and the serving overlay belong to S1.

**Suppression overrides availability, not history.** Immutable identity means bytes are never replaced under the same ID; it does not promise that harmful content can never be withdrawn. The public serving layer consults a content-free withdrawal registry, disables affected old/current HTML, JSON, search, tile and download paths, and returns 410 with a safe reason/category/date. Old original bytes remain restricted or are deleted only by the existing authorised process. Purge operator-controlled caches; do not promise recall of third-party copies. Body-bearing public records use revalidation/short TTL (proposed 5 minutes) until the suppression design is proven; only non-sensitive code/CSS assets use year-long immutable caching. Counts/search indexes/archives referencing the withdrawn object need replacement releases or withdrawal of the affected artifact. S1 must prove this whole-artifact blast radius is workable before rollout.

## 7. Data and query contracts

All examples are proposed schema shapes. Canonical schemas should be generated/validated through the existing ownership pattern; do not hand-edit ontology-generated artifacts. A UI projection schema may be hand-authored in its established non-ontology contract location, but a new stored ontological class requires ontology source changes and generation.

### Release catalog and PublishedRecord

```json
{
  "schema": "sig.publication/1",
  "publication_id": "<publication_id>",
  "data_release_id": "<existing-release-id>",
  "manifest_sha256": "<sha256>",
  "as_of_world": "<UTC instant or explicitly date-precision cut>",
  "as_of_belief": "<UTC instant>",
  "ruleset_version": "<version>",
  "resolver_version": "<version>",
  "projection_version": "sig.published-record/1",
  "renderer_version": "<git/version identifier>",
  "compartments": [{"id": "osm_physical", "license": "ODbL-1.0", "manifest_href": "<href>"}],
  "availability": "available"
}
```

This is an external catalog record, not an artifact hashed by its own integrity manifest. `availability` is mutable and outside both immutable hash inputs. A record's mandatory fields are:

```json
{
  "schema": "sig.published-record/1",
  "publication_id": "<publication_id>",
  "record_key": "<compartment>:<type>:<uuid>",
  "entity_id": "<uuid>", "entity_type": "physical_asset",
  "compartment": "osm_physical", "license": "ODbL-1.0",
  "label": {"text": "<evidenced label or unnamed-record label>", "basis": "claim", "claim_ids": ["<id>"]},
  "jurisdiction": {"id": "<qualified-id-or-null>", "label": "<label-or-null>", "basis": "asserted", "claim_ids": ["<id>"]},
  "location": {"kind": "point", "lat": 0.0, "lon": 0.0, "published_precision": "<policy value>"},
  "facts": [{"predicate": "camera_operator", "label": "Operator", "status": "unresolved", "candidates": [], "evidence_refs": []}],
  "relationship_refs": [],
  "source_refs": [{"source_id": "<id>", "label": "<public name>", "upstream_href": "<https-url>"}],
  "coverage": {"question_set_id": "<versioned-scope>", "answered": 0, "partial": 0, "conflicted": 0, "unknown": 0, "not_applicable": 0},
  "review": {"status": "unreviewed", "resolution_eval": "provisional"},
  "href": "<immutable-html-href>", "json_href": "<same-compartment-json-href>"
}
```

Coordinates above are schema placeholders, not sample observations. `location` is a discriminated union: `point` (only policy-reduced public coordinates), `area` (only public geometry reference), or `withheld|unreported|conflicted` with no hidden precision. No sensitive coordinate, name or field may be placed in an unused property or HTML data attribute. `jurisdiction.basis` may be `asserted|derived|unresolved`; a derived boundary join requires the boundary version and derivation claim, not a map-label inference. A facts candidate carries `value`, epistemic status, assertion/observation dates, source claim IDs and capture-specific evidence refs; unknown values are not automatically absent claims.

Evidence refs contain `claim_id`, `artifact_id`, `capture_id`, `capture_sha256`, `locator` (typed page/table/cell/text-position/etc.), `access` (`public_bytes|public_excerpt|metadata_only|withdrawn`), and immutable `href`. Missing locators are explicit `unlocated`, not a fabricated paragraph. S1 decides whether exact quote text is publishable; the UI does not copy restricted bytes into snippets. A relationship ref carries its edge kind, source/target record keys, establishing claim IDs, temporal status and evidence href. The graph and list must use the same edge IDs.

### Search endpoint

`GET /v1/releases/<publication_id>/compartments/<compartment>/search?q=&kind=&jurisdiction=&technology=&source=&location=&limit=50&cursor=`

- `q`: maximum 200 Unicode code points; ordinary words/phrases and identifier exact lookup only. No regex, arbitrary FTS grammar, SQL or wildcard language. Empty q permits filtered browse. Text query minimum 3 characters except exact canonical identifier or a selected facet. Two-letter place codes are selected from the jurisdiction facet, not rejected as textual searches without explanation.
- `kind`, `jurisdiction`, `technology`, `source`: validated canonical IDs, OR within a repeated facet and AND between facets; maximum 10 values per facet. Unsupported facets return 422 rather than silently ignored filters.
- `location`: `any|public-point|no-public-point`; exact bounding-box filtering is deferred until S1 confirms policy-reduced geography semantics. The initial workspace map highlights the selected/search-result records without pretending a viewport search exists.
- `limit`: 1–100, default 50. Sort for the first iteration is stable normalized label + type + ID; expose relevance only once pinned search-engine behavior and ranking pagination are validated. Search is lexical retrieval, not probability of truth or same-entity matching.
- Cursor: base64url of versioned publication ID, compartment, normalized filter hash, sort definition and last key. Validate all fields and lengths; reject mismatched release/filter/compartment with 409 `cursor_context_mismatch`; malformed cursors 422. No credentials in cursors; signing is optional integrity, not authorization.
- Response is one compartment only, with `publication_id`, `compartment`, `license`, normalized query, `scope.indexed_records`, `scope.eligible_records`, `scope.excluded_records_by_reason`, `results`, `next_cursor`, and `total_matches: {value: null, relation: "not_computed"}` unless a bounded exact count exists. Never represent “50 shown” as “50 total.” Source scope and totals are over public records only.
- Results use a lightweight subset of `PublishedRecord`: key, specific href, label, kind, evidenced jurisdiction, sources, matched field names and record status. Snippets are optional, bounded to permitted text and escaped; they never reveal a withheld matching term.
- Query/facets affect matching **before** pagination. No sparse pages caused by filtering withheld hits afterwards. All eligible published records must be reachable by following next cursors; a page limit is not a corpus cap.
- Unknown publication/compartment → 404; withdrawn partition → 410; bounded-query timeout → 503 + Retry-After; throttling → 429. Errors are accessible and do not silently fall back to fixture or current-spine data.

### Candidate index and deployment approach

Prefer a deterministic, **per-compartment SQLite FTS5 artifact built from PublishedRecord**, served read-only by the existing Python API package, over adding Elasticsearch or sending the whole corpus to the browser. Add a plain normalized-label/identifier table plus indexes for facets/keyset browse; pin SQLite/tokenizer settings in the artifact metadata. No claim-spine writes are needed for search. The index is another licensed artifact, not an exception to publication checks.

This is a proposed architecture decision contingent on a benchmark: **230k eligible records, 14 compartments, representative Unicode/identifier/common/rare/empty-facet queries and 8 concurrent readers**. Stage an index to verified immutable local files (not mutable gcsfuse SQLite), atomically select an approved publication, open `mode=ro` and only use `immutable=1` for digest-verified files that cannot change. Retain bounded disk cache for older publications; resource exhaustion returns a service error, never newest-release results. If this cannot meet resource/SLO limits on existing infrastructure, prefer an explicitly release-keyed PostgreSQL read projection under a new ADR; do not silently use the current entity tables or acquire a paid search service.

The all-collections HTML search representation federates independent partitions into attributed sections. JSON clients request a selected partition, or multiple separate partition responses (maximum four in flight). The UI may display a common list with source/collection attribution only after S1 approves produced-work treatment; no combined machine-readable export. BM25 scores from separate partitions are not globally comparable and are not merged into an apparent universal confidence order. The default view can show a bounded first page per collection with “More in this collection.” All counts say whether they count collection records, observations or resolved entities.

### Workspace state and consistency

Canonical query state: `release`, `q`, repeated permitted facets, `collection`, `focus=<record_key>`, and `view=list|map|network`. View switching preserves compatible state. Search/filter changes clear pagination but retain focus only if the selected record remains in the scope; otherwise announce that selection was cleared. Browser back/forward restores state. Keyboard focus moves only on explicit actions; incoming results update an aria-live summary without stealing focus.

Map viewport (`z`, `lat`, `lon`) is transient in memory by default; an explicit “Share this view” may encode the **published** viewport in the URL. No visitor geolocation, persistent localStorage research history, account, background save, or analytics identifying the subject of a query. The full record link works when JS is disabled. The selected entity's evidence drawer is optional enhanced navigation; it always includes “Open evidence page” and does not duplicate or reinterpret the capture.

A release is activated only when record/browse HTML, per-compartment JSON, search indexes, graph subsets, tiles and capture metadata all pass cross-reference/hash checks. Update the small latest pointer after uploading/validating all immutable artifacts. Keep prior publication addresses intact. A page and API response must agree on publication ID and `record_key`; a mismatch is an error with a reload-to-release choice, not a silent refresh.

## 8. Real anonymous correction intake

### Protocol and minimal state

Keep `/dispute/` as a static explanation/entry. The “Start report” link opens a same-origin dynamic `/intake/new` HTML form in the separate receiver, which issues an expiring anti-replay form token and accepts no-JS `application/x-www-form-urlencoded` POST. A single usable form is preferable to an account or multistep SPA. Do not require identity, email, scripts, CAPTCHA or a third-party provider. A “Check a receipt” page uses a POSTed bearer receipt token; never put the secret in a query string, analytics, referrer or public correction URL.

Proposed `POST /intake/v1/reports` body:

```json
{
  "form_token": "<expiring signed token>",
  "idempotency_key": "<random per-form nonce>",
  "category": "factual_error",
  "publication_id": "<publication_id-or-null>",
  "record_key": "<record_key-or-null>",
  "claim_ids": ["<maximum-10-public-ids>"],
  "description": "<plain text, 20–4000 Unicode code points>",
  "evidence_urls": ["<up-to-3-public-https-references>"],
  "contact_for_legal_demand": null
}
```

The JSON transport is optional; HTML is the baseline. The form explains that free text can disclose personal information and asks for institutional/record facts, not plates, personal movements or identifying information. This is minimization, not a claim that arbitrary submitted text contains no PII. No attachments or automatic URL retrieval in the first iteration; URL credentials, non-HTTPS/private hosts and obvious secrets are rejected with a private error. Operator inspection still treats references as untrusted. Do not promise DLP reliably detects all identifiers; every body is quarantined.

Successful response **only after durable transaction commit**: 201 JSON or 303 to a no-store receipt display, containing an opaque public receipt ID, one-time bearer status token, accepted time, category's policy response window, and “Received; not yet verified or published.” If 303 would require placing the token in a URL, render the confirmation directly instead. API retries with the same form nonce produce the same receipt and do not double-count. Failed persistence → 503, explicitly “not received”; validation failure 422 preserves escaped safe form fields. No blind optimistic success message.

Separate state:

1. **Restricted payload store:** encrypted report body/contact/URLs, access limited to intake reviewer role, never published/search-indexed/evidence-archived automatically. Keep outside the append-only claim spine and WORM evidence store because unreviewed input may need expunging. Proposed payload retention: until 30 days after final disposition, with a 90-day review/reminder ceiling; any necessary extension/legal hold is recorded by an authorized reviewer. Operator must ratify retention; no automatic new retention authority is inferred.
2. **Append-only intake events:** received, triaged, assigned, review requested, disposition proposed, disposition approved, applied, published, closed. Store receipt ID, category, actor role, times, safe reference IDs and sanitized reason—not raw body/contact/IP. Metadata itself remains restricted until its public fields are approved. Status is derived from events.
3. **Receipt capability:** random ≥128-bit secret; store only a keyed digest, compare in constant time, rate-limit failed lookups. It reveals only coarse status and an approved response, not the original report or existence of restricted entities. No public list of incoming reports.
4. **Durable reviewer queue:** receipt/events are visible through the loopback curator app after restart; polling is explicit or scheduled by the operator. A committed outbox item for a configured private notification channel can be added later, but no email/webhook containing report text, identity or tokens is sent by this plan. A dashboard queue is the required delivery target, not a speculative notification.

Use existing category IDs, priorities and hours from `policy/data/takedown.toml`: privacy/security 72h, legal/copyright 168h, factual error 336h. Clarify these are the existing **response/triage SLA**, not a promise of final resolution within that time. A monitored owner and escalation coverage must be named before launching the form; without that, the page must not advertise operational intake.

### Abuse, privacy and operator safety

- The receiver has its own narrow database role and network profile. It can INSERT reports/events into intake storage, not write claims, query sealed evidence or call the curator service. The public read API has no new POST methods; the curation app remains absent from its route table.
- Validate content type and a 16KB total body limit; cap individual fields/links/IDs; escape all output; do not render reporter HTML, Markdown images or link previews. Prohibit automatic resolution of submitted URLs (SSRF/no egress). Incoming text is untrusted data, never agent instructions.
- Basic abuse controls: form nonce with an appropriate accessible expiry/reissue path; duplicate nonce idempotency; per-source-network token bucket and global queue circuit breaker. Proposed starting rates: 5 accepted reports/hour per rotating short-lived network pseudonym, burst 3; global 100/hour then backpressure. These are tunable proposals, not empirical guarantees. Shared networks/Tor must have an escalation path; a rate-limited person sees a retry interval and safe offline preparation option, not false acceptance.
- Compute an abuse pseudonym as HMAC of normalized ingress network address with a daily rotated secret; maximum 24h TTL. Do not persist raw IPs/user-agent fingerprints/cookies to application logs. IP-derived hashes remain potentially personal data; do not call them anonymous. Review load-balancer, Cloud Run, reverse-proxy and monitoring logs too; application log hygiene alone is insufficient. Infrastructure retention/log exclusions require operator approval and proof before privacy claims.
- Validate Origin when supplied and use Fetch Metadata defensively, but allow legitimate privacy clients without those headers through signed form-token checks. No cross-origin CORS write access by default. Tokens cannot serve as authority to submit a correction directly to the spine.
- A status query is POST with token in body, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`; redact bodies/headers. Receipt pages do not contain third-party assets. Do not place the capability in a `Location` URL or automatically copy it to persistent browser storage.
- Moderation applies privacy/security priority regardless of whether the underlying factual allegation is correct. A report itself must not instantly hide a target record; coordinated mass reporting must not become a takedown vote. Escalate credible imminent exposure through the existing authorized suppression path.
- Legal-demand contact is optional at intake and retained separately/restricted; identity/standing can be requested only for the disposition that needs it. No generalized real-name collection or public auth project; D-R7.1-AUTH remains deferred.

### Applying outcomes

The public receiver never invokes `BeliefLog.correct` as production storage. That class is an in-memory policy model, not the PG sink. Reviewer decisions validate all required fields before appending a disposition, then an authorized idempotent command applies a correction through the canonical claim/evidence path with provenance and supersedes links; S1 supplies this contract. Submission, accepted correction, implemented correction and published correction are separate states. A crash between approval/apply/publication resumes by idempotency key without double assertions or claiming completion.

Suppression/deletion invoke the existing policy gates, including two-person authorization for true deletion; no generic reviewer button skips them. Public notices omit reporter text/contact and show only approved reasons and affected public IDs. A refusal has safe published reasoning, but publication must not expose a privacy report's target or sensitive details; aggregate or redacted notices are valid when necessary. Quarterly counts distinguish received reports, final dispositions and repeated events so replay/reconsideration does not inflate totals.

## 9. Honest dossier coverage and accessible presentation

Replace “N unresearched fields” with a versioned **question inventory by scope and technology**, shared with S2: What capability? Which public operator? What source/effective dates? What location precision? Which vendor/contract/funding? What access? What policy/authorization? What retention? What deadline? Which accountability events? Questions can be answered, partial, conflicted, unknown/unresearched, or not applicable. Applicability itself has a rule/evidence and never reduces the denominator silently.

Example wording: “3 of 10 applicable questions have evidenced answers; 2 have partial answers; 5 remain unknown. 2 questions do not apply.” Those categories are mutually exclusive at the question level, with partial/conflict facts visible beneath them. Publish the question-set version, denominator, source scope and review date. This is **documentation coverage**, not percentage of actual surveillance or proof of completeness. A reviewed local dossier and a machine-generated inventory overview receive distinct labels and different eligibility criteria; a jurisdiction bucket including `unresolved` cannot be marketed as a completed local investigation.

Homepage: at most four curated metrics, readable names/numbers and short uncertainty explanations; all predicate-level diagnostics remain on coverage/research pages with pagination. Record-level provenance names that record's captures/dates; site-wide corpus metadata belongs on the release page. Unknown, unavailable, withheld, and absent after an actual search are not interchangeable. “Last fetched,” “last successful ingest,” “source says updated,” “claim observed,” and “release published” remain distinct dates.

Accessibility acceptance extends the existing AA contract: semantic headings/lists/tables, correct table captions and scoped headers; visible focus not covered by sticky panes; 24×24 CSS-pixel targets or valid spacing exceptions; single-pointer and keyboard alternatives to graph dragging; reflow at 320 CSS pixels/400% zoom; focus returns to invoking control when a drawer closes; errors summarized and linked to fields; result counts announced without repeating the entire result list. Colour is never the sole status signal. Respect reduced motion; do not auto-pan/animate while a reader inspects evidence. Use plain language in product UI; move ticket IDs, predicate IDs and ruleset mechanics into expandable technical details where useful.

## 10. Performance, reliability and measurement

These are **proposed acceptance targets to validate**, not measurements already achieved. Hold constant the P31.15 plain-basemap policy and existing no-JS content-page budget. Run production-shaped fixtures locally/CI, not expensive load tests on the live service without approval.

| Surface | Proposed acceptance budget / behavior |
|---|---|
| Static record/dossier/browse page | Existing total transfer budget ≤150KiB including shared assets; 0 script bytes; paginate long evidence/relationship lists. Search/map/network are the named exceptions, not every `/r/` route. |
| Search/list HTML | ≤150KiB compressed initial transfer excluding optional hydration; 50 rows, at most 100 by explicit setting; results visible with JS off. No 230k-row embedded index. |
| Search JSON | ≤100KiB compressed per 50-record partition page; at most four concurrent partition requests; query cancellation/debounce only after user input, no speculative tracking. |
| Query execution | On benchmark hardware matching the current small service: p95 ≤500ms warm per partition; ≤1s for common filtered searches; hard 2s per-query execution budget. Cold index staging may show explicit readiness/503 rather than block unboundedly. Final target and resource allocation require measured evidence. |
| Browser interaction | p75 target INP ≤200ms; user-meaningful result first paint ≤2.5s under a documented mobile network/CPU profile; manual responsiveness on a 4GB device. Treat these as field/lab targets, not guaranteed from one Lighthouse score. |
| Map/network | Load only on requested view; use P31.15 tile ranges; cap initial ego network at 50 nodes/100 edges and provide continued edge lists. No full-corpus GeoJSON or 17MB points fallback. JS/CSS/worker compressed-budget baseline measured before setting a hard threshold; target ≤1MiB initial island assets and ≤2MiB initial visible tiles, escalating an unmet target rather than silently exempting all island performance. |
| Receiver | p95 durable acceptance ≤1s at 5 submissions/min in staging; no 2xx before commit; restart/retry proof; 429/503 explicit. Priority backlog age and SLA breaches visible to the operator. |
| Complete record publication | At 230k records, 50/page implies ~4,600 browse pages before compartment duplication. Record HTML at an assumed 8KiB averages ~1.8GiB uncompressed; this is an estimate, **not measured cost**. Measure final record count, file count, compressed bytes, build memory/time and GCS operation cost before approval. Stream/partition generation so peak memory is bounded; avoid loading 230k full records per route. |

A complete static record surface may need hundreds of thousands of objects. Prototype a deterministic partitioned/streaming build over the real-sized published fixture before committing to that deployment; retain digest-addressed assets and reuse unchanged files between publications. Proposed engineering guardrails: peak build RSS ≤2GiB and bounded 10k-record partitions. If static publication exceeds approved resource/cost limits, explicitly consider deterministic no-JS record HTML served from immutable release files plus an offline archive export; that changes the static-serving contract and needs a new ADR. Do not solve it by dropping records or making JavaScript mandatory.

**Success evidence:** build-time `indexed_eligible/eligible = 1.0` for every compartment (with explicit policy exclusions); following all browse/search pages yields each record exactly once within its declared record-key scope; every hit points to a valid record and every evidence ref resolves to the declared capture or honest unavailable state. The old “500 of corpus” note disappears because full coverage is proven, not because the note is hidden.

Conduct five consented moderated sessions (mix local journalist/civic researcher/council staff; include keyboard/screen-reader users where feasible) on the three journeys. Proposed pilot success: ≥4/5 complete the find-and-cite task without coaching; every participant can distinguish recorded absence from missing research; no participant interprets configured access as observed use after reading a selected edge. Small samples guide design, not statistical population claims. S3's entity-resolution ground truth is a separate exercise.

Collect no third-party analytics, query text, entity focus, viewport or user/session identifier. Use aggregate service counters for response class, latency bucket, bytes, partition readiness and queue age; access logs must strip query strings/tokens. Obtain user consent for moderated notes and retention. A local opt-in performance probe may be considered later, but is not necessary to launch; timing cannot justify collecting research intent.

## 11. Migration and verification plan

1. **Rebase at the completed P31 boundary.** Record actual release/ADR/contracts, P31.14–16 outputs and outstanding S1 publication safeguards. Do not claim P31.16 is already published from this snapshot.
2. **Truthful interim copy.** Replace unsupported citation/intake/task/completeness promises in a separately reviewed change; do not remove functionality that does work. Preserve legacy citation strings as historical artifacts, but stop emitting broken new pins.
3. **Freeze/prove a publication.** Implement artifact-based publication identity and compatibility lookup, stage existing demonstrably preserved outputs, and exercise content-free withdrawal/rollback before broad link migration. Every newly generated link uses immutable paths.
4. **Build complete record/browse/index projections.** Use seeded real-PG and export inputs plus denied/unknown/licence-mixed cases. Compare canonical JSON field values and evidence refs across HTML, API and index; raw-source/restricted rows must be absent before pagination and facets.
5. **Add released search and existing-island navigation.** Run no-JS and keyboard journeys; migrate old search/map links to specific records. Ship as an explicit release so rollback switches the latest pointer without invalidating already cited publications.
6. **Enable intake only after staffing/security review.** Prove durable receipt-to-reviewer-to-disposition in staging, including failure/restart/privacy cases. Operator records public-exposure and retention/logging decisions. No unsolicited outreach or submissions in this planning run.
7. **Publish under HG-11 with a user-facing diff.** Include changed coverage denominators, available records, citation behavior, intake owner, privacy notice, limits and withdrawal behavior. Verify on both public origins. Conduct moderated tasks after publication only with explicit participants, never fabricated user study results.

## 12. Seven implementation-sized ticket candidates

Names below are semantic draft units for the root planner to number and order. M/L are relative scope, not promised calendar durations. Split a unit if implementation reveals separate migration/deployment ownership; never weaken acceptance to fit it.

| Unit | Size; dependency | Concrete deliverables and acceptance | Negative/failure tests; gate |
|---|---|---|---|
| **S4-T1 PUBLICATION-PINS** | M; S1 temporal/publication contract, final P31.16 | Publication manifest/hash and immutable route namespace; latest pointer; historical compatibility resolver; release index and correct citation component. A stored citation serves identical approved bytes after a later publication; invalid historical tuple never serves latest. | Different emitted bytes with same publication ID rejected; absent/ambiguous legacy tuple 404/409; corruption prevents activation; withdrawal returns safe 410 across variants. New ADR; live cutover HG-11. |
| **S4-T2 PUBLIC-RECORDS** | L; T1 + S1 projection, S2 scope | Per-compartment PublishedRecord schema/producers; specific static entity/capture views; complete paginated browse including no-point records; human labels/unknown states; resource-sized build report. Every eligible record reachable and every hit/evidence ID coherent. | Reviewed-name refusal, tier/rights exclusions, missing locator, multiple licences, no coordinates, >500 records, non-ASCII labels, entity split/merge aliases; no secret values in unused props. Storage/cost decision before hosted land. |
| **S4-T3 RELEASED-SEARCH** | L; T2 | Per-compartment index artifacts; read-only API JSON and no-JS HTML search; bounded filters/cursors; existing search island wiring; 230k/14-partition benchmark. Complete browse exhaustion proves no missing/duplicate record keys. | Current-spine insert cannot affect pinned results; cross-release cursor rejected; malformed FTS text, SQL metacharacters, hidden terms/counts, unavailable index, 429/503, all-unknown jurisdiction; no whole-index browser fetch. ADR for bounded dynamic search. |
| **S4-T4 INVESTIGATE-NAVIGATION** | M–L; T2/T3 + P31.14/15 | Shared query/focus state across the existing three islands, selected-record/evidence links, bounded ego graph/list parity, accessible small-screen flow; no new basemap. | Back/forward, JS off, stale selection, not-on-map record, no WebGL, failed tiles, withdrawn record, >100 edges, keyboard-only/no drag, reduced motion; no new JS on static content pages. |
| **S4-T5 DURABLE-INTAKE** | L; S1 suppression boundary + operator design ratification | Separate public receiver, restricted payload store and append-only receipt events; no-JS form, receipt/status protocol, idempotency/rate limits/log redaction; truthful Submit UI. Accepted report survives process restart and is visible in restricted queue. | Crash-before/after-commit, duplicate nonce, oversized body, HTML/script, URL credentials/private host, malicious instructions, token enumeration, shared-network throttling, CSRF/Origin omissions, expiry without data loss; no claim-spine privileges or curation routes. Public exposure/retention gates. |
| **S4-T6 REVIEW-DELIVERY** | M–L; T5 + S1 canonical disposition path | Curator intake queue with policy priority/SLA, safe response, transactional/idempotent apply workflow, durable outbox markers if configured, receipt state and redacted transparency exports. Show received→approved→applied→published distinctions. | Missing correction fields cannot append final success; replay does not double-count/assert; reviewer lacks deletion quorum; suppression affects every public artifact; reporter PII not in notices; no notification without configured/authorized destination. Named staffed owner; no auto-approval. |
| **S4-T7 COMPREHENSION-ACCEPTANCE** | M; T2/T4/T6 + S2 question inventory, S3 disclosures | Homepage/navigation simplification, versioned coverage/gap counters, dossier vs overview labels, per-record provenance, manual accessibility and consented journey study plan/results. At most four homepage metrics; applicable-question counts reconcile. | Empty/partial/conflicted/N/A case matrices; unreviewed source families not labelled independent; provisional eval stays; invalid deadlines not promoted; no map/list ability missing in no-JS path. Real human findings required for usability DONE; unavailable participants create a named return pass, not fabricated green. |

Suggested order: T1 → T2 → T3 → T4; T5/T6 may proceed after S1's receiver/publication boundaries are settled; T7 consolidates. Shared contract ownership is T2; every later ticket consumes its field schema instead of inventing another API model. Root planner assigns the single public release owner after these units; these tickets do not each independently push the site.

## 13. Cross-stream acceptance matrix and open decisions

| Candidate obligation | Owner / acceptance evidence |
|---|---|
| **S4-R1 Complete discovery** | T2/T3: every public eligible record participates in finite browse and released search; no hidden 500-row corpus cap. |
| **S4-R2 Specific navigation** | T2/T4: each site/source/entity/edge result opens its actual record at the same publication; plain-link fallback. |
| **S4-R3 True released citation** | T1 + S1: bytes/manifest identity, history lookup, no fallback to latest; withdrawal represented honestly. |
| **S4-R4 Representation parity** | S1/T2: HTML/JSON/search/map/graph consume the same admitted projection; matching capture IDs and source rights. |
| **S4-R5 Durable, private intake** | T5/T6: committed receipt reaches restricted reviewer queue after restart; no public raw report; no source/spine mutation from receiver. |
| **S4-R6 Honest completeness** | S2/T7: denominators and statuses come from the applicable question inventory, not a hardcoded gap list. |
| **S4-R7 Accessible scale** | T3/T4/T7: 230k-scale/no-JS/keyboard paths, bounded objects/queries, no basemap policy retained. |
| **S4-R8 Privacy-respecting operations** | T5/T6/operator: documented ingress/application log handling, receipt secrecy, payload expiry and workload ownership; no claim of total anonymity. |

Unsettled items requiring an explicit decision before implementation/public exposure: (a) acceptance of the new released-search dynamic HTML boundary; (b) complete static record build/storage cost versus deterministic HTML over immutable release artifacts if benchmarks exceed limits; (c) produced-work treatment of cross-compartment HTML discovery with separate downloadable representations; (d) receiver deployment/role/storage and ratified payload/log retention; (e) named review owner and achievable policy SLA; (f) S1's content withdrawal across immutable artifacts, archives and caches. None is silently approved by this research document.

The full-SPA question should be reconsidered only after complete discovery/records and several real user journeys show a need for persistent multi-entity investigation state that the existing islands cannot meet. An optional read-only companion could then share the release contract; it must not create a second source of truth, expose curator writes, erase the no-JS archive, or acquire personal accounts by default.
