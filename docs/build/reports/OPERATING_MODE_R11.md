# OPERATING MODE — Round 11 (full text)

> Written by SEED-17 (Round-11 Stage B, T5) at 2026-10-01T16:51:35Z (`date -u`) on branch `r11/seed`, harness
> `claude-code/claude-opus-5-5/subagent`. **Binding for chain rows 201–510 from GATE-B:** C10 records GATE-B in GATE
> DECISIONS, sets `projectStatus: IN_PROGRESS` and `pauseRequested: false`, and appends the `harness-switch` PHASE LOG
> entry; until then the seed is paused and no ticket is dispatched. The LEDGER head (`docs/build/LEDGER.md`,
> `OPERATING MODE — Round 11`) carries the one-line form of each rule and points here; the manifest's
> `## Operating rules (binding on every ticket)` restates the per-ticket subset. Where this file, the head and a
> ticket contract disagree, stop and ask (OM-18).
>
> **Sources.** Plan `docs/build/planning/2026-09-30-next-phase/NEXT_PHASE_PLAN.md` §3.3 (OM-01…OM-20, the S4c wording
> ratified at GATE-P, S5-1), §8.3, §8.5, §12 and Appendix A T5; the operator's answers, verbatim with their round time,
> from `docs/build/planning/2026-09-30-next-phase/feedback/RATIFICATION_LOG.md` (rounds 1–23 committed as `de0b3591`;
> rounds 24–27 appended later); the final skill contract (build-memory 0.5.0, skills commit `8aeb6dc`) as recorded in
> `docs/build/planning/2026-09-30-next-phase/stageB/T0c_sync_obligations.md`; H2 §7 and G2 §2 (design notes under
> `docs/build/planning/2026-09-30-next-phase/design/`); the Stage-B carry list `stageB/CARRY.md`. The decisions
> applied here are recorded in ADR-149 (Round-11 operating model), ADR-146 (dates), ADR-147 (gate records) and ADR-148
> (ledger contract). *Agent readings are labelled.* GATE DECISIONS `### Round 11` holds the operator's words this file
> relies on as rows.
>
> **Amendments.** Append a dated `## Amendment — <date -u>` section at the end of this file naming the operator's words
> or the record that authorises it; no line above it is edited (OM-13). A change of a rule's meaning is an operator
> decision (a GATE DECISIONS row), never an agent edit.
>
> **Supersedes** the Round-1 OPERATING MODE (recorded 2026-09-08) and the Round-10 import amendment (written
> 2026-09-27T02:40:53Z), both archived byte-for-byte in `docs/build/reports/memory-repair/LEDGER_head_R01-R10.txt`, and
> SEED-10's placeholder, archived in `docs/build/reports/memory-repair/LEDGER_head_placeholder_SEED-10.txt`. Their ledger
> path, commit-policy note, ticket count, resume condition and dispatch details no longer bind.

## 1. Who runs what (A-15, round 25, round 27)

- **Executor.** Devin Desktop with `swe-2-high` (256k window) runs every chain row 201–510. The operator's words:
  *"We will drive most of the execution with Devin Desktop using their new SWE-2 High model (256k context window)"*
  (A-15, round 6, 2026-10-01T04:16:29Z) and *"How about Devin for everything and Claude Code can do a deep review after
  the entire thing, similar to what we did here where Claude Code with high-powered Opus 5.5 xhigh discovered issues
  from Devin over a many-dozen-ticket build"* (A-15 rest of execution, round 7, 2026-10-01T04:21:56Z). The post-round
  deep review (REVIEW-R11) runs in Claude Code after the final release; GATE-ANNOUNCE waits on it (§5).
- **Harness string (OM-01, BM-HARNESS-01).** `devin-desktop/swe-2-high/subagent` is the CURRENT STATE `harness:` value
  and the `Harness:` line of every Round-11 contract and run ledger; there is no separate `model:` key. The Stage-B seed
  is its own segment (`claude-code/claude-opus-5-5/subagent`). Any other harness or model at a boundary is an
  unrequested switch: stop and ask; `harness:` is never overwritten silently at a close.
