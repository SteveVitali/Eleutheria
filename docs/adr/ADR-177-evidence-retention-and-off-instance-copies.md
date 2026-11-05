# ADR-177 — Evidence retention: the dedicated bucket, the 365-day unlocked policy, and the off-instance copies (P37.3)

- Date: 2026-11-05
- Status: accepted
- Ticket: P37.3 (Round 11 / P37, row 421 — R11-OPS-04, SIG-STORE-048;
  G1-RET [B-14] = a carried verbatim; COV-14)
- Base: `r11/P36.73-sub-round-11c-acceptance`
- Related: ADR-023 (the OCFL write-once store), ADR-175 (the logical-export
  policy this row copies off-project), ADR-181/ADR-189 (WV-06/WV-11 — the
  operator-only deletion path the unlocked policy preserves), ADR-201 (the
  conditioned capture-rewrite grant carried onto the new bucket),
  ADR-203 (the seal whose material the replica excludes),
  D-P37.3-1 (the queued apply leg), D-P34.42b-1 (the standing review row
  whose owner is this row)

## Context

SIG-STORE-048 requires the hosted OCFL capture store and the ops run/probe
records to be protected against overwrite and deletion by a bucket retention
policy or by object versioning with ≥ 90-day noncurrent retention — and
forbids any document calling a store WORM until such a control is in force.
G1 §3.1's protection matrix names the shape: a dedicated `…-sig-evidence`
bucket with a retention policy, captures moved out of `sig-restricted`,
runtime writers without delete, and off-instance copies (a weekly replica
and a cross-project monthly-export copy, G1-03). The operator's answered
decision fixes the retention value: `G1-RET [B-14] = a` — **365 days,
unlocked** — so lawful takedowns and the WV-06 deletion path stay possible
(B-14, "Accept all three (Recommended)", 2026-10-01T04:39:45Z).

Three design points needed deciding:

1. *How "an ingest SA delete attempt on a capture fails" is enforced.* IAM
   alone cannot express it: `storage.objects.delete` under a prefix is a
   role verb, and ADR-201 showed the OCFL inventory-head rewrite needs
   object-replace under `evidence/captures/` (the conditioned `objectUser`
   grant). A bucket **retention policy** is the control that makes the
   delete fail regardless of the grant — under an unlocked policy no
   principal, not even the operator, may delete or overwrite an object
   inside its retention window, while versioning still lets an overwrite
   land as a new generation. The IAM posture (create + read + conditioned
   rewrite) is least-privilege; the retention policy is the enforcement
   the acceptance shape reads.
2. *What "captures moved" means under the append-only posture.* The leg
   copies `evidence/captures/` restricted → evidence (additive — the
   source objects are never deleted; deletion is the operator's WV-06 act,
   never an ops script's) and repoints every ingest job's `captures`
   volume onto the new bucket, so the evidence bucket becomes the write
   target and the restricted copies remain only as history under their
   versioning + 90-day noncurrent lifecycle.
3. *How sealed material stays off the off-instance copies* (the S4c plan
   note: "exclude or separately encrypt"). After the move, every capture —
   including every `capture_seal`-sealed one — lives under exactly
   `evidence/captures/` on the restricted bucket. The weekly replica
   therefore excludes that prefix **wholesale**: the sealed-material
   exclusion needs no seal lookup on the copy path, and a sealed object
   can never reach the replica. `ops/seal/` (ids/digests/counts metadata)
   is not excluded — the deny set must survive an off-instance restore.
   The monthly-export copy touches only `pg/monthly/` — spine dumps carry
   no captures by construction, so no exclusion is needed on that path.

## Decision

1. **One dedicated evidence bucket, retention declared and unlocked.**
   `<project>-sig-evidence`: private, uniform bucket-level access,
   versioning on, retention policy `retention_period_seconds = 31536000`
   (365 days) with `is_locked = false`. Locking is a later review decision,
   never this leg's.
2. **The ingest identity's posture is carried, not widened.** On the
   evidence bucket `sig-ingest-rt` holds `objectCreator` + `objectViewer`
   plus the one conditioned `objectUser` under `evidence/captures/`
   (title `p37-3-capture-rewrite`, the ADR-201 shape); the exec host's
   conditioned read follows the store; `sig-probe-rt` reads bucket
   metadata on both new buckets for live-diff. No unconditional delete is
   granted anywhere; the retention policy fails a delete regardless.
3. **The off-instance copies are append-only `copyTo` jobs, records on
   the destination.** `sig-restricted-replica` (weekly, Sunday 09:00Z)
   copies `sig-restricted → <project>-sig-restricted-dr` (dual-region
   `nam4`) excluding `evidence/captures/`, parity rule
   `dest == source − excluded` with every exclusion enumerated;
   `sig-pg-export-copy` (monthly, day 2 14:30Z) copies `pg/monthly/` on
   `sig-backups` to `<SIG_BACKUP_PROJECT>-sig-backups`, parity
   `dest == source`. Both emit `sig.restricted-replica/1` /
   `sig.pg-export-copy/1` on the **destination** bucket — the record
   survives the source, which is the point of an off-instance copy.
   `sig-replica-rt` is declared `reserved` in `sig.iam-identities/1`
   until the leg binds it (the leg's own amendment claims the two jobs
   and bumps `expected_job_count` to 102).
4. **The whole mutation is one bounded, pre-authorised, window-guarded
   leg.** GATE-G6 §4 (2026-11-05T15:20Z, "Approve all 15 (rec.)") names
   P37.3 verbatim; `ops/gcp/evidence-store.sh` enforces never
   03:00–10:00Z (exit 42 queued), `SIG_EVSTORE_AUTHOR` per apply, the
   repoint leg refusing while any ingest execution runs, and a retention
   delete-probe that MUST fail. It stayed QUEUED `prepared_not_executed`
   at the engineering dispatch (`SIG_GCP_PROJECT` absent → `D-P37.3-1`,
   OM-19 re-run prompt in the contract).

## Consequences

- `sig-evidence` becomes the capture store of record; the restricted
  bucket's `evidence/captures/` prefix is history only.
- A capture survives ingest-SA compromise, accidental deletion and — for
  365 days — even an operator delete, while lawful takedown remains
  possible at window end or through WV-06's logged path.
- `ops/probes/` and `ops/runs/` remain honestly *not-WORM* until P34.3's
  queued versioning leg lands (versioning + 90-day noncurrent is the
  SIG-STORE-048 alternative for ops records; the README says so).
- The second-project copy is gated on `SIG_BACKUP_PROJECT`; without it
  the `pg-export-copy` leg records QUEUED inside the same apply.

## Revisit trigger

Revisit when (a) the evidence store's write path stops rewriting OCFL
inventory heads in place (the conditioned rewrite grant can retire —
D-P34.42b-1's trigger), (b) the 365-day window is reviewed for lock or
duration change (a new operator decision), (c) a second project is named
and the export-copy leg runs, or (d) GCS IAM gains narrower-than-prefix
object-verb conditions.
