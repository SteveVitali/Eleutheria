## 23. Connector specifications

Each connector is specified as: purpose; access path; incrementality; the predicates it may write;
the predicates it MUST NOT write; and its known failure modes. Only the governing rules and the
non-obvious constraints appear here; per-connector detail lives with the connector code and its
fixture suite (§48).

### 23.1 Universal connector rules

**SIG-INGEST-033 (MUST).** A connector MUST declare a **predicate allowlist**. Writing outside it
is a schema error. This is what prevents a portal scraper from asserting a contract date, or a
contract parser from asserting a current camera count — the `D6` admissibility filter (§10.5)
enforced at ingestion rather than only at resolution.

**SIG-INGEST-034 (MUST).** A connector MUST NOT perform entity resolution itself. It emits
candidate identifiers; the identity layer (§14.6) resolves them.

### 23.2 `osm` — physical assets

Writes: geometry, asset type, manufacturer, mobility, direction, mount, upstream ids, OSM version.
MUST NOT write: deployment linkage, operator attribution derived from SIG inference (that is L4),
contract facts.
Constraints: REQ-R1-01…R1-06. Handles nodes, ways, relations. Semicolon multi-values as sets.
Cross-key normalization. Preserves OSM element id **and version**, so a later OSM edit is detectable.
Output lands in the **ODbL-licensed** asset table (§42.3).

**SIG-INGEST-045 (MUST).** The connector MUST consume at minimum the following keys, and MUST record
any surveillance-bearing key it encounters outside this list as an unmapped value with a research
task (REQ-R1-02). Measured coverage is against the 144,312 elements tagged
`surveillance:type=ALPR` as of 2026-08-20 (R1-F1.5).

| Key | Carries | ALPR coverage | Handling |
|---|---|---|---|
| `man_made=surveillance` | The primary feature | 99.7% | Selection predicate |
| `surveillance:type` | Device kind — **116 distinct values** | — | Split on `;` as an unordered set; normalize via versioned mapping |
| `surveillance` | Zone — **430 distinct values**, polluted with types and booleans | 88.3% | Never trusted alone (R1-F1.4) |
| `surveillance:zone` | Zone (`traffic` 83.4%) | 87.4% | Cross-checked against `surveillance` |
| `camera:type` | `fixed` 92.0% | 92.4% | Drives `mobility`; ~8% are non-fixed |
| `camera:mount` | `pole` 22.4%, `street_lamp` 2.5% | 30.6% | Sparse → field-research task |
| `direction` | Bearing | **93.6%** | Input to derived FOV (§19.3) |
| `camera:direction` | Bearing (alternate) | 3.7% | Reconciled with `direction` |
| `manufacturer` | Vendor string — **7,031 distinct values** DB-wide | 86.9% | Normalize; `Flock Safety` 73.3%, `Motorola Solutions` present |
| **`manufacturer:wikidata`** | Vendor QID | **83.4%** | **First-class crosswalk key** (SIG-STORE-044) |
| **`operator`** | Operating organization | **19.1%** | **Absence is the ~116,800-device backlog** (SIG-ONTO-028) |
| `operator:wikidata` | Operator QID | 12.3% | Crosswalk |
| `operator:type` | Operator class | 2.9% | Sparse → research task |
| `brand` / `brand:wikidata` | Brand | 3.8% / 3.5% | Reconciled with manufacturer |
| `ref` | Device reference/label | — | Preserved as an upstream identifier |
| `start_date` / `check_date` | Installation / last verification | — | `valid_from` / staleness input |
| `source` | Provenance of the mapping | 1.7% | Recorded as source-dependence input (§10.8) |
| `electricity` | Power arrangement | 2.6% | Descriptive |
| `description` | Free text | 1.5% | `raw_value` only; never parsed into claims |

Non-camera surveillance types are in scope from Phase 4, not deferred: `gunshot_detector` (3,250
elements) and `AFR` (67) exist in OSM today (R1-F1.3).

**SIG-INGEST-045a (MUST).** `first_observed` MUST be derived from the element version at which
surveillance tags **first appeared**, obtained by walking the element history. It MUST NOT be read
from the element's creation timestamp.

