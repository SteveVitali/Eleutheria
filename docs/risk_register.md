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

## Phase 5 — Probabilistic ER, review queue, curation UI (P05.2 — the review queue + the LLM boundary)

P05.2 adds the internal review queue + curation contract (`resolution.review_queue`) and
the model-assisted-extraction scaffolding (`parsing.extraction`) as library code + data +
a CLI. It **partly retires RISK-P5-04**: the review-queue persistence and curation surface
now exist (JSON-serialisable queue + `sig-resolution review` CLI); the live claim-table
*write* path for accepted decisions remains P08.x. See ADR-030.

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P5-07 | **Model output reaching the graph** — an LLM extraction or review rationale silently becoming a published claim. | Every model-extracted claim is constructed R6/`PROPOSED` with `writes_to_graph` always False, and the only sink is a `ReviewQueue` with no graph-write method; a decision on model output logs `model_id`+`prompt_version` (SIG-IDENT-026, SIG-LLM-002/005). Proven by `test_extracted_claim_is_r6_and_proposed_and_never_writes_to_graph`, `test_queue_has_no_graph_write_path`, `test_model_extraction_item_is_model_assisted_and_logs_provenance_on_decision`. |
| RISK-P5-08 | **A hallucinated extraction** — a model-invented value with no basis in the source. | Every extracted claim carries a `SourceSpan` whose verbatim text must appear in the capture at its offsets, or the extraction is rejected (SIG-LLM-004 / SIG-PARSE-003) — hallucination is mechanically detectable. Proven by `test_span_text_not_in_the_capture_is_rejected`, `test_extract_rejects_the_whole_batch_when_one_span_is_unlocatable`. |
| RISK-P5-09 | **Lowered evidentiary standard on model outage** — emitting a weaker claim to keep the pipeline moving when the model is down. | `run_extraction` queues the work (`queued=True`, no claims) rather than failing or degrading the standard (SIG-LLM-007). Proven by `test_unavailable_model_queues_the_work_and_emits_no_claim`. |

### Partly retired

| id | Update |
|---|---|
| RISK-P5-04 | **Review-queue persistence + curation UI delivered.** `resolution.review_queue.ReviewQueue` (append-only decisions, `to_dict`/`from_dict`) and the `sig-resolution review enqueue/list/show/decide` CLI realise the review queue and curation surface P05.1 deferred. The live claim-table **write** path that acts on an accepted decision is still P08.x, and the public web curation UI is still P15.x — both compensated by the append-only, provenance-carrying `ReviewItem`/`ReviewDecision` shapes tested here (`test_queue_round_trips_through_json_dict`). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P5-10 | The **actual model client** for model-assisted extraction (`SIG-LLM-001`). No vendor SDK or network call is wired; `run_extraction` drives an injected `ModelClient` protocol. | A concrete model integration (auth, batching, cost, the `ai-train=no` vs model-assisted-extraction distinction, SIG-LIC-004c) is an operator decision beyond this ticket, and wiring one would make the scaffolding non-deterministic and untestable offline. | The whole boundary is enforced on the *output* regardless of which model produced it — schema validation, span-in-capture, R6/`PROPOSED`, provenance logging, graceful degradation — so any client is a drop-in behind a tested guardrail (ADR-030 revisit trigger). |
| RISK-P5-11 | The **gold-set accuracy cadence** for SIG-LLM-006 uses seeded per-type thresholds and an on-demand `measure_accuracy`, not a scheduled measurement against a national gold set. | The published cadence and the real per-extraction-type gold sets are a data/ops effort beyond a code ticket (mirrors RISK-P5-05 for the ER gold set). | The demotion *mechanism* is built and tested: a measured accuracy below the versioned floor flips the type to human-only deterministically (`evaluate_demotion`), and sampling is reproducible; formalising the cadence is a data migration + ops schedule. |

## Phase 6 — Vertical slice: one jurisdiction end-to-end (P06.1 — Oklahoma City / OKCPD Flock)

P06.1 carries one real jurisdiction (Oklahoma City, OKCPD Flock ALPR) from
evidence to a rendered dossier and executes J-1, to **falsify the design before
it is replicated** (§51.1). It adds the minimal count-reconciliation seed
(`reconcile.weight/counts/model`), the §39.2 dossier renderer (`exports.dossier`),
the J-1 acceptance query (`tests/acceptance/`), the three missing §29.1 count
predicates, the pre-registered hardness precondition, and the committed
retrospective (HARD GATE §54).

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P6-01 | **Design falsification (§51.2).** The claim/temporal/epistemic/reconciliation model might not survive contact with a real, messy jurisdiction — and discovering that at national scale would be catastrophic. | One real jurisdiction is carried end to end through J-1; the epistemic weight model reproduces Appendix D.2 exactly (`test_appendix_d2_worked_example_reproduces_exact_weight_classes`), the count predicates stay distinct with `PREDICATE_CONFLATION` firing on a deliberate conflation, and every material fact resolves to a document at a locator. The model **survived** on its core claim (reconciliation-not-aggregation, contradictions stay visible) and its **failures are recorded and mostly fixed now** in `docs/slice/P06.1_retrospective.md` — at one jurisdiction rather than twenty thousand. |

### Findings surfaced by the slice (recorded in the retrospective)

| id | Finding | Disposition |
|---|---|---|
| RISK-P6-02 | The predicate registry shipped with three of the six §29.1 count predicates missing; `C` could not be derived for `mapped/invoiced/claimed_device_count`. | **Fixed here** (additive registry rows, ADR-031). A conformance check for the §29.1 set is handed to P08. |
| RISK-P6-03 | Appendix D.2's published `W2` for OSM-mapped does not follow from §10.6 without the unstated structured-export `+1` upgrade. | Implemented faithfully and test-anchored; **spec doc fix** recommended (retrospective finding 2). |
| RISK-P6-04 | The count model conflates *basis* with *scope*: real municipal data (metro-mapped 299 > city-active 90) inverts the Appendix-D delta ordering. | Handed to P08 — the count model needs a scope/population dimension (retrospective finding 3; ADR-031 revisit trigger). |
| RISK-P6-05 | `count_basis` is load-bearing in §29.1 but has no home in the schema/model; the generated `Contradiction`/`ResearchTask` models are thinner than the DB tables and the contradiction-type vocabulary is spec-only. | Handed to P08 / ontology generation (retrospective findings 4–5). |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-031 | A minimal count-reconciliation seed in `reconcile/` ahead of the Phase-8 engine, plus the three added count predicates (additive, back-compatible). |
| ADR-032 | A minimal §39.2 dossier renderer in `exports/` with a print-CSS PDF path; a server-side PDF renderer and the full epistemic surface are deferred to P15.2. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P6-06 | **Live acquisition of the slice's evidence.** The records/procurement/parsing connectors (P07) and the portal layer (P11) do not exist yet, so the slice's evidence is committed fixtures faithfully transcribing cited public sources, not live captures. | Phase 6 is deliberately sequenced before those connectors (§52); building them here would pre-empt P07/P11. | Each artifact's bytes are content-addressed (a real `capture_digest`), its real source URL is the `stable_locator`, and each claim's `locator` pins a span in the captured document — the full evidence→claim shape (§D.4) is proven end to end, and the tension is recorded in the retrospective (finding 6). |
| RISK-P6-07 | **The live claim-spine / DB write path.** The slice reconciles and renders over in-memory value objects (matching the connector/ER convention), not the PG claim table. | Docker-free acceptance queries run in CI (SIG-CHART-009); the live write path is P08.x. | The reconciliation value objects align with `db/deploy/graph_annotations.sql`; the append-only guarantees are unchanged (no writable current-value columns introduced). |

## Phase 7 — Records, procurement, and document parsing (P07.1 — the layered parsing stack)

