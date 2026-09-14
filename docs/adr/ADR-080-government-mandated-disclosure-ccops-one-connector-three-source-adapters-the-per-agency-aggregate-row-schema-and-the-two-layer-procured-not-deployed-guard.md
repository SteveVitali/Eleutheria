# ADR-080 — The `government_mandated_disclosure` connector (CCOPS): one connector, three paying source adapters; the per-agency aggregate-row schema; the two-layer `procured ≠ deployed` guard with the use-reporting-disclosure override (vs one connector per city, per-device rows, or a procurement-documents reuse)

- **Status:** Accepted
- **Phase / ticket:** P24.7 — CCOPS disclosure connector (CCOPS.1 / GL-CCOPS-01)
- **Date:** 2026-09-13
- **Related:** ADR-071 (the one-connector-three-extractors precedent this follows),
  ADR-074 (the Part VIII guard pattern this mirrors), ADR-033 (the deferred parser
  layers it drives), ADR-049 (licence compartments — UNDETERMINED fails closed),
  RISK-P21-16 (procured ≠ deployed, applied to this class), RISK-P0-08 (Part VIII),
  SIG-INGEST-049/-049a/-049b/-049c/-049d/-049e/-049f, SIG-INGEST-050, SIG-INGEST-033,
  HG-03/HG-04 (operator gates — nothing flipped, nothing fetched),
  `docs/tickets/DEFERRALS.md` D-CCOPS.1-1/-2; the defining standard (§3.1: no fact
  asserted the evidence does not support).

## Context

P24.7 closes the gap P17-FLIP-01 recorded honestly: P21.9 delivered the P17
*pathway* connectors, but `SIG-INGEST-049*` is a different source class —
**municipal surveillance-ordinance (CCOPS) disclosures** — that P21.9 correctly
left PARTIAL. The spec requirements are exact:

- **049** — register `government_mandated_disclosure` as its own source class,
  distinct from `civil_society_dataset` and `vendor_portal`: licence public
  record, format pdf, extraction document_pipeline.
- **049a** — scope it *depth, not breadth*, with the honest numbers carried: ~26
  jurisdictions ≈ 5% of the US population, ~0.14% of US law-enforcement agencies;
  zero publish machine-readable output; the canonical national list is a JPEG on
  the ACLU page (revised 2024-11).
- **049b** — the per-technology dossier fields no other source supplies.
- **049c** — implement the three connectors that "pay for themselves": the city
  with quarterly reporting + richest per-technology detail (Seattle), the city
  publishing 42 policies on a stable URL pattern (NYC POST Act), and the city
  with a biannual citywide inventory carrying a compliance metric (SF).
- **049d** — its highest use is calibration, not coverage.
- **049e** — a disclosure reporting use *without* the required policy is a
  first-class non-compliance finding.
- **049f / 050** — the one national state-ALPR-statute inventory seeded and
  labelled with its frozen date; future-due mandated sources registered now
  with their commencement date.