**This is not a refinement; it prevents a systematic corruption of the temporal layer** (SC-17.3).
Measured on four live ALPR nodes: all were created on the same day in **2009** as part of a freeway
import, and all were **repurposed** into surveillance nodes on **2024-12-15** by adding tags to the
existing node. A connector reading the creation timestamp would date these devices to 2009 — before
the vendor existed — and would do so plausibly enough to escape notice, because old dates on road
infrastructure look unremarkable. At national scale this would corrupt exactly the property the
project exists to provide (OL-22.5).

**SIG-INGEST-045b (RATIONALE).** A bare OSM element id is **not** a well-defined reference across time.
The same id denoted a freeway feature for fifteen years and a surveillance device thereafter. Only
`(element_type, id, version)` is unambiguous, which is why REQ-R1-01 requires the version and why
§23.2 preserves it.

**SIG-INGEST-045c (MUST).** The element history endpoint
(`/api/0.6/<type>/<id>/history.json`) returns the complete version history with per-version tag sets
and is **verified working**. SIG MUST fetch it for elements under active reconciliation and MUST NOT
replicate the OSM history planet. This is the operative answer to outline Q19.

**SIG-INGEST-045e (MUST).** SIG MUST **discard OSM `user` and `uid` at ingest** and MUST NOT store
or expose them. A queryable table of *which mapper recorded which police camera* is a targeting
surface, and building one would make SIG a hazard to the volunteers it depends on. The upstream
history services adopt the same posture. `changeset` id is retained — it is the provenance anchor
and is not person-identifying on its face.

**SIG-INGEST-045f (MUST).** Element keys MUST be `(osm_type, osm_id)`, never `osm_id` alone: node,
way and relation id spaces are independent and overlap.

**SIG-INGEST-045g (MUST).** **Deletions require snapshot diffing.** Overpass's `(changed:…)` filter
reports modifications but **never reports deletions**, so a purely incremental connector would never
observe a device being removed. SIG MUST diff successive snapshots to detect disappearance, and MUST
distinguish *deleted from OSM* (a mapping event) from *removed from the street* (a world event) —
they are different claims with different predicates, and conflating them would let a mapper's
cleanup read as a decommissioning.

**SIG-INGEST-045h (MUST).** Overpass quotas are published and MUST be respected: **≤10,000
requests/day and ≤1 GB/day**, default `[timeout:180]`, `[maxsize:512MiB]`. `429` means slot
exhaustion — **back off in time**; `504` means the query was too large — **shrink it**. Retrying a
504 unchanged is useless and rude. The connector MUST poll `/api/status` rather than model quota
locally, because one DNS name fronts independently rate-limited servers.

**SIG-INGEST-045i (MUST NOT).** The Overpass documentation explicitly names *"stitching bounding
boxes to scrape the full data of the complete world"* as prohibited use and directs bulk consumers
to a planet dump. SIG MUST therefore use **PBF + tag filtering for bulk** and reserve **tiled
Overpass for increments**. A worldwide unbounded query fails in practice regardless.

**SIG-INGEST-045j (MUST).** SIG MUST NOT use another project's self-hosted Overpass instance without
that project's explicit permission, even where it is publicly reachable.

**SIG-INGEST-045d (MUST).** The Overpass connector MUST send a **descriptive** User-Agent with a
contact address. A browser-spoofed agent returns **HTTP 406** from the public instance — the
politeness requirement of §26 is mechanically enforced here, not merely conventional. The connector
MUST also avoid spaces in Overpass tag-value filters, which trip a request filter; filter
client-side instead.

### 23.3 `atlas` — agency adoption

**Input shape.** The upstream's methodology combines nine components, each of which is a different
evidence genre and therefore a different `R`/`D` profile that SIG MUST preserve rather than flatten
into one tier: OSINT; news reporting; government documents; meeting minutes; press releases;
procurement leads (including commercial procurement aggregators); crowdsourcing; staff and intern
review; and imported specialist datasets (OL-2D-AT-02). Where the upstream records which component
produced a row, SIG MUST carry it; where it does not, SIG MUST record the granularity loss rather
than assign a tier by guess.

Writes: `deployment_exists` at family-level technology granularity, with Atlas's own source
attribution preserved.
MUST NOT write: device counts, coordinates, configuration, current status.
Constraints: key on the Atlas agency identifier, routing non-ORI-shaped values to the surrogate path.
Preserve Atlas source attribution and allow later evidence to supersede or temporally qualify
(OL-2D-AT-06). Record the Atlas vocabulary version, and record category retirements so a
disappearance is never read as a world change (SIG-ONTO-059).

