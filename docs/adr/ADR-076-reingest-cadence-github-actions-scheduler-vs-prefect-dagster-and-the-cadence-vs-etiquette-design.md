# ADR-076 — Re-ingest cadence: a GitHub Actions cron scheduler (vs Prefect/Dagster) and the cadence-vs-etiquette design

- **Status:** Accepted
- **Phase / ticket:** P24.2 — Re-ingest cadence & orchestration (SCHED.1, GL-SCHED-01)
- **Date:** 2026-09-10
- **Related:** ADR-065 (live connector wiring — `PoliteFetcher`, `HttpxTransport`, the gated
  `sig-connectors run --mode live` CLI and the fetch record), ADR-016 (Dagster OSS as the
  chosen-but-unwired orchestrator, SIG-INGEST-020/021), ADR-075 (the zero-cost GCP host),
  ADR-067 (the monthly `keepalive.yml` cron precedent); SIG-INGEST-011/037/045d/045h (crawler
  conduct + Overpass etiquette), SIG-EVID-013/014/015 (disappearance as data + the sweep
  cadence), SIG-STORE-003 (binding zero-cost posture); RISK-P21-04, RISK-P24-01, HG-03/HG-09.

## Context

P21.3 wired real transports behind the ingestion gate but explicitly deferred
**scheduling/orchestration** to the backlog ("Scheduling/orchestration (Prefect/Dagster seam)
— backlog"). SCHED.1 (GL-SCHED-01) closes that seam: drive `sig-connectors run` per source on
a cadence that respects source etiquette, track per-source freshness, and run the
disappearance-detection sweep on a cadence — **via a minimal scheduler, not a heavyweight
orchestrator unless warranted**.

Two facts shape the decision:

- **The runner already exists and is already polite + gated.** `connectors.runner.run_source`
  runs the eight stages through the shared `PoliteFetcher` (per-host crawl-delay from robots,
  retry-with-backoff on 429/503/504 honouring `Retry-After`, Overpass 429/504 = back off) and
  **refuses a live fetch (exit 3) for any non-green source** (ADR-065). Disappearance already
  has a first-class home (`connectors.disappearance` → `evidence.disappearance`, SIG-EVID-013/014,
  with `sweep_cadence_days` keyed by volatility). A scheduler must **build on** these, not
  re-implement crawler conduct or the disappearance datum.
- **The zero-cost posture (SIG-STORE-003) is binding** and the repo already runs a free
  GitHub Actions cron for degraded-mode keepalive (ADR-067). A Prefect/Dagster control plane
  would add a hosted, always-on service (cost + ops surface) for a workload that is a handful
  of per-source re-ingests on multi-day intervals.

The `orchestration/` package is the **only** package permitted to import a workflow
orchestrator (Dagster is the chosen-but-unwired one, ADR-016 / SIG-INGEST-021); the import
boundary is enforced by `tests/unit/test_import_boundary.py`.

## Decision

**1. The scheduler form is a GitHub Actions cron (`.github/workflows/reingest.yml`), not
Prefect/Dagster.** It is the minimal thing that works, is $0 (free tier), and reuses the exact
`keepalive.yml` shape (ADR-067). The `orchestration/` Dagster seam stays **reserved and
reversible** (`ORCHESTRATOR_MODULES` unchanged, import boundary intact): if fan-out,
backfills, retries-with-state, or cross-source dependencies ever warrant a control plane, the
cadence engine below is the unit a Dagster job would call — no rewrite.

**2. Cadence vs etiquette is a two-layer design** (`orchestration.cadence`, GL-SCHED-01):

- *Coarse — the re-ingest interval (this layer).* `reingest_interval_days(source)` derives a
  per-source interval from the registry `cadence` free-text (parsing counts like "every 7 days"
  and the common cadence words), defaulting to **30 days** (the `MODERATE` volatility class) and
  **clamped to a `MIN_INTERVAL_DAYS = 1` etiquette floor** — the scheduler never drives a source
  faster than daily even if its text says "hourly". `sig-orchestration due` lists the sources
  whose interval has elapsed since the last recorded ingest; the workflow loops that list.
- *Fine — request pacing (the existing `PoliteFetcher` layer).* Every `sig-connectors run` the
  workflow invokes egresses through `PoliteFetcher`/`HttpxTransport` — per-host crawl-delay,
  429/503/504 back-off, no challenge defeat (SIG-INGEST-011/037). The scheduler **never
  bypasses the gate**: a non-green source is refused (exit 3) before any socket opens, so the
  workflow is safe to ship before any HG-03 flip.

**3. Freshness is an append-only ledger** (`FreshnessLedger`, JSONL per source under
`docs/build/freshness/`): a scheduled ingest **appends** a dated `FreshnessRecord`
(`ingested_at`, `claim_count`, connector, release version) and never rewrites one. A re-ingest
that observes changed upstream content produces **new dated claims** (a new release
version/digest + retrieval date, the data_driven release model, SIG-INGEST-043d/017) into the
shared claim sink — the prior claims are retained, never overwritten (append-only, P1–P3).

**4. Disappearance detection rides the sweep cadence.** `disappearance_sweep_days(volatility)`
delegates to `evidence.disappearance.sweep_cadence_days` (single source of truth), and
`detect_disappearance(...)` reuses `connectors.disappearance` verbatim to turn a scheduled
fetch outcome (404/410 link rot, 401/451 access-restricted, a persistent challenge) into a
first-class disappearance **event + research task** — never a swallowed retry. The scheduler
decides *when* (the cadence), not *how* (that stays in the connector/evidence layers).

## Consequences

- SIG has a working, zero-cost re-ingest scheduler that respects source etiquette at two
  layers and produces new dated claims + freshness on every tick, with a disappearance record
  when a source goes dark — all three P24.2 acceptance behaviours are covered by tests that
  fail if the behaviour is removed (`tests/orchestration/test_reingest_cadence.py`).
- Additive/append-only/back-compat: `orchestration/` gains a `cadence` module + CLI verbs
  (`due`/`interval`/`freshness`/`record`/`sweep-cadence`) and a new workflow file; no existing
  command, schema, or the frozen §47 layout changes. `orchestration/` now declares its inward
  dependency on `sig-connectors`/`sig-evidence` (the import boundary still forbids any package
  importing *out* to the orchestrator).
- The real live re-ingest stays HG-03-gated: until a source is flipped green the workflow's
  per-source run is refused (exit 3) and skipped, not failed — nothing fetched, no green
  fabricated.

## Alternatives considered

- **Prefect / Dagster deployment now** — rejected as not warranted: an always-on control plane
  adds cost + ops surface for a multi-day-interval, few-source workload under a binding
  zero-cost posture. The `orchestration/` Dagster seam is kept reserved for the day fan-out /
  stateful backfills justify it (SIG-INGEST-021 — reversible).
- **A cron on the GCE box (ADR-075)** — rejected as the default: it couples the schedule to the
  single always-free VM (which the compose stack already saturates) and hides the schedule from
  review; GitHub Actions keeps it in-repo, reviewable, and free. (An operator may still add a
  host cron later; the CLI is the same surface.)
- **Encoding the cadence as a fixed per-source constant in code** — rejected: the registry
  already carries an observed `cadence` field; parsing it (with a safe default + etiquette
  floor) keeps one source of truth and lets a registry edit change the cadence without code.
- **Overwriting a source's claims on re-ingest ("latest wins")** — rejected outright: it
  violates the append-only claim spine (P1–P3). A re-ingest adds new dated claims; corrections
  are new claims, never mutations.

## Revisit trigger

Revisit this decision when any of the following holds:

- **A source is flipped green (HG-03) and its real cadence is observed.** Once live fetches
  run, confirm the derived interval matches what the source tolerates (429 rate, `Retry-After`
  patterns in the fetch records) and tighten `reingest_interval_days`/the registry `cadence`
  if the default over- or under-polls.
- **Fan-out, stateful backfills, retries-with-state, or cross-source dependencies appear.**
  If the schedule needs a real DAG (e.g. re-ingest → reconcile → export chained with retries
  and observability), promote the cadence engine into a Dagster job in `orchestration/` — the
  seam and the import boundary already exist for exactly this.
- **The free GitHub Actions scheduler is disabled for inactivity or removed.** The known decay
  path for free cron (RISK-P0-12, ADR-067): if the reingest workflow silently stops, move the
  cadence loop to the host cron on the GCE box (ADR-075) or a `keepalive`-style loud-failing job.
- **A disappearance sweep proves too slow/fast for a volatility class.** If `sweep_cadence_days`
  misses real link rot or over-checks, revisit the volatility→days mapping (SIG-EVID-015).