- **Dispatch (round 25).** *"Orchestrator + sub-agents (Recommended)"* (A-15 dispatch, 2026-10-01T06:14:06Z): one Devin
  Desktop orchestrator session (`swe-2-high`) runs `orchestrate-build` with `dispatchTarget: subagent` and hands each
  ticket to a fresh sub-agent; it reads head-bound CI at every boundary (§4 CI) and records harness + model per ticket.
  The orchestrator holds no state the LEDGER does not, so it may be restarted from the LEDGER at any boundary when its
  context fills. A RETURN PASS key is a landed ticket and is never re-dispatched as a ticket: a Round-10 key's live leg runs
  as the Round-11 row named in its re-run line, in chain order; a later OM-19 row's leg runs as that ticket's own live
  re-run (§9).
- **Isolation check (round 25; plan §8.5, S6R-13).** (1) T6 runs a throwaway probe dispatch before row 201, and P34.1's
  dispatch repeats it (`docs/tickets/201_P34.1__toolchain-pin-and-ci-hygiene.md`, § Dispatch isolation check), so the
  2026-10-19 deadline never hinges on the check. (2) The orchestrator generates a nonce with `openssl rand -hex 16` and
  records only its sha256 in the boundary record — never in a file, an environment variable, git, the dispatch prompt
  or Devin's persistent Knowledge/memory; the dispatch prompt carries a separate positive-control token. The sub-agent
  reports its initial context sources, every 32-hex token it holds, its own `date -u` start (later than the dispatch
  record) and its harness/model. **Pass** = control token echoed, nonce absent, start and model recorded; the
  orchestrator then reveals the nonce in the record (its sha256 verifies) and keeps the report verbatim. (3) A cheap
  probe repeats at each sub-round GATE and after any orchestrator restart.
- **Fallback order on a failed check (round 27, SB-3).** *"Approve headless fallback (Recommended)"*
  (2026-10-01T13:46:58Z). The orchestrator pauses (`blockedOn: isolation check failed at <row>`), then: (1) a verified
  non-interactive Devin command through `drive-build.sh --agent-cmd "<cmd>"` — only if T6 verified such a command
  (recorded in the HANDOFF); (2) otherwise the manual tier,
  `bash ~/.claude/skills/orchestrate-build/scripts/drive-build.sh --ledger docs/build/LEDGER.md --print-prompt`, pasted
  into ONE new Devin Desktop `swe-2-high` session per ticket and re-run after each unit; `gh auth status` must pass
  first. The tier taken is recorded in a PHASE LOG entry with the failed check's record.
- **Chain lock** (*agent design, labelled — the plan names a chain lock, not its mechanism*). The lock is the directory
  `drive-build.sh` uses as its single-driver lock, `<LEDGER path>.drive-lock` (atomic `mkdir`). The orchestrator session
  takes it when it starts dispatching and removes it at every pause, stop and session end; `drive-build.sh` takes it
  itself; the leg-runner (§9) takes it before any leg. Nobody removes a lock they did not take; a lock older than 6 h
  with no live session is reported to the operator, not broken.

## 2. Orient and sizing (BM-ORIENT-01; plan §8.5)

