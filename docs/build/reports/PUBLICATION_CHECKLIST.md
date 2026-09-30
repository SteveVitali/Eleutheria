# Publication checklist (§43, SIG-PUB-*)

The pre-launch list every jurisdiction clears before go-public. Each item is ticked
with an evidence link, or marked `gate pending: HG-nn` when it depends on a human
gate the operator has not ticked. **Go-public is impossible until every item is
ticked** — it is a single human decision made against this list.

**Jurisdiction:** Oklahoma City (first jurisdiction, P21.4).
**State:** staging complete; HG-01 ✅ (interim, 2026-09-15); **go-public GATED** (HG-11 items 2–3 + HG-02 counsel on item 4 + the Go-public decision still pending).

| # | Item | State | Evidence |
|---|---|---|---|
| 1 | **Legal home named (HG-01, SIG-GOV-012)** | ✅ ticked (interim — personal capacity) | `docs/governance/governance-and-code-of-conduct.md § Legal home` names **Steven Vitali** as the legal home (individual maintainer, personal capacity, 2026-09-15). Interim personal-name home; a more durable home + counsel (HG-02) recommended before Go-public. `D-P21.4-1` DONE. |
| 2 | **Two-reviewer concurrence (HG-11, SIG-PUB-008)** | `gate pending: HG-11` | `docs/build/okc/concurrence.md` — fewer than two independent reviewer roles recorded; operator answer: SKIP — governance not established. |
| 3 | **Takedown / corrections contact live** | `gate pending: HG-11` | The corrections *mechanism* is built and served (`/corrections`, `/dispute`, the corrections-methodology page); the live contact is a governance item pending HG-11. |
| 4 | **ODbL 4.4(b) disposition (HG-02)** | ✅ ticked | Operator disposition recorded: "OSM-derived surveillance layer is publishable as a Produced Work with ODbL attribution + share-alike notice, kept in its separate ODbL compartment and offered under ODbL; **included in exports (not link-only)**." The jurisdiction export writes the OSM layer to a **separate** `osm_physical` compartment under `ODbL-1.0` (see `exports/out/okc/osm_physical/`, `manifest.json`), attribution "© OpenStreetMap contributors, ODbL 1.0 (share-alike)". |
| 5 | **Sensitivity tier + coordinate rules verified on every published page** | ✅ ticked | The API/store publishes only `sensitivity_tier = 0` (`api/src/api/store_pg.py`), coordinates are jurisdiction-only (the export's `osm_physical` geometry is a jurisdiction-centroid point; the dossier carries no raw sensitive coordinate). `applyPublicationPolicy` runs over every dossier at build time (`web/src/pages/dossier/[slug].astro:30`, SIG-PUB-017) — it can only ever withhold (§0.7). |
| 6 | **Officer-naming gate green on the data** | ✅ ticked | No un-permitted public-employee name is published on the OKC pages: claims are attributed to source roles/records, `policy.officer` two-reviewer gate defaults person-named claims to no-publish (`concurrence.md`), and the hostile-reader review (below) found no uncited or improperly-named claim. |
| 7 | **robots + `/terms` served** | ✅ ticked | `web/public/robots.txt` (crawlable/archivable, SIG-UI-037) ships to `web/dist/robots.txt`; `/terms` is served by the read API (`api/src/api/app.py`, SIG-API-013). |
| 8 | **Licence statement per compartment on `/terms`** | ✅ ticked | `/terms` states the per-compartment licences (CC-BY-4.0 graph; ODbL-1.0 OSM-derived layer, share-alike) — SIG-LIC-004/010; the export `manifest.json` carries the per-artifact licence, and the two compartments are physically separate files (`osm_physical/` vs `sig_graph/`). |
| 9 | **Backups of PG + OCFL taken** | ✅ ticked (staging) | The compose PG volume (`sig_pg_data`) is a durable named volume; `sig-ops down` uses `-v` only on explicit teardown. OCFL evidence is write-once (ADR-023). For go-public, a snapshot of the PG volume + the OCFL root is taken before cut-over (documented in `ops/README.md`). |
| 10 | **Hostile-reader review clean** | ✅ ticked | `docs/build/okc/hostile_reader_review.md` — a reader following `docs/governance/hostile-reader-review-dossier.md` found no uncited claim on the OKC dossier; every number links claim → evidence and the 299-vs-190 contradiction is shown with both sources and dates (§3.1). |

## Go / no-go

- **Staging:** ✅ complete (local staging, HG-12 — `sig-ops up/status/down` healthy; the
  static site built from the export; acceptance queries run against the API).
- **Go-public:** ❌ **NO** — HG-01 now ticked (item 1, interim); still blocked on items 2–3
  (HG-11, operator-deferred 2026-09-15), counsel superseding item 4 (HG-02, operator-deferred),
  and the operator's Go-public decision. This ticket is complete-with-gates-skipped → **RETURN PASS**.

---

## 2026-09-10 re-run (LIVE.2 / GL-LIVE-02, prepare-only) — re-verified gate state

*(Lane-B re-run of the same P21.4 contract on branch `devin/p21-4-live2-rerun`;
append-only. Environment clock read 2026-09-13, so the regenerated evidence files
carry that stamp — the run itself is the chain's LIVE.2 pass.)* The local composed
staging path was re-run **for real** over Docker (`sh docs/build/tools/run_okc.sh`
end-to-end: `sig-ops up` → shadow/fixture connectors → resolution → reconcile →
export → `SIG_DATA_SOURCE=export` web build → J-1 + Q-1…Q-13 against the running API →
`docs/build/reports/okc/acceptance_2026-09-13.json`). Every gate is re-stated at its
**current** posture below; each gated item reads ticked or `gate pending: HG-nn` with
the exact command/action that satisfies it.

| # | Item | Current state (2026-09-10 re-run) | What satisfies it |
|---|---|---|---|
| 1 | **Legal home named (HG-01)** | ✅ ticked (interim — personal capacity, 2026-09-15) — resolves the GL-GATE-01 interim posture: `docs/governance/governance-and-code-of-conduct.md § Legal home` names **Steven Vitali** (individual maintainer, personal capacity). Interim personal-name home, **not counsel**; a more durable home + HG-02 counsel recommended before real public exposure. `D-P21.4-1` DONE. | Satisfied for HG-01. Go-public still gated on HG-11 (items 2–3) + counsel superseding item 4. |
| 2 | **Two-reviewer concurrence (HG-11)** | `gate PARTIAL: HG-11` — **interim first reviewer named 2026-09-15** (Steven Vitali, maintainer/first reviewer, `governance-and-code-of-conduct.md § Reviewer roles`); the **second independent reviewer + written concurrence are still owed**. `docs/build/reports/okc/concurrence.md` still a template. `D-P21.4-2` PARTIAL. | Name a second independent reviewer + record written concurrence (`ReviewerConcurrence`, SIG-PUB-008); then tick. Go-public stays blocked until then. |
| 3 | **Takedown / corrections contact live** | ✅ ticked (interim, 2026-09-15) — a live human is now named behind the served `/corrections`+`/dispute` mechanism: Steven Vitali (`governance-and-code-of-conduct.md § Reviewer roles`). | Satisfied on an interim basis; revisit if the contact of record changes. |
| 4 | **ODbL 4.4(b) disposition (HG-02)** | ✅ ticked — **INTERIM engineering disposition** (GL-GATE-02, P23.3/HUMAN-H2; **pending counsel**). OSM-derived layer IS included in the export in its **separate ODbL compartment** with attribution + share-alike (re-verified: export `licenses: ["CC-BY-4.0","ODbL-1.0"]`, `exports/out/okc/` two-compartment layout). | Real counsel opinion (`D-LEGAL.1-1` OPEN) supersedes the interim disposition before real public exposure. |
| 5 | **Sensitivity tier + coordinate rules verified on every published page** | ✅ ticked (Part VIII, binding) — `policy.publication` runs over the export at build; re-verified by the export-mode e2e (dossier.spec.ts, a11y + render), coordinates jurisdiction-only, tier-0 only published. | — |
| 6 | **Officer-naming gate green on the data** | ✅ ticked (Part VIII, binding) — no un-permitted public-employee name published on the OKC pages; re-verified by the export-mode e2e (jurisdiction.spec.ts name-withholding) + hostile-reader review. | — |
| 7 | **robots + `/terms` served** | ✅ ticked — re-verified in the export web build (`web/dist/robots.txt`; `/terms` served by the read API). | — |
| 8 | **Licence statement per compartment on `/terms`** | ✅ ticked — CC-BY-4.0 graph + ODbL-1.0 OSM-derived layer (share-alike), SIG-LIC-004/010; two compartments physically separate in the export. | — |
| 9 | **Backups of PG + OCFL taken** | ✅ ticked (staging) — durable named PG volume; OCFL write-once. Pre-cutover snapshot procedure documented in `ops/README.md`. | Real snapshot taken by the operator at Go-public. |
| 10 | **Hostile-reader review clean** | ✅ ticked — `docs/build/reports/okc/hostile_reader_review.md`; the 299-vs-190 contradiction shown with both sources + dates (§3.1); re-verified this run (contradiction survives to the export-built dossier HTML). | — |

**Re-verification evidence (2026-09-10 re-run):** `sig-ops up/status/down` healthy/clean;
`run_okc.sh` complete (acceptance **2 pass / 11 blocked / 0 failed**, J-1 pass, Q-6 confirms
299-vs-190 CONTESTED/UNRESOLVED); `npm run test:e2e` **192 passed in BOTH fixtures and export
modes**; `check:perf` budgets hold; `SIG_REQUIRE_DB_TESTS=1 make check` **2767 passed, 2 skipped,
0 failed**; `make docs-check` exit 0; `check-build-memory.sh .` no violations.

**Go / no-go (unchanged):** Staging ✅ complete (local, HG-12). **Go-public ❌ NO** — reserved to
the human (GL-GATE-05 / GATE-G2 / P23.6); genuinely gated on a **real** HG-01 legal home + HG-11
governance. `D-P21.4-1/2/3` stay OPEN. No live fetch (HG-09 tokens + network absent); no public
cut-over; no `0.2.0` bump. → **RETURN PASS**.

---

## 2026-09-16 — GO-PUBLIC EXECUTED (operator decision; gates dispositioned, not silently dropped)

The operator decided **GO** and directed the remaining human gates be skipped or deferred
("no need for counsel opinion, legal home, human reviewers, outreach emails — let's just go
public"). Each gate is recorded below with its honest disposition — nothing here is marked
satisfied that was not.

### Gate dispositions

| Gate | Disposition | Record |
|---|---|---|
| HG-11 (two-reviewer concurrence) | **SKIPPED-BY-OPERATOR** — sole-maintainer posture; no second reviewer, no written concurrence; `concurrence.md` stays a template. The published surface makes no two-reviewer claim (reviewer state derives from recorded review data). | `D-P21.4-2`; LEDGER § GATE DECISIONS |
| HG-02 remainder (ODbL 4.4(b), officer-naming, publication tiers, Part VIII counsel opinions) | **DEFERRED** — published on the interim engineering dispositions (GL-GATE-02); the derived-facts publication question itself is resolved (counsel → ADR-086). | `D-LEGAL.1-1` |
| HG-04 (Stage-0 outreach: compact ×19, France operators, CCOPS operators) | **DEFERRED** — `not_contacted` stays the honest published posture; `declarationcamera_be` (eID) and `ccops_sf` (robots) keep their recorded refusals. | `D-P21.1-2`, `D-JURIS.2-2`, `D-CCOPS.1-2` |
| HG-08 (MapRoulette/OE), HG-10 (usability study) | **DEFERRED** — not read-surface prerequisites. | `D-P21.7-1`, `D-P21.7-2` |
| DNS / custom domain | **DEFERRED** — the public surface is the run.app URL + the `storage.googleapis.com` bucket endpoints; a custom domain can be added later (registrar action is the operator's). | `D-P21.4-3` note |

### Technical safeguards in force (unchanged by the skips)

- `sig_read_public` role serves tier-0 rows only (RLS); officer-naming gate defaults
  person-named claims to no-publish; coordinates stay jurisdiction-level.
- ODbL stays in its own `osm_physical` compartment; the `derived_facts` compartment (ADR-086)
  is dedicated and never merged into `sig_graph`/`osm_physical`/`portal`.
- Upstream expressive content is never re-hosted — exports carry SIG's claim rows only.
- `sig-restricted` and `sig-backups` buckets stay private (verified: anonymous 403).

### Execution + anonymous verification evidence (2026-09-16)

- Export rebuilt deterministically (`sig-exports build --jurisdiction okc` — release
  `sig-2026-08-20-95c7a19a`, byte-identical to the committed artifacts).
- Web built from export bytes (`SIG_DATA_SOURCE=export`): 50 pages; full web gate green —
  typecheck, unit, build, licence check, **192/192 e2e** (chromium + no-JS, axe WCAG 2.2 AA).
- `web/dist` → `gs://zeta-medley-508121-u7-sig-web` (website config: index.html / 404.html);
  `exports/out/okc` → `gs://zeta-medley-508121-u7-sig-public/okc`.
- Public Access Prevention cleared + `allUsers:roles/storage.objectViewer` granted on
  **sig-web + sig-public only** (the provisioning-script posture; restricted + backups
  untouched, PAP still enforced).
- `roles/run.invoker` granted to `allUsers` on `sig-api` (Cloud SQL attachment, Secret
  Manager binding, `SIG_API_ROLE=sig_read_public` unchanged).

| Endpoint | Result |
|---|---|
| `sig-web-873541617837.us-central1.run.app/` — **canonical site** | **200** (anonymous; zero `<script>` verified live) |
| `…/data-freshness/`, `…/dossier/oklahoma-city/`, `…/editorial-standards/`, `…/map/`, `…/watch/` | **200** each (correct titles); `/data-freshness` (no slash) → **301** to trailing slash |
| `…/nonexistent-page/` | **404** |
| `…/_astro/*.css` assets | **200** |
| `…-sig-public/okc/manifest.json` (bucket endpoint) | **200** |
| `…-sig-public/okc/web/dossiers.json` (bucket endpoint) | **200** |
| `…-sig-restricted/probe` | **403** (private — correct) |
| `…-sig-backups/probe` | **403** (private — correct) |
| `sig-api-e5ctyx36jq-uc.a.run.app/` | **200** (anonymous) |
| `…/terms` | **200** |
| `…/v1/search?q=flock` | **200** |
| `…/v1/dossier/okc` | **200** |
| `…/v1/contradiction` | **200** — 1 contradiction returned (299-vs-190, visible as required; ~105 s compute-on-read cold) |

**Serving fix (same day):** the raw bucket endpoints do NOT resolve directory
indexes — GCS `MainPageSuffix` only applies through a custom domain CNAME'd to
`c.storage.googleapis.com`, so `/data-freshness/` on `*.storage.googleapis.com`
404'd (and `/` returned the XML bucket listing). Since DNS is deferred, the site
is served by a new **`sig-web` Cloud Run service** (`nginx:1.27-alpine`,
gen2, `--allow-unauthenticated`, port 80) with the `sig-web` bucket mounted
read-only via Cloud Storage FUSE at `/usr/share/nginx/html` — nginx's native
`index index.html` resolves every directory URL correctly. The buckets stay
public-read for direct object access (export artifacts + site files); the
canonical human-facing site URL is the `sig-web` run.app URL.

### Go / no-go (2026-09-16)

**GO — executed.** Public surface live: static site (`sig-web` Cloud Run service)
+ published export compartment + read-only API, all anonymously reachable;
private compartments verified closed.
**Recorded debt:** second reviewer (HG-11), remaining counsel opinions (HG-02 remainder),
outreach (HG-04), contribution-back credentials (HG-08), usability study (HG-10) — all
OPEN/DEFERRED in `docs/tickets/DEFERRALS.md`, none claimed done.

---

## 2026-09-22 — P27.8 (LAUNCH.8): NATIONAL public cut-over — publication gate package (staged, operator tick pending)

The OKC go-public (2026-09-16 section above) took the first jurisdiction public. P27.8 stages the
**national** real-data surface (~1.06M claims / 210 sources incl. GB/AU/TH/NZ) over the same GCP
infra. The deterministic machinery is landed + proven; the **hosted cut-over itself is deferred**
(D-P27.8-1) on the national export prerequisite (D-P27.4-1 → the in-flight OSM land D-SOURCES.17-1).
The public go is the operator's tick against this package.

### Gate answers (operator, recorded verbatim in `docs/build/LEDGER.md` § GATE DECISIONS, 2026-09-22)

| Gate | Answer | Consequence for the national cut-over |
|---|---|---|
| **HG-01** (publication go / legal home) | **Carry forward, proceed** | Legal home stays **Steven Vitali, individual maintainer** (personal capacity, `governance-and-code-of-conduct.md § Legal home`, D-P21.4-1 DONE 2026-09-15). Authorized to build + deploy the national real-data surface to the public buckets (published compartment only). The hosted deploy/sync stays infra-gated on GCP ADC (HG-12 / D-ACCT.1-1). |
| **HG-11** (reviewer concurrence) | **Carry forward sole-maintainer posture** (D-P21.4-2) | Proceed on the recorded waiver; a second independent reviewer + written concurrence stays owed post-launch. The published surface makes **no two-reviewer claim** (`policy.officer._concurrence_ok` still denies person-named claims). |
| **HG-02** (counsel disposition) | **Carry forward interim engineering dispositions** (D-LEGAL.1-1) | Proceed on the interim publication-permitting dispositions + built safeguards; dated counsel opinions (ODbL 4.4(b), officer-naming, tiers/coordinates, Part VIII) stay owed post-launch. |

### What goes public (the published compartment only — §42 / Part VIII; ADR-096)

- **Public-read** (`gs://…-sig-web` static site + `gs://…-sig-public` export objects): the CC-BY-4.0
  SIG-original graph (`sig_graph`), the `web/*.json` render surfaces, and the export descriptors
  (`metadata`) — every compartment whose licence is **non-share-alike** and carries no export
  exclusion.
- **PRIVATE** (`gs://…-sig-restricted`, kept closed): the **ODbL-1.0** OSM-derived layer
  (`osm_physical`), the **CC-BY-SA-4.0** portal layer, and any UNDETERMINED / counsel-pending /
  non-redistributable byte. Proven by `ops/src/ops/publish.py:assert_public_clean` (a leak guard
  that fails loud on any share-alike/UNDETERMINED artifact in the public tree; `tests/ops/test_publish.py`).
  The national ODbL layer's public release is a dedicated, gated decision pending HG-02 counsel
  (ADR-096 / D-LEGAL.1-1) — a conservative tightening over §42.3 for the national surface.

### Part VIII safeguards in force (unchanged by the carry-forwards)

- `sig_read_public` role serves tier-0 rows only (RLS); coordinates jurisdiction-level; officer-naming
  gate defaults person-named claims to no-publish (two-reviewer concurrence absent → denied).
- The export fail-closed licence gate keeps UNDETERMINED / non-redistributable bytes out of every
  compartment; the compartment partition keeps ODbL/share-alike out of the public bucket.
- The public build reads the real national export or **fails loud** — never a fixtures fall-back
  (§38.1); the public site is never a demo wearing the national name.

### Go / no-go (2026-09-22)

**Staged, gated → RETURN PASS.** The deterministic producer + partition + leak guard + gate package
are landed and green. The hosted national cut-over is **NOT executed** — it is blocked on the national
export (`exports/out/national`, D-P27.4-1), which itself waits on the OSM land (D-SOURCES.17-1, LAND IN
PROGRESS). No live green fabricated, no deployed URL claimed. Re-run command + evidence: `D-P27.8-1`.
The operator ticks Go-public once the national export exists and the ADC-armed cut-over runs clean.

## 2026-09-23 — P27.10 (LAUNCH.10): custom-domain cut-over to surveillancegraph.org (HG-11 / Go-public — DNS action)

The final P27 launch row points the canonical public origin `https://surveillancegraph.org`
(+ `www`→apex) at the `sig-web` Cloud Run service with Google-managed TLS. Chosen mapping approach:
an **external HTTPS Application Load Balancer + serverless NEG** (ADR-098) — the Cloud Run domain
mapping is hard-blocked on interactive Search Console domain verification the cloud-platform ADC
cannot perform, whereas the LB needs no verification and reserves a real static IP.

**Applied for real (operator ADC, 2026-09-23, project `zeta-medley-508121-u7`, `us-central1`):**
global static IP `136.81.80.102`, serverless NEG → `sig-web`, backend service, Google-managed
multi-domain cert `sig-web-cert` (apex + www, PROVISIONING), HTTPS url map (apex→backend, www→apex
301), HTTP→HTTPS redirect, and the :443/:80 forwarding rules — all idempotent
(`ops/gcp/domain-mapping.sh`; re-run skips every create). The `:80` LB data path is live-verified
(`http://136.81.80.102` with Host `surveillancegraph.org` → **301 → https://surveillancegraph.org/**).

### HG-11 / Go-public gate action — the exact Squarespace DNS records the operator adds

The domain's registrar + DNS is Squarespace. These records are **PUBLIC config, never secrets**
(HG-09). Adding them is the **operator's live decision** (HG-11 / Go-public), never auto-ticked.

| Host | Type | Value | Note |
|---|---|---|---|
| `@` (apex) | `A` | `136.81.80.102` | the LB static IP; the apex cannot be a CNAME |
| `www` | `A` | `136.81.80.102` | same IP; the LB 301-redirects `www`→apex |

No verification `TXT` is needed (the LB path requires none). After the records resolve, Google-managed
TLS on `sig-web-cert` provisions to ACTIVE (allow up to ~60 min):

```
gcloud compute ssl-certificates describe sig-web-cert --global \
  --project zeta-medley-508121-u7 --format='value(managed.status)'   # expect ACTIVE
```

### Go / no-go (2026-09-23)

**Applied, DNS-gated → RETURN PASS (`D-P27.10-1`).** The mapping IaC is fully applied and the real
DNS records are produced from the realized IP. **Valid TLS + `probe-hosted` on the custom domain are
NOT yet green** — Google-managed TLS provisions only after the operator adds the DNS records at
Squarespace and they resolve; no live TLS/probe green is fabricated. The operator explicitly accepts
that the domain serves the current OKC demo until the national deploy (`D-P27.8-1`, gated on the OSM
land) completes. `astro` `site` is already `https://surveillancegraph.org` (P27.6), so no permalink
churns when the domain goes live. The `*.run.app` origin stays the documented fallback.

## 2026-09-24 — P30.3 (GO-LIVE.3): NATIONAL PUBLIC LAUNCH EXECUTED

The national real-data surface is live on `https://surveillancegraph.org` (and the `sig-web` run.app
fallback), built from the settled, materialized hosted spine. This supersedes the 2026-09-22 staged package
above (D-P27.8-1 DONE) and the P27.10 interim ("the domain serves the OKC demo").

### Gate answers (LEDGER § GATE DECISIONS)

| Gate | Answer | How it was honoured |
|---|---|---|
| **HG-11 / Go-public** (2026-09-23) | *"I give you the launch go approval now."* — with the binding safety framing (compartment separation; export from the settled materialized spine; probe confirms real data on both URLs; HALT on any failure) | all three conditions verified before/after the sync (below); nothing failed, so no halt |
| **Launch sequencing** (2026-09-24) | *"Fix resolution first, then launch."* | done by P30.2a/P30.2b; the launch publishes P30.2b's measured metric as the export computes it |
| **Share-alike layers** (2026-09-24) | *"counsel says it's okay and we can publish it all together."* | ADR-106: every layer on ONE public site (ODbL 4.4(b) produced work, "© OpenStreetMap contributors" wherever OSM points render); the downloads stay LICENCE-SEPARATED compartments; ODbL never merged into the CC-BY graph |
| HG-01 / HG-11 reviewer / HG-02 | carry-forward (2026-09-22) | sole-maintainer posture, interim engineering dispositions — unchanged |

### What went public

- **`gs://…-sig-web`** (site, public-read; mirrored exactly — the prior OKC demo pages and the non-public
  `/curate/` shell removed; the prior site is kept privately at `gs://…-sig-restricted/rollback/sig-web-pre-p30.3-2026-09-24/`).
- **`gs://…-sig-public`** (downloads, public-read): the national release `sig-2026-09-24-bd01cb94` —
  `manifest.json`, `LICENCES.json` (one entry per compartment: SPDX licence, URL, share-alike, attribution),
  `datapackage.json`, `provenance.ttl`, `exclusions.json` (0 refused), the SIG `web/*.json` surfaces (CC-BY-4.0)
  and **12 site compartments, each one licence**:

  | compartment | licence | camera-site rows |
  |---|---|---:|
  | `osm_physical` | ODbL-1.0 — © OpenStreetMap contributors | 154,705 |
  | `public_record` | LicenseRef-PublicRecord-FactualCompilation | 38,484 |
  | `operator_accepted` | LicenseRef-OperatorAccepted-DBRight | 21,682 |
  | `portal` | CC-BY-SA-4.0 (incl. CC0 feeds placed under their most-constraining target) | 10,052 |
  | `sig_graph` | CC-BY-4.0 (+ SIG framing tables) | 3,978 |
  | `dot511_ccbysa2` | CC-BY-SA-2.0 | 3,000 |
  | `ogl_uk3` | OGL-3.0 | 1,514 |
  | `ccby3` | CC-BY-3.0 | 861 |
  | `ogc_canada2` | OGL-Canada-2.0 | 160 |
  | `ottawa_odl2` | LicenseRef-Ottawa-ODL-2.0 | 146 |
  | `stalbert_odl1` | LicenseRef-StAlbert-ODL-1.0 | 80 |
  | `peel_odl1` | LicenseRef-Peel-ODL-1.0 | 37 |

  (Rows are observation-level slices per (source, rights); 230,330 observation-level records → 227,998
  resolved sites, PROVISIONAL — D-R6.1-EVAL.)
- **Kept PRIVATE** (`gs://…-sig-restricted`, anonymous GET → 403): `web/map.json`, the map render input
  labelled with all twelve licences (a mixed-licence file is never a public download); the full unpartitioned
  bundle under `exports/national/2026-09-24T154017Z/`. Nothing UNDETERMINED or excluded exists in the release
  (0 refused slices; effective UNDETERMINED 0 per the launch baseline).

### Safety proof (the binding framing)

- (a) **Compartment separation** — export-time `assert_separated` + fail-closed licence gate (it stopped the
  first hosted build on a real CC0+public-record mix; fixed by per-(source, rights) slicing, never merged);
  publish-time `assert_public_clean` (one known licence per artifact and per public compartment, no
  UNDETERMINED/excluded/mixed byte, no stray file) — green; independent re-check: 14 public compartments,
  one licence each; `web/map.json` absent from the public bucket (404).
- (b) **Settled, materialized spine** — claims 2,304,784 unchanged since P30.2b, camera-site run
  `camsite:13bedfe7…` (fh2bh), pg_stat upd/del 0; the export ran in one `REPEATABLE READ READ ONLY` snapshot.
- (c) **Real data renders on both URLs** — `sig-ops probe-hosted` green on `https://surveillancegraph.org` and
  `https://sig-web-e5ctyx36jq-uc.a.run.app`; a headless browser on each confirms the headline
  "227998 resolved sites (from 230330 observation-level records; dedup ratio 0.010)" with the PROVISIONAL
  disclosure, 225,105 points drawn on the map with "© OpenStreetMap contributors (ODbL)" in the attribution
  control, zero `<script>` on content pages, and no OKC-demo content; TLS valid (Google Trust Services WR3,
  apex + www, `sig-web-cert` ACTIVE).

### Part VIII review

Tier-0 only (234,699 of 234,699 public site rows tier 0, `full_precision` per §19.4 tier 0); no person or
plate fields (row keys are entity/source/rights/geometry only; labels are entity ids); the officer-naming gate
is unchanged (default no-publish); the export read the spine and wrote nothing.

### Counsel status

Share-alike clearance is **operator-reported** (2026-09-24); no dated written opinion is on file —
`D-P30.3-COUNSEL` stays OPEN (file it under `docs/governance/`). If the opinion narrows the clearance, an
`export_disposition = "excluded"` data row moves the affected compartments back to restricted at the next
deploy (ADR-106 revisit trigger).

### Go / no-go (2026-09-24)

**GO — executed.** Follow-ups (not launch-blocking): D-P30.3-1 (freshness dates not recorded on the hosted
spine), D-P30.3-2 (zoomable tiles / basemap / compression), D-P30.3-3 (presentation analytics for a
real-data build), D-P30.2-2 (sharing edges / accountability links), D-R6.1-EVAL (first-principles eval).