P07.1 adds the §24 **parser interface every connector extracts through** as focused,
dependency-light modules in `parsing/` beside the P05.2 layer-6 model boundary: the
seven-layer cheapest-sufficient enum (`parsing.layers`), byte/zip-manifest classification
with per-member archive handling (`parsing.classification`), the six-kind locator schema
(`parsing.locator`), the `raw_value` claim contract (`parsing.claim`), the versioned
reversible reason-code mapping (`parsing.reason_codes` + `data/reason_codes.toml`), and the
fixtures + canary parser-drift defences (`parsing.drift`). It adds no third-party dependency
(`pylock.toml` unchanged) and no DDL — it produces the shapes the P02 claim spine already
stores. See ADR-033.

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P7-01 | **Silent parser drift (R11, a top-5 operational risk).** An upstream source changes shape and a parser keeps producing garbage undetected. | Two complementary defences: committed fixtures fail a test on any parser-output change (`parsing.drift.assert_no_drift`), and a structural canary **alerts** — returns findings, never drops — when a live sample's shape drifts (`parsing.drift.run_canary`, `CanaryReport.alerted`). Proven by `tests/parsing/test_drift.py::test_a_drifted_parser_fails_the_fixture_assertion`, `::test_canary_alerts_and_does_not_drop_on_structural_drift`. |
| RISK-P7-02 | **An extraction with no provenance** — a value admitted to the graph that cannot say where it came from. | A `ParsedClaim` cannot be constructed without a `Locator` (six validated kinds); a locator-less claim is rejected (SIG-PARSE-003). Proven by `tests/parsing/test_claim.py::test_a_claim_without_a_locator_is_rejected`. |
| RISK-P7-03 | **A value SIG cannot parse being dropped as an error** — losing data about the source (P2). | `ParsedValue.unparseable` keeps the raw literal with `parsed=None`; `raw_value` is mandatory and never None. Proven by `tests/parsing/test_claim.py::test_raw_value_is_preserved_for_an_unparseable_value_round_trip`. |
| RISK-P7-04 | **A reason-vocabulary change rewriting history** (SIG-STORE-038). | The mapping is versioned data; every normalized reason is stamped with the version; a re-classification is new claims (`vocabulary_migration`), never an edit. Proven by `tests/parsing/test_reason_codes.py::test_changing_the_mapping_does_not_rewrite_history`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-033 | The §24 stack as the `parsing` parser interface: classification by byte/zip-manifest signals (no `pypdf`/`openpyxl` dependency), the heavy layer-3/4/5 engines deferred to the connectors that need them, and the reason-kind/signal fields mapped onto existing claim-spine columns rather than a new migration. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P7-05 | The **concrete extraction engines** for layers 3–5 (PDF text/table, OCR). Only the layer *selection* and interface are built; classification routes to a layer, it does not run one. **Owner: P07.2/P07.3** (ADR-033 Decision 4) — §24.1 mandates the strategy, not a specific engine, so no `SIG-PARSE-*` requires an engine here; the P07.2/P07.3 "P07.1 parses documents" dependency phrasing notwithstanding, the engines are added behind this interface by the connectors that first parse real documents. | Wiring the heavy libraries (and OCR) here would pre-empt those tickets and add runtime dependencies with no caller; a firmer assignment is a decompose-step / canonical-spec-source change (SIG-ENG-003), not an edit of the derived ticket. | The interface is complete and tested end-to-end; the scanned-PDF signal is a deterministic byte heuristic whose mis-route is corrected downstream, never a silent drop (ADR-033 revisit trigger). |
| RISK-P7-06 | The **nightly canary schedule** (SIG-PARSE-008 MUST). The deterministic drift core exists; the scheduled fetch-a-live-sample-and-alert job does not. **Owner: the `orchestration/` layer / live-run wiring** — the spec provides for it via SIG-INGEST-020 (Dagster, cron-swappable) and the SIG-GOV-020/021 degraded-mode keepalive; no standalone ticket names the cross-parser job, so it lands with live orchestration (mirrors the P05.2 gold-set cadence, RISK-P5-11). | The ops schedule and alert destinations are an operations concern, not a code ticket; the per-connector canary ACs (spec line 6782) carry the per-parser half in the meantime. | `structural_findings`/`run_canary` are pure and tested; the nightly job is a thin fetch-and-call wrapper whose alerting contract is a tracked ops deliverable. |

## Phase 7 — Records, procurement, and document parsing (P07.2 — the `records` connector)

