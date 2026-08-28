# Risk register

Per §53 / SIG-ENG-031, each phase updates this register. Unverifiable
requirements (SIG-ENG-005) are recorded here with their compensating control.

## Phase 0 — Foundations, governance, ecosystem coordination

### Legal items referred to counsel before launch (SIG-LIC-009)

These are decisions the executable policy cannot settle; they are flagged so
they are resolved before launch, not discovered after.

| id | Item | Compensating control until resolved |
|---|---|---|
| RISK-P0-01 | Whether API responses returning device-linked claims constitute distribution of a Derivative Database under ODbL clause 4.4(b) | OSM-derived data kept in its own ODbL compartment (ADR-011); export gate fails closed on unresolved rights (SIG-LIC-004) |
| RISK-P0-02 | Whether OSM-sourced jurisdiction geometry contaminates the operator property under the Collective Database guideline | Conservative reading governs; `upstream_license` provenance can force the stricter compartment (SIG-LIC-009a) |
| RISK-P0-03 | The correct regional-cut unit for substantiality | Documented as open; systematic ~144k-feature extraction treated as substantial by default |
| RISK-P0-04 | EU sui generis database right for the international phase | Deferred to the international phase; not triggered by the initial US-scoped corpus |

### Unverifiable-by-automation requirements (SIG-ENG-005)

| id | Requirement | Why not automatable now | Compensating control |
|---|---|---|---|
| RISK-P0-05 | SIG-PUB-008 two-reviewer *concurrence itself* (the human judgement) | The written human concurrence is agentic, not deterministic | The **gate** around it is deterministic and tested (`test_policy_officer.py`): no publish without two independent, written, concurring reviewers |
| RISK-P0-06 | SIG-INGEST-037 no-circumvention as a *legal posture* | "Requires counsel" is a process fact, not a unit test | `assert_no_circumvention` fails closed on the enumerated techniques; deviation is an ADR-level decision |
| RISK-P0-10 | SIG-GOV-014/015/016 governance, Code of Conduct, editorial board, and funding policy | Adopting and *operating* prose governance (a real board, real enforcement) is agentic, not a unit test | The documents are published and link-checked (`test_governance_docs.py`); the deterministic officer-naming gate (`test_policy_officer.py`) is the board's enforced counterpart |
| RISK-P0-11 | SIG-CONTRIB-007/008 know-your-rights guidance and the detained-contributor policy | Correctness of jurisdiction-aware legal guidance is agentic and needs counsel review | Policy published and presence-tested (`test_governance_docs.py`); guidance flagged for counsel review before launch |
| RISK-P0-12 | SIG-GOV-021 degraded-but-alive mode is *tested* (incl. dormant-scheduler keepalive) | The keepalive + its test are built in the operations phase, not P00.3 | Posture documented now (`docs/governance/governance-and-code-of-conduct.md`); the executable test is a tracked deliverable of the ops phase |

### Legal / launch prerequisites (human, not code)

| id | Item | Compensating control until resolved |
|---|---|---|
| RISK-P0-13 | SIG-GOV-012 legal home (fiscal sponsor or nonprofit) established before public launch | Tracked as a launch-blocking prerequisite; no public launch without it |
| RISK-P0-14 | SIG-GOV-013 legal-defence resources identified *before* needed | Identified during Phase 0 outreach; referenced by the contributor-safety detained/arrested policy |

### Ecosystem / operational

| id | Risk | Mitigation |
|---|---|---|
| RISK-P0-07 | Bulk-export egress cost becomes existential (§38.5) — "success is the failure mode" | ADR-015: CloudFront caching + torrent/IPFS offload + low-egress mirror; egress-budget alarm is the ADR's revisit trigger |
| RISK-P0-08 | An ecosystem project's unauthenticated audit dump enables the de-pseudonymisation join (§43.2a) | SIG never ingests per-search operator rows; operator ids hashed with a held-back salt; no operator-joinable surface (`policy.publication`) |
| RISK-P0-09 | Vendor/agency takedown pressure (already observed against a peer project) | Rigorous provenance; conservative crawler conduct (§26); corrections/takedown path owned by P00.3 |

### Source registry (P00.4)

