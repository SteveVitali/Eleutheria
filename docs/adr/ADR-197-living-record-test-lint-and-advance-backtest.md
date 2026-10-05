# ADR-197 — The living-record test lint: a declared policy, an AST lint, and a nightly advance backtest (P34.31)

- Date: 2026-10-05
- Status: accepted
- Ticket: P34.31 (Round 11 / P34, row 236 — owns SIG-ENG-040; BM-TEST-01, OM-15)
- Base: `r11/P34.30-memory-cutover-disposition-and-transition-rule`
- Related: BM-TEST-01 (tests assert invariants, never the current value of a
  living record), the #165/#179/#185 pin breakages, SEED-03 / PKG-02 ED-11
  (invariant conversions), SIG-MEM-004 (coverage matrix verdicts are re-judged),
  ADR-120/126/127 (the Round-10 memory extension this guards).

## Context

Build memory is a set of *living* records — the LEDGER cursor, BUILD_INDEX,
DEFERRALS, the coverage matrix, readouts, the generated projection, the build
README's row range, the manifest, the ADR index — whose contents legitimately
change at nearly every closeout. A test that asserts their *current* contents
is a pin: it fails not because code broke but because the record did its job
(#165 pinned `EXPECTED_ROWS`; #179 and #185 pinned ledger cursor values).
SEED-03 converted the known pins to invariants, and the vendored validator's
§8b `living-pin?` grep warned on test files naming a living record plus a
living key — but the grep is unscoped text matching: it fired on three
`tmp_path` fixture constants and could never distinguish a real-tree read from
a fixture, a conditional status check from a pinned status, or a frozen
artifact's settled facts from living state.

## Decision

1. **A declared policy owns "living" — not a filename heuristic.**
   `docs/build/tools/record_policy/living_records.toml`
   (`living-record-policy/1`) names the living paths and globs, the frozen
   artifacts (living wins on overlap), the LEDGER current-state keys, the
   status vocabulary, the named-id shapes and the `[invariants.allowed]`
   escape-hatch registry. Every consumer — the lint, the backtest, the §8b
   structural check — reads the same declaration.

2. **An AST lint replaces the grep.** `docs/build/tools/living_record_lint.py`
   evaluates a test only when it reads a declared living path from the
   repository root — anchored `Path(__file__).resolve().parents[N]` /
   `REPO_ROOT` expressions, `read_text()`/`open()`/`exists()`/`glob()` calls,
   repo-relative literals bound to a helper's path parameter (transitively),
   or a constant loop iterable. Reads through `tmp_path` fixtures, validator
   calls (`audit_current_state.audit(REPO_ROOT)`), and `git show <sha>:<path>`
   snapshots are never evaluated (snapshots are recorded as the sanctioned
   channel). An evaluated test is a violation on any of the four pin shapes:
   a literal current-state `key: value`; an assertion carrying a status-word
   literal together with a record id in the test, or asserted of a
   living-derived value, or a living-derived expression equated to a record
   id (`rows.get(200) == "P33.8"`); `len(<living-derived>) == <int>`; a
   literal row-range or calendar date inside an assertion. The rules scan
   literals, f-strings and assertions only — docstrings and f-string segments
   are not literals.

3. **The escape hatch is a registry, not a pragma.**
   `@pytest.mark.living_record_invariant("<key>")` exempts one test only when
   `<key>` is registered with a reason in `[invariants.allowed]`; an
   unregistered key is itself a violation. Five keys are registered at
   landing — the three SEED-03-registered invariants
   (coverage-row-uniqueness, build-index-append-only-history,
   backlog-terminal-history) plus gate-readout-state-vocabulary and
   ledger-cursor-done-consistency — and every one is exercised by a rule the
   lint actually fires. `tests/unit/test_no_living_record_pins.py` drives the
   lint under `make check` and fails on violations, unregistered marks, and a
   vacuous run (zero scanned files or zero evaluated tests).

4. **§8b keeps a structural check, not a second heuristic.** The vendored
   validator requires the policy/lint/driver wiring and the
   `living-record-policy/1` schema line, and runs the lint when a
   tomllib-capable python3 is present — violations, not `living-pin?`
   warnings.

5. **A nightly advance backtest catches pins the lint cannot see.**
   `docs/build/tools/living_record_backtest.py` (`living-backtest/1`)
   replays — read-only, via `git archive` into a temp tree — the
   living-reading tests of each first-parent commit C against the tree at the
   next commit C′ that changed a declared living record. A failure where the
   test is byte-identical at C and C′ is `pin-broken`; an edited test is
   `converted-in-head`; a removed test is `removed-in-head`; collection errors
   are `infra`. C′-only test files stay in the tree (the coverage checker
   cites tests as evidence — deleting them fabricates a red). The nightly
   runs the stage `continue-on-error`, feeds `nightly_report.py`'s gate, and
   uploads the text + JSON report; `fetch-depth: 0` supplies the full
   first-parent history; a vacuous run exits 3, never green.

## Consequences

- Any future test pinning a living value fails `make check` at authoring time
  (the lint) and would fail the nightly at the transition that legitimately
  changes the value (the backtest) — defense in depth for BM-TEST-01.
- Real-tree reads of living paths are now enumerated (`38 tests` at landing) —
  the report's evaluated set is itself auditable.
- The backtest replays tests under the workspace interpreter at HEAD:
  package imports in replayed tests resolve from HEAD's environment while
  build-memory paths resolve inside the replayed tree. That is the fidelity
  the gate needs — the evaluated set is docs-reading tests — but a future
  test that both reads a living record and exercises a changed package API
  could report a historical red that is neither a pin nor a conversion; the
  classification fields exist to read such a report.

## Alternatives

- **Keep the grep warning.** It already false-positived on fixture constants,
  could not express "assert-scoped" rules at all, and warned rather than
  gated — the ticket asks for a lint that fails.
- **A test-file convention (directory split for real-tree tests).** Requires
  moving dozens of files and gives no rule-level judgement; the AST approach
  keeps tests where they are and reasons about what they actually read.
- **Sandboxed checkout for the backtest (worktree or clone).** `git archive`
  into a temp dir is simpler, has no index/gitconfig interaction, and cannot
  mutate the working tree by construction; a worktree adds bookkeeping for no
  fidelity gain.
- **`pytest --basetemp`/fixture patching to redirect living reads.** Changes
  what the test does rather than judging what it is — the lint is a static
  judgement precisely so the suite's behaviour is unchanged.

## Revisit trigger

- A pin shape the four rules miss turns up in a nightly backtest finding that
  the lint did not flag → add the rule and a registry key.
- The replay environment gap (package imports resolve at HEAD) produces a
  false pin-broken report → namespace the replay into a virtualenv built from
  C′'s lockfile, or restrict the evaluated set further.
- The `[invariants.allowed]` registry grows beyond a handful of keys →
  revisit whether the allowed-form vocabulary itself should be a first-class
  policy section.
