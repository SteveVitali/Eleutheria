## 39. The product surfaces

### 39.0 Users

**SIG-UI-001 (MUST).** The surfaces MUST be designed against named personas with real tasks:

| Persona | Arrives with | "Done" looks like | Would distrust the site if |
|---|---|---|---|
| Investigative journalist, on deadline | "What can I say about this agency, and can I defend it?" | A quotable claim with a citable document and a permalink | A number appears with no source, or the page changes under a citation |
| Academic researcher | "Give me the national picture and the denominators" | A reproducible bulk export with documented methods | Coverage is implied to be complete |
| **Local advocate, council meeting in 6 days** | "What is deployed here, what does it cost, when does it renew?" | **A printed dossier they can hand to a council member** | It reads as advocacy rather than record |
| Civil-liberties attorney | "What is documented, and what is the provenance chain?" | Evidence with page anchors and acquisition history | Inference is presented as observation |
| Council staffer | "Is what the vendor told us consistent with the record?" | A neutral comparison with sources | The tone is hostile to their institution |
| Resident | "Is there surveillance near me, and who runs it?" | A plain answer with an honest gap statement | Absence looks like proof of absence |
| Downstream developer | "Can I build on this?" | Stable ids, documented API, clear licence | Identifiers move |
| SIG contributor | "What needs doing near me?" | A concrete task with a closing condition | Work disappears into a queue with no effect |

**SIG-UI-002 (MUST).** The local advocate is the **design center**. That choice drives the print
path, the six-day time horizon of the renewal watch, and the plain-language register.

### 39.1 The epistemic visual language

This is the project's defining UI problem: communicating uncertainty without either false
confidence or paralysing hedging.

**SIG-UI-003 (MUST).** Support MUST render as a **four-step glyph** (e.g. ⊕⊕⊕◯) with an accessible
text equivalent, always accompanied by a machine-readable evidence count and, where downgraded, a
**downgrade reason code**. A confidence mark that does not say *why* is decoration.

**SIG-UI-004 (MUST).** The four epistemic fields (§10.7) MUST be independently visible. A single
fused badge is prohibited, because "strongly supported but contested" and "confirmed but
historical" must both be expressible at a glance.

**SIG-UI-005 (MUST).** Encoding MUST NOT rely on colour alone (WCAG 1.4.1). Every epistemic state
MUST carry a redundant non-colour channel: glyph, texture, or text.

**SIG-UI-006 (MUST).** Saturated colour MUST be reserved for epistemic state and data, never for
decoration. **Green MUST NOT be used for epistemic state** — it reads as endorsement, and SIG does
not endorse; it reports.

**SIG-UI-007 (MUST).** **Absence MUST have exactly one visual texture** (a hatch), used for nothing
else and meaning exactly one thing: *we do not have this*. The four absence kinds (§9.5) MUST be
distinguishable within it, and each MUST be **clickable, generating a research task**. This turns
the gap from an admission into an invitation — and it is what stops a mostly-hatched map from
reading as "this site has nothing."

**SIG-UI-008 (MUST).** A contested value MUST carry a persistent marker at every appearance —
table cell, summary tile, map popup, API response, export — not only in a detail view. A user who
never opens the detail must still know the number is disputed.

**SIG-UI-009 (MUST).** Contradictions MUST render as a **value range with the competing claims
plotted**, each labelled with source, tier, date, and document link, plus an explicit note where
the values measure *different quantities* (§29.1). The user must be able to see at a glance that
"42 vs 38" is not necessarily a disagreement.

### 39.2 The local dossier

**SIG-UI-010 (MUST).** The dossier is the primary public artifact. Sections, in order: at-a-glance;
what is deployed; cost and expiry; who else can see the data; configuration and retention; usage;
where the hardware is; policy; accountability events; timeline; **what we don't know**; how we know
this.

**SIG-UI-011 (MUST).** **"What we don't know" is not an appendix.** It appears in the summary, in
the print export, and in the API. In a project whose standard is "no synthetic certainty," the gap
list is a headline feature.

