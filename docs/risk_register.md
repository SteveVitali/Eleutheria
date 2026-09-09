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
| RISK-P0-05 → BL-001 | SIG-PUB-008 two-reviewer *concurrence itself* (the human judgement) | The written human concurrence is agentic, not deterministic | The **gate** around it is deterministic and tested (`test_policy_officer.py`): no publish without two independent, written, concurring reviewers |
| RISK-P0-06 → BL-001 | SIG-INGEST-037 no-circumvention as a *legal posture* | "Requires counsel" is a process fact, not a unit test | `assert_no_circumvention` fails closed on the enumerated techniques; deviation is an ADR-level decision |
| RISK-P0-10 → BL-036 | SIG-GOV-014/015/016 governance, Code of Conduct, editorial board, and funding policy | Adopting and *operating* prose governance (a real board, real enforcement) is agentic, not a unit test | The documents are published and link-checked (`test_governance_docs.py`); the deterministic officer-naming gate (`test_policy_officer.py`) is the board's enforced counterpart |
| RISK-P0-11 → BL-035 | SIG-CONTRIB-007/008 know-your-rights guidance and the detained-contributor policy | Correctness of jurisdiction-aware legal guidance is agentic and needs counsel review | Policy published and presence-tested (`test_governance_docs.py`); guidance flagged for counsel review before launch |
| RISK-P0-12 → BL-030 | SIG-GOV-021 degraded-but-alive mode is *tested* (incl. dormant-scheduler keepalive) | The keepalive + its test are built in the operations phase, not P00.3 | Posture documented now (`docs/governance/governance-and-code-of-conduct.md`); the executable test is a tracked deliverable of the ops phase |

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
| RISK-P0-19 → BL-032 | SIG-LIC-001 per-source rights *review* (which SPDX, whether redistributable) | Reading each source's terms and judging redistributability is agentic, not a unit test | The registry *shape* is enforced (rights populated-or-`UNDETERMINED`, fail-closed export gate); the review itself is a tracked, per-row research task, `UNDETERMINED` until done |
| RISK-P0-20 → BL-033 | SIG-INGEST-030 Eyes on Flock partnership / archival-succession *outreach* | Conducting and concluding outreach is agentic (§22.5) | Access is resolved under public CC-BY-SA terms and the Stage-0 outcome is recorded on the row; partnership/succession outreach flagged as a remaining Phase-0 deliverable (SIG-INGEST-030a/032) |

## Phase 1 — Ontology as code + vocabularies (P01.1)

### Risk retired

| id | Risk | How it is retired |
|---|---|---|
| RISK-P1-01 | **Ontology churn** — the schema, vocabularies, DDL, and docs drift apart, and a taxonomy written in 2026 silently rewrites the meaning of past claims (§20) | One LinkML source of truth (ADR-007) generates all five downstream forms plus SKOS; a deterministic CI gate fails if any committed artifact differs from a fresh generation (`make verify-gen`, `test_generation_gate.py`). Vocabularies publish as versioned SKOS at stable per-version IRIs (SIG-STORE-035) and are immutable once published (SIG-STORE-036), so later change is a versioned migration, not an edit. |

