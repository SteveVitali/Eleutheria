## 13. Controlled vocabularies

All vocabularies here are published as versioned SKOS concept schemes (§20.2) and are immutable
once published. The full term lists live in `ontology/vocab/` as the generated source of truth;
this section specifies their **structure, governing rules, and the terms that are load-bearing**.

### 13.1 Technology (`domain` → `family` → `technology`)

**SIG-ONTO-052 (MUST).** **14 domains, 36 families, 104 technologies** at v1.

**SIG-ONTO-052a (MUST).** Phase 1 acceptance MUST assert these counts against the generated
vocabulary artifact, and MUST assert that every technology term carries its distinguishing
criterion, evidence signature, and salience rating (SIG-ONTO-056). Counts asserted in prose but not
checked against an artifact are unfalsifiable, and this requirement exists to prevent that.

| Domain | Covers |
|---|---|
| `surveillance-vehicle` | ALPR (fixed, mobile, covert, trailer, checkpoint, unspecified), vehicle-fingerprint re-identification, commercial plate-data purchase |
| `surveillance-video` | Fixed CCTV, PTZ, private-camera registry / integration / per-incident request, video analytics, camera trailers |
| `body-worn-video` | **Body-worn cameras (`bwc-recorded`, `bwc-livestream`, `bwc-unspecified`); in-car video; live BWC streaming into an integration platform** |
| `biometric-id` | Face (1:1, 1:N, retrospective, live), iris, DNA/rapid DNA, tattoo, gait, voice |
| `acoustic` | Gunshot detection, acoustic sensing |
| `robotics-aerial` | UAS, drone-as-first-responder, tethered aerostat, persistent aerial |
| `robotics-ground` | UGV, robot dogs |
| `comms-intercept` | Cell-site simulators, tower dumps, wiretap, metadata interception |
| `device-forensics` | Logical/physical extraction, cloud-account extraction, exploit services |
| `data-acquisition` | Ad-tech location purchase, location-data subscription platforms, person-records brokers, utility records |
| `analytics-inference` | Predictive policing (place/person), risk assessment, behavioral analytics, social-media monitoring, OSINT platforms |
| `integration-platform` | RTCC platform, CAD/RMS integration, camera federation hub, third-party investigative platforms |
| `person-monitoring` | Electronic monitoring, jail-communications monitoring |
| `facility-screening` | Weapon detection, school surveillance |

**Governing rules:**

- **SIG-ONTO-053 (MUST).** Slugs are lowercase-hyphenated, **stable forever, never reused**.
  Retirement is `status: retired` + `superseded_by`, never deletion.
- **SIG-ONTO-054 (MUST).** Every family MUST have an `-unspecified` leaf (SIG-ONTO-020).
- **SIG-ONTO-055 (MUST).** Slugs encode `family-discriminator`, never a vendor.
- **SIG-ONTO-056 (MUST).** Each technology carries a **distinguishing criterion** (the single test
  separating it from its nearest sibling — two terms sharing a criterion are the same technology),
  an **evidence signature** (the literal strings that indicate presence in real contracts, portals,
  and reporting), and a **salience** rating `L`/`M`/`H`/`C`, where `C` marks technologies
  implicating a constitutional or statutory special category: biometrics, content of
  communications, immigration status, reproductive or religious activity, or First-Amendment-
  protected association.
- **SIG-ONTO-057 (MUST).** Two terms that external taxonomies treat as technologies are **not**
  technologies in SIG: a *fusion center* is an Organization type; an *RTCC* is both a Technology
  (`rtcc-platform`, the software) and an Organization sub-type (the unit), and the two MUST be
  distinguished.

**SIG-ONTO-057a (SHOULD).** Where SIG's own taxonomy must align with an external one, it SHOULD be
shaped after the **civil-liberties-argument** taxonomy rather than the procurement-visible one, with
the latter's categories as **children**.