**SIG-UI-012 (MUST).** Every dossier MUST carry an explicit incompleteness banner naming the number
of unresearched fields and stating that absence of a row is not evidence of absence
(OL-9.4-01, OL-9.4-02).

**SIG-UI-013 (MUST).** The dossier MUST have a **print/PDF path** producing a document suitable for
handing to a council member: paginated, with sources, with the as-of date and permalink on every
page. The outline's design center needs paper, not a URL.

**SIG-UI-014 (MUST).** Every material figure MUST be expandable to its reconciliation: the rule
that fired, the competing claims, each source's tier and date, and a link to the document at the
page or cell that supports it.

**SIG-UI-014a (MUST).** The dossier MUST carry three blocks the outline's §15.1 field list omits.
Each is what converts the dossier from a description into something a person can act on:

| Block | Fields | Why it is the difference between informing and enabling |
|---|---|---|
| **`authorization`** | Which body approved it; the vote; **whether it passed on a consent agenda**; whether public comment was taken; the date | *"Approved 7–0 after public comment"* and *"passed unopposed on the consent agenda with no discussion"* are politically opposite facts. The second is the single most actionable thing a local advocate can learn, and no existing dataset records it |
| **`termination_mechanics`** | Auto-renewal flag; notice window; the **`next_decision_date`** derived from them | An expiry date is the wrong figure to surface. A contract expiring 2027-04-02 with auto-renewal and a 90-day notice window has a real deadline of **2027-01-02** — and after that date the decision is made by default. The dossier MUST surface the *decision* date, not the *expiry* date |
| **`legal_regime`** | The applicable state statute; the local ordinance; the disclosure duties each imposes | This answers *"what lever exists here?"* — whether there is a statutory retention cap, a disclosure duty, or an ordinance requiring council approval. Without it a reader knows what is happening but not what can be done about it |

**SIG-UI-014b (MUST).** `next_decision_date` MUST be computed and displayed wherever an expiry is
displayed, and the renewal watch (§39.5) MUST key its alerts on it.

**SIG-UI-015 (MUST).** The dossier MUST render **the outline's** Appendix B content contract in full, including the
`unknown` values — a policy whose configuration evidence is unknown MUST display as "unknown," not
be omitted.

### 39.3 The infrastructure map

**SIG-UI-016 (MUST).** Layers: physical devices; deployments; RTCCs and integration hubs; sharing
edges; private-public networks; service areas; lifecycle status. Derived layers (FOV, coverage)
MUST be separately toggled and visually distinct (SIG-GEO-006).

**SIG-UI-017 (MUST).** The **coverage underlay MUST be bound to the point layer with a single
control**, so a user cannot look at points without seeing where SIG has not looked. Two independent
toggles would let the map lie by default.

**SIG-UI-018 (MUST).** Low-coverage areas MUST NOT be able to read as low-density. Desaturation or
value-suppressing encoding MUST be applied so that "we don't know" is visually distinct from
"there is little here."

**SIG-UI-019 (MUST).** At national zoom the map MUST switch to density binning; individual points
appear only where the zoom supports honest rendering of their precision.

**SIG-UI-020 (MUST).** Assets with no coordinates MUST be represented — as jurisdiction-level
indicators — never silently dropped. A map that shows only locatable assets systematically
understates capability, which is the outline's core critique of camera maps.

**SIG-UI-021 (MUST).** Sharing edges MUST NOT be drawn as a national hairball. Default to an
ego-network from a selected entity, with matrix and arc views as alternatives.

### 39.4 The network explorer

**SIG-UI-022 (MUST).** Default view is an **ego network with expansion**, not a global graph.

**SIG-UI-023 (MUST).** Every centrality or hub statistic MUST carry an **ER-quality disclosure**
inline (P6, SIG-IDENT-030). If entity resolution is imperfect, so is every network statistic, and
the UI must say so where the statistic appears, not in a footnote.

