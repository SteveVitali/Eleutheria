# P32.25 — accepted release publish + public verification + rollback

**Verdict: pass** — checks=25 (25 pass, 0 fail, 0 deferred, 0 n/a)

The subject is exactly the GATE-G3-accepted P32.23a fixture candidate — this is a **bounded/staging-namespace** proof of the publish + verify + rollback machinery over that artifact set. **No production exposure is claimed**: nothing was served publicly, no intake operation ran, no synthetic submission was sent, and the deferred-evaluation posture is carried, not resolved.

## Accepted pins

- publication `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587`
- identity `sha256:bc20d4bfbc3845896b69c6bfde71b2b588d9e15d385d7c956e1c3f9c64bf4f2f`
- frozen snapshot `sha256:138714a684982c982610ece27a8215fc93e0c4cc4a220b7574307ad358695d99`
- descriptor `17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587`
- release manifest `3966c7657b7b30b379c50608e6cb6d35f90b29bd03b0f336716bca48fc9a23ce`
- ruleset `provisional-ruleset/1` — evaluation `deferred`/`shadow`/`applied=[]`

## Pointer transition

- before: `null`
- after: `{"data_release_id": "sig-2026-10-19-518afbaf", "manifest_sha256": "3966c7657b7b30b379c50608e6cb6d35f90b29bd03b0f336716bca48fc9a23ce", "ordinal": 1, "publication_id": "p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587", "schema": "sig.latest-pointer/1"}`

## Checks

| check | status | detail |
|---|---|---|
| `PF.gate_signed` | **pass** | GATE-G3 readout records SIGNED acceptance of the exact candidate (publication + identity + frozen snapshot pinned in the readout) |
| `PF.candidate_pinned` | **pass** | CANDIDATE_MANIFEST pins exactly the accepted publication, descriptor, manifests, identity, snapshot, ruleset and deferred evaluation — nothing else can be published by this run |
| `PF.release_bytes` | **pass** | validate_release=complete; all 18 manifest artifacts re-hashed byte-for-byte against the approved digests |
| `PF.disclosure_posture` | **pass** | DISCLOSURE pins evaluation.status=deferred / mode=shadow / decision=null / applied=[] / resolved_sites=null; the 3 recorded dispositions + loudly-recorded exclusion totals carry the withheld slices — nothing silently dropped |
| `PF.dossier_scope` | **pass** | all three dossiers carry the reduced GATE-G3 scope honestly — review.status=not_run, pilot_complete=False; mechanical_complete reported per-dossier (never a completion claim) |
| `PF.rollback_packet` | **pass** | the P32.23a rollback packet is prepared: pointer-only reversal, immutable namespace retained, and the no-prior-pointer path recorded for this first-release candidate |
| `P.validate_first` | **pass** | activate() ran validate_release first — state=complete, artifacts_checked=18: the latest pointer can only move on a fully-verified release |
| `P.pointer_transition` | **pass** | latest.json flipped atomically: absent (no prior release — this is the first immutable namespace) → p-17b713cee4f4f605f7… with the pinned manifest digest |
| `P.catalog` | **pass** | the catalog registers exactly the accepted publication — pinned manifest digest, honest 0 records, no compartments |
| `P.staged_revalidates` | **pass** | post-publish staged tree re-validates: state=complete, artifacts_checked=18 |
| `P.activation_receipt` | **pass** | the activation is receipted under activations/ with validator + withdrawal-application evidence |
| `V.digests` | **pass** | all 18 published artifacts re-hash to the approved sha256+size over the served tree; 0 undeclared files under the public routes |
| `V.http_reads` | **pass** | 23 unauthenticated GETs over a plain static server — every manifest route answers 200 with the approved bytes; the directory routes serve their index pages |
| `V.citations` | **pass** | the immutable /r/<pub> routes carry 'cite this URL' marking; a selector naming this cut redirects to the immutable namespace, the bare selector answers the latest convenience pointer, and a pre-release selector is honestly unavailable — never substituted |
| `V.records_honest_zero` | **pass** | the fixture candidate publishes 0 records — the catalog entry, the record route tree and the entity convenience stubs all agree (no phantom record surface) |
| `V.search_honest` | **pass** | release-scoped search over the published artifact set answers the honest state — 404 unknown_compartment for the 0-record candidate's compartments, 404 unknown_publication for a phantom namespace; there is no silent fallback to current-spine data |
| `V.tiles_honest` | **pass** | no tile artifact is declared or staged for this candidate — honestly absent, not masqueraded |
| `V.withdrawal_barrier` | **pass** | the staged registry carries zero withdrawal dispositions — every manifest route is route_access-permitted and the generated deny map is empty (the barrier itself is exercised in R.*) |
| `V.suppressed_slices` | **pass** | the 3 spine-level dispositions are recorded loudly in the packet (exclusions.json + DISCLOSURE) and no withheld record or edge appears anywhere on the public surface — the 0-record surface contains nothing to leak |
| `V.disclosures` | **pass** | the provisional basis is on the published surface: descriptor + landing carry ruleset=provisional-ruleset/1; no artifact anywhere asserts a completed pilot, a final evaluation decision, or a certified resolved-sites count (eval.status=deferred everywhere) |
| `V.intake_unavailable` | **pass** | the receiver is honestly unavailable: ops/config.toml operational=false, the env gate is unset, /intake/new and POST /intake/v1/reports answer 503 receiver_not_operating, and no published byte advertises a live submission surface. No synthetic report was submitted — none are authorized. |
| `V.zero_js` | **pass** | every published page is script-free (SIG-UI-036/037 zero-JS public surface) |
| `R.prior_release` | **pass** | prior-release rollback restores the pointer atomically: latest p-17b713cee4f4f6… → p-81f1986aac5cb1…; the candidate's non-denied bytes still serve byte-identically at their immutable routes (old citations preserved), current withdrawals keep denying under the rollback (artifact tombstone + entity deny), the catalog keeps both activations and the rollback is receipted |
| `R.no_prior_pointer` | **pass** | the ROLLBACK_PACKET path — with no prior pointer, reversal removes latest.json entirely rather than fabricating a predecessor: the catalog keeps the activated history, the immutable routes keep serving identical bytes, and the convenience pointer is honestly absent |
| `R.refused_deploy` | **pass** | a tampered release can never partially deploy: activate() refuses on validate_release before staging, leaving latest.json, the catalog and every served byte byte-identical — the previous release remains, atomically |

