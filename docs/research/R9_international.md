# R9 — Internationalization: proving the SIG ontology generalizes beyond the U.S.

**Workstream:** R9
**Researched:** 2026-08-20
**Researcher:** R9 (international / ontology-generalization workstream)
**Outline sections covered:** §5 (all), §4.7, §8.1–§8.16 (stress-tested), §14 (licensing, international), §17 Stage 6, §18, §21 (International)
**Outline questions answered:** §20 Data access (international feasibility), §20 Identity (non-US identifiers), §20 Licensing (non-US license regimes), §20 Safety/privacy (GDPR-conditional publication)
**Confidence in this file overall:** high

---

## How to read this file

The outline asserts (§5) that "the data model should be international from the beginning" and names Technopolice
and a `sous-surveillance.net` → OSM import as the evidence. This workstream tested that assertion empirically.

The headline results:

1. **The Technopolice → OSM story is true, but the outline attributes it to the wrong actor.** The OSM import
   happened, was completed in **March 2025**, and moved roughly **18,000 cameras** — but it was executed by
   OpenStreetMap Belgium contributors importing `sous-surveillance.net`, *not* by Technopolice. Technopolice's own
   Technocarte is a **stale, 51-commune, polygon-level campaign map** that Technopolice itself now labels obsolete.
2. **The most valuable non-US structured sources are not activist datasets — they are government open-data
   obligations.** France's DECP (daily national procurement JSON, Licence Ouverte 2.0) and the UK's OCDS
   procurement APIs (Open Government Licence v3.0) are *better* than anything SIG can get in the U.S. for the
   Contract/Procurement entity (§8.10). Internationalization is, counter-intuitively, a **data-quality upgrade**
   for parts of the graph, not only an expansion of scope.
3. **The U.S.-shaped parts of the ontology that actually break are jurisdiction, organization_type,
   acquisition_method, label/i18n, and the publication policy** — in that order of severity. §9 below specifies
   fixes for each.

Retrieval note: 70+ distinct retrievals were performed on 2026-08-20. Where a fetch failed (Cloudflare 403,
Overpass rate-limit, JS-only page), the failure and its exact mode are recorded as `INACCESSIBLE` with a fallback.

---

# Part A — Technopolice, La Quadrature du Net, and the French mapping ecosystem

### F9.1 — Technopolice is a campaign, not a database project

**Claim:** Technopolice is a La Quadrature du Net-adjacent activist campaign launched September 2019 to document
"Safe City" surveillance in French municipalities; its public surfaces are editorial (Villes, Entreprises, Forum,
Fuiter, Se mobiliser), not a queryable dataset.
**Status:** VERIFIED
**Evidence:**
- `https://technopolice.fr/` (fetched 2026-08-20, HTTP 200, 73,147 bytes). Manifesto text: *"La « Smart City »
  révèle son vrai visage : celui d'une mise sous surveillance totale de l'espace urbain à des fins policières.
  En septembre 2019, des associations et collectifs militants ont donc lancé la campagne Technopolice…"*.
  Navigation: `Accueil / Actu / Villes / Entreprises / Forum / Fuiter / Se mobiliser`. Contact
  `contact@technopolice.fr`.
- `https://data.technopolice.fr/` (2026-08-20) **redirects to** `https://technopolice.fr/` — the separate document
  repository the outline-era ecosystem referenced no longer resolves independently.
**Retrieved:** 2026-08-20
**Implication for the spec:** Technopolice must be modeled as an **evidence publisher / Tier D–E source**
(§9.1), not as a Tier C reviewed specialist dataset. Ingestion from Technopolice means scraping city dossier pages
and their linked documents, not consuming a feed.
**Outline delta:** CORRECTS §5.2 — the outline implies Technopolice "documented and mapped" a technology inventory
usable as a data source. Its mapping artifact is thin and deprecated (F9.3).

---

### F9.2 — Technopolice publicly declares its own map obsolete

**Claim:** The Technopolice `Villes` page carries an explicit obsolescence notice.
**Status:** VERIFIED
**Evidence:** `https://technopolice.fr/villes/` (2026-08-20, HTTP 200, 71,770 bytes), first paragraph verbatim:
*"Attention, l'organisation des militant.es Technopolice a changé ! Cette carte est désormais obsolète."*
The page then lists projects in prose: *"« Observatoire de la tranquillité publique » à Marseille, « Safe City » de
Thalès à Nice et à La Défense, portiques de reconnaissance faciale dans deux lycées de la région Sud,
vidéosurveillance intelligente à Toulouse, Valenciennes, dans les Yvelines ou dans les couloirs du métro à Paris,
capteurs sonores à Saint-Etienne, déploiement de drones à Istres, traceurs dans les rues de Lannion en Bretagne…"*
and notes *"La liste n'est bien évidemment pas exhaustive."*
**Retrieved:** 2026-08-20
**Implication for the spec:** Any Technopolice ingestion must attach a **source-level staleness flag** and must not
be used to generate negative claims (§9.4). The prose list above is nonetheless a high-quality **seed list of
Deployment candidates** (§8.5) for a French pilot: 12+ named communes with named technologies and, in several
cases, a named vendor (Thalès).
**Outline delta:** CORRECTS §5.2 and §21 (International) — both cite the Technocarte as a live resource.

---

### F9.3 — The Technocarte's actual data: 51 communes, polygon granularity, no device layer, Belgium empty

**Claim:** `carte.technopolice.fr` is a static Leaflet map whose data ships as four JavaScript asset files; the
French city layer contains **51 commune features**, the département layer **1**, the région layer **1**, and the
**Belgian layer is an empty object**. Features are commune *polygons* carrying a category list — there is no
individual-device (PhysicalAsset) layer at all.
**Status:** VERIFIED
**Evidence:** Fetched with `curl` + browser UA on 2026-08-20:
- `https://carte.technopolice.fr/` → HTTP 200, 6,884 bytes. `<title>Technocarte</title>`; Leaflet 1.x;
  base tiles `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` attributed to
  *"Contributeur·rices d'OpenStreetMap"*; `maxZoom: 12`; bounds `L.latLngBounds(L.latLng(52,-5.3), L.latLng(41.2,10))`.
- `https://carte.technopolice.fr/geo-data-cities-fr.js` → HTTP 200, 997,628 bytes, **51** `"type":"Feature"`
  occurrences. Variable naming is `var city_fr_<INSEE>` (e.g. `city_fr_01173` = Gex, `city_fr_06029` = Cannes-area,
  `city_fr_12145`). Sample property block:
  `{"name":"Gex","description":"Cette commune utilise le logiciel de vidéosurveillance automatisée « Briefcam ».","marker":[46.3425,6.0475],"categories":["vsa"],"url":"https://technopolice.fr/briefcam/"}`,
  geometry `Polygon`.
- `https://carte.technopolice.fr/geo-data-departements-fr.js` → HTTP 200, 20,075 bytes, 1 feature (`departement_fr_78`, Yvelines).
- `https://carte.technopolice.fr/geo-data-regions-fr.js` → HTTP 200, 116,445 bytes, 1 feature.
- `https://carte.technopolice.fr/geo-data-cities-be.js` → HTTP 200, **50 bytes**, entire content:
  `var typeCitiesBe = {\n};\nvar geoDataCitiesBe = [];`
- Category tallies across the 51 French communes: `vsa` 25, `drones` 14, `divers` 9, `police_predictive` 7,
  `cameras_parlantes` 4, `capteurs_sonores` 3, `rf` 2, `cameras_thermiques` 2.
- Deep-link URLs cluster on campaign pages: `technopolice.fr/briefcam/` ×12,
  `laquadrature.net/2020/04/01/covid-19-lattaque-des-drones/` ×6,
  `technopolice.fr/blog/la-police-predictive-progresse-en-france-exigeons-son-interdiction/` ×6, plus ~30
  one-per-city dossier links (`technopolice.fr/marseille/`, `/nice/`, `/toulouse/`, `/rouen/`, `/metz/`, …).
**Retrieved:** 2026-08-20
**Implication for the spec:** The Technocarte maps cleanly onto SIG as **Deployment claims at commune
granularity**, with `jurisdiction` = the INSEE commune code embedded in the variable name and `technologies[]`
from the `categories` array. It contributes **zero** PhysicalAssets. This is an argument for the outline's
`Claim` granularity field: SIG must be able to say "this source asserts capability X exists in jurisdiction Y"
without inventing a device.
**Outline delta:** CORRECTS §5.2 — the outline lists "CCTV; intelligent video; facial recognition experiments;
drones; thermal cameras; acoustic sensors; 'safe city' systems" as things Technopolice "documented and mapped."
The map covers 8 categories over 51 communes and contains **no CCTV/camera-location layer whatsoever**, and the
Belgian coverage the outline's "France and Belgium: Technopolice" heading implies is an empty file.

---

### F9.4 — The Technocarte's French technology taxonomy (verbatim), and no license statement

**Claim:** The controlled vocabulary is defined in one file, `meta-i18n-filter.js`; the site publishes **no**
license, terms of use, or attribution statement for the data.
**Status:** VERIFIED (taxonomy) / VERIFIED-NEGATIVE (license)
**Evidence:** `https://carte.technopolice.fr/meta-i18n-filter.js` (2026-08-20, HTTP 200) contains exactly:
```js
var filtersI18n = {
  cameras_parlantes: "Caméras parlantes",
  cameras_thermiques: "Caméras thermiques",
  capteurs_sonores:   "Capteurs sonores",
  divers:             "Divers",
  drones:             "Drones",
  police_predictive:  "Police prédictive",
  rf:                 "Reconnaissance faciale",
  vsa:                "Vidéosurveillance automatisée",
};
```
`https://carte.technopolice.fr/meta-types-filter.js` (2,214 bytes) builds one Leaflet `layerGroup` per key over the
four geo files. A grep of `technopolice.fr` for `licence|license|creative commons|CC BY|domaine public` returned
**no matches**.
**Retrieved:** 2026-08-20
**Implication for the spec:** Per CONVENTIONS rule 4, this is an **unlicensed source**. SIG may cite and link
Technopolice as evidence (fair-dealing/quotation), but must **not** redistribute the Technocarte GeoJSON as SIG
data without written permission. Record `license: unknown-no-statement` and `redistribution: not-permitted-pending-permission`.
**Outline delta:** EXTENDS §14.2 — source licenses as first-class metadata must include an explicit
`no-license-statement-found` value, distinct from `unknown` and from `all-rights-reserved`.

---

### F9.5 — Technopolice's mapping forum explicitly resolved in favour of OSM

**Claim:** The forum thread the outline cites is a live, 63-message, 18-participant, 22,900-view debate whose
dominant position is that surveillance mapping must be done *in* OSM, and which criticises `sous-surveillance.net`
for consuming OSM tiles without contributing data back.
**Status:** VERIFIED
**Evidence:** `https://forum.technopolice.fr/topic/405/cartographier-la-surveillance` and `.../62` (2026-08-20,
HTTP 200, 122,264 bytes). Thread header: *"Cartographie des caméras — 63 Messages, 18 Publieurs, 22.9k Vues."*
Key positions quoted:
- *"que les données soient liés à OpenStreetMap, dans le cas contraire le projet risque d'être non viable"*
- *"OSM c'est le monde entier, si un collectif ou une orga locale est moins active un moment pas grave"*
- On sous-surveillance.net: uses OSM for basemap but does not reciprocate; *"la cartographie semble s'être arrêtée
  en 2017"*; a contributor counters that *"il y'avait une file d'attente de 2 ou 3 ans dans la modération"*.
- Later pages are operational OSM support: contributors mapping cameras with **Vespucci** and viewing results on
  `https://sunders.uber.space/`.
**Retrieved:** 2026-08-20
**Implication for the spec:** §1.2 ("federation") and §5.1 (OSM as global substrate) are **confirmed by the most
mature non-US community's own conclusion**. SIG should not build a bespoke non-US device store; it should
reconcile against OSM and push corrections upstream, exactly as the outline says for DeFlock.
**Outline delta:** CONFIRMS §5.1 and §5.2.

---

### F9.6 — The sous-surveillance.net → OSM import is real, documented, and COMPLETE as of March 2025

**Claim:** There is a formal OSM import plan page; the import ran in two phases (Brussels pilot March 2020, full
import finalised March 2025) and moved **~18,000 cameras worldwide** from a ~20,000-camera source database.
**Status:** VERIFIED
**Evidence:** `https://wiki.openstreetmap.org/wiki/Import/Catalogue/sous-surveillance.net?action=raw`
(2026-08-20, HTTP 200, 7,583 bytes of wikitext). Verbatim schedule:
```
✔️ 10/2019 - Discussion with sous-surveillance.net and Openstreetmap Belgium.
✔️ 10/2019 - Proposition to sous-surveillance.net
✔️ 03/2020 - Import limited to Brussels in OSM (authorization granted)   [changeset 82207370]
✔️ 09/2020 - Authorization granted to import the full dataset
✔️ 09/2020 - Communication towards OSM France
✔️ 03/2025 - Finalized import in OSM - Around 18 000 cameras where imported worldwide
```
Other verified specifics:
- Source format: **GeoJSON FeatureCollection**; coverage "many cities in France, Belgium, Luxembourg and also with
  less importance few cities elsewhere in the world (Montréal, Seattle, Moscow and Minsk)."
- Scale framing: *"around 20 000 cameras mostly located in France and Belgium where OSM includes around 80 000
  cameras in the whole world."* (that 80k figure is from ~2019; see F9.9 for the 2026 figure).
- Executor: `User:Vucod` via dedicated account `User:VucodImport`, with support of OpenStreetMap Belgium.
- Tooling: Python/Jupyter conversion then JOSM;
  `https://gitlab.com/vucod/osm-import-sous-surveillance.net-brussels/-/tree/master`.
- Provenance of the **Brussels-phase** proposal: `https://lists.openstreetmap.org/pipermail/talk-be/2020-March/010946.html`
  (fetched 2026-08-20) — *"Soon, I will upload a subset of those cameras (only Brussels)… The full import may
  happen in the future if we get more permissions."*
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the **canonical worked example** of the outline's federation thesis: an
activist database with a moderation queue and a 2017 stall was resolved by migrating into a commons. SIG's
Stage-6 posture in any new country should be "find the local dataset, negotiate an OSM import, then reconcile
against OSM" — not "ingest the local dataset into SIG."
**Outline delta:** CONFIRMS §5.2's claim that an import occurred; **CORRECTS** the number and the attribution
(see F9.7).

---

### F9.7 — The outline's "~12,000 cameras" figure and Technopolice attribution are both imprecise

**Claim:** The outline says "A historical French `sous-surveillance.net` dataset of roughly 12,000 cameras was
imported into OpenStreetMap," inside a section titled "France and Belgium: Technopolice." Both the number and the
implied actor are off.
**Status:** PARTIALLY VERIFIED / CORRECTED
**Evidence:** The import wiki (F9.6) states ~20,000 in source and ~18,000 imported worldwide. The ~12,000 figure
appears in secondary summaries as the **France-only** subset. The import was carried out by `User:Vucod` with
**OpenStreetMap Belgium**, and the wiki page is categorised `[[Category:Import from Belgium]]`. Technopolice
appears nowhere in the import plan; the connection is that Technopolice's forum independently advocated OSM (F9.5).
**Retrieved:** 2026-08-20
**Implication for the spec:** When SIG cites precedent in its own documentation, the citation must carry the
import-plan URL and the ~18k/March-2025 figures. More substantively: **do not model this as "Technopolice data."**
The upstream identifier that survives in OSM is `ref:sous-surveillance_net`, which is the join key SIG should use.
**Outline delta:** CORRECTS §5.2 — number (12,000 → ~18,000 imported / ~20,000 source), completion date (absent →
March 2025), and actor (Technopolice → OSM Belgium / `User:Vucod`).

---

### F9.8 — The import's permission record is a one-line email — a licensing anti-pattern SIG must not repeat

**Claim:** The legal basis for relicensing ~18,000 activist-collected camera records under ODbL is an email
fragment reproduced on the wiki as `C'est ok pour le transfert.` with the sender address redacted.
**Status:** VERIFIED
**Evidence:** The `===Background===` section of the import wiki reads:
```
Link to permission:
extract from ******@sous-surveillance.net:
  C'est ok pour le transfert.
```
The `===OSM Data Files===` section reads literally `The OSM data file are available [???here???].` — i.e. the
processed import files were never linked. The `==See also==` section still contains the placeholder
`Email to the Imports mailing list (YYYY-MM-DD) … at [https://lists.openstreetmap.org/XXX]`.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's `EvidenceArtifact` and source-registry model must require, for every ingested
dataset, a **structured permission record**: grantor identity, grant date, grant scope (which fields, which
territory), grant instrument (URL or archived document hash), and the license the grant enables. A free-text
"we got an email" must be representable but must *downgrade* the redistribution flag to
`redistribution: asserted-but-unverifiable`.
**Outline delta:** EXTENDS §14.2 — the outline treats license as a metadata field; this shows it must be a
**small entity** with its own provenance, not a string.

---

### F9.9 — OSM's global surveillance layer is now 558,645 objects; ALPR tagging has exploded to 144,312

**Claim:** As of the 2026-08-20 taginfo snapshot, `man_made=surveillance` has 558,645 objects globally, and
`surveillance:type=ALPR` alone has 144,312 — up from the ~80,000 total cameras cited in the 2019-era import plan.
**Status:** VERIFIED
**Evidence:** taginfo API, `data_until: 2026-08-20T00:59:51Z`:
- `https://taginfo.openstreetmap.org/api/4/tag/stats?key=man_made&value=surveillance` →
  all **558,645**; nodes 557,900; ways 716; relations 29.
