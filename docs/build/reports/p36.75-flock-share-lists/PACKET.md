# P36.75 — the append-only `configured_access` share-list write packet (`prepared_not_executed`)

`sig.flock-share-packet/1` — see `packet.json` for the machine row.

## The named mutation

GATE-G5 §4 (2026-10-25T18:40Z, kind `pre-authorization`, expires GATE-G6)
names **P36.75** verbatim among the 13 pre-authorised 11C OM-20 rows (the
mutation it names is quoted in `packet.json` `mutation`). Window
`AR-3 + AR-2`. The §43.2a screen lane was approved GATE-G5 §3 (A-7) — the
screen machinery proceeds under this row's own gates regardless.

## Why queued

`live_verification=false` dispatch + the hosted environment is absent —
no `SIG_GCP_PROJECT`, no ADC, no claim-spine writer DSN (the same posture
as P36.33's basemap host create). The leg queues `prepared_not_executed`
under OM-19: the screen + builder + write machinery + this packet land;
no hosted write was attempted or fabricated.

## Re-run prompt (exact)

```
implement-spec spec=docs/tickets/385_P36.75__flock-share-lists-configured-access.md live_verification=true
```

which resumes at the write — the screen + claim builder are re-runnable
and append-only.

## Preconditions the leg-runner checks

- `SIG_GCP_PROJECT` + ADC + `SIG_SHARE_WRITE_DSN` + `SIG_SHARE_LISTS_AUTHOR`
  exported (env only, HG-09); `cloud-sql-proxy` on PATH.
- `SIG_SHARE_SNAPSHOT` = the staged mirror snapshot whose multihash equals
  the stored `eyes_on_flock` `evidence_capture.content_digest` (the write
  binds that capture; a file that was never captured fails closed).
- AR-3 + AR-2: outside 03:00–06:30Z and the batch window (day 6 → day 13).

## The leg (verbatim plan — `ops/gcp/flock-share-lists.sh --check`)

1. `cloud-sql-proxy … sig-pg` on 127.0.0.1:5433.
2. `sig-connectors flock-share-lists --snapshot $SIG_SHARE_SNAPSHOT
   [--portal-extraction <page.json> …] --dsn-env SIG_SHARE_WRITE_DSN`
   — dry-run plan (units bindable, claims_pending, claim_set_digest).
3. The same + `--apply` — INSERT-only `configured_sharing_partner`
   claims via `PgClaimSink`, chunked, `is_replay` bound to the stored
   captures; +0-convergent.
4. Read-back: the dry re-run reports `edges_already_claimed =
   claims_total`.

## Restore point

Append-only is additive — the restore record is the written claim set's
digest list (`claim_set_digest` in plan + apply reports).

## Explicit non-goals

No person-level or audit-row claim (A-22 whole-fieldset screen), no
`ingestion_permitted` flip, no HG-nn tick, no GX-08b page build (P37.25's
row owns the overview — this row's feed shapes the claims it consumes).
