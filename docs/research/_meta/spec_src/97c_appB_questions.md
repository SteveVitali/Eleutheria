# Appendix B — Answers to the 37 mandatory questions (outline §20)

The outline designates these as mandatory research tasks for the downstream agent. Each is answered
with its status: **ANSWERED** (resolved with evidence), **ANSWERED-DESIGN** (a design decision made
here), **PARTIAL** (partly resolved; residual in the risk register), or **BLOCKED** (could not be
resolved; the spec hedges and Stage 0 must close it).

## Data access

**Q1 — Does Eyes on Flock expose an API, downloadable database, or archival repository?**
**ANSWERED — YES, and verified independently** (SC-18, R2-F2.6). A public, unauthenticated,
key-free JSON API: `GET /api/v1/data` returns HTTP 200, 7.6 MB, `{summary, portals}` with **950
portals × 20 fields** plus national roll-ups; `GET /api/audit/{state}/{slug}` is paginated and
supports **`?download=true` for CSV bulk export**; `GET /api/v1/map/{slug}` returns imagery.
`robots.txt` grants `User-agent: * → Allow: /`. No headless browser is required.

**The portal field set maps almost one-for-one onto the outline's inventory (OL-2B-FP-02)**,
including `data_retention`, `total_cameras`, `total_searches`, `vehicles_captured`, `hotlist_hits`,
`organizations_shared_with`, `organizations_received_from`, and `prohibited_uses`. **Phase 11 is
unblocked and risk R-02 is closed.**

**Q2 — Can we obtain its historical portal snapshots directly?** **ANSWERED — yes, two ways.**
(a) The audit exports themselves carry roughly **9.5 months of accumulated history per portal**, far
exceeding the vendor's ~30-day public window. (b) The Internet Archive holds **29 captures of the
API endpoint itself** spanning about 13 months, giving SIG a back-fill at **zero cost to the
operator** (SIG-INGEST-030b).

This matters disproportionately because the vendor's own domains are excluded from the general web
archive (SC-13): these aggregator captures are plausibly the **only** longitudinal record of portal
state that exists anywhere.

**Q3 — What are its reuse/licence terms?** **ANSWERED: CC BY-SA 4.0**, stated in the site footer
and confirmed in the built JS bundle. Contact published: `contact@eyesonflock.com`.

**ShareAlike is architecturally consequential**, not merely an attribution note: it is a *third*
incompatible licence regime alongside ODbL and CC-BY-4.0, and it forced the export model from a
two-way split to the N-compartment design of SIG-LIC-004a. A residual question remains open —
whether the grant is intended to cover the **API payload** as well as site content — and it is a
Stage-0 question for the operator (G.4.3).

**Q4 — What exports does HIBF make available, under what licence and cadence?** **PARTIAL.** The
record *types* and their exact fields are documented in full and captured verbatim (F2.3):
Organization Audit, Network Audit, Portal/Public Audit, SharedNetworks.csv, Event Logs, and
Configuration Settings. Licence and cadence were **not** located; Stage 0 must resolve them.

**Q5 — What APIs/exports does ALPR Watch publish?** **PARTIAL.** Confirmed public artifacts: KMZ
avoidance packages, offline routing data packages, a Superset FOIA dashboard, and GitLab
repositories — **GitLab, not GitHub** (F1.10). No REST API observed. The project's scope has shifted
materially from the outline's description.

**Q6 — What machine-readable interfaces does EFF Atlas expose beyond CSV?** **PARTIAL.** Bulk CSV
confirmed; >15,000 datapoints across 6,000+ jurisdictions; last updated 2026-08-12. No additional
public API confirmed. Notably, EFF has publicly delegated the device layer to DeFlock (SC-10),
which defines the federation boundary.

**Q7 — MuckRock API constraints and redistribution terms?** **ANSWERED (constraints).** It is
**api_v2**, not the v1 the outline references; **every data endpoint returns 401**; auth is a
5-minute JWT; ~15 requests/minute. Redistribution terms remain a Stage 0 item.

**Q8 — What can be pulled from DocumentCloud programmatically?** **ANSWERED.** The search API and
S3 full-text assets were successfully called unauthenticated for public documents.

## Identity

**Q9 — Best public canonical US law-enforcement agency identifier?** **ANSWERED.** **ORI9**, via the
FBI CDE per-state agency endpoints (api.data.gov key required), with the **LEAIC crosswalk** as the
essential ORI↔FIPS↔place bridge — obtained **manually**, not automatically (§14.2).

