# LIVE_WIRING_REPORT — P21.3 (connector live wiring behind the gate)

**Status: complete, gate HG-03 pending (RETURN PASS).** This ticket wired the real
connector network path (`HttpxTransport`), the OCFL-backed capture store
(`OcflCaptureStore`), and the gated `sig-connectors run --mode live|replay|shadow`
CLI + fetch-record format (ADR-065). Per the operator's gate answers it performed
**no live fetch** and **flipped no source**: HG-03 = skip (no source is green) and
HG-09 = no tokens provided. Every deliverable is exercised over a **local HTTP
stub** (`httpx.MockTransport`, no network in tests) and fixture `shadow`/`replay`
(byte-identical, diff = 0). A live fetch is **structurally impossible** until a
source's `sig-connectors review-status` is fully green — `run --mode live` refuses
with **exit 3** and the gate reasons, before any transport is constructed or any
socket is opened (the LD-X08 guard).

## Per-source table

Modes actually run this ticket: **shadow** (fixture-backed connectors) and the
**live-refusal** assertion (every non-green source). Live URLs fetched = 0,
live captures = 0, live claims = 0 everywhere (HG-03 pending).

| source (registry id) | connector | mode run | gate state | live URLs | captures | claims | contradictions surfaced | blocker |
|---|---|---|---|---|---|---|---|---|
| `osm_overpass` (OSM/DeFlock via Overpass) | `osm` | shadow (fixture) + live-refused | REFUSED (exit 3) | 0 | 0 | 0 | 0 (shadow diff = 0; 19 claims unchanged) | **gate pending: HG-03** — `ingestion_permitted=false`; no review metadata. Rights **resolved** (ODbL-1.0), so this is the closest-to-green critical-path source. |
| `osm_element_history` (per-element history) | `osm` | live-refused | REFUSED (exit 3) | 0 | 0 | 0 | — | **gate pending: HG-03** — same as `osm_overpass`. |
| `eff_atlas_of_surveillance` (EFF Atlas) | `atlas` | shadow (fixture) + live-refused | REFUSED (exit 3) | 0 | 0 | 0 | 0 (shadow diff = 0) | **gate pending: HG-03** — not flipped. |
| `muckrock` (records/MuckRock) | `records` | live-refused | REFUSED (exit 3) | 0 | 0 | 0 | — | **gate pending: HG-03** + rights `UNDETERMINED` + **HG-09** (needs `SIG_MUCKROCK_TOKEN`, not provided). |
| `usaspending` (procurement sub-awards) | `procurement` | live-refused | REFUSED (exit 3) | 0 | 0 | 0 | — | **gate pending: HG-03** — the only prior live fetch (P07.3) bypassed the gate; now refused. Left `UNDETERMINED` deliberately (RISK-P21-02). |
| `okc_council` (agenda via CivicClerk `oklahomacityok`) | `procurement` | live-refused | REFUSED (exit 3) | 0 | 0 | 0 | — | **gate pending: HG-03** + tenant unverified (see `agenda_tenants.toml`; verification needs a live probe — HG-03/HG-09 `SIG_CIVICCLERK_BASE`). |
| `okc_procurement` (cited contract PDFs/HTML) | document connector | live-refused | REFUSED (exit 3) | 0 | 0 | 0 | — | **gate pending: HG-03** + rights `UNDETERMINED`. Document-connector fetch of `okc_sources.json` URLs is HG-03-gated. |
| `okcpd_policy` (Ops Manual §5-118) | document connector | live-refused | REFUSED (exit 3) | 0 | 0 | 0 | — | **gate pending: HG-03** + rights `UNDETERMINED`. |
| `ok_statute` (47 O.S. §7-606.1) | document connector | live-refused | REFUSED (exit 3) | 0 | 0 | 0 | — | **gate pending: HG-03** + rights `UNDETERMINED`. |

*Contradictions surfaced stay visible per the defining standard (§3.1): shadow
mode diffs the replayed claim set against the fixture-encoded one and reports the
delta; over the committed fixtures the delta is 0 (no synthetic certainty — a
genuine change would be seen).*

## Crawler-conduct evidence (rate-limit / robots)

No live request was made, so no fetch record was written this run
(`docs/build/live_runs/` is empty apart from its README). The conduct machinery is
proven over the stub instead:

- **Rate-limit / backoff (RISK-P21-04):** `HttpxTransport` backs off and retries on
  429/503/504 honouring `Retry-After` and records each event. Test evidence
  (`tests/connectors/test_httpx_transport.py`): a `429` with `Retry-After: 2`
  yields **exactly one** retry after **≥ 2 s**, emitting
  `{"status": 429, "action": "back_off", "wait_seconds": 2.0, "attempt": 1}`; a
  persistent 429 is returned after `max_retries` (never identity-rotated); an
  Overpass `504` is backed off and retried (SIG-INGEST-045h), not treated as a
  challenge; a `401/403` challenge is never retried (SIG-INGEST-013).