- `https://taginfo.openstreetmap.org/api/4/key/values?key=surveillance:type` → **116 distinct values**. Top:
  `camera` 371,941 · `ALPR` 144,312 · `gunshot_detector` 3,250 · `guard` 2,003 · `camera;radar` 255 ·
  `sensor` 104 · `AFR` 67 · `camera;guard` 65 · `camera;ALPR` 61 · `traffic` 49 · `ALPR;camera` 42 ·
  `webcam` 37 · `PTZ` 36 · **`flock safety` 29** · `SC511` 25.
- `key=surveillance` → **430 distinct values**: `public` 273,978 · `outdoor` 127,724 · `traffic` 22,093 ·
  `indoor` 12,743 · `yes` 3,877 · `camera` 3,560 · `private` 2,746 · `no` 2,496 · `webcam` 1,976 · `cctv` 847.
- `key=camera:type` → **140 distinct**: `fixed` 293,970 · `dome` 89,459 · `panning` 15,769 · `doorbell` 1,567 ·
  `panorama` 1,046 · `ALPR` 85 · `fixed;dome` 66 · `dome;fixed` 51.
- `key=camera:mount` → **676 distinct**: `pole` 116,698 · `wall` 100,362 · `ceiling` 17,623 · `street_lamp` 17,127 ·
  `building` 8,173 · `traffic_signals` 6,742 · `gantry` 2,359 · `traffic_signal` 1,417 (note the singular/plural split).
**Retrieved:** 2026-08-20
**Implication for the spec:** Two hard requirements. (a) SIG's OSM ingester must implement a **normalisation
layer with an explicit alias map** — `ALPR;camera` ≡ `camera;ALPR`, `traffic_signal` ≡ `traffic_signals`,
`dome;fixed` ≡ `fixed;dome` — and must **quarantine junk values** such as `surveillance:type=flock safety`
(a vendor name in a capability field) into a review queue rather than dropping or trusting them. (b) The
630+ long-tail values are exactly the "vocabulary drift" that motivates §8.4's vendor-independent Technology
entity; the mapping from OSM tag → SIG Technology must be a **versioned, reviewable crosswalk table**, not code.
**Outline delta:** EXTENDS §2 (OpenStreetMap) and §8.4 — the outline treats OSM tags as clean; they are not.

---

### F9.10 — Per-country OSM surveillance density: France leads the world, and it is an artefact of the import

**Claim:** France holds ~13.6% of all global `man_made=surveillance` objects, far out of proportion to population
or camera count, because of the sous-surveillance import.
**Status:** VERIFIED (5 countries) / INACCESSIBLE (rest, rate-limited)
**Evidence:** Overpass API (`https://overpass-api.de/api/interpreter`, `out count;` queries scoped by
`area["ISO3166-1"=<cc>][admin_level=2]`), 2026-08-20:

| Country | `man_made=surveillance` | of which `surveillance:type~ALPR` |
|---|---:|---:|
| France (FR) | **75,926** | 765 |
| United Kingdom (GB) | 15,627 | 1,359 |
| Netherlands (NL) | 12,004 | not queried |
| Australia (AU) | 3,969 | not queried |
| Brazil (BR) | 2,307 | not queried |
| **Global** | **558,645** (taginfo) | 144,312 (taginfo) |

DE, US, BE, CA, IN, ES, IT returned rate-limit errors from both `overpass-api.de` and the `overpass.kumi.systems`
mirror after ~12 successful queries. Fallback for a production ingester: use **Geofabrik country PBF extracts**
plus `osmium tags-filter`, not the public Overpass endpoint.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) SIG's coverage/incompleteness metrics (§7.1 Goal 6) must be **normalised per
jurisdiction and annotated with import provenance**, or France will look "well covered" and Germany "empty" when
the real difference is one 2025 changeset. (b) Do not architect OSM ingestion around Overpass; architect it around
scheduled PBF diffs. (c) The FR ALPR count (765) versus the GB count (1,359) versus the global 144,312 shows the
ALPR layer is overwhelmingly U.S./DeFlock-driven — the outline's ALPR-first Stage 2 does **not** transfer to
Stage 6 as-is.
**Outline delta:** EXTENDS §5.1 and §7.1 Goal 6.

---

### F9.11 — sous-surveillance.net is still online but effectively dormant

**Claim:** The site (SPIP CMS) resolves and serves content, but its visible activity is a press review whose most
recent item is May 2024, with items from 2013–2017 on the front page.
**Status:** VERIFIED
**Evidence:** `https://sous-surveillance.net/` → 302 to `https://www.sous-surveillance.net/`, HTTP 200,
23,270 bytes. Sections: `CARTE de la surveillance / REVUE DE PRESSE / PROJET`. Front-page items dated
*"mercredi 27 novembre 2013"*, *"mardi 24 septembre 2013"*, *"jeudi 9 mai 2024"* (VSA and the Olympics),
*"mardi 3 janvier 2017"*, *"dimanche 14 février 2016"*. Project blurb: *"une cartographie participative,
collaborative et accessible au plus grand nombre."* PGP key `0x9651304952C31F6B` published. `spip.php?page=projet`
returns HTTP 404 (the working path is the site's own menu link).
**Retrieved:** 2026-08-20
**Implication for the spec:** Treat `sous-surveillance.net` as a **historical upstream** reachable through the
`ref:sous-surveillance_net` key already in OSM, not as a live feed. This is a good test case for the outline's
§8.15 `EvidenceArtifact` + §9.2 observation-vs-validity-time separation: the camera observations are real but
their `survey:date` values are up to a decade old, and the import itself flagged anything older than 10 years
with `fixme="This may be disused"`.
**Outline delta:** EXTENDS §5.2.

---

### F9.12 — The import's translation table is a ready-made non-US field crosswalk

**Claim:** The wiki documents a complete source-field → OSM-tag mapping, including semantic conversions, which is
directly reusable as a template for SIG's per-source crosswalk artifact.
**Status:** VERIFIED
**Evidence:** From the import wikitext (2026-08-20):

| sous-surveillance field | OSM tag | Conversion rule (verbatim/paraphrased) |
|---|---|---|
| — | `man_made=surveillance` | added to every node |
| — | `surveillance:type=camera` | added to every node |
| — | `survey:date` | from the camera's submission date on the website |
| `apparence` | `camera:type` | `dome` kept; `radar` **not** kept but `surveillance:type` set to `ALPR`; `boîte`/`nue`/`encastre` → `fixed`, unless `camera:feature=motion`, then `panning` |
| `apparence=encastre` | `camera:mount=wall` | |
| `direction` | `camera:direction` | |
| `angle` | `camera:angle` | |
| `camera_zoom` | `camera:feature` | if true, add `zoom` |
| `camera_rotation` | `camera:feature` | if true, add `motion` |
| `op_type` | `surveillance` | value `private` converted to `outdoor` |
| `title` | `name` | |
| `op_name` | `operator` | |
| `id_camera` | `ref:sous-surveillance_net` | **upstream identifier preserved** |
| `description` | `description` | |
| `zone` | — | not imported (geographical area) |

Conflation rules: source camera <5 m from an existing OSM camera → excluded; 5–10 m → imported with
`fixme="This may be a duplicated camera"`; `survey:date` older than 10 years → `fixme="This may be disused"`.
Belgium estimates: ~92.5% direct import (~16k), ~7% excluded (~1k), ~0.5% flagged (~100). Changeset tags:
`description="Import of the sous-surveillance.net cameras"`, `source="sous-surveillance.net"`, `source:date=…`.
QA surface: `https://kamba4.crux.uberspace.de/`.
**Retrieved:** 2026-08-20
**Implication for the spec:** Three transferable requirements. (a) **Preserve upstream identifiers** as
namespaced refs — SIG's `PhysicalAsset.upstream_ids[]` (§8.6) should adopt the `ref:<source>` convention verbatim.
(b) **Distance-banded conflation with an explicit uncertainty band** (<5 m auto-merge, 5–10 m flag, >10 m new) is
an already-field-tested default for SIG's §11.1 camera reconciliation. (c) An **age-based staleness flag** is a
first-class output of ingestion, not a query-time computation.
**Outline delta:** EXTENDS §11.1 and §8.6 with concrete, precedented thresholds.

---

### F9.13 — La Quadrature du Net is the live French source, and it is publishing operational detail on LAPI right now

**Claim:** LQDN (`laquadrature.net`) is actively publishing 2026-dated investigations that contain exactly the
structured facts SIG wants — device counts by mobility class, operating agencies, retention periods, and the
names of the national backing databases.
**Status:** VERIFIED
**Evidence:** `https://www.laquadrature.net/` (2026-08-20, HTTP 200) front page carries, among others:
*"Loi RIPOST, quand Nuñez attaque : les « LAPI » ou la surveillance massive des déplacements"* (17 June 2026,
updated 18 June 2026), *"France Travail déploie un outil de profilage algorithmique à des fins de contrôle"*
(20 July 2026), *"Projet de loi SURE : main basse sur les données…"*. Site is multilingual: `FR EN ES DE`.
From the LAPI article (fetched 2026-08-20):
- **LAPI = Lecteurs Automatiques de Plaques d'Immatriculation** — the French ALPR term.
- Fleet: **~700 state LAPI devices** — **480 fixed**, **98 mobile**, **23 transportable** across police nationale,
  gendarmerie nationale and douanes; **douanes operate 175 additional devices**, targeting **200 by end-2027**.
- Central system: **STCL** (système de traitement centralisé de lecture des plaques), holding **>60 million plate
  photographs** at any moment; RIPOST would raise retention from **15 days to one year** (~700 million plates).
- Cross-referenced against **FOVeS** (fichier des objets et véhicules signalés) and **N-SIS** (Schengen).
- Legal basis: **Code de la sécurité intérieure**; RIPOST adds administrative (non-judicial) access, algorithmic
  movement analysis (art. 15 bis), and **conventions letting communes share municipal LAPI data with the State**.
**Retrieved:** 2026-08-20
**Implication for the spec:** This single article populates five SIG entity types at once — Deployment (§8.5),
PhysicalAsset counts by `mobility` (§8.6, and note the French three-way *fixe / mobile / transportable* split,
which the U.S. two-way fixed/mobile split cannot express), DataSystem (§8.7: STCL, FOVeS, N-SIS),
AccessRelationship (§8.8: commune→State conventions, administrative vs judicial access), and Policy (§8.11:
retention 15 d → 1 y). **`PhysicalAsset.mobility` must be an extensible vocabulary, not a boolean.**
**Outline delta:** EXTENDS §8.6 (mobility is not binary) and §21 — LQDN belongs in the International registry in
its own right, above Technopolice.

---

### F9.14 — Ma Dada is France's MuckRock, and it is bigger than the outline assumes any non-US FOI ecosystem to be

**Claim:** `madada.fr` is an Alaveteli-family public-records platform hosting **51,669 requests** against
**51,918 referenced public authorities**, with per-authority deep-link URLs and Atom feeds but **no complete API**.
**Status:** VERIFIED
**Evidence:**
- `https://madada.fr/` (2026-08-20, HTTP 200, 39,518 bytes): *"Parcourir les 51 669 demandes aux 51 918 autorités
  publiques"*; *"Ma Dada est un site associatif qui vous aide à demander des documents publics, dits
  « administratifs » (rapports, délibérations, contrats, factures, algorithmes, correspondances, etc.)"*;
  *"L'autorité dispose d'un mois pour vous [répondre]"*.
- `https://madada.fr/aide/api` (HTTP 200): *"Ma Dada n'a pas d'API complète pour l'instant, mais nous ajoutons
  graduellement des éléments dont l'usage se rapproche de celui d'une API."* Documented affordances: authority
  deep links `/new/<authority-slug>` with `title`, `default_letter`, `body`, `tags` parameters; **Atom feeds**.
  The page still contains the untranslated Alaveteli example `/new/liverpool_city_council`, confirming the
  codebase lineage shared with WhatDoTheyKnow.
- Technopolice ran a dedicated campaign on it: `https://technopolice.fr/blog/madada-exigeons-les-documents-de-la-technopolice/`
  and `https://www.laquadrature.net/2021/03/08/madada-exigeons-les-documents-de-la-technopolice/` (8 March 2021).
**Retrieved:** 2026-08-20
**Implication for the spec:** `EvidenceArtifact.acquisition_method` must carry a **jurisdiction-qualified FOI
value**, e.g. `foi_request` with `foi_regime: FR-CADA` / `US-FOIA` / `US-STATE-<code>` / `GB-FOIA` /
`GB-EIR` / `IN-RTI`, because the response deadlines, appeal bodies, and redaction obligations differ per regime
and SIG's task generator (§12) needs them. Ma Dada's Atom feeds are the integration point; the `tags` parameter
is how SIG-generated requests would be made discoverable back to the French community (§7.1 Goal 7).
**Outline delta:** EXTENDS §10 Phase 1F and §21 — Ma Dada is a first-class international analogue of MuckRock and
is absent from the outline entirely.

---

# Part B — French structured evidence sources (the real Stage-6 payload)

### F9.15 — DECP: a daily, national, machine-readable public-procurement feed under an open license

**Claim:** France publishes **Données Essentielles de la Commande Publique** as a daily JSON feed on
data.gouv.fr under **Licence Ouverte 2.0**, mandated by decree for *every* French public buyer. This is the
single most valuable international structured source found in this workstream.
**Status:** VERIFIED
**Evidence:** `https://www.data.gouv.fr/api/1/datasets/5df410e86f44413a91d34be3/` (2026-08-20, HTTP 200):
- title `API DECP`; organization **Agence pour l'Informatique Financière de l'État (AIFE)**;
  `license: lov2`; `frequency: daily`; `last_update: 2026-08-20T03:30:08Z` (i.e. this morning);
  **1,944 JSON resources** (one per publication day).
- Legal basis stated in the dataset description: the **arrêté du 22 mars 2019** relatif aux données essentielles
  (`https://www.legifrance.gouv.fr/loda/id/JORFTEXT000038318675`) obliges *"tous les acheteurs publics français
  (collectivités territoriales, ministères, hôpitaux publics, établissements publics, etc.) et toutes les
  autorités concédantes françaises"* to publish. **From 1 January 2024** publication moved to data.gouv.fr under
  the amended **arrêtés du 22 décembre 2022** (marchés: `LEGIARTI000048876437`; concessions: `LEGIARTI000048916375`).
  Also mirrored at `https://data.economie.gouv.fr/explore/?sort=modified&q=essentielles`.
- Downloaded and parsed `https://static.data.gouv.fr/resources/api-decp/20260818-013140/decp-18082026-034-0131.json`
  (1,715,577 bytes): top-level `{"marches": {"marche": [...1278 records...], "contrat-concession": [...]}}`.
**Retrieved:** 2026-08-20
**Implication for the spec:** See F9.16 for the field-level mapping. Strategically: the outline's §6.7
"procurement-to-deployment lifecycle" gap — which it treats as an unsolved U.S. problem requiring FOIA and
council-minutes scraping — is **already solved as a national open-data obligation in France**. Stage 6 in France
gives SIG a *higher-fidelity* Contract layer than Stage 1–5 will ever have in the U.S.
**Outline delta:** CONTRADICTS the implicit premise of §5 that the U.S. is the data-richest starting point. For
the Contract/Procurement entity specifically, **France is richer than the United States.**

---

### F9.16 — DECP maps 1:1 onto §8.10 Contract, and carries amendment history for free

**Claim:** Every field the outline specifies for `Contract` exists in DECP, plus a `modifications[]` array that
directly implements the outline's temporal requirements.
**Status:** VERIFIED
**Evidence:** Parsed record from the 2026-08-18 file (abridged, verbatim structure):
```json
{ "id": "2025kazvs0000000",
  "acheteur": { "id": "20009020700016" },           // buyer, SIRET
  "nature": "Marché",
  "objet": "Biodéchets - Collecte transport et traitement …",
  "codeCPV": "90523000",
  "procedure": "Appel d'offres ouvert",
  "lieuExecution": { "code": "08", "typeCode": "Code département" },
  "dureeMois": 12,
  "dateNotification": "2025-04-01",
  "datePublicationDonnees": "2025-04-04",
  "montant": 1000000,
  "titulaires": [ { "titulaire": { "typeIdentifiant": "SIRET", "id": "31483054800140" } } ],
  "modifications": [ { "modification": { "id": 49006,
        "dateNotificationModification": "2026-07-28",
        "datePublicationDonneesModification": "2026-08-17",
        "dureeMois": 1, "montant": 1 } } ],
  "source": "AIFE_ATLINE" }
```
Field frequency over all 1,278 records in that file: 28 fields present on 100% of records
(`id, acheteur, nature, objet, codeCPV, techniques, modalitesExecution, marcheInnovant, ccag, offresRecues,
attributionAvance, tauxAvance, typeGroupementOperateurs, sousTraitanceDeclaree, procedure, lieuExecution,
dureeMois, dateNotification, datePublicationDonnees, montant, typesPrix, formePrix, origineUE, origineFrance,
titulaires, considerationsSociales, considerationsEnvironnementales, source`), plus `modifications` on 463,
`idAccordCadre` on 73, `actesSousTraitance` on 5.

Mapping to §8.10:

| §8.10 `Contract` field | DECP field | Note |
|---|---|---|
| `buyer` | `acheteur.id` (SIRET) | resolves via SIRENE → INSEE commune SIREN (F9.24) |
| `seller` | `titulaires[].titulaire.id` (SIRET) | typed by `typeIdentifiant` |
| `amount` | `montant` | EUR |
| `signed_date` | `dateNotification` | plus `datePublicationDonnees` = observation time |
| `start_date` / `end_date` | `dateNotification` + `dureeMois` | end must be **derived**, not stored |
| `renewal_options` | `idAccordCadre`, `modifications[]` | framework-agreement linkage |
| `products` / `quantities` | `objet` (free text) + `codeCPV` | **no line items** — see F9.17 |
| `document` | — | **absent**: DECP has no document URL |
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) `Contract` must model **amendments as first-class dated sub-events**, not as a
mutated row — DECP proves the requirement is real (36% of records carry them) and the outline's §19.3
"time before overwrite" principle has a concrete schema consequence here. (b) `Contract.end_date` must be
**derivable-or-stated**, with a flag for which. (c) DECP carries **no document link**, so the DECP→EvidenceArtifact
edge is to the *record*, not a PDF; the PDF must be sourced separately (BOAMP/TED/Ma Dada). (d) The two-date
pattern (`dateNotification` vs `datePublicationDonnees`) is exactly §9.2's validity-time/observation-time split,
natively present — SIG should not collapse it.
**Outline delta:** CONFIRMS §8.10, §9.2, §19.3; EXTENDS §8.10 with `amendments[]` and a derived/stated flag.

