# Part V — Resolution, reconciliation, and inference

## 27. Entity resolution pipeline

Specified at §14.6–14.8. The operational requirements that belong to the pipeline rather than the
model:

**SIG-RECON-001 (MUST).** ER MUST run as a distinct pipeline stage between `normalize()` and
`load()`, with its own run record, its own quality report, and its own rollback path.

**SIG-RECON-002 (MUST).** ER MUST be **re-runnable** over historical claims without destroying the
prior clustering. A re-clustering produces new `same_as` assertions with a new ruleset version; it
does not silently move claims between entities.

**SIG-RECON-003 (MUST).** No network-analytics surface may ship before the §14.7 quality gates
pass, and every centrality or hub statistic MUST carry an ER-quality disclosure in the UI (P6).

---

## 28. The reconciliation engine

This is the intellectual core of the project. The outline states the requirement (outline §6.2, §6.5, §22.1); this section makes it executable.

### 28.1 Rule-based and auditable, by requirement

**SIG-RECON-004 (MUST).** Resolution MUST be **deterministic, rule-based, and explainable**. It
MUST NOT use an unsupervised truth-discovery model, a learned scorer, or any procedure whose output
cannot be traced to a named rule.

**Rationale, stated because the alternative is tempting.** The truth-discovery literature offers
elegant iterative source-weighting methods. They are the wrong tool here for three reasons: their
weights are not explainable to a journalist defending a claim; they assume source independence that
this ecosystem violates (§10.8); and they optimize for accuracy against a hidden truth, whereas
SIG's obligation is to be *defensible about its reasoning*, which is a different objective. A rule
that is 3% less accurate and fully explainable is the better instrument for this project.

**SIG-RECON-005 (MUST).** The ruleset MUST be **data, not code** — versioned, diffable, testable,
and separately attributable from the resolver implementation (SIG-STORE-017).

### 28.2 The algorithm

**SIG-RECON-006 (MUST).** `RESOLVE(subject, predicate, as_of_world, as_of_belief, ruleset)` MUST
execute these phases in order:

```
Phase 0  GATHER
  0.1  claims := {c : c.subject = S, c.predicate = P, c.sys_period contains as_of_belief}

Phase 1  ADMISSIBILITY            (admissibility is prior to weight)
  1.1  drop if review_status ∈ {retracted, withdrawn}
  1.2  drop if valid_period does not intersect as_of_world
  1.3  drop if D(genre(c), P) = D6                    ← non-probative for THIS predicate
  1.4  drop if superseded by a later claim from the SAME source with the same valid_time
  1.5  if empty → UNRESOLVED(NO_EVIDENCE)

Phase 2  CANONICALIZE
  2.1  canonicalize units, enum casing, entity identity, date granularity
  2.2  if a claim cannot be canonicalized → emit Contradiction(VALUE_DOMAIN_MISMATCH), drop
  2.3  if P is a count predicate and claims disagree on count_basis
       (contracted vs installed vs active vs mapped vs reported):
         emit Contradiction(PREDICATE_CONFLATION); drop the mismatched claims
         ← the §29.1 guard: NEVER silently compare different things

Phase 3  WEIGHT
  3.1  W(c) := compose(R, D, I, C)                    ← §10.6
  3.2  W0 claims leave the resolving set but are retained for display

Phase 4  INDEPENDENCE
  4.1  group claims into independence classes          ← §10.8
  4.2  W(class) := max W within the class
  4.3  per candidate value: supporting classes, method breadth, best weight

Phase 5  STRATEGY
  5.1  apply the predicate's resolution strategy       ← §28.4
  5.2  produce a TOTAL order over candidates

Phase 6  AMBIGUITY TEST                                ← §28.5
  6.1  if AMBIGUOUS → UNRESOLVED(first triggering condition, candidates, rationale)

Phase 7  EMIT
  7.1  winner, support, agreement, currency            ← §10.7
  7.2  supporting / dissenting / excluded claim ids with exclusion reasons
  7.3  independence classes, rules fired, ruleset version
  7.4  input_digest = hash(sorted claim ids + content hashes)
  7.5  as_of_world, as_of_belief, computed_at
```

**SIG-RECON-007 (MUST).** The ranking MUST be a **total order**. The universal final tie-break,
applied after every strategy's own criteria are exhausted, is:

```
(weight desc, method_breadth desc, observed_at desc, source_registry_rank asc, claim_id asc)
```

