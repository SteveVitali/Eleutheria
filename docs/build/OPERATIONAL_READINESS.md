# OPERATIONAL_READINESS — capability × {code, rights, infra, human} + the critical path (P20.1, Phase F)

The document the operator reads to decide **what to unblock next**. It turns
`DECISION_MEMO.md` §6 into a checkable map: for each capability, what the *code* does today
(from `COVERAGE_MATRIX.csv` / `CAPSTONE_CLOSURE.md`), what *rights* state its sources are in
(live `uv run sig-connectors validate`, 2026-09-08), what *infra* it needs, and which *human gate*
(HG-nn, role not name — Part VIII §0.7) unblocks it. Backlog ids (`BL-nnn`) reference `BACKLOG.csv`.

Baseline at the chain tip `devin/p19-5-capstone-gap-closure`: `make check` green (2417 passed, 1 xfailed —
`LD-V08` → P21.4); `PgClaimSink` + `PgReadStore` + ER-over-PG wired (P19.4/P19.5). **Nothing is deployed.**

---

## (a) Capability map

### Ingest — one row per connector (9). Live rights counts from `uv run sig-connectors validate` (2026-09-08)

Every connector is **built and fixture-tested** through the eight-stage framework (§21) but has
**never fetched a live source** (LD-V03): `ingestion_permitted` defaults false and is a tested runtime
gate (`test_ingestion_gate.py`). Registry-wide today: 109 sources, 87 UNDETERMINED, **0 permitted, 0
loadable**. Per-connector, over that connector's own source set:

| connector | code state | rights (permitted / UNDETERMINED / loadable of N) | infra needed | human gate | first target | owning ticket |
|---|---|---|---|---|---|---|
| osm | built; fixture-tested; no live Overpass fetch (LD-F03) | 0 / 0 / 0 of 6 (SPDX ODbL-1.0) | live HTTP transport + OCFL CaptureStore | HG-03 flip + HG-02 (ODbL 4.4(b)) | OKC (`osm_overpass`) | P21.3 (BL-023); rights P21.1 (BL-032) |
| atlas | built; fixture-tested; no live fetch (LD-F03/RISK-P4-10) | 0 / 2 / 0 of 3 | live HTTP transport + OCFL CaptureStore | HG-03 | OKC | P21.3 (BL-023) |
| audit_structural | built; fixture-tested; aggregates-only (§43.6) | 0 / 0 / 0 of 3 (AGPL hazard `sm_alpr`, CC0) | none live (structural) | HG-03 | n/a (later) | P21.3 (BL-023/BL-024) |
| flock_portal | built; fixture-tested; no live `/api/v1/data` (RISK-P11-05) | 0 / 2 / 0 of 5 (CC-BY-SA compartment) | live transport + snapshot diffing | HG-03 + HG-04 (Stage-0) | OKC (`deflock_repo`) | P21.3 (BL-024); rights P21.1 (BL-032/033) |
| accountability | built; fixture-tested; no live Atlas/CourtListener (RISK-P13-07) | 0 / 3 / 0 of 3 | live transport | HG-03 | n/a (later) | P21.3 (BL-024) |
| procurement | built; fixture-tested; only P07.3 USAspending traced live (LD-X08) | 0 / 9 / 0 of 9 | live transport for the 9 APIs (RISK-P7-15) | HG-03 | OKC (`okc_procurement`, `okc_council`) | P21.3 (BL-023/024); rights P21.1 (BL-032) |
| records | built; fixture-tested; no live MuckRock token mint (RISK-P7-10) | 0 / 3 / 0 of 3 | live transport + token (HG-09) | HG-03 + HG-09 | OKC (`journalrecord`, `oklahoman`) | P21.3 (BL-024) |
| france_belgium_procurement | built; fixture-tested; `ingestion_permitted=false` by design (RISK-P18-06) | 0 / 1 / 0 of 1 | live transport (DECP) | HG-03 (design-gated) | n/a (P21.8) | P21.8 (BL-042) |
| france_belgium_records | built; fixture-tested; `ingestion_permitted=false` by design (RISK-P18-13) | 0 / 2 / 0 of 3 (RAA ODbL) | live transport + arrêté-PDF extraction | HG-03 (design-gated) | n/a (P21.8) | P21.8 (BL-042) |

### Other capabilities

