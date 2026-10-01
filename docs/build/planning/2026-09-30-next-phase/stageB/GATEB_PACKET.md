# GATE-B — operator packet (draft)

> Drafted by Stage-B unit SEED-18b (plan Appendix A **T6**, fifth bullet) at 2026-10-01T17:47:53Z (`date -u`), harness
> `claude-code/claude-opus-5-5/subagent`. Format S5-2 (*"Ratify (Recommended)"*, round 19, 2026-10-01T04:54:19Z):
> status · budget · rights · publication · OM-20 list · questions. **`continue` answers only the batch lines marked
> [batch]**; it never answers a line marked [own answer] (publication, Part VIII, identity, OM-20, own-words lines; S4
> TS-02). Nothing is decided on silence. `PD` = `docs/build/planning/2026-09-30-next-phase/`. Agent readings are labelled.
> The planning orchestrator presents this packet and records the answers verbatim (GATE DECISIONS `### Round 11`, C10).

## Status

- **Stage B (T0–T6) is built on `r11/seed`, still local** (B-16). The seed holds the guard core, the vendored validator
  sync, 34 operator-decision ADRs plus the waiver ADRs, the requirement families, the manifest for rows 201–510 with full
  11A contracts, the registers, the LEDGER head (OPERATING MODE — Round 11, CURRENT STATE `PAUSED`, `nextTicket: P34.1`)
  and this hand-off (`PD/HANDOFF.md`).
- **Checks at T6** (SEED-18b ledger `docs/build/runs/SEED-18b.md`): projection regenerated and `verify` OK; vendored
  validator, `memory_guard.py all --worktree` and `make docs-check` results as recorded there; `make scan-secrets` clean
  (5,279 files). SEED-18a ran `make check` green (5,473 passed; 387 Docker-gated suites skipped — not run on this machine).
- **Still owed before row 201:** the pre-push decisions (Q-1, Q-2) → OP-05 → bundle refresh (OP-23) → push and the seed
  PR **5/5 green** → the operator-run Devin Desktop checks and the isolation probe (Q-8) → this gate → C10.
- **A1 delta (2026-10-01T17:23:36Z; `PD/baseline/DELTA_T6.md`): 14 of 87 keys changed; build-memory control files 0.**
  `main` = `00f67f4b` after your #141–#154 sitting (GitHub `mergedAt` 04:24:07Z–04:26:00Z — a minute earlier than the
  plan's "04:25–04:26Z"); 36 open PRs #155–#190, **all 5/5 green**; production and the public site unchanged since A1
  except one automated backup and an unexplained Cloud SQL `settingsVersion` 63 → 64 (no UPDATE operation; settings
  identical). **New:** three commits pushed 2026-10-01T00:58–01:01Z onto #179, #165, #185 (Q-9), so the remaining merge
  sitting now conflicts once and `ACCEPT-R10.md` disagrees between #185's head and the seed (Q-9, Q-10).
- **GitHub settings read at 17:28Z:** no stack ruleset, squash/rebase merges still on (OP-05 not applied); 0 Actions
  variables (OP-07 not applied).

## Budget

