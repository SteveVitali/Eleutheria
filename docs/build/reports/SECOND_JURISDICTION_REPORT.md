# Second-jurisdiction report — France (Commune de Gex, vidéoprotection)

> P24.6 — JURIS.2 / GL-JURIS-01. The second jurisdiction is the design's proof,
> not a copy (D7): this report records what the adapter framework needed —
> and what it did not — to carry a second jurisdiction end to end over fixtures.

## Decision recorded at build time (spec defers final selection, non-blocking)

**Jurisdiction: France — Commune de Gex, département de l'Ain (vidéoprotection).**
Rationale: §52 Phase 18 names France "the recommended first non-US adapter"; the
committed P18.2 test vectors already exercise Gex / Préfecture de l'Ain, so the
slice is grounded in recorded fixtures rather than invented data; and the shapes
are the ones the US baseline lacks — authorization by published **arrêté
préfectoral** (dated, five-year renewable), procurement by **DECP national open
data** (not municipal portals), records regime **fr.cada** (never `us.foia` —
SIG-ONTO-068). Belgium was the weaker candidate (its camera register is eID-walled
`no_equivalent_available` — a true known-complete-unknown but less pipeline to
exercise). If the operator selects otherwise, the dispatch tables make it a data
row. Recorded in **ADR-079**.

## Sources and rights posture (no flip, `provided: no`)

| source | connector | compact / custody | rights | packet |
|---|---|---|---|---|
| `raa_prefectures` | `france_belgium_records` | public_terms_only / REFERENCE | ODbL-1.0 recorded | `docs/build/reports/rights/raa_prefectures.md` |
| `decp_fr` | `france_belgium_procurement` | public_terms_only / REFERENCE | UNDETERMINED (Licence Ouverte 2.0 — no accepted SPDX; counsel-needed) | `docs/build/reports/rights/decp_fr.md` (new) |
| `madada` | `france_belgium_records` | not_contacted / LINK | UNDETERMINED | `docs/build/reports/rights/madada.md` (new) |
| `declarationcamera_be` | `france_belgium_records` | not_contacted / LINK | UNDETERMINED | Belgium — out of the France slice; HG-04 work |

All stay `ingestion_permitted=false`; every live run is refused exit 3 (HG-03).
`provided: no` — no live content fetched for any source this run.

## The run (fixture/shadow — NO live fetch)

`bash docs/build/tools/run_france.sh` over local Docker staging (2026-09-14):

| stage | outcome |
|---|---|
| `sig-ops up --jurisdiction france --seed` | PG18+PostGIS up; **11 claims, 4 entities** seeded |
| shadow: `raa_prefectures` | **10 claims, diff=0** (arrêté → `fr.arrete_prefectoral`, sunset derived 2031-02-01) |
| shadow: `decp_fr` | **26 claims, diff=0** (2 marchés; accord-cadre → `cooperative_piggyback` + `parent_cooperative_contract`) |
| shadow: `madada` | **REFUSED at the loader gate** — `compact_status=not_contacted` (recorded, honest) |
| `sig-resolution match --jurisdiction france` | **1 PROPOSED** org match → PG review queue |
| `reconcile resolve --jurisdiction france` | deployment_exists/authorization_state/statutory_citation/implements_technology/procurement_state/contract_value/contract_signed_date **RESOLVED**; the §11.14 predicates (`instrument_type`/`enacting_body`/`sunset_date`/`acquisition_method`) recorded "predicate not in resolver ruleset — skipped" |
| `sig-exports build --jurisdiction france` | 11 artifacts; compartments `osm_physical` (ODbL) + `sig_graph` (CC-BY); dossier `gex-videoprotection`; **DECP content absent** (`UNRESOLVED` dossier gap — the gate exercised, not bypassed) |
| empty PMTiles | no OSM device layer imported → honest empty tile set (`sig-exports tiles`) |
| web build (`SIG_DATA_SOURCE=export`) | **53 pages** incl. `/dossier/gex-videoprotection` (+ its JSON); officer-name row renders **withheld** under FR-GDPR |
| acceptance `live_api_france.py` | **7 pass / 3 blocked / 0 failed** — fixture subset all pass; traversal pass |

