# ADR-238 — Keyed AU traffic-camera lanes: declared-contract GeoJSON kinds and the QLDTraffic supersession (P37.70)

- Date: 2026-11-07
- Status: accepted
- Ticket: P37.70 (Round 11 / P37, row 434 — the named home of D-SOURCES.8-2's
  engineering half; GATE-G6 §4 pre-authorisation, expires GATE-ACCEPT-R11)
- Base: `r11/P37.12-keyed-us-511-wiring`
- Related: ADR-237 (the wire-only credential seam + env-name registry rule
  these lanes reuse), ADR-083 (the API allowlist), ADR-088 (GL-GATE-08 —
  robots probed and recorded, never enforced), HG-09 (secrets are
  environment/Secret Manager only), D-SOURCES.8-2, E4-R4c = b, OP-13,
  `connectors/dot_511.py`, `connectors/data/camera_registry_targets.toml`,
  `ops/cadence.toml`.

## Context

Two Australian traffic-camera APIs are enumerated in
`camera_registry_targets.toml` as `keyed_api`: TMR's QLDTraffic
`api.qldtraffic.qld.gov.au/v1/webcams` (HTTP 401 'Missing Authentication
Token' at the 2026-09-18 probe; the CKAN dataset documents CC-BY-3.0/CC-BY-4.0)
and TfNSW's Live Traffic `api.transport.nsw.gov.au/v1/live/cameras` (HTTP 401;
robots.txt answered 500 so no policy was recorded). D-SOURCES.8-2 part a owes
their wiring **after the operator registers the keys** (OP-13/HG-09); E4-R4c =
b decides the QLDTraffic API **replaces** `camreg_qldc_au`'s gated ArcGIS lane
as QLD's authoritative registry.

Both endpoints' published developer documentation declares the same payload
shape — a GeoJSON `FeatureCollection` of camera Features — but two different
credential forms: QLDTraffic documents the `?apikey=` query parameter, TfNSW's
API Gateway documents the `Authorization: apikey <key>` request header. ADR-237
already built the generic seams (`auth_param` wire-only query param, the
`Authorization` header path, `api_key_env` env-NAME-only declarations,
`KeyNotProvisioned` zero-egress refusal): this row's decision is the declared
contract and the supersession, not new machinery.

Neither payload has ever been observed — every probe answered the key wall —
so the contracts are DECLARED from the published docs and enforced strictly at
parse.

## Decision

1. **Reuse the ADR-237 credential seams, no new carrier.** QLDTraffic's
   `?apikey=` rides `auth_param` (the credential reaches the wire URL only —
   every recorded surface keeps the credential-free URL); TfNSW's key rides
   the documented `Authorization: apikey <key>` header so no credential lands
   in any URL at all. Each graduated row carries `api_key_env` naming a
   `SIG_*` env var (`SIG_QLDTRAFFIC_KEY`, `SIG_NSW_LIVE_KEY`) — a literal is a
   registry defect (`KeyedSpecNotDeclared`), and an unset env is a recorded
   `KeyNotProvisioned` refusal before any egress.
2. **Two declared-contract, fail-closed kinds.** `qldtraffic_geojson` and
   `nsw_live_geojson` expand to a single declared page each and parse the
   documented shape strictly: `type == "FeatureCollection"`, a `features`
   list, every member a `{type: "Feature", geometry, properties}` object —
   an error envelope, a non-JSON shell, a non-FeatureCollection type, or a
   malformed feature is `ContentDrift`, never a silent emit. TfNSW's Developer
   Guide additionally documents a `rights` member ({copyright, licence}): its
   absence is drift under the declared contract — the in-band licence
   declaration is evidence, and a payload missing it is never silently
   re-licensed. Feature rows normalise to (properties + the top-level `id`,
   the `geometry.coordinates` [lon, lat] point) at extract; media-bearing
   fields (`image_url`, `href`, `url`, …) stay name-excluded under the
   existing blocklist (Part VIII).
3. **QLDTraffic replaces `camreg_qldc_au` (E4-R4c = b).** The new keyed lane
   is its own source (`camreg_qldtraffic_au`) — a keyed target never shares a
   source row with an unkeyed one (ADR-237 consequence) — and carries
   `qld_qldtraffic_api` graduated to `[[targets]]`. The gated
   `camreg_qldc_au` ArcGIS row stays in `[[targets]]` as the verified
   enumeration record, its notes recording the supersession; the source row's
   notes record the replacement lane. Nothing is deleted or renamed.
4. **Every lane stays gated and paused.** Both new `camreg_*` source rows are
   `ingestion_permitted=false` (rights UNDETERMINED; the CC-BY leads are seed
   evidence for the rights review, not a resolved record); the two
   `ops/cadence.toml` seats are `state = "paused"` carrying the
   `SIG_*_KEY` → `sig-*-key` Secret-Manager binding map — the wiring the
   operator's OP-13 registration fills. The operator's HG-03 rights flip plus
   the key is the only route to a live fetch; the keyed live legs are
   deferred under `D-P37.70-1` (the GATE-G6 §4 naming recorded, the
   contract's own preconditions unmet in the engineering dispatch).

## Consequences

- The `dot_511` connector now carries two GeoJSON FeatureCollection lanes
  through the same strict-parse / env-name-credential discipline the US 511
  lanes use — no bespoke HTTP client, no credential in any record.
- TfNSW's `rights` member is the first in-band licence declaration enforced
  as part of a declared contract: an absent or changed member is recorded
  drift (OM-18), the licence provenance rides the captured payload.
- The supersession is recorded, never erased: `camreg_qldc_au` stays a gated,
  verified target row and the authoritative lane is the keyed API — matching
  the Austin `austin_atd_legacy_cameras` enumeration-honesty pattern.
- An unprovisioned lane is a per-target refusal, not a stalled multi-target
  source and not a fabricated disappearance.

## Alternatives considered

- **One generic `geojson_rows` kind for both APIs** — rejected: the
  credential carriers differ (query param vs header) and NSW's declared
  contract carries `rights` while QLD's does not; per-platform kinds keep the
  declared contract honest and let a future keyed GeoJSON source land the
  same way P37.12/P37.70 did.
- **Flip `camreg_qldc_au`'s existing source row to carry the API** —
  rejected: the ArcGIS upstream and the keyed API are different upstreams
  with different rights postures; mixing them would hide which fetch produced
  which claims and would couple an unkeyed gated row to a keyed lane.
- **Parse leniently** — rejected for the ADR-237 reason: the contract is
  unobserved; lenient parse would silently emit whatever shape arrives.

## Revisit trigger

- Either keyed run meets a payload deviating from the declared contract — a
  non-FeatureCollection document, features without `properties`, a missing
  NSW `rights` member — then this ADR's declared contract needs amending or a
  further kind.
- Either platform publishes a credential form other than `?apikey=` /
  `Authorization: apikey` — the env-name registry pattern holds, the
  transport seam may need a third carrier.
- The operator's OP-13 registration lands and any `sig-qldtraffic-key` /
  `sig-nsw-live-key` binding changes name — the cadence `secrets` maps and
  `api_key_env` values must be updated together.
- The rights review resolves the CC-BY lead differently (the CKAN metadata
  proves stale or the in-band `rights` member disagrees) — the source rows'
  licence lead is seed evidence, not the resolved record.
