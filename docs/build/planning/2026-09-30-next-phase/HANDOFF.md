# HANDOFF — Round 11: from the Stage-B seed (Claude Code) to the chain (Devin Desktop, row 201)

> Written by Stage-B unit SEED-18b (plan Appendix A **T6**, fourth bullet; plan §8.5, §11, §12) at 2026-10-01T17:47:53Z (`date -u`),
> harness `claude-code/claude-opus-5-5/subagent`, on `r11/seed` at HEAD `03effc4d` + this unit's files. `PD` =
> `docs/build/planning/2026-09-30-next-phase/`. Binding rules live in `docs/build/reports/OPERATING_MODE_R11.md` (the
> LEDGER head carries their one-line form); this file is the operator's and the executor's start-up sheet and adds no
> rule. Where it and the OPERATING MODE disagree, the OPERATING MODE wins and the executor stops and asks (OM-18).
> *Agent design where the plan is silent is labelled "agent design".* Nothing here was run in Devin Desktop: this unit
> runs in Claude Code and cannot drive Devin Desktop, so every Devin-side check is an **operator-run check** (§4).

## 0. What has to happen before row 201, in order

| # | step | who | state at this writing |
|---|---|---|---|
| 1 | Commit SEED-18b (this file, `stageB/GATEB_PACKET.md`, `stageB/PREPUSH_SCAN.md`, `baseline/DELTA_T6.md`, `docs/build/runs/SEED-18b.md`, the regenerated `docs/build/reports/current/`) | planning orchestrator | pending |
| 2 | Decide the pre-push scan items (`stageB/PREPUSH_SCAN.md` § Verdict: the Part VIII layer pointers and the handle occurrences) | orchestrator + operator (packet Q-1, Q-2) | open |
| 3 | **OP-05** — GitHub stack ruleset (H2 S-2: `refs/heads/r11/**`, `non_fast_forward` + `deletion`, no bypass) and merge settings (S-3: squash and rebase merges off) | operator | **not applied** (read 2026-10-01T17:28Z: no "stack" ruleset; squash/rebase still allowed — `baseline/DELTA_T6.md` § D6) |
| 4 | **OP-23** — refresh the private git bundle after the last seed commit, store it off-disk: `git -C /Users/stevenvitali/Eleutheria-next-phase bundle create ~/SIG-planning-backup-<date -u +%Y%m%dT%H%MZ>.bundle r11/seed claude/next-phase-planning && git bundle verify <that file>` | orchestrator makes it; operator stores it | the 05:03Z bundle exists; refresh owed |
| 5 | Push `r11/seed`; open the **seed PR** (base `devin/p33-8-agent-docs-refresh`, #190's head `b051732c`); **5/5 green on its head** (`python`, `docs`, `composed`, `security`, `web`) | orchestrator (push uses the operator's account) | pending |
| 6 | **Operator-run checks** in Devin Desktop, incl. the throwaway isolation probe (§4–§5) | operator | pending |
| 7 | **GATE-B** answered (`stageB/GATEB_PACKET.md`) | operator | pending |
| 8 | **C10:** GATE DECISIONS row for GATE-B verbatim; a PHASE LOG `gate` (or `pause`) entry naming GATE-B, dated no later than that row; then the `harness-switch` entry (draft: `docs/build/runs/SEED-17.md` § Draft); CURRENT STATE `projectStatus: IN_PROGRESS`, `pauseRequested: false`, `updatedAt`; `current_projection.py generate` | planning orchestrator | pending |
| 9 | **OP-07** (`SIG_GCP_PROJECT` Actions variable, billing/plan check, usage alert) and **OP-24** (leg-runner schedule, §6) | operator | not applied (0 Actions variables) |
| 10 | Start ONE Devin Desktop session with the resume prompt (§2) | operator | — |

## 1. Where the chain resumes

- **Worktree:** `/Users/stevenvitali/Eleutheria-next-phase` — the LEDGER's `buildWorktree` (its comment "T6 confirms"):
  confirmed at T6 — the directory exists, is a worktree of the SIG repository, has `r11/seed` checked out and was clean at
  `03effc4d` before this unit wrote its files. The main checkout `/Users/stevenvitali/Eleutheria` stays on
  `devin/p33-8-agent-docs-refresh` and is not the build worktree.
- **Branch:** `r11/seed` is the `chainTip`. Row 201 branches from it as `r11/P34.1-toolchain-pin-and-ci-hygiene`, PR base
  = `r11/seed` (H2 PR-1: each PR's base is the previous ticket's branch). One ticket, one branch, one PR; agents never
  merge, retarget, rebase, force-push, tag or push `main`, and never push to a branch once a successor exists (plan §12).
- **First row:** **201 = P34.1 TC-PIN** — `docs/tickets/201_P34.1__toolchain-pin-and-ci-hygiene.md`
  (`implement-spec spec=docs/tickets/201_P34.1__toolchain-pin-and-ci-hygiene.md live_verification=false`). It must **land
  before 2026-10-19T00:00Z** (`ubuntu-latest` → Ubuntu 26). It carries the dispatch isolation check (§5).
- **Harness string:** `devin-desktop/swe-2-high/subagent` — CURRENT STATE `harness:`, every contract's and run ledger's
  `Harness:` line; no separate `model:` key. Run ledgers also carry `Skills: <git -C ~/agent-skills rev-parse --short
  HEAD>` (`8aeb6dc` at this writing, build-memory release 0.5.0).
- **Operating rules:** `docs/build/reports/OPERATING_MODE_R11.md` (full text; §1 dispatch, isolation, fallback, chain
  lock · §2 orient and sizing · §3 OM-01…OM-20 verbatim · §4 skill rules · §5 pauses and gates · §9 live legs).

## 2. The resume prompt (Devin Desktop, model `swe-2-high`; paste verbatim into ONE new session after step 8)

```text
You are the SIG Round-11 orchestrator: ONE Devin Desktop session, model swe-2-high (256k window), running the
orchestrate-build skill over the committed LEDGER. You dispatch each chain ticket to a FRESH sub-agent and never
implement a ticket in your own context. Harness string: devin-desktop/swe-2-high/subagent.

0. Start. Run `date -u +%FT%TZ`; every date you write comes from `date -u` at that moment (OM-04). If your model is not
   swe-2-high, or you cannot start sub-agents, write nothing, say which, and stop (OM-01).
   cd /Users/stevenvitali/Eleutheria-next-phase ; git status ; git rev-parse --abbrev-ref HEAD   (expect the branch the
   last ticket left checked out — r11/seed before row 201; a dirty tree is a finding: stop and ask).
   `gh auth status` must pass.
1. Orient (BM-ORIENT-01; ≤ 48 KiB in all; never read LEDGER, DEFERRALS or BUILD_INDEX whole):
   O1 sed -n '1,/^## OPEN FINDINGS/p' docs/build/LEDGER.md
   O3 awk '/^### RETURN PASS — current/{f=1;print;next} f&&/^#{2,3} /{exit} f' docs/build/LEDGER.md
   O4 python3 docs/build/tools/current_projection.py verify ; then read docs/build/reports/current/CURRENT.md
   O5 tail -n 3 docs/build/LEDGER.md
   O6 grep -F "_<nextTicket>__" docs/tickets/00_MANIFEST.md ; then the contract header (first ~16 lines)
   Then read docs/build/reports/OPERATING_MODE_R11.md §1, §2, §4 and §5 (the rules you apply at every boundary).
   Expect: projectStatus IN_PROGRESS, pauseRequested false, nextTicket P34.1, harness devin-desktop/swe-2-high/subagent,
   and a PHASE LOG harness-switch entry (claude-code → devin-desktop) as one of the last lines. If any differs: stop and ask.
2. Before every dispatch (OM-05, BM-CI-01):
   bash ~/.claude/skills/orchestrate-build/scripts/ci-boundary.sh --ledger docs/build/LEDGER.md --ticket <lastCompleted> --stack
   red, pending after the wait, or unknown → set blockedOn, leave nextTicket, stop. Before row 201 this reads the seed PR.
   Record `git merge-base --is-ancestor origin/main <chainTip>` (exit code) in the boundary record (COV-14).
   Run due live legs first (OPERATING_MODE §9); never present a GATE while an OM-19 leg is due.
3. Size the ticket (A-15; plan §8.5): re-measure the contract's Load list as UTF-8 bytes ÷ 3 and ÷ 4 (name the counter),
   ADD the skill-text share (implement-spec + self-review ≈ 17.5k tokens) and the contract's DEFERRALS allowance
   (16 KiB in the 11A contracts). The higher figure must be ≤ ~150k tokens loaded (256k window; a sub-agent cannot
   compact — a hard ceiling). Over the line → split at the named seam or by decompose-spec mode=extend; never squeeze.
   P34.7 runs as two sequential contexts (its contract).
4. Dispatch (round 25): hand the ticket to a fresh sub-agent with the contract's Run line
   (implement-spec spec=<contract> live_verification=<as the contract says>). Record harness + model per ticket.
   Row 201 (P34.1) carries the isolation check: generate the nonce and control token exactly as
   OPERATING_MODE_R11.md §1 "Isolation check" says (nonce: `openssl rand -hex 16`, only its sha256 recorded; never in a
   file, env var, git, the prompt or Devin Knowledge/memory); put the control token in the dispatch prompt; judge the
   sub-agent's report (pass = control token echoed, nonce absent, its `date -u` start later than your dispatch record,
   harness/model recorded); reveal the nonce in the record. Repeat a cheap probe at each sub-round GATE and after any
   restart of this session. On failure: blockedOn "isolation check failed at <row>", stop dispatching, digest, and tell
   the operator to take the fallback in PD/HANDOFF.md §3.
5. After the sub-agent returns: verify its closeout (run ledger with Harness/Skills/Started/Closed from date -u, PR open,
   BUILD_INDEX row, PHASE LOG entry, CURRENT STATE advanced), then
   bash scripts/docs/check-build-memory.sh . --range <chainTip before>..<chainTip after>
   python3 docs/build/tools/memory_guard.py all --worktree
   and the head-bound CI read of its PR (step 2). Exit 1, 3 or 5 is red. A different harness or model in its records →
   stop and ask.
6. Pause only where OPERATING_MODE §5 says (HG gates, ING-GO, spend > $300/mo, red CI, a production mutation not on a
   live OM-20 pre-authorization row, gate markers GATE-G4/G5/G6/ACCEPT-R11/ANNOUNCE, a usage-limit event, the OM-18
   stop-and-ask list). Silence is never consent. At every pause, at session end, once per wave and at a usage-limit
   event write the digest (PD/HANDOFF.md §7). Release the chain lock (docs/build/LEDGER.md.drive-lock) at every pause,
   stop and session end; never break a lock you did not take.
7. Never: merge, retarget, rebase, force-push, tag or push main; flip a source's ingestion_permitted; tick a human gate;
   sign for the operator; contact anyone; write a secret to a file; edit a protected record above its end.
When this session's context fills, finish the current boundary, write the digest, release the lock and tell the
operator to start a new session with this same prompt (you hold no state the LEDGER does not).
```

PD in that prompt means `docs/build/planning/2026-09-30-next-phase/`. The prompt adds no rule: every step restates
OPERATING_MODE_R11.md §1–§5 or plan §8.5/§12, so the OPERATING MODE governs if they ever drift.

## 3. Dispatch modes and the fallback order (round 25; round 27 SB-3)

| mode | how | harness string (agent design for the fallbacks, labelled) | when |
|---|---|---|---|
| **A — orchestrator + fresh sub-agents (primary)** | §2's prompt in one Devin Desktop session; a fresh sub-agent per ticket | `devin-desktop/swe-2-high/subagent`; `dispatchTarget: subagent` | from row 201, while every isolation check passes |
| **B — headless Devin command (fallback 1)** | `bash ~/.claude/skills/orchestrate-build/scripts/drive-build.sh --ledger docs/build/LEDGER.md --agent-cmd "<verified command>"` — the command must take the prompt as a **trailing positional argument**, run non-interactively with `swe-2-high`, write without prompting, and exit when the unit is done; with `--agent-cmd` you own the autonomy posture | e.g. `devin-cli/swe-2-high/headless` (record the exact string) | only if a command was **verified** (§4 check f) — **T6 status: not verified** (below) |
| **C — manual tier (fallback 2)** | `bash ~/.claude/skills/orchestrate-build/scripts/drive-build.sh --ledger docs/build/LEDGER.md --print-prompt` → paste the printed prompt into **ONE new** Devin Desktop `swe-2-high` session; when that unit closes, re-run the command for the next one | `devin-desktop/swe-2-high/manual`; `dispatchTarget: manual` | when A fails and B is unverified or also fails |

- **Operator's words.** Round 25 (2026-10-01T06:14:06Z): *"Orchestrator + sub-agents (Recommended)"*. Round 27 SB-3
  (2026-10-01T13:46:58Z), asked "approve a non-interactive Devin command (via `drive-build --agent-cmd`) as a fallback
  before the manual tier": *"Approve headless fallback (Recommended)"* — so the GATE-B packet no longer needs to ask
  S6R-16's question; it is answered and recorded (GATE DECISIONS row of round 27).
- **When to switch (plan §8.5; OPERATING_MODE §1).** A failed isolation check — at the T6 probe (§5), at P34.1, or at a
  later repeat (each sub-round GATE, every orchestrator restart); or Devin Desktop exposing no sub-agent primitive
  (§4 check c). The orchestrator pauses (`blockedOn: isolation check failed at <row>`), writes the digest (`--trigger
  block`) and asks; the operator takes B if verified, else C. The tier taken is recorded in a PHASE LOG entry with the
  failed check's record; a harness change goes through the same entry (OM-01; SB-3 is the authority). *(Agent design:)*
  going back to A needs a passing probe and the operator's words — never automatic.
- **Preconditions for B and C:** `gh auth status` passes; `cd /Users/stevenvitali/Eleutheria-next-phase` with the
  branch the previous ticket left checked out (plan §12); `projectStatus: IN_PROGRESS` and `pauseRequested: false`
  (otherwise `drive-build.sh` exits 0 as "paused" and prints nothing to dispatch); its CI gate green (it runs
  `ci-boundary.sh` itself and exits 2 on red/pending/unknown). It takes the single-driver lock
  `docs/build/LEDGER.md.drive-lock` itself.
- **Cost of C (inference, plan §8.5/§11.2):** ≈ 300 operator-started sessions — open a session, paste the
  `--print-prompt` output, confirm the close, ≈ 3–5 min each — **≈ 15–25 h** of operator time on top of plan §11.2's
  ≈ 27–49 h.
- **T6 status of the headless command (B).** Not verified. In this unit's shell (2026-10-01T17:2xZ) there is **no
  `devin` executable on `PATH`** (bash, and a login `zsh -lc`), nor in `/opt/homebrew/bin` or `~/.local/bin`; the Devin
  CLI's data directory `~/.local/share/devin/cli/` exists (a session store and logs, so a CLI has run on this machine —
  plan §8.5 records Devin CLI reading `~/.claude/skills` at 2026-10-01T04:16:29Z); `/Applications/Devin.app/Contents/
  Resources/app/bin/devin-desktop` is the desktop editor's launcher (a VS Code-style CLI), not a headless agent runner.
  So B is usable only after the operator finds and verifies a command (§4 f) and the HANDOFF or a PHASE LOG entry records
  it; until then the fallback is C.

