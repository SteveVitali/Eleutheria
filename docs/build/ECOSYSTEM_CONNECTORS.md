# Ecosystem connectors — Data Driven + coarse-international (P21.8)

Per-source record of the ecosystem connectors P21.8 landed: the requirement ids
each satisfies, the committed fixtures it runs over, its live state, and the claims
it produces. **No live fetch ran this ticket** — HG-03/HG-04 = SKIP (no source
flipped); every source below is `ingestion_permitted=false` and `run --mode live`
**REFUSES (exit 3)** until an operator flips it after reading the rights packet.

## `data_driven` — EFF/MuckRock Data Driven releases

- **Connector:** `connectors/src/connectors/data_driven.py` (`DataDrivenConnector`),
  registered in `sig-connectors list-connectors`.
- **Source:** `eff_data_driven` — `custody_posture=MIRROR` candidate, rights
  **UNDETERMINED** (packet `docs/build/rights/eff_data_driven.md`),
  `ingestion_permitted=false`.
- **Requirement ids:** SIG-INGEST-043, 043a, 043b, 043c, 043d (MET); SIG-INGEST-044
  (rationale — embodied by the records-request linkage); SIG-INGEST-021/033/034/028.
- **Fixtures:** `tests/connectors/fixtures/data_driven/release_v1.json`,
  `release_v2.json` (two release versions proving versioning), and
  `release_with_per_search_column.json` (proves the aggregate-only rejection).
- **Live state:** **REFUSED (exit 3)** — gate reasons: `ingestion_permitted=false`,
  rights UNDETERMINED, review metadata absent (HG-03 pending). Asserted by
  `test_data_driven.py::test_cli_live_run_exits_3`.
- **Claims produced (over fixtures, replay/shadow):** per-agency **aggregate**
  claims only — `deployment_exists` (non-Flock vendor), `scan_volume_observed`,
  `hit_volume_observed`, `non_hit_proportion_observed` (~99.552% non-hit for the
  federal row), `sharing_partner_degree` (degree only, never an edge list),
  `pooled_lookup_participation`, `retention_window_observed` (per-column, units
  preserved), plus a `records_request_link` to the MuckRock request that produced
  each agency's data. Every claim is **historical** (`observed_at`) and carries the
  release version + digest + retrieval date; a versioned re-ingest appends new
  dated claims and overwrites nothing. Shadow re-run over the fixtures = **0 diffs**.

## `coarse_international` — Carnegie AI GSI / Facial Recognition World Map / ASPI

- **Connector:** `connectors/src/connectors/coarse_international.py`
  (`CoarseInternationalConnector`), registered in `list-connectors`. Every row is
  routed through `coarse_claim`, so the anti-disaggregation guard (SIG-INGEST-042)
  cannot be bypassed.
- **Sources (all LINK posture, rights UNDETERMINED, `ingestion_permitted=false`):**
  - `carnegie_ai_gsi` — country-level; packet `rights/carnegie_ai_gsi.md`.
  - `facial_recognition_world_map` — country-level; packet
    `rights/facial_recognition_world_map.md`.
  - `aspi_mapping_chinas_tech_giants` — vendor-level; packet
    `rights/aspi_mapping_chinas_tech_giants.md`.
- **Requirement ids:** the P18.1 coarse-source ids routed P21.8; SIG-INGEST-042
  (anti-disaggregation), SIG-INGEST-021/028.
- **Fixtures:** `tests/connectors/fixtures/coarse_international/{carnegie_ai_gsi,
  facial_recognition_world_map,aspi_mapping_chinas_tech_giants}.json`.
- **Live state:** **REFUSED (exit 3)** for all three — LINK custody + not_contacted
  compact + `ingestion_permitted=false` (HG-03 pending). LINK posture is kept; the
  capture path runs through `run --mode live` unchanged once a packet + flip changes
  a row. Asserted by
  `test_coarse_international.py::test_all_three_coarse_sources_keep_link_posture_and_are_gated`.
- **Claims produced (over fixtures, replay/shadow):** coarse claims at the dataset's
  own granularity (country `jurisdiction` or `vendor`), stamped
  `disaggregation_prohibited=true`, raw value preserved (P2). Shadow re-run = 0 diffs.

## Gate status

HG-03 / HG-04 **per source: SKIP — no source flipped.** No live run occurred; no
`docs/build/live_runs/` fetch record was written. Every new/updated row stays rights
UNDETERMINED / `ingestion_permitted=false`. Per-source HG-03/HG-04 recorded
**pending**.
