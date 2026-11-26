# VERIFY-FIXES — the two verify-side defects from `p37.65a-modes-triage/FINDINGS.md`

- **Scope:** implement the two code fixes the triage report recommends —
  finding 1 (`D-P37.65a-4`, the V3 `page_index.json` allow-list spec-gap)
  and finding 5 (`D-P37.65a-8`, the `check_v5` memory bound that OS-killed
  the tree-mode suite at ~576k pages). Source:
  `docs/build/reports/p37.65a-modes-triage/FINDINGS.md` (committed on
  `origin/r11/ops-modes-triage` / PR #571). Findings 2, 3, 4 are not this
  leg's (2 = web data-layer nullable read `D-P37.65a-5`; 3 = owner/spec
  decision `D-P37.65a-6`; 4 = registry machinery + operator bind
  `D-P37.65a-7`).
- **Harness:** devin-desktop/swe-2-high/subagent
- **Branch / base:** `r11/ops-verify-fixes` (worktree
  `/private/tmp/sig-verify-fixes`) off
  `origin/r11/P38.3c-round11-integration-plan-2` (`7aa79dbe`); PR base the
  same.
- **Mutations:** none — code + spec-doc + tests + this ledger; no hosted
  write, gate record, source flip, or operator contact.

## Fix A — V3 allow-list spec-gap (finding 1)

- `ops/src/ops/release_verify.py` `check_v3`: `allowed_s` gains
  `"page_index.json"` alongside `"release.json"` — the J3 §8.1 withdrawal
  index `assemble_site_trees` writes at `s/<pub>/page_index.json`
  (`site_trees.py:228-232`, consumed by V10 per the G3 §5.5 V10 row).
  Additive, allow-listed never `required` — it is pipeline-emitted like
  `release.json`, not a web-build route. `allowed_v` unchanged (the index
  lives only in `s/`).
- `docs/build/planning/2026-09-30-next-phase/design/G3-release-model.md`
  §5.4: the "Added prefixes" line now names `page_index.json` (annotated:
  the J3 §8.1 withdrawal index, `s/<pub>/` only).
- `ops/public_routes.toml` deliberately untouched — its header contract is
  the synced web tree's top level; `page_index.json` is a
  release-pipeline namespace, the same class as `r/ entity/ conf/
  compat_index.json release.json` which the file explicitly does not list.
- **Operator-visible note (SIG-OPS-003):** the triage records that an
  allow-list edit is historically the publish decision and recommends the
  operator confirm §5.4 may grow the entry. The parent dispatched both
  edits; the confirmation ask is preserved here, not silently discharged.
- **Nothing else needed beyond `allowed_s`:** `assert_allowlisted_tree`
  checks top-level *names* only (`publish.py:874-904`), so the file form
  (what `assemble_site_trees` writes) is covered; `page_index.json` needs
  no V5-link-crawl carve-out (it is a file, not linked) and no
  `required` entry (a real `s/` tree always carries it, but `required`
  would fail `v/`-style contexts where it legitimately cannot exist —
  mirroring `release.json`'s own treatment).

## Fix B — `check_v5` memory bound (finding 5)

- **`_html_files` → lazy iterator** (`release_verify.py:460-488`): the
  whole-corpus `sorted(rglob)` materialisation (~1.28 M `Path`s per check
  across the four namespaces) is replaced by `_walk_sorted`, a DFS that
  sorts each directory's entries as it reaches them (a dir's subtree ranks
  under `<name>/`, reproducing `sorted(rglob)` order exactly — `/` sorts
  after every name character). Resident cost: O(dir fan-out), order
  preserved, non-`.html` entries skipped identically. Call sites now
  iterate lazily; `check_v5` walks the tree twice (once for the link map,
  once for `latest_version_targets`), `check_v4` counts `pages_crawled`
  with a counter instead of `len(pages)`, `check_v13`/`check_v6`/
  `check_v11`/`check_v8` iterate unchanged.
- **Bounded-resident witness accumulation** (`release_verify.py:494-516`):
  `_witness_add` keeps only the `cap` smallest referrers per route — the
  exact prefix `sorted(full_set)[:cap]` produces — so `links` holds ≤2
  witnesses and `containment_targets` ≤1 (every consumer's bound:
  `from_pages[0]`, `links[route]` — formerly `sorted(set)[0]` /
  `sorted(set)[:2]`). Resident cost drops from O(all link edges, ~25 M
  string pairs) to O(unique routes); duplicate edges and late arrivals
  never grow the window, and a violation always keeps ≥1 witness — verdict
  semantics identical.
- **Unchanged by design:** the serial-fetch wall-clock bound (the ~30–60 h
  V4/V5 crawl at release scale) is the separately recorded leg bound, not
  this defect; the P-mode `v5_sample` cap and `sorted(routes)` order are
  untouched.
- **Not taken:** the report's optional per-check subprocess isolation —
  the two resident bounds it names are the fix; isolation is a separate
  resilience improvement the parent may schedule.

## Tests added (`tests/ops/test_release_verify.py`)

- Fixture: `_write_site_tree` now emits `s/<pub>/page_index.json`
  (mirroring `assemble_site_trees`), so the honest fixture carries the
  index everywhere.
- `test_v3_allows_the_page_index_withdrawal_index` — the index is
  allow-listed in `s/` (V3 green) while an actually-unlisted top-level
  entry still fails.
- `test_v5_referrer_sets_are_resident_bounded` — a 2,000-referrer
  synthetic set (shuffled + duplicated) keeps exactly
  `sorted(set)[:cap]`; the `cap=1` containment form keeps the min.
- `test_v5_escape_witnesses_stay_bounded` — a dead route linked from 3
  `s/` pages still fails, the recorded escape names the smallest
  referrer, and the dead-link leg still lists the route.
- `test_html_files_streams_in_sorted_order` — `_html_files` returns an
  iterator (`iter(r) is r`), yields `sorted(rglob)` order
  (file-vs-directory `<name>/` edge case pinned), skips non-HTML and
  absent roots.

## Results

- `uv run pytest tests/ops -q` — **2525 passed, 2 skipped** in 581 s
  (both skips are the recorded web-build-environment absences in
  `test_publish.py`, covered by the CI `web` job). The four new tests
  pass inside `tests/ops/test_release_verify.py` (28/28);
  `test_release_verify_b.py` 55/55 (imports the fixture — unaffected by
  the new `s/` file).
- `uv run ruff check` + `uv run ruff format --check` — clean on
  `ops/src/ops/release_verify.py` + `tests/ops/test_release_verify.py`.
- `uv run mypy ops/src/ops/release_verify.py` — clean.

## Deferred

- No DEFERRALS.md rows written — the parent records them. Proposed: this
  leg **closes** `D-P37.65a-4` (finding 1: `allowed_s` +
  G3 §5.4 landed, test pinned — pending the parent recording the row and
  the SIG-OPS-003 operator-confirmation ask above) and **closes**
  `D-P37.65a-8` (finding 5: bounded witnesses + lazy `_html_files`
  landed, tests pinned; the optional per-check subprocess isolation is
  recorded as not-taken, available as a follow-on if the parent wants a
  new row for it).
- Still open, untouched by this leg: `D-P37.65a-5` (emit-side nullable
  presentation payload — web change + dist re-emit), `D-P37.65a-6`
  (V13 chrome-scope owner decision — blocks on the answer, not code),
  `D-P37.65a-7` (verb_build label-bind machinery + the operator's
  `sig-2026-11-25.1` bind — a registry write only the operator runs).
