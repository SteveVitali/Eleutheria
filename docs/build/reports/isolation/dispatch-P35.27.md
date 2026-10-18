# Isolation check — resume dispatch of P35.27 (row 306; orchestrator restart probe)

Recorded 2026-10-18T19:09:15Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).

Context: the previous devin-desktop orchestrator session crashed (Devin renderer crash ~2026-10-18T17:30Z)
mid-P35.27 — its dispatched worker died in-flight leaving uncommitted work on the branch and no surviving
drive-lock. The operator resumed this orchestrator session with a verified-state handoff prompt (~18:5xZ).
The resume re-ran orient before dispatch: LEDGER CURRENT STATE reads `nextTicket: P35.27`, `lastCompleted:
P35.26`, `chainTip: r11/P35.26-roles-and-time-backend` (PR #320), `blockedOn: CI fail on #299@19ed46d
(docs)` — the operator-waived ancestor red (GATE DECISIONS 2026-10-15T20:49Z), a standing baseline dispatched
past. Worktree verified on `r11/P35.27-resolver-input-truth` at `ae70500e` (the P35.27 dispatch
boundary-confirm head, 0 commits vs its base, never pushed) with the inherited WIP intact: untracked
`docs/build/runs/P35.27.md` plus modified `reconcile/src/reconcile/resolve.py`,
`reconcile/src/reconcile/rationale.py`, `reconcile/src/reconcile/data/ruleset.toml`. No other Devin
session drives this ledger (the only other `devin acp` pid's cwd is `~/Rhēma`, not this repo — same
precedent as P35.28). `ci-boundary.sh --ticket P35.26 --stack` re-read 2026-10-18T19:06:45Z: #320 head
`ae70500e` pass (5/5), the open `r11/` ancestors pass, only the waived `#299@19ed46d` red
(`logs/ci-P35.26-pre-dispatch-resume.json`). `current_projection.py verify` reads STALE on exactly one
input — the untracked `docs/build/runs/P35.27.md` (new input not covered by the recorded manifest);
expected from the interruption, the resume closeout's regen repairs it (P36.9a/P35.19 precedent). Chain
lock `docs/build/LEDGER.md.drive-lock` taken by this session (`mkdir`, 2026-10-18T19:06:45Z; no stale lock
present).

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before the sub-agent
reported — the nonce itself was never written to a file, an environment variable, git, the dispatch prompt
or persistent memory until the reveal below. `printf %s <nonce> | shasum -a 256` reproduces the recorded
sha256.

## Isolation check (plan §8.5, S6R-13) — PASS

- Dispatch record: 2026-10-18T19:08:56Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `be3f9a94fcd8eea290e8ef2c0c1abd9ca584a15be8af853de885c71a8e4a3e2c`
- Revealed nonce (after the sub-agent reported): `e32d30a4255c5214d5ed2563ee3e5aa9` — hash verified by the
  orchestrator at 2026-10-18T19:09:15Z
- Control token: `4b77aa2b735469ee0b4c0da78fda83c9`
- Sub-agent (subagent_general) report (verbatim):

  > **Isolation-check probe report**
  >
  > 1. **Positive-control token:** `4b77aa2b735469ee0b4c0da78fda83c9`
  >
  > 2. **`date -u` output (start timestamp):** `Sun Oct 18 19:08:58 UTC 2026`
  >
  > 3. **Initial context sources:**
  >    - System prompt: identity line "You are a subagent of Devin, Cognition's agentic coding CLI" plus
  >      tool-use/permission and reporting instructions for a subagent.
  >    - User/task message: this isolation-check probe spec (the token, the allowed command list, the
  >      report format).
  >    - Mid-task injection (arrived as a second user turn *after* my commands ran, not present at start):
  >      a `<rules type="always-on">` block containing
  >      `/Users/stevenvitali/.codeium/windsurf/memories/global_rules.md` (empty),
  >      `/Users/stevenvitali/Eleutheria/AGENTS.md` (full SIG build-orchestrator ruleset), and
  >      `/Users/stevenvitali/Eleutheria/CLAUDE.md` (`@AGENTS.md` reference).
  >    - No files were read into context; no other memories.
  >
  > 4. **All 32-hex tokens in my context:** `4b77aa2b735469ee0b4c0da78fda83c9` — the only one. (The
  >    injected AGENTS.md contains no 32-hex strings.)
  >
  > 5. **Harness/model identity as exposed:** "You are a subagent of Devin, Cognition's agentic coding
  >    CLI." No model name is exposed to me.
  >
  > 6. **`pwd` output:** `/Users/stevenvitali/Eleutheria`. `docs/build/LEDGER.md.drive-lock` **exists** —
  >    it is an empty directory (`drwxr-xr-x`, `total 0`, only `.` and `..`), mtime **Oct 18 15:06**.
  >    (`LEDGER.md` also exists: `-rw-r--r--`, 1,028,968 bytes, mtime Oct 18 12:49.)
  >
  > 7. **Actions taken:** `date -u`; `pwd`;
  >    `ls -la docs/build/LEDGER.md docs/build/LEDGER.md.drive-lock` (with
  >    `workdir=/Users/stevenvitali/Eleutheria`). Nothing else — no edits, no creates, no deletes, no
  >    tests.

- Verdict: **PASS** — the control token was echoed exactly; the nonce appears nowhere in the sub-agent's
  context (it lists only the control token among 32-hex tokens); sub-agent start `2026-10-18T19:08:58Z`
  follows the dispatch record `2026-10-18T19:08:56Z`; initial context sources reported clean. The probe
  observed the chain lock held by this orchestrator session.
- Note (recorded, not smoothed): the sub-agent's context does not name its model — identical to the
  P36.9a, PLAN-11B-C13, P35.28 and P35.19 records. The harness/model recorded for this dispatch is the
  orchestrator's session identity `devin-desktop/swe-2-high/subagent`; a sub-agent cannot self-attest a
  model.
