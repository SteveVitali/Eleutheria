# REVIEW-R11 — Round-11 closing-review findings register

- **Scope:** the Round-11 chain, manifest rows 201–509 (~302 engineered tickets),
  reviewed as `git diff main...HEAD` at `58d81274` (the landed P38.4 tip,
  `r11/P38.4-round11-docs-refresh`; merge-base `2f4e9e57`, 3,778 commits,
  8,873 files, +2,274,567/−16,346).
- **Reviewer / provenance (honesty note):** the manifest note specs this review
  as "Claude Code, Opus 5.5, xhigh" (`00_MANIFEST.md` REVIEW-R11 row, A-15). The
  operator elected to dispatch a Devin review worker — this register is an
  **agent-drafted review by `devin-desktop/swe-2-high/subagent`** (worktree
  `/private/tmp/sig-review-r11`, branch `r11/ops-review-r11`), not the specced
  Opus review. Findings are evidence-bound; the operator dispositions every
  S0/S1 (S6-F3) before GATE-ANNOUNCE.
- **Method:** adversarial read of the round's highest-risk surfaces — `db/`
  sqitch changes (append-only, grants, the purge exception), `policy/` gates,
  `api/` authz paths, `ops/` live-mutation scripts, `exports/` licence
  compartmentation, the build-memory record surfaces (signature coverage,
  append-only, live-claim citations) — plus the committed read-only validators
  run verbatim below, and a 15-entry spot-check of
  `reports/p38.3b-round11-spec-reconciliation.md` against code/records.
- **What this review could not re-run:** `uv`-resolved test suites, `make
  check`, Docker `tests/db`/`tests/e2e`, and the web gate (no env in this
  worktree). The recorded CI boundary on the base tip (`ci: pass #546@01815d6`,
  5/5 head-bound, run 45227471113) and P38.4's amd64 `make test-db` 806/806 are
  cited as records, not independently reproduced here.

## 0. Tooling verdicts (run verbatim at `58d81274`, 2026-11-23T23:0xZ)

| check | verdict |
|---|---|
| `memory_guard.py all --worktree` | **green** — 0 violations, 5 items |
| `check_coverage_matrix.py` | **green** — 994 rows OK, 2,800 evidence refs |
| `check_backlog.py` | **green** — deferral homes 196/196, LD 90/90, ADR triggers 251/251, 0 duplicate ids |
| `obligation_events.py check` | **green** — 797 events / 515 assessments, **14 warnings** (volatile `docs/build/logs/**` refs + 5 stale superseded-row refs; see S2-3) |
| `check_round_close.py check` | **green** — offered/evaluated all legs |
| `check_round_close.py check --round-tail 2026-10-01` | **FAIL — 13 problems** (5 missing probe records, 6 stale >24 h, 2 vacuous all-skipped records; expected pre-tail state — see S2-2) |
| `check_live_claims.py corpus` | **green** — 109 claims, 0 violations |
| `check_live_claims.py range main...HEAD` | **FAIL — 112 violations** — every flagged line blames a commit **pre-dating the binding's activation** (all grandfathered-eligible; artifact of whole-round range, not per-PR invocation) |
| `check_spec_src.py` | **green** — BUILD.sh byte-identical (980,403 B), 994 ids, Appendix F == 251 ADR files |
| `ledger_contract.py check` | **green** — 0 violations (444 warnings; 3,033 items) |
| `return_pass.py check` | **green** — 281 obligations, 196 owed each in exactly one home; generated region byte-identical |
| `adr_index_check.py` | **green** — 284 evaluated, 1 warning (ADR-120 legacy owner cell `—`) |
| `adr_triggers.py check` | **green** — 252 register rows OK |
| `audit_current_state.py --require-reconciled` | **green** — 0 errors, 9 conflicts all covered by `reconciliations.json` (incl. `D-P21.5-1` PARTIAL-lead/DONE-tail ambiguity, recorded not resolved) |
| `check_runbook.py` | **green** — 9/9 sections, 68 commands, 0 violations |
| `redaction_guard.py` | **green** — 9,153 files, 0 hits |
| `current_projection.py generate+verify` (temp out) | **green** — fresh, 1,319/1,319 digests |
| `scripts/ci/secret_scan.py` | **green** — 9,153 files, 0 credential shapes |
| `check_trailers.py` (HEAD~50…HEAD sample) | **green** — 68 commits, every commit trailered or operator |
| `check_gate_signatures.py --range main...HEAD` | **FAIL — 842 records / 842 uncovered** — decomposed below; **one** genuinely uncovered post-key record (S1-1) |

