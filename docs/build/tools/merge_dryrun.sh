#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
#
# merge_dryrun.sh — prove the open-PR stack integrates cleanly, WITHOUT touching
# any ref (P20.3, deliverable 1; owned by docs/tickets/P20.3__integration-release.md).
#
# What it does (idempotent, read-only w.r.t. every ref):
#   1. `gh pr list --state open` → every open PR, in ascending number order.
#   2. In a THROWAWAY detached worktree checked out at origin/main:
#        Pass A (independent) — for each PR head: `git merge --no-commit --no-ff`,
#          record rc + conflicted files, `git merge --abort`. Isolates each PR's
#          conflict surface against main.
#        Pass B (bottom-up)  — reset the detached HEAD to origin/main and merge the
#          PR heads in number order, committing each on the DETACHED HEAD only
#          (never a branch ref), then assert the accumulated tree equals the
#          top (highest-numbered) PR's tree.
#   3. `git worktree remove --force` + prune. Prints a table; exits non-zero if
#      ANY PR conflicts (Pass A) or the bottom-up tree does not match the top PR.
#
# It creates NO branch, NO tag, NO commit on any real ref, and never pushes. The
# operator runs it immediately before integrating (INTEGRATION_PLAN.md §(d)); this
# ticket runs it now and pastes the table into INTEGRATION_PLAN.md §(b).
#
# Requirements: bash, git, gh (authenticated), jq (via gh --jq). Run from anywhere
# inside the repo. Invoke as `sh docs/build/tools/merge_dryrun.sh` or directly;
# it re-execs under bash (it uses arrays + process substitution).
# Re-exec into a full (non-POSIX) bash: `sh …` may be bash in POSIX mode, which
# rejects the arrays + process substitution below. The guard prevents a loop.
if [ -z "${SIG_MERGE_REEXEC:-}" ]; then SIG_MERGE_REEXEC=1 exec bash "$0" "$@"; fi
set -euo pipefail

WORKTREE="${SIG_MERGE_WORKTREE:-/tmp/sig-merge}"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# --- refuse to run with a dirty index in the worktree path -------------------
cleanup() {
  # Remove the throwaway worktree if it exists; never touch real refs. Called
  # directly (not via a path-grep) so the /tmp -> /private/tmp symlink on macOS
  # can't cause a stale worktree to survive.
  git worktree remove --force "$WORKTREE" 2>/dev/null || true
  rm -rf "$WORKTREE" 2>/dev/null || true
  git worktree prune 2>/dev/null || true
}
trap cleanup EXIT

echo "== merge_dryrun.sh =="
echo "repo:        $REPO_ROOT"

# Refresh remote-tracking refs so the dry-run reflects the server. This updates
# ONLY refs/remotes/* (never local main); the caller can skip it by exporting
# SIG_MERGE_NO_FETCH=1 (e.g. offline re-runs).
if [ "${SIG_MERGE_NO_FETCH:-0}" != "1" ]; then
  git fetch --quiet origin
fi

BASE_REF="origin/main"
BASE_SHA="$(git rev-parse "$BASE_REF")"
echo "base:        $BASE_REF ($BASE_SHA)"

# --- enumerate open PRs in ascending number order ----------------------------
# Fields: number, head branch, base branch, head commit SHA.
PR_ROWS=()
while IFS= read -r line; do
  [ -n "$line" ] && PR_ROWS+=("$line")
done < <(
  gh pr list --state open --limit 200 \
    --json number,headRefName,baseRefName,headRefOid \
    --jq 'sort_by(.number)[] | "\(.number)\t\(.headRefName)\t\(.baseRefName)\t\(.headRefOid)"'
)

if [ "${#PR_ROWS[@]}" -eq 0 ]; then
  echo "no open PRs — nothing to dry-run."
  exit 0
fi

echo "open PRs:    ${#PR_ROWS[@]}"
echo

# --- throwaway detached worktree at origin/main ------------------------------
cleanup
git worktree add --detach --quiet "$WORKTREE" "$BASE_SHA"

declare -a NUMS HEADS BASES SHAS
for row in "${PR_ROWS[@]}"; do
  IFS=$'\t' read -r n head base sha <<<"$row"
  NUMS+=("$n"); HEADS+=("$head"); BASES+=("$base"); SHAS+=("$sha")
done

