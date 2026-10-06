# T0c — final skill contract (release 0.5.0) and what the SIG seed must sync

Recorded by the planning orchestrator from the T0c sub-agent's report (2026-10-01). Skills repo `~/agent-skills`, branch
`claude/r11-skill-rest` (local; checked out = live via `~/.claude/skills`): `c814f8d` build-memory validator/history/adr-index ·
`fee87b1` orchestrate-build/implement-spec/decompose-spec · `4129756` reconcile-build/synthesize-spec · `e172f52` release 0.5.0 ·
`4140fda` stale-path fix · `8aeb6dc` closed run ledgers may only gain lines. Earlier tiers: 0.3.0 (Tier A, `f70e608`), 0.4.0
(Tier B-must, `3971a7d`). All 25 B6 proposals applied. Suites pass; both SIG trees: exit 0, 0 violations, 73 warnings.

## Vendored validator (`scripts/docs/check-build-memory.sh`)
Upstream now contains SIG's `contract/patch/3` JSON shape (`build-memory-check/2`), so **replace the fork with 0.5.0 + a
provenance banner** (record skill commit), keeping SIG's inherited differences (duplicates keyed on ticket id, tolerant
DEFERRALS status parsing, human output `- check: message`). If a fork is kept, port every check added since 0.2.0: guards
marker warn/fail semantics; ledger budget/shape (head ≤ 12 KiB, CURRENT STATE ≤ 3 KiB and ≤ 256 B/line, no `| PRIOR`,
`returnPass` as id list, no stray key lines, PHASE LOG last region, entries ≤ 2 KiB); `harness` slot between `round` and
`updatedAt`; readout `Status:` lines; P-row owner/trigger warning; DONE-without-signed-GATE-ACCEPT and pre-answered-gate
warnings; 7-column GATE DECISIONS `kind` + pre-authorization scope; markup-tolerant PHASE LOG parser + exit 3; value
vocabularies; stale paths/tokens; lowest-unlanded `nextTicket`; BUILD_INDEX scan; tree clock warnings + `--now`; new-file
rules (guard sentence, `Harness:`, ADR "—" cells) judged by commit ancestry; close-repair, round-banner, orient-probe and
`living-pin?` warnings; old-index recognition; `--planning`; `--range`/`--staged`/`--first-parent` → `check-history.sh`;
`--exclude-dir=logs` in the secret scan.

## Other syncs
- Vendor `adr-index.sh` 0.5.0, then regenerate `docs/adr/README.md` (143 rows change + the new ADRs).
- Vendor `check-history.sh`, **or** build `docs/build/tools/memory_guard.py` accepting
  `all --range A..B | --staged | --first-parent SHA [--json PATH] [--now ISO]` with exits 0/1/2/3/5 (history mode hands off
  to a repo guard `docs/build/tools/memory_guard.*` when present).
- CI docs job: `--range base..head` on PRs, `--first-parent` on pushes to main (job already fetches full history).

## New SIG files
- Guards marker line `<!-- build-memory-guards: 1 -->` in `docs/build/README.md`.
- `docs/build/tools/record_policy/history.policy`: `archive docs/build/reports/memory-repair` (B3 head archive);
  `exempt docs/build/LEDGER.md ### RETURN PASS — current`; `append-only db/sqitch.plan` + a `date` rule for it (C-10: L44–52
  allow-listed, never re-stamped); `date` rules for `sources.toml` rights dates; `allow` entries with expiries for scheduled
  future dates (e.g. the 10-10 OSM replay).
- From 0.4.0: `docs/build/tools/record_policy/ci_required.txt` (python, docs, composed, security, web) and
  `docs/build/tools/ci_boundary.py` (Round-11 `r11/` PRs only; called as `--pr <n> --json <path>`, exits 0/3/4/5).
  Optional `record_policy/stale_tokens.txt` (retire a default with `!token`). `reports/digests/` is created on first
  `digest.sh --write`.
- Manifest: `## Operating rules` (nine short rules incl. Records and Reporting); Round-11 rows under banners starting
  `### Round 11` — one per wave so the digest cadence has a boundary; rows 184–187 marked deferred in their chain rows (else
  the `nextTicket` check warns).
- BUILD_INDEX: a `## Round 11` table with the 12-column header (new live-verification vocabulary + `harness`).
- DEFERRALS flips in the form `DONE <date> (evidence) — was: OPEN …`.
- The 4 `living-pin?` test files (incl. `tests/.../test_agent_docs_current_state.py:85` + 3 more): convert or delete before the
  seed changes the values they pin (= SEED-03 / PKG-02).
