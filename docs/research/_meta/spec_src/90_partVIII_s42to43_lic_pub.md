# Part VIII — Governance, safety, and law

This part is not an appendix of good intentions. It contains binding constraints that the rest of
this specification is written to satisfy. Several architectural decisions elsewhere exist *because*
of these requirements, and an implementation that ships Parts II–VII without Part VIII is a
different and worse project (§0.7).

**Nothing in this Part is legal advice.** It identifies the questions, the governing authorities,
and defensible default postures, and it marks explicitly where counsel is required.

## 42. Licensing and rights

### 42.1 Rights as first-class data

**SIG-LIC-001 (MUST).** Every source and every evidence artifact MUST carry a **rights record**:
SPDX licence expression (using `LicenseRef-SIG-<slug>` for bespoke terms); attribution string;
**`redistributable` as a separately reviewed boolean**; derivative permission; the terms URL; and
the retrieval date. *(Discharges OL-14.2-01.)*

**SIG-LIC-002 (MUST).** The referenced terms text MUST itself be **archived as evidence**. Terms
change, and a rights determination that cannot show what the terms said when it was made is
unverifiable.

**SIG-LIC-003 (MUST).** `redistributable` MUST NOT be derived from the licence string
(SIG-INGEST-024). A site-wide permissive licence may not cover incorporated third-party data, and
inferring in either direction is an error with legal consequences (SC-09).

