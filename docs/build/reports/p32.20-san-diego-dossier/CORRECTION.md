# CORRECTION — P32.20 San Diego dossier packet (a fixture run)

Written 2026-10-01T08:21:03Z (`date -u`) by Claude Code, harness `claude-code/claude-opus-5-5/subagent`, Round-11 Stage-B unit SEED-08 (ADR-146 Decisions 2 and 4; B1 §5.5). **Every other file in this directory is kept byte-for-byte**: they are historical run evidence whose digests later records cite. Nothing here re-runs or regenerates them; the code fix and superseding artifacts belong to P34.22a/b. This file is append-only.

## What was fixture

- The whole packet. P32.20 ran offline (`live_verification=false`, as `EVIDENCE_PACK.md` line 4 says) and read only hand-authored stand-in documents committed under `tests/connectors/fixtures/dossier/` (authored 2026-09-27T12:06:40Z in `f73a997e`; that directory's `SOURCES.md` says none of its files is a fetched capture). No document was fetched; the "how obtained" column of `EVIDENCE_PACK.md` names a fixture for every document.
- The run: PR #177 (`createdAt` 2026-09-27T18:27Z), implementation `8e7bdfbe` (2026-09-27T18:26:56Z), closeout `5efe4b9d`; executed in the Devin CLI session `carefree-caption`, model `swe-2-high` (B7 §3 S9).
- The packet's own review mark is `review.status = not_run` (no independent reviewer — `D-R10-HUMAN-1` OPEN), and its live-source return pass is prepared, not executed (`LIVE_RETURN_PASS.json`; `D-P32.20-1` OPEN).

## What was claimed on it

- **Dates.** The packet's as-of pair and every retrieved / observed / searched / generated date inside these files are scenario or replay labels, not dates on which anything happened (B1 §3 #37) — table below. The dates the documents themselves state (`valid_from`, effective dates, signed dates) are real-world dates and are not corrected.
- **Verdicts.** `docs/build/COVERAGE_MATRIX.csv` records `SIG-DOS-005` MET by P32.20, and the dossier-family verdicts rest on this bounded, fixture scope (F-16). The Round-11 re-verdicts under ADR-150 (B-5) replace those headlines; ACCEPT-R10's "34 MET" that included them is superseded (C-13, 2026-10-01T05:03:05Z).
- **Publication scope.** GATE-G3 approved publishing the dossiers as `mechanical_complete` (San Diego 29/36) with `review.status=not_run` and no pilot-completion claim; that approval is superseded with candidate `p-17b713…` (B-4, 2026-10-01T04:32:16Z; `docs/build/reports/p32.23a-release-candidate/CORRECTION.md`). No dossier page from this directory is deployed (F-14).

## Date corrections (register `docs/build/reports/memory-repair/date_corrections.csv`)

| file · field / line | recorded → true (UTC) | evidence | register recs |
|---|---|---|---|
| `EVIDENCE_PACK.md` L4; `EVIDENCE_PACK.md` L48; `FOLLOW_UP_DRAFTS.json` L37 generated_at; `PART_VIII_PREFLIGHT.json` L5 generated_at; `san_diego_dossier.json` belief/observed_at/retrieved_date/searched_at/text/world x133; `san_diego_dossier.print.html` L1; `san_diego_dossier_packet.json` belief/generated_at/observed_at/retrieved_date/searched_at/text/world x96; `san_diego_dossier_portfolio.json` belief/observed_at/retrieved_date/searched_at/text/world x133 | stand-in label: recorded 2026-10-01 → true no such event — a stand-in replay or scenario label (fixtures authored 2026-09-27T12:06Z, `f73a997e`; B1 §3 #37) | packet generated 2026-09-27T18:26:56Z (8e7bdfbe) from hand-authored stand-in fixtures | 323, 324, 325, 326, 327, 328, 329, 330 |
