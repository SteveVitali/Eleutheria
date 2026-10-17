# ADR-210 — Per-target axis-order declarations and the closed geometry-defect classes (P35.16)

- Date: 2026-10-17
- Status: accepted
- Ticket: P35.16 (Round 11 / P35, manifest row R11-DATA-01 — F-322, severity S1)
- Base: `r11/P35.13-provenance-stamp-release-json-headers`
- Related: SIG-GEO-008 (axis order is a declared property of a feed), SIG-IDENT-004
  (never assert a location the evidence does not support), SIG-INGEST-033
  (closed predicate allowlist), P35.14a (the closed claim-sink vocabulary
  `geometry_defect` registers through), P35.15b (the append-only backfill
  pattern the correction pass mirrors), P35.66 (the parcel-screen precedence:
  a defect-marked point never reaches the screen), ADR-113 (`is_replay`
  evidence-link classification), ADR-092 (observation-level row semantics —
  the export disclosure this ticket adds)

## Context

F-322 audited the shipped camera-registry surface against its own published
coordinates and found seven defect groups — records whose asserted point
contradicts the jurisdiction the row claims:

- **Nottingham** (562 rows) and **mark43** (561): the feeds serve the
  coordinate pair lat-first; the ingest read every positional pair as
  Esri/GeoJSON `x=longitude`, so the asserted points landed off East Africa.
- **trafficops D5** (~828 of ~1,430 rows): Central-Florida cameras asserted
  under a declared California jurisdiction.
- **gmh_emc** (GA label, Mongolian points), **bangla** (BD label, Singaporean
  points), **oosgis** (NL label, Belgian points).
- **dot_511_ga** and **camreg_fl511_fl**: `(0,0)`/near-`(0,0)` null-island
  placeholder geometry asserted as real camera locations.

The root cause is structural: the published pair's *axis order* was an
implicit assumption, not a declared property, so a transposed feed produced
silently wrong claims — and nothing ever asked "does this point contradict
the declared jurisdiction?" at emit time. Separately, the portal's
`row_count` on observation-level tables read as an entity count — a
licence-conflicted entity splits across compartment files, so the raw row
count overstates distinct subjects.

## Decision

1. **`axis_order` is a declared per-target field, closed vocabulary**
   (`"lon-lat"` | `"lat-lon"`). It interprets POSITIONAL coordinate pairs —
   the ArcGIS `x`/`y` geometry member and GeoJSON `coordinates[]` slots.
   `"lon-lat"` is the documented default for synthetic/run-time targets
   only; every committed registry row declares the field explicitly and
   `sig-connectors validate` fails on a missing or non-member value — a
   guessed orientation is exactly how F-322 happened. NAMED pairs
   (`latitude`/`longitude` fields, or a keyed point object) are
   name-authoritative under either declaration: a publisher that swaps its
   named columns surfaces as a detector finding, never a silent relabel.

2. **Detector bounds are declared data, not geometry heuristics.**
   `jurisdiction_extents.toml` carries one declared `[min_lon, min_lat,
   max_lon, max_lat]` bound per `(jurisdiction_scheme, code)` the merged
   registry uses; a target may pin its own `extent` where the generic
   bound is not trustworthy (city-tier rows, the axis-defect targets
   themselves). A `sig.unresolved` target carries no bound by design — the
   check records a skip, never a silent pass.

3. **Four closed defect classes, evaluated on the publisher's RAW pair**
   (pre-tier, pre-parcel-screen — the defect lives in the published
   evidence): `null_island` (within 1° of `(0,0)` — the F-322 measure),
   `axis_swap` (outside the bound, the transposition rescues it),
   `sign_flip` (a single-axis negation rescues it), `wrong_jurisdiction`
   (unrescued). A flagged record is **marked, never corrected at emit**:
   it emits a `geometry_defect` claim (registered predicate; class +
   observed pair + failed bound + detector version in the claim evidence)
   and NO `camera_latitude`/`camera_longitude` claims — a defective pair is
   never asserted as a location. The parcel screen does not run on it (the
   verdict records `unscreened`).

4. **Corrections are append-only claims assembled by a declared scope.**
   `geometry_corrections.toml` (`sig.geometry-corrections/1`) declares the
   seven F-322 groups; `sig-connectors geometry-corrections` plans and —
   only with `--apply` — writes through `PgClaimSink` (`is_replay`,
   `ON CONFLICT DO NOTHING`, chunked commits): one `geometry_defect` mark
   per flagged subject, and for `axis_swap` verdicts the provable corrected
   coordinate claims carrying `revises_claim` + `correction_reason`. Other
   classes mint no replacement value — the truth is never fabricated.
   Out-of-scope flags are counted and reported, never written: a defect
   group is corrected only under its committed declaration. Original claims
   are read, never rewritten.

5. **Portal manifests disclose rows vs entities.** Every entity-bearing
   export artifact carries `distinct_entities` beside `row_count` — the
   observation-level semantics (ADR-092) made legible in the index instead
   of implied by a row count that can double-count split entities.

## Consequences

- New ingest over the corrected declarations reads the Nottingham/mark43
  feeds correctly (`axis_order="lat-lon"`); the append-only pass repairs the
  spine for the already-asserted rows without touching history.
- A camera legitimately sited near a jurisdiction boundary is safe: bounds
  carry a practical margin, and the detector targets continent/ocean-scale
  defects, not border surveying.
- Points inside a *neighbouring-jurisdiction overlap* (e.g. a Belgian point
  that still falls inside NL's bounding box) are not flagged — the declared
  bound is a bounding box, not a polygon; residual cases stay visible to the
  per-point mark rather than pretending precision the check does not have.

## Revisit trigger

- A defect class outside the four members (e.g. projected-CRS pairs,
  truncated-precision drift) — add the member to the closed set + the
  detectors together.
- A source whose positional order is neither `lon-lat` nor `lat-lon`
  (e.g. a projected CRS the connector should reject anyway) — the axis
  vocabulary and `extract_coordinate`'s range checks together are the
  answer; do not add a third member for a case that is really
  `out_of_range`.
- A defect group beyond the seven F-322 rows — a new
  `sig.geometry-corrections` artifact version declares it (the scope is the
  authorization); the pass never writes outside a declared group.
- Hosted application still requires the AR-2 restore point + the OM-20
  authorized window — this ADR changes no live posture.