# --- Pass A: independent merge of each PR head onto origin/main ---------------
declare -a A_RC A_CONFLICTS
ANY_CONFLICT=0
for i in "${!NUMS[@]}"; do
  git -C "$WORKTREE" reset --hard --quiet "$BASE_SHA"
  git -C "$WORKTREE" clean -fdq
  set +e
  git -C "$WORKTREE" merge --no-commit --no-ff --quiet "${SHAS[$i]}" >/dev/null 2>&1
  rc=$?
  set -e
  conflicts="$(git -C "$WORKTREE" diff --name-only --diff-filter=U | tr '\n' ' ' | sed 's/ *$//')"
  A_RC+=("$rc")
  if [ -n "$conflicts" ]; then
    A_CONFLICTS+=("$conflicts")
    ANY_CONFLICT=1
  else
    A_CONFLICTS+=("[none]")
  fi
  git -C "$WORKTREE" merge --abort 2>/dev/null || true
done

# --- Pass B: bottom-up accumulation on the detached HEAD ----------------------
git -C "$WORKTREE" reset --hard --quiet "$BASE_SHA"
git -C "$WORKTREE" clean -fdq
BOTTOMUP_OK=1
declare -a B_STAGED
for i in "${!NUMS[@]}"; do
  set +e
  git -C "$WORKTREE" merge --no-commit --no-ff --quiet "${SHAS[$i]}" >/dev/null 2>&1
  set -e
  u="$(git -C "$WORKTREE" diff --name-only --diff-filter=U)"
  if [ -n "$u" ]; then
    BOTTOMUP_OK=0
    ANY_CONFLICT=1
    B_STAGED+=("CONFLICT")
    git -C "$WORKTREE" merge --abort 2>/dev/null || true
    break
  fi
  # Commit the merge on the detached HEAD (no branch ref is created or moved).
  git -C "$WORKTREE" commit --no-edit --quiet \
    -m "dry-run bottom-up merge of PR #${NUMS[$i]} (${HEADS[$i]})" >/dev/null 2>&1 || true
  staged="$(git -C "$WORKTREE" diff --name-only "$BASE_SHA" HEAD | wc -l | tr -d ' ')"
  B_STAGED+=("$staged")
done

# Top PR = highest number (last in ascending order).
TOP_IDX=$(( ${#NUMS[@]} - 1 ))
TOP_SHA="${SHAS[$TOP_IDX]}"
TREE_MATCH="n/a"
if [ "$BOTTOMUP_OK" -eq 1 ]; then
  acc_tree="$(git -C "$WORKTREE" rev-parse 'HEAD^{tree}')"
  top_tree="$(git -C "$WORKTREE" rev-parse "${TOP_SHA}^{tree}")"
  if [ "$acc_tree" = "$top_tree" ]; then
    TREE_MATCH="yes (== PR #${NUMS[$TOP_IDX]} tree $top_tree)"
  else
    TREE_MATCH="NO (acc $acc_tree != top $top_tree)"
    ANY_CONFLICT=1
  fi
fi

# --- report table ------------------------------------------------------------
echo "PR      head                                         base                                 rc  conflicts"
echo "------  -------------------------------------------  -----------------------------------  --  ---------"
for i in "${!NUMS[@]}"; do
  printf '#%-5s  %-43s  %-35s  %-2s  %s\n' \
    "${NUMS[$i]}" "${HEADS[$i]}" "${BASES[$i]}" "${A_RC[$i]}" "${A_CONFLICTS[$i]}"
done
echo
echo "bottom-up accumulation: $( [ "$BOTTOMUP_OK" -eq 1 ] && echo "clean (${#NUMS[@]}/${#NUMS[@]})" || echo "STOPPED on conflict" )"
echo "final tree == top PR:   $TREE_MATCH"

# --- verify no real ref moved ------------------------------------------------
cleanup
AFTER_MAIN="$(git rev-parse main 2>/dev/null || echo '(no local main)')"
AFTER_OMAIN="$(git rev-parse origin/main)"
echo
echo "main:        $AFTER_MAIN"
echo "origin/main: $AFTER_OMAIN (base was $BASE_SHA)"
echo "worktrees:   $(git worktree list | wc -l | tr -d ' ') (expect 1 — main tree only)"

if [ "$ANY_CONFLICT" -ne 0 ]; then
  echo
  echo "RESULT: CONFLICTS or tree mismatch found — see table above. (exit 1)"
  exit 1
fi
echo
echo "RESULT: all ${#NUMS[@]} open PRs merge clean; bottom-up tree matches the top PR. (exit 0)"
exit 0
