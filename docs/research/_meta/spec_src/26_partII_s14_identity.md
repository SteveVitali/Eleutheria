## 14. Identity architecture

The outline is unambiguous: entity resolution is *foundational infrastructure*, not ancillary
(OL-6.1-03), and identity must be solved before impressive graph visualizations (OL-24-04),
because bad entity resolution makes every network statistic misleading (P6).

### 14.1 The identity problem, stated concretely

One organization appears as: `Los Angeles Police Department`, `LAPD`, `Los Angeles CA PD`,
`City of Los Angeles Police Dept.`, `Los Angeles Police Dept` (OL-6.1-01). Across sources, the
identifiers do not align: vendor portal organization names, EFF Atlas agency names, ORI codes, OSM
`operator` strings, procurement customer names, records-platform jurisdiction records, police
rosters, and court documents each use a different convention (OL-6.1-02).

### 14.2 Per-class canonical identifiers (Q9, Q10, Q11, Q12)

**SIG-IDENT-001 (MUST).** Every organization class MUST have a designated canonical identifier
scheme; where none exists, SIG mints a surrogate under §14.4.

| Organization class | Canonical identifier | Source | Coverage |
|---|---|---|---|
| US law-enforcement agency | **ORI9** | FBI CDE agency registry, per-state endpoints | Broad but not total; excludes non-LE |
| US law-enforcement (crosswalk to geography) | **LEAIC** (ORI ↔ FIPS ↔ census place) | ICPSR | **Manual acquisition** — not automatically fetchable |
| Municipality / county / state | **Census GEOID** | Census Gazetteer + TIGER/Line | Complete for US |
| Named place | **GNIS feature id** | Census `ANSICODE` | Complete |
| School district | **NCES LEAID** | NCES | Complete |
| University | **IPEDS UNITID** | IPEDS | Complete |
| Transit agency | **NTD ID** | FTA | Complete |
| Hospital facility | **CMS CCN** (preferred), NPI secondary | CMS | Good |
| Corporate entity | **GLEIF LEI** | GLEIF golden-copy (CC0) | Public companies and many private |
| Federal contractor | **SAM UEI** (+ legacy DUNS) | USAspending (keyless) | Complete for federal awardees |
| Any entity, cross-project | **Wikidata QID** | Wikidata | Excellent for vendors; **weak for US agencies** |
| Non-US jurisdiction | ISO 3166-2, INSEE, ONS, AGS + **GeoNames id** | national sources | Varies |
| Everything else | **SIG surrogate** | §14.4 | — |

**SIG-IDENT-002 (MUST).** ORI codes MUST be validated against `^[A-Z0-9]{9}$` and MUST NOT be
parsed on the assumption that positions 1–2 are a USPS state code. A `ucr_state_code ↔
usps_state_code` reference table is REQUIRED, containing at minimum `NB→NE` and `GM→GU`.

**SIG-IDENT-003 (MUST).** ORIs whose ninth character is alphabetic MUST be flagged as possible
civil/applicant ORIs and MUST NOT be auto-linked to a surveillance-operating organization without
a second corroborating source.

**SIG-IDENT-004 (MUST).** Agency-registry latitude/longitude MUST be stored with
`geometry_precision = 'organization_centroid_or_unknown'` and MUST NOT be used for point-in-polygon
jurisdiction assignment or as an organization address. Using an agency centroid as a device
location would be a fabrication.

**SIG-IDENT-005 (MUST).** GEOIDs MUST be stored as **fixed-width strings** with a length check,
and every jurisdiction row MUST carry an explicit `level`, because 7-character GEOIDs are ambiguous
across place, county-subdivision, elementary school district, and school-district-administrative
levels.

**SIG-IDENT-006 (MUST).** `Jurisdiction.identifiers` and `Organization.identifiers` MUST be sets
of `(scheme, value)` pairs, never single columns.

**SIG-IDENT-007 (MUST).** Wikidata QIDs MUST be recorded where available but MUST NOT be depended
on for coverage of US law-enforcement agencies. For **vendors**, by contrast, they are strong:
`manufacturer:wikidata` is present on 83.4% of the world's mapped ALPRs (SC-08.2).

