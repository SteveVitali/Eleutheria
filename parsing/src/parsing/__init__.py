# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `parsing` package — the acquisition-side parsing and extraction stage (§24–§25).

P07.1 adds the **layered document-parsing stack** (§24) — the parser interface every
connector extracts through:

* :mod:`parsing.layers` — the seven extraction layers and the **cheapest sufficient
  method**, recorded on the extraction (SIG-PARSE-001);
* :mod:`parsing.classification` — **file classification before parsing**, with the verdict
  recorded and mixed-format ZIPs classified **per member** (SIG-PARSE-002);
* :mod:`parsing.locator` — the **mandatory locator** (page/bbox/cell/row/byte-range/DOM
  path) every claim carries; a locator-less extraction is rejected (SIG-PARSE-003);
* :mod:`parsing.claim` — the claim contract that **preserves ``raw_value``** before any
  typing, **including for values SIG cannot parse** (SIG-PARSE-004, P2);
* :mod:`parsing.reason_codes` — reason-code normalization through a **versioned,
  inspectable, reversible** mapping stored as data, with the mapping version stamped on the
  claim and free-text vs constrained-dropdown reasons distinguished (SIG-PARSE-005/006);
* :mod:`parsing.drift` — parser-drift defences: committed **fixtures** per parser and a
  nightly **canary** that alerts (never silently drops) on structural change (SIG-PARSE-007/008).

P05.2 added the **model-assisted extraction scaffolding** — the LLM boundary
(:mod:`parsing.extraction`, §25, SIG-LLM-001–007), which layer 6 of the stack wires in:
every extraction records its ``model_id``/``prompt_version``/deterministic parameters and
is schema-validated (SIG-LLM-003); every extracted claim carries a source span whose text
must appear in the capture or it is rejected (SIG-LLM-004 / SIG-PARSE-003); every extracted
claim is R6 and ``PROPOSED`` with no path to the graph (SIG-LLM-005); the pipeline queues
rather than fails when the model is unavailable, emitting no lowered-standard claim
(SIG-LLM-007); and each extraction type carries a human-review sampling rate and a
gold-accuracy floor below which it is demoted to human-only (SIG-LLM-006).
"""

__version__ = "0.0.0"
