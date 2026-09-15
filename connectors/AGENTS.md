# AGENTS.md — `connectors/` (source connector framework)

## Purpose

The framework and per-source connectors that acquire evidence from external sources and emit claims
(§21). Includes the source registry, the eight-stage pipeline, and connectors for OSM, Flock, Atlas,
records, procurement, France/Belgium, and the broader-pathway sources.

## Build & Test

- CLI: `uv run python -m connectors <cmd>` / `sig-connectors <cmd>` (`connectors/src/connectors/cli.py`):
  - `validate` — the registry self-checks that must hold at every phase gate.
  - `stages` — list the eight connector stages in order (§21.1).
  - `list-connectors` — the registered source connectors.
  - `gate --source <id>` — the connector-loader gate verdict for a source.
  - `export-check` — the export licence per compartment (SIG-LIC-010).
- Unit/integration tests run under the top-level `make check`.

## Critical gotchas

1. **`ingestion_permitted` gates acquisition.** Sources are declared in
   `connectors/src/connectors/data/sources.toml` with an `ingestion_permitted` flag; the loader gate
   **REFUSES** a source that is not permitted (`gate --source <id>` reports the verdict). Never
   bypass the gate to fetch a source — flipping a source to permitted is a human/rights decision, not
   a code change.
2. **Live fetching is the exception, not the default.** Most connectors are exercised over committed
   fixtures; real external fetches are legally gated and land in later (P21) tickets. Don't add live
   network calls into a connector's default/test path.
3. **Reconciliation logic is owned elsewhere.** The §29.3/§29.7 sharing-edge + snapshot-diff logic is
   owned by `reconcile` (P08.2); connectors **consume** it and must not re-implement it.

## Do / Don't

- **Do** register a new source in `sources.toml` and let the loader gate decide; run
  `sig-connectors validate` after registry changes.
- **Don't** fetch a non-permitted source or duplicate reconciliation logic.
