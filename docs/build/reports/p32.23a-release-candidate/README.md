# P32.23a — the post-evaluation release candidate (fixture build packet)

**Schema family:** `sig.release-candidate/1` + `sig.candidate-identity/1` +
`sig.candidate-materialization/1` + `sig.candidate-disclosure/1` +
`sig.candidate-rollback/1` + `candidate-return-pass/1` +
`sig.candidate-manifest/1`.
**Requirement:** SIG-TRUST-010 (§55.8) · **ADR:** ADR-142 ·
**Ticket:** `docs/tickets/188_P32.23a__post-evaluation-release-candidate.md`
(Round 10 / S1, row 188).

## What this packet is

The ONE unpublished release candidate built from the frozen P32.22 repaired-input
snapshot — on the **engineering fixture spine** (PG18+PostGIS testcontainer, the
same deterministic P32.6 fixture the P32.22 stage used). The production half of
this obligation is the operator-gated live pass under `D-R10-LIVE-1` — still
**OPEN**; `LIVE_RETURN_PASS.json` pins it.

The S3 human-evaluation spine (HUMAN-H4 → P32.22a → HUMAN-H5 → P32.23) is
**deferred wholesale by explicit operator choice (2026-10-19)** — there is **no
final evaluation decision**. The candidate therefore builds under the active
**PROVISIONAL** resolution policy with the deferral disclosed everywhere the
candidate is described: the identity document, the manifest, the disclosure,
the exclusions note inside the export bytes, and the
`provisional-ruleset/1` ruleset stamp every artifact carries.

## Files

| file | contents |
|---|---|
| `CANDIDATE_MANIFEST.json`/`.md` | `sig.candidate-manifest/1` — the roll-up P32.24 validates: identity digest, input digests, frame check, materialization (+0), staged release + descriptor/manifest digests, pointer state, disclosure, rollback packet, deferral dispositions |
| `DISCLOSURE.json`/`.md` | `sig.candidate-disclosure/1` — change (4 applied / 0 failed, +0 rerun), suppression (3 dispositions + refused-slice totals), and the provisional/review-only evaluation disclosure; `prior_preview_counts_reused: false` |
| `ROLLBACK_PACKET.json`/`.md` | `sig.candidate-rollback/1` — prepared pointer-reversal plan (`prepared_not_needed`): the `latest.json` rollback steps, the recorded prior pointer (none existed), the immutable-namespace retention rule |
| `MATERIALIZATION.json` | `sig.candidate-materialization/1` — the six-step dependency order (resolution → camera-sites → edges → contradictions → coverage → accountability), pass-1 `+3` (coverage), rerun `+0`, and the appended `ingest_run`/`ingest_run_completion` ids |
| `LIVE_RETURN_PASS.json` | `candidate-return-pass/1`, `prepared_not_executed` — the production-candidate commands + checklist + reservations keeping `D-R10-LIVE-1` OPEN |
| `candidate_export/` | the licence-compartmented export under `provisional-ruleset/1` — `manifest.json` (reproducibility inputs pin the provisional ruleset), `exclusions.json` (deferral note inside the bytes), `sig_graph/` table artifacts, `web/` surfaces incl. `research_dossiers.json` (the three committed `sig.dossier-packet/1`s recomposed) + `web/analytics/*` |
| `candidate_release/` | the staged-but-never-activated release namespace — `releases/p-17b713…/` descriptor/integrity manifest/catalog entry + `r/p-17b713…/` bound artifacts (18 manifest-listed artifacts, all 16 of them `c/web/evidence/<uuid>/` anchor pages; `input_records`/`output_records`/`dossier_pages` = 0 — the fixture corpus projects no publishable `sig.published-record/1` rows, an honest 0 never fabricated) |
| `_regen_snapshot/` | the fresh `sig.repaired-snapshot/1` this run froze over the re-seeded fixture — its `population_frame` reconciles digest-for-digest with the committed P32.22 snapshot; execution-provenance fields (execution id, minted repair-claim id, timestamps) differ as expected |

## The identity

```json
{
  "ruleset_version": "provisional-ruleset/1",
  "frozen_snapshot_digest": "sha256:138714a684982c982610ece27a8215fc93e0c4cc4a220b7574307ad358695d99",
  "evaluation": {"status": "deferred", "policy": "eval-confidence/1", "mode": "shadow", "applied": []},
  "identity_digest": "sha256:bc20d4bfbc3845896b69c6bfde71b2b588d9e15d385d7c956e1c3f9c64bf4f2f"
}
```

Cross-artifact agreement by construction: the export `manifest.json`
`reproducibility_inputs.ruleset_version`, the release `descriptor.json`
`ruleset_version`, the analytics `provenance.json` ruleset stamp, the ingest_run
row's `ruleset_version`, and this manifest's identity all read
`provisional-ruleset/1`; the descriptor's `data_release_id`
(`sig-2026-10-19-518afbaf`) is the release descriptor's own derived id.

## Provenance of the fixture run

Rebuilt on a throwaway `postgis/postgis:18-3.6` container with the real sqitch
plan: `seed_fixture_spine` → `run_audit` (`p32.22-fixture-seed-v1`, 16 claims) →
`build_recovery_plan` (adjudicator repair for the unsupported unit) →
`execute_bounded_apply` (4 applied / 0 skipped / 0 failed, `rerun.plus_zero`) →
`freeze_snapshot` → `ops.release_candidate.run_candidate` with the committed
`REPAIRED_SNAPSHOT.json` pinned. The committed snapshot's population frame
(16 ids, 13 eligible) reconciles digest-for-digest; the regenerated snapshot in
`_regen_snapshot/` differs only in execution-provenance fields (execution id,
the newly minted repair-claim id, watermarks) — the population semantics are
identical.

**Not claimed:** production recovery, hosted OCFL verification, human labels,
a final evaluation decision, publication, GATE-G3/HG-11. `eval-confidence/1`
stayed `mode=shadow` with `applied=[]`; P32.10's confidence policy was never
activated; `latest.json` was read before and after staging and never written.
