# R13 — Reconciliation, Confidence, and the Inference Layer

**Workstream:** R13
**Researched:** 2026-08-20
**Researcher:** claude-opus-5 (SIG research agent R13)
**Outline sections covered:** §6.2, §6.5, §8.12, §8.15, §8.16, §9 (all), §11 (all), §12, §19, §22.1, §22.2, §22.4, §22.5, Appendix B
**Outline questions answered:** Q19 (partial — OSM history representation for freshness), Q21 (partial — claim-level provenance + bitemporal requirements), Q28 (partial — where inference must produce review queues rather than writes), Q33 (partial — how corrections flow upstream without laundering inference into OSM)
**Confidence in this file overall:** high for the literature findings and the OSM/portal measurements; medium for the numeric thresholds proposed in the algorithm (they are defensible starting values that must be calibrated against a real corpus, and the design makes them versioned data precisely so they can be changed without changing code)

---

## 0. What this file is

This is the design of SIG's **reconciliation engine**: the component that takes the set of mutually
inconsistent `Claim` records attached to a `(subject, predicate)` pair and produces a *resolved view*
that a journalist can quote, a researcher can reproduce, and an adversary cannot easily impeach.

The outline's own framing is the constraint (§22.1, §22.2): there is no single source of truth, and the
project's authority derives from provenance, not omniscience. The engine below is built so that every
published value is a **function** — deterministic, versioned, replayable — of `(claims, ruleset)`, and so
that the function's output includes its own justification.

Structure:

- §1 — Findings from the truth-discovery / data-fusion literature (F13.1–F13.12)
- §2 — Findings from calibrated-uncertainty and evidence-grading standards (F13.13–F13.22)
- §3 — Findings from SIG's actual source ecosystem (F13.23–F13.34)
- §4 — **Design: the multi-axis source model** and the Admiralty ↔ Tier A–F reconciliation
- §5 — **Design: predicate volatility** and the decay table
- §6 — **Design: source dependence** and independence classes
- §7 — **Design: the resolution algorithm** (pseudocode) and the confidence vocabulary
- §8 — **Design: per-predicate strategy assignment**
- §9 — **Design: the nine reconciliation workflows**
- §10 — **Design: the inference catalog**
- §11 — **Design: the `Contradiction` entity** and the detector→task contract
- §12 — **Design: coverage and quality metrics**, including the capture–recapture verdict
- §13 — Open questions
- §14 — Spec requirements emitted (`REQ-R13-nn`)

Design sections are normative for `docs/2_canonical_design_spec.md`. Findings sections are evidence.

---

# 1. Findings — truth discovery, data fusion, copy detection

### F13.1 — Naive majority voting is provably wrong under copying, and the canonical fix is a Bayesian copy detector

**Claim:** Dong, Berti-Équille & Srivastava (VLDB 2009) formalize source dependence and show that
majority voting over sources that copy from one another systematically elects the copied value, and
they give a closed-form Bayesian test for dependence that keys on *shared false values*.
**Status:** VERIFIED
**Evidence:** `http://www.vldb.org/pvldb/vol2/vldb09-pvldb47.pdf` — retrieved and text-extracted in full.
The motivating example (Table 1) is five sources on researcher affiliations where S3 is copied by S4 and
S5, so "a naive voting would consider them as the majority and so make wrong decisions for three
researchers." The core intuition is stated as: "for a particular object, there are often multiple distinct
false values but usually only one true value. Sharing the same true value does not necessarily imply
sources being dependent; however, sharing the same false value is typically a rare event when the sources
are fully independent." The dependence probability is Eq. (8):

```
Pr(S1 ~ S2 | Φ)
  = [ 1 + ((1-α)/α) · ((1-ε)/(1-ε+cε))^kt · (ε/(cn+ε-cε))^kf · (1/(1-c))^kd ]^-1
```

with `kt` = count of objects where the two sources agree on the *true* value, `kf` = count where they
agree on a *false* value, `kd` = count where they differ; `α` = prior probability of dependence,
`c` = probability a copier's value was copied, `ε` = independent error rate, `n` = number of false values
in the domain. Vote counting is then discounted: for a value `v`, total vote is
`Σ_{S ∈ So(v)} (1-c)^d(S,G)` over the dependence graph `G` (Eq. 9), estimated in `O(s² log s)` by
`I(S) = Π_{S0 ∈ Pre(S)} (1 - c·P(S ~ S0))` (Eq. 11). The paper's three stated assumptions are
independent values, independent copying, and no loop copying.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG must *never* count "N sources agree" without first partitioning those
sources into independence classes. But — see F13.4 — SIG's situation is strictly easier than the paper's,
because SIG's ingestion pipeline *knows* which source it scraped from. The Bayesian test should be
implemented as a **detector for undeclared copying** (emitting a `Contradiction`/task), never as a silent
re-weighter of published values.
**Outline delta:** EXTENDS §6.2 and §6.5 — the outline's worked example ("portal says 20, contract says
25, city presentation says 22, OSM has 18") tacitly assumes four independent sources. In SIG's real
ecosystem several of these are derivative (see F13.24, F13.26), and the outline does not say so.

### F13.2 — TruthFinder's own authors treat source independence as a known-false assumption patched by a fudge factor

**Claim:** TruthFinder (Yin, Han & Yu) computes a fixpoint between website trustworthiness and fact
confidence, and explicitly introduces a "dampening factor" because the independence assumption fails.
**Status:** VERIFIED
**Evidence:** `http://web.cs.ucla.edu/~yzsun/classes/2014Spring_CS7280/Papers/Trust/kdd07_xyin.pdf` —
extracted. Confidence of a fact `s(f) = 1 - Π_{w ∈ W(f)} (1 - t(w))`; trustworthiness score
`τ(w) = -ln(1 - t(w))`; confidence score `σ(f) = Σ_{w ∈ W(f)} τ(w)` (Lemma 1); adjusted confidence
`σ*(f) = σ(f) + ρ · Σ_{o(f')=o(f)} σ(f') · imp(f' → f)` with negative `imp` for conflicting facts. The
paper then states plainly: "One problem with the above model is we have been assuming different web sites
are independent with each other. This assumption is often incorrect because errors can be propagated
between web sites… if a fact f is provided by five web sites with trustworthiness of 0.6 (which is quite
low), f will have confidence of 0.99! But actually some of the web sites may copy contents from others.
In order to compensate for the problem of overly high confidence, we add a dampening factor γ."
**Retrieved:** 2026-08-20
**Implication for the spec:** The multiplicative "1 − Π(1 − t)" corroboration form is exactly the trap SIG
must avoid: it converts three weak, correlated observations into near-certainty. SIG's corroboration rule
must be **bounded and ordinal** (at most one confidence step up, and only across independence classes),
not multiplicative.
**Outline delta:** CONFIRMS §9.3's instruction to avoid opaque numeric confidence — this is a concrete
mechanism by which a numeric confidence becomes indefensible.

### F13.3 — Empirically, sophisticated unsupervised truth discovery barely beats majority voting, and both fail in exactly SIG's regime

