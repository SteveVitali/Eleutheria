# ADR-041: The records-request generator — the 51-jurisdiction records-law table, residency routing, versioned templates, and consent

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P10.3
- **Requirement ids:** SIG-TASK-015, SIG-TASK-016, SIG-TASK-016a, SIG-TASK-016b, SIG-TASK-017, SIG-TASK-018, SIG-TASK-009 (exercised through the records path)
- **Spec:** docs/2_canonical_design_spec.md §36 (records-request generation); cross-references §33.4/§33.5 (dispositions, geographic queue, P10.1), §32.1/§9.5 (coverage, P09.1)

## Context

P10.3 turns a detected research gap into a **ready-to-file public-records request**.
§36 layers four obligations onto that: emit with the *correct statute for the
jurisdiction* (SIG-TASK-015) from a 51-jurisdiction reference table (SIG-TASK-016);
treat residency as **operationally binding**, not informational — refuse a
non-resident's request in the six restricted states, route it to a local filer, and
record the barrier as a coverage fact (SIG-TASK-016a/016b); version the request
language and **measure its success rate** (SIG-TASK-017); and never file on a
contributor's behalf without **consent** (SIG-TASK-018). Several structural questions
had to be settled against the P10.1 engine and the P09.1 coverage model this ticket
consumes.

1. **Where does the residency barrier land in the four-state §9.5 coverage model?**
   The barrier is not "we searched and found nothing" — SIG *could not search* (a
   non-resident cannot file). Recording it as `searched_not_found` would be exactly
   the §32.2 error the requirement forbids: thin evidence in a restricted state read
   as an *absence of surveillance* rather than a *legal barrier*.
2. **What does "route the task to the geographic queue" mean** given P10.1's
   `GeographicQueue` is a claims-and-ordering coordinator, not a task container?
3. **Where does the reference table and the request language live** — code or data?
4. **How is a template "success rate measured" (SIG-TASK-017)** without a filing
   backend yet?

## Decision

1. **The residency-barrier coverage fact is `not_researched`, attributed in
   `search_method`.** `residency_barrier_coverage` writes an
   `inference.coverage.CoverageRecord` (P09.1, reused — not re-encoded) with
   `absence_kind = "not_researched"`, the jurisdiction and subject set, and
   `search_method = f"residency_barrier:{citation}"`. `not_researched` is the honest
   §9.5 state (SIG has not — and structurally cannot — research it here), and it is
   *distinguishable* from `searched_not_found` at every read path (SIG-TIME-012), so
   thin coverage in a restricted state reads as the legal barrier it is, not an
   absence (SIG-TASK-016a item 3, §32.2). Adding a fifth `absence_kind` was rejected:
   the four-kind vocabulary is a frozen P09.1/DDL contract, and this is additive.

2. **"Route to the geographic queue" = surface the jurisdiction's local filers and
   active claimants.** A residency block returns a `ResidencyBlock` carrying the
   jurisdiction's `local_filers` (from the SIG-owned `LocalGroupRegistry`, which is
   *load-bearing infrastructure* here — in six states SIG's records-acquisition
   capability is exactly its local-contributor coverage) and the `claimant_groups`
   holding an active claim on that jurisdiction (from the P10.1 `GeographicQueue`).
   The generator does **not** mutate task lifecycle state or "insert" a task into the
   queue, because P10.1's queue is a coordination affordance (claims + ordering),
   not a container — every open jurisdiction-scoped task is already workable by a
   jurisdiction's claimants via `order_for_group`. The block is the routing decision;
   applying it through the P10.1 pool/lifecycle is the caller's (and a downstream
   ticket's) job.

3. **The reference table and the templates are DATA, not code (SIG-ENG-001).**
   `data/records_law.toml` (51 rows) and `data/request_templates.toml` load through a
   new cached `tasks._data.load_table`, mirroring `connectors._data`/`policy._data`.
   Amending a statute citation, a residency flag, or a template wording is a reviewed,
   **versioned** data change (`table_version`/`template_set_version`, §20), never a
   silent code edit. The `citation` and `residency_required` fields are load-bearing
   and asserted by the suite; the operational-detail fields (deadline, fee rules,
   appeal path) are honest seed summaries pending per-jurisdiction counsel review
   (RISK-P10-16, SIG-ENG-005) — real, widely-documented, and deliberately coarse
   ("reasonable time") where no single statutory number exists, never fabricated.

