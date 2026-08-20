# Part IX — Engineering practice

## 47. Stack and repository

**SIG-ENG-010 (MUST).** Primary language **Python** for the data platform; **TypeScript** confined
to the web package. SIG MUST NOT author Rust or Go components without an ADR — a small team cannot
maintain four toolchains.

**SIG-ENG-011 (MUST).** **Monorepo**, as a workspace, with a committed lockfile plus a
standards-based lock export and an SBOM per release.

**SIG-ENG-012 (MUST).** Repository layout:

```
ontology/        LinkML source of truth; vocabularies (SKOS); generated artifacts
db/              sqitch migrations; RLS policies; DDL
connectors/      one package per source; each with fixtures/
parsing/         format handlers; extraction; locators
resolution/      entity resolution; blocking; gold set; metrics
reconcile/       resolver; rulesets (data); strategies; contradiction detectors
inference/       L4 derivations
tasks/           detectors; lifecycle; records-request templates
api/             read API; OpenAPI; as-of handling
web/             the public site (TypeScript)
exports/         bulk artifact builders; licence computation
orchestration/   the ONLY package importing the orchestrator
policy/          publication rules; sensitivity classification; licence gates
ops/             deployment; observability; runbooks
docs/            spec, ADRs, methodology, governance
tests/           unit; integration; acceptance/queries; property; fixtures
```

**SIG-ENG-013 (MUST).** Every pipeline stage MUST be invocable as a plain CLI command, with the
orchestrator import confined to `orchestration/` (SIG-INGEST-021).

**SIG-ENG-014 (MUST).** `policy/` MUST be a real, tested code package — the publication rules,
sensitivity classification, and licence gates are executable logic, not prose in `docs/`.

---

## 48. Testing

**SIG-ENG-015 (MUST).** The test taxonomy MUST include all of:

| Class | Asserts |
|---|---|
| Schema | Entity tables hold no attribute columns (SIG-STORE-009); no plate-capable column (SIG-STORE-026); append-only trigger column list matches the live schema |
| **Temporal property tests** | Randomized: `valid_from ≤ valid_to`; supersession chains acyclic and terminating; `as_of` monotonicity; correction preserves prior belief |
| Referential integrity | No orphan claims; every claim has origin and rights |
| Vocabulary conformance | Every claim's predicate registered; every term in scheme; no retired term on a new claim |
| **Geospatial sanity** | Asset falls inside the jurisdiction it is attributed to, or the mismatch raises a task (§33.2 #12) |
| **Count plausibility** | A source reporting 0 after reporting 300 is an alert, never a silent overwrite |
| Resolution determinism | Rebuild L3 from scratch; assert identical output (SIG-STORE-018) |
| **Reproducibility** | Re-run a pinned connector over pinned digests; assert byte-identical claims modulo id and sys_period |
| ER regression | Precision/recall on the frozen holdout; auto-demote on breach (SIG-IDENT-028) |
| **Parser fixtures** | Committed real captures with expected outputs (SIG-PARSE-007) |
| **Upstream canary** | Nightly, against live sources; alerts on structural drift (SIG-PARSE-008) |
| RLS policy | Per role and tier, both visibility and non-visibility (SIG-STORE-024) |
| **Licence gate** | A deliberately incompatible source MUST fail the export build |
| **Policy engine** | Each sensitivity class produces the specified precision; a residential-parcel candidate is never published |
| Acceptance queries | Q-1…Q-13, J-1…J-4 against fixtures (SIG-CHART-009) |
| Accessibility | Automated WCAG checks; no-JS smoke test |
| Performance | Budgets enforced; build fails on regression |

**SIG-ENG-016 (MUST).** Per-PR: unit, schema, property, fixture, licence-gate, policy-engine,
acceptance. Nightly: canaries, ER regression, full L3 rebuild, reproducibility.

**SIG-ENG-017 (MUST).** Data-quality checks MUST run **in the pipeline**, not only in CI
(SIG-ENG-004.3). A check that only runs against fixtures does not protect production data.

**SIG-ENG-018 (MUST).** Data-quality tooling MUST be OSI-licensed; several widely-recommended
options in this category have moved to source-available licences and MUST be re-verified at
adoption time rather than assumed.

---

## 49. Observability

**SIG-ENG-019 (MUST).** Structured logging with run correlation; metrics on ingestion volume,
claim/contradiction/task counts, resolution latency, and per-source freshness; error tracking.

**SIG-ENG-020 (MUST).** A **public** data-freshness and status page (SIG-METRIC-007). Publishing
staleness is a trust affordance, and hiding it is the beginning of implying completeness.

**SIG-ENG-021 (MUST).** Alerting MUST cover: connector failure; parser drift; count-plausibility
breach; ER precision breach; licence-gate failure; policy-engine failure; and a **silent success**
condition — a connector that "succeeds" while returning zero records MUST alert, never pass
(SIG-IDENT-008).

**SIG-ENG-022 (MUST).** Runbooks MUST exist for: source disappearance; upstream schema change; a
bad-merge rollback; a takedown request; a suspected poisoning campaign; and evidence-store
restoration.

---

## 50. Deployment and cost

**SIG-ENG-023 (MUST).** Topology: managed Postgres+PostGIS; object storage with versioning and
governance-mode Object Lock; a small compute instance for crawlers and jobs; CDN for static
artifacts; static site hosting; error tracking.

**SIG-ENG-024 (MUST).** **Egress-friendly object storage is a hard requirement**, not an
optimization (SIG-EXPORT-008).

**SIG-ENG-025 (MUST).** Three cost scales MUST be maintained and reviewed quarterly:

| Scale | Character |
|---|---|
| **Bootstrap** | Free/low tiers, zero-egress storage, free CI on a public repository, a single small instance. **Order of tens of dollars per month.** |
| **Steady state** | Paid database tier, headless-browser capacity, LLM extraction budget, monitoring |
| **Ambitious** | Redundancy, mirrors, higher-frequency capture, staffed review |

**SIG-ENG-026 (MUST).** LLM extraction cost MUST be budgeted per document class and monitored
against the budget, with the pipeline degrading to human-queue rather than exceeding it
(SIG-LLM-007).

**SIG-ENG-027 (MUST).** The bootstrap scale MUST be **real and tested** — the project must be able
to survive on it (SIG-GOV-020), and a plan that only works when funded is not a plan for a
public-interest project.

---