**Whole-round `check_gate_signatures` decomposition** (the raw verdict is an
artifact, analysed per-record): `allowed_signers` does not exist at the
merge-base, so the check reads a header-only/absent file and fails closed on
*everything* — its designed behaviour for a range whose base predates OP-25.
Of the 842 flagged records: ~800 are pre-regime (pre-2026-10-04 G4c / pre-10-09
key) commits or unsigned GitHub merge diffs whose in-PR adding commits verify
`G` (sampled: `83f96c19` GATE-G5, `ede12a67` GATE-ACCEPT-R11, `b91f8e58`
GATE-G6, `aab6c8ef` GATE-G4, `f8d97d9b`, `99018e1b`, `b4bbae0e`, `4c75c68e`,
`ddaa969e` — all `G` against the HEAD `allowed_signers`, one `sig-operator-gate`
ssh-ed25519 key). Post-key flagged commits that are genuinely unsigned and
non-merge: exactly **two** — `6df21fce` (S1-1) and `6b83ff68` (the ACCEPT-R10
readout adoption onto `main`; its HEAD blame for the `Status: SIGNED` line is
`4127dbf3`, 2026-09-28 — a pre-regime record, exempt in spirit). All 536
`source-flip` records: the two post-key flagged flips trace to `G`-signed
commits / the signed GATE-G5 pre-authorisation rows — **no uncovered flip**.

## 1. Findings

### S1-1 — An uncovered `decision` gate record stands at HEAD (ING-GO-B)

- **Severity:** S1 (record-integrity; OP-25 / SIG-SEC-010 / ADR-147 decision 6).
- **Location:** `docs/build/LEDGER.md:325` — the `decision` row "P36.12 gate —
  ING-GO-B (Wave-B activation go, verbatim)".