4. **Templates are versioned; the success rate is measured by an outcome log.**
   `TemplateLibrary` holds the version history per record type (a wording change is an
   appended version, so a measured rate always names the exact language). Because no
   filing/response backend exists yet, `TemplateOutcomeLog` is the measurement
   surface: callers record each filed request's outcome, and it reports the per-version
   success rate and flags a version for revision once it falls below a data-defined
   floor over a minimum sample (so one early denial does not condemn a template). A
   `no_responsive_records` reply is **not** counted as a template failure — the agency
   answered on the record, which becomes a coverage finding (decision 5).

5. **The no-responsive-records path reuses the P10.1 coverage-writing bridge.**
   `record_no_responsive_records` routes through
   `tasks.dispositions.resolve_no_evidence_exists` (the single bridge that writes a
   `searched_not_found` `CoverageRecord` *before* closing the task), naming the
   emitted request (agency + statute) as the searched source. So the §36 records path
   exercises SIG-TASK-009 exactly as every other search path does — the queue shrinks
   only by producing data.

6. **Consent is a gate on the emit path only (SIG-TASK-018).** `generate` refuses to
   emit unless the `Filer` has `consent_granted` *and* `acknowledged_public_act`, and
   every emitted request carries a `public_act_notice` stating that filing is a public
   act attributable to the filer. The residency-block path does **not** require the
   original (non-resident) filer's consent — SIG is not filing on their behalf, it is
   routing to a local filer who will supply their own consent when they file.

## Consequences

The generator is a set of pure-Python value objects plus two TOML data tables, with a
single owner of the jurisdiction→statute mapping, the residency-routing contract, the
versioned language, and the consent gate. Three §36 MUSTs that are easy to leave as
prose are executable: a non-resident (or unknown-residency) filer in a restricted state
cannot produce an emitted request (residency is checked before emit), an unconsented
filer cannot produce one either, and a residency barrier always writes a
`not_researched` coverage fact rather than a misleading `searched_not_found`. `tasks`
gains a `data/` resource dir and a `_data` loader but no new runtime dependency (the
coverage reuse was already `sig-inference`, added in P10.1). Persisting the emitted
request, transmitting it, and ingesting the reply remain downstream (the `records`
connector, P07.2, owns ingestion); binding the local-filer routing into a live
`TaskPool`/`GeographicQueue` reassignment is downstream too.

## Alternatives considered

- **Record the residency barrier as `searched_not_found`** (rejected: it is the exact
  §32.2 error — a legal barrier misread as an absence of surveillance; and it would be
  refused anyway for lacking `sources_searched`, since nothing was searched).
- **Add a fifth `absence_kind = "legal_barrier"`** (rejected: the four-kind vocabulary
  is a frozen P09.1/DDL contract; `not_researched` + a `search_method` attribution is
  additive and distinguishable, which is all §32.2 requires).
- **Have the generator mutate the task and insert it into the queue** (rejected:
  P10.1's `GeographicQueue` is claims + ordering, not a task store; a blocked task is
  already workable by claimants once jurisdiction-scoped, so the routing artifact is
  the *decision* — local filers + claimants — not a queue mutation).
- **Hard-code the 51-jurisdiction table and the templates in Python** (rejected:
  SIG-ENG-001 — the statute table and proven language are reviewed, versioned data, so
  a counsel correction is a tracked migration, not a code change).
- **Compute a template success rate from a static field in the TOML** (rejected:
  SIG-TASK-017 says the rate is *measured*; a hand-written number is a claim, not a
  measurement — the outcome log measures it from real filed outcomes).
- **Depend on `connectors.records.RecordsRequest`** (rejected: that is the ingest-side
  shape of a *filed* request; a *generated* request is a distinct value object, and
  wiring `tasks → connectors` would add a heavy dependency edge for no reuse).

## Revisit trigger

Revisit when a filing/response backend lands (the `TemplateOutcomeLog` is fed by real
outcomes and the local-filer routing is applied through a live `TaskPool` reassignment
and geographic-queue claim), when the per-jurisdiction operational fields
(deadline/fee/appeal) complete their counsel review (RISK-P10-16) and the seed values
are replaced with reviewed ones, when a jurisdiction's records law materially changes
(a versioned `records_law.toml` migration), or if a `legal_barrier` coverage kind is
ever added to the §9.5/§32.1 model (then the residency fact is realigned to it).