Since `claim_id` is stable, the order is fixed forever. **There MUST be no random tie-break
anywhere in the system** — a resolution that could differ between two runs over identical inputs is
not reproducible and cannot be cited.

### 28.3 Predicate volatility and currency

**SIG-RECON-008 (MUST).** Every predicate MUST carry a volatility class and half-life `h`. Currency
is derived at query time:

```
age = as_of_world − observed_at
C1 CURRENT      age ≤ 0.5h
C2 AGING        0.5h < age ≤ 1.0h
C3 STALE        1.0h < age ≤ 3.0h
C4 HISTORICAL   age > 3.0h        (IMMUTABLE predicates: h = ∞, always C1)
```

**SIG-RECON-009 (MUST).** The volatility table is ruleset data and MUST be recalibrated once SIG
has observed enough change-rate data to measure it. Initial assignment:

| Predicate class | Volatility | `h` |
|---|---|---|
| Contract dates, contract value, contracted quantity | IMMUTABLE | ∞ |
| Organization legal name, jurisdiction, ORI | GLACIAL | 10 y |
| Vendor of product, product capabilities | GLACIAL | 5 y |
| `deployment_exists` | SLOW | 3 y |
| `asset_operator` attribution | SLOW | 3 y |
| Written policy values | SLOW | 2 y |
| Fixed asset location | SLOW | 2 y |
| `asset_exists_at_location`, procurement status | MODERATE | 12 mo |
| `configured_retention_days`, vendor default retention | MODERATE | 9 mo |
| `operational_state`, `active_device_count`, `installed_device_count` | FAST | 6 mo |
| `configured_sharing_partner_set` | FAST | 4 mo |
| National/state lookup toggles, hotlist configuration | VOLATILE | 2 mo |
| Windowed usage counts | VOLATILE | 1 mo |

**SIG-RECON-010 (MUST).** For IMMUTABLE and GLACIAL predicates, **recency MUST NOT break a tie**.
A newer claim about a 2019 signing date has no advantage from being newer.

**SIG-RECON-011 (MUST).** **Windowed predicates are indexed, not stale.** A 30-day search count for
July does not become "stale" in August — it becomes *a value for July*. Windowed predicates carry
explicit window bounds in `valid_period` and are **exempt from currency downgrade for the window
they describe**. What decays is the *current rate*, which is a different, derived predicate with its
own volatility. Conflating these produces "412 searches in the last 30 days" on a dossier whose
underlying data is nine months old — a specific, avoidable, and highly visible failure.

### 28.4 Per-predicate strategies

**SIG-RECON-012 (MUST).** Every predicate MUST be assigned a resolution strategy in the ruleset:

| Strategy | Applies to |
|---|---|
| `latest_observation_wins` | FAST/VOLATILE operational state, active counts, sharing sets |
| `authoritative_source_wins` | Legal facts: contract dates, values, statutory citations |
| `interval_union` | Coverage and validity spans where sources report partial periods |
| `interval_intersection` | Facts requiring simultaneous support |
| `max_support` | Categorical facts with no clear authority ordering |
| `never_resolve` | Predicates SIG records but deliberately does not adjudicate (e.g. a contested data-controller assertion, §12.4) |

**SIG-RECON-013 (MUST).** A predicate with no assigned strategy MUST NOT be resolvable
(SIG-ONTO-067). Silence in the ruleset produces `UNRESOLVED`, never a guess.

### 28.5 The ambiguity test — when SIG refuses to answer

**SIG-RECON-014 (MUST).** `UNRESOLVED` MUST be returned when any of the following holds, evaluated
**in order** so the reason is deterministic:

| id | Condition | Why |
|---|---|---|
| `U0` | No admissible claims after Phase 1 | No evidence — distinct from balanced evidence |
| `U1` | Best weight ≤ `W1` | Nothing above weak; a tip alone never resolves |
| `U2` | Top and second have equal weight, disjoint independence classes, and equal method breadth | A genuine standoff between equal independent evidence |
| `U3` | The winner has exactly one class, and a dissenting method-distinct class is at `W2`+ | One source versus one source is never resolvable by fiat |
| `U4` | Numeric predicate; relative spread exceeds the predicate's tolerance; nothing dispositive | Numbers too far apart to pick between |
| `U5` | Winner's currency is STALE/HISTORICAL and the predicate is MODERATE/FAST/VOLATILE | **The best answer is too old to assert about a changing quantity** |
| `U6` | Claims were dropped for `count_basis` mismatch and fewer than two survive | The remainder cannot be compared |
| `U7` | An open `Contradiction` on this pair has severity BLOCKING | A human flagged it as not-safe-to-publish |
| `U8` | Agreement would be IRRECONCILABLE and support below CONFIRMED | Strong unreconciled dissent beats a merely-strong winner |

