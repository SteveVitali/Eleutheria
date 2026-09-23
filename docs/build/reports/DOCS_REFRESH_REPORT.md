<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# DOCS_REFRESH_REPORT — P22.1 human-facing documentation refresh

Ticket: `docs/tickets/P22.1__repo-docs-refresh.md` · skill: `refresh-repo-docs` (full audit) ·
branch: `devin/p22-1-repo-docs-refresh` (stacked on `devin/p21-9-stage5-pathway-connectors`).

This was the first whole-repo human-facing docs pass since the build began: `audit: full`, every
in-scope doc audited claim-by-claim against the code at HEAD `8d8deb4`. The corpus was already in
good shape — most package READMEs and the ADR/build/research index READMEs had been kept current by
their own tickets — so the work was concentrated on the four gaps the ticket named (README run
modes + package map, the new `docs/README.md`, the governance index, the CHANGELOG backfill) plus a
handful of stale-count corrections found in passing.

## 1. Per-doc changes (stale fixed / cruft removed / gaps filled / mode fixes)

| Doc | Change | Kind |
|---|---|---|
| `README.md` | Added a one-line-per-package table for all 14 workspace members + a note on `web/`. | gap filled |
| `README.md` | Added "Running SIG — three ways" (`make check`; `sig-ops up` + `run_okc.sh`; `sig-ops degraded`) with the fixture-backed / not-live caveat sourced from `OPERATIONAL_READINESS.md`. | gap filled |
| `README.md` | "nine fixture-tested connectors" → "twelve" (P21.8/P21.9 added `data_driven`, `coarse_international`, `pathways`; verified via `sig-connectors list-connectors`). | stale fixed |
| `docs/README.md` | **New.** One-screen map classifying every top-level `docs/` entry as generated / frozen / append-only / historical record / living, and how each is changed. | gap filled |
| `docs/governance/README.md` | Added a **Status** column (adopted / protocol-adopted-not-run / published / template, each read from the document) and the missing eighth doc row (`stage0-outreach-letter.md`). | gap filled |
| `CHANGELOG.md` | Backfilled the Phase-21 operationalization chain (P21.1–P21.9) under the unreleased `0.1.0`, each entry citing its PR (#56–#65) + ADR + ticket; refreshed "Known limitations" (LD-V08 / A5 / A6 resolved; SIG-UI-047 still unbuilt-by-design; HG-07/08/10 deferred). Evidence-backed from `git log` + `gh pr list` only; `0.1.0` stays "unreleased". | stale fixed / gap filled |
| `CHANGELOG.md` | "nine fixture-tested connectors" → "twelve", listing the Phase-21 additions. | stale fixed |
| `Makefile` | Added `docs-check-repo` target (runs the vendored detector on `.`). | gap filled (tooling) |
| `scripts/docs/check-repo-docs-freshness.sh` | **New (vendored, MIT).** The refresh-repo-docs detector with a licence header + provenance comment; the only logic change is the corpus `find` filter, which encodes this repo's scope boundary (excludes virtualenv/third-party trees and the report-only set). | gap filled (tooling) |

No cruft was removed (no dead docs found) and no mode-drift relocations were needed — the in-scope
docs were already in their correct Diátaxis mode.

Docs audited and left unchanged (verified current): `CONTRIBUTING.md`, `db/README.md`,
`evidence/README.md`, `ops/README.md`, `web/README.md`, `docs/adr/README.md` (index complete through
ADR-071), `docs/build/README.md`, `docs/research/README.md`, `docs/studies/*`, `docs/slice/*` (no
broken references).

## 2. Remaining gaps (need a human)

- **Legal home / hosting entity (HG-01)** and **operating-governance body (HG-11)** are unnamed by
  design; the README/CONTRIBUTING correctly describe the project as pre-launch staging and cite the
  `PUBLICATION_CHECKLIST.md`. No doc should name a legal home until the operator sets one.
- **Contact channels.** Governance docs deliberately name roles / organisational channels only
  (Part VIII §0.7). A real project inbox / issue-tracker URL for outreach and takedown intake is a
  human decision; the docs use placeholders/roles until then — not filled here.
- **CHANGELOG `[0.1.0]` release date + tag.** Stays "unreleased" until the operator cuts `v0.1.0`
  per `INTEGRATION_PLAN.md` §(d); the compare/tag link is pre-wired but not live.

## 3. Code suspects (doc described intent; code looks wrong → BACKLOG.csv)

- **`pyproject.toml` `description` = "skeleton"** for `db`, `parsing`, `reconcile`, `orchestration`,
  `policy`, though all five are fully built and tested. Package metadata now contradicts the shipped
  code. Not a doc in this skill's scope (code metadata) → filed as **BL-052** (`type=docs-drift`).
  Recommended owner: a code-metadata cleanup ticket (P22+); a one-line description edit per package.

## 4. Excluded-scope findings (report-only set — reported, not fixed here, with owners)

The detector and the audit surfaced the following inside the report-only / never-edit set. Per the
ticket's scope boundary these are reported, not fixed in this ticket.

| Finding | Location | Severity | Owner / disposition |
|---|---|---|---|
| 4 "broken references" flagged by the detector | `docs/research/R1_osm_physical_layer_and_odbl.md` (`33.74,-84.42,…`, `tile`, `area.a`, `…`) | critical (detector) | **Accepted / false positive** — these are Overpass query fragments and a bbox coordinate string inside fenced code blocks, mis-parsed as markdown link targets; `docs/research/**` is a frozen cache (not edited). |
| ~143 "broken references" | `.venv/…/linkml*/…` (third-party package docs) | n/a | **Out of corpus** — a virtualenv, not repo docs; the vendored detector excludes `.venv`/`site-packages`. |
| P21.7 risks (`RISK-P21-12/13`) filed under the P21.6 section header (no `(P21.7)` header) | `docs/risk_register.md` | minor | **Report-only** (append-only register); owner: next register-maintaining ticket, or accept. Not rewritten here. |

## 5. Detector before/after counts

| Run | Command | Docs scanned | Critical (broken refs) | Exit |
|---|---|---|---|---|
| Before (skill detector, whole tree incl. `.venv`) | `bash <skill>/scripts/check-repo-docs-freshness.sh .` | 613 | 147 (143 in `.venv`, 4 false-positives in `docs/research/R1`) | 1 |
| After (vendored detector, in-scope corpus) | `bash scripts/docs/check-repo-docs-freshness.sh .` | 349 | **0** | **0** |

In-scope critical issues: **0 before and after** (the 147 "before" criticals were all in the
excluded virtualenv/report-only set). The vendored detector reports the honest in-scope corpus.

## Agent-docs note (for P22.2)

While auditing in passing, the `AGENTS.md` hierarchy (root + `db/`, `web/`) read as accurate and
current; no drift was fixed (agent docs are out of this skill's scope). P22.2 (`agent-docs`) should
run the agent-docs refresh and wire **both** detectors (`docs-check-repo` here + its own) into CI —
this ticket adds `make docs-check-repo` but leaves CI wiring to P22.2 per the manifest.
