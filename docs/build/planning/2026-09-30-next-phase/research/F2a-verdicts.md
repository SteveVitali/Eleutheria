# F2a — Requirement verdict re-audit, engineering half (49 ids)

Row **F2a** of the Stage-P ledger (META_PLAN §6.F, row F2; the orchestrator split F2 into
F2a/F2b to fit one context). Observed **2026-09-30T17:00:29Z – 17:16:36Z** (`date -u`). The
audit is read-only: it wrote only this file, `data/coverage_delta_F2a.csv` and
`findings/incoming/F2a.csv`. `docs/build/COVERAGE_MATRIX.csv` is untouched. The deltas are
**proposals**; T4 applies them after S5 decides the vocabulary (§8.3).

**Code base audited:** the chain tip `b051732c` (2026-09-28T18:47:58-04:00). The worktree HEAD
(`7642f8d1`) differs from it only under `docs/build/planning/`, verified with
`git diff --name-only b051732c HEAD | grep -v '^docs/build/planning/'`, which is empty.

## 1. Scope

- **15 "engineering" ids (Appendix C):** PUB-007, 012, 015, 016; INGEST-046b, 046c; UI-010,
  UI-040; EPIS-018; RECON-039, 040; SEC-005, 006; STORE-004, 005.
- **34 "claimed but no id-linked test" ids:** ONTO-001, 028, 035, 051, 054, 055, 057, 057a, 060,
  064, 065; INGEST-004, 005, 006, 007, 008, 010, 025a, 025b, 025c, 041, 048; GEO-002, 005, 007;
  STORE-013, 037, 044, 045; RECON-052; ENG-004, 034; EVID-001; CONTRIB-019.

All ids carry the `SIG-` prefix. Their universe rows are U-0128 … U-0257; the u_id of each is in
§4.

## 2. Method

1. For each id I read the bold paragraph in `docs/2_canonical_design_spec.md`, including any
   table or list that follows it, and the id's `COVERAGE_MATRIX.csv` row (verdict, evidence,
   owning_tickets, tests, routing, note).
2. **Mechanical id grep.** `git grep -l -w SIG-<id> -- ':!docs' ':!*.md'` found code or test
   hits for only 11 of the 49 ids. So the audit searched for behaviour, not for tags.
3. **Behavioural verification.** Five read-only verification agents ran in parallel, one per
   domain: publication/security/robots, UI/epistemics/reconcile/projections, ontology, ingestion,
   and geo/store/process. Each located the implementation (file:line), read the test assertions,
   and ran targeted non-Docker tests.
4. **Independent spot-checks.** I re-verified every load-bearing claim myself before adopting it,
   and corrected three agent errors:
   - The affirmative-refusal example in SIG-INGEST-046c is the **ALPR Abuse Library** (spec
     :8203), not HIBF.
   - The §22.7 roster has **16** rows, not 17.
   - Parquet/DuckDB analytics **does** exist (`exports/src/exports/formats.py:172`,
     `db/src/db/analytics.py`).

   Load-bearing claims checked this way:
   - `lifecycle` has no production importer.
   - `spine_export` puts no rows in the timeline.
   - The `mobile` value is not in the `Mobility` enum.
   - The SKOS self-broader triple.
   - There is no RTCC organization type.
   - `content_digest` inputs.
   - `redact()` has no non-test caller.
   - No `SECURITY.md` and no `--service-account` flag.
   - BL-009 is closed with no follow-up row.
   - The ENG-034 commit ancestry.
5. **Every cited test node id was validated.** I extracted all 66 `tests/…::name` references from
   the delta CSV and ran `uv run pytest --collect-only` on them. All of them collect except
   `tests/e2e/test_composed_stack.py::test_s8_web_build_renders_from_export_bytes`, which is
   skipped at collection without Docker; its `def` is present at line 831.
