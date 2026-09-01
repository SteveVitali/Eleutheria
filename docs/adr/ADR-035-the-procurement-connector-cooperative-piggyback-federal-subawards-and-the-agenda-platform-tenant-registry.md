# ADR-035: The `procurement` connector — cooperative-piggyback contracts, USAspending sub-award tracing, the `FundingInstrument` runtime shape, and the published agenda-platform tenant registry

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P07.3
- **Requirement ids:** SIG-ONTO-032, SIG-ONTO-033, SIG-INGEST-047, SIG-INGEST-033, SIG-INGEST-034, SIG-INGEST-036/037, SIG-METRIC-002a (wired ahead of P09.1, via `db.absence` / SIG-TIME-011), and the §23.6 `procurement` connector + §11.11 `Contract` / §11.12 `FundingInstrument` entity/predicate requirements
- **Spec:** docs/2_canonical_design_spec.md §23.6 (`procurement` — cooperative vehicles, USAspending, agenda platforms); §11.11 (`Contract`, SIG-ONTO-032); §11.12 (`FundingInstrument` **[NEW]**, SIG-ONTO-033); §22.3 (sources the outline does not name — the tenant registry SIG must build and publish); §23.1 (universal connector rules); §10.3.2 (the `artifact_type` vocabulary); §13.4 (the procurement lifecycle track); §9.5 (the absence/coverage model)

## Context

P07.3 adds the fourth source connector on the P04.1 framework — the **procurement
channel** (`procurement`: cooperative purchasing vehicles, USAspending, and agenda
platforms) — plus the runtime shapes of the §11.11 `Contract` and §11.12
`FundingInstrument` entities. Four things about this channel forced decisions:

1. **Cooperative purchasing is a dominant acquisition channel, and an agency riding
   a master award often files no local RFP at all (SIG-ONTO-032).** Sourcewell,
   OMNIA, NASPO ValuePoint, BuyBoard, TIPS, HGACBuy, Equalis, and GSA let an agency
   buy against someone else's competitively-awarded master contract. A model that
   assumes a local competitive procurement will conclude, wrongly, that *no
   procurement evidence exists* when it finds no local RFP.
2. **Purchaser ≠ operator ≠ funder (SIG-ONTO-033).** BIDs, HOAs, foundations, and
   federal grant programs routinely fund surveillance an agency operates — a pattern
   CCOPS ordinances (which regulate *agency acquisition*) miss. Federal grant → local
   surveillance is programmatically traceable through **USAspending sub-awards** (not
   only prime awards), which name LPR purchases by sheriffs under Byrne JAG and UASI
   and identify deployments that appear in no local procurement record.
3. **Agenda platforms are per-tenant APIs and no municipality→platform directory
   exists upstream (§22.3).** Legistar/PrimeGov/CivicClerk/CivicPlus are real APIs
   keyed by a tenant slug; "SIG should build one". This ticket **owns** that directory.
4. **The `artifact_type` vocabulary (§10.3.2) must additionally carry
   `state_auditor_survey`, `warrant`, and `procurement_aggregator_record`, and the
   paywalled procurement aggregator must be registered under a `LINK` custody
   posture (SIG-INGEST-047).**

The §11.11 `Contract` and §11.12 `FundingInstrument` classes, the `AcquisitionChannel`
and `FundingInstrumentType` enums, and the `ProcurementState` lifecycle track already
exist in the ontology (P01.1); the four-state absence model already exists as tested
code (`db.absence`, P02.3); and the cooperative-vehicle, USAspending, agenda-platform,
and paywalled-aggregator (`govspend`, LINK) source rows are already seeded (P00.4). So
this ticket owns the connector **runtime** shape, the tenant registry, and the
`artifact_type` vocabulary — not most new schema.

## Decision

1. **A `cooperative_piggyback` `Contract` MUST link its master award, enforced in
   the runtime shape.** `Contract.__post_init__` raises `InvalidContract` if
   `acquisition_channel == 'cooperative_piggyback'` and `parent_cooperative_contract`
   is unset (SIG-ONTO-032). `_build_contract` defaults a contract sourced from a
   cooperative vehicle to that channel and carries the master award through, so the
   invariant is impossible to satisfy while dropping the ridden award — a missing
   local RFP is never read as "no procurement evidence". `acquisition_channel` is a
   **required model element**, validated against the frozen `AcquisitionChannel` enum
   (lock-stepped to the ontology by a test).

