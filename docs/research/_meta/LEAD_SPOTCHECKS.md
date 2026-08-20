# Lead-agent independent spot-checks

Verifications performed by the synthesizing agent directly, to cross-validate workstream
findings rather than rely solely on delegated research.

## SC-01 — OSM surveillance node counts (taginfo API, live)

**Retrieved:** 2026-08-20, `data_until: 2026-08-20T00:59:51Z`
**Endpoint:** `https://taginfo.openstreetmap.org/api/4/tag/stats?key=man_made&value=surveillance`

| Element type | Count |
|---|---|
| all | **558,645** |
| nodes | 557,900 |
| ways | 716 |
| relations | 29 |

**Implication:** the physical layer is overwhelmingly nodes (99.87%), but ways and relations
exist and the schema MUST NOT assume point geometry keyed on node id. `man_made=surveillance`
can be a way (e.g. a mapped camera mast/enclosure) or relation.

## SC-02 — `surveillance:type` value distribution (taginfo API, live)

**Endpoint:** `.../api/4/key/values?key=surveillance%3Atype&sortname=count&sortorder=desc`
**Total distinct values: 116** — the vocabulary is *not* clean and the spec must plan for
normalization with an inspectable mapping, not an enum.

| Value | Count | Fraction | In wiki |
|---|---|---|---|
| `camera` | 371,941 | 71.18% | no |
| `ALPR` | **144,312** | 27.62% | yes |
| `gunshot_detector` | 3,250 | 0.62% | yes |
| `guard` | 2,003 | 0.38% | no |
| `camera;radar` | 255 | 0.05% | no |
| `sensor` | 104 | 0.02% | no |
| `AFR` (automated facial recognition) | 67 | 0.01% | no |
| `camera;guard` | 65 | | no |
| `camera;ALPR` | 61 | | no |
| `traffic` | 49 | | no |
| `ALPR;camera` | 42 | | no |
| `webcam` | 37 | | no |
| `PTZ` | 36 | | no |
| `flock safety` | 29 | | no |
| `SC511` | 25 | | no |
| …101 further values | | | |

**Implications for the spec (all load-bearing):**

1. **Semicolon multi-values are real** (`camera;radar`, `camera;ALPR`, `ALPR;camera`). The OSM
   parser MUST split on `;`, MUST treat the value as an unordered set, and MUST NOT rely on
   ordering — `camera;ALPR` and `ALPR;camera` are the same fact spelled two ways.
2. **Case and spelling are inconsistent** (`ALPR` vs `flock safety` as a *type*, which is a
   manufacturer leaking into a type field). Normalization must be a versioned, inspectable
   mapping table per OL-2C-AW-05, not a hardcoded enum.
3. **OSM already carries non-camera surveillance**: 3,250 `gunshot_detector` nodes and 67 `AFR`
   nodes exist. This independently corroborates outline §4.5 (acoustic sensors must not be
   forced into a "camera" abstraction) and §4.7, and it means the non-ALPR physical layer is
   available at Stage 1 rather than Stage 5.
4. **Long tail of 116 values** means an `unmapped_source_value` escape hatch and a research task
   for unmapped vocabulary are required.

## SC-03 — ALPR count vs. secondary reporting

A secondary source (MapAtlas blog, "DeFlock Put 336K ALPRs on OpenStreetMap") circulates a
~336,000 figure. The directly measured count of `surveillance:type=ALPR` today is **144,312**
worldwide. The 336K figure is **not corroborated** by taginfo and must not be repeated in the
spec without a primary source. This is a live illustration of the outline's own doctrine
(OL-4.1-04, OL-24-03): a crowdsourced figure requires independent verification before it is
treated as canonical.

## SC-04 — DeFlock domain correction

