# ADR-237 — Keyed US 511 lanes: a wire-only query-param credential seam and declared-contract, fail-closed parse (P37.12)

- Date: 2026-11-07
- Status: accepted
- Ticket: P37.12 (Round 11 / P37, row 433 — the named home of D-SOURCES.7-2's
  engineering half; GATE-G6 §4 pre-authorisation, expires GATE-ACCEPT-R11)
- Base: `r11/P37.11-sam-gov-sweep-resume`
- Related: ADR-083 (the API allowlist these keyed hosts join), ADR-088
  (GL-GATE-08 — robots probed and recorded, never enforced), HG-09 (secrets
  are environment/Secret Manager only), D-SOURCES.7-2, OP-13,
  `connectors/net.py`, `connectors/dot_511.py`, `connectors/stages.py`,
  `connectors/pipeline.py`, `connectors/data/dot_511_targets.toml`,
  `ops/cadence.toml`.

## Context

Ten US state 511 camera APIs (FL, NY, AZ, NV, OH, PA, WI, AK, CT, and the
ME/NH/VT New England coalition feed) are enumerated in
`dot_511_targets.toml` as `keyed_api`/`access_restricted` — the 2026-09-17
probe answered HTTP 400 `Invalid Key` on nine Iteris/IBI-511 hosts and HTTP
401 `API key required` on OHGO. D-SOURCES.7-2 owes their graduation to live
targets **once the operator registers the keys** (OP-13/HG-09): the wiring
must be committed beforehand, the credential must never be committed, and the
named mutation (the keyed live run) stays gate-pending until the key exists
and the rights flip lands.