- **Orient, ≤ 48 KiB in all.** (O1) the LEDGER head: `sed -n '1,/^## OPEN FINDINGS/p' docs/build/LEDGER.md` (≤ 12 KiB;
  CURRENT STATE inside it, ≤ 3 KiB); (O3) `### RETURN PASS — current`; (O4) `python3 docs/build/tools/current_projection.py
  verify` and `docs/build/reports/current/CURRENT.md`; (O5) the last three PHASE LOG entries (`tail -n 3
  docs/build/LEDGER.md` — the Round-11 PHASE LOG is the file's last region and every entry is one line); (O6) the next
  row's manifest line (`grep -F "_<nextTicket>__" docs/tickets/00_MANIFEST.md`) and its contract header. Never read
  LEDGER, DEFERRALS or BUILD_INDEX whole; workers still load their contract and the DEFERRALS rows it scopes. A head
  over budget, a path in it that does not exist, or a stale token is a finding to fix before dispatch.
- **Sizing (A-15; SEED-13b, SEED-13e).** Before each dispatch the orchestrator re-measures the ticket's Load list with
  the named proxy counter (UTF-8 bytes ÷ 3 and ÷ 4, both recorded with the counter's name; S6R-27), **adds the
  skill-text share (implement-spec + self-review ≈ 17.5k tokens)** and the DEFERRALS allowance the contract names
  (16 KiB in the 11A contracts); the higher figure must be ≤ ~150k tokens loaded. A ticket over the line is split at its
  named seam or by `decompose-spec mode=extend` (OM-03) before dispatch — never squeezed. P34.7 is dispatched as two
  sequential contexts (its contract: part a = deliverables 1, 2, 6, 7; part b = 3, 4, 5 + PR).

## 3. The operating clauses OM-01…OM-20 (plan §3.3, verbatim)

The text below is copied byte-for-byte from plan §3.3 (S4c wording; OM-19 and OM-20 ratified at GATE-P, S5-1 + S5-3,
*"Both + list + P34.45"*, round 9, 2026-10-01T04:28:49Z). Section references in it are the plan's.

OM-01 one harness + model per segment — **Devin Desktop, `swe-2-high`** (A-15) for chain rows 201–510, recorded as `harness: devin-desktop/swe-2-high/subagent` in CURRENT STATE and in every run-ledger and contract header (no separate `model:` key; key set per the final skill contract per T0c); the Stage-B seed is its own segment, `claude-code/claude-opus-5-5/subagent`; switches only at a boundary, recorded as a PHASE LOG `harness-switch` (GATE-B → row 201); **dispatch = one orchestrator session handing each ticket to a fresh sub-agent** (`dispatchTarget: subagent`; round 25), its isolation proven on row 201, with the manual tier (`drive-build.sh --print-prompt`, one new session per ticket) as the fallback; **every agent commit carries a trailer naming the harness and model, and a G-check fails a Round-11 PR with an untrailered agent commit** (B5 OM-01 verbatim; TS-11; required because commits keep the operator's name as author, A-21) — **trailer grammar (SEED-02; S6R-10):** any recognised harness trailer passes (`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` for Claude Code, the Devin Desktop co-author trailer naming `swe-2-high`, or `Harness: <harness>/<model-id>/<tier>`); an operator commit is identified by a valid OP-25 signature (or `Harness: operator`) and needs no harness trailer — so the seed PR's ≈ 90 planning commits, all trailered `Co-Authored-By: Claude Opus 5.5`, pass ·
OM-02 the worker closes its own ticket in one commit after the PR exists; two orchestrator repairs in a round → `blockedOn` ·
OM-03 rows enter only from a reviewed plan (`decompose-spec mode=extend`) · OM-04 every date from `date -u` or git/GitHub
time; never a "chain date" · OM-05 read the PR's head-bound checks after push; red/missing → `blockedOn` · OM-06 every
status names its layer (engineered · fixture-verified · staging-verified · live-executed · public · human-completed) ·
OM-07 gate records quote the operator verbatim; agent text confirmed against its sha256 prefix · OM-08 no proxy
signatures; a past "counsel" determination is recorded as **the operator's own determination (no counsel)** (U-013; TS-09) · OM-09 hedged words get a yes/no question · OM-10 no
unbounded pre-answers · OM-11 human work is scheduled with an owner or deferred with a trigger, never silently ·
OM-12 `blockedOn` is used · OM-13 protected regions only gain lines · OM-14 no production mutation outside a ticket that
names it · OM-15 tests assert invariants, never living records · OM-16 size budget (default 3,000 changed lines) and a
tail that reads live state · OM-17 boundary lines + an operator digest with merges read from GitHub · OM-18 stop and ask;
**silence is never consent**.

**OM-19 (new; S4c wording) — windows and the live-leg queue.** A contract whose live stage has a window or a named go
carries a `Live window:` header and names its live-leg re-run prompt. Outside the window or without the go, the ticket
lands engineering and staging; the live leg goes into RETURN PASS with its window, go id and re-run line; the chain
continues. At every boundary the orchestrator compares `date -u` and live scheduler state with the queue and re-runs due
legs before dispatching. A row that needs a queued leg's **live result** (`live:` edge) waits. **A GATE is not presented
while a leg is *due*** — its earliest time has passed, its go is held, and it has not run. A leg whose window extends past
the GATE is listed in the packet and carried (FEA-03). **Execution mechanics (FEA-05):** a leg runs on its own branch
`r11/<id>-live-<n>`, created from the current chain tip, with one PR (base = the tip branch) and a head-bound CI read; the
next ticket stacks on it. Legs whose go is already held run even while the chain waits at a GATE, a `blockedOn` or a
usage-limit stop. **Backstop:** a scheduled headless leg-runner (OP-24; prompt written by SEED-17) fires at each window's
opening and close and every 6 h inside a window; it takes the chain lock, runs only legs whose go is held, and alerts the
operator (through the P34.4 channel) when a due leg cannot run.

**OM-20 (S4c wording; ratified at GATE-P, S5-1) — bounded pre-authorisation.** At GATE-B and each sub-round GATE the
operator *may* pre-authorise named production mutations of the next sub-round: exact row ids, each contract's mutation,
restore point, expiry at the next GATE. **Nothing is pre-authorised on silence.** **The 11A list was approved at GATE-P
(S5-3, 2026-10-01T04:28:49Z) verbatim plus P34.45's ER re-run, expiring at GATE-G4:** P34.3, P34.4, P34.5, P34.6 (drill
clone), P34.21a (attribution backfill), P34.24b (clone rehearsal), P34.40 (dark LB/nginx), P34.42a/b (IAM), P34.43
(execution host + logins), P34.44b (nightly quality job), P34.49 (Part VIII sealing), P34.45 (ER re-run; A-20 = a). **Never
pre-authorised:** HG-11/Class S promotions and republishes; **any roll that changes a public route's response** (API rolls
P35.57, P36.38, P37.20, P37.42); ING-GO; HG-03 flips (each executed by the operator, OP-26); **any hosted sqitch change that alters an existing table or takes an
ACCESS EXCLUSIVE lock** (P34.46, P35.14b; new-table-only changes such as P35.32 may be listed); the bounded apply
(P35.61); **any capture run or archive write touching a Part VIII-screened family** (P37.16a/b, P37.36; P34.49's
restricted-tier move is protective — it only removes material from publishable tiers — and is outside this class,
S6R-30); irreversible external deposits (P37.55); the Wave-C tier bump; any spend above $300/mo; **any WV-06 true
deletion or WV-11 purge, and the hosted deploy of the purge function's sqitch change** (P37.71). A red probe, a failed restore point or a
production read that contradicts a record voids it for the affected rows. A row not on an approved list pauses in-ticket
(§8.1: 57 OM-20 rows, 13 of them pre-authorised for 11A). **Class R standing go (B-9):** expires at the next sub-round GATE or after 30 days, whichever is
first, and is void on any ratchet regression, any Part VIII screen change or any new source (TS-13); it is renewed at each
sub-round GATE and never by `continue`. **A-20 = a:** a structural spine write may change a live-spine API answer before
HG-11, disclosed by the basis label on every response and a `/status/` notice; it still needs its OM-20 listing or an
in-ticket go.

**OM-20 in force for 11A.** The thirteen pre-authorised rows are GATE DECISIONS `### Round 11` rows of kind
`pre-authorization`, one per row id, each with `expires: GATE-G4` and `voided-by:` (a red probe, a failed restore
point, a production read that contradicts a record). P34.40's row covers **only its `sig-web` nginx roll (L1)**: the
`/v1/*` load-balancer step (L2) changes what the main-site host answers and needs its own in-ticket go (orchestrator's
conservative reading, SEED-13d; raised in the GATE-B packet). P34.6's row covers the drill clone only. A row not on a
live list pauses in-ticket for the operator's go; a pre-authorised step that meets a new fact stops and asks.

## 4. Skill rules (build-memory 0.5.0; T0c)

- **Clock (BM-CLOCK-01, OM-04).** Every date written is `date -u` at that moment, or the git/GitHub time of the event
  with its source named; never a "chain date", never later than the commit that records it.
- **CI (BM-CI-01, OM-05).** Before every dispatch, and before reporting a pause:
  `bash ~/.claude/skills/orchestrate-build/scripts/ci-boundary.sh --ledger docs/build/LEDGER.md --ticket <lastCompleted> --stack`.
  It hands off to SIG's hook `docs/build/tools/ci_boundary.py` (head-bound check-runs; Round-11 `r11/` stacks only, so
  the Round-10 reds #165/#179/#185 never block; required set `docs/build/tools/record_policy/ci_required.txt` =
  python, docs, composed, security, web). Red, pending after the wait, or unknown → `blockedOn: CI <state> on
  #<n>@<sha7> (<job>): <class>: <first failing line>`, `nextTicket` unchanged, stop. Local-only green is written
  `locally-green`. The H2 PR/CI clauses are §6.