---

### F9.17 — Surveillance procurement is findable in DECP via CPV codes, at meaningful density

**Claim:** Filtering DECP by CPV code and object-text keywords surfaces real vidéoprotection contracts with
buyer, amount, and geography.
**Status:** VERIFIED
**Evidence:** Keyword+CPV filter over the 1,278 records of the 2026-08-18 file yielded **38 candidate records**
(~3%). The cleanest true positive:
```
CPV 35125300-2 (Caméras de sécurité) | 50 754,79 EUR | acheteur SIRET 42882285202298 | dept 59 |
"La présente consultation a pour objet la fourniture et l'installation d'un système de vidéoprotection sur …"
```
Also matched: `CPV 79714000-2` (surveillance services) 2 330 000 EUR, and a cluster of `45xxxxxx` building-works
CPVs whose `objet` mentions security works — i.e. the filter has **false positives from generic construction
contracts**, and would have **false negatives** where a camera system is a lot inside a larger works contract.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG needs a **CPV → Technology crosswalk** as a versioned reference table
(`35125300` security cameras, `32323500` video-surveillance system, `35120000` surveillance & security systems,
`34970000` traffic-monitoring equipment, `79714000` surveillance services, `30216130` barcode/plate readers), and
must record `extraction_method: cpv_filter+keyword` and a **precision estimate** on the resulting Claims (§8.16
`confidence`, §9.3 explainable confidence). Contract→Deployment inference from procurement text must be a
*reviewable* Claim, never an automatic Deployment creation. This is the international instance of the outline's
§19.11 "contracted is not installed."
**Outline delta:** EXTENDS §8.16 and §19.11.

---

### F9.18 — Arrêtés préfectoraux: the strongest formal authorization record in France, but locked in 22,403 PDFs

**Claim:** French vidéoprotection systems require a **prefectural authorization valid for five years, renewable**,
issued after opinion of the **commission départementale de vidéoprotection**; those arrêtés are published in the
préfectures' *Recueils des Actes Administratifs*; and data.gouv.fr now publishes an **ODbL-licensed, weekly index
of 22,403 RAA PDFs** with direct URLs and département codes.
**Status:** VERIFIED
**Evidence:**
- Legal regime: Code de la sécurité intérieure, **Titre V Vidéoprotection, art. L251-1 à L255-1**; authorization
  chapter **L252-1 à L252-7**; procedure and commission **R252-1 à R252-17**. Authorization is granted for
  **five years and is renewable**; the arrêté designates which agents (police, gendarmerie, douanes, SDIS,
  police municipale) may receive images. (Légifrance section URLs
  `https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000025503132/LEGISCTA000025505402/` and
  `.../LEGISCTA000028285409/`; note `legifrance.gouv.fr` itself returned **HTTP 403** to direct curl —
  Cloudflare challenge — see F9.20 for the working bulk route.)
- Index dataset: data.gouv.fr **"Recueils des actes administratifs des préfectures"**, id `6a826c488feaf1584f1dba40`,
  `license: odc-odbl`, `frequency: weekly`, `last_update: 2026-08-17T09:59:11Z`. Description verbatim:
  *"Ce jeu de données recense les recueils des actes administratifs (RAA) publiés sur les sites internet des
  préfectures de département… regroupant dans un jeu de données unique des informations aujourd'hui consultables
  séparément sur le site de chaque préfecture."* Fields: `departement` (INSEE dept code), `titre`, `url`,
  `mise_a_jour`.
- Downloaded the CSV (`…/20260817-095910/raa-des-prefectures.csv`, 4,107,372 bytes): **22,403 data rows**,
  header `titre;url;departement;mise_a_jour`, delimiter `;`, BOM present. Sample row:
  `recueil-01-2026-001-recueil-des-actes-administratifs;https://www.ain.gouv.fr/contenu/telechargement/34196/238661/file/recueil-01-2026-001-recueil-des-actes-administratifs.pdf;01;2026-08-17T00:25:43.000Z`
  Only **33 rows** carry "vidéo" in the title — the arrêtés are *inside* the PDFs, not in the titles.
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the French analogue of "council minutes and contracts" (§2 Layer F) but with
**far better structure at the index level and far worse structure at the document level**. Stage-6 France requires
a PDF text-extraction + arrêté-segmentation pipeline. The payoff is exceptional: an arrêté préfectoral gives
SIG a **legally authoritative, dated, expiring authorization** naming the operator, the site, the number of
cameras, and the retention period — i.e. it populates Deployment, PhysicalAsset counts, Policy, **and** an
expiry date that drives §12 research-task generation ("this authorization lapses in 2027; is there a renewal?").
The U.S. has **no equivalent instrument**.
**Outline delta:** EXTENDS §8.11 substantially — see F9.30 for the `Authorization` entity this forces.

---

### F9.19 — CNIL délibérations, sanctions, mises en demeure and contrôles are all open data

**Claim:** The French DPA publishes its decision corpus as open data under Licence Ouverte, with bulk XML dumps.
**Status:** VERIFIED
**Evidence:** data.gouv.fr API query for CNIL (2026-08-20, 17 datasets under org **CNIL**):

| Dataset | License | Last update |
|---|---|---|
| Les délibérations de la CNIL | `fr-lo` | 2026-07-31 |
| Sanctions prononcées par la CNIL | `fr-lo` | 2025-05-05 |
| Mises en demeure prononcées par la CNIL | `fr-lo` | 2024-10-01 |
| Contrôles réalisés par la CNIL | `fr-lo` | 2024-10-18 |
| Plaintes reçues par la CNIL | `fr-lo` | 2026-05-19 |
| Marchés publics de la CNIL | `fr-lo` | 2026-05-22 |
| Les délibérations de la CNIL **vectorisées** (DINUM) | `lov2` | 2026-08-18 |

The délibérations dataset's resources are: format `xml`, *"CNIL: les délibérations de la Commission nationale de
l'informatique et des libertés"* → `https://echanges.dila.gouv.fr/OPENDATA/CNIL/`, plus a `dtd` resource →
`https://echanges.dila.gouv.fr/OPENDATA/DTD_LEGIFRANCE`. Frequency: monthly. Delibérations run from **1979**.
**Retrieved:** 2026-08-20
**Implication for the spec:** CNIL délibérations are the French counterpart of the outline's §8.14
`Incident / AccountabilityEvent` with `adjudicated` epistemic state, and of §8.11 `Policy` where the CNIL issues
binding *autorisations uniques* or sectoral frameworks. The `event_type` vocabulary in §8.14 must therefore admit
`dpa_decision`, `dpa_sanction`, `dpa_formal_notice` (mise en demeure), and `dpa_inspection` (contrôle) —
categories with no U.S. equivalent, since no U.S. body issues binding administrative privacy decisions against
police agencies. **A DPA decision is not a "lawsuit" and must not be flattened into one.**
**Outline delta:** EXTENDS §8.14's `event_type` and `alleged/confirmed/adjudicated` enumeration.

---

### F9.20 — DILA's open-data server is the working bulk route into all French legal text

**Claim:** `echanges.dila.gouv.fr/OPENDATA/` serves unauthenticated bulk archives of the entire French legal
corpus, including JORF, LEGI, BOAMP and CNIL — and is reachable when `legifrance.gouv.fr` is not.
**Status:** VERIFIED
**Evidence:** `https://echanges.dila.gouv.fr/OPENDATA/` (2026-08-20, HTTP 200, Apache directory index).
Directories present, with last-modified dates showing active maintenance:
`ACCO/ · AMF/ (2026-08-20) · ASSOCIATIONS/ · BALO/ · **BOAMP/** · BOCC/ · BODACC/ · CAPP/ · CASS/ (2026-08-17) ·
CIRCULAIRES/ · **CNIL/** (2026-07-31) · CONSTIT/ (2026-08-04) · DOLE/ · DTD_LEGIFRANCE/ · INCA/ · JADE/ (2026-08-19) ·
**JORF/** (2026-08-20) · JORFSIMPLE/ · KALI/ · **LEGI/** (2026-08-19) · RefOrgaAdminEtat/ · SARDE/ …`
plus a top-level `AVERTISSEMENT-Donnees_a_caractere_personnel.pdf` (verified HTTP 200, `application/pdf`,
15,921 bytes) — a **personal-data warning notice attached to the corpus itself**.
`…/OPENDATA/BOAMP/` contains `2026/`, `Documentation/`, `FluxHistorique/`, `Schemas/` and presentation PDFs.
`…/OPENDATA/JORF/` contains daily increments plus `Freemium_jorf_global_20250713-140000.tar.gz` (**1.6 GB**).
By contrast `https://www.legifrance.gouv.fr/` returned **HTTP 403** ("Just a moment… Enable JavaScript and
cookies to continue") to a browser-UA curl.
**Retrieved:** 2026-08-20
**Implication for the spec:** Record `legifrance.gouv.fr` web UI as `INACCESSIBLE (Cloudflare interstitial)` with
fallback **(a)** DILA bulk tarballs (no auth) and **(b)** the Légifrance API on the PISTE gateway (OAuth key
required — not tested here). More generally: **the existence of a DILA-published personal-data warning attached
to the legal corpus is direct evidence for F9.35's jurisdiction-conditional publication requirement.**
**Outline delta:** EXTENDS §10 and §21.

---

### F9.21 — BOAMP and TED are separate from DECP and cover different lifecycle stages

**Claim:** France has three overlapping procurement surfaces — BOAMP (national notices), TED (EU-threshold
notices), DECP (post-award essential data) — and SIG must ingest them as **different lifecycle events on the same
procurement**, not as duplicate contracts.
**Status:** VERIFIED
**Evidence:** BOAMP bulk at `https://echanges.dila.gouv.fr/OPENDATA/BOAMP/2026/` (F9.20). TED at
`https://ted.europa.eu` with the v3 search API (F9.22). DECP at data.gouv.fr (F9.15). DECP's own description
confirms it is the *post-award* "données essentielles" obligation with a 5-year publication duration.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's §8.10 Contract needs a **`procurement_stage`** discriminator
(`pipeline / prior_information / tender_notice / award_notice / contract_data / amendment / termination`) and a
**procurement-thread identifier** so that a TED tender notice, a BOAMP notice and a DECP award record about the
same purchase resolve to one procurement with multiple dated observations. OCDS already models this exactly
(`ocid` + `tag[]`) — see F9.26 — and SIG should adopt OCDS's shape rather than invent one.
**Outline delta:** EXTENDS §8.10 and §6.7.

---

### F9.22 — The TED API is open, unauthenticated, working, and already language-tagged

**Claim:** `https://api.ted.europa.eu/v3/notices/search` accepts anonymous POST queries and returns EU-wide
procurement notices filterable by CPV and date, with per-language links and **language-keyed buyer names**.
**Status:** VERIFIED
**Evidence:** POST to `https://api.ted.europa.eu/v3/notices/search` on 2026-08-20 with
`{"query":"classification-cpv=35125300 AND publication-date>=20260101", "fields":[…], "limit":8}` →
**HTTP 200**, 66,069 bytes, `totalNoticeCount: 410`, `timedOut: false`, `iterationNextToken` for paging.
First result verbatim (abridged):
```json
{ "publication-number": "1025-2026",
  "buyer-name": { "ron": ["SECTOR 3 AL MUNICIPIULUI BUCURESTI"] },
  "buyer-country": …, "publication-date": "2026-01-02+01:00",
  "classification-cpv": ["35125300","35125300"],
  "place-of-performance": ["RO321","ROU","RO321","ROU"],
  "links": { "xml": {"MUL": "https://ted.europa.eu/en/notice/1025-2026/xml"},
             "pdf": {"BUL": …, "DEU": …, "ENG": …, "FRA": …, /* 24 languages */ },
             "html": { /* 24 languages */ } } }
```
EU-wide 2026-YTD notice counts by CPV (each verified by a separate API call):

| CPV | Meaning | Notices 2026 YTD |
|---|---|---:|
| 35120000 | Surveillance and security systems and devices | **2,257** |
| 79714000 | Surveillance services | 1,143 |
| 32323500 | Video-surveillance system | 580 |
| 35125300 | Security cameras | 410 |
| 34970000 | Traffic-monitoring equipment | 389 |
| 30216130 | Barcode / plate readers | 135 |

**Retrieved:** 2026-08-20
**Implication for the spec:** (a) TED is a **turnkey EU-27 discovery layer** for the surveillance procurement
lifecycle — it alone would seed a pan-European Vendor/Product/Deployment graph. (b) `place-of-performance` uses
**NUTS codes** (`RO321`) and `buyer-country` uses ISO 3166-1 alpha-3 (`ROU`) — a *third* geographic code system
alongside INSEE and ISO 3166-2, reinforcing F9.31. (c) **`buyer-name` is a map from ISO-639-3 language code to a
list of strings.** This is the exact multilingual-label shape SIG needs (F9.34) and it comes from a production
EU system — SIG should copy it rather than design its own.
**Outline delta:** EXTENDS §21 International and §8.1 (organization names are language-keyed, not scalar).

---

# Part C — EU-level law and the EU AI Act database

### F9.23 — The EU high-risk AI database exists in law but is (a) deferred to December 2027 and (b) structurally excludes law enforcement

**Claim:** Article 71 of the AI Act mandates a public, machine-readable EU database of Annex III high-risk AI
systems — but registrations for **law enforcement, migration, asylum and border control** go into a **non-public**
section, and the Digital Omnibus regulation adopted in July 2026 pushed the whole Annex III obligation to
**2 December 2027**. It is therefore **not** a usable Stage-6 source.
**Status:** VERIFIED
**Evidence:**
- Article 71 text (`https://artificialintelligenceact.eu/article/71/`, `https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-71`,
  fetched 2026-08-20): Commission sets up and maintains the database; information *"shall be accessible and
  publicly available in a user-friendly manner… easily navigable and machine-readable"* — **except** information
  registered under **Article 49(4)** and **Article 60(4)(c)**, which is *"accessible only to market surveillance
  authorities and the Commission"* unless the provider consents. Art. 49(4) covers Annex III points 1, 6 and 7 —
  **biometrics, law enforcement, and migration/asylum/border control**. Personal data in the database is limited
  to *"names and contact details of natural persons"* responsible for registration.
- Digital Omnibus: **Regulation (EU) 2026/1744** — existence verified directly on EUR-Lex
  (`https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202601744`, HTTP 200, page title
  *"Regulation - EU - 2026/1744 - EN - EUR-Lex"*). Secondary sources (Gibson Dunn, Pinsent Masons, DLA Piper,
  Cloud Security Alliance, aiactblog.nl, all fetched 2026-08-20) concur: provisional Council/Parliament agreement
  7 May 2026, Council confirmation 29 June 2026, **published in the OJ 24 July 2026, in force 27 July 2026**;
  standalone **Annex III high-risk obligations deferred from 2 August 2026 to 2 December 2027**; Annex I embedded
  high-risk to **2 August 2028**; Article 50 transparency duties and Article 4 AI-literacy duty **unchanged**.
**Retrieved:** 2026-08-20
**Implication for the spec:** Do **not** design Stage 6 around the EU high-risk database. Record it as a
**scheduled future source** with `expected_availability: 2027-12-02` and `expected_coverage: excludes-law-enforcement`.
The negative finding is itself important: the outline's §22.1 thesis ("no master surveillance database") holds in
Europe too, and the EU explicitly legislated the surveillance subset *out* of the public register.
**Outline delta:** EXTENDS §5 with a hard negative — the most-cited "coming EU transparency source" will not
serve SIG's domain.

---

### F9.24 — AI Act Article 5 creates a genuinely new evidence type: the RBI authorization event

**Claim:** Real-time remote biometric identification for law enforcement is prohibited from **2 February 2025**
except in enumerated cases, each requiring **prior authorization by a judicial or independent administrative
authority**, **per-use notification** to the market surveillance authority and the DPA, and **annual Member State
reports to the Commission**, which publishes **aggregated annual reports**.
**Status:** VERIFIED
**Evidence:** `https://artificialintelligenceact.eu/article/5/` (2026-08-20). Art. 5(1)(h) exceptions: targeted
search for victims of abduction/trafficking/sexual exploitation and missing persons; prevention of a specific,
substantial and imminent threat to life or physical safety, or a genuine and present/foreseeable terrorist
threat; localisation/identification of a suspect of an offence punishable by **≥4 years** custodial sentence.
Art. 5(2): system may only confirm identity of a **specifically targeted individual**; necessity/proportionality
assessment on seriousness, probability, scale of harm. Art. 5(3): **prior authorization** by judicial authority or
independent administrative authority; **24-hour** emergency window with subsequent authorization; refusal ⇒
immediate deletion. Art. 5(4): **each use notified** to the relevant market surveillance authority and national
DPA. Art. 5(6)–(7): **annual national reports to the Commission; Commission publishes aggregated annual reports.**
Prohibitions applicable **2 February 2025**.
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG needs an **`Authorization` entity** distinct from both `Policy` (§8.11) and
`Contract` (§8.10). An authorization has: issuing authority, subject deployment, legal basis, grant date,
expiry date, scope limits (temporal/geographic/personal), and — crucially — an **outcome/validity state that can
be revoked or annulled retroactively** (see F9.29 for the French case where a court annulled an extension after
the fact). Article 5's aggregated annual Commission reports are a **future Tier-B structured source**
(country-level counts of RBI authorizations) worth registering now.
**Outline delta:** EXTENDS §8.11 — the outline's `Policy` object (`applies_to`, `effective period`, `policy_type`,
`text/source`) cannot express "authorized by X on date D for 5 years, subject to conditions C, annulled on date E."

