# Generator for docs/adr/*.md — kept in scratch (gitignored); only the .md outputs are committed.
import os, textwrap

ADRS = [
("001","PostgreSQL 18 + PostGIS as the canonical store; everything else a projection",
 "SIG-STORE-006, SIG-STORE-001","§15.1–15.4",
 "SIG needs one authoritative store for an append-only, temporally-versioned, claim-level graph with heavy geospatial reasoning. Candidate stores were graph databases, document stores, and a relational core.",
 "PostgreSQL 18 with PostGIS is the single canonical store. Every other representation — search index, analytics tables, tiles, exports — is a rebuildable projection of it.",
 "One place holds truth; projections can be dropped and rebuilt. Requires disciplined migrations and RLS. Geospatial and temporal logic live in one engine.",
 "A native graph DB (weak temporal + geospatial story, second source of truth); a document store (loses referential integrity and constraints).",
 "PostGIS or a core Postgres capability SIG depends on is deprecated, or the claim spine cannot meet query-latency budgets at national scale despite projection."),
("002","Append-only claim table; entity tables hold identity only",
 "SIG-STORE-009, SIG-STORE-020","§16.1–16.4",
 "The defining standard forbids silent overwrites (§3.1). A conventional mutable-row model destroys the history a provenance graph exists to keep.",
 "Claims are append-only; entity tables carry identity only, never attribute values. Resolved values are a derived view over claims. Corrections are new assertions with `supersedes`.",
 "History is preserved by construction; a query at a prior belief time is reproducible. Costs storage and requires derived-view machinery for 'current value'.",
 "Mutable entity rows with an audit log (the audit log becomes a second, divergent source of truth).",
 "A measured need arises to store a value with no supporting claim, or the derived-value view cannot meet performance budgets even after projection."),
("003","Two interval time dimensions plus one ordering scalar",
 "SIG-TIME-001","§9",
 "Surveillance facts have both a real-world validity interval and a belief/record interval, and events need a total order for reproducibility.",
 "Model valid-time and belief-time as two intervals, plus one monotonic ordering scalar for deterministic replay.",
 "Bitemporal queries ('what did we believe on date X about period Y') are expressible; replays are deterministic. Adds temporal-property test burden.",
 "Single timestamp (cannot distinguish validity from belief); event-sourcing only (loses interval semantics).",
 "A third independent time dimension proves necessary, or bitemporal modelling is shown to be unusable by contributors in practice."),
("004","EDTF for uncertain dates",
 "SIG-TIME-004","§9.5",
 "Source dates are frequently partial or uncertain ('summer 2019', '2021?'). Coercing them to exact timestamps manufactures false precision (violating §3.1).",
 "Use the Extended Date/Time Format (EDTF) to represent uncertain and partial dates as first-class values.",
 "Uncertainty is preserved, not invented. Requires EDTF parsing/validation and UI affordances.",
 "Nullable exact dates (loses the distinction between unknown and uncertain); free text (unqueryable).",
 "EDTF tooling becomes unmaintained, or a superseding standard is broadly adopted by our data sources."),
("005","Resolution as a stored decision record, not a view",
 "SIG-STORE-018, SIG-IDENT-028","§14.6–14.8",
 "Entity resolution must be re-runnable and auditable without silently moving claims between entities.",
 "Store each resolution as an explicit, versioned decision record (a `same_as` assertion with a ruleset version), not as an implicit view computed on read.",
 "Re-clustering produces new assertions with a new ruleset version; prior clustering is preserved and diffable. Requires a decision-record schema and rebuild path.",
 "Compute clusters as a materialized view (non-auditable, destroys prior state on refresh).",
 "Resolution volume makes stored decisions impractical, or a provably-auditable view mechanism becomes available."),
("006","OCFL 1.1 evidence store on object storage with governance-mode Object Lock",
 "SIG-EVID-005, SIG-EVID-006, SIG-GOV-009","§17.3",
 "Raw source snapshots must be immutable, digest-verifiable, re-parseable years later, and recoverable without SIG's software — while remaining removable for legitimate privacy demands.",
 "Store evidence bytes in an OCFL 1.1 root on S3-compatible object storage, one object per source stream, one version per capture, with Object Lock in **governance** mode (never compliance mode).",
 "E1–E6 (§17.1) satisfied by construction; the inventory is recoverable JSON. Governance mode keeps takedown (§45) satisfiable via a permissioned, audited path, at the cost of not being unimpeachable against a hostile demand.",
 "A bespoke content-addressed layout (reinvents OCFL); compliance-mode lock (makes legitimate removal technically impossible).",
 "OCFL is superseded by a better-supported preservation standard, or a legal regime forces reconsideration of governance vs compliance mode."),
("007","LinkML as the single ontology source of truth",
 "SIG-ONT-001","§20",
 "The schema, vocabularies, and generated artifacts must have one authoritative definition to avoid drift across code, DDL, and docs.",
 "Define the ontology in LinkML as the single source of truth; generate downstream artifacts (DDL fragments, docs, validators) from it.",
 "One edit point; generated artifacts are gated to match a fresh generation (SIG-ENG-016). Adds a LinkML toolchain dependency.",
 "Hand-maintained DDL plus separate docs (guaranteed drift); OWL-first (heavier than needed for this data).",
 "LinkML tooling becomes unmaintained, or generation cannot express a modelling need the domain requires."),
("008","SKOS for published controlled vocabularies",
 "SIG-ONT-008","§20",
 "Published vocabularies need stable identifiers, multilingual labels, and interoperability with the wider linked-data ecosystem.",
 "Publish controlled vocabularies as SKOS concept schemes.",
 "Standard, widely-consumed vocabulary format; supports adoption. Requires SKOS export from the LinkML source.",
 "Bespoke enums (poor interoperability); OWL classes for vocabularies (overweight).",
 "SKOS proves insufficient for a required vocabulary relationship, or adoption data shows consumers need a different format."),
("009","SPDX expressions for per-source licensing, with a build-time compatibility gate",
 "SIG-LIC-001, SIG-LIC-010, SIG-LIC-004a","§42",
 "Every source carries distinct rights; incompatible licence regimes must never be silently merged into one export.",
 "Record each source's licence as an SPDX expression (with `LicenseRef-SIG-*` for bespoke terms) in a rights record, and compute export licences from constituent rights with a compatibility gate that fails the build on incompatibility. Compartments are data (`policy/data/licenses.toml`), not code.",
 "Cross-compartment merges fail in CI; adding a new share-alike source is a data row. `redistributable` stays a separately-reviewed boolean, never derived from the string.",
 "A single project-wide licence (legally wrong for federated data); deriving redistributability from the licence string (SIG-LIC-003 forbids it).",
 "SPDX cannot express a licence SIG must ingest, or the compartment model needs a regime the data schema cannot represent."),
("010","DuckDB/Parquet analytics boundary; no raw audit rows anywhere",
 "SIG-STORE-010","§18",
 "Analytics must not become a back-door that stores or exposes the per-search audit rows the publication policy forbids.",
 "Run analytics over a DuckDB/Parquet projection built from aggregates only; no raw audit rows enter the analytics boundary, ever.",
 "Analytics scale cheaply and stay offline-friendly; the de-pseudonymisation hazard (§43.2a) cannot leak through analytics. Requires an aggregation step before projection.",
 "Analytics directly on the OLTP store (contention, and tempts raw-row access); a warehouse ingesting raw rows (violates §43.2a).",
 "Aggregation-only analytics cannot answer a required question, or DuckDB cannot meet analytic scale."),
("011","The ODbL posture: OSM-derived assets in a separate compartment (Strategy B)",
 "SIG-LIC-006, SIG-LIC-004a","§42.3",
 "SIG's device attribution is defined by comparison with OSM and uses OSM geometry, so the conservative reading of the OSM guidelines triggers ODbL share-alike; the two relevant guidelines point in opposite directions.",
 "Adopt Strategy B: publish the OSM-derived physical-asset layer under ODbL-1.0 as a physically separate table and export file, keeping the SIG-original graph under CC-BY-4.0.",
 "The licence enforces the federation compact (giving operator attributions back to OSM). ODbL and the CC-BY graph never merge. Requires per-compartment export files.",
 "Strategy A ('store only identifiers' — a join key is still a reference; unsafe); Strategy C (share-alike on everything — needlessly restricts non-OSM data).",
 "OSMF issues definitive guidance that changes the substantiality or collective-database analysis, or counsel (SIG-LIC-009) reaches a different regional-cut conclusion."),
("012","Sensitivity tiers enforced by RLS, applied at the view layer",
 "SIG-GEO-008, SIG-SEC-004, SIG-STORE-024","§19.4, §44.4",
 "Coordinate precision and record visibility must degrade by sensitivity class without ever leaking full precision through an aggregate or a mis-scoped query.",
 "Enforce sensitivity tiers with restrictive row-level security, and apply coordinate-precision transforms at the view layer; full precision is retained only in canonical storage. Export roles run with row security off so a would-be-filtered export fails loudly.",
 "Precision policy is enforced by the database, not by application discipline; RLS policy tests are CI-blocking. Requires careful role design.",
 "Application-layer filtering only (one missed query leaks); blurring after aggregation (leaks precise values through the aggregate, SIG-GEO-010).",
 "Postgres RLS proves inadequate for a required policy, or the view-layer transform cannot meet query-latency budgets."),
("013","uv as the workspace and lockfile tool",
 "SIG-ENG-011","§47",
 "A monorepo of many Python packages needs fast, reproducible dependency management with a committed lockfile and a standards-based export.",
 "Use uv for the workspace, the committed `uv.lock`, and a PEP 751 `pylock.toml` export; humans and CI run identical `make` targets.",
 "Fast, reproducible, frozen installs; one toolchain. Adds a dependency on a relatively young tool (mitigated by the standards-based export).",
 "pip-tools + venv (slower, more moving parts); Poetry/PDM (heavier, or weaker workspace story at adoption time).",
 "uv's licence or maintenance changes adversely, or PEP 751 tooling in the wider ecosystem makes a different resolver clearly preferable."),
("014","Astro for the public web surface",
 "SIG-ENG-010, SIG-UI-002","§47, §39",
 "The design centre is a local advocate who needs a fast, printable, static-first site; TypeScript is confined to `web/`.",
 "Build the public site with Astro, producing static HTML by default with islands only where interactivity is needed.",
 "Static-first output is cheap to host, mirrorable, and survives the app being offline (§46.5); good print path. Ties the web layer to Astro's conventions.",
 "Next.js (heavier, SSR-first); a SPA framework (poor no-JS and print story, fails SIG-UI accessibility goals).",
 "Astro cannot meet the accessibility/no-JS or print requirements, or its maintenance/licence posture changes."),
("015","AWS S3 for the evidence store and CloudFront for bulk-export delivery",
 "SIG-EVID-005, SIG-EXPORT-008, SIG-EXPORT-009","§17.3, §38.5",
 "The evidence store needs S3 semantics (versioning + Object Lock governance mode, ADR-006). But §38.5 makes egress pricing the existential cost for bulk downloads, and AWS egress is expensive — 'success is the failure mode'.",
 "Use AWS S3 for the evidence store (where its Object Lock semantics are load-bearing and volume is modest), and front bulk exports with CloudFront to cap origin egress. Reconcile the §38.5 constraint by (a) CloudFront caching, (b) offering torrent and IPFS for the largest artifacts (SIG-EXPORT-009), and (c) keeping a low/zero-egress object-storage mirror (e.g. R2/B2) for bulk export files so the four-figure-bill scenario is bounded.",
 "Object Lock governance mode is available for evidence; bulk-download egress is bounded rather than open-ended. Multi-provider setup adds operational complexity and an explicit egress-budget alarm.",
 "All-AWS with direct S3 downloads (unbounded egress bill); a single zero-egress provider for everything (weaker Object Lock / preservation guarantees for the evidence store).",
 "Monthly egress cost crosses the budgeted threshold, download volume exceeds the modelled TB/month, or a provider changes egress pricing — at which point bulk delivery shifts further to the low-egress mirror and peer-to-peer distribution."),
("016","Dagster OSS for orchestration, kept reversible",
 "SIG-INGEST-020, SIG-INGEST-021, SIG-INGEST-022","§21.8",
 "Per-source, per-day backfill should be first-class, but a volunteer-footing project must not be captured by a tool whose licence or hosting economics may change.",
 "Use Dagster OSS (Apache-2.0), self-hosted on Postgres, with the orchestrator import confined to `orchestration/` and every stage runnable as a plain CLI so replacing Dagster with cron costs a config file, not a rewrite. AGPL/BUSL/Elastic-licensed orchestrators are excluded; Kubernetes is not a hard dependency.",
 "Asset model maps onto evidence→claim lineage; backfill is first-class; the choice is reversible by construction (enforced by the import-boundary test).",
 "Airflow (heavier, weaker asset model); Prefect (licence/hosting trajectory); bespoke cron from day one (loses backfill ergonomics).",
 "Dagster moves to a non-OSI licence, its self-hosting economics degrade, or the asset model stops fitting — in which case the confined import boundary lets cron/Prefect replace it."),
("017","FastAPI for the read API",
 "SIG-API-001","§47, §37",
 "SIG needs a documented, typed read API with as-of handling and an OpenAPI contract; this is a lower-stakes default.",
 "Use FastAPI for the read API, with generated OpenAPI and Pydantic models.",
 "Typed request/response models, automatic OpenAPI, good async support. Ties the API layer to FastAPI/Starlette.",
 "Flask (no built-in typing/OpenAPI); Django REST (heavier than a read-only API needs).",
 "The API grows needs FastAPI cannot serve, or its maintenance posture changes materially."),
("018","MapLibre GL for the web map",
 "SIG-GEO-012, SIG-UI-002","§19.5, §39",
 "The public map must render static PMTiles without a mandatory dynamic tile server, and must not depend on a proprietary map SDK.",
 "Use MapLibre GL (open source) as the web map renderer, consuming static PMTiles v3.",
 "Open, self-hostable, consumes static tiles; no proprietary SDK lock-in or usage-based billing. Requires PMTiles generation (tippecanoe).",
 "Mapbox GL JS (proprietary licence, usage billing); Leaflet (weaker vector-tile/GL story).",
 "MapLibre cannot render a required cartographic feature, or a superior open renderer is broadly adopted."),
("019","pytest + Hypothesis for testing",
 "SIG-ENG-015, SIG-ENG-016","§48",
 "The test taxonomy requires randomized temporal-property tests alongside conventional unit/integration tests.",
 "Standardize on pytest as the runner and Hypothesis for property-based tests (e.g. temporal invariants, deterministic transforms).",
 "One runner; property tests catch edge cases table-driven tests miss. Hypothesis adds a dev dependency and some flakiness discipline (seed control).",
 "unittest only (no property testing); a separate property-test framework (fragmentation).",
 "Hypothesis maintenance/licence changes, or property tests prove net-negative in maintenance for this codebase."),
("020","GitHub Actions for CI",
 "SIG-ENG-015, SIG-ENG-016","§48",
 "CI must run the same `make` gate humans run, on every PR, with dependency/container scanning and per-release SBOM/signing.",
 "Use GitHub Actions as the CI system, invoking the same `make` targets as local development.",
 "Ubiquitous, no extra hosting, matches where the code lives. Couples CI config to GitHub.",
 "Self-hosted CI (operational burden for a small team); another SaaS CI (another account/economics).",
 "The project moves off GitHub, Actions pricing/limits become prohibitive, or a compliance need requires self-hosted runners."),
]

os.makedirs("docs/adr", exist_ok=True)
for num,title,reqs,secs,context,decision,cons,alts,revisit in ADRS:
    fn=f"docs/adr/ADR-{num}-{title.lower().split(';')[0].split(':')[0].replace(',','').replace('.','').replace('/','-').replace('(','').replace(')','').replace(' ','-')[:60].strip('-')}.md"
    body=f"""# ADR-{num}: {title}

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** {reqs}
- **Spec:** docs/2_canonical_design_spec.md {secs}

## Context

{context}

## Decision

{decision}

## Consequences

{cons}

## Alternatives considered

{alts}

## Revisit trigger

{revisit}
"""
    open(fn,"w").write(body)
    print(fn)
print("wrote", len(ADRS), "ADRs")
