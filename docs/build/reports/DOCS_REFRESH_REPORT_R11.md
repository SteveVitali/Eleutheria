<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# DOCS_REFRESH_REPORT_R11 — P38.4 Round-11 docs refresh (repo docs + agent docs)

Ticket: `docs/tickets/508_P38.4__round11-docs-refresh.md` · run mode:
`implement-spec spec=docs/tickets/508_P38.4__round11-docs-refresh.md live_verification=false` +
`refresh-repo-docs` then `refresh-agent-docs` (both vendored as
`scripts/docs/check-repo-docs-freshness.sh` / `check-agent-docs-freshness.sh`) ·
branch: `r11/P38.4-round11-docs-refresh` (forked at `edb6cc7a` off
`r11/P38.3c-round11-integration-plan-2`, caught up to `301a97c0`).

This is the third whole-repo docs pass (P22.1 → `DOCS_REFRESH_REPORT.md`, P33.7 →
`DOCS_REFRESH_REPORT_R10.md`) and the first to cover both halves in one row. Since P33.7 the
chain landed all of Round 11 through P38.3c: the Part XII §56 contract extension, the SIG-REL
release toolchain, the second public republish (P37.61a, 2026-11-16), the GATE-ACCEPT-R11
packet, and the P38.3c Round-11 integration plan.

