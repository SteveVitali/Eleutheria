# ADR-065: Live connector wiring — the httpx transport, OCFL capture store, and the gated `run` CLI

- **Status:** Accepted
- **Date:** 2026-09-10
- **Phase:** P21.3
- **Requirement ids:** SIG-INGEST-001, SIG-INGEST-002, SIG-INGEST-011, SIG-INGEST-012, SIG-INGEST-013, SIG-INGEST-014, SIG-INGEST-017, SIG-INGEST-018, SIG-INGEST-019, SIG-INGEST-021, SIG-INGEST-027, SIG-INGEST-028, SIG-INGEST-037, SIG-INGEST-045d, SIG-INGEST-045h, SIG-EVID-004, SIG-EVID-005

## Context

Through the end of the 46-ticket build and the P19–P21.2 capstone work, **no
connector had ever executed a real FETCH** (LD-V03): every source adapter was
driven over committed fixtures, and the shared politeness layer
(`connectors.net.PoliteFetcher`) drove an *injected* `Transport` that the tests
and the P19.4 runner filled with a static, socket-free stub. Two seams were
explicitly deferred to "the live-wiring ticket" that did not yet exist (LD-F03):
a real HTTP transport, and an OCFL-backed `CaptureStore` adapter. The one prior
live fetch (P07.3 USAspending) **bypassed the gate** (LD-X08) — a structural hole
this ticket had to close.

Two human gates bound the work. **HG-03**: a real fetch runs only for a source
whose `sig-connectors review-status` is fully green (flipped by the operator in
P21.1 with recorded review metadata). **HG-09**: tokens/keys are environment-only,
never in files. For this run the operator answered **HG-03 = skip** (no source
flipped) and **HG-09 = no tokens provided**. So the deliverables had to land and
be provable **without any live fetch** — over a local HTTP stub and fixture
replay — while making a real fetch *structurally impossible* until a source is
green.

## Decision

1. **`HttpxTransport` (`connectors/transports/httpx_transport.py`) is the real
   network path**, implementing the existing `connectors.net.Transport` Protocol
   over `httpx` (promoted from a dev dependency to a `connectors` runtime
   dependency via `uv add`). The politeness layer is unchanged (additive /
   back-compat, SIG-INGEST-011); the transport adds only the transport-level
   duties the fetcher cannot own:
   - **retry-with-backoff on 429/503/504 honouring `Retry-After`** (§26 Rule 3,
     SIG-INGEST-037) — a transient rate-limit or gateway-timeout is *backed off and
     retried*, **not** treated as a bot-management challenge; this is the Overpass
     etiquette (429 = slot exhaustion → back off; 504 = query too large — we still
     back off before giving up, SIG-INGEST-045h / LD-F03). A 401/403 challenge is
     **never** retried and is surfaced by the fetcher (SIG-INGEST-013);
   - **conditional GET / ETag** (SIG-INGEST-017): the last validators are replayed
     as `If-None-Match` / `If-Modified-Since`, and a 304 serves the previously
     captured bytes back rather than re-downloading;
   - **no circumvention** (§26 Rule 4, SIG-INGEST-037): identity is never rotated,
     TLS verification is never disabled, and a configured circumvention technique
     is a hard error (`policy.crawler.assert_no_circumvention`).
   Tests run the transport against an in-process `httpx.MockTransport`, so **no
   socket is ever opened** in the suite.

2. **`OcflCaptureStore` (`connectors/capture_ocfl.py`) adapts the evidence OCFL
   root to the connectors' `CaptureStore` Protocol** (SIG-EVID-004/005, §17.3).
   One OCFL object per content multihash (content-addressed, so identical bytes
   deduplicate to one blob and a re-run adds a version, never overwrites —
   append-only P1–P3); the raw bytes are the `capture` logical file and a
   `metadata.json` sidecar records the **retrieval time, source URI, media type,
   and response headers** (retrieval provenance, never content). An optional WACZ
   logical file is written for HTML pages through the P02.2 Playwright path when a
   `wacz_builder` is supplied (`--wacz`, LD-F02/LD-H02). The returned `CaptureRef`
   carries the **connectors' multihash**, identical to `InMemoryCaptureStore`, so
   post-capture stages and fixture replay are byte-identical whichever store backs
   the run.

3. **The `sig-connectors run --source ID --mode live|replay|shadow` CLI owns the
   run surface and the fetch-record format** (this ticket owns both; P21.4 invokes
   `run`). `live` mode **refuses (exit 3, with the gate reasons)** unless the
   source's review-status is *fully green* — `ingestion_permitted` true, an
   ingestion-permitting `compact_status`, a content-fetching `custody_posture`, a
   resolved rights block, and recorded review metadata. This is the **LD-X08
   guard**: a live fetch is impossible without a green review-status, checked
   *before any transport is constructed or any socket is opened*. `replay` /
   `shadow` run over a committed fixture under network isolation and never fetch;
   a live run writes an immutable, dated **fetch record**
   (`docs/build/live_runs/<date>_<source>.json`: URL list, status codes, byte
   counts, capture digests, claim count, duration, and the crawler-conduct
   evidence — rate-limit events + robots decisions) that carries **no content**.

## Consequences

- **This run performs no live fetch and flips no source** (HG-03 skip). Every
  deliverable lands and is verified over the stub + fixtures: the transport
  (MockTransport), the capture store (local OCFL root), the runner (gate refusal,
  shadow diff = 0, reproducible replay), and isolation with `HttpxTransport`
  present. Each critical-path source is reported **complete, gate HG-03 pending**
  in `docs/build/LIVE_WIRING_REPORT.md` with the exact command that would run it
  once green — a RETURN PASS entry, not a block.
- **The prior gate hole is closed.** After this ticket a live fetch cannot happen
  for a non-green source: `run --mode live` refuses before egress (LD-X08 can
  never recur). The P07.3 USAspending bypass is structurally prevented.
- **Secrets stay env-only** (HG-09): `SIG_MUCKROCK_TOKEN`, `SIG_DATA_GOV_KEY`,
  `SIG_OVERPASS_ENDPOINT`, `SIG_CIVICCLERK_BASE` are read from the environment;
  with none set, live runs are skipped/refused. A test (`RISK-P21-05`) fails the
  build if any `SIG_*_TOKEN`/`api_key` literal appears in a `.py`/`.toml` file, and
  `.env*` is gitignored.
- **The `Transport` / `CaptureStore` Protocols are unchanged and `InMemory*`
  remain the defaults** — the wiring is additive, so the whole existing suite and
  the composed-stack replay are untouched (fixture replay stays byte-identical).

## Revisit trigger

Revisit when the operator answers **HG-03** (flips a source to a fully-green
`review-status`) and/or **HG-09** (provides a token): the first real fetch then runs
— `run --mode live` stops refusing for that source, a dated fetch record lands in
`docs/build/live_runs/`, and `LIVE_WIRING_REPORT.md` records live URLs/captures/claims
> 0 with a second-run-inserts-0 idempotency check (BL-024). Also revisit if the WACZ
capture path is promoted from the optional `wacz_builder` seam to a default for HTML
sources (BL-026), or if the retryable-status set / backoff policy needs to change for
a specific source's published etiquette (RISK-P21-04).
