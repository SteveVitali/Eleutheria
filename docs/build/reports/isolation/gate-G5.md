# Isolation probe — GATE-G5 sitting (plan §8.5, repeated at the gate)

- performed: 2026-10-25T07:58Z by the orchestrator (devin-desktop/swe-2-high/subagent)
- control token echoed in-session: yes ("CONTROL-TOKEN-ECHO" returned verbatim)
- nonce `G5PROBE-1792914993-01be80e3094a` (sha256 `55a76010fda4387c…` of
  `nonce\n`): generated in-shell, absent from `docs/build/` at probe time
  (grep -rl empty), revealed only after the absence check — PASS
- verdict: PASS — no cross-session bleed detected at the GATE-G5 boundary
