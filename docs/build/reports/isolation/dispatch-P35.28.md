# Isolation check — resume dispatch of P35.28 (row 286; orchestrator restart probe)

Recorded 2026-10-14T04:04:24Z (`date -u`) by the orchestrator session (devin-desktop/swe-2-high/subagent).

Context: this is the restart probe for the interrupted P35.28 boundary. The resumed orchestrator found
CURRENT STATE `nextTicket` P35.28 / `chainTip` `r11/P36.11-…`, the ticket branch checked out with the
contract's uncommitted implementation, an open `docs/build/runs/P35.28.md`, and no surviving
`docs/build/LEDGER.md.drive-lock`; no other orchestrator/build process was found. The orchestrator took
the chain lock at 2026-10-14T04:01:03Z and appended the restart PHASE LOG note before this probe.

The nonce was generated with `openssl rand -hex 16`; only its sha256 was recorded before the sub-agent
reported — the nonce itself was never written to a file, an environment variable, git, the dispatch
prompt or persistent memory until the reveal below. `printf %s <nonce> | shasum -a 256` reproduces the
recorded sha256.

## Isolation check (plan §8.5, S6R-13) — PASS

- Dispatch record: the probe dispatch immediately preceded the sub-agent's recorded start
  (`2026-10-14T04:03:39Z`); no separate orchestrator `date -u` was captured at the dispatch call —
  recorded, not smoothed.
- Nonce sha256: `1b58606ce8413cfb31117ddda48260da7b40de9fb4ec253c04cfd99f3e449567`
- Revealed nonce (after the sub-agent reported): `c9b068f6e34b3601f6459afcc5f8e912` — hash verified by
  the orchestrator at 2026-10-14T04:04:24Z.
- First probe (read-only profile): control `33d4c2d2286a871acf3ca19bc145e356` echoed and no nonce held,
  but the profile exposed no shell so it could not produce `date -u`; repeated with a profile that can
  run the clock command.
- Second probe control token: `40317a76c7fd68651158a9ed0b36e5bc`
- Sub-agent report (verbatim):

  > **SIG Round-11 Isolation Probe — compact report**
  >
  > - **Probe timestamp (exact `date -u` output):** `2026-10-14T04:03:39Z`
  > - **Working dir:** `/Users/stevenvitali/Eleutheria`
  > - **Lock observation (read-only `ls`, not touched):** `docs/build/LEDGER.md.drive-lock` exists as a
  >   directory, mtime `Oct 14 00:01`; `docs/build/LEDGER.md` present (935,270 B, Oct 14 00:01). No
  >   create/remove/modify performed.
  >
  > **Context sources actually used:**
  > 1. The user prompt (probe rules + control token).
  > 2. Injected always-on rules: `/Users/stevenvitali/Eleutheria/AGENTS.md` (full SIG repo rules),
  >    `/Users/stevenvitali/Eleutheria/CLAUDE.md` (`@AGENTS.md` pointer),
  >    `/Users/stevenvitali/.codeium/windsurf/memories/global_rules.md` (empty body).
  > 3. System prompt identifying this as a Devin subagent session.
  > 4. Tool outputs: `date -u`, `pwd`, `ls -la docs/build/`.
  >
  > **Harness/model identity as exposed:** "a subagent of Devin, Cognition's agentic coding CLI" — no
  > model name/version exposed.
  >
  > **32-hex tokens held (complete list):**
  > - `40317a76c7fd68651158a9ed0b36e5bc` (positive control, echoed verbatim)
  >
  > **Actions taken:** 2 read-only shell commands (`date`, `pwd && ls`). No edits, no tests, no commits,
  > no pushes, no P35.28 work, no lock interaction.

- Verdict: **PASS** — the control token was echoed exactly; the nonce appears nowhere in the sub-agent's
  report (it lists only the control token among 32-hex tokens); sub-agent start `2026-10-14T04:03:39Z`
  follows the dispatch; initial context sources were reported. Chain lock
  `docs/build/LEDGER.md.drive-lock` is held by this orchestrator session.
- Note (recorded, not smoothed): the sub-agent's context does not name its model. The dispatch identity
  remains the orchestrator's recorded `devin-desktop/swe-2-high/subagent`; a sub-agent cannot self-attest
  a model.
