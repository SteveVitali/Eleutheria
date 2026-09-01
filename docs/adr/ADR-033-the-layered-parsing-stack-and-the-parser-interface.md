# ADR-033: The layered document-parsing stack as the parser interface every connector extracts through, in `parsing`

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P07.1
- **Requirement ids:** SIG-PARSE-001, SIG-PARSE-002, SIG-PARSE-003, SIG-PARSE-004, SIG-PARSE-005, SIG-PARSE-006, SIG-PARSE-007, SIG-PARSE-008, SIG-STORE-038
- **Spec:** docs/2_canonical_design_spec.md §24 (document parsing and extraction: §24.1 layered strategy, §24.2 reason-code normalization, §24.3 parser drift); §25 (the LLM boundary layer 6 wires in, ADR-030); §21.1 (the eight-stage connector `parse→extract→normalize` seam, ADR-026); §16.2 / §D.4 (the claim spine's `raw_value`, `normalization_id`/`normalization_version`, and `claim_evidence.locator` columns this produces)

## Context

P07.1 owns the **parser interface every records/procurement/document connector calls**
(P07.2, P07.3, and every later document source extract *through* it). §24 is not a single
parser; it is a *stack* of contracts that must hold identically across every source, so a
connector cannot forget one per-source:

1. parsing proceeds by the **cheapest sufficient** of seven layers, with the method recorded
   (§24.1, SIG-PARSE-001);
2. **classification runs before parsing** and its verdict is recorded — and real records
   responses are **mixed-format ZIPs** that must be classified *per member* (SIG-PARSE-002);
3. every claim carries a **locator**, and a locator-less extraction is **rejected**
   (SIG-PARSE-003);
4. **`raw_value` is preserved** before any typing, *including for values SIG cannot parse*
   (SIG-PARSE-004, P2);
5. reason fields are normalized through a **versioned, inspectable, reversible** mapping
   stored as data, with the version stamped on the claim and free-text vs constrained-dropdown
   reasons distinguished (SIG-PARSE-005/006);
6. parser drift is defended by **committed fixtures** and a **nightly canary** (SIG-PARSE-007/008,
   R11).

Three questions had to be settled. **Where does this live?** **What does it build on that
already exists?** **How much of a real parser stack is in scope for the *interface* ticket,
given the frozen §47 layout and the no-new-heavy-dependencies posture?**

The claim spine already provides the storage side: `claim.raw_value text NOT NULL`,
`claim.normalization_id` / `normalization_version`, `claim_evidence.locator jsonb`, and
`extraction.method` (P02.1/P02.2, `db/deploy/claim.sql`, `db/deploy/evidence.sql`). So this
ticket is the **Python parser interface that produces those shapes**, not a schema change.

## Decision

1. **The stack lives in `parsing`** as focused, dependency-light modules beside the existing
   §25 model boundary (`parsing.extraction`, ADR-030), which is layer 6 of this stack:
   - `parsing.layers` — `ExtractionLayer` (an `IntEnum` whose value *is* the cost rank) and
     `cheapest_sufficient`; each layer's `.method` is the string recorded in
     `extraction.method`, and `LLM_ASSISTED.method == "llm_assisted"` matches the DB `CHECK`
     that ties layer 6 to the §25 model-provenance columns (SIG-PARSE-001).
   - `parsing.classification` — `classify(name, data)` and `classify_archive(name, data)`,
     which detect the four archetypes (scanned fax, `/Encrypt` PDF, `<mergeCells>` XLSX,
     multi-sheet XLSX) and classify a ZIP **per member**, recording the verdict and the
     cheapest sufficient layer (SIG-PARSE-002).
   - `parsing.locator` — `Locator` with six validated kinds (page/bbox/cell/row/byte-range/
     DOM path) and the `LocatorRequired`/`InvalidLocator` rejections (SIG-PARSE-003).
   - `parsing.claim` — `ParsedValue` (raw literal mandatory; `unparseable()` keeps it with
     `parsed=None`) and `ParsedClaim` (rejects a claim with no locator; records the layer
     method; carries the normalized reason) (SIG-PARSE-003/004).
   - `parsing.reason_codes` — a versioned, reversible mapping in
     `data/reason_codes.toml`; `normalize_reason` retains the raw text, stamps the mapping
     version, and distinguishes free-text (moderate signal) from constrained-dropdown
     (strong signal) (SIG-PARSE-005/006).
   - `parsing.drift` — `assert_no_drift` over committed `FixtureCase`s (SIG-PARSE-007) and a
     `StructuralExpectation`/`run_canary` core that **alerts** (returns findings) on
     structural drift rather than dropping (SIG-PARSE-008), mirroring the precedent already
     set by `connectors.osm.canary_findings`.

2. **Classification is a deterministic function of the bytes, with no third-party parser.**
   Format sniffing uses magic bytes and the stdlib `zipfile` manifest; the archetype flags
   use reliable byte-level signals (`/Encrypt`, `<mergeCells>`, `xl/worksheets/sheetN.xml`
   counts, image magic, an image-XObject-without-`/Font` heuristic for scanned PDFs). This
   keeps classification cheap enough to run on every ingest and testable against a committed
   real archive, and it defers the *heavy* extraction engines (a PDF text/table library, an
   OCR engine) to the layer implementations the connectors add — exactly as `parsing.extraction`
   injects a `ModelClient` rather than shipping a vendor SDK.

3. **The reason-code mapping is versioned data, changed by migration, never by rewrite.**
   `reason_codes.toml` carries a `version`; every `NormalizedReason` is stamped with it; a
   bulk re-classification under a newer mapping is performed as **new claims**
   (`extraction_method = 'vocabulary_migration'`, the `VOCABULARY_MIGRATION_METHOD` constant),
   never an edit of the claims stamped with the old version (SIG-STORE-038).

## Consequences

Every connector now extracts through one stack: it classifies first (per member for an
archive), picks the cheapest sufficient layer and records the method, emits claims that
*cannot* be built without a locator, always preserves the raw literal (even for values it
cannot type), and normalizes reasons through inspectable versioned data. The locator schema
and `raw_value` contract are a **stable interface** P07.2/P07.3 depend on. Costs and
deferrals, stated rather than hidden:

- **No heavy extraction engines are wired here.** The layer *selection* and the interface are
  complete and tested; the concrete layer-3/4/5 parsers (PDF text/table, OCR) are added by
  the connectors that need them, behind this interface. Classification's scanned-PDF signal
  is a deterministic heuristic, not a rendering-based decision — a mis-route is corrected
  downstream, never a silent drop.
- **The canary is the deterministic core, not the schedule.** `structural_findings`/`run_canary`
  are pure functions of a parsed sample; the nightly job that fetches a live sample and
  raises the alert is an ops schedule (like the P05.2 gold-set cadence), not code shipped
  here.
- **No DDL.** The stack produces the shapes the claim spine already stores; no migration is
  added. The reason fields it emits (`reason_code`, `reason_raw_value`, `reason_kind`,
  `reason_signal_strength`, `reason_mapping_version`) map onto the existing `raw_value` /
  `normalization_id` / `normalization_version` columns plus the `UsageAggregate.reason_*`
  model fields; a first-class physical home for the reason-kind/signal columns, if wanted, is
  an additive P08 migration.

## Alternatives considered

- **A new `parsing`-adjacent package (e.g. `extract`).** Rejected: the §47 layout is frozen
  (SIG-ENG-012) and `parsing` is §24–§25's designated home; the stack sits naturally beside
  the layer-6 boundary already there.
- **Depending on `pypdf`/`openpyxl` for classification now.** Rejected: classification only
  needs to *route*, and byte/zip-manifest signals do that deterministically with no new
  runtime dependency (`pylock.toml` unchanged); the heavy libraries belong to the layer
  implementations, injected like the `ModelClient`.
- **A single locator blob instead of typed kinds.** Rejected: six validated kinds make an
  ill-formed locator a construction-time error and keep the evidence viewer's resolver total.
- **Reason codes as a Python mapping.** Rejected for the same reason as every other SIG
  vocabulary (ADR-027/028/029/030): it must be versioned, diffable data changed by migration,
  because SIG-STORE-038 forbids rewriting history to a newer vocabulary.
- **Fixtures without a canary (or a canary without fixtures).** Rejected: SIG-PARSE-007/008
  are complementary — fixtures pin known inputs and pass forever; the canary catches an
  upstream that changes *after* the fixture was captured.

## Revisit trigger

A concrete layer-3/4/5 parser (PDF text/table, OCR) is wired by P07.2/P07.3 and needs the
layer interface to carry more than a method string (e.g. per-layer confidence or fallback
chains); or the reason-kind/signal-strength fields earn a first-class physical column in an
additive P08 migration; or the nightly canary is formalised as an ops schedule and the
alerting contract (thresholds, destinations) needs to live in data; or a real records
response exhibits an archetype the four detected here do not cover (e.g. an encrypted ZIP
member, a nested archive deeper than one level) and classification must grow to route it.
