# ADR-233 — Connector-level ingestion-mode declarations and the adjudicated unwired-function scan (P37.5a)

- Date: 2026-11-06
- Status: accepted
- Ticket: P37.5a (Round 11 / P37, row 424 — R11-DEBT-03; serves SIG-INGEST-005
  and SIG-INGEST-006; F2a-verdicts.md §6.5's mechanical-scan recommendation,
  F5-eng-debt.md PKG-12)
- Base: `r11/P37.4b-security-baseline-restricted-access-audit-logs`
- Related: SIG-INGEST-006 (the MUST this discharges), SIG-INGEST-021 (the
  name-registry plug-in seam the scan adjudicates as wired), P37.5b (the
  split-b half: manual-acquisition runbook + disappearance events, named as
  the owner of the change-detection findings)

## Context

P37.5a carries three of the F2a group-10 scope lines — the replay
`valid_*`/`as_of` test (SIG-INGEST-005), declared `ingestion_mode` +
incrementality (SIG-INGEST-006), and the scan for public functions with only
test callers — ahead of P37.5b's persistence half. Two decisions needed
recording rather than leaving as code-shape accidents:

1. *Where the SIG-INGEST-006 declaration lives.* The spec says "every
   connector MUST declare its ingestion mode and its incrementality
   strategy". The mode could have been a `sources.toml` field or a connector
   class attribute. A source row and its connector do not pair 1:1 — one
   connector serves many registry rows, and mode describes *how the adapter
   acquires*, so a row-level field would repeat one fact across ~1,600 rows
   and could disagree with the adapter.
2. *What "only test callers" means mechanically.* F2a §6.5 recommends a
   mechanical scan but does not define its precision. Two conventions decide
   the finding set: whether a reference inside the defining file counts
   (module-internal helpers called by the file's own connector class are
   wired through the connector — counting them floods the report with
   trivia), and what a finding *means* (a name indirection like the
   `get_connector` name registry is production reachability the AST cannot
   see, so a finding is an adjudication row, never a proof of deadness).

## Decision

1. **The declaration is a connector class attribute.** `Connector` gains
   `ingestion_mode` (a member of the closed §21.3 vocabulary
   `connectors.ingestion_mode.INGESTION_MODES` — nine modes, verbatim from
   the spec table) and `incrementality` (a non-empty strategy label). All
   twenty-six registered connectors declare both. `sig-connectors validate`
   fails closed on an absent or out-of-vocabulary declaration via
   `ingestion_declaration_violations()` — the check is lazy so importing the
   module never forces connector registration. `""` is undeclared and a
   violation, never a vocabulary member: a connector that cannot honestly
   say how it acquires is a defect, not a metadata gap.
2. **The scan counts same-file references as wiring and adjudicates the
   rest.** `connectors.unwired_scan` reports a *finding* for each public
   module-level def/class in `connectors` + `parsing` whose only referers
   live under `tests/`. References are import-resolved (`from mod import f`,
   `import mod` + `mod.f`, `from pkg import submod`, `__init__.py`
   re-exports, relative imports) — never bare-name guesses outside the
   defining file. A reference in the **defining file counts as wiring**: a
   helper the module's own connector calls is reachable through the
   connector, so the scan reports the *top* of each unwired cluster rather
   than every helper under it. The scan is deliberately conservative —
   dynamic lookup (`getattr`, the name registry, CLI dispatch) can mask real
   usage — so every committed finding carries a recorded disposition in
   `connectors/data/unwired_scan_baseline.toml`:
   `seam:name-registry` (registered connector classes, wired by name
   through `get_connector`), `test-surface` (committed-data accessors the
   suite reads directly), `api-reserved` (framework API reserved for the
   orchestration/CLI seam, SIG-INGEST-001/021, SIG-ENG-013) or
   `capability-half` (a built capability whose consumer row is named —
   `flock_portal` change detection → P37.5b; OSM replication-diff halves,
   the minting-parity codec, the publish-matrix batch render, the §24/§25
   dispatcher/canary/eval halves → unscheduled, recorded).
3. **The baseline is a two-way ratchet.** `baseline_drift` reports `new`
   (an unwired public function appeared — wire it or adjudicate it in the
   same change) and `resolved` (a baseline finding wired or deleted —
   regenerate the baseline in the same change). The ratchet test and
   `sig-connectors unwired-scan --drift` (exit 3) fail loud on either; the
   report (`docs/build/reports/p37.5a-unwired-scan/report.json`,
   `sig.unwired-scan/1`) is the committed audit record.

## Consequences

- SIG-INGEST-006 is discharged: every registered connector declares mode +
  incrementality, validated by `sig-connectors validate` and the declaration
  test. A new connector that cannot name its mode fails both.
- SIG-INGEST-005's framework half is pinned: replay preserves `observed_at`
  and `valid_*` verbatim while minting fresh belief columns, an improved
  parser's re-extraction lands new append-only rows, and belief-pinning
  returns the prior interpretation (the spine-side `claim_as_of` half stays
  with `tests/db/test_as_of.py`).
- The audit found **no dead-path removal** inside the ingestion stack: the
  99 findings adjudicate to four dispositions — 26 name-registry connector
  classes, test-surface accessors, api-reserved framework predicates, and
  capability halves with named owners — and the capability-half findings are
  the same "built but unwired" class F5 PKG-12 names, each recorded with an
  owner rather than deleted (several have unscheduled consumers; P37.5b owns
  the portal change-detection set). A finding that is genuinely dead code in
  a later adjudication is removed with its baseline row in the same change —
  never silently.
- Out-of-stack F2a suspects (`reconcile.lifecycle`, `evidence.redaction`,
  `policy.crawler`, the access-log `expired()` purge) keep their own owners —
  the scan scope is the ingestion stack, and re-scoping them silently would
  double-own the debt.

## Revisit trigger

A new unwired public function lands outside the four disposition classes
(the disposition vocabulary gains a fifth, recorded class); a
`capability-half` finding's named consumer lands and the finding resolves
(the baseline regenerates and this ADR's owner list is re-read); the scan's
conservative rules prove to hide a real dead path (tighten the reference
resolution — e.g. `getattr`/registry-string awareness); or a package is
added to or split from the ingestion stack (extend `SCAN_PACKAGES`).