### 23.4 `flock_portal` — via the aggregator API

**SIG-INGEST-035 (MUST).** This connector MUST source the portal layer from the **aggregator's
public CC BY-SA 4.0 API** (§22.5, SC-18), and MUST NOT attempt direct capture from the vendor, whose
every path returns a bot challenge (F2.1). Output MUST land in the **CC BY-SA 4.0 compartment**
(SIG-LIC-004a), never merged into the CC-BY graph.

**The discovery problem, stated because it sizes the fallback.** The vendor publishes **no directory
of portals**. Portal discovery has historically been performed by **brute-force enumeration over
candidate locality/agency URL slugs** — which is why Eyes on Flock's discovery work is
infrastructural rather than cosmetic (OL-2B-EOF-02, OL-A.1). Combined with F2.1 (every path returns
403 to a scripted client) this means SIG **cannot discover portals at all** by its own lawful means.
Discovery must come from a partner, from contributor reports of portals they have visited, or from
agency-side records confirming a portal exists. An implementer who does not understand this will
under-size the Phase 11 fallback.

**Writes when enabled:**

| Predicate | Volatility | Notes |
|---|---|---|
| `active_device_count` | FAST | `D1` for this predicate |
| `configured_retention_days` | MODERATE | Distinct from policy and vendor default (§29.5) |
| `configured_sharing_partner` | FAST | Directional; configured access only |
| `state_lookup_enabled`, `national_lookup_enabled`, `federal_sharing_enabled` | VOLATILE | |
| `subscribed_hotlist_topic` | VOLATILE | |
| **`vehicles_detected_windowed_count`** | VOLATILE, `h`=1 mo | **Windowed** (SIG-RECON-011) |
| **`hotlist_hit_windowed_count`** | VOLATILE, `h`=1 mo | **Windowed.** One of the two headline statistics the portal-aggregation ecosystem exists to collect |
| `usage_search_windowed_count` | VOLATILE, `h`=1 mo | **Windowed** |
| **`portal_stated_permitted_use`** | SLOW | `R2 · D2`. A **first-party portal statement**, distinct from an adopted `Policy` document (§11.13) |
| **`portal_stated_prohibited_use`** | SLOW | Same |
| `portal_exists` / portal disappearance | — | An event on the artifact (§17.6) |
| `portal_last_updated_declared` | — | The portal's own claim about its freshness; never trusted as `observed_at` |

MUST NOT write: contract facts, device geometry, or any per-search row.

### 23.5 `records` — MuckRock, NextRequest, DocumentCloud

Writes: `RecordsRequest` entities, `EvidenceArtifact` rows, released-document captures.
Constraints: MuckRock is **api_v2** with auth on all data endpoints and a short-lived JWT; the
outline's api_v1 reference is wrong. `no_responsive_records` is a positive finding feeding the
coverage model (SIG-ONTO-040).

### 23.6 `procurement` — cooperative vehicles, USAspending, agenda platforms

Writes: `Contract`, `FundingInstrument`, `acquisition_channel`, quantities, renewal terms,
lifecycle transitions with dates.
Constraints: cooperative piggyback contracts MUST set `parent_cooperative_contract`. USAspending
sub-awards MUST be pulled, not only prime awards. Agenda platforms are per-tenant APIs, so the
connector needs a tenant registry, which SIG must build and publish (§22.3).

**SIG-INGEST-047 (MUST).** The `artifact_type` vocabulary (§10.3.2) MUST additionally carry
`state_auditor_survey`, `warrant`, and `procurement_aggregator_record`, and the source registry MUST
carry the commercial procurement aggregator named by the upstream Atlas methodology as an origin of
its procurement leads — under a `LINK` custody posture, because it is paywalled. Several state
auditors periodically survey agencies on surveillance-technology holdings; those surveys are `R1`
government datasets and are among the highest-value under-exploited sources available (OL-2F-GOV-02).

### 23.7 `audit_structural` — HIBF / agency audit exports

Writes: `UsageAggregate`, configured sharing edges from `SharedNetworks.csv`, event-log lifecycle
transitions, and `Camera Count` observations.
MUST NOT write: any per-search or per-plate row (§18.1).
Constraints: REQ-R2-05…R2-09. `***` redaction ≠ empty. Portal audit schema is agency-configured
and must be discovered per capture. The four audit source types are **not interchangeable** and
MUST be recorded on every aggregate.

