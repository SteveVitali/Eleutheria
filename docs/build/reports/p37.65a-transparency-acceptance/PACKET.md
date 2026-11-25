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
| `release-cut` | production-mutation | **executed, machinery-bound stop** (re-cut leg, 2026-11-25, operator go `99018e1b`): `cut` + `built` journaled — `registry/events/000006-…-cut-root.json` (16:38:24Z) + `000007-…-built-p-31371dfb.json` (17:52:32Z) for `p-31371dfb4b2b26453f818fefd311ea07be50ef8413aa9185be1ede927a773a8b` / `sig-2026-11-25.1` over the real national export (`export_manifest_sha256` `39e6549b…8153c` matches `manifest.json` verbatim; integrity manifest 462,494 artifacts re-verified `complete`); `sites` never invoked — both export-mode Astro dists hit the verified `ERR_STRING_TOO_LONG` bound (`osm_physical/statements.jsonl` 1,013,125,905 B > V8's `0x1fffffe8` cap, `web/src/lib/data.ts:2029`, reproduced via `vitest` under pinned node v24.21.0) plus the non-memoized per-page full-corpus re-parse; `stage --apply` measured **~0.014 obj/s** (~7 serial GCS calls/object each paying a 5–6 s `gcloud` ADC token subprocess) then **died** at 8/462,497 objects on the token-timeout path (`GcsError: no GCS access token available`, verbatim in `docs/build/logs/p37.65a-live-1/11-stage.txt`) — `staged` never emitted; lock left held `{verb:stage, 19:41:59Z}` + 8 residue objects, append-only forensic state | deferred (`D-P37.65a-1`; new bounds `D-P37.65a-2` / `D-P37.65a-3`) |
| `live-crawl` | live | **never reached** — no `staged` candidate exists; even a completed stage hits V14 (no prior `latest.json`) + V15 (no `sig.quality-report/1`) as blocking skips per SIG-ENG-042 | deferred (`D-P37.65a-1`) |

## The cut — deferred once, then executed to the machinery's bounds

**Re-cut leg (2026-11-25, this leg):** once `D-P35.53-1` landed (the real
registry `gs://zeta-medley-508121-u7-sig-release` + the IAM-only staging
origins exist) and project ADC/`SIG_GCP_PROJECT` were present inside a
valid window, the leg ran end-to-end at the machinery's own boundaries —
see the `release-cut`/`live-crawl` rows above and the run ledger
`docs/build/runs/P37.65a-live-1.md`. The cut + build journaled green; the
web dist builds, `sites`, `staged` and `verify` hit verified bounds,
recorded verbatim — never fabricated.

**Original dispatch (2026-11-18, history):** the ticket's named production
mutation is the final release cut (a release
build under the plan's window text: `final release cut never inside AR-3
windows (12-06 -> 12-13T12:00Z)` — verbatim). That dispatch could not run it
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
