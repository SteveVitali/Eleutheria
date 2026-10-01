# OPERATIONAL_READINESS — capability × {code, rights, infra, human} + the critical path (P20.1, Phase F; **Round 3–4 delta refresh by P24.8 / REC.1, 2026-09-13; Round-10 refresh by P33.4, 2026-09-28 — see §(f)**)

The document the operator reads to decide **what to unblock next**. It turns
`DECISION_MEMO.md` §6 + the go-live spec `docs/3_sig_golive_spec.md` into a checkable
map: for each capability, what the *code* does today (from `COVERAGE_MATRIX.csv` /
`CAPSTONE_CLOSURE.md`), what *rights* state its sources are in (live
`uv run sig-connectors validate`, re-verified 2026-09-13), what *infra* it needs, and
which *human gate* (HG-nn, role not name — Part VIII §0.7) unblocks it. Backlog ids
(`BL-nnn`) reference `BACKLOG.csv`; deferral ids (`D-*`) reference
`docs/tickets/DEFERRALS.md` and each cites exactly one `BL-` home.

**Round 3–4 delta (this refresh).** Since the P20.1 baseline (chain tip
`devin/p19-5-capstone-gap-closure`), Rounds 3 (go-live) and 4 (productionize) changed
the picture: the OKC critical subset is **flipped** (`ingestion_permitted=true: 6`,
`loadable now: 6`, RIGHTS.1 / GL-GATE-03); the three OKC document connectors exist
(P23.5); the GCP infra-as-code, scheduler, observability and composed-CI lanes landed
(P24.1–P24.4, ADR-075…078); the backlog was re-triaged (P24.5); a **second
jurisdiction ran end-to-end over fixtures** (P24.6 France/Gex, ADR-079) and the
**CCOPS connector class landed**, retiring OPEN FINDING P17-FLIP-01 (P24.7, ADR-080).
Baseline at the chain tip `devin/p24-7-ccops-disclosure` @ `919bde0`: `make check`
green (2975 passed, 2 env-gated skips — see P24.7's run ledger; re-verified this run).
**Still nothing is deployed or fetched live** — every credentialed step is
gate-pending, recorded, never fabricated.

Every `OPEN`/`PARTIAL` deferral now names its single backlog home (P24.8):

| deferral | gate | BL home |
|---|---|---|
| D-P21.1-2 (HG-04 US outreach) | HG-04 | BL-033 |
| D-P21.3-1 (PARTIAL — live fetch) | HG-09+net | BL-023 |
| D-P21.3-2 (HG-09 tokens) | HG-09 | BL-024 |
| D-P21.4-1 / -2 / -3 (home, governance, go-public) | HG-01/11 | BL-034 / BL-036 (D-P21.4-3 depends on both) |
| D-P21.5-1 (real deposit/store/egress/SWH) | HG-07 | BL-029 |
| D-P21.7-1 / -2 (push/pull, study) | HG-08/10 | BL-039 / BL-040 |
| D-P21.8-1, D-P21.9-1 (ecosystem/pathway fetches) | HG-03/04/09 | BL-042 / BL-043 |
| D-LEGAL.1-1 (counsel opinions) | HG-02 | BL-035 |
| D-ACCT.1-1, D-DEPLOY.1-1, D-OBS.1-1 (host, apply, live obs) | HG-12 (+HG-09) | BL-037 |
| D-LIVE.1a-1 (OKC doc-source live smoke) | HG-09+net | BL-023 |
| D-META.1-1 / -2 (calibration, records backend) | real data | BL-045 / BL-028 |
| D-JURIS.2-1 / -2 (FR flips+fetches, FR outreach) | HG-03/04 | BL-042 / BL-033 |
| D-CCOPS.1-1 / -2 (CCOPS flips+fetches+seed, outreach) | HG-03/04 | BL-054 / BL-033 |

`LEDGER.md § OPEN FINDINGS`: **zero open** — CI-RED-01 + DOCKER-DOWN closed by P24.4,
MATRIX-INT-01 closed by P24.5, P17-FLIP-01 retired by P24.7. ADR revisit triggers:
79/79 homed (ADR-079→BL-053, ADR-080→BL-054). `check_backlog.py` exits 0
(risk 102/102, ADR 79/79, LD 90/90, 0 duplicates).

---

## (a) Capability map

### Ingest — one row per connector. Live rights counts from `uv run sig-connectors validate` (2026-09-13)

Every connector is **built and fixture/shadow-tested** through the eight-stage
framework (§21); shadow replay `diff=0` is the deterministic proxy. Registry-wide
today: **121 sources, 95 rights-UNDETERMINED, 6 permitted, 6 loadable** (was 109 /
87 / 0 / 0 at P20.1). Per-connector, over that connector's own runnable source set:

| connector | code state | rights (permitted / UNDETERMINED / loadable of N) | infra needed | human gate | first target | owning ticket |
|---|---|---|---|---|---|---|
| osm | built; fixture-tested; **shadow replay diff=0**; no live Overpass fetch yet (HG-09/egress) | **1** / 0 / **1** of 7 family rows (osm_overpass flipped ODbL-1.0, 2026-09-10; all osm_* rows carry rights blocks) | live HTTP transport (landed) + OCFL CaptureStore (landed) | ~~HG-03 flip~~ done for osm_overpass; HG-09/egress for the fetch | OKC (`osm_overpass`) | P21.3 (BL-023); flip done P21.1/RIGHTS.1 |
| atlas | built; fixture-tested; shadow diff=0; no live fetch (LD-F03/RISK-P4-10) | 0 / 2 / 0 of 3 | live transport (landed) | HG-03 | OKC (`eff_atlas_of_surveillance`) | P21.3 (BL-023) |
| audit_structural | built; fixture-tested; aggregates-only (§43.6) | 0 / 0 / 0 of 3 (AGPL hazard `sm_alpr`, CC0) | none live (structural) | HG-03 | n/a (later) | P21.3 (BL-023/BL-024) |
| flock_portal | built; fixture-tested; no live `/api/v1/data` (RISK-P11-05) | **1** / 2 / **1** of 5 (`deflock_repo` flipped MIT, 2026-09-10; CC-BY-SA compartment stays separate) | live transport (landed) + snapshot diffing | ~~HG-03~~ done for deflock_repo; HG-04 outreach owed; HG-09/egress for the fetch | OKC (`deflock_repo`) | P21.3 (BL-024); outreach D-P21.1-2 (BL-033) |
| accountability | built; fixture-tested; no live Atlas/CourtListener (RISK-P13-07) | 0 / 3 / 0 of 3 | live transport (landed) | HG-03 | n/a (later) | P21.3 (BL-024) |
| procurement | built; fixture-tested; only P07.3 USAspending traced live (LD-X08) | **1** / 8 / **1** of 9 family rows (`okc_council` flipped CC0-1.0, 2026-09-10; `okc_procurement` is now its own connector — row below) | live transport for the API family (landed; RISK-P7-15) | ~~HG-03~~ done for okc_council; HG-09/egress for the fetch | OKC (`okc_council`) | P21.3 (BL-023/024); rights P21.1 (BL-032) |
| records | built; fixture-tested; no live MuckRock token mint (RISK-P7-10) | 0 / 3 / 0 of 3 (news stay LINK-posture per packets) | live transport (landed) + token (HG-09) | HG-03 + HG-09 | OKC (`journalrecord`, `oklahoman`) | P21.3 (BL-024) |
| **okc_documents** (P23.5, ADR-074) | **landed**: `okc_procurement`/`okcpd_policy`/`ok_statute` fetch→OCFL→sig-parsing→claims; shadow diff=0 ×3 | **3** / 0 / **3** of 3 (all flipped CC0-1.0, 2026-09-10) | live transport (landed) | ~~HG-03~~ done; **live smoke gate-pending HG-09 + egress** | OKC (the three doc sources) | P23.5; live half D-LIVE.1a-1 / D-P21.3-1 (BL-023) |
| data_driven (P21.8, ADR-070) | landed; release-versioned claims over fixtures; shadow diff=0 | 0 / 1 / 0 of 1 (`eff_data_driven` UNDETERMINED) | live transport | HG-03 (+HG-09) | n/a (SOURCES.1) | P21.8 (BL-042); D-P21.8-1 |
| coarse_international (P21.8, ADR-070) | landed; REFERENCE-capture path over fixtures; shadow diff=0 | 0 / 3 / 0 of 3 (aspi/carnegie/fr_world_map) | live transport | HG-03/HG-04 per source | n/a (SOURCES.1) | P21.8 (BL-042); D-P21.8-1 |
| pathways (P21.9, ADR-071) | landed; 3 family extractors + parser layers; shadow diff=0; procured≠deployed | 0 / 3 / 0 of 3 (LINK/UNDETERMINED) | live transport | HG-03/HG-04 per source | n/a (SOURCES.1) | P21.9 (BL-043); D-P21.9-1 |
| france_belgium_procurement | built; fixture/shadow-tested (`decp_fr` shadow diff=0, P24.6); `ingestion_permitted=false` by design (RISK-P18-06) | 0 / 1 / 0 of 1 (LO 2.0 disposition **counsel-needed**) | live transport (DECP) | HG-03 (design-gated) | France (P24.6) | P21.8/JURIS.2 (BL-042); D-JURIS.2-1 |
| france_belgium_records | built; fixture/shadow-tested (`raa_prefectures` diff=0; **`madada` REFUSED at the compact gate** — recorded, not bypassed) | 0 / 3 / 0 of 3 (RAA ODbL; madada `not_contacted`) | live transport + arrêté-PDF extraction | HG-03 (design-gated) + HG-04 | France (P24.6) | P21.8/JURIS.2 (BL-042); D-JURIS.2-1/2 |
| **government_mandated_disclosure** (P24.7, ADR-080) | **landed**: CCOPS class; per-agency aggregate rows only; two-layer procured≠deployed; shadow diff=0 ×3 | 0 / 3 / 0 of 3 paying (+ class row + NCSL seed asset `as_of 2022-02-03`; municipal-record posture **counsel-needed**) | live transport | HG-03 + HG-04 | n/a (CCOPS.1) | P24.7; live half D-CCOPS.1-1/2 (BL-054/BL-033) |

### Other capabilities

| capability | code state | rights/data state | infra needed | human gate | first target | owning ticket |
|---|---|---|---|---|---|---|
| resolve (ER) | ER over PG wired: `sig-resolution match/review decide --dsn` (P19.5); exercised on the France run (1 PROPOSED enqueued) | gold set seeded by judgement, not EM-estimated (RISK-P5-05 → D-META.1-1 calibration) | PG18 | — | OKC | closed-by:P19.5 (BL-017); calibration BL-045/D-META.1-1 |
| reconcile | compute-on-read conforming (A5/HG-14); 299-vs-190 contradiction survives to the export dossier | — | PG18 (materialise → BL-004 closed-accepted) | — | OKC | P21.2 (BL-004/027 closed) |
| tasks | task engine + MapRoulette client + OSM feed → LeverageLedger (P21.7/ADR-069); push refused while `registered=false` (exit 3) | — | MapRoulette/OSM accounts | HG-08 + HG-10 | OKC | P21.7 (BL-039/040); D-P21.7-1/2 |
| API | `PgReadStore` over PG (16 methods, P19.4); rate limit metadata-only (RISK-P14-09) | — | PG18 + one small VM/container — **IaC exists** (P24.1) | HG-12 | OKC | closed-by:P19.4 (BL-015); deploy D-DEPLOY.1-1 (BL-037) |
| exports | export gate honours `derivative_permitted` (P19.5); **tiles (.pmtiles), .torrent, degraded build, dry-run deposit all real** (P21.5/ADR-067); tables still fixture/projected, not live (RISK-P14-18) | ODbL split computed; Zenodo = FakeZenodo until HG-07 | object store + Zenodo | HG-07 | OKC | P21.4 (BL-008); deposit D-P21.5-1 (BL-029) |
| web | zero-JS Astro; **reads export bytes** (P21.4 — LD-V08 flipped; 299-vs-190 rendered from export); France dossier renders (P24.6, FR-GDPR withholding exercised) | — | static host (GCS in the IaC) | HG-12 | OKC | P21.4 (BL-007 closed); map spec P20.2 A1 (BL-010 accepted) |
| contribution-back | MapRoulette client + OSM changeset feed landed (P21.7/ADR-069); no live push/pull | — | MapRoulette/OSM accounts | HG-08 + HG-10 | later | P21.7 (BL-038/039/040) |
| international adapters | jurisdiction-adapter framework **generalized + proven by France** (P24.6/ADR-079 — dispatch tables, no per-jurisdiction hack; okc path byte-identical) | `ingestion_permitted=false` by design; madada compact `not_contacted` | live transports | HG-03 + HG-04 | France done over fixtures | P21.8/P24.6 (BL-042); 3rd jurisdiction BL-053 |
| CCOPS disclosures | **`government_mandated_disclosure` class landed** (P24.7/ADR-080; P17-FLIP-01 retired) | rights packets UNDETERMINED (counsel-needed) | live transport | HG-03 + HG-04 | n/a | P24.7; expansion BL-054 |
| **deployment** (P24.1, ADR-075) | `ops/gcp/` IaC + `ops/Dockerfile` + `sig-ops deploy/backup-drill` **validated green with NO ADC**; e2-micro compose chosen over Cloud SQL; local restore drill DONE over Docker | — | GCP project `$SIG_GCP_PROJECT` + operator ADC | HG-12 | GCP | P24.1; apply D-DEPLOY.1-1 / D-ACCT.1-1 (BL-037) |
| **scheduling** (P24.2, ADR-076) | `reingest.yml` GHA cron → `sig-orchestration due` → per-source `sig-connectors run`; append-only FreshnessLedger; disappearance sweep wired | — | runs on CI runner; live sources for real ticks | HG-03/09 per source | OKC | P24.2 (the P21.3 scheduling backlog, closed) |
| **observability** (P24.3, ADR-077) | record-first alert ledger + env webhook (`SIG_ALERT_WEBHOOK_URL`); probe metrics + `compute_uptime` budgets (`no-data` honest); keepalive verified end-to-end | — | hosted endpoints to probe; webhook URL | HG-12 + HG-09 | GCP | P24.3; live side D-OBS.1-1 (BL-037) |
| **CI** (P24.4, ADR-078) | `composed` job runs `tests/e2e` **for real** (Node + Docker, `SIG_REQUIRE_DB_TESTS=1`); `security` scans; `nightly.yml`; **first on-runner run green** (run 34802316750, composed 16/0 incl. S8) | — | GitHub Actions | — (first nightly tick unobserved) | — | P24.4; D-CI.1-1 closed |

---

## (b) Minimum viable live slice — Oklahoma City (J-1)

The smallest end-to-end that puts one real jurisdiction live (`DECISION_MEMO.md` §6
step 4). **The rights half is now done**: the OKC critical subset is flipped —
`okc_procurement`, `okc_council`, `okcpd_policy`, `ok_statute` (CC0-1.0, public
records/statutory text per their packets), `osm_overpass` (ODbL-1.0, separate
compartment), `deflock_repo` (MIT) — `loadable now: 6` (≥ 5 required). News sources
`journalrecord`/`oklahoman` stay LINK-posture per their packets.

- **Sources (8):** `deflock_repo`, `okc_procurement`, `okc_council` (CivicClerk),
  `okcpd_policy`, `ok_statute`, `journalrecord`, `oklahoman`, `osm_overpass`.
  6 of 8 flipped; the 2 news sources are not required for the slice (LINK-only).
- **Connectors:** `flock_portal`/`atlas` (`deflock_repo`), `procurement`
  (`okc_council`), the three `okc_documents` connectors (P23.5), `records`
  (`journalrecord`, `oklahoman`), `osm` (`osm_overpass`). All wired into
  `runner.CONNECTOR_FOR_SOURCE`; `run --mode live` no longer refuses the six on gate
  grounds (`live_gate_reasons` empty — verified by the P21.3 LIVE.1 re-run for the
  doc sources; `loadable now: True` ×6 per `sig-connectors validate`).
- **Tables:** the append-only `claim` spine + `resolution` (ER over PG), the OCFL
  `evidence` store, the identity registries (`entity` / surrogate `entity_id`),
  `graph_annotations` (compute-on-read, conforming per A5), and the projected
  `ExportTable`s.
- **Pages:** the J-1 dossier, the OKC map/network view, the coverage/methodology
  page, the corrections log, and the task-intake page — **already built from export
  bytes** (`SIG_DATA_SOURCE=export`, P21.4; 50 pages incl. the 299-vs-190
  contradiction visible), not committed fixtures.
- **What stands between here and live:** HG-09 API tokens + network egress for the
  first real fetch (D-P21.3-1/2, D-LIVE.1a-1); HG-12/ADC for the real host
  (D-ACCT.1-1, D-DEPLOY.1-1); then HG-01 (real home, interim only) + HG-11
  (governance owed) + HG-02 (real counsel, interim engineering disposition only)
  before Go-public (D-P21.4-1/2/3, D-LEGAL.1-1 — Go-public is reserved to the
  human, GL-GATE-05).

---

## (c) Critical path — no placeholders (re-verified 2026-09-13)

`DECISION_MEMO.md` §6 + the go-live critical path (`3_sig_golive_spec.md` §4)
re-verified against the current matrix/closure. Each step names its `ticket:` and a
`proof:` command/artefact. `⧗` marks a human action (the gate that unblocks it).
There are no unresolved placeholders; the only unknowns are the *dates* of the `⧗`
human actions.

1. **Memory committed.** `ticket:` P19.1 (+ P22.3 build-memory v2). `proof:` `bash scripts/docs/check-build-memory.sh .` exit 0; `git ls-files docs/build docs/tickets | wc -l` ≥ 100.
2. **Capstone: verdict matrix + composed stack + spine wiring + closure.** `ticket:` P19.2 → P19.3 → P19.4 → P19.5 + PR #68 capstone. `proof:` `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra` = 16 passed, 0 failed, 0 xfailed (P24.4 tip); `CAPSTONE_CLOSURE.md` §(e) HG-14 signed (⧗ **HG-14**, done 2026-09-08).
3. **Backlog + readiness.** `ticket:` P20.1; **delta refresh P24.8** (this document + `BACKLOG.csv` + the `D-*`→`BL-*` map above). `proof:` `python docs/build/tools/check_backlog.py` exits 0 (`risk deferred rows: 102/102`, `ADR revisit triggers: 79/79`, `LD rows: 90/90`, `duplicate sources: 0`).
4. **Spec reconciled + integration plan.** `ticket:` P20.2 (⧗ **HG-13** A1–A8, applied) → P20.3 (plan only; merges nothing). `proof:` `python docs/build/tools/check_spec_src.py` exit 0 (671 ids, 79 ADRs, byte-identical); `sh docs/build/tools/merge_dryrun.sh` exits 0; `INTEGRATION_PLAN.md` §(d) complete.
5. **OKC registry rows + rights packets + flips.** `ticket:` P21.1 + RIGHTS.1 re-run (`devin/p21-1-rights-flip-rerun`, 2026-09-10). `proof:` `uv run sig-connectors validate` → `ingestion_permitted=true: 6`, `loadable now: 6`. ⧗ **HG-03** partially done (OKC subset flipped; remainder + FR/CCOPS owed — D-P21.8-1/D-P21.9-1/D-JURIS.2-1/D-CCOPS.1-1); ⧗ **HG-04** outreach owed (D-P21.1-2/D-JURIS.2-2/D-CCOPS.1-2 → BL-033).
6. **Connectors + live transports behind the gate.** `ticket:` P21.3 (+ LIVE.1 re-run) → P23.5 (LIVE.1a doc connectors). `proof:` shadow replay `diff=0` per flipped source; `run --mode live` refuses exit 3 for every non-green source (no socket). ⧗ **HG-09** tokens + network egress for the first real fetch (D-P21.3-1, D-LIVE.1a-1 → BL-023/BL-024).
7. **Full OKC run from fixture/shadow → local staging.** `ticket:` P21.4 (+ LIVE.2 re-run `devin/p21-4-live2-rerun`, 2026-09-13). `proof:` `sh docs/build/tools/run_okc.sh` completed over Docker; `docs/build/reports/okc/acceptance_2026-09-13.json` — J-1 pass, 2 pass / 11 blocked / 0 failed, 299-vs-190 contradiction UNRESOLVED/visible from export bytes. ⧗ **HG-12** real host (D-ACCT.1-1 → BL-037).
8. **Productionize.** `ticket:` P24.1 (DEPLOY.1 — IaC validated, ADR-075) → P24.2 (SCHED.1 — `reingest.yml` cron, ADR-076) → P24.3 (OBS.1 — recorded alerts/uptime, ADR-077) → P24.4 (CI.1 — composed CI green on-runner, ADR-078). `proof:` `bash ops/gcp/provision.sh --check` + `bash ops/gcp/backup.sh --check` + `sig-ops deploy --target gcp --dry-run` exit 0 with no ADC/no network; `tests/db/test_restore_drill.py` real over Docker; `gh run view 34802316750` — composed 16 passed / 0 failed incl. all three `test_s8_web_build_*` (D-CI.1-1 closed). ⧗ **HG-12** apply/deploy (D-DEPLOY.1-1), ⧗ **HG-07** credentialed deposit/store (D-P21.5-1 → BL-029), ⧗ live obs endpoints (D-OBS.1-1 → BL-037).
9. **Public publish.** `ticket:` P21.4 publish step → P23.6 (Go-public marker, GATE-G2). `proof:` `docs/build/reports/PUBLICATION_CHECKLIST.md` fully ticked, then DNS → public. ⧗ **HG-01** real legal home (interim posture only — D-P21.4-1 → BL-034), ⧗ **HG-11** two named reviewers + concurrence + takedown contact (D-P21.4-2 → BL-036), ⧗ **HG-02** real counsel disposition (interim engineering disposition only — D-LEGAL.1-1 → BL-035; until then the OSM-derived layer stays in its separate ODbL compartment), ⧗ **Go-public** reserved to the human (GL-GATE-05; D-P21.4-3).
10. **Sustained operation.** `ticket:` P21.5 (INFRA.1 re-run — tiles/torrent/degraded/keepalive proven free-path; ⧗ **HG-07** real deposit), P21.7 (CONTRIB.1 re-run — dry-run/fixtures proven; ⧗ **HG-08/HG-10**), P21.8/P21.9 (SOURCES.1 re-run — connectors proven; ⧗ **HG-03/HG-04 + HG-09**). `proof:` `sig-exports tiles` valid PMTiles v3; `sig-ops degraded` builds `web/dist` with no API; `keepalive.yml` + `observability.yml` + `reingest.yml` valid + wired; MapRoulette push refuses exit 3 while `registered=false`.
11. **Federation proof — second jurisdiction.** `ticket:` P24.6 (JURIS.2 — France / Commune de Gex, ADR-079). `proof:` `docs/build/tools/run_france.sh` completed over Docker staging (11 claims/4 entities; raa+decp shadow diff=0; `madada` REFUSED at the compact gate — recorded); `docs/build/reports/france/acceptance_2026-09-14.json` — 7 pass / 3 blocked / 0 failed; web `/dossier/gex-videoprotection` renders, officer name withheld under FR-GDPR. ⧗ **HG-03/HG-04** FR flips + outreach (D-JURIS.2-1/2 → BL-042/BL-033).
12. **Connector-class completeness.** `ticket:` P24.7 (CCOPS.1 — `government_mandated_disclosure`, ADR-080). `proof:` `tests/connectors/test_government_mandated_disclosure.py` 40 passed; shadow diff=0 ×3; live refuses exit 3; `check_coverage_matrix.py` → `671 rows OK` (SIG-INGEST-049*/050 PARTIAL/MISSING → MET; OPEN FINDING P17-FLIP-01 retired). ⧗ **HG-03/HG-04** CCOPS flips + outreach (D-CCOPS.1-1/2 → BL-054/BL-033); expansion BL-054.
13. **Readiness delta + operator signature.** `ticket:` P24.8 (REC.1 — this delta) → **P24.9 GATE-ACCEPT**. `proof:` this document; `check_backlog.py` exit 0; `CAPSTONE_CLOSURE.md` addendum stating the ACCEPTED list is unchanged at 77 MET-DIFFERENTLY rows (no new Round 3–4 deviation). ⧗ **operator re-signs** the accepted-deviations list at GATE-ACCEPT.

---

## (d) Human-gate checklist HG-01..14 — what unblocks it, and who (role, never a private individual)

| gate | what it unblocks | what unblocks it | who (role) | state 2026-09-13 | backlog |
|---|---|---|---|---|---|
| HG-01 | naming a legal home before public launch | fiscal sponsor / nonprofit identified, recorded in `docs/governance/` | project maintainer + legal counsel | **INTERIM only** (GL-GATE-01 maintainer-stewardship; NOT a real home) — D-P21.4-1 OPEN | BL-034 |
| HG-02 | public export of the ODbL/CC-BY-SA compartments | counsel disposition on ODbL 4.4(b), sui generis, RISK-P0-01..04 recorded | legal counsel | **INTERIM engineering disposition** (GL-GATE-02, publish-permitting, NOT a legal opinion) — D-LEGAL.1-1 OPEN | BL-035 |
| HG-03 | any live fetch of a source | reviewer sets `ingestion_permitted=true` + `last_verified` + reviewer per rights packet | rights reviewer (counsel-reviewed) | **PARTIAL — 6 flipped** 2026-09-10 (OKC subset, GL-GATE-03); remainder + FR/CCOPS owed | BL-032 (closed for OKC subset); flips owed via D-P21.8-1/D-P21.9-1/D-JURIS.2-1/D-CCOPS.1-1 |
| HG-04 | flock/portal + compact-status sources | Stage-0 outreach conducted and its outcome recorded on the row | ecosystem-outreach lead | **OWED** (US 19 projects + FR + CCOPS) — D-P21.1-2/D-JURIS.2-2/D-CCOPS.1-2 OPEN | BL-033 |
| HG-05 | integrating the stack (post-chain) | operator runs `merge_dryrun.sh` then `INTEGRATION_PLAN.md` §(d) | project maintainer | **DEFERRED by operator** (P23.1/REL.1 skipped, non-blocking milestone) — RETURN PASS | — (P20.3 plan) |
| HG-06 | first jurisdiction choice | decided = Oklahoma City (no gate unless overridden) | project maintainer | decided | — |
| HG-07 | Zenodo deposit + object store + CDN | accounts created; concept DOI reserved | infra/ops owner | **OWED** — `provided: no` (P23.4/ACCT.1); D-P21.5-1 OPEN | BL-037 / BL-029 |
| HG-08 | live MapRoulette client + OSM contribution | accounts created; Organised-Editing activity registered with OSMF | contribution-back lead | **OWED** — `provided: no`; D-P21.7-1 OPEN | BL-038 |
| HG-09 | token-authenticated connectors (MuckRock, APIs) | tokens set as env secrets in the runner shell | infra/ops owner | **OWED** — `provided: no`; blocks every live fetch (D-P21.3-2, D-LIVE.1a-1) | BL-024 |
| HG-10 | moderated usability study | ≥5 ontology-naïve participants recruited; protocol approved | research/UX lead | **OWED** — protocol + aggregate-only instrumentation landed; D-P21.7-2 OPEN | BL-040 |
| HG-11 | operating governance + publish concurrence | board seated; Code of Conduct + funding policy adopted; two named reviewers | governance board | **OWED** (P23.2 recorded OWED) — D-P21.4-2 OPEN | BL-036 |
| HG-12 | staging + production hosting | a host + budget approved (GCP `$SIG_GCP_PROJECT` chosen, GL-GATE-04) + operator `gcloud` ADC for the `apply` | infra/ops owner | **ANSWERED, apply OWED** — IaC validated (P24.1); D-ACCT.1-1 / D-DEPLOY.1-1 OPEN | BL-037 |
| HG-13 | normative spec amendments (A1–A8) | operator ticks the amendment list | project maintainer | **DONE** — all 8 applied 2026-09-08 (P20.2) | — |
| HG-14 | capstone ACCEPTED-deviations list | operator signs §(b) — **SIGNED 2026-09-08, 76/76, 0 rejected** (+ §(b) addendum: 77th row = same zero-JS-map deviation under SIG-UI-047) | project maintainer | **SIGNED; re-sign at P24.9 GATE-ACCEPT** — P24.8 addendum records the list is unchanged at 77 | — (see §(e) of CAPSTONE_CLOSURE) |

---

## (e) Cost posture — zero-cost mode vs the egress risk

- **Zero-cost start (SIG-STORE-003, SIG-STORE-004/005, SIG-GOV-021).** The design targets a
  zero-cost floor: local-first artefacts, static `web/dist` on any static host, and a
  **degraded-but-alive** mode with a dormant-scheduler keepalive. The keepalive is
  **now tested and wired** (P21.5 `sig-ops degraded` + `keepalive.yml`; P24.3
  `observe.verify_keepalive` proves the machinery + the function and fires a recorded
  `critical` alert on failure; BL-030 closed). The export/deposit path targets
  Zenodo's free tier + low-egress mirrors (SIG-GOV-022).
- **The egress risk (RISK-P0-07, ADR-015).** Bulk-export egress is the "success is the
  failure mode" cost — if download volume crosses the modelled TB/month, egress
  becomes existential. ADR-015's mitigations (CloudFront/CDN caching + torrent/IPFS
  offload + a low-egress mirror) are now **partially wired**: the `.torrent` mirror is
  real (P21.5), and the egress-budget **alarm is implemented** — `sig-ops
  egress-report --alert` fires a recorded alert on `warn`/`alarm` (P24.3/ADR-077);
  the live usage read stays gate-pending HG-07 (`gate-pending`, computes `level=ok`
  only for a simulated `--usage-gb`).
