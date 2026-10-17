# ADR-160 — The jurisdiction registry, the GeoParquet boundary pack, and `lookup@1` (P35.17)

- Date: 2026-10-17
- Status: accepted
- Ticket: P35.17 (Round 11 / P35, manifest row 297 — K4 §3.1/§3.2/§4.2/§5.4)
- Base: `r11/P35.16-geometry-defects-at-ingest`
- Related: ADR-079 (revisited — the jurisdiction-collision trigger fired),
  ADR-122 (revisited — the count-scope jurisdiction-as-token trigger fired),
  SIG-GEO-008 (never assert a location the evidence does not support),
  SIG-IDENT-005/006 (fixed-width codes; (scheme, value) identity),
  SIG-JUR-D01 (no bare jurisdiction labels), SIG-INGEST-028 (the fail-closed
  ingestion gate), P35.12 (the descriptor-v2 `boundaries_root` field this
  populates), P35.16 (geometry hygiene upstream of this foundation)

## Context

The K4 dossier/index architecture needs a jurisdiction spine: placement,
containment, and the K13 `kind=place` consumer all name jurisdictions, and
today's surface names them with **bare labels** — `jurisdiction = "MN"`,
`"ID"`, `"DE"`. Those labels are ambiguous by construction: `ID` is ISO
3166-1 for Indonesia *and* USPS for Idaho; `MN` is ISO for Mongolia *and*
USPS for Minnesota; `DE` is ISO for Germany *and* USPS for Delaware — while
"Cologne" is simultaneously a German municipality (AGS `05315000`, German
name *Köln*) and a Census place in Minnesota (GEOID `2712670`). Two revisit
triggers fired on landed ADRs:

- **ADR-079** (SEED-11d evaluation, 2026-10-01): "jurisdiction codes collide"
  — the ILIKE jurisdiction filter and bare labels cannot scale past the seed
  jurisdictions (FIRED).
- **ADR-122** (same evaluation): "the count-scope jurisdiction is an
  unscoped token, not structured geometry" (LIKELY FIRED).

The boundary bytes themselves are gated: `census_gazetteer_tiger` (TIGER/Line
+ Gazetteer — a US Government work, no copyright under 17 U.S.C. §105, terms
captured verbatim into `docs/build/reports/rights/census_gazetteer_tiger.md`)
and `natural_earth_10m` (public domain, terms captured into
`docs/build/reports/rights/natural_earth_10m.md`) are registered with
`ingestion_permitted=false`. **D-K4-1 = yes** (2026-10-01T04:21:56Z)
authorises the terms-text capture *first*, then an in-ticket pause for the
operator's **HG-03 flips** — the flips are the operator's act and did not
happen in this run. The hosted OCFL capture therefore stayed **queued, never
exercised** (this invocation ran `live_verification=false`); the pack
machinery, registry, and lookup contract merged anyway against declared
fixture inputs.

