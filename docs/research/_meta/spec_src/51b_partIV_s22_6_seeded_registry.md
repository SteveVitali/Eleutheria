### 22.6 The seeded source registry

**SIG-INGEST-038 (MUST).** Phase 0 MUST seed the source registry with **every row below**. Each row
MUST receive a rights record, a custody posture, a `compact_status`, and an `ingestion_permitted`
flag. `Verified` records whether the lead research pass actually reached the URL on 2026-08-20;
**unverified rows MUST be verified during Phase 0 before any connector targets them.**

This section exists because a registry described in prose is not executable (SIG-ENG-001). Every
URL named in OL-21 appears here, plus every source added by research (§22.3).

#### A. Physical infrastructure

| Source | URL | Role | Verified |
|---|---|---|---|
| OSM surveillance tagging | `https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance` | Schema authority | — |
| OSM copyright / licence | `https://www.openstreetmap.org/copyright` | **ODbL authority** (§42.3) | ✅ |
| OSMF Licence Community Guidelines | `https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines` | Collective Database, Horizontal Layers, Substantial, Produced Work | ✅ |
| OSM taginfo API | `https://taginfo.openstreetmap.org/api/4/` | Tag statistics; vocabulary discovery | ✅ |
| OSM Overpass API | `https://overpass-api.de/api/interpreter` (+ mirrors) | Element extraction | — |
| OSM replication diffs | `https://planet.openstreetmap.org/replication/` | Incremental updates | — |
| OSM element history | `https://api.openstreetmap.org/api/0.6/node/<id>/history.json` | Per-element history (Q19) | — |
| OSM Automated Edits CoC | `https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct` | **Hard constraint on write-back** (R-14) | — |
| DeFlock | **`https://deflock.org/` — use this** (200, serves the app) · `https://deflock.me/` (403, Cloudflare challenge fires ahead of a 301 to `.org`) | Upstream field observation | ✅ |
| DeFlock — canonical repos | `https://github.com/FoggedLens/deflock` (MIT) · `https://github.com/FoggedLens/deflock-app` (AGPL-3.0) | The real code | ✅ |
| ~~`flockhopper3/deflock-data`~~ | Cited at OL-21-04. **Exists, but belongs to a different project** — it is not DeFlock's | Do not treat as DeFlock | ✅ |
| Surveillance under Surveillance | `https://sunders.uber.space/` | Peer OSM visualization; evidence of the international community | ✅ |
| PanoptiCity | `https://panopticity.fr/` | FOV/coverage analysis; downstream consumer of derived geometry | ✅ |
| Drivers Against Flock | `https://driversagainstflock.org/` | Downstream consumer; **do not compete** | ✅ |

#### B. Vendor / portal layer

| Source | URL | Role | Verified |
|---|---|---|---|
| Flock transparency portals | `https://transparency.flocksafety.com/` | First-party config/usage. **403 on all paths — no lawful automated access** | ✅ |
| Flock API & Integration Terms | `https://www.flocksafety.com/legal/api-integration-terms` | ToS constraint | — |
| Eyes on Flock | `https://eyesonflock.com/` | **Top Stage-0 dependency** (§22.5) | ✅ |
| Eyes on Flock description | `https://www.reddit.com/r/FlockSurveillance/comments/1ra26qw/` | Methodology context | — |
| Axon Community Connect | `https://axoncommunityconnect.com/communities/` | Private-camera federation scale | ✅ |
| Footnote4a | `https://footnote4a.org/news/transparency-portals` | Portal tracking; surfaced via HIBF | — |
| CA sharing visualization | `https://www.reddit.com/r/FlockSurveillance/comments/1slvs6a/` | Archival-design precedent | — |

#### C. Usage and audit layer

