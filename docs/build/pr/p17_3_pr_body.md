## Summary

Continues P17.1/P17.2's standing proof of **§5.2** (SIG-CHART-027/028): the schema frozen in Phase 2/4 absorbs a further Stage-5 technology span with **no change**. This ticket *populates* **gunshot detection**, **drones**, and **commercial location data** as instance graphs over the committed generated Pydantic model and the §13.1/§13.2 vocabularies, extending the generalization conformance suite.

The load-bearing constraint is **SIG-ONTO-027**: acoustic gunshot sensors and drones are **non-camera physical sensors** and are represented **without a camera abstraction**.

No LinkML source, generated artifact, or wire contract changed (the ontology is owned by P01.1). `verify-gen` is byte-clean, so no Phase-1 defect was required — the no-schema-change test is the deterministic Phase-1-defect detector.

## What changed

- `tests/ontology/generalization/test_stage5_acoustic_drone_location.py` (new) — 7 tests populating the three constructs + the no-schema-change proof.
- `docs/traceability.md` — P17.3 traceability section (requirement -> where -> test).
- `docs/risk_register.md` — P17.3 risk-register section (RISK-P17-10 through 14).

## Design decisions

- **Gunshot detection** -> an acoustic `PhysicalAsset` with `asset_type=gunshot-detection-fixed` (domain `acoustic`; already in OSM as `gunshot_detector`, R1-F1.3), `mobility=fixed`, never a camera. A rooftop sensor's coordinate sensitivity is carried at the **role** level via two separate `RoleAssignment`s — `operator` (the PD) and `host` (the building owner) — so §43.3 protects the **host**, not the operator (§12.4 item 6).
- **Drones / UAS** -> airborne `PhysicalAsset`s (`mobility=airborne`, `asset_type` under `robotics-aerial`: `uas-general`, `drone-as-first-responder`), not a camera abstraction.
- **Commercial location data** -> a `data-acquisition` `Deployment` (`technology=[location-data-subscription]`, no product/vendor/`PhysicalAsset`) plus a reference `DataSystem`, realised in the closed §12 catalog as `subscribes_to` (consistent with P17.1's broker chain) — a deployment with no roadside device. No `Person` row is minted for the corpus's individuals (§11.3, §43.4).
- **No ADR** — an ADR records a deviation; there is none (no schema change).

## Verification

- `make check` — **green**: `ruff check`/`ruff format --check` clean; `mypy` 181 files, no issues; `pytest` **2269 passed**; `verify-gen` byte-clean (`pylock.toml` + `ontology/generated` unchanged).
- New suite `test_stage5_acoustic_drone_location.py`: 7 passed.
- No runtime/live surface (test-only instance graphs over the committed model), same as P17.1/P17.2.

## Requirement IDs stamped

`SIG-CHART-027`, `SIG-CHART-028`, `SIG-ONTO-027`, `SIG-ONTO-026`, `SIG-ONTO-031` — plus the §11/§13.1 entity/vocab ids realised: `PhysicalAsset` (§11.8, `asset_type`/`mobility`), `Deployment` (§11.7), `DataSystem` (§11.10), `Capability` (§13.2 `alert.gunshot.own`, `dispatch.uas.autonomous`, `search.location_history.commercial`), technologies (§13.1 `acoustic`/`gunshot-detection`, `robotics-aerial`/`uas`, `data-acquisition`/`location-data`), `RoleAssignment` (§12.4 `operator`/`host`), `AccessRelationship` `subscribes_to` (§12.5).

## Acceptance criteria -> evidence

| AC | Status | Evidence |
|---|---|---|
| AC1 — populated with **no schema change**; conformance suite passes; any required change recorded as a Phase-1 defect (SIG-CHART-027/028) | met | `test_stage5_acoustic_drone_location_required_no_schema_change`; `make check` `verify-gen` byte-clean; `docs/risk_register.md` RISK-P17-10 |
| AC2 — non-camera physical sensors without a camera abstraction; commercial subscription = deployment with no owned sensor (SIG-ONTO-026/027) | met | `test_gunshot_detection_is_an_acoustic_non_camera_physical_asset`, `test_drones_are_airborne_non_camera_physical_assets`, `test_commercial_location_is_a_subscription_with_no_owned_sensor`, `test_no_sensor_is_forced_into_a_camera_abstraction` |
| AC3 — phase-gate §51.3: CI green incl. data-quality; new reqs have tests (SIG-ENG-004); ADRs for deviations (none); traceability + risk register updated | met | `make check` green; `docs/traceability.md` / `docs/risk_register.md` (Phase 17 — P17.3) |
| §12.4 item 6 / §43.3 — rooftop sensor coordinate risk at role level protects the host | met | `test_gunshot_sensor_coordinate_risk_is_evaluated_at_the_host_role` |
| §11.3 / §43.4 — no Person rows for observed individuals | met | `test_no_person_rows_are_minted_for_observed_individuals` |

Implements `docs/tickets/P17.3__broader-acoustic-drone-loc.md`.

Generated with [Devin](https://devin.ai)
