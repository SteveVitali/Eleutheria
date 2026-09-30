# C5 — Landscape and differentiation scan

- **Row:** C5 (Stream C, research, optional, Q-18) · **Written:** 2026-09-30 (research window 2026-09-30T18:15:42Z –
  18:22:22Z, `date -u`) · **Worktree HEAD at start:** `038e25b9`
- **Feeds:** C6 (review synthesis), D3 (product direction), E2 (SIG-CONTRIB-012 option memo), I-rows (source candidates).
- **Query log (P15):** `data/query_log_C5.csv` holds **59 logged rows**: 31 curl, 23 WebFetch, 4 `gh api`, and 1 WebSearch
  that was **not performed** because the session's WebSearch budget was exhausted (200/200). 44 rows kept at least one hit.
  Three rows (Q019, Q027, Q032) issued the same URL twice in one command, so there were 61 HTTP GETs in total. That is one
  over the 60 time box, and it is disclosed here. Every `[Qnnn]` below resolves to a row in that log. Only fetched pages are
  cited. A search-engine summary is never cited.
- **Evidence classes (P1):** peer facts and SIG live facts are `live-read` (fetched 2026-09-30). Facts about SIG's
  registry, spec and sibling rows are `code` (file:line). Ratings, differentiators, gaps and positioning (§§3–7) are
  `inference`, and they are labelled as such.
- **Status vocabulary (P5):** "SIG today" means what the public site at `surveillancegraph.org` showed on 2026-09-30
  (release as-of 2026-09-27). "SIG in principle" means what the spec requires. Nothing here is `engineered` or verified work.
- **Part VIII preflight:** Have I Been Flocked shows plate lookup and operator names [Q004]. The Eyes on Flock API carries
  audit search-reason fields [Q011]. No values from either were printed or retained: only field names and counts were
  computed, and the file was deleted. No person- or plate-level data appears in this note.

---

## 0. Summary

**Matrix headline (inference, §2).** Thirteen core tasks were scored for the design centre (a local advocate with a
council meeting in days, SIG-UI-002) and the co-primary audiences (investigative journalists and organizers, U-002). On
the live site today SIG fully answers **1 of 13** (a printable, citable brief), partly answers 6, does not answer 5, and
excludes 1 by design ("how do I act"). Peers already answer the agency-level questions well:

- what is deployed: Atlas, Eyes on Flock, city portals
- which vendor: Atlas, Eyes on Flock
- who can receive the data, and what retention and prohibited uses apply: Eyes on Flock, for 1,528 Flock portals, with a
  median update of 2026-09-23
- when it is on an agenda: alpr.watch, Oakland and Seattle
- how to act: DeFlock, the ACLU, S.T.O.P.

Three cells are **empty across the whole ecosystem**:

- **A3:** what does it cost, and when is the next decision or renewal date?
- **A8:** do the sources disagree?
- **A11:** a per-jurisdiction printable, cited brief. DeFlock's own council guide asks advocates to "Bring a brief printed
  summary of key points" and leaves them to make it themselves [Q016].

That white space is exactly what the SIG spec promises. It is also the place where the live site is weakest: only the
*form* of A11 is demonstrated.

**SIG's real differentiators:**

| differentiator | on the page today? |
|---|---|
| Epistemic honesty: "not researched" vs "unresolved" vs "unknown", named denominators, "not a census" | **Demonstrated.** No peer seen does this. ALPR Accountability Atlas comes closest [Q035] |
| Printable, as-of, belief-pinned, citable dossier | **Form demonstrated** (zero-JS print view, permalink on every page [Q051]). **Substance absent**: every governance field is "unknown" [Q038] |
| Joined evidence across independent sources (SIG-CHART-002) | **Not demonstrated.** The TX dossier joins 4 camera-registry sources only [Q038]. Atlas, Eyes on Flock and CCOPS claims never reach a jurisdiction page (I1 NEW-4) |
| Contradictions | **Barely demonstrated**: coordinate conflicts only ("⚠ Unresolved" [Q038]). There is no source-vs-source or vendor-vs-record case |
| Access / relationship graph (configured vs observed vs declared) | **Concept demonstrated, content illegible.** 131 nodes are labelled only by UUID, with one hub of degree 130, and every edge is "weakly supported (1 of 4)" [Q043][Q045] |
| Temporal history | **Mechanics only.** The as-of permalinks work, but the TX "Timeline" section is empty [Q038] |
| Claim-level provenance | **Not demonstrated.** "No claims with a full evidence view yet" [Q041], and sources appear as bare registry ids [Q038]. Atlas (per-record MuckRock/DocumentCloud links [Q019]) and Eyes on Flock (`portal_url` on every row [Q011]) do better |