The measurement supports this: of the procurement-oriented taxonomy's 12 categories, only **6
exact-match** the civil-liberties one; **five of the latter's technologies have no equivalent at
all** in the former — community surveillance apps, electronic monitoring, forensic extraction tools,
police access to IoT devices, and real-time location tracking — and one of the former's entries has
no counterpart because it is an *organization type*, not a technology. The civil-liberties taxonomy
is the broader and more structurally sound of the two, and it already covers the
data-access-without-hardware categories that OL-4.9 identifies as the future of the domain. So
`surveillance_camera_network` parents `camera_registry`, `rtcc_platform`, and `video_analytics`,
rather than the three sitting as siblings of it.

**SIG-ONTO-058 (MUST).** External taxonomies partition this space on **incompatible axes** — the
EFF Atlas by procurement-visible technology, EFF Street-Level Surveillance by civil-liberties
argument, and municipal surveillance-ordinance inventories by legal trigger. Crosswalks MUST
therefore be many-to-many with explicit SKOS mapping relations and a `lossy` flag (§20.3). SIG
MUST NOT adopt any external vocabulary as its primary key.

**SIG-ONTO-059 (MUST).** External vocabularies **change, and their changes carry negative
semantics**. The EFF Atlas retired its Ring/Neighbors category in March 2024 and removed ~2,530
data points, while adding Third-Party Investigative Platforms. Therefore *absence of a Ring data
point after March 2024 means "category retired", not "program ended"*. Every ingested external
vocabulary MUST carry a version stamp, and the coverage model (§32) MUST record category
retirements so that a disappearance is never read as a world change. *(R7-F7.4; a concrete
instance of OL-9.4-01.)*

### 13.2 Capability (`verb.object.scope`)

**SIG-ONTO-060 (MUST).** ~45 terms at v1, following the grammar of §11.6 (Capability). Scopes: `own`,
`partner`, `state`, `region`, `national`, `commercial`, `subject`. Classes: query, alerting,
live-operations, acquisition/extraction, **export/onward-disclosure**, governance (negative).

### 13.3 Evidence and epistemics

| Vocabulary | Terms |
|---|---|
| `source_reliability` (R) | `R1`…`R6` (§10.4) |
| `claim_directness` (D) | `D1`…`D6` (§10.5) |
| `artifact_integrity` (I) | `I1`, `I2`, `I3` |
| `currency` (C) | `C1` CURRENT, `C2` AGING, `C3` STALE, `C4` HISTORICAL |
| `weight_class` (W) | `W0`…`W4` |
| `confidence` | §10.6 |
| `evidence_role` | `establishes`, `corroborates`, `contextualizes`, `contradicts`, `supersedes_basis`, `attests_absence` |
| `epistemic_status` (events) | `alleged`, `reported`, `confirmed`, `adjudicated`, `policy_action`, `vendor_statement`, `disputed`, `retracted` |
| `absence_kind` | `not_researched`, `searched_not_found`, `evidence_of_absence`, `not_applicable` |
| `contradiction_state` | `uncontested`, `resolved_conflict`, `unresolved_conflict`, `insufficient` |
| `value_kind` | `value`, `somevalue`, `novalue` |
| `predicate_volatility` | `IMMUTABLE`, `GLACIAL`, `SLOW`, `MODERATE`, `FAST`, `VOLATILE` |

### 13.4 Deployment lifecycle — four orthogonal tracks

**SIG-ONTO-061 (MUST).** Lifecycle MUST be modelled as **four orthogonal state variables plus a
flag**, not one enum. *(R7 Part 7; corrects OL-6.7-01, which is one dimension short.)*

The proof that one enum is insufficient: a jurisdiction can simultaneously have a *cancelled
contract*, *hardware still physically mounted*, and *service unplugged*. That is three
simultaneous states on three different axes. A single enum forces a choice among them, and every
available choice produces a false statement.

**All fourteen of the outline's states are retained**; each is assigned to a track; ten are added.

