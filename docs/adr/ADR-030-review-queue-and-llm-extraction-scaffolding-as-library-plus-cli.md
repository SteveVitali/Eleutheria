# ADR-030: The review queue and the LLM-extraction scaffolding as library + CLI, in `resolution` and `parsing`

- **Status:** Accepted
- **Date:** 2026-08-27
- **Phase:** P05.2
- **Requirement ids:** SIG-IDENT-025, SIG-IDENT-026, SIG-LLM-001, SIG-LLM-002, SIG-LLM-003, SIG-LLM-004, SIG-LLM-005, SIG-LLM-006, SIG-LLM-007, SIG-PARSE-003, SIG-RECON-001
- **Spec:** docs/2_canonical_design_spec.md §25 (LLM usage policy), §14.6 (tiers 4–5 → review), §27 (the ER pipeline review path); ADR-029 (the probabilistic tier that produces the PROPOSED matches this queue reviews), ADR-026 (connectors/ER not DB-wired yet)

## Context

P05.2 owns two things the spec keeps tightly coupled: the **internal review queue +
curation UI** where a human adjudicates the tier-4/5 `PROPOSED` matches P05.1 produces
(SIG-IDENT-025/026), and the **model-assisted-extraction scaffolding** — the boundary
that keeps LLM output out of the graph (SIG-LLM-001–007, SIG-PARSE-003). Three questions
had to be settled:

1. **Which packages own this?** The frozen §47 layout (SIG-ENG-012) has no "review" or
   "curation" package, and adding one is an ADR-level act (as ADR-023 did for
   `evidence`). Two existing packages are the natural homes, and using them avoids
   minting a package for a cross-cutting concern.

2. **Is the "curation UI" a web app now?** `web/` is an explicit skeleton whose real
   surface is Phase 15 (P15.x is out of scope here, and the ticket says so).

3. **How does model output stay out of the graph mechanically**, not just by convention?

## Decision

1. **The LLM-extraction scaffolding lives in `parsing`** (`parsing/src/parsing/extraction.py`,
   `parsing/src/parsing/data/extraction_schema.toml`). Parsing is the acquisition-side
   extraction stage (§24–§25); this is where a model proposes candidate claims from
   documents. It has **no path to the graph**:
   - `ModelExtraction` records `model_id`, `prompt_version`, and the deterministic
     decoding parameters actually used, and `validate_output` checks raw output against a
     versioned schema before anything else runs (SIG-LLM-003).
   - `SourceSpan` + `validate_span` reject a span whose verbatim text is not present in
     the capture at its offsets — the mechanical hallucination guardrail (SIG-LLM-004 /
     SIG-PARSE-003). A span-less or unlocatable extraction never becomes a claim.
   - `ExtractedClaim` is **constructed** R6 and `PROPOSED` and refuses any other
     reliability/status — a lowered-standard model claim cannot be built (SIG-LLM-005);
     `writes_to_graph` is always `False`.
   - `run_extraction` **degrades gracefully**: an unavailable model returns a
     `queued=True` outcome with no claims and does not raise; no claim is emitted at a
     lowered standard to compensate (SIG-LLM-007).
   - `ExtractionTypePolicy` carries a per-extraction-type human-review sampling rate and a
     gold-accuracy floor; `evaluate_demotion` flips a type to **human-only** on a breach
     (SIG-LLM-006). Sampling (`should_sample_for_review`) is a deterministic hash, not
     randomness, so it is reproducible.

2. **The review queue + curation contract lives in `resolution`**
   (`resolution/src/resolution/review_queue.py`). It is downstream of parsing in the
   pipeline, so it may take a **forward dependency** on `parsing.extraction` (parsing
   never imports resolution — no cycle). It adjudicates both kinds of proposal:
   - a tier-4/5 `ProbabilisticMatch` (P05.1), whose per-comparison Bayes-factor
     decomposition is surfaced inline as the **confidence explanation** (SIG-IDENT-025);
   - a model-assisted `ExtractedClaim`, carrying its model/prompt provenance.
   `ReviewQueue.decide` records an append-only `ReviewDecision` and, for a model-assisted
   item, **logs `model_id` and `prompt_version`** with the decision (SIG-IDENT-026). The
   queue has **no** graph-write method: accepting an item records a decision; the
   claim-table writer that acts on it is P08.x.

