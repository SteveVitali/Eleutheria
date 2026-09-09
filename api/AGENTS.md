# AGENTS.md — `api/` (the read API + curation service)

## Purpose

The FastAPI **read** surface over the claim spine (§37): as-of queries, dereferenceable resolution
envelopes, sensitivity-tiered views. It also hosts the **authenticated curation app** — a *separate*
app/process that is never mounted on the public API (Part VIII §0.7). Nearest-file-wins: this file
adds to the root `AGENTS.md`.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `api/src/api/app.py` | ~100 | the public read-API FastAPI app factory |
| `api/src/api/routes.py` | ~450 | read routes (as-of, dereference, terms, prohibitions) |
| `api/src/api/store_pg.py` | ~600 | `PgReadStore` — read-only view over the PG spine |
| `api/src/api/store.py` | ~300 | the in-memory demo store the CLI serves by default |
| `api/src/api/curation.py` | ~680 | `create_curation_app` — the gated, loopback-only write surface |
| `api/src/api/tiers.py` | ~70 | sensitivity-tier filtering applied at the view layer |
| `api/src/api/cli.py` | ~100 | `sig-api serve` / `serve-curation` entry point |

## Build & Test

- CLI: `uv run python -m api --help` / `sig-api serve` (public read API over the demo store),
  `sig-api serve-curation` (curation app; exits 3 unless `SIG_CURATION_ENABLED=1`).
- Tests run under the top-level `make check`: `uv run pytest tests/api`.
- The `PgReadStore` path is exercised by the Docker-gated DB/e2e suites (`make test-db`,
  `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e`).

## Code Conventions

- FastAPI dependency markers (`Depends`/`Query`/`Header`) are call-in-argument-default **by design**;
  ruff `B008` is configured to allow them (`pyproject.toml`). Follow the existing route idiom.
- Responses are typed Pydantic models; read routes never mutate the spine.

## Critical Gotchas

1. **The curation app must never be public.** `create_curation_app` is a *separate* FastAPI app on a
   *separate* loopback-bound process; with `SIG_CURATION_ENABLED` unset it carries **no**
   `/v1/curation/*` routes at all (404, not merely guarded). Never mount curation routes on the
   public read app — it is a Part VIII §0.7 breach (RISK-P21-10). Tests pin route absence.
2. **Reads are read-only.** `PgReadStore` never writes; contradictions and dispositions are
   compute-on-read, not stored mutations. Don't add a write path here.
3. **Sensitivity tiers are enforced at the view layer** (`tiers.py`), backed by RLS in `db/`. A route
   that bypasses the tier filter can leak a coordinate the sensitivity matrix forbids.

## Terminology

- **As-of query** — a read pinned to a valid-time / decision-time point.
- **Dereference** — resolve an envelope/entity id to its current resolved view.

## Do

- Add read routes as typed FastAPI handlers with tier filtering; test under `tests/api`.
- Keep the curation surface auth-gated and loopback-only.

## Don't

- Don't mount curation on the public app or add write paths to the read API.
- Don't bypass tier filtering or query the spine outside `PgReadStore`.
