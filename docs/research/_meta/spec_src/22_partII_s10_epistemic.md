## 10. The epistemic model

The outline states (§9) that SIG must be designed around the difference between fact,
observation, claim, inference, derived metric, and unresolved contradiction. This section
defines those distinctions as concrete objects with concrete rules. §28 defines the algorithm
that operates on them.

### 10.1 The evidence → claim chain

**SIG-EPIS-001 (MUST).** Every published material fact MUST be reachable by this chain, and the
chain MUST be traversable in both directions through the API and the UI:

```
Source (an upstream dataset, publisher, or records channel)
   └─ EvidenceArtifact        the identified document/dataset/page/record
        └─ EvidenceCapture    an immutable, content-addressed snapshot of it at a moment
             └─ Extraction    a versioned parse of a capture by a named method
                  └─ Claim    subject · predicate · value, with raw value and time
                       └─ Resolution      the current-best answer for that subject+predicate
                            └─ Presentation  what a user or API consumer sees
```

**SIG-EPIS-002 (MUST).** No shortcut through this chain is permitted. Specifically:

- A Claim MUST reference an Extraction, or be a `human_assertion` with a named author and a
  rationale, or be an `inference` living at L4. There is no fourth kind.
- An Extraction MUST reference exactly one EvidenceCapture.
- An EvidenceCapture MUST reference exactly one EvidenceArtifact and MUST carry a content hash.
- An EvidenceArtifact MUST reference exactly one Source and MUST carry a rights record (§42.4).

**Rationale.** This is the mechanical implementation of OL-24-18: *make the system reproducible
enough that a journalist can defend a graph claim by tracing it back to evidence.* If any link
is optional, the guarantee collapses to a convention, and conventions decay.

### 10.2 Source, EvidenceArtifact, and EvidenceCapture are three different things

The outline's `EvidenceArtifact` (OL-8.15) conflates three objects that must be separated,
because they change at different rates and carry different rights.

| Object | Identity | Mutability | Example |
|---|---|---|---|
| **Source** | The publisher/dataset/channel | Long-lived; its terms and license attach here | "Flock Safety transparency portals"; "EFF Atlas of Surveillance"; "MuckRock request #12345" |
| **EvidenceArtifact** | A specific addressable thing within a source | Its *content* may change over time; its identity does not | "The transparency portal at slug `hagerstown-md-pd`"; "the Atlas CSV"; "contract PDF, 14 pp." |
| **EvidenceCapture** | The bytes SIG obtained at a specific instant | **Immutable, forever** | "SHA-256 `ab12…` retrieved 2026-08-20T14:03Z, 412 KB, `text/html`" |

**SIG-EPIS-003 (MUST).** A transparency portal that reports 25 cameras today and 28 next month
is **one artifact with two captures**, not two artifacts. This is what makes portal diffing
(§29.7) and the "what did the portal say on date T" question (OL-2B-IND-02) expressible.

**SIG-EPIS-004 (MUST).** An artifact that *disappears* MUST be recorded as an event on the
artifact, not as a deletion. A vanished Flock portal is data (OL-2B-FP-03): the artifact gains a
`disappeared_observed_at`, its last capture remains, and a research task is generated. The
outline's Q18 (how to preserve deleted portals and inactive organizations) is answered by this
rule plus §17.6.

### 10.3 Field specifications

#### 10.3.1 `Source`

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `name` | text | ✓ | |
| `source_kind` | vocab | ✓ | `upstream_project`, `vendor_site`, `government_portal`, `records_channel`, `news_publisher`, `court_system`, `academic`, `community`, `contributor`, `commercial` |
| `homepage_url` | url | | |
| `operator_org_id` | SIG id | | Who publishes it |
| `default_tier` | vocab | ✓ | Default evidence tier (§10.4); overridable per artifact |
| `rights_id` | SIG id | ✓ | The rights record (§42.4) |
| `custody_posture` | vocab | ✓ | `MIRROR` / `DERIVE` / `REFERENCE` / `LINK` (§8.4) |
| `compact_status` | vocab | ✓ | Outreach/permission state (§22.2) |
| `ingestion_permitted` | bool | ✓ | Hard gate; connectors refuse to run when false |
| `robots_policy` | vocab | ✓ | `honor` / `honor_with_exception` / `not_applicable` |
| `crawl_budget` | struct | | Per-host rate limits (§26) |

#### 10.3.2 `EvidenceArtifact`

