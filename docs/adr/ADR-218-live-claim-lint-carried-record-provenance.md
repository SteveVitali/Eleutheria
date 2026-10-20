# ADR-218 — Live-claim lint: listed, verified provenance for carried records

- Date: 2026-10-20
- Status: accepted
- Ticket: P35.16 (orchestrator repair on `r11/P35.16-geometry-defects-at-ingest`, PR #309)
- Base: `r11/P35.13-provenance-stamp-release-json-headers`
- Related: SIG-MEM-011 (the live-claim binding), P35.3 (`check_live_claims.py`,
  `live_claims.toml`), ADR-199 (the "exempt by date, listed" grandfathering
  precedent the binding adopts), OP-25 (operator-approved governance change),
  BM-HIST-01 (append-only records carried verbatim)

## Context

The corpus leg of `check_live_claims.py` grandfathers a production-state claim
when `git blame` dates its line before the binding's activation (the commit
that introduced `live_claims.toml`, 2026-10-16T07:40:46Z). Blame dates a line
by the commit that introduced it on the path blame follows.

During the 2026-10-20 reconciliation of the open r11 stack (PR #293's P34.42a
records carried forward from #306 to #337), the forward merge `85b9941a` on
the P35.16 branch resolved a LEDGER conflict with `--ours`. That dropped the
incoming #293 rows the merge of `8e3a0356` was meant to carry verbatim. The
repair `e324b22c` re-added them byte-for-byte as an ordinary commit. Blame
then attributes those lines to `e324b22c` (2026-10-20), not to the
2026-10-14 commits that authored them. Five of them carry assert words, so the
corpus leg judged them as new uncited claims on every head that descends from
`e324b22c` (PRs #309 through #337), in the docs job and the python job's
`test_committed_tree_passes`. Where the same rows arrive through a merge
(#307, #308), blame follows the merge's second parent to the originals, and
the lint grandfathers them.

Three alternatives were weighed and rejected by the operator:

- re-landing all 24 affected PRs as new branches (heavy churn, stale
  PR-number references across the build memory);
- per-branch delete-then-re-merge commits that rebuild blame (transient
  deletions of append-only rows, flagged by per-commit replay);
- a waiver: the corpus leg also runs on pushes to `main`, so the red would
  persist after integration, unlike #299's waived red.

## Decision

`live_claims.toml` gains an optional `[[carried]]` array. Each entry names a
repair `commit`, the ancestor `source` it carried from (both full 40-hex
shas), and a required `reason`. In the corpus leg, a claim line blamed to a
listed `commit` is grandfathered, and reported separately as `carried` (count
plus a `carried_list` that is never truncated), only when every check holds:

1. `source` is an ancestor of `commit`;
2. the line's exact text exists in `source`'s copy of the same file;
3. `source`'s own blame dates that line before activation.

Any failed check leaves the line judged as before. New or edited text can
never qualify, because it does not exist pre-activation in the source. A
malformed entry is a usage error (exit 2), so the gate fails closed. The range
leg is unchanged.

The first entry lists `e324b22c` carried from `8e3a0356`.

## Consequences

- The five carried P34.42a lines are grandfathered by verified provenance on
  every descendant head, and the corpus leg returns to green without editing
  or re-attributing any record.
- Each future use needs a reviewed policy entry; the exemption is listed and
  scoped to one commit, never global.
- Blame of each listed source is computed once per file per run (cached).

## Revisit trigger

Revisit if a `[[carried]]` entry is ever needed for a commit that is not a
re-add of records dropped by a merge resolution, if more than three entries
accumulate (a sign the carry procedure itself needs fixing, e.g. merge-tool
guards in the reconciliation runbook), or if the corpus leg moves to a
provenance mechanism other than `git blame`.
