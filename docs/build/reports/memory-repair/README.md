# Memory repair — Round-11 Stage-B seed

`docs/build/reports/memory-repair/` — the committed home of the build-memory repair registers (B3 §3.2,
`docs/build/planning/2026-09-30-next-phase/design/B3-ledger-redesign.md`; `PD` below = that planning directory).
Written by the Stage-B units SEED-01, SEED-04, SEED-06 and SEED-07 (T2, part α) at 2026-10-01T07:49:43Z (`date -u`), harness
`claude-code/claude-opus-5-5/subagent`; run ledger `docs/build/runs/SEED-01-04-06-07.md`. **Append-only:** later seed
units (SEED-05, SEED-10, SEED-14, …) add their files and append their own sections here; nothing in this directory is
rewritten, and a correction is a new dated row or section.

## Purpose

- **Date truth (B1 → ADR-146).** One register of every recorded date that was not taken from a clock, with the true
  time from git or GitHub, so that each control file carries a single dated DATE CORRECTION entry that points here
  instead of having its lines edited.
- **Append-only truth (B2).** The register of every commit that removed or rewrote a protected build-memory line,
  classified; the GATE DECISIONS deletion (`c2055d96`) is repaired by SEED-06, the rest by P34.27 (CF-07).
- **Transitions the seed may not make (S2 CF-03).** The queue of DEFERRALS lead-token transitions that SEED-14 decides
  but leaves for P34.8 to apply through the repaired obligation-event tool.

## Files

| file | bytes | sha256 | data rows | written by |
|---|---:|---|---:|---|
| `date_corrections.csv` | 354,386 | `f9471d43b41228ae4374741716c4b9726634110c57949de192ca95d5aa0c8648` | 1,083 | SEED-04 (promoted from `PD/data/date_drift.csv` + planning rows), extended by SEED-06 and SEED-07 |
| `append_only_register.csv` | 205,327 | `602132b40b44faa8fa1debe4e63fe912d086195e1563dfd1496b1b30ccd682ca` | 539 | SEED-04 (byte-identical copy of `PD/data/append_only_violations.csv`) |
| `pending_transitions.csv` | 154 | `084eab61e72ba340f0c3b5f4aeadfcb92de13ba225b3052e41371a03d77ebde7` | 0 | SEED-04 (header only; SEED-14 appends, P34.8 applies) |
| `README.md` | — | — | — | this file |

Still to come (other units): `LEDGER_head_R01-R10.txt` (SEED-10, C6: LEDGER lines 1–54 at `<PRE>`, byte-for-byte) and
`phase_log_index_r01-r10.csv` (SEED-05, C2; its `correction_ref` column can cite the `DC-L-nn` ids below).

## SEED-01 — C0 preflight

### Control-ledger authority (P10)

- **The operator's words (verbatim):** *"Then after that you can synthesize and proceed as you see fit"* — the end of the
  operator's S5 request, recorded verbatim in `PD/feedback/RATIFICATION_LOG.md` (lines 5–6, stamped
  2026-10-01T03:34:09Z, i.e. 2026-09-30 23:34 local −04:00; the log's closing section and META_PLAN call it the message
  of 2026-09-30) and recorded there as **the GATE-P go**.
