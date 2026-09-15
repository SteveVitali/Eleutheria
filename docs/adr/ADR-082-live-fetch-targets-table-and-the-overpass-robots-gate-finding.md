# ADR-082 — Live fetch targets as a declarative table (`data/live_targets.toml`), and the Overpass robots-gate finding

- **Status:** Accepted
- **Phase / ticket:** P24.1 live deploy follow-on (DEPLOY.1 / GL-DEPLOY-01) → closes the P21.3 deliverable-4 target gap; opens P25.1 (live-fetch operationalization)
- **Date:** 2026-09-15
- **Related:** P21.3 (`live-connector-wiring` — deliverable 4 named the OSM Overpass query + doc URLs but the runner shipped a placeholder), P23.5 / ADR-074 (the OKC document connectors), `docs/tickets/DEFERRALS.md` D-P21.3-1 / D-LIVE.1a-1, SIG-INGEST-037 / §26 (crawler conduct: robots + no circumvention, RISK-P0-06), SIG-INGEST-045i (a connector never enumerates targets itself), §42.3 (ODbL compartment), HG-09 (secrets env-only); the defining standard.

## Context

The live runner (`connectors.runner._run_live`) was structurally complete — gate → `PoliteFetcher`/`HttpxTransport` → OCFL capture → claim sink — but it built its fetch target as a **placeholder** (`https://<source>/x`) and never populated `ctx.parameters["targets"]`, so a green source fetched nothing. The committed fixtures encode connector *responses*, not *request targets*, so there was nowhere the real per-source targets lived. P21.3 deliverable 4 named them in prose (the OKC-bbox Overpass query; the document URLs) but they were never made data.

## Decision

Add a declarative **`connectors/src/connectors/data/live_targets.toml`** — one row per source, read by a single `connectors.live_targets.live_targets(source_id)` (mirroring the `_data.load_table` pattern; targets are DATA, not code, SIG-ENG-001). `_run_live` now loads it and passes `{"targets": …}` into the `RunContext`; a green source with **no** row raises `NoLiveTargets` (CLI exit 4) rather than fetching a placeholder. The first row is `osm_overpass` (kind `overpass`): the OKC-metro-bbox `man_made=surveillance` query, whose response matches the committed fixture shape so the existing parser is unchanged and output stays in the ODbL compartment. Endpoints/tokens are resolved from the environment at call time (`$SIG_OVERPASS_ENDPOINT`, HG-09), never stored in the table.

## Consequences

- The placeholder gap is closed; the live path is driven by reviewed data + covered by tests (`tests/connectors/test_live_targets.py`, network-free).
- **Finding (recorded, not worked around):** a real live run — `sig-connectors run --source osm_overpass --mode live` against the default public endpoint — is **refused by SIG's own conduct layer**: `overpass-api.de`'s `robots.txt` disallows `/api/`, and `PoliteFetcher` honours robots with no circumvention (SIG-INGEST-037). So the OSM live fetch is **not** blocked on plumbing but on a **policy/endpoint decision**: either point `$SIG_OVERPASS_ENDPOINT` at a robots-permitting instance (self-host / a permitting mirror), or record a rights determination that documented, rate-limited API use is distinct from crawling. This is deliberately an operator/policy call, not a code bypass — opened as **P25.1**.
- The document connectors (`okc_procurement`/`okcpd_policy`/`ok_statute`, `okc_council`) additionally need content-drift handling (live PDF/HTML ≠ the hand-transcribed fixtures) before their live targets are wired — also P25.1.

## Revisit trigger

Revisit if: the operator provides a robots-permitting Overpass endpoint (or the rights determination) so the OSM live fetch can run and this records its evidence; **or** P25.1 lands document-connector content-drift handling and adds their `live_targets.toml` rows; **or** the target schema needs a non-overpass/non-document kind (e.g. an authenticated API target), at which point the `live_targets` reader grows that kind.
