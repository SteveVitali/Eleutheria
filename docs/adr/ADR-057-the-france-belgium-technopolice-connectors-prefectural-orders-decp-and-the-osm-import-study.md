# ADR-057: The France/Belgium (Technopolice) connectors — prefectural orders → LegalInstrument, DECP → Contract, and the OSM import study

- **Status:** Accepted
- **Date:** 2026-09-08
- **Phase:** P18.2
- **Requirement ids:** SIG-CHART-029, SIG-ONTO-068, SIG-ONTO-032, SIG-CONTRIB-016;
  realising §11.14 `LegalInstrument`, §13.8 acquisition-method (`fr.cada`,
  `no_equivalent_available`), and §23.5/§23.6 connector obligations
- **Spec:** docs/2_canonical_design_spec.md §5.3 (international scope — the France/Belgium
  stress-test), §11.14 `LegalInstrument`, §13.8 (internationalised acquisition method),
  §23.5 `records`/§23.6 `procurement`, §35.2 (contribution back to OSM — the import study),
  §52 Phase 18; R9 (French/Belgian evidence base, F9.6–F9.18/F9.31/F9.41/F9.42)
- **Relates to:** ADR-056 (the P18.1 jurisdiction adapter framework this consumes — the
  first non-US adapter is exercised here), ADR-055 (no direct automated OSM writes / the
  human-mediated suggestion workflow the import study is a precondition of), the
  `records`/`procurement` US connectors (P07.2/P07.3) whose runtime shapes are reused where
  country-neutral and deliberately *not* reused where US-shaped

## Context

P18.1 opened the jurisdiction adapter framework; P18.2 is its **first consumer** and its
stress-test. The France/Belgium (Technopolice) evidence base is structurally different from
the US in exactly the ways that break a US-shaped model (§5.3): authorization is carried by
**published prefectural orders** (arrêtés préfectoraux), not contracts, and procurement by a
**single national open-data dataset** (DECP), not thousands of municipal systems. Both must
map onto the existing entities — a `LegalInstrument` and a `Contract` — or the failure to map
is a §5.3 defect to be found here, not in production. Separately, the already-executed
~12,000-camera OSM import is the concrete activist-database → common-substrate path SIG's
federation thesis depends on, and SIG-CONTRIB-016 makes **studying it a precondition** of any
SIG-originated contribution at scale.

## Decision

1. **A new `connectors.france_belgium` module with two registered connectors, deliberately
   not reusing the US connectors' US-shaped machinery (§5.3, SIG-ONTO-068).** The `records`
   connector's MuckRock/`foia_request` vocabulary and the `procurement` connector's
   USAspending/cooperative-US-vehicle vocabulary are precisely the US-shaped assumptions the
   international model prohibits, so `france_belgium_records` and `france_belgium_procurement`
   are new adapters that reach for **no `us.*` term**. Country-neutral runtime shapes *are*
   reused: the procurement connector builds the same `connectors.procurement.Contract`, which
   is the point — national open-data procurement maps onto the *existing* Contract without loss.

2. **The `LegalInstrument` runtime shape (§11.14); P18.2 is its first consumer.** A published
   arrêté préfectoral parses into a `LegalInstrument` whose `instrument_type` is
   `fr.arrete_prefectoral` — a national child of the abstract `prefectoral_order` parent
   (SIG-ONTO-068). `abstract_instrument_type` rolls the national child up to the shared parent,
   so "authorization by prefectural order maps onto `instrument_type=prefectoral_order`" (AC2)
   is a queryable property, not a coincidence. The five-year renewable validity (Code de la
   sécurité intérieure L252, F9.18) is derived to a `sunset_date` and flagged as derived, so the
   §12 renewal-watch task can fire.

3. **The internationalised records-request vocabulary at the seam (§13.8, SIG-ONTO-068).** The
   records connector emits the `AcquisitionMethod` regime for the jurisdiction — `fr.cada` for
   France (Ma Dada / CADA), `no_equivalent_available` for Belgium (whose national camera
   register sits behind a Belgian-eID wall and is not public — a *known-complete-unknown*,
   F9.31). `assert_not_us_records_method` refuses `foia_request` / `us.foia` /
   `us.state_public_records` outright: "the non-US records-request vocabulary is used, including
   `no_equivalent_available`, not `foia_request`" (AC1) is enforced, not documented.

4. **DECP → Contract, with the framework-agreement piggyback invariant (§23.6, SIG-ONTO-032).**
   `contract_from_decp` maps a DECP record 1:1 onto `Contract` (F9.16: `acheteur.id`→buyer,
   `titulaires[].titulaire.id`→seller, `montant`→amount EUR, `dateNotification`→signed date;
   `end_date` left *derivable-not-stored* from `dureeMois`). A marché riding an `idAccordCadre`
   (accord-cadre / framework agreement) is a piggyback on a master award and MUST set
   `parent_cooperative_contract` — the same SIG-ONTO-032 invariant the US cooperative-vehicle
   case turns on, reached here through French open data with no US vocabulary; the `Contract`
   dataclass's own `__post_init__` enforces it.

