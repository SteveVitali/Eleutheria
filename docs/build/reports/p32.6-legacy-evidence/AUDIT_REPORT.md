# Legacy evidence audit — `evidence-audit/1`

> Read-only, offline, reproducible. Generated (deterministic run).

## Input identity (the reproducibility contract)

| field | value |
|---|---|
| population source | `input-json:docs/build/reports/p32.6-legacy-evidence/fixture_spine.json` |
| claims selected | 16 |
| population digest | `sha256:9920fd40b88c3faa7c1cf0ce71a79df7d12d3dfe26be7697ff0b84ee54efd98c` |
| seed | `p32.6-fixture-seed-v1` |
| sample requested/drawn | 16/16 (+2 targeted) |
| roll boundary | `2026-09-25T00:00:00Z` |
| capture probe | `ocfl:docs/build/reports/p32.6-legacy-evidence/capture_root` |
| bytes read/budget | 188/2147483648 (exhausted: False) |
| code commit | `616b889c19b587871483930ca358eb35712a2dcf` |

## Census (denominators reconcile: True)

- 16 claims; links 16; establishing 16
- by source family: `{'atlas_registry': 10, 'osm_overpass': 6}`
- by capture epoch: `{'post_roll': 6, 'pre_roll': 10}`
- by predicate role: `{'operator': 5, 'unmapped': 11}`
- by compartment: `{'ontology': 1, 'osm_physical': 7, 'sig_graph': 8}`

## Strata

| stratum (family|epoch|role|compartment) | universe | drawn | weight |
|---|---|---|---|
| atlas_registry|post_roll|operator|sig_graph | 1 | 1 | 1.000 |
| atlas_registry|post_roll|unmapped|osm_physical | 1 | 1 | 1.000 |
| atlas_registry|post_roll|unmapped|sig_graph | 2 | 2 | 1.000 |
| atlas_registry|pre_roll|operator|osm_physical | 1 | 1 | 1.000 |
| atlas_registry|pre_roll|unmapped|osm_physical | 2 | 2 | 1.000 |
| atlas_registry|pre_roll|unmapped|sig_graph | 3 | 3 | 1.000 |
| osm_overpass|post_roll|operator|osm_physical | 1 | 1 | 1.000 |
| osm_overpass|post_roll|unmapped|sig_graph | 1 | 1 | 1.000 |
| osm_overpass|pre_roll|operator|osm_physical | 1 | 1 | 1.000 |
| osm_overpass|pre_roll|operator|sig_graph | 1 | 1 | 1.000 |
| osm_overpass|pre_roll|unmapped|ontology | 1 | 1 | 1.000 |
| osm_overpass|pre_roll|unmapped|osm_physical | 1 | 1 | 1.000 |

## Metrics (probability sample)

| metric | n/d |
|---|---|
| source attribution | 14/14 (100.0%; weighted 100.0%) |
| verified capture availability | 9/14 (64.3%; weighted 64.3%) |
| occurrence — exact | 14/14 (100.0%; weighted 100.0%) |
| occurrence — bounded | 0/14 (0.0%; weighted 0.0%) |
| occurrence — unknown | 0/14 (0.0%; weighted 0.0%) |
| exact locator coverage | 14/14 (100.0%; weighted 100.0%) (document-occurrence w/o locator: 0) |
| replay success (mechanical) | 8/8 (100.0%; weighted 100.0%) |
| publication eligibility | 14/14 (100.0%; weighted 100.0%) |
| legacy/synthetic exposure | 0/14 (0.0%; weighted 0.0%) |

### Grade distribution

| grade | claims |
|---|---|
| exact_replayable | 8 |
| restricted_not_public | 2 |
| unrecoverable | 4 |

## Semantic support (the three required forms)

| form | value |
|---|---|
| support over ALL sampled eligible claims | 8/14 = 57.1% |
| conditional adjudicated fidelity | 8/14 = 57.1% |
| adjudication yield | 8/14 = 57.1% |
| unresolved — evidence unavailable (stays in fidelity denominator) | 6 |
| unresolved — needs adjudication | 0 |

### Targeted set (reported separately, never weighted)

| claim | grade | occurrence | adjudication |
|---|---|---|---|
| claim-unsupported-0 | source_attributed_only | bounded | not_established |
| claim-synthetic-0 | source_attributed_only | bounded | unresolved |

## Findings

| kind | claim | detail |
|---|---|---|
| digest_mismatch | claim-mismatch-0 | stored bytes do not match the recorded content_digest |
| digest_mismatch | claim-mismatch-1 | stored bytes do not match the recorded content_digest |
| unsupported_role_mapping | claim-unsupported-0 | entity-ref predicate with no verified evidence supporting the role |
| missing_bytes | claim-missing-0 | recorded capture bytes absent from the probed root |
| missing_bytes | claim-missing-1 | recorded capture bytes absent from the probed root |

## Limitations

- Offline read-only audit: no live fetch, no spine mutation, no publication change.
- occurrence 'exact' requires post-P31.4 ingest_run_capture marks; pre-roll acquisitions are 'bounded' by construction, not 'exact'.
- Mechanical replay covers byte_range/row/cell locators; page/bbox/dom_path and normalization-level fidelity need the adjudicator instrument (HUMAN-H4).
- unverified captures (no probe mounted / restricted unreadable) are reported as unverified, never counted as missing.