**Top 3 gaps vs peers (inference, §4):**

1. **The vendor, sharing and retention questions go unanswered even though SIG ingests the peers that answer them.** Atlas
   gives the vendor per agency. Eyes on Flock gives sharing partners (917 portals), retention (1,462) and prohibited uses
   (1,458). SIG's TX page says "unknown" and "Not researched".
2. **There is no city or agency lookup.** SIG has 55 dossiers, all state-level or national, and no city or county
   dossier [Q037][Q038]. Atlas answers "Austin" in one server-rendered search [Q010].
3. **"When is it decided, and how do I act" leads to a dead end.** `/watch/` is empty [Q040], and SIG pages carry **0
   outbound links** to any peer or official portal [Q046–Q050]. Meanwhile alpr.watch sends agenda alerts by ZIP code
   [Q053], Oakland's PAC lists a meeting on 2026-10-01 [Q030], and DeFlock and the ACLU publish action guides
   [Q016][Q034].

**Top linking and collaboration opportunities (inference, §5):**

1. **Add a per-dossier "elsewhere" block plus per-claim origin links:** the Atlas record, the Eyes on Flock / Flock
   `portal_url`, the DeFlock council, FOIA and groups pages, the alpr.watch alert, the ACLU toolkit, and the city
   SIR/PAC page. This is SIG-CHART-002 applied literally.
2. **Get listed in the hubs that already link each other.** The ACLU "Get the Flock Out" toolkit links deflock.org,
   haveibeenflocked.com and alpr.watch [Q058]. The Atlas Data Library links 25+ projects [Q059]. Neither mentions SIG.
   Seek a listing only after one joined, city-level dossier exists.
3. **Stage-0 outreach with concrete offers (SIG-CONTRIB-012a).** Offer Eyes on Flock and Atlas a joined diff:
   portal-vs-Atlas-vs-OSM discrepancies returned upstream. Offer DeFlock plausibility checks, plus the dossier as the
   "printed summary" its guide asks for. Add alpr.watch, which is absent from the registry and the spec, to the compact
   list.

---

## 1. Tasks scored

The tasks come from the spec's persona table (`docs/2_canonical_design_spec.md:5721-5730`), U-001 (joined evidence, a
printable dossier, linking rather than rebuilding) and U-002 (journalists and organizers as co-primary audiences).
**D** = design centre, **J** = journalist, **O** = organizer.

| id | task (the 10-minute question) | who |
|---|---|---|
| A1 | What surveillance is deployed in my city or agency? | D, O |
| A2 | Which vendor supplies it? | D, J |
| A3 | What does it cost, and when is the next decision or renewal (notice) date? | D |
| A4 | What rules govern it: retention, prohibited uses, use policy, ordinance? | D, J |
| A5 | Who else can access or receive the data? | D, J, O |
| A6 | Who decides, and when is it on an agenda? | D, O |
| A7 | How do I act: council guide, records request, local group? | D, O |
| A8 | Do sources disagree, e.g. a vendor claim to council vs the record? | D, J |
| A9 | Show me the document behind a claim | J |
| A10 | How has it changed over time? | J, O |
| A11 | Give me a printable, citable brief for council or a story | D, J |
| A12 | Bulk data I can reuse: download, API, licence | J |
| A13 | Documented misuse or usage: audits, incidents | J, O |

---

## 2. Capability matrix (tasks × projects × SIG)

Legend: ● answers directly · ◐ partial or narrow · ○ not offered · n/o not observed in this row · ✕ excluded by design.
The cell ratings are `inference` from the cited `live-read`s. † means the page is client-rendered, so its content was not
read.

