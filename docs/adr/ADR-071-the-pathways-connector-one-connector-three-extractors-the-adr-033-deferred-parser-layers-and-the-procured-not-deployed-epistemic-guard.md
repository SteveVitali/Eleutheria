# ADR-071 — The `pathways` connector: one connector + three extractors, the ADR-033-deferred parser layers, and the procured≠deployed epistemic guard

- **Status:** Accepted
- **Phase / ticket:** P21.9 — Stage-5 connectors for the Phase-17 pathways (federation/RTCC, FR/CSS/forensics, acoustic/drone/location) + the deferred parser layers
- **Date:** 2026
- **Related / amends:** ADR-033 (**realises** the deferred concrete layer-3/4 engines, LD-F17), ADR-026 (the eight-stage connector contract), ADR-063/ADR-065 (registry review metadata + the gated `run --mode live|replay|shadow`), ADR-070 (the sibling coarse-international / Data Driven capture paths, HG-03 posture); LD-H12, LD-V10, LD-F17; RISK-P17-02/03/08/09/13/14, RISK-P21-16/17; SIG-INGEST-046b/046c/049a–d, the P17.x SIG-ONTO pathway ids, SIG-PARSE-001..008, SIG-INGEST-021/027/028/033/034.

## Gate status (copied from the run contract)

- **HG-03/HG-04 per source: SKIP — no source flipped.** The three pathway families ship
  over **committed fixtures** drawn from public documents already cited in the research
  cache (each fixture directory carries a `SOURCES.md` with per-document source URL +
  retrieval date). Rights packets are produced for each new source
  (`docs/build/rights/pathways_*.md`); the `sources.toml` rows stay rights `UNDETERMINED`
  / `ingestion_permitted = false`, so a `run --mode live` for them **REFUSES (exit 3)**.
  No live fetch this run. Per-source HG-03/HG-04 recorded **pending** → RETURN PASS.

## Context

Phase 17 *proved* the frozen ontology can express the broader-surveillance pathways as
conformance-suite instance graphs — "expressibility, not ingestion" (RISK-P17-03, LD-V10):
private-camera federation / RTCC integration / the commercial data-broker chain (P17.1),
facial recognition / cell-site simulators / mobile-device forensics (P17.2), and gunshot
detection / drones / commercial location data (P17.3). P21.9 does the ingestion half —
connectors that read public procurement, policy, federation, and deployment documents and
emit the **same** pathway claims as dated, evidenced claim-spine rows (LD-H12).

Two design questions had to be settled.

**One connector or three?** The three pathway families reuse the same parser layers, the
same claim-shaping, and — decisively — the same epistemic guard. Three connectors would
triplicate the eight-stage framework boilerplate around near-identical code.

**Which of the ADR-033-deferred parser layers are actually needed?** ADR-033 froze the
seven-layer vocabulary but deferred the *concrete* layer-3/4/5 engines to "the connector
tickets that need them" (LD-F17: "which connectors implement which layer?"). The pathway
extractors need exactly two: **layer-4 table extraction** (a procurement contract lays
vendor/product/amount out as a table) and a **layer-3 clause locator** (an agency policy or
court order is prose organised into numbered clauses).

## Decision

1. **One `pathways` connector, three per-family extractors** (`connectors/src/connectors/
   pathways.py`). `extract` dispatches on the fixture's `pathway_family`
   (`rtcc_federation` / `fr_css_forensics` / `acoustic_drone_location`) to a per-family
   set of documents; each document's `kind` (`procurement_table` / `policy_clauses` /
   `assertions`) selects a parser-layer extractor. The connector self-registers
   (`sig-connectors list-connectors` includes `pathways`), keyed to three LINK-posture
   registry sources (one per family) in `runner.CONNECTOR_FOR_SOURCE`.

