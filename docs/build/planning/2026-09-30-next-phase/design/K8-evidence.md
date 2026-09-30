# K8 — `/evidence` diagnosis and redesign · operator ask U-003.8

Row **K8** of `META_PLAN.md` §6 Stream K (owner R/D, depends J1, C3). Written 2026-09-30 by Claude Code (Opus 5.5) in the
planning worktree `/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `e69f3fde`). Every
code path cited is byte-identical to chain tip `b051732c`. Work window (`date -u`): **2026-09-30T21:36:08Z → 22:01:07Z**
(the same session as K7 and K11). `PD` = `docs/build/planning/2026-09-30-next-phase`. Findings are in
`findings/incoming/K7K8K11.csv`.

> **Design only (P3/P10).** Production was only read; K7's header gives the request budget and the UA. Nothing here is
> `engineered` or `live-executed` (P5). Public sentences are **agent-drafted**. **This note extends J3 §5 (record
> provenance) and J4 (lanes); it does not redo them.** Data-layer work stays with J3's TX tickets (exactly one owner, P9).
> This note owns the `/evidence/` product surface and the claim-viewer model. Scratch evidence:
> `docs/build/logs/next-phase/K7K8K11/`.

**Operator ask (U-003.8, verbatim):** *"the "/evidence" page doesn't actually seem to show anything yet, but this may just be
that everything is stuck in the research queue"*.

**Inputs read.**
- `META_PLAN.md` §3; the K block.
- J1 §0/§A.3/§A.4/§B.1–B.4 (NEW-4, NEW-9, NEW-10).
- J3 §1 (G-6, G-7), §5, §11 (D05, D11–D13) and §12 (TX-01, TX-03, TX-05, TX-08, TX-09, TX-12).
- J4 §0 (lanes).
- J2 PC-3 (the record provenance panel: OpenSanctions statements, PROV-O).
- C3 DATA_TRUTH §4.10.
- C2 JOURNEYS P4-T1.
- ROUTES R12/R13.
- FINDINGS F-098, F-229, F-357, F-368, F-375, F-376.
- Code:
  - `web/src/pages/evidence/{index,[id]}.astro`;
  - `web/src/lib/{evidence-viewer,recommender,data,empty}.ts`, `web/src/lib/watch-evidence-fixture.ts`;
  - `exports/src/exports/spine_export.py`, `exports/src/exports/analytics.py`;
  - `db/src/db/{claim_sink,dispositions}.py`, `db/deploy/{evidence,evidence_store,claim_evidence,graph_annotations}.sql`;
  - `api/src/api/store_pg.py`;
  - `tasks/src/tasks/{detect,research_pg}.py`;
  - spec §39.6 (SIG-UI-028/029/030).

---

## 0. Summary

**Is everything stuck in the research queue? No.** No research task gates what the evidence page shows:
- `research_task` rows have no field that affects claim, artifact or capture eligibility (`graph_annotations.sql:37-50`).
- None of the queue's 243,761 tasks is about publishing evidence (K11 §1).
- `answers_open_task` is `false` on all 255 published artifacts.
- The publication gates (tier, rights, ADR-124 dispositions) pass 2,423,194 claims.

The operator's reasonable guess was probably prompted by the empty state's only link, "See the research queue"
(**inference**).

**Why the page shows nothing (four stacked causes, all downstream of eligibility).**
1. **The exporter never builds a claim view.** `_evidence()` returns `"claim_views": []` as a literal
   (`spine_export.py:1185`), and has done since P27.4 (`93f04c51`) (F-357 names the symptom).
2. **The page ignores what *is* published.** `/evidence/` renders only `claim_views` (`evidence/index.astro:18,29-37`).
   The same `web/evidence.json` lists 255 artifacts from 219 sources, and none of them appears (NEW-7).
3. **There is nothing real to point at yet.** Every claim-to-capture binding in the live spine goes to a **synthetic**
   per-source-per-run capture: 0 bytes, `capture_classification 'synthetic'` (`claim_sink.py:1225-1227`; J3 G-6). The 350
   real OCFL captures are restricted and unbound until sqitch L44–52 and the actual bindings land (G2 steps 1–2).
4. **The viewer's model cannot show the honest states.** `assertClaimView` requires `document_text` for every non-sealed
   capture. So a synthetic, derived-only or link-only claim view would fail the build, or would force SIG to publish
   bytes it may not redistribute: J4 puts 172 of 237 in-scope sources in `derived-only`. The capture diff is a fixture
   pair wired to the fixture claim id `active-device-count` in every build mode (NEW-8).

A latent defect sits beside these. The public artifact query omits the shared artifact-eligibility gate that the binding
query applies, so a withheld artifact would still be listed (NEW-9).

**Redesign headline.** `/evidence/` becomes the **evidence browser**, organised around three grains that share one
provenance vocabulary with J3:
- the artifact: a document or dataset SIG read;
- the capture: a dated, hashed copy or record of that read;
- the claim: one statement extracted from a capture.

It shows today's truth ("every published claim currently rests on a run-level record, not a stored document") instead
of a blank page. Each artifact gets a page with capture history, hashes, the claims it supports, contradictions and a
lane-correct "view original". The claim viewer becomes **lane-aware**: a highlighted span only where the bytes may be
shown; otherwise the locator, digest and "view at source".

**Tickets (§9):** EV-01 (S, safety wave), EV-02 (M), EV-03 (M), plus the J3 tickets they depend on.
**Operator decisions (§10):** D-K8-1…D-K8-4.

---

## 1. Live QA (2026-09-30T21:38–21:44Z)

| # | check | result | evidence |
|---|---|---|---|
| Q1 | `GET /evidence/` | 200, 5,660 B, `last-modified` 2026-09-27T01:33:42Z; body sha256 `b6fc5cdf…`, identical to J1's 16:5xZ read. The page has not changed | live-read; `curl/evidence.*` |
| Q2 | Content | the intro paragraph describes a viewer that does not exist ("shows the document with the supporting span highlighted…"). Then "No claims with a full evidence view yet … Their absence is a research gap, not evidence that no claims exist." with **one** link, "See the research queue". Then the national "How we know this" block (Artifacts 255, independent sources 218) | live-read; `text/scen_pages_evidence_desktop.txt`; screenshot `shots/20260930T214328Z_scen_pages_evidence_full_desktop.png` sha256 `e437f33c…` |
| Q3 | Links in the main area | `/research-queue/`, `/methodology/`, `/data-freshness/`, `/coverage-metrics/`, `/dispute/` and the ignored-as-of permalink (J1 NEW-5). **No** link to any artifact, source or claim | live-read; `json/scen_pages_evidence_links.json` |
| Q4 | `/evidence/<id>/` pages | none deployed: 0 claim views → 0 static paths (ROUTES R13) | live-read (C1) + code |
| Q5 | `web/evidence.json` (release `sig-2026-09-27-ce480ab1`, sha256 `3df209d5…`) | 255 artifacts, `claim_views: []`. Types: camera_registry 178, connector_run 33, terms_page 27, portal_document 4, agenda_document 3, news_article 2, bill_index 2, and 1 each of official_statement, contract, community_map, agency_policy, executed_contract, portal_snapshot. 219 distinct sources. **0/255** http(s) permalinks (228 `sig:connector:…`, 27 `sig:terms:…`); **255/255** titles equal the artifact UUID; `subject_id` empty; `currency` empty; `directness` = primary 27 / secondary 228 | live-read + recorded-execution (python over the file) |
| Q6 | API | `/v1/claim/{id}` has no `artifact_id`, so a reader cannot get from a claim to `/v1/evidence`. `/v1/evidence` serves the synthetic capture with `bytes_available: true` (J1 §A.4; F-357) | live-read (J1, cited) |
| Q7 | Upstream links that already exist as claim data | agenda items and notices carry a `document` claim: `https://webapi.legistar.com/v1/seattle/matters/17425` (Seattle CB 121279) and the sam.gov opportunity URL (`curl/api_entity_agenda.body`, `api_entity_notice.body`). They reach no evidence page | live-read |

