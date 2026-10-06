# PLAN-11B — Contracts for 11B rows + the SIG-TRANSP requirement family

<!-- BM-RUN-01: Harness = the exact PR-trailer string. Started/Closed = UTC
     `date -u` at branch start / when the last acceptance criterion is
     satisfied. The OM gap table is the ticket's operating checklist.
     This run ledger is shared by the thirteen contexts C1–C13 of row 239;
     each context appends its own section and its own Started/Closed. C13
     closes the ledger — no `Closed:` header line before then. -->

Harness: devin-desktop/swe-2-high/subagent
Started: 2026-10-05T11:32Z (`date -u` at branch creation; branch
`r11/PLAN-11B-contracts-for-11b-and-transp-family` from `0de78f39` on
`r11/P34.33-round-close-record-checks`)
Closed: 2026-10-06T14:04Z (`date -u`; last C13 criterion = the
head-bound ci read recorded in the C13 section below)
PR: #236 (opened at the C1 push; base `r11/P34.33-round-close-record-checks`;
stays open — the row closes only at C13)

## Spec / Base / Branch / Config

- Spec: `docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md`
  (manifest row 239 — Round 11, `decompose-spec mode=extend`, thirteen
  contexts C1–C13 over rows 261–343; each context ≤ 8 rows).
- Base: `r11/P34.33-round-close-record-checks` @ `0de78f39`
- Branch: `r11/PLAN-11B-contracts-for-11b-and-transp-family` (shared;
  one PR for the whole row). PR base = the base branch (PR-1).
- Config: `decompose-spec mode=extend`; `live_verification=false` — this
  row writes contracts and spec text; it executes no 11B row, mutates no
  production and ticks no gate.
- Requirement ids (from the contract): **written here** — the SIG-TRANSP
  family (plan §6.2, spec §56.8); **owners re-confirmed** — SIG-SEC-008 →
  P35.1a/b, SIG-SEC-009 → P35.4, SIG-CONF-010 → P35.60 (the §56 `Owner:`
  lines as written); **cited** — SIG-ENG-003 (spec changes through
  `spec_src` + `BUILD.sh`), SIG-ENG-041 (MISSING rows and routing; owner
  SEED-15).

## Deferrals read

Read `docs/tickets/DEFERRALS.md` first (AGENTS.md gotcha 8). Rows naming
surfaces this plan row touches:

- `D-R11-ARCHIVE-1` (OPEN; cites BL-029, BL-037) — the non-GCS mirror leg is
  named to P35.5 (row 262); P35.5's contract keeps the deferral open and
  carries the mirror question. Read for C1's row 262 contract.
- `D-P34.50-1` (OPEN) — OP-09 is operator-owned; P35.67 (row 263) is the
  verifying probe row. Read for C1's row 263 contract.
- Rows `D-R11-OSMUID-1` and the tribal/later-phase placements of the
  contract's deliverable 8 are carried items of the *plan* row; their
  landing rows sit in C2–C12's batches — noted in each context's section.
- No OPEN/PARTIAL row is closed by this planning row; no row's lead token
  changes, so no obligation-event transitions are owed.

## Contexts

### C1 — 2026-10-05 (rows 261–265 + the SIG-TRANSP family)

Started: 2026-10-05T11:32Z · Closed: 2026-10-05T16:36Z (`date -u`; last C1
criterion = green head-bound CI at 70ab52a).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverables 1, 2-in-part, 3-in-part):

- Append the SIG-TRANSP family (SIG-TRANSP-001…043) to `spec_src`,
  de-duplicated against existing ids and the K13 set (D26–D43 written
  once here; PLAN-11C cites the final ids); register `TRANSP` in §0.3;
  rebuild via `docs/research/_meta/spec_src/BUILD.sh`; commit the
  draft→final id map `docs/build/reports/plan-11b/TRANSP_id_map.csv`;
  update `check_spec_src.py` baselines and Appendix G.7 (the SEED-12
  pattern); add one `COVERAGE_MATRIX.csv` row per id, verdict MISSING,
  routed to the owning chain row; one `coverage-assessment/1` event per
  id.
- Rewrite skeletons to full contracts: row 261 (P35.57, API release
  parity), 262 (P35.5, zero-egress distribution host), 263 (P35.67,
  post-DNS-cutover probe), 264 (P35.1a, scheduler of record / live diff /
  cron lint), 265 (P36.1a, opt-out register + reservation refusal).
- Re-confirm §56 owner lines: SIG-SEC-008 → P35.1a/b, SIG-SEC-009 →
  P35.4, SIG-CONF-010 → P35.60 — recorded in the row-264 contract;
  no spec change needed (the owner lines already read so).
- Notes for C2+: the tribal/S8 item (8b) and its reading belong to
  C2/C5 per the contract's placement instructions — not read or placed
  by C1.

Findings / decisions:

- Committed TRANSP work verified before building on it (5c771f66): all 43
  `SIG-TRANSP-001…043` ids land in spec §56.10 (the family is appended *under*
  §56.8's later-family/de-dup rules — the ledger header's "spec §56.8" cites
  the governing rules section, the requirements themselves are §56.10);
  `TRANSP` registered in §0.3; Appendix G.7 row `R11-X2`; draft→final map
  `docs/build/reports/plan-11b/TRANSP_id_map.csv`; 43 MISSING coverage rows
  routed to their owning 11B chain rows; 43 `coverage-assessment/1` events.
  `BUILD.sh` reproduces the committed spec byte-identically (852,023 bytes);
  `check_spec_src.py` OK (1,644/1,644 ids; 820 requirement ids = 668 + 152
  fold-backs); coverage matrix 820/820 rows OK.
- Contracts rewritten in place (same filenames). Corrections found against
  the ratified plan rows (`data/round11_plan.csv`) and fixed:
  - 261 (P35.57): confirmed deps P34.25;P34.46;P34.40, IN-TICKET PAUSE /
    never pre-authorised (public API responses), 1 live leg (the roll after
    the go), size M.
  - 262 (P35.5): `Depends on` corrected `none` → `P34.5, P34.10`; live legs
    corrected 2 → 1 (the post-cutover probe belongs to row 263); OM-20
    conditional (listed at GATE-G4) else in-ticket pause.
  - 263 (P35.67): gate status corrected to `none` (the plan cell carries no
    gate); read-only; `live:OP-09` edge kept; 2 legs (post-OP-09 probe +
    cert-renewal read ~2026-11-22).
  - 264 (P35.1a): deps confirmed P34.4; no live legs — the production write
    (scheduled-ops deploy + first live-diff) runs in-ticket only if the
    GATE-G4 OM-20 list names the row; size L-split-a. SIG-SEC-008 ownership
    confirmed P35.1a/b as written.
  - 265 (P36.1a): `Live window: none` added (no live legs but the field is
    still declared); size corrected S → L-split-a; SIG-INGEST-046c
    affirmative-reservation refusal, the S6 R-19 express-terms classification
    route, S6R-28 GATE-G5 routing and the P36.1a → P35.11 hard edge all
    carried.
  - All five now carry: the literal `Run:` line, harness header, verbatim
    operator words, OM-20 status, live stage/window/legs + re-run prompt
    (OM-19), production-mutation declarations (OM-14), token-counted Load
    lists (bytes ÷3 and ÷4), requirement ids, layered ACs (each layer
    named — OM-06), cross-cutting invariants and the B5 §6.2/H2 §7
    operating-clause block. No skeleton headers remain.
- Verification fixes found and corrected (in place, C1 scope):
  - `docs/build/tools/test_check_spec_src.py` hardcoded
    `EXPECTED_IDS == 777`; the committed TRANSP append raised it to 820 and
    the companion test was missed → red under `make check`. Fixed to 820
    with the arithmetic comment.
  - The committed `current` projection was stale after 5c771f66 (spec,
    coverage matrix, assessments and this ledger had drifted); regenerated
    — `verify` now fresh 973/973.
- Local environment honesty (P11): the local Docker daemon is unreachable —
  `docker info` hangs (> 17 min, no timeout in `tests/ops/test_web_iac.py`'s
  probe), `docker version`/`docker.from_env().ping()` return EOF. `make
  check` was run with a PATH-ahead `docker` stub so the Docker-gated
  `tests/db`, `tests/e2e` and `test_web_iac` docker rows **skip** instead of
  hanging — they run in CI's `python` (db) and `composed` jobs.
  `SIG_GCP_PROJECT` armed with the local sentinel `sig-local-sentinel` for
  the fail-closed secrets scan (OP-07 pattern; the real id lives in
  `vars.SIG_GCP_PROJECT`).
- Boundary (OM-05): first read `ci_boundary.py --pr 236` @`9dcb023` =
  **blockedOn** (docs job red — the projection digest for this ledger had
  drifted: the C1 regen predated the same-commit ledger edit). Fix-forward
  `70ab52a` regenerated the projection after the ledger edits; head-bound
  re-read: `ci: pass #236@70ab52a` — python/docs/composed/security/web 5/5
  (run 37339562266; stack pass; `main` 2de7b50 descends:no merges:0
  open-other:6; log `docs/build/logs/ci-PLAN-11B-C1.json`, gitignored).
  The final C1 record commit's own head-bound read lands in the same log;
  C13 reads the boundary again at closeout.

### C2 — 2026-10-05 (rows 266–271 + the 8b/8c placements)

