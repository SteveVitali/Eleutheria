## Summary

**E2-12-BACKFILL-1 — DONE.** Applies the second attribution-corrections artifact
(`sig.attribution-corrections/1`, all 34 source/record pairs) to the production
sig-pg spine under the operator-signed go `c3cec493`, clearing the
`assert_attribution_rows` refusal that stopped OPS-EXPORT-GCE-3.

The leg required a writer extension: 31 of the 34 sources are ADR-178-suppressed
public re-keys, and `rights_decision` redirects join on the **recorded** spine
`source_id` — a decision keyed on the public alias joins nothing (the reason
P34.21a-live-3's artifact never reached them). `rights_corrections.py` now
accepts `source_id_digests` (`sha256:` of the retired id), resolves the recorded
ids over `evidence_artifact`/`source_registry`/`rights_decision`, keys each
decision on the resolved id, and classifies priors **per pair** with a new
`out_of_scope` kind for reachable-but-unlisted priors. Reports emit digests,
never handles.

## Result (all read-back green)

- **Apply:** `rights_decision` +34, `rights_record` +3 — INSERT-only, 0 refused,
  104,807 claims covered. The other 31 corrected records pre-existed from the
  earlier public-id-keyed attempt; only the 3 `D-P34.21a-2` under-review
  sources' declared-attribution variants were new.
- **E2-12 gate replica:** 0 `attribution_required && empty` violations (was 34 —
  one per corrected pair).
- **Corrected pairs:** 0 claims with empty effective attribution; 0
  wrong-attribution rows. Licence-blind residual 115,301 → 10,494 = exactly the
  out-of-scope `dot_511_ky`/`dot_511_ut` `CC0-1.0` priors (no attribution
  required — untouched, never relicensed).
- **Insert-only held:** `n_tup_upd`/`n_tup_del` +0 on all 8 spine tables;
  second `--apply` wrote 0 rows.
- **Preconditions recorded:** `protect.sh --verify` 11 OK / 0 DRIFT, ON_DEMAND
  backup `1795588277489` SUCCESSFUL, probe-run 06:32Z ≤ 24 h, apply at 06:36Z
  outside the 03:00–06:30Z never-band.

## Records

- `D-E2-12-BACKFILL` registered OPEN in DEFERRALS + `:e0` anchor (`2028d82c`),
  closed `:e1` DONE with cell flip + PHASE LOG row (`e45b346f`);
  `obligation_events check` green (799 events).
- Run ledger `docs/build/runs/E212-BACKFILL-1.md`; evidence under
  `docs/build/logs/e212-backfill-1/` (gitignored).

## Follow-on

`assert_attribution_rows` is green — the GCE export leg (`D-P37.65a-1` chain)
can be re-dispatched.

Generated with [Devin](https://devin.ai)
