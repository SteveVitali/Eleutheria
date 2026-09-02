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