| capability | code state | rights/data state | infra needed | human gate | first target | owning ticket |
|---|---|---|---|---|---|---|
| resolve (ER) | ER over PG wired: `sig-resolution match/review decide --dsn` (P19.5) | gold set seeded by judgement, not EM-estimated (RISK-P5-05) | PG18 | — | OKC | closed-by:P19.5 (BL-017); calibration BL-044 |
| reconcile | value objects + minimal count reconciliation; not persisted to PG (LD-D07) | — | PG18 (materialise) | — | OKC | P21.2 (BL-004/027) |
| tasks | detector catalog + task engine in memory (RISK-P10-07/08) | — | PG18 (persist) | — | OKC | P21.2 (BL-004/027) |
| API | `PgReadStore` over PG (16 methods, P19.4); rate limit is metadata-only (RISK-P14-09) | — | PG18 + one small VM/container | HG-12 (hosting) | OKC | closed-by:P19.4 (BL-015); rate-limit BL-031 |
| exports | export gate honours `derivative_permitted` (P19.5); tables caller-supplied, not projected from a live store (RISK-P14-18) | ODbL split computed; Zenodo = FakeZenodo (RISK-P14-16) | object store + Zenodo | HG-07 | OKC | P21.4 (BL-008); deposit P21.5 (BL-029) |
| web | zero-JS Astro shell; jurisdiction-conditional render (P19.5) but reads committed TS fixtures, not the live `/v1` API (RISK-P15-07) | — | static host | HG-12 | OKC | P21.4 (BL-007); map spec P20.2 (BL-010) |
| contribution-back | contributor + leverage modelled in memory; no live MapRoulette/OSM feed (RISK-P16-14) | — | MapRoulette/OSM accounts | HG-08 + HG-10 | later | P21.7 (BL-039/040/041) |
| international adapters | jurisdiction-adapter framework + FR/BE claim shape; no live connector (RISK-P18-05) | `ingestion_permitted=false` by design | live transports | HG-03 | later | P21.8/P21.9 (BL-042/043) |

---

## (b) Minimum viable live slice — Oklahoma City (J-1)

The smallest end-to-end that puts one real jurisdiction live (`DECISION_MEMO.md` §6 step 4).

- **Sources (8, added as 6 OKC registry rows + rights packets in P21.1):** `deflock_repo`,
  `okc_procurement`, `okc_council` (CivicClerk), `okcpd_policy`, `ok_statute`, `journalrecord`,
  `oklahoman`, and `osm_overpass`. At least `okc_procurement`, `okc_council`, `okcpd_policy`,
  `ok_statute` (public government records, R1/R2) and `osm_overpass` (ODbL) must reach
  `ingestion_permitted=true` for `loadable now ≥ 5` (HG-03; ODbL export stays link-only until HG-02).
- **Connectors:** `flock_portal`/`atlas` (`deflock_repo`), `procurement` (`okc_procurement`,
  `okc_council`), `records` (`journalrecord`, `oklahoman`, `okcpd_policy`, `ok_statute`), `osm`
  (`osm_overpass`).
- **Tables:** the append-only `claim` spine + `resolution` (ER over PG), the OCFL `evidence` store,
  the identity registries (`entity` / surrogate `entity_id`), `graph_annotations`
  (compute-on-read until P21.2 materialises), and the projected `ExportTable`s.
- **Pages:** the J-1 dossier, the OKC map/network view, the coverage/methodology page, the
  corrections log, and the task-intake page — built from the live `/v1` API/exports (P21.4),
  not committed fixtures.

---

## (c) Critical path to one jurisdiction live — no placeholders

`DECISION_MEMO.md` §6 re-verified against the current matrix/closure. Each step names its `ticket:`
and a `proof:` command/artefact. `⧗` marks a human action (the gate that unblocks it). There are no
unresolved placeholders below; the only unknowns are the *dates* of the `⧗` human actions.

1. **Memory committed.** `ticket:` P19.1. `proof:` `git ls-files docs/build docs/tickets | wc -l` ≥ 72.
2. **Capstone: verdict matrix + composed stack + spine wiring + closure.** `ticket:` P19.2 → P19.3 → P19.4 → P19.5. `proof:` `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra` = 0 failed, 1 xfailed (`LD-V08` → P21.4); `CAPSTONE_CLOSURE.md` §(e) HG-14 signed (⧗ **HG-14**, done 2026-09-08).
3. **Backlog + readiness.** `ticket:` P20.1. `proof:` `python docs/build/tools/check_backlog.py` exits 0 (`risk deferred rows: 100/100`, `ADR revisit triggers: 61/61`, `LD rows: 90/90`, `duplicate sources: 0`).
4. **Spec reconciled + integration plan.** `ticket:` P20.2 (⧗ **HG-13** normative amendments) → P20.3 (plan only; merges nothing). `proof:` `sh docs/build/tools/merge_dryrun.sh` exits 0; `INTEGRATION_PLAN.md` §(d) complete.
5. **OKC registry rows + rights packets + flips.** `ticket:` P21.1. `proof:` `uv run sig-connectors validate` shows `loadable now ≥ 5`. ⧗ **HG-03** (reviewer flips `ingestion_permitted`) + ⧗ **HG-04** (Stage-0 outreach recorded).
6. **Annotations persisted (if not ACCEPTED-away) + live transports behind the gate.** `ticket:` P21.2 → P21.3. `proof:` `LIVE_WIRING_REPORT.md` lists each flipped source with a fetch timestamp, a capture digest, and claim count > 0. ⧗ **HG-09** (any token as an env secret).
7. **Full OKC run from live data → staging.** `ticket:` P21.4. `proof:` `FIRST_JURISDICTION_REPORT.md` with the acceptance-query outputs (the 299-vs-190 contradiction stays visible) and Lighthouse/axe results from a staging URL. ⧗ **HG-12** (a host).
8. **Public publish.** `ticket:` P21.4 publish step. `proof:` `PUBLICATION_CHECKLIST.md` fully ticked, then DNS → public. ⧗ **HG-01** (legal home), ⧗ **HG-11** (two named reviewers concur; takedown/corrections contacts live), ⧗ **HG-02** (counsel disposition on ODbL 4.4(b); until then the OSM-derived layer is link-only/not exported).
9. **Sustained operation.** `ticket:` P21.5 (Zenodo deposit ⧗ **HG-07**, tiles, mirrors, degraded mode), then P21.6–P21.9 widen the surface. `proof:` Zenodo concept DOI recorded; `sig-connectors validate` degraded-mode keepalive test green (BL-030).