---

### F9.25 — GDPR/LED and the French anonymisation duty make publication a jurisdiction-conditional act

**Claim:** French law **legally requires** anonymisation before online publication of administrative documents
containing personal data, and the EU DPA-guidance environment makes "publish the FOIA release as received" —
the standard U.S. practice — unlawful in France.
**Status:** VERIFIED
**Evidence:**
- **Article L312-1-2 CRPA**: documents and data containing personal data *"ne peuvent être rendus publics
  qu'après avoir fait l'objet d'un traitement permettant de rendre impossible l'identification de ces personnes."*
  Confirmed via CADA's own guidance page `https://www.cada.fr/administration/lanonymisation-des-donnees`
  (fetched via search corpus 2026-08-20) and CNIL's `guide-open-data.pdf`. Exceptions are fixed by decree.
- CADA itself: `https://www.cada.fr/` (HTTP 200, 2026-08-20) — *"autorité administrative indépendante chargée de
  veiller à la liberté d'accès aux documents administratifs… Le recours devant la CADA constitue un préalable
  obligatoire à tout recours contentieux."* (i.e. **CADA appeal is a mandatory precondition to litigation** — a
  procedural difference from U.S. FOIA that SIG's task generator must encode.)
- CADA's advice corpus is **itself open data**: `https://cada.data.gouv.fr/` → redirects to
  `https://www.data.gouv.fr/explore/cada` (HTTP 200, 2026-08-20) — *"Recherchez parmi les avis et conseils rendus
  par la Commission d'accès aux documents administratifs… depuis les années 1980."*
- DILA attaches `AVERTISSEMENT-Donnees_a_caractere_personnel.pdf` to its entire legal-corpus open-data tree (F9.20).
- EDPB **Guidelines 1/2024** on Article 6(1)(f) legitimate interests (adopted 8 October 2024) require a rigorous
  three-part test, that the right to object always be honoured, that processing be *necessary* (not merely useful)
  with no less-intrusive alternative, and reject *"vague or generic legitimate interest claims."*
**Retrieved:** 2026-08-20
**Implication for the spec:** SIG's publication policy **cannot be one global rule**. See F9.36 for the specified
model. Minimum: (a) an `EvidenceArtifact` acquired in France may need to be stored but **not served publicly**
until redacted; (b) officer/agent names appearing in an arrêté or a DECP record are personal data under GDPR and
their publication needs a jurisdiction-specific lawful basis and a documented balancing test; (c) the outline's
§13.4 "preserve source without overexposing sensitive contents" must become a **jurisdiction-parameterised
storage/serving split**, not an editorial guideline.
**Outline delta:** CORRECTS §13 — §13.2 "minimize personal data" and §13.4 are stated as global ethical norms;
in the EU they are **legal obligations with different thresholds per member state**, and §13.3's "treat exact
coordinates contextually" acquires a legal dimension (a camera location plus an operator name can be personal
data about the operator's premises).

---

# Part D — United Kingdom

### F9.26 — UK procurement is available as OCDS through two unauthenticated APIs under OGL v3.0

**Claim:** Find a Tender and Contracts Finder both expose Open Contracting Data Standard endpoints, no API key,
with an explicit machine-readable license field in the payload.
**Status:** VERIFIED
**Evidence:** Both fetched 2026-08-20 with browser UA:
- `https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages?updatedFrom=2026-08-01T00:00:00&limit=2`
  → HTTP 200, 16,585 bytes. `"version": "1.1"`, `"publisher": {"name":"Cabinet Office","scheme":"GB-GOR","uid":"D2"}`,
  **`"license": "http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"`**,
  `"publicationPolicy": "https://www.gov.uk/government/publications/open-contracting"`. Declares 10 OCDS
  extensions including the EU profile, amendment-rationale, budget-breakdown, contract-completion, documentation,
  pagination, suitability and the `cabinetoffice/ocds_uk_extension`.
- `https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search?publishedFrom=2026-08-01&stages=award&size=2`
  → HTTP 200, 606,766 bytes, same OGL v3.0 license string, 7 extensions.
- Sample release (verbatim, abridged): `{"ocid":"ocds-b5fd17-783f0291-…","id":"…","language":"en",
  "date":"2026-08-20T18:05:26+01:00","tag":["award"],"initiationType":"tender",
  "tender":{"classification":{"scheme":"CPV","id":"60000000",…},"items":[{"deliveryAddresses":[{"postalCode":"IP1 2BX"},…]}],
  "contractPeriod":{"startDate":"2026-09-03T01:00:00+01:00","endDate":"2029-07-31T23:59:59+01:00"}},
  "parties":[{"id":"GB-CFS-154927","name":"Suffolk County Co…"}]}`
- Coverage boundary, from `https://www.find-tender.service.gov.uk/Search` (HTTP 200): *"From 24 February 2025,
  both above and below threshold notices about new UK procurements will be published on this service, except
  below threshold in Scotland… For procurements that started before that, only above threshold notices are
  published here, usually over £139,688 including VAT."* Below-threshold pre-2025 England data remains on
  Contracts Finder (>£12,000, or >£30,000 outside central government).
- Ecosystem scale: `https://data.open-contracting.org/` (2026-08-20) — *"over 100 publishers from around the
  world"*, downloadable as JSON, Excel and CSV.
