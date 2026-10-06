# Run ledger — SEED-13d (Stage B, T3 fourth context): full 11A contracts for rows 241–260

- Harness: claude-code/claude-opus-5-5/subagent
- Skills: 8aeb6dc
- Started: 2026-10-01T15:12:46Z (this unit's first `date -u`; a previous attempt was cut off by a usage limit before writing anything)
- Closed: 2026-10-01T15:46:19Z
- Unit: SEED-13d — plan Appendix A T3, second bullet, for rows 241–260 of the 60 11A rows. Owns only the 20 contract files below and this ledger. Not owned: rows 221–240 incl. PLAN-11B (row 239, SEED-13c, writing concurrently), the manifest, CI/tools, registers (SEED-14), LEDGER (SEED-17).
- Worktree / branch: `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (no git state change made by this unit; no network, no production, no sub-agents — AGENT_BRIEF rule 8)
- Read (targeted sections only): `stageB/AGENT_BRIEF.md`, `stageB/CARRY.md`, `stageB/T3_contract_map.csv` rows 241–260 (+ the 11B OM-20 cells of rows 261–343), `docs/build/runs/SEED-13b.md`, `docs/tickets/201_P34.1__…` and `204_P34.3__…` (shape), the 20 skeletons, `docs/tickets/_TEMPLATE.md`, the 0.5.0 `~/.claude/skills/build-memory/templates/ticket.md`; plan Appendix A T3, §3.3, §4.3, §5.1, §5.4, §5.8, §5.9, §6.5, §7 (authors), §8.1, §8.3–§8.5, §10.2, §11.2, §13.1, §13.5; `data/round11_plan.csv` + `data/ticket_catalog.csv` rows 241–260 (+ the CONF/PKG key → row map), `data/decision_catalog.csv` (S5-2, S5-3, OD-22, E4-B1…B6, E4-R6a/b, I7-S1…S9, Q-27, OD-08, D-G3-1), `stageB/T1_id_map.csv`, `feedback/RATIFICATION_LOG.md` rounds 3, 4, 8, 9, 12, 19, 21 (+ C-10 result); design-note sections: G2 §2, steps 1, 2, 4, 5, 6, §5; G3 §4, §8; G1 §2 (rows G1-01/05/08/17), §3.4, §3.7, §3.9; F5 PKG-03/04/05; F1 §6; E4 §4, R6a/b; L3 §2, §3.1–3.6, §4.5–4.6, §5.3, §9; L1 §6.2; L2 §0, §1, §4, Appendix; I7-rights-packets §1.2; R10_PREVIEW §3.x, §7–§9; S2 §3.6, §4.1, §7.3; S4-feasibility FEA-03, FEA-07; S4-truth-safety TS-07; S6r S6R-30; FINDINGS F-16, F-151…F-159, F-272, F-406, F-506…F-521; spec §55.3/55.5/55.8, §56.4–56.7 and the cited older ids; ADR-146/149/152/153/154/159/169/180/181/185 (sections); repo code anchors named in each Load list.

## What this unit did

Replaced the 20 skeleton files of rows 241–260 with full contracts under the same names (the manifest rows bind them), in P34.1's shape: header (sequence, phase, kind, `Harness: devin-desktop/swe-2-high/subagent`, `r11/<id>-<slug>` branch, `Depends on`, `Run:` with `live_verification`, gate status with the operator's words verbatim and their round `date -u`, OM-20 status, live stage, `Live window:` with the live-leg re-run prompt where windowed (OM-19), `Production mutations:` (OM-14), `Size budget:`, the token-counted Load figure); Goal; a Load list with the byte count of every entry; deliverables; out of scope naming owner rows; live legs with `live:` edges; a production-mutation section (authority · restore point · pre-state · mutations · rollback · stop rules); acceptance criteria each tagged with its BM-STATUS-01 layer; the universal ACs (verification, head-bound CI read, one-commit closeout incl. the `rows 1-N as of` line of `docs/build/README.md`, `check_coverage_matrix.VERDICTS`, `FLIPPED <date> (<gate|ADR>)`, transitions with evidence); requirement ids (owner / also / cited); cross-cutting invariants (C-10 in every contract); the B5 §6.2 operating-clauses block filled per row; notes. GATE-G4 is written as a gate marker (no run line, no branch): the S5-2 packet, answer rules and recording.

### Token counts (counter `utf8-bytes÷3 | ÷4`, plan §8.5 / S6R-27; measured 2026-10-01 on the `r11/seed` working tree)

Same method as SEED-13b: bytes are exactly what each Load entry names (whole files, named `§` sections, line ranges, grep-selected DEFERRALS rows); the LEDGER orient region counted at 12 KiB; DEFERRALS-first = the CURRENT.md owed-obligation index + the named rows + a 16 KiB allowance; the contract itself included (self-size verified equal to the file). Files that earlier rows will write are counted at a labelled estimate. Target: ÷3 ≤ ~150k.

| row | id | file | Load entries | bytes | ≈ tokens ÷3 | ≈ tokens ÷4 | contract bytes | OM-20 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 241 | P34.34a | `241_P34.34a__release-archive-link-depth-and-crawl.md` | 21 | 176,822 | 58,941 | 44,206 | 15,963 | not OM-20 | no split |
| 242 | P34.34b | `242_P34.34b__export-mode-ci-build-and-island-budgets.md` | 23 | 208,675 | 69,558 | 52,169 | 13,506 | not OM-20 | no split |
| 243 | P34.35 | `243_P34.35__research-dossier-disclosure.md` | 21 | 185,812 | 61,937 | 46,453 | 13,651 | not OM-20 | no split |
| 244 | P34.36 | `244_P34.36__release-search-states.md` | 19 | 194,452 | 64,817 | 48,613 | 12,100 | not OM-20 | no split |
| 245 | P34.37 | `245_P34.37__intake-defects-and-moderation-hardening.md` | 19 | 256,012 | 85,337 | 64,003 | 13,496 | not OM-20 | no split |
| 246 | P34.38 | `246_P34.38__sources-pilot-prep-and-registry-rows.md` | 24 | 234,399 | 78,133 | 58,600 | 18,471 | not OM-20 | no split |
| 247 | P34.39a | `247_P34.39a__osm-replay-read-back.md` | 15 | 166,607 | 55,536 | 41,652 | 14,540 | not OM-20 | no split |
| 248 | P34.39b | `248_P34.39b__first-fire-read-backs.md` | 15 | 185,879 | 61,960 | 46,470 | 13,108 | not OM-20 | no split |
| 249 | P34.40 | `249_P34.40__serving-topology-dark.md` | 24 | 186,464 | 62,155 | 46,616 | 17,537 | pre-authorised (S5-3) | no split |
| 250 | P34.41 | `250_P34.41__withdrawal-barrier-bytes.md` | 20 | 153,346 | 51,115 | 38,336 | 12,294 | not OM-20 | no split |
| 251 | P34.42a | `251_P34.42a__least-privilege-service-identities.md` | 20 | 166,602 | 55,534 | 41,650 | 15,599 | pre-authorised (S5-3) | no split |
| 252 | P34.42b | `252_P34.42b__least-privilege-job-identities-remove-editor.md` | 20 | 184,074 | 61,358 | 46,018 | 16,251 | pre-authorised (S5-3) | no split |
| 253 | P34.43 | `253_P34.43__execution-host-and-least-privilege-db-logins.md` | 20 | 173,480 | 57,827 | 43,370 | 17,247 | pre-authorised (S5-3) | no split |
| 254 | P34.49 | `254_P34.49__part-viii-at-rest-audit.md` | 22 | 156,532 | 52,177 | 39,133 | 17,646 | pre-authorised (S5-3) | no split |
| 255 | P34.44a | `255_P34.44a__quality-check-registry-and-ratchet-engine.md` | 16 | 150,380 | 50,127 | 37,595 | 14,715 | in-ticket go (not on S5-3) | no split |
| 256 | P34.44b | `256_P34.44b__quality-baseline-run-and-nightly-probe.md` | 17 | 187,250 | 62,417 | 46,812 | 15,403 | pre-authorised (S5-3) | no split |
| 257 | P34.45 | `257_P34.45__honest-evaluation-posture.md` | 18 | 195,426 | 65,142 | 48,856 | 18,438 | pre-authorised (S5-3; ER re-run only) | no split |
| 258 | P34.46 | `258_P34.46__round10-schema-allows-and-api-roll.md` | 23 | 205,560 | 68,520 | 51,390 | 21,431 | never pre-authorised (in-ticket go) | no split |
| 259 | P34.47 | `259_P34.47__sub-round-11a-acceptance.md` | 17 | 163,358 | 54,453 | 40,840 | 15,336 | not OM-20 | no split |
| 260 | GATE-G4 | `260_GATE-G4__11a-check-in.md` | 10 | 71,154 | 23,718 | 17,788 | 13,717 | gate marker | no split |

Largest: P34.37 ≈ 85k (÷3; `intake.py` + `curation.py` ≈ 91 KB) and P34.38 ≈ 78k. **No row exceeds ~150k, so no split is proposed.**

**P34.46 (pre-flagged oversized, S6/§8.5):** Load 205,560 B → ≈ 68,520 (÷3) · ≈ 51,390 (÷4). Its working set is per leg (inference): L1 ≈ 20–30k, L2 ≈ 30–50k, L3 ≈ 10–20k tokens; each leg runs in its own context from the re-run line, so the worst context is ≈ 69k + 50k ≈ 120k (÷3 basis) — under the ~150k target. **No split needed.** If the orchestrator wants margin anyway, the natural seam is the existing leg structure: P34.46a = engineering + L1 (go/no-go checker, pause-list computation, re-rehearsal diff, go request) and P34.46b = L2 slot + L3 soak; nothing in this count requires it. C-10 is stated in the header, out-of-scope and an AC (L44–52 byte-identical by change id).

### Requirement → ticket index (rows 241–260; spec §56 `Owner:`/`Also:` as written in the contracts)

| id | role | row(s) |
|---|---|---|
| SIG-SEC-007 | owner | P34.42a (services), P34.42b (jobs + Editor removal) |
| SIG-CONF-013 | owner | P34.43 |
| SIG-CONF-003, SIG-CONF-006, SIG-CONF-007 | owner | P34.44a |
| SIG-CONF-009 | also (owner P35.34) | P34.44a, P34.44b |
| SIG-CONF-001 | owner | P34.45 |
| SIG-CONF-005 | also (owner P35.47) | P34.45 |
| SIG-CONF-012 | also (owner P37.44) | P34.47 |
| SIG-FIND-001, SIG-FIND-002 | cited | P34.34a, P34.40, P34.41 |
| SIG-FIND-003, SIG-UI-040, SIG-UI-050 | cited | P34.36 (SIG-UI-050 also P34.34b) |
| SIG-FIND-005, SIG-UI-041, SIG-ENG-040 | cited | P34.34b |
| SIG-UI-024, SIG-UI-033, SIG-UI-049, SIG-LIC-011 | cited | P34.34a (SIG-LIC-011 also P34.35) |
| SIG-DOS-001, SIG-DOS-002, SIG-TRUST-009, SIG-TRUST-010, SIG-METRIC-006 | cited | P34.35 |
| SIG-FIND-006, SIG-FIND-008, SIG-GOV-011, SIG-GOV-001/002 (WAIVED, WV-05) | cited | P34.37 |
| SIG-INGEST-036, SIG-PUB-002, SIG-ACQ-004, SIG-INGEST-046c | cited | P34.38 |
| SIG-ENG-042, SIG-OPS-011, SIG-MEM-005, SIG-MEM-011 | cited | P34.39a (SIG-ENG-042/OPS-011/MEM-011 also P34.39b; SIG-MEM-011/OPS-011 also P34.47) |
| SIG-OPS-006 | cited | P34.39b, P34.44b |
| SIG-OPS-003, SIG-REL-004, SIG-REL-006 | cited | P34.40 |
| SIG-REL-013, SIG-GOV-007 | cited | P34.41 (SIG-GOV-007 also P34.49) |
| SIG-SEC-009, SIG-OPS-005 | cited | P34.42a, P34.42b |
| SIG-STORE-048 | cited (owner P37.3) | P34.42b |
| SIG-SEC-011 | cited (owner P34.25) | P34.43, P34.46 |
| SIG-PUB-003, SIG-INGEST-045e, SIG-GOV-008, SIG-STORE-011 | cited | P34.49 (SIG-STORE-011 also P34.46) |
| SIG-REL-010, SIG-EVAL-001, SIG-EVAL-004, SIG-EVAL-006 | cited | P34.45 (SIG-REL-010 also P34.46) |
| SIG-OPS-001 | cited (owner P34.6) | P34.46 (post-deploy drill) |
| SIG-SEC-010, SIG-REL-012 | cited | GATE-G4 |

Every id written in the 20 contracts exists in `docs/2_canonical_design_spec.md` (checked by script). C4's DR-C4-nn are cited as agent drafts, never as requirement ids.

### Must-haves of the unit prompt — where each landed

- **P34.45:** the ER re-run is the only pre-authorised mutation (S5-3 "Both + list + P34.45", 04:28:49Z; expires GATE-G4); A-20 = a ("Yes, with labels", 04:25:48Z) — live-API changes disclosed by the basis label + `/status/` notice; P35.57 is not a precondition; the present-tense merge sentence stays with P35.63 (TS-03). Owns SIG-CONF-001; GQ-24 and GQ-27 flip to `enforce` here.
- **P34.46:** measured (above) — no split; go/no-go protocol (FEA-07) with numeric thresholds, degraded-mode notice, trigger pause-list rule, stop-and-ask; C-10 in Gate status, out-of-scope and an AC; A-10/ADR-159 auto-allow set; post-deploy drill (SIG-OPS-001).
- **PLAN-11B:** its row is **239, SEED-13c's range** (T3 map) — not written here. Its must-haves (SIG-TRANSP in §0.3, SIG-INGEST-004 → P35.34 MUST carried or owed, SIG-ONTO-060 enum read + proposal, the GATE-ANNOUNCE outreach-owed list SIG-CHART-033/SIG-INGEST-029/030a/SIG-CONTRIB-012, the 11B re-split rule / likely GATE-G4b, S6R-15) are SEED-13c's to land; GATE-G4's packet reports whether the re-split rule fired.
- **P34.47:** read-only; layered verdicts per 11A row (SIG-MEM-011); the handle-list + L3 §4.5 + C6 status-word probe; RI-01's repo-tip and `sig-public` condition; cannot pass with a red, a ratchet regression, a pending seed transition or a due leg; drafts the GATE-G4 packet.
- **GATE-G4 (row 260):** S5-2 packet (`continue` answers only batch lines; OM-20/rights/money/own-words lines verbatim; silence = pause); ING-GO-A/B with the Wave A/B flip lists (OP-26, S6R-17); the 11B OM-20 list (19 candidate rows from the T3 map; never-list rows named); Class R standing-go renewal (B-9 text verbatim, sha256 prefix, expiry, voiding, never by `continue`); P35.57 as an improvement, its own go line; the REVIEW-R11 → GATE-ANNOUNCE rule (information); the carried P34.6 "drill clone" question if GATE-B has not answered it.

### Decisions taken (agent readings, labelled in the contracts)

1. **P34.40 "dark":** the `/v1/*` LB rule makes the already-public API answer on the canonical origin; treated as dark (no allow-listed route changes) with a fallback: if "dark" excludes any newly answering path, the URL-map step pauses for an in-ticket go. No `sig-api` roll here; the registry mount is engineered only (bucket = P35.53).
2. **P34.43 two legs:** the `sig_recovery` role exists only after L52 (`recovery_apply`) deploys, so its login is an L2 with `live:P34.46`; the SELECT grants on `ingest_run_capture`/`entity_identity_key` are a new sqitch change after L52 that rides P34.46's deploy (P34.46's L1 re-rehearses the moved tip).
3. **P34.45 `live:P34.46`:** A-20's disclosure needs the basis label (P34.25), which deploys with P34.46's API roll; the CSV has no such edge.
4. **P34.46 post-deploy drill:** SIG-OPS-001 requires a drill after every schema-changing deploy; queued as a re-run of P34.6's drill leg under P34.6's own S5-3 entry.
5. **P34.44a:** no production write is planned in this half; the in-ticket-go pause applies only if one proves necessary.
6. **P34.38:** prepares, never flips or clears — the B1 flip patch for the operator (S6R-17), screens drafted as `screening_required`, B-42's agent clear recorded by P37.16a/b; the BidNet terms GET needs `live:P35.38a`.
7. **P34.49:** sealing only by append-only records or a restricted deny set — no delete/overwrite, no table-altering sqitch change; the capture-side SIG-INGEST-045e fix is routed as a DEFERRALS row whose owner the orchestrator assigns.
8. **P34.42b:** an overwrite check precedes removing object-delete (GCS overwrites need delete); a prefix-scoped condition is an ADR + a P37.3 DEFERRALS row, never a bucket-wide grant.
9. **P34.34a/b split content:** the empty-tile state rides with `leverage.json` in a; b is the CI export-mode build + budgets. **P34.41:** tombstones link the corrections page and never embed an address.
10. **P34.47:** uses the amended exit wording (B-8/WV-08: no response times; FEA-03: no *due* leg) where S2 §4.1 predates them.

## Checks run

| check | result |
|---|---|
| `python3 docs/build/planning/2026-09-30-next-phase/tools/s13/gen_t3.py check` | **exit 0** — "310 Round-11 manifest rows, 310 plan rows, errors 0" (titles, Harness header, no skeleton marker in the 20 files, file ↔ map ↔ manifest). |
| `bash scripts/docs/check-build-memory.sh .` | **exit 0 — no violations, 44 warnings** (the pre-existing legacy warnings SEED-13b recorded). |
| `python3 docs/build/tools/memory_guard.py all --worktree` (the mode exists) | **exit 0** — 0 violations, 0 warnings (the worktree also holds SEED-13c's concurrent edits; item count varies with them). |
| script checks over the 20 files | every SIG id exists in the spec; no `**Kind:** skeleton`; no 32-hex token; no e-mail address or personal identifier; every Load list sums to its header total and its self-entry equals the file size. |

## Open issues for the orchestrator / other units

1. **PLAN-11B (row 239) is SEED-13c's** — the PLAN-11B must-haves in this unit's prompt were not written here (see above).
2. **Carried question:** P34.40's "dark" reading (`/v1/*` newly answering on the canonical origin) — orchestrator decides or adds it to the GATE-B packet.
3. **Edges not in the CSV** (agent readings): P34.45 → `live:P34.46`; P34.43 L2 → `live:P34.46`. Both make GATE-G4 timing tight (P34.46 L2 ≥ 2026-10-14T14:00Z; the S5-3 pre-authorisations expire at GATE-G4, ≈ 10-15 → 10-17); unrun legs are re-listed on the 11B OM-20 list or go in-ticket — written into P34.47 and GATE-G4.
4. **P34.6 "drill clone" scope** (SEED-13b's carry) is also used by P34.46's post-deploy drill re-run and P34.46 L1's fresh-clone re-rehearsal; GATE-G4's packet repeats the question if GATE-B has not answered it.
5. **Estimates to re-measure at dispatch:** Load entries for files earlier rows write (P34.24b rehearsal record, P34.26 census, P34.39a report, P34.42a IaC, P34.44a harness, P34.47 packet, PLAN-11B OM-20 lines, BUILD_INDEX Round-11 rows) and every spec line-range entry (SEED-12c's BUILD.sh run will shift spec line numbers; the labels name the requirement ids, so re-measurement is mechanical).
6. **Not done here (Appendix A T3 last bullet):** the requirement → ticket index across all 60 11A rows and the fresh-context Phase-4 sizing review — this ledger gives rows 241–260; SEED-13e (CARRY) completes it.
7. **Q-E2-13** (re-deciding aikner, Calgary, Lexington, MD iMAP; CARRY) stays unowned in 11A — P34.38 names it out of scope.
8. The generator for these contracts lives in the session scratchpad (`s13d/`); the contracts are the record.
