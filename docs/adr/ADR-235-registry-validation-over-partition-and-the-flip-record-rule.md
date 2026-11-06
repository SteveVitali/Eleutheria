# ADR-235 — Registry validation over partition, and the flip-record consistency rule (P37.6)

- Date: 2026-11-06
- Status: accepted
- Ticket: P37.6 (Round 11 / P37, row 426 — R11-GOV-05; answers the ADR-021 and
  ADR-063 revisit triggers recorded `fired-answered(P37.6)` in the SEED-11d
  evaluation; serves SIG-INGEST-023/024/028/038, SIG-LIC-001/009)
- Base: `r11/P37.5b-manual-acquisition-and-disappearance-events`
- Related: ADR-021 (source registry as seeded data — the trigger this row
  answers; its decision stays in force, qualified not rewritten), ADR-063
  (registry review metadata + the flip rule — the index it names is
  regenerated), ADR-194 (the source-scoped rights-record key the consistency
  rule audits), ADR-146 (additive date corrections — untouched), ADR-222 /
  GL-GATE-08 / ADR-088 (declared-robots posture — the stale-comment basis)

## Context

The ADR-021 trigger evaluation (SEED-11d, 2026-10-01) marked the registry's
revisit trigger LIKELY FIRED: the single flat `sources.toml` had grown to 342
rows with rights-field drift (E4 NEW-10, B1 NEW-5); it now holds 590 sources
and ~15k lines. Its recorded answer was this row, with the caveat that a
partition would need a new ADR. The audit this row ran found the drift
concretely:

- **15 flipped rows** carried no `review_packet` field although their packets
  exist on disk — the recorded review's audit trail was unlinked.
- **18 flipped rows** carried the loader's `2026-08-20` `retrieval_date`
  placeholder written literally — no terms-retrieval date was recorded
  (eleven of the packets record a verbatim 2026-09-09 fetch; eight record
  "not fetched verbatim this pass", matching the `retrieval_date` =
  `rights_reviewed_on` convention the P29.3 annexes already use).
- **6 flipped rows** wrote the flip marker as
  `FLIPPED to ingestion_permitted=true <date>` — the Record-rule form
  `FLIPPED <date> (<gate|ADR>)` was not machine-findable.
- **26 flipped packets** still carried the unchecked template Decision line —
  the recorded answers (reviewer role, dates, gate citations) were never
  written back from the registry rows.
- **`RIGHTS_REVIEW_INDEX.md`** was a stale snapshot (588-row counts against
  590 registered, a "loadable now: 0 / gate skipped" paragraph that no longer
  held, a retired `.agents/scratch/` regenerate pointer, and a packet column
  that ignored the recorded `review_packet` field and the `annex/` batches).
- **Stale bonfire/procurement comments** still named the robots wall as the
  D-SOURCES.9-2 blocker although GL-GATE-08/ADR-088/ADR-222 made a declared
  `Disallow` a recorded posture, never a gate (E4 NEW-3/§5).

## Decision

1. **Validate, not partition.** The registry stays one flat
   `connectors/data/sources.toml` (ADR-021 stands): the drift found is
   field-level and mechanical, not structural — a partition would split the
   ingestion gate from the loader that enforces it and buys nothing a
   validator cannot enforce today. A new `## Revisit trigger` below names
   the conditions under which this answer is re-opened.
2. **The flip-record consistency rule is enforced in `sig-connectors
   validate`** via `connectors.review.rights_record_consistency_violations` —
   the *record* half of the flip rule that `review_metadata_violations`
   covers on the metadata side. A flipped row MUST: name a `review_packet`
   path that resolves to a committed file (per-source packet or batch annex);
   carry the `FLIPPED <YYYY-MM-DD>` marker **and** the `rights_reviewed_on`
   date inside `notes` (review and flip are distinct recorded events — the
   reviewed-then-flipped rows carry both dates); and carry a complete ADR-194
   resolver tuple (`rights.attribution`, `rights.terms_url`, and an explicit
   `rights.retrieval_date` — the loader's `2026-08-20` fallback is the
   marker that none was recorded and is a violation on a flipped row).
3. **The repaired record form.** Drift repairs wrote the recorded values
   only: `review_packet` fields point at the committed per-source packets;
   `retrieval_date` takes the packet-verbatim fetch date where the packet
   records one and the review date where it records "not fetched verbatim";
   the six notes were normalised to `FLIPPED 2026-09-10 (GL-GATE-03,
   RIGHTS.1 re-run)` with the recorded date byte-identical (ADR-146's
   corrections still carry the true dates).
4. **The index is generated, never hand-edited** —
   `docs/build/tools/gen_rights_index.py` regenerates
   `docs/build/reports/RIGHTS_REVIEW_INDEX.md` from the live registry; the
   packet column follows the recorded `review_packet` field so batch-annex
   rows link correctly.

## Consequences

`sig-connectors validate` now fails closed on a flip whose record cannot be
audited — the gate's "a flip without its review metadata is a data error"
posture extends to the packet, the markers, and the resolver tuple. Every
flipped source's packet records its decision; `0` flipped packets carry a
blank Decision line (gated sources keep the template box unchecked — the
honest undecided posture; the P26.16 `annex/` stubs record the same fields
compactly in their header bullets, and the P29.3 `annex/p293` packets carry
prose decisions). A future rights-field repair runs the same audit
(`rights_record_consistency_violations`) rather than a bespoke sweep.

## Alternatives considered

Partitioning the registry per layer/connector (rejected for now — splits the
gate data from the loader, multiplies the validation surface, and solves no
failure the audit actually found; named in the revisit trigger); a one-off
repair script with no enforced rule (rejected — the drift would regrow;
SIG-ENG-001 wants the invariant executable); folding the new checks into
`review_metadata_violations` (rejected — a separate function keeps the
P21.1 rule's contract and messages stable for its existing callers/tests).

## Revisit trigger

Partition is re-opened when: the single file's row count or review latency
makes a per-change review impractical at the rate flips land; a second
writer class (generated target rows, ecosystem registries) needs per-file
review scopes the flat file cannot express; or the §47 layout gains the
dedicated registry package ADR-021 already names. The consistency rule's
field set is re-opened when a flip legitimately cannot carry one of its
fields (e.g. a licence with no stable terms URL) — the honest posture is a
recorded exception, never a dropped check.
