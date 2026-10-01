# D3 — Product direction for Round 11

> **Agent draft for operator ratification at S5. Nothing here is decided until the operator confirms it verbatim.**
> Operator words are quoted with U-ids; everything else is agent synthesis. D2 is batched with S5 and may amend this memo.

Written 2026-09-30T22:03Z (`date -u`), HEAD `95340b50`. Inputs: U-001…U-015, META_PLAN §1/§3/§4/§7, C5, C6, K12a/b, I7,
J3, G2, G3, K4, K7, spec §1–§2 and §39.0.

## 0. Headline direction

**Round 11 makes SIG show, correct and open up the evidence it already holds, while growing US-wide vendor coverage
from high-quality origins.**

Today a visitor sees SIG's honesty mechanics but never its joined evidence (C5 §4). The gap is mostly "a routing and
labelling problem over data that already exists" (K12b §2).

The work runs in this order:
1. safety and honesty;
2. correctness;
3. exploration.

Source growth runs in parallel.

## 1. What SIG is (landing-page text, agent-drafted from U-001 and spec §1)

> SIG, the Surveillance Infrastructure Graph, is an open, evidence-first record of public surveillance infrastructure.
> It joins independent public sources — crowdsourced maps, agency and vendor disclosures, contracts, policies, grants
> and records releases — into one knowledge graph showing what surveillance capabilities exist where, who operates them,
> who can access their data, what rules and contracts govern them, and how that has changed over time. Every claim
> links to its evidence; disagreements between sources stay visible; every gap is labelled as not researched, searched
> and not found, or contested. SIG is not a census and not another camera map: it reconciles existing projects and links
> to them. It is built first for someone with a council meeting in days who needs a printable, sourced dossier, and for
> journalists and organizers who need to trace any figure to its document.

## 2. Audiences and acceptance journeys

