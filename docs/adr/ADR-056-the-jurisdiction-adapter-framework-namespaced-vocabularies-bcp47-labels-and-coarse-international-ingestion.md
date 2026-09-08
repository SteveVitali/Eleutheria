# ADR-056: The jurisdiction adapter framework — country-namespaced vocabularies, BCP-47 labels, and coarse international ingestion

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P18.1
- **Requirement ids:** SIG-CHART-029, SIG-CHART-030, SIG-ONTO-068, SIG-ONTO-069,
  SIG-PUB-017, SIG-ENG-036, SIG-INGEST-042; realising §11.1 `Jurisdiction`, §11.2
  `Organization`, §11.14 `LegalInstrument`
- **Spec:** docs/2_canonical_design_spec.md §5.3 (international scope), §13.7–13.8
  (internationalisation of vocabularies + the internationalised acquisition method),
  §43.8 (jurisdiction-conditional publication), §52 Phase 18; R9 Part I (the 18-item
  jurisdiction-adapter checklist)
- **Relates to:** ADR-007 (LinkML as the single ontology source — the enum edits are
  made in the LinkML source and regenerated), ADR-008 (SKOS for published vocabularies —
  the namespace hierarchy is published as `skos:broader`), ADR-046 (policy legal
  instruments — the `LegalInstrument` this namespaces), the publication policy of
  P13.2/§43 (the jurisdiction-conditional rule this generalises)

## Context

P18.1 **owns the jurisdiction adapter framework** that P18.2 (France/Belgium) is the
first consumer of. The data model must be international from the beginning
(SIG-CHART-029) and a US-shaped enum is prohibited (SIG-CHART-030, §5.3). Prior tickets
had laid pieces — a first-class `Jurisdiction`, a partly-namespaced `AcquisitionMethod`,
`name_lang`, and the jurisdiction-conditional `publication_permitted` — but there was no
reusable *adapter* a new country plugs into, no machine-checked "no US-shaped assumption"
gate, the `LegalInstrumentType` enum was flat, there was no `transliteration_scheme`, and
the coarse country-/vendor-level international datasets (§22.7) were neither registered nor
guarded against agency-level disaggregation.

## Decision

1. **Country-namespaced vocabularies with a shared abstract parent, expressed via LinkML
   `is_a` (SIG-ONTO-068).** The four internationalised enums — `OrganizationType`,
   `JurisdictionType`, `LegalInstrumentType`, `AcquisitionMethod` — carry a country-neutral
   **abstract parent** (dotless) and national `<cc>.*` children linked to it by LinkML
   permissible-value `is_a`. P18.1 adds **non-US** children (`fr.*`, `uk.*`, `de.*`,
   `eu.*`) and links the existing law-enforcement and records-request terms to their
   abstract parent; **no `us.*` value is added** (a frozen us.* baseline is asserted by
   test). The SKOS structural generator publishes `is_a` as `skos:broader`, so the
   abstract-parent hierarchy (e.g. `us.le.*` **and** `fr.police_municipale` both `broader`
   than `law_enforcement`) is queryable and cross-country rollups work.

2. **A `transliteration_scheme` qualifier for multilingual labels (SIG-ONTO-069).**
   `Jurisdiction` and `Organization` — the label-bearing entities the spec names — carry
   repeatable `name_lang` (BCP-47) and a new repeatable `transliteration_scheme` qualifier,
   so a romanised/transliterated name records the scheme it was produced under and the
   original script stays recoverable.