**The binding constraint this row ran under:** the newest committed `sig.probe-run/1` record is
`docs/build/reports/probes/p37.61a-harm-republish-post.json` generated **2026-11-16T09:42:48Z** —
outside the live-claim policy's 24-hour freshness window (`docs/build/tools/record_policy/
live_claims.toml`) at refresh time (2026-11-23). The policy therefore permits no *new*
unqualified production-state assertion. Every refreshed production claim was re-dated,
bounded (`queued` / `prepared_not_executed` / `gated` / "as recorded"), or left untouched as a
dated grandfathered record — none was asserted fresh and none was silently removed.

## 1. Per-doc changes (stale fixed / bounded / gaps filled)

| Doc | Change | Kind |
|---|---|---|
| `README.md` | Spec stats **9,377 lines / 715 ids / v1.1.0** → **10,648 lines / 994 ids / v1.2.0** (`check_spec_src.py`, spec header); ADR count **144 → 251** (Appendix F); added the **Part XII** (§56) entry to the organization list. | stale fixed |
| `README.md` | "twenty registered connectors" → **thirty-six registered connectors** (×2 — intro + package row; `sig-connectors list-connectors` prints 36). | stale fixed |
| `README.md` | `connectors` row — "live fetch only where … green" → "**the gated** live fetch runs only where … green" (bounding verb, same fact). | bounded |
| `README.md` | `ops` row — Round-10-only verb list → names the gated hosted-deploy lane + the Round-11 release toolchain and leg-runner declarations. | stale fixed / bounded |
| `README.md` | "Deployed state" heading — Round-10 date kept; appended "Round-11 additions below are bounded records, nothing re-probed". New **Round-11 bullet** records: the 2026-11-16 republish, the clean-failed→fully-reverted schema deploy, the queued export/re-cut chain, the `prepared_not_executed` promote chain, and the stale-probe disclosure. Historical bullets untouched. | bounded (append-only) |
| `README.md` | Releases § — integration-plan pointer moved from P33.6 to **P38.3c** (`reports/p38.3c-integration-plan/INTEGRATION_PLAN.md`); the superseded plans stay named as dated records. | stale fixed |
| `CHANGELOG.md` | `[0.1.0] — unreleased` header — plan pointer moved to P38.3c (supersedes P33.6). | stale fixed |
| `CONTRIBUTING.md` | Integration pointer moved to the P38.3c plan; superseded plans kept as dated records. | stale fixed |
| `docs/README.md` | Top-level table gained the missing **`ops/`** row (`docs/ops/RUNBOOK.md`, `manual-acquisition.md`; living; agent-drafted, operator-gated). | gap filled |
| `docs/research/README.md` | Header counts **26,862 lines / 541 findings** → **26,818 / 501** (matches its own table sums and the root README's Contents row). | stale fixed |
| `ops/README.md` | Verb table — two rows appended naming the Round-11 families verified against `sig-ops --help` (release toolchain + gated leg-runner/probe machinery), each posture cell labelled `prepared_not_executed`/offline; the section intro now says "gated hosted-ops … Round-10 + Round-11". | stale fixed / bounded |
| `ops/README.md` | Appended dated update (2026-11-23): republish #2 record; schema deploy clean-fail→revert; queued export/promote chain; authoritative-state pointers. Executed record above preserved verbatim. | bounded (append-only) |
| `ops/gcp/README.md` | Appended dated update (2026-11-23) in the file's own update-block style: `sig-pg` `db-custom-2-7680` Wave-C L2 record; the `OPS-SPINE-SCHEMA-DEPLOY` clean failure (19/41 → reverted, `closed_vocabulary` verify division-by-zero, 133 pre-existing NULL IRIs); owed fix + PITR rehearsal; lapsed L3 window; 12 keyed secrets pending. | bounded (append-only) |
| `web/README.md` | Islands sentence — `/network/` → the current T2 set `/map/`, `/explore/`, `/search/` (ADR-242; `/network/` 301s since P37.26) + the ADR-155 page-type registry as the budget authority; `src/pages/` row lists the current route set (`explore/`, `r/**`, `s/**`, `intake/`); Commands block rebuilt from `web/package.json` scripts (`check` chain now runs 16 legs incl. `check:lhci`/`map-styles`/`paths`/`snapshot`/`dom`/`figures`/`tokens`/`lexicon`/`copy`/`feeds`/`dsrc`/`runtime-deps`; `check:perf:national`, `check:visual`, `test:visual`, `gallery:visual` documented). | stale fixed |
| `AGENTS.md` (root) | Key-Files line counts re-measured (Makefile ~400, ci.yml ~750, generate.py ~650, claim_sink ~2560, store_pg ~1790, conftest ~380, test_composed_stack ~1250, MANIFEST ~990); `make docs-check` row now describes the real 16-check gate incl. the live-claim lint; gotcha 6's "t1-module-entries empty until UXK0-4" → the six ADR-224 entries. | stale fixed (agent-docs half) |
| `connectors/AGENTS.md` | "twenty registered connectors" → **thirty-six**. | stale fixed |
| `ops/AGENTS.md` | `cli.py` ~2820 → ~7290; purpose cell names the Round-11 families; gotcha 4 generalised to the gated leg-runner (exit 42 `prepared_not_executed`). | stale fixed |
| `api/AGENTS.md`, `exports/AGENTS.md`, `db/AGENTS.md`, `tests/AGENTS.md`, `web/AGENTS.md` | Key-Files line counts re-measured to current (`app.py` ~710, `routes.py` ~1010, `store_pg`/`store`/`curation`/`cli`, `exports/cli.py` ~2610, `claim_sink` ~2560, `conftest` ~380, `test_composed_stack` ~1250, `package.json` ~70); `web/AGENTS.md` `check` row lists the real 16-leg chain. | stale fixed |

## 2. Docs audited and left unchanged (verified current at HEAD)

`db/README.md`, `evidence/README.md`, `docs/evaluation/README.md`,
`docs/governance/README.md` (current — ten rows incl. the intake packet + opinion drafts),
`docs/adr/README.md` (generated index — never hand-edited), `CITATION.cff`,
`docs/studies/`, `docs/slice/`, `docs/ops/RUNBOOK.md` (P35.4-maintained;
`check_runbook.py` verifies every command — green), `docs/ops/manual-acquisition.md`,
`ops/monitoring/README.md`, `docs/build/OPERATIONAL_READINESS.md` (the authoritative Round-11
state surface; §(g) already records the queued posture — cited, not edited),
`docs/tickets/**` (historical record), `docs/risk_register.md`,
`docs/traceability.md` (append-only registers).

## 3. Detector results

| Run | Command | Result |
|---|---|---|
| Before (base `301a97c0`) | `bash scripts/docs/check-repo-docs-freshness.sh .` | 448 docs scanned, 0 broken refs, 0 stale suspects |
| Before | `bash scripts/docs/check-agent-docs-freshness.sh .` | 8 agent docs scanned, 0 issues |
| Before | `python3 docs/build/tools/check_live_claims.py corpus` | 14 files, 3,684 segments, 113 claims — all 113 grandfathered (pre-policy), 0 violations |
| After | all three + `check_live_claims.py range --range r11/P38.3c-round11-integration-plan-2...HEAD` | recorded in `docs/build/runs/P38.4.md` |

Note: the live-claim lint is the binding check for this row — all 113 pre-existing claims are
grandfathered dated records and stay verbatim; every *added* line was kept assert-free or paired
with a bounding word in the same segment (the classifier splits on `;`/`|`/`. ` and reads
backtick spans out).

## 4. Commands in the docs — checked in this environment (macOS, uv workspace)

| Command | Where documented | Checked |
|---|---|---|
| `sig-connectors list-connectors` | README, connectors/AGENTS | executed — 36 names printed |
| `uv run sig-ops --help` | README ops row, ops/README verb table, ops/AGENTS | executed — every listed verb family verified present in the help surface |
| `npm --prefix web run check` script names | web/README Commands, web/AGENTS | verified against `web/package.json` `scripts` block (not executed — no web code changed; the CI `web` job is the evidence) |
| `python3 docs/build/tools/check_spec_src.py` | README spec stats | executed — 38/38 spec sources, 251/251 Appendix-F entries consistent |
| credentialed/hosted verbs | ops/README, ops/gcp/README, RUNBOOK | labelled gated/credentialed in-doc; not executable here — recorded, never claimed |

## 5. Remaining gaps (owned, linked — nothing closed here)

- **The owed register stands unchanged** — `docs/tickets/DEFERRALS.md` (no row names P38.4;
  the promote chain `D-P36.72b-1 → D-P37.65a-1 → D-P37.65b-1`, the Wave-C legs, `D-P38.2-1`
  GAP-RP-1 disposition, `D-P38.3a-1`, `D-P38.3b-1` and the watch items stay OPEN — cited, not
  re-decided).
- **113 grandfathered claims** (`check_live_claims` `grandfathered_list`) are dated records the
  policy deliberately reports rather than rewrites. Refreshing any of them requires a fresh
  probe-run — the next live-verification row (or a tail probe sweep) is the owner.
- **Nightly CI red** (`NIGHTLY-RED-1`, ≥43 consecutive at last record) and the carried
  `PY-T0-FRESHNESS-1` fixture debt (`tests/ops/test_release_verify.py`) are operational debt
  recorded in the LEDGER — not doc defects, not fixed here.

## 6. History preservation notes

Dated records kept verbatim: the go-live launch/republish claims in README's Deployed-state
bullets and ops/README's executed cut-over section, `ops/gcp/README.md`'s earlier update blocks
(the e2-micro/≈$0 design record, the Cloud SQL + Cloud Run deployment record, the P35.4 pointer),
OPERATIONAL_READINESS §(a)–(f), every `runs/`/`pr/`/`readouts/`/`reports/` entry, the CHANGELOG
per-phase entries, and the generated spec / ADR index (never hand-edited). All edits were to
living docs; the two operational READMEs gained appended update blocks rather than rewrites of
their executed records.
