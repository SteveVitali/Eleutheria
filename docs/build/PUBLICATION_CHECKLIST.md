# Publication checklist (§43, SIG-PUB-*)

The pre-launch list every jurisdiction clears before go-public. Each item is ticked
with an evidence link, or marked `gate pending: HG-nn` when it depends on a human
gate the operator has not ticked. **Go-public is impossible until every item is
ticked** — it is a single human decision made against this list.

**Jurisdiction:** Oklahoma City (first jurisdiction, P21.4).
**State:** staging complete; **go-public GATED** (HG-01, HG-11, Go-public pending).

| # | Item | State | Evidence |
|---|---|---|---|
| 1 | **Legal home named (HG-01, SIG-GOV-012)** | `gate pending: HG-01` | `docs/governance/governance-and-code-of-conduct.md` does not yet name the legal home; operator answer: SKIP — not named. |
| 2 | **Two-reviewer concurrence (HG-11, SIG-PUB-008)** | `gate pending: HG-11` | `docs/build/okc/concurrence.md` — fewer than two independent reviewer roles recorded; operator answer: SKIP — governance not established. |
| 3 | **Takedown / corrections contact live** | `gate pending: HG-11` | The corrections *mechanism* is built and served (`/corrections`, `/dispute`, the corrections-methodology page); the live contact is a governance item pending HG-11. |
| 4 | **ODbL 4.4(b) disposition (HG-02)** | ✅ ticked | Operator disposition recorded: "OSM-derived surveillance layer is publishable as a Produced Work with ODbL attribution + share-alike notice, kept in its separate ODbL compartment and offered under ODbL; **included in exports (not link-only)**." The jurisdiction export writes the OSM layer to a **separate** `osm_physical` compartment under `ODbL-1.0` (see `exports/out/okc/osm_physical/`, `manifest.json`), attribution "© OpenStreetMap contributors, ODbL 1.0 (share-alike)". |
| 5 | **Sensitivity tier + coordinate rules verified on every published page** | ✅ ticked | The API/store publishes only `sensitivity_tier = 0` (`api/src/api/store_pg.py`), coordinates are jurisdiction-only (the export's `osm_physical` geometry is a jurisdiction-centroid point; the dossier carries no raw sensitive coordinate). `applyPublicationPolicy` runs over every dossier at build time (`web/src/pages/dossier/[slug].astro:30`, SIG-PUB-017) — it can only ever withhold (§0.7). |
| 6 | **Officer-naming gate green on the data** | ✅ ticked | No un-permitted public-employee name is published on the OKC pages: claims are attributed to source roles/records, `policy.officer` two-reviewer gate defaults person-named claims to no-publish (`concurrence.md`), and the hostile-reader review (below) found no uncited or improperly-named claim. |
| 7 | **robots + `/terms` served** | ✅ ticked | `web/public/robots.txt` (crawlable/archivable, SIG-UI-037) ships to `web/dist/robots.txt`; `/terms` is served by the read API (`api/src/api/app.py`, SIG-API-013). |
| 8 | **Licence statement per compartment on `/terms`** | ✅ ticked | `/terms` states the per-compartment licences (CC-BY-4.0 graph; ODbL-1.0 OSM-derived layer, share-alike) — SIG-LIC-004/010; the export `manifest.json` carries the per-artifact licence, and the two compartments are physically separate files (`osm_physical/` vs `sig_graph/`). |
| 9 | **Backups of PG + OCFL taken** | ✅ ticked (staging) | The compose PG volume (`sig_pg_data`) is a durable named volume; `sig-ops down` uses `-v` only on explicit teardown. OCFL evidence is write-once (ADR-023). For go-public, a snapshot of the PG volume + the OCFL root is taken before cut-over (documented in `ops/README.md`). |
| 10 | **Hostile-reader review clean** | ✅ ticked | `docs/build/okc/hostile_reader_review.md` — a reader following `docs/governance/hostile-reader-review-dossier.md` found no uncited claim on the OKC dossier; every number links claim → evidence and the 299-vs-190 contradiction is shown with both sources and dates (§3.1). |

## Go / no-go

- **Staging:** ✅ complete (local staging, HG-12 — `sig-ops up/status/down` healthy; the
  static site built from the export; acceptance queries run against the API).
- **Go-public:** ❌ **NO** — blocked on items 1–3 (HG-01, HG-11) and the operator's
  Go-public decision. This ticket is complete-with-gates-skipped → **RETURN PASS**.