- **What exists today: IaC written + validated; still nothing applied.** P24.1 landed
  `ops/gcp/` (idempotent `gcloud` scripts + `ops/Dockerfile` + `sig-ops deploy
  --target gcp`) — ADR-075 chose a single always-free `e2-micro` GCE running the
  compose stack over the smallest Cloud SQL tier (~$9+/mo, kept documented); cost ≈
  **$0/mo within Always-Free** (`ops/gcp/README.md` table). The `apply`/deploy and
  the cloud restore are gated on operator ADC (D-DEPLOY.1-1); the **local** restore
  drill runs for real over Docker (`tests/db/test_restore_drill.py`). No object
  store, no CDN, no Zenodo deposit, no running API/host — everything runs locally or
  in CI.
- **What the gated steps add.** The P21.3/P21.4 re-runs make the first real fetch +
  staging publish (⧗ HG-09 + egress + HG-12); the P24.1 `apply` brings up GCP
  staging/private (⧗ ADC); P21.5's credentialed half adds the real Zenodo deposit +
  object store + live egress + SWH save (⧗ HG-07) — the transition from "staging" to
  "sustained"; Go-public (DNS + `v0.2.0`) stays a deliberate human action
  (GL-GATE-05) after real HG-01 + HG-11 + HG-02.