| Source | URL | Role | Verified |
|---|---|---|---|
| Have I Been Flocked | `https://haveibeenflocked.com/` | Specialist upstream for usage | ✅ |
| HIBF methodology hub | `https://haveibeenflocked.com/about` | Methodology | — |
| HIBF audit-log guide | `https://haveibeenflocked.com/about/audit-logs` | **Canonical audit field schemas** (F2.3) | ✅ |
| ALPR Watch | `https://alprwatch.org/` | FOIA normalization; routing; offline packages | ✅ |
| ALPR Watch Flock FOIA method | `https://alprwatch.org/news/2025-07-28_flock_foia/` | Pipeline reference | — |
| ALPR Watch code | `https://gitlab.com/alprwatch-org` | **GitLab, not GitHub** (C-02) | ✅ |
| ALPR Watch FOIA dashboard | `https://superset.alprwatch.org/superset/dashboard/columbia-river-gorge-foia/` | Worked analysis | ✅ |
| flock.ajith.fyi | `https://flock.ajith.fyi/` | Network-topology visualization precedent | ❌ |
| Monahan, "Grounding the Flock" (2026) | `https://journals.sagepub.com/doi/10.1177/20501579261453519` | Academic framing. **403 — `capture_status = paywalled`** (SC-07) | ✅ |

#### D. Adoption layer

| Source | URL | Role | Verified |
|---|---|---|---|
| EFF Atlas of Surveillance | `https://www.atlasofsurveillance.org/` | **Primary deployment seed**; `CC-BY-4.0` w/ third-party caveat | ✅ |
| Atlas methodology | `https://www.atlasofsurveillance.org/methodology` | Evidence standards; the "not a complete inventory" statement | — |
| Atlas about / scope boundary | `https://atlasofsurveillance.org/pages/about` | Delegates the device layer to DeFlock (SC-10) | ✅ |
| Atlas Data Library | `https://www.atlasofsurveillance.org/data-library` | **Index of specialist datasets** (§22.7) | — |
| EFF copyright | `https://www.eff.org/copyright` | Licence authority for Atlas | ✅ |
| EFF Street-Level Surveillance | `https://www.eff.org/issues/street-level-surveillance` | Second technology taxonomy for crosswalk (§20.3) | — |
| **EFF Data Driven (2018 release)** | `https://www.eff.org/deeplinks/2018/11/eff-and-muckrock-release-records-and-data-200-law-enforcement-agencies-automated` | **Vendor-neutral ALPR network source** (§23.10) | — |

#### E. Accountability layer

| Source | URL | Role | Verified |
|---|---|---|---|
| ALPR Accountability Atlas | `https://alpratlas.org/` | Incidents; **the epistemic-label model SIG adopts** | ✅ |
| ALPR Abuse Library | `https://library.kansas.watch/` | Curated source index; held **unnormalized** (SIG-EPIS-030) | ✅ |
| **ACLU Get the Flock Out toolkit** | `https://www.aclu.org/get-the-flock-out-toolkit` | **Defines the local-advocate requirements the dossier serves** (§39.0) | — |
| ACLU cell-site simulators | `https://www.aclu.org/issues/privacy-technology/surveillance-technologies/stingray-tracking-devices` | Agency possession dataset | — |
| WIRED ShotSpotter sensor leak | `https://www.wired.com/story/shotspotter-secret-sensor-locations-leak` | Acoustic sensors; **leak-provenance veto applies** (SIG-PUB-005) | — |
| Guardian, Flock cameras (2026-08-20) | `https://www.theguardian.com/us-news/2026/aug/20/flock-cameras-surveillance` | Vendor-replacement reporting | — |
| CourtListener / RECAP | `https://www.courtlistener.com/api/rest/v4/` | Litigation. **~5/min, 50/hr, 125/day — lookup only** | ✅ |

#### F. Records, procurement, evidence

