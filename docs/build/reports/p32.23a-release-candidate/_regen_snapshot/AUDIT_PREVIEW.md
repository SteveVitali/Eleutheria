# Repaired-input audit preview — HUMAN-H4 frame

> **PROVISIONAL PREVIEW — unpublished, not a release candidate.**
> Frozen by `sig.repaired-snapshot/1` (P32.22). Human evaluation is owed;
> nothing here is a label, an eligibility verdict, or a publication decision.

- Snapshot digest: `sha256:0de1494c58b084b51d0fd39d570f83c68a33fb45b41e6e4720fae5fcbd0a39ce`
- Population: 16 claims (pre-apply `sha256:d9edce6e37e87141cc92d13bf6f35fa70d1ead72b242ba376ae7c10b9a5931d6` → post-apply `sha256:d9edce6e37e87141cc92d13bf6f35fa70d1ead72b242ba376ae7c10b9a5931d6`)
- Post-apply audit digest: `sha256:3977dcc9f17a34291b8f0939502a0986e061367fcbfcffb1c91857c5ee2bf93a`
- Actions applied: 4 (3 dispositions, 1 repair claims, 0 already-bound conflicts)

## Post-apply grade distribution

- `exact_replayable`: 8
- `restricted_not_public`: 2
- `unrecoverable`: 4

## Findings

- `unsupported_role_mapping` on `2007d8e5-4241-59e3-af19-0b4c263c9f55` — entity-ref predicate with no verified evidence supporting the role
- `digest_mismatch` on `83f41edf-a6ca-5548-94a1-42a5c91444f7` — stored bytes do not match the recorded content_digest
- `digest_mismatch` on `8daffc4c-219b-5490-bd03-62a661db27f8` — stored bytes do not match the recorded content_digest
- `missing_bytes` on `c101e8bc-4999-5309-aed4-fd9626822263` — recorded capture bytes absent from the probed root
- `missing_bytes` on `dae8cca4-dc93-5a3f-98fa-41c4c2495eca` — recorded capture bytes absent from the probed root

## Explicit reservations

- this frame is UNPUBLISHED — no public pointer, no release artifact, no HG-11 state
- human evaluation is owed (HUMAN-H4); zero labels exist in this frame
- the final post-evaluation release candidate is P32.23a's — never this artifact
- D-R10-LIVE-1 stays OPEN — the production bounded apply has not run
- D-P31.4-1's reserved 2026-10-10 batch-05 verification is unchanged
