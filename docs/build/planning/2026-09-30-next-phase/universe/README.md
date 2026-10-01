# Work universe (row A3): the obligation universe, extracted mechanically

`UNIVERSE.csv` holds **one row per source item** that Round 11 must give exactly one disposition
(META_PLAN §3 P9, §8.1). Row **A3** built it on 2026-09-30 (`date -u` 16:54:46Z), and it is
read-only over the repository. The control files it reads are byte-identical to the A1 baseline:
`--check` compares their sha256 against `baseline/baseline.json` and reports "all tracked control
files match A1". S1 fills the columns A3 leaves empty (`disposition`, `disposition_ref`,
`rationale`, `priority`) and merges in the F-ids (`finding`) and U-ids (`feedback`).

Output sha256 at A3: `e2776930d08211ec19d6daec7605f7d45ac1ac1216cc627313e3e61eacaf3ae0`
(528 rows, 224,556 bytes).

## How to run

```sh
# regenerate UNIVERSE.csv (the only file the tool writes) and print the reconciliation table
python3 docs/build/planning/2026-09-30-next-phase/tools/extract_universe.py

# verify only: the CSV is byte-identical to a fresh extraction, every source item appears exactly
# once, and counts reconcile to the A1 baseline or the difference is explained (exit 1 on any error)
python3 docs/build/planning/2026-09-30-next-phase/tools/extract_universe.py --check

# tests (NOT collected by `make check`: pytest testpaths = ["tests"])
uv run python -m pytest docs/build/planning/2026-09-30-next-phase/tools/test_extract_universe.py
```

The tool uses only the standard library (Python ≥ 3.11). `--stdout` prints the CSV and writes
nothing. At A3, `--check` exits 0 and the test file passes 16 of 16.

## Per-source counts (reconciliation printed by the tool)

"Expected" comes from `baseline/baseline.json` (`mem.deferrals.rows`, `mem.current.owed`,
`mem.coverage.*`, `mem.backlog.status`, `mem.adr.files`) or from the row prompt (readouts,
manifest rows, and the 8 reduced-scope ids). "—" means no prior total exists, so the tool prints
the derivation instead.

| source_kind | source | expected | actual | u_id range | explanation |
|---|---|---|---|---|---|
| `deferral` | `docs/tickets/DEFERRALS.md`, every `\| D-…` obligation row | 97 (36 owed) | **97** (owed **36** = 32 OPEN + 4 PARTIAL; 57 DONE, 4 WONTFIX) | U-0001–0097 | matches; owed set == OPERATIONAL_READINESS §(f3) set == META_PLAN App. B |
| `requirement` | `docs/build/COVERAGE_MATRIX.csv`, verdict ≠ MET, plus 8 reduced-scope MET | 154 (69 + 77 + 8) | **161** | U-0098–0258 | **+7**: the 7 `N/A-RATIONALE` rows (SIG-CHART-031/035, INGEST-044/045b/048a, LIC-007, STORE-033) also have verdict ≠ MET, so they are included. By source_status: PARTIAL 54 · MISSING 10 · AT-RISK-INTEGRATION 5 · MET-DIFFERENTLY 77 · N/A-RATIONALE 7 · MET(reduced-scope?) 8 |
| `backlog` | `docs/build/BACKLOG.csv`, status open + accepted | 36 (32 + 4) | **36** | U-0259–0294 | matches; the 22 closed rows are excluded |
| `risk` | `docs/risk_register.md`, rows `RISK-… → BL-nnn` whose BL is open or accepted | — | **62** | U-0295–0356 | 101 routed rows: 58 → open BL, 4 → accepted BL, 39 → closed BL (excluded, because their BL is closed). The register has 317 RISK rows in total |
| `ledger_finding` | `LEDGER.md` `## OPEN FINDINGS` + `## OPEN FINDINGS additions` | — | **1** | U-0357 | 7 entries; 6 carry RESOLVED/CLOSED/RETIRED markers; only `APPENDIX-F-01` is open |
| `return_pass` | `LEDGER.md` `## RETURN PASS` table ∪ `returnPass:` key | — | **19** | U-0358–0376 | 16 table rows ∪ 18 key entries: P24.3, P24.6, P24.7 are key-only and P31.4 is table-only |
| `adr_trigger` | `docs/adr/ADR-*.md` `## Revisit trigger` | 144 | **144** | U-0377–0520 | matches (ADR-064 does not exist; no file lacks the section) |
| `readout` | `docs/build/readouts/*.md` with status PENDING | 2 | **2** | U-0521–0522 | HUMAN-H4 and HUMAN-H5. Of the other 9 readouts, 7 are SIGNED/PASSED/INTERIM/RECORDED and GATE-G1/G2 are SKIPPED-BY-OPERATOR (see NEW-3) |
| `manifest_row` | `docs/tickets/00_MANIFEST.md` rows not landed | 6 | **6** | U-0523–0528 | 158, 159 (unused) and 184–187 (S3-deferred). Seven manifest rows have no BUILD_INDEX row: 184–187 are included; 190 GATE-G3 and 195 GATE-ACCEPT are excluded because their readouts are signed; 170a is excluded because it is recorded as a second "170" (F-24) |
| **total** | | | **528** | | |

