## Summary

P15.3 lands the **infrastructure map** (§39.3) and the **network explorer** (§39.4) — the two spatial/graph public surfaces — on P15.1's epistemic visual language and zero-JS / a11y / archivability baseline. Every honest-rendering rule is pure, tested logic; the two shipped pages stay zero-JS with a tabular/list equivalent as the source of truth.

Implements spec `docs/tickets/P15.3__map-network.md` (canonical §§39.3, 39.4, 19.4/19.5). TypeScript is confined to `web/` (SIG-ENG-010). Additive: the P15.1 reference map/graph, fixtures, and components are untouched.

## What changed

- **`web/src/lib/map.ts`** — §39.3 rules: the 7 observed + 2 derived layers with derived flagged/separately-toggled (SIG-UI-016); the single control binding coverage to the point layer (SIG-UI-017); the low-coverage≠low-density desaturation/value-suppression encoding (SIG-UI-018); national-zoom binning + per-sensitivity-tier point honesty (SIG-UI-019, SIG-GEO-011); no-coordinate → jurisdiction indicators with a conservation law (SIG-UI-020); ego-default sharing view (SIG-UI-021).
- **`web/src/lib/network.ts`** — §39.4 rules: ego network with expansion (SIG-UI-022); a `CentralityStatistic` that **cannot be constructed without** its inline ER-quality disclosure (SIG-UI-023, SIG-IDENT-030); the three §12.2 access edge types with distinct glyph+dash, independently filterable, unmerged by default (SIG-UI-024); access-path closure with full hop list + per-hop evidence, path-minimum confidence, and speculative-beyond-threshold (SIG-UI-025, SIG-RECON-050), mirroring `inference/src/inference/access_paths.py`.
- **`web/src/lib/map-tiles.ts` + `web/src/pages/map/style.json.ts`** — the static-PMTiles serving contract: a MapLibre GL style over self-hosted PMTiles v3 with OSM attribution and no third-party tile CDN, served at `/map/style.json` and validated at build (SIG-UI-038, SIG-GEO-012/013).
- **`web/src/pages/map.astro`, `network.astro`** — the two zero-JS surfaces (static SVG + the authoritative tabular/list equivalents); OSM attribution rendered into the static HTML (every context incl. print).
- **`web/src/lib/map-network-fixture.ts`** — the worked Oklahoma City fixture (assets across all tiers, a low-coverage vs low-density bin pair, the three access-edge types, centrality stats, and a headline + a speculative access path).
- Wiring: nav links, `tests/e2e/pages.ts` (so the axe sweep covers the new pages), CSS.
- Docs (phase gate): **ADR-051**, plus the P15.3 rows in `docs/traceability.md` and `docs/risk_register.md`, and the ADR index.

## Design decisions

- **Static-PMTiles serving contract, not a bundled renderer (deviation from ADR-018, recorded in ADR-051).** The Lighthouse budget is a hard global CI gate — **0 script bytes**, **≤150 KB** per page — and ADR-049 makes archivability structural. Bundling the maplibre-gl runtime would fail both. ADR-049 explicitly deferred the self-hosted-tiles renderer to P15.3; the closest faithful alternative is to land the **serving contract** (the style + self-hosted PMTiles v3 source + OSM attribution a MapLibre renderer consumes) as a real, fetchable, tested artifact, while the shipped pages stay zero-JS. The requirement under test (SIG-UI-038/SIG-GEO-012/013) is met and machine-verified.
- **ER disclosure is structural, not conventional** — the statistic type cannot exist without its disclosure, so a page can't forget it.
- **Access-path/edge shapes mirror the pipeline** (`ACCESS_KINDS`, `SPECULATIVE_HOP_THRESHOLD = 3`, path-minimum confidence) so the surface presents exactly what the inference layer computes.

## Verification

- `npm run check` (mirror of the CI `web` job): typecheck (0 errors) · **73 unit** tests · build · OSI-licence gate (197 prod deps) · **62 e2e** (chromium render paths + axe **WCAG 2.2 AA** on `/map/` + `/network/` + the JS-disabled no-JS baseline) — all green.
- `npm run check:perf` (Lighthouse): 5 URLs incl. `/map/` + `/network/` — **0 script bytes**, ≤150 KB, perf ≥ 0.9, a11y = 1 — pass. `dist` ships **0 `.js` files**.
- `/map/style.json` verified as valid PMTiles v3 with OSM attribution and self-hosted relative sources.
- Python ADR gate (`tests/unit/test_policy_adrs.py`): 53 passed (ADR-051 valid).

## Acceptance criteria → evidence

| Acceptance criterion | Evidence |
|---|---|
| Every centrality/hub statistic carries an inline ER-quality disclosure (deterministic) | `network.ts::centralityStatistic` (throws without ER) · `network.test.ts` · `map-network.spec.ts` + `.nojs.spec.ts` |
| Coverage underlay bound to the point layer by a single control (deterministic) | `map.ts::POINT_COVERAGE_CONTROL`/`assertCoverageBinding` · `map.test.ts` · `map-network.spec.ts` |
| Low-coverage does not read as low-density, vs a low-coverage fixture (agentic) | `map.ts::coverageEncoding`/`readsAsDensity`/`renderBin`; `LOW_COVERAGE_BIN` vs `LOW_DENSITY_BIN` · `map.test.ts` · `map-network.nojs.spec.ts` |
| No-coordinate assets appear as jurisdiction indicators; none dropped (deterministic) | `map.ts::partitionByLocatability` (conservation) · `map.test.ts` · `map-network.spec.ts` |
| Map has a tabular equivalent; network a list equivalent; both usable no-JS (deterministic) | `map.astro`/`network.astro` · `map-network.nojs.spec.ts` (JS disabled) |
| Public map served from static PMTiles, OSM attribution, no hard third-party CDN (deterministic) | `map-tiles.ts::assertServingContract`; `/map/style.json` · `map-tiles.test.ts` · `map-network.spec.ts` |
| Phase-gate: CI green; new requirements tested; ADR for deviation; traceability + risk register updated | ADR-051; `docs/traceability.md` + `docs/risk_register.md` P15.3 sections; all gates green |

## Requirement IDs

SIG-UI-016, SIG-UI-017, SIG-UI-018, SIG-UI-019, SIG-UI-020, SIG-UI-021, SIG-UI-022, SIG-UI-023, SIG-UI-024, SIG-UI-025, SIG-UI-038, SIG-GEO-011, SIG-GEO-012, SIG-GEO-013, SIG-IDENT-030, SIG-RECON-050.

Generated with [Devin](https://devin.ai)
