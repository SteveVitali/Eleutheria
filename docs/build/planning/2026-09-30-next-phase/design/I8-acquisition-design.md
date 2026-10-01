# I8 — Acquisition and ingestion design (Round 11)

Row **I8** of `META_PLAN.md` Stream I (owner D). It turns I7's prioritized backlog into a sequenced Round-11 plan that
configures the new sources and ingests them into **production**, which is what the operator asked for (§7.1, "configure them
for ingestion and ingest them into prod"). Every production step waits for the operator's HG-03 rights lines and a verbatim
per-wave production go.

- **Written** 2026-09-30, work window (`date -u`) 21:38:05Z → 22:16:00Z, by Claude Code (Opus 5.5) in the planning worktree
  (`claude/next-phase-planning`, HEAD `c5dd458c`). Nothing was committed. No control file, registry, target, cadence, ops or
  test file was edited. No production system was changed.
- **Production reads (read-only, P3):**
  - `gcloud sql instances list/describe` at 21:40:23Z;
  - `gcloud run jobs list` and `gcloud scheduler jobs list` at 21:40:31Z.
  - No values were copied except tier, disk and counts (P14).
- **Web, secrets and identity:** no web searches or fetches were run, and no request carried the operator's identity to a
  third party (P16). The gcloud reads are the operator's own project.
- **Outputs**, and nothing else:
  - this note;
  - `data/acquisition_plan.csv`: 694 rows, one per I7 unit, covering W, Tier 1, Tier 2 and Tier 3;
  - `findings/incoming/I8.csv`: NEW-1…NEW-8.

> **Planning only.** The registry rows, targets, cadence rows, jobs and tickets below are proposals. Rights lanes and
> Part VIII lanes are classifications, never decisions. HG-03, the per-wave production go, Q-23 and HG-11 belong to the
> operator (P4). Status words follow P5: code tickets end **fixture-verified**, activation tickets end **live-executed**,
> and only a release makes anything **public**.

**Evidence rule.** Every factual sentence cites one of:
- `file:line` in the repo;
- a planning note, as `G1:65`, `I7 §6.2` and so on;
- a candidate id, whose row in `data/candidates_consolidated.csv` holds the evidence;
- a live read above.

Estimates carry the word *estimate* or *inference*. Evidence for planning notes and code was gathered by three read-only
sub-agents and spot-checked here. The load-bearing code citations (§2) were re-read directly.

---

## 0. Summary

**What Round 11 acquires, by wave.** "Candidates" counts I7 units.

| wave | content | candidates | new registry rows | est. claims | live window (earliest; §7.3) |
|---|---|---|---|---|---|
| **A** | Widening: Legistar keyword pass, USAspending/CROL vocabulary, 2026 statute seed, label fixes | 43 of W | 0 | ≈ 18k | 2026-10-19 → 10-23 |
| **B** | Tier 1: DOT/CCTV, agency ALPR/Flock, ATE, registers, statutory disclosures, CCOPS/policies, grants/council docs | 108 | ≈ 89 (+7 targets under 4 flipped sources) | ≈ 250k | 2026-10-26 → 11-05 |
| **C** | Widening: OSM becomes the **origin** of the national ALPR layer (plus speed cameras and AU) | 3 of W | 0 | ≈ 1.11M | default 2026-11-16 → 11-20 (earliest 10-26) |
| **D** | Tier 2 subset, conditional on operator lines | 151 (143 ACQ + 8 via G2 step 5) | ≤ 140 (3 of the 143 are flips of existing gated rows) | ≈ 115k | 2026-11-23 → 12-04, 12-14 → 12-18 |
| later | Tier 2 remainder | 130 | — | — | Round 12+ with named triggers |
| none | Tier 3 | 259 | — | — | not acquired (I7 §6.4) |

**Findings that change the shape of I7's plan** (all in `findings/incoming/I8.csv`):
1. **Widening `osm_overpass` alone would not make OSM the origin of the national ALPR layer** (NEW-1).
   - OSM geometry and technology ride `record_kind="asset"` rows, which `PgClaimSink` skips (`db/src/db/claim_sink.py:882-888`).
   - `physical_asset_rows` has no production caller (`connectors/src/connectors/osm.py:428`; only tests call it).
   - Camera-site ER pools only `traffic_camera:%` subjects (`resolution/src/resolution/camera_sites_pg.py:119-125`).
   - So the OSM widening is an M-sized connector and ER change (ACQ-17), not configuration.
2. **The Legistar and CROL "widenings" are adapter changes too** (NEW-2).
   - Legistar pulls only `$top=100&$orderby=MatterLastModifiedUtc desc` per tenant, with no `$filter` and no paging
     (`procurement_vocab.toml:346`).
   - CROL pulls only the latest 500 notices (`procurement_portal_tenants.toml:275-295`).
   - The historic Flock/ALPR matters I3 and I5 found with `substringof` are unreachable today.
3. **Four more gaps, each a precondition written into ACQ-01:**
   - Tooling cannot add a second batch round, and it creates triggers already enabled (NEW-4).
   - The reviewed ArcGIS rate of 10/min is not applied to camera-registry targets, which run at 60/min (NEW-3).
   - 63 of I7's proposed source ids are truncated mid-word, and some are mis-prefixed (NEW-5).
   - Tier-1 ATE "violation" datasets would put 10⁵–10⁶ claims in the spine unless aggregated (NEW-7).

**Ticket count.** 28 tickets, ACQ-01…ACQ-28 (§8):
- **Core, 19 tickets:** 3 enablers (ACQ-01…03), 4 widening code tickets (ACQ-04…06 and the OSM origin, ACQ-17), 8 Tier-1 family tickets, 3 activation tickets (A, B, C) and the closeout, ACQ-28.
- **Conditional, 9 tickets:** 8 Tier-2 family tickets plus the Wave-D activation.
- **Sizes:** 9 S and 20 M-sized units, counting ACQ-23 as two parts (23a, 23b). Nothing is L: the one L-shaped family, international portals, is the one that is split.

**New connector families for Tier 2.** Eight fit Round 11, conditional on operator lines (§6.2):
- aggregate lanes (Socrata `$group` and ArcGIS `outStatistics`);
- federal datasets;
- agenda platforms v2;
- international open-data portals and files, plus OGC WFS;
- the Puerto Rico legislature (SUTRA);
- document-list pages;
- the S1 programme-level lane;
- the Tier-2 reuse wave.

The long tail waits for later rounds: SEC EDGAR (Q-30), court bulk data (C8), OCDS, vendor pages, and bespoke agenda systems.

**Capacity and cost** (§7.4):
- **Round-11 volume:** ≈ 1.5M claims, about 3.8 GB at the measured ≈ 2.55 KB per claim (inference). The OSM origin is 74% of it.
- **Starting point:** Cloud SQL `sig-pg` is `db-custom-1-3840` with a 15 GB SSD, 6.42 GB used (`G1:64-65`), and unlimited autoresize (live read).
- **Year-end projection:** 11–17 GB. The spread comes from organic growth, which has only been measured once.
- **Recommendation:**
  - Answer Q-23 with an autoresize cap of 40 GB and pre-grow the disk to 25 GB before Wave C (≈ +$1.70/mo).
  - Keep the tier, but bump it temporarily to `db-custom-2-7680` for the Wave-C first run and ER rematerialization (≈ $3 one-off).
  - Scale permanently (≈ +$49/mo) only on named triggers.
- **Steady-state delta:** ≈ +$4–6/mo against G1's ≈ $90–100/mo estimate. Q-10 is still unanswered.

**Coverage outcome** (§9):
- **After Waves A–C:**
  - 12 of the 14 I1 blind spots move (#3 needs PKG-06/K4; #12 stays dark);
  - 7 of 10 tier-A states (AR, DE, ME, MI, NH, VT, WV) and 3 of 5 tier-B (DC, HI, NM);
  - 13 of 36 thin large cities;
  - every I2 technology class, with ATE only once ACQ-03 lands;
  - the national ALPR layer from its origin.
- **Wave D, if its lines are answered:** adds RI and ND, about 7 more thin cities, Puerto Rico, and camera layers in up to 10 countries.
- **Stays dark:**
  - MS, WY and MT;
  - AS, MP and every tribal nation;
  - North Las Vegas and about 15 other thin cities;
  - Flock's own customer, sharing and audit data;
  - Axon Fusus and Community Connect;
  - EDGAR vendor disclosures;
  - records and court corpora;
  - all person-level data, by design.

---

## 1. Inputs and method

**Read in full or in the named parts:**
- `META_PLAN.md`: §3 (P3, P4, P15, P16), Stream I, §7 (Q-19…Q-23, Q-30) and §7.1.
- `research/I7-candidates.md` in full, `design/I7-rights-packets.md` §1–§5, and `data/candidates_consolidated.csv` (all 72 columns).
- Via cited agent reports:
  - `research/I1-source-coverage.md` §1, §4 and §7;
  - `research/G1-ops.md`, `design/G2-activation.md` and `design/G3-release-model.md` in full;
  - `research/F5-eng-debt.md` (PKG-02/06/07/11/12);
  - `research/J4-redistribution-matrix.md` §2 and §9;
  - `design/H2-branch-ci.md`.
- **Code:** the connector framework and families under `connectors/src/connectors/**`, `connectors/src/connectors/data/*.toml`, `ops/cadence.toml`, `ops/src/ops/**` (scheduled-ingest, roll-jobs), `ops/gcp/scheduled-ops.sh` (read only), `resolution/` camera-site ER, and the relevant tests.

**Method.**
1. **Map the code.** Establish what the code does today (§2), because I7 classified connector reuse from the candidates' side.
2. **Re-route each unit** to the family that fits its output:
   - statutory reports go to the disclosure connector, not `dossier_documents` (NEW-8);
   - violation datasets go to aggregate transports (NEW-7).
3. **Write the plan.** Consolidate registry rows per publisher and channel, then write one plan row per I7 unit. The routing
   rules are applied mechanically and listed in §6.4, so the CSV can be re-derived by reading them.
4. **Place the waves** in the fixed calendar (G1, G2, G3).
5. **Project capacity** from measured unit volumes.
6. **Project coverage** per blind spot.

**Deviations.**
1. **The CSV generator is not committed.** It was written in the session scratchpad; this row may write only its three
   outputs. §6.4 states its rules completely.
2. **Claim estimates are model-based:** about 10 claims per site, 4 per aggregate row, ~12 per document and ~5 per list item (§5.0).
   - Per-feature counts come from I7's live reads (`count=` values). Where the count is unknown, 50 features are assumed.
   - These are estimates, never measurements.
3. **No web fetch was needed.** I7 had already captured terms.

---

## 2. What the code does today (facts the design rests on)

| area | fact | cite |
|---|---|---|
| gates | `assert_loadable` requires `ingestion_permitted`, a permitting `compact_status` and custody MIRROR/DERIVE/REFERENCE. The live gate adds a resolved rights block, `rights_reviewed_by` and `rights_reviewed_on`. `run --mode live` exits 3 when refused | `loader.py:45-59,94-116`; `runner.py:428-451`; `cli.py:296-352` |
| routing | every source needs a `CONNECTOR_FOR_SOURCE` entry or a `live_dispositions.toml` row (a CI test); a green source with no live target exits 4 | `runner.py:69`; `tests/connectors/test_live_dispositions.py:35-55`; `live_targets.py:40-90` |
| camera layers | `dot_511` has two transports (`arcgis_query` with `outFields=*`, and `socrata_rows` with `$select=*`). Every record is typed `traffic_camera` (subject `traffic_camera:<source>:<target>:<ref>`). Targets carry no technology field | `dot_511.py:130-136,185-206,541,600-604` |
| camera claims | external ref/id, jurisdiction `{scheme,value}`, publisher, operator (only if declared), lat/lon, coordinate source, and optional name/roadway/county/status/direction. No count or aggregate predicate | `dot_511.py:585-677`; `dot_511_vocab.toml:58-73` |
| Part VIII | camera layers use a deny-list over `outFields=*`, and raw captures keep every field. OSM `user`/`uid` are stripped at extract, but the live query is `out meta center`. The residential demotion exists but is not wired | `dot_511.py:285-324`; `osm.py:132-140`; `live_targets.toml:25-30`; `policy/sensitivity.py:57` |
| OSM | the live Overpass query is the OKC bbox only (a test pins it). Geometry and technology ride asset rows that the sink skips. Version-based edit detection needs `osm_version` | `live_targets.toml:19-30`; `tests/connectors/test_live_targets.py:34-35`; `osm.py:609-626`; `claim_sink.py:882-888` |
| ER | camera-site ER pools `traffic_camera:%` subjects. Grid blocking and tiers are 1g shared ref, 3g ≤ 1 m, 4g/5g ≤ 25 m. It never merges records from the same source and never merges ALPR with traffic or CCTV. Device class comes from source-id substrings (`flock|alpr|lpr`), operator text or `camera_type` | `camera_sites_pg.py:119-125`; `camera_site_rules.toml:29-56,73-102`; `camera_sites.py:320-335` |
| lineage | mirrors are inferred from data (≥ 20 pairs, ≥ 50% share). `derived_from_source` is never persisted, and `sources.toml` has no mirror field | `camera_sites.py:421-470`; `materialize.py:297-318`; F5 PKG-12 ED-49 |
| disclosures | `government_mandated_disclosure` emits ordinance, inventory_entry, disclosure, disclosure_use and compliance_finding. Its allowlist includes usage_count, retention_period, sharing_partner and vendor_name. Index pages reach documents through per-publisher adapters. Technology is kept as literal text | `government_mandated_disclosure_vocab.toml:37-108,240-360`; `government_mandated_disclosure.py:624-653,754-824` |
| documents | `dossier_documents` uses literal-anchored per-document fields. Its three sources (`dossier_okc/tulsa/san_diego`) are gated, with no rights block | `live_targets.toml:1216-1350`; `sources.toml:7503-7512` |
| agenda | Legistar is limited to `$top=100` by recency per tenant; there are 306 tenants, ≤ 20 docs per tenant and a 350-document cap per run. The content vocab has 15 terms and 78 regexes | `procurement_vocab.toml:342-383`; `procurement.py:1808-1873`; `agenda_content_vocab.toml` |
| USAspending | the sweep has 19 keywords and 3 agencies, with `prime_max_pages=1` and `sub_max_pages=2`. The live row carries 10 keywords | `procurement_vocab.toml:560-601`; `live_targets.toml:52-56` |
| statute seed | the frozen NCSL seed covers 16 states, `as_of 2022-02-03`, with a strict parser. The row has `ingestion_permitted=false` by design and is loaded by `load-seed` | `state_alpr_statute_seed.toml:20-30`; `sources.toml:1744-1765`; `statute_seed.py:87-185` |
| politeness | host delay comes only from the target row's `rate_limit_per_min`. The default is 1.0 s. `api_allowlist.toml` declares 10/min for `services.arcgis.com`, but that is not applied to dot_511 targets | `runner.py:935-938`; `net.py:65`; `api_allowlist.toml:202-206` |
| ops | `scheduled-ops.sh` creates one job and one **enabled** HTTP trigger per cadence row. Source jobs time out at 60m, batch jobs at 36h, with 0 retries. `roll-jobs` cannot create jobs. `cadence.toml` is baked into the image. The P26.16 batch generator writes batches only if none exist | `ops/gcp/scheduled-ops.sh:107-122,234-245,278-289`; `ops/src/ops/job_roll.py`; G1 NEW-10; `docs/build/tools/p2616_batch.py:1962` |
| test pins | the permitted set is pinned to `_FLIPPED_SUBSET`, so every flip edits it (PKG-02). The camreg green-source sets are pinned too | `tests/unit/test_source_registry.py:393-394`; `tests/connectors/test_dot_511.py:872` |
| capacity | `sig-pg` is POSTGRES_18, `db-custom-1-3840`, 15 GB PD_SSD, autoresize on with limit 0 (unlimited), ZONAL, backups and PITR on, deletion protection off. 88 Cloud Run jobs and 79 schedulers exist | live read 21:40:23Z / 21:40:31Z; `G1:64-65,79-80` |

---

## 3. Design rules for Round-11 acquisition

- **R1 — One row per publisher and channel; datasets are targets.**
  - A dataset from the same publisher, the same portal and the same licence as an already-flipped source becomes a new
    **target** under that source.
  - The operator confirms such targets in the HG-03 readout as X3-like configuration; they get no new rights line.
  - This cuts I7's 108 Tier-1 rows to **≈ 89 new registry rows plus 7 targets under 4 flipped sources** (§5.9).
- **R2 — Ids are permanent, so normalize them before any row is written** (NEW-5).
  - Form: `<prefix>_<place>_<channel>`, at most 40 characters, lowercase snake case, never truncated mid-token.
  - Prefix by family: `camreg_` (camera/ALPR/ATE layers), `dot_511_` (state DOT), `procportal_`, `statrep_`
    (statutory, oversight and federal disclosures), `ccops_`, `policy_`, `grant_`, `agenda_`, `legis_`.
  - The normalized ids are in §5.
  - The ACQ-01 generator rejects any id that is a prefix of another id, and any collision with the 342 registered ids.
  - It also rejects a dataset id already present in `sources.toml` or the targets files (I7 NEW-1).
- **R3 — Technology from the first ingest.**
  - Every camera target declares a SKOS `technology` slug under PKG-07: `alpr-fixed`, `fixed-camera-*`, an ATE subtype
    after ACQ-03, and so on.
  - **No ALPR or ATE record is ever typed `traffic_camera`** (I1 NEW-9).
  - Camera tickets therefore depend on PKG-07 and PKG-11. Ingesting first and backfilling later would add more
    `traffic_camera`-only subjects to the append-only spine.
- **R4 — Jurisdiction key on every target.** State-level uses `iso.3166_2` (for example `US-DE`), never a bare code
  (I1 NEW-1; F5 PKG-06a). City- and county-level agencies also record their Census place or county GEOID in the target
  data. It is emitted as a `us.census.geoid` candidate once PKG-06a/K4 fix the sub-state key (`resolution/data/canonical_schemes.toml:22-26`).
- **R5 — Lineage.**
  - A mirror or republish of an origin being acquired is retired from cadence when the origin lands. Its past claims stay,
    because the spine is append-only.
  - Its non-independence is recorded through PKG-12 ED-49 (`derived_from`) and checked through `infer_lineages`.
  - This applies to the DeFlock/Stanford republishes → OSM, and to `ncdot_runneals_mirror` → `dot_511_nc`.
- **R6 — First-run protocol (fixes G1 NEW-8 for new sources).** Every new job and trigger follows five steps:
  1. **Create paused.** ACQ-01 adds `--paused` to `scheduled-ops.sh`.
  2. **Run once by hand** (`gcloud run jobs execute … --wait`) in a quiet window, under the wave's verbatim production go (G2 AR-1).
  3. **Verify** (§7.7).
  4. **Run again** for the +0 re-run.
  5. **Resume** the trigger.

  No new source's first execution is ever an unobserved scheduler first-fire.
- **R7 — Part VIII lanes are per family** (J4 §9):
  - **P8-5:** an `out_fields` **allowlist** replaces `outFields=*` for new camera targets, so raw captures hold only
    allowlisted fields.
  - **P8-7:** no imagery.
  - **P8-2:** documents are never re-hosted.
  - **P8-3:** matter metadata only.
  - **P8-6:** natural-person payees are dropped.
  - **P8-8:** mapper identity is never captured.
  - **Screened lanes S1–S9** apply only where the operator answered the S-line `a`.
- **R8 — Rollback is append-only** (§7.8). No `DELETE` or `UPDATE`. A rights reversal is a new dated decision. Suppression
  from a release is a withdrawal. PITR is used only through a clone, never an in-place restore (G2 AR-2).
- **R9 — Windows.**
  - No hosted first run, image roll or tier change inside G2 AR-3: days 6 00:00Z → 13 12:00Z of each month, or daily
    03:00–06:30Z.
  - No first run on a G3 cut day (the 15th, 14:00Z).
  - Activation happens on weekdays, 14:00–20:00Z (`G2:103-105`).

---

## 4. Widening group (46): exact changes, yield, tests, tickets

### 4.1 Legistar (26 units) → ACQ-02 (labels) + ACQ-04 (keyword pass); live in ACQ-07

**Adapter change** (ACQ-04; code, not configuration, NEW-2). Changes to `procurement_vocab.toml [platform_endpoints.legistar]`:
- **Add a keyword index query** beside the recency query:
  `keyword_index_query = "$filter=({or-group of substringof('<term>',MatterTitle)})&$top=1000&$skip={skip}"`.
  - Page until fewer than 1000 rows come back.
  - Split the terms into 3–4 OR-groups so each URL stays under ~1,500 characters.
- **Keep the recency query** unchanged. Two index passes per tenant feed the same `agenda_index` rows, so a matter seen by
  both passes is one claim through `content_digest` (`claim_sink.py:33-39`).
- **Filter terms:** substrings deliberately broad on the server side:
  - ALPR and vendors: `license plate`, `LPR`, `Flock`, `Vigilant`, `Fusus`;
  - RTCC: `real time crime`, `real-time crime`;
  - gunshot detection: `ShotSpotter`, `SoundThinking`, `gunshot`;
  - drones: `drone`, `unmanned aer`;
  - face recognition: `facial recognition`, `Clearview`;
  - forensics and monitoring platforms: `Cellebrite`, `GrayKey`, `Grayshift`, `Magnet Forensics`, `Dataminr`, `Babel Street`;
  - school surveillance: `Gaggle`, `GoGuardian`, `Securly`, `Lightspeed`;
  - ATE: `Verra`, `red light camera`, `speed camera`, `speed safety`, `automated enforcement`, `automated traffic`;
  - monitoring and BWC: `electronic monitoring`, `body-worn`, `body worn`;
  - other vendors: `Axon`, `BriefCam`, `Genetec`, `Rekor`;
  - catch-all: `surveillance`.
- **Precise filtering happens client-side.** Word-boundary regexes from `agenda_content_vocab.toml` run on the returned
  titles. This drops server-side noise: `Axon` inside `Saxon`, `UAS` inside `persuasive`, workers-comp titles on Cook
  County (I4-C218), and so on.
- **Order of work:**
  1. Test `substringof` case behaviour first (I4 Q5). *Inference:* the InSite back end is case-insensitive by collation.
  2. The fixture test pins the result.

**Content vocabulary** (ACQ-04). `agenda_content_vocab.toml` gets a versioned bump. It adds ATE, mobile-forensics,
video-analytics, biometric, SMM, electronic-monitoring and school-surveillance terms (I4 NEW-6), with SMM given word
boundaries. The per-run document caps (20 per tenant, 350 per run) stay as they are. Document fan-out is not the widening:
the matter index is.

**Label fixes** (ACQ-02, X4; I7 packets §5 M1–M5). The `jurisdiction` strings in `agenda_tenants.toml` change:

| row | old label | new label |
|---|---|---|
| `charlotte_ia` (:1329) | City of Charlotte, IA | Charlotte, NC |
| `concord_ca` (:1669) | City of Concord, CA | Concord, NH |
| `san_bernardino_ca` (:3189) | City of San Bernardino, CA | San Bernardino County, CA |
| `newark` (:2749) | unresolved | Newark, NJ |
| `clark` (:1589) | unresolved | Clark County, NV |
| `carrollton_ga` (:1279) | City of Carrollton, GA | Carrollton, TX |

- **Keys stay unchanged**, unless a grep proves a key never enters a claim identity. Agenda subjects are
  `agenda_item:<src>:<tenant>:<id>`, and the ticket confirms whether `<tenant>` is the key or the API slug.
- **M6:** mark `ncdot_runneals_mirror` as a mirror of NCDOT (see ACQ-08).
- **M7:** point `faa_drone_waivers.homepage_url` at the Part 107 and Part 91.113 tables.
- These are registry edits under X4. The spine is untouched.

**Yield** (live-read counts from I3 and I5, in the CSV's `volume_estimate`).

| tenant (unit) | matters found | est. claims | unit |
|---|---|---|---|
| Metro Nashville (I5-C123) | 58 | 232 | I7-U114 |
| Madison (I5-C121) | 37 | 148 | U112 |
| Newark NJ (I5-C117) | up to 200 (cap) | ≈ 800 | U120 |
| Charlotte NC (I5-C116) | 19 | 76 | U119 |
| Oakland ShotSpotter (I4-C076) | 19 | 76 | U130 |
| Columbus (I3-C056) | 17 + 3 | 80 | U123 |
| Cleveland (I5-C118) | 13 | 52 | U110 |
| Louisville (I3-C057) | 9 + 2 | 44 | U124 |
| Winston-Salem, Dallas, Mesa, Cook County EM, St. Paul, Albuquerque, Detroit, Brazoria, OUSD, Culver City, Fresno, Washoe, Concord NH, Clark, San Bernardino | 1–10 each | 4–40 each | U111, U113, U116, U121, U122, U125, U126, U129, U133–U135, U139–U141, U109 |
| **all 306 tenants** (family I3-C048) | ≈ 1,500–3,000 matters (*inference*) | ≈ 6,000 | U117 |
| Milwaukee FR (I4-C117) | 4 (already matched) | regression check only | U131 |
| S.T.O.P. tracker (I6-C023) | — | 0 (vocabulary seed only) | U151 |

- **Total:** ≈ 7.9k claims.
- **Cities gaining agenda evidence:** Cleveland, St. Paul, Madison, Nashville, Albuquerque, Charlotte, Newark,
  Winston-Salem and Detroit (GL1), plus Concord NH (tier-A state).
- **Two tenants to verify:** OUSD (I4-C205) and Washoe (I9b-C105) point at `granicusideas.com` pages. If either is not a
  Legistar tenant, it moves to ACQ-22.

**Part VIII.** P8-3 applies: matter metadata only, and attachments and minutes stay out. The incremental-exposure rule
covers private names in titles (I7 §2). The existing forbidden-token guard (`procurement.py:1159,1216`) is kept, and the
vocabulary precision tests are the screen for I4-C218.

**Tests** (ACQ-04):
- fixtures for keyword-filtered, paged index JSON for 3 tenants (`cabq`, `columbus`, `newark`), including a second page;
- false-positive fixtures (Saxon, persuasive, workers-comp);
- a shadow run with `changed_count == 0`;
- a +0 replay;
- a label test showing the six rows resolve to the corrected jurisdictions.

**Ops.** Per run, about 306 × (1 recency + 2–4 keyword pages) plus 350 documents, which is ≈ 1,300–1,600 requests at
1 req/s, or ≈ 25–30 min. ACQ-01 adds a per-row `task_timeout` and raises `sig-ingest-legistar` from 60m to 3h. The cron
`0 5 20 * *` is unchanged.

### 4.2 USAspending (5) and NYC CROL (1) → ACQ-05; live in ACQ-07

**Changes to `procurement_vocab.toml [usaspending_sweep]`:**
- **Keywords:**
  - forensics (T19): Cellebrite, GrayKey, Grayshift, Magnet Forensics, AXIOM, Oxygen Forensic, Belkasoft, MSAB/XRY;
  - SMM (T20): Dataminr, Babel Street, Skopenow, ShadowDragon, Voyager Labs, Cobwebs, Fivecast;
  - data brokers (T21): LexisNexis Risk, Thomson Reuters Special Services, TransUnion, Fog Data Science, Penlink;
  - ATE: red light camera, speed camera, automated traffic enforcement;
  - counter-drone: counter-UAS, counter unmanned.
- **Vendor names**, used as a `recipient_search_text` slice rather than keywords: Flock Safety/Flock Group, Axon
  Enterprise, SoundThinking/ShotSpotter, Skydio, BRINC, Clearview AI, Verra Mobility, Rekor, Genetec, BriefCam, Palantir.
  Motorola Solutions is excluded as a bare name because radio contracts would drown it; it is matched only together with
  a surveillance keyword.
- **Assistance-listing filter** via `program_numbers`: ALN 16.835, BJA BWC (I4-C250, 613 awards live-read). The FEMA
  C-UAS ALN is added when its number is verified at origin.
- **Bounds:** `prime_max_pages` rises from 1 to 5, with a bounded run.

**Adapter work.** Add `program_numbers`, `recipient_search_text` and a recipient-type exclusion. P8-6 drops natural-person
and sole-proprietor recipients, and each run logs the count it dropped. Align `live_targets.toml [usaspending]`'s
`post_body` keywords with the sweep.

**CROL (I9b-C002).**
- `procurement_portal_tenants.toml [tenants.new_york_ny]` gets an optional `where` template (a SoQL `upper(vendor_name) like
  …` OR-group), beside the latest-500 recency pull.
- A client-side word-boundary post-filter rejects known false positives: "CLEARVIEW DATA SYSTEMS" and "Parsons
  Brinckerhoff" (for `%BRINC%`).
- The same `where` support serves Cook County and WA DES (ACQ-11).

**Units that are vocabulary only:** I6-C026 (OJP awards) arrives through the ALN slices, and its pages are never fetched
(login redirect). I4-C266 (Mijente) contributes vendor names only.

**Yield:** ≈ 1,000 award rows × 8–10 claims ≈ 8k claims, plus CROL ≈ 1.8k. The award rows create the first recipient
**vendor** entities for classes SIG cannot see today (I4 NEW-5). Vendor modelling of the Atlas (I1 NEW-7) is out of I8's
scope.

**Tests:** slice-builder unit tests for ALN and recipient text; a fixture page per slice; a P8-6 fixture with an
individual recipient that gets dropped; CROL false-positive fixtures; a shadow run with diff 0.

### 4.3 OSM becomes the origin of the national ALPR layer (3 units) → ACQ-17 (code) + ACQ-18 (live)

I7 treated this as configuration. It is not (NEW-1). **ACQ-17**, M:

1. **Emit camera-site claims from OSM.**
   - For each node or way with `surveillance:type` or `highway=speed_camera`, `osm.py` also emits the camera-site predicate
     family: `camera_external_ref = osm:<type>/<id>`, `camera_latitude/longitude` (way centre), `camera_coordinate_source=osm`,
     `camera_jurisdiction = sig.unresolved` (§4.3 item 5), `camera_operator` from `operator=` (organisation only), and a
     `technology` claim under PKG-07 (`alpr-fixed`, ATE subtype, …).
   - Tag claims such as `manufacturer`, `brand`, `direction` and `camera:mount` stay as today.
   - The subjects join the camera-site ER pool: ACQ-17 extends `_TARGETS_SQL`, or emits under a pool-admitted prefix, or both.
   - The asset rows keep feeding the ODbL `physical_asset` projection once wired, but nothing depends on that.
2. **Stop capturing mapper identity (P8-8, SIG-INGEST-045e).**
   - Use `out body center qt;`, not `out meta center`. Overpass has no "meta without user" level.
   - Edit detection for these targets moves from `osm_version` to the content-digest snapshot diff that already exists
     (`osm.py:260-312`). `osm_element_history` stays the version-history channel.
   - The pinned test (`test_live_targets.py:34-35`) is updated in the same PR.
3. **National and global tiling.**
   - A discovery pass runs `out count;` per area: 50 states + DC via `area["ISO3166-2"="US-xx"]`, then every country with a
     non-zero count.
   - The fetch pass then runs `out body center qt;` per non-empty area.
   - Overpass settings: timeout 180 s, one query per ~30 s, ≈ 70–90 queries per run (inference), and a ContentDrift check
     against the discovery counts.
   - The OKC bbox query stays as one of the targets.
4. **RF-derived screen.** Nodes whose `source`/`survey` tags name Wi-Fi, BLE or RF detection keep coarsened coordinates
   (3 decimal places) until the SIG-PUB-011..014 residential screen is wired.
   - That residential screen is owed anyway, because the same exposure ships today through the ArcGIS republish (I7 §6.2).
   - It is a publication-side dependency (PKG-06b/policy), not an ingest blocker.
5. **Jurisdiction.** State and country attribution for OSM origin sites comes from PKG-06b's point-in-polygon QA at export
   (F5 PKG-06b), the same mechanism as every other source. No new geo dependency: the workspace has no shapely.
   Once PKG-06b lands, the 154k "unresolved" ALPR sites (I1 NEW-4) become attributable. This is the biggest single movement
   on I1#3.
6. **Fixtures and shadow diff.** Take two Overpass fixtures: an OKC slice and a US-state slice with ≈ 200 ALPR nodes. A
   shadow diff against the republish fixture for the same area must show ≥ 95% 1g/3g merges (shared OSM id or ≤ 1 m) in a
   test ER run.

**ACQ-18**, M, live (Wave C):
1. **Pre-state.** Take an on-demand backup (AR-2). Q-23 must be answered. Grow the disk to 25 GB and set the autoresize
   limit (§7.4). Get the tier-bump go and move to `db-custom-2-7680`.
2. **Retarget the source.** Change `osm_overpass` from weekly `12 4 * * 1` to monthly `12 8 24 * *`.
   - *Inference:* ALPR mapping and a monthly snapshot diff are adequate. The operator may keep weekly at +0 cost to the spine.
   - The job is rebuilt with the new image. The first national run is manual.
3. **Verify.**
   - The tile totals are within ±2% of the discovery counts, and within the taginfo figure of 154,814 (I3-C069) for the same date.
   - No capture contains `"user"` or `"uid"`.
   - Claims > 0.
   - A +0 re-run inserts 0 claims.
4. **Rematerialize camera-site ER.**
   - Expected: ≥ 95% of the 132,689 DeFlock-republish rows merge onto OSM origin sites, and ≈ 22k net-new sites (*inference*:
     154,814 − 132,689).
   - `infer_lineages` records the republish as the same lineage (R5). No corroboration is counted between the two.
5. **Retire the mirrors.** Remove the ALPR mirror targets `osm_surveillance_deflock` (132,689) and
   `osm_surveillance_alpr_nationwide` (19,044) of `camreg_osm_surveillance` (`camera_registry_targets.toml:2661-2674`) from
   `camreg-batch-05` before the next 10th-of-month fire.
   - The four small CCTV republish targets stay until each origin is checked.
   - The `derived_from` link is recorded under PKG-12 ED-49.
6. **Revert the tier** after the rematerialization and a 24 h soak.

**Units:**
- **I3-C069 (ALPR):** ≈ 154,814 objects × ~7 claims ≈ 1.08M, plus technology claims, ≈ 1.1M in total.
- **I4-C316 (speed cameras):** ≈ 1,383 US nodes, typed ATE. It depends on ACQ-03, and the enforcement relations are not emitted.
- **I5-C343 (AU):** covered by the global tiles. The OzWatch viewer is never fetched.

**Dependencies:** PKG-07/11, PKG-12 ED-49, ACQ-03 (speed cameras), Q-23, G2 step 1 (L44), and G1's `sig-ingest-rt` service
account (AR-8).
- The L44 dependency is deliberate. L44 rewrites `claim_evidence` under an ACCESS EXCLUSIVE lock (G2 NEW-3). Adding ≈ 1.1M
  claims **before** it would lengthen that rewrite. Doing it after keeps the lock short.

### 4.4 State ALPR statute seed 2026 refresh (11 units) → ACQ-06; live `load-seed` in ACQ-07

- **New seed, old seed kept.** Add a new committed asset `state_alpr_statute_seed_2026.toml` beside the frozen 2022 seed,
  which stays as it is (append-only, P7).
  - Its schema is a v2: every entry adds `origin_url` (the legislature or governor page), `instrument_type`
    (statute/executive_order), `effective_date` and `verified_on`.
  - It adds `supersedes_asset` and a `seeds.toml` row. The strict parser's totals re-derive for v2.
- **Entries.** Enactments verified at origin by I9a:
  - NM SB 40 ch.20; WA ESSB 6002; OR SB 1516; KY HB 58; CT PA 26-14; ID S1180;
  - MO EO 26-18, typed `executive_order`;
  - VA §2.2-5517.
  - Plus the LAPPA-2025-enumerated states, **each verified at its own origin** before entry (≈ 15, *estimate*). NCSL, LAPPA and
    GHSA serve as enumeration aids only; no claim cites them (C9 default a; I7 NEW-7).
- **Duty rows** (SIG-INGEST-050). VA §2.2-5517 I/J/K (agency reports by 1 April, the VSP aggregate by 1 July, posting) and
  the I9a duty leads (NM DPS reports from 2027-04-01, etc.) are registered as `future_statutory_disclosure_*` rows with
  `ingestion_permitted=false` and commencement dates.
- **The registry row stays as it is:** `state_alpr_statute_inventory` keeps `ingestion_permitted=false` by design (P27.2). The
  seed loads through `load-seed` (exit 4 means no seed, 5 means drift), as the 2022 seed did.
- **Yield:** ≈ 150 claims. The statute layer moves from "frozen 2022, 16 states" to "2026, ≈ 30 states, origin-cited".
- **Tests:** v2 parser round-trip, totals, `executive_order` typing, and a no-NCSL-citation assertion for new entries.

### 4.5 Widening summary

| ticket | units | est. claims | live |
|---|---|---|---|
| ACQ-02 labels | 5 label fixes (+M6/M7) | 0 | with the Wave-A image |
| ACQ-04 Legistar | 26 | ≈ 7.9k | ACQ-07 |
| ACQ-05 USAspending + CROL | 6 | ≈ 9.8k | ACQ-07 |
| ACQ-06 statute seed | 11 | ≈ 150 | ACQ-07 |
| ACQ-17/18 OSM origin | 3 | ≈ 1.11M | ACQ-18 |

---

## 5. Tier 1 (108) by connector family

### 5.0 Common elements

- **Registry rows.** Generated by ACQ-01 from the CSV's proposed fields, with normalized ids (R2) and
  `ingestion_permitted=false`.
  - Each family ticket applies the flip recipe (I7 packets §2; E4 §2) **only** for rows whose operator line reads `a`.
  - The flip sets `compact_status=public_terms_only` and custody DERIVE (documents) or MIRROR (layers). It records the
    rights block, `rights_reviewed_by` (a role), `rights_reviewed_on` and `last_verified`.
  - The same PR updates the permitted-set pin (`tests/unit/test_source_registry.py:393-394`), unless PKG-02 has replaced it
    with the invariant.
- **Wiring.** Each row gets `CONNECTOR_FOR_SOURCE` routing, a `live_targets.toml` row (`kind="dot_511_targets"`,
  `index_page`, …), a cadence batch membership, and a policy licence/compartment row where a licence is new.
- **Fixtures.** One captured response per target, taken at ticket time. A fixture over 1 MB (PA WZSSC 11.9 MB, FL 2.2 MB)
  is committed as a text extract, with the original's sha256 recorded (§8.4 of META_PLAN).
- **Shadow tests.** A `sig-connectors run --mode shadow --fixture …` test asserts `changed_count == 0`, plus a replay
  reproducibility test in the family's test file.
- **Claim model** (inference, for `expected_claims`):
  - sites ≈ 10 claims, from 1,369,210 claims over 132,689 republish rows (`G1:326`) and `dot_511.py:585-677`;
  - aggregate rows ≈ 4;
  - documents ≈ 12;
  - list items ≈ 5;
  - unknown feature counts assume 50.
- **Verification is the same for every row** (§7.7): review-status green, a manual first execution with captures landed
  and claims > 0, a +0 re-run, technology typed, the jurisdiction key set, and the coverage delta recorded.

### 5.1 ACQ-08 — Official camera layers: DOT and police/city CCTV (10) · `dot_511(arcgis_query)` · batch `r11-layers-01` `17 7 16 * *`

| cand | proposed id (normalized) | features | est. claims | batch line |
|---|---|---|---|---|
| I5-C003 | `dot_511_de` (target `deldot_cameras`; also hosts I5-C005 in ACQ-10) | 445 | 4,450 | RB-02 |
| I5-C001 | `dot_511_vt` (CCTV rows only, filtered by `DeviceType`) | 88 | 880 | RB-02 |
| I5-C009 | `dot_511_wv` | 73 | 730 | RB-02 |
| I5-C002 | `dot_511_mi` (stale since 2021: record the last-edit date) | 681 | 6,810 | RB-02 |
| I5-C017 | `dot_511_nc` (origin; `ncdot_runneals_mirror` target retired, M6) | 1,157 | 11,570 | RB-02 |
| I5-C107 | `camreg_lincoln_ne_traffic` | 55 | 550 | RB-01 |
| I5-C106 | `camreg_omaha_ne_parks` | 37 | 370 | RB-01 |
| I3-C082 | `camreg_hyattsville_md_cctv` | ≈ 50 | 500 | RB-01 |
| I3-C079 | target `denver_police_halo` under `camreg_denver_co` (if the licence matches; else `camreg_denver_co_halo`) | ≈ 50 | 500 | (existing flip) |
| I3-C081 | `camreg_seattle_wa_spd_cctv_areas` (polygons → programme areas, never device points) | ≈ 10 | 100 | RB-01 |

- **Adapter changes:**
  - a per-target `out_fields` allowlist (R7);
  - a per-target `technology`;
  - `geometry_kind = "area"` for Seattle, so the target emits an area claim and not `camera_latitude`;
  - the `DeviceType` filter for VT;
  - applying the api_allowlist rate to generated targets (NEW-3).
- **Part VIII:** P8-5 and P8-7.
- **ER impact:**
  - DOT points dedupe against existing `dot_511_*` and camreg rows in the same state, and against OSM `man_made=surveillance`.
  - Expect few merges in DE, VT, WV and MI, which have no DOT source today (I1#5).
  - NCDOT merges 1g with the mirror's refs, and the mirror's lineage is recorded.
  - Denver HALO dedupes against `camreg_denver_co` points, typed `fixed-camera` and not traffic.
- **Jurisdiction:** `iso.3166_2` state codes, plus place GEOIDs for Lincoln, Omaha, Hyattsville, Denver and Seattle (R4).
- **Rights prerequisite:** RB-02 `a` (5) and RB-01 `a` (4). Denver needs a licence check only.
- **Size:** M. **Est. claims:** ≈ 26k.

### 5.2 ACQ-09 — Agency ALPR/Flock layers, including the FDOT inventory and removal status (16) · batch `r11-layers-02` `17 7 17 * *`

| cand | proposed id | rows | est. claims |
|---|---|---|---|
| I3-C002 + I3-C003 | `camreg_fdot_flock` (targets `fdot_d3_flock_inventory` 407; `fdot_flock_removal_status` 523) | 930 | 9,300 |
| I3-C007 | `camreg_pueblo_co_flock` | 114 | 1,140 |
| I3-C012 | `camreg_rocky_mount_nc_lpr` | 74 | 740 |
| I3-C014 | `camreg_shelbyville_tn_flock` | ≈ 50 | 500 |
| I3-C015 | `camreg_temecula_ca_flock` | ≈ 50 | 500 |
| I3-C017 | `camreg_marble_falls_tx_flock` | ≈ 50 | 500 |
| I3-C019 | `camreg_prince_william_va_safety_cams` | 29 | 290 |
| I3-C020 | `camreg_milford_ct_flock` | ≈ 50 | 500 |
| I3-C023 | `camreg_elgin_il_lpr` | ≈ 50 | 500 |
| I3-C024 | `camreg_south_fulton_ga_lpr` | ≈ 50 | 500 |
| I3-C025 | `camreg_pittsylvania_va_lpr` | ≈ 50 | 500 |
| I3-C026 | `camreg_alabaster_al_lpr` | ≈ 50 | 500 |
| I3-C010 | `camreg_thomasville_ga_flock` | ≈ 50 | 500 |
| I3-C013 | `camreg_leon_fl_overwatch` (check against the live `camreg_leon_fl` org first; target-under-existing if same org) | 11 + layers | 610 |
| I3-C018 | `camreg_peachtree_corners_ga_flock` | ≈ 50 | 500 |

- **Row rules** (I7 §6.1 notes, carried into the CSV verification column):
  - I3-C002 and I3-C003 are ingested **in the same run**. Removal-status values are permit-compliance facts (S5 guard): a
    removal becomes `valid_to`, never a deletion.
  - I3-C019's proposed sites become `status=proposed`.
  - I3-C020's coordinates are `approximate`.
  - I3-C014's "Hits" column is **not** ingested.
  - I3-C013's Vigilant LPR rows are typed `alpr-fixed`, and its RTCC/CCTV layers are typed separately.
- **Why monthly cadence even for "once" layers:** the 2026 removal wave (FDOT's order; I9a NEW-2) makes currency the value,
  and a +0 re-run costs nothing.
- **Part VIII:** pass. P8-5 applies. No private-operator columns in Tier 1; those are Tier 2 under S1.
- **ER impact:**
  - The largest camera-dedupe surface. Agency points meet OSM/DeFlock ALPR points at 4g/5g (≤ 25 m). They are independent
    lineages, agency and crowd, so corroboration is legitimate unless `infer_lineages` finds a systematic share.
  - The agency is linked to Eyes on Flock portal entities by `camera_operator` and agency resolution.
  - Every row is typed `alpr-fixed`. Source-id substrings alone no longer decide device class (`camera_sites.py:320-335`).
- **Jurisdiction:** state `iso.3166_2`, plus place and county GEOIDs.
- **Rights prerequisite:** RB-01 `a`. **Depends on:** PKG-07 and PKG-11.
- **Size:** M. **Est. claims:** ≈ 17k.

### 5.3 ACQ-10 — Automated traffic enforcement: layers and aggregates (15) · batch `r11-ate-01` `17 7 18 * *`

**Prerequisite:** ACQ-03 adds an ATE technology concept to the ontology, with subtypes red-light, speed, bus-lane,
school-bus stop-arm and work-zone, plus a zone geometry kind (I1 NEW-8; I4 NEW-9). Until then the 15 rows have rights and
access ready but no concept (I7 §6.1).

| cand | proposed id / target | shape | est. claims | batch |
|---|---|---|---|---|
| I5-C005 | target `deldot_red_light` under `dot_511_de` | 60 sites | 600 | RB-01 |
| I4-C051 + I4-C052 | targets under `dot_511_dc` (licence CC-BY-4.0 check; else `camreg_dc_ddot_ate`) | ≈ 550 sites + camera-month counts | 5,500 + 79,200 | RB-06 |
| I4-C055 + I4-C056 + I4-C062 | `camreg_montgomery_md_ate` (3 targets) | site × quarter counts + 2024 site layer | 9,600 + 2,400 + 2,000 | RB-06/RB-01 |
| I4-C053 + I4-C054 | targets under `camreg_chicago_il` (live; same portal) | camera × month via SoQL `$group` | 23,000 + 50,400 | (existing flip) |
| I4-C058 | `camreg_nyc_mta_bus_lane_ate` | route rows | 200 | RB-01 |
| I4-C061 | `camreg_tacoma_wa_ate` | ≈ 50 sites | 500 | RB-01 |
| I4-C064 | `camreg_howard_md_school_zone_ate` | zone geometries | 300 | RB-01 |
| I9b-C084 | `camreg_lakeland_fl_red_light` | 11 | 110 | RB-01 |
| I9b-C083 | `camreg_suffolk_ny_red_light` (2015 snapshot; CC-BY-4.0 attribution) | 215 | 2,150 | RB-06 |
| I9b-C082 | `camreg_medford_or_ate` | 5 | 50 | RB-01 |
| I5-C015 | `camreg_ctdot_speed_safety` (approximate locations) | 89 | 890 | RB-01 |

- **Adapter changes** (NEW-7). Two aggregate transports, reused by Tier 2 (ACQ-20) and ACQ-11:
  - **`socrata_aggregate`:** `$select=<camera_id>, date_trunc_ym(<date>), sum(<violations>)&$group=…&$where=<date> >= '<window>'`;
  - **`arcgis_outstatistics`:** `outStatistics` with `groupByFieldsForStatistics`.
- **An aggregate predicate family:** `enforcement_count {period, count, measure}` on the camera or programme subject. It is
  on the allowlist, while the `plate_read`, `person` and citation genres stay forbidden.
- **Window:** 2023-10 onward for the first run, about 36 months. After that, monthly increments of ≈ 4.6k claims (*inference*).
- **Part VIII:** aggregates only, never per-violation or citation rows. Plate-level datasets (I4-C059, I4-C060) stay Part VIII
  blocked (X2).
- **ER impact:** ATE sites dedupe against the live ATE camreg rows (Baltimore ATVES, `camreg_chicago_il` points, …) and
  against OSM `highway=speed_camera` from Wave C, at 3g/4g. All typed ATE, never `traffic_camera`.
- **Rights:** RB-01 `a`, RB-06 `a`. The Chicago targets ride the existing flip. Chicago's revocation clause (C5) applies to
  them as it already does to `camreg_chicago_il`.
- **Size:** M. **Est. claims:** ≈ 177k (93% aggregates). This is the one Tier-1 group where volume matters (§7.4).

### 5.4 ACQ-11 — Procurement and programme registers (3) · batch `r11-procurement-01` `17 7 19 * *`

| cand | proposed id | route | est. claims |
|---|---|---|---|
| I3-C077 | `procportal_cook_il_awards` | `procurement(portal_tenants: socrata)` + `where` vendor/description filter (from ACQ-05) | 400 |
| I6-C010 | `procportal_wa_des_contract_sales` | same; `where` on surveillance vendors and contract numbers; public-entity customers only | 18,000 |
| I3-C084 | `camreg_dc_ovsjg_camera_rebate` | `arcgis_outstatistics` (ward × year counts) | 320 |

- **Part VIII:** P8-6 drops natural-person payees. I3-C084 is **programme-level only**: no registrant location, name or
  address (P8-4; the S1 rule applied to a Tier-1 row).
- **ER:** purchase records link to vendor entities (from ACQ-05) and to buyer agencies, and link to Legistar contract matters
  by contract number where both exist.
- **Rights:** RB-06 `a` (Cook), RB-04 `a` (WA DES), RB-01 `a` (DC).
- **Size:** S.

### 5.5 ACQ-12 — Statutory disclosures I: ALPR regimes (10) · `government_mandated_disclosure(statutory)` · batch `r11-disclosures-01` `27 7 21 * *`

I7 routed these to `dossier_documents`. I8 re-routes them to the disclosure connector (NEW-8), for three reasons:
- the disclosure connector's claim types and allowlist *are* the statutory-reporting model (usage_count, retention_period,
  sharing_partner, audit_mechanism, legal_authority);
- its index-page adapters already fan out from an index to documents;
- `dossier_documents` is built around OKC's gated, literal-anchored dossier fields.

**Changes** (generalizing the connector beyond municipal CCOPS):
- state and federal publishers in `[sources]`, with the jurisdiction scheme `iso.3166_2`;
- a technology-literal → SKOS mapping table, so disclosure claims are typed (PKG-07's slug set);
- a `statutory_report` genre in `[genre_claim_types]`: `disclosure_use` only where the report states use;
- one `[adapters.<publisher>]` row per publisher (`doc_url_contains`, `doc_suffixes`, `technology_*_pattern`).

| cand | proposed id | documents / items | est. claims |
|---|---|---|---|
| I9a-C036 | `statrep_wa_ago_alpr_registry` | 76 agency registrations + policy links | 690 |
| I3-C039 | `statrep_mn_bca` (target `lpr_agency_list`; also hosts I4-C005 UAV reports) | agency list + ~726 location strings | 3,000 |
| I3-C042 | `statrep_va_vsp_alpr` | 1 spec | 12 |
| I3-C043 | `statrep_va_vscc_alpr` | 1 report (16 pp) | 30 |
| I9a-C011 | `statrep_ne_crime_commission_alpr` | 89 PDFs | 1,070 |
| I9a-C012 | `statrep_vt_dps_alpr` | 8 reports | 100 |
| I9a-C019 | `statrep_il_isp_alpr` | ≥ 4 reports | 50 |
| I9a-C042 | `statrep_austin_tx_auditor` | 1 audit | 20 |
| I9a-C047 | `statrep_md_dls_mandated_reports` (index; surveillance-relevant entries only) | ≈ 20 | 100 |
| I6-C040 | `statrep_va_rga` (index; same) | ≈ 20 | 100 |

- **Modelling rule:** WA AGO and MN BCA entries are agency **assertions of registration** (`inventory_entry`), not verified
  deployments. The AGO says it did not verify them (I9a-C036).
- **Part VIII:** P8-2 applies. Officer names are never extracted; §43.4 gates any named person.
- **ER:**
  - Agencies resolve against the agency registry and the Eyes on Flock portal agencies.
  - MN BCA location strings stay literals. They are not geocoded into points in Round 11 (*inference*: geocoding would create
    a new geometry lineage and needs its own review).
- **Rights:** RB-03 `a` (10).
- **Size:** M. **Est. claims:** ≈ 5.2k.

### 5.6 ACQ-13 — Statutory disclosures II: UAV/FRT/CSS/interception/ATE reports and federal privacy documents (23) · batch `r11-disclosures-02` `27 7 22 * *`

- **Grouped state rows:**
  - `statrep_co_frt_accountability`: the CO family I4-C102, with Arvada I4-C103 as its first target;
  - `statrep_wa_wtsc_ate`: the WTSC 2026 report I4-C067 plus the ~29 city reports I4-C068, enumerated from the WTSC index;
  - the MN UAV reports I4-C005 as a target under `statrep_mn_bca`.
- **One row each:**
  - `statrep_wa_watech_frt` (I4-C100);
  - `statrep_detroit_mi_frt_weekly` (I4-C108; the weekly index is enumerated, and per-week counts are `usage_count` claims in
    the `disclosure_use` genre only);
  - `statrep_me_dps_uav` (I9b-C053);
  - `statrep_il_icjia_drone` (I4-C006);
  - `statrep_hi_judiciary_interception` (I9b-C078);
  - `statrep_mn_court_interception` (I9b-C077);
  - `statrep_md_msp_css` (I9b-C065);
  - `statrep_de_diac` (I4-C274; its technology concept is proposed `fusion-center`, pending the ontology);
  - `statrep_seattle_wa_sdot_ate` (I4-C069; its site table becomes ≈ 50 ATE site literals);
  - `statrep_fl_flhsmv_red_light` (I9b-C056; ~10 editions);
  - `statrep_pa_wzssc` (I9b-C057);
  - `statrep_seattle_wa_oig` (SRC-012).
- **Federal rows:**
  - `statrep_us_dhs_privacy_compliance`, one row with 5 targets: I4-C167 (PIA hub, ~98 PIAs), I4-C259 (component indexes,
    189+), I4-C261 (OBIM HART), I4-C269 (CBP BSS), I4-C260 (CBP telemetry);
  - `legis_us_dhs_sorn_plate_data` (I3-C072, ~8 SORNs, fetched as Federal Register document pages; no API adapter needed).
  - PIAs are E-Government Act §208 mandated disclosures, so the disclosure model fits them.
- **Part VIII:** P8-2 applies. Wiretap and interception reports emit institution-level counts only. Judge and prosecutor names
  are not extracted; their appendices are Tier 2 S5.
- **Rights:** RB-03 `a`, RB-04 `a` (Detroit), RB-05 `a` (DHS, CC0-1.0, federal works), RB-06 `a` (WTSC).
- **Size:** M. **Est. claims:** ≈ 3.6k.

### 5.7 ACQ-14 — CCOPS reports, police policies and district self-disclosures (17) · batch `r11-documents-01` `27 7 23 * *`

- **CCOPS (5), `government_mandated_disclosure(ccops)`:** `ccops_columbia_mo`, `ccops_st_louis_mo`, `ccops_dayton_oh`,
  `ccops_anchorage_ak` (the ordinance; a GL1 city) and `ccops_austin_tx` (the TRUST resolution). This updates the stale CCOPS
  denominator (I6 NEW-3, I9a NEW-6).
- **Police policies (7), `agency_policy`:**
  - The okcpd_policy path is generalized: `OkcDocumentConnector` subclasses become one `agency_policy` connector with
    `document_page` targets and inline clause literals (`okc_documents.py:689`; `live_targets.toml:308-338`).
  - Rows: `policy_houston_tx_hpd`, `policy_albuquerque_nm_apd` (SOP 1-22 ALPR), `policy_bangor_me_pd`,
    `policy_little_rock_ar_pd`, `policy_orange_county_ca_sheriff` (CSS 610; RB-07 facts and citations),
    `policy_pasadena_ca_pd` (CSS 620; RB-07), and `legis_ca_gov_code_53166`.
- **District pages (4 rows + 1 channel):** `policy_st_cloud_mn_isd742`, `policy_onslow_nc_schools`,
  `policy_pflugerville_tx_isd` and `policy_whitesboro_ny_csd`.
  - These are self-disclosures with vendor_name/product_name `inventory_entry` claims in the `policy_document` genre.
  - The family I9b-C040 is the discovery channel. **It gets no registry row.**
- **Part VIII:** P8-2 applies. No student data; the pages disclose vendor use only.
- **Rights:** RB-03 `a`, RB-07 `a`.
- **Size:** M. **Est. claims:** ≈ 0.6k.

### 5.8 ACQ-15 — Grant, council and procurement documents, and bills (14) · batch `r11-documents-01`

- **Grants, `dossier_documents(clause_fields)`, with rights-reviewed new rows rather than the gated `dossier_*` rows:**
  - `grant_tx_txdmv_mvcpa` (≈ 100 lines/yr);
  - `grant_ca_bscc_ort` (≈ 55 grantees);
  - `grant_fl_senate_lfir`;
  - `grant_al_adeca_psn`;
  - `grant_nj_oag_bwc`;
  - `grant_ok_dac_jag_lle` (SRC-009).
- **Council and procurement documents:**
  - `agenda_haskell_ar_council` (AR tier-A);
  - `agenda_des_moines_ia_council`;
  - `agenda_jasper_sc_council` (Cellebrite);
  - `procportal_davie_fl_purchasing` (Cellebrite sole source);
  - `procportal_forsyth_nc_purchasing` (RTCC RFP);
  - `legis_gu_governor` (Guam; CC0 per I7-F032).
- **Bills:** I9b-C068 (AZ HB 2574) and I9b-C069 (NY S7037) are **targets under the live `openstates` source**, added to
  `openstates_plan.toml`. They are configuration, with no new row.
- **Modelling:** grant lines become `grant_award {recipient agency, amount, purpose literal, programme}`. Procurement
  documents become `contract`/`buyer`. Never `deployment`: procured ≠ deployed.
- **Rights:** RB-04 `a`, RB-06 `a` (Guam).
- **Size:** S–M. **Est. claims:** ≈ 1.7k.

### 5.9 Tier-1 roll-up

| ticket | rows | new registry rows | targets under existing flipped sources | est. claims | rights lines needed |
|---|---|---|---|---|---|
| ACQ-08 | 10 | 9 | 1 (`camreg_denver_co`) | 26.5k | RB-02, RB-01 |
| ACQ-09 | 16 | 15 (14 if Leon is the same org) | 0–1 | 17.1k | RB-01 |
| ACQ-10 | 15 | 8 | 4 (`dot_511_dc` ×2, `camreg_chicago_il` ×2); DE is under the new `dot_511_de` | 176.9k | RB-01, RB-06 |
| ACQ-11 | 3 | 3 | 0 | 18.7k | RB-04, RB-06, RB-01 |
| ACQ-12 | 10 | 10 | 0 | 5.2k | RB-03 |
| ACQ-13 | 23 | 16 | 0 (plus 7 consolidated members) | 3.6k | RB-03/04/05/06 |
| ACQ-14 | 17 | 16 | 0 (plus 1 channel with no row) | 0.6k | RB-03, RB-07 |
| ACQ-15 | 14 | 12 | 2 (`openstates`) | 1.7k | RB-04, RB-06 |
| **total** | **108** | **≈ 89** | **7 (+1 Leon, if it matches)** | **≈ 250k** | RB-01…RB-07 |

These are the id corrections to I7's proposals (NEW-5). Every other Tier-1 id in the tables above replaces I7's. The CSV
keeps I7's unit and candidate ids, so both forms stay traceable.

| I7 proposed id | issue | I8 id |
|---|---|---|
| `procportal_cook_county_il_procurement_awarde` | truncated | `procportal_cook_il_awards` |
| `camreg_montgomery_county_md_automated_red_li`, `…_automated_speed`, `…_speedcameras_202` | truncated, and split across 3 rows | `camreg_montgomery_md_ate` (3 targets) |
| `camreg_prince_william_cou_va_community_safet` | truncated | `camreg_prince_william_va_safety_cams` |
| `camreg_tacoma_wa_automated_enforcement_locat` | truncated | `camreg_tacoma_wa_ate` |
| `camreg_peachtree_corners_ga_flock_camera_loc` | truncated | `camreg_peachtree_corners_ga_flock` |
| `camreg_pittsylvania_count_va_stationary_lpr` | truncated | `camreg_pittsylvania_va_lpr` |
| `statrep_arvada_co_facial_recognition_technol` | truncated | target under `statrep_co_frt_accountability` |
| `statrep_orange_county_ca_policy_610_cellular` | truncated, wrong prefix | `policy_orange_county_ca_sheriff` |
| `agenda_jasper_county_sc_special_called_meeti` | truncated | `agenda_jasper_sc_council` |
| `procportal_forsyth_county_nc_rfp2449_real_ti` | truncated | `procportal_forsyth_nc_purchasing` |
| `policy_onslow_county_nc_schools_gaggle_safet` | truncated | `policy_onslow_nc_schools` |
| `policy_whitesboro_ny_central_school_district` | 44 chars | `policy_whitesboro_ny_csd` |
| `policy_albuquerque_nm_apd_standard_operating` | truncated | `policy_albuquerque_nm_apd` |
| `statrep_me_safety_maine_law`, `statrep_hi_hawai_judiciary_under` | garbled stop-word stripping | `statrep_me_dps_uav`, `statrep_hi_judiciary_interception` |
| `camreg_dc_automated_safety_cameras(_2)`, `camreg_chicago_il_*` | same publisher as a flipped source | targets under `dot_511_dc` / `camreg_chicago_il` |
| `camreg_de_traffic_devices_red` | same publisher as `dot_511_de` | target under `dot_511_de` |

---

## 6. Tier 2 (281)

### 6.1 What each row needs, and whether it fits Round 11

These counts come from the CSV. "R11" means an ACQ ticket, **conditional** on the operator's line.

| need | fits R11 | later | total |
|---|---|---|---|
| New or extended connector (+ rights line) | 72 | 64 | 136 |
| Part VIII screen on a reused connector (+ rights line) | 29 | 42 | 71 |
| Rights decision only (reused connector) | 37 | 7 | 44 |
| Verification or lineage step first | 5 | 1 | 6 |
| Lead, derived, mirror or channel (acquire the origin) | 0 | 16 | 16 |
| Already packeted in E4 (dossier captures) | 8 (G2 step 5) | 0 | 8 |
| **total** | **151** | **130** | **281** |

The 37 rights-only rows ride **ACQ-19**, the Tier-2 reuse wave, once their line reads `a`:
- N-lines for the non-US rows are in ACQ-23.
- RB-09 flips of existing gated rows: `dhs_fusion_centers`, `ccops_boston`, `ccops_berkeley`.
- RB-03 oversight rows (SRC-013…021, NYC DOI and Comptroller, BART).
- RB-02 state layers (Idaho ITD).
- The C6-conditional rows (Bellevue, Honolulu PD).

### 6.2 New connector families

These eight families fit Round 11. Sizes follow F5's scale: S ≤ 0.5 d, M 0.5–2 d, L > 2 d; an L must be split.

| ticket | family | design sketch | R11 rows | size |
|---|---|---|---|---|
| ACQ-19 | **Tier-2 reuse wave** | Existing families (`dot_511`, disclosure, `agency_policy`, `curated_index`) with the R1–R7 rules. It includes verification-first rows (I3-C016/C021/I5-C040 owner-org check, NEW-5 of I7; I5-C010 lat≈0 geometry fix; I5-C006 NMDOT authority), the S2 `out_fields` allowlist rows (I3-C004, I5-C104, I5-C014) and the `curated_index` S3 aggregate-only rows | 32 | M |
| ACQ-20 | **Aggregate lanes** | Reuses ACQ-10's `socrata_aggregate` / `arcgis_outstatistics`: checkbooks and payments as vendor × year sums, dropping payee names (S7): TX DIR, Mesa, the Socrata checkbook family, DE, WA, Chicago, NJ. ShotSpotter as district × month counts (S4): Detroit, Chicago, Oakland. School-bus and ATE aggregates (S3) | 14 | M |
| ACQ-21 | **Federal datasets** | One fetch-and-parse helper (CSV/XLSX/JSON) with small per-dataset adapters: US Courts wiretap summary tables, the Federal Register API documents search (term-filtered, which also serves FAA/CBP rulemakings), the OMB/DHS AI use-case inventories, the ICE 287(g) agency list (and monthly encounters as aggregates, S3) and NCES SSOCS. All RB-05 (CC0) | 8 | M |
| ACQ-22 | **Agenda platforms v2** | New platform adapters in `procurement.py` beside Legistar, PrimeGov, CivicClerk and eScribe: CivicPlus AgendaCenter (Durham, Hialeah, Bexar), CivicWeb (Jersey City, Dallas County), OnBase/AgendaOnline (Frisco, Tampa, Maricopa), Savannah's AgendaPlus and Fargo's HTML archive. The tenant rows join the `agenda_tenants` shape, and P8-3 applies | 10 | M |
| ACQ-23a/b | **International open-data portals and files** | (a) CKAN `package_search`/`package_show` and OpenDataSoft `explore`, feeding (b) file readers (CSV, GeoJSON, XLSX) and OGC WFS `GetFeature`, emitting `dot_511`-shaped camera-site claims. WMS (image-only) and STAC are later. N-lines and RB-06 `a` are required, with SIG-PUB-017 jurisdiction-conditional publication | 40 | 2 × M |
| ACQ-24 | **Puerto Rico** | A SUTRA measures adapter (7 legislative measures) and the OCPR contract registry (S7: contractor names that are natural persons are dropped). Conditional on RB-08 `a` (territorial basis; I7 NEW-6) | 8 | S |
| ACQ-25 | **Document-list pages** | An index-page → PDF/HTML enumerator for pages with no platform: cooperative contract documents (Florida Buy, NERIC, NASPO, WSIPC; facts and citations), award lists (IL GATA, OH BWC, MA BWC) and the MA capital plan. It emits `contract` / `grant_award` | 8 | M |
| ACQ-26 | **S1 programme-level lane** | Private-camera registries and Flock layers with private operators, reduced to programme facts: programme exists, agency, launch date, published registrant count. Flock layers keep the agency-operated rows only; private-operator rows collapse to a count. Drone flight logs become agency × month counts. Registrant or flight locations are never captured. Conditional on S1 `a` | 23 | M |

These families go to later rounds, with their triggers:
- **SEC EDGAR full-text search** (4 rows): when Q-30 is answered.
- **CourtListener and CAP bulk** (2): after the C8 decision and an S3 screen.
- **OCDS: UK Contracts Finder, AusTender** (2).
- **Canadian search APIs and CanadaBuys** (3): the non-commercial clause, C6.
- **Vendor pages and contract vehicles** (IU lines): after terms are captured.
- **GitHub-derived compilations** (2): derived, I = 0.
- **Bespoke agenda and document systems** (≈ 10: Laserfiche, Revize, eCode360, Miami-Dade govaction, OC agendaext, Utah PMN, CivicPlus DocumentCenter): low value per adapter.
- **OGC WMS and DATEX II** (4): images or traffic feeds.
- **Alaveteli and FragDenStaat** (2): S6 free text.
- **One-off HTML or PDF extractors** (≈ 10).

### 6.3 Rows deferred inside Tier 2, and why

| reason | rows |
|---|---|
| S7 names inside documents: extraction-time redaction for document families is not built | 23 |
| New family not worth a Round-11 adapter (§6.2 list) | 21 |
| S6 free text: SIG-PUB-014a excerpt screen for new families | 16 |
| Derived or mirror: acquire the origin | 11 |
| S5 officer and judge names: §43.4 gate | 10 |
| S4 point layers: coarsening not wired (`policy/sensitivity.py:57` has no caller) | 10 |
| E4 R6a/S2 (BidNet/Bonfire) or R4a (Edmonton) pending | 7 |
| IU terms not captured | 5 |
| Q-30 (EDGAR) | 4 |
| Channel or family with no index | 6 |
| Tribal governance (TR, S8) | 3 |
| Other: S9 row-specific screens (2), and one each for IT1/C5 OpenFEMA, IT4 GETS, IT7 Axon, C6 co-op terms, C8, FAA host unreachable, OCR, discovery-only, ArcGIS org identity, marginal class, origin withheld, per-member-office letters | 14 |

### 6.4 Routing rules (how `data/acquisition_plan.csv` was derived)

1. **W** units map by I7 widening line to ACQ-04, 05, 06 or 17 (§4).
2. **Tier 1** maps by candidate to ACQ-08…15 (§5), with the claim estimates of §5.0.
3. **Tier 2** is routed by the first matching rule:
   1. E4-packeted → `G2-step5`.
   2. The P16/EDGAR line, or `sec_edgar*` → later (Q-30).
   3. Tribal line or S8 → later.
   4. IU line → later.
   5. IT line: IT2/3/5/6 → ACQ-19 or ACQ-23, conditional on C6. Otherwise later.
   6. E4 R6a/R4a → later.
   7. Screen class (I7 packets §1.2):
      - **S2:** ACQ-19, except I4-C001, which goes later.
      - **S3:** ACQ-20 or ACQ-17 aggregate-only, except CourtListener (later, C8), ICE 287(g) (ACQ-21) and a discovery surface (later).
      - **S1:** ACQ-26, except I9a-C003 (IT7).
      - **S4:** ACQ-20 for ShotSpotter aggregates; everything else later.
      - **S5, S6, S9:** later.
      - **S7:** ACQ-20 for Socrata/XLSX payments, ACQ-24 for OCPR; everything else later.
   8. Derived → later.
   9. Channel, family-without-index, journalism lead, origin withheld, marginal, org-identity or reference-spine → later.
   10. Image-only PDF → later (OCR).
   11. Geometry defect, origin unverified or authority unverified → ACQ-19, verification first.
   12. By connector label: SoQL aggregate → ACQ-20; the federal labels → ACQ-21; agenda platform labels → ACQ-22;
       CKAN/ODS/file/WFS/data.europa → ACQ-23; SUTRA/OCPR → ACQ-24; document-list labels → ACQ-25; any other `new:` label → later.
   13. A reused connector: non-US → ACQ-23; RB-09 → ACQ-19 (flip); RB-08 → ACQ-19 (conditional); anything else → ACQ-19.
4. **Tier 3** → `defer`, with no ticket; the I7 reason is copied into `verification`.
5. **Tier-1 adjustments (R1):** the 7 targets under existing flipped sources (§5.9) are `widen`, and their `rights_batch`
   names the existing flip. The 11 consolidated members name their new row in `verification`. I9b-C040 is `defer`: it is a
   discovery channel with no registry row.
6. **Tier-2 claim estimates:** parsed from `volume_estimate`, capped at 5,000 rows, × 10 (× 4 for aggregates). Where
   unparsable, a per-family default is used (federal 3,000; aggregate 5,000; international 500; agenda 200; otherwise 60).
   They are the roughest numbers in the plan.

---

## 7. Hosted ingestion plan

### 7.1 Jobs and schedulers

**New cadence rows.** All batch rows, generated by ACQ-01's batch generator (NEW-4), in the same PR as the rows they carry.
The `unscheduled_live_sources` drift guard fails any flipped source without one (`ops/src/ops/scheduled.py:203-221`).

| batch / job (`sig-ingest-…` / `sig-sched-…`) | members | cron (UTC) | why this slot |
|---|---|---|---|
| `r11-layers-01` | ACQ-08 (9 new sources; Denver HALO runs in `camreg_denver_co`'s batch) | `17 7 16 * *` | after the day 6–13 batch window and the 15th release cut; the existing 16th trigger fires 05:00–06:09Z |
| `r11-layers-02` | ACQ-09 (15 sources) | `17 7 17 * *` | same |
| `r11-ate-01` | ACQ-10 (8 layers; the 4 existing-source targets run in their sources' jobs) | `17 7 18 * *` | same |
| `r11-procurement-01` | ACQ-11 (3) | `17 7 19 * *` | same |
| `r11-disclosures-01` | ACQ-12 (10) | `27 7 21 * *` | the 20th is Legistar |
| `r11-disclosures-02` | ACQ-13 (16) | `27 7 22 * *` | — |
| `r11-documents-01` | ACQ-14 + ACQ-15 (28) | `27 7 23 * *` | — |
| `osm_overpass` (existing job) | OKC + national tiles | `12 8 24 * *` (was `12 4 * * 1`) | monthly; outside the 03:00–06:30Z band |
| `legistar`, `usaspending`, `procportal_nyc_ny` (existing) | widened | unchanged: `0 5 20 * *`, `0 5 3 * *`, `0 12 30 * *` | the timeout rises to 3h for Legistar |
| Wave D `r11-tier2-01…03` | ACQ-19…26 | days 25–27, 07:37Z (set in ACQ-27) | avoids the dot_511 24–27 04:00/06:00Z triggers |

- **Net change:** +7 jobs and +7 triggers in Waves A–C (79 → 86 schedulers), and +3 in Wave D.
- **Crons:** every new cron restricts either day-of-month or day-of-week, never both, so the OR-semantics defects of G1 NEW-9
  cannot recur. ACQ-01 adds the lint `cron_or_semantics_ok` (G1).

**Images (ADR-111).**
- One image build per wave, pinned by digest. It is rolled to every existing job with `sig-ops roll-jobs --record` (before
  and after digests), and the new jobs are created with `scheduled-ops.sh --apply --paused` on the **same digest** (the one
  fleet digest per roll proposed in G1's SIG-SEC-008).
- `cadence.toml` ships inside the image (G1 NEW-10), so a cadence change without a roll never takes effect.
- `camreg-batch-05` is deliberately held on `feff986c` (P31.4, `G1:249-252`). Wave C's retirement of its ALPR targets is its
  roll. It happens after the 2026-10-10 replay has been read back (G2 gate for step 1), never before.

**Runtime.**
- New jobs run as `sig-ingest-rt` (G1 per-workload service accounts; G2 AR-8), never as the default compute account.
- Batch timeout is 6h for the documents and layers batches (a per-row `task_timeout`), not the fixed 36h.
- 1 vCPU / 2 GiB, except OSM: 2 vCPU / 4 GiB for ~60 MB tile responses (*estimate*).
- `--max-retries 0`: resume by `logical_run`.

### 7.2 First-run safety

- **Unobserved first fires.** G1 NEW-8 and G2 NEW-8 show the existing fleet's first-fire problem: 32 triggers fire for the
  first time between 10-01T06:00Z and 10-21T06:09Z, and peel-on fires on 10-29. R6 (paused-create, manual first run, verify,
  resume) means **no new source adds to that wave**.
- **No stacking on the wave or the replay.** No Round-11 acquisition first run before the 10-10 replay's read-back, and none
  inside AR-3 (10-06 00:00Z → 10-13 12:00Z; 11-06 → 11-13; 12-06 → 12-13), inside the daily 03:00–06:30Z band, or on a cut
  day (the 15th).
- **Order of work in each wave:**
  1. the pre-state capture (OM-14: job and trigger JSON, `sources.toml` sha, `cadence --check`);
  2. an on-demand backup (AR-2);
  3. the roll;
  4. create paused;
  5. manual runs, one family per day;
  6. verification;
  7. the +0 re-runs;
  8. resume;
  9. materialize.
- **Targets added under an existing source** (Chicago and Denver in `camreg-batch-02`, `14 3 7 * *`; DC in
  `sig-ingest-dot-511-dc`; the bills in `sig-ingest-openstates`) get their first run as a single-source manual execution in
  Wave B: `gcloud run jobs execute <existing job> --args=scheduled-ingest,--source,<id>,--sink,pg --wait`. Their next
  scheduled fire is then a +0 re-run, not a first fire. This matters most for the Chicago ATE aggregates, ≈ 73k claims on
  first run, which would otherwise land inside the day 6–13 batch window.
- **Concurrency:** at most one new manual job at a time. Never concurrent with `sig-materialize`, which peaks the single
  vCPU (`G1:566-567`), or with a G2 step 1–3 slot.

### 7.3 Calendar

Fixed dates come from G1, G2 and G3. Wave dates are the **earliest** feasible dates. They assume R0 ≤ 2026-10-14 and
G2 step 1 by about 10-16 plus its 48 h soak. They slip with R0 (*inference*).

| date (UTC) | event | acquisition action |
|---|---|---|
| 10-01 → 10-21 | 32 first fires of existing triggers (G2 NEW-8) | code tickets ACQ-01…06, 08…15, 17 proceed; nothing live |
| 10-06 00:00Z → 10-13 12:00Z | AR-3 freeze; 10-10 03:35Z OSM replay (batch-05) | none |
| ≥ max(R0 + 5 d, 10-14) | G2 step 1 (L44–52, ADR-124 allows, Round-10 API) + 48 h soak | none |
| 10-15 14:00Z | G3 monthly cut (release #1) | none |
| **10-19 (Mon) → 10-23 (Fri)**, 14:00–20:00Z | — | **Wave A (ACQ-07):** roll; manual Legistar, USAspending and CROL runs; `load-seed` 2026; +0 re-runs |
| **10-26 (Mon) → 11-05 (Thu)**, 14:00–20:00Z | 10-29 12:00Z peel-on first fire | **Wave B (ACQ-16):** one family a day in ticket order ACQ-08→15; `sig-materialize` after the last |
| 11-06 → 11-13 | AR-3 freeze (existing batches) | none. New monthly triggers first fire on 11-16…11-24, after resume |
| 11-15 14:00Z | G3 cut: **Class S** release (Waves A+B new sources; operator readout, 1–2 h) | provides source list and V14 expectations |
| **11-16 (Mon) → 11-20 (Fri)** | — | **Wave C (ACQ-18):** disk pre-grow + tier bump; national OSM first run; ER rematerialize; retire mirrors; revert tier (earliest possible 10-26 if ACQ-17, PKG-07 and Q-23 land early) |
| **11-23 → 12-04** (not 11-26) and **12-14 → 12-18** (not 12-15) | — | **Wave D (ACQ-27):** Tier-2 families whose lines read `a` |
| 12-15 14:00Z | G3 cut: Class S (OSM origin; first Wave-D sources) | — |
| 2027-01-15 | G3 cut | remaining Wave-D sources |

### 7.4 Cloud SQL capacity and cost

**Measured.**
- Size: 6.42 GB used on 09-30, 6.94 GB peak on 09-25, 15 GB SSD, autoresize limit 0 (unlimited).
- Load: memory daily max 1.0 on every day 09-16…09-24, and CPU peaks of 1.0 during materialize and export
  (`G1:64-66,566-567`; live read).
- Claims: the live watermark was 2,514,683 at 09-30 17:07Z (`G3:131`).
- **Derived unit:** ≈ 2.55 KB of disk per claim, including evidence, indexes and other tables (*inference*).

**Projection to 2026-12-31** (*inference*; ranges, not measurements).

| component | claims | disk |
|---|---|---|
| today | 2.51M | 6.4 GB |
| organic growth from existing schedules, incl. first fires | +0.2M … +2.3M | +0.5 … +5.8 GB |
| PKG-07 technology backfill (~200k subjects, F5) | +0.2M | +0.5 GB |
| Wave A (widening) | +0.02M | +0.05 GB |
| Wave B (Tier 1) | +0.25M | +0.64 GB |
| Wave C (OSM origin) | +1.11M | +2.8 GB |
| Wave D (Tier 2, if all lines are `a`) | +0.12M | +0.3 GB |
| **year-end total** | **4.4M … 6.5M** | **≈ 11 … 17 GB** |
| transient: the L44 `claim_evidence` rewrite (G2 NEW-3) | — | + about the table size, during the deploy |

Notes on the projection:
- The organic band's upper end extrapolates the only net measurement (+91,483 claims in about 3.65 days, `G3:131`) over a
  quarter. Its lower end assumes re-runs are mostly +0.
- **Measure before Wave C:** a weekly read-only `pg_database_size` plus per-source counts (G1 QA-9 baseline) narrows the band.
  ACQ-18's pre-state records it.

**Recommendations.** These are the draft answer to Q-23; the operator decides.
1. **Disk.** Set `storageAutoResizeLimit` to a cap that binds, e.g. **40 GB**. The G2 NEW-9 ceilings can never bind while
   the limit is 0.
   - Pre-grow the disk to 25 GB in ACQ-18's pre-state. The change is one-way.
   - Add a disk-utilization alert at 70% and 85% of the *cap*, extending G1 QA-3.
   - Cost: ≈ +$1.70/mo at a ~$0.17/GB-month list price (*inference*; not read from billing).
2. **Tier.**
   - Waves A, B and D stay on `db-custom-1-3840`.
   - Wave C only: bump temporarily to **`db-custom-2-7680`** for the national first run and camera-site rematerialization,
     about 48 h, ≈ $3 at G1's ≈ $0.07/h per extra vCPU plus memory (`G1:385`). Revert after a 24 h soak.
   - Each tier change restarts the instance (the 09-30 PITR restart gave one 503 in 16 s). It is scheduled inside the wave's
     window with its own verbatim go. The four unrecorded tier changes of September (F-38) are the precedent **not** to repeat.
3. **Permanent scale-up** (≈ +$49/mo; *inference* from the same unit price over 730 h) happens only on a named trigger:
   - memory max 1.0 on ≥ 3 of 7 days **and** API `/health` p95 above the SLO;
   - or `sig-materialize` exceeds 2 h;
   - or a monthly batch misses its window.

   The trigger is recorded as the revisit trigger of ADR-107/111 (`G1:385`).
4. **Cost summary.**
   - **Steady-state delta:** ≈ +$4–6/mo. That is 7 triggers at $0.10 (+$0.70), ≈ 8 extra job-hours at $0.19/h (≈ +$1.5), disk
     (+$1.7) and backup growth (small).
   - **One-off:** ≈ $5–10 (tier bump, first runs, fixture captures).
   - **Release cost** is G3's (≈ $2.5 per release) and is not changed by acquisition.
   - All of this is against G1's ≈ $90–100/mo list estimate. Q-10 (the ceiling) is still open.
5. **GCS.** Raw captures add ≈ 60 MB per OSM national snapshot per month and < 100 MB per month for everything else
   (*estimate*), into `sig-restricted`. That bucket has no lifecycle today (G1 NEW-4); nothing here needs one.

### 7.5 Rematerialization and republish

- **After each wave:**
  - `sig-materialize` (camera-site ER, `coverage_record`, `contradiction`), run manually after the last first run and outside
    ingest runs;
  - reconcile's sharing-edge build, where WA AGO or statute claims add `sharing_partner`;
  - the ACQ-01 coverage-delta tool (§7.7) against the pre-wave snapshot.
- **Release.** G3's monthly cut on the 15th publishes. Every wave's new sources make that release **Class S**: a
  candidate-specific readout the operator signs, costing 1–2 h (`G3:422,436-442`).
  - The OSM origin swap will exceed V14's +50% per-compartment bound in `osm_physical`, so it is Class S whatever happens.
- **Release preconditions**, which gate publication, not ingestion:
  - PKG-06a/06b: jurisdiction keys and point-in-polygon QA, so new geographies do not repeat I1 NEW-1/2;
  - PKG-07: a technology column in the exports;
  - PKG-08: per-source attribution. CC-BY-4.0 rows (DC, Suffolk) must render attribution (J4 NEW-3);
  - J4's raw/derived lanes: most new rows are `derived-only`; RB-05 and RB-06 rows are `raw-ok` after P8 screening.

### 7.6 Monitoring

- **G1's quick actions must be live before Wave A** (G2 step 0): QA-3 (e-mail channel, a log-based `SIG-ALERT` alert and a
  metric alert on `run.googleapis.com/job/completed_execution_count{result="failed"}`), QA-4 (uptime) and QA-9 (drill).
- The failed-execution alert covers new jobs automatically.
- **Added by ACQ-01/ACQ-18:**
  - Cloud SQL disk utilization against the Q-23 cap;
  - memory utilization > 0.9 sustained for 1 h during Wave C;
  - the `sig-probe` cadence targets refreshed with the new jobs, rolled with QA-5.
- **Per activation ticket:** the ticket confirms that each new job's manual execution produced a run row. An intentionally
  failed dry execution (`--mode shadow` with a missing fixture, which exits 2) shows that the alert fires once per wave.

### 7.7 Verification (per source and per wave)

| layer | check | command / evidence |
|---|---|---|
| engineered | registry valid; row gated or flipped exactly as the operator line says | `uv run sig-connectors validate`; `review-status --source <id>`; `gate --source <id>`; `export-check` |
| fixture-verified | shadow diff 0; replay reproducible | family test files (`test_dot_511.py`, `test_government_mandated_disclosure.py`, …) |
| schedule | no unscheduled live source; cron lint | `uv run sig-ops cadence --check` |
| live-executed | captures landed (bytes in the OCFL store, not digest-only: J4 NEW-5); run row `ok`; claims > 0 | `gcloud run jobs execute <job> --wait`; `gs://…-sig-restricted/ops/runs/<source>/…` |
| idempotence | a second execution inserts 0 claims (re-sightings where supported) | run row `claims_added == 0` (`tests/db/test_resightings.py` pattern) |
| typing | 0 ALPR/ATE subjects without a technology claim; 0 new `traffic_camera`-only typing | read-only SQL over the spine (ACQ-01 verify CLI) |
| ER | expected merges (§5, §4.3); lineage recorded for mirrors | `camera_site_run` / `camera_site_match` counts |
| coverage | delta per I1 blind spot, tier-A/B state, GL1 city, technology class and country | ACQ-01 `coverage-delta` (I1's method as a committed tool; `/v1/coverage` is unusable as volume evidence, I1:559-560) |
| public | source appears in the release with attribution and freshness | G3 V1–V14 on the Class S candidate |

### 7.8 Rollback

- **A job or image.** Re-point to the previous digest from the roll record (`G1:540`). For a new job: `gcloud scheduler jobs
  pause`, and delete the job only in a ticket-scoped live stage.
- **A source.** A new dated rights decision sets `ingestion_permitted=false`, so the next run exits 3. Its claims stay
  (append-only). The next release withdraws it through G3's withdrawal path, which must reach every alias within 15 min
  (`G3:502`).
- **Anomalous data.** A forward fix by new claims. For corruption only: a PITR **clone**, never an in-place restore
  (`G2:91-102`, `G1:388`).
- **Tier.** Patch back to `db-custom-1-3840` (restart).
- **OSM origin.** If ER merges fall below 95% or lineage fails, keep the republish targets scheduled; retirement is the last
  step of ACQ-18. Suppress the origin layer from the release until fixed.

---

## 8. Round-11 ticket outline

**Conventions (H2, B5).**
- One ticket, one branch: `r11/acq-NN-<slug>`, stacked on the previous ticket's branch, never merged by the agent.
- Five sha-bound checks on every PR.
- ≤ 3,000 changed lines excluding fixtures (OM-16).
- Live stages live only inside the ticket that owns them (B3 R6).
- Each live stage names its operator go verbatim (G2 AR-1), with pre-state, rollback command and run-ledger entry (OM-14).
- S2/T3 map ACQ-NN to manifest rows 201+ and phases P34+.

| # | ticket | size | contents | depends on | live stage | operator gates |
|---|---|---|---|---|---|---|
| ACQ-01 | Acquisition plumbing and verification harness | M | registry-row/target/cadence generator from the plan CSV (R2 ids, dataset-id dedupe, collision checks); new-round batch generator (NEW-4); `scheduled-ops.sh --paused` and per-row `task_timeout`; cron OR-semantics lint; `out_fields` allowlist and api_allowlist rpm for dot_511 targets (NEW-3); `coverage-delta` and wave-verify CLIs | PKG-02 (permitted-set invariant), H2 seed | none | — |
| ACQ-02 | Registry and tenant label corrections M1–M7 | S | §4.1 labels; NCDOT mirror note; FAA homepage | — | none | X4 |
| ACQ-03 | ATE technology concept | S | LinkML/SKOS ATE family and subtypes; zone geometry kind; `make gen`; ADR if the vocabulary governance requires one | PKG-11 | none | — |
| ACQ-04 | Legistar keyword-filtered, paged matter pass and agenda vocabulary | M | §4.1 | ACQ-01, ACQ-02 | none (live in ACQ-07) | — |
| ACQ-05 | USAspending/CROL vocabulary and filters | S | §4.2; the portal `where` support used by ACQ-11 | ACQ-01 | none | — |
| ACQ-06 | State ALPR statute seed 2026 and duty rows | S | §4.4 | ACQ-01 | none | C9 (default a) |
| ACQ-07 | **Wave A activation** | S | roll (one digest); manual runs of legistar/usaspending/procportal_nyc_ny; `load-seed`; +0; verify; coverage delta | ACQ-02, 04–06; G2 step 0 (QA-1…QA-10); G2 step 1 + soak | **yes** (10-19 → 10-23) | **ING-GO-A** (verbatim) |
| ACQ-08 | Official camera layers (DOT/CCTV) | M | §5.1 | ACQ-01, PKG-07/11 | none | HG-03 RB-02, RB-01 |
| ACQ-09 | Agency ALPR/Flock layers (incl. FDOT) | M | §5.2 | ACQ-01, PKG-07/11 | none | HG-03 RB-01 |
| ACQ-10 | ATE layers and aggregate transports | M | §5.3 | ACQ-01, ACQ-03, PKG-07 | none | HG-03 RB-01, RB-06 |
| ACQ-11 | Procurement and programme registers | S | §5.4 | ACQ-05, ACQ-10 | none | HG-03 RB-04/06/01 |
| ACQ-12 | Statutory disclosures I (ALPR) + connector generalization | M | §5.5 | ACQ-01, PKG-07 slugs | none | HG-03 RB-03 |
| ACQ-13 | Statutory disclosures II (UAV/FRT/CSS/interception/ATE/DHS) | M | §5.6 | ACQ-12 | none | HG-03 RB-03/04/05/06 |
| ACQ-14 | CCOPS, police policies, district self-disclosures | M | §5.7 | ACQ-12 | none | HG-03 RB-03, RB-07 |
| ACQ-15 | Grant, council and procurement documents, and bills | S | §5.8 | ACQ-01 | none | HG-03 RB-04, RB-06 |
| ACQ-16 | **Wave B activation** | M | roll; create 7 batch jobs paused; manual run per family (ACQ-08→15); +0; resume; materialize; coverage delta | ACQ-07, ACQ-08…15; `sig-ingest-rt` SA | **yes** (10-26 → 11-05) | **ING-GO-B**; HG-11 for the 11-15 Class S release |
| ACQ-17 | OSM as a camera-site origin (code) | M | §4.3 items 1–6 | PKG-07/11, PKG-12 ED-49, ACQ-03 | none | — |
| ACQ-18 | **Wave C: OSM national origin** | M | §4.3 ACQ-18 steps; disk pre-grow; tier bump and revert; retire mirror targets | ACQ-16, ACQ-17, G2 step 1 (L44), Q-23 | **yes** (default 11-16 → 11-20) | **ING-GO-C**; **Q-23**; tier-bump go; HG-11 (12-15 Class S) |
| ACQ-19 | Tier-2 reuse wave | M | §6.2 | ACQ-08/12 families | none | lines per row (RB-xx, RG, C6) |
| ACQ-20 | Aggregate lanes (S3/S4/S7) | M | §6.2 | ACQ-10 | none | S3/S4/S7 `a` + batch lines |
| ACQ-21 | Federal datasets family | M | §6.2 | ACQ-01 | none | RB-05 `a` |
| ACQ-22 | Agenda platforms v2 | M | §6.2 | ACQ-04 | none | RB-04 `a` |
| ACQ-23a/b | International portals and files; OGC WFS | M + M | §6.2 | ACQ-01 | none | N-lines / RB-06 `a` |
| ACQ-24 | Puerto Rico (SUTRA, OCPR) | S | §6.2 | ACQ-01 | none | RB-08 `a`, S7 `a` |
| ACQ-25 | Document-list pages | M | §6.2 | ACQ-01 | none | RB-04/07 `a` |
| ACQ-26 | S1 programme-level lane | M | §6.2 | ACQ-09 | none | S1 `a` |
| ACQ-27 | **Wave D activation** | M | as ACQ-16, for the Tier-2 families that landed | ACQ-19…26 | **yes** (11-23 → 12-04; 12-14 → 12-18) | **ING-GO-D**; HG-11 |
| ACQ-28 | Coverage outcome and acquisition closeout | S | the coverage-delta report per blind spot (§9); ADR-130 queue outcomes; DEFERRALS rows for the 130 later-phase Tier-2 rows and the duty leads; the Class S readout inputs for G3 | ACQ-18 (and ACQ-27 if run) | none (read-only reads) | — |

- **Tally:** 28 tickets and 29 PR-sized units, because ACQ-23 has two parts. 9 are S (02, 03, 05, 06, 07, 11, 15, 24, 28)
  and 20 are M (01, 04, 08, 09, 10, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23a, 23b, 25, 26, 27). None is L.
- **Core (19):** ACQ-01…18 and 28. **Conditional (9):** ACQ-19…27.

**Operator gates, collected:**
- **HG-03** batch lines RB-01…RB-07 (Tier 1 needs RB-01…07; RB-08/09 are Tier 2), the S-lines (S1–S4, S7 for Wave D),
  the N/IT/IU/TR lines, C6 and C9, and the confirmations X1–X4 (I7 packets §1).
  - A code ticket whose line is unanswered lands its rows with `ingestion_permitted=false`, and the activation skips them.
    It never guesses.
- **ING-GO-A…D:** one verbatim production-ingestion go per wave. This is the operator's explicit ask made operational (G2 AR-1).
- **Q-23:** disk cap and tier (§7.4). It is needed before ACQ-18.
- **The tier-bump go** (ACQ-18).
- **HG-11:** each Class S release (G3).
- **Q-30:** EDGAR, needed only for a later round.
- **Q-10:** the monthly ceiling. It is informative: nothing in the design exceeds G1's baseline by more than ≈ $6/mo
  without a named trigger.

**Cross-stream dependencies** (owned elsewhere; I8 only orders against them):
- G2 step 0 (QA-1…QA-10, restore drill) and step 1 (L44);
- G1's per-workload service accounts;
- F5 PKG-02, PKG-06a/06b, PKG-07, PKG-08, PKG-11 and PKG-12 ED-49;
- K4 (the sub-state jurisdiction key);
- G3's release pipeline and Class S readouts;
- H2's CI policy (TC-PIN before 2026-10-19).

---

## 9. Coverage outcome projection

"Now" is I1 (§7, I1:488-510). The waves are cumulative. Wave D is conditional on its lines. Projections are *inference*
from the rows' `geographies`, `gap_ref` and `technology_classes` columns, as I7 §7 did, restricted to rows assigned to a
Round-11 ticket.

| I1 blind spot | after Waves A+B | + Wave C | + Wave D (conditional) | stays dark after Round 11 (why) |
|---|---|---|---|---|
| **#1 Flock at origin and scale** | agency-origin layers for 14 agencies in 11 states; FDOT D3 inventory (407) + removal ledger (523); statutory operator lists (WA AGO 76 agencies; MN BCA); NE (89) / VT / IL reports; Cook, Haskell, Des Moines; Legistar Flock matters in ≥ 8 cities | **national ALPR layer from its origin** (154,814 objects vs 132,689 in the stale republish), mirrors retired | + 5 agency Flock layers, agency-operated rows only (S1) | Flock's own customer, sharing and audit data (portals refused; terms prohibit, T15; audit rows are Part VIII); a census of ~6,600 networks |
| **#2 Axon/Fusus, PCAM, RTCC** | DC camera-rebate programme counts; Leon Overwatch (Vigilant + RTCC); Forsyth RTCC RFP; RTCC/Fusus council matters (Columbus, Louisville, Detroit); CA BSCC RTCC grants | — | ~10 private-camera programmes and Project Green Light at programme level (S1) | Axon Fusus Connect and Community Connect (automated access prohibited, C4); Polaris/CrimeWatch registries (Part VIII / terms) |
| **#3 Jurisdiction attribution** | every new target carries an `iso.3166_2` key and a recorded GEOID | the 154k OSM ALPR sites become attributable **when PKG-06b's point-in-polygon lands** | — | sub-state attribution until PKG-06a and K4 land (not an acquisition fix) |
| **#4 Statutory and ordinance reporting** | 34 Tier-1 reporting rows (WA, MN, NE, VT, IL, VA, MD, ME, HI, PA, FL, CO, DE, MO, OH, TX, AK, US-federal); 5 new CCOPS jurisdictions; statute layer 2022/16 states → 2026/≈ 30 states, origin-cited | — | Boston/Berkeley flips; NYC DOI, Comptroller, BART, San Jose, Santa Clara | reports behind refused hosts (I9a NEW-5); duties that start later (NM 2027-04-01) |
| **#5 DOT/official registries (tier-A)** | DE, VT, WV, MI (+ NC, CT speed) | — | + NM (verify authority), ID ITD, WV PA layer | AR (IDrive terms), MS (terms), NH (keyed newengland511, HG-09), RI, ME, WY (no reachable channel) |
| **#6 Procurement and co-op** | Cook County awards; WA DES sales by customer; USAspending vendor and ALN slices; CROL vendor terms; council contracts; 6 state grant programmes | — | checkbooks/payments as vendor sums (TX DIR, DE, WA, Chicago, Mesa, NJ); co-op documents; IL/OH/MA award lists | Sourcewell, OMNIA (terms, C3); BidNet/Bonfire (E4 R6a); paid databases (Q-21) |
| **#7 Zero-channel classes** | SMM: DHS PIAs, NY S7037, USAspending SMM vendors. Forensics: Cellebrite/GrayKey purchases (USAspending, Jasper, Davie, council). School: 4 district pages, OUSD matters, AZ HB 2574. ATE: 15 rows once ACQ-03 lands | OSM speed cameras (ATE) | NCES SSOCS; AI use-case inventories | censuses for SMM and forensics (only purchase records exist) |
| **#8 Drones/GSD/FRT/CSS** | ME/MN/IL UAV reports and 2 UAS orders; CO/WA/Detroit FRT reports; MD CSS report and CA CSS policies/statute; Oakland ShotSpotter lifecycle | — | ShotSpotter aggregates (Detroit, Chicago, Oakland); drone programme counts (S1); wiretap tables; ICE 287(g) | FAA waiver tables (host unreachable, I9b NEW-1); FR audit rows (Part VIII blocked) |
| **#9 Thin large cities (GL1, of 36)** | 13: Cleveland, St. Paul, Madison, Nashville, Albuquerque, Charlotte, Newark, Winston-Salem, Detroit, Lincoln, Omaha, Anchorage, Houston | — | ≈ 20: + Jersey City, Durham, Hialeah, Frisco, Tampa, Las Vegas (S2); Anaheim, Honolulu (C6) | North Las Vegas (nothing found); Cape Coral, Indianapolis, Wichita, Norfolk, Greensboro, Chesapeake, Boise, Henderson, Irvine, Plano (Tier 3 only); Tulsa (locations withheld); Memphis, Virginia Beach (S7 later); St. Petersburg (discovery only) |
| **#10 Mobile ALPR and sharing currency** | WA AGO registrations and policies; VT/NE reports; statute sharing restrictions (VA §2.2-5517 F …); Brazoria DPS/HIDTA MOUs | — | — | per-agency sharing lists (records releases; DocumentCloud/MuckRock declined, C2) |
| **#11 International** | — | AU and every other country with `surveillance:type=ALPR` objects (per-country counts logged at the first run) | camera layers in up to 10 countries (GB, AU, IE, IT, ES, PT, SI, FR, CA, UA) | EU statutory registers (gated); UK ANPR (terms prohibit, T4/T5); NZ OIA (terms); non-commercial publishers until C6 |
| **#12 Records and courts** | — | — | — | dark all Round (C8 CourtListener basis; DocumentCloud/MuckRock declined; CAP names S7) |
| **#13 Data brokers** | DHS SORNs on commercial plate data; CBP telemetry PIA; USAspending LexisNexis/TR/TransUnion/Fog recipients | — | — | vendor filings (EDGAR, Q-30); Fog records (DocumentCloud) |
| **#14 Territories and tribes** | GU (press release; CC0); PR/VI at statute level | — | PR (SUTRA 7 measures; OCPR contracts); VI legislature (RB-08 `a`) | AS, MP (no channel); every tribal nation (governance rule, I7 NEW-6) |

**Headline counts.**

| | after Waves A+B | + Wave C | + Wave D |
|---|---|---|---|
| tier-A states (of 10) | 7: AR, DE, ME, MI, NH, VT, WV | 7 | 8 (+ RI via S1) |
| tier-B (of 5) | 3: DC, HI, NM | 3 | 4 (+ ND via Fargo) |
| GL1 thin cities (of 36) | 13 | 13 | ≈ 20 |
| technology classes (I2 T01–T29) | 28–29 (ATE needs ACQ-03; T16 robotics is one lead) | 29 | 29 |
| countries beyond the US | 0 | ≥ 1 (AU; others counted at the first run) | ≤ 10 via camera layers |
| I1 blind spots moved (of 14) | 11 | 12 (+ #11) | 12 (#3 via PKG-06; #12 dark) |

**Dark after Round 11, by cause:**
- **No reachable channel:** MS, WY, MT, AS, MP, North Las Vegas.
- **Terms prohibit:** Flock, Axon, Sourcewell/OMNIA, TxDOT origin, UK ANPR.
- **Operator decision pending:** C6, Q-30, RB-08, tribal governance.
- **Part VIII by design:** plate, audit and person-level data.
- **Engineering not in Round 11:** S4 coarsening, S5 naming, S6 excerpts, records corpora.

---

## 10. Findings raised (`findings/incoming/I8.csv`, all `proposed`)

| id | sev | title (short) |
|---|---|---|
| NEW-1 | S1 | Widening `osm_overpass` alone cannot make OSM the ALPR origin: geometry rides asset rows the sink skips, and ER pools only `traffic_camera:%` |
| NEW-2 | S2 | The Legistar/CROL/USAspending "widenings" need adapter changes: fixed recency windows (`$top=100`, `$limit=500`, `prime_max_pages=1`) with no keyword filter |
| NEW-3 | S2 | The reviewed ArcGIS API budget (10/min) is not applied to camera-registry targets, which fetch at the 1 s default (60/min) |
| NEW-4 | S2 | There is no path to add a second cadence-batch round, and new triggers are created enabled, so new sources' first executions would be unobserved first fires |
| NEW-5 | S2 | 63 of I7's Tier-1/2 proposed source ids are truncated mid-word at 44 characters, and others are garbled or mis-prefixed; ids are permanent |
| NEW-6 | S2 | Capacity: Round-11 ingestion (≈ 1.5M claims, ≈ 3.8 GB) plus unmeasured organic growth projects 11–17 GB against a 15 GB disk with unlimited autoresize; Q-23 is needed before Wave C |
| NEW-7 | S3 | The Tier-1 ATE "violations" datasets are per camera-day or per period; routed as `socrata_rows` they would add 10⁵–10⁶ claims; they need `$group` aggregation and a count predicate |
| NEW-8 | S3 | Statutory reports fit `government_mandated_disclosure`, not `dossier_documents`; the disclosure connector keeps technology as literal text and is scoped to municipal CCOPS |

Seen, already raised elsewhere, and not re-raised:
- G1 NEW-8 and G2 NEW-8 (first-fire wave), G1 NEW-10 (baked cadence), G2 NEW-3 (L44 rewrite), G2 NEW-9 (autoresize);
- I1 NEW-5/9 (republish and `traffic_camera`), I1 NEW-8 (ATE ontology);
- J4 NEW-4 (raw OSM meta in captures), J4 NEW-5 (digest-only captures);
- I7 NEW-1…NEW-8.

---

## 11. Open questions for the operator and for synthesis (S2/S5)

1. **Q-23:** accept an autoresize cap of 40 GB, a pre-grow to 25 GB before Wave C, and temporary-only tier bumps (§7.4)?
2. **OSM cadence:** monthly national + OKC (recommended), or keep weekly? Weekly has +0 spine cost but ~4× the Overpass load.
3. **ING-GO per wave:** does the operator want one verbatim go per wave (recommended; G2 AR-1), or one per family day?
4. **Targets under existing flipped sources** (Chicago ATE, DC ASC, Denver HALO, openstates bills): confirm these as X3-like
   configuration in the HG-03 readout, rather than new lines.
5. **Round-11 scope:** core ACQ-01…18 + 28 only, or also the conditional Tier-2 wave (ACQ-19…27)? The answer depends on the
   operator's answers to RB-08, the S-lines, the N-lines and C6. Wave D is sized so it can be dropped whole.

---

## 12. Reproduction

1. Run the §6.4 rules over `data/candidates_consolidated.csv`, plus the S-line and individual-line membership tables of
   `design/I7-rights-packets.md` §1.2–§1.3. The output is `data/acquisition_plan.csv`: 694 rows, unique `plan_id`s, and
   actions widen 53 (the 46 W units plus the 7 Tier-1 targets under flipped sources) / new-row 180 / new-connector 71 /
   defer 390 (including the I9b-C040 channel).
2. The per-unit W and Tier-1 claim estimates are the §4–§5 table values.
3. Check the counts:
   - `python3 -c "import csv,collections;r=list(csv.DictReader(open('data/acquisition_plan.csv')));print(len(r),collections.Counter(x['tier'] for x in r))"`
     should print 694 and {W 46, 1 108, 2 281, 3 259}.