### Unverifiable-by-automation / scaffolded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P1-02 → BL-044 | SIG-STORE-039 (published crosswalks to *every* external taxonomy SIG ingests) | The full, curated crosswalk to each live external vocabulary is a research task that grows as connectors land (P04+) | The crosswalk *mechanism* is built and tested: many-to-many rows with a SKOS mapping relation and a `lossy` flag, seeded for the six §20.3 taxonomies (`vocab/crosswalks.yaml` → `generated/skos/crosswalks.nt`). Completeness is a tracked per-connector deliverable. |
| RISK-P1-03 → BL-045 | SIG-EPIS-017 (the full genre × predicate directness matrix) | The complete matrix is owned and consumed by the reconcile ruleset (P08); it is calibrated against real evidence | Each predicate carries a full directness *row* over the published §10.5 artifact genres (SIG-ONTO-067, tested); the matrix predicates use the published §10.5 values, others a conservative default, completed in P08. |
| RISK-P1-04 → BL-045 | SIG-RECON-009 (volatility half-lives recalibrated once change-rate data exists) | Half-lives are an initial assignment until SIG has measured change rates | Initial per-predicate volatility + half-life from §28.3 are registered and tested; recalibration is a ruleset-data change in a later phase, not a schema change. |

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
| RISK-P2-03 → BL-048 | SIG-STORE-018 (a CI job regenerates a sample of resolution rows from their stored inputs and asserts they match) | Resolution *recomputation* needs the resolver, which is P08.1 (`reconcile`); this ticket provides the table + constraints only | The resolution *shape* — stored inputs (`considered_claims`, `dissenting_claims`, `strategy_id`, `ruleset_version`, `resolver_version`), the exclusion constraint, and independent versioning — is built and tested; the determinism rebuild job is a tracked P08.1 deliverable. |
| RISK-P2-04 → BL-049 | SIG-STORE-045 (shipped DDL generated from the LinkML ontology) | Partitioning, triggers, RLS, and exclusion constraints are not expressible in LinkML; the physical enforcement layer is authored DDL that this ticket explicitly owns | The claim spine is authored as sqitch migrations (SIG-STORE-041) and the ontology remains the source of truth for the *logical* schema, vocabularies, and the predicate registry the DDL and its tests consume (`test_schema_integrity.py` reads the generated predicate registry). Reconciling the generated logical projection with the physical schema is tracked for the ontology/db seam. |

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
| RISK-P2-09 → BL-026 | SIG-EVID-007/008 (live WACZ capture of a JS-rendered portal with a real browser) | End-to-end capture needs a headless browser + a live source; running one per PR is slow, flaky, and hits third-party sites | The capture-set contract and the deterministic WARC→WACZ 1.1.1 packager are built and tested from fixtures (`evidence.capture`, `test_capture.py`); the real Playwright capture path (`capture_live`) ships behind the `capture` extra and is exercised by the connectors (P04+), mirroring how the DB tests gate on Docker. |
| RISK-P2-10 → BL-026 | SIG-EVID-017 (a CI test asserts re-running a pinned connector over pinned digests yields byte-identical claim tuples modulo `claim_id`/`sys_period`) | The connector that produces claim tuples is P04+; this ticket owns the evidence side | The reproducibility *machinery* is built and tested: a deterministic environment (`LC_ALL=C`/`TZ=UTC`, SIG-EVID-018), an `ingest_run` record of all reproducibility inputs (SIG-EVID-016), and the canonicalisation the CI test compares (`evidence.ingest_run.canonical_claim_tuple`, `test_ingest_run.py`). Deterministic packaging is proven (`test_capture.py::test_wacz_packaging_is_deterministic`). |

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
| RISK-P2-14 → BL-007 | SIG-TIME-005/012 also bind the **API and UI** rendering surfaces (`ongoing` with observation date; four absence states distinguishable) | The read API (`api/`, ADR-017) and the web UI (`web/`, ADR-014) are later phases; this ticket owns the shared rendering + query contract they consume | The conformant renderings and the distinguishable absence presentation are built and tested here (`db.temporal.render_valid_bound`/`assert_conformant_rendering`, `db.absence.render_absence`); a non-conformant "currently …" rendering is rejected in code, so the API/UI wire to a contract that already fails closed. |
| RISK-P2-15 → BL-048 | TI-6 (mutually-exclusive resolved intervals) and TI-7 (supersedes-chain acyclicity) as **whole-graph** guarantees | The pipeline checks (`db.invariants.check_ti6/7`) see only the batch a connector hands them; the resolver (`reconcile`, P08.1) and a nightly full-graph audit own the cross-batch view | Same-predicate L3 overlap is already a hard DB constraint from P02.1 (`resolution_no_overlap`); the batch checks catch within-run breaches now; the full-graph audit is a tracked P08.1 / nightly deliverable (§48). |

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
| RISK-P3-02 → BL-044 | SIG-IDENT-010 (the two classification axes) draws `operating_relationship` from a vocabulary | Rather than mint a competing enum, the relationship axis reuses the existing fourteen-role `Role` vocabulary (§12.4) — "purchaser but not operator" is a role over a specific deployment (`entity_role`), materialized when connectors assert roles in P04+ | The axes and their independence are modelled and tested now (`resolution.identity.TwoAxisClassification`); a conformance test grounds `organization_class` in `OrganizationType` and `operating_relationship` in `Role` (`test_vocab_conformance.py`), so the two-axis contract is fixed even though role edges are populated later. |
| RISK-P3-03 → BL-006 | Persisting registries and minting surrogate `entity_id`s end-to-end into Postgres | The registry-*ingest* orchestration (reading Census/FBI-CDE/IPEDS/… and writing entities + claims) is a connector concern (P04+); this ticket owns the identity model, the guards, and the row/claim emitters | The domain layer emits table rows (`Organization.to_row`, `OrganizationRelation.to_row`) and enforces every guard as pure, tested logic, and the physical layer is exercised against a real PG18+PostGIS via `tests/db/test_identity_registry.py`; surrogate minting is deterministic and idempotent (`resolution.identity.mint_surrogate`). Public `sig:` identifier minting, `normalize_org_name()`, the crosswalk, and the deterministic cascade are P03.2. |
| RISK-P3-04 → BL-047 | The legacy `Organization.succession` / `SuccessionKind` slots (P01.1) coexist with the reified `OrganizationRelation` | The reified, bitemporal relation is the authoritative model for organizational change (SIG-IDENT-016); the older per-entity slots predate this ticket and are retained additively for back-compat | New temporal-identity edges are written only as `organization_relation` rows with the seven-value vocabulary; the reified model is the one the fixtures and the physical test assert, and it is where later phases read succession from. |

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
| RISK-P3-07 → BL-044 | SIG-IDENT-002 UCR↔USPS table and the SIG-IDENT-033/034 crosswalk *content* | This ticket owns the *machinery* (the reference table, the export builders + licence gate), not the full national code table or the populated crosswalk rows, which a connector run (P04+) fills. | The table ships with the mandated divergences (NB→NE, GM→GU) and passes-through the identical majority; the export builders validate every ORI/GEOID and fail the build on a malformed row; publishing goes only through the licence gate (`export_crosswalk` → SIG-LIC-004). Populating rows end-to-end is a connector concern. |
| RISK-P3-08 → BL-046 | SIG-IDENT-031 dereferenceable `/id/<type>/<uuid>` HTTP endpoint + rendered HTML/JSON-LD/RDF representations | The URL construction and the content-negotiation *decision* are owned here as pure logic; the live HTTP route and the serialisers that render each representation are an API-surface concern (P07+ delivery). | `dereference_url` and `negotiate` are deterministic and tested; the representations they select (`html`/`json-ld`/`rdf`) are wired to real responders when the public API ships. |
| RISK-P3-09 → BL-044 | The Tier-2 collision list and the acronym/normalise ruleset are seed data, not the full data-generated corpus | The spec calls the collision list "data-generated"; here it is a versioned seed exclusion set with the correct shape and injection seam (`CascadeContext`), regenerated from the corpus in a later data pass. | Rulesets are versioned data (`data/*.toml`) with committed test vectors that run in CI (SIG-IDENT-022); changing what auto-writes is a reviewable data diff, and `CascadeContext.from_data()` is overridable so a regenerated list drops in without code change. |

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
| RISK-P4-04 → BL-023 | The real OCFL-backed `CaptureStore` adapter over `evidence.store.EvidenceStore` (SIG-INGEST-001, §17) | P04.1 owns the stage *contract* and ships the in-memory `CaptureStore` the tests and replay harness use; adapting the OCFL/S3 store to the protocol is a P04.2 concern (it drags object storage into every connector test). | The `CaptureStore` protocol (`put`/`get`/`has`, content-addressed) is the stable seam; the evidence store already writes content-addressed capture rows (P02.2), so the adapter is mechanical and does not change the framework contract (ADR-026). |
| RISK-P4-05 → BL-023 | Source-specific `discover/fetch/parse/extract/normalize` and a real HTTP `Transport` for `PoliteFetcher` (SIG-INGEST-006/007) | The framework is source-agnostic by design; the first concrete connectors (OSM/Atlas) and a real transport are P04.2/P04.3. | The `Transport` protocol and the `Connector` base class are the injection seams; a toy connector + fake transport exercise every framework guarantee end-to-end in CI, so a real connector inherits gate/isolation/lineage/replay/disappearance unchanged. *(Connector half retired by P04.2 — the `osm` connector is now built and tested; a real HTTP `Transport` is still owed, see RISK-P4-06.)* |

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
| RISK-P4-06 → BL-023 | Live Overpass fetching: a real HTTP `Transport` for `PoliteFetcher`, the OCFL `CaptureStore` adapter (carried from RISK-P4-04/05), and shared-layer handling of Overpass **429 → back off / poll `/api/status`** and **504 → shrink** (SIG-INGEST-045h). The framework's `PoliteFetcher` currently classifies 429 as a bot challenge → disappearance, which is wrong for Overpass slot exhaustion. | This ticket owns the source-specific stages + etiquette, all exercised over committed fixtures (SIG-PARSE-007); a real transport and the OCFL adapter are the live-wiring ticket, and reconciling the shared 429 semantics is framework surgery deliberately deferred (out of P04.2 scope — ADR-026/027). | The etiquette is built and tested as pure helpers now (`overpass_status_action` 429→back_off/504→shrink, `build_overpass_query` `[timeout]/[maxsize]` + no-space filters, `acquisition_mode` PBF-vs-tiled, `assert_own_or_public_instance`, `BulkStitchingForbidden`); the descriptive contact-carrying UA is already enforced by the shared `PoliteFetcher` (SIG-INGEST-045d). ADR-027 records the deferral and its revisit trigger. |
| RISK-P4-07 → BL-046 | A **physically separate** ODbL `physical_asset` table in the DB per §42.3. The Appendix-C `physical_asset` table carries the OSM columns inline and is not itself compartment-split. | Connectors are not DB-wired in P04.x (the framework asserts through the `ClaimSink` seam, RISK-P4-06); splitting the stored table is a DB/ontology concern, not a connector one. | Every OSM output row is stamped `license=ODbL-1.0`/`compartment=osm_physical` and the export gate (`policy.licensing.compute_export_license`, tested) fails any merge with the CC-BY graph, so the separation obligation (SIG-LIC-006) holds at the export boundary today; the stored-table split is tracked for the DB layer (ADR-027 revisit trigger). |

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
| RISK-P4-08 → BL-045 | Resolver-side **supersession / temporal qualification** of an Atlas row by later evidence (§23.3, OL-2D-AT-06). The connector does not itself decide when a later claim supersedes an Atlas row. | Reconciliation/supersession is the resolver's job (P08.x), explicitly out of scope for a connector ticket; deciding it here would duplicate and pre-empt that layer. | Every Atlas row is **append-only** and carries the full provenance a resolver needs (source attribution, Atlas vocabulary version, candidate agency identifier, upstream links), and the connector marks nothing "current"/authoritative — so supersession is a pure resolver decision over existing data, tested by `test_rows_are_append_only_with_no_current_value_flag`. ADR-028 records the deferral. |
| RISK-P4-09 → BL-044 | An **exhaustive** Atlas category → family map. Only the five crosswalk-seeded families (ALPR, face recognition, gunshot detection, UAS, camera-federation hub) are mapped; the real Atlas taxonomy carries more. | The authoritative external crosswalk (`ontology/vocab/crosswalks.yaml`) seeds exactly these; extending the map is a reviewed §20 data migration, not code, and guessing the remainder would fabricate mappings (SIG-STORE-040). | An unmapped category is recorded as an unmapped category **+ a research task** (never a guessed family), tested by `test_unmapped_category_files_a_research_task_and_writes_no_deployment`; the map grows by additive data migration exactly as the osm vocabulary does. |
| RISK-P4-10 → BL-023 | Live Atlas fetching: a real HTTP `Transport` for `PoliteFetcher` and the OCFL `CaptureStore` adapter (carried from RISK-P4-04/05/06). | The framework is not live-wired yet (ADR-026); this ticket owns the source-specific stages, all exercised over committed fixtures (SIG-PARSE-007). | The `Transport` protocol + `CaptureStore` seam are stable; the connector inherits gate/isolation/lineage/replay/disappearance unchanged and is driven end-to-end over committed CSV fixtures, so a real transport is a drop-in (ADR-026/028 revisit trigger). |

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
| RISK-P5-04 → BL-017 | The **live claim-table / `resolution`-table write path and the review queue** for PROPOSED proposals (§14.6, §27). The ER stage emits proposals, `same_as` relations, and an `ERRun` as in-memory value objects with `to_row()` shapes, not DB rows. | Connectors/ER are not DB-wired in P05.1 (ADR-026/029), and the review-queue persistence + curation UI are explicitly P05.2. Wiring here would pre-empt that ticket. | The append-only, versioned, provenance-carrying shapes a DB writer needs are established and tested now (`ERRun.to_row`, `OrganizationRelation.to_row`, `ProbabilisticMatch.match_evidence`); `run_entity_resolution` composes the full six-tier cascade end-to-end over library inputs. ADR-029 records the deferral and its revisit trigger. |
| RISK-P5-05 → BL-044 | The gold set's **model m/u values are seeded by judgement, not EM-estimated**, and the committed gold set is a small illustrative one, not the national stratified sample. | A trained model would be non-deterministic and undefendable as a stated rule (§28.1, SIG-RECON-004); building the full national gold set is a data-collection effort beyond a code ticket. | The gold set's *construction* (stratified sampling, double adjudication + κ, three-value vocab, frozen holdout, per-label provenance) is built and tested (`resolution.gold_set`), and the auto-write demotion gate (SIG-IDENT-028) bounds the risk of a mis-specified model by demoting any tier whose holdout precision falls below the published floor. Refitting is a versioned model migration. |
| RISK-P5-06 → BL-001 | The **adjudicators' human judgement itself** (the correctness of a `match` / `non_match` / `not_enough_information` label) and inter-adjudicator agreement in the wild. | Human adjudication is agentic, not a unit test (the same posture as SIG-PUB-008 in RISK-P0-05). | The *machinery* around it is deterministic and tested: the three-value vocabulary, the written adjudication rules as versioned data, Cohen's κ computation, double-adjudication consensus (disagreement yields no silent pick), and the immutable frozen holdout (`test_frozen_holdout_pair_cannot_be_relabelled`). |

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
| RISK-P5-10 → BL-025 | The **actual model client** for model-assisted extraction (`SIG-LLM-001`). No vendor SDK or network call is wired; `run_extraction` drives an injected `ModelClient` protocol. | A concrete model integration (auth, batching, cost, the `ai-train=no` vs model-assisted-extraction distinction, SIG-LIC-004c) is an operator decision beyond this ticket, and wiring one would make the scaffolding non-deterministic and untestable offline. | The whole boundary is enforced on the *output* regardless of which model produced it — schema validation, span-in-capture, R6/`PROPOSED`, provenance logging, graceful degradation — so any client is a drop-in behind a tested guardrail (ADR-030 revisit trigger). |
| RISK-P5-11 → BL-044 | The **gold-set accuracy cadence** for SIG-LLM-006 uses seeded per-type thresholds and an on-demand `measure_accuracy`, not a scheduled measurement against a national gold set. | The published cadence and the real per-extraction-type gold sets are a data/ops effort beyond a code ticket (mirrors RISK-P5-05 for the ER gold set). | The demotion *mechanism* is built and tested: a measured accuracy below the versioned floor flips the type to human-only deterministically (`evaluate_demotion`), and sampling is reproducible; formalising the cadence is a data migration + ops schedule. |

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
| RISK-P6-06 → BL-024 | **Live acquisition of the slice's evidence.** The records/procurement/parsing connectors (P07) and the portal layer (P11) do not exist yet, so the slice's evidence is committed fixtures faithfully transcribing cited public sources, not live captures. | Phase 6 is deliberately sequenced before those connectors (§52); building them here would pre-empt P07/P11. | Each artifact's bytes are content-addressed (a real `capture_digest`), its real source URL is the `stable_locator`, and each claim's `locator` pins a span in the captured document — the full evidence→claim shape (§D.4) is proven end to end, and the tension is recorded in the retrospective (finding 6). |
| RISK-P6-07 → BL-015 | **The live claim-spine / DB write path.** The slice reconciles and renders over in-memory value objects (matching the connector/ER convention), not the PG claim table. | Docker-free acceptance queries run in CI (SIG-CHART-009); the live write path is P08.x. | The reconciliation value objects align with `db/deploy/graph_annotations.sql`; the append-only guarantees are unchanged (no writable current-value columns introduced). |

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
| RISK-P7-05 → BL-025 | The **concrete extraction engines** for layers 3–5 (PDF text/table, OCR). Only the layer *selection* and interface are built; classification routes to a layer, it does not run one. **Owner: P07.2/P07.3** (ADR-033 Decision 4) — §24.1 mandates the strategy, not a specific engine, so no `SIG-PARSE-*` requires an engine here; the P07.2/P07.3 "P07.1 parses documents" dependency phrasing notwithstanding, the engines are added behind this interface by the connectors that first parse real documents. | Wiring the heavy libraries (and OCR) here would pre-empt those tickets and add runtime dependencies with no caller; a firmer assignment is a decompose-step / canonical-spec-source change (SIG-ENG-003), not an edit of the derived ticket. | The interface is complete and tested end-to-end; the scanned-PDF signal is a deterministic byte heuristic whose mis-route is corrected downstream, never a silent drop (ADR-033 revisit trigger). |
| RISK-P7-06 → BL-025 | The **nightly canary schedule** (SIG-PARSE-008 MUST). The deterministic drift core exists; the scheduled fetch-a-live-sample-and-alert job does not. **Owner: the `orchestration/` layer / live-run wiring** — the spec provides for it via SIG-INGEST-020 (Dagster, cron-swappable) and the SIG-GOV-020/021 degraded-mode keepalive; no standalone ticket names the cross-parser job, so it lands with live orchestration (mirrors the P05.2 gold-set cadence, RISK-P5-11). | The ops schedule and alert destinations are an operations concern, not a code ticket; the per-connector canary ACs (spec line 6782) carry the per-parser half in the meantime. | `structural_findings`/`run_canary` are pure and tested; the nightly job is a thin fetch-and-call wrapper whose alerting contract is a tracked ops deliverable. |

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
| RISK-P7-10 → BL-024 | The **live MuckRock token mint** (POST username/password to `accounts.muckrock.com/api/token/`) and the **real HTTP transport** the connector fetches through. Only the TTL / refresh-on-401 cache logic and the endpoint construction ship here. **Owner: `orchestration/`/`ops` live-run wiring**, the same deferral `connectors.net` already makes for its HTTP transport. | Wiring a live account + real sockets here would add a credentialed network dependency with no live caller and duplicate the injected-transport seam the framework already defines. | `MuckRockTokenCache` refreshes through an injected `TokenSource` and is fully tested for TTL + refresh-on-401; the endpoint/auth facts are versioned data (`data/records_vocab.toml`, re-verify per ADR-034 revisit trigger). |
| RISK-P7-11 → BL-025 | **Running the layer-3/4/5 extraction engine over a captured released document** (PDF text/table, OCR). P07.2 captures each released document as an `EvidenceArtifact` and **classifies** it (routing it to a layer via the P07.1 parser), but does not run the engine. **Owner: the point a document-derived claim is needed** (§23.5 scopes P07.2 to the request + its captures; "the layered parsing of the released documents themselves" is P07.1's interface, ADR-033 Decision 4). | §23.5 explicitly hands document parsing to P07.1's interface and scopes this connector to the request and its released captures; wiring an engine here would pre-empt that and add heavy runtime dependencies. | Every released document is captured (content-addressed) and its classification verdict recorded, so extraction is a pure re-processing step over stored bytes; a mis-route of the scanned-PDF heuristic is corrected downstream, never a silent drop. |

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
| RISK-P7-15 → BL-023 | The **live HTTP transport** for USAspending / cooperative-vehicle / agenda-platform APIs the connector fetches through. Only the endpoint/field facts (`procurement_vocab.toml`, `agenda_tenants.toml`) and the pure parse/extract/normalize logic ship here. **Owner: `orchestration/`/`ops` live-run wiring**, the same deferral `connectors.net` already makes for its HTTP transport. | Wiring real sockets + credentials here would add a network dependency with no live caller and duplicate the injected-transport seam the framework already defines. | The connector fetches through the shared politeness layer over an injected transport and is tested end-to-end over canned responses; the endpoint/field facts are versioned data, re-verified per the ADR-035 revisit trigger. |
| RISK-P7-16 → BL-024 | **The tenant registry is a small, partly-unverified seed**, and the tenant-discovery negatives are produced but not yet consumed by a coverage surface. **Owner: ongoing records/discovery research; P09.1 for the coverage surface.** | Filling out a national municipality→platform directory is continuous research, not a one-ticket deliverable; the coverage surface that renders the negatives is P09.1. | Rows carry an honest `verified` flag (no synthetic certainty, §3.1); the discovery-negative path (`tenant_discovery_negatives`) ensures every probed-but-empty jurisdiction is retained as a `db.absence` coverage record now (SIG-METRIC-002a), so gaps are recorded rather than hidden. |
| RISK-P7-17 → BL-025 | **Running the layer-3/4/5 extraction engine over a captured procurement document** (a signed PDF contract, an award-packet ZIP). The connector captures each document as an `EvidenceArtifact` with its `artifact_type` and **classifies** it, but does not run the engine. **Owner: the point a document-derived claim is needed** (§23.6 scope; the parser interface is P07.1's, ADR-033 Decision 4). | §23.6 hands document parsing to P07.1's interface; wiring an engine here would pre-empt that and add heavy runtime dependencies with no caller. | Every captured document is content-addressed and its classification verdict recorded, so extraction is a pure re-processing step over stored bytes; a mis-route is corrected downstream, never a silent drop. |

## Phase 8 — Resolver (P08.1)

The deterministic §28 resolver `RESOLVE(subject, predicate, as_of_world, as_of_belief,
ruleset)` — the intellectual core of the project (ADR-060, retro-fitted by P19.5). P08.1
shipped with no ADR and no §53 section (LD-X05); this section closes the §53 gap. The two
standing risks are both about the two artefacts P08.1 made "data, not code": the ruleset and
the rationale templates.

| id | Risk | How it is retired |
|---|---|---|
| RISK-P8-00a | **Ruleset-as-data drift.** The resolver's tolerances, strategy vocabulary, and versioned rationale templates live in `reconcile/src/reconcile/data/ruleset.toml` (data, separately attributable and diffable, SIG-RECON-021). A hand edit that changes the numeric tolerances, the strategy vocabulary, or the `ruleset_version` without the matching test would silently change every resolution outcome. | The committed `check_ruleset` test (`tests/reconcile/test_ruleset.py`) pins the ruleset's structure, its strategy vocabulary, and its version so a drift fails the build; `resolver_version` and `ruleset_version` are independent (SIG-STORE-017) so a template change is a versioned, attributable event, not a silent one. |
| RISK-P8-00b | **Rationale quotability depends on fixture wording.** Rationales are generated from versioned templates (§25.2: an LLM never resolves or produces confidence); a template edit could produce a sentence that reads well in a unit test yet fails the §41 editorial rules on a live resolution (e.g. mixing a support term and an agreement term in one sentence). | The `check_template` clauses (a–e) run on every committed template AND a **live** resolution's rationale is asserted quotable + conformant (`test_live_resolution_rationale_is_quotable_and_conformant`, PR #20), so the editorial gate is proven on real output, not just fixtures. |

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
| RISK-P8-09 → BL-004 | **Persistence + lifecycle of the contradictions and the L4 inference** these workflows emit. The workflows produce in-memory `Contradiction`/`Inference`/`ResearchTask` value objects; storing them, running the contradiction lifecycle, and materializing `inference.derived_fact` are downstream. **Owner: P08.3 (§31) for contradictions; P12.x (§30) for the L4 layer.** | Materializing those entities here would create two competing owners of the same tables and pre-empt the tickets that own them. | The value objects are aligned with the persisted shapes (`db/deploy/graph_annotations.sql`, `db/deploy/inference_schema.sql`), so persistence is a wiring step; every emitted finding is a first-class, addressable object with its evidence and task, never a silent drop. |

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
| RISK-P9-08 → BL-007 | SIG-TIME-012 "distinguishable in the **UI**" | The UI (`web/`, TypeScript) is deferred to Phase 15; there is no browser surface to drive here | The **API-contract** half is deterministic and tested (distinct `absence_code`/`label` per kind in `CoverageRecord.public_view`); the UI rendering is a tracked P15.5 deliverable that consumes these tokens. |

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
| RISK-P10-07 → BL-027 | The concrete detector catalog (§33.2) and the `Facts` shape its detectors read | The 34 detectors and their real graph-query surface are **P10.2**; this ticket owns the DSL they register against | The DSL is exercised with representative in-memory `Facts` fixtures; P10.2 pins the query surface to the real graph. Registration/lifecycle/dedup are all tested against the engine now. |
| RISK-P10-08 → BL-004 | Persistence of tasks, claims, and local groups (no `local_group`/claim DDL exists in Appendix C) | Live Postgres persistence and the claiming API are downstream; Appendix C names no `local_group` table | Fields track the `research_task` DDL; SIG-TASK-014's ownership guarantee is met by a self-contained in-memory registry with no external dependency (F1.9). Adding a schema is an additive downstream change (ADR-039 revisit trigger). |

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
| RISK-P10-13 → BL-004 | The catalog detectors' binding to the real materialized-graph query surface (they read documented `Facts` keys, not live projections) | No graph-query surface exists for the detectors to bind to yet; ADR-039/040 scope it downstream | Each row's contract (which facts it reads, when it fires, when it closes) is pinned with committed positive/negative fixtures and an end-to-end auto-invalidation test; binding the keys to live projections is an additive downstream change (ADR-040 revisit trigger). |
| RISK-P10-14 → BL-027 | Task routes for `temporal_impossibility` and `undeclared_copying` are mapped ahead of any reconcile detector that emits them | The P08.2/P08.3 workflows do not yet emit these two of the nine `contradiction_type`s | The map covers the **full** §31 vocabulary so a future emitter already has a route; the chosen catalog task is revisited if a real emitter proves it a poor fit (ADR-040 revisit trigger). |

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
| RISK-P10-17 → BL-028 | The per-jurisdiction operational-detail fields (`response_deadline`, `fee_rules`, `appeal_path`) are honest seed summaries, not counsel-reviewed legal advice | Per-jurisdiction counsel review is a Phase-0/legal deliverable, not an engineering one; a statute's fixed number often does not exist ("reasonable time") | The two load-bearing fields (`citation`, `residency_required`) are asserted by the suite; the operational fields are **versioned data** (`table_version`), so a counsel correction is a tracked migration, not a code change (ADR-041 revisit trigger). |
| RISK-P10-18 → BL-028 | Template success rates are measured through an in-memory `TemplateOutcomeLog` fed by the caller, not by a live filing/response backend (SIG-TASK-017) | No filing/response ingestion backend exists yet (the `records` connector, P07.2, ingests replies; wiring outcomes back to the log is downstream) | The measurement surface (per-version rate + the min-sample-guarded revision flag) is fully implemented and tested; feeding it from real filed outcomes is an additive downstream change (ADR-041 revisit trigger). |

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
| RISK-P11-05 → BL-024 | The connector is not DB-wired and runs no live `/api/v1/data` fetch in CI; cross-capture snapshot diffing (§29.7) and portal appearance/disappearance detection (SIG-INGEST-035) are module functions invoked by the backfill/change-feed driver rather than a single connector run's output | A single run is a pure function of one capture (SIG-INGEST-003), so it cannot diff two captures; the live transport and the driver that supplies multiple captures land with orchestration, exactly as every prior connector defers the live HTTP transport (ADR-028/029) | The pure diff/appearance/disappearance logic is fully implemented and tested against committed multi-snapshot fixtures (`test_snapshot_diff_produces_per_field_change_events_via_p08_2`, `test_portal_disappearance_produces_an_event_and_a_task`, `test_portal_appearance_produces_an_event_and_a_no_known_deployment_task`); wiring it to the live driver is an additive downstream change (ADR-042 revisit trigger). |
| RISK-P11-06 → BL-027 | The §29.3 sharing-edge asymmetry contradictions and research tasks are produced by the reconciler but not folded into the connector's L1 claim stream (SIG-RECON-035, owned by P08.2) | The reconciler mints non-deterministic task ids that would break the run's reproducibility fingerprint (SIG-INGEST-003), and finding emission is P08.2's responsibility, not the connector's | The connector produces the raw edges and invokes the reconciler (`reconcile_portal_sharing`, exposed via `FlockPortalConnector.reconcile_sharing`); asymmetry firing is tested (`test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler`); a driver persists the findings (ADR-042 revisit trigger). |
| RISK-P11-07 → BL-026 | `upstream_refresh_days` is a conservative data default (1 day), not the confirmed upstream cadence (SIG-INGEST-030a) | The confirmed refresh cadence is a Phase-0 outreach deliverable, not an engineering one | The cadence is **versioned data** (`data/flock_portal_vocab.toml`), so a confirmed value is a one-line data edit, not a code change; the poll-suppression logic keyed on it is tested (`test_is_poll_due_keys_on_the_snapshot_and_respects_the_refresh_cadence`) (ADR-042 revisit trigger). |

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
| RISK-P11-13 → BL-016 | The `UsageAggregate` analytics substrate (Hive-partitioned Parquet on DuckDB, small-cell suppression, the UUID+period join) is not built here | §18's substrate is **P12.1's** deliverable; building it here would pre-empt that ticket | The connector *writes* the `usage_aggregate` rows with the full §11.16 predicate surface + source-agency provenance so P12.1 can land them; suppression/substrate are downstream (ADR-043 revisit trigger). |
| RISK-P11-14 → BL-027 | The §29.3 sharing asymmetry contradictions/tasks and the §29.1 count findings are produced by the P08.2 reconcilers but not folded into the connector's L1 claim stream | The reconcilers mint non-deterministic ids that would break the reproducibility fingerprint (SIG-INGEST-003), and finding emission is P08.2's responsibility | The connector produces the observations and invokes the reconcilers (`reconcile_audit_sharing`, `reconcile_camera_counts`); asymmetry firing is tested (`test_sharing_asymmetry_is_a_finding_via_the_p08_2_reconciler`); a driver persists the findings (ADR-043 revisit trigger). |
| RISK-P11-15 → BL-024 | The connector is not DB-wired and runs no live public-records fetch in CI; cross-export de-duplication across many captures is bounded to within-run window blocks | No live records backend is wired (the transport lands with orchestration, as with every prior connector, ADR-028/029/042); combining aggregates across captures is P12.1's aggregation boundary | The pure aggregation / dedup / count / sharing logic is fully implemented and tested against committed CSV fixtures; `deduplicate_events` realizes the `(source_org, searching_org, window)` block dedup and is tested (`test_overlapping_exports_are_deduplicated_by_window_block`) (ADR-043 revisit trigger). |

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
| RISK-P12-06 → BL-027 | Resolution of textual org identifiers → `sig_entity_id` UUIDs for `project_aggregate` is the caller's responsibility, not performed inside `db.analytics` | Entity resolution is P6's concern (the connector link stage); folding it into the analytics layer would duplicate and could diverge from the canonical resolver | `project_aggregate` takes the resolved UUIDs as explicit inputs and deliberately drops any name field so a name cannot cross the boundary (SIG-STORE-028); the layering is recorded in ADR-044. |
| RISK-P12-07 → BL-027 | The suppression review tasks (ambiguous cells; complementary suppression forced onto an institutional cell) are produced as `review_tasks` strings, not yet enqueued into the P10.1 research-task engine | Task persistence and the queue are owned elsewhere; wiring them here would couple the substrate to the task engine | `suppress_group` surfaces every review reason in `GroupSuppressionResult.review_tasks`; a driver enqueues them (ADR-044 revisit trigger). Proven present by `tests/db/test_suppression.py::test_ambiguous_small_cell_is_suppressed_and_raises_a_review_task`, `::test_complementary_falls_on_institutional_only_when_forced_and_flags_review`. |

## Phase 12 — Usage and network layer (P12.2 — access edges and access-path closure)

Per §53 / SIG-ENG-031, P12.2's risk-register entries. P12.2 delivers access-path closure (ADR-045),
"SIG's most powerful and most dangerous inference" (§30.2): it is where a false "A can search C" or an
unlabelled long theoretical path would be manufactured if the composition/scope/temporal bounds and
the speculative label were not enforced.

### Design risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P12-08 | **The three §12.2 sharing edge types are merged, collapsed, or defaulted into one another** — `observed_use` silently treated as `configured_access`, destroying the "set up to permit" vs "someone actually did it" vs "someone said so" distinction (SIG-ONTO-042). | Closure composes ONLY `configured_access`/`federates_search_to` (`COMPOSABLE_LABELS`) and preserves each hop's `edge_label` verbatim; the three kinds are the P08.2 `ACCESS_KINDS` reused, reconciled separately by `reconcile.sharing`. Proven by `tests/inference/test_access_paths.py::test_only_configured_access_and_federation_compose`, `::test_closure_never_relabels_a_hop_kind`, `::test_access_edge_kinds_stay_distinct_and_are_not_defaulted`. |
| RISK-P12-09 | **`observed_use` (or an outbound `distributes_list_to` hotlist) composes** — "A searched B and B searched C" becomes a false "A can search C", or a one-way list flow invents an inbound search channel (SIG-RECON-049 #1/#2). | Only the two composable labels are ever traversed; `observed_use`/`declared_policy`/`distributes_list_to` edges in the input contribute no chain. Proven by `tests/inference/test_access_paths.py::test_observed_use_does_not_compose`, `::test_a_standalone_observed_use_chain_reaches_nothing_by_composition`, `::test_distributes_list_to_does_not_compose_in_the_query_direction`. |
| RISK-P12-10 | **A chain broadens its own scope, or crosses an expired hop presented as live** — a partner-scoped edge inherits a downstream national reach, or a path through a lapsed edge is rendered as current access (SIG-RECON-049 #3/#4). | A hop that broadens the chain's scope is refused (`SCOPE_ORDER`/`_scope_breadth`); a future hop is not traversed and an expired hop taints the whole path `historical` (`AccessPath.temporal_status`), excluded from `headline_paths`. Proven by `tests/inference/test_access_paths.py::test_scope_may_not_broaden_along_a_chain`, `::test_expired_hop_yields_a_historical_labelled_path`, `::test_a_future_hop_is_not_asserted_as_of_the_query_time`. |
| RISK-P12-11 | **Confidence is laundered by averaging**, or a path is published with no per-hop evidence — an unexplained "A can reach B" (SIG-RECON-049 #5/#6). | Confidence is the path *minimum* (`CONFIDENCE_ORDER`), every `AccessEdge` requires non-empty `evidence` at construction, and `public_view`/`to_inference` always carry the full hop list with per-hop evidence. Proven by `tests/inference/test_access_paths.py::test_confidence_is_the_minimum_over_the_path_never_the_average`, `::test_every_published_path_carries_its_full_hop_list_with_per_hop_evidence`, `::test_a_hop_without_evidence_is_rejected`. |
| RISK-P12-12 | **A long theoretical path is blurred into a shared-data relationship** — the difference between "these agencies share data" and "a seven-hop path exists" is lost (SIG-RECON-050). | Beyond `SPECULATIVE_HOP_THRESHOLD` a path is labelled `speculative` and excluded from headline figures (`is_headline`, `reachable(headline_only=True)`); it is still returned with its hops, never hidden and never counted. Proven by `tests/inference/test_access_paths.py::test_paths_beyond_threshold_are_speculative_and_excluded_from_headlines`, `::test_paths_within_threshold_are_headline_and_not_speculative`. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P12-13 → BL-004 | Persisting the L4 closure inferences into `inference.derived_fact` and rendering them on the map/UI with the observation-vs-inference distinction (§30.4, §39.1, SIG-UI-025) is downstream (P15.x) | The read-API envelope and the map/UI surfaces are owned by later delivery-phase tickets; building them here would pre-empt them | `AccessPath.to_inference()` produces a value object aligned with the persisted `inference.derived_fact` shape (ADR-045), and `public_view()` already emits the full hop list + labels every surface must show; persistence/render is an additive wiring step (ADR-045 revisit trigger). |
| RISK-P12-14 → BL-027 | Mapping raw §12.5 `AccessRelationship` / §12.3 integration edges into the normalized accessor→provider `AccessEdge` (respecting each edge type's native direction) is the caller's responsibility, not performed inside closure | Edge-direction normalization depends on the reconciled edge stream (P08.2) and the integration-edge polarity; folding it into the closure engine would entangle the safety rules with per-type direction handling | The closure engine is direction-agnostic and its bounds are legible; the accessor→provider contract is documented on `AccessEdge`, and `SPECULATIVE_HOP_THRESHOLD`/`MAX_PATH_HOPS`/the scope ranking are parameters so a confirmed policy is a one-line change (ADR-045 revisit trigger). |

## Phase 13 — Accountability, policy, legal instruments (P13.1 — accountability events and the `accountability` connector)

Per §53 / SIG-ENG-031, P13.1's risk-register entries. P13.1 brings accountability into the graph as
first-class, epistemically-honest records (§§11.17–11.18, §23.8): this is where an allegation could be
laundered into a fact, a court-record-backed claim made indistinguishable from an advocacy blog post,
or a rate-limited court API turned into a crawl if the `epistemic_status` contract, the source-class
tagging, and the targeted-lookup discipline were not enforced.

### Design risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P13-01 | **An allegation is flattened into a fact** — "a plaintiff alleged X in a pending lawsuit" is stored/rendered as "X happened" (SIG-ONTO-038, OL-2E-AA-05). | `epistemic_status` is REQUIRED at write (`AccountabilityEventRecord` raises `MissingEpistemicStatus`), preserved verbatim (`raw_epistemic_status`; emitted under the registered `event_epistemic_status` predicate so `RESOLVE` carries it unchanged), and the render guard refuses a factual verb for a non-factual status. Proven by `tests/connectors/test_accountability.py::test_epistemic_status_is_required_on_write`, `::test_epistemic_status_is_preserved_verbatim_on_the_claim_rows`, `tests/reconcile/test_resolve.py::test_event_epistemic_status_is_preserved_verbatim_through_resolution`, `tests/exports/test_accountability_render.py::test_the_three_named_non_factual_statuses_never_render_as_a_bare_fact`, `::test_the_guard_rejects_an_allegation_phrased_as_a_fact`. |
| RISK-P13-02 | **A claim resting only on advocacy analysis is presented as equivalent to one resting on a court record** — the source class is lost (SIG-ONTO-039). | The six OL-2E-AL-03 classes are a frozen `SourceClass` enum; every `EvidenceLink` validates and records its class, and `rests_only_on` makes advocacy-only distinguishable from court-record. Proven by `tests/connectors/test_accountability.py::test_an_incident_links_to_all_six_source_classes_with_the_class_recorded`, `::test_advocacy_only_claim_is_distinguishable_from_a_court_record_claim`, `::test_an_out_of_vocabulary_source_class_is_rejected`. |
| RISK-P13-03 | **The connector writes outside its remit** — a Policy, a LegalInstrument (P13.2), a deployment, or a device count leaks in through the accountability channel (SIG-INGEST-033). | The predicate allowlist is a hard schema gate (`assert_predicate_allowed`); the out-of-scope write-set is named data (`forbidden_predicate_genres`). Proven by `tests/connectors/test_accountability.py::test_the_allowlist_is_the_only_write_set`, `::test_a_forbidden_predicate_is_refused_at_the_ingest_boundary`, `::test_forbidden_genres_are_outside_the_allowlist`. |
| RISK-P13-04 | **The upstream record categories are adopted wholesale**, or an unknown category is silently guessed into a SIG event_type (§23.8, §3.1 no synthetic certainty). | The categories are crosswalked in data (`[crosswalk.*]` with SKOS relation + `lossy`); an unmapped category yields a research task, never a guess. Proven by `tests/connectors/test_accountability.py::test_upstream_categories_are_crosswalked_not_adopted_wholesale`, `::test_an_unmapped_category_yields_a_research_task_never_a_guess`. |
| RISK-P13-05 | **CourtListener/RECAP is crawled** — a ~5/min court API is enumerated instead of looked up, a legal-posture violation (§22.2, SIG-INGEST-036/037). | `assert_targeted_lookup` refuses crawl/list/search modes, pagination cursors, and bare collection endpoints; `discover`/`fetch` assert it for every court target. Proven by `tests/connectors/test_accountability.py::test_crawling_the_court_api_is_refused`, `::test_discover_refuses_a_courtlistener_crawl_target`. |
| RISK-P13-06 | **The Abuse Library's curated entries are normalized into facts** rather than kept as an index (OL-2E-AL-02). | Abuse Library entries become `index_only` advocacy-analysis evidence links, never event claims. Proven by `tests/connectors/test_accountability.py::test_abuse_library_entries_are_index_only_advocacy_links_never_facts`. |

## Phase 13 — Accountability, policy, legal instruments (P13.2 — policy, legal instruments, and policy/configuration divergence)

Per §53 / SIG-ENG-031, P13.2's risk-register entries. P13.2 models what governs the infrastructure and
surfaces where it is disobeyed (§§11.13–11.14, §29.6, §10.9). The `Policy` / `LegalInstrument` entities
(P01.1) and the §29.6 divergence reconciler (P08.2) are consumed as-is; this ticket adds no schema and
no persisted surface, so its risks are narrow: the two governing objects could be folded into one, the
divergence could be editorially collapsed, or a curated index entry could be silently promoted to a
claim. See ADR-046 for the decision to land P13.2 as acceptance tests plus the SIG-EPIS-030 general form.

### Design risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P13-10 | **`Policy` and `ConfigurationState` are merged into one object** — a written rule and the observed configuration are folded together, destroying the §29.6 finding before it can be made (SIG-ONTO-034, P10). | The two are distinct classes with disjoint predicate surfaces in the ontology, and distinct types at the resolution layer (`reconcile.policy_config.PolicyStatement` vs `ConfigurationState`, both sides retained). Proven by `tests/ontology/test_schema_structure.py::test_policy_and_configuration_state_are_never_merged`, `tests/reconcile/test_policy_config.py::test_policy_and_configuration_are_distinct_and_never_merged`. |
| RISK-P13-11 | **Policy/configuration divergence is editorially collapsed** — a written policy prohibiting immigration-related use and an enabled immigration hotlist are merged into one answer instead of surfaced as a finding carrying both sides' evidence (SIG-RECON-044, OL-8.12-02). | `reconcile_policy_configuration` emits a `policy_configuration_divergence` finding with both sides' evidence and a research task; `PolicyConfigResult.collapse()` raises. Proven by `tests/reconcile/test_policy_config.py::test_canonical_immigration_divergence_is_a_first_class_finding`, `::test_divergence_must_not_be_collapsed`, `::test_required_but_disabled_is_a_finding`. |
| RISK-P13-12 | **A curated source index is normalized into claims** — a bibliography of reporting is materialized into low-quality facts about its subjects, destroying the index's value (SIG-EPIS-030, §10.9, OL-2E-AL-02). | `connectors.curated_index.CuratedSourceIndex` holds entries as `index_only` references; `as_claims()` raises `IndexNormalizationRefused`, and the P13.1 Abuse Library path consumes this general form. Proven by `tests/connectors/test_curated_index.py::test_index_records_are_index_only_never_claim_rows`, `::test_normalizing_a_curated_index_into_claims_is_refused`, `::test_the_accountability_connector_relies_on_the_general_capability`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-046 | The `Policy` / `LegalInstrument` predicate surfaces (P01.1) and the §29.6 divergence reconciler (P08.2) were front-loaded by dependencies, so P13.2 re-implements nothing: it adds the ticket's acceptance tests against those surfaces (no schema change; the generation gate is untouched) and lands SIG-EPIS-030 as the general `connectors.curated_index` module, refactoring the P13.1 Abuse Library path to consume it additively (the emitted `index_only` row shape is byte-identical). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P13-13 → BL-007 | Public API / export surfaces over `Policy` / `LegalInstrument`, and `ConfigurationState` population | Out of scope: the read/export surfaces are P14.1 / P14.2, and `ConfigurationState` population + the configuration-cut rule are owned upstream (P01.1 + the config-writing connectors); this ticket only reconciles against them. | The predicate surfaces and the never-merged invariant are proven now, so the downstream surfaces build on a tested, additive base; the §29.6 reconciler already renders the divergence finding both sides retained. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully automatable now | Compensating control |
|---|---|---|---|
| RISK-P13-07 → BL-024 | The connector is not DB-wired and runs no live Accountability Atlas / CourtListener fetch in CI | No live transport is wired (it lands with orchestration, as with every prior connector, ADR-028/029/042); the accountability sources' rights remain `UNDETERMINED` in the registry until reviewed | The pure `parse`/`extract`/`normalize` logic is fully implemented and tested against in-memory CSV/JSON captures for all five Atlas artifacts + the Abuse Library + a CourtListener docket; entity resolution of the candidate identifiers is P03.2/P05.1 (SIG-INGEST-034). |
| RISK-P13-08 → BL-007 | The production dossier surface that renders `epistemic_status` in the full epistemic visual language is P15.2 | The slice-scoped `exports.dossier` renderer is superseded by P15.2 (ADR-032); building the full surface here would pre-empt that ticket | `exports.accountability` ships the verb-selection contract + the mechanical `assert_not_flattened` guard P15.2 consumes, so the "never a factual verb for an allegation" invariant is enforced from the first render surface (revisit at P15.2). |
| RISK-P13-09 → BL-007 | `Policy`, `LegalInstrument`, and policy/configuration divergence are out of scope (P13.2) | This ticket owns accountability events + the connector only; the policy entities and the §10.9 curated-index-without-normalization capability are P13.2's deliverable | The predicate allowlist refuses those write genres at the ingest boundary today, so P13.2 lands additively without loosening this connector's gate. |

## Phase 14 — API and exports (P14.1 — the public read API)

Per §53 / SIG-ENG-031, P14.1's risk-register entries. P14.1 owns the versioned §37 read wire contract.
Its risks are almost entirely **disclosure** risks — the API is the surface where a Part VIII breach
would actually reach the public — so the compensating controls are structural (fail-closed at app
construction) and reuse the already-tested publication engines rather than reimplementing them. See
ADR-047 for the decision to build a hand-written contract over a `ReadStore` seam.

### Design / disclosure risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P14-01 | **A material fact is returned as a bare value** — a consumer gets a number with no support/agreement/currency/as-of/ruleset, treating a contested or stale value as settled fact (SIG-API-002, §3.1). | The value only ever leaves the API inside `api.envelope.ResolutionEnvelope`; `RESOLUTION_ENVELOPE_FIELDS` is the single required-field set asserted by the contract test. Proven by `tests/api/test_api_envelope_contract.py::test_a_material_fact_is_never_a_top_level_bare_value`, `::test_resolution_response_carries_the_full_envelope`. |
| RISK-P14-02 | **A response omits its as-of pair or implies "latest"** — a citation cannot be reproduced because the response never states which world/belief instants it used (SIG-API-005). | Every read resolves through `db.temporal.AsOf` (explicit defaults) and echoes the resolved pair with `*_defaulted` flags; no "latest" sentinel exists. Proven by `tests/api/test_api_as_of.py::test_omitting_both_params_echoes_explicit_defaults_not_latest`, `::test_every_read_family_accepts_and_echoes_as_of`. |
| RISK-P14-03 | **A belief-pinned citation is not reproducible after a correction** — a later correction retroactively changes the answer to a past-belief query (SIG-API-006, SIG-TIME-008). | Append-only belief-time filtering: `InMemoryStore.claims_for` returns only claims asserted on or before `as_of_belief`, so a correction (a new, later-asserted claim) is invisible to a past-belief read. Proven by `tests/api/test_api_reproducibility.py::test_belief_pinned_request_is_reproducible_after_a_correction`, `::test_a_correction_is_a_new_claim_never_an_edit`. |
| RISK-P14-04 | **A prohibited endpoint is mounted** — a device-liveness, per-person-lookup, sealed-bytes, or over-precise-coordinate surface exists (SIG-API-012, Part VIII). | `api.prohibitions.assert_no_prohibited_routes` runs at app construction (fail-closed) and the generic `/entity` route refuses per-person entity types; sealed bytes are withheld by `evidence.tiers.public_representation`; coordinates are reduced by `policy.sensitivity.apply_tier`. Proven by `tests/api/test_api_prohibitions.py::test_no_mounted_route_is_a_prohibited_surface`, `::test_building_an_app_with_a_prohibited_route_fails_closed`, `::test_sealed_capture_never_returns_its_bytes`, `::test_a_person_entity_type_is_refused_by_the_generic_entity_route`, `::test_coordinates_are_reduced_to_the_sensitivity_tier`. |
| RISK-P14-05 | **A tier grants `restricted`/`sealed` material** — a partner (or any) key reaches material the public API must never serve (SIG-API-011). | `api.tiers.assert_public_visibility` is tier-independent: `restricted`/`sealed` records return a generic 404 for every tier (anonymous/registered/partner), and its detail does not confirm the tier. Proven by `tests/api/test_api_tiers.py::test_no_tier_can_read_a_restricted_entity`, `::test_the_visibility_gate_is_tier_independent`. |
| RISK-P14-06 | **A collection response fabricates a single licence across incompatible compartments, or over a non-redistributable source** — a downstream consumer mis-licenses SIG data (SIG-API-004, SIG-LIC-004/004a). | `api.envelope.license_statement` reuses `policy.licensing.compute_export_license` and reports no single licence — listing the compartments, or `EXPORT-GATE-CLOSED` — rather than merging incompatible or non-redistributable rights. Proven by `tests/api/test_api_coverage_license.py::test_incompatible_compartments_yield_no_single_licence`, `::test_a_non_redistributable_source_closes_the_licence_gate`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-047 | The read API is built as a hand-written FastAPI contract over an in-memory `ReadStore` seam (no in-Python DB fetch layer exists yet); `restricted`/`sealed` *captures* are served as their SIG-EVID-009/010 metadata-only public representation (bytes never reach the surface) rather than blocked; a bare date `as_of` follows `db.temporal`'s midnight-UTC coercion; and ruff B008 is configured to allow FastAPI's `Depends`/`Query`/`Header` call-in-default markers (scoped to exactly those three). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P14-07 → BL-015 | The production `ReadStore` is not DB-wired; the app runs over the deterministic `InMemoryStore` in CI | No live transport / query layer is wired (it lands with orchestration, as with every connector, ADR-028/029/042); the `db` package is still a schema plus in-memory helpers | The `ReadStore` Protocol is the seam production wires to Postgres; the whole §37 surface is proven over the in-memory store and the pure adapters, and the wire contract (models + OpenAPI) is fixed and versioned. |
| RISK-P14-08 → BL-008 | Bulk exports, export-licence computation, the ODbL split, crosswalk export, and Zenodo deposit are out of scope | Those are P14.2 (SIG-EXPORT-*); the read API only *lists* available bulk artifacts at `/export` | `/export` is an index only (computes no artifact and no export licence); the P14.2 exports reproduce the P14.1 envelope response shape via the same code path (SIG-EXPORT-003), so they build on a tested, versioned base. |
| RISK-P14-09 → BL-031 | Rate limiting is expressed as tier metadata, not enforced in-process | Enforcement is an ops/gateway concern; the security-relevant tier boundary (no `restricted`/`sealed` at any tier) is what P14.1 owns and enforces | `api.tiers.TIER_RATE_LIMITS` declares the budgets so the contract is inspectable; the data reachable never changes by tier (SIG-API-011), which is the invariant tested. |
| RISK-P14-10 → BL-031 | GraphQL (SIG-API-010, a SHOULD) is not offered | Out of scope unless trivially free; it MUST NOT be the only surface, and REST is the surface | REST + OpenAPI is the complete, cacheable, archivable surface §37 requires; a later GraphQL layer, if added, is additive over the same `ReadStore`. |

## Phase 14 — API and exports (P14.2 — bulk exports, licence computation, Zenodo deposit)

Per §53 / SIG-ENG-031, P14.2's risk-register entries. P14.2 owns the bulk dataset publication and
the export-time licence computation (§38, §42.4). Its risks are **licence-leak** risks — the export
is where a wrong licence or a merged share-alike file would ship irrevocably — so the compensating
controls fail the *build* closed rather than catching a violation after publication. See ADR-048.

### Design / licence risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P14-11 | **A share-alike input is folded into an incompatible export** — an ODbL or CC-BY-SA source is merged into the CC-BY graph, silently forcing the whole file share-alike (SIG-EXPORT-004, SIG-LIC-010). | The bundle *computes* each file's licence from constituent rights via `policy.licensing.compute_export_license`; an incompatible mix raises and fails the build. Proven by `tests/exports/test_bundle.py::test_incompatible_share_alike_mix_fails_the_build`, `test_compartments.py::test_incompatible_mix_in_one_table_fails_the_build`. |
| RISK-P14-12 | **The ODbL asset layer ships merged with the CC-BY graph** (SIG-EXPORT-005). | Each table computes to one licence and one `licenses.toml` compartment directory, so ODbL and CC-BY are physically separate files; `assert_separated` + the build-time separate-serving-artifacts check enforce it. Proven by `tests/exports/test_bundle.py::test_odbl_assets_are_a_distinct_file_never_merged_into_cc_by`, `::test_route_privacy_and_researcher_layers_are_separate_files`. |
| RISK-P14-13 | **A silently-travelling share-alike obligation is laundered** — content derived from a share-alike upstream ships as permissive because an intermediary dropped the obligation (SIG-LIC-009a). | `policy.licensing.effective_license` promotes a share-alike `upstream_license` to the governing regime, and an *unresolvable* upstream forces the build to fail closed rather than default permissive. Proven by `tests/unit/test_policy_licensing.py::test_silently_travelling_share_alike_uses_stricter_upstream`, `::test_unresolvable_upstream_provenance_fails_closed_not_silently_permissive`. |
| RISK-P14-14 | **A downstream consumer cannot determine a fact's licence** and is forced to assume the strictest (SIG-EXPORT-006, SIG-LIC-011). | Every exported row is stamped with its per-row obligation via `policy.licensing.downstream_obligations` — the same function the read API uses. Proven by `tests/exports/test_compartments.py::test_enrich_rows_stamps_per_row_rights_provenance`, `test_bundle.py::test_every_exported_row_carries_rights_provenance`. |
| RISK-P14-15 | **Popularity becomes an existential egress bill** — a metered-egress provider turns a 2 GB × 5,000 download month into a four-figure invoice (SIG-EXPORT-008). | `exports.distribution.assert_low_egress` fails a build that targets a metered provider; the largest artifacts also get torrent/IPFS references (SIG-EXPORT-009). Proven by `tests/exports/test_bundle.py::test_metered_egress_store_fails_the_build`, `test_distribution.py::test_largest_artifacts_get_torrent_and_ipfs`. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-048 | PMTiles ships as a valid v3 archive carrying the ODbL layer as metadata (real GeoJSON of the layer ships alongside); rendered vector tiles are deferred to the map surface (Phase 15). `derivative_permitted` is not added to the shared export gate (SIG-LIC-004 gates `redistributable` + `UNDETERMINED`; expanding it is P00.4's contract). Binary-format byte-reproducibility is keyed on a fixed toolchain version (DuckDB stamps its version into Parquet). |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P14-16 → BL-029 | The Zenodo deposit runs against a deterministic `FakeZenodoTransport`, not the live Zenodo HTTP API | No network in CI; the real client lands with orchestration/publication, like every external transport | The deposit *policy* — concept + version DOI, evidence bytes excluded, digest manifest deposited — is behind the `ZenodoTransport` seam and fully tested; the production client must satisfy the same contract (`tests/exports/test_zenodo.py`). |
| RISK-P14-17 → BL-029 | The PMTiles tileset is metadata-only (no rendered vector tiles) | Tile rendering is a tippecanoe-class build step owned by the Phase-15 map surface; the archive is a valid v3 container | The route/privacy class's data need is served by the real, complete GeoJSON of the ODbL layer; the PMTiles archive is spec-valid and its tile bodies fill when the tiler lands (ADR-048). |
| RISK-P14-18 → BL-008 | Export inputs (`ExportTable`s) are supplied by the caller/CLI, not yet projected from a live `ReadStore` | The production read/query layer is not DB-wired (RISK-P14-07); the export reuses the same `policy.licensing` / `resolution.crosswalk` code path the API uses | Reproducibility is a pure function of the `BuildSpec`; the projection wires to the same `ReadStore` seam when it is DB-backed (SIG-EXPORT-003), re-verified per ADR-048's revisit trigger. |

## Phase 15 — Public web surfaces (P15.1 — the web shell + the epistemic visual language)

Per §53 / SIG-ENG-031, P15.1's risk-register entries. P15.1 owns the epistemic visual language and
the a11y / no-JS / archivability baseline that P15.2–P15.5 all consume, so its risks are
**misrepresentation** risks — a page that looks confident about a contested or absent fact, or that
silently stops being archivable — plus the two CI gates (licence, performance) the spec mandates be
enforced by machine, not memory. See ADR-049 for the decisions and the one recorded deviation.

### Design / disclosure risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P15-01 | **A fused badge collapses the four epistemic fields** — "strongly supported but contested" or "confirmed but historical" becomes unexpressible and a reader mistakes one axis for another (SIG-UI-004). | The four §10.7 fields render as four independent chips; `EpistemicFields.astro` emits `data-fused="false"` and no fused token exists. Proven by `web/tests/e2e/shell.spec.ts` "renders four separate field chips and never a fused badge" and `web/tests/unit/epistemic.test.ts` "four independent fields". |
| RISK-P15-02 | **Green is used for epistemic state** — saturated green reads as SIG *endorsing* a fact, which it never does (SIG-UI-006). | Every `--sig-epi-*` token is an `hsl()` whose hue is outside the green band [75°,165°], enforced by a stylesheet-parsing unit test and re-checked on the *rendered* hues in the browser. Proven by `web/tests/unit/design-tokens.test.ts` and `web/tests/e2e/shell.spec.ts` "no green for epistemic state, rendered". |
| RISK-P15-03 | **A contested value appears unmarked** — a reader who never opens the detail treats a disputed number as settled (SIG-UI-008). | `ContestedMarker` renders at every appearance — detail, map popup, table cell, graph list, and the SVG edge. Proven by `web/tests/e2e/shell.spec.ts` "contested marker is persistent across render paths". |
| RISK-P15-04 | **A gap reads as "nothing here"** — a hatched cell looks like proof of absence instead of an invitation (SIG-UI-007, §9.5). | Absence is one hatch texture with four distinguishable kinds, each a clickable GET link that generates a `GENERATED` research task on a pre-generated no-JS page. Proven by `web/tests/e2e/shell.spec.ts` "absence hatch → research task, end to end" and `web/tests/e2e/content.nojs.spec.ts`. |
| RISK-P15-05 | **A citation stops being reproducible after a correction** — the permalink silently resolves to the new value (SIG-UI-035, SIG-TIME-008). | Every page's permalink pins both as-of axes + the ruleset version; belief-time filtering (`resolveAsOfBelief`) makes a later-asserted correction invisible to the pinned belief. Proven by `web/tests/unit/citation.test.ts` "reproducible after a correction" and the every-page e2e citation check. |
| RISK-P15-06 | **Archivability erodes silently** — client JavaScript creeps in and the page stops rendering in a web archive years later (SIG-UI-036/037). | Astro `output: "static"` with no `client:*` directive ships zero client JS; the no-JS Playwright project renders every core surface with JavaScript disabled, and the Lighthouse `script:size` budget is 0 bytes. |

### Deviations recorded as ADRs (SIG-ENG-031)

| ADR | Deviation |
|---|---|
| ADR-049 | The dependency-licence gate is "OSI-approved **or** a short, explicitly-enumerated waiver" rather than literal OSI-only (SIG-UI-039): the Astro toolchain tree resolves two dependencies to `CC0-1.0` and `BlueOak-1.0.0` — permissive/public-domain, and none of the excluded categories (CC-BY-NC / source-available / BUSL). They sit in a separate `WAIVED` set (never mislabelled as OSI); any *other* non-OSI licence still fails the build. The self-hosted-tiles map renderer (SIG-UI-038) and Postgres FTS search (SIG-UI-040) are not implemented here (P15.3 / on demonstrated need); the reference map is a static, tile-CDN-free SVG + table. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P15-07 → BL-007 | The shell renders from committed TS fixtures, not the live `/v1` read API | Static-first means no build-time API dependency (SIG-UI-036), and the read API has no DB-wired store yet (RISK-P14-07/17) | `web/src/lib/fixtures.ts`'s `ResolutionEnvelope` is a faithful *subset* of `api/src/api/models.py`; wiring to the live API is a data-source swap, not a component change (ADR-049 revisit trigger). |
| RISK-P15-08 → BL-007 | Only reference/demo pages exist (visual-language, reference map/graph, task intake) — not the dossier, map, network, watch, or corrections surfaces | Those surfaces are P15.2–P15.5; P15.1 owns only the shared visual language + baseline | The components are the canonical, tested surface later tickets import; a change to the visual language is a new ADR, not an ad-hoc edit (§0.7, ADR-049). |

## Phase 15 — Public web surfaces (P15.2 — the local dossier)

Per §53 / SIG-ENG-031, P15.2's risk-register entries. P15.2 owns the **production** dossier — the
project's primary public artifact, built for a local advocate at a podium in six days (SIG-UI-002).
Its risks are **actionability** risks (the print path and the decision date are the design center, not
niceties) and **synthetic-certainty** risks (a gap or an unknown that reads as settled fact). See
ADR-050 for the decisions; it supersedes but retains the P06.1 `exports.dossier` renderer (ADR-032).

### Design / disclosure risks retired by executable checks

| id | Risk | Compensating control |
|---|---|---|
| RISK-P15-09 | **The print export is not a usable, citable document** — it is not genuinely paginated, or a page lacks the as-of date / permalink, so a page handed to a council member cannot be traced back (SIG-UI-013). | The dedicated print route (`dossier/[slug]/print.astro`) paginates into `.sig-print-page` blocks, **each** carrying a footer with the as-of pair and the belief-pinned permalink. Proven by `web/tests/e2e/dossier.spec.ts` "every print page carries a footer …" (footers == pages) and "renders to a usable, multi-byte PDF" (headless `page.pdf()` yields a real, >1-page `%PDF`). |
| RISK-P15-10 | **The surfaced expiry misleads** — a reader sees a contract's expiry date and misses that an auto-renewing contract's real deadline is the notice-window-earlier decision date, or `next_decision_date` drifts from what the renewal watch (P15.4) alerts on (SIG-UI-014b). | `next_decision_date` is a pure, never-stored derivation (`expiry − notice_window` when auto-renewing, else the expiry), rendered wherever the expiry is (the "cost and expiry" section) and exposed under one stable wire name P15.4 keys on. Proven by `web/tests/unit/dossier.test.ts` (the Appendix-D example: 2027-04-02 / 90d → 2027-01-02) and `web/tests/e2e/dossier.spec.ts` "shown wherever the expiry is". |
| RISK-P15-11 | **"What we don't know" is demoted to an appendix** — it appears in one surface but not another, so a machine or a reader who takes the summary or the API at face value never learns the gaps (SIG-UI-011). | The gap list is single-sourced in `renderDossierJson` and rendered in the HTML summary, its §39.2 section, and the print export, and emitted as a top-level `what_we_dont_know` key by the static JSON endpoint. Proven by `web/tests/e2e/dossier.spec.ts` "appears in the summary, the section, AND the API". |
| RISK-P15-12 | **An unknown value is silently omitted** — a policy whose configuration evidence is unknown reads as "no such policy" rather than "not yet researched", i.e. synthetic certainty (SIG-UI-012/015). | Rows render `null` as the literal "unknown" (`rowDisplayValue`); absence rows render the single clickable hatch; the incompleteness banner names the distinct-unresearched count. Proven by `web/tests/unit/dossier.test.ts` + `web/tests/e2e/dossier.spec.ts` / `dossier.nojs.spec.ts`. |

### Scaffolded / bounded requirements (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P15-13 → BL-007 | The dossier renders from a committed TS fixture for one worked jurisdiction, not the live `/v1` dossier API | Static-first means no build-time API dependency (SIG-UI-036), and the read API has no DB-wired store yet (RISK-P14-07/17) | `renderDossierJson`'s shape is the `/v1` dossier contract; wiring to the live API is a data-source swap, not a component change (ADR-050 revisit trigger). |
| RISK-P15-14 → BL-007 | A material figure's document link resolves to the claim endpoint (`/v1/claim/{id}`), not yet to the highlighted page/cell span (SIG-UI-014) | The span-level evidence viewer is §39.6 (a later P15 surface); the claim URL is the addressable locator that resolves the span, consistent with P15.1's contradiction view | Every reconciliation carries the rule, each competing claim's source/tier/date, and a resolvable document link; the fine-grained span is an additive drill-down the evidence viewer adds (SIG-UI-028). |

## Phase 15 — Public web surfaces (P15.3 — the infrastructure map + network explorer)

Per §53 / SIG-ENG-031, P15.3's risk-register entries. P15.3 owns the two spatial/graph surfaces
(§39.3/§39.4) and their honest-rendering rules, plus the static-PMTiles serving contract
(SIG-UI-038/SIG-GEO-012/013). Implementation is `web/` (SIG-ENG-010).

### Deviation recorded as an ADR (SIG-ENG-003)

| ADR | Deviation + rationale |
|---|---|
| ADR-051 | The static-PMTiles serving contract is landed as a **served, tested artifact** — a MapLibre GL style over self-hosted PMTiles v3 with OSM attribution at `/map/style.json` — but the **maplibre-gl runtime is NOT bundled** into the archivable pages (a deviation from ADR-018's "renderer"): doing so would ship client JS, failing the mechanically-enforced ADR-049 zero-JS invariant and the Lighthouse budgets (0 script bytes, ≤150 KB). The shipped `/map/` + `/network/` pages stay zero-JS with the tabular/list equivalent as source of truth; the OSM attribution renders in the static HTML (every context incl. print). This is the closest faithful alternative that keeps every hard CI gate green, and the requirement under test (SIG-UI-038/SIG-GEO-012/013 — the map *served* from static PMTiles with OSM attribution and no hard third-party CDN) is met and machine-verified. |

### Honest-rendering risks addressed

| id | Risk (what breaks the defining standard if unhandled) | Compensating control |
|---|---|---|
| RISK-P15-15 | **The map lies by default** — a user sees device points with the coverage underlay switched off, so a sparsely-covered area reads as "there is nothing here" (SIG-UI-017). | The point layer and the coverage underlay are governed by a **single** `LayerControl`; `coverageBoundToPoints`/`assertCoverageBinding` reject any control set that could show points without coverage. Proven by `web/tests/unit/map.test.ts` "coverage bound … by a single control" and `web/tests/e2e/map-network.spec.ts`. |
| RISK-P15-16 | **Low coverage reads as low density** — a barely-searched cell with a low count looks like a confidently-low count, understating capability (SIG-UI-018). | Low/absent-coverage cells are desaturated, value-suppressed, and hatched (`coverageEncoding`); a low-coverage count never renders as a density bucket (`renderBin` → bucket 0), and `readsAsDensity` is false. The two encodings are provably distinct. Proven by `web/tests/unit/map.test.ts` "low coverage MUST NOT read as low density" and `map-network.nojs.spec.ts`. |
| RISK-P15-17 | **No-coordinate assets are silently dropped** — a map showing only locatable assets systematically understates capability (SIG-UI-020). | `partitionByLocatability` rolls point-less / tier-3 assets into jurisdiction indicators with a conservation law (`locatable + Σ indicators = total`); the page renders them. Proven by `web/tests/unit/map.test.ts` + `web/tests/e2e/map-network.spec.ts` (conservation). |
| RISK-P15-18 | **A centrality figure appears without its ER-quality disclosure** — a hub statistic reads as fact when imperfect entity resolution makes it imperfect (SIG-UI-023, SIG-IDENT-030). | The disclosure is **structural**: a `CentralityStatistic` cannot be constructed without a valid `ErQuality` + inline `disclosure` (`centralityStatistic` throws), and it renders at the statistic, never a footnote. Proven by `web/tests/unit/network.test.ts` + `web/tests/e2e/map-network.spec.ts`/`.nojs.spec.ts`. |
| RISK-P15-19 | **A theoretical path is presented as a shared-data relationship** — a long speculative chain blurs into "these agencies share data" (SIG-UI-025, SIG-RECON-050). | A path beyond `SPECULATIVE_HOP_THRESHOLD` (3) is labelled **speculative** and excluded from headline figures; every hop carries per-hop evidence (an evidence-less hop is rejected); confidence is the path minimum. Mirrors `inference.access_paths`. Proven by `web/tests/unit/network.test.ts` + `web/tests/e2e/map-network.spec.ts`. |

### Deferred / not-fully-closed here (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P15-20 → BL-007 | The map/network render from committed TS fixtures for the worked Oklahoma City case, not the live `/v1` API | Static-first means no build-time API dependency (SIG-UI-036); the read API has no DB-wired store yet (RISK-P14-07/17) | The fixture shapes mirror the pipeline (`§19.4` tier, `§12.2` `access_kind`, the `inference.access_paths` hop list); wiring to the live API is a data-source swap, not a component change (ADR-051 revisit trigger). |
| RISK-P15-21 → BL-010 | No interactive MapLibre map ships; the served `/map/style.json` is not yet loaded by a running renderer, and the real `sig-infrastructure.pmtiles` / basemap archives do not exist yet | The zero-JS + perf gates forbid the runtime here (ADR-051); the `.pmtiles` binaries are a build artifact of the upstream geospatial phase (tippecanoe over the resolution projection), out of P15.3 scope | The serving **contract** (PMTiles v3, self-hosted relative paths, OSM attribution, no third-party CDN) is fixed and tested (`assertServingContract`), and the honest-rendering logic is single-sourced so an interactive renderer cannot diverge from the static render (ADR-051 revisit trigger). |

## Phase 15 — Public web surfaces (P15.4 — renewal watch + evidence recommender + evidence viewer)

Per §53 / SIG-ENG-031, P15.4's risk-register entries. P15.4 owns the actionable-timing
and evidence-inspection surfaces (§39.5/39.5a/39.6) and, critically, the recommender's
**neutrality guarantee** (SIG-UI-027b). Implementation is `web/` (SIG-ENG-010).

### Neutrality + honest-rendering risks addressed

| id | Risk (what breaks the defining standard if unhandled) | Compensating control |
|---|---|---|
| RISK-P15-22 | **The recommender becomes an advocacy instrument** — it ranks evidence by predicted persuasiveness / sentiment / vote effect, and SIG stops being a record (SIG-UI-027b). | Neutrality is **structural**: the `EvidenceArtifact` type carries only the six §39.5a axes; `assertNeutralInputs` rejects any artifact bearing a denylisted signal at runtime; the score is a pure function of the six axes with a per-axis breakdown; a D6 artifact is excluded. Proven by `web/tests/unit/recommender.test.ts` "the neutrality guarantee" and `web/tests/e2e/watch-evidence.spec.ts`. |
| RISK-P15-23 | **The watch alerts on the wrong date** — it surfaces the expiry, so a reader misses the auto-renewal notice deadline and the decision is made by default (SIG-UI-014b). | The watch reuses P15.2's `resolveTermination`/`nextDecisionDate` **verbatim** — it never recomputes or forks the wire name — so the alert date (expiry-minus-notice for an auto-renewing contract) is byte-identical to the dossier's. Proven by `web/tests/unit/watch.test.ts` and the iCal/RSS DTSTART/pubDate keyed on 2027-01-02, not 2027-04-02. |
| RISK-P15-24 | **A sealed capture leaks bytes** — the viewer renders withheld material, or presents an inference as an observation without its provenance (SIG-UI-030/028, §17.5). | The `Capture` tier invariant is enforced (`assertCaptureTier`): a sealed capture MUST carry no `document_text` and MUST explain why; the viewer renders metadata-only. `assertClaimView` enforces the full SIG-UI-028 provenance chain (method+version, review, digest, acquisition, full history) at build. Proven by `web/tests/unit/evidence-viewer.test.ts` + `web/tests/e2e/watch-evidence.spec.ts`. |

### Deferred / not-fully-closed here (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P15-25 → BL-007 | The watch, recommender, and viewer render from committed TS fixtures for the worked Oklahoma City case, not the live `/v1` API | Static-first means no build-time API dependency (SIG-UI-036); the read API has no DB-wired store yet (RISK-P14-07/17) | The fixture shapes mirror the pipeline (`TerminationInput`/`next_decision_date`, directness `D`/currency `C`, `storage_tier`/`capture_status`, extraction method + locator); wiring to the live API is a data-source swap, not a component change (ADR-052 revisit trigger). |
| RISK-P15-26 → BL-007 | The subscriptions are static per-jurisdiction feeds emitted at build, not a live/dynamic feed the moment a decision date changes | The zero-JS + static-first gates forbid a feed server here (ADR-049/052); a rebuild regenerates the feeds deterministically | The iCal/RSS serializers are single-sourced and tested (valid RFC 5545 with §3.1 folding, RSS 2.0), keyed on `next_decision_date`; a subscriber re-fetches the static file and a rebuild refreshes it (ADR-052 revisit trigger). |

## Phase 15 — Public web surfaces (P15.5 — research queue + corrections log + methodology/metrics + editorial standards)

Per §53 / SIG-ENG-031, P15.5's risk-register entries. P15.5 owns the editorial-standards
conformance gate and the corrections surface — the required eighth surface (SIG-UI-032),
the register rules, and the hostile-reader review whose disposition blocks release
(SIG-UI-042). Implementation is `web/` (SIG-ENG-010).

### Honesty + neutrality risks addressed

| id | Risk (what breaks the defining standard if unhandled) | Compensating control |
|---|---|---|
| RISK-P15-27 | **The coverage page publishes a total** — a completeness percentage or a capture–recapture population estimate implying SIG knows the denominator of reality, understating the very thing it documents (SIG-METRIC-008/010). | "Never a total" is **structural**: `CoverageMetric.is_population_total` is typed `false` (a total is unrepresentable), `assertCoverageMetric` requires a NAMED denominator and rejects "reality"/"all … that exist" and any missing population-unknown note, and only the four §32.5-legitimate kinds exist (no capture–recapture kind). Enforced at build in `coverage-metrics.astro` and proven by `web/tests/unit/metrics.test.ts` + the e2e "never claim a total". |
| RISK-P15-28 | **Generated rationale text editorializes** — a resolver-generated sentence characterizes, states an allegation as fact, or imputes motive, and SIG's own machinery violates the register it holds contributors to (SIG-UI-043/046). | The register rules are an executable denylist (`checkRegisterConformance`) applied to **generated rationale templates** at build (`style-guide.astro` calls `assertRegisterConformant`), mirroring the ADR-052 recommender-neutrality pattern; a violating template fails the build. Proven by `web/tests/unit/editorial.test.ts` "register conformance applies to generated text too". |
| RISK-P15-29 | **A dossier template ships with un-answered hostile-reader findings** — release proceeds while a sentence counsel would challenge is still open, so the dossier is attackable as evidence (SIG-UI-042). | Release is gated by `assertReviewReleasable`, run at build in `editorial-standards.astro`: it throws unless there are two independent reviewers and every finding carries a disposition + resolution. The review is committed with the template version (`HOSTILE_READER_REVIEW` + `docs/governance/hostile-reader-review-dossier.md`). Proven by `web/tests/unit/editorial.test.ts` "hostile-reader review release gate". |
| RISK-P15-30 | **Geographic claiming hardens into territorial gatekeeping** — a claimed jurisdiction excludes other contributors, defeating the federation principle (SIG-TASK-011). | Claiming is priority-only by construction: `claimStatusFor` always returns `anyone_may_work: true`, claims expire without renewal (`claimIsActive`), and there is no volume leaderboard (SIG-TASK-012). Proven by `web/tests/unit/research-queue.test.ts` + the e2e "claiming grants priority, never exclusivity". |

### Deferred / not-fully-closed here (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P15-31 → BL-007 | The research queue, corrections log, freshness, and coverage render from committed TS fixtures for the worked Oklahoma City case, not the live `tasks` / governance / metrics APIs | Static-first means no build-time API dependency (SIG-UI-036); those read paths have no DB-wired store yet (RISK-P14-07/17) | The fixture shapes mirror the engine's controlled vocabularies (`tasks.vocabulary`/`catalog` assignee/disposition/effort/scope, the §45 intake categories/outcomes, the §32.4/32.5 metric shapes); wiring to live data is a source swap, not a component change (ADR-053 revisit trigger). |
| RISK-P15-32 → BL-007 | The dispute intake is a static page describing the channel and its categories/priorities/outcomes, not a live submission endpoint that files a case | The zero-JS + static-first gates forbid an intake server here (ADR-049/053); the §45 backend (correction-as-new-assertion storage) is owned upstream and out of P15.5 scope | The one-click path is present on every page (`DisputeLink` in the base layout), the categories/priority/identity rules are single-sourced and tested, and the transparency report renders from the corrections fixture; wiring to the live intake is additive (ADR-053 revisit trigger). |

## Phase 16 — Contributors and contribution-back (P16.1 — the contributor system)

Per §53 / SIG-ENG-031, P16.1's risk-register entries. P16.1 owns the contributor-tier
model, the retention-minimisation posture ("what is not stored cannot be subpoenaed"),
and the revert-as-new-assertion contract that P16.2's contribution-back depends on
(ADR-054). The dominant live failure mode is **inflationary** — panic-driven or
adversarial over-reporting (R12-F12.28) — so the anomaly rules assume bad faith.

### Threat-resistance risks addressed

| id | Risk (what breaks the defining standard if unhandled) | Compensating control |
|---|---|---|
| RISK-P16-01 | **A contribution is auto-rejected**, silently discarding a real observation and letting an adversary tune submissions past the filter — or a false-*absence* campaign is treated as helpfulness and waved through (SIG-CONTRIB-010/011). | Auto-rejection is **unrepresentable**: `RoutingDecision` has only `accept` / `route_to_review`, so anomalous patterns (burst / coordinated-similar / contested-resolving) can only be *held for human review*. The detector never branches on `polarity`, so false-absence trips the identical rules. Proven by `test_tasks_poisoning.py` (`test_no_auto_reject_outcome_exists`, `test_false_absence_is_guarded_equally`, the three routing tests). |
| RISK-P16-02 | **A fabricated node enters the graph as an observation** — vendor V "operates" in region C where SIG has no evidence V operates at all (the active 2026-08 incident), inflating the record (SIG-CONTRIB-011a). | `check_operating_territory` holds an unsupported V-in-C claim at the **lowest confidence** and emits a **verification task instead of** letting it enter as an observation. Proven by `test_tasks_poisoning.py::test_unsupported_territory_held_at_lowest_confidence_with_task`. |
| RISK-P16-03 | **SIG becomes the proximate cause of a mass revert** — a SIG-fed suggestion, later judged implausible, drives a bulk bot-removal that damages SIG, the mapper, and the upstream project (SIG-CONTRIB-011b). | SIG never applies a revert: `apply_reverts_automatically` is a hard refusal and `RevertSuggestion(applied_by_sig=True)` cannot be constructed; only human-reviewed suggestions are produced. Proven by `test_tasks_poisoning.py::test_sig_never_auto_applies_a_mass_revert`. |
| RISK-P16-04 | **An unverified community observation renders with records-derived authority**, laundering an unconfirmed report into an apparently-sourced claim (SIG-CONTRIB-011c). | `visual_weight` places `UNVERIFIED_COMMUNITY` strictly below `RECORDS_DERIVED`; `assert_distinct_visual_weight` fails if they ever coincide. Proven by `test_tasks_poisoning.py::test_unverified_renders_below_records_derived`. |
| RISK-P16-05 | **Contributor PII accumulates and is later subpoenaed** — a real name, device id, or location history that never needed to exist becomes a compulsion target (SIG-CONTRIB-005). | Minimisation is structural: `SubmissionRecord` has no such fields (`FORBIDDEN_CONTRIBUTOR_DATA` asserted absent), `Contributor` is handle-keyed with no real-name field, and `OperationalLog.purge_expired` empties transient IP logs past `PII_MINIMISATION_WINDOW`. Proven by `test_tasks_submission.py` + `test_tasks_contributor.py::test_contributor_carries_no_real_name_field`. |

### Deferred / not-fully-closed here (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P16-06 → BL-040 | SIG-CONTRIB-003 the moderated usability study is run with **real** ontology-naïve humans | Running a session with five+ human participants is agentic, not a unit test | The as-run study is published (`docs/governance/contributor-onboarding-usability-study.md`) and its measured result is machine-checked (`tasks.onboarding.UsabilityStudy.meets_requirements` over `data/usability_study.toml`): ≥5 ontology-naïve participants, median ≤10 min. The gate re-checks on any flow change via a data swap (`test_tasks_onboarding.py`). |
| RISK-P16-07 → BL-005 | The contributor system is modelled in memory (tiers, submissions, revert, anomaly), not yet persisted to Postgres | Consistent with the established `tasks`/`policy.governance` pattern — the engine owns the rules; DB wiring is downstream | The revert contract is additionally proven over the **live** claim spine (`tests/db/test_reverts.py` via `claim.retraction_of`); the in-memory shapes mirror the SQL (`research_task`, the append-only claim table). Wiring a contributor/submission store is additive (ADR-054 revisit trigger). |
| RISK-P16-08 → BL-041 | SIG-CONTRIB-007/008 jurisdiction-aware know-your-rights + detained-contributor guidance shown during onboarding | Correctness of legal guidance is agentic and needs counsel review (cf. RISK-P0-11) | The prose policy is published + presence-tested (`docs/governance/contributor-safety.md`, `test_governance_docs.py`); the study protocol shows it before any field task; flagged for counsel review before launch. |

## Phase 16 — Contributors and contribution-back (P16.2 — contribution back)

Per §53 / SIG-ENG-031, P16.2's risk-register entries. P16.2 owns the human-mediated
suggestion posture and its two OSM compliance surfaces — the Automated Edits Code
(escaped by keeping a human in the loop) and the Organised Editing Guidelines
(satisfied by the registered activity page + hashtag), recorded in ADR-055. The
design objective is to minimise the human cost per resolution (~one decision per
device), never to maximise write volume (SIG-CONTRIB-017a).

### Threat-resistance risks addressed

| id | Risk (what breaks the defining standard if unhandled) | Compensating control |
|---|---|---|
| RISK-P16-09 | **A code path writes to OSM automatically** — a bot edit that OSM's Automated Edits Code "will treat as vandalism", risks a mass revert (RISK-P16-03), and makes SIG the proximate cause of harm to the mapper and the upstream project (SIG-CONTRIB-014). | An automated OSM write is **unrepresentable**: `tasks.contribution.write_to_osm` exists only to raise, and `AppliedEdit` refuses a `mapper_account` of "SIG". A suggestion becomes an edit only when a human mapper applies it in their own account (`apply_by_mapper`). Proven by `test_tasks_contribution.py::test_no_automated_osm_write_path_exists`, `::test_sig_can_never_be_the_account_that_applies_an_edit`. |
| RISK-P16-10 | **A contribution task is built on a licence-incompatible source** — publishing it would invite a mapper into a licence breach, making SIG the proximate cause (SIG-CONTRIB-016f, §42.3a). | The contribution-path gate runs **before rendering**: `tasks.contribution.build_suggestion` calls `policy.licensing.assert_contribution_permitted`, which blocks an `UNDETERMINED`, no-derivatives, or not-relicensable-to-ODbL source. Proven by `test_tasks_contribution.py::test_licence_gate_blocks_a_task_on_an_incompatible_source` and the `test_policy_licensing.py` contribution-gate suite. |
| RISK-P16-11 | **A SIG-originated edit is untraceable** — the §7 leverage metric collapses to inferring SIG's influence from tag-count deltas, and the contribution stream is not third-party auditable (SIG-CONTRIB-016e). | The declared hashtag `#sig_operator_attribution` is required on every SIG suggestion/edit (a missing one raises `MissingChangesetHashtagError`), and `LeverageLedger.accepted_operator_attributions` reads accepted upstream changesets bearing it — a public signal a critic can reproduce. Proven by `test_tasks_contribution.py::test_declared_hashtag_is_required_on_a_sig_suggestion`, `::test_leverage_metric_reads_accepted_edits_from_the_hashtag`. |
| RISK-P16-12 | **A claim's upstream is acknowledged only in aggregate** (an About page), breaking attribution reciprocity and the federation compact (SIG-CONTRIB-020). | Attribution is structural: the API `/claim` response carries per-claim `attribution`, and every exported row carries its `_rights` provenance. Proven by `test_api_coverage_license.py::test_claim_response_names_its_upstream_attribution` and `test_compartments.py::test_export_row_names_its_upstream_structurally`. |

### Deferred / not-fully-closed here (SIG-ENG-005)

| id | Requirement | Why not fully closed now | Compensating control |
|---|---|---|---|
| RISK-P16-13 → BL-038 | SIG-CONTRIB-016/016d the ADR and the Organised Editing activity page are **actually filed** with OSMF (the automated-edits scope conclusion and the registered activity) | Registering with the OSM community is an agentic, off-repo act needing a real OSM account and community consultation | The compliance analysis is recorded in ADR-055 and the activity page is published (`docs/governance/organised-editing-activity.md`) with every required disclosure machine-checked from `data/organised_editing.toml` (`OrganisedEditingActivity.__post_init__`); the `registered` flag + wiki namespace are recorded, flagged for real filing before launch. |
| RISK-P16-14 → BL-039 | The contribution system is modelled in memory; there is **no live MapRoulette client** and **no live OSM changeset feed** populating `LeverageLedger` | Consistent with the established `tasks`/`policy.governance` pattern — the engine owns the rules; a live client is downstream | The MapRoulette object-model crosswalk is documented and tested (`MAPROULETTE_FIELD_CROSSWALK`); the suggestion/apply/metric shapes mirror the challenge model. Wiring a live client + changeset feed is additive (ADR-055 revisit trigger). |
| RISK-P16-15 → BL-039 | The §7 leverage metric's **published surface** (§39.8 public metrics page) reads the live count | P15.5's metrics page renders from committed fixtures (RISK-P15-31); the live tasks/metrics read paths have no DB-wired store yet | `LeverageLedger` computes the metric deterministically from hashtag-bearing changesets; wiring it into the published page is a source swap, not a component change (ADR-053/ADR-055 revisit triggers). |
| RISK-P16-16 → BL-035 | SIG-LIC-009 counsel review: whether device-linked API responses / OSM-sourced geometry constitute ODbL derivative-database distribution | Legal determination needs counsel (carried from §42.3a) | Recorded here and in ADR-055; the ODbL asset layer stays in its own compartment (ADR-011) and the contributed subset is CC0 (SIG-LIC-007a); flagged for counsel before launch. |

## Phase 17 — Broader surveillance technologies (P17.1 — private-camera federation + RTCC integration)

Per §53 / SIG-ENG-031, P17.1's risk-register entries. P17.1 is the standing proof
of §5.2: it *populates* the Stage-5 span (private-camera federation, RTCC
integration hubs, the six-layer commercial data-broker chain) over the frozen
schema and proves it with the generalization conformance suite. No LinkML source,
generated artifact, or wire contract changed — so **no ADR is required** (an ADR
records a *deviation*, and there is none). The one design risk is that a future
Stage-5 construct silently forces a schema change; the compensating control makes
that impossible to do silently.

### The Phase-1-defect record path (SIG-CHART-027/028, AC1)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P17-01 | **A Stage-5 construct is populated by silently widening the schema** — a hand-edit to the LinkML source or generated artifacts to make a technology "fit", which would falsify the §5.2 generalization guarantee (SIG-CHART-027) and cross into P01.1's ownership. | The population is a **test-only** instance graph over the *committed* Pydantic model and vocabulary; `verify-gen` in `make check` fails if any generated artifact drifts from the source, and `test_stage5_federation.py::test_stage5_population_required_no_schema_change` fails if any edge type, role, entity class, or §13.1 slug the pathways need is not already present. A required change therefore surfaces as a **red conformance test** — the recorded Phase-1 defect — and is filed against the ontology (P01.1), never patched in this ticket. No such defect was found: all three pathways populate with the frozen schema. |

### Deferred / out of scope here (SIG-ENG-005)

| id | Requirement | Why not addressed here | Compensating control |
|---|---|---|---|
| RISK-P17-02 → BL-043 | The remaining Phase-17 priority technologies — facial recognition, cell-site simulators, mobile-device forensics, and federal authorization datasets (**P17.2**); gunshot detection, drones, and commercial location-data ingestion (**P17.3**) | Explicitly out of scope for P17.1 (the phase is populated technology-by-technology, OL-17.5-01) | Each has its own ticket; the schema-absorption guarantee proven here (SIG-CHART-027) is the invariant those tickets extend. The §22.7 EFF Data Library roster is the registered Phase-17 ingestion backlog (SIG-INGEST-041). |
| RISK-P17-03 → BL-043 | The populated pathways are **instance graphs in the conformance suite**, not rows persisted to the claim spine | P17.1 is the §5.2 expressibility proof, not an ingestion connector; live population arrives with the Stage-5 connectors (P17.2/P17.3) over the same frozen schema | The instance shapes mirror the generated model exactly (they *are* the generated Pydantic classes); persisting them is additive and needs no schema change, which is precisely what this ticket proves. |

### Modelling observations (not a schema change here)

| id | Observation | Why it is not acted on here | Note for the ontology owner (P01.1) |
|---|---|---|---|
| RISK-P17-04 | `RoleAssignment` inherits the required `edge_type` from `Edge`, but the closed §12 catalog has no role-specific member — the role semantics live entirely in `role`/`party`/`over` (§12.4). Populating owner ≠ operator therefore carries a structurally-valid-but-semantically-orthogonal `edge_type`. | The separation **is** representable (SIG-ONTO-048 is satisfied — the tests assert on `role`/`party`/`over`, never on the inherited `edge_type`), so no schema change is required and none is made here (P01.1 owns the LinkML source). | A future refinement could drop `edge_type` from `RoleAssignment` or add a dedicated `holds_role` catalog member; recorded as an observation, not a Phase-1 defect, because expressibility is intact. |

## Phase 17 — Broader surveillance technologies (P17.2 — facial recognition, cell-site simulators, mobile-device forensics)

Per §53 / SIG-ENG-031, P17.2's risk-register entries. P17.2 continues the §5.2
proof P17.1 began: it *populates* facial recognition, cell-site simulators, and
mobile-device forensics — plus the federal-authorization case — over the frozen
schema and proves it with the generalization conformance suite. No LinkML source,
generated artifact, or wire contract changed — so **no ADR is required** (an ADR
records a *deviation*, and there is none). The design risk is identical to P17.1's:
that a Stage-5 construct silently forces a schema change; the compensating control
makes that impossible to do silently.

### The Phase-1-defect record path (SIG-CHART-027/028, AC1)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P17-05 | **A Stage-5 construct is populated by silently widening the schema** — a hand-edit to the LinkML source or generated artifacts to make facial recognition, a cell-site simulator, a forensic extraction, or a federal authorization "fit", which would falsify the §5.2 generalization guarantee (SIG-CHART-027) and cross into P01.1's ownership. | The population is a **test-only** instance graph over the *committed* Pydantic model, `capability.yaml`, and `technology.yaml`; `verify-gen` in `make check` fails if any generated artifact drifts from the source, and `test_stage5_forensics.py::test_stage5_forensics_required_no_schema_change` fails if any capability slug, edge type, entity class, technology slug, or lifecycle state the constructs need is not already present. A required change therefore surfaces as a **red conformance test** — the recorded Phase-1 defect — filed against the ontology (P01.1), never patched in this ticket. No such defect was found: all constructs populate with the frozen schema (`verify-gen` byte-clean). |

### Modelling observations (not a schema change here)

| id | Observation | Why it is not acted on here | Note for the ontology owner (P01.1) |
|---|---|---|---|
| RISK-P17-06 | §11.10's FR illustration names predicates `can_query` and `searches_against`, but the **closed §12 catalog** (SIG-ONTO-041) contains neither — it realises "the query moves, the corpus stays" as `federates_search_to` (and its perspectival inverse `is_queryable_by`). | The construct **is** expressible (SIG-ONTO-031 is satisfied — FR resolves to a reference `DataSystem` via `federates_search_to`, `data_comes_to_rest=False`), so no new edge type is required and none is added here. | The illustrative predicate names in §11.10 are prose, not catalog members; a future refinement could align the prose with the catalog. Recorded as an observation, not a Phase-1 defect. |
| RISK-P17-07 | The `authorizes` edge (§12.1, "A grants B legal permission … no data moves") is populated as a `StructuralEdge`; the closed catalog does not bind `authorizes` to a specific `Edge` subclass. | A structural (non-data-bearing) carrier is the faithful choice for a permission relationship; the test asserts on `edge_type`/`source`/`target` and the native validity interval, never on the subclass. Expressibility is intact, so no schema change is made (P01.1 owns the LinkML source). | A future refinement could add a dedicated legal/authorization edge class; recorded as an observation, not a Phase-1 defect. |

### Deferred / out of scope here (SIG-ENG-005)

| id | Requirement | Why not addressed here | Compensating control |
|---|---|---|---|
| RISK-P17-08 → BL-043 | The remaining Phase-17 priority technologies — gunshot detection, drones, and commercial location-data ingestion (**P17.3**); private-camera federation, RTCC, and the data-broker chain (**P17.1**, landed) | Explicitly out of scope for P17.2 (the phase is populated technology-by-technology, OL-17.5-01) | Each has its own ticket; the schema-absorption guarantee proven here (SIG-CHART-027) is the invariant those tickets extend. The §22.7 EFF Data Library roster is the registered Phase-17 ingestion backlog (SIG-INGEST-041). |
| RISK-P17-09 → BL-043 | The populated constructs are **instance graphs in the conformance suite**, not rows persisted to the claim spine, and there is **no live authorization-dataset connector** (§23) | P17.2 is the §5.2 expressibility proof, not an ingestion connector; live population arrives with the Stage-5 connectors over the same frozen schema | The instance shapes mirror the generated model exactly (they *are* the generated Pydantic classes); persisting them — and wiring a §23 authorization-dataset connector that maps native validity intervals to EDTF via `db.edtf` — is additive and needs no schema change, which is precisely what this ticket proves. |

## Phase 17 — Broader surveillance technologies (P17.3 — gunshot detection, drones, commercial location data)

Per §53 / SIG-ENG-031, P17.3's risk-register entries. P17.3 continues the §5.2
proof P17.1/P17.2 began: it *populates* gunshot detection, drones, and commercial
location data over the frozen schema and proves it with the generalization
conformance suite. The load-bearing constraint is SIG-ONTO-027: acoustic gunshot
sensors and drones are **non-camera physical sensors** and MUST be representable
without a camera abstraction. No LinkML source, generated artifact, or wire
contract changed — so **no ADR is required** (an ADR records a *deviation*, and
there is none). The design risk is identical to P17.1/P17.2's: that a Stage-5
construct silently forces a schema change; the compensating control makes that
impossible to do silently.

### The Phase-1-defect record path (SIG-CHART-027/028, AC1)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P17-10 | **A Stage-5 construct is populated by silently widening the schema** — a hand-edit to the LinkML source or generated artifacts to make gunshot detection, a drone, or a commercial location subscription "fit" (e.g. adding an `airborne` mobility value, an `acoustic`/`robotics-aerial`/`data-acquisition` technology, or a `subscribes_to` edge that did not already exist), which would falsify the §5.2 generalization guarantee (SIG-CHART-027) and cross into P01.1's ownership. | The population is a **test-only** instance graph over the *committed* Pydantic model, `capability.yaml`, and `technology.yaml`; `verify-gen` in `make check` fails if any generated artifact drifts from the source, and `test_stage5_acoustic_drone_location.py::test_stage5_acoustic_drone_location_required_no_schema_change` fails if any capability slug, edge type, entity class, technology slug, mobility value, or role the constructs need is not already present. A required change therefore surfaces as a **red conformance test** — the recorded Phase-1 defect — filed against the ontology (P01.1), never patched in this ticket. No such defect was found: all constructs populate with the frozen schema (`verify-gen` byte-clean). |

### Modelling observations (not a schema change here)

| id | Observation | Why it is not acted on here | Note for the ontology owner (P01.1) |
|---|---|---|---|
| RISK-P17-11 | Gunshot detection has both a specific slug (`gunshot-detection-fixed`) and an `-unspecified` coarsest-level slug under the `acoustic`/`gunshot-detection` family; the drone family likewise carries `uas-general`, `drone-as-first-responder`, and `uas-unspecified`. The population uses the *specific* slugs where the OSM/evidence signature supports them. | The coarsest-level fallback is a deliberate ontology feature (evidence names the family but not the discriminator), not a gap; choosing the specific slug where warranted is correct, and both levels already exist. Expressibility is intact, so no schema change is made (P01.1 owns the LinkML source). | No action required; recorded to document that the coarsest-level slugs are available for lower-confidence evidence. |
| RISK-P17-12 | The `RoleAssignment` used to place the rooftop gunshot sensor's coordinate risk on the **host** (§43.3, §12.4 item 6) inherits the required `edge_type` from `Edge`, which the closed §12 catalog does not specialise for roles (the same observation as RISK-P17-04). | The host ≠ operator separation **is** representable (SIG-ONTO-048 — the tests assert on `role`/`party`/`over`, never on the inherited `edge_type`), so no schema change is required and none is made here. | Same note as RISK-P17-04: a future refinement could drop `edge_type` from `RoleAssignment` or add a role-specific catalog member. Recorded as an observation, not a Phase-1 defect. |

### Deferred / out of scope here (SIG-ENG-005)

| id | Requirement | Why not addressed here | Compensating control |
|---|---|---|---|
| RISK-P17-13 → BL-043 | The other Phase-17 technology spans — private-camera federation, RTCC, and the data-broker chain (**P17.1**); facial recognition, cell-site simulators, mobile-device forensics, and federal authorization datasets (**P17.2**) — both landed | Explicitly out of scope for P17.3 (the phase is populated technology-by-technology, OL-17.5-01) | Each has its own ticket; the schema-absorption guarantee proven here (SIG-CHART-027) is the invariant those tickets share. The §22.7 EFF Data Library roster is the registered Phase-17 ingestion backlog (SIG-INGEST-041). |
| RISK-P17-14 → BL-043 | The populated constructs are **instance graphs in the conformance suite**, not rows persisted to the claim spine, and there is **no live gunshot/drone/location-data connector** (§23) | P17.3 is the §5.2 expressibility proof, not an ingestion connector; live population arrives with the Stage-5 connectors over the same frozen schema (gunshot detectors already exist in OSM as `gunshot_detector`, R1-F1.3, ready for that connector) | The instance shapes mirror the generated model exactly (they *are* the generated Pydantic classes); persisting them — and wiring a §23 connector that carries the host-role coordinate rule (§43.3) — is additive and needs no schema change, which is precisely what this ticket proves. |

## Phase 18 — International adapter #1 (P18.1 — the jurisdiction adapter framework)

Per §53 / SIG-ENG-031, P18.1's risk-register entries. P18.1 **owns the jurisdiction
adapter framework** (§5.3) that P18.2 (France/Belgium) is the first consumer of:
country-namespaced vocabularies under a shared abstract parent (SIG-ONTO-068), BCP-47
labels with a transliteration qualifier (SIG-ONTO-069), jurisdiction-conditional
publication (SIG-PUB-017), and coarse international ingestion (SIG-ENG-036/INGEST-042).
Unlike the P17.x "populated with no schema change" tickets, P18.1 makes **additive
schema changes** (national enum children via LinkML `is_a`, a `transliteration_scheme`
slot), so **ADR-056 records the deviation** and `verify-gen` proves the committed
generated artifacts match a fresh generation.

### The no-US-shaped-assumption guarantee (SIG-CHART-029/030, SIG-ONTO-068)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P18-01 | **A US-shaped assumption re-enters through the vocabulary** — a national type added by widening a `us.*` enum, or a non-US adapter that reaches for a `us.*` term — falsifying SIG-CHART-030 / SIG-ONTO-068. | The us.* permissible set of each internationalised enum is **frozen** and asserted (`tests/ontology/test_i18n.py::test_no_us_enum_was_widened`); national children are added only under their own namespace with a country-neutral abstract parent (`::test_every_non_us_national_child_has_a_shared_abstract_parent`); and `policy.jurisdiction.assert_no_us_shaped_assumption` raises on any foreign-namespace term in a non-US adapter (`tests/unit/test_jurisdiction_adapter.py::test_a_us_term_in_a_non_us_adapter_is_rejected`). A regression surfaces as a red test. |
| RISK-P18-02 | **The adapter checklist drifts from the real ontology** — an adapter declares an org/legal/records term that is not a permissible value of the corresponding enum, so the checklist "passes" against a private string list. | The adapter vocabulary is cross-checked against the LinkML enums (`tests/unit/test_jurisdiction_adapter.py::test_adapter_vocab_terms_are_real_ontology_enum_values`); a typo or a removed enum value fails CI. |

### Additive schema deviation (ADR-056)

| id | Deviation | Why it is safe / bounded | Compensating control |
|---|---|---|---|
| RISK-P18-03 | P18.1 edits the LinkML source (enum `is_a` linkage + national children; `transliteration_scheme` slot) and regenerates every artifact — a schema change, unlike P17.x. | Purely **additive**: no existing permissible value, wire name, or slot is removed or renamed (SIG-ENG-003 back-compat); new slots are optional (today's-behaviour default = absent). Pre-existing `us.gov.*` / sector `private.*` values are untouched. | `make check` `verify-gen` proves the committed `ontology/generated` tree equals a fresh byte-deterministic generation; the P02 claim-spine DDL is regenerated from the same source. ADR-056 records the deviation and its revisit trigger. |

### Deferred / out of scope here (SIG-ENG-005)

| id | Requirement | Why not addressed here | Compensating control |
|---|---|---|---|
| RISK-P18-04 → BL-042 | The **per-source ingestion checklist items** — boundary sources, Wikidata coverage, the law-enforcement organisation registry, procurement portals, the official gazette, DPA corpora, date/number locale (R9 Part I items 2/4/5/8/11/13/14/16) — are not gated by the framework. | These are per-country *connector* work (the France RAA → arrêté pipeline, DECP procurement, CADA/CNIL corpora), which is **P18.2**, not the framework. | They are recorded in `policy.jurisdiction.CHECKLIST_ITEMS` as items the framework does not yet gate, mapped `None`, so a reader sees exactly what a live onboarding still owes. The adapter ships read-only until a local partner is named (item 18). |
| RISK-P18-05 → BL-042 | The coarse-international layer is the **claim shape + anti-disaggregation guard**, not a live connector; the three datasets (Carnegie AI GSI, Facial Recognition World Map, ASPI) are registered `ingestion_permitted = false`. | The datasets are LINK-posture / UNDETERMINED pending rights review (§22.7); a live fetch connector is downstream, exactly as the source-registry gate intends. | `connectors.coarse_international.assert_not_disaggregated` refuses agency-level disaggregation at the seam (`tests/connectors/test_coarse_international.py::test_agency_level_disaggregation_is_refused`), so the P4 guarantee holds the moment a connector is wired; the registry rows fail the ingestion gate closed until reviewed. |
| RISK-P18-06 → BL-042 | **The France/Belgium connectors themselves** (Technopolice, prefectoral-order → LegalInstrument, national procurement → Contract, the ~12,000-camera OSM import study) are not built here. | Explicitly out of scope — **P18.2**. | P18.1 provides the framework (namespaced vocabularies under a national parent, the adapter checklist, coarse-granularity guard) those connectors consume; each will exercise one adapter end-to-end (ingest → reconcile → serve). |

## Phase 18 — International adapter #1 (P18.2 — the France/Belgium connectors)

Per §53 / SIG-ENG-031, P18.2's risk-register entries. P18.2 is the **first consumer**
of the P18.1 jurisdiction adapter framework and its §5.3 stress-test: it builds the
France/Belgium (Technopolice) connectors — published prefectural orders →
`LegalInstrument`, national open-data procurement (DECP) → `Contract`, the non-US
records-request vocabulary incl. `no_equivalent_available` — and studies the
already-executed ~12,000-camera OSM import (SIG-CONTRIB-016). It makes **additive
schema changes** (the `be.*` national children + a few `fr.*` org types), so
**ADR-057 records the deviation** and `verify-gen` proves the committed generated
artifacts match a fresh generation.

### The §5.3 stress-test: both authorization and procurement must map (SIG-ONTO-032, §11.14)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P18-07 | **Authorization by prefectural order fails to map onto `LegalInstrument`** — the arrêté préfectoral is a §5.3 defect if it needs a shape the model cannot hold. | It maps: `prefectoral_order_from_raa` builds a `LegalInstrument` with `instrument_type=fr.arrete_prefectoral` (a national child of the abstract `prefectoral_order` parent), and `abstract_instrument_type` rolls it up so AC2's "maps onto `instrument_type=prefectoral_order`" is a queryable property (`tests/connectors/test_france_belgium.py::test_prefectoral_order_maps_onto_legal_instrument_prefectoral_order`). |
| RISK-P18-08 | **National open-data procurement fails to map onto `Contract`**, or a framework-agreement piggyback silently drops `parent_cooperative_contract` (SIG-ONTO-032), so a missing local RFP reads as "no procurement". | `contract_from_decp` maps a DECP record 1:1 onto the country-neutral `Contract`; a marché riding an `idAccordCadre` is reclassified to `cooperative_piggyback`, and the `Contract` dataclass's `__post_init__` refuses that channel without a `parent_cooperative_contract` (`::test_decp_framework_agreement_is_a_piggyback_that_links_its_master`). |
| RISK-P18-09 | **A US-shaped records term leaks into the non-US connector** — `foia_request` / `us.foia` — falsifying AC1. | `assert_not_us_records_method` refuses the three US terms at the seam, and the connector emits only `fr.cada` / `no_equivalent_available` (`::test_records_connector_emits_fr_cada_not_foia`, `::test_a_us_records_method_is_refused`). The vocab↔ontology lock-step test catches drift. |

### Additive schema deviation (ADR-057)

| id | Deviation | Why it is safe / bounded | Compensating control |
|---|---|---|---|
| RISK-P18-10 | P18.2 adds `be.*` national children (JurisdictionType/OrganizationType/LegalInstrumentType) and a few `fr.*` org types, and regenerates every artifact. | Purely **additive**: no existing permissible value, wire name, or slot is removed or renamed (SIG-ENG-003); the frozen `us.*` org set is unchanged; `fr.gendarmerie` (P18.1) is kept, no duplicate added. | `make check` `verify-gen` proves the committed `ontology/generated` tree equals a fresh byte-deterministic generation; `tests/unit/test_france_belgium_adapter.py::test_no_us_enum_was_widened_for_france_or_belgium` asserts the frozen us.* baseline; ADR-057 records the deviation. |

### Modelling choices recorded (not defects)

| id | Observation | Why it is not a defect | Note |
|---|---|---|---|
| RISK-P18-11 | Belgium's national camera register exists but is inaccessible (Belgian-eID wall, F9.31) — a *known-complete-unknown* — represented as an `acquisition_method=no_equivalent_available` claim with a `known_complete_unknown` flag, not a `db.absence` state. | The register is neither `NO_EVIDENCE_FOUND` nor `EVIDENCE_OF_ABSENCE`; forcing it into the §9.5 absence vocabulary would misrepresent it. The flag records the state faithfully. | A dedicated coverage state for "complete authoritative register exists but is inaccessible" is an additive §9.5 extension a later ticket can make; recorded, not acted on here. |
| RISK-P18-12 | DECP carries a `modifications[]` amendment history and a `dureeMois` from which `end_date` is derivable; the connector preserves modifications in `raw` and leaves `end_date` unset rather than fabricating an "amended" `ProcurementState` (there is none) or a stored end date (F9.16). | Modelling amendments as first-class dated sub-events and a derived/stated `end_date` flag is an additive extension; fabricating a state or a value would violate P2/P4. | Recorded for the ontology owner (P01.1) as a candidate `Contract` refinement, not a Phase-18 defect. |

### Deferred / out of scope here (SIG-ENG-005)

| id | Requirement | Why not addressed here | Compensating control |
|---|---|---|---|
| RISK-P18-13 → BL-042 | **Live fetch** of the France/Belgium sources and **arrêté-PDF text extraction / segmentation** are not performed here. | The three sources (`raa_prefectures`, `madada`, `declarationcamera_be`) are registered `ingestion_permitted = false` pending rights review (§22.6 I), and the PDF parser is P07.1's, only *called* here (SIG-INGEST-046a). | The connectors interpret the documented DECP/RAA record shapes (F9.16/F9.18) over fixtures end-to-end; a live run is a data-gate flip plus wiring the P07.1 parser, no schema change. |
| RISK-P18-14 → BL-039 | Any **SIG-originated OSM contribution executed at scale** is not performed here. | Explicitly out of scope — gated on the import study (this ticket) and the P16.2 human-mediated contribution-back architecture (SIG-CONTRIB-014/015). | `connectors.osm_import_study.assert_import_studied_before_scaled_contribution` refuses a scaled proposal until conventions/consultation/outcome are documented (`tests/connectors/test_osm_import_study.py::test_gate_refuses_a_scaled_contribution_when_a_section_is_undocumented`); a bulk contribution still owes the full SIG-CONTRIB-016c requirements. |

## Phase 19 — Post-build capstone (P19.1 — build memory)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P19-01 | **A committed build-memory digest carries personal data of a private individual** — the ticket contracts and the planning artifacts promoted to `docs/build/` (and later capstone/backlog reports) could quote a name, email, or handle that Part VIII (§0.7) forbids committing. | The step-2 personal-data scan is run before staging every copied file (emails / phone-like / `@`-handle patterns); the P19.1 scan found none (the artifacts quote only public officials and project ids). Raw run ledgers and PR bodies stay **uncommitted** under `.agents/scratch/` (gitignored); anything flagged in a future promotion is redacted and noted before commit. |
| RISK-P19-02 | **Unifying and renaming the 44 scratch ledgers loses build provenance** — the three historical naming styles collapse to `implement-spec_<PXX.Y>.md`, so the link from a ticket back to its run record could be broken. | Ledgers are **moved/renamed only** (contents never edited, invariant P1–P3) and the full original-path → new-path mapping table is recorded in `.agents/scratch/README.md`; `docs/build/BUILD_INDEX.md` independently links each ticket to its ledger and PR body, so provenance is reconstructable from committed memory even though the raw ledgers stay gitignored. |

## Phase 19 — Capstone gap analysis (P19.2)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P19-03 | **The 668 coverage verdicts are one reader's judgement** — a single independent pass over spec + code + tests can misjudge a row (mark MET where a composed path is unwired, or MISSING where a design property already satisfies the requirement), and downstream tickets (P19.4/P19.5/P20.1) inherit that judgement instead of re-deriving it. | Two controls: (1) a **seeded 10-row spot-check** (§h) runs the named tests for `covered+tested` rows — 10/10 passed, so at least that class's evidence is executable, not asserted; (2) **P19.3's composed run** exercises the full stack end-to-end and will convert every AT-RISK-INTEGRATION verdict into a demonstrated pass or a recorded blocker, and the `docs/build/tools/check_coverage_matrix.py` gate keeps the matrix internally consistent (668 rows, valid enums, every non-MET row routed). "No synthetic certainty" — rows the reader could not confirm are PARTIAL, never MET. |
| RISK-P19-04 | **The id→ticket mapping is derived from PR bodies + ADR `Requirement ids`, so silently-implemented ids can be mis-scored** — an id implemented in code but never cited in a PR body, ADR, test, or traceability row appears "uncovered" and could be wrongly routed or marked PARTIAL/MISSING when it is in fact satisfied. | The `class=covered+untested` rows (142) are exactly this population — they carry a `src`/DDL/ADR evidence anchor and verdict MET, and are the explicit backfill work list for **P19.4/P20.1** (test + traceability backfill). Range-notation expansion (per SCOPING §i) is applied to every evidence class so range-cited ids are not missed, and the matrix records the anchor for each so a reviewer can confirm the id is genuinely implemented rather than trusting the score. |

## Phase 19 — Composed verification (P19.3)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P19-05 | **The composed end-to-end test depends on Docker, so it skips locally and could silently no-op** — the whole point of `tests/e2e/test_composed_stack.py` (the first time the PG18+PostGIS spine → OCFL → connectors → resolution → API → exports → `web/` path runs as one unit) is lost if a missing daemon is treated as "green". | The module mirrors `tests/db/conftest.py`: without a reachable Docker daemon it **skips cleanly**, but with `SIG_REQUIRE_DB_TESTS=1` (which CI sets) a missing daemon is a **hard failure** (`_require_or_skip`, imported not re-invented) — so the composed path can never silently no-op. CI (`ubuntu-latest`, Docker present) runs the suite for real; the local dev gate `make test-db` (114 passed) and the no-Docker skip check both pass. Verified: `DOCKER_HOST=tcp://127.0.0.1:1 uv run pytest tests/e2e` → module skips; `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra` → 10 passed, 4 xfailed, 0 failed, 0 skipped. |
| RISK-P19-06 | **Fixture replay is not a live fetch, so a green composed run could be mistaken for "the connectors work against real sources"** — S3 replays `atlas`/`osm` over committed fixtures through the real pipeline, which proves the interpretation stages but not the network transport (all sources stay `ingestion_permitted=false`; `assert_loadable` would refuse — 0 sources permitted). | The composed test is explicit that replay ≠ live fetch (SIG-INGEST-018): it drives `replay()` over archived captures under network isolation and records the connector→PG write as an `xfail` (`LD-F06b`), never a pass. Real, rights-gated live fetches are **P21.3**; the loader gate stays fail-closed. The `tests/e2e/test_isolation_reproof.py` re-proof (LD-X06) confirms a DNS lookup from inside a connector run still fails the run, so an accidental egress during replay cannot masquerade as success. |

## Phase 19 — Spine wiring (P19.4)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P19-07 | **Compute-on-read annotations can diverge from the persisted rows once P21.2 lands** — `PgReadStore._compute_on_read()` derives contradictions/tasks by running `RESOLVE` over the live claims (the `graph_annotations` tables are empty until P21.2). When P21.2 begins materialising those rows, a read that prefers persisted rows could silently disagree with what the resolver would compute now, so a stale or mis-built annotation could be published as authoritative. | The seam is explicit and single-homed: `_compute_on_read()` is the only annotation source today, documented in ADR-059 as *the* thing P21.2 replaces. P21.2 owns a `--recompute` diagnostic that recomputes annotations from the claims and a **rebuild-equality test** asserting the persisted rows equal the computed ones (byte-identical decision keys, SIG-RECON-020); until then the store reads persisted rows *only if any exist* and otherwise computes, so it can never serve a half-materialised set. Contradictions stay visible either way (§3.1). |
| RISK-P19-08 | **A PG connection opened per `PgReadStore` instance does not scale** — the store opens one psycopg connection at construction; under a real request load (a connection per request, or a long-lived store shared across threads) this is either connection-churn or a single-connection bottleneck, and an unpooled connection can exhaust the server's backends. | Documented as a known, bounded limitation (ADR-059 revisit trigger): the store exposes `close()` and holds exactly one connection with RLS enabled (never `BYPASSRLS`), so behaviour is correct if not yet fast. Production pooling (pgbouncer or a psycopg pool behind the same `PgReadStore` seam) is a drop-in change that does not touch the `ReadStore` Protocol or `create_app`; the `--dsn` serve path and the tests exercise the seam so the pool can be added without a contract change. |

## Phase 19 — Gap closure (P19.5)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P19-09 | **The TypeScript publication mirror can drift from the Python policy.** Jurisdiction-conditional publication (SIG-PUB-017) is decided at web build time in `web/src/lib/publication.ts`, a hand-written mirror of `policy.jurisdiction.adapter_publication_permitted`. If the Python jurisdiction table changes (a jurisdiction flips `public_employee_names_publishable`) without the TS mirror following, the web surface could publish a name the export gate would withhold — a §0.7 violation. | The mirror is pinned to the same rule and unit-tested against the US/FR/BE cases (`web/tests/unit/publication.test.ts`) plus an e2e assertion that the FR/BE dossiers withhold and the US one publishes (`jurisdiction.spec.ts` + `.nojs`); the mirror only ever **withholds** (an unknown jurisdiction defaults to no-publish), so a drift fails safe (over-withholding), never open. Generating the TS table from the Python data is the documented next step (ADR-061 revisit trigger) if the table grows. |
| RISK-P19-10 | **Compute-on-read ER: `sig-resolution match --dsn` re-scores rather than reads persisted matches.** ER over PG (LD-F04) enqueues proposals and appends `review_decision` rows, but the match itself is recomputed from `organization` candidates each run; it does not yet read a persisted match table, so a change to the matcher or the candidate set changes what is proposed. | The proposals are idempotent (`review_item` `ON CONFLICT DO NOTHING`) and the decisions are append-only (`review_decision`, history on repeat, `decided_at` by the DB), so re-running match never duplicates a proposal and never rewrites a decision; persisting the *resolved* match/annotation set is explicitly P21.2 (ADR-061 revisit trigger), the same seam as RISK-P19-07. The JSONL/in-memory `ReviewQueue` remains the default, so existing behaviour is unchanged. |

## Phase 20 — Backlog & readiness (P20.1)

Per §53 / SIG-ENG-031, P20.1's risk-register entry. P20.1 replaces the four
overlapping backlogs (the risk-register deferred-class tables, the ADR
`## Revisit trigger` sections, `LEDGER_DEFERRALS.md`, and the `CHECKLIST_ITEMS→None`
pattern) with **one** normalized `docs/build/BACKLOG.csv` where every deferred RISK
row, every ADR revisit trigger, and every LD row appears in **exactly one** `sources`
cell (defining standard §3.1). This section adds no code; the phase gate is uniform
(`make check` green) and this register + the traceability doc are the deliverables.

### Backlog-drift risk and its compensating control (SIG-ENG-005)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P20-01 | **Backlog drift — two sources of truth re-emerge.** Once the risk register keeps its `BL-nnn` cross-refs and `BACKLOG.csv` keeps the deferred items, an editor could add a deferred RISK row, an ADR revisit trigger, or an LD row without a backlog id (an orphan), or map one source into two items (a double-owned source), so the "one backlog" invariant silently rots. The obvious fix — put the check in `make check` — is **declined**: `check_backlog.py` reads `docs/adr/*.md` and `docs/risk_register.md`, which change every phase, so wiring it into the CI gate would make unrelated tickets red on backlog edits and couple the code gate to docs churn. | **Compensating control (kept a PR-invoked docs tool, not a `make check` step):** `docs/build/tools/check_backlog.py` (stdlib) parses the three source universes and asserts each id appears in exactly one `sources` cell, that enums are valid, and that no source is double-owned — printing `risk deferred rows: N/N`, `ADR revisit triggers: M/M`, `LD rows: 90/90`, `duplicate sources: 0`. It is run in the P20.1 PR (and by any later ticket that sets `status=closed` on a `BL-` id) and is named in the ticket's Definition of Done, so drift is caught at review time. The count of `BL-` cross-ref suffixes in `docs/risk_register.md` equals the distinct RISK ids in `sources` (100), a second deterministic cross-check a reviewer can run in one line. |

## Phase 20 — Spec reconciliation (P20.2)

Per §53 / SIG-ENG-031, P20.2's risk-register entry. P20.2 applies the eight ticked
HG-13 amendments (A1–A8) at `spec_src`, folds back three requirement ids
(SIG-UI-047, SIG-EVID-020, SIG-ENG-039), rebuilds Appendix F to repository ADR
numbering, and adds ADR-062. No package code or schema changed (only the new stdlib
`check_spec_src.py` and its test); `git diff --stat` is `docs/**` only.

### Deferred — spec-vs-code drift after the ticked amendments (SIG-ENG-005)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P20-02 → BL-051 | **Unbuilt work legitimised by the ticked amendments could drift from the spec.** The amendments accept deferrals whose *build* is still outstanding: the optional MapLibre island (SIG-UI-047 → P21.5), the Phase-21 persistence of contradiction/coverage/task objects (A5 → P21.2), and the web curation surface (A6 → P21.6). If those tickets never land, a reader of the spec could expect a surface the code does not yet provide (conforming today, but a divergence risk over time). Also folded-back ids and future ADRs must keep landing with their Appendix F row / `spec_src` paragraph in the same PR (SIG-ENG-039), or Appendix F drifts again. | **Compensating control:** `docs/build/tools/check_spec_src.py` (stdlib, PR-invoked) asserts byte-identical `BUILD.sh` reproduction, Appendix F ↔ `docs/adr/` equality, the `668 + 3` id count, and no duplicate/malformed/reserved ids; the residual build items are carried in `docs/build/BACKLOG.csv` (BL-051 and the existing BL-004/BL-007/BL-010 rows) with `landing` set to the P21.x ticket that builds each. `SPEC_RECONCILIATION_PLAN.md §(e)` names this residual explicitly. |

## Phase 20 — Integration & release (P20.3)

Per §53 / SIG-ENG-031, P20.3's risk-register entry. P20.3 makes integration a copy-paste operator
procedure (`docs/build/INTEGRATION_PLAN.md`) and bumps every member's version to `0.1.0`, while
**merging nothing, tagging nothing, and not touching `main` or any branch**. Only version fields,
lockfiles, and docs change. The three risks below are release/integration risks; each carries a
compensating control that is either a committed tool or an explicit step in the operator procedure.

### Integration & release risks and their compensating controls (SIG-ENG-005)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P20-03 | **`main` is unprotected.** `main` has no branch protection (`gh api …/branches/main/protection` → 404). A release cut onto an unprotected `main` can be force-pushed or have a non-green merge land, silently breaking the tagged tree; and any account with write access can push directly. | **Recommendation, recorded but NOT applied (an operator decision, not a ticket action):** `docs/build/INTEGRATION_PLAN.md §(d)` step 4 writes the exact `gh api -X PUT …/branches/main/protection` payload (require the `python` + `web` status checks strict, 1 review, block force-pushes and deletions). `docs/build/CI_STATUS.md` restates the recommended settings. Applying it needs repo-admin and is left to the operator so the append-only chain is never coupled to a protection change. |
| RISK-P20-04 | **The release could imply the graph is live.** A v0.1.0 release of a surveillance-infrastructure project invites the reader to assume it contains live, published data — but nothing is deployed and no source has been fetched (0 loadable, 87 UNDETERMINED). Overclaiming readiness violates the defining standard §3.1. | **Compensating control:** `docs/build/RELEASE_NOTES_v0.1.0.md` states, up front and explicitly, **what is NOT live** — nothing deployed, no live fetch, no jurisdiction published, the one `tests/e2e` `xfail` (`LD-V08` → P21.4), and the MAY-level/deferred surfaces — sourced from `OPERATIONAL_READINESS.md §(a)/(e)` and `SCOPING_NUMBERS §(ii)`. `CHANGELOG.md` carries the same "Known limitations". No synthetic certainty about readiness. |
| RISK-P20-05 | **The dry-run is stale by the time the operator merges.** `merge_dryrun.sh` is run now over #27–#53, but the operator merges after #55–#63 also exist; a conflict introduced by a later PR would be invisible in this ticket's table. | **Compensating control:** the dry-run is **re-runnable by design** (idempotent, read-only, generic `gh pr list --state open`) and `INTEGRATION_PLAN.md §(d)` step 0 makes `sh docs/build/tools/merge_dryrun.sh` the **first** operator action — it must exit 0 with `conflicts=[none]` for every open PR (and asserts the bottom-up tree equals the top PR) **before** any `gh pr merge` runs. The script exits non-zero on any conflict, so the procedure halts rather than merging blind. |

> **P20.4 annotation — CI-RED-01 (the `python`-job web-build red) is now FIXED.** `docs/build/CI_STATUS.md`
> flagged one pre-existing `python`-job failure and tracked it "with `RISK-P20-05`/backlog follow-up":
> `tests/e2e/test_composed_stack.py::test_s8_web_build_emits_dossier_route` shelled `npm --prefix web run
> build` unconditionally, but the `python` job installs no Node / `web/node_modules` (only the `web` job
> does), so `npm run build` returned `127` and the assertion failed — identically on #52/#53/#54, a latent
> harness gap introduced when `tests/e2e` landed (P19.3), not a P20.3 regression. **This annotation is
> append-only: the RISK-P20-05 row above (the stale-dry-run risk) is unchanged; CI-RED-01 is a distinct
> issue that CI_STATUS.md happened to file under the RISK-P20-05 follow-up.** P20.4 fixes it by gating the
> S8 `web_build` fixture on a usable web-build environment (`shutil.which("npm") is None` or missing
> `web/node_modules` → `pytest.skip(...)`), mirroring the module's existing Docker `_require_or_skip`
> pattern. Result: the `python` job **skips S8 cleanly** (0 failed) with no loss of coverage — the web
> build is still fully exercised by the **`web` job** (`npm run build`) and locally, where S8 runs
> unchanged and ends in the `LD-V08` xfail. No S8 assertion was loosened; `ci.yml`'s job structure is
> unchanged (adding Node to the `python` job was explicitly *not* the chosen fix). Verified node-present
> (`make check` = 2418 passed / 1 xfailed, S8 → `LD-V08` xfail) and node-absent (S8 skipped, 0 failed).
> Landed by `devin/p20-4-fix-ci-e2e-webbuild` (P20.4).

## Phase 21 — Operationalization (P21.1)

Per §53 / SIG-ENG-031, P21.1's risk-register entry. P21.1 turns "0 of N loadable" into a reviewable,
one-line-per-source decision: the 6 OKC critical-path rows are registered (115 total), a machine-checked
flip rule requires review metadata, 27 rights-review packets + the 19-project Stage-0 outreach record give
a human what they need to unblock ingestion **without touching code**. The gate is **skipped this run**
(HG-03/HG-04 = SKIP): nothing is flipped (`loadable now: 0`, `flip-ready: 18`) and no outreach is recorded.

### Rights-review / registry-completion risks and their compensating controls (SIG-ENG-005)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P21-01 | **Packets quote terms that may change.** A rights-review packet quotes a source's terms/robots text verbatim, but published terms and licences change over time; a packet that silently ages could carry a stale quote into a future flip decision, and a reviewer might act on terms that no longer hold (defining standard §3.1 — no synthetic certainty about rights). | **Compensating control:** every packet's verbatim quote carries an explicit `retrieval_date` (the date the agent actually fetched the terms page — reading a terms page is permitted research, not ingestion), separated from the reviewer's judgement (the Decision line). The registry row carries `rights.retrieval_date` and, once reviewed, `last_verified`; the flip rule (`connectors.review.review_metadata_violations`) refuses a flip whose `last_verified` is absent. Where a terms page could not be fetched this pass, the packet says so honestly and records the `terms_url` for the reviewer rather than inventing text. Packets are regenerable and the index (`RIGHTS_REVIEW_INDEX.md`) is reproduced from `sig-connectors validate`. |
| RISK-P21-02 | **A recorded reviewer role could be mistaken for a legal opinion.** The registry records `rights_reviewed_by` (a reviewer *role*) on a flip; a reader could read that as counsel sign-off on the licence — but a per-source rights review is not a legal opinion, and the ODbL §4.4(b)/sui-generis and AGPL-linking questions remain open counsel items (HG-02, RISK-P0-01..04, SIG-INGEST-048b). | **Compensating control:** `rights_reviewed_by` is a **role string, never a personal name** (Part VIII §0.7); every packet carries an explicit **counsel-needed flag** (YES/NO/PARTIAL, SIG-LIC-009) and states that it asserts no legal conclusion. ADR-063 records that the reviewer metadata is provenance-of-flip, not counsel disposition; the OSM/ODbL-derived and AGPL compartments stay export/link-only until HG-02 counsel review, independently of any `ingestion_permitted` flip. `usaspending` is left `UNDETERMINED` (public-domain facts laid out, SPDX candidate `CC0-1.0`) precisely so this ticket makes no rights judgement. |

## Phase 21 — Operationalization (P21.2)

Per §53 / SIG-ENG-031, P21.2's risk-register entry. P21.2 was **decision-gated** on the capstone
verdict: with amendment **A5** ticked (HG-13) and the compute-on-read family (ADR-037/038/039/054)
on the operator-signed ACCEPTED list (HG-14, `docs/build/CAPSTONE_CLOSURE.md` §(b)), the ticket
**shrank** to its alignment-test + ADR-note deliverables — the annotation layer stays a compute-on-read
computation layer and is **not** persisted (`BL-004`/`BL-005`/`BL-027` closed as accepted). The new
guard `tests/db/test_annotation_alignment.py` introspects the live `contradiction`/`coverage_record`/
`research_task`/`inference.derived_fact` schema against the value objects and holds their shapes in step
(0 mismatches) so a future persistence ticket is a purely additive change.

### Deferred-persistence risks and their compensating controls (SIG-ENG-005)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P21-03 | **Annotation-layer history tables grow unbounded once persisted.** When the annotation layer is eventually persisted (deferred; `BL-004`), the append-only temporal model (state changes as new rows with `valid_from`/`recorded_at`) means `contradiction`/`coverage_record`/`research_task`/`inference.derived_fact` history accumulates without bound; with no partitioning or retention design, table-wide maintenance and scan cost could exceed budget at national scale (the same physical concern ADR-022 defers for `claim`). | **Compensating control:** persistence is not built yet, so no unbounded table exists today (compute-on-read, A5/HG-14). Append-only is preserved by design (never `UPDATE`/`DELETE`); partitioning/retention is explicitly **deferred** under **ADR-022**'s revisit trigger (`claim` growth or query-latency budget breach designs a partition-compatible FK strategy + sqitch migration), and the same trigger governs the annotation tables. Tracked as backlog **BL-003** (claim partitioning) and **BL-004** (persist annotation layer). `tests/db/test_annotation_alignment.py` guarantees the value-object ↔ table shapes stay aligned, so a partition-compatible or retention-aware migration lands additively (new nullable column, never a drop) rather than as a redesign. |

## Phase 21 — Operationalization (P21.3)

Per §53 / SIG-ENG-031, P21.3's risk-register entries. P21.3 wires the **real** connector
network path (`HttpxTransport`) and the OCFL-backed `CaptureStore`, and owns the gated
`sig-connectors run --mode live|replay|shadow` CLI and the fetch-record format (ADR-065).
This run is **HG-03 skip / HG-09 no tokens**: no source is flipped and no live fetch runs;
every deliverable is exercised over a local HTTP stub (`httpx.MockTransport`) and fixture
`shadow`/`replay` (diff = 0). A live fetch is structurally impossible until a source's
review-status is fully green (`run --mode live` refuses with exit 3 — the LD-X08 guard).

### Live-fetch and secret-handling risks and their compensating controls (SIG-ENG-005)

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P21-04 | **Live fetch cadence could exceed a source's etiquette.** Once a source is green (HG-03) and real fetches begin, an over-eager cadence — polling faster than a small civic host or an Overpass public instance tolerates, or retrying a rejected query unchanged — could burden the source, trip its rate limiter, or get SIG blocked, and would violate crawler conduct (§26 Rule 3, SIG-INGEST-011/037) and Overpass etiquette (SIG-INGEST-045d/045h). | **Compensating control:** the shared `PoliteFetcher` enforces a per-host minimum interval (crawl-delay from robots or a conservative default) *before* every request, and `HttpxTransport` adds **retry-with-backoff on 429/503/504 honouring `Retry-After`** — a transient rate-limit/gateway-timeout is backed off and retried, never treated as a challenge and never hammered (Overpass 429 = back off, SIG-INGEST-045h). A 401/403 challenge is never retried (SIG-INGEST-013). Cadence is a first-class field: every fetch record (`docs/build/live_runs/`) carries the `rate_limit_events` (each back-off, its wait, and the attempt number) and robots decisions, so a reviewer can audit that the run stayed polite. No live fetch runs this ticket (HG-03 pending), so no source is contacted; the backoff/etiquette path is proven over the stub (a 429 with `Retry-After: 2` yields exactly one retry after ≥ 2 s). |
| RISK-P21-05 | **A credential could leak into the repository.** The authenticated sources (MuckRock, data.gov, a self-hosted Overpass/CivicClerk endpoint) need a token/key; hardcoding one in a file — or committing a `.env` — would leak a secret into git history irrecoverably (HG-09). | **Compensating control:** secrets are **environment-only** — `SIG_MUCKROCK_TOKEN`, `SIG_DATA_GOV_KEY`, `SIG_OVERPASS_ENDPOINT`, `SIG_CIVICCLERK_BASE` are read from the process environment and never written to a file; with none set (this run), live runs are skipped/refused and the stub tests cover the transport. `.env*` is gitignored, and `tests/connectors/test_secrets.py` fails the build if any `SIG_*_TOKEN`/`api_key` literal appears in a `.py`/`.toml` file (the sanctioned pattern is an `os.environ`/`getenv` read). The fetch record contains provenance only — no content and no credential; the credential rides the shared egress seam as a per-request `Authorization` header (authentication, not circumvention — Rule 4 / SIG-INGEST-037). |

## Phase 21 — Operationalization (P21.4)

| id | Risk | Compensating control |
|---|---|---|
| RISK-P21-06 | **Live pages depend on export freshness.** The static site is built FROM the `sig-exports build` output (`SIG_DATA_SOURCE=export`, ADR-066), so a stale export silently yields a stale page — a reader could act on an out-of-date device count or contradiction with no signal that the data aged, breaching the defining standard (§3.1, no synthetic certainty about currency). | **Compensating control:** every page carries the resolved as-of pair and the ruleset version (the SIG-UI as-of banner / belief-pinned permalink, SIG-UI-035), and the dossier bundle records `asOf`/`rulesetVersion`; the build is a pure function of the export bytes so a page can never claim more currency than the export. The export directory is dated and append-only (P1–P3), and `web/src/lib/data.ts` fails LOUD (never falls back to fixtures) if an export artifact is missing, so an absent/partial export is a build failure, not a silently-stale page. `docs/build/tools/run_okc.sh` rebuilds the export immediately before the web build so the two cannot drift within a run. |
| RISK-P21-07 | **Staging exposes real-shaped data before the go-public gates.** Standing the stack up on staging (`sig-ops up`) serves the dossier/API before HG-01 (legal home) and HG-11 (operating governance) are ticked; if staging were world-reachable, real-shaped surveillance data would be published ahead of the governance that must precede publication (RISK-P0-05, §0.7). | **Compensating control:** the default staging is **local** (HG-12: `docker compose` + `uvicorn` + a local static server bound to `127.0.0.1`), access-restricted by construction — nothing is world-reachable without an explicit operator cut-over. Go-public is a **separate human decision** that is impossible until HG-01 and HG-11 are ticked and `docs/build/PUBLICATION_CHECKLIST.md` is green (deliverable 7 is NOT done this ticket — the ticket ends at staging, RETURN PASS). The OSM-derived layer stays in its separate ODbL compartment with attribution + share-alike (HG-02 disposition recorded). Publication policy (`policy.publication`/`applyPublicationPolicy`) runs over the export before build and the officer-naming gate is applied, so even the staged bytes are publication-filtered. |

## Phase 21 — Operationalization (P21.5)

Per §53 / SIG-ENG-031, P21.5's risk-register entries. P21.5 adds the infrastructure around the
published graph — a citable Zenodo deposit, an object store/CDN with an egress alarm, real rendered
vector tiles, mirrors + Software Heritage, and a tested degraded-but-alive mode (ADR-067). This run
is **HG-07 (no accounts) + HG-12 (zero-cost) + A1 ticked**: every credentialed integration runs in
dry-run / sandbox-stub and is recorded `gate pending: HG-07`; the free paths (`.torrent`, tiles,
degraded mode, keepalive) are done for real; the MapLibre island is **not** built (A1 ticked).

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P21-08 | **A sandbox DOI could be cited as if it were the production DOI.** The Zenodo *sandbox* mints throwaway `10.5072/zenodo.*` test DOIs on a free account; the production instance mints real `10.5281/zenodo.*` DOIs. If a sandbox (or dry-run) identifier leaked into a citation, `CITATION.cff`, or a paper as the canonical concept DOI, readers would cite an identifier that resolves to nothing durable — a false claim of citability (§3.1). | **Compensating control:** the deposit ledger `docs/build/DEPOSITS.md` is append-only and its **`environment` column is binding** — every row is marked `dry-run` / `sandbox` / `production`, and the header states that a `10.5072/…` sandbox DOI is **not** citable and **not** the production concept DOI. The prefixes are distinct constants (`ZENODO_SANDBOX_PREFIX`/`ZENODO_PRODUCTION_PREFIX`) asserted in tests. `sig-exports deposit` without `--sandbox` never mints a sandbox id, and the first **production** deposit is a deliberate one-command operator action that appends its own row. `CITATION.cff` carries the concept DOI only once a production deposit exists (HG-07 pending until then). |
| RISK-P21-09 | **The egress budget alarm is untested against a real bill.** Egress pricing is the existential cost of a bulk-data project (RISK-P0-07); ADR-015's "revisit if egress climbs" trigger had no instrument, and with no object-store account (HG-07) the alarm threshold in `ops/config.toml` cannot be validated against real monthly usage — an under- or over-set threshold could miss a runaway bill or cry wolf. | **Compensating control:** the alarm is a **pure function of (usage, budget)** — `ops.egress.build_report` — tested at the ok / warn / alarm / gate-pending boundaries, so the *logic* is proven even without a live store. With no usage API reachable, `sig-ops egress-report` reports `gate pending: HG-07` and states the documented threshold rather than fabricating a measurement (§3.1). The store is chosen **zero-egress** (Cloudflare R2, ADR-067) so the failure mode is structurally bounded — a metered provider fails the build (SIG-EXPORT-008) — and content-hash keys + an immutable `Cache-Control` give the cheapest possible egress profile. The threshold + revisit trigger are documented for the operator to tune against the first real invoice. |

## Phase 21 — Operationalization (P21.6)

Per §53 / SIG-ENG-031, P21.6's risk-register entries. P21.6 adds the authenticated
curation surface — the ER review queue, contradiction/task dispositions, L0 contributor
entry, and revert — as a web surface plus its API (ADR-068). Part VIII §0.7 is binding:
the curation service is authenticated and is never on the public API process; every
write is append-only with a human actor id; machine suggestions are labelled and never
auto-apply. P21.2 shipped the shrunk case, so no new persistence was built — ER
decisions use the JSONL curation log / `PgReviewQueue`.`review_decision`, and
contradiction/task dispositions are compute-on-read.

| id | Risk (what breaks the acceptance gate if unhandled) | Compensating control |
|---|---|---|
| RISK-P21-10 | **The curation endpoint could be exposed publicly.** The curation API is a *write* surface bound to the P16.1 contributor tiers; if it were mounted on the public read-API process, or bound to a world-reachable interface, an unauthenticated or wrong-tier caller could reach a write path (a decision, a disposition, a revert) — a Part VIII §0.7 breach (the curation service must never be public) and a §3.1 breach (a write with no attributable human actor). | **Compensating control:** the curation surface is a **separate FastAPI app** (`create_curation_app`), a **separate process** (`sig-api serve-curation`, which exits 3 unless `SIG_CURATION_ENABLED=1`), on a **separate port bound to loopback** (`127.0.0.1:8001`; the `docker-compose` `api-curation` service publishes only to `127.0.0.1`, in the `curation` profile). It is **disabled by default and structurally absent**: with the flag unset the app carries **no** `/v1/curation/*` routes at all (404), not merely guarded — `tests/api/test_curation.py::test_routes_absent_when_disabled` and `::test_public_read_api_never_carries_curation_routes` prove it. When enabled, every route requires a bearer token mapping to a pseudonymous contributor tier (no/unknown token → 401) and asserts the tier holds the route's write scope (insufficient → 403). `sig-ops status` reports the curation process on its own line, marked *authenticated, non-public*. |
| RISK-P21-11 | **Reviewer fatigue could bury the high-impact proposals.** The review queue mixes tier-4/5 ER matches and model-assisted extractions; if the surface presented them in an arbitrary or purely chronological order, a reviewer working top-down could spend attention on low-weight/low-impact items while a decisive high-weight merge waits, degrading the quality and throughput of adjudication (the human-judgement bottleneck of §14.6). | **Compensating control:** both the API (`/v1/curation/review-queue`) and the web queue order proposals by **impact** — highest \|match weight\| first, then by id (deterministic) — so the most decisive proposals surface first; `tests/api/test_curation.py::test_reviewer_can_list_queue_ordered_by_impact`, `web/tests/unit/curation.test.ts`, and the e2e queue-order test pin the ordering. Decided items drop out of *pending* (compute-on-read) so the queue shrinks as work is done, and the queue can be filtered by tier. A machine suggestion is a labelled hint with its confidence class, not extra items to triage. Deeper prioritisation (impact-weighted by downstream fan-out) is a future refinement, not required for the gate. |
