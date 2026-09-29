# P27 — Public launch-readiness plan (DRAFT — planning artifact, not yet a ratified chain)

> **Status:** planning draft, 2026-09-22. Authored while the P26.18/P26.19 tickets are still in
> flight (another orchestrator owns them). This file is **new build memory** and deliberately does
> **not** touch the shared machine state (`LEDGER.md`, `00_MANIFEST.md`, `BUILD_INDEX.md`,
> `DEFERRALS.md`) — those row appends happen in a coordinated pass once the P26 chain lands.
> Nothing here merges, tags, pushes, flips a gate, or writes to the spine.

## 0. Why this exists

The production public surface (`https://sig-web-…run.app`) renders the **OKC vertical-slice demo**
(fixtures: `sig.example`, frozen `as_of 2026-08-20`, 4 sources, 42 devices, a 2-edge graph) even
though the hosted spine holds ~1.06M claims. This plan turns the demo into a **launch-ready,
data-driven public surface over the real graph**, per the operator's four launch decisions
(2026-09-22):

- **Scope:** broad / national from the bulk data (not OKC-only).
- **Interactivity:** zero-JS static now; interactive map later.
- **Gate boundary:** plan through to the real public cut-over (operator ticks HG-01/HG-11/HG-02).
- **Design:** full launch redesign (ambition high).

## 1. Live spine audit (read-only, 2026-09-22)

Connected to Cloud SQL `zeta-medley-508121-u7:us-central1:sig-pg` via `cloud-sql-proxy` + the
`sig-pg-password` secret, `default_transaction_read_only=on`. Headline facts:

| Fact | Value |
|---|---|
| claims / `claim_evidence` | **1,059,533** / 1,059,533 |
| entities (`entity`) | 92,169 — `entity_type` = `deployment` (92,165) + `organization` (4) |
| sources (`source_registry`) | 210 — **all `ingestion_permitted=true`, all `custody_posture=REFERENCE`** |
| evidence artifacts | 219 (`evidence_artifact`/`_capture`/`_blob`) |
| sensitivity | **every claim `sensitivity_tier = 0`** (public tier) |
| rights | **every claim has a `rights_id`**; 20 distinct `rights_record` rows shared across the 210 sources |

**Publishable licence mix (claims by `rights_record.spdx_expression`):**

| claims | spdx | redistributable | derivative |
|---:|---|---|---|
| 372,869 | LicenseRef-PublicRecord-FactualCompilation | yes | yes |
| **256,172** | **UNDETERMINED** | **UNDETERMINED** | **UNDETERMINED** |
| 225,753 | LicenseRef-OperatorAccepted-DBRight | yes | yes |
| 82,539 | CC0-1.0 | yes | yes |
| 46,992 | CC-BY-SA-2.0 | yes | yes |
| 44,305 | CC-BY-4.0 | yes | yes |
| 12,359 | OGL-3.0 | yes | yes |
| 11,642 | CC-BY-SA-4.0 | yes | yes |
| 5,929 | ODbL-1.0 | yes | yes (own compartment) |
| 640 | LicenseRef-StAlbert-ODL-1.0 | yes | yes |
| 333 | LicenseRef-Peel-ODL-1.0 | yes | yes |

→ **~803k claims (76%) already carry a redistributable licence.** The single blocker is the
**256,172 UNDETERMINED (24%)**, attributed by connector: `procurement` 204,918 + `dot_511` 34,650 +
`france_belgium_procurement` 14,462 + small tails (`data_driven` 1,015, `coarse_international` 851,
`state_statute_seed` 108, `government_mandated_disclosure` 81, …). These are overwhelmingly
government / public-record material — **legitimately resolvable** to a real licence by rights review.

**Claims by connector (top):** `dot_511` 814,066 · `procurement` 204,918 ·
`france_belgium_procurement` 14,462 · `flock_portal` 11,192 · `atlas` 5,373 · `osm` 4,505 ·
`accountability` 2,863 · `data_driven` 1,015 · `coarse_international` 851 · then hundreds.

**Geolocation:** predicates `camera_latitude` / `camera_longitude` (93,305 claims each) hold
coordinates **as text** on **75,479 distinct entities**. Sample: Oregon DOT (TripCheck) camera,
`45.36999 / -122.84318`, jurisdiction `OR`. `camera_jurisdiction` spread is national + international:
FL 12,953 · GA 7,049 · IL 6,383 · CA 6,139 · WA 4,584 · TX 4,000 · MD · IA · OR · **TH 2,111** · DC ·
MO · **GB-ENG 1,776** · **AU-QLD/AU-ACT** · PA · **NZ 1,060** … + **16,859 `unresolved`**.