---

## (f) Round-10 readiness — 2026-09-28 (P33.4, post-GATE-ACCEPT)

Sections (a)–(e) are the Round-3/4 snapshot; nothing above is rewritten — this
section is the Round-10 state, recorded after the operator **signed** the
Round-10 acceptance readout (`docs/build/readouts/ACCEPT-R10.md`, SIGNED
2026-09-28). The signature accepts the `CAPSTONE_CLOSURE.md` §(f) packet **as
presented** — explicitly *not* the owed register as closed. That register is
§(f5): **36 owed rows (32 OPEN + 4 PARTIAL) + `SIG-MEM-004`** (scheduled chain
work, owner P33.8 row 200), each with owner, landing, closure condition and
compensating control. `projectStatus` stays `IN-PROGRESS` under BM-TAIL-03
while the register is non-empty.

### (f1) Readiness by domain — a fixture or staging pass is never a live or public pass

- **implemented** (code landed + green under `make check`/the Docker suites):
  the whole Round-10 engineering spine — `sig.assertion/1` typed assertions +
  actual-capture bindings (P32.2/ADR-121); role/count semantics + scoped
  organisation identity (P32.3/ADR-122); the shared bitemporal occurrence
  contract (P32.4/ADR-123); one publication-eligibility policy (P32.5/ADR-124);
  legacy-evidence audit + recovery plan/apply machinery (P32.6 + P32.22,
  ADR-125/141); obligation events + current projection + single-writer
  closeout protocol — landed **shadow-only** (P32.7/P32.8, ADR-126/127);
  blinded human-eval campaign tooling + the shadow evaluator (P32.9/P32.10,
  ADR-128/129 — `mode=shadow`, `awaiting_humans`, `applied=[]`); reviewed
  acquisition queue + bounded document adapters (P32.11/P32.12, ADR-130/131);
  immutable releases + per-compartment FTS5 search + coordinated workspace
  (P32.13–15, ADR-132/133/134); durable anonymous intake + reviewed correction
  application (P32.16/16a, ADR-135); dossier schema + three mechanical packets
  (P32.17–20, ADR-136–139); acquisition funnel (P32.21, ADR-140); candidate
  identity + publish verification + journey portfolio (P32.23a–25,
  ADR-142/143/144); composed verification `sig.composed-verification/1`
  **pass 20/20** (P33.2); the capstone packet + register guard (P33.3).
