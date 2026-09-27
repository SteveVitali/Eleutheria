# P32.6 — Legacy evidence audit + recovery planner: dry-run evidence packet

`SIG-TRUST-007` · `evidence-audit/1` + `recovery-plan/1` (ADR-125) · offline-only
(`live_verification=false` — nothing hosted or public was touched by this run).

## Contents

| file | what it is |
|---|---|
| `fixture_spine.json` | the audit input of record — 16 claims in the `evidence-audit-rows/1` loader shape, hand-built to cover every fixture class the ticket requires (recoverable, digest-mismatched, missing, restricted/sealed, synthetic-only, unsupported role), stratified across 2 source families × 2 capture epochs × roles × 3 compartments |
| `capture_root/` | a real OCFL 1.1 root fixture — objects for the recoverable and restricted captures, deliberately **different bytes** for the digest-mismatch captures, and no object at all for the missing/sealed ones |
| `targeted_ids.txt` | the separately-reported targeted set (publication-sensitive / known-problem fixtures) |
| `adjudications.json` | the adjudicator instrument's verdicts for the targeted set |
| `audit_report.json` | the reproducible `evidence-audit/1` report (deterministic: same input + seed ⇒ byte-identical output) |
| `AUDIT_REPORT.md` | the human-readable summary (strata, denominators, metric table, semantic trio, findings) |
| `recovery_plan.json` | the `recovery-plan/1` dry-run plan — append-only proposals, zero-write rules, batches, estimates citing the measured ceilings |
| `plan_digests.txt` | the action digests — an applier's resume marker; feeding them back yields a +0 re-plan |
| `LIVE_RETURN_PASS.md` + `live_return_pass_packet.json` | the **prepared, unexecuted** live pass contract — pinned commands, ceilings and the checklist for the later hosted read-only run (D-R10-LIVE-1, owner P32.22) |

## The dry-run command lines (reproduce byte-for-byte)

```sh
uv run sig-ops evidence-audit \
  --input-json docs/build/reports/p32.6-legacy-evidence/fixture_spine.json \
  --capture-dir docs/build/reports/p32.6-legacy-evidence/capture_root \
  --seed p32.6-fixture-seed-v1 --sample 16 \
  --targeted docs/build/reports/p32.6-legacy-evidence/targeted_ids.txt \
  --adjudications docs/build/reports/p32.6-legacy-evidence/adjudications.json \
  --out <outdir>

uv run sig-ops recovery-plan \
  --audit <outdir>/audit_report.json --out <outdir>
```

## Fixture classes → results (all 16 claims sampled)

| class | claims | grade | semantic verdict |
|---|---|---|---|
| recoverable (verified bytes + occurrence + locator + extractor) | 8 | `exact_replayable` | `established` (mechanical byte_range replay) |
| digest-mismatched bytes | 2 | `unrecoverable` + `digest_mismatch` finding | `unresolved` (evidence unavailable) |
| missing bytes | 2 | `unrecoverable` + `missing_bytes` finding | `unresolved` (evidence unavailable) |
| restricted (verified, tier `restricted`) | 1 | `restricted_not_public` | `unresolved` (evidence unavailable) |
| sealed (unreadable at this root) | 1 | `restricted_not_public` + `restricted_unverified` — never `missing` | `unresolved` |
| unsupported role (operator predicate, synthetic-only) | 1 | `source_attributed_only` + `unsupported_role_mapping` | `not_established` (adjudicator) |
| synthetic-only attribute | 1 | `source_attributed_only` | `unresolved` (needs adjudication) |

Semantic trio: support over all sampled eligible **8/14 = 57.1%**; conditional
fidelity **8/14 = 57.1%** (the 6 evidence-unavailable units stay in the
denominator — missing evidence cannot inflate the number by disappearing);
adjudication yield **8/14 = 57.1%**.

Recovery plan: 2 proposed `publication_disposition` withholds (the two public
missing-bytes claims), 0 writes for every ambiguous/unrecoverable/restricted/
mismatched unit, 1 batch, `+0` on restart via `plan_digests.txt`. Nothing was
applied anywhere.