- **Recorded as the authority for control-ledger edits** in `PD/META_PLAN.md` §11, entry 2026-10-01T07:26:23Z ("Stage B
  starts"): *"Authority for control-ledger edits (SEED-01 C0 preflight; P10): the operator's GATE-P instruction … — Stage
  B edits LEDGER, DEFERRALS, the manifest, BACKLOG and COVERAGE_MATRIX on `r11/seed` only; nothing reaches `main` (the
  operator merges)."*
- **Restore-first order:** GATE-P line A-13, round 5 (2026-10-01T04:09:43Z), the operator's answer *"Full seed
  (Recommended)"*, which answers Q-14 = a (the seed restores the deleted GATE DECISIONS rows first, B3 Q4) and
  Q-B4-1 = yes (`PD/data/decision_catalog.csv`).
- *Agent interpretation (labelled):* the go covers the append-only LEDGER and BUILD_INDEX entries and the files in this
  directory, on `r11/seed`. It covers no human gate (HG-nn), no `ingestion_permitted` flip, no merge and no production
  or GCP action.

### A1 delta re-run (read-only)

- **Procedure:** `PD/baseline/BASELINE.md` § "Delta procedure". The canonical `a1_delta.py` was extracted unchanged
  (sha256 `c71ce1dfe3a687b3712d83d820adfe09572aeedd92ded27f82a17cb7b9965090`, as recorded in BASELINE.md) and driven by
  a restricted wrapper that keeps only this unit's allowed reads: local git, `git ls-remote origin` and `gh pr list`.
  No `git fetch`, `gcloud`, `curl`, `gh api` or `gh pr checks` call was made.
- **Run:** 2026-10-01T07:35:56Z → 07:35:58Z (`date -u`), against the baseline frozen at 2026-09-30T16:31:55Z.
- **Result: 8 of 42 re-run keys changed; every change is explained** by the operator's merge sitting of #141–#154
  (2026-10-01T04:25–04:26Z; recorded in META_PLAN §11, entry 2026-10-01T05:08:27Z):

  | key | baseline | now |
  |---|---|---|
  | `git.origin_main_sha` | `b7c9e2e3` | `00f67f4b` (merge of #154) |
  | `git.origin_main_tree` | `53fa9d04` | `7eb11d62` |
  | `git.origin_main_tree_equals_p31_4_tree` | true | false (main moved past the P31.4 tree) |
  | `gh.pr_open` / `gh.pr_merged` | 49 / 142 | 36 / 155 (13 merged: #141–#154 less #148, merged earlier) |
  | `gh.open_min` | 141 | 155 |
  | `gh.lowest_open_base` | `devin/round9-waveb-seed` | `devin/p31-19-round9-closeout` (#155's base) |
  | `gh.open_heads_sha256` | `8331f062…` | `24a4f1b1…` (the open set shrank to #155–#190) |

- **Unchanged:** all 18 `mem.*` keys (the nine control files at the chain tip, byte counts and sha256) and the 7
  `mem.ledger.*` keys — so B3 C0's acceptance "delta shows no unexplained `mem.*` change" holds; the chain tip
  `devin/p33-8-agent-docs-refresh` = `b051732c` locally and on origin; `git.chain_tip_descends_from_origin_main` false;
  `git.worktree_count` 8; `gh.pr_total` 191; `gh.pr_closed` 0; `gh.open_max` 190.
- **Not re-run (45 keys), recorded as such:** `gh.ci_all_pass_count`, `gh.ci_failing_count`, `gh.ci_failing_prs` (need
  `gh pr checks`) and the 42 `prod.*` keys (need `gcloud` / `curl`). The full delta, GCP leg included, is still owed
  before T6 (META_PLAN §11, 2026-10-01T05:08:27Z).

### `<PRE>` pinned

- **`<PRE>` = `f66b245037372838260b204d5b28d9b7a4993686`** — `git rev-parse HEAD` on `r11/seed` at the preflight (2026-10-01T07:36:13Z), the commit this
  repair starts from. The unit was dispatched while HEAD was `8ce834c2`; `f66b2450` (committed 2026-10-01T07:28:09Z) adds
  only the Stage-B brief under the planning tree.
- `git diff b051732c f66b2450 -- docs/build ':!docs/build/planning' docs/tickets docs/adr db/sqitch.plan scripts/docs`
  is empty: every protected build-memory path at `<PRE>` is byte-identical to the chain tip `b051732c` (B3 §5 defines
  `<PRE>` as the seed base: the chain tip or its successor). At `<PRE>`, `docs/build/LEDGER.md` is 679,109 B, sha256
  `d459173f7afd5adab36cd42b9ab7600e4c10182305f4c9974a4da6c0f20a1a30`; `docs/build/BUILD_INDEX.md` is 295,436 B, sha256
  `7830dbc3864bf934dbc6943758a7b4a9bce39f700672cdcde9f5d1533eaad029`.
- Every "line @PRE" in this directory and in the LEDGER / BUILD_INDEX correction entries refers to `<PRE>`.

## `date_corrections.csv` (SEED-04; extended by SEED-06 and SEED-07)

- **Source.** Bytes 1–340,298 are `PD/data/date_drift.csv` (B1) unchanged — sha256
  `468132193c61c33e08078057756c0643cc170b7055c03a25ebee96f5bd8dcb7c`, 1,051 rows. The 11-column schema is unchanged:
  `path, line_or_field, recorded_value, introducing_commit, commit_date_utc, true_event_date, class, artifact_kind,
  fix_mechanism, deployed_or_signed, note` (B1 §10). No field contains a line break and lines end in CRLF as in the
  source, so **rec *n* = data record *n* = file line *n* + 1**; the correction entries cite rec numbers.
- **Appended rows (recs 1052–1083), never edits:**
  - **1052–1078 (SEED-04): the planning stamps.** A blame scan of `PD/META_PLAN.md` at `<PRE>` (every
    `2026-09-30/10-01THH:MMZ` token vs its line's committer time, flagged when more than 5 min later) finds 27 tokens:
    F-074's 24 late change-log stamps (17 commits, `6266f393` … `41ab9521`); the operator-decision stamp "18:2xZ"
    (F-074's second clause; true ≤ `e5725b7b` 17:10:49Z) and the J4 stamp (20:25Z → `56c53158` 17:55:17Z), both named
    in the META_PLAN §11 CORRECTION entry of 2026-09-30T17:56:21Z; and one class-a row (a scheduled time, not an event).
    `artifact_kind` = `planning` (a value B1 did not use). These lines are already corrected by that append-only
    META_PLAN entry; G1 never scans `docs/build/planning/**` (S6R-10), and the rows are here so the register is
    complete.
  - **1079–1082 (SEED-06):** the restored GATE DECISIONS rows R37–R40 (recorded 2026-09-10 → true ≤
    2026-09-13T19:40:01Z, `eb72be5f`; B1 §3 #2). Their `line_or_field` gives the LEDGER line at the seed write and the
    source line at `eb9a23d0`.
  - **1083 (SEED-07):** refines rec 113 — BUILD_INDEX L257 @PRE holds two `2026-10-19` tokens: the `landed` cell is
    P32.23a's landing (PR #180, 2026-09-28T02:11Z; B1 §3 #30) and the ADR-cell text is the S3 deferral (rec 113).
- **Totals:** 1,083 rows — class b 626 (595 + 31), class a 457 (456 + 1).
- **Exact times.** Where B7's reads of the Devin session store give an exact time — S3 deferral 2026-09-28T01:15:49Z,
  GATE-G3 03:49:14Z, ACCEPT-R10 18:46:46Z, confirmed by the operator at GATE-P (B-4 → Q-B1-2, 2026-10-01T04:32:16Z) —
  the LEDGER and BUILD_INDEX correction entries carry it. The register keeps B1's bound (≤ the writing commit:
  `a33cd6ec` 01:27Z, `95c8a73f` 03:49:46Z), which the exact time satisfies.
- **G1 (SEED-02):** the `recorded_value` column of this file is exempt (B4 G1 R3).
- **Never:** `db/sqitch.plan` L44–52 are not re-stamped — a local database (`sig-p332-db`) holds them as stamped (C-10,
  GATE-P round 21, 2026-10-01T04:59:41Z).

### Where each LEDGER / BUILD_INDEX register row is corrected

Every class-b row of this register for `docs/build/LEDGER.md` or `docs/build/BUILD_INDEX.md` (plus recs 1079–1083) is
referenced by exactly one correction entry (checked by the writer at write time):

| entry | location (find with `grep -n -F`) | register recs |
|---|---|---|
| GATE DECISIONS `### Round 11` row, kind `correction` | LEDGER, `### Round 11` | 172, 173 (L116 GATE-G3, L117 S3 deferral @PRE) |
| restoration annotation table, R37–R40 | LEDGER, `**Annotation of the restored rows` | 1079–1082 |
| `DC-L-01` … `DC-L-46` | LEDGER, `## DATE CORRECTIONS — LEDGER, Rounds 1–10` (end of file at the seed write) | the other LEDGER rows |
| `DC-BI-01` … `DC-BI-40` | BUILD_INDEX, `## Index repairs — Round 11 seed` → `### Row corrections — dates` | all BUILD_INDEX rows + 1083 |

Corrections for other paths in the register (runs, pr, readouts, DEFERRALS, the manifest, ADRs, spec, code, fixtures,
`*.jsonl`, release identity) belong to SEED-08, ADR-146 and the Round-11 tickets (e.g. P34.22), not to this unit.

## `append_only_register.csv` (SEED-04)

- Byte-identical to `PD/data/append_only_violations.csv` (B2): 539 rows — 405 benign, 88 transition-justified, 4
  transition-unjustified, 42 loss; sha256 `602132b40b44faa8fa1debe4e63fe912d086195e1563dfd1496b1b30ccd682ca`.
- **Resolved here:** the two `loss` rows for the GATE DECISIONS deletion (`c2055d96` and merge `e2175c93`, 56 lines
  each) — by the SEED-06 restoration (LEDGER GATE DECISIONS; find it with `grep -n -F 'RESTORED from' docs/build/LEDGER.md`; the 53 rows, contiguous, sha256
  `baec891da75e0e082d37cc69639fdf6e4910133dde1ebd9f32c9e04eef182bd8`).
- **Owed:** every other `loss` and `transition-unjustified` row — P34.27 (MEM-04, B2 steps 2–7) under M1's append-only
  modes (S2 CF-07). Resolutions are recorded where they are made, never by editing this file.

## `pending_transitions.csv` (SEED-04; S2 CF-03)

- **What it is:** the queue of DEFERRALS lead-token transitions the Stage-B seed decides but does not make, because the
  guard forbids a status-token change without an obligation event. **SEED-14** appends `queue` rows; **P34.8** (MEM-03)
  applies each through the repaired obligation-event tool and appends an `applied` row naming the event; an entry that
  will not be applied gets a `withdrawn` row. Rows are never edited or removed.
- **Columns:** `entry_id` (`PT-nnn`); `action` (`queue` / `applied` / `withdrawn`); `queue_ref` (for `applied` /
  `withdrawn`: the queued `entry_id`); `obligation_id` (`D-…`); `expected_previous_event` (the `event_id` the
  transition chains to, as in `obligation-event/1`); `from_status`, `to_status` (`OPEN` / `PARTIAL` / `DONE` /
  `WONTFIX`); `decision_ref` (the GATE-P line or GATE DECISIONS row that decides it); `decided_at` (that answer's round
  time in the ratification log); `evidence_refs` (`;`-separated paths); `reason`; `written_by` (unit or ticket);
  `written_at` (`date -u`).
- **Pending** = `queue` rows with no later `applied` or `withdrawn` row. Seeded empty (header only) by the SEED-04 write of 2026-10-01T07:46:38Z (the same `date -u` stamp as the
  LEDGER / BUILD_INDEX entries of this unit); the 11A
  exit requires 0 pending (`PD/NEXT_PHASE_PLAN.md` §9.2, S2 CF-03).
- *Agent design (labelled):* the plan names the file `pending_transitions` without fixing its shape; the columns and the
  `.csv` suffix are this unit's choice, aligned with `obligation-event/1` (`docs/build/tools/obligation_events.py`).

## Verify

```sh
D=docs/build/reports/memory-repair
head -c 340298 $D/date_corrections.csv | shasum -a 256          # = 46813219…dcb7c (PD/data/date_drift.csv)
shasum -a 256 $D/append_only_register.csv \
  docs/build/planning/2026-09-30-next-phase/data/append_only_violations.csv   # equal
git show c2055d96^:docs/build/LEDGER.md | sed -n '114,166p' | shasum -a 256   # = baec891d…82bd8
n=$(grep -n -F "$(git show c2055d96^:docs/build/LEDGER.md | sed -n '114p')" docs/build/LEDGER.md | cut -d: -f1)
sed -n "${n},$((n+52))p" docs/build/LEDGER.md | shasum -a 256                    # = baec891d…82bd8
git diff f66b2450 -- docs/build/LEDGER.md docs/build/BUILD_INDEX.md | grep -c '^-[^-]'   # = 0 (append-only)
```
