<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# WAVE_A_RUNBOOK — P35.11 Wave-A activation (I8 ACQ-07; OM-19/OM-20)

*The scripted runbook for the first live ingestion wave. The machinery —
`ops/src/ops/wave_a.py` (`sig.wave-a-gate/1` + `sig.wave-a-plan/1`) and the
`ops/gcp/wave-a.sh` driver — is engineered and fixture-tested; **the three
legs stay queued** until the window opens under the recorded ING-GO-A.*

## Contract (ticket 271)

- **Window:** 2026-10-19 → 2026-10-23, 14:00–20:00Z each day (weekday), ≥ 48 h
  after P34.46's close. Production writes only inside it, under ING-GO-A
  (GATE-G4 §3, recorded 2026-10-09T17:32Z — "Window + flips at open").
- **One-shot authorisation:** a re-entry after a close re-collects ING-GO-A
  verbatim — it is never a standing go.
- **The wave-open HG-03 flip list (OP-26)** is the operator's signed commit or
  GATE DECISIONS row naming each source id to flip. Until it lands every row
  stays `ingestion_permitted=false` and activation skips unreviewed sources.
  This row flips nothing itself.
- **Legs (in order — a missed leg is reported, never silently skipped):**
  1. **L1** — image roll + `load-seed` + the three manual first runs
     (`legistar`, `usaspending`, `procportal_nyc_ny`), one at a time, each
     verified before the next.
  2. **L2** — `+0` re-runs of the same sources: `claims_added == 0`.
  3. **L3** — resume the paused `scheduled-ops.sh --paused` rows and
     `sig-sched-legistar`, each trigger only after its source ran green.

## Machinery

| artifact | role |
|---|---|
| `sig-ops wave-a-plan [--json]` | the deterministic `sig.wave-a-plan/1` step list — every step admission-gated, contingent steps marked |
| `sig-ops wave-a-gate --inputs <json>` | `sig.wave-a-gate/1` verdict over **recorded** inputs; exit `0` go / `42` no-go (queued, never silent) / `2` usage |
| `ops/gcp/wave-a.sh --check` | plan-only print; no ADC, no network, exit `0` |
| `ops/gcp/wave-a.sh --apply --leg <L1\|L2\|L3> --inputs <json>` | gates then executes the named leg; a failed verify aborts and is reported |

## Gate criteria (each refuse-on-fail)

`go` (verbatim ING-GO-A + `date -u` recorded_at) · `window` (supplied `now`
in-window, weekday, 14:00–20:00Z) · `leg` (`completed` = the ordered prefix
before the requested leg) · `scope` (`run_set` ⊆ declared set;
`doj_ctas_awards` never — AP-T2-093 stays `D-R11-LATER-09`) · `screened`
(ADR-185 lane ⇒ in `flip_list` + the no-human-review disclosure recorded) ·
`trigger` (L1: `sig-sched-legistar` paused, or `now ≥ 2026-10-20T05:00Z`) ·
`serialize` (no active `sig-materialize`, no manual run in flight) · `backup`
+ `prestate` (L1 only: AR-2 `SUCCESSFUL` + OM-14 pre-state capture with a
green `cadence --check`).

## Leg L1 — step order

1. **Pre-state (OM-14):** per-source job + trigger JSON
   (`gcloud run jobs describe sig-ingest-<id>`, `gcloud scheduler jobs
   describe sig-sched-<id>` for the wave set), `sources.toml` sha256,
   `uv run sig-ops cadence --check` green.
2. **AR-2:** `gcloud sql backups create --instance $SIG_SQL_INSTANCE` →
   record the newest backup `SUCCESSFUL`.
3. **Legistar mitigation:** `gcloud scheduler jobs pause sig-sched-legistar`
   before the roll — `0 5 20 * *` fires once in-window at 2026-10-20 05:00Z,
   outside the daily band but inside the window days; the alternative is a
   roll at/after that fire (the gate admits either, recorded).
4. **Roll:** `SIG_JOB_IMAGE=<ref> uv run sig-ops roll-jobs --record` — one
   pinned digest across the fleet (ADR-111).
5. **Seed:** `uv run sig-connectors load-seed --source
   state_alpr_statute_inventory_2026 --sink pg --dsn $SIG_PG_DSN` (the
   ticket's `sig-ops load-seed` resolves to the connectors CLI; the packaged
   2026 asset over the static transport — never a fetch).
6. **Manual first runs, one at a time, verified between:**
   `gcloud run jobs execute sig-ingest-<job-id> --args
   scheduled-ingest,--source,<id>,--sink,pg --wait` for `legistar` →
   `usaspending` → `procportal_nyc_ny`. After each: latest execution read +
   the `gs://…-sig-restricted/ops/runs/<source>/` run row — `ok`, captures
   landed bytes (not digest-only, J4 NEW-5), claims > 0, coverage-delta read.
   A failed verify stops the leg and is reported.
7. **Screened lane (ADR-185 S8), contingent on `flip_list`:** the same
   single-source execution for `camreg_tribal_all_leaders_directory` then
   `legis_tribal_tohono_oodham_notice`, each verified before the next — each
   run row discloses *no human review occurred*; facts/citations only.
   Un-flipped screened sources are reported skipped, never silently.

## Leg L2 — `+0` re-runs

Re-execute each source that ran in L1 in the same order; each run row must
read `claims_added == 0` on unchanged inputs. A non-zero read stops the wave
and is reported.

## Leg L3 — resume

`gcloud scheduler jobs resume` for each paused `--paused` trigger whose
source ran green, plus `sig-sched-legistar`. Triggers of un-flipped sources
stay paused — reported, never silently.

## Rollback (I8 §7.8)

- **Image:** re-point the previous digest from the roll record.
- **Job/trigger:** re-pause; delete only in a ticket-scoped live stage.
- **Source:** a new dated rights decision sets `ingestion_permitted=false` —
  the next run exits 3; claims stay (append-only); the next release withdraws.
- **Anomalous data:** forward-fix claims; corruption → PITR clone, never
  in-place restore.

## Deferred / excluded (recorded, not implicit)

- `doj_ctas_awards` (AP-T2-093) — not tribal; `D-R11-LATER-09` stays OPEN.
- `CG-LATER-tribal-data-governance-rule-i7-new-6` stays OPEN — the screened
  lane is the interim posture, not the governance rule; tribal governance is
  the individual HG-03 item.
- `D-R11-OSMUID-1` — handed to P37.1 (the OSM connector's next change).
- Outreach (ADR-171, `D-R11-LATER-04`) — SIG-CHART-033 / SIG-INGEST-029 /
  SIG-INGEST-030a / SIG-CONTRIB-012 / SIG-CONTRIB-012a / SIG-CONTRIB-013 /
  SIG-GOV-024 owed and unmet at launch; no outside contact is made.
- Public surfacing — downstream of the release carrying the claims (P36.72b);
  nothing public ships here.

## Re-run prompt

`implement-spec spec=docs/tickets/271_P35.11__wave-a-activation.md
live_verification=true` — each leg needs the recorded ING-GO-A, the window,
and its own gate inputs; the wave-open HG-03 flip list is the operator's
OP-26 action.
