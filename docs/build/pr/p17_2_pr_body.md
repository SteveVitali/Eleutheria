## Summary
Implements **P17.2** — extends the populated Stage-5 graph to **facial recognition**, **cell-site simulators**, and **mobile-device forensics**, plus the **federal-authorization** case, with **no schema change**. This continues P17.1's standing proof of §5.2: the schema frozen in Phase 2/4 absorbs a further technology span with no change (SIG-CHART-027/028).

Like P17.1, the constructs are populated as **test-only instance graphs** over the *committed* generated Pydantic model and the *committed* `capability.yaml` / `technology.yaml` — no LinkML source, generated artifact, or wire contract is touched. `verify-gen` is byte-clean, so §5.2 holds and no Phase-1 defect was required. The no-schema-change test is the deterministic Phase-1-defect detector.

Spec: `docs/tickets/P17.2__broader-fr-css-forensics.md`. Base: `devin/p17-1-broader-federation-rtcc` (stacked PR chain).

## What changed
- **`tests/ontology/generalization/test_stage5_forensics.py`** (new, 9 tests) — populates FR, CSS, forensics, and the federal-authorization case.
- **`docs/traceability.md`** — P17.2 requirement → test matrix.
- **`docs/risk_register.md`** — Phase 17 / P17.2 entries (Phase-1-defect path, modelling observations, deferrals).

## Design decisions
- **FR "searches_against a reference gallery"** (§11.10, SIG-ONTO-031): the illustrative predicates `can_query`/`searches_against` are prose, not members of the closed §12 catalog (SIG-ONTO-041). Realised as `federates_search_to` — the query moves, the gallery corpus stays put (`data_comes_to_rest=False`). Recorded as RISK-P17-06.
- **`authorizes` carried on a `StructuralEdge`** ("no data moves"); the catalog does not bind it to a subclass. Recorded as RISK-P17-07.
- **Native validity interval**: stored as EDTF on both the `LegalInstrument` (`effective_from`/`effective_to`) and the `authorizes` edge (`valid_from`/`valid_to`), and proven a genuine `EdtfInterval` with two distinct bounds via `db.edtf.parse_edtf` / `derive_envelope` — never coerced to a point.
- **No `Person` rows** are minted for observed individuals (§11.3, §43.4).
- **No ADR** — an ADR records a deviation, and there is none (no schema change).

## Verification
- `make check` fully green: `lint` + `format-check` + `typecheck` (181 source files) + `pytest` (**2261 passed**) + `verify-gen` (**byte-clean** — ontology + `pylock.toml` unchanged).
- New suite: `test_stage5_forensics.py` — 9 passed.

## Acceptance criteria → evidence

| AC (spec) | Status | Evidence |
|---|---|---|
| FR/CSS/forensics **populated with no schema change**; generalization suite still passes; any required change recorded as a Phase-1 defect (SIG-CHART-027/028) | met | `test_stage5_forensics_required_no_schema_change`; `verify-gen` byte-clean; full suite 2261 passed |
| **Non-camera capabilities with no physical asset** represented without a camera abstraction — CSS/forensics Deployment with no product/vendor/asset; FR resolves to a reference DataSystem; none forced into a camera type (SIG-ONTO-026/027/031) | met | `test_css_and_forensics_are_deployments_with_no_product_vendor_or_asset`; `test_face_recognition_is_a_capability_searching_a_reference_datasystem`; `test_face_recognition_has_no_locally_owned_sensor`; `test_no_construct_is_forced_into_a_camera_abstraction` |
| **Federal authorization datasets populate `authorization_state` with native validity intervals** — carries its own EDTF interval, not a fabricated point (§13.4 track 4) | met | `test_federal_authorization_populates_track4_authorization_state`; `test_authorization_carries_native_validity_interval_not_a_point` |
| **Phase-gate (§51.3):** CI green incl. data-quality; new requirements have automated tests (SIG-ENG-004); ADRs for any deviation; traceability + risk register updated | met | `make check` green; `docs/traceability.md`, `docs/risk_register.md` (Phase 17 — P17.2); no ADR (no deviation) |

### Requirement IDs stamped
SIG-CHART-027, SIG-CHART-028, SIG-ONTO-026, SIG-ONTO-023, SIG-ONTO-031; §11.6 Capability / §11.7 Deployment / §11.10 DataSystem / §11.14 LegalInstrument; §13.1 (`biometric-id`, `comms-intercept`, `device-forensics`); §13.4 `authorization_state` (track 4). Each is covered by an automated test.

Generated with [Devin](https://devin.ai)
