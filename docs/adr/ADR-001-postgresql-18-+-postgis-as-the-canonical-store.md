# ADR-001: PostgreSQL 18 + PostGIS as the canonical store; everything else a projection

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-STORE-006, SIG-STORE-001
- **Spec:** docs/2_canonical_design_spec.md §15.1–15.4

## Context

SIG needs one authoritative store for an append-only, temporally-versioned, claim-level graph with heavy geospatial reasoning. Candidate stores were graph databases, document stores, and a relational core.

## Decision

PostgreSQL 18 with PostGIS is the single canonical store. Every other representation — search index, analytics tables, tiles, exports — is a rebuildable projection of it.

## Consequences

One place holds truth; projections can be dropped and rebuilt. Requires disciplined migrations and RLS. Geospatial and temporal logic live in one engine.

## Alternatives considered

A native graph DB (weak temporal + geospatial story, second source of truth); a document store (loses referential integrity and constraints).

## Revisit trigger

PostGIS or a core Postgres capability SIG depends on is deprecated, or the claim spine cannot meet query-latency budgets at national scale despite projection.