---

## 2. Full trace: capture → claim → eligibility → export → page

```
connector run ──► claim_sink: one SYNTHETIC capture per (source, run)       claim_sink.py:1199-1236 (J3 G-6)
               │     storage_tier 'public', 0 bytes, digest = sha256(connector|source|run), classification 'synthetic'
               └─► OCFL store: 350 real captures (restricted bucket), bound to no claim until L44 (G2 step 1)
claim_evidence: every published claim → its synthetic capture ("2,423,200 of 2,423,200 … resolvable", C3 §4.10)
eligibility: tier-0 + rights + ADR-124 {PUB_CLAIM_GATE} → 2,423,194 publishable claims       (passes; not the blocker)
research_task: 243,761 rows; no column gates evidence; not on this path                   (not the blocker)
export (spine_export.fetch_export_raw):
   evidence_artifacts  WHERE sensitivity_tier = 0 AND capture_status = 'captured'   :161-168  (no artifact gate → NEW-9)
   evidence_bindings   … AND {PUB_ARTIFACT_GATE}                                    :222-231  (used only by P32.13 records)
   _evidence(): artifacts[] shaped; "claim_views": []   ← literal                  :1163-1185  (cause 1)
web: getEvidence() → {artifacts, claimViews}                                        data.ts:318-338
   /evidence/ renders claimViews only → EmptyState("evidenceIndex")                 index.astro:18,29-37 (cause 2)
   /evidence/[id]/ getStaticPaths(claimViews) → 0 pages; assertClaimView needs document_text  [id].astro:30-35 (cause 4)
   capture diff = fixture DIFF_CAPTURES in every mode; shown iff claim_id == "active-device-count"  data.ts:800-802; [id].astro:43
```