2. **`FundingInstrument` makes funder, recipient, and purchaser distinct, enforced.**
   `funder` and `recipient` are both required and validated to **differ**
   (`InvalidFundingInstrument` otherwise) — the entity exists precisely because the
   party paying is not the party operating (SIG-ONTO-033). `instrument_type` is
   validated against the frozen `FundingInstrumentType` enum, and `federal_award_id`
   carries the USAspending link.

3. **USAspending sub-awards are pulled, not only prime awards, and traced to a local
   deployment.** `assert_pulls_subawards` refuses a USAspending target that does not
   set `subaward` truthy (enforced in both `discover()` and `fetch()`), so a prime-only
   pull that would miss the federal-grant → local link cannot run.
   `funding_instrument_from_subaward` maps a `SubAward` (prime awardee = funder,
   sub-awardee = recipient, `prime_award_id` = `federal_award_id`) to a
   `federal_grant` `FundingInstrument`, and `trace_subaward_to_deployment` emits the
   `federal_award_id` → deployment candidate link (requiring a `federal_award_id`).

4. **This ticket builds and publishes the agenda-platform tenant registry, and the
   connector reads its targets from it.** `data/agenda_tenants.toml` is the
   municipality→platform directory (§22.3): each row maps a jurisdiction to the
   platform source id and the per-tenant API key. `agenda_tenants()` /
   `tenant_targets()` load it, and `ProcurementConnector.discover()` reads its targets
   for an agenda-platform source. It is DATA, not code (SIG-ENG-001), versioned like
   every other registry (§20).

5. **Tenant-discovery negatives are retained as coverage records, wired now ahead of
   P09.1 (SIG-METRIC-002a).** A jurisdiction probed and found to have no discoverable
   agenda platform is a `[negatives.*]` row in the registry, and
   `tenant_discovery_negatives()` renders each as a `NO_EVIDENCE_FOUND` coverage
   record by reusing `db.absence` (naming the platforms probed, SIG-TIME-011). The
   negative space is retained now so P09.1's coverage surfaces inherit it rather than
   a discarded null — the same reuse-`db.absence` pattern ADR-034 established for the
   records channel's `no_responsive_records`.

6. **`artifact_type` becomes a controlled ontology vocabulary carrying the
   SIG-INGEST-047 additions.** The §10.3.2 `artifact_type` vocabulary had no
   executable, testable home (the DB column is free text; the 9-value directness
   `artifact_genres` in `predicates.yaml` is a different vocabulary). It is added as a
   LinkML `ArtifactType` enum in the ontology source of truth (§20.1) — the full
   §10.3.2 genre list **plus** `state_auditor_survey`, `warrant`, and
   `procurement_aggregator_record` — attached to `EvidenceArtifact.artifact_type` and
   published as a versioned SKOS scheme, then regenerated. This is additive and
   back-compatible: a new optional slot and a new enum, no change to a prior wire name
   or the free-text DB column. The paywalled aggregator (`govspend`) is already
   registered under `LINK` (P00.4); the connector stamps
   `procurement_aggregator_record` on its captured documents.

7. **The connector is a targeted-lookup client with a predicate allowlist, emitting
   candidates only.** Like `records`, it never crawls; its claim rows pass the
   predicate allowlist (SIG-INGEST-033) — only the `Contract`/`FundingInstrument`
   surface plus the dated lifecycle transition; a device count, a deployment, a
   records-request claim, or a parsed-document claim is refused at ingest. Party
   predicates (`buyer`/`seller`/`parent_cooperative_contract`/`funder`/`recipient`)
   carry **candidate identifiers**, never resolved entity ids (SIG-INGEST-034).

8. **A captured procurement document is classified via the P07.1 parser, not parsed
   here.** A non-JSON capture (a signed PDF contract, a mixed-format ZIP of award
   packets) becomes an `EvidenceArtifact` row carrying its `artifact_type` and the
   `parsing.classification` verdict; the layer engines run in P07.1, exactly as for
   the records channel.

