# First jurisdiction — Oklahoma City, end to end (P21.4)

SIG run as a **system**, not a test suite, for one real jurisdiction: the composed
stack (`sig-ops`) stood up, the OKC slice ingested/seeded, resolved, reconciled,
exported, and the static site built **from the export**, with the acceptance
queries run against the **running API**. Reproduce with `sh docs/build/tools/run_okc.sh`.

> **This run is NOT live.** P21.3 left **0 sources green** (HG-03 skipped), so there
> was **no live fetch**: every connector ran in `--mode shadow` over a committed
> fixture under network isolation, and the OKC claims were loaded from the committed
> P06.1 slice by `sig-ops seed`. The whole staging path still runs end to end — that
> is the real deliverable — but no result here is "live".

## 1. What was fetched (from the fetch records)

Nothing was fetched from the network. Connector runs, recorded in
`docs/build/okc/connector_runs_<date>.txt`:

| Source | Mode | Sink | State |
|---|---|---|---|
| `eff_atlas_of_surveillance` | shadow (fixture) | PG | shadow OK — recorded, not live |
| `osm_overpass` | shadow (fixture) | PG | shadow OK — recorded, not live (ODbL compartment) |

Every other permitted source is **HG-03-pending**: the acceptance report records, per
query, the exact `sig-connectors run --source <id> --mode live --sink pg` command to
run once a source is flipped green.

## 2. Claim / evidence / contradiction / task counts

Loaded by `sig-ops seed --jurisdiction okc` (append-only via `PgClaimSink`):

- **Claims:** 5 (`claimed_device_count` 299 + 190; `active_device_count` 90;
  `contracted_device_count` 90; `mapped_device_count` 31 — OSM/ODbL).
- **Evidence:** one L0 artifact/capture/extraction chain per source per run (append-only).
- **Contradictions:** 1 material — `claimed_device_count` **299 (DeFlock, 2026-08-20)
  vs 190 (Chief Bacy, 2026-08-18)**, resolver verdict `UNRESOLVED`/`CONTESTED`, both
  values retained (never collapsed — §3.1). Confirmed live on the API:
  `/v1/resolution/sig:deployment:okc-okcpd-flock/claimed_device_count`.
- **Tasks:** the unresolved contradiction surfaces a research task (compute-on-read,
  ADR-059; annotation persistence is P21.2-shrunk).
- **Entities:** the OKC deployment subject + two near-duplicate OKCPD organisations
  (the ER match candidates).

## 3. The J-1 output

