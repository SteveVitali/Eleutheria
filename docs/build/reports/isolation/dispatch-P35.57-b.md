# Dispatch isolation record — P35.57 (row 261), probe 2

- **Supersedes:** dispatch-P35.57.md (probe 1, recorded 19:59Z) — its raw nonce was held only in the orchestrator's pre-restart session state and is unrecoverable after the session interruption during the Docker Hub CI incident; a fresh probe is issued rather than a verdict recorded on a nonce the orchestrator can no longer check. Probe 1's control token never entered a prompt; no worker ran under it.
- **Dispatched at:** 2026-10-09T22:10Z (date -u) by the devin-desktop/swe-2-high orchestrator, fresh sub-agent (post-GATE-G4 restart probe, plan §8.5).
- **Branch/base:** stacks on r11/P34.47-sub-round-11a-acceptance (tip 825eaf04 at dispatch).
- **Control token (in prompt):** P3557-CTL-076941c7
- **Nonce (never in prompt, never written to the tree):** sha256 747a8c194c05af84194f0e602bc1266e01015b3e6b50c3022fcbc6bb22332906 — the raw nonce is held by the orchestrator only; the worker cannot echo it.
- **Judgement:** pending — recorded at P35.57's close (token echoed in the worker's isolation block; nonce absent from the tree).

## Verdict

- **Nonce reveal:** 57d0b6bff6133e7a359aa8861c59a55d (SHA-256 747a8c194c05af84194f0e602bc1266e01015b3e6b50c3022fcbc6bb22332906 — matches the pre-dispatch hash).
- **Report location:** docs/build/runs/P35.57.md "Isolation data" — control token echoed exactly (appended at 5c7bdc54 after the closeout initially omitted the positive-control fields; the resumed session still held the prompt's token, which is the probe's point).
- **Verdict: PASS** — token P3557-CTL-076941c7 echoed exactly; 32-hex token held: No; harness devin-desktop/swe-2-high/subagent recorded; nonce absent from the tree (git grep clean at reveal, 2026-10-10T01:58Z).