- **fixture** (deterministic proof over committed fixtures/staging trees —
  committed evidence, NOT live): the composed verification over one committed
  fixture on a scratch PG18 spine (P33.2); dossier packets
  `mechanical_complete` (`review.status=not_run`, `pilot_complete=False`);
  release candidate `p-17b713…` with publish-verification **25/25** inside the
  bounded staging namespace (P32.25); journey portfolio 38 checks over the
  declared `sig.journey-corpus/1` corpus + the real-PG18 intake journey proof
  (P32.24); recovery apply +0 on the seeded fixture (P32.22); every live
  return-pass packet `prepared_not_executed` under `docs/build/reports/`.
- **hosted** (real infrastructure): the pre-Round-10 hosted surface stands as
  recorded by earlier rounds (P30/P31.16 lineage — `sig-pg`/`sig-api`/`sig-web`,
  the national publish + republish). Round-10 executed **no production hosted
  leg**: the staging namespace is verified; `D-R10-LIVE-1` (hosted
  audit/recovery/freeze), `D-P32.23a-1` (production candidate over the hosted
  snapshot) and `D-R10-PUBLISH-1` (production exposure) stay OPEN. Scheduled
  hosted work: `D-FEDERAL.1-1` (monthly `sig-sched-sam-gov` cron + the +0
  re-run check) and `D-P31.4-1` (the date-bound 2026-10-10 batch-05 replay —
  verifiable only after the cron fires).