| Source | URL | Notes | Verified |
|---|---|---|---|
| MuckRock | `https://www.muckrock.com/` | **api_v2**; 401 on all data endpoints; 5-min JWT; ~15/min | ✅ |
| DocumentCloud | `https://api.www.documentcloud.org/api/documents/search/` | Public search + full text | ✅ |
| USAspending | `https://api.usaspending.gov/` | Prime **and sub-awards** (grant→deployment tracing) | ✅ |
| SAM.gov | `https://api.sam.gov/` | Vendor identity. **Free key = 10 requests/day** | ✅ |
| GovSpend | `https://www.govspend.com/` | Commercial procurement aggregator cited by Atlas; **paywalled — LINK posture** | — |
| Sourcewell | `https://www.sourcewell-mn.gov/` | **Free full competitive record + monthly SKU price lists** | ✅ |
| OMNIA Partners | `https://www.omniapartners.com/` | Cooperative vehicle | — |
| NASPO ValuePoint | `https://www.naspovaluepoint.org/` | Cooperative vehicle | — |
| BuyBoard / TIPS / HGACBuy / Equalis | `https://www.buyboard.com/` · `https://www.tips-usa.com/` · `https://www.hgacbuy.org/` · `https://equalisgroup.org/` | Cooperative vehicles | — |
| Legistar InSite API | `https://webapi.legistar.com/v1/<client>/` | Matters, attachments, histories, events | ✅ |
| PrimeGov | `https://<tenant>.primegov.com/api/v2/PublicPortal/` | Meetings, agendas | ✅ |
| CivicClerk | `https://<tenant>.api.civicclerk.com/v1/Events` | Meetings + plaintext file stream | ✅ |
| NextRequest | `https://<tenant>.nextrequest.com/client/requests` | Published request logs + released docs | ✅ |
| GovQA / JustFOIA / FOIAXpress | vendor-hosted per agency | Records portals | — |
| OpenStates | `https://v3.openstates.org/` | State legislation. 403 without key | ✅ |
| FBI CDE agency registry | `https://api.usa.gov/crime/fbi/cde/agency/byStateAbbr/{ST}` | **ORI9 authority** | ✅ |
| LEAIC crosswalk | ICPSR study 35158 | ORI↔FIPS↔place. **Manual acquisition** | — |
| Census Gazetteer / TIGER | `https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html` · `https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html` | GEOID + boundaries | — |
| Census Geocoder | `https://geocoding.geo.census.gov/geocoder/` | Address→jurisdiction (keyless) | — |
| GLEIF | `https://www.gleif.org/en/lei-data/gleif-golden-copy` | LEI, CC0 | — |
| NCES / IPEDS / NTD / CMS | `https://nces.ed.gov/ccd/` · `https://nces.ed.gov/ipeds/` · `https://www.transit.dot.gov/ntd` · `https://data.cms.gov/` | Per-class identifiers (§14.2) | — |
| Wikidata SPARQL | `https://query.wikidata.org/sparql` | QID crosswalk; **83.4% of ALPR manufacturers** | — |
| Internet Archive Wayback | `https://archive.org/wayback/available` | Archival. **`*.flocksafety.com` is excluded** (C-12) | ✅ |
| DHS fusion centers | `https://www.dhs.gov/fusion-center-locations-and-contact-information` | 80 centers (54 primary + 26 recognized) | — |
| FAA drone waivers | `https://www.faa.gov/uas/` + EFF FOIA release | Dated `authorization_state` records | — |

#### G. Lead generation

| Source | URL | Role | Verified |
|---|---|---|---|
| Flock Finder | `https://github.com/simeononsecurity/flock-finder` | RF/OUI candidates. **`R6`, lead generation only** | — |
| Flock-You | `https://github.com/colonelpanichacks/flock-you` | Local RF detection. **Never auto-confirms** | — |
| WiGLE | `https://wigle.net/` | Underlying radio observations | — |

#### H. Community ecosystem

| Source | URL | Role | Verified |
|---|---|---|---|
| FlockReporter | `https://flockreporter.org/` | Local-group directory. **Did not respond** (C-03, R-12) | ✅ (failure) |
| Eyes Off Cedar Rapids | `https://eyesoffcr.org/` | Confirmed live local group | ✅ |
| r/FlockSurveillance | `https://www.reddit.com/r/FlockSurveillance/` | Ecosystem discovery. **Blanket `Disallow: /`** — manual reference only | — |

**SIG-INGEST-039 (MUST).** Phase 0 MUST seed the **local-group registry** (SIG-TASK-014) with the
following. These URLs were **recovered from the last surviving archive capture of the ecosystem
directory and then individually re-tested** on 2026-08-20 (SC-11); they are not the outline's bare
names. A `403` here means the site is alive behind bot protection, not that it is gone.

