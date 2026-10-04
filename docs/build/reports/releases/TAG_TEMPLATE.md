<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# TAG_v0.N.0 — template (agents fill; the operator tags — SIG-REL-014)

Copy this file to `TAG_v0.N.0.md` in the **last stack PR of a range** (G3
§9.2). Fill every `<…>`; the prepared file is what the operator executes
against in `TAGGING.md`. Nothing here places a tag — tagging is the
operator's action alone.

- **status:** not tagged — operator action (OP-08 pattern; agents never tag
  or push `main`)
- **tag:** `v<0.N.0>`
- **kind:** annotated (`git tag -a`); the tag object carries the true date —
  no date is typed in this file's tag block, the message, or the CHANGELOG
  heading
- **points at:** the `main` merge commit produced by the sitting that
  merges `<range>` — sha decided at merge time; the invariant is the tree
- **tree:** `<git rev-parse <tip>^{tree} — the pinned stack tip's tree the
  merge commit must equal (H1 tree invariant)>`
- **sitting / included PRs:** `<PR range, e.g. #141–#190 — every PR whose
  merge lands in this tag>`
- **green CI run ids:** `<run id(s) whose docs/python/composed/security/web
  jobs all read success on the commit the tag will point at — agent fills
  the pinned-head evidence; operator replaces with the merge commit's run>`
- **CHANGELOG section:** `## [0.N.0] — tagged by the operator (see git show
  v0.N.0)` (was `[Unreleased]` until the tag PR lands)
- **production release labels built from commits in the range:**
  `<each sig-YYYY-MM-DD[-<content-key>] / p-<sha> publication label the
  range's commits produced — per G3 §9.5 each CHANGELOG section lists the
  release labels it produced>`
- **prepared:** `<ticket id> (PR #<n>), <date -u> — agent-prepared;
  verified and executed by the operator`

## Operator checklist (summary of TAGGING.md)

- [ ] sitting merged to `main` via GitHub
- [ ] merge commit CI green head-bound (docs, python, composed, security,
      web) — run id recorded above
- [ ] `git rev-parse <merge-sha>^{tree}` == `tree:` above
- [ ] `git tag -a v0.N.0 <merge-sha> -m "<CHANGELOG section>"` +
      `git push origin v0.N.0`
- [ ] CHANGELOG heading flipped in the next stack PR; optional GitHub
      Release with the section as body
