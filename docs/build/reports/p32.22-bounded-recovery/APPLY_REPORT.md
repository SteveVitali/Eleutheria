# Bounded recovery apply — execution `exec-p32-22-fixture-v1`

> Engineering stage on the fixture/test spine. The production execution is
> the operator-gated live pass (`LIVE_RETURN_PASS.json`); `D-R10-LIVE-1`
> stays OPEN.

- status: **complete** · authority `op:p32-22-fixture-authority (engineering stage, live_verification=false)`
- pins: plan `sha256:73a3f75e037222900617c59d0408b15257f931cc4594784819e828c53f6ae17f`, audit input `sha256:d9edce6e37e87141cc92d13bf6f35fa70d1ead72b242ba376ae7c10b9a5931d6`, role `sig_recovery`
- scope: 4 actions selected (15 excluded), dry-run↔applied `True`
- counts: {'applied': 4, 'conflict_existing': 0, 'already_applied': 0, 'skipped': 0}

## Before/after inventory

| table | before | after | Δ |
|---|---|---|---|
| claims | 3 | 3 | 0 |
| claim_evidence | 3 | 3 | 0 |
| publication_disposition | 0 | 3 | 3 |
| recovery_application | 0 | 4 | 4 |
| ingest_run | 2 | 3 | 1 |

## Results

- `17061f1acaa5…` record_disposition → **applied** → disposition `4512f706-dd71-4495-9756-82d34a6b86bd`
- `4123531823d8…` repair_claim → **applied** → new claim `01a0e454-a576-754d-a760-e664a8b0a583`
- `423b83b60bdb…` record_disposition → **applied** → disposition `fa45ce23-1f7c-4fe3-a74d-82443cf191b8`
- `a8e56f9e35ad…` record_disposition → **applied** → disposition `82451bcf-3cc3-4f56-90b0-a521f4d08218`

## Resource use

- wall clock 0.243s · workers 1 · batch bounds respected `True`
- result writes: +1 claims, +1 bindings, +3 dispositions; scoped inventory +3 dispositions, +4 receipts
- **+0 rerun verified: True**

## Rematerialization (dependency order)

- 1. resolution: 0→0 (+0, 0.051s)
- 2. camera-sites: 0→0 (+0, 0.083s)
- 3. edges: 0→0 (+0, 0.007s)
- 4. contradictions: 0→0 (+0, 0.018s)
- 5. coverage: 0→3 (+3, 0.057s)
- 6. accountability: 0→0 (+0, 0.006s)

_no code path in the applier fetches; the probe only re-reads recorded pinned bytes for digest verification_
