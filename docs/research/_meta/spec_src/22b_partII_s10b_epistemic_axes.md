### 10.4 Source reliability `R` — a property of the publisher, not the claim

**SIG-EPIS-013 (MUST).** The outline's Tier A–F (OL-9.1) MUST be retained as shorthand but MUST be
**redefined as a genre scale, not a reliability scale**, and crossed with three further axes before
it drives any resolution.

**The correction, stated plainly.** OL-9.1-01 places "signed contracts" and "direct field
observation" together in Tier A. But a signed contract is authoritative about what was *purchased*
and says nothing about what is switched on today; a field observation is authoritative about what
was *on a pole last Tuesday* and says nothing about who owns it. These artifacts are not equally
reliable — they are **reliable about different things**. Tier A therefore splits across two very
different reliability values once directness is factored out. *(R13; this is the correction the
outline most needs.)*

**SIG-EPIS-014 (MUST).** `R` MUST be assigned **per source in the registry**, with a written
justification, reviewed on a schedule — never re-judged per claim.

| `R` | Definition | Admiralty | Outline tier | Examples |
|---|---|---|---|---|
| `R1` | Legally-operative or system-of-record artifact produced by the party with authority and consequences for error | A | A | Executed contract; court filing; invoice; official device inventory; government open-data release |
| `R2` | First-party statement by the operating or vendor organization under its own name | B | A/B | Transparency portal page; agency policy PDF; council agenda packet; vendor or agency press release |
| `R3` | Reviewed specialist dataset with a published, checkable methodology | C | C | EFF Atlas; HIBF processed exports; Accountability Atlas; Eyes on Flock aggregations |
| `R4` | Professional reporting or research with editorial accountability but no published record-level method | C/D | D | Investigative article; academic paper; NGO report |
| `R5` | Community/volunteer observation from a structured collection process, individually unreviewed | D/E | E | An individual OSM/DeFlock node; a community photo report |
| `R6` | Heuristic, automated, or model-generated candidate with unresolved entity matching | F | F | RF/OUI match; LLM extraction; fuzzy name match |

**SIG-EPIS-015 (MUST).** A separate boolean `reliability_provisional` MUST exist for genuinely
**novel** sources, defaulting them to `R5` with the flag set. Novelty is not unreliability, and
conflating them (as a naive reading of Admiralty "F" would) unfairly penalizes new civic projects.

**SIG-EPIS-016 (MUST NOT).** SIG MUST NOT score a claim's *plausibility* against a prior
expectation of how much surveillance an agency "should" have. That is an editorial position, not a
measurement, and it would make the system's output a function of its authors' assumptions.

### 10.5 Claim directness `D` — the (genre × predicate) matrix

**SIG-EPIS-017 (MUST).** `D` MUST be read from a **published, versioned matrix** with one row per
artifact genre and one column per predicate. This is where "a Tier A contract is weak evidence for
current camera count" is encoded mechanically rather than left to judgment.

| `D` | Meaning |
|---|---|
| `D1` | The artifact is the authoritative record **of the fact itself** |
| `D2` | A first-party report of the fact |
| `D3` | Secondhand report, or a close proxy |
| `D4` | Establishes a *related* fact from which the target is a short inference |
| `D5` | Bears on the target only through a modelling assumption |
| `D6` | **Non-probative for this predicate — excluded from the admissible set** |

Illustrative rows (the full matrix ships with the ruleset):

| Artifact genre | `contract_signed_date` | `contracted_device_count` | `active_device_count` | `retention_days` | `configured_sharing_partner` |
|---|---|---|---|---|---|
| Executed contract PDF | **D1** | **D1** | D5 | D4 / D6 | D6 |
| Invoice | D3 | D2 | D4 | D6 | D6 |
| Transparency portal snapshot | D6 | D5 | **D1** | **D1** | **D1** |
| Council minutes / agenda packet | D2 | D2 | D4 | D3 | D4 |
| Agency written policy | D6 | D6 | D6 | **D2** (policy value) | D3 (declared) |
| OSM node set (field observation) | D6 | D5 | D3 (lower bound only) | D6 | D6 |
| Audit-log export | D6 | D6 | D4 | D6 | D4 (proves use, not configuration) |
| News article | D3 | D3 | D3 | D3 | D3 |
| Vendor default-settings page | D6 | D6 | D6 | D5 | D6 |

**SIG-EPIS-018 (MUST).** Two consequences are normative:

1. **A Tier-A contract is `D5` for `active_device_count`** and therefore cannot beat a `D1` portal
   snapshot on that predicate, regardless of tier. This discharges OL-9.1's requirement
   mechanically instead of rhetorically.
2. **`D6` is an admissibility filter, not a weight.** A portal snapshot contributes *nothing* to
   `contract_signed_date` — it is not weak evidence, it is not evidence. Excluding it is what
   prevents the resolver from ever emitting "the contract was signed around July 2026 (portal)."

### 10.6 Integrity `I`, currency `C`, and the composed weight `W`

**SIG-EPIS-019 (MUST).** `I` is assigned **mechanically** by the pipeline:
`I1` content-addressed archive stored with checksum, fetch timestamp, and HTTP status;
`I2` live URL recorded and retrievable at ingest but no durable archive;
`I3` secondhand transcription, screenshot without provenance, or an artifact SIG cannot re-fetch.

