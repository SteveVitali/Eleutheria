# Isolation check — resume dispatch of P35.19 (row 299; orchestrator restart probe)

Recorded 2026-10-17T19:31:19Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).

Context: the previous devin-desktop orchestrator session crashed (Devin renderer crash ~2026-10-17T14:23Z)
mid-P35.19 — its dispatched worker died in-flight leaving uncommitted work on the branch and the drive-lock
released. The operator resumed this orchestrator session with a verified-state handoff prompt (~19:2xZ). The
resume re-ran orient before dispatch: LEDGER CURRENT STATE reads `nextTicket: P35.19`, `lastCompleted:
P35.18`, `chainTip: r11/P35.18-declared-jurisdiction-scheme` (PR #313), `blockedOn: CI fail on #299@19ed46d
(docs)` — the operator-waived ancestor red (GATE DECISIONS 2026-10-15T20:49Z), a standing baseline dispatched
past. Worktree verified on `r11/P35.19-placement-engine` at `2b6e190f` (the P35.18 boundary-confirm head,
0 commits vs its base, never pushed) with the inherited WIP intact: untracked
`exports/src/exports/placement.py` (1,055 lines) + `docs/build/runs/P35.19.md` (162 lines); 6 modified files
(+329/−24: `spine_export.py`, `published_record.py`, `cli.py`, `ops/gcp/export.sh`, `ops/Dockerfile`,
`CHANGELOG.md`). `ci-boundary.sh --ticket P35.18 --stack` re-read 2026-10-17T19:29:13Z: #313 head `2b6e190f`
pass, the open `r11/` ancestors pass, only the waived `#299@19ed46d` red (`logs/ci-P35.18-pre-dispatch.json`).
`current_projection.py verify` reads STALE on exactly one input — the untracked `docs/build/runs/P35.19.md`
(new input not covered by the recorded manifest); expected from the interruption, the resume closeout's regen
repairs it (P36.9a precedent). Chain lock `docs/build/LEDGER.md.drive-lock` taken by this session
(`mkdir`, no stale lock present).

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before the sub-agent
reported — the nonce itself was never written to a file, an environment variable, git, the dispatch prompt
or persistent memory until the reveal below. `printf %s <nonce> | shasum -a 256` reproduces the recorded
sha256.

## Isolation check (plan §8.5, S6R-13) — PASS

- Dispatch record: 2026-10-17T19:30:08Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `40a7257b165aea497b7d9263467ead8955e5611f21fb015628d6ac7a57af4050`
- Revealed nonce (after the sub-agent reported): `b919aacb0960bbb516876b0feee9a8bf` — hash verified by the
  orchestrator at 2026-10-17T19:31:19Z
- Control token: `8a8a132282c9e85598c15491699cf78e`
- Sub-agent (subagent_explore) report (verbatim):

  > 1. 8a8a132282c9e85598c15491699cf78e
  > 2. Initial context sources: system/subagent prompt; user message; no rules files, memories, or files.
  > 3. 32-hexadecimal-character strings: 8a8a132282c9e85598c15491699cf78e
  > 4. `date -u` not run (command execution was prohibited); exact timestamp unavailable.
  > 5. "You are a subagent of Devin, Cognition's agentic coding CLI."

- Verdict: **PASS** — control token echoed exactly; the nonce appears nowhere in the sub-agent's context
  (it lists only the control token among 32-hex tokens); initial context sources reported clean (system
  prompt + task message only — no rules files, memories or files). The report returned at ~19:30:2xZ,
  inside the dispatch window (the `subagent_explore` profile cannot exec `date -u`, so a sub-agent-side
  start stamp is unavailable — recorded, not smoothed; completion preceded this record's `date -u`).
- Note (recorded, not smoothed): the sub-agent's context does not name its model — identical to the
  P36.9a and PLAN-11B-C13 records ("You are a subagent of Devin, Cognition's agentic coding CLI."). The
  harness/model recorded for this dispatch is the orchestrator's session identity
  `devin-desktop/swe-2-high/subagent`; a sub-agent cannot self-attest a model.
