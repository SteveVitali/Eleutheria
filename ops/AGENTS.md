# AGENTS.md — `ops/` (runtime composition)

## Purpose

`sig-ops` is the SIG **runtime composition** command (ADR-066): it stands the whole system up as a
service on one small machine (the zero-cost posture, SIG-STORE-003) — **not** a test suite. The
stateful piece (PG18+PostGIS with the real sqitch plan) runs from `ops/docker-compose.yml`; the read
API (uvicorn) and the static `web/dist` server run as host processes. Nearest-file-wins: this file
adds to the root `AGENTS.md`. See `ops/README.md` for the operator runbook.

## Key Files

| File | Lines | Purpose |
|---|---|---|
| `ops/src/ops/cli.py` | ~500 | `sig-ops` (`up`, `status`, `down`, `seed`, egress/swh sub-commands) |
| `ops/src/ops/seed.py` | ~160 | load a jurisdiction slice into the spine via `db.claim_sink.PgClaimSink` |
| `ops/src/ops/egress.py` | ~120 | egress accounting / `egress-report` |
| `ops/src/ops/degraded.py` | ~80 | the degraded / keepalive posture |
| `ops/src/ops/swh.py` | ~85 | Software Heritage `swh-save` |
| `ops/docker-compose.yml` | — | the PG18+PostGIS service (with sqitch deploy on start) |
| `ops/config.toml` | — | runtime config (staging endpoints, tasks/contribution gates) |

## Build & Test

- CLI: `uv run python -m ops --help` / `sig-ops up --jurisdiction okc` / `sig-ops status` /
  `sig-ops down` / `sig-ops seed --jurisdiction okc`.
- `sig-ops up` **needs a running Docker daemon** (it brings up the compose PG service).
- Tests run under the top-level `make check`: `uv run pytest tests/ops` (they don't require Docker).

## Code Conventions

- Host endpoints default to local and are overridable by env (the HG-12 local-staging default);
  never bake host-specific values into the image.

## Critical Gotchas

1. **`sig-ops up` requires Docker; `sig-ops down` must leave nothing behind.** `up` stands up the
   compose PG service (+ sqitch deploy) and launches the API + static host processes; `down` runs
   `docker compose down -v` and stops the host processes, leaving **no** containers or stray
   processes. A missing daemon makes `up` fail — that is expected, not a bug to work around.
2. **`seed` is append-only.** It loads slice claims through `PgClaimSink` (insert-only); it never
   updates or deletes spine rows.
3. **Runtime, not tests.** `sig-ops` is for standing the system up; don't route test logic through it.

## Terminology

- **Compose PG** — the stateful PG18+PostGIS container defined in `ops/docker-compose.yml`.
- **Degraded mode** — the low/zero-cost keepalive posture (SIG-GOV-021).

## Do

- Use `sig-ops up/status/down` to run a local jurisdiction; keep endpoints env-overridable.
- Add ops sub-commands as additive CLI verbs with `tests/ops` coverage.

## Don't

- Don't leave containers/processes running after `down`; don't add write paths that mutate the spine.
- Don't hard-code hosting-specific values (HG-12 is an operator decision).
