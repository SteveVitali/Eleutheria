# ADR-067 — Zenodo deposits, object store/CDN, tile generation, mirrors, and degraded mode

- **Status:** Accepted
- **Phase / ticket:** P21.5 — Infrastructure, deposits, tiles
- **Date:** 2026
- **Related:** ADR-015 (evidence store on S3/CloudFront + Object Lock), ADR-018 (MapLibre
  map), ADR-048 (bulk exports: computed-licence compartments, reproducible releases,
  egress-friendly distribution), ADR-051 (the static-PMTiles serving contract + the zero-JS
  map), ADR-066 (runtime composition + export-backed web); LD-F07/LD-H08 (tile-generation
  handoff), LD-F09 (MapLibre), LD-P06/LD-P07 (infra accounts, zero-cost keepalive),
  LD-V07 (Zenodo dry-run); RISK-P0-07 (egress), RISK-P0-12 (degraded mode),
  RISK-P21-08/09; SIG-STORE-003/004/005, SIG-GOV-021/022/023/024, SIG-EXPORT-002/008/009,
  SIG-LIC-004, SIG-UI-038, SIG-GEO-012/013.

## Context

Through P21.4 SIG published a real jurisdiction to **local staging**: a reproducible bulk
export, a static site built from it, and a claim spine behind the read API. What was still
missing was the infrastructure the spec promises *around* the graph — the parts that make
it **citable, distributable, mirrored, and survivable**: a Zenodo deposit with a concept
DOI (§38.2), bulk exports on an object store behind a cache with an egress alarm (§38.5),
real rendered vector tiles for the map (the orphaned LD-F07/LD-H08 handoff), mirrors +
Software Heritage for succession (§46.5), and a tested degraded-but-alive zero-cost mode
(SIG-GOV-021).

Two hard gates shape this ticket:

- **HG-07 (accounts):** no Zenodo / object-store / Software Heritage credentials are
  available on this run. Every credentialed integration therefore runs in **dry-run /
  sandbox-stub** and is recorded `gate pending: HG-07` — never faked as done (§3.1, no
  synthetic certainty).
- **HG-12 (budget):** the **zero-cost posture** (SIG-STORE-003) is binding. No paid
  infrastructure is provisioned; CDN/object-store config are **templates only**.
- **Amendment A1 (from P20.2):** **A1 is ticked** — the zero-JS static map stays as the
  conforming default. This ticket **does not** build the MapLibre progressive-enhancement
  island (deliverable 4 is skipped) and does **not** raise the `/map/` script budget.

## Decision

**1. Zenodo deposit over an `httpx` transport, dry-run by default.**
`exports.zenodo.ZenodoHttpTransport` implements the `ZenodoTransport` seam over `httpx`
(the real deposition flow: create → PUT metadata → upload to the bucket → publish).
`sig-exports deposit --in <export>`:
- with **no `--sandbox`** → an offline dry-run (`FakeZenodoTransport`, production-shaped
  DOIs); production deposit is an operator-only action, out of scope here;
- with **`--sandbox --dry-run`** → an offline dry-run using the sandbox `10.5072` prefix;
- with **`--sandbox`** (no `--dry-run`) → a **real sandbox deposit** requiring
  `SIG_ZENODO_SANDBOX_TOKEN`; absent, it exits **4** (`gate pending: HG-07`) and writes
  nothing.
Every deposit is recorded append-only in `docs/build/DEPOSITS.md`, whose `environment`
column marks `dry-run` / `sandbox` / `production`. The deposit carries the per-compartment
licence in its metadata (SIG-LIC-004, §42): the OSM-derived layer's ODbL 1.0 and the SIG
graph's CC-BY-4.0 are both spelled out. `CITATION.cff` (root) travels with the deposit and
takes the concept DOI once minted.

**2. Object store = Cloudflare R2; AWS S3 + CloudFront (ADR-015) is the documented
alternative.** The CLI already named `cloudflare-r2:sig-bulk`; ADR-015 named S3/CloudFront
for the **evidence** Object-Lock store. This ADR **reconciles** them: the *bulk-export*
store is **Cloudflare R2** — chosen because egress is the existential cost of a bulk-data
project (RISK-P0-07) and R2 has **zero egress** (`exports.distribution.EGRESS_CLASS`); a
metered-egress provider *fails the build* (SIG-EXPORT-008). S3 + CloudFront stays the
**documented alternative** and remains the store for the ADR-015 evidence corpus (Object
Lock / WORM), which R2 does not need to replace. `sig-exports push --store` uploads under
**content-hash keys** (append-only, never overwritten — P1–P3) with an immutable
`Cache-Control`, so a CDN caches objects forever (the cheapest egress profile). `boto3`
(already an ADR-015 dependency) is reused; the push *policy* is tested against a fake S3
client — **no live store** this run (HG-07). `sig-ops egress-report` reads
`ops/config.toml`'s documented budget and alarms non-zero on a real breach; with no live
usage API it reports `gate pending` rather than fabricating a measurement (RISK-P21-09).
A `.torrent` (pure-Python bencode, no daemon) is produced per bulk artifact as the
**zero-egress peer mirror** (SIG-EXPORT-009).

