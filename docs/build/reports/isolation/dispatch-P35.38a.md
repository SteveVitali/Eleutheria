# Isolation check — resume dispatch of P35.38a (row 203; orchestrator restart probe)

Recorded 2026-10-02T04:05:00Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).
Context: the orchestrator session that closed P34.2 was interrupted after dispatching P35.38a; the first
worker died mid-flight at ~2026-10-02T02:32Z leaving uncommitted work on `r11/P35.38a-…`. The operator
resumed the orchestrator ("resume after interruption"); per plan §8.5 (3) an orchestrator restart repeats
the probe, so this resume dispatch carried a fresh nonce and control token. The nonce was generated with
`openssl rand -hex 16`; only its sha256 was recorded before the sub-agent reported — the nonce itself was
never written to a file, an environment variable, git, the dispatch prompt or persistent memory until the
reveal below. `printf %s <nonce> | shasum -a 256` reproduces the recorded sha256.

## Isolation check (plan §8.5, S6R-13; contract `docs/tickets/203_P35.38a__crawler-ua-contact-and-explanation-page.md`) — PASS

- Dispatch record: 2026-10-02T02:40:11Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `913e9933b858d82e6314eaca8125fbb5ea4f6d8cb2e9c1544b7ec6a88905db13`
- Revealed nonce (after the sub-agent reported): `f71af4b7d0791ab7e9a1430b7febf067` — hash verified by the
  orchestrator at 2026-10-02T04:05:00Z
- Control token: `P3538a-CTL-10d63f08`
- Sub-agent report (verbatim, from `docs/build/runs/P35.38a.md` § Isolation check; the same report appeared
  in the sub-agent's final response):

  > - Positive-control token: `P3538a-CTL-10d63f08`
  > - Initial context sources: the orchestrator's dispatch prompt + injected repo rules (root `AGENTS.md`,
  >   `web/AGENTS.md`, `connectors/AGENTS.md`, `tests/AGENTS.md`, `CLAUDE.md`, empty `global_rules.md`) and
  >   own `git status`/`git log` output; no persistent-memory reads
  > - 32-hexadecimal-character tokens in context: `none`
  > - `date -u` at session start: `2026-10-02T02:40:44Z` (after dispatch record `02:40:11Z`)
  > - Harness/model: `devin-desktop/swe-2-high/subagent`

- Verdict: **PASS** — control token echoed exactly; the nonce absent from the sub-agent's context (32-hex
  tokens held: none); sub-agent start `2026-10-02T02:40:44Z` later than the `2026-10-02T02:40:11Z` dispatch
  record; harness/model recorded as `devin-desktop/swe-2-high/subagent`.
- Note: the first (interrupted) dispatch of this row ran outside this orchestrator session; its probe, if
  any, was not recorded. The resumed worker re-verified the inherited uncommitted work before completing
  the ticket (recorded in `runs/P35.38a.md` `Resumed:`).
