# Part VII — Delivery

## 37. The public API

### 37.1 Principles

**SIG-API-001 (MUST).** The API MUST be a **hand-written, versioned contract**, never a schema
reflection. A reflected API leaks internal schema changes to consumers and makes the storage layer
un-refactorable.

**SIG-API-002 (MUST).** Every response carrying a material fact MUST include its resolution
envelope: `value`, `resolution_status`, `support`, `agreement`, `currency`, `rationale`,
`supporting_claim_ids`, `dissenting_claim_ids`, `as_of_world`, `as_of_belief`, `ruleset_version`.
A bare value MUST NOT be returned.

**SIG-API-003 (MUST).** Every response MUST carry a **coverage statement** — what was evaluable,
what was not, and why (§32.2).

**SIG-API-004 (MUST).** Every collection response MUST carry a licence statement computed from the
constituent rights records (§42.4), and every entity response MUST carry upstream attribution
(SIG-CONTRIB-020).

### 37.2 As-of semantics

**SIG-API-005 (MUST).** Every read endpoint MUST accept `as_of_world` and `as_of_belief`, defaulted
explicitly (§9.4), and MUST echo the resolved values back in the response. Omitting them MUST NOT
mean "latest" implicitly — the response states what it used.

**SIG-API-006 (MUST).** Responses MUST be cacheable by the full as-of pair. A belief-pinned request
is immutable and MUST be served with a long cache lifetime; a `now`-pinned request MUST NOT be.

### 37.3 Shape

**SIG-API-007 (MUST).** REST with OpenAPI generation is the baseline. Resource families:
`/entity/{type}/{id}`, `/claim/{id}`, `/resolution/{subject}/{predicate}`,
`/evidence/{artifact}/{capture}`, `/dossier/{jurisdiction|org}`, `/search`, `/task`,
`/coverage/{scope}`, `/contradiction`, `/crosswalk`, `/export`, `/changes`.

**SIG-API-008 (MUST).** Every SIG identifier MUST be dereferenceable at `/id/{type}/{uuid}` with
content negotiation to HTML, JSON-LD, and RDF (SIG-IDENT-031).

**SIG-API-009 (MUST).** A `/changes` feed MUST exist, driven by the snapshot-diff layer (§29.7), so
downstream consumers can follow SIG incrementally rather than re-downloading.

**SIG-API-010 (SHOULD).** GraphQL MAY be offered as a secondary read surface. It MUST NOT be the
only surface, because it defeats caching and archivability.

### 37.4 Access tiers and anti-misuse

**SIG-API-011 (MUST).** Tiers: anonymous (rate-limited, public data), registered (higher limits),
partner (bulk, agreed terms). No tier grants access to `restricted` or `sealed` material through
the public API.

**SIG-API-012 (MUST).** The API MUST NOT expose: any real-time device-liveness signal; any endpoint
enabling per-person lookup; any endpoint returning `sealed` capture bytes; or coordinates at finer
precision than the asset's sensitivity tier permits (§19.4).

**SIG-API-013 (MUST).** Acceptable-use terms MUST prohibit re-identification attempts, and MUST
state the remedy for violation. Terms without a stated remedy are decorative.

---

## 38. Exports and dataset publication

### 38.1 Static-first

**SIG-EXPORT-001 (MUST).** SIG MUST publish **versioned bulk artifacts** to object storage with
checksums and a manifest: Parquet, CSV, JSONL, GeoJSON, PMTiles, JSON-LD/RDF, and a
SQLite/Datasette bundle.

**SIG-EXPORT-002 (MUST).** Tabular exports MUST ship as a **Frictionless Data Package**; evidence
bundles MUST ship as **RO-Crate**. Each quarterly release MUST be deposited to **Zenodo** with a
concept DOI for the dataset and a version DOI for the release; evidence **bytes** are excluded by
size, but the **manifest of digests** MUST be deposited.

**SIG-EXPORT-003 (MUST).** Exports MUST be reproducible from `(as_of pair + ruleset version +
resolver version)` via the same code path the API uses. A hand-built export is a different dataset
wearing the same name.

### 38.2 Licence computation

**SIG-EXPORT-004 (MUST).** An export bundle's licence MUST be **computed** from the SPDX
expressions of its constituent rights records, and the build MUST **fail** if a share-alike input
appears in an export whose declared licence does not satisfy it (§42.4).

**SIG-EXPORT-005 (MUST).** OSM-derived physical assets MUST ship as a **separate file** under
**ODbL-1.0**; SIG-original graph data ships separately under **CC-BY-4.0** (§42.3). A single merged
file would force the whole export share-alike.

**SIG-EXPORT-006 (MUST).** Every export MUST carry per-row rights provenance, so a downstream user
can determine the licence of any individual fact rather than being forced to assume the strictest.

### 38.3 The crosswalk export

**SIG-EXPORT-007 (MUST).** The identifier crosswalk (SIG-IDENT-033) MUST be published under the
most permissive licence its constituents allow, prominently, and separately from the main dataset.
It is the highest-leverage artifact SIG produces for the ecosystem.

### 38.4 Downstream application classes as design targets

**SIG-EXPORT-010 (MUST).** The export portfolio MUST be validated against **six named downstream
application classes** (OL-15.7-01). Each is a design target, not an aspiration: for each, SIG MUST
be able to name the specific artifact that serves it, and a class with no serving artifact is an
export-design defect.

| Class | Serving artifact | Requirement it imposes |
|---|---|---|
| Academic analysis | Parquet + the crosswalk export + Zenodo DOIs | Reproducibility; stable citation; coverage denominators |
| Newsroom tools | JSON API + per-claim evidence links + belief-pinned permalinks | Defensibility under editorial review |
| Local dashboards | Per-jurisdiction JSON/CSV slices | Small, cacheable, jurisdiction-scoped extracts |
| Route / privacy applications | PMTiles + GeoJSON of the **ODbL** asset layer | Correct licence separation; geometry without the graph |
| Policy trackers | The procurement/renewal feed + iCal/RSS | Forward-looking dates, not only history |
| Visualizations | The edge list + entity crosswalk | Typed edges with ER-quality metadata attached |

**SIG-EXPORT-011 (MUST).** Where a class's needs conflict with another's — for example, route
applications want the device layer alone while researchers want it joined — SIG MUST serve them as
**separate artifacts** rather than one compromise artifact. This is also what the licence separation
of §42.3 requires, so the two constraints agree.

### 38.5 Sustainability of distribution

**SIG-EXPORT-008 (MUST).** Bulk distribution MUST use zero-or-low-egress object storage. **Egress
pricing, not storage or compute, is the existential cost** for a project whose value is bulk data
downloads: a 2 GB export downloaded 5,000 times a month is 10 TB of egress, which is free on some
providers and a four-figure monthly bill on others. Success is the failure mode, and the storage
choice must be made with that in mind.

**SIG-EXPORT-009 (SHOULD).** Torrent and IPFS distribution SHOULD be offered for the largest
artifacts, both for cost and for takedown resilience (§46.5).

---
