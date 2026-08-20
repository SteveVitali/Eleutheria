# Appendix F — Architecture Decision Record index

**SIG-STORE-006** requires each decision below to be written as an ADR under `docs/adr/` in Phase 1,
using a consistent template: context, decision, status, consequences, alternatives considered, and —
mandatory per SIG-STORE-007 — a **revisit trigger**.

| ADR | Decision | Spec | Revisit trigger |
|---|---|---|---|
| ADR-001 | PostgreSQL 18 + PostGIS canonical; everything else a projection | §15.1 | A projection becomes the sole home of any fact; or a managed-Postgres dependency becomes unavailable |
| ADR-002 | Append-only claims; entity tables hold identity only | §16.1–16.3 | Write throughput becomes a demonstrated bottleneck |
| ADR-003 | Two interval time dimensions + one ordering scalar | §9.2 | A use case requires `AS OF` travel along observation time |
| ADR-004 | EDTF for uncertain dates | §16.7 | EDTF tooling becomes unmaintained |
| ADR-005 | Resolution as a stored decision record | §16.4 | Storage cost of resolutions exceeds a defined share of the database |
| ADR-006 | OCFL 1.1 evidence store, governance-mode Object Lock | §17.3 | A legal regime makes governance mode untenable |
| ADR-007 | LinkML as the single ontology source of truth | §20.1 | Generated artifacts diverge from hand-written needs in more than one target |
| ADR-008 | SKOS for published vocabularies | §20.2 | A downstream consumer standard displaces SKOS |
| ADR-009 | SPDX expressions + a build-time licence gate | §42.1, §42.4 | A key source's terms are inexpressible in SPDX |
| ADR-010 | DuckDB/Parquet analytics boundary; no raw audit rows | §18 | Interactive aggregate latency misses its budget |
| ADR-011 | **Strategy B ODbL posture: separate ODbL asset layer, CC-BY-4.0 graph** | §42.3 | OSMF guidance changes; or counsel advises differently on the §42.3 residuals |
| ADR-012 | Sensitivity tiers via RLS, applied at the view layer | §16.8, §19.4 | A tier transform is shown to be invertible from published aggregates |
| ADR-013 | Apache-2.0 code; CC-BY-4.0 data; CC0 ontology | §42.2 | Proprietary re-hosting causes demonstrated harm to the commons |
| ADR-014 | Dagster OSS orchestration, kept reversible | §21.8 | Its licence changes; or ops burden exceeds the cron alternative |
| ADR-015 | Static-first, zero-JS-default frontend | §40 | Interactive requirements make progressive enhancement untenable |
| ADR-016 | Splink 4 for probabilistic ER | §14.6 | Holdout precision cannot reach the auto-write threshold |
| ADR-017 | No direct automated OSM writes | §35.2 | The OSM automated-edits review (R-14) concludes otherwise |
| ADR-018 | Rule-based, non-learned resolution | §28.1 | A learned resolver demonstrates both better accuracy *and* per-decision explainability |
