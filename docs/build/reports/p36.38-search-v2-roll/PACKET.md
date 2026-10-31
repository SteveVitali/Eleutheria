# P36.38 — the v2 search API roll packet (`prepared_not_executed`)

`sig.search-v2-roll-packet/1` — see `packet.json` for the machine row.

## The named mutation

The plan cell (row 379, verbatim): **"IN-TICKET PAUSE (never pre-authorised
under OM-20: API roll that changes a public route's response); explicit
verbatim go · D-K3-5 [B-30] = yes: sig-api 512 MiB -> 1 GiB (+$3/mo) and the
v2 API rolls (U-003.3) · API roll ="**. The roll is never pre-authorised —
it runs only on the operator's explicit verbatim go, inside `AR-3 + AR-2`.

One bounded `gcloud run services update` on `sig-api`:

```
gcloud run services update sig-api \
  --memory 1Gi \
  --update-env-vars SIG_API_SEARCH_V2=on
```

- `--memory 1Gi` — D-K3-5 [B-30] = yes: 512 MiB → 1 GiB (≈ +$3/mo, recorded
  K3 §5.7) so the verified local copies of `sig.release-search-index/2`
  fit (K3 §5.5: Cloud Run local disk is memory; ≈ 200 MB for two releases).
- `SIG_API_SEARCH_V2=on` — mounts `GET /v1/releases/{pub|latest}/search`
  (`api/release_search_v2.py`). Default `off` mounts nothing: an image
  without the code is inert under the env either way, so the flip is
  rollback-safe in both directions. `ops/gcp/config.sh` `SIG_API_MEMORY`
  and `ops/gcp/provision.sh --memory` already declare 1 GiB for fresh
  provisions (engineering, not the roll).

## Why queued

`live_verification=false` dispatch + the roll is **never pre-authorised**
(OM-20): no operator verbatim go exists and the hosted env is absent (no
ADC, `SIG_GCP_PROJECT` unset). The serving code, store, LRU, roll runner
and this packet land; the roll itself is recorded `prepared_not_executed`
and filed `D-P36.38-1` — never run, never fabricated.

## Re-run prompt (exact)

```
implement-spec spec=docs/tickets/379_P36.38__search-api-serving-v2.md live_verification=true
```

resuming at `ops/gcp/search-v2-roll.sh --apply` (the serving code ships
dark either way; the script is idempotent).

## Preconditions the leg-runner checks

- The operator's verbatim go recorded — `SIG_SEARCHV2_AUTHOR` exported
  (env only, HG-09); silence is never consent.
- ADC + `SIG_GCP_PROJECT` present (lib.sh `require_adc`/`require_project`).
- The serving image carries the v2 serving code (the verify leg's route
  probe fails loud on a 404-unmounted route — never claimed).
- Window `AR-3 + AR-2`: outside the 03:00–06:30Z daily freeze and every
  declared AR-3 batch window (the script's guard refuses exit 42 inside).

## The legs (verbatim plan — `--check`)

1. `prestate` — `gcloud run services describe sig-api --format json` → the
   recorded restore point (env, memory, `latestReadyRevisionName`).
2. `roll` — `services update --memory 1Gi --update-env-vars
   SIG_API_SEARCH_V2=on` (one bounded revision).
3. `verify` — describe reads back `on` + `1Gi`, names the serving revision,
   and probes `GET /v1/releases/latest/search?q=probe` for a mounted
   answer (200/410/422/503 — a 404 means not mounted and fails loud).

## Restore point / rollback

The prior deployment revision's env + memory (prestate describe). Rollback:
`gcloud run services update sig-api --memory <prior>
--remove-env-vars SIG_API_SEARCH_V2` — or the prestate spec verbatim. The
v1 route is untouched; with the env removed the v2 route unmounts and the
public response is byte-identical to pre-roll.
