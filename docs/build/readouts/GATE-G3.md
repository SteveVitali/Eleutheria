# GATE-G3 — signed readout

Status: **SIGNED — publish approved with the explicitly recorded scope below.**

Contract: `docs/tickets/190_GATE-G3__round10-publication-gate.md`.
Decision domain: HG-11 publication, source/exposure/operating approvals as separately scoped.

- [x] No unresolved public-safety/rights/unsupported-affirmation blocker or OPEN obligation scoped as required-for-publication remains. The required-for-publication set is the candidate itself, the release machinery (P32.13–P32.15), the journey portfolio (P32.24, verdict pass), and the withdrawal/redaction barriers (P32.5/P32.13) — all landed and verified. The deferred S3 spine and `D-R10-USERS-1` are *not* publication prerequisites: the candidate discloses `evaluation.status=deferred` and the PROVISIONAL-eval disclosure stays on every "resolved sites" surface.
- [x] Only actual operator decision signs the gate; absent/declined approval leaves candidate unpublished. — The operator's explicit decision is recorded here.
- [x] Three dossiers meet the fixed pilot rubric and independent semantic review, **or** the operator explicitly records a reduced/incomplete publication scope without claiming pilot completion. — **Reduced/incomplete scope recorded:** the independent dossier semantic review is deferred with the S3 spine (operator decision 2026-10-19); the dossiers publish as `mechanical_complete` (OKC 34/36, San Diego 29/36, Tulsa 24/36 deliberately partial) with `review.status=not_run` and `pilot_complete=False` carried in their artifacts. **No claim of pilot completion is made anywhere.**

**Additional scope recorded by this acceptance:**
- **Intake receiver stays non-operational.** `D-P32.16-1` prerequisites (named owner, staffed rotation, retention ratification, secrets/role grants, infra log exclusions) are unmet; `[intake].operational=false` stands and the receiver is not advertised on the public surface. Publishing the release does not approve its operation.
- **Evaluation posture disclosed, not resolved.** The release carries `provisional-ruleset/1` + `evaluation.status=deferred` + `eval-confidence/1 mode=shadow applied=[]`; the deferred human-evaluation chain (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23) remains OPEN. A future accepted evaluation re-issues the release — nothing in this decision asserts it.

**Inputs under review:**
- Candidate publication `p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587`; identity `sha256:bc20d4bfbc3845896b69c6bfde71b2b588d9e15d385d7c956e1c3f9c64bf4f2f` over frozen snapshot `sha256:138714a684982c982610ece27a8215fc93e0c4cc4a220b7574307ad358695d99`.
- Evidence: `docs/build/reports/p32.23a-release-candidate/` (CANDIDATE_MANIFEST, DISCLOSURE, ROLLBACK_PACKET, LIVE_RETURN_PASS) and the P32.24 journey-verification report (`docs/build/reports/p32.24-investigation-journey-verification/`).
- Intake operating packet: `docs/governance/intake-receiver-operating-packet.md`.

**Decision:** sign/accept — publish the candidate under the recorded scope. Consequence: P32.25 executes the publish + verify + rollback rehearsal for `p-17b713…`; `D-R10-PUBLISH-1`'s release-exposure half is satisfied by this signature; the intake-operation half remains scoped out above.

Authority: repository operator. Date: 2026-10-19.
