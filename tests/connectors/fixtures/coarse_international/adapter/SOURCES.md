# Fixture provenance — `coarse_international/adapter/` (P25.4)

Real upstream captures (or verbatim excerpts of them) the curated coarse-dataset
adapters are tested against. Retrieval context: laptop egress, 2026-09-15/16,
polite single GETs; the upstream surfaces are public (carnegieendowment.org
robots allows the page + chunks; docs.google.com robots `Allow: /spreadsheet`
covers the gviz `out:csv` route).

| Fixture | Upstream | Fidelity |
|---|---|---|
| `carnegie_index.html` | `https://carnegieendowment.org/features/ai-global-surveillance-technology` (301 target of `…/publications/interactive/ai-surveillance`) | The page's 28 `/_next/static/chunks/*.js` `<script src>` links **verbatim**; surrounding markup trimmed (the discovery surface is what the adapter consumes). |
| `carnegie_chunk.js` | `https://carnegieendowment.org/_next/static/chunks/02dsg86hwl1n3.js` | The embedded country dataset array `h=[{arrayItem:!0,…},…]` **verbatim** (75 country entries — the dataset facts); surrounding minified component/module code trimmed (not re-hosted). |
| `carnegie_chunk_lib.js` | same page, a non-data chunk | Representative excerpt — carries no `{arrayItem:!0,` marker; exercises the `js_asset` zero-claim path. |
| `frwm_sheet_*.csv` (6 files) | `https://docs.google.com/spreadsheets/d/157mTA67QAMxb0N4e7tO755r9uw2wsaT1z2rcCO1hPIU/gviz/tq?tqx=out:csv&gid=<gid>` — the sheet the FRWM page links via `bit.ly/TheFacialRecognitionWorldMap` | Verbatim gviz CSV per continent sheet: `north_america` gid 689675349 · `south_america` 520821635 · `europe` 102380128 · `me_central_asia` 2060189382 · `asia_oceania` 1320430692 · `africa` 0. 194 data rows total; Egypt appears twice (Middle East & Central Asia + Africa) with disagreeing statuses — an upstream contradiction both rows keep. |
| `carnegie_chunk_drift.js` | synthetic | Marker present, entry shape broken — ContentDrift path. |
| `frwm_drift_header.csv` / `frwm_unknown_country.csv` / `frwm_unknown_status.csv` / `frwm_person_column.csv` | synthetic | Header drift, unmapped country, unmapped status, forbidden per-person column — the fail-closed paths. |
