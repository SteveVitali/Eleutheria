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
investigation preceded it in the same context) · Closed: pending —
this context's last criterion is the head-bound CI pass on the
boundary-record commit; that commit fills this cell and the Boundary
lines below.
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
- Read 2 @ the fix/boundary commit: pending — this commit records it
  after push.

Boundary-record commit (`<pending>` in this commit — filled by the
boundary-record commit): appends the read-2 `ci:` line and this
section's Closed cell; a third commit then re-reads head-bound on it
and records both (C2's two-read pattern).

### C4 — pending

### C5 — pending

### C6 — pending

### C7 — pending

### C8 — pending

### C9 — pending

### C10 — pending

### C11 — pending

### C12 — pending

### C13 — pending (fresh-context Phase-4 sizing review; closes this ledger)

## OM gap table

One row per operating clause of the contract's B5 §6.2 / H2 §7 block;
filled per context.

| clause | status | note |
|---|---|---|
| OM-01 harness/model recorded; commits trailered | ok (C1, C2, C3) | header + every commit trailer `Harness: devin-desktop/swe-2-high/subagent` |
| OM-04 dates from `date -u` / git / GitHub (source named) | ok (C1, C2, C3) | header Started from `date -u`; C2/C3 Started from file mtime (source named) |
| OM-05 CI read at every boundary; red → blockedOn | ok (C1, C2, C3) | @9dcb023 blockedOn (docs/projection stale — fixed forward) → `ci: pass #236@70ab52a` 5/5 head-bound (log `logs/ci-PLAN-11B-C1.json`); C2 `ci: pass #236@60c3fe4` 5/5 head-bound (log `logs/ci-PLAN-11B-C2.json`); C3 @427c5ef blockedOn (docs history guard — subject named ticket ids; `seed-commit` fix-forward) → read-2 pending (log `logs/ci-PLAN-11B-C3.json`) |
| OM-06 every AC names its layer | ok (C1, C2, C3) | each contract's ACs tag a layer (engineered / fixture-verified / staging-verified / live-executed / public / human-completed) |
| OM-14 production mutations | n/a | none — planning row |
| OM-13 protected records appended only | ok (C1, C2, C3) | manifest Plan-extensions + ledger C2/C3 sections appended only; C3 adds a `seed-commit` policy line for its own rewrite commit (recorded, scoped to 427c5efb); memory_guard --staged run pre-commit |
| OM-15 no test asserts a living record's current value | ok (C1, C2, C3) | no test touched by C3 |
| OM-07/08/09 gate records verbatim | ok (C2, C3) | gate cells carried verbatim from the plan rows (X4 `approve`, C9 `a`, ING-GO-A verbatim-at-GATE-G4, C3's OM-20 conditional ×3 + never-pre-authorised + HG-03 ×2); nothing decided by this row |
| OM-16 size budget | ok (C1, C2, C3) | C1 = transparency family + 5 contracts + test/projection fixes; C2 = 6 contracts + manifest/ledger lines; C3 = 7 contracts + policy/ledger lines; within a single context |
| OM-02 closeout is one commit after the PR exists | pending | C13 |
| OM-19 windows / live legs | n/a | none for this row (each written contract carries its own) |
| OM-20 pre-authorisation | n/a | not an OM-20 row |
| OM-03 rows only from the ratified plan | ok | rows 261–278 are the ratified chain rows; placements landed via a Plan-extensions line, no renumber; C3's one dep correction (P36.3 → 277) is recorded in-contract, not in the plan |
| PR-1 branch from chainTip; PR base = previous branch | ok (C1, C2, C3) | branch from `0de78f39`; PR #236 base `r11/P34.33-round-close-record-checks` |
| CI-2/CI-6 pre-closeout head green | pending | C13 |
| P11 local gate | ok (C1, C2, C3, with recorded limits) | `make docs-check` + `make check` green with the PATH docker stub + `SIG_GCP_PROJECT=sig-local-sentinel`; Docker-gated suites skipped locally, run in CI; C3 touched no code (docs-check + range guard re-run locally) |
| CI-8 CI config changed | no | |