| id | Risk | Mitigation |
|---|---|---|
| RISK-P0-15 | Unverified §22.6 rows targeted by a connector before their access/rights are re-checked (SIG-INGEST-038) | `ingestion_permitted` defaults false and is a tested runtime gate (`test_ingestion_gate.py`); a row stays inert until a reviewer re-verifies it and flips the flag; `verified` records the 2026-08-20 research-pass state per row |
| RISK-P0-16 | A source's rights are unresolved at seed time and content leaks to export (SIG-LIC-001/004) | Unresolved rows are `UNDETERMINED` + `redistributable=false` and fail the export gate closed, proven over the live seed (`test_registry_export_gate.py`); `redistributable` is never derived from the licence string (SIG-INGEST-024) |
| RISK-P0-17 | The Eyes on Flock public API is a single point of failure for the only lawful route to the portal layer (SIG-INGEST-030a/031) | Documented fallbacks retained (records acquisition, contributor captures, partner archives); archival-succession offer (SIG-CONTRIB-013) is a Phase-0 deliverable; a challenge-defeating crawler is explicitly out of scope and MUST NOT be added |
| RISK-P0-18 | AGPL-3.0 upstream code (`sm-alpr`, `deflock-app`) linked into SIG's Apache-2.0 codebase (SIG-INGEST-048b) | Registered with `derivative_permitted=false` and a licence-hazard note; methods may be studied, code MUST NOT be linked; tested (`test_source_registry.py::test_agpl_projects_are_marked_non_derivative_licence_hazards`) |

### Unverifiable-by-automation requirements (SIG-ENG-005) — P00.4

| id | Requirement | Why not automatable now | Compensating control |
|---|---|---|---|
| RISK-P0-19 | SIG-LIC-001 per-source rights *review* (which SPDX, whether redistributable) | Reading each source's terms and judging redistributability is agentic, not a unit test | The registry *shape* is enforced (rights populated-or-`UNDETERMINED`, fail-closed export gate); the review itself is a tracked, per-row research task, `UNDETERMINED` until done |
| RISK-P0-20 | SIG-INGEST-030 Eyes on Flock partnership / archival-succession *outreach* | Conducting and concluding outreach is agentic (§22.5) | Access is resolved under public CC-BY-SA terms and the Stage-0 outcome is recorded on the row; partnership/succession outreach flagged as a remaining Phase-0 deliverable (SIG-INGEST-030a/032) |

## Phase 1 — Ontology as code + vocabularies (P01.1)

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P1-01 | **Ontology churn** — the schema, vocabularies, DDL, and docs drift apart, and a taxonomy written in 2026 silently rewrites the meaning of past claims (§20) | One LinkML source of truth (ADR-007) generates all five downstream forms plus SKOS; a deterministic CI gate fails if any committed artifact differs from a fresh generation (`make verify-gen`, `test_generation_gate.py`). Vocabularies publish as versioned SKOS at stable per-version IRIs (SIG-STORE-035) and are immutable once published (SIG-STORE-036), so later change is a versioned migration, not an edit. |

### Unverifiable-by-automation / scaffolded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P1-02 | SIG-STORE-039 (published crosswalks to *every* external taxonomy SIG ingests) | The full, curated crosswalk to each live external vocabulary is a research task that grows as connectors land (P04+) | The crosswalk *mechanism* is built and tested: many-to-many rows with a SKOS mapping relation and a `lossy` flag, seeded for the six §20.3 taxonomies (`vocab/crosswalks.yaml` → `generated/skos/crosswalks.nt`). Completeness is a tracked per-connector deliverable. |
| RISK-P1-03 | SIG-EPIS-017 (the full genre × predicate directness matrix) | The complete matrix is owned and consumed by the reconcile ruleset (P08); it is calibrated against real evidence | Each predicate carries a full directness *row* over the published §10.5 artifact genres (SIG-ONTO-067, tested); the matrix predicates use the published §10.5 values, others a conservative default, completed in P08. |
| RISK-P1-04 | SIG-RECON-009 (volatility half-lives recalibrated once change-rate data exists) | Half-lives are an initial assignment until SIG has measured change rates | Initial per-predicate volatility + half-life from §28.3 are registered and tested; recalibration is a ruleset-data change in a later phase, not a schema change. |

## Phase 2 — The bitemporal claim and evidence spine (P02.1)

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P2-01 | **Risk 3 (§51.2) — a claim/temporal model that cannot express contradiction** (part) | The physical claim spine makes the defining-standard invariants *physically enforceable*, not aspirational: `claim` is append-only (DB trigger + role-level DELETE revocation, SIG-STORE-011/012), corrections are new assertions that preserve prior belief in transaction time (SIG-STORE-020, proven by `test_corrections.py`), and `resolution` is a stored decision record whose `contradiction_state='unresolved_conflict'` is a first-class publishable outcome (SIG-STORE-015) with at-most-one current value per (subject, predicate, valid instant) enforced by a GiST exclusion constraint (SIG-STORE-016, `test_resolution_exclusion.py`). The remaining part of Risk 3 (as-of query functions, EDTF envelope derivation, PROV-O export) lands in P02.3; the evidence-store bytes land in P02.2. |

### Deviations recorded as ADRs (SIG-ENG-031)

| id | Deviation | ADR |
|---|---|---|
| RISK-P2-02 | `claim` is not physically partitioned by `observed_at` (§16.2 design point 6): a single-column `claim_id` PK — required because it is the universal FK target — is incompatible with partitioning by a nullable column in PostgreSQL. The FK contract is retained; partitioning is deferred. No acceptance criterion depends on it. | ADR-022 |

