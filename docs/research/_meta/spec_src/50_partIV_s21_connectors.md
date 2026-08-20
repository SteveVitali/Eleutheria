# Part IV — Acquisition

## 21. Connector architecture

### 21.1 The eight-stage pipeline

**SIG-INGEST-001 (MUST).** Every source adapter MUST implement the same eight-stage interface.
Stages are separately addressable, separately retryable, and each persists a content-addressed
artifact so that any downstream stage can be re-run without re-contacting the source.

```
discover()  → what exists at this source right now (identifiers, not content)
fetch()     → obtain bytes           [the ONLY stage permitted network egress]
capture()   → immutable, content-addressed storage + evidence_capture row
parse()     → structure from bytes   [pure function of a capture]
extract()   → raw claims with locators
normalize() → typed values beside preserved raw values
link()      → entity resolution against the identity layer
load()      → claims into L1
```

**SIG-INGEST-002 (MUST).** `fetch()` MUST be the **only** stage permitted network egress. Every
stage after `capture()` MUST be a pure function of stored artifacts. This is what makes replay
possible and is enforced by running replay in a network-isolated context — an attempted egress in
`parse()` or later MUST fail the run, not silently succeed.

**SIG-INGEST-003 (MUST).** Every stage MUST be idempotent. Re-running a stage over identical inputs
MUST produce identical outputs modulo generated ids and transaction timestamps.

### 21.2 Claim identity and re-extraction

**SIG-INGEST-004 (MUST).** The claim's logical identity MUST include `extractor_version` and
`normalizer_version`. A better parser therefore produces **genuinely new claim rows**, not
mutations of existing ones. *(R11; this is the operational reading of P2 and P3.)*

**SIG-INGEST-005 (MUST).** Re-extraction MUST preserve `observed_at` and `valid_*` from the source
and set `recorded_at = now()`. An `as_of_belief` query in the past therefore still returns the old
interpretation, and reproducibility survives every parser improvement.

**Why this matters more than it looks.** Treating re-extraction as a migration — updating rows in
place when the parser improves — silently destroys history and breaks every citation made against
the previous interpretation. Treating it as a *write path* costs storage and preserves the record.
R11 identifies this as the top operational risk the outline does not address.

### 21.3 Source classes and incrementality (Q23, Q24)

**SIG-INGEST-006 (MUST).** Every connector MUST declare its ingestion mode and its incrementality
strategy.

| Mode | Incrementality | Examples |
|---|---|---|
| Bulk file download | ETag / Last-Modified / content-hash diff, then row-level diff | Atlas CSV, GLEIF, Census Gazetteer, TIGER |
| REST API | Cursor or updated-since watermark | DocumentCloud, USAspending, CourtListener, Legistar, PrimeGov, CivicClerk, NextRequest, FBI CDE |
| Replication diff | Sequence number | OSM minutely/daily diffs |
| Bulk geodata | Regional extract + diff application | OSM PBF extracts |
| HTML scraping | Normalized-content hashing on **extracted structure**, not raw HTML | Agency sites, vendor pages |
| Headless-browser capture | Same, plus WACZ | SPA sources |
| Manual / human-in-the-loop | Upload event | FOIA responses, contributor photos, manually acquired research datasets |
| Partner feed | Partner-defined | Ecosystem collaborations |
| Alert stream | Message id | RSS, agenda notifications, news |

**SIG-INGEST-007 (MUST).** Change detection on scraped pages MUST diff the **extracted structured
payload**, not the HTML. Boilerplate churn, session tokens, and rotating asset hashes otherwise
produce a continuous stream of false changes that destroys the value of the change feed.

**SIG-INGEST-008 (MUST).** Some dependencies are **manual-acquisition** and MUST be modelled as
such, with a documented human procedure recording DOI, version, and checksum. The build MUST NOT
assume they are automatically fetchable. Pretending a manual dependency is automatable produces a
pipeline that silently runs on stale data.

### 21.4 Source disappearance is data

**SIG-INGEST-009 (MUST).** A 404, a removal, or a persistent challenge MUST be recorded as a
**first-class event row**, not handled as a retryable exception. *(§17.6; OL-2B-FP-03, OL-3-04.)*

**SIG-INGEST-010 (MUST).** Disappearance MUST generate a research task and MUST be queryable, so
that "which agencies quietly removed their transparency portal" is an answerable question. If
disappearance lives only in the exception path, that dataset never exists — and it is one of the
most informative datasets SIG can produce.

### 21.5 Politeness and access

**SIG-INGEST-011 (MUST).** A shared rate-limiter and robots layer MUST sit between every connector
and the network, with per-host budgets, a documented crawler UA carrying a contact URL, and
crawl-delay honoring. Connectors MUST NOT hold their own HTTP clients.

**SIG-INGEST-012 (MUST).** Where `robots.txt` cannot be retrieved, crawl permission MUST be treated
as **not granted** and the connector MUST refuse to run. *(REQ-R2-02; this case is real —
`transparency.flocksafety.com/robots.txt` returns 403, F2.1.)*

**SIG-INGEST-013 (MUST NOT).** SIG MUST NOT operate a crawler that defeats a bot-management
challenge on any source. *(REQ-R2-01; §26, §46.5.)*

**SIG-INGEST-014 (MUST).** The connector loader MUST check the source's `ingestion_permitted` flag
and `custody_posture` (§8.4) **before** any fetch, and MUST refuse to run when permission is absent
or unresolved. Licensing is enforced by the pipeline, not by good intentions.

### 21.6 Lineage

**SIG-INGEST-015 (MUST).** Every claim MUST be traceable to its `ingest_run`, recording: connector
name and version, code commit, ruleset version, vocabulary version, input evidence digests,
parameters, and environment (§17.7).

**SIG-INGEST-016 (MUST).** Lineage records MUST map onto **PROV-O** for interoperable export:
captures and claims are `prov:Entity`; runs and extractions are `prov:Activity`; connectors,
curators, and sources are `prov:Agent`; `revises_claim` is `prov:wasRevisionOf`.

### 21.7 Backfill and replay

**SIG-INGEST-017 (MUST).** SIG MUST be able to re-run extraction over archived captures with an
improved parser and produce a new claim set **without destroying the old one**.

**SIG-INGEST-018 (MUST).** Replay MUST run against archived snapshots only, in a network-isolated
context. The interface makes contacting the source impossible during replay, which both guarantees
reproducibility and prevents a replay from accidentally hammering an upstream.

**SIG-INGEST-019 (MUST).** A replay MUST be able to run in **shadow mode**: producing the new claim
set, diffing it against the current one, and reporting the delta for review *before* the new claims
are asserted. A parser change that silently alters 40,000 claims must be seen before it lands.

### 21.8 Orchestration

**SIG-INGEST-020 (SHOULD).** Orchestration SHOULD use **Dagster OSS** (Apache-2.0), self-hosted on
Postgres. Its asset model maps directly onto SIG's evidence→claim lineage, and its partitions make
per-source, per-day backfill a first-class operation rather than a bespoke script.

**SIG-INGEST-021 (MUST).** The orchestration choice MUST be **reversible**. Every stage MUST be
runnable as a plain CLI invocation, with the orchestrator import confined to a single
`orchestration/` package. Replacing Dagster with cron MUST cost a configuration file, not a
rewrite. Rationale: a public-interest project on a volunteer footing must not be captured by a tool
whose licence or hosting economics may change.

**SIG-INGEST-022 (MUST NOT).** Orchestrators under AGPL, BUSL, or Elastic-style licences MUST NOT
be adopted (SIG-STORE-002). Kubernetes MUST NOT be a hard dependency.

---
