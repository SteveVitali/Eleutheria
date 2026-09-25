# ADR-112 — Partner organisations as entity-ref claims: one identifier scheme, the ambiguity rule, and never a person

- **Status:** Accepted
- **Phase / ticket:** Phase 31 / P31.5 (`docs/tickets/P31.5__entity-ref-claims-procurement.md`) — Round 9 `DEEPEN.1`. This is the design's placeholder `ADR-R9-ENTITYREF`; the ticket owns the partner org-identity decision (scheme, normalization, the never-a-person rule).
- **Date:** 2026-09-25
- **Related:** §3.1 (the defining standard), §11.2 (Organization), §11.11/§11.12 (Contract, FundingInstrument), §11.17/§11.18 (AccountabilityEvent, LegalProceeding), §14 (identity: SIG-IDENT-012/022, the crosswalk), §16 (the append-only spine), Part VIII (no person data), ADR-005 (append-only), ADR-099 (materialize at scale), ADR-104 (the registry pattern, the `connector_run` directness rule), ADR-110 (the identity guard and the object seam — Decision 6(b), revisit trigger (d)). Deferrals **D-P30.2-2** (advanced; the hosted half is P31.6), **D-P30.2a-1** (the procurement + accountability family registered; the rest is P31.8), **D-P31.5-1** and **D-P31.5-2** (opened here); backlog home **BL-057**.

## Context

- **0 of 2,304,784 hosted claims carry `object_entity`.** Procurement parties land as text (`buyer` 14,582,
  `seller` 5,101, `recipient` 2,895, `funder` 947 claims; `reports/p30.2a-hosted/predicate_inventory_before.json`)
  with a `procurement.org_name` candidate identifier nobody resolves. So the P28.2 edge and P28.6 accountability
  materializers have no input (P30.2 wrote 0 edges and 0 links, honestly).
- **The object seam exists but nothing uses it** (ADR-110 Decision 6(b)): `PgClaimSink(object_resolver=…)`
  resolves an `EntityRef` through the identity guard and writes `object_type='entity_ref'`. The guard refuses any
  scheme outside `GUARDED_SCHEMES`, and ADR-110 revisit trigger (d) requires a new guarded scheme to ship with the
  backfill of its existing identifiers.
- **`content_digest` covers the claim record, not the resolver's output.** Resolving the existing text record
  would either dedupe to +0 (already on the spine) or store the text record as an `entity_ref` claim, which would
  change the "text claims unchanged" contract.
- **The connector inventory, re-confirmed** (the ticket names `buyer`/`seller`/`recipient`/`funder`/`applies_to`/
  `operator`): the procurement connectors (Contract, FundingInstrument, SAM.gov, USAspending, TED, portal
  notices; France DECP through `Contract`) emit `buyer`/`seller`/`recipient`/`funder`; the accountability
  connector emits `event_organizations` (a list) and `proceeding_parties`. **No procurement or accountability
  path emits `applies_to` or `operator`.** The deployment → operating-organisation edge the P28.6 chain joins on
  is emitted by the camera registries as `camera_operator` (`dot_511`, the reviewed per-target publisher name)
  and by OSM as `operator_stated`.
- **The P28.6 assembler trusted `entity.entity_type`**, but the connector sink types every subject it mints with
  the placeholder `deployment` (`claim_sink._DEFAULT_ENTITY_TYPE`), including every contract, notice and
  accountability event on the hosted spine. With seller entity-refs present, its direct-vendor rule
  (`seller` on a `deployment`) would have made each procurement notice a "deployment" with a vendor — a
  procured ≠ deployed violation.

## Decision

