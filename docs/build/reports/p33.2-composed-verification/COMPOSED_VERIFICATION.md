# Composed Round-10 verification — P33.2

* **schema:** `sig.composed-verification/1`
* **code revision:** `ad0bd843b140cf006c7db06ae1bb8f7cbc049ef6`
* **dsn:** `localhost:55433/sig`
* **generated_at:** 2026-09-28T06:13:07Z
* **live_verification:** false (offline fixture + local Docker only)
* **intake receiver operational (ops/config.toml):** `False` — the honest production state
* **verdict:** **PASS**

## Inputs

* fixture: `docs/build/fixtures/p33-2_composed_fixture.json` (sha256 `eb092827da6b4572a0c916b93df3c04ceb3f61a3dac040fa7b4bedb9531c0346`)
* connector fixture: `tests/connectors/fixtures/atlas/adoption_feed.csv` (sha256 `8c5c7965e23424d841da1745ab952d8ceefe1514fc1ac9777eaf3163ccddd9fd`)

## Legs

### A.capture_to_claim

  - [x] **connector_pipeline_asserted** — atlas over committed fixture: claim_count=7 inserted=5 through PgClaimSink (asserted=True, captures=1)
  - [x] **capture_bound_claims** — 5 claim_evidence rows bind the 5 inserted claims (7 records, 2 in-batch duplicates) to the pipeline capture digest bcnaavp3rg6zw2hn2sie7uw6… — classification {'document_only': 5} (atlas rows carry no typed locator → the binding is honestly document_only, SIG-TRUST-002)
  - [x] **fixture_claims_asserted** — 22/22 fixture claims inserted (duplicates=0)
  - [x] **fixture_locator_bindings** — 22/22 fixture bindings are actual_capture with a typed row locator into the fixture document
  - [x] **resighting_append_only** — re-assert against a later capture: inserted=0 (+0), claim_evidence links=44 (2×22 — every claim now carries two establishing occurrences, append-only)

### B.temporal_role_resolution

  - [x] **occurrence_selection_parity** — latest eligible occurrence for the restated count: pure model 01a0e6a5-446d-7b74-a526-076904c75f25 == eligible_occurrence 01a0e6a5-446d-7b74-a526-076904c75f25 (the re-sighting capture retrieved 2026-09-27 wins over the first 2026-09-21)
  - [x] **belief_time_parity** — belief as-of 2026-09-28 06:13:05.752077+00:00: both twins select the FIRST capture 01a0e6a5-43b9-7fdc-9669-dc15a43a3de9 (the later binding is not yet known — sys/belief time respected)
  - [x] **observation_bases** — dated count → basis=claim (2026-06-01); undated camera_presence → basis=capture_retrieved_at_latest (2026-09-27) — no fabricated dates
  - [x] **role_separation** — camera_registry_publisher → PUBLISHER (object_entity NULL — provenance mints nothing); camera_operator → 01a0e6a5…, vendor → 01a0e6a5… (distinct partner orgs, SIG-TRUST-003)

### C.eligible_release

  - [x] **withhold_recorded** — entity-level WITHHOLD disposition 77557e96-7ce2-4678-8f78-ea51ad283747… recorded on 01a0e6a5… (fx-dep-withheld)
  - [x] **undetermined_decision_recorded** — rights_decision lifts 8 UNDETERMINED claims to redistributable (licence still UNDETERMINED) — decision(s): ['01a0e6a5']
  - [x] **materialization_idempotent** — rematerialize pass-1 +35, rerun +0 (shared materializers, stable +0)
  - [x] **eligible_subjects_released** — fx-dep-released → sig_graph sites (1 rows); fx-dep-odbl → osm_physical sites (1 rows) — licence compartments preserved
  - [x] **licence_gate_exclusion** — withheld entity 01a0e6a5… absent; UNDETERMINED-rights subject 01a0e6a5… absent and its refused slice named in exclusions.json ([{'surface': 'sites', 'source_id': 'composed-fixture', 'rights_id': '01a0e6a5-4571-7267-a160-3f2f8564ebc1', 'spdx': 'UNDETERMINED', 'reason': 'UNDETERMINED', 'rows': 1}]) — loud exclusion, never silent drop
  - [x] **release_activated** — validate_release state=complete (23 artifacts); activated p-8414a4165a786609492258…; latest.json points at it

### D.search_record

  - [x] **search_index_finds_record** — FTS5 index (contract-pinned) returns the released record sig_graph:deployment:01a0e6a5-43e4-7789-9bd8-24701a5a7c37 for q='P33.2 Composed Fixture' (1 hits)
  - [x] **record_to_capture_trace** — published record r/p-8414a4165a7866…/entity/deployment/01a0e6a5… → 4 claim anchors → claim_evidence → capture digest bcnaeiqy7lvxjikwbqr3dtv7… == the fixture document multihash (record→claim→evidence→input bytes)
  - [x] **serving_barrier** — route_access(r/p-8414a4165a7866094922585e022be28c755f57da4a1b…) permitted; current selector resolves p-8414a4165a786609492258…

### E.correction

  - [x] **intake_journey** — submit_durable=ok; survives_restart=ok; moderation_queue=ok; reviewed=ok; applied_canonical=ok; exactly_once=ok; published_linkage=ok; distinct_states=ok; resolved_state=ok; receiver_no_fact_write=ok
  - [x] **append_only_correction** — §16.6 close+revises: corrected claim 01a0e6a5… (value_text='225', correction_reason=acceptance_journey) revises 01a0e6a5…; prior sys_period closed=True — no UPDATE anywhere

## Release identity

* publication_id: `p-8414a4165a7866094922585e022be28c755f57da4a1bcb801071b0863e615ffe`
* manifest_sha256: `445f885fab72f66cb29ece3e0cc1f7ad371474faa9abebf76ba34f7f58202f65`
* compartments: `{"osm_physical": {"license": "ODbL-1.0", "record_count": 1, "search_index_sha256": "88e83c05796f5896d107816afb0d731cb1723e937ec190f6c93d33f53a7e9995"}, "sig_graph": {"license": "CC-BY-4.0", "record_count": 1, "search_index_sha256": "c527580677ec2461741dfb31992fcf858159cda2bb67b1d49a7a245daeb480cf"}}`

Generated by `sig-ops composed-verify` / `ops.composed_verify.run_composed_verification`.
