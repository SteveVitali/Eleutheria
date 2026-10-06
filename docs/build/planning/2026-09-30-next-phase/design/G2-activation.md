# G2 — Round-10 activation plan (production safety, honesty, and the live return passes)

Row **G2** of `META_PLAN.md` (Stage P, owner D). Written 2026-09-30T17:51Z onward (`date -u`) in the planning worktree
`/Users/stevenvitali/Eleutheria-next-phase` (branch `claude/next-phase-planning`, HEAD `41ab9521`, chain tip `b051732c`).
`PD` = `docs/build/planning/2026-09-30-next-phase`.

> **Design only (P3/P10).** Nothing here was executed against production. GCP access was `describe`/`list` only (§11).
> Every command below is for a future Round-11 ticket or operator go. Each is tagged **[packet]** (copied from a committed
> `LIVE_RETURN_PASS.json`), **[runbook]** (copied from a committed runbook or script), **[G1]** (copied from
> `research/G1-ops.md`), or **[unverified]** (drafted here, never run). Durations and costs marked **[est]** are planning
> guesses; list prices are **inference**. Every public sentence in §6 is **agent-drafted** and must be confirmed verbatim
> by the operator before it ships (META_PLAN §2). The operator's personal address is referred to as **‹operator address›**
> (the value is recorded in META_PLAN §7.1; it is not repeated here, following G1's practice).

**Inputs read.** META_PLAN §3, the G2 row, §7/§7.1, §8.2, §11; `review/R10_PREVIEW.md` (C4, whole); `research/F1-owed-register.md`
(whole); `design/E2-governance-options.md` §0, E2-02, E2-12, A-1, §6–§9; `research/G1-ops.md` §0–§3.10, §5–§8;
`research/E3-human-work.md` §0, R9, R10, §9; `design/H1-integration.md` §1.1, §3, §5; `design/B3-ledger-redesign.md` §4 (grep);
`design/E4-rights-packets.md` §1, §4.2–§4.4, §7; `research/B1-date-drift.md` §5.4, §5.7, §5.8, §7, §9;
`docs/build/OPERATIONAL_READINESS.md` §(f)–(f3); the seven packets under `docs/build/reports/p32.18-*`…`p32.25-*`;
DEFERRALS rows D-R10-LIVE-1, D-R10-PUBLISH-1, D-R10-MEMORY-1, D-P32.16-1, D-P32.23a-1, D-P32.10a-1 (grep);
`docs/governance/intake-receiver-operating-packet.md` §1, §6–§8; `ops/config.toml [intake]`; ADR-124 L100–125;
`docs/build/reports/GCP_DEPLOYMENT.md` §9; code named inline. Findings: `findings/FINDINGS.csv` (S0 rows) and the incoming
CSVs (S0 rows plus the C4/F1/G1/B1/J1/C3/C2 rows cited).

**Outputs.** This file and `findings/incoming/G2.csv` (NEW-1…NEW-11).

---

## 0. Summary

**The critical path is operator gos and two calendar windows, not engineering.** Nine ordered steps; the engineering for
steps 4 and 6 can start on Round-11 day 1 and run in parallel with steps 0–3.

| step | what | hard preconditions | gate / approver | closes (owed rows · findings) |
|---|---|---|---|---|
| **0** | Production safety + honesty wave: G1 QA-1…QA-10, restore drill, one allow-listed publish path, web copy fixes + republish, attribution fix, API honesty code, sqitch hygiene | none (first wave, §7.1) | operator go **per action** (Track-0 style); republish = operator go (HG-11 semantics) | F-03, E1-02/E3 NEW-1, J1 NEW-2/3, F-06, G1 NEW-7, (C2 NEW-1, C3 NEW-2 pending confirmation); durable halves of F-01/F-02; D-P32.10a-1, D-P32.16a-1 |
| **1** | Round-10 schema (sqitch L44–52) + ADR-124 `allow` dispositions + Round-10 API image | 0 (drill, alerts, sqitch hygiene, restore point); **after** the 10-06…10-13 batch window and the D-P31.4-1 read-back | operator go + operator's allow list (ADR-124) | live legs of D-P31.1-1, D-P31.5-2; F1 NEW-4 row; C3 NEW-1; E2 H-5 |
| **2** | D-R10-LIVE-1: hosted audit → plan → reviewed bounded apply → +0 → rematerialize → freeze | 1; date constants fixed; execution host decided; restore point | operator go + recorded `--authority` scope | D-R10-LIVE-1 (production half; "final candidate" stays owed) |
| **3** | D-P32.23a-1: production candidate over the hosted snapshot, true dates; supersede `p-17b713…` (no re-sign) | 2; B1 constants; export-mode web build passes | operator go (no publication) | D-P32.23a-1; C4 NEW-11/26/31/32; B1 NEW-2 |
| **4** | C4 blockers: archive links, stand-in disclosure, `/v1` + `/intake` routing, deploy path that cannot wipe release trees, moderator 500 | engineering from day 1; verified on the step-3 candidate in staging | code review; the sig-web / LB changes need an operator go | C4 NEW-1…NEW-10, 12–19, 22–23, 29–32 |
| **5** | Dossier live captures D-P32.18/19/20/21-1, replacing stand-ins | HG-03 per target (E4 B1–B6, batched with I7); D-R10-SOURCES-1 prep | **HG-03** (operator) + Part VIII sign (B2) + operator go | D-P32.18-1…D-P32.21-1 → D-R10-SOURCES-1; C4 NEW-2 (on exposure) |
| **6** | Intake operation D-P32.16-1 (operator owner/moderator, disclosed single-maintainer SLAs, retention, log exclusions) | step-4 intake defects fixed; Q-27; least-privilege service identity | operator (Q-27) + exposure under **HG-11** in step 7 | D-P32.16-1; F-03 (fully) |
| **7** | D-R10-PUBLISH-1: production exposure of the REAL candidate + rollback rehearsal on the live surface | 3, 4 (always); 5 before any research-dossier route; 6 before `/intake/` | **HG-11**: a new candidate-specific readout, signed verbatim | D-R10-PUBLISH-1 |
| **8** | D-R10-MEMORY-1 split (B3 option C) | none on production; can run any time | operator decision at S5 | D-R10-MEMORY-1 (as split) |

**Ticket list (25; §5).** ACT-01 ops data protection · ACT-02 alerts that reach a human · ACT-03 cost guard · ACT-04
restore drill + restore-point procedure · ACT-05 one allow-listed publish path · ACT-06 web honesty wave + republish ·
ACT-07 attribution defect · ACT-08 API honesty code · ACT-09 sqitch hygiene + clone rehearsal of L44–52 · ACT-10 ADR-124
allow tooling + owed row · ACT-11 Round-10 schema + API activation · ACT-12 release-identity date truth + supersede
`p-17b713` · ACT-13 execution host for hosted return passes · ACT-14 D-R10-LIVE-1 live pass · ACT-15 D-P32.23a-1 production
candidate · ACT-16 release-archive correctness · ACT-17 serving topology · ACT-18 research-dossier disclosure · ACT-19
release-search states · ACT-20 intake defects · ACT-21 D-R10-SOURCES-1 prep · ACT-22 dossier live captures · ACT-23 intake
operation · ACT-24 D-R10-PUBLISH-1 exposure · ACT-25 memory split (merged into B3 M6).

**Claim rules (§6).** The site claims only what the step that just finished made true. Until step 7: no release archive,
no research dossier, no intake form is public, and the dispute route is email to ‹operator address› with single-maintainer
response times. "Reviewed" appears only where `review_status` says so; "captured/retrieved <date>" only for live captures
with true dates; "anonymous" never.

**Top risks (§8).** (1) The monthly camera-registry batch window (days 6–13, 03:07–~10:00Z; the 10-10 OSM replay inside
it) collides with any hosted write. (2) L44 rewrites `claim_evidence` under an exclusive lock (NEW-3); unmeasured.
(3) The API S0 (C3 NEW-1) cannot ship without the Round-10 API, which needs L44–52 plus the ADR-124 allows first (NEW-6).
(4) Alerts and a drilled restore are not in place before 10-01/10-10 unless the operator makes a Track-0 exception (NEW-7).
(5) A routine web redeploy erases release trees, and the live nginx cannot honour withdrawals (C4 NEW-10, NEW-2).
(6) Intake privacy promises conflict with G1's backup/log hardening and with the interim email channel (NEW-4, NEW-5).
(7) Cost ceilings Q-10/Q-23 are unanswered; autoresize makes the P32.22 disk ceilings meaningless (NEW-9).

---

## 1. Ground truth at planning time (2026-09-30T17:44–17:51Z, live-read unless marked)

| item | observed | consequence for activation |
|---|---|---|
| `sig-api` | revision `sig-api-00011-wic`, image `sig-api@sha256:40a47da8…`, AR tag `api-ba3dca617291` = commit `ba3dca61` (P31.8, 2026-09-25), **128 commits behind the chain tip**; default compute SA (project Editor); **no volume mounts** | the Round-10 API and its release-search route need a new image, a registry mount and a new CMD flag (C4 NEW-9) |
| `sig-web` | image `sig-web@sha256:d8244804…`, AR tag `5c0648812053` (built 2026-09-26T21:29Z). That commit **predates P32.13** (`4eafb9d9`); `git show 5c064881:ops/web/nginx.conf` has **0** `withdrawn_*` includes (code) | the live nginx cannot serve the withdrawal barrier; step 7 needs a sig-web roll (NEW-2) |
| Cloud SQL `sig-pg` | `db-custom-1-3840`, ZONAL, 15 GB SSD, autoresize on with **limit 0 (unlimited)**; backups on (05:00, 7 retained); **PITR on**; **deletion protection off**; no maintenance window | a restore path exists but is undrilled (G1-04); ceilings must be absolute (NEW-9) |
| backups | `1790785806842` AUTOMATED 16:30Z SUCCESSFUL; `1790785111976` ON_DEMAND 16:18Z SUCCESSFUL | the on-demand backup is the pattern for per-step restore points (§2 AR-2) |
| LB | one URL map `sig-web-urlmap`, default service `sig-web-backend`, **no path rules**; backend logging not enabled | `/v1/*` and `/intake/*` cannot reach `sig-api` / a receiver today (C4 NEW-9) |
| logging | `_Default` 30 days, `_Required` 400 days, **0 exclusions** on either sink | Cloud Run request logs (client IP/UA — inference) for any intake service would be retained 30 days (NEW-4) |
| Scheduler | 79 jobs; **33 never fired**: 32 first-fire between 10-01T06:00Z and 10-21T06:09Z, plus `camreg-peel-on` 10-29T12:00Z; camreg batch-01…08 fire **10-06…10-13 at 03:07–03:56Z** (monthly, `M 3 D * *`, D = 6…13); `batch-05` `35 3 10 * *` never attempted; `sam-gov` next 10-01T05:00Z | a recurring **monthly write window, days 6–13**, not only 10-10 (NEW-8) |
| Run jobs | no job named `*migrat*`, `*recover*`, `*audit*`, `*release*`, `*candidate*`, `*intake*` | every Round-10 return pass lacks an execution host (NEW-10) |
| hosted sqitch head | **not read** (no read-only path used here). B1 infers head = L43 `camera_site_human_decisions`; L44–52 undeployed (B1 §5.7; Q-B1-1) | step 1 must read it first (ACT-09) |
| return-pass packets | 7/7 `prepared_not_executed`, `approval_refs: []` (F1 §3); P32.25's `subject_publication_id` is the fixture `p-17b713…` | step 7's packet must be regenerated for the real candidate |

---

## 2. Activation rules (apply to every step; proposed text for the Round-11 OPERATING MODE and ticket template)

- **AR-1 One step, one go.** Each live stage names its operator go (or gate) and records it verbatim with `date -u`.
  Agent-drafted gate text is labelled and confirmed verbatim (E2-17 / Q-E2-18).
- **AR-2 Restore point before any hosted write** (DB or bucket). After ACT-04's drill has passed once:
  ```bash
  # [unverified] — flags per gcloud 583; confirm at execution
  T0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  gcloud sql backups create --instance sig-pg --project zeta-medley-508121-u7 --description "pre-<ACT-nn>-$T0"
  gcloud sql backups list --instance sig-pg --project zeta-medley-508121-u7 --limit 3   # SUCCESSFUL
  # read-only role over the proxy: record spine_watermark + per-table counts (G1 §3.1 list) + sqitch head in the run ledger
  ```
  **Rollback order of preference:** (1) forward fix — new rows, a `withdraw` disposition, a superseding record (the spine
  is append-only); (2) a PITR **clone** to `T0` for comparison (`gcloud sql instances clone sig-pg sig-pg-pit-$STAMP
  --point-in-time $T0` **[G1]**); (3) last resort, operator decision: re-point services to the clone (loses writes after
  `T0`, including scheduled ingests, which re-run +0). Never restore over `sig-pg` in place; never `UPDATE`/`DELETE`.
- **AR-3 Windows.** No hosted DB write, schema change or image roll of jobs during the **monthly batch window (day 6
  00:00Z → day 13 12:00Z)** or daily 03:00–06:30Z. The recommended activation slot is 14:00–20:00Z on a weekday (the
  operator's daytime; commits are −04:00), with the operator watching. Emergency takedowns are exempt.
- **AR-4 Clock guard.** Any read-back of a scheduled event checks `date -u` ≥ the fire time **and** the scheduler's
  `lastAttemptTime` (B1 NEW-4). Every record uses `date -u`; no hand-typed dates (B1).
- **AR-5 Verify at the live layer (P5, P11).** A step is `live-executed` only after its unauthenticated probe or hosted
  read passes: `uv run sig-ops probe-hosted` plus the step's own checks. `fixture-verified` / `staging-verified` never
  stand in. Each newly exposed route gets a presence target; each non-public route an absence target (G1 §3.2 item 5).
- **AR-6 Disclosure before exposure.** The copy that describes a surface's limits ships in the same publish as the surface.
- **AR-7 One publish path.** Every web/bucket change goes through ACT-05's allow-listed command; hand `rsync` is forbidden
  (G1 NEW-6, the F-02 cause).
- **AR-8 Least privilege for anything new.** New services and jobs (the receiver, the return-pass jobs) never run as the
  default compute SA (G1-01). Existing workloads migrate under G1's identity ticket.
- **AR-9 Ceilings are absolute.** Disk, spend and wall-clock ceilings are recorded as numbers (Q-10, Q-23), and a step
  stops at a ceiling without asking to continue.

---

## 3. Calendar (fixed dates, `date -u`; R0 = the first Round-11 ticket start, unknown today)

| when (UTC) | event | activation rule |
|---|---|---|
| 2026-10-01 05:00 / 06:00 | `sam_gov` fire (expect `quota_reached`, F1 NEW-1); `muckrock` first fire (F1 NEW-7) | watch only |
| 10-02 … 10-05 | first fires: eff-atlas, usaspending, eff-data-driven, osm-element-history, ted-eu | watch only |
| **10-06 03:07 → 10-13 ~10:00** | camreg batch-01…08 (monthly); **10-10 03:35 batch-05 OSM replay (D-P31.4-1)**, pinned image `feff986c` without re-sighting recording (G1 §3.3) | **hosted-write freeze** (AR-3); only QA metadata actions and web-bucket republishes allowed, outside 03:00–10:00Z |
| 10-10, after the execution ends (expected 15 min–5 h after 03:35Z; timeout 36 h) | D-P31.4-1 read-back (clock-guarded, AR-4; G1 §3.7 success criteria) | gate for step 1 |
| 10-14 … 10-21 | remaining first fires (06:09Z daily, light) | activation allowed 14:00–20:00Z |
| 10-29 12:00 | `camreg-peel-on` first fire | — |
| 11-06 → 11-13, then monthly | next batch window | freeze again; step 1's ingest-throughput check reads 11-06…11-13 runs |

**Earliest sequence [est]:** step 0 ops actions R0+0…2 d; drill R0+1…3 d; republish #1 ≈ R0+3…6 d; attribution
republish ≈ R0+8…14 d. Step 1 not before max(R0+~5 d, 10-14). Steps 2–3 ≈ 2–5 d after step 1 (48 h soak). Step 7 after
step 3 plus the step-4 tickets plus the HG-11 readout: ≈ 2–4 weeks after R0 for an archive-only exposure; later for
dossiers (HG-03 lead time) and intake (Q-27).

---

## 4. Steps (each: purpose · preconditions · commands · duration · cost · blast radius · rollback · verification · approval · tickets · public claim after)

### Step 0 — Production safety and honesty wave (first Round-11 wave, §7.1)

Operator decision (§7.1, 18:2xZ as recorded): the S0 hotfixes, QA-1…QA-10 and the `/task/new/` demo pages are "approved in
principle, to be specified as Round-11 tickets — not executed now". Sub-steps run in the order below.

**0a. Ops safety (ACT-01, ACT-02, ACT-03, ACT-04).**

| field | content |
|---|---|
| purpose | a restore path, deletion guard and alerting that reach a human **before** any Round-10 hosted write |
| preconditions | none. Q-10 number for QA-10; ‹operator address› for QA-3 (§7.1, approved for alerts) |
| commands | QA-1…QA-10 exactly as G1 §5 **[G1]** (flags to be verified at execution); drill per G1 §3.1 **[G1]**; restore-point procedure AR-2 **[unverified]**. Add (G1 §3.1): versioning + 30-day noncurrent lifecycle on `sig-web` and `sig-public` so a republish can be rolled back without a manual pre-copy. Add (NEW-9): a Cloud SQL `--storage-auto-increase-limit` at the Q-23 cap **[unverified flag]** |
| duration [est] | QA actions: minutes each (≈ 2–3 h operator in total, one sitting); drill ≲ 1.5 h (G1) |
| cost | QA ≲ $1/mo each; drill ≈ $0.15–0.40 one-off (G1, inference); versioning ≲ $0.30/mo |
| blast radius | QA-1/2/6: metadata; QA-5 rolls `sig-probe` only; **QA-7** can break the site if `sig-web` does not read through its own SA (G1: verify `/`, `/tiles/…` 206, `/map/` on both origins) |
| rollback | each reversible per G1 §5 (patch back; re-add `allUsers`; `gh workflow enable`; previous probe digest from the roll record) |
| verification | `gcloud sql instances describe` shows the flags; a synthetic `SIG-ALERT` reaches ‹operator address›; uptime checks green; `sig-probe` next sweep **succeeds** (red since 09-27, G1-02); drill record has RTO/RPO and exact count parity at `T` |
| approval | operator go per action (QA-1…QA-10) |
| closes | G1-02/03/04/05/10/14 (in part), A1 NEW-2/3, G1 NEW-2/4/5/14; F-01 durable half |

> **Timing conflict (NEW-7).** G1 placed QA-1/2/3/4/5 before 10-01 and QA-9 before 10-09. If R0 is after ~10-08, the
> first-fire wave and the 10-10 replay run with no human-routed alert and no drilled restore. **Operator decision:**
> either a Track-0 exception for QA-3/QA-4 (additive, alert-only) and QA-9 (creates and deletes a separate instance), or
> an explicit acceptance of that risk. Recommendation: the exception for QA-3/QA-4/QA-9 only.

**0b. One allow-listed publish path (ACT-05).** Must land before any republish.

| field | content |
|---|---|
| scope | G1 §3.2 items 1–6: internal routes not built by default; committed `ops/public_routes.toml`; content assertions (curate banner, loopback form actions, `demo_*` task slugs); `dist/.sig-release.json` (release id, commit, build time, tree digest; F-11); sync; post-sync absence probes. **Plus** (C4 NEW-10, DR-C4-07): the sync never deletes `r/`, `releases/<pub>/`, `entity/`, `conf/`; exactly one generator owns `releases/index.html`; the staged release tree is published by the same command, never by a second raw sync |
| commands | `sig-ops publish-web --apply` (name proposed by G1) **[unverified]** |
| verification | the regression tests in G1 §3.2 item 6 (sync refuses `curate/`, an unlisted top-level dir, a `demo_` page; a staged tree survives a web redeploy) |
| approval | code review; its first live use is 0c |

**0c. Web honesty republish #1 (ACT-06).** Copy and small code; data unchanged (release `sig-2026-09-27-ce480ab1`).

| field | content |
|---|---|
| scope | **H-1** `/editorial-standards/` → "not yet performed", and move the SIG-UI-042 gate so a truthful record does not fail the build (E2 NEW-1). **H-3** every `DisputeLink` footer and `/dispute/`: email to ‹operator address›, single-maintainer response times, no "one click", no "anonymous", no `/intake/new` promise, no requirement ids/"GATE-G3" in copy (C4 NEW-20), a do-not-send notice (NEW-5); the governance doc's `:30` "served `/corrections` and `/dispute` mechanisms" gets an appended correction. **H-4** `/methodology/` "frozen, human-verified holdout" (`web/src/lib/resolution-eval.ts:67`) → accurate provenance + the κ row. **H-6** publication-basis label. **`/task/new/`** strip `demo_*` in export mode (G1 NEW-7). **Release stamp** on every page: release id, as-of, "the API is live and may differ" (F-08/F-11, disclosure half only). **Interim sources-and-licences page** (E2-12 (d)) if ACT-07 is not ready. **Pending operator confirmation (S0s not in the §7.1 approved list):** `/visual-language/` "illustrative, synthetic example" label or removal from the allow-list (C2 NEW-1); a display alias for source ids that embed personal account handles (C3 NEW-2) |
| preconditions | 0b landed; export-mode build of the chain-tip web over the live 09-27 export **succeeds** — *unverified*: C4 NEW-26 shows the export build is strict about artifacts, so the 09-27 export may lack Round-10 inputs; if it fails, republish from a fresh export after 0d instead |
| commands | build → `publish-web --apply` **[unverified]**; pre-copy the live bucket to `rollback/sig-web-pre-<ACT-06>-$T0/` as P31.16 did (**[runbook]** pattern, `sig-restricted/rollback/`) unless versioning (0a) is on |
| duration [est] | engineering ≤ 2–3 d (E2 sizes: H-1 ≤ 1 d, H-3 ≤ 1 d, H-4 ≤ 0.5 d, H-6 ≤ 1 d); republish ≈ 1 h operator |
| cost | ≈ $0 (a few hundred object writes) |
| blast radius | the whole public site (copy on every page); no data change |
| rollback | restore the pre-copy / previous object versions via the same command; nginx unchanged |
| verification | route set equals the allow-list; absence probes (`/curate/`, a `demo_` page, `/releases/`, `/research-dossier/`, `/intake/`) 404 on the canonical origin, run.app and (until QA-7) the bucket URL; `grep` of the built tree finds no "one click", "human-verified", "Reviewer A"; axe 0 on changed pages; the `/dispute/` address is a working mailbox (operator sends a test) |
| approval | operator go for the republish (HG-11 semantics until G3 defines a standing go) + operator confirms every public sentence verbatim |
| closes | F-03 (false promise; the channel's operation is step 6/7), E1-02/E3 NEW-1, F-06, G1 NEW-7, E2 NEW-1, C4 NEW-20; C2 NEW-1 and C3 NEW-2 if confirmed |

**0d. Attribution defect (ACT-07).** E2-12, J1 NEW-2 (orchestrator ruling S0), J1 NEW-3.

| field | content |
|---|---|
| scope | the sink keys rights records per source (not per SPDX: `db/src/db/claim_sink.py:949-975` `_rights_id` caches by `spdx` and reuses the first row); an **additive** backfill for existing claims through the existing append-only override `rights_decision` (`db/deploy/rights_decisions.sql:6-26`: effective rights = latest decision matching `(source_id, prior_rights_id)`), never an `UPDATE`; exports, API and the map attribution use the effective per-source record; licence ids/URLs fixed in `datapackage.json`; a **publish-time gate** failing on any attribution-required row without attribution; `LICENCES.json` wording; the interim page from 0c becomes the permanent sources page |
| preconditions | 0a drill passed; AR-2 restore point; *unverified:* that every reader consults `rights_decision` for attribution text (the API checks the table exists, `api/src/api/store_pg.py:813`; exports not checked) |
| commands | the backfill tool is new **[unverified]**; re-export `ops/gcp/export.sh run` (09-27: 12 min, ≈ $0.10) **[runbook]**; republish #2 via ACT-05 |
| duration [est] | 2–4 d engineering (E2) + ≈ 2 h live (backfill, export, publish) |
| cost | ≈ $0.10–0.30 compute; object writes for 132 files |
| blast radius | attribution text in the API (live on write) and in the next export/site; 12 compartments |
| rollback | superseding `rights_decision` rows (forward); previous export and site objects via versioning |
| verification | `sqlite3 …/sites.sqlite`: 0 rows with `rights_attribution_required=1` and empty attribution (today 61,603 + 3,272 wrong); `GET /v1/search?q=austin` obligations name "EFF Atlas of Surveillance" with a terms URL; the map credits the drawn sources; the publish gate refuses a seeded unattributed row |
| approval | operator go (hosted write) + republish go |
| closes | J1 NEW-2/NEW-3, E1-12 (as a defect; COVERAGE stays PARTIAL until verified live); prerequisite for E2-09 outreach |

**0e. API honesty code (ACT-08)** — code in step 0, **deployed in step 1** (NEW-6): `/v1/dossier/{scope}` must not return
the first 25 eligible subjects for a non-entity scope (`api/src/api/store_pg.py:927-956`; return 404 or an honest
jurisdiction dossier) (C3 NEW-1, S0); `/terms` board/counsel wording (E2 H-5, `api/src/api/terms.py:32-33`); the
`https://sig.example/id/` placeholder IRIs (F3). **Operator option:** a hotfix image built from `ba3dca61` plus this patch
closes the S0 before step 1, at the cost of a production image that exists on no chain branch (provenance gap, and it
must be superseded by step 1). Recommendation: no hotfix unless step 1 slips past ~10-21; the endpoint is unlinked from the
site (C3), so exposure is limited to direct API users.

**0f. Sqitch hygiene + rehearsal (ACT-09).** D-P32.10a-1 (`verify/shared_temporal_contract.sql:30` asserts 27 facets; 28
exist) and D-P32.16a-1 (`revert/extensions.sql:7`), each as a new append-only change (repair shape = maintainer
decision); a CI job running full `sqitch deploy`/`verify`/`revert` on PG18; pin `sqitch/sqitch` by digest
(`ops/gcp/materialize.sh:106,112` use `:latest`). **Plus:** read the hosted head read-only (B1 Q-B1-1:
`SELECT change, change_id, planned_at, committed_at FROM sqitch.changes ORDER BY committed_at DESC LIMIT 5;`), and
**rehearse L44–52 on a PITR clone of `sig-pg`** (ACT-04's drill instance) to measure the `claim_evidence` rewrite, lock
time, index builds and temporary disk (NEW-3). Never edit plan lines ≤ L43; do not re-stamp L44–52 (B1 §5.7).

### Step 1 — Round-10 schema, ADR-124 allows, Round-10 API (ACT-10, ACT-11)

**What the Round-10 API changes publicly** (code diff `ba3dca61..b051732c -- api/src`: 10 files, +2,585/−109):

| change | public effect | handling |
|---|---|---|
| ADR-124 publication gate (`db/src/db/dispositions.py:76-124`) | organisations with `publication_review_required` and no current `allow` become `pending_publication_review` tombstones; `withdrawn`/`suppressed` deny | **allows first** (F1 NEW-4); anything not allowed is a disclosed change, not a regression |
| `spine_watermark` read (P32.4) | `/v1/contradiction` fast path (live 13.6 s today, F1 NEW-2) | measure; closes D-P31.1-1 live leg |
| P32.2 route generalisation, P32.3 role/count semantics | entity routes and some counts/labels change | before/after parity sample; changelog |
| `/v1/releases/{pub}/compartments/{comp}/search` | answers 503 `release_search_unconfigured` until a registry is mounted (C4 K21) | honest; not linked until step 7 |
| intake / curation routes | only in `serve-intake` / `serve-curation` (`api/src/api/cli.py:55,88`), **not** mounted by `serve` | none |

| field | content |
|---|---|
| preconditions | step 0a (alerts, drill) and 0f (sqitch hygiene, head read, clone rehearsal numbers accepted); D-P31.4-1 read-back done and the 10-06…10-13 window over (AR-3); ACT-10 landed: a DEFERRALS row for the ADR-124 allows, a `sig-ops disposition` verb (dry-run default, list input, `--authority`, `--decided-by`, INSERT-only via `db.dispositions.record_disposition`) — **today no operator path exists** (NEW-1) — and the operator's allow list, built from a read-only census of flagged organisations on the clone |
| commands | AR-2 restore point → pause the ingest triggers that overlap the slot (`gcloud scheduler jobs pause …`, **[runbook]** GCP_DEPLOYMENT §8 "Pause / disable") → `ops/gcp/materialize.sh --apply schema` (`sqitch deploy --verify` as the schema owner over the proxy) **[runbook]**, with `lock_timeout` set **[unverified]** → `sig-ops disposition record --allow --from <list> --dry-run`, then `--apply` **[unverified, new]** → build `sig-api:api-<sha12>`, `gcloud run services update sig-api --image …@sha256:<digest> --no-traffic --tag r10` → smoke the tag URL → `update-traffic --to-latest --remove-tags r10` **[runbook]** GCP_DEPLOYMENT §9 → resume triggers |
| duration [est] | schema deploy: **unmeasured**, dominated by the `claim_evidence` rewrite (NEW-3) — the clone rehearsal gives the number; allows: 1–2 h operator (depends on N); API roll ≈ 30 min; soak 48 h before step 2 |
| cost | ≈ $0 (clone rehearsal ≈ $0.15–0.40 in 0f) |
| blast radius | every API read (schema locks during deploy; new gate after roll); ingest writes during the deploy; the public site is unaffected (static) |
| rollback | API: roll back by digest to `sig-api@sha256:40a47da8…` (**never** a label-only update, ADR-107 §5) **[runbook]** — the old image ignores the additive tables (inference; confirm on the clone). Schema: **no hosted `sqitch revert`** (it would drop `publication_disposition` with the recorded allows, and revert is broken, D-P32.16a-1); fix forward with a new change. Allows: a superseding disposition row |
| verification | `sqitch status` = plan tip; `sqitch verify` exits 0 (needs 0f); `/health` 200 throughout (≤ 1 transient 503); `/v1/contradiction` < ~1 s warm, 8 concurrent (D-P31.1-1 rule); `/v1/search?q=Vigilant` shows the allowed label or a `pending_publication_review` tombstone as decided (D-P31.5-2); `/v1/dossier/fl` no longer returns the 25-subject placeholder; a 50-request before/after parity sample differs only in the documented ways; `n_tup_upd`/`n_tup_del` on claim tables unchanged by the deploy; next batch window (11-06…11-13) throughput vs the P31.4 bench (179,882 claims/min) — the statement-level watermark triggers (`db/deploy/shared_temporal_contract.sql:278-292`) should be cheap (inference) |
| approval | operator go (schema + roll) and the operator's own allow list (ADR-124: an operator act) |
| tickets | ACT-10, ACT-11 (+ ACT-08 code ships here) |
| closes | live legs of D-P31.1-1 and D-P31.5-2 (T4 annotations), F1 NEW-2/3/4, C3 NEW-1, E2 H-5; prerequisite for D-P32.3-1 (partner-name audit needs the P32.3 schema) |
| public claim after | API changelog entry (agent-drafted, §6); the site is unchanged |

### Step 2 — D-R10-LIVE-1: hosted audit → recovery → freeze (ACT-12, ACT-13, ACT-14)

| field | content |
|---|---|
| purpose | the production half of D-R10-LIVE-1: execute the P32.22 contract against the hosted spine and the mounted OCFL root |
| preconditions | step 1 + 48 h soak; ACT-12 (B1 §5.4 constants in `ops/src/ops/release_candidate.py:7,103,112,125`, dossier packet dates, `release_publish_verify.py:94-96` parametrised, a build-time future-date guard, DR-C4-15; the `p-17b713` supersession record); ACT-13 execution host: one-off Cloud Run jobs on a least-privilege SA with a **read-only** gcsfuse mount of `gs://…-sig-restricted/evidence/captures/` and a login in the `sig_recovery` role — or a recorded decision to run from the operator's workstation through the proxy (egress, broader credentials) (NEW-10); the reviewed scope written into the live packet **before** execution (packet `explicit_reservations`); AR-2 restore point; outside AR-3 windows; disk below the absolute cap (NEW-9) |
| commands **[packet]** | `uv run sig-ops evidence-audit --dsn $SIG_HOSTED_DSN --capture-dir <mounted OCFL root> --seed <recorded> --sample <recorded> --out <live-audit>/` (read-only transaction) → `uv run sig-ops recovery-plan --audit <live-audit>/audit_report.json --out <live-audit>/` → **operator reviews the plan and fixes the scope** → pilot: `recovery-apply … --apply --execution-id <recorded> --authority <operator-auth-ref> --capture-dir <OCFL root> --verify-rerun --rematerialize --out <live-apply>/` with `--max-actions` and a `--batches`/`--claims` selection inside the pilot ceiling → the same for each approved batch → `uv run sig-ops recovery-freeze --dsn $SIG_HOSTED_DSN --apply-report <live-apply>/APPLY_REPORT.json --plan … --audit … --out <live-apply>/`; then `implement-spec spec=docs/tickets/183_P32.22__bounded-recovery-and-activation.md live_verification=true` (OPERATIONAL_READINESS §(f3)) |
| ceilings **[packet]** | pilot: 40 claims, 30 min wall clock, 2 GiB bytes, 1 worker. Batch: ≤ 10,000 assertions, ≤ 250 MB distinct bytes, 1 worker. Storage: warn 0.7, disposition 0.85, ≥ 0.2 free per batch — **must be restated in GB** because autoresize is unlimited (NEW-9) |
| duration [est] | audit: unmeasured on ~2.4 M claims on 1 vCPU (0.5–3 h, off-peak, statement timeouts); plan review 1–4 h operator; pilot ≤ 30 min; batches ≤ 1 h each; rematerialize 2–30 min (09-27 took 2 min); freeze minutes. Total ≈ 1–3 working days |
| cost (inference) | job compute ≈ $0.19/h at 2 vCPU/8 GiB → ≈ $0.2–1; optional Cloud SQL tier bump ≈ $0.07/h per extra vCPU for the window; GCS reads in-region ≈ $0 |
| blast radius | hosted spine writes (receipts, bindings, repairs, dispositions — insert-only); **`--rematerialize` refreshes the materialized tables the live API reads** (`coverage_record`, `contradiction`, last built 09-27 — inference from G1 §3.6), so public API numbers move while the site stays on 09-27 |
| rollback | apply is exactly-once with receipts; a wrong action is corrected forward (a new claim, or a `withdraw` disposition); the snapshot is unpublished, so no public rollback is needed; PITR clone to `T0` for forensic comparison; re-pointing to a clone is the last resort (AR-2) |
| verification **[packet]** | population digest reconciles before any write; applied ⊆ plan, digest for digest; receipts unique; restart mid-apply reconciles `already_applied`; +0 re-run; no fetch path used; rematerialize +0 on re-run; snapshot `frozen_unpublished`; plus `/health` and probe-hosted green during and after |
| approval | operator go + the operator's `--authority` reference for the reviewed scope; no HG gate (nothing is published) |
| closes | D-R10-LIVE-1 **production recovery half** only. "Final post-evaluation candidate" stays owed to HUMAN-H4 → H5 → P32.23 (rows 184–187) |
| public claim after | none on the site. API changelog: "materialized coverage and contradiction views refreshed <date>" (agent-drafted) |

### Step 3 — D-P32.23a-1: the production release candidate (ACT-15)

| field | content |
|---|---|
| preconditions | step 2 frozen snapshot (`sig.repaired-snapshot/1`, `frozen_unpublished`); ACT-12 landed (true as-of = `date -u` at build; identity digests change, which is intended, B1 §5.4); `p-17b713…` superseded by an appended record (B1 option C; Q-12/Q-B1-3) — **not** re-signed; the export includes `web/leverage.json`, `web/tiles/*-sites.pmtiles`, `web/releases.json` (C4 NEW-26) |
| commands **[packet]** | `uv run sig-ops release-candidate --dsn $SIG_HOSTED_DSN --snapshot <live-apply>/REPAIRED_SNAPSHOT.json --plan <plan> --audit <audit> --apply-report <live-apply>/APPLY_REPORT.json --registry <release registry> --out <candidate>/`; then `implement-spec spec=docs/tickets/188_P32.23a__post-evaluation-release-candidate.md live_verification=true`. **Plus [unverified]:** export-mode web build over the candidate (`SIG_DATA_SOURCE=export SIG_EXPORT_DIR=<candidate>/candidate_export npx astro build`, the C4 command); the DR-C4-01 link crawl; island budgets and Lighthouse on real data (DR-C4-13, C4 NEW-25) |
| duration [est] | materialize 2–30 min; export ≈ 12 min (09-27, 4 vCPU/16 GiB); staging the release tree ≈ 2 min locally for ~237 k records (P32.13 measured ~98 s for 236,994 records → 475,112 files / 2.0 GB); web build + crawl + budgets ≈ 1 h; total ≈ half a day |
| cost (inference) | ≈ $0.10–0.30 compute; ~2 GB staged (≈ $0.04/mo); ≈ $2.4 in object writes per full upload of ~475 k objects (Class A ≈ $0.005/1k) — paid again in step 7 |
| blast radius | none public: the namespace is staged, `latest.json` must be byte-identical before and after |
| rollback | an appended supersession record; immutable namespaces are never deleted |
| verification **[packet]** | frame `consistent`, `materialization.plus_zero`, validation `complete`, `pointer_unchanged: true`, `published: false`; every manifest cites the same identity digest; `eval-confidence/1` shadow with `applied=[]`; disclosure "provisional/review-only"; **no date later than the build clock** anywhere in the tree |
| approval | operator go |
| closes | D-P32.23a-1; C4 NEW-11/26/31/32 (on the real candidate); B1 NEW-2 |
| public claim after | none |

### Step 4 — C4 blockers (ACT-16…ACT-20; engineering from Round-11 day 1)

Verified in staging on the step-3 candidate (P5 `staging-verified`), then live in step 7. Nothing here is exposed on its own.

| ticket | fixes (C4 ids; draft requirements) | live element | approval |
|---|---|---|---|
| ACT-16 release-archive correctness | relative-link depth (`exports/src/exports/release_pages.py:117,193`) + a link-resolution crawl gate (NEW-1, DR-C4-01); nav, dispute link and licence on every exports-rendered page (NEW-5, DR-C4-02); edge type configured/observed/declared (NEW-6, DR-C4-06); released dossiers linked, provisional posture, readable headings, licence (NEW-7); `/r/<pub>/` landing (NEW-29); zero-record landing explained (NEW-31) | none until step 7 | code review |
| ACT-17 serving topology | LB path rules `/v1/releases/*` → a serverless NEG for `sig-api`, `/intake/*` → the step-6 receiver (C4 option 3a; keeps one origin and a future Cloud Armor rule); `sig-api` read-only gcsfuse mount of the registry + `--release-registry` in the CMD (`ops/Dockerfile:112`) (NEW-9); absolute or same-origin links in API HTML; **sig-web roll** carrying the P32.13 nginx (withdrawal include, `/r/`, `/releases/`, `/entity/` locations) with 410 tombstone bodies and alias coverage (NEW-14, DR-C4-08, NEW-2 here); a documented way to make a new withdrawal take effect (the include is read at nginx start — inference); registry location is a G3 decision | URL-map change + two service rolls (operator go, in step 7 or a dark launch before it) | operator go |
| ACT-18 research-dossier disclosure | per-assertion acquisition label (live capture / committed transcription / stand-in) and an above-the-fold page disclosure (NEW-2, DR-C4-03); review label derived from `review_status` (NEW-3, DR-C4-04); true dates (NEW-32, B1 NEW-3); licence (NEW-22); print permalink and per-page as-of (NEW-23) | none; `/research-dossier/` stays off the allow-list until ACT-18 **and** ACT-22 land | code review |
| ACT-19 release-search states | empty-state wording (NEW-4, DR-C4-05); HTML error pages (NEW-13, DR-C4-10); scope counts include access-time denials (NEW-12, DR-C4-09); pager text (NEW-28) | none | code review |
| ACT-20 intake defects | reviewer detail 500 (NEW-8); gate requires `owner` and `staffed` (NEW-15, DR-C4-11); limiter keys on the edge-normalised client and refusals are not charged (NEW-16); the reporter sees outcome and approved response (NEW-17, DR-C4-12); proposal shape validated at proposal time (NEW-18); form fixes (NEW-19); demo tokens refused whenever a DSN is set (NEW-30) | none until step 6 | code review |

C4 NEW-21, NEW-24, NEW-25 (reflow, workspace links, map mobile) and NEW-27 (fixture marker) route to C6; NEW-25's real-data
budget measurement happens in step 3.

### Step 5 — Dossier live captures D-P32.18/19/20/21-1 (ACT-21, ACT-22)

| field | content |
|---|---|
| purpose | replace hand-authored stand-ins with actual captures (or honest refusals) for the OKC, Tulsa and San Diego dossiers and the two pilot families |
| preconditions | **HG-03 decisions** per E4 §1: B1 (rights basis for the 23 new targets; URL reconciliation first), B2 (Part VIII `clear` per family), B3 (SRC-027 workbook path → `rejected`, recommended), B4 (16 MB PAB PDF + 403 policy), B5 (4 targets on green sources: confirm), B6 (3 registry rows) — batched with I7's packets at S5 (Q-19). ACT-21: URL reconciliation (E4 NEW-7: 5 URLs differ from research, 7 have no research record), the pilot packet fix (E4 NEW-8, `tasks/src/tasks/acquisition_pilot.py:1336`), Part VIII screening drafts, the 3 registry rows added **gated**. ACT-12 dates fixed. Outside AR-3 windows |
| commands **[packet / §(f3)]** | record B1 per E4 §4.4 (`rights = {document_bytes, fact_extraction, derived_publication}` with `decision_ref`), then `uv run sig-tasks acquisition check`, `uv run sig-tasks acquisition pilot-check` (0 violations), `uv run sig-connectors gate --source dossier_okc` (and `_tulsa`, `_san_diego`) → LOADABLE; then `implement-spec spec=docs/tickets/179_P32.18__oklahoma-city-evidence-dossier.md live_verification=true`, likewise `180_P32.19…`, `181_P32.20…`, `182_P32.21…`. OKC also applies its seed-correction packet to the hosted spine (`sig-ops seed-correct`, append-only; arguments **[unverified]**) — a hosted write, so AR-2 applies |
| bounds **[packet]** | 6 OKC, 6 Tulsa, 9 San Diego targets; `html_text`/`pdf_text` only; page/byte caps as the replay path; pilot ≤ 10 documents per family, 2 retries per target, 0 new protocol families; SRC-027 metadata-only |
| duration [est] | HG-03: E3 R9 6.5–26 h operator for the rights rows plus ≈ 0.5–1.5 h per candidate target; each live pass ≈ 1–3 h; rebuild dossiers ≈ 1 h |
| cost | ≈ $0 (tens of documents) |
| blast radius | new evidence rows and captures (insert-only); OKC seed corrections (append-only); no publication |
| rollback | a wrong capture → a `withdraw` disposition on the artifact (ADR-124); rights reversal → the source flips back to refused (fail-closed) |
| verification | each target has a capture digest + locator + true retrieval date, or an honest `link_rotted`/403/`too_large` record; dossiers rebuilt; the acquisition label on each assertion is correct; `review_status` stays `not_run` (H4 deferred) |
| approval | **HG-03** per target (operator), Part VIII sign-off (operator, B2), operator go for each live pass |
| closes | D-P32.18-1, D-P32.19-1, D-P32.20-1, D-P32.21-1 → D-R10-SOURCES-1; B1 NEW-3 for re-built packets; C4 NEW-2 for captured assertions |
| public claim after | none until step 7 |

### Step 6 — Intake operation D-P32.16-1 (ACT-23)

| field | content |
|---|---|
| purpose | make the P32.16 receiver operable with the operator as owner and moderator, honestly disclosed |
| preconditions | ACT-20 landed; **Q-27** answered (the receiver opens; **backup moderator: none** → the single-maintainer disclosure, E3 R10, E2 A-1); the operating-packet §1 rows green: owner named in `ops/config.toml [intake]`, `staffed=true` meaning "the published single-maintainer SLAs" (a reviewed change), retention ratified (30 days after disposition, 90-day ceiling), secrets in Secret Manager, receiver and reviewer DB logins granted, infra exclusions enumerated (§7). **The infra exclusions must be designed with G1's hardening (NEW-4):** a `_Default`-sink exclusion (or a short-retention bucket) for the receiver's Cloud Run request logs; LB logging stays off; the monthly logical export (G1 §3.1) excludes the `intake` schema or the retention text discloses it; automated backups/PITR (≤ 7 days) disclosed. A dedicated least-privilege SA (AR-8). An **email handling rule** for the interim channel (NEW-5) |
| commands | `sig-api serve-intake --dsn <receiver login DSN>` as a new Cloud Run service `sig-intake` with `SIG_INTAKE_ENABLED=1`, `SIG_INTAKE_OPERATIONAL=1`, `SIG_INTAKE_FORM_SECRET`, `SIG_INTAKE_ABUSE_SECRET` from Secret Manager (**[runbook]** shape from C4 §1 rows 9–10; service definition **[unverified]**); `GRANT sig_intake_receiver TO <login>`, `GRANT sig_intake_reviewer TO <login>` (packet §7); moderation only on loopback: `SIG_CURATION_ENABLED=1 uv run sig-api serve-curation --intake-dsn <proxy DSN>` on the operator's machine (packet §6; C4 row 12) with demo tokens refused (ACT-20); purge on a schedule: `sig-api intake-purge --dry-run`, then `--apply` (packet §8). **Dark launch:** deploy with `operational=false` first (503 state, "ready" per C4), flip only in step 7 |
| duration [est] | setup 4–8 h + 2–4 h/week at low volume (E3 R10) |
| cost (inference) | `sig-intake` at min 0 ≈ $0–2/mo; min 1 ≈ $7–10/mo; 2 secrets ≈ $0.12/mo |
| blast radius | a public write endpoint that stores reporter text; abuse and spam; Part VIII content arriving (the screen refuses plates before storage, C4) |
| rollback | `operational=false` (or unset `SIG_INTAKE_OPERATIONAL`) → `receiver_not_operating` on the next revision; remove the LB path rule; stored reports stay under the retention schedule |
| verification | an unauthenticated probe: the form accepts, the receipt is idempotent, a report reaches the loopback queue, moderation transitions fail closed, apply is exactly-once (D-P32.16-1 verify rule); refusals render HTML; `/intake/new` 503 before the flip; no IP/UA in any intake table |
| approval | operator (owner, Q-27, retention, secrets, logins); public exposure under **HG-11** in step 7 (D-R10-PUBLISH-1 covers "receiver public exposure") |
| closes | D-P32.16-1; F-03 fully (with step 7); C4 NEW-15/16/30 in production |

### Step 7 — D-R10-PUBLISH-1: production exposure of the real candidate (ACT-24)

| field | content |
|---|---|
| preconditions | step 3 candidate; ACT-05, ACT-16, ACT-17, ACT-19 live-ready; **a new candidate-specific HG-11 readout** naming the new publication id, true dates, approved artifact digests, the disclosures in §6 and the route list — agent-drafted, confirmed verbatim (GATE-G3's signature on `p-17b713` is superseded, E2-17 / Q-E2-18; B1 NEW-2); the P32.25 packet regenerated for the new publication id; research-dossier routes **only** if ACT-18 + ACT-22 are done; `/intake/` **only** if step 6 is done; AR-2 restore point (bucket versioning on) |
| commands **[packet]**, with the ACT-05 path replacing the raw sync | `sig-ops release-publish --candidate <dir> --out <report>` (activate over the hosted registry) → publish the staged tree + `conf/withdrawn_routes.conf` through `publish-web --apply` (not "sync `staged/` → the web bucket") → roll `sig-web` (ACT-17 nginx) and `sig-api` (registry mount) by digest → add the LB path rules → probe: `GET /releases/`, `/releases/<pub>/`, every manifest route, sha256 vs the approved digests; `/intake/new` 503 (or the operating form if step 6 is in scope) → `implement-spec spec=docs/tickets/191_P32.25__accepted-release-public-verification.md live_verification=true` |
| rollback rehearsal on the live surface **[packet]** | (i) no prior pointer: `exports.release.clear_latest_pointer(<registry>)` → `/releases/` shows no latest, `r/<pub>` stays reachable; (ii) post-publish withholding: `record_withdrawal(<registry>, [<disposition>])` on one low-stakes record → 410 with the tombstone body on every alias after the sig-web roll; (iii) prior-release pointer rollback — **not rehearsable on the first real release** (no prior activated release); rehearse on the second release, or seed a same-session scratch release in a separate namespace (**[unverified]**). Each rehearsal is reversed and receipted |
| duration [est] | readout reading 1–2 h operator; upload ≈ 1–2 h for ~475 k objects **[est]**; rolls + LB ≈ 1 h; probes + rehearsal ≈ 1–2 h |
| cost (inference) | ≈ $2.4 object writes; ≈ $0.04/mo storage; LB path rules and serverless NEGs ≈ $0 extra; optional Cloud Armor ≈ +$5–6/mo |
| blast radius | the public origin (new routes, nginx config, LB routing); citable URLs become permanent commitments |
| rollback | pointer rollback / `clear_latest_pointer`; withdrawal; previous object versions; previous `sig-web`/`sig-api` digests; remove LB rules. Immutable namespaces are withdrawn, never deleted |
| verification | digest match on every manifest route; the ACT-16 crawl passes live (no non-200 same-origin link except declared 410s); absence probes for non-allow-listed routes; presence probes added to `cadence.toml`; `latest.json` as intended; `/v1/releases/…/search` 200 on the canonical origin; +0 re-run of the publish verification |
| approval | **HG-11** (operator signature on the candidate-specific readout) + operator go |
| closes | D-R10-PUBLISH-1 (the release exposure half; the receiver half with step 6) |

### Step 8 — D-R10-MEMORY-1 (ACT-25 → merged into B3 M6)

No production blast radius. Per B3 §4 option (C): repair and **enforce** obligation events in CI (a DEFERRALS lead-token
change needs a matching transition event); keep the current projection as a CI-verified orientation view; keep the
closeout journal in shadow as `later-phase(<trigger>)`; a new ADR supersedes ADR-126/127's cutover statements. Verify
`python3 docs/build/tools/obligation_events.py check` and `current_projection.py verify` **[§(f3)]**. Approval: the
operator at S5 (the row is operator-owned). It can land in the Stage-B seed or as an early M-ticket; it gates nothing in
steps 0–7, but correct dates (B1) should land before step 2 so live-pass records are true.

---

## 5. Round-11 tickets (provisional keys; S2/T3 assign manifest rows 201+ and merge overlaps, P9)

| key | title | scope (one line) | wave/step | live stage | gate | depends | overlap |
|---|---|---|---|---|---|---|---|
| ACT-01 | Ops data protection | QA-1, QA-2, QA-6, QA-7 + versioning on `sig-web`/`sig-public` + Cloud SQL autoresize cap | 0a | yes | op go ×n | — | G1 |
| ACT-02 | Alerts that reach a human | QA-3 (to ‹operator address›), QA-4, QA-5 (+ absence targets), QA-8 | 0a | yes | op go ×n | — | G1 |
| ACT-03 | Cost guard | QA-10 budget at Q-10 + billing export; record Q-23 cap | 0a | yes | op go; Q-10 | — | G1 |
| ACT-04 | Restore drill + restore-point procedure | QA-9 PITR clone drill, `backup-drill --cloudsql-clone`, AR-2 procedure, relabel 09-15 dumps | 0a | yes | op go | ACT-01 | G1 |
| ACT-05 | One allow-listed publish path | G1 §3.2 fix + no-delete of release trees + one owner of `/releases/index.html` | 0b | first use in ACT-06 | review | — | G1-06, C4 NEW-10 |
| ACT-06 | Web honesty wave + republish #1 | H-1, H-3 (‹operator address›), H-4, H-6, `demo_*` strip, release stamp, interim sources page; C2 NEW-1/C3 NEW-2 if confirmed | 0c | republish | op go (HG-11 sem.) + verbatim copy | ACT-05 | E2 H-1/3/4/6 |
| ACT-07 | Attribution defect | per-source rights keying, additive `rights_decision` backfill, exports/API/map, publish-time gate, republish #2 | 0d | hosted write + republish | op go ×2 | ACT-04, ACT-05 | E2-12, J3 |
| ACT-08 | API honesty code | `/v1/dossier/{scope}`, `/terms`, placeholder IRIs | 0e (deploys in 1) | via ACT-11 | — | — | E2 H-5, F3 |
| ACT-09 | Sqitch hygiene + L44–52 clone rehearsal | D-P32.10a-1, D-P32.16a-1, full verify/revert CI, pinned image, hosted head read, rehearsal numbers | 0f | read-only + clone | op go (clone) | ACT-04 | F1 2b |
| ACT-10 | ADR-124 allows: row + tool + census | DEFERRALS row, `sig-ops disposition` verb, flagged-org census, operator list | 1 | read-only census | op (list) | ACT-09 | F1 NEW-4 |
| ACT-11 | Round-10 schema + API activation | restore point, L44–52, allows, API roll by digest, parity + perf checks | 1 | yes | op go | ACT-02/04/08/09/10; after 10-13 | F1 4a |
| ACT-12 | Release-identity date truth | B1 §5.4 constants, packet dates, parametrised verify, future-date build guard, `p-17b713` supersession | 2 | — | Q-12 | — | B1 §5.8 |
| ACT-13 | Execution host for hosted return passes | one-off Cloud Run jobs, least-privilege SA, read-only OCFL mount, `sig_recovery` login | 2 | infra create | op go | G1 identity design | G1-01 |
| ACT-14 | D-R10-LIVE-1 live pass (row 183) | audit → plan → reviewed bounded apply → +0 → rematerialize → freeze | 2 | yes | op go + authority | ACT-11/12/13 | F1 4b |
| ACT-15 | D-P32.23a-1 production candidate (row 188) | candidate over the hosted snapshot + export-mode web build + crawl + real-data budgets | 3 | staged only | op go | ACT-14 | F1 4c |
| ACT-16 | Release-archive correctness | C4 NEW-1/5/6/7/29/31 | 4 | via ACT-24 | review | — | C6 |
| ACT-17 | Serving topology | LB path rules, `sig-api` registry mount + CMD, sig-web P32.13 nginx roll, 410 bodies, aliases | 4 | infra (dark or in 7) | op go | ACT-05 | C4 NEW-9/14, G3 |
| ACT-18 | Research-dossier disclosure | acquisition labels, review labels, true dates, licence, print permalink | 4 | via ACT-24 | review | ACT-12 | C4 NEW-2/3/22/23/32 |
| ACT-19 | Release-search states | empty state, HTML errors, scope counts, pager | 4 | via ACT-24 | review | — | C4 NEW-4/12/13/28 |
| ACT-20 | Intake defects | C4 NEW-8/15/16/17/18/19/30 | 4 | via ACT-23 | review | — | — |
| ACT-21 | D-R10-SOURCES-1 prep | URL reconciliation, pilot packet fix, Part VIII drafts, 3 gated registry rows | 5 | — | — | — | F1 2d, E4 |
| ACT-22 | Dossier live captures (rows 179–182) | four live return passes after HG-03 | 5 | yes | **HG-03** + B2 + op go | ACT-12/18/21 | F1 4d |
| ACT-23 | Intake operation D-P32.16-1 | owner, SLAs, retention, secrets, logins, log exclusions, `sig-intake` service (dark), email rule | 6 | yes | op (Q-27) | ACT-17/20 | E3 R10 |
| ACT-24 | D-R10-PUBLISH-1 exposure (row 191) | HG-11 readout, publish via ACT-05, rolls, LB, probes, live rollback rehearsal, allow-list expansion | 7 | yes | **HG-11** | ACT-15/16/17/19 (+18/22, +23) | F1 4e |
| ACT-25 | D-R10-MEMORY-1 split | B3 option (C) | 8 | none | op at S5 | — | **merged-into B3 M6** |

---

## 6. What the public site may claim at each stage

All sentences are **agent-drafted** and need verbatim operator confirmation. "Must not" lists apply from that stage on.

| stage (after) | may claim | must disclose (agent-drafted wording) | must not claim |
|---|---|---|---|
| **today** | — (false claims live: F-03, E1-02, J1 NEW-2, C3 NEW-1, F-06, G1 NEW-7, C2 NEW-1, C3 NEW-2) | — | — |
| **0c** honesty republish | the standards as standards; email corrections | footer: "Found an error? Email ‹operator address›." `/dispute/`: "Our online correction form is not operating yet. Email ‹operator address›. One person reads this inbox; we aim to reply within 72 hours for privacy or safety issues, 7 days for legal or copyright matters and 14 days for factual corrections, and replies may pause during absences. Please don't include licence plate numbers or personal details about other people; if we need more, we'll ask." Stamp: "This site shows release sig-2026-09-27-ce480ab1, data as of 2026-09-27. The public API is updated continuously and may show newer records." `/editorial-standards/`: the E2-02 (d) wording. Interim sources page: "Per-record source credit is being repaired; until then, this page lists every source, its licence and its terms." | "one click", "no account required" as a promise of a channel, "anonymous", a hostile-reader review, "human-verified holdout", any `/intake/` path |
| **0d** attribution | "every record names its source and licence" — only after the publish gate passes on the live export | a dated correction note on the sources page that earlier downloads credited some rows to the wrong source (E2-09 outreach follows) | per-row attribution before the gate passes |
| **1** API | the API's contradiction and entity routes as served | API changelog: "Organisations awaiting a publication decision are shown as 'pending publication review'." | that a tombstoned organisation was reviewed and rejected |
| **2–3** | nothing new on the site | API changelog: "Coverage and contradiction views recomputed on <date>; figures may differ from the site, which shows the 2026-09-27 release." | "evidence repaired", "verified", "final candidate" |
| **5** captures | inside a dossier: "captured <true date>" for captured documents only | per assertion: "Stand-in: this passage comes from a test document, not a capture of the real source" wherever a stand-in remains; "Not yet independently reviewed" while `review_status=not_run` | "Reviewed research dossier"; any retrieval date for a document never retrieved |
| **6** intake (dark) | nothing new | — | an operating form |
| **7** exposure | "Release <pub> is immutable and citable at /r/<pub>/…"; archive browse; release search; (if 5) research dossiers; (if 6) the form | release landing: "Provisional release. Matching of records to the same device has not been independently evaluated (D-R6.1-EVAL); automatic matching remains provisional. Some areas were not researched; those are marked." Intake (if open): "We do not ask who you are, and the report system does not store network addresses. Our hosting provider's request logs keep network addresses for up to ‹N› days. Deleted reports can remain in encrypted database backups for up to 7 days. One person moderates reports." | "anonymous"; any SLA shorter than the single maintainer can keep; "complete" for a release with 0 compartments |

---

## 7. Which S0/S1 findings each step closes

| finding | sev | closed by |
|---|---|---|
| F-01 backups | S0 (remediated) | durable: ACT-01 (QA-1), ACT-04 (drill) |
| F-02 `/curate/` | S0 (remediated) | durable: ACT-05, ACT-01 (QA-7) |
| F-03 dispute channel | S0 | false promise: ACT-06; a working channel: ACT-23 + ACT-24 |
| E1 NEW-1 / E3 NEW-1 hostile-reader fixture | S0 | ACT-06 (H-1) + E2 NEW-1 gate move |
| J1 NEW-2 misattribution (ruled S0), J1 NEW-3 | S0 / S2 | ACT-07 (interim page in ACT-06) |
| C3 NEW-1 API placeholder dossier | S0 | ACT-08 code → ACT-11 deploy (or the hotfix option, §4 0e) |
| C3 NEW-2 personal handles in source ids | S0 | ACT-06 if confirmed (display alias); a durable id policy is outside G2 |
| C2 NEW-1 `/visual-language/` fixture facts | S0 | ACT-06 if confirmed |
| F-06 "human-verified" | S1 | ACT-06 (H-4) |
| G1 NEW-7 demo task pages | S2 | ACT-06 + ACT-05 assertion |
| F1 NEW-2 / NEW-3 live legs | S2 | ACT-11 |
| F1 NEW-4 ADR-124 allows | S2 | ACT-10 + ACT-11 |
| C4 NEW-1, 5, 6, 7 | S1 | ACT-16 → live in ACT-24 |
| C4 NEW-2 (S0 on exposure), NEW-3 | S1 | ACT-18 + ACT-22; exposure only in ACT-24 |
| C4 NEW-4 | S1 | ACT-19 |
| C4 NEW-8 | S1 | ACT-20 |
| C4 NEW-9, NEW-10 | S1 | ACT-17 + ACT-05 |
| C4 NEW-11 (S0 on exposure) | S1 | ACT-12 (supersede) + ACT-15 (real candidate) |
| B1 NEW-2, NEW-3 | S1 | ACT-12 (+ ACT-18, ACT-22) |
| E2 H-5 (API terms), H-6 (basis label) | S1 | ACT-08/11; ACT-06 |

Out of G2's scope (routed elsewhere): E2 H-7 crawler text and H-9 naming gate (E stream); F-44/C3 geography collisions (C6/I);
F-08 cadence and F-11 provenance model (G3); G1-01 identities (G1 ticket; AR-8 makes it a precondition only for new
services and jobs).

---

## 8. Risks and mitigations

| # | risk | L×I | mitigation | owner/step |
|---|---|---|---|---|
| R1 | A hosted write, schema change or job roll during the monthly batch window (days 6–13, incl. the 10-10 replay) confounds D-P31.4-1 (`n_tup_upd/del`, run time) and competes for 1 vCPU / 3.75 GB | 4×3 | AR-3 freeze; step 1 not before 10-14; D-P31.4-1 read-back clock-guarded (AR-4); a deny-maintenance period 10-06…10-13 with QA-2 | ACT-01, ACT-11 |
| R2 | L44 adds `bound_at … DEFAULT clock_timestamp()` (volatile) to `claim_evidence`, forcing a full rewrite under ACCESS EXCLUSIVE lock; L46 builds indexes non-concurrently; API reads and ingest block, temporary disk ≈ the table size (NEW-3) | 3×3 | rehearse on a PITR clone (ACT-09) for time and disk; set `lock_timeout`; pause overlapping triggers; weekday slot; if the rewrite is too long, the remedy is a maintainer decision: editing L44's landed deploy script is an in-place edit the convention discourages and is thinkable only if no persistent database holds L44 (B1 Q-B1-4; hosted very likely does not, B1 §5.7) | ACT-09, ACT-11 |
| R3 | Cloud SQL disk: 15 GB provisioned, 6.42 GB used (09-30, G1); autoresize unlimited and one-way; growth from the first-fire wave (≲ 1 GB OSM, G1), L44 rewrite, Stream I ingests, recovery rows | 3×2 | absolute cap tied to Q-23 (autoresize limit); P32.22 ceilings restated in GB (NEW-9); a disk read before and after every step; Stream I ingests scheduled outside steps 1–3 | ACT-01/03, I8 |
| R4 | Cost: ≈ $90–100/mo estimated (G1), Q-10/Q-23 unanswered; one-off activation spend ≈ $5–10 list (inference, excluding a tier bump); monthly delta ≈ +$1–15; denial-of-wallet on public buckets | 3×2 | QA-10 before any step-1 spend; a stated ceiling per step (AR-9); versioned buckets' noncurrent lifecycle; Cloud Armor only if Q-10 allows | ACT-03 |
| R5 | First-fire wave (32 triggers 10-01…10-21, 12 never-executed jobs, 2 last failed) runs unattended if alerts are not live (NEW-7) | 3×3 | Track-0 exception for QA-3/4 (recommended) or accepted risk; watch plan G1 §3.7; don't stack activation on first-fire days before 06:30Z | operator, ACT-02 |
| R6 | The API S0 stays live until step 1 (NEW-6) | 3×2 | code in step 0; step 1 early (≥ 10-14); hotfix image only if step 1 slips past ~10-21 | ACT-08/11 |
| R7 | ADR-124 silently tombstones public vendor names if allows are not recorded first (F1 NEW-4); no tool exists to record them (NEW-1) | 3×3 | ACT-10 before ACT-11; before/after `/v1/search` parity on named partners | ACT-10 |
| R8 | A routine web redeploy erases `/r/`, `/entity/`, `conf/` (C4 NEW-10); the live nginx ignores the deny map (NEW-2) → withdrawn routes served 200 | 3×4 | ACT-05 before any tree is published; ACT-17 sig-web roll in the same change as the first tree; absence probe for a withdrawn route | ACT-05/17 |
| R9 | Stand-in or fixture content exposed as fact (C4 NEW-2/NEW-11 become S0) | 2×5 | allow-list excludes `/research-dossier/` until ACT-18 + ACT-22; the real candidate replaces `p-17b713`; the future-date build guard | ACT-05/12/18 |
| R10 | Intake privacy promises contradicted by infra: request logs with IP/UA (inference), G1's 90-day `_Default` proposal, monthly logical export ×3, backups ≤ 7 days (NEW-4) | 3×3 | a joint design in ACT-23 (log exclusion, intake schema excluded from logical exports, disclosed backup window) before the flip | ACT-23, G1 |
| R11 | Publishing the operator's personal address: spam, harassment, no succession, and personal data (incl. plates) arriving in an inbox with no retention or redaction (NEW-5; Q-29 accepted risk) | 3×3 | the do-not-send line; an inbox filter/label; a written handling rule (delete after resolution, never forward plate data, 30-day retention to mirror the receiver); revisit trigger: move to a project alias when volume or exposure grows (Q-29) | operator, ACT-06/23 |
| R12 | Recovery `--rematerialize` moves live API numbers while the site stays on 09-27, widening site/API drift (G1-07) | 4×2 | API changelog line (§6); G3 republish cadence; ideally step 7 follows within weeks | ACT-14, G3 |
| R13 | Hosted return passes run as project Editor or from a workstation with broad credentials (G1-01, NEW-10) | 2×4 | ACT-13 least-privilege jobs; scoped DB roles (`sig_recovery`, `sig_materialize`) | ACT-13 |
| R14 | A resuming orchestrator trusts future-dated records (B1 NEW-4) — now also in the planning ledger itself (NEW-11) | 3×3 | AR-4; date guard in validators (B3/B4); correct §11 of META_PLAN by appended entries | orchestrator, B4 |
| R15 | The first real release cannot rehearse a prior-pointer rollback on the live surface | 2×2 | rehearse the other two cases live; rehearse the pointer case on the second release, recorded as owed | ACT-24 |
| R16 | Chain integrity: Round-11 branches stack on #190; an agent rebasing or the operator's unbounded merge loop sweeping ACT PRs into `main` (H1 §3, NEW-5) | 2×3 | H1's rules; `TOP=190` for the operator's merge loop | H2 |

---

## 9. Operator decisions this plan needs (existing ids where they exist)

1. **Track-0 exception for QA-3/QA-4/QA-9 before 10-10** (NEW-7), or accept the risk. Recommendation: the exception.
2. **Q-10 / Q-23**: monthly ceiling, one-off ceiling, Cloud SQL disk cap in GB.
3. **Q-12 / Q-B1-3**: supersede `p-17b713` (recommended) — no re-sign.
4. **Q-E2-18**: GATE-G3's signature superseded; the step-7 readout is new.
5. **Confirm the two S0s outside the §7.1 approved list** (C2 NEW-1 `/visual-language/`, C3 NEW-2 personal handles) join ACT-06.
6. **Q-E2-05 wording + SLA values** for `/dispute/` (the 72 h / 7 d / 14 d mirror of `takedown.toml`, or longer honest times).
7. **ADR-124 allow list** (which HG-11-approved partner organisations are released) — ACT-10.
8. **API hotfix option** for C3 NEW-1 (recommended: no, unless step 1 slips past ~10-21).
9. **Q-27**: open the receiver in Round 11 with no backup moderator, under disclosed single-maintainer SLAs? And the email handling rule (NEW-5).
10. **Q-9**: which Round-10 surfaces ship in step 7 — recommendation: archive + release search first; research dossiers only after step 5; intake only after step 6.
11. **HG-03 batch** (E4 B1–B6 with I7) — gates step 5 only.
12. **D-R10-MEMORY-1 split** (B3 option C) at S5.

---

## 10. Findings filed (`findings/incoming/G2.csv`)

| id | sev | title (short) | routed |
|---|---|---|---|
| NEW-1 | S2 | No operator tool records ADR-124 `allow` dispositions; `record_disposition` is called only by recovery-apply, intake-apply and composed-verify | S1 + G2 (ACT-10) |
| NEW-2 | S2 (S1 on exposure) | The live `sig-web` image predates P32.13: its nginx has no withdrawal include and no `/r/`, `/releases/`, `/entity/` locations | G2 (ACT-17); G3 |
| NEW-3 | S2 | L44 `claim_assertion_bindings` forces a `claim_evidence` table rewrite (volatile default) under an exclusive lock; hosted cost unmeasured, fixtures cannot show it | G2 (ACT-09/11) |
| NEW-4 | S2 | G1's backup/log hardening (monthly logical exports ×3, `_Default` 90 d) conflicts with the intake retention and no-identifier promises; no log exclusion exists | G1 + G2 (ACT-23) |
| NEW-5 | S2 | The interim email channel (Q-29) carries the data the receiver was built to minimise with no handling rule; chain-tip `/dispute/` calls the receiver "anonymous" against packet §7 | G2 (ACT-06/23); E2 |
| NEW-6 | S2 | The API S0 (C3 NEW-1) cannot be fixed without an API roll, and the only chain-consistent roll needs L44–52 + ADR-124 allows; the serving image is P31.8 `ba3dca61`, 128 commits behind | S2 sequencing; G2 |
| NEW-7 | S2 | G1's pre-10-01/10-09 timing for alerts and the restore drill is incompatible with "Round-11 tickets only" unless Round 11 starts by ~10-08 | operator; S2 |
| NEW-8 | S3 | First-fire count refined (32 in 10-01…10-21 + peel-on 10-29) and the camreg batch window is a monthly 8-day write window (days 6–13), not a single 10-10 event | G1; S2 |
| NEW-9 | S3 | P32.22 storage ceilings are fractions but `sig-pg` autoresize is unlimited, so they can never bind | G2 (ACT-01/14); I8 |
| NEW-10 | S3 | No hosted execution host exists for any Round-10 return pass (packets use `$SIG_HOSTED_DSN` and `<mounted OCFL root>` placeholders; no job) | G2 (ACT-13); G1 |
| NEW-11 | S2 | The planning ledger repeats the F-21 clock failure: META_PLAN §11 entries dated 18:00Z–20:15Z and a §7.1 "18:2xZ" stamp are later than the commits that record them (≤ 17:42Z) | orchestrator; B4 |

---

## 11. Command log (read-only; project `zeta-medley-508121-u7`; times `date -u`)

| time (reads between the two `date -u` anchors 17:44:29Z and 17:51:03Z are approximate, ≈) | command (abridged) | used for |
|---|---|---|
| 17:42:26 | `date -u`; `git branch`, `git status`; `ls` of PD | header |
| 17:43:45 | `git log -8 --format='%h %cI %s'` | NEW-11 |
| 17:44:29 | `gcloud sql instances describe sig-pg --format=yaml(settings…)` | §1, NEW-9 |
| ≈17:45 | `gcloud run services describe sig-api/sig-web` (image, revision, traffic); `gcloud sql backups list --instance sig-pg` | §1 |
| ≈17:46 | `gcloud scheduler jobs list --location us-central1 --format=csv(name,schedule,state,lastAttemptTime,scheduleTime)` (to scratchpad) | §1, §3, NEW-8 |
| ≈17:47 | `gcloud compute backend-services list`; `gcloud compute url-maps list`; `gcloud run jobs list` (grep) | §1, NEW-10 |
| ≈17:47 | `gcloud logging sinks list`; `gcloud logging buckets list` | §1, NEW-4 |
| ≈17:48 | `gcloud artifacts docker images list …/sig-api` and `…/sig-web --include-tags` (grep the serving digests) | §1, NEW-2, NEW-6 |
| ≈17:48 | `git log`/`merge-base` for `ba3dca61`, `5c064881`; `git show 5c064881:ops/web/nginx.conf \| grep -c withdrawn_` → 0 | NEW-2, NEW-6 |
| ≈17:49 | `gcloud run services describe sig-api/sig-web --format=yaml(volumes, serviceAccountName)` | §1, C4 NEW-9 |
| ≈17:45–17:51 | `sed`/`grep` of `db/sqitch.plan`, `db/deploy/{claim_assertion_bindings,shared_temporal_contract,publication_dispositions,…}.sql`, `db/src/db/{claim_sink,dispositions}.py`, `api/src/api/{store_pg,cli}.py`, `ops/src/ops/{cli,recovery_apply}.py`, `ops/Dockerfile`, `ops/web/nginx.conf`, `ops/gcp/materialize.sh`, `ops/config.toml`, `web/src/{components/DisputeLink.astro,pages/dispute.astro,lib/resolution-eval.ts}`; `uv run sig-ops --help` | §4, NEW-1, NEW-3, NEW-5 |

17:51:03 `date -u` (drafting start); 17:57:51 `date -u` (CSV written). No hosted database query was run. No secret value was read (P14). No file outside `PD/design/G2-activation.md` and
`PD/findings/incoming/G2.csv` was written; nothing was committed.
