# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG `parsing` package — the acquisition-side parsing and extraction stage (§24–§25).

P05.2 adds the **model-assisted extraction scaffolding** — the LLM boundary
(:mod:`parsing.extraction`, §25, SIG-LLM-001–007): every extraction records its
``model_id``/``prompt_version``/deterministic parameters and is schema-validated
(SIG-LLM-003); every extracted claim carries a source span whose text must appear in the
capture or it is rejected (SIG-LLM-004 / SIG-PARSE-003); every extracted claim is R6 and
``PROPOSED`` with no path to the graph (SIG-LLM-005); the pipeline queues rather than
fails when the model is unavailable, emitting no lowered-standard claim (SIG-LLM-007);
and each extraction type carries a human-review sampling rate and a gold-accuracy floor
below which it is demoted to human-only (SIG-LLM-006).
"""

__version__ = "0.0.0"
