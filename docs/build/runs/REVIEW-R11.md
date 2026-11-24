# REVIEW-R11 — Round-11 closing review (independent findings register)

- **Unit:** REVIEW-R11 — a unit outside the chain, not a manifest row
  (`00_MANIFEST.md` REVIEW-R11 note; runs after P38.4, before GATE-ANNOUNCE;
  its S0/S1 register feeds P38.5's packet, every finding dispositioned by the
  operator per S6-F3).
- **Harness:** devin-desktop/swe-2-high/subagent — **agent-drafted review**
  (the manifest specs "Claude Code, Opus 5.5, xhigh"; the operator elected a
  Devin review worker; the register's provenance line says so honestly).
- **Worktree / branch:** `/private/tmp/sig-review-r11` on
  `r11/ops-review-r11`, forked at `58d81274` (the landed P38.4 tip).
  Other branches/worktrees untouched; `main` untouched; nothing merged.
- **Reviewed range:** `main...HEAD` — merge-base `2f4e9e57`, 3,778 commits,
  8,873 files, +2,274,567/−16,346 (rows 201–509 chain).
- **Started:** 2026-11-23, before the first `date -u` read of this session
  (2026-11-23T23:14Z) — dispatch time recorded bounded, not fabricated
- **Closed:** 2026-11-23T23:14Z (`date -u` at close of register writing;
  commit timestamps are git-authoritative)
- **Config:** read-only review — no code change, no live/hosted leg, no
  production mutation, no gate tick, no source flip, no operator contact.
- **Output:** `docs/build/reports/review-r11/FINDINGS.md` — the S0/S1/S2/nit
  register (this file is the run ledger).

## Deferrals read

`docs/tickets/DEFERRALS.md` read first (196 owed obligations at read —
`return_pass.py check` green, each in exactly one home). No OPEN row names
REVIEW-R11 as its home (it is not a chain row). This review opens **none**,
closes **none** — its findings are disposition proposals for the operator,
never new `D-` rows.

## What was run (verbatim verdicts in the register §0)

All green unless noted: `memory_guard all --worktree`, `check_coverage_matrix`
(994 rows OK), `check_backlog`, `obligation_events check` (14 warnings),
`check_round_close check`, `check_live_claims corpus`, `check_spec_src`,
`ledger_contract`, `return_pass check`, `adr_index_check`, `adr_triggers`,
`audit_current_state --require-reconciled`, `check_runbook`,
`redaction_guard`, `current_projection generate+verify` (temp dir),
`secret_scan`, `check_trailers` (HEAD~50 sample).

Red results, decomposed in the register:

- `check_round_close check --round-tail 2026-10-01` — 13 problems (expected
  pre-tail state; → S2-1).
- `check_live_claims range main...HEAD` — 112 violations, **all** blamed to
  pre-activation commits (grandfathered-eligible; range mode does not
  grandfather — artifact, no finding).
- `check_gate_signatures --range main...HEAD` — 842/842 uncovered: artifact of
  `allowed_signers` absent at the merge-base + unsigned GitHub merges +
  pre-regime records. Decomposed per-commit: all post-key flagged operator
  commits verify `G`; **one** genuinely uncovered post-key record stands —
  `6df21fce`'s `decision` row at LEDGER:325 (→ S1-1).

## Findings

| id | severity | finding |
|---|---|---|
| S1-1 | S1 | uncovered `decision` gate record at HEAD — ING-GO-B row, `docs/build/LEDGER.md:325`, blame unsigned `6df21fce`; waiver substance only in exempt `confirmation` rows |
| S2-1 | S2 | tail probe sweep red pre-P38.5; `api-release-parity` + `number-truth` committed records vacuous (all-skipped) |
| S2-2 | S2 | `nightly.yml` standing red (≥43 consecutive, recorded `NIGHTLY-RED-1`) — announce-optics/correctness item |
| S2-3 | S2 | 14 obligation-ledger warnings — volatile `docs/build/logs/**` + stale superseded-row refs |
| nit-1 | nit | `evidence_capture` in-place backfill UPDATE (`claim_assertion_bindings`) — disclosed new-column exception |
| nit-2 | nit | curation token `resolve` non-constant-time; demo-token strip is DSN-detected |

**S0: none. S1: one.** An empty register was a valid outcome; the evidence
showed one S1 — recorded, not manufactured, not suppressed.

## Gap table — review clauses

| clause | verdict | record |
|---|---|---|
| Harness/model honestly labelled (the Opus-spec gap named, not hidden) | met | header + register provenance line — `devin-desktop/swe-2-high/subagent`, never labelled the specced Opus review |
| Adversarial, evidence-bound; every finding cites a record | met | each finding names file:line + blame/command evidence |
| Read-only — no production/live/gate/merge act | met | tool runs + git reads only; the two written files are the register + this ledger |
| High-risk surfaces sampled (db sqitch, policy, api authz, ops, exports, Part VIII) | met | §2 of the register — sampled-clean list with what was checked |
| Reconciliation honesty spot-checked (10–15 entries) | met | 15 entries — all honest (register §2) |
| No findings manufactured or suppressed | met | 1 S1 recorded; tool-artifact reds decomposed, not suppressed |
| Commits trailered; no gate-affecting record authored | met | `Harness: devin-desktop/swe-2-high/subagent` trailer; no decision/waiver/readout row touched |
| PR vs fork base (chain convention H2 PR-1) | met | base `r11/P38.4-round11-docs-refresh`; never merged by the agent |