| Group | URL | Verified 2026-08-20 |
|---|---|---|
| ALPR Pictures | `https://alpr.pictures/` | alive (403) |
| DeFlock Atlanta | `https://deflockatlanta.org/` | **200** |
| DeFlock Birmingham | `https://deflockbhm.com/` | **200** |
| DeFlock Joplin | `https://deflockjoplin.today/` | alive (403) |
| DeFlock Lynnwood | `https://deflocklynnwood.com/` | **200** |
| DeFlock Olympia | `https://deflockoly.noblogs.org/` | **200** |
| DeFlock Redmond | `https://bsky.app/profile/deflock-redmond.bsky.social` | **200** (no own domain) |
| DeFlock Tucson | `https://deflocktucson.com/` | **200** |
| DeFlock Vegas | `https://www.deflock.vegas/` | **200** |
| Eyes Off Cedar Rapids | `https://eyesoffcr.org/` | alive (403) |
| Eyes Off Colorado | `https://www.eyesoffcolorado.org/` | **200** |
| Eyes Off Indiana | `https://eyesoffindiana.org/` | **200** |
| Live Free VA | `https://livefreeva.org/` | **200** |
| Community Discord | `https://discord.gg/m9VsbR6d5z` | listed in the directory |

**SIG-INGEST-039a (MUST).** Two groups the outline names — **DeFlock Idaho** and the **Monterey
Park organizers** — do **not** appear in the recovered directory and MUST be registered as
`status = unlocated`, not silently dropped. Their absence is itself a coverage fact.

