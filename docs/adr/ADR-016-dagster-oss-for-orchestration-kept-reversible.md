# ADR-016: Dagster OSS for orchestration, kept reversible

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-INGEST-020, SIG-INGEST-021, SIG-INGEST-022
- **Spec:** docs/2_canonical_design_spec.md §21.8

## Context

Per-source, per-day backfill should be first-class, but a volunteer-footing project must not be captured by a tool whose licence or hosting economics may change.

## Decision

Use Dagster OSS (Apache-2.0), self-hosted on Postgres, with the orchestrator import confined to `orchestration/` and every stage runnable as a plain CLI so replacing Dagster with cron costs a config file, not a rewrite. AGPL/BUSL/Elastic-licensed orchestrators are excluded; Kubernetes is not a hard dependency.

## Consequences

Asset model maps onto evidence→claim lineage; backfill is first-class; the choice is reversible by construction (enforced by the import-boundary test).

## Alternatives considered

Airflow (heavier, weaker asset model); Prefect (licence/hosting trajectory); bespoke cron from day one (loses backfill ergonomics).

## Revisit trigger

Dagster moves to a non-OSI licence, its self-hosting economics degrade, or the asset model stops fitting — in which case the confined import boundary lets cron/Prefect replace it.

### Trigger evaluation — SEED-11 (Round 11 T1, 2026-10-01): FIRED

Evaluated at Round-11 Stage B, T1 (unit SEED-11d, 2026-10-01T07:49:22Z) from F3 §5.1
(`docs/build/planning/2026-09-30-next-phase/research/F3-backlog.md`) and the Round-11 plan
(`docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md`); an agent evaluation, not an operator
decision. **The trigger fired:** Dagster was never deployed; the scheduler of record is Cloud Scheduler (79
triggers) plus 88 Cloud Run jobs, and the GitHub `reingest.yml` workflow failed 6 of 6 runs on main,
2026-09-25…09-30 (A1 NEW-2, F-39, F-41; F3 §5.1). **Answer:** row P35.1a writes ADR-174 (scheduler of record:
Cloud Scheduler + daily live-diff + cron lint), which supersedes this ADR's scheduler clause and ADR-076's
scheduling path; P35.1a appends that status line here in its own PR (plan §7, S6R-24). P34.4 disables the
GitHub `reingest` schedule (QA-8) and P35.1b consolidates the scheduler (B-13). The decision above stays in
force until that answer lands; this ADR's body is unchanged (SIG-ENG-003).
