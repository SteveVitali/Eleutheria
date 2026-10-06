# K3 — Knowledge-graph search (operator ask U-003.3)

- **Row:** K3 (Stream K, design) · **Written:** 2026-09-30, work window 22:09:14Z–22:30:45Z (`date -u`; stamps in §15).
- **Worktree HEAD at write time:** `b6b3d970` (branch `claude/next-phase-planning`). `git diff --stat b051732c HEAD -- exports
  api web/src connectors/src ontology/vocab docs/2_canonical_design_spec.md` is empty, so every `code` citation is also a
  chain-tip citation.
- **Operator ask (U-003.3, verbatim):** *"the search functionality at "/search" is extremely crude and naive, and ideally a
  user would be able to search in a much more flexible way across the whole knowledge graph, of course we don't have to boil
  the ocean for the first pass, but we can definitely improve over what we have"*. Also U-005 (journalists must "really truly
  explore the knowledge graph … querying/exploring the data interactively, always with full explicit transparent
  evidence/lineage") and U-008 (≤ $300/month without an explicit go).
- **Binding input:** `design/K0-interactive-architecture.md` — `/search/` is a **T2** surface (≤ 60 KiB gzip initial JS,
  ≤ 40 KiB after an action, ≤ 50 KiB per keystroke shard, ≤ 40 KiB per result page, LCP ≤ 1.5 s, CLS ≤ 0.02, TBT ≤ 100 ms,
  keystroke → suggestions ≤ 100 ms at 4× CPU throttle); "one GET form → the release-pinned API FTS5 … plus static
  per-compartment typeahead shards"; MiniSearch 7.x (5.9 KB); no-JS GET form → server-rendered results; URL state
  `sig.workspace-state/2`; I-10 (release-pinned data only; live-spine `/v1/*` is never a public page's data source).
- **Inputs read:** META_PLAN §3, the K3 row, §8.2; K0 (whole); `research/K12a-prior-art.md` §0, §1, §2.4, §4, §8, §9;
  `review/JOURNEYS.md` (P1, P2, P6, P7 and the persona list); `review/K12b-explorability.md` §1, §3.2, §4 (`/search/`),
  §5; `review/R10_PREVIEW.md` §3.4–§3.6, §8 (DR-C4-*), §9; `design/K4-dossier-index.md` §0, §3.1, §5.4, §6, §7, §9;
  `design/G3-release-model.md` §0, §4, §6.4, §11; hooks in `design/J3-transparency-design.md` (§ sources table),
  `K10-source-pages.md` (§13), `K8`, `K11`; `research/G1-ops.md` line 73 (service sizes); `findings/FINDINGS.csv` and every
  `findings/incoming/*.csv` (dedup); spec SIG-UI-040, SIG-FIND-003/004, SIG-IDENT-024, SIG-UI-049. Code:
  `exports/src/exports/search_index.py`, `release.py:420-520`, `release_pages.py:531-660`, `api/src/api/release_search.py`,
  `api/src/api/routes.py:278-335`, `api/src/api/store_pg.py:195-245, 878-925`, `web/src/pages/search.astro`,
  `web/src/islands/SearchIsland.tsx`, `connectors/src/connectors/data/{sources,camera_registry_targets}.toml`,
  `ontology/vocab/technology.yaml`. **`design/K2-graph-and-entities.md` did not exist at write time** (K2 in progress);
  §13 lists what K3 needs from it.
- **Evidence classes (P1):** `code` (file:line at `b6b3d970`); `recorded-execution` (a local prototype over the live
  release's parquet, hashed by C3 — no production request was made by this row); `live-read` only as cited from C2/K12b/C4;
  `inference` is labelled. Relevance judgements in §9 are **agent-written expectations, not human relevance labels** (P4).
- **P3/P14/P16:** production was not touched. The prototype ran on C3's hashed bucket capture
  (`docs/build/logs/next-phase/C3/bucket/`) and L2's public-domain Natural Earth files; `minisearch@7.2.0` was installed into
  the gitignored `docs/build/logs/next-phase/K3/node/` with `npm install --userconfig=/dev/null --ignore-scripts` (no identity
  sent). No secrets appear here.
- **Status vocabulary (P5):** nothing here is engineered. The prototype is a measurement instrument, not code for the build.
- **Writes:** this file and `findings/incoming/K3.csv` only. Prototype artefacts (gitignored) are under
  `docs/build/logs/next-phase/K3/` with `SHA256SUMS`.

---

## 0. The decision on one page

**First pass (Round 11):** one search box that searches **the whole published release** — every record in all 12 licence
compartments — **plus a catalog of named things**: places (countries and first-level subdivisions now; US counties and
places when K4's registry lands), the 178 sources by name, the 153 technology concepts of SIG's vocabulary, the organizations
the release names (and every K2 agency/vendor entity as it lands) and the 255 evidence documents. Results are **typed cards**
that link to the dossier, source, entity, evidence or record page and show **why they matched and what evidence stands behind
them**. A query that names a place resolves to the place first ("Canberra" → Australian Capital Territory, 1,328 records).
Acronyms are aliases, not substrings ("ICE" → *U.S. Immigration and Customs Enforcement*, with an honest "SIG's release names
no record for it" and the 98 word-matches for "ice" collapsed underneath). Typos get a "did you mean". Facets: result type,
licence group, jurisdiction, source, location (technology and dates when their data exists). It works as a plain GET form with
JavaScript off; with JavaScript, a header typeahead suggests places, sources, technologies and organizations.
**Later:** claim-text search, contracts and policies as typed entities (K7/K2), research tasks (K11), entity-scoped search,
result export, date facets (K5), US cities before K4, semantic search. None of these block the first pass.

**Architecture (K0-conformant): "release search v2" — a federated, release-pinned SQLite FTS5 service plus static catalog
typeahead shards.** No hosted engine, no Pagefind, no client-side SQLite, no live-spine reads.

| measured on the live release (232,625 records), Apple M3 Pro, warm cache | landed P32.14 index | **v2 prototype** |
|---|---|---|
| Index bytes, all 12 compartments | **488.6 MB** (osm_physical 301 MB) | **77.0 MB** (records 72.3 MB + catalog 4.7 MB); + ≈ 22 MB for a compact claim-id table = **≈ 99 MB** |
| Build time (excluding parquet reads) | ≈ 6.7 s | ≈ 1.8 s |
| Federated query over 12 compartments (+ catalog), 40 queries | p50 1.8 ms · p95 2.8 ms · max 15.2 ms | p50 1.45 ms · p95 10.1 ms · max 64.2 ms (a 154,528-row source match) |
| Benchmark: expected answer in top 3 (30 answerable queries) | **6 / 30** | **30 / 30** on the development set (tuned on it; §9 requires a held-out set) |
| Benchmark: no misleading top hit (10 queries the release cannot answer) | 10 / 10 (by returning nothing) | 10 / 10 |
| Typeahead shards (catalog only, word-start sharding) | — | 921 shards, **815 KB gzip total**, median 275 B, p95 3.4 KB, max 20 KB; MiniSearch build + query on the largest shard **3.4 ms** (≈ 14 ms at 4× throttle, inference) |

**Cost (inference from G1/K0 unit prices):** ≈ **$3–5/month** incremental (raising `sig-api` from 512 MiB to 1 GiB so verified
index copies live on local disk; queries ≈ $1 per million; shards and index storage ≈ cents). A hard worst case under sustained
abuse with `max-instances 2` is ≈ $140/month — inside U-008 but above K0's $50 revisit trigger, so rate limiting and a cost
alert are part of the first pass.

**Matching and ranking:** a six-stage pipeline — exact identifier → alias (case-sensitive acronyms) → exact place/catalog
name → weighted catalog FTS → weighted record FTS per compartment → spelling suggestion — with a **tier** per result that is
comparable across compartments (identifier > exact name/alias > phrase in name > all words in name > words in other fields >
suggestion) and bm25 (field weights name 10 · alternates 6 · place 2 · source 1) only *within* a tier. Places with records
outrank homonyms without (Maryland, US before Maryland, Liberia). Order is **match quality, never importance or truth**.

**Benchmark:** 40 persona-derived queries (§9), 30 judged on top-3 and 10 on "no misleading top hit", plus a required
held-out set of ≥ 40 written before implementation by someone other than the implementer.

**Tickets (§10): SRCH-01 … SRCH-08** — index v2 builder (M) → query engine v2 + benchmark harness (M) → API serving v2 (M)
→ no-JS results page (M) → typeahead + `/search/` rewrite (M) → scoped search on dossier/source pages (S) → acceptance +
activation (S, live) → result export (S, later wave). Depends on K2 (label rule, entities), K4 (JUR-01 registry, `lookup@1`),
G3 (REL-01 descriptor v2, REL-05 API parity), G2 ACT-17 (production wiring, F-155), K0 UXK0-1/2/4/5/6.

**New findings (§14):** 7 (0 S0, 0 S1, 6 S2, 1 S3). The two that matter most: the landed P32.14 index sorts every result
list **alphabetically, empty labels first** (osm_physical needs 3,089 pages before its first named record), and on the real
release it is **488.6 MB** and read **whole into memory** for verification on a **512 MiB** service.

---

## 1. Ground truth: what exists today

| surface | what it does | evidence |
|---|---|---|
| **Live `/search/`** | A React island (`client:only`) filters a 733-item list serialized into the page: 55 dossiers, **the first 500 of 232,625 sites** (Iowa first) and 178 source keys. Case-insensitive substring over label + sublabel. Site hits link to `/map/`, source hits to `/data-freshness/`. "Canberra" → 0; "ICE" → an Iowa rest-area camera "near Joice" and a UK police source key; "Vigilant", "Austin Police", "ALPR" → 0 | `web/src/pages/search.astro:55-75,140`, `SearchIsland.tsx:84-92` (`code`); C2 P6-T1, K12b §4, F-101, K12b NEW-10 (`live-read`) |
| **P32.14 release search** (landed, ADR-133, **not deployed**, F-155) | One deterministic SQLite FTS5 (`unicode61`) index per licence compartment over label, entity id, source id and jurisdiction; `identifiers` (entity id, record key, every claim id); `facets` (kind, jurisdiction, source, location, technology). Tokens are ANDed; results are ordered by `(label_sort, entity_type, entity_id)` — **alphabetical, not ranked**; 2-letter queries resolve only through the jurisdiction facet; one compartment per request; no aliases, places, stemming or fuzziness; 2 s deadline; ≤ 50 rows; ≤ 100 KiB | `exports/src/exports/search_index.py:83-121` (DDL), `:123` (`_KEYSET_ORDER`), `:517-694` (`search`); `api/src/api/release_search.py` |
| **Live-spine `/v1/search`** | `entity_identifier.value ILIKE '%q%'`, ordered by `entity_id` (UUID time order), labels from `organization.cached_canonical_name` or the first identifier. Finds "Vigilant Solutions (LEARN)" and "data_driven:agency:Austin Police Department" — but it reads the **live spine**, which G3 labels "not a citation" and K0 I-10 forbids as a public page's data source; searching an entity's own UUID returns 0 | `api/src/api/store_pg.py:201-214, 878-925`, `routes.py:282-333` (`code`); K12b's captured `api__v1_search_q_*.json` (`live-read`, 21:34Z) |
| **What the release holds** (the corpus a release-pinned search can index) | 232,625 records, **all `entity_type = deployment`**; 192,536 (82.8%) with an empty label (K0 NEW-1); **no agency, vendor or organization records** — the only named organization is the `partner_ref` string "Vigilant Solutions (LEARN)" on 130 rows of `sharing_edges.csv`; 178 source ids, **every one** with a human name in `sources.toml` (e.g. `camreg_austin_tx` → "Austin traffic cameras (Socrata open-data registry)"); 255 evidence artifacts whose titles are their UUIDs; 55 jurisdiction codes in four schemes (K4); no technology field on any record (F-325) | duckdb over C3's capture, 22:11:44Z (`recorded-execution`); `sources.toml` (`code`) |
| **Service envelope** | `sig-api` 1 vCPU / **512 MiB**, min 1, max 2 | G1-ops line 73 |

**What this means.** Deploying P32.14 as-is (G2 ACT-17) would already turn C2's "Canberra → 0" into 50 address hits — but
as an alphabetical list of Canberra street addresses, not as "Canberra is in the Australian Capital Territory; here is its
dossier". It would still answer "ICE" with ice rinks and "Maryland" with Winnipeg intersections (§2.2), and it would ask the
reader to choose one of 12 licence compartments before searching. The fix is not a new engine; it is ranking, a catalog of
named things, place resolution, aliases and federation — on the engine SIG already has.

---

## 2. Measurements (prototype, `recorded-execution`)

All figures come from scripts in `docs/build/logs/next-phase/K3/tools/` run between 22:13:47Z and 22:23:17Z over C3's
sha256-verified capture of release `sig-2026-09-27-ce480ab1` (`parquet/*.parquet`; e.g. `osm_physical.parquet`
`860845d7e093…`, `public_record.parquet` `a3d631cff8ab…`). Machine: Apple M3 Pro, 36 GiB, SQLite 3.53.1, Python 3.12, Node
25.2.1. Warm OS cache; **Cloud Run on 1 vCPU and a gcsfuse mount will be slower** — SRCH-07 measures on staging.

### 2.1 The landed P32.14 index on the real release (`a_baseline.py`, the landed `build_search_index` called unchanged)

| compartment | records | index bytes | | compartment | records | index bytes |
|---|---:|---:|---|---|---:|---:|
| osm_physical | 154,705 | 301,428,736 | | sig_graph | 4,834 | 12,595,200 |
| public_record | 39,921 | 88,072,192 | | dot511_ccbysa2 | 3,000 | 11,407,360 |
| operator_accepted | 21,682 | 50,864,128 | | ogl_uk3 | 1,514 | 3,563,520 |
| portal | 5,685 | 17,678,336 | | ccby3 · ogc_canada2 · ottawa_odl2 · stalbert_odl1 · peel_odl1 | 1,284 | 2,952,192 |
| **total** | **232,625** | **488,562,688** | | | | |

Where the bytes go (osm_physical, `dbstat`): `identifiers` 88.8 MB (773,747 rows: entity id + record key + 3.0 claim ids per
record, all as text), `facets` 61.2 MB, `records` 45.4 MB, six covering indexes 68.4 MB plus the unique record-key index
12.4 MB, and **the FTS tables themselves 25.2 MB**. K0's 37.7 MB figure (an FTS5 table over four columns) did not include the
identifier, facet and covering-index tables of the landed layout, which is 13× larger (inference from the two measurements). `ReleaseSearchStore._verify` reads
each file whole (`release_search.py:120`, `data = path.read_bytes()`) — 301 MB for osm_physical on a 512 MiB service (NEW-2).

### 2.2 P32.14 behaviour on 40 persona queries, federated over 12 compartments (`a_bench.py`)

| query | first-page hits | what comes first | verdict |
|---|---:|---|---|
| Canberra | 50 (sig_graph) | "109 Canberra Ave, Griffith ACT 2603" — addresses, alphabetical | hits, but no place |
| Austin | 55 | "1 BLK S PLEASANT VALLEY RD (KREIG FIELD)" | no place, no agency, no source card |
| Texas | 22 | "2731 BLK S CAPITAL OF TEXAS HWY NB" | a highway name, not the state |
| TX | 100 + **10 × 422** `query_too_short` | Austin street addresses | 10 of 12 compartments error (NEW-5) |
| Maryland | 11 | Winnipeg "Cornish & Maryland", "Maryland & Sargent" | street names, not the state (NEW-3) |
| Georgia | 60 | Vancouver "Beatty St and W Georgia St" | street names (NEW-3) |
| Idaho | 13 | "I-5 @ MP 119.7: Idaho Ave" (Washington) | street names (NEW-3) |
| Oklahoma | 2 | DC "Benning Rd and Oklahoma Ave NE" | street names (NEW-3) |
| **ICE** | 4 | "Nottingham Ice Stadium", "Dundonald International Ice Bowl" | exact tokens still mislead (NEW-3) |
| Winnipeg | 50 | an **unlabelled** record first | empty labels sort first (NEW-1) |
| ALPR · license plate reader · Vigilant · LEARN · Flock Safety · Motorola · Austin Police · Canbera · Vigilent · Austn · data.act.gov.au · DeFlock · news article · agenda · red light camera · Oklahoma City · Kansas City | **0** each | — | no catalog, no aliases, no fuzziness, source names not indexed |
| camreg_austin_tx | 50 | Austin records, alphabetical | no source card |
| Cavalier & Portage · Northbourne Avenue · police station · a site UUID | 1 · 3 · 4 · 1 | correct | label and id lookups work |

Unfiltered browse (`a_order2.py`, 22:23:15Z): the first 50 rows are unlabelled in **every** large compartment; osm_physical
has 154,483 unlabelled records before its first named one (**3,089 pages**), public_record 396 pages, operator_accepted 257.
The `technology` facet has **0 rows** in every compartment and `kind` has one value (NEW-4).

### 2.3 The v2 prototype (`b_build_v2.py`, `c_query_v2.py`)

**Layout.** (a) One **catalog** index: 4,911 documents — 4,324 places (Natural Earth admin-0 + admin-1 with alternate names,
ISO and postal codes; the 55 SIG jurisdictions mapped onto them with record counts and dossier links), 178 sources (registry
name, id, homepage, agency, record count, compartments), 153 technology concepts (labels, slugs and `evidence_signature`
synonyms from `technology.yaml`; one duplicate slug skipped, the F-228 collision), 1 organization (the release's only named
one), 255 evidence documents (type + source name, since titles are UUIDs), plus an alias table. Weighted FTS5 (`porter
unicode61 remove_diacritics 2`, prefix 2/3), a trigram table over names and alternates, and an exact-name table.
(b) One compact **record** index per compartment: a contentless weighted FTS5 over name (the published label only), place
(jurisdiction name + country + code) and source (registry name + id); display name = label, or a *marked* derived name
("Camera site · Austin traffic cameras (Socrata open-data registry)") until K2's rule exists; entity id; two filter indexes.

| file | bytes | | file | bytes |
|---|---:|---|---|---:|
| catalog | 4,698,112 | | sig_graph | 1,462,272 |
| osm_physical | 49,745,920 | | dot511_ccbysa2 | 942,080 |
| public_record | 11,575,296 | | ogl_uk3 | 479,232 |
| operator_accepted | 5,939,200 | | 5 small compartments | 355,328 |
| portal | 1,605,632 | | **total** | **77,025,280** |

A compact claim-id → record table (`claim BLOB(16)` primary key, `WITHOUT ROWID`) measured **25.0 bytes per claim** on
osm_physical (464,337 anchors → 11.6 MB); the release has 891,661 claim anchors → **≈ 22 MB** (inference, linear). That keeps
SIG-FIND-003's exact claim-id lookup at ≈ 1/4 of P32.14's text `identifiers` table.

**Benchmark (§9):** 30/30 top-3 and 10/10 honest on the development set; p50 1.45 ms, p95 10.1 ms, max 64.2 ms ("DeFlock":
its source name matches 154,528 records). Spelling suggestions fired on 3 queries (Canbera → canberra, Austn → austin, Marylnd
→ maryland); aliases on 3 (ICE, ALPR, LEARN). **Two honest caveats:** "Canberra" resolves only because Natural Earth happens to
carry `woe_name = "Canberra"` for AU-ACT — production needs a city layer (§4.3); "Vigilent" matched through Porter stemming
("vigil"), not through fuzziness.

Facet cost (`g_facets.txt`): counting a 154,528-row match 2.7 ms; grouping it by jurisdiction 37 ms; top-10 by bm25 61 ms;
a 3,996-row place filter grouped by source 0.4 ms. Broad source- or place-name matches are therefore answered as a **card
plus a filter** ("154,528 records from this source"), not by ranking every row (§4.2 stage 5).

### 2.4 Typeahead shards (`e_typeahead.py`, `node/bench.mjs`)

Word-start sharding (the first two characters of every word of the name and alternates, so "police" finds "Austin Police
Department"); a shard over 24 KB gzip splits to three characters.

| suggestion set | entries | shards | gzip total | median | p95 | max (shard) | MiniSearch parse + build + query on the max shard |
|---|---:|---:|---:|---:|---:|---:|---|
| **A — catalog only** (places, sources, technologies, organizations) | 4,656 | 921 | 815,840 | 275 | 3,383 | 20,198 (`de`) | 0.55 + 3.12 + 0.30 ms |
| B — A + all 40,089 labelled records | 44,745 | 2,269 | 7,118,565 | 488 | 14,404 | **338,659** (`at_`) | 3.43 + 38.44 + 6.74 ms |
| C — A + a synthetic 12,000 US places/counties + 7,800 agencies (K4/K2 growth; names synthetic) | 24,456 | 1,023 | 1,292,280 | 268 | 4,525 | 42,802 (`cou`) | 1.75 + 8.81 + 2.61 ms |

Inside a shard, MiniSearch's fuzzy match found "canbera" → Australian Capital Territory and "vigilent" → Vigilant Solutions
(LEARN). **Records do not belong in the typeahead**: set B breaks the ≤ 50 KiB-per-keystroke budget sevenfold and would cost
≈ 190 ms per keystroke at 4× throttle (inference). Records are found by the full search. Sets A and C fit with room to spare.

---

## 3. Scope: what is searchable, first pass vs later

| result type | source of the data | first pass? | link target | dependency |
|---|---|---|---|---|
| **Place** (country, state/province) | K4 jurisdiction registry (Natural Earth 10m in the interim) + SIG record counts | **yes** | the dossier (`/dossier/usa/tx/`, today `/dossier/tx/`); places without a dossier → "records in X" search | K4 JUR-01 for canonical keys; interim NE mapping works today |
| Place (US county/city) | K4 registry (Census Gazetteer 2025; 2,482 counties and 9,382 places hold records) | **when JUR-01 lands** | county/place dossier (JUR-03) | K4 JUR-01/JUR-03 |
| Place (non-US city: "Canberra", "Winnipeg", "Glasgow") | a city layer: Natural Earth populated places (public domain) first; GeoNames `cities15000` (CC BY 4.0) optional | **yes** (NE) | the containing subdivision's dossier, with "Canberra is in the Australian Capital Territory" | D-K3-3; K4 `lookup@1` |
| **Source** | `sources.toml` names (all 178 release sources have one) + K9 facet fields (class, geography, publisher type, licence, lane, status) | **yes** | `/sources/<id>/` (K10); until it exists, the `/data-freshness/` row anchor | K9/K10 for the page |
| **Technology concept** | `ontology/vocab/technology.yaml` (153 concepts, synonyms in `evidence_signature`) | **yes** | search filtered by `technology=<slug>` + a definition | records carry no technology yet (F-325): the card says so |
| **Organization / agency / vendor** | K2 entity export (today the release names one organization) | **yes, as K2 publishes them** | `/entity/<type>/<id>/` (K2) | K2 (hard dependency for the journalist queries) |
| **Evidence document** | release `evidence.json` (255 artifacts) → K8 titles | **yes** | `/evidence/<artifact>/` (K8) | K8 for readable titles and pages |
| **Record (site)** | every published record, all 12 compartments | **yes** | the latest-view entity page (K2) or the release record `/r/<pub>/c/<comp>/entity/<type>/<id>/` | K2 derived labels; REL-09 for `/r/` |
| Dossier and content pages (methodology, about, releases) | titles + headings at build time, as catalog docs of type `page` | **yes** (small) | the page | — (replaces a Pagefind index; §5.7) |
| Claim text ("retention 30 days", "renewal 2027") | claim predicate + value per compartment | **later** (SRCH-09) | the record page, anchored at the claim | size unmeasured: ≈ 240 MB for 2.4 M claims at ~100 B each (inference) |
| Contracts, policies, agenda items, bills | K7 watch items / K2 entity types | later | watch item / entity page | K7, K2 |
| Research tasks ("what SIG does not know about Austin") | K11 task export | later | `/task/<id>/` | K11 RQ-01 |
| Relationships and paths ("who can access Austin's data") | K2 access-path closures | later (graph explorer answers first) | `/explore/` | K2 |

**Not in scope ever (Part VIII):** plate-, person- or officer-level data (SIG-PUB-010, §18.1). The index builder reads only the
bound release projection — the same eligibility selector as every export — so nothing unpublished can become searchable.

---

## 4. Matching and ranking

### 4.1 Principles

1. **Say why.** Every result carries its match reason (identifier · alias "ICE" · place name · name phrase · all words in name
   · words in place/source · did-you-mean) in the card and in JSON (`matched`).
2. **Order by match quality, never by importance or truth.** No popularity, no "confidence" boost, no evidence-count boost.
   Support is *shown* on each card (§6.3), never used to rank. (The landed HTML already says "page order is not a relevance
   score or a probability of truth"; v2 keeps the second half and replaces the first with "ordered by how well the words
   match".)
3. **Places first, then names, then text.** A reader who types a place wants the place.
4. **Acronyms are exact and case-sensitive.** "ICE" is an alias; "ice" is a word. An alias expands meaning; it never asserts
   a relationship.
5. **No silent rewriting.** Suggestions are shown as "Showing results for *canberra*; search instead for *canbera*".
6. **Deterministic per release.** Same release + same query → same bytes (cacheable, citable).

### 4.2 The pipeline (prototype-verified; SRCH-02 specifies it)

| stage | rule | tier |
|---|---|---|
| 1 identifier | a UUID, record key, source id (`camreg_austin_tx`) or claim id → the exact thing; stop | 0 |
| 2 alias | case-sensitive table for acronyms (ICE, CBP, DHS, FBI, HSI, LEARN, RTCC); case-insensitive for technical terms (ALPR, LPR, ANPR, CCTV). An alias card states the expansion and its cited source; if the target is a SIG entity, that entity follows; otherwise "SIG's release names no record for this". Word-hits of the same letters are **collapsed** ("98 records contain the word *ice* — not ICE the agency · show them") | 1 |
| 3 exact name | normalized query = a catalog name or alternate (place names, ISO/postal codes, source names, technology labels and synonyms, entity names/aliases). Place homonyms are ordered by **SIG records held** (Maryland, United States 2,753 records before Maryland, Liberia 0), then level; all are shown with their parent ("Georgia — country" and "Georgia — US state") | 1 |
| 4 catalog text | weighted FTS: bm25(name 10, alternates 6, context 1) × a small type prior (place > organization > technology = source > document) | 2 |
| 5 records | per compartment: if stage 3 resolved a place (or a source) and the query is only that name, records come as a **filter** ("1,328 records in Australian Capital Territory" → a link), not as text hits; otherwise weighted FTS bm25(name 10, place 2, source 1). Each hit gets a comparable tier: phrase in name (2) · all words in name (3) · words only in place/source (4) | 2–4 |
| 6 suggestion | only when stages 1–5 find nothing strong: per word, the most frequent vocabulary term within edit distance 1 (≤ 8 letters) or 2 (longer), sharing a first or last letter; kept **only if** the corrected query finds strong results | 5 |

**Across compartments** bm25 scores are not comparable (IDF differs per index), so results merge by **tier**, and bm25
orders only within a tier and compartment. Records are presented in **licence groups** (§5.3), each ordered on its own.

**Tokenization.** `porter unicode61 remove_diacritics 2` for names and text ("cameras" = "camera", "Montréal" = "montreal").
The live tokenizer splits `camreg_austin_tx` into three words, so source ids are also matched as identifiers (stage 1). No
stop-word removal in matching; function words ("at", "de", "&") are excluded only from typeahead shard keys (the largest
shards in §2.4 were `de` and `at_`).

**Typo tolerance.** Server: stage 6 plus a trigram table over catalog names for substring fallbacks. Client: MiniSearch
`fuzzy: 0.2, prefix: true` inside a shard. **SIG-IDENT-024 applies:** trigram or edit-distance similarity may suggest; it
never merges, resolves or scores identity.

### 4.3 Place resolution

- **Contract:** K4's `jurisdiction.lookup(name, level=None, within=None) → [candidate{jkey, name, level, score, basis}]`
  (`lookup@1`), applied to the whole query and to "X, Y" forms ("Springfield, IL"). Ambiguity returns several candidates;
  search shows them all, never guesses.
- **Names:** registry official names + alternates (Census Gazetteer, Natural Earth `name_*`/`name_alt`, ISO names, USPS
  codes). **Cities outside the US:** Natural Earth populated places (public domain) in the first pass; a city card says "X is in
  <subdivision>" and links that dossier, with the city's own dossier once one exists.
- **A place card is not a claim about the place.** It says what SIG's release holds there: "1,328 records from 1 source,
  release sig-2026-09-27 (as of 2026-09-27)". The "not yet placed" bucket (K4 §5.5) is never a place facet value.
- **Addresses and ZIP codes:** not in the first pass (K4 JUR-07; no query logging, no third-party geocoder, K0 I-6).

### 4.4 Aliases: governance

Aliases are **data rows** (`exports/data/search_aliases.toml`, reviewed like registry rows): `key`, `case_sensitive`,
`expansion`, `target` (a SIG id or none), `source_url` for the expansion (e.g. the agency's own site), `added_by`, `reviewed_on`.
Rules: only abbreviations and official alternate names; never a characterization ("ICE" → the agency's name, not "deportation
agency"); never a vendor's marketing term as a technology; every alias is visible in the card that uses it. Registry
alternates (K4), vocabulary synonyms (`evidence_signature`) and K2 entity aliases (identifiers, former names, Wikidata labels)
feed the same table automatically.

---

## 5. Architecture (K0-conformant)

### 5.1 Components

```
 release build (sig-exports release build, once per release; deterministic)
   ├─ r/<pub>/c/<comp>/search_index.sqlite      v2 compact record index (licence = the compartment's)      ≈ 72 MB total
   ├─ r/<pub>/c/<comp>/claim_ref.sqlite          claim id → record (exact-id lookup, SIG-FIND-003)          ≈ 22 MB total
   ├─ releases/<pub>/search/catalog.sqlite       places · sources · technologies · entities · documents · pages · aliases ≈ 5 MB
   ├─ releases/<pub>/search/shards/<xx>.json     typeahead shards (catalog only)                            ≈ 0.8 MB gzip
   └─ all in sig.release-integrity/1; search_index_version = release-search-index/2 in descriptor v2 (G3 §3.2)
 sig-api (release-backed route, G3 §6.4)
   GET /v1/releases/{pub|latest}/search?q=&type=&jurisdiction=&technology=&source=&collection=&location=&within=&cursor=&format=html|json
   GET /v1/releases/{pub}/compartments/{c}/search      (kept: v1 contract, compatibility)
 site
   /search/  (T2)  GET form → the API route; Preact app ≤ 60 KiB enhances it (instant facets, combobox)
   header    (T1)  <sig-typeahead> ≤ 20 KiB (MiniSearch 5.9 KB + element) over static shards; Enter submits the form
```

### 5.2 Why this shape (and not the alternatives)

| option | verdict | reason (evidence) |
|---|---|---|
| **Extend the landed per-compartment FTS5 (v2) behind the release-pinned API + static catalog shards** | **adopt** | meets relevance on the development set (§2.3), sub-100 ms warm, ≈ $3–5/month, reuses ADR-133's integrity, withdrawal and cursor machinery; K0-conformant |
| Keep P32.14 unchanged and just deploy it (G2 ACT-17) | reject as the end state; **do deploy it first** if SRCH-01…03 slip | 6/30 on the benchmark; alphabetical; 488.6 MB; 12-form UX; but better than the 500-row sample |
| Expose the live-spine `/v1/search` to the site (K12b's first-pass idea, F-23) | reject | K0 I-10 and G3 REL-05: public pages never read the live spine; unranked substring over identifiers (NEW-6); cannot be cited |
| Postgres FTS (SIG-UI-040's letter) | reject for the public site | the spine is not the release; K0 amends SIG-UI-040 to the release FTS5 design |
| Hosted engine (Meilisearch Cloud $23–30/month plans; Typesense GPL-3.0, RAM 2–3× data) | reject now; revisit on measured need | K12a §4.3 [Q056]/[Q057]; Meilisearch's $30 plan covers 100K documents vs 232,625 records here; adds a runtime service, a licence review (Typesense) and a second copy of the data outside the release model |
| Pagefind (static, per-page index) | reject for records; not needed for content | reported failure at 250k–300k pages (K12a [Q054]); content pages (≈ 10³) fit as `page` docs in the catalog with one ranking and no extra JS |
| Client-side SQLite (sql.js-httpvfs) | reject | 322 KB WASM (K0 §2.1) > the whole T2 budget |
| One unified index file across compartments | reject | the index files are published per compartment (`r/<pub>/c/<comp>/`); a merged file would mix ODbL (osm_physical) with other licences in one database (ADR-118 separation); federation costs < 2 ms warm (§2.2) |
| Records in the typeahead | reject | set B: max shard 339 KB gzip, ≈ 45 ms per keystroke on an M3 (§2.4) |

### 5.3 Licences and compartments in one search box

- Each **record** index stays inside its compartment and carries its licence (unchanged from ADR-133).
- The **catalog** is SIG's own compartment (CC BY 4.0 metadata) plus public-domain gazetteer names (Census, Natural Earth); a
  GeoNames layer, if adopted, adds its CC BY 4.0 attribution line. **A name known only from a compartment's data (e.g. an
  operator name from an OSM tag) is indexed in that compartment, never in the catalog**, so ODbL content never leaves
  osm_physical's index.
- **Result groups:** catalog cards first, then records **grouped by licence compartment**, each group headed by its licence
  and attribution line ("OpenStreetMap contributors, ODbL 1.0 — 154,528 records match"), each with its own cursor. A reader can
  narrow to one compartment (`collection=`), exactly as ADR-134's `collection` facet does today.
- The API computes the groups in one request (federation), so the reader no longer picks a compartment first (NEW-5).

### 5.4 Release pinning and cadence (G3)

- Indexes and shards are built in the release build, staged with the release, verified by V1 (integrity) and served only for
  **promoted** publications; `latest` resolves through the API's conf-gen pointer (REL-05). Every response states the release
  label, publication id and as-of; the HTML repeats G3's stamp.
- A format change (v1 → v2) bumps `search_index_version`, which mints a new namespace (ADR-132); older promoted releases keep
  their v1 route working (`/compartments/{c}/search`).
- **Freshness = release freshness** (monthly per G3 §7). The results page says: "Search covers release sig-… (data as of …).
  The developer API may hold newer, uncited data." No incremental index between releases.
- Responses to `release=p-<sha>` URLs are immutable: `Cache-Control: public, max-age=31536000, immutable`; `latest`:
  `max-age=300`. Parameterized search URLs are `noindex,follow` with a canonical to `/search/` (K0 §4.5).
- G3 V5 (link crawl) samples search result `href`s on staging; the builder chooses each target from the release's route
  allow-list (G3 §5.4), so a result never links to a 404 (the C4 NEW-1 / K12b "page roots" failure).

### 5.5 Serving: memory, storage and failure

- **Verify and copy, never read whole.** On first use per publication, stream each index file from the read-only release
  mount to local disk in 1 MiB chunks while hashing; compare with the integrity manifest; open the local copy `mode=ro`. This
  replaces `path.read_bytes()` (NEW-2) and avoids SQLite page reads over gcsfuse (latency unmeasured — SRCH-07 measures).
- **Memory:** Cloud Run's local disk is in memory; ≈ 99 MB of v2 indexes per served release fits in **1 GiB** (D-K3-5).
  Two releases (latest + one pinned) ≈ 200 MB. An LRU evicts older publications' copies.
- **Degraded mode (§46.5, K0 R-8):** API down → the `/search/` page still offers the typeahead (static shards) and the browse
  index; the no-JS form's target returns the LB's error page, and the page links the static browse (K0 §5.2 item 4).

### 5.6 Abuse and rate limits

- **Bounded work per request (keep from ADR-133):** q ≤ 200 code points and ≤ 10 words; limit ≤ 50 per group; 2 s deadline;
  ≤ 100 KiB body; cursors bound to release + query + filters.
- **Per-client token bucket in the API** (e.g. 30 requests/minute, burst 10; D-K3-6), keyed on the client address the Google
  external LB appends to `X-Forwarded-For` (not the peer — C4 NEW-16's intake limiter bug); 429 with an HTML page for `format=html`
  (DR-C4-10).
- **Cost ceiling:** Cloud Run `max-instances 2` (unchanged); a budget alert when search-attributable cost exceeds $50/month (K0
  revisit trigger 4). Cloud Armor rate rules are an operator option, not first-pass work (prices not re-read).
- **No query logging** (D-K3-4): no query strings in logs or analytics; only aggregate counters (requests, zero-result rate,
  p95 latency) per release. Readers of a surveillance-accountability site should not create a record of what they looked for.

### 5.7 Cost (monthly; **inference** from G1/K0 unit prices; Cloud Run request fees not re-read)

| item | estimate |
|---|---|
| `sig-api` 512 MiB → 1 GiB at min-instances 1 (0.5 GiB × 2.63 M s × $0.0000025/GiB-s) | ≈ **$3.3** |
| Queries: ≈ 30 ms vCPU each → 1 M queries ≈ 30,000 vCPU-s × $0.000024 + request fees | ≈ **$1 per million** (≈ $0.1 at 100k/month) |
| Index + shard storage (≈ 100 MB per retained release) and ≈ 1,000 extra objects per release | < $0.05 |
| Typeahead egress (≈ 10 KB of shards per session; 100k sessions ≈ 1 GB) | ≈ $0.12 on GCS; $0 on R2 |
| **Incremental total** | **≈ $3–5**, inside U-008 and K0's $50 search trigger |
| Worst case: 2 instances saturated all month (2 × 2.63 M s × ($0.000024 + 1 GiB × $0.0000025)) | ≈ $140 — why §5.6 exists |

---

## 6. UX

### 6.1 The `/search/` page (T2)

- **One labelled search field** (`<label>Search places, organizations, sources and records</label>`), one Submit button, and
  facets as real form controls, all inside `<form method="get" action="/v1/releases/<pub>/search">` with `format=html`. With
  JS, the Preact app intercepts submit, fetches JSON from the same URL and renders the same markup into the reserved box that
  already holds the server-rendered first view (K0 I-2, NEW-3's CLS fix).
- **Results order:** "Top matches" (identifier, alias and exact-name cards) → typed sections *Places · Organizations ·
  Technologies · Sources · Documents* → *Records*, in licence groups. Each section shows ≤ 5 with "more places (12)".
- **Facets with counts** (GET links without JS; instant with JS): Type, Licence group, Jurisdiction (hierarchical by K4 key
  chain), Source, Location (public point / no public point); Technology when F-325's field exists; Date (first/last seen) when
  K5's per-run fields exist. A facet value with 0 is shown only when selected ("0 of N" stays linkable, ADR-134).
- **Header strip:** "Release sig-2026-09-27 · data as of 2026-09-27 · 232,625 records in 12 licence groups searched" (named
  totals, SIG-FIND-003), and "Cite this search" (the snapshot-pinned URL, K0 §4.5).
- **Query the data (later, SRCH-08):** "Download these results (CSV/JSON, ≤ 10,000 rows)" — Datasette-style (K12a [Q087]).

### 6.2 The typeahead (`<sig-typeahead>`, T1 in the site header; also on `/search/`)

- ARIA APG combobox (`role=combobox`, `aria-expanded`, `aria-controls`, `aria-activedescendant`, `aria-autocomplete=list`):
  Down/Up move, Enter opens the highlighted suggestion or submits the form if none, Escape closes, Tab leaves. A live region
  says "5 suggestions". Suggestions are text only (no `innerHTML`, K0 §4.8).
- Suggests **named things only** (§2.4 set A/C): places with a record count and parent ("Texas — US state · 3,996 records"),
  organizations, sources, technologies. Selecting one navigates to its page; records are reached by submitting.
- Fetches one shard (≤ 50 KiB, typically < 1 KB) after two characters; never sends keystrokes to a server.
- Without JS it is an ordinary search field that submits the form.

### 6.3 Result cards: the evidence basis on every result

| type | card shows (always) | links |
|---|---|---|
| Place | name, level, parent; "N records from M sources in this release"; declared vs located counts when K4 lands; freshness | dossier · map framed on the place (K1 `at=`/bbox) · "search within" |
| Organization | name, type, aliases; "named in N claims from M sources, first/last seen" with currency (e.g. HISTORICAL for the 2020 LEARN edges, K12b NEW-2) | entity page · relationships |
| Technology | label, family, definition (vocabulary); "records classified: 0 — SIG does not yet classify sites by technology" until F-325 is fixed; sources whose names match | filtered search · methodology |
| Source | registry name, publisher, licence and SIG publication basis, records, last successful run, compartments | source page (K10) · upstream link (J4 lane) |
| Document | type, source, capture date, capture status, directness | evidence page (K8) · original (J4 lane) |
| Record | display name — **"(name derived; the source gives none)"** when derived — type, place, source(s), licence group, record's `n_sources`/`n_observation_claims`, tier, release | record page with claims and evidence · map point · dossier |
| Alias | "ICE = U.S. Immigration and Customs Enforcement (source)"; what SIG holds for it; the collapsed word-hits | the target, if any · "what an empty result means" |

Every card also shows its **match reason** (§4.1) in small text, and every group its licence line.

### 6.4 Empty and partial states that do not mislead (C4 NEW-4 / F-150, DR-C4-05; agent-drafted copy)

- **No match:** "No record in release sig-2026-09-27 matches *zzqx-nonexistent* (232,625 records in 12 licence groups searched,
  data as of 2026-09-27). This means SIG's published record does not contain these words. It does not mean the thing does not
  exist, and it is not a finding that SIG looked for it." Links: what search covers · browse · suggest a source.
- **Alias with no record:** "SIG's release names no record for U.S. Immigration and Customs Enforcement. That is not evidence
  of any relationship, or of its absence." (K12b J3's expectation, without asserting research status.)
- **Filter to zero:** "No records match *camera* with Licence group = ODbL. 3 other licence groups have matches."
- **Degraded:** "Full search is unavailable right now. Suggestions and the browse index below still work."
- Never "recorded absence", never "not researched", never a link to the research queue as the explanation (K7/K8 NEW-6).

### 6.5 No-JS, keyboard, screen readers, mobile

- The HTML results page (from the API) carries the site navigation, G3 stamp, dispute link and per-group licences
  (DR-C4-02), HTML error pages for every status (DR-C4-10), and reflows at 320 px with wrapping ids (DR-C4-14).
- Headings: `h1` "Search results for …", `h2` per section, each result an `<article>` with an `h3` link. After a JS search,
  focus moves to the results heading and a polite live region announces "42 results in 5 groups".
- Facets are checkboxes in `<fieldset>`s with a visible "Apply" button without JS; with JS they apply instantly and announce.
- Pagination: "More records in this licence group" (per-group cursor), never a global page number that mixes licences.
- Both states pass axe with WCAG 2.2 AA and the page-type budgets (K0 I-8, SIG-UI-D series).

### 6.6 URL state (`sig.workspace-state/2`, K0 §4.5)

`/search/?v=2&release=p-<sha>&view=search&q=police%20station&type=record&type=source&jurisdiction=iso3166-2:US-TX&technology=alpr
&source=camreg_austin_tx&collection=portal&location=public-point&within=<scope>&cursor=<group:cursor>`

- `type` = result type (place · organization · technology · source · document · page · record); `kind` stays the entity type
  (v1). Legacy jurisdiction codes (`TX`) are accepted and normalized to K4 keys, with a visible note.
- The no-JS equivalent of any such URL is the API HTML route with the same parameters (the page's `<noscript>` names it).

### 6.7 Scoped search ("search within")

- **Dossier:** a GET form on every dossier (T1, zero JS): "Search within Texas" → `jurisdiction=<jkey>`, including descendants
  through K4's `jurisdiction_chain` (K6 needs this; K0 §8 "In-dossier search is a GET form").
- **Source page:** "Search this source's records" → `source=<id>` (K10 §13 hands the 154,528-row OSM layer to K3 search).
- **Entity page:** "Search related records" → `within=entity:<id>` over the entity's 1-hop neighbourhood (**later**, SRCH-09;
  needs K2's neighbourhood files).

---

## 7. API contract sketch (`sig.search-results/2`)

```json
{
  "schema": "sig.search-results/2",
  "release": {"label": "sig-2026-09-27.1", "publication_id": "p-…", "as_of_world": "2026-09-27"},
  "query": {"q": "ICE", "normalized": "ice", "filters": {}, "suggestion": null},
  "scope": {"records_searched": 232625, "groups_searched": 12, "excluded_records_by_reason": {"withdrawn": 0}},
  "top": [{"type": "alias", "key": "ICE", "expansion": "U.S. Immigration and Customs Enforcement",
           "expansion_source": "https://…", "target": null, "matched": "alias"}],
  "sections": [{"type": "place", "total": 0, "results": []}, "…"],
  "record_groups": [{"compartment": "ogl_uk3", "license": "OGL-UK-3.0", "attribution": "…",
                     "total": 12, "collapsed_reason": "word matches for an acronym alias",
                     "results": [{"record_key": "…", "name": "Nottingham Ice Stadium (Lower Parliament St)",
                                  "name_derived": false, "type": "deployment", "jurisdiction": "iso3166-2:GB-ENG",
                                  "sources": ["camreg_nottingham_gb"], "support": {"n_sources": 1, "n_observation_claims": 4},
                                  "matched": "word in name", "tier": 3, "href": "/r/p-…/c/ogl_uk3/entity/deployment/…/"}],
                     "next_cursor": "…"}],
  "facets": {"type": [["record", 98]], "collection": [["ogl_uk3", 12]], "jurisdiction": [["iso3166-2:GB-ENG", 9]]}
}
```

Totals are exact counts from FTS (cheap: 2.7 ms for 154,528 matches, §2.3), capped only if a count exceeds the deadline
("10,000+", stated). Scope counts include access-time denials (DR-C4-09).

---

## 8. Draft requirements (provisional `SIG-SRCH-Dnn`; T1 numbers or folds them) and acceptance tests

| id | draft requirement | acceptance test |
|---|---|---|
| SIG-SRCH-D01 | Public search MUST cover every eligible record of the selected release across **all** licence compartments in one request, keeping each compartment's records in a labelled licence group | crawl: one query returns groups from ≥ 2 compartments with correct licence lines; `scope.records_searched` = release record count − denials |
| SIG-SRCH-D02 | Results MUST be typed (place, organization, technology, source, document, page, record) and each MUST link to an existing page of that type in the same release | link check over the benchmark results: 0 non-200 `href`s on staging (G3 V5) |
| SIG-SRCH-D03 | Result order MUST be by match quality with a stated match reason per result; it MUST NOT use popularity, evidence counts or confidence | code review + a test that permuting `n_sources` does not change order |
| SIG-SRCH-D04 | A query that exactly names a jurisdiction (official or alternate name, ISO or postal code) MUST return that place first; homonyms MUST all be shown with their parent, ordered by records held | B01, B03, B04, B06, B07, B08, B39 top-1/top-3 |
| SIG-SRCH-D05 | Acronym aliases MUST match case-sensitively, show their expansion and its source, and MUST NOT present word-matches as matches for the acronym | B11: top-1 alias card; 0 record hits above the collapsed group; the card cites its expansion |
| SIG-SRCH-D06 | A query with no strong match MUST offer a spelling suggestion when one yields strong results, and MUST say it did so | B20, B22, B23 |
| SIG-SRCH-D07 | Every result MUST show its evidence basis (sources, support counts, release, as-of; for derived names, that the name is derived) | DOM check on every card type |
| SIG-SRCH-D08 | Empty and filtered-to-zero states MUST name what was searched (release, record count, groups) and MUST NOT assert research status or absence | B36 copy check (DR-C4-05) |
| SIG-SRCH-D09 | Search MUST work without JavaScript (GET form → server-rendered HTML with site chrome, facets, per-group paging and HTML error pages) and pass WCAG 2.2 AA in both states | Playwright JS-off journey over 5 benchmark queries; axe 0 violations JS on/off |
| SIG-SRCH-D10 | The typeahead MUST be an APG combobox over static per-release shards of named things, ≤ 50 KiB per shard, keystroke → suggestions ≤ 100 ms at 4× CPU throttle, sending no keystroke to a server | budget spec + a network assertion (only same-origin shard GETs) |
| SIG-SRCH-D11 | Search indexes MUST be built from the bound release projection, verified against the integrity manifest by streaming hash before use, and served only for promoted releases | unit test on a corrupted file (503); memory test: verification of a 300 MB file stays < 64 MiB RSS growth |
| SIG-SRCH-D12 | Search MUST NOT log query strings; per-client rate limits MUST key on the LB-reported client address | log grep in e2e; 429 test with two client addresses |
| SIG-SRCH-D13 | Relevance MUST be measured each release on a development set and a held-out set: top-3 success ≥ 90% (dev) and ≥ 80% (held-out) on answerable queries; 0 misleading top hits on the honest set; zero-result rate reported | benchmark harness output attached to the release readout (REL-06) |
| SIG-SRCH-D14 | p95 latency ≤ 300 ms for the benchmark on the production service shape (1 vCPU); index bytes ≤ 150 MB per release | SRCH-07 staging measurement |

Budgets (from K0 §4.3, unchanged): `/search/` initial JS ≤ 60 KiB, document ≤ 100 KiB, result page data ≤ 40 KiB, LCP ≤ 1.5 s,
CLS ≤ 0.02, TBT ≤ 100 ms, Lighthouse mobile ≥ 0.95, a11y 1.0; header typeahead ≤ 20 KiB as a T1 enhancement.

---

## 9. The benchmark query set

**Development set (40 queries, `tools/queries.py`):** derived from the C2/K12b personas and their recorded failures. Each row
has an id, persona, query, intent, expected answer, whether the live release can answer it, and what it needs.

| group | ids | queries |
|---|---|---|
| Places (12) | B01–B10, B38, B39 | Canberra · Austin · Texas · TX · Oklahoma City · Maryland · Georgia · Idaho · Winnipeg · Glasgow · Kansas City · Oklahoma |
| Aliases, technology (5) | B11–B13, B37, B15 | ICE · ALPR · license plate reader · red light camera · LEARN |
| Organizations, vendors, agencies (5) | B14, B16–B19 | Vigilant · Flock Safety · Motorola · Austin Police Department · Austin Police |
| Typos (4) | B20–B23 | Canbera · Vigilent · Austn · Marylnd |
| Record labels (3) | B24, B25, B40 | Cavalier & Portage · Northbourne Avenue · police station |
| Sources (3) | B26–B28 | data.act.gov.au · City of Austin traffic camera · DeFlock |
| Identifiers (3) | B29–B31 | camreg_austin_tx · a site UUID · the operator's research-queue agency UUID |
| Documents, contracts, policies (4) | B32–B35 | news article · agenda · contract renewal · retention policy |
| Negative (1) | B36 | zzqx-nonexistent |

**Judging.** 30 queries are judged on "the expected item is in the top 3" (a place, source, technology, organization,
document or record id); 10 that the release cannot answer (agencies and vendors not yet published, the research-queue UUID,
contracts, policies, US cities before K4, the nonsense string) are judged on "no misleading top hit". **Revision log:** after
the first run, B16 (Flock Safety) and B37 (red light camera) moved from "honest" to "top-3" because the release *does* hold the
right answer — the "Friendswood Flock Safety ALPR camera locations" source and several red-light camera sources; my first
expectation was wrong, not the engine.

**Results:** P32.14 6/30 + 10/10; v2 30/30 + 10/10. **The v2 figure is a development-set score** — I tuned the pipeline
(place ordering by records held, suggestion strictness) against these same queries, and one pass depends on an incidental
Natural Earth alternate (§2.3). It shows feasibility, not quality.

**Required before SRCH-02 ships (D-K3-7):** a **held-out set of ≥ 40 queries** with expected answers, written before the
implementation run by someone other than the implementing agent — ideally the operator (≈ 30 minutes: "what would you type,
and what should come first?"), otherwise a separate agent context whose output is labelled agent-written (P4). The harness
reports top-3 success, mean reciprocal rank, zero-result rate and misleading-top-hit count per release (SIG-SRCH-D13). Query
logs are not a source of test queries (D-K3-4).

---

## 10. Round-11 ticket outline

Sizes follow J3 §12 / K4 §9: **S** ≈ half a fresh-context run, **M** one run. "Live" = a production stage needing an
operator go.

| # | key | title | size | scope (one line) | depends | live / gate |
|---|---|---|---|---|---|---|
| 0 | *(ACT-17)* | *Wire the landed P32.14 search in production* | — | *G2's activation step (LB `/v1/*` rule, `--release-registry`, `SIG_RELEASE_SEARCH_BASE`; F-155). Not K3's ticket; K3 reuses the wiring. Fix NEW-2's whole-file read before this goes live* | G2, G3 REL-03b | op go |
| 1 | **SRCH-01** | Search index v2 builder | M | `sig.release-search-index/2`: compact per-compartment record index (weighted FTS5, marked derived names via K2's rule or an interim rule, K4 place text, registry source names), `claim_ref` table, catalog index (places from JUR-01 or the NE interim + NE populated places, sources with K9 facet fields, technology vocabulary, K2 entities as present, K8 documents, content pages), `search_aliases.toml` + loader; determinism, integrity, descriptor `search_index_version`; real-release size/time report (≤ 150 MB, ≤ 60 s) | REL-01 (descriptor v2); K2 label rule (interim allowed); JUR-01 (interim allowed) | — |
| 2 | **SRCH-02** | Query engine v2 + benchmark harness | M | the §4.2 pipeline in `exports.search_index`; tiers; per-group cursors; facets with counts; suggestions; `sig.search-results/2`; the withdrawal barrier and bounds carried over; the dev + held-out benchmark as a test with a real-sized **synthetic** fixture (invented names, K0 R-11) plus a release-mode run | SRCH-01; D-K3-7 (held-out set) | — |
| 3 | **SRCH-03** | API serving v2 | M | `GET /v1/releases/{pub|latest}/search` (federated) beside the v1 route; streaming verify-and-copy (fixes NEW-2); LRU; `latest` via conf-gen (REL-05); scope counts with denials (DR-C4-09); rate limiter on the LB client address; no query logging; cache headers; OpenAPI | SRCH-02; REL-05; ACT-17 wiring | API roll — op go |
| 4 | **SRCH-04** | No-JS results page | M | the API HTML representation: site chrome + stamp + dispute + licences (DR-C4-02), typed sections, cards with evidence basis, facet GET links, per-group paging, empty states (§6.4), HTML errors (DR-C4-10), 320 px reflow (DR-C4-14), "cite this search" | SRCH-03; REL-02 (stamp); UXK0-5 (cite form) | via API roll |
| 5 | **SRCH-05** | Typeahead + `/search/` rewrite | M | shard builder (catalog only, function words excluded from keys); `<sig-typeahead>` (T1, ≤ 20 KiB) in the header; `/search/` as T2 Preact (≤ 60 KiB) with URL state v2, reserved box, instant facets; remove the 500-row sample, `client:only` and React; degraded mode | SRCH-01, SRCH-04; UXK0-1/2/4/5/6 | via release |
| 6 | **SRCH-06** | Scoped search on dossiers and source pages | S | GET forms "Search within <place>" (descendants via `jurisdiction_chain`) and "Search this source"; typeahead scope | SRCH-04; JUR-03/04; K10 page | via release |
| 7 | **SRCH-07** | Acceptance + activation | S | real-release build; benchmark dev ≥ 90% / held-out ≥ 80% / 0 misleading; staging p95 ≤ 300 ms at 1 vCPU (gcsfuse vs local copy measured); budgets and Lighthouse on real data; axe JS on/off; cost check; agent journey walkthroughs (not user research, P4) | SRCH-01…06; G3 cut → promote (Class S) | **live** — op go |
| 8 | SRCH-08 | Result export (later wave) | S | CSV/JSON download of a result set (≤ 10,000 rows), per licence group with licence files (J3 TX download conventions) | SRCH-07; J3 downloads | via release |
| 9 | SRCH-09 | Later: claim-text search, entity-scoped search, tasks, contracts/policies, date facets | L (split) | only after the first pass is live and measured | K2, K5, K7, K11 | — |

**Order:** SRCH-01 → 02 → 03 → 04 → 05 → 06 → 07 (≈ 6.5 runs). SRCH-01 and SRCH-02 can start before K2/K4 land (interim
labels and the NE gazetteer), and must be re-run in SRCH-07 once they have. **Exactly-one ownership (P9):** production wiring
is ACT-17's; the jurisdiction registry and `lookup@1` are JUR-01's; label derivation and entity export are K2's; source facet
fields are K9's; the technology field is F-325's owner (I-stream); K3 owns the index format, engine, API route, results page,
typeahead and scoped forms.

---

## 11. Operator decisions needed

| id | decision | recommendation |
|---|---|---|
| **D-K3-1** | Adopt release search v2 (federated FTS5 behind the release-pinned API + static catalog typeahead shards); no hosted engine, no Pagefind, no live-spine search on the site | **Yes** |
| D-K3-2 | Alias governance: aliases are reviewed data rows with a cited expansion; expansion only, never a characterization or relationship | **Yes** |
| D-K3-3 | City layer for non-US places: Natural Earth populated places (public domain) now; GeoNames `cities15000` (CC BY 4.0, needs attribution) only if NE proves too thin | **NE now** (an HG-03-style rights check alongside D-K4-1) |
| D-K3-4 | Query logging | **None**; aggregate counters only |
| D-K3-5 | Raise `sig-api` memory 512 MiB → 1 GiB (≈ +$3/month) to hold verified local index copies | **Yes** |
| D-K3-6 | Rate limit (e.g. 30/min, burst 10 per client address); Cloud Armor not now | **Yes** |
| D-K3-7 | Who writes the held-out relevance set | **The operator** (≈ 30 min); otherwise a separate agent context, labelled agent-written |

---

## 12. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | Overfitting to the development set (tuned by the author) | held-out set written first by someone else (D-K3-7); report both scores |
| R-2 | Derived names mislead ("Camera site · …" implies a camera type SIG has not classified) | K2's rule; the "name derived" marker; technology words only from the technology field |
| R-3 | An alias card read as a relationship ("ICE" near records) | copy says expansion only; word-hits collapsed; no records under an alias unless they name the entity |
| R-4 | Place homonyms (Georgia, Springfield, Kansas City) | show every candidate with its parent; "records held" ordering disclosed; never auto-redirect |
| R-5 | Part VIII: search as a lookup tool for person-level data | index only the bound release projection; no free-text claim values in the first pass; a builder test that fails on any field outside the projection |
| R-6 | Abuse and cost | bounded work, rate limit, max-instances 2, $50 alert |
| R-7 | gcsfuse latency and memory | local verified copies; 1 GiB; measured in SRCH-07 |
| R-8 | Growth: K2 entities (6,849 Flock share-list targets and 917 portals, I3), K4 places, claim search | budgets in SRCH-01 (≤ 150 MB); catalog shards measured at 1.3 MB gzip for +19.8k names (set C) |
| R-9 | bm25 not comparable across compartments | tiers dominate; records presented per licence group |
| R-10 | Licence mixing in the catalog | catalog = SIG CC BY 4.0 + public domain (+ GeoNames CC BY if adopted); compartment-only names stay in their compartment's index |
| R-11 | K2/K4 slip, leaving the journalist's queries (agencies, vendors, US cities) unanswerable | ship v2 with the catalog it can have; the honest empty state says what is missing; SRCH-07 re-runs when K2/K4 land |

---

## 13. Interfaces

| row | K3 needs from it | K3 gives it |
|---|---|---|
| K0 | page types, budgets, URL state v2, component kit (`<sig-typeahead>`), CSP | the `/search/` T2 and header T1 designs; measured shard budgets |
| **K2** (not yet written) | a deterministic **label derivation rule** (type · operator · place) for the 82.8% unlabelled records; agency/vendor/organization **entities in the release** with names, aliases and ids; entity pages as link targets; later, neighbourhood files for entity-scoped search | an entity search box; `type=organization` results |
| K4 | JUR-01 registry (keys, names, alternates, levels, parents, bbox), `lookup@1`, `jurisdiction_chain`, dossier URLs | the `kind=place` consumer K4 §7 names; in-dossier search |
| K5 | per-run first/last seen (date facets, later) | — |
| K6 | — | in-dossier search form (§6.7) |
| K8 | readable document titles; `/evidence/<id>/` pages | `type=document` results |
| K9/K10 | source facet fields (class, geography, publisher type, licence, lane, status); `/sources/<id>/` pages | `source=` scoped search; the multi-facet source filter J3 routes to `/search/` |
| K11 | task pages (later) | tasks as a type (later) |
| J3 | licence and attribution lines; download conventions | — |
| G3 | descriptor v2 (`search_index_version`), REL-05 API parity, V5 link crawl, V11 budgets, stamp | release-pinned, immutable search responses |
| G2 | ACT-17 production wiring (F-155) | the v2 route to wire |
| K1 | `at=`/bbox parameter | place cards link the map framed on the place |
| C4 | DR-C4-02, 05, 09, 10, 14 | adopted in SRCH-03/04 |
| I-stream (F-325 owner) | a technology field on published records | a live technology facet |

---

## 14. New findings (`findings/incoming/K3.csv`)

| id | sev | title |
|---|---|---|
| NEW-1 | S2 | P32.14 release search orders every result list alphabetically by label, and empty labels sort first: unfiltered browse opens on unlabelled records in every large compartment (osm_physical: 3,089 pages before the first named record) |
| NEW-2 | S2 | On the real release the P32.14 index layout is 488.6 MB (osm_physical 301 MB, mostly text claim-id and facet tables), and the API verifies each file by reading it whole into memory on a 512 MiB service (latent) |
| NEW-3 | S2 | Exact-token matching does not remove the misleading hits: P32.14 answers "ICE" with ice stadiums and "Maryland", "Georgia", "Idaho" and "Oklahoma" with street names in other states and countries |
| NEW-4 | S2 | The technology facet offered by the release search API, its HTML form and the workspace URL contract is structurally empty (0 rows in every compartment), and `kind` has a single value |
| NEW-5 | S2 | Release search makes the reader choose one of 12 licence compartments before searching, and a two-letter code returns 422 in every compartment that lacks it (10 of 12 for "TX") |
| NEW-6 | S3 | Live-spine `/v1/search` cannot find an entity by its own id and returns substring matches in UUID order, so it is no substitute for a public search |
| NEW-7 | S2 | The release publishes no agency, vendor or organization records, so no release-pinned search can answer the journalist's name queries; the "expose `/v1/search`" shortcut (K12b F-23) would answer them only from the live spine that K0 I-10 and G3 REL-05 bar from public pages |

---

## 15. Limitations and command log

**Limitations.**
- All latencies are warm-cache on an Apple M3 Pro; Cloud Run 1 vCPU and gcsfuse were not measured (SRCH-07 does).
- The v2 relevance score is on a development set the author tuned against; judgements are agent-written (P4).
- The prototype's "Canberra" resolution relies on a Natural Earth `woe_name` alternate; US city queries (Austin, Oklahoma City,
  Kansas City) do not resolve to places without K4's Census places, and no Census place file was available locally.
- Organization search was exercised with one organization (the release's only named one); K2's entity export will change the
  catalog's size and the ranking mix (set C is a synthetic size proxy only).
- The derived display name is a placeholder, not a proposal for K2's rule.
- Cloud Run request fees, Cloud Armor and current vCPU prices were not re-read; costs reuse G1/K0 unit prices (inference).
- The compact claim table was built for one compartment and extrapolated linearly.
- Claim-text search size is an estimate (≈ 100 B per claim), not a measurement.

**Commands** (all local and read-only with respect to production; outputs under `docs/build/logs/next-phase/K3/out/`, hashed in
`SHA256SUMS`):

| # | `date -u` | command | result |
|---|---|---|---|
| K1 | 22:09:14Z | `git branch --show-current`; list planning dir | `claude/next-phase-planning` |
| K2 | 22:11:44Z | duckdb over `C3/bucket/parquet/*.parquet`: look up the network agency/organization ids; count labels matching Austin/Flock/Vigilant/Canberra | 0 agency/org records; 17 · 0 · 0 · 66 |
| K3 | 22:13:47Z–22:13:55Z | `tools/a_baseline.py` (landed `build_search_index`, unchanged) | §2.1 sizes |
| K4 | 22:14:53Z | `tools/a_bench.py` (40 queries × 12 compartments, landed `search`) | §2.2 |
| K5 | between K4 and K6 | `dbstat` breakdown; `a_order.py` | §2.1 table split; empty-label ordering |
| K6 | 22:17:40Z–22:19:33Z | `tools/b_build_v2.py` (three fix-and-rerun cycles: duplicate NE keys, missing names, the F-228 duplicate slug); `tools/c_query_v2.py` (two runs; §9 revision log) | §2.3 |
| K7 | between K6 and K8 | `tools/d_score_baseline.py` | P32.14 6/30 + 10/10 |
| K8 | 22:20:31Z–22:20:36Z | `tools/e_typeahead.py` | §2.4 shard sizes |
| K9 | 22:20:46Z | `npm install --userconfig=/dev/null --ignore-scripts --no-audit --no-fund minisearch@7.2.0` into `K3/node/` | 7.2.0 |
| K10 | 22:21:00Z | `node node/bench.mjs` | §2.4 MiniSearch timings, typo probes |
| K11 | between K10 and K12 | `g_facets` (inline Python); `h_claimids` (inline Python) | §2.3 facet cost; 25.0 B/claim, 891,661 anchors |
| K12 | 22:22:39Z | `sysctl`; `git rev-parse`; `shasum -a 256` of tools and outputs → `K3/SHA256SUMS`; `git diff --stat b051732c HEAD -- exports api web/src connectors/src ontology/vocab docs/2_canonical_design_spec.md` | M3 Pro; `b6b3d970`; diff empty |
| K13 | 22:23:15Z | `a_order2.py` (re-run with clock stamps for NEW-1/NEW-4) | 50/50 unlabelled on page 1 in 5 compartments; technology facet 0 rows |