6. **Recorded executions** (`PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider …`):
   - 2026-09-30T17:13:12Z: 24 key tests → **24 passed**.
   - 2026-09-30T17:16:36Z: every cited non-Docker node plus `tests/evidence/test_redaction.py`,
     `test_access_log.py`, `tests/unit/test_policy_officer.py` and
     `tests/reconcile/test_lifecycle.py` → **114 passed**.
   - `npx vitest run tests/unit/dossier.test.ts tests/unit/map.test.ts tests/unit/publication.test.ts`
     → **42 passed** (3 files).
   - Agent runs: 17 + 29 + 11 + 4 + 3 + 7 + 3 + 14 (web) + 54 + 16 + 23 + 1 + 6 + 84 + 1 + 3 +
     19 + 16 + 2 + 21 (web) → all passed.
   - **Not run:** `tests/db/**` and `tests/e2e/**` need Docker and were read only. Per
     `.github/workflows/ci.yml:72-91`, CI runs them with `SIG_REQUIRE_DB_TESTS=1`, so a
     Docker-gated test is cited as "Docker; CI". Under P11 that means CI-run, not re-run here.
7. **Homing.** Each id was grepped in `BACKLOG.csv`, `DEFERRALS.md`, `00_MANIFEST.md` and the
   ticket files.
8. **Note provenance.** `git log -S '<note text>'` on the matrix. This dates every current note
   (see §6).

Evidence classes used: `code`, `recorded-execution`, and `inference` (always labelled). No live
production state was read (P3).

## 3. Summary

### 3.1 Verdict counts (49 ids)

| verdict | current | proposed |
|---|---:|---:|
| MET | 0 | **7** |
| MET-DIFFERENTLY(ADR) | 0 | **1** |
| MET-ENGINEERED | — | 0 |
| PARTIAL | 40 | **35** |
| MISSING | 4 | **2** |
| AT-RISK-INTEGRATION | 5 | **2** |
| N/A-RATIONALE | 0 | **2** |
| **total** | 49 | 49 |

Twelve verdicts change. Two more keep their verdict, but for a **different reason**, because the
old reason is stale: PUB-007 and RECON-040. No id in this slice needs `MET-ENGINEERED`. The two
public-facing METs (UI-010, INGEST-046b) are already live-executed. The DB METs are engineered
behaviours with no owed live leg.

### 3.2 Transitions

| from → to | ids |
|---|---|
| AT-RISK-INTEGRATION → MET | UI-010, EPIS-018 |
| AT-RISK-INTEGRATION → PARTIAL | RECON-039 |
| AT-RISK-INTEGRATION → AT-RISK-INTEGRATION (re-reasoned) | PUB-007, RECON-040 |
| MISSING → MET | INGEST-046b |
| MISSING → PARTIAL | PUB-015 |
| MISSING → MISSING | PUB-016, INGEST-046c |
| PARTIAL → MET | ONTO-054, INGEST-007, STORE-013, ENG-034 |
| PARTIAL → MET-DIFFERENTLY(ADR-108;ADR-133) | UI-040 |
| PARTIAL → N/A-RATIONALE | GEO-007, ENG-004 |
| PARTIAL → PARTIAL (re-evidenced) | 30 ids |

For the 34 "claimed" ids, **4 become MET** on existing tests: ONTO-054, INGEST-007, STORE-013
and ENG-034. **2 become N/A-RATIONALE**: GEO-007 and ENG-004. **28 stay PARTIAL**, and every one
now has a concrete test-writing or build disposition.

### 3.3 Dispositions (§8.1)

| disposition | count |
|---|---:|
| `ticket(NEW: …)` in 14 proposed groups (§5) | 35 |
| `ticket(BL-049)` (an existing open home) | 1 |
| `already-done(…)` (all 7 MET and the 1 MET-DIFFERENTLY) | 8 |
| `spec-amendment(…)`: ONTO-060, INGEST-004, ENG-004 | 3 |
| `later-phase(next technology-vocabulary version)`: ONTO-057a (a SHOULD) | 1 |
| `wontfix(rationale paragraph; obligation carried by SIG-GEO-006)`: GEO-007 | 1 |

