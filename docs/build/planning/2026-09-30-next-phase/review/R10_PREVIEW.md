# C4 — Pre-release review of the unreleased Round-10 surfaces (local)

Row **C4** of `META_PLAN.md` (Stage P, owner R). Run window 2026-09-30T17:00:17Z → 17:32:21Z (`date -u`). Worktree
`/Users/stevenvitali/Eleutheria-next-phase`, branch `claude/next-phase-planning`. HEAD moved from `4aff9a48` to `888930ff`
during the run because other rows committed. `web/ api/ ops/ exports/ db/ policy/ tasks/` are byte-identical to chain tip
`b051732c` (checked with `git diff --quiet b051732c HEAD -- …`). `PD` below means `docs/build/planning/2026-09-30-next-phase`,
and `LG` means `docs/build/logs/next-phase/C4` (gitignored).

> **This is an agent walkthrough, not user research** (P4/P5). `D-R10-USERS-1` stays OPEN. Nothing here counts as a human
> evaluation. Independence: `META_PLAN.md` Appendix A and `PD/findings/**` were not read. The only file this row wrote
> under `findings/` is `findings/incoming/C4.csv`.
>
> **Every result carries its layer (P5).** `fixture-verified` means the web fixtures build or the synthetic P32.24 corpus
> (75 records). `staging-verified` means the P32.25 staging registry (the GATE-G3 candidate) or a local PG18 intake stack.
> Nothing here is `live-executed` or `public`. Production was not touched.

---

## 0. Summary

- **Surfaces that ran.**
  - Web app, fixtures mode: `/releases/`, `/research-dossier/` with `okc-alpr` and its `.json`, the chain-tip
    `/dispute/`, and the P32.15 workspace on `/search/`, `/map/` and `/network/`.
  - The two static release trees, from P32.25 staging and the P32.24 corpus: `/releases/`, `/releases/<pub>/`,
    `/r/<pub>/c/<comp>/…`, `/r/<pub>/dossier/<scope>/` and `/entity/…`.
  - Release search on the read API, over three registries (staging, corpus, and a scratch copy with a release-level
    withdrawal), plus the API with no registry.
  - The intake receiver in its non-operational 503 state, and in a local operational preview on PG18.
  - Moderation through the curation app, and the P32.16a apply and publish steps.
  - The production nginx config, run over a composite of the corpus tree and `web/dist`.
- **What did not run.**
  - The **export-mode** web build. It fails as C1 predicted: `leverage.json` is missing ([NEW-26]).
  - `sig-ops up`. The Docker daemon was down, so I used podman equivalents (§1).
  - axe with JS disabled. It is not applicable there.
- **Readiness (§6).**
  - **Blocked (5):** the release archive, the research dossiers, the operational intake flow, the staging candidate, and
    the production composition.
  - **Needs work (7):** Astro `/releases/`, the released dossiers, release-search JSON, release-search no-JS HTML, the
    workspace islands, `/dispute/`, and `/entity/` stubs.
  - **Ready (1):** the non-operational intake 503 state only.
- **Findings.** 32 (`NEW-1…NEW-32`): **0 S0 · 11 S1 · 18 S2 · 3 S3**. No S0, because nothing reviewed is exposed.
  NEW-2 and NEW-11 would become **S0 on exposure**: false provenance about named agencies and sources.
- **Positives, which are not findings.**
  - axe found 0 WCAG 2.x/2.2 AA violations on the 26 JS-on page states tested (26 distinct URLs). Lighthouse accessibility scored 1.0 on
    all 11 runs.
  - Every archive page, research-dossier page and API-search HTML page ships 0 `<script>`.
  - All three island budgets are inside their ceilings on fixtures.
  - The Part VIII screen refuses a plate string before storage.
  - Receipts are idempotent. Apply is exactly-once (a retry reconciles). The moderation transitions fail closed.
  - Search honours the withdrawal barrier: a release deny gives 410 with a tombstone, and entity/claim denies are
    dropped before pagination.
  - An unknown workspace-state version shows a visible notice. Back and forward restore the query.
  - The intake status token never appears in a URL, and the CSP is `default-src 'none'`.

---

## 1. Environment and exact commands

