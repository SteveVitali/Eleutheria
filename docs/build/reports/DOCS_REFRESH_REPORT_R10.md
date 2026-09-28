<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# DOCS_REFRESH_REPORT_R10 — P33.7 human-facing documentation refresh

Ticket: `docs/tickets/199_P33.7__round10-repo-docs-refresh.md` · skills:
`implement-spec` (full rigor, `live_verification=false`) + `refresh-repo-docs`
(full audit, structural mode) · branch: `devin/p33-7-repo-docs-refresh` (stacked on
`devin/p33-6-integration-plan`, base `474f69f4`).

This is the second whole-repo human-facing docs pass (the first was P22.1, report at
`DOCS_REFRESH_REPORT.md`). Since P22.1 the chain landed the go-live (GCP deployment,
go-public executed 2026-09-16, domain live 2026-09-23, national publish 2026-09-24,
republish 2026-09-27), the national/expansion rounds (P25–P31), and all of Round 10
(P32/P33). Every in-scope doc was audited claim-by-claim against **code, run, or
public evidence at HEAD** — the drift concentrated exactly where expected: the docs
still described the pre-launch "nothing is deployed / no live fetch" posture.

## 1. Per-doc changes (stale fixed / cruft removed / gaps filled)

| Doc | Change | Kind |
|---|---|---|
| `README.md` | "not a running service: nothing is deployed and no source has been fetched live" → the bounded current state: **deployed + public** at `surveillancegraph.org` (GCP, launch 2026-09-24 / republish 2026-09-27, ~2.4M-claim watermark — `LAUNCH_RECORD_2026-09-24.md`, `REPUBLISH_LIVE_2026-09-27.md`) AND the honest Round-10 qualifiers: provisional-policy release candidate **staging-only**, production exposure `D-R10-PUBLISH-1` OPEN, intake `operational=false` (`503 receiver_not_operating`), evaluation deferred. | stale fixed |
| `README.md` | Spec stats 9,047 lines / 671 ids → **9,377 lines / 715 requirement ids / v1.1.0** (`check_spec_src.py`); added **Part XI** (§55) to the organization list; Appendix F count → **144 ADRs**. | stale fixed |
| `README.md` | "twelve fixture-tested connectors" → **twenty registered connectors** (`sig-connectors list-connectors`). | stale fixed |
| `README.md` | "no source is 'green' (HG-03 pending)" → per-source fail-closed gate with the green subset fetched live by hosted scheduled jobs (`SOURCE_LIVE_OPS_MATRIX.md`); un-green sources still refuse exit 3. | stale fixed |
| `README.md` | Releases §: no longer points only at the superseded P20.3 `INTEGRATION_PLAN.md` §(d) tag procedure — names the current P33.6 plan (`reports/p33.6-integration-plan/INTEGRATION_PLAN.md`), records REL.1 skipped-by-operator / `v0.1.0` untagged (`git tag -l` empty). | stale fixed |
| `README.md` | `Contents` table gained `docs/evaluation/` (P32.9/10 campaign packet); `governance/` row names the intake packet + opinion drafts; `ops` package row names the hosted-deploy and Round-10 verbs. | gap filled |
| `README.md` | New "Deployed state" block + "Current state & owed work" pointers (OPERATIONAL_READINESS §(f), CAPSTONE_CLOSURE §(f), DEFERRALS). | gap filled |
| `CHANGELOG.md` | "[0.1.0] — unreleased" header names the current integration plan; "not a running service (nothing deployed; no source fetched live)" → dated post-Phase-21 chain summary (go-live + national + Round 10) ending at the signed GATE-ACCEPT + 36 owed rows + `SIG-MEM-004`. | stale fixed / gap filled |
| `CHANGELOG.md` | "Known limitations" rewritten: deployment + live fetches happened; real owed set now listed (staging-only candidate / `D-R10-PUBLISH-1`; intake `503`; deferred S3 spine; `D-SOURCES.*` lanes). Two references to the moved `docs/build/PUBLICATION_CHECKLIST.md` repaired to `reports/`. | stale fixed |
| `CHANGELOG.md` | "MapLibre island remains not built by design" → the `/map/` opt-in MapLibre+PMTiles island shipped (P27.9, ADR-097; budgets ADR-134); the static-PMTiles claim preserved as history in the P21.5 line. | stale fixed |
| `CONTRIBUTING.md` | Integration pointer moved to the P33.6 plan (P20.3 file kept, dated); `make docs-check` added to the target list (it exists since P22.2 and runs in `make docs-check`). | stale fixed / gap filled |
| `docs/README.md` | Top-level table gained the missing `evaluation/` row (living; prepared-not-executed). | gap filled |
| `docs/governance/README.md` | "Eight documents" → **ten**; rows added for `intake-receiver-operating-packet.md` (*prepared; not ratified* — `D-P32.16-1`, §55.5, SIG-FIND-006) and `publication-opinion-drafts.md` (*operator-adopted analyses — NOT legal advice* — HG-02/`D-LEGAL.1-1`); the Status legend gained both new status kinds. | stale fixed / gap filled |
| `ops/README.md` | "no cloud-specific config" scoped to the composition + pointed at `ops/gcp/` + `GCP_DEPLOYMENT.md`; command surface extended with a bounded Round-10 verb-family table (deploy/probe/cadence, recovery, release machinery, dossier packets — each labelled offline/staging/credentialed per `sig-ops --help`); `docs/build/FIRST_JURISDICTION_REPORT.md` → `reports/`; "Go-public cut-over — Deferred" rewritten as the executed record (2026-09-16 go-public, 09-23 domain, 09-24 launch, 09-27 republish; owed items named). | stale fixed / gap filled |
| `ops/gcp/README.md` | Appended a dated update: the "no real apply" gate text kept as the P24.1 authoring record; the apply ran 2026-09-15 under ADR-081 (Cloud SQL + Cloud Run, ~$9/mo) — `GCP_DEPLOYMENT.md`. | stale fixed (append-only) |
| `web/README.md` | "the build ships no client JavaScript" (absolute) → zero-JS on public content pages with the three opt-in islands `/map/` `/network/` `/search/` (ADR-068/097/134, per-island budgets, SIG-UI-050 no-JS fallbacks) + `/curate/**`; the `src/pages/` row lists the current route set (releases/, search, corrections/dispute, dossier/research-dossier, evidence, watch, task, curate). | stale fixed |
| `docs/build/README.md` | "one row per landed chain row (rows 1-66)" → rows 1-199 (P33.7 closeout). | stale fixed |
| `docs/build/reports/current/` | Regenerated by `docs/build/tools/current_projection.py generate` after the row-199 ledger append (was projecting P33.3-era control state). | stale fixed (generated) |

