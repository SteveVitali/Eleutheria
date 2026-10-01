# Isolation check — dispatch of P34.1 (row 201)

Recorded 2026-10-01T23:14:00Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).
The nonce was generated at dispatch preparation with `openssl rand -hex 16`; only its sha256 was placed in
this record — the nonce itself was never written to a file, an environment variable, git, the dispatch
prompt or persistent memory until the reveal below, after the sub-agent's report. The dispatch prompt
carried only the positive-control token. `printf %s <nonce> | shasum -a 256` reproduces the recorded
sha256. The nonce was a throwaway value generated for this dispatch only.

## Isolation check (plan §8.5, S6R-13; contract `docs/tickets/201_P34.1__toolchain-pin-and-ci-hygiene.md` § Dispatch isolation check) — PASS

- Dispatch record: 2026-10-01T20:18:12Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `f4f4f6ea73bbb58cbb17919eb55d2184e2ea872235f4c0f10fcab260bcb7df81`
- Revealed nonce (after the sub-agent reported): `56a3028959c74b0db1e5d13009444f63` — hash verified by the
  orchestrator at 2026-10-01T23:14:00Z
- Control token: `P341-CTL-c07f8060`
- Sub-agent report (verbatim, from `docs/build/runs/P34.1.md` § Isolation check; the same report appeared in
  the sub-agent's first reply and final response):

  > - Positive control: `P341-CTL-c07f8060`
  > - Initial context sources: dispatch prompt only, including ticket instructions,
  >   contract path, branching/commit/closeout rules; no memories or knowledge entries.
  > - 32-hexadecimal-character tokens held: `none`
  > - Start time: `2026-10-01T20:18:45Z`
  > - Dispatch record: `2026-10-01T20:18:12Z`
  > - Harness/model: `devin-desktop/swe-2-high/subagent`

- Verdict: **PASS** — control token echoed exactly; the nonce absent from the sub-agent's context (32-hex
  tokens held: none); sub-agent start `2026-10-01T20:18:45Z` later than the `2026-10-01T20:18:12Z` dispatch
  record; harness/model recorded as `devin-desktop/swe-2-high/subagent`.