1. **One identifier scheme per partner** (`resolution.partner_identity.partner_identity`). An external crosswalk
   id when the record carries one — `gleif.lei`, `us.sam.uei`, `dnb.duns`, `us.dla.cage`, `us.cgac.agency_code`,
   in that precedence — otherwise the normalized name under **`sig.org.name`**, the value being
   `normalize_org_name(name)` (SIG-IDENT-022, ruleset v1). Two records that normalize alike name the same entity;
   any merge beyond that is entity resolution (P28.1). **FIPS is not a partner scheme**: a place code is shared by
   every body in the place (the county and its sheriff), an attribute scheme like `us.state` (ADR-110). No
   emitter captures a crosswalk id today (USAspending requests no UEI field; a DECP party is a bare SIRET), so
   every partner minted today is `sig.org.name`; the crosswalk path is the documented upgrade.
2. **The ambiguity and never-a-person rules** (versioned data, `resolution/data/partner_identity.toml` v1),
   checked on the name even when a crosswalk id is present (sole traders hold UEIs and SIRETs too). In order: no
   alphabetic word (a bare id) → text only; several parties in one string (`/`, `;`, `|`, ` + `) → text only; an
   individual/sole-trader phrase (`dba`, `doing business as`, `sole proprietor`, `family trust`,
   `entrepreneur individuel`, …) → text only; an honorific, a personal suffix or a **common given name** (a
   reviewed list that omits names which are also common place names — San Jose, St. Paul, Will County) → text
   only; a **role or title word** (`sheriff`, `chief`, `detective`, `trooper`, `attorney`, …) with no
   institutional head noun (`office`, `department`, `board`, …) → text only (the officer-naming gate);
   **no distinguishing word** — every word generic or an organisation marker (`Police Department`,
   `Fire Department`, `Board of Education`, a bare `Department of Justice`) → text only, because the same words
   name a body in every jurisdiction; **an organisation marker** (a multi-letter legal form, a public-body or
   sector word, in English and the TED/DECP languages; the two-letter forms `SA`/`SE`/`AG`/`AS`/`AB`/`CO` are
   left out because they are also name syllables — `Kim Se-hoon`, `Jose Sa`) → an organisation; one bare word →
   text only; anything else (two or more words, no marker — `John A. Smith`, `JOHN Q CITIZEN`) → text only.
   Only a positive organisation signal mints. When in doubt the partner stays text: that is the Part VIII
   direction. (These rules were tightened after the independent self-review found `Sheriff John Smith`,
   `John Smith Consulting` and `Kim Se-hoon` minting under the first draft; each is now a pinned refusal.)
3. **The emitters** — the connectors' `link()` stage (the framework's identity seam) calls
   `resolution.partner_identity.partner_ref_rows`: after each accepted partner text claim it appends a
   **separate** record, a copy of the text claim (same subject, predicate, evidence locators, provenance) plus an
   `object_ref = {scheme, value, entity_type: "organization", label, basis, rules}`. A list value
   (`event_organizations`) yields one record per accepted party. The text claim is never touched, so its digest
   and every existing hosted claim are unchanged; the entity-ref record's digest differs by its `object_ref`
   (and the rules version it carries, so a rule change is a new claim, never a silent re-identification).
   Wired for: procurement + France procurement (`buyer`/`seller`/`recipient`/`funder`), accountability
   (`event_organizations`), `dot_511` (`camera_operator`). **Excluded:** `parent_cooperative_contract` /
   `amends_contract` (they name contracts), `proceeding_parties` (litigants are routinely natural persons), OSM
   `operator_stated` (the ODbL compartment and crowd free text — an ask-first boundary; a later ticket may add
   it with its compartment decision).
4. **The sink** (ADR-110's seam, not redesigned): `db.claim_sink.record_object_ref` is the production
   `object_resolver`, wired by `connectors.sinks.make_claim_sink('pg')` (a caller may still pass its own). It
   carries the record's `object_ref` into an `EntityRef` and **refuses a `person` object outright** (so does the
   sink for any resolver). `EntityRef` gains an optional `label` and `rules`. For each newly seen organisation object the
   sink writes one `organization` row — `organization_type='unclassified'` (the record names the party, not its
   class), `identity_basis` = the scheme, value and deciding rules version (SIG-IDENT-012), `cached_canonical_name` = the first label seen
   (so `_label_for` labels it; the sink is the deterministic resolver here), and
   `publication_review_required = true` for a name-only identity (SIG-ONTO-013: a body known only by name may be
   private) — `INSERT … ON CONFLICT DO NOTHING`, never a rewrite. The `vocab_predicate` placeholder stays
   `object_type='literal'` (the registry is the source of truth, as in ADR-104).
