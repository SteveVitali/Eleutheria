# Isolation check — resume dispatch of P35.45 (row 324; orchestrator restart probe)

Recorded 2026-10-21T21:52Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).

Context: the previous devin-desktop orchestrator session ended/was interrupted while the P35.45 worker
(agent `11c0aa6a`, dispatched 2026-10-21 ~17:3xZ) was mid-flight — substantial uncommitted WIP on the
branch, no surviving drive-lock, no pushed commits beyond the boundary-confirm. The operator resumed
this orchestrator session with "resume after interruption". The resume re-ran orient before dispatch:
LEDGER CURRENT STATE reads `nextTicket: P35.45`, `lastCompleted: P35.44`, `chainTip:
r11/P35.44-dossier-contribution-export` (PR #342), `blockedOn: (nothing)`. Worktree verified on
`r11/P35.45-dossiers-at-every-level-unplaced-report` at `4771e925` (the P35.45 dispatch boundary-confirm
head, local-only, never pushed) with the inherited WIP intact and never reset/stashed: staged route
restructure (`web/src/pages/dossier/[...path].{astro,json.ts}` added, `[slug]` routes renamed/deleted,
`[...path]/print.astro` rename), 25+ modified files (exports emitters, web lib, tests, COVERAGE_MATRIX,
copy-batch, LEDGER.md — the worker's in-place "`live-claim`"→"claim-lint" reword of the boundary entry +
its disclosed `P35.45 correction` entry, seed-commit declaration still owed), untracked
`exports/src/exports/dossier_keys.py`, `tests/exports/test_dossier_keys.py`, open
`docs/build/runs/P35.45.md` (232 lines). External operator digests `reports/digests/2026-10-2{0,1}.md`
stay untracked. One `devin acp` pid only in `~/Eleutheria` (47019 — this session; others' cwds are
`~/Rhēma`, `~/Heniochos`, `~/MetaHarness`) — this session drives the ledger. `ci-boundary.sh --ticket
P35.44 --stack` re-read 2026-10-21T21:51Z: `ci: pass #342@8c80634` (5/5 head-bound; stack pass;
`logs/ci-P35.45-resume-pre-dispatch.json`). Chain lock `docs/build/LEDGER.md.drive-lock` taken by this
session (`mkdir`, 2026-10-21T21:50:59Z; none present — the interrupted session left none).

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before the sub-agent
reported — the nonce itself was never written to a file inside the repo, an environment variable, git,
the dispatch prompt or persistent memory until the reveal below (held briefly in a chmod-600 /tmp file,
deleted after verification). `printf %s <nonce> | shasum -a 256` reproduces the recorded sha256.

## Isolation check (plan §8.5, S6R-13) — PASS

- Dispatch record: 2026-10-21T21:51Z (`date -u`, orchestrator, at nonce generation immediately before
  dispatch)
- Nonce sha256: `f3c4cc70a4df578addc4ce067570b7226a843e144ba79c4f3e05b9458938ad96`
- Revealed nonce (after the sub-agent reported): `75709762b25f3867e74dd7032644b0a4` — hash verified by
  the orchestrator at 2026-10-21T21:51:38Z
- Control token: `2ceaf1a3a8f39ac5a0fced891c45d5c1`
- Probe profile: `subagent_explore` (read-only — no shell/exec tool)
- Sub-agent report (verbatim):

  > 1. Initial context sources: system prompt sections describing available tools and my role as a
  >    read-only Explore-mode subagent of Devin; user prompt containing the probe instructions and
  >    positive-control token. No file contents, memory items, or knowledge items were injected/read.
  >
  > 2. 32-hex-character tokens held:
  >    `2ceaf1a3a8f39ac5a0fced891c45d5c1`
  >
  > 3. `date -u +%Y-%m-%dT%H:%M:%SZ` output: unavailable — no shell `exec` tool is available to me in
  >    this Explore-mode context, so I could not run the command.
  >
  > 4. Harness/model identity: Devin, Cognition's agentic coding CLI, running as an Explore-mode
  >    subagent. Model id is not specified in my injected context.

- Verdict: **PASS** — the control token was echoed exactly; the nonce appears nowhere in the sub-agent's
  context (it lists only the control token among 32-hex tokens); initial context sources reported clean.
- Notes (recorded, not smoothed):
  - The sub-agent's context does not name its model — identical to all prior records this round. The
    harness/model recorded for this dispatch is the orchestrator's session identity
    `devin-desktop/swe-2-high/subagent`; a sub-agent cannot self-attest a model.
  - The probe could not self-report `date -u` — the read-only profile carries no shell tool. The probe
    ran entirely within 2026-10-21T21:51Z–21:52Z, after the dispatch record; ordering is attested by the
    orchestrator's own clock reads, not the agent's.