Started: 2026-10-05T16:58Z (first C2 file write; source: file mtime —
investigation preceded it in the same context) · Closed: 2026-10-05T17:39Z
(last C2 criterion = the head-bound CI pass at `3243036`, read
17:38:56Z per the ci-boundary log's `read_at`).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + deliverable 8b/8c placements):

- Rewrite skeletons to full contracts: row 266 (P35.6, acquisition
  plumbing and verification harness), 267 (P35.7, registry/tenant label
  corrections M1–M7), 268 (P35.8, Legistar keyword-filtered paged matter
  pass + agenda vocabulary), 269 (P35.9, USAspending/CROL vocabulary and
  filters), 270 (P35.10, state ALPR statute seed 2026 + duty rows),
  271 (P35.11, Wave-A activation).
- Place the carried items: tribal S8 members `AP-T2-201` and
  `AP-T2-210` → P35.11 (ADR-185 screened lane); `AP-T2-093` excluded,
  stays `D-R11-LATER-09`; `D-R11-OSMUID-1` → Plan-extensions hand-off to
  P37.1 (PLAN-11C); the ADR-171 outreach-owed set recorded in P35.6 and
  P35.11.

Findings / decisions (per row):

- 266 (P35.6): deps `SEED-03;P35.1a`; no gate, no live stage, 1.0 run,
  owns `F-330 (S1)` per the plan's `S0/S1` column. Carries the registry/target/cadence
  generator (R2 ids, dataset-id dedupe, collision checks), the NEW-4
  batch generator, `scheduled-ops.sh --paused`, per-row `task_timeout`,
  cron OR-semantics lint, `out_fields`/ArcGIS allowlist RPM for
  `dot_511`, and the `coverage-delta` + wave-verification CLIs. No live
  acquisition is claimed — plumbing/harness only; `ingestion_permitted`
  untouched.
- 267 (P35.7): gate `I7-X4 [B-40] = approve` verbatim (2026-10-01T04:49:27Z);
  0.5 run; six `jurisdiction` label fixes + `ncdot_runneals_mirror`
  lineage marking + `faa_drone_waivers` homepage fix; key-stability check
  before any rename.
- 268 (P35.8): deps P35.6;P35.7; no gate; 1.0 run; `substringof`
  keyword index query beside the unchanged recency query, paged to
  exhaustion in OR-groups under the ~1,500-char URL bound, client-side
  word-boundary precision filter, `agenda_content_vocab.toml` versioned
  bump, legistar `task_timeout` 60m→3h, OUSD/Washoe tenant verification
  (non-Legistar → ACQ-22/P37.50).
- 269 (P35.9): deps P35.6; no gate; 0.5 run; 17/76-source term set,
  `acq_keyword_terms` on `usa_spending`/`crol`, generic `portal_where`
  (CROL `B00329`, Cook County; WA DES plain), pruned fallback,
  award-notice description fan-out.
- 270 (P35.10): deps P35.6; gate `I7-C9 [B-39] = a` verbatim; 0.5 run;
  owns `F-374 (S1)`; seed refresh from recorded origins, duty rows,
  50-state validation test.
- 271 (P35.11): deps P35.7/P35.8/P35.9/P35.10/P34.3–P34.6/P34.46/P36.1a/
  P35.38a; production-write OM-20 row; gate ING-GO-A verbatim at GATE-G4
  else in-ticket pause; X3 posture recorded; window 2026-10-19→23
  14:00–20:00Z, ≥ 48 h after P34.46; three legs (roll+`load-seed`+3
  manual first runs one at a time / `+0` re-runs / resume schedules);
  legistar trigger `0 5 20 * *` paused or roll delayed past its
  2026-10-20 05:00Z fire; no overlap with `sig-materialize`.

Placements (manifest `## Plan extensions` line appended 2026-10-05):

- Tribal S8: `AP-T2-201` (`dot_511` arcgis_query, IND-TRIBAL) and
  `AP-T2-210` (`dossier_documents`, IND-TRIBAL) → **P35.11** under
  ADR-185 (screened lane, no outside contact, facts/citations or
  screened metadata only, no-human-review disclosure);
  `CG-LATER-tribal-data-governance-rule-i7-new-6` stays OPEN.
- `AP-T2-093` (`doj_ctas_awards`, IND-P8/RB-05, not IND-TRIBAL): stays
  `D-R11-LATER-09`; explicitly excluded from Wave A.
- `D-R11-OSMUID-1` → hand-off to **P37.1** (row 344, the OSM
  connector's next code change; PLAN-11C authors it). Caveat: P35.26's
  11B OSM re-ingest may precede it — compensating controls are
  `extract()`'s pre-claim discard + P34.49's seal; C13 may re-route.
- Outreach-owed (ADR-171): SIG-CHART-033 / SIG-INGEST-029 /
  SIG-INGEST-030a / SIG-CONTRIB-012 / SIG-CONTRIB-012a /
  SIG-CONTRIB-013 / SIG-GOV-024 recorded as owed — unmet at launch
  (D-R11-LATER-04) in P35.6 and P35.11; P35.7–P35.10 record why the set
  does not apply. No outside contact made or implied.

Local verification (P11, with recorded limits):

- `make check` — **green** (ruff + format + mypy 313 files + pytest
  6,957 items + verify-gen clean), run with the pre-existing PATH-ahead
  fast-fail `docker` stub (`/tmp/sig-nodocker-bin/docker` = `exit 1`,
  not committed) because the local Docker daemon stays wedged from C1
  (`docker info` hangs / EOF): the Docker-gated `tests/db`,
  `tests/e2e`, `test_web_iac` and pg-backend rows **skip** locally and
  run in CI's `python`/`composed` jobs. `SIG_GCP_PROJECT` armed with
  the sentinel `sig-local-sentinel` (OP-07 pattern).
- `make docs-check` — green after the projection regen (below): no
  skeleton/manifest violations on the rewritten rows; `memory_guard
  --worktree` clean; `check_spec_src` 1,644/1,644 ids;
  `check_coverage_matrix` 820/820; `obligation_events check` green;
  `audit_current_state` 0 errors.
- The committed `current` projection digests drifted on this context's
  edits (the six contracts, the manifest line, this ledger); regenerated
  with `current_projection.py generate` — `verify` fresh before commit.
- `python3 docs/build/tools/memory_guard.py all --staged` — run green
  before the commit (protected records appended only).

Boundary (OM-05): `ci_boundary.py --pr 236` @ `60c3fe4e` (content
commit) = **`ci: pass #236@60c3fe4`** — python/docs/composed/security/web
5/5 head-bound (run 37348287333); the boundary-record commit
`32430362` was then pushed and re-read head-bound:
**`ci: pass #236@3243036`** (run 37349874555; stack pass; `main`
2de7b50 descends:no merges:0 open-other:6). Green on the first head,
no fix-forwards; both reads land in
`docs/build/logs/ci-PLAN-11B-C2.json` (gitignored). C13 reads the
boundary again at closeout.

### C3 — 2026-10-05 (rows 272–278)

Started: 2026-10-05T~18:30Z (first C3 file write; source: file mtime —
investigation preceded it in the same context) · Closed:
2026-10-05T~20:10Z (work complete; boundary unresolved at close — three
consecutive GitHub hosted-runner acquisition cancels, recorded below;
the context stops blockedOn per DRAFT-MEM-3/G3 rather than looping, and
C13's closeout re-read settles it).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a check):

- Rewrite skeletons to full contracts: row 272 (P35.14a, vocabulary
  conformance + closed vocabulary at the sink), 273 (P35.14b, entity
  typing + hosted CHECK-NOT-VALID sqitch change), 274 (P35.15a,
  technology slug + export columns + facets), 275 (P35.15b, ~200k-subject
  append-only technology backfill), 276 (P36.3, ATE technology concept +
  zone geometry kind), 277 (P36.4, official camera layers ×10,
  `r11-layers-01`), 278 (P36.5, agency ALPR/Flock layers ×16 targets,
  `r11-layers-02`).
- Deliverable 8a (ADR-171 outreach-owed placement): applied per row —
  recorded why-not on 276/277/278 (see below).

Findings / decisions (per row):

- 272 (P35.14a): deps `P34.24b`; OM-20 conditional (GATE-G4 verbatim
  listing else in-ticket pause); INSERT-only hosted vocabulary
  registrations only — six predicates, genre stamps, Mobility correction,
  group-13 items. Corrections to the earlier draft: the
  `SuccessionKind`/`succession`/`succession_kind` retirement
  (BL-047/RISK-P3-04 — legacy slots coexisting with the reified
  `OrganizationRelation` model) was missing from scope and is now
  carried; SIG-ONTO-060 rides as the SEED-12b proposal artifact (read the
  realised enum, write the amendment proposal — never apply it: a
  closed-list relaxation needs the operator's words, G.7.5). `live:`
  edge → P34.24b.
- 273 (P35.14b): deps `P35.14a`; gate verbatim `IN-TICKET PAUSE (never
  pre-authorised under OM-20 …); explicit verbatim go` — the plan §3.3
  never-pre-authorised class names it by id (hosted sqitch change that
  alters an existing table / ACCESS EXCLUSIVE). 1 leg (0.5 run): AR-2
  restore point → `sqitch deploy --verify` with `lock_timeout` →
  append-only typed-identity write (new decision records; existing entity
  rows never updated/deleted) — all behind the operator's verbatim
  in-ticket go; re-run prompt lands the OM-19 queue. `live:` edge →
  P35.14a.
- 274 (P35.15a): deps `P35.14b`; OM-20 conditional; INSERT-only
  registration of the `technology` predicate + new technology slugs; no
  claim/entity writes, no backfill, no flip, no fetch. Correction: the
  draft's stale "enforcement family" wording was removed — P36.3 (row
  276) owns the ATE technology concept; P35.15a owns slug registration,
  export columns and facets, with technology declared per-target (never
  source-ID/name substrings). `live:` edge → P35.14b.
- 275 (P35.15b): deps `P35.15a`; OM-20 conditional
  (`(hosted append-only backfill)` verbatim); 1 leg (0.5 run) inside
  AR-3 + AR-2 — the ~200k-subject append-only technology-claim backfill:
  AR-2 restore point → hosted `vocab_*` check → dry run → `--apply`
  chunked INSERT-only → read-back → `+0` re-run. No subject reads
  `traffic_camera` unless its target declares it; Flock/DeFlock lineages
  read ALPR; leg refuses if `live:` P35.15a's registrations are not
  landed (P35.14a's closed sink would quarantine). `live:` edges →
  P35.15a + P35.14a.
- 276 (P36.3): deps `P35.14b`; gate `none`; not an OM-20 row; 0.5 run;
  no live stage. ATE family + subtypes (red-light, speed, bus-lane,
  school-bus stop-arm, work-zone + `-unspecified` leaf) under §11.5's
  hierarchy, each with `distinguishing_criterion`/`evidence_signature`/
  `salience` (SIG-ONTO-056), plus the zone geometry kind the area-shaped
  records declare. `make gen` regeneration; the §13.1 canonical counts
  (SIG-ONTO-052/052a) change through `spec_src` + `BUILD.sh` with the
  manifest amendment line and an ADR — never a direct edit of the
  generated spec.
- 277 (P36.4): deps `P35.6;P35.15b;P35.14b` + **P36.3 added** (recorded
  correction, agent-labelled in-contract: the Seattle target's
  `geometry_kind="area"` emit needs the zone geometry kind P36.3
  registers — P35.14a's closed sink would quarantine the value; chain
  order already places 276 before 277). Gate verbatim `HG-03
  I7-RB-01/RB-02 [A-7] = a (GL-GATE-07 re-confirmed: batch-wide; Part
  VIII S-lines still apply): …`. 1.0 run; no live stage/legs — the
  flips are the operator's OP-26/ING-GO-B execution at P36.12. Ten
  targets: `dot_511_{de,vt,wv,mi,nc}` + `camreg_{lincoln_ne_traffic,
  omaha_ne_parks,hyattsville_md_cctv,seattle_wa_spd_cctv_areas}` +
  Denver HALO (under `camreg_denver_co` if the licence matches, else
  `camreg_denver_co_halo`); per-target `out_fields` allowlist +
  `technology`, VT `DeviceType` filter, Seattle polygon → programme
  area (never a device point), arcgis api_allowlist RPM (I8 NEW-3);
  all `ingestion_permitted=false`.
- 278 (P36.5): deps `P35.6;P35.15b;P35.14b`; gate verbatim `HG-03
  I7-RB-01 [A-7] = a (…same batch-wide wording…)`. 1.0 run; no live
  stage/legs. Fifteen sources / sixteen targets (the `camreg_fdot_flock`
  source carries two: `fdot_d3_flock_inventory` +
  `fdot_flock_removal_status`, ingested same-run so the removal ledger
  and inventory stay consistent). Row rules: removal → `valid_to` never
  deletion; Prince William `status=proposed`; Milford `approximate`
  coordinates; Shelbyville "Hits" column excluded; Leon County splits
  Vigilant LPR (`alpr-fixed`) from RTCC/CCTV + the existing
  `camreg_leon_fl` same-org check recorded. Every row typed by declared
  `technology`; all `ingestion_permitted=false`; flips are the
  operator's at Wave B (P36.12).

ADR-171 outreach-owed (deliverable 8a) — why-not recorded per row:

- 276/277/278 each carry a "**recorded why it does not apply**" block:
  no §6-compact or §22.4–22.5/§35.1 ecosystem-project connector is
  written, widened or activated — 276 is vocabulary only; 277's ten
  layers and 278's sixteen targets are all agency-origin sources (state
  DOT 511 endpoints, city/police published layers, FDOT + municipal
  inventories). The Eyes on Flock relationship on 278 stays read-side
  (`camera_operator` links agency entities to existing EoF portal
  entities at resolution — no EoF fetch or connector change), and ER
  dedupe against OSM points is a read-time comparison, not an OSM
  connector change. The Stage-0 set (SIG-CHART-033, SIG-INGEST-029/
  030a, SIG-CONTRIB-012/012a/013, SIG-GOV-024) stays owed under
  `D-R11-LATER-04` — recorded, never implied satisfied; no outside
  contact made (ADR-171 Decision 3, U-011).

Local verification (P11, with recorded limits):

- `make docs-check` — green after the projection regen: no
  skeleton/manifest violations on the rewritten rows; `check_spec_src`
  1,644/1,644 ids; `check_coverage_matrix` 820/820;
  `obligation_events check` green; `audit_current_state` 0 errors
  (9 reconciled conflicts, all pre-existing); build-memory layout and
  ledger-contract gates clean.
- The committed `current` projection digests drifted on this context's
  edits (the seven contracts); regenerated with
  `current_projection.py generate` — `verify` fresh before commit.
- `python3 docs/build/tools/memory_guard.py all --staged` — green
  before the content commit (protected records appended only).
- `make check` — not re-run this context: no code changed (contracts,
  policy comment lines and this ledger only); C2's green at `b1206694`
  stands and CI is the authority. Docker stays wedged (recorded C1).
- `python3 docs/build/tools/memory_guard.py all --range
  0de78f39...427c5efb` — green after the `seed-commit` declaration
  (below); exactly the CI range check that failed.

Boundary (OM-05):

- Read 1 @ `427c5efb` (content commit): **`blockedOn: CI fail on
  #236@427c5ef (docs)`** — the history guard flagged the contract
  rewrites: the commit subject named ticket ids (`P35.14a/b`, …) so
  `executed()` (B2 §7) marked all seven contracts "executing" in-range
  and every rewritten skeleton line read as a frozen-contract edit (658
  append-only findings, run 37363207636). The branch ruleset forbids
  force-push, so the subject cannot be reworded; fix-forward = the
  `seed-commit 427c5efb` declaration in `history.policy` (this commit —
  the sanctioned mechanism for verifier-backed bulk-rewrite commits,
  same class as the Stage-B seeds and P34.18/ADR-178), with the scope
  and consequence note recorded in the policy comment itself.
- Read 2 @ `e34dd7c2` (the seed-commit fix-forward): **`blockedOn: CI
  cancel on #236@e34dd7c (composed)`** — "The job was not acquired by
  Runner of type hosted even after multiple attempts" (run
  37364225123): a GitHub hosted-runner acquisition failure, not a check
  failure. The governed flake re-run (B-15) does not cover it —
  `ci_boundary.py` only re-runs `conclusion == failure` results that
  match an allow-listed pattern; a `cancelled` conclusion is never
  re-run, and a fresh head is the fix.
- Read 3 @ `8920c463` (the boundary-record commit): **`blockedOn: CI
  cancel on #236@8920c46 (web)`** — same hosted-runner acquisition
  failure, different job (run 37366260351); the `python` job on this
  head completed green and `docs` passed (the `seed-commit`
  declaration holds — the history guard is green in range). GitHub
  runner capacity, not the change.
- Read 4 @ `a5a0b965` (the second boundary record): **`blockedOn: CI
  cancel on #236@a5a0b96 (python)`** — third consecutive
  acquisition cancel, third different job (run 37368155535). Three
  cancels on three heads = a GitHub hosted-runner capacity incident,
  not the change: on `8920c46` the `python` job ran green and `docs`
  passed end-to-end. The context stops here per G3 (cancelled required
  check → blockedOn → stop until fixed or operator-waived); this
  close-record commit is the next head and its push gives CI a fourth
  try — its result lands in `logs/ci-PLAN-11B-C3.json` and C13's
  closeout re-read settles the boundary either way.

Close record (this commit): records reads 1–4 and fills Closed. The
shared `Closed:` header stays unwritten — C13 owns closeout.

### C4 — 2026-10-05 (rows 279–284)

Started: 2026-10-05T20:48Z (first C4 file write; source: file mtime —
investigation preceded it in the same context) · Closed:
2026-10-05T21:31Z (second boundary re-read confirmed).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a check):

- Rewrite skeletons to full contracts: row 279 (automated traffic
  enforcement layers + aggregate transports, 15), 280 (procurement
  and programme registers, 3), 281 (statutory disclosures I: ALPR
  regimes, 10 — plus the `government_mandated_disclosure`
  generalization NEW-8), 282 (statutory disclosures II-a: UAV + FRT),
  283 (statutory disclosures II-b: CSS, interception, ATE, DHS),
  284 (CCOPS reports, police policies, district self-disclosures, 17).
- Deliverable 8a (ADR-171 outreach-owed placement): applied per row —
  the why-not is recorded on all six (below).

Findings / decisions (per row):

- 279: deps `P35.6;P36.3;P35.15b` + **P36.4 added** (agent-labelled
  correction, in-contract: `deldot_red_light` is consolidated as a
  target under `dot_511_de` — acquisition_plan `AP-T1-003`'s own
  verification column says so — a source row only P36.4 registers;
  chain order already places 277 before 279). Two widen groups ride
  existing flips (`dot_511_dc` licence-match CC-BY-4.0 else
  `camreg_dc_ddot_ate`; `camreg_chicago_il` under the C5 revocation
  clause) as X3-like configuration. New: the two aggregate transports
  (`socrata_aggregate`, `arcgis_outstatistics`) and the
  `enforcement_count {period, count, measure}` predicate in
  `predicates.yaml`; its hosted `vocab_*` registration is recorded as
  a P36.12 wave prerequisite (seam noted for C5 below). ≈ 177k
  claims, 93% aggregates — the volume group (I8 §7.4). Gate: HG-03
  RB-01/RB-06 verbatim; not OM-20; no legs.
- 280: deps `P35.9;P36.6` confirmed (catalog R11-ACQ-05;R11-ACQ-10 —
  the portal `where` support and the `arcgis_outstatistics`
  transport). Three rows (Cook, WA DES public-entity-only, DC OVSJG
  rebate ward × year programme-level); P8-6 drops natural-person
  payees; `D-SOURCES.9-1` (procportal_chicago_il) recorded as a
  different, untouched source. Size S 0.5 run.
- 281: deps `P35.6;P35.15b` confirmed. The row owns the NEW-8
  connector generalization (state/federal publishers, the
  `statutory_report` genre, the technology-literal → SKOS map,
  `[adapters.<publisher>]` dispatch — existing CCOPS fixtures diff 0)
  plus the ten `statrep_*` ALPR-regime rows; `statrep_mn_bca` hosts
  the a-row's UAV target later. WA AGO/MN BCA entries modelled as
  `inventory_entry` assertions, never verified deployments; MN
  literals never geocoded in R11.
- 282 (9a): deps `P36.8`; the S4c split boundary (FEA-04) — the seven
  UAV/FRT candidates (CO FRT + Arvada target, WaTech, Detroit weekly
  index → `usage_count` in `disclosure_use` only, ME/IL UAV, the MN
  UAV target under `statrep_mn_bca`). Shared `r11-disclosures-02`
  batch + gate cell with 283; batch membership idempotent.
- 283 (9b): deps `P36.9a`; the remaining sixteen candidates — WTSC
  index enumeration (~29 city reports), HI/MN interception
  (institution-level counts only; judge/prosecutor appendix names
  never extracted, Tier-2 S5), MD MSP CSS, DE DIAC (`fusion-center`
  slug proposed/pending — coarsest declared, never guessed), Seattle
  SDOT ATE literals, FL/PA ATE statutory, Seattle OIG, DHS PIA
  five-target row + `legis_` SORN document pages (RB-05 CC0-1.0).
  Oversized fixtures (WZSSC 11.9 MB, FL 2.2 MB) land as text extracts
  with recorded sha256 (§5.0 rule).
- 284: deps `P36.8` confirmed (the five CCOPS rows ride 281's
  generalized connector). BL-054 carry landed in-contract: the six
  registered-not-permitted `ccops_*` rows (berkeley, davis, boston,
  baltimore, nashville, grand_rapids) are named on the Wave-B flip
  list alongside the five new rows — still the operator's OP-26
  decision; the fired ADR-080 trigger (b) is a named deliverable —
  evaluated and recorded in the run ledger, reaffirm-as-is or a new
  ADR, never an edit of ADR-080. The `agency_policy` generalization
  collapses the `OkcDocumentConnector` subclasses with a
  byte-stable-fixtures guard (sibling class if the collapse would
  touch the live path). BL-054 itself stays open (the dedicated
  legislative-platform scraper breadth is later-phase).

ADR-171 outreach-owed (deliverable 8a) — why-not recorded per row:

- All six carry a "**recorded why it does not apply**" block: every
  publisher is government/agency-origin (state DOTs, municipal/county
  portals, state oversight and disclosure offices, federal
  DHS/Federal Register pages, school districts, a state statute);
  none is a §6-compact or §22.4–22.5/§35.1 ecosystem project, and no
  row writes, widens or activates a connector for one. Read-side
  notes kept distinct: ER dedupe against OSM/EoF entities is a
  read-time comparison (279/281), and 284's I9b-C040 discovery
  channel is read-only with no registry row (the ACLU-list cell is
  `D-CCOPS.1-2` WONTFIX history). The Stage-0 set (SIG-CHART-033,
  SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013, SIG-GOV-024) stays
  owed under `D-R11-LATER-04` — recorded, never implied satisfied;
  no outside contact made (ADR-171 Decision 3, U-011).

Carried seam for C5 (row 290's author):

- 279's new `enforcement_count` predicate needs a hosted `vocab_*`
  registration before Wave-B's first live emit or P35.14a's closed
  sink quarantines it — recorded in 279's contract as a named
  prerequisite of the wave-activation row's registration step
  (P36.12 is the OM-20 production-write row that owns it). The
  disclosures rows' genre/SKOS config is committed vocab, needing no
  hosted step. C13's review may confirm or re-route.

Local verification (P11, with recorded limits):

- `make docs-check` — green after the projection regen: no
  skeleton/manifest violations on the rewritten rows;
  `check_spec_src` 1,644/1,644 ids; `check_coverage_matrix` 820/820;
  `obligation_events check` green; `audit_current_state` 0 errors
  (9 reconciled conflicts, all pre-existing); build-memory layout and
  ledger-contract gates clean.
- The committed `current` projection digests drifted on this
  context's edits (the six contracts, this ledger); regenerated with
  `current_projection.py generate` — `verify` fresh before commit.
- `python3 docs/build/tools/memory_guard.py all --staged` — green
  before the content commit (protected records appended only).
- `make check` — not re-run this context: no code changed (contracts
  and this ledger only); C2's green at `b1206694` stands and CI is
  the authority. Docker stays wedged (recorded C1).

Boundary (OM-05):

- `blockedOn: CI fail on #236@5877a44 (python): failure — The
  operation was canceled. (run 37372747692)` — a hosted-runner
  capacity cancel (the C3 infrastructure issue recurring), not a red
  result: the job never ran its checks. Re-read once after a short
  wait per policy — still canceled (record
  `logs/ci-PLAN-11B-C4.json`, read 2026-10-05T20:59Z and
  re-read ~T21:11Z, both head-bound on 5877a44).
- The boundary-record push re-triggered CI at 917db14: `python`,
  `composed` and `security` acquired runners and ran **green**;
  `docs` and `web` both failed runner acquisition —
  `blockedOn: CI cancel on #236@917db14 (docs): cancelled — The job
  was not acquired by Runner of type hosted even after multiple
  attempts (run 37374430350)` (web same, same run); re-read once,
  still canceled (log updated in place, head-bound on 917db14).
  Three acquisition cancels so far — the same hosted-runner capacity
  issue as C3's three; infra.
- The second record push re-triggered CI at ec24cab: every job
  acquired a runner and went green —
  `ci: pass #236@ec24cab (python 37376459637; docs 37376459637;
  composed 37376459637; security 37376459637; web 37376459637)` —
  5/5 head-bound, ancestor stack pass, `main: 2de7b50 descends:no
  merges:0` (log updated in place). Confirms the earlier cancels
  were acquisition noise, not content: `docs` (the job that checks
  these contracts) ran green on this head.

Close record (this commit): records all three head-bound reads and
fills Closed at 2026-10-05T21:31Z — work complete; boundary passed
green at ec24cab after three infra cancels (python at 5877a44,
docs + web at 917db14). The shared `Closed:` header stays
unwritten — C13 owns closeout.

### C5 — 2026-10-05 (rows 285–290)

Started: 2026-10-05T~21:40Z (first C5 file write; source: file mtime —
investigation preceded it in the same context) · Closed:
2026-10-05T22:28Z (`date -u`; last C5 criterion = the head-bound CI
pass at `5238ded`).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a/8b Wave-B checks):

- Verified the five C5 drafts against the landed shape and the
  ratified plan rows (deps, gate cells, est_runs → size) and wrote
  the row-290 contract in full: row 285 (P36.11, grant/council/
  procurement documents + bills, 14), 286 (P35.28, officer-naming
  gate default-deny), 287 (P36.15, redaction pipeline), 288
  (P35.66, residential demotion wired), 289 (P36.74, Flock
  portal probe-only, WV-10), 290 (P36.12, Wave-B activation).
- Deliverable 8a/8b for Wave B and the C4 `vocab_*` seam: applied
  and recorded below.

Findings / decisions (per row):

- 285 (P36.11): deps `P35.6` confirmed; gate HG-03 RB-04/RB-06 [A-7]
  verbatim; size S (0.5 run). Twelve new `grant_*`/`agenda_*`/
  `procportal_*`/`legis_*` rows + two `openstates` bill widen
  targets under a `plan_version` bump (no source-row edit, X3-like
  licence-match vs CC0-1.0); `r11-documents-01` membership
  idempotent vs row 284; procured ≠ deployed guard carried
  (`grant_award`/`contract`/`buyer`, never `deployment`);
  `sig-sched-openstates` OR-semantics defect recorded (fix belongs
  to P35.1a lint / P35.1b live sweep). No correction needed.
- 286 (P35.28): deps empty → `nothing (chain order)` confirmed;
  gate `none`; size M (1.0). The publication-path officer-naming
  gate: `evaluate_officer_naming` gains a persisted two-reviewer
  concurrence record (append-only) that the export/web dossier
  path reads — no record → withheld, whatever the jurisdiction
  rule says; `web_dossier.py`'s `Approving official` fixture and
  `publication.test.ts` assert the record precondition (fixed,
  never loosened); SIG-PUB-009/010 carve-outs stand; WV-03/ADR-163
  boundary recorded (the naming concurrence stands unamended).
- 287 (P36.15): deps empty → `nothing (chain order)` confirmed;
  gate `none`; size M (1.0). The redaction pipeline end to end —
  `redact()` gains a production caller, the derivative is a new
  OCFL capture (`parent_capture_id`, method, version), the
  review record is append-only and required (its absence is a
  loud failure), the removal is text-layer-irreversible
  (SIG-PUB-016's extraction test), and every excerpt surface
  (tiers, API, dossier/export) serves the derivative where one
  exists. The P36.74 in-memory-before-persist screen is a
  distinct, separately-binding path — recorded.
- 288 (P35.66): deps `P35.14b` confirmed; gate `none`; size M (1.0;
  `live_stage: none (ships with the next export/release)` carried
  verbatim). TS-07 wiring of `demote_for_residential_parcel` —
  flag producer (declared parcel signal; screened vs unscreened
  distinguishable, never silent-clean), demotion at every
  `sensitivity_class` stamping site, and the publish-path refusal
  (no residential candidate at any precision, ever). The
  parcel-signal input is the honest open design point — bounded
  in-contract, concrete source named at build time. `live:` edge
  lands in 290.
- 289 (P36.74): deps `P35.6;P35.14b;P35.15b;P36.1a(S2);P35.28;
  P36.15;P35.66;P34.49;P35.38a` confirmed verbatim; gate WV-10
  [S6R-01] + D3-Q3 [A-17] = b verbatim + HG-03 flip note; size S
  (0.5 run — the S6c probe-only sizing, corrected from the plan
  note's stale `size M` lead token: the same cell records
  `sized down 1.0 -> 0.5 (size S)`). Probe-only per ADR-188:
  one polite request per known portal per run, stop-and-record
  on any challenge, `sig.probe-run/1` records, CC BY-SA 4.0
  compartment, aggregate-only emission, in-memory Part VIII
  screen before persistence, expected yield ≈ 0. The
  no-circumvention test and the ADR-188 revisit triggers are
  wired in-contract.
- 290 (P36.12): written in full from the skeleton — the Wave-B
  activation row. Deps carried verbatim (P35.11 edge is
  SEQUENCE-only per the S4c note; P36.9a rides through P36.9b).
  Gate: ING-GO-B verbatim at GATE-G4 else in-ticket pause;
  OM-20 `never pre-authorised` carried. Window verbatim:
  10-26 → 11-05 14:00–20:00Z, one family per day (ACQ-11 +
  ACQ-15 may share), never with the 10-29T12:00Z peel-on fire,
  no release cut (P36.72b's Class S). Legs enumerated L0–L10:
  opening (pre-state, AR-2 backup, image roll, seven paused
  batch jobs, the `enforcement_count` hosted `vocab_*`
  registration — C4's seam, carried), eight ACQ-08…15
  family-days in ticket order, the Flock probe leg, and the
  materialize + coverage-delta + resume closing leg. The
  operator's OP-26 flip-list execution is recorded per leg —
  the row never flips.
- **Sizing flag (contract deliverable 4 input for C13):**
  P36.12 is recorded oversized in the contract — ten family
  legs + opening + materialize over an 11-day window, plan
  `leg_runs 4.5` vs `est_runs 1.0`, ≈ 89 new sources + 7 widen
  targets + ≈ 917 probe targets each with per-source I8 §7.7
  verification. The declared read set (~204 KB ≈ 68k tokens ÷3)
  fits, but the accumulated live working set across ~10 leg-days
  is the overflow the plan itself flags (S6 A-15: "split … at the
  PLAN row's Phase-4 review"; S6c S6R-15: "likely to fire").
  Contracted whole with the flag recorded; a candidate seam
  (L0 + ACQ-08…12 / ACQ-13…15 + probe + materialize, suffix-letter
  rows under the banner) is noted for C13, which owns the split
  decision — nothing pre-split here.

ADR-171 outreach-owed (deliverable 8a) — per row:

- 285/286/287/288 each carry a "**recorded why it does not
  apply**" block: no §6-compact or §22.4–22.5/§35.1
  ecosystem-project connector is written, widened or activated —
  285's fourteen rows are government-published documents (the
  `openstates` targets ride that reviewed source's envelope;
  OpenStates is not a compact-table project); 286 is
  publication-path gate wiring; 287 is evidence-store pipeline
  wiring; 288 is policy wiring inside emit/publish paths.
- 289 records the check honestly: the probe set derives from the
  Eyes on Flock inventory but the fetches hit **Flock-hosted
  vendor pages** (a commercial platform, not an ecosystem
  project); Eyes on Flock stays a read-side mirror, its connector
  unchanged and already `ingestion_permitted`.
- 290 records the owed list per the P35.11 wave-activation
  precedent — the flip list contains no compact/ecosystem-project
  connector, and the probe leg touches the §22.5 Eyes on Flock
  relationship read-side only — so the Stage-0 set
  (SIG-CHART-033, SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013,
  SIG-GOV-024) is recorded verbatim as **owed — unmet at launch**
  under `D-R11-LATER-04`. No outside contact made or implied
  (ADR-171 Decision 3, U-011).

Tribal S8 (deliverable 8b) — why-not for Wave B:

- `AP-T2-201` / `AP-T2-210` already landed at **P35.11** (C2,
  ADR-185 screened lane); Wave B's flip list carries no tribal
  candidate and exercises no S8 lane. `AP-T2-093` stays
  `D-R11-LATER-09` (not IND-TRIBAL). `CG-LATER-…-i7-new-6` stays
  OPEN. Recorded in 290's contract.

Local verification (P11, with recorded limits):

- `make docs-check` — (filled at commit: green after the
  projection regen; no skeleton/manifest violations on the
  rewritten rows; `check_spec_src` 1,644/1,644;
  `check_coverage_matrix` 820/820; `obligation_events check`
  green).
- The committed `current` projection digests drifted on this
  context's edits (the row-290 contract, this ledger);
  regenerated with `current_projection.py generate` — `verify`
  fresh before commit.
- `python3 docs/build/tools/memory_guard.py all --staged` — green
  before the content commit (protected records appended only).
- `make check` — not re-run this context: no code changed
  (contracts and this ledger only); C2's green stands and CI is
  the authority. Docker stays wedged (recorded C1).

Boundary (OM-05):

- Read @ `5238ded9` (content commit): **`ci: pass #236@5238ded`**
  — python/docs/composed/security/web 5/5 head-bound (run
  37381411791; stack pass; `main` 2de7b50 descends:no merges:0
  open-other:6; log `docs/build/logs/ci-PLAN-11B-C5.json`,
  gitignored, read 2026-10-05T~22:2xZ). Green on the first head —
  the C3/C4 hosted-runner acquisition cancels did not recur. This
  boundary-record commit's own head-bound re-read lands in the
  same log; C13 reads the boundary again at closeout.

Close record (this commit): records the head-bound read and fills
Closed at 2026-10-05T22:28Z — work complete; boundary green on the
first head. The shared `Closed:` header stays unwritten — C13
owns closeout.

### C6 — 2026-10-05 (rows 291–298)

Started: 2026-10-05T~21:5xZ (first C6 file write; source: file mtime —
investigation preceded it in the same context) · Closed:
2026-10-05T23:19Z (`date -u`; last C6 criterion = the head-bound CI
pass at `0dc6bc1`).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a ADR-171 checks):

- Rewrote all eight skeletons in place to the landed full-contract
  shape: row 291 (fleet hygiene — cruft jobs, AR cleanup, dispatcher
  consolidation), 292 (production-truth probes + sentinel scan),
  293 (ops runbook + stale ops doc fixes), 294 (release identity v2
  + clock guards), 295 (provenance stamp / release.json / headers),
  296 (geometry defects at ingest), 297 (jurisdiction registry +
  boundary pack), 298 (declared jurisdiction scheme).

Findings / decisions (per row):

- 291 (fleet hygiene): deps `P35.1a` confirmed; gate carried verbatim
  (OM-20 conditional + G1-TRIM [B-13] `a` — the operator's verbatim
  consolidation answer); production-write mutations enumerated (six
  named cruft-job deletions, the AR cleanup policy, four cron
  reconciles, the `sig-alerts` disposition, the hourly `due`
  dispatcher + ~79-trigger retirement). Plan-note corrections
  recorded in-contract: "owns ADR-174" and "sole owner of the cron
  lint" are the copied unsplit R11-OPS-03 scope — after the a/b
  split the ADR + lint mechanism are P35.1a's; this row is the
  sweep/consolidation half. "reingest schedule removal" resolves to
  P35.1a's repo-side removal + the operator's QA-8 click; this row
  verifies the end state. SIG-SEC-008 carried as the shared a/b
  owner (this row the sweep half).
- **Sizing flag (contract deliverable 4 input for C13):** row 291 is
  recorded oversized — contracted whole, never pre-split. Eight
  enumerated live legs (pre-state+backup → keep-list guards → AR
  policy dry-run → deletions → sig-alerts → dispatcher deploy +
  consolidation → post-sweep live-diff + cost record); the declared
  read set (~77k tokens ÷3) fits but the accumulated working set —
  a new dispatcher mechanism + a fleet-wide destructive sweep +
  live-diff verification across ~8 mutation groups — overflows a
  single ≤ 1-run context; est_runs 1.0 understates it. Candidate
  seam recorded (a-leg = the pure sweep legs 1–6; b-leg = the
  dispatcher build + consolidation + closing proof), suffix-letter
  rows under the banner if C13 splits — **C13 owns the Phase-4
  split decision; nothing here pre-splits.**
- 292 (probes + sentinel scan): deps `P34.44b;P34.4` confirmed; no
  gate; size M. The probe registry declares every G10 probe's
  trigger points (PR / candidate / publish / schedule / tail) and
  reuses the landed `sig.probe-run/1` writer — placed, not
  re-implemented; extends `tail_probe_sweep.toml`'s ADR-199
  contract, never forks it. Sentinel list, live-claim ≤ 24 h
  citation binding, and the no-vacuous-probe rule (SIG-ENG-042)
  wired; owner reqs SIG-MEM-011 + SIG-OPS-011 + SIG-OPS-012 stamped.
- 293 (ops runbook): deps `nothing (chain order)` confirmed; no gate;
  size M. **SIG-SEC-009 ownership asserted in-contract** (the seam
  requirement): the contract map's `SIG-OPS-010 SIG-SEC-009` binding
  resolves to a committed, value-less secret register (owner,
  consumer, last-rotation — `unknown` where unevidenced) + the
  §Secret rotation procedure — never claiming a rotation that
  didn't happen. Four stale-doc fixes named (ops/gcp §DECISION +
  $0 table superseded, "WORM" wording, OPERATIONAL_READINESS
  scheduling row, GCP_DEPLOYMENT drill caveat); every command
  verified against the tree.
- 294 (release identity v2): deps `P34.22b;P34.23` confirmed; gate
  `D-G3-1/D-G3-2 [B-9] = yes` verbatim (Option-1: calendar-date
  label + hash-suffixed export id). Descriptor v2
  `sig.publication-descriptor/2`, label registry lock, NEW-1
  export-id fix, §3.3 clock guards, promotion refusals, ADR-161
  extending ADR-132 (B-9 quoted verbatim; `boundaries_root` recorded
  as row 297's K4 input); owner reqs SIG-REL-001/002/003 stamped.
- 295 (provenance stamp): deps `P35.12;P34.17` confirmed; no gate;
  live stage `publish (next republish)` carried verbatim — the stamp
  machinery merges here, the republish row's leg exercises it live.
  The interim-text constraint binds: the stamp never emits
  "belief-pinned" until the descriptor's posture is true; owner req
  SIG-REL-009 stamped.
- 296 (geometry defects): deps `nothing (chain order)` confirmed;
  OM-20 conditional verbatim (correction claims). Per-target
  `axis_order` + three ingest detectors (axis-swap / null-island /
  sign-flip) + the seven F-322 named defects corrected by append-only
  claims + portal `row_count` distinct-or-disclosed. Recorded
  correction: no §56 Owner names P35.16 — the owned finding is
  F-322 (S1) per the plan row's S0/S1 column; SIG-GEO-008 /
  SIG-IDENT-004 cited as the standards served.
- 297 (jurisdiction registry): deps `P35.12` confirmed; gate cell
  verbatim (OM-20 conditional + D-K4-1 [A-18] `yes` + D-K4-2/D-K4-4
  [B-22] `as recommended`). The A-18 sequence is load-bearing in the
  contract: terms-text capture → repo-side rows (`ingestion_permitted`
  stays false) → **in-ticket pause for the operator's HG-03 flips
  (OP-26 — never performed or claimed here)** → hosted OCFL capture →
  registry/pack → `boundaries_root` → ADR-160 (ADR-079/ADR-122 gain
  `Revisited by ADR-160` status lines — appended, never body-edited).
  Owned findings F-44 + F-321 recorded; D-K4-1/2/4 named.
- 298 (declared scheme): deps `P35.17;P34.24b` confirmed; no gate;
  size S (0.5 run — honest budget). `candidate_identifier` →
  `value_json` {scheme, value} persistence (K4 §3.2 — text value +
  digest unchanged); scheme-keyed shaping replaces the bare-value
  `_slugify` site; legacy claims get `declared_scheme_from_config@
  <sha256>`; the no-mix + grep guards. Recorded correction: no §56
  Owner names P35.18 — SIG-IDENT-006/005 cited as the model it
  enforces; hosted effect via the next ingest, no backfill.

ADR-171 outreach-owed (deliverable 8a) — per row:

- All eight rows carry "**recorded why it does not apply**" blocks:
  291 is GCP fleet/scheduler hygiene; 292 is verification machinery;
  293 is internal ops docs; 294/295 are release-identity/provenance
  machinery; 296 corrects claims on existing targets (no new
  connector); 297 is agency/data-path source acquisition under
  HG-03 (terms capture is a read of published text — never
  contact); 298 is claim-shaping code. None writes, widens or
  activates a §6-compact / §22.4–22.5 / §35.1 ecosystem connector.
  The Stage-0 set (SIG-CHART-033, SIG-INGEST-029/030a,
  SIG-CONTRIB-012/012a/013, SIG-GOV-024) stays owed — unmet at
  launch — under `D-R11-LATER-04` (recorded verbatim on each row).
  No outside contact made or implied (ADR-171 Decision 3, U-011).

Local verification (P11, with recorded limits):

- `make docs-check` — green on content checks before the projection
  regen (manifest=509/509, deferrals=156/156, ledger=20/20,
  tickets=507/507, coverage=820/820, adrs=191/191;
  `obligation_events check` green — 636 events / 26 transitions;
  `--require-reconciled` 0 diagnostic failures; the 9 conflict rows
  are pre-existing, covered by reconciliations.json). The eight
  contract digests drifted the projection (expected) — regenerated
  with `current_projection.py generate`, `verify` fresh before this
  commit.
- `python3 docs/build/tools/memory_guard.py all --staged` — green
  before the content commit (0 violations, 1234 items; protected
  records appended only).
- `make check` — not re-run this context: no code changed (contracts
  + this ledger + projection only); the C5 green stands and CI is
  the authority. Docker stays wedged (recorded C1).

Boundary (OM-05):

- Read @ `0dc6bc1d` (content + ledger head): **`ci: pass
  #236@0dc6bc1`** — python/docs/composed/security/web 5/5 head-bound
  (run 37386655921; stack pass; `main` 2de7b50 descends:no merges:0
  open-other:6; log `docs/build/logs/ci-PLAN-11B-C6.json`,
  gitignored, read 2026-10-05T~23:1xZ). Green on the first head —
  the C3/C4 hosted-runner acquisition cancels did not recur. This
  boundary-record commit's own head-bound re-read lands in the same
  log; C13 reads the boundary again at closeout.

Close record (this commit): records the head-bound read and fills
Closed at 2026-10-05T23:19Z — work complete; boundary green on the
first head. The shared `Closed:` header stays unwritten — C13
owns closeout.

### C7 — 2026-10-06 (rows 299–306)

Started: 2026-10-06T~01:4xZ (first C7 file write; source: file mtime —
investigation preceded it in the same context) · Closed:
2026-10-06T02:40Z (`date -u`; last C7 criterion = the head-bound CI
pass at `5479f608` after the advisory-gate fix-forward).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a ADR-171 checks):

- Rewrote all eight skeletons in place to the landed full-contract
  shape: row 299 (placement engine `placement@1`), 300 (PKG-10
  split a — per-dossier provenance + unclamped coverage), 301
  (PKG-10 split b — freshness classes + map-table suppression),
  302 (truthful claim identity — volatile fields leave the
  digest), 303 (truthful subject keys + append-only re-keying),
  304 (declared lineage, id namespaces, independence), 305 (roles
  and time backend — operator vs publisher, dated edges,
  supersession), 306 (resolver input truth — valid time,
  directness, tolerance-aware dissent).

Findings / decisions (per row):

- 299 (placement engine): deps `P35.17;P35.18;P35.16(S2)` confirmed —
  the S2 edge to P35.16 is ordering-only (CF-14: corrected axis order
  lands before placement reads points; chain order already places 296
  before 299 — recorded, no plan change). No gate (`none`); not an
  OM-20 row; output arrives with the next export/release (ADR-092
  compute-on-read — a no-spine-write guard test is contracted).
  R1–R8 ruleset carried verbatim from K4 §3.3 (located wins, R3
  repair heuristics fall back to declared, unplaced is a quality
  state never a jurisdiction). Recorded correction: no §56 Owner
  names P35.19 — the owned findings are F-04/F-135/F-324/F-469/F-529
  per the plan row's S0/S1 column; SIG-IDENT-004/005/006 +
  SIG-ONTO-010/011 + SIG-RECON-058 + SIG-UI-048 + SIG-GEO-001 cited;
  K4's draft SIG-JUR-D03/D04/D05 named as design refs (final ids are
  PLAN-11C's). I8's name→key attribution named out-of-scope (R8 is
  fixture-only).
- 300 (PKG-10 a): dep `P35.18` confirmed; no gate; L-split a budget
  recorded. Per-dossier/per-surface provenance emission (ED-41 — the
  `provenance ?? getSiteProvenance()` fallback dies, absent rows
  render "site-wide" explicitly) + the unclamped coverage numerator
  (ED-42 — resolved+publishable+non-conflicted, `min(resolved,
  claimed)` clamp removed, exclusions disclosed; F-134 owned).
  Recorded plan-row note: S0/S1 lists F-134 on both splits — F-134
  is this a-half's finding; the b-half serves ED-43/ED-44's
  component findings. Recorded seam (agent-labelled): K4 §9's P9
  note ("per-dossier 'How we know this' moves to K5 DSRC-01")
  resolves data-vs-presentation — this row lands the derivation +
  emitted rows; DSRC-01 (P35.44, row 323) owns the contribution
  export + presentation. `number_trace.csv` is the oracle —
  re-derive, never edit.
- 301 (PKG-10 b): dep `P35.20a` confirmed; no gate; L-split b.
  `staleness_not_evaluable` emitted + rendered (never "ok"/"stale 0"
  for a non-evaluable source); per-source volatility classes as a
  declared registry field (SIG-METRIC-006 + ADR-104(e) basis —
  declared, never inferred); non-site freshness rows (the 41
  evidence-bearing sources without rows); one suppression function
  feeding figure + accessible table + SVG titles (ED-44 — the
  601-cell / 40,913-record "Devices"-header leak); cell-to-
  jurisdiction reconciliation consuming P35.19's keys where landed.
  Owned-finding note mirrors row 300's (F-134 is the a-half's; this
  half serves C3 NEW-8/NEW-16/NEW-21 + F-08's freshness clause).
  GQ-15's freshness clause served, not flipped.
- 302 (claim identity): dep `P34.44b` confirmed (the claim-minting-
  diff harness is the parity oracle). OM-20 conditional verbatim;
  live stage `production write — re-ingest on next scheduled runs`
  verbatim + window `camera-registry batches days 6–13` verbatim.
  Recorded note: the "write" is **new minting under the new
  identity** — CP-1's no-mass-re-mint forbids touching stored rows;
  recorded so the legs are never read as a backfill. Volatile fields
  leave `digest_base` → evidence binding; `value_json`
  normalisation + `payload_version`; `obs`/`ref` identity split;
  one identity function emitter-side and sink-side. F-504 owned;
  SIG-INGEST-003/004 + ADR-159 cited; SIG-EPIS-009 recorded as
  context (P35.25 owns its binding). S6 A-20: `/status/` API-basis
  notice contracted; **no `live:` edge to P35.57** (the plan row's
  verbatim note).
- 303 (subject keys): dep `P35.22` confirmed (L3 S1 edge). OM-20
  conditional verbatim; live stage `production write — hosted
  re-key run` verbatim; window AR-3 + AR-2 verbatim. Pinned
  per-target field sets + tenant/state scope + `key_version`; the
  5,278-collided-subject count is re-derived at run time
  (discrepancy recorded, never assumed); re-keying is appended
  correction claims — a no-update/delete test is contracted.
  F-506 + F-518 owned. S6 A-20 disclosure; no `live:` edge to
  P35.57.
- 304 (lineage/namespaces/independence): dep `P35.24` confirmed (S2
  edge). OM-20 conditional; live stage `registry change +
  rematerialize` verbatim — the writes are additive registry
  metadata + materialization appends (recorded note). **SIG-CONF-014
  is the family's only §56 Owner — stamped**; SIG-EPIS-029/009 +
  SIG-IDENT-005 cited. `undeclared` is first-class, never
  `independent`-by-default; a mirror never corroborates its
  original; `derived_from_claim_ids` persisted at emit. ODbL
  compartment lineage recorded as a licence-metadata distinction,
  not this row's connector lineage. S6 A-20; no `live:` edge to
  P35.57.
- 305 (roles and time): dep `P35.14b` confirmed. OM-20 conditional;
  live stage `re-ingest EFF/OSM + rematerialize edges` verbatim —
  re-ingest inside **existing** ingestion permission (no rights
  flip; recorded). Role vocabulary + valid-time + `undated`
  first-class (epoch-zero rejected) + correction-claim supersession
  + explicit-unknown operator (SIG-ONTO-028). F-521 owned;
  SIG-TRUST-003 + GQ-07/GQ-15 cited/served. **Recorded plan-row
  notes:** the cell carries **no** S6 A-20 clause (unlike its
  neighbours) — carried as-is, with the contract still recording
  the disclosure posture; the live legs' scope is EFF + OSM only —
  other sources' stale role edges correct on their own next runs
  (recorded, never silently extended); the OSM leg stays inside the
  ODbL compartment.
- 306 (resolver input truth): deps `P35.25;P35.14b` confirmed. OM-20
  conditional; live stage `rematerialize` verbatim. Valid-time-aware
  candidate selection (non-overlap = succession, not conflict);
  directness reads declared lineage; tolerance-aware dissent emits
  `contested` (persisted signal) vs real conflict; the four-state
  vocabulary (`uncontested`/`insufficient`/`resolved_conflict`/
  `unresolved_conflict`) preserved exactly — `contested` is a
  signal, never a fifth state (SIG-STORE-015's vocabulary not
  extended). F-519 owned; SIG-RECON-053 + SIG-STORE-015 cited.
  Undeclared tolerance → candidate conflict (recorded default,
  never a guessed tolerance). S6 A-20; no `live:` edge to P35.57.

ADR-171 outreach-owed (deliverable 8a) — per row:

- All eight rows carry "**recorded why it does not apply**" blocks:
  299 is an export-time computation over captured evidence + the
  committed boundary pack; 300/301 correct export/inference/web
  derivations (the volatility field is registry metadata, not a
  connector change); 302/303 change claim/subject keying (the claim
  path itself, not a connector surface); 304 declares lineage on
  existing sources + back-populates spine fields; 305 re-ingests
  **already-permitted** sources under corrected emitters — a
  data-lineage act, not a connector act (no posture change, no new
  source, no compact touched — the OSMUID contribution-back caveat
  is recorded in-contract: those obligations stay exactly where
  they are if the OSM evidence path exercises that seam); 306 is
  resolver logic + materialization. None writes, widens or
  activates a §6-compact / §22.4–22.5 / §35.1 ecosystem connector.
  The Stage-0 set (SIG-CHART-033, SIG-INGEST-029/030a,
  SIG-CONTRIB-012/012a/013, SIG-GOV-024) stays owed — unmet at
  launch — under `D-R11-LATER-04` (recorded verbatim on each row).
  No outside contact made or implied (ADR-171 Decision 3, U-011).

Local verification (P11, with recorded limits):

- `make docs-check` — recorded below after the projection regen
  (the eight contract digests drift the projection — regenerated
  with `current_projection.py generate`, `verify` fresh before the
  commit).
- `python3 docs/build/tools/memory_guard.py all --staged` — run
  before the content commit (protected records appended only).
- `make check` — not re-run this context: no code changed (contracts
  + this ledger + projection only); CI is the authority. Docker
  stays wedged (recorded C1).

Boundary (OM-05):

- First read @ `2c2ef14a` (content head): **`blockedOn` — the
  `security` job's npm advisory gate blocked on a NEW advisory,
  source-map-js GHSA-68fv-2mgg-jv7q (high, event-loop DoS via
  indexed source-map section offsets; run 37404414780)** — a
  time-varying advisory-feed finding, not the docs change (the
  commit touched contracts + ledger + projection only).
  Fix-forward (red→green, honest fix over allow-list): upstream's
  1.2.2 (published 2026-09-30) patches exactly this advisory;
  `web/package-lock.json` bumped 1.2.1→1.2.2 as a surgical edit
  (every parent range `^1.0.1`/`^1.2.1` admits it; `npm ls`
  resolves cleanly; `npm_audit_gate.sh` locally reports
  `blocked=0` — the remaining candidate is the allowed
  http-cache-semantics entry). Committed as `5479f608`.
- Re-read @ `5479f608` (fix-forward head): **`ci: pass
  #236@5479f60` — python/docs/composed/security/web 5/5
  head-bound (run 37404618425; stack pass; `main` 2de7b50
  descends:no merges:0 open-other:6; log
  `docs/build/logs/ci-PLAN-11B-C7.json`, gitignored, read
  2026-10-06T~02:3xZ).** Green on the second head — the advisory
  gate cleared with the bump, all five required jobs green.

Close record (this commit): records the head-bound read and fills
Closed at 2026-10-06T02:40Z — work complete; boundary green on
the second head after the recorded fix-forward. The shared
`Closed:` header stays unwritten — C13 owns closeout.

### C8 — 2026-10-06 (rows 307–314)

Started: 2026-10-06T~03:0xZ (first C8 file write; source: file mtime —
investigation preceded it in the same context) · Closed:
2026-10-06T03:25Z (`date -u`; last C8 criterion = the head-bound CI
pass at `acde44ec` — first head).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a ADR-171 checks):

- Rewrote all eight skeletons in place to the landed full-contract
  shape: row 307 (the shared label/slug/hash module), 308
  (`/network/` labels, dates and evidence — export side), 309
  (transparency scrub + fail-closed publish secret gate +
  capture-tier derivation), 310 (`ingest_run_report` table, writer
  and WORM backfill — the OM-20 conditional hosted change), 311
  (run/capture/issue export + the auto issue classes + the
  cadence/freshness inputs), 312 (run telemetry `per_fetch` +
  upstream count + the SIG-INGEST-004 binding-version test — the
  MUST carried, not weakened), 313 (registry redistribution lanes +
  `v_transparency_source` + source metadata export), 314 (the
  `withBase()` helper + CI containment check).

Findings / decisions (per row):

- 307 (shared labels): no plan deps; gate `D-K2-1 [A-10] = b + c`
  carried verbatim (round 4, 2026-10-01T04:07:45Z — the label half
  of ADR-159); not an OM-20 row. One derivation module
  (`policy/src/policy/labels.py`) + `sig.entity-label/1` per
  compartment; label_basis closed set; Crockford-base32 7-char
  hashes frozen; the Part VIII person-name screen runs over literal
  parties too. Recorded correction: no §56 Owner names P35.29 —
  the skeleton's UXR-17 is a draft ref (PLAN-11C numbers the UX
  family), recorded not stamped. Soft prerequisites recorded as
  ordering-only: P35.14b typing (kind parsed from the key
  meanwhile) + the `{place}` fallback ("place not recorded" until
  the jurisdiction rows land).
