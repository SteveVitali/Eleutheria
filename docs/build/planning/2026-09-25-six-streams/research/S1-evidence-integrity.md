# S1 — Evidence integrity from acquisition to publication

Date: 2026-09-25. Research/design, not an implementation or publication decision.
Owner: evidence-integrity research stream. Baseline: commit 0e57e6461d6a5db2e8e0042464750ce2ea65db5e in the isolated codex/sig-six-stream-research worktree. P31.8 code is present; its closeout was not part of the snapshot. Revalidate seams against the final integrated P31 tip before implementation. This document does not alter the active orchestrator state.

## 1. Decision summary

SIG's claim/decision separation is a sound foundation. The immediate need is a production contract that preserves what its parsers already know, then carries the same evidence, time, semantic and publication decisions into every reader. The proposed program has eight bounded work units, with hosted remediation separated from deterministic implementation and explicitly gated.

The design should:

1. Bind assertions to actual capture occurrences, immutable OCFL versions and exact extraction locators. Preserve historical synthetic links as explicitly classified legacy provenance.
2. Separate assertion identity from evidence occurrence identity, observation time from system knowledge time, and replay from a new source observation.
3. Preserve typed claim metadata at the sink; separate publisher/registry custodian from device operator; keep source record type distinct from the thing the record describes.
4. Require comparable count populations before diagnosing a contradiction. Reclassify the OKC example as differently scoped source reports and an approximate derived sum until a genuine comparable disagreement is established.
5. Make publication disposition a shared, fail-closed read contract across labels, claims, evidence metadata, derived facts, search, exports and citations. Keep factual correction, access suppression and rights decisions separate.
6. Measure attributable, captured, locatable, reproducible and publication-eligible claims separately, with denominators and honest unknowns.

No design here approves rights, names a person for publication, authorizes a live source fetch, retroactively creates evidence, or supplies a legal opinion. Existing licence compartments and human decisions retain their scope.

## 2. Method, evidence classes and source register

Evidence classes used below:

- C: inspected code/schema/configuration at the pinned commit.
- R: committed report of a historical execution, not independently rerun against hosted state.
- X: bounded local experiment of existing pure functions, no network/DB/filesystem writes.
- W: primary standard or original publisher/reporting page read through the web tool on 2026-09-25; not acquired into SIG's evidence store.
- I: inference or design proposal. A code counterexample is not a demonstrated production incident.

Only the assigned research document was written. No shared checkout changes, tests requiring services, builds, database queries, cloud commands, connector runs or deployment occurred. The only runtime experiment used python3 -B, imported the existing pure partner-identity helpers from this worktree, and printed results; it did not instantiate a sink.

### Repository source register

Paths and symbols are the durable anchors; line numbers aid review at this baseline and may move.

| ID | Class | Source and inspected anchors | What it supports |
|---|---|---|---|
| R01 | C | db/src/db/claim_sink.py:127 content_digest; :232 record_resightings; :342 _INSERT_CLAIMS; :899 _ensure_evidence; :1017 _insert_claim; :1139 batched insert | Synthetic evidence chain; limited persisted metadata; duplicate/sighting behavior; hardcoded tier/epistemic defaults |
| R02 | C | db/deploy/evidence.sql; evidence_store.sql; claim.sql; claim_evidence.sql | Existing capture/extraction, raw_context, qualifier, revision, retraction, temporal and locator columns already exist |
| R03 | C | parsing/src/parsing/claim.py ParsedClaim/ParsedValue; locator.py Locator/to_row; connectors/src/connectors/pipeline.py run_post_capture/_emit | Parser locator/method contract; capture context is known before sink handoff |
| R04 | C | connectors/src/connectors/capture_ocfl.py OcflCaptureStore.put/get/metadata; evidence/src/evidence/ocfl.py; evidence/redaction.py | Real bytes and metadata can be stored; current digest reference reads head version; redaction is a derivative |
| R05 | R | docs/adr/ADR-111-restart-resume-capture-store-and-pinned-job-images.md:15–19,63–65; docs/adr/ADR-113-asserting-replay-of-persisted-captures.md | Pre-roll ephemeral captures; durable capture mounts and asserting replay introduced in P31.4/P31.6 |
| R06 | C | connectors/src/connectors/runner.py replay_ingest:1278–1356; db/src/db/claim_sink.py record_capture/resume_marks | Replay uses original capture marks but newly inserted claims still receive the sink's synthetic evidence chain |
| R07 | C | reconcile/src/reconcile/materialize.py CAPTURE_TIME_JOIN/observation_time/read_claim_groups; api/src/api/store_pg.py claims_for; resolution/src/resolution/camera_sites_pg.py _RECORDS_SQL/read_camera_records | Different latest-observation rules and unbounded capture dating under historical belief |
| R08 | C | exports/src/exports/shaping.py observation_envelope/shape_sites, run_shaping provenance metric; spine_export.py _provenance_ttl | Export observation semantics differ from value resolution; source linkage is called provenance completeness; release-level synthetic provenance |
| R09 | C/X | connectors/src/connectors/dot_511.py:633,909–917,958–1000; data/camera_registry_targets.toml:901–915; runner.py:295; resolution/src/resolution/partner_identity.py | Publisher→operator mapping; pure helper accepts OSM publisher as an organization and emits an entity-ref twin |
| R10 | C | resolution/src/resolution/partner_identity.py:155–193,205–239; data/partner_identity.toml; db/src/db/identity_guard.py; docs/adr/ADR-112-partner-organisation-entity-ref-claims.md:36–43,147–167 | Global normalized-name identity; absent emitted external IDs; acknowledged publication-review seam |
| R11 | R | docs/build/reports/p31.6-hosted/inventory_after.json; VERIFICATION.md:24–40,64–92 | Recorded hosted counts, thin entity-link coverage and open publication-review guard |
| R12 | C/R | ops/src/ops/seed.py:11–16,43–105; tests/acceptance/fixtures/okc_sources.json; tests/acceptance/okc_slice.py:151–219; docs/slice/P06.1_retrospective.md §3; docs/build/reports/P30.2_HOSTED_MATERIALIZATION.md:30 | Seed origin, source genre/scoping problems, prior acknowledgement and hosted seeded contradiction |
| R13 | C | reconcile/src/reconcile/model.py CountClaim.scope_note; counts.py _resolve_one_basis/reconcile_as_single_count; resolve.py _admissibility | Basis checks exist, but scope_note does not guard comparison; one-value-per-source treatment must not erase distinct qualified facts |
| R14 | C | db/deploy/access_control.sql:67–103; rights_decisions.sql; api/src/api/store_pg.py rights_for/_label_for/search labels; policy/rights.py; exports/compartments.py | Tier and rights controls exist; rights/publication are distinct; current organization label reads ignore review flag |
| R15 | C | evidence/src/evidence/tiers.py public_representation; redaction.py; policy/src/policy/officer.py/publication.py; db/src/db/suppression.py | Existing byte tiers, redaction lineage, officer gate and small-cell safeguards that must remain intact |
| R16 | R | docs/tickets/DEFERRALS.md D-P31.5-2, D-P31.1-3, D-R6.1-EVAL; docs/build/reports/ROUND9_FOLLOWUPS_DESIGN.md; manifest P31.8–P31.19 | Ownership boundaries; current planned work must not be duplicated or declared complete here |