| item | value |
|---|---|
| Tools | node v25.2.1, npm 11.6.2, uv 0.12.6, Python 3.12.14, Playwright 1.62.1 with chromium-1234 (from the worktree's own `web/node_modules`), `@axe-core/playwright` 4.13.0, Lighthouse from `web/node_modules/.bin`, podman 6.1.0 (applehv machine, already running) |
| Docker | **unavailable**: `docker info` reported that the daemon socket `~/.docker/run/docker.sock` does not exist. Docker.app was not started. Podman was used instead |
| `postgis/postgis:18-3.6` | there is no arm64 manifest (`no image found in image index for architecture "arm64"`), so I pulled `--platform linux/amd64` and ran it under emulation |
| Ports used (all `127.0.0.1`) | 4331 web/dist · 8091 staging `staged/` · 8092 corpus `staged/` · 8093 composite (web/dist + staging staged) · 8095 nginx container (prod config) · 8010 API + corpus registry · 8011 API + staging registry · 8012 API with no registry · 8013 API + scratch withdrawn registry · 8002 intake (non-operational) · 8003 intake (operational preview) · 8004 curation + `--intake-dsn` · 55432 PG18 container |
| Not mine, left alone | :4321 (node pid 48452, pre-existing) and :8000 (`sig-api` pid 77349 from the main checkout, started 2026-09-14) |
| Teardown | every listener killed at 17:26:11Z. The containers `c4-sig-pg` and `c4-nginx` and the PG anonymous volume were removed (17:26:26Z). API :8010 was briefly re-run for the 409 probe and stopped at 17:32:13Z. The podman image cache is left: postgis amd64, `sqitch/sqitch`, `nginx:1.27.5-alpine` (`podman rmi` if unwanted) |
| Gitignored artefacts | `web/node_modules` (496 MB), `web/dist` (2.5 MB), `web/.astro`, `LG/**` (52 MB, including `dist-export/` from the failed build, composite trees and a scratch registry). The pre-existing `.venv` was reused. No tracked file was edited |

Commands, in order. The first word of each "result" cell is ok, **FAILED** or **UNAVAILABLE**:

| # | command (abridged; full logs in `LG/logs/`) | result |
|---|---|---|
| 1 | `npm --prefix web ci` | **FAILED, harness only**: my wrapper aborted because `git check-ignore web/node_modules` exits 1 on a directory path. The re-run succeeded 17:01:08→17:01:13Z (`LG/logs/npm_ci.log`) |
| 2 | `cd web && SIG_DATA_SOURCE=export SIG_EXPORT_DIR=$PWD/../docs/build/reports/p32.23a-release-candidate/candidate_export npx astro build --outDir $LG/dist-export` | **FAILED** (exit 1, 17:02:03Z): `SIG_DATA_SOURCE=export but the leverage metric artifact is missing: …/candidate_export/web/leverage.json`. Not patched around (PROTOCOL §8 5b). The candidate also has no `web/tiles/*-sites.pmtiles` and no `web/releases.json` |
| 3 | `cd web && SIG_RELEASE_SEARCH_BASE=http://127.0.0.1:8010 npx astro build` | ok: 56 pages (17:02:10Z) |
| 4 | `python3 -m http.server {4331,8091,8092,8093} --bind 127.0.0.1 --directory …` | ok |
| 5 | `uv run sig-api serve --host 127.0.0.1 --port 8010 --release-registry docs/build/reports/p32.24-investigation-journey-verification/corpus_registry`, and `--port 8011 --release-registry docs/build/reports/p32.25-accepted-release-verification/staging_registry`, `--port 8012` (no registry), `--port 8013 --release-registry LG/scratch_registry_withdrawn` (the corpus plus one `release_artifact` withdraw) | ok: `/health` 200 in-memory |
| 6 | `LG/tools/probe.sh` (curl): 51 probes, recorded in `LG/curl/probes.tsv` | ok (§3.4) |
| 7 | `podman run -d --name c4-sig-pg --platform linux/amd64 -e POSTGRES_USER=sig -e POSTGRES_PASSWORD=sig -e POSTGRES_DB=sig -p 127.0.0.1:55432:5432 docker.io/postgis/postgis:18-3.6` | ok: ready 17:03:46Z |
| 8 | `podman run --rm --network container:c4-sig-pg -v $PWD/db:/repo:ro -w /repo sqitch/sqitch:latest deploy db:pg://sig:sig@127.0.0.1:5432/sig` | ok: 48 changes, including `intake_storage`, `intake_application_bridge` and `recovery_apply` |
| 9 | `SIG_INTAKE_ENABLED=1 uv run sig-api serve-intake --host 127.0.0.1 --port 8002 --dsn postgresql://sig:sig@127.0.0.1:55432/sig` | ok (non-operational) |
| 10 | step 6b of PROTOCOL: the scratch `LG/scratch_ops/config.toml` (only `operational = true`), then `SIG_INTAKE_ENABLED=1 SIG_INTAKE_OPERATIONAL=1 SIG_INTAKE_FORM_SECRET="$(openssl rand -hex 32)" SIG_INTAKE_ABUSE_SECRET="$(openssl rand -hex 32)" uv run sig-api serve-intake --port 8003 … --ops-config LG/scratch_ops/config.toml` | ok. The orchestrator's C4 brief asked for an end-to-end walk against the local receiver only. Secrets lived only in the shell. Submissions were synthetic, with no personal data. The receipt tokens were deleted before hashing |
| 11 | `uv run python -c "…ops.journey_verify._seed_journey_target(dsn,'c4local')"` | ok: seeded one fixture target claim into the local PG only |
| 12 | `SIG_CURATION_ENABLED=1 uv run sig-api serve-curation --port 8004 --intake-dsn <local dsn>` | ok: `token_store: demo` |
| 13 | `node LG/tools/capture.mjs …` (the PROTOCOL §6.4 helper plus axe, tab stops and print), for the 55 entries in `LG/tools/caplist.txt` | ok. **Harness error:** under zsh, the multi-flag entries were not word-split on the first pass, so I re-ran the 14 affected entries. The three files `…171438Z_W05_search_desktop.png`, `…171450Z_W06_map_desktop.png` and `…171459Z_W07_network_desktop.png` are JS-on duplicates, not no-JS. The true no-JS captures are at 17:17:16–57Z |
| 14 | `node LG/tools/workspace.mjs` and `workspace2.mjs` (back/forward and deep-link checks) | ok |
| 15 | `node web/scripts/measure-island-budgets.mjs --out LG/logs/island-budgets-c4.md` | ok: all inside |
| 16 | `lighthouse <url> [--preset=desktop] --only-categories=performance,accessibility,best-practices,seo` over 11 runs (`LG/lh/`) | ok |
| 17 | `podman run -d --name c4-nginx -p 127.0.0.1:8095:8080 -v LG/nginx/nginx.conf:/etc/nginx/nginx.conf:ro -v LG/site-composite-corpus:/mnt/sig-web:ro nginx:1.27.5-alpine`. The config is `ops/web/nginx.conf` with the Brotli `load_module` and `brotli*` lines removed | first try **FAILED**: my strip left a dangling `brotli_types` list (`unknown directive "text/plain"`). The second try was ok |
| 18 | `uv run sig-ops release-serve check --registry <corpus_registry> --route <route>` | ok: dep-41 and dep-54 give `permitted:false` (rc 4); dep-00 gives `permitted:true` |

---

## 2. Fixture-only vs staging, and how each page discloses it

| surface | data behind it here | does the page itself say so? |
|---|---|---|
| web `/releases/`, `/search/`, `/map/`, `/network/`, `/research-dossier/`, `/dispute/` | `web/src/lib/*-fixture.ts`. The placeholder publication is `p-000…001`, data release `sig-2026-09-27-demo` | **No**, apart from the string `sig-2026-09-27-demo`. The pages name real agencies and vendors (City of Oklahoma City, Flock Safety, OKC County Sheriff, Tulsa PD) with made-up values and link `https://fixture/okc-*` ([NEW-27]). The "How we know this" and "Cite this page" blocks carry fixture provenance (as-of 2026-08-20, "Partially human-reviewed") that disagrees with the release as-of 2026-09-27 shown on the same page. That disagreement is fixture-only |
| release archive (P32.24 corpus `p-81f1986a…`) | **synthetic by declaration**: 75 records, "Acceptance Deployment NN" | Partly. Each record's source attribution reads "© src_acc_registry (acceptance fixture)" (73 pages), and the data-release id ends in `-acceptance`. There is no banner saying "synthetic" |
| staging candidate (P32.25 `p-17b713ce…`, the GATE-G3-accepted candidate) | **0 records, 0 compartments**, 16 evidence pages, as-of 2026-10-19 (later than `date -u`) | **No.** Evidence pages cite real source ids (`atlas_registry`, `osm_overpass`) with `https://example.test/…` locators, and say the locator "identifies the pinned evidence object in the custody store" ([NEW-11]) |
| research dossiers (candidate `research_dossiers.json` and the P32.18–P32.20 print HTML) | **hand-authored stand-in documents**. Each `EVIDENCE_PACK.md` says: "the documents replayed committed stand-ins; the URLs are reviewed targets, not captured bytes" | **No.** The pages render the government URLs as sources, with "retrieved 2026-10-01", under the headline "Reviewed research dossier". The stand-in documents carry `access_mode=document`, the same value as real captures, and the template renders neither `access_mode` nor `capture_method`. The Tulsa and San Diego prints mention "stand-in"/"fixture" on 0 pages ([NEW-2], [NEW-3]) |
| intake / moderation | local PG18 with one seeded fixture claim | n/a (local only) |

---

## 3. Per-surface review

### 3.1 Astro `/releases/` (fixtures) and the staged `/releases/` it collides with
- It renders with 0 scripts, one `h1`, a skip link and landmarks, and axe finds 0 violations. It is **not in the site
  navigation**: 17 nav links, none to `/releases/`. Only `/search/` links to it.
- The 66-character publication id does not wrap: scrollWidth 807 px at 320 px ([NEW-21]).
- **The page path collides.** The staged tree also ships `releases/index.html`. The publish plan syncs the staged tree
  into the web bucket, and the web deploy runs `rsync --delete-unmatched-destination-objects web/dist`, so whichever
  sync runs last wins. The next web deploy also deletes `/r/` ([NEW-10]). Composite digests: Astro `78d144d8…`, staged
  `66af349e…`, and the composite kept the staged page (`LG/logs/releases_index_collision.txt`).
- The staged `/releases/` (exports-rendered) is minimal and has no site nav. It shows a "(latest)" marker.

### 3.2 Release archive `/releases/<pub>/`, `/r/<pub>/c/<comp>/…`, `/entity/…` (P32.24 corpus)
- **Broken navigation, one root cause.** `release_pages.py:117,193` emit `../../entity/…` and `../../evidence/…` from
  pages that sit three levels deep. The crawl from `/releases/` found 164 URLs, of which **150 return non-200**:
  - every browse → record link and jurisdiction → record link returns 404;
  - every record → evidence link returns 404;
  - this holds under both http.server and the production nginx config ([NEW-1]).

  The "complete browse, no service required" fallback is therefore dead.
- No page has a dispute link or site navigation ([NEW-5]).
- Record pages show both sharing edges as `sharing_access`, so configured access and observed use cannot be told apart
  ([NEW-6]).
- Positives:
  - Record pages state the location clearly ("Point not reported — this record does not publish a location").
  - They disclose `Resolution eval provisional … (D-R6.1-EVAL)`.
  - They carry the licence per compartment (CC-BY-4.0, ODbL-1.0).
  - The citation block says "cite this URL, not a 'latest' alias".
  - The evidence page says capture bytes are not served (T3 is satisfied if the page is reached).
- **Withdrawals.**
  - Under http.server the tombstone pages are honest. Under the production nginx config the deny map returns nginx's
    generic 136-byte "410 Gone", and the `…/index.html` alias bypasses the map (200, tombstone bytes) ([NEW-14]).
  - The `/entity/` stub for the withdrawn `ent-acc-dep-41` still returns 200 and links the `index.html` form.
- `/r/<pub>/` returns 403 under nginx because the namespace root has no landing page ([NEW-29]).
- The staging candidate's landing page shows an empty compartments table marked "Completeness: complete" ([NEW-31]).
  Its 16 evidence pages are fixtures ([NEW-11]).

### 3.3 Released dossiers `/r/<pub>/dossier/{okc,tulsa,san-diego}/`
- Nothing in the tree links to them ([NEW-7]).
- The text has no provisional or eval-deferred posture. That fails T7.
- Section headings are raw keys (`at_a_glance`, `what_is_deployed`, `how_we_know_this`).
- There is no licence.
- The print is one page with the as-of but no permalink.
- Positive: counts are framed as "Observation-level count … not a resolved device census", and gaps are labelled
  `NOT_RESEARCHED`.

### 3.4 Release search API: status matrix (`LG/curl/probes.tsv`, 17:05Z; 409 at 17:32Z)
| state | probe | result |
|---|---|---|
| 200 JSON / HTML | K01, K02, K03 (Accept `text/html`) | ok. Scope 63/63, keyset cursor, `total_matches: not_computed` |
| 200, empty | K04/K05 `zzqx-nonexistent` | empty JSON. The HTML says "recorded absence, not missing research" ([NEW-4], S1) |
| 404 `unknown_publication` | S05, S06 (`latest`), S12 (fixture `p-000…001`) | ok |
| 404 `unknown_compartment` | S01, S02 (staging has 0 compartments), K17 | ok. With `format=html` the response is still JSON (S04, S09) ([NEW-13]) |
| 409 `cursor_context_mismatch` | K26 (a `sig_graph` cursor used on `osm_physical`), K27 (a different q) | ok |
| 410 `withdrawn` + tombstone | K22/K23 (scratch registry with a release deny) | ok, but always JSON |
| 422 | K06/K07 `query_too_short`, K08/K09 limit, K10 `malformed_cursor`, K11/K12 location, K20 `query_too_long`, S08 unknown param | ok |
| 503 | K21 `release_search_unconfigured` (no registry); S03 `index_not_staged` + Retry-After for pseudo-compartment `web` ([NEW-29]) | ok / S3 |
| runtime denies | K18 (the withdrawn id gives 0 hits); a full walk returns 61 records | the scope still says 63 eligible and `excluded_records_by_reason: {}` ([NEW-12]) |
| XSS probe | K25 `<script>` in q, `format=html` | escaped, 0 `<script>` |

In production, `/v1/…` is reachable from neither the web origin nor the static pages ([NEW-9]):

- The `sig-api` CMD has no `--release-registry`.
- nginx has no `/v1` proxy, and the LB routes only to `sig-web`.
- `SIG_RELEASE_SEARCH_BASE` is unset.
- The API's no-JS result links are relative `/r/…`, which returns 404 on the API origin.

### 3.5 Release search no-JS HTML (API `format=html`)
- 0 scripts, `lang` set, labelled selects, axe 0.
- The page states that the page order is not a relevance score or a probability of truth, and that search is not
  federated across compartments.
- The pager says "next 50 →" whatever the limit ([NEW-28]).
- Error states are raw JSON ([NEW-13]).
- Reflow is 507 px at 320 ([NEW-21]).

### 3.6 Coordinated workspace islands `/search/`, `/map/`, `/network/` (fixtures)
- Budgets are inside (`LG/logs/island-budgets-c4.md`):

  | island | script (raw / ceiling) | document (bytes / ceiling) |
  |---|---|---|
  | map | 1,785,585 / 2,000,000 | 22,597 / 153,600 |
  | network | 231,446 / 400,000 | — |
  | search | 229,900 / 400,000 | — |

- Lighthouse:
  - accessibility 1.0 on every run;
  - performance: `/map/` 0.44 mobile (LCP 8.25 s, TBT 788 ms) and 0.91 desktop; `/network/` 0.97 / 0.92 (desktop CLS
    0.177); `/search/` 0.96 / 1.0.
  - **Caveat:** the numbers come from fixtures only (6 sites). The deployed real-data `/map/` document is 3.46 MB
    against a 153,600-byte ceiling ([NEW-25]).
- URL state:
  - typing a query updates the URL to `?v=1&release=…&q=Oklahoma&view=list`, and back/forward restores it;
  - `?v=9` shows the notice "State version "9" is not supported…".
  - Defect: the static "Investigation views" links drop `q` (only the island links carry it), and the no-JS
    quick-filter box renders empty ([NEW-24]).
- `/network/` explains the three access-edge types well, with two non-colour channels and an ER-quality note on each
  statistic. The map has a table equivalent.

### 3.7 `/research-dossier/` (+`okc-alpr`, `.json`) and the P32.18–P32.20 print dossiers
- Structure is good: twelve questions, six answer states, "Disputed" rendered with both values, "Unknown" with the
  search basis and the follow-up, an independent checklist, and "What we don't know".
- **Blocking defects.**
  - The headline says "Reviewed research dossier" while `review_status=not_run` ([NEW-3]).
  - The stand-in source documents are presented as captures with real government URLs and future retrieval dates
    ([NEW-2], [NEW-32]).
- **Other defects.**
  - No licence in the HTML or the JSON ([NEW-22]).
  - Prints (6–8 pages) carry a permalink on no page, and the web print shows the as-of on page 1 only ([NEW-23]).
  - Duplicated gate text and raw enums ([NEW-28]).
  - The page is not in the site nav; it is reachable from `/dossier/`.
- The export-mode rendering could not be produced ([NEW-26]). The candidate JSON was inspected directly: 3 dossiers,
  all `not_run`, rubric 34, 24 and 29 of 36, no pilot complete.
- Part VIII: the rendered dossiers show no person-level data.

### 3.8 `/dispute/` (chain tip)
- It honestly says the receiver is not operating, lists the outcomes (including Refuse and Annotate), and states the
  Part VIII refusal and that a report never auto-applies.
- It opens with "Anyone can ask SIG to correct…" but offers no interim channel and does not say there is none
  ([NEW-20]).
- Requirement ids and "GATE-G3" appear in public copy.
- It promises `/intake/new` "on this same site", which returns 404 under the production composition ([NEW-9]).

### 3.9 Intake: non-operational → operational preview → moderation → P32.16a application
- **Non-operational (8002)** — ready as a state.
  - `GET /` reports `operational:false`.
  - `/intake/new` returns 503 with an honest HTML page (no-store). `POST /intake/v1/reports` returns 503
    `receiver_not_operating`.
  - The 503 page has no viewport meta and names `GATE-G3 / HG-11`.
  - `/intake/status` shows a receipt form even though no receipt can exist yet (S3, noted).
- **Operational preview (8003)** — form → receipt.
  - The gate opened with `owner=""` and `staffed=false` ([NEW-15]).
  - The form (0 scripts, strict CSP) defaults the category to "Privacy harm", renders 980 px wide on a phone, and
    makes the reporter hand-type `p-<64 hex>` and record keys ([NEW-19]).
  - Receipt 201: "Received; not yet verified or published", with the token shown once.
  - A reload re-POST returns the same receipt (idempotent), but as JSON.
  - Refusals, all correct: plate string, text shorter than 20 chars, an unknown field, a contact on a non-legal
    category, a non-https URL, and a missing form token (422/403). All come back as JSON ([NEW-13]).
  - The third submission hit the limiter: burst 3, then a 720 s wait, with rejected submissions charged ([NEW-16]).
- **Moderation (8004).**
  - No token gives 401. The anonymous tier gives 403.
  - The reviewer queue is in priority order with `sla_hours`.
  - **Reviewer detail returns 500** (UUID serialisation) ([NEW-8]).
  - Transitions fail closed: a reviewer cannot approve (403), and apply before approval gives 409
    `no_current_approval`.
  - Demo tokens are active ([NEW-30]).
- **P32.16a application.**
  - The first approved proposal was unapplicable (409 `value_shape_mismatch`) and needed re-proposal and re-approval
    ([NEW-18]).
  - After that, apply returned 201 with `result_claim_id`, and a retry reconciled to the same application.
  - A bad linkage (`latest`) gave 422, and published gave 201.
  - The spine then held 2 claims, and the event trail was received → triaged → proposed → approved → proposed →
    approved → applied → published.
- **Reporter view.** Status shows "resolved" only. The reviewer's `public_response` and the outcome never reach the
  reporter ([NEW-17]).

### 3.10 Production composition (nginx prod config over the composite corpus tree, :8095, 17:24Z)
| path | status |
|---|---|
| `/` | 200 |
| `/releases/` | 200 |
| `/releases/<pub>/` | 200 |
| `/r/<pub>/` | 403 |
| withdrawn record | 410, generic nginx page |
| withdrawn record `…/index.html` | 200 |
| record | 200 |
| mis-resolved browse link | 404 |
| `/v1/releases/…/search` | 404 |
| `/intake/new` | 404 |
| unknown route | 404, 146-byte body |

---

## 4. Task outcomes (agent scripts; outcome codes from P32.24 and PROTOCOL §3)

| task | start | path and outcome | wrong_conclusion_risk | findings |
|---|---|---|---|---|
| **T1** find and cite a record | corpus `/releases/` | release → `sig_graph` → browse deployment/1 → record link returns **404**. Only URL editing reaches the record, whose citation block is good. **abandoned** by navigation; completed_with_detour by URL editing | n | NEW-1 |
| **T2** a record with no public point | API search `location=no-public-point` | 12 hits. The record link is relative, so it 404s on the API origin. Reached directly: "Point not reported — this record does not publish a location". **completed_with_detour** | n | NEW-1, NEW-9 |
| **T3** follow an evidence link | record page | evidence link returns **404**. The evidence page, reached directly, says capture bytes are not served. **abandoned** by link | n | NEW-1 |
| **T4** sharing happened vs allowed | archive record | both edges are `sharing_access`, with no type. **abandoned**. The fixture web `/network/` does answer it, which is a positive | **y** | NEW-6 |
| **T5** search for an absent thing | API search HTML | empty state: "recorded absence, not missing research". **completed** | **y** | NEW-4 |
| **T6** a record is wrong | archive record | no dispute link. The web `/dispute/` says the receiver is not operating. Locally, the operational preview gives receipt → moderation → apply → publish, but the reporter only sees "resolved". **abandoned** in the production posture | n | NEW-5, 8, 9, 17, 20 |
| **T7** what "provisional" means | released dossier | the dossier has no provisional text and nothing links to it. The research dossier says "Reviewed" beside "not_run". **abandoned** | **y** | NEW-3, NEW-7 |
| P1-T1 (re-aimed) "you live in Oklahoma City" | web `/dossier/` → `/research-dossier/okc-alpr/` | 2 clicks, not in the nav. The persona leaves with fixture or stand-in facts about a real city presented as "Reviewed". **completed_with_detour** | **y** | NEW-2, 3, 27 |
| P1-T2 cost and renewal | research dossier | the fixture gives 270,000 USD. The candidate gives next_decision_date 2027-06-30, derived from a stand-in contract. **completed** | **y** | NEW-2 |
| P1-T3 print for council | research dossier print | 6 pages, as-of on page 1, 0 permalinks. The released dossier print is 1 page with no permalink. **completed_with_detour** (the print does not meet SIG-UI-013 rules) | n | NEW-23, NEW-7 |
| P2-T2 cite without it moving | archive record | release-pinned route plus JSON, "never cite the alias". The canonical URL is shown relative (no origin). **completed_with_detour** | n | NEW-1 |
| P10-T1 agency correction | web `/dispute/` | honest non-operating state; no interim channel; no link from records. **abandoned**, which is honest | n | NEW-5, NEW-20 |

---

## 5. Heuristics per surface class (pass / fail / n/a)

| H | web R10 pages (fixtures) | release archive | API search HTML | islands | research dossier | intake pages |
|---|---|---|---|---|---|---|
| H01 numbers | n/a (fixture) | pass | **fail** (NEW-12) | n/a | **fail** (NEW-2) | n/a |
| H02 epistemic | pass | **fail** (NEW-6, 7) | **fail** (NEW-4) | pass | **fail** (NEW-3) | n/a |
| H03 task success | **fail** (T6) | **fail** (T1, T3, T4, T7) | pass | pass | **fail** | **fail** (NEW-8, 17) |
| H04 IA/navigation | **fail** (not in nav) | **fail** (NEW-5) | pass | **fail** (NEW-24) | pass | **fail** (no nav) |
| H05 copy | **fail** (ids in copy) | **fail** (raw keys) | pass | pass | **fail** (NEW-28) | **fail** (GATE-G3) |
| H06 WCAG spot | pass (axe 0) except reflow | pass except reflow | pass except reflow | pass | pass except reflow | **fail** (no viewport) |
| H07 performance/JS | pass (0 scripts) | pass | pass | **fail** (map mobile) | pass | pass |
| H08 mobile | **fail** (NEW-21) | **fail** | **fail** | **fail** | **fail** | **fail** (980 px) |
| H09 print | n/a | **fail** (no permalink) | n/a | n/a | **fail** (NEW-23) | n/a |
| H10 citation | fixture-only as-of mismatch | pass (release-pinned) | pass | pass (URL state) | **fail** (no permalink in print) | n/a |
| H11 licence | **fail** (no site licence) | pass on records, **fail** on dossiers | pass (licence shown) | n/a | **fail** (NEW-22) | n/a |
| H12 Part VIII | pass | pass | pass (escaped) | pass | pass | pass (refusal works); NEW-15/30 are gate risks |
| H13 provenance/trust | fixture-only | pass | pass | pass (ER disclosure) | **fail** (NEW-2, 3) | n/a |
| H14 empty/error states | pass | **fail** (NEW-14, 31) | **fail** (NEW-13) | **fail** (empty no-JS box) | pass | **fail** (JSON errors) |
| H15 discoverability | **fail** (not in nav) | **fail** (no meta description; `/r/<pub>/` 403) | **fail** (no meta description) | pass | pass | n/a |
| H16 consistency | fixture-only as-of mismatch | pass | pass | **fail** (two sets of view links) | pass | n/a |
| H17 freshness | n/a | pass (2026-09-27) | pass | n/a | **fail** (2026-10-01/02) | n/a |
| H18 fixture leak | **fail** (NEW-27) | acceptable (declared) | acceptable | **fail** (fixture) | **fail** | n/a |

---

## 6. Readiness per surface (the input to G2)

| surface | verdict | reasons (finding ids) |
|---|---|---|
| Astro `/releases/` | **needs-work** | page collision with the staged `/releases/` and the deploy-order hazard (10); not in the nav; reflow (21) |
| Release archive `/releases/<pub>/` and `/r/<pub>/c/…` | **blocked** | record and evidence links 404 (1); no dispute or nav path (5); untyped edges (6); a web redeploy would erase the tree (10); generic 410 and a deny-map alias (14) |
| Released dossiers `/r/<pub>/dossier/…` | **needs-work** | orphaned; no provisional disclosure; raw headings; no licence (7) |
| `/entity/` convenience stubs | **needs-work** | links the non-canonical `index.html` form; still 200 for a withdrawn entity (14) |
| Release search API (JSON) | **needs-work** | the engine is sound (all 404/409/410/422/503 states correct), but there is no production wiring (9) and the scope count excludes denies silently (12) |
| Release search no-JS HTML | **needs-work** | empty-state wording (4, S1); JSON errors (13); cross-origin relative links (9); reflow (21) |
| Workspace islands `/search/` `/map/` `/network/` | **needs-work** | budgets and a11y pass on fixtures; view links drop the query (24); map mobile perf and no real-data measurement (25); reflow (21) |
| `/research-dossier/` (+slug, JSON) | **blocked** | stand-in documents undisclosed (2); "Reviewed" label (3); export build fails (26); no licence (22); print (23) |
| `/dispute/` (chain tip) | **needs-work** | no interim channel; jargon (20); promises a same-site `/intake/new` that does not route (9) |
| Intake, non-operational 503 state | **ready** (as a closed state) | honest; S2/S3 copy fixes (19) are recommended before exposure |
| Intake, operational flow (receipt → moderation → apply → publish) | **blocked** | reviewer detail 500 (8); gate ignores owner/staffed (15); limiter behind the proxy (16); the reporter never sees the outcome (17); demo tokens (30); `D-P32.16-1` staffing and retention still unmet |
| Staging candidate `p-17b713ce…` | **blocked** | a fixture: 0 records, `example.test` evidence under real source ids, future as-of (11, 31, 32). It must not be the activated production candidate (`D-P32.23a-1`) |
| Production composition (bucket, nginx, LB, sig-api) | **blocked** | no `/v1` or `/intake` routing; no registry on sig-api (9); `rsync --delete` versus the staged tree (10) |

---

## 7. What must change before production exposure, and what is fixture-only

**Before any G2 activation (in order).**
1. Build a real production candidate (`D-P32.23a-1`) that passes an **export-mode web build**. Supply `leverage.json`,
   the tiles and `releases.json` (NEW-26). Re-run this review on it; the fixtures cannot stand in for it.
2. Fix the relative-link depth in `exports/src/exports/release_pages.py` and add a link-resolution crawl to the release
   validation (NEW-1).
3. Decide the serving topology:
   - route `/v1/releases/*` (and later `/intake/*`) from the LB or nginx to `sig-api`, **or** set
     `SIG_RELEASE_SEARCH_BASE` and make the API HTML links absolute;
   - mount the registry and pass `--release-registry` in the `sig-api` CMD (NEW-9).
4. Merge the web deploy and the release staging into **one** publish step. There must be no `--delete` over `/r/`,
   `/releases/<pub>/`, `/entity/` or `conf/`, and there must be exactly one owner of `/releases/index.html` (NEW-10).
5. Make the deny map serve the tombstone body with 410, and cover the `/index.html` and no-slash aliases (NEW-14).
6. Research dossiers: until real captures exist (`D-P32.18-1`, `D-R10-SOURCES-1`), render a per-assertion
   **acquisition label** (stand-in / fixture transcription / live capture) and a page-level disclosure. Replace the
   "Reviewed" label with the actual `review_status`. Pin dates to the real clock (NEW-2, 3, 32).
7. Add dispute links and site navigation to every exports-rendered page. Render the edge type
   (configured / observed / declared) on archive records and in the published-record JSON. Add the provisional posture
   to released dossiers and link them from the release landing (NEW-5, 6, 7).
8. Fix the release-search empty-state wording and give no-JS clients HTML error pages (NEW-4, NEW-13).
9. Intake, before `[intake].operational` flips:
   - fix the reviewer-detail 500;
   - make the gate require `owner` and `staffed`;
   - normalise the client address at the edge and stop charging refusals to the limiter;
   - surface the outcome and the approved response to the reporter;
   - disable the demo tokens whenever a DSN is set;
   - validate the proposal shape at proposal time;
   - add a category placeholder, a viewport meta and a record-page "report this" deep link (NEW-8, 15–19, 30).

**Fixture-only, not defects of the design.** The fixture provenance blocks and as-of dates on the web pages. The
`p-000…001` search targets that 404 against both local registries. The OKC/Tulsa entities on `/network/` and `/map/`.
The synthetic `Acceptance …` corpus. The fixture research dossier `okc-alpr`. These become defects only if a fixture
build is deployed (NEW-27 asks for a visible fixture marker as defence in depth).

---

## 8. Draft requirements (proposed, for C6/S; each marked `NEW-NEED` or amending an existing id)

| id | draft requirement | source |
|---|---|---|
| DR-C4-01 | Every release build SHALL pass a link-resolution check: every same-origin `href`/`action` in the staged tree resolves to 200, or to an explicitly denied route (410) | NEW-1 (amends SIG-FIND-001/002) |
| DR-C4-02 | Every exports-rendered public page SHALL carry the site navigation, a dispute/correction link and the licence of the data it shows | NEW-5, NEW-22 (SIG-UI-033/049, SIG-LIC-011) |
| DR-C4-03 | Every rendered assertion SHALL show how its bytes were obtained (live capture, committed transcription, or stand-in). A page resting on any non-live evidence SHALL say so above the fold | NEW-2 (`NEW-NEED`, SIG-DOS) |
| DR-C4-04 | Review-state labels SHALL be derived from the recorded review status. No template may hard-code "reviewed" | NEW-3 (SIG-DOS-002, P4/P5) |
| DR-C4-05 | Empty-search copy SHALL say "no released record in this compartment matches"; it SHALL NOT assert research status or absence | NEW-4 (SIG-FIND-003) |
| DR-C4-06 | The public release record and its HTML SHALL carry the access-edge type (configured / observed / declared) | NEW-6 (SIG-UI-024) |
| DR-C4-07 | One publish operation SHALL own the web bucket. Web-site and release-namespace syncs SHALL NOT delete each other, and `/releases/index.html` SHALL have exactly one generator | NEW-10 (`NEW-NEED`) |
| DR-C4-08 | Denied routes SHALL return 410 with the tombstone body, covering every alias (`/`, `/index.html`, no-slash, `.json`) | NEW-14 (SIG-FIND-001) |
| DR-C4-09 | Release-search `scope` SHALL count access-time denials in `eligible_records` and `excluded_records_by_reason` | NEW-12 (SIG-FIND-003) |
| DR-C4-10 | HTML clients of the search and intake routes SHALL receive HTML error pages for every error status | NEW-13 (SIG-UI-050) |
| DR-C4-11 | The intake operating gate SHALL fail closed unless `owner` is non-empty and `staffed = true`. Curation apps with a DSN SHALL refuse demo tokens | NEW-15, NEW-30 (SIG-FIND-006/008) |
| DR-C4-12 | The reporter status SHALL show the outcome kind, the approved public response and the correction or release link once published | NEW-17 (SIG-FIND-008, SIG-GOV-011) |
| DR-C4-13 | Island and page budgets SHALL be verified on an export-mode (real-data) build before activation. `lighthouserc` SHALL cover `/releases/`, `/research-dossier/` and one archive record | NEW-25, NEW-26 (SIG-FIND-005) |
| DR-C4-14 | Every public page SHALL reflow at 320 CSS px; long identifiers SHALL wrap | NEW-21 (WCAG 1.4.10) |
| DR-C4-15 | Displayed as-of, retrieval and release dates SHALL NOT be later than the build clock. The build SHALL fail on a future date | NEW-32 (P2, SIG-METRIC-006) |

---

## 9. Findings index (`PD/findings/incoming/C4.csv`, §8.2 schema, ids NEW-n)

| id | sev | title (short) | routed |
|---|---|---|---|
| NEW-1 | **S1** | archive relative links one level too shallow (browse/evidence 404) | C6 |
| NEW-2 | **S1** (S0 on exposure) | research dossiers: stand-in documents presented as captures | C6;G2 |
| NEW-3 | **S1** | "Reviewed research dossier" while review not_run | C6 |
| NEW-4 | **S1** | empty search says "recorded absence, not missing research" | C6 |
| NEW-5 | **S1** | archive pages: no dispute link, no navigation | C6 |
| NEW-6 | **S1** | archive edges untyped (`sharing_access`) | C6 |
| NEW-7 | **S1** | released dossiers: no provisional posture; orphaned | C6 |
| NEW-8 | **S1** | reviewer detail 500 with the PG store | C6;G2 |
| NEW-9 | **S1** | no production wiring for `/v1` release search or `/intake` | G2 |
| NEW-10 | **S1** | web `rsync --delete` would erase the release tree; `/releases/` collision | G2 |
| NEW-11 | **S1** (S0 on exposure) | GATE-G3 staging candidate is a fixture | G2 |
| NEW-12 | S2 | search scope counts omit runtime denies | C6 |
| NEW-13 | S2 | JSON error bodies to no-JS HTML clients | C6 |
| NEW-14 | S2 | generic nginx 410; deny-map alias gap | C6;G2 |
| NEW-15 | S2 | intake gate ignores owner/staffed | G2 |
| NEW-16 | S2 | intake limiter keys on the peer and charges refusals | G2 |
| NEW-17 | S2 | reporter never sees the outcome or response | C6 |
| NEW-18 | S3 | approved proposal can be unapplicable | C6 |
| NEW-19 | S2 | intake form: default category, no viewport, hand-typed ids | C6 |
| NEW-20 | S2 | `/dispute/`: no interim channel; jargon | C6 |
| NEW-21 | S2 | 320 px reflow failures | C6 |
| NEW-22 | S2 | research and released dossiers lack a licence | C6 |
| NEW-23 | S2 | research-dossier prints lack a permalink and a per-page as-of | C6 |
| NEW-24 | S2 | workspace view links drop the query; empty no-JS box | C6 |
| NEW-25 | S2 | map mobile perf 0.44; no real-data budget measurement | C6 |
| NEW-26 | S2 | export-mode build fails on the P32.23a candidate | G2;H1 |
| NEW-27 | S2 | fixture builds carry no fixture marker | C6 |
| NEW-28 | S3 | copy defects (duplicated gate text, raw enums, "next 50") | C6 |
| NEW-29 | S3 | `/r/<pub>/` 403; pseudo-compartment `web` answers 503; no meta description | C6 |
| NEW-30 | S2 | demo curation tokens active with an intake DSN | G2 |
| NEW-31 | S2 | zero-record release landing is unexplained | C6 |
| NEW-32 | S2 | future as-of, retrieval and release dates | C6 |

---

## 10. Evidence manifest

- All bulky evidence lives under `LG/` (gitignored), with 237 files listed in `LG/SHA256SUMS`.
  - Screenshots and PDFs: `LG/shots/`.
  - Lighthouse JSON: `LG/lh/`.
  - Curl bodies and headers, plus the intake and moderation walks: `LG/curl/`; the probe matrix is `LG/curl/probes.tsv`.
  - Crawls: `LG/text/crawl_{corpus,staging}.jsonl`.
  - Build, server, sqitch, capture and workspace logs: `LG/logs/`.
  - Helpers: `LG/tools/{capture.mjs, probe.sh, crawl.py, workspace*.mjs, intake_client.py, restart_intake.sh, caplist.txt}`.
  - The nginx test config: `LG/nginx/nginx.conf`.
  - The per-capture JSON lines are in `LG/capture.jsonl`, sha256 `f5ed65f4…981bf0`.
- The finding rows cite each file by sha256.
- No secrets were written anywhere. The intake form and abuse secrets were generated inside the shell only. The two
  local receipt status tokens were deleted before hashing, and only redacted `sha256:` prefixes appear in the JSON
  logs.
- `git status` shows this row added only `PD/review/R10_PREVIEW.md` and `PD/findings/incoming/C4.csv`. The other
  untracked files belong to concurrent rows.
