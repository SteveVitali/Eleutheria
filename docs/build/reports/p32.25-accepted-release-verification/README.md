# P32.25 — accepted release publish + public verification + rollback rehearsal

Bounded/staging-namespace proof that the GATE-G3-accepted P32.23a fixture
candidate — publication `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587` — publishes atomically, verifies
over unauthenticated reads, and rolls back cleanly. **No production exposure
is claimed** (`live_verification=false`).

- `PUBLISH_PROOF.json` — `sig.release-publish-verification/1`: the accepted
  pins, the pointer transition, every check, the verdict
  (verdict=pass).
- `PUBLIC_VERIFICATION.md` — the human-readable report.
- `staging_registry/` — the bounded registry: catalog, latest.json, compat
  index, withdrawals, activation receipt, and the staged public tree.
- `rehearsal/` — scratch registries exercising prior-release rollback, the
  no-prior-pointer path (the candidate's real rollback shape), and the
  failed-deployment refusal. The "prior" is the committed P32.24
  acceptance-corpus release — a labelled stand-in, NOT a production
  predecessor.
- `ROLLBACK_REHEARSAL.json` — the rehearsal record + live rollback
  instructions.
- `LIVE_RETURN_PASS.json` — `sig.release-publish-return-pass/1`,
  `prepared_not_executed`: the production commands + the open deferrals
  (D-R10-PUBLISH-1 production half, D-P32.23a-1, D-R10-LIVE-1, D-P32.16-1).