## 4. Per-id results

The full evidence, with file:line and test node ids, is in `data/coverage_delta_F2a.csv`.

| u_id | id | current → proposed | disposition |
|---|---|---|---|
| U-0230 | PUB-007 | AT-RISK → **AT-RISK (re-reasoned)** | ticket: officer-naming gate on the publication path |
| U-0231 | PUB-012 | PARTIAL → PARTIAL | ticket: asset-promotion gate (homeless, NEW-2) |
| U-0234 | PUB-015 | MISSING → **PARTIAL** | ticket: redaction pipeline |
| U-0235 | PUB-016 | MISSING → MISSING | ticket: redaction pipeline |
| U-0206 | INGEST-046b | MISSING → **MET** | already-done |
| U-0207 | INGEST-046c | MISSING → MISSING | ticket: affirmative rights-reservation state (NEW-3) |
| U-0255 | UI-010 | AT-RISK → **MET** | already-done |
| U-0257 | UI-040 | PARTIAL → **MET-DIFFERENTLY(ADR-108;ADR-133)** | already-done |
| U-0165 | EPIS-018 | AT-RISK → **MET** | already-done |
| U-0236 | RECON-039 | AT-RISK → **PARTIAL** | ticket: lifecycle into dossier timeline (NEW-1) |
| U-0237 | RECON-040 | AT-RISK → **AT-RISK (re-reasoned)** | ticket: lifecycle into dossier timeline (NEW-1) |
| U-0242 | SEC-005 | PARTIAL → PARTIAL | ticket: audited restricted-byte access + log purge |
| U-0243 | SEC-006 | PARTIAL → PARTIAL | ticket: security baseline (NEW-9) |
| U-0244 | STORE-004 | PARTIAL → PARTIAL | ticket: projection rebuild CI (with BL-048) |
| U-0245 | STORE-005 | PARTIAL → PARTIAL | ticket: projection rebuild CI |
| U-0212 | ONTO-001 | PARTIAL → PARTIAL | ticket: layer-direction test |
| U-0217 | ONTO-028 | PARTIAL → PARTIAL | ticket: ontology conformance batch |
| U-0218 | ONTO-035 | PARTIAL → PARTIAL | ticket: ontology conformance batch (MFA missing) |
| U-0219 | ONTO-051 | PARTIAL → PARTIAL | ticket: ontology conformance batch (carrier test) |
| U-0220 | ONTO-054 | PARTIAL → **MET** | already-done |
| U-0221 | ONTO-055 | PARTIAL → PARTIAL | ticket: ontology conformance batch (NEW-5) |
| U-0222 | ONTO-057 | PARTIAL → PARTIAL | ticket: ontology conformance batch (RTCC org type) |
| U-0223 | ONTO-057a | PARTIAL → PARTIAL | later-phase |
| U-0224 | ONTO-060 | PARTIAL → PARTIAL | spec-amendment (scope list) |
| U-0225 | ONTO-064 | PARTIAL → PARTIAL | ticket: lifecycle (test only) |
| U-0226 | ONTO-065 | PARTIAL → PARTIAL | ticket: lifecycle (2 missing detectors) |
| U-0194 | INGEST-004 | PARTIAL → PARTIAL | spec-amendment (NEW-7) |
| U-0195 | INGEST-005 | PARTIAL → PARTIAL | ticket: ingestion framework hardening (test only) |
| U-0196 | INGEST-006 | PARTIAL → PARTIAL | ticket: ingestion framework hardening |
| U-0197 | INGEST-007 | PARTIAL → **MET** | already-done |
| U-0198 | INGEST-008 | PARTIAL → PARTIAL | ticket: ingestion framework hardening |
| U-0199 | INGEST-010 | PARTIAL → PARTIAL | ticket: ingestion framework hardening (NEW-6) |
| U-0200 | INGEST-025a | PARTIAL → PARTIAL | ticket: statute-seeded records leads |
| U-0201 | INGEST-025b | PARTIAL → PARTIAL | ticket: statute-seeded records leads |
| U-0202 | INGEST-025c | PARTIAL → PARTIAL | ticket: statute-seeded records leads |
| U-0203 | INGEST-041 | PARTIAL → PARTIAL | ticket: registry completeness + discovery sweep (NEW-8) |
| U-0208 | INGEST-048 | PARTIAL → PARTIAL | ticket: registry completeness + discovery sweep |
| U-0180 | GEO-002 | PARTIAL → PARTIAL | ticket: ontology conformance batch (lint test) |
| U-0181 | GEO-005 | PARTIAL → PARTIAL | ticket: ontology conformance batch (NEW-4) |
| U-0182 | GEO-007 | PARTIAL → **N/A-RATIONALE** | wontfix (rationale) |
| U-0246 | STORE-013 | PARTIAL → **MET** | already-done |
| U-0248 | STORE-037 | PARTIAL → PARTIAL | ticket: ontology conformance batch |
| U-0249 | STORE-044 | PARTIAL → PARTIAL | ticket: ontology conformance batch |
| U-0250 | STORE-045 | PARTIAL → PARTIAL | ticket(BL-049) |
| U-0239 | RECON-052 | PARTIAL → PARTIAL | ticket: inference distinguishability |
| U-0134 | ENG-004 | PARTIAL → **N/A-RATIONALE** | spec-amendment (align DoD with §8.3) |
| U-0149 | ENG-034 | PARTIAL → **MET** | already-done |
| U-0177 | EVID-001 | PARTIAL → PARTIAL | ticket: security baseline (E4 audited takedown) |
| U-0128 | CONTRIB-019 | PARTIAL → PARTIAL | ticket: statute-seeded records leads (task link) |