- **public**: the public surface is the prior HG-11-signed national publish.
  Round-10 added **no new public exposure**: the candidate is staged not
  served, the intake receiver answers `503 receiver_not_operating`, the
  provisional evaluation disclosure stands. Production exposure = OPEN
  (`D-R10-PUBLISH-1` + `D-P32.23a-1` + `D-R10-LIVE-1`).
- **human**: **signed** — GATE-G3 (2026-10-19, scoped: provisional candidate,
  reduced dossier scope, intake stays non-operational) and GATE-ACCEPT
  (2026-09-28, the packet accepted as presented). **Owed** — the S3 spine
  deferred wholesale (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23, re-enter at
  manifest row 184): `D-R10-HUMAN-1`, `D-R6.1-EVAL`, `D-P30.2b-1/-2`; reviewer
  sessions (`D-P32.3-1` identity dispositions; the `D-R10-SOURCES-1` +
  `D-SOURCES.*`/`D-JURIS.2-1` rights lanes); participants (`D-R10-USERS-1`);
  the intake operating packet (`D-P32.16-1`); credentials/accounts
  (`D-P21.3-2`, `D-P21.5-1`, `D-P21.7-1`); maintainer repair-shape decisions
  (`D-P32.10a-1`, `D-P32.16a-1`); the external-IdP + consenting-filer
  decisions (`D-R7.1-AUTH`, `D-R7.2-SEND`).

