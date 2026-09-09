# ADR-073 — Build memory is committed under `docs/build/`; agent scratch is retired

- **Status:** Accepted
- **Ticket:** P22.3
- **Phase / ticket:** P22.3 — Build-memory v2 migration (retire `.agents/scratch/`; adopt the committed `docs/build/` layout)
- **Date:** 2026
- **Requirement ids:** SIG-ENG-001, SIG-ENG-003, SIG-ENG-031
- **Spec:** build-memory-v2-spec §§3–10 (the layout, ledger, deferrals, ADR, index, validator, compatibility contracts); this repo's `docs/2_canonical_design_spec.md` §47/§53.
- **Supersedes:** ADR-058 §3 (the "`.agents/scratch/` is the single gitignored scratch root, never committed" home for the machine ledger). ADR-058's other decisions — tickets committed under `docs/tickets/`, planning artifacts promoted to `docs/build/`, the `AGENTS.md` hierarchy — **stand**. ADR-058 is immutable and its body is **not** edited (SIG-ENG-003); the generated ADR index shows both records, and this ADR states precisely what it supersedes.

## Context

ADR-058 (P19.1) committed the tickets and promoted the durable planning artifacts to `docs/build/`, but
kept the live `orchestrate-build` **machine ledger** gitignored under `.agents/scratch/planning/` (§4.7,
"the single exception"). Two production builds (this repo: 65 tickets + a capstone; Rhēma: 22 ticket runs)
then hand-rolled the same missing structures around that gitignored ledger and both reversed the gitignore
rule in practice. Keeping the ledger in scratch has three concrete costs the `build-memory-v2` analysis
records: (a) a **sibling build worktree cannot see** the main worktree's scratch, so the `git-common-dir`
trick makes the ledger and the branch disagree; (b) the machine state — the record a fresh session resumes
from — is **not versioned with the chain tip** it describes; (c) "scratch" invites deletion (this repo lost
4.5 MB of logs; that is fine, but the ledger sat in the same "delete freely" tree).

`build-memory` v2 (SK.1, merged to `agent-skills` `main` `2c59325`) makes the committed `docs/build/` the
standard: one validated layout every build skill reads and writes the same way, opted in by the marker
`<!-- build-memory: v2 -->` in `docs/build/README.md`, with the machine state at `docs/build/LEDGER.md`,
per-ticket run ledgers at `docs/build/runs/<ID>.md`, and a `check-build-memory.sh` validator. Adopting it
here is a build-memory/layout decision, not a change to any product requirement or the canonical spec.

## Decision

1. **Commit the build's memory under `docs/build/` in the build-memory v2 layout.** The machine ledger moves
   from `.agents/scratch/planning/sig-postbuild-build-ledger.md` to the committed `docs/build/LEDGER.md`
   (CURRENT STATE with the BM-LEDGER-02 key set, GATE DECISIONS, RETURN PASS, PHASE LOG); run ledgers to
   `docs/build/runs/<ID>.md`; PR bodies to `docs/build/pr/<ID>.md`; the ADR index becomes generated
   (`docs/adr/README.md`); deferred obligations get a committed home at `docs/tickets/DEFERRALS.md`.
2. **Retire `.agents/scratch/`.** It is removed from the tree; the migration was **move/rename only**
   (contents byte-identical, verified by `sha256`/`cmp`, mapping recorded in `docs/build/README.md`); only
   regenerable logs were dropped. The `.gitignore` `scratch/` line stays (harmless) and gains
   `docs/build/logs/` — the one gitignored subtree that remains.
3. **The layout is validated, not conventional.** `scripts/docs/check-build-memory.sh .` (vendored from the
   `build-memory` skill, MIT) runs in `make docs-check` and gates the layout, the ticket sequence, the
   DEFERRALS ids, the ADR index ↔ files, the ledger key set, and the secret/size scans.
4. **Secrets never enter any ledger** (env vars only; ledgers record `provided: yes/no`), and committed run
   ledgers are scanned for private individuals' personal data before staging (Part VIII).

## Consequences

- A fresh session (or a sibling worktree) resumes from `docs/build/LEDGER.md` on its **own** chain tip; the
  ledger travels with the branch it describes. The `orchestrate-build`/`drive-build.sh` readers parse the
  committed ledger unchanged.
- The build's history (what was owed, decided, deferred, and verified) is now auditable in git rather than in
  a deletable scratch dir. The pre-v2 `docs/build/` project reports and the functional `okc/`, `live_runs/`,
  `rights/` subtrees were relocated under `docs/build/reports/` to satisfy the v2 root allowlist — **no code
  changed** (the only references are comments, `sources.toml` note strings, and env-gated tests).
- No product code, schema, or canonical-spec requirement changed; `make check` is unaffected. The one edited
  file is the machine ledger (three keys appended + the CURRENT STATE reshaped to the v2 key order); every
  other moved file is byte-identical.

## Alternatives considered

- **Keep the machine ledger gitignored (ADR-058 §3 status quo).** Rejected: the sibling-worktree defect and
  the "state not versioned with the tip" problem are exactly what `build-memory` v2 was written to fix; two
  builds already reversed the rule in practice.
- **Promote only selected artifacts, keep scratch.** Rejected: promotion is a second, error-prone step (this
  repo's post-hoc reconstruction cost a full ticket, P19.1); git is already the artifact store.
- **A committed `docs/build/scratch/`.** Rejected (spec D2): a committed directory of run ledgers is not
  "scratch", and the name invites the same delete-freely behaviour.

## Revisit trigger

Revisit if the committed build memory measurably slows the inner loop or bloats the repo beyond audit value
(e.g. a single run ledger or report exceeds the validator's 5 MB flag, or `docs/build/` growth dominates
clone size), or if `build-memory` upstream changes the layout contract in a way this repo's paths cannot
follow. At that point, either prune to `logs/`-style gitignored carve-outs (recording the change here) or
adopt the new upstream layout via a new ADR.