### 4.1 Notes on every change and re-reasoning

- **SIG-PUB-007: AT-RISK-INTEGRATION, re-reasoned.**
  - *Old reason, stale:* "web reads fixtures, P21.4". The public build forces
    `SIG_DATA_SOURCE=export` (`ops/src/ops/publish.py:146`), and BL-007 is closed.
  - *Real gap:* the five-prong gate (`policy/src/policy/officer.py:93`) runs only on OKC ingest
    (`connectors/src/connectors/okc_documents.py:214`). The publication path applies only the
    SIG-PUB-017 jurisdiction rule. `web_dossier.py:360-367` hard-codes an "Approving official"
    name, and `web/tests/unit/publication.test.ts:17` asserts that a US name is publishable.
  - This is the same defect as **E1/NEW-12**: latent, since `/dossier/okc/` returns 404. Merge
    the ticket with it.
- **SIG-PUB-015: MISSING → PARTIAL.**
  - *Built:* `evidence/src/evidence/redaction.py:43` records a new capture plus method and
    version, and `tests/evidence/test_redaction.py` passes.
  - *Not built:* `redact()` has no non-test caller, there is no review record, and API/UI
    excerpts are not sourced from a redacted derivative. `tiers.py:87` returns public excerpts
    raw.
- **SIG-INGEST-046b: MISSING → MET.**
  - Under ADR-088 the spec text itself now requires the `robots_disregarded` marker (amended by
    ADR-145). `connectors/net.py:365-393` records it, and the runner serialises it.
  - Covered by `tests/connectors/test_net.py::test_robots_disallow_is_recorded_and_disregarded`.
  - Live-executed: `docs/build/reports/live_runs/2026-09-19_ok_statute_p2617.json`.
  - The matrix note "no live transport, LD-F03" is stale.