2. **The ADR-033-deferred concrete engines land in `parsing/`** (LD-F17), dependency-light
   and deterministic exactly as ADR-033's classification is (no third-party PDF/OCR
   library in the frozen §47 layout):
   - `parsing.tables` — the **layer-4 `pdf_table`** engine: parses a procurement table into
     addressable cells and emits `ParsedClaim`s with `CELL` locators (SIG-PARSE-003);
   - `parsing.clauses` — the **layer-3 `pdf_text`** engine: splits a policy document into
     numbered clauses, each addressed by a `BYTE_RANGE` locator;
   - `parsing.genre` — **document-genre classification** (procurement / policy / deployment
     / vendor / agenda), the axis distinct from file format. `sig-parsing classify` now
     reports the genre alongside the format verdict and cheapest sufficient layer.

3. **The epistemic guard: `procured` NEVER implies `deployed` (RISK-P21-16, §46).** A
   `deployment` claim may be asserted only from a **deployment-genre** document
   (`parsing.genre.DEPLOYMENT_GENRES = {deployment_report}`). Two guards enforce it and
   both run inside `pathway_claim` so they cannot be bypassed:
   - a **genre-level** guard (`assert_claim_type_supported_by_genre`) — a `deployment` claim
     from a non-deployment-genre document raises `DeploymentInferenceError`;
   - a **predicate-level** guard (`assert_deployment_predicate_has_deployment_type`) — the
     deployment predicates (`deployed` / `actually_provides_capability` / `in_operation`)
     may ride only on a `deployment` claim.
   The genre is **re-derived from the document text**, never trusted from a fixture label,
   so a procurement document cannot be relabelled to unlock a deployment claim.

4. **Every claim is typed, evidenced, and dated** (§3.1): a `claim_type` ∈ {`vendor_product`,
   `procurement`, `policy`, `deployment`}, the parser-layer locator + `extraction_method` +
   source URL + retrieval date, and an `observed_at`. A predicate allowlist (SIG-INGEST-033)
   is the D6 admissibility filter at ingest.

5. **Coverage is a test** (`tests/connectors/test_pathway_coverage.py`): every P17
   conformance-suite pathway (the nine `test_stage5_*.py` graphs) has ≥1 connector-produced
   claim, rendered into `docs/build/STAGE5_CONNECTORS.md`. This is the mechanical retirement
   of RISK-P17-03 (marked `→ retired by P21.9`).

6. **Sources stay gated** (HG-03): three LINK-posture rows, rights `UNDETERMINED`,
   `ingestion_permitted = false`; `run --mode live` refuses (exit 3); `replay`/`shadow` run
   over committed fixtures with 0 diffs (SIG-INGEST-018/019).

## Consequences

- Populating the P17 pathways required **no schema change** (the conformance suite already
  proved this); the connector emits instances of the frozen classes.
- The genre axis is now a first-class, reusable parser concept any future document connector
  can key an epistemic decision off — not a bespoke `pathways` hack.
- RISK-P21-17: the parser layers could regress on real PDFs; committed fixtures + `shadow`
  diffs defend against it (the SIG-PARSE-007 posture), and the heavy real-PDF engines remain
  deferred behind the same layer vocabulary.
- No live population happens until an operator flips a source with a rights packet (HG-03);
  the live path is built and gated, not exercised.

## Revisit trigger

Revisit when **HG-03/HG-04 clears** for any pathway source — an operator flips
`pathways_rtcc_federation` / `pathways_fr_css_forensics` / `pathways_acoustic_drone_location`
to `ingestion_permitted = true` with a resolved rights packet and recorded review metadata,
so the gated live path runs for real and writes fetch records + claims to PG. Also revisit if
a **heavy real-PDF/OCR engine** is adopted behind the layer-3/4 vocabulary (the deferred
concrete engines ADR-033 named), or if the genre roster needs a **new document genre** beyond
the five recognised here (e.g. a distinct court-docket or audit genre) — a new genre that
would unlock a stronger claim type must be added to `parsing.genre` and its
genre→claim-type gate deliberately, never inferred, so the procured≠deployed guarantee
(RISK-P21-16) stays intact.
