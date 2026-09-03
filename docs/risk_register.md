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