5. **The guard**: `db.identity_guard.PARTNER_ORG_SCHEMES` join `GUARDED_SCHEMES`, with the sqitch change
   `partner_org_identity_key` backfilling every existing identifier of those schemes to its earliest entity (0 rows
   on today's spines; the deploy fails closed if one stays unkeyed). A test pins the code set to the SQL lists.
6. **The registry** (the procurement half of D-P30.2a-1): 46 rows in `ontology/vocab/predicates.yaml` — the
   §11.11/§11.12 procurement surface, the notice surface (`notice_type`, `posted_date`, `response_deadline`,
   `title`, `description`, `place_of_performance`, `country`, `matched_keyword`, `content_term`, `document`) and
   the §11.17/§11.18 accountability surface — each with an `object_kind` (`entity_ref` for the six partner
   predicates, `literal` otherwise; `camera_operator` gains `entity_ref`) and, where the meaning is equal, a
   `maps_to` row whose volatility, strategy and legacy-genre directness it copies (`amount` → `contract_value`,
   `signed_date`/`start_date`/`end_date` → `contract_*`, `program_name` → `funding_program_name`,
   `lifecycle_transition` → `procurement_state`). `connector_run` directness follows ADR-104's rule: D3 for a
   record's descriptive facts, D1 for its own identifiers and own-text matches; `camera_registry` D6 (`instrument_type`,
   shared with the §11.14 legal instruments the France seed carries in `agency_policy`, reads D2 there). The
   `agenda_document`/`portal_document`/`bill_index` genres are not added (P31.8). SKOS carries
   `sig:objectKind` / `sig:mapsTo`.
7. **The readers.** The P28.6 assembler: `camera_operator` is an operator predicate and `event_organizations` /
   `event_deployments` are the event slots; a subject still typed with the connector placeholder `deployment` that
   carries a `buyer`/`seller` (contract), `recipient`/`funder` (funding instrument) or `event_*` (accountability
   event) claim is typed by the predicate's domain **and is never a deployment anchor**; `seller` leaves the
   direct-vendor set (it is a contract predicate — a vendor is reached through operator → buyer → seller). The
   export's `sharing_edges` read excludes the partner predicates, so a buyer never surfaces as an
   "unclassified" access edge. The P28.2 edge reader is unchanged: it reads the new claims and, correctly,
   classifies none as a §12.2 access edge (SIG-ONTO-042).

## Consequences

- **Fixture proof** (`tests/partner_fixtures.py`, committed partner fixtures + the TED/DECP/WSDOT fixtures): the
  records without an `object_ref` are exactly the base-commit records (golden digests computed at `34406ff`,
  shadow diff 0); 9 entity-ref claims are emitted; over a real PG18 spine the WSDOT contract buyer, USAspending
  recipient, both camera operators and the Atlas event resolve to ONE organisation; the P28.6 materializer writes
  8 links (procured_under_contract / has_vendor / funded_by / overseen_by, 2 each), anchored only on the two
  cameras, each citing entity-ref claims, re-run +0; a replay inserts +0; person-shaped and ambiguous parties
  mint nothing.
- Six Appendix C.4 sub-table columns now share a name with a registered predicate (`contract.acquisition_channel`
  / `parent_cooperative_contract` / `amends_contract`, `funding_instrument.instrument_type`,
  `legal_instrument.instrument_type`, `accountability_event.event_type`); they join the reviewed SIG-STORE-046
  allowlist (typed identity columns beside the evidence claims), as `records_request.external_id` did in ADR-104.