### Unverifiable-by-automation / scaffolded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P2-03 | SIG-STORE-018 (a CI job regenerates a sample of resolution rows from their stored inputs and asserts they match) | Resolution *recomputation* needs the resolver, which is P08.1 (`reconcile`); this ticket provides the table + constraints only | The resolution *shape* — stored inputs (`considered_claims`, `dissenting_claims`, `strategy_id`, `ruleset_version`, `resolver_version`), the exclusion constraint, and independent versioning — is built and tested; the determinism rebuild job is a tracked P08.1 deliverable. |
| RISK-P2-04 | SIG-STORE-045 (shipped DDL generated from the LinkML ontology) | Partitioning, triggers, RLS, and exclusion constraints are not expressible in LinkML; the physical enforcement layer is authored DDL that this ticket explicitly owns | The claim spine is authored as sqitch migrations (SIG-STORE-041) and the ontology remains the source of truth for the *logical* schema, vocabularies, and the predicate registry the DDL and its tests consume (`test_schema_integrity.py` reads the generated predicate registry). Reconciling the generated logical projection with the physical schema is tracked for the ontology/db seam. |

## Phase 2 — The bitemporal claim and evidence spine (P02.2 — the OCFL evidence store)

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P2-05 | **Loss of the raw evidentiary record** — snapshots that are mutable, unverifiable, or unreadable without SIG's software (§17.1 E1/E2/E5) | Evidence bytes are content-addressed (multihash, `evidence.digest`, SIG-EVID-002/003/004) and written write-once into an OCFL 1.1 root (`evidence.ocfl`, SIG-EVID-005) whose `inventory.json` resolves version→digest→path with no SIG code (proven by `test_ocfl.py::test_object_readable_without_sig_code`). Production storage is S3 with versioning + **governance-mode** Object Lock and a documented default retention (`evidence.storage`, SIG-EVID-006, `test_storage.py`), so a lawful takedown (§45) stays satisfiable. |
| RISK-P2-06 | **Source disappearance treated as an error, not a datum** (§17.6; R11 top-5 operational risk) | Disappearance is recorded as an event on the artifact (`disappeared_observed_at` + failing status) and never a delete, and it generates a `source_disappeared` research task (`evidence.disappearance`, SIG-EVID-013/014, `tests/db/test_evidence_store.py::test_disappearance_is_an_update_not_a_delete`). A link-rot sweep re-checks on a volatility-proportional cadence with Wayback registration for permitted public artifacts (SIG-EVID-015). |

### Deviations recorded as ADRs (SIG-ENG-031)

| id | Deviation | ADR |
|---|---|---|
| RISK-P2-07 | A new top-level `evidence/` package is added beyond the frozen §47 layout (SIG-ENG-012): §17 needs a connector-facing home and §47 names none. Registered as an ADR-sanctioned workspace member (`tests/support.py::ADR_EXTENSION_PACKAGES`). | ADR-023 |
| RISK-P2-08 | The P02.1 `evidence_capture UNIQUE (content_digest, artifact_id)` is dropped and dedup uniqueness moved to `evidence_blob (blob_digest, source_uri)`: the P02.1 constraint blocked SIG-EVID-004's "one blob, N capture rows". Done as a new sqitch change, never an in-place edit (SIG-STORE-042). | ADR-023 |

### Unverifiable-by-automation / scaffolded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P2-09 | SIG-EVID-007/008 (live WACZ capture of a JS-rendered portal with a real browser) | End-to-end capture needs a headless browser + a live source; running one per PR is slow, flaky, and hits third-party sites | The capture-set contract and the deterministic WARC→WACZ 1.1.1 packager are built and tested from fixtures (`evidence.capture`, `test_capture.py`); the real Playwright capture path (`capture_live`) ships behind the `capture` extra and is exercised by the connectors (P04+), mirroring how the DB tests gate on Docker. |
| RISK-P2-10 | SIG-EVID-017 (a CI test asserts re-running a pinned connector over pinned digests yields byte-identical claim tuples modulo `claim_id`/`sys_period`) | The connector that produces claim tuples is P04+; this ticket owns the evidence side | The reproducibility *machinery* is built and tested: a deterministic environment (`LC_ALL=C`/`TZ=UTC`, SIG-EVID-018), an `ingest_run` record of all reproducibility inputs (SIG-EVID-016), and the canonicalisation the CI test compares (`evidence.ingest_run.canonical_claim_tuple`, `test_ingest_run.py`). Deterministic packaging is proven (`test_capture.py::test_wacz_packaging_is_deterministic`). |