- 308 (`/network/`): deps `P35.29;P34.15` confirmed; same A-10
  answer carried verbatim. Node labels from 307's module (never
  the entity id — F-106/F-420); edges carry predicate + observed
  date + date kind + source + currency + claim ids (draft
  SIG-EXPORT-D21 stays a ref); degree is a node attribute, never
  an edge (SIG-INGEST-043c); 1970 → "undated"; no new JS — the
  island at its current ceiling renders the richer JSON. No §56
  Owner; owned findings F-106/F-420/F-421 per the S0/S1 column.
- 309 (scrub + gate + tier): dep `P34.25` confirmed; no gate; not
  an OM-20 row. `policy/src/policy/transparency.py` lands the J4
  S-1…S-14 rules verbatim as code; the publish secret gate wires
  into the single allow-listed publish path and fails closed (one
  secret-shaped value aborts — no override flag); `storage_tier`
  derives from lane + Part VIII class (F-400 — the hard-coded
  `public` defect), unknown → `sealed`. **SIG-TRANSP-022 is the
  §56.10 Owner — stamped** (the scrub-gate requirement); F-400
  owned; SIG-TRANSP-020 also (the raw-ok lane machinery — the
  requirement's owner is P37.36). The interim lane basis (the
  rights record, until row 313's toml fields land) is recorded.
- 310 (`ingest_run_report`): dep `P34.24b` confirmed. **The OM-20
  conditional carried verbatim** (`named mutation → pre-authorised
  only if the GATE-G4 list names this row; otherwise in-ticket
  pause`); live stage `production write (hosted DB change)` and
  window `AR-3 + AR-2` verbatim; one leg + the header re-run
  prompt. A new append-only change (immutability trigger, grants —
  the `ingest_run_completion` pattern; `sqitch.plan` lines 44–52
  never touched); `scheduled-ingest` writes a row per execution;
  `sig-ops backfill-run-reports` mints the 387 WORM rows
  (re-derived, never assumed) + the K10 C-14 unmatched and
  repo-record rows (`run_id` NULL + `link_basis` + `clock_basis`);
  `backfilled_from` uniqueness → `+0` re-run. No §56 Owner;
  SIG-TRANSP-036 also (its owner P36.46 renders the history).
  `per_fetch` is a column here — the writer is row 312's.
- 311 (run/capture/issue export): deps `P35.31;P35.32` confirmed;
  gate `D-J3-2 [B-19] = yes` verbatim (robots disregard disclosed
  as host + count + the GL-GATE-08 reference — never per-request
  detail). `v_transparency_run`/`v_transparency_capture`
  explicit-column views (`sig_export` only); `runs.jsonl`/
  `captures.jsonl`/`issues.jsonl` through 309's scrub; the closed
  issue-class vocabulary (incl. `zero_records` — silent success is
  an issue, SIG-ENG-021); the K9 C-4…C-7 + K10 C-13 amendments
  (cadence rule on release pages, `one_time_load`,
  `run_record_missing`, the two "last change" columns,
  execution-keyed rows, shared-run values never the execution's).
  No §56 Owner; SIG-TRANSP-006 also (P36.46 renders the log). The
  freshness verdict function itself is recorded as P35.41's (row
  320) — this row lands its inputs.
- 312 (telemetry + binding-version test): no deps; no gate. **The
  C8 seam:** the SEED-12b carry is recorded — SIG-INGEST-004's
  drafted weakening amendment was withheld (G.7.5), so the MUST
  stands: the contract lands the binding-version test plus the
  withheld amendment's own disposition (add `extractor_version`/
  `normalizer_version` to the logical identity for **new minting
  only** — never a re-mint — or record the residual gap `D-…`
  with the test pinned to the posture; the requirement text is
  never touched). **SIG-CONF-009 is the §56.7 Owner — stamped**;
  per-fetch fields + the upstream-count pair + the closed
  reason vocabulary (`unexplained` recorded unexplained); the
  >1 % fail rule binds where P34.44a/b's check machinery reads it
  (the `Also:` pair). `/v1/changes` recorded out (P36.67). Soft
  edge to 310's `per_fetch` column recorded as ordering-only.
