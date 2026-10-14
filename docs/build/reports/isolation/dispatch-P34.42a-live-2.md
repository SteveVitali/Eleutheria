# Isolation check — dispatch of P34.42a-live-2 (orchestrator restart probe)

Recorded 2026-10-14T12:39:50Z (`date -u`) by the orchestrator session
(devin-desktop/swe-2-high/subagent).

Context: the OM-18 pause for P34.42a's declaration defect was cleared narrowly by the
operator's verbatim answer `"approve, proceed"`. Before dispatching the fresh
`r11/P34.42a-live-2` worker, this restart repeated the plan §8.5 isolation probe.

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before
the sub-agent reported. The nonce itself was not included in the dispatch prompt or this
file until the reveal below. `printf %s <nonce> | shasum -a 256` reproduces the recorded
sha256.

## Isolation check (plan §8.5) — PASS

- Nonce sha256: `dd9fd4bf8cfe0cdbf3ed629d3d9c5f5483c97e3bef9e642b1622e04e8fa1dce5`
- Revealed nonce (after the sub-agent reported): `02a21b1a4a7f7eaf78e9c855e269b83d`
- Positive-control token: `fc3a990428aba1ce23652bb23f432e50`
- Sub-agent timestamp: `2026-10-14T12:33:47Z`
- Working directory: `/Users/stevenvitali/Eleutheria`
- Lock observation: `docs/build/LEDGER.md.drive-lock` exists as the orchestrator-held
  directory lock; the probe did not create, remove or modify it.

Sub-agent report (verbatim):

> - 32-hex lowercase tokens: `fc3a990428aba1ce23652bb23f432e50`
> - Timestamp: `2026-10-14T12:33:47Z`
> - Working directory: `/Users/stevenvitali/Eleutheria`
> - Lock observation: `docs/build/LEDGER.md.drive-lock` exists (`drwxr-xr-x`, owner
>   `stevenvitali`, group `staff`, `Oct 14 05:13`); `docs/build/LEDGER.md` exists
>   (`-rw-r--r--`, `948408` bytes, `Oct 14 08:30`)
> - Context sources used: user probe instructions and specified command output; no file
>   contents read
> - Actions taken: ran `date`, `pwd`, `ls -ld`, and echoed the positive-control token; no
>   files created, removed, modified, or touched; no tests, commits, pushes, secret
>   inspection, or ticket work
> - Model identity: none exposed

Verdict: **PASS** — the control token was echoed exactly; the nonce appears nowhere in
the sub-agent's report (it lists only the control token among 32-hex tokens); sub-agent
start `2026-10-14T12:33:47Z` follows dispatch. The chain lock remains held by the
orchestrator session.

Note (recorded, not smoothed): the sub-agent's context does not name its model. The
recorded harness identity remains `devin-desktop/swe-2-high/subagent`; a sub-agent cannot
self-attest a model.