- **Records (BM-HIST-01, OM-13).** Protected regions only gain lines, at their ends. Before every closeout commit:
  `bash scripts/docs/check-build-memory.sh . --staged` (the repo guard `docs/build/tools/memory_guard.py` runs in
  history mode). At each boundary: `--range <chainTip before>..<chainTip after>`. Exit 1, 3 or 5 is red.
- **Harness (BM-HARNESS-01).** `harness:` in CURRENT STATE and `Harness:` + `Skills:` (`git -C ~/agent-skills rev-parse
  --short HEAD`) in every run ledger; every agent commit carries a harness trailer (OM-01 grammar; CI's
  `docs/build/tools/check_trailers.py` fails an untrailered agent commit); a different harness or model → stop and ask.
- **Digest (BM-DIGEST-01; A-2, A-15).** Once per wave (each `### Round 11` manifest banner is a wave boundary), at every
  pause, at session end and at every usage-limit event:
  `bash ~/.claude/skills/orchestrate-build/scripts/digest.sh --ledger docs/build/LEDGER.md --trigger <wave|pause|session-end|usage-limit|block|gate> --write --spend "<infra spend vs the $300/mo ceiling + source>" --usage "<runs; median/max per run; cumulative; projection; usage-limit events | not measured>"`.
  The spend line covers infrastructure only (A-2a, *"Infra only; alert later"*, round 2, 2026-10-01T03:53:59Z); the
  figure is "inference" until P34.5's billing export measures it (C-7, *"Don't know; keep estimate"*). Agent usage is
  reported, not capped (A-2b, *"Report + pause on limit (Recommended)"*). If a secret value appeared in a transcript:
  `--exposed yes` and stop for rotation (the value is never written).