- **Evidence:** `git blame -L 325,325 docs/build/LEDGER.md` → `6df21fce`
  (2026-10-15, unsigned, `Harness: devin-desktop/swe-2-high/subagent`), an
  ancestor of HEAD via merge `b8b0c532` inside the merged PR #299 chain.
  `check_gate_signatures` flags it in every range containing it; per the tool's
  own rule a pushed commit can never be retro-covered. The operator's go +
  waiver exist only in **exempt-kind** rows: LEDGER:326 (the go re-recorded as
  `confirmation`) and LEDGER:327 (the #299 gate-signature waiver recorded as
  `confirmation`), both blamed to unsigned `f80b7946` — `confirmation` is
  G4c-skipped by design, so the *waiver substance* has no signature coverage
  either. The row text discloses this honestly ("the `decision` row above stays
  in history unsigned").
- **Mitigants (why not S0):** the verbatim answer is authentic and disclosed;
  the same decision substance (Wave-B window + flips-at-open) stands in the
  `G`-signed GATE-G4 record (LEDGER:316, blame `aab6c8ef` — verifies `G`);
  the waived red was knowingly merged by the operator (LEDGER PHASE LOG
  2026-10-15, the P36.12 orchestrator-repair entry); the Wave-B window the go
  authorised already ran.
- **Proposed disposition:** **operator's call** — either (a) a signed
  `waiver`/`decision` row re-recording the ING-GO-B go and the #299 merge
  waiver under the OP-25 key (leaves a covered record of the same substance;
  the unsigned row stays disclosed in history), or (b) accept-with-reason
  citing LEDGER:316 (signed substance) + LEDGER:326–327 (disclosed
  confirmation-kind re-record) + the exercised window.

### S2-1 — Tail probe sweep is red pre-P38.5; two committed probe records are vacuous

- **Severity:** S2 (owed-work/risk flag for the announce packet).
- **Location:** `docs/build/tools/record_policy/tail_probe_sweep.toml` sweep;
  records `docs/build/reports/probes/`.
- **Evidence:** `check_round_close.py check --round-tail 2026-10-01` → 13
  problems: no records for `route-allowlist`, `release-record`,
  `live-config-drift`, `monitoring-liveness`, `conf-gen-regression`; six
  records stale (>24 h); and `api-release-parity` + `number-truth` records
  **evaluated nothing** (all-skipped — "needs --api-sample and --release-dir
  together"; "manifest.json declares no per-file counts"). G11 fails a vacuous
  record at the tail.
- **Proposed disposition:** **defer-with-trigger** to P38.5/announce — the tail
  sweep re-run is contract work; flag that two producers must actually measure
  (a re-run producing another all-skipped record fails G11 again).

### S2-2 — `nightly.yml` red ≥43 consecutive runs (recorded, repair operator-routed)

- **Severity:** S2 (announce optics + a live scheduled gate failing).
- **Location:** `.github/workflows/nightly.yml`; LEDGER OPEN FINDINGS
  `NIGHTLY-RED-1`.
- **Evidence:** the recorded re-reads (P38.1a/P38.2/P38.3a) — ≥43 consecutive
  completed failures at 2026-11-19, same `oracle-unexpected` replay signature
  at `e8dfcb76` plus `depaudit`/`npm` legs; the replay machinery works and
  reports the unexpected rows — the verify condition stands unmet. Already an
  owed observation under `D-P34.7-1`/`D-P34.2-2`, repair operator-routed.
- **Proposed disposition:** **accept-with-reason or fix row** — recorded and
  honestly bounded; the announce packet should carry it verbatim as a standing
  red scheduled job, not a new defect.

### S2-3 — Obligation-ledger warnings: volatile + stale evidence refs

- **Severity:** S2/nit (record quality).
- **Location:** `docs/build/reports/obligations/events.jsonl` +
  `COVERAGE_MATRIX.csv` superseded rows.
- **Evidence:** `obligation_events.py check` green but **14 warnings** — six
  event refs and eight coverage refs cite `docs/build/logs/**` (gitignored —
  absent on fresh checkout: `D-P34.6-1`, `D-P32.10a-1`, `D-P32.16a-1`,
  `D-P34.24b-1`, `D-P34.28-1`, `SIG-MEM-007`, `SIG-OPS-003/004`) and five
  superseded-row refs no longer resolve (`SIG-MEM-002`, `SIG-CHART-006/007`,
  `SIG-ENG-020`, `SIG-EPIS-001`).
- **Proposed disposition:** **accept-with-reason** (historical refs, warnings
  not failures) or a small fix row re-citing committed paths for the six event
  refs — the operator's call; non-blocking.

### nit-1 — `evidence_capture` in-place backfill UPDATE (`claim_assertion_bindings`)

- **Severity:** nit (design exception worth naming, not a violation).
- **Location:** `db/deploy/claim_assertion_bindings.sql:85-92`.
- **Evidence:** the migration `UPDATE`s existing `evidence_capture` rows to
  backfill the new `capture_classification` column (`synthetic` for
  `sig:connector:*` artifacts, `actual` for byte-bearing captures,
  `legacy` for the unverifiable rest). Not a claim-table mutation; no
  append-only trigger covers `evidence_capture` (only RLS + grants); the
  sqitch.plan entry discloses the backfill. Deterministic and
  provable-only — unverifiable rows stay `legacy` rather than being guessed.
- **Proposed disposition:** **accept-with-reason** — a new-column
  classification backfill, disclosed, outside the claim spine's guard list.

### nit-2 — Curation token `resolve` is a plain dict lookup; demo-token posture is DSN-detected

- **Severity:** nit.
- **Location:** `api/src/api/tier_tokens.py:152-155`, `api/src/api/curation.py:966-983`.
- **Evidence:** `TierTokenStore.resolve` uses `dict.get` — not constant-time
  (theoretical timing side-channel on bearer tokens; the intake receiver's
  receipt tokens do compare in constant time). Demo tokens are stripped only
  when the app is `dsn_backed` — a curation deployment without a DSN would
  accept published demo keys (documented design: "a real deployment
  provisions real tokens"; the surface stays loopback + `SIG_CURATION_ENABLED`
  gated, routes structurally absent otherwise — verified at `cli.py`/config).
- **Proposed disposition:** **accept-with-reason** — both are recorded design
  postures; a `hmac.compare_digest` lookup would be a cheap hardening fix if a
  fix row is preferred.

## 2. Sampled and found clean (negative results — no finding)

- **`sig_purge_claims`** (`db/deploy/operator_purge.sql`, the sole SIG-STORE-011
  exception): invoking-role strict check (`current_setting('role')` ==
  `sig_purge_operator`, NOLOGIN, never granted — verified no `GRANT
  sig_purge_operator` anywhere); closed category vocabulary; 14-relation
  blocker scan; tombstone+audit inside the same transaction; `DISABLE TRIGGER
  USER` only on the four claim tables with FK triggers armed (a missed
  dependent fails closed); `REVOKE ALL … FROM PUBLIC`, `GRANT EXECUTE` to the
  operator role only.
- **Append-only posture, net diff:** zero `-| D-` deletions in
  `docs/tickets/DEFERRALS.md` and zero `-|` row deletions in
  `docs/build/LEDGER.md` across `main...HEAD`; the diff's other
  `UPDATE`/`DELETE` SQL is (a) BEFORE-trigger refusals, (b) new-column
  backfills (nit-1), (c) `GRANT UPDATE` scoped to `capture_status` /
  `disappeared_observed_at` / `claim.sys_period` only (disappearance events +
  §16.6 belief-close, documented), (d) `intake`-schema reporter-PII
  redact/expunge SECURITY DEFINER functions (`EXECUTE` revoked from PUBLIC,
  reviewer-role only — quarantined intake schema, not the spine).
- **Intake receiver:** `ops/config.toml [intake]` `operational=false`,
  `owner=""`, `staffed=false` at HEAD; `intake_operational` requires the
  committed flag AND `SIG_INTAKE_OPERATIONAL=1`; `503 receiver_not_operating`
  honest; HMAC form token, sha256-only receipt capability, constant-time
  compare, token-bucket abuse gates.
- **Curation authz:** separate loopback app; routes structurally absent unless
  `SIG_CURATION_ENABLED=1`; invite+env-token (HG-09, no committed secret);
  `without_demo_tokens` on DSN-backed apps; `assert_no_prohibited_routes` at
  construction.
- **Exports:** compartment computed from rights records
  (`compute_export_license`), declared compartment *validated* not trusted,
  licence-without-compartment raises — the fail-closed gate stands.
- **`sources.toml`:** 237 `ingestion_permitted=true` / 259 `=false`;
  `flock_transparency_portals` stays `false` with the WV-10 probe-only posture
  recorded; every post-key flip traces to `G`-signed coverage (§0).
- **Ops scripts:** all `DELETE`/`DROP`/`TRUNCATE` strings are documented
  rollback log lines or **write-refusal probes** (`ops/db_logins.py` —
  `DELETE FROM claim WHERE false` asserted refused per login role); the
  leg-runner families keep the recorded `exit 42` queued posture.
- **`sig_purge_operator`:** NOLOGIN, never granted to any login or migration —
  verified by grep over the whole tree.
- **Reconciliation spot-check (15 entries, `p38.3b`):** all honest —
  WV-11→ADR-189/`operator_purge` scoped ✓, WV-12/`SIG-UI-022`→`WAIVED(ADR-190)`
  ✓, WV-10/`SIG-INGEST-035`→ADR-188 probe-only ✓, `SIG-STORE-045`→
  `MET-DIFFERENTLY(ADR-248)` ✓, `SIG-UI-040`→`MET-DIFFERENTLY(ADR-200)` ✓,
  `SIG-ENG-005`→`MET-DIFFERENTLY(RISK-R11-34)` ✓, `SIG-GOV-016`→
  `MET-DIFFERENTLY(RISK-P0-10)` ✓, `SIG-ENG-041` `MISSING`→SEED-15 ✓,
  `SIG-MEM-007`/`SIG-CONF-012` routed P38.5 ✓, `D-R10-PUBLISH-1` OPEN ✓,
  `D-P38.2-1` (GAP-RP-1) OPEN ✓, `D-P38.3b-1` OPEN kind P cites BL-087 ✓,
  `SIG-RECON-018` `AT-RISK-INTEGRATION`→BL-085 ✓.
- **Coverage two-sum:** `994 rows OK` verified by the checker; 650 satisfied /
  246 engineered-only / 16 waived / 73 routed-open / 9 N-A sums to 994.
- **Record surfaces:** `allowed_signers` carries exactly one operator key;
  every sampled `G` commit verifies against it; merge commits are unsigned by
  design and their records trace to signed in-PR commits.

## 3. Register summary

| severity | count | findings |
|---|---|---|
| S0 | 0 | — |
| S1 | 1 | S1-1 uncovered `decision` row (ING-GO-B, LEDGER:325) |
| S2 | 3 | S2-1 tail sweep red + vacuous probe records · S2-2 `nightly.yml` standing red · S2-3 volatile/stale obligation refs |
| nit | 2 | nit-1 `evidence_capture` backfill UPDATE · nit-2 curation token lookup / demo-token posture |

P38.5's packet + the GATE-ANNOUNCE sitting consume this register: S1-1 needs an
operator disposition (S6-F3); the S2s are defer-with-trigger /
accept-with-reason candidates.