## Phase 2 — The bitemporal claim and evidence spine (P02.3 — temporal semantics and provenance)

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P2-11 | **Risk 3 (§51.2) — a claim/temporal model that cannot express contradiction and uncertainty** (final part; the P02.1 entry RISK-P2-01 retired the append-only/correction/resolution spine). The remaining exposure was that time and provenance were stored but not yet *queryable or invariant-checked*: imprecise dates could silently sharpen, an `ongoing` edge could read as "true now", a past citation might not reproduce, absence states could collapse to NULL, and lineage had no interoperable export. | EDTF Level 1 stays imprecise with a **pinned, deterministic** envelope (`db.edtf`, ADR-024; `"early 2025"` never becomes `2025-01-01`, `test_edtf.py`). `ongoing` is rendered only with its observation date and never as "currently" (`db.temporal`, SIG-TIME-005, `test_temporal_semantics.py`). The two as-of axes ship as `claim_as_of`/`resolution_as_of`, and a belief-pinned query reproduces a corrected-away value (`tests/db/test_as_of.py`, SIG-TIME-009). The four absence states render distinguishably (`db.absence`, `test_absence.py`). TI-1..TI-8 are enforced as pipeline data-quality checks with property tests (`db.invariants`, `test_temporal_invariants.py`, SIG-TIME-013/014). Lineage exports as validated PROV-O (`exports.provo`, SIG-INGEST-016, `test_provo.py`). |

### Deviations recorded as ADRs (SIG-ENG-031)

| id | Deviation | ADR |
|---|---|---|
| RISK-P2-12 | The EDTF `tstzrange` envelope is derived by an in-repo, stdlib-only, version-pinned function (`ENVELOPE_RULESET_VERSION`) rather than a third-party EDTF library, so the widening policy is deterministic and auditable; EDTF Level 2 is not yet supported. | ADR-024 |
| RISK-P2-13 | TI-1..TI-8 are enforced as pure pipeline data-quality checks (complementing the P02.1 physical constraints) rather than all as DB constraints, and the as-of contract ships as SQL functions plus a Python predicate builder. Explicitly permitted by SIG-TIME-013 ("DB constraints OR run-failing data-quality checks"). | ADR-025 |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P2-14 | SIG-TIME-005/012 also bind the **API and UI** rendering surfaces (`ongoing` with observation date; four absence states distinguishable) | The read API (`api/`, ADR-017) and the web UI (`web/`, ADR-014) are later phases; this ticket owns the shared rendering + query contract they consume | The conformant renderings and the distinguishable absence presentation are built and tested here (`db.temporal.render_valid_bound`/`assert_conformant_rendering`, `db.absence.render_absence`); a non-conformant "currently …" rendering is rejected in code, so the API/UI wire to a contract that already fails closed. |
| RISK-P2-15 | TI-6 (mutually-exclusive resolved intervals) and TI-7 (supersedes-chain acyclicity) as **whole-graph** guarantees | The pipeline checks (`db.invariants.check_ti6/7`) see only the batch a connector hands them; the resolver (`reconcile`, P08.1) and a nightly full-graph audit own the cross-batch view | Same-predicate L3 overlap is already a hard DB constraint from P02.1 (`resolution_no_overlap`); the batch checks catch within-run breaches now; the full-graph audit is a tracked P08.1 / nightly deliverable (§48). |

## Phase 3 — Identity registry and deterministic ER (P03.1)

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P3-01 | **Risk 2 (§51.2) — bad entity resolution makes every network statistic misleading** (first part; the deterministic cascade and probabilistic matcher land in P03.2 / P05). The exposure this half closes: an unstable identity substrate — GEOIDs stored as integers or without a level, a municipality conflated with its police department, a rename silently minting a new identifier and fragmenting an entity's history, an agency centroid used as a device location, or a silent-zero ingest quietly poisoning coverage. | The substrate is now enforced in code (`resolution/`): GEOIDs are fixed-width strings validated against an explicit level (`resolution.geoid`, SIG-IDENT-005); a municipality and its department are distinct organizations joined by a reified `parent_of` relation (`resolution.temporal_identity.municipality_department_pair`, SIG-IDENT-009); a pure rename produces a new version + dated alias and provably **no** succession relation and **no** new identifier (`resolution.temporal_identity.rename_organization`, SIG-IDENT-017, with the five worked succession fixtures, SIG-IDENT-019); an agency centroid is stamped `organization_centroid_or_unknown` and refused for point-in-polygon and address use (`resolution.geometry_precision`, SIG-IDENT-004); a zero-record ingest fails the run and distinguishes absent from not-observed via the P02.3 four-state model (`resolution.registry_ingest`, SIG-IDENT-008); identifiers are sets of `(scheme,value)` (SIG-IDENT-006); and jurisdiction geometry is temporally versioned so a point's containing jurisdiction is evaluated as of its observation date (`resolution.jurisdiction.boundary_as_of`, SIG-ONTO-011). |

### Deviations recorded as ADRs (SIG-ENG-031)

