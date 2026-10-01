# Legacy evidence audit — `evidence-audit/1`

> Read-only, offline, reproducible. Generated (deterministic run).

## Input identity (the reproducibility contract)

| field | value |
|---|---|
| population source | `dsn(read-only)` |
| claims selected | 16 |
| population digest | `sha256:d9edce6e37e87141cc92d13bf6f35fa70d1ead72b242ba376ae7c10b9a5931d6` |
| seed | `p32.22-fixture-seed-v1` |
| sample requested/drawn | 16/16 (+2 targeted) |
| roll boundary | `2026-09-25T00:00:00Z` |
| capture probe | `ocfl:docs/build/reports/p32.6-legacy-evidence/capture_root` |
| bytes read/budget | 188/2147483648 (exhausted: False) |
| code commit | `10547fff2072e1a9f9481dc8d7adf2a972031091` |

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
| 2007d8e5-4241-59e3-af19-0b4c263c9f55 | source_attributed_only | bounded | not_established |
| 95ed13f3-e64b-579f-b03c-e0b3cd8edeec | source_attributed_only | bounded | unresolved |

## Findings

| kind | claim | detail |
|---|---|---|
| unsupported_role_mapping | 2007d8e5-4241-59e3-af19-0b4c263c9f55 | entity-ref predicate with no verified evidence supporting the role |
| digest_mismatch | 83f41edf-a6ca-5548-94a1-42a5c91444f7 | stored bytes do not match the recorded content_digest |
| digest_mismatch | 8daffc4c-219b-5490-bd03-62a661db27f8 | stored bytes do not match the recorded content_digest |
| missing_bytes | c101e8bc-4999-5309-aed4-fd9626822263 | recorded capture bytes absent from the probed root |
| missing_bytes | dae8cca4-dc93-5a3f-98fa-41c4c2495eca | recorded capture bytes absent from the probed root |

## Limitations

- Offline read-only audit: no live fetch, no spine mutation, no publication change.
- occurrence 'exact' requires post-P31.4 ingest_run_capture marks; pre-roll acquisitions are 'bounded' by construction, not 'exact'.
- Mechanical replay covers byte_range/row/cell locators; page/bbox/dom_path and normalization-level fidelity need the adjudicator instrument (HUMAN-H4).
- unverified captures (no probe mounted / restricted unreadable) are reported as unverified, never counted as missing.