**SIG-UI-024 (MUST).** The three access edge types MUST be visually distinct and independently
filterable, and MUST NOT be shown merged by default (§12.2).

**SIG-UI-025 (MUST).** Access-path closure results MUST show the full hop list with per-hop
evidence and MUST label paths beyond the published hop threshold as speculative
(SIG-RECON-050).

### 39.5 Procurement and renewal watch

**SIG-UI-026 (MUST).** For every contract: expiry, renewal window, notice deadline, approving body,
next scheduled meeting, and replacement procurement if known.

**SIG-UI-027 (MUST).** Subscriptions MUST be offered by jurisdiction with iCal and RSS output, so a
local group can put a renewal deadline in their own calendar. This is what turns passive history
into "actionable civic timing" (OL-15.4-01).

#### 39.5a The evidence recommender

**SIG-UI-027a (MUST).** For a given upcoming decision point — a renewal, a council agenda item, a
hearing — SIG MUST be able to produce a ranked list of the evidence artifacts most useful to a
person preparing for it. This is the component that makes journey **J-3** executable
(SIG-CHART-008); without it J-3 cannot pass.

Ranking inputs, all already present in the model:

| Input | Contribution |
|---|---|
| Claim directness `D` for the predicates at issue | `D1`/`D2` artifacts rank above `D3`+ |
| Currency `C` relative to predicate volatility (§28.3) | Fresh artifacts on volatile predicates rank up |
| Open contradictions touching the subject | Artifacts on both sides of a live dispute rank up |
| Open research tasks for the subject | Named gaps rank up, as things to raise |
| Artifact type vs the decision type | A contract and its amendments rank first for a renewal |
| `capture_status` | Retrievable artifacts rank above paywalled or link-rotted ones |

**SIG-UI-027b (MUST).** The recommender MUST NOT rank by "persuasiveness", sentiment, or predicted
effect on a vote. It ranks by evidentiary directness, recency, and dispute status only. A tool that
optimized for persuasion would make SIG an advocacy instrument and forfeit the neutrality on which
its usefulness to every other persona depends.

**SIG-UI-027c (MUST).** Output MUST be exportable as a citation list with permalinks and as-of
dates, suitable for attaching to public comment.

### 39.6 The evidence viewer

**SIG-UI-028 (MUST).** MUST render the document with the supporting span highlighted at its
locator, and MUST show: the claim; the extraction method and version; review status; conflicting
claims; capture date and digest; acquisition method; and the full history of the claim.

**SIG-UI-029 (MUST).** MUST support **diffing two captures of the same artifact**, field by field,
so "what changed on the portal between June and August" is directly visible (§29.7).

**SIG-UI-030 (MUST).** For `sealed` captures, MUST show the metadata-only representation with an
explanation of why the bytes are withheld (§17.5).

### 39.7 The research queue

**SIG-UI-031 (MUST).** Task cards MUST state the closing condition, the evidence sought, the
assignee class, and the effort estimate. MUST support geographic filtering, claiming with expiry,
and the full disposition vocabulary including "searched, found nothing" (§33.2).

### 39.8 Corrections, methodology, and metrics

**SIG-UI-032 (MUST).** A **public corrections log** MUST exist as a first-class page, listing every
correction with what changed, when, why, and who reported it. *(The outline has seven surfaces and
none is a corrections surface — this is a required addition.)*

**SIG-UI-033 (MUST).** A public **dispute/correction submission** path MUST exist on every page,
one click from any claim (§45).

**SIG-UI-034 (MUST).** A methodology page, a data-freshness page (§32.4), and a coverage-metrics
page MUST be public and linked from every dossier.

### 39.9 Citation and permanence

**SIG-UI-035 (MUST).** Every page MUST expose a belief-pinned permalink and a "cite this page"
affordance including the as-of pair and the ruleset version. A citation of SIG made today MUST
remain reproducible after SIG corrects itself (SIG-TIME-008).