- **SIG-UI-010: AT-RISK → MET.**
  - The twelve-section order is enforced in the export (`exports/src/exports/dossier.py:37-52`)
    and at web build (`web/src/lib/dossier.ts:40-55`, called from `[slug].astro:33`). Production
    reads export bytes.
  - Tested in Python and web unit tests, and by the Docker e2e
    `test_s8_web_build_renders_from_export_bytes`.
  - *Caveat:* sections exist but can be empty. The timeline is always empty (NEW-1), which is
    RECON-040's problem, not UI-010's.
- **SIG-UI-040: PARTIAL → MET-DIFFERENTLY(ADR-108;ADR-133).**
  - The API uses `pg_trgm` substring search; ADR-108 explicitly rejects `tsvector` for
    identifiers. The released corpus uses SQLite FTS5 (ADR-133). No dedicated engine was added,
    so the licence-check clause is never triggered.
  - The old note ("web reads fixtures; no PG read path") is stale. T4 should record the reason,
    since neither ADR cites SIG-UI-040.
- **SIG-EPIS-018: AT-RISK → MET.**
  - The "annotation persistence" reason never applied to this id. D5 for contracts on
    `active_device_count` and the D6 admissibility filter are implemented
    (`reconcile/resolve.py:539-542`, `weight.py:198`).
  - Four `test_resolve.py` tests assert both consequences. Resolutions are materialized.
- **SIG-RECON-039: AT-RISK → PARTIAL.**
  - "Event log preferred" is only a within-window ordering tie-break
    (`lifecycle.py:136`). `current_state()` returns `None` for a mixed window, so the event log
    never decides the state.
  - No production code imports `reconcile.lifecycle`, and nothing sets `from_event_log=True`.
- **SIG-RECON-040: AT-RISK, re-reasoned.**
  - The EDTF unordered-within-window algorithm is correct and tested
    (`test_overlapping_fuzzy_envelopes_are_unordered_within_window`).
  - It is never persisted, served or published, and the national dossier timeline is
    structurally empty (NEW-1). The old P21.2 reason is stale: P21.2 landed 2026-09-09 and
    BL-004 is closed.
- **SIG-ONTO-054: PARTIAL → MET.** Covered by
  `tests/ontology/test_vocabularies.py::test_every_family_has_an_unspecified_leaf`. The test
  cites the id as "SIG-ONTO-020/054", which the matrix's id-linker missed (NEW-10).
- **SIG-INGEST-007: PARTIAL → MET.** `reconcile/snapshot_diff.py` diffs extracted fields.
  `test_snapshot_diff.py::test_unchanged_fields_produce_no_event` feeds two captures with
  different digests and the same fields, and gets no events; the `/changes` feed test confirms
  the wiring.
- **SIG-STORE-013: PARTIAL → MET.**
  - The trigger `db/deploy/claim_append_only.sql:56-64` makes the lower bound immutable and
    allows a close only once.
  - `tests/db/test_append_only.py::test_sys_period_lower_bound_is_immutable` and
    `::test_closing_sys_period_is_permitted` cover it (Docker; CI).
  - Hardening note: "DB-assigned" rests on a DEFAULT.
- **SIG-ENG-034: PARTIAL → MET (by record).**
  - The P06.1 retrospective (`b1b9965d`, 2026-09-01T09:38:03-04:00) is an ancestor of the first
    P07.1 commit (`cacbfeba`, 10:03:56-04:00).
  - `test_slice_artifacts.py::test_retrospective_is_committed_and_substantive` passes.
- **SIG-GEO-007: PARTIAL → N/A-RATIONALE.**
  - The paragraph is the 93.6% measurement behind SIG-GEO-006, with no new obligation. The
    precedent is SIG-INGEST-048a.
  - **Flag for F2b:** SIG-GEO-006 is MET, yet no code writes FOV cones to
    `inference.derived_geometry`, and the tiles export has only a points layer.
