## Summary

P21.1 turns "0 of N loadable" into a reviewable, one-line-per-source decision. It registers the six
Oklahoma City critical-path sources (115 total), adds a machine-checked **flip rule** that a source may
only be flipped to `ingestion_permitted=true` with its review metadata, and ships the human-facing
surface (27 rights-review packets, a rights index, a 19-project Stage-0 outreach record + letter
template) so a reviewer can unblock ingestion **without touching code**.

**Gate HG-03 / HG-04 = SKIP** (operator answer, recorded in the ticket's Gate-status block): **nothing
is flipped** and **no outreach is fabricated**. `sig-connectors validate` shows `loadable now: 0`;
`review-status` shows `flip-ready: 18`. The ticket is **complete-with-gate-skipped** → listed for a
RETURN PASS re-run once the operator picks flips.

Implements `docs/tickets/P21.1__rights-review-and-registry-completion.md`.

## What changed

- **Registry (`connectors/`)** — 6 OKC rows in `sources.toml` (`okc_procurement`, `okc_council`
  [CivicClerk tenant `oklahomacityok`], `okcpd_policy`, `ok_statute`, `journalrecord`, `oklahoman`),
  all UNDETERMINED + gated. Additive optional `SourceRecord` fields `rights_reviewed_by` (reviewer
  **role**, never a name), `rights_reviewed_on`, `review_packet`. New `connectors/review.py`: the flip
  rule + flip-ready + per-source gate breakdown. `cli.py`: `validate` now enforces the flip rule;
  new `review-status [--source ID]` subcommand.
- **Packets** — `docs/build/rights/` 27 packets + `_TEMPLATE.md`; each has `Terms (verbatim)`,
  `SPDX candidate`, `Decision`. Facts (quoted terms + retrieval date, fetched by reading terms pages —
  permitted research) are separated from judgement (the reviewer decision line). `usaspending` left
  UNDETERMINED (public-domain facts laid out; a rights block would itself be a flip decision).
- **Indexes/records** — `docs/build/RIGHTS_REVIEW_INDEX.md` (115 rows, counts reproduced from
  `validate`); `docs/build/STAGE0_OUTREACH_RECORD.md` (the 19 federation-compact projects of spec
  §6/§35.1); `docs/governance/stage0-outreach-letter.md`.
- **Docs/gates** — ADR-063 (+ Appendix F row via `BUILD.sh`, `docs/adr/README.md`); risk register
  `## Phase 21` (RISK-P21-01/02); `docs/traceability.md`; `BACKLOG.csv` BL-032/BL-033 → `status=closed`.
- **Tests** — `tests/connectors/test_review_status.py`, `test_okc_slice_mapping.py`,
  `test_stage0_outreach.py`.

## Design decisions

- **Flip rule lives in data + a tested function**, not prose: `validate` fails naming the offending id.
  `ingestion_permitted` still defaults false — the rule adds an obligation to flips, it does not loosen
  the default (additive/back-compat).
- **The acceptance fixture `tests/acceptance/fixtures/okc_sources.json` is UNCHANGED** — a new mapping
  test relates its `source_id`s to the registry rows (`src:okc-procurement` → `okc_procurement`, …;
  `src:deflock` → existing `deflock_repo`).
- **Nothing flipped, nothing fabricated** (defining standard §3.1, Part VIII §0.7, append-only P1–P3):
  contact channels are organisational addresses only; FlockReporter's `no_response` is a pre-existing
  recorded state (SIG-INGEST-039b), not new outreach.
- **27-packet reconciliation:** the ticket's `6 + {deflock_repo, osm_overpass, usaspending} + 18` list
  double-counts `deflock_repo`/`osm_overpass` (both in the 18 flip-ready). To satisfy the literal
  `wc -l = 27` while staying on the OKC/DeFlock critical path, the two make-up packets are `deflock`
  (the DeFlock upstream; `src:deflock` in the OKC fixture) and `civicclerk` (the portal `okc_council`
  flows through). Recorded here and in the ledger.

## Verification

- `make check` → **2449 passed, 1 xfailed** (`LD-V08` S8), verify-gen clean.
- `uv run sig-connectors validate` → `registered sources: 115` … `loadable now: 0`, self-checks OK.
- `uv run sig-connectors review-status` → `flip-ready: 18`, `loadable now: 0`.
- `ls docs/build/rights/*.md | grep -v _TEMPLATE | wc -l` → `27` (each has the three sections).
- `python docs/build/tools/check_spec_src.py` → 63 ADRs, 671 ids; `check_backlog.py` → 63/63, exit 0.

## Acceptance criteria → evidence

| AC | Status | Evidence |
|---|---|---|
| `validate` → `registered sources: 115`, self-checks OK; a permitted row lacking `rights_reviewed_by` makes validation fail naming the id | met | `validate` output; `test_review_status.py::test_validate_fails_naming_the_offending_id` |
| 27 packets, each with `Terms (verbatim)` / `SPDX candidate` / `Decision` | met | `ls … wc -l`=27; section grep clean |
| `review-status` prints `flip-ready: 18` and `loadable now: N` = `validate` | met | `review-status` output (18 / 0); `test_review_status.py` |
| `STAGE0_OUTREACH_RECORD.md` 19 rows + consistency test passes | met | `test_stage0_outreach.py` (8 tests) |
| conditional "if operator flipped ≥1" | N/A (gate skipped) | nothing flipped; `loadable now: 0` |
| packets factual, quote actual terms | met | OSM copyright, usaspending, DeFlock MIT fetched verbatim (retrieval 2026-09-09); others honestly noted |
| Phase-gate: `make check` green; ADR-063; traceability + risk register; BACKLOG closed | met | `make check`; ADR-063; RISK-P21-01/02; BL-032/033 closed |

Requirement ids: SIG-INGEST-023/027/028/038/030, SIG-LIC-001/004/009/009a, SIG-CONTRIB-012/012a/013.