| cause | class | would fixing it alone make `/evidence/` useful? |
|---|---|---|
| 1 `claim_views` hard-coded `[]` | code | **No.** A claim view built today could only say "run record, no document" (cause 3), and the current model rejects that (cause 4) |
| 2 index ignores the 255 artifacts | code | **Partly.** The reader would see what SIG read, from where, when and under which licence, honestly labelled as run records |
| 3 synthetic bindings only | data / activation | needs G2 steps 1–2 (L44–52 + actual bindings), then TX-08 |
| 4 viewer model requires bytes | design | needs the lane-aware model (§5.4) |
| NEW-9 artifact gate missing | code (latent exposure) | a prerequisite for showing more artifact metadata |

**Answer.** It is not the research queue. It is a missing producer, a page that ignores its own data, an activation step
that has not happened, and a viewer model that assumes SIG may show every document. All four sit after the publication
gates.

---

## 3. What the evidence experience must do (from the ask, J2, J3 and the personas)

- **Attorney (P4-T1):** "Pick any claim and show me the document it rests on, with the page anchor and acquisition
  history."
- **Journalist:** "What did the portal say in June vs August? Give me the original link, the hash and the capture time so
  I can verify it independently."
- **Skeptic / researcher:** "How much of this is backed by documents, and how much by bulk dataset rows? Show me counts,
  not adjectives."
