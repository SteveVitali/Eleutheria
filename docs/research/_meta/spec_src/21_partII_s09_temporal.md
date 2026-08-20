## 9. Temporal semantics

The outline's requirement is stated once and is absolute: *never collapse observation time and
validity time* (OL-9.2-01). That single requirement, taken seriously, forces a richer temporal
model than the outline itself sketches. This section specifies it.

### 9.1 Why two dimensions are not enough

Conventional bitemporal modeling has two axes: **valid time** (when the fact was true) and
**transaction time** (when the database recorded it). SIG needs more, because SIG is not the
observer. SIG records what *someone else* observed, published, and SIG then retrieved.

Consider the outline's own example. A Flock portal is captured on 2026-08-20 and says
"25 cameras". The portal page says it was last updated 2026-08-01. SIG's crawler fetched it at
14:03 UTC on 2026-08-20 and the extraction ran on 2026-08-22 after a parser fix.

Collapsing these produces false statements. The only fact directly established is:

> On 2026-08-01, the Flock portal for agency X asserted a camera count of 25; SIG retrieved
> that assertion on 2026-08-20 and recorded it on 2026-08-22.

Whether 25 cameras were physically installed on any date is a *separate, weaker, derived*
question. The model must make it impossible to state the strong version by accident.

### 9.2 The five temporal dimensions

**SIG-TIME-001 (MUST).** SIG MUST model five distinct temporal dimensions. Each lives at a
specific layer; none may be substituted for another.

| # | Dimension | Question it answers | Layer | Storage |
|---|---|---|---|---|
| T1 | **Valid time** | When was this true *in the world*? | L1 claim | `valid_from`, `valid_to`, `valid_from_kind`, `valid_to_kind` |
| T2 | **Observation time** | When did the source observe or assert it? | L1 claim | `observed_at`, `observed_at_precision` |
| T3 | **Publication time** | When did the source publish the artifact carrying it? | L0 evidence | `published_at` on `evidence_artifact` |
| T4 | **Retrieval time** | When did SIG obtain the artifact? | L0 evidence | `retrieved_at` on `evidence_capture` |
| T5 | **Assertion (transaction) time** | When did SIG record this claim, and when did SIG stop asserting it? | L1 claim | `recorded_at`, `superseded_at` |

**SIG-TIME-016 (MUST).** Only **two** of the five dimensions are queryable `AS OF` axes:
T1 (valid) and T5 (assertion). T2 (observation) is an **ordering scalar** used by the resolution
engine to rank competing claims — it is not an axis you travel along. T3 and T4 belong to the
evidence layer and MUST NOT be copied onto claim rows; a claim that carries its own
`retrieved_at` has confused the artifact with the assertion. In the standard vocabulary: SIG is
**bitemporal in the query sense and tri-temporal in the record sense**. *(Corroborated by R6-F17,
R6-F19.)*

**SIG-TIME-002 (MUST).** T2 (observation) MUST NOT default to T3 (publication) or T4
(retrieval). Where a source does not state when it observed something, `observed_at` MUST be
NULL with `observed_at_unknown_reason` populated, and the resolution engine MUST treat the claim
as having observation time bounded above by T3 and below by nothing — it MUST NOT silently
substitute a timestamp.

**SIG-TIME-003 (MUST).** T1 (valid time) MUST NOT be populated by inference at ingestion. A
portal's "25 cameras" claim has `observed_at = 2026-08-01` and `valid_from`/`valid_to` NULL with
`valid_from_kind = 'unknown'`. Converting an observation into a validity interval is a
**resolution-layer** operation (§28) governed by predicate volatility (§28.3), and it happens at
L3, never at L1.

This is the single most-violated rule in comparable systems and the most important one here.

### 9.3 Encoding uncertain and open-ended time

**SIG-TIME-004 (MUST).** `valid_from` and `valid_to` MUST each be accompanied by a *kind*
discriminator drawn from a closed vocabulary. A NULL bound is never self-explanatory.

| Kind | Meaning | Example |
|---|---|---|
| `exact` | The bound is known to the stated precision. | Contract signed 2025-03-14 |
| `ongoing` | Known to still hold as of the latest evidence; no end observed. | Sharing edge still listed on the most recent portal capture |
| `unknown` | It ended or began, but SIG does not know when. | A deployment that clearly predates the earliest evidence |
| `before` | Known to be no later than the stated instant. | "Cameras were installed by the June council meeting" |
| `after` | Known to be no earlier than the stated instant. | "Installation began after contract execution" |
| `never` | The bound does not apply; the fact is atemporal. | A contract's signing date is an event, not an interval |

**SIG-TIME-005 (MUST).** `valid_to_kind = 'ongoing'` MUST NOT be interpreted as "true now". It
means "true as of the last observation, with no observed end". Every consumer — API, UI, export
— MUST render it with the observation date attached. "Currently sharing with 147 organizations"
is a non-conformant rendering; "sharing with 147 organizations as observed 2026-07-14" is
conformant. This directly implements P12 (installed is not active).