The checker (`check_rows`, also run by `--check` and by the tests) enforces the following. Any
failure is an error:

- **exactly once**: each extracted `(source_kind, source_ref)` appears in the CSV exactly once, and
  no CSV row lacks a source item. `source_ref` is unique across the whole universe.
- **ordering and ids**: `u_id` runs U-0001…U-0528 contiguously over the sort (KIND_ORDER, then a
  natural sort of `source_ref`).
- **naive re-counts**: deliberately naive re-counts that share no code with the parsers
  (`^\| D-` lines, raw CSV filters, a glob plus substring for ADRs) equal the extractor's counts.
- **§(f3) match**: the owed-deferral set equals OPERATIONAL_READINESS §(f3), and every owed row
  has a blocker_class.
- **§55 coverage**: all 9 D-ids named in spec §55 are deferral rows.
- **links**: every link resolves to a universe row, is cross-kind, and is symmetric.
- **S1 columns**: the four S1 columns are empty. `stream`, `source_status`, `effective_status` and
  `evidence` are non-empty, and `blocker_class` is empty or a §8.1 enum value.
- **counts**: each count equals its expected value, or the difference equals a computed
  explanation (today only the requirement +7).

## Columns and conventions

The columns are the §8.1 columns in order, with **`links` appended at the end**. `links` is an A3
extension: a space-separated list of `source_ref`s for the same obligation, or directly related
obligations, in *other* sources. Cross-source duplicates are linked, never collapsed or
double-dispositioned.

| column | how A3 fills it |
|---|---|
| `u_id` | `U-nnnn`, positional over a deterministic sort. It is stable for fixed source bytes; if a source changes, re-run, and S1 freezes the ids it dispositions |
| `source_kind` | the §8.1 enum, plus two A3 extensions: **`ledger_finding`** (LEDGER OPEN FINDINGS; §8.1 `finding` stays reserved for FINDINGS.csv F-ids) and **`return_pass`** (the LEDGER RETURN PASS table/key) |
| `source_ref` | D-id · SIG-id · BL-nnn · RISK-id · finding id · `RETURN-PASS:<ticket>` · ADR-nnn · readout stem · `MANIFEST-<row>` |
| `title` | deferral: the `item` cell · requirement: first ≤200 chars of its paragraph in `docs/2_canonical_design_spec.md` · BL: title · risk: second cell · ADR: H1 title · others: the row text (whitespace collapsed, `**` stripped, clipped with …) |
| `source_status` | what the source itself says: deferral = the status cell's leading token · requirement = matrix verdict, with **`MET(reduced-scope?)`** for SIG-TRUST-009/010, FIND-006, DOS-002…005, ACQ-004 · BL = status · risk = `routed→BL-nnn` · ledger_finding = `open` · return_pass = `table=<m> key=<m>` (see caveats) · adr_trigger = `monitor` · readout = `PENDING` · manifest_row = `deferred` / `unused(<fate>)` |
| `effective_status` | deferral = head `to_status` of the `obligation-event/1` chain in `docs/build/reports/obligations/events.jsonl` (leading token if no event) · requirement = latest `coverage_assessments.jsonl` verdict, else the matrix verdict (the 8 reduced-scope rows therefore read `MET`) · BL = status · risk = its BL's status · return_pass = `owed` / `terminal` / `unlinked` over its linked deferrals · adr_trigger = `monitor` · manifest_row = `not-landed` (no BUILD_INDEX row) |
| `blocker_class` | filled **only for the 36 owed deferrals**, by mapping the OPERATIONAL_READINESS §(f3) "blocking domain" cell (quoted verbatim in `evidence`) with the rule below. Empty elsewhere; S1 and the F rows fill it |
| `evidence` | `file:line` pointers plus the facts used (the event id and interpretation, backlog_home, §(f3) domain, matrix class/owning/routing/ADRs, BL landing/gate, ADR status + trigger text, and so on) |
| `disposition`, `disposition_ref`, `rationale`, `priority` | **empty** (S1) |
| `stream` | the META_PLAN row that should adjudicate: deferral → **F1** · requirement → **F2** · backlog, risk → **F3** · return_pass → **B3** · ledger_finding (APPENDIX-F-01, spec App. F / `check_spec_src`) → **B4** · readout, manifest_row → **F4** · adr_trigger → **S1** (no Stage-P row owns revisit triggers; see NEW-4) |
| `links` | see "Linking rules" |

