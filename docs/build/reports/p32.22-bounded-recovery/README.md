# P32.22 — Bounded integrity recovery + rematerialization: engineering-stage evidence packet

`SIG-TRUST-008` · `recovery-apply/1` + `recovery-apply-report/1` + `sig.repaired-snapshot/1`
(ADR-141) · **`live_verification=false`** — this entire packet ran on a throwaway
PG18+PostGIS test container seeded from the P32.6 fixture. Nothing hosted, public, or
production was touched; `D-R10-LIVE-1` stays **OPEN** and the final post-evaluation
release candidate belongs to **P32.23a** (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23 →
P32.23a is still ahead).

## What this packet proves (the ticket's acceptance lines)

- **Dry-run ↔ applied scope match.** The apply selected exactly the plan's `proposed`
  actions — 4 of 19 (3 `record_disposition`, 1 `repair_claim`), digest-for-digest
  (`scope.selected_action_digests` = the plan's proposed set). The other 15 actions are
  recorded exclusions (`no_write` / status).
- **Missing bytes never trigger a refetch.** There is no fetch/transport code in the
  applier at all — the capture probe only re-reads recorded pinned bytes for digest
  verification; unverifiable bytes yield an explicit `skipped`/`bytes_not_reverified`
  outcome (asserted in `tests/db/test_recovery_apply.py`), never a fabricated binding.
- **Checkpoint interruption + restart → no duplicate repair.** Exactly-once comes from
  `recovery_application` `UNIQUE(action_digest)` committing atomically with the canonical
  write: a restart reconciles `already_applied`, a re-plan over the recorded digests
  proposes **+0**, and the verified second run is `plus_zero: true` (`rerun` block).
- **Resource bounds recorded + respected.** One worker, the S1 §6 batch ceilings
  (10 000 assertions / 250 MiB distinct bytes) re-checked before writes, wall clock +
  before/after inventories + per-kind result writes all recorded.
- **Rematerialization follows dependency order** — resolution → camera-sites → edges →
  contradictions → coverage → accountability — every step append-only/idempotent.
- **Frozen HUMAN-H4 frame.** `REPAIRED_SNAPSHOT.json` is `frozen_unpublished` +
  `provisional_preview: true` + `not_a_release_candidate: true`, digest
  `sha256:138714a684982c982610ece27a8215fc93e0c4cc4a220b7574307ad358695d99`.
- **Provisional vs shadow.** `PROVISIONAL_VS_SHADOW.*` records that the PROVISIONAL
  production rules remain active while the eval-confidence/1 evaluator stays `shadow`
  with `applied: []` — nothing promoted, demoted, or certified; no safety demotion is
  scoped in this packet.

## The applied writes (all append-only)

| action | canonical write | authority |
|---|---|---|
| 3× `record_disposition` | `publication_disposition` rows (`withhold` / `pending_publication_review`) | the operator authorization — the plan's placeholder string never lands |
| 1× `repair_claim` | the §16.6 pair: the old claim's `sys_period` closed (the ONLY permitted update) + a NEW claim carrying `revises_claim` + `correction_reason` + the adjudicator's `asserted_by` entity + the SAME captures re-bound | adjudicator's recorded `repair_instructions` |

Post-apply eligibility: **13 of 16** claims remain publication-eligible (3 withheld —
2 unrecoverable + the superseded unsupported claim). Post-apply grade distribution:
8 `exact_replayable`, 2 `restricted_not_public`, 4 `unrecoverable`; findings preserved
(`unsupported_role_mapping`, 2× `digest_mismatch`, 2× `missing_bytes`).

## Contents

| file | what it is |
|---|---|
| `id_map.json` | fixture-id → real-uuid mapping the seeder minted (`uuid5`, deterministic) |
| `claim_ids.txt` / `targeted_ids.txt` / `adjudications.json` / `repairs.json` | the audit's population selection + targeted set + adjudicator channel, remapped to the real uuids |
| `audit_report.json` / `AUDIT_REPORT.md` | the `evidence-audit/1` report over the REAL seeded rows — reproduces the fixture's 8/14 support / 57.1% trio |
| `recovery_plan.json` / `plan_digests.txt` | the `recovery-plan/1` dry-run with repair instructions supplied |
| `APPLY_REPORT.json` / `APPLY_REPORT.md` | `recovery-apply-report/1` — scope, results, inventories, resource use, +0 rerun, rematerialization |
| `REPAIRED_SNAPSHOT.json` / `AUDIT_PREVIEW.md` | the frozen `sig.repaired-snapshot/1` frame + human-readable provisional preview for HUMAN-H4 |
| `PROVISIONAL_VS_SHADOW.json` / `.md` | the provisional-rules-vs-shadow-eligibility report |
| `LIVE_RETURN_PASS.json` / `.md` | `recovery-apply-return-pass/1` — the prepared, unexecuted operator-gated live packet (the OPEN return-pass row for `D-R10-LIVE-1`) |

## Reproduce (fixture/test-PG only)

```sh
# 1. stand up a throwaway PG18+PostGIS + sqitch deploy (tests/db harness or docker)
# 2. seed the fixture (deterministic uuid5 mapping; idempotent)
SIG_STAGING_DSN=<test-dsn> uv run sig-ops recovery-fixture-seed \
  --fixture docs/build/reports/p32.6-legacy-evidence --out <gen>
# 3. audit over the real rows
uv run sig-ops evidence-audit --dsn <test-dsn> --claim-ids <gen>/claim_ids.txt \
  --capture-dir docs/build/reports/p32.6-legacy-evidence/capture_root \
  --seed p32.22-fixture-seed-v1 --sample 16 \
  --targeted <gen>/targeted_ids.txt --adjudications <gen>/adjudications.json \
  --out <gen>/audit
# 4. plan (adjudicator repair instructions supplied)
uv run sig-ops recovery-plan --audit <gen>/audit/audit_report.json \
  --repairs <gen>/repairs.json --out <gen>/plan
# 5. bounded apply (+0 rerun verified; rematerialize in order)
uv run sig-ops recovery-apply --dsn <test-dsn> \
  --plan <gen>/plan/recovery_plan.json --audit <gen>/audit/audit_report.json \
  --apply --execution-id <id> --authority <operator-auth> \
  --capture-dir docs/build/reports/p32.6-legacy-evidence/capture_root \
  --verify-rerun --rematerialize --out <gen>/apply
# 6. freeze the unpublished snapshot + preview
uv run sig-ops recovery-freeze --dsn <test-dsn> \
  --apply-report <gen>/apply/APPLY_REPORT.json \
  --plan <gen>/plan/recovery_plan.json --audit <gen>/audit/audit_report.json \
  --capture-dir docs/build/reports/p32.6-legacy-evidence/capture_root \
  --sqitch-head 'sqitch:recovery_apply@plan-head' --out <gen>/freeze
```

## Explicit reservations

- `D-R10-LIVE-1` remains **OPEN** — the production bounded apply + hosted OCFL probe
  have not run; `LIVE_RETURN_PASS.*` is prepared, not executed.
- `D-P31.4-1` is **unchanged** — the reserved 2026-10-10 batch-05 replay-verification
  calendar row stands.
- No public pointer moved, no HG-11 decision changed, no human evaluation fabricated,
  no source-rights decision made, no person/plate data ingested or generated.
- Prior auto-writes are not certified; the shadow evaluator installed nothing.
