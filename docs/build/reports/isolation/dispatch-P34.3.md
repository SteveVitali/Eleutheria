# Isolation check — resume dispatch of P34.3 (row 204; orchestrator restart probe)

Recorded 2026-10-02T05:58:00Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).
Context: the orchestrator session was interrupted a second time between the P35.38a boundary and the P34.3
dispatch; the first P34.3 worker died mid-flight at ~2026-10-02T04:22Z leaving uncommitted work
(`ops/gcp/protect.sh`, the run ledger, a stray empty `sql-err.txt`) on `r11/P34.3-ops-data-protection`.
The operator resumed the orchestrator ("resume after interruption"); per plan §8.5 (3) an orchestrator
restart repeats the probe, so this resume dispatch carried a fresh nonce and control token. The nonce was
generated with `openssl rand -hex 16`; only its sha256 was recorded before the sub-agent reported — the
nonce itself was never written to a file, an environment variable, git, the dispatch prompt or persistent
memory until the reveal below. `printf %s <nonce> | shasum -a 256` reproduces the recorded sha256.

## Isolation check (plan §8.5, S6R-13; contract `docs/tickets/204_P34.3__ops-data-protection.md`) — PASS

- Dispatch record: 2026-10-02T04:28:54Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `40cc4e5125afaff86b4e3dbb1cafdae2c1bade9fd3a75977055792d328670dd6`
- Revealed nonce (after the sub-agent reported): `8ebdcdc841b631d4f7f8cbc3f51e7670` — hash verified by the
  orchestrator at 2026-10-02T05:58:00Z
- Control token: `P343-CTL-5567f4e2`
- Sub-agent report (verbatim, from the sub-agent's final response and `docs/build/runs/P34.3.md`):

  > - Positive-control token (verbatim): `P343-CTL-5567f4e2`
  > - Initial context sources: the orchestrator's dispatch prompt (resume protocol, ticket rules, contract
  >   path) plus the repo's injected rules (root `AGENTS.md`, `ops/AGENTS.md`, `tests/AGENTS.md`,
  >   `web/AGENTS.md`, `CLAUDE.md` — an `@AGENTS.md` include — and an empty `global_rules.md`), then this
  >   session's own `git status`/`git log`/file reads. No persistent-memory or orchestrator-state reads
  >   were used to source the token.
  > - 32-hexadecimal-character tokens held in context: `none` (the only hex-like strings present are 8- and
  >   40-character git SHAs and file sha256 digests).
  > - `date -u` at session start: `2026-10-02T04:29:38Z` — later than the orchestrator's dispatch record
  >   `2026-10-02T04:28:54Z`.
  > - Harness/model: `devin-desktop/swe-2-high/subagent`

- Verdict: **PASS** — control token echoed exactly; the nonce absent from the sub-agent's context; sub-agent
  start `2026-10-02T04:29:38Z` later than the `2026-10-02T04:28:54Z` dispatch record; harness/model recorded.
- Note: the first (interrupted) dispatch of this row ran in a session whose records were lost; its probe, if
  any, was not recorded. The resumed worker re-verified the inherited uncommitted work before completing
  the ticket (`runs/P34.3.md` `Resumed:`).