**SIG-LIC-004 (MUST).** A source with unresolved rights MUST be `UNDETERMINED`, which MUST **fail
the export gate closed**. The connector may still run for internal research; the data may not be
published. *(Discharges OL-14.2-02 — "do not discover after launch that a key dataset cannot
legally be redistributed.")*

### 42.2 SIG's own licences

**SIG-LIC-004a (MUST).** The export architecture MUST be an **N-compartment model keyed on the
rights record**, not a fixed two-way split. Each mutually-incompatible licence regime present in the
corpus gets its own separable table and its own export file, and the set of compartments is **data,
not code** — adding a source under a new share-alike licence MUST NOT require a schema change.

**This is a correction.** An earlier framing treated the problem as "ODbL assets vs everything
else". SIG has at least **three** incompatible regimes, and the third was discovered only by
checking (SC-18.3):

| Compartment | Licence | Share-alike? | Source |
|---|---|---|---|
| OSM-derived physical assets | **ODbL-1.0** | Yes | OpenStreetMap |
| Portal layer | **CC BY-SA 4.0** | Yes | Eyes on Flock |
| SIG-original graph | **CC-BY-4.0** | No | SIG |

ODbL and CC BY-SA 4.0 are not mergeable with each other, and **neither may be folded into a
CC-BY-4.0 export.** A Phase-14 export that merged portal-derived camera counts into the main
CC-BY graph would be a licence violation that is **invisible in the data and obvious to the
licensor** — the worst combination. The compatibility gate of SIG-EXPORT-004 MUST therefore run
per compartment, and its test suite MUST include a deliberate cross-compartment merge that fails
the build.

**SIG-LIC-004b (MUST).** The rights record MUST carry **`ai_training_permitted`** as a first-class
boolean, separate from the licence expression. A permissive licence does not imply permission to use
the content as model training data: Eyes on Flock's `robots.txt` carries
`Content-Signal: search=yes, ai-train=no, use=reference` while simultaneously granting `Allow: /` to
general agents (SC-18.2). Access permission and training permission are **different grants**, and a
licence string alone cannot express the distinction.

**SIG-LIC-004c (MUST).** Content marked `ai-train=no` MUST NOT be routed through any model-training
pipeline, and the prohibition MUST be enforced at the data layer rather than by convention. Note
this does **not** restrict §25's model-*assisted extraction*, which is inference over a document,
not training on it — but the distinction MUST be documented so that a future contributor does not
collapse it.

**SIG-LIC-005 (MUST).**

| Artifact | Licence | Reasoning |
|---|---|---|
| **Code** | **Apache-2.0** | Patent grant and trademark reservation. AGPL is rejected: the valuable asset is the graph, not the crawler, and AGPL would deter adoption by exactly the newsrooms and institutions Goal 8 targets |
| **OSM-derived physical assets** | **ODbL-1.0**, separate table and file | §42.3 |
| **Portal layer (Eyes on Flock–derived)** | **CC BY-SA 4.0**, separate table and file | ShareAlike; SC-18.3 |
| **SIG-original graph data** | **CC-BY-4.0** | Attribution is what keeps the provenance chain alive downstream — SIG's entire thesis. CC0 is rejected for that reason |
| **Documentation** | **CC-BY-4.0** | |
| **Ontology and vocabularies** | **CC0-1.0** | A vocabulary succeeds only by adoption; every obligation is an adoption tax, and term lists are barely copyrightable in any case |

### 42.3 The ODbL posture (Q13, Q14)

**SIG-LIC-006 (MUST).** SIG MUST adopt **Strategy B** of OL-14.1: publish the OSM-derived
physical-asset layer under ODbL as a physically separate table and export file, and keep the
SIG-original evidence graph under CC-BY-4.0.

**The reasoning, from the actual guidelines** (R1-F1.11 … F1.16):

1. The **Collective Database Guideline** permits adding a *property* to a primary feature **by
   reference** without triggering share-alike — and it names `operator` explicitly as a *property*
   — but only if **no OSM data** is used for that property within a regional cut.
2. The **Horizontal Map Layers Guideline** states that *"if you improve data used in the
   OpenStreetMap layer, such as additions or factual corrections, then you need to share those
   improvements,"* and gives as a "must share" example adding non-OSM data *based on comparison
   with* OSM data. SIG's device attribution is defined by comparison with OSM: it targets exactly
   the nodes OSM lacks an operator for, and it uses OSM geometry for spatial reasoning.
3. The two guidelines therefore point in **opposite directions** for SIG's exact case, and the
   conservative reading governs.
4. **Strategy A is unsafe.** Storing "only identifiers" does not avoid share-alike: the guideline
   holds a join key *is* a reference, states that physical separation is **not** sufficient for
   independence, and requires factual improvements to be shared regardless.
5. **Strategy C is unnecessary** and would impose share-alike on contract, policy, and
   accountability data containing no OSM content, restricting the reuse Goal 8 depends on.
6. **Substantiality is not available as an escape.** The OSMF guideline sets "insubstantial" at
   roughly a village — under 100 features — and states explicitly that *"repeated small extractions
   [count as] one big extraction."* SIG extracts ~144,312 ALPR features systematically and
   repeatedly.

**SIG-LIC-007 (RATIONALE).** This constraint is **mission-aligned, not a cost.** ODbL share-alike on the device
layer requires SIG to give its operator attributions back in a form OSM contributors can use —
which is what P5 and OL-22.6-01 want anyway. The licence enforces the federation compact.

### 42.3a The contribution licence conflict, and its resolution

**SIG-LIC-007a (MUST).** The subset of SIG-authored data that is offered upstream to OSM MUST be
**dual-licensed under CC0-1.0** for that purpose, separately from SIG's CC-BY-4.0 graph licence.

**The conflict is real and would otherwise block the write-back programme.** OSM's import guidance
states: *"We must be able to release the data with our OpenStreetMap License… Your data must be
compatible with the ODbL"* and — decisively — *"**You must not claim an additional copyright for
yourself as the importer.**"* OSM's own compatibility assessment rates **CC-BY-4.0 as requiring an
additional waiver**. So SIG's operator attributions, offered under plain CC-BY-4.0, are **not**
directly contributable.

**Why CC0 for this subset is the right answer rather than a concession:**

1. It satisfies the no-additional-copyright rule directly, with no waiver negotiation.
2. The contributed payload is *facts about public infrastructure* — that an identified agency
   operates an identified device. Facts are thin copyright subject matter at best, and asserting
   rights over them would be both legally weak and contrary to the project's purpose.
3. SIG's goal for this data is **maximum dissemination** (P5, OL-22.6-01). Attribution on the
   contributed subset buys SIG nothing it needs and costs it the ability to give the data away.
4. It is narrowly scoped: **only the contributed subset**, not the graph. SIG's reconciliations,
   contradictions, resolutions, and evidence chains — the actual work — remain CC-BY-4.0.

**SIG-LIC-007b (MUST).** SIG's attribution expectations for the contributed subset MUST be limited
to what OSM offers: mention on the contributors wiki page, a note on the import or activity account,
and source information in changesets. The guidance is explicit that *"if none of these are
acceptable attribution for a data source, you cannot proceed"* — so SIG MUST decide in advance that
they are acceptable, and record that decision, rather than discovering the constraint at
contribution time.

**SIG-LIC-007c (MUST).** The Organised Editing activity page (SIG-CONTRIB-016d) MUST publish the
licence of SIG's operator evidence, because the guidelines require disclosing data sources *"and
their usage conditions"*. Where a piece of evidence's own licence does not permit deriving a
contributed fact from it, that evidence MUST NOT feed a contribution task — which is the
contribution-path licence gate of SIG-CONTRIB-016f, arrived at independently from the licensing side.

**SIG-LIC-008 (MUST).** Produced Works (rendered maps, PDF dossiers, static images) MAY carry SIG's
own licence, **provided the underlying database is also published** as **ODbL clause 4.6** requires. Vector
tiles, GeoJSON, and bulk downloads are **database distribution, not Produced Works**, because they
are intended for extraction.

**SIG-LIC-009 (MUST).** The following MUST be referred to counsel before launch and MUST appear in
the risk register: whether API responses returning device-linked claims constitute distribution of
a Derivative Database under **ODbL clause 4.4(b)**; whether jurisdiction geometry sourced from OSM boundary
relations contaminates the operator property under the Collective Database fourth bullet; the
correct regional-cut unit; and the EU sui generis database right for the international phase.

### 42.4 Export-time computation

**SIG-LIC-009a (MUST).** SIG MUST detect **silently travelling share-alike obligations**. An
obligation does not disappear because an intermediary failed to pass it on: at least one ecosystem
project republishes OSM-derived data **without ODbL attribution**, so a downstream consumer ingesting
from that project would inherit an ODbL obligation with nothing in the artifact to signal it.

Therefore the rights record MUST capture not only a source's own licence but the **provenance of its
data**, and the ingestion gate MUST flag any source whose content is plausibly derived from a
share-alike upstream even where the source itself declares a permissive licence or none. Where this
cannot be resolved, the compartment MUST default to the **stricter** regime, not the declared one.

**SIG-LIC-010 (MUST).** Export licence MUST be **computed** from constituent rights, and the build
MUST fail on incompatibility (SIG-EXPORT-004). This is a CI gate with a test that deliberately
introduces an incompatible source and asserts the build fails.

**SIG-LIC-011 (MUST).** SIG MUST pass downstream the attribution and provenance obligations it
received, per row, so a downstream user can comply without re-deriving the chain.

### 42.5 Reusability

**SIG-LIC-012 (MUST).** Per OL-14.3-01, open code is not enough. SIG MUST ship: open code; open
schemas; downloadable datasets where licensing permits; documented APIs; provenance; versioned
snapshots; and reproducible ingestion. A release missing any of these is incomplete.

---

## 43. Publication policy

### 43.1 The bright line

**SIG-PUB-001 (MUST).** SIG documents **institutions and infrastructure**, not people
(SIG-CHART-024, OL-13.1-01). Every rule below follows from that.

### 43.2 Categorically excluded data

**SIG-PUB-002 (MUST NOT).** SIG MUST NOT store, in any tier, at any sensitivity level:

| Excluded | Enforcement |
|---|---|
| Licence plate numbers, or reversible derivatives | No such column may exist (SIG-STORE-026); schema test |
| Individual travel histories or sightings | No such entity or edge (§12.8) |
| Home addresses of officers or private individuals | **Categorical. No balancing test applies** |
| Private-person names encountered incidentally | Extraction-time redaction |
| Residential association membership of individuals | §14.4 |
| Personal identifiers unrelated to institutional conduct | Extraction-time redaction |

**SIG-PUB-003 (MUST).** Home addresses are excluded **categorically, not by public-interest
balancing**. The outline's §13.2 applies a public-interest standard to officer data generally; that
standard is correct for *names in an accountability claim* and **wrong for addresses**, where the
foreseeable harm is severe, the informational value is near zero, and several jurisdictions impose
strict-liability regimes on publishing them. *(Corrects OL-13.2-01/02 by making one item categorical.)*

### 43.2a SIG must never become the de-pseudonymisation join

**SIG-PUB-003a (MUST).** Operator, user, or account identifiers appearing in third-party audit data
MUST be **hashed with a held-back salt at ingest**, and the raw values MUST NEVER be stored in a
publishable tier or republished — **regardless of the fact that a third party has already published
them.**

**The hazard is live, specific, and named** (R2-F2.15). One ecosystem project publishes, at a single
unauthenticated URL, a 65 MB SQLite database containing **350,043 search-audit rows with raw
operator UUIDs on every row — zero redaction — across 9,717 distinct operators**, joined to
timestamps, agencies, and free-text reasons. A *different* ecosystem project publishes police
rosters and name-resolution tooling.

Neither project individually publishes officer identities. **The join does.** Stable pseudonymous
identifiers plus timestamps plus agency, cross-referenced against rosters and shift schedules
obtainable by records request, re-identify individuals.

**SIG-PUB-003b (MUST).** SIG MUST NOT construct, publish, or enable that join. This is not a
consequence of a general rule; it is a specific prohibition, because SIG is uniquely positioned to
be the thing that makes it work — reconciling identities across projects is precisely what SIG is
for, and this is the one place that capability must be withheld.

Concretely, SIG MUST NOT: ingest per-search rows carrying operator identifiers (§18.1 already
forbids this, and this is the reason it matters most); publish any table joinable on an operator
identifier; or expose an API surface permitting per-operator aggregation.

**SIG-PUB-003c (MUST).** "It is already public" MUST NOT be accepted as a justification anywhere in
this system. The material's prior publication does not reduce the harm of SIG amplifying,
normalising, or making it joinable — and §43.6a establishes that the republisher absorbs the
consequence regardless of the original source's conduct.

**SIG-PUB-003d (SHOULD).** Where SIG becomes aware of an ecosystem project exposing personal data
in this way, it SHOULD raise it privately with that project as part of Stage-0 engagement rather
than publicise it. The objective is that the data stop being exposed, not that SIG be seen to have
noticed.

### 43.3 Coordinate sensitivity

**SIG-PUB-004 (MUST).** Every asset MUST carry a sensitivity class determining published precision
(§19.4). Classification is **role-aware**, not asset-aware (§12.4 separation 6).

| Class | Applies to | Published |
|---|---|---|
| **C1** | Publicly visible hardware on public right-of-way | **Exact** |
| **C2** | Hidden sensor on public infrastructure | **Reduced precision** (documented radius / tract level); exact only if the operator has already published it |
| **C3** | Private-residence candidate; private registrant in a camera-sharing program | **No location.** Program-level facts only |
| **C4** | Confidential facility (domestic-violence shelter, protective, undercover) | **Jurisdiction only; existence not resolvable** |
| **C5** | Mobile asset | **Jurisdiction only**, plus dated historical observations. **Never a current position** |

**SIG-PUB-005 (MUST).** Overrides: an operator-already-published upgrade; **automatic demotion to
C3 on residential-parcel intersection**; a freshness gate beyond which precision is reduced; and a
leak-provenance veto — material whose only provenance is a leak of sensor locations MUST go through
human review before any publication, regardless of its public circulation.

**SIG-PUB-006 (MUST).** C1 is the default for roadside ALPR hardware, consistent with existing
community practice in OSM and DeFlock. SIG does not invent a new norm for the ordinary case; it
adds discipline for the unusual ones.

### 43.4 The officer-naming test

**SIG-PUB-007 (MUST).** A named individual MAY be published **only** if **all five** prongs hold:

1. The claim concerns **official conduct**, not private life.
2. The name appears **on the face of an `R1`/`R2` record** — never inferred, never assembled.
3. The record is **public in the jurisdiction that produced it**.
4. The accountability claim **genuinely fails without the name** — a role designation would not
   serve.
5. Severity, currency, and safety are **proportionate**.

**SIG-PUB-008 (MUST).** **Two independent reviewers MUST concur in writing.** Disagreement defaults
to **no-publish**. The decision, its reasoning, and its reviewers MUST be recorded.

**SIG-PUB-009 (MUST).** Home addresses are outside the test entirely — never, under any prong
(SIG-PUB-003).

**SIG-PUB-010 (MUST).** Routine audit-log rows naming an officer MUST NOT trigger this test,
because they MUST NOT be ingested at all (§18.1).

### 43.5 Candidate assets and RF-derived leads

**SIG-PUB-011 (MUST).** A `CandidateAsset` MUST NOT appear in any public device layer.

**SIG-PUB-012 (MUST).** Promotion to a published `PhysicalAsset` requires **either** human field or
imagery confirmation, **or** a documentary record — never corroboration count alone.

**SIG-PUB-013 (MUST NOT).** A candidate whose location intersects a residential parcel MUST NOT be
published **at any precision, ever**, regardless of corroboration. *(Discharges OL-7.2-06,
OL-2G-FY-03.)*

**SIG-PUB-014 (MUST).** Public UI MUST NOT describe an RF-derived candidate in language implying a
device is known to exist. "A radio observation consistent with this hardware vendor was recorded
nearby" is conformant; "suspected camera location" is not.

### 43.6 Aggregate disclosure

Specified at §18.4. The rule that matters most: **institutional small counts are published;
individual-identifying small counts are suppressed**, and where the two cannot be separated, the
default is suppress-and-review, not publish.

### 43.6a The republisher absorbs the consequence — a worked precedent

**SIG-PUB-014a (MUST).** Any free-text field originating from a records request or a government
data release MUST pass a **pre-publication personal-data screen** before it appears on a public
surface, regardless of the fact that the source is an official record and was lawfully obtained.

**The precedent, verified directly (2026-08-20).** A civil-liberties organization obtained
state-level electronic search-warrant disclosure data that the state was statutorily obliged to
publish but had taken offline. It published the data. The state agency then contacted it to say
that *"staff had failed to properly redact potentially personal information from these fields"* —
specifically the free-text `nature of investigation` and `facts giving rise to the emergency`
columns. The publisher responded in three stages over ten weeks: it first replaced the published
files with **column-reduced versions**; then, once the agency supplied properly redacted data,
replaced them again; and finally **withdrew from hosting the dataset entirely**.

Four things follow, and each is already a requirement elsewhere in this document — this precedent is
why:

| Lesson | Requirement |
|---|---|
| A lawfully public government record can contain unredacted personal data, and **the republisher, not the originating agency, absorbs the consequence** | SIG-PUB-014a, above |
| SIG must be able to **replace a published artifact in place with a reduced version while preserving the claim** | §45.2 outcomes; §17.5 redacted derivative as a new capture |
| SIG must have a takedown path that can escalate all the way to un-hosting | §45.2, SIG-GOV-007 suppression |
| "Link, don't mirror" is the right default for high-risk record sets — **but** the upstream here had itself gone dark, which is why it was mirrored in the first place | §8.4 custody postures; the resolution is **mirror privately, publish metadata publicly** (§17.5 `sealed`) |

**SIG-PUB-014b (MUST).** The tension in the fourth row MUST NOT be resolved by refusing to mirror.
Upstream instability is real (SC-11), and refusing to mirror loses the record. The `sealed` tier
exists exactly so that SIG can hold what it must not publish, and SIG MUST prefer that over either
horn of the false choice between "publish it" and "lose it".

### 43.7 Redaction

**SIG-PUB-015 (MUST).** Redaction produces a **new capture** (SIG-EVID-011), records its method and
version, and is reviewable. Redaction MUST be applied to excerpts surfaced in the UI and API, not
only to stored bytes.

**SIG-PUB-016 (MUST).** Redaction MUST be **irreversible in the published artifact** — no
black-box overlays on extractable text, which is a recurring and embarrassing failure mode in this
field.

### 43.8 Jurisdiction-conditional publication

**SIG-PUB-017 (MUST).** Publication rules MUST be **jurisdiction-conditional**. A single global
rule is not available: data-protection regimes in some jurisdictions constrain publishing even
public-body employee names, while others treat the same records as presumptively public. The policy
engine MUST evaluate the jurisdiction of the data subject and of the record's origin.

---
