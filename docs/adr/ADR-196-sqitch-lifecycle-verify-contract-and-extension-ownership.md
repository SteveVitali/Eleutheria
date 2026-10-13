# ADR-196 — Sqitch lifecycle hygiene: the verify contract, extension ownership, and the CI round trip (P34.24a)

- Date: 2026-10-04
- Status: accepted
- Ticket: P34.24a (Round 11 / P34, row 228 — owns SIG-ENG-045; closes
  D-P32.10a-1 and D-P32.16a-1)
- Base: `r11/P34.23-versioning-discipline-one-version-source`
- Related: ADR-146 (date corrections append; records never rewritten), C-10
  (RATIFICATION_LOG: `db/sqitch.plan` L44–52 are never edited or re-stamped),
  F5 engineering-debt experiments (`docs/build/planning/2026-09-30-next-phase/`),
  SIG-STORE-041 (sqitch-managed physical migrations), SIG-MEM-005.

## Context

Two whole-plan lifecycle defects were carried as deferrals:

- **D-P32.10a-1** — `db/verify/shared_temporal_contract.sql` asserted
  `count(*) FROM spine_watermark = 27`. `publication_dispositions` (P32.5, the
  next plan line) legitimately adds a 28th facet, so a whole-plan
  `sqitch verify` divided by zero. Every harness ran `deploy` only, so nothing
  ever ran a whole-plan verify.
- **D-P32.16a-1** — `db/revert/extensions.sql` drops `postgis`, which the
  `postgis/postgis` image's initdb had pre-created alongside
  `postgis_topology` / `postgis_tiger_geocoder` (dependents) and
  `fuzzystrmatch`. The plan's `CREATE EXTENSION IF NOT EXISTS` was a silent
  no-op there, and the revert tried to drop an extension the plan never
  created — refused for its dependents.

Editing a landed plan line or script in place is forbidden (append-only
discipline; the change id — sha1 over name, dependencies, planner and
`planned_at` — is already stamped in a persistent local database, `sig-p332-db`,
per C-10).

## Decision

1. **A verify script asserts what its own change installs — never a global
   count of a living registry.** `verify/shared_temporal_contract.sql` asserts
   the presence of the 27 named facets it installs. Any later change that adds
   a facet carries the assertion for its own facet. An unscoped
   `count(*) FROM spine_watermark` in a live verify script fails
   `tests/unit/test_sqitch_hygiene.py`.
2. **The repair mechanism is sqitch's append-only `tag` + `rework`.** Plan
   tail: `@r11-sqitch-hygiene` then
   `shared_temporal_contract [shared_temporal_contract@r11-sqitch-hygiene]`.
   The landed scripts are preserved byte-identically as
   `*@r11-sqitch-hygiene.sql` (fixture-compared in tests). The reworked
   deploy/revert are deliberate no-ops — the schema is unchanged; the repair
   is the verify. On a database that has never deployed the change, the tagged
   instance still runs the real DDL and its original verify (27 facets exist
   at that point), then the reworked instance's no-op deploy and scoped
   verify.
3. **The plan owns only the extensions it creates.** Test and CI databases
   are created `TEMPLATE template0` — never the postgis image's initdb
   database, which pre-installs `postgis_topology`/`postgis_tiger_geocoder`/
   `fuzzystrmatch`. In a template0 database `deploy/extensions.sql` installs
   `postgis` + `btree_gist` for real and `revert/extensions.sql` drops exactly
   those, leaving `plpgsql` only. **One sqitch plan per database**: the plan
   also creates cluster-global roles, so a full revert is only defined on a
   database (and effectively a cluster) the plan owns outright. On a
   pre-provisioned database (hosted, ops compose) the `IF NOT EXISTS` deploy
   treats ambient extensions as already-present; a whole-plan revert is *not*
   supported there — that is the accepted limitation, not a bug to mask.
4. **The lifecycle is proven in CI, every PR.** `make test-sqitch-roundtrip`
   (`scripts/ci/sqitch_roundtrip.sh`, wired into the `python` job and
   `ci-local`) runs: fresh `postgis/postgis:18-3.6` container →
   `CREATE DATABASE sig TEMPLATE template0` → `deploy --verify` → `verify` →
   `revert -y` → clean-state asserts (extensions = `plpgsql`, zero non-sqitch
   relations, `sqitch.changes` empty) → `deploy --verify` → `verify`, logging
   to `docs/build/logs/sqitch-roundtrip-<UTC>.log`. The harnesses
   (`tests/db`, `tests/e2e`, `tests/api`, `tests/resolution`) share
   `tests/db/conftest.py` helpers with the same template0 posture and deploy
   with `--verify`, so the whole-plan verify runs on every DB-suite pass.
5. **`sqitch/sqitch` is pinned by digest** —
   `sqitch/sqitch@sha256:f247ab0e0b66e9c2d09a400864f7314358893f5cf209cddcc4f213f7d5bfe4d3`
   (the `latest` resolution at writing, App::Sqitch v1.6.1) in every
   operational path; a mutable tag or a different digest fails the hygiene
   test.
6. **New plan lines are clock-true and planner-true.** `planned_at` on a line
   appended after L52 must not post-date the commit that records it (the
   existing `test_no_future_date_literals.py` bound), and the planner must be
   the plan's recorded identity `Devin <devin@sig-project.org>` — set through
   `SQITCH_FULLNAME`/`SQITCH_EMAIL`, never the ambient git user.
7. **L44–52 are untouched, byte-identical** (C-10) — their stamped change ids
   stand; a date correction would be an appended record under ADR-146, never
   an edit.

## Consequences

- `sqitch deploy → verify → revert → deploy → verify` over the whole plan is
  green on every PR; the two deferrals close on the CI log's evidence.
- The `postgis/postgis` image's initdb database is no longer a plan deploy
  target anywhere in tests/CI; ops compose still deploys into it (extensions
  ambient via `IF NOT EXISTS`) — deploy-only, never reverted.
- A future change adding a watermark facet asserts its own facet; a future
  repair of a deployed change is another `tag` + `rework`, never an edit.

## Alternatives considered

- **Edit `verify/shared_temporal_contract.sql` in place** — rejected: an
  in-place edit of a deployed script; rework preserves the landed bytes as
  the tagged copy and records the repair in the plan.
- **`DROP EXTENSION ... CASCADE` or ordered drops in `revert/extensions.sql`**
  — rejected: an in-place edit of a landed revert, and CASCADE silently drops
  dependents it does not own. No SQL depends on the image-only extensions, so
  no teardown change is needed.
- **An appended `extension_dependents_teardown` change** (deploy no-op,
  revert drops the image's extra extensions) — rejected: it would fix the
  *image* environment rather than the ownership model, and keeps the tests
  exercising an extension set production never had.
- **Mutable `sqitch/sqitch:latest` retained** — rejected: the lifecycle gate
  must be reproducible; the digest is recorded and the guard bites on drift.

## Revisit trigger

Revisit when any of these hold: (a) the plan must deploy or revert on a
database it does not wholly own (e.g. a shared cluster, a hosted database
with operator-managed extensions) — the one-plan-per-database assumption and
the extension revert must then be redesigned; (b) a schema change needs its
deployed *deploy* script amended (rework with a real deploy, not just a
verify repair) — the deploy-history implications for already-deployed
databases need a fresh decision; (c) sqitch moves past the pinned digest and
the lifecycle semantics here must be re-verified; (d) `spine_watermark`
stops being a living registry (facets fixed forever) and the scoped-verify
rule can relax.