**Claim:** A 12-algorithm reimplementation and evaluation found that majority voting is within a small
margin of the best truth-discovery algorithms on real data, that several algorithms are non-repeatable,
and that *all* methods fail when there are few conflicts per item and many unreliable sources.
**Status:** VERIFIED
**Evidence:** `https://arxiv.org/pdf/1409.6428` (Waguih & Berti-Équille, "Truth Discovery Algorithms: An
Experimental Evaluation," QCRI TR, May 2014) — extracted. Conclusions verbatim: "(1) Stability and
repeatability of the results are significant issues for LTM and 3-ESTIMATES… (3) All methods do not
perform significantly better than random guessing when the data set has few conflicts per data item and a
large number of non reliable sources (pessimistic scenarios). (4) Although MAJORITY VOTING can be
misleading when sources are dependent, it remains the most efficient and scalable for a minor degradation
in precision compared to the other methods that are from 9 (TRUTHFINDER) to 120 times (ACCU) slower."
Their per-dataset tables confirm it numerically: on *Book*, majority voting precision 0.9804 vs TruthFinder
0.9777; on *Population*, 0.8206 vs 0.8505; on *Weather*, 0.6305 vs 0.6443.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the decisive empirical argument for SIG's architecture. SIG's regime is
the "pessimistic scenario": typically 2–5 claims per `(subject, predicate)`, drawn from a small number of
sources whose reliability cannot be estimated from data because there is no ground truth. Unsupervised
truth discovery buys ≈0–3 points of precision, costs all explainability, and is *unstable across runs* — a
fatal property for a public-interest project whose numbers get quoted in city council meetings. SIG uses a
**rule-based resolver**.
**Outline delta:** CONFIRMS §9.3 and §19.4 with hard evidence; the outline asserts the preference for
explainability on principle, and this finding shows the accuracy cost of that preference is near zero.

### F13.4 — Correlation between sources is broader than copying: shared *method* creates positive correlation without any copying

**Claim:** Pochampally et al. (SIGMOD 2014) show that sources can be correlated because they apply common
extraction rules or cover complementary domains, not only because one copies another, and they model
source quality as precision *and recall*, with recall scoped to the source's domain.
**Status:** VERIFIED
**Evidence:** `https://lunadong.com/publication/fusionWCorr_sigmod.pdf` (URL discovered via
`https://lunadong.com/publications`) — extracted. Abstract: "correlation between sources can be much
broader than copying: sources may provide data from complementary domains (negative correlation),
extractors may focus on different types of information (negative correlation), and extractors may apply
common rules in extraction (positive correlation, without copying)." Source quality is
`p_i = Pr(t | S_i ⊨ t)` and `r_i = Pr(S_i ⊨ t | t)`, with the caveat: "The recall of a source should be
calculated with respect to the 'scope' of its input… we may penalize the recall of S for providing only 1
out of the 3 professions of Obama, but should not penalize the recall of S for not providing any profession
for Bush."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG has a textbook case of *method* correlation with no copying: two
independent field-mapping efforts both photograph cameras visible from a public road, so both miss the
same rear-facing, tree-obscured, and private-property devices. Declared-lineage independence classes
(§6) are therefore **not sufficient** — SIG needs a second, coarser grouping by `collection_method`, and
corroboration across two sources of the same method must be discounted. The scoped-recall point is the
formal statement of the outline's §9.4 negative-claims rule: a source's silence is only evidence within its
declared scope.
**Outline delta:** EXTENDS §9.4 — the outline says absence from a dataset "means little"; the correct
formulation is that absence is evidence exactly to the extent that the item lies inside the source's declared
collection scope, and SIG must therefore record a machine-readable `collection_scope` per source.

### F13.5 — Google's Knowledge Vault achieves calibrated probabilities only by assuming a large curated KB as training labels

**Claim:** Knowledge Vault's "calibrated probabilities of fact correctness" are produced by supervised
classifiers trained on labels derived from Freebase under a *local closed world assumption*.
**Status:** VERIFIED
**Evidence:** `https://lunadong.com/publication/kv_kdd.pdf` — extracted. "we use Freebase as our source of
prior data"; §2.2 "Local closed world assumption (LCWA): All the components of our system use supervised
machine learning methods to fit probabilistic binary classifiers… For (s,p,o) triples that are in
Freebase, we assume the [triple is true]… we could [assume all others false] (closed world assumption),
but this would be rather dangerous, since we know that Freebase is very incomplete. So instead, we make
use a somewhat more refined heuristic that we call the local closed world assumption."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG cannot replicate this. There is no Freebase of surveillance
infrastructure — building one is the project. And the LCWA (if a subject has *some* values for a
predicate, other values are false) is precisely the inference §9.4 forbids: an agency having three mapped
cameras does not make a fourth camera's existence false. **SIG must not emit numeric probabilities of
correctness.** Any such number would be uncalibrated by construction.
**Outline delta:** CONFIRMS §9.3 ("Avoid opaque '87% confidence' values unless probability is actually
calibrated") and supplies the missing reason: calibration requires labeled ground truth SIG does not and
will not have.

### F13.6 — Knowledge-Based Trust is an endogenous source-quality signal, and it needs to separate extraction error from source error

**Claim:** Dong et al. (VLDB 2015) estimate web-source trustworthiness from the correctness of the facts a
source asserts, using a multi-layer model that distinguishes extraction errors from source errors.
**Status:** VERIFIED
**Evidence:** `https://arxiv.org/pdf/1502.03519` — abstract extracted: "We propose a way to distinguish
errors made in the extraction process from factual errors in the web source per se, by using joint
inference in a novel multi-layer probabilistic model… we apply it to a database of 2.8B facts extracted
from the web, and thereby estimate the trustworthiness of 119M webpages."
**Retrieved:** 2026-08-20
**Implication for the spec:** The *architectural* lesson transfers even though the algorithm does not.
SIG's `Claim` must carry an `extraction_method` and an `extraction_confidence` **separate from** source
reliability, so that "the portal's PDF parser mis-read the number" is a distinguishable failure from "the
portal is wrong." The outline's §8.16 already has `extraction_method`; this finding says the two error
channels must also be separately *reportable* in the rationale.
**Outline delta:** EXTENDS §8.16 — add `extraction_confidence` and require that extraction failure be a
distinct `Contradiction` type (`EXTRACTION_SUSPECT`) rather than a source disagreement.

### F13.7 — Truth discovery's founding principle is unsupervised source weighting, which is the property SIG must reject

**Claim:** The standard survey defines the field's general principle as mutually bootstrapping source
weights and truths without supervision, explicitly because "source reliability is usually unknown a priori."
**Status:** VERIFIED
**Evidence:** `https://arxiv.org/pdf/1505.02463` (Li, Gao, Meng, Li, Su, Zhao, Fan, Han, "A Survey on
Truth Discovery") — extracted. "As truth discovery methods usually work without any supervision, the
source reliability can only be inferred based on the data." General principle: "If a source provides
trustworthy information frequently, it will be assigned a high reliability; meanwhile, if one piece of
information is supported by sources with high reliabilities, it will have big chance to be selected as
truth." The Mount Everest example is used to argue that majority voting is wrong because Wikipedia's
minority value is correct.
**Retrieved:** 2026-08-20
**Implication for the spec:** For SIG, source reliability *is* known a priori and is a **published editorial
judgment**, not a learned parameter. A signed contract is more reliable than a tweet for the same reason a
court says so, not because an EM loop discovered it. Making reliability a curated, versioned, publicly
reviewable registry entry is both more honest and more defensible than learning it — and it is auditable by
critics, which a learned weight is not. This is the single most important architectural inversion in R13.
**Outline delta:** CONFIRMS §9.1's premise (a *declared* hierarchy) and CORRECTS the implicit assumption
in §6.5 that resolution is a scoring problem; it is a policy-application problem.

### F13.8 — Probabilistic Soft Logic is real, convex, and scalable — and its reference implementation is near-dormant

**Claim:** PSL/HL-MRFs are a mature formalism (JMLR 2017) with a Java reference implementation whose last
commit is 2024-05-08 and which publishes no GitHub releases.
**Status:** VERIFIED
**Evidence:** `https://arxiv.org/pdf/1505.04406` (Bach, Broecheler, Huang, Getoor, *JMLR* 18 (2017) 1–67,
"Hinge-Loss Markov Random Fields and Probabilistic Soft Logic") — abstract extracted; PSL is "a
probabilistic programming language that makes HL-MRFs easy to define using a syntax based on first-order
logic" with MAP inference "much more scalable than general-purpose convex optimization methods."
Repository state from `https://api.github.com/repos/linqs/psl` (2026-08-20): 315 stars, `archived: false`,
`pushed_at: 2024-06-10T15:37:44Z`, language Java; `/releases/latest` returns no release; latest tags are
`CANARY-2.3.1`-style pre-release tags; the three most recent commits are all dated 2024-05-08. Repo page
`https://github.com/linqs/psl` confirms 2,121 commits and 315 stars.
**Retrieved:** 2026-08-20
**Implication for the spec:** Do not build SIG on PSL. The formalism is sound but the ecosystem is one
research group deep, the runtime is JVM, and a ~2-year commit gap is an unacceptable dependency for
infrastructure meant to outlive a vendor. PSL's *syntax* — weighted first-order rules over soft truth
values — is nevertheless a good mental model for SIG's ruleset, and PSL is a reasonable **offline research
tool** for validating that SIG's hand-written rules aren't leaving accuracy on the table.
**Outline delta:** EXTENDS §9 — the outline does not consider probabilistic KB formalisms at all; this
records that they were considered and rejected on maintenance and explainability grounds, not on merit.

### F13.9 — DeepDive is effectively abandoned; Snorkel has pivoted to a commercial product

**Claim:** DeepDive's last release is v0.8-STABLE (2016-02-25) with last repository activity 2022-06-09;
Snorkel's last release is v0.10.0 (2024-02-27) and its README directs users to the commercial Snorkel Flow.
**Status:** VERIFIED
**Evidence:** `https://api.github.com/repos/HazyResearch/deepdive` → 1,979 stars,
`pushed_at: 2022-06-09T05:49:44Z`; `/releases/latest` → `v0.8-STABLE`, `2016-02-25T11:10:11Z`.
`https://api.github.com/repos/snorkel-team/snorkel` → 5,999 stars, `pushed_at: 2026-06-08T19:59:20Z`;
`/releases/latest` → `v0.10.0`, `2024-02-27T23:00:37Z`. Repo page `https://github.com/snorkel-team/snorkel`
carries the announcement that the team is "focusing our efforts on Snorkel Flow," described as "an
end-to-end AI application development platform."
**Retrieved:** 2026-08-20
**Implication for the spec:** Weak supervision as a *dependency* is off the table. Its *idea* — labeling
functions as inspectable code whose disagreements are themselves data — survives and is directly adopted:
SIG's resolution rules are exactly labeling functions, and its `Contradiction` objects are exactly the
disagreement matrix, except that SIG surfaces them to humans instead of marginalizing them away.
**Outline delta:** EXTENDS §9 — records the rejection with dated evidence so a future reader does not
re-litigate it.

### F13.10 — Markov Logic Networks require MCMC inference and weight learning, both of which destroy replayability

**Claim:** MLNs attach weights to first-order clauses and perform inference by MCMC over a ground Markov
network, with weights learned by optimizing pseudo-likelihood.
**Status:** PARTIALLY VERIFIED (search-result synthesis of the Richardson & Domingos 2006 *Machine
Learning* paper; the paper's landing pages at `link.springer.com` and `dl.acm.org` were identified but the
full text was not fetched, and `https://homes.cs.washington.edu/~pedrod/papers/mlj05.pdf` was located but
not retrieved)
**Evidence:** Search against `Richardson Domingos "Markov logic networks" Machine Learning 2006` returned
consistent descriptions across `https://link.springer.com/article/10.1007/s10994-006-5833-1`,
`https://www.microsoft.com/en-us/research/publication/markov-logic-networks/` and
`https://cs.uwaterloo.ca/~ppoupart/teaching/cs486-fall12/slides/cs486-lecture21.pdf`: "A Markov logic
network (MLN) is a first-order knowledge base with a weight attached to each formula (or clause)…
Inference in MLNs is performed by MCMC over the minimal subset of the ground network required for
answering the query. Weights are efficiently learned from relational databases by iteratively optimizing a
pseudo-likelihood measure."
**Retrieved:** 2026-08-20
**Implication for the spec:** MCMC inference means the published camera count could differ between two
runs on identical inputs. That is disqualifying for SIG regardless of accuracy. **Determinism is a
first-class requirement**, and it rules out this entire family.
**Outline delta:** EXTENDS §19.1/§19.4 — adds "determinism/replayability" to the outline's data-quality
principles as an explicit, testable property.

### F13.11 — Provenance semirings give the correct algebra for propagating support through derived facts

**Claim:** Green, Karvounarakis & Tannen (PODS 2007) show that annotating tuples with elements of a
commutative semiring and propagating those annotations through relational algebra (join → ·, union → +) is
the general form of provenance, and that recursive Datalog provenance requires formal power series
(i.e., can be infinite).
**Status:** VERIFIED
**Evidence:** `https://web.cs.ucdavis.edu/~green/papers/pods07.pdf` — extracted. "We introduce
K-relations, in which tuples are annotated (tagged) with elements from K… we argue that K must be a
commutative semiring"; Proposition 3.4 shows the RA identities hold iff `(K,+,·,0,1)` is a commutative
semiring; "For the (possibly infinite) provenance in datalog query answers we propose semirings of formal
power series that are shown to be generated by finite algebraic systems of fixed point equations."
Keywords include "data provenance, data lineage, incomplete databases, probabilistic databases, semirings,
datalog."
**Retrieved:** 2026-08-20
**Implication for the spec:** Every derived fact SIG publishes should carry a **provenance expression** —
a symbolic polynomial over base claim ids — not merely a flat list of "supporting claims." Conjunctive
support multiplies (all hops of an access path must hold); alternative support adds (either of two
independent derivations). The infinite-power-series result is the formal reason SIG's transitive closure
over access edges **must have a hop bound**: cyclic sharing relationships (A↔B↔C) make unbounded
provenance, and unbounded provenance cannot be rendered in a rationale string.
**Outline delta:** EXTENDS §6.4 — the outline asks for claim-level provenance on *assertions*; this says
derived assertions need provenance *expressions*, which is strictly more than a citation list.

### F13.12 — W3C PROV-O already supplies the vocabulary SIG needs for derivation, attribution, and primary-source distance

**Claim:** PROV-O defines Entity/Activity/Agent plus `wasDerivedFrom`, `wasAttributedTo`,
`wasGeneratedBy`, `used`, `actedOnBehalfOf`, `wasRevisionOf`, `wasQuotedFrom`, `hadPrimarySource`,
`specializationOf`, and `Bundle` (provenance of provenance).
**Status:** VERIFIED
**Evidence:** `https://www.w3.org/TR/prov-o/` — fetched. `prov:hadPrimarySource` "references preceding
entity produced by agents with direct experience about the topic"; `prov:wasDerivedFrom` is "a
transformation of one entity into another, an update resulting in a new entity, or construction based on a
pre-existing one"; `prov:Bundle` is "a named set of provenance descriptions, and is itself an Entity, so
allowing provenance of provenance to be expressed."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's `derived_from_source` chain (required by the brief) should be a
PROV-O-compatible `wasDerivedFrom` chain, and the "is this a primary source" flag in §8.15
(`primary_or_secondary`) should be expressed as presence/absence of `hadPrimarySource`. `prov:Bundle`
gives the exact mechanism for versioning a `ResolvedView`'s own provenance. Adopting the vocabulary costs
nothing and makes SIG's exports consumable by existing provenance tooling.
**Outline delta:** EXTENDS §8.15/§8.16 — names a concrete standard for a field the outline leaves abstract.

---

# 2. Findings — calibrated uncertainty and evidence grading

### F13.13 — ICD 203 separates *likelihood* from *confidence* and forbids mixing them in one sentence

**Claim:** The U.S. Intelligence Community's analytic standards directive mandates a fixed seven-band
probability vocabulary, a separate three-level confidence vocabulary, and an explicit prohibition on
combining the two in the same sentence.
**Status:** VERIFIED
**Evidence:** `https://www.bmbs.org/salamanca/readings/ODNI_ICDs_203-206-208.pdf` (ICD 203 as amended;
originally signed 2015-01-02, superseding the 2007-06-21 version; technical amendment conforming to DNI
Memo ES 2022-01273) — extracted verbatim. Standard e.(2): "Analytic products should indicate and explain
the basis for the uncertainties associated with major analytic judgments, specifically the likelihood of
occurrence of an event or development, and the analyst's confidence in the basis for this judgment."
The mandated likelihood bands are:

| almost no chance | very unlikely | unlikely | roughly even chance | likely | very likely | almost certain |
|---|---|---|---|---|---|---|
| remote | highly improbable | improbable (improbably) | roughly even odds | probable (probably) | highly probable | nearly certain |
| 01–05% | 05–20% | 20–45% | 45–55% | 55–80% | 80–95% | 95–99% |

and: "Analysts are strongly encouraged not to mix terms from different rows. Products that do mix terms
must include a disclaimer clearly noting the terms indicate the same assessment of probability."
Then e.(2)(b): "To avoid confusion, products that express an analyst's confidence in an assessment or
judgment using a 'confidence level' (e.g., 'high confidence') must not combine a confidence level and a
degree of likelihood, which refers to an event or development, in the same sentence."
Standard e.(3) additionally requires products to "clearly distinguish statements that convey underlying
intelligence information used in analysis from statements that convey assumptions or judgments."
The canonical ODNI-hosted copy at
`https://www.intel.gov/assets/documents/intelligence-community-directives/ICD_203.pdf` returned **HTTP
403** on 2026-08-20 (INACCESSIBLE); the `bmbs.org` mirror above is the copy actually read, and
`https://www.dni.gov/files/documents/ICD/ICD-203.pdf` is the alternate canonical location to try.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the battle-tested answer to §9.3 and SIG should adopt its *structure*
wholesale: **two orthogonal vocabularies, never fused into one token.** SIG's analogue of "likelihood" is
*support for the value*; SIG's analogue of "confidence" is *quality/consistency of the evidence base*.
The prohibition on mixing them in one sentence becomes a rationale-template constraint. Standard e.(3)
becomes SIG's hard rule that observations and inferences are separately labeled (§10).
**Outline delta:** CORRECTS §9.3. The outline's proposed vocabulary — `confirmed / strongly supported /
probable / unverified / contradicted / historical` — is a **single scale conflating three orthogonal
dimensions**: support strength (`confirmed`…`unverified`), conflict state (`contradicted`), and currency
(`historical`). Under that scheme a claim that is well-supported, contested, and stale has no
representable label. §7.2 below replaces it with three orthogonal fields.

### F13.14 — ICD 206 requires citing the *most original* source, source descriptors, and preservation of ephemeral sources

**Claim:** The IC's sourcing directive requires that a source reference "reference the most original source
that presents the relevant information," requires per-source qualitative descriptors, requires a holistic
"source summary statement" identifying which sources are corroborative or conflicting, and requires that
dynamic or ephemeral sources be preserved as a record.
**Status:** VERIFIED
**Evidence:** Same document, `https://www.bmbs.org/salamanca/readings/ODNI_ICDs_203-206-208.pdf`, ICD 206
section D.3. D.3.a(4): "An SRC should reference the most original source that presents the relevant
information in a form appropriate for use in analysis." D.3.c: "A source descriptor is used in conjunction
with an SRC to describe source qualitative factors germane to specific product judgments, or when the time
of pertinent information in a source is significantly different from the time of publication of the
source." D.3.d(2): "A source summary statement should cover strengths and weaknesses of the source base,
which sources are most important to key judgments, what sources are meaningfully corroborative or
conflicting." D.5: "If citing a source that is dynamic (e.g., from an Internet posting), ephemeral…, or not
subject to an IC element's policy for systematic storage… a record of the source shall be preserved for
retention by the IC element producing the covered analytic product for at least one year."
**Retrieved:** 2026-08-20
**Implication for the spec:** Three direct requirements. (1) "Cite the most original source" is the
*normative* version of copy-discounting — SIG should resolve a claim's citation up its `derived_from`
chain to the root artifact and cite that, listing intermediaries as derivation path. (2) The "source
summary statement" is precisely SIG's rationale string, and ICD 206 tells us what it must contain: which
sources mattered, and which corroborate or conflict. (3) Portal pages are the paradigm "dynamic source" —
SIG must archive a content-addressed snapshot at ingest, not link to a live URL.
**Outline delta:** EXTENDS §8.15 and §11.3 — supplies concrete, externally-validated content requirements
for the rationale field the outline only gestures at, and independently justifies the snapshot-archive
requirement.

### F13.15 — The Admiralty/NATO code is a 6×6 two-axis system whose axes are *instructed* to be judged independently

**Claim:** NATO AJP-2.1 (STANAG 2511) rates source reliability A–F and information credibility 1–6, and
doctrine requires the two to be assessed independently of one another.
**Status:** VERIFIED
**Evidence:** `https://www.cambridge.org/core/services/aop-cambridge-core/content/view/E67548E8010A47345C3439D45D9EC6B3/S1930297525100077a.pdf/effect_of_source_reliability_and_information_credibility_on_judgments_of_information_quality_in_intelligence_analysis.pdf`
— Kelly, Budescu, Dhami & Mandel, *Judgment and Decision Making* (2025) 20:e36, doi:10.1017/jdm.2025.10007,
CC-BY. Their Table 1 reproduces NATO AJP-2.1 (NATO, 2016): reliability of the collection capability
**A** completely reliable, **B** usually reliable, **C** fairly reliable, **D** not usually reliable,
**E** unreliable, **F** reliability cannot be judged; credibility of the information **1** completely
credible, **2** probably true, **3** possibly true, **4** doubtful, **5** improbable, **6** truth cannot be
judged. "The Admiralty Code uses a 6 × 6 alphanumeric rating system, which requires the evaluation of
source reliability and information credibility independently from one another." Source reliability is "the
confidence associated with a source's long-term success in providing quality information"; a completely
novel source is 'F'. Credibility 1 = "originates from another source than the already existing information
on the same subject" (i.e., **independent corroboration is the definition of top credibility**);
6 = information that "provides no basis for comparison with any known behavior pattern of a target."
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the two-axis model the brief asks for, and it maps onto SIG cleanly
*once* one notices that Admiralty's axis-2 (credibility) is doing two jobs at once: corroboration state
*and* plausibility. SIG splits those (§4). Note especially that Admiralty defines "1" by *independent*
corroboration — which makes copy detection load-bearing even inside the classic scheme.
**Outline delta:** EXTENDS §9.1 — the outline's Tier A–F is a *one*-axis scale and is therefore strictly
weaker than a 60-year-old military standard; §4 supplies the reconciliation.

### F13.16 — Empirically, humans collapse the Admiralty code's two axes onto the diagonal

**Claim:** Encoders using the Admiralty code overwhelmingly assign matched pairs (A1, B2, C3…), use source
reliability as a cue for credibility, and do not in fact treat the axes independently; interpretation
(decoding) is also unreliable.
**Status:** VERIFIED
**Evidence:** Kelly et al. 2025 (URL above), §2 "Challenges with applying the Admiralty Code": "when
assigning (i.e., encoding) the alphanumeric codes, analysts or operators most often assign codes that fall
along the diagonal such that source reliability and information credibility align perfectly in the ordinal
position (i.e., assigned codes of A1, B2, C3, etc.; Baker et al., 1968)… encoders may use source
reliability as a cue for information credibility and not vice versa (Miron et al., 1978). These findings
indicate that analysts may not be assigning source reliability and information credibility classifications
independently from one another despite the instruction within the Admiralty Code to do so." They also
report Samet (1975): across two tasks, "response consistency was lower than expected." Their own result:
"intraindividual reliability was best when levels of source reliability and information credibility were
moderately consistent compared to when they were maximally inconsistent… trustworthiness ratings depended
more on source reliability than on information credibility."
**Retrieved:** 2026-08-20
**Implication for the spec:** **Do not ask a human curator to assign both axes freely.** SIG must derive
axis 1 (source reliability) *mechanically from the source registry* — it is a property of the publisher,
not of the claim, so a human never re-judges it per claim — and derive axis 2 (claim support/directness)
*mechanically from the artifact type × predicate matrix*. Human judgment enters only at registry
maintenance and at explicit, logged override. This design decision is a direct consequence of the
empirical literature on the standard SIG is borrowing from, and it is the difference between a rubric that
works and one that decays into a single vibe score.
**Outline delta:** CORRECTS §9.1's framing as a thing analysts apply per claim. Tier assignment must be a
lookup, not a judgment call, at claim time.

### F13.17 — IPCC's calibrated language uses a two-dimensional evidence×agreement grid to produce a qualitative confidence that is explicitly *not* a probability

**Claim:** The IPCC guidance note defines confidence as a qualitative synthesis of evidence (type, amount,
quality, consistency) and agreement, on a five-point scale, and states that confidence "should not be
interpreted probabilistically"; a separate seven-band likelihood scale carries quantified uncertainty.
**Status:** VERIFIED
**Evidence:** `https://www.ipcc.ch/site/assets/uploads/2017/08/AR5_Uncertainty_Guidance_Note.pdf`
(Mastrandrea et al., 2010) — extracted. "The AR5 will rely on two metrics… Confidence in the validity of a
finding, based on the type, amount, quality, and consistency of evidence… and the degree of agreement.
Confidence is expressed qualitatively. Quantified measures of uncertainty in a finding expressed
probabilistically." ¶9: "A level of confidence is expressed using five qualifiers: 'very low,' 'low,'
'medium,' 'high,' and 'very high.'… Confidence should not be interpreted probabilistically, and it is
distinct from 'statistical confidence.'" Figure 1 is the evidence(limited/medium/robust) × agreement
(low/medium/high) grid. ¶2 requires "a traceable account: a description in the chapter text of your
evaluation of the type, amount, quality, and consistency of evidence and the degree of agreement, which
together form the basis for a given key finding." ¶11 criterion A: for a variable that "is ambiguous, or
the processes determining it are poorly known or not amenable to measurement: **Confidence should not be
assigned**; assign summary terms for evidence and agreement." Likelihood scale (Table 1): virtually
certain 99–100%, very likely 90–100%, likely 66–100%, about as likely as not 33–66%, unlikely 0–33%, very
unlikely 0–10%, exceptionally unlikely 0–1%. ¶3 warns about group convergence and anchoring on previous
values. ¶10: "'About as likely as not' should not be used to express a lack of knowledge."
**Retrieved:** 2026-08-20
**Implication for the spec:** Three adoptions. (1) The evidence×agreement grid is the correct shape for
SIG's confidence: `evidence_strength × agreement` → `confidence`, with the grid itself published as data.
(2) "Confidence should not be assigned" for ambiguous variables is the IPCC's version of SIG's
`UNRESOLVED` — an authoritative precedent that refusing to grade is a legitimate, standard-compliant
output. (3) "Traceable account" is the rationale string, and IPCC specifies its content: type, amount,
quality, consistency of evidence, and degree of agreement. SIG's rationale template should have exactly
those five slots.
**Outline delta:** CONFIRMS §11.1's "Do not produce a false single 'true count'" and gives it a
standards-body precedent; EXTENDS §9.3 by supplying the grid structure the outline lacks.

### F13.18 — GRADE's "indirectness" domain is exactly the axis the outline conflates with source quality

**Claim:** GRADE starts evidence at a certainty level determined by study design, then rates it down for
risk of bias, inconsistency, **indirectness**, imprecision, and publication bias, and up for large effect,
dose-response, and residual confounding — each adjustment documented.
**Status:** VERIFIED
**Evidence:** `https://www.gradeworkinggroup.org/` — "high, moderate, low and/or very low"; eight domains
listed: risk of bias, imprecision, inconsistency, indirectness, publication bias, large effects,
dose-response gradients, residual plausible opposing bias; recommendations carry a separate strength
(strong/conditional) and direction (for/against) from the certainty of evidence.
`https://pmc.ncbi.nlm.nih.gov/articles/PMC10578932/` — confirms randomized trials start "high,"
observational studies start "low"; "Reviewers reduce certainty one level for 'serious' concerns, two levels
for 'very serious' ones"; indirectness is "evidence failing to match the review question regarding
patients, interventions, comparisons, or outcomes." The Journal of Clinical Epidemiology full text of "The
GRADE Working Group clarifies the construct of certainty of evidence"
(`https://www.jclinepi.com/article/S0895-4356(16)30703-X/fulltext`) returned **HTTP 403**, and the PubMed
record `https://pubmed.ncbi.nlm.nih.gov/28529184/` served a cookie-consent interstitial rather than the
abstract — both INACCESSIBLE; the two sources above are what was actually read.
**Retrieved:** 2026-08-20
**Implication for the spec:** GRADE's structure is the best available template for SIG's per-claim scoring:
**a starting level from artifact genre, then named, published, individually-logged downgrades and
upgrades.** Critically, *indirectness* is precisely the brief's "a first-rate contract PDF is weak evidence
for current active camera count" — GRADE has a name for it, a place for it, and a rule for how much it
costs. SIG adopts: `directness` is a downgrade domain, not a property of the source. GRADE's
one-level/two-level convention ("serious"/"very serious") gives SIG its downgrade quantum.
**Outline delta:** CORRECTS §9.1 — the outline places "signed contracts" and "direct field observation"
together in Tier A as if tier were a property of the artifact alone. Under GRADE logic, the artifact sets
the *starting* level and the predicate determines the *indirectness downgrade*, so the same Tier A contract
is high certainty for `contract_signed_date` and low certainty for `active_device_count`.

### F13.19 — The Berkeley Protocol splits verification into three separate objects and distinguishes weight from admissibility

**Claim:** The UN OHCHR / Human Rights Center Berkeley Protocol defines open-source verification as three
separate considerations — the source, the digital item/file, and the content — assessed collectively, and
separately defines reliability, relevance, probative value, and weight.
**Status:** VERIFIED
**Evidence:** `https://www.ohchr.org/sites/default/files/2024-01/OHCHR_BerkeleyProtocol.pdf` — extracted.
¶176: "Verification refers to the process of establishing the accuracy or validity of information that has
been collected online… Verification is broken down into three separate considerations: the source, the
digital item or file, and the content, which should be looked at collectively and compared for
consistency." ¶177: "Source analysis is the process of assessing a source's credibility and reliability."
¶194: "External corroboration is provided by information that lies outside a digital item itself but that
coincides with and thus supports the veracity of the item's content." ¶56–57: every item should be
assessed for "reliability, relevance and probative value"; "Weight refers to the value attributed to an
item and the degree to which it will ultimately be relied upon in drawing a legal or factual conclusion.
The determination of weight should be a holistic assessment that depends, in part, on the other information
that may support, corroborate or contradict the fact in question." ¶191 defines chronolocation as
corroborating *when* something was captured.
**Retrieved:** 2026-08-20
**Implication for the spec:** This supplies a **third axis** the brief did not ask for and the outline does
not have: **artifact integrity**. A portal screenshot with no archive, no checksum, and no capture
timestamp is a different evidentiary object from a WARC-archived, hash-verified capture of the same page —
even though the source (the portal) and the directness (portal → active count) are identical. SIG must
score `(source_reliability, directness, artifact_integrity)`. The weight-vs-admissibility split maps
directly onto SIG's `admissible claim set` filter (§7.3 step 1) versus `claim weight` (step 3).
**Outline delta:** EXTENDS §8.15 — the outline's `EvidenceArtifact` has `checksum` and `archived_copy` as
optional-looking fields; this makes their presence a scored, published property that changes resolution
outcomes.

### F13.20 — Wikidata's rank system is the closest production precedent for publishing conflicting sourced values

**Claim:** Wikidata keeps all sourced values and annotates them with preferred/normal/deprecated rank;
queries return "best rank"; deprecation is for erroneous statements, *not* for outdated ones, which instead
carry start/end-time qualifiers; and ranks carry explicit `reason for preferred rank` (P7452) /
`reason for deprecated rank` (P2241) qualifiers.
**Status:** VERIFIED
**Evidence:** `https://www.wikidata.org/wiki/Help:Ranking` — fetched. Preferred = "the most current
statement or statements that best represent consensus"; normal = default, "no judgement or evaluation of a
value's accuracy and currency"; deprecated = statements "known to include errors" or "outdated knowledge",
and explicitly "does not apply to historically accurate information with appropriate time qualifiers;
those use start/end time annotations instead." The Query Service maintains a "best" rank view (preferred if
any, else normal) reachable via the `wdt:` property path. Ranks are distinguished from references: "ranks
indicate what data value is considered the most correct" while references show sources; disputes are
resolved by discussion, not by ranking.
**Retrieved:** 2026-08-20
**Implication for the spec:** Validates SIG's shape: **claims are never deleted or overwritten; a separate
ranking layer designates the resolved value; the ranking carries a machine-readable reason.** SIG improves
on it in two ways: SIG's rank is *computed by a versioned ruleset* rather than set by hand, and SIG's
"reason" is a generated rationale rather than a single qualifier. The deprecated-vs-outdated distinction is
important and SIG should copy it exactly: a superseded value is not a wrong value.
**Outline delta:** CONFIRMS §6.5 and §19.3 with a working, decade-old production system at scale.

### F13.21 — Dempster–Shafer combination is known to produce counterintuitive results under high conflict

**Claim:** Dempster's rule of combination, when sources conflict strongly, can assign full belief to a
hypothesis both sources considered nearly impossible (Zadeh's counterexample), because of the
normalization step.
**Status:** PARTIALLY VERIFIED (the Zadeh counterexample and the normalization critique are consistently
reported across multiple independent search results; the primary Zadeh review was not retrieved. The
Berkeley-hosted survey PDF at `https://www.stat.berkeley.edu/~aldous/Real_World/dempster_shafer.pdf` was
retrieved and confirms the framing — "An important aspect of this theory is the combination of evidence
obtained from multiple sources and **the modeling of conflict between them**. This report surveys a number
of possible combination rules for Dempster-Shafer structures" — but the extracted text did not contain the
Zadeh example itself.)
**Evidence:** `https://www.stat.berkeley.edu/~aldous/Real_World/dempster_shafer.pdf` (abstract extracted,
2026-08-20). Corroborating search results describe the standard example: physician A believes meningitis
0.99 / brain tumour 0.01; physician B believes concussion 0.99 / brain tumour 0.01; Dempster's rule yields
m(brain tumour) = 1. Alternative rules exist (Yager's transfer to the universe, Dubois–Prade, the
Transferable Belief Model's unnormalized conflict mass) precisely because of this. Sources consulted:
`https://ieeexplore.ieee.org/document/1591951/` ("Shedding new light on Zadeh's criticism of Dempster's
rule of combination"), `https://arxiv.org/pdf/1304.2718` ("Can Evidence Be Combined in the Dempster-Shafer
Theory").
**Retrieved:** 2026-08-20
**Implication for the spec:** Reject Dempster–Shafer for SIG's core resolver. SIG's most interesting cases
are *precisely* the high-conflict ones (contract 42 vs portal 38 vs OSM 31), which is where DS is least
trustworthy and least explainable. The one DS idea worth keeping is the explicit representation of
*ignorance* as mass on the frame of discernment — SIG's equivalent is that `UNRESOLVED` is a first-class
output rather than an absence of output.
**Outline delta:** EXTENDS §9.3 — records a considered rejection of the most commonly proposed alternative
formalism.

### F13.22 — Subjective logic's opinion tuple maps to a Beta distribution and needs a base rate SIG cannot supply

**Claim:** A subjective-logic opinion is `(belief, disbelief, uncertainty, base_rate)` with
`b + d + u = 1`, bijectively mapped to a Beta distribution with `α = r + Wa`, `β = s + W(1-a)`.
**Status:** PARTIALLY VERIFIED (search-result synthesis, corroborated across the UAI 2016 tutorial listing
`https://www.auai.org/uai2016/tutorials_pres/subj_logic.pdf` and
`https://www.cs.cmu.edu/~yuqingt/PDFs/kaplan13reasoningunderuncertainty.pdf`; the tutorial PDF was
downloaded but its slide text did not extract cleanly, so the formulas are recorded as reported rather than
as read.)
**Evidence:** Search against `Josang subjective logic opinion belief disbelief uncertainty base rate` —
consistent statements that "belief + disbelief + uncertainty = 1", that opinions "also contain a base rate
parameter which express the a priori belief in the absence of evidence", and the Beta mapping with
`r` = observations of x, `s` = observations of ¬x, `a` = base rate, `W` = non-informative prior weight
(typically 2).
**Retrieved:** 2026-08-20
**Implication for the spec:** The *uncertainty mass* concept is genuinely valuable and SIG adopts its
spirit: absence of evidence produces `u ≈ 1`, not `b ≈ d ≈ 0.5`. But subjective logic requires a
**base rate** — the prior probability that an arbitrary agency has, say, ICE-accessible sharing enabled —
and any base rate SIG picked would itself be a contested political claim. Encoding one into the resolver
would be laundering an editorial position as arithmetic. Rejected for the core resolver; the `u`-mass idea
survives as the `UNSUPPORTED`/`UNRESOLVED` distinction (no evidence ≠ balanced evidence).
**Outline delta:** EXTENDS §9.4 — gives a formal reason why "no evidence" must be a distinct output value
from "evidence balanced."

---

# 3. Findings — SIG's actual sources, measured

These findings exist because the reconciliation design must be grounded in what the real corpus looks
like, not in a hypothetical one. All measurements were taken on 2026-08-20.

### F13.23 — Only 19.05% of the world's mapped ALPR devices carry an `operator` tag

**Claim:** As of the 2026-08-20 taginfo snapshot, OpenStreetMap contains 144,312 objects tagged
`surveillance:type=ALPR`, of which 27,496 (19.05%) carry `operator`; 125,376 (86.9%) carry `manufacturer`,
and 105,743 (73.3%) carry `manufacturer=Flock Safety`.
**Status:** VERIFIED
**Evidence:** `https://taginfo.openstreetmap.org/api/4/tag/stats?key=surveillance%3Atype&value=ALPR` →
`data_until: 2026-08-20T00:59:51Z`; all = 144,312; nodes = 144,169; ways = 140; relations = 3.
`https://taginfo.openstreetmap.org/api/4/tag/combinations?key=surveillance%3Atype&value=ALPR&rp=200` →
56 distinct combinations total; `man_made` 143,934 (0.9974); `direction` 135,027 (0.936);
`camera:type` 133,398 (0.924); `manufacturer` 125,376 (0.869); `manufacturer=Flock Safety` 105,743 (0.733);
`surveillance:zone=traffic` 120,363 (0.834); **`operator` 27,496 (0.1905)**; `operator:wikidata` 17,816
(0.1235); `operator:type` 4,182 (0.029) of which `government` 1,196 and `private` 1,725; `source` 2,450
(0.017). The HTML page `https://taginfo.openstreetmap.org/tags/surveillance%3Atype=ALPR` renders these
statistics via JavaScript and was **not** usable through WebFetch — the JSON API above is the working
access path.
**Retrieved:** 2026-08-20
**Implication for the spec:** **Device attribution (§11.2) is not an edge case; it is the majority case.**
Roughly four out of five mapped ALPR devices in the world are operator-orphaned. Any SIG design that
treats attribution as a nice-to-have will publish a physically-mapped count that cannot be joined to an
agency for 81% of devices. The attribution workflow in §9.2 below is therefore the single
highest-throughput reconciliation path in the system and must be built to run at ~10⁵ scale with a human
review queue, not as an ad-hoc curator task.
**Outline delta:** EXTENDS §11.2 dramatically. The outline presents device attribution as an occasional
puzzle ("A field mapper or public-records researcher can resolve it"); the measurement shows it is the
dominant workload.

### F13.24 — OSM ALPR nodes carry essentially no survey-date metadata, so freshness must come from element history

**Claim:** Of the 56 tag keys that co-occur with `surveillance:type=ALPR` at measurable frequency, **none**
is a date key — no `check_date`, no `survey:date`, no `start_date`.
**Status:** VERIFIED
**Evidence:** Same taginfo combinations query as F13.23, requested with `rp=200` and returning the complete
set of 56 combinations (`total: 56`). Filtering for any key containing "date" returns nothing; the tail of
the distribution is `direction` variants at ~1,000 occurrences and `highway` at 1,009.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG cannot read "when was this camera last seen?" off the tags. It must
derive observation time from the OSM element's own `version`/`timestamp`/`changeset` metadata, which means
the OSM connector must ingest element metadata, not just tags. This is the concrete, minimal answer to
outline Q19 ("How should OSM edit history be represented without replicating the entire OSM history
database?"): SIG needs `(osm_type, osm_id, version, timestamp, changeset, uid)` per ingested element and
the previous version's timestamp for the specific tags SIG consumes — not the full history planet.
Consequence for reconciliation: an OSM-derived claim's `observed_time` is the element's last-edit time,
which is an *upper* bound on when a human actually looked at the pole — and for a node created in 2024 and
never re-edited, it is the only timestamp available. That is a systematically optimistic freshness signal
and the volatility model must treat it as such.
**Outline delta:** EXTENDS §9.2 — the outline's observation-vs-validity distinction is right, but for OSM
SIG cannot even observe the observation time directly; it observes an *edit* time, which is a third clock.

### F13.25 — DeFlock writes into OSM; it is not an independent source

**Claim:** DeFlock is an OpenStreetMap editor whose changesets are written directly to OSM and tagged
`created_by=DeFlock *.*.*`, and deflock.me renders OSM data rather than a separate database.
**Status:** VERIFIED
**Evidence:** `https://wiki.openstreetmap.org/wiki/Deflock` — "a mobile OpenStreetMap editor expressly for
adding Automatic License Plate Readers (ALPRs)"; "Changesets submitted through DeFlock are automatically
tagged with `created_by=DeFlock *.*.*`"; supports eight manufacturers (Flock Safety, Motorola/Vigilant,
Genetec, Leonardo, Neology, Rekor, Axis Communications, ShotSpotter); licensed GNU AGPL v3.
`https://raw.githubusercontent.com/FoggedLens/deflock/master/README.md` — "Uses OpenStreetMap data to
populate a map with crowdsourced locations of ALPRs"; Cloudflare R2 is used for points and vector tiles,
i.e. as a cache/CDN layer, not as a primary datastore; AWS Lambda "for region segmenting and counts."
`https://deflock.me/` itself returned **HTTP 403** to WebFetch (INACCESSIBLE); the GitHub README and OSM
wiki are the working access paths. NB: a third-party blog claims DeFlock "put 336K ALPRs on
OpenStreetMap," which is inconsistent with the measured 144,312 `surveillance:type=ALPR` objects in F13.23;
that figure is **not verified** and is not used anywhere in this design.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is SIG's canonical source-dependence case and it is *declarable*, not
inferable. A DeFlock-sourced claim and an OSM-sourced claim about the same node are **the same claim**.
Counting them as two corroborating sources would be exactly the Dong et al. failure (F13.1) — and it is the
easy failure to make, because the outline's §21 source registry lists OSM and DeFlock as separate
"core physical infrastructure" sources. SIG must record `derived_from_source: OSM` on every DeFlock-derived
claim at ingest and collapse them into one independence class before any vote.
**Outline delta:** CORRECTS §6.2's worked example and §21's registry framing. "OSM contains 24
field-observed Flock ALPR nodes" and "DeFlock shows 24" are one observation, not two.

### F13.26 — Flock transparency portals are enabled by a minority of customers and are the only live operational-count source

**Claim:** Flock's transparency portal is an opt-in feature that pulls live values from the Flock system;
one enumeration effort catalogued ~562 portal pages under `transparency.flocksafety.com/<org>` and
estimated adoption at under 10% of law-enforcement customers, while Flock's own marketing claims 1,500+
agencies publish portals.
**Status:** PARTIALLY VERIFIED — both figures were read from their respective sources; neither was
independently confirmed, and they disagree.
**Evidence:** `https://www.ryanohoro.com/post/list-of-flock-safety-transparency-pages` — ~562 pages
enumerated via `archive.ph/transparency.flocksafety.com`; URL pattern
`transparency.flocksafety.com/[organization-name]` with `-pd`/`-so` suffixes; "Only a small number of law
enforcement customers enable this feature (< 10%), which implies that there are thousands of other
organizations for which we cannot directly view how they use Flock Safety data." (No date was surfaced for
this post.) `https://www.flocksafety.com/blog/how-flock-builds-transparency-into-public-safety-technology`
(published 2026-05-22, byline date 2026-07-24) — describes portal contents as policy information, usage
statistics, sharing details, and a "public-friendly search audit" showing "case number, search reason,
offense type, anonymized user identifier, and the number of cameras or networks searched," with values
drawn directly from the Flock system. A search snippet attributed to Flock states "More than 1,500 agencies
publish a transparency portal showing their policy, retention period and sharing partners" — I did not
locate that sentence on a page I fetched, so it is recorded as unverified.
`https://eyesonflock.com/` returned **HTTP 403** to WebFetch (INACCESSIBLE) — the aggregator that would
reconcile these numbers could not itself be read; R2/R4 should retry with a different client.
**Retrieved:** 2026-08-20
**Implication for the spec:** Two things. (1) The portal is the *only* routinely-refreshed source of
operational state, so it dominates the `active_device_count` strategy — but (2) its coverage is a small,
self-selected, non-random subset of deployments, which means portal *absence* carries almost no
information about deployment existence and must never be scored as negative evidence. Portal coverage
becomes an explicit published coverage metric (§12), and this discrepancy (562 vs 1,500+) is itself a
worked `Contradiction` of type `COUNT_DISAGREEMENT` at the vendor level.
**Outline delta:** CONFIRMS §9.4 with a measured example; EXTENDS §11.1 by establishing that the portal
source is high-directness but low-coverage, which are independent properties.

### F13.27 — EFF's Atlas of Surveillance publicly disclaims completeness and is explicitly not an inventory

**Claim:** The Atlas is crowdsourced + aggregated OSINT, CC-BY licensed, last updated 2026-08-12, and EFF
states it is incomplete and "not an inventory of every technology in use."
**Status:** VERIFIED
**Evidence:** `https://atlasofsurveillance.org/methodology` — crowdsourcing via a "Report Back" tool with
1,300+ students and volunteers (as of Feb 2025) doing 20–30 minute research assignments verified by
University of Nevada, Reno interns and EFF staff; plus aggregation of existing public datasets from
journalists, nonprofits, government agencies, and vendors. Stated limitations: "The information is only as
good as the source: sometimes government agencies withhold information"; technologies may be abandoned
without public announcement; "It is impossible to exhaustively fact-check each one"; the Atlas represents
what was documented, "not an inventory of every technology in use." Last updated 2026-08-12; corrections
to `aos@eff.org`. License CC-BY, confirmed on `https://atlasofsurveillance.org/` ("CC-by").
**Retrieved:** 2026-08-20
**Implication for the spec:** Atlas is the model for how SIG should talk about itself. Operationally: an
Atlas row is a **Tier C** claim with high reliability for *existence of adoption* and low directness for
*current status, quantity, or configuration* — because EFF explicitly says technologies may be abandoned
without announcement. So an Atlas row should be able to establish `deployment_exists` at
`STRONGLY_SUPPORTED` while contributing nothing to `active_device_count` and nothing to
`deployment_operational_status` once it is more than one volatility half-life old.
**Outline delta:** CONFIRMS §9.1 Tier C and §9.4; EXTENDS §11 by showing the same source must be scored
differently per predicate — which is the whole point of the two-axis model.

### F13.28 — Have I Been Flocked's data is FOIA-derived, incomplete, and lagged by months to years

**Claim:** HIBF's dataset consists of Flock audit logs obtained through public-records requests and
transparency-portal publications, is explicitly incomplete and often redacted, and can lag actual searches
by months or years.
**Status:** VERIFIED
**Evidence:** `https://haveibeenflocked.com/about/faq` — the data "consists of audit logs that have been
released via open records (FOIA) requests," with some governments publishing "heavily redacted versions on
a Flock-provided transparency portal"; "The dataset is incomplete; few governments provide easy access to
these logs, and the records we obtain are often redacted"; "There can be a significant delay—months or even
years—between when a search occurs and when it appears on this website. This is not a real-time monitoring
tool." Records also do not show when vehicles actually passed cameras.
**Retrieved:** 2026-08-20
**Implication for the spec:** Audit-derived `ObservedUse` edges are **high reliability, high directness,
and terrible currency**. This is the case that proves the three axes are independent: an audit log is the
best possible evidence that a search happened, and near-worthless evidence that a sharing relationship is
*currently* configured. SIG must never let an audit log's Tier A quality promote a stale
`ConfiguredAccess` claim.
**Outline delta:** CONFIRMS §11.3's insistence that actual use and configured access are different edges,
and supplies the reason it matters operationally: they have opposite currency profiles.

### F13.29 — The vendor-replacement pattern is real, dated, and produces exactly the false conclusion the outline warns about

**Claim:** Syracuse, NY adopted a five-year, $422,636.28 Axon contract in February 2026, revoked Flock's
operating rights in March 2026 with a 60-day removal order, and as of a 2026-07-24 report the Flock cameras
were still physically standing with no confirmation they had been disconnected.
**Status:** VERIFIED
**Evidence:** `https://cnycentral.com/news/local/months-after-syracuse-ditched-flock-critics-say-switch-to-axon-solved-nothing`
(published 2026-07-24). February 2026: Common Council voted to adopt a five-year, $422,636.28 contract with
Axon Enterprise. March 2026: Council formally revoked Flock's operating rights and ordered removal within
60 days. As of publication, cameras "remained standing"; privacy advocate Daniel Schwarz: "I would hope
that the city disconnected and disabled all these cameras. But I don't have any further information."
The article notes the city's Surveillance Technology Working Group has not met since early 2026 and that
Schwarz was denied access to both the ALPR policy and the Axon contract after a six-month-old request.
Corroborating context (broader pattern, no named cities in the accessible portion):
`https://www.404media.co/cities-are-ditching-flock-immediately-replacing-it-with-axon-license-plate-readers/`
(published 2026-08-06) — references "a handful of cities across the U.S." sourced from "local media reports
and government documents," and notes Axon cameras "attach to an existing streetlamp"; the full article is
member-gated so city names were not readable (PARTIALLY ACCESSIBLE).
**Retrieved:** 2026-08-20
**Implication for the spec:** This single case forces the three-track lifecycle model in §9.4. On
2026-07-24 the Syracuse deployment simultaneously had: procurement state `TERMINATED`, hardware state
`PRESENT`, operational state `UNRESOLVED`, and a `replaced_by` edge to an Axon deployment whose own
hardware state was `INSTALLING`. A single `status` field cannot represent that, and any single-field
representation would render it as either "canceled" (falsely implying removal) or "active" (falsely
implying operation). **This is the strongest empirical argument in the whole file for the outline's §22.5
thesis, and it also shows the outline's own §6.7 state list is inadequate to express it.**
**Outline delta:** CONFIRMS §22.5 and §6.7's motivation; CORRECTS §6.7's *model* — the thirteen listed
states are not a single machine's states, they are values drawn from three different machines.

### F13.30 — Flock's default retention is a moving, vendor-set default that customers override, making it a fast-decaying predicate

**Claim:** Flock states retention is set per community, "In most communities, that's 30 days unless local
law says otherwise," with automatic deletion; customers set sharing settings; and press reporting indicates
the default was reduced from 30 days to seven.
**Status:** PARTIALLY VERIFIED — the 30-day statement and customer-control statements were read directly;
the reduction to seven days was reported in search results attributed to
`https://thenextweb.com/news/flock-safety-privacy-changes-data-retention`, which I did not fetch.
**Evidence:** `https://www.flocksafety.com/trust/data-privacy` — "In most communities, that's 30 days
unless local law says otherwise"; "Retention is set in advance, and the system deletes data automatically";
"Our customers set sharing settings and policies. Nothing is shared unless they choose to share it";
"Data Sharing Is a Local Choice." No policy-change dates appear on that page.
**Retrieved:** 2026-08-20
**Implication for the spec:** `retention_days` has three distinct sources that are *not* the same
predicate: the vendor default, the agency's written policy, and the actual system configuration. The
outline's §8.12 already identifies the policy-vs-configuration split; this adds a third layer (vendor
default), which matters because a vendor-wide default change silently alters thousands of deployments'
actual configuration without any agency-level document being produced. SIG's retention reconciliation
(§9.6) must therefore model `vendor_default_retention_days` as a separate subject-level claim on the
*vendor*, inheritable to deployments only as a weak, explicitly-labeled inference.
**Outline delta:** EXTENDS §8.12 and §11 — adds a third layer the outline's two-layer policy/configuration
model does not have.

### F13.31 — Flock Reports demonstrates a working three-state verification vocabulary with retained retractions

**Claim:** An independent accountability database of 3,083 Flock-related incidents publishes a
verified/unconfirmed/retracted verification state per entry, keeps retracted entries visible with logged
corrections, and refuses to publish on an uncorroborated tip.
**Status:** VERIFIED
**Evidence:** `https://www.flocksafety.com` is not the source — the source is
`https://www.flockreports.com/` (last updated 2026-08-15): 3,083 entries across all 50 states + DC,
covering 2010–2026 with deepest coverage 2025–2026; 6,449 total sources cited; records drawn from "news
reports, court filings, audits, council minutes, and public-records responses"; entries marked "verified"
have independent confirmation against primary or established secondary sources, "unconfirmed" entries exist
in published reports but lack corroboration, and "retracted" entries remain visible with corrections
logged; "Nothing gets published on a tip alone." A `flock-issues-2026.json (schema v2)` is referenced but
no public API or download link is documented on the page. Licensing is not stated on the page.
**Retrieved:** 2026-08-20
**Implication for the spec:** Direct precedent for two SIG requirements: (1) `review_status` on `Claim`
(§8.16) needs at least `{unconfirmed, verified, retracted}` and retraction must be non-destructive; (2) the
"nothing on a tip alone" rule is a concrete admissibility filter — a claim whose only support is a
Tier E/F artifact should be *ingested and visible* but must not be *resolvable* to a published value on its
own. That is encoded in ambiguity condition **U1** below.
**Outline delta:** EXTENDS §8.16 — the outline lists `review_status` without a vocabulary; this supplies a
field-tested one.

### F13.32 — Berkeley Protocol / Bellingcat practice requires archiving and method documentation as part of verification

**Claim:** OSINT practice standards treat archiving the item and documenting the method as constitutive of
verification, not as optional hygiene.
**Status:** VERIFIED
**Evidence:** Berkeley Protocol (URL in F13.19), ¶176 and ¶194 as quoted. Bellingcat,
`https://www.bellingcat.com/resources/2021/11/09/first-steps-to-getting-started-in-open-source-research/`
— "record/archive what you are doing"; "the real skill is methodology. So, look up successful examples of
OSINT methodology to learn from"; "Don't take what others say as fact, check it yourself. Always seek
context"; the Berkeley Protocol is recommended as the comprehensive reference for "workflow, from ethical
and legal considerations of research to security awareness and data collection and analysis."
**Retrieved:** 2026-08-20
**Implication for the spec:** The `artifact_integrity` axis (§4.3) is not SIG's invention; it is standard
OSINT practice rendered machine-readable. A claim derived from an unarchived, un-hashed page is
categorically weaker and SIG should say so numerically-in-ordinal-terms rather than in a footnote.
**Outline delta:** CONFIRMS §13.4 and §8.15.

### F13.33 — SQL:2011 already standardizes the bitemporal storage SIG needs

**Claim:** SQL:2011 provides system-versioned tables (transaction time) and application-time period tables
(valid time), with `AS OF SYSTEM TIME` and `VERSIONS BETWEEN SYSTEM TIME` query syntax.
**Status:** VERIFIED
**Evidence:** `https://cs.ulb.ac.be/public/_media/teaching/infoh415/tempfeaturessql2011.pdf` — Kulkarni &
Michels (IBM), "Temporal features in SQL:2011," *ACM SIGMOD Record* 41(3). "SQL:2011 was published in
December of 2011… This paper covers the most important new functionality that is part of SQL:2011: the
ability to create and manipulate temporal tables." The paper notes that ISO work began in 1995 from TSQL2
and that "commercial adoption has been rather slow."
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's `ResolvedView` must be queryable "as of" two clocks: the world time
being asked about (valid time / application time) and the knowledge state being reproduced (transaction
time / system time). "What did the graph say on 2026-07-01 about the state of the world on 2025-06-01?"
must be answerable, because that is what makes a published number defensible six months later when the
underlying claims have changed. This is a storage requirement that flows directly out of reconciliation
being a derived artifact.
**Outline delta:** EXTENDS §9.2 — the outline names observation time and validity time; this adds the third
required clock, *knowledge time*, without which resolutions are not reproducible.

### F13.34 — Rego/Datalog-style declarative policy is the right shape for an inspectable, testable ruleset

**Claim:** Open Policy Agent's Rego is a Datalog-derived declarative language for evaluating policy against
structured data, supports policy unit testing, and emits decision logs carrying rule labels.
**Status:** VERIFIED
**Evidence:** `https://www.openpolicyagent.org/docs/policy-language` — "Rego was inspired by Datalog and
extends it to support structured document models such as JSON"; developers "focus on what queries should
return rather than how queries should be executed"; the docs cover Policy Testing; decision logs record
metadata including `rule_labels`.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG does not need to *use* OPA, but it should copy the pattern: rules are
data, rules are unit-testable, and every decision emits a log naming the rules that fired. That is the
concrete meaning of "auditable, not a black box." SIG's ruleset format (§7.1) is specified as versioned
declarative data for exactly this reason.
**Outline delta:** EXTENDS §9.3 — supplies an implementation pattern for the outline's explainability
requirement.

---

# 4. Design — the multi-axis source model

## 4.1 The outline's Tier A–F is a *genre* scale, not a reliability scale

§9.1 lists "signed contracts" and "direct field observation" together in Tier A. But a signed contract is
authoritative about what was purchased and says nothing about what is switched on today, while a field
observation is authoritative about what was on a pole last Tuesday and says nothing about who owns it.
These artifacts are not "equally reliable"; they are *reliable about different things*. The tier list is
therefore a taxonomy of **evidence genre**, and it must be crossed with a second axis before it can drive
resolution. This is GRADE's structure exactly (F13.18): genre sets the starting level, and *indirectness*
adjusts it per question.

SIG keeps Tier A–F — it is good shorthand and R2/R4 will use it in the source registry — but redefines it
as the **starting level** and adds three further axes.

## 4.2 The four axes

| Axis | Symbol | Domain | Assigned by | Varies per |
|---|---|---|---|---|
| Source reliability | `R` | R1…R6 | Source registry (curated, versioned) | publisher/feed, **not** per claim |
| Claim directness | `D` | D1…D6 | `(artifact_genre × predicate)` lookup table | claim |
| Artifact integrity | `I` | I1…I3 | Ingest pipeline (mechanical) | evidence artifact |
| Currency | `C` | C1…C4 | `f(age, predicate volatility)` (§5) | claim, at query time |

`R` is a property of the **publisher and its method**, evaluated once, reviewed on a schedule, and
published as a registry row with a written justification. It is never re-judged when a claim is ingested.
This follows directly from F13.16: humans asked to score two axes per item collapse them onto the diagonal,
so SIG never asks them to.

`D` is a property of the **pairing** of artifact genre and predicate, read from a published matrix. It is
the GRADE "indirectness" domain and it is where "a Tier A contract is weak evidence for active camera
count" gets encoded.

`I` is mechanical: `I1` = content-addressed archive stored + checksum + fetch timestamp + HTTP status
recorded; `I2` = live URL recorded and retrievable at ingest but no durable archive; `I3` = secondhand
transcription, screenshot without provenance, or an artifact SIG cannot re-fetch. Berkeley Protocol's
"digital item" axis (F13.19).

`C` is derived at query time from the predicate's volatility class and the claim's `observed_time`, and is
therefore not stored on the claim. A claim's currency changes without the claim changing — which is why
resolutions must be recomputed rather than cached forever (§7.6).

## 4.3 Source reliability scale, with Admiralty and Tier alignment

| `R` | SIG definition | Admiralty | Typical Tier | SIG examples |
|---|---|---|---|---|
| **R1** | Legally-operative or system-of-record artifact produced by the party with authority and consequences for error | A — completely reliable | A | executed contract PDF from the buyer's records portal; court filing; invoice; official device inventory; government open-data release |
| **R2** | First-party statement by the operating or vendor organization, published under its own name | B — usually reliable | A/B | Flock transparency portal page; agency policy PDF; council agenda packet; vendor press release; agency press release |
| **R3** | Reviewed specialist dataset with a published, checkable methodology | C — fairly reliable | C | EFF Atlas of Surveillance (F13.27); Have I Been Flocked processed exports (F13.28); Flock Reports "verified" entries (F13.31); Eyes on Flock aggregations |
| **R4** | Professional reporting or research with editorial accountability but no published record-level method | C/D | D | investigative news article; academic paper; NGO report |
| **R5** | Community/volunteer observation, individually unreviewed but from a structured collection process | D/E | E | an individual OSM/DeFlock node; a community-submitted photo report; an activist spreadsheet row |
| **R6** | Heuristic, automated, or model-generated candidate with unresolved entity matching | F — cannot be judged | F | RF/OUI match; LLM extraction from an unstructured page; fuzzy name match; automated web scrape with unconfirmed entity resolution |

Notes on the alignment:

- SIG's `R` and Admiralty's letter scale differ in one important respect. Admiralty `F` means "reliability
  cannot be judged" — a *novel* source. SIG's `R6` means "reliability is known to be low because the method
  is heuristic." SIG therefore adds a separate boolean `reliability_provisional` for genuinely novel
  sources, defaulting them to `R5` with the flag set, rather than conflating novelty with unreliability.
- Admiralty's numeric axis (1–6, credibility) is **not** adopted as-is, because it fuses two things SIG
  must keep apart: independent corroboration (which SIG computes, in §6) and plausibility/consistency with
  prior expectation (which SIG deliberately does *not* score, because a prior over how much surveillance an
  agency "should" have is an editorial position, not a measurement). SIG's `D` axis takes Admiralty's slot
  in the pairing but carries a different, more defensible meaning.
- The outline's Tier letters map many-to-one onto `R`, and one Tier can span several `R` values once
  directness is factored out — see the Tier A split above between R1 (contract) and R5 (field observation).
  **This is the correction the outline most needs.**

## 4.4 Claim directness `D` — the `(genre × predicate)` matrix

`D1` the artifact is the authoritative record *of the fact itself*; `D2` the artifact is a first-party
report of the fact; `D3` the artifact reports the fact secondhand or reports a close proxy;
`D4` the artifact establishes a *related* fact from which the target is a short inference;
`D5` the artifact bears on the target only through a modelling assumption; `D6` the artifact is
non-probative for this predicate and must be excluded from the admissible set.

Illustrative rows of the published matrix (the full matrix is one row per genre × predicate and is
versioned with the ruleset):

| Artifact genre | `contract_signed_date` | `contracted_device_count` | `active_device_count` | `retention_days` | `configured_sharing_partner` |
|---|---|---|---|---|---|
| Executed contract PDF | **D1** | **D1** | D5 | D4 (if specified) / D6 | D6 |
| Invoice | D3 | D2 | D4 | D6 | D6 |
| Transparency portal snapshot | D6 | D5 | **D1** | **D1** | **D1** |
| Council minutes / agenda packet | D2 | D2 | D4 | D3 | D4 |
| Agency written policy | D6 | D6 | D6 | **D2** (policy value) | D3 (declared) |
| OSM node set (field observation) | D6 | D5 | D3 (as a lower bound only) | D6 | D6 |
| Audit-log export | D6 | D6 | D4 | D6 | D4 (proves use, not configuration) |
| News article | D3 | D3 | D3 | D3 | D3 |
| Vendor default-settings page | D6 | D6 | D6 | D5 | D6 |

Two consequences worth stating loudly:

1. **A Tier A contract is `D5` for `active_device_count`** and therefore cannot win that predicate against
   a `D1` portal snapshot, regardless of tier. That is the brief's requirement, discharged mechanically.
2. **`D6` is an admissibility filter, not a weight.** A portal snapshot contributes *nothing whatsoever*
   to `contract_signed_date`; it is not weak evidence, it is not evidence. Excluding it is what stops the
   resolver from producing "the contract was signed around July 2026 (portal)."

## 4.5 Composing the axes into a weight class

Axes compose by a published ordinal table, not by arithmetic. Start from `R`, then apply GRADE-style
downgrades (F13.18: one level for serious, two for very serious):

```
base(R1)=W4  base(R2)=W3  base(R3)=W3  base(R4)=W2  base(R5)=W2  base(R6)=W1

downgrade for directness:  D1: 0   D2: 0   D3: -1   D4: -2   D5: -2 (and cap at W1)   D6: EXCLUDE
downgrade for integrity:   I1: 0   I2: -1  I3: -2
downgrade for currency:    C1: 0   C2: -1  C3: -2   C4: -2 (and cap at W1)

upgrade (at most +1 total, and never above W4):
  +1 if the claim is a machine-readable structured export rather than a text extraction
       AND extraction_confidence = EXACT
  +1 if the claim was independently field-verified by a SIG curator with a logged verification event

W(claim) = clamp(W0..W4) of the above
```

`W4` dispositive · `W3` strong · `W2` moderate · `W1` weak · `W0` non-probative (retained, never resolving).

Worked example — Appendix B's Example City. The contract PDF says 42 (`R1`, `D1` for
`contracted_device_count`, `I1`, `C1` since contract quantity is `IMMUTABLE`) → **W4** for
`contracted_device_count`. The *same artifact* for `active_device_count` is `R1`, `D5`, `I1`,
`C3` (17 months old, `FAST` predicate) → base W4, −2 directness with cap at W1, −2 currency → **W1**.
The portal snapshot saying 38 is `R2`, `D1`, `I1`, `C1` (5 weeks old) → **W3**. The portal wins
`active_device_count` 38 by three weight classes, and the contract's 42 is retained as a
`contracted_device_count` = 42 at W4 — a *different predicate*, not a losing claim. There is no conflict at
all, and the entire apparent "42 vs 38 contradiction" in the outline's Appendix B dissolves into two
correct answers to two different questions plus one genuine finding: an unresolved delta of 4.

---

# 5. Design — predicate volatility and currency

## 5.1 Why this is a first-class axis

Age only degrades evidence for predicates that can change. A signing date from 2019 is exactly as good
today as it was in 2019. An active-camera count from 2019 is nearly worthless. The outline has no model of
this at all, which means it has no principled way to let a recent Tier B claim beat an old Tier A claim —
which is the situation SIG will face constantly.

SIG assigns each predicate a **volatility class** with a half-life `h`. Currency is then:

```
age = as_of_time − claim.observed_time
C1 CURRENT     age ≤ 0.5·h
C2 AGING       0.5·h < age ≤ 1.0·h
C3 STALE       1.0·h < age ≤ 3.0·h
C4 HISTORICAL  age > 3.0·h
```

For `IMMUTABLE` predicates `h = ∞` and `C` is always `C1`. Half-lives are ruleset data, not code, and are
expected to be recalibrated once SIG has enough observed change-rate data to measure them (§13).

## 5.2 The volatility table

| Predicate | Class | Half-life `h` | Rationale |
|---|---|---|---|
| `contract_signed_date`, `contract_effective_date`, `contract_expiry_date` | IMMUTABLE | ∞ | A historical event; amendments create new claims, they do not change this one |
| `contract_value_usd`, `contracted_device_count` | IMMUTABLE (per contract instance) | ∞ | Fixed by the instrument; amendments are new contract entities |
| `organization_legal_name`, `organization_jurisdiction`, `ori_code` | GLACIAL | 10 y | Changes only on merger/incorporation/dissolution |
| `vendor_of_product`, `product_capabilities[]` | GLACIAL | 5 y | Vendor acquisitions and product renames do occur (Vigilant→Motorola) |
| `deployment_exists` (agency uses technology T from vendor V) | SLOW | 3 y | The predicate EFF Atlas is good for; adoption is sticky |
| `policy_written_retention_days`, `policy_immigration_use_prohibited` | SLOW | 2 y | Policy documents are revised on multi-year cycles |
| `asset_location` (fixed pole-mounted device) | SLOW | 2 y | Devices are relocated but not often; use `MODERATE` for trailers |
| `asset_exists_at_location` | MODERATE | 12 mo | Removal/replacement happens; Syracuse (F13.29) shows year-scale persistence |
| `deployment_procurement_status` | MODERATE | 12 mo | Contract cycles |
| `configured_retention_days` | MODERATE | 9 mo | Agency-configurable and vendor-default-driven (F13.30) |
| `deployment_operational_status` | FAST | 6 mo | Suspensions, pauses, and quiet deactivations |
| `active_device_count`, `installed_device_count` | FAST | 6 mo | Continuous adds/removals within a deployment |
| `configured_sharing_partner_set` | FAST | 4 mo | Network membership changes with no public notice |
| `national_lookup_enabled`, `hotlist_configuration` | VOLATILE | 2 mo | Toggled in software, often in response to controversy |
| `usage_search_count_30d` | VOLATILE | 1 mo | An inherently windowed measurement; older values are history, not staleness |
| `asset_operator` (attribution) | SLOW | 3 y | Follows the deployment, not the device |
| `vendor_default_retention_days` | MODERATE | 9 mo | Vendor-wide, changes affect all customers at once |

Rule: for `IMMUTABLE` and `GLACIAL` predicates, **recency never breaks a tie** — a newer claim gets no
advantage from being newer, and the tie-break falls through to weight and then to source reliability. For
`FAST` and `VOLATILE` predicates, currency downgrades bite hard and the resolution strategy is
latest-observation-wins (§8).

## 5.3 Windowed predicates are not stale, they are indexed

`usage_search_count_30d` for July 2026 does not become "stale" in August; it becomes *a value for July*.
Windowed predicates carry an explicit `window_start`/`window_end` in the claim's `valid_time` and are never
subject to currency downgrade for the window they describe. What decays is the answer to "what is the
current rate," which is a different, derived predicate (`usage_search_rate_current`) with its own
volatility. Conflating these is the mistake that produces "412 searches last 30 days" on a dossier where
the underlying data is nine months old.

---

# 6. Design — source dependence and independence classes

## 6.1 SIG declares copying rather than inferring it

Dong et al. (F13.1) must infer dependence from a snapshot because they cannot see inside their sources.
SIG *builds* its sources' intake and therefore knows. This is a strict advantage and SIG should exploit it:

> **Every `Claim` carries `derived_from_source: SourceRef[]`**, populated at ingest with the upstream
> source(s) the ingesting connector knows it consumed, forming a DAG over sources
> (PROV-O `wasDerivedFrom`, F13.12). The chain is transitive and materialized.

Declared examples, from measured evidence:

- `DeFlock → OSM` (F13.25): every DeFlock-surfaced device claim is derived from OSM. Same class.
- `Eyes on Flock → Flock transparency portal`: EOF aggregates portal pages; an EOF sharing-partner claim
  and a portal sharing-partner claim for the same org are the same observation.
- `EFF Atlas → {news article, agency record, vendor dataset}` (F13.27, "Data Aggregation" path): Atlas rows
  that came from aggregation inherit the upstream's identity; Atlas rows that came from "Report Back"
  crowdsourcing are Atlas-original but derive from a named cited artifact.
- `news article → transparency portal`: extremely common; a reporter quoting the portal's number is not a
  second observation of the number.

## 6.2 Independence classes

```
IndependenceClass(claims C, as_of t):
    build graph G over C:
        edge(c_i, c_j)  if  root_sources(c_i) ∩ root_sources(c_j) ≠ ∅
        where root_sources(c) = leaves of c.derived_from_source transitive closure
                                ∪ {c.source} if the chain is empty
    classes := weakly connected components of G
```

**Class weight rule (the anti-double-counting rule):**

```
W(class) = max( W(c) for c in class )        # NOT sum, NOT 1 - Π(1-w)
support_breadth = |classes that assert value v|
```

This is the ordinal analogue of Dong's `(1-c)^d(S,G)` discount with `c → 1` for *declared* copying: a
declared copy contributes exactly zero incremental support. Where copying is declared, there is no reason
to be softer than that.

## 6.3 Method correlation — the partial discount

F13.4 shows correlation without copying. SIG records `collection_method` on every source and applies a
second, weaker grouping:

| `collection_method` | Shared blind spot |
|---|---|
| `roadside_visual_survey` | rear-facing devices, private-property devices, tree/pole obstruction, rural roads |
| `vendor_self_report` | anything the vendor's product does not instrument; anything the customer disabled from the portal |
| `public_records_response` | records the agency withheld, exempted, or never created |
| `web_scrape_structured` | pages behind auth, JS-rendered content, deleted pages |
| `news_reporting` | anything not newsworthy in that market |

**Rule:** corroboration across two independence classes that share a `collection_method` counts as
`support_breadth = 1.5`, not 2 — implemented as: it does **not** satisfy the `≥2 independent classes`
condition required to upgrade confidence, but it **does** satisfy the `≥2 classes` condition required to
avoid the single-source ambiguity trigger (U3). This is the honest middle position: two roadside surveys
agreeing is more than one, and less than two.

## 6.4 The undeclared-copying detector

Declared lineage is necessary but not sufficient — an agency's press release may silently reproduce the
vendor's number. SIG therefore runs Dong et al.'s Eq. (8) **as a monitor, on a schedule, offline**:

- Inputs: pairs of sources with ≥ 20 co-asserted `(subject, predicate)` pairs.
- `kt` / `kf` are computed against SIG's *own current resolutions* as a proxy for truth, with the explicit
  caveat that this is circular and therefore the output is a **suspicion, not a fact**.
- Output: a `Contradiction` of type `UNDECLARED_DEPENDENCE_SUSPECTED` with the computed probability,
  routed to a curator, who either adds a declared `derived_from_source` edge (which *does* change future
  resolutions) or dismisses it with a logged reason.
- **The detector never mutates a resolution directly.** This is the load-bearing rule that keeps the
  resolver deterministic and the numbers replayable.

---

# 7. Design — the resolution algorithm

## 7.1 Why rule-based, and what "rule" means

The empirical case is F13.3: unsupervised truth discovery gains ~0–3 points of precision, is unstable
across runs, and fails outright in SIG's few-claims/few-sources regime. The institutional case is that SIG
publishes numbers that get read into the record at city council meetings; the number must survive a hostile
question of the form "why does your site say 38?" answered in one sentence, by a volunteer, from the page.
The engineering case is F13.10: MCMC-based approaches cannot guarantee that two runs on identical inputs
agree, and reproducibility is non-negotiable for a derived public artifact.

**Ruleset format.** The ruleset is *data*, not code: a versioned, signed, human-readable document
(YAML/JSON, checked into the repository, released with a semantic version) containing (a) the source
registry `R` assignments with written justifications, (b) the `(genre × predicate) → D` matrix, (c) the
volatility table, (d) the per-predicate strategy assignments, (e) the numeric thresholds, (f) the rationale
templates. Every rule has a stable `rule_id`. Every resolution records which `rule_id`s fired
(the OPA decision-log pattern, F13.34). The ruleset ships with a golden-case test suite: fixed claim
bundles with expected resolutions, run in CI, so that a ruleset change that alters any published value
fails loudly and produces a diff.

## 7.2 The confidence vocabulary

Following ICD 203 (F13.13) and IPCC (F13.17), SIG publishes **three orthogonal fields plus a status**,
never one fused token.

```
resolution_status : RESOLVED | UNRESOLVED | SUPERSEDED | WITHDRAWN
support           : CONFIRMED | STRONGLY_SUPPORTED | PROBABLE | WEAKLY_SUPPORTED | UNSUPPORTED
agreement         : UNCONTESTED | MINOR_DISAGREEMENT | CONTESTED | IRRECONCILABLE
currency          : CURRENT | AGING | STALE | HISTORICAL
```

`support` is computed *only* from the winning value's evidence:

| `support` | Condition |
|---|---|
| `CONFIRMED` | winner has a `W4` claim, **or** ≥2 independent classes (§6.2, method-distinct) each at `W3`+ |
| `STRONGLY_SUPPORTED` | winner has a `W3` claim, or ≥2 independent classes at `W2`+ |
| `PROBABLE` | winner has exactly one class at `W2`+ |
| `WEAKLY_SUPPORTED` | winner's best claim is `W1` |
| `UNSUPPORTED` | no admissible claim above `W0` (always co-occurs with `UNRESOLVED`) |

`agreement` is computed *only* from the dissent structure:

| `agreement` | Condition |
|---|---|
| `UNCONTESTED` | all admissible claims map to the same canonical value |
| `MINOR_DISAGREEMENT` | dissenting values exist but all dissent is `W1`/`W0`, or (numeric) all dissent is within the predicate's `tolerance` |
| `CONTESTED` | dissent exists at `W2`+ from ≥1 independent class |
| `IRRECONCILABLE` | dissent at `W3`+ from ≥2 independent classes, or an open `BLOCKING` `Contradiction` |

`currency` is the winning claim's `C` (§5.1), surfaced directly.

**Presentation label.** UIs that need one word derive it from a published lookup over
`(support, agreement, currency)` — e.g. `(CONFIRMED, UNCONTESTED, CURRENT) → "confirmed"`;
`(STRONGLY_SUPPORTED, CONTESTED, CURRENT) → "disputed"`; `(*, *, HISTORICAL) → "historical"`;
`(*, IRRECONCILABLE, *) → "contradicted"`. The API always returns all four fields; the one-word label is
never the primary representation, and per ICD 203 the rationale template never places a support term and an
agreement term in the same sentence.

**Delta from the outline.** §9.3 proposes
`confirmed / strongly supported / probable / unverified / contradicted / historical`. Four of those are
support levels, one is an agreement level, and one is a currency level, so the vocabulary cannot express
"strongly supported but contested" or "confirmed but historical" — both of which are extremely common in
this domain and both of which are the interesting cases. The three-field replacement is a superset: every
outline label is recoverable from a `(support, agreement, currency)` triple.

## 7.3 The algorithm

```
RESOLVE(subject S, predicate P, as_of t, ruleset V) -> ResolvedView

# --- Phase 0: gather ------------------------------------------------------
 0.1  claims := all Claim c where c.subject = S and c.predicate = P
                and c.knowledge_time <= t.knowledge          # bitemporal (F13.33)

# --- Phase 1: admissibility (Berkeley Protocol "admissibility" vs "weight") -
 1.1  drop c if c.review_status in {RETRACTED, WITHDRAWN}
 1.2  drop c if c.valid_time does not intersect t.world      # as-of window
 1.3  drop c if D(genre(c), P) = D6                          # non-probative for THIS predicate
 1.4  drop c if c is SUPERSEDED by a later claim from the same source with
               the same valid_time  (a source's own correction replaces it)
 1.5  if claims is empty -> return UNRESOLVED(reason = NO_EVIDENCE)

# --- Phase 2: normalize to a comparable domain ---------------------------
 2.1  for each c: v := canonicalize(c.value, P.value_domain)
      # units, enum casing, org identity via canonical org id, date granularity
 2.2  if any c cannot be canonicalized:
          emit Contradiction(VALUE_DOMAIN_MISMATCH, c) ; drop c
 2.3  if P is a count predicate and two claims disagree on count_basis
          (contracted vs installed vs active vs mapped):
          emit Contradiction(PREDICATE_CONFLATION) ; drop the mismatched claims
          # this is the §11.1 guard: never silently compare different things

# --- Phase 3: weight ------------------------------------------------------
 3.1  for each c: W(c) := WEIGHT(R(c.source), D(genre(c),P), I(c.artifact),
                                 CURRENCY(t.world - c.observed_time, volatility(P)))
 3.2  drop c if W(c) = W0 from the *resolving* set (retain for display)

# --- Phase 4: independence ------------------------------------------------
 4.1  classes := INDEPENDENCE_CLASSES(claims)          # §6.2
 4.2  for each class k: W(k) := max(W(c) for c in k)
                        method(k) := set of collection_methods in k
 4.3  for each candidate value v:
          classes(v) := {k : some c in k asserts v}
          breadth(v) := |{distinct collection_methods across classes(v)}|
                        counted with the §6.3 half-credit rule
          best(v)    := max(W(k) for k in classes(v))

# --- Phase 5: apply the predicate strategy --------------------------------
 5.1  strategy := V.strategy[P]                        # §8 table
 5.2  candidate_ranking := STRATEGY_RANK(strategy, candidates, t)
      # each strategy defines a TOTAL order; see §8.2

# --- Phase 6: the ambiguity test (§7.4) -----------------------------------
 6.1  if AMBIGUOUS(candidate_ranking, classes, P, t):
          return UNRESOLVED(reason = <the first triggering condition id>,
                            candidates = candidate_ranking,
                            rationale  = RATIONALE_UNRESOLVED(...))

# --- Phase 7: emit --------------------------------------------------------
 7.1  winner := candidate_ranking[0]
 7.2  support   := SUPPORT(best(winner), breadth(winner))            # §7.2
      agreement := AGREEMENT(candidate_ranking[1:], classes)         # §7.2
      currency  := CURRENCY(winner's best claim)
 7.3  supporting_claim_ids := all c asserting winner (incl. W0, flagged)
      dissenting_claim_ids := all c asserting anything else
 7.4  return ResolvedView{
          subject, predicate, value = winner,
          resolution_status = RESOLVED,
          support, agreement, currency,
          rationale = RATIONALE(...),                                # §7.5
          supporting_claim_ids, dissenting_claim_ids,
          excluded_claim_ids  = {(id, exclusion_reason)},            # phases 1-3
          independence_classes = [class -> claim_ids],
          rules_fired = [rule_id...],
          ruleset_version = V.version,
          input_digest = sha256(sorted claim ids + their content hashes),
          as_of_world = t.world, as_of_knowledge = t.knowledge,
          computed_at = now()
       }
```

**Determinism.** `STRATEGY_RANK` must yield a *total* order. The universal final tie-break, applied by
every strategy after its own criteria are exhausted, is:

```
(W(k) desc, breadth desc, observed_time desc, source_registry_rank asc, claim_id asc)
```

`claim_id` is a content-addressed, stable identifier, so the order is fixed forever. There is no random
tie-break anywhere in the system.

## 7.4 The ambiguity test — the exact conditions that force `UNRESOLVED`

`AMBIGUOUS` returns the **first** matching condition (evaluated in order, so the reason is deterministic):

| id | Condition | Rationale |
|---|---|---|
| **U0** | `claims` empty after Phase 1 | No evidence. Distinct from balanced evidence (F13.22). |
| **U1** | `best(top) ≤ W1` | Nothing above weak. The Flock Reports "nothing on a tip alone" rule (F13.31). |
| **U2** | `best(top) == best(second)` **and** `classes(top)` and `classes(second)` are disjoint **and** `breadth(top) == breadth(second)` | A genuine standoff between independent evidence of equal quality. |
| **U3** | `|classes(top)| == 1` **and** ∃ a dissenting class with `W ≥ W2` **and** that class is method-distinct from `classes(top)` | One source versus one source is never resolvable by fiat. |
| **U4** | P is numeric **and** `(max(candidates) − min(candidates)) / max(candidates) > P.max_relative_spread` (default 0.15) **and** `best(top) < W4` | Numbers too far apart, nothing dispositive. |
| **U5** | `currency(top) ∈ {STALE, HISTORICAL}` **and** `volatility(P) ∈ {MODERATE, FAST, VOLATILE}` | The best available answer is too old to assert about a changing quantity. Emits `UNRESOLVED(reason=STALE)` and publishes the stale value as `last_known` with its date. |
| **U6** | Any admissible claim was dropped in Phase 2.3 for `count_basis` mismatch **and** fewer than 2 claims survive | The remaining evidence cannot be compared. |
| **U7** | An open `Contradiction` on `(S,P)` has `severity = BLOCKING` | A human has flagged this as not-safe-to-publish. |
| **U8** | `agreement` would be `IRRECONCILABLE` **and** `support` would be below `CONFIRMED` | Strong, independent, unreconciled dissent beats a merely-strong winner. |

`UNRESOLVED` is not an error state and is not hidden. It renders as an explicit finding with all candidate
values, their evidence, and a generated research task (§11.4). IPCC precedent (F13.17 ¶11-A: "Confidence
should not be assigned") establishes that declining to grade is a standards-compliant output.

**U5 deserves emphasis** because it is the rule the outline is missing entirely. It is what stops SIG from
publishing "42 active cameras" from a 2024 contract in 2026 — even with no dissent at all, even with a
Tier A source. Silence plus age is not a resolution.

## 7.5 Rationale generation

A rationale is generated from a versioned template, filled from the resolution's own structured fields. Per
ICD 206 (F13.14) it must name which sources mattered and which corroborate or conflict; per IPCC (F13.17)
it must convey type, amount, quality, consistency of evidence and degree of agreement; per ICD 203
(F13.13) it must not put a support term and an agreement term in the same sentence.

Template skeleton:

```
{VALUE_CLAUSE}. {BASIS_CLAUSE}. {AGREEMENT_CLAUSE}. {CURRENCY_CLAUSE}. {GAP_CLAUSE}
```

Five real examples, generated from the cases documented in this file:

> **1 (resolved, contested).** "SIG reports 38 active Flock ALPR devices for Example City PD. This is the
> figure the agency's own Flock transparency portal reported in the snapshot SIG archived on 2026-07-15.
> Two other sources give different figures: the 2025-04-03 procurement contract specifies 42 contracted
> units, and 31 devices attributed to this agency are currently mapped in OpenStreetMap. Those figures
> measure contracted and mapped quantities respectively, not active devices, so they are reported
> separately rather than treated as disagreement. The portal figure is five weeks old against a predicate
> that changes on a roughly six-month scale. Four contracted units remain unaccounted for in any
> operational source, and eleven reported-active devices are not yet mapped."

> **2 (unresolved, U2 standoff).** "SIG does not report a single retention period for Example County SO.
> The agency's written ALPR policy, adopted 2025-11-02, states 30 days. The agency's Flock transparency
> portal, snapshotted 2026-08-01, reports 365 days. These are independent sources of comparable quality
> describing, respectively, declared policy and system configuration, and SIG treats a policy/configuration
> divergence as a finding rather than a conflict to be averaged. Both values are published with their
> evidence. An open research task requests a current configuration export."

> **3 (unresolved, U5 stale).** "SIG cannot report a current active-device count for Example Township PD.
> The most recent operational evidence is a council presentation dated 2023-09-12 reporting 12 devices.
> That is 35 months old against a predicate SIG treats as changing on a six-month scale, and no source
> published since has reported an operational figure. The 2023 value is retained as the last known count
> with its date. No portal is published for this agency, and portal absence is not evidence that the
> deployment ended."

> **4 (resolved, three-track lifecycle).** "As of 2026-07-24, SIG records the City of Syracuse's Flock ALPR
> deployment as commercially terminated, physically present, and operationally unknown. The Common Council
> revoked Flock's operating rights in March 2026 with a 60-day removal order; local reporting on 2026-07-24
> found the cameras still standing and could not establish whether they had been disconnected. In February
> 2026 the Council approved a five-year, $422,636.28 contract with Axon Enterprise for replacement ALPR
> service, which SIG links as a vendor-replacement edge. SIG does not characterize this as a reduction in
> surveillance capability."

> **5 (resolved by exclusion, dependence).** "SIG reports 31 physically mapped devices for Example City PD.
> All 31 derive from a single independence class: OpenStreetMap. DeFlock, which some sources treat as a
> separate dataset, writes its observations directly into OpenStreetMap and is therefore not independent
> corroboration. This figure is a lower bound on installed devices, not a count of them; roadside visual
> survey systematically misses rear-facing and private-property installations."

Rationales are regenerated whenever the resolution is recomputed and are never hand-edited. A curator who
disagrees with a rationale files a ruleset change or a pin (§7.7), both of which are logged.

## 7.6 Recomputation, versioning, immutability

- A `ResolvedView` is a **derived artifact**. It is never edited in place, and it is never the storage
  location of a fact. Deleting the entire resolved-view table must be a no-op that costs only CPU.
- Every `ResolvedView` row is keyed by
  `(subject, predicate, as_of_world, as_of_knowledge, ruleset_version)` and carries `input_digest`.
- **Reproducibility contract:** given the claim store as of `as_of_knowledge` and ruleset
  `ruleset_version`, re-running `RESOLVE` must produce a byte-identical value/support/agreement/currency
  tuple and an identical `input_digest`. This is a CI-enforced property, tested against a frozen corpus.
- **Recomputation triggers:** (a) a new/updated/retracted claim on `(S,P)`; (b) a change to any source's
  registry row that affects `R`; (c) a ruleset release; (d) a declared-dependence edge added; (e) crossing
  a currency boundary — because `C` is time-dependent, every resolution has a *scheduled expiry*
  at the next `C` transition, and the scheduler recomputes then. Without (e), stale resolutions silently
  persist, which is the single most likely operational failure mode of this design.
- Ruleset releases produce a **diff report**: every `(subject, predicate)` whose published value, support,
  agreement, or currency changed, with before/after. That report is published, not just logged, so that
  external users can see when a number changed because the world changed versus because SIG's rules
  changed. This is the derived-artifact analogue of a corrections policy.

## 7.7 Human override — pinning as an editorial act

A curator may pin a resolution. The pin is **itself a claim**, not a mutation:

```
Claim {
  subject: <S>, predicate: <P>, value: <pinned value>,
  claim_type: CURATOR_RESOLUTION_OVERRIDE,
  source: <SIG editorial, with the curator as a named prov:Agent>,
  author: <curator identity>,
  rationale: <required free text, min 120 chars, explaining what the ruleset got wrong>,
  observed_time: <now>, valid_time: <explicit>,
  expires_at: <required; default now + 180 days, max 365>,
  supersedes_resolution: <input_digest of the resolution being overridden>
}
```

Rules:

1. A pin participates in resolution as a `W4` claim of genre `curator_override`, and short-circuits Phase
   5 — but it does **not** delete or hide the dissenting claims, and Phase 7 still emits the full
   supporting/dissenting/excluded sets.
2. `resolution_status` on a pinned view becomes `RESOLVED` with an additional flag
   `editorially_pinned: true`, and the API and UI must surface it as an editorial act with the curator's
   name and rationale visible at the same level as the value. It is never invisible.
3. Pins **expire**. An unexpiring pin is a fact laundered into the graph. On expiry the resolution reverts
   to computed and a task is generated.
4. Pins are counted and published as a quality metric (§12): a rising pin count means the ruleset is
   drifting from reality and needs revision, which is exactly the signal that should not be suppressible.
5. A pin that contradicts a `W4` non-override claim requires a second curator's countersignature.

---

# 8. Design — per-predicate resolution strategies

## 8.1 Strategy definitions

| Strategy | Ranking rule | Use when |
|---|---|---|
| `AUTHORITATIVE_SOURCE_WINS` | Order by `authority_rank(source, P)` from the ruleset's per-predicate authority list; only if no authoritative source is present, fall through to weight | The predicate has a designated system of record (legal facts) |
| `LATEST_OBSERVATION_WINS` | Order by `observed_time desc`, restricted to claims at `W ≥ W2` and `D ≤ D2` | Volatile operational state where recency dominates quality |
| `MAX_SUPPORT` | Order by `(best(v), breadth(v))` | Genuinely multi-source facts with no natural authority |
| `INTERVAL_UNION` | Value is the union of asserted intervals; conflicts only on gap/overlap semantics | "When did this exist/apply at all" |
| `INTERVAL_INTERSECTION` | Value is the intersection; empty intersection ⇒ `UNRESOLVED(U-INTERVAL)` | "When was this simultaneously true across all evidence" — required for access-path validity |
| `SET_UNION_WITH_PROVENANCE` | Value is a set; each member carries its own support/agreement | Sharing partner lists, capability lists |
| `NO_RESOLUTION` | Always `UNRESOLVED`; publish all claims side by side | Predicates SIG refuses to collapse on principle |
| `TRACK_SEPARATE` | Not one predicate — split into N sibling predicates and resolve each | Predicates the outline conflates |

## 8.2 Assignment table

| Predicate | Strategy | Authority order / notes | Tolerance |
|---|---|---|---|
| `contract_signed_date` | `AUTHORITATIVE_SOURCE_WINS` | executed contract > council record > invoice > news | exact |
| `contract_value_usd` | `AUTHORITATIVE_SOURCE_WINS` | executed contract > purchase order > budget line > invoice sum | $0 |
| `contract_expiry_date` | `AUTHORITATIVE_SOURCE_WINS` | contract (incl. amendments) > council record | exact |
| `contracted_device_count` | `AUTHORITATIVE_SOURCE_WINS` | contract line items > amendment > invoice > council | 0 |
| `invoiced_device_count` | `MAX_SUPPORT` | sum over invoice set; partial invoice sets flagged | 0 |
| `installed_device_count` | `LATEST_OBSERVATION_WINS` | requires `D ≤ D2`; portal is D5 here so it does **not** qualify | 0 |
| `active_device_count` | `LATEST_OBSERVATION_WINS` | portal (D1) > agency statement (D2); contract excluded (D5) | `max_relative_spread` 0.10 |
| `mapped_device_count` | derived, not resolved | computed from the attributed-asset set; see §10 | n/a |
| `field_verified_device_count` | `MAX_SUPPORT` | curator field-verification events only | 0 |
| `deployment_exists` | `MAX_SUPPORT` | never resolves to `false` from absence (§9.4) | n/a |
| `deployment_procurement_status` | `AUTHORITATIVE_SOURCE_WINS` + lifecycle machine (§9.4) | contract/council record > vendor statement > news | n/a |
| `deployment_operational_status` | `LATEST_OBSERVATION_WINS` | portal/agency statement only | n/a |
| `deployment_hardware_status` | `LATEST_OBSERVATION_WINS` | field observation > news > agency statement | n/a |
| `policy_retention_days` | `AUTHORITATIVE_SOURCE_WINS` | signed policy document > policy web page > news | 0 |
| `configured_retention_days` | `LATEST_OBSERVATION_WINS` | portal (D1) > config export (D1) > vendor default (D5, excluded from resolving) | 0 |
| `configured_sharing_partner_set` | `SET_UNION_WITH_PROVENANCE` | per-member resolution; asymmetry is a finding, not a merge (§9.3) | n/a |
| `declared_sharing_policy` | `AUTHORITATIVE_SOURCE_WINS` | policy doc > portal policy text | n/a |
| `observed_use_count` | windowed; `MAX_SUPPORT` within window | audit export > portal audit view | 0 |
| `asset_operator` | `AUTHORITATIVE_SOURCE_WINS`, else `NO_RESOLUTION` | records/signage/field evidence resolve; inference never resolves (§9.2) | n/a |
| `asset_exists_at_location` | `LATEST_OBSERVATION_WINS` | field observation > imagery | n/a |
| `org_exists` / `org_identity` | `AUTHORITATIVE_SOURCE_WINS` | ORI registry > state registry > census place > network-list string | n/a |
| `capability_present` | `TRACK_SEPARATE` then `MAX_SUPPORT` | split by capability ontology term before resolving (§9.8) | n/a |
| `policy_vs_configuration_agreement` | `NO_RESOLUTION` | by design: both values always published (§8.12 of outline) | n/a |
| `immigration_enforcement_access` | `NO_RESOLUTION` unless a `W4` config export exists | highest-stakes predicate; refuses to resolve on policy text alone | n/a |
| `total_devices_in_jurisdiction` | `NO_RESOLUTION` | a completeness estimate, not a fact; see §12.4 | n/a |

Two entries are deliberate refusals. `policy_vs_configuration_agreement` and
`immigration_enforcement_access` are the predicates most likely to be quoted politically and least likely
to be resolvable from public evidence; `NO_RESOLUTION` is the correct engineering answer to a question SIG
cannot honestly answer, and publishing both values with provenance is more useful than picking one.

---

# 9. Design — the reconciliation workflows

## 9.1 Camera-count reconciliation (outline §11.1)

**The core correction: these are not five estimates of one quantity.** The outline's input list
(contract quantity / portal count / OSM observed / agency statement / invoice quantity) enumerates *five
different predicates*, and averaging or voting across them is a category error. SIG defines them
explicitly:

| Predicate | Counts | Unit hazard |
|---|---|---|
| `authorized_device_count` | units a governing body approved | approvals often authorize a *maximum*, not a purchase |
| `contracted_device_count` | units named in the executed instrument | contracts may count *cameras*, *devices*, or *pole installations* — record `count_basis` |
| `invoiced_device_count` | units actually billed | partial invoice sets undercount; recurring-service lines double-count |
| `installed_device_count` | units physically mounted | includes powered-off units |
| `active_device_count` | units the operator's system reports as live | vendor-defined; excludes units in maintenance |
| `mapped_device_count` | units in OSM attributed to this agency | derived (§10.1); a lower bound only |
| `field_verified_device_count` | units a SIG curator confirmed in person, dated | tiny but `W4` |
| `decommissioned_device_count` | units removed | rarely published |

Every count claim **must** carry `count_basis ∈ {camera, device, pole_installation, unspecified}` and
`scope ∈ {agency_owned, within_jurisdiction_boundary, agency_operated_anywhere}`. Claims with
`count_basis = unspecified` are admissible at `−1` weight and can never be `W4`.

**Algorithm.**

```
COUNT_RECONCILE(deployment Dp, as_of t):
  for each count predicate P in the table above:
      r[P] := RESOLVE(Dp, P, t, V)                      # §7.3, independently
  # deltas are DERIVED, not resolved
  delta_contract_to_active := r[contracted].value − r[active].value        (if both RESOLVED)
  delta_active_to_mapped   := r[active].value − r[mapped].value            (if both RESOLVED)
  delta_installed_to_active:= r[installed].value − r[active].value         (if both RESOLVED)
  for each delta that is non-zero:
      emit DeltaExplanation with the enumerated candidate causes and the
           evidence that would discriminate among them
  if any r[P] is UNRESOLVED: the corresponding deltas are UNRESOLVED, not zero
```

**Output object** (extends the outline's five fields):

```yaml
subject: deployment/<id>
as_of_world: 2026-08-20
as_of_knowledge: 2026-08-20T14:00:00Z
ruleset_version: 1.4.0
counts:
  authorized:      {value: 45, support: STRONGLY_SUPPORTED, agreement: UNCONTESTED, currency: CURRENT, basis: device, claims: [...]}
  contracted:      {value: 42, support: CONFIRMED, ...}
  invoiced:        {value: 38, support: PROBABLE, note: "invoice set incomplete: 3 of an estimated 6 quarters"}
  installed:       UNRESOLVED {reason: NO_EVIDENCE}
  active:          {value: 38, support: STRONGLY_SUPPORTED, agreement: MINOR_DISAGREEMENT, currency: CURRENT}
  mapped:          {value: 31, derived: true, lower_bound: true}
  field_verified:  {value: 6, ...}
  decommissioned:  UNRESOLVED {reason: NO_EVIDENCE}
deltas:
  contracted_minus_active: {value: 4, status: UNEXPLAINED, candidate_causes:
      [never_installed, installed_then_removed, counted_on_different_basis, portal_undercount],
      discriminating_evidence: [invoice_set_completion, field_survey, config_export]}
  active_minus_mapped:     {value: 7, status: EXPECTED, note: "mapped count is a lower bound; see coverage"}
coverage:
  mapping_completeness_estimate: {see §12.4 — published as a range with assumptions, or omitted}
  portal_present: true
  portal_last_snapshot: 2026-07-15
  contract_evidence_present: true
evidence: [claim ids, artifact ids, archive urls, checksums]
contradictions_open: [contradiction/8812]
research_tasks_open: [task/4471, task/4472]
```

**Failure modes and mitigations.** (a) *Basis conflation* — mitigated by mandatory `count_basis` and Phase
2.3. (b) *Double-counting mobile units* — a trailer or patrol-car reader is a device with
`mobility != fixed`; excluded from `mapped_device_count` and flagged separately. (c) *Shared deployments* —
a device jointly operated by two agencies must not be counted once for each; attribution is set-valued
(§9.2) and the count predicate is scoped `agency_operated_anywhere` with an explicit shared-device
deduction line. (d) *Portal counts networks, not devices* — some portal views report "cameras searched"
rather than "cameras owned"; the connector must map to the right predicate or refuse. (e) *Silent
undercount by the vendor* — no mitigation; recorded as a limitation in the published rationale.

## 9.2 Device attribution (outline §11.2)

Given F13.23 — 81% of mapped ALPR devices have no `operator` — this is SIG's highest-volume workflow.

**Candidate generation** for an unattributed asset `a`:

```
C1 spatial containment: deployments of agencies whose jurisdiction polygon contains a.geom
C2 road authority:      the operator/maintainer of the nearest highway way within 30 m of a.geom
                        (county road inside a city ⇒ county agency becomes a candidate)
C3 adjacency buffer:    agencies whose boundary is within 2 km of a.geom  (border installations)
C4 deficit match:       deployments with (contracted − mapped) > 0 in the containing or adjacent jurisdiction
C5 vendor match:        deployments whose vendor == a.manufacturer
C6 corridor match:      agencies with ≥3 already-attributed devices within 5 km on the same route
```

**Scoring** — integer feature scores from the ruleset, summed (published, inspectable, no learned weights):

| Feature | Score |
|---|---|
| jurisdiction polygon contains the asset | +4 |
| nearest-road authority == candidate agency | +3 |
| manufacturer matches candidate deployment's vendor | +3 |
| candidate deployment has an unexplained count deficit ≥ 1 | +2 |
| ≥3 attributed devices of the same agency within 5 km | +2 |
| asset within 250 m of the jurisdiction boundary (ambiguity penalty) | −2 |
| ≥2 candidate agencies score ≥ 6 (contest penalty, applied to all) | −2 |
| candidate is a state/federal agency with no deployment evidence in this area | −4 |
| OSM `operator:type` present and inconsistent with candidate (`private` vs a police agency) | −5 |

**Thresholds.** `score ≥ 8` and a **unique** top scorer with a ≥3-point margin ⇒ emit an inferred edge
`asset –probable_operator→ agency`. `4 ≤ score < 8`, or a top-two margin < 3 ⇒ emit **no edge**, emit a
`ResearchTask(ATTRIBUTE_DEVICE)` with the ranked candidates. `score < 4` ⇒ drop silently.

**Hard cases, handled explicitly:**

- *County road inside a city.* C1 and C2 disagree by construction. Both candidates score; the margin rule
  suppresses the edge and produces a task. This is correct — it is genuinely ambiguous, and SIG's value is
  in *saying so* rather than in guessing.
- *State police device inside a city.* The `−4` no-local-deployment-evidence penalty prevents a state
  agency from absorbing city devices by containment alone; a state agency only wins with independent
  deployment evidence (a state contract covering that corridor).
- *Agency A operates on behalf of agency B.* Modeled as three separate edges — `operated_by`, `owner`,
  `data_controller` (outline §19.8) — and attribution only ever infers `operated_by`. Ownership and control
  are never inferred from geography.
- *Multi-agency shared deployment.* Attribution is set-valued: `attribution_cardinality ∈ {single, multi,
  unknown}`. When two candidates tie above threshold and there is independent evidence of a joint program
  (a shared contract, an interlocal agreement), SIG emits `probable_operator` to **both** and marks the
  asset `shared: true` so downstream counts deduct it once.

**Output.** An `InferredEdge` with `inference_rule_id`, `score`, `score_breakdown[]`, `candidates_rejected[]`,
`inferred_at`, `inputs_digest`, and `label: INFERENCE`.

**Failure modes.** (a) *Feedback loop* — an inferred attribution must never be written back to OSM, never
count toward `field_verified_device_count`, and never feed C6's "already-attributed" corridor feature
(C6 counts only `W3`+ *observed* attributions). Without that last restriction the corridor feature
self-amplifies. (b) *Jurisdiction polygon errors* propagate silently; SIG records the boundary source and
version on every attribution. (c) *Private ALPR* — 1,725 ALPR nodes carry `operator:type=private` (F13.23);
those must never be attributed to a police agency by containment, hence the `−5`.

## 9.3 Sharing-edge reconciliation (outline §11.3)

**Three edge types, never merged.**

| Edge | Asserts | Source genres | Direction | Temporal semantics |
|---|---|---|---|---|
| `ConfiguredAccess(A → B, scope)` | A's system is configured to permit B to reach A's data | portal sharing lists, SharedNetworks.csv, config exports | strictly directional; `A shares_to B` and `B receives_from A` are the *same* edge viewed twice, and must be stored once with an explicit direction field | **point-observed**: a snapshot proves presence at `observed_at` only |
| `ObservedUse(B → A, window, count)` | B actually queried A's data during a window | audit-log exports, portal audit views | directional, searcher → data owner | windowed interval; never extrapolated |
| `DeclaredPolicy(A, statement)` | A states a rule about sharing | policy PDFs, portal policy text, council testimony | not an edge between orgs; an attribute of A (may *name* B) | validity from adoption date to supersession |

**Never** infer one from another. An `ObservedUse` edge in March does **not** establish `ConfiguredAccess`
in August (F13.28: HIBF data lags by months to years). A `DeclaredPolicy` prohibiting immigration-related
sharing does **not** establish absence of `ConfiguredAccess` — that is the outline §8.12 contradiction, and
it is the reason `immigration_enforcement_access` is `NO_RESOLUTION` by default (§8.2).

**Temporal semantics of a single snapshot.** A portal snapshot on 2026-07-15 listing partner B supports
exactly:

```
Claim{ subject: A, predicate: configured_sharing_partner_present,
       object: B, valid_time: [2026-07-15, 2026-07-15], observed_time: 2026-07-15 }
```

It does **not** support `valid_from = unknown, valid_to = open`. Interval construction requires ≥2
snapshots, and even then SIG emits an *inference*:

```
INFER continuous_presence(A→B, [t1, t2]) FROM present_at(t1) AND present_at(t2)
  WHERE (t2 − t1) ≤ 2 × volatility_halflife(configured_sharing_partner_set)   # ≤ 8 months
  LABEL: INFERENCE, confidence: PROBABLE, invalidated_by: any snapshot in (t1,t2) lacking B
```

Beyond the gap limit, SIG publishes two point observations and an explicit `coverage_gap`, not a line.

**Asymmetry handling.** If A's portal lists B as an outbound partner and B's portal does not list A as an
inbound partner, that is **not** reconciled. It emits:

```
Contradiction{ type: SHARING_ASYMMETRY, severity: MEDIUM,
               parties: [A, B], observed: [snapshot_A@t, snapshot_B@t'],
               candidate_causes: [snapshot_time_skew, portal_scope_difference,
                                  one_portal_lists_only_agencies_not_all_orgs,
                                  genuine_configuration_asymmetry, portal_staleness],
               task: OBTAIN_CONTEMPORANEOUS_SNAPSHOTS }
```

Both edges are published with their own provenance. Union and intersection are both wrong: union
fabricates access, intersection erases it.

**Failure modes.** (a) *Snapshot skew* — the most common false asymmetry; SIG must record snapshot time to
the second and refuse to compare snapshots more than 14 days apart without flagging skew as the leading
candidate cause. (b) *Entity resolution* — a partner named "Springfield PD" must resolve to a canonical org
before comparison; unresolved names go to §9.7, not into the edge set. (c) *Scope difference* — some
portals list only law-enforcement partners and omit private-camera contributors; the connector must record
`list_scope` per portal or the asymmetry detector will fire constantly.

## 9.4 Deployment lifecycle reconciliation (outline §11.4, §6.7)

**The correction:** the outline's thirteen states are values from **three independent state machines**.
F13.29 (Syracuse) is the proof: on one date the deployment was commercially terminated, physically present,
and operationally unknown. No single field can hold that.

```
Track P — procurement/commercial
  none → proposed → approved → contracted → { renewed ⇄ contracted }
                                          → nonrenewed → expired
                                          → terminated
  (also: contracted → amended → contracted)

Track H — hardware/physical
  none → installing → installed → { present_powered ⇄ present_unpowered }
                                → removing → removed
  (also: installed → replaced_in_place)

Track O — operational
  not_operating → piloting → active → { restricted ⇄ active }
                                    → suspended → active
                                    → deactivated
```

Plus a **cross-deployment edge** `replaced_by(Dp_old, Dp_new)` with `replacement_scope ∈
{same_capability, reduced_capability, expanded_capability}` and `evidence[]`.

**Algorithm.**

```
LIFECYCLE(deployment Dp):
 1 collect all dated LifecycleEvent claims for Dp
 2 for each event: assign it to exactly one track via the event-type→track map
      (a "contract canceled" event writes ONLY to track P; it may not write to H or O)
 3 normalize dates to intervals: exact → [d,d]; "March 2026" → [2026-03-01, 2026-03-31];
      "spring 2026" → [2026-03-01, 2026-05-31]; "by mid-year" → [-inf, 2026-06-30]
 4 within each track, order events by Allen interval precedence on their date intervals:
      e_i precedes e_j iff e_i.latest < e_j.earliest        (strict, unambiguous)
      if intervals overlap, order is UNDETERMINED
 5 for undetermined pairs: if the transitions are compatible in the track's automaton in
      exactly one order, adopt that order and set order_source = TOPOLOGY
      else emit both orderings, set timeline.order_uncertain = true, and emit a task
 6 walk each track's automaton; an event that is not a legal transition from the current
      state emits Contradiction(ILLEGAL_TRANSITION) and is held out of the walk
 7 state(track, t) := the state after the last event with latest ≤ t;
      if the most recent event in a track is older than 3× that track's volatility half-life,
      state := UNRESOLVED(reason = STALE)   # this is what produced Syracuse's operational UNKNOWN
 8 detect replacement:
      if track P reaches {terminated, nonrenewed, expired} for vendor V
      and a deployment exists for the same organization with a different vendor V'
      and same capability, with proposed/approved/contracted date within ±18 months
      then assert replaced_by(Dp, Dp') as an INFERENCE, and set
      surveillance_continuity = CONTINUED | REDUCED | EXPANDED
      based on comparing resolved device counts and capability sets
 9 NEVER emit a summary string containing "surveillance removed" unless
      track H = removed AND track O = deactivated AND no replaced_by edge exists
```

Step 9 is a hard output guard, not a stylistic preference. It is the operational form of §22.5.

**Failure modes.** (a) *A news article reporting "the city canceled Flock"* is a track-P event only; the
connector's event-type map must not let it set hardware or operational state — this is the single most
likely path to the false conclusion. (b) *Fuzzy-date cascades* — a chain of month-granularity events can
leave a whole timeline `order_uncertain`; SIG publishes it as such rather than picking. (c) *Replacement
false positives* — an agency adding a second vendor without dropping the first is not replacement; the
detector requires track P to have reached a terminal state. (d) *Replacement false negatives* — the new
vendor's procurement is often not public until after the old contract ends; the ±18-month window is
generous by design and the resulting edge is an inference, revisited on every recompute.

## 9.5 Retention reconciliation (outline §8.12, extended by F13.30)

**Three (not two) layers.** `vendor_default_retention_days` (subject = Vendor·Product) →
`policy_retention_days` (subject = Organization, from the written policy) →
`configured_retention_days` (subject = Deployment, from portal/config export).

**Algorithm.** Resolve all three independently. Then:

```
if configured RESOLVED and policy RESOLVED and configured ≠ policy:
    emit Contradiction(POLICY_CONFIGURATION_DIVERGENCE, severity = HIGH,
                       direction = (configured > policy ? RETAINS_LONGER_THAN_POLICY
                                                        : RETAINS_SHORTER_THAN_POLICY))
    # publish BOTH. Never resolve to one. (strategy = NO_RESOLUTION for the pair predicate)
if configured UNRESOLVED and vendor_default RESOLVED:
    emit Inference(configured ≈ vendor_default) at PROBABLE, label INFERENCE,
         invalidated_by: any deployment-level evidence, and by any vendor default change
if a vendor default change is observed:
    invalidate every deployment-level inference derived from the old default,
    and emit a bulk research task per affected jurisdiction
```

The `direction` field matters editorially: an agency retaining *longer* than its own policy is a compliance
finding; retaining *shorter* is usually not. Collapsing them into "policy mismatch" loses the story.

**Failure modes.** Units (days vs hours vs "30 days for non-hits, 1 year for hits") — retention is often
*conditional*, so the value domain must be a structured `{scope → days}` map, not a scalar, and a scalar
claim from a source that only gave one number is `count_basis`-equivalent ambiguous.

## 9.6 Cost / contract-value reconciliation

**Inputs.** Executed contract value; amendment values; purchase orders; invoice line items; adopted budget
lines; council-approved not-to-exceed amounts; vendor public statements.

**Algorithm.** These are *different quantities* and are separate predicates:
`contract_total_value`, `contract_annual_value`, `not_to_exceed_amount`, `invoiced_to_date`,
`budgeted_amount`. Resolve each. Then run **arithmetic consistency checks** as detectors, not resolvers:

```
if invoiced_to_date > not_to_exceed_amount               -> Contradiction(OVERSPEND, HIGH)
if contract_annual_value × term_years ≉ contract_total_value (±2%)
                                                          -> Contradiction(ARITHMETIC_INCONSISTENCY, MEDIUM)
if budgeted_amount < contract_annual_value                -> Contradiction(BUDGET_SHORTFALL, LOW)
if Σ(invoice line items) ≠ invoice header total           -> Contradiction(EXTRACTION_SUSPECT, MEDIUM)
```

**Failure modes.** (a) Multi-year vs annual conflation is the dominant error and must be caught by
requiring `value_period` on every money claim. (b) Bundled contracts (ALPR + drone + RTCC on one PO) —
SIG must record `allocable: false` and refuse to attribute the full value to the ALPR deployment;
publishing an unallocated bundle value as an ALPR cost is a real-world misreporting risk. (c) Grant-funded
purchases appear in neither the city budget nor the invoice stream.

## 9.7 Organization-existence reconciliation

**Trigger.** A sharing-network list, audit log, or portal names an organization SIG's registry does not
contain (outline §12 "New sharing node").

**Algorithm.**

```
 1 normalize the string (expand PD/SO/DPS, strip "City of", canonicalize state)
 2 deterministic match against: ORI registry (≈15,000 US LE agencies, 9-char codes),
   state incorporation/municipality registries, Census place FIPS, prior SIG aliases
 3 if unique deterministic match -> assert alias, done (no inference label needed)
 4 if fuzzy match only -> DO NOT WRITE. Emit ResearchTask(RESOLVE_ORG_IDENTITY) with
   ranked candidates and their evidence.        # outline Q28: fuzzy => review queue
 5 if no match at all -> create a provisional org shell with
   existence_status = ASSERTED_BY_NETWORK_LIST_ONLY, and predicate
   org_exists resolved at support = PROBABLE, agreement = UNCONTESTED,
   with an explicit note that a network-list mention is first-party evidence of
   *something* but not of legal existence, jurisdiction, or type
 6 classify: is this a public agency, a private business, a school district, a hospital,
   an HOA, or a vendor-internal test account? Each has different publication ethics.
```

**Failure modes.** (a) Test/demo accounts in vendor networks look like real orgs and must not be published
as agencies. (b) Private HOAs and businesses raise §13.1 "observe institutions not individuals" concerns —
a single-family-adjacent HOA camera contributor is close to an individual; publication policy (R-privacy
workstream) governs. (c) Multi-state name collisions ("Springfield PD") are the canonical entity-resolution
trap and must never be resolved by string similarity alone.

## 9.8 Capability reconciliation

**Question form:** does agency X have capability Y (facial recognition, cell-site simulator, gunshot
detection, drone), per N disagreeing sources?

**Algorithm.** Capability is `TRACK_SEPARATE` (§8.1) — the first step is *ontology normalization*, because
sources disagree about the question, not the answer. "Facial recognition" in an Atlas row may mean the
agency runs FR software, has access to a state FR system, or has requested searches from a fusion center.
SIG splits into `capability_operated`, `capability_accessible_via_partner`, `capability_requested_from_third_party`,
`capability_piloted_historically`. Only after splitting does `MAX_SUPPORT` run per sub-predicate.

`deployment_exists`/`capability_present` **never resolves to `false`** from source silence (§9.4 of the
outline). The only paths to a negative are (a) an explicit first-party denial (`W3`+, and it resolves
`capability_operated = false` with `agreement` reflecting any contrary evidence), or (b) a records response
stating no responsive records exist — which SIG models as its own predicate, `no_responsive_records`, with
the requesting party, date, and request scope, and which supports a negative only within that scope.

**Failure modes.** Vendor rebranding (Vigilant → Motorola) makes the same capability appear as two;
capability inheritance from a parent agency is an inference (§10.5), not a fact.

## 9.9 Geographic-coverage reconciliation

**Question form:** what share of a jurisdiction's road network is under ALPR observation, and how does that
compare across jurisdictions?

**Algorithm.** This is a derived metric, never a claim. Compute per jurisdiction:

```
observed_ingress_ratio := (# of road segments crossing the jurisdiction boundary that have a
                           mapped ALPR within 150 m) / (total boundary-crossing segments of
                           functional class ≥ residential)
device_density         := mapped_device_count / centerline_km
corridor_coverage      := fraction of the jurisdiction's principal-arterial length within
                          200 m of a mapped device
```

Every one of these is computed from `mapped_device_count`, which is a **lower bound** (F13.23, F13.4). SIG
must therefore publish each with `is_lower_bound: true` and a companion coverage figure, and must never
render a choropleth that visually implies "this county has less surveillance" when it may only have fewer
mappers. **Rule: no geographic-coverage visualization may be published without the mapping-coverage layer
rendered alongside it.**

**Failure modes.** The dominant failure is mapper-density confounding, which is severe and not correctable
by the data alone; see §12.4.

---

# 10. Design — the inference catalog

## 10.1 Derived values are not claims, and `mapped_device_count` is the worked case

A **claim** is something a source asserted. A **derived value** is something SIG computed. They are
different kinds of object, they live in different tables, and conflating them is the mechanism by which a
project like SIG launders its own guesses into its own evidence base.

`mapped_device_count` is the case that makes the distinction concrete. No source ever says "31 devices are
mapped for this agency." SIG computes it by counting the assets whose attribution to that agency currently
resolves. It therefore:

- is **not** resolved by §7.3 — there are no competing claims to reconcile;
- has **no** `support`/`agreement`, because those are properties of evidence about a value and there is no
  evidence *about this value*, only evidence about its inputs;
- carries instead `derived: true`, `derivation_rule_id`, `inputs_digest`, `computed_at`,
  `ruleset_version`, and `is_lower_bound: true`;
- is **recomputed, never corrected** — a wrong `mapped_device_count` is always a wrong input or a wrong
  rule, and fixing it anywhere else is a bug.

The general rule, applied to every entry in this catalog:

> **Derivation rule.** A derived value's provenance is a *provenance expression* over base claim ids
> (F13.11), not a citation list: conjunctive dependence multiplies, alternative derivations add. Its
> weight is at most `min(W)` over its conjunctive inputs, minus one weight class for the derivation
> itself, and it can never exceed `W3`. **No derived value is ever `W4`.** Nothing SIG computed is
> dispositive.

That last sentence is the whole of §10 compressed. Everything below is its application.

## 10.2 The inference record, and the labeling rule

Every entry in this catalog emits one object shape:

```yaml
inference:
  id: inference/<uuid>
  rule_id: I-ATTR-01              # stable; versioned with the ruleset
  ruleset_version: 1.4.0
  label: INFERENCE                # never OBSERVATION, never RECORD
  subject: <entity>
  predicate: <predicate>
  value: <value>
  provenance_expression: "c/8812 · c/8813 + c/9001"    # §10.1, F13.11
  inputs_digest: sha256(...)
  weight: W2
  confidence: PROBABLE            # from the §7.2 vocabulary, never a bare number
  score_breakdown: [...]          # for scored rules (§9.2)
  candidates_rejected: [...]
  invalidated_by: [<condition>, ...]   # REQUIRED, non-empty
  hop_bound_applied: 2            # for transitive rules
  computed_at: <ts>
```

Three rules bind all of them, and they are the rules the outline's §19.2 asks for without specifying:

1. **`label` is structural, not cosmetic.** It travels into every export row, every API response, and
   every rationale sentence. A consumer that filters `label = INFERENCE` must get a dataset containing no
   SIG-computed values at all, and that filter must be a CI-tested property of the export.
2. **`invalidated_by` may not be empty.** An inference that nothing could falsify is not an inference; it
   is an assumption, and it must not ship. This is testable at ruleset-load time.
3. **An inference is never an input to an inference of the same family.** Attribution inferences do not
   feed the attribution corridor feature (§9.2 failure mode (a)); a derived access path is not a hop in a
   longer derived access path (§10.6); a derived FOV is not evidence that a device exists (§10.3). Without
   this rule every scored inference in the catalog self-amplifies.

## 10.3 `I-FOV` — derived field of view and observation geometry

**Question form:** which stretch of road can this device plausibly read?

**Inputs.** OSM `direction` (present on 93.6% of ALPR nodes — F13.23), `camera:type`, `camera:mount`,
the nearest highway way's geometry and functional class, and the manufacturer's published read range and
lens angle where SIG has a cited figure for that model.

**Output.** An `ObservationGeometry`: a *sector on the road centerline* — bearing, half-angle, range —
never a filled polygon of certainty, and never a claim about any vehicle.

**The constraints are the design.**

- **The output half-angle is the sum of the optical half-angle and the tag's own quantization.** OSM
  `direction` is routinely an 8-point compass value, which is ±22.5° of pure encoding error before any
  optics are considered. A model that reports a ±15° optical cone from a ±22.5° input is reporting
  precision it does not have.
- **Manufacturer read-range figures are `R2`/`D5` vendor marketing.** They are ruleset parameters with a
  cited source, not constants in code, and the rendered geometry names them.
- **`I-FOV` is `D6` for every other predicate.** A derived FOV is non-probative for `asset_exists`,
  `active_device_count`, `asset_operator`, and coverage. It is an output of the graph and never an input
  to it. In particular it must not feed §9.9's coverage ratios: those are already built on a lower bound
  (F13.23), and stacking a model on a lower bound produces a number with no defensible interpretation.
- **No vehicle-level inference, ever.** SIG models institutions (§13.1 of the outline). `I-FOV` answers
  "what road segment is within this device's stated capability," and SIG must not possess, derive, or
  publish anything about who traversed it.
- **Rendering rule.** Graded sector with the model's parameters visible on hover, plus an explicit
  "modelled, not observed" label. A hard-edged coverage polygon is prohibited: it is the visual form of
  the false-precision failure this whole file exists to prevent.

**Invalidation.** Any edit to the node's `direction`, `manufacturer`, or `camera:*` tags; any change to the
road geometry or its version; any change to the model parameters. Because FOV is derived, all of these are
recomputes, not corrections.

## 10.4 `I-ATTR` — device attribution

Specified in full at §9.2; catalogued here for completeness and for the three properties every catalog
entry must declare.

| Property | Value |
|---|---|
| Emits | `asset –probable_operator→ agency`, `label: INFERENCE`, `attribution_cardinality` |
| Never emits | `owner`, `data_controller`, or `operator` (the observed predicate) |
| Weight ceiling | `W2` — see §10.1; a scored geographic inference is never strong evidence |
| Publishes an edge only when | `score ≥ 8` **and** unique top scorer **and** margin ≥ 3 |
| Otherwise | a `ResearchTask(ATTRIBUTE_DEVICE)` with ranked candidates, or silence below 4 |
| `invalidated_by` | any observed `operator` tag; any records-derived attribution; any boundary-dataset version change; any change to the candidate deployment's evidence |
| Feedback guard | inferred attributions are excluded from feature C6 and from `field_verified_device_count` |

The one thing worth restating: **attribution never resolves `asset_operator`** (§8.2 assigns that
`AUTHORITATIVE_SOURCE_WINS`, else `NO_RESOLUTION`). An inferred `probable_operator` edge and a resolved
`asset_operator` value are different predicates with different names, and the export must keep them in
different columns. Merging them at any layer — storage, API, tile — reintroduces exactly the laundering
this section forbids.

## 10.5 `I-ORG` — organizational hierarchy, and why capability does not inherit

Organizations relate in at least three ways that look alike in a graph and behave nothing alike:

| Relation | Example | Propagates downward | Propagates upward |
|---|---|---|---|
| `part_of` (true hierarchy) | a division of a state police agency; a precinct of a city PD | **constraints only** | **containment only, as a named predicate** |
| `governed_by` (jurisdictional) | a city PD and its city council | authority and policy, *if evidenced* | nothing |
| `member_of` (association) | a fusion centre; an ALPR-sharing task force; a mutual-aid compact | **nothing** | **nothing** |

**Downward: constraints, not capabilities.** From `B part_of A` SIG may derive that B's jurisdiction is
contained in A's, and that B's authorization cannot exceed A's — these are *upper bounds* and they are
useful precisely because they can generate contradictions (a subordinate unit operating outside its
parent's jurisdiction is a finding). SIG may **not** derive that B operates what A operates. A sheriff's
office having ALPR says nothing about the county constable; a state police agency running facial
recognition says nothing about an individual troop.

**Upward: containment, under a different predicate.** If B operates technology T, SIG may assert about A
only `capability_present_in_subordinate_unit(A, T, via: B)` — never `capability_operated(A, T)`. This is
the same split §9.8 makes for `capability_accessible_via_partner`, applied to hierarchy instead of
partnership, and for the same reason: a reader who sees "the State of X operates ALPR" cannot tell whether
that means a statewide programme or one county unit, and those have completely different policy
consequences.

**Membership propagates nothing, in either direction.** This is the most common real-world error in this
domain and it must be a hard rule rather than a caution. A fusion centre's capability is not its member
agencies' capability; a task force's ALPR access is not each member department's ALPR access; a member
agency's contract is not the task force's contract. Where a member agency's personnel can in fact use a
shared system, that is an **access** fact (§10.6), evidenced by a configuration export or an audit log,
not a hierarchy inference.

**Hop bound.** Downward constraint propagation is bounded at 1 hop per derivation step and re-derived at
each level, so that every intermediate assertion carries its own provenance and can be independently
contradicted. Upward containment roll-up may span the full tree but **must name every subordinate it
aggregated** in the value, or it is not publishable.

## 10.6 `I-PATH` — access-path transitive closure, and exactly how far transitivity is legitimate

This is the highest-stakes rule in the catalog, because the question it is tempting to answer with it —
*can a federal immigration agency reach this city's plate data through some chain of sharing agreements?* —
is the single question in this domain with the largest gap between public interest and available evidence.

**The default is: no closure.** `ConfiguredAccess(A→B)` and `ConfiguredAccess(B→C)` do **not** imply
`ConfiguredAccess(A→C)`. Transitivity is a property of the *platform's re-sharing semantics*, not of the
graph's shape, and SIG does not know those semantics unless it has evidence of them.

**The mechanism gate.** Every `DataSystem` carries
`resharing_semantics ∈ {none, explicit_reshare_permitted, transitive_by_default, unknown}` with its own
evidence and its own `R`/`D`/`I`/`C`. Closure is computed **only** where that field resolves to
`explicit_reshare_permitted` or `transitive_by_default`, on evidence at `W3` or better — vendor
documentation, a configuration export showing a re-shared network, or a first-party agency statement.
`unknown` is the default and produces no paths. Absence of evidence about the mechanism is not evidence
that the mechanism exists.

**Where closure is licensed, five constraints bind it:**

1. **Hop bound = 2** (one intermediary). F13.11 is the formal reason: recursive derivation over a graph
   with cycles — and sharing graphs are cyclic — generates provenance as a formal power series, which is
   unbounded and cannot be rendered in a rationale sentence. It is also the practical reason: no evidence
   in this domain supports a 3-hop claim, and a path that cannot be explained in one sentence cannot be
   defended in a council meeting.
2. **Temporal intersection, not union.** The path is valid only over `INTERVAL_INTERSECTION` (§8.1) of its
   hops' validity. Since a portal snapshot supports a *point* interval only (§9.3), a two-hop path built
   from two snapshots yields a point-in-time claim, and only if the snapshots are contemporaneous under
   §9.3's 14-day skew rule. A path assembled from a March snapshot and an August snapshot is not a path.
3. **Scope intersection, not union.** Access scope — which cameras, which time window, which capability,
   which user population — intersects along the path. If either hop's scope is unknown, the path's scope
   is unknown, and an access path of unknown scope is **not publishable as an access claim**; it is
   publishable only as a research task.
4. **Weight.** `W(path) = min(W(hops)) − 1`, capped at `W2` by §10.1. A derived path is never strong
   evidence and never dispositive.
5. **Distinct type, distinct rendering.** The output is an `InferredAccessPath`, never a
   `ConfiguredAccess` edge. It has its own entity type, its own colour in every visualization, its own
   API field, and its own export resource. It must never be counted in network-topology metrics that also
   count observed edges.

**The two things `I-PATH` may never do:**

- **It may never satisfy `immigration_enforcement_access`.** §8.2 assigns that predicate
  `NO_RESOLUTION` unless a `W4` configuration export exists. A two-hop inference is `W2` by construction
  and therefore cannot reach it. This is deliberate and it is the most important single line in this
  section: the highest-stakes question is the one where inference is most tempting, most likely to be
  quoted, and most damaging if wrong in either direction. SIG publishes the observed edges, the scope of
  each, and the open question — not a derived answer.
- **It may never convert a human intermediary into an access path.** An audit log showing that a user at
  agency B ran a query whose stated reason names agency C is evidence of
  `lookup_performed_on_behalf_of(B, C)` — a distinct predicate, evidenced by the reason field, and
  editorially significant in its own right. It is **not** evidence that C has configured access to A's
  data, and the two must never be merged. Most of the real reported misuse in this domain takes exactly
  this shape, and getting it wrong in the friendly direction ("no configured access, therefore no
  access") is as bad as getting it wrong in the alarming one.

**Cycles.** Path enumeration uses a visited set and the hop bound. SIG stores **paths**, each with its own
provenance expression, and never a materialized transitive-closure relation — a closure table has no place
to put the per-path scope, interval, and provenance that make each path individually defensible.

## 10.7 The rest of the catalog

Three further inferences are specified elsewhere in this file and are listed here so the catalog is
complete and so their common properties are enforced by the same machinery:

| Rule | Emits | Specified at | Weight ceiling | `invalidated_by` |
|---|---|---|---|---|
| `I-TEMP` continuous presence | `continuous_presence(A→B, [t1,t2])` from two point snapshots within 2× the predicate half-life | §9.3 | `W2` | any snapshot inside `(t1,t2)` lacking B; any gap exceeding the half-life bound |
| `I-RET` vendor-default inheritance | `configured_retention_days ≈ vendor_default` at `PROBABLE` | §9.5 | `W1` | **any** deployment-level evidence; any observed change to the vendor default |
| `I-REPL` vendor replacement | `replaced_by(Dp_old, Dp_new)` + `surveillance_continuity` | §9.4 step 8 | `W2` | track P not reaching a terminal state; a second concurrent vendor without termination |

## 10.8 What SIG does not infer

An inference catalog is defined as much by its exclusions, and these are load-bearing rather than modest:

- **Existence from absence.** No rule may conclude `deployment_exists = false`, `capability_present =
  false`, or `asset_removed` from any source's silence (§9.8). The only routes to a negative are a
  first-party denial or a scoped `no_responsive_records` finding.
- **Counts from money.** SIG does not divide a contract value by a unit price to infer device count.
  Bundled contracts (§9.6 failure mode (b)) make this arithmetic wrong in an unbounded direction and the
  result would be quoted as if it were counted.
- **Operation from installation.** A mapped device is not an operating device (F13.29, Syracuse). No rule
  may promote a hardware-track fact into an operational-track fact.
- **Policy compliance from policy existence.** A written policy is evidence of a written policy (§9.5).
- **Source quality from agreement with SIG.** SIG does not compute endogenous source-trust scores and
  feed them back into resolution (F13.7). Sources are graded by a published, human-written registry row.
  A source that frequently loses resolutions generates an editorial review task, never an automatic
  downgrade.
- **Anything about a person.** No inference in this system takes a natural person as subject or produces
  one as output, with the single exception of public officials acting officially.

---

# 11. Design — the `Contradiction` entity and the detector→task contract

## 11.1 What is, and is not, a contradiction

The word does two jobs in the outline and they must be separated. `UNRESOLVED` is a property of a
*resolution* at a moment (§7.4). A `Contradiction` is a **persistent entity** with an identity, a
lifecycle, a disposition, and an owner. Every `IRRECONCILABLE` agreement implies an open `Contradiction`;
the converse does not hold, because most contradictions do not block resolution.

**A contradiction exists when** two or more admissible claims about the same `(subject, predicate)` with
overlapping validity assert incompatible canonical values, from at least two independent classes (§6.2),
with at least one side above `W1` — **or** when one of the structural detectors below fires. Structural
contradictions have no possible "winner" and that is what distinguishes them: they are findings about the
evidence, not competitions between values.

**A contradiction does not exist when:**

- the values belong to **different predicates** — "contract says 42, portal says 38" is the §4.5/§9.1
  category error and is prevented at Phase 2.3, not recorded as a disagreement. Recording it as a
  contradiction would manufacture thousands of false ones on day one;
- a claim is superseded by its own source's later correction (Phase 1.4);
- values differ within the predicate's `tolerance` (`MINOR_DISAGREEMENT`, not contradiction);
- there is no evidence, weak evidence, or only stale evidence (`U0`, `U1`, `U5`). **Absence is not
  contradiction**, and conflating them is how a coverage problem gets published as a dispute;
- the disagreement is between a value and an *inference* — an inference that conflicts with an observation
  is simply an invalidated inference (§10.2 rule 2), and it is retracted, not litigated.

## 11.2 The entity

```yaml
contradiction:
  id: contradiction/8812
  type: POLICY_CONFIGURATION_DIVERGENCE
  severity: HIGH                       # LOW | MEDIUM | HIGH | BLOCKING
  subject: organization/example-county-so
  predicates: [policy_retention_days, configured_retention_days]
  parties: [organization/..., organization/...]     # for two-party types
  sides:                               # claims grouped by asserted value
    - {value: 30,  claim_ids: [c/4401], classes: [k1], best_weight: W3}
    - {value: 365, claim_ids: [c/5510], classes: [k2], best_weight: W3}
  direction: RETAINS_LONGER_THAN_POLICY       # type-specific, editorially meaningful
  detected_by: {rule_id: X-RET-02, ruleset_version: 1.4.0}
  first_detected_at: 2026-06-02T00:00:00Z
  last_confirmed_at: 2026-08-20T14:00:00Z
  recurrence_count: 7                  # detector re-fired this many times
  signature: sha256(type + subject + predicates + sorted value set)
  status: OPEN                         # §11.5
  candidate_causes: [policy_superseded_undocumented, configuration_drift,
                     portal_reports_a_different_scope, extraction_error]
  discriminating_evidence:             # what would settle it — the task contract
    - {type: config_export, must_cover_window: "after 2025-11-02"}
    - {type: written_agency_statement, must_name: retention_scope}
  task_ids: [task/4471]
  resolution: null
  publication: {visible: true, blocks_resolution: false}
```

**Type vocabulary**, drawn from the detectors this file already specifies plus three additions:

| Type | Emitted at | Default severity |
|---|---|---|
| `VALUE_DOMAIN_MISMATCH` | Phase 2.2 | LOW |
| `PREDICATE_CONFLATION` | Phase 2.3 | MEDIUM |
| `COUNT_DISAGREEMENT` | §9.1, F13.26 | MEDIUM |
| `POLICY_CONFIGURATION_DIVERGENCE` | §9.5 | HIGH |
| `SHARING_ASYMMETRY` | §9.3 | MEDIUM |
| `ILLEGAL_TRANSITION` | §9.4 step 6 | MEDIUM |
| `ORDER_UNDETERMINED` | §9.4 step 5 | LOW |
| `OVERSPEND` | §9.6 | HIGH |
| `ARITHMETIC_INCONSISTENCY` | §9.6 | MEDIUM |
| `BUDGET_SHORTFALL` | §9.6 | LOW |
| `EXTRACTION_SUSPECT` | §9.6 | MEDIUM |
| `UNDECLARED_DEPENDENCE_SUSPECTED` | §6.4 | LOW |
| `ENTITY_IDENTITY_CONFLICT` | §9.7 | MEDIUM |
| `TEMPORAL_IMPOSSIBILITY` | new — a claim dated before its subject existed, or a device predating the vendor | MEDIUM |
| `SOURCE_SELF_CONTRADICTION` | new — one source asserts both values in the same publication | MEDIUM |

**Severity semantics, stated precisely because they are easy to get wrong:**

- `LOW`/`MEDIUM`/`HIGH` are **editorial priority only**. They change what a curator sees first and what a
  dossier surfaces prominently. They do **not** change any published value.
- `BLOCKING` is the only severity that alters resolution behaviour, via `U7`, and it is **never assigned
  by a detector**. Only a maintainer may set it, it requires a written reason, and it is a
  publication-safety act with the same visibility obligations as a pin (§7.7). The machine must not be
  able to block itself, or determinism (§7.6) is lost.
- Severity is otherwise fixed per type in the ruleset, not chosen per instance, so that two identical
  situations are ranked identically.

## 11.3 Detection

Contradiction detectors are ruleset **data**, exactly like resolution rules (§7.1), and they obey the
same constraints:

- **Pure queries.** A detector may not call an external service and must be re-runnable against a
  historical claim store to produce the identical contradiction set.
- **They run on the §7.6 recomputation triggers**, not on a separate schedule, so that a contradiction and
  the resolution it concerns are always computed from the same inputs.
- **Deduplication is by `signature`** — `(type, subject, predicates, sorted value set)`. A re-firing
  updates `last_confirmed_at` and increments `recurrence_count`; it never creates a sibling. A *changed*
  value set is a different signature and therefore a different contradiction, which is what makes
  "the disagreement moved" visible rather than silent.
- **Detectors never mutate resolutions.** The only coupling from contradiction to resolution is `U7`, and
  `U7` keys on a human-set `BLOCKING` flag. This is the same rule as §6.4's for the copy detector and it
  exists for the same reason.
- **The one exception is asymmetric and deliberate:** a `PREDICATE_CONFLATION` or `VALUE_DOMAIN_MISMATCH`
  contradiction is emitted *by* the resolution algorithm during Phases 2.2–2.3, in the course of dropping
  a claim. Those are recorded as a side effect of resolution, which is why the resolver must be able to
  emit them atomically with the `ResolvedView` and with the same `input_digest`.

## 11.4 The detector → task contract

An open contradiction that generates no task is a complaint. The contract that turns it into work is
mechanical and is enforced at ruleset-load time:

**Every contradiction type MUST declare, in the ruleset:**

| Field | Meaning | CI check |
|---|---|---|
| `candidate_causes[]` | the enumerated explanations, ordered by prior likelihood | non-empty |
| `discriminating_evidence[]` | what artifact, covering what window, would distinguish among them | **non-empty — a detector that cannot say what would settle it must not ship** |
| `task_template` | the research task to generate | resolves to a known task rule |
| `assignee_class` | who can close it | in the assignee vocabulary |
| `auto_dormant_after` | when an unactioned contradiction goes `DORMANT` rather than ageing forever | present |
| `severity` | fixed per type | never `BLOCKING` |

**And the binding rules:**

1. **The generated task's `required_evidence` *is* the contradiction's `discriminating_evidence`.** It is
   not written twice and cannot drift. The task promises exactly what the detector says would settle the
   question.
2. **Task completion re-runs the detector, and the detector decides.** If it no longer fires, the
   contradiction transitions automatically to `RESOLVED_SUPERSEDED` with the closing evidence attached.
   If it still fires, the task cannot close — the reviewer's judgement does not override the detector,
   because the detector is the published definition of the problem.
3. **One open task per contradiction**, keyed on the contradiction id, so a contradiction that re-fires
   seven times does not generate seven tasks.
4. **Priority is computed, not assigned**, from severity, the number of published values depending on the
   contradiction's subject, the prominence of the parties, and `recurrence_count` — a contradiction that
   has re-fired every week for two months is either important or a false positive, and both deserve
   attention.
5. **A contradiction implicating a partner's own published data is routed to that partner before SIG
   publishes anything derived from it**, on a bounded window. This is the reconciliation-engine end of the
   contribution-back contract; the routing table itself belongs to the ecosystem workstream.

## 11.5 Resolution, and how a resolved contradiction stays visible

**Six terminal dispositions**, and the third and fourth are the ones most systems lack:

| Disposition | Meaning | Consequence |
|---|---|---|
| `RESOLVED_SUPERSEDED` | new evidence arrived; the detector no longer fires | resolution recomputes normally |
| `RESOLVED_CORRECTED` | a source corrected itself, or SIG corrected an extraction | the corrected claim is retracted non-destructively (F13.31) |
| `RESOLVED_BOTH_TRUE` | the values measure different things or different times | **requires a predicate split** — a ruleset change, reviewed, with a diff report. This is the honest outcome for most `COUNT_DISAGREEMENT`s |
| `IRRECONCILABLE_PUBLISHED` | SIG cannot resolve it and says so permanently | both values published side by side with provenance, forever; the resolution stays `UNRESOLVED`; **this is a legitimate terminal state, not a failure** |
| `DISMISSED_FALSE_POSITIVE` | the detector was wrong | **must** produce either a ruleset change or a recorded written justification for leaving the rule as it is |
| `DORMANT` | the subject ceased to exist, or the evidence aged out of relevance | retained, not deleted |

**Permanent visibility is the whole point.** A resolved contradiction:

- is **never deleted and never hidden**. It remains attached to its subject and to every claim it
  involved, and the `ResolvedView` carries `contradictions_resolved[]` alongside `contradictions_open[]`;
- appears on the entity page in an always-present "previously contested" section showing the dates, the
  values, the disposition, and who dispositioned it. This is F13.31's retained-retraction precedent
  generalized from claims to disagreements;
- **reopens automatically** if the detector fires again with a *different* signature, carrying a link to
  the prior instance — so a retention value that flips back and forth reads as a pattern rather than as a
  series of unrelated incidents;
- is included in the ruleset diff report (§7.6) when a ruleset change would alter its status, because
  "SIG stopped considering this a contradiction" is exactly the kind of change an external reader is
  entitled to see.

**Three prohibitions:**

- **A contradiction may never be closed by choosing a value without evidence.** That act exists, it is
  called a pin (§7.7), it expires, and it is labelled. Anything that walks like a pin must be a pin.
- **A contradiction may never be closed to make a dossier look cleaner.** Dispositions are evidence-driven
  and the disposition rationale is published.
- **`IRRECONCILABLE_PUBLISHED` may not be used to avoid work.** It requires a written statement of what
  evidence would resolve it and why that evidence is believed to be unobtainable — and it converts to
  `OPEN` the moment that belief is falsified.

## 11.6 Where contradictions surface

Contradictions are **output**, not defects, and the surfaces follow from that:

1. **On the value.** Every `ResolvedView` carries its open and resolved contradiction ids; a value with an
   open `HIGH` or `BLOCKING` contradiction cannot be rendered anywhere without its contradiction marker.
2. **On the entity page**, as a first-class section rather than a footnote.
3. **In the jurisdiction dossier**, because "the city says 40, the portal says 75, the contract says 78"
   is frequently the most newsworthy thing SIG knows about a jurisdiction.
4. **In the exports**, as their own resource with the full entity shape — a consumer must be able to
   download every contradiction SIG holds without scraping entity pages.
5. **In the diff feed**, on open, on disposition, and on reopen.
6. **In the quality report** (§12.6), as counts, ages and false-positive rates per detector.

---

# 12. Design — coverage and quality metrics

## 12.1 The naming rule that prevents the central error

Every metric in this section is a statement about **SIG's evidence**, not about the world. That
distinction is not rhetorical: a reader who sees "Cochise County: 12% coverage" will conclude something
about Cochise County, and will be wrong.

> **Naming rule.** Metrics describing SIG's evidence are prefixed `evidence_` or `coverage_` and their
> published label must name the denominator. SIG publishes **no** metric that purports to describe the
> total quantity of surveillance infrastructure in a place. `total_devices_in_jurisdiction` is
> `NO_RESOLUTION` (§8.2) and stays that way.

The corollary, already stated at §9.9 and repeated here because it is the highest-traffic surface: **no
geographic-coverage visualization may be published without the mapping-coverage layer rendered alongside
it.** A choropleth of device density is a map of where mappers live until proven otherwise.

## 12.2 Per-jurisdiction coverage metrics

All measured, none inferred, each published with its denominator:

| Metric | Definition | Why it matters |
|---|---|---|
| `coverage_agencies_with_any_evidence` | agencies with ≥1 admissible claim ÷ agencies in the registry for that jurisdiction | the base rate for everything else |
| `coverage_deployment_evidence` | agencies with a resolved `deployment_exists` ÷ agencies with any evidence | separates "we know they exist" from "we know what they run" |
| `coverage_portal` | agencies with a live transparency portal ÷ agencies with deployment evidence | bounded above by vendor opt-in (F13.26); **low values say nothing about deployment** |
| `coverage_contract` | agencies with ≥1 linked `Contract` ÷ agencies with deployment evidence | the records-request frontier |
| `coverage_policy` | agencies with a resolved `policy_retention_days` ÷ same | the policy-vs-configuration surface (§9.5) |
| `coverage_audit_log` | agencies with ≥1 `ObservedUse` window ÷ same | the scarcest and most lagged evidence type (F13.28) |
| `evidence_attribution_rate` | assets with a resolved `asset_operator` ÷ mapped assets | **baseline 19.05% globally in OSM (F13.23)**; SIG's own rate must be reported against it |
| `evidence_depth_p50` | median count of independent classes (§6.2) per published claim | the honest measure of how much corroboration exists |
| `evidence_archive_rate` | claims whose artifact is `I1` ÷ published claims | Berkeley Protocol compliance, made countable (F13.32) |
| `unresolved_rate` | `UNRESOLVED` ÷ all `(subject, predicate)` pairs attempted, by `U0`–`U8` reason | see below |
| `contested_rate` | `agreement ∈ {CONTESTED, IRRECONCILABLE}` ÷ resolved | the disagreement surface |

**`unresolved_rate` is not a defect rate.** Broken out by reason it is a diagnostic: a high `U0` share is
a coverage problem, a high `U5` share is a freshness problem, a high `U2`/`U3` share is a genuine dispute
density, and a high `U4` share usually means a `count_basis` or tolerance mis-specification. Reporting it
as a single number destroys all of that, so the ruleset requires the histogram and forbids the scalar.

## 12.3 Per-source metrics, and the trap they must avoid

Per source: last successful capture, cadence adherence, content-hash drift, claims contributed, retraction
rate, share of claims at each weight class, `R` row last-reviewed date, and — for partner sources —
whether the licence statement's hash has changed.

**The trap:** it is trivial to compute "share of this source's claims that lost their resolutions" and
tempting to feed it back into `R`. **SIG must not.** That is endogenous source weighting, which F13.7
identifies as truth discovery's founding assumption and F13.3 shows buys ~0–3 points of precision at the
cost of stability and explainability; and in SIG's case it is worse than that, because the "loss rate"
would be measured against SIG's own resolutions, making the whole loop circular (the same objection the
copy detector carries at §6.4).

The metric is still worth computing — as an **editorial signal**. A source whose claims consistently lose
generates a `REVIEW_SOURCE_RELIABILITY` task for a human, who may revise the registry row with a written
justification, versioned and diff-reported like any other ruleset change. The path from "this source seems
unreliable" to "this source's claims count for less" runs through a person, in public, or it does not run
at all.

## 12.4 Completeness estimation, and the capture–recapture verdict

### 12.4.1 The verdict

**Capture–recapture cannot be used to estimate ALPR device counts from volunteer mapping and vendor portal
reporting. Not with a caveat, not with a wide interval — the estimator's assumptions fail, and they fail
in the direction that would make SIG systematically understate surveillance.**

The Lincoln–Petersen estimator `N̂ = n₁n₂/m₂` requires four things. Against SIG's two candidate
"observation processes" — volunteer roadside mapping into OSM, and agency-published transparency portals —
they stand as follows:

**1. Individual identification and linkage — fails outright, and this alone is dispositive.**
Recapture requires knowing *which* individuals appear in both samples. Transparency portals publish a
**count**, not an inventory: there is no device identifier, no location, and no attribute to match on
(F13.26 — the portal reports policy, usage statistics, sharing details, and camera counts). `m₂` is
therefore not merely hard to measure, it is **undefined**. Estimating `m₂` from the two totals is circular:
it assumes the answer. There is no version of this analysis that survives that fact, and everything below
is why it would still fail even if the linkage problem were solved.

**2. Population closure — fails.** `active_device_count` is a `FAST` predicate with a six-month half-life
(§5.2). Devices are added and removed continuously. The two "samples" are not even contemporaneous: an
OSM-derived observation time is an *edit* time and a systematically optimistic upper bound on when a human
actually looked (F13.24), while a portal snapshot is a point observation at a known instant (§9.3). Any
window wide enough to accumulate both lists is wider than the closure horizon.

**3. Independence of the two processes — fails, and fails in the worst direction.** Portal publication is
opt-in and self-selected: one enumeration found ~562 portals and estimated adoption at under 10% of
law-enforcement customers (F13.26). Agencies that publish portals are disproportionately those under local
scrutiny — which is to say, those in jurisdictions with an active local accountability group, which is
also where volunteer mappers are. The two capture probabilities are therefore **positively correlated**.
Positive correlation inflates `m₂`, and inflated `m₂` deflates `N̂`. The estimator would not be noisy; it
would be **biased low, by an unknown amount, in exactly the direction that matters**. A public-interest
project cannot publish a number whose known failure mode is "understates the thing we exist to document."

**4. Homogeneous capture probability — fails, with shared structure.** Roadside visual survey
systematically misses rear-facing, tree-obscured, and private-property devices (§6.3, F13.4); portal
reporting misses anything the vendor does not instrument or the customer disabled. Mapper density varies
by orders of magnitude across jurisdictions (§9.9). This is structured, spatially clustered missingness,
not random thinning — and the two processes' blind spots are correlated with each other through the same
urban/rural and salience gradients. Heterogeneity of this kind biases Lincoln–Petersen downward even
without list dependence.

**Would a multi-list model rescue it?** No. Log-linear multi-list models (Bishop–Fienberg–Holland) can
absorb pairwise list dependence, but they require **three or more lists with individual-level linkage**
and they cannot identify the highest-order interaction — the one that matters here, since all of SIG's
lists share the "public visibility" latent factor. SIG has neither the linkage nor a third genuinely
independent list.

**The one place it is legitimate.** Where SIG holds a **records-derived installation list with locations**
for a specific jurisdiction — the only artifact in this domain that is a true device-level inventory — a
two-sample estimate against a *blind* field survey of that jurisdiction is defensible, because linkage is
possible and the two processes are genuinely independent if the survey is conducted without sight of the
list. Even then it estimates **the field survey's recall in that jurisdiction**, not the number of devices
in the world, and it must be pre-registered, conducted within a window shorter than the predicate's
half-life, and published as a *measurement of SIG's method* rather than as a fact about the jurisdiction.
That is a validation exercise, and validation exercises do not extrapolate.

### 12.4.2 What SIG publishes instead

1. **Counted quantities with named denominators**, never estimated totals. "31 devices mapped and
   attributed to X" and "38 reported active by X's portal on 2026-07-15" are both true, both citable, and
   neither is an estimate.
2. **Bounds, from records.** `mapped_device_count` is a lower bound (`is_lower_bound: true`, §9.1);
   `authorized_device_count` and `contracted_device_count` are documented upper bounds on what was
   approved and purchased. The interval `[best observed lower bound, best documented upper bound]` is
   derived entirely from artifacts and is publishable as an interval — clearly labelled as an interval
   between two *different* measured quantities, not as a confidence interval around a total.
3. **Reconciliation ratios**, per agency, where two measured quantities both exist — e.g.
   `mapped ÷ portal_reported`, with both dates. This is a statement about the relationship between two
   observations. Aggregating it across agencies to produce a national "mapping completeness" figure is
   prohibited, because the agencies where both quantities exist are precisely the non-random subset.
4. **Measured recall on a calibration subset**, per §12.4.1's legitimate case, published with the
   jurisdiction named and with an explicit non-extrapolation statement.
5. **Evidence-type coverage** (§12.2), which is a fully measurable property of SIG's corpus and is what
   most people actually want when they ask "how complete is this?"
6. **The known unknowns, named.** The portal-count disagreement itself (~562 enumerated vs the vendor's
   1,500+ claim, F13.26) is published as a `COUNT_DISAGREEMENT` contradiction at the vendor level, because
   an honest project's best answer to "how many portals are there" is "two sources say different things
   and here they are."

**And the standing prohibition:** SIG must never publish a national, state, or per-jurisdiction estimate
of total devices, total agencies with ALPR, or percentage coverage of a road network as a fact about the
world. Every one of those numbers would be quoted forever, and none of them is computable from what
exists. EFF's Atlas takes exactly this position about itself — "not an inventory of every technology in
use" (F13.27) — and it is the correct one.

## 12.5 Freshness, staleness, and SLA-style targets

Freshness targets derive mechanically from the volatility table (§5.2): the goal is to keep the bulk of
published claims inside `C1`/`C2`, i.e. under one half-life.

| Predicate class | `h` | Target: p50 evidence age | Target: share at `C1`+`C2` | Re-check cadence |
|---|---|---|---|---|
| `VOLATILE` | 1–2 mo | ≤ 3 weeks | ≥ 70% | weekly where a live source exists |
| `FAST` | 4–6 mo | ≤ 3 months | ≥ 80% | monthly |
| `MODERATE` | 9–12 mo | ≤ 5 months | ≥ 85% | quarterly |
| `SLOW` | 2–3 y | ≤ 12 months | ≥ 90% | annual |
| `GLACIAL` | 5–10 y | ≤ 3 years | ≥ 95% | annual registry review |
| `IMMUTABLE` | ∞ | n/a | n/a | never (re-check the *extraction*, not the fact) |

**Metrics:**

- `currency_distribution` — share of published values at `C1`/`C2`/`C3`/`C4`, per predicate class.
  Published as a distribution, never as a mean age.
- `stale_share` — `C3 + C4`, per predicate class and per jurisdiction.
- `recompute_backlog` — resolutions past their scheduled currency-boundary recompute (§7.6 trigger (e)).
  **Target: zero, always.** This is the design's most likely silent failure mode and the metric exists
  specifically to make it loud.
- `source_staleness` — per source, time since last successful capture against its declared cadence.
- `link_rot_rate` — artifacts whose URL now 404s and for which no archived copy exists. **Target: zero**,
  since `evidence_archive_rate` is supposed to make this impossible.
- `pin_expiry_backlog` — pins past `expires_at` whose resolution has not reverted.

**Hard invariants, which are not targets and admit no exceptions:**

1. Any published value at `C4` **must** be labelled `HISTORICAL` in every surface that renders it.
2. Any `IRRECONCILABLE` resolution **must** have an open `Contradiction` with a task attached.
3. No value may be published without its `currency` field. A number without a date is not a finding.
4. `evidence_archive_rate` ≥ 95% for published claims — and the 5% must be enumerable, not residual.

**The honesty clause.** SIG does not control its sources, so these are *targets* and their misses are
published rather than smoothed. In particular `coverage_portal` puts a hard ceiling on how fresh SIG's
operational picture can ever be: portals are the only routinely-refreshed operational source (F13.26), and
they cover a self-selected minority. That ceiling is itself a published metric, so that "SIG's data is
stale here" is legible as "no one publishes anything here," which is the true and more useful statement.

## 12.6 Engine-health metrics

These measure the reconciliation engine rather than the corpus, and they are the ones that tell SIG when
its own rules have drifted from reality:

| Metric | Reading |
|---|---|
| `pin_count`, `pin_rate` (pins ÷ published values) | rising ⇒ the ruleset is drifting from reality (§7.7 item 4). **Must not be suppressible** |
| `pin_reissue_rate` | a pin that expires and is immediately re-pinned without a ruleset change is the specific pathology to alarm on: a fact being laundered on a 180-day cycle |
| `contradiction_open_count` by type and severity | the disagreement surface |
| `contradiction_median_age` by type | ageing contradictions mean the detector→task contract is not closing |
| `detector_false_positive_rate` | `DISMISSED_FALSE_POSITIVE` ÷ dispositioned, per detector. A detector above threshold is a ruleset bug, not a curator burden |
| `ruleset_diff_size` | `(subject, predicate)` pairs whose published value/support/agreement/currency changed per ruleset release (§7.6). Published, not logged |
| `unresolved_reason_histogram` | `U0`–`U8` shares over time; a shift between reasons is a change in SIG's failure mode |
| `golden_case_pass` | binary, CI-gated; a ruleset change that alters a golden case fails the build with a diff |
| `resolution_reproducibility` | double-run `input_digest` match over a frozen corpus. **Target: 100%.** Anything else means the engine is not deterministic and the whole design's central promise has failed |

All of these belong in the published release quality report and on a public dashboard, at the same
cadence as the data. A project whose authority rests on provenance rather than omniscience (§22.1) does
not get to keep its own error metrics private.

---

## Open questions

**OQ-1 — Every half-life in the volatility table is a defensible guess.** §5.2's classes were assigned
from domain reasoning and a handful of dated examples (F13.29, F13.30), not from measured change rates.
SIG has no longitudinal corpus yet, and until it does the entire currency axis — which is what makes `U5`
fire and what determines whether a value is `HISTORICAL` — rests on unvalidated constants. *Hedge:* the
table is ruleset data, versioned, and every change produces a published diff report (§7.6), so
recalibration is visible rather than silent. The first year of portal snapshots is the corpus that would
settle it.

**OQ-2 — All numeric thresholds are uncalibrated starting values.** The attribution score cut-off of 8,
the 3-point margin, `max_relative_spread` 0.15/0.10, the 14-day snapshot-skew limit, the ±18-month
replacement window, the 2×half-life interpolation gap, the ≥20-pair minimum for the copy detector, the
`W`-composition downgrade steps. Each is defensible; none is measured. The design's mitigation is that
they are data rather than code, but a wrong threshold that never gets revisited is just as wrong.

**OQ-3 — The `(genre × predicate) → D` matrix is illustrative, not complete.** §4.4 publishes nine genres
against five predicates. The real matrix is every artifact genre against every predicate SIG resolves, and
it has to be written by hand, reviewed, and maintained as new genres appear. This is a substantial
unglamorous authoring task and it is on the critical path: `D6` is an *admissibility* filter, so a missing
cell silently admits non-probative evidence.

**OQ-4 — There is no ground truth, so there is no accuracy measurement.** F13.5's central point applies to
SIG directly: Knowledge Vault got calibrated probabilities only by having a large curated KB to train
against, and SIG has nothing equivalent. The golden-case suite (§7.1) tests *consistency* — that the engine
does what the ruleset says — not *correctness*. The only correctness signal available is field
verification on a small subset, and it is expensive. SIG must therefore never claim an accuracy figure for
its resolutions, and this file's design is built to make that refusal survivable rather than embarrassing.

**OQ-5 — Whether `count_basis` is recoverable from real documents at a useful rate.** Phase 2.3 and the
whole of §9.1 depend on connectors being able to determine whether a contract counts cameras, devices, or
pole installations. No sample of real contracts was examined for this. If the answer is "rarely," then
most count claims arrive as `count_basis: unspecified`, capped below `W4`, and the `U6` ambiguity
condition fires far more often than intended. *This is the most likely way §9.1 degrades in practice.*

**OQ-6 — The portal denominator is unknown.** F13.26 records ~562 enumerated portals against a vendor
claim of 1,500+, unreconciled, with `eyesonflock.com` returning 403 to this environment. `coverage_portal`
(§12.2) has no trustworthy denominator until that is settled, and it is one of the metrics most likely to
be quoted.

**OQ-7 — The undeclared-copying detector may never have statistical power.** §6.4 requires ≥20
co-asserted `(subject, predicate)` pairs per source pair. Whether SIG's corpus will be dense enough for
that, for the source pairs that matter, is unknown — and the detector is circular by construction, using
SIG's own resolutions as a truth proxy. It is specified as a suspicion generator for exactly this reason,
but if the density never arrives it simply will not fire, and undeclared copying will go undetected.

**OQ-8 — OSM edit time as `observed_time` is systematically optimistic by an unquantified amount**
(F13.24). A node created in 2024 and never re-edited carries a 2024 timestamp and an unbounded true
observation age. The volatility model treats it as such in principle, but SIG has no measurement of the
distribution of "time since a human actually looked," and no way to obtain one without field verification.

**OQ-9 — Vendor re-sharing semantics are unknown, and §10.6 defaults to no closure because of it.**
Whether the dominant platform permits an agency to re-share a partner's cameras onward is the single
highest-value unknown in the inference catalog: it determines whether two-hop access paths exist at all.
It is answerable — a configuration export or vendor documentation would settle it — and it should be an
explicit records-request target rather than a modelling assumption.

**OQ-10 — Whether `NO_RESOLUTION` predicates survive contact with users.** §8.2 refuses to resolve
`immigration_enforcement_access` and `policy_vs_configuration_agreement` on principle. Publishing two
values and declining to pick is editorially correct and may be practically unusable in a one-page dossier
or a map popup. The UI treatment is unspecified here and belongs to the product workstream, but if it is
solved badly the refusal will be read as evasion.

**OQ-11 — Whether the generated rationale (§7.5) is adequate for evidentiary use.** The legal-use
interface wants per-claim provenance defensible in a filing. Whether a template-generated rationale plus a
provenance expression meets that bar has not been reviewed by anyone qualified to say, and the answer
affects whether rationales need a second, longer form.

**OQ-12 — Ruleset implementation is undecided.** F13.34 recommends copying OPA's *pattern* — rules as
data, unit-testable, decision logs naming the rules that fired — without committing to Rego. Bespoke YAML
is simpler to author and read; Rego brings a real evaluator and a test framework at the cost of a
dependency and a learning curve. The decision has genuine consequences for §7.1's testability guarantees
and is deferred here.

**OQ-13 — Pin countersignature authority.** §7.7 item 5 requires a second curator to countersign a pin
that contradicts a `W4` claim. Whether that second signature should instead come from an editorial body,
and how that interacts with pin expiry and the `pin_reissue_rate` alarm (§12.6), is a governance question
this file raises but does not settle.

**OQ-14 — Whether the three-track lifecycle generalizes beyond ALPR.** §9.4's P/H/O decomposition was
derived from one very well-documented case (F13.29). It is almost certainly right for fixed-installation
technologies; whether it holds for software-only capabilities (facial recognition access, data-broker
subscriptions), where there is no hardware track at all, is untested — the likely answer is that track H
becomes optional per technology class, but that has not been worked through.

---

## Spec requirements emitted

Each is concrete and testable. Section references point at this file.

**The source model**

| ID | Requirement |
|---|---|
| **REQ-R13-01** | Evidence MUST be graded on four separate stored axes — source reliability `R`, claim directness `D`, artifact integrity `I`, and currency `C` — and MUST NOT be collapsed into a single tier or score at any layer. (§4.2) |
| **REQ-R13-02** | `R` MUST be a property of the publisher and its method, assigned once in a versioned source registry with a written justification, reviewed on a schedule, and MUST NOT be re-judged per claim by an ingesting connector or a human reviewer. (§4.2, F13.16) |
| **REQ-R13-03** | `D` MUST be read from a published `(artifact_genre × predicate)` matrix versioned with the ruleset. `D6` MUST act as an **admissibility filter** — a `D6` claim contributes nothing and is excluded in Phase 1.3, not down-weighted. (§4.4) |
| **REQ-R13-04** | `I` MUST be assigned mechanically by the ingest pipeline from `I1` (content-addressed archive + checksum + fetch timestamp + HTTP status), `I2` (live URL only), `I3` (unre-fetchable). It MUST NOT be human-assignable. (§4.2, F13.32) |
| **REQ-R13-05** | `C` MUST be derived at query time from `(as_of − observed_time)` and the predicate's volatility class, and MUST NOT be stored on the claim. (§4.2, §5.1) |
| **REQ-R13-06** | A genuinely novel source MUST default to `R5` with `reliability_provisional: true`, and MUST NOT be assigned `R6`; `R6` means "known-heuristic method," not "unknown." (§4.3) |
| **REQ-R13-07** | Axis composition MUST be an ordinal table (`base(R)`, then bounded downgrades and at most `+1` upgrade), never arithmetic on numeric scores, and the composition table MUST be ruleset data. (§4.5) |

**Volatility and currency**

| ID | Requirement |
|---|---|
| **REQ-R13-08** | Every predicate MUST be assigned a volatility class with a half-life `h`, stored as ruleset data and versioned. Predicates MUST NOT be resolved without one. (§5.1, §5.2) |
| **REQ-R13-09** | For `IMMUTABLE` and `GLACIAL` predicates, recency MUST NOT break a tie; the tie-break MUST fall through to weight and then source-registry rank. (§5.2) |
| **REQ-R13-10** | Windowed predicates MUST carry explicit `window_start`/`window_end` in `valid_time` and MUST NOT be currency-downgraded for the window they describe. "Current rate" MUST be a separate derived predicate with its own volatility. (§5.3) |

**Independence and copy discounting**

| ID | Requirement |
|---|---|
| **REQ-R13-11** | Every `Claim` MUST carry `derived_from_source: SourceRef[]`, populated at ingest, forming a materialized transitive DAG over sources, expressed as PROV-O `wasDerivedFrom`. (§6.1, F13.12) |
| **REQ-R13-12** | Corroboration MUST be counted over **independence classes**, computed as weakly connected components over shared root sources — never over raw claim or source counts. (§6.2) |
| **REQ-R13-13** | A class's weight MUST be `max(W)` over its members. Multiplicative corroboration (`1 − Π(1−w)`) and additive vote-summing over dependent sources are prohibited. [testable: two DeFlock+OSM claims for one node yield `support_breadth = 1`] (§6.2, F13.1, F13.2) |
| **REQ-R13-14** | Every source MUST declare a `collection_method` and a machine-readable `collection_scope`. Two independence classes sharing a `collection_method` MUST NOT satisfy the "≥2 independent classes" condition for a confidence upgrade, but MUST satisfy the "≥2 classes" condition that avoids the `U3` single-source trigger. (§6.3, F13.4) |
| **REQ-R13-15** | The Bayesian undeclared-copying test MUST run offline as a monitor emitting `UNDECLARED_DEPENDENCE_SUSPECTED` contradictions for human disposition, and MUST NOT re-weight any published value. (§6.4, F13.1) |

**The resolution algorithm**

| ID | Requirement |
|---|---|
| **REQ-R13-16** | Resolution MUST be a deterministic, rule-based function of `(claims, ruleset_version, as_of_world, as_of_knowledge)`. Learned weights, MCMC, and any non-deterministic estimator are prohibited in the resolving path. (§7.1, F13.3, F13.10) |
| **REQ-R13-17** | The ruleset MUST be versioned, signed, human-readable data in the repository containing the `R` registry with justifications, the `D` matrix, the volatility table, the strategy assignments, the numeric thresholds, and the rationale templates. Resolution logic MUST NOT be embedded in application code. (§7.1, F13.34) |
| **REQ-R13-18** | Every resolution MUST record the `rule_id`s that fired, the `ruleset_version`, and an `input_digest` over the sorted claim ids and their content hashes. (§7.1, §7.3) |
| **REQ-R13-19** | The published confidence vocabulary MUST be four orthogonal fields — `resolution_status`, `support`, `agreement`, `currency` — and the API MUST always return all four. A single fused label MAY be derived for display but MUST NOT be the primary representation. (§7.2) |
| **REQ-R13-20** | A rationale MUST NOT place a support term and an agreement term in the same sentence. (§7.2, §7.5, F13.13) |
| **REQ-R13-21** | Phase 1 MUST drop retracted/withdrawn claims, claims outside the as-of window, `D6` claims, and source-superseded claims **before** any weighting. (§7.3) |
| **REQ-R13-22** | Count predicates MUST carry `count_basis ∈ {camera, device, pole_installation, unspecified}` and `scope`. Claims disagreeing on `count_basis` MUST be dropped with a `PREDICATE_CONFLATION` contradiction, never compared. `count_basis: unspecified` MUST be admitted at −1 weight and MUST NOT reach `W4`. (§7.3 Phase 2.3, §9.1) |
| **REQ-R13-23** | `STRATEGY_RANK` MUST yield a total order, with the universal final tie-break `(W desc, breadth desc, observed_time desc, source_registry_rank asc, claim_id asc)` over content-addressed claim ids. There MUST be no random tie-break anywhere in the system. (§7.3) |
| **REQ-R13-24** | Every `ResolvedView` MUST emit supporting, dissenting, and excluded claim id sets, with an exclusion reason per excluded claim, plus the independence-class partition. (§7.3) |

**The ambiguity test**

| ID | Requirement |
|---|---|
| **REQ-R13-25** | `AMBIGUOUS` MUST evaluate conditions `U0`–`U8` in a fixed order and MUST return the **first** triggering condition id as the `UNRESOLVED` reason, so that the reason is deterministic. (§7.4) |
| **REQ-R13-26** | A claim whose only support is `W1` or below MUST NOT resolve to a published value (`U1`), implementing "nothing on a tip alone." (§7.4, F13.31) |
| **REQ-R13-27** | `U5` MUST force `UNRESOLVED` when the best available claim is `STALE`/`HISTORICAL` on a `MODERATE`/`FAST`/`VOLATILE` predicate **even with zero dissent and a Tier A source**, publishing the value as `last_known` with its date. [testable: a 2024 contract MUST NOT yield a 2026 `active_device_count`] (§7.4) |
| **REQ-R13-28** | `UNRESOLVED` MUST be rendered as an explicit published finding with all candidate values and their evidence, MUST NOT be hidden or treated as an error, and MUST generate a research task. (§7.4, §11.4, F13.17) |

**Rationale, recomputation, override**

| ID | Requirement |
|---|---|
| **REQ-R13-29** | Rationales MUST be generated from versioned templates filled from the resolution's structured fields, MUST name the sources that mattered and those that conflict, MUST be regenerated on every recompute, and MUST NOT be hand-editable. (§7.5, F13.14, F13.17) |
| **REQ-R13-30** | A `ResolvedView` MUST be a derived artifact, keyed by `(subject, predicate, as_of_world, as_of_knowledge, ruleset_version)`, never edited in place; deleting the entire resolved-view store MUST be a recoverable no-op costing only CPU. (§7.6) |
| **REQ-R13-31** | Re-running `RESOLVE` over a frozen corpus at a fixed `ruleset_version` MUST produce byte-identical output and an identical `input_digest`. This MUST be CI-enforced. (§7.6) |
| **REQ-R13-32** | Every resolution MUST carry a **scheduled expiry at its next currency-class boundary**, and the scheduler MUST recompute then. A recompute backlog MUST be a published metric with a target of zero. (§7.6, §12.5) |
| **REQ-R13-33** | Every ruleset release MUST publish a diff report enumerating each `(subject, predicate)` whose value, support, agreement, or currency changed, with before/after. (§7.6) |
| **REQ-R13-34** | The API MUST support independent `as_of_world` (valid time) and `as_of_knowledge` (transaction time) queries. (§7.6, F13.33) |
| **REQ-R13-35** | A curator override MUST be stored as a `CURATOR_RESOLUTION_OVERRIDE` **claim** with a named agent, a rationale of at least 120 characters, and a required `expires_at` (default 180 days, maximum 365). It MUST NOT mutate or hide dissenting claims, MUST surface as `editorially_pinned: true` with the curator and rationale visible at the same level as the value, and MUST revert to computed on expiry with a task generated. A pin contradicting a `W4` non-override claim MUST require a second countersignature. (§7.7) |
| **REQ-R13-36** | Pin count, pin rate, and pin reissue rate MUST be published quality metrics and MUST NOT be suppressible. (§7.7, §12.6) |

**Per-predicate strategies and the nine workflows**

| ID | Requirement |
|---|---|
| **REQ-R13-37** | Every resolvable predicate MUST be assigned exactly one strategy from the §8.1 vocabulary in the ruleset. An unassigned predicate MUST fail ruleset load. (§8.1, §8.2) |
| **REQ-R13-38** | `policy_vs_configuration_agreement` and `immigration_enforcement_access` MUST be `NO_RESOLUTION` — both values always published with provenance — except that `immigration_enforcement_access` MAY resolve on a `W4` configuration export. (§8.2) |
| **REQ-R13-39** | Device counts MUST be modelled as eight distinct predicates (authorized, contracted, invoiced, installed, active, mapped, field-verified, decommissioned), resolved independently. Deltas between them MUST be **derived**, and a delta involving an `UNRESOLVED` count MUST itself be `UNRESOLVED`, never zero. Every non-zero delta MUST emit a `DeltaExplanation` with enumerated candidate causes and discriminating evidence. (§9.1) |
| **REQ-R13-40** | Device attribution MUST use published integer feature scores with a threshold, a uniqueness requirement, and a margin requirement; it MUST emit an edge only above threshold with a unique top scorer and a ≥3-point margin, and otherwise MUST emit a research task with ranked candidates. Attribution MUST only ever infer `operated_by`; `owner` and `data_controller` MUST NOT be inferred from geography. (§9.2) |
| **REQ-R13-41** | Inferred attributions MUST NOT be written back to OSM, MUST NOT count toward `field_verified_device_count`, and MUST NOT feed the corridor feature that generated them. (§9.2, §10.2) |
| **REQ-R13-42** | `ConfiguredAccess`, `ObservedUse`, and `DeclaredPolicy` MUST be three distinct object types and MUST NOT be inferred from one another in any direction. (§9.3) |
| **REQ-R13-43** | A single sharing snapshot MUST yield a point-interval claim only. Interval construction requires ≥2 snapshots within 2× the predicate half-life and MUST be emitted as a labelled inference invalidated by any intervening snapshot lacking the partner. (§9.3, §10.7) |
| **REQ-R13-44** | Sharing asymmetry MUST emit a `SHARING_ASYMMETRY` contradiction with both edges published and their own provenance. Union and intersection of the two portals' partner lists are both prohibited. Snapshots more than 14 days apart MUST be flagged for time skew. (§9.3) |
| **REQ-R13-45** | Deployment lifecycle MUST be modelled as three independent state machines — procurement, hardware, operational — each with its own current state and its own staleness. A single `status` field is prohibited. An event MUST write to exactly one track. (§9.4, F13.29) |
| **REQ-R13-46** | Fuzzy dates MUST be normalized to intervals and ordered by strict Allen precedence; overlapping intervals MUST yield `order_uncertain` or a topology-derived order with `order_source` recorded, never a silent guess. (§9.4) |
| **REQ-R13-47** | SIG MUST NOT emit any summary asserting that surveillance was removed or reduced unless the hardware track is `removed`, the operational track is `deactivated`, and no `replaced_by` edge exists. This MUST be a mechanical output guard. (§9.4 step 9, §22.5 of the outline) |
| **REQ-R13-48** | Retention MUST be modelled in three layers — vendor default, written policy, system configuration. Policy/configuration divergence MUST emit a `HIGH` contradiction carrying a `direction` field and MUST publish both values. A vendor-default change MUST invalidate every deployment-level inference derived from the old default. Retention values MUST support a structured `{scope → days}` domain, not a scalar. (§9.5, F13.30) |
| **REQ-R13-49** | Money MUST be modelled as distinct predicates with a mandatory `value_period`; arithmetic consistency checks MUST run as contradiction detectors, never as resolvers. Bundled contracts MUST carry `allocable: false` and MUST NOT have their full value attributed to one technology. (§9.6) |
| **REQ-R13-50** | A fuzzy-only organization match MUST NOT write. It MUST emit a `RESOLVE_ORG_IDENTITY` task with ranked candidates. An organization known only from a network list MUST be created with `existence_status: ASSERTED_BY_NETWORK_LIST_ONLY` and MUST NOT be published as an agency without classification. (§9.7) |
| **REQ-R13-51** | Capability predicates MUST be split by ontology term before resolution into at minimum `capability_operated`, `capability_accessible_via_partner`, `capability_requested_from_third_party`, `capability_piloted_historically`. (§9.8) |
| **REQ-R13-52** | `deployment_exists` and `capability_present` MUST NOT resolve to `false` from source silence. The only negative paths are a first-party denial at `W3`+ or a scoped `no_responsive_records` predicate carrying requester, date, and request scope. (§9.8, F13.4) |
| **REQ-R13-53** | Geographic coverage metrics MUST be derived, MUST carry `is_lower_bound: true`, and MUST NOT be rendered without the mapping-coverage layer displayed alongside. (§9.9, §12.1) |

**The inference catalog**

| ID | Requirement |
|---|---|
| **REQ-R13-54** | Derived values MUST be stored separately from claims, MUST carry `derived: true`, `derivation_rule_id`, `inputs_digest`, and `computed_at`, and MUST NOT carry `support`/`agreement`. (§10.1) |
| **REQ-R13-55** | Every derived value and inference MUST carry a **provenance expression** over base claim ids (conjunctive `·`, alternative `+`), not merely a citation list. (§10.1, F13.11) |
| **REQ-R13-56** | No derived value or inference may exceed `W3`, and none may be `W4`. Its weight MUST be at most `min(W)` over its conjunctive inputs minus one class. (§10.1) |
| **REQ-R13-57** | Every inference MUST carry `label: INFERENCE`, and the label MUST propagate into every export row and API response. Filtering `label != INFERENCE` MUST yield a dataset containing no SIG-computed values; this MUST be a CI-tested property of the export. (§10.2) |
| **REQ-R13-58** | Every inference rule MUST declare a non-empty `invalidated_by`; a rule with an empty `invalidated_by` MUST fail ruleset load. (§10.2) |
| **REQ-R13-59** | An inference MUST NOT be an input to another inference of the same family. (§10.2) |
| **REQ-R13-60** | Derived field of view MUST be emitted as a sector whose half-angle includes the source tag's own quantization, MUST use cited manufacturer parameters held as ruleset data, MUST be `D6` for every other predicate, MUST NOT be rendered as a hard-edged certainty polygon, and MUST NOT feed coverage metrics. (§10.3) |
| **REQ-R13-61** | No inference in the system may take a natural person as subject or produce one as output, except public officials acting officially. In particular, field-of-view derivation MUST NOT produce or support any claim about a vehicle or a person. (§10.3, §10.8) |
| **REQ-R13-62** | Organizational `part_of` edges MUST propagate constraints downward (jurisdiction containment, authorization ceiling) and containment upward only, under the distinct predicate `capability_present_in_subordinate_unit` naming the subordinate. `capability_operated` MUST NOT be inherited in either direction. (§10.5) |
| **REQ-R13-63** | `member_of` (task force, fusion centre, compact) MUST propagate nothing in either direction. Shared-system use by a member MUST be modelled as an evidenced access fact, never as a membership inference. (§10.5) |
| **REQ-R13-64** | Access-path transitive closure MUST be disabled by default. It MUST require the `DataSystem`'s `resharing_semantics` to resolve to `explicit_reshare_permitted` or `transitive_by_default` on `W3`+ evidence; `unknown` MUST produce no paths. (§10.6) |
| **REQ-R13-65** | Where closure is licensed, it MUST be bounded at 2 hops, MUST use temporal **intersection** and scope **intersection** (never union), MUST be emitted as a distinct `InferredAccessPath` type rendered distinctly and excluded from observed-edge topology metrics, and MUST be capped at `W2`. (§10.6, F13.11) |
| **REQ-R13-66** | An inferred access path MUST NOT satisfy `immigration_enforcement_access`. (§10.6, §8.2) |
| **REQ-R13-67** | An audit-log entry indicating a lookup run on another party's behalf MUST be modelled as `lookup_performed_on_behalf_of` and MUST NOT be converted into a `ConfiguredAccess` edge. (§10.6) |
| **REQ-R13-68** | SIG MUST store enumerated access **paths** with per-path provenance, scope, and interval, and MUST NOT materialize a transitive-closure relation. (§10.6) |
| **REQ-R13-69** | SIG MUST NOT infer device counts from contract value ÷ unit price, operational status from installation, policy compliance from policy existence, or source quality from agreement with SIG's own resolutions. (§10.8, F13.7) |

**Contradictions**

| ID | Requirement |
|---|---|
| **REQ-R13-70** | `Contradiction` MUST be a persistent first-class entity with the §11.2 shape, distinct from a resolution's `UNRESOLVED` status, carrying a stable `signature`, `first_detected_at`, `last_confirmed_at`, and `recurrence_count`. (§11.1, §11.2) |
| **REQ-R13-71** | Claims about different predicates MUST NOT generate contradictions; predicate conflation is prevented in Phase 2.3. Absence of evidence, weak evidence, and staleness MUST NOT be recorded as contradictions. (§11.1) |
| **REQ-R13-72** | Contradiction detectors MUST be pure ruleset queries, MUST run on the §7.6 recomputation triggers, MUST deduplicate on `signature`, and MUST NOT mutate any resolution. (§11.3) |
| **REQ-R13-73** | `BLOCKING` severity MUST NOT be assignable by a detector. Only a human may set it, with a written reason, and it is the sole severity that alters resolution behaviour (via `U7`). (§11.2, §7.4) |
| **REQ-R13-74** | Every contradiction type MUST declare non-empty `candidate_causes[]` and non-empty `discriminating_evidence[]`, a `task_template`, an `assignee_class`, and an `auto_dormant_after`. A type with empty `discriminating_evidence` MUST fail ruleset load. (§11.4) |
| **REQ-R13-75** | The generated task's `required_evidence` MUST be the contradiction's `discriminating_evidence` by reference, not by duplication. Task closure MUST re-run the detector; if the detector still fires, the task MUST NOT close. Exactly one open task per contradiction. (§11.4) |
| **REQ-R13-76** | Contradiction resolution MUST use the six §11.5 dispositions. `RESOLVED_BOTH_TRUE` MUST require a predicate split via a reviewed ruleset change. `DISMISSED_FALSE_POSITIVE` MUST produce a ruleset change or a recorded justification. (§11.5) |
| **REQ-R13-77** | A resolved contradiction MUST remain permanently visible on the subject and on every claim it involved, MUST appear in a "previously contested" section with dates and disposition, and MUST reopen automatically if the detector fires again with a different signature. Deletion and silent closure are prohibited. (§11.5, F13.31) |
| **REQ-R13-78** | A contradiction MUST NOT be closed by selecting a value without evidence; that act is a pin (REQ-R13-35) and MUST be labelled and expiring. (§11.5) |
| **REQ-R13-79** | Contradictions MUST surface on the value, on the entity page, in the jurisdiction dossier, in the exports as their own resource, in the diff feed, and in the quality report. A value with an open `HIGH` or `BLOCKING` contradiction MUST NOT render anywhere without its marker. (§11.6) |

**Coverage, completeness, freshness**

| ID | Requirement |
|---|---|
| **REQ-R13-80** | Every coverage metric MUST be published with its denominator named and MUST be prefixed to identify it as a property of SIG's evidence, not of the world. (§12.1) |
| **REQ-R13-81** | `unresolved_rate` MUST be published as a histogram over `U0`–`U8` reasons; a scalar unresolved rate MUST NOT be published. (§12.2) |
| **REQ-R13-82** | Per-source "claims that lost resolution" MUST NOT feed `R` or any weight. It MUST generate a `REVIEW_SOURCE_RELIABILITY` task whose only outcome is a human-written, versioned, diff-reported registry change. (§12.3, F13.7) |
| **REQ-R13-83** | SIG MUST NOT publish capture–recapture, mark–recapture, or multi-list population estimates of device or deployment totals derived from volunteer mapping and vendor portal reporting. The estimator's individual-identification, closure, independence, and homogeneity assumptions all fail, and the resulting bias is downward. (§12.4.1) |
| **REQ-R13-84** | SIG MUST NOT publish any national, state, or per-jurisdiction estimate of total devices, total agencies with a technology, or percentage road-network coverage as a fact about the world. (§12.4.2, §8.2, F13.27) |
| **REQ-R13-85** | Completeness MUST instead be expressed as: counted quantities with named denominators; bounds derived from records (`is_lower_bound` / documented upper bounds); per-agency reconciliation ratios with both dates, never aggregated across agencies; measured recall on a named calibration subset with an explicit non-extrapolation statement; and evidence-type coverage. (§12.4.2) |
| **REQ-R13-86** | A capture–recapture style estimate MAY be computed only as a **method-validation** exercise, against a records-derived device-level installation list, with a blind field survey, pre-registered, inside a window shorter than the predicate half-life, published as a measurement of SIG's survey recall in that named jurisdiction and never extrapolated. (§12.4.1) |
| **REQ-R13-87** | Freshness targets MUST be derived from the volatility table per predicate class and published as a dashboard with `currency_distribution`, `stale_share`, `recompute_backlog`, `source_staleness`, `link_rot_rate`, and `pin_expiry_backlog`. Mean evidence age MUST NOT be published in place of the distribution. (§12.5) |
| **REQ-R13-88** | Four hard invariants MUST hold and MUST be tested: every `C4` value is labelled `HISTORICAL` in every surface; every `IRRECONCILABLE` resolution has an open contradiction with a task; no value is published without its `currency` field; `evidence_archive_rate` ≥ 95% with the remainder enumerable. (§12.5) |
| **REQ-R13-89** | `recompute_backlog` and `resolution_reproducibility` MUST have published targets of zero and 100% respectively, and a reproducibility failure MUST fail the build. (§12.5, §12.6, §7.6) |
| **REQ-R13-90** | Engine-health metrics — pin rate, pin reissue rate, contradiction counts and median age by type, per-detector false-positive rate, ruleset diff size, unresolved-reason histogram, golden-case pass, reproducibility — MUST be published in the release quality report at the same cadence as the data. (§12.6) |
