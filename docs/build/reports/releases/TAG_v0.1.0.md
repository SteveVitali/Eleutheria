<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# TAG_v0.1.0 — prepared for the operator (not tagged — operator action)

- **status:** **not tagged — operator action** (OP-08; D-G3-6 [B-10] "Yes":
  the operator tags `v0.1.0` after the #190 merge sitting; agents never tag
  or push `main`)
- **tag:** `v0.1.0`
- **kind:** annotated (`git tag -a`); the tag object carries the true date —
  no date is typed in this file's tag block or in the CHANGELOG heading
- **points at:** the `main` merge commit produced by the sitting that
  merges the rest of #141–#190 — sha decided at merge time; the invariant
  is the tree below
- **tree:** `64a23cd7c0330fa23c93d659c96e7da94df59934`
  (= `b051732c^{tree}`, the pinned stack tip per LEDGER
  `buildBranchBase: devin/p33-8-agent-docs-refresh` /
  `pinnedBaseSha: b051732c`; H1 tree invariant, G3 §9.2)
- **sitting / included PRs:** **#141–#190.** At preparation (2026-10-04,
  GitHub read): #141–#176 already merged (the operator's 2026-10-03
  sitting); #177–#190 open, pending this sitting.
- **green CI run ids (pinned-head evidence — replace with the merge
  commit's run before tagging):** run `36494519255` on `b051732c`, all
  five required jobs `success` — docs `109170979851`, python
  `109170979757`, composed `109170979606`, security `109170979728`, web
  `109170980091` (check-runs read 2026-10-04).
- **CHANGELOG section:** `## [0.1.0] — tagged by the operator (see git show
  v0.1.0)` — the existing `## [0.1.0] — unreleased` section of
  `CHANGELOG.md` (the post-`0.1.0` `[Unreleased]` section stays open for
  the next tag).
- **production release labels built from commits in the range**
  (per the committed records):
  - `sig-2026-08-20-95c7a19a` — the fixture-backed OKC export lineage
  - `sig-2026-09-24-bd01cb94` — the launch publish
    (`docs/build/reports/LAUNCH_RECORD_2026-09-24.md`)
  - `sig-2026-09-27-ce480ab1` — the republish
    (`docs/build/reports/REPUBLISH_LIVE_2026-09-27.md`)
- **prepared:** P34.23 (this PR), 2026-10-04 — agent-prepared; verified and
  executed by the operator.

## Operator checklist (summary of TAGGING.md)

- [ ] sitting merged to `main` via GitHub
- [ ] merge commit CI green head-bound (docs, python, composed, security,
      web) — run id recorded above
- [ ] `git rev-parse <merge-sha>^{tree}` ==
      `64a23cd7c0330fa23c93d659c96e7da94df59934`
- [ ] `git tag -a v0.1.0 <merge-sha> -m "<CHANGELOG section>"` +
      `git push origin v0.1.0`
- [ ] CHANGELOG heading flipped in the next stack PR; optional GitHub
      Release with the section as body