### (f2) Backlog-home reconciliation (the P33.4 sweep — verified, nothing re-homed)

`docs/build/tools/check_backlog.py` at this revision exits 0 and the sweep
records:

- **ADR-120…144** — each `## Revisit trigger` is owned by **exactly one**
  `BACKLOG.csv` `sources` cell: `BL-058` (the Round-10 umbrella row,
  `landing=P32+`, theme T4). Checker line: `ADR revisit triggers: 143/143`,
  `duplicate sources: 0`.
- **Deferral homes** — every `OPEN`/`PARTIAL` DEFERRALS row names a BL home:
  `deferral homes: 36/36` (all 15 `BL-058`-homed rows — the whole Round-10
  deferral set — keep `BL-058`; the §(f5) register's three carried-in
  adjudications `D-R6.1-EVAL`, `D-P30.2b-1`, `D-P30.2b-2` keep `BL-057`, and
  the other carried-forward rows keep their original homes). No `D-*` id
  lives in a
  `sources` cell; the `(cites BL-nnn)` convention holds everywhere.
- **Mirror** — `docs/build/BACKLOG.md` regenerated by
  `build_backlog_md.py`: **byte-identical** to the pre-sweep mirror — the homes
  were already normalized; this run verifies and records, it does not
  re-home. `--check` exits 0.
- **Historic outcomes preserved** — no CSV row re-homed or re-triaged, no
  DEFERRALS status flipped, no landed ADR body edited; the one thing that
  changed in the world (the ACCEPT-R10 signature) is recorded additively in
  `docs/tickets/DEFERRALS.md`'s P33.4 section and here.
- For the record: `D-R7.2-SEND`'s status cell cites **one** home (`BL-057`);
  the `BL-028` token in its verify text is a cross-reference to the
  records-request backend, not a second home — no ambiguity, nothing changed.

### (f3) RETURN PASS — a concrete command for every owed row