| task | Atlas (EFF) | DeFlock | Eyes on Flock | HIBF | ALPR Watch (.org) | alpr.watch | ALPR Acct. Atlas | ACLU (CCOPS + GTFO) | Seattle / Oakland official | Georgetown CPT | S.T.O.P. / LPL | Surveillance Watch | **SIG today** | **SIG in principle** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 deployed here | ● [Q010] | ◐† [Q009] | ● [Q011] | ◐ [Q004] | ◐ [Q005] | ◐ [Q053] | ○ | ◐ [Q034] | ● own city [Q033][Q030] | ◐ FR 2016 [Q025] | ○ | ○ | ◐ map only [Q044] | ● |
| A2 vendor | ● [Q019] | n/o | ● Flock-only | ● Flock-only | n/o | ○ | ◐ Flock-only | ○ | n/o | n/o | ○ | ● corp. graph [Q032] | **○** [Q038] | ● |
| A3 cost / decision date | ○ [Q019] | ○ | ○ | ○ | ○ | ◐ agenda flag | ○ | ○ | ◐ process [Q033] | ○ | ○ | ○ | **○** [Q038][Q040] | ● SIG-UI-014b |
| A4 rules | ○ | ○ | ● retention, prohibited uses [Q011] | ○ | ○ | ○ | ◐ | ◐ 26 CCOPS [Q021] | ● SIRs, use policies | ◐ model policy | ◐ NY tracker [Q023] | ○ | **○** [Q038] | ● |
| A5 access / sharing | ○ | ○ | ● named orgs, 917 portals [Q011] | ◐ ⚠VIII | ○ | ○ | ○ | ○ | n/o | ◐ ICE narrative [Q026] | ○ | ◐ | ◐ UUID-only [Q043] | ● SIG-UI-024 |
| A6 who decides / when | ○ | ◐ guide | ○ | ○ | ○ | ● ZIP alerts [Q053] | ○ | ◐ | ● agendas, 10-01 mtg [Q030] | ○ | ◐ | ○ | **○** [Q040] | ● watch + ICS |
| A7 how to act | ○ | ● [Q016–Q018] | ○ | ○ | ◐ | ◐ | ○ | ● [Q034] | ◐ comment stage | ◐ model acts | ● NY / ◐ Chicago | ○ | ✕ (dispute link only) | ✕ → link |
| A8 sources disagree | ○ | ○ | ○ | ○ | ○ | ○ | ◐ keeps claim types distinct [Q035] | ○ | ○ | ○ | ○ | ○ | ◐ coordinates only [Q038] | ● |
| A9 document behind claim | ◐ per-record links [Q019] | n/o | ● `portal_url` every row | ◐ | n/o | ○ | ● source index [Q035] | ○ | ● primary docs | ◐ | ○ | n/o | ◐ aggregate only [Q041] | ● |
| A10 change over time | n/o | n/o | ◐ `data_last_updated` | ○ | n/o | ○ | ◐ "checked through" | ◐ | ● filings 2017–2025 [Q033] | ◐ 2025 foreword | ○ | n/o | ◐ as-of links, empty timeline [Q038] | ● |
| A11 printable cited brief | n/o | ○ (asks users to make one [Q016]) | ○ | ○ | ○ | ○ | ○ | ◐ toolkit | ◐ per-tech SIRs | ◐ national report | ○ | ○ | **● form / ○ substance** [Q051] | ● SIG-UI-013 |
| A12 bulk data | ● CSV, CC BY [Q057] | ◐ via OSM (not verified here) | ● JSON API, CC BY-SA (registry) | ○ [Q004] | ● KMZ, API [Q005] | ○ | ● CSV, GeoJSON [Q035] | ○ | ◐ docs | ◐ PDFs | ○ | n/o | ◐ dossier JSON [Q038] | ● |
| A13 misuse / usage | ○ | ○ | ◐ search counts | ● ⚠VIII [Q004] | ◐ FOIA dashboards | ○ | ● incidents [Q035] | ○ | ◐ annual reports | ◐ | ◐ LPL FOIA | ○ | ○ | ◐ (Part VIII limits) |
| **freshness seen** | "last updated on Aug 27, 2026" [Q008] | n/o† | median 2026-09-23 [Q011] | "months or even years" lag [Q004] | none shown | "future flags 100% moderator approved" | client-side | map 2024-11-21 | Master List Sept 2025; mtg 2026-10-01 | 2016; 2025 foreword | active | n/o | as-of 2026-09-27 | — |

**Readings (inference):**

- **No single peer answers more than 4 tasks at ● for one city.** The official Seattle and Oakland portals come closest
  for their own city (A1, A4, A6, A9, A10). Eyes on Flock is the strongest *data* peer for A4 and A5, but only for Flock.