Artifacts: `docs/build/reports/france/acceptance_2026-09-14.json`,
`docs/build/reports/france/connector_runs_2026-09-14.txt`, `exports/out/france/`.

## France's own acceptance queries (not relabelled OKC ones)

- **FR-1** «La vidéoprotection est-elle autorisée ?» → `authorization_state` =
  `authorized` (the arrêté is the dated authorization — not a contract). PASS.
- **FR-2** legal regime → `statutory_citation` = CSI L251-1 à L255-1. PASS.
- **FR-3** deployment attested → `deployment_exists` = true. PASS.
- **FR-4** marché notifié → `contract_value` = 50754 on
  `contract:france:decp-2025kazvs0000000` (in the spine; excluded from the export
  while rights are UNDETERMINED). PASS.
- **FR-5** operating organization → `/v1/search?q=france` hits the police-municipale
  projections. PASS.
- **FR-6** technology → `implements_technology` = `camera-fixed-cctv`. PASS.
- **FR-7** Part VIII → dossier flags `isPublicEmployeeName`/`originJurisdiction:FR`;
  `adapter_publication_permitted(FR)=False` (SIG-PUB-017; the US dossier publishes
  the equivalent row). PASS.
- **FR-8/9/10** (RAA corpus, Ma Dada register, commune OSM layer) — `blocked`,
  HG-03-pending, with the exact flip+live commands recorded.

## Part VIII on the new jurisdiction's data

- The signing-officer row names the office ("M. le préfet de l'Ain"), never a
  person, and is withheld at build under FR-GDPR (verified in `dist/`).
- The ODbL compartment stays separate (`legal_instruments` under `osm_physical/`).
- No plate/person/trip/biometric data anywhere in the slice (pinned by
  `test_france_slice_has_no_part_viii_forbidden_data`).
- DECP content excluded until the LO 2.0→SPDX disposition resolves (HG-03,
  counsel-needed flag in the packet).

## OKC-specific assumptions surfaced — dispositions

| # | assumption | disposition |
|---|---|---|
| 1 | `sig-ops seed`/`up --seed` refused non-`okc` | generalized — `_SEED_SLICES` dispatch (`okc` path byte-identical) |
| 2 | `sig-exports build --jurisdiction` refused non-`okc` | generalized — `_jurisdiction_request` dispatch |
| 3 | `build_web_dossiers` refused non-`okc` | generalized — `_france_dossier()` |
| 4 | `tests/acceptance/live_api.py` is OKC-shaped | a parallel France module (D7 — own queries, not a parameterization) |
| 5 | `CONNECTOR_FOR_SOURCE` lacked france_belgium ids | added (4 data rows) |
| 6 | jurisdiction filters are `ILIKE '%<j>%'` substring | retained; subjects pinned to carry the token (test) — RISK-P24-04 |
| 7 | `web/src/lib/data.ts` appends FR/BE demo dossiers | pre-existing, unchanged; export mode uses the real export |
| 8 | §11.14 predicates outside the resolver ruleset | recorded; skipped by `reconcile resolve`, 404 on `/v1/resolution`; material facts use registered predicates |
| 9 | the web build requires `web/tiles/*.pmtiles` | `run_france.sh` step 6b renders the honest empty tile set (no OSM layer imported) |

## Per-jurisdiction hacks required — none, recorded exceptions

The adapter framework needed **no per-jurisdiction hack** beyond data rows: the
seed/export/dossier/connector seams are dispatch tables. The recorded exceptions
(in the ADR + script comments): (a) the empty-tile step in `run_france.sh` is an
honest artifact step, not a code hack; (b) `madada`'s compact-gate refusal is a
recorded blocker, not a workaround; (c) the ILIKE jurisdiction filter stays a
convention — RISK-P24-04.

## Owed operator work (gates — nothing fabricated)

- **D-JURIS.2-1** (HG-03): flip the three France sources after their reviews
  resolve (the LO 2.0 disposition is counsel-needed) + the real LIVE fetches.
- **D-JURIS.2-2** (HG-04): Stage-0 outreach to the FR source operators (+ the
  Belgium packet if Belgium lands).

No source was flipped, no live fetch performed, no green fabricated.