None. The seven-value `OrganizationRelationType` and the `GeometryPrecision`
vocabularies are **additive** to the LinkML source of truth (§20.1, ADR-007) — new
controlled vocabularies §14 already mandates — and the physical registry tables
(App C.4 `jurisdiction`/`organization`/`organization_relation`/`entity_identifier`)
were shipped verbatim in P02, so no schema change and no design deviation was
required. The canonical DDL's free-text `relation_type` / `status` columns are kept
as-is (vocabulary is enforced in the ontology + `resolution/`, not by a CHECK the
canonical DDL deliberately omits).

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P3-02 | SIG-IDENT-010 (the two classification axes) draws `operating_relationship` from a vocabulary | Rather than mint a competing enum, the relationship axis reuses the existing fourteen-role `Role` vocabulary (§12.4) — "purchaser but not operator" is a role over a specific deployment (`entity_role`), materialized when connectors assert roles in P04+ | The axes and their independence are modelled and tested now (`resolution.identity.TwoAxisClassification`); a conformance test grounds `organization_class` in `OrganizationType` and `operating_relationship` in `Role` (`test_vocab_conformance.py`), so the two-axis contract is fixed even though role edges are populated later. |
| RISK-P3-03 | Persisting registries and minting surrogate `entity_id`s end-to-end into Postgres | The registry-*ingest* orchestration (reading Census/FBI-CDE/IPEDS/… and writing entities + claims) is a connector concern (P04+); this ticket owns the identity model, the guards, and the row/claim emitters | The domain layer emits table rows (`Organization.to_row`, `OrganizationRelation.to_row`) and enforces every guard as pure, tested logic, and the physical layer is exercised against a real PG18+PostGIS via `tests/db/test_identity_registry.py`; surrogate minting is deterministic and idempotent (`resolution.identity.mint_surrogate`). Public `sig:` identifier minting, `normalize_org_name()`, the crosswalk, and the deterministic cascade are P03.2. |
| RISK-P3-04 | The legacy `Organization.succession` / `SuccessionKind` slots (P01.1) coexist with the reified `OrganizationRelation` | The reified, bitemporal relation is the authoritative model for organizational change (SIG-IDENT-016); the older per-entity slots predate this ticket and are retained additively for back-compat | New temporal-identity edges are written only as `organization_relation` rows with the seven-value vocabulary; the reified model is the one the fixtures and the physical test assert, and it is where later phases read succession from. |

## Phase 3 — Identity registry and deterministic ER (P03.2 — deterministic cascade, normalisation, public identifiers)

P03.2 closes the deterministic half of Risk 2 (§51.2): the explainable,
auto-writing tiers of entity resolution now exist in code and every auto-merge is
traceable. No schema change and no design deviation was required — the cascade,
the name normaliser, the crosswalks, and public-identifier minting are pure,
versioned, tested domain logic in `resolution/`; the crosswalk exports reuse the
existing P00.2 licence gate (`policy.licensing`). The one dependency added is
`sig-resolution → sig-policy` (the export gate), recorded in `resolution/pyproject.toml`.

| id | Item | Status / compensating control |
|---|---|---|
| RISK-P3-05 | **Risk 2 (§51.2) — the deterministic half.** An unexplainable or over-eager auto-merge silently corrupts every downstream network statistic. | Tiers 0–3 are the only auto-writing path and each records `match_tier` + `match_evidence` (`resolution.cascade`, SIG-IDENT-025); a civil/applicant ORI is refused as a sole basis (SIG-IDENT-003); Tier-2 name+state+class is gated by a data-generated collision exclusion list; blocking-only address keys K3/K4 can never be identity evidence (`resolution.address`, SIG-IDENT-013). Probabilistic tiers 4–5, the gold/holdout set, cluster-shape alerts, and auto-demotion are P05.1. |
| RISK-P3-06 | **The public-identifier stability contract (SIG-IDENT-032)** — the one failure that would poison every downstream citation is a `sig:` id silently reassigned to a different entity. | `resolution.public_id.PublicIdRegistry` makes every split/merge an explicit dated event with `redirects_to`/`split_into` pointers and tombstones; a split source is provably never reused as a successor and a tombstoned id can never be re-registered; a merged-away id redirects (transitively) to its survivor. Verified by a simulated split and merge (`tests/resolution/test_public_id.py`). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P3-07 | SIG-IDENT-002 UCR↔USPS table and the SIG-IDENT-033/034 crosswalk *content* | This ticket owns the *machinery* (the reference table, the export builders + licence gate), not the full national code table or the populated crosswalk rows, which a connector run (P04+) fills. | The table ships with the mandated divergences (NB→NE, GM→GU) and passes-through the identical majority; the export builders validate every ORI/GEOID and fail the build on a malformed row; publishing goes only through the licence gate (`export_crosswalk` → SIG-LIC-004). Populating rows end-to-end is a connector concern. |
| RISK-P3-08 | SIG-IDENT-031 dereferenceable `/id/<type>/<uuid>` HTTP endpoint + rendered HTML/JSON-LD/RDF representations | The URL construction and the content-negotiation *decision* are owned here as pure logic; the live HTTP route and the serialisers that render each representation are an API-surface concern (P07+ delivery). | `dereference_url` and `negotiate` are deterministic and tested; the representations they select (`html`/`json-ld`/`rdf`) are wired to real responders when the public API ships. |
| RISK-P3-09 | The Tier-2 collision list and the acronym/normalise ruleset are seed data, not the full data-generated corpus | The spec calls the collision list "data-generated"; here it is a versioned seed exclusion set with the correct shape and injection seam (`CascadeContext`), regenerated from the corpus in a later data pass. | Rulesets are versioned data (`data/*.toml`) with committed test vectors that run in CI (SIG-IDENT-022); changing what auto-writes is a reviewable data diff, and `CascadeContext.from_data()` is overridable so a regenerated list drops in without code change. |