3. **A data-driven jurisdiction adapter framework in `policy/` (SIG-CHART-029/030).**
   `policy.jurisdiction` defines `JurisdictionAdapter` (jurisdiction levels + code systems,
   namespaced org/legal-instrument types, records-request vocabulary, default languages,
   publication profile, local partner), a machine-checked checklist
   (`adapter_checklist` / `validate_adapter`), and a hard `assert_no_us_shaped_assumption`
   gate that rejects any non-US adapter reaching for a `us.*` (or other-namespace) term.
   The adapters are **data** (`policy/data/jurisdiction_adapters.toml`: US, FR, UK), and
   `sig-policy jurisdiction` validates them all. Publication stays jurisdiction-conditional:
   `adapter_publication_permitted` binds the data subject's jurisdiction to the adapter and
   still requires both it and the record's origin to permit publication (SIG-PUB-017), so the
   FR-GDPR-redacts / US-publishes contrast falls out of the adapter set, not a global rule.

4. **Coarse international ingestion with an anti-disaggregation guard (SIG-ENG-036 /
   SIG-INGEST-042).** `connectors.coarse_international` stamps every claim from a
   country-/vendor-level dataset with its **explicit coarse granularity** and refuses, via
   `assert_not_disaggregated`, any attempt to attach it to an agency/deployment/device — the
   disaggregation-by-inference §5.3 forbids (P4). The three named datasets (Carnegie AI
   Global Surveillance Index, Facial Recognition World Map, ASPI Mapping China's Tech Giants)
   are registered LINK-posture / `ingestion_permitted = false` (§22.7).

## Consequences

- Onboarding a non-US jurisdiction is a data row plus a fixture; the "no US-shaped
  assumption" property is a *test*, not a hope. A `us.*` term in a non-US adapter, or a
  silently-widened us.* enum, fails CI.
- The vocabulary namespace hierarchy is real SKOS, so international rollups ("any
  law-enforcement organisation, in any country") are expressible.
- A coarse international index cannot be pinned to an agency by inference anywhere in the
  ingestion path without raising.

## Deviations

- **`LegalInstrumentType` / `JurisdictionType` were extended additively, not restructured.**
  Their pre-existing generic terms (`statute`, `municipality`, …) are kept as the shared
  abstract parents; national children are added under them. Pre-existing `us.gov.*` and the
  sector `private.*` values are left untouched (back-compat: prior wire names/IDs are not
  broken, SIG-ENG-003). The abstract-parent + no-widening rules are asserted for the
  country-namespaced children, which is the SIG-ONTO-068 obligation.
- **The adapter gates the checklist items expressible from vocabulary + publication data
  now; the per-source ingestion items** (boundary sources, procurement portals, official
  gazette, DPA corpora — R9 Part I items 2/4/5/8/13/14/16) are recorded in
  `CHECKLIST_ITEMS` as owned by each country's connector work (P18.2+), not asserted here.
- **The coarse-international layer is the claim shape + guard, not a live connector** — the
  three datasets are `ingestion_permitted = false` pending rights review (§22.7), so live
  fetch is downstream.
- **Multilingual labels reuse the spec's parallel-slot shape rather than a structured
  language-tagged object.** `name`/`name_lang`/`transliteration_scheme` are repeatable slots
  paired positionally (`name[i]` is tagged by `name_lang[i]`), matching the §11.1/§11.2
  predicate tables exactly; `Organization.canonical_name` stays a single-valued claim
  ("a claim, not a column", SIG-ONTO-003), with multilingual organisation names carried as
  repeatable `alias` + `name_lang`. Restructuring these into a nested object is a P01.1-owned
  schema change with API/export/dossier blast radius and is not made here; the positional
  pairing is documented on the slots and asserted by the round-trip test. `transliteration_scheme`
  is added to the two entities the spec's label tables name (`Jurisdiction`, `Organization`);
  extending it to other label-bearing terms is additive when a later ticket needs it.

## Revisit trigger

Revisit when P18.2 lands the first live France/Belgium connectors (which will exercise the
adapter end-to-end: ingest → reconcile → serve for one municipality), when a coarse dataset's
rights review flips `ingestion_permitted`, or if a new country needs a checklist item the
framework does not yet gate. Adding a `us.*` vocabulary value, changing the no-US-shaped-
assumption gate, or relaxing the anti-disaggregation guard is a spec amendment (SIG-ENG-003),
not an edit here.