### External source register — all accessed 2026-09-25

| ID | Source | Limited use in this design |
|---|---|---|
| W01 | [OCFL 1.1 specification](https://ocfl.io/1.1/spec/), §§3.3–3.5 | Version immutability, inventory state→digest→content paths, fixity. A database row naming an OCFL object is not proof the bytes exist. |
| W02 | [W3C PROV-DM](https://www.w3.org/TR/prov-dm/), entities/activities/agents and §5.2 | Distinguish generation, quotation, revision and derivation; represent a correction as a new attributed result. |
| W03 | [W3C PROV-O](https://www.w3.org/TR/prov-o/), wasDerivedFrom/qualifiedDerivation/wasRevisionOf | Serialize the actual qualified evidence chain, not only source attribution or an export-time pseudo-capture. |
| W04 | [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/#selectors) | Selectors identify a segment of a specific source; selector interpretation must be tied to the captured representation. Reuse existing Locator first; do not migrate every locator to a new standard at once. |
| W05 | [PostgreSQL 18 range types](https://www.postgresql.org/docs/18/rangetypes.html) | Explicit half-open bounds and containment semantics. PostgreSQL ranges alone do not enforce application bitemporality or observation ordering. |
| W06 | [Journal Record original reporting, August 18, 2026](https://journalrecord.com/2026/08/18/okc-council-votes-keep-flock-cameras-privacy-concerns/) | Currently reports 90 OKCPD cameras and about 100 privately owned within city limits. Supports separate reported components; SIG's 190 is a derived approximate sum, not a verbatim quotation. |
| W07 | [DeFlockOKC publisher page](https://deflockokc.com/) | Currently labels 299 as a community-map figure for the metro area in September 2026. Supports a differently scoped publisher report; does not establish the fixture's August 20 observation date. |
| W08 | [DeFlockOKC case page](https://deflockokc.com/the-case.html) | An advocacy synthesis links to contracts and policy. A capture of this page is not itself an executed contract, statute or policy original. No legal propositions from the page are adopted here. |
| W09 | [KGOU original reporting, August 19, 2026](https://www.kgou.org/politics-and-government/2026-08-19/oklahoma-city-council-renews-license-plate-reader-contract-despite-pushback) | Confirms the fixture URL is a news report, not the original council minutes. No source rights disposition follows. |

The external pages were inspected as research, not preserved as rights-cleared SIG captures. A future acquisition must use the authorized capture/rights workflow. Short factual paraphrases here do not imply redistribution permission for the original material.

## 3. Revalidated findings and corrections to the first audit

### F1 — The strongest gap is the sink contract, not the absence of a provenance model

Confirmed C. The schema already supports claim_evidence.locator/excerpt/extraction_id, claim.raw_context, normalization version, valid-time, correction links and epistemic fields. ParsedClaim requires a locator. The live pipeline has CaptureRef at run_post_capture and _emit. Yet PgClaimSink._ensure_evidence creates a synthetic source/genre/run capture: digest of connector/source/run, zero byte size, synthetic sig:connector URI, synthetic OCFL object identifier, and empty extraction parameters. _LINK_EVIDENCE writes claim_id/capture_id/role only. _insert_claim hashes the connector dictionary but discards its evidence locator/method/context as independently retrievable fields.

Additionally, _INSERT_CLAIMS uses the fixed R3/D2/I1 defaults and sensitivity tier zero for every staged claim, rather than reading supplied values; the write path does not carry the existing valid-time, qualifier, revision/retraction and normalization fields. Reader-domain typing compensates for the sink's deployment placeholder. These are observable losses even where a particular connector currently emits only public facts.

Correction to prior framing: there is real OCFL code, parser provenance, and now durable capture storage. It is wrong to say SIG has no evidence architecture or that every claim is unsubstantiated. The gap is between acquired bytes, parsed claims and their persisted/public representation. Upstream Part VIII filters exist; this audit has not demonstrated a sensitive-data disclosure.

Additional C detail: OcflCaptureStore stores one object per byte digest and adds metadata versions, while get/metadata resolve its head. Same bytes fetched at different times/URLs therefore need explicit occurrence/version references; a content digest identifies bytes, not the acquisition event. The release _provenance_ttl builds source-attributed capture entities dated at export time. These should be described as release/source contributions, not offered as original acquisition provenance.

### F2 — Historical preservation is partial; the missing-byte fraction is unknown

Confirmed R, bounded by report coverage. ADR-111 records that hosted captures were ephemeral before the rollout and no bucket held capture objects at the measured time. P31.4 added durable capture mounts. P31.6 replayed stored captures successfully for a bounded subset. This does not prove all earlier evidence is irretrievably lost: a fixture, local archive, WACZ, backup or independently retained exact blob may survive. Nor does it establish the fraction of the current corpus with replayable raw evidence.

Confirmed C. The exported provenance numerator accepts a nonempty source_id. The earlier audit correctly challenged a blanket byte-replayability interpretation, but must call this a metric-definition problem rather than accuse its underlying source-attribution count of arithmetic error.

Design consequence: inventory first; distinguish synthetic reference, exact bytes verified, occurrence attested, locator verified, replay verified and unavailable. Reacquisition today is a new observation and can never repair an old capture timestamp by assertion.

### F3 — Publisher/operator confusion is reproducible, but its public impact remains unmeasured

Confirmed C/X. camreg_osm_surveillance routes through dot_511. The camera target's agency is copied to camera_operator; the link method explicitly identifies the reviewed publisher name as the operating organization. The target label OpenStreetMap contributors (republished man_made=surveillance nodes) passes partner_identity because surveillance is an organization marker. The pure-function experiment produced a sig.org.name reference with normalized value openstreetmap contributors republished man made surveillance nodes, and partner_ref_rows emitted the corresponding entity-ref twin. No DB was used.

Confirmed R: P31.6 records 26,839 inserted claims on the OSM replay and 29,496 camera_operator entity refs overall. It does not list every organization's label or demonstrate a public dossier containing the erroneous attribution. Treat exact live/public exposure as an audit question, not a concluded incident.

Confirmed C design risk: identical normalized names share a global identity key; partner_identity has no jurisdiction argument. The helper accepts Springfield Police Department as one such key. That demonstrates missing disambiguating input, not that two specific real Springfield agencies were merged. External ID preference exists but the audited emitters do not supply those IDs. Do not substitute a universal jurisdiction key: national vendors and cross-jurisdiction bodies require stable external identity and explicit matching, while source-scoped unresolved names should remain separate candidates.

### F4 — Latest observation and past belief are not one shared contract

Confirmed C counterexamples; no database reproduction was run in this planning pass.

- P31.7 records A→B→A by adding a sighting of existing A. Camera-site selection still orders by claim_id, so the newer B claim wins there. A useful fix to value resolution is not yet propagated to camera clustering.
- CAPTURE_TIME_JOIN uses maximum retrieved_at across all linked captures. API claims_for filters claim.sys_period at requested belief time but does not time-bound the evidence links. A future sighting of old A can change a computation requested at a belief time before that sighting.
- The join also lacks an evidence-role filter. Future real contradicting/background bindings must not count as a source reasserting the value.
- New claims produced by an asserting replay receive a new synthetic capture with current time, even though replay marks preserve original capture time. record_resightings correctly suppresses duplicate freshness on replay, but that does not fix the dating of newly extracted claims from old bytes.
- observation_time reduces timestamps to UTC dates, and same-source supersession breaks equal-date ties by claim ID. Same-day A→B→A is therefore a required negative test, not covered by the different-month example.
- Export observation_envelope intentionally retains distinct values as conflict, while the camera reader chooses a single latest claim. This is not automatically a bug: one is an observation history and the other a current selection. The UI/schema must name the two products and carry a shared context so they are not presented as equivalent current facts.

Correction to the prior audit: these are deterministic structural counterexamples, not measured historical-response failures. Reconcile RESOLVE delegates belief filtering to its caller, so the correction belongs in the shared input contract as well as its consumers. Simply adding retrieved_at <= belief is insufficient: a historically dated capture ingested later was not known to SIG earlier. Binding recorded_at is also needed.

### F5 — The seeded count example is evidence-informed, but not a comparable contradiction

Confirmed C/R/W. The initial claim seed explicitly comes from committed transcriptions. Current original reporting supports the 90-plus-about-100 components; current DeFlockOKC supports its 299 metro report. Thus the first audit must not imply those numbers were invented. The 190 value is SIG's approximate arithmetic derivation from two reported populations, while its seed raw_value holds only the private-business clause. The geography differs and the map figure's fixture observation date is not independently established by today's page.

The test fixture has scope_note, and P06.1_retrospective §3 already calls out the scope/population defect. Counts._resolve_one_basis does not consume that qualifier as a comparability guard; the seed loses it entirely. The later hosted report still presents these values as its lone contradiction. This is previously recognized design debt that survived integration.

A further evidence distinction matters: a fixture artifact marked executed_contract points to an advocacy summary, and an artifact marked council_minutes points to KGOU reporting. Genre and directness must describe the captured artifact, while references to a primary contract/minutes are separate links. Counting source-family labels does not establish independent corroboration when those labels ultimately derive from the same reporting.

Design consequence: preserve reported components, represent the approximate derivation and its assumptions, attach geography/population/basis qualifiers, and classify comparison as not_comparable or comparison_undetermined. Do not delete the old demonstration or force a new genuine contradiction just to keep a dashboard nonzero.

### F6 — Publication review is an actual open seam; rights approval is a different decision

Confirmed C/R. PgClaimSink writes publication_review_required for name-only organizations. API labels/search reads ignore it; P31.6 says the row stays open for P31.16 after hosted organizations were added. Hiding only organization labels would be incomplete: literals, raw_value, reverse links, facets, claim endpoints and export-derived paths can repeat the name.

Rights decisions, sensitivity tiers, officer naming, factual status, evidence access and aggregate suppression are separate controls. The existing rights_decision log lifts specific UNDETERMINED records under recorded authorization; it is not a general publication veto/revocation channel. OCFL retention does not imply public bytes. A sealed capture's public metadata may itself need URI/header/locator minimization; the current metadata representation exposes source_uri by design, so adding real source URIs must never expose tokens or sensitive paths.

No legal conclusion follows from source availability, a review flag, this audit, or existing operator risk acceptance. Preserve the exact rights decision and its basis. A future new rights approval remains HG-03; public cut-over remains the appropriate publication gate.

## 4. Target contracts and examples

### 4.1 A typed assertion envelope with a separately keyed evidence occurrence

Use existing packages and schema fields where possible; no new top-level package. Define a versioned, dependency-light connector/sink contract, validated at the production boundary. Keep a lossless raw payload in an appropriately restricted artifact when necessary; do not indiscriminately persist prohibited fields just because they are raw.

Current abbreviated input and persisted result:

~~~json
{
  "input": {
    "predicate_id": "camera_operator",
    "value": "Registry Publisher",
    "evidence": {"source_url": "https://example.invalid/feed", "locator": {"kind": "row", "row": 4}}
  },
  "persisted": {
    "extraction_method": "deterministic",
    "capture_source_uri": "sig:connector:dot_511:source:camera_registry",
    "capture_byte_size": 0,
    "claim_evidence_locator": null
  }
}
~~~

Proposed conceptual v2 shape (not final generated model):

~~~json
{
  "contract_version": "claim-input/2",
  "assertion": {
    "source_record_key": "source:target:record-17",
    "subject_ref": {"scheme": "sig.source.record", "value": "source:target:record-17", "kind": "camera_observation"},
    "predicate_id": "camera_operator",
    "object": {"kind": "entity_candidate", "label": "Example City Department", "identifiers": []},
    "raw_value": "Example City Department",
    "normalization": {"rule": "organization-name", "version": "2"},
    "qualifiers": {"operator_role": "operates", "jurisdiction": "reviewed-place-id"},
    "valid_time": {"from": null, "to": null, "from_kind": "unknown", "to_kind": "unknown"},
    "observation": {"at": null, "precision": "unknown", "basis": "not_stated"},
    "sensitivity_tier": 0,
    "rights_ref": "existing-reviewed-rights-id",
    "origin_kind": "live_extraction"
  },
  "evidence_occurrences": [{
    "capture_ref": {"digest": "sha256-or-multihash-of-real-bytes", "object_id": "sig:capture:...", "version": "v3", "logical_path": "capture", "retrieved_at": "2026-09-25T10:15:20Z"},
    "role": "establishes",
    "locator": {"kind": "row", "row": 4},
    "extraction": {"method": "arcgis_feature_json", "extractor_version": "2", "config_digest": "sha256:..."},
    "literal_digest": "sha256:...",
    "origin_kind": "live_capture"
  }]
}
~~~

The example claims an operator only if a source field or reviewed explicit source-wide attestation supports it. Otherwise emit publisher/custodian provenance and operator unknown. Preserve source identifiers as typed data; never turn a numeric record ID into a device serial number or a publisher into an owner.

Assertion digest v2 covers source assertion identity and semantic fields, including qualifiers, time precision and normalization version; it excludes acquisition timestamps and capture-occurrence IDs. Evidence occurrence identity includes capture occurrence, role, locator and extraction version. Changing a source locator alone should not silently create a new factual assertion; changing semantic content should. Exact repeated evidence should be idempotent, but a genuinely new acquisition of identical bytes remains a new sighting.

Do not reinterpret or overwrite legacy content_digest. Introduce a version-tagged digest/alias mapping with explicit legacy links, initially in dual-read mode. Existing claim IDs and citations remain valid.

### 4.2 Additive physical model

Implement via new sqitch changes with deploy/revert/verify and a new ADR; update LinkML/source generation where the public ontology changes. Candidate names are design placeholders:

| Additive object | Required purpose and invariants |
|---|---|
| capture_occurrence / evidence binding metadata | Reference an actual evidence_capture, immutable OCFL version/logical path, verified digest/size and sanitized acquisition context. Separate original retrieval instant from DB-recorded knowledge instant. Actual capture rows use real bytes; legacy synthetic rows retain their original IDs and receive a classification event. |
| claim_evidence_binding | claim/capture/extraction/role/locator, exact literal or protected literal digest, DB recorded_at, origin and unique binding digest. Supports multiple locators for one claim/capture/role, which the existing claim_evidence primary key cannot express. Existing claim_evidence remains a compatibility projection/link where safe; never UPDATE its old rows to pretend they were exact. |
| assertion_identity_alias | Versioned stable digest→claim group/claim mapping; legacy claim IDs remain addressable. No destructive dedup or silent merge of claims with different scopes. |
| claim_disposition_event | Accepted/revised/retracted/quarantined/legacy-demonstration disposition with target claim, reason, evidence, actor role, decision time and replacement claim references. Reuse existing revision/retraction fields for new claims; events make old immutable records correctable in all reads. |
| entity_type/identity decision | Source-record type and resolved thing type may differ. Add attributable type/identity decisions rather than UPDATE existing deployment rows. Name-only candidates are source-scoped until a recorded resolution links them; reviewed external IDs may join across sources. |
| publication_disposition_event | Separate allow/withhold/restrict/redacted-derivative decision for a claim/entity/capture/release projection, reason, authority, scope, evidence and effective time. Does not relicense data. Restrictive current decisions apply even when a reader requests historical belief. |
| integrity_audit_result | Append-only measurement of capture/locator/replay verification with tool/ruleset version, sampled IDs, denominator and result. A past pass is not a guarantee of future object availability. |

Prefer existing extraction and evidence_capture columns to duplicate tables. The first implementation ADR must inventory those fields and justify each new column/table. New indexing: binding(claim_id, recorded_at, capture_id), occurrence(capture_id, retrieved_at), disposition(target_id, decided_at, event_id), digest-version lookup. Batch writes by capture/chunk, preserve transaction boundaries and identity-guard ordering from ADR-110/111. No per-claim WAN round trips.

Rows already associated with a legacy global-name organization remain historical claims. If a name collision is demonstrated, append distinct source-scoped entities and revised claims plus an identity split decision. Preserve historical identifier resolution and expose a disambiguation/tombstone view; do not repoint every old foreign key or pretend the old identifier always meant one corrected entity.

### 4.3 Temporal context shared by every materializer and reader

Define one resolver input context:

~~~json
{
  "world_at": "2026-09-20T12:00:00Z",
  "belief_at": "2026-09-21T12:00:00Z",
  "ruleset_version": "...",
  "spine_snapshot": "...",
  "publication_policy_at": "current-authorized-policy",
  "representation": "current_resolution"
}
~~~

For a historical read, require claim/system eligibility AND binding recorded_at <= belief_at. Original acquisition time must not be later than the eligible observation boundary, but its existence alone never proves earlier system knowledge. Do not manufacture exact binding knowledge times for legacy rows. Use known lower/upper bounds or explicitly report historical binding uncertainty.

For undated observations, use the latest eligible establishing source sighting as an explicitly labeled proxy. Background/contradicts roles, redaction generation, extraction replay and export build times do not refresh a source observation. Replay-created claims are known at replay time but cite the original occurrence and use its observation proxy. Date-only source values stay date-only; retain an exact ordering instant separately when a capture provides one. Within-day ordering must not collapse to claim UUID order.

Value resolution, camera records and public exports consume the shared selection. Observation history can remain a separate intentional representation listing A and B; label it history, not a contradictory current coordinate. Coordinate pairs come from one eligible source-record occurrence, not independently selected latitude and longitude values from different times. Camera run completion must be per execution even if the input digest matches an older run, so A→B→A cannot leave the latest-completed pointer on B's run.

Public historical responses apply current suppression/publication restrictions. Privileged reproducibility can reconstruct historical epistemic state without making currently withheld data public. Include policy/ruleset/rights decision watermarks in cache keys; a claim-count-only key cannot represent a publication restriction or a time-driven freshness transition.

### 4.4 Count comparison contract and the OKC correction

Each quantity needs a qualified measurement key:

~~~json
{
  "basis": "reported_operating_devices",
  "unit": "physical_camera",
  "geography": {"id": "oklahoma-city-limits", "boundary_version": "known-or-unknown"},
  "population": {"operator_class": "private_business", "technology": "alpr", "inclusions": [], "exclusions": []},
  "time_window": {"start": "2026-08-18", "end": "2026-08-18", "precision": "day"},
  "estimate": {"kind": "approximate", "value": 100, "bounds": null},
  "method": "reported_statement",
  "derivation": null
}
~~~

Comparison returns comparable, not_comparable, or unknown, with dimension-by-dimension reasons. Unknown is not equivalent to matching. Equivalent boundaries may be proven by a versioned mapping; do not use fuzzy geography strings as proof. Population subsets may support a labeled coverage/difference question but not a value_disagreement. Contradiction detection runs only over compatible measurements whose uncertainty ranges disagree under the recorded rule.

For OKC: preserve reported 90 police-operated and approximately 100 privately owned components with their citations; an optional approximate 190 derived estimate names both inputs and non-overlap/coverage assumptions. Preserve 299 as a publisher's metro-map report at its evidenced observation time. Display different scopes, comparison undetermined/not comparable, and an actionable request for a compatible inventory. Append a correction of the seeded contradiction's interpretation, retain its historical record and stop including it in the current genuine-comparable-contradiction KPI. Do not alter archived ADR/report bodies.

### 4.5 One publication decision function, two kinds of history

The public decision is a conjunction of explicitly separate policies: factual disposition permits use; evidence provenance is disclosed at the proper strength; source/claim rights permit this output; sensitivity and officer rules permit the fields; required entity review is satisfied; publication veto/embargo does not block; aggregate suppression rules hold. A current veto does not erase the original claim or its historical derivation.

Apply the same decision function to claim literals/raw text, organization labels/aliases, graph endpoints, search/facets/counts, evidence metadata, PROV output, dossier tables, download artifacts, tile properties and public corrections. A withheld label cannot reappear in a query suggestion or parent-capture URL. Public tombstones use safe reason categories; privileged audit records retain detailed rationale.

Redaction creates a new digest-bearing capture with parent link and method/version. Locators into the original and redacted derivative are separately verified; never point an original byte offset at edited bytes. If redaction removes the establishing content, the public excerpt cannot claim to demonstrate the fact; disclose restricted supporting evidence or withhold the claim as policy requires. A successful fact extraction does not make raw unredacted bytes public. Remove secret-bearing request/query/header data before logging; record protected fingerprints where necessary. Sealed metadata is minimized independently of access to the body.

For rights, retain recorded rights and the authorized effective decision separately. Corrections to review interpretation are not automatic relicensing. Maintain per-compartment artifacts and lineage for derived facts; if joined inputs have incompatible/unresolved output rights, fail closed or publish a permitted metadata-only reference according to a reviewed rule. This design makes no decision about ODbL or other legal obligations.

## 5. Inventory, recovery and remediation algorithm

1. **Pin inputs.** After the active chain reaches an integration boundary, record commit, schema, job-image digests, source registry/ruleset versions, snapshot watermark and sample seed. Use a read-only consistent DB snapshot; do not run global locks or full raw-byte downloads on the live host.
2. **Inventory metadata cheaply.** Count claims by connector/source/genre/origin/capture classification/rights compartment and historical period. Identify synthetic signatures explicitly, not by byte_size=0 alone: a legitimate empty response can be zero bytes. Build a capture-index inventory without fetching prohibited or unavailable external content.
3. **Classify each recoverable unit.** exact preserved bytes + acquisition occurrence; exact bytes without historical occurrence; transcription with cited URL; synthetic run record only; missing/unknown; intentionally restricted/sealed. Keep these classifications orthogonal to factual accuracy and permission to publish.
4. **Find candidate archived bytes.** Use run marks, sidecar inventories and approved existing archives. Verify bytes against their recorded digest and exact OCFL version, then validate occurrence metadata. Search local/backup archives only in explicitly authorized locations. Do not infer the original from a same-URL current page.
5. **Replay without network.** Use the pinned original extractor/config where available and the proposed updated extractor separately. Match claim semantics and exact literal+locator. Append a verified binding only when the evidence is sufficient; if multiple captures/locators match and occurrence is uncertain, record ambiguity instead of choosing one.
6. **Repair semantics additively.** Generate a dry-run repair proposal per target: old claim IDs, replacement facts/qualifiers, changed source genre/type/identity, reason, evidence and affected materializations. Existing public source material may justify a new correctly scoped claim; a seed does not become historically captured simply because today's text is similar.
7. **Review and apply a bounded batch.** Require the appropriate existing gate when publication/rights/Part VIII is involved. Run idempotent compare-and-append with expected input digest, batch manifest and resume marker. Pause on changed source/config, unknown lineage, conflicting identity or unexpected counts. The rollback is a new disposition and restored read pointer, not DELETE.
8. **Recompute and compare.** Materialize only impacted subjects/partitions under the same pinned context; measure differences in claims, current dispositions, comparable contradictions, identities, graph paths, public rows and exact evidence metrics. Existing human/pinned decisions remain protected.
9. **Publish a correction release only after authorization.** Produce an immutable release manifest, changed/withdrawn citation map, public safe correction notes and internal recovery report. Old release IDs stay stable; public retrieval respects current access restrictions. Previously downloaded copies cannot be recalled, so do not promise erasure of third-party archives.

Missing bytes and unresolved history are expected legitimate outcomes. They create owned research tasks and disclosures, not guessed locators, artificial historical timestamps, silent removal from denominators or a perpetual need to retry unchanged sources.

## 6. Audit protocol, metrics and resource budget

### Metadata census and stratified manual/byte audit

Perform a complete metadata census first; do not equate it with complete source verification. Independently sample by connector class, source lineage, capture epoch (pre/post durable storage), predicate family, country/jurisdiction, format, rights compartment, sensitivity/publication posture, seeded/manual/live/replay origin, and all high-impact derived/public claims. Oversample suspect strata while preserving sampling weights.

Pilot: 40 claims across at least eight strata to validate protocol/cost; then 400 probability-sampled claims plus every publication-sensitive or known-problem fixture in a separately reported targeted set. These are audit workload proposals, not a precision guarantee. Publish weighted estimates and confidence intervals for the probability sample; never mix targeted failure cases into an unweighted corpus pass rate. Audit units can cluster by capture/source; record cluster-aware uncertainty rather than treat hundreds of rows in one file as independent.

Each sampled claim must answer: what does the source literally establish; at what location in which bytes; what transformation produced the value; what is the source's own record identity and role; which dates are stated versus inferred; is the comparison scope valid; are rights and publication decisions correctly projected; can another reviewer reproduce the same normalized fact offline? A finding is unresolved if any necessary step cannot be established.

Report, by stratum and total denominator:

| Metric | Numerator / denominator |
|---|---|
| Source attribution | Claims with attributable source / eligible claims |
| Actual capture availability | Claims with an actual verified digest-bearing capture / eligible claims |
| Occurrence confidence | Claims with supported acquisition event/time, separately exact/bounded/unknown / eligible claims |
| Exact locator coverage | Claims with a validated locator into that representation / eligible claims |
| Replay success | Sampled eligible claims reproduced by pinned extractor / sampled claims attempted, with unavailable cases retained |
| Semantic fidelity | Adjudicated sampled claims supported at claimed type/role/scope/precision / sampled claims adjudicated |
| Publication eligibility | Eligible claims passing current authorized policy / candidate public claims, with exclusion reasons |
| Legacy/demo exposure | Current public assertions deriving only from seeded/transcribed material / public assertions |

Metrics do not collapse into a single trust score. Provenance strength and source factual reliability are independent: perfectly preserved bytes can contain a false assertion.

### Cost model and operating limits

- Metadata inventory is O(claims + bindings + capture index). Use batched scans and indexes, process near the database, and record SQL plans before hosted application. Avoid per-row remote calls.
- Exact-byte audit cost is total size of distinct sampled captures, not number of claims. Deduplicate retrieval by digest; read a capture once per batch. Initial pilot ceilings: 2 GiB read, 40 claims, one worker, 30 minutes; stop and report before exceeding. Operator can expand after actual cost is known.
- Recovery batches default to at most 10,000 assertions or 250 MiB of distinct input bytes, whichever occurs first, one worker on the small hosted tier. These are proposed conservative controls, to be measured locally and confirmed before hosted use.
- New storage grows with actual sightings/bindings, not just distinct claims. The P31.7 measured 210.9 bytes/link is a historical measurement of the old narrow row, not a reliable estimate for locator-rich bindings. Benchmark 10k/100k realistic rows with indexes and TOAST; project 12 months from measured cadence and actual DB disk/headroom. Warn at projected 70% capacity; require a disposition before projected 85% or any batch with less than 20% free headroom.
- Metadata sidecars can grow per identical-byte retrieval even if raw blobs dedupe. Track occurrence metadata and object-version growth independently, and avoid duplicating long excerpts across every field of a capture.
- P31.4's scheduled OSM run is not an excuse to run a second full acquisition. Use captured replay or the next authorized cadence and preserve its outcome as a separate calendar-owned verification.

## 7. Measurable acceptance criteria and negative tests

The implementation tickets should select the applicable rows, not duplicate the whole suite in every unit. Real PG tests are required for temporal visibility, immutability, constraints, RLS and crash recovery; pure tests suffice for mapping/comparability. No green from skipped DB tests.

| ID | Acceptance / negative case |
|---|---|
| AC-E1 | A JSON row and PDF/text claim persist actual capture digest/version, exact locator, extractor/config version and literal digest. An independent offline verifier reproduces the value; absent/wrong digest, malformed locator and version mismatch fail with an explicit disposition. |
| AC-E2 | Identical bytes fetched twice produce one blob and two acquisition occurrences; the original occurrence metadata never reads the second event's head sidecar. One occurrence with multiple valid locators remains representable and idempotent. |
| AC-E3 | Supplied tier/rights/valid-time/raw-context/normalization/qualifiers survive sink roundtrip. Unsupported or inconsistent metadata fails closed; a tier-2 input cannot land as tier 0. Old legacy input is accepted only through an explicitly classified compatibility path, not silently upgraded. |
| AC-T1 | A→B→A at different dates and within one day yields A in current API, materialized resolution and camera selection; a past-belief query between B and final A yields B. Binding added later to an old capture does not appear in earlier belief. |
| AC-T2 | Replaying old bytes creates a new extraction/knowledge event but not a fresh source observation; both new and duplicate replayed claims use original acquisition time. Contradicts/background bindings never refresh a source assertion. |
| AC-T3 | Latitude and longitude correction snapshots never form a hybrid point. Recurrent input state produces a new execution completion pointing to the correct existing result. Unknown-date/legacy-binding uncertainty is visible and never guessed. |
| AC-S1 | OSM publisher target emits publisher provenance, not an operator organization claim unless an explicit row/source-wide operator assertion exists. Unknown operator stays unknown. Two unrelated identical-name agencies remain separate candidates; identical verified external IDs resolve together; a national vendor may span jurisdictions. |
| AC-S2 | A source notice remains a notice/contract record even when it mentions cameras; procurement does not prove deployment. Captured news discussing a contract remains news unless a separate contract capture is bound. No extra independent corroboration from mirrors or renamed source-family labels. |
| AC-C1 | Metro 299 and city approximately 190 are not a genuine comparable contradiction. Approximate 190 names the two input claims and assumptions. Different count basis, population, time window, uncertainty or unknown boundary produces reasoned non-comparability/unknown, while an explicit same-scope incompatible pair still produces a contradiction. |
| AC-P1 | A publication-review-required organization cannot be recovered through label, alias, raw literal, claim API, search/facet, graph path, tile, PROV or download. A reviewed safe disposition changes the allowed surface consistently; denied cases are covered under public-role RLS and privileged-role projection tests. |
| AC-P2 | Restricted original plus safe derivative exposes only authorized derivative bytes/locator and minimized metadata. Sealed original, sensitive URL/query/header, suppressed cell and revoked/publication-withheld fact do not reappear in historical endpoints or stale caches. |
| AC-P3 | A rights decision cannot silently relicense already-resolved claims; each artifact retains its compartment. Historical epistemic requests still obey current public suppression. No person entity is created by automated extraction. |
| AC-R1 | Interrupted recovery resumes without duplicate claims/bindings, partial commits remain attributable, changed input digest refuses stale repair, missing bytes yield an owned disposition, and re-run inserts zero new rows. No claim/old ADR/history is rewritten. |
| AC-R2 | Metrics use declared denominators and separately count source-only, exact capture, locator and replay statuses. Synthetic zero-byte run records never score as verified original captures. A legitimate empty response is not falsely classified synthetic solely by size. |
| AC-R3 | Two independent replay runs on pinned inputs/config produce identical assertion projections and lineage digests after excluding only explicitly nondeterministic execution identifiers; public eligibility/correction differences are explained by named decisions. |

The negative suite must contain new, purpose-built synthetic cases, clearly excluded from production. The historic OKC example stays a regression case for non-comparability, not a requirement to preserve a misleading current contradiction.

## 8. Candidate implementation units and P31 ownership boundaries

These are coherent candidate units, not final ticket numbers. Root planning owns sequencing, IDs, ADR allocation and final contracts.

| Unit | Concrete deliverable | Dependencies and verification | Boundary |
|---|---|---|---|
| Integrity census and truthful metrics | Read-only inventory CLI/report schema; synthetic/actual/unknown classification; split provenance metrics; dry-run exposure report for seeds and name-only orgs | P31 final schema; fixtures plus bounded snapshot profiling; AC-R2 | No live repairs or new rights. May expose current facts before further deployment. |
| Typed capture-to-claim persistence | Versioned input envelope, actual occurrence/version/locator binding, lossless supported metadata mapping, additive schema/digest compatibility | Census; new ADR/sqitch; real PG AC-E1–E3 and crash tests | Extends P31.3/4/7 plumbing without replacing batching/resume. |
| Unified temporal evidence selection | Shared belief/observation/role-aware readers; replay dating; paired coordinates; recurring-result completion; context/caching watermarks | Typed bindings; AC-T1–T3 across API/materializer/export | P31.7 latest dating is prerequisite; P31.11 review/cluster decisions remain intact. |
| Semantic source/entity boundaries | Publisher/operator adapters, source-record types, explicit source-wide role evidence, conservative source-scoped name candidates and stable-ID links | Typed envelope; audited connector families; AC-S1/S2 | Does not duplicate P31.8 predicate registry expansion or P31.12/13 acquisition adapters. |
| Qualified counts and seeded correction | Measurement qualifiers, comparability classifier, approximate derivation, seeded-origin/current-disposition views, corrected OKC presentation proposal | Typed qualifiers; temporal selection; AC-C1; append-only correction fixtures | No fabrication of a genuine contradiction; integrates with local-dossier stream's evidence acquisition. |
| Shared publication and safe evidence projection | Review/disposition gate across all public paths, metadata minimization, redacted locator binding, policy watermark invalidation | Existing officer/tier/rights safeguards plus new decisions; AC-P1–P3 | D-P31.5-2 is already owed to P31.16. Reconcile ownership: implement there if still open, or prove its closure and extend only missing surfaces. |
| Bounded recovery and semantic remediation | Offline candidate binding/replay tool, versioned repair manifests, dry-run impact diff, idempotent resume, gated hosted apply | Previous units; AC-R1; sampled independent review | Live write/capture/republication are separate gated stages. Unknown evidence stays unknown; original IDs survive. |
| Independent acceptance audit and release contract | Reproducibility protocol executed by a separate reviewer, stratified outcomes, release trust manifest and safe corrections/citation map | Recovery rehearsal, publication projection; AC-R3 plus all high-impact negatives | Public release only with applicable sign-off; no declaration of human ground truth or legal clearance. |

P31.8 is actively closing registry coverage and must be allowed to finish independently. P31.9 owns peer classes; P31.10/11 own review-to-clustering wiring; P31.14/15 own presentation analytics and tiles; P31.16 owns the planned gated refresh; P31.19 owns the current tail sweep. S1 should land after rebasing onto their accepted final seams or through an explicitly coordinated boundary integration. None of these proposed units should close existing deferrals merely because it writes a design.

The human resolution-evaluation campaign remains the evaluation stream/Round 10. S1 supplies reliable evidence packets, source lineage and temporal truth for that campaign; it does not substitute agent labels for human adjudication.

## 9. Proposed normative requirement ideas

Provisional semantic IDs below are suggestions for root's SIG-TRUST namespace; not an allocation in the canonical spec yet.

| Proposed ID | Normative intent | Trace to finding / acceptance |
|---|---|---|
| SIG-TRUST-EVID-BIND | Every new production assertion MUST bind to an actual capture occurrence and a representation-specific locator, or carry an explicit non-captured/manual/legacy classification that cannot pass exact-evidence metrics. | F1/F2; AC-E1/E2/R2 |
| SIG-TRUST-META-PRESERVE | Supported typed metadata MUST survive parser→sink→reader; unsupported or conflicting protection/time/type metadata MUST fail closed rather than default to a more public or more certain value. | F1; AC-E3 |
| SIG-TRUST-TIME-CONTEXT | Historical reads MUST select evidence by both system knowledge and source observation context; replay and derivation MUST NOT be presented as new source observations. | F4; AC-T1/T2 |
| SIG-TRUST-RECORD-ROLE | Source publisher/custodian and record type MUST remain distinct from asserted operator/owner/deployment type; semantic conversion requires cited evidence and a versioned rule. | F3; AC-S1/S2 |
| SIG-TRUST-COUNT-SCOPE | Count comparisons MUST prove population, geography, basis, unit, time and uncertainty compatibility, and preserve approximation/derivation; unknown compatibility MUST NOT become value disagreement. | F5; AC-C1 |
| SIG-TRUST-DISPOSITION | Corrections, identity splits, retractions and publication restrictions MUST be attributable append-only decisions honored consistently by all public read paths and derived outputs. | F5/F6; AC-P1/R1 |
| SIG-TRUST-PUBLIC-EVIDENCE | Evidence preservation MUST NOT imply public access; redacted derivatives and public metadata MUST obey current authorized controls, including on historical queries and immutable citations. | F6; AC-P2/P3 |
| SIG-TRUST-REPLAY-MEASURE | Evidence-quality claims MUST name their denominator and distinguish attribution, bytes, occurrence, locator and replay verification; independent sampled verification MUST accompany a release claiming reproducibility. | F2; AC-R2/R3 |

Suggested canonical homes: §16 claim/evidence binding and append-only corrections; §17 acquisition/OCFL/redaction; §21/24 connector-parser contract; §14 identity semantics; §28 temporal resolution; §29 count comparability; §37–39 reader/export/citation consistency; Part VIII current publication protection. Use a new ADR for changed decisions; preserve prior ADR bodies, append traceability, regenerate the spec only through the corrected isolated-worktree builder.

## 10. Remaining decisions and honest limits

- Which legacy evidence grades may remain public with explicit disclosure, and which require withholding until reviewed, is a concrete publication-policy decision. Prepare the actual affected-row report first; do not ask for blanket approval in the abstract.
- Recovery quality, the number of affected public operator claims, global-name collisions and missing historical capture coverage are not measured by this planning pass. Their census/audit is deliverable one, not assumed evidence for implementation success.
- Effective rights and current public suppression must be distinct from historical belief. Legal/rights decisions require their existing authority; no standards citation decides them.
- A v2 digest and source-record identity contract must preserve old IDs and support multi-valued predicates/qualified assertions; do not reuse one-value-per-source supersession for sets or distinct count populations.
- The proper initial success criterion is a small, independently reproducible set of real investigative paths plus honest corpus-wide integrity metrics. Large row counts, many green tests and valid RDF alone do not establish semantic correctness.

## Independent-review correction — semantic metric denominator

The conditional semantic-fidelity row above must never be displayed alone. The final contract reports (a) supported at claimed type/role/scope/precision divided by **all sampled eligible claims**, with unresolved units counted as not established; (b) conditional fidelity among adjudicated units; and (c) adjudication/labelability yield. Stratification weights and clustered uncertainty apply to each appropriate estimand. This prevents missing evidence from improving a headline fidelity percentage by leaving its denominator.
