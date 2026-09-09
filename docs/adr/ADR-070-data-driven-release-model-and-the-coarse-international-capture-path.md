# ADR-070 — The Data Driven release model and the coarse-international capture path

- **Status:** Accepted
- **Phase / ticket:** P21.8 — Ecosystem connectors: EFF/MuckRock Data Driven releases as a first-class source; the coarse-international content path
- **Date:** 2026
- **Related / amends:** ADR-014 (plain-CLI stages), ADR-034 / ADR-056 (ecosystem
  connectors + international coarse sources), ADR-065 (`HttpxTransport` / the gated
  live-run posture, `run --mode live|replay|shadow`), ADR-063 (registry review
  metadata + the flip rule); SIG-INGEST-043/043a/043b/043c/043d/044,
  SIG-INGEST-021/033/034/028, SIG-INGEST-042, RISK-P0-08, RISK-P21-14, RISK-P21-15;
  BL-042.

## Gate status (copied from the run contract)

- **HG-03 / HG-04 (per source): SKIP — no source flipped.** The `data_driven`
  connector and the coarse-international REFERENCE-capture path ship over
  **committed fixtures**. Every new/updated `sources.toml` row stays rights
  **UNDETERMINED** / `ingestion_permitted` absent (false); `run --mode live` for
  `eff_data_driven` and for the coarse trio **REFUSES (exit 3, gate reasons)** —
  asserted by `tests/connectors/test_data_driven.py::test_cli_live_run_exits_3` and
  `test_coarse_international.py::test_all_three_coarse_sources_keep_link_posture_and_are_gated`.
  Per-source HG-03/HG-04 recorded **pending** → the ticket RETURNS PASS with the
  gate skipped. No live network fetch this run.

## Context

The canonical spec names EFF/MuckRock's **Data Driven** releases a first-class
ingestion source (§23.9, SIG-INGEST-043) — the only substantial public evidence
base for pre-Flock, non-Flock ALPR network behaviour — but no ticket in the
46-ticket build ever built it (DECISION_MEMO §5.5, BL-042). Likewise the three
coarse-international datasets (Carnegie AI GSI, the Facial Recognition World Map,
ASPI's Mapping China's Tech Giants) had only a claim-shape + anti-disaggregation
guard (`connectors.coarse_international`, §47/P18.1), not a capture path.

Two problems have to be solved without violating the binding invariants: Data
Driven is per-agency **aggregate** data whose per-search/per-person detail must
never enter the graph (Part VIII §0.7, RISK-P0-08), and it is re-released over
time in incommensurable shapes; the coarse datasets stay LINK-posture and must
never be disaggregated to agency level.

## Decision

1. **The release is the unit of ingestion.** `connectors.data_driven` treats each
   Data Driven release as a **versioned artifact addressed by a content digest**
   and stamped with its retrieval date (`ReleaseManifest`, SIG-INGEST-043b). Every
   claim carries `release_version` + `release_digest` + `retrieved_date` +
   historical `observed_at`, so a **versioned re-ingest yields a new dated claim
   set and never overwrites** the prior one (SIG-INGEST-043d/017). The connector
   targets the **file artifacts directly** and records the article URL as
   *context* (a dead end with no data links, 043b).
2. **Per-agency aggregate rows ONLY, enforced at the ingest boundary.**
   `assert_aggregate_only` scans the release's declared columns and every agency
   row's keys against a data-defined forbidden-token list and **refuses the whole
   release** (`PerSearchColumnError`) if any per-search / per-plate / per-person /
   officer / sharing-edge / partner-list token appears (SIG-INGEST-043, §18.1,
   RISK-P0-08, RISK-P21-15). A predicate allowlist is a second hard schema gate.
3. **Sharing DEGREE, never the edge list** (SIG-INGEST-043c): the connector writes
   `sharing_partner_degree` (how many partners an agency had) tagged
   `degree_only_no_edge_list`, never a specific edge — the 463 source-document
   links resolve to a host that blocks automated access, and rendering degree as a
   network would be the unexplained edge the defining standard forbids.
4. **Per-column retention windows preserved in incommensurable units**
   (SIG-INGEST-043d): each vendor's retention window is kept with its own unit and
   window definition and never normalized together — direct, dated evidence for
   the incommensurable-counts problem (§29.1).
5. **Agency crosswalk through the P03.2 cascade** (SIG-INGEST-043c/§14.6): `link()`
   resolves each agency aggregate against known SIG identities via
   `resolution.cascade.resolve` and **labels a match with its cascade tier**
   (defining standard §3.1). The connector emits candidate identifiers and never
   mints identity itself (SIG-INGEST-034).
6. **Records-request linkage** (SIG-INGEST-044): where a release documents the
   public-records request that produced an agency's data, the aggregate is linked
   back to the `connectors.records.RecordsRequest` it derives from — the release is
   the *result* of a MuckRock request. (MuckRock is the co-publisher of the joint
   EFF/MuckRock release; it is **not** registered as a distinct source row here —
   the existing `muckrock` row is the live records-API channel, a different thing —
   so no new registry row is added.)
7. **The coarse-international REFERENCE-capture path** keeps LINK posture: the
   `coarse_international` connector routes every row through `coarse_claim`, so the
   anti-disaggregation guard cannot be bypassed. The three datasets stay LINK /
   `ingestion_permitted=false`; a live run is refused at the loader gate until a
   packet + flip changes a row, at which point the existing extractor runs through
   `run --mode live` unchanged. Over fixtures it runs replay/shadow with no network.

## Consequences

- Data Driven is ingestible the moment a reviewer flips `eff_data_driven` (now a
  MIRROR candidate, rights UNDETERMINED, packet produced); until then the loader
  gate refuses it (exit 3) and the connector is exercised over two committed
  release fixtures (v1, v2) that prove versioning.
- The aggregate-only guarantee is mechanical and tested, so a future upstream file
  carrying per-search detail is refused rather than silently ingested.
- Coarse-international ingestion is now one operator flip away, with the P4
  anti-disaggregation guarantee holding at the seam.
- The Data Driven baseline (structural, historical) is available to the
  vendor-replacement analysis (§29.4) that a Flock-only graph would mis-model.

## Revisit trigger

Revisit when **HG-03 clears** for any of these sources: an operator flips
`eff_data_driven` (or one of the coarse trio) to `ingestion_permitted=true` with
recorded review metadata after deciding its rights packet. At that point the first
**live** `sig-connectors run --mode live` fetch runs (writing a content-free fetch
record under `docs/build/live_runs/`), and this ADR's assumptions — the release
digest/version model, the aggregate-only guard against a real upstream file, the
degree-only sharing posture, and the coarse anti-disaggregation guard — must be
re-checked against the live response. Also revisit if a Data Driven re-release changes
the column schema (a new digest + a shadow diff surfaces it, RISK-P21-14) or if MuckRock
begins hosting the release under a distinct, separately-licensed channel worth a
dedicated registry row.