## Rollback rehearsals

- **R.prior_release** — `docs/build/reports/p32.25-accepted-release-verification/rehearsal/prior_registry`
- **R.no_prior_pointer** — `docs/build/reports/p32.25-accepted-release-verification/rehearsal/no_prior_registry`
  - the candidate's real rollback shape — remove latest.json, never fabricate a predecessor; immutable routes stay reachable
- **R.refused_deploy** — `docs/build/reports/p32.25-accepted-release-verification/rehearsal/refused_registry`
  - validate_release refuses a corrupted bundle before staging — the previous pointer is untouched

## Live rollback instructions (return pass — prepared, not executed)

- **roll back to a prior activated release** — `exports.release.rollback(<registry>, <prior_pub>) — pointer-only; immutable bytes stay; current withdrawals re-apply under the rollback; receipted under activations/`
- **this candidate has no prior pointer** — `exports.release.clear_latest_pointer(<registry>) — removes latest.json, re-emits the overlay, receipts; the r/<pub> namespace stays reachable as immutable history`
- **post-publish withholding** — `record_withdrawal(<registry>, [<disposition>]) — denied routes tombstone (sig.tombstone/1) + the nginx deny map regenerates; unaffected bytes are untouched`

## Residual production obligations (recorded, never claimed)

- `D-R10-PUBLISH-1` — release-exposure authorization signed at GATE-G3; the production-exposure half stays OPEN until an actual public serve
- `D-P32.23a-1` — the production release-candidate build over the hosted repaired snapshot — the fixture candidate proven here is not it
- `D-R10-LIVE-1` — hosted production recovery/freeze + final production candidate — the production public exposure is this return pass
- `D-P32.16-1` — intake owner/staffing/retention/secrets/role grants/infra-log exclusions unmet — the receiver stays non-operational

NOT DONE here (by contract): production serve, production candidate (D-P32.23a-1), hosted recovery (D-R10-LIVE-1), intake operation (D-P32.16-1), any evaluation decision, any usability session, merge/tag/push-main.
