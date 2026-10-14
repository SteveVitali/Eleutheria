# P34.48 — SET.csv derivation

Derived 2026-10-06 (P34.48 context C1; `date -u`) from `docs/build/COVERAGE_MATRIX.csv`
at `8494cd3d` on `r11/PLAN-11B-contracts-for-11b-and-transp-family`.

## Predicate

A row joins the set when it still carries the bare (unparametrised)
`MET-DIFFERENTLY` verdict whose note is one of the two shapes F2b §4 counts among
the 75 bulk-accepted rows:

- **`classifier-boilerplate`** — the `classify.py` prefix default note
  ("charter/process/epistemic/publication-safety principle satisfied by design +
  policy package (P00.2/P00.3) + honest-rendering rules; not cited by id"),
  written without a row-by-row evidence read.
- **`hand-override-note`** — the same bare verdict kept by hand on rows whose
  F2b sample suggested a parameterised verdict that could not be raised
  (no ADR/RISK row naming the id), so the boilerplate verdict stood un-reverified.

…minus the 13 F2b-sampled rows and the purposive SIG-CHART-033 (both already
re-verdicted by SEED-14b), minus any other row SEED-14/SEED-15 re-verdicted
(their notes carry dated `R11 T4` clauses and their `coverage-assessment/1`
events exist).

## Named addition

- **`SIG-UI-040`** — not a boilerplate row. SEED-15 (2026-10-01T16:35:31Z,
  assessment `SIG-UI-040:r11-2`) withdrew its `MET-DIFFERENTLY(ADR-108;ADR-133)`
  to bare `MET-DIFFERENTLY` routed to P34.48 because neither cited ADR names the
  id (ADR-150 D1/D4) and landed ADR bodies are frozen. It is counted **beside**
  the 61, not inside them (`family = named-addition`).

## Counts

| measure | count |
|---|---|
| plan §6.6 expected family | 61 |
| discovered family (53 classifier-boilerplate + 8 hand-override-note) | **61** |
| named addition | 1 (`SIG-UI-040`) |
| `SET.csv` total | **62** |

The 62 vs 61 delta is the named addition, not a missing family row: the F2b §4
population of 75 minus 13 sampled minus SIG-CHART-033 minus the 61 family rows
reconciles exactly — every other bare-verdict row was already re-verdicted by
SEED-14b/SEED-15 with a dated note clause and an assessment event.

## Seam

C1 (this context) re-verdicts rows 1–31 (`SIG-CHART-*` then `SIG-ENG-018`–`032`).
C2 takes rows 32–62 (`SIG-ENG-033+`, `SIG-EPIS-*`, `SIG-GOV-017/018`,
`SIG-IDENT-014`, `SIG-ONTO-006/008/009`, `SIG-PUB-*`, `SIG-RECON-051`,
`SIG-SEC-002`, `SIG-TIME-003`, `SIG-UI-040`) plus the two stray `P34.48`-routed
non-family rows (`SIG-ENG-005`, `SIG-GOV-016` — their routing must move before
the row lands), the `REVERDICTS.md` report, and closeout.