**Blocker mapping from §(f3) domain.** The first matching rule wins:

1. `external…` → external
2. contains `rights` → rights
3. `credentials` / `accounts` → operator
4. `scheduled` / `date-bound` → scheduled
5. `maintainer` → engineering
6. contains `operator` → operator
7. `human…` → human
8. `hosted…` → live-execution
9. `public` → operator
10. `engineering` → engineering

Result: operator 10 · rights 8 · live-execution 6 · human 5 · engineering 3 · scheduled 2 ·
external 2. Seven rows differ from META_PLAN Appendix B's hand grouping. These are inputs for F1
to adjudicate, not corrections:

- D-P32.16-1, D-R10-MEMORY-1, D-R10-PUBLISH-1, D-R7.1-AUTH and D-R7.2-SEND map to *operator*;
  App. B lists them under "human decision or review".
- D-R10-SOURCES-1 maps to *rights*; App. B says live-execution.
- D-SOURCES.12-1 maps to *rights*; App. B says engineering.

**Linking rules.** Links are mechanical and come only from explicit id mentions in an item's own
source text. The union is taken in both directions, same-kind pairs are dropped, and every target
must be a universe row.

- **Id shorthand is expanded** before matching: `D-P30.3-1/-2/-3`, `D-P21.4-1/2`,
  `SIG-IDENT-020/025`, `SIG-TASK-016a/b`, `SIG-DOS-002…005`.
- **HUMAN readouts and manifest rows**: `HUMAN-H4`/`HUMAN-H5` link both the readout and the
  manifest row. `P31.17`, `P31.18`, `P32.22a` and `P32.23` (strict word boundaries, so `P32.23a`
  does not match) link manifest rows 158, 159, 185 and 187.
- **ADR revisit triggers** are link *targets* only from BACKLOG `sources`: BL-002 lists the
  foundational ADRs and BL-056/057/058 list the round ADRs. ADR citations elsewhere are too
  ubiquitous to mean "same obligation". An ADR's own trigger text can still link out to
  D/SIG/BL/RISK/HUMAN ids.
- **return_pass** items link the D-ids they name, plus every deferral whose id is prefixed by the
  row's ticket or semantic id (`P21.1` → `D-P21.1-*`, `DEPLOY.1` → `D-DEPLOY.1-*`).
- **Deferrals** also link their `events.jsonl` `backlog_home`.

## Known parsing caveats

- **DEFERRALS row shapes.** Of the 97 rows:
  - **78** follow the 8-column header.
  - **17 are legacy 7-column rows**: the P21.x rows at lines 35–45 and the GL cross-reference rows
    D-LEGAL.1-1 … D-CI.1-1 at lines 71–76. They lack the separate `proxy now` cell.
  - **D-P21.9-1** (line 47) is an 18th legacy 7-column row, with **2 literal pipes inside a code
    span** (`[federation|forensics|acoustic]`), so a naive split sees 9 cells.
  - **D-P27.5-1** (line 305) has **bare literal pipes** (`fixtures|export`) and splits to 10 cells.

  In every shape, status = last cell and title = third cell, and both are correct for all 97
  rows. There are **no escaped pipes (`\|`) in DEFERRALS**; the splitter still honours them (one
  occurs in `risk_register.md` at RISK-P21-11, an unrouted row). One limit remains: a 7-column row
  with exactly one code-span pipe would read as 8 cells. No such row exists today (tested).