- **The ecosystem's empty cells are A3, A8 and A11.** No peer offers any ● in A3 (cost and decision date) or A8 (source
  disagreement). For A11 (a per-jurisdiction cited brief), the SIG print view is the only one, and it is thin. These
  cells are SIG's spec-defined niche (SIG-UI-013, -014b; §29; SIG-CHART-002).
- **SIG today scores below its own upstreams on A2, A4 and A5.** It ingests Atlas (15,187 claims) and Eyes on Flock
  (11,976 claims per weekly run) (`research/I1-source-coverage.md:213`), but that content never reaches a jurisdiction
  page (I1 NEW-4, :521). The Atlas vendor field is not turned into claims, and the API has 0 vendor entities
  (I1 NEW-7, :524).
- **The largest quantitative surface on the live site is the map**: "232625 mapped sites" [Q044]. With the joins absent,
  a first-time visitor meets SIG as a map plus methodology. This is the SIG-CHART-001 risk ("another surveillance map")
  in practice (inference).

---

## 3. Project profiles

Short cards follow. "10 min" is what a design-centre user can finish in ten minutes, starting from the home page. It is
`inference` from the fetched pages, not a usability test.

**EFF Atlas of Surveillance** ([Q001][Q008][Q010][Q019][Q056][Q057])
- **Audience:** "journalists, academics, and, most importantly, members of the public". It is compiled by more than
  1,000 students and volunteers, with UNR Reynolds School of Journalism.
- **Scale and freshness:** "more than 15,000 datapoints in 6,000-plus jurisdictions"; "last updated on Aug 27, 2026".
- **10 min:** type a city and get a server-rendered list of agency × technology records. Each record (e.g. Manor PD ALPR)
  gives Agency, Location, Technology, **Vendor** (Flock Safety), a sentence "according to data obtained in July 2025",
  and links to MuckRock and DocumentCloud.
- **Not offered:** contract dates, cost, policy, sharing.
- **Data access:** `download.csv`, with a "CC-by" footer (the registry records CC-BY-4.0, `sources.toml` `eff_atlas_of_surveillance`).
  The Data Library also curates about 25 external datasets and projects [Q059].
- **Link to it for:** agency adoption and vendor, and the per-record origin link.

**DeFlock** ([Q002][Q007][Q009][Q015–Q018])
- The app is client-rendered. The canonical host is deflock.org; deflock.me answered 301 [Q002], where spec
  :3589 records a 403.
- **Action content, read from the public repo:**
  - **Council guide:** talking points; "Meet Council Members Privately"; "Speak at Council Meetings"; a sample email;
    "Bring a brief printed summary of key points".
  - **FOIA how-to:** permits, invoices, contracts and emails, with templates pointing to MuckRock.
  - **Local groups directory:** "independently run and are not affiliated with DeFlock".
- **10 min:** see cameras on a map (not rendered in this row), then get a council script and a records-request recipe.
- **Link to it for:** the device map, how to act, and local groups.

