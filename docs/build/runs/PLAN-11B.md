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
2026-10-06T0x:xxZ (`date -u`; last C8 criterion = the head-bound CI
read at the content+ledger head — see Boundary).
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

- Recorded below — the head-bound read at the content+ledger head
  lands in `docs/build/logs/ci-PLAN-11B-C8.json` (gitignored);
  the verbatim `ci:` line is appended here after the read.

Close record (this commit): appends the head-bound read and fills
Closed — work complete. The shared `Closed:` header stays
unwritten — C13 owns closeout.

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
| OM-01 harness/model recorded; commits trailered | ok (C1, C2, C3, C4, C5, C6, C7, C8) | header + every commit trailer `Harness: devin-desktop/swe-2-high/subagent` |
| OM-04 dates from `date -u` / git / GitHub (source named) | ok (C1, C2, C3, C4, C5, C6, C7, C8) | header Started from `date -u`; C2/C3/C4/C5/C6/C7/C8 Started from file mtime (source named); C7/C8 Closed from `date -u` |
| OM-05 CI read at every boundary; red → blockedOn | ok (C1, C2, C4, C5, C6, C7); C3 blockedOn | @9dcb023 blockedOn (docs/projection stale — fixed forward) → `ci: pass #236@70ab52a` 5/5 head-bound (log `logs/ci-PLAN-11B-C1.json`); C2 `ci: pass #236@60c3fe4` 5/5 head-bound (log `logs/ci-PLAN-11B-C2.json`); C3 @427c5ef blockedOn (docs history guard — `seed-commit` fix-forward; docs+python green on 8920c46) → three hosted-runner acquisition cancels (@e34dd7c composed, @8920c46 web, @a5a0b96 python) — infra, reported blockedOn (log `logs/ci-PLAN-11B-C3.json`); C4 @5877a44 + @917db14 blockedOn on infra cancels (python run 37372747692; docs+web run 37374430350 — each re-read once) → `ci: pass #236@ec24cab` 5/5 head-bound (log `logs/ci-PLAN-11B-C4.json`); C5 `ci: pass #236@5238ded` 5/5 head-bound, first head (run 37381411791; log `logs/ci-PLAN-11B-C5.json`); C6 `ci: pass #236@0dc6bc1` 5/5 head-bound (log `logs/ci-PLAN-11B-C6.json`); C7 @2c2ef14a blockedOn (security npm advisory gate — new advisory GHSA-68fv-2mgg-jv7q on source-map-js 1.2.1, advisory-feed timing not the docs change) → fix-forward bump to 1.2.2 (upstream fix, surgical lockfile edit, `blocked=0` locally) → `ci: pass #236@5479f60` 5/5 head-bound (run 37404618425; log `logs/ci-PLAN-11B-C7.json`); C8 — see the C8 Boundary line (log `logs/ci-PLAN-11B-C8.json`) |
| OM-06 every AC names its layer | ok (C1, C2, C3, C4, C5, C6, C7, C8) | each contract's ACs tag a layer (engineered / fixture-verified / staging-verified / live-executed / public / human-completed) |
| OM-14 production mutations | n/a | none — planning row |
| OM-13 protected records appended only | ok (C1, C2, C3, C4, C5, C6, C7, C8) | manifest Plan-extensions + ledger C2/C3/C4/C5/C6/C7/C8 sections appended only; C3 adds a `seed-commit` policy line for its own rewrite commit (recorded, scoped to 427c5efb); C4's + C6's + C7's + C8's rewrite commits name no ticket ids in their subjects; memory_guard --staged run pre-commit |
| OM-15 no test asserts a living record's current value | ok (C1, C2, C3, C4, C5, C6, C7, C8) | no test touched by C3, C4, C5, C6, C7 or C8 |
| OM-07/08/09 gate records verbatim | ok (C2, C3, C4, C5, C6, C7, C8) | gate cells carried verbatim from the plan rows (X4 `approve`, C9 `a`, ING-GO-A verbatim-at-GATE-G4, C3's OM-20 conditional ×3 + never-pre-authorised + HG-03 ×2, C4's HG-03 RB-lines ×6; C5's HG-03 RB-04/RB-06 + WV-10/D3-Q3 verbatim + ING-GO-B; C6's G1-TRIM B-13 `a` + OM-20 conditionals ×3 (291/296/297) + D-K4-1/2/4 verbatim + HG-03 operator-flip; C7's `none` ×3 (299/300/301) + `named-mutation → OM-20 conditional; otherwise in-ticket pause` ×5 (302–306) verbatim; C8's D-K2-1 [A-10] `b + c` ×2 (307/308) + D-J3-2 [B-19] `yes` (311) + D-J3-1 [B-19] `raw-ok only` + D-J3-5 [B-19] `no` (313) + the named-mutation OM-20 conditional (310) + `none` ×2 (312/314) verbatim; the SEED-12b withheld-amendment carry on 312 recorded verbatim); nothing decided by this row |
| OM-16 size budget | ok (C1, C2, C3, C4, C5, C6, C7, C8) | C1 = transparency family + 5 contracts + test/projection fixes; C2 = 6 contracts + manifest/ledger lines; C3 = 7 contracts + policy/ledger lines; C4 = 6 contracts + ledger lines; C5 = 6 contracts (five verified + row 290 written) + ledger lines; C6 = 8 contracts + ledger lines + projection regen; C7 = 8 contracts + ledger lines + projection regen; C8 = 8 contracts + ledger lines + projection regen; within a single context |
| OM-02 closeout is one commit after the PR exists | pending | C13 |
| OM-19 windows / live legs | n/a | none for this row (each written contract carries its own — C7's contracts carry the verbatim live windows/legs: camera-registry days 6–13 (302) + AR-3 + AR-2 (303–306) + EFF/OSM re-ingest + rematerializes; C8's 310 carries `AR-3 + AR-2` + one leg + the header re-run prompt under the OM-20 listing) |
| OM-20 pre-authorisation | n/a | not an OM-20 row (C7's contracts carry the conditional verbatim — five rows' live legs queue behind the operator's named-mutation pre-authorisation; C8's 310 carries the same conditional for its hosted change + backfill) |
| OM-03 rows only from the ratified plan | ok | rows 261–306 are the ratified chain rows; placements landed via a Plan-extensions line, no renumber; the dep corrections (P36.3 → 277, P36.4 → 279), C6's recorded plan-note corrections (291's copied unsplit-scope notes; 296/297/298's "no §56 Owner" → findings/cited ids), C7's recorded notes (299's S2 ordering-only edge; 300/301's shared F-134 column → a-half owns, b-half serves; 300's K4-P9 DSRC-01 seam resolution; 302's no-mass-re-mint live-stage reading; 303's 5,278 re-derive-not-assume; 304/306's "production write = appends" readings; 305's missing S6 clause + EFF/OSM-only leg scope) and C8's recorded notes (307's UXR-17 draft-ref + soft prerequisite edges; 308's draft SIG-EXPORT-D21 + findings not §56 Owner; 309's interim lane basis; 310's C-14 unmatched/repo-record rows + `per_fetch` column split with 312; 311's verdict-function handoff to P35.41; 312's SEED-12b MUST-carried disposition + `/v1/changes` out; 313's C-6 same-field wording + interim-basis replacement; 314's helper-before-consumers / sweep-stays-P36.66a) are recorded in-contract, not in the plan |
| PR-1 branch from chainTip; PR base = previous branch | ok (C1, C2, C3, C4, C5, C6, C7, C8) | branch from `0de78f39`; PR #236 base `r11/P34.33-round-close-record-checks` |
| CI-2/CI-6 pre-closeout head green | pending | C13 |
| P11 local gate | ok (C1, C2, C3, C4, C5, C6, C7, C8, with recorded limits) | `make docs-check` + `make check` green with the PATH docker stub + `SIG_GCP_PROJECT=sig-local-sentinel`; Docker-gated suites skipped locally, run in CI; C3/C4/C5/C6/C7/C8 touched no code (docs-check + projection regen locally) |
| CI-8 CI config changed | no | |
