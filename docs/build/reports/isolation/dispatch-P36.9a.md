# Isolation check — resume dispatch of P36.9a (row 282; orchestrator restart probe, second restart session)

Recorded 2026-10-13T13:59:32Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).

Context: this is the **second** orchestrator restart for the P36.9a boundary on 2026-10-13. The
first restart session (~13:50Z) oriented cleanly — `current_projection.py verify` fresh
(1026/1026 digests), CI boundary `ci: pass #283@993d338` (stack #233–#282 pass; main `b8842aa`
descends:no; the operator's recorded merges #218–#232 at ~03:31–03:33Z), and confirmed the
interrupted-ticket shape (branch `r11/P36.9a-statutory-disclosures-uav-frt` at `993d3383`, zero
commits ahead of `r11/P36.8-…`, uncommitted WIP: 7 modified files incl. `ops/cadence.toml`, 9
untracked `tests/connectors/fixtures/statrep/*`). It ran an isolation probe that **passed but was
never recorded** (control `7b659600415fda601ee8a99e996bc9eb` echoed, nonce absent, sub-agent start
`2026-10-13T13:53:27Z` > dispatch record `13:53:06Z`; revealed nonce `9aaa4a43efea041c9ced2440d73931ec`,
sha256 `86ff61014da57b7feac8471f46eecd6125bf08d3ab0c88a6b72221a6e7fabb0f`), then stopped on the
OM-01 harness mismatch — the session's model was claude-opus-5-5-high, not swe-2-high — and wrote
**nothing** to the tree or ledger (operator choice: "Stop; I'll restart on SWE-2"). The operator
restarted on swe-2-high ("switched to SWE-2 High here. proceed"), so this resume dispatch repeats
the probe with a fresh nonce + control per plan §8.5 (3).

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before the
sub-agent reported — the nonce itself was never written to a file, an environment variable, git,
the dispatch prompt or persistent memory until the reveal below.
`printf %s <nonce> | shasum -a 256` reproduces the recorded sha256.

## Isolation check (plan §8.5, S6R-13) — PASS

- Dispatch record: 2026-10-13T13:59:05Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `4e41e44599feed47b5fcd940c877d5fe5686e5c4a3d1e9c854e70df99ae00d4b`
- Revealed nonce (after the sub-agent reported): `6f4e62876f0e5e43c2ea2d45f8aff568` — hash verified
  by the orchestrator at 2026-10-13T13:59:32Z
- Control token: `dcc82b6de2f11736b6e128d7c0264393`
- Sub-agent report (verbatim):

  > 1. dcc82b6de2f11736b6e128d7c0264393
  > 2. Context sources: the system prompt (Devin subagent instructions + tool definitions) and this
  >    task's user message; no rules files or memory were present.
  > 3. Only the control token.
  > 4. 2026-10-13T13:59:16Z
  > 5. "You are a subagent of Devin, Cognition's agentic coding CLI." — no explicit model name/version
  >    is stated in my context.

- Verdict: **PASS** — control token echoed exactly; the nonce appears nowhere in the sub-agent's
  report (it lists only the control token among 32-hex tokens); sub-agent start `2026-10-13T13:59:16Z`
  later than the `13:59:05Z` dispatch record; initial context sources reported (system prompt + task
  only, no rules/memory). Chain lock `docs/build/LEDGER.md.drive-lock` held by this session.
- Note (recorded, not smoothed): the sub-agent's context does not name its model — identical to the
  aborted session's probe ("Subagent Default"). The harness/model recorded for this dispatch is the
  orchestrator's session identity `devin-desktop/swe-2-high/subagent` (the operator's restart
  statement is the authority); a sub-agent cannot self-attest a model. Same caveat as the
  PLAN-11B-C13 record's deviation note: recorded here, not smoothed.