- **The four P32.1 status-conflict rows** are D-P21.4-3, D-P21.5-1, D-SOURCES.2-4 and
  D-R7.3-BREADTH. Each has an owed leading token next to a dated terminal token in the same cell.
  `obligation_events.py` records an interpretation for each, and 11 later rows got the same
  treatment (15 events with interpretation `reconciled`). Today every cell's leading token equals
  its event head, so `source_status == effective_status` for all 97. Only **D-P21.5-1** still leads
  `PARTIAL` while also carrying dated per-leg `DONE` tokens (recorded interpretation: PARTIAL, owed
  residue = operator decision); its `evidence` flags this. `reconciliations.json` covers
  manifest/ticket conflicts only. A3 cites it on MANIFEST-158/159 (the P31.17/P31.18
  dependency-not-in-chain reconciliation).
- **Kind vocabulary.** D-P27.5-1 has `kind=E`, which is outside the header's V/F/D/H/P/X
  (NEW-5).
- **Requirements.** `coverage_assessments.jsonl` holds assessments only for SIG-MEM-001…004, which
  are MET and not in the universe, so every universe requirement's `effective_status` is its matrix
  verdict. Titles come from the spec's `**SIG-… (LEVEL).**` paragraphs (715 of 715 found).
- **LEDGER** is read by the program only, never in full into context (P13). The tool reads the two
  `## OPEN FINDINGS` sections, the `## RETURN PASS` section and the one `returnPass:` line.
  - A finding is closed if RESOLVED, CLOSED or RETIRED appears after its id. P17-FLIP-01 reads
    "RETIRED — closed for real" and counts as closed.
  - The `returnPass:` value is split on top-level `, ` (parentheses respected) after stripping the
    trailing `   # …` comment.
  - `table=`/`key=` markers are a heuristic: `done-marked` means DONE/CLEARED is present and "owed"
    is absent, `partly-done-marked` means both are present, and `listed` means neither. They say
    what the LEDGER text claims. `effective_status` (from linked deferrals) says what the
    obligation register says, and the two disagree on several rows (NEW-2).
- **Risk register.** Two RISK ids occur twice (RISK-P5-04 at lines 289/313, RISK-P20-01 at
  1262/1451). At most one occurrence of each is routed (`RISK-P5-04 → BL-017`, and BL-017 is
  closed), so no universe ref collides.
  `RISK-P17-03 → BL-043 → retired by P21.9` is parsed and excluded because BL-043 is closed.
  RISK-P21-03 is cited by BL-004 (closed) but has no `→ BL` route (NEW-5).
- **ADRs** use two header styles, `- **Status:** Accepted` (119 files, including ADR-145) and
  `- Status: accepted …` (25 files: ADR-120…ADR-144). Both are parsed, and all 144 read
  "accepted". ADR-064 does not exist (no file).
- **Readouts.** The status comes from `Status:`, else `## Verdict:`, else the H1. ACCEPT-R8 has
  its status only in the H1.
- **Manifest.** The deferred rows come from the "Dispatch amendment — S3 human-evaluation deferral"
  line (`00_MANIFEST.md:5`, "rows 184–187"). The unused rows come from the Round-9 note "Rows 158
  and 159 are unused" (`00_MANIFEST.md:343`); neither row exists in any manifest table.

## Observations for downstream rows (inputs, not dispositions)

- **F2.** 57 of the 69 not-MET requirement rows have no link to any other universe item. Their
  own matrix row names no open/accepted BL, deferral, risk, readout or manifest row, and none of
  those (nor any ADR trigger) names them. F-30 reports 55 not-MET ids "in no
  BACKLOG/DEFERRALS/manifest row"; the method differs, because closed BLs and landed manifest rows
  are not universe items. Separately, 9 more MET rows cite an owed deferral (NEW-1).
- **B3.** RETURN PASS items by `effective_status`:
  - 5 owed: P21.3, P21.5, P21.7, P24.6, P31.4.
  - 13 terminal: every linked deferral is DONE or WONTFIX.
  - 1 unlinked: P23.1 (HG-05 integrate & release), which has no deferral row at all (NEW-2,
    NEW-3).
- **S1.** 122 of the 144 ADR-trigger items link to a BL row (mostly BL-002/056/057/058) or to a
  deferral/requirement named in the trigger text.

Findings raised by A3 are in `findings/incoming/A3.csv` (NEW-1 … NEW-5).