**SIG-INGEST-046a (MUST).** Where an upstream publishes **derived** rather than primary data, SIG
MUST NOT ingest it as though it were the underlying record.

The specialist audit project's bulk exports are derived artifacts: plate values are **hashed**,
person names are **inferred** with confidence scores, reasons are **redacted**, and editorial
annotations are **injected into the data fields themselves**. Ingesting those rows as agency records
would silently import another project's inferences into SIG's graph **as though they were
observations** — the exact confusion the whole epistemic model exists to prevent (§10.1).

Such data MUST be ingested, if at all, as `R3` claims **about the upstream's conclusions**, with the
upstream named as the asserting party and its inference method recorded — never as `R1`/`R2` claims
about the agency. Where SIG needs the primary record, it MUST obtain it by records request.

**SIG-INGEST-046b (MUST).** A `robots.txt` disallow MUST be honoured **even where the data behind it
is technically reachable**. That project's exports exist, but its `robots.txt` disallows the API
path serving them. Reachability is not permission (§26 rule 2). The correct action is to **ask** —
which is Stage-0 outreach, and which the succession offer (SIG-CONTRIB-013) makes worth answering.

**SIG-INGEST-046c (MUST).** An **affirmative machine-readable rights reservation** MUST be honoured
as a refusal and recorded on the rights record. One ecosystem project combines
`Content-Signal: ai-train=no`, explicit AI-crawler disallows, and an **EU DSM Article 4 reservation**
— a formal opt-out with legal effect in the EU. `UNDETERMINED` and *"affirmatively refused"* are
different states and MUST be stored differently: the first invites a Stage-0 conversation, the
second closes it.

**SIG-INGEST-046 (MUST).** The upstream specialist's six documented capabilities (OL-2C-HIBF-08) are
dispositioned as follows, explicitly, so that none is silently dropped:

| Capability | SIG's disposition |
|---|---|
| Officer / name resolution | **Deliberately not performed.** SIG does not ingest per-search rows, so no officer names enter (SIG-PUB-010, §18.1). This is discharge by exclusion, and it is intentional, not an omission |
| Police rosters | **Not ingested.** A roster is a list of natural persons; §11.3 forbids `Person` rows outside the officer test. SIG references the upstream's roster work rather than reproducing it |
| Duplicate handling | Applies at the **aggregate** level: overlapping audit exports covering the same period MUST be deduplicated by `(source_org, searching_org, window)` before aggregation, and the overlap recorded |
| Source-agency provenance | Preserved: every aggregate carries the audit export it came from and that export's requesting agency |
| Anomaly detection | SIG consumes the upstream's published anomaly findings as `R3` claims; it does **not** rebuild detection over data it does not hold |
| Records-request templates | Reused, with attribution, in the request generator (§36) |

### 23.8 `accountability` — Accountability Atlas, Abuse Library, CourtListener

**Input shape (Accountability Atlas).** The upstream publishes five artifacts, each of which MUST be
consumed rather than only the headline CSV: an **issue-record CSV**; a **source-index CSV**; a
**GeoJSON**; a **data dictionary**; and a **research archive** (OL-2E-AA-02). The data dictionary is
the authority for the crosswalk (§20.3), and the source index is what allows SIG to preserve the
distinction between an event and the reporting about it. Its record categories — local
regulation/action, litigation, wrongful stop / false alert, immigration / data sharing,
security / product issues, stakeholder / company context — MUST be crosswalked, not adopted
wholesale.

Writes: `AccountabilityEvent`, `LegalProceeding`, source-class-tagged evidence links.
Constraints: `epistemic_status` is REQUIRED and preserved verbatim from the upstream where the
upstream provides one. Court APIs are targeted-lookup only (§22.2). A curated source index MAY be
ingested as an index without normalizing entries into facts (OL-2E-AL-02).

### 23.9 `data_driven` — the vendor-neutral historical ALPR network

**SIG-INGEST-043 (MUST).** EFF/MuckRock's Data Driven releases MUST be ingested as a **first-class
connector**, not treated as background reading. The outline designates them a priority ingestion
source for the first vendor-neutral ALPR model (OL-4.2-01), and they are the only substantial public
evidence base for pre-Flock, non-Flock ALPR network behaviour.