**The modeling gap (the real work):** these tables are **empty** — `resolution`, `jurisdiction`,
`coverage_record`, `relationship`, `organization_relation`, `physical_asset`, `deployment` (domain
table), `contradiction`, `legal_instrument`, `policy` — and **`value_geom` is unused (0 rows)**.
Entities are bare nodes; all facts (incl. coordinates) live in `claim`. So the map / per-jurisdiction
dossiers / coverage / network the web needs must be **assembled from raw claims** — and nothing has
assembled them yet. The **export build is the right one-time place** to do that aggregation for a
static site.

### Audit caveats
- Rights → source attribution via `rights_id` alone fans out (many sources share one record); use
  `ingest_run.connector_name` for per-source attribution (done above for UNDETERMINED).
- Counts are raw claims, **pre-resolution** — cross-source duplicate cameras (`dot_511` vs `osm` vs
  `atlas` vs `flock_portal`) are **not** deduped yet; "75,479 entities" is observation-level.

## 2. Implications for the plan (vs. the pre-audit sketch)

1. Publishability is in far better shape than the last recorded posture implied — the fix is a
   **bounded rights-review pass** over ~3 connectors, not a 190-source slog.
2. There is a **genuine, launch-worthy national/international camera map + procurement watch** in the
   real data — the "broad" vision is achievable with real bytes.
3. The critical path is a **data-shaping layer** (geometry assembly, per-jurisdiction grouping,
   cross-source resolution/dedup, coverage aggregation), done in the export, **before** any web
   wiring pays off.

## 3. Proposed P27.x tickets

### Data / backend track (frontend-stack-independent)

| # | Ticket | Scope | Depends | Gate |
|---|---|---|---|---|
| P27.1 | data & rights audit → scope memo | Formalize this audit as a repeatable read-only `sig-exports audit` (or `reconcile`) verb + `PUBLIC_SURFACE_AUDIT.md`; freeze the per-page data contracts each web surface consumes. | — | live |
| P27.2 | maximize publishable scope (rights) | Review + record real licences for the UNDETERMINED buckets (`procurement`, `dot_511`, `france_belgium_procurement`, tails) — public-record/factual-compilation/CC0 where the evidence supports it; keep ODbL/CC-BY-SA in their own compartments; **flag `facial_recognition_world_map` + `pathways_*` for explicit operator sign-off**. Never blanket-bypass the gate. | P27.1 | HG-03, HG-02 |
| P27.3 | export data-shaping | Assemble points from `camera_latitude`/`_longitude` (populate `value_geom` / a materialized site view via the normalization path, not a hand-edit); per-jurisdiction grouping from `camera_jurisdiction`; cross-source resolution/dedup (or honest observation framing); coverage aggregation with named denominators. | P27.1 | — |
| P27.4 | spine-backed export bundle | Replace the fixture `_jurisdiction_request` / `build_web_dossiers` with real spine readers; emit the national export: dossier index + per-jurisdiction dossiers, map layer (GeoJSON + PMTiles), sharing-edge network, data-freshness (all publishable sources), coverage metrics, watch/evidence/corrections/research-queue. Fail-closed compartments (ODbL separate). | P27.2, P27.3 | — |

### Frontend track — **DECISION-SPA resolved 2026-09-22 = B (static core + React islands)**

Zero-JS, archivable, WCAG-2.2-AA content core (SIG-UI-036/037 preserved) **plus** cutting-edge
interactive React islands where interactivity earns its JS (map, graph, search). The launch ships the
static core first ("zero-JS now"); the islands are a fast-follow ("interactive later"). React arrives
via `@astrojs/react` (components render to static HTML by default; only islands hydrate), and a new
ADR **extends** ADR-068's island allowance from `/curate/**` to the named public islands.

- P27.5 web data layer + wire all pages to the export (extend `web/src/lib/data.ts` beyond
  dossiers+leverage; convert map/network/freshness/coverage/watch/evidence/corrections/research-queue
  off direct fixture imports; fixtures stay CI default; fail-loud in export mode).
- P27.6 IA + nav redesign + landing + jurisdiction index + design system (grouped nav, real landing,
  per-jurisdiction index, fix hardcoded `/dossier/oklahoma-city/`, reconcile `map`↔`reference-map` /
  `network`↔`reference-graph`, real canonical URL + as-of from the export manifest). Zero-JS content.