**SIG-IDENT-008 (MUST).** Any ingest job returning **zero** records for a jurisdiction MUST fail
the run rather than persist a zero, and MUST distinguish `absent` from `not observed`. A silent
zero is how coverage metrics become lies.

### 14.3 Organization taxonomy and the municipality/department distinction

**SIG-IDENT-009 (MUST).** A municipality and its police department MUST be **distinct
organizations** joined by `parent_of`. They have different identifiers, different legal capacities,
and frequently different surveillance postures — the city signs the contract, the department
operates the system.

**SIG-IDENT-010 (MUST).** Organizations MUST be classified on **two independent axes**:
`organization_class` (what kind of body it is) and `operating_relationship` (how it relates to the
surveillance in question). A university is a class; "purchaser but not operator" is a relationship.

**SIG-IDENT-011 (MUST).** Agency names containing a colon MUST be parsed into a parent
organization plus a local unit, and the parent MUST be materialized as its own Organization.

### 14.4 Surrogate identity for organizations with no external identifier (Q12)

**SIG-IDENT-012 (MUST).** Organizations with no external canonical identifier — HOAs, apartment
complexes, small businesses, private security firms appearing only in a vendor network list — MUST
receive a SIG-minted surrogate with a stored, **immutable** `identity_basis`:
`{normalized_name, org_class, place_geoid, address_hash, first_seen_source_ref, first_seen_at}`.

**SIG-IDENT-013 (MUST).** Address disambiguation MUST emit tiered keys: K1 (TIGER line + side),
K2 (block GEOID), K3 (tract GEOID), K4 (place GEOID). **K1/K2 may support matching; K3/K4 are
blocking-only** and MUST NOT be used as evidence of identity.

**SIG-IDENT-014 (MUST).** An organization that fails the publicity tests of §43.4 MUST NOT be
published by name. It MUST be represented publicly by an **aggregate count within its
jurisdiction**, with the full record retained privately. Network edges to suppressed nodes MUST
remain publishable in aggregate, so that the *shape* of private participation stays visible even
where the participants are not named.

**Rationale.** This is the honest resolution of a real tension. "Forty-seven residential
associations in this county share camera access with the police department" is exactly the kind of
structural fact SIG exists to surface. Naming a specific twelve-household HOA is closer to naming
twelve families. The aggregate preserves the finding; the suppression preserves the people.

**SIG-IDENT-015 (MUST).** Vendor portal slugs MUST be parsed by a documented, versioned grammar
rather than by ad-hoc splitting, with vendor-internal test organizations excluded by an explicit
denylist. Slug parsing is a *hypothesis generator*, never an identity assertion.

### 14.5 Temporal identity: merges, splits, renames, dissolutions (Q29)

**SIG-IDENT-016 (MUST).** Organizational change MUST be modelled as **reified
`OrganizationRelation` records** carrying valid time and transaction time, using a seven-value
vocabulary: `same_as`, `succeeded_by`, `merged_into`, `split_into`, `absorbed`, `parent_of`,
`acquired`.

**SIG-IDENT-017 (MUST).** A pure **rename** MUST produce a new organization *version* and an alias
with a `valid_to`. It MUST NOT produce a succession relation and MUST NOT produce a new identifier.
Renaming is not succession, and conflating them fragments the entity's history.

**SIG-IDENT-018 (MUST).** `Organization.status` MUST use `active | inactive | withdrawn |
suppressed`, where `withdrawn` means the entity was created in error and `suppressed` means it
exists but is not publishable (§14.4).

**SIG-IDENT-019 (MUST).** Five worked cases MUST each exist as a test fixture: a police department
disbanded and absorbed by a county sheriff; two departments merging into a new one; a department
splitting; a pure rename; and a vendor acquisition transferring product ownership.

### 14.6 The resolution cascade (Q27, Q28)

**SIG-IDENT-020 (MUST).** Matching MUST proceed as a **six-tier cascade**, deterministic first.
Tiers 0–3 MAY auto-write. **Tiers 4 and 5 MUST create `PROPOSED` claims and enqueue human review.**
Tier 6 MUST NOT persist per-pair records.