## 4. Operator-run checks before row 201 (plan Appendix A T6 third bullet; R-30)

Run them in Devin Desktop with the dry-run prompt below (read-only; it dispatches no chain row), then put the results in
the GATE-B answer (packet Q-7). If **a, b, c or the probe** fails, the chain does not start in mode A: the orchestrator
pauses before row 201 and the operator chooses B (if f passed) or C.

| # | check | pass | if it fails |
|---|---|---|---|
| a | **Orient dry-run** resolves row 201 | O1–O6 (§2 step 1) print `nextTicket: P34.1` and the manifest line `201_P34.1__toolchain-pin-and-ci-hygiene.md`; `current_projection.py verify` OK | stop; report the mismatch |
| b | **Skills load from `~/.claude/skills`** | the session names `orchestrate-build`, `implement-spec`, `build-memory`, `self-review` as available skills and quotes `~/.claude/skills/orchestrate-build/SKILL.md`'s `name:` line; `git -C ~/agent-skills rev-parse --short HEAD` = `8aeb6dc` | the orchestrator appends a dated `## Amendment — <date -u>` to `docs/build/reports/OPERATING_MODE_R11.md` carrying the B6 §5.3 overrides (`PD/research/B6-skill-proposals.md` § 5.3) and the hand-applied Tier A/B-must template content; the GATE-B record says so |
| c | **Sub-agent primitive** (`dispatchTarget: subagent`) exists | the session can start a sub-agent with its own fresh context and receive its final report | mode A is impossible → B or C |
| — | **Throwaway isolation probe** (§5) | pass as defined there | B or C |
| d | **A sub-agent cannot compact** (plan §8.5 inference) | Devin Desktop's documentation or the probe sub-agent's own report says whether a sub-agent context compacts or summarises; record the answer | if it *can* compact, record it — the ≤ ~150k loaded rule still binds |
| e | **Co-author trailer** Devin Desktop writes | in a throwaway clone (`git clone --shared /Users/stevenvitali/Eleutheria-next-phase /tmp/sig-trailer-probe`, never pushed) one commit made by the session passes `python3 docs/build/tools/check_trailers.py --range HEAD~1..HEAD` run in that clone (a Devin co-author line without a model passes with a warning — SEED-02b) | P34.1's contract records the trailer the executor must add by hand (OM-01 grammar) |
| f | **Headless command** for mode B | a command that runs one prompt non-interactively with `swe-2-high`, takes the prompt as a trailing argument and exits; record it verbatim | mode B unavailable; fallback = C |
| g | **Scheduled sessions** for OP-24 | Devin Desktop can schedule a session (every 6 h + one-offs) | OP-24 runs in Devin CLI headless with the same model (`LEG_RUNNER_PROMPT.md`) |
| h | **`gh auth status`** | logged in, scopes include `repo`, `workflow` | fix before any mode |
| i | **Model and window** | the session reports `swe-2-high` with a 256k window | stop: a different model is a harness change |

