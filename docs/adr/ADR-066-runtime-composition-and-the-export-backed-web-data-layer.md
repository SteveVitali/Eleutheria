# ADR-066 — Runtime composition (`sig-ops`) and the export-backed web data layer

- **Status:** Accepted
- **Phase / ticket:** P21.4 — First real jurisdiction end to end (Oklahoma City)
- **Date:** 2026
- **Related:** ADR-001 (PG18+PostGIS), ADR-023 (OCFL), ADR-032/050 (dossier),
  ADR-059 (PgClaimSink/PgReadStore/compute-on-read), ADR-061 (jurisdiction render),
  ADR-065 (live connector wiring); LD-V08; RISK-P21-06/07; SIG-STORE-003.

## Context

Through P21.3 SIG existed as a set of packages that a **test suite** wired together
(the composed `tests/e2e` run). It had never been stood up as a **service**: no
command brought up the PG spine + API + static site together, and the web shell
rendered only from committed TypeScript fixtures (`web/src/lib/*-fixture.ts`) — the
seam recorded as `LD-V08` ("web reads fixtures, not exports"). P21.4 runs one real
jurisdiction end to end and deploys to staging, which forces two decisions.

Two constraints shape them: the **zero-cost posture** (SIG-STORE-003 — SIG must run
on one small machine, no cloud-specific config), and **no green sources** on this
build (HG-03 was skipped in P21.3), so the first-jurisdiction run is fixture-backed
and must never be described as "live".

## Decision

**1. Runtime composition lives in `ops/` as `sig-ops`.**
`ops/docker-compose.yml` owns the stateful piece — a `postgis/postgis:18-3.6` claim
spine with the real `db/sqitch.plan` deployed on start (mounted read-only; the
volume is mounted at `/var/lib/postgresql` for the PG18 layout). The read API
(`uvicorn`) and the static server for `web/dist` are launched by `sig-ops up` as
**host processes** — the HG-12 local-staging default (uvicorn + a static file
server) — so they run the host's toolchain at HEAD without baking a
platform-specific image. `sig-ops {up,status,down,seed}`: `down` stops the host
processes and runs `docker compose down -v`, leaving no containers. `seed
--jurisdiction okc` loads the committed OKC slice through `db.claim_sink.PgClaimSink`
(append-only, idempotent) — above all the 299-vs-190 `claimed_device_count`
contradiction. Staging endpoints default to local and are overridable by
`SIG_STAGING_{DSN,API_URL,STATIC_URL}`.

*Rejected:* containerising the API + static site (a Python/Node image). It buys
little on one machine, is platform-fragile (a host venv cannot run in a linux
container), and needs network installs. The stateful DB is the only piece worth a
container; the rest are host processes the operator already has.

**2. The web reads through `web/src/lib/data.ts`, switched by `SIG_DATA_SOURCE`.**
`fixtures` (the DEFAULT, so CI is unchanged) returns the committed typed fixtures;
`export` reads the `sig-exports build --jurisdiction <j>` output directory at BUILD
time (`web/dossiers.json` — the `/v1` dossier contract). Every dossier surface reads
through `getDossiers()`. It is build-time only (Node `node:fs`), so the zero-JS
budget is unchanged; `export` mode fails LOUD if an artifact is missing (never a
silent fall-back to fixtures — that would fabricate green). This crosses `LD-V08`:
the OKC dossier renders the 299-vs-190 contradiction from the export bytes.

**3. `sig-exports build --jurisdiction <j>` emits the web dossier bundle.**
Alongside the licence compartments (ODbL `osm_physical` + CC-BY `sig_graph`, kept
physically separate — §42, HG-02) it writes `web/dossiers.json`. The OKC bundle is a
pure function of the committed slice (no green sources → not a live fetch), so the
site builds identically from fixtures or the export.

## Consequences

- One command (`docs/build/tools/run_okc.sh`) drives the whole staging path; P21.8
  reuses it for the next jurisdiction.
- The site and the export agree by construction (§38.1) — the dossier is no longer a
  hand-kept parallel of the export.
- **Export freshness** becomes load-bearing (a stale export = a stale page):
  RISK-P21-06 (build timestamp / as-of banner on every page).
- **Staging exposes real-shaped data before the go-public gates** (HG-01/HG-11):
  RISK-P21-07 (staging is local / access-restricted; go-public is a separate human
  decision, gated).
- `@types/node` is added to `web/` devDependencies (build-time file reads); it is a
  dev-only type stub (MIT), not a runtime/shipped dependency, so the zero-JS and
  licence gates are unaffected.

## Revisit trigger

Revisit when any of the following fires (SIG-STORE-007):

- **A source is flipped green (HG-03)** and a real live fetch begins — the
  fixture-backed `seed`/`shadow` posture of `run_okc.sh` is replaced by live ingest,
  and the "not live" framing here no longer holds.
- **Go-public is approved (HG-01 + HG-11 ticked)** — the local-only staging posture
  (RISK-P21-07) is replaced by a real host/DNS cut-over (P21.5 infra), which may
  warrant containerising the API/static tier rather than running them as host
  processes.
- **The single-machine / zero-cost posture (SIG-STORE-003) is outgrown** — if the
  jurisdiction count or data volume exceeds one small machine, the compose topology
  (single PG, host-process API/static) is redesigned (object store / CDN / tiles —
  P21.5), and this ADR's "no cloud-specific config" decision is revisited.
- **The web needs export data beyond dossiers** (map tiles, network, evidence) read
  through `data.ts` in `export` mode — the current `getDossiers()`-only export seam
  is extended, and the fixture-passthrough for the other surfaces is reconsidered.