- **Stop and ask (OM-18).** A red check · production contradicting a record · a date not from the clock · tentative or
  delegating words · a pre-authorised step meeting a new fact · a production change off the contract or the OM-20 list
  · rewriting a protected record · a second human deferral · a harness or model change · a usage-limit event.
  **Silence is never consent.**

## 5. Pauses, gates and the operator's touchpoints (A-15, A-2b, plan §8.3)

- **When the chain pauses (A-15 pauses, *"Gate pauses + wave digest (Recommended)"*, round 7, 2026-10-01T04:21:56Z).**
  Only at: HG gates (HG-03 lines, HG-11 / Class S readouts); one ING-GO per acquisition wave; spend above the ceiling;
  red CI (`blockedOn`); a production mutation not on an operator-approved OM-20 list (in-ticket pause); the gate markers
  below; a usage-limit event; and the stop-and-ask list (§4). Otherwise it continues, with one digest per wave.
- **Usage-limit event (A-2b).** The orchestrator stops dispatching, writes a digest (`--trigger usage-limit`), records a
  PHASE LOG `pause` entry, releases the chain lock and asks the operator before resuming. Work a terminated sub-agent
  left uncommitted is audited (inspected, parked or discarded with a record), never merged as found. *Precedent:* the
  seed's own pause (2026-10-01T14:24:47Z) and the operator's answer *"Resume now (I added capacity)"* (14:25:28Z).
- **Gate markers.** GATE-G4 (row 260), GATE-G5 (343), GATE-G6 (420), GATE-ACCEPT-R11 (504), GATE-ANNOUNCE (510). Each
  check-in GATE follows its acceptance row; the packet is S5-2's (*"Ratify (Recommended)"*, round 19,
  2026-10-01T04:54:19Z): `continue` answers only batch lines. After GATE-P a packet carries only what the rows raise:
  ING-GOs, the wave's HG-03 flip list (OP-26), the next sub-round's OM-20 list, the Class R standing-go renewal (B-9),
  the spend report. A GATE is not presented while an OM-19 leg is due. A gate-marker `decision` row needs a PHASE LOG
  `pause` entry naming the marker in the same round (SEED-02a).