Discharges OL-8.15-02 and OL-2F-DC-02, corrected and extended.

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `source_id` | SIG id | ✓ | |
| `url` | url | | May be absent for offline records |
| `stable_locator` | text | ✓ | The identity within the source (portal slug, DocumentCloud id, docket number, OSM element ref, MuckRock request id) |
| `artifact_type` | vocab | ✓ | `contract`, `invoice`, `council_minutes`, `agenda_packet`, `audit_export`, `configuration_export`, `portal_page`, `policy_document`, `court_filing`, `news_article`, `dataset`, `press_release`, `presentation`, `email`, `photograph`, `osm_element`, `radio_observation`, `budget`, `grant_award`, `statute`, `regulation`, `screenshot`, `other` |
| `title` | text | | |
| `publisher_org_id` | SIG id | | Issuing organization (OL-2F-DC-02) |
| `published_at` | edtf | | T3 |
| `document_date` | edtf | | The date *of* the document, distinct from publication |
| `acquisition_method` | vocab | ✓ | `public_web`, `api`, `bulk_download`, `foia_request`, `leak`, `field_observation`, `contributor_upload`, `partner_feed`, `court_records`, `purchase`, `unknown` — internationalized per §13.8 |
| `records_request_id` | SIG id | | Links to the request that produced it (OL-2F-MR-02) |
| `page_count` | int | | |
| `primary_or_secondary` | vocab | ✓ | `primary`, `secondary`, `tertiary` |
| `default_tier` | vocab | ✓ | Overrides the source default |
| `rights_id` | SIG id | ✓ | |
| `sensitivity_class` | vocab | ✓ | §43.3; drives storage tier and public exposure |
| `capture_status` | vocab | ✓ | `captured`, `access_restricted`, `paywalled`, `link_rotted`, `not_attempted`, `refused_by_policy` |
| `disappeared_observed_at` | timestamptz | | Set when the artifact is confirmed gone |
| `supersedes_artifact_id` | SIG id | | Amended contracts, revised policies |

**SIG-EPIS-005 (MUST).** `capture_status` MUST be populated for every artifact. An artifact SIG
cited but could not retrieve is a legitimate, recordable state (see spot-check SC-07); it MUST
NOT be silently omitted, and it MUST NOT be treated as evidence of the same weight as a captured
artifact.

#### 10.3.3 `EvidenceCapture`

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `artifact_id` | SIG id | ✓ | |
| `content_hash` | text | ✓ | Multihash; algorithm recorded, not assumed (§17.2) |
| `retrieved_at` | timestamptz | ✓ | T4 |
| `retrieved_by_run_id` | SIG id | ✓ | Pipeline lineage (§21.6) |
| `http_status` | int | | |
| `media_type` | text | ✓ | |
| `byte_size` | bigint | ✓ | |
| `storage_uri` | text | ✓ | Object-store location (§17.3) |
| `storage_tier` | vocab | ✓ | `public`, `restricted`, `sealed` (§17.5) |
| `capture_method` | vocab | ✓ | `http_get`, `api_call`, `headless_browser`, `warc`, `manual_upload`, `screenshot`, `pdf_print` |
| `capture_tool_version` | text | ✓ | |
| `request_fingerprint` | jsonb | | Headers/params sent, for reproducibility |
| `redaction_applied` | bool | ✓ | Whether SIG applied redaction before storing (§43.7) |
| `parent_capture_id` | SIG id | | For derived captures (a redacted copy of a sealed original) |

**SIG-EPIS-006 (MUST).** Captures are immutable. A redacted derivative is a **new capture**
with `parent_capture_id` set, not an edit. This preserves OL-13.4-01's requirement for raw
private archival storage alongside a redacted public derivative.

#### 10.3.4 `Extraction`

This object does not appear in the outline and is required. It is what makes re-parsing
possible without destroying history (P2, P3, and the backfill requirement of §21.7).

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `capture_id` | SIG id | ✓ | |
| `method` | vocab | ✓ | `structured_parse`, `html_selector`, `pdf_text`, `pdf_table`, `ocr`, `tabular_import`, `llm_assisted`, `human_transcription`, `api_field_map` |
| `extractor_name` | text | ✓ | Module path |
| `extractor_version` | text | ✓ | Semantic version, pinned |
| `model_id` | text | | Required when `method = llm_assisted` (§25.3) |
| `prompt_version` | text | | Required when `method = llm_assisted` |
| `parameters` | jsonb | ✓ | Deterministic settings actually used |
| `extracted_at` | timestamptz | ✓ | |
| `run_id` | SIG id | ✓ | |
| `review_status` | vocab | ✓ | `unreviewed`, `sampled_ok`, `human_verified`, `disputed`, `rejected` |
| `superseded_by_extraction_id` | SIG id | | Set when re-extracted with a better parser |

**SIG-EPIS-007 (MUST).** Re-extracting a capture with an improved parser MUST produce a **new**
Extraction and a new set of Claims. The prior Claims are superseded (§9.4), not deleted, so that
a citation made against the old extraction remains reproducible.

#### 10.3.5 `Claim`

Discharges OL-8.16-02, extended.