| Tier | Rule | Disposition |
|---|---|---|
| 0 | Exact shared canonical identifier (ORI9, GEOID, LEI, UEI, QID) | Auto-write |
| 1 | Exact upstream-id crosswalk already established | Auto-write |
| 2 | `normalized_name + state + class`, with a **data-generated** collision exclusion list | Auto-write |
| 3a | Government-domain match, with a shared-hosting denylist, domain from a Tier-A/B source | Auto-write |
| 3b | Exact address key K1 + normalized name | Auto-write |
| 4 | Probabilistic match above the review threshold | **Review queue** |
| 5 | Model-assisted or weak-signal candidate | **Review queue** |
| 6 | Below threshold | Discard; no per-pair record |

**SIG-IDENT-021 (MUST).** The probabilistic matcher MUST be **Splink 4** (MIT) on a DuckDB
backend. AGPL-licensed and proprietary matchers are excluded by SIG-STORE-002.

**SIG-IDENT-022 (MUST).** `normalize_org_name()` MUST be a **pure, deterministic, versioned**
function with a committed test-vector suite that runs in CI. It MUST collapse "Sheriff's Office"
and "Sheriff's Department" to one canonical suffix. Acronyms (LAPD, NYPD, LASD, CHP…) MUST be
resolved by **exact lookup** against an `acronym_alias` table and MUST NEVER be fuzzy-matched —
fuzzy-matching acronyms is how two unrelated agencies with similar initials get merged.

**SIG-IDENT-023 (MUST).** Blocking rules MUST be sized before use and rejected above a documented
comparison ceiling. Blocking on suffix alone or state alone is prohibited.

**SIG-IDENT-024 (MUST).** Trigram similarity MAY power an online candidate-search path but MUST
NOT be used as a decision score.

**SIG-IDENT-025 (MUST).** Every match MUST record `match_tier` and `match_evidence`, and for
probabilistic matches the match weight **and its per-comparison decomposition**, surfaced in the UI
as the confidence explanation. An unexplainable merge is a violation of the defining standard.

**SIG-IDENT-026 (MUST).** LLMs MAY generate **review rationales** for the human queue but MUST NOT
write to the graph. Model id and prompt version MUST be logged with each human decision. *(Q28.)*

### 14.7 Quality gates

**SIG-IDENT-027 (MUST).** A **gold-standard label set** MUST be constructed by stratified
blocked-pair sampling across match-weight bands, with double adjudication reporting Cohen's κ, a
three-value label vocabulary, written adjudication rules, and a **frozen holdout**. It MUST be
versioned data with per-label provenance.

**SIG-IDENT-028 (MUST).** Every ER run MUST report pairwise precision/recall/F1 at each tier
boundary and B-cubed cluster precision/recall on the holdout. **Auto-write tiers MUST be
automatically demoted to review if holdout precision falls below the published threshold.**

**SIG-IDENT-029 (MUST).** Cluster-shape alerts MUST fire for implausible clusters — a municipal PD
or sheriff cluster above a size threshold, or a cluster joined by a single bridge into components
that are each substantial. These are the signatures of a bad merge.

**SIG-IDENT-030 (MUST).** No network-analytics surface may ship before these gates pass (P6,
§14.7). The UI MUST carry an ER-quality disclosure wherever centrality or hub statistics appear.

### 14.8 Public identifiers and stability (Q37)

**SIG-IDENT-031 (MUST).** SIG MUST mint persistent public identifiers of the form
`sig:<type>:<uuidv7>`, dereferenceable at `https://<host>/id/<type>/<uuid>` with content
negotiation (HTML, JSON-LD, RDF).

**SIG-IDENT-032 (MUST).** Public identifiers MUST be **stable across cluster changes**. When a
cluster splits or merges, the surviving identifiers MUST be preserved and the change recorded as an
explicit, dated **merge/split event** with `redirects_to` or `split_into` pointers and tombstones.
An identifier MUST NEVER be silently reassigned to a different real-world entity — that is the one
failure that would poison every downstream citation.

**SIG-IDENT-033 (MUST).** SIG MUST publish a **crosswalk export** mapping SIG identifiers to every
external identifier it holds, under the most permissive licence the constituent rights permit. This
is the single highest-leverage artifact SIG can give the ecosystem: it lets other projects
reproduce national analyses without rebuilding entity resolution (OL-22.6-01).

**SIG-IDENT-034 (MUST).** SIG MUST publish and maintain an `ORI9 → Census GEOID` crosswalk as a
public artifact, subject to the licensing gate.

---