**3. Tile generation closes LD-F07/LD-H08.** `sig-exports tiles --in <geojson> --out
<pmtiles>` renders a GeoJSON point layer to a real PMTiles v3 archive: **tippecanoe** when
it is on `PATH`, else a self-contained **pure-Python Web-Mercator → MVT + PMTiles v3
writer** for small extents (the OKC point layer is tiny — a single `z0` tile carries every
point). Either path preserves the layer's **ODbL licence + OSM attribution** in the archive
metadata (ADR-048, §42). The jurisdiction export renders the ODbL layer to
`web/tiles/sig-infrastructure.pmtiles`; the web build **in `export` mode** copies it into
`/tiles/…`, so the map's self-hosted PMTiles source (SIG-UI-038, `/map/style.json`)
resolves to a real rendered archive. This does **not** re-open the client-JS question: the
served map stays zero-JS (ADR-051), and **A1 is ticked** so no MapLibre island is built.

**4. Mirrors + Software Heritage for succession (SIG-GOV-022/023/024).**
`ops/mirrors.toml` is the mirror manifest (Zenodo, object store, BitTorrent, Software
Heritage, git forge — "no sole home", SIG-STORE-004/005). `docs/build/SUCCESSION.md`
documents what is deposited where and how to rebuild the site from Zenodo + the repo in ≤10
steps. `sig-ops swh-save` builds a Software Heritage "save code now" request (public API, no
token needed for a public repo); it is **implemented but untriggered** this run
(`gate pending`: no public repo URL saved).

**5. Degraded-but-alive mode + a monthly keepalive (SIG-GOV-021, RISK-P0-12).**
`sig-ops degraded` builds the fully static site with **no API** — a pure function of
committed bytes (ADR-066), with each dynamic page carrying its last-export as-of banner. It
**fails loudly** if it cannot rebuild. `.github/workflows/keepalive.yml` (monthly + manual)
runs exactly `sig-ops degraded`, so a free scheduler that silently disables dormant
workflows is caught by a **red build**, not a dead site (*"a sustainability plan that fails
silently is not a plan"*). Documented monthly cost: **$0 beyond the static host**.

## Consequences

- SIG is now **citable** (concept/version DOI logic, sandbox-ready), **distributable**
  (content-hash object keys + CDN template + `.torrent`), **mapped** (real rendered tiles),
  **mirrored** (manifest + SWH request), and **survivable** (tested degraded mode +
  keepalive) — each done for real on the free paths, or blocked with the exact missing
  credential on the credentialed ones.
- **RISK-P21-08:** a sandbox DOI (`10.5072/…`) is not a production DOI (`10.5281/…`);
  `DEPOSITS.md` marks the environment so a sandbox identifier is never cited as production.
- **RISK-P21-09:** the egress alarm threshold is documented but untested against a real
  bill; the ADR-015 revisit trigger now has an instrument (`sig-ops egress-report`).
- **Gate-status:** HG-07 credentialed steps (real sandbox deposit, live object-store push,
  triggered SWH save) are `gate pending`; HG-12 zero-cost posture is honoured (templates
  only); **A1 is ticked — no MapLibre island.** The ticket returns PASS with the HG-07
  credentialed steps pending.

*Rejected:* (a) making S3 the bulk store — its metered egress is the exact failure mode
SIG-EXPORT-008 guards against; (b) a dynamic tile server — a hard third-party dependency
SIG-UI-038 forbids; (c) shipping the MapLibre island — A1 is ticked and the zero-JS map is
the conforming default; (d) recording the dry-run/sandbox integrations as "done" — that
would fabricate green (§3.1), so they are `gate pending: HG-07`.

## Revisit trigger

Revisit this decision when any of the following holds:

- **HG-07 credentials arrive.** When a Zenodo (production) token, object-store keys, or a
  Software Heritage token become available, the gate-pending integrations run for real: a
  production deposit mints a `10.5281/…` concept DOI (recorded in `DEPOSITS.md`, promoted
  into `CITATION.cff`), `sig-exports push` writes to the live store, and `sig-ops swh-save
  --now` saves the repo — at which point this ADR is revisited to confirm the object-store
  and CDN choices against real behaviour.
- **The egress alarm fires against a real bill (RISK-P21-09).** The first real invoice from
  the object store lets the documented `ops/config.toml` budget be tuned; if egress on the
  chosen zero-egress store is ever metered or the threshold proves mis-set, revisit the
  store choice (R2 vs the S3/CloudFront alternative) and the threshold.
- **The pure-Python tiler outgrows small extents.** If a jurisdiction's device layer is too
  large for the single-`z0` pure-Python fallback (multi-zoom tiling needed) and tippecanoe
  is not available on the deploy target, revisit the tile-generation path.
- **Amendment A1 is unticked.** If A1 is ever reversed, revisit to build the MapLibre
  progressive-enhancement island and the documented `/map/` lhci override.
- **The keepalive fails to prevent dormancy.** If the monthly `keepalive.yml` is itself
  disabled by the scheduler despite the cadence, revisit the keepalive mechanism (e.g. an
  external cron/ping) — the decay path SIG-GOV-021 warns about.