- **GATE-ANNOUNCE re-anchoring (plan §8.3; S6-F3, *"S0/S1 must be dispositioned (Recommended)"*, round 24,
  2026-10-01T06:05:22Z; S6R-19).** GATE-ANNOUNCE depends on REVIEW-R11 and is answered only when each REVIEW-R11 S0/S1
  finding is fixed or dispositioned by the operator. The manifest is append-only, so no row is renumbered: if a finding
  needs a fix, `decompose-spec mode=extend` appends the fix rows after row 510, then appends a new GATE-ANNOUNCE row after
  the last of them, and row 510 receives the appended token `superseded-by(row <n>)` — the pattern rows 184–187 use.
- **HG-03 flip mechanics (OP-26; plan §8.3, S6R-17).** The agent prepares the patch on `r11/<wave>-flips`; the operator
  applies it in one commit signed with the OP-25 key (or signs a GATE DECISIONS row naming each source id); P34.28's G4c
  check fails any `ingestion_permitted` false→true transition not covered by an operator-signed commit or record. No agent
  flips a source. A flip is recorded `FLIPPED <date -u> (<gate|ADR>)`. A row whose flip has not been executed lands with
  `ingestion_permitted=false` and activation skips it.
- **Class R standing go (B-9, *"Adopt + standing go (Recommended)"*, round 12, 2026-10-01T04:35:53Z).** Recorded as a
  GATE DECISIONS `pre-authorization` row with the adopted sentence verbatim (agent-drafted, adopted by the operator). It
  expires at the next sub-round GATE or after 30 days, whichever is first; it is void on any ratchet regression, any Part
  VIII screen change or any new source (TS-13); it is renewed only by the operator's words at a sub-round GATE, never by
  `continue`.
- **Gate records (BM-GATE-05…09; OM-07…OM-10; A-16).** Rows are appended at the end of the `### Round 11` table in the
  7-column form: `date` an ISO-8601 Z time; the operator's exact words in quotes with the channel; the recorder's reading
  labelled; `kind` ∈ decision · pre-authorization · confirmation · waiver · correction. Hedged or interrogative words get
  a yes/no question and a later `confirmation` row (A-16 forward rule, *"Key + forward rule (Recommended)"*, round 6). No
  agent signs, ticks or decides for the operator; past "counsel" determinations are recorded as the operator's own
  determination (no counsel) (C-3; OM-08).

## 6. PR and CI clauses (H2 §7; refine OM-05, OM-12, OM-17)

Adapted from H2's paste block to the files that exist (the required set is `record_policy/ci_required.txt`, not a
`.toml`; the flake allow-list arrives with P34.2):

- **PR-1 Stack.** One ticket = one branch `r11/<id>-<slug>` = one PR; base = the previous ticket's branch (the seed PR's
  base is `devin/p33-8-agent-docs-refresh`); body = `docs/build/pr/<ID>.md` (single source; `gh pr edit --body-file`
  after closeout). Agents never merge, retarget, rebase, force-push, merge `main`, "Update branch", delete branches, or
  change settings, rulesets, variables or secrets.
- **PR-2 Immutable prefix.** Once a successor branch exists nobody pushes to a branch; later fixes go forward on the tip as
  a `repair` naming the red sha. A moved non-tip head sets `blockedOn` (stack).
- **CI-1 Required.** python, docs, composed, security, web on the current head of every PR, docs-only included.
- **CI-2 Sha-bound read.** Truth = the check-runs of the pushed head sha (== `chainTip` == the PR's head); `gh pr checks` is
  display only.
- **CI-3 Wait.** Poll 60 s; 5-min registration grace; 45-min deadline; API errors retried, then unavailable. Never push to a
  branch while its previous head's run is in progress.
- **CI-4 Red.** Any non-success state (failure, cancelled, timed_out, action_required, startup_failure, stale, neutral, a
  skipped required job, missing, conflict, stack) → `blockedOn`, `nextTicket` unchanged, stop. New, inherited-latent,
  flake-exhausted, unavailable and stack classes all block.
- **CI-5 Flakes.** Only a failure matching an unexpired entry of the flake allow-list (P34.2 creates it) gets one
  `gh run rerun --failed` per head; both attempts are recorded; never quarantine, skip, xfail or loosen a test to pass.
- **CI-6 Close.** Closeout only after the pre-closeout head is green; the orchestrator re-reads the final head before the
  next dispatch.
- **CI-7 Unavailable.** CI that cannot run is never green: `blockedOn` + the operator's choice (wait, fix, or a waiver row
  with ids and expiry); waived work is `locally-green` via `make ci-local` with Docker up and owes a bottom-up
  re-verification when CI returns.
