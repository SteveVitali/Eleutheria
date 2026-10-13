# ADR-195 — Versioning discipline and one version source (P34.23)

- Date: 2026-10-04
- Status: accepted
- Ticket: P34.23 (Round 11 / P34, row 227 — REL-10; owns SIG-REL-014)
- Base: `r11/P34.22b-date-truth-fixtures-and-sources-dates-v2` (Round-11 chain)
- Related: G3 §9 (codebase versioning — `docs/build/planning/2026-09-30-next-phase/design/G3-release-model.md`),
  finding NEW-3/GT-7 (`resolver_version`/`renderer.version` = `0.0.0` in every
  release, 11 of 14 `__version__` hard-coded), SIG-REL-014 (§56.6), SIG-ENG-003
  (decision changes land as new ADRs).

## Context

Code versions came from three disagreeing places: every `pyproject.toml` and
`web/package.json` said `0.1.0` while 11 of 14 `__init__.py` files hard-coded
`__version__ = "0.0.0"`, and `run_spine_export` stamped `resolver_version`
with the exports package's own placeholder — so the GATE-G3-signed candidate
records `resolver_version 0.0.0`, `renderer.version 0.0.0` (GT-7/NEW-3).
SIG-REL-014 requires code versions from one source, no `0.0.0`, operator-only
semver tags on `main`, and a CHANGELOG entry for every public-behaviour
change.

G3 §9.3/§9.4 prescribe the mechanism; this ADR records the sub-decisions the
ticket owned.

## Decision

1. **`__version__` derives from installed distribution metadata.** Every
   package's `__init__.py` reads
   `__version__ = _dist_version("sig-<pkg>")`
   (`from importlib.metadata import version as _dist_version`). The dist
   names are `sig-<pkg>` (e.g. `sig-db`), which uv materialises from each
   `[project] version` at sync time — so the pyproject pair is the single
   declaration point and `uv sync` is the only refresh step. A missing
   install raises `PackageNotFoundError` rather than falling back to a
   literal — a second source is worse than a loud failure.
2. **`resolver_version` = `resolution.__version__` + `+g<commit8>`.**
   `exports.versioning.default_resolver_version()` reads the tree's commit
   via `git rev-parse --short=8 HEAD` — taken from the tree, never typed
   (GT-7). When no git tree answers (a deployed artifact with no checkout)
   the suffix is omitted and the bare resolution version is returned:
   honest identity, never a fabricated commit.
3. **`scripts/bump_version.py <x.y.z>`** rewrites the `[project] version`
   line of all 14 member pyprojects (read live from
   `tool.uv.workspace.members`) plus `web/package.json` — dry-run by
   default, `--apply` to write, `0.0.0` and non-`x.y.z` refused. Lock
   regeneration (`uv sync`, `make gen`) is a printed follow-up, not part of
   the script, so the bump touches version files and nothing else.
4. **CHANGELOG gate in the `docs` CI job** (`changelog_gate.py`, schema
   `changelog-gate/1`): a PR range touching the G3 §9.4 public-behaviour
   path set must change `CHANGELOG.md` or carry a
   `Changelog: none (<reason>)` trailer read from a commit's final
   paragraph (the lenient `check_trailers` grammar; an empty `()` reason
   does not count). Exit codes mirror the repo's other range gates:
   0 pass · 1 violation · 3 vacuous · 5 unknown — never green on
   unreadable input. PR-only: a landed head was judged at PR time.
5. **Tag procedure + template** under `docs/build/reports/releases/`:
   `TAGGING.md` (operator-only: annotated `git tag -a`, tree-hash
   verification, no typed date), `TAG_TEMPLATE.md` (agents fill in the
   last stack PR of a range), `TAG_v0.1.0.md` prepared for the #141–#190
   sitting, marked "not tagged — operator action" (OP-08; D-G3-6 [B-10]).

## Consequences

- `git grep '"0.0.0"'` on package `__version__` lines is empty; the
  equality test (`tests/unit/test_version_source.py`) fails on any
  divergence between pyproject, installed metadata, `__version__`, and
  `web/package.json`, and on any re-hardcoded literal.
- Export manifests built after this change carry a real resolver code
  identity (`0.1.0+g<commit8>`); pre-change manifests remain as recorded
  evidence (append-only; the 09-27 manifest's `0.0.0` is history, not a
  file to edit).
- The CHANGELOG gate joins the `docs` job's required-check set — a public
  path PR without an entry or trailer goes red at PR time (CI-8 disclosed
  in the PR body).
- `v0.1.0` remains an unplaced tag until the operator's post-#190 sitting
  executes `TAGGING.md` (OP-08); nothing here tags or pushes `main`.

## Alternatives considered

- **Hard-code `0.1.0` everywhere** (fix the literals, keep the shape):
  rejected — it recreates the exact drift mechanism (NEW-3): a literal can
  silently disagree with the pyproject again.
- **`setuptools-scm` / `hatch-vcs` dynamic versions**: rejected for now —
  adds a build-time dependency on `.git` presence for metadata generation;
  importlib metadata gives one source with zero new dependencies. REL-01
  (P35.12) may revisit for descriptor v2's commit binding.
- **Trailer-free gate (CHANGELOG change always required)**: rejected — the
  spec names the `Changelog: none (<reason>)` escape for changes with no
  public-behaviour surface; requiring a reason keeps a skip honest.

## Revisit trigger

- REL-01 (P35.12, release identity v2) builds descriptor v2 — revisit
  whether `code_commit`/`renderer.revision` derivation moves into the
  BuildSpec/descriptor path or stays in `exports.versioning`.
- If a workspace member ever ships outside a git checkout where the `+g`
  suffix is still required (e.g. a wheel-only deployment), add an explicit
  `SIG_CODE_COMMIT` injection at build time rather than weakening the
  no-fabrication rule.
