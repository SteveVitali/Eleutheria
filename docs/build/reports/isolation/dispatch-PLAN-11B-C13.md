# Isolation check — resume dispatch of PLAN-11B context C13 (row 239; orchestrator restart probe)

Recorded 2026-10-06T14:52Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).
Context: the prior orchestrator session ended after the PLAN-11B C12 close record (`bb4298f0`,
~2026-10-06T06:54Z boundary); an uncommitted `docs/tickets/REQUIREMENT_INDEX_R11.md` regeneration
(dated 2026-10-06T07:35:17Z in its generated header; `req_index.py check` → `req_index: current`)
survived as the only trace of an interrupted C13 attempt — the same shape as the interrupted P34.3 /
P35.38a dispatches. The operator resumed the orchestrator ("Resume the in-progress SIG build"); per
plan §8.5 (3) an orchestrator restart repeats the probe, so this resume dispatch carried a fresh nonce
and control token. The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded
before the sub-agent reported — the nonce itself was never written to a file, an environment
variable, git, the dispatch prompt or persistent memory until the reveal below.
`printf %s <nonce> | shasum -a 256` reproduces the recorded sha256.

## Isolation check (plan §8.5, S6R-13; contract `docs/tickets/239_PLAN-11B__contracts-for-11b-and-transp-family.md`, context C13) — PASS

- Dispatch record: 2026-10-06T12:06:16Z (`date -u`, orchestrator, immediately before dispatch)
- Nonce sha256: `07aba7ea96be73db4762ac69111cda4d7094045a9ad81d8cf6754638641120b2`
- Revealed nonce (after the sub-agent reported): `352372824d7462baf7b92fae19c5d637` — hash verified by
  the orchestrator at 2026-10-06T14:52Z
- Control token: `P11BC13-CTL-182c7b5e`
- Sub-agent report (verbatim, from `docs/build/runs/PLAN-11B.md` § C13):

  >     P11BC13-CTL-182c7b5e
  >     Tue Oct  6 12:07:26 UTC 2026
  >     /Users/stevenvitali/Eleutheria
  >     r11/PLAN-11B-contracts-for-11b-and-transp-family
  >      M docs/tickets/REQUIREMENT_INDEX_R11.md

  with `Context model: devin-desktop/swe-2-high/subagent` recorded in the same section.

- Verdict: **PASS** — control token echoed exactly; sub-agent start `2026-10-06T12:07:26Z` later than
  the `2026-10-06T12:06:16Z` dispatch record; harness/model recorded; the nonce appears nowhere in the
  sub-agent's output or the tree (grep clean at reveal).
- Note: the sub-agent's verbatim block omitted the explicit "initial context sources" and
  "32-hexadecimal-character tokens held" fields the P34.3 record carried — the dispatch prompt asked
  for both; recorded here, not smoothed. The pass judgement stands on the control echo, the absent
  nonce (grep over the whole tree at reveal: no hit outside this file), the later start, and the
  recorded model.