Two further posture answers were carried from the operator's K-BATCH-a batch
(packet B-22, answer `a` — "accept the 52 K-row design recommendations as
written", 2026-10-01T04:33:54Z), verbatim:

- **D-K4-2** — *Disputed-territory point of view (TW, PS, HK, XK, EH,
  Crimea)*: **"as recommended (B-22 K-BATCH a): ISO 3166-1 as published; XK
  labelled user-assigned; neutral names; one standing note."**
- **D-K4-4** — *US territories: under the United States or as countries*:
  **"as recommended (B-22 K-BATCH a): under US (Census state-equivalents),
  with ISO 3166-1 aliases."**

## Decision

1. **Canonical keys name their scheme — a jurisdiction is never keyed on a
   bare code** (K4 §3.1, SIG-JUR-D01). The key families:
   `iso3166-1:<A2>` (countries), `iso3166-2:<A2>-<sub>` (admin-1),
   `us.census.geoid.county:<SSCCC>` and `us.census.geoid.place:<SSPPPPP>`
   (fixed-width Census GEOIDs, level explicit per SIG-IDENT-005), and
   `national:<scheme>:<code>` via `key_scheme = "national:<scheme>"` (e.g.
   `de.ags:05315000`) for non-US municipalities whose national open datasets
   land later (K4 §4.3). Every other identifier rides as a
   `(scheme, value, kind)` pair (SIG-IDENT-006); `(scheme, value)` must
   resolve to at most one key.
2. **The declared-scheme map** (K4 §3.2): claim-side `(scheme, value)` pairs
   map deterministically — `us.state_abbr:MN → iso3166-2:US-MN`,
   `iso.3166_1_alpha2:MN → iso3166-1:MN`, `iso.3166_2` passthrough,
   `sig.unresolved →` no key. An undeclared scheme raises — a bare code is
   never guessed.
3. **D-K4-4 — territories under the US.** Census state-equivalents (PR, VI,
   GU, AS, MP, UM) key `iso3166-2:US-*` with parent `iso3166-1:US`; where ISO
   publishes a 3166-1 code for the territory it is carried as an identifier
   with `kind = "alias"` — an alias, never the key, so `iso3166-1:PR` and
   `iso3166-2:US-PR` can never be conflated.
4. **D-K4-2 — disputed territories.** ISO 3166-1 codes as published (TW, PS,
   HK, EH); Kosovo keys `iso3166-1:XK` carrying `code_status =
   "user-assigned"`; names are neutral; the registry document carries ONE
   standing note. This is a recorded posture, not an adjudication
   (SIG-GEO-008 §3.1) — the registry asserts nothing about sovereignty.
5. **The boundary pack is a restricted export input, verified.** Upstream
   files (TIGER/Line state/county/place, Gazetteer names/points, Natural
   Earth 10m admin-0/admin-1, the 500k cartographic set for display only —
   never containment, K4 §4.1) are declared in
   `exports/data/boundary_pack.toml` (`sig.boundary-pack/1` spec — data, not
   code), captured to OCFL after the HG-03 flips, and converted by
   `sig-exports boundaries build` to GeoParquet (WKB + the `geo` footer
   block, written through DuckDB `spatial`). `build_pack` **fails closed**:
   it refuses unless every declared layer's source is
   `ingestion_permitted`, or the caller declares fixture inputs — which is
   recorded as `gate.mode = "fixture-bypass"` in the manifest so a fixture
   pack can never pass for a captured one. Each layer file is sha256'd and
   the manifest's `boundaries_root` is the digest of the canonical
   `{relpath: sha256}` map.
6. **`boundaries_root` binds the verified pack to descriptor v2.** The pack
   staged at `<export>/inputs/boundary-pack/` is re-verified file-by-file at
   release build; the *recomputed* root is what the descriptor signs, and an
   explicit `--boundaries-root` that disagrees fails the build — a
   contradiction is never signed (REL-01). No staged pack → declared-empty
   (the P35.12 semantics).
7. **`lookup@1`** (K4 §5.4): `lookup(name, level=None, within=None)` returns
   candidates `{jkey, name, level, score, basis, rules}` — exact normalised
   official name (1.0), then identifiers (0.95 — a code asked for its
   scheme's value), then alternates (0.9), filtered by level and by ancestor
   subtree (`within` is inclusive). **Ambiguity returns every candidate** —
   the consumer records `name_ambiguous` (R8); lookup never guesses.
8. **US enrichment order:** the Gazetteer layers mint no keys — they enrich
   TIGER-keyed rows (names, GNIS/ANSI ids, internal points). The GB admin-1
   rollup is recorded in the spec (`geonunit → ENG/SCT/WLS/NIR`): the 232
   local-authority units union to the ISO 3166-2 first tier, and the rollup
   map *is* the record of the tier chosen.

## Consequences

- Bare jurisdiction labels are no longer admissible where a canonical key is
  required; the `ID`/`MN`/`DE` collisions resolve through scheme or through
  `within`/`level` filters, and an un-resolvable name returns all candidates.
- The hosted OCFL capture of the two boundary sources remains **queued behind
  the operator's HG-03 flips** — the OM-20 listing names this row, but the
  invocation's `live_verification=false` means capture was never exercised;
  the re-run prompt lives in RETURN PASS.
- Fixture packs are honest: `gate.mode = "fixture-bypass"` is in every
  fixture manifest, and the descriptor still verifies staged bytes before
  binding the root.
- Non-US national municipality schemes (e.g. `de.ags`) are admitted by the
  schema before their datasets land — keys mint when a layer is declared,
  never before.
- `exports` gains `sig-exports boundaries {build,registry,verify,root,stage,
  lookup,validate}` — all offline, all fail-closed with non-zero exits.

## Alternatives considered

- **Key on display names or bare codes** — rejected: ambiguity is the defect
  being fixed (ADR-079's fired trigger).
- **A political adjudication layer for disputed territories** — rejected:
  out of scope and out of competence; ISO-as-published + a standing note is
  the recorded posture (D-K4-2).
- **Wait for the HG-03 flips before landing any code** — rejected: the
  contract sequence is terms capture → repo machinery merges → pause →
  capture; blocking the registry on a human gate would put the K13 consumer
  behind a calendar, not a decision.

## Revisit trigger

Revisit this decision when any of the following holds:

- **The HG-03 flips land and the hosted OCFL capture runs** — the
  `boundaries_root` binds a captured pack; if real TIGER/NE vintages change
  the minting behaviour (e.g. NE ships an ISO code for Kosovo, or a new
  admin-0 unit), the rollup/skip rules and this posture record are re-read
  against the captured evidence.
- **A non-US national dataset lands** (e.g. a German AGS layer or GeoNames
  per OD-09) — the `national:<scheme>` family gets its first production
  member; the scheme registry may need promotion to a declared table.
- **lookup@1 proves insufficient** — e.g. a consumer needs ranked fuzzy
  match, phonetics, or containment-by-point; a `lookup@2` is a new ADR (the
  ruleset id is versioned).
- **A rights review reclassifies either boundary source** — the registry's
  CC-BY-4.0 attribution header and the pack's gate record are regenerated,
  never silently edited.
- **A new disputed-territory posture is directed by the operator** — D-K4-2
  is a recorded posture; a different operator answer is a new decision, and
  the standing note + `code_status` vocabulary change together.