- **CI-8 CI changes.** A PR touching workflows, gate targets, test config, thresholds or `record_policy/` says `CI config
  changed: yes`, carries an ADR if it loosens a gate, and is flagged in the boundary line.
- **CI-9 Toolchain.** Before P34.1 (TC-PIN) lands: `npm ci` only in `web/`, never `npm install`; any lockfile change is
  stop-and-ask.

## 7. Production activation (G2 §2 AR-1…AR-9; A-20; D-P31.4-1)

- **AR-1 One step, one go.** Each live stage names its operator go (or gate) and records it verbatim with `date -u`.
- **AR-2 Restore point before any hosted write** (DB or bucket): an on-demand Cloud SQL backup confirmed SUCCESSFUL plus
  the spine watermark, per-table counts and sqitch head saved in the run ledger. Rollback preference: forward fix
  (append-only) → a PITR clone for comparison → re-pointing services to the clone only by the operator's decision. Never
  restore over `sig-pg` in place; never `UPDATE`/`DELETE`.
- **AR-3 Windows.** No hosted DB write, schema change or job image roll during the monthly batch window (day 6 00:00Z →
  day 13 12:00Z) or daily 03:00–06:30Z; preferred slot 14:00–20:00Z on a weekday with the operator reachable. Emergency
  takedowns are exempt.
- **AR-4 Clock guard.** Any read-back of a scheduled event checks `date -u` ≥ the fire time **and** the scheduler's
  `lastAttemptTime`. **D-P31.4-1:** P34.39a never reads, records or closes the `sig-sched-camreg-batch-05` OSM replay
  before both hold for its scheduled fire; until then the record says "not yet fired", never a result.