- Guards-marker dry run on the current tree: 26 violations, all cleared by B3's seed (archived head, values-only CURRENT STATE,
  `IN_PROGRESS`, new last PHASE LOG region). **Trap:** B3 §3.6's tombstone sentence quotes "gitignored", ".agents/scratch"
  and "Do not resume until" literally — fails under the marker; rephrase or retire those defaults with `!token`.

## Seed LEDGER — CURRENT STATE (exact keys, this order, values only; ≤ 256 B/line, block ≤ 3 KiB, head ≤ 12 KiB; no other
line in the file may start with one of these key names)
`projectStatus` · `nextTicket` · `lastCompleted` · `blockedOn` · `pauseRequested` · `returnPass` · `manifest` ·
`canonicalSpec` · `memoryRoot` · `dispatchTarget` · `buildWorktree` · `buildBranchBase` · `pinnedBaseSha` · `chainTip` ·
`benchmarkSet` · `autonomy` · `mergePolicy` · `round` · `harness` · `updatedAt`.
**Orchestrator override of T0c's example values (the plan + operator answers win):** `dispatchTarget: subagent` and
`harness: devin-desktop/swe-2-high/subagent` (round 25), not `manual`; check `mergePolicy`/`autonomy` against the layout's
value vocabulary (plan intent: agents never merge — operator integrates; checkpoint autonomy with A-15 pause rules);
`projectStatus: PAUSED` until C10 sets `IN_PROGRESS`. The seed runs on Claude Code, so a `harness-switch` PHASE LOG entry
(claude-code → devin-desktop) quoting A-15 ("We will drive most of the execution with Devin Desktop using their new SWE-2 High
model (256k context window)", round 6) and round 25 is appended before the first Devin dispatch; otherwise the first Devin
session is an unrequested switch and must stop and ask. New entries go under `## PHASE LOG — Round 11` at the end of the
file, shape `- YYYY-MM-DD — <ID> <kind> — …`.

## OPERATING MODE lines the final skills expect
- Orient (BM-ORIENT-01): O1 head (`sed -n '1,/^## OPEN FINDINGS/p'`); O3 `### RETURN PASS — current`; O4
  `current_projection.py verify` + `CURRENT.md`; O5 last three PHASE LOG entries; O6 next row's manifest line + contract
  header; never read LEDGER/DEFERRALS/BUILD_INDEX whole; ≤ 48 KiB total.
- Clock (BM-CLOCK-01): every date from `date -u` at the moment of writing.
- CI (BM-CI-01): `ci-boundary.sh --ledger docs/build/LEDGER.md --ticket <lastCompleted> --stack` before every dispatch (uses
  SIG's `ci_boundary.py`); red/pending/unknown → `blockedOn`.
- Records (BM-HIST-01): protected regions only gain lines, at their ends; `check-build-memory.sh . --staged` before every
  closeout commit; `--range <chainTip before>..<after>` at each boundary.
- Harness (BM-HARNESS-01): `harness:` + every run ledger's `Harness:`/`Skills:`; commits carry a harness trailer; a different
  harness or model → stop and ask.
- Digest (BM-DIGEST-01): `digest.sh --ledger docs/build/LEDGER.md --trigger <why> --write --spend "<infra spend vs $300 +
  source>" --usage "<runs; median/max per run; cumulative; projection; usage-limit events | not measured>"` at every pause,
  session end, usage-limit event, and once per wave; `--exposed yes` and stop if a secret appeared in a transcript.
- Stop and ask: red check · production contradicting a record · a date not from the clock · tentative/delegating words · a
  pre-authorized step meeting a new fact · a production change off the contract or OM-20 list · rewriting a protected record
  · a second human deferral · a harness/model change · a usage-limit event. Silence is never consent.
- Manual-tier resume (fallback): `bash ~/.claude/skills/orchestrate-build/scripts/drive-build.sh --ledger
  docs/build/LEDGER.md --print-prompt` → paste into ONE new Devin Desktop `swe-2-high` session; re-run after the unit.

## Open items
- The cross-harness eval (B6 Q-B6-5) was not run; no CI/Linux run for agent-skills (macOS bash 3.2 only).
- Seed run ledgers SEED-11a/11b/11c/12a recorded `Skills: 4140fda` (0.5.0 minus `8aeb6dc`, which only adds the history-mode
  rule "closed run ledgers may only gain lines") — immaterial to tree checks.
- The ADR index must be regenerated after all SEED-11 ADRs land (0.4.0 and 0.5.0 both flag it).