Dry-run prompt (paste into a new Devin Desktop session; it changes nothing):

```text
Read-only dry run for the SIG Round-11 hand-off. Do not edit, commit, push, or dispatch any chain ticket.
Run `date -u +%FT%TZ` first and report it. Report your model and context window.
cd /Users/stevenvitali/Eleutheria-next-phase ; git status ; git rev-parse --abbrev-ref HEAD ; gh auth status
Orient: sed -n '1,/^## OPEN FINDINGS/p' docs/build/LEDGER.md ; tail -n 3 docs/build/LEDGER.md ;
python3 docs/build/tools/current_projection.py verify ; grep -F "_P34.1__" docs/tickets/00_MANIFEST.md
Report: nextTicket, projectStatus, harness, and the manifest line for row 201.
List the skills you have loaded and where you read them from; print the `name:` line of
~/.claude/skills/orchestrate-build/SKILL.md and `git -C ~/agent-skills rev-parse --short HEAD`.
Say whether you can start a sub-agent with a fresh context, whether a sub-agent's context can compact or summarise,
whether this app can run scheduled sessions, and whether a non-interactive (headless) Devin command exists on this
machine (give its exact form). Then run the throwaway isolation probe in PD/HANDOFF.md §5 exactly as written
(PD = docs/build/planning/2026-09-30-next-phase) and report its record.
```