| Field | Type | Req | Notes |
|---|---|---|---|
| `id` | SIG id | ✓ | |
| `subject_type` / `subject_id` | vocab / SIG id | ✓ | The entity the claim is about |
| `predicate` | vocab | ✓ | From the versioned predicate registry (§13.6) |
| `object_type` | vocab | ✓ | `literal`, `entity_ref`, `vocab_term`, `quantity`, `money`, `geometry`, `duration`, `interval`, `document_ref` |
| `object_entity_id` | SIG id | | When `object_type = entity_ref` |
| `value_json` | jsonb | ✓ | The normalized value, typed per predicate |
| `raw_value` | text | ✓ | **NOT NULL.** The source's literal text (P2, OL-2C-AW-05) |
| `raw_context` | jsonb | | Surrounding text, cell coordinates, page/bbox — the citation anchor |
| `unit` | text | | For quantities |
| `normalization_method` | vocab | | How raw → value |
| `normalization_version` | text | | Versioned and inspectable (OL-2C-AW-05) |
| `valid_from` / `valid_to` | edtf | | T1 |
| `valid_from_kind` / `valid_to_kind` | vocab | ✓ | §9.3 |
| `observed_at` | edtf | | T2 |
| `observed_at_unknown_reason` | vocab | | Required when `observed_at` is NULL |
| `value_kind` | vocab | ✓ | `value`, `somevalue` (a value exists but is unknown), `novalue` (asserted to have no value). Wikibase-derived; NULL cannot carry this distinction (§9.5, R6-F31) |
| `rank` | vocab | ✓ | `preferred`, `normal`, `deprecated`. A source's own ranking of its statements; deprecation preserves a known-wrong claim without deleting it |
| `asserted_by_person_id` | SIG id | | For human assertions |
| `assertion_rationale` | text | | Required for human assertions |
| `evidence_tier` | vocab | ✓ | §10.4 |
| `claim_polarity` | vocab | ✓ | `affirms`, `denies` — enables `EVIDENCE_OF_ABSENCE` (§9.5) |
| `qualifiers` | jsonb | | Scope qualifiers (Wikidata-style), e.g. "as reported by the vendor" |
| `derived_from_claim_ids` | SIG id[] | | Source-dependence chain (§28.6) — critical for not double-counting copied sources |
| `recorded_at` | timestamptz | ✓ | T5 |
| `superseded_at` | timestamptz | | T5 close |
| `supersedes_claim_id` | SIG id | | |
| `correction_reason` | vocab | | Required when superseding |
| `review_status` | vocab | ✓ | `unreviewed`, `machine_accepted`, `human_verified`, `disputed`, `retracted` |
| `sensitivity_class` | vocab | ✓ | §43.3 |
| `rights_id` | SIG id | ✓ | Inherited from artifact; drives export licensing (§42.4) |

**SIG-EPIS-008 (MUST).** `raw_value` is NOT NULL with no exceptions. If a claim has no
corresponding literal source text — because it is an inference — it does not belong at L1. It
belongs at L4.

**SIG-EPIS-009 (MUST).** `derived_from_claim_ids` MUST be populated whenever SIG ingests a claim
from a source that itself derived it from another source SIG also ingests. Several ecosystem
projects reuse each other's data. Without this field, three sources that all copied one portal
would appear as three independent corroborations, and the reconciliation engine would report
false confidence. §28.6 specifies the discount rule.

---
#### 10.3.6 `ClaimEvidence` — a claim has an evidence *set*, not a source

**SIG-EPIS-010 (MUST).** A claim MUST NOT hold a single `source` foreign key. It MUST reference
an evidence **set** through a join table in which each row carries a **role**. The outline's
`Claim.source` (OL-8.16-02) is a simplification that cannot express the situations SIG exists to
handle. *(Corrects OL-8.16-02; corroborated by R6-F33.)*

| Field | Type | Req | Notes |
|---|---|---|---|
| `claim_id` | SIG id | ✓ | |
| `extraction_id` | SIG id | | The parse that produced or supports this claim |
| `capture_id` | SIG id | ✓ | Denormalized for traversal without a join through extraction |
| `role` | vocab | ✓ | See below |
| `locator` | jsonb | | Page, bbox, cell, line, byte range, DOM path, CSV row — the *exact* anchor |
| `excerpt` | text | | The quoted span, subject to §43.7 redaction |
| `weight_note` | text | | Why this artifact bears on this claim, when non-obvious |

**Evidence roles:**

| Role | Meaning |
|---|---|
| `establishes` | The artifact directly states the claim. |
| `corroborates` | An independent artifact stating the same thing. |
| `contextualizes` | Supports interpretation without stating the claim. |
| `contradicts` | The artifact bears on this claim and disagrees with it. |
| `supersedes_basis` | The artifact is why a prior claim was corrected. |
| `attests_absence` | The artifact was searched and did not contain the fact (§9.5). |

**SIG-EPIS-011 (MUST).** The `contradicts` role is required and is not decorative. It allows a
single claim to carry, in its own evidence set, the artifact that undermines it — which is what
makes contradiction visible at the point of use rather than only in an aggregate view
(OL-6.5-01, OL-24-11).

**SIG-EPIS-012 (MUST).** Every `establishes` row SHOULD carry a `locator`, and MUST carry one
for artifacts over one page. "The contract says 42 cameras" is not evidence; "page 7, table 2,
row 3 of capture `sha256:ab12…`" is. The evidence viewer (§39.6) renders from this field, and
the extraction-quality gate (§25.3) fails LLM extractions that omit it.

---
