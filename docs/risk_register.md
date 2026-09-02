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

### Ecosystem / operational

| id | Risk | Mitigation |
|---|---|---|
| RISK-P0-07 | Bulk-export egress cost becomes existential (§38.5) — "success is the failure mode" | ADR-015: CloudFront caching + torrent/IPFS offload + low-egress mirror; egress-budget alarm is the ADR's revisit trigger |
| RISK-P0-08 | An ecosystem project's unauthenticated audit dump enables the de-pseudonymisation join (§43.2a) | SIG never ingests per-search operator rows; operator ids hashed with a held-back salt; no operator-joinable surface (`policy.publication`) |
| RISK-P0-09 | Vendor/agency takedown pressure (already observed against a peer project) | Rigorous provenance; conservative crawler conduct (§26); corrections/takedown path owned by P00.3 |