**Retrieved:** 2026-08-20
**Implication for the spec:** **SIG's `Contract` entity should be an OCDS profile, not a bespoke schema.**
Concretely: adopt `ocid` as the procurement-thread key; adopt `tag[]` as `procurement_stage` (F9.21); adopt
`parties[]` with `scheme`-qualified ids (`GB-CFS-…`, and France's SIRET) as the organization-identifier pattern;
adopt `classification.scheme = "CPV"`. This single decision makes 100+ countries ingestible with one adapter
and makes SIG interoperable with the entire open-contracting community. The UK's OGL v3.0 permits redistribution
with attribution — compatible with a CC-BY-style SIG output layer, and **not** viral like ODbL.
**Outline delta:** EXTENDS §8.10 with a concrete standard; EXTENDS §14 with a second, cleaner license regime
(OGL v3.0) alongside ODbL.

---

### F9.27 — The UK National ANPR Service is the best comparative case for a nationally governed ALPR system

**Claim:** The UK operates a genuinely national ALPR system (NAS) with a central data store (NADC), published
Home Office standards, and a 1-year retention rule — a governance structure with no U.S. federal equivalent.
**Status:** VERIFIED (documents) / PARTIALLY VERIFIED (numbers, secondary)
**Evidence:**
- `https://www.gov.uk/government/publications/national-anpr-standards` (2026-08-20, HTTP 200, 113,058 bytes):
  *"These documents relate to law enforcement automatic number plate recognition (ANPR) and the National ANPR
  Service (NAS). From: Home Office. Published: 24 January 2019. **Last updated: 29 July 2026**."* Publishes
  *"National ANPR standards for policing and law enforcement"* (**NASPLE**) in HTML and PDF (703 KB, 52 pages).
- Technical specification: `https://assets.publishing.service.gov.uk/media/675860c4e677f284d6cfc95f/NAS_Technical_Specs_V3.6+Final+December+2024.pdf`
  ("National ANPR Service Technical Specifications Version 3.6 Final", December 2024).
- Scale (secondary, ASD-Europe and Wikipedia, 2026-08-20): ~**11,000 cameras**; **~50 million** reads/day
  historically, **~90 million/day** in more recent NAS figures from England, Wales and Scotland forces; data
  collated centrally at the **National ANPR Data Centre (NADC)** with **1-year retention**.
- Procurement trail is visible: Find a Tender notices `061205-2025` and `040831-2024`, and a MOPAC decision
  "ANPR NAS management server" on `london.gov.uk`.
**Retrieved:** 2026-08-20
**Implication for the spec:** The UK is the clean test of §8.7 `DataSystem` and §8.8 `AccessRelationship` at
**national** scope. In the U.S., ALPR sharing is a mesh of bilateral agency-to-agency edges; in the UK it is a
**hub**: every force feeds one `DataSystem` (NADC) and draws from it. SIG's `AccessRelationship.scope`
vocabulary (`nationwide/statewide/local`) must therefore become **jurisdiction-relative** — "nationwide" means
something structurally different in a unitary state — and SIG needs an explicit `hub_and_spoke` vs `peer_mesh`
network-topology attribute on `DataSystem` (relevant to §6.6 and §22.4).
**Outline delta:** EXTENDS §8.7, §8.8, §6.6.

---

### F9.28 — CORRECTION: the UK Surveillance Camera Commissioner has NOT been abolished

**Claim:** Contrary to widely circulated 2023-era reporting, the Data (Use and Access) Act 2025 did **not**
abolish the Biometrics and Surveillance Camera Commissioner or repeal the Surveillance Camera Code of Practice;
the office is operating in 2026.
**Status:** VERIFIED (correction of an initially retrieved secondary claim)
**Evidence:** Initial searches surfaced 2023 reporting (IFSEC, Biometric Update, Open Rights Group briefing)
stating the DUA Bill would abolish the office. Direct verification contradicts this:
- `https://www.legislation.gov.uk/ukpga/2025/18/contents` (2026-08-20, HTTP 200, 144,281 bytes) — a full-text
  scan of the Act's section list for "surveillance" / "biometric" returns **only** the block
  *"Retention of biometric data — 126. Retention of biometric data and recordable offences · 127. Retention of
  pseudonymised biometric data · 128. Retention of biometric data from INTERPOL"*. There is **no** section
  abolishing the Surveillance Camera Commissioner and **no** repeal of the Protection of Freedoms Act 2012
  surveillance-camera provisions.
- `https://www.gov.uk/government/organisations/biometrics-and-surveillance-camera-commissioner` (2026-08-20,
  HTTP 200, live, not redirected to a "closed organisation" page) still lists as current publications the
  *Surveillance camera code of practice*, the *National surveillance camera strategy for England and Wales*,
  annual reports, DPIA guidance for surveillance cameras, a survey on law-enforcement use of uncrewed aerial
  vehicles, FOI responses dated **27 July 2026**, and a Commissioner's statement on live facial recognition
  consultation dated **24 February 2026**. A *"Biometrics Commissioner's valedictory report: 2024 to 2025"* was
  published 19 May 2026 (a personnel transition, not an abolition).
**Retrieved:** 2026-08-20
**Implication for the spec:** Two things. (a) The Surveillance Camera Code of Practice remains a live
`Policy`-type instrument that binds relevant authorities in England and Wales, and BSCC publications are a
usable Tier-B source. (b) Methodologically, this is a **worked example of why SIG needs contradiction as a
first-class state (§6.5)**: a large volume of credible secondary reporting asserts an abolition that the primary
legislative text does not contain. SIG must be able to hold "N sources say abolished, primary text says not"
without editorial collapse.
**Outline delta:** CONFIRMS §6.5 with a live example; adds BSCC to §21.

---

### F9.29 — UK live facial recognition is moving to fixed installations, which changes the PhysicalAsset model

**Claim:** The Met's LFR deployment shifted from vans to **static cameras mounted on existing street furniture**,
with a published pilot record.
**Status:** VERIFIED (secondary, Met press office)
**Evidence:** `https://news.met.police.uk/news/met-makes-one-arrest-every-35-minutes-during-live-facial-recognition-pilot-509256`
and `.../met-commissioner-to-announce-plans-to-introduce-lfr-into-crime-hotspots-across-the-west-end-510675`
(2026-08-20): pilot ran **October 2025 – March 2026** using *"static cameras mounted to existing infrastructure
such as lampposts"*; **24 separate operations**, **173 arrests**, **>470,000 people** passed the camera,
**1 false alert**; 61% of linked offences in Croydon. Plans announced for static LFR across the **West End and
Soho by end of year**, with the caveat that *"while these cameras are static, they will not be permanent in any
one location."*
**Retrieved:** 2026-08-20
**Implication for the spec:** This breaks a binary the U.S. model takes for granted. A `PhysicalAsset` here is
**physically fixed but administratively relocatable**, and the *deployment operation* (a dated, bounded event at
a named location) is the real unit of accountability — not the device. SIG needs `PhysicalAsset.mobility` values
beyond `fixed|mobile` (see also F9.13's *fixe/mobile/transportable*) **and** a `DeploymentOperation` concept:
a time-boxed activation of a capability at a location, with its own authorization, which is exactly what AI Act
Art. 5(3) authorizations (F9.24) and French arrêtés (F9.18) attach to.
**Outline delta:** EXTENDS §8.5 and §8.6 materially.

---

### F9.30 — WhatDoTheyKnow is blocked to automated access

**Claim:** mySociety's WhatDoTheyKnow API help page returns Cloudflare 403 to scripted requests even with full
browser headers.
**Status:** INACCESSIBLE
**Evidence:** `https://www.whatdotheyknow.com/help/api` fetched 2026-08-20 twice — once with a plain browser UA
(HTTP **403**, 5,611 bytes) and once with UA + `Accept: text/html,application/xhtml+xml,…` +
`Accept-Language: en-GB,en;q=0.9` (HTTP **403**, 5,740 bytes). Body: *"Just a moment… Enable JavaScript and
cookies to continue."*
**Retrieved:** 2026-08-20
**Implication for the spec:** Do not design UK FOI ingestion around scraping WhatDoTheyKnow. Fallbacks, in order:
(1) Alaveteli exposes **Atom/RSS feeds** per authority and per search (the same affordance documented on Ma Dada,
F9.14) — test those endpoints rather than the HTML; (2) request a **research agreement / bulk export** from
mySociety directly, which is their documented route for researchers; (3) treat individual request pages as
`EvidenceArtifact` URLs discovered via web search rather than enumerated. Record the 403 in the source registry
so the ingester does not retry blindly.
**Outline delta:** EXTENDS §20 "Data access".

---

# Part E — Other national and regional ecosystems (condensed findings)

### F9.31 — Belgium: a legally complete national camera register that the public cannot see

**Claim:** Belgium's *loi caméras* (21 March 2007) requires **every** surveillance camera to be declared; since
25 May 2018 declarations go to the police only, via a single national portal — which requires Belgian eID
authentication. The register is not public.
**Status:** VERIFIED
**Evidence:** `https://www.declarationcamera.be/` (2026-08-20) → HTTP 200 but immediately redirected to
`https://idp.iamfas.belgium.be/fas/XUI/?goto=…acr_values=urn:be:fedict:iam:fas:citizen:Level300…` — the Belgian
federal identity provider at citizen assurance Level 300. No anonymous access path. Legal basis: *"Loi du 21 mars
2007 réglant l'installation et l'utilisation de caméras de surveillance"*; since 25 May 2018 declaration is to
police services (no longer to the Commission de la protection de la vie privée) and is made electronically. The
controller's register must be made available **on request to the Data Protection Authority and police services** —
not to the public. `https://www.gegevensbeschermingsautoriteit.be/burger/thema-s/camerabewaking` returned HTTP 404
(site reorganised; the live theme is *"Camera's en uw privacy"*).
**Retrieved:** 2026-08-20
**Implication for the spec:** This is the sharpest available case for the outline's §7.1 Goal 6 (quantify
incompleteness) and §9.4 (negative claims). SIG must be able to represent: *"a complete authoritative register
of this population exists, is held by organisation O, and is not accessible"* — a **known-complete-unknown**.
That state is different from "we have no data" and different from "no such data exists," and it converts directly
into a §12 research task (an access request to the DPA or to a police zone). Belgium is also where the OSM import
actually landed first (F9.6), so OSM is currently a *better* public source than the legal register.
**Outline delta:** EXTENDS §9.4 with a third negative-claim category.

---

### F9.32 — Netherlands: device-level municipal open data, but frequently without a license

**Claim:** Dutch municipalities publish public-order camera locations as live open data with per-device status,
but the portals often declare **no license at all**.
**Status:** VERIFIED
**Evidence:** `https://data.eindhoven.nl/api/explore/v2.1/catalog/datasets/locaties-cameras-oov/records?limit=3`
(2026-08-20, HTTP 200): `total_count: 45`. Sample record verbatim:
`{"geo_point_2d":{"lon":5.4757222…,"lat":51.4434871…},"objectid":2,"naam":"EHV01.1 Fellenoord Fietstunnel",
"opmerking":"Online","nabij_locatie":"Lardinoisstraat 24 Fellenoord Stadsdeel Centrum","typecamera":"OOV",
"geo_shape":{…}}`. Dataset metadata (`…/catalog/datasets/locaties-cameras-oov`):
`title = "Camera's openbare orde"`, `publisher = "Gemeente Eindhoven"`, `modified = 2026-08-20T03:02:14+00:00`,
**`license = None`, `license_url = None`, `attributions = None`.** A companion dataset `locaties-cameras-vri`
covers junction (traffic-signal) cameras. Amsterdam publishes camera-surveillance *areas*; `data.overheid.nl`
carries `Cameragebieden` and `Cameratoezicht gebieden` datasets. Legal framing: municipal camera surveillance
requires a mayoral DPIA under GDPR Art. 35; footage retention max 28 days.
**Retrieved:** 2026-08-20
**Implication for the spec:** (a) The Dutch data is genuinely device-level and **includes an operational status
field** (`opmerking: "Online"`) — that is a `ConfigurationState` (§8.12), not a static attribute, and it is
exactly the kind of thing the outline says must be time-versioned rather than overwritten (§19.3). (b) The
missing license is the norm, not the exception, across EU municipal portals. SIG's ingestion gate must **refuse
to publish** data whose license is `null` under a redistributable output license, while still recording it
internally with `license: none-declared` and generating a task to ask the publisher. This is materially different
from the U.S. situation where government works are frequently public domain by default.
**Outline delta:** EXTENDS §14.2; CONFIRMS §8.12.

---

### F9.33 — Germany: no register, no national project — OSM plus the CCC is the entire substrate

**Claim:** Germany has no public surveillance-camera register and no dominant national mapping project; the
functioning artifact is **Surveillance under Surveillance**, an OSM-derived viewer hosted by the Chaos Computer
Club Hamburg, updated hourly.
**Status:** VERIFIED
**Evidence:** Surveillance under Surveillance is reachable at both `https://sunders.uber.space/` and
`https://sunders.hamburg.ccc.de/` (2026-08-20 search corpus + the Technopolice forum's own operational
references, F9.5). It *"uses data from OpenStreetMap contributors that is not visualized on the regular
OpenStreetMap site"*; contributors add cameras or guards with an existing OSM account; **database updated
hourly**. OSM wiki has a full German-language tagging page `DE:Tag:man_made=surveillance` and a German admin
hierarchy page (`https://wiki.openstreetmap.org/wiki/DE:Grenze`, HTTP 200, 41,881 bytes) documenting
`admin_level` 2 (Bund) / 4 (Länder) / 5 (Regierungsbezirke) / 6 (Kreise) / 7–8 (Ämter, Gemeinden) / 9–11
(Ortsteile, Stadtteile, statistische Bezirke) — and, for some cities, non-standard levels 12/13/14
(*Stadtzellen, Blockgruppen*). Berlin is commonly cited at ~22,289 public-space cameras (~6.3 per 1,000
residents) but this is a statistics-aggregator figure, not a register.
**Retrieved:** 2026-08-20
**Implication for the spec:** Germany confirms §5.1 by elimination — with no register and no national dataset,
OSM *is* the German layer, and SIG's German adapter is mostly (a) OSM ingestion and (b) `Organization`/jurisdiction
modelling. It also supplies the hardest case for the jurisdiction model: **German `admin_level` usage is not
uniform across Länder and extends past 11 in some cities**, which is precisely why SIG cannot hardcode depth.
**Outline delta:** CONFIRMS §5.1; EXTENDS §5 with Germany as a distinct adapter case.

---

### F9.34 — Brazil, India, Latin America, Africa: NGO trackers, two of them license-compatible

**Claim:** Four non-Western ecosystems have real trackers; **India's is CC-BY and the strongest**, Brazil's is
spreadsheet-based and crowdsourced, and the Latin American and African efforts are report-level rather than
record-level.
**Status:** VERIFIED
**Evidence:**
- **India — Panoptic Tracker** (`https://panoptic.in/`, 2026-08-20): run by the **Internet Freedom Foundation**;
  tracks government facial-recognition deployments; headline counters **170 installed FRT systems**,
  **118 RTI requests filed**, **₹1,513.26 Cr** total outlay; browsable by state; **license statement: "All
  contents licensed under CC-BY unless stated otherwise."** Source code described as open; however a GitHub API
  scan of `orgs/internetfreedomfoundation/repos` (20 repos, 2026-08-20) found **no** Panoptic repository — the
  nearest public artifact is `DataKind-BLR/panoptic_fp` (Apache-2.0, last updated 2023-01-28). Repository status:
  PARTIALLY VERIFIED.
- **Brazil — O Panóptico** (`https://opanoptico.com.br/`, 2026-08-20): *"Monitor de novas tecnologias na
  segurança pública do Brasil"*, a project of **CESeC** (Centro de Estudos de Segurança e Cidadania), funded by
  Open Society Foundations and Ford Foundation. Publishes a **"Banco de dados" via Google Sheets** plus a
  **"Metodologia"** document, and runs a public tip form (estado / cidade / bairro / description). **No license
  statement found.**
- **Latin America — Al Sur / Derechos Digitales**: `https://www.alsur.lat/en/reports`. The 2021 mapping covered
  **38 facial-recognition systems in 9 countries**; the 2025 update
  (`https://www.alsur.lat/sites/default/files/2025-07/Reporte%20reconocimiento%20facial.pdf`, EN version
  `…/2025-08/Facial%20recognition%20and%20surveillance.pdf`) analyses **83 initiatives across 15 countries**,
  covering public space, borders and government services. PDF only.
- **Africa — Paradigm Initiative, *Londa*** (`https://paradigmhq.org/londa/`): annual digital-rights report;
  **LONDA 2025 covers 29 African countries** scored on **12 indicators out of 60** against the ACHPR Declaration.
  PDF only; per-country narrative includes surveillance and shutdowns.
**Retrieved:** 2026-08-20
**Implication for the spec:** These are **coarse-granularity Claim sources** (§8.16) — mostly
`organization × technology × year`, sometimes with a cost figure and an RTI/FOI document behind it. SIG's
`Claim.granularity` must be explicit (`device / site / organization / jurisdiction / country`) so that a
country-level Al Sur claim and a device-level OSM node can coexist without one implying the other. Panoptic's
CC-BY is directly ingestible; O Panóptico requires a permission request; Al Sur and Londa are citation-only
until a data agreement exists.
**Outline delta:** EXTENDS §5.3 — the outline names only three global datasets and treats "other countries" as
undifferentiated; there are at least four organised national/regional trackers with different license postures.

---

### F9.35 — Canada, Australia/NZ, Hong Kong

**Claim:** Canada supplies adjudicated regulator findings; New Zealand supplies the most ontologically
interesting case in this workstream (police riding **private** ALPR networks); Hong Kong supplies a large,
state-announced build-out with no public data.
**Status:** VERIFIED (secondary sources, all fetched 2026-08-20)
**Evidence:**
- **Canada** — `https://www.priv.gc.ca/en/opc-actions-and-decisions/investigations/investigations-into-businesses/2021/pipeda-2021-001/`
  **PIPEDA Findings #2021-001**, the joint OPC / CAI Québec / OIPC BC / OIPC Alberta Clearview AI investigation
  (3 February 2021): Clearview scraped >3 billion images; **48 accounts** created for Canadian law-enforcement
  agencies and organisations, with per-account search volumes ranging from tens to thousands. Follow-on:
  compliance order 14 December 2021; separate RCMP finding 10 June 2021. ALPR: **OIPC BC Investigation Report
  F12-04** (Victoria Police Department ALPR); **IPC Ontario** *Best Practices for Automated Licence Plate
  Recognition Technologies* (Toronto Police Service engaged 2024). Academic: *"Automated Licence Plate
  Recognition in Canadian Policing: Documenting Use and Policy"*, **Canadian Public Policy**, doi
  `10.3138/cpp.2024-056` — finding that most Canadian services using ALPR have **no written procedure**.
- **New Zealand** — police access the **private** ANPR networks of **Auror** (Auckland) and **SaferCities**;
  ~**6,000 staff** can run non-tracking lookups and ~**1,000** have additional authority for vehicle-to-vehicle
  tracking; **>500,000 queries** in the last reported year, a sharp increase. Police Manual chapter published at
  `https://www.police.govt.nz/about-us/publication/automatic-number-plate-recognition-police-manual-chapter-0`.
  Legal challenges to ANPR-derived evidence are active (RNZ 501012, NZ Herald).
- **Hong Kong** — police **SmartView** programme: expansion to **60,000 cameras by 2028** backed by
  **HK$4.06 bn**, phase 2 adding **20,000 cameras/year 2026–2028** including connecting other departments'
  cameras into the police network, phase 3 adding 6,500 more 2028–2031; the police commissioner stated an
  intention to add facial recognition to police-managed CCTV *"within this year"* with a legal framework in
  preparation (HKFP 16 February 2026; SCMP).
**Retrieved:** 2026-08-20
**Implication for the spec:** New Zealand is the decisive stress test for §8.8 `AccessRelationship`. The
Flock-shaped U.S. assumption is *agency owns/contracts the network and shares with other agencies*. In NZ the
network is **owned by retailers and a private vendor**, and the police relationship is *query access with
tiered internal authorisation* (6,000 basic / 1,000 tracking). SIG therefore needs, on `AccessRelationship`:
`accessor_org`, `data_holder_org`, `data_owner_org` (three distinct roles, not two), plus an
`authorized_user_count` and an `internal_authorization_tier`. Hong Kong shows the need for a
`planned/announced` Deployment status with a **target date and target quantity** distinct from `contracted`
(§8.5 has `proposed_at` but no quantity-target concept).
**Outline delta:** EXTENDS §8.8 and §8.5.

---

### F9.36 — Global cross-country datasets: one is cleanly reusable, two are not

**Claim:** Of the three global datasets the outline names in §5.3, only the Carnegie AI Global Surveillance Index
is openly licensed and downloadable; ASPI's map is behind a bot wall and Freedom House's scores require an email
request.
**Status:** VERIFIED
**Evidence:**
- **Carnegie AIGS Index** — `https://data.mendeley.com/datasets/gjhf5y4xjp/4` (2026-08-20): *"AI & Big Data
  Global Surveillance Index (2022 updated)"*, author **Steven Feldstein**, published **6 June 2022**, version 4,
  **DOI 10.17632/gjhf5y4xjp.4**, **license CC BY 4.0** (`https://creativecommons.org/licenses/by/4.0/`).
  Covers **179 countries, 2012–2022**; **97 countries** with documented capability in four categories —
  smart/safe city platforms **64**, public facial-recognition systems **78**, smart policing **69**, social-media
  surveillance **38**. Explicit exclusions: private-sector surveillance, privately-owned business monitoring,
  airport border control. The 2019 original is `10.17632/386s7f9d25/1` and the underlying citations are an open
  Zotero library, group **2347403** (`https://www.zotero.org/groups/2347403/global_ai_surveillance/items`).
- **ASPI Mapping China's Tech Giants** — `https://chinatechmap.aspi.org.au/` → **HTTP 403**, 5,649 bytes,
  Cloudflare *"Just a moment…"* interstitial, with both WebFetch and a full browser-UA curl. **INACCESSIBLE.**
  Secondary: 27 companies, **3,900+ global entries**, first published April 2019, relaunched June 2021.
  Fallback: ASPI's per-report PDFs on `aspi.org.au` are reachable; a data request to ASPI ICPC would be required
  for the underlying records.
- **Freedom on the Net** — `https://freedomhouse.org/report/freedom-net` (2026-08-20): latest edition
  **FOTN 2025, "An Uncertain Future for the Global Internet"**, **72 countries**, 87% of global internet users.
  **Scoring data is not downloadable**: it must be requested by email with subject "FOTN Data Request". No
  reuse license stated on the page; "Content Permissions" referenced but not detailed.
- **IPVM** — `https://ipvm.com/` : paywalled subscription research (Info+ and Enterprise/Research Service),
  **one-year contract**, 2FA required, **account sharing explicitly prohibited**; 11,000+ proprietary reports,
  1,300+ empirical tests; claims 10,000+ subscribers in 120+ countries.
**Retrieved:** 2026-08-20
**Implication for the spec:** Only Carnegie AIGS can be **ingested and redistributed** (CC BY 4.0, attribution to
Feldstein + DOI). It enters SIG as country-level `Claim`s with `granularity: country` and
`validity_period: 2012–2022` — i.e. **already stale by four years**, so it must be flagged
`superseded_by: none; staleness: high`. ASPI and Freedom House enter as **linked citations only**. IPVM must be
recorded as a source SIG **cannot** ingest under any circumstance — sharing paywalled content would breach their
terms — but IPVM *reporting* can be cited as an `EvidenceArtifact` with `access: paywalled`.
**Outline delta:** CORRECTS §5.3 — the outline lists three global datasets as if equivalently available; two are
effectively unavailable to an automated system, and the one that is available is four years out of date.

---

# Part F — The FR ↔ EN technology crosswalk

Sources: Technopolice `meta-i18n-filter.js` (F9.4), the Technopolice `/villes/` prose inventory (F9.2), LQDN's
LAPI article (F9.13), the OSM import translation table (F9.12), the French Code de la sécurité intérieure
(F9.18), and the loi JO / loi RIPOST sequence (F9.38).

| French term (as used) | Literal gloss | SIG `Technology` (§8.4) | OSM tagging | Notes / traps |
|---|---|---|---|---|
| **vidéosurveillance** | video surveillance | `fixed_cctv` | `man_made=surveillance` + `surveillance:type=camera` | The critical/activist register. Same referent as *vidéoprotection*. |
| **vidéoprotection** | "video protection" | `fixed_cctv` | same | The **official/legal** register since 2011 (LOPPSI 2). All statutes, arrêtés and CPV-tagged tenders use this word. **A crawler keyed only on "vidéosurveillance" will miss the entire legal corpus.** |
| **VSA — vidéosurveillance algorithmique** | algorithmic video surveillance | `video_analytics` | no standard tag | Technopolice key `vsa`, label *"Vidéosurveillance automatisée"* — note the site's own label says *automatisée*, the discourse says *algorithmique*. Legally defined as **behaviour/event detection excluding biometric identification** (F9.38). |
| **caméra augmentée** | "augmented camera" | `video_analytics` | — | The government's preferred euphemism for VSA; appears in CNIL and ministerial texts. |
| **reconnaissance faciale (RF)** | facial recognition | `facial_recognition` | `surveillance:type=AFR` (67 uses globally) | Technopolice key `rf`. **Legally distinct from VSA in France** — conflating them will produce false claims. |
| **LAPI — lecture / lecteur automatisé(e) de plaques d'immatriculation** | automated plate reading | `alpr` | `surveillance:type=ALPR` | The French ALPR term. Plural *"les LAPI"*. Mobility classes: **fixe / mobile / transportable** (three, not two). |
| **STCL** | centralised plate-processing system | `DataSystem` | — | Not a technology — a national `DataSystem` (§8.7). |
| **FOVeS / N-SIS** | flagged-vehicle file / Schengen IS | `DataSystem` (reference DB) | — | §4.7's "reference database" pattern, in French form. |
| **caméras parlantes** | "talking cameras" | `audio_broadcast_camera` | `camera:…` + `speaker` | Technopolice key `cameras_parlantes`. **No U.S. equivalent capability in the outline's §8.4 list.** |
| **caméras thermiques** | thermal cameras | `thermal_imaging` | `camera:type` variants | Technopolice key `cameras_thermiques`. |
| **capteurs sonores** | acoustic sensors | `acoustic_detection` | `surveillance:type=gunshot_detector` (imperfect) | Technopolice key `capteurs_sonores`. French deployments (Saint-Étienne) are **general acoustic anomaly detection**, not gunshot-specific — mapping to `gunshot_detector` would be a distortion. |
| **police prédictive** | predictive policing | `predictive_policing` | — | Technopolice key `police_predictive`. |
| **drones / aéronefs (caméras aéroportées)** | drones / camera-equipped aircraft | `drone_surveillance` | — | The legal term in décret 2023-828 is *"caméras installées sur des aéronefs"*. |
| **« Safe City » / « Smart City » sécuritaire** | — | (programme, not technology) | — | Model as a **Deployment programme** with multiple technologies, not as a Technology. |
| **portique de reconnaissance faciale** | FR access gate | `facial_recognition` (access control) | — | The Région Sud *lycées* case; access-control FR, not public-space FR. |
| **verbalisation / vidéo-verbalisation** | camera-issued traffic fines | `automated_enforcement` | — | A *use* of vidéoprotection, i.e. a `Policy`/purpose attribute, not a device type. |
| **arrêté préfectoral** | prefectural order | (`Authorization`) | — | See F9.18 / F9.44. |
| **commission départementale de vidéoprotection** | departmental video-protection commission | `Organization` (oversight) | — | `organization_type: oversight_commission`. |
| **police municipale / police nationale / gendarmerie nationale / douanes** | — | `Organization` types | `operator=*` | See F9.42. |

**Two crosswalk rules that fall out of this table:**
1. **`vidéosurveillance` ↔ `vidéoprotection` must be an alias pair with a register annotation
   (`critical` / `official`)**, not two Technology rows and not a silent merge. Register matters because it
   predicts which corpus a term appears in.
2. **`capteurs sonores` must NOT auto-map to `gunshot_detector`.** SIG's Technology entity needs a
   `parent_capability` relation (`acoustic_detection` ⊃ `gunshot_detection`) so that a French acoustic-sensor
   claim and a U.S. ShotSpotter claim can be compared at the right level without over-claiming.

---

### F9.37 — French vendor and product names differ, and the "safe city" prime contractors are national champions

**Claim:** The French vendor layer is populated by different firms than the U.S. one, and the same capability
maps to different products.
**Status:** VERIFIED (from Technopolice/LQDN corpus)
**Evidence:** From `technopolice.fr/villes/` and the Technocarte payload (F9.2, F9.3): **Briefcam** is the
dominant VSA software (12 of 51 Technocarte communes deep-link to `technopolice.fr/briefcam/`); **Thalès** is
named as the Safe City prime for **Nice** and **La Défense**; the LQDN 2025 corpus names **Videtics** (acquired
by the Swiss firm **Technis**) among the Olympic-law VSA algorithm providers; SNCF and RATP are named as VSA
operators. The Grenoble administrative court ruled in January 2025 that a VSA deployment (Moirans) was
*"illégal et disproportionné"*.
**Retrieved:** 2026-08-20
**Implication for the spec:** §8.2/§8.3 hold without modification — Vendor and Product are already
country-neutral. But **`Vendor` needs a jurisdiction-qualified legal-entity identifier**: in France that is
SIREN/SIRET (which DECP uses natively, F9.16), in the UK a Companies House number, in the EU a **EUID**. A
single `vendor.identifiers[]` array with `{scheme, value}` is required; a bare `name` will not reconcile
`Briefcam` (Israeli, Canon-owned) across a French arrêté, a TED notice and an OSM `operator` tag.
**Outline delta:** EXTENDS §8.2.

---

### F9.38 — French VSA legal status: authorised, censured, then re-authorised — a temporal-authorization worked example

**Claim:** The legal authorization for algorithmic video surveillance in France was created in 2023, expired in
March 2025, had its extension **struck down by the Conseil constitutionnel in April 2025**, and was re-created and
widened by the **loi RIPOST adopted 21 July 2026**, now running to **2030**.
**Status:** VERIFIED
**Evidence:** Sequence, each element separately sourced (all retrieved 2026-08-20):
1. **19 May 2023** — art. 10, **loi n° 2023-380** relative aux Jeux Olympiques et Paralympiques de 2024 creates
   the VSA experiment.
2. **28 August 2023** — **décret n° 2023-828** (`https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000048007135`)
   sets the modalities for algorithmic processing of vidéoprotection images and of *"caméras installées sur des
   aéronefs"*.
3. **December 2023** — Conseil d'État decision on Briefcam functions: certain functions unlawful, but no sanction
   where not activated (or not in real time) — i.e. **written-configuration vs actual-configuration is already
   litigated in France**, precisely the outline's §8.12 distinction.
4. **31 March 2025** — original experiment expiry. An amendment adopted **11 February 2025** replaced that date
   with **1 March 2027** inside the *proposition de loi relative à la sécurité dans les transports*; the CMP
   validated it **7 March 2025**.
5. **24 April 2025** — the **Conseil constitutionnel** censured that article as a **cavalier législatif**
   (no link, even indirect, to the initial bill — art. 45 of the Constitution). The extension therefore never
   took effect.
6. **January 2025** — tribunal administratif de Grenoble: VSA deployment outside the JO framework
   *"illégal et disproportionné"*, implicating hundreds of local deployments.
7. **21 July 2026** — **loi RIPOST** adopted in commission mixte paritaire. Article 19 extends the experiment to
   **2030** and widens it to *"bâtiments ouverts au public, leurs abords et la voie publique"*. Facial
   recognition and biometric identification remain **explicitly excluded**. The same law expands LAPI powers
   (F9.13).
**Retrieved:** 2026-08-20
**Implication for the spec:** This single chain requires **five** things the outline's §8.11 `Policy` cannot do:
(a) an authorization with an **expiry date**; (b) an authorization whose validity was **retroactively annulled by
a different body**; (c) a **court decision as an entity that changes the state of an authorization**, not merely
an `Incident`; (d) a `Deployment` whose legal status can be `unauthorized-but-operating` (the post-Grenoble local
deployments); (e) **procedural-ground annulment** — the extension fell on a *procedural* defect, not on the
merits, which is materially different information for a downstream user. See F9.44.
**Outline delta:** CONTRADICTS the sufficiency of §8.11 for non-US legal systems; EXTENDS §8.12 and §8.14.

---

# Part G — Country-by-country source table

Legend — **Obtainable**: `API` (unauthenticated, tested) · `BULK` (bulk download, tested) · `SCRAPE` ·
`REQUEST` (permission/email required) · `NO` (blocked/paywalled). **Distortion**: whether the SIG ontology as
written in §8 can hold the source without loss.

| Country / body | Source | What it is | Obtainable | Format | License (verified) | Ontology fit |
|---|---|---|---|---|---|---|
| **Global** | OpenStreetMap | 558,645 surveillance objects; 144,312 ALPR | BULK (Geofabrik PBF; Overpass rate-limits) | PBF / XML / JSON | **ODbL 1.0** — share-alike, viral | §8.6 PhysicalAsset — clean, but tag normalisation required (F9.9) |
| **Global** | Carnegie AIGS Index v4 | 179 countries, 2012–2022 | BULK | CSV (Mendeley) | **CC BY 4.0**, DOI 10.17632/gjhf5y4xjp.4 | §8.16 Claim at `granularity: country`; stale |
| **Global** | Freedom on the Net 2025 | 72-country scores | REQUEST (email) | n/a | not stated | citation only |
| **Global** | ASPI China Tech Map | 27 firms, 3,900+ entries | **NO** (Cloudflare 403) | — | not seen | citation only |
| **Global** | IPVM | vendor research | **NO** (paywall, sharing prohibited) | — | proprietary | citation only, `access: paywalled` |
| **Global** | OCDS Data Registry | 100+ procurement publishers | BULK | JSON/XLSX/CSV | per-publisher | §8.10 — **adopt as the Contract schema** |
| **EU** | TED API v3 | EU-wide notices; 2,257 CPV-35120000 notices YTD 2026 | **API** (no key, tested) | JSON + per-language XML/PDF/HTML | EU reuse (Decision 2011/833/EU family) — **not directly verified** | §8.10 + §8.2 — good; language-keyed names (F9.22) |
| **EU** | AI Act Art. 71 database | high-risk AI register | **NO** until 2027-12-02, and LE/migration excluded | — | n/a | — |
| **EU** | AI Act Art. 5(6)-(7) reports | aggregated RBI authorization counts | future | PDF (expected) | EU reuse | new `Authorization` aggregate |
| **France** | **DECP / API DECP** | daily national procurement, all buyers | **API/BULK** (tested, 1,944 files) | JSON | **Licence Ouverte 2.0 (`lov2`)** | §8.10 — **best-in-class**; needs `amendments[]` |
| **France** | RAA des préfectures | 22,403 indexed prefecture gazettes | **BULK** (CSV tested) | CSV index → PDFs | **ODbL (`odc-odbl`)** | §8.15 + new `Authorization` (F9.44) |
| **France** | DILA OPENDATA (JORF, LEGI, BOAMP, CNIL, JADE) | full legal corpus | **BULK** (tested) | XML tarballs | Licence Ouverte | §8.11, §8.14 |
| **France** | CNIL délibérations / sanctions / mises en demeure / contrôles | DPA decisions since 1979 | **BULK** | XML + DTD | **`fr-lo`** | §8.14 — needs `dpa_*` event types |
| **France** | CADA avis (data.gouv `/explore/cada`) | FOI-appeal jurisprudence since 1980s | API/SCRAPE | web + dataset | Licence Ouverte | §8.15 acquisition provenance |
| **France** | Ma Dada | 51,669 FOI requests / 51,918 authorities | SCRAPE + Atom (no full API) | HTML/Atom | site terms | §8.15 `acquisition_method: foi_request(FR-CADA)` |
| **France** | geo.api.gouv.fr / INSEE COG | commune→dept→région→EPCI + SIREN | **API** (tested) | JSON | Licence Ouverte | **jurisdiction spine** (F9.41) |
| **France** | SIRENE (INSEE) | all legal entities, SIREN/SIRET | BULK | CSV | **`lov2`** | §8.1/§8.2 identifier resolution |
| **France** | Min. Intérieur "Vidéoprotection – Implantation des caméras" | Paris PVPP camera list | BULK | KML + ODS | **`fr-lo`** | §8.6 — **but last updated 2018-11-16, Paris only** |
| **France** | Technocarte | 51 communes, polygon-level | SCRAPE (JS assets) | GeoJSON-in-JS | **none declared** | §8.5 Deployment claims only; obsolete |
| **UK** | Find a Tender (OCDS) | all UK notices since Feb 2025 | **API** (tested) | OCDS JSON | **OGL v3.0** (in payload) | §8.10 — clean |
| **UK** | Contracts Finder (OCDS) | pre-2025 + below-threshold England | **API** (tested) | OCDS JSON | **OGL v3.0** | §8.10 |
| **UK** | Home Office NAS standards (NASPLE) | national ANPR governance; updated 2026-07-29 | BULK (PDF/HTML) | PDF/HTML | OGL v3.0 (gov.uk default) | §8.7 DataSystem + §8.11 |
| **UK** | BSCC | Surveillance Camera Code, national strategy | SCRAPE | PDF/HTML | OGL v3.0 | §8.11 |
| **UK** | WhatDoTheyKnow | FOI corpus | **NO** to scripts (403); Atom/agreement fallback | HTML/Atom | site terms | §8.15 |
| **UK** | ONS Open Geography Portal | 361 LADs + full hierarchy | **API** (tested) | GeoJSON/ArcGIS | OGL v3.0 | **jurisdiction spine** |
| **Belgium** | declarationcamera.be register | legally complete camera register | **NO** (eID auth wall) | — | n/a | §9.4 known-complete-unknown |
| **Belgium** | OSM (post-import) | ~16k Brussels-region cameras | BULK | PBF | ODbL | §8.6 |
| **Netherlands** | data.eindhoven.nl et al. | device-level municipal cameras + status | **API** (tested, 45 recs) | JSON/GeoJSON | **none declared** | §8.6 + §8.12 |
| **Germany** | OSM + Sunders (CCC Hamburg) | OSM-derived viewer, hourly | BULK (via OSM) | — | ODbL | §8.6 |
| **Canada** | OPC / OIPC BC / IPC ON findings | adjudicated regulator decisions | SCRAPE | HTML/PDF | Crown/open gov | §8.14 `adjudicated` |
| **New Zealand** | NZ Police ANPR manual + reporting | police access to private ALPR nets | SCRAPE | HTML/PDF | NZ CC-BY (gov default) | **§8.8 needs 3 org roles** |
| **India** | Panoptic (IFF) | 170 FRT systems, 118 RTIs | SCRAPE | HTML | **CC-BY** (site statement) | §8.5 + §8.16 |
| **Brazil** | O Panóptico (CESeC) | FRT monitor + crowdsourced tips | SCRAPE / REQUEST | Google Sheets | none declared | §8.5 |
| **LatAm** | Al Sur | 83 initiatives, 15 countries | SCRAPE | PDF | not stated | §8.16 `granularity: organization` |
| **Africa** | Paradigm Initiative *Londa* 2025 | 29 countries, 12 indicators | SCRAPE | PDF | not stated | §8.16 `granularity: country` |
| **Hong Kong** | SmartView (announcements) | 60k cameras by 2028 | SCRAPE | news/HTML | n/a | §8.5 `planned` + target quantity |

---

# Part H — Ontology generalization: stress test and specification

## F9.39 — Summary of what breaks

| §8 element | Breaks internationally? | Severity | Fix |
|---|---|---|---|
| 8.1 Organization | **Yes** — `organization_type` and `ORI / government identifiers` are U.S.-shaped | **High** | F9.42 |
| 8.1 `jurisdiction` | **Yes** — no generic model; US state/county/place/FIPS assumed | **Critical** | F9.40–F9.41 |
| 8.2 Vendor | Minor — needs scheme-qualified legal-entity ids | Low | F9.37 |
| 8.3 Product | No | — | — |
| 8.4 Technology | Partial — list omits FR capabilities (caméras parlantes, general acoustic detection) and needs `parent_capability` | Medium | Part F |
| 8.5 Deployment | **Yes** — no authorization link, no `planned` target quantity, no time-boxed operation | High | F9.24, F9.29, F9.35, F9.44 |
| 8.6 PhysicalAsset | **Yes** — `mobility` is treated as binary | Medium | F9.13, F9.29 |
| 8.7 DataSystem | Partial — no hub-vs-mesh topology attribute | Medium | F9.27 |
| 8.8 AccessRelationship | **Yes** — two org roles, needs three; no authorized-user tiering | High | F9.35 |
| 8.9 IntegrationRelationship | No | — | — |
| 8.10 Contract | Partial — should be an **OCDS profile**; needs `amendments[]`, `procurement_stage`, `ocid` | Medium | F9.16, F9.21, F9.26 |
| 8.11 Policy | **Yes** — cannot express authorizations, expiry, annulment, DPA decisions, codes of practice | **Critical** | F9.44 |
| 8.12 ConfigurationState | No — already validated by the French Briefcam litigation | — | F9.38 |
| 8.13 UsageObservation | Partial — NZ/UK aggregate query counts fit; scope vocab is US-shaped | Low | F9.27 |
| 8.14 Incident | Partial — `event_type` lacks `dpa_*` and `constitutional_annulment` | Medium | F9.19, F9.38 |
| 8.15 EvidenceArtifact | **Yes** — `acquisition_method` has no FOI-regime dimension; `license` must be an entity | High | F9.8, F9.14, F9.45 |
| 8.16 Claim | Partial — needs explicit `granularity` and language of the source text | Medium | F9.34, F9.46 |
| §13 publication policy | **Yes** — stated as one global rule; must be jurisdiction-conditional | **Critical** | F9.47 |

---

### F9.40 — Requirement: a generic hierarchical jurisdiction model with a pluggable national code system

**Claim:** No two of the five studied countries share a subdivision hierarchy, a depth, or a code system, and at
least two (France, Germany) have hierarchies that are not strict trees. A US-shaped `state/county/place/FIPS`
model cannot be generalised by adding columns.
**Status:** VERIFIED
**Evidence:** Verified structures, 2026-08-20:
- **France** — `https://geo.api.gouv.fr/communes?code=75056&fields=…` → HTTP 200,
  `[{"nom":"Paris","code":"75056","codeDepartement":"75","codeRegion":"11","codeEpci":"200054781",
  "population":2103778,"siren":"217500016"}]`. So: région → département → commune (**INSEE/COG codes**), **plus**
  `EPCI` (intercommunalité), which is a *parallel*, overlapping grouping of communes, **not** a level in the
  région/département tree. Communes also carry a **SIREN**, linking jurisdiction directly to the organization and
  procurement layers.
- **United Kingdom** — `https://services1.arcgis.com/ESMARspQHYMw9BZ9/…/Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0/query?returnCountOnly=true`
  → HTTP 200, `{"count":361}`. Four nations, then a **non-uniform** mix of counties / unitary authorities /
  districts / London boroughs / wards, coded with **ONS GSS codes** (`E06…`, `E07…`, `E08…`, `E09…`, `S12…`,
  `W06…`, `N09…`). Police force areas are a **separate geography** from local government.
- **Germany** — `https://wiki.openstreetmap.org/wiki/DE:Grenze` (HTTP 200): Bund(2) / Länder(4) /
  Regierungsbezirke(5) / Kreise(6) / Ämter–Gemeinden(7–8) / Ortsteile–Stadtteile(9–11), plus city-specific
  levels **12, 13, 14** (Stadtzellen / Blockgruppen / Blöcke). Codes: **AGS / ARS**.
- **EU-wide** — TED uses **NUTS** for place-of-performance (`RO321`) and ISO-3166-1 alpha-3 for country (F9.22).
- **Cross-walkable spine** — Wikidata SPARQL (`https://query.wikidata.org/sparql`, 2026-08-20, HTTP 200):
  `P300` ISO 3166-2 **5,459** items · `P374` INSEE municipality code **40,037** · `P439` German municipality key
  (AGS) **11,531** · `P836` GSS code **21,469** · **`P402` OpenStreetMap relation ID 576,998**.
**Retrieved:** 2026-08-20
**Implication for the spec / SPECIFICATION:**

```text
Jurisdiction
  id                     SIG-internal stable id
  wikidata_qid           Q…                      -- primary neutral anchor (CC0, cross-language)
  osm_relation_id        integer                 -- boundary geometry anchor (ODbL: keep geometry separable)
  iso_3166_1             "FR" | "GB" | "DE" | …  -- country, always present
  iso_3166_2             "FR-IDF" | "GB-ENG" | … -- present only where a level maps to ISO-3166-2 (nullable)
  level_rank             integer                 -- 0 = country, increasing downward; ADAPTER-DEFINED
  level_label            {lang: string}          -- "département" / "department"; multilingual (F9.46)
  level_kind             controlled vocab: country | region | province | department | county |
                         district | municipality | borough | ward | special_district | other
  parent_jurisdiction    Jurisdiction | null     -- containment tree
  overlapping_parents[]  Jurisdiction[]          -- NON-TREE memberships (EPCI, police force area, NUTS)
  national_codes[]       [{ scheme, value, valid_from, valid_to }]
                         -- scheme ∈ { INSEE, FR-EPCI, ONS-GSS, DE-AGS, DE-ARS, US-FIPS, US-GNIS,
                         --            NUTS, BE-NIS, NL-CBS, CA-SGC, BR-IBGE, IN-LGD, … }
  names[]                [{ lang(BCP47), value, kind: official|common|historical, script }]
  valid_from / valid_to  -- boundary reforms are frequent (FR communes nouvelles, UK unitarisation)
```

Design rules, each traceable to evidence above:
1. **`level_rank` is defined by the jurisdiction adapter, not by SIG.** Germany needs 14 levels; France needs 4;
   the UK needs a non-uniform 3–4. Hardcoding depth is the failure mode.
2. **`overlapping_parents[]` is mandatory, not optional.** France's EPCI and the UK's police force areas are
   real, funded, and *are the buyer* in procurement records — but they are not levels in the containment tree.
   Without this the model silently loses the entity that actually bought the cameras.
3. **The neutral spine is Wikidata QID + OSM relation ID + ISO 3166-1/2**, in that order of reliance.
   Wikidata is **CC0** (no attribution burden, safe to embed); OSM relation ids are the geometry join key but
   **the geometry itself is ODbL** and must stay in a separable layer per the outline's §14.1 Strategy A;
   ISO 3166-2 is stable and universally understood but **only covers the first subdivision level** (5,459 items
   worldwide) and the ISO standard itself is not freely licensed — so SIG should carry ISO 3166-2 codes as
   *values sourced from Wikidata P300*, never republish the ISO list as a dataset.
4. **National codes are an array with validity dates.** French communes merge (*communes nouvelles*), UK
   districts are abolished and re-created, German Kreise are reformed. A code is a claim with a time range.
5. **Jurisdiction ≠ Organization.** France makes this vivid: commune 75056 has SIREN 217500016. The SIREN is the
   *organization*; the INSEE code is the *jurisdiction*. Conflating them (as `place FIPS = the city government`
   implicitly does in a U.S. model) breaks as soon as an EPCI, a *syndicat mixte*, or a police force area buys
   the equipment for a territory it does not coincide with.
**Outline delta:** EXTENDS §8.1 substantially — the outline's `Organization.jurisdiction` is a single scalar field.

---

### F9.41 — Requirement: `organization_type` must be an extensible, namespaced vocabulary

**Claim:** The outline's §8.1 examples (municipality, police department, sheriff, state police, federal agency,
university police, school district, HOA, …) are a **U.S. enumeration**. Half have no non-US referent and the
non-US categories are absent.
**Status:** VERIFIED
**Evidence:** Categories encountered in this workstream that the §8.1 list cannot express:
France — *police nationale* (state, national), *gendarmerie nationale* (military status, Ministry of the
Interior), *police municipale* (communal), *douanes* (customs, an ALPR operator per F9.13), *préfecture* (state's
representative in the département — the **authorizing** body, F9.18), *commission départementale de
vidéoprotection* (oversight), *EPCI* (intercommunal). UK — 43 territorial forces, **British Transport Police**,
**NCA**, PCCs/MOPAC (governance bodies distinct from forces), BSCC/ICO/IPCO (oversight). Belgium — *zones de
police locale* + *police fédérale*. Germany — *Landespolizei* per Land + *Bundespolizei* + *BKA*. NZ/Brazil —
private ALPR network operators as first-class infrastructure owners (F9.35). EU — market surveillance
authorities and DPAs as **registration recipients** under AI Act Art. 5(4).
**Retrieved:** 2026-08-20
**Implication for the spec / SPECIFICATION:**
```text
organization_type: [ { scheme, value, lang_label{} } ]     -- an ARRAY of namespaced terms
  scheme = "sig:core"      → { government, law_enforcement, oversight_body, vendor, private_operator,
                               education, healthcare, transport_operator, nonprofit, community_association }
  scheme = "sig:fr"        → { police_nationale, gendarmerie_nationale, police_municipale, douanes,
                               prefecture, commission_departementale_videoprotection, epci, syndicat_mixte }
  scheme = "sig:gb"        → { territorial_force, btp, nca, pcc, mopac, local_authority }
  scheme = "sig:us"        → { police_department, sheriff, state_police, federal_agency, school_district, hoa }
```
Every organization carries at least one `sig:core` term (for cross-country queries such as "all law-enforcement
ALPR deployments in Europe") and zero or more national terms (for fidelity). **`sig:core` must be small and
functional; national vocabularies must be additive and versioned.** A flat global enum will either lose
gendarmerie/douanes or pollute the U.S. vocabulary with untranslatable terms.
Identifiers likewise: replace `ORI / government identifiers` with
`identifiers[]: [{scheme, value}]` where `scheme ∈ {US-ORI, US-NCIC, FR-SIREN, FR-SIRET, GB-COMPANIES-HOUSE,
GB-GOR, EU-EUID, WIKIDATA-QID, OCDS-PARTY-ID, …}` — note that OCDS already ships scheme-qualified party ids
(`GB-CFS-154927`, F9.26) and DECP ships bare SIRETs, so both are directly loadable.
**Outline delta:** CORRECTS §8.1.

---

### F9.42 — Requirement: `Policy` must be split into Policy / Law / Authorization / Guidance

**Claim:** The outline's single `Policy` object (`applies_to`, `effective period`, `policy_type`, `text/source`)
cannot represent an arrêté préfectoral, a five-year expiry, a constitutional annulment on procedural grounds, a
DPA sanction, an EU directive, or a non-binding code of practice.
**Status:** VERIFIED (by the French and UK cases in F9.18, F9.19, F9.24, F9.28, F9.38)
**Implication for the spec / SPECIFICATION:** four related entities, sharing a common `LegalInstrument` supertype:

```text
LegalInstrument (abstract)
  id · jurisdiction · issuing_organization · title{lang} · citation · text_source(EvidenceArtifact)
  enacted_at · effective_from · effective_to · superseded_by · language(BCP47)
  binding: binding | advisory | voluntary_code
  instrument_class: statute | regulation | decree | administrative_order | directive |
                    transposition | code_of_practice | dpa_decision | court_decision | internal_policy

Law            : instrument_class ∈ {statute, regulation, decree, directive}
                 + transposes: Law | null        -- EU directive → national law (LED 2016/680 etc.)
                 + applies_in: Jurisdiction[]

Authorization  : NEW.  instrument_class = administrative_order | judicial_authorization
                 authorizes: Deployment | DeploymentOperation | DataSystem
                 legal_basis: Law
                 granted_by: Organization           -- préfet, judge, independent admin authority
                 granted_at · expires_at            -- FR vidéoprotection: 5 years, renewable
                 renewal_of: Authorization | null
                 scope: { temporal, geographic, personal, quantity }   -- AI Act Art.5(2) shape
                 status: in_force | expired | renewed | withdrawn | annulled | never_took_effect
                 status_changed_by: LegalInstrument  -- e.g. CC decision 24 Apr 2025
                 annulment_ground: substantive | procedural | null    -- F9.38 requires this distinction

Policy         : organizational rules (retention, acceptable use, immigration restriction, audit) — as §8.11
Guidance       : non-binding (UK Surveillance Camera Code, CNIL recommendations, EDPB guidelines,
                 IPC Ontario best practices) — `binding: advisory|voluntary_code`
```
Two consequences that must be testable: (a) a `Deployment` can be in state
`operating_without_valid_authorization` (post-Grenoble French VSA, F9.38); (b) an `Authorization` with
`status: annulled, annulment_ground: procedural` must render differently from `annulment_ground: substantive`,
because only the latter says anything about the merits of the surveillance.
**Outline delta:** CONTRADICTS the sufficiency of §8.11; this is the single largest ontology change R9 proposes.

---

### F9.43 — Requirement: `EvidenceArtifact.acquisition_method` must be internationalised, and `license` must become an entity

**Claim:** "FOIA" is not a universal acquisition method; and license needs its own provenance (F9.8).
**Status:** VERIFIED
**Implication for the spec / SPECIFICATION:**
```text
EvidenceArtifact.acquisition_method:
  { method: public_web | official_publication | official_gazette | open_data_portal | open_api |
            bulk_dataset | access_request | leak | field_observation | crowd_report | purchase |
            court_record | scraped_portal_snapshot
    access_request_regime: US-FOIA | US-STATE:<code> | FR-CADA | GB-FOIA | GB-EIR | IN-RTI |
                           BE-PUBLICITE | DE-IFG | CA-ATIA | CA-PROV:<code> | BR-LAI | NONE
    intermediary_platform: muckrock | madada | whatdotheyknow | direct | null
    statutory_deadline_days · appeal_body · appeal_is_precondition_to_litigation: bool }
```
The last flag is not decoration: in France, a CADA appeal is a **mandatory precondition** to litigation (F9.25),
which changes the shape of a §12 research task. `intermediary_platform` is what lets SIG hand work back to
Ma Dada / MuckRock / WhatDoTheyKnow instead of duplicating their infrastructure (§18, §7.1 Goal 7).

```text
SourceLicense (entity, not string)
  spdx_or_name · url_of_license_text · retrieved_at · seen_directly: bool
  attribution_required · attribution_string · share_alike · redistribution_permitted:
       yes | no | permission_granted | asserted_but_unverifiable | none_declared | unknown
  permission_record: { grantor, grant_date, grant_scope, instrument_url_or_hash } | null
```
`none_declared` (Technocarte, Eindhoven) is distinct from `unknown`, and both are distinct from
`asserted_but_unverifiable` (the sous-surveillance "C'est ok pour le transfert" email, F9.8). data.gouv.fr's own
license registry (`https://www.data.gouv.fr/api/1/datasets/licenses/`, 12 entries: `cc-by, cc-by-sa, cc-zero,
fr-lo, lov2, notspecified, odc-by, odc-odbl, odc-pddl, other-at, other-open, other-pd`) confirms that a national
portal already needs a `notspecified` value — SIG must too, and must gate publication on it.
**Outline delta:** EXTENDS §8.15 and §14.2.

---

### F9.44 — Requirement: multilingual labels, per the Wikidata/SKOS/TED pattern

**Claim:** Names, descriptions and vocabulary labels must be language-tagged collections, not scalars, and this
is already the shape used by every serious international system encountered.
**Status:** VERIFIED
**Evidence:** TED returns `"buyer-name": {"ron": ["SECTOR 3 AL MUNICIPIULUI BUCURESTI"]}` — an ISO-639-3-keyed
map to a list (F9.22), and offers notice text in **24 languages**. Wikidata models `label` / `description` /
`aliases[]` per language and is the source of the ISO/INSEE/AGS/GSS cross-walk (F9.40). LQDN publishes in
`FR EN ES DE` (F9.13). OSM uses `name`, `name:<lang>`, `int_name`, `alt_name`, `official_name`. Belgium's DPA
site serves NL/FR/EN/DE.
**Implication for the spec / SPECIFICATION:**
```text
LangString = [ { lang: BCP47,          -- "fr", "fr-BE", "sr-Latn", "ar"
                 value: string,
                 script: ISO-15924 | null,
                 kind: official | common | short | historical | transliteration | machine_translation,
                 source: EvidenceArtifact | null,
                 romanization_scheme: string | null } ]
```
Rules:
1. **`canonical_name` is a *pointer into* the `names[]` array plus a display-language preference**, not a
   separate authoritative string. Choosing one string as canonical bakes in a language.
2. **BCP 47, not ISO 639-1.** Needed for `fr-BE` vs `fr-FR`, `nl-BE` vs `nl-NL`, `pt-BR`, `zh-Hant`/`zh-Hans`.
   Note TED emits **ISO 639-3** (`ron`, `deu`, `fra`) — the adapter must map 639-3 → BCP 47 on ingest.
3. **Transliteration is a `kind`, and must record `romanization_scheme`** (Pinyin, BGN/PCGN, ALA-LC). Never
   store a romanization as if it were the name.
4. **RTL**: store logical order, never inject bidi control characters into stored values; emit
   `dir` at render time from the script subtag. Never assume `value` is safe to concatenate with punctuation.
5. **Dates are ISO 8601 in storage, always.** French sources emit `dd/mm/yyyy`, U.S. sources `mm/dd/yyyy` —
   `01/02/2026` is ambiguous and has already been observed in DECP-adjacent CSVs. Parsers must be
   locale-declared per source, and any date whose locale is unknown must be stored as an **unparsed string plus
   a parse-failure flag**, never guessed.
6. **Addresses are not a fixed schema.** Store the raw address string with a `country` and an optional structured
   overlay; do not force `street/city/state/zip`. (French `lieuExecution` is a *département code*; Dutch records
   give `nabij_locatie` free text; UK OCDS gives a bare `postalCode`.)
7. **Controlled vocabularies get SKOS-style labels**: every Technology, organization_type and
   `level_kind` value has `prefLabel{lang}` + `altLabel{lang}[]`, so the FR/EN crosswalk in Part F is *data*, not
   documentation.
**Outline delta:** EXTENDS §8.1, §8.4, §8.16 — the outline uses scalar `canonical_name` and `aliases[]` with no
language dimension anywhere.

---

### F9.45 — Requirement: jurisdiction-conditional publication rules

**Claim:** SIG cannot have one global publication policy. The same fact — an officer's name in a contract, a
camera's exact coordinates, an unredacted FOI PDF — is publishable in the U.S., restricted in France, and
conditional in the UK.
**Status:** VERIFIED (F9.25, F9.31, F9.32; EDPB Guidelines 1/2024)
**Implication for the spec / SPECIFICATION:**
```text
PublicationPolicy (evaluated per Claim / EvidenceArtifact at serve time, not at ingest time)
  inputs:  subject_jurisdiction, publisher_jurisdiction, viewer_jurisdiction?,
           data_category (personal_data | special_category | institutional | geospatial),
           source_license, acquisition_method, subject_role (public_official | private_individual | organization)
  outputs: store: yes|no
           serve_public: yes|no|redacted
           serve_to_researchers: yes|no|on_agreement
           redaction_profile: <named profile>
           lawful_basis_note: string
           review_required_by_human: bool
```
Baseline profiles that must ship with v1:

| Profile | Personal names of public officials | Raw FOI/FOIA PDFs | Exact device coordinates | Notes |
|---|---|---|---|---|
| `US-DEFAULT` | serve | serve | serve (with §13.3 contextual review) | current outline assumption |
| `FR-GDPR` | **redact by default**; publish only with documented Art. 6(1)(f) balancing test | **must be anonymised before online publication** (CRPA L312-1-2) | serve, but operator names are personal data if the operator is a natural person | CADA appeal is a precondition to litigation |
| `EU-GDPR` | redact by default | redact by default | serve | EDPB Guidelines 1/2024: no generic legitimate-interest claim |
| `GB` | conditional; UK GDPR + FOIA s.40 | conditional | serve | Surveillance Camera Code still live (F9.28) |
| `UNKNOWN` | **fail closed** — store, do not serve | store, do not serve | store, do not serve | default for any unmapped jurisdiction |

Two non-negotiables: (a) the policy is evaluated **at serve time against a versioned ruleset**, so that a change
in law re-gates already-stored data without re-ingestion; (b) the default for an unmapped jurisdiction is
**fail-closed**, because the cost of an incorrect publication under GDPR is asymmetric.
**Outline delta:** CORRECTS §13 — the outline's §13.1–13.5 are written as a single global ethical stance.

---

# Part I — The jurisdiction-adapter checklist

Every country added in Stage 6 must ship an adapter satisfying **all 18 items**. An adapter is "done" when a
test fixture for one real municipality in that country round-trips through ingest → reconcile → serve.

**Identity and geography**
1. `jurisdiction_levels[]` — ordered list of `level_rank`, `level_kind`, `level_label{lang}` for the country.
2. `overlapping_parent_kinds[]` — non-tree groupings (FR EPCI, GB police force area, EU NUTS) with their sources.
3. `national_code_schemes[]` — code system(s), authoritative source URL, refresh cadence, historical-code policy.
4. **Boundary source** — OSM relation ids and/or the national geoportal, with license recorded.
5. **Wikidata coverage check** — % of the country's municipalities carrying a QID and P402; below a threshold,
   the adapter must supply its own crosswalk file.

**Organizations**
6. `organization_type` vocabulary (`sig:<cc>`) with `sig:core` mappings for every term.
7. `organization_identifier_schemes[]` (FR-SIREN/SIRET, GB Companies House + GB-GOR, DE …) and a resolver.
8. **Law-enforcement organization registry** — an authoritative list of forces/agencies with jurisdictions.

**Legal**
9. `LegalInstrument` type map — which national instruments fill `Law`, `Authorization`, `Policy`, `Guidance`.
10. **Authorization regime** — is there one? Who grants it, for how long, is it published, where, in what format?
    (FR: préfet, 5 years, published in the RAA as PDF. US: usually none. BE: declaration, not published.)
11. **Data-protection regime** — DPA name, decision corpus URL/format, whether decisions are open data.

**Evidence**
12. `access_request_regime` — statute, deadline, appeal body, whether appeal precedes litigation, intermediary
    platform, and whether that platform permits automated interaction (test it; record 403s).
13. **Procurement sources** — national portal(s), whether OCDS or bespoke, API endpoint, license, CPV or other
    classification scheme, and the `procurement_stage` coverage of each portal.
14. **Official gazette** — bulk access route for statutes and administrative orders.

**Language and presentation**
15. `default_languages[]` (BCP 47), plus the script(s) and any transliteration scheme.
16. `date_locale` and `number_locale` per source (never per country — DECP is ISO 8601, RAA filenames are not).

**Publication and governance**
17. `publication_profile` — which `PublicationPolicy` profile applies, with the specific statutory citation.
18. **Local partner or reviewer named**, per §7.1 Goal 7 / §18. An adapter without a local counterpart ships in
    read-only, non-public mode.

**Estimated effort per adapter** (engineer-weeks, assuming SIG core is generic by then):

| Component | France | UK | Germany | Belgium | A "hard" country (e.g. Brazil) |
|---|---:|---:|---:|---:|---:|
| Jurisdiction + org identity | 1.5 | 1.5 | 2.5 | 1 | 3 |
| Procurement ingest | **1** (DECP is clean) | **1** (OCDS) | 3 (fragmented Länder portals) | 2 | 3 |
| Legal/authorization ingest | **4** (RAA PDF pipeline) | 1.5 | 2 | 1 | 3 |
| DPA / accountability corpus | 1 | 1 | 2 | 1 | 2 |
| OSM reconciliation | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| i18n + publication profile | 1 | 0.5 | 1 | 1.5 (3 languages) | 1 |
| **Total** | **~9** | **~6** | **~11** | **~7** | **~12.5** |

The France total is dominated by one line: turning 22,403 RAA PDFs into structured arrêtés. That is also where
France's unique value lies (F9.18), so it should not be deferred — but it is the item most likely to overrun,
and it should be scoped as "one département end-to-end" before "all 101."

---

# Part J — Stage 6 plan

### F9.46 — Recommendation: the second country is the **United Kingdom**, not France

**Claim:** Despite France being the richer *evidence* environment and the obvious cultural fit (Technopolice,
LQDN), the UK is the correct second country because it minimises the number of ontology changes and legal
constraints that must be solved *simultaneously*.
**Status:** RECOMMENDATION grounded in F9.25–F9.30, F9.40–F9.45
**Reasoning:**
- **English-language.** Deferring the full i18n build-out by one country lets Stage 6 prove the *jurisdiction*
  and *organization* generalisation independently of the *language* generalisation. Two hard changes at once is
  how ontology migrations fail.
- **Procurement is OCDS and free.** Two tested, unauthenticated APIs under OGL v3.0 (F9.26). Adopting OCDS for
  the UK simultaneously buys 100+ other publishers later.
- **A genuinely national ALPR system** (NAS/NADC) exercises `DataSystem` hub topology and
  `AccessRelationship` at national scope (F9.27) — the exact things the U.S. mesh model does not exercise.
- **Live, high-salience facial recognition** with published deployment records (F9.29) exercises
  `DeploymentOperation` and time-boxed authorization without needing the French `Authorization` PDF pipeline.
- **UK GDPR is GDPR-shaped but with FOIA s.40 practice already worked out**, so the `PublicationPolicy`
  machinery gets built and tested under a regime that is strict but not as strict as CRPA L312-1-2.
- Known blockers to plan around: WhatDoTheyKnow is 403 to scripts (F9.30) — budget a mySociety conversation.

**France is third, and is the flagship.** France should follow immediately, because: DECP is the best Contract
source in the world (F9.15); the arrêté corpus is the best Authorization source in the world (F9.18); OSM
coverage is the densest on Earth at 75,926 objects (F9.10); Ma Dada is a mature partner (F9.14); and LQDN is an
active, credible counterpart (F9.13). France is where the `Authorization` entity, the FR/EN crosswalk, and the
`FR-GDPR` publication profile get proven.

### Ordered Stage-6 plan

| Phase | Scope | Gate to exit |
|---|---|---|
| **6.0 — De-Americanise the core** (before any country) | Implement F9.40 Jurisdiction, F9.41 organization_type, F9.42 LegalInstrument split, F9.43 acquisition_method + SourceLicense entity, F9.44 LangString, F9.45 PublicationPolicy. Backfill the U.S. graph onto the new model as `sig:us`. | The existing U.S. graph reproduces byte-identical public output through the generic model. **This is the real Stage-6 deliverable; countries are its test.** |
| **6.1 — Global OSM layer** | Ingest `man_made=surveillance` worldwide from Geofabrik PBF diffs (not Overpass, F9.10). Normalise the 116 `surveillance:type` / 430 `surveillance` / 676 `camera:mount` value sets via a versioned crosswalk (F9.9). Keep ODbL data in a separable layer (§14.1 Strategy A). | 558k+ objects loaded; junk values (`flock safety`) quarantined not dropped; per-country coverage metrics annotated with import provenance. |
| **6.2 — OCDS procurement, multi-country** | UK Find a Tender + Contracts Finder; then TED EU-wide (F9.22, F9.26). Build the CPV→Technology crosswalk (F9.17). | A surveillance-procurement query returns results for ≥5 countries with correct `procurement_stage` threading by `ocid`. |
| **6.3 — United Kingdom adapter** | Full 18-item checklist. NAS/NADC as `DataSystem`; Met LFR operations as `DeploymentOperation`; BSCC Code as `Guidance`. | One English local authority's dossier is complete and publishable under the `GB` profile. |
| **6.4 — France adapter** | DECP daily ingest; SIRENE/SIREN↔INSEE resolution; RAA→arrêté pipeline scoped to **one département first**; CNIL délibérations; CADA avis; Ma Dada partnership; FR/EN crosswalk as SKOS data. | One commune's dossier complete, served under `FR-GDPR` with anonymisation applied and reviewed by a French counterpart. |
| **6.5 — Belgium + Netherlands** | Cheap: OSM is already dense (post-import), Dutch municipal APIs are live, Belgian register is a documented known-unknown (F9.31). Exercises multilingual (`nl-BE`/`fr-BE`/`de-BE`) and `none_declared` licensing. | The Belgian register renders correctly as a known-complete-unknown with a generated access-request task. |
| **6.6 — Country-level global datasets** | Carnegie AIGS v4 (CC BY 4.0) as `granularity: country` Claims with staleness flags; Al Sur, Londa, Panoptic as linked evidence; ASPI/FOTN/IPVM as citations only (F9.36). | A country page shows coarse claims without implying device-level knowledge. |
| **6.7 — Germany, Canada, others** | Per-adapter, demand-driven. Germany's 14-level hierarchy is the final proof that `level_rank` is truly pluggable. | — |

**Total estimate:** 6.0 ≈ 10–14 engineer-weeks (core refactor, the dominant cost). 6.1 ≈ 3. 6.2 ≈ 4.
6.3 ≈ 6. 6.4 ≈ 9. 6.5 ≈ 7. 6.6 ≈ 2. **≈ 41–45 engineer-weeks to a credible four-country international SIG**,
of which roughly a third is the U.S.-agnostic core refactor that should arguably happen at Stage 1 instead.

**The strongest single recommendation in this file:** do **6.0 during Stage 1**, not Stage 6. Every finding above
shows that the U.S.-shaped choices (scalar jurisdiction, enum organization_type, single Policy object, scalar
names, one publication rule) are cheap to avoid now and expensive to unwind after five stages of U.S. data have
been loaded onto them.

---

## Open questions

1. **TED reuse terms were not directly verified.** The API works and is unauthenticated, but
   `https://ted.europa.eu/en/simap/legal-notice` returned **HTTP 404** on 2026-08-20. The applicable regime is
   almost certainly Commission Decision 2011/833/EU (free reuse with attribution), but the spec must hedge:
   treat TED as `redistribution: unknown` until the current legal notice URL is located and read.
2. **Ma Dada's terms of use and rate limits are unknown.** Only `/aide/api` was read. Before any automated
   interaction, obtain explicit agreement — the platform is small and association-run.
3. **Whether the Technocarte data can be licensed at all.** Technopolice is a decentralised campaign with no
   obvious legal entity; there may be no one who *can* grant a license. Hedge: link, never redistribute.
4. **Légifrance API (PISTE) requires OAuth credentials** that were not obtained. The DILA bulk route works, but
   incremental/targeted lookups will need the API. Unknown: rate limits, terms, whether redistribution of
   extracted articles is permitted.
5. **Whether arrêtés préfectoraux are extractable at acceptable precision.** 22,403 PDFs with generic titles;
   no sample was OCR'd in this workstream. If precision is poor, the French Authorization layer's value estimate
   drops sharply. **Scope one département as a spike before committing.**
6. **Overpass rate limits made 7 of 12 country counts unobtainable.** The per-country OSM density table is
   incomplete; a Geofabrik-based recount is needed before coverage metrics are published.
7. **Whether the Panoptic (IFF) data is actually retrievable in bulk.** The site states CC-BY and "open source"
   but no repository was found under the IFF GitHub org. Contact IFF.
8. **The `sig:core` organization_type vocabulary is proposed, not validated.** It needs review against at least
   one non-European, non-Anglophone country (Brazil or India) before being frozen.
9. **AI Act Art. 5 aggregated annual reports** — no such Commission report has been located as published yet
   (prohibitions applied 2 Feb 2025; first reports would be due 2026). Worth a check in six months.
10. **GDPR balancing tests for publishing named officials** are jurisdiction- *and* case-specific. R9 specifies
    the *mechanism* (per-jurisdiction profiles with fail-closed defaults) but the substantive legal analysis per
    country is out of scope and needs counsel before the EU public surface goes live.

---

## Spec requirements emitted

| ID | Requirement |
|---|---|
| **REQ-R9-01** | `Jurisdiction` MUST be a generic hierarchical entity with adapter-defined `level_rank`/`level_kind`, a `parent_jurisdiction` tree, **and** a separate `overlapping_parents[]` for non-tree groupings (FR EPCI, GB police force areas, EU NUTS). Depth MUST NOT be fixed in the schema. |
| **REQ-R9-02** | `Jurisdiction.national_codes[]` MUST be an array of `{scheme, value, valid_from, valid_to}`, with `scheme` drawn from an extensible registry (INSEE, FR-EPCI, ONS-GSS, DE-AGS, DE-ARS, US-FIPS, NUTS, …). No national code may occupy a dedicated column. |
| **REQ-R9-03** | The neutral jurisdiction spine MUST be `wikidata_qid` (CC0) + `osm_relation_id` + `iso_3166_1/2`. ISO 3166-2 values MUST be sourced via Wikidata P300 and MUST NOT be republished as an ISO-derived dataset. OSM-derived boundary geometry MUST live in a separable ODbL layer (§14.1 Strategy A). |
| **REQ-R9-04** | `Jurisdiction` MUST be distinct from `Organization`. A jurisdiction-to-governing-organization link is a typed edge, not identity. |
| **REQ-R9-05** | `Organization.organization_type` MUST be an array of `{scheme, value}` with a small mandatory `sig:core` term plus optional `sig:<cc>` national terms. A flat global enum is prohibited. |
| **REQ-R9-06** | `Organization.identifiers[]` and `Vendor.identifiers[]` MUST be `{scheme, value}` arrays supporting at minimum US-ORI, FR-SIREN, FR-SIRET, GB-COMPANIES-HOUSE, GB-GOR, EU-EUID, WIKIDATA-QID, OCDS party ids. |
| **REQ-R9-07** | The outline's `Policy` MUST be split into `Law`, `Authorization`, `Policy`, `Guidance` over a shared `LegalInstrument` supertype with `binding: binding\|advisory\|voluntary_code` and `instrument_class`. |
| **REQ-R9-08** | `Authorization` MUST support `granted_by`, `granted_at`, `expires_at`, `renewal_of`, `scope{temporal,geographic,personal,quantity}`, `status ∈ {in_force, expired, renewed, withdrawn, annulled, never_took_effect}`, `status_changed_by: LegalInstrument`, and `annulment_ground ∈ {substantive, procedural}`. |
| **REQ-R9-09** | `Deployment.status` MUST admit `operating_without_valid_authorization`, and `Deployment` MUST support a `planned` state carrying `target_quantity` and `target_date`. |
| **REQ-R9-10** | A `DeploymentOperation` entity MUST exist: a time-boxed activation of a capability at a location, with its own `Authorization`, distinct from both `Deployment` and `PhysicalAsset`. |
| **REQ-R9-11** | `PhysicalAsset.mobility` MUST be an extensible vocabulary (minimum: `fixed`, `relocatable_fixed`, `transportable`, `mobile`, `aerial`, `body_worn`), never a boolean. |
| **REQ-R9-12** | `AccessRelationship` MUST distinguish `accessor_org`, `data_holder_org` and `data_owner_org` as three roles, and MUST support `authorized_user_count` and `internal_authorization_tier`. |
| **REQ-R9-13** | `DataSystem` MUST carry a `network_topology` attribute (`hub_and_spoke` \| `peer_mesh` \| `federated`) and a jurisdiction-relative `scope`. |
| **REQ-R9-14** | `Contract` MUST be implemented as an **OCDS profile**: adopt `ocid` as the procurement-thread key, `tag[]`/`procurement_stage`, `parties[]` with scheme-qualified ids, and `classification.scheme = CPV`. Amendments MUST be dated sub-events, not row mutations. `end_date` MUST record whether it is stated or derived. |
| **REQ-R9-15** | SIG MUST maintain a versioned, reviewable **CPV → Technology crosswalk** and MUST record `extraction_method` and a precision estimate on every Claim derived from code/keyword filtering. Procurement MUST NOT auto-create Deployments (§19.11). |
| **REQ-R9-16** | `Technology` MUST support `parent_capability`. `capteurs sonores` MUST NOT be auto-mapped to `gunshot_detector`; `vidéosurveillance`/`vidéoprotection` MUST be an alias pair annotated with register (`critical`/`official`). |
| **REQ-R9-17** | All human-readable names, descriptions and controlled-vocabulary labels MUST be `LangString` arrays keyed by **BCP 47**, with `kind`, optional `script` (ISO 15924) and `romanization_scheme`. `canonical_name` MUST be a pointer plus display-language preference, not an authoritative scalar. |
| **REQ-R9-18** | Ingest adapters MUST map ISO 639-3 (TED) and other language identifiers to BCP 47. Dates MUST be stored as ISO 8601 with a per-source declared locale; ambiguous dates MUST be stored unparsed with a parse-failure flag, never guessed. Addresses MUST be storable as raw string + country, with structure optional. |
| **REQ-R9-19** | `EvidenceArtifact.acquisition_method` MUST be a structured object carrying `method`, `access_request_regime` (US-FOIA, FR-CADA, GB-FOIA, GB-EIR, IN-RTI, …), `intermediary_platform`, `statutory_deadline_days`, `appeal_body` and `appeal_is_precondition_to_litigation`. |
| **REQ-R9-20** | `SourceLicense` MUST be an entity with `redistribution_permitted ∈ {yes, no, permission_granted, asserted_but_unverifiable, none_declared, unknown}` and an optional structured `permission_record{grantor, grant_date, grant_scope, instrument_url_or_hash}`. `none_declared` MUST be distinct from `unknown`. |
| **REQ-R9-21** | Publication MUST be gated by a `PublicationPolicy` evaluated **at serve time** against a versioned ruleset, parameterised by subject jurisdiction, data category and subject role, with named profiles at minimum for `US-DEFAULT`, `FR-GDPR`, `EU-GDPR`, `GB` and `UNKNOWN`. `UNKNOWN` MUST fail closed (store, do not serve). |
| **REQ-R9-22** | Data with `SourceLicense.redistribution_permitted ∈ {no, none_declared, unknown}` MUST NOT be served under SIG's public output license, and MUST generate a research task to obtain clarification. |
| **REQ-R9-23** | `Claim` MUST carry an explicit `granularity ∈ {device, site, organization, jurisdiction, country}` and the BCP 47 `language` of the source text it was extracted from. |
| **REQ-R9-24** | `Incident/AccountabilityEvent.event_type` MUST include `dpa_decision`, `dpa_sanction`, `dpa_formal_notice`, `dpa_inspection`, `court_decision` and `constitutional_annulment`; a DPA decision MUST NOT be flattened into `lawsuit`. |
| **REQ-R9-25** | SIG MUST represent a **known-complete-unknown**: an authoritative complete register exists, is held by a named organization, and is inaccessible (Belgian camera register). This state MUST be distinct from "no data" and from "no such data exists" (§9.4). |
| **REQ-R9-26** | The OSM ingester MUST run on scheduled Geofabrik PBF extracts, not the public Overpass endpoint, and MUST apply a versioned tag-normalisation crosswalk that quarantines out-of-vocabulary values (e.g. `surveillance:type=flock safety`) for review rather than dropping or trusting them. |
| **REQ-R9-27** | `PhysicalAsset.upstream_ids[]` MUST adopt the OSM `ref:<source>` namespacing convention, preserving upstream identifiers such as `ref:sous-surveillance_net`. |
| **REQ-R9-28** | Camera conflation MUST use distance-banded rules with an explicit uncertainty band (default <5 m merge, 5–10 m flag as possible duplicate, >10 m distinct) and an age-based staleness flag applied at ingest, per the field-tested sous-surveillance import parameters. |
| **REQ-R9-29** | Every ingested source MUST record its reachability test result (HTTP status, blocking mechanism, date) so that known-blocked sources such as WhatDoTheyKnow, ASPI and Légifrance are not retried blindly and have a documented fallback route. |
| **REQ-R9-30** | Coverage and incompleteness metrics (§7.1 Goal 6) MUST be normalised per jurisdiction **and annotated with import provenance**, so that bulk-import artefacts (France's 75,926 OSM objects) are not read as genuine density differences. |
| **REQ-R9-31** | Each country adapter MUST satisfy all 18 items of the jurisdiction-adapter checklist (Part I), including a named local partner/reviewer; an adapter without one ships read-only and non-public. |
| **REQ-R9-32** | The de-Americanisation work (REQ-R9-01 … REQ-R9-21) SHOULD be executed during Stage 1, not deferred to Stage 6, because retrofitting it after five stages of U.S. data is materially more expensive than building it generically at the outset. |