## 5. The throwaway isolation probe (plan §8.5 (1); S6R-13; run before row 201)

The orchestrator session (the dry-run session of §4 is fine) does, in order:

1. `date -u +%FT%TZ` → the dispatch-record time. `openssl rand -hex 16` → the **nonce**, held only in this session's
   context; record **only** `printf %s <nonce> | shasum -a 256`. Never write the nonce to a file, an environment variable,
   git, the probe prompt or Devin's Knowledge/memory.
2. A **control token** that is not 32-hex (agent design, so it cannot be confused with the nonce class): `PROBE-CTL-`
   followed by `openssl rand -hex 4`. It goes into the probe prompt.
3. Start one fresh sub-agent with exactly this prompt (fill the token):

   ```text
   Isolation probe for the SIG Round-11 hand-off. Change nothing: no file edits, no git, no network.
   1. Run `date -u +%FT%TZ` and report it as your start time.
   2. Echo this control token exactly: <CONTROL TOKEN>
   3. List your initial context sources: the prompts, files, memories or Knowledge entries present when you started.
   4. List every 32-hexadecimal-character string present in your context, or write "none". Do not search for one.
   5. Report your harness and model.
   ```
4. **Pass** = the control token echoed exactly, the nonce absent from the report, a start time later than step 1's
   record, harness/model reported. Then reveal the nonce in the record (its sha256 verifies) and keep the sub-agent's
   report verbatim.
