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

---

## 2026-09-10 — LIVE.1 fetch re-run (prepare-only; append-only, prior body unchanged)

**Status: gate HG-03 CLEARED for the OKC critical-path sources; live fetch still
pending HG-09 (tokens) + network egress.** This is the Lane-B re-run of the
already-landed P21.3 contract (manifest row 73, semantic LIVE.1 / GL-LIVE-01),
run per its verbatim `Run:` line
(`implement-spec spec=docs/tickets/P21.3__live-connector-wiring.md live_verification=true`).
The two upstream unblockers arrived since the original run: **RIGHTS.1 / P21.1**
flipped the OKC critical subset to `ingestion_permitted=true` (HG-03 satisfied,
GL-GATE-03) and **LIVE.1a / P23.5** added the three OKC document connectors
(`okc_procurement`, `okcpd_policy`, `ok_statute`) and wired them into the runner.
**HG-09 tokens are still `provided: no`** (P23.4 / ACCT.1) and this isolated
context has **no network egress**, so a REAL live fetch STILL cannot run. **No
live green is fabricated.** No product code changed this re-run — the wiring below
is verified, not modified.

### What flipped since the original run (per-source gate delta)

`uv run sig-connectors review-status --source <id>` — all five gate fields now
`True`, `loadable now: True`, for every OKC critical-path source (was
`REFUSED / gate pending: HG-03` in the prior body's per-source table):

| source (registry id) | connector (live path) | prior state | now | live fetch |
|---|---|---|---|---|
| `okc_procurement` | `okc_procurement` (P23.5 doc connector) | gate pending HG-03 | **GATE-CLEARED** (all 5 True, loadable) | pending HG-09 + network |
| `okcpd_policy` | `okcpd_policy` (P23.5 doc connector) | gate pending HG-03 | **GATE-CLEARED** | pending HG-09 + network |
| `ok_statute` | `ok_statute` (P23.5 doc connector) | gate pending HG-03 | **GATE-CLEARED** | pending HG-09 + network |
| `osm_overpass` | `osm` | gate pending HG-03 | **GATE-CLEARED** (ODbL-1.0) | pending HG-09 + network |
| `deflock_repo` | (registry source; MIT) | not flipped | **GATE-CLEARED** (MIT) | pending network |
| `okc_council` | `procurement` (CivicClerk tenant) | gate pending HG-03 | **GATE-CLEARED** (CC0-1.0) | pending HG-09 (`SIG_CIVICCLERK_BASE`) + network |

`run --mode live` **no longer refuses these on gate grounds** — the deterministic
gate check `live_gate_reasons(<id>)` returns `[]` (empty) for all six, i.e. the
review-status gate passes. The refusal now only fires for still-un-flipped sources
(verified below). The step past the gate — constructing `HttpxTransport` and
fetching — is not exercised this run (no tokens, no network; not run to avoid any
egress).

### Deterministic ACs re-confirmed (still hold; no network)

- **Gate refusal (un-flipped source):** `uv run sig-connectors run --source
  usaspending --mode live --sink memory` → **exit 3** with the gate reasons
  (`ingestion_permitted=false`, `rights block is UNDETERMINED`, `no recorded review
  metadata`) and **no socket opened** (the gate is checked in `_run_live` before any
  transport is constructed; `tests/connectors/test_runner.py` + `test_isolation.py`
  assert no egress). The refusal-path tests are pointed at `usaspending` (kept
  UNDETERMINED) precisely because the OKC sources are now green.
- **Shadow diff = 0 (every fixture-backed connector):**
  `run --source osm_overpass --mode shadow` = 19 claims, **diff changed=0**;
  `eff_atlas_of_surveillance` = 7 claims, **diff=0**;
  the three OKC document connectors over their committed fixtures
  (`tests/connectors/fixtures/okc/<id>.json`) each **diff=0**
  (`okc_procurement` 5 claims, `okcpd_policy` 2, `ok_statute` 2) — fetch → capture →
  parse (via `sig-parsing`) → emit is byte-identical over the fixtures
  (`tests/connectors/test_okc_documents.py`, 41 passed).
- **No token literal / secrets env-only:** `tests/connectors/test_secrets.py`
  green — no `SIG_*_TOKEN`/`api_key` string-literal in any `.py`/`.toml`
  (an env read is the sanctioned pattern); `.gitignore` contains `.env` + `.env.*`
  + `*.env`. (The bare AC grep `SIG_MUCKROCK_TOKEN=\|api_key=` matches only kwarg
  passing — `api_key=None`, `api_key=self.api_key` — and `.venv/` third-party code,
  none of which is a hardcoded secret; the test is the precise guard.)
- **Isolation with the real transport present:** the network-isolation guard still
  holds with `HttpxTransport` constructed (`test_isolation.py`).
- **P21.3 deterministic suite:** `uv run pytest tests/connectors -k "transport or
  capture_ocfl or runner or secrets or isolation or okc_documents"` = **75 passed,
  1 skipped** (the skip = the `SIG_GCP_PROJECT` leak check, unarmed — benign).

### Exact single command to run each live fetch once HG-09 tokens are exported

Secrets are environment-only (HG-09); export in the run shell, then one command per
source (nothing is fabricated — these run for real only with tokens + network):

```sh
# OKC document connectors (now GATE-CLEARED; fetch the cited public PDFs/HTML,
# capture to OCFL, parse via sig-parsing, emit the fixture-shaped claims):
sig-connectors run --source okc_procurement --mode live --sink pg --dsn "$SIG_DSN" --capture-dir .sig/captures --wacz
sig-connectors run --source okcpd_policy    --mode live --sink pg --dsn "$SIG_DSN" --capture-dir .sig/captures --wacz
sig-connectors run --source ok_statute      --mode live --sink pg --dsn "$SIG_DSN" --capture-dir .sig/captures --wacz

# OSM / DeFlock via Overpass (ODbL compartment; optional endpoint override):
export SIG_OVERPASS_ENDPOINT="https://overpass-api.de/api/interpreter"   # default public
sig-connectors run --source osm_overpass --mode live --sink pg --dsn "$SIG_DSN" --capture-dir .sig/captures

# OKC council agenda via CivicClerk tenant oklahomacityok:
export SIG_CIVICCLERK_BASE="https://oklahomacityok.api.civicclerk.com/v1/Events"   # default from agenda_tenants.toml
sig-connectors run --source okc_council --mode live --sink pg --dsn "$SIG_DSN" --capture-dir .sig/captures
```

Each writes a **fetch record** (no content) under `<capture-dir>/live_runs/<date>_<source>.json`
carrying the URL list, status codes, byte counts, capture digests, claim count,
duration, and the rate-limit/robots evidence; a second run inserts **0 new claims**
(idempotent on `content_digest`). Until tokens + network are present, the same
connectors are exercised over their committed fixtures (shadow/replay, diff = 0),
which is the standing proxy for the deferred live fetch.

### Honest gate status (no fabricated live green)

- **HG-03 (RIGHTS.1 flips):** CLEARED for the OKC critical subset (D-P21.1-1 DONE).
- **HG-09 (`SIG_*` API tokens):** `provided: no` (D-P21.3-2 / D-LIVE.1a-1 OPEN) —
  a real live fetch cannot run.
- **Network egress:** absent in this isolated context — even token-free public
  fetches (OSM/DeFlock) cannot run here.
- The deterministic gate/isolation/shadow ACs (transport, capture, runner,
  gate-refusal, shadow diff 0, no-token literal) are the honest evidence that the
  wiring is complete and correct; the live fetch is carried as a RETURN PASS /
  gate-pending obligation (`D-P21.3-1` PARTIAL, `D-P21.3-2` + `D-LIVE.1a-1` OPEN),
  **not** a block.
