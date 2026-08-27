# Architecture Decision Records (Appendix F)

Every architectural decision is recorded here under a consistent template
(context, decision, status, consequences, alternatives considered, and a
**revisit trigger**). An ADR with no revisit trigger is incomplete
(SIG-STORE-007); `tests/unit/test_policy_adrs.py` enforces this mechanically.

Decisions are immutable: a change is a **new ADR** (SIG-ENG-003), never an edit
of a landed one.

## Index

| ADR | Decision |
|---|---|
| ADR-001 | PostgreSQL 18 + PostGIS as the canonical store; everything else a projection |
| ADR-002 | Append-only claim table; entity tables hold identity only |
| ADR-003 | Two interval time dimensions + one ordering scalar |
| ADR-004 | EDTF for uncertain dates |
| ADR-005 | Resolution as a stored decision record, not a view |
| ADR-006 | OCFL 1.1 evidence store on object storage with governance-mode Object Lock |
| ADR-007 | LinkML as the single ontology source of truth |
| ADR-008 | SKOS for published controlled vocabularies |
| ADR-009 | SPDX expressions for per-source licensing, with a build-time compatibility gate |
| ADR-010 | DuckDB/Parquet analytics boundary; no raw audit rows anywhere |
| ADR-011 | The ODbL posture (§42.3) — OSM-derived assets in a separate compartment |
| ADR-012 | Sensitivity tiers enforced by RLS, applied at the view layer |
| ADR-013 | uv as the workspace and lockfile tool |
| ADR-014 | Astro for the public web surface |
| ADR-015 | AWS S3 evidence store + CloudFront for bulk-export delivery (reconciling §38.5 egress) |
| ADR-016 | Dagster OSS for orchestration, kept reversible |
| ADR-017 | FastAPI for the read API |
| ADR-018 | MapLibre GL for the web map |
| ADR-019 | pytest + Hypothesis for testing |
| ADR-020 | GitHub Actions for CI |

ADR-001…012 are the §15.5 decision set; ADR-013…020 are the stack ADRs. The
egress question of §38.5 is resolved for the whole project in ADR-015.
