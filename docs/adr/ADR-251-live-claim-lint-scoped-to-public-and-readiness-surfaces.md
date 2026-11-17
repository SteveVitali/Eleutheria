# ADR-251 — The live-claim lint is scoped to public and readiness surfaces (P37.61d)

- Date: 2026-11-16
- Status: accepted (engineering; lint policy only — no control-state writes)
- Ticket: P37.61d (Round 11 / P37, sub-round 11D, manifest row 489d — on
  `r11/P37.61d-live-claims-rescope`)
- Base: `r11/P37.61c-projection-out-of-commit-path` (`e7798f0a`)
- Authority: operator **RULING E-3**, recorded verbatim in
  `docs/build/LEDGER.md` GATE DECISIONS (2026-11-15, channel interactive)
  and `docs/build/readouts/RULINGS-2026-11-15.md`
- Relates: ADR-199 (the SIG-MEM-011 binding's record-check family), ADR-218
  (the `[[carried]]` provenance mechanism — unchanged; its seeded entry is
  now dead configuration, recorded below), SIG-MEM-011

## Context

P35.3 bound **SIG-MEM-011**: no unevidenced assertion of production state.
`check_live_claims.py` classifies markdown segments on the corpus listed in
`docs/build/tools/record_policy/live_claims.toml`; a segment asserting a
production claim (`deployed` / `live` / `hosted` / `publicly` / `production` /
`operational` / …) with no same-segment disclosure or denial must cite a
`sig.probe-run/1` record fresh at its commit. Two legs enforce it: the corpus
leg judges every globbed file by blame time, and the range leg judges every
claim a diff *adds* on a corpus path.

The defect RULING E-3 names: the corpus reached **build-memory meta-text** —
`docs/build/LEDGER.md`, `docs/build/reports/**/*.md`,
`docs/build/runs/**/*.md` and (through the run-ledger and PHASE LOG records)
the whole committed machine state. Run ledgers and PHASE LOG entries describe
live legs as a matter of course — *queued* legs, `prepared_not_executed`
packets, repair arcs that quote the vocabulary itself ("same-segment live-claim
rewords"), deferral rows whose owner/trigger cells name `live` dispatch
surfaces, and branch names (`r11/P36.68-live-<n>`). Their evidence is already
governed by the run-ledger and live-leg rules (the live-leg declaration,
`prepared_not_executed`, the seed-commit protocol); a probe-citation lint on
top added a second, wrong instrument. Twenty-three recorded false positives
were repaired forward one at a time — the *repair* vocabulary ("queued",
"remains", `pre-authorised`, `unreleased`, code-spanning the assert token)
grew around each hit, and the next meta-text line fired again.

The operator's RULING E-3 (2026-11-15) settles the direction: keep the
SIG-MEM-011 guarantee on the surfaces it exists for — public and readiness
prose — and stop it firing on build memory.

## Decision

1. **The corpus is rescoped to public and readiness surfaces only.** One list
   (`[surfaces].corpus` in `live_claims.toml`) drives both legs — the corpus
   leg globs it, the range leg matches every added-line path against it —
   so the single edit rescopes both. The pinned globs:

   | glob | surface | matched at pin time |
   |---|---|---|
   | `README*` | root README (the ruling's literal `README*` — `pathlib` matches root only) | 1 file |
   | `db/README*`, `docs/README*`, `docs/evaluation/README*`, `docs/governance/README*`, `docs/research/README*`, `evidence/README*`, `ops/README*`, `ops/*/README*`, `web/README*` | committed package READMEs (no brace expansion in `pathlib`, so named explicitly) | 9 files |
   | `docs/ops/*readiness*` | the ruling's readiness glob — **matches nothing today**; kept verbatim for the day a readiness doc lands under `docs/ops/` | 0 files |
   | `docs/build/OPERATIONAL_READINESS.md` | the explicit readiness carve-out — the real readiness doc lives inside the excluded `docs/build/**` | 1 file |
   | `docs/ops/**/*.md` | the maintained ops surface (P35.4's runbook coverage, carried) | 2 files |

   The corpus leg at pin time: **14 files, 3528 segments, 113 claims, all
   grandfathered, 0 violations** — green at HEAD as the contract requires.

2. **Build memory and ticket records leave the corpus.**
   `docs/build/**` (LEDGER, BUILD_INDEX, `runs/`, `reports/`, `pr/`,
   `readouts/`, `fixtures/`, `logs/`) and `docs/tickets/**` carry no glob.
   Their production-state prose stays governed by the instruments that own it:
   the run-ledger declaration, `prepared_not_executed`, the live-leg dispatch
   records, and the obligation-event chain — never by a prose lint.
   `docs/adr/**` is likewise out: ADR bodies are decision records that cite
   their own evidence, and `docs/adr/README.md` is a *generated* index —
   regenerated prose is the class the lint never held (same disposition as the
   generated projections the corpus never carried).

3. **Two ruling-named surfaces are deferred, with the basis measured.** The
   ruling's corpus list named "the web copy" and "release notes and announce
   material". At pin time `web/src/**/*.astro` carries **29** claim-shaped
   post-activation lines and `CHANGELOG*`/`ANNOUNCE*` carries **32** — every
   one a genuine prose production-state statement written before any
   `sig.probe-run/1` citation grammar could apply to it. The citation grammar
   cannot bind retroactively (a record `generated_at` within 24 h of the
   line's commit cannot exist for committed copy), so including the surfaces
   would make the corpus leg red at HEAD — the opposite of the contract's
   green-at-HEAD acceptance. They are therefore deferred as
   **`D-P37.61d-1`** (OPEN): the operator decides whether those surfaces are
   remediated into coverage (respell + cite) or formally ruled out. Nothing
   about the guarantee changes meanwhile — the surfaces were never corpus
   before E-3 either.

4. **Seven package-README claim lines are respelled by the sanctioned
   code-span convention** so the package READMEs the ruling named can enter
   the corpus green: `db/README.md` ×2 (`live` → `` `live` ``),
   `ops/README.md` ×3 (`hosted` → `` `hosted` ``; "capture live under" →
   "capture sits under"), `ops/gcp/README.md` ×1, `ops/monitoring/README.md`
   ×1. Each respell marks a term-of-art token as code — the same convention
   the historical repairs used — never a weakened assertion.

5. **The detector is byte-for-byte unchanged** — segmentation, assert/negate
   classification, the probe-run citation rule (committed + remote forms,
   ≤ 24 h freshness at commit), the grandfathering mechanism, the
   `[[carried]]` provenance rule (ADR-218), and all exit codes stand. One
   consequence is recorded, not changed: the seeded `[[carried]]` entry
   `commit e324b22c` ← `source 8e3a0356` (ADR-218's first entry) becomes
   **dead configuration** — the file it protected is a build-memory record
   no glob reaches. It is kept (still valid, still loadable); removing it
   would be config churn with no behavioural difference.

6. **The 23 recovered false positives are committed as negative fixtures**
   — `docs/build/fixtures/live_claims_false_positives.json`, each line
   verbatim at the path that recorded it. `test_check_live_claims.py`
   asserts: all 23 exit clean under the shipped policy (corpus + range legs);
   every line still claim-shaped under today's vocabulary **fails** when
   placed on a public surface (the guarantee moved, not the vocabulary);
   genuine unevidenced production assertions fail on each held surface
   family; and the corpus covers `README*`/the readiness carve-out/
   `docs/ops/**` while covering no `docs/build/**` or `docs/tickets/**` path.

### The 23 recovered false positives

Each row is the verbatim committed line (or its recorded hunk line), the path
that recorded it, and its evidence source — `docs/build/reports/memory-repair/`
archives hold the pre-repair bytes byte-for-byte.

| # | surface | fired phrase (verbatim) | evidence |
|---|---|---|---|
| FP-01 | `docs/build/runs/P35.23.md` L158 | "read-only live/offline diff, `rollback` name-checked" | `memory-repair/P35.23run_L158_L200_L224_pre-P35.23-liveclaim.txt` |
| FP-02 | `docs/build/runs/P35.23.md` L200 | "\"same-segment live-claim rewords\" segment carried `\blive\b` with" | same archive |
| FP-03 | `docs/build/runs/P35.23.md` L224 | "**Live-executed** (AC-3): the scheduled restricted lane is" | same archive |
| FP-04 | `docs/tickets/DEFERRALS.md` L1416 | "a capture ticket under the connector-live sweep" | `memory-repair/DEFERRALS_L1416_pre-P35.23-liveclaim.txt` |
| FP-05 | `docs/build/reports/obligations/events.jsonl` L687 | `D-P35.23-2:e0` migration event — "connector-live sweep" owner text | `memory-repair/events_L687_pre-P35.23-liveclaim.txt` |
| FP-06 | `docs/tickets/DEFERRALS.md` L1495 | "the OM-19 leg-runner — the orchestrator's live dispatch" | `memory-repair/DEFERRALS_L1495_pre-P36.33-liveclaim.txt` |
| FP-07 | `docs/build/reports/obligations/events.jsonl` L710 | `D-P36.33-1:e0` migration event — "the orchestrator's live dispatch" owner text | `memory-repair/events_L710_pre-P36.33-liveclaim.txt` |
| FP-08 | `docs/build/LEDGER.md` L1261 | "kind-vocabulary fold … same-segment live-claim rewords" | `memory-repair/LEDGER_phaselog_L1261_pre-P35.23-liveclaim.txt` |
| FP-09 | `docs/tickets/DEFERRALS.md` `D-P36.68-1` | `r11/P36.68-live-<n>` branch token (repair renamed it `-mirror-`) | `memory-repair/DEFERRALS_D-P36.68-1_pre-P36.68-liveclaim-respell.txt` |
| FP-10 | `docs/tickets/DEFERRALS.md` `D-P37.4a-1` | "the leg's cosign verify finds ≥1 signature per deployed digest" | `memory-repair/DEFERRALS_D-P37.4a-1_pre-P37.4a-liveclaim-respell.txt` |
| FP-11 | `docs/build/LEDGER.md` L1287 | "leg B (first real wire) held … leg-b-packet live-claim negation" | `memory-repair/LEDGER_L1287_phaselog_pre-P36.77-liveclaim.txt` |
| FP-12 | `docs/build/LEDGER.md` L1702 | "`blockedOn` carried ancestors verbatim … uncited live claim" | `memory-repair/LEDGER_L1702_pre-P37.43-liveclaim.txt` |
| FP-13 | `docs/build/LEDGER.md` L1503 | "fix arc: describedby pin … + live-claim phrasing" | `memory-repair/LEDGER_phaselog_L1503_pre-P36.66a-liveclaim-respell.txt` |
| FP-14 | `docs/build/LEDGER.md` L1508 | "committed-line live-claim respell (archived, seed-commit declared)" | `memory-repair/LEDGER_phaselog_L1508_pre-P36.67-liveclaim-respell.txt` |
| FP-15 | `docs/build/LEDGER.md` L1518 | "carried waived-ancestor reds #432@444a679 + #434@2633dd8 + #435@03dc29f" | `memory-repair/LEDGER_phaselog_L1518_pre-P36.69-liveclaim-respell.txt` |
| FP-16 | `docs/build/LEDGER.md` L1522 | "inherited `bd90b169` matrix+live-claim reds repaired forward" | `memory-repair/LEDGER_phaselog_L1522_pre-P36.72a-liveclaim-respell.txt` |
| FP-17 | `docs/build/LEDGER.md` L1537 | "sub-round 11C acceptance — live-read sweep" | `memory-repair/LEDGER_phaselog_L1537_pre-P36.73-liveclaim-respell.txt` |
| FP-18 | `docs/build/LEDGER.md` L1780 | "generated-vs-deployed schema conformance" | `memory-repair/LEDGER_phaselog_L1780_pre-P37.58-liveclaim-respell.txt` |
| FP-19 | `docs/build/runs/P37.41.md` L54 | "CI's hosted run green" | `memory-repair/runs_P37.41_L54_pre-P37.42-liveclaim.txt` |
| FP-20 | `docs/build/runs/P37.42.md` L51 | "run-ledger live-claim respell … recorded verbatim" | `memory-repair/runs_P37.42_L51_pre-P37.43-liveclaim.txt` |
| FP-21 | `docs/build/LEDGER.md` L1242 | "the first live run is P37.2's" | `memory-repair/LEDGER_phaselog_L1242_pre-P37.1.txt` `[1]` base bytes at `ae9e02ef`; repaired forward by `024eca86` ("remains queued") |
| FP-22 | `docs/build/LEDGER.md` L1256 | "hosted read-only partner-name audit" | line as committed at `ff268902`; in-place segment-negation repair `1aef6b8d` (seed-commit `85a1e7ac`) — the archive file for this repair was committed empty, bytes recovered from `1aef6b8d^` |
| FP-23 | `docs/build/LEDGER.md` L1528 | dispatch boundary-confirm "outside AR-3" live-window phrasing | `memory-repair/LEDGER_phaselog_L1528_pre-P36.72b-livewindow-respell.txt`; repair `736be305` |

Three lines (FP-05, FP-07, FP-09) no longer classify as claims under today's
vocabulary — the negate list grew around them (`queued`,
`prepared_not_executed`, `pre-authorised`). They are still exercised as
negative fixtures (non-coverage) and the fixture record marks
`still_claim_shaped` per line.

## Consequences

- SIG-MEM-011 keeps its force exactly where it belongs: an unevidenced
  production-state assertion on a README, the readiness doc, or the ops
  surface fails — corpus and range legs alike, unchanged mechanics.
- Build memory stops paying the respell tax: run ledgers, PHASE LOG entries,
  deferral owner/trigger cells, and repair prose describe live legs in
  natural language without tripping a lint that was never their instrument.
- The 23 historical false positives are now regression fixtures — the rescope
  cannot silently revert.
- `D-P37.61d-1` records the two ruled-but-unpinned surfaces (web copy,
  release notes/announce material) as owed operator scope: 29 + 32
  claim-shaped post-activation lines measured at pin time.
- The range leg inherits the rescope for free — both legs read the one list.

## Alternatives considered

- **Keep the corpus; narrow the vocabulary.** Rejected — the firing text is
  not a vocabulary accident: meta-text legitimately says "live leg",
  "hosted run", "the first live run is P37.2's". Every narrowing lands on
  the same wall the 23 repairs hit, and each widened negate silently weakens
  the guarantee on the surfaces that need it.
- **Keep the corpus; exclude paths by deny-list.** Rejected — a second list
  to drift apart from the first; the ruling names the *included* surfaces,
  and a positive corpus is the auditable statement of what the lint judges.
- **Include `CHANGELOG*`/`web/src/**/*.astro` now and remediate.** Rejected —
  61 post-activation claim-shaped lines with no lawful retroactive citation;
  respelling release history falsifies the record's own prose, and the
  contract's green-at-HEAD acceptance forbids landing a red corpus. Deferred
  openly instead (`D-P37.61d-1`).
- **Exclude `docs/adr/**` silently.** Recorded instead: ADR bodies are
  evidence-citing decision records and the index is generated — both are
  classes the lint never held; naming the exclusion keeps it auditable.

## Revisit trigger

- **A new public or readiness surface lands** (a `docs/ops/*readiness*`
  doc, a committed announce doc, new package READMEs): add its glob in the
  same change and record it here — the corpus is the auditable surface list.
- **`D-P37.61d-1` resolves:** when the operator rules the web copy and
  release-notes surfaces in or out, their globs (or their recorded
  exclusion) land with the ruling cite — the deferral, not silence, is the
  seam.
- **A false positive on a held surface:** if the corpus fires on
  non-claim prose *inside* the public/readiness set, the fix is
  vocabulary-level (assert/negate or code-span convention), never
  corpus shrinkage below the ruling's floors — a new ADR records it.
- **The detector or citation rule changes:** this ADR pins the corpus
  *scope*; any change to `check_live_claims.py` mechanics is a separate
  decision and its own ADR.
