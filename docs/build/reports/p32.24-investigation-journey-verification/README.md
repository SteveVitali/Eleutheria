# P32.24 — the public investigation acceptance portfolio

**Schema family:** `sig.journey-portfolio/1` + `sig.journey-corpus/1` +
`sig.journey-intake-proof/1`.
**Requirement:** SIG-FIND-007 · **ADR:** ADR-143 ·
**Ticket:** `docs/tickets/189_P32.24__investigation-journey-verification.md`
(Round 10 / S4, row 189). **Verification mode:** `live_verification=false` —
everything here is offline over committed bytes and a throwaway PG18 container;
nothing fetched, nothing published, nothing activated.

## What this packet is

The acceptance readout for the public investigation surface. It verifies two
things, kept strictly separate:

1. **The P32.23a candidate packet** (`candidate_dir`, read-only) — digests,
   identity, release validation state, deferral dispositions, zero-JS
   footprint, and the honest fact that **this candidate publishes zero
   records** (its fixture-seeded repaired spine exports 16 claims, but the
   bound release projection materializes no `sig.published-record/1` rows).
   Candidate checks are `pass`/`not_applicable` — never fabricated into
   record coverage.

2. **The acceptance corpus release** — a declared `sig.journey-corpus/1`
   export (75 records across two licence compartments: `sig_graph` CC-BY-4.0 +
   `osm_physical` ODbL-1.0) built and staged through the **real**
   `exports.release.build_release` + `activate` path into a scratch registry
   under this directory — never the published registry. Every
   record/dossier/edge/withdrawal journey leg runs over that staged release.

Journey **C** (intake → moderation → canonical correction) ran on a real
`postgis/postgis:18-3.6` testcontainer with the full sqitch plan; the emitted
`sig.journey-intake-proof/1` is folded into the portfolio so the C checks are
executed `pass`, not assumed.

## Files

| file | contents |
|---|---|
| `JOURNEY_PORTFOLIO.json` | `sig.journey-portfolio/1` — the machine readout: subject (candidate identity + eval posture), acceptance_release (pub id + manifest digest), every check with evidence class (`automated_conformance` / `agent_walkthrough` / `independent_human`), status, detail, expected answer, owner + landing, and the honest-gaps roll-up |
| `JOURNEY_PORTFOLIO.md` | the rendered readout — verdict table + honest gaps |
| `INTAKE_JOURNEY.json` | `sig.journey-intake-proof/1` — the real-PG journey-C execution: 10/10 steps (submit → restart → queue → approve → apply → exactly-once retry → publish linkage → resolved → live receiver-role refusals) |
| `corpus_export/` | the `sig.journey-corpus/1` acceptance export — `manifest.json` + `corpus.json` (the declared cases + expected answers) + compartment `sites.jsonl`/`record_claims.jsonl` + `web/` payloads |
| `corpus_release/` | the staged release built from the corpus — descriptor `p-81f1986a…`, integrity manifest, per-compartment records + FTS5 search indexes + browse/jurisdiction pages + dossier/evidence pages |
| `corpus_registry/` | the scratch serving registry — the corpus release **staged** (never the published registry) plus the recorded `denied`/`withhold` dispositions and their tombstoned routes |
| `WALKTHROUGH_LOG.md` | the agent-walkthrough record — keyboard, print, back/forward, release-citation, receipt→moderation narrative, each tagged by evidence class |
| `USABILITY_TASK_PROTOCOL.md` | the moderated-session task protocol — the compensating control for `D-R10-USERS-1`; run verbatim when volunteers exist |

## Verdict — **PASS** (with disclosed deferrals)

38 checks: **31 pass · 3 verified_by_test · 2 deferred · 2 not_applicable ·
0 fail.**

- `not_applicable` — `candidate.record_surface`, `B.candidate_network`: the
  candidate publishes no records/edges on this build. Owner `D-P32.23a-1` →
  the production candidate at the `D-R10-LIVE-1` return pass.
- `deferred` — `B.eval_deferred` (any configured≈observed or
  certified-resolved interpretation awaits the deferred S3 human-evaluation
  spine, `D-R10-HUMAN-1`) and `UX.independent_sessions` (no volunteers;
  `D-R10-USERS-1` stays **OPEN**, the task protocol is the compensating
  control).
- `verified_by_test` — the browser-interaction legs (`WT.keyboard`,
  `WT.back_forward`, `WT.receipt_to_moderation`) whose interactive proof is
  owned by the web e2e / DB suites; the emitted-bytes half is verified
  inline.

## Evidence classes

| class | meaning | count |
|---|---|---|
| `automated_conformance` | deterministic checks over released bytes / the PG proof | 31 (27 pass + 2 deferred + 2 n/a) |
| `agent_walkthrough` | agent-executed walkthrough, recorded in `WALKTHROUGH_LOG.md` | 6 (3 pass + 3 verified_by_test) |
| `independent_human` | a real moderated session — **none run** | 1 (deferred) |

No human-usability result is claimed anywhere in this packet. `eval=deferred`
is restated on every journey that could read as an evaluation claim.

## Reproduce

```sh
uv run sig-ops journey-verify \
  --out docs/build/reports/p32.24-investigation-journey-verification \
  --intake-proof docs/build/reports/p32.24-investigation-journey-verification/INTAKE_JOURNEY.json

# the PG leg (Docker): emits the proof this portfolio folds in
uv run sig-ops journey-intake \
  --dsn postgresql://sig:sig@127.0.0.1:5432/sig \
  --publication p-81f1986aac5cb18b29f2dae0458f74d8b639f6efc1a9de35abc38167b126d2dd \
  --record sig_graph:deployment:ent-acc-dep-00 --key p3224report \
  --out INTAKE_JOURNEY.json
```

**Not claimed:** production candidate verification (that is `D-R10-LIVE-1`'s
return pass), live serving verification, human usability results, a final
evaluation decision, publication or activation. The candidate's `latest.json`
was never touched; the scratch `corpus_registry/` is evidence bytes only.