**Audiences.** The local advocate stays the design centre (U-002: *"yes for Q-D1-02"*) and decides conflicts over
register and print. Journalists and organizers are co-primary (U-002: *"but also think investigative journalists and
other organizers"*), and their journeys gate the capstone equally (§7 Q1).

**Test.** Every journey starts cold at `/`, on desktop and at 390 px. It is walked twice: once by a fresh-context agent
(recorded as `agent-verified`, never as "user-tested") and once by the operator. A journey **passes** when it stays
within its budget (an agent estimate), carries no wrong-conclusion risk, and gives every fact a source, an as-of date
and a release id.

**Local advocate, council meeting in 6 days (≤10 min in total)**

| id | budget | task | pass |
|---|---|---|---|
| A1 | 1 min, ≤3 clicks | Type "Oklahoma City" | Reaches the city dossier, or the nearest record stating "no city-level record". Places appear by name, never by code |
| A2 | +3 min | Find what is deployed, who runs and approved it, and the next decision | Each answer is a sourced value, or a typed absence that says what would close it |
| A3 | +2 min | Print it for a council member | Page 1 is a council brief. Every page shows the as-of date, release id, permalink and licence |
| A4 | +3 min | Know what to bring | A place document list, plus a records-request template for the top unknown |

**Investigative journalist.** U-005: *"really truly explore the knowledge graph, answer questions … interactively,
always with full explicit transparent evidence/lineage"*.

| id | budget | task | pass |
|---|---|---|---|
| J1 | 5 min | Defend a headline figure | The figure shows its unit, denominator, "not a census", as-of date, release id and provisional flag. Its rows download in ≤3 clicks |
| J2 | 10 min | "Who supplies ALPRs to Texas agencies, and who can access the data?" | Name search reaches the vendor and agency pages. Every edge shows its date, currency and source, with evidence ≤2 clicks away. No UUIDs appear |
| J3 | 3 min | Is this figure disputed? | A contested marker, with both sides 1 click away |
| J4 | 3 min | Cite it durably | The pinned URL returns identical bytes after the next release |
| J5 | 5 min | What changed since the last release? | A changes page and a feed per place, source and entity |

**Organizers**

| id | budget | task | pass |
|---|---|---|---|
| O1 | 3 min | Who runs what in my county or city? | Named agencies, technology classes and counts. Each is sourced or shown as a typed absence |
| O2 | 2 min | Who decides and when, and can I subscribe? | The approving body and the next date, or a typed absence. An iCal/RSS feed |
| O3 | 2 min | A local list without the map | A no-JS list with CSV, licence and attribution |
| O4 | 3 min | Act on a gap | A plain-language task with a closing condition, a request template and where to send results |

## 3. Success criteria (U-007's three outcomes)

**(a) Features and UX.** U-007: *"query/explore/navigate … while maintaining strict standards of evidence/lineage"*.
- All 13 journeys pass live.
- U-003.1 to U-003.11 pass their K-row acceptance live.
- 0 UUID-only labels and 0 undated edges.
- Every figure reaches its evidence in ≤2 clicks, or states why it cannot.
- Search resolves 55 jurisdictions, 20 cities and the top 25 vendor and agency names.
- The K0 budgets and accessibility checks pass on real data.

**(b) Correctness and comprehensiveness.** U-007: *"_high quality_ sources to maximal degree … increased confidence in
algorithms"*.
- **Correctness:**
  - no mixed-scheme dossiers;
  - no undisclosed out-of-polygon points;
  - `unresolved` is not a jurisdiction;
  - a clean C3 number trace;
  - every site row is technology-typed.
- **Coverage:**
  - every US state and DC has a dossier (22 lack one today);
  - OSM ALPR, Eyes on Flock and Atlas vendor data reach place and entity pages;
  - Flock, Axon and Motorola/Vigilant exist as entities with dated, sourced agency links;
  - all 154 I7 Tier-1 and widening candidates are live or dispositioned;
  - I7's projected reach is verified live: 40 of 51 states plus DC, and 28 of 29 technology classes.
- **Confidence:**
  - L1 and L2 are published with baselines and targets;
  - real-data invariants run in CI;
  - anything unevaluated is labelled PROVISIONAL.

**(c) Clarity.** U-007: *"beautiful experience … very clear what the project is and why it exists"*.
- §1 is above the fold.
- The home page is ≤5 screens at 390 px, with ≤6 quotable figures.
- There are 0 internal ids in prose.
- The K14 design system, with dark mode, covers every template.
- Each persona has a "start here" path.
- A fresh agent can say what SIG is, what it isn't, and three things it does, within 2 minutes.
- "Beautiful" is the operator's call.

## 4. Round-11 scope

**Must ship, in order**
- **Wave 0, safety and honesty** (G2 step 0; §7.1 approved in principle):
  - the six S0s;
  - QW-1 to QW-15;
  - G1 QA-1 to QA-10 plus a restore drill;
  - one publish path;
  - the attribution fix;
  - an honest API;
  - withdrawing forbidden-terms sources;
  - no wording that implies counsel, an editorial board or human verification (U-013).
- **Wave 1, correctness:**
  - a canonical jurisdiction key;
  - a geometry gate;
  - technology typing;
  - routing governance, procurement and sharing claims to places and entities;
  - names instead of UUIDs;
  - dated edges;
  - "explain this number".
- **Wave 2, exploration:** K0, then:
  - basemap (K1);
  - entity pages and bounded graphs (K2);
  - typed search (K3);
  - county and city dossiers (K4);
  - source ledgers (K5);
  - embedded visuals (K6);
  - watch feeds (K7);
  - evidence locker (K8);
  - source pages and zero-egress downloads (K9, K10, J3);
  - research questions (K11);
  - design and onboarding (K14).
- **Round-10 features (Q-9, per G2):**
  - archive, pinned citations and release search at step 7 (HG-11);
  - research dossiers only after live captures;
  - intake dark unless Q2 says otherwise.
- **In parallel from week 1:**
  - Stream I: the widening group first, then Tier 1, each after its HG-03 packet;
  - Stream L.
- **Geography:**
  - US-nationwide; non-US dossiers are corrected but not expanded;
  - 1–3 "golden" places, chosen by the agent, where at least 4 independent sources overlap and disagree (C5 §7).

**Later**

| item | why |
|---|---|
| A whole-graph canvas (10⁵+ nodes) | No peer offers one; renderers handle about 10³–10⁴ labelled nodes (K12a) |
| Outreach, sending records requests, recruiting | U-011: *"no one should be contacted outside the project"* |
| Independent human evaluation | U-008: *"no humans on our team other than me"*. Round 11 measures, discloses and marks results PROVISIONAL |
| Counsel-dependent obligations | U-013: *"err on the side of not blocking on counsel"*. These become waivers |
| Email alerts, accounts, paid or international data, tribal-keyed data | Privacy; Q-21 = $0; the US focus (U-007); I7 NEW-6 |

**Constraints**
- **Cost.** Keep total cost ≤$300/mo. Today's estimate is ≈$90–100/mo (G1, unverified); the R2 basemap adds ≈$2/mo.
  - Every design states its monthly cost.
  - Anything above $300 needs the operator's go on a stated trade-off (U-008).
- **Autonomy.** Agents have maximal autonomy, with a visible spend ledger (U-011).
- **Standing go.** It covers Class R releases only (G3).

## 5. Ready to announce (U-009: *"when the time is right"*)

- [ ] The operator's test, the inverse of U-005: "I would send this to a journalist today."
- [ ] Every S0 is closed live, and every status word is bound to recorded state.
- [ ] All 13 journeys pass both walkthroughs (agent and operator).
- [ ] The §3(b) correctness criteria hold live.
- [ ] The attribution gate and the Part VIII screens are green, and forbidden-terms sources are withdrawn.
- [ ] Every page shows a pinned citation and its release id.
- [ ] Zero-egress serving is live, and the kill switch and budget alert have been tested.
- [ ] Cost at 100× traffic stays within $300/mo, or the operator has approved more.
- [ ] Backups, a drilled restore and operator alerts are in place.
- [ ] The dispute email discloses single-maintainer response times.
- [ ] The §1 text, a known-issues page and the PROVISIONAL disclosures are live.
- [ ] The operator has confirmed the announcement copy and posts it. Agents contact no one.

## 6. Principles and non-goals to preserve

- **Evidence.**
  - Every fact is evidenced, and every claim carries provenance.
  - Contradictions stay visible, and absences are typed.
  - No totals, and no claim to be a census.
- **Part VIII.**
  - No plate or person data; institutions only, under the officer-naming gate.
  - Audit data appears only as aggregates.
  - No evasion instructions.
  - No user location is shared with third parties.
- **Print and interactivity.** The printed and cited record stays complete, zero-JS and citable (consistent with K0's
  HTML-first page types). Interactivity enhances pages, never replaces that record:
  - every visual has a table equivalent;
  - every view keeps its state in the URL;
  - no SPA.
- **Precision.** U-004: *"I like how technically precise the language is and how clear the definitions, editorial
  standards, methodology, etc. are articulated."* Add a plain-language layer and cut verbosity (U-005); never dilute a
  definition.
- **Stance.** A neutral register. Not another camera map. Link to peers rather than rebuild them.
- **Data integrity.** Append-only data, the ingestion gate, and HG-03 flips owned by the operator.

## 7. Open questions for S5

1. **Q1 — Co-primary audiences.** Should journalist and organizer journeys gate the capstone equally, with the advocate
   winning conflicts? *Recommend: yes.*
2. **Q2 — Intake (Q-27).** Should the correction form open in Round 11, with you as sole moderator, or stay email-only
   until after the announcement? *Recommend: email-only.*
3. **Q3 — Vendor terms.** Flock's API terms and Axon's ToS forbid automated extraction (I7 packets C4). Should Flock
   and Axon facts come only from agency pages, procurement records and statutory reports, and never from vendor hosts?
   This limits how deep that coverage can go. *Recommend: accept.*
4. **Q4 — Linking (C5 Q-C5-1).** Should dossiers carry a neutral "Other public resources" block (Atlas, Eyes on Flock,
   DeFlock, the ACLU toolkit, alpr.watch), excluding avoidance routing and plate lookups? *Recommend: yes.*
5. **Q5 — Landing text and announce gate.** Do you confirm §1 verbatim and §5 as the gate, or would you allow an earlier
   share labelled "preview"?
