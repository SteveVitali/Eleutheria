# Frozen per-page data contracts (P27.1, LAUNCH.1)

The **stable interface the rest of the P27 chain inherits**: the data shape each of the ten public
web surfaces consumes. `docs/build/reports/public_surface_contracts.schema.json` is the machine
artifact (JSON Schema draft 2020-12); this file is its human companion.

- **P27.4 (LAUNCH.4) EMITS** these shapes from the real spine (replacing the fixture
  `_jurisdiction_request` / `build_web_dossiers`).
- **P27.5 (LAUNCH.5) RENDERS** them (routing every page through `web/src/lib/data.ts` off direct
  fixture imports; fixtures stay the CI default; fail-loud in export mode).

**These shapes are largely count-independent** — the OSM land (D-SOURCES.17-1) and the P27.2 rights
pass change the row *values*, not the contract. The audit snapshot moves; these contracts do not. Each
surface names its **source-of-truth TypeScript interface** (`x_source` in the schema) so a drift check
can assert the export still matches what the web renders.

Authority: the interfaces under `web/src/lib/*.ts` and their `*-fixture.ts` exemplars, plus the SIG-UI
`/v1` dossier contract (§39). Nothing here is a new normative decision — it freezes what already exists
so downstream tickets code against a fixed contract rather than re-deriving it.

| # | Surface | Page(s) | Source-of-truth interface | Producer (export) | §/SIG-UI |
|---|---|---|---|---|---|
| 1 | **Dossier index / landing** | `/`, `/dossier` | `dossier.ts#Dossier[]` (index: slug/subject_label/jurisdiction/asOf) | `exports.web_dossier.build_web_dossiers` → `web/dossiers.json` | §39.2 |
| 2 | **Per-jurisdiction dossier** | `/dossier/[slug]` | `dossier.ts#Dossier` (12 sections) | same; publication gate applied at build (§43.8) | §39.2, SIG-UI-010..015, SIG-PUB-017 |
| 3 | **Map layer** | `/map` (`reference-map`) | `map.ts#MapLayer` / `MapAsset` / `JurisdictionIndicator` | GeoJSON + PMTiles (**ODbL compartment SEPARATE**) + tabular equivalent | §39.3, §19.4/§43.3 |
| 4 | **Network** | `/network` (`reference-graph`) | `network.ts#NetworkNode` / `NetworkEdge` / `AccessPath` | sharing-edge export | §39.4, §12.2, SIG-UI-024/025 |
| 5 | **Data-freshness** | `/data-freshness` | `metrics.ts#FreshnessRow[]` | per-source freshness roll-up | §32.4, SIG-METRIC-006/007 |
| 6 | **Coverage** | `/coverage` | `metrics.ts#CoverageMetric[]` | named-denominator coverage metrics | §32.5, SIG-METRIC-008/009/010 |
| 7 | **Watch** | `/watch` | `watch.ts#ContractWatchItem[]` | renewal/contract watch | §39.5, SIG-UI-026/027 |
| 8 | **Evidence** | `/evidence`, `/evidence/[id]` | `recommender.ts#EvidenceArtifact[]` + `evidence-viewer.ts#ClaimView`/`Capture` | recommender + viewer export | §39.5a/§39.6, SIG-UI-027b/028/030 |
| 9 | **Corrections** | `/corrections` | `corrections.ts#CorrectionEntry[]` + `TransparencyReport` | corrections log + transparency counts | §39.8, SIG-GOV-005/011 |
| 10 | **Research queue** | `/research-queue` | `research-queue.ts#ResearchTaskCard[]` | task-catalog export | §39.7, SIG-UI-031, SIG-TASK-002 |

## Invariants the contracts bake in (do not relax downstream)

- **Never a bare total (§32/SIG-METRIC-008/009/010).** Every `CoverageMetric` carries a REQUIRED named
  `denominator`, a `population_note`, and `is_population_total: false`. The forbidden-denominator guard
  (`assertCoverageMetric`) rejects "reality"/"all …". A count without a named denominator is not
  publishable.
- **Coordinate reduction by sensitivity tier (§19.4/§43.3, Part VIII §0.7).** `MapAsset.tier ∈ {0,1,2,3}`
  drives precision; `lat`/`lon` are nullable — a tier-3/mobile/unknown asset publishes NO point, only a
  `JurisdictionIndicator` roll-up. No per-person or per-plate field appears in any surface.
- **Contradictions stay visible (§3.1, §29.1).** `Figure.contested` / `ClaimView.conflicting_claims`
  preserve disagreement; a within-predicate conflict is never collapsed to one value.
- **Gaps are first-class (§9.5).** `Row.absence` / `Gap.kind` are one of the four absence kinds
  (NOT_RESEARCHED / NO_EVIDENCE_FOUND / UNRESOLVED / NOT_APPLICABLE); a `null` value renders "unknown",
  never omitted (SIG-UI-015). This is what lets the national surface show its honest coverage gap.
- **The three access-edge types MUST NOT be merged (§12.2, SIG-ONTO-042).** `NetworkEdge.access_kind ∈
  {configured_access, observed_use, declared_policy}`. Access paths carry per-hop evidence — an
  unexplained hop is a forbidden edge (SIG-UI-025).
- **Sealed evidence is metadata-only (§17.5).** `Capture.storage_tier = 'sealed'` ⇒ no `document_text`,
  a `sealed_reason` present.
- **History is never rewritten (SIG-GOV-005).** `CorrectionEntry.previous_value` stays citable at its
  `previous_belief_date`.

## Snapshot-dependent notes (from the P27.1 audit — provisional, re-audit required)

- The **map layer** currently has NO assembled geometry: `claim.value_geom` = 0 rows and the
  `physical_asset`/`deployment` modeling tables are empty. The map's `MapAsset[]` must be assembled from
  the `camera_latitude`/`camera_longitude` claims in **P27.3** (via the normalization path, not a
  hand-edit) before P27.4 can emit a non-fixture map layer.
- **Coverage** (§32.5) has no `coverage_record` rows yet — until P27.3 populates them, coverage can only
  honestly report "researched vs not-yet-researched", not "known-absent".
- **Dossier index** at national scale is a set of per-jurisdiction dossiers grouped from
  `camera_jurisdiction`; the large `(null)`/`unresolved` bucket must be surfaced, not hidden.