**SIG-TIME-006 (MUST).** Date precision MUST be explicit. SIG MUST support and preserve
imprecise dates using **EDTF (Extended Date/Time Format, ISO 8601-2)** semantics: year-only
(`2025`), year-month (`2025-03`), approximate (`2025-03~`), uncertain (`2025-03?`), and
intervals with unspecified components. The storage encoding is specified in §16.7. A source
that says "in early 2025" MUST NOT be stored as `2025-01-01`.

**Rationale.** Public records routinely give imprecise dates ("the department began using ALPRs
in 2019"). Silently sharpening them creates false precision, violating P4, and corrupts
lifecycle reconciliation (§29.4), which orders events by date.

### 9.4 As-of query semantics

**SIG-TIME-007 (MUST).** Every read path — API endpoint, export, and UI view — MUST accept two
independent as-of parameters and MUST default them explicitly rather than implicitly:

| Parameter | Axis | Meaning | Default |
|---|---|---|---|
| `as_of_world` | T1 | "…about the state of the world on this date" | today |
| `as_of_belief` | T5 | "…according to what SIG knew on this date" | now (latest) |

This yields the four questions the system must answer:

| `as_of_world` | `as_of_belief` | Question |
|---|---|---|
| today | now | What do we currently believe is true now? |
| past date | now | What do we now believe was true then? |
| today | past date | What did we believe, on that date, was true then? |
| past date | past date | What did we believe on date B about the state on date W? |

**SIG-TIME-008 (MUST).** The fourth form MUST work. It is what makes a published SIG citation
defensible: a journalist who cited SIG on 2026-09-01 must be able to reproduce exactly what SIG
said on 2026-09-01, even after SIG has since corrected itself. Every public page MUST expose a
belief-pinned permalink (§39.9).

**SIG-TIME-009 (MUST).** Correcting a past error MUST NOT destroy the record of having made it.
A correction sets `superseded_at` on the prior claim and inserts a new claim with
`supersedes = <prior id>` and a `correction_reason`. Queries at `as_of_belief` before the
correction MUST still return the erroneous value. This is required by P3 and by the takedown and
corrections procedure (§45.4).

### 9.5 Absence and the encoding of "unknown"

**SIG-TIME-010 (MUST).** The model MUST distinguish four epistemic states that are commonly and
wrongly conflated into NULL:

| State | Meaning | Encoding |
|---|---|---|
| `NOT_RESEARCHED` | SIG has not looked. | No claim exists; coverage record marks the subject/predicate unattempted. |
| `NO_EVIDENCE_FOUND` | SIG looked and found nothing. | A negative-coverage record naming the sources searched and when. |
| `EVIDENCE_OF_ABSENCE` | A source affirmatively asserts the thing does not exist. | A claim with a negative value and normal provenance. |
| `UNRESOLVED` | Evidence exists and disagrees; no resolution is defensible. | An L3 resolution row with outcome `UNRESOLVED` and the dissenting claims. |

**SIG-TIME-011 (MUST).** `NO_EVIDENCE_FOUND` MUST record *which* sources were searched, because
"not in the Atlas" and "not in the Atlas, not in any portal, and not in three years of council
minutes" are very different statements. This is the mechanism by which the outline's negative-
claims doctrine (OL-9.4-01, OL-9.4-02) becomes queryable rather than editorial.

**SIG-TIME-012 (MUST).** The API and UI MUST both render these four states distinguishably
(OL-9.4-03). Rendering `NOT_RESEARCHED` identically to `NO_EVIDENCE_FOUND` is non-conformant.

### 9.6 Temporal invariants

**SIG-TIME-013 (MUST).** The following MUST be enforced as database constraints or as pipeline
data-quality checks that fail the run, not as application-level conventions:

| Invariant | Rule |
|---|---|
| TI-1 | `valid_from <= valid_to` when both are `exact`. |
| TI-2 | `recorded_at <= superseded_at` when superseded. |
| TI-3 | `observed_at <= published_at` when both known, allowing a configurable tolerance for clock skew and time-zone-free source dates. |
| TI-4 | `published_at <= retrieved_at` when both known, same tolerance. |
| TI-5 | A claim MUST NOT have `observed_at` in the future relative to `recorded_at`. |
| TI-6 | For predicates declared mutually exclusive (§13.4 lifecycle states), the resolved intervals for one subject MUST NOT overlap at L3. Overlap at L1 is legal and is a contradiction, not an error. |
| TI-7 | A `supersedes` chain MUST be acyclic and MUST terminate. |
| TI-8 | Every claim MUST have at least one of `observed_at`, `published_at`, or an explicit `temporally_unanchored` flag with a reason. A claim floating free of all time is a data-quality failure. |

**SIG-TIME-014 (MUST).** TI-6's distinction is essential and is easy to get backwards.
*Contradictory claims at L1 are expected and are the point of the system.* Only the **resolved**
view at L3 must be internally consistent, and where it cannot be, it resolves to `UNRESOLVED`
rather than picking arbitrarily (P4, OL-6.5-01).

### 9.7 Multilingual and locale-sensitive temporal data

**SIG-TIME-015 (MUST).** All timestamps MUST be stored in UTC with the original source
representation preserved alongside. Source documents state dates in local time and in local
formats (`14/03/2025` is ambiguous between March 14 and unparseable depending on locale). The
raw string MUST be preserved per P2, and the parsed value MUST record the assumed locale and
time zone so that a later correction is possible.

---
