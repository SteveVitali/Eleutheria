# ADR-063: Registry review metadata and the flip rule

- **Status:** Accepted
- **Date:** 2026-09-09
- **Phase:** P21.1
- **Requirement ids:** SIG-INGEST-023, SIG-INGEST-027, SIG-INGEST-028, SIG-INGEST-038, SIG-LIC-001, SIG-LIC-004, SIG-LIC-009, SIG-LIC-009a, SIG-CONTRIB-012, SIG-CONTRIB-012a, SIG-CONTRIB-013, SIG-INGEST-030

## Context

At the end of the 46-ticket build the source registry held 109 rows with **0
loadable**: 87 `UNDETERMINED`, and `ingestion_permitted` absent (false) on every
row. Turning "0 of N loadable" into a reviewable, one-line-per-source decision needs
three things prose alone could not give (SIG-ENG-001): (1) the OKC critical-path
sources actually registered; (2) a machine-checked rule that a flip to
`ingestion_permitted = true` carries the metadata that makes it auditable; and (3) a
per-source packet + status surface a human can act on **without touching code**
(SIG-LIC-001, RISK-P0-15/16/19).

The loader gate (`connectors.loader.assert_loadable`, ADR earlier) already checks the
flag + `compact_status` + `custody_posture` at runtime. What it did *not* model is the
**provenance of the flip itself**: who reviewed the rights, when, and against which
packet. A flag flipped without a recorded review is indistinguishable, to the gate,
from one flipped after counsel review — exactly the ambiguity SIG-INGEST-028/038 and
SIG-LIC-001 exist to remove.

Two human gates block real ingestion and are **prepared but never performed** by this
ADR's ticket: **HG-03** (a rights reviewer flips specific sources) and **HG-04**
(Stage-0 outreach outcomes). This run ships with both **skipped** — packets, tooling,
and record templates only; nothing is flipped, so `loadable now: 0`.

## Decision

1. **Additive review-metadata fields on the registry row** (`sources.toml` +
   `connectors.registry.SourceRecord`), all optional so the change is back-compatible
   and an unreviewed row carries none: `rights_reviewed_by` (a reviewer **role**
   string — never a personal name, Part VIII §0.7), `rights_reviewed_on` (date), and
   `review_packet` (path to the row's `docs/build/rights/<id>.md`).

2. **The flip rule** (`connectors.review.review_metadata_violations`, wired into
   `sig-connectors validate`): a row with `ingestion_permitted = true` is **invalid**
   unless it carries a resolved rights block (not `UNDETERMINED`) **and**
   `rights_reviewed_by` **and** `rights_reviewed_on` **and** `last_verified`.
   `validate` fails, naming the offending id, otherwise. `ingestion_permitted` still
   defaults false (SIG-INGEST-028); the rule adds an obligation to flips, it does not
   loosen the default.

3. **`sig-connectors review-status [--source ID]`** — per-source gate breakdown across
   five fields (`ingestion_permitted / compact / custody / rights / reviewed-by`) and,
   with no arg, the `validate` counts plus **flip-ready** (rights block + compact ok +
   custody ok, flag false) and **loadable now** (= `validate`).

4. **The rights-review packet format** (`docs/build/rights/_TEMPLATE.md` + 27 packets):
   facts (verbatim quoted terms + retrieval date) are laid out **separately** from
   judgement (the reviewer decision line); no packet asserts a legal conclusion
   (defining standard §3.1). Reading a terms/robots page is permitted research, not
   ingestion; source *content* is never fetched here.

5. **The Stage-0 outreach record format** (`docs/build/STAGE0_OUTREACH_RECORD.md`, one
   row per the 19 federation-compact projects of spec §6/§35.1, + the outreach letter
   template `docs/governance/stage0-outreach-letter.md`) flows outcomes into the closed
   `compact_status` vocabulary (SIG-INGEST-027). It is **append-only** (P1–P3): a real
   outreach event adds a new dated row; earlier rows are never rewritten.

6. **`usaspending` left `UNDETERMINED`.** The DATA-Act public-domain facts (17 U.S.C.
   §105) are laid out in its packet with the SPDX candidate `CC0-1.0` (the accepted
   public-domain expression in `policy/data/licenses.toml`), but the registry row keeps
   no rights block: adding one is the reviewer's flip decision, and doing so here would
   itself make the source flip-ready (a rights judgement this ticket must not make).

## Consequences

- A flip is now an auditable, tested data change: `validate` refuses a flip that lacks
  its review metadata, naming the id. `sig-connectors validate` reports
  `registered sources: 115` (109 + the 6 OKC rows); `loadable now: 0` and `flip-ready:
  18` until a reviewer acts (HG-03/HG-04).
- A human can unblock ingestion entirely through data + records (flip the flag, set the
  three metadata fields, record the outreach outcome) — no code change (SIG-LIC-001).
- P21.3 refuses to fetch any source whose `review-status` is not fully green; this ADR
  owns the rule it enforces.
- New registry keys are optional and `ingestion_permitted` still defaults false, so the
  change is additive/back-compat; the `tests/acceptance/fixtures/okc_sources.json`
  fixture is unchanged (a mapping test relates its `source_id`s to the new rows).

## Revisit trigger

Revisit when the operator answers HG-03 (which sources to flip) or HG-04 (outreach
outcomes): the flips + review metadata land on `sources.toml` (with `last_verified`),
`STAGE0_OUTREACH_RECORD.md` gains dated rows, and `validate` then shows
`loadable now ≥ 1`. Also revisit if the packet set widens beyond the 27 critical-path
sources (P22+ backlog).