- **Advocate:** "Which documents should I bring to the council meeting?" (via K7's scoped recommender).

**Principles** (on top of J3 §2):
- **E-P1: One vocabulary.** K8 pages, J3 record panels and K7 watch items use the same binding states (J3 §5.1), the same
  lane "view original" rule (J3 §5.3) and one `<ProvenancePanel>` component.
- **E-P2: Say what SIG holds.** Every artifact and capture carries its classification: document capture, dataset
  snapshot, API response, or **run record (no stored document)**. Bytes are never implied (C4 NEW-2 lesson; J3 D05).
- **E-P3: Browse from both ends.** Figure → claim → capture → artifact → upstream, **and** source → artifact → captures →
  claims. `/evidence/` is the second entry.
- **E-P4: No per-claim page explosion.** 2.42M claims get anchors in record pages (J3 G-10). Standalone claim views
  exist only for document-genre claims with actual captures, capped, and the cap is disclosed.
- **E-P5: Stable, readable names.** Artifacts get handles (K11 §3 grammar). Claims get a plain-language sentence title
  plus a short id.

---

## 4. Information architecture

| route | purpose | grain | notes |
|---|---|---|---|
| `/evidence/` | hub: state of the evidence + browse artifacts | all | replaces today's page |
| `/evidence/page/<n>/`, `/evidence/source/<id>/`, `/evidence/type/<genre>/`, `/evidence/lane/<lane>/`, `/evidence/place/<key>/`, `/evidence/state/<binding_state>/` | one-dimension facet lists, paginated at 50 rows | artifact | J3 G-11 facet rule |
| `/evidence/artifact/<handle>/` (+ `.json`) | artifact page | artifact + captures | the **latest-view alias** of J3's release anchor `/r/<pub>/c/<comp>/evidence/<aid>/`, same template; "Cite" points at the immutable `/r/` URL (D-K8-3) |
| `/evidence/artifact/<handle>/diff/<capA>..<capB>/` | field-by-field capture diff (SIG-UI-029) | captures | only when both captures are real and extracted fields differ |
| `/evidence/claim/<claim_id>/` (+ `.json`) | claim viewer (SIG-UI-028 v2) | claim | generated only for document-genre claims with `actual_capture`, capped (J3 §5.2) |
| record claim anchors `…/entity/…#claim-<id>` | per-claim panel on record pages | claim | J3 TX-08 (not K8) |
| `/sources/<id>/captures/` | per-source capture history | captures | J3 TX-05 (not K8); artifact pages link to it |

### 4.1 `/evidence/` hub (zero-JS)

1. **What evidence means at SIG** (≤80 words; agent-drafted): artifact / capture / claim. It links "How to check a
   claim", a four-step walkthrough with screenshots of one real example.
2. **State of the evidence.** Every number is rendered through J3's `<Figure>` with a definition and a data pointer (J3
   D13).
   - **Claims by binding state.** Today: `legacy_synthetic` 2,423,194, and 0 for each of `actual_capture`, `replayed` and
     `document_only`.
   - **Artifacts by classification and by lane:** raw-ok, derived-only, link-only, restricted, unknown.
   - **Captures with stored bytes vs digest-only.** J4 NEW-5: 349 of 6,144 digests have bytes.

   Each count links to its facet list.
3. **Current-state banner** (agent-drafted; replaces the "research gap" copy): *"Every published claim currently points
   to a run-level record: SIG logged which source run produced it, but did not yet link each claim to a stored copy of
   the page or file it came from. SIG holds <N> document captures internally; they will be linked to claims after
   <activation step>. Until then, each source's page lists what was fetched, when, and its hash."* The numbers come from
   the release. The activation wording comes from G2/G3 once dated.
4. **Browse artifacts.** A table of 50 rows per page, sortable through pre-rendered sort routes (the existing
   `data-freshness/[...sort]` pattern). Columns:
   - artifact (human title → artifact page);
   - source name (→ `/sources/<id>/`);
   - type/genre;
   - place;
   - captures (count, latest date);
   - classification;
   - lane badge;
   - claims supported (count);
   - "view at source" (lane rule).
5. **Recently captured** (last 30 days, from the release; the status lane may add "since release").
6. **Downloads:** the artifact index JSON/CSV and the per-compartment `statements` files (J3 TX-08a, TX-10b).

### 4.2 Artifact page `/evidence/artifact/<handle>/`

