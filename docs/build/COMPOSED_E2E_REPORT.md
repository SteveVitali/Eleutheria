# COMPOSED_E2E_REPORT — the whole build driven as one unit (P19.3, CAPSTONE step 3)

The first time the SIG build is exercised end-to-end as a single composed stack, plus the
retroactive `implement-spec` Phase-5.3 live verification that 28 tickets skipped or ran over
fixtures only. The composed suite lives at `tests/e2e/test_composed_stack.py` (Docker-gated) and
`tests/e2e/test_isolation_reproof.py` (LD-X06); it is driven by
`SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e -ra`.

> **Never fabricate green (orchestrate-build §3.1).** A seam that *exists but has never been wired
> together* is recorded as an `xfail` whose reason begins with its `LEDGER_DEFERRALS` id
> (`^LD-[A-Z]+[0-9]+[a-z]?:`) — never a loosened or removed assertion. The composed run's result is
> only `passed` + `xfailed` (0 failed, 0 skipped under `SIG_REQUIRE_DB_TESTS=1`). Contradictions
> stay **visible** (S5), never collapsed.

Headline run (this machine): **`10 passed, 4 xfailed in 10.16s`** — 0 failed, 0 skipped. The full
gate is green too: `make check` → **`2378 passed, 4 xfailed`** (baseline 2365 + 17 new: 8 composed +
6 isolation + 3 SPDX-header params; 13 pass + 4 xfail).

## (a) Environment

