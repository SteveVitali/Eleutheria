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

---

## 2026-09-10 re-run (LIVE.2 / GL-LIVE-02, prepare-only) — re-verified gate state

*(Lane-B re-run of the same P21.4 contract on branch `devin/p21-4-live2-rerun`;
append-only. Environment clock read 2026-09-13, so the regenerated evidence files
carry that stamp — the run itself is the chain's LIVE.2 pass.)* The local composed
staging path was re-run **for real** over Docker (`sh docs/build/tools/run_okc.sh`
end-to-end: `sig-ops up` → shadow/fixture connectors → resolution → reconcile →
export → `SIG_DATA_SOURCE=export` web build → J-1 + Q-1…Q-13 against the running API →
`docs/build/reports/okc/acceptance_2026-09-13.json`). Every gate is re-stated at its
**current** posture below; each gated item reads ticked or `gate pending: HG-nn` with
the exact command/action that satisfies it.

| # | Item | Current state (2026-09-10 re-run) | What satisfies it |
|---|---|---|---|
| 1 | **Legal home named (HG-01)** | `gate pending: HG-01` — **INTERIM posture only** (GL-GATE-01, P23.2/HUMAN-H1): "SIG operates as an independent open-source project under maintainer stewardship pending a formal legal-home designation." This is an engineering/interim disposition, **NOT counsel and NOT a real named home**. `D-P21.4-1` OPEN. | Operator names a real legal home in `docs/governance/governance-and-code-of-conduct.md` (SIG-GOV-012); then tick. Required **before** Go-public. |
| 2 | **Two-reviewer concurrence (HG-11)** | `gate pending: HG-11` — **OWED / not established** (P23.2/HUMAN-H1): no two named reviewer roles with written concurrence. `docs/build/reports/okc/concurrence.md` is a template only. `D-P21.4-2` OPEN. | Operator establishes two independent reviewer roles + written concurrence + a live takedown/corrections contact; fill `concurrence.md` (`ReviewerConcurrence`, SIG-PUB-008); then tick. |
| 3 | **Takedown / corrections contact live** | `gate pending: HG-11` — mechanism built + served (`/corrections`, `/dispute`, corrections-methodology page, re-verified in this run's e2e), live contact still owed with HG-11. | Governance item; ticks with HG-11. |
| 4 | **ODbL 4.4(b) disposition (HG-02)** | ✅ ticked — **INTERIM engineering disposition** (GL-GATE-02, P23.3/HUMAN-H2; **pending counsel**). OSM-derived layer IS included in the export in its **separate ODbL compartment** with attribution + share-alike (re-verified: export `licenses: ["CC-BY-4.0","ODbL-1.0"]`, `exports/out/okc/` two-compartment layout). | Real counsel opinion (`D-LEGAL.1-1` OPEN) supersedes the interim disposition before real public exposure. |
| 5 | **Sensitivity tier + coordinate rules verified on every published page** | ✅ ticked (Part VIII, binding) — `policy.publication` runs over the export at build; re-verified by the export-mode e2e (dossier.spec.ts, a11y + render), coordinates jurisdiction-only, tier-0 only published. | — |
| 6 | **Officer-naming gate green on the data** | ✅ ticked (Part VIII, binding) — no un-permitted public-employee name published on the OKC pages; re-verified by the export-mode e2e (jurisdiction.spec.ts name-withholding) + hostile-reader review. | — |
| 7 | **robots + `/terms` served** | ✅ ticked — re-verified in the export web build (`web/dist/robots.txt`; `/terms` served by the read API). | — |
| 8 | **Licence statement per compartment on `/terms`** | ✅ ticked — CC-BY-4.0 graph + ODbL-1.0 OSM-derived layer (share-alike), SIG-LIC-004/010; two compartments physically separate in the export. | — |
| 9 | **Backups of PG + OCFL taken** | ✅ ticked (staging) — durable named PG volume; OCFL write-once. Pre-cutover snapshot procedure documented in `ops/README.md`. | Real snapshot taken by the operator at Go-public. |
| 10 | **Hostile-reader review clean** | ✅ ticked — `docs/build/reports/okc/hostile_reader_review.md`; the 299-vs-190 contradiction shown with both sources + dates (§3.1); re-verified this run (contradiction survives to the export-built dossier HTML). | — |

**Re-verification evidence (2026-09-10 re-run):** `sig-ops up/status/down` healthy/clean;
`run_okc.sh` complete (acceptance **2 pass / 11 blocked / 0 failed**, J-1 pass, Q-6 confirms
299-vs-190 CONTESTED/UNRESOLVED); `npm run test:e2e` **192 passed in BOTH fixtures and export
modes**; `check:perf` budgets hold; `SIG_REQUIRE_DB_TESTS=1 make check` **2767 passed, 2 skipped,
0 failed**; `make docs-check` exit 0; `check-build-memory.sh .` no violations.

**Go / no-go (unchanged):** Staging ✅ complete (local, HG-12). **Go-public ❌ NO** — reserved to
the human (GL-GATE-05 / GATE-G2 / P23.6); genuinely gated on a **real** HG-01 legal home + HG-11
governance. `D-P21.4-1/2/3` stay OPEN. No live fetch (HG-09 tokens + network absent); no public
cut-over; no `0.2.0` bump. → **RETURN PASS**.