- 313 (registry lanes + source metadata): deps
  `P35.31;P34.17;P34.21b` confirmed; gates `D-J3-1 [B-19]` (raw-ok
  only, after the Part VIII byte screen) and `D-J3-5 [B-19] = no`
  carried verbatim. `[redistribution]` fields per source carrying
  spec §5.7's verbatim wording (ADR-183; the G3 C-3/C-6
  instruction — the same field, never a new column);
  `v_transparency_source` explicit-column view; `sources.json`/
  `counts.json` through the scrub; `no_upstream_url_recorded` and
  `review_needed` honest defaults. No §56 Owner; SIG-TRANSP-002 +
  SIG-TRANSP-035 both also (owners P35.40 and P37.36 — this row
  lands the vocabulary + metadata they read). The lane field
  replaces 309's interim rights-record basis (recorded).
- 314 (`withBase()`): no deps; no gate; S budget (0.5 run). NEW
  (S4c) per FEA-06/COV-08 — the helper precedes its consumers
  (P35.36, P35.42, all 11C pages); the CI containment check bounds
  G3 NEW-6's counted 85 root-absolute path sites in 36 files (0
  `BASE_URL` uses) — the count may only shrink (P36.66a's sweep),
  never grow. No §56 Owner; SIG-REL-008 also (owner P36.66b —
  P34.34a records "CI check P35.65"). The legacy sweep is
  explicitly P36.66a's, not this row's.

ADR-171 outreach-owed (deliverable 8a) — per row:

- All eight rows carry "**recorded why it does not apply**" blocks:
  307/308 derive labels and network fields over captured claims +
  committed config; 309 is a policy module + a publish-path gate;
  310 adds a database relation + writers over the run-record path;
  311/313 are views + export artifacts over already-captured or
  committed records (313's lane fields are registry metadata, not
  connector posture); 312 adds run-record fields + an identity
  test; 314 is a web helper + a repo check. None writes, widens or
  activates a §6-compact / §22.4–22.5 / §35.1 ecosystem connector.
  The Stage-0 set (SIG-CHART-033, SIG-INGEST-029/030a,
  SIG-CONTRIB-012/012a/013, SIG-GOV-024) stays owed — unmet at
  launch — under `D-R11-LATER-04` (recorded verbatim on each row).
  No outside contact made or implied (ADR-171 Decision 3, U-011).

Local verification (P11, with recorded limits):

- `make docs-check` — recorded below after the projection regen
  (the eight contract digests drift the projection — regenerated
  with `current_projection.py generate`, `verify` fresh before the
  commit).
- `python3 docs/build/tools/memory_guard.py all --staged` — run
  before the content commit (protected records appended only).
- `make check` — not re-run this context: no code changed (contracts
  + this ledger + projection only); CI is the authority. Docker
  stays wedged (recorded C1).

Boundary (OM-05):

- Read @ `acde44ec` (content+ledger head): **`ci: pass
  #236@acde44e (python 37407963600; docs 37407963600; composed
  37407963600; security 37407963600; web 37407963600) · stack:
  #235 #234 #233 #232 #231 #230 #229 #228 #227 #226 #225 #224
  #223 #221 #220 #219 #218 #217 #216 #214 #213 #211 #210 #209
  #208 #207 #205 #204 #203 #202 #201 #200 #199 #198 #197 #196
  #195 #193 #192 pass · main: 2de7b50 descends:no merges:0
  open-other:6` (log `docs/build/logs/ci-PLAN-11B-C8.json`,
  gitignored, read 2026-10-06T~03:2xZ).** Green on the first head —
  all five required jobs head-bound.

Close record (this commit): records the head-bound read and fills
Closed at 2026-10-06T03:25Z — work complete; boundary green on
the first head. The shared `Closed:` header stays
unwritten — C13 owns closeout.

### C9 — 2026-10-06 (rows 315–322)

Started: 2026-10-06T~03:3xZ (first C9 file write; source: file mtime —
investigation preceded it in the same context; this context resumed
from a summary, the seven earlier file writes 03:34–03:45Z stand)
· Closed: 2026-10-06T04:13Z (`date -u`; last C9 criterion = the
head-bound CI pass at `3670b7e9` — first head).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a ADR-171 checks):

- Rewrote all eight skeletons in place to the landed full-contract
  shape: row 315 (per-compartment `statements`/`record_claims.jsonl`
  + the shared `<ProvenancePanel>` data contract + S-6-gated
  `upstream_href`), 316 (figure-to-evidence pointers — every material
  public number a Figure with artifact/pointer/definition/href +
  the raw-numeral build check), 317 (the IRI-base half — new release
  IRIs on `surveillancegraph.org`, published IRIs immutable, the
  append-only alias map + compat note), 318 (ontology/exporter data
  dictionary + per-resource Table Schema + DCAT 3 + PROV-O as linked
  files), 319 (source = registry row + the six-state lifecycle
  partition + named count predicates + the anomaly list), 320
  (freshness semantics v2 — the one shared verdict function + the
  two clocks + the two change dates), 321 (the citation block +
  release ID on every page + edge-side legacy selector handling),
  322 (the watch producer v1 — `EXPORT_QUERIES` reads +
  `exports/watch.py` derivation + `sig/watch/2` + coverage block).

Findings / decisions (per row):

- 315 (statements + provenance panel): deps `P35.31;P35.65`
  confirmed; no gate; not an OM-20 row. **SIG-TRANSP-011 is the
  §56.10 Owner — stamped.** Per-compartment `record_claims.jsonl`
  beside the record artifacts; `source_refs.upstream_href` filled
  only through the scrub's S-6 URL gate (never a guessed link); the
  four binding states (`actual_capture`/`replayed`/`document_only`/
  `legacy_synthetic`) rendered verbatim — a legacy-synthetic row
  never masquerades as a capture, and no panel implies SIG holds a
  document it does not. One panel data contract across record
  pages / relationship rows / edge panels / map selection / claim
  viewer; licensing, Part VIII, contradiction, supersession and
  review state carried through unchanged. The SIG-TRANSP-012 "view
  original" element is recorded as a stub pending TX-08b's lane
  table (P36.51) — never a raw link this row mints.
- 316 (figure→evidence): deps `P35.36;P35.20b` confirmed; no gate.
  **SIG-TRANSP-013 is the §56.10 Owner — stamped; F-102 owned.**
  Figure contract = value + manifest-listed artifact + JSON pointer
  + definition + visible evidence href; coverage tiles and
  evaluation metrics are figures, not exempt chrome; the build
  check fails on a missing pointer and on an unscoped raw numeral
  (a scanned numeral with no pointer is a defect, not a fallback);
  zero-JS preserved (the pointer resolves server-side into the
  emitted artifact).
- 317 (IRI base + provenance identity): deps `P34.25;P35.38a`
  confirmed. **Gate `Q-E2-03 [B-6] = 'Move UA, don't buy domain'`
  carried verbatim** — an operator decision recorded, never an
  agent call; the declined defensive-registration half is recorded
  as residual squatting risk, not silently dropped. New release
  IRIs mint on `https://surveillancegraph.org/`; already-published
  IRIs are immutable and resolve through an append-only alias map +
  compat note. The stale literals are enumerated in-contract
  (`exports/provo.py:33`, `exports/formats.py:103`,
  `build_predicates.py:72`, the `ontology.sig-project.org`
  vocab paths); generated artifacts regenerate through `make gen`,
  never hand-edit; crawler retrieval-time + upstream-URL semantics
  unchanged; no personal contact added (P35.38a's rule — e-mail
  waits for `contact@`). No §56 Owner (recorded; R11-SAFE-06).
- 318 (data dictionary + metadata): deps `P35.14b;P35.38b`
  confirmed — **recorded fix-forward during docs-check:** the
  Depends line's prose "the P35.38 split" parsed as a dep on a
  non-existent `P35.38` row; reworded to "the a/b split of the IRI
  row" (the audit's DEP_ID_RE never sees a bare stem on the line;
  content unchanged). **SIG-TRANSP-016 + 017 are the §56.10
  Owners — stamped; SIG-TRANSP-033 is the `Also:`** (Owner
  P36.48 — the Table Schema machinery this row lands serves that
  download). Exporter column registry → `dictionary.json`; a Table
  Schema per tabular resource (the J1 NEW-11 fix); datapackage v2
  per bundle; DCAT 3 `catalog.jsonld` + PROV-O `provenance.jsonld`
  as **linked files only** (D-J3-7 — no inline JSON-LD `<script>`
  on public pages; a new ADR would be needed to exempt a named
  page — this row seeks none); `prov:generatedAtTime` is true
  `retrieved_at`. ODbL separation + fail-closed rights unchanged.
- 319 (source universe + lifecycle + counts): deps
  `P35.31;P35.35;P34.17` confirmed; no gate. **SIG-TRANSP-002 +
  026 + 027 are the §56.10 Owners — stamped; SIG-TRANSP-001 is the
  `Also:` (Owner P36.48); F-431 owned.** A source is exactly one
  registry row; connectors/agenda tenants/camera endpoints/capture
  hosts/mirrors are attributes, not sources; a data-bearing
  identifier without a registry row is an anomaly, listed —
  never silently counted. Lifecycle precedence verbatim
  (`withdrawn` > `published` > `ingested_not_published` >
  `permitted_not_ingested` > `gated` > `refused`); partition
  totals must equal the registry count (build-checked). The
  historical numbers (178/218/219/208/236/342) are explained by
  named predicate, never silently reused; the IDs behind each
  funnel difference publish. No connector or outreach change.
- 320 (freshness semantics v2): deps `P35.33;P35.32;P35.20b;P35.34`
  confirmed. **The OM-20 conditional carried verbatim** — named
  mutation (the connector-image roll deploying the capture-side
  fields) pre-authorised only if the GATE-G4 list names this row,
  expiry at the next gate, otherwise in-ticket pause; live stage
  `production write / connector roll` + window `AR-3 + AR-2`
  verbatim; one leg + re-run prompt. **SIG-TRANSP-007 + 029 + 030
  + 031 are the §56.10 Owners — stamped; SIG-TRANSP-034 is the
  `Also:` (Owner P36.43 — this row lands the release-side rule);
  F-137 owned.** One `freshness_verdict(cadence, executions, at)`
  shared by exporter/status/alerting; every verdict carries its
  evaluation time; release pages show fixed as-of values only.
  Volatility derives from the ontology predicate registry over all
  published claims; staleness always shows evaluable +
  not-evaluable counts — `unknown` and `not evaluable` are
  distinct words and `0 stale` is never emitted for unevaluable
  data; `one_time_load`/`not_applicable` preserved; upstream
  last-modified preferred, canonical records digest the fallback,
  and a byte-only change never moves the upstream-change date.
- 321 (citation block + release ID): deps `P35.13;P35.65`
  confirmed; no gate; S budget (0.5 run). **SIG-TRANSP-023 is the
  §56.10 Owner — stamped** (this row satisfies the citation-block
  half; the snapshots/selectors half belongs to the named `Also:`
  rows); **F-07/F-099/F-101/F-390/F-399 owned.** `BaseLayout`
  citation block on every page: immutable `/s/<pub>/`/`/r/<pub>/`
  link + release ID + `as_of_world`/`as_of_belief` + ruleset id;
  legacy selectors resolve at the edge — exact→redirect,
  none→404, malformed→400, ambiguous→409 — never a silent
  substitute of current content; zero-JS preserved.
- 322 (watch producer v1): deps `P35.19;P35.31;P34.21b` confirmed;
  no gate (D-K7-4 windows / D-K7-5 feed coverage cited as pending
  operator decisions — the design's windows land as declared
  inference, flagged, never ratified); not an OM-20 row. **No §56
  Owner (recorded); F-481 owned** — the renewal watch has no
  producer today (nothing fills `raw['contract_watch']`; verified
  against the exporter). `EXPORT_QUERIES` watch reads +
  `exports/watch.py` (the six kind-derivations verbatim;
  `upper_bound` never labelled a deadline; `_next_decision_date`
  reused, never a second formula); `sig.watch-item/1` +
  `web/watch.json` v2 (`sig/watch/2`) with the coverage block —
  an empty result arrives with its coverage statement; placement
  follows the K7 §5.3 order with `unplaced` as an honest bucket
  (a NUTS code is never an ISO 3166-2 code — no place guessed);
  the read-only sizing count query is a named deliverable. Later
  watch rows recorded out: pages/facets 402 (P36.59), recommender
  repair 454 (P37.30), dated decision predicates 455 (P37.31),
  the contract-expiring detector 456 (P37.32), the watch lane 457
  (P37.33), feeds v2 458 (P37.34) — this row is the producer, not
  the surface. Draft `SIG-WATCH-D01…D10` cited as design refs
  (K7 §8 defers the final ids to PLAN-11C), recorded not stamped.

ADR-171 outreach-owed (deliverable 8a) — per row:

- All eight rows carry "**recorded why it does not apply**"
  blocks: 315/316/318/319/320/322 are exporter code + emitted
  artifacts + web components over already-captured claims and
  committed config; 317 swaps IRI-base literals + regenerates
  generated artifacts (the contact surface is P35.38a's already-
  landed UA/URL — this row adds no contact); 321 is a template +
  an edge rule. None writes, widens or activates a §6-compact /
  §22.4–22.5 / §35.1 ecosystem connector; the watch's
  `what_you_can_do` field is procedural text a reader could act
  on — SIG itself sends no e-mail and makes no contact (W-P5).
  The Stage-0 set (SIG-CHART-033, SIG-INGEST-029/030a,
  SIG-CONTRIB-012/012a/013, SIG-GOV-024) stays owed — unmet at
  launch — under `D-R11-LATER-04` (recorded verbatim on each row).
  No outside contact made or implied (ADR-171 Decision 3, U-011).

Local verification (P11, with recorded limits):

- `make docs-check` — **green, second run.** First run caught one
  real diagnostic (`318`'s Depends-line prose "the P35.38 split"
  → dependency-not-in-chain on `P35.38`); reworded in place
  (recorded above), audit re-run 0 failing diagnostics, full
  `docs-check` re-run green (both vendored freshness detectors,
  build-memory, memory-guard worktree, spec-src reproduction
  byte-identical, coverage matrix 820/820, backlog, ledger
  contract, current-state audit `--require-reconciled` — 9
  conflicts covered by reconciliations.json, 0 failing).
- Projection regenerated (`current_projection.py generate` —
  the eight contract digests + input_commit advanced; `verify`
  fresh before the content commit).
- `python3 docs/build/tools/memory_guard.py all --staged` — run
  before the content commit (protected records appended only;
  this ledger's C9 section replaces the `### C9 — pending`
  placeholder, the established per-context convention).
- `make check` — not re-run this context: no code changed
  (contracts + this ledger + projection only); CI is the
  authority. Docker stays wedged (recorded C1).

Boundary (OM-05):

