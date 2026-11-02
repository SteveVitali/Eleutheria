# P36.33 — R2 basemap host create packet (`prepared_not_executed`)

`sig.basemap-host-packet/1` — see `packet.json` for the machine row.

## The named mutation

GATE-G5 §4 (2026-10-25T18:40Z, kind `pre-authorization`, expires GATE-G6)
names **P36.33** verbatim among the 13 pre-authorised 11C OM-20 rows — "the
R2 basemap host create (bucket/host provisioning after the DNS move, OP-09
posture)". Window `AR-3 + AR-2`.

## Why queued

`live_verification=false` dispatch + the hosted env is absent (no
`SIG_CF_ACCOUNT_ID`/`SIG_CF_API_TOKEN`/`SIG_R2_*`, no ADC) **and** OP-09 —
the operator's DNS-zone move to Cloudflare — has not landed. The create
therefore queues `prepared_not_executed` under OM-19: the machinery +
lock + packet land; no hosted write was attempted or fabricated.

## Re-run prompt (exact)

```
implement-spec spec=docs/tickets/374_P36.33__basemap-pipeline-and-host.md live_verification=true
```

resuming at `sig-ops basemap host --apply` then `sig-ops basemap refresh --apply`
(the pipeline, styles, glyphs and lock ship either way — `basemap.lock.json`
pins them).

## Preconditions the leg-runner checks

- OP-09 done: `surveillancegraph.org` NS on Cloudflare (operator act).
- `SIG_CF_ACCOUNT_ID`, `SIG_CF_API_TOKEN`, `SIG_R2_ACCESS_KEY_ID`,
  `SIG_R2_SECRET_ACCESS_KEY`, `SIG_BASEMAP_AUTHOR` exported (env only, HG-09).
- AR-3 windows: outside batch (day 6 00:00Z → day 13 12:00Z) and 03:00–06:30Z.

## The leg (verbatim plan — `sig-ops basemap host --check`)

1. R2 bucket create `sig-basemap` (cloudflare-r2).
2. CORS: `GET, HEAD` from the site origins, `Range` allowed, `Content-Range`/`ETag`/`Content-Length` exposed.
3. Custom domain `tiles.surveillancegraph.org`, public access on the domain only; bucket stays non-listable.
4. First upload = `sig-ops basemap refresh --apply` (fetch → b3sum-verify → versioned key `basemap/<build>.pmtiles`, `Cache-Control: public, max-age=31536000, immutable`).
5. Header verify on the created host: `curl -I` + a `Range:` GET answering 206 with `Content-Range`, CORS headers on an `Origin:` request, `immutable` cache-control.

## Restore point

The host is re-creatable from `ops/basemap.lock.json` + the upstream archive;
bucket versioning off (objects are immutable content-keyed). Kill switch:
lock `serving.active_source → context` + operator-side domain disable.

## Explicit non-goals

No DNS change, no HG-11 publication claim, no served-state assertion — the
host does not exist until this leg runs; every "map draws" claim waits.