J-1 (the journalist's traversal, §2.2) executed end to end against the composed
stack — 12 hops in order, ≥3 independent source families, and the contested-count
hop cross-checked on the running API:

```
city → police_agency → deployment → contract → contracted_cameras →
mapped_devices → sharing_relationships → network_searches → retention_settings →
policy → related_litigation → replacement_vendor
```

Source families crossed: executed contract / procurement record, community
field-mapping, investigative journalism, municipal governance record, agency policy.
`j1_status: pass` (see `docs/build/okc/acceptance_<date>.json`).

## 4. The acceptance-query table (against `SIG_STAGING_API_URL`)

From `docs/build/okc/acceptance_<date>.json`: **2 pass, 11 blocked, 0 failed;
fixture-subset all pass; J-1 pass.**

| Q | Question | State | Note |
|---|---|---|---|
| Q-2 | Which organization owns/operates it? | ✅ pass | OKCPD org projections searchable in the composed spine |
| Q-6 | How many devices? | ✅ pass | 299-vs-190 `claimed_device_count` — CONTESTED, both retained |
| Q-1, Q-3, Q-4, Q-5, Q-7, Q-8, Q-9, Q-10, Q-11, Q-12, Q-13 | (carriers) | ⛔ blocked | HG-03-pending — carrier not ingested; each records the exact `--mode live` command to run once a source is green |

Blocked queries are **recorded, not failures** (no green sources). The fixture-backed
subset (Q-2, Q-6) all pass; J-1 passes.

## 5. Lighthouse / axe results

- `npm run test:e2e` (Playwright chromium + no-JS, `@axe-core/playwright` WCAG 2.2 AA):
  **172 passed in fixtures mode AND 172 passed in export mode** — zero a11y violations,
  zero `<script>` on the shell pages (zero-JS budget held).
- `npm run check:perf` (lhci over the built site): **all Lighthouse budgets hold**
  (`web/lighthouserc.json`).

## 6. What remained fixture-backed and why (per-source gate state)

Everything is fixture-backed: **HG-03 was skipped in P21.3, so 0 sources are green
and no live fetch is permitted** (`sig-connectors run --mode live` refuses with exit
3 for a non-green source, ADR-065). The connectors therefore ran in `shadow` mode and
the OKC claims came from the committed slice via `sig-ops seed`. Per-source blockers
are recorded in the acceptance report as `HG-03-pending`, each with the command to run
once the source is flipped. The OSM-derived layer is included in the export in its
**separate ODbL compartment** (HG-02 disposition), not link-only.

## 7. Retrospective delta vs `P06.1_retrospective.md`

P06.1 proved the slice *could* be carried from evidence to a rendered dossier in the
library. P21.4's delta: the same slice now runs through the **composed system** —
persisted to PG (append-only), served by the read API, exported to licence
compartments, and rendered into the static site **from the export bytes**
(`SIG_DATA_SOURCE=export`, LD-V08 crossed). The 299-vs-190 contradiction, which P06.1
kept visible in-library, now survives the full ingest→resolve→export→build→serve path
and is asserted on the live page (`test_s8_web_build_renders_from_export_bytes`). No
new *live* data changed the picture (no green sources); what changed is that the
pipeline is now a service, not a test.

## 8. Go / no-go state per gate

| Gate | State | Note |
|---|---|---|
| HG-12 hosting/staging | ✅ satisfied (local) | `sig-ops up/status/down` healthy; local `docker compose` PG + uvicorn API + static server |
| HG-02 ODbL 4.4(b) | ✅ ticked | OSM layer included in exports as a Produced Work, separate ODbL compartment, attribution + share-alike |
| HG-01 legal home | ⏳ pending | not named (operator: SKIP) — public publish gated |
| HG-11 operating governance | ⏳ pending | two reviewer roles + live takedown contact not established (operator: SKIP) — public publish gated |
| Go public | ❌ NO | staging only; impossible until HG-01 + HG-11; deliverable 7 not done |

**Verdict:** staging **complete**; go-public **gated** (HG-01, HG-11, Go-public
pending). This ticket is complete-with-gates-skipped → **RETURN PASS**.

---

## 2026-09-10 re-run (LIVE.2 / GL-LIVE-02, prepare-only)

*(Lane-B re-run of the same P21.4 contract on branch `devin/p21-4-live2-rerun`,
base `devin/p21-3-live-wiring-rerun`; append-only. The environment clock read
2026-09-13, so the regenerated evidence files carry that stamp; the run is the
chain's LIVE.2 first-jurisdiction staging pass.)*

The full **LOCAL composed staging path was re-run for real** over Docker 29.1.3
(`sh docs/build/tools/run_okc.sh` end-to-end). Nothing about the gate posture
changed — this re-confirms the whole ingest→resolve→reconcile→export→build→serve
system runs as a service, and advances the reports to the **current** interim-gate
state (HG-01 interim / HG-11 owed / HG-02 interim-disposition / live-fetch pending /
Go-public reserved to the human). **No product code changed** in this re-run — it is
re-verification + dated documentation only.

**What ran (re-verified evidence):**

- **Composed pipeline (`run_okc.sh`, 8 steps):** `sig-ops up --seed` (5 OKC claims, 1
  entity) → shadow connectors `eff_atlas_of_surveillance` + `osm_overpass` (OK,
  recorded, **NOT live** — HG-03 subset now green but no live fetch: HG-09 tokens +
  network absent) → `sig-resolution match` (1 PROPOSED proposal enqueued) → `reconcile
  resolve` (**`claimed_device_count` UNRESOLVED / CONTESTED — 299 vs 190, both retained**)
  → annotations rebuild **skipped** (P21.2 shrunk → compute-on-read, ADR-059) →
  `sig-exports build` (13 artifacts, `licenses: ["CC-BY-4.0","ODbL-1.0"]`, separate ODbL
  compartment) → `SIG_DATA_SOURCE=export` web build (50 pages from export bytes) →
  acceptance J-1 + Q-1…Q-13 against the running API.
- **Acceptance (`docs/build/reports/okc/acceptance_2026-09-13.json`):** **2 pass, 11
  blocked, 0 failed; fixture-subset all pass; J-1 pass (12 hops, 5 source families).**
  Q-2 pass (owns/operates), Q-6 pass (**299-vs-190 CONTESTED/UNRESOLVED, both retained**);
  Q-1/3/4/5/7/8/9/10/11/12/13 blocked = `HG-03-pending` with the exact `--mode live`
  command each (recorded, not failures — no live fetch this run).
- **Contradiction survives to the page:** the export-built dossier HTML
  (`web/dist/dossier/oklahoma-city/index.html`) contains `299`, `190`, `contested`,
  `unresolved`; the `SIG-UI-014` reconciliation e2e (`dossier.spec.ts:71`) passes in
  **export mode**.
- **Deterministic ACs re-confirmed:** `sig-ops up/status/down` healthy → clean (no
  containers remain); `npm run test:e2e` **192 passed in fixtures mode AND 192 passed in
  export mode** (zero a11y violations, zero-JS held); `npm run check:perf` all Lighthouse
  budgets hold; `SIG_REQUIRE_DB_TESTS=1 make check` **2767 passed, 2 skipped, 0 failed**
  (the 2 skips are env-gated: the live-api test — run instead by `run_okc.sh` — and the
  GCP leak check, `SIG_GCP_PROJECT` unset, correct for prepare-only); `make docs-check`
  exit 0; `check-build-memory.sh .` no violations.

**Gate state (current, per LEDGER GATE DECISIONS + P23.2/P23.3/P23.4):**

| Gate | State (2026-09-10 re-run) | Note |
|---|---|---|
| HG-12 hosting/staging | ✅ satisfied (LOCAL) | composed staging re-run for real over Docker |
| HG-02 ODbL 4.4(b) | ✅ interim disposition (GL-GATE-02) | OSM in exports, separate ODbL compartment, attribution + share-alike; **pending counsel** (`D-LEGAL.1-1` OPEN) |
| HG-01 legal home | ⏳ INTERIM only (GL-GATE-01) | maintainer-stewardship interim posture, **not a real named home**; real home required before Go-public (`D-P21.4-1` OPEN) |
| HG-11 operating governance | ⏳ OWED | two reviewer roles + written concurrence + live takedown contact not established (`D-P21.4-2` OPEN) |
| Live fetch (HG-09 + network) | ⏳ pending | OKC subset is green (RIGHTS.1) but no tokens + no network egress → shadow/fixture only; no live green fabricated (`D-P21.3-2` OPEN) |
| Go public | ❌ reserved to the human (GL-GATE-05 / GATE-G2 / P23.6) | impossible until a **real** HG-01 + HG-11; deliverable 7 + `0.2.0` bump NOT done (`D-P21.4-3` OPEN) |

**Re-run verdict:** local staging **complete + re-verified**; go-public **genuinely
gated**. → **RETURN PASS** (P21.4 stays in RETURN PASS; next chain row is P23.6, the
Go-public GATE-G2 marker, handled by the orchestrator/operator).
