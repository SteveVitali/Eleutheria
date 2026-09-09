## Summary

Implements **P16.2 — Contribution back to the ecosystem** (`docs/tickets/P16.2__contribution-back.md`, spec §35 / §7 / §32.6 / §42.3a). Contribution back is built as pure, tested Python in the `tasks` package ahead of persistence (the established `tasks`/`policy.governance` pattern), plus a `policy.licensing` gate and a read-API attribution field. **Additive — no prior wire name, id, or schema contract changes.**

The design has one non-negotiable shape: **SIG proposes, a human decides.**

- **No direct automated OSM writes (SIG-CONTRIB-014).** `tasks.contribution.write_to_osm` exists only to raise, and an `AppliedEdit` cannot record SIG as the applier — the suggestion-not-write posture is structural.
- **Human-mediated suggestion workflow (SIG-CONTRIB-015/015a/015b).** A MapRoulette **cooperative** challenge (`cooperativeType=tags`) proposes a specific `TagChange`; a mapper applies it in their own account via `apply_by_mapper`. The MapRoulette field crosswalk, account holder, and located API docs are recorded.
- **The OSM compliance analysis is recorded as ADR-055** (the spec's Appendix-F "ADR-017"): the Automated-Edits-Code scope test, why the exceptions don't apply, why individual human review keeps SIG outside the Code, and the full proposal/decision path a genuine bulk edit would require (SIG-CONTRIB-016/016a/016b/016c).
- **The changeset hashtag `#sig_operator_attribution`** is required on every SIG-originated edit and wired to the **§7 leverage metric** via `LeverageLedger`, which counts *accepted* upstream changesets bearing the hashtag — a public, third-party-auditable signal (SIG-CONTRIB-016e).
- **The Organised Editing activity page** is published + registered and discloses org+contact, hashtag, goal, timeframe, every non-standard tool and data source with usage conditions, participating accounts, and metrics stated as **task outcomes, not contributor rankings** (SIG-CONTRIB-016d/016g; SIG-LIC-007a/b/c). Every required field is machine-checked from `data/organised_editing.toml`.
- **The contribution-path licence gate (SIG-CONTRIB-016f, §42.3a)** — `policy.licensing.assert_contribution_permitted` — blocks a source that is `UNDETERMINED`, forbids derivatives, or is not relicensable to OSM's ODbL-1.0, and is applied *before* a suggestion is rendered. Distinct from the §42.4 export gate.
- **Structural upstream attribution (SIG-CONTRIB-020).** The API `/claim` response now carries `attribution`; exports already stamp per-row `_rights`. Per-project correction channels (`PROJECT_CHANNELS`) use each project's own stated channel (SIG-CONTRIB-018).
- **Device-observation routing (SIG-CONTRIB-004)** landed in P16.1 and is re-cited as the §35-owned surface.

## What changed

- `tasks/src/tasks/contribution.py` (new) + `tasks/src/tasks/data/organised_editing.toml` (new); `tasks/__init__.py` docstring.
- `policy/src/policy/licensing.py`: `permits_osm_contribution` / `assert_contribution_permitted` / `ContributionGateClosed` / `OSM_CONTRIBUTION_TARGET`.
- `api/src/api/models.py` + `api/src/api/routes.py`: `ClaimResponse.attribution` wired in the `/claim` route.
- Docs: `docs/adr/ADR-055-*.md` (+ index), `docs/governance/organised-editing-activity.md` (+ index), `docs/traceability.md` (P16.2 section), `docs/risk_register.md` (P16.2 section).
- Tests: `tests/tasks/test_tasks_contribution.py` (new), plus additions to `tests/unit/test_policy_licensing.py`, `tests/api/test_api_coverage_license.py`, `tests/exports/test_compartments.py`.

## Design decisions

- **In-memory model ahead of persistence** (ADR-055), consistent with P16.1. A live MapRoulette client and a live OSM changeset feed into `LeverageLedger` are tracked downstream (risk register).
- **ADR numbering:** the repo numbers ADRs sequentially, so the spec's conceptual "ADR-017" is recorded as repo **ADR-055** (repo ADR-017 is FastAPI); the mapping is stated in the ADR.
- **Licence gate reuses the export `relicensable_to` relation** rather than a new compatibility model — a CC-BY-SA-4.0 (or plain CC-BY-4.0) source is correctly refused, matching SIG-LIC-007a.

## Verification

`make check` green — **2238 passed**, lint/format/typecheck clean, `verify-gen` byte-clean. `mypy -p tasks -p policy -p api -p exports`: no issues.

### Acceptance criteria → evidence

| AC (spec) | Status | Evidence |
|---|---|---|
| No unattended OSM write; suggestion requires human application (014/015) | met | `tasks.contribution.write_to_osm`/`AppliedEdit`; `test_no_automated_osm_write_path_exists`, `test_sig_can_never_be_the_account_that_applies_an_edit`, `test_suggestion_becomes_an_edit_only_when_a_human_mapper_applies_it` |
| Automated-edits compliance ADR written, scope conclusion recorded (016) | met (agentic) | `docs/adr/ADR-055-*.md`; `test_policy_adrs.py` |
| Organised Editing activity page published + registered, tools/data disclosed (016d) | met | `docs/governance/organised-editing-activity.md`, `data/organised_editing.toml`, `OrganisedEditingActivity`; `test_activity_page_discloses_tools_and_data_sources_with_conditions` |
| Hashtag declared, required, wired to §7 metric (016e) | met | `CHANGESET_HASHTAG`, `LeverageLedger`; `test_declared_hashtag_is_required_on_a_sig_suggestion`, `test_leverage_metric_reads_accepted_edits_from_the_hashtag` |
| Contribution-path licence gate blocks an incompatible source (016f) | met | `policy.licensing.assert_contribution_permitted`; `test_licence_gate_blocks_a_task_on_an_incompatible_source`, `test_policy_licensing.py` contribution suite |
| Device observations route to OSM/DeFlock, not SIG capture (004) | met (P16.1) | `tasks.submission.route_device_observation`; `test_device_observation_is_routed_not_captured` |
| Upstream attribution in API + export, not only About page (020) | met | `ClaimResponse.attribution` + `/claim`; exports `_rights`; `test_claim_response_names_its_upstream_attribution`, `test_export_row_names_its_upstream_structurally` |
| Phase-gate: CI green; new reqs tested; ADR; traceability + risk register updated | met | `make check` green; ADR-055; `docs/traceability.md` + `docs/risk_register.md` P16.2 sections |

## Deviations / deferrals

- No live MapRoulette client / OSM changeset feed yet; §7 metric's published surface (P15.5 page) reads fixtures — both source swaps, recorded in the risk register (RISK-P16-14/15).
- Real OSMF filing of the ADR/activity registration is an off-repo agentic act (RISK-P16-13); SIG-LIC-009 ODbL-distribution questions remain for counsel (RISK-P16-16).
- Out of scope, confirmed not implemented: records-request emission (SIG-CONTRIB-019, P10.3); export licence *computation* (P14.2); contributor tiers/onboarding/revert (P16.1). Stage-0 outreach (012/012a/013) is realised via the connectors compact/source registry.

Implements `docs/tickets/P16.2__contribution-back.md`.

Generated with [Devin](https://devin.ai)