Two platform facts shape the design. First, the Iteris/IBI-511 family's
documented credential form is a **query parameter** (`?key=…`) — no header
form is published. A query-param credential lands in the URL string, and the
URL is the most-recorded surface in the run (per-fetch telemetry, robots
verdicts, conduct decisions, the capture's `source_uri`, claim evidence). The
existing `headers=` seam (SAM.gov's `X-Api-Key`, MuckRock's Bearer) cannot
carry it. Second, **no keyed payload has ever been observed** — every probe
answered the key wall, so the response contract must be declared from the
platforms' published documentation and enforced strictly at parse, never
assumed.

## Decision

1. **`auth_param` is a wire-only credential seam.** `PoliteFetcher.fetch`
   accepts `auth_param: tuple[str, str]` and appends it to the *wire* URL
   only. Every recorded surface — the opt-out/refusal/reservation records,
   `conduct_decisions`, `robots_outcomes`, `per_fetch`, and the returned
   `FetchResult.url` that becomes the capture `source_uri` — keeps the
   credential-free URL. The discipline is the same as the `X-Api-Key` header
   pattern (P26.4): a secret exists between process env and the transport
   call, and nowhere else. Where a platform publishes both a header and a
   query form (OHGO's `Authorization: APIKEY` vs `?api-key=`), the header is
   used — no credential lands in any URL at all.
2. **`api_key_env` declares a NAME, never a value.** Each graduated
   `[[targets]]` row carries `api_key_env = "SIG_US511_*_KEY"` — the
   environment variable the operator's Secret-Manager secret binds to
   (declared per cadence seat). `assert_target_keyed_spec` refuses anything
   that is not a `SIG_*` env name — a key literal in the registry is a
   registry defect (`KeyedSpecNotDeclared`), and a non-keyed kind carrying
   the field is likewise refused.
3. **An unprovisioned key is a recorded refusal, not a disappearance.**
   `KeyNotProvisioned` is raised before any egress — before even the robots
   probe — and the pipeline records it on `report.refusals` per-target
   (completion `partial`), alongside the rights refusals. A keyed source
   whose keys are absent therefore records an honest partial run rather than
   a crash, a fabricated fetch, or a fake "the host went away" disappearance.
4. **The payload contracts are declared, strict, and fail closed.** Two new
   kinds: `iteris_511_rows` (a top-level JSON camera array; any object
   envelope — `{"Message": "Invalid Key"}` — non-JSON shell, or non-object
   row is `ContentDrift`) and `ohgo_511_cameras` (the ApiResult envelope
   `{Results: [...], TotalResultCount, CurrentResultCount}`; a truncated
   page — `CurrentResultCount < TotalResultCount` — is `ContentDrift`, so a
   partial inventory is never emitted as complete). A keyed run that meets a
   different shape — e.g. the recorded, unverified Castle Rock "511x"
   platform migrations reported for some Iteris states — stops and records
   drift rather than silently emitting.
5. **Feed-content containers are excluded by name.** The vocab's media-field
   blocklist gains `Views`, `CameraViews`, `Links`, `Href` (and the
   `DirectionOfTravel` direction alias): the per-view image/stream URLs and
   per-row link objects are recorded-excluded — their names land on
   `excluded_fields`, their values never reach a claim (Part VIII).
6. **Every lane stays gated and paused.** The ten new `dot_511_*` source
   rows are `ingestion_permitted=false` (rights UNDETERMINED; the licence
   lead `LicenseRef-PublicRecord-FactualCompilation` is seed evidence only);
   the ten `ops/cadence.toml` seats are `state = "paused"` carrying the
   `SIG_US511_*_KEY` → `sig-us511-*-key` Secret-Manager binding map — the
   wiring the operator's OP-13 registration fills. The operator's HG-03
   rights flip plus the key is the only route to a live fetch; the keyed
   live legs are deferred under `D-P37.12-1`.

## Consequences

- A query-param credential can now ride the shared politeness layer without
  a bespoke HTTP client and without ever landing in a record. The seam is
  generic — any future keyed query-param source uses the same contract.
- The registry refuses credential literals by construction: a `SIG_*` env
  name is the only permissible `api_key_env` value, and
  `sig-connectors validate` enforces it.
- The declared-contract parse trades flexibility for honesty: an unobserved
  payload that deviates is drift data to research, never a best-effort emit.
- A keyed target never shares a source with an unkeyed one (nvroads_api gets
  its own `dot_511_nvroads` seat, distinct from `dot_511_nv`'s ArcGIS lane),
  so an unprovisioned key is a per-target refusal rather than a stalled
  multi-target source.
- The ten enumerated probe outcomes are graduated, not deleted: each
  graduated row's notes carry the verbatim 2026-09-17 probe record and the
  declared-contract caveat; the other enumerated rows (robots-unretrievable,
  not-found, unresolved-rights) are untouched.

## Alternatives considered

- **Header-only support, refuse query-param platforms** — rejected: it would
  strand nine of the ten keyed lanes; the platform's documented form is the
  contract and the wire-only discipline removes the leak surface rather than
  the lane.
- **Raise `KeyNotProvisioned` as a fatal run error** — rejected: it would
  turn an unprovisioned credential into a crash that abandons the run's
  other targets and would look like a failure rather than the honest
  `partial` record of a not-yet-provisioned lane.
- **Parse leniently (accept whatever keys exist)** — rejected: the contract
  is unobserved; lenient parse would silently emit whatever shape arrives
  (including an error page's table cells). Strict drift is the evidence-first
  posture.

## Revisit trigger

- A registered Iteris/IBI-511 state answers a keyed run with a **non-array**
  payload or a platform other than the documented family (e.g. the reported
  511x migrations) — then this ADR's declared contract needs amending or a
  second kind.
- OHGO begins paginating `v1/cameras` (`CurrentResultCount <
  TotalResultCount` in a keyed capture) — the single-page contract breaks;
  add declared page expansion or stop at drift permanently.
- A platform publishes a credential form other than `?key=`/
  `Authorization: APIKEY` — the env-name registry pattern holds, the
  transport seam may need a third carrier.
- The operator's OP-13 registration lands and any `sig-us511-*-key` binding
  changes name — the cadence `secrets` maps and `api_key_env` values must be
  updated together.