## Consequences

Procurement now ingests through the same eight stages as every other source. A
cooperative piggyback cannot be recorded without its master award, so the "no local
RFP ⇒ no procurement" error is structurally impossible; a federal grant is traceable
to the local deployment it funded through USAspending sub-awards; agenda platforms
have a published tenant directory the connector reads, and the jurisdictions where no
platform was found are retained as queryable coverage rather than dropped; and the
`artifact_type` vocabulary is finally executable and carries the three SIG-INGEST-047
additions. Costs and deferrals, stated rather than hidden:

- **No live USAspending/Legistar/PrimeGov HTTP transport ships here.** The connector
  fetches through the shared politeness layer over an injected transport, the same
  deferral `connectors.net` already makes; the sub-award/tenant endpoint facts are
  versioned data (`procurement_vocab.toml`, `agenda_tenants.toml`).
- **The tenant registry seed is small and partly unverified.** Rows carry an honest
  `verified` flag; unverified seeds assert no certainty SIG does not have (§3.1). The
  registry is the *mechanism* (the directory + the negatives bridge); filling it out
  is ongoing research, and the discovery-negative path ensures gaps are recorded, not
  hidden.
- **The tenant-discovery coverage rows are produced but not yet consumed by a coverage
  surface.** P09.1 owns the surface; this ticket wires the negatives into
  `db.absence`-shaped records now (SIG-METRIC-002a) so they are not discarded, the
  same forward-wiring ADR-034 did for records coverage.
- **Adding `ArtifactType` regenerated the committed ontology artifacts.** The change is
  additive (a new enum + optional slot) and byte-deterministic under the `make
  verify-gen` gate; the free-text `artifact_type` DB column is unchanged.
- **No document-extraction engine ships here** (per §23.6 scope + ADR-033 Decision 4):
  the connector captures and classifies procurement documents; running a layer engine
  is triggered when a document-derived claim is needed, behind the P07.1 interface.

## Alternatives considered

- **Leaving `acquisition_channel`/`parent_cooperative_contract` as optional
  conveniences.** Rejected by SIG-ONTO-032: they are required model elements, and the
  cooperative-piggyback→parent invariant is the whole point — enforcing it in the
  runtime shape is the only way a missing local RFP can never be mistaken for absence.
- **Pulling only USAspending prime awards.** Rejected by SIG-ONTO-033: sub-awards are
  the traceable federal-grant → local-surveillance link, and prime-only would miss
  exactly the deployments that appear in no local record.
- **Treating agenda platforms as one "agenda system" without a tenant registry.**
  Rejected: they are per-tenant APIs and no upstream directory exists; §22.3 requires
  SIG to build and publish one.
- **Carrying `artifact_type` as connector-local data or leaving it prose-only.**
  Rejected: §10.3.2 is a controlled vocabulary and SIG-INGEST-047 requires the
  additions be testable; the ontology is the source of truth for controlled
  vocabularies (§20.1), so it is the correct, single home.
- **A bespoke coverage encoding for tenant-discovery negatives.** Rejected: the
  four-state absence model already exists as tested code (`db.absence`); reusing it
  keeps the negative identical to every other `NO_EVIDENCE_FOUND` finding and enforces
  SIG-TIME-011 for free.

## Revisit trigger

Revisit if any of: a cooperative vehicle or agenda platform changes its API shape or a
new vehicle/platform is added (update `procurement_vocab.toml` / `agenda_tenants.toml`,
re-verify the tenant mappings); USAspending changes its sub-award endpoint or the
`prime_award_generated_internal_id` field that is the `federal_award_id` link (re-verify
against `api.usaspending.gov`); P09.1 lands and the tenant-discovery negatives must feed
its coverage surface (Decision 5); the `artifact_type` vocabulary gains further genres
or a downstream needs a DB `CHECK` constraint over it (Decision 6); the P07.1
document-extraction engines land and the connector must run a layer over a captured
procurement document (Decision 8 / ADR-033 Decision 4); or SIG-INGEST-036/037's
crawler-conduct posture is amended (an ADR with counsel, per §26).