Re-dispatches run the same contract with `live_verification=true` **only**
after the recorded gate/credential/pre-condition is satisfied (per the Run
line convention: a live stage reuses the same ticket after recorded scope +
approval). Human rows have no engineering command — the recorded human action
is the return path, then the named verification runs.

**Round-10-scoped (18 rows):**

| obligation | blocking domain | unblocked by | RETURN PASS |
|---|---|---|---|
| `D-R10-HUMAN-1` | human | operator assigns independent reviewers | re-enter the deferred spine in order at manifest row 184: `implement-spec spec=docs/tickets/184_HUMAN-H4__human-development-and-dossier-review.md` (orchestrator pauses; operator records the readouts) → `185_P32.22a__candidate-and-confirmatory-frame-freeze.md` → `186_HUMAN-H5__blinded-confirmatory-human-campaign.md` → `187_P32.23__human-evaluation-and-rules-decision.md` |
| `D-R6.1-EVAL` | human → engineering | the same H4→H5→P32.23 spine lands real labels | after P32.23's measured decision: re-`build_gold_set` from the human holdout → re-measure P/R/F1 + B-cubed + κ → the P31.18 rules re-derivation (carried into Round 10 — authored at that point; no chain file exists yet) |
| `D-P30.2b-1` | human → engineering | real human review decisions exist | same spine; an accepted proposal appears as a human edge in the next `camera_site` run; re-run `+0` |
| `D-P30.2b-2` | engineering | rules-v3 + a fresh holdout under the human campaign | same spine → P31.18 re-derivation: a rules-v3 soft conflict measured on the new frozen holdout; tier-3g precision re-measured ≥ 0.98 |
| `D-R10-SOURCES-1` | human (rights) → hosted | HG-03 per-target review + Part VIII preflight for the four pilot rows below | the four `D-P32.*-1` live re-dispatches are its legs (see below) |
| `D-R10-LIVE-1` | hosted | reviewed scope + ceilings + pinned inputs; HUMAN-H5/P32.23 before a *final* candidate | `uv run sig-ops evidence-audit --dsn $SIG_HOSTED_DSN --capture-dir <mounted OCFL root> --out <live-audit>/` → `sig-ops recovery-plan --audit <live-audit>/audit_report.json --out <live-audit>/` → `sig-ops recovery-apply --dsn $SIG_HOSTED_DSN --plan … --audit … --apply --execution-id <id> --authority <op-ref> --capture-dir <OCFL root> --verify-rerun --rematerialize --out <live-apply>/` → `sig-ops recovery-freeze …` — exact forms + ceilings: `docs/build/reports/p32.22-bounded-recovery/LIVE_RETURN_PASS.json`; then `implement-spec spec=docs/tickets/183_P32.22__bounded-recovery-and-activation.md live_verification=true` |
| `D-R10-PUBLISH-1` | public | GATE-G3-signed scope stands; production exposure needs the operator's serve decision | `implement-spec spec=docs/tickets/191_P32.25__accepted-release-public-verification.md live_verification=true`; rollback cases: `docs/build/reports/p32.25-accepted-release-verification/LIVE_RETURN_PASS.json` |
| `D-R10-MEMORY-1` | human (operator-approved cutover) | operator approves the entry-point boundary | apply `contract/patch/1..3` per `docs/build/tools/CLOSEOUT_WRITER_PROTOCOL.md` at an approved boundary; verify: `python3 docs/build/tools/obligation_events.py check` + `current_projection.py verify` fresh post-cutover; `168_P32.8__memory-concurrency-and-recovery.md` |
| `D-R10-USERS-1` | human | operator recruitment + volunteers exist | run `docs/build/reports/p32.24-investigation-journey-verification/USABILITY_TASK_PROTOCOL.md`; land `USABILITY_SESSIONS.json`; re-run `implement-spec spec=docs/tickets/189_P32.24__investigation-journey-verification.md` — the portfolio check re-evaluates `UX.independent_sessions` |
| `D-P32.3-1` | human (reviewer session) | reviewer sits with the dry-run report | `uv run sig-resolution partner-name-audit --dsn $SIG_HOSTED_DSN` → record a `same_as`/`distinct`/`keep` disposition per legacy `sig.org.name` key until `split_keys` exposure is reviewed to zero |
| `D-P32.10a-1` | decision (maintainer) | repair-shape decision (count-derived / `>=` / stop pinning global counts) | append-only sqitch change for the chosen shape; verify `sqitch verify` over a fully deployed PG18 container exits 0 (today: `ERROR: division by zero` at `verify/shared_temporal_contract.sql:30`) |
| `D-P32.16-1` | human (operator) | operating packet §1 rows filled | per `docs/governance/intake-receiver-operating-packet.md`: `ops/config.toml [intake]` `operational=true` + named owner + `staffed=true` + retention/secrets/log-exclusions on file; an unauthenticated probe then shows the form accepting and a submitted report reaching moderation |
| `D-P32.16a-1` | decision (maintainer) | repair-shape decision (CASCADE vs ordered drops vs a new teardown change) | append-only sqitch change; verify `sqitch revert` over a fully deployed container exits 0 (today: `ERROR: cannot drop extension postgis` at `revert/extensions.sql:7`) |
| `D-P32.18-1` | hosted | HG-03 per-target review + Part VIII preflight | `implement-spec spec=docs/tickets/179_P32.18__oklahoma-city-evidence-dossier.md live_verification=true`; packet: `docs/build/reports/p32.18-okc-dossier/LIVE_RETURN_PASS.json` |
| `D-P32.19-1` | hosted | same | `implement-spec spec=docs/tickets/180_P32.19__tulsa-evidence-dossier.md live_verification=true`; packet: `docs/build/reports/p32.19-tulsa-dossier/LIVE_RETURN_PASS.json` |
| `D-P32.20-1` | hosted | same + the SRC-027 admissibility decision | `implement-spec spec=docs/tickets/181_P32.20__san-diego-evidence-dossier.md live_verification=true`; packet: `docs/build/reports/p32.20-san-diego-dossier/LIVE_RETURN_PASS.json` |
| `D-P32.21-1` | hosted | HG-03 exact-target review (three rights lanes separately) + Part VIII screening | `implement-spec spec=docs/tickets/182_P32.21__source-pilot-and-maintenance-decision.md live_verification=true`; packet: `docs/build/reports/p32.21-acquisition-pilot/ACQ_PILOT_RETURN_PASS.json` |
| `D-P32.23a-1` | hosted | `D-R10-LIVE-1` executed (hosted recovery + freeze) | `LIVE_RETURN_PASS.json` (`docs/build/reports/p32.23a-release-candidate/`): `sig-ops recovery-apply … --rematerialize` + `sig-ops recovery-freeze` → `sig-ops release-candidate --dsn $SIG_HOSTED_DSN --snapshot …/REPAIRED_SNAPSHOT.json …`; the produced `CANDIDATE_MANIFEST.json` must validate (`consistent`, `plus_zero`, `complete`, `pointer_unchanged: true`); then `implement-spec spec=docs/tickets/188_P32.23a__post-evaluation-release-candidate.md live_verification=true` |