- **`publication_review_required` is written but no read surface honours it yet (D-P31.5-2).** The API labels an
  organisation from `cached_canonical_name`; before the hosted replay (P31.6) lands partner organisations on the
  served spine, the read surfaces must gate name-only organisations on the flag (or the flag must be decided
  moot for public bodies), and P31.16's republish must honour it.
- **Edges stay 0 here (D-P31.5-1).** No in-scope emitter produces an access-edge predicate, so the P28.2 edge
  materializer writes 0 rows from these claims — the honest result, not a gap papered over. The first edges come
  from the `configured_access_edge` claims P31.6 owns.
- **The hosted spine is untouched** (live_verification=false). P31.6 replays the affected sources on hosted.
  Note for P31.6: hosted subjects keep their placeholder `deployment` type forever (append-only), which is why the
  assembler types record subjects by predicate domain rather than by `entity_type`; and a `camera_operator`
  replay adds about one entity-ref claim per camera (≈ 230k on the hosted registries).
- **Recall costs, accepted:** single-word vendors (`Verkada`), two-letter legal forms (`Siemens AG`), companies
  named after a person (`Walt Disney Company`), a bare `Los Angeles County Sheriff`, bare federal agencies (`Department of Justice`),
  names whose letters `normalize_org_name` v1 does not transliterate (Polish `ł`: `Oddział`, `Spółka`), and DECP
  SIRET-only parties stay text. Homonyms across jurisdictions (`City of Springfield`) share one `sig.org.name`
  entity; a recorded `distinct` decision (P28.1) is the correction path.
- Dossiers list the entity-ref claim beside its text twin (same value). The resolver's §28 supersession within
  one source (Phase 1.4) keeps one of the two, so support is not double counted. For a list-valued predicate
  (`event_organizations`) the twins carry single parties, so value resolution picks one claim per source — the
  resolver's pre-existing single-value behaviour (it does not read `cardinality`); the entity-ref claims themselves
  are all kept and all feed the materializers.

## Alternatives considered

- **Resolve the text record itself** (the resolver returns an `EntityRef` for the existing record). Rejected: the
  digest does not cover the resolver output, so it dedupes +0 on the hosted spine or rewrites a text claim as an
  `entity_ref` (the ticket's digest caveat).
- **A crosswalk id or a jurisdiction-scoped name as the only identity.** Rejected: no emitter carries an id today
  (every partner would stay text), and scoping by jurisdiction yields different identifiers for the same body
  across sources (no join).
- **Type every subject correctly in the sink** (a subject-type hook). Not taken: the hosted subjects are already
  `deployment` and cannot be retyped append-only, so the reader must handle the placeholder anyway; a subject-type
  hook stays a later option.
- **Accept any name without a person marker.** Rejected: a two-word name with no organisation marker is exactly
  what a natural person's name looks like (Part VIII).
- **Emit `operator_stated` (OSM) as the operator edge.** Deferred: the ODbL compartment separation is an ask-first
  boundary.

## Revisit trigger

Revisit when any of: (a) an emitter starts capturing a crosswalk id (UEI/LEI/CAGE/agency code) — decide how a
crosswalk-keyed entity and the same body's `sig.org.name` entity are linked (a recorded `same_as`, P28.1);
(b) `normalize_org_name`'s ruleset or `partner_identity.toml` changes version — entity-ref claims carry the
rules version, so decide whether the re-emitted claims supersede the old ones; (c) a person-shaped name is found
minted as an organisation, or a measured recall check (P31.6's hosted counts) shows the rules refuse a large share
of real organisations; (d) P31.6 or a later ticket adds OSM `operator_stated`, SIRET names, or `proceeding_parties`
as partner sources; (e) the sink gains a subject-type hook, retiring the assembler's predicate-domain typing; (f) the read
surfaces start honouring `publication_review_required` (D-P31.5-2) — re-decide the flag's default for public bodies.
