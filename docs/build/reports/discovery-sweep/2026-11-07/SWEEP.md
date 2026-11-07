# Discovery sweep 2026-11-07 — registry completeness over the Data Library index (P37.13, `sig.discovery-sweep/1`)

The first sweep under `../README.md`, continuing Stream I's method
(research/I3…I9b — a query log, per-candidate dispositions, honest negatives).
Scope: the documented feed universe — the EFF Data Library index, the spec
§22.7 roster, and the spec §22.6 H2 project list — mapped against the source
registry (`sources.toml`). `live_verification=false`: nothing here runs a
connector stage; the index page itself was fetched and byte-recorded as the
enumeration input (Q001/Q002), never an ingestion.

## Inputs

- **Index fetch (Q001/Q002):** `https://www.atlasofsurveillance.org/data-library`
  — 55,418 B, sha256 `0a0d364c05f00f31…`, fetched 2026-11-07; **42** dataset
  sections enumerated (name + report/dataset links).
- **Spec roster (Q003):** the §22.7 table parses to **16** rows from
  `docs/research/_meta/spec_src/51b_partIV_s22_6_seeded_registry.md`
  (F2a-verdicts.md: 16, not 17).
- **Spec §22.6 H2 (Q004):** 7 project rows — all already registered.
- **Registry diff (Q005–Q008):** 602 registered ids before this ticket.

## Findings

- **The §22.7 roster is now fully registered — 16/16** (SIG-INGEST-041).
  The F2a verdict's "11 of 16 unregistered" (2026-09-30) moved twice since:
  P35.6's ACQ-01 generation pre-covered three entries
  (`statrep_us_upturn_mass_extraction_2020`,
  `statrep_us_wiretap_summary_tables`, and the CA auditor rows
  `ca_state_auditor` + `statrep_ca_california_auditor_alpr`), and P37.13
  registers the remaining **eight** as LINK rows (`datalib_*`), never
  `ingestion_permitted` — the operator's HG-03 line flips them.
- **Mapping honesty.** Two entries are recorded `equivalent`, not `exact`:
  the index's Cell-site Simulators is Kevin Collier's aggregation (the spec
  names the ACLU set — `aclu_cell_site_simulators` carries it), and the CA
  ALPR entry links EFF's raw-CPRA mirror where the registry rows carry the
  State Auditor's own publication. An `equivalent` is a recorded claim, never
  a silent conflation; the roster file's `mapping` column holds the verdict.
- **Coverage beyond the roster.** The index carries **23 datasets the spec
  roster does not name** — Data Driven 2: California Dragnet, the CalECPA
  search-warrant disclosures, the state BWC surveys/grant lists, the Brennan
  social-media-policy directory, the Prison Policy contracts library, the
  National Police Funding Database, Surveillance Watch, Archivo de la
  Vigilancia, and more — recorded `candidate-unregistered` in
  `candidates.csv` (registered/nearby rows are named `related:` where they
  exist). Registering them is out of this ticket's scope: each needs its own
  id, rights and connector decision — `D-P37.13-1` carries the triage.
- **No unregistered §22.6 H2 rows.** All seven SIG-INGEST-048 project rows
  resolve to existing registry ids.

## Counts

| surface | enumerated | registered before | registered by this sweep | candidates |
|---|---|---|---|---|
| §22.7 spec roster | 16 | 8 | 8 (LINK) | 0 |
| Index (non-roster) | 26 | 3 (`eff_atlas_of_surveillance`, `surveillance_under_surveillance`, `deflock`) | 0 | 23 |
| §22.6 H2 projects | 7 | 7 | 0 | 0 |
| **total** | **49** | **18** | **8** | **23** |

## Anchors for the registered rows

<a id="datalib_who_has_your_face"></a>`datalib_who_has_your_face` ·
<a id="datalib_clearview_ai_table"></a>`datalib_clearview_ai_table` ·
<a id="datalib_public_safety_drones"></a>`datalib_public_safety_drones` ·
<a id="datalib_ring_neighbors_partnerships"></a>`datalib_ring_neighbors_partnerships` ·
<a id="datalib_federally_funded_bwc"></a>`datalib_federally_funded_bwc` ·
<a id="datalib_aaron_swartz_day"></a>`datalib_aaron_swartz_day` ·
<a id="datalib_mediajustice_em_map"></a>`datalib_mediajustice_em_map` ·
<a id="datalib_atlas_border_communities"></a>`datalib_atlas_border_communities`
— all `custody_posture = "LINK"`, `ingestion_permitted = false`, rights
UNDETERMINED; `live_dispositions.toml` `link_only`.

## Next sweep

Per `../README.md`: re-fetch + re-enumerate, diff against `candidates.csv` —
moved dispositions are coverage gain; new index sections are discovery yield.
`D-P37.13-1` owns the 23 candidates' registration triage.
