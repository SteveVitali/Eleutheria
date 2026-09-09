## Summary
Implements ticket **P00.2 — Executable policy and the decision record**. Turns SIG's executable governing rules into a tested `policy/` package and writes the architecture decision record. Also resolves the repo-wide licence posture that P00.1 left as a placeholder (P00.2 owns this): first-party code becomes **Apache-2.0** (SIG-LIC-005), replacing the `LicenseRef-SIG-Undetermined` LICENSE file and every SPDX header.

Base branch is `p00-1` (stacked PR chain).

## What changed
- **`policy/` package** (data tables under `policy/data/`, *data not code*):
  - `crawler` — eight Crawler Conduct rules, robots.txt + content-signal honouring (unretrievable ⇒ not granted), no-circumvention as a legal posture (§26, SIG-INGEST-036/037).
  - `rights` + `licensing` — rights-record shape (SIG-LIC-001/003); UNDETERMINED fails the export gate closed (SIG-LIC-004); **N-compartment export model keyed on rights** with a per-compartment compatibility gate — a deliberate cross-compartment merge fails the build (SIG-LIC-004a/010); `ai_training` gate enforced at the data layer (SIG-LIC-004b/004c); per-row downstream obligations (SIG-LIC-011).
  - `sensitivity` — C1–C5 coordinate matrix + tier transforms, residential-parcel demotion, deterministic (non-jitter) offset (§43.3/§19.4, SIG-PUB-004/005/013, SIG-GEO-009).
  - `officer` — five-prong officer-naming test + two-reviewer concurrence (SIG-PUB-007/008/009/010).
  - `publication` — categorical exclusions, de-pseudonymisation prohibition, jurisdiction-conditional publication (SIG-PUB-002/003a/017).
  - `threat_model` — versioned artifact; every adversary row maps to a requirement id (§44, SIG-SEC-001).
- **Decision record**: `docs/adr/ADR-001..012` (§15.5) + stack ADRs 013..020 (uv, Astro, AWS S3+CloudFront reconciling the §38.5 egress constraint, Dagster, FastAPI, MapLibre, pytest+Hypothesis, GitHub Actions). Each names a **revisit trigger** (SIG-STORE-006/007).
- **Phase-gate artifacts**: `docs/traceability.md`, `docs/risk_register.md`.
- **Licence posture**: rewrote `LICENSE`; `LicenseRef-SIG-Undetermined` → `Apache-2.0` across all source headers; `web/package.json` license; header test updated.

## Design decisions
- **Data, not code**: compartments, sensitivity matrix, threat model, exclusions, crawler rules, and jurisdiction policy are TOML under `policy/data/`, read via `importlib.resources` (stdlib `tomllib`, no new runtime deps). Adding a source under a new share-alike licence is a data row.
- **Compatibility as a data relation**: each licence declares `relicensable_to`; share-alike licences are self-only, so ODbL and CC-BY-SA can't merge and neither folds into CC-BY-4.0. CC0 folds anywhere. Silently-travelling share-alike (SIG-LIC-009a) is modelled via `upstream_license`, which forces the stricter regime.
- **Officer gate is deterministic; the concurrence is agentic** — the human judgement is recorded in the risk register as an SIG-ENG-005 compensating-control item.
- Added Hypothesis (dev) to make ADR-019 real: a property test asserts the SIG-GEO-009 deterministic/bounded-offset invariant and truncation idempotence.

## Test plan
- [x] `make check` green (lint + format + mypy + pytest + generated-artifact gate)
- [x] 210 tests pass (was 104; +106 for policy + ADRs + property)
- [x] Deliberate cross-compartment merge raises `LicenseIncompatibilityError`
- [x] Officer gate rejects on any missing prong / <2 independent written concurring reviewers
- [x] `ai-train=no` blocked at the data layer; UNDETERMINED fails export closed
- [x] Every ADR has a revisit trigger; threat model validates
- [x] `uv run python -m policy validate` self-checks OK

Implements spec: `docs/tickets/P00.2__policy-as-code.md` (canonical §§26, 42, 43, 44, 15.5, 47, 19.4, 51.3).

Generated with [Devin](https://devin.ai)

