# P32.1 baseline reconciliation — the landed P31.19 tree vs the Round-10 map (SIG-MEM-001)

**Date:** 2026-09-27 · **Auditor revision:** `devin/p32-1-baseline-and-memory-audit` on seed
`codex/round10-seed-after-p31-19` @ `c8d72cc329f6b295967e2cca7633c19de188c4a7`.
**Parser:** `docs/build/tools/audit_current_state.py` (read-only; this report's machine output is
`discrepancies.json` / `discrepancies.md` beside it, with SHA-256 input digests).
**Live verification:** `live_verification=false` — every hosted/public figure below is *recorded*
evidence quoted with its date and revision, not a re-measurement; nothing here claims a live pass.

## 1. Baseline anchors (recorded, not re-measured)

| anchor | value | evidence |
|---|---|---|
| Round-10 seed | `codex/round10-seed-after-p31-19` @ `c8d72cc` | this branch's `base_branch`; git log |
| Round-10 import commit | `d6c562e` (PR #155, all-green CI run `36289234505`) | integration receipt `docs/build/planning/2026-09-25-six-streams/integration/2026-09-26-after-p31-19.md` |
| Landed P31.19 tip | `08d87c4` on `devin/p31-19-round9-closeout` (PR #154) | LEDGER chainTip PRIOR, BUILD_INDEX row 160 |
| P31.19 exact-head CI | run `36287547278` — docs/python/security green; **web/composed red at `npm ci`** (missing lockfile entries, before tests ran) | integration receipt — preserved verbatim; not relabelled green |
| ACCEPT-R8 | signed at `0a715fc` (authoritative readout `docs/build/readouts/ACCEPT-R8.md`) | contrary P31.19 prose corrected by appended import notes only — the signed record is not rewritten |
| Local imported validation | `make check` + `SIG_REQUIRE_DB_TESTS=1`: **4,404 passed / 3 skipped / 0 failed**, verify-gen clean, one existing Starlette deprecation warning | integration receipt (P31.19's own closeout recorded 4,403/3, `make test-db` 280, composed 16) |
| Research snapshot | `research/S1…S6` authored 2026-09-25 — a **dated** snapshot, not a claim about the P31.19 tree | DESIGN.md line 54; `DESIGN.md §P31.19 integration delta` |

## 2. DESIGN ownership-row reconciliation

Each row of `DESIGN.md §Existing P31 ownership and the delta` was checked against landed code,
tests, and recorded hosted/public evidence at `c8d72cc`.

| DESIGN row | landed preserve/consume evidence (code + tests) | recorded hosted/public evidence | delta for this round |
|---|---|---|---|
| P31.1 pooled API + bounded search | `api/src/api/store_pg.py` (`@_pooled`, self-healing pool, ADR-108); bounded `/v1/search` (limit ≤ 200, `next_cursor`) in `api/src/api/routes.py`; `tests/api/test_store_pg.py`, `test_api_shape.py` | `sig-api` rolled `sig-api@sha256:40a47da8…` (`sig-api-00011-wic`) at P31.8 — recorded | **two open defects verified below** → P32.2 (route) + P32.4 (watermark) |
| P31.2/.4/.6 run lifecycle, captures, replay | `evidence/` OCFL store; append-only `ingest_run_completion` (ADR-109); `ops/src/ops/cli.py` replay/dry-run inventory; pinned job images (ADR-111); restart/resume capture store | per-source hosted re-runs **+0** recorded on P31.12/13 jobs; batch-05 replay job held for 2026-10-10 | actual claim-to-capture locators/completeness states = P32.2/P32.6; the reserved cron is **not** advanced |
| P31.5 entity references | ADR-112; `connectors/src/connectors/records.py:415` emits `entity_ref` twins at link() stage; `resolution/partner_identity`; `tests/db/test_partner_entity_refs.py` | hosted spine holds **no** partner-org entity claims (P31.5 fixture-path); partner org names DO surface via `cached_canonical_name` labels (see §3) | role-aware extraction + eligibility consumption = P32.3/P32.5 |
| P31.7 re-sightings | ADR-114 (re-sighting links, latest-capture dating, supersession); `tests/db/test_resightings.py` | hosted roll 70/70 jobs by digest, re-run +0 — recorded | one shared as-of occurrence selection = P32.4 |
| P31.8 predicates | `ontology/vocab/predicates.yaml` + generated `ontology/generated/registry/predicate_registry.json`; never_resolve dispositions; directness config | hosted +13,131 envelopes then +0; live `/v1/entity/deployment/01a0a5da-…` flipped 404→200 — **registry half of D-P31.1-3 DONE** (recorded) | typed qualifiers through the sink + genre validation = P32.2 |
| P31.9 coverage peers | `inference/src/inference/data/peer_classes.toml` declared tracked/never-resolve peers | hosted +1,035,351 `not_researched`, re-run +0 — recorded | dossier absence states = P32.18–20 |
| P31.10/.11 review tooling + clustering wiring | `db/deploy/review_campaign.sql`, `camera_site_human_decisions.sql`; stratified sampler (`camsite-r10-seed-round10-v1`, 400 items, re-draw +0); loopback curation surface; review_decision→`camera_site_match` fold | **0 decisions hosted** (recorded); κ 0.669 < 0.70 → LLM suggester only | blinded independent labels/abstention/leakage-safe partitions = P32.9+, HUMAN-H4/H5 — no invented labels |
| P31.12/.13 source breadth | 8 adapters wired (`accountability::oversight_report` ×4, `government_mandated_disclosure` ×3, `procurement` assistance ×1); committed fixtures; shadow diff=0 | digest-pinned `sig-ingest-*` jobs (images `ingest-daf83934a7f1`, `ingest-26d5ceeeab74`); +25 +4,164 claims total; rights_decision rows appended — **D-R7.3-BREADTH 8/8 recorded DONE** | only scored gap-closing targets = P32.11; existing-source improvement is first-class acquisition |
| P31.14/.15/.16 analytics, tiles, public refresh | ADR-117/118; export analytics getters fail loud on missing analytic; tippecanoe z0–z14 per-compartment PMTiles; repo-owned nginx compression + `sig-web` deploy path | **public:** `sig-web` rolled `sha256:d8244804…` (rev `sig-web-00002-5nw`); `/map/points.json` → 404 both origins + object gone (R8-1 CLOSED); 178/178 freshness dates, 130 edges, accountability links, analytics, 12 tiles live; `probe-hosted` 7/7 — all recorded | release-specific records/search + no-JS pagination + publication completeness = P32.13–15 |
| P31.19 closeout | ADR-119 leak check scoped to code+config (`scripts/ci/secret_scan.py`, armed in CI, verified armed); capstone `docs/build/reports/CAPSTONE_VERIFICATION_2026-09-27.md`; 24-row sweep table in DEFERRALS | — | exact 2026-10-10 replay obligation (D-P31.4-1) retained **unpre-dated**; scheduled Round-10 homes recorded — no premature closure |

## 3. Closure-contract verification (D1/D4) — confirmed, NOT closed

The three contracts the import scheduled were re-checked against the landed tree. Defect locations
are verified in code at `c8d72cc`; statuses remain `OPEN`.

| obligation | verified defect/half-state at `c8d72cc` | already-closed half | scheduled owner | this run's action |
|---|---|---|---|---|
| **D-P31.1-3** unregistered-predicate serving | `api/src/api/routes.py:155` — the `/v1/entity/{type}/{id}` loop turns ANY `KeyError` from `RESOLVE` into a whole-entity 404 instead of serving registered facts + labelling the rest | registry half DONE at P31.8 (recorded: live deployment entity now answers 200 incl. `retention_period` RESOLVED and `disclosure_field_state` explicit-UNRESOLVED) | **P32.2** (registered facts stay servable under an unknown predicate; composed check at P33.2) | routing confirmed; baseline defect re-measured in code; **row stays OPEN** |
| **D-P31.1-1** annotation watermark ~10 s | `api/src/api/store_pg.py:876` — `_spine_watermark` counts `claim` (≈2.3M rows), closed rows, latest assertion, `claim_evidence`, `evidence_capture`, `evidence_artifact` on every annotation call under the annotation lock (8 concurrent calls → median 48 s recorded 2026-09-24) | — | **P32.4** (bounded, correctly-invalidated watermark under the shared temporal contract; e2e evidence at P32.24) | routing confirmed; cost path verified in code; **row stays OPEN** |
| **D-P31.5-2** `publication_review_required` read surfaces | flag written (`db/deploy/domain_entities.sql`; `db/src/db/claim_sink.py`; `resolution/src/resolution/identity.py` — every `sig.org.name` org `true`, `tests/db/test_partner_entity_refs.py`) but **no read path consumes it**: `PgReadStore` labels organisations from `cached_canonical_name` | web surface honours the flag **by construction** — every `web/network.json` node labels by entity id, zero partner-org names in any public artifact (recorded P31.16 surface verification); the **API** read surface publicly labels flagged partner orgs (`GET /v1/search?q=Vigilant`, `/v1/entity/organization/01a0d751-…` → `label: "Vigilant Solutions (LEARN)"` — recorded) | **P32.5** (the common publication-eligibility contract; release verification P32.23a/P32.24) | routing confirmed; **scope reduction appended (§6)**; **row stays OPEN** |

## 4. Parser discrepancy report (D2)

`audit_current_state.py` on the real tree at `c8d72cc`: **0 errors, 12 conflicts** across 125 hashed
inputs (`discrepancies.json`). The parser makes no control-state write; severities: `error`
(structural violation) vs `conflict` (ambiguity requiring a *recorded* reconciliation — nothing is
silently resolved, no last-token-wins).

| finding | obligations/files | reconciliation recorded here |
|---|---|---|
| `deferrals/status-conflict` ×4 | D-P21.4-3 (OPEN lead, cell records DONE 2026-09-16 go-public); D-P21.5-1 (PARTIAL lead, credentialed legs DONE + SWH leg blocked on repo-visibility decision); D-SOURCES.2-4 (PARTIAL lead, resolved-by-GL-GATE-08 2026-09-19); D-R7.3-BREADTH (OPEN lead, 8/8 landed DONE 2026-09-26) | each is an **append-only formatting artifact** the P31.19 sweep already documents verbatim; a mechanical reader and the prose genuinely disagree, so each needs an explicit evidence-transition event in the P32.7 migration (SIG-MEM-002) — the audit does not pick an interpretation and the rows are not rewritten or closed |
| `manifest/duplicate-file` ×6 | `P21.1/P21.3/P21.4/P21.5/P21.7/P21.8` files at chain rows 55–62 AND rows 71–78 | **documented, intentional**: Lane-B re-run pointer rows (manifest `## Decomposition decisions` RENUMBER note, line ~438 — "pointers to untouched existing contracts… not renamed"). Parser uses the first chain position for id→position resolution; no action owed |
| `tickets/dependency-not-in-chain` ×2 | `P31.17`, `P31.18` inside `P31.19`'s `Depends on:` line | **documented prose context**: the same line says "P31.17 was **dropped**… and P31.18 **moved to Round 10** — neither is a Round-9 dependency" (rows 158/159 consciously unused). Not stale — verified against LEDGER GATE DECISIONS 2026-09-25 |

Forward-dependency check uses **physical manifest row order**, not the `#` cell (inserted rows
P30.2a=140/P30.2b=141 sit physically before row 138 P30.3 — the documented INSERT). No forward deps
exist on the real tree; adversarial fixtures prove detection for numbered-and-legacy filenames alike.

## 5. Demonstrated defects · hypotheses · already-closed seams · still-owed work

Per SIG-MEM-001 these are kept **separate** — a verified defect is not a hypothesis, a recorded
closure is not re-opened, and an owed row is not closed by parsing.

**Demonstrated defects (re-verified in code at `c8d72cc`):**
- `routes.py:155` whole-entity 404 on unregistered predicate (`→ P32.2`, D-P31.1-3).
- `store_pg.py:876` annotation watermark = 6 relation counts per call under the annotation lock
  (`→ P32.4`, D-P31.1-1).
- `publication_review_required` written but never read on any serve path (`→ P32.5`, D-P31.5-2).
- `scripts/docs/check-build-memory.sh:65` writes its JSON report to a **shared**
  `/tmp/build-memory-check.json` across worktrees — the S6 worktree-collision defect, still landed
  (`→ P32.8`, D-R10-MEMORY-1; this run's parser already uses the caller-provided-path pattern as the
  compensating shape).

**Hypotheses → resolved or still open:**
- S6's "spec builder crosses checkout boundaries" — **resolved before this run**: `spec_src/BUILD.sh:6`
  resolves `ROOT` relative to the script (`$SOURCE_DIR/../../../..`); verified at `c8d72cc`.
- Two-phase closeout crash ambiguity — still a workflow risk, scheduled to P32.8 (SIG-MEM-003), not
  demonstrated as a live failure.

**Already-closed seams (recorded, not re-verified live):**
- D-P31.1-3 registry half (P31.8, hosted 200); D-R7.3-BREADTH 8/8 (P31.12/13); D-SOURCES.12-1;
  D-P30.4-4 (ADR-119, this import's leak scope); D-P30.2-2, D-P30.2-3, D-P30.2a-1/-2, D-P30.2b-3,
  D-P30.3-1/-2/-3, D-P30.4-1, D-P30.2-1, D-P31.5-1, D-P27.5-1, R8-1 (points.json retired);
  D-P21.4-3's own cell records DONE-with-artifact noted above. P31.19's whole-build capstone and
  24-row sweep stand as written.

**Still-owed work — explicitly routed (D3):**

| obligation | owner path | status after this run |
|---|---|---|
| D-P31.1-3 route half | **P32.2** → composed verify P33.2 | OPEN (unchanged) |
| D-P31.1-1 watermark | **P32.4** → e2e verify P32.24 | OPEN (unchanged) |
| D-P31.5-2 eligibility/labels | **P32.5** → release verify P32.23a/P32.24; narrowed per §6 | OPEN (unchanged) |
| D-P31.4-1 OSM replay | automatic at the 2026-10-10T03:35Z cron, then the row's exact verify command | OPEN — **not pre-dated, not advanced** |
| D-R6.1-EVAL + human halves of D-P30.2b-1/-2 | HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 | OPEN (unchanged) |
| D-P30.2b-2 name-level conflicts | Round-10 evaluation refresh | OPEN (unchanged) |
| D-R10-HUMAN/SOURCES/LIVE/PUBLISH/USERS-1 | HUMAN-H4/H5, P32.18–21, P32.22/23a, GATE-G3→P32.25, P32.24 | OPEN (unchanged) |
| D-R10-MEMORY-1 single-writer cutover | P32.8 — **this run does not claim enforcement or cutover** | OPEN (unchanged) |
| operator/reviewer rows (D-P21.3-2 HG-09, D-P21.5-1 repo-visibility, D-P21.7-1 HG-08, D-JURIS.2-1 HG-04, D-SOURCES.*/GL-* remainder, D-R7.1-AUTH, D-R7.2-SEND, D-FEDERAL.1-1 quota tail) | per P31.19 sweep owners | unchanged — human/scheduled decisions, never agent-ticked |
| the four mechanical status-conflicts | **P32.7** evidence-transition migration events (SIG-MEM-002) | remain OPEN/PARTIAL exactly as written until the migration records an interpretation |
| stale-doc inventory (§7) | **P33.8** (SIG-MEM-004 doc refresh) | unchanged |

## 6. Scope reductions appended before consumer dispatch

Per DESIGN line 54 — shrink deltas through an appended amendment rather than re-implement:

1. **D-P31.5-2 narrowed to the API read surface + the eligibility decision.** The DESIGN's "consumed
   publication-review status" row assumed an unverified read surface; the landed baseline shows the
   **web surface already honours the flag by construction** (recorded P31.16 verification). P32.5's
   remaining delta is (a) the common publication-eligibility policy over read surfaces, (b) the API
   label path (`cached_canonical_name`), and (c) the recorded policy choice the row itself names —
   mootness ADR for public accountability organisations *or* a read-surface gate. No web-side re-audit
   is owed. Recorded in `DESIGN.md §P32.1 baseline addendum (2026-09-27)`.
2. **No parser-projection in P32.1.** The S6 landable units keep the deterministic current-state
   *projection* (`docs/build/reports/current/`, obligation events, coverage-event schema) in P32.7
   and the writer-lock/recovery protocol in P32.8. This run delivers unit 1 only: the strict parser +
   discrepancy report + reconciliation. `discrepancies.*` here is a run artifact, not the P32.7
   projection.

## 7. Stale-doc conflict inventory (routed to P33.8, not fixed here)

Strict reading of doc-vs-landed surfaces the following conflicts; per SIG-MEM-004 they belong to the
Round-10 documentation tail, so they are **recorded and routed, not rewritten**:

- `README.md:17` + `:142` — "not a running service: nothing is deployed and no source has been
  fetched live" — stale: surveillancegraph.org has served the live national surface since
  2026-09-24/27 (P31.16 recorded publish).
- `AGENTS.md:23,113` — "(Astro, static, zero-JS)" / "public web budget is zero-JS" — stale vs the
  landed public islands `web/src/islands/{Map,Network,Search}Island.tsx` mounted `client:only="react"`
  on `/map`, `/search`, `/network` (ADR-091/097; retained by ADR-120 §4). `web/AGENTS.md`'s
  "zero-JS-by-default … the `/curate/**` island allowance is the only exception" understates it too.
- `docs/build/BUILD_INDEX.md:1` — header still reads "the 46-ticket chain" though the index carries
  160+ rows (cosmetic; the table itself is correct).
- `docs/tickets/DEFERRALS.md` lines 567–570 — the sweep table's landing column still says "BL-057, no
  chain row" for D-P31.1-1/-3 + D-P31.5-2 while the same file's own landing amendment (bottom section)
  names their P32.x homes; the cells themselves get the P32.1 annotation appended (below).

## 8. Unresolved delta decisions (all named; none silently resolved)

1. The four `deferrals/status-conflict` rows — a strict reader cannot tell "formatting artifact" from
   "unreconciled status" without the appended sweep prose; **decision owed by P32.7's migration
   events**, whose evidence requirement this run's routing annotations make explicit.
2. Six pointer-row duplicates — reconciled **now** against the manifest's own RENUMBER note; no event
   needed (the manifest documents them).
3. P31.17/P31.18 names in a depends-line — reconciled **now** as documented dropped/moved context.
4. `check-build-memory.sh` shared report path — kept running as-is (the vendored validator's own
   convention); the *new* parser refuses shared paths. The replacement is P32.8's, gated by
   D-R10-MEMORY-1.
5. D-P31.5-2's closure *choice* (mootness ADR vs read-surface gate) is a policy decision P32.5 must
   put before the operator — the audit deliberately does not pre-answer it.

## 9. Source funnel + evidence domains

The named definitions live beside this file:
`EVIDENCE_DOMAINS_AND_SOURCE_FUNNEL.md` (5 evidence domains; 8 funnel units) with this baseline's
measured/recorded values. Contract: fixture evidence cannot supersede hosted failure; hosted success
cannot establish public publication; unavailable domains are named, never omitted.