- Read @ `3670b7e9` (content+ledger head): **`ci: pass
  #236@3670b7e (python 37411758538; docs 37411758538; composed
  37411758538; security 37411758538; web 37411758538) · stack:
  #235 #234 #233 #232 #231 #230 #229 #228 #227 #226 #225 #224
  #223 #221 #220 #219 #218 #217 #216 #214 #213 #211 #210 #209
  #208 #207 #205 #204 #203 #202 #201 #200 #199 #198 #197 #196
  #195 #193 #192 pass · main: 2de7b50 descends:no merges:0
  open-other:6` (log `docs/build/logs/ci-PLAN-11B-C9.json`,
  gitignored, read 2026-10-06T04:01:48Z).** Green on the first
  head — all five required jobs head-bound.

Close record (this commit): records the head-bound read and fills
Closed at 2026-10-06T04:13Z — work complete; boundary green on
the first head. The shared `Closed:` header stays
unwritten — C13 owns closeout.

### C10 — 2026-10-06 (rows 323–330)

Started: 2026-10-06T~05:0xZ (this context resumed from a summary;
the eight contract writes landed ~05:1x–05:3xZ, source: `date -u` —
the files' mtimes read 01:25–01:37Z, earlier than the wall clock, a
recorded mtime anomaly, so `date -u` is the anchor) · Closed:
2026-10-06T05:55Z (`date -u`; last C10 criterion = the head-bound
CI pass at `80193e22` — first head).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a ADR-171 checks):

- Verified the three full-contract drafts the interrupted worker
  left uncommitted (323 — `sig.dossier-sources/1` contribution
  export + the four binding evidence-availability states + the S-6
  `upstream_href` gate; 324 — dossiers at every level + the
  unplaced report, `D-K4-3 [B-44] = as recommended (county + place
  pages)` carried verbatim, backward-compat placement; 325 —
  derivation collapse + possible duplicates, the full conditional
  OM-20 gate verbatim, live stage `production write`, window
  `AR-3 + AR-2`, one append-only ER leg + re-run prompt,
  `live_verification=true`) — all three carry the landed shape
  (harness header, Run line, OM-20 status, Load ÷3/÷4, layered
  ACs, operating-clause block, §56 stamping).
- Rewrote the five remaining skeletons in place: 326 (publish the
  dedup — `site_id`/`copies[]`/`possible_duplicates[]`/
  `n_independent_lineages` + count intervals), 327 (agent review
  lane — `sig.agent-review/1`, two blind same-family contexts,
  never gates), 328 (page-type registry + route discovery +
  script-policy + no-JS parity specs), 329 (`sig.page-budgets/1`
  + generated `lighthouserc.json` + the ≥232k/5k/400k synthetic
  national fixture), 330 (`sig.map-tiles/2` tile retention +
  verifier + ADR-156 write-up).

Findings / decisions (per row):

- 323 (dossier contribution export): verified — deps
  `P35.19;P35.31` confirmed; no gate (D-K5-4's merge answered yes
  at T3 — absorbed scope, recorded); not an OM-20 row; no live
  stage. **SIG-TRANSP-008 + 040 recorded as `Also:` (Owner
  P36.69, row 348)** — the export serves the transparency family
  the row cites; the ledger's earlier "no §56 Owner" reading
  stands corrected in-contract (the draft carries the `Also:`
  placement).
- 324 (dossiers at every level + unplaced report): verified —
  deps `P35.19;P35.44` confirmed; **`D-K4-3 [B-44] = as
  recommended (county + place pages)` carried verbatim**; not an
  OM-20 row; no live stage. Threshold provenance and the
  backward-compat placement rule are in-contract; the unplaced
  report is an honest bucket, never a guessed place.
- 325 (derivation collapse + possible duplicates): verified —
  deps `P35.25;P35.15b` confirmed; **the conditional OM-20 gate
  `Q-L3-6 [B-31] = a: C2 enabled · Q-L3-1 [A-6] = a:
  auto-collapse only C0–C2 (SIG-EVAL-004 lower bound waived for
  C0–C2, ADR-153) · …` carried verbatim**; live stage
  `production write`, window `AR-3 + AR-2`, one ER leg, `+0`
  idempotence, `live_verification=true`. **SIG-CONF-004 is the
  §56.7 Owner — stamped** (Also: P37.46a/b recorded);
  derivation ≠ identity (`merged_into` never written);
  possible duplicates show, never merge.
- 326 (publish the dedup): written — deps `P35.46;P35.44;P35.39`
  confirmed (R11-CONF-07a;R11-K13-DSRC-01;R11-K13-TX-10a
  verbatim map). **Gate `D-K13-4 [B-26] = yes (dedup is an
  announce criterion) · publication rides P35.63 (HG-11 Class S)`
  carried verbatim**; live stage `publish` + window
  `AR-3 + AR-2` carried as the publish row's leg (the same
  carry-shape C9's 320 uses — the effect lands inside P35.63's
  window); `live_verification=false` (exporter code + emitted
  fields; no leg of this row's own). **SIG-CONF-005 is the §56.7
  Owner — stamped; F-511 owned** (no cluster id exported; one
  national count only; `merged_into` writerless — all closed at
  the field level). Deliverables: the four published fields with
  the L3 §5.2 display strings verbatim, per-dossier/map/bulk
  count intervals (upper = copies collapsed, lower = possible
  duplicates merged), the multi-view class (same-layer distinct
  records are never duplicates), honest-absence states,
  dictionary registration, the GQ-10 check wired (dossier
  inflation ≤ 1.02× vs lineage roots is the ratchet target —
  measured, never assumed). Publish itself = row 341 (P35.63)
  recorded out; rendering = row 463 (P37.39).
- 327 (agent review lane): written — dep `P34.44b` confirmed
  (R11-CONF-01 verbatim map). **Gate `Q-L3-4 [B-31] = no:
  same-family blind contexts only; labelled, never gating`
  carried verbatim**; not an OM-20 row; no live stage; S budget.
  **SIG-CONF-002 is the §56.7 Owner — stamped.** `sig.agent-
  review/1` JSONL under the reports tree (the design's first
  option pinned); seeded weekly sample (50 sites + 30 edges over
  the verbatim strata); two blind same-family contexts —
  `labeller_kind: agent`, model id, prompt digest, context id,
  seed; disagreement routes to the maintainer-queue stratum (the
  OPCHECK protocol itself was dropped at B-31 — recorded); three
  prohibition guards as tests (no `human_eval_*` write, no
  gate/promotion read, no reserved-partition labels); κ + GQ-22
  report-only, basis class `agent review`; `camera_site_gold.json`
  relabelled "agent (Claude Opus 5.5), twice", development-only.
  **Recorded plan-note reconciliation (agent-labelled):** the S1b
  "lands so OPCHECK can accompany P35.63" is superseded in half —
  S6/B-31 `c` drops OPCHECK; the pull-forward stands (chain
  order), the superseded rationale half is recorded, never
  silently deleted. Second family → `D-R11-LATER-18`.
- 328 (page-type registry + discovery): written — dep `SEED-11`
  confirmed (ADR-155 + the §40 amendments landed there; the
  dep is informational — recorded, OM-03). **Gate `D-K0-1 [A-12]
  = a: HTML-first page types (ADR-155) replace the zero-JS rule`
  carried verbatim**; not an OM-20 row; no live stage; M budget.
  **No §56 Owner (recorded)** — the row implements SIG-UI-036/
  041/050's amended text; `UXR-02` cited as the design ref (the
  final K13 id is PLAN-11C's, per spec §56.10). Deliverables:
  `web/src/lib/page-types.ts` (pattern → type + owner ticket +
  data-contract id + no-JS equivalent; overlapping patterns are
  an error), the `astro:build:done` hook failing unclassified or
  doubly-classified routes, `script-policy.spec.ts` (replacing
  `islands.spec.ts`'s policy half; D-J3-7's linked-files-only
  answer governs the data-block clause), `nojs-parity.spec.ts`,
  every sweep rewired to discovered routes, and the two
  AGENTS.md stanza rewrites (the code half of K0 UXK0-7 — the
  "until P35.50/P35.51 land" hedge retires with 329).
- 329 (page budgets + LHCI + national fixture): written — dep
  `P35.50` confirmed; no gate (the plan cell is empty — recorded);
  not an OM-20 row; M budget. **No §56 Owner (recorded;
  SIG-FIND-005's `Owner:` stays P32.15 — this row serves its
  fixture/budget half).** Deliverables: `sig.page-budgets/1` at
  `web/tests/e2e/page-budgets.json` with the §4.9 table's numbers
  verbatim (superseding `island-budgets.json` in the same change —
  single truth, recorded seam), `web/scripts/gen-lhci.mjs`
  generating `lighthouserc.json` + the drift sync test (≥ one
  route per type, performance assertions are errors), the
  generalised `budget.spec.ts` (gzip and brotli, before and after
  one scripted interaction per surface), and the deterministic
  synthetic national fixture (≥ 232k sites / ≥ 5k agencies / ≥
  400k sharing edges, invented names only, F-173's guard as a
  test). **CI-8 declared `yes`** — the discovered-route LHCI run
  (K0 NEW-3) touches the web job's wiring; recorded honestly.
  The /map/ 497 KB-over-budget reading is a recorded measured
  gap, never smoothed — the fix is a map-surface row's.
- 330 (tile retention + verifier + ADR-156): written — deps
  `P34.34b;P35.51` confirmed (R11-ACT-16 + R11-K13-UXK0-2
  verbatim maps); no gate; not an OM-20 row; M budget. **F-104 +
  F-414 owned; ADR-156 written by this row** (reserved number;
  ADR-170 already cites it provisionally for the self-hosted-
  basemap direction). `sig.map-tiles/2`: two layers — `cells`
  (H3 z0–9, band res 3/4/5/6; per-compartment counts only — a
  cross-compartment archive is licence-mixed, never published,
  K1 §3.2/ADR-106 §4) + `sites` (tier 0 z10+, tier 1 z11+, tier
  2 z12+ as its H3 polygon, tier 3 never); per-feature
  `"tippecanoe"` zoom-range members, `-r1`, the forbidden-flags
  guard, fail-loud on oversize; pure-Python parity (no same-cell
  coalescing; byte-identical dedupe only); `web/tiles/index.json`
  manifest with the verbatim field set + content-hash names;
  `sig-exports tiles verify` running the six §9.2 checks →
  `reports/tiles_verify.json`; pinned tippecanoe 2.79.0 built in
  CI once + cached; the 50k-point fixture (clustered cities,
  co-located points, all tiers, 3 compartments) + the nightly
  real-sized run over dep's fixture. **CI-8 declared `yes`** —
  the tippecanoe build + nightly verifier run touch CI wiring.
  The island's rendering half (unused `MIN_POINT_ZOOM_BY_TIER`
  et al.) is MAP-03's — recorded seam; the full property payload
  is row 440 (P37.17, MAP-01b).

ADR-171 outreach-owed (deliverable 8a) — per row:

