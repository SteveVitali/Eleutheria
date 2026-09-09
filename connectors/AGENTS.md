# AGENTS.md — `connectors/` (source connector framework)

## Purpose

The framework and per-source connectors that acquire evidence from external sources and emit claims
(§21): the source registry, the eight-stage pipeline, and connectors for OSM, Flock, Atlas, records,
procurement, France/Belgium, Data Driven, and the broader pathway sources — all behind a fail-closed
ingestion gate. Nearest-file-wins: this file adds to the root `AGENTS.md`.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `connectors/src/connectors/loader.py` | ~170 | the fail-closed ingestion gate (`assert_loadable`) |
| `connectors/src/connectors/cli.py` | ~280 | `sig-connectors` (`validate`, `stages`, `gate`, `run`, …) |
| `connectors/src/connectors/data/sources.toml` | — | the source registry (rights + `ingestion_permitted`) |

## Build & Test

- CLI: `uv run python -m connectors <cmd>` / `sig-connectors <cmd>` (`connectors/src/connectors/cli.py`):
  - `validate` — the registry self-checks that must hold at every phase gate.
  - `stages` — list the eight connector stages in order (§21.1).
  - `list-connectors` — the registered source connectors.
  - `gate --source <id>` — the connector-loader gate verdict for a source.
  - `run --source <id> --mode live|replay|shadow` — drive a connector; `live` refuses (exit 3) a non-green source.
  - `export-check` — the export licence per compartment (SIG-LIC-010).
- Unit/integration tests run under the top-level `make check`: `uv run pytest tests/connectors`.

## Code Conventions

- A new source is a new row in `connectors/src/connectors/data/sources.toml`, left
  `ingestion_permitted=false`; the loader gate decides loadability. Run `sig-connectors validate`
  after registry changes.
- Connectors are exercised over committed fixtures by default; keep parse/extract/normalize pure.

## Critical Gotchas

1. **`ingestion_permitted` defaults false; the loader gate refuses un-reviewed sources.** The loader
   (`connectors/src/connectors/loader.py`, `assert_loadable`) fails closed unless `ingestion_permitted`
   is true **and** the `compact_status`/`custody_posture` permit it; `gate --source <id>` reports the
   verdict and `run --mode live` refuses (exit 3) any non-green source. Never bypass the gate to fetch
   a source — flipping a source is a human/rights decision (**HG-03**), not a code change.
2. **Live fetching is the exception, not the default.** Most connectors run over committed fixtures;
   real external fetches are legally gated. Don't add live network calls to a connector's default/test
   path.
3. **Reconciliation logic is owned elsewhere.** The §29.3/§29.7 sharing-edge + snapshot-diff logic is
   owned by `reconcile` (P08.2); connectors **consume** it and must not re-implement it.

## Terminology

- **Ingestion gate** — the fail-closed loader check (`assert_loadable`) run before any fetch.
- **Compact status / custody posture** — a source's rights state; gate inputs for ingestion.

## Do

- Register a new source in `sources.toml` (left un-permitted) and let the loader gate decide.
- Run `sig-connectors validate` after registry changes; keep fetches behind the gate.

## Don't

- Don't fetch a non-permitted source, bypass the gate, or duplicate reconciliation logic.
- Don't flip a source to `ingestion_permitted=true` in code — that is the HG-03 human gate.
