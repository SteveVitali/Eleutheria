# Named evidence domains and the source funnel (P32.1 / SIG-MEM-001, D3)

Published 2026-09-27 for the Round-10 consumers: the **evidence-domain** names govern every
verification claim in run ledgers, the coverage matrix and the P32.7 current projection
(SIG-MEM-002); the **source-funnel** unit names govern the funnel counters the projection and the
P32.21 bounded pilot report (SIG-ACQ-004). These are *definitions and routing*, not implementations —
the projection that consumes them lands in P32.7, the pilot funnel in P32.21.

## 1. Evidence domains

Every claim of "verified" in Round 10 names exactly one domain, one revision and one date.
Domains are ordered by how far the evidence reaches; **no domain substitutes for another**:

| domain | definition | typical instruments | can never establish |
|---|---|---|---|
| `fixture` | committed fixtures + unit/property tests over synthetic or recorded bytes; deterministic and offline | `uv run pytest tests/unit|acceptance|property`, adversarial fixture trees, shadow diff=0 replays | a live fetch, a hosted count, public exposure |
| `implementation` | landed code on a named revision: lint/typecheck/`make check`, generated-artifact verification | `make check`, `verify-gen`, spec/backlog/coverage checkers | anything about the running stack |
| `composed-db` | the Docker-gated suites against real Postgres/PostGIS + the composed stack | `make test-db`, `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db|e2e` | hosted/public behaviour (testcontainers, not the deployment) |
| `hosted` | the deployed GCP spine/jobs/API (`sig-pg`, `sig-materialize`, `sig-ingest-*`, `sig-api`, buckets) — restricted/internal surfaces | digest-pinned Cloud Run jobs, `probe-hosted`, Cloud SQL checks, `probe -print` | public availability or a published artifact |
| `public` | the anonymously reachable surface + released artifacts (`sig-web`, `gs://…-sig-public`, record URLs, tiles, indexes) | unauthenticated fetches, release manifests, GATE-G3/P32.25 readouts | — (weakest claim beyond public is none) |

**Transition rules** (from research S6 + §55.7, made normative by naming):

- A `fixture` pass cannot silently supersede a `hosted` failure; a `hosted` pass cannot establish
  `public` publication; an `implementation`/`fixture` result cannot close a row whose verification
  column names a higher domain.
- An unavailable domain is reported as **unavailable** (e.g. "composed-db unavailable: no Docker
  daemon") — never as green and never omitted.
- A `live_verification=false` run may *quote* recorded hosted/public evidence with its date and
  revision but claims only `fixture`/`implementation` (and `composed-db` where actually run).
- Coverage/obligation assessments are per-domain: the same requirement can be MET in `implementation`
  and MISSING in `public`; the P32.7 event schema records `(requirement, domain, verdict, revision,
  evidence)` so one domain's verdict never overwrites another's.

## 2. Source funnel — named units

One unit per stage, counted per source (and per target URL for dossier-acquisition rows).
Names follow research S6 ("discovered, reviewed, permitted, mapped, captured, extracted, linked,
published") — the ordering is the funnel direction; authority to advance a unit is named so no
engineering step fabricates a rights decision:

| unit | definition | measured from | authority to advance |
|---|---|---|---|
| `discovered` | a candidate source/target exists in the researched inventory or a gap query emitted it | `docs/build/planning/2026-09-25-six-streams/data/source-candidates.csv` (27 rows); P32.11 gap-query output | any engineering run may add a candidate row |
| `reviewed` | a rights/registry packet exists with a dated review verdict (allow/decline/pending) | `docs/build/reports/rights/**`, `sources.toml [rights]` blocks, `review-status` CLI | the reviewer/operator under HG-03/HG-04; agents record, never decide |
| `permitted` | `sources.toml` row has `ingestion_permitted = true` and the loader gate verdict is LOADABLE | `connectors/src/connectors/data/sources.toml`; `sig-connectors gate` | HG-03 human flip only |
| `mapped` | a class connector + reviewed live target/adapter wired with committed fixtures (shadow diff=0) | `CONNECTOR_FOR_SOURCE`, `live_targets.toml`, fixture runs | engineering (fixture domain) |
| `captured` | source bytes landed in the OCFL capture store with content digests | `evidence_capture`/`evidence_artifact` rows (hosted domain) | a run on the hosted stack or fixture captures in fixture domain |
| `extracted` | claims were emitted from captures through the parser stack | `claim` rows citing the source's captures | same |
| `linked` | claims bound into the graph — envelopes, entity refs, relationship/accountability edges | materializer outputs (`resolution`, `camera_site`, `accountability`, `derived_fact`) | same |
| `published` | the source's eligible records reached a released artifact on the public partition | release manifests + public artifact inventory | GATE-G3 → P32.25 only |

## 3. Baseline values at `c8d72cc` (each labelled with its domain + date)

| unit | value | domain · date · evidence |
|---|---|---|
| discovered | **339** registered `[sources.*]` + **27** researched candidates | implementation · 2026-09-27 · `sources.toml`, `source-candidates.csv` |
| reviewed | rights blocks + disposition artifacts per source (`p293_dispositions.json` validated offline); per-row review depth recorded on the 27 candidates | implementation · 2026-09-27 |
| permitted | **236** `ingestion_permitted = true` (of 339) | implementation · 2026-09-27 · counted from `sources.toml` |
| mapped | 8 accountability sources wired (P31.12/13, shadow diff=0); earlier classes per the P25/P26 chain | fixture+implementation · recorded 2026-09-26 |
| captured | OCFL-backed captures behind every landed claim; per-job counts recorded per run (e.g. ccops 46/42/72 + fema 4,060 records → claims) | hosted · recorded 2026-09-26 (P31.12/13 run ledgers) |
| extracted | 2,074,963 admissible claims on the hosted spine (after P30.2a materialization) | hosted · recorded 2026-09-24 (P30.2a run) |
| linked | 1,872,344 envelopes → 227,998 resolved sites (from 230,330 obs-level records, dedup 0.0101) + 130 relationship edges + 200 derived-fact links | hosted · recorded 2026-09-24/25 |
| published | national surface live: export `sig-2026-09-27-ce480ab1` published to `…-sig-public`, `sig-web` rolled `sha256:d8244804…`, 12 z0–z14 tiles, 178/178 freshness dates | public · recorded 2026-09-27 (P31.16 publish half) |

Units not yet populated for Round-10 work (e.g. `captured` for dossier-acquisition targets) stay
explicitly **0/not-run** in any projection — never inferred.

## 4. Unresolved-flag routing (the "don't lose them" half of D3)

Every still-OPEN P31 flag is routed in §5 of `RECONCILIATION.md` (beside this file); the three
engineering contracts are verified against code in §3 there. Nothing in this document flips a
`permitted` bit, authorizes a fetch, or re-labels a proxy measurement as a live one.