- All eight rows carry "**recorded why it does not apply**"
  blocks: 323/324/325/326 are exporter code + emitted fields over
  already-captured spine rows (326's publish effect rides
  P35.63's leg); 327 samples published artifacts and stores
  labelled agent records; 328/329 are registry/spec/fixture CI
  machinery; 330 changes how already-permitted records render
  into tiles (the basemap stays self-hosted — no third-party tile
  service contacted, by design and by ADR-156). None writes,
  widens or activates a §6-compact / §22.4–22.5 / §35.1 ecosystem
  connector. The Stage-0 set (SIG-CHART-033, SIG-INGEST-029/030a,
  SIG-CONTRIB-012/012a/013, SIG-GOV-024) stays owed — unmet at
  launch — under `D-R11-LATER-04` (recorded verbatim on each
  row). No outside contact made or implied (ADR-171 Decision 3,
  U-011).

Local verification (P11, with recorded limits):

- `make docs-check` — **green, first run.** Both vendored
  freshness detectors, build-memory (0 violations, 41 legacy
  warnings — none C10's), memory-guard worktree (0 violations),
  spec-src reproduction byte-identical (852,023 B), coverage
  matrix 820/820, backlog, ledger contract (0 violations),
  current-state audit `--require-reconciled` (9 pre-existing
  conflicts covered by reconciliations.json, 0 failing),
  obligation check, projection verify, return-pass, planning
  memory, ADR index + triggers, round-close — all clean. The
  eight Depends lines name only chain ids; no C9-style
  prose-parse diagnostic recurred.
- Projection regenerated (`current_projection.py generate` — the
  eight contract digests + input_commit advanced; `verify` fresh
  before the content commit).
- `python3 docs/build/tools/memory_guard.py all --staged` — run
  before the content commit (protected records appended only;
  this ledger's C10 section replaces the `### C10 — pending`
  placeholder, the established per-context convention).
- `make check` — not re-run this context: no code changed
  (contracts + this ledger + projection only); CI is the
  authority. Docker stays wedged (recorded C1).

Boundary (OM-05):

- Read @ `80193e22` (content+ledger head): **`ci: pass
  #236@80193e2 (python 37420161300; docs 37420161300; composed
  37420161300; security 37420161300; web 37420161300) · stack:
  #235 #234 #233 #232 #231 #230 #229 #228 #227 #226 #225 #224
  #223 #221 #220 #219 #218 #217 #216 #214 #213 #211 #210 #209
  #208 #207 #205 #204 #203 #202 #201 #200 #199 #198 #197 #196
  #195 #193 #192 pass · main: 2de7b50 descends:no merges:0
  open-other:6` (log `docs/build/logs/ci-PLAN-11B-C10.json`,
  gitignored, read 2026-10-06T05:52Z).** Green on the first
  head — all five required jobs head-bound; no blockedOn.

Close record (this commit): records the head-bound read and fills
Closed at 2026-10-06T05:55Z — work complete; boundary green on
the first head. The shared `Closed:` header stays unwritten — C13
owns closeout.

### C11 — 2026-10-06 (rows 331–337)

Started: 2026-10-06T~05:5xZ (this context resumed from a summary;
the row-331 write landed in the prior segment and rows 332–337
landed ~05:59–06:03Z; the files' mtimes read 01:59–02:03 — the
recorded local-clock offset C10 noted, so `date -u` is the
anchor) · Closed: 2026-10-06T06:19Z (`date -u`; last C11
criterion = the head-bound CI pass at `6fccb086` — first head).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a ADR-171 checks):

- Rewrote all seven skeletons in place: 331 (release pipeline —
  the `sig-ops release` verb family with registry lock/events/
  dry-run/apply, the private versioned bucket with the §4.1
  namespace layout, two IAM-only staging services, the
  `sig-release` job + `sig-release-rt` SA, the NEW-5 eviction of
  committed release trees with a recommit guard, the
  stale-generation refusal), 332 (envsubst-templated nginx +
  `conf/<gen>/` generations + metadata-only `promote` — the
  promoted.map 404 gate, digest rolls, zero byte copies, atomic
  latest flip), 333 (rollback/clear-latest/withdraw/
  `--purge-versions` — withdrawals re-applied on rollback, no
  config reversion, alias-complete tombstones, dormant R2/CDN
  purge hooks, the legacy-floor import machinery, the conf-gen
  regression probe, runbook sections appended into P35.4's file),
  334 (verification suite A — V1–V5 + V11–V13, S/P modes, JSON
  results, skip-blocks, each seeded defect fails), 335 (suite B —
  V6–V10 + V14 + the P1 probe set + the D-G3-8 pre-authorised
  post-promote auto-rollback + the V15 hook point), 336 (the dark
  cutover — legacy-floor import, `sig-web` digest roll,
  byte-compare of every allow-listed route, bucket-root serving
  retirement), 337 (release classifier + Class-R standing go +
  the agent-drafted readout generator + the sign-off-scope ADR).

Findings / decisions (per row):

- 331 (release pipeline): written — deps `P34.10;P34.3;P34.43`
  confirmed verbatim. **The conditional OM-20 gate `named
  mutation -> OM-20: pre-authorised only if the GATE-G4 list …
  names this row …; otherwise NOT pre-authorised = IN-TICKET
  PAUSE (private release bucket, staging services, sig-release
  job)` + `D-G3-10 [B-9] = yes` carried verbatim**; live stage
  `production write`, window `AR-3 + AR-2`, one infra-create leg
  (AR-2 restore point → IaC apply → private-reachability proof →
  stale-generation refuse), `live_verification=true`.
  **SIG-REL-004 + SIG-REL-005 are the §56.6 Owners — stamped.**
  The mutation list is named (private bucket + two IAM-only
  staging services + `sig-release` job/`sig-release-rt`); the plan
  cell enumerates no legs, so the contract derives one leg from
  the creates + the unauthenticated-probe AC (recorded reading).
  `live:` edges recorded — P34.40's L2 `/v1/*` step (8d seam;
  GB-Q4 authority expires GATE-G4, named on the 11B OM-20 list if
  still paused) and P35.59's consumption of the topology. NEW-5's
  eviction removes files, not history — recorded.
- 332 (config generations + promote): written — deps
  `P35.53;P34.40;P34.41` confirmed verbatim. **Gate `none`
  carried verbatim**; not an OM-20 row; live stage `none (used by
  R11-REL-09)` carried. **SIG-REL-006 is the §56.6 Owner —
  stamped.** Promotion is a metadata act: `conf/<gen+1>` composed
  whole (promoted.map + latest.json + withdrawn/selectors/labels
  + `releases/` index — release tool the only generator), zero
  release bytes copied, `sig-api` then `sig-web` rolled by digest
  with `min-instances=1`, the latest flip atomic per revision,
  unpromoted namespaces 404 by `map` construction,
  `SIG_STAGING=1` bypass + `noindex` env-guarded. Recorded:
  `D-P34.13-1`'s `error_page` surface preserved; the approval
  check reads the standing go or signed readout — never creates
  one; Cloud Run traffic reversion forbidden (333's clause).
- 333 (rollback/withdrawal/purge/runbook): written — deps
  `P35.54;P35.4` confirmed verbatim. **Gate `none` carried
  verbatim**; not an OM-20 row; live stage `none (rehearsed in
  R11-REL-09/11)` carried — the 10/15-minute targets are measured
  at REL-11, recorded as targets (D-G3-9). **SIG-REL-013 is the
  §56.6 Owner — stamped.** Rollback re-applies the *current*
  withdrawal set and writes `conf/<gen+1>` (latest moves; serving
  configuration is never reverted — Cloud Run traffic reversion
  is forbidden by construction); withdraw = the §8.3 order
  verbatim over every staged namespace with alias-complete
  `withdrawn.conf` and 410 `sig.tombstone/1` probed on every
  alias; `--purge-versions` deletes noncurrent versions of
  withdrawn objects only (the append-only claim spine untouched);
  the R2/CDN purge hooks are wired but dormant until J3 TX-11's
  mirror exists (a missing mirror config is a no-op, recorded);
  the §7.3 needs-no-readout set is carried — every verb records
  the operator go or pre-authorisation id; the runbook sections
  are appended into P35.4's file, never a rewrite.
- 334 (verification suite A): written — deps
  `P35.13;P35.53;P34.34b;P35.31` confirmed verbatim. **Gate
  `none` carried verbatim**; not an OM-20 row; no live stage.
  **SIG-REL-007 recorded as `Also:` — Owner stays P35.58** (the
  requirement's own §56.6 `Also:` naming). V1–V5 + V11–V13 in S
  and P modes per the §5.5 table; every check writes a JSON
  result; a skip blocks (SIG-ENG-042 — never a silent pass); the
  waiver exists only under Class S and is recorded in the
  readout; **each V-check fails a seeded defect** (the catalog AC
  verbatim). The 2 % stratified integrity sample is this check's
  — the full-tree monthly audit is a named later row, recorded.
- 335 (verification suite B + auto-rollback): written — deps
  `P35.56;P35.57;P35.55;P34.21b;P35.19;P35.16;P35.20b;P34.4`
  confirmed verbatim (the catalog fan-out map). **Gate `D-G3-8
  [B-9] = yes (auto-rollback pre-authorised)` carried
  verbatim** — the one always-authorised mutation class, cited on
  every invocation record; not an OM-20 row; no live stage.
  **SIG-REL-007 is the §56.6 Owner — stamped.** V6 number truth
  (DR-C3-15 recompute), V7 API parity (§6.4 verbatim over every
  dossier scope + 20 coverage scopes), V8 attribution sanity, V9
  jurisdiction–coordinate sanity (the named regression cases as
  fixtures), V10 withdrawal barrier (every alias, conf-gen
  equality), V14 diff sanity (six deltas emitted for 337's
  classifier — never interpreted here); the P1 probes join
  `cadence.toml` with trigger points + `probe-run/1` records; a
  seeded post-promote failure rolls back automatically and
  alerts (the catalog AC); the V15 hook point is hosted —
  SIG-CONF-007's checks stay P34.44a's, a ratchet regression
  feeds the Class-S signal.
- 336 (dark cutover): written — deps
  `P35.54;P35.56;P35.55;P34.17;P34.21b` confirmed verbatim. **The
  conditional OM-20 gate carried verbatim**; live stage
  `production write`, window `AR-3 + AR-2`, one cutover leg
  (restore point → floor import → digest roll → byte-compare →
  retirement), `live_verification=true`, S budget.
  **No §56 Owner (recorded)** — the cutover serves SIG-REL-004/
  005/006 + SIG-OPS-004. The floor lands as
  `staged/v/legacy-<YYYYMMDD>/` labelled `legacy-…`, never a pub
  id ("the import is not a publication", §8.2); `sig-web` rolls
  by digest with `SIG_LATEST_PUB=legacy-…`, `SIG_CONF_GEN=0`;
  every allow-listed route byte-compares identical on the
  canonical origin + run.app URL — a difference fails the leg and
  reverts; the bucket-root serving *path* retires (the `sig-web`
  bucket itself keeps public-read 90 days as the floor source
  under D-G3-7's carried answer — `D-R11-LATER-20`'s clock
  anchors on this row's recorded landing date). **`live:P34.40`
  seam recorded (8d)** — the `/v1/*` step precedes or is named on
  the OM-20 list, never dropped.
- 337 (classifier + standing go + readout): written — dep
  `P35.58` confirmed verbatim. **Gate `D-G3-3 [B-9] = a` carried
  verbatim** (standing-go adopted form; the standing-go text,
  expiry/void conditions and required Class-S wording are
  agent-drafted for operator adoption — labelled, never implied
  adopted). **SIG-CONF-010 + SIG-REL-012 are the §56 Owners —
  stamped; the C11 seam correction is recorded in-contract:
  SIG-CONF-010's owner is P35.60 — P37.45 carries an `Also:`
  placement (the P38 notice-surface extension), never the
  ownership.** The classifier is fail-closed (any unevaluable
  check → S; a ratchet-regression input → S — the catalog AC);
  the template fingerprint is a fixed-fixture build digest; the
  standing go is a record (adopted text + expiry + void
  conditions; expiry honoured for in-flight only; absent/expired/
  void refused); the readout generator emits the verbatim
  required wording — "single maintainer, no second reviewer" and
  "no human check performed" — labelled agent draft, signature
  slot never filled; the notice rides the landed mail path to the
  operator's configured destination (no address written into any
  file); the sign-off-scope ADR lands here per SIG-REL-012's
  "ADR at P35.60" clause.

ADR-171 outreach-owed (deliverable 8a) — per row:

- All seven rows carry "**recorded why it does not apply**"
  blocks: 331 creates cloud infrastructure and repo tooling; 332
  adds serving config and promotion machinery; 333 adds reversal
  machinery and runbook text; 334/335 add verification and
  rollback-orchestration code plus probe config; 336 imports an
  already-published tree and rolls a serving image; 337 adds
  classification and readout machinery plus drafted texts (its
  notice channel delivers to the operator through the landed
  mail path — internal notification, never outside contact). None
  writes, widens or activates a §6-compact / §22.4–22.5 / §35.1
  ecosystem connector or project. The Stage-0 set (SIG-CHART-033,
  SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013, SIG-GOV-024)
  stays owed — unmet at launch — under `D-R11-LATER-04` (recorded
  verbatim on each row). No outside contact made or implied
  (ADR-171 Decision 3, U-011); no operator e-mail address written
  into any file.

Local verification (P11, with recorded limits):

- `make docs-check` — **green through every detector.** Both
  freshness detectors, build-memory (0 violations; the same
  legacy warning set as C10 — none C11's), memory-guard worktree
  (0 violations), spec-src reproduction byte-identical (852,023
  B), coverage matrix 820/820, backlog, ledger contract (0
  violations), current-state audit `--require-reconciled` (9
  pre-existing conflicts covered, 0 failing), obligation check —
  all clean. The projection verify reported the seven contract
  digests stale, as expected — regenerated before the commit.
- Projection regenerated (`current_projection.py generate` — the
  seven contract digests + input_commit advanced; `verify` fresh
  before the content commit).
- `python3 docs/build/tools/memory_guard.py all --staged` — run
  before the content commit (protected records appended only;
  this ledger's C11 section replaces the `### C11 — pending`
  placeholder, the established per-context convention).
- `make check` — not re-run this context: no code changed
  (contracts + this ledger + projection only); CI is the
  authority. Docker stays wedged (recorded C1).

Boundary (OM-05):

- Read @ `6fccb086` (content+ledger head): **`ci: pass
  #236@6fccb08 (python 37422175926; docs 37422175926; composed
  37422175926; security 37422175926; web 37422175926) · stack:
  #235 #234 #233 #232 #231 #230 #229 #228 #227 #226 #225 #224
  #223 #221 #220 #219 #218 #217 #216 #214 #213 #211 #210 #209
  #208 #207 #205 #204 #203 #202 #201 #200 #199 #198 #197 #196
  #195 #193 #192 pass · main: 2de7b50 descends:no merges:0
  open-other:6` (log `docs/build/logs/ci-PLAN-11B-C11.json`,
  gitignored, read 2026-10-06T06:09Z).** Green on the first
  head — all five required jobs head-bound; no blockedOn.

Close record (this commit): records the head-bound read and fills
Closed at 2026-10-06T06:19Z — work complete; boundary green on
the first head. The shared `Closed:` header stays unwritten — C13
owns closeout.

### C12 — 2026-10-06 (rows 338–343, to GATE-G5)

Started: 2026-10-06T06:23Z (`date -u` at the first contract
write; this context resumed from a summary — the six skeleton
inspections and the plan-cell reads landed in the prior
segment) · Closed: 2026-10-06T06:54Z (`date -u`; last C12
criterion = the head-bound CI pass at `fce56436` — second
head, the first red on the run-ledger digest, fixed forward).
Context model: devin-desktop/swe-2-high/subagent.

Scope (contract deliverable 2-in-part + the 8a ADR-171 checks
+ the C13 seam inputs):

- Rewrote all six skeletons in place: 338 (the D-R10-LIVE-1
  live pass — hosted read-only audit → recovery plan → the
  operator review pause → bounded apply inside the recorded
  ceilings → +0 re-run → rematerialize → `frozen_unpublished`
  snapshot, three legs verbatim), 339 (the D-P32.23a-1
  production candidate over the frozen snapshot — staged only,
  the export-mode build + DR-C4-01 crawl, true dates, the
  `p-17b713` supersession never re-signed), 340 (PLAN-11C — a
  real plan-kind contract modelled on this file's own shape:
  `decompose-spec mode=extend`, the K13 UX requirement
  families append in C1, twelve contexts ≤ 8 rows over rows
  344–420 per the ratified CSV and plan §8.1's count — 74
  tickets, PLAN-11D, acceptance P36.73, GATE-G6 — the
  Phase-4 review, the 11C re-split evaluation, the draft 11C
  OM-20 list for GATE-G5, and the 8a/8b carry placements),
  341 (the first model release — the staged cut, full V1–V15
  green, the Class S candidate-specific HG-11 readout signed
  verbatim with the two required statements, promote + the
  live rollback rehearsal, the ratchet-based gate, the
  allow-list opening archive + pinned citations + release
  search first), 342 (the real 11B acceptance capstone —
  read-only live-read sweep writing `probe-run/1`, the S2
  §4.2 exit items checked live, layered verdicts for rows
  261–343, the unresolved-issue visibility rule, the six-part
  GATE-G5 packet draft), 343 (the GATE-G5 gate marker — guard
  sentence, no run/branch/live stage, the S5-2 packet with
  ING-GO-C + the Wave-C/vendor flip list + the 11C OM-20
  list + the Class R renewal, `continue` answers batch lines
  only, silence = pause).

Findings / decisions (per row):

- 338 (live pass): written — deps
  `P34.46;P34.22b;P34.43;P34.6;P35.46(S2);P35.15b(S2);P35.31`
  confirmed verbatim (the two `(S2)` edges recorded as
  ordering-only). **The never-pre-authorised in-ticket pause
  `explicit go + recorded --authority scope` carried
  verbatim**; live stage `production write`, window `AR-3 +
  AR-2; >= 48 h after P34.46; after the 11B spine writes
  (P35.14-P35.46)` verbatim, three legs verbatim (L1 audit +
  plan, L2 operator review 1–4 h, L3 apply + freeze), leg
  runs 2.0. **No §56 Owner (recorded); owned finding F-522
  (S1) carried.** The D-R10-LIVE-1 production half is this
  row's; the final-candidate half stays owed through the
  superseded human-evaluation path — recorded, never
  silently closed. **`live:` edge to the candidate row
  recorded.**
- 339 (production candidate): written — deps
  `P35.61;P34.22b;P34.34b` confirmed verbatim. **The
  conditional OM-20 gate carried verbatim** (`pre-authorised
  only if the GATE-G4 list … names this row …; otherwise
  NOT pre-authorised = IN-TICKET PAUSE (staged candidate; no
  publication)`); live stage `none (staged only)`, window
  `staging only`, no legs — the OM-19 re-run prompt still
  carried. **No §56 Owner (recorded).** The mutation list is
  named (staged namespace + staging-origin artifacts only —
  ≈ +$0.04/mo S1a upper end, ~2 GB); nothing promotes, the
  superseded `p-17b713` stays superseded by appended record,
  `activate()`/`rollback()` never called. `live:` edge to
  the publish row recorded.
- 340 (PLAN-11C): written as a **plan-kind contract**
  modelled on row 239's own landed form — `Run:
  implement-spec … live_verification=false` dispatched as
  twelve contexts (C1 the K13 family append + rows 344–346;
  C2–C11 batches of ≤ 8; C12 the fresh-context Phase-4
  review). **Correction recorded in-contract:** the T3
  skeleton's provisional context table named stale row ids;
  the contract's table follows the ratified CSV — 11C is
  rows 344–420 (74 tickets, PLAN-11D at 418, P36.73 at 419,
  GATE-G6 at 420; plan §8.1 verbatim). Depends `PLAN-11B`
  verbatim; no gate, not OM-20, no live stage; scheduled
  `while P35.63 waits for its HG-11 go` verbatim, finishing
  before GATE-G5. est 7.0 runs (§8.1's table shows 6.0 in
  the PLAN column — **plan-internal drift recorded, not
  resolved**, flagged for C12-of-11C's review). Carried:
  SEED-12a's family append (new prefix vs SIG-UI fold
  recorded in `K13_id_map.csv`; UXR-A10's TRANSP drafts map
  onto PLAN-11B's landed ids, never re-added), SIG-OPS-007 →
  P35.2 re-confirm, P36.2's out-of-rule rights re-decision
  sized at the Phase-4 review, the 11C re-split rule (76
  eng. rows / 66.5 eng. runs at S6c — fires only if splits
  push over 85 / 75), the draft 11C OM-20 list for GATE-G5,
  the ADR-171 11C-part list and the PLAN-11B C13 hand-offs.
- 341 (first model release): written — all 21 deps confirmed
  verbatim in order (`P35.62;P34.34b;P34.40;P34.41;P34.36;
  P34.23;P35.12;P35.13;P35.53;P35.54;P35.55;P35.56;P35.59;
  P35.60;P35.57;P35.45;P35.47(S2);P35.52(S2);P35.30(S2);
  P35.42(S2);P34.45`; the four `(S2)` edges ordering-only).
  **The HG-11 in-ticket pause cell carried verbatim** (the
  candidate-specific readout signed verbatim; `no OPCHECK:
  Q-L3-3 = c`; the readout states "single maintainer, no
  second reviewer" and "no human check performed"; Q-9/
  G2-HOTFIX [B-7] = a allow-list order); never pre-authorised
  (publication is in the never-listed set). Live stage
  `publish`, window `release cut never inside AR-3 windows
  (G3 §7.2); 14:00-20:00Z; operator available for HG-11`
  verbatim, two legs (L1 stage + V1–V15 + readout; L2 promote
  after HG-11 + live rollback rehearsal — the prior-pointer
  leg recorded not-rehearsable on a first release). **No §56
  Owner (recorded)** — the row executes the activation/
  readout path; SIG-REL-012 and SIG-CONF-010 stay P35.60's
  (P37.45 `Also:` recorded, never re-owned). The ratchet
  gate (FEA-11: 0 regressions + 0 enforce-flip failures),
  the Stream-L move to the 11D CONF-14 row, residual misses
  as known-issue lines, the merge-sentence condition (the
  honest-posture re-run + derivation census, probe-run ≤
  24 h), and the G3-signature non-transfer all carried.
- 342 (11B acceptance): written as a **real capstone
  contract** — deps `P35.63;PLAN-11C` verbatim; read-only
  live stage `after P35.63 promotion`; 0.5 runs. The sweep,
  the S2 §4.2 exit list verbatim (V1–V15 + 0 waivers, the
  rehearsal, `/r/<pub>/` + release search live, withdrawals
  honoured, the G3-signature supersession, the L3 `enforce`
  target table with L2 baselines, the traceability items,
  Wave A +0), the layered verdicts for rows 261–343,
  OPCHECK recorded not-required (Q-L3-3 = c — never claimed
  performed), unresolved-issue visibility, and the six-part
  GATE-G5 packet draft all land. **No §56 Owner
  (recorded).** The D-K2-1 top-50 review (OP-14) is listed
  for the sitting, never performed here.
- 343 (GATE-G5): written as a **gate marker** modelled on
  row 260's landed form — the guard sentence carried
  verbatim; no run, no branch, no live stage/legs; depends
  `P35.64`; the S5-2 packet drafted by the acceptance row.
  The gate collects ING-GO-C for Wave C (the 11C row's
  11-16 → 11-20 window), the Wave-C/vendor HG-03 flip list
  (OP-26), the 11C OM-20 list (drafted by the plan row, each
  entry traceable to a written header, `expires: GATE-G6`),
  and the Class R standing-go renewal — plus budget,
  publication and rights with per-line verbatim answers;
  `continue` answers batch lines only; silence = pause,
  never consent. **Correction recorded, not resolved:** the
  plan title's `ING-GO-B` vs the S4c note's `collects
  ING-GO-C` — the packet drafts the note's content and
  records the title token verbatim (ING-GO-B was the prior
  gate's Wave-B line). The never-listed set for 11C named
  (the Wave-C tier bump, the search-API roll, the
  core-surfaces HG-11 readout, every HG-03 flip, and the
  REL-11 row if the standing go has lapsed).

Oversized flags + C13 candidate seams (the dispatch's own
ask, recorded for the Phase-4 review):

- **338 (the live pass)** — plan flag S6 A-15 carried; the
  declared read set fits but the multi-leg hosted pass's
  accumulated working set plausibly exceeds one ≤ 1-run
  context. Candidate seam recorded in-contract: **the live
  legs split at the pause — audit + plan + packet (L1 + the
  L2 pause) as the a-row; the reviewed apply + freeze + the
  +0/closing verification (L3) as the b-row** — suffix
  letters under the banner if C13 splits. Nothing pre-split.
- **341 (the first model release)** — plan flag S6 A-15
  carried; staging + 15 verification reads + the readout
  assembly fill one context and the promotion + rehearsal is
  a second operator-bounded leg. Candidate seam recorded
  in-contract: **the two live legs themselves — stage +
  V1–V15 + drafted readout as the a-row; promote after HG-11
  + post-promote + the reversed rehearsal as the b-row** —
  the split decision is C13's. Nothing pre-split.

ADR-171 outreach-owed (deliverable 8a) — per row:

- All six rows carry "**recorded why it does not apply**"
  blocks: 338 is a hosted data-repair pass over
  already-captured evidence (its apply has no fetch path by
  construction); 339 builds and stages release artifacts;
  340 is contract-authoring (its own deliverable 7a carries
  the 11C-part rule forward to the real connector rows);
  341 publishes a release of already-captured data (the
  readout's known-issue lines carry the launch-unmet MUSTs
  it names); 342 is a read-only sweep (the packet's status
  part carries the list); 343 collects operator lines (no
  connector work). None writes, widens or activates a
  §6-compact / §22.4–22.5 / §35.1 ecosystem connector or
  project. The Stage-0 set (SIG-CHART-033,
  SIG-INGEST-029/030a, SIG-CONTRIB-012/012a/013,
  SIG-GOV-024) stays owed — unmet at launch — under
  `D-R11-LATER-04` (recorded verbatim on each row). No
  outside contact made or implied (ADR-171 Decision 3,
  U-011); no operator e-mail address written into any file.

Local verification (P11, with recorded limits):

- `make docs-check` — **green through every detector.** Both
  freshness detectors (0 broken refs), build-memory (0
  violations; the same legacy warning set as C11 — none
  C12's), memory-guard worktree (0 violations), spec-src
  reproduction byte-identical (852,023 B), coverage matrix
  820/820, backlog, ledger contract (0 violations),
  current-state audit `--require-reconciled` (9
  pre-existing conflicts covered, 0 failing — the same set
  as C11), obligation check (636 events), return_pass,
  adr-index/triggers, round-close — all clean.
- One audit finding fixed forward inside the context:
  `tickets/forward-dependency` read `GATE-G5` out of the
  acceptance row's `Depends on:` parenthetical (the same
  prose-dependency class C9 hit) — reworded to "the
  check-in packet"; and a `P32`-series id inside the
  publish row's depends parenthetical would have read as
  `dependency-not-in-chain` — reworded to "the landed
  tombstone-carrying nginx roll". The depends cells carry
  only the ratified ids.
- Projection regenerated (`current_projection.py generate`
  — the six contract digests + input set advanced; `verify`
  fresh, 973/973, **0 known inconsistencies**) before the
  content commit.
- `python3 docs/build/tools/memory_guard.py all --staged` —
  run before the content commit (protected records appended
  only; this ledger's C12 section replaces the
  `### C12 — pending` placeholder, the established
  per-context convention).
- `make check` — not re-run this context: no code changed
  (contracts + this ledger + projection only); CI is the
  authority. Docker stays wedged (recorded C1).

Boundary (OM-05):

- Read @ `458e89ae` (content+ledger head, first push):
  **blockedOn — docs job failure, exit code 2 (run
  37424915860): `docs-check-projection` reported
  `docs/build/runs/PLAN-11B.md: stale digest` — the projection
  regen ran before the ledger write, so the recorded digest
  predated the committed ledger (the same shape C1's first
  head hit; C11's boundary-record head `04c5cd70` also went
  red on it — its record commit omitted the regen C8's and
  C10's records carried).** Fix-forward `fce56436` —
  projection regen only (ledger digest advanced; `verify`
  fresh 973/973 locally).
- Read @ `fce56436` (fix-forward head): **`ci: pass
  #236@fce5643 (python 37425285698; docs 37425285698; composed
  37425285698; security 37425285698; web 37425285698) · stack:
  #235 #234 #233 #232 #231 #230 #229 #228 #227 #226 #225 #224
  #223 #221 #220 #219 #218 #217 #216 #214 #213 #211 #210 #209
  #208 #207 #205 #204 #203 #202 #201 #200 #199 #198 #197 #196
  #195 #193 #192 pass · main: 2de7b50 descends:no merges:0
  open-other:6` (log `docs/build/logs/ci-PLAN-11B-C12.json`,
  gitignored, read 2026-10-06T06:54Z).**

Close record (this commit): records the head-bound read and
fills Closed at 2026-10-06T06:54Z — work complete; boundary
green on the second head after the projection-digest
fix-forward. The shared `Closed:` header stays unwritten —
C13 owns closeout. **C13's remaining work,
recorded:** the Phase-4 sizing review across all 83
contracts, the split decisions on the two flagged rows (the
seams above), the GATE-G4b re-split evaluation with counts,
the requirement-index regeneration, the draft 11B OM-20
list, the 11B outreach-owed list, the 8b/8c placement
confirmations, and this row's closeout.

### C13 — 2026-10-06 (Phase-4 review of all 11B contracts; deliverables 4–8; closes this ledger)

Started: 2026-10-06T12:07Z (`date -u` at the isolation echo —
resumed context; the file reads and audits ran ahead of it in
the same context window) · Closed: 2026-10-06T14:04Z
(`date -u` at close — the last criterion is the head-bound CI
read). Context model: devin-desktop/swe-2-high/subagent.

Isolation check (positive control — the verbatim block):

    P11BC13-CTL-182c7b5e
    Tue Oct  6 12:07:26 UTC 2026
    /Users/stevenvitali/Eleutheria
    r11/PLAN-11B-contracts-for-11b-and-transp-family
     M docs/tickets/REQUIREMENT_INDEX_R11.md

(the ` M` line is the regenerated requirement index C12 left
staged for C13's audit — this context's own edits extend it).

Scope (contract row 62 + deliverables 4–8): the fresh-context
Phase-4 sizing review of every 11B contract (rows 261–343), the
split decisions on the four flagged rows, the GATE-G4b
re-split evaluation, the regenerated requirement index, the
draft 11B OM-20 list, the 11B outreach-owed list, the 8b/8c/8d
placement confirmations, and this row's closeout.

Phase-4 sizing review — method (deliverable 4):

- Every contract file of rows 261–343 (83 files before the
  split) re-read: `## Load` header versus its entries on the
  current tree, `Depends on:`/`live:` edges resolved against
  the manifest, `Gate status`/`OM-20 status`/`Production
  mutations` headers audited, requirement-id coverage checked
  against spec §56's `Owner:`/`Also:` lines.
- Working-set model (the T3 convention): Load ÷3 + ≈ 17.5k
  implement-spec/self-review skill text + ≈ 15k harness/dispatch
  + written output × 1.75 (re-reads) + ≈ 25k tool output + ≈ 12k
  per live leg that runs inside the same dispatch context.
  Verdict bands: ok ≤ 200k, tight 200–235k, split > 235k or a
  scope too large for one run regardless of Load.
- Declared reads: **no contract exceeds the ~150k-token ÷3
  ceiling.** Largest after the split: P35.27 (306) ≈ 93.3k,
  P35.26 (305) ≈ 91.7k, P35.25 (304) ≈ 90.0k, P35.6 (266)
  ≈ 89.4k, P35.22 (302) ≈ 88.3k, P35.24 (303) ≈ 85.0k; the
  rest trail off below ≈ 77k. The two non-ticket rows record
  loads in their own forms (PLAN-11C ≈ 106.7k ÷3 per context;
  GATE-G5 a gate marker). Modelled peaks for the heavy
  conditional-OM-20 rows land ≈ 200–225k (tight, fitting) —
  their live legs dispatch under the OM-19 re-run prompt.

The four flagged rows — decided:

- **P35.1b (row 291) — SPLIT.** Its mutations are all
  *in-ticket* under the OM-20 listing (`Live legs: none
  separately queued`) — unlike the leg rows, nothing forces
  the work across dispatches. One context would carry the
  engineering plus ~8 mutation groups (pre-state + backup, six
  deletions, keep-list + `sig-export` guard, AR policy dry-run
  + apply, four cron reconciles, `sig-alerts` disposition,
  dispatcher build + deploy + ~79 retirements, closing proof):
  ≈ 77k Load + ≈ 57.5k fixed + ≈ 52.5k output + ≈ 90k of live
  leg work ≈ **275k — over the 235k split line**, and the
  destructive sweep and the new dispatcher mechanism are two
  different working sets with different blast radii. The
  contract recorded the seam; this context executed it.
- **P36.12 (row 290) — NOT split.** Its ten family legs run
  10-26 → 11-05, each landing on its own day after ING-GO-B —
  separately dispatched under the re-run prompts, never one
  context. The dispatch context holds the engineering + the
  L0 opening + at most the first family leg (≈ 68k + 57.5k +
  52.5k + 24k ≈ **202k, tight but fitting**); each later leg is
  a fresh context with its own +0 verification. The recorded
  family-boundary seam stays available to the orchestrator at
  dispatch — a seam-stop mid-wave is a clean `blockedOn`, not
  a split this review needs to bake in. Splitting the row
  statically would also force the ING-GO-B gate cell and the
  window onto two suffix rows for no working-set gain.
- **P35.61 (row 338) — NOT split.** The L2 pause is a *hard*
  boundary by construction: the apply leg cannot start until
  the operator's verbatim in-ticket go with a recorded
  `--authority` scope, so L3 is always a separate dispatch
  under the re-run prompt. What stays in the dispatch context
  is audit + plan + packet assembly (≈ 58k + 57.5k + 52.5k +
  12k ≈ **180k — ok**). The candidate seam (audit/packet vs
  apply/freeze) would only formalise a boundary the pause
  already imposes.
- **P35.63 (row 341) — NOT split.** Same shape: the HG-11
  in-ticket pause between stage+readout and promote+rehearsal
  already forces two dispatches (≈ 67k + 57.5k + 52.5k + 12–24k
  ≈ **190–200k in the first, tight but fitting**). Splitting the
  row would duplicate the publication-window contract without
  shrinking either context's work.

The rest of the adversarial review:

- **Ordering:** no forward or unresolved `Depends on:` or
  `live:` edges — programmatic sweep over all 83 contracts,
  every live: target resolves to a chain row (0 errors;
  `check_order.py` over the plan CSV also 0).
- **Orphan seams:** none found. The carried seam — P34.40's
  `/v1/*` LB leg (deliverable 8d) — is honoured: 331 (P35.53)
  and 336 (P35.59) both carry `live:P34.40` (its L2) with the
  recorded fallback (the 11B OM-20 list names it, or the
  landed GB-Q4 pre-authorisation runs it). The leg-level
  live: edges the T3 line recorded (P34.43→P34.46,
  P34.45→P34.46, P34.21b→P34.21a/P34.18) sit where the 11B
  contracts that consume them expect.
- **Fragmented decisions:** none found. The scattered SIG-CONF-010
  owner correction is recorded in 337's notes (owner P35.60,
  not P37.45); the SEED-12a owner re-confirmations
  (SIG-OPS-007 → P35.2, SIG-SEC-008 → P35.1a/b, SIG-SEC-009 →
  P35.4, SIG-CONF-010 → P35.60) are carried by the written
  contracts; C-context recorded plan-note corrections (C6–C12)
  stand.
- **Coverage:** the regenerated index resolves every §56 id
  with an 11B owner — 38 ids, each listing exactly its owner
  row(s) and each owner contract listing the id (`owner
  contract lists it: yes` on all 38; SIG-SEC-008's a/b band is
  the only multi-owner pair, as the spec declares). Every
  SIG-TRANSP id maps to exactly one owner row — the 29 whose
  owner rows are 11C/11D skeletons (rows 386–466) read
  `owner contract is a skeleton`, expected: PLAN-11C/11D write
  those contracts. The 4 seed-owned §56 ids stand per §56.1.
  No contract lost a requirement in the split (291's Owner:
  SIG-SEC-008 line stays; 291a cites it — see the index).
- **Over-factoring:** not proposed — the five existing a/b
  splits keep disjoint halves; a further split of tight rows
  would double the row count for no working-set gain (the T3
  recorded tradeoff).
- **Live legs vs engineering runs:** separately-dispatched leg
  work (the Wave-A/B family legs, the post-pause legs of
  338/341, the OM-19 re-run prompts) is never counted as an
  engineering run — the counts below use only the manifest
  est-runs cells of ticket rows.

The split, landed (OM-03; `decompose-spec mode=extend`):

- **`291a_P35.1c__dispatcher-consolidation.md`** — new full
  contract at row **291a** under the same part-3 banner:
  `sig-sched-due` dispatcher build + deploy, the
  `[dispatcher]` declaration, the ~79 per-source trigger
  retirements, the closing 0-drift proof + consolidated cost
  record; `Depends on: P35.1b`; same window (AR-3 + AR-2), same
  OM-20 conditional, same B-13 `a` answer; 1.0 run; Load
  ≈ 60.7k ÷3.
- **`291_P35.1b__fleet-hygiene.md`** re-scoped to the sweep
  half (its own recorded seam) — landed as an **appended
  `> Amended 2026-10-06:` note** (BM-TICKET-04), not an
  in-place rewrite: the C13 commit's subject named the ticket
  id, so `memory_guard` judged the contract
  frozen-after-execution from that commit on (the docs-job
  red at `f9c407c8`, 147 violations; fixed forward by
  restoring the authored bytes + appending the note, with
  `history.policy` `seed-commit` declarations keyed to the
  two attributing commits — the `427c5efb` precedent; the
  branch rule forbids force-push). The
  amendment scopes the OM-14 mutation list, deliverables,
  ACs, clauses and re-run prompt to the sweep; the plan-cell
  Gate status kept verbatim; Load re-totalled ≈ 65.7k ÷3.
- Manifest: row `291a` inserted after 291 (suffix-letter
  insert convention, the `170a` precedent); a `## Plan
  extensions` line records the split; this section +
  `## Decomposition decisions` hold the review. `gen_t3.py
  check` (310 plan rows vs 310 CSV rows — the suffix insert is
  invisible to the T3 checker by design) and `check_order.py`
  both report 0 errors.

GATE-G4b re-split rule (deliverable 5; S6R-15) — **evaluated,
does not fire:**

- Engineering rows after the split: **82** (ticket kind across
  rows 261–343, excluding PLAN-11C 340 and GATE-G5 343;
  84 if the plan+gate rows are counted) — under 85.
- Engineering runs after the split: **74.5** (sum of the
  manifest est-runs cells of ticket rows; live legs and the
  PLAN row's fan-out excluded) — under 75.
- Both counts clear under either reading → no `GATE-G4b`
  marker is added after row 290; the banner boundary stays
  what it is for a later review.

Requirement index (deliverable 7 — regenerated, audited,
committed):

- `req_index.py write` + `check` → **`req_index: current`** —
  311 contracts scanned (144 full, 167 skeleton), 277 distinct
  ids cited, P35.1c present as `cited` on SIG-SEC-008 /
  SIG-OPS-005 / SIG-STORE-003 / SIG-ENG-042 (owner rows stay
  P35.1a/b as §56 declares).
- Tool patch recorded (in this commit):
  `req_index.py`'s map-row filter `int(r["row"])` would crash
  on a suffix-letter insert — now parses the numeric prefix
  (`291a` sorts under row 291). The generator's scan source is
  the T3 contract map, so `T3_contract_map.csv` gained the
  `291a` row (kind ticket / contract_kind full / completed_by
  PLAN-11B C13); `gen_t3.py check` still reads only plan-CSV
  rows against the map — 0 errors.
- Audit findings worth recording: the index's
  `owner contract does not (yet) list` list is 29 rows — all
  rows ≥ 344 (11C/11D skeletons), expected at this stage; the
  four seed-owned §56 ids stand; `SIG-TRANSP` 11B-owner rows
  all resolve (002/007/011/013/016/017/019/022/023/026/027/
  029/030/031) with no row owning two copies of the same id.

Draft 11B OM-20 list (deliverable 6 — built only from the
written `Production mutations (OM-14)` headers; expiry `the
next GATE` = GATE-G5 per each contract's own text; the
operator approves verbatim at GATE-G4; **nothing is
pre-authorised on silence** — an unlisted row pauses
in-ticket):

| row | mutation (from the contract's OM-14 block) | restore point / rollback | expires | voided-by |
|---|---|---|---|---|
| **P35.5** (262) | R2 bucket + CDN route config, release-object pushes to the R2 origin, the $50/mo egress alert thresholds, enabling the `mirrors.toml` R2 entry — all after OP-09 lands | disable the CDN route + `enabled = false`, delete pushed objects, revert thresholds; GCS stays origin of record | GATE-G5 | a red probe, a failed restore point, or a production read that contradicts a record |
| **P35.1a** (264) | `scheduled-ops` Scheduler creates/updates/deletes from `cadence.toml` (incl. the inert monthly-export trigger, gated on D-P34.6-2's own go) + the daily live-diff wiring into `sig-probe` | revert the cadence row + re-run `scheduled-ops`; `live-diff` mutates nothing | GATE-G5 | same |
| **P35.14a** (272) | INSERT-only `vocab_*` registrations (six predicates, genre stamps, Mobility crosswalk, group-13 rows) via the appended sqitch seed | forward-only — superseding registrations (slugs never reused); AR-2 backup + per-table counts precede | GATE-G5 | same |
| **P35.15a** (274) | INSERT-only `vocab_*` registrations for `technology` + new slugs | forward-only supersession; AR-2 backup precedes | GATE-G5 | same |
| **P35.15b** (275) | INSERT-only technology backfill claims (chunked `--apply`, `+0` re-run) | forward-only supersession; the run stops clean and resumes from checkpoint | GATE-G5 | same + the hosted vocabulary check failing (leg waits on `live:` P35.15a) |
| **P35.1b** (291) | the six named job deletions, the AR cleanup policy, the four cron reconciles, the `sig-export` guard roll, the `sig-alerts` disposition | AR-2 backup before the first delete; every delete's `describe` JSON saved; cadence rows reconcilable back; `sig-alerts` spec captured | GATE-G5 | same |
| **P35.1c** (291a) | the `sig-sched-due` dispatcher job + hourly trigger creation and the ~79 recorded per-source trigger retirements | per-trigger `describe` JSON saved verbatim; the per-source shape re-creatable from `cadence.toml`; dispatcher removed after triggers restored | GATE-G5 | same |
| **P35.16** (296) | append-only `geometry_defect`/correction claim inserts on the seven identified targets | additive writes; the pre-state capture is the record; a wrong claim is superseded, never deleted | GATE-G5 | same |
| **P35.17** (297) | OCFL captures of the boundary-source objects (TIGER ×3, Gazetteer ×2, NE admin-0/1, 500k) + the `jurisdictions` registry rows — only after the operator's separate HG-03 flips | additive OCFL objects; the pre-capture store state is the record; a wrong capture is superseded | GATE-G5 | same |
| **P35.22** (302) | new-identity minting on the next scheduled ingest of affected sources (camera-registry days 6–13 in window) + the `/status/` notice + label | stop minting under the new identity (a deploy revert) — no stored row is ever touched | GATE-G5 | same |
| **P35.24** (303) | one hosted re-key run appending re-keying correction claims + the `/status/` notice | forward-only — a reversal correction names the run's ids; the dry-run artifact is the replayable record | GATE-G5 | same |
| **P35.25** (304) | registry lineage declarations + the rematerialize back-populating `id_namespace`/lineage/independence | forward-only — a reversal materialization correction; never a delete | GATE-G5 | same |
| **P35.26** (305) | EFF + OSM re-ingest appending role/time-corrected claims + the edge rematerialize (inside existing ingestion permission; OSM leg inside the ODbL compartment) | forward-only corrections/materializations; claim-identity idempotent | GATE-G5 | same |
| **P35.27** (306) | one rematerialize recomputing resolved values + contradiction states | forward-only — a reversal correction names the run's rows | GATE-G5 | same |
| **P35.32** (310) | the `ingest_run_report` sqitch deploy + insert-only report rows (scheduled-ingest + the one-shot backfill) | `sqitch revert` + stopping the writer; the backfill is `+0`-idempotent | GATE-G5 | same |
| **P35.41** (320) | the connector-image roll (redeploy of the hosted ingest job family carrying the capture changes) | AR-2 restore point precedes; a roll-back to the prior digest | GATE-G5 | same |
| **P35.46** (325) | the ruleset-v3 ER run (append-only derivation links, site ids, possible-duplicate links, census and demotion records; never concurrent with `sig-materialize`) | forward-only — a reversal run names the run's rows; AR-2 restore point precedes | GATE-G5 | same |
| **P35.53** (331) | the three creates — private bucket (+lifecycle/IAM), two IAM-only staging services, `sig-release` job + `sig-release-rt` SA | each create is independently reversible (delete it); AR-2 restore point precedes; nothing existing is mutated | GATE-G5 | same |
| **P35.59** (336) | the legacy floor import (private-bucket writes), the `sig-web` revision roll, the serving-path retirement declaration | roll `sig-web` back to the prior digest; the import is additive; the retirement is a config revert; byte-compare failure → revert, never patch | GATE-G5 | same |
| **P35.62** (339) | `staged/` namespace object writes + staged artifacts on the IAM-only staging origins | an appended supersession record; immutable namespaces are never deleted | GATE-G5 | same |

Notes on the list:

- **Count is 20 rows, not 19** — GATE-G4's item-4 enumeration
  ("the 19 OM-20 rows of 11B") predates this split; the
  P35.1b mutations split across rows 291 + 291a, so the draft
  names both under the same conditional authority. The list
  above is the packet input; each entry is traceable to a
  contract header.
- **Never pre-authorised (unchanged):** P35.57 (261),
  P35.11 (271), P35.14b (273), P36.12 (290), P35.61 (338),
  P35.63 (341), and every HG-03 flip — P35.17's boundary flips
  included (in-ticket goes or the operator's own act).
- **P34.40's `/v1/*` leg (deliverable 8d):** not an 11B row —
  it is carried on this list per the recorded fallback only if
  still paused at GATE-G4 (else it runs under the landed
  GB-Q4 pre-authorisation); naming it here records the seam,
  it does not smuggle an authorisation.

ADR-171 outreach-owed list (deliverable 8a — the 11B part;
from the written contracts' outreach blocks, never inferred):

| row | connector/project it touches | ids owed — unmet at launch (ADR-171, `D-R11-LATER-04`) |
|---|---|---|
| **P35.6** (266) | connector-registration plumbing — every compact/ecosystem-adjacent source flows through it | SIG-CHART-033, SIG-INGEST-029, SIG-INGEST-030a, SIG-CONTRIB-012, SIG-CONTRIB-012a, SIG-CONTRIB-013, SIG-GOV-024 |
| **P35.11** (271) | Wave-A activation — activates connector behaviour incl. the three manual first runs + the tribal S8 screened lane | the same seven |
| **P36.74** (289) | the Flock portal probe — the §22.5 Eyes on Flock relationship (probe only; EoF stays a read-side mirror) | the same seven |
| **P36.12** (290) | Wave-B activation — ~89 sources, seven widen targets, the probe leg | the same seven |

- Every other 11B contract records *why the set does not
  apply* (no §6 compact-table or §22.4–22.5/§35.1 ecosystem
  connector written, widened or activated) and re-states the
  set as owed-unmet — audited programmatically: **no 11B
  contract stamps any of the seven ids satisfied** (the only
  "satisfied" hits are the verbatim disclaimer "None is
  stamped satisfied").
- Trigger (every row): **the operator authorises outside
  contact**. No outside contact made or implied anywhere
  (ADR-171 Decision 3, U-011); no operator e-mail address in
  any file.
- Handed on: PLAN-11C (row 340 — its own deliverable 7a
  carries the 11C part; P36.77's DocumentCloud/MuckRock row
  leaves the set unmet) and PLAN-11D (the contribution-back
  rows); GATE-ANNOUNCE's "spec MUSTs unmet at launch" list is
  where the operator signs it verbatim (plan §13.5, row 510).

Placements confirmed (deliverable 8b/8c — verified against the
written contracts, not just the Plan-extensions line):

- **Tribal S8 screened lane** — `AP-T2-201` (`dot_511`
  arcgis_query; IND-TRIBAL) and `AP-T2-210`
  (`dossier_documents`; IND-TRIBAL) **stay in P35.11** (row
  271): its contract's deliverable 5 lands both under ADR-185
  (screened lane, no outside contact, facts/citations or
  screened metadata only, the no-human-review disclosure) and
  names `AP-T2-093` (`doj_ctas_awards`; IND-P8, **not**
  IND-TRIBAL) as excluded under `D-R11-LATER-09`;
  `CG-LATER-tribal-data-governance-rule-i7-new-6` stays OPEN.
  P36.12's contract repeats both placements for Wave B.
  Confirmed — no change.
- **`D-R11-OSMUID-1`** — **stays handed to P37.1** (row 344,
  "OSM as a camera-site origin (code)"; PLAN-11C authors the
  contract). The review's re-route option was examined: the
  fix is a capture-side connector-code change (`extract()` /
  the Overpass query) and **no 11B row owns an OSM connector
  change**; P35.26 (305) re-ingests EFF/OSM before 11C lands
  but does so under the deferral's stated compensating
  controls (the pre-claim discard + P34.49's capture seal),
  which its contract records verbatim in the outreach/OSMUID
  caveat. The hand-off route (parent-contract deliverable-8
  AC + Plan-extensions line) is sound — confirmed, not
  re-routed.

Verification (this context; recorded with limits):

- `req_index.py check` — `req_index: current` (311 contracts
  scanned after the insert; the check re-derives the file and
  byte-compares).
- `check_order.py` — 0 errors; totals 310 rows / eng runs
  285.5 (the suffix insert is a manifest row invisible to the
  plan-CSV checker; order recorded by the banner convention).
- `gen_t3.py check` — `310 Round-11 manifest rows, 310 plan
  rows, errors 0` (the insert does not disturb the 1:1
  comparison; no stray-file flag — `291a_*` is outside the
  checker's 3-digit glob, recorded).
- `make check` — green: ruff clean, format clean, mypy 313
  files clean, **pytest 6,495 passed / 464 skipped / 0 failed**
  (333.52 s — the P34.33 baseline exactly; a docs/tools-only
  change), `verify-gen` clean. **Recorded limits:** the PATH
  docker stub + `SIG_GCP_PROJECT=sig-local-sentinel`
  (Docker daemon unreachable locally — the C1-recorded
  wedge; the Docker-gated `tests/db`/`tests/e2e`/`test_web_iac`
  rows skipped and run in CI). First bare `make check` attempt
  hung in the Docker probe — re-run under the recorded stub.
- `make docs-check` — green on every leg except the
  expected-stale `docs-check-projection` at this point in the
  sequence (the projection names the changed files; it is
  regenerated after the ledger write and before the commit —
  the C1/C12 ordering rule): freshness detectors 0 broken
  refs, build-memory 0 violations (41 pre-existing warnings,
  none C13's), spec-src byte-identical (852,023 B), coverage
  820/820, backlog/ledger-contract/audit (9 covered conflicts,
  same set)/obligation-events (636) all clean, return_pass 0.
- `check_spec_src.py` — OK (38/38 src, 191/191 appendix-f,
  1,644/1,644 ids).
- `check_coverage_matrix.py docs/build/COVERAGE_MATRIX.csv` —
  820/820 rows OK.
- `memory_guard.py all --staged` — 0 violations (1,030 items)
  before the content commit.
- Docker limitation stands (recorded C1): locally-green
  `(tests/db, tests/e2e, test_web_iac docker rows not run:
  daemon unreachable)` — CI is the authority for them.

Boundary (OM-05) — appended after the pushes:

- `f9c407c8` — pushed ≈13:38Z; **docs red at the history
  guard** (147 `append-only` findings on
  `291_P35.1b__fleet-hygiene.md` — the commit subject named
  the ticket ids, so `executed()` marked the contract
  executing mid-range and the sanctioned C6 skeleton→contract
  rewrite plus the C13 re-scope read as frozen-contract
  edits). `ci_boundary` verdict at the same read:
  `blockedOn: CI stack on #236@f9c407c (external): off-stack
  merge #190 (`devin/p33-8-agent-docs-refresh` → `main`) into
  main at 2026-10-06T12:15:59Z — not a chain row (since
  2026-10-05T10:55:21Z)` (ci_boundary ≈13:40Z — external
  operator stack integration, not a chain row defect;
  `logs/ci-PLAN-11B-C13-content.json`). Fixed forward:
  `08c1840b` (≈13:50Z) restores the authored bytes + appends
  the split as a conforming `> Amended` note, `4c622b1d`
  (≈13:58Z) declares the `seed-commit` exemptions keyed to
  the attributing commits (the `427c5efb`/C3 precedent — the
  branch rule forbids force-push) → range guard **0
  violations / 17,394 evaluated** (the same `check-history`
  leg green in the `4c622b1d` docs job).
- `4c622b1d` — docs red on `docs-check-projection` only (the
  restore/policy digests advanced past the committed
  snapshot — expected-stale mid-sequence); history guard
  green. Boundary: `blockedOn: CI stack on #236@4c622b1
  (external): off-stack merge #190 … same line` (ci_boundary
  ≈14:05Z — `logs/ci-PLAN-11B-C13-fixhead.json`; the
  external scan lists nine merges #185–#195 since the last
  recorded boundary — the operator's stack integration in
  flight).
- `369ec6f6` — pushed ≈14:08Z; docs red on
  `docs-check-projection` **again** — recorded not smoothed:
  the regen commit carried `reports/current/` but left the
  edited `runs/PLAN-11B.md`/`LEDGER.md` sources uncommitted,
  so the recorded digest mismatched the pushed file
  (recorded 5646cc1e… vs pushed 8e31704e… — job
  `112312874850` in run `37476415068`). The full closeout
  commit lands sources + regen together.
- The closeout head's read lands in the post-closeout
  record commit per convention.

Close record — appended at closeout (OM-02, one commit after
the PR exists).

- PLAN-11B closed by C13: all **83** ratified 11B chain rows
  (261–343) carry execution-grade contracts; the Phase-4
  sizing review split row 291 exactly once — new suffix row
  **291a / P35.1c** `docs/tickets/291a_P35.1c__dispatcher-consolidation.md`
  holds dispatcher consolidation + the closing proof;
  P35.1b keeps the sweep half (amended in place via a
  conforming `> Amended 2026-10-06:` note, BM-TICKET-04).
  Post-split: **82 engineering rows / 74.5 engineering runs**
  — both under the GATE-G4b thresholds (85 / 75), so G4b
  does not fire. `REQUIREMENT_INDEX_R11.md` regenerated and
  verified (`req_index.py check` current; 291a cited; the
  suffix-row parser fix keyed on the numeric prefix). The
  OM-20 list (20 rows), the ADR-171 outreach-owed list, the
  tribal-member placement and the `D-R11-OSMUID-1` placement
  are recorded in the C13 section above.
- Verification at closeout: `make check` green (ruff /
  format / mypy 313 files / 6,495 passed · 464 skipped · 0
  failed / verify-gen byte-identical); `check_order.py` 0
  errors; `gen_t3.py check` 310 manifest rows = 310 plan
  rows, 0 errors; `check_spec_src.py` 38/38 · 191/191 ·
  1,644/1,644; `check_coverage_matrix.py` 820/820;
  `memory_guard.py all --staged` 0 violations; projection
  fresh (156 obligations · 87 owed · 636 events · 245
  assessments · 0 known inconsistencies · 974/974 digests).
  Docker-gated legs (tests/db, tests/e2e, web IaC) remain
  CI-authoritative — the daemon is unreachable locally.
- Boundary sequence recorded verbatim above: heads
  `f9c407c8` / `4c622b1d` / `369ec6f6` each carried docs-red
  findings that were fixed forward (history-guard executed()
  attribution → `seed-commit` exemption + appended Amended
  note; projection regen split from its sources → committed
  together here), and every boundary read returned
  `blockedOn … (external)` — off-stack merges #185–#195 into
  `main` (the operator's 10-06 stack integration, since
  2026-10-06T12:15:59Z) — not a chain-row defect. The
  closeout head's check-run verdict lands in the
  post-closeout record commit per convention; no `ci: pass`
  is claimed for a head whose five required check-runs did
  not all succeed.
- Deferrals/deviations: none new — this is a planning row
  (OM-14 n/a); production mutations, outreach sends, tribal
  governance and `D-R11-OSMUID-1` implementation stay owed
  to their owning rows. chainTip →
  `r11/PLAN-11B-contracts-for-11b-and-transp-family`
  (PR #236); next → **P34.48** (manifest row 240).

## OM gap table

One row per operating clause of the contract's B5 §6.2 / H2 §7 block;
filled per context.

| clause | status | note |
|---|---|---|
| OM-01 harness/model recorded; commits trailered | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13) | header + every commit trailer `Harness: devin-desktop/swe-2-high/subagent` |
| OM-04 dates from `date -u` / git / GitHub (source named) | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13) | header Started from `date -u`; C2/C3/C4/C5/C6/C7/C8/C9 Started from file mtime (source named); C7/C8/C9 Closed from `date -u`; C10 Started + Closed from `date -u` (file mtimes read earlier than wall clock — a recorded anomaly, `date -u` anchored); C11 Started from `date -u` (file mtimes read 01:59–02:03 vs wall clock ~05:59–06:03 — the same recorded local-clock offset, `date -u` anchored); C12 Started from `date -u` (resumed context — contract writes began ~06:23Z); C13 Started + Closed from `date -u` (resumed context across two compactions — the sizing review ran ~13:0xZ, fix-forwards through ~14:0xZ) |
| OM-05 CI read at every boundary; red → blockedOn | ok (C1, C2, C4, C5, C6, C7, C8, C9, C10, C11, C12); C3 + C13 blockedOn | @9dcb023 blockedOn (docs/projection stale — fixed forward) → `ci: pass #236@70ab52a` 5/5 head-bound (log `logs/ci-PLAN-11B-C1.json`); C2 `ci: pass #236@60c3fe4` 5/5 head-bound (log `logs/ci-PLAN-11B-C2.json`); C3 @427c5ef blockedOn (docs history guard — `seed-commit` fix-forward; docs+python green on 8920c46) → three hosted-runner acquisition cancels (@e34dd7c composed, @8920c46 web, @a5a0b96 python) — infra, reported blockedOn (log `logs/ci-PLAN-11B-C3.json`); C4 @5877a44 + @917db14 blockedOn on infra cancels (python run 37372747692; docs+web run 37374430350 — each re-read once) → `ci: pass #236@ec24cab` 5/5 head-bound (log `logs/ci-PLAN-11B-C4.json`); C5 `ci: pass #236@5238ded` 5/5 head-bound, first head (run 37381411791; log `logs/ci-PLAN-11B-C5.json`); C6 `ci: pass #236@0dc6bc1` 5/5 head-bound (log `logs/ci-PLAN-11B-C6.json`); C7 @2c2ef14a blockedOn (security npm advisory gate — new advisory GHSA-68fv-2mgg-jv7q on source-map-js 1.2.1, advisory-feed timing not the docs change) → fix-forward bump to 1.2.2 (upstream fix, surgical lockfile edit, `blocked=0` locally) → `ci: pass #236@5479f60` 5/5 head-bound (run 37404618425; log `logs/ci-PLAN-11B-C7.json`); C8 `ci: pass #236@acde44e` 5/5 head-bound, first head (run 37407963600; log `logs/ci-PLAN-11B-C8.json`); C9 `ci: pass #236@3670b7e` 5/5 head-bound, first head (run 37411758538; log `logs/ci-PLAN-11B-C9.json`); C10 `ci: pass #236@80193e2` 5/5 head-bound, first head (run 37420161300; log `logs/ci-PLAN-11B-C10.json`); C11 `ci: pass #236@6fccb08` 5/5 head-bound, first head (run 37422175926; log `logs/ci-PLAN-11B-C11.json`); C12 @458e89a blockedOn (docs `docs-check-projection` run-ledger digest stale — regen-before-ledger-write ordering, the same shape C1's first head hit; `04c5cd70` red on it too) → fix-forward `fce5643` regen → `ci: pass #236@fce5643` 5/5 head-bound (run 37425285698; log `logs/ci-PLAN-11B-C12.json`); C13 @f9c407c8 blockedOn (docs history-guard red — 147 append-only findings on `291_P35.1b__fleet-hygiene.md`: the commit subject named the ticket ids → `executed()` attribution; fixed forward by `08c1840b` restore+appended-`Amended` + `4c622b1d` `seed-commit` policy lines, the 427c5efb/C3 precedent — range guard 0/17,394 green on the `4c622b1d` docs job) → @4c622b1d blockedOn (docs `docs-check-projection` stale — expected mid-sequence) → @369ec6f6 blockedOn (docs `docs-check-projection` stale — regen landed without its ledger sources; committed together in the closeout) + every head's read `blockedOn … (external)` — off-stack merges #185–#195 → `main` since 2026-10-06T12:15:59Z (operator stack integration, not chain red; logs `logs/ci-PLAN-11B-C13-content.json` / `-fixhead.json` / `-projhead.json`) → the closeout-head verdict lands in the post-closeout record |
| OM-06 every AC names its layer | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13) | each contract's ACs tag a layer (engineered / fixture-verified / staging-verified / live-executed / public / human-completed) |
| OM-14 production mutations | n/a | none — planning row |
| OM-13 protected records appended only | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13) | manifest Plan-extensions + ledger C2/C3/C4/C5/C6/C7/C8/C9/C10/C11/C12 sections appended only (C9's + C10's + C11's + C12's sections replace their `### Cn — pending` placeholders, the established convention); C3 adds a `seed-commit` policy line for its own rewrite commit (recorded, scoped to 427c5efb); C4's + C6's + C7's + C8's + C9's + C10's + C11's + C12's rewrite commits name no ticket ids in their subjects; C13's f9c407c8 named 291's ticket ids → `executed()` flagged the base-existing contract mid-range (147 findings) → fixed forward, never hidden: `08c1840b` restored the authored bytes + landed the re-scope as a conforming appended `> Amended 2026-10-06:` note, `4c622b1d` declared `seed-commit` policy lines keyed to the attributing commits (recorded, scoped — the C3 precedent); memory_guard --staged run pre-commit |
| OM-15 no test asserts a living record's current value | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13) | no test touched by C3, C4, C5, C6, C7, C8, C9, C10, C11, C12 or C13 (C13's `req_index.py` edit is a tool source change — the numeric-prefix row parser — no test file touched) |
| OM-07/08/09 gate records verbatim | ok (C2, C3, C4, C5, C6, C7, C8) | gate cells carried verbatim from the plan rows (X4 `approve`, C9 `a`, ING-GO-A verbatim-at-GATE-G4, C3's OM-20 conditional ×3 + never-pre-authorised + HG-03 ×2, C4's HG-03 RB-lines ×6; C5's HG-03 RB-04/RB-06 + WV-10/D3-Q3 verbatim + ING-GO-B; C6's G1-TRIM B-13 `a` + OM-20 conditionals ×3 (291/296/297) + D-K4-1/2/4 verbatim + HG-03 operator-flip; C7's `none` ×3 (299/300/301) + `named-mutation → OM-20 conditional; otherwise in-ticket pause` ×5 (302–306) verbatim; C8's D-K2-1 [A-10] `b + c` ×2 (307/308) + D-J3-2 [B-19] `yes` (311) + D-J3-1 [B-19] `raw-ok only` + D-J3-5 [B-19] `no` (313) + the named-mutation OM-20 conditional (310) + `none` ×2 (312/314) verbatim; the SEED-12b withheld-amendment carry on 312 recorded verbatim; C9's Q-E2-03 [B-6] `Move UA, don't buy domain` (317) + the named-mutation OM-20 conditional with expiry + in-ticket pause (320) + `none` ×6 (315/316/318/319/321/322) verbatim; C10's D-K4-3 [B-44] `as recommended (county + place pages)` (324) + the conditional OM-20 gate Q-L3-6 [B-31] = a · Q-L3-1 [A-6] = a (325) + D-K13-4 [B-26] `yes` + the P35.63/HG-11 publication ride (326) + Q-L3-4 [B-31] `no` (327) + D-K0-1 [A-12] `a` (328) + `none` ×3 (323/329/330) verbatim; C11's named-mutation OM-20 conditionals ×2 (331 — private release bucket + staging services + sig-release job; 336 — dark cutover with byte-compare + no-visible-change) + D-G3-10 [B-9] `yes` (331) + `none` ×3 (332/333/334) + D-G3-8 [B-9] `yes (auto-rollback pre-authorised)` (335) + D-G3-3 [B-9] `a` (337) verbatim; C12's never-pre-authorised in-ticket pause `explicit go + recorded --authority scope` (338) + the named-mutation OM-20 conditional `(staged candidate; no publication)` (339) + `none (plan only, OM-03)` (340) + the HG-11 in-ticket pause `candidate-specific readout signed verbatim … no OPCHECK: Q-L3-3 = c … Q-9/G2-HOTFIX [B-7] = a` (341) + `none` (342) + the S5-2 gate cell `continue answers batch lines only … silence = pause (OM-18), never consent` (343) verbatim; C13's new row 291a carries 291's gate cells verbatim — the G1-TRIM B-13 `a` answer, the same window and the same named-mutation OM-20 conditional — and declares its dep on P35.1b explicitly); nothing decided by this row |
| OM-16 size budget | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, C12, C13) | C1 = transparency family + 5 contracts + test/projection fixes; C2 = 6 contracts + manifest/ledger lines; C3 = 7 contracts + policy/ledger lines; C4 = 6 contracts + ledger lines; C5 = 6 contracts (five verified + row 290 written) + ledger lines; C6 = 8 contracts + ledger lines + projection regen; C7 = 8 contracts + ledger lines + projection regen; C8 = 8 contracts + ledger lines + projection regen; C9 = 8 contracts + ledger lines + projection regen; C10 = 3 verified drafts + 5 written contracts + ledger lines + projection regen; C11 = 7 contracts + ledger lines + projection regen; C12 = 6 contracts + ledger lines + projection regen; C13 = the Phase-4 sizing review across 83 contracts + 1 new contract (291a/P35.1c) + 291's appended `Amended` note + manifest/contract-map/req-index/history-policy/LEDGER lines + projection regen; within a single context |
| OM-02 closeout is one commit after the PR exists | pending | C13 |
| OM-19 windows / live legs | n/a | none for this row (each written contract carries its own — C7's contracts carry the verbatim live windows/legs: camera-registry days 6–13 (302) + AR-3 + AR-2 (303–306) + EFF/OSM re-ingest + rematerializes; C8's 310 carries `AR-3 + AR-2` + one leg + the header re-run prompt under the OM-20 listing; C9's 320 carries `AR-3 + AR-2` + the connector-roll leg under the same conditional; C10's 325 carries `AR-3 + AR-2` + the ER leg under the conditional OM-20 gate, and 326 carries `AR-3 + AR-2` + live stage `publish` as P35.63's leg (the carry-shape of C9's 320); C11's 331 carries `AR-3 + AR-2` + the infra-create leg + re-run prompt, and 336 carries `AR-3 + AR-2` + the cutover leg + re-run prompt — both under the OM-20 listing; C12's 338 carries `AR-3 + AR-2; >= 48 h after P34.46; after the 11B spine writes (P35.14-P35.46)` + three legs (audit+plan / operator pause / apply+freeze) + re-run prompt under its never-pre-authorised pause, 339 carries `staging only` + the OM-19 re-run prompt, 341 carries `release cut never inside AR-3 windows (G3 §7.2); 14:00-20:00Z; operator available for HG-11` + two legs (stage+V1–V15+readout / promote+rehearsal) + re-run prompt, and 342 carries `after P35.63 promotion` read-only — 343 names none); C13's 291a carries 291's window verbatim (the split keeps one cell) |
| OM-20 pre-authorisation | n/a | not an OM-20 row (C7's contracts carry the conditional verbatim — five rows' live legs queue behind the operator's named-mutation pre-authorisation; C8's 310 carries the same conditional for its hosted change + backfill; C9's 320 carries it for the connector-image roll — mutation list named in-contract, otherwise in-ticket pause; C10's 325 carries the conditional gate verbatim — its ER leg queues behind the operator's named-mutation pre-authorisation; C11's 331 carries the conditional for the private bucket + staging services + job/SA creates, and 336 carries it for the dark cutover — both with named mutation lists, otherwise in-ticket pause; C12's 339 carries the conditional for the staged candidate — mutation list named in-contract, otherwise in-ticket pause; 338 and 341 carry their never-pre-authorised pauses verbatim; C13's 291a carries 291's named-mutation OM-20 conditional verbatim — the dispatcher-consolidation live leg queues behind the same operator pre-authorisation) |
| OM-03 rows only from the ratified plan | ok | rows 261–306 are the ratified chain rows; placements landed via a Plan-extensions line, no renumber; the dep corrections (P36.3 → 277, P36.4 → 279), C6's recorded plan-note corrections (291's copied unsplit-scope notes; 296/297/298's "no §56 Owner" → findings/cited ids), C7's recorded notes (299's S2 ordering-only edge; 300/301's shared F-134 column → a-half owns, b-half serves; 300's K4-P9 DSRC-01 seam resolution; 302's no-mass-re-mint live-stage reading; 303's 5,278 re-derive-not-assume; 304/306's "production write = appends" readings; 305's missing S6 clause + EFF/OSM-only leg scope) and C8's recorded notes (307's UXR-17 draft-ref + soft prerequisite edges; 308's draft SIG-EXPORT-D21 + findings not §56 Owner; 309's interim lane basis; 310's C-14 unmatched/repo-record rows + `per_fetch` column split with 312; 311's verdict-function handoff to P35.41; 312's SEED-12b MUST-carried disposition + `/v1/changes` out; 313's C-6 same-field wording + interim-basis replacement; 314's helper-before-consumers / sweep-stays-P36.66a) and C9's recorded notes (315's SIG-TRANSP-012 stub-pending-TX-08b; 317's stale-literal enumeration + declined defensive-registration residual risk + no-§56-Owner record; 318's Depends-line rewording fix-forward — the audit parsed "the P35.38 split" as a dep on a non-existent row; 319's old-counts 178/218/219/208/236/342 named-predicate reconciliation; 320's connector-roll mutation list + `0 stale` never-for-unevaluable rule; 322's no-§56-Owner record + F-481 producer gap verified + the later watch rows' split recorded + K7 §8 draft ids deferred to PLAN-11C) and C10's recorded notes (326's publish-rides-P35.63 carry-shape + GQ-10 measured-not-assumed ratchet + DSRC-04 export-half mapping; 327's S1b-vs-S6 OPCHECK reconciliation superseded-half record + `D-R11-LATER-18` second-family placement; 328's SEED-11 informational-dep + no-§56-Owner record + `UXR-02` draft id deferred to PLAN-11C + the islands.spec.ts superseded-in-place seam; 329's SIG-FIND-005 Owner-stays-P32.15 record + island-budgets.json supersession seam + CI-8 declared-yes + the measured /map/ 497 KB gap; 330's F-104/F-414 owned + ADR-156 write-up + the MAP-03 rendering seam + MAP-01b property-payload seam + CI-8 declared-yes) and C11's recorded notes (331's derived-leg reading — the plan cell enumerates no legs so the contract derives one from the creates + the probe AC; 332's `error_page`-surface preservation + approval-check-reads-never-writes; 333's 10/15-minute targets recorded-as-measured-at-REL-11 + purge-hooks-dormant-until-TX-11; 334's SIG-REL-007 `Also:` placement (owner stays P35.58) + the 2%-vs-monthly-audit seam; 335's V14-emits-never-classifies + the V15 hook-point hosted not re-implemented; 336's no-§56-Owner record + the `live:P34.40` 8d seam + `D-R11-LATER-20`'s clock anchored on the landing date + serving-path-retires-not-the-bucket under D-G3-7; 337's **SIG-CONF-010 seam correction — owner is P35.60, P37.45 is an `Also:` placement** + agent-drafted standing-go/readout texts labelled never-implied-adopted + no operator e-mail in files) are recorded in-contract, not in the plan; C13's Phase-4 split inserts suffix row 291a (P35.1c — dispatcher consolidation + closing proof) directly after 291 under the same Part-3 banner via a Plan-extensions line — no renumbering, the 82-row / 74.5-run post-split counts stay under GATE-G4b's 85/75 so no re-split marker lands |
| PR-1 branch from chainTip; PR base = previous branch | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11) | branch from `0de78f39`; PR #236 base `r11/P34.33-round-close-record-checks` |
| CI-2/CI-6 pre-closeout head green | pending | C13 |
| P11 local gate | ok (C1, C2, C3, C4, C5, C6, C7, C8, C9, C10, C11, with recorded limits) | `make docs-check` + `make check` green with the PATH docker stub + `SIG_GCP_PROJECT=sig-local-sentinel`; Docker-gated suites skipped locally, run in CI; C3/C4/C5/C6/C7/C8/C9/C10/C11 touched no code (docs-check + projection regen locally; C9's first docs-check caught a Depends-line prose dep → reworded, re-run green) |
| CI-8 CI config changed | no (PLAN-11B itself); C10's contracts 329/330 declare CI-8 `yes` in-contract for their own rows' CI wiring | |
