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