**SIG-RECON-015 (MUST).** **`U5` is the rule the outline lacks entirely, and it is essential.** It
is what stops SIG from publishing "42 active cameras" in 2026 on the strength of a 2024 contract —
*even with no dissent at all, even from a Tier-A source*. Silence plus age is not a resolution. In
this domain, where deployments change quietly and constantly, an unchallenged stale number is the
most likely way for SIG to publish something false.

**SIG-RECON-016 (MUST).** On `U5`, SIG MUST publish the stale value as `last_known` **with its
date**, not suppress it. "38 as of 2026-07-01, not since verified" is useful; a blank is not.

**SIG-RECON-017 (MUST).** `UNRESOLVED` is **not an error and MUST NOT be hidden**. It renders as an
explicit finding with all candidate values, their evidence, and an automatically generated research
task (§33). Declining to grade is a standards-compliant output, not a failure.

### 28.6 Independence and dependence discounting

Specified at §10.8. The engine-side requirement:

**SIG-RECON-018 (MUST).** Corroboration MUST be counted per independence class and per distinct
collection method, never per claim. A candidate value supported by five claims from one class has
the support of **one** class.

### 28.7 Recomputation, versioning, immutability

**SIG-RECON-019 (MUST).** Resolutions MUST be recomputed when: a new claim lands on the pair; a
claim is superseded; the ruleset version changes; or **currency crosses a class boundary** — the
last of which happens with no data change at all, purely through the passage of time, and is the
reason resolutions cannot be cached indefinitely.

**SIG-RECON-020 (MUST).** A resolution MUST be reproducible from `(claims + ruleset_version +
resolver_version + as_of pair)`, verified by the stored `input_digest`. CI MUST regenerate a sample
and assert a match (SIG-STORE-018).

**SIG-RECON-021 (MUST).** Resolutions MUST NEVER be edited in place. A new resolution supersedes
the old one in transaction time.

### 28.8 Rationale generation

**SIG-RECON-022 (MUST).** Every resolution MUST carry a human-readable rationale generated from a
**versioned template** filled from the resolution's own structured fields. It MUST name which
sources mattered, and which corroborate or conflict.

Worked examples of conformant rationales:

> "38, as reported by the agency's transparency portal captured 2026-07-01. The portal is the most
> direct available source for currently active devices. The executed contract's figure of 42 is
> recorded separately as the contracted quantity; it is not evidence of the active count."

> "Unresolved. The contract specifies 30 devices and the portal reported 28 on 2026-07-01, but the
> two figures describe different quantities and no source establishes the active count directly.
> Both values are shown with their evidence."

> "Unresolved, stale. The most recent evidence for this deployment's operational state is 31 months
> old, and operational state typically changes within about six months. Last known: active, as of
> 2024-01-12."

> "Confirmed. Three independent sources using different collection methods — an executed contract,
> council minutes, and a vendor press release — agree on a signing date of 2025-03-14."

> "Contested. The agency's written policy prohibits immigration-related queries, while a
> configuration export dated 2026-05-02 shows an immigration hotlist enabled. Both are first-party
> evidence and neither supersedes the other; the disagreement is the finding."

**SIG-RECON-023 (MUST).** Every rationale template MUST pass a committed template test asserting
that its rendered output: (a) contains no unresolved placeholder; (b) names at least one source; (c)
attributes every value to a source or to a named rule; (d) contains no support term and agreement
term in the same sentence (SIG-EPIS-025); and (e) uses no evaluative adjective from the prohibited
list in the style guide (§41). Template changes MUST re-run this suite.

*Rationale (not itself testable).* The target is that a journalist can quote the rationale verbatim
without adding interpretation. Clauses (a)–(e) are the mechanical properties that make that
achievable.

### 28.9 Human override

**SIG-RECON-024 (MUST).** A curator MAY pin a resolution. The override is itself recorded with
`decided_by` and a mandatory `override_rationale`, is displayed in the UI **as an editorial act**,
and is subject to the same review and correction process as any other claim (SIG-STORE-019).

**SIG-RECON-025 (MUST).** An override MUST NOT delete or hide the algorithmic result. Both are
shown, so a reader can see that a human disagreed with the rule and why.

---