- **Infrastructure** (the $300/mo ceiling, A-2a *"Infra only; alert later"*): no measured figure — the plan's projection
  is ≈ $90–100/mo now, ≈ $112–122/mo by 11D (inference on G1's unverified list prices; C-7 *"Don't know; keep estimate"*);
  P34.5's billing export measures it in early 11A. No over-$300 approval is planned. Watch item until P34.21b/P35.5: the
  world-readable `sig-public` tree (denial of wallet).
- **Agent usage** (reported, not capped — A-2b): Stage B hit one usage-limit event (2026-10-01T14:24:47Z) and resumed on
  your *"Resume now (I added capacity)"* (14:25:28Z); per-unit usage was not measured. If the isolation check forces the
  manual tier: ≈ 300 sessions, ≈ 15–25 h of your time (inference).

## Rights

- No source is flipped by the seed; `ingestion_permitted` stays as it was. HG-03 flips run per wave as OP-26 (Waves A/B
  at GATE-G4). Nothing in this gate flips a source.
- Answered since GATE-P and recorded (no question): **SB-2** — ADR-183's express-terms acceptance covers the scheduled
  refreshes of the same sources (*"Yes, same sources (Recommended)"*, round 27, 2026-10-01T13:46:58Z; SEED-11d's question).
  The Q-E2-13 option c re-decision of the out-of-rule / counsel-flagged rows is folded into P36.2.

## Publication

- **No republish at this gate.** The public release stays `sig-2026-09-27-ce480ab1`.
- **The seed push publishes the planning directory** (B-16; **OD-27 = a, "publish as recorded"**, 04:39:45Z) after the
  scans. Scan result (`PD/stageB/PREPUSH_SCAN.md`): secrets clean; your address appears only where OD-27 expects it (new
  occurrences only inside your verbatim quotes in META_PLAN §7.1, `baseline/TRACK0_RECORD.md`,
  `feedback/OPERATOR_FEEDBACK.md`); **two items need your decision before the push** — Q-1 (Part VIII layer pointers) and
  Q-2 (ArcGIS handles and two owner usernames).

## OM-20 list

- **Unchanged from GATE-P** (S5-3, 2026-10-01T04:28:49Z; recorded by SEED-17 as 13 `pre-authorization` rows, `expires:
  GATE-G4`, `voided-by:` red probe / failed restore point / contradicting production read): P34.3, P34.4, P34.5, P34.6
  (drill clone), P34.21a, P34.24b, P34.40 (dark LB/nginx), P34.42a, P34.42b, P34.43, P34.44b, P34.49, P34.45 (ER re-run),
  plus the **B-9 Class R standing go** row. GATE-B adds nothing to it. Two scope readings need your words (Q-3, Q-4).

## Questions

**Q-1 [own answer — Part VIII / publication] Planning notes point at public layers that expose plate reads and
registrant PII.** Research I3 found (and blocked, "rows never read") ArcGIS/Socrata layers whose schemas hold plate
reads with time and place, LPR hits with hotlist reasons, call-for-service rows and a camera registry's registrant names,
addresses, phones and e-mails. The notes record **their service URLs** in 12 lines of 5 planning files (list: `PREPUSH_SCAN.md` § (c)1; three
further lines cite Oakland's official per-read open dataset, already cited in the public repo — kept).
No row data is copied. Publishing them would put a list of where such data sits into a public repo.
- (a) **Forward-fix before the push (Recommended):** one commit replaces each service URL with `[layer URL withheld —
  Part VIII]`, keeping the finding text, ids and field names; the URLs stay in the pushed history (planning commits
  reach the chain unchanged, plan §12), which the seed PR body discloses.
- (b) Rewrite the local planning commits before the first push so the URLs never publish — removes them from history but
  changes every later commit id that run ledgers, the PHASE LOG and GATE DECISIONS cite, and departs from plan §12.
- (c) Publish as recorded.

**Q-2 [own answer — identity] Personal-looking ArcGIS handles.** The 31 personal-looking `camreg_*` source ids
(F-097/F-131) appear in 113 lines of 27 seed files — far beyond the findings that quote them (data tables, ADR-169, the
manifest, two contracts, DEFERRALS, run ledgers, CARRY). The same ids are already public at `b051732c` (connector data)
and on the live site; P34.18 re-keys them. Two further ArcGIS **owner usernames** that look like individuals' accounts are
new to the repository (four lines in two planning CSVs).
- (a) **Publish the 31 ids as recorded; forward-fix the two new owner usernames in Q-1's commit (Recommended).**
- (b) Forward-fix every occurrence to `H<nn>` tokens (the map stays in the gitignored C3 list).
- (c) Publish everything as recorded.

**Q-3 [own answer — OM-20] Does "P34.6 (drill clone)" also cover P34.6's first monthly logical export and the
`sig-backups` lifecycle changes?** SEED-13b read it as not covering them (they take an in-ticket go).
- (a) **No — drill clone only; the export and the lifecycle change each need an in-ticket go (Recommended).**
- (b) Yes — pre-authorise both too, expiring at GATE-G4, with the contract's restore points.

**Q-4 [own answer — OM-20] P34.40's `/v1/*` load-balancer rule.** It makes the API answer on the main site's host — a
public-surface change, so the orchestrator read it as not "dark": only the nginx roll runs pre-authorised.
- (a) **Confirm: the `/v1/*` step needs its own in-ticket go (Recommended).**
- (b) Treat all of P34.40 as pre-authorised.

**Q-5 [batch] Chain lock** *(agent design, OPERATING_MODE_R11 §1)*: the lock is drive-build's single-driver directory
`docs/build/LEDGER.md.drive-lock` (atomic `mkdir`), taken by the orchestrator, `drive-build.sh` and the leg-runner;
nobody breaks a lock they did not take; a lock older than 6 h with no live session is reported to you. **Recommended:
confirm.**

**Q-6 [batch] B-9 Class R standing go — expiry reading** *(agent reading)*: it expires at **GATE-G4 or 2026-10-31,
whichever is first** (30 days from adoption at 2026-10-01T04:35:53Z); void on a ratchet regression, a Part VIII screen
change or a new source; renewed only by your words at a sub-round GATE. **Recommended: confirm.** Alternative: count the
30 days from GATE-B.

**Q-7 [batch] Leg-runner alerts until P34.4 lands** *(agent design)*: a digest entry (`digest.sh --trigger block
--write`) plus the session's final message; P34.4's channel replaces it once landed. **Recommended: confirm.**

**Q-8 [own answer — tooling facts] Devin Desktop checks** (`PD/HANDOFF.md` §4–§5; R-30). Please run the dry-run prompt
and paste: (a) orient resolves row 201; (b) skills load from `~/.claude/skills`; (c) a fresh sub-agent can be started;
the **isolation probe record**; (d) can a sub-agent compact; (e) the co-author trailer it writes; (f) a headless Devin
command, verbatim, or "none"; (g) scheduled sessions — and therefore the leg-runner's harness string; (h) `gh auth
status`; (i) model and window. **T6 found no `devin` executable on `PATH` in Claude Code's shell**, so fallback B is
unverified until (f). Consequences are already decided (round 27 SB-3): a failed (a)/(c)/probe → pause → B if (f) is
verified, else the manual tier; a failed (b) → the orchestrator appends the B6 §5.3 overrides to OPERATING_MODE_R11.md
before row 201.

**Q-9 [own answer — records] The three mid-stack pushes and ACCEPT-R10.** At 2026-10-01T00:58:12Z, 00:59:09Z and
01:01:36Z commits `b01ef231` (#179), `f8377011` (#165) and `4a2ce75d` (#185) landed with your identity as author and a
`Co-Authored-By: Claude Opus 4.8` trailer; no planning record mentions them. `4a2ce75d` restores `ACCEPT-R10.md` to
"PENDING … No approval … is asserted" on #185's head, while the chain tip and the seed keep the SIGNED text with SEED-08's
annotation (your approval reached the session at 2026-09-28T18:46:46Z — confirmed as C-1 — and C-13 *"Superseded"*).
(i) **Attribution:** were these pushes made at your direction, and in which tool? — (a) yes, at my direction, in
<tool> · (b) don't recall — record the git facts only. *(No recommendation: only you know.)*
(ii) **Which record stands after the merges:**
- (a) **Keep the chain's record (Recommended):** at the seed PR's merge resolve `ACCEPT-R10.md` to the seed's text (SIGNED
  + B7 annotation + C-13 supersession); an early Round-11 row appends a dated annotation naming `4a2ce75d` and why it was
  superseded. *(Agent reading: this matches your C-1 and C-13 answers; `main` shows PENDING only between #185's merge and
  the seed's.)*
- (b) Keep PENDING: resolve to #185's text and append the seed's annotation under it with a dated note.
- (c) Decide at the merge sitting; P38.3c's integration plan records it.

**Q-10 [batch] The OP-08 sitting now conflicts once.** Merging #180 conflicts in `docs/build/BUILD_INDEX.md` (row 183:
`b01ef231` on #179 vs. the stack's later text); H1's "zero conflicts, tree-identical to #190" no longer holds. **Recommended:
take the stack's side at #180** (the later row text; the simulation then runs clean to #190, differing from #190 only in
`ACCEPT-R10.md`, Q-9). Agents do not merge; this is guidance for your sitting.

**Q-11 [own answer — records] The C10 `harness-switch` entry.** SEED-17 drafted it (`docs/build/runs/SEED-17.md` § Draft):
claude-code → devin-desktop, reason A-15 and round 25, quoting your words of 04:16:29Z, 04:21:56Z and 06:14:06Z verbatim.
- (a) **Approve the draft as written (Recommended)** — C10 fills the dates from `date -u` and the GATE-B row time.
- (b) Edit it (give the change).

**Q-12 [own answer — the gate] GATE-B.** Start Round 11 at row 201 (P34.1) in Devin Desktop, `swe-2-high`, mode A
(orchestrator + fresh sub-agents), once the seed PR is 5/5 green and the Q-8 checks pass; the 11A OM-20 list stays as
approved at GATE-P; fallback order as SB-3.
- (a) **Go (Recommended).**
- (b) Go, but in the manual tier from row 201.
- (c) Hold.

## Already answered — recorded, not asked again

- **S6R-16 / round 25's third option:** the headless Devin command is approved as the first fallback before the manual
  tier — round 27 SB-3, *"Approve headless fallback (Recommended)"*, 2026-10-01T13:46:58Z (GATE DECISIONS row by SEED-17).
- **SEED-11d's ADR-183 scope question:** round 27 SB-2 (Rights above).

## Your actions outside the questions (manifest § Human prerequisites)

OP-05 **before the push** · OP-23 store the refreshed bundle **before the push** · OP-25 signing key **by GATE-B if
possible** (at the latest before GATE-G4) · OP-07 and OP-24 **before row 201** · OP-01…OP-04 review the live skill
releases before row 201 · OP-08 any time (safety item; Q-9/Q-10).