| item | value |
|---|---|
| Docker | client/server **29.1.3** (`docker info` OK — the ticket's stated precondition) |
| PG image | `postgis/postgis:18-3.6` @ `sha256:8d67cc8fe5f45808d54fe95cc210b05ce6b3ea3682e9a97c36362f3e1b8ff939` |
| sqitch image | `sqitch/sqitch:latest` @ `sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3` |
| uv | `0.12.6 (7938ca5d5 2026-08-25 aarch64-apple-darwin)` |
| Python | 3.12.14 (workspace venv) |
| node / npm | `v25.2.1` / `11.6.2` |
| pytest | 9.1.1 |

Harness: `tests/e2e/conftest.py` reuses the **exact** claim-spine Docker/testcontainers + sqitch
harness (`tests/db/conftest.py`) — the schema is stood up with the real `db/sqitch.plan` on a shared
Docker network exactly as production would (§20.4, §48; SIG-STORE-024/041). `_require_or_skip` is
imported from that file, not re-invented: without a daemon the module skips, and with
`SIG_REQUIRE_DB_TESTS=1` a missing daemon is a hard failure.

## (b) Seam table S1–S8

| # | seam | verdict | evidence / anchor | closing command (if xfail) |
|---|---|---|---|---|
| S1 | PG18+PostGIS claim spine — deploy `db/sqitch.plan` into a fresh `postgis/postgis:18-3.6`; append-only preserved through the composed DB path | **crossed** | 8 spine tables present (`claim`,`entity`,`evidence_artifact`,`evidence_capture`,`resolution`,`contradiction`,`coverage_record`,`research_task`); `postgis_version()` non-null; UPDATE `claim` → *immutable*, DELETE → *DELETE forbidden* (SIG-STORE-011/012, P1–P3) | — |
| S2 | OCFL evidence store — capture the 10 OKC fixture artifacts as evidence objects | **crossed** | `OcflStore` over a tmp `LocalFileStore`; 10 OCFL 1.1 objects, each `resolve(v1)` round-trips to its bytes; inventory `digestAlgorithm=sha512`, `head=v1` (§17.3, SIG-EVID-005) | — |
| S3 | connector → claim spine — replay `atlas` + `osm` over committed fixtures via `replay()` with a claim sink | **xfail(LD-F06b)** | live run asserts claims into `InMemoryClaimSink`; network-isolated `replay()` reproduces the claim set byte-for-byte (SIG-INGEST-003/017/018). Only `InMemoryClaimSink` exists (`connectors/stages.py:280`) | **P19.4** — write a PG `ClaimSink` (`SIG-INGEST-016/017`) |
| S4 | entity resolution — `ProbabilisticMatcher.match` over the slice orgs; `ReviewQueue.enqueue/decide` round-trip | **xfail(LD-F04)** | Splink/DuckDB matcher returns tier-4/5 **PROPOSED** proposals (never auto-writes, SIG-IDENT-020); review queue enqueue→decide is append-only and records the human reviewer (SIG-IDENT-026); re-decide refused. Nothing persisted to PG | **P19.4** — DB-wire ER matches + review decisions |
| S5 | reconciliation resolver — `RESOLVE` keeps the 299-vs-190 `claimed_device_count` contradiction **visible** | **crossed** | `RESOLVE` → `UNRESOLVED` / `CONTESTED` / `contradiction_state=unresolved_conflict`, `value is None` (NOT collapsed to one number); both DeFlock 299 and Chief Bacy 190 retained in `considered_claim_ids` (§3.1, P06.1 retrospective) | — |
| S6 | API — `create_app(store)` served **live** (real uvicorn); every §37.3 family answers 200 | **xfail(LD-F06)** | live uvicorn on an ephemeral port hit with real `httpx`: `/v1/resolution/agency:okcpd/active_device_count` → 200 with `{fact,coverage,attribution,as_of}` envelope (SIG-API-002/005); `dossier`,`coverage`,`contradiction`(+id),`task`(+id),`/id/agency/okcpd` all 200. Served over `InMemoryStore` (`api/store.py:147`) | **P19.4** — DB-backed `ReadStore` (`SIG-API-001/002`, `SIG-TIME-008`) |
| S7 | exports — `sig-exports build --zenodo-dry-run` into a tmp dir | **crossed** | real `sig-exports` subprocess, rc 0; ODbL geo compartment `osm_physical/devices.pmtiles` written **separately** from `sig_graph/claims.parquet` (licence split, SIG-LIC-004a); summary licences `{ODbL-1.0, CC-BY-4.0}`; dry-run Zenodo concept vs version DOI split (SIG-EXPORT-002) | — |
| S8 | web — `npm --prefix web run build`; the dossier route for the slice jurisdiction is emitted | **xfail(LD-V08)** | `npm run build` rc 0 (31 pages); `web/dist/dossier/oklahoma-city/index.html` exists and contains "Oklahoma City". `web/` renders from `web/src/lib/*-fixture.ts`, **not** the S7 export bytes | **P21.4** — web reads exports/API (`SIG-UI-010`, `SIG-PUB-007`) |

**4 crossed** (S1, S2, S5, S7) · **4 xfail** (S3 LD-F06b, S4 LD-F04, S6 LD-F06, S8 LD-V08). This is
exactly the DECISION_MEMO §2/§6 prediction: the composed path stops at the PG/API spine seam.

## (c) Retro 5.3 table — one row per ticket that skipped or ran fixture-only (18 + 10 = 28)

Legend: **fixture-only (18)** = ran in-process / CLI over committed fixtures labelled "live";
**not-recorded (10)** = ledger + PR said nothing (BUILD_INDEX §A.3). For every ticket carrying an
`LH-*` ledger-hygiene row, the evidence below was **regenerated here; the ledger is not trusted**
(LEDGER_DEFERRALS §7).

### fixture-only (18)

| # | ticket | what was driven now | command / seam | result |
|---|---|---|---|---|
| 1 | P00.3 governance-policies | policy pack validated | `python -m policy validate` (matrix) | rc 0 — "crawler conduct rules: 8" |
| 2 | P03.2 deterministic-er | org-name normalisation | `sig-resolution normalize LAPD` (matrix) | rc 0 — "los angeles police department" |
| 3 | P04.2 osm-connector | replay over `overpass_snapshot.json` through the real pipeline (S3) | composed S3 | crossed (in-mem); PG write **xfail LD-F06b** |
| 4 | P04.3 atlas-connector | replay over `adoption_feed.csv` through the real pipeline (S3) | composed S3 | crossed (in-mem); PG write **xfail LD-F06b** |
| 5 | P05.1 probabilistic-er *(LH-14)* | `ProbabilisticMatcher.match` over slice orgs (S4) | composed S4 | crossed (in-mem); DB-wire **xfail LD-F04** — evidence regenerated, ledger not trusted |
| 6 | P05.2 curation-ui | `ReviewQueue.enqueue/decide` round-trip (S4) + `review list` | composed S4 + matrix | crossed (in-mem); `review list` rc 0 |
| 7 | **P06.1 vertical-slice (HARD GATE)** *(LH-03)* | composed retro-fit of the gate: OCFL evidence (S2) + RESOLVE contradiction visible (S5) | composed S2+S5 (LD-V01) | crossed — evidence regenerated, ledger not trusted |
| 8 | P07.2 records-connectors *(LH-04)* | connector registry + loader gate | `sig-connectors list-connectors` / `gate` (matrix) | rc 0 / rc 1 (gate correctly REFUSES) — ledger not trusted |
| 9 | P08.1 resolver | `RESOLVE` runs the §28 phase pipeline (S5) | composed S5 + `python -m reconcile --help` | crossed |
| 10 | P08.3 contradiction-object | contradiction emitted & kept visible (S5) | composed S5 | crossed |
| 11 | P10.1 task-engine *(LH-12)* | task CLI skeleton | `python -m tasks --help` (matrix) | rc 0 — ledger not trusted |
| 12 | P10.2 detector-catalog | reconcile detector surface | `python -m reconcile --help` (matrix) | rc 0 |
| 13 | P11.1 flock-portal | fixture connector via the S3 replay class | composed S3 pattern + `list-connectors` | crossed (in-mem) |
| 14 | P11.2 audit-structural | usage-analytics schema (no plate/name column) | `sig-db analytics assert-schema` (matrix) | rc 0 — schema OK |
| 15 | P12.2 network-inference *(LH-07)* | inference CLI skeleton | `python -m inference --help` (matrix) | rc 0 — ledger not trusted; P19.5 correlates |
| 16 | P13.1 accountability *(LH-12)* | accountability contradiction/task served via API (S6) | composed S6 `/v1/contradiction` | 200 (in-mem store); **xfail LD-F06** — ledger not trusted |
| 17 | P18.1 international-framework *(LH-15)* | jurisdiction adapters US/FR/UK/BE | `python -m policy jurisdiction` (matrix) | rc 0 — "BE OK 11/11" — ledger not trusted |
| 18 | P18.2 france-belgium | export licence compartments | `sig-connectors export-check` (matrix) | rc 0 |

### not-recorded (10)

| # | ticket | what was driven now | command / seam | result |
|---|---|---|---|---|
| 19 | P00.1 repo-skeleton | CI-mirror gate (no runtime surface) | `make check` | green — 2378 passed, 4 xfailed |
| 20 | P00.2 policy-as-code *(LH-01)* | policy pack validated | `python -m policy validate` (matrix) | rc 0 — ledger not trusted |
| 21 | P00.4 source-registry *(LH-02)* | registry self-check (109 sources) | `sig-connectors validate` (matrix) | rc 0 — ledger not trusted |
| 22 | P01.1 ontology-as-code | generated artifacts vs a fresh generation | `sig-ontology generate --check` (matrix, `PYTHONHASHSEED=0`) | rc 0 — "up to date" |
| 23 | P07.1 parsing-stack | document classification | `sig-parsing classify <fixture>` (matrix) | rc 0 — "plaintext → llm_assisted" |
| 24 | P08.2 reconciliation-workflows *(LH-06)* | resolver + reconcile served via API (S5/S6) | composed S5 + `python -m reconcile --help` | crossed — ledger not trusted |
| 25 | P09.1 coverage | coverage statement served live | composed S6 `/v1/coverage/agency:okcpd` | 200 (in-mem store); **xfail LD-F06** |
| 26 | P10.3 records-request-gen *(LH-12)* | tasks CLI skeleton | `python -m tasks --help` (matrix) | rc 0 — ledger not trusted |
| 27 | P13.2 policy-legal *(LH-08)* | jurisdiction legal regime | `python -m policy jurisdiction` (matrix) | rc 0 — ledger not trusted |
| 28 | P16.2 contribution-back | contributor/api surface (no live MapRoulette — LD-V09) | composed S6 + `python -m policy validate` | 200 (in-mem store) |

Reading: the composed run **converts** the P19.2 AT-RISK-INTEGRATION verdicts into demonstrated
passes (S1/S2/S5/S7) or recorded, LD-tagged CODE gaps (S3/S4/S6/S8). No row is silently upgraded.

## (d) CLI matrix output (`sh docs/build/tools/retro_cli_matrix.sh`)

Script exits **0**, **17 rows** (≥ 14). One `rc=1` row is the loader gate correctly **REFUSING** an
unpermitted source — honest evidence, not a failure:

```
# retro CLI matrix (P19.3, LD-V02) — one drive per stage CLI
# format: rc=<exit code> | <command> | <first line of output>
#--------------------------------------------------------------
rc=0   | python -m policy validate                     | crawler conduct rules: 8
rc=0   | python -m policy jurisdiction                 | adapter BE (be.*): OK — 11/11 checklist items, profile 'BE-GDPR'
rc=0   | sig-connectors validate                       | registered sources: 109
rc=0   | sig-connectors stages                         | 1. discover
rc=0   | sig-connectors list-connectors                | accountability
rc=1   | sig-connectors gate --source osm_overpass     | source 'osm_overpass': REFUSED (SIG-INGEST-014/028)
rc=0   | sig-connectors export-check                   | compartment 'sig_graph': 1 source(s) -> CC-BY-4.0
rc=0   | sig-ontology generate --check                 | ontology artifacts up to date
rc=0   | sig-parsing classify <fixture>                | <tmp>/doc.txt: plaintext → llm_assisted  scanned=False ...
rc=0   | sig-resolution normalize LAPD                 | los angeles police department
rc=0   | sig-resolution review list <queue>            | (no pending proposals)
rc=0   | python -m reconcile --help                    | usage: sig-reconcile [-h] [--version]
rc=0   | python -m inference --help                    | usage: sig-inference [-h] [--version]
rc=0   | python -m tasks --help                        | usage: sig-tasks [-h] [--version]
rc=0   | sig-db analytics assert-schema                | analytics-store schema OK (no plate/name column; UUID + period join keys): ...
rc=0   | sig-exports --help                            | usage: sig-exports [-h] [--version] {provo,build} ...
rc=0   | sig-ops --help                                | usage: sig-ops [-h] [--version]
#--------------------------------------------------------------
rows: 17
retro_cli_matrix OK
```

## (e) CODE-gap handoff — each xfail → an item (P19.4 spine seams · P19.5/P21.x the rest)

Every composed xfail is listed exactly once. The spine-seam rows (claim sink, read store) are the
**P19.4** work; the ER/annotation and web-render rows are **P19.5** or fold into **P21.2/P21.4**
(matching CAPSTONE_GAP_ANALYSIS §i).

| seam | xfail (LD id) | requirement ids | owner | the CODE change P19.x makes |
|---|---|---|---|---|
| S3 connector → claim spine | **LD-F06b** | `SIG-INGEST-016`, `SIG-INGEST-017` | **P19.4** (spine) | implement a PG `ClaimSink` so `pipeline.run` writes connector claims into the `claim` table; the S3 xfail flips to an assert on PG rows |
| S6 API → claim store | **LD-F06** | `SIG-API-001`, `SIG-API-002`, `SIG-TIME-008` | **P19.4** (spine) | implement a DB-backed `ReadStore` over the claim spine; the S6 xfail flips to an assert that the API served from PG |
| S4 entity resolution | **LD-F04** | `SIG-EPIS-018`, `SIG-RECON-039`, `SIG-RECON-040` | **P19.5** (rest; `P19.4:S` / P21.2) | persist ER matches + review decisions (annotation entities); the S4 xfail flips to an assert on persisted rows |
| S8 web → data | **LD-V08** | `SIG-UI-010`, `SIG-PUB-007` | **P21.4** (rest) | wire `web/` to read the export/API path instead of `*-fixture.ts`; the S8 xfail flips to a "rendered from export" assert |

**P19.4 spine work list (from CAPSTONE §i, confirmed by this run):** `P19.4:M` — `SIG-API-001`,
`SIG-API-002`, `SIG-INGEST-016`, `SIG-INGEST-017`, `SIG-PUB-007`, `SIG-TIME-008`, `SIG-UI-010`;
`P19.4:S` — `SIG-EPIS-018`, `SIG-RECON-039`, `SIG-RECON-040`. Of these the **spine critical path**
(the composed test blocks on) is the claim sink (S3) + the read store (S6); the rest are P19.5/P21.x.

## (f) Timings (this machine)

| step | wall time |
|---|---|
| S1 setup — container start + sqitch deploy | 7.07 s |
| S1 call — schema + append-only proof | 0.13 s |
| S2 OCFL capture (10 objects) | ~0.02 s |
| S3 connector run + replay (atlas+osm) | ~0.01 s |
| S4 Splink/DuckDB match + review round-trip | 0.52 s |
| S5 RESOLVE contradiction | ~0.01 s |
| S6 uvicorn spin-up + 8 HTTP hits | 0.30 s |
| S7 `sig-exports build` subprocess | 0.22 s |
| S8 `npm run build` (31 pages) | 1.05 s |
| **composed suite total** | **10.16 s** (`10 passed, 4 xfailed`) |
| isolation re-proof (`tests/e2e/test_isolation_reproof.py`) | 6 passed, <0.1 s |
| `make test-db` (local, LD-V11) | **114 passed in 12.40 s** |

The one-time cost is the PG container + sqitch deploy (~7 s); everything downstream is sub-second
except the Splink match and the static web build. CI (`ubuntu-latest`, Docker present) runs the same
suite for real via `SIG_REQUIRE_DB_TESTS`.
