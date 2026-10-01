# Pre-push scan of `r11/seed` (B-16; plan §12; Appendix A T6 second bullet)

> Written by Stage-B unit SEED-18b at 2026-10-01T17:55:21Z (`date -u`), harness `claude-code/claude-opus-5-5/subagent`. **The
> repository is public; the push publishes every file and every commit in the range.** This file names no secret, never
> writes the operator's address, and reports the personal-looking ArcGIS handles by index only. Nothing was redacted by
> this unit (the brief: "do not redact yourself"); the decisions are the orchestrator's and the operator's (GATE-B packet
> Q-1, Q-2). `PD` = `docs/build/planning/2026-09-30-next-phase/`.

## Scope and method

- **Range:** `git diff b051732c..HEAD` with HEAD = `03effc4d` — **129 commits, 786 files (603 added, 183 modified, 0
  deleted), +116,228 / −1,985 lines.** Every changed file was scanned **whole** at HEAD; each hit is marked new (on a line
  the range adds) or pre-existing (already public on #190). The added lines of **every commit** in the range
  (`git log -p`, 143,725 patch lines) were scanned too, so a value added and later removed would still show.
- **This unit's own files** (uncommitted at the scan; they will be pushed): `PD/HANDOFF.md`, `PD/baseline/DELTA_T6.md`,
  `PD/stageB/GATEB_PACKET.md`, this file, `docs/build/runs/SEED-18b.md` and the regenerated `docs/build/reports/current/`
  (§ This unit's files).
- **Tools:** (a) `make scan-secrets` and `uv run python scripts/ci/secret_scan.py <the 786 files>` (the repo's gate,
  ADR-078) plus a supplementary shape list run over the files and the history (Anthropic/Google-OAuth/GitLab/npm/HF/Stripe
  keys, JWTs, credentials in URLs, quoted password/token assignments, bearer tokens, PEM/OpenSSH blocks, service-account
  JSON, `SIG_INTAKE_*` literals); (b) e-mail and phone patterns (US and international), the operator's identities
  derived from commit metadata at run time (no literal in the script), the operator's name, `/Users/<name>` paths, the
  repo slug, `@handles`, third-party GitHub/Bluesky/X account URLs, the 31 ids of the gitignored C3 list
  (`docs/build/logs/next-phase/C3/personal_like_ids.txt`) as full ids and as bare handles, and ArcGIS `owner` strings;
  (c) officer-title + name, honorific + name, plate-shaped tokens on plate/VRM/hotlist lines, licence-plate keyword
  contexts, registrant/homeowner/doorbell/private-residence keywords, house-number street addresses, 5-decimal
  coordinate pairs, and every service URL on a line that describes plate reads, LPR hits or registrant PII. Pattern
  scans find candidates; each candidate below was read in context and classified by hand.

## Counts

| class | candidates | after reading | needs a decision |
|---|---:|---|---|
| (a) secrets — repo gate | 0 in 5,279 tracked files; 0 in the 786 changed files | clean | — |
| (a) secrets — supplementary shapes, tree | 0 | clean | — |
| (a) secrets — history | 2 commits (`4df1552f`, `2cf03075`, 2026-09-30) add a credential-shaped `SIG_INTAKE_*` literal | the local-preview value C-9 confirmed was never used in any deployed or staging config (*"Confirm"*); SEED-00 forward-fixed it from the tree; it stays in history by design (plan Appendix A T0) | no (recorded) |
| (b) the operator's address | 10 lines in the range (4 new) | the 4 new lines are verbatim operator quotes in the three files plan §12 names | **no** (OD-27 = a) |
| (b) other e-mail-shaped strings | 61 hits, 13 addresses (+ Devin's bot identity on 5 lines) | project aliases, bot identities, test fixtures, organisations' public contacts | no |
| (b) the operator's name | 1,095 hits | commit-author columns, quotes, records already public | no |
| (b) `/Users/<username>` paths | 87 lines in 63 files | worktree/tool paths; the same pattern is public at `b051732c` (44×) | no |
| (b) phone numbers | 0 | — | — |
| (b) ArcGIS handles (C3 list) | 120 hits, 113 lines, 27 files | 8 files quote findings/research; **19 files go beyond them** | **yes — packet Q-2** |
| (b) ArcGIS owner usernames outside the C3 list | 2 individual-looking, 4 lines | new to the repository | **yes — packet Q-2** |
| (b) third-party personal GitHub accounts | 11 individual-looking accounts, 36 lines (6 of them already cited at `b051732c`) | public repos cited as data/tool sources (attribution) | no (listed) |
| (c) pointers to layers exposing plate reads / registrant PII | 12 lines, 5 files (+3 lines citing an official open dataset) | metadata only, rows never read — but the URLs index where such data sits | **yes — packet Q-1** |
| (c) plate numbers | 0 | 69 keyword lines, all search strings or descriptions | — |
| (c) officer names | 0 | 17 title hits: titles without names, a product name, two pre-existing fixture names | — |
| (c) named private individuals | 0 | the notes record "private person; not copied", "victim unnamed", "never names" | — |
| (c) resident/business camera-registrant data | 0 rows | 225 keyword hits describe programmes and block registrant data; the one registrant-PII layer URL is in (c)1 | (c)1 only |
| (c) precise private-residence locations | 0 confirmed | 1 street address quoted from the release search index (unverified kind), 1 public highway-camera coordinate | no (listed) |

## Verdict

**Needs redaction before the push — two items, decided by the operator (GATE-B packet Q-1 and Q-2); everything else is
safe to push under OD-27 = a ("publish as recorded").**

1. **(c)1 — the 12 lines in 5 planning files that carry service URLs of public layers holding plate reads, LPR hits,
   call-for-service rows and a camera registry's registrant PII** (list below). Recommended: a forward-fix commit that
   replaces each URL with `[layer URL withheld — Part VIII]`, keeping the finding ids, layer descriptions and field names;
   disclose in the seed PR body that the pushed history still holds them (packet Q-1 option a). The 3 lines citing
   Oakland's official per-read open dataset (ODC-By; already cited 3× in the public repo at `b051732c`) are not in the
   recommended redaction.
2. **(b)5–(b)6 — the ArcGIS handles.** Recommended: publish the 31 C3 ids as recorded (already public at `b051732c` in
   connector data and on the live site; P34.18 re-keys them), but include the two individual-looking owner usernames new
   to the repository in the same forward fix (packet Q-2 option a). The rule "only where the plan quotes findings" is not
   met as written (19 files go beyond the findings), so the operator's words are needed either way.

A forward fix cannot remove anything from the pushed history; only rewriting the local planning commits before the first
push can (packet Q-1 option b), at the cost of every commit id the seed's records cite.

## (a) Secrets

- `make scan-secrets` (2026-10-01T17:37:19Z): **exit 0** — "clean — 5279 file(s) scanned, 0 credential shapes found".
- `uv run python scripts/ci/secret_scan.py` over the 786 changed files: **exit 0** — "clean — 786 file(s) scanned, 0
  credential shapes found".
- Supplementary shapes over the 786 files: 0. Over the added lines of all 129 commits: the repo rules plus the
  supplementary list hit only `4df1552f` (`PD/review/PROTOCOL.md`) and `2cf03075` (`PD/review/R10_PREVIEW.md`), each one
  `sig-credential-literal` / `SIG_INTAKE_*` line — the C-9 value (see Counts). No other credential shape in the history.

## (b) Personal identifiers — full occurrence lists

#### (b)1 The operator's address (never written here; OD-27)

| file:line | new in the range? | class |
|---|---|---|
| `PD/META_PLAN.md:919` | yes | inside a verbatim operator quote, in one of the three files plan §12 names — **allowed (OD-27)** |
| `PD/META_PLAN.md:962` | yes | inside a verbatim operator quote, in one of the three files plan §12 names — **allowed (OD-27)** |
| `PD/baseline/TRACK0_RECORD.md:46` | yes | inside a verbatim operator quote, in one of the three files plan §12 names — **allowed (OD-27)** |
| `PD/feedback/OPERATOR_FEEDBACK.md:101` | yes | inside a verbatim operator quote, in one of the three files plan §12 names — **allowed (OD-27)** |
| `docs/build/BUILD_INDEX.md:188` | no | unchanged line, already public at `b051732c` (#190) |
| `docs/build/BUILD_INDEX.md:199` | no | unchanged line, already public at `b051732c` (#190) |
| `docs/build/LEDGER.md:429` | no | unchanged line, already public at `b051732c` (#190) |
| `docs/build/LEDGER.md:437` | no | unchanged line, already public at `b051732c` (#190) |
| `docs/build/LEDGER.md:552` | no | unchanged line, already public at `b051732c` (#190) |
| `docs/tickets/DEFERRALS.md:242` | no | unchanged line, already public at `b051732c` (#190) |

Total 10 lines: 4 new (all inside verbatim operator quotes in the three named files), the rest unchanged lines already public at `b051732c`; 13 further files hold it unchanged outside the range (run ledgers P26.x/P27.x, PR body P27.1). History check: the 129 commits add the address on exactly those 4 lines (no commit adds it anywhere it was later removed).

Devin's own commit identity (a vendor bot address, public in commit metadata) on 5 lines: `PD/findings/FINDINGS.csv:85`, `PD/findings/incoming/B5.csv:2`, `PD/research/B5-orchestration-retro.md:64`, `docs/build/tools/check_trailers.py:20`, `docs/build/tools/test_check_trailers.py:171` — not a person; no action.

#### (b)2 Other e-mail-shaped strings

| address | class | lines (file:line; *pre* = present at `b051732c`) |
|---|---|---|
| `contact@surveillancegraph.org` | the project alias planned as OP-10 (not a person) | 28: `PD/META_PLAN.md:136`, `PD/META_PLAN.md:956`, `PD/NEXT_PHASE_PLAN.md:1677`, `PD/data/decision_catalog.csv:7`, `PD/data/decision_catalog.csv:7`, `PD/data/decision_catalog.csv:304`, `PD/data/round11_plan.csv:269`, `PD/data/round11_plan.csv:367`, `PD/data/ticket_catalog.csv:187`, `PD/design/S1c-decision-catalog.md:187`, `PD/feedback/OPERATOR_FEEDBACK.md:101`, `PD/feedback/OPERATOR_FEEDBACK.md:119`, `PD/feedback/RATIFICATION_LOG.md:373`, `PD/reviews/REVIEW_CLOSURE.md:120`, `PD/tools/s6/s6_decisions.py:70`, `PD/tools/s6/s6_decisions.py:278`, `PD/tools/s6/s6_doc.py:183`, `PD/tools/s6/s6_doc.py:184`, `PD/tools/s6/s6_plan.py:217`, `PD/universe/UNIVERSE_DISPOSED.csv:1094`, `docs/adr/ADR-162-transparency-and-distribution.md:85`, `docs/adr/ADR-168-collection-conduct-gl-gate-08-re-confirmed-on-every-host.md:94`, `docs/adr/ADR-173-acquisition-waves-and-capacity.md:74`, `docs/adr/ADR-184-terms-conflicted-public-pages-fetch-envelope.md:70`, `docs/build/reports/OPERATING_MODE_R11.md:271`, `docs/build/runs/SEED-11b.md:68`, `docs/tickets/00_MANIFEST.md:79`, `docs/tickets/468_P37.44__mechanical-evaluation-report.md:9` |
| `noreply@anthropic.com` | Claude's co-author trailer (bot) | 10: `PD/NEXT_PHASE_PLAN.md:328`, `docs/adr/ADR-149-round-11-operating-model.md:98`, `docs/build/reports/OPERATING_MODE_R11.md:92`, `docs/build/runs/SEED-02b.md:35`, `docs/build/tools/check_trailers.py:16`, `docs/build/tools/check_trailers.py:17`, `docs/build/tools/check_trailers.py:78`, `docs/build/tools/test_check_trailers.py:36`, `docs/build/tools/test_check_trailers.py:124`, `docs/build/tools/test_check_trailers.py:200` |
| `t@example.invalid` | test fixture (reserved TLD) | 7: `docs/build/tools/test_check_trailers.py:47`, `docs/build/tools/test_check_trailers.py:204`, `docs/build/tools/test_check_trailers.py:238`, `docs/build/tools/test_ci_boundary.py:151`, `docs/build/tools/test_memory_guard.py:89`, `docs/build/tools/test_memory_guard.py:778`, `docs/build/tools/test_memory_guard.py:789` |
| `contact@eyesonflock.com` | a third-party project's public contact (organisation) | 4: `docs/2_canonical_design_spec.md:3791` *pre*, `docs/2_canonical_design_spec.md:8702` *pre*, `docs/research/_meta/spec_src/51_partIV_s22_registry.md:174` *pre*, `tests/unit/test_source_registry.py:268` *pre* |
| `noreply@github.com` | GitHub's bot identity in the trailer checker | 3: `docs/build/tools/check_trailers.py:28`, `docs/build/tools/check_trailers.py:83`, `docs/build/tools/test_check_trailers.py:302` |
| `sig-test@example.invalid` | test fixture | 2: `tests/unit/test_closeout_protocol.py:46` *pre*, `tests/unit/test_closeout_protocol.py:48` *pre* |
| `corrections@surveillancegraph.org` | a project alias named in a design note (not a person) | 1: `PD/META_PLAN.md:870` |
| `someone@example.invalid` | test fixture | 1: `docs/build/tools/test_check_trailers.py:199` |
| `devin@example.invalid` | test fixture | 1: `docs/build/tools/test_check_trailers.py:201` |
| `NOREPLY@anthropic.com` | test fixture of the trailer checker (bot) | 1: `docs/build/tools/test_check_trailers.py:356` |
| `Infoconnect@nzta.govt.nz` | a government agency's public contact | 1: `docs/tickets/DEFERRALS.md:160` |
| `contact@openstates.org` | an organisation's public contact | 1: `docs/tickets/DEFERRALS.md:192` *pre* |
| `open@stalbert.ca` | a municipality's open-data contact | 1: `docs/tickets/DEFERRALS.md:210` |

#### (b)3 The operator's name

1095 hits (1086 on lines new in the range). Already public: commit author metadata (478 of 480 Round 1–10 commits; TS-11) and the LEDGER/DEFERRALS/readouts at `b051732c`.

| file | lines | class |
|---|---|---|
| `PD/META_PLAN.md` | 135, 919, 924 | 919: a verbatim operator quote (§7.1); 135 and 924: the operator-decision register's record of U-014 (the operator approved their name + address as the contact string) |
| `PD/data/append_only_violations.csv` | 2–444, 452–540 | git `author` column of the append-only register (commit metadata, already public) |
| `PD/design/B4-verification.md` | 176 | quoting git author metadata or recorded text (findings, research) |
| `PD/feedback/OPERATOR_FEEDBACK.md` | 100–101 | inside verbatim operator quotes / the operator-decision register |
| `PD/findings/FINDINGS.csv` | 32, 38, 85 | quoting git author metadata or recorded text (findings, research) |
| `PD/findings/FINDINGS.md` | 109, 160 | quoting git author metadata or recorded text (findings, research) |
| `PD/findings/incoming/A1.csv` | 2 | quoting git author metadata or recorded text (findings, research) |
| `PD/findings/incoming/B5.csv` | 2 | quoting git author metadata or recorded text (findings, research) |
| `PD/research/B2-append-only.md` | 145 | quoting git author metadata or recorded text (findings, research) |
| `PD/research/B5-orchestration-retro.md` | 63 | quoting git author metadata or recorded text (findings, research) |
| `PD/research/E1-contradictions.md` | 90, 200, 205, 213 | quoting git author metadata or recorded text (findings, research) |
| `PD/reviews/S4-truth-safety.md` | 395 | quoting git author metadata or recorded text (findings, research) |
| `docs/3_sig_golive_spec.md` | 4 | pre-existing at `b051732c` |
| `docs/build/LEDGER.md` | 150, 234, 238, 437, 533 | 234 and 238: restored GATE DECISIONS rows (SEED-06) quoting the LEDGER's own history (public in git history); 150, 437, 533 unchanged since `b051732c` |
| `docs/build/readouts/ACCEPT-R8.md` | 46 | pre-existing at `b051732c` |
| `docs/build/readouts/HUMAN-H1.md` | 29 | pre-existing at `b051732c` |
| `docs/build/reports/memory-repair/append_only_register.csv` | 2–444, 452–540 | git `author` column of the append-only register (commit metadata, already public) |
| `docs/tickets/DEFERRALS.md` | 39–40 | pre-existing at `b051732c` |

#### (b)4 The operator's local username inside absolute paths (`/Users/<username>/…`)

87 lines (86 new) in 63 files; 44 occurrences in 24 files were already public at `b051732c` (e.g. the LEDGER's `buildWorktree`). Class: worktree and tool paths; already public pattern — no action recommended.

| file | lines |
|---|---|
| `PD/META_PLAN.md` | 5, 885 |
| `PD/baseline/BASELINE.md` | 33, 172, 195 |
| `PD/baseline/baseline.json` | 19, 95, 300–307 |
| `PD/design/B3-ledger-redesign.md` | 8 |
| `PD/design/B4-verification.md` | 7 |
| `PD/design/E4-rights-packets.md` | 398 |
| `PD/design/G2-activation.md` | 4 |
| `PD/design/G3-release-model.md` | 4 |
| `PD/design/H1-integration.md` | 8 |
| `PD/design/H2-branch-ci.md` | 9 |
| `PD/design/J3-transparency-design.md` | 4 |
| `PD/design/K11-research-queue.md` | 4 |
| `PD/design/K4-dossier-index.md` | 4 |
| `PD/design/K5-dossier-sources.md` | 4 |
| `PD/design/K7-watch.md` | 4 |
| `PD/design/K8-evidence.md` | 4 |
| `PD/design/K9-sources-table.md` | 4 |
| `PD/design/L3-confidence-program.md` | 4 |
| `PD/design/S1c-decision-catalog.md` | 4 |
| `PD/design/S2-round-structure.md` | 5 |
| `PD/findings/FINDINGS.csv` | 70 |
| `PD/findings/incoming/B3.csv` | 5 |
| `PD/research/B5-orchestration-retro.md` | 7 |
| `PD/research/B6-skill-proposals.md` | 9, 1573 |
| `PD/research/B7-harness-attribution.md` | 7 |
| `PD/research/F5-eng-debt.md` | 4 |
| `PD/research/L1-pipeline-audit.md` | 4 |
| `PD/research/L2-graph-quality.md` | 4 |
| `PD/review/DATA_TRUTH.md` | 4 |
| `PD/review/PROTOCOL.md` | 4, 354, 399, 527 |
| `PD/review/R10_PREVIEW.md` | 4 |
| `PD/review/REVIEW_SYNTHESIS.md` | 4 |
| `PD/stageB/AGENT_BRIEF.md` | 8 |
| `PD/tools/s6/s6_catalog.py` | 5 |
| `PD/tools/s6/s6_decisions.py` | 10 |
| `PD/tools/s6/s6_doc.py` | 10 |
| `PD/tools/s6/s6_plan.py` | 6 |
| `docs/build/LEDGER.md` | 40, 275, 323 |
| `docs/build/reports/memory-repair/LEDGER_head_R01-R10.txt` | 10, 14, 27, 44 |
| `docs/build/runs/SEED-01-04-06-07.md` | 13 |
| `docs/build/runs/SEED-02a.md` | 6 |
| `docs/build/runs/SEED-02b.md` | 6 |
| `docs/build/runs/SEED-02c.md` | 10 |
| `docs/build/runs/SEED-03.md` | 10 |
| `docs/build/runs/SEED-05-10-16.md` | 12, 46, 120 |
| `docs/build/runs/SEED-08-09.md` | 8 |
| `docs/build/runs/SEED-11a.md` | 9 |
| `docs/build/runs/SEED-11c.md` | 9 |
| `docs/build/runs/SEED-11d.md` | 6 |
| `docs/build/runs/SEED-12a.md` | 8 |
| `docs/build/runs/SEED-12b.md` | 8 |
| `docs/build/runs/SEED-12c.md` | 8 |
| `docs/build/runs/SEED-13a.md` | 8 |
| `docs/build/runs/SEED-13b.md` | 9 |
| `docs/build/runs/SEED-13c.md` | 9 |
| `docs/build/runs/SEED-13d.md` | 8 |
| `docs/build/runs/SEED-13e.md` | 11 |
| `docs/build/runs/SEED-14a.md` | 8 |
| `docs/build/runs/SEED-14b.md` | 8 |
| `docs/build/runs/SEED-15.md` | 8 |
| `docs/build/runs/SEED-17.md` | 11 |
| `docs/build/runs/SEED-18a.md` | 8 |
| `docs/tickets/221_P34.18__personal-handle-source-id-rename.md` | 41 |

#### (b)5 Personal-looking ArcGIS handles (the 31 `camreg_*` ids of F-097/F-131)

Reported by index `H01…H31` into the gitignored list `docs/build/logs/next-phase/C3/personal_like_ids.txt` (the values are not repeated here). `id` = the full `camreg_<handle>` id; `token` = the bare handle (≥ 5 characters, word-bounded). All 31 ids were already public at `b051732c` in the connector registry data and on the live site; P34.18 re-keys them.

| file | lines (handle indices) | where the plan quotes findings? |
|---|---|---|
| `PD/data/candidates_I3.csv` | 2 (H06); 35 (H06) | **no — beyond the findings quotes** |
| `PD/data/candidates_I5.csv` | 86 (H06) | **no — beyond the findings quotes** |
| `PD/data/candidates_consolidated.csv` | 239 (H06); 469 (H06); 495 (H06) | **no — beyond the findings quotes** |
| `PD/data/query_log_I3.csv` | 13 (H06); 17 (H06) | **no — beyond the findings quotes** |
| `PD/data/query_log_I5.csv` | 55 (H06) | **no — beyond the findings quotes** |
| `PD/data/redistribution.csv` | 206 (H01); 214 (H02); 224 (H04); 226 (H03); 229 (H05); 235 (H06); 242 (H31); 246 (H30); 253 (H07); 254 (H08); 260 (H09); 264 (H10); 266 (H11); 267 (H12); 268 (H13); 270 (H14); 280 (H15); 287 (H16); 288 (H17); 289 (H18); 291 (H19); 305 (H20); 306 (H21); 309 (H22); 311 (H23); 316 (H24); 317 (H25); 332 (H26); 335 (H27); 337 (H28); 340 (H29) | **no — beyond the findings quotes** |
| `PD/data/source_coverage.csv` | 206 (H01); 214 (H02); 224 (H04); 226 (H03); 229 (H05); 235 (H06); 242 (H31); 246 (H30); 253 (H07); 254 (H08); 260 (H09); 264 (H10); 266 (H11); 267 (H12); 268 (H13); 270 (H14); 280 (H15); 287 (H16); 288 (H17); 289 (H18); 291 (H19); 305 (H20); 306 (H21); 309 (H22); 311 (H23); 316 (H24); 317 (H25); 332 (H26); 335 (H27); 337 (H28); 340 (H29) | **no — beyond the findings quotes** |
| `PD/design/E2-governance-options.md` | 717 (H01) | yes — findings/research quoting them |
| `PD/design/K10-source-pages.md` | 72 (H01); 189 (H01) | yes — findings/research quoting them |
| `PD/findings/FINDINGS.csv` | 187 (H01); 196 (H01); 404 (H23) | yes — findings/research quoting them |
| `PD/findings/incoming/E1.csv` | 5 (H01); 14 (H01) | yes — findings/research quoting them |
| `PD/findings/incoming/J4.csv` | 2 (H23) | yes — findings/research quoting them |
| `PD/research/E1-contradictions.md` | 449 (H01); 480 (H01) | yes — findings/research quoting them |
| `PD/research/I1-source-coverage.md` | 323 (H01,H17,H18); 355 (H06); 364 (H15); 376 (H30); 380 (H04); 386 (H01); 402 (H19); 404 (H22); 449 (H21,H24); 450 (H09); 451 (H23); 463 (5 handles); 464 (H12); 465 (H08); 466 (H10); 479 (H06) | yes — findings/research quoting them |
| `PD/research/J4-redistribution-matrix.md` | 189 (H23); 222 (H23); 248 (H23) | yes — findings/research quoting them |
| `PD/stageB/CARRY.md` | 12 (H01) | **no — beyond the findings quotes** |
| `PD/stageB/T3_contract_map.csv` | 155 (H01) | **no — beyond the findings quotes** |
| `PD/tools/s13/gen_t3.py` | 462 (H01) | **no — beyond the findings quotes** |
| `docs/adr/ADR-169-rights-basis-with-guardrails-gl-gate-07-re-confirmed.md` | 137 (H01) | **no — beyond the findings quotes** |
| `docs/build/runs/SEED-11c.md` | 56 (H01) | **no — beyond the findings quotes** |
| `docs/build/runs/SEED-13a.md` | 32 (H01) | **no — beyond the findings quotes** |
| `docs/build/runs/SEED-13d.md` | 116 (H01) | **no — beyond the findings quotes** |
| `docs/build/runs/SEED-14a.md` | 15 (H01) | **no — beyond the findings quotes** |
| `docs/tickets/00_MANIFEST.md` | 906 (H01) | **no — beyond the findings quotes** |
| `docs/tickets/246_P34.38__sources-pilot-prep-and-registry-rows.md` | 68 (H01) | **no — beyond the findings quotes** |
| `docs/tickets/350_P36.2__rights-flip-decline-batch-and-terms-capture.md` | 20 (H01) | **no — beyond the findings quotes** |
| `docs/tickets/DEFERRALS.md` | 925 (H01) | **no — beyond the findings quotes** |

Totals: 120 hits on 113 lines in 27 files; 19 of those files are outside the findings/research notes.

#### (b)6 ArcGIS owner usernames outside the C3 list

Found as `owner <name>` strings in the I5 candidate notes. Seven are agency accounts (VTrans, MDOT, NDOT, CTDOT, Iowa DOT,
Providence GIS and a TxDOT org) — not persons. **Two look like individuals' account names** and are new to the repository
(0 occurrences at `b051732c`); reported by position, not value:

| id | lines | context |
|---|---|---|
| O-1 (an individual-style username inside a TxDOT org) | `PD/data/candidates_I5.csv:9`, `PD/data/candidates_consolidated.csv:443` | owner of a TxDOT ITS device layer |
| O-2 (an individual-style username inside a city org) | `PD/data/candidates_I5.csv:37`, `PD/data/candidates_consolidated.csv:487` | Hub owner of a city data platform |

The owner string of H01's registry (an individual-style username) is in `PD/data/source_coverage.csv:206` and was already
public 9× at `b051732c` (connector notes).

#### (b)7 Third-party individuals' public accounts cited as sources

| account (public GitHub unless noted) | lines | at `b051732c` |
|---|---|---|
| kevincollier (a journalist's repo) | `PD/data/candidates_I4.csv:97`, `PD/data/candidates_consolidated.csv:542`, `PD/data/query_log_I4.csv:320`, `:327` | 2 |
| rxsklife | `PD/data/candidates_I3.csv:66`, `PD/data/candidates_consolidated.csv:426`, `PD/data/query_log_I3.csv:160` | 0 |
| ksualprs | `PD/data/candidates_I3.csv:64`, `PD/data/candidates_consolidated.csv:368`, `PD/data/query_log_I3.csv:158`, `PD/design/I7-rights-packets.md:572` | 1 |
| rhowardstone | `PD/data/candidates_I3.csv:65`, `PD/data/candidates_consolidated.csv:667`, `PD/data/query_log_I3.csv:162`, `PD/design/I7-rights-packets.md:303` | 1 |
| jdmediallc | `PD/data/candidates_I3.csv:68`, `PD/data/candidates_consolidated.csv:685`, `PD/data/query_log_I3.csv:159` | 0 |
| StickyHashTr33 | `PD/data/candidates_I3.csv:67`, `PD/data/candidates_consolidated.csv:433`, `PD/data/query_log_I3.csv:161`, `PD/design/I7-rights-packets.md:601` | 0 |
| simeononsecurity | `PD/data/redistribution.csv:91`, `docs/2_canonical_design_spec.md:3941`, `:4011`, `tests/unit/test_source_registry.py:185` | 19 |
| none-below | `PD/data/redistribution.csv:97`, `PD/data/source_coverage.csv:97`, `docs/2_canonical_design_spec.md:4007`, `:4022`, `tests/unit/test_source_registry.py:191` | 17 |
| colonelpanichacks | `docs/2_canonical_design_spec.md:3942` | 6 |
| lucaong (a library author) | `PD/data/query_log_K12a.csv:94`, `PD/research/K12a-prior-art.md:572` | 0 |
| hyperknot (a map-tiles project author) | `PD/data/query_log_K12a.csv:91`, `PD/research/K12a-prior-art.md:569` | 0 |

Organisations, not persons: FoggedLens (DeFlock), SouthFLPrivacyAdvocates, Cantica-Systems, eye-on-surveillance,
eyes-off, and the `deflock-redmond` Bluesky account (`docs/2_canonical_design_spec.md:3966`, public 6× at `b051732c`).
Class: attribution of public repositories the research read; no action recommended.

#### (b)8 Phone numbers — 0

US (`NXX-NXX-XXXX` and bracketed forms) and international (`+cc …`) patterns: no hit in the 786 files; a looser
digit-group check also found none outside dates and ids.

#### (b)9 Other handle shapes

- `@`-tokens in Markdown/CSV (341): commit/ref anchors (`@b051732c` 264, `@PRE` 33), npm scopes (`@emnapi`, `@types`,
  `@astrojs`, `@playwright`), CSS at-rules (`@media`, `@page`), viewport labels (`@mobile`, `@reflow320`), sqitch tags
  (`@tag`, `@r11-sqitch-hygiene`), placeholder domains (`@sig.example`) and one bot address fragment — **no personal
  handle**.
- The repository slug `SteveVitali/…` (118 lines, 30 new): the public repo's own URL — already public (149× at
  `b051732c`).

## (c) Part VIII — full candidate lists

#### (c)1 Pointers to public layers that expose plate reads, LPR hits, call-for-service rows or registrant PII — **needs a decision (packet Q-1)**

Each line carries the service URL; the descriptions come from the line itself ("rows never read", metadata only).

| file:line | finding / item | what the layer's schema holds (per the note) |
|---|---|---|
| `PD/data/candidates_I3.csv:37` | I3-C036 (HAZARD, BLOCK) | Flock search results in a city GIS org: plate, capture time, network, camera, lat/lon (also names five sibling layers) |
| `PD/data/candidates_I3.csv:86` | I3-C085 | a town's camera-registry layer: registrant first/last name, address, phone, e-mail |
| `PD/data/candidates_consolidated.csv:446` | I7 copy of I3-C036 | as above |
| `PD/data/candidates_consolidated.csv:522` | I7 copy of I3-C085 | as above |
| `PD/data/query_log_I3.csv:41` | I3-F020 | Flock search results (city GIS org): plate, capture time, network, camera, lat/lon |
| `PD/data/query_log_I3.csv:42` | I3-F021 | Flock search results (a town account): the same + image file names |
| `PD/data/query_log_I3.csv:53` | I3-F032 | a fusion-centre "LPR Hits" layer (2016–17; obfuscated fields) |
| `PD/data/query_log_I3.csv:55` | I3-F034 | a vendor-hosted "LPR Hits" layer: camera, plate, vehicle, hotlist reason, timestamp, address |
| `PD/data/query_log_I3.csv:57` | I3-F036 | an LPR-named layer holding call-for-service rows (call time, nature, business, street) |
| `PD/data/query_log_I3.csv:206` | I3-F102 | the town camera-registry layer (registrant PII fields) |
| `PD/findings/FINDINGS.csv:331` | F-330 (S1, part-viii) | two of the URLs above (city Flock search results; town registry) |
| `PD/findings/incoming/I3.csv:2` | I3:NEW-1 = F-330 | the same two URLs |

Not in the recommended redaction (an official open dataset, ODC-By, already cited 3× in the public repo at
`b051732c`): Oakland's per-read ALPR views — `PD/data/candidates_I3.csv:38`, `PD/data/candidates_consolidated.csv:460`,
`PD/data/query_log_I3.csv:83`.

#### (c)2 Plate numbers — 0

70 licence-plate keyword hits (13 files; 69 new) are search strings, programme descriptions and statute citations; every
plate-shaped token on a plate/VRM/hotlist line was a document or programme id (`287(g)` counts, `SRC-`/`GEO-` ids, `ADR124`,
`GET 2026`), none a plate.

#### (c)3 Officer names — 0

17 title-pattern hits, none a named officer: `PD/data/candidates_I3.csv:78`, `PD/data/candidates_I4.csv:41`, `:88`,
`PD/data/candidates_consolidated.csv:2` (3), `:225` (2), `:565`, `PD/design/I7-rights-packets.md:537` (titles such as
"Chief Procurement Officer" with no name); `PD/data/query_log_I9b.csv:142` ("Sheriff Policy 610"), `:166` (a forensic
product name), `PD/findings/FINDINGS.csv:97` and `PD/findings/incoming/C2.csv:2` ("County Sheriff" + a confidence
label), `PD/research/I3-alpr-networks.md:269` ("County Sheriff" + a vendor); `docs/build/runs/P31.5.md:107` (2, fixture
names in a landed run ledger, pre-existing).

#### (c)4 Named private individuals — 0

No honorific + name hit; contexts naming victims, defendants, residents or misidentified people say they were not copied
(`PD/data/candidates_I9b.csv:56` / `PD/data/candidates_consolidated.csv:608` "private person; not copied";
`PD/data/candidates_I5.csv:148` / `:635` of the consolidated file "victim unnamed"; `PD/data/candidates_I3.csv:89` "never
names").

#### (c)5 Resident/business camera-registrant data — 0 rows

225 keyword hits in 38 files (most: `PD/data/candidates_consolidated.csv` 95, `PD/data/candidates_I9a.csv` 31,
`PD/data/candidates_I3.csv` 19, `PD/data/candidates_I5.csv` 10, `PD/design/I7-rights-packets.md` 7) describe registry
programmes and their screens ("programme-level facts only; registrant data never", "BLOCK rows", risk tags such as
`private-registrant-location`). No registrant name, address, phone or location is copied. Programme pages of agencies'
voluntary camera registries are cited by URL (public programme pages, not data). The one pointer to an exposed registrant
layer is in (c)1.

#### (c)6 Precise private-residence locations — 0 confirmed

- Street-address pattern, 8 hits: five are company or document names ("Babel Street" ×3, "EFF Street-Level", an Arkansas
  regulation number) — `PD/data/candidates_I4.csv:100`, `:150`, `PD/data/coverage_delta_F2a.csv:24`,
  `PD/data/query_log_I9a.csv:81`, `PD/data/query_log_I9b.csv:258`; **three quote one street address** returned by the
  release search for an Australian Capital Territory record — `PD/design/K3-search.md:138`, `PD/findings/FINDINGS.csv:462`,
  `PD/findings/incoming/K3.csv:2`. *(Agent reading, unverified:)* the record is a site in the published release's ACT
  compartment (the K3 index was built from release data), so the address is already public on the release; this scan did
  not verify whether the site is a private residence. Listed for the orchestrator; no redaction recommended unless the
  record is found to be one.
- Coordinate pairs (5 decimals), 3 hits — `PD/findings/FINDINGS.csv:105`, `PD/findings/incoming/C2.csv:10`,
  `PD/review/C2_PAGE_INDEX.csv:100`: one Iowa interstate traffic camera (I-80, mile marker 82.5) from the live map's own
  table — public infrastructure.

## This unit's files (scanned from the working tree before the orchestrator's commit)

| file | (a) secrets | (b) identifiers | (c) Part VIII |
|---|---|---|---|
| `PD/HANDOFF.md` | 0 | 7 `/Users/<username>` worktree paths (the resume prompt needs the path) | 0 |
| `PD/baseline/DELTA_T6.md` | 0 | 0 (the three pushes are described as "authored with the operator's identity"; no address, no name) | 0 |
| `PD/stageB/GATEB_PACKET.md` | 0 | 0 (handles referred to as "the 31 `camreg_*` ids", no value) | 0 (layer pointers described, no URL) |
| `PD/stageB/PREPUSH_SCAN.md` (this file) | 0 | 0 values: the operator's address never written; handles by index; owner usernames by position; third-party GitHub account names of (b)7 only (public repos) | 0 URLs of the (c)1 layers |
| `docs/build/runs/SEED-18b.md` | 0 | 1 worktree path | 0 |
| `docs/build/reports/current/*` (regenerated) | 0 | derived from DEFERRALS/LEDGER text already in the range: the worktree path (1), the operator's name (3 hits, from DEFERRALS rows public at `b051732c`), three organisations' public addresses, one H01 id (from the DEFERRALS row listed in (b)5) | 0 |

Repo gate over these files: `uv run python scripts/ci/secret_scan.py <files>` exit 0 (§ Checks of
`docs/build/runs/SEED-18b.md`).

## What to re-run after a redaction commit

`make scan-secrets`; `uv run python scripts/ci/secret_scan.py $(git diff --name-only b051732c..HEAD)`; the URL check of
(c)1 (`git grep -nE 'arcgis\.com/[A-Za-z0-9]+/arcgis/rest/services/([A-Za-z0-9_]*(Search_Results|LPR_Hits|LPR_Data|Registered)|RF9Vk)' HEAD -- docs/build/planning`
must print nothing); `python3 docs/build/tools/current_projection.py generate` then `verify` if a projection input
changed; the Appendix A T6 validators.