---

## (d) Human-gate checklist HG-01..14 — what unblocks it, and who (role, never a private individual)

| gate | what it unblocks | what unblocks it | who (role) | backlog |
|---|---|---|---|---|
| HG-01 | naming a legal home before public launch | fiscal sponsor / nonprofit identified, recorded in `docs/governance/` | project maintainer + legal counsel | BL-034 |
| HG-02 | public export of the ODbL/CC-BY-SA compartments | counsel disposition on ODbL 4.4(b), sui generis, RISK-P0-01..04 recorded | legal counsel | BL-035 |
| HG-03 | any live fetch of a source | reviewer sets `ingestion_permitted=true` + `last_verified` + reviewer per rights packet | rights reviewer (counsel-reviewed) | BL-032 |
| HG-04 | flock/portal + compact-status sources | Stage-0 outreach conducted and its outcome recorded on the row | ecosystem-outreach lead | BL-033 |
| HG-05 | integrating the stack (post-chain) | operator runs `merge_dryrun.sh` then `INTEGRATION_PLAN.md` §(d) | project maintainer | — (P20.3 plan) |
| HG-06 | first jurisdiction choice | decided = Oklahoma City (no gate unless overridden) | project maintainer | — |
| HG-07 | Zenodo deposit + object store + CDN | accounts created; concept DOI reserved | infra/ops owner | BL-037 / BL-029 |
| HG-08 | live MapRoulette client + OSM contribution | accounts created; Organised-Editing activity registered with OSMF | contribution-back lead | BL-038 |
| HG-09 | token-authenticated connectors (MuckRock, APIs) | tokens set as env secrets in the runner shell | infra/ops owner | BL-024 |
| HG-10 | moderated usability study | ≥5 ontology-naïve participants recruited; protocol approved | research/UX lead | BL-040 |
| HG-11 | operating governance + publish concurrence | board seated; Code of Conduct + funding policy adopted; two named reviewers | governance board | BL-036 |
| HG-12 | staging + production hosting | a host + budget approved (default: static `web/dist` + one small VM/container with PG18) | infra/ops owner | (BL-015/BL-007 landing) |
| HG-13 | normative spec amendments (A1–A8) | operator ticks the amendment list | project maintainer | (P20.2) |
| HG-14 | capstone ACCEPTED-deviations list | operator signs §(b) — **SIGNED 2026-09-08, 76/76, 0 rejected** | project maintainer | — (see §(e)) |

---

## (e) Cost posture — zero-cost mode vs the egress risk

- **Zero-cost start (SIG-STORE-003, SIG-STORE-004/005, SIG-GOV-021).** The design targets a
  zero-cost floor: local-first artefacts, static `web/dist` on any static host, and a
  **degraded-but-alive** mode with a dormant-scheduler keepalive. That keepalive is **documented but
  not yet tested** (RISK-P0-12, BL-030 → P21.5); the export/deposit path targets Zenodo's free tier +
  low-egress mirrors (SIG-GOV-022).
- **The egress risk (RISK-P0-07, ADR-015).** Bulk-export egress is the "success is the failure mode"
  cost — if download volume crosses the modelled TB/month, egress becomes existential. ADR-015's
  mitigations (CloudFront/CDN caching + torrent/IPFS offload + a low-egress mirror; an egress-budget
  alarm as the ADR's revisit trigger) are **design, not deployment**.
- **What exists today: nothing deployed.** There is **no Dockerfile, no compose file, and no
  deployment manifest** in the repo (SCOPING_NUMBERS §(vi); the only container use is
  testcontainers-PG18 for `make test-db`). No object store, no CDN, no Zenodo deposit, no running
  API/host. Everything runs locally or in CI.
- **What P21.4/P21.5 add.** P21.4 stands up **staging** (static `web/dist` + one small VM/container
  with PG18; ⧗ HG-12) and runs the first live OKC publish. P21.5 adds the first **Zenodo deposit**
  (⧗ HG-07), rendered tiles, low-egress mirrors, and the tested degraded mode — the transition from
  "live" to "sustained".
