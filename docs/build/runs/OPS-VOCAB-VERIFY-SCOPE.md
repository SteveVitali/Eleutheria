# Run ledger — OPS-VOCAB-VERIFY-SCOPE (closed_vocabulary verify scope repair)

- Harness: devin-desktop/swe-2-high/subagent
- Branch: `r11/ops-closed-vocab-verify-fix` (worktree `/private/tmp/sig-vocab-fix`)
- Finding cited: **OPS-SPINE-SCHEMA-DEPLOY** (LEDGER 2026-11-20) —
  `sqitch deploy --verify` of the pending 41-change chain to production
  `sig-pg` applied 19 changes then failed on `closed_vocabulary`: the
  "every seeded predicate carries full registry metadata" assert in
  `db/verify/closed_vocabulary.sql` divided by zero because the spine
  carries 133 runtime-registered `vocab_predicate` rows with
  `skos_concept_iri IS NULL` (pre-P35.14a sink auto-registration, P19.4
  defaults). sqitch reverted all 19 — poststate == prestate. Same
  fresh-vs-existing verify class as D-P34.24b-1.

## Fix shape + rationale

`closed_vocabulary` was **never deployed on any spine** (the failed
verify rolled back its own deploy; the only prior runs were ephemeral
testcontainers on a fresh spine, where the unscoped assert trivially
held). Two options were evaluated:

- **(b) a new append-only change** — rejected: the failure is the
  change's own verify script, which `deploy --verify` runs at the moment
  `closed_vocabulary` deploys. A later change cannot retro-fix that
  assert; only re-shaping the verify tied to the change can.
- **(a) sqitch rework under a tag** — chosen, per the `@r11-verify-membership`
  / `@r11-sqitch-hygiene` precedent (ADR-196 — a verify asserts what
  holds of its own change on the spine it deploys onto). The rework is
  also the shape a repair needs if any dev/clone spine did deploy the
  change: plan history stays append-only and honest either way.

Rework layout (tag `@r11-vocab-verify-scope`, appended at plan EOF):

- `deploy|revert/closed_vocabulary@r11-vocab-verify-scope.sql` — byte-preserved
  copies of the landed scripts (the tagged instance carries the real DDL;
  deploy is INSERT-only `ON CONFLICT DO NOTHING` and needs no change).
- `verify/closed_vocabulary@r11-vocab-verify-scope.sql` — the repair: the
  metadata assert scopes to `skos_concept_iri IS NOT NULL`, the marker
  only ontology-registry seeds write (the runtime auto-registration never
  wrote it). A pre-existing NULL-iri row `ON CONFLICT` keeps is outside
  the assert **by design** — its NULL is honest runtime state, corrected
  by queued hosted work, never fabricated here. Added asserts: every
  projected predicate id (manifest = the change's own `directness_matrix`
  rows at `ruleset_version 1.0.0`) resolves to a `vocab_predicate` row,
  and every IRI-carrying row's IRI names its own slug (`'%/' ||
  predicate_id` — base-agnostic, per D-P35.38b-1 the join key is the
  slug, never the IRI). Still bites: a registry-IRI row with a malformed
  IRI or a non-IMMUTABLE NULL half-life divides by zero.
- `deploy|revert/closed_vocabulary.sql` (head) — deliberate `SELECT 1`
  no-ops; `verify/closed_vocabulary.sql` (head) re-asserts the same
  scoped invariants at the plan tip.

Per-id scoping (assert metadata over the 280 seed ids) was rejected:
`ON CONFLICT DO NOTHING` means a registry id the runtime registry had
already minted NULL-iri keeps its values verbatim — the change never
established metadata on it, so asserting over the id set can fail on
exactly the spine shape it must repair.

## Local verification

- `SIG_REQUIRE_DB_TESTS=1 pytest tests/db/test_closed_vocabulary_verify_scope.py`
  — new regression test, **green**: deploys to `er_rerun_login` (last
  change before `closed_vocabulary`), inserts the P19.4 runtime shape
  (`deployed` — a registry id ON CONFLICT must keep verbatim — and a
  never-registered id, both `skos_concept_iri IS NULL`), then
  `deploy --verify` to the tip and standalone `sqitch verify` pass;
  read-back shows the NULL rows untouched and seeds canonical; a planted
  malformed-IRI row makes `sqitch verify` fail on `closed_vocabulary`.
- `make test-sqitch-roundtrip` — **green**: fresh container deploy
  --verify → verify → revert -y → clean-state asserts → redeploy →
  verify (`docs/build/logs/sqitch-roundtrip-20261120T182710Z.log`).
- `SIG_REQUIRE_DB_TESTS=1 uv run pytest tests/db` — **807 passed**.
- `make check` — lint, format-check, mypy (506 files), verify-gen green;
  full pytest green except three failures proven pre-existing/environmental
  and outside this diff's reach: `test_secrets.py`'s GCP-id check fails
  closed by design with `SIG_GCP_PROJECT` unset (passes armed; OP-07),
  `test_release_verify.py`'s P-mode freshness check fails on a 35-day-old
  fixture age bound (identical failure reproduced on an unrelated worktree
  at `2b2b1587`), and `test_no_future_date_literals` flagged the two new
  plan lines while uncommitted (the guard bounds literals by HEAD commit
  time — clean once the lines' own commit lands).
- Docker note: amd64 images run under emulation on this arm64 host
  (`DOCKER_DEFAULT_PLATFORM=linux/amd64`; `postgis/postgis:18-3.6` has
  no arm64 manifest).

## Production implication

`sig-pg` remains at 39 deployed changes (the failed run reverted all
19). On re-deploy, the reworked plan deploys the tagged
`closed_vocabulary` instance (real DDL) whose verify now passes over the
133 NULL-iri rows, then the remaining chain, then the head no-op
instance. The ledger's named pre-requisite — a PITR-clone rehearsal
before re-deploy — is unchanged and still owed by the ops leg.