- **SIG-ENG-004: PARTIAL → N/A-RATIONALE.**
  - This is the Definition-of-Done meta-rule the verdict process applies; it is not a buildable
    behaviour.
  - Disposition: `spec-amendment` to align its five criteria with the §8.3 vocabulary (MET =
    criteria 1+2; criteria 3–5 recorded per row).
  - Criterion 5 (id in commit/PR) is unenforced; there is no PR template or hook.

### 4.2 Notable unchanged PARTIALs (new reasons)

- **SIG-INGEST-004.**
  - Claim identity is `content_digest` over the connector payload. No connector puts
    `extractor_version` in it (`git grep` finds 0 hits in `connectors/src`).
  - ADR-121 records the versions on the `claim_evidence` binding instead, without citing the id
    (NEW-7).
  - Proposed disposition: `spec-amendment`, recording binding-level versioning, plus a test.
    Alternative if declined: add the versions to the digest.
- **SIG-STORE-045.**
  - The deployed DDL is hand-written sqitch. The generated `sig.sql` is neither deployed nor
    compared. RISK-P2-04 → **BL-049 (open)** is the only open home among these 49 ids.
  - The core clause is unmet and borderline MISSING; it is kept PARTIAL because generation and
    the freshness gate exist.
- **SIG-GEO-005.** The mobility model exists but writes the out-of-vocabulary value `'mobile'`
  (NEW-4).
- **SIG-INGEST-041.** 11 of the 16 §22.7 roster rows are unregistered, while a closed BL's risk
  rows claim the roster "is the registered backlog" (NEW-8).
- **SIG-SEC-006.**
  - Present: secret and licence scans and nightly pip-audit. So the note "scanning not set up in
    CI" is stale.
  - Missing: container scanning, the SBOM wired to releases, signing, dedicated service
    accounts, and `SECURITY.md` (NEW-9).
- **SIG-EVID-001.** E1, E2, E3, E5 and E6 each have a passing test. E4 (a permissioned, audited
  takedown path) is structurally possible (Object Lock in GOVERNANCE mode) but has no routine
  and no test.

## 5. Proposed ticket groups (for S1/S3 sizing; one-line scopes)

| # | group | ids | scope |
|---|---|---|---|
| 1 | Officer-naming gate on the publication path | PUB-007 (+ E1/NEW-12) | route `isPublicEmployeeName` rows through `evaluate_officer_naming` with a persisted two-reviewer decision; default withhold; fix the asserting tests |
| 2 | Asset-promotion gate | PUB-012 | `promotion_permitted()` as the only candidate→PhysicalAsset writer; refuses corroboration-only |
| 3 | Redaction pipeline | PUB-015, PUB-016 | wire `redact()`; add a review record; irreversible text-layer removal with an extraction test; excerpts come from the derivative |
| 4 | Affirmative rights-reservation state | INGEST-046c (+ E1/NEW-15 runtime leg) | a refused state distinct from UNDETERMINED; fetch-time detection; gate refusal; re-record ALPR Abuse Library |
| 5 | Lifecycle into the dossier timeline | RECON-039, RECON-040, ONTO-064, ONTO-065 | event-log-decides-state; `from_event_log` from claims; `resolve_lifecycle` → export/API timeline; free_trial test; 2 missing soft-constraint detectors |
| 6 | Projection rebuild CI | STORE-004, STORE-005 (+ BL-048) | a documented rebuild command per projection; a CI rebuild-and-verify over a seeded spine; drop-all/rebuild equality |
| 7 | Layer-direction test | ONTO-001 | per-layer grant test; L4 drop/rebuild (could merge into 6) |
| 8 | Security baseline | SEC-006, EVID-001 (E4) | container scan; SBOM per release; cosign; per-service SAs; `SECURITY.md`; audited takedown |
| 9 | Audited restricted-byte access | SEC-005 | a single audited access function; scheduled purge of expired log rows (could merge into 8) |
| 10 | Ingestion framework hardening | INGEST-005, 006, 008, 010 | replay valid_*/as_of test; declared ingestion_mode + incrementality; a manual-acquisition record + runbook; persist disappearances |
| 11 | Statute-seeded records leads | INGEST-025a, 025b, 025c, CONTRIB-019 | mandate→gap generator; one-time auditor-survey artifact + a no-follow-up CoverageRecord; LegalInstrument session/text + a publish gate; RecordsRequest→task link |
| 12 | Registry completeness + discovery sweep | INGEST-041, INGEST-048 | register the 11 missing §22.7 rows (LINK, not permitted); a roster test; a recurring discovery sweep (coordinate with Stream I) |
| 13 | Ontology conformance batch | ONTO-028, 035, 051, 055, 057; STORE-037, 044; GEO-002, 005 | operator-unknown count; MFA slot; carrier test; slug-collision fix; RTCC org type; lossy-flag propagation; QID→vendor link; ST_DWithin lint test; Mobility enum fix + CHECK |
| 14 | Inference distinguishability | RECON-052 | an inferred/L4 marker on every export and API record; an epistemic CSS class; a cross-surface test |
| — | existing home | STORE-045 | BL-049: generated-vs-deployed schema conformance test, or an ADR making sqitch DDL authoritative |