**SIG-INGEST-039b (MUST).** **FlockReporter, the directory itself, is dead.** Its DNS ceased to
resolve between 2026-07-28 (its last and only archive capture) and 2026-08-20. It MUST be
registered with `disappeared_observed_at = 2026-08-20`, its recovered capture retained as evidence,
and a research task generated (§33.2 #8). Its community Matrix room was homeserver-bound to the
same domain and died with it.

**This is the worked justification for §46.5, not a hypothetical.** A single-maintainer ecosystem
project vanished *during the research window for this specification*, and the directory survived
only because a third party captured it **exactly once**. That one capture is the entire margin
between recovering the ecosystem's coordination layer and losing it. Every group it indexed is
still alive; only the index died. SIG's archival-succession offer (SIG-CONTRIB-013) exists for
precisely this failure mode, and the cost of not having made that offer is now measurable.

**SIG-INGEST-040 (MUST).** Phase 0 MUST also register the national partner organizations that are
consumers and contributors rather than data sources — at minimum EFF, ACLU and its state
affiliates, EPIC, the Brennan Center, STOP, Oakland Privacy, Lucy Parsons Labs, Stop LAPD Spying,
MediaJustice, and the Reporters Committee — with contact channels, so that outreach and
correction-routing have somewhere to go.

#### H2. Projects the outline does not name (discovered 2026-08-20)

**SIG-INGEST-048 (MUST).** These MUST be registered in Phase 0. Four were created after mid-2025,
which is why the outline does not have them — and which is itself evidence that this ecosystem's
membership turns over fast enough that the registry needs a **recurring discovery sweep**, not a
one-time census.

| Project | URL | Licence | Why it matters |
|---|---|---|---|
| `none-below/sm-alpr` | `https://github.com/none-below/sm-alpr` | **AGPL-3.0** | The most sophisticated portal archiver found: daily dated captures per slug, sharing-graph builder, records-audit importer, **rename detection**, scrape diffing. Prior art for §29.7 |
| `eyes-off/eugene-oregon` | `https://github.com/eyes-off/eugene-oregon` | **CC0-1.0** | Long-term archive of search-audit CSVs, built explicitly to defeat the 30-day rolling window |
| `resistanceisliberty/panopti.ca` | `https://panopti.ca/` | **MIT** | Canadian DeFlock fork; bilingual EN/FR; also maps government CCTV. **Extends the model beyond the US** — a live Stage-6 precedent |
| `mcclatchy-southeast/private_eyes` | `https://github.com/mcclatchy-southeast/private_eyes` | **MIT** | A newsroom dataset that **flags portal-vs-reality discrepancies** in a controlled column. Direct prior art for §29.1 |
| `simeononsecurity/flock-finder` | `https://github.com/simeononsecurity/flock-finder` | **MIT** | RF/OUI detection modality (already at OL-21-25); actively maintained |
| `flock.ajith.fyi` | `https://flock.ajith.fyi/` | **none stated** | **Do not ingest.** Publishes raw operator identifiers (§43.2a) |
| `Ringmast4r/FLOCK` | `https://ringmast4r.github.io/FLOCK` | **none** | Claims "336K+ cameras worldwide"; unmaintained since 2025-11 |

**SIG-INGEST-048a (RATIONALE).** The last row closes an open question. An uncorroborated
"336K ALPRs" figure circulates in secondary coverage; direct measurement finds **144,312**
`surveillance:type=ALPR` elements (SC-03). The likely origin is this project's own headline claim.
It is unmaintained, unlicensed, and its figure is not reproducible from OSM — so the figure MUST NOT
be repeated, and this row exists so that a future contributor who encounters it can see why.

**SIG-INGEST-048b (MUST).** Two of these are **licence hazards** and MUST be handled as such:
`none-below/sm-alpr` is **AGPL-3.0**, so its *code* MUST NOT be linked into SIG's Apache-2.0
codebase (its *methods* may be studied freely); and two projects state **no licence at all**, which
under SIG-LIC-004 means `UNDETERMINED` and a closed export gate, not implied permission.

#### H3. Government-mandated disclosure (CCOPS) — a source class of its own

**SIG-INGEST-049 (MUST).** Municipal surveillance-ordinance disclosures MUST be registered as their
own source class, `government_mandated_disclosure`, distinct from both `civil_society_dataset` and
`vendor_portal`: `licence: public record`, `format: pdf`, `extraction: document_pipeline`.

**SIG-INGEST-049a (MUST).** It MUST be scoped as **depth, not breadth** — and the honest numbers
must be carried with it, because the temptation to oversell this class is real. It covers roughly
**26 jurisdictions**: about **5% of the US population** and **0.14% of US law-enforcement agencies**.
It will never be a national picture. **Zero** jurisdictions publish machine-readable output; the
canonical national list of which cities have such ordinances is an image file on an advocacy page.
Vocabularies, cadences, and scopes differ per city; at least one city runs months past its statutory
deadline; at least one blocks automated access.

**SIG-INGEST-049b (MUST).** Against that, it supplies **exactly the dossier fields SIG cannot obtain
anywhere else**: named sharing partners, acquisition and operating cost *including vendor-provided
freebies*, retention, audit mechanisms, deployment locations, signage and visibility, effectiveness
claims, complaint counts, and **real usage counts**. Several regimes are genuinely current.

**SIG-INGEST-049c (SHOULD).** Implement **three** connectors that pay for themselves — the city with
quarterly reporting and the richest per-technology detail; the city publishing 42 policies on a
stable URL pattern; and the city with a biannual citywide inventory carrying a compliance metric —
and route the remainder through the legislative-platform scrapers already required for §39.5.

**SIG-INGEST-049d (MUST).** This class's **highest value is calibration, not coverage**, and the
spec should treat it that way. These jurisdictions are the only places where SIG can check its
inferred picture against a **legally compelled disclosure**, which makes them the natural evaluation
corpus for the reconciliation engine (§28) and for measuring device-attribution accuracy (§29.2).
Roughly 1% of the adoption layer's row count, with perhaps twenty times the fields per row.

**SIG-INGEST-049e (MUST).** These disclosures also surface a finding class available nowhere else:
**non-compliance**. One city's own biannual inventory recorded a substantial share of technologies
in use *without* the policy the ordinance requires. That is a first-class `AccountabilityEvent`, and
SIG MUST be able to represent "the operator's own mandated disclosure says it is out of compliance."

**SIG-INGEST-049f (MUST).** State ALPR statutes MUST be seeded from the one national inventory that
exists, and **labelled with its date**: it is HTML-only, covers 16 states, and has been **frozen
since 2022-02-03** — predating the entire recent expansion, and demonstrably missing at least one
state statute enacted since. It is a one-time seed, never a feed, and SIG must maintain it onward.

#### H4. Future recurring sources — mandated but not yet flowing

**SIG-INGEST-050 (MUST).** Statutory disclosure duties that have been **enacted but whose first
reports are not yet due** MUST be registered now, with their commencement date, rather than
discovered when they begin.

At least one state statute mandates public posting of **nine specified items whose fields map almost
exactly onto SIG's deployment schema**, with first reports due **2027-04-01**. That is a genuine
recurring, structured, statutorily-compelled source — the thing this domain almost never has (§22.3,
SIG-INGEST-025a) — and it arrives on a known date.

Registering it early costs nothing and buys three things: the connector can be specified against the
statute's field list before any data exists; SIG can record the *absence* of reports before the due
date as a lawful `not_applicable` coverage state rather than a gap; and non-compliance after the due
date becomes immediately detectable and is itself an `AccountabilityEvent` (SIG-INGEST-049e).

#### I. International

| Source | URL | Role | Verified |
|---|---|---|---|
| Technopolice | `https://technopolice.fr/` | FR/BE mapping; Stage 6 model | ✅ |
| Technopolice mapping discussion | `https://forum.technopolice.fr/topic/405/cartographier-la-surveillance` | The OSM-vs-own-database debate | — |
| Technocarte update | `https://technopolice.fr/blog/mise-a-jour-de-la-technocarte/` | Dataset state | — |
| La Quadrature du Net | `https://www.laquadrature.net/` | Publisher | — |
| `sous-surveillance.net` → OSM import | OSM import wiki | ~12,000 cameras; activist-DB→commons precedent | — |
| TED (EU tenders) | `https://ted.europa.eu/` | EU procurement | — |
| DECP (FR procurement) | `https://www.data.gouv.fr/` | National open procurement data | — |

### 22.7 The Data Library specialist-dataset backlog

**SIG-INGEST-041 (MUST).** The EFF Data Library index is the **Phase 17 ingestion backlog**, and its
entries MUST be registered in Phase 0 rather than discovered later. Each is `LINK` posture until its
rights are reviewed.

| Dataset | Technology it populates | Phase 17 priority |
|---|---|---|
| Vigilant / Data Driven ALPR data | ALPR (vendor-neutral, historical) | **1 — also Phase 12** |
| Who Has Your Face? | Face recognition; reference databases | 2 |
| Clearview AI usage table (BuzzFeed) | Face recognition | 2 |
| Cell-site simulator datasets (ACLU) | `comms-intercept` | 3 |
| Upturn *Mass Extraction* | `device-forensics` | 4 |
| Public-safety drone datasets | `robotics-aerial` | 6 |
| Ring / Neighbors historical partnerships | Private-camera request. **Category retired 2024 — absence ≠ program ended** (SIG-ONTO-059) | 1 |
| California ALPR survey data (CA DOJ / SB 34) | ALPR; state reporting mandates | 1 |
| Federally funded body cameras | **Body-worn video** (§13.1) | 5 |
| Wiretap reports | `comms-intercept` | 3 |
| Aaron Swartz Day Police Surveillance Project | Multi | 7 |
| Electronic monitoring (MediaJustice) | `person-monitoring` | 7 |
| Atlas Border Communities | ALPR (checkpoint/covert) | 1 |
| AI Global Surveillance Index (Carnegie) | Country-level; **coarse granularity** (OL-5.3-02) | 8 |
| Facial Recognition World Map | Country-level | 8 |
| Mapping China's Tech Giants (ASPI) | Vendor-level, international | 8 |

**SIG-INGEST-042 (MUST).** Country-level datasets MUST be ingested as claims with **explicit coarse
granularity**, never disaggregated to agency level by inference (OL-5.3-02).

---