**Track 1 — `procurement_state` (14):** `proposed`*, `rfp_issued`, `awarded`, `contracted`*,
`cooperative_piggyback`, `bundle_included`, `free_trial`, `donated`, `third_party_funded`,
`grant_funded_pending`, `renewed`, `nonrenewed`*, `canceled`*, `rejected`.

**Track 2 — `physical_state` (7):** `not_installed`, `installation`*, `installed`,
`installed_inactive`, `decommissioning`*, `removed`*, `destroyed_or_lost`.

**Track 3 — `operational_state` (6):** `inactive`, `pilot`*, `active`*, `expanded`*,
`restricted`*, `suspended`*.

**Track 4 — `authorization_state` (6):** `unauthorized`, `approval_pending`, `authorized`,
`authorized_expired`, `moratorium`, `sunset_by_ordinance`.

**Flag:** `litigation_hold` — coexists with any combination.

*(\* = a state named in OL-6.7-01.)*

**SIG-ONTO-062 (MUST).** `replaced` is **NOT** a state. It is the `replaced_by` edge (§12.3).
Modelling replacement as a state is precisely the error that lets a vendor swap read as a
surveillance reduction — the failure OL-22.5-02 and OL-6.7-02 exist to prevent.

**SIG-ONTO-063 (MUST).** `unknown` MUST be an admissible value on **every** track and MUST be the
default. This puts OL-9.4 and OL-6.6 in the schema rather than in prose.

**SIG-ONTO-064 (MUST).** `free_trial → operational:active` with **no procurement transition** is a
legal path. It is the mechanism by which surveillance capability is acquired with no procurement
paper trail at all, and it is the single most important edge in the state machine for SIG's
discovery mission.

**SIG-ONTO-065 (MUST).** Forbidden combinations MUST be **soft** constraints — flagged, never
rejected — because the interesting cases are real:

| Combination | Disposition |
|---|---|
| `physical=removed` ∧ `operational=active` | Impossible; flag as data error |
| `procurement=canceled` ∧ `physical=installed` | **Legal and common.** MUST NOT be blocked |
| `procurement=canceled` ∧ `operational=active` | Legal during wind-down; flag for a research task |
| `authorization=authorized` ∧ `physical=not_installed` | Legal; a high-value research task (authorized but not deployed) |

### 13.5 Organization type, evidence type, acquisition method, roles

Specified inline at §11.2, §10.3.2, and §12.4. All are namespaced and extensible per §13.7.

### 13.6 Predicates

**SIG-ONTO-066 (MUST).** Every predicate MUST be registered in `vocab_predicate` with:
`predicate_id`, `vocab_version`, `value_datatype`, `cardinality`, `definition`,
`skos_concept_iri`, **`volatility_class` and half-life** (§28.3), **`resolution_strategy`**
(§28.4), and its **row in the directness matrix** (§10.5).

**SIG-ONTO-067 (MUST).** A predicate MUST NOT be added without all of those, because a predicate
with no volatility class and no resolution strategy cannot be resolved — it can only be guessed at.

### 13.7 Internationalization of vocabularies

**SIG-ONTO-068 (MUST).** `organization_type`, `jurisdiction_type`, `acquisition_method`, and
`legal_instrument_type` MUST be **namespaced by country** (`us.*`, `fr.*`, `uk.*`, `de.*`) with a
shared abstract parent per concept. A US-shaped enum is prohibited (§5.3).

**SIG-ONTO-069 (MUST).** Every label-bearing term and every entity name MUST support repeatable
values tagged with **BCP 47** language tags. Transliterations carry a `transliteration_scheme`
qualifier.

### 13.8 Acquisition method, internationalized

`foia_request` is a US-specific term. The vocabulary MUST carry the abstract parent
`records_request` with national children (`us.foia`, `us.state_public_records`, `fr.cada`,
`uk.foi`, `eu.access_to_documents`), plus `no_equivalent_available` for jurisdictions with no
access regime — which is itself a coverage fact worth recording.

---