- **Robots (SIG-INGEST-012):** an unretrievable robots.txt returns `None` text and
  the fetcher fails closed; a robots-**disallowed** path is **never requested** —
  the transport's handler sees only `/robots.txt`, never the disallowed URL.
- **No circumvention (§26 Rule 4):** a configured circumvention technique is a hard
  error (`CircumventionError`); identity is never rotated, TLS never disabled.
- **Fetch-record format** (owned here): every live run will write
  `docs/build/live_runs/<date>_<source>.json` carrying URL list, status codes, byte
  counts, capture digests, claim count, duration, and the `rate_limit_events` +
  `robots_decisions` — and **no content** (`tests/connectors/test_runner.py`).

## Isolation on the composed stack (LD-X06)

With the real `HttpxTransport` constructed, the network-isolation guard still holds:
inside `network_isolated()` the transport cannot open a socket or resolve DNS —
both raise (`tests/connectors/test_isolation.py::test_httpx_transport_present_cannot_escape_isolation`).
The post-capture stages and replay run inside this context, so an accidental egress
fails the run (SIG-INGEST-002/018).

## Exact env + commands (to run each source once it is green)

Secrets are **environment-only** (HG-09); none are set this run, so live runs are
refused/skipped. When the operator flips a source to green (P21.1) and exports the
credential, the single command per source is:

```sh
# OSM / DeFlock via Overpass (ODbL compartment). No token; optional endpoint override:
export SIG_OVERPASS_ENDPOINT="https://overpass-api.de/api/interpreter"   # default public
sig-connectors run --source osm_overpass --mode live --sink pg --dsn "$SIG_DSN" --capture-dir .sig/captures

# MuckRock records (needs a short-lived JWT minted from the env token):
export SIG_MUCKROCK_TOKEN="…"        # never committed; .env* is gitignored
sig-connectors run --source muckrock --mode live --sink pg --dsn "$SIG_DSN"

# USAspending sub-awards through the gate:
sig-connectors run --source usaspending --mode live --sink pg --dsn "$SIG_DSN"

# OKC council agenda via CivicClerk tenant oklahomacityok:
export SIG_CIVICCLERK_BASE="https://oklahomacityok.api.civicclerk.com/v1/Events"   # default from agenda_tenants.toml
sig-connectors run --source okc_council --mode live --sink pg --dsn "$SIG_DSN"

# data.gov-keyed sources (when wired):
export SIG_DATA_GOV_KEY="…"

# Document connectors (fetch the cited PDFs/HTML, capture, parse, emit the fixture claims):
sig-connectors run --source okc_procurement --mode live --sink pg --dsn "$SIG_DSN" --wacz
sig-connectors run --source okcpd_policy    --mode live --sink pg --dsn "$SIG_DSN" --wacz
sig-connectors run --source ok_statute      --mode live --sink pg --dsn "$SIG_DSN" --wacz
```

Until then, exercise the same connectors over their committed fixtures — no
network, byte-identical:

```sh
sig-connectors run --source osm_overpass --mode shadow \
  --connector osm --fixture tests/connectors/fixtures/osm/overpass_snapshot.json \
  --media-type application/json --kind overpass          # -> shadow diff changed=0
sig-connectors run --source eff_atlas_of_surveillance --mode shadow \
  --connector atlas --fixture tests/connectors/fixtures/atlas/adoption_feed.csv \
  --media-type text/csv --kind bulk_csv                   # -> shadow diff changed=0
```

And confirm the gate refuses every non-green source:

```sh
sig-connectors run --source osm_overpass --mode live --sink memory ; echo "exit $?"   # -> exit 3
```

## Traceability

- **ADR-065** — transport choice, capture adapter, gate-refusal semantics, fetch-record format.
- **RISK-P21-04** (live fetch cadence vs source etiquette → `cadence`/backoff) and **RISK-P21-05** (token leakage → env-only + `.env*` gitignore + no-token-literal test) — `docs/risk_register.md`.
- Requirement ids stamped: SIG-INGEST-001/002/011/012/013/014/017/018/019/021/027/028/037, SIG-INGEST-045d/045h, SIG-EVID-004/005.
- Backlog: `docs/build/BACKLOG.csv` rows **BL-023** (transports + OCFL capture store — code delivered) and **BL-026** (WACZ seam + byte-identical reproducibility) landed here; **BL-024** (live token mint + real FETCH) stays open, gated on HG-03/HG-09.
