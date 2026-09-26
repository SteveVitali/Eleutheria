# ADR-086 — HG-02 counsel resolution: derived-facts sources publish in a dedicated `derived_facts` compartment

- **Status:** Accepted
- **Phase / ticket:** operator-reported counsel determination (HG-02, 2026-09-16), post-P25.7 licence-compartment resolution
- **Date:** 2026-09-16
- **Related:** ADR-085 (the derived-facts + mandated-disclosure basis), P25.7 (the recorded-exclusion seam), HG-02, SIG-LIC-003/004a/005, §42.2/42.3, `policy/data/licenses.toml`, `connectors/data/sources.toml`.

## Context

Eleven sources carry `spdx = "LicenseRef-DerivedFacts-Citations"` — the ADR-085 /
counsel-approved basis under which SIG emits its own derived facts and citations
and never re-hosts upstream expressive content: `ccops_seattle`, `ccops_nyc_post`,
`ccops_sf`, `pathways_rtcc_federation`, `pathways_fr_css_forensics`,
`pathways_acoustic_drone_location`, `madada`, `declarationcamera_be`,
`carnegie_ai_gsi`, `facial_recognition_world_map`, `aspi_mapping_chinas_tech_giants`.

P25.7 recorded the pending HG-02 publication decision as data:
`export_disposition = "excluded"` + `exclusion = "counsel_pending"` on the licence
row, so every export gate refused the licence with a *named* reason rather than an
unhandled gap. The row's own comment documented the intended resolution path —
counsel replaces the exclusion with a real `relicensable_to` set + a
`[compartments.*]` row as a data change.

On 2026-09-16 counsel resolved HG-02: the derived-facts/citations surface may be
published (operator-reported determination, recorded in `docs/build/LEDGER.md`
GATE DECISIONS).

## Decision

1. **`licenses.toml`: the exclusion is replaced by a real licence row.**
   `LicenseRef-DerivedFacts-Citations` gets
   `relicensable_to = ["LicenseRef-DerivedFacts-Citations"]` — self-relicensable
   only, `share_alike = false`, `attribution_required = true` — and a dedicated
   `[compartments.derived_facts]` row keyed to it. The exclusion keys
   (`export_disposition`, `exclusion`, `exclusion_reason`) are removed.
2. **A dedicated compartment, not a fold into `sig_graph` (CC-BY-4.0).**
   Counsel approved publishing *under the derived-facts basis*; the conservative
   execution keeps the basis visible end-to-end rather than asserting a CC-BY-4.0
   relicensing counsel did not state. The compartment file travels under the
   `LicenseRef-DerivedFacts-Citations` expression, self-describing, and cannot
   merge into any other compartment (`relicensable_to` intersects to itself only).
3. **`redistributable` flips `false → true` on the eleven records.** The flag is
   the separately-reviewed boolean SIG-LIC-003 requires, and counsel's resolution
   *is* that review. The flag governs what leaves the system through the export
   gate — and what leaves is SIG-authored claim rows (facts + citations), never
   upstream bytes: no connector emits upstream content into the claim spine and
   evidence artifacts carry content digests + upstream URIs, not content. The
   ADR-085 invariant "upstream bytes are never re-hosted" is architectural and
   unchanged by this flag.
4. **Per-record attribution carries the citation obligation downstream**
   (`downstream_obligations` already surfaces `attribution` + `terms_url` per row).

## Consequences

- The eleven derived-facts sources' claims can now reach an export — into
  `derived_facts` only, with attribution required; they still cannot fold into
  `sig_graph`, `osm_physical`, or `portal` (the licence math forbids it).
- `aspi`/`ccops_sf`/`declarationcamera_be` have no claims to export today (WAF /
  interstitial / eID walls remain — recorded dispositions stand); the flag change
  is a posture, not a fetch claim.
- The OSM-contribution gate is unaffected: `LicenseRef-DerivedFacts-Citations`
  is not relicensable to `ODbL-1.0`, so these sources still cannot feed
  contribution tasks.
- The remaining HG-02 scope (publication tiers, sensitive-coordinate rules,
  Part VIII surface, the ODbL 4.4(b) opinion — `D-LEGAL.1-1`) is NOT resolved by
  this determination; this ADR covers only the derived-facts publication
  compartment.

## Revisit trigger

Revisit if counsel refines the publication terms for derived-facts sources (e.g.
permits folding into CC-BY-4.0, or attaches conditions beyond attribution), or if
a connector for a derived-facts source is ever changed to emit upstream content
rather than SIG-authored claims.
