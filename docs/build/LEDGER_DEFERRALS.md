# LEDGER_DEFERRALS — everything the 44 ledgers (and, where a ledger is a stub, the PR body) admit was not done, done differently, deferred, or never run

- **Produced:** 2026-09-08, planning-only session (Phase A, read-only). Companion to `BUILD_INDEX.md`.
- **Method:** three read-only subagents read every ledger in full with a fixed extraction schema (non-met gap rows; deferrals/TODOs; deviations; human prerequisites; surprises); PR bodies `gh pr view N --json body` grepped for `live|docker|testcontainer|uvicorn|curl|served|preview|playwright|chromium|not run|skipped|fixture` where the ledger was a stub. Hand spot-checks in `BUILD_INDEX.md` §A.6.
- **Ids:** `LD-V` verification gaps · `LD-F` deferred/not-wired functionality · `LD-D` deviations · `LD-H` handoff seams between tickets (decomposition-time "X is PYY's job" statements; P19.2 must confirm each landed) · `LD-P` human prerequisites · `LD-X` other findings · `LH` ledger hygiene. Every row names its **source path:line** and a **suggested landing** (P19.2 gap analysis / P19.3 composed verification / P19.4 closure / P20.1 backlog / P20.2 spec reconciliation / P21.x operationalization). Landing is a suggestion for Phases C–G, not a decision.
- Paths abbreviated: `L=` `.agents/scratch/`, `S=` `scratch/`.

## 1. LD-V — verification gaps (implement-spec 5.3 never crossed a real surface)

Roll-up is in `BUILD_INDEX.md` §A.3 (15 run / 18 fixture-only / 3 n-a / 10 not-recorded). Rows below are the ones with a *drivable* surface that was not driven, plus caveats on "run" rows.