5. **Record** *(agent design, labelled — the plan fixes the content, not the place):* the operator pastes the record
   (dispatch time, nonce sha256, revealed nonce, control token, the verbatim report, pass/fail) into the GATE-B answer;
   C10 keeps it as `docs/build/reports/isolation/probe-T6.md` and cites it in the GATE-B PHASE LOG entry. P34.1's repeat
   follows its contract § Dispatch isolation check.

## 6. Leg-runner backstop (OM-19; OP-24)

- Prompt and scheduling notes: `PD/stageB/LEG_RUNNER_PROMPT.md` (paste the fenced prompt verbatim as the scheduled
  session's task).
- **Where:** Devin Desktop if check g passes; otherwise Devin CLI headless, same model. Record the harness string the
  session uses — `devin-desktop/swe-2-high/headless` or `devin-cli/swe-2-high/headless` — in the GATE-B answer; the first
  leg-runner session writes it in its run-ledger entry. **T6 could not determine which** (check g).
- **When:** at each live window's opening and close and every 6 h inside a window; *agent suggestion (in the prompt
  file):* one schedule every 6 h plus one-off runs at the window edges each wave digest names.
- **Lock:** it takes `docs/build/LEDGER.md.drive-lock` before any leg and never breaks a lock it did not take.
- **Alerts until P34.4 lands** *(agent design, labelled; packet Q-6):* a digest entry
  (`digest.sh … --trigger block --write`) plus the session's final message; P34.4's alert channel replaces it once landed.
