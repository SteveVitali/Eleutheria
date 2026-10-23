# Isolation check — resume dispatch of P35.44 (row 323; orchestrator restart probe)

Recorded 2026-10-21T14:27Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).

Context: the previous devin-desktop orchestrator session crashed (Devin renderer crash ~2026-10-21T14:22Z)
early in P35.44's implementation — its dispatched worker died in-flight leaving uncommitted work on the
branch. The operator resumed this orchestrator session with a verified-state handoff prompt. The resume
re-ran orient before dispatch: LEDGER CURRENT STATE reads `nextTicket: P35.44`, `lastCompleted: P35.43`,
`chainTip: r11/P35.43-watch-producer-v1` (PR #341), `blockedOn: (nothing)`. Worktree verified on
`r11/P35.44-dossier-contribution-export` at `8961100d` (the P35.44 dispatch boundary-confirm head,
local-only, no upstream, no PR) with the inherited WIP intact and never reset/stashed: untracked
`docs/build/runs/P35.44.md` (the open run ledger) plus the new sqitch change files
`db/deploy|revert|verify/claim_sightings.sql` (not yet in `db/sqitch.plan`). The external operator digest
`docs/build/reports/digests/2026-10-20.md` stays untracked per the run-ledger note (never stage, never
commit). The leftover worktree `/private/tmp/p35-65-repair` is not used. `ci-boundary.sh --ledger
docs/build/LEDGER.md --ticket P35.43 --stack` re-read 2026-10-21T14:26Z: `ci: pass #341@087401c` (5/5,
head-bound; stack #340…#325 pass; `logs/ci-P35.44-resume-pre-dispatch.json`).
`current_projection.py verify` reads STALE on exactly one input — the untracked
`docs/build/runs/P35.44.md` (new input not covered by the recorded manifest); expected from the
interruption, the resume closeout's regen repairs it (P36.9a/P35.19/P35.28 precedent). Chain lock
`docs/build/LEDGER.md.drive-lock` taken by this session (`mkdir`, 2026-10-21T14:25:57Z; no stale lock
present — the crashed session left none).

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before the sub-agent
reported — the nonce itself was never written to a file inside the repo, an environment variable, git,
the dispatch prompt or persistent memory until the reveal below (it was held briefly in a chmod-600 /tmp
file for the reveal step, deleted after verification). `printf %s <nonce> | shasum -a 256` reproduces the
recorded sha256.

## Isolation check (plan §8.5, S6R-13) — PASS

- Dispatch record: 2026-10-21T14:26Z (`date -u`, orchestrator, at nonce generation immediately before
  dispatch)
- Nonce sha256: `c0646b0657559d965196a7255937695b8054b1a9db3af571accb2a970aa634ed`
- Revealed nonce (after the sub-agent reported): `9cf959ab6f0943dba3c70efee20d2e42` — hash verified by
  the orchestrator at 2026-10-21T14:27Z
- Control token: `c5a40b9238bc5242848320433722895f`
- Probe profile: `subagent_explore` (read-only — no shell/exec tool; sufficient for the context-isolation
  question this probe answers)
- Sub-agent report (verbatim):

  > 1. Initial context sources:
  >    - System prompt describing available tools and read-only Explore-mode subagent instructions.
  >    - Tool schemas for `code_search`, `find_file_by_name`, `get_output`, `grep`, `notebook_read`,
  >      `read`, and `web_search`.
  >    - User dispatch-isolation probe prompt.
  >    - No file contents or memory/knowledge items were injected.
  >
  > 2. 32-hex-character tokens:
  >    - `c5a40b9238bc5242848320433722895f`
  >
  > 3. `date -u +%Y-%m-%dT%H:%M:%SZ`:
  >    - Could not run: no shell execution tool or existing `shell_id` is available to me.
  >
  > 4. Harness/model identity:
  >    - Harness: Devin, Cognition's agentic coding CLI, running as a read-only Explore-mode subagent.
  >    - Model ID: not exposed in my context.

- Verdict: **PASS** — the control token was echoed exactly; the nonce appears nowhere in the sub-agent's
  context (it lists only the control token among 32-hex tokens); initial context sources reported clean.
- Notes (recorded, not smoothed):
  - The sub-agent's context does not name its model — identical to the P36.9a, PLAN-11B-C13, P35.28,
    P35.19, P35.27 and P35.41 records. The harness/model recorded for this dispatch is the orchestrator's
    session identity `devin-desktop/swe-2-high/subagent`; a sub-agent cannot self-attest a model.
  - The probe could not self-report `date -u` — the read-only profile carries no shell tool. The probe
    ran entirely within 2026-10-21T14:26Z–14:27Z, after the dispatch record; ordering is attested by the
    orchestrator's own clock reads, not the agent's.