`deflock.org` (as cited in the outline's source registry, OL-21-03) did not serve content;
`deflock.me` is the live domain (returned HTTP 403 to a plain fetch, indicating an active
Cloudflare-fronted host rather than a dead domain). The spec's source registry must carry the
corrected domain and record that the host requires browser-like request headers.

## SC-05 — `manufacturer` values on OSM (taginfo, live 2026-08-20)

7,031 distinct `manufacturer` values exist in OSM. The top values across the *entire* database:

| Value | Count | Domain |
|---|---|---|
| **Flock Safety** | **108,100** | surveillance |
| Vestas | 34,869 | wind turbines |
| GE | 24,431 | wind turbines |
| Enercon | 12,530 | wind turbines |
| Siemens | 10,889 | mixed |
| Gamesa | 7,684 | wind turbines |
| Nordex | 7,643 | wind turbines |
| **Motorola Solutions** | **6,745** | surveillance (Vigilant-lineage ALPR) |
| Triarca | 4,468 | mixed |
| Federal Signal | 4,353 | sirens |

**Findings:**

1. `manufacturer=Flock Safety` is the **most common manufacturer value in all of OpenStreetMap**,
   ahead of every wind-turbine manufacturer. The DeFlock/OSM ALPR mapping effort is, by volume,
   one of the largest manufacturer-attribution efforts in the project's history. This
   independently corroborates the outline's assessment that the OSM/DeFlock physical layer is
   unusually developed (OL-ES-04, OL-ES-05) — and quantifies it.
2. `manufacturer=Motorola Solutions` at 6,745 independently corroborates OL-2D-DD-03 /
   OL-4.2-01: the mapped physical ALPR layer is **already multi-vendor**. A Flock-only physical
   model would discard a measurable existing population on day one.
3. 108,100 `Flock Safety` manufacturer tags against 144,312 `surveillance:type=ALPR` implies a
   large ALPR population with **no manufacturer attribution** (~36,000 at minimum, before
   accounting for non-Flock manufacturers). This is the "orphaned device" research task
   (OL-12-05) quantified: it is a five-figure backlog, not an edge case.

## SC-06 — the `surveillance` key is semantically overloaded (taginfo, live)

430 distinct values on the `surveillance` key:

| Value | Count | Intended semantic |
|---|---|---|
| `public` | 273,978 | zone |
| `outdoor` | 127,724 | zone |
| `traffic` | 22,093 | zone |
| `indoor` | 12,743 | zone |
| `yes` | 3,877 | *not a zone* — boolean misuse |
| `camera` | 3,560 | *not a zone* — type leaking into the zone key |
| `private` | 2,746 | zone |
| `no` | 2,496 | boolean misuse |
| `webcam` | 1,976 | type leaking into zone key |
| `cctv` | 847 | type leaking into zone key |

**Finding:** in OSM the `surveillance=*` key carries the *zone*, while `surveillance:type=*`
carries the *kind of device*. Both keys are polluted by values belonging to the other, plus
boolean misuse. **The OSM connector MUST NOT trust either key in isolation**; it must apply a
versioned, inspectable cross-key normalization that reconciles `surveillance`,
`surveillance:type`, `surveillance:zone`, and `camera:type` into SIG's own vocabulary, and it
must emit an unmapped-value research task for tail values. This is a concrete instance of
OL-2C-AW-05 ("never overwrite source text with normalized semantics").

## SC-07 — academic citation retrievability

`https://journals.sagepub.com/doi/10.1177/20501579261453519` (Monahan, "Grounding the Flock",
cited at OL-21-36) returns **HTTP 403** to an ordinary client. **Status: INACCESSIBLE.**

**Implication:** a nontrivial share of the scholarly and paywalled evidence base is not
machine-retrievable. The `EvidenceArtifact` model MUST support artifacts that are cited but not
captured, with an explicit `capture_status` distinguishing *captured* / *access-restricted* /
*paywalled* / *link-rotted* / *not-attempted*. Treating "we could not fetch it" as equivalent to
"it does not exist" would violate OL-9.4-01.

## SC-08 — Tag co-occurrence on the world's mapped ALPRs (taginfo combinations API, live 2026-08-20)

Base population: the **144,312** OSM elements tagged `surveillance:type=ALPR`.

| Co-occurring tag | Count | % of ALPRs |
|---|---|---|
| `man_made=surveillance` | 143,898 | **99.7%** |
| `direction=*` | 135,027 | **93.6%** |
| `camera:type=*` | 133,398 | 92.4% |
| `camera:type=fixed` | 132,843 | 92.0% |
| `surveillance=*` | 127,455 | 88.3% |
| `surveillance:zone=*` | 126,082 | 87.4% |
| `manufacturer=*` | 125,376 | 86.9% |
| `surveillance:zone=traffic` | 120,363 | 83.4% |
| `manufacturer:wikidata=*` | 120,335 | **83.4%** |
| `surveillance=public` | 108,916 | 75.5% |
| `manufacturer=Flock Safety` | 105,743 | 73.3% |
| `manufacturer:wikidata=Q108485435` (Flock Safety) | 104,589 | 72.5% |
| `camera:mount=*` | 44,138 | 30.6% |
| `camera:mount=pole` | 32,276 | 22.4% |
| **`operator=*`** | **27,496** | **19.1%** |
| `operator:wikidata=*` | 17,816 | 12.3% |
| `brand=*` | 5,463 | 3.8% |
| `camera:direction=*` | 5,345 | 3.7% |
| `operator:type=*` | 4,182 | 2.9% |
| `electricity=*` | 3,696 | 2.6% |
| `source=*` | 2,450 | 1.7% |

### SC-08.1 — The orphaned-device backlog, quantified

**Only 19.1% of mapped ALPRs carry an `operator` tag.** Roughly **116,800 mapped ALPR devices
worldwide have no operator attribution.**

This is the single most important measurement in this spot-check file. It means:

1. The outline's "orphaned device" research task (OL-12-05) is not an edge case — it is a
   six-figure backlog and arguably SIG's largest single unit of addressable work.
2. The device-attribution reconciliation workflow (OL-11.2-01, §29.2) is not a nice-to-have.
   Without it, ~81% of the physical layer cannot be connected to any organization, deployment,
   contract, policy, or sharing relationship — which is to say, the entire rest of the graph.
3. **This is precisely the value SIG adds that no upstream currently provides.** DeFlock and OSM
   hold the geometry; the attribution linking geometry to institutions is missing, and it is
   exactly what reconciliation against contracts, portals, and jurisdiction geometry can supply
   as `probable` inferred edges for human confirmation.
4. The Cedar Rapids illustrative gap (OL-3-06, "14 OSM devices have unknown operator") is, at
   national scale, an 81% figure. The spec should say so.

### SC-08.2 — Wikidata is already the de-facto identity anchor in OSM

`manufacturer:wikidata` is present on **83.4%** of ALPRs — *more often than the plain
`manufacturer` tag is machine-normalizable* — and `operator:wikidata` on 12.3%. Flock Safety is
`Q108485435`.

**Implication:** the vendor and organization identity layers (§14) SHOULD adopt Wikidata QIDs as
a first-class crosswalk identifier, not merely as an optional one. OSM has already done the
entity-resolution work for vendors, and inheriting it is free precision. This materially
strengthens the answer to OL-Q12 and OL-Q37.

### SC-08.3 — Derived field-of-view is broadly feasible

`direction=*` is present on **93.6%** of ALPRs and `camera:mount` on 30.6%. PanoptiCity-style
FOV derivation (OL-2A-PC-02) is therefore computable for the large majority of the population —
which makes the outline's insistence on separating source facts from derived facts an *urgent*
architectural requirement rather than a theoretical one, since the derived layer will be nearly
as large as the observed layer.

### SC-08.4 — Mobility is already encoded

`camera:type=fixed` on 92.0% means the remaining ~8% are non-fixed (mobile/trailer/PTZ). The
`PhysicalAsset.mobility` requirement (OL-8.6-03, "coordinates must not be required for movable
assets") has an immediate, non-hypothetical population.

### SC-08.5 — Sparse tags define the field-research task backlog

`camera:mount` (30.6%), `operator:type` (2.9%), and `source` (1.7%) are sparse. These are
directly actionable field-verification and records-research tasks (§33), and their sparsity
gives SIG a quantified, prioritizable work queue on day one rather than a vague call to
"research surveillance" (OL-15.6-01).

## SC-09 — Adjudicating a conflict between workstreams: the EFF Atlas licence

Two workstreams returned incompatible findings on a load-bearing question:

- **R7** reported the Atlas is **CC-BY**, citing a "CC-by" footer link on every page.
- **R11** reported the Atlas **"states no dataset license anywhere"**, and therefore specified
  its connector ship as `UNDETERMINED`, failing the export gate closed.

**Direct verification (curl, 2026-08-20):**

- `https://atlasofsurveillance.org/pages/about` — footer and page body contain
  `<a href="https://www.eff.org/copyright">CC-by</a>`. Confirmed on the homepage too.
- `https://www.eff.org/copyright` states verbatim: *"Any and all original material on the EFF
  website may be freely distributed at will under the Creative Commons Attribution 4.0
  International License (CC-BY), unless otherwise noted. **All material that is not original to
  EFF may require permission from the copyright holder to redistribute.**"*
- The Atlas homepage states the research *"incorporates datasets from a variety of public and
  non-profit sources."*

**Adjudication — both are partly right, and the synthesis is what matters:**

1. R7 is correct that a CC-BY assertion exists and is discoverable. R11 is correct that there is
   **no dataset-specific licence statement** — the CC-BY link is a site-wide EFF policy applied
   to web pages, not a data licence attached to the CSV.
2. The site-wide statement is **explicitly conditional**: it covers *original* EFF material only,
   and the Atlas states on its own homepage that it incorporates third-party datasets. So an
   unqualified `CC-BY-4.0` on the whole dataset would be an overclaim, and `UNDETERMINED` on the
   whole dataset would be an underclaim that needlessly blocks the project's single most
   important seed source.

**Spec posture adopted (§22.2, §42.5):** record the Atlas rights as
`CC-BY-4.0 WITH LicenseRef-SIG-EFF-third-party-caveat`, `redistributable = true` for
EFF-original rows, `redistributable = review_required` for rows sourced from an incorporated
third-party dataset — which the Atlas's own per-row source attribution makes distinguishable —
and open a Stage-0 confirmation item with `aos@eff.org`. Attribution string:
*"Electronic Frontier Foundation and the Reynolds School of Journalism, University of Nevada,
Reno."*

**Methodological note for the spec.** This is the exact failure mode the project is built to
handle, occurring inside the project's own research process: two competent sources disagreed,
neither was simply wrong, and the correct output was not a majority vote but a *reconciliation*
that preserved both readings and named the residual uncertainty. It is recorded here as a live
worked example for §28, and as a justification for SIG-STORE-015 (`unresolved_conflict` must be
publishable) and for §42.5's requirement that `redistributable` be a **separately reviewed**
field rather than a function of the licence string.

## SC-10 — EFF has already drawn the agency/device boundary SIG proposes to straddle

The Atlas About page states: *"Please do not send us the individual locations of surveillance
cameras or automated license plate readers. That data may be better suited for DeFlock.me."*

This is direct, quotable, first-party ecosystem precedent for the federation compact (§6): the
largest US surveillance-adoption dataset has publicly delegated the device layer to DeFlock. It
strengthens OL-18-01/OL-18-02/OL-18-06 from an assumption into a documented division of labour,
and it means SIG's reconciliation role — joining the agency layer to the device layer — is
occupying a gap the incumbents have *explicitly declined to fill*, not competing for territory.

Note also: the Atlas links to `https://deflock.org/` with the link text "DeFlock.me", which
suggests `deflock.org` redirects to `deflock.me`. The source registry MUST record both and
resolve the canonical one at Phase 0.

---

# Completion pass (2026-08-20, after the spend limit was lifted)

## SC-11 — FlockReporter is dead at the DNS level, and the ecosystem it indexed is not

**Retrieved:** 2026-08-20

| Check | Result |
|---|---|
| `dig +short flockreporter.org` | **no answer** — the domain does not resolve |
| `curl https://flockreporter.org/` | `HTTP 000` after **0.0038 s** — instant DNS failure, not a timeout or a block |
| `curl https://www.flockreporter.org/` | `HTTP 000` |
| Wayback availability | **one** capture: `20260728225506`, status 200 |
| Wayback CDX (`collapse=timestamp:6`) | **exactly one capture in the archive's entire history** |

The site was alive on **2026-07-28** and its DNS has since lapsed. This is not a transient outage
and not bot protection: bot protection returns 403 with a body (as several sites below do), whereas
this returns nothing because there is no address to connect to.

### SC-11.1 — The recovered directory

The single Wayback capture (72 KB) yielded the complete local-group directory the outline relies on
(OL-3-02, OL-18-13). Liveness re-tested directly, 2026-08-20:

| Group | URL | Status |
|---|---|---|
| ALPR Pictures | `https://alpr.pictures/` | 403 (alive, bot-protected) |
| DeFlock Atlanta | `https://deflockatlanta.org/` | **200** |
| DeFlock Birmingham | `https://deflockbhm.com/` | **200** |
| DeFlock Joplin | `https://deflockjoplin.today/` | 403 (alive, bot-protected) |
| DeFlock Lynnwood | `https://deflocklynnwood.com/` | **200** |
| DeFlock Olympia | `https://deflockoly.noblogs.org/` | **200** |
| DeFlock Redmond | `https://bsky.app/profile/deflock-redmond.bsky.social` | **200** (Bluesky, no own domain) |
| DeFlock Tucson | `https://deflocktucson.com/` | **200** |
| DeFlock Vegas | `https://www.deflock.vegas/` | **200** |
| Eyes Off Cedar Rapids | `https://eyesoffcr.org/` | 403 (alive, bot-protected) |
| Eyes Off Colorado | `https://www.eyesoffcolorado.org/` | **200** |
| Eyes Off Indiana | `https://eyesoffindiana.org/` | **200** |
| Live Free VA | `https://livefreeva.org/` | **200** |
| Community Discord | `https://discord.gg/m9VsbR6d5z` | listed |
| Community Matrix | `#deflock:flockreporter.org` | **dead with the domain** |

**All thirteen groups are alive. Only the directory that indexed them died.**

Two of the outline's named groups do not appear in the recovered directory — **DeFlock Idaho** and
**DeFlock Monterey Park / Monterey Park organizers** — so either the directory was already
incomplete or those efforts ended earlier. `alpr.pictures` is a project the outline never names.

### SC-11.2 — Why this matters more than one dead link

1. **The outline's assumption is now falsified in production.** OL-3-02 and OL-18-13 treat
   FlockReporter as the mechanism by which SIG discovers collaborators. That mechanism no longer
   exists. SIG-TASK-014 (SIG maintains its own registry) was written as a hedge; it is now a
   requirement in fact, not in theory.
2. **The archival-insurance argument is no longer hypothetical.** §46.5 argues SIG should offer
   mirroring to single-maintainer upstreams because "if those projects vanish unmirrored, the
   record vanishes." One did vanish, inside the research window for this very specification, and it
   survived only because a third party happened to capture it **once**. A single capture is the
   entire margin between "we recovered the ecosystem directory" and "the ecosystem directory is
   gone."
3. **The Matrix room died with the domain.** `#deflock:flockreporter.org` was homeserver-bound, so
   losing the domain destroyed the community's coordination channel too — a second-order loss that a
   naive "the website is down" framing misses entirely.
4. **It is a live instance of SIG's own doctrine.** A source disappearing is *data*
   (SIG-INGEST-009/010), and "which ecosystem projects quietly went dark" is exactly the dataset
   that only exists if disappearance is recorded rather than retried.

**Spec consequences:** seed the local-group registry from this recovered list with verified URLs
rather than from the outline's bare names (SIG-INGEST-039); record FlockReporter as
`disappeared_observed_at = 2026-08-20` with its last capture retained; and cite this as the worked
justification for §46.5 rather than the hypothetical the spec currently offers.

## SC-12 — The OSM Automated Edits Code of Conduct, read; and why the compliant path is narrower *and* easier than it looks

**Retrieved:** 2026-08-20 · `https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct`

This closes risk **R-14** and answers outline **Q33**.

### SC-12.1 — Scope: what counts as an automated edit

Verbatim: the policy *"covers all edits where changes are made to objects in the database **without
review individually by the person controlling the edits**."* It explicitly names bots, imports,
scripted changes, **"use of find-and-replace functionality using a standard editor such as JOSM or
finding using services such as Overpass API and changing without reviewing each object
individually"**, and *"manually changing tags without adequate review."*

And the enforcement posture, verbatim: *"Ignoring this policy will be treated as vandalism and will
be responded to as such if it persists."*

### SC-12.2 — What compliance would require, if SIG bot-wrote

A documented proposal at a wiki page `Automated edits/<username>` stating **all** of: who is making
the change (*"preferably your real name and how to contact you, ideally e-mail address"*);
motivation; *"a detailed description of the algorithm you will use to decide which objects are
changed how"*; consultation conducted, with links; when/how often; and **"information on how to
'opt out'"**. It must be added to `Category:Automated edits log` and discussed on an OSMF-run
platform (Community Forums or the `talk` list), plus national or local channels where the edit is
geographically scoped.

Three clauses matter especially for SIG:

1. *"there must be a permanent record of a community discussion and decision on the Community forum
   or this Wiki"* — a Discord or Slack consensus does not count.
2. *"any later modification or extension to the scope of changes you propose to make should also be
   discussed in the same way and **requires new community approval**. It is not possible to get
   blanket approval."* A one-time blessing for "SIG adds operator tags" would not cover next year's
   expansion.
3. *"If you find that your plan is widely accepted except for a few dissenters… consider making an
   exception for their edits or area."* Compliance is per-community and can be partial.

### SC-12.3 — Operator attribution is **not** covered by any exception

The listed exceptions are narrow: blatant typos, reverting vandalism, correcting your own work, and
reverting unapproved automated edits. The page is explicit that *"'I think that this tagging schema
is silly and should be changed' does not count as typo."*

Adding `operator=*` from contracts and public records is **new information from an external source**.
It is not a typo fix, and because the data originates outside OSM it would additionally engage
`Import/Guidelines`. At ~116,800 candidate nodes it is unambiguously in scope.

### SC-12.4 — The decisive insight, which makes the constraint tractable

The CoC's scope hinges on *"without review individually by the person controlling the edits."*

**A workflow in which a human reviews each proposed change individually, in their own account, using
their own judgment, is therefore not an automated edit at all — it falls outside the policy's
scope.** This is precisely the shape of a MapRoulette-style task challenge, and it is why
SIG-CONTRIB-015's human-mediated suggestion design is not merely a cautious choice: it is the
mechanism that keeps SIG out of the regime entirely, rather than a way of complying with it.

The corollary is a real constraint on SIG's ambitions and should be stated plainly in the spec:
**SIG cannot clear the 116,800-device backlog mechanically.** It can only make each device cheap for
a human to resolve. Throughput is bounded by mapper attention, and the design goal is therefore to
*minimize the human cost per resolution* — surfacing the contract, the jurisdiction, and the
candidate operator together — not to maximize automated write volume.

**Spec consequences:** R-14 is closed; SIG-CONTRIB-014/015 are confirmed correct and their rationale
strengthened from "pending review" to "verified"; and SIG-CONTRIB-016's ADR should record the
scope-based argument above rather than treating the CoC as an obstacle to be complied with.

## SC-13 — Flock domains are excluded from the Wayback Machine (independently confirmed, with controls)

**Retrieved:** 2026-08-20. This independently confirms a finding first reported by workstream R4,
using controls to rule out a malformed query or a transient API failure.

| Query | Result | Reading |
|---|---|---|
| CDX `transparency.flocksafety.com*` | `[]` | Query succeeded; **zero captures** |
| Availability API, a real portal slug | `{"archived_snapshots": {}}` | **No snapshot, ever** |
| CDX `flocksafety.com` | **empty response — not even the header row** | The signature of an **exclusion rule**, not merely an absence of crawling |
| **Control:** CDX `eff.org` | Header row + captures from **1996** onward | The API works |
| **Control:** CDX `deflock.me` | Header row + captures from 2024 onward | Small, recent civic sites are archived normally |

The difference between the two Flock queries is diagnostic. `transparency.flocksafety.com*` returns
a well-formed empty array — the archive answered and had nothing. `flocksafety.com` returns *no
response body at all*, which is how the CDX endpoint behaves for an excluded host rather than an
unarchived one.

### Why this is load-bearing rather than a curiosity

1. **There is no third-party archive fallback for the portal layer.** SIG's §22.5 fallback chain
   already excludes scraping on legal grounds (F2.1); this removes the remaining passive option.
   The portal layer is obtainable through partnership, public records, or human-mediated capture —
   or not at all.
2. **The historical record is being lost continuously, right now.** Portal statistics are rolling
   rather than immutable (OL-2B-FP-03). Every day without capture is a day of configuration and
   usage history that no one will be able to reconstruct.
3. **It converts SIG's archival role from a courtesy into the ecosystem's only insurance.** Combined
   with SC-11 — where a directory survived solely because a third party captured it exactly once —
   the pattern is consistent: this ecosystem's evidence base is one custodian deep almost
   everywhere, and in the vendor's case, zero deep.
4. **It sharpens the Stage-0 priority.** If Eyes on Flock holds historical portal snapshots, those
   snapshots may be **globally unique**. That materially raises what SIG should be willing to offer
   in the collaboration, and it is a concrete, checkable thing to ask about first.

**Spec consequence:** §22.5's fallback ordering and SIG-INGEST-032's mirroring offer are correct as
written; this finding upgrades their justification from inference to measurement, and should be
cited in the Phase-0 outreach as a reason the collaboration matters to *both* parties.

## SC-14 — The Organised Editing Guidelines DO apply, and they hand SIG its leverage metric

**Retrieved:** 2026-08-20 · `https://wiki.osmfoundation.org/wiki/Organised_Editing_Guidelines`
(Approved November 2018.)

SC-12 established that a human-mediated suggestion workflow falls **outside** the Automated Edits
Code of Conduct. It does **not** fall outside these. Verbatim scope:

> *"The organised editing guidelines apply to any edits that involve more than one person and can be
> grouped under one or more sizeable, substantial, coordinated editing initiatives."*

A SIG-run task challenge directing volunteers at ~116,800 orphaned devices is exactly that. Status,
verbatim: *"They are not a policy, but following them is the best way to make your organised edit
successful and receive constructive community feedback."* — advisory in form, but the community
treats non-compliance as bad faith, and SIG's federation posture (P5) makes voluntary compliance
the only coherent choice.

### SC-14.1 — What is required

A wiki page at `Organised Editing/Activities/<Name>`, registered in the activities list,
truthfully describing:

- the coordinating person or organisation, and **a way to contact them**;
- **a unique hashtag to be used in the changeset comments**;
- the goal, *"explaining also why the goal is being pursued"*;
- the timeframe;
- **any non-standard tools and data sources used, and their usage conditions**, with links;
- participating accounts that wish to be identified;
- the metrics used, if participant performance is measured in any way;
- any training material or written instructions given to participants.

*"A best-effort approach is expected and enough; more substantial initiatives are expected to spend
a more substantial amount of effort."*

### SC-14.2 — The changeset hashtag is a gift, not a cost

The hashtag requirement solves a problem SIG already had and had no clean answer to.

§7 commits SIG to publishing **ecosystem-leverage metrics**, the first of which is *"count of
SIG-originated operator-attribution suggestions accepted upstream."* Without a marker, that is
unmeasurable — SIG would be reduced to inferring its own influence from tag-count deltas, which is
both unreliable and slightly disreputable.

A declared changeset hashtag makes SIG's contribution stream **publicly auditable by anyone**,
including by SIG's critics. It can be queried from OSM's changeset API and from third-party tools,
so the leverage metric becomes a measurement rather than a claim, and the measurement is not under
SIG's control — which is the property that makes it credible.

It also inverts cleanly: the same mechanism is how SIG detects *other* projects' organised edits,
which is the general form of the open question about identifying DeFlock-originated edits.

### SC-14.3 — Two requirements SIG must be careful about

1. **"Any non-standard tools and data sources used, and their usage conditions."** SIG's data
   sources carry heterogeneous licences (§42). The disclosure must state, per source, what the
   mapper is permitted to do with it — and if a source's terms do not permit using it to derive an
   OSM edit, that source **must not** be surfaced in a task at all. This is a licence gate on the
   *contribution* path, not only on the export path, and the spec did not previously have one.
2. **"If the success or performance of participants will be measured… a description of the metrics
   used."** This intersects §33.6's prohibition on volume gamification. SIG's answer is consistent:
   it measures *task outcomes*, not *contributor rankings*, and must say so in the disclosure.

**Spec consequences:** add the organised-editing disclosure as a Phase-16 deliverable; declare a
changeset hashtag and use it as the basis for the §7 leverage metric; and extend the licence gate to
the contribution path (a new requirement, since §42.4 covers exports only).

## SC-15 — MapRoulette's API is live and natively supports the exact workflow the spec requires

**Retrieved:** 2026-08-20 · `https://maproulette.org/api/v2/challenges?limit=2` → **HTTP 200,
`application/json`**, real challenge objects returned.

This matters because §35.2 now commits SIG to a human-mediated suggestion workflow as the *only*
compliant contribution path (SC-12). If no usable mechanism existed, that commitment would be a
recommendation with no implementation behind it. It does exist, and it is a closer fit than expected.

### SC-15.1 — The challenge object's fields, mapped to SIG's requirements

Observed keys include: `id`, `name`, `description`, `instruction`, `blurb`, `enabled`, `created`,
`difficulty`, `defaultPriority`, `highPriorityRule`, `highPriorityBounds`, `defaultZoom`,
`cooperativeType`, `checkinComment`, `checkinSource`, `completionMetrics`, `completionPercentage`,
`limitTags`, `limitReviewTags`, `featured`, `isGlobal`, `isArchived`, `deleted`.

| SIG requirement | MapRoulette field |
|---|---|
| **The mandatory changeset hashtag** (SIG-CONTRIB-016e) | **`checkinComment`** — the comment applied to resulting changesets |
| Attribution of the originating tool/source | **`checkinSource`** |
| Surfacing the evidence to the mapper (contract, jurisdiction, candidate operator) | `instruction`, `description`, `blurb` |
| The task priority function (§33.1 `priority_fn`) | `defaultPriority`, `highPriorityRule`, `highPriorityBounds` |
| Geographic queues (§33.5, outline Q36) | `highPriorityBounds`, `isGlobal` |
| The §7 leverage metric — contributions accepted upstream | `completionMetrics`, `completionPercentage` |
| Task lifecycle / retirement (§33.3) | `isArchived`, `deleted`, `enabled` |

### SC-15.2 — `cooperativeType` is the decisive field

MapRoulette supports **cooperative challenges**, in which the challenge proposes a *specific tag
change* that the mapper reviews and accepts or rejects rather than editing freehand.

That is precisely SIG's operator-attribution case: *"this OSM node has no `operator`; SIG's evidence
— this contract, this jurisdiction — suggests `operator=X`; accept, reject, or edit."* It preserves
individual human review (keeping SIG outside the Automated Edits Code's scope, SC-12) while reducing
the mapper's cost per device to roughly one decision — which is exactly the objective
SIG-CONTRIB-017a sets, since throughput is bounded by mapper attention rather than by compute.

### SC-15.3 — Caveats recorded honestly

- `https://maproulette.org/docs/swagger.json` returns **404** and `learn.maproulette.org/documentation/`
  returns a **404 page**, so the formal API documentation was not located at the expected URLs. The
  API itself responds correctly; the docs are elsewhere and Phase 16 must locate them.
- `POST /api/v2/challenge` returns **400** unauthenticated, as expected — challenge *creation*
  requires an API key. Phase 0 must establish who holds SIG's MapRoulette account, and that account
  is subject to the Organised Editing disclosure (SC-14).
- `api.maproulette.org` does **not** resolve; the API is served from the main host.

**Spec consequence:** SIG-CONTRIB-015 should name MapRoulette cooperative challenges as the concrete
verified mechanism rather than describing a generic "task challenge", and `checkinComment` should be
named as where the required hashtag lives — turning two separate requirements into one implemented
field.

## SC-16 — State ALPR mandates do not produce state ALPR datasets (California, verified)

**Source:** findings contributed by a peer research session, **independently spot-verified by the
lead agent** before adoption. **Retrieved:** 2026-08-20.

### SC-16.1 — What I verified directly

| Check | Peer claim | My result |
|---|---|---|
| `information.auditor.ca.gov/reports/2019-118/index.html` | 200 | **200** (5.0 KB) ✓ |
| `…/reports/2019-118/surveys.html` | 200, 381-row survey table, scrape-only | **200** (289 KB), 2 `<table>`, **384 `<tr>`**, and **zero** `.csv`/`.xlsx`/`.json` links ✓ |
| `…/reports/recommendations/2019-118` | 200, recommendation tracker | **200** (57 KB) ✓ |
| `data.ca.gov` open-data portal, `q=ALPR` | count 0 | **`"count": 0`** ✓ |
| `data.ca.gov`, `q=license plate reader` | (not claimed) | **`"count": 0`** — independently confirms the negative |

384 `<tr>` less header rows reconciles with the peer's 381 data rows. The absence of any tabular
download link confirms **scrape-only**: the richest state-level ALPR artifact in the country is an
HTML table with no machine-readable export.

### SC-16.2 — The peer's further findings, adopted as reported

Not independently re-verified by me, but internally consistent and specifically cited:

- The 2019-118 recommendation tracker shows **all 54 agency recommendations Fully Implemented** but
  **all 6 Legislature recommendations Not Enacted / No Action Taken**. **No follow-up ALPR audit
  exists.**
- AG bulletin **2023-DLE-06** (`oag.ca.gov/system/files/media/2023-dle-06.pdf`, 5 pp) imposes **no
  reporting duty** and produced **no published compliance list**. The widely-cited "18 agencies"
  figure is **journalism, not an AG publication**.
- **SB 34 policies are decentralized.** No central registry; the DOJ does not collect them.
- OpenJustice contains **zero** ALPR references; its bulk host is **login-gated (INACCESSIBLE)**.
- **SB 274 (2025)** would have mandated DOJ random audits — **vetoed 2025-10-01 explicitly on audit
  cost**; veto sustained 2026-03-02.
- **SB 1013** (Cervantes) is live on the Assembly floor as of 2026-08-18, but its DOJ annual-audit
  clause is **appropriation-contingent** and the bill contains **zero occurrences of "publish"**.

### SC-16.3 — Two citation traps the peer caught

Worth recording because either would have been an embarrassing error in a published spec:

1. **"SB 210" is ambiguous.** The 2023-24 and 2025-26 SB 210s are **Budget Acts**. The ALPR SB 210
   is Wiener's 2021-22 bill, which **died**.
2. **AB 1814 (2023-24, Ting) is facial recognition, not ALPR** — and also died.

### SC-16.4 — The design consequence, which is a correction

The spec's §22.3 lists "state auditor surveys" and state ALPR reporting mandates as a source class,
with the implicit assumption that a statutory mandate yields a recurring machine-readable dataset.

**California falsifies that assumption in the strongest available case.** It is the most
ALPR-regulated state in the country — SB 34 has been law since 2016 — and it produces: no recurring
dataset, no central policy registry, no open-data presence, one one-time audit from 2020 published
as un-downloadable HTML, a vetoed audit bill, and a live bill whose audit clause is budget-contingent
and never uses the word "publish". Every legislative recommendation from the audit went unenacted.

This yields a named anti-pattern the spec should carry: **a mandate to *do* something is not a
mandate to *publish* it, and neither implies a dataset.** The correct posture is to treat state
mandates as evidence that *records exist to be requested* — which is a records-acquisition lead, and
a strong one — rather than as a feed to ingest. It also strengthens the project's core thesis: if
the most-regulated state's data must still be assembled by hand, reconciliation is the scarce
capability, not collection.

Finally, the recommendation tracker itself is a genuine finding: **54/54 agency recommendations
implemented against 0/6 legislative ones** is a publishable structural fact about where surveillance
accountability succeeds and fails, and it is exactly the kind of claim SIG exists to make traceable.

## SC-17 — Overpass, the history API, and a systematic trap in OSM element dating

**Retrieved:** 2026-08-20. All queries executed live.

### SC-17.1 — Overpass rejects browser-spoofed User-Agents

A request to `https://overpass-api.de/api/interpreter` carrying a Chrome User-Agent returned
**HTTP 406 Not Acceptable** (Apache). The identical query with a **descriptive** agent string —
`SIG-research/0.1 (surveillance-infrastructure-graph; contact: …)` — returned **HTTP 200** and valid
JSON from `Overpass API 0.7.62.11`.

This is a pleasing alignment: §26's Crawler Conduct Policy requires SIG to identify itself with a
descriptive UA and a contact, and Overpass **enforces** that. Spoofing a browser is not merely
against policy here, it does not work. Recorded because an implementer copying a browser UA from
another connector would otherwise waste time on an opaque 406.

Also observed: `node["manufacturer"="Flock Safety"]` returned 406 while
`node["surveillance:type"="ALPR"]` succeeded — the space in the tag value appears to trip a request
filter. The connector MUST therefore avoid spaces in Overpass tag-value filters, or filter
client-side.

### SC-17.2 — The element history API works and answers Q19

`https://api.openstreetmap.org/api/0.6/node/<id>/history.json` returned the **complete version
history** for a live node: six versions spanning 2009-03-07 to 2026-05-27, each with `version`,
`changeset`, `user`, `timestamp`, and the full tag set **as of that version**.

This **verifies** the Q19 design that was previously only a proposal: store the element id **and the
version SIG observed**, and fetch history on demand for the small set of elements under active
reconciliation. Replicating the history planet is unnecessary. Q19 moves from ANSWERED-DESIGN to
**ANSWERED-VERIFIED**.

### SC-17.3 — The trap: an OSM node's creation date is not the device's date

Four ALPR-tagged nodes, checked individually:

| Node | Versions | Node created | Became a surveillance node | Gap |
|---|---|---|---|---|
| 356521524 | 4 | 2009-03-07 | v3, 2024-12-15 | **15 years** |
| 356522344 | 4 | 2009-03-07 | v3, 2024-12-15 | **15 years** |
| 356522718 | 5 | 2009-03-07 | v4, 2024-12-15 | **15 years** |
| 356523027 | 6 | 2009-03-07 | v5, 2024-12-15 | **15 years** |

All four were created on the same day in 2009 by the same mapper as part of a **freeway import**
(v1 carried a single tag: `source=SanGIS Freeways_SD public domain`). They were **repurposed** into
surveillance nodes fifteen years later by adding tags to the *existing* node, rather than by
creating new ones.

**The consequence is severe and silent.** A connector that reads a node's creation timestamp as the
device's `first_observed` would record these ALPRs as first observed in **2009** — before the vendor
existed. At national scale this would systematically corrupt the temporal layer, which is the
project's stated differentiator (OL-22.5), and it would do so in a way that looks entirely
plausible: old dates on old infrastructure.

**The correct rule:** `first_observed` MUST be derived from the version at which surveillance tags
*first appeared*, which requires walking the element history — it is not readable from the element's
current metadata. This gives the Q19 history-fetch design a **mandatory** use, not merely an
optional one.

A second consequence: element identity is not stable *in meaning*. `node 356523027` denotes a
freeway feature for fifteen years and a surveillance device thereafter. A reference to the bare id
is therefore ambiguous across time, and only `(id, version)` is a well-defined reference — which is
exactly what REQ-R1-01 requires, now with a concrete demonstration of why.

### SC-17.4 — The Organised Editing hashtag mechanism, observed in the wild

The most recent edit to all four nodes came from a commercial mapping team's organised editing
activity, carrying `hashtags=#tomtom;#tt_mapfeedback` alongside `created_by`, `comment`, and
`source`. This is live confirmation that the changeset-hashtag convention required by the Organised
Editing Guidelines (SC-14) is what real organised teams actually do, and that it is queryable from
changeset metadata — validating SIG-CONTRIB-016e's plan to use it as the leverage-metric instrument.

Note also: the 2009 creating changeset carried **no `created_by` tag at all**, so tool attribution is
not available for older elements and MUST be treated as optional.

## SC-18 — The Eyes on Flock API is real (verified), and it brings a third licence regime

**Retrieved:** 2026-08-20. Verifies R2-F2.6/F2.7 independently, because this finding changes the
phase plan and should not be adopted on a single report.

### SC-18.1 — The API

`GET https://eyesonflock.com/api/v1/data` → **HTTP 200**, `application/json`, **7,627,201 bytes**,
unauthenticated, no key.

Structure: `{summary, portals}` where `portals` is a list of **950** entries. Observed portal fields:

`city · county · state · slug · type · population · portal_url · data_last_updated ·
data_retention · total_cameras · total_searches · vehicles_captured · hotlist_hits ·
hotlist_hit_rate · organization_count · organizations_shared_with · organizations_received_from ·
receiving_organization_count · prohibited_uses · public_search_audit`

`summary` carries national roll-ups: `total_portals_found`, `total_cameras`, `total_searches`,
`total_hotlist_hits`, `total_vehicles_captured`, `total_organization_count`,
`total_receiving_organization_count`.

**This maps almost field-for-field onto the outline's portal inventory (OL-2B-FP-02)** — including
the two predicates I had to add as gaps during the closure pass (`hotlist_hits`,
`vehicles_captured`) and the `prohibited_uses` statement. **The project's top blocker is resolved:
the portal layer is obtainable lawfully, without scraping Flock and without a headless browser.**

### SC-18.2 — `robots.txt`: permitted for SIG, forbidden for AI crawlers

```
User-agent: *
Content-Signal: search=yes,ai-train=no,use=reference
Allow: /

User-agent: ClaudeBot     Disallow: /
User-agent: GPTBot        Disallow: /
User-agent: CCBot         Disallow: /
User-agent: Google-Extended  Disallow: /
User-agent: Bytespider / Amazonbot / Applebot-Extended / meta-externalagent  Disallow: /
```

Two obligations follow, and they are **not** the same obligation:

1. **Access is permitted.** `User-agent: * → Allow: /`. A SIG connector identifying itself
   descriptively is within the operator's stated permission, and `use=reference` grants exactly the
   use SIG needs.
2. **`ai-train=no` is a distinct, binding restriction.** SIG MUST NOT use this content as model
   training data, and MUST NOT route it through any pipeline that would. This is separable from
   ingestion and must be recorded on the rights record as its own field — a licence string alone
   does not carry it.

SIG MUST also never present as a disallowed agent, which the descriptive-UA rule (§26) already
requires.

### SC-18.3 — The licence finding, and why it is an architectural correction

The footer string in the site bundle reads: **"EyesOnFlock is licensed under CC BY-SA 4.0."**
Contact: `contact@eyesonflock.com`. Both confirmed in the built JS.

**CC BY-SA 4.0 is ShareAlike.** That gives SIG a *third* mutually-incompatible licence regime:

| Compartment | Licence | Share-alike? |
|---|---|---|
| OSM-derived physical assets | **ODbL-1.0** | Yes |
| Portal layer (Eyes on Flock–derived) | **CC BY-SA 4.0** | Yes |
| SIG-original graph | **CC-BY-4.0** | No |

ODbL and CC BY-SA 4.0 are not mutually mergeable, and **neither may be folded into a CC-BY-4.0
export**. §42.3 currently frames the licensing architecture as a *two*-way split. That framing is
now wrong: it is an **N-compartment** problem, and the portal layer needs its own separable
compartment for exactly the reason the OSM layer does.

This is a correction worth catching before implementation rather than after: a Phase-14 export that
merged portal-derived counts into the main CC-BY graph would be a licence violation that is invisible
in the data and obvious to the licensor.

**Spec consequences:** generalize §42.3 from a two-layer split to an N-compartment model keyed on the
rights record; add `ai_training_permitted` as a first-class rights field; register Eyes on Flock as
`MIRROR`-permitted with CC BY-SA 4.0 and a stated contact; and unblock Phase 11.

## SC-19 — CORRECTION to SC-04: the DeFlock domain question, resolved properly

**Retrieved:** 2026-08-20. **This corrects my own earlier finding (SC-04) and also declines a
correction offered by workstream R1 (F1.36), because neither was right.**

| Claim | Source | Verdict |
|---|---|---|
| "`deflock.me` is the live domain; `deflock.org` is wrong-but-live" | SC-04 (mine) | **Wrong** — inferred canonicality from a 403, which proves only that a host exists |
| "`deflock.me` 301-redirects to `deflock.org`" | R1-F1.36 | **Not reproducible here** — 0 redirects observed, with two different UAs |

**What is actually observed:**

| Host | Status | Evidence |
|---|---|---|
| `deflock.me` | **HTTP 403, `cf-mitigated: challenge`, `num_redirects: 0`** | Cloudflare interactive challenge; no redirect, with both a browser UA and a descriptive UA |
| `deflock.org` | **HTTP 200**, serves the real application | SPA shell (3,191 B) loading `/assets/index-C_9V1eer.js`; `/map` returns distinct content (5,421 B); **zero** occurrences of `deflock.me` in the HTML |

**Conclusion: both hosts serve the project, and `deflock.org` serves it without a bot challenge.**
There is no redirect in either direction. The practical guidance is therefore the opposite of what
SC-04 said: a connector should target **`deflock.org`**, because it responds to ordinary clients,
while `deflock.me` is challenge-gated and would require exactly the circumvention SIG forbids
(SIG-INGEST-013).

### Why this is recorded rather than quietly amended

Three methodological points, each of which the specification asserts and this incident tests:

1. **A 403 is not evidence of canonicality.** SC-04 reasoned "403 means alive, therefore this is the
   real host". A 403 means a host exists and is protected — nothing more. This is the
   `capture_status` distinction (SIG-EPIS-005) applied to my own research: *inaccessible* is not
   *authoritative*.
2. **A correction from a second source is not automatically right either.** R1's 301 claim was not
   reproducible from here. Adopting it because it arrived later and contradicted me would have been
   recency bias — precisely the failure mode the resolution engine's rule against
   latest-observation-wins-for-everything exists to prevent (§28.4).
3. **The correct output was neither claim but a reconciliation of both** — which is the project's
   own thesis, encountered for the third time in its own research process (cf. SC-09, SC-16).

Discrepancy retained rather than resolved by fiat: R1's observation may reflect a different vantage
point, a Cloudflare rule that varies by client or geography, or a transient configuration. The
source registry MUST record **both hosts, both observed behaviours, and the observation dates**, and
MUST NOT assert a redirect that this vantage point cannot reproduce.

### SC-19.1 — Addendum: R1's explanation reconciles both observations

R1's completion pass reports `deflock.me` **301-redirects** to `deflock.org`, and explains the
discrepancy: *the Cloudflare challenge fires before the redirect*. That is consistent with
everything observed here — a compliant client that never solves the challenge never reaches the
301, so it sees only the 403. The two observations are not in conflict; they are the same server
seen from two positions.

**The operational conclusion is settled and is the same under either reading: target
`deflock.org`.** And the substantive correction is to *my* SC-04, not to the outline: **the
outline's `deflock.org` citation was right**, and my "correction" of it was wrong. SC-04's
`deflock.me`-is-canonical claim is **withdrawn**; REQ-R1-14 is superseded by R1's completion pass.

Recorded rather than silently amended because this is the second time in this project that a 403
was over-read (cf. the local groups in SC-11, where 403 correctly meant "alive"). The general rule
worth carrying: **a 403 tells you a host exists and is protected. It tells you nothing about
canonicality, and nothing about what lies behind it.**
