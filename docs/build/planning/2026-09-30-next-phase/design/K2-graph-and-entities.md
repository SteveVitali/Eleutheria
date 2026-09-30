# K2 — Graph explorer, global graphs and entity pages (operator ask U-003.2)

- **Row:** K2 (Stream K, design/architecture) · **Written:** 2026-09-30, work window 22:09Z–22:38Z (`date -u`)
- **Worktree HEAD at write time:** `b6b3d970` (branch `claude/next-phase-planning`). `git diff --stat b051732c HEAD --
  exports api db web ontology reconcile inference resolution policy connectors` is empty, so every `code` citation is
  also a chain-tip citation.
- **Operator input answered (verbatim):** U-003.2 — *"the network explorer is confusing and very opaque, for one thing, the
  UUIDs are meaningless, e.g. '01a0d751-0901-7a6c-8789-06bab8c7456e' should be replaced with something human-readable, and
  perhaps these can link to detail pages with metadata on the underlying referenced entity, or whatever makes sense, and
  moreover, I think we would strongly prefer a global graph or set of graphs, perhaps searchable/navigable or perhaps not
  that truly lays bare all that we know and makes it explorable"*; U-005 — journalists *"need to be able to really truly
  explore the knowledge graph … always with full explicit transparent evidence/lineage"*. U-008 (≤ $300/month) bounds cost.
- **Binding input:** `design/K0-interactive-architecture.md` — `/explore/` is T2 with ≤ 120 KiB initial JS; entity pages
  are T1 and static per release; overview graphs ≤ ~3,000 nodes; sigma + graphology; the no-JS rule; `sig.workspace-state/2`;
  static per-release neighbourhood files; no live-spine data on public pages (K0 I-10).
- **Inputs read:** META_PLAN §3 and the K2 row; K0 (all); `research/K12a-prior-art.md` §3, §5, §6.2, §8; `review/K12b-explorability.md`
  (all) and `findings/incoming/K12b.csv`; `findings/incoming/K0.csv`; `review/DATA_TRUTH.md` §1, §4.11–§4.16, §5;
  `design/J3-transparency-design.md` §0, §3, §5, §12; `design/K4-dossier-index.md` §0, §3.1, §7; `design/K5-dossier-sources.md`
  §0; `design/K11-research-queue.md` §3; `design/G3-release-model.md` §0; `research/I3-alpr-networks.md` §1; `findings/incoming/L1.csv`
  (landed 22:15:49Z during this run; titles and NEW-4/5/8/10/12 read) and `findings/FINDINGS.csv` (grep for overlap); spec
  SIG-UI-004/009/021–025, SIG-TIME-010–012, SIG-IDENT-027–033, SIG-RECON-049/050, SIG-INGEST-043/043c, §43.2a; ADR-106.
  Code: listed per citation. Two read-only exploration sub-agents mapped the ontology/DDL and the export/API/web label path;
  every line cited below from their reports was re-read by me (§16).
- **Evidence classes (P1):** `code` (file:line at `b6b3d970`), `recorded-execution` (read-only spine queries K00–K31 and
  local computations, §16), `live-read` (3 public API GETs, 22:17:36Z–22:17:42Z), `release` (C3's sha-verified copy of
  `sig-2026-09-27-ce480ab1`). Sizes, costs and user behaviour are **`inference`** and say so.
- **Two different data sets.** The **release** is what the public site shows (232,625 site records, one 131-node network).
  The **spine** is the live Cloud SQL database (read at 22:14–22:25Z; 250,046 deployment-typed entities, 973 organisations,
  ≈2.5 M claims). The spine holds far more graph than the release publishes; both are measured and never mixed (C3 §1).
- **P3 / P14 / P16.** Production was only read: spine queries through the read-only path row L2 opened (cloud-sql-proxy →
  `SET ROLE sig_read_public`, `BEGIN READ ONLY`, 60 s timeout, SELECT/WITH only; the password stayed in process memory);
  3 anonymous API GETs with UA `SIG-planning-K2-review/1 (read-only)`. No secret, and no person-level value, appears
  here. Part VIII: agency, vendor and government names quoted below are institutions taken from SIG's own data.
- **Status (P5):** nothing here is engineered. It is a design; requirements are drafts for K13/T1.
- **Writes:** this file and `findings/incoming/K2.csv` only.

---

## 0. Summary on one page

**Why the network shows UUIDs although SIG holds the names (root cause, `code` + `recorded-execution`).** Four seams, all
confirmed:
1. **The exporter looks the names up in the wrong table.** `_network_from_materialized` labels each node with
   `source_names.get(entity_id, entity_id)` (`exports/src/exports/spine_export.py:994-995`); `source_names` is
   `source_registry` keyed by *source* ids (`:132-135`), so an entity UUID never matches and the label is the id. The names
   live in `organization.cached_canonical_name` (written at `db/src/db/claim_sink.py:482-497`), which the exporter never reads.
   The API does read it (`api/src/api/store_pg.py:219-227, 632-668`), which is why `/v1/entity` says
   "Vigilant Solutions (LEARN)" (live-read 22:17:36Z).
2. **There is no name model.** The ontology has no generic label slot (`Entity` carries only `id`); names are type-specific
   slots that the pipeline does not populate as claims; there is no `canonical_name` predicate and no name resolution
   (`ontology/src/ontology/schema/entities.yaml:24-28, 78-84`).
3. **Every connector subject is typed `deployment`** (`claim_sink.py:118`; L1 NEW-5). Agencies, contracts, grants, bills and
   Flock portals carry their only human name *inside the connector key* (`data_driven:agency:Austin Police Department`),
   and the API's fallback label is that raw key (K12b capture sha `334e4083…`: `atlas:Austin Police Department:face-recognition`,
   `traffic_camera:camreg_austin_tx:austin_tx_traffic_cameras:1`).
4. **Sites take a label only from `camera_name`** (`exports/src/exports/shaping.py:101-102, 1099`), which only the
   `dot_511`/camera-registry connector emits (`connectors/src/connectors/dot_511.py:665-673`). In the ODbL `osm_physical`
   compartment (OSM/DeFlock republishes) 154,483 of 154,705 records have no name (K0 NEW-1). Result in the release: **192,536 of 232,625 records (82.8 %) unlabelled; 162,175
   (69.7 %) have neither a label nor a placed jurisdiction; and existing labels are not unique — 3,743 labels are shared by
   11,588 records (up to 504 per label).**

