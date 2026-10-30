# ADR-229: The basemap pipeline — `sig.basemap-lock/1`, generated styles, self-hosted glyphs, the context fallback, and the R2 host posture

- **Status:** Proposed (agent-drafted; implements MAP-02's half of ADR-156 §Decision 6)
- **Phase:** Round 11 / P36 / sub-round 11C
- **Ticket:** P36.33 (manifest row 374; run ledger `docs/build/runs/P36.33.md`)
- **Written:** 2026-10-30 (`date -u`; Devin sub-agent — agent-drafted, labelled)
- **Implements:** ADR-156 §Decision 6 (the self-hosted basemap direction it framed for MAP-02); carries the answered plan cells verbatim — **D-K1-1** (basemap yes), **Q-31/D-K1-2 [A-3] = a** (basemap on R2 after the DNS move, OP-09), **D-K1-3 [B-22] = as recommended**. **Extends ADR-223**'s CSP policy by K0 §4.8's own `connect-src 'self' <SIG tile origin>` row. **Cites:** SIG-UI-100 (owned), SIG-UI-039/040, SIG-ENG-042, SIG-STORE-003, ADR-156/223/155/160, K1 §2, K0 §4.8.

## Context

ADR-156 recorded the basemap *direction* (self-hosted Protomaps OSM extract on a SIG-controlled origin, reversing Round-9 Q8 at U-003.1) and deferred the pipeline + host to MAP-02. The unanswered shape questions — pin record, flavour picks, glyph origin, serving keys, the kill switch, the header posture — are this row's owned decisions.

## Decision

1. **`sig.basemap-lock/1`** (`ops/basemap.lock.json`) is the single pin: the reference build (`20260930.pmtiles`, measured in K1 §2.1 — 138.5 GB, z0–15, schema 4.15.2 — now rotated upstream and kept as the sizing reference, never a fetchable pin), the upstream index/archive bases, the style package (`@protomaps/basemaps` 5.7.2, BSD-3 — the v4↔5.x pairing verified against its emit), the glyph + context declarations, the host block, the serving flag, the refresh policy and the cost posture.
2. **Generated styles, not shipped JS.** `web/scripts/gen-map-styles.mjs` emits `style-light.json` (grayscale flavour), `style-dark.json` (black) and `style-context.json` under `web/public/map/` from the pinned package — flavours picked from K1's own candidates ("grayscale or white" / "black or dark") so SIG's data hue carries the meaning. K1's keep/drop list is applied: `address_label` + `roads_shields` + `roads_oneway` dropped (POI-class and the only sprite-requiring layers — **no sprite sheet is served**), every `icon-image` reference stripped, `buildings` ≥ z15, `roads_labels_major` ≥ z13, `lang: "en"`. The generated files are committed and `--verify`ed in the web gate.
3. **Glyphs same-origin.** Noto Sans Regular + Italic — the fontstacks the emitted styles name — are fetched, sha256-manifested (`sig.basemap-glyphs/1`) and committed under `web/public/map/fonts/` with `OFL.txt`, so `/map/fonts/{fontstack}/{range}.pbf` works on every posture (incl. basemap-down and the context fallback) and never needs a second origin.
4. **`context.pmtiles` (`sig.context-tiles/1`)** — the K1 §2.6 boundaries fallback built by `sig-ops basemap context-build` from JUR-01's boundary pack (P35.17): country/state/county outlines + place-name points, z0–10, public domain, served same-origin — never the basemap host.
5. **The R2 host** (queued): `sig-basemap` on `tiles.surveillancegraph.org`; versioned keys `basemap/<build>.pmtiles`; `Cache-Control: public, max-age=31536000, immutable`; CORS `GET, HEAD` from the site origins with `Range` allowed and `Content-Range`/`ETag`/`Content-Length` exposed. The named OM-20 create (GATE-G5 listed) is `prepared_not_executed` — hosted creds + OP-09 absent — and re-runs as `D-P36.33-1`.
6. **Budget alert + kill switch.** `ops/basemap.alert.json` (`sig.basemap-alert/1`) declares the Cloudflare usage-billing thresholds and the two-level switch: the SIG-side flip — one committed `serving.active_source → context` (`sig-ops basemap kill-switch`) repoints every generated style at the boundaries fallback — and the provider-side domain disable (operator act).
7. **CSP `connect-src`** admits `https://tiles.surveillancegraph.org` — K0 §4.8's literal `<SIG tile origin>` row inside ADR-223's meta ∩ header split; first-party, T0 pages lose the directive anyway.

## Consequences

- Positive: the pipeline is pinned, verified and regenerable; the map can draw the basemap the moment the host exists; the fallback needs no second origin.
- Negative: +$2/mo steady-state (SIG-STORE-003 posture, far inside the $300 cap); a second origin in CSP; upstream daily-build rotation means the served build is pinned at refresh time, not in-repo.

## Revisit trigger

1. Basemap hosting costs more than $25/month, or egress abuse is observed (ADR-156's trigger stands too).
2. Protomaps rotates the v4 schema or the `5.x` style package; the pairing must be re-verified.
3. The operator declines the R2 posture or moves the tile origin off Cloudflare.
4. A future ticket needs sprites, POIs, or a third fontstack — each is a lock + style regeneration, never an ad-hoc add.
5. `context.pmtiles` must carry more than boundaries + names (e.g. terrain or water fills).
