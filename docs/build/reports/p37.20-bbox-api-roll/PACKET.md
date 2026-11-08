<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P37.20 — the bbox-API roll packet (`prepared_not_executed`)

`sig.bbox-api-roll-packet/1` — see `packet.json` for the machine row.

## The named mutation

The plan cell (row 444, verbatim): **"IN-TICKET PAUSE (never pre-authorised
under OM-20: API roll that changes a public route's response); explicit
verbatim go"**. The roll is never pre-authorised — it runs only on the
operator's explicit verbatim go, inside `AR-3 + AR-2`.

One bounded `gcloud run services update` on `sig-api`:

```
gcloud run services update sig-api \
  --memory 1Gi \
  --update-env-vars SIG_API_BBOX=on
```

- `--memory 1Gi` — D-K3-5 [B-30] = yes ("sig-api 512 MiB -> 1 GiB (+$3/mo)
  and the v2 API rolls (U-003.3)"): the decision covers the v2-artifact
  API rolls plural, so the verified local copies of the
  `sig.release-search-index/2` artifacts fit (K3 §5.5: Cloud Run local
  disk is memory). Idempotent when the P36.38 roll (D-P36.38-1) already
  landed the bump.
- `SIG_API_BBOX=on` — mounts
  `GET /v1/releases/{pub|latest}/sites` and
  `GET /v1/releases/{pub|latest}/compartments/{comp}/sites`
  (`api/release_bbox.py` — the K1 MAP-06 routes). Default `off` mounts
  nothing: an image without the code is inert under the env either way,
  so the flip is rollback-safe in both directions. The bbox list reads
  the same verified per-compartment index copies the v2 search reads —
  no new artifact class, no new memory class beyond D-K3-5's bound.

## Why queued

`live_verification=false` dispatch + the roll is **never pre-authorised**
(OM-20): no operator verbatim go exists and the deployment env is absent
(no ADC, `SIG_GCP_PROJECT` unset). The serving code, store, roll runner
and this packet land; the roll itself is recorded `prepared_not_executed`
and filed `D-P37.20-1` — never run, never fabricated.

## Re-run prompt (exact)

```
implement-spec spec=docs/tickets/444_P37.20__release-pinned-bbox-api.md live_verification=true
```

resuming at `ops/gcp/bbox-api-roll.sh --apply` (the routes ship dark
either way; the script is idempotent).

## Preconditions the leg-runner checks

- The operator's verbatim go recorded — `SIG_BBOX_AUTHOR` exported
  (env only, HG-09); silence is never consent.
- ADC + `SIG_GCP_PROJECT` present (lib.sh `require_adc`/`require_project`).
- The serving image carries the P37.20 serving code (the verify leg's
  route probe fails loud on a 404-unmounted route — never claimed).
- A promoted release whose `search_index_v2.sqlite` carries the
  `site_points` R*Tree (a pre-P37.20 build answers the typed absence
  `spatial_index_not_published`, honestly — the roll does not mint one).
- Window `AR-3 + AR-2`: outside the 03:00–06:30Z daily freeze and every
  declared AR-3 batch window (the script's guard refuses exit 42 inside).
