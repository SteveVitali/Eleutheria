# ADR-198 — ADR-index truth, the status-line declaration grammar, and the trigger-register checker (P34.32)

- Date: 2026-10-05
- Status: accepted
- Ticket: P34.32 (Round 11 / P34, row 237 — owns SIG-ENG-043; satisfies SIG-ENG-039; B4 G8, COV-14)
- Base: `r11/P34.31-living-record-test-lint`
- Related: ADR-073/126/127/148 (build memory v2/v2.1 this checker guards), ADR-146+ (the T1 template
  boundary the index check hard-fails on), BL-002 (the accepted monitor home), BL-084 (this ADR's
  trigger home), `docs/build/tools/adr_index_check.py`, `docs/build/tools/adr_triggers.py`,
  `scripts/docs/adr-index.sh` (the vendored generator the local patch adapts — recorded for the
  upstream skill proposal B6/SK-21, not sent)

## Context

B4 NEW-6 counted the landed forms the vendored generator could not parse (79/142/25 `—` cells at
planning; the title and `Phase:`/`Phase / ticket:` forms were adapted earlier — one `—` cell
remained at P34.32's dispatch: ADR-120's owner). G8 asks the index to tell the truth about every
ADR — number, title, owning ticket or phase, and current status — while landed bodies stay frozen
(SIG-ENG-003; the generator adapts, never the ADRs). COV-14 requires every ADR another ADR
supersedes, amends, qualifies or extends to carry its appended status line — the one legal
post-landing body change (BM-ADR-01, G2). SEED-15 created `ADR_TRIGGERS.csv`; G8-3's full checker —
open homes by state, the round-tail mode, probe hooks — is this row's.

## Decision

1. **The index status is the latest appended status line, not the frozen header.**
   `status_line()` (the P34.32 local patch to `scripts/docs/adr-index.sh`) reads the last
   `- **Status:** <Kind> by ADR-NNN …` line inside `## Status updates` — all five kinds
   (Superseded / Amended / Qualified / Extended / Revisited), section-scoped so trigger evaluations
   and decision prose can never rewrite the cell. Twenty landed rows whose headers still read
   `Accepted` now show their true state (e.g. ADR-002 → Qualified by ADR-189).

2. **The owner-label list stays closed — and ADR-120's `—` is a declared warning, not silent.**
   The owning phase comes from `**Ticket:**`, then `**Phase:**`, then `**Phase / ticket:**`,
   exactly as G8-1 names. ADR-120's header carries only `Date`/`Status`/`Scope`/`Baseline`; its
   body is frozen, `Scope:`/`Baseline:` are not owners, and an override file would hand-patch the
   derived index — so the generator's `—` stands and the checker reports it as the one named
   warning. The checker's hard failures are the cells that *can* be fixed: any `—` on ADR-146+
   (the T1 template boundary) and any cell whose field is present but unparseable (an unexplained
   `—`). The vendored validator's own post-marker viol already mirrors this split, so its warn
   stays as is; the new strictness lives in `adr_index_check.py`.

3. **The checked declaration surface is the one actually in use — fields, annotations, and
   sentence-initial body declarations.** Beyond the four named fields, the combined
   `Amends / qualifies / extends:` and `Relationship|Relation to landed ADRs:` fields are
   verb-scanned, and each `ADR-NNN` token's annotation inside `Related:`/`Relates to:`/
   `Related / amends:` is scanned for a kind word (`— <kind>`, `**<kind>**`, `is <kind>`,
   `the <kind> <noun>`) or a first-person verb (`this … supersedes|amends|qualifies|extends|
   revises|departs`) — a kind word wins when both appear ("this extends — qualified"). The
   convention's own history treats these as line-worthy (ADR-075←081's "departs", ADR-092←099's
   "this ADR supersedes"). Bare `Related:` references, mechanism notes ("this mirrors",
   "the per-claim attribution extends"), `none` values, quoted spans, `no status line for` /
   `assigns … line to` / `leaves … unchanged` cancellations, records-supersession phrases,
   `not <kind>` clauses and self-references oblige nothing; a named target with no file fails
   closed. Eight declared-but-unlined relationships were appended with `date -u` (ADR-030←068,
   ADR-039←054, ADR-055←069, ADR-068←091+097, ADR-087←088, ADR-104←114, ADR-105←116). ADR-120's
   "This decision extends ADR-073…" is deliberately outside the grammar: a prospective,
   scope-bounding clause ("only in the narrowly stated future interfaces") whose operative
   relationships the implementing ADRs landed with their own lines (ADR-153→105, ADR-155→091/097).

4. **The register's home rule is the backlog's own rule, judged from the register side.**
   A `home` must be an *open* BACKLOG row, an *accepted* monitor row (BL-002) unless the trigger
   is `fired-unanswered`, or a *closed* row only while the trigger is `quiet`/`superseded`
   (F3 NEW-3) — and the register's `home` must equal the BL row whose `sources` name the ADR
   (the same edge `check_backlog.py` judges; both sides now verify it).

5. **`--round-tail` binds the closing rows.** Every row's `last_evaluated` must fall inside the
   round, and a `fired-unanswered` row must carry an `S1… disposition:` record in its evidence —
   the stage-1 sweep's routing of the unanswered trigger (P34.33's tail calls and the P38 tail
   rely on it). `probe_id` is honoured when present — validated as a token, never required —
   the G10 hook.

## Alternatives considered

- A committed owner-override file (a `date_corrections.csv`-style source for ADR-120's cell):
  honest but heavier — it invents a second writer for a derived column to serve one row; the
  declared warning is the truer shape.
- `Scope:`/`Baseline:` as owner fallbacks: a scope is not an owner; putting it in the Ticket
  column mislabels the cell.
- Only the spec's four named field labels as the checked surface: it would pass the tree but
  produce exactly the "none superseded" reading the spec warns against — real declared
  amendments (ADR-116→105) would escape.
- Scanning all body prose for relationship verbs: trigger conditions, quoted shorthand and
  conditional futures would fabricate obligations; the grammar stays on declared surfaces.
- `This decision` in the first-person rule: ADR-120's clause is prospective and scope-bounding;
  recording it would also backdate an "Extended" over ADR-097/105's later superseded/amended
  lines and distort the index's last-line-wins status.

## Consequences

- `docs/adr/README.md` is regenerated by the patched generator (20 status corrections + the new
  ADR row); it is never hand-edited.
- Eight `## Status updates` lines were appended across seven landed ADRs with 2026-10-05
  `date -u` stamps and provenance notes — the only legal body change.
- `make docs-check` gains `docs-check-adr` (`adr_index_check.py` + `adr_triggers.py check`);
  both report offered/evaluated counts (SIG-ENG-042) and run in the CI `docs` job.
- P34.33 and the P38 tail call `adr_triggers.py check --round-tail <round-start>`.

## Revisit trigger

- A new declaration surface or status-line form lands (a new `Supersedes:`-family label, a new
  annotation grammar, a new status kind) — the checker's grammar list is explicit, so a new form
  needs a recorded extension.
- The G10 probe grammar lands and pins `probe_id` beyond the token shape.
- A legal mechanism appears for ADR-120's owner cell (e.g. an ADR-146-class correction record
  with an owner field) — the declared warning then resolves.
- A round tail shows the `S1… disposition:` citation grammar too strict or too loose.