| block | fields | source |
|---|---|---|
| header | human title; source (link); publisher; artifact type/genre; place; classification; lane badge with reason | `evidence_artifact`, registry, J4 lanes |
| upstream | host plus full URL after the S-6 scrub; "View at source"; terms URL and terms capture date/digest | `evidence_artifact.url` (not exported today, J1 B.1), TX-01 |
| captures | one row per capture: retrieved_at (full UTC), sha256 (full, monospace, copyable), BLAKE3 where present, bytes, media type, HTTP status, capture method, classification (**synthetic rows are labelled "run record — no stored copy"**), changed since the previous capture (digest compare), "view original" per J3 §5.3 | `evidence_capture` ∪ `ingest_run_capture` via TX-03 `captures.jsonl` |
| claims supported | count by predicate (plain-language predicate labels), then a paginated list: claim sentence → record anchor or claim viewer | TX-08a `statements` |
| contradictions | open contradictions touching claims from this artifact, with the `≠` marker and links | contradiction materialization |
| status | disappearance / link rot (once F-229 writes `disappeared_observed_at`); withdrawal tombstone (410) | `evidence_artifact`, ADR-124 |
| rights | SPDX, attribution text **from the registry** (J3 principle), redistribution lane | registry, J4 |
| used by | watch items citing it (K7), open tasks it could close (K11), dossiers whose figures rest on it | K7/K11 exports |
| equivalent requests | JSON twin, `/v1/evidence/<a>/<c>` for each capture | TX-15 parity |
| cite | release-pinned citation | TX-13a |

**Human title rule.** The title is built from the registry source name, the artifact type label and the most specific
locator. For example: "Austin, TX procurement portal — solicitation NA230000215", or "OpenStates — bill index (Texas,
89th session)". It is never a UUID (NEW-7; J1 NEW-4). When no locator exists the title is "<source name> — <type> (run
<date>)".

### 4.3 Claim viewer `/evidence/claim/<claim_id>/` (SIG-UI-028 v2)

The page has four parts.

**1. Claim sentence and value.** For example "Seattle City Council agenda item CB 121279 — agenda content term:
*contract notice*". It shows `raw_value` verbatim, the predicate definition link, the subject link (K2 entity page) and the
resolution envelope the claim contributes to (supporting or considered).

**2. The document pane, by binding state × lane × Part VIII (extends J3 §5.3).**