| Id | Ticket | What was not driven live | Source | Landing |
|---|---|---|---|---|
| LD-V01 | **P06.1** (hard gate) | The vertical slice ran "Docker-free" over committed fixtures; the retrospective is the gate artifact, the composed path never touched PG/OCFL/API/web | ledger `L=implement-spec_devin-p06-1-vertical-slice_20260901.md:38` ("Evidence log — TBD Phase 5"); PR #16 "J-1 acceptance query runs in CI without Docker … live acquisition is P07/P11" | P19.3 (composed E2E over the real stack is the retro-fit of this gate) |
| LD-V02 | P00.2, P00.4, P01.1, P07.1 | CLIs exist (`python -m policy …`, `sig-connectors validate`, `sig-ontology generate --check`, `sig-parsing classify`) but no drive recorded | `S=ledger_p00-2.md` (4 lines); no P00.4 ledger; `L=implement-spec_devin-p01-1-ontology-as-code_20260827.md:38`; `L=ledger_p07-1.md:38` | P19.3 (cheap CLI matrix) |
| LD-V03 | P04.2, P04.3, P07.2, P11.1, P11.2, P18.2 (all connectors) | Every connector was driven over committed fixtures only; no connector has ever executed FETCH against a real source except P07.3's USAspending trace | PR #12 "no live network"; PR #13; PR #18 (RISK-P7-10 live token mint "Owner: ops/live-run"); PR #27 "No live fetch / DB wiring in CI"; `L=…p11-2…:68`; `L=…p18-2…:66`; PR #46 "sources `ingestion_permitted=false`" | P19.3 (fixture replay through the *real* pipeline into PG); P21.x (real fetch, rights-gated) |
| LD-V04 | P05.1, P05.2 | ER matcher and review queue run on in-package data / JSONL; "ER not DB-wired"; no live PG round-trip | `L=ledger_p05-1.md:96,104`; `L=ledger_p05-2.md:43` | P19.3 |
| LD-V05 | P08.1, P08.2, P08.3, P09.1, P10.1, P10.2, P10.3, P12.2, P13.1, P13.2 | Whole reconcile/inference/tasks layer is pure-Python value objects "aligned to graph_annotations.sql" — never persisted to or read from the real DB tables they mirror | `L=implement-spec_P08.1-resolver.md:23`; `L=implement-spec_p08-2_ledger.md:7,25`; `L=…p08-3…:81`; `L=…p09-1…:19`; `L=…p10-1…:6-7`; `L=…p12-2…:38-39`; `L=…p13-1…:69`; `L=implement-spec_p13-2-policy-legal_20260901.md:31` | P19.3 (DDL ↔ dataclass alignment test over live PG) + P19.4 if drift found |
| LD-V06 | P14.1 (run, caveat) | API served live but over an **in-memory ReadStore**; "No DB fetch-by-id layer exists" — the API has never read the claim spine | `L=implement-spec_devin-p14-1-public-api_20260901.md:107-108` | P19.3 / P19.4 (DB-backed ReadStore is a CODE gap, see LD-F06) |
| LD-V07 | P14.2 (run, caveat) | Zenodo = `--zenodo-dry-run`/`FakeZenodo`; object store `cloudflare-r2:sig-bulk` never written; `pyarrow/shapely/pmtiles NOT installed` at build time | `L=implement-spec_devin-p14-2-exports_20260901.md:25,39,114` | P19.3 (install optional deps; real build to local dir); P21.x (real Zenodo sandbox deposit) |
| LD-V08 | P15.x (run, caveat) | Web verified with astro preview / chromium e2e over **fixture data**; never rendered from the live API or exports | `L=…p15-1…:137`; P15.1 ledger L43–47 (dossier/map/watch/corrections routes = later tickets); `L=…p18-1…:56` "Live web render deferred to P15/P18.2" | P19.3 |
| LD-V09 | P16.1, P16.2 | Contributor system + contribution-back "modelled in memory, not yet persisted"; no live MapRoulette client / OSM changeset feed | PR #40 (RISK-P16-07); PR #41 (RISK-P16-14/15); `L=…p16-2…:75` "real filing deferred RISK-P16-13" | P19.3 (what exists) / P21.x (live accounts) |
| LD-V10 | P17.1–P17.3 | "Population is expressibility, not ingestion" — conformance-suite instance graphs, no claim-spine rows (RISK-P17-03) | PR #42; `L=…p17-3…:58` | P20.1 backlog (Stage-5 connectors); accepted as designed |
| LD-V11 | all | `tests/db` (Docker) last recorded green at P14.1 (L51) and P16.1 (L7); not recorded for P17.x–P18.2; not run in the v2 planning session | ledgers; planning ledger §2.1 | P19.3 first step |
| LD-V12 | P18.1 | "Live web render deferred to P15/P18.2 (deterministic AC = model round-trip)" — but P18.2 contains no `web/` work (PR #46 scope) → jurisdiction-conditional publication + BCP-47 labels never rendered | `L=implement-spec_devin-p18-1-international-framework_20260908.md:56` | P19.2 → P19.4 |

## 2. LD-F — functionality deferred / left un-wired (as admitted in ledgers or PR bodies)

| Id | Ticket | Deferred item | Quote / source | Named owner | Landing |
|---|---|---|---|---|---|
| LD-F01 | P02.1 | `claim` table **not partitioned** (§16.2 #6) — PK/FK contract kept instead | "No AC depends on partitioning. Keep FK contract, defer partitioning." `L=implement-spec_p02-1-claim-spine.md:13-15`; ADR-022 | ADR-022 revisit trigger | P20.1 (revisit trigger → backlog) |
| LD-F02 | P02.2 | Live-connector WACZ per PR + connector-level reproducibility | "Scaffolded (documented RISK-P2-09/10): live-connector WACZ per-PR and connector-level reproducibility land P04+/P08." `L=…p02-2…:46` | P04+/P08 | P19.2 (verify landed) |
| LD-F03 | P04.2 | Live HTTP transport for `osm`; `PoliteFetcher` 429-as-challenge vs Overpass 429/504 semantics; OCFL `CaptureStore` adapter | PR #12: "reconciling the shared `PoliteFetcher` … + the OCFL `CaptureStore` adapter + a live HTTP transport are the live-wiring ticket — **RISK-P4-06**" | "live-wiring ticket" (none exists) | P20.1 → P21.x |
| LD-F04 | P05.1 | ER **not DB-wired**; data-quality check realised as an ER-run gate, not a pipeline/DB check | `L=ledger_p05-1.md:66,96` ("noted in risk register RISK-P5") | — | P19.4 / P20.1 |
| LD-F05 | P05.2 | Curation UI is **CLI + JSONL queue**; "web/ deferred to P15" — no P15.x ticket builds a curation/review web surface (manifest rows 35–39) | `L=ledger_p05-2.md:12-13`; ADR-030 | P15 (never picked up) | P19.2 (MISSING vs §? curation UI reqs) → P20.1 or P20.2 |
| LD-F06 | P14.1 | **DB-backed ReadStore** absent; API contract exists over an in-memory implementation | `L=…p14-1…:107-108` | — | P19.4 (CODE gap on the critical path to "one jurisdiction live") |
| LD-F07 | P14.2 | Rendered vector tiles (tippecanoe-class) "deferred to the map surface (Phase 15)"; P15.3 then lists "tile-gen pipeline" as **out of scope** → **nobody owns tile generation** | `L=…p14-2…:106-107`; `L=…p15-3…:80` | Phase 15 → nobody | P19.2 → P19.4 or P20.1 |
| LD-F08 | P14.2 | `derivative_permitted` not in the export gate; "expanding that shared gate is P00.4's contract" (P00.4 already merged) | `L=…p14-2…:109-110` | P00.4 (closed) | P19.2 → P20.1 |
| LD-F09 | P15.3 | Interactive MapLibre runtime **not shipped** — Lighthouse zero-JS budget is a hard gate; static PMTiles serving contract + zero-JS `/map/` instead | `L=implement-spec_devin-p15-3-map-network_20260908.md:8-22`; ADR-051 | ADR-051 | P20.2 (spec says MapLibre map, ADR-018) / P20.1 |
| LD-F10 | P16.1 | Contributor tiers/submissions/reverts **in memory, not persisted** (ADR-054 revisit trigger, RISK-P16-07); usability study (≥5 naïve users) is an agentic AC not performed | PR #40; `L=…p16-1…:21,43` | ADR-054 | P20.1; LD-P03 |
| LD-F11 | P16.2 | No live MapRoulette client; no OSM changeset feed into `LeverageLedger`; §7 metric page reads fixtures; "real filing deferred RISK-P16-13" | PR #41 (RISK-P16-14/15); `L=…p16-2…:75` | risk register | P21.x |
| LD-F12 | P08.1 | "research-task auto-gen (§33) DEFERRED to tasks/ phase" | `L=implement-spec_P08.1-resolver.md:37` | P10.x | P19.2 (verify P10.1 closes it) |
| LD-F13 | P09.1 | "UI half honestly deferred to P15.5 (RISK-P9-08, ADR-038)" | `L=…p09-1…:73` | P15.5 | P19.2 (verify P15.5 methodology page covers §32 metrics) |
| LD-F14 | P10.3 | Residency fact uses `absence_kind="not_researched"` because P09.1's absence vocabulary is frozen ("Cannot add a new absence_kind") | `L=…p10-3…:40-45`; ADR-041 | ADR-041 | P20.2 (spec §32.2 wording) |
| LD-F15 | P12.2 | `inference` CLI "is skeleton (no subcommands wired for existing modules) -> won't wire CLI" | `L=…p12-2…:21` | — | P20.1 |
| LD-F16 | P07.2 | Live MuckRock token mint + real HTTP transport (RISK-P7-10); extraction engine deliberately not run on released docs | PR #18 L17, L20, L40 ("Owner: ops/live-run") | ops/live-run | P21.x |
| LD-F17 | P07.1 | Parser layers 1–5 "deferred to connectors per ADR-033" | `L=ledger_p07-1.md:39` | connectors | P19.2 (which connectors implement which layer?) |
| LD-F18 | P11.2 → P12.1 | Aggregates landed in P11.2 without the DuckDB substrate (RISK-P11-13/14/15 handoff) — landed in P12.1 | `L=…p11-2…:19`; `L=…p12-1…:12` | P12.1 (done) | closed — record in P19.2 as MET |

## 3. LD-D — deviations from the spec recorded in ledgers (all say "ADR written"; Phase D dispositions each)

| Id | Ticket | Deviation | Source | ADR (repo #) |
|---|---|---|---|---|
| LD-D01 | P02.1 | tstzrange + GiST EXCLUDE instead of ticket wording "native PERIOD/WITHOUT OVERLAPS" (PG18 has no temporal PKs); physical DDL authored as sqitch, not generated from LinkML (SIG-STORE-045 tension) | `L=implement-spec_p02-1-claim-spine.md:16-17,49` | ADR-022 (+ note only for SIG-STORE-045) |
| LD-D02 | P02.2 | New `evidence` package layout; `evidence_capture` uniqueness relaxed → `evidence_blob` dedup model | `L=…p02-2…:38,40` | ADR-023 |
| LD-D03 | P05.1 | "ADR drift: spec Appendix F logical 'ADR-016 = Splink'; repo ADR-016 already = dagster" → Appendix F numbering ≠ repo numbering | `L=ledger_p05-1.md:15-16` | ADR-029 (Phase D: Appendix F correction) |
| LD-D04 | P05.2 | Curation UI = CLI + JSONL (see LD-F05) | `L=ledger_p05-2.md:12-13` | ADR-030 |
| LD-D05 | P06.1 | Minimal count-reconciliation ahead of Phase 8; minimal dossier renderer ahead of Phase 15 (superseded by P15.2, kept for back-compat); 3 count predicates added to `predicates.yaml` (registry incompleteness = retrospective finding) | `L=…p06-1…:62,65-67` | ADR-031, ADR-032 (ledger says "ADR-024/025") |
| LD-D06 | P07.2 | `connectors.net` Fetcher/PoliteFetcher/Transport extended with optional per-request headers (additive) | `L=…p07-2…:27` | ADR-034 |
| LD-D07 | P08.3, P09.1, P10.1, P10.2, P10.3 | Contradiction / coverage / task entities as pure-Python value objects, **no Postgres persistence** (precedent chain ADR-031→036→037→038→039) | `L=…p08-3…:81`; `L=…p09-1…:14,19` | ADR-037, 038, 039 |
| LD-D08 | P10.3 | `not_researched` absence kind for residency barrier (see LD-F14) | `L=…p10-3…:40-45` | ADR-041 |
| LD-D09 | P14.2 | PMTiles as v3 archive with ODbL layer metadata, no rendered tiles; `derivative_permitted` not gated | `L=…p14-2…:106-110` | ADR-048 |
| LD-D10 | P15.1 | OSI licence gate: `OSI_ALLOW` vs documented `WAIVED{CC0-1.0,BlueOak-1.0.0}` | `L=…p15-1…:64` | ADR-049 |
| LD-D11 | P15.3 | Zero-JS static map instead of interactive MapLibre (see LD-F09) | `L=…p15-3…:8-22` | ADR-051 |
| LD-D12 | P18.1 | `canonical_name` scalar vs multivalued — "deliberate deviation (spec-faithful §11.2; P01.1 ownership; back-compat)" | `L=…p18-1…:71` | ADR-056 |
| LD-D13 | P18.2 | DECP `end_date` unset (derivable from `dureeMois`); amendments kept in `raw` (no `ProcurementState`) | PR #46 L21 | ADR-057 |
| LD-D14 | P14.1→P12.1 | Post-hoc hardening of P12.1's analytics boundary landed on **P14.1's branch** (`4493b14`): reason_raw, rights_record, forbidden org-id columns, COMPLEMENTARY rationale (SIG-STORE-028/030/031, §11.16, §18.4) | `L=p_analytics_hardening_commit.txt:1-9`; `git log devin/p13-2-policy-legal..devin/p14-1-public-api` | none (no ADR; P12.1's ADR-044 not amended) |

## 4. LD-H — handoff seams ("X is ticket Y's job") that P19.2 must confirm were picked up

| Id | From → To | Statement | Source | Known status now |
|---|---|---|---|---|
| LD-H01 | P01.1/P02.1/P02.3 → P08.1 | "obs->validity NOT done (P08.1)" / "resolver write logic (P08.1, table+constraints only here)" | `L=…p02-3…:67-68`; `L=implement-spec_p02-1-claim-spine.md:50` | P08.1 landed; whether it **writes** the `resolution` table (vs value objects, LD-V05) is unverified |
| LD-H02 | P02.2 → P04+/P08 | live-connector WACZ per PR; connector-level reproducibility | `L=…p02-2…:46` | unverified |
| LD-H03 | P04.1 → P04.2 | "SIG-INGEST-021 plain-CLI stages; orchestrator confined — met (per-connector runner P04.2)" | `L=implement-spec_p04-1_20260827.md:99` | P04.2 has no ledger; verify in code |
| LD-H04 | P05.2 → P15 | curation web UI | `L=ledger_p05-2.md:12` | **not picked up** (no P15.x scope) — LD-F05 |
| LD-H05 | P06.1 → P15.2 | production dossier supersedes slice renderer (kept) | `L=…p06-1…:13,59`; `L=…p15-2…:19-21` | landed (P15.2) |
| LD-H06 | P08.1/P08.3/P09.1/P10.1/P13.1 → P14.1 | public API endpoint for contradictions, coverage statement, tasks, accountability | `L=…p08-3…:43,86`; `L=…p09-1…:40-44`; `L=…p10-1…:32-36`; `L=…p13-1…:27-30` | P14.1 ships a contract over in-memory store — verify each endpoint exists (LD-F06) |
| LD-H07 | P09.1 → P15.5 | methodology/coverage web pages for §32 metrics | `L=…p09-1…:73,82` | P15.5 shipped methodology pages — verify §32 metric coverage |
| LD-H08 | P14.2 → P15.3 → ∅ | vector-tile rendering | `L=…p14-2…:106`; `L=…p15-3…:80` | **orphaned** — LD-F07 |
| LD-H09 | P14.2 → P00.4 | `derivative_permitted` gate expansion | `L=…p14-2…:109-110` | orphaned (P00.4 closed) — LD-F08 |
| LD-H10 | P16.2 → P10.3 | records-request link (SIG-CONTRIB-019) | `L=…p16-2…:87` | verify |
| LD-H11 | P18.1 → P15/P18.2 | live web render of jurisdiction-conditional publication | `L=…p18-1…:56` | **not picked up** — LD-V12 |
| LD-H12 | P17.x → "Stage-5 connectors" | live population of federation/RTCC/FR/CSS/acoustic/drone/location pathways | PR #42 (RISK-P17-03) | no ticket exists — P21.x candidates |
| LD-H13 | P11.1/P11.2/P12.2 → P08.2 | §29.3/§29.7 sharing-edge + snapshot-diff logic owned by P08.2, consumed downstream (manifest ownership note) | `docs/tickets/00_MANIFEST.md:99`; `L=…p11-2…:35-39` | verify no re-implementation (P19.2 seam hunt) |

## 5. LD-P — human prerequisites surfaced by ledgers / PR bodies (not code)

| Id | Item | Source | Landing |
|---|---|---|---|
| LD-P01 | Stage-0 outreach to the 19 compact projects; `no_response` recorded; consumed by P00.4 `CompactStatus` (SIG-CONTRIB-012/012a/013 "Stage-0 outreach (connectors CompactStatus/sources.toml …)") | manifest "Human prerequisites"; `L=…p16-2…:87` | P21.x gate |
| LD-P02 | Legal home identified (SIG-GOV-012); legal items referred to counsel before launch (SIG-LIC-009, risk register Phase 0 L8–19) | manifest; `docs/risk_register.md:8-36` | P21.x gate |
| LD-P03 | Moderated usability study (≥5 naïve contributors, median ≤10 min, protocol + results published) — P16.1 AC7 (agentic), not performed | `L=…p16-1…:21,43` | P21.x |
| LD-P04 | MapRoulette account + API doc + account-holder disclosure; Organised Editing activity **registration** (`registered` flag) | `L=…p16-2…:31,33` | P21.x |
| LD-P05 | Rights reviews flipping `ingestion_permitted` for every source currently `false`/`UNDETERMINED` (FR/BE sources explicitly `ingestion_permitted=false`; MuckRock token; Overpass etiquette) | PR #46 L40; PR #18 L40; PR #12 L21 | P21.x (Phase F counts them via `sig-connectors validate`) |
| LD-P06 | Infra accounts: Zenodo (concept DOI), object store (`cloudflare-r2:sig-bulk` named in CLI, ADR-015 says S3/CloudFront), Docker-capable CI runner for `tests/db` | `L=…p14-2…:114`; ADR-015 | P21.x / Phase E CI_STATUS |
| LD-P07 | Zero-cost CI mode (R-11) keepalive / tested degraded mode "owned …" downstream | PR #1 L21 | P20.1 |

## 6. LD-X — other findings

| Id | Finding | Source | Landing |
|---|---|---|---|
| LD-X01 | Spec-amendment edit (32→34 task types) sat **uncommitted in the working tree** through P00.1–P02.3 and was excluded/stashed per ticket; manifest records it as applied 2026-08-26 | `S=implement-spec_p00-1_ledger.md:60`; `L=implement-spec_p00-3_20260827.md:6-7`; `L=…p02-3…:8`; manifest L101–102 | P19.2 confirm the committed spec carries it (v2 session verified BUILD.sh byte-identical → yes) |
| LD-X02 | Uncommitted P12 WIP (`db/analytics.py`, `db/suppression.py`, `tests/db/*`) present on the base during P13.1 and P13.2, deliberately unstaged; later landed as `4493b14` on P14.1's branch (LD-D14) | `L=…p13-1…:6-7`; `L=implement-spec_p13-2-policy-legal_20260901.md:5-6` | Phase E (integration): confirm nothing else was left behind (`git status` clean at tip ✔) |
| LD-X03 | `verify-gen` "fails only on uncommitted generated artifacts (expected — passes once committed)" — gate semantics depend on commit state | `L=…p18-2…:64`; `L=…p01-1…:38`; `L=…p02-2…:43` | P20.1 (docs-drift / DX) |
| LD-X04 | Ledger ADR numbers use spec Appendix-F logical numbering in P02.1 ("ADR-012/013"), P05.1, P06.1 ("ADR-024/025"), P16.2 ("ADR-017 (repo ADR-055)") → Appendix F ↔ `docs/adr/` mapping is inconsistent | ledgers; `docs/adr/` | Phase D → P20.2 |
| LD-X05 | P08.1 has **no ADR and no risk-register section**; P13.1 no ADR (claims no deviation) | `docs/risk_register.md` headings (Phase 8 starts at P08.2, L460); ADR `**Phase:**` fields | P19.2 → P19.4 (phase-gate §51.3 completeness) |
| LD-X06 | P04.1 self-review closed a DNS escape hatch in network isolation (`getaddrinfo`/`gethostbyname*`) — isolation guarantees depend on this guard list | `L=implement-spec_p04-1_20260827.md:106` | P19.3 (re-prove ISOLATION on the composed stack) |
| LD-X07 | P01.1 RDF generators nondeterministic → canonicalised via `rdflib.compare.to_canonical_graph` | `L=…p01-1…:60-61` | none (accepted; note for AGENTS.md) |
| LD-X08 | P07.3 is the only ticket that fetched a **real external source** live (USAspending, public-domain federal data) | PR #19 L22, L32 | P19.2: confirm `ingestion_permitted` for `usaspending` was true at the time |
| LD-X09 | `.devinignore` (untracked) re-includes `docs/tickets/` + `.agents/scratch/` for agent tools; if tickets become committed (T4) its first two lines become redundant | `git status`; `.devinignore` | P19.1 |
| LD-X10 | Manifest row 25 still says "32/34 detectors" although the amendment fixed the count to 34 | `docs/tickets/00_MANIFEST.md:71` | P19.1 (manifest amendment) |
| LD-X11 | `_TEMPLATE.md` says "Sequence: <n> of 43"; chain is 46 | `docs/tickets/_TEMPLATE.md:9` | P19.1 (already in the draft) |

## 7. LH — ledger hygiene (why "retro live verification" needs P19.3 rather than a re-read)

| Id | Ticket | Condition | Source |
|---|---|---|---|
| LH-01 | P00.2 | 4-line resume anchor; no plan/gap/evidence | `S=ledger_p00-2.md` |
| LH-02 | P00.4, P04.2 | no ledger at all | — |
| LH-03 | P06.1 | "Evidence log — TBD Phase 5" | `L=…p06-1…:38` |
| LH-04 | P07.2 | "Phase status: 0-4 done. Phase 5 verification + 6 PR next." (never updated) | `L=…p07-2…:48` |
| LH-05 | P07.3 | 16 lines, "Status: implementing" | `L=implement-spec_p07-3.md:16` |
| LH-06 | P08.2 | "Gap table: TBD / Evidence: TBD" | `L=implement-spec_p08-2_ledger.md:25` |
| LH-07 | P12.2 | gap table + evidence log "TBD" | `L=…p12-2…:38-39` |
| LH-08 | P13.2 | "Test matrix / gap table / evidence — filled during run." (never filled); gap table shows 4 GAP rows as the *plan*, closure unrecorded | `L=implement-spec_p13-2-policy-legal_20260901.md:14-21,31` |
| LH-09 | P15.2 | gap table + evidence "(tbd)", all phase boxes unticked | `L=…p15-2…:12-16,61-63` |
| LH-10 | P16.1 | gap table + evidence "TBD", every deliverable/AC box unticked | `L=…p16-1…:12-16,37-66` |
| LH-11 | P17.2 | gap table / evidence sections empty | `L=…p17-2…:43-45` |
| LH-12 | P10.1, P10.3, P13.1 | AC/requirement checkboxes left `[ ]` despite green gates | `L=…p10-1…:11-30`; `L=…p10-3…:19-22`; `L=…p13-1…:22-25` |
| LH-13 | P14.2, P15.3, P15.4 | phase-status blocks self-contradictory (both `[x]` and `[ ]` for the same phase; Phase 6 ticked before 1–5) | `L=…p14-2…:146-151`; `L=…p15-3…:55-62`; `L=…p15-4…:49-51` |
| LH-14 | P05.1 | "AC6 phase-gate — MET (pending full `make check` after commit)" | `L=ledger_p05-1.md:96` |
| LH-15 | P18.1 | "final run pending after regen (green gate Phase 6.0)" — final make check recorded later at L83 (2322) | `L=…p18-1…:75,83` |

For these tickets the PR body (`gh pr view N`) is the better evidence record; P19.1's BUILD_INDEX should link both, and P19.3 should treat every LH row as "evidence must be regenerated, not trusted".

## 8. Counts

- LD-V 12 · LD-F 18 · LD-D 14 · LD-H 13 · LD-P 7 · LD-X 11 · LH 15 → **90 rows**, each with a source.
- Rows already closed by a later ticket (recorded so P19.2 can mark them MET): LD-F18, LD-H05.
- Rows with **no owner anywhere** (orphaned seams): LD-F05/LD-H04 (curation web UI), LD-F07/LD-H08 (tile generation), LD-F08/LD-H09 (`derivative_permitted` gate), LD-V12/LD-H11 (jurisdiction-conditional web render), LD-F03 (osm live wiring), LD-H12 (Stage-5 connectors), LD-X05 (P08.1 §53 section).
