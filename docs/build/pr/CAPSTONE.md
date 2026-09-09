## Summary

Final composed verification of the whole chain (`implement-spec`, full rigor). Closes the two scoped
integrity gaps from the capstone gap analysis, then exercises the entire build as one unit with Docker
up (29.1.3). Append-only throughout: the signed `CAPSTONE_CLOSURE.md §(b)` table and all ADR bodies are
unchanged (addenda only). Nothing merged/tagged/pushed to `main`; no source flipped; no HG gate ticked.

Spec/evidence: `docs/build/CAPSTONE_VERIFICATION.md` (new).

## What changed
- `docs/build/COVERAGE_MATRIX.csv` — MATRIX-INT-01 (2 invalid-enum rows fixed).
- `docs/research/_meta/spec_src/99a_appF_adr.md` + regenerated `docs/2_canonical_design_spec.md` — APPENDIX-F-01 (ADR-072 row).
- `docs/build/CAPSTONE_CLOSURE.md` — append-only §(b) addendum (76→77 MET-DIFFERENTLY reconciliation).
- `docs/build/CAPSTONE_VERIFICATION.md` (new) — gap closure + composed-E2E evidence + accepted deviations + human-gated items + verdict.
- `docs/traceability.md`, `docs/risk_register.md` — append-only `Capstone verification` sections.

## Gap closure
- **MATRIX-INT-01** — `SIG-STORE-003` `verdict=COVERED`→`MET` (test-cited: `tests/ops/test_degraded.py`, zero-non-PostGIS-extension §15.2); `SIG-UI-047` `class=deferred(A1-ticked)`→`deviated(ADR)`, `verdict=MISSING`→`MET-DIFFERENTLY`, `routing=P21.5`→`P20.2:spec` (same accepted zero-JS-map deviation as `SIG-UI-038`). `check_coverage_matrix.py` **exit 0** (`671 rows OK`). MET-DIFFERENTLY **76→77** (only SIG-UI-047 crosses; SIG-STORE-003 is MET) — reconciled by an append-only addendum.
- **APPENDIX-F-01** — `check_spec_src.py` flagged exactly `ADR-072` absent from Appendix F (ADR-063…071 present; ADR-064 is a skipped number). Added the row via `spec_src`, ran `BUILD.sh`. `check_spec_src.py` **exit 0** (byte-identical repro; Appendix F 71 ADRs = docs/adr set).

## Verification (composed, Docker 29.1.3)
- `make check`: **2718 passed, 1 skipped, 0 failed, 0 xfailed**.
- `make test-db`: **120 passed** (real PG18+PostGIS).
- `SIG_REQUIRE_DB_TESTS=1 pytest tests/e2e`: **16 passed, 0 skipped, 0 xfailed** — S8/LD-V08 export→web **RAN** and passed (`web/node_modules` present).
- `run_okc.sh`: **8/8** end-to-end over the composed fixture DB (no live fetch). 299-vs-190 rendered from EXPORT bytes (`unresolved_conflict`); acceptance J-1 **pass**, `{passed:2, blocked:11, failed:0}`.
- `check_coverage_matrix.py`, `check_spec_src.py`: **exit 0**.

## Known pre-existing blocker (routed to operator)
`check_backlog.py` is **exit 1** — `docs/build/BACKLOG.csv` is byte-identical to the chain tip (drift
predates this run; the checker is not a `make check` step, RISK-P20-01). Full failure set + closing
command are in `CAPSTONE_VERIFICATION.md §(f)`; a scoped `P22+` backlog-reconciliation ticket closes it.
Not fabricated green.

## AC → evidence
| AC | Evidence |
|---|---|
| MATRIX-INT-01 closed | `check_coverage_matrix.py` exit 0; §(b) addendum |
| APPENDIX-F-01 closed | `check_spec_src.py` exit 0; spec diff = 1 ADR-072 row |
| Whole build green | make check / test-db / e2e (S8 ran) / run_okc all pass |
| Append-only preserved | signed §(b) table + ADR bodies unchanged; addenda only |