---

## 40. Implementation stack and design system

**SIG-UI-036 (SHOULD).** The frontend SHOULD be a **zero-JS-by-default static-first framework with
opt-in interactive islands**. Rationale: SIG pages will be archived, cited in filings, and read
from web archives years later. A framework whose *default* is no client JavaScript makes
archivability structural — breaking it requires an explicit, greppable directive — rather than a
discipline that erodes.

**SIG-UI-037 (MUST).** Core content MUST be usable **without JavaScript**. Every map MUST have a
tabular equivalent; every graph MUST have a list equivalent. This is simultaneously an
accessibility requirement and an archival one.

**SIG-UI-038 (MUST).** Maps MUST use an open-source renderer with self-hosted vector tiles
(§19.5). Third-party tile CDNs MUST NOT be a hard dependency, and basemap attribution MUST be
correct in every context (SIG-GEO-013).

**SIG-UI-039 (MUST).** Every dependency MUST be OSI-licensed. Non-commercial (CC-BY-NC),
source-available, and dual BUSL licences MUST be excluded — this rules out several popular graph
and search components, and the exclusion MUST be checked in CI, not by memory.

**SIG-UI-040 (SHOULD).** Search SHOULD start with Postgres full-text search and add a dedicated
engine only on demonstrated need, checking licensing at that time.

**SIG-UI-041 (MUST).** Performance budgets MUST be enforced in CI, with the build failing on
regression. A dense evidence page that takes eight seconds to load will not be used at a podium.

---

## 41. Editorial standards

**SIG-UI-042 (MUST).** Each dossier template version MUST receive a recorded **hostile-reader
review** before release: two reviewers independently read a real rendered dossier adopting the
stance of the documented organization's counsel, log every sentence they would challenge, and sign
off. The review, its findings, and their disposition MUST be committed alongside the template
version. Release is blocked until every finding is dispositioned.

*Rationale (not itself testable).* The standard being approximated is that a police chief or vendor
counsel reading their own dossier should find it accurate, neutral, and hard to attack. That is not
politeness — it is the property that makes the work usable as evidence. The recorded review above is
the testable proxy.

**SIG-UI-043 (MUST).** Register rules:

1. Report; do not characterize. "The portal reported 38 cameras on 2026-07-01," not "the department
   admitted to only 38 cameras."
2. Never state an allegation as a fact. `epistemic_status` governs the verb.
3. Attribute every evaluative statement to its source.
4. Prefer the specific and dated to the general and timeless.
5. Name uncertainty in the same sentence as the number.
6. Do not editorialize about motive. SIG documents what institutions do, not why.

**SIG-UI-044 (MUST).** Every page MUST carry a "How we know this" module: artifact counts, tier
distribution, source-independence count, date range, rules applied, and human-review status.

**SIG-UI-045 (MUST).** Example conformant copy for the three hardest cases:

> **A pending lawsuit.** "A complaint filed 2026-03-04 in [court] alleges that a plate misread led
> to a wrongful stop. The allegation has not been adjudicated. The department has not filed a
> public response as of 2026-08-20. [complaint, p. 4]"

> **A policy/configuration divergence.** "The department's written policy, adopted 2025-11-02,
> prohibits use of the system for immigration enforcement. A configuration export dated 2026-05-02,
> obtained by records request, shows an immigration-related hotlist enabled. SIG has not determined
> which reflects current practice; both documents are linked, and this is an open question."

> **A cancellation with hardware remaining.** "The city council voted on 2026-07-14 not to renew
> the contract, which expires 2026-09-30. As of the most recent field observation on 2026-08-11,
> 23 devices remain physically installed. SIG has no evidence about whether they are operational.
> This is not a record of surveillance being removed."

**SIG-UI-046 (MUST).** A public **style guide** MUST codify these rules, and editorial review MUST
apply them to generated rationale templates as well as to hand-written copy — generated text is
published text.

---