- **AR-5 Verify at the live layer.** A step is `live-executed` only after its unauthenticated probe or hosted read passes
  (`uv run sig-ops probe-hosted` plus the step's own checks); `fixture-verified` and `staging-verified` never stand in.
- **AR-6 Disclosure before exposure** — the copy that describes a surface's limits ships in the same publish.
- **AR-7 One publish path** — every web or bucket change goes through the allow-listed publish command; no hand `rsync`.
- **AR-8 Least privilege** — new services and jobs never run as the default compute service account.
- **AR-9 Ceilings are absolute** — disk, spend and wall-clock ceilings are numbers; a step stops at one without asking to
  continue. Spend above $300/mo is never pre-authorised.
- **A-20 live-API disclosure** (*"Yes, with labels"*, round 8, 2026-10-01T04:25:48Z). A structural spine write may change
  a live-spine API answer before HG-11, disclosed by the basis label on every response and a `/status/` notice; it still
  needs its OM-20 listing or an in-ticket go. P35.57 is an improvement, not a gate.

## 8. Contact, honesty and integration

- **P16 alias first (C-8, *"Alias first (Recommended)"*, round 21, 2026-10-01T04:59:05Z).** No request that needs a
  contact string (EDGAR, 511 / QLD / NSW key sign-ups) is sent until the
  `contact@surveillancegraph.org` alias exists; until then the ticket stops and records. Nobody outside the project is
  contacted (U-011); no outreach, recruiting or records-request sending. The operator's personal address is never added
  to a new file.
- **No human checks claimed (B-31 *"No maintainer check"*, B-42 *"Agent clears, disclosed"*).** No agent label counts as
  a human label and no agent signs; where a human check would appear the record says "no human check performed"; Part
  VIII family screens are "cleared by agent screen, no human review". The About page has no "who runs SIG" section until
  the operator writes it (C-5, *"Omit until I write it"*).
- **Authorship (A-21, *"Keep my name"*, round 8, 2026-10-01T04:25:48Z).** Commits keep the operator's name as author
  (a disclosed risk); every agent commit carries a harness trailer — `Harness: devin-desktop/swe-2-high/subagent` (or the
  Devin co-author trailer naming `swe-2-high`; T6 confirms what Devin Desktop writes); an operator commit carries a
  valid OP-25 signature or `Harness: operator`. CI fails a Round-11 PR with an untrailered agent commit.
- **Integration boundary record (COV-14; plan §12).** At every boundary the orchestrator records the result of
  `git merge-base --is-ancestor origin/main <chainTip>` (after `git fetch origin`) in the boundary line. The operator
  merges (OP-08), bounded at #190; agents never merge. If the operator commits to `main` or a pre-#190 branch again, the
  fix is mirrored into the Round-11 stack tip.

## 9. Live legs and the leg-runner backstop (OM-19; OP-24)

- A contract with a `Live window:` header or a named go lands engineering and staging when outside its window or without
  its go; the leg goes into `### RETURN PASS — current` (window, go id, re-run line) and the chain continues. At every
  boundary the orchestrator compares `date -u` and the live scheduler state with the queue and runs due legs, each on its
  own branch `r11/<id>-live-<n>` from the current chain tip, one PR (base = the tip branch) carrying its run-ledger entry,
  `probe-run/1` record and DEFERRALS / obligation transition, with a head-bound CI read; the next ticket stacks on it.
- **Backstop:** the operator schedules (OP-24) the headless leg-runner prompt in
  `docs/build/planning/2026-09-30-next-phase/stageB/LEG_RUNNER_PROMPT.md` — in Devin Desktop if it supports scheduled
  sessions (T6 verifies), else Devin CLI headless with the same model, recorded as a harness note (OM-01). It fires at
  each window's opening and close and every 6 h inside a window, takes the chain lock, runs only legs whose go is
  already held, and alerts the operator when a due leg cannot run.

## 10. Records conventions (SEED-02a, SEED-03, Stage-B carry)

- **Closeout additions (SEED-03).** A closeout also updates the "rows 1-N as of" line of `docs/build/README.md`; a new
  verdict word extends `check_coverage_matrix.VERDICTS` in the same change; a source flip is recorded
  `FLIPPED <date -u> (<gate|ADR>)`; D-P32.18-1…D-P32.21-1 close only with a recorded transition event.
- **Shapes the history guard relies on (SEED-02a).** A restored block's caption is the last bullet before its table;
  annotation rows start `| R<n> |`; an archived LEDGER head and its replacement land in the same commit with a pointer
  comment naming the archive file; DEFERRALS flips read `DONE <date -u> (evidence) — was: OPEN …`; a correction that
  quotes an old date says `DATE CORRECTION` or `recorded … → true …` with the true date; Round-11 GATE DECISIONS rows are
  ISO-Z, quoted, `kind`-typed and appended at the end of the 7-column table; a gate-marker `decision` needs a PHASE LOG
  `pause` entry naming the marker in the same round.
- **Recorded dates (ADR-146; C-10, *"Let me inspect it (Recommended)"*, round 21).** A wrong recorded date is corrected
  only by an appended, dated correction; `db/sqitch.plan` lines 44–52 are never edited or re-stamped.
- **PHASE LOG entries** go only at the end of the file, one line each, ≤ 2 KiB:
  `- <date -u +%F> — <ID> <kind> — branch · PR · base · summary · **Verify:** … · **Deferrals:** … · **Deviations:** … · chainTip → … · next → … · harness: …`.
- **Numbers and paths.** Ticket-authored ADRs take the next free number at dispatch (≥ ADR-191; `ls docs/adr` at that
  moment), and the ADR index is regenerated with `adr-index.sh`. Copy for operator confirmation goes in
  `docs/build/reports/copy-batches/batch-<NN>.md` (two digits, from 01; created by the first ticket that needs one).
  When `UNIVERSE_DISPOSED.csv` or `data/round11_plan.csv` change, re-run `python3 docs/build/tools/later_register.py`
  and commit its output in the same change. Regenerate `docs/build/reports/current/` with `current_projection.py
  generate` at each closeout.

## 11. Skill loading (B6 §5.3 — conditional)

The skills (`implement-spec`, `orchestrate-build`, `build-memory`, `self-review`, …) are read from `~/.claude/skills`
(symlinks into `~/agent-skills`, release 0.5.0). Devin CLI was verified to read that path (2026-10-01T04:16:29Z); whether
Devin Desktop does is checked by T6's orient dry-run. **No B6 §5.3 override is in force.** If T6 finds that Devin Desktop
does not load the skills, T6 appends an amendment here carrying the B6 §5.3 overrides and the hand-applied Tier A/B-must
template content, and the GATE-B packet says so.
