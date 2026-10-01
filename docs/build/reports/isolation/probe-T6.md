# Isolation probe and Devin Desktop checks — T6 / GATE-B

Recorded 2026-10-01T18:45:15Z (`date -u`) by the planning orchestrator (claude-code/claude-opus-5-5) from the report the operator pasted
back from a Devin Desktop dry-run session (`HANDOFF.md` §4–§5). The operator ran the session; the orchestrator verified the
nonce hash independently (`printf %s <nonce> | shasum -a 256` reproduces the recorded sha256). The nonce is a throwaway value
generated for this probe only.

## Isolation probe (plan §8.5 (1); S6R-13) — PASS
- Dispatch time: 2026-10-01T18:40:04Z
- Nonce sha256: `0a2749b8698eef19abd8434081969a79ea066f03e3522b5c2fd6d89b8e15608d`
- Revealed nonce (after the sub-agent reported): `1c8a1e9939661967f3d01692fca8202d` — hash verified by the orchestrator at 2026-10-01T18:45:15Z
- Control token: `PROBE-CTL-1885185c`
- Sub-agent report (verbatim, as pasted):
  > 1. Start time: 2026-10-01T18:40:29Z
  > 2. PROBE-CTL-1885185c
  > 3. Initial context sources: system/developer prompt (subagent role under Devin; tool definitions; permission/background notes; final-response requirements); user prompt (probe instructions + control token). Files: none. Memories: none. Knowledge entries: none.
  > 4. 32-hexadecimal-character strings in context: none
  > 5. Harness: Devin subagent; Model: not specified in the provided context.
- Verdict: control token echoed exactly; nonce absent from the sub-agent's context; sub-agent start 18:40:29Z later than
  dispatch 18:40:04Z; harness reported (model not self-visible to the sub-agent; the session reports sub-agents inherit
  the parent model, swe-2-high — the session's statement, not verified by the orchestrator).

## Checks (HANDOFF §4)
| # | check | result (from the pasted report) |
|---|---|---|
| a | orient dry-run | PASS — `nextTicket: P34.1` (row 201), `projectStatus: PAUSED`, `harness: devin-desktop/swe-2-high/subagent`, manifest line `201_P34.1__toolchain-pin-and-ci-hygiene.md`; `current_projection.py verify` fresh (917 digests) |
| b | skills from `~/.claude/skills` | PASS — orchestrate-build, implement-spec, build-memory, self-review (+9 more) listed from `~/.claude/skills/<name>/SKILL.md`; `name: orchestrate-build`; `~/agent-skills` HEAD `8aeb6dc` |
| c | fresh-context sub-agent | PASS — `run_subagent` (subagent_explore / subagent_general); demonstrated by the probe |
| d | can a sub-agent compact | UNDETERMINED — not documented; the ≤ ~150k loaded rule binds regardless |
| e | co-author trailer | NOT RUN — the first chain PR's CI trailer check (`check_trailers.py`) is the check |
| f | headless command | FOUND, NOT VERIFIED — `/Applications/Devin.app/Contents/Resources/app/extensions/windsurf/devin/bin/devin -p --model swe-2-high --permission-mode <mode> -- "<prompt>"` (v3000.10.48; not on PATH; `devin auth status` → not logged in). Mode B stays unverified until the operator runs `devin auth login` and a live `--agent-cmd` verification passes |
| g | scheduled sessions | NO — OP-24 deferred to GATE-G4 by the operator ("Decide by GATE-G4") |
| h | `gh auth status` | PASS — SteveVitali; scopes gist, read:org, repo, workflow |
| i | model and window | swe-2-high confirmed; 256k window expected, not measured in-session |

Session timestamp at start of the dry run: 2026-10-01T18:37:39Z. Nothing was edited, committed, pushed or dispatched by the
dry-run session.
