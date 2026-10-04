<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Tagging procedure (operator-only — SIG-REL-014, G3 §9.2)

Semver tags are placed on `main` by the **operator** after merge sittings.
Agents never tag and never push `main` (mergePolicy: OPERATOR). The agent's
part ends at preparing `TAG_v0.N.0.md` from `TAG_TEMPLATE.md` in the last
stack PR of a range.

## Steps (operator)

1. **Merge the sitting.** Merge the stack's PRs to `main` via GitHub in
   order (the operator's normal sitting; H1/H2 §2.4).
2. **Wait for green CI on the merge commit.** The five required jobs —
   `docs`, `python`, `composed`, `security`, `web` — must read `success`
   head-bound on the merge commit. Record that run's id in the TAG file's
   `green CI run ids` (replacing the pinned-head evidence the agent
   prepared).
3. **Verify the tree invariant.** The merge commit's tree must equal the
   tree hash the TAG file recorded:

   ```
   git rev-parse <merge-sha>^{tree}
   # must equal the `tree:` line of TAG_v0.N.0.md (H1 tree invariant)
   ```

   A mismatch means the sitting resolved a conflict differently than the
   stacked tips promised — stop and reconcile; do not tag.

4. **Tag — annotated, no typed date.**

   ```
   git tag -a v0.N.0 <merge-sha> -m "<CHANGELOG section>"
   git push origin v0.N.0
   ```

   The tag object carries the true tag date itself, so **no date is typed**
   anywhere — not in the message, not in the CHANGELOG heading (§9.4: the
   heading reads `## [0.N.0] — tagged by the operator (see git show v0.N.0)`).

5. **CHANGELOG section flip** (next stack PR, agent-side): rename
   `## [Unreleased]` to `## [0.N.0] — tagged by the operator (see git show
   v0.N.0)` and end the section with "Production releases built from this
   range: …".
6. **GitHub Release (optional, operator-run).** One per tag, with the
   CHANGELOG section as its body (G3 §9.5).

## Version numbering (G3 §9.2)

- `v0.N.0` each sitting: **minor** when the range includes any public
  route, API, schema, descriptor or ontology change; **patch** (`v0.N.P`)
  for fix-only sittings.
- `v1.0.0` is an operator criterion (proposed: the human-evaluation spine
  complete **and** the HG-11 governance prerequisites met without waiver).