| state | lane | pane |
|---|---|---|
| `actual_capture` | raw-ok, clear, text-extractable | stored text with `<mark>` at the locator span (today's highlighter), "Download original (sha256, bytes, retrieved)" |
| `actual_capture` | raw-ok, P8-5/6/8 | the **redacted capture's** text with span; the method and version of the redaction |
| `actual_capture` | derived-only | the locator described ("page 3, ¶2", "row 1,204, column `operator`", "JSON pointer `/features/12/properties/brand`"); an excerpt only if D-K8-1 allows; "View at source"; sha256, bytes and retrieved time |
| `actual_capture` | link-only | locator + "View at source" + hash/time |
| any | restricted / sealed | metadata-only with the reason class (SIG-UI-030), no URL where S-6 forbids |
| `document_only` | any | "Extracted from a document; no page capture" plus the document reference |
| `legacy_synthetic` | any | J3's run-level text: "Recorded by run <id> on <date>. SIG did not keep a per-record copy…", with links to the source's run and capture pages |

**3. Provenance.** Extraction method and version, bound_at, directness D-class with its meaning, epistemic tier, review
status ("Not yet independently reviewed"), competing claims (`≠`), history (revisions and retractions with belief dates),
and per-claim rights.

**4. Cite and equivalent requests.**

The **model change** is that `ClaimView.capture.document_text` becomes optional. A new `pane` discriminated union
(`text_span | locator_only | metadata_only | run_record`) replaces the rule "non-sealed ⇒ text". `assertClaimView` then
checks the pane against the lane, instead of demanding bytes.

### 4.4 Capture diff (SIG-UI-029)

The diff is built from the claims bound to two **real** captures of the same artifact. It compares their extracted fields
(predicate → value) and lists changed, added and removed fields, with both capture hashes and times. For
portal-snapshot genres it is the "what changed between June and August" view. In export mode the diff must never draw on
fixtures: a build check fails on `DIFF_CAPTURES` or the literal `active-device-count` in `dist/`.

### 4.5 JS posture (K0 pending)

**No-JS baseline.** Every page above is static HTML under J3's budgets (≤150 KiB, 0 scripts). Long lists are paginated.
Claim lists on artifact pages use `<details>` per predicate group. Browser find-in-page works on the text pane.

**Enhanced (only if K0 allows).** A filter/sort island over the artifact index JSON (small: 255 rows today; thousands
after activation, **inference**), reusing the `/search/` island with evidence facets (J3 G-11). Also a side-by-side
capture diff with scroll sync. The baseline stays complete.

---

## 5. What can ship before real captures (interim, EV-01)

These are honest improvements that need neither G2 step 1 nor TX-08.

1. **List the 255 artifacts** that `evidence.json` already carries, grouped by source (219), with the source's registry
   name and a type label. Each is labelled **"run record — SIG did not store this document"** where
   `capture_classification = 'synthetic'`; the export adds that field (EV-01). Of the 255, 238 are `camera_registry`
   (178), `connector_run` (33) or `terms_page` (27) artifacts. The other 17 are portal and agenda documents, news
   articles, bill indexes, contracts, a policy, a statement and a community map. They are still what the
   claims point to, and showing them is truthful (D-K8-4).
2. **Fix the copy** (shared with K7 WX-07). Drop the research-queue CTA. The body names the cause class ("not yet linked
   to stored documents").
3. **Apply `{PUB_ARTIFACT_GATE}`** to the `evidence_artifacts` query (NEW-9) before any more artifact metadata is shown.
4. **Remove the fixture capture diff** from export builds (NEW-8).
5. **Where subject claims already carry an upstream `document` URL** (agenda items, notices), show it on the item's record
   or watch page as "the source's own link (recorded as a claim)". It passes the S-6 scrub and is never presented as a
   capture.

---

## 6. Draft requirements (provisional `SIG-EVUI-Dnn`; T1 folds them into SIG-UI-028/029/030 and J3's SIG-TRANSP)

| id | requirement | acceptance criteria |
|---|---|---|
| SIG-EVUI-D01 | `/evidence/` MUST list every publishable artifact in the release, paginated, with a human title, source, type, classification and lane. It MUST NOT be empty while the release has publishable artifacts. | crawl: listed rows == artifact index rows == `evidence.json` artifacts; 0 scripts; each page ≤150 KiB |
| SIG-EVUI-D02 | Each publishable artifact MUST have a page with the §4.2 blocks. Each field MUST be a value or a named absence. | JSON Schema `sig.evidence-artifact/1` validates for all artifacts; no empty field; no UUID-only title (crawl) |
| SIG-EVUI-D03 | Every capture row MUST show its classification, and a synthetic capture MUST be labelled a run record. `bytes_available`/"download original" MUST appear only for raw-ok lanes with bytes in the public archive (= J3 SIG-TRANSP-D05). | matrix test per lane × classification; 0 download links for non-raw-ok sources |
| SIG-EVUI-D04 | The claim viewer MUST render by binding state × lane × Part VIII class (§4.3). A missing document text MUST NOT fail the build when the lane forbids bytes. **Amends SIG-UI-028** ("render the document with the supporting span highlighted *where the lane permits showing the bytes*; otherwise the locator, digest and a view-at-source link"). | fixture spine with one claim per row of the §4.3 table → one page each, each rendering the expected pane |
| SIG-EVUI-D05 | Capture diffs MUST be computed only from real captures of the same artifact. An export build MUST contain no fixture evidence identifiers. | build check greps `dist/` for fixture ids (`active-device-count`, `okcpd-…`, `contract:okcpd-…`) and fails in export mode |
| SIG-EVUI-D06 | The artifact export MUST apply the shared artifact eligibility gate (ADR-124). A withheld or withdrawn artifact MUST be absent from indexes and answer 410 with a content-free tombstone. | fixture spine with a `withhold` artifact disposition → absent from `evidence.json`, the index and counts; tombstone route 410 |
| SIG-EVUI-D07 | Every claim MUST be navigable to its evidence: record claim anchors link to artifact pages, and `/v1/claim` returns `artifact_id`, capture ids and a provenance href (J3 §5.5). | API parity test; crawl from 100 sampled record anchors → artifact page 200 |
| SIG-EVUI-D08 | Empty or partial evidence states MUST name the cause class (not built / not yet linked to stored documents / rights-restricted) and MUST NOT call a pipeline gap a research gap. | copy lint + reviewer sign-off |
| SIG-EVUI-D09 | Claim-view pages MUST be generated for every document-genre claim with an `actual_capture` binding, up to a published cap. The cap and the overflow count MUST be stated on `/evidence/`. | count test: generated == min(eligible, cap); the disclosure is rendered |
| SIG-EVUI-D10 | Artifact handles MUST be human-readable, stable across releases, and redirect when they change. | handle golden tests (K11 §3); redirect map test |

---

## 7. Acceptance journeys (agent walkthroughs; P4)

| id | persona | task | success |
|---|---|---|---|
| KJ8-1 | attorney (P4-T1) | from a `/dossier/md/` figure, reach the document behind one claim | ≤4 clicks: figure → record → claim anchor → artifact page with capture hash, time, method and "view at source". **Before activation:** the run-level statement plus the source's run and capture pages; no dead end |
| KJ8-2 | journalist | "When did SIG capture the Austin procurement notice NA230000215, and what hash?" | `/evidence/source/procportal_austin_tx/` → artifact → capture row with full sha256 and a UTC time; "view at source" opens the city's page |
| KJ8-3 | skeptic | "How much of SIG rests on documents vs run records?" | the `/evidence/` state panel gives counts by binding state and lane that reconcile with the downloadable statements file |
| KJ8-4 | journalist | "What changed on a vendor portal between two captures?" | a diff page when two real captures exist; otherwise "only one capture of this artifact" |
| KJ8-5 | any | open a derived-only claim | the locator, hash and view-at-source render; no bytes; no build failure |

---

## 8. Scale and budgets

**Artifacts.**
- 255 today (tier-0, captured).
- After activation, bounded by distinct artifacts across 6,144 capture digests and 208 run-row sources (J4, J1). This is
  thousands of static pages at most (**inference**).
- Pages are ~10–30 KB each (**inference**, from today's dossier pages).

**Claim views.** Only document genres with actual captures. J3 §5.2 suggests ≤20k (**inference**), inside J3's
"Astro +≤5 min for ≈3k pages" per-release budget only if they are rendered by the release-page helpers, not Astro. EV-03
decides that at T3.

**`web/evidence.json`** grows. It is replaced by `evidence/index.json` (the artifact index, paginated shards ≤1 MB) plus
per-artifact JSON twins.

---

## 9. Round-11 ticket outline

| key | title | size | scope | depends | live / gate |
|---|---|---|---|---|---|
| EV-01 | Evidence truth fix + interim artifact list | S | §5 items 1–4; exporter adds `capture_classification` and `source_name` to `evidence.json` artifacts; `{PUB_ARTIFACT_GATE}` on `evidence_artifacts`; fixture diff removed in export mode + the D05 build check; copy (shared with WX-07) | none (registry names already read by `source_names`) | republish (safety wave) |
| EV-02 | Evidence hub + artifact pages | M | §4.1, §4.2, §4.4 skeleton; facet and pagination routes; handles; JSON twins; links from sources, records, watch and tasks | TX-01, TX-03 (captures.jsonl), TX-05a (source pages), TX-08b (evidence anchors, upstream_href); K11 handle grammar | republish |
| EV-03 | Claim viewer v2 + real capture diff | M | lane-aware `ClaimView` (`pane` union), `assertClaimView` by lane, generation for document-genre `actual_capture` claims with a cap, diff from real captures; spec amendments to SIG-UI-028/029 | G2 steps 1–2 (ACT-11, ACT-14: L44–52 + actual bindings); TX-01 (tier derivation, J3 NEW-2); TX-08a; TX-12 for raw-ok text; D-K8-1, D-K8-2 | republish after activation |
| (merged) | `/v1/claim` artifact_id, `/v1/evidence` classification and honest `bytes_available` | — | → **J3 TX-08b / G2 ACT-08** | — | — |
| (merged) | Figure → evidence pointers on every page | — | → **J3 TX-09** | — | — |
| (merged) | Raw archive and "download original" | — | → **J3 TX-12** | — | — |
| (merged) | Disappearance written to `evidence_artifact` (F-229) | — | → **F5 / F3 owner** (not K8) | — | — |

**Order.** EV-01 in the safety wave, with WX-07 and RQ-00 (K11). EV-02 in the first product wave, after TX-03, TX-05a and
TX-08b; with legacy_synthetic data it already gives real value (source and capture history). EV-03 after G2 steps 1–2.

---

## 10. Operator decisions needed

| id | question | recommendation |
|---|---|---|
| D-K8-1 | May claim views quote an excerpt from derived-only sources, and how long? | a locator always; an excerpt of ≤300 characters only where the source's recorded terms permit quotation (J4 per-source evidence); otherwise none. Needs E/J4 input; not legal advice |
| D-K8-2 | Claim-view scope and cap | document genres with `actual_capture`; cap 20k per release; overflow count disclosed |
| D-K8-3 | Are `/evidence/artifact/<handle>/` pages latest-view aliases of the release anchors, or separate pages? | aliases (one template, one data path); citations always go to `/r/<pub>/…` |
| D-K8-4 | Show the 255 synthetic "run record" artifacts before activation, or hide `/evidence/` until real captures are bound? | show them with honest labels. They are what every claim points to today, and hiding them repeats the blank page |

---

## 11. Risks

- **R1: Exposure through upstream URLs.** Showing `evidence_artifact.url` and capture `source_uri` exposes query strings
  and person-level pages. Mitigation: TX-01 (S-1…S-14, S-6) is a hard dependency of EV-02, and NEW-9's gate lands first.
- **R2: Latent public-tier bytes.** J3 NEW-2: the actual-capture writer marks every capture `public`. EV-03 must not ship
  before TX-01's tier derivation.
- **R3: Overclaiming** ("evidence" implies "document"). Mitigation: E-P2 labels and the binding-state counts on the hub.
- **R4: Page explosion.** Mitigation: E-P4 and the cap.

## 12. Interfaces

- **J3:** TX-01, TX-03, TX-05, TX-08, TX-09, TX-12, TX-13a, TX-15 (one data path).
- **J4:** lanes, S-rules.
- **G2:** steps 1–2.
- **K2:** entity pages for subjects.
- **K5:** dossier source contributions link to artifact pages.
- **K7:** watch item evidence and the recommender.
- **K9/K10:** source pages host capture lists; artifact pages link to them.
- **K11:** the handle grammar; tasks ↔ artifacts.
- **K13:** the `<ProvenancePanel>` component inventory.
- **K0:** the enhanced island only.

## 13. New findings (`findings/incoming/K7K8K11.csv`)

| id | title (short) | sev |
|---|---|---|
| NEW-6 | Empty states on `/watch/` and `/evidence/` blame a "research gap" and link the research queue (shared with K7) | S2 |
| NEW-7 | `/evidence/` renders only `claim_views` and ignores the 255 artifacts the release publishes, so the page is blank | S2 |
| NEW-8 | The viewer model requires document bytes for every non-sealed capture and cannot show synthetic, derived-only or link-only states; the capture diff is a fixture pair in every build mode | S2 |
| NEW-9 | The public `evidence_artifacts` export omits the shared artifact-eligibility gate that `evidence_bindings` applies (latent withdrawal-barrier gap) | S2 |
| NEW-5 | The recommender over the live `evidence.json` yields NaN scores for all 255 artifacts (shared with K7) | S2 |

Existing findings this note relies on and does not duplicate: F-098, F-357 (the symptom and synthetic provenance), F-368
(public tier on actual captures), F-375 (digest-only capture history), F-376 (OKC seed sources), F-229 (disappearance not
written).

## 14. Limits

- The spine was not queried. The counts of actual captures per genre after activation are inferences from J1/J4.
- The claim sentence templates, excerpt policy and banner copy are agent-drafted and need operator approval.
- The 17 non-registry, non-run artifacts were not opened individually. Their upstream URLs are not in the public file.