## Phase 4 — Connector framework, OSM, Atlas (P04.1 — the connector framework)

P04.1 builds the reusable eight-stage substrate every source adapter plugs into
(§21). It writes no source-specific connector (OSM/Atlas are P04.2/P04.3) and
reuses the existing evidence store (captures, `ingest_run`, disappearance),
`policy` (licensing + crawler conduct), `resolution` (the `link()` cascade), and
the `exports` PROV-O projection — so it adds a stage contract and wiring, not new
domain logic. One deviation ADR was written (ADR-026: fetch-only egress +
socket-level network-isolated replay + the `CaptureStore` seam). Dependencies
added: `sig-connectors → sig-evidence, sig-resolution, sig-exports` (none depend
back — no cycle), recorded in `connectors/pyproject.toml`.

| id | Item | Status / compensating control |
|---|---|---|
| RISK-P4-01 | **Replay reproducibility (SIG-INGEST-017/018).** A parser change that silently alters claims, or a replay that accidentally re-contacts a source, corrupts history or hammers an upstream. | Replay runs the post-capture stages under socket-level `network_isolated` (any egress raises and fails the run) and reads captures back by digest; byte-identical modulo `claim_id`/`sys_period` is asserted over `claim_set_fingerprint` (`tests/connectors/test_replay.py`). |
| RISK-P4-02 | **Silent egress after capture (SIG-INGEST-002).** A post-capture stage that reaches the network breaks the purity guarantee replay depends on. | `connectors.isolation` blocks sockets below any HTTP client; the driver runs every post-capture stage inside it on live runs *and* replay; a leaky-parse connector is proven to fail the run. |
| RISK-P4-03 | **A connector running against a source it may not (SIG-INGEST-014/028, SIG-LIC-010).** Ingesting without permission, or exporting incompatible licences merged together, is a legal error. | `connectors.loader.assert_loadable` gates on ingestion_permitted + compact_status + custody_posture *before any fetch*; `assert_export_compatible` delegates to `policy.licensing.compute_export_license` so mixing incompatible compartments fails the build (`connectors export-check`, tested). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P4-04 | The real OCFL-backed `CaptureStore` adapter over `evidence.store.EvidenceStore` (SIG-INGEST-001, §17) | P04.1 owns the stage *contract* and ships the in-memory `CaptureStore` the tests and replay harness use; adapting the OCFL/S3 store to the protocol is a P04.2 concern (it drags object storage into every connector test). | The `CaptureStore` protocol (`put`/`get`/`has`, content-addressed) is the stable seam; the evidence store already writes content-addressed capture rows (P02.2), so the adapter is mechanical and does not change the framework contract (ADR-026). |
| RISK-P4-05 | Source-specific `discover/fetch/parse/extract/normalize` and a real HTTP `Transport` for `PoliteFetcher` (SIG-INGEST-006/007) | The framework is source-agnostic by design; the first concrete connectors (OSM/Atlas) and a real transport are P04.2/P04.3. | The `Transport` protocol and the `Connector` base class are the injection seams; a toy connector + fake transport exercise every framework guarantee end-to-end in CI, so a real connector inherits gate/isolation/lineage/replay/disappearance unchanged. *(Connector half retired by P04.2 — the `osm` connector is now built and tested; a real HTTP `Transport` is still owed, see RISK-P4-06.)* |

## Phase 4 — Connector framework, OSM, Atlas (P04.2 — the `osm` connector)

P04.2 is the first real connector on the P04.1 substrate: surveillance physical
assets from OpenStreetMap (§23.2), landing in the physically separate ODbL asset
layer (§42.3). All source-specific logic is pure and fixture-driven; no live
network is contacted in CI.

### Deviations recorded as ADRs (SIG-ENG-031)