**SIG-EPIS-020 (MUST).** `C` MUST be derived **at query time** from the predicate's volatility class
and the claim's `observed_at` (§28.3). It MUST NOT be stored on the claim: a claim's currency
changes without the claim changing, which is precisely why resolutions must be recomputed rather
than cached indefinitely (§28.7).

**SIG-EPIS-021 (MUST).** Axes MUST compose by a **published ordinal table**, never by arithmetic on
invented numbers:

```
base:        R1→W4   R2→W3   R3→W3   R4→W2   R5→W2   R6→W1
directness:  D1 0    D2 0    D3 −1   D4 −2   D5 −2 (cap W1)   D6 EXCLUDE
integrity:   I1 0    I2 −1   I3 −2
currency:    C1 0    C2 −1   C3 −2   C4 −2 (cap W1)

upgrade, at most +1 total, never above W4:
  +1  machine-readable structured export AND extraction_confidence = EXACT
  +1  independently field-verified by a SIG curator with a logged verification event

W = clamp(W0..W4)
```

`W4` dispositive · `W3` strong · `W2` moderate · `W1` weak · `W0` non-probative (retained for
display, never resolving).

**SIG-EPIS-022 (MUST).** Free-form numeric confidence is **prohibited** unless calibrated against a
labelled set with published calibration (OL-9.3-01). Weight classes are ordinal and explainable;
"87% confidence" is neither.

### 10.7 The confidence vocabulary: three orthogonal fields, not one

**SIG-EPIS-023 (MUST).** SIG MUST publish **three orthogonal fields plus a status**, never one
fused token:

```
resolution_status : RESOLVED | UNRESOLVED | SUPERSEDED | WITHDRAWN
support           : CONFIRMED | STRONGLY_SUPPORTED | PROBABLE | WEAKLY_SUPPORTED | UNSUPPORTED
agreement         : UNCONTESTED | MINOR_DISAGREEMENT | CONTESTED | IRRECONCILABLE
currency          : CURRENT | AGING | STALE | HISTORICAL
```

**Why this replaces the outline's list.** OL-9.3-02 proposes
`confirmed / strongly supported / probable / unverified / contradicted / historical`. Four of those
are *support* levels, one is an *agreement* level, and one is a *currency* level. A single flat
enum therefore cannot express **"strongly supported but contested"** or **"confirmed but
historical"** — and in this domain those are the common and interesting cases. The three-field
model is a strict superset: every outline label is recoverable from a `(support, agreement,
currency)` triple. *(Corrects OL-9.3-02 while preserving all six labels.)*

`support` is computed **only** from the winning value's evidence:

| `support` | Condition |
|---|---|
| `CONFIRMED` | Winner has a `W4` claim, **or** ≥2 independent, method-distinct classes each at `W3`+ |
| `STRONGLY_SUPPORTED` | A `W3` claim, or ≥2 independent classes at `W2`+ |
| `PROBABLE` | Exactly one class at `W2`+ |
| `WEAKLY_SUPPORTED` | Best claim is `W1` |
| `UNSUPPORTED` | No admissible claim above `W0` (always co-occurs with `UNRESOLVED`) |

`agreement` is computed **only** from the dissent structure:

| `agreement` | Condition |
|---|---|
| `UNCONTESTED` | All admissible claims map to the same canonical value |
| `MINOR_DISAGREEMENT` | Dissent exists but is all `W1`/`W0`, or (numeric) within the predicate's tolerance |
| `CONTESTED` | Dissent at `W2`+ from ≥1 independent class |
| `IRRECONCILABLE` | Dissent at `W3`+ from ≥2 independent classes, or an open BLOCKING contradiction |

**SIG-EPIS-024 (MUST).** The API MUST always return all four fields. A one-word presentation label
MAY be derived from a published lookup for UI density, but MUST NEVER be the primary
representation.

**SIG-EPIS-025 (MUST).** Generated rationale text MUST NOT place a support term and an agreement
term in the same sentence. Mixing them is what produces sentences like "probably contested", which
readers cannot parse into a defensible meaning.

### 10.8 Source dependence

**SIG-EPIS-026 (MUST).** SIG MUST **declare** copying rather than infer it. Every claim carries
`derived_from_claim_ids` / `derived_from_source`, populated at ingest.

**Why SIG can do what the truth-discovery literature cannot.** Published data-fusion methods must
*infer* source dependence from a snapshot, because they cannot see inside their sources. SIG builds
its own intake and therefore **knows** which upstream a claim came from. This is a strict advantage
and SIG must exploit it: declared dependence is exact where inferred dependence is statistical.

**SIG-EPIS-027 (MUST).** Claims sharing an upstream origin MUST be grouped into a single
**independence class**, and corroboration MUST be counted **per class, not per claim**. Three
projects that all scraped one portal are one piece of evidence, not three.

**SIG-EPIS-028 (MUST).** Claims produced by the **same collection method** across different sources
MUST receive only partial independence credit, because a shared method shares a failure mode.

**SIG-EPIS-029 (MUST).** An **undeclared-copying detector** MUST run: claims from nominally
independent sources that match implausibly closely — including matching each other's errors — MUST
raise a review flag. Matching errors are near-proof of copying and are the cheapest available
signal.

### 10.9 Curated indexes need not be normalized

**SIG-EPIS-030 (MUST).** SIG MUST be able to hold a curated source index *as an index*, without
normalizing its entries into claims (OL-2E-AL-02). A well-maintained bibliography of reporting is
valuable on its own terms, and forcing premature normalization would both destroy that value and
manufacture low-quality claims.

---