**Label policy (§3).** One shared derivation (`sig.entity-label/1`) used by exporter, pages, overviews, typeahead and API.
Per semantic kind: a source-given name where one exists (with its basis shown), otherwise a SIG template over claims
("Traffic camera · I-35 at 6th St · Austin, TX"), otherwise a typed fallback ("ALPR camera #K3M9Q2A · place not recorded ·
OpenStreetMap"); a descriptor line; deterministic disambiguation; the Part VIII person-name screen; **never a UUID or a
connector key.** URLs: `/entity/<type>/<name-slug>--<hash7>/`, hash = Crockford base32 of sha256(UUID), frozen once issued
(measured: 10 hex digits of sha256 are already unique over all 251,019 entities), 301 on rename/merge, 410 on withdrawal,
`/id/<type>/<uuid>` → current URL.

**Entity pages (§4).** T1 pages, static per release, one template: header + descriptor, identifiers and crosswalks, claims
by predicate with the four epistemic fields and provenance, typed relationship tables with dates, currency, sources and
evidence, access (who can reach whose data), contradictions, timeline, map snippet, related dossiers/sources/tasks,
downloads, cite. **Wave E1 ≈ 2,700 pages** (973 organisations, 200 Data Driven agencies, 1,528 Flock portals); **E2 ≈ 3,500**
(1,414 surveillance-relevant notices, 652 contracts, 1,079 grants, 347 bills/ordinances/instruments, 4 events); **E3 ≈ 4,100**
Atlas agencies once placed. Sites keep their T0 record pages and gain derived labels. ≈ 26k new objects per release,
≈ $0.13 in writes, +10–15 min build (inference).

**The real graph (§1, spine).** 42,488 entity-to-organisation edges over 41,897 nodes in **354 connected components**; the
largest is a 26,840-node star ("OpenStreetMap contributors" as camera *operator* — a modelling error, NEW-2). 969
organisations: median degree 1, 21 with ≥ 100, top 21 carry 94.5 % of edges. **0 edges have a bounded valid period; 500 of
42,488 (1.2 %) have any date.** Literal (unresolved) party claims add a much larger latent graph: buyer→seller 5,136 nodes /
4,746 pairs; funder→recipient 703 / 752; 139 camera operators. Flock share lists (474,184 edges, I3) are not claims yet.

**The set of graphs (§5), each ≤ 3,000 nodes, per-compartment files, static SVG + table + download:** O0 **type map** (≈24
nodes; "everything SIG holds, by kind", gaps included) · O1 **supply** (surveillance-relevant buyer ↔ vendor; ≈1.4k nodes,
≈43 KB gz) · O2 **access** ("who can search whose data"; 131 nodes today, historical; Flock scale → state × state matrix + egos)
· O3 **funding** (703 nodes, ≈22 KB gz) · O4 **operators × places** (≈200 nodes) · O5 **governance** (≈420 nodes) · O7
**adoption** (Atlas agency × technology, after placement). Measured compact encoding: 3k nodes / 10k edges = 132 KB gzip,
inside K0's 200 KiB per-overview budget.

**Key interactions.** Search-to-node (K3 shards) · neighbourhood expansion from static JSON twins (≤ 10 expansions) · filters
(kind, relation with the three access kinds separate, currency, year range, source, jurisdiction, technology, compartment)
· path finding (≤ 3 hops publishable, per-hop evidence, typed "no path") · node panel and list/table equivalents · **every
edge → edge panel → J3 provenance panel in ≤ 2 actions, with and without JS.**

**Honesty (§7).** Historical and undated edges visibly labelled and excluded from present-tense statements; degree-only
sharing data never drawn as edges (SIG-INGEST-043c); derived labels and default directness disclosed; no centrality or hub
ranking until SIG-IDENT-030's ER gates pass or an ADR waives them (the live `/network/` already violates this, NEW-6).

**Tickets (§10): GX-01…GX-10 — 14 units with the a/b splits, ≈ 12.5 runs.** First and cheapest: GX-01 labels + GX-02 the `/network/` label/date fix, shippable
in the first product republish.

**Operator decisions (§11):** D-K2-1 organisation publication review (all 969 referenced organisations are review-flagged,
NEW-1) · D-K2-2 SIG-IDENT-030 posture · D-K2-3 degree-only rendering · D-K2-4 Flock share lists as org-level claims ·
D-K2-5 supply relevance rule · D-K2-6 URL scheme and page waves · D-K2-7 "possibly the same" wording.

**New findings (§14, `findings/incoming/K2.csv`):** 1 × S1, 7 × S2, 1 × S3.

---

## 1. Ground truth: what the graph actually is

### 1.1 The release (`release`; C3's copy, sha256 verified by C3; hashes re-computed here)

| artifact | sha256 prefix | what it holds (measured) |
|---|---|---|
| 12 × `*/sites.parquet` | e.g. `osm_physical` `860845d7…`, `public_record` `a3d631cf…` | 236,994 rows, **232,625 entities, all `entity_type = deployment`**; 192,536 unlabelled (82.8 %); 66,415 with a placed jurisdiction; 162,175 (69.7 %) with neither label nor placed jurisdiction; 40,089 labelled with 32,244 distinct labels; **3,743 labels shared by 11,588 entities, max 504 per label** |
| `web/network.json` | `556101e6…` | 131 nodes (130 `agency`, 1 `partner`), 130 edges, `access_paths: []`; **131 of 131 node labels equal the node id**; edges carry `support: WEAKLY_SUPPORTED`, `evidence_count: 1`, **no date, no source, no currency, no `evidence` key** (the key was added by P32.15, commit `a78720ab` (`git log`), so the release was built by earlier code) |
| `sig_graph/sharing_edges.csv` | `1cb8b7e0…` | 632 rows: 260 `configured_sharing_partner` (130 agencies × 2 twins: one literal `partner_ref = "Vigilant Solutions (LEARN)"`, one entity ref), 370 `sharing_partner_degree` over 185 agencies (median 68, max 851, sum 29,642 partner slots), 2 `sharing_restriction` (`okcpd_policy`); all EFF rows `observed_at = 2020-01-28` |
| anything organisation-, contract- or policy-shaped | — | **absent.** No release file carries organisations, contracts, grants, bills or policies as rows; they reach the public only as UUIDs in the two files above and in dossier governance rows (`spine_export.py:1311-1328`) |

### 1.2 The spine (`recorded-execution`, read-only, 22:14–22:25Z)

**Entities by semantic kind** (K01; kind = first segment of the `sig.connector.subject` key, or the `organization` table;
"has" columns count subjects with ≥ 1 current claim of that family):

| kind (entity_type) | n | name-bearing claim | party claim | place claim | dated claim | notes |
|---|---:|---|---|---|---|---|
| traffic_camera (deployment) | 232,628 | `camera_name` 43,339 | `camera_operator` 232,627 | 232,627 (166,210 declared `unresolved`, K26) | 0 | 139 distinct operator strings (K26) |
| procurement_notice (deployment) | 5,376 | `title` 2,287 | buyer 5,376 · seller 2,441 | 2,287 | 4,265 | TED 2,287, usaspending 879, NYC 746, KCMO 500, SF 401, Austin 320, FEMA 200, SAM 43 (K22) |
| atlas (deployment) | 4,756 | agency name only in the key (4,170 raw / 4,134 normalised names) | — | 0 | 0 | ALPR 3,574 · face recognition 945 · gunshot detection 237 (K11) |
| contract (deployment) | 1,872 | — | buyer 1,871 · seller 652 | 0 | 652 | Legistar 1,219 · DECP (FR) 652 |
| flock_portal (deployment) | 1,528 | slug only (e.g. `abington-ma-pd`) | — | 0 | 0 | 1,498 slugs carry a US-state token and 99 a `-tx` token (K29/K30; a regex, so a token such as `-co-` can be a false positive — inference) |
| agenda_item (deployment) | 1,364 | — | — | 0 | 0 | `document` 3,037, `content_term` 1,093 |
| funding_instrument (deployment) | 1,079 | `program_name` 200 | funder 1,079 · recipient 1,079 | 0 | 1,051 | usaspending 879, FEMA HSGP 200 |
| organization (organization) | 973 | `cached_canonical_name` 973 | — (**0 subject claims**, K13) | 0 | 0 | 969 `unclassified` + all **`publication_review_required = true`**; 4 typed, unreferenced (K05) |
| osm (deployment) | 665 | description 59 · operator_stated 57 | manufacturer 539 | 0 | 0 | |
| legislative_bill (deployment) | 308 | `bill_title` 308 | — | 308 | 308 | congress.gov + OpenStates |
| data_driven (deployment) | 200 | agency name only in the key | vendor 200 | 0 | observed 2020-01-28 | the EFF Data Driven agencies |
| jurisdiction (deployment) | 195 | ISO code in the key | `ai_surveillance_supplier` 74 | — | — | country-level index records |
| legal_instrument / ccops / accountability / pathways / madada / records / sig / seed | 30 / 9 / 4 / 3 / 25 / 1 / 2 / 1 | citations, bodies | enacting_body, event_organizations | 29 (legal) | 25 (legal) · 4 (events) | `records` carries a `requesting_party` (Part VIII: never displayed, §3.4) |

**Entity-reference edges** (claims whose object is an entity; K03, K07):

| predicate | from kind | → | claims | distinct subjects | distinct orgs | dated (`observed_at`) | bounded valid period |
|---|---|---|---:|---:|---:|---:|---:|
| `camera_operator` | traffic_camera | organization | 39,396 | 38,871 | 21 | 0 | 0 |
| `seller` | procurement_notice | organization | 1,288 | 1,119 | 842 | 0 | 0 |
| `buyer` | procurement_notice | organization | 1,127 | 1,126 | 77 | 0 | 0 |
| `recipient` | funding_instrument / procurement_notice | organization | 170 + 170 | 170 + 170 | 22 | 170 | 0 |
| `vendor` | data_driven | organization | 200 | 200 | 1 | 200 | 0 |
| `configured_sharing_partner` | data_driven | organization | 130 | 130 | 1 | 130 | 0 |
| `event_organizations` | accountability | organization | 7 | 4 | 6 | 0 | 0 |
| **total** | | | **42,488** | **40,928** | **969** | **500 (1.2 %)** | **0** |

**Shape** (`comp.py` over K07): 41,897 nodes, **354 connected components**; sizes 26,840 · 1,706 · 1,470 · 1,329 · 1,189 ·
1,007 · 872 · 862 · 857 · 781 …; 229 two-node components. Every large component is a camera-operator star. The largest centre
is **"OpenStreetMap contributors (republished man_made=surveillance nodes)"** as `camera_operator` of 26,839 cameras
(K06; NEW-2). Organisation degree (distinct subjects): median **1**, p90 4, max 26,839; 680 of 969 have degree 1; 21 have
≥ 100; the top 21 carry 94.5 % and the top 50 96.5 % of all organisation edges. Projected organisation–organisation graph
(shared subject): 734 subjects link ≥ 2 organisations, 1,197 pairs, 354 components, largest 344, 335 isolated.

**The latent graph in literal (unresolved) party claims** (K08, K09; node = distinct normalised string or entity id, so a
party present both as text and as an entity counts twice — upper bounds):

| projection | left | right | nodes | distinct pairs | components (largest) | notes |
|---|---:|---:|---:|---:|---|---|
| procurement buyer → seller (all notices + contracts) | 1,988 | 3,148 | 5,136 | 4,746 | 1,854 (1,912) | max buyer out-degree 617 |
| … only the 1,414 keyword-matched (surveillance-relevant) notices (K24/K25) | 432 | 780 | 1,212 | 852 | — | 1,025 notices name both sides |
| funding funder → recipient | 19 | 684 | 703 | 752 | 8 (669) | FEMA/usaspending |
| camera operator strings × declared jurisdiction (K26) | 139 | 55 | 194 | 139 | — | each operator string sits in exactly one declared jurisdiction |
| Data Driven access | 130 agencies | 1 pool | 131 | 130 | 1 | + degree attributes for 185 agencies |
| Flock portal share lists (I3 §1 item 6; **not claims**) | 917 portals | 6,849 targets | ≤ 7,766 | 474,184 | not measured | resolution is I8's |

**Epistemic state of edges** (K16–K18, K20):
- **Resolution:** `camera_operator`, `buyer`, `seller`, `recipient`, `funder` are all `probable / uncontested`
  (232,625; 6,796; 2,788; 2,158; 1,279 resolutions). `configured_sharing_partner` 130 and `sharing_partner_degree` 185 are
  `weakly_supported / insufficient`; `vendor` 200 is `unsupported / insufficient`. No edge predicate has a contested
  resolution; the only 2 contradiction rows concern one agency subject (C3 §4.11; K12b: one the `okcpd_policy` source also
  describes).
- **Directness and reliability are constants:** all **348,053** current party and sharing claims carry `D2 / R3`, the sink
  defaults (`claim_sink.py:116`, `_DEFAULT_DIRECTNESS = "D2"`) (NEW-3).
- **Evidence binding:** every edge claim has ≥ 1 `claim_evidence` row, but **0** point to a capture with bytes and **0** to
  an `http(s)` source URI — every edge is J3's `legacy_synthetic` state (J3 §5.1).
- **Materialised `relationship` table:** 130 rows, all `configured_access`, `valid_from = 2020-01-28` (kind `unknown`),
  **`valid_to_kind = ongoing`** (K17) — a 2016–17 observation recorded as open-ended (L1 NEW-10 has the root cause).
- **Accountability links:** 200 `accountability_link:has_vendor` derived facts (K14), all from Data Driven.

**Same agency, several entities** (K27, K28; exact normalised-name match, so an **inference** about identity): 170 of the 200
Data Driven agency names equal an Atlas agency name; 563 Atlas names span > 1 entity (one per technology); "Austin Police
Department" is 2 entities (Atlas face recognition; Data Driven). No organisation ER runs (L1 NEW-12).

**Procurement relevance** (K22, K23): the four city procurement portals (NYC 746, KCMO 500, SF 401, Austin 320 = 1,967
notices) carry **no** `matched_keyword` claim; only TED (543 of 2,287) and usaspending (871 of 879) do. Top keywords:
drone 367, cctv 363, surveillance_camera 243, alpr 215, body_worn_camera 117 (NEW-7).

### 1.3 What the API shows (`live-read`, 22:17:36Z–22:17:42Z)

`/v1/entity/organization/<id>` for Vigilant Solutions (LEARN) (`7ffd4570…`), Washington State Department of Transportation
(`0fbf81cf…`) and City of Austin (`3283a1ee…`): each returns the name, **`facts: []`**, `attribution: []`, `location: null` and
`coverage: {complete: true, evaluated: 0}`. Organisations hold no claims of their own and the API has no inbound-relationship
view (`api/src/api/routes.py:100-489` lists no neighbour route), so an organisation that operates 1,705 cameras reads as an
empty, "complete" record (NEW-5). The labels appear because P32.5's organisation gate is not deployed (F-218).

### 1.4 What "laying bare all we know" means per edge type, today

| edge type | what SIG can truthfully show | what it cannot |
|---|---|---|
| `configured_sharing_partner` (Data Driven → Vigilant LEARN pool) | 130 agencies; one source; recorded 2020-01-28 (the data itself is 2016–17 per L1 NEW-10); `weakly_supported`, `insufficient`, currency HISTORICAL, rationale "too weak to assert alone" | anything present-tense; partner identities beyond the pool |
| `sharing_partner_degree` | "shared with N agencies (partners not named)" for 185 agencies | any specific edge (SIG-INGEST-043c) |
| `vendor` (Data Driven) | "used Vigilant (2016–17 records)" for 200 agencies, `unsupported` | current vendor |
| `camera_operator` | the operator a camera registry names, per camera; probable, uncontested; undated | when the operation began or ended; the OSM "operator" is a source artefact (NEW-2) |
| `buyer`/`seller`/`recipient`/`funder` | the parties a notice, contract or award names; the notice's own dates (posted/award/signed) | whether a notice is surveillance-related unless keyword-matched (NEW-7); whether two parties are the same organisation |
| Flock share lists | nothing yet (not claims) | — |

---

## 2. Why labels are missing, in one chain

| seam | what happens | citation | fix owner |
|---|---|---|---|
| Ontology | no generic label slot; `Organization.canonical_name` is "a claim, not an authoritative column" but no name predicate or name resolution exists | `ontology/src/ontology/schema/entities.yaml:24-28, 78-84`; no `canonical_name` predicate in `ontology/vocab/predicates.yaml` (sub-agent grep) | GX-01 (derived label, not a new claim) |
| Sink | subjects typed `deployment`; an organisation's `cached_canonical_name` = first-seen label, `ON CONFLICT DO NOTHING` | `db/src/db/claim_sink.py:118, 482-497` | L1 NEW-5 (typing, F5 PKG-11); GX-01 reads the kind from the key meanwhile |
| Materialiser | builds edges only from the entity-ref twin; the literal twin that carries the name stays in `sharing_edges.csv` | `reconcile/src/reconcile/materialize.py:776-796` | GX-02 |
| Exporter, network | label lookup in `source_names` by entity id → always the id | `exports/src/exports/spine_export.py:132-135, 994-995` (older path `:1095-1096` hard-codes the id) | GX-02 |
| Exporter, identifiers | `entity_labels` (first `entity_identifier` by scheme) is fetched but used only for dossier gap rows | `spine_export.py:139-143, 1455-1461, 1707` | GX-01 |
| Exporter, sites | label = `camera_name` if resolved, else `None` | `exports/src/exports/shaping.py:101-107, 1017, 1099` | GX-01 |
| Connectors | only `dot_511` (and the camera-registry targets it drives) emits `camera_name`; OSM emits none | `connectors/src/connectors/dot_511.py:665-673, 1028` | none needed: derive (§3) |
| API | label = `cached_canonical_name` else the first identifier value → the raw connector key | `api/src/api/store_pg.py:219-227, 658-668` | GX-01 (API reads the shared label) |
| Web | `labelOf = … ?.label ?? id` on page and island | `web/src/pages/network.astro:49`; `web/src/islands/NetworkIsland.tsx:100-103` | GX-02; then GX-09 |
| Record pages | `f"Unnamed {record.entity_type}"` → "Unnamed deployment" | `exports/src/exports/release_pages.py:138` | GX-01 |

---

## 3. Label policy

### 3.1 Principles (binding on every GX ticket)

- **L-1 One derivation, everywhere.** A single `labels` module computes `label`, `descriptor`, `label_basis`, `url_key` for
  every entity at export time from the export's one snapshot. Exporter, record pages, T1 pages, overviews, typeahead shards,
  map popups (K1) and the API all read that result; no surface derives its own (K0 R-3).
- **L-2 Never an identifier as a label.** No UUID, connector key, source id or hash appears as a label, heading, node text,
  link text or table cell outside the "Identifiers" block (SIG-UI-D20). The fallback is typed words plus a short hash.
- **L-3 Say where a label came from.** `label_basis ∈ {source_name, source_title, key_name, slug_name, derived, fallback}`;
  anything other than `source_name`/`source_title` shows a one-line note ("Label composed by SIG from type, road and place").
  A derived label is never presented as an official name.
- **L-4 Labels are untrusted text.** Rendered as text only (K0 §4.8); trimmed; control characters removed; ≤ 80 characters
  in lists and nodes (cut on a word boundary with "…"; full text in the page heading).
- **L-5 Casing as recorded.** No automatic title-casing ("ILLINOIS EMERGENCY MANAGEMENT AGENCY…" stays as the source wrote it);
  the descriptor line carries the readable type.
- **L-6 Part VIII first.** Every label and slug passes the person-name screen (`policy/src/policy/officer.py`,
  `resolution/src/resolution/partner_identity.py:258-263` person-shaped refusal). A failure yields the typed fallback and a curation
  item. Person entities have no label, page, node or slug. `requesting_party` and similar fields are never label inputs.
  Handle-like source ids (C2 NEW-2, S0) never appear in a label; the source's publisher display name does (K10), or "a public
  ArcGIS publisher" when none is recorded.
- **L-7 Publication gate first.** An entity the gate withholds (P32.5, `policy/src/policy/eligibility.py:169-206`) has no label
  and no node; claims that reference it are withheld too (`:209-228`). Surfaces say "some relationships are not shown pending
  publication review" without naming or counting Part VIII withholdings.

### 3.2 Derivation per semantic kind (templates are agent-drafted; coverage from §1.2)

`{place}` = the finest K4 jurisdiction display name the entity is placed in (place → county → state → country), else omitted
from the label and shown as "place not recorded" in the descriptor. `{source}` = the source's display name (K10), never its id.

| kind | label (first rule that yields a value) | descriptor line | coverage today | example (illustrative) |
|---|---|---|---|---|
| organisation (`organization` table) | 1. `cached_canonical_name` (`source_name`) → 2. "Organisation (name pending review)" only on internal surfaces; public: not shown (L-7) | "{role summary} · {place} · named by {n} source(s)" | 973 / 973 named | "Washington State Department of Transportation" · "Operates 1,705 cameras · Washington · named by 1 source" |
| agency programme (`data_driven`) | 1. agency name parsed from the key (`key_name`) → 2. "Agency in EFF Data Driven #{hash}" | "ALPR programme recorded by EFF Data Driven (2016–17 records) · {place}" | 200 / 200 | "Austin Police Department" · "ALPR programme recorded by EFF Data Driven (2016–17 records)" |
| agency × technology (`atlas`) | "{agency} — {technology in words}" (`key_name`) | "Atlas of Surveillance record · {place}" | 4,756 / 4,756 | "Austin Police Department — face recognition" |
| Flock portal (`flock_portal`) | "{slug words, state token upper-cased} — Flock transparency portal" (`slug_name`) → "Flock transparency portal {slug}" | "Agency portal published by Flock Safety · state from portal address: {ST}" | 1,528 (1,498 with a state token) | "Abington MA PD — Flock transparency portal" |
| camera / site (`traffic_camera`) | 1. resolved `camera_name` (`source_name`) → 2. "{technology class} camera · {roadway} · {place}" (`derived`) → 3. "{technology class} camera #{hash} · {source}" (`fallback`) | "{technology class} · operated by {operator} (per {source}) · {place}" | name 43,339; roadway 24,606; operator 232,627; place: ≈ 227k of 232.6k placeable by K4's point-in-polygon (K4 §0) | "Traffic camera · I-35 at 6th St · Austin" |
| OSM node (`osm`) | 1. `description` → 2. "{camera_type/asset_type} camera · {manufacturer} (OSM tag) · {place}" → 3. "Surveillance camera, OSM node {id}" | "Mapped on OpenStreetMap · operator tag: {operator_stated or 'none'}" | 665 | "ALPR camera · Flock Safety (OSM tag) · Tulsa" |
| procurement notice | 1. `title` → 2. "{notice_type} by {buyer} · {posted_date}" → 3. "Procurement notice {external_id} · {buyer}" | "{source} · {technology keyword or 'not classified as surveillance-related'}" | title 2,287; buyer 5,376; dated 4,265 | "Contract notice by City of Austin · 2026-08-14" |
| contract | 1. "{buyer} – {seller} contract · signed {signed_date}" → 2. "Contract {external_id} · {buyer}" | "{source} · value as recorded · {place}" | buyer 1,871; seller 652; dated 652 | "Contract · Ville de … – Société … · signed 2025-03-14" |
| grant / funding instrument | 1. `program_name` → 2. "{funder} award to {recipient} · {award_date or period}" | "{source} · {amount as recorded}" | program 200; parties 1,079; dated 1,051 | "{funder} award to HOMELAND SECURITY, ARIZONA OFFICE OF · {award date}" |
| legislative bill | "{bill_identifier} ({jurisdiction} {session}) — {bill_title}" | "{status} on {bill_status_date}" | 308 / 308 | — |
| legal instrument / CCOPS ordinance | 1. `citation`/`ordinance_citation` → 2. "{instrument_type} · {jurisdiction} · effective {effective_from}" | "{enacting_body} · constrains {technology}" | 39 | — |
| agenda item | "Agenda item · {body/tenant} · {meeting date}" → "Agenda item #{hash} ({platform})" | "{source} · matched terms: {content_term}" | 1,364 (no title claim) | — |
| accountability event | "{event_type} · {organisations} · {event_date}" | "{source} · {epistemic status}" | 4 | — |
| records request | "Records request to {target_agency} ({platform})" — never the requester | "{status} · {response_date}" | 1 | — |
| country record (`jurisdiction`) | country name from the K4 registry | merges into the K4 country dossier (no entity page) | 195 | — |
| source | registry display name (K10) | — | 220 | — |
| person | **none** — no page, node, label or slug | — | 0 public | — |

**Disambiguation (deterministic).** Within (kind, release), if two entities share a label, append `· {place}`; if still equal,
append `· {source}`; if still equal, append `#{hash4}`. Test: no two public entities of a kind share a full display label
(SIG-UI-D23). Today this touches ≥ 11,588 site records (§1.1).

**"Possibly the same".** Where normalised names match across kinds (170 Data Driven agencies ↔ Atlas; §1.2), pages show
"SIG has not resolved whether these records describe the same organisation" with links — never a merge, never combined counts
(H-8; D-K2-7).

### 3.3 Stable, readable URL keys

```
/entity/<type>/<name-slug>--<hash>/
type      = org | agency | atlas | portal | notice | contract | grant | bill | policy | event | request
            (sites stay at their T0 record path; places → /dossier/…; sources → /sources/<id>/)
name-slug = K11 §3 slug rules (ASCII-fold, [a-z0-9]+ tokens, no scheme prefixes) over the display label,
            plus "-<K4 display slug of the state>" when placed (e.g. -usa-tx); cut at 56 characters on a token boundary
hash      = Crockford base32 of sha256(canonical UUID text), 7 characters (35 bits), extended by one character on a
            collision within the slug registry; frozen once issued and never reissued
```

- **Measured headroom (K31):** over all 251,019 entities, the first 8 hex digits of sha256(UUID) collide 7 times and the first
  10 collide 0 times; 7 base32 characters (35 bits) should therefore collide about once (inference: n²/2³⁶ ≈ 0.9) and the
  extension rule handles it.
- **The hash is authoritative; the slug is cosmetic.** Any `/entity/<type>/<anything>--<hash>/` 301s to the canonical URL.
- **Redirects** (one generated nginx include per release, like K4 §8 and K11 §3; lands with G3 REL-03b):
  `/id/<type>/<uuid>` (SIG-IDENT-031) → 302 to the current URL · rename → 301 · merge (`merged_into`, SIG-IDENT-032) → 301 to
  the survivor · split → 300 choice page · withdrawal → 410 T0 tombstone · re-typing (L1 NEW-5 fix: an `agency` page
  becoming an `org` page) → 301.
- **Registry:** `sig.slug-history/1` in the release (§6.5). The UUID stays the canonical identity (ENT-6).

### 3.4 Part VIII specifics

- Procurement `seller` literals can name sole proprietors: the partner-identity rules refuse a person-shaped name as an
  *entity* but keep it as a text claim ("When in doubt the partner stays text", `resolution/src/resolution/partner_identity.py:31-33,
  258-263`), so **GX-01 runs the person-name screen over literal party values before any label, node or slug is made from
  them** (R-8).
- Flock portal material: only the organisation-level facts; never audit rows, officer names or search reasons (§43.2a,
  SIG-PUB-003a–c).
- No label may be formed from coordinates finer than the published precision (§19.4), and no label carries a street address
  of a private registrant (I3 NEW-1 hazards).

---

## 4. Entity pages

### 4.1 Page types and routes (K0 registry)

| route | type | content | built by |
|---|---|---|---|
| `/entity/<type>/<slug>--<hash>/` (+ `/s/<pub>/…` snapshot) | **T1** | the readable entity page (§4.2) | Astro, from `sig.entity-page/1` |
| `/entity/…/index.json` | data | the JSON twin: page data incl. the 1-hop neighbourhood (§6.2) | exporter |
| `/entity/…/relationships/<relation>/<n>/` | T1 | full paginated lists (100 rows) for groups over 50 rows | Astro |
| `/r/<pub>/c/<comp>/entity/<type>/<uuid>/` | **T0** | the citable record with J3's per-claim provenance anchors | exporter (`release_pages.py`, extended from sites to every published kind) |
| `/graphs/`, `/graphs/<overview>/`, `/graphs/<overview>/<state>/` | T1 | static SVG overview + adjacency table + downloads (§5) | Astro + exporter |
| `/explore/` | **T2** | the interactive explorer (§5.3) | Preact + sigma island |
| `/network/` | — | 301 → `/explore/?v=2&overview=access` (the static page's content moves to `/graphs/access/`) | nginx |

### 4.2 Anatomy (every section has a typed empty state, SIG-TIME-012)

| # | section | contents | data source |
|---|---|---|---|
| 1 | **Header** | label (H1), descriptor, type, label basis note, place chain (K4 `jkey`), release stamp (G3), review status "Not yet independently reviewed" (J3 §5.2), "possibly the same as …" links | label registry; K4 registry |
| 2 | **Summary** | 3–8 plain sentences from counts: "Operates 1,705 cameras (per the WSDOT 511 registry, undated)"; "Named as buyer in 320 procurement notices (City of Austin procurement portal)" — every number a J3 `<Figure>` with a pointer | twin |
| 3 | **Identifiers and crosswalks** | `sig:<type>:<uuid>`, URL key, record id in each source (parsed connector key, shown as "record id in {source}"), external ids (UEI, FIPS/GEOID, Wikidata QID, OSM node, ISO), link to the crosswalk export (SIG-IDENT-033) | `entity_identifier`, `entity_identity_key` |
| 4 | **What SIG records** | claims grouped by predicate (ENT-1): resolved value; **resolution status, support, agreement, currency as four separate fields** (SIG-UI-004); sources; observed and valid dates; directness with "default, not assessed per claim" while D2/R3 are defaults (H-6); competing values as a range (SIG-UI-009); each claim links to its T0 anchor `#claim-<id>` (J3 panel) | statements file (J3 TX-08a) + resolutions |
| 5 | **Relationships** (ENT-3/GRA-1) | one table per relation, direction in words ("operates" / "operated by", "bought from" / "sold to", "configured access to"); the three access kinds never merged (SIG-UI-024). Columns: counterparty (label, link), role, date + date kind, currency, support, source(s), evidence link. Groups over 50 rows show grouped counts (by place, type, year) + the first 50 + "all N" link + CSV | twin |
| 6 | **Access** ("who can reach this agency's data / whose data it can reach") | access-path closures with hop lists and per-hop evidence (SIG-UI-025), live vs historical, ≤ 3 hops publishable, speculative beyond (SIG-RECON-049/050); degree-only facts as sentences ("Shared with 851 agencies — partners not named (SIG-INGEST-043c)") | GX-07 |
| 7 | **Graph** | a static SVG 1-hop ego (≤ 50 nodes, sectors per relation, deterministic radial layout, every node an `<a href>`), caption and legend; "Open in the explorer" (`/explore/?v=2&focus=<key>&hops=1`). The relationships table *is* its long description | exporter (Python) |
| 8 | **Disagreement** | contradiction records, dissenting claims, coordinate conflicts (5,290 subjects, C3), and ER uncertainty ("possibly the same") | contradiction, resolution |
| 9 | **Timeline** | dated events: award/signed/start/posted/effective/sunset/bill status/event dates, edge observation dates, first/last seen per source (K5 re-sightings); undated items listed apart as "undated" | twin |
| 10 | **Map snippet** | for entities with located subjects (operators, sites): a static SVG of counts by place (K6's generator), with ODbL attribution when OSM-derived; else "location not recorded" | K6 |
| 11 | **Related** | dossiers (K4 keys), sources (K10), research tasks (K11 handles), watch items (K7), documents (K8) | registries |
| 12 | **Downloads** | this entity's statements (per compartment and licence, ADR-106), relationships CSV/JSON, the JSON twin | J3 TX-10 |
| 13 | **Cite** | release-pinned citation (`/s/<pub>/entity/…`, G3/J3 TX-13a), SIG id, "Cite this relationship" per row | G3 |
| 14 | **Technical details** | UUID, API URLs (labelled "live, not a citation", K0 §5.2), T0 record link | — |

Print: T0 in print (K0 §4.10): the SVG ego and the timeline print; tables print in full up to 200 rows, then "N more at <URL>".

### 4.3 Which kinds get pages first, counts and sizes

| wave | kinds | pages (spine counts, before gating) | why first |
|---|---|---:|---|
| **E1** | organisations 973 · Data Driven agencies 200 · Flock portals 1,528 | **≈ 2,700** | they are the network's nodes and the operator's example (the U-003.11 UUID is a Data Driven agency, K11) |
| **E2** | keyword-matched notices 1,414 · DECP contracts 652 · grants 1,079 · bills 308 · legal instruments 30 · CCOPS 9 · events 4 | **≈ 3,500** | supply, funding and governance overviews need them |
| **E3** | Atlas agency × technology 4,756 (pages per agency name ≈ 4,100) · Legistar contracts 1,219 · agenda items 1,364 (as K7 watch items) | ≈ 4,100–6,700 | after K4 placement and a relevance rule; agenda items are owned by K7 |
| — | 1,967 unclassified portal notices | rows on buyer pages only | relevance unknown (NEW-7) |
| — | 232,628 cameras + 665 OSM nodes | T0 record pages (exist) gain derived labels and operator links | K1 owns the map feature view |

**Sizes (inference from §6 measurements):** T1 HTML ≈ 20–60 KB raw, 5–12 KB brotli (inside the 150 KiB document budget);
twin median ≈ 0.4–2 KB gzip, max ≈ 10–30 KB for aggregated high-degree organisations; ≈ 420 paginated list pages (the OSM
"operator" alone would need ≈ 269 until NEW-2 is fixed). E1 + E2 ≈ 6.2k pages → ≈ 26k objects per release with twins, T0
records and lists; ≈ 0.3–0.6 GB; ≈ $0.13 in writes per release at K0's per-object rate; build + 10–15 min (K4's "≤ 5 min per ≈ 3k
Astro pages").

---

## 5. The graphs

### 5.1 Principles

- **G-1 Entity first, graph as a view** (K12a GRA-1). Every edge drawn is a row in some entity page's relationship table.
- **G-2 No national hairball** (SIG-UI-021). "Global" = a *set* of overviews, each ≤ 3,000 nodes, aggregated by construction
  (K0 D-K0-6), each drilling down to entity egos (SIG-UI-022).
- **G-3 Evidenced edges only.** Degree-only facts are node attributes (SIG-INGEST-043c); closures are labelled paths, never
  new edges; "possibly the same" is a note, never an edge.
- **G-4 Descriptive, not analytic, until SIG-IDENT-030 passes.** Counts of evidenced relationships with the ER disclosure;
  no centrality, "hub", "most connected" ranking or labelled communities (D-K2-2). Build-time community detection may position
  nodes but is never shown as a finding.
- **G-5 Licence compartments stay separate** (ADR-106): overview data files are per compartment; the explorer composes them
  on the client like the map's per-compartment tiles; the rendered SVG is the produced work with every licence line.
- **G-6 Release-pinned** (K0 I-10). Every overview names its release, as-of and sources; positions carry "position has no
  geographic meaning; nearby nodes share relationships".

### 5.2 The catalogue

| id | question it answers | nodes → edges (today, measured) | aggregation when large | size (columnar gzip, §6.3) | depends |
|---|---|---|---|---|---|
| **O0 types** | "What does SIG hold, by kind, and how do kinds connect?" — the global map of the record, gaps included (e.g. 0 product and 0 policy entities recorded — L2's Q011 output, read) | ≈ 24 kinds → ≈ 60 predicate edges with counts | none | ≈ 3 KB | GX-05 |
| **O1 supply** | "Who sells surveillance technology to whom?" | buyers 432 + vendors 780 (keyword-matched notices) + 200 Data Driven agencies → Vigilant + 9 OSM manufacturer tags → ≈ 1.4k nodes, ≈ 1.6k edges | per buyer, collapse degree-1 vendors into "N other suppliers"; technology facet; state pages | ≈ 43 KB | GX-04 relevance, GX-05b, D-K2-5 |
| **O2 access** | "Who can search whose data?" | today 131 → 130 (configured access, historical) + degree attributes on 185 agencies | Flock scale (I8): 917 → 6,849 / 474,184 edges → **state × state matrix** (≤ 56 × 56 cells, weighted, the SIG-UI-021 matrix view) + per-agency egos grouped by state and type; never node-link nationally | today ≈ 5 KB; matrix ≈ 25 KB | GX-07, I8 |
| **O3 funding** | "Who funds whom?" | 19 funders → 684 recipients; 703 nodes, 752 edges | none needed | ≈ 22 KB | GX-05b |
| **O4 operators** | "Who runs the cameras, where?" | 139 operator strings + 21 organisations × places (55 declared; states/counties after K4) ≈ 200 nodes | by state; counties on drill-down | ≈ 12 KB | NEW-2 fix, JUR-02 |
| **O5 governance** | "Which laws and ordinances govern which technologies where?" | 308 bills + 39 instruments/ordinances + bodies + jurisdictions + technologies ≈ 420 nodes, ≈ 700 edges | by jurisdiction | ≈ 15 KB | GX-05b |
| **O7 adoption** | "Which agencies use which technology, by state?" | Atlas 4,756 agency × technology records (3 technologies) | a star with 3 hubs is uninformative → **state × technology matrix** + agency lists | ≈ 10 KB (est.) | JUR-02 placement of Atlas agencies, I8 |
| (O6 accountability) | events ↔ organisations | 4 → 6 | folded into O0/O5 until it grows | — | — |

Every overview has three forms from one file: `/graphs/<id>/` (T1: SVG + adjacency table paginated ≤ 100 rows + CSV/JSON per
compartment), `/graphs/<id>/<state>/` (single-facet no-JS pages, ≤ 56 per overview), and `/explore/?v=2&overview=<id>` (T2).

### 5.3 Interactions

| interaction | JS (T2 `/explore/`) | no-JS equivalent |
|---|---|---|
| **Open** | overview or `focus=` ego drawn into the reserved box that already holds the static SVG (K0 NEW-3 fix) | the static SVG + table |
| **Search to node** | K3's typeahead shards filtered to kinds present; picking an absent entity loads its ego | GET search → entity page |
| **Expand** | click/Enter on a node fetches its twin (`/entity/…/index.json`, ≤ 50 items per relation + counts); ≤ 10 expansions and ≤ 3,000 nodes on canvas, then "open the entity page for the full list" | the entity page's relationship tables |
| **Filter** | kind; relation (three access kinds as separate toggles, SIG-UI-024); currency (current · aging · stale · historical · undated); year range; source (mirrors grouped, P15); jurisdiction; technology; compartment | per-state pages; other facets named in a `<noscript>` notice with links (K0 §4.4 option 2) |
| **Path** ("how is X connected to Y?") | graphology shortest path (+≈ 19 KB after the action, inside K0's 60 KiB post-action budget) over the loaded overview or the two entities' component files (§6.4); access questions use only composing edges (SIG-RECON-049); hop list with per-hop evidence; ≤ 3 hops publishable, beyond labelled speculative; "no path within 3 hops in SIG's evidence as of release X" is a typed answer, never "not connected" | entity page "Connections within 2 hops" list (via-node shown; nodes above 500 relationships skipped as via-nodes, disclosed) |
| **Inspect edge** | edge panel: relation sentence, four epistemic fields, date + kind, currency text, sources (→ `/sources/<id>/`), each supporting claim (→ T0 anchor with J3 panel), binding state wording, contradictions, "Cite this relationship" | the relationship row's evidence link |
| **Inspect node** | node panel: label, descriptor, counts, neighbours as buttons (keyboard), "Open entity page" | entity page |
| **Cite this view** | snapshot URL `/s/<pub>/explore/?v=2&…` + static equivalent link (K0 §4.5) | page permalink |

**URL state (`sig.workspace-state/2`, K0 §4.5) — K2 uses** `overview`, `focus`, `hops`, `edge`, `expand`, and the common
`jurisdiction`, `technology`, `source`, `collection`, `kind`; **K2 proposes adding** `path=<key>~<key>`,
`currency=<class>…` and `years=<from>-<to>` (for UXK0-5).

**Keyboard and accessibility** (K0 §4.9): Tab order filters → search → node list → canvas; the node list is a sortable table
(label, kind, place, relationship count — descriptive); arrow keys move between a node's neighbours in the panel; Escape closes
panels and returns focus; `prefers-reduced-motion` → precomputed layout, no animation; every canvas feature is a focusable list
item; symbols carry a second channel (dash = historical, hollow = undated; SIG-UI-005).

**Budgets** (K0 §4.3, T2 graph): initial JS ≤ 120 KiB (sigma + graphology 37.8 KB + Preact 5.4 KB + app ≤ 60); per overview or
expansion ≤ 200 KiB (measured ≤ 132 KB at the 3k/10k cap); Lighthouse mobile ≥ 0.90; CLS ≤ 0.05.

---

## 6. Data contracts

All files are release artifacts recorded in the descriptor (G3 descriptor v2), per compartment where they carry
compartment-licensed facts (ADR-106), and built from the export's one snapshot.

### 6.1 `sig.entity-label/1` — `labels/<compartment>.jsonl`

`{entity_id, sig_id, kind, url_type, label, descriptor, label_basis, label_source_id, place_jkey, slug, hash, url,
disambiguator, component_id, part8: pass|fallback}`. ≈ 250 B/row → ≈ 63 MB raw, ≈ 10 MB gzip for 251k entities
(inference). Feeds K3 shards, K1 popups, K11 handles, the API.

### 6.2 `sig.entity-page/1` — `/entity/…/index.json`

`{key, label, descriptor, kind, place, identifiers[], summary[], claims[{predicate, envelope{status, support, agreement,
currency, rationale}, values[], sources[], claim_ids[]}], relations[{relation, direction, access_kind, count, by_place{},
by_year{}, items[≤50]{key, label, kind, date, date_kind, currency, support, sources[], claim_ids[≤3]}, more}],
access{closures[], degree_only[]}, contradictions[], timeline[], related{}, downloads[], cite{}}`. Measured shape
(§16 local computations): 1 neighbour ≈ 0.35 KB gzip, 10 ≈ 0.7 KB, 50 ≈ 1.8 KB.

### 6.3 `sig.graph-overview/1` — `graph/<overview>/<compartment>.json` + `…/overview.svg`

Columnar: `dict` (predicates, sources, kinds, currency classes, places) and parallel arrays `nodes{id, l, t, j, x, y, n}`,
`edges{s, t, p, n, y, cur, src}`; positions precomputed at build (deterministic seed; a BSD-licensed Python layout, **not**
the `igraph` package present in `pylock.toml`, which is GPL-2.0-or-later — the ticket confirms the licence); no claim ids
(fetched on click). Measured (synthetic shapes at real counts, §16): 131/130 → 4.6 KB · 703/752 → 21.9 KB · 1,422/1,591 → 43.1 KB · 3,000/10,000 → **132.5 KB** gzip (a row-per-object
encoding of the same 3k/10k was 368 KB, over budget). Build fails if an overview exceeds 3,000 nodes without an aggregation
rule (SIG-UI-D30).

### 6.4 `sig.graph-components/1`

`component_id` per entity (in the label registry) and one file per component of ≤ 3,000 nodes (largest measured: 344 in the
organisation projection; 1,912 in the all-procurement projection). Path search loads at most two component files.

### 6.5 `sig.slug-history/1`

`{hash, uuid, url_type, slug, from_pub, to_pub, status: current|renamed|merged|split|withdrawn, target}` → the nginx redirect
include (G3 REL-03b).

### 6.6 Costs (monthly; inference from K0 §5.3 unit prices)

| item | 10k explore sessions | 100k |
|---|---|---|
| explorer transfer (≈ 0.25 MB assets + ≈ 0.2 MB data first view) | ≈ 4.5 GB → ≈ $0.5 on GCS | ≈ $5.4 (≈ $0 on R2) |
| entity pages (≈ 10 KB brotli each) | negligible | ≈ $1 |
| per-release writes (≈ 26k objects) | ≈ $0.13 per release | same |
| storage (+0.3–0.6 GB per retained release) | ≈ $0.01 | same |
| **total incremental** | **≤ $2** | **≤ $10** |

### 6.7 API needs (within K0 §5.2)

**None new for pages or graphs** — both are static release files. For API parity (G3 REL-05, J3 TX-15), `/v1/entity/…` should
return the shared `label`, `label_basis` and a capped `relationships` block (in and out) so that an organisation is not an empty
"complete" record (NEW-5); `/v1/search` returns shared labels (K3). Explore surfaces never read live-spine routes (I-10).

---

## 7. Honesty rules (binding; each has a test in §8)

- **H-1** No UUID or connector key as a label (L-2).
- **H-2** Every edge and relationship row states: relation in words, direction, access kind, date + date kind or the word
  "undated", currency as text, the four epistemic fields separately, source names, and an evidence link.
- **H-3 Historical and undated are visible and never present-tense.** Dash + "historical"; hollow + "undated". Headlines,
  summaries and the "current" filter exclude them; a closure through a historical edge is a *historical path*
  (SIG-RECON-049 rule 4). The Data Driven edges read "recorded 2020-01-28 from 2016–17 records (EFF Data Driven); historical"
  once L1 NEW-10 fixes the date semantics — until then, "recorded 2020-01-28; the data may be older".
- **H-4 Degree is not a network.** "Shared with N agencies — partners not named" is a node attribute (SIG-INGEST-043c).
- **H-5 Derived labels disclose their basis** (L-3).
- **H-6 Provisional evaluation is disclosed.** Model-labelled evaluations (L1 NEW-9) read "evaluated by an AI model, not
  independently reviewed"; directness shows "default (D2), not assessed per claim" while NEW-3 stands; review status "Not yet
  independently reviewed" (J3 §5.2).
- **H-7 Contradictions visible.** Contested values as ranges with both sides (SIG-UI-009); contested edges marked in overviews;
  entity pages list contradiction records and coordinate conflicts.
- **H-8 ER disclosure at every count** (SIG-UI-023): "SIG has not merged organisations across sources; one agency can appear
  more than once" with "possibly the same" links; the live `/network/` copy claiming "deterministic identity resolution … exact
  … never an estimate" is withdrawn (NEW-6).
- **H-9 Typed absence** (SIG-TIME-012): not researched · no evidence found (with sources searched) · withheld pending review
  (no count for Part VIII withholdings) · not publishable under the source's terms.
- **H-10 Coverage is not density** (SIG-UI-018): each overview header names its sources and their period ("1 source: EFF Data
  Driven, 2016–17").
- **H-11 Mirrors count once** (P15): an edge "from 2 sources" never counts DeFlock and OSM separately.
- **H-12 Source is not operator:** a source attribution never renders as an operating organisation (NEW-2).
- **H-13 Relevance is disclosed:** a procurement notice appears in O1 only with its matched technology; others are listed on the
  buyer's page as "not classified as surveillance-related" (NEW-7).

---

## 8. Draft requirements (provisional ids for K13/T1; K0 used SIG-UI-D01…D10)

| id | requirement | acceptance |
|---|---|---|
| SIG-UI-D20 | No public surface MAY render a UUID, connector key or source id as a label, heading, node text, link text or table cell outside an "Identifiers" block. | crawl of `dist` + overview `l` fields: 0 matches for the UUID and `^[a-z_]+:[^ ]+:` key patterns in `h1–h3`, `a`, `td`, SVG `text` |
| SIG-UI-D21 | Every entity MUST have exactly one label from `sig.entity-label/1`, identical on entity page, T0 record, overview, typeahead, map popup and API. | parity test over a 500-entity stratified sample |
| SIG-UI-D22 | Every non-source label MUST display its basis. | template test per `label_basis` |
| SIG-UI-D23 | Within (kind, release) no two public entities MAY share a full display label. | uniqueness check in the exporter |
| SIG-UI-D24 | Labels and slugs MUST pass the person-name screen; person entities MUST have no page, node, label or slug. | golden tests incl. sole-proprietor literals |
| SIG-UI-D25 | Entity URLs MUST follow §3.3; the hash MUST never be reissued; rename/merge → 301, split → 300, withdrawal → 410, `/id/<type>/<uuid>` → current. | redirect fixtures; slug-history replay |
| SIG-UI-D26 | Entity pages MUST contain the §4.2 sections with typed empty states, within T1 budgets and JS-off parity. | `nojs-parity.spec.ts`; section presence test |
| SIG-UI-D27 | Every relationship row and edge MUST show H-2's fields. | DOM test per row; overview schema test |
| SIG-UI-D28 | Historical and undated relationships MUST be excluded from present-tense text and from the default "current" filter, and MUST be visibly marked. | copy lint + filter test on the Data Driven fixture |
| SIG-UI-D29 | Degree-only facts MUST NOT be drawn as edges. | schema test: no edge with predicate `sharing_partner_degree` |
| SIG-UI-D30 | Each overview MUST have ≤ 3,000 nodes, per-compartment data files, a static SVG, an adjacency table and a download. | exporter build check; `/graphs/<id>/` crawl |
| SIG-UI-D31 | `/explore/` state MUST round-trip through `sig.workspace-state/2` incl. `path`, `currency`, `years`; "cite this view" yields the snapshot URL. | workspace spec |
| SIG-UI-D32 | Path answers MUST list every hop with evidence, publish ≤ 3 hops, label longer paths speculative, and type "no path". | fixture graph with 2-, 3-, 4-hop and disconnected pairs |
| SIG-UI-D33 | No centrality, hub ranking or labelled community MAY ship before SIG-IDENT-030's gates pass or an ADR waives them; every count carries the H-8 disclosure. | grep of templates for ranking copy; disclosure test |
| SIG-UI-D34 | From any edge or relationship row, the J3 provenance panel of each supporting claim MUST be reachable in ≤ 2 actions with and without JS. | keyboard journey + no-JS crawl |
| SIG-EXPORT-D20 | The exporter MUST emit `sig.entity-label/1`, `sig.entity-page/1`, `sig.graph-overview/1`, `sig.graph-components/1`, `sig.slug-history/1`, per compartment, listed in the release descriptor. | release manifest check (G3 V4) |
| SIG-EXPORT-D21 | Network and overview edges MUST carry relation, date + kind, currency class, sources and supporting claim ids from the claims, never constants. | exporter unit tests; the `WEAKLY_SUPPORTED`/`evidence_count: 1` constants removed (`spine_export.py:1004-1005`) |

---

## 9. Acceptance journeys (agent walkthroughs at acceptance, not user research — P4/P5)

**J-1 Journalist: "Who supplies ALPRs to agencies in Texas and who can search them?"**
Path: `/search/` "Texas ALPR" → `/dossier/usa/tx/` (K4) → "Explore the graph for Texas" →
`/explore/?v=2&overview=supply&jurisdiction=iso3166-2:US-TX&technology=alpr`, then `overview=access`.
Expected answer, given today's data (after GX-01…GX-09, JUR-02, I8's Flock ticket and agency placement — Data Driven and
Atlas agencies carry no place today, K12b §4, so Texas membership needs a recorded placement, not a name guess): (a) supply — keyword-matched notices with
Texas buyers and their vendors, each dated; Data Driven: Texas agencies recorded as Vigilant users **(2016–17 records,
historical, unsupported)**; OSM manufacturer tags as "mapped by volunteers"; Atlas: "N Texas agencies use ALPR — vendor not
recorded" (typed); (b) access — Texas agencies in the LEARN pooled lookup (historical, weakly supported) with "shared with N
agencies (partners not named)"; 99 Texas Flock portals (state from the portal address) with their org-level shared-with lists
once I8 lands. **Pass:** every node named; every edge dated or "undated" and currency-labelled; every figure links to rows;
nothing historical phrased in the present tense; the same facts reachable with JS off through `/graphs/supply/usa-tx/`,
`/graphs/access/usa-tx/` and entity pages. **Today:** fails at every step (K12b §3.2 J1–J2).

**J-2 Journalist: "What is SIG's evidence for this vendor–agency link?"** From the Austin Police Department node (or its
entity page row) → edge "configured access to Vigilant Solutions (LEARN)" → edge panel: claim `configured_sharing_partner`;
source EFF Data Driven (→ `/sources/eff_data_driven/`); recorded 2020-01-28 (data 2016–17 per L1 NEW-10); currency HISTORICAL;
support WEAKLY_SUPPORTED; agreement; resolution UNRESOLVED with the rationale text; binding state `legacy_synthetic` in J3's
wording; the twin claims (`vendor`, `pooled_lookup_participation`); "Cite this relationship". **Pass:** ≤ 2 actions from graph
or page, JS on and off (SIG-UI-D34). **Today:** "1 evidence", not a link (K12b J4).

**J-3 Advocate: "Who runs the cameras in Austin and what did the city buy?"** `/entity/org/city-of-austin-transportation-and-public-works-usa-tx--…/`
(1,006 cameras, map snippet, undated) and `/entity/org/city-of-austin-usa-tx--…/` (buyer in 320 notices, all listed as "not
classified as surveillance-related" until the relevance rule classifies them), each with "possibly the same organisation as".
**Pass:** both pages reachable from `/dossier/usa/tx/austin…` and from search; no claim that they are one body.

**J-4 Organizer: "Is Acworth PD still sharing with Vigilant?"** (the operator's U-003.11 UUID). The entity page shows the
historical edge, the degree-only fact where one is recorded, and the K11 task `T-usa-ga-acworth-share-pd-…` with its records-request draft.
**Pass:** the answer reads "SIG's only evidence is historical (EFF Data Driven); SIG does not know whether this is current".

**J-5 Researcher: "Give me everything behind this graph."** `/graphs/supply/` → per-compartment CSV/JSON of nodes and edges
+ statements pointers; recomputed counts match the page (G3 V6). **Pass:** byte-level reproduction from the release.

**J-6 Keyboard / screen-reader user.** Complete J-2 using only the node list, panels and tables. **Pass:** axe clean in the
interaction states; no focus trap; Escape returns focus.

---

## 10. Round-11 ticket outline

Sizes: **S** ≈ half a fresh-context run, **M** one run, **L** split a/b at T3.

| key | title | size | scope | depends |
|---|---|---|---|---|
| **GX-01** | Shared label derivation + label registry | M | `labels` module in a package exporter and API both import (candidate: `policy`); §3.2 templates, disambiguation, basis, Part VIII screen incl. literal parties; `sig.entity-label/1`; site and T0 record labels ("Unnamed deployment" retired); API `label` from the module | K11 slug function (share it); K4 registry (`{place}` falls back to "place not recorded" until JUR-02) |
| **GX-02** | `/network/` label, date and evidence fix (first republish) | M | node labels from GX-01; edges carry predicate, `observed_at` + kind, source, currency, claim ids (SIG-EXPORT-D21); degree as attribute; remove the "deterministic ER … exact" copy; historical marking | GX-01; L1 NEW-10 fix (1970 dates, `ongoing`) in the same wave; G2 honesty wave |
| **GX-03** | Entity URL keys, slug history, redirects | S | §3.3; `sig.slug-history/1`; nginx include; `/id/<type>/<uuid>` | GX-01; G3 REL-03b |
| **GX-04** | Procurement relevance rule for graphs | S | derived relevance from `matched_keyword`, products/CPV/NAICS where present; unclassified notices shown only as buyer-page rows (H-13) | D-K2-5; I8 (classification of new sources) |
| **GX-05** | Entity data contract (`sig.entity-page/1`) | L — **05a** organisations, agencies, portals + relationships + degree-only; **05b** notices, contracts, grants, bills, instruments, events + timeline + contradictions + related | exporter; per compartment; publication gate; T0 record builder extended to these kinds | GX-01, GX-03; J3 TX-08a (statements); K5 DSRC (first/last seen); JUR-02 (related dossiers, 05b); **D-K2-1** before publication |
| **GX-06** | Entity pages (T1) | L — **06a** template, header, claims, relationship tables, typed absence, downloads, cite; **06b** static SVG ego, timeline strip, map snippet, print | Astro `/entity/**`, list pages | GX-05; UXK0-1, UXK0-4 (`<sig-table>`, `<sig-cite>`); J3 TX-13a; K6 SVG generator (shared); K14 tokens |
| **GX-07** | Access closures + degree-only facts | M | `inference/access_paths.py` at build per entity; hop lists, per-hop evidence, live vs historical, ≤ 3 hops; "shared with N" sentences | GX-05a; L1 NEW-10; D-K2-2, D-K2-3 |
| **GX-08** | Overview builder | L — **08a** O0 types, O1 supply, O3 funding, O4 operators + `/graphs/**` static pages; **08b** O2 access (Data Driven now, Flock matrix after I8), O5 governance, O7 adoption, components index | Python layout (deterministic, BSD), columnar files per compartment, SVG, adjacency tables, per-state pages, 3k cap check | GX-04, GX-05; NEW-2 fix (O4); JUR-02 (O4, O7); I8 Flock edges (O2 at scale) |
| **GX-09** | `/explore/` T2 app | L — **09a** Preact + sigma island in a reserved SSR box, overview loading, node and edge panels → provenance, URL state, cite view, `/network/` 301; **09b** expansion, filters, search-to-node, path finder, keyboard list | K0 budgets; axe on interaction states | GX-08a; UXK0-2, UXK0-5, UXK0-6; K3 shards |
| **GX-10** | K2 acceptance | S | J-1…J-6 as agent walkthroughs (labelled), SIG-UI-D20 crawl, budgets, parity, a11y; readout for K13 | all above in scope |

**Order and waves.** Wave 1 (first product republish): GX-01 → GX-02 (+ L1 NEW-10). Wave 2: GX-03, GX-04, GX-05a → GX-06a →
GX-07. Wave 3: GX-05b → GX-06b, GX-08a → GX-09a. Wave 4 (after I8/JUR-02): GX-08b → GX-09b → GX-10.

**Merged or consumed (P9):** K12b NEW-1/NEW-2/NEW-4/NEW-5 → GX-02/GX-05/GX-08/GX-09; K0 NEW-1 (82.8 % unlabelled) → GX-01;
K12b idea I-01 (entity pages) → GX-05/06; I-04 ("who can access what") → GX-07/O2; I-05 (date and currency everywhere) → H-2/H-3.
Not owned here: organisation ER (L1 NEW-12 → L3/F5), entity typing (L1 NEW-5 → F5 PKG-11), sharing-seam dates (L1 NEW-10),
Flock share-list extraction (I8), the allow-disposition tool (G2 NEW-1 / F-282).

---

## 11. Operator decisions needed

| id | decision | recommendation |
|---|---|---|
| **D-K2-1** | How do the 969 review-flagged organisations become publishable? Under P32.5 every organisation label and all 42,488 organisation edges are withheld (NEW-1). | (a) an operator batch review in degree order — **50 reviews unlock 96.5 % of edges** — through the G2 allow tool; plus (b) an ADR rule auto-allowing organisations matched to an authoritative public registry (Census of Governments, SAM UEI, Wikidata QID), with the person-name screen always applied and the basis shown; (c) the rest stay withheld with typed absence |
| **D-K2-2** | SIG-IDENT-030 ("no network-analytics surface before the ER gates pass") while U-008 rules out independent labellers | ship **descriptive** views (evidenced edges, counts with the ER disclosure); no centrality, rankings or labelled communities until L3 either passes the gates or an ADR waives them; remove today's centrality statistic |
| **D-K2-3** | Degree-only sharing data | node attribute sentences only (SIG-INGEST-043c); confirm |
| **D-K2-4** | Flock portal shared-with lists (474,184 edges) as organisation-level `configured_access` claims | yes, organisation level only, after a §43.2a/P8 screen (no operator ids, search reasons or audit rows), decided with I8 and E-stream |
| **D-K2-5** | Supply relevance | exclude unclassified procurement from O1; show it on buyer pages as "not classified" |
| **D-K2-6** | URL scheme and page waves | adopt §3.3 and waves E1 → E2 → E3 |
| **D-K2-7** | "Possibly the same" wording for unresolved same-name entities | adopt H-8's text; never merge or add counts |

---

## 12. Risks

| id | risk | mitigation |
|---|---|---|
| R-1 | Guilt by association: a named graph reads as accusation | relation wording in words, evidence on every edge, typed absence, no rankings |
| R-2 | Naming organisations known only by name (SIG-ONTO-013) | D-K2-1; publication gate; dispute link on every page |
| R-3 | Label churn breaks citations | hash authoritative and frozen; 301 history |
| R-4 | Historical data read as current | H-3 as a test (SIG-UI-D28); default filter "current" excludes historical and undated |
| R-5 | Irrelevant contracts inflate the vendor graph | GX-04, H-13 |
| R-6 | Duplicate agencies read as different agencies, or wrongly merged | "possibly the same", never merge without ER |
| R-7 | Build time and object count growth | waves; per-release write cost ≈ $0.13; G3 incremental upload |
| R-8 | Person names inside literal party values (sole proprietors) | GX-01 screen over literals before any label or node |
| R-9 | SIG-IDENT-030 breach | D-K2-2; SIG-UI-D33 |
| R-10 | Licence mixing in graph files | per-compartment files, composed on the client (ADR-106) |
| R-11 | OSM "operator" star dominates any operator view | NEW-2 fixed before O4 ships |

---

## 13. Interfaces

| row | what K2 needs / gives |
|---|---|
| K0 | page types, budgets, kit, URL state v2 (K2 adds `path`, `currency`, `years`), Preact migration |
| K1 | the map popup uses GX-01 labels and links to T0 records and operator pages; K2 uses K1/K6 static map snippets |
| K3 | typeahead shards carry GX-01 labels and descriptors; search results link to entity pages |
| K4 | `{place}` and related dossiers need JUR-01/02; per-state `/graphs/…/<state>/` use K4 display slugs |
| K5 | first/last seen per source feed the timeline |
| K6 | dossier network embeds reuse GX-06b's SVG ego and GX-08 overview renderers scoped to a jurisdiction |
| K7 / K8 / K10 / K11 | watch items, documents, sources and tasks link to entity pages; K11's handle grammar shares GX-01's slug function |
| J3 | T0 record provenance panel, statements files, citation block, `<Figure>` pointers |
| G3 | release descriptor entries, `/s/<pub>/` snapshots, nginx includes, V4/V6/V11 checks |
| G2 | allow-disposition tool (F-282) for D-K2-1; the honesty wave carries GX-02 |
| L1 / L2 / L3 | L1 NEW-5 typing, NEW-10 sharing dates, NEW-12 organisation ER; L3 decides the SIG-IDENT-030 path and review disclosure |
| I8 | Flock share-list claims and organisation resolution; Atlas vendor and place claims |
| K13 | page templates, requirements and ticket merge |

---

## 14. New findings (`findings/incoming/K2.csv`)

| id | sev | title |
|---|---|---|
| NEW-1 | S1 | All 969 referenced organisations are review-flagged, so P32.5's gate will withhold every organisation label and 100 % of the spine's 42,488 organisation edges; 50 reviews in degree order would unlock 96.5 % |
| NEW-2 | S2 | "OpenStreetMap contributors" is recorded as the `camera_operator` of 26,839 cameras (63.2 % of all organisation edges): a source modelled as an operator |
| NEW-3 | S2 | Directness and reliability on all 348,053 current party and sharing claims are the sink defaults D2/R3, so any per-edge directness display is a constant |
| NEW-4 | S2 | No current party, operator or sharing claim in the spine has a bounded valid period and only 500 of 42,488 organisation edges (1.2 %) carry any date, so per-edge currency cannot be computed for 98.8 % of edges |
| NEW-5 | S2 | Organisations hold no claims of their own and the API has no inbound-relationship view: `/v1/entity/organization/<WSDOT>` returns `facts: []` and `coverage.complete: true, evaluated: 0` for an operator of 1,705 cameras |
| NEW-6 | S2 | The live `/network/` ER disclosure says endpoints come from "deterministic identity resolution" and degree is "exact … never an estimate", while no organisation ER runs and 170 of 200 Data Driven agency names exactly match separate Atlas entities; SIG-IDENT-030's gate is unmet |
| NEW-7 | S2 | 1,967 city-portal procurement notices carry no surveillance-relevance claim; an unfiltered buyer→seller graph would put unrelated city contracts into the surveillance supply chain |
| NEW-8 | S2 | The API's fallback label is the raw connector key (`traffic_camera:camreg_austin_tx:austin_tx_traffic_cameras:1`, `atlas:Austin Police Department:face-recognition`), which embeds source ids and row ordinals |
| NEW-9 | S3 | Existing labels are not unique: 3,743 labels are shared by 11,588 released records (up to 504 per label) |

---

## 15. Limits

- Spine counts are the **live** database at 22:14–22:25Z, not the 09-27 release; the release will differ (C3 §1).
- `publication_disposition` is not readable by `sig_read_public` (K02 error), so how many of the 969 organisations already have
  an `allow` disposition is unknown; NEW-1's "100 %" assumes none, consistent with F-218/F-282 (no tool exists to record one).
- Label-template coverage counts subjects with ≥ 1 claim of the input predicate, not resolved values; resolution can reject some.
- Overview sizes use synthetic records shaped like the design at the measured node/edge counts; real labels may compress
  differently (± 30 %, inference).
- Flock share-list numbers are I3's, not re-measured. Relevance is keyword-based only. Same-agency matches are exact normalised
  strings (an inference about identity, not a resolution).
- No browser was used; UX claims about today's `/network/` rely on K12b and C2 captures.
- No human reviewed anything here (P4).

---

## 16. Reproduction

**Read-only spine queries** (runner mirrors L2's `tools/q.py` safeguards; results kept in the session scratchpad, not
committed; SQL sha256 prefixes from the query log):

| id | start (UTC) | rows | sql sha256 | what |
|---|---|---:|---|---|
| K00 | 22:14:01Z | 1 | `f6b93c4e21dc` | role `sig_read_public`, read-only on, 1 min timeout, tier 0 |
| K01 | 22:14:02Z | 21 | `9d2c0cace944` | entities by kind × label/party/place/date inputs |
| K02 | 22:14:46Z | error | `ac47884a2821` | `publication_disposition` not visible to the role |
| K03 | 22:14:47Z | 8 | `48f6da8bfda5` | entity-ref edges by predicate × kind, dated/valid counts |
| K05 | 22:14:58Z | 3 | `24ccb0cff9b5` | organisations by type/status/review flag, referenced, in-claims |
| K06 | 22:15:26Z | 40 | `fc4fb0e068d7` | top 40 organisations by degree |
| K07 | 22:15:40Z | 42,488 | `992ea01f102e` | entity-ref edge list (ids only) → `comp.py` components/degree |
| K08 | 22:15:42Z | 29 | `2dec2e0e6126` | literal party values: counts, distinct normalised values, dates |
| K09 | 22:16:28Z | 31,882 | `e68312da7587` | party nodes (entity id or md5 of normalised text) → `proj.py` |
| K10 | 22:16:43Z | 93 | `aea24155f5c7` | predicates per non-camera kind |
| K11 / K12 | 22:16:57Z | 3 / 20 | `8d24784c6c76` / `0b1523552158` | Atlas key structure; key shapes |
| K13–K18 | 22:18:05Z–22:18:48Z | — | `4cd7ad576b12` … `74a3a366a268` | org subject claims (0); derived facts; relationship rows; resolution support; validity kinds; directness/reliability |
| K19 / K31 | 22:21:07Z / 22:25:22Z | 1 / 1 | `b7dd45f79b66` / `bef9295b8df6` | UUID-suffix and sha256-prefix uniqueness |
| K20 | 22:21:14Z | 14 | `73bf21bda2ad` | evidence binding of edge claims |
| K22–K26 | 22:21:38Z–22:22:24Z | — | `e12a173e0132` … `eeadbb5dc893` | procurement relevance; keyword notices; supply projection; operator × jurisdiction |
| K27–K30 | 22:24:48Z–22:25:02Z | — | `f3823b020cd8` … `bf3023f0d90e` | same-name agencies; Flock slug state tokens |

(K04 listed table grants. K21 was a malformed aggregate that printed organisation names — institutions and businesses; its
result file was deleted and nothing from it is used.)

**Local computations:** `comp.py` (union-find components, degree percentiles, organisation projection over K07); `proj.py`
(buyer→seller and funder→recipient projections over K09); `supply.py` (keyword-matched subset, K24/K25); `size.py` / `size2.py`
(gzip -9 of synthetic overview and neighbourhood files at the measured counts: row-per-object 3k/10k = 368,042 B; columnar
131/130 = 4,593 B, 703/752 = 21,859 B, 1,422/1,591 = 43,068 B, 420/700 = 15,142 B, 326/2,704 = 25,291 B, 3,000/10,000 =
132,488 B; ego twins 1/3/10/50 neighbours = 352/405/699/1,842 B).

**Release reads (DuckDB 1.5.5 over C3's copy):** `count(distinct entity_id)`, empty-label and unplaced counts across
`parquet/*.parquet`; label duplicate counts; `sharing_edges.csv` composition; `network.json` shape.

**API GETs (22:17:36Z, 22:17:40Z, 22:17:42Z):** `/v1/entity/organization/01a0d751-0901-7a6c-8789-06bab8c7456e`,
`…/01a0dc4e-4122-79c4-8ae6-2ac0c65f3702`, `…/01a0f0e7-b2dd-7a09-ade7-8c96cb7cd3b2`; 200; bodies sha256 `7ffd4570…`,
`0fbf81cf…`, `3283a1ee…`.

**Code re-read for this note:** `exports/src/exports/spine_export.py:130-145, 990-1010`; `exports/src/exports/shaping.py:99-108,
1095-1101`; `api/src/api/store_pg.py:215-228, 630-670`; `db/src/db/claim_sink.py:116-119, 480-498`;
`policy/src/policy/eligibility.py:169-240`; `reconcile/src/reconcile/materialize.py:776-796`; `web/src/lib/network.ts:182-183`;
`web/src/pages/network.astro:49`; `web/src/islands/NetworkIsland.tsx:100-103`; `connectors/src/connectors/dot_511.py:660-675`;
`connectors/src/connectors/data_driven.py:24-55`; `inference/src/inference/access_paths.py:100-122`; `api/src/api/routes.py`
route list; spec lines 988-1008, 2495-2545, 4322-4356, 4935-4957, 5740-5765, 5835-5855, 6255-6285; ADR-106 §Decision.