**Carried-forward pre-Round-10 rows (18):** unchanged owners/landings — the row's
own `how to verify` cell in `DEFERRALS.md` is the proof; the command below is
the trigger.

| obligation | blocking domain | RETURN PASS |
|---|---|---|
| `D-P21.3-2` | human (credentials) | export `SIG_MUCKROCK_TOKEN`/`SIG_DATA_GOV_KEY`/`SIG_OVERPASS_ENDPOINT`/`SIG_CIVICCLERK_BASE` in the run shell (Secret Manager holds `sig-muckrock-refresh`, `sig-data-gov-key`), then `implement-spec spec=docs/tickets/P21.3__live-connector-wiring.md live_verification=true` |
| `D-P21.5-1` | human (credentials) | export `SIG_ZENODO_SANDBOX_TOKEN`/`SIG_OBJECT_STORE_*` → `implement-spec spec=docs/tickets/P21.5__infra-deposit-and-tiles.md live_verification=true` (the SWH save-now leg was declined-by-operator 2026-09-16 — repo stays private) |
| `D-P21.7-1` | human (accounts) | MapRoulette account + OSM Organised-Editing page + `SIG_MAPROULETTE_API_KEY` + `registered=true` → the one-step re-run in `docs/build/CONTRIBUTION_BACK_LIVE.md` |
| `D-JURIS.2-1` | human (rights) | reviewer resolves the FR packets (`docs/build/reports/rights/{raa_prefectures,decp_fr,madada}.md`) + the LO 2.0 disposition → record each flip with reviewer+date → `sig-connectors gate --source <id>` green → keyed live run |
| `D-SOURCES.2-2` | human (rights) | reviewer resolves documentcloud's source posture; operator accepts-or-declines the FLP terms → recorded flip/decline → `run --mode live` stops refusing exit 3 |
| `D-SOURCES.7-1` | human (rights) | per-state terms for `dot_511_<st>` resolved (MD additionally needs a LicenseRef row) → `sig-connectors gate --source dot_511_<st>` green |
| `D-SOURCES.7-2` | human (credentials) | per-platform keys exported (Secret-Manager bindings, the P26.4 pattern) → keyed live run; `[[enumerated]]` rows graduate to `[[targets]]` |
| `D-SOURCES.8-1` | human (rights) | remaining `camreg_*` terms resolved (10/14 done under GL-GATE-07; Bellevue non-commercial call + Lexington counsel owed) → `sig-connectors gate --source camreg_<id>` green |
| `D-SOURCES.8-2` | human (credentials) | per-platform keys exported → keyed live run |
| `D-SOURCES.9-1` | human (rights) | Chicago portal terms fetched/quoted into `docs/build/reports/rights/procportal_chicago_il.md` → gate green → live run |
| `D-SOURCES.9-2` | external + rights | a tenant's robots policy lifts or a reviewer records an ADR-083-class API-mode basis → live fetch |
| `D-SOURCES.9-3` | external | a documented public endpoint/API emerges with reviewable terms → live fetch |
| `D-SOURCES.9-4` | human (rights) | `bidnetdirect.com/terms` quoted into `docs/build/reports/rights/bidnet_direct.md` → gate green → live run |
| `D-SOURCES.12-1` | human (rights) + engineering | `camreg_stalbert_ab` licence text captured verbatim + gated-row terms resolved from the recorded `licence_verbatim` evidence → gate green → the reviewed artifact's `spdx=null`/`blocker` rows are the enumerable worklist |
| `D-FEDERAL.1-1` | hosted (scheduled) | the monthly `sig-sched-sam-gov` cron fires → GCS run row `outcome=ok` with `claims_added` → a +0 re-run check; or an operator api.data.gov key-tier upgrade unblocks early |
| `D-R7.1-AUTH` | human (operator decision) | demonstrated demand + ratified moderation/safety/threat model → author a new ADR + ticket for external-IdP OAuth (pseudonymous id + tier only, no passwords/PII) |
| `D-R7.2-SEND` | human (operator + consenting filer) | a consenting residency-valid `Filer` bound → `RecordsRequestGenerator.generate(gap, filer)` emits → the operator files through the jurisdiction's channel → `sig-tasks records-outcomes record` (BL-028) |
| `D-P31.4-1` | hosted (date-bound) | after the 2026-10-10T03:35Z cron: the batch-05 run rows under `gs://…-sig-restricted/ops/runs/camreg_osm_surveillance/2026-10-10/` show `outcome` ok/partial + `fetches` 158 + `claims_added` ≈ 1.37M (the row's exact verify command in `DEFERRALS.md`) |

**Scheduled (not a deferral):** `SIG-MEM-004` — owner **P33.8** (manifest row
200): `implement-spec spec=docs/tickets/200_P33.8__round10-agent-docs-refresh.md live_verification=false` when the chain reaches it — docs refresh after P33.5–P33.7 land.

## Addendum — DATE CORRECTION (SEED-15, appended 2026-10-01T16:55:17Z; ADR-146; append-only)

- *Agent record (labelled): written by Claude Code, harness `claude-code/claude-opus-5-5/subagent`, Round-11 Stage-B
  unit SEED-15.* The lines above are not edited. The row maps a date this record carries that was not taken from a clock
  to the true time (git committer time of the signing commit; the operator confirmed the date at GATE-P, C-1 / Q-B1-2),
  per the date-correction register `docs/build/reports/memory-repair/date_corrections.csv` (carry item β/14a).

| corr | line | recorded → true (UTC) | evidence | register rec |
|---|---|---|---|---|
| DC-OR-01 | L266 | GATE-G3 signature: recorded 2026-10-19 → true 2026-09-28T03:49:14Z (spec Appendix G.7.4 R11-C1; ADR-146 event row 33) | G3SIGN: commit `95c8a73f` "docs(build): GATE-G3 signed …" (committer 2026-09-27T23:49:46-04:00 = 2026-09-28T03:49:46Z) | 210 |