| id | Deviation | ADR |
|---|---|---|
| — | The SIG-INGEST-045 tag→claim vocabulary is versioned **data** (`data/osm_tag_vocab.toml`), not code, so changes are §20 versioned migrations; keying is `(osm_type, osm_id, version)`; the ODbL layer is realised at the connector layer (compartment stamping + `physical_asset_rows` projection + the export gate) because connectors are not DB-wired yet; Overpass 429/504 etiquette lives in the connector as pure helpers rather than the shared fetcher. | ADR-027 |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P4-06 | Live Overpass fetching: a real HTTP `Transport` for `PoliteFetcher`, the OCFL `CaptureStore` adapter (carried from RISK-P4-04/05), and shared-layer handling of Overpass **429 → back off / poll `/api/status`** and **504 → shrink** (SIG-INGEST-045h). The framework's `PoliteFetcher` currently classifies 429 as a bot challenge → disappearance, which is wrong for Overpass slot exhaustion. | This ticket owns the source-specific stages + etiquette, all exercised over committed fixtures (SIG-PARSE-007); a real transport and the OCFL adapter are the live-wiring ticket, and reconciling the shared 429 semantics is framework surgery deliberately deferred (out of P04.2 scope — ADR-026/027). | The etiquette is built and tested as pure helpers now (`overpass_status_action` 429→back_off/504→shrink, `build_overpass_query` `[timeout]/[maxsize]` + no-space filters, `acquisition_mode` PBF-vs-tiled, `assert_own_or_public_instance`, `BulkStitchingForbidden`); the descriptive contact-carrying UA is already enforced by the shared `PoliteFetcher` (SIG-INGEST-045d). ADR-027 records the deferral and its revisit trigger. |
| RISK-P4-07 | A **physically separate** ODbL `physical_asset` table in the DB per §42.3. The Appendix-C `physical_asset` table carries the OSM columns inline and is not itself compartment-split. | Connectors are not DB-wired in P04.x (the framework asserts through the `ClaimSink` seam, RISK-P4-06); splitting the stored table is a DB/ontology concern, not a connector one. | Every OSM output row is stamped `license=ODbL-1.0`/`compartment=osm_physical` and the export gate (`policy.licensing.compute_export_license`, tested) fails any merge with the CC-BY graph, so the separation obligation (SIG-LIC-006) holds at the export boundary today; the stored-table split is tracked for the DB layer (ADR-027 revisit trigger). |

## Phase 4 — Connector framework, OSM, Atlas (P04.3 — the `atlas` connector)

P04.3 is the second real connector on the P04.1 substrate and is deliberately of a
different shape from `osm`: agency-level **adoption** from the EFF Atlas of
Surveillance (§23.3), writing a single predicate — `deployment_exists` — at
family-level technology granularity into the CC-BY-4.0 SIG graph compartment. All
source-specific logic is pure and fixture-driven; no live network is contacted in
CI.

### Deviations recorded as ADRs (SIG-ENG-031)

| id | Deviation | ADR |
|---|---|---|
| — | The Atlas category→family mapping, the nine evidence genres, the predicate allowlist, and the retired-category ledger are versioned **data** (`data/atlas_vocab.toml`), not code (§20 migrations); the category map is **seeded from the `eff_atlas` crosswalk** and rolled to family level (SIG-STORE-039/040); `deployment_exists` landing in the CC-BY-4.0 SIG graph is realised at the connector layer (compartment stamping + the export gate) because connectors are not DB-wired yet; a category retirement (SIG-ONTO-059) is recorded as a `vocabulary_event` row keyed on the Atlas version rather than wall-clock time so `normalize` stays idempotent (SIG-INGEST-003). | ADR-028 |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P4-08 | Resolver-side **supersession / temporal qualification** of an Atlas row by later evidence (§23.3, OL-2D-AT-06). The connector does not itself decide when a later claim supersedes an Atlas row. | Reconciliation/supersession is the resolver's job (P08.x), explicitly out of scope for a connector ticket; deciding it here would duplicate and pre-empt that layer. | Every Atlas row is **append-only** and carries the full provenance a resolver needs (source attribution, Atlas vocabulary version, candidate agency identifier, upstream links), and the connector marks nothing "current"/authoritative — so supersession is a pure resolver decision over existing data, tested by `test_rows_are_append_only_with_no_current_value_flag`. ADR-028 records the deferral. |
| RISK-P4-09 | An **exhaustive** Atlas category → family map. Only the five crosswalk-seeded families (ALPR, face recognition, gunshot detection, UAS, camera-federation hub) are mapped; the real Atlas taxonomy carries more. | The authoritative external crosswalk (`ontology/vocab/crosswalks.yaml`) seeds exactly these; extending the map is a reviewed §20 data migration, not code, and guessing the remainder would fabricate mappings (SIG-STORE-040). | An unmapped category is recorded as an unmapped category **+ a research task** (never a guessed family), tested by `test_unmapped_category_files_a_research_task_and_writes_no_deployment`; the map grows by additive data migration exactly as the osm vocabulary does. |
| RISK-P4-10 | Live Atlas fetching: a real HTTP `Transport` for `PoliteFetcher` and the OCFL `CaptureStore` adapter (carried from RISK-P4-04/05/06). | The framework is not live-wired yet (ADR-026); this ticket owns the source-specific stages, all exercised over committed fixtures (SIG-PARSE-007). | The `Transport` protocol + `CaptureStore` seam are stable; the connector inherits gate/isolation/lineage/replay/disappearance unchanged and is driven end-to-end over committed CSV fixtures, so a real transport is a drop-in (ADR-026/028 revisit trigger). |

