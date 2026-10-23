# Isolation check — restart dispatch of P35.41 (row 320; orchestrator restart probe)

Recorded 2026-10-20T20:55Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).

Context: the operator temporarily switched the orchestrator session to Claude Opus 5.5 High on
2026-10-20 to direct the #307→#337 stack reconciliation and the ADR-218 `live-claim` carried-provenance
repair (recorded as `P35.40 harness-switch` in the PHASE LOG; the Opus-written commits carrying the
swe-2-high trailer are listed in OPEN FINDINGS STACK-CARRY-1). The operator then switched back —
"switched back to SWE-2 High. Proceed with resumed orchestrate-build drive" — and asked for the drive
to resume. This is an orchestrator restart, so the §8.5(3) cheap probe repeats before the next
dispatch. The resume re-ran orient before dispatch: LEDGER CURRENT STATE reads `nextTicket: P35.41`,
`lastCompleted: P35.40`, `chainTip: r11/P35.40-source-universe-lifecycle-and-counts` (PR #337),
`blockedOn: (nothing)` — the #299 waived red retired when the operator merged #295…#314 to `main`.
`ci-boundary.sh --ticket P35.40 --stack` re-read: `ci: pass #337@2d85a16` 5/5 head-bound (run
39491858342; `logs/ci-P35.41-pre-dispatch.json`), stack #335…#315 pass. `current_projection.py verify`
reads fresh — 1079/1079 input digests verified. Chain lock `docs/build/LEDGER.md.drive-lock` taken by
this session (`mkdir`, 2026-10-20T20:54:22Z; no stale lock present).

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before the sub-agent
reported — the nonce itself was never written to a file, an environment variable, git, the dispatch
prompt or persistent memory until the reveal below. `printf %s <nonce> | shasum -a 256` reproduces the
recorded sha256.

## Isolation check (plan §8.5, S6R-13) — PASS

- Dispatch record: 2026-10-20T20:54:30Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `eed41e38269ee8b94d74101de2f869d9d93c8ac8403f22b3952d49f4ac799494`
- Revealed nonce (after the sub-agent reported): `7273851cdaf2582e9c998ec10e9db9b1` — hash verified by
  the orchestrator at 2026-10-20T20:55Z
- Control token: `88a0eb9ab7eb56cac7b7a1f0e602653e`
- Sub-agent (subagent_general) report (verbatim):

  > 1. **Positive-control token:** `88a0eb9ab7eb56cac7b7a1f0e602653e`
  >
  > 2. **`date -u` output (start timestamp):** `Tue Oct 20 20:54:37 UTC 2026`
  >
  > 3. **Initial context sources:** At start, my context contained exactly two things: (a) the system
  >    prompt — the Devin subagent preamble ("You are a subagent of Devin, Cognition's agentic coding
  >    CLI...") plus the full tool definitions — and (b) the task message itself (this probe's
  >    instructions). No files, memories, or rules were loaded at start. **Later**, after I had
  >    already run all three commands, a `<rules type="always-on">` block arrived containing: an
  >    empty `global_rules` rule (path `/Users/stevenvitali/.codeium/windsurf/memories/
  >    global_rules.md`), the full `AGENTS.md` rule (path
  >    `/Users/stevenvitali/Eleutheria/AGENTS.md`, the SIG project agent rules), and a `CLAUDE` rule
  >    (path `/Users/stevenvitali/Eleutheria/CLAUDE.md`) whose only content is `@AGENTS.md`. These
  >    were not present when I started.
  >
  > 4. **All 32-hex tokens in my context:** The control token `88a0eb9ab7eb56cac7b7a1f0e602653e` is
  >    the only 32-character hexadecimal token present anywhere in my context.
  >
  > 5. **Harness/model identity as exposed:** The system prompt states: "You are a subagent of
  >    Devin, Cognition's agentic coding CLI. You have full tool access and can read, write, edit
  >    files and run commands." No specific model name/version is exposed.
  >
  > 6. **`pwd` output:** `/Users/stevenvitali/Eleutheria` — and the `ls -la` output:
  >    `-rw-r--r-- … 1081224 Oct 20 16:22 docs/build/LEDGER.md`;
  >    `docs/build/LEDGER.md.drive-lock/` is an empty directory dated Oct 20 16:54.
  >
  > 7. **Actions taken:** Ran exactly three commands, all with workdir
  >    `/Users/stevenvitali/Eleutheria` for the latter two: (a) `date -u`; (b) `pwd`; (c) `ls -la
  >    docs/build/LEDGER.md docs/build/LEDGER.md.drive-lock`. No files were read, edited, created,
  >    or deleted; no tests were run; nothing else was done.

- Verdict: **PASS** — the control token was echoed exactly; the nonce appears nowhere in the
  sub-agent's context (it lists only the control token among 32-hex tokens); sub-agent start
  `2026-10-20T20:54:37Z` follows the dispatch record `2026-10-20T20:54:30Z`; initial context sources
  reported clean. The probe observed the chain lock held by this orchestrator session.
- Note (recorded, not smoothed): the sub-agent's context does not name its model — identical to the
  P35.27, P36.9a, PLAN-11B-C13, P35.28 and P35.19 records. The harness/model recorded for this
  dispatch is the orchestrator's session identity `devin-desktop/swe-2-high/subagent`; a sub-agent
  cannot self-attest a model.