No cruft (dead docs) found; no mode-drift relocations needed.

## 2. Docs audited and left unchanged (verified current at HEAD)

`docs/evaluation/README.md` (P32.9/10-authored, honestly says `tooling_ready`/`awaiting_humans`),
`db/README.md`, `evidence/README.md`, `docs/research/README.md` (frozen cache index — its counts are
the research-phase record), `docs/adr/README.md` (generated index — never hand-edited),
`CITATION.cff` (the no-production-DOI comment stays true: `D-P21.5-1`/HG-07 open),
`docs/studies/`, `docs/slice/`, `docs/build/OPERATIONAL_READINESS.md` (§(a)–(e) is a labelled
Round-3/4 snapshot; §(f) is the dated Round-10 state — preserved verbatim per its own contract),
`docs/build/CAPSTONE_CLOSURE.md` §(f) (dated, append-only), `docs/build/INTEGRATION_PLAN.md`
(carries the P33.6 supersession note — dated record, not rewritten), `docs/tickets/**`,
`docs/risk_register.md`, `docs/traceability.md` (append-only registers — dated entries stay).

## 3. Detector results

| Run | Command | Docs scanned | Broken refs | Stale suspects |
|---|---|---|---|---|
| Before (base `474f69f4`) | `bash scripts/docs/check-repo-docs-freshness.sh .` | 430 | 0 | 1 (`README.md`, mtime heuristic) |
| After | same + `make docs-check` | 430 | 0 | 0 expected — recorded in the run ledger |

Note: the detector inspects markdown-link targets only; the audit additionally caught
three **backtick path references** to files P22.3 moved into `docs/build/reports/`
(`PUBLICATION_CHECKLIST.md` ×2, `FIRST_JURISDICTION_REPORT.md` ×1) — repaired.

## 4. Commands in the docs — checked in this environment (macOS, uv workspace, Docker up)

| Command | Where documented | Checked |
|---|---|---|
| `make check` | README, CONTRIBUTING | executed — recorded in the run ledger |
| `make docs-check` | CONTRIBUTING, this report | executed |
| `make test-db`, `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/e2e` | README, CONTRIBUTING, db/README | executed under Docker (in-suite / standalone — ledger) |
| `uv run sig-ops --help` / `--version` | ops/README verb table | executed — every listed verb verified present in help |
| `uv run sig-ops up/status/down`, `seed`, `degraded` | README, ops/README | prior committed run evidence (`run_okc.sh`, FIRST_JURISDICTION_REPORT); `up`/`down` re-run under Docker where exercised by `tests/ops` |
| `sig-connectors list-connectors` | README (20 registered) | executed — 20 printed |
| `npm --prefix web run check` | web/README, CONTRIBUTING-adjacent | not run (no web code change; P33.2's run stands most recent — recorded) |
| credentialed verbs (`deploy --apply`, hosted probes, `scheduled-ingest`, `swh-save`) | ops/README, ops/gcp/README | labelled credentialed/gated in-doc; not executable in this environment — recorded, not claimed |

## 5. Remaining gaps (owned, linked — nothing closed here)

- **36 owed obligations + `SIG-MEM-004`** — unchanged; the full register is
  `docs/tickets/DEFERRALS.md` (P33.7 sweep record appended — no status change).
- **Agent-facing docs drift (out of scope — P33.8 owns).** Root `AGENTS.md` still
  describes `web/` as "static, zero-JS" and `web/AGENTS.md` still says the
  "`/curate/**` island allowance is the only exception"; both predate the three
  public islands (ADR-097/134). Reported, not fixed — `SIG-MEM-004` / manifest
  row 200 (`docs/tickets/200_P33.8__round10-agent-docs-refresh.md`) is the owner; the human-facing wording
  is corrected here.
- **A direct probe of one ICPSR research URL returned a Cloudflare challenge** —
  recorded as a blocked observation; not cited as fetch evidence anywhere.
- **Legal home posture** — HG-01 interim (personal capacity) stands; counsel review
  (`D-LEGAL.1-1`) open. Docs name roles/interim posture only.

## 6. History preservation notes

Dated historical records were kept verbatim: the P22.1 report above, the Phase-21
CHANGELOG blockquote (its claims are about that phase), the OPERATIONAL_READINESS
§(a)–(e) snapshot (its own §(f) header declares it a Round-3/4 record), every
`runs/`/`pr/`/`readouts/` entry, the append-only registers, and the generated spec /
ADR index (never hand-edited). The only edits were to living docs, plus the
regenerated `reports/current/` projection.