3. **The curation UI is a plain CLI** (`sig-resolution review …` and `sig-parsing
   extract|sampling`, SIG-ENG-013) over a JSON-serialisable queue — the review-queue
   *persistence* P05.1 deferred here (RISK-P5-04). The public web surface is Phase 15;
   building it now would pre-empt P15.x. The CLI is enough to drive and verify the whole
   accept/reject flow with the confidence explanation shown inline.

## Consequences

Model output is now boxed by construction, not by discipline: a model can only produce an
R6/`PROPOSED` `ExtractedClaim` that carries a capture-verified span and its provenance,
and the only sink for it is a review queue with no graph-write path. A reviewer sees the
same per-comparison decomposition for a probabilistic match that P05.1 computes, and every
decision on model output is attributable to the model and prompt that proposed it. Costs
and deferrals, stated rather than hidden:

- **`resolution` now depends on `parsing`** (a new intra-workspace edge). This is a
  forward pipeline dependency and introduces no third-party packages, so `pylock.toml` is
  unchanged; `uv.lock` gains only the edge. The import-boundary test (only
  `orchestration/` may import an orchestrator) is unaffected.
- **No live claim-table write path and no web UI.** Like P05.1/ADR-029, the queue is a
  value object with `to_dict`/`from_dict` persistence and a CLI, not a DB writer or a web
  app. The append-only, provenance-carrying `ReviewDecision`/`ReviewItem` shapes make the
  P08.x wiring and the P15.x UI faithful drop-ins.
- **The model client is injected, never called here.** `run_extraction` drives a
  `ModelClient` protocol; this repo ships no model integration (no network call, no
  vendor SDK). That keeps the scaffolding deterministic and offline-testable and defers
  the actual model wiring to the operator — model *assisted extraction* is permitted
  (SIG-LLM-001), model *training* is not (SIG-LIC-004c), and neither is implemented here.

## Alternatives considered

- **A new `review`/`curation` package.** Rejected: the §47 layout is frozen
  (SIG-ENG-012) and a cross-cutting review surface does not warrant a package when two
  pipeline-adjacent homes exist; ADR-023's precedent (add a package only when a §-mandated
  home genuinely has none) does not apply here.
- **Putting the queue in `parsing`.** Rejected: it would force `parsing → resolution` (to
  adapt a `ProbabilisticMatch`), a backward pipeline dependency; resolution is downstream
  and is the correct owner of the ER proposals.
- **Building the web curation UI now.** Rejected: `web/` is a Phase-15 skeleton and P15.x
  is explicitly out of scope; a CLI + serialisable queue realises the contract at the
  layer that exists today.
- **Letting a model emit a claim directly / at a lower standard when unavailable.**
  Rejected outright: SIG-LLM-002/005/007. A model may only propose into the queue at R6,
  and unavailability queues work rather than lowering the bar.
- **Storing the extraction schema / sampling policy as Python literals.** Rejected for the
  same reason as the connector vocabularies and the Splink model (ADR-027/028/029): it is
  versioned, diffable data (`extraction_schema.toml`), changed by migration.

## Revisit trigger

The live claim-table writer (P08.x) lands and needs a firmer contract from the queue than
"in-memory items + `to_dict`"; or the Phase-15 web curation UI (P15.x) lands and supersedes
the CLI surface; or a real model client is wired and the `ModelClient` protocol needs to
grow (batching, streaming, cost controls); or the gold-accuracy cadence (SIG-LLM-006) is
formalised against a real gold set and the demotion policy needs per-type thresholds beyond
the seeded defaults.
