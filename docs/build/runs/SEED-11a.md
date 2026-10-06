# Run ledger — SEED-11a (Round 11 Stage B, T1): Round-11 ADRs 146–156 authored by SEED-11

- **Harness:** claude-code/claude-opus-5-5/subagent
- **Skills:** 4140fda
- **Started:** 2026-10-01T07:32:48Z
- **Closed:** 2026-10-01T07:44:42Z
- **Unit:** SEED-11a — write the ADRs numbered 146…156 whose author in `PD/NEXT_PHASE_PLAN.md` §7 is SEED-11
  (`PD` = `docs/build/planning/2026-09-30-next-phase/`); brief `PD/stageB/AGENT_BRIEF.md`.
- **Worktree / branch:** `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (no git state changed by this unit;
  the planning orchestrator commits).
- **Scope from §7 (author = SEED-11, numbers 146…156):** written — ADR-146, 147, 148, 149, 150, 152, 153, 154, 155.
  **Skipped (ticket-authored per §7):** ADR-151 "Toolchain pin and CI truth" (author **P34.1**) and ADR-156 "Public map
  v2" (author **P35.52**).
- **Contexts:** this unit's context wrote ADR-146/147/148/150 and the ledger; two forks of it (same harness and model)
  wrote ADR-152/153/154 and ADR-149/155 in parallel to the same header template; this context reviewed their files and
  normalised the headers.

## What was done

| ADR | title | Date (decision time) | operator lines (log rounds) | adopted / own words quoted (sha256) |
|---|---|---|---|---|
| 146 | Correcting recorded dates that were not taken from a clock | 2026-10-01T04:59:05Z | A-13 (5), B-4 (10), C-1 (19), C-10 (21; inspection 04:59:41Z) | — (option labels only) |
| 147 | Gate-record integrity and readout authorship | 2026-10-01T05:03:05Z | A-16 (6), B-4 (10), C-1, C-3 (19), C-13 (22–23) | C-3 sentence `1461ae21…eca6c6` (agent-drafted, adopted 04:54:19Z); the operator's S5 request `c78c3c51…6a5f` (own words, 03:34:09Z) |
| 148 | Build memory v2.1: ledger contract and enforced append-only | 2026-10-01T04:09:43Z | A-13 (5) incl. OD-05 a, OD-06, Q-17 | — |
| 149 | Round-11 operating model | 2026-10-01T06:14:06Z | A-2 (2), A-15 (6, 7, 25), A-20/A-21 (8), S5-1/S5-3 (9), S5-2 (19), S6-F3 (24) | A-15 custom answers `f48e95e0…2983` and `3f628f69…289d` (the operator's own words) |
| 150 | Coverage verdict vocabulary | 2026-10-01T05:03:05Z | B-5 (11), C-13 (22–23) | — |
| 152 | Confidence without independent review | 2026-10-01T04:43:37Z | A-6 (3), B-31 (15) | A-6 sentence `03c0a79e…dd55` (agent-drafted, adopted 04:03:25Z) |
| 153 | Derivation, not identity | 2026-10-01T04:43:37Z | A-6 (3), B-31 (15) | A-6 sentence `03c0a79e…dd55` |
| 154 | Graph-quality suite as a ratcheted release gate | 2026-10-01T04:03:25Z | A-6 (3) | — |
| 155 | HTML-first page types | 2026-10-01T04:33:54Z | A-12 (5), B-22 batch (11: D-K0-2/3/5) | — |

Every sha256 was recomputed with `printf '%s' "<sentence>" | shasum -a 256` from the log's text; the A-6 and C-3 values
equal S6 §5's. "Recorded:" stamps in the ADR headers came from `date -u` in the command that wrote them.

**Header form.** Mirrors ADR-145 and BM-ADR-01 / B4 G8-1: H1 `# ADR-NNN: <title>`; bold `Status` (Accepted), `Date`,
`Phase`, `Ticket`, `Decided by`, `Requirement ids`, `Spec`, a machine-readable `Supersedes` field (for G8-2) and a
separate `Amends / qualifies / extends` field, `Sources`, `Recorded`; sections Context / Decision / Consequences /
Alternatives considered / Revisit trigger.

**Supersedes / amends / qualifies / extends (for SEED-11d's appended status lines; from §7 unless labelled):**
- ADR-146: none. It is the correction record for the dates of 26 landed ADRs (065, 074, 076, 113, 114, 116–118, 121–129,
  134–138, 142–145; 33 positions) — no footer and no status line on any of them (CF-02).
- ADR-147: none (supersedes records: the GATE-G3 signature, ACCEPT-R10's "34 MET").
- ADR-148: **supersedes ADR-126's and ADR-127's cutover statements only**; extends ADR-073 (agent interpretation; no
  §7 line).
- ADR-149: none.
- ADR-150: none (extends ADR-126's `coverage-assessment/1` use — agent interpretation; no §7 line).
- ADR-152: none (supersedes manifest rows 184–187 as records).
- ADR-153: **supersedes ADR-105 §5; amends ADR-099 §3.**
- ADR-154: none.
- ADR-155: **supersedes ADR-091 §3–4 and ADR-097 §2–3/§6; extends ADR-134; leaves ADR-068 unchanged.**

## Checks

| check | result |
|---|---|
| `uv run pytest tests/unit/test_policy_adrs.py -q` (worktree incl. other units' new ADRs) | `169 passed in 0.14s` |
| `bash ~/.claude/skills/build-memory/scripts/adr-index.sh --check docs/adr` (read-only; index not written) | all nine rows parse: title, `Ticket` = `SEED-11 (unit SEED-11a)`, `Status` = `Accepted` |
| `git log --diff-filter=A` of each landed ADR in ADR-146's table; `git log -1` of `95c8a73f`, `a33cd6ec` | match `PD/data/date_drift.csv` |

No other file was touched; no git state was changed; the ADR index was not regenerated.

## Open issues for the orchestrator / other units

1. **ADR-155's Date** is 2026-10-01T04:33:54Z (the B-22 batch that adopted D-K0-2 Preact, D-K0-3 viewport-in-URL and
   D-K0-5), not A-12's 04:09:43Z, under the "latest round of the ADR's lines" rule; change the Date line only if the
   orchestrator wants A-12's time.
2. **ADR-155 narrows two neighbouring clauses K0 §6 does not list** — ADR-091 Decision 1 ("content pages ship no
   `<script>`") and the React choice in ADR-091 Decision 2 / ADR-097 Decision 1. Recorded as a labelled observation;
   whether they get status lines is SEED-11d's / the orchestrator's call.
3. **Requirement ids cite SEED-12's in-progress id map** (`PD/stageB/T1_id_map.csv`, read at writing): SIG-MEM-005…010,
   SIG-MEM-012, SIG-ENG-040…045, SIG-OPS-009, SIG-CONF-001…014. Re-check them against SEED-12's final map before commit.
4. **ADR-144 and ADR-145** cite the GATE-G3 signature that ADR-146/147 record as superseded; §7 assigns them no status
   line, so none is proposed (noted in ADR-147's Consequences).
5. ADR-147 labels as interpretation that the log's "msg of 2026-09-30" (GATE-P go) is the operator's local date for the
   2026-10-01T03:34:09Z request.
6. ADR-154's only S5 line is A-6, whose question does not name the suite; its link to A-6 is labelled interpretation.
7. Seen in passing, not this unit's files: ADR-158 and ADR-159 contained an `@@` placeholder at the time of the check.