The research (F3.19–F3.27) adds the shape constraints: every CCOPS output is a
PDF document (never an API); the SIR is a *pre-acquisition commitment* document;
mandated fields may sit blank (Seattle's Fiscal 1.1/1.2); procurement or
authorization never proves deployment; and some regimes report non-compliance
outright (SF: 26% in use without an approved policy).

## Decision

**1. One connector class, three paying source adapters — not one connector per city.**
`connectors.government_mandated_disclosure` is a single registered connector
whose `extract` dispatches on the document `kind` to three per-source
extractors — `field_questionnaire` (Seattle's fixed ~50-field SIR),
`policy_clauses` (NYC POST's clause-located impact & use policies, layer-3
`pdf_text`), `inventory_table` (SF's appendix rows + compliance metric). This is
the ADR-071 reasoning applied to the class: all three share the claim-shaping,
the aggregate schema gate, and the epistemic guard, so the differences live in
the extractor dispatch, not in three parallel connectors. A fourth paying
source is a new extractor kind, not a new connector — the same shape the
remaining ~23 jurisdictions and the legislative-platform scrapers will take.

**2. The emitted row is a per-agency AGGREGATE row — schema-enforced, Part VIII.**
Every claim is keyed `ccops:<jurisdiction>:<agency>` and must carry `agency` +
`reporting_period` (+ `technology` for every non-`ordinance` claim) plus the
stamped `aggregate_level = agency_technology_period` — the disclosure's own
granularity. `assert_aggregate_row` is the mechanical gate: missing aggregate
fields, a forbidden column (plate / person / per-search / per-incident /
officer / device-serial), or a forbidden token in the predicate or raw value
fails closed (`NonAggregateRow` / `PartVIIIViolation`). Person-naming predicates
are refused outright (§43.4 default). Per-device, per-incident, per-search and
per-person CCOPS rows are never emitted — the disclosures' depth is
institutional (fields, statuses, counts), which is exactly the granularity Part
VIII permits.

**3. `procured ≠ deployed` is a two-layer guard with one honest override.**
A disclosure *authorizing* or *procuring* a system is not evidence it is
deployed (RISK-P21-16 applied to this class):

- **Predicate level** — the use predicates (`in_use`, `usage_count`,
  `complaint_count`, `deployment_location`, `effectiveness_claim`) may ride only
  on a `disclosure_use` claim (`assert_use_predicate_has_use_claim`).
- **Document level** — `disclosure_use`/`compliance_finding` claims are
  admissible only where the disclosure *itself reports actual use*: a
  `deployment_report`-genre document unconditionally, or a mandated disclosure
  carrying `reports_actual_use` (e.g. SF's biannual inventory, whose own rows
  mark technologies "in use without an approved policy" — the legally compelled
  statement of use, not an inference). A `procurement_record` or
  `vendor_disclosure` genre can NEVER report use, however labelled
  (`never_use_genres`). The genre is re-derived from the document text
  (`parsing.genre.classify_genre`), never trusted from a fixture label — a
  mislabelled procurement document cannot unlock the use surface.

The `reports_actual_use` override is the honest addition over the pathways
model: a real CCOPS inventory is genre-classified `policy_document` (it is full
of policy language) yet its own row statuses *assert* use. The flag records
that document-level fact; it cannot rescue a procurement or vendor genre, and
it is still row-level — an `approved` / `seeking_procurement_or_pilot` status in
the same document yields only an `inventory_entry` claim.

**4. Mandated ≠ populated is a recorded distinction.** Field states are
`answered` / `present_but_empty` / `absent` (`field_state_of`): Seattle's blank
Fiscal 1.1/1.2 cost tables land as `disclosure_field_state` claims, never as
fabricated values.

**5. The class posture and scope are carried as data.** The vocab registers the
class (`licence: public record`, `format: pdf`, `extraction: document_pipeline`)
and the 049a scope numbers (`registry_row_cap: 26`) as data rows; the per-source
SPDX stays UNDETERMINED until a packet + operator flip (HG-03) — the export gate
fails closed. The three sources are `custody_posture=REFERENCE` +
`compact_status=public_terms_only` (statutorily published municipal records)
with rights packets recorded; `run --mode live` refuses (exit 3).

**6. 049f/050 land honestly within scope.** The NCSL inventory was already a
registered source row; the seed adds the committed statute asset
(`data/state_alpr_statute_seed.toml` — 16 states / 17 NCSL rows / 21 enactments,
`as_of: 2022-02-03`, `never_a_feed`) and a test pinning the label. The
future-due row (`future_statutory_disclosure_2027`, due 2027-04-01) already
carries its commencement date; a test pins the registration. Their spine
ingestion stays operator-gated like everything else (D-CCOPS.1-1).

**7. Sources stay unflipped; the live half is deferred.** No live fetch, no
source flip, `ingestion_permitted=false` — HG-03/HG-04 are operator gates. The
real fetches + flips + outreach land in `DEFERRALS.md` D-CCOPS.1-1/-2.

## Alternatives considered

- **One connector per city.** Rejected: three parallel connectors would triplicate
  the claim-shaping, aggregate gate, and epistemic guard; ADR-071 already settled
  the one-connector-many-extractors shape for exactly this situation.
- **Reuse the `okc_documents` procurement/policy connector.** Rejected: CCOPS is a
  different source class with different epistemics — its disclosures can report
  *use* (the override above), which the OKC document connectors deliberately
  never assert; reusing them would either weaken their guard or mislabel the class.
- **Per-device or per-incident rows.** Forbidden — Part VIII §0.7/§43.2. The
  aggregate-row schema is the design's point: the disclosures' value is
  institutional depth, not granularity.
- **Treat every inventory status as deployment.** Rejected: `approved` /
  `seeking_procurement` / `draft` statuses are authorization, not use — only
  `in_use_statuses` yield use claims.
- **Leave 049f/050 PARTIAL as out-of-scope.** Considered; rejected because the
  honest artifacts were small and real (the registered rows + the labelled seed
  asset + tests) — claiming them MET is evidence-backed, not fabricated.

## Consequences

- `SIG-INGEST-049*` (049, 049a–049f) + `SIG-INGEST-050` move PARTIAL → MET with
  deterministic test evidence; OPEN FINDING P17-FLIP-01 is retired with that
  evidence.
- The connector emits typed, evidenced, per-agency aggregate claims only; the
  genre+predicate+aggregate guards cannot be bypassed by a future extractor
  (all three run inside `disclosure_claim`, and the emitted set is swept again
  at `normalize`).
- The class is honestly bounded: ≤ 26 jurisdictions, zero machine-readable
  outputs, calibration not coverage — the scope row is data a test pins.
- HG-03/HG-04 work (flips, real fetches, outreach) is recorded, not performed.

## Revisit trigger

Revisit if (a) a CCOPS jurisdiction ships a machine-readable inventory (the
`machine_readable_outputs = 0` scope fact and the document-pipeline assumption
change), (b) a fourth paying source or the legislative-platform scrapers land —
the extractor dispatch then decides whether the class generalizes or splits,
(c) a jurisdiction's mandated disclosure begins publishing person-level or
per-incident rows (the aggregate gate's vocabulary may need to grow), or
(d) the `reports_actual_use` override proves too permissive in live review —
the honest fallback is to admit use claims only from `deployment_report`-genre
documents and record the inventory's use assertions as `disclosure` facts.