**Q10 — How complete are ORI codes, and how should non-LE entities be represented?** **ANSWERED.**
Broad for law enforcement, absent for everything else. Non-LE entities use per-class identifiers
(GEOID, NCES LEAID, IPEDS UNITID, NTD ID, CMS CCN, GLEIF LEI, SAM UEI) or a SIG surrogate with an
immutable `identity_basis` (§14.4). Two ORI traps are specified: the 9-character pattern must not be
parsed positionally for state, and alphabetic-9th-character ORIs may be civil/applicant ORIs
(SIG-IDENT-002/003).

**Q11 — Which datasets provide canonical municipal/county/state identifiers?** **ANSWERED.** Census
GEOID via Gazetteer and TIGER/Line, with GNIS feature ids, plus GeoNames for international
generality. Fixed-width storage with an explicit level is mandatory because 7-character GEOIDs are
ambiguous (SIG-IDENT-005).

**Q12 — How should private organizations in vendor networks be disambiguated?** **ANSWERED-DESIGN.**
SIG surrogate + `identity_basis` + tiered address keys, with K3/K4 blocking-only; and the
publication rule that an entity failing the publicity tests is represented publicly **as an
aggregate count**, with network edges to suppressed nodes still publishable in aggregate (§14.4).

## Licensing

**Q13 — Precisely how does ODbL apply to a graph joining OSM records to non-OSM entities?**
**ANSWERED.** In depth at §42.3 / R1-F1.12–F1.16. The Collective Database Guideline's fourth bullet
would permit adding `operator` — explicitly named as a *property* — by reference, **if** no OSM data
is used for that property within a regional cut. But the Horizontal Layers Guideline requires
sharing "additions or factual corrections" to OSM-layer data and specifically names
adding-by-comparison-with-OSM as a must-share case, which describes SIG's workflow. The guidelines
conflict for SIG's case; the conservative reading governs.

**Q14 — Can an OSM physical-assets table remain logically/licensably separate?** **ANSWERED — and
the answer is "not by separation alone."** The guideline states a join key **is** a reference and
that physical separation is **not** sufficient for independence. So Strategy A fails. SIG adopts
**Strategy B**: the asset layer is separate *and* ODbL; the SIG-original graph is CC-BY-4.0. Note
also that substantiality offers no escape — the threshold is ~100 features and repeated small
extractions count as one large one (F1.14).

**Q15 — Licences governing Atlas, HIBF, Eyes on Flock, ALPR Watch, Accountability Atlas?**
**ANSWERED — and the answer is negative for most of them**, which is itself the finding.

| Source | Position |
|---|---|
| Atlas | `CC-BY-4.0` **with a third-party-content caveat** (SC-09) — an adjudication between two workstreams that disagreed |
| Eyes on Flock | **CC BY-SA 4.0** (SC-18.3) |
| HIBF | **No licence at all** — no copyright line, no reuse grant anywhere on the domain |
| ALPR Accountability Atlas | **No licence at all** |
| ALPR Watch | **Mixed** — copyleft on some repositories, nothing on the bulk data tree |
| ALPR Abuse Library | **None, plus an affirmative refusal** — `ai-train=no`, AI-crawler disallows, and an EU DSM Article 4 reservation |

Four of six therefore register as `UNDETERMINED` or `refused`, and the export gate is **closed**
against them (SIG-LIC-004). This is the outcome OL-14.2-02 exists to prevent discovering after
launch, and it is why `redistributable` is a separately reviewed field rather than a function of the
licence string.

**Q16 — What source documents may be archived vs merely linked?** **ANSWERED-DESIGN.** Governed by
`custody_posture` (MIRROR / DERIVE / REFERENCE / LINK, §8.4) and enforced before fetch
(SIG-INGEST-014), with `capture_status` recording artifacts that are cited but unretrievable
(SIG-EPIS-005) and storage tiers governing exposure (§17.5).

## Temporal data

**Q17 — What snapshot cadence is justified for transparency portals?** **ANSWERED, and the answer
is set by the upstream rather than by SIG.** The aggregator's own recrawl advances its snapshot
field roughly **monthly**. SIG MUST key change detection on that field rather than on fetch time,
and MUST NOT poll faster than the upstream refreshes — polling faster adds load without adding
information (SIG-INGEST-030c).

Direct capture from the vendor remains unavailable (F2.1), and the fallback channels' cadences are
derived from predicate volatility (§28.3) rather than from habit:

| Channel | Justified cadence | Derivation |
|---|---|---|
| Partner feed, if obtained | Follow the partner's own capture rate; **add no independent load** | Duplicating a partner's crawl is both wasteful and rude |
| Contributor-mediated capture | Opportunistic, prioritized by staleness | Driven by the "sharing snapshot stale" detector (§33.2 #34) |
| Records-based configuration acquisition | **Annual baseline**, plus event-triggered | `configured_retention_days` is MODERATE (h = 9 mo); an annual request keeps it inside `C2` |
| Event-triggered re-request | On any of: a contract renewal, a policy change, a reported incident, or a lifecycle transition | These are the events that change configuration, so they are the correct trigger |

The general rule the outline was reaching for: **snapshot cadence should be a function of the
predicate's half-life, not of what is technically convenient.** Capturing a VOLATILE predicate
annually is nearly worthless; capturing an IMMUTABLE one repeatedly is waste.

**Q18 — How should deleted portals and inactive organizations be preserved?** **ANSWERED-DESIGN.**
Disappearance is a **dated event on the artifact**, never a deletion; the last capture is retained;
a research task is generated; the state is distinctly rendered (§17.6, SIG-INGEST-009).

**Q19 — How to represent OSM edit history without replicating the whole history database?**
**ANSWERED — VERIFIED** (SC-17.2). Store element id **and version** on every asset claim
(REQ-R1-01, §23.2); fetch per-element history on demand for the small set of elements under active
reconciliation; never mirror the history planet.

The endpoint `/api/0.6/<type>/<id>/history.json` was **tested live** and returns the complete
version history with per-version tag sets, `changeset`, `user`, and `timestamp`.

The design also turned out to have a **mandatory** use rather than an optional one: `first_observed`
cannot be read from an element's creation date, because OSM elements are routinely *repurposed*.
Four measured ALPR nodes were created in 2009 as freeway imports and became surveillance nodes in
2024 — a fifteen-year gap that, if taken as the device date, would silently corrupt the temporal
layer (SIG-INGEST-045a).

## Graph storage

**Q20 — Relational/PostGIS, property graph, RDF, or hybrid?** **ANSWERED.** **Hybrid with a
relational core**: PostgreSQL ≥18 + PostGIS ≥3.6.3 canonical, everything else a rebuildable
projection (§15.1). Scored decisively against four alternatives; the disqualifications are concrete
(an archived repository, GPL/BUSL licensing on the features SIG needs, no geospatial story), not
aesthetic.

**Q21 — Which model best supports claim-level provenance and bitemporal history?** **ANSWERED, with
a qualification that matters.** RDF-star/Wikibase model provenance best; XTDB models bitemporality
best; **neither carries SIG's geospatial, access-control, and constraint requirements.** Postgres
carries all of them and can *emit* the other two as projections; the reverse is not true (§15.3).

**Q22 — How should high-volume audit aggregates remain separate?** **ANSWERED.** Hive-partitioned
Parquet queried by DuckDB, joined to the graph **by UUID and period only, never by name**, with
partitions registered as evidence artifacts (§18). The boundary is also a privacy boundary: no raw
audit rows exist on either side.

## Ingestion

**Q23 — Which connectors can be incremental?** **ANSWERED.** Per-class matrix at §21.3, with an
explicit strategy per mode and a `manual_acquisition` class for dependencies that cannot be
automated (SIG-INGEST-008).

**Q24 — Which sources require scraping?** **ANSWERED — and reframed.** Scraping is four separate
legal tracks, not one technical question (§26). Concretely: the highest-value scraping target is
**not lawfully scrapable** (F2.1), while several sources the outline treats as scraping targets
turn out to have **real APIs** — Legistar, PrimeGov, CivicClerk, NextRequest, DocumentCloud,
USAspending — all successfully called (§22.2).

**Q25 — How should source snapshots be content-addressed?** **ANSWERED.** Multihash (base32) so the
algorithm is part of the value; SHA-2 for interop with BLAKE3 in fixity; OCFL 1.1 storage root on
object storage with versioning and **governance-mode** Object Lock; WACZ for web captures so pages
stay **re-parseable**, not merely viewable (§17).

**Q26 — What parser architecture handles PDF/HTML/CSV/XLSX/ZIP/JSON/meeting systems/contracts?**
**ANSWERED.** The seven-layer cheapest-sufficient ladder with recorded method, mandatory locators,
file classification before parsing, and committed fixtures plus a live canary (§24).

## Entity resolution

**Q27 — Which matches can be deterministic?** **ANSWERED.** Cascade tiers 0–3: shared canonical
identifier; established crosswalk; normalized-name+state+class with a data-generated collision
exclusion list; government-domain match with a shared-hosting denylist; exact address key K1 +
normalized name (§14.6).

**Q28 — Where should fuzzy/model-assisted matching generate review queues rather than writes?**
**ANSWERED.** Tiers 4 and 5, always. LLMs may generate review rationales but **may not write to the
graph**, with model and prompt version logged against each human decision (SIG-IDENT-026,
SIG-LLM-002).

**Q29 — How should aliases and mergers be represented?** **ANSWERED.** Typed aliases with their own
validity intervals; reified `OrganizationRelation` records with valid and transaction time over a
seven-value vocabulary; and the rule that **a rename is not a succession** (SIG-IDENT-016/017), with
five worked cases as required fixtures.

## Safety and privacy

**Q30 — What publication policy governs plates, names, private-residence detections, sensitive
content?** **ANSWERED.** §43: categorical exclusions (plates never; **home addresses categorically,
not by balancing**); the five-class coordinate matrix; the five-prong officer test requiring two
concurring reviewers with no-publish as the default on disagreement; and the RF rule that a
residential-parcel candidate is never published at any precision.

**Q31 — Which raw records should be stored privately and represented publicly only by metadata?**
**ANSWERED.** The `sealed` storage tier, which **still carries a public metadata representation** —
existence, source, date, digest, and the claims it supports — so SIG can say "we hold this contract,
here is its hash, here is what it establishes" without publishing it (SIG-EVID-010).

**Q32 — How should takedown/correction requests work?** **ANSWERED.** §45: one-click intake from any
claim; categories with privacy-harm prioritized; five permitted outcomes **including published
refusal**; corrections as new assertions preserving prior belief; and **suppression as a primitive
distinct from deletion** — the omission in the outline's append-only model that would otherwise
force a destructive delete on the first valid privacy demand (SIG-GOV-007).

## Collaboration

**Q33 — How can corrections flow upstream to OSM/DeFlock?** **ANSWERED, and now verified against
both governing documents** (SC-12, SC-14). Risk R-14 is closed.

**No direct automated writes.** Contribution goes through a human-mediated suggestion workflow in
which SIG supplies evidence and a mapper decides, in their own account (SIG-CONTRIB-014/015).

The reason this is the right architecture is sharper than "caution". The **Automated Edits Code of
Conduct** governs edits made *"without review individually by the person controlling the edits"* —
so a workflow where a human reviews each change individually is **outside its scope entirely**,
rather than merely compliant with it. Operator attribution is covered by none of the Code's
exceptions (those are typos, vandalism reversion, correcting one's own work, and reverting
unapproved automated edits), and as external data it would additionally engage the import
guidelines — so a SIG bot account would face the full documentation, consultation, opt-out and
per-scope-change re-approval burden, with *"ignoring this policy will be treated as vandalism"* as
the enforcement posture.

The **Organised Editing Guidelines** *do* apply, because SIG coordinating volunteers is *"a sizeable,
substantial, coordinated editing initiative"*. SIG must publish an activity page disclosing its
organisation, contact, goal, timeframe, tools, data sources **and their usage conditions**, and
**a unique changeset hashtag** (SIG-CONTRIB-016d).

Two consequences worth stating in the answer itself:

- **The hashtag is an asset, not a cost.** It makes SIG's upstream contribution stream publicly
  auditable by third parties, which is what turns the §7 leverage metric from an assertion into a
  measurement SIG does not control (SIG-CONTRIB-016e).
- **The backlog cannot be cleared mechanically.** Throughput is bounded by mapper attention, so the
  design objective is minimizing human cost per resolution, not maximizing write volume
  (SIG-CONTRIB-017a). This is a roadmap constraint, not a footnote.

**Q34 — Could Atlas consume deployment corrections?** **PARTIAL.** A contact address is published
and EFF has stated its scope boundary (SC-10), but no correction-submission channel was confirmed.
Stage 0 item.

**Q35 — Can research tasks link directly to HIBF/MuckRock workflows?** **PARTIAL.** HIBF documents a
submission path and publishes report surfaces SIG should **link to rather than recompute**
(REQ-R2-10). MuckRock's API requires auth on all data endpoints, so programmatic filing is
unconfirmed. The task→`RecordsRequest` model is specified either way (SIG-CONTRIB-019).

**Q36 — Could local groups claim geographic research queues?** **ANSWERED-DESIGN.** Yes — claiming
grants visibility, notification, and queue priority, but **never exclusivity**, and claims expire.
The expiry is the safeguard against coordination hardening into gatekeeping (§33.4).

**Q37 — What stable IDs would allow other projects to link back?** **ANSWERED.**
`sig:<type>:<uuidv7>`, dereferenceable with content negotiation; **stability across cluster
splits/merges via explicit dated merge/split events, redirects, and tombstones**; and a published
crosswalk export — the single highest-leverage artifact SIG can give the ecosystem, because it lets
others reproduce national analyses without rebuilding entity resolution (§14.8).

---