5. **Belgium onboarded under the `be.*` national namespace (§13.7, SIG-ONTO-068).** New
   `be.*` children under shared abstract parents — `JurisdictionType` (`be.region`,
   `be.province`, `be.commune`, `be.police_zone`), `OrganizationType` (`be.police_locale`,
   `be.police_federale`), `LegalInstrumentType` (`be.loi_cameras`) — plus the missing France
   org types the evidence names (`fr.police_nationale`, `fr.douanes`, `fr.prefecture`, F9.41).
   A `BE` adapter row and a `BE-GDPR` (redact-by-default) publication row are added; **no `us.*`
   enum is widened** (the frozen us.* baseline is asserted by test).

6. **The OSM import study as a testable precondition (§35.2, SIG-CONTRIB-016).** The
   sous-surveillance.net → OSM import is studied in prose
   (`docs/studies/osm-sous-surveillance-import.md`) and as data
   (`connectors/data/osm_import_study.toml`): its field crosswalk + distance-banded conflation
   conventions (F9.12), its consultation timeline and the one-line-email licensing anti-pattern
   it must not repeat (F9.6/F9.8), its measured outcome (F9.6/F9.7/F9.10), and the corrections
   to the outline's number (~12,000 → ~18,000 imported / ~20,000 source; ~12,000 is the France
   subset) and actor attribution (OSM Belgium / `User:Vucod`, not Technopolice). A gate,
   `assert_import_studied_before_scaled_contribution`, refuses a SIG-originated contribution *at
   scale* until conventions, consultation, and outcome are all documented.

## Consequences

- The France/Belgium adapter is exercised end-to-end at the connector level: prefectural order
  → `LegalInstrument`, records regime → `fr.cada`/`no_equivalent_available`, DECP → `Contract`.
  The §5.3 stress-test passes — both authorization and procurement map onto existing entities.
- The "not `foia_request`" and "no widened `us.*` enum" properties are *tests*, not hopes.
- SIG reconciles against OSM via the `ref:sous-surveillance_net` join key rather than
  re-importing the activist database; a bulk contribution stays gated on the studied precedent.

## Deviations

- **The records connector's Belgian branch models `no_equivalent_available` as an
  `acquisition_method` claim with a `known_complete_unknown` flag, not a `db.absence` state.**
  The Belgian register *exists* but is inaccessible — that is neither `NO_EVIDENCE_FOUND` nor
  `EVIDENCE_OF_ABSENCE`; representing it as an absence state would misuse the §9.5 model. The
  flag records the known-complete-unknown faithfully without overloading the coverage vocabulary.
- **`end_date` is left unset for DECP contracts** (derivable from `dureeMois`, not stored, F9.16);
  the DECP `modifications[]` amendment history is preserved in `raw` rather than forced into a
  lifecycle state the `ProcurementState` vocabulary does not carry (there is no "amended" state).
  Modelling amendments as first-class dated sub-events is an additive extension a later ticket
  can make; it is not fabricated here.
- **The procurement connector reuses the country-neutral `Contract` shape**, so DECP parties keep
  the `procurement` connector's `procurement.org_name` candidate-identifier scheme rather than a
  France-specific `fr.siret` scheme. This is deliberate: the AC is that national procurement maps
  onto the *existing* Contract, and the SIRET rides through as the candidate value — still a
  candidate, never a resolution (SIG-INGEST-034).
- **`fr.gendarmerie` (seeded by P18.1) is kept; no duplicate `fr.gendarmerie_nationale` is added**
  (back-compat: prior wire names are not broken, SIG-ENG-003).
- **The connectors interpret documented DECP/RAA record shapes; live fetch/PDF segmentation is
  downstream.** The three France/Belgium sources (`raa_prefectures`, `madada`,
  `declarationcamera_be`) are registered but `ingestion_permitted = false` pending rights review,
  and arrêté-PDF text extraction is P07.1's parser, only *called* here.

## Revisit trigger

Revisit when a France/Belgium source's rights review flips `ingestion_permitted` (enabling a live
run), when the DECP amendment history warrants first-class dated sub-events, or when a
SIG-originated OSM contribution at scale is actually proposed (which must satisfy the full
SIG-CONTRIB-016c requirements and the P16.2 human-mediated workflow, beyond this study gate).
Adding a `us.*` vocabulary value or relaxing the no-US-records-method / import-study gates is a
spec amendment (SIG-ENG-003), not an edit here.
