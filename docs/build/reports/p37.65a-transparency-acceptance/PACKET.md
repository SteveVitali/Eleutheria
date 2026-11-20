# P37.65a — Transparency acceptance packet (J3 TX-16, R11-K13-TX-16)

The acceptance packet the P37.65b Class S HG-11 readout folds in (the plan
cell: `none (cut + checks; the HG-11 pause is P37.65b)`). Every row names
the BM-STATUS-01 layer the evidence reached — engineered /
fixture-verified results only; nothing here claims a staging, live or
public verdict (SIG-ENG-042).

## Leg ledger (sig.transparency-acceptance/1)

| leg | stage | verdict | layer |
|---|---|---|---|
| `scrub-audit` | deterministic | ran in this dispatch — **273 published-transparency files scanned, 0 secret-shaped hits** (`policy.transparency.find_secrets` over the fresh emitted dist); `sig.scrub-audit/1` record at `scrub-audit.json` beside this packet | fixture-verified |
| `journeys` | deterministic | **4/4 pass (chromium)** — the J1/J4 deterministic legs in `web/tests/e2e/transparency-acceptance.spec.ts` (agent walkthrough, never user research) | fixture-verified |
| `budgets` | deterministic | **523/523 budgets green** — `national_budget_leg.sh budgets` wire-measured over the real-sized national build (the recorded `measured_gaps` rows held inside their regression bounds) | fixture-verified |
| `release-cut` | production-mutation | **prepared_not_executed** — queues exit 42 | deferred (`D-P37.65a-1`) |
| `live-crawl` | live | **prepared_not_executed** — queues exit 42 | deferred (`D-P37.65a-1`) |

## The cut that did not run — recorded, never fabricated

The ticket's named production mutation is the final release cut (a release
build under the plan's window text: `final release cut never inside AR-3
windows (12-06 -> 12-13T12:00Z)` — verbatim). This dispatch could not run it
honestly:

- **The hosted release registry does not exist.** `gsutil ls
  gs://eleutheria-sig-release/registry/` → `404 BucketNotFoundException`
  (2026-11-18) — `D-P35.53-1` (the release-infra apply leg: bucket +
  IAM-only staging services + the `sig-release` job) is OPEN, owner: the
  operator (OP-24), trigger: a valid AR-3 + AR-2 window.
- **No SIG-project ADC / `SIG_GCP_PROJECT` in this environment** — the
  active `gcloud` account cannot see the deployment project (the same
  recorded absence `D-P37.42-1`/`D-P36.44-1` carry).
- **The promote is P37.65b's in-ticket pause**, never this row's leg —
  the HG-11 final Class S readout and the promote run only on the
  operator's verbatim go.

The leg is deferred as `D-P37.65a-1` (kind V) with the OM-19 re-run
prompt; `sig-ops transparency-acceptance run --leg release-cut|live-crawl`
queues exit 42 today and executes on the re-run once the hosted registry
and ADC exist inside a valid window.

## What the deterministic half proves

- **Scrub audit** — every file under the declared published-transparency
  families (`transparency/`, `status/`, `sources/`, `data/`, `raw/` +
  `artifact/` mirrors, `evidence/`, `changes/`, the `r/`/`v/`/`s/`
  `releases/` namespaces where present, `statements/`) passes the one
  shared detector; a hit or a vacuous scan fails. The release-scale side
  is V12 inside `release verify --mode S` — the same detector, the whole
  publish set — on the `live-crawl` leg.
- **J1** — figure → recomputing bytes (≤ 2 actions), the as-of stamp +
  "not a census" framing, pointer/breakdown contract non-vacuous.
- **J4 (deterministic half)** — every cite-carrying emitted route shows
  exactly one cite mode and the pinned-selector permalink
  (`as_of_world` + `as_of_belief` + `ruleset`) resolves; the
  "reproducible after SIG corrects itself" promise appears only beside an
  immutable `/s/<pub>/` or `/r/<pub>/` cite URL. The durable-pin half
  (identical bytes after the next release) is a property of the staged
  candidate — `live-crawl` scope.
- **Budgets** — page-type budgets all types, wire-measured over the
  national build (`budget.spec.ts`, `sig.page-budgets/1`).

## Acceptance shape (catalog)

`capstone journeys J1, J4 pass (K13 §8)` — J1 and J4's deterministic
halves green at fixture layer; J4's durable-pin half is recorded as
release scope, never claimed. `page-type budget all types` — cited at
the national measure.

## Live dispatch — 2026-11-20 (`D-P37.65a-1` attempt; run ledger `runs/P37.65a-live-1.md`)

Under GATE-ACCEPT-R11 `2026-11-20T00:15Z` ("Authorize now" — release-cut +
live-crawl ONLY; promote still paused pending the operator-signed
`sig.promotion-approval/1`), the authorized legs ran against the real
registry `gs://zeta-medley-508121-u7-sig-release` inside a clean AR-3
window (cut at 06:30:28Z, host-clock skew 0.678 s):

- **`release-cut` — partially executed.** Journal rows:
  `events/000002-…-cut-root.json` (t0 06:30:28Z),
  `events/000003-…-built-p-846b3554.json`,
  `events/000004-…-sites-p-846b3554.json` (`trees:{}`). Candidate:
  `p-846b3554843914820c2e18658fad58204d5089992ad623adcee81cc2d3d3c33d`,
  label `sig-2026-09-27.1`, `environment=production`, integrity manifest
  `complete` over 475,040 artifacts. `stage` was started per the declared
  chain, measured ~0.37 objects/s (475,040-object plan ⇒ ~14.7 days
  serial), and halted — **no `staged` event exists**; `registry/LOCK`
  remains held by the interrupted attempt (`--break-lock <reason>` is the
  designed recovery); 262 staged objects landed (resume-safe).
- **`live-crawl` — not run.** No staged candidate exists to verify; the
  journal, candidate, and registry state above are the leg's honest
  boundary.
- **Blocking finding:** the newest authorized export
  (`…/exports/national/2026-09-27T005153Z/`) predates the `web/*`
  artifact set — `SIG_DATA_SOURCE=export` fails closed on missing
  `web/evaluation.json`, so no latest/snapshot dists exist and `sites`
  journaled `trees:{}`. Without `v/<pub>/`/`s/<pub>/`, V3/V5 cannot go
  green; V14 has no baseline; no `sig.quality-report/1` exists so V15
  skips. A skip blocks (SIG-ENG-042) — `D-P37.65a-1` stays **OPEN**.
  Refusals recorded verbatim in `docs/build/logs/p37.65a-live-1/`:
  AR-3 daily-window cut refusal (04:15:45Z), dist build failure
  (04:15:52Z), label/snapshot-mismatch build refusal (06:30:59Z),
  lock-held refusal + recorded break (06:34:45Z), premature no-release
  verify refusal (04:52:12Z), stage halt (06:58:43Z).
- **Promotion remained paused throughout** — `registry/catalog.json`
  still `{"publications":[]}`, no `latest.json`, no approval record.
