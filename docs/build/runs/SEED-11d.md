# Run ledger — SEED-11d (Round 11 Stage B, T1): the operator-waiver and acceptance ADRs 179–189, landed-ADR status lines and the recorded revisit-trigger evaluations

- **Unit:** SEED-11d — one of the SEED-11 sub-agent contexts (Appendix A T1; `data/ticket_catalog.csv` SEED-11)
- **Harness:** claude-code/claude-opus-5-5/subagent
- **Skills:** 4140fda (`git -C ~/agent-skills rev-parse --short HEAD`)
- **Worktree / branch:** `/Users/stevenvitali/Eleutheria-next-phase`, `r11/seed` (HEAD `f66b2450` at start); nothing committed by this unit — the orchestrator commits
- **Started:** 2026-10-01T07:31:17Z (the unit's first `date -u`, taken after reading the brief and the plan)
- **Closed:** 2026-10-01T07:52:54Z
- **Inputs read:** `PD/stageB/AGENT_BRIEF.md`; `PD/NEXT_PHASE_PLAN.md` §1.3, §4, §5.5, §5.8, §5.10, §6.3, §6.5, §7, §11.3, §13.5, §14, §15, Appendix A; `PD/feedback/RATIFICATION_LOG.md` (all rounds); `PD/design/S6-ratification-applied.md` §5–§7 and the S6b addendum; `PD/research/F3-backlog.md` §5; `PD/design/B4-verification.md` G2/G8; `PD/research/B2-append-only.md` (frozen-after-landing); `PD/design/E2-governance-options.md` §E2-02; `PD/data/{decision_catalog,round11_plan}.csv`; `PD/universe/UNIVERSE_DISPOSED.csv` (adr_trigger rows); `docs/2_canonical_design_spec.md` (read-only); the landed ADRs touched; `docs/risk_register.md` (read-only); `~/.claude/skills/build-memory/{layout.md,templates/adr-TEMPLATE.md,scripts/adr-index.sh}`. `PD` = `docs/build/planning/2026-09-30-next-phase/`.

## §7 check (numbering and authorship)

Plan §7 assigns ADR-179 … ADR-189 to **SEED-11**, with the titles and decisions the unit prompt listed — no difference.
None of 179–189 is ticket-authored, so none was skipped. (The ten ticket-authored ADRs of §7 are 151, 156, 157, 160,
161, 174, 175, 176, 177, 178; none is in this range.)

## What was written

### New ADRs (11) — `docs/adr/`

| ADR | file | decision recorded | operator words (time) · sha256 |
|---|---|---|---|
| 179 | `ADR-179-wv-04-sig-ui-042-release-block-waived.md` | WV-04: SIG-UI-042's release-block clause waived; review recorded "not yet performed" | A-23 WV-04 sentence (04:28:49Z) · `2a0339a9…9c22` |
| 180 | `ADR-180-wv-05-e-mail-only-intake-for-round-11.md` | WV-05: GOV-001's one-click clause and GOV-002 waived for Round 11 | WV-05 sentence (04:28:49Z) · `bf1f65d5…6142`; B-8; C-12 sentence · `da7889af…2a16` |
| 181 | `ADR-181-wv-06-single-operator-true-deletion.md` | WV-06: GOV-008's two-person clause waived; scope + tombstone clauses stand | WV-06 sentence (04:28:49Z) · `dbf7a851…966c`; S6R-03 (06:51:11Z) |
| 182 | `ADR-182-wv-07-counsel-review-clauses-waived.md` | WV-07: LIC-009 counsel-referral and INGEST-037 counsel clauses waived; risk-register and ADR-level clauses stand | WV-07 sentence (04:28:49Z) · `c5a71e9d…25ac` |
| 183 | `ADR-183-express-terms-acceptance.md` | A-8 express-terms acceptance; A-9 "may be commercial" for new NC sources (not a waiver) | A-8 sentence (04:09:43Z) · `cd76b74e…2fb4`; A-9 label (04:07:45Z) · `9ea4affa…95ed` |
| 184 | `ADR-184-terms-conflicted-public-pages-fetch-envelope.md` | the vendor/platform fetch envelope (A-17 D3-Q3 b, B-35 IT7, B-39, B-41 R2a, C-8 alias first, B-6 UA); the INGEST-037 ADR-level deviation decision | option labels A-17, B-6, B-35, B-39, B-41 R2a, C-8, S6R-01, S6R-08 (verbatim, timed); envelope text labelled agent interpretation · `71385999…f3eb` |
| 185 | `ADR-185-part-viii-screened-lanes-without-a-human-clear.md` | S1–S9 lanes incl. S8 tribal; TR facts + cite; agent clears dossier families, disclosed; B-44 Part VIII rows; the one PUB-002 persistence rule | option labels B-32, B-35, B-36+B-37, B-42, B-44 (verbatim, timed) |
| 186 | `ADR-186-wv-08-gov-003-response-time-slas-waived-handling-priority-published.md` | WV-08: GOV-003 SLA-time clause waived; priority clause met differently | WV-08 sentence (06:05:22Z) · `806faae3…43fb` |
| 187 | `ADR-187-wv-09-crawler-rule-6-waived-for-documentcloud-muckrock.md` | WV-09: INGEST-036 rule 6 waived for DocumentCloud/MuckRock only | WV-09 sentence (06:05:22Z) · `94f06123…1fb0` |
| 188 | `ADR-188-wv-10-flock-portals-probe-only.md` | WV-10: INGEST-035 no-direct-capture clause waived; probe-only; INGEST-013/rule 4/INGEST-037 stand | WV-10 sentence (06:51:11Z) · `82487f7b…8fcf` |
| 189 | `ADR-189-wv-11-one-operator-only-purge-function.md` | WV-11: one operator-only purge function, the sole STORE-011 exception | WV-11 sentence (06:51:11Z) · `04e7b77f…19b1` |

Each ADR uses the template header (`# ADR-NNN: <title>`, `- **Status:**`, `- **Date:**`, `- **Ticket:**`,
`- **Requirement ids:**`, `- **Spec:**`), quotes the waived spec text with its line numbers (spec as built at
`71e8bc83`, with the `spec_src` file named so the reference survives T1's rebuild), states scope, compensating
controls, consequences and alternatives, and ends with `## Revisit trigger`. Every adopted sentence carries the label
"agent-drafted, adopted by the operator at <round time>" and its sha256 (`printf '%s' "<sentence>" | shasum -a 256`),
recomputed here; all nine equal the values S6/S6b/S6c recorded. Dates came from `date -u` in the shell command that
installed the files (2026-10-01T07:45:36Z).

### Appended to landed ADRs (57 files; append-only — `git diff` shows 644 insertions, 0 deletions)

Format (no precedent existed for status lines; the trigger-evaluation form follows the P21.2 precedent in ADR-037,
038, 039 and 054): a `### Trigger evaluation — SEED-11 (Round 11 T1, <date>): <verdict>` subsection appended after the
`## Revisit trigger` text, then — where a status line applies — a final `## Status updates` section of
`- **Status:** <relation> by ADR-NNN (<date -u +%F>) …` lines, each followed by a `- **Status note …**` bullet.
`adr-index.sh --check` reads the appended `Superseded by` lines as the Status cell (verified on a copy).

- **Superseded (11 files):** ADR-015 → 081 (in practice), ADR-032 → 050, ADR-058 §3 → 073, ADR-075 → 081 (e2-micro
  DB-tier decision), ADR-092 Decision 2 → 099 and 101, ADR-096 §Decision 1 → 106 (F3 §5.2; F-249); ADR-105 §5 → 153,
  ADR-091 §3–4 → 155, ADR-097 §2–3/§6 → 155, ADR-126 and ADR-127 cutover statements → 148 (plan §7).
- **Qualified / Amended / Extended (6 files):** ADR-086 and ADR-106 qualified by 167; ADR-088 extended by 168; ADR-099
  §3 amended by 153; ADR-124 extended by 159; ADR-134 extended by 155.
- **Recorded trigger evaluations (42 files):** F3 §5.1's 26 "need a new ADR or a ticket" (ADR-012, 016, 021, 052, 053,
  062, 063, 067, 073, 076, 077, 079, 081, 090, 098, 101, 105, 107, 111, 114, 120, 122, 126, 130, 132, 145) and its 16
  "needing only a recorded evaluation" (ADR-027, 028, 034, 035, 036, 037, 038, 039, 040, 041, 042, 046, 048, 054, 070,
  080), each with F3's evidence and the Round-11 answer (row / ADR) from the plan and `universe/UNIVERSE_DISPOSED.csv`.
- **Not touched (ticket-owned, S6R-24):** the `Superseded by ADR-174` lines on ADR-016/076 (P35.1a), `Qualified by
  ADR-175` on ADR-081 (P34.6), `Extended by ADR-161` on ADR-132 (P35.12), `Revisited by ADR-160` on ADR-079/122
  (P35.17), `Superseded by ADR-156` on ADR-118 §2 (P35.52). Those ADRs' evaluation blocks say the ticket appends its
  own line.
- **Not regenerated:** `docs/adr/README.md` (as instructed).

## Checks

| check | result |
|---|---|
| `uv run pytest tests/unit/test_policy_adrs.py -q` | **180 passed** (every ADR, incl. 179–189 and the 57 appended files, has a non-empty `## Revisit trigger`) |
| sha256 of each adopted sentence as written in ADR-179…183, 186…189 vs. the value stated in the same file | 9/9 match |
| `git diff -- docs/adr` on landed files | 57 files, 644 insertions, **0 deletions** (append-only) |
| `bash ~/.claude/skills/build-memory/scripts/adr-index.sh --check` on a copy | appended `Superseded by` lines parse into the Status cell; new ADRs parse title / ticket / status |
| `bash scripts/docs/check-build-memory.sh .` | exit 1 — **1 violation**: `docs/adr/README.md` stale vs a fresh regeneration (expected; the index is regenerated by the orchestrator per Appendix A T1); **1 warning**: BM-ADR-04, spec Appendix F ≠ ADR file set (expected until SEED-12 adds Appendix F rows for ADR-146+) |

## Open issues / hand-offs

1. **G2 guard policy (SEED-02).** B2/B4 define `frozen-after-landing` as "only a `Superseded by ADR-NNN` status line may
   be appended". Plan §7 (COV-14) adds `Amended by` / `Qualified by` / `Extended by` lines, and Appendix A adds recorded
   trigger evaluations. The record policy for `docs/adr/` must accept an EOF block made of `### Trigger evaluation — …`
   subsections and/or a `## Status updates` section of `- **Status:** …` / `- **Status note …**` bullets, or the seed PR
   fails its own guard. "ADR-NNN must exist" holds only once ADR-148/153/155/159/167/168 land in the same seed.
2. **ADR_TRIGGERS.csv (SEED-15).** `trigger_sha256` should hash the `## Revisit trigger` text only up to the first
   `### Trigger evaluation` subsection, or every later evaluation will read as a changed trigger (the P21.2 blocks
   already sit inside that section).
3. **ADR-032 → ADR-050** is beyond the "(incl. …)" list of Appendix A but is the sixth ADR F-249 names and ADR-050
   declares "Closes out: ADR-032"; included under "every superseded landed ADR". The orchestrator may drop it.
4. **ADR-002** — ADR-189 makes the one exception to its decision; §7 names no status line for it, so none was added.
5. **ADR-015's supersession** is "in practice" (F3); ADR-081 never says it supersedes ADR-015. The status line says so.
6. **Descriptions of concurrent ADRs.** The status notes describe ADR-148/153/155/159/167/168 from plan §7's one-line
   decisions ("Per plan §7 row NNN"); this unit did not read those files (written concurrently).
7. **Risk register.** RISK-P15-29 describes `assertReviewReleasable` as the release gate WV-04 retires; its dated
   append-only correction is T4's (SEED-14). ADR-182 notes RISK-P0-01…04 stay; RISK-P0-06 closes via ADR-168.
8. **ADR-183 open question for the operator:** whether rows re-ingested after 2026-10-01 from the express-terms sources
   are covered by "currently public rows" — recorded as open, not decided.
9. **Counsel-dormant restatements (F3 §5.4, 13 ADRs)** were not appended (not in this unit's list); ADR-182 names them.