**Eyes on Flock** ([Q006][Q011])
- "An independent project aggregating and analyzing data from Flock Safety's public transparency portals."
- **API:** 1,528 portals (1,304 police departments, 224 sheriff's departments) in 45 states.
- **Field coverage:** every row has a `portal_url` to Flock's own portal. Sharing lists are present for 917 portals,
  retention for 1,462 and prohibited uses for 1,458.
- **Freshness:** median `data_last_updated` is 2026-09-23, and 1,486 portals were updated since 2026-09-01.
- **Licence:** CC BY-SA 4.0 per the SIG registry.
- **10 min:** find your agency and read its camera count, retention, prohibited uses, and who it shares with and receives
  from. This is the vendor's self-declared configuration.
- **Link to it for:** A4 and A5 for Flock agencies. SIG adds value only by joining this with other sources (§4).

**Have I Been Flocked** ([Q004])
- Aggregates Flock audit logs from FOIA requests and portals.
- **What it offers:** plate lookup, agency and search-reason browsing, thematic reports, and a county density map. There
  are no downloads.
- **Freshness:** "months or even years" of delay.
- **⚠ Part VIII:** plate-level lookup and operator names are shown. SIG must link only to its methodology and report
  pages, never to lookups, and must not re-host it (SIG-PUB-003a/b, H12).

**ALPR Watch, alprwatch.org** ([Q005])
- Map, suspected locations, **avoidance routing**, KMZ offline packages, an API link and FOIA dashboards. It builds on
  DeFlock and MuckRock.
- **⚠** Linking to avoidance routing may conflict with SIG's "no evasion instructions" (PROTOCOL H12). That is a
  linking-policy question for D3.

**alpr.watch** ([Q053][Q058]) — *new: absent from SIG's registry and spec (`grep` count 0).*
- Scans government meeting agendas for "flock", "license plate reader" and "alpr".
- Users can set email + ZIP radius alerts: "We'll notify you when surveillance tech appears on agendas within your
  specified radius."
- Moderated: "All future flags are 100% moderator approved."
- The ACLU toolkit links to it.
- **Link to it for:** A6. It is the closest thing to SIG's renewal watch that actually runs.

**ALPR Accountability Atlas** ([Q035])
- "A living, source-auditable map of reported issues involving Flock Safety and automated license plate readers."
- **Downloads:** ZIP, CSV issue records, a source-index CSV, GeoJSON and a data dictionary.
- **Epistemic stance:** "Allegations, findings, court actions, policy decisions, and company statements stay distinct." It
  is the peer closest to SIG's epistemic stance.
- **Link to it for:** A13 (incidents), and as a candidate for a shared vocabulary.

**ACLU: CCOPS and the "Get the Flock Out" toolkit** ([Q021][Q034][Q058])
- **CCOPS:** "adopted in 26 jurisdictions … nearly 18 million people", plus a model bill and a resource library. The map
  image is dated 2024-11-21, and there is no per-jurisdiction list with dates on the page.
- **Toolkit:** how to find out whether your city uses ALPR, three model bills, a template email and council guidance.
  Outbound links go to deflock.org, haveibeenflocked.com, alpr.watch and state affiliates (aclu-wa, aclu-ia) [Q058].
- **Link to it for:** A7, and as the organizer distribution channel.

**Seattle surveillance-technology programme** ([Q029][Q033])
- SMC 14.18. Master List filings run from 2017-11-30 to September 2025, with clerk file numbers.
- Surveillance Impact Report register, technologies under review, a public-comment stage and a community working group.
- **Link to it for:** A1, A4, A6 and A10 in Seattle. SIG already ingests it as `ccops_seattle` (5 claims, I1 :218), but
  it does not reach a page.

**Oakland Privacy Advisory Commission** ([Q030])
- Agendas since 2016 and per-technology use policies and impact reports (ALPR, BWC, ShotSpotter and others).
- **The next listed meeting is "10-1-26"**, while SIG's `/watch/` shows no decisions [Q040].
- SIG ingests it as `ccops_oakland` (46 claims, I1 :218).

**Georgetown CPT** ([Q025][Q026])
- *The Perpetual Line-Up* (2016-10-18): a face-recognition scorecard for 25 agencies, a clickable map by state and city,
  and model legislation. It is static: "© 2016".
- *American Dragnet* (2022-05-10, foreword May 2025): ICE's access to DMV, utility and child-welfare data. It has no
  lookup; it is a report only.
- **Link to it for:** the national context on A5 (federal access to local data).

**S.T.O.P. and Lucy Parsons Labs** ([Q023][Q024])
- **S.T.O.P.:** New York-focused litigation, legislation and Know Your Rights work, with a legislative tracker. No open
  data is listed.
- **LPL:** Chicago, 1,000+ FOIA requests, 100+ public-records cases, and the #StopShotSpotter coalition. No tool is named
  on its home page.
- Both are local A7 partners and potential records sources. Neither has a data surface to link to.

**Surveillance Watch** ([Q028][Q032])
- "An interactive map revealing the intricate connections between surveillance companies, their funding sources and
  affiliations." It is client-rendered, so its content was not read.
- It is relevant to SIG's organization and ownership edges for A2 (vendor → parent → funder).

**Not characterised within the time box:**
- **MuckRock:** 403 to both fetchers [Q022][Q027]. It is reached in practice through Atlas record links and the DeFlock
  FOIA guide.
- **Brennan Center:** two 404s and a landing page without surveillance items [Q031][Q054][Q055]. It is linked from the
  Atlas Data Library [Q059].
- **Flock's transparency hub:** 403 [Q036].
- **policefundingdatabase.org:** named in the Atlas library [Q059], not fetched. It is a possible A3 (cost and grants)
  source for the I-rows.

---

## 4. SIG differentiators: demonstrated or not (inference on live-reads)

1. **Epistemic honesty.** This is the one differentiator a visitor sees today.
   - Every figure names its denominator ("2423200 of 2423200 published tier-0 claims", "3994 of 3996 evaluable
     geolocated site observations … not a resolved device census") [Q037][Q038].
   - Gaps are typed, e.g. "Not researched — SIG has not looked yet. Absence of a row is not evidence of absence" and
     "⚠ Unresolved — Evidence exists and disagrees".
   - Human review is disclosed ("Not yet human-reviewed").
   - No peer seen does this. alpr.watch's counters render blank, and Atlas has one global "last updated". ALPR
     Accountability Atlas's allegation/finding separation is the nearest equivalent.
2. **The printable, citable dossier.** The **form** is demonstrated: the print view has 0 `<script>` tags, and the as-of
   pair and belief-pinned permalink are repeated on the page [Q051]. The **substance** is not. Auto-renews, notice
   window, contract expiry, next decision date, approving body, vote, statute and ordinance are all "unknown" on TX
   [Q038]. A council member handed this page learns that SIG does not know.
3. **Joined evidence (SIG-CHART-002), the defining differentiator.** **Not demonstrated.**
   - TX "How we know this" lists 4 `camreg_*` sources [Q038]. The joins that would be unique are absent: Eyes on Flock
     portal, Atlas adoption and OSM devices for the same agency; CCOPS policy; agenda and procurement dates.
   - Those joins are ingested but unattributed to places (I1 NEW-4).
4. **Contradictions.** Only coordinate conflicts are surfaced [Q038]. The spec's headline case, the persona "is what the
   vendor told us consistent with the record?" (spec :5723), has no public instance.
   - An available instance is ingested but not surfaced: Eyes on Flock `total_cameras` for an agency vs OSM ALPR points
     vs the Atlas record. Showing it would be joined evidence (inference).
5. **The access graph.** The concept is unique and is shown in the legend:
   - "◉ Configured access … Never implies: That anyone used it"
   - "▶ Observed use"
   - "§ Declared policy"

   Eyes on Flock lists partners but does not separate configured from declared. The **content is illegible**, however:
   131 UUID-labelled nodes, a single hub of degree 130, and every edge "weakly supported (1 of 4) … BEST_CLAIM_W1"
   [Q043][Q045]. Not demonstrated usefully.
6. **Temporal history.** As-of permalinks are demonstrated. There is no history *content*: the Timeline section is
   empty [Q038]. Seattle's dated Master List filings already give a better public history for Seattle [Q033].
7. **Provenance.** It is strong at the aggregate and methodology level (artifacts, tier distribution, date range,
   ruleset). It is weak at the claim level:
   - The evidence viewer has 0 entries [Q041].
   - Sources appear as bare ids with no outbound link [Q038][Q049].

   Both Atlas and Eyes on Flock put a clickable origin on each record. This agrees with J2 pattern 2
   (`research/J2-prior-art.md`).

**Net (inference).** SIG's *demonstrated* differentiation today is honesty and citation mechanics. Joins, contradictions,
the named access graph, history and dossier substance are engineered or specified, but they are not visible. The
live site does not yet show why SIG exists.

---

## 5. Gaps where SIG is weaker than a peer on a core task (inference; proposed severities for C6)

| id | gap | peer that does it better | SIG evidence | proposed sev. |
|---|---|---|---|---|
| C5-G1 | Vendor, sharing partners, retention and prohibited uses per agency are unanswered, although both upstreams that answer them are ingested | Atlas [Q019]; Eyes on Flock [Q011] | TX "Not researched" / no vendor row [Q038]; I1 NEW-4, NEW-7 | S1 (design-centre task A2/A4/A5 fails) |
| C5-G2 | No city or agency lookup; dossiers are state-level only | Atlas city search [Q010]; Eyes on Flock per agency; Seattle / Oakland | 55 dossiers, none city-level [Q037]; PROTOCOL §3 release facts | S1 |
| C5-G3 | "When is it decided / how do I act" ends in an empty watch and 0 outbound links | alpr.watch [Q053]; Oakland 10-01 meeting [Q030]; DeFlock [Q016]; ACLU [Q034] | `/watch/` empty [Q040]; 0 external hosts on 5 pages [Q046–Q050] | S1 (A6) / S2 (A7, linking) |
| C5-G4 | No claim-level origin link | Atlas per-record links [Q019]; Eyes on Flock `portal_url` [Q011]; ALPR Accountability Atlas source index [Q035] | Evidence viewer empty [Q041]; bare source ids [Q038] | S2 (journalist A9) |
| C5-G5 | Bulk data is less discoverable than peers' single-click CSV | Atlas `download.csv` [Q057]; ALPR Accountability Atlas CSV and GeoJSON [Q035] | Only dossier JSON is linked from a page [Q038]; exports are covered by J1/J4 | S3 |
| C5-G6 | The access-graph page is unreadable (UUID labels) | Eyes on Flock names partner agencies [Q011] | [Q043][Q045] | S2 |

---

## 6. Linking and collaboration opportunities, and Stage-0 outreach implications

**Linking (SIG-CHART-002: "link to that project rather than reimplement").**

- **L1 — An "Elsewhere" block per dossier** (inference). It holds jurisdiction-scoped deep links:
  - the Atlas search for the place
  - each agency's Flock `portal_url`, via the Eyes on Flock mirror
  - the DeFlock council, FOIA and groups pages
  - an alpr.watch alert sign-up
  - ACLU CCOPS and the toolkit
  - the city SIR or PAC page where one exists

  Label it neutrally ("Other public resources; SIG does not endorse"), because SIG-UI-027b bars SIG from becoming an
  advocacy instrument. Whether linking advocacy toolkits is compatible with neutrality is a **D3 decision**.
- **L2 — Per-claim origin links.** Carry the upstream record URL (Atlas `/a/<id>`, `portal_url`) through to the claim
  and render it. This closes most of C5-G4 without the full evidence viewer.
- **L3 — Do not rebuild** (inference):
  - device maps and avoidance routing (DeFlock, ALPR Watch)
  - audit-log search (HIBF; also Part VIII)
  - incident catalogues (ALPR Accountability Atlas)
  - agenda keyword alerts (alpr.watch)
  - advocacy toolkits (ACLU, DeFlock)
  - national reports (Georgetown CPT)

  SIG's own build should go to A3, A8, A11 and the joins.
- **L4 — Link policy for Part VIII peers.** HIBF gets methodology and report pages only. ALPR Watch routing is
  undecided, pending D3.

**Getting linked (inbound).** The ACLU toolkit [Q058] and the Atlas Data Library [Q059] are the ecosystem's two link
hubs. The toolkit's first step, "find out whether your city uses ALPR", is SIG's design-centre use case. Neither hub
mentions SIG. **Seek a listing only after at least one joined, city-level dossier exists**: a listing of today's
state-level "unknown" pages would spend the introduction (inference).

**Stage-0 outreach (SIG-CONTRIB-012 / 012a).** The facts are `code`; the offers are `inference`.
- `docs/build/reports/STAGE0_OUTREACH_RECORD.md` lists 19 projects, all with `date_sent` "—". The two peers SIG actually
  **mirrors**, Atlas and Eyes on Flock (`custody_posture = MIRROR`, `ingestion_permitted = true` in `sources.toml`), were
  ingested with no outreach. E1 owns that contradiction. C5 adds that the landscape now supplies a concrete opening
  offer for each project, as SIG-CONTRIB-012a asks:

  | project | concrete offer |
  |---|---|
  | Eyes on Flock | Jurisdiction attribution for its 1,528 portals, plus a returned diff: portal `total_cameras` vs OSM points vs Atlas. First fix SIG's own empty CC-BY-SA attribution for it (E1 :389; I1 :531). |
  | Atlas | An upstream "possible update" feed: Flock portals and vendors seen in Eyes on Flock or procurement data but absent from Atlas. Also ask for a Data Library listing. |
  | DeFlock | The plausibility checks the spec already names (§34.4, SIG-CONTRIB-012a text at spec :5376), and the dossier as the "brief printed summary" its council guide tells advocates to bring. |
  | alpr.watch | **Not in the compact, the registry or the spec.** Add it to the compact list before any connector (SIG-CHART-033). Exchange: SIG decision dates (once real) ↔ its agenda flags. |
  | ALPR Accountability Atlas (compact #8, `not_contacted`) | A crosswalk between its claim types and SIG's epistemic statuses. |
  | ACLU national and affiliates | Dossiers as the toolkit's "find out" step, once they are city-level. |

- **Registry and record inconsistency (`code`):** `sources.toml` has `deflock` `compact_status = "not_contacted"`, but
  STAGE0 row 2 records DeFlock as `public_terms_only`. This should be routed to E1 / F-rows.
- **New landscape entrants for the compact or the I-rows:** alpr.watch, Surveillance Watch, Georgetown CPT, S.T.O.P.,
  Lucy Parsons Labs and policefundingdatabase.org. `grep` finds 0 of these in `sources.toml`, except that "Lucy
  Parsons" and "brennan" each appear once in the spec.

---

## 7. Positioning implications (inference)

- **One-line position, derived from the matrix.** "Atlas tells you what an agency adopted. Eyes on Flock tells you what
  Flock's portal says. DeFlock shows where the cameras are. alpr.watch tells you when it is on an agenda. **SIG shows
  whether those agree, which document says what, what is still unknown, and when the next decision is, on one
  printable, citable page.**" Every clause after the bold one is a link, not a feature.
- **Design centre (local advocate).** The job is not a better map. It is **one golden dossier**: pick 1–3 places where at
  least four peers and official sources overlap. Seattle and Oakland qualify: CCOPS documents are ingested, Eyes on Flock
  portals likely exist (to be checked), and Atlas and OSM have records. Ship a city-level page that joins them, shows at
  least one real disagreement, states the decision date or says why it is unknown, and hands off to the action links.
  That single page demonstrates SIG-CHART-002 better than any number of state pages.
- **Investigative journalists.** Journalists already use Atlas CSVs, the ALPR Accountability Atlas source index and Eyes
  on Flock JSON. SIG wins only with claim-level provenance (L2 and the evidence viewer), stable ids, and
  cross-source contradictions they can report as findings ("the portal says X cameras; permits show Y"). Until the
  evidence viewer has entries, SIG is a secondary source to them.
- **Organizers.** Their comparative advantage is regional pattern: who shares with whom across agencies, and which
  contracts come up next quarter across a county. That needs **named** network nodes (C5-G6) and a populated renewal
  watch. The distribution channel already exists: DeFlock groups, ACLU affiliates and alpr.watch alerts.
- **SIG-CHART-001 check.** Until the joins surface, the live site's most substantial surface is a 232,625-site map
  [Q044]. By its own charter, that is the thing SIG must not be.

---

## 8. Open questions for C6 / D3

1. **Q-C5-1.** May SIG link to advocacy toolkits (DeFlock, ACLU) under SIG-UI-027b neutrality? Is a mixed "other public
   resources" block (official portals plus NGOs) acceptable? May it link to avoidance routing (ALPR Watch) under H12?
2. **Q-C5-2.** Which 1–3 places should get a golden, city-level joined dossier (Seattle, Oakland, or the Oklahoma
   pilot, which has no dossier per I1)?
3. **Q-C5-3.** Should Stage-0 outreach to the two mirrored peers (Atlas, Eyes on Flock) happen *before* the next
   publication that uses their data, given SIG-CONTRIB-012's ordering? This interacts with E1/E2.
4. **Q-C5-4.** Should alpr.watch be treated as a peer to link (A6) or as a source to ingest (agenda flags)? Either way,
   it enters the compact list first.

## 9. Limits

- **WebSearch was unavailable** (session budget exhausted, [Q020]), so peers came from the brief, SIG's registry and
  spec, and links found on fetched pages. Peers that only a search would surface may be missing.
- **Client-rendered sites were not read:** DeFlock's map, Surveillance Watch's graph, alpr.watch's counters and ALPR
  Accountability Atlas's counts. Their ratings rest on page text, repo source or meta descriptions, and cells are
  marked † or n/o where unread.
- **MuckRock, Brennan and Flock's hub were not characterised** (403/404).
- **WebFetch summaries are model-generated.** Load-bearing link claims (the ACLU toolkit's outbound hosts, SIG's
  absence from the hubs) were re-verified against raw HTML [Q058][Q059].
- **This is a desk scan, not a usability test.** The "10 min" statements are inference. C2/C3 own measured persona
  journeys.