- Working directory = `buildWorktree`; `gh auth status` and, for hosted legs, the operator's `gcloud` credentials as the
  chain uses them; no secret in the prompt or a file.

## 7. The digest command (BM-DIGEST-01; A-2, A-15)

```bash
bash ~/.claude/skills/orchestrate-build/scripts/digest.sh --ledger docs/build/LEDGER.md \
  --trigger <wave|pause|session-end|usage-limit|block|gate> --write \
  --spend "<infra spend vs the \$300/mo ceiling + source; 'inference' until P34.5 measures it>" \
  --usage "<runs; median/max per run; cumulative; projection; usage-limit events | not measured>"
```

Once per wave (each `### Round 11` manifest banner), at every pause, at session end and at every usage-limit event. It
appends to `docs/build/reports/digests/<date -u +%F>.md`. If a secret value appeared in a transcript: add `--exposed yes`
(exit 3) and stop for rotation; the value is never written.

## 8. The operator's prerequisites and due points (manifest § Human prerequisites, Round 11)

| OP | action | due |
|---|---|---|
| OP-01…OP-04 | review the live skill releases (0.3.0 → 0.5.0, `~/agent-skills` `8aeb6dc`) applied by agents at T0/T0b/T0c | before row 201 |
| **OP-05** | stack ruleset (S-2) + merge settings (S-3) | **before the T6 push** — not applied at 17:28Z |
| OP-06 | `main` ruleset with the five required checks (S-1) | after OP-08 |
| **OP-07** | Actions variable `SIG_GCP_PROJECT` (S-4), billing/plan check + usage alert (S-5), optional action restrictions (S-7) | **before row 201** — 0 variables at 17:28Z |
| OP-08 | bottom-up merge sitting #155–#190 (+ `v0.1.0` tag) — a safety item (public `main` keeps the false governance text and repo-tip handle strings until merged) | any time; before OP-06. **Now: one BUILD_INDEX conflict at #180 and an ACCEPT-R10 decision** (`baseline/DELTA_T6.md` § D1–D2; packet Q-9) |
| OP-09 / OP-10 | move the DNS zone to Cloudflare (P34.50 runbook); then the `contact@` alias | by GATE-G4 |
| OP-12 | cost approvals and billing-admin steps (P34.5) | early 11A |
| OP-13 | US 511 + QLDTraffic + NSW keys in Secret Manager (after OP-10) | by GATE-G6 |
| OP-19 | Zenodo production deposit | after P37.55 |
| OP-20 | release-signing key (minisign) in Secret Manager | by GATE-G5 |
| OP-22 | walkthroughs and sign-offs (copy batch #1 ≈ 10-08 → 10-10; journeys at P37.68a–d; gallery before P38.5) — recorded "operator walkthrough (maintainer, not independent)" | recurring |
| **OP-23** | store the refreshed git bundle privately, off-disk | **before the T6 push** |
| **OP-24** | schedule the leg-runner (§6) | **before row 201** |
| **OP-25** | gate-signing SSH key (passphrase- or hardware-backed, never in an agent-reachable ssh-agent); public key → `docs/build/tools/record_policy/allowed_signers` (P34.28) | **by GATE-B if possible**; at the latest before GATE-G4 |
| OP-26 | HG-03 flips per wave (agent patch on `r11/<wave>-flips`; operator-signed commit or row) | Waves A/B at GATE-G4; C at GATE-G5; D at GATE-G6; A-18 inside P35.17 |

Also early 11A: in-ticket gos for P34.18, P34.24a, P34.44a and P34.21b's bucket-access step; P34.40's `/v1/*` step needs
its own go (packet Q-4); P34.46's schema slot needs the operator present (2026-10-14/15, 14:00–20:00Z). HG-05 is an
operator-owned integration disposition (manifest), not a deferral.

## 9. After the round: REVIEW-R11

A deep, read-only review by **Claude Code (Opus 5.5, xhigh effort)** after the final release and P38.4, before
GATE-ANNOUNCE (A-15 round 7, 2026-10-01T04:21:56Z: *"How about Devin for everything and Claude Code can do a deep review
after the entire thing, …"*). Output: a findings register (S0–S3 with evidence classes) and a next-round planning input.
**GATE-ANNOUNCE waits on it:** each S0/S1 finding is fixed — by fix rows appended after row 510 with GATE-ANNOUNCE
re-anchored after them (row 510 gets `superseded-by(row <n>)`) — or dispositioned by the operator (S6-F3, round 24,
2026-10-01T06:05:22Z, *"S0/S1 must be dispositioned (Recommended)"*). S2/S3 findings feed the next round. It is not a
manifest row and not operator work; ≈ 8–12 contexts sized by its own meta-plan (plan §13.4).

## 10. Notes the executor needs (Stage-B carry, `PD/stageB/CARRY.md`)

- **Windows and named mutations (SEED-13b):** where row text and plan §8.4/§10.2 disagreed, the contracts took the
  stricter window (P34.3, P34.4, P34.6); P34.13's `/terms` redirect ships only with notice N-7; P34.4's
  `gh workflow disable reingest.yml` is a named mutation (reingest still fails daily — `baseline/DELTA_T6.md` § D4).
- **P34.1** owns the docs-job push trigger and the `--first-parent` step (TODO in `ci.yml`); **P34.28/OP-25** commit
  `docs/build/tools/record_policy/allowed_signers` (SEED-02b).
- **History replay (SEED-02b):** a `--first-parent` replay of single seed commits flags 125 seed-ADR edits (expected);
  the seed is judged as one range `b051732c..r11/seed` (passes) — say so in the seed PR body.
- **GATE-M (SEED-17):** its G4a-pause warning cannot be cleared honestly; no future PHASE LOG entry containing "pause"
  may name GATE-M.
- **WV-01 vs C-5 (SEED-11b):** the legal-home disclosure must not name the operator or describe them beyond the adopted
  WV-01 sentence until they write the About text (C-5, *"Omit until I write it"*).
- **Sizing heuristics (SEED-13e):** decompose-spec's ≈ 128k whole-working-set heuristic vs the plan's ≤ ~150k loaded rule —
  the tradeoff is recorded in the manifest's Decomposition decisions; the plan's rule binds dispatch.
- **ACCEPT-R10 and the merge sitting (this unit):** `baseline/DELTA_T6.md` § D1–D2 — #185's head now restores ACCEPT-R10
  to PENDING (`4a2ce75d`), the seed annotates the SIGNED text; the remaining sitting conflicts once (BUILD_INDEX at #180)
  and the seed PR's later merge conflicts in `docs/build/readouts/ACCEPT-R10.md`. Agents do not resolve it (agents never
  merge); the operator decides (packet Q-9).
- **Projection:** regenerate `docs/build/reports/current/` with `current_projection.py generate` at every closeout; it is
  an input-hashed view, so any later edit to an input (LEDGER, DEFERRALS, manifest, tickets, ADRs, run ledgers) makes
  `verify` STALE until regenerated.

## 11. Pointers

- Plan (canonical): `PD/NEXT_PHASE_PLAN.md` — §3.3 OM clauses, §8.5 sizing/dispatch, §11 human work, §12 branch policy,
  §13.4 REVIEW-R11, Appendix A T6.
- Planning ledger: `PD/META_PLAN.md` (§3 principles, §9 clock rule, §11 change log).
- Operator's words: `PD/feedback/RATIFICATION_LOG.md` (rounds 1–27); earlier: `PD/feedback/OPERATOR_FEEDBACK.md`.
- Stage-B carry: `PD/stageB/CARRY.md`; T0c contract: `PD/stageB/T0c_sync_obligations.md`.
- This unit: `PD/stageB/GATEB_PACKET.md`, `PD/stageB/PREPUSH_SCAN.md`, `PD/baseline/DELTA_T6.md`,
  `docs/build/runs/SEED-18b.md`.
- Rules: `docs/build/reports/OPERATING_MODE_R11.md`; leg-runner: `PD/stageB/LEG_RUNNER_PROMPT.md`; C10 draft:
  `docs/build/runs/SEED-17.md` § Draft.
- Machine state: `docs/build/LEDGER.md` (head + CURRENT STATE), manifest `docs/tickets/00_MANIFEST.md`, register
  `docs/tickets/DEFERRALS.md`.

## Merge-sitting guidance (GATE-B packet Q-10; recorded 2026-10-01T18:11:04Z)

Merging #180 now conflicts once in `docs/build/BUILD_INDEX.md` (row 183: `b01ef231` on #179 vs the stack's later text): take the **stack's side** at #180; the simulation then runs clean to #190 and differs from #190 only in `docs/build/readouts/ACCEPT-R10.md`. At the seed PR's merge, resolve `ACCEPT-R10.md` to the **seed's text** (GB-Q9 (ii) *"Keep the chain's record (Recommended)"*). Agents never merge.

## GATE-B record (C10, 2026-10-01T18:45:15Z)

- **GATE-B: "Go (Recommended)"** — recorded in GATE DECISIONS `### Round 11` and RATIFICATION_LOG. Seed PR #192 5/5 green
  at `d8ea72ef` before C10 (one B-15 flake re-run of `web`).
- Devin Desktop dry-run + isolation probe: **PASS** (`docs/build/reports/isolation/probe-T6.md`). Correction to §3/§4: a
  `devin` binary exists at `/Applications/Devin.app/Contents/Resources/app/extensions/windsurf/devin/bin/devin` but is not
  logged in, so mode B is unverified (manual tier is the fallback until `devin auth login` + verification).
- OP-24 deferred to GATE-G4. CURRENT STATE: `projectStatus: IN_PROGRESS`, `pauseRequested: false`, `nextTicket: P34.1`,
  `harness: devin-desktop/swe-2-high/subagent`. The PHASE LOG ends with the GATE-B gate entry and the C10 harness-switch.
- **To start Round 11:** open one new Devin Desktop session (model `swe-2-high`) in `/Users/stevenvitali/Eleutheria-next-phase`
  on branch `r11/seed` and paste §2's resume prompt verbatim.