Spec amendments to hand to E2/S: **ONTO-060** (the capability scope list; the spec's own §11.6
examples break it), **INGEST-004** (identity via binding-level versions, per ADR-121),
**ENG-004** (DoD ↔ §8.3), and, inside group 13, **ONTO-055** (the family-prefix rule; the spec's
own `bwc-*` examples break it).

## 6. Systemic observations

1. **These notes predate Round 5.** `git log -S` dates every current note on the 49 rows:
   - "claimed (PR/traceability) but no code or test evidence", "web/ renders from fixtures",
     "robots.txt / rights-reservation live-fetch", "redaction-as-new-capture" and "search over
     Postgres full-text" come from **P19.2 `4ffae4fb` (2026-09-08)**.
   - "P19.5: reviewed at capstone closure" and "annotation persistence is P21.2" come from
     **P19.5 `89d27528` (2026-09-08)**.
   - "projection-rebuildability exercised" comes from **P21.5 `6c8ec20a` (2026-09-09)**.
   - Blame is useless here: commit `729fb268` (P32.25) re-wrote every line for CRLF.
   - The independent **P33.1** gap analysis (`7a2ff9fa`) re-verdicted only the 38 Round-10
     (§55) ids, so no pre-Round-10 verdict has been re-audited since 2026-09-09.
2. **Routing is dead for 47 of the 49 ids.**
   - 12 route to landed P21.x tickets: P21.2 ×3, P21.3 ×2, P21.4 ×4, P21.5 ×2, P21.6 ×1.
   - 37 route to `P20.1:backlog`, but only **STORE-045** (BL-049, open) and STORE-004 (BL-048,
     partial) have an open BACKLOG row.
   - The BL rows the matrix leans on are **closed**: BL-004, BL-007, BL-009 and BL-043. BL-009
     and BL-043 were closed with the gap still open (NEW-2, NEW-8).
   - No DEFERRALS row names any of the 49 ids.
3. **The "claimed but no id-linked test" class is a tooling artifact as much as a coverage
   fact.** The linker misses grouped citations (`SIG-ONTO-020/054`, `022/055`, `023/024/060`) and
   untagged Docker DB tests. Six of the 34 ids resolve without any new code (4 MET,
   2 N/A-RATIONALE). Seven of the remaining 28 need only a test or a spec amendment: ONTO-001,
   ONTO-051, ONTO-064, INGEST-005 and GEO-002 need a test; ONTO-060 and INGEST-004 need an
   amendment.
4. **Wrong evidence cells.** STORE-004/005 cite `ops/mirrors.toml`, which covers copies of exports
   and source, not projections versus canonical state. UI-040 cites `ADR-049-the-`, a truncated
   filename. Most "claimed" rows cite the spec line itself as evidence.