## Phase 5 — Probabilistic ER, review queue, curation UI (P05.1 — the matcher + §14.7 quality gates)

P05.1 adds the probabilistic top of the resolution cascade (Splink 4 on DuckDB),
sized blocking, the gold set + frozen holdout, the auto-write demotion gate, and
cluster-shape alerts. Per SIG-IDENT-030 / SIG-RECON-003 no network-analytics surface
ships before these gates pass. As with the connectors (ADR-026/027/028), the stage is
realised at the layers that exist today — pure, tested library code plus versioned
data — because the review-queue persistence, the curation UI, and the claim-table
write path are P05.2 / P08.x.

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P5-01 | **Uncertain matches writing themselves** (the Phase-5 headline risk, §52): a probabilistic or weak-signal match silently merging two organisations. | Tiers 4 and 5 return `ProbabilisticMatch` objects with `disposition="review"` / `claim_status="PROPOSED"` and no auto-write path exists on them (SIG-IDENT-020); tier 6 returns nothing at all. Proven by `test_every_probabilistic_match_is_proposed_never_auto_write` and `test_tier6_below_threshold_persists_no_record`. |
| RISK-P5-02 | **An unsized blocking rule** degrading into an all-pairs scan, or a low-cardinality rule (state/suffix alone) that blocks nothing. | Every blocking rule is sized against a documented ceiling and rejected if oversized; sole low-cardinality keys are refused (SIG-IDENT-023). The matcher sizes before it scores. Proven by `test_oversized_rule_is_rejected`, `test_sole_low_cardinality_key_is_prohibited`, `test_oversized_blocking_aborts_the_match`. |
| RISK-P5-03 | **An unexplainable merge** — a match weight with no decomposition a journalist could defend. | The model is fully-specified m/u data, so every match carries its weight and per-comparison Bayes-factor decomposition (SIG-IDENT-025), deterministic run to run. Proven by `test_every_match_records_tier_evidence_weight_and_decomposition` and `test_matching_is_deterministic`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| id | Deviation | ADR |
|---|---|---|
| — | Splink 4 is driven as a **fully-specified, deterministic** model (per-level m/u in versioned `data/splink_model.toml`) rather than an EM-trained one, so the match weight and its decomposition are reproducible and explainable (§28.1); tiers 4–5, the gold set, the quality gates, the ER run record, and the `same_as`/stability wiring are realised as pure library code + data because connectors/ER are not DB-wired yet; the auto-write-demotion floor is published with the model. numpy/pandas/splink stubs are excluded from mypy via `follow_imports = "skip"` (their stubs don't type-check under the 3.11 target). | ADR-029 |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P5-04 | The **live claim-table / `resolution`-table write path and the review queue** for PROPOSED proposals (§14.6, §27). The ER stage emits proposals, `same_as` relations, and an `ERRun` as in-memory value objects with `to_row()` shapes, not DB rows. | Connectors/ER are not DB-wired in P05.1 (ADR-026/029), and the review-queue persistence + curation UI are explicitly P05.2. Wiring here would pre-empt that ticket. | The append-only, versioned, provenance-carrying shapes a DB writer needs are established and tested now (`ERRun.to_row`, `OrganizationRelation.to_row`, `ProbabilisticMatch.match_evidence`); `run_entity_resolution` composes the full six-tier cascade end-to-end over library inputs. ADR-029 records the deferral and its revisit trigger. |
| RISK-P5-05 | The gold set's **model m/u values are seeded by judgement, not EM-estimated**, and the committed gold set is a small illustrative one, not the national stratified sample. | A trained model would be non-deterministic and undefendable as a stated rule (§28.1, SIG-RECON-004); building the full national gold set is a data-collection effort beyond a code ticket. | The gold set's *construction* (stratified sampling, double adjudication + κ, three-value vocab, frozen holdout, per-label provenance) is built and tested (`resolution.gold_set`), and the auto-write demotion gate (SIG-IDENT-028) bounds the risk of a mis-specified model by demoting any tier whose holdout precision falls below the published floor. Refitting is a versioned model migration. |
| RISK-P5-06 | The **adjudicators' human judgement itself** (the correctness of a `match` / `non_match` / `not_enough_information` label) and inter-adjudicator agreement in the wild. | Human adjudication is agentic, not a unit test (the same posture as SIG-PUB-008 in RISK-P0-05). | The *machinery* around it is deterministic and tested: the three-value vocabulary, the written adjudication rules as versioned data, Cohen's κ computation, double-adjudication consensus (disagreement yields no silent pick), and the immutable frozen holdout (`test_frozen_holdout_pair_cannot_be_relabelled`). |