Writes: historical `Organization` rows; historical `configured_access` edges across a vendor network;
`deployment_exists` claims for a non-Flock vendor; aggregate scan/hit-rate observations.
MUST NOT write: current-state claims of any kind — every claim from this source carries its
historical `observed_at` and is subject to normal currency decay (§28.3), which for
`configured_sharing_partner_set` (FAST, 4-month half-life) means these claims are `C4 HISTORICAL`
and cannot resolve present-tense questions.

**SIG-INGEST-043a (MUST).** The dataset is **retrievable and MUST be ingested with its measured
values**, not paraphrased. Verified figures: **200 agency rows × 20 columns** across 23 states plus
a federal row; **2,541,566,055 detections against 11,384,164 hits — 99.552% of scans matched no
hotlist**; a mean of **160.2 direct sharing partners** per agency (maximum **851**); and **130
agencies** feeding a vendor-operated pooled lookup service. A companion release covering 89 agencies
in one state independently gives **99.948%** non-hit.

The non-hit proportion is the most analytically important number in the corpus and the easiest to
lose in summary: it establishes that ALPR collection is **overwhelmingly of uninvolved vehicles**,
which is a structural property of the technology rather than of any one vendor.

**SIG-INGEST-043b (MUST).** The connector MUST target the **file artifacts directly**. The
article URL cited by the outline (OL-21-35) is a **dead end containing no data links**; the data
lives at separate file paths. Record both, and mark the article as context rather than as the source.

**SIG-INGEST-043c (MUST).** A hard limitation MUST be recorded with the ingest: all **463
source-document links resolve to a document host that blocks automated access**. SIG therefore
obtains **sharing degree** — how many partners each agency had — but **not the sharing edge list**.
The distinction matters: degree supports the claim "this agency shared with 851 others"; it does not
support drawing any specific edge. Rendering degree as if it were a known network would be exactly
the unexplained edge the defining standard forbids.

**SIG-INGEST-043d (MUST).** This corpus already contains **vendor-specific retention-window columns
in incommensurable units** — a 30-day-window column for one vendor alongside other vendors' figures.
This is direct, dated evidence for the incommensurable-counts problem (§29.1) appearing *five years
before* the current vendor landscape, and the connector MUST preserve the window definition per
column rather than normalizing the values together.

**SIG-INGEST-044 (RATIONALE).** This connector's value is **structural, not current**: it proves that
cross-agency ALPR networks predate and exceed any single vendor (OL-2D-DD-03), and it supplies the
historical baseline against which vendor-replacement analysis (§29.4) is measured. A Flock-only
graph would mis-model the problem, and this connector is the concrete guard against that.

---

### 23.10 `rf_candidates` — lead generation

Writes: `CandidateAsset` only, at `R6`.
MUST NOT write: `PhysicalAsset`, or anything with `residential_parcel_flag = true` (§43.5).

---

## 24. Document parsing and extraction

### 24.1 Layered strategy

**SIG-PARSE-001 (MUST).** Parsing MUST proceed by the cheapest sufficient method, with the method
recorded on the extraction:

| Layer | Method | Use when |
|---|---|---|
| 1 | Structured import (CSV/XLSX/JSON/GeoJSON) | The source is already structured |
| 2 | Deterministic selector/template extraction | Stable HTML or a known form layout |
| 3 | PDF text extraction | Digital-native PDF |
| 4 | PDF table extraction | Tabular content in a digital PDF |
| 5 | OCR | Scanned documents |
| 6 | LLM-assisted structured extraction | Unstructured prose where 1–5 fail (§25) |
| 7 | Human transcription | Everything else, and all adjudication |

**SIG-PARSE-002 (MUST).** File classification MUST run before parsing, and its verdict MUST be
recorded. Real records responses arrive as mixed-format ZIPs containing scanned faxes,
password-protected PDFs, XLSX with merged headers, and native exports with multiple sheets.

**SIG-PARSE-003 (MUST).** Every extraction MUST emit a **locator** (page, bbox, cell, row, byte
range, DOM path) for every claim. An extraction that cannot say where a value came from MUST be
rejected, because the evidence viewer (§39.6) and the defensibility guarantee (OL-24-18) both
depend on it.

**SIG-PARSE-004 (MUST).** Extraction MUST preserve the raw literal in `raw_value` before any
typing or normalization (P2), including for values that fail to parse. A value SIG could not parse
is data about the source, not an error to be dropped.

### 24.2 Reason-code normalization