P07.2 adds the third source connector on the P04.1 framework (`connectors.records`) — the
public-records channel (MuckRock/NextRequest/DocumentCloud) — plus the `RecordsRequest`
runtime shape and the `no_responsive_records` → coverage bridge. It is a **targeted-lookup**
client (never a crawler, a legal posture under SIG-INGEST-036/037), authenticates to MuckRock's
api_v2 with a five-minute JWT that refreshes early and on a 401, and turns an agency's on-record
"no responsive documents" into a `NO_EVIDENCE_FOUND` coverage record (SIG-ONTO-040) by reusing
`db.absence`. See ADR-034.

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P7-07 | **A records "no responsive records" reply is discarded as a null**, losing the agency's on-record statement that the surveillance it was asked about does not exist (SIG-ONTO-040). | `no_responsive_records` writes a `CoverageRecord` in the `NO_EVIDENCE_FOUND` state via the canonical §9.5 model (`db.absence`), which MUST name the sources searched (SIG-TIME-011). Proven by `tests/connectors/test_records.py::test_no_responsive_records_writes_a_coverage_record`, `::test_no_responsive_records_flows_through_normalize`, `::test_coverage_record_must_name_the_sources_searched`. |
| RISK-P7-08 | **A rate-limited records API is crawled/enumerated** — both prohibited and a legal-posture breach (SIG-INGEST-036/037), and doomed at ~15 req/min. | `discover()` returns only supplied targets and `assert_targeted_lookup` refuses a crawl mode, a pagination cursor, or a bare listing endpoint (`CrawlAttempted`). Proven by `tests/connectors/test_records.py::test_crawl_mode_target_is_refused`, `::test_paginated_target_is_refused`, `::test_bare_listing_endpoint_is_refused`, `::test_discover_returns_only_supplied_targets_and_refuses_a_crawl`. |
| RISK-P7-09 | **A "fetch a MuckRock token at job start" design fails** — the JWT expires after five minutes and every subsequent data endpoint 401s (R4 F4.3). | `MuckRockTokenCache` refreshes once the token is within its margin of expiry (effective TTL < 5 min) and re-mints on a 401 (`RecordsConnector.fetch` catches `ChallengeEncountered`, retries once); a persistent challenge still propagates. Proven by `tests/connectors/test_records.py::test_the_jwt_cache_refreshes_before_the_token_expires`, `::test_fetch_refreshes_the_jwt_on_a_401_and_retries_once`, `::test_a_persistent_challenge_still_propagates`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-034 | The `records` connector: an **additive per-request `headers` seam** on the shared `connectors.net` fetcher (so the MuckRock JWT rides the single egress seam, SIG-INGEST-011, rather than a records-owned HTTP client); the concrete token mint and real HTTP transport deferred to the ops/live-run layer (injected `TokenSource`, mirroring the injected `Transport`); the document-extraction engines still deferred (§23.5 scopes P07.2 to capturing + classifying + linking released documents, not running a layer — the connector calls `parsing.classification` to route); `connectors` gains `sig-db`/`sig-parsing` as direct workspace deps (no cycle, `pylock.toml` unchanged); and per-source export compartments left to the licence gate rather than stamped, since the records channel spans REFERENCE sources with varying per-document rights. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P7-10 | The **live MuckRock token mint** (POST username/password to `accounts.muckrock.com/api/token/`) and the **real HTTP transport** the connector fetches through. Only the TTL / refresh-on-401 cache logic and the endpoint construction ship here. **Owner: `orchestration/`/`ops` live-run wiring**, the same deferral `connectors.net` already makes for its HTTP transport. | Wiring a live account + real sockets here would add a credentialed network dependency with no live caller and duplicate the injected-transport seam the framework already defines. | `MuckRockTokenCache` refreshes through an injected `TokenSource` and is fully tested for TTL + refresh-on-401; the endpoint/auth facts are versioned data (`data/records_vocab.toml`, re-verify per ADR-034 revisit trigger). |
| RISK-P7-11 | **Running the layer-3/4/5 extraction engine over a captured released document** (PDF text/table, OCR). P07.2 captures each released document as an `EvidenceArtifact` and **classifies** it (routing it to a layer via the P07.1 parser), but does not run the engine. **Owner: the point a document-derived claim is needed** (§23.5 scopes P07.2 to the request + its captures; "the layered parsing of the released documents themselves" is P07.1's interface, ADR-033 Decision 4). | §23.5 explicitly hands document parsing to P07.1's interface and scopes this connector to the request and its released captures; wiring an engine here would pre-empt that and add heavy runtime dependencies. | Every released document is captured (content-addressed) and its classification verdict recorded, so extraction is a pure re-processing step over stored bytes; a mis-route of the scanned-PDF heuristic is corrected downstream, never a silent drop. |

## Phase 7 — Records, procurement, and document parsing (P07.3 — the `procurement` connector)

P07.3 adds the fourth source connector on the P04.1 framework (`connectors.procurement`) — the
procurement channel (cooperative purchasing vehicles, USAspending sub-awards, and agenda
platforms) — plus the `Contract`/`FundingInstrument` runtime shapes, the published
agenda-platform tenant registry, and the `artifact_type` ontology vocabulary. It is a
targeted-lookup client; a cooperative piggyback cannot be recorded without its ridden master
award (SIG-ONTO-032); a federal grant is traced to the local deployment it funded through
USAspending **sub-awards** via `federal_award_id` (SIG-ONTO-033); and the municipality→platform
tenant directory the outline says "SIG should build" is built and published, with discovery
negatives retained as `db.absence` coverage records ahead of P09.1. See ADR-035.

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P7-12 | **A cooperative-vehicle purchase is recorded as if it had a local competitive procurement, or its ridden master award is dropped** — so a missing local RFP is wrongly read as "no procurement evidence" (SIG-ONTO-032). | `Contract.__post_init__` refuses a `cooperative_piggyback` contract with no `parent_cooperative_contract`, and `_build_contract` defaults a cooperative-vehicle source to that channel and carries the master award through. Proven by `tests/connectors/test_procurement.py::test_cooperative_piggyback_contract_requires_parent`, `::test_cooperative_vehicle_source_defaults_to_piggyback_and_links_master`, `::test_cooperative_vehicle_without_master_award_is_a_hard_error`. |
| RISK-P7-13 | **A federal grant → local surveillance purchase is invisible** because only USAspending prime awards are pulled, or the funder is conflated with the operating agency (SIG-ONTO-033). | The connector asserts every USAspending target pulls sub-awards (`assert_pulls_subawards` in `discover`/`fetch`), maps a sub-award to a `FundingInstrument` with funder ≠ recipient and the prime award id as `federal_award_id`, and traces it to a local deployment. Proven by `tests/connectors/test_procurement.py::test_usaspending_target_must_pull_subawards`, `::test_subaward_becomes_funding_instrument_distinguishing_funder_from_recipient`, `::test_subaward_traces_to_deployment_via_federal_award_id`, `::test_subaward_flows_through_normalize_and_traces`. |
| RISK-P7-14 | **Agenda-platform coverage is silently incomplete** — a per-tenant API with no directory means jurisdictions are missed with no record of the gap (§22.3, SIG-METRIC-002a). | SIG builds and publishes the `data/agenda_tenants.toml` tenant registry the connector reads, and a jurisdiction probed with no discoverable platform is retained as a `NO_EVIDENCE_FOUND` coverage record naming the platforms probed (SIG-TIME-011), not discarded. Proven by `tests/connectors/test_procurement.py::test_connector_reads_tenants_from_the_registry`, `::test_tenant_discovery_negatives_are_retained_as_coverage`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-035 | The `procurement` connector: the §10.3.2 `artifact_type` vocabulary — which had no executable, testable home (a free-text DB column; the 9-value directness `artifact_genres` is a different vocabulary) — is promoted to a controlled `ArtifactType` LinkML enum in the ontology source of truth carrying the full genre list **plus** the SIG-INGEST-047 additions (`state_auditor_survey`, `warrant`, `procurement_aggregator_record`), attached to `EvidenceArtifact.artifact_type`, published as SKOS, and regenerated (additive: a new enum + optional slot, free-text DB column unchanged); the agenda-platform tenant registry is a new **published** data artifact this ticket owns (`data/agenda_tenants.toml`); the SIG-METRIC-002a tenant-discovery negatives are wired into `db.absence` now, ahead of P09.1's coverage surface, mirroring ADR-034's forward-wiring of the records `no_responsive_records` bridge; and the connector calls `parsing.classification` to classify a captured procurement document but does not run a layer engine (§23.6 scope + ADR-033 Decision 4). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P7-15 | The **live HTTP transport** for USAspending / cooperative-vehicle / agenda-platform APIs the connector fetches through. Only the endpoint/field facts (`procurement_vocab.toml`, `agenda_tenants.toml`) and the pure parse/extract/normalize logic ship here. **Owner: `orchestration/`/`ops` live-run wiring**, the same deferral `connectors.net` already makes for its HTTP transport. | Wiring real sockets + credentials here would add a network dependency with no live caller and duplicate the injected-transport seam the framework already defines. | The connector fetches through the shared politeness layer over an injected transport and is tested end-to-end over canned responses; the endpoint/field facts are versioned data, re-verified per the ADR-035 revisit trigger. |
| RISK-P7-16 | **The tenant registry is a small, partly-unverified seed**, and the tenant-discovery negatives are produced but not yet consumed by a coverage surface. **Owner: ongoing records/discovery research; P09.1 for the coverage surface.** | Filling out a national municipality→platform directory is continuous research, not a one-ticket deliverable; the coverage surface that renders the negatives is P09.1. | Rows carry an honest `verified` flag (no synthetic certainty, §3.1); the discovery-negative path (`tenant_discovery_negatives`) ensures every probed-but-empty jurisdiction is retained as a `db.absence` coverage record now (SIG-METRIC-002a), so gaps are recorded rather than hidden. |
| RISK-P7-17 | **Running the layer-3/4/5 extraction engine over a captured procurement document** (a signed PDF contract, an award-packet ZIP). The connector captures each document as an `EvidenceArtifact` with its `artifact_type` and **classifies** it, but does not run the engine. **Owner: the point a document-derived claim is needed** (§23.6 scope; the parser interface is P07.1's, ADR-033 Decision 4). | §23.6 hands document parsing to P07.1's interface; wiring an engine here would pre-empt that and add heavy runtime dependencies with no caller. | Every captured document is content-addressed and its classification verdict recorded, so extraction is a pure re-processing step over stored bytes; a mis-route is corrected downstream, never a silent drop. |

## Phase 8 — Reconciliation engine and contradictions (P08.2 — the §29 reconciliation workflows)

The §29 per-predicate workflows layered on the P08.1 resolver (ADR-036). The
risks here are all failures of the "keep the distinction visible" mandate — the
politically consequential collapses §29 exists to prevent.

| id | Risk | How it is retired |
|---|---|---|
| RISK-P8-01 | **An orphan device's operator is guessed and written as observed** — a `probable` attribution is treated as fact, or pushed to OSM, corrupting the source of truth (SIG-RECON-031). | Attribution returns a `reconcile.model.Inference` whose `layer` is always `L4`, `is_observation` is always `False`, `pushable_to_osm` is always `False`, and `as_observed_operator()` raises; promotion needs a human confirmer or a D1/D2 source (`attribution.promote`/`PromotionRefused`). Proven by `tests/reconcile/test_attribution.py::test_inference_is_not_writable_as_observed_operator`, `::test_inference_is_never_auto_pushable_to_osm`, `::test_high_score_does_not_promote_itself`. |
| RISK-P8-02 | **A device is defaulted to the containing jurisdiction** even when a county/state road, a boundary, or a shared deployment makes attribution ambiguous by construction (SIG-RECON-032). | The hard cases are modelled as explicit branches that enqueue a research task rather than pick (boundary, containment-only, cross-jurisdiction road, tie) or record multiple operators (shared). Proven by `tests/reconcile/test_attribution.py::test_containment_alone_is_not_attribution`, `::test_boundary_device_is_enqueued_not_picked`, `::test_county_road_inside_city_does_not_default_to_containing_jurisdiction`, `::test_multi_agency_shared_deployment_is_multiple_operators_not_a_conflict`. |
| RISK-P8-03 | **A sharing asymmetry is silently resolved** — A's export lists B, B's does not list A, and the system picks one explanation, destroying the signal (SIG-RECON-035). | `reconcile.sharing.reconcile_sharing` retains both observations, emits a `SHARING_ASYMMETRY` contradiction, and links a research task; the three edge types are reconciled separately and never merged. Proven by `tests/reconcile/test_sharing.py::test_asymmetry_is_a_finding_not_a_merge`, `::test_the_three_edge_types_are_reconciled_separately`. |
| RISK-P8-04 | **A single snapshot invents a start date**, or an `observed_use` edge silently becomes a `configured_access` edge at L1 (SIG-RECON-036/037). | A single-snapshot edge carries `valid_from_kind='unknown'`; use→access is available only as a labelled L4 inference (`infer_access_from_use`), and no L1 configured_access edge is materialized from observed_use. Proven by `tests/reconcile/test_sharing.py::test_single_snapshot_edge_carries_unknown_valid_from_kind`, `::test_observed_use_does_not_create_configured_access_at_l1`. |
| RISK-P8-05 | **Vendor replacement is rendered as "surveillance removed"** — the most politically consequential lifecycle mistake — or a canceled contract with hardware still present is smoothed into one summary (SIG-RECON-041/042). | `detect_vendor_replacement` creates a `replaced_by` edge rendered "vendor replaced"; `render_lifecycle_status` states "contract canceled; hardware still present as of <date>" and never omits either track. Proven by `tests/reconcile/test_lifecycle.py::test_vendor_replacement_is_rendered_as_replacement`, `::test_canceled_contract_with_hardware_present_is_stated_plainly`. |
| RISK-P8-06 | **Fuzzy-dated lifecycle events are given a false order** rather than recorded as indeterminate (SIG-RECON-040). | `resolve_track` orders by EDTF envelope (reusing `db.edtf.derive_envelope`) and merges overlapping envelopes into a single unordered-within-window slot instead of picking an order. Proven by `tests/reconcile/test_lifecycle.py::test_overlapping_fuzzy_envelopes_are_unordered_within_window`, `::test_distinct_dated_events_are_ordered`. |
| RISK-P8-07 | **A vendor default silently becomes the configured retention**, or a vendor default change retroactively rewrites existing deployments (SIG-RECON-043, SIG-ONTO-036). | `populate_configured_from_vendor_default` raises `VendorDefaultLeak`; `apply_vendor_default_change` returns the configured value unchanged; the three retention predicates are kept distinct and their disagreement is a finding. Proven by `tests/reconcile/test_retention.py::test_vendor_default_never_populates_configuration`, `::test_vendor_default_change_is_not_retroactive`. |
| RISK-P8-08 | **Policy/configuration divergence is editorially collapsed** — the written policy and the enabled configuration are merged into one number/answer (SIG-RECON-044). | `reconcile_policy_configuration` emits a `policy_configuration_divergence` finding carrying both sides' evidence; `PolicyConfigResult.collapse()` raises. Proven by `tests/reconcile/test_policy_config.py::test_canonical_immigration_divergence_is_a_first_class_finding`, `::test_divergence_must_not_be_collapsed`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-036 | The §29 workflows ship as thin value-object modules in `reconcile/` (following ADR-031) that **emit** contradictions/tasks and an L4 device-attribution inference but do **not** persist — P08.3 (§31) owns the materialized `Contradiction` entity and P12.x (§30) owns the L4 inference layer. `reconcile` gains a `sig-db` workspace dependency to **reuse** the canonical `db.edtf.derive_envelope` (ADR-024) for lifecycle ordering rather than duplicate the envelope ruleset; the derivation is pure, so no Postgres runtime coupling is introduced. The three §29.5 retention predicates are modelled as local keys (`policy_written_retention_days` is not yet a registered ontology predicate), which is sufficient because the retention workflow keeps them distinct rather than weighing them through the registry-driven resolver. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P8-09 | **Persistence + lifecycle of the contradictions and the L4 inference** these workflows emit. The workflows produce in-memory `Contradiction`/`Inference`/`ResearchTask` value objects; storing them, running the contradiction lifecycle, and materializing `inference.derived_fact` are downstream. **Owner: P08.3 (§31) for contradictions; P12.x (§30) for the L4 layer.** | Materializing those entities here would create two competing owners of the same tables and pre-empt the tickets that own them. | The value objects are aligned with the persisted shapes (`db/deploy/graph_annotations.sql`, `db/deploy/inference_schema.sql`), so persistence is a wiring step; every emitted finding is a first-class, addressable object with its evidence and task, never a silent drop. |

## Phase 8 — Reconciliation engine and contradictions (P08.3 — contradiction as a first-class object)

The materialized `Contradiction` entity and its lifecycle (§31), plus the
byte-identical L3 rebuild guarantee (§28.7), delivered on the ADR-037 decision.
The risks here are failures of the "every contradiction stays visible" half of the
defining standard (§3.1) and of the reproducibility contract SIG-RECON-020 pins.

| id | Risk | How it is retired |
|---|---|---|
| RISK-P8-10 | **A resolved contradiction is deleted or edited in place**, erasing the disagreement from history and breaking append-only provenance (SIG-RECON-055/021). | The lifecycle is append-only: `reconcile.model.Contradiction.resolve`/`accept_unresolvable`/`supersede` return a **new** frozen record that retains every field (`claim_ids`, `research_task_ids`, `contradiction_type`); nothing is deleted and the original is untouched. Proven by `tests/reconcile/test_contradiction.py::test_resolution_sets_status_and_does_not_delete`, `::test_resolved_contradiction_remains_visible_in_history`. |
| RISK-P8-11 | **An open contradiction is suppressed from the published surface** — a value ships as if uncontested when a disagreement is open (SIG-RECON-055, OL-6.5-01). | An open contradiction publishes as `unresolved_conflict` and is included (never filtered) in `reconcile.contradiction.publishable_view` / `Contradiction.public_view`; the resolver also stamps `contradiction_state = unresolved_conflict` on the resolution itself. Proven by `tests/reconcile/test_contradiction.py::test_open_contradiction_is_published_as_unresolved_conflict_not_suppressed`, `::test_resolution_contradiction_state_exposes_open_conflict`. |
| RISK-P8-12 | **The manual brake fails to stop publication** — a curator marks a value unsafe (`severity = blocking`) but it publishes anyway (SIG-RECON-054). | `reconcile.contradiction.forces_unresolved` returns `True` for an open, blocking contradiction on the pair, and the resolver forces `U7`/`UNRESOLVED` when fed it; a resolved/non-blocking/other-pair contradiction does not brake. Proven by `tests/reconcile/test_contradiction.py::test_open_blocking_contradiction_forces_unresolved_u7`, `::test_brake_only_bites_for_open_blocking_on_the_same_pair`. |
| RISK-P8-13 | **An L3 resolution is not reproducible** — a stored decision cannot be regenerated from its inputs, so the `input_digest` guarantee every citing surface depends on is hollow (SIG-RECON-019/020/021). | `reconcile.rebuild.verify_reproducible` reruns the resolver and asserts the fresh `input_digest` **and** full decision key match; a committed sample (`data/l3_rebuild_sample.json`) is regenerated and asserted in CI, and a version change is refused as `NonReproducible` rather than silently diverging. Proven by `tests/reconcile/test_rebuild.py::test_committed_sample_regenerates_byte_identically`, `::test_a_changed_claim_breaks_the_digest`, `::test_a_version_change_refuses_to_reproduce`. |
| RISK-P8-14 | **A contradiction is stated with no path to close it** — a detector surfaces disagreement but generates no research task, so it can sit open forever (SIG-RECON-057, OL-6.5-02). | The detector→task contract is mechanically checked over **every** detector (the §29 workflows and the resolver's Phase-2 guards) by `reconcile.contradiction.detector_task_violations`; each emitted contradiction links a task with a non-empty closing condition. Proven by `tests/reconcile/test_detector_task_contract.py::test_every_detector_honours_the_detector_task_contract`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-037 | The materialized `Contradiction` entity is modelled in **pure Python** aligned with `db/deploy/graph_annotations.sql` and is **not** persisted to Postgres here — continuing the ADR-031/036 precedent; persistence and the read-API projection are downstream (P14.1). The existing `reconcile.model.Contradiction` is **promoted** into the entity (additive fields, back-compat) rather than introducing a second type. The byte-identical L3 rebuild is verified **in-process** against the resolver. To make the detector→task contract hold uniformly, the resolver's Phase-2 contradictions emit **deterministic** (content-derived) research-task ids, and `Resolution`/`CountResolution` gained an additive `tasks` field. |

## Phase 9 — Coverage and negative space (P09.1 — the §32 coverage-metrics layer)

The §32 metrics that make negative space queryable rather than editorial (ADR-038).
The risks here are failures of the "explicit about uncertainty" principle (§3.1, P4):
a negative claim that cannot say what was searched, an aggregate published without a
denominator, four absence kinds collapsed into one, freshness measured in flat days,
and — the sharpest — a population total published from data that cannot support one.

| id | Risk | How it is retired |
|---|---|---|
| RISK-P9-01 | **A negative claim cannot say what was searched** — a `searched_not_found` record without `sources_searched[]`, so "not in the Atlas" and "not in the Atlas, any portal, or three years of minutes" are indistinguishable (SIG-METRIC-001/002). | `inference.coverage.CoverageRecord.__post_init__` rejects a `searched_not_found` record with empty `sources_searched` (mirroring the `graph_annotations.coverage_record` CHECK); `probe_coverage_records` refuses an anonymous negative. Proven by `tests/inference/test_coverage.py::test_searched_not_found_requires_sources_searched`, `::test_probe_requires_named_sources`. |
| RISK-P9-02 | **Discovery-probe negatives are discarded** — the more informative half of an enumeration is thrown away, so a new portal/agency/tenant cannot be detected later without re-probing, and "we found N" never becomes "we tested M, N exist" (SIG-METRIC-002a). | `inference.coverage.probe_coverage_records` retains every confirmed-absent candidate as a `searched_not_found` `CoverageRecord`. Proven by `tests/inference/test_coverage.py::test_probe_retains_only_the_confirmed_absent_candidates`, `::test_probe_is_a_denominator_present_plus_absent_equals_candidates`. |
| RISK-P9-03 | **The four absence kinds collapse** — `not_researched` renders identically to `searched_not_found`, so "we have not looked" reads as "we looked and found nothing" (SIG-TIME-010/012). | Each of the four §32.1 coverage kinds has a distinct machine token via `db.absence.render_coverage_kind`; `CoverageRecord.public_view` carries it, and `not_applicable` (no epistemic state) is distinct from every "unknown". Proven by `tests/inference/test_coverage.py::test_four_kinds_render_distinguishably_in_the_api_view`; `tests/unit/test_absence.py::test_render_coverage_kind_covers_all_four_kinds_distinguishably`. |
| RISK-P9-04 | **An aggregate ships without a denominator** — "37 agencies share data" published with no evaluable population and no not-evaluable count, implying completeness (SIG-METRIC-003). | `PublishedAggregate` carries denominator + not-evaluable, and `assert_denominated` refuses a bare count as a type error; per-jurisdiction counts are all denominated by agencies known. Proven by `tests/inference/test_denominators.py::test_bare_count_is_not_publishable`, `::test_jurisdiction_coverage_denominates_every_count`. |
| RISK-P9-05 | **Freshness is measured in flat days** — a two-year-old immutable contract date is flagged stale, or a two-year-old FAST active count is treated as fresh (SIG-METRIC-006). | `inference.freshness` derives currency `C1..C4` from the predicate's volatility class and half-life (reusing `reconcile.weight.currency`, §28.3), so the same age yields opposite freshness by predicate. Proven by `tests/inference/test_freshness.py::test_same_age_yields_different_currency_by_volatility`, `::test_immutable_is_never_stale_however_old`. |
| RISK-P9-06 | **A population total is published** — a capture–recapture or multi-list estimate ships (even caveated), whose known failure mode is *understating* the surveillance footprint SIG exists to document (SIG-METRIC-008/008a/010). | The estimators are executable refusals (`capture_recapture_population`, `multi_list_log_linear_population` always raise `ProhibitedEstimateError`); `CompletenessStatement`/`assert_no_population_total` reject an implied denominator of reality; the sole exception (`RecordsDerivedRecall`) is constrained to pre-registered, within-half-life, non-extrapolated method-recall. Proven by `tests/inference/test_completeness.py::test_capture_recapture_is_never_published`, `::test_completeness_statement_rejects_a_denominator_of_reality`, `::test_records_derived_recall_window_must_beat_the_half_life`. |

### Provenance-completeness target (SIG-METRIC-005)

| id | Item | Compensating control |
|---|---|---|
| RISK-P9-07 | SIG-METRIC-005 targets 100% of published claims resolvable to an evidence artifact; reaching 100% depends on upstream connector coverage that lands over later phases, not on P09.1. | The *metric* is deterministic and its shortfall is materialized as a defect list (`inference.denominators.provenance_completeness`), so any gap is an actionable list of claim ids, not a statistic. Proven by `tests/inference/test_denominators.py::test_provenance_shortfall_is_a_defect_list_not_a_statistic`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-038 | The §32 coverage-metrics layer lives in `inference/` (the §47 home for derived metrics; no dedicated `metrics/` package is added) as **pure-Python** value objects aligned with `db/deploy/graph_annotations.sql`, **not** persisted to Postgres and **not** served over HTTP here — persistence + the read-API coverage statement are P14.1, the web surfaces P15.5, continuing the ADR-031/036/037 precedent. It **reuses** `db.absence` (extended only with the fourth `not_applicable` rendering; `AbsenceRendering.state` widened to `Optional`) and `reconcile.weight.currency` rather than re-encoding the four states or a second freshness notion. The capture–recapture / multi-list prohibitions are implemented as functions that **always raise**, so the §32.5 MUST NOT is gated by a test. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P9-08 | SIG-TIME-012 "distinguishable in the **UI**" | The UI (`web/`, TypeScript) is deferred to Phase 15; there is no browser surface to drive here | The **API-contract** half is deterministic and tested (distinct `absence_code`/`label` per kind in `CoverageRecord.public_view`); the UI rendering is a tracked P15.5 deliverable that consumes these tokens. |

## Phase 10 — Research-task generation (P10.1 — the task-coordination engine)

Per §53 / SIG-ENG-031, the phase's risk-register entries. P10.1 owns the detector-as-data
contract, the lifecycle/disposition vocabulary, geographic queues, anti-abuse, and the
SIG-owned local-group registry (ADR-039). The concrete catalog is P10.2; the
records-request path is P10.3.

### Design risks retired by executable checks (SIG-METRIC / SIG-TASK)

| id | Risk | Compensating control |
|---|---|---|
| RISK-P10-01 | **"Research this" tasks** — a task type with no testable closing condition can never be decided done, so it can only leave the queue on success and the backlog only grows (SIG-TASK-002, M-17). | `tasks.spec` models `closing_condition` as a `Callable[[Facts], bool]`, and `TaskTypeRegistry.register` refuses a type whose condition is `None` (`UntestableClosingConditionError`). Proven by `tests/tasks/test_spec.py::test_untestable_closing_condition_cannot_register`. |
| RISK-P10-02 | **Stale tasks linger** — evidence arrives by another route but the task stays in the queue, wasting mapper attention (SIG-TASK-006). | The same callable detector is re-evaluated by `TaskPool.sweep_invalidations`; a task whose detector no longer fires is silently invalidated. Proven by `tests/tasks/test_lifecycle.py::test_auto_invalidate_when_detector_stops_firing`. |
| RISK-P10-03 | **The queue can only grow** — "searched, found nothing" is unrecordable, so a negative result becomes nothing instead of data (SIG-TASK-009, M-17). | `resolved_no_evidence_exists` is reachable **only** through `tasks.dispositions.resolve_no_evidence_exists`, which builds a `searched_not_found` `CoverageRecord` (reusing P09.1, inheriting the `sources_searched`-required invariant) before closing the task; `ResearchTask.close` refuses the disposition directly. Proven by `tests/tasks/test_dispositions.py::test_resolved_no_evidence_exists_writes_a_coverage_record`, `::test_no_evidence_exists_is_unreachable_through_plain_close`. |
| RISK-P10-04 | **Geographic claiming hardens into gatekeeping** — a claim becomes de-facto exclusivity and defeats the federation principle (SIG-TASK-010/011). | `any_contributor_may_work(task)` takes no contributor and no claim (it is `task.is_open`), so no code path lets a claim exclude anyone; claims expire (`GeographicClaim.is_active`) and only affect ordering, not membership. Proven by `tests/tasks/test_geographic.py::test_a_claim_never_grants_exclusivity`, `::test_claims_expire_without_renewal`. |
| RISK-P10-05 | **Volume gamification** — a leaderboard ranking contributors by volume produces low-quality submissions at scale (SIG-TASK-012). | `volume_leaderboard` is an executable refusal (always raises `ProhibitedLeaderboardError`); `recognize` derives recognition only from *verified* contributions with no score/rank field. Proven by `tests/tasks/test_recognition.py::test_volume_leaderboard_is_an_executable_refusal`, `::test_recognition_ignores_unverified_volume`. |
| RISK-P10-06 | **One badly-modelled entity floods the queue** (SIG-TASK-013). | `TaskPool.generate` enforces `(task_type, subject)` duplicate suppression and a per-subject `RateLimiter`; deduplicated generation does not consume budget. Proven by `tests/tasks/test_lifecycle.py::test_pool_refuses_to_flood_one_subject_with_task_types`, `::test_duplicate_suppression_by_task_type_and_subject`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-039 | The task engine lives in `tasks/` as **pure-Python** value objects aligned to `research_task` (`db/deploy/graph_annotations.sql`), **not** persisted to Postgres and **not** served/claimed over HTTP here — persistence and the contributor API/UI are downstream, continuing the ADR-031/036/037/038 precedent. `detector`/`closing_condition` are modelled as **callables** (not free text) so testability is mechanical; `resolved_no_evidence_exists` is routed through a bridge that writes a `CoverageRecord` first; and the anti-abuse MUSTs are executable (a raising `volume_leaderboard`, a per-subject `RateLimiter`). `tasks` gains a `sig-inference` dependency (one-directional). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P10-07 | The concrete detector catalog (§33.2) and the `Facts` shape its detectors read | The 34 detectors and their real graph-query surface are **P10.2**; this ticket owns the DSL they register against | The DSL is exercised with representative in-memory `Facts` fixtures; P10.2 pins the query surface to the real graph. Registration/lifecycle/dedup are all tested against the engine now. |
| RISK-P10-08 | Persistence of tasks, claims, and local groups (no `local_group`/claim DDL exists in Appendix C) | Live Postgres persistence and the claiming API are downstream; Appendix C names no `local_group` table | Fields track the `research_task` DDL; SIG-TASK-014's ownership guarantee is met by a self-contained in-memory registry with no external dependency (F1.9). Adding a schema is an additive downstream change (ADR-039 revisit trigger). |

## Phase 10 — Research-task generation (P10.2 — the detector catalog)

Per §53 / SIG-ENG-031, P10.2's risk-register entries. P10.2 owns the concrete §33.2
catalog (the 34 task types) and the §31 contradiction→task map (ADR-040), registered
against the P10.1 engine.

### Design risks retired by executable checks (SIG-TASK)

| id | Risk | Compensating control |
|---|---|---|
| RISK-P10-09 | **A "research this" catalog row** — a §33.2 task type ships without a testable closing condition, so it can never leave the queue on any disposition but success and the backlog grows (SIG-TASK-002/003). | Every row is registered through `TaskTypeRegistry.register`, which refuses an untestable closing condition; `build_catalog()` registering all 34 is therefore the proof. Proven by `tests/tasks/test_tasks_catalog.py::test_building_the_catalog_registers_every_type`, `::test_every_catalog_type_has_a_testable_closing_condition`. |
| RISK-P10-10 | **A contradiction with no route to resolution** — a §31 detector fires but no task type exists to work it, so detection is "just an alarm" (SIG-TASK-004). | `CONTRADICTION_TASK_MAP`'s keys are asserted to be exactly `reconcile.model.CONTRADICTION_TYPES` and every value a registered catalog slug, so an unrouted contradiction type is a failing test. Proven by `tests/tasks/test_tasks_catalog.py::test_every_contradiction_type_maps_to_a_task`, `::test_every_mapped_task_type_is_a_registered_catalog_type`. |
| RISK-P10-11 | **Stale catalog tasks linger** — a catalog detector keeps firing after the gap it names is closed, wasting contributor attention (SIG-TASK-006). | Each row is built so its detector stops firing exactly when the gap closes; the P10.1 `TaskPool.sweep_invalidations` then silently invalidates it. Proven per-type (all 34) by `tests/tasks/test_tasks_catalog.py::test_task_auto_invalidates_when_its_condition_clears`. |
| RISK-P10-12 | **Catalog drifts from the spec count** — §33.2 grows/shrinks but the catalog does not, or the Part X "32" figure is used instead of §33.2's 34. | `CATALOG_SIZE = 34` and the unique-slug count are asserted against §33.2 as the count authority. Proven by `tests/tasks/test_tasks_catalog.py::test_catalog_has_exactly_the_34_types_of_the_count_authority`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-040 | The catalog's detectors read representative in-memory `Facts` keys (with committed positive/negative fixtures), **not** the live materialized graph — continuing ADR-039's scaffolding boundary (RISK-P10-07); binding the keys to the real query surface is downstream. SIG-TASK-004 is modelled as a **many-to-one** map from the §31 `contradiction_type` vocabulary to catalog task slugs (the catalog is coarser than the type vocabulary), cross-checked against `reconcile.model.CONTRADICTION_TYPES` as a **test-only** import so no new runtime dependency is added to `tasks`. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P10-13 | The catalog detectors' binding to the real materialized-graph query surface (they read documented `Facts` keys, not live projections) | No graph-query surface exists for the detectors to bind to yet; ADR-039/040 scope it downstream | Each row's contract (which facts it reads, when it fires, when it closes) is pinned with committed positive/negative fixtures and an end-to-end auto-invalidation test; binding the keys to live projections is an additive downstream change (ADR-040 revisit trigger). |
| RISK-P10-14 | Task routes for `temporal_impossibility` and `undeclared_copying` are mapped ahead of any reconcile detector that emits them | The P08.2/P08.3 workflows do not yet emit these two of the nine `contradiction_type`s | The map covers the **full** §31 vocabulary so a future emitter already has a route; the chosen catalog task is revisited if a real emitter proves it a poor fit (ADR-040 revisit trigger). |

## Phase 10 — Research-task generation (P10.3 — records-request generation)

Per §53 / SIG-ENG-031, P10.3's risk-register entries. P10.3 owns the §36 records-request
generator (ADR-041): the 51-jurisdiction records-law table, emit-with-the-correct-statute,
operationally-binding residency routing, versioned templates with measured success rates,
and the consent gate — built on the P10.1 engine and the P09.1 coverage model.

### Design risks retired by executable checks (SIG-TASK)

| id | Risk | Compensating control |
|---|---|---|
| RISK-P10-15 | **A residency barrier is read as an absence of surveillance** — a non-resident-blocked jurisdiction records `searched_not_found`, so thin coverage there looks like "we looked and there is nothing" instead of "we are legally barred from filing" (SIG-TASK-016a, §32.2). | The barrier writes a `not_researched` `CoverageRecord` (never `searched_not_found`), attributed to the statute in `search_method`; the emit path is unreachable for a non-resident/unknown-residency filer in a restricted state. Proven by `tests/tasks/test_tasks_records_request.py::test_non_resident_in_restricted_jurisdiction_refuses_routes_and_records_coverage`, `::test_residency_barrier_coverage_is_never_searched_not_found`, `::test_unknown_residency_defaults_to_restrictive`. |
| RISK-P10-16 | **A request cites the wrong statute** — the emitted request names a citation that does not match the target jurisdiction, or SIG files on a contributor's behalf without consent (SIG-TASK-015/018). | The citation is looked up in the reviewed 51-jurisdiction table (never guessed) and the emit path refuses a filer without explicit consent and a public-act acknowledgement. Proven by `tests/tasks/test_tasks_records_request.py::test_emits_the_correct_statute_for_the_jurisdiction`, `::test_emit_without_consent_is_refused`, `::test_emit_without_public_act_acknowledgement_is_refused`; the table's per-row completeness/uniqueness by `tests/tasks/test_tasks_records_law.py`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-041 | The residency barrier is recorded with `absence_kind = not_researched` (attributed to the statute in `search_method`), **not** a new `legal_barrier` kind — the four-kind §9.5/§32.1 vocabulary is a frozen P09.1/DDL contract and this is additive. "Route to the geographic queue" is realized as a **routing decision** (`ResidencyBlock` naming the jurisdiction's local filers + active claimants), not a mutation of the P10.1 `TaskPool`/`GeographicQueue`, because that queue is a claims-and-ordering coordinator, not a task container; applying the routing through the live pool is downstream. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P10-17 | The per-jurisdiction operational-detail fields (`response_deadline`, `fee_rules`, `appeal_path`) are honest seed summaries, not counsel-reviewed legal advice | Per-jurisdiction counsel review is a Phase-0/legal deliverable, not an engineering one; a statute's fixed number often does not exist ("reasonable time") | The two load-bearing fields (`citation`, `residency_required`) are asserted by the suite; the operational fields are **versioned data** (`table_version`), so a counsel correction is a tracked migration, not a code change (ADR-041 revisit trigger). |
| RISK-P10-18 | Template success rates are measured through an in-memory `TemplateOutcomeLog` fed by the caller, not by a live filing/response backend (SIG-TASK-017) | No filing/response ingestion backend exists yet (the `records` connector, P07.2, ingests replies; wiring outcomes back to the log is downstream) | The measurement surface (per-version rate + the min-sample-guarded revision flag) is fully implemented and tested; feeding it from real filed outcomes is an additive downstream change (ADR-041 revisit trigger). |

## Phase 11 — Flock portal layer (P11.1 — the `flock_portal` connector)

Per §53 / SIG-ENG-031, P11.1's risk-register entries. P11.1 adds the `flock_portal` connector
(ADR-042): the Eyes on Flock portal layer via the aggregator's public CC-BY-SA-4.0 API, in its
own separable compartment, keyed on the upstream snapshot field, honouring a challenge as a
refusal, and feeding P08.2's §29.3/§29.7 reconcilers. It is external-API-gated (SIG-ENG-035): it
MUST NOT block later tickets.

### Design risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P11-01 | **R-02 residual — the aggregator API is the single lawful route to the portal layer** (SIG-INGEST-030/031). Access is resolved under public CC-BY-SA terms, but the dependency remains a single point of failure, and the tempting "fix" is a challenge-defeating crawler. | The three SIG-INGEST-031 fallbacks are retained as named routes in code (records acquisition, contributor capture, partner archive — `fallback_routes`/`fallback_tasks_for_gaps`), and a challenge-defeating crawler is explicitly not a route. Proven by `tests/connectors/test_flock_portal.py::test_the_three_fallback_routes_are_retained_and_named`, `::test_missing_aggregator_fields_route_to_the_fallbacks`. The archival-succession offer (SIG-CONTRIB-013) and partnership outreach remain Phase-0 deliverables (RISK-P0-17/P0-20, SIG-INGEST-030a/032). |
| RISK-P11-02 | **A bot-management challenge is worked around** — retried, proxied, or solved — turning a lawful connector into a circumvention tool (SIG-INGEST-036/037, §26 rule 4, a legal posture). | The connector holds no HTTP client of its own and egresses only through the shared `PoliteFetcher`, which raises `ChallengeEncountered` on a 401/403/429; the pipeline records it as a first-class disappearance and never retries. Proven by `tests/connectors/test_flock_portal.py::test_challenge_response_is_honoured_as_a_refusal`, `::test_the_fetcher_never_defeats_a_challenge`; the module contains no circumvention code (`assert_no_circumvention` still governs the fetcher). |
| RISK-P11-03 | **Share-alike portal data leaks into the permissive CC-BY graph** (SIG-LIC-004a) — a portal claim exported under CC-BY-4.0 would strip the ShareAlike obligation. | Every row is stamped `compartment='portal'` / `license='CC-BY-SA-4.0'` (`_stamp`), and the computed export gate fails the build on any merge with a CC-BY source. Proven by `tests/connectors/test_flock_portal.py::test_rows_land_in_the_cc_by_sa_portal_compartment`, `::test_export_merging_portal_with_the_cc_by_graph_fails_the_build`. |
| RISK-P11-04 | **Change detection reads SIG's fetch clock instead of the upstream snapshot** — SIG would poll faster than the upstream refreshes (adding load without information) and misdate observations (SIG-INGEST-030c). | `observed_at` and `is_poll_due` key on the upstream `data_last_updated` field; the portal's declared freshness is recorded as `portal_last_updated_declared` but never used as an observation time. Proven by `tests/connectors/test_flock_portal.py::test_observed_at_is_the_upstream_snapshot_date_not_fetch_time`, `::test_is_poll_due_keys_on_the_snapshot_and_respects_the_refresh_cadence`. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P11-05 | The connector is not DB-wired and runs no live `/api/v1/data` fetch in CI; cross-capture snapshot diffing (§29.7) and portal appearance/disappearance detection (SIG-INGEST-035) are module functions invoked by the backfill/change-feed driver rather than a single connector run's output | A single run is a pure function of one capture (SIG-INGEST-003), so it cannot diff two captures; the live transport and the driver that supplies multiple captures land with orchestration, exactly as every prior connector defers the live HTTP transport (ADR-028/029) | The pure diff/appearance/disappearance logic is fully implemented and tested against committed multi-snapshot fixtures (`test_snapshot_diff_produces_per_field_change_events_via_p08_2`, `test_portal_disappearance_produces_an_event_and_a_task`, `test_portal_appearance_produces_an_event_and_a_no_known_deployment_task`); wiring it to the live driver is an additive downstream change (ADR-042 revisit trigger). |
| RISK-P11-06 | The §29.3 sharing-edge asymmetry contradictions and research tasks are produced by the reconciler but not folded into the connector's L1 claim stream (SIG-RECON-035, owned by P08.2) | The reconciler mints non-deterministic task ids that would break the run's reproducibility fingerprint (SIG-INGEST-003), and finding emission is P08.2's responsibility, not the connector's | The connector produces the raw edges and invokes the reconciler (`reconcile_portal_sharing`, exposed via `FlockPortalConnector.reconcile_sharing`); asymmetry firing is tested (`test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler`); a driver persists the findings (ADR-042 revisit trigger). |
| RISK-P11-07 | `upstream_refresh_days` is a conservative data default (1 day), not the confirmed upstream cadence (SIG-INGEST-030a) | The confirmed refresh cadence is a Phase-0 outreach deliverable, not an engineering one | The cadence is **versioned data** (`data/flock_portal_vocab.toml`), so a confirmed value is a one-line data edit, not a code change; the poll-suppression logic keyed on it is tested (`test_is_poll_due_keys_on_the_snapshot_and_respects_the_refresh_cadence`) (ADR-042 revisit trigger). |

## Phase 11 — Flock portal layer (P11.2 — the `audit_structural` connector)

Per §53 / SIG-ENG-031, P11.2's risk-register entries. P11.2 adds the `audit_structural` connector
(ADR-043): the agency Flock audit-export layer parsed into structural aggregates and configured
edges only — the point in the system where the Part VIII "no searchable database of people's
movements" line bites hardest. It is external-source-gated (SIG-ENG-035): it MUST NOT block P12+.

### Design risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P11-08 | **A per-search or per-plate row is ingested** — the audit exports are per-search logs, so a naïve connector would build exactly the searchable movement database Part VIII forbids (§18.1, SIG-STORE-025). | The per-search rows are read transiently and consumed in `extract`; only aggregates leave. The bright line is a schema property: `assert_no_per_row_output` rejects any emitted row whose keys collide with the data-driven `forbidden_output_columns` (plate/officer/search_id/timestamp) as a `PerRowLeak`. Proven by `tests/connectors/test_audit_structural.py::test_no_per_search_or_per_plate_row_is_produced` (the fixture carries Plate + Officer columns; none leak), `::test_the_per_row_schema_gate_rejects_a_plate_bearing_row`. |
| RISK-P11-09 | **A derived HIBF export is ingested as though it were the agency record** (SIG-INGEST-046a) — hashed plates and inferred names would enter the graph as observations. | The connector runs against a dedicated `agency_audit_export` source (the agency's OWN public record, CC0-1.0), never `have_i_been_flocked`; officer/name resolution is discharged by exclusion (no per-search/per-person row is ingested). Recorded in `connectors/data/sources.toml` and ADR-043. |
| RISK-P11-10 | **The audit `Camera Count` is silently merged into another count** — summed with portal/vendor counts into a fabricated "true count" (SIG-RECON-026). | It lands as an independent `active_device_count` claim carrying its `count_basis` and is reconciled by P08.2's `reconcile.counts.reconcile_counts`, which resolves each basis on its own and surfaces disagreement as a finding — never a merged total. Proven by `tests/connectors/test_audit_structural.py::test_camera_count_is_reconciled_against_other_counts_never_merged_via_p08_2` (resolved value ≠ the sum; the audit count retained as dissenting). |
| RISK-P11-11 | **A `***` redaction is conflated with an empty cell** — a withheld reason read as "no reason", erasing the negative space (SIG-INGEST-046). | `classify_cell` is the single reader every cell goes through, returning `redacted` / `empty` / `present`; a redacted reason maps to the distinct `redacted` category (never `unspecified`) and is recorded as an `audit_cell_redacted` state. Proven by `tests/connectors/test_audit_structural.py::test_classify_cell_distinguishes_redacted_from_empty_and_present`, `::test_reason_category_keeps_redacted_distinct_from_unspecified`, `::test_redacted_and_empty_reasons_produce_distinct_aggregate_buckets`. |
| RISK-P11-12 | **The four audit source types are silently unioned** — organization / network / portal-public / event-log rows merged as if interchangeable (§23.7). | `assert_audit_source_type` enforces the closed set and `audit_source_type` is stamped on every aggregate / count / lifecycle row, so the types are distinguishable and never merged. Proven by `tests/connectors/test_audit_structural.py::test_the_four_audit_source_types_are_the_closed_set`, `::test_every_aggregate_records_its_source_type_and_they_are_not_unioned`. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P11-13 | The `UsageAggregate` analytics substrate (Hive-partitioned Parquet on DuckDB, small-cell suppression, the UUID+period join) is not built here | §18's substrate is **P12.1's** deliverable; building it here would pre-empt that ticket | The connector *writes* the `usage_aggregate` rows with the full §11.16 predicate surface + source-agency provenance so P12.1 can land them; suppression/substrate are downstream (ADR-043 revisit trigger). |
| RISK-P11-14 | The §29.3 sharing asymmetry contradictions/tasks and the §29.1 count findings are produced by the P08.2 reconcilers but not folded into the connector's L1 claim stream | The reconcilers mint non-deterministic ids that would break the reproducibility fingerprint (SIG-INGEST-003), and finding emission is P08.2's responsibility | The connector produces the observations and invokes the reconcilers (`reconcile_audit_sharing`, `reconcile_camera_counts`); asymmetry firing is tested (`test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler`); a driver persists the findings (ADR-043 revisit trigger). |
| RISK-P11-15 | The connector is not DB-wired and runs no live public-records fetch in CI; cross-export de-duplication across many captures is bounded to within-run window blocks | No live records backend is wired (the transport lands with orchestration, as with every prior connector, ADR-028/029/042); combining aggregates across captures is P12.1's aggregation boundary | The pure aggregation / dedup / count / sharing logic is fully implemented and tested against committed CSV fixtures; `deduplicate_events` realizes the `(source_org, searching_org, window)` block dedup and is tested (`test_overlapping_exports_are_deduplicated_by_window_block`) (ADR-043 revisit trigger). |

## Phase 12 — Usage and network layer (P12.1 — usage aggregates and the analytics boundary)

Per §53 / SIG-ENG-031, P12.1's risk-register entries. P12.1 builds the §18 analytics boundary
(ADR-044): the DuckDB/Parquet substrate, the UUID+period join, partition-as-evidence, and
rationale-driven small-cell suppression. This is a **hard privacy line** — the store the boundary
projects is derived from per-search audit logs, so it is where "no searchable database of people's
movements" (Part VIII) is enforced at rest and at query time.

### Design risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P12-01 | **A per-search or per-plate row (or a plate-capable column) reaches the analytics store** — a columnar side store becomes the back door the Postgres bright line closed (§18.1, SIG-STORE-025/026). | The analytics schema is a closed column set (`ANALYTICS_COLUMNS`) carrying only UUIDs + period + facts + lineage; `assert_no_name_or_plate_column` / `assert_analytics_schema` (token-based, mirroring the Postgres test) run in `AnalyticsRow.__post_init__`, in `write_partitions` before any bytes are written, and as `sig-db analytics assert-schema`. Proven by `tests/db/test_analytics.py::test_no_analytics_column_is_a_name_or_plate_column`, `::test_plate_or_name_columns_are_rejected`, `::test_project_aggregate_keys_on_uuids_and_drops_names`. |
| RISK-P12-02 | **Partitions are joined to the graph by name** — reintroducing, invisibly and in a layer nobody watches, the entity-resolution failure P6 prevents (§18.3, SIG-STORE-028). | There is no name column to join on, and `assert_join_keys` refuses any key outside `{searching_org_id, source_org_id, period}` (a name key is a hard `JoinKeyError`), so `build_graph_join_sql` cannot construct a name join. Proven by `tests/db/test_analytics.py::test_assert_join_keys_refuses_name_keys`, `::test_join_sql_refuses_to_build_on_a_name_column`, `::test_partitions_join_to_the_graph_by_uuid`. |
| RISK-P12-03 | **A summary crosses the boundary without provenance** — an aggregate figure is published with no evidence, breaking the §10.1 chain (SIG-STORE-029). | Each partition is content-addressed (interop multihash) and registered as an `evidence_artifact`; a claim is created only as a *summary statement* citing the partition digest (`cites_partition_digest`). Proven by `tests/db/test_analytics.py::test_written_partitions_are_content_addressed`, `::test_partition_is_registered_as_an_evidence_artifact`, `::test_summary_claim_cites_the_partition_as_evidence`. |
| RISK-P12-04 | **Small-cell suppression gets the institutional-vs-individual distinction backwards** — accountability information ("an agency ran 3 immigration-reason searches") is suppressed while a private person's small cell leaks; or a suppressed cell is published as a disclosive zero (SIG-STORE-030/031/032). | `db.suppression` decides by §18.4 rationale, not size: `institutional_conduct` publishes even when small; `protects_individual` suppresses to `null` + `suppressed_flag` + `k_threshold` (never zero); `ambiguous` defaults to suppress + raise a review task. Proven by `tests/db/test_suppression.py::test_institutional_small_count_is_published_not_suppressed`, `::test_individual_small_count_is_suppressed_to_null_never_zero`, `::test_ambiguous_small_cell_is_suppressed_and_raises_a_review_task`. |
| RISK-P12-05 | **A suppressed cell is recoverable by subtraction** from a published margin total (SIG-STORE-030). | `suppress_group` applies complementary (secondary) suppression when exactly one cell in a published margin is suppressed (preferring a non-institutional cell; flagging review if forced onto an institutional one), and withholds the margin total when no cell can absorb it. Proven by `tests/db/test_suppression.py::test_a_lone_suppressed_cell_triggers_complementary_suppression`, `::test_single_cell_margin_withholds_the_total_when_it_would_be_invertible`. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P12-06 | Resolution of textual org identifiers → `sig_entity_id` UUIDs for `project_aggregate` is the caller's responsibility, not performed inside `db.analytics` | Entity resolution is P6's concern (the connector link stage); folding it into the analytics layer would duplicate and could diverge from the canonical resolver | `project_aggregate` takes the resolved UUIDs as explicit inputs and deliberately drops any name field so a name cannot cross the boundary (SIG-STORE-028); the layering is recorded in ADR-044. |
| RISK-P12-07 | The suppression review tasks (ambiguous cells; complementary suppression forced onto an institutional cell) are produced as `review_tasks` strings, not yet enqueued into the P10.1 research-task engine | Task persistence and the queue are owned elsewhere; wiring them here would couple the substrate to the task engine | `suppress_group` surfaces every review reason in `GroupSuppressionResult.review_tasks`; a driver enqueues them (ADR-044 revisit trigger). Proven present by `tests/db/test_suppression.py::test_ambiguous_small_cell_is_suppressed_and_raises_a_review_task`, `::test_complementary_falls_on_institutional_only_when_forced_and_flags_review`. |
