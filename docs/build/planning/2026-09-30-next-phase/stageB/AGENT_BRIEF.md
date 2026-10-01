# Stage B — common brief for every seed sub-agent

You are one fresh-context sub-agent of **Stage B** (translation of the ratified Round-11 plan into build artifacts) for SIG,
the Surveillance Infrastructure Graph. The planning orchestrator (Claude Code, Opus 5.5) dispatches you and commits your
output. Read this brief, then your unit prompt.

## Where
- Worktree: `/Users/stevenvitali/Eleutheria-next-phase`, branch **`r11/seed`** (cut from the planning head). `PD` =
  `docs/build/planning/2026-09-30-next-phase/`.
- Canonical plan: `PD/NEXT_PHASE_PLAN.md` (CANONICAL). **Appendix A** is the Stage-B checklist; your unit names its items.
  §6 = requirement changes, §7 = ADR list (numbers + author column), §3.3 = operating clauses OM-01…OM-20, §8 = ticket plan,
  §9 = obligation mapping. Data: `PD/data/round11_plan.csv` (authoritative rows), `PD/data/ticket_catalog.csv`,
  `PD/data/decision_catalog.csv` (`operator_answer`, `answered_at`).
- Operator words: `PD/feedback/RATIFICATION_LOG.md` (rounds 1–26, verbatim answers with `date -u` round headers, adopted
  sentences, labelled agent interpretations, closing deviation table, round-26 record clarification). Earlier feedback:
  `PD/feedback/OPERATOR_FEEDBACK.md`. Planning ledger: `PD/META_PLAN.md` (§3 principles P1–P16, §9 clock rule, §11 log).
- Design/research notes the plan cites live under `PD/design/`, `PD/research/`, `PD/reviews/`, `PD/baseline/`.
- Repo rules: root `AGENTS.md` and the nearest package `AGENTS.md` of any file you touch. Build-memory contract (skills,
  live): `~/.claude/skills/build-memory/layout.md` and its `templates/`.

## Hard rules
1. **Git:** never run a state-changing git command (`commit`, `add`, `rm`, `mv`, `checkout`, `switch`, `restore`, `stash`,
   `reset`, `rebase`, `merge`, `cherry-pick`, `clean`, `push`, `tag`, branch creation). Read-only git (`log`, `show`,
   `blame`, `diff`, `ls-files`, `rev-parse`) is fine. Other sub-agents are editing **other** files in this worktree at the
   same time — touch only the files your unit owns; if you must change a file outside your unit, stop and report it.
2. **Clock:** every date/time you write is produced by `date -u` inside the same shell command that writes it.
3. **Append-only records:** never rewrite landed ADR bodies, the risk register, traceability history, GATE DECISIONS rows,
   PHASE LOG entries, or DEFERRALS history — append dated entries that name what they correct (P2/P7, OM-13). Never edit
   `docs/2_canonical_design_spec.md` directly (edit `docs/research/_meta/spec_src/` and let `BUILD.sh` regenerate; the
   orchestrator runs the final build). Never hand-edit `ontology/generated`. Never re-stamp `db/sqitch.plan` L44–52 (C-10).
4. **Truth:** cite only what you read; no fabricated human work, approvals or verification; label agent interpretation;
   operator decisions carry the operator's adopted words verbatim with their round time from the log and, where the plan
   says so, a sha256 and the label "agent-drafted, adopted by the operator at <time>".
5. **Safety:** no secrets in files; no network; no production/GCP/`gh` mutations; never contact anyone; never flip a source's
   `ingestion_permitted`; never tick a human gate. The operator's personal e-mail address must not be added anywhere new.
   Refer to the operator as "the operator" (they/them).
6. **Run ledger:** write `docs/build/runs/<UNIT>.md` (e.g. `SEED-06.md`) in the shape of the newest existing run ledgers
   (`docs/build/runs/P33.8.md`) with header lines `Harness: claude-code/claude-opus-5-5/subagent`, `Skills: <git -C
   ~/agent-skills rev-parse --short HEAD>`, `Started:` / `Closed:` from `date -u`; list what you did, the checks you ran with
   their results, and open issues. (Units that share one prompt may share one ledger named in the prompt.)
7. **Checks:** run the checks your unit names; report failures honestly; do not loosen tests.

## Report back (concise)
Files written/changed · checks + results · anything you could not do or that another unit/the orchestrator must handle.