5. **"Integration" gaps moved; they did not close.** The AT-RISK-INTEGRATION cluster was about
   web fixtures and annotation persistence, and both of those are fixed. The real integration
   gaps now sit one layer down:
   - built-and-tested modules with no production caller (`reconcile.lifecycle`,
     `evidence.redaction.redact`, `policy.crawler` Content-Signal helpers, `flock_portal`
     change detection, the access-log `expired()` purge);
   - schema columns nothing reads (`promotion_status`, `confirmation_status`, `operating_area`,
     `evidence_artifact.disappeared_observed_at`).

   A mechanical "public function with only test callers" scan would find more of this class;
   this is recommended for B/C4.
6. **Vocabulary signals for S5.** In this slice, `MET-ENGINEERED` is not needed. `N/A-RATIONALE`
   is needed for one definitional MUST (ENG-004), not only rationale paragraphs. A verdict whose
   reason changed while its value did not (PUB-007, RECON-040) should carry a dated re-reason in
   `note`, not keep the stale text (P7).
7. **Reachable only through fixtures.** The officer-name leak (E1/NEW-12) and the `SB 34`
   session-less citation (INGEST-025c) both sit on the `--jurisdiction okc` export or seed paths,
   which the public national build does not use. They are latent, and the tests assert the
   unsafe behaviour as correct.

## 7. New findings (`findings/incoming/F2a.csv`)

| f_id | sev | title (short) |
|---|---|---|
| NEW-1 | S2 | Lifecycle reconciliation has no production caller; the national dossier timeline is always empty (RECON-039/040) |
| NEW-2 | S2 | The PUB-012 asset-promotion gate is homeless: BL-009 was closed with the gate split out, and no follow-up row exists |
| NEW-3 | S2 | ALPR Abuse Library (the spec's affirmative-refusal example) is registered UNDETERMINED; no refused rights state (INGEST-046c) |
| NEW-4 | S2 | The OSM connector writes `mobility='mobile'`, which is not in the Mobility enum; no CHECK; the test asserts it (GEO-005) |
| NEW-5 | S3 | The SKOS technology concept `private-camera-integration` is broader than itself; 29–40/104 slugs are not family-prefixed (ONTO-055) |
| NEW-6 | S2 | Source disappearance is never persisted to the spine, so it is not queryable (INGEST-010) |
| NEW-7 | S2 | Claim identity excludes extractor/normalizer versions (ADR-121 binding-level): an unrecorded divergence from INGEST-004 |
| NEW-8 | S2 | RISK-P17-02/08/13 (→ closed BL-043) claim the EFF roster is registered; 11 of 16 rows are absent (INGEST-041) |
| NEW-9 | S2 | Security baseline gaps: default compute SA in IaC; no `SECURITY.md`, signing, container scan, or release SBOM (SEC-006) |
| NEW-10 | S3 | "Claimed but no id-linked test" over-reports: the id-linker misses grouped citations and Docker tests; notes date from 2026-09-08/09 |

Cross-references (not duplicated): **E1/NEW-12** (the officer-name publication gate) → PUB-007;
**E1/NEW-15** (no runtime Content-Signal/TDM control) → INGEST-046c; **E1/NEW-6** (the "honour
robots" prose drift) → INGEST-046b; **J1/NEW-6** (run-row outcomes unpublished) → INGEST-010;
**F-30** (the systemic not-MET staleness) is confirmed and quantified for this half by §6.

## 8. Limits

- Docker suites were not re-run locally. Their test ids are cited as "Docker; CI" and rest on
  ci.yml running them. Under P11 that is CI-run, not re-verified here.
- No live state was read (P3). NEW-4 (live rows carrying `'mobile'`) and NEW-9 (live service
  accounts) are labelled inference.
- The verdicts are proposals for S5/T4. `COVERAGE_MATRIX.csv` is unchanged.