**SIG-PARSE-005 (MUST).** Free-text reason fields MUST be normalized through a **versioned,
inspectable, reversible** mapping stored as data. The raw text MUST be retained; the mapping
version MUST be recorded on every claim; and changing the mapping MUST NOT rewrite history
(SIG-STORE-038). *(OL-2C-AW-04, OL-2C-AW-05.)*

**SIG-PARSE-006 (MUST).** Reason fields arrive in **two** forms — free text and constrained
dropdowns — depending on configuration. These are different normalization problems and MUST be
distinguished on the claim, because a dropdown value is a much stronger signal than a typed phrase.

### 24.3 Parser drift

**SIG-PARSE-007 (MUST).** Every parser MUST have committed fixtures (real captured inputs, expected
outputs) so that an upstream redesign fails a test rather than silently producing garbage (§48).

**SIG-PARSE-008 (MUST).** Fixtures alone are insufficient: they pin known inputs and keep passing
forever. A **nightly canary** MUST run each parser against live sources and alert on structural
change. *(R11 identifies silent parser drift as a top-5 operational risk.)*

---

## 25. LLM usage policy

### 25.1 Permitted uses

**SIG-LLM-001 (MAY).** Models MAY be used for: proposing candidate structured claims from
unstructured documents; suggesting reason-code categorizations; suggesting entity aliases;
drafting summaries **for human reviewers**; and generating review rationales.

### 25.2 Prohibited uses

**SIG-LLM-002 (MUST NOT).** Models MUST NOT:

1. be the **sole basis** for a published factual claim;
2. write directly to the graph without review at or above the threshold of §14.6 tier 4;
3. overwrite, paraphrase, or "clean" source text (P2);
4. produce confidence values (§10.6 — confidence is computed by rule, from evidence);
5. resolve contradictions;
6. create a `Person` row (SIG-ONTO-016);
7. promote a `CandidateAsset` (§43.5);
8. determine a sensitivity classification.

### 25.3 Required scaffolding

**SIG-LLM-003 (MUST).** Every model-assisted extraction MUST record `model_id`, `prompt_version`,
and the deterministic parameters actually used, and MUST validate output against a schema.

**SIG-LLM-004 (MUST).** Every model-extracted claim MUST carry a **source span** — the exact text it
came from — and an extraction that cannot cite its span MUST be rejected (SIG-PARSE-003). This is
the single most important guardrail: it makes hallucination detectable mechanically, because a span
that does not appear in the capture fails validation.

**SIG-LLM-005 (MUST).** Model-extracted claims MUST be `R6` (§10.4) and enter as `PROPOSED`.

**SIG-LLM-006 (MUST).** A sampling rate for human review MUST be defined per extraction type, and
accuracy MUST be measured against a gold set on a published cadence. If measured accuracy falls
below the published threshold, the extraction type MUST be demoted to human-only.

**SIG-LLM-007 (MUST).** The pipeline MUST degrade gracefully when the model is unavailable: work
queues, it does not fail, and no claim is emitted with a lower evidentiary standard to compensate.

---

## 26. Crawler conduct

**SIG-INGEST-036 (MUST).** SIG MUST adopt and publish a Crawler Conduct Policy binding on every
connector. Its operative rules:

1. **Identify.** A descriptive UA with a contact URL and an explanation page. No spoofing.
2. **Honor `robots.txt`**, including AI-crawler directives and content-signal headers. Where
   robots.txt is unretrievable, permission is **not granted** (SIG-INGEST-012).
3. **Rate-limit conservatively**, per host, with backoff. Never burden a small civic host.
4. **Never circumvent access controls** — no authentication bypass, no paywall evasion, no
   challenge-solving, no proxy rotation or human-mimicking to defeat bot management.
5. **Prefer the offered channel.** If a source publishes an API, a bulk download, or a partner
   feed, use it instead of scraping the HTML.
6. **Ask first** where the compact is unresolved and the source is a small civil-society project.
7. **Honor opt-out** immediately and record it in the compact.
8. **Cache aggressively; refetch rarely.** Conditional requests, content-hash short-circuits.

**SIG-INGEST-037 (MUST).** Rule 4 is not merely ethical. Circumvention techniques have been held
to support anti-circumvention claims independent of any computer-fraud theory, and vendor API terms
in this sector expressly prohibit bulk extraction (R8). The policy is also a **legal posture**, and
deviating from it is an ADR-level decision requiring counsel, not an engineering judgment.

---