- P27.7 empty-states / honest-gap UX / polish at national scale (large-table pagination, "not
  researched" gaps, visual polish). Zero-JS + WCAG-2.2-AA preserved throughout.
- P27.9 interactive React islands (map over PMTiles, network graph, search) with the zero-JS tabular
  fallbacks preserved; the ADR extending the island allowance (revisits A1/SIG-UI-047). Fast-follow.

### Deploy / go-public (both tracks)

| # | Ticket | Scope | Gate |
|---|---|---|---|
| P27.8 | build + deploy from the real export; public cut-over | Deploy builds `web/dist` with `SIG_DATA_SOURCE=export` against the national export; wire into `sig-ops deploy` + Cloud Run/GCS sync + the public export objects; verify hosted; take through the publication gates. | HG-01, HG-11, HG-02 |

### Parallel (not web): widen publishable scope via HG-03 rights flips as needed — quantified by P27.1.

## 4. Decisions (resolved 2026-09-22)

- **Scope = broad/national from bulk data.** **Interactivity = zero-JS now, interactive later.**
  **Gate boundary = go all the way to public** (operator ticks HG-01/HG-11/HG-02). **Design = full
  launch redesign.**
- **DECISION-SPA = B (static core + React islands).** Keeps the archivability/a11y/citation
  guarantees while allowing cutting-edge interactive islands where they earn their JS; the island
  allowance is extended from `/curate/**` to the named public islands via a new ADR (P27.9).

## 5. Coordination

Write only **new** files until the P26 chain lands: the `docs/tickets/P27.*.md` contracts + this
report. Append the manifest/LEDGER/BUILD_INDEX/DEFERRALS rows in a **coordinated pass afterward** so
this planning work never collides with the in-flight P26.18/P26.19 machine-state edits.

## 6. STAGED coordinated build-memory pass — **APPLY ONLY AFTER P26.19 LANDS**

> ⚠️ **REMINDER (owed follow-up):** do NOT apply this while P26.18/P26.19 are in flight — it edits the
> shared machine state the P26 orchestrator owns. Apply once `nextTicket` has advanced past P26.19 and
> the P26 chain tip is settled. This section is the ready-to-paste content so nothing is re-derived.

**6a. `docs/tickets/00_MANIFEST.md` — new round banner + chain rows 117–125** (append after row 116;
format matches the P25/P26 tail `| # | file | phase | kind | lane | scope | gate |`):

> **Round 5 — Public launch readiness (rows 117–125).** Seeded 2026-09-22 by an operator-directed
> planning session (see `docs/build/reports/P27_LAUNCH_READINESS_PLAN.md`; live spine audit + four
> launch decisions + DECISION-SPA=B). **Operator-ratified 2026-09-22.** Turns the fixture demo into a
> data-driven national public surface over the real ~1.06M-claim spine. All rows are Lane **C**
> (new-code contracts); they stack on the P26.19 tip. Per-ticket ADRs land the new normative decisions
> (see §7 of the plan report); the map island is already `SIG-UI-047 (MAY)`.

| 117 | `P27.1__public-surface-audit.md` | 27 | ticket | **C** | **[semantic `LAUNCH.1`]** read-only data & rights audit → `PUBLIC_SURFACE_AUDIT.md` + frozen per-page data contracts + launch-scope memo. | — (read-only; live) |
| 118 | `P27.2__maximize-publishable-scope.md` | 27 | ticket | **C** | **[semantic `LAUNCH.2`]** resolve UNDETERMINED rights (procurement/dot_511/fr-be) via real review; ODbL/share-alike compartmented; Part-VIII classes held for sign-off. | HG-03, HG-02 |
| 119 | `P27.3__export-data-shaping.md` | 27 | ticket | **C** | **[semantic `LAUNCH.3`]** geometry assembly from `camera_latitude/longitude`, jurisdiction grouping, cross-source dedup/resolution, coverage aggregation (materialize vs compute-on-read per P27.1). | — |
| 120 | `P27.4__spine-backed-export-bundle.md` | 27 | ticket | **C** | **[semantic `LAUNCH.4`]** replace fixture `_jurisdiction_request`/`build_web_dossiers` with real spine readers; emit the national export (dossiers/map/network/freshness/coverage/watch/evidence/corrections/research-queue); fail-closed compartments. | — |
| 121 | `P27.5__web-data-layer-wiring.md` | 27 | ticket | **C** | **[semantic `LAUNCH.5`]** route EVERY public page through `web/src/lib/data.ts` (off direct fixture imports); fixtures stay CI default; fail-loud in export mode; zero-JS preserved. | — |
| 122 | `P27.6__ia-redesign-landing.md` | 27 | ticket | **C** | **[semantic `LAUNCH.6`]** grouped nav + national landing + per-jurisdiction index + real canonical/as-of + design system; fix hardcoded OKC link; reconcile map/reference-map. | — (ADR if it supersedes a SIG-UI decision) |
| 123 | `P27.7__empty-states-and-polish.md` | 27 | ticket | **C** | **[semantic `LAUNCH.7`]** empty/partial/gap states, large-table pagination, epistemic legibility at scale, responsive + print, visual QA. | — |
| 124 | `P27.8__deploy-and-public-cutover.md` | 27 | ticket | **C** | **[semantic `LAUNCH.8`]** deploy builds `web/dist` in export mode from the national export; publish only the published compartment; hosted verify; publication package. | HG-01, HG-11, HG-02 |
| 125 | `P27.9__interactive-islands.md` | 27 | ticket | **C** | **[semantic `LAUNCH.9`]** interactive React islands (map/graph/search) over the static core; zero-JS fallbacks preserved; ADR extending ADR-068 (map island already SIG-UI-047). | — (new ADR) |

**6b. `docs/build/LEDGER.md` CURRENT STATE edits:**
- `nextTicket:` → `P27.1` (row 117) once P26.19 lands; note the Round-5 public-launch chain (rows 117–125), operator-ratified 2026-09-22.
- `chainTip:` → P27.1 forks from the settled P26.19 tip (`devin/p26-19-*`); each P27 ticket forks the previous.
- `round:` → add `round 5 = P27 public launch (ratified 2026-09-22)`.
- `projectStatus:` → append a note that the P27 public-launch round is ratified + drafted (rows 117–125), replacing the "drafted manifest exhausted at 116" line.
- **PHASE LOG:** add a `2026-09-22` planning entry — live spine audit (1,059,533 claims / 210 sources; 76% publishable; 75,479 geolocated; modeling tables empty), P27.1–P27.9 drafted, DECISION-SPA=B, no code/gate/flip/spine-write; only new files committed.

**6c. `docs/build/BUILD_INDEX.md`:** no rows in this pass — a BUILD_INDEX row is added per ticket **as it lands** (rows 117–125 fill in during execution), matching the existing convention.

**6d. `docs/tickets/DEFERRALS.md`:** add one tracked row for the **owed spec/ADR work** (see §7) so it
is not lost: `D-P27-SPEC-1` (OPEN) — the Round-5 normative decisions need ADRs + spec_src fold-backs;
homed to P27.1/P27.6/P27.9 as each lands.

## 7. Spec grounding & owed ADRs / spec amendments

The canonical spec (`docs/2_canonical_design_spec.md`) was **not** edited (it is generated from
`docs/research/_meta/spec_src/` via `BUILD.sh`; edits go there + an ADR, SIG-ENG-003). The P27 tickets
**cite** existing, verified anchors. The cross-cutting **new decisions are now recorded as ADRs**
(drafted 2026-09-22, `Accepted`, indexed via `scripts/docs/adr-index.sh`):

| Decision | ADR | Spec status | Owed |
|---|---|---|---|
| Broad/national public surface (vs local-dossier-only) | **ADR-090** | new | §39–41 + §38 spec_src amendment via `BUILD.sh` — lands with P27.4/P27.6 |
| Static core + React islands (DECISION-SPA=B); public-island allowance | **ADR-091** | map island = `SIG-UI-047 (MAY)`; graph/search + budget = new | §40 spec_src amendment extending ADR-068 — lands with P27.9 |
| Export built from the live spine + resolution posture (compute-on-read / observation-level) | **ADR-092** | new (epistemic-honesty relevant) | §29 + §38 spec_src amendment — lands with P27.3/P27.4 |
| IA redesign (nav, landing, index) | (per-ticket) | may supersede a landed SIG-UI decision | ADR iff it changes a landed requirement (P27.6) |
| Maximize publishable scope (mass rights resolution) | (per-ticket) | operational — uses the existing gate (cf. P26.16/GL-GATE-07, ADR-086) | gate disposition + ADR at landing (P27.2), not a spec change |

**What is done vs still owed.** The three cross-cutting ADRs (090/091/092) are written now — each with
a "Proposed spec_src amendment (NOT yet applied)" section stating the exact fold-back — so the tickets
cite a canonical *decision* rather than a planning doc. **Still owed** (tracked as `D-P27-SPEC-1`): the
actual `spec_src` edits + `sh docs/research/_meta/spec_src/BUILD.sh` regeneration + the manifest "Spec
amendments applied" entry — deferred to the implementing tickets under the phase gate (the repo pattern:
a normative spec change is gated, e.g. HG-13 for P20.2, and lands with the code, not in planning). IA
(P27.6) and rights (P27.2) write their own ADRs at landing if they deviate.
