# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Model-assisted extraction scaffolding — the LLM boundary (§25, SIG-LLM-001–007).

This is the guardrail that keeps model output *out of the graph*. A model MAY propose
candidate structured claims (SIG-LLM-001), but everything it produces is a **candidate
for the review queue** — R6 and `PROPOSED`, never an auto-write (SIG-LLM-002/005). This
module makes that boundary mechanical, not aspirational:

* **Every extraction records its provenance** (:class:`ModelExtraction`): the
  ``model_id``, the ``prompt_version``, and the deterministic decoding parameters
  actually used (SIG-LLM-003). Model output is never anonymous.
* **Output is validated against a schema** (:func:`validate_output`) before anything
  else runs (SIG-LLM-003) — a structurally malformed candidate is rejected at the door.
* **Every extracted claim carries a source span** (:class:`SourceSpan`) whose text must
  appear in the capture (:func:`validate_span`). A span that is not present in the
  capture is the signature of a hallucination and is rejected — the single most
  important guardrail (SIG-LLM-004 / SIG-PARSE-003).
* **Every extracted claim is R6 and `PROPOSED`** (:class:`ExtractedClaim`), with no path
  to the graph at all (SIG-LLM-005). A model can only *propose*.
* **The pipeline degrades gracefully** (:func:`run_extraction`): when the model is
  unavailable the work *queues* rather than failing, and **no claim is emitted at a
  lowered evidentiary standard** to compensate (SIG-LLM-007).
* **Each extraction type has a human-review sampling rate and a gold-accuracy floor**
  (:class:`ExtractionTypePolicy`); when measured accuracy falls below the floor the type
  is **demoted to human-only** (SIG-LLM-006).

The pure ``m/u``-style split from :mod:`resolution.probabilistic` applies here too: the
policy and schema are versioned data (:mod:`extraction_schema.toml <parsing.data>`), and
the code is deterministic and fully testable — no network call is made by this module;
a caller injects a :class:`ModelClient`.
"""

from __future__ import annotations

import hashlib
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cache
from importlib.resources import files
from typing import Any, Protocol

__all__ = [
    "EXTRACTION_SCHEMA_VERSION",
    "R6",
    "PROPOSED",
    "MODEL_UNAVAILABLE",
    "ExtractionRejected",
    "SourceSpan",
    "ModelExtraction",
    "ExtractedClaim",
    "ExtractionOutcome",
    "ExtractionTypePolicy",
    "ModelClient",
    "deterministic_parameters",
    "validate_span",
    "validate_output",
    "extract_claims",
    "run_extraction",
    "load_policies",
    "should_sample_for_review",
    "measure_accuracy",
    "evaluate_demotion",
]

# Model-extracted claims are R6 (§10.4 — heuristic/automated/model-generated candidate)
# and enter as PROPOSED (SIG-LLM-005). Kept as named constants so callers and tests refer
# to the contract, not a bare string. The value mirrors resolution.probabilistic.PROPOSED
# without taking a dependency on it (parsing is upstream of resolution in the pipeline).
R6 = "R6"
PROPOSED = "PROPOSED"

# The reason recorded when work queues because the model could not be reached
# (SIG-LLM-007). The work waits; no lowered-standard claim is emitted to compensate.
MODEL_UNAVAILABLE = "model_unavailable"


class ExtractionRejected(ValueError):
    """A model extraction that violates a hard guardrail (schema / span / standard).

    Raised by the span, schema, and claim-construction gates. It is a *rejection*, not a
    failure of the pipeline: a rejected extraction simply does not become a claim (a
    hallucinated span, a malformed candidate, a lowered evidentiary standard).
    """


@cache
def _schema() -> dict[str, Any]:
    resource = files("parsing").joinpath("data", "extraction_schema.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


EXTRACTION_SCHEMA_VERSION: str = str(_schema()["version"])


def deterministic_parameters() -> dict[str, Any]:
    """The deterministic decoding parameters a caller must pin (SIG-LLM-003).

    Greedy decoding with a fixed seed, read from the versioned schema — a convenience so
    callers record the same reproducible parameters rather than inventing their own.
    """
    return dict(_schema()["deterministic_parameters"])


@dataclass(frozen=True)
class SourceSpan:
    """The exact source location a model-extracted value came from (SIG-PARSE-003/LLM-004).

    ``text`` is the verbatim substring the value was read from; ``start``/``end`` are its
    character offsets in the capture; ``locator`` is the addressable pointer (page, bbox,
    cell, row, byte range, DOM path) the evidence viewer (§39.6) resolves. A span that
    cannot be located in the capture is a hallucination — that check is
    :func:`validate_span`, run against the real capture text.
    """

    text: str
    start: int
    end: int
    locator: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.text:
            raise ExtractionRejected(
                "a source span MUST carry the exact text it came from (SIG-LLM-004)"
            )
        if self.start < 0 or self.end < self.start:
            raise ExtractionRejected(
                f"a source span MUST have 0 <= start <= end, got [{self.start}, {self.end})"
            )
        if not self.locator:
            raise ExtractionRejected(
                "a source span MUST carry a locator (page/bbox/cell/row/byte-range/DOM "
                "path) so the value can be located in the capture (SIG-PARSE-003)"
            )


def validate_span(span: SourceSpan, capture_text: str) -> None:
    """Reject a span whose text is not present in the capture (SIG-LLM-004, SIG-PARSE-003).

    Two mechanical checks: the span's offsets must fall within the capture, and the
    verbatim ``text`` must actually appear at those offsets. A span that does not appear
    in the capture is the signature of a hallucinated extraction and fails validation.
    This is what makes hallucination detectable mechanically rather than by eye.
    """
    if span.end > len(capture_text):
        raise ExtractionRejected(
            f"span offsets [{span.start}, {span.end}) exceed the capture length "
            f"{len(capture_text)} — the span is not present in the capture (SIG-LLM-004)"
        )
    if capture_text[span.start : span.end] != span.text:
        raise ExtractionRejected(
            "span text does not match the capture at its offsets — a span not present in "
            "the capture is rejected (SIG-LLM-004, SIG-PARSE-003)"
        )


@dataclass(frozen=True)
class ModelExtraction:
    """The provenance every model-assisted extraction records (SIG-LLM-003).

    ``model_id`` and ``prompt_version`` identify exactly which model and prompt produced
    the candidate; ``parameters`` are the deterministic decoding parameters actually used
    (temperature, seed, …). This record travels with every :class:`ExtractedClaim` and is
    logged against the human review decision (SIG-IDENT-026) — model output is never
    anonymous, and a decision can always be traced to the model and prompt that proposed
    it.
    """

    model_id: str
    prompt_version: str
    extraction_type: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        for name, value in (
            ("model_id", self.model_id),
            ("prompt_version", self.prompt_version),
            ("extraction_type", self.extraction_type),
        ):
            if not value:
                raise ExtractionRejected(
                    f"a model-assisted extraction MUST record a non-empty {name} (SIG-LLM-003)"
                )
        if not self.parameters:
            raise ExtractionRejected(
                "a model-assisted extraction MUST record the deterministic parameters "
                "actually used (SIG-LLM-003)"
            )

    def to_row(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "extraction_type": self.extraction_type,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class ExtractedClaim:
    """A single model-extracted candidate claim (SIG-LLM-004/005).

    It carries the subject/predicate/value triple, the mandatory :class:`SourceSpan`, and
    the :class:`ModelExtraction` provenance. It is **always** R6 and ``PROPOSED`` and has
    no path to the graph: a model may only propose into the review queue (SIG-LLM-002/005).
    Construction enforces the standard — there is no way to build a lower-reliability or
    already-accepted model claim through this type.
    """

    subject: str
    predicate: str
    value: str
    span: SourceSpan
    extraction: ModelExtraction
    source_reliability: str = R6
    claim_status: str = PROPOSED

    def __post_init__(self) -> None:
        if self.source_reliability != R6:
            raise ExtractionRejected(
                f"a model-extracted claim MUST be R6 (§10.4, SIG-LLM-005), got "
                f"{self.source_reliability!r}"
            )
        if self.claim_status != PROPOSED:
            raise ExtractionRejected(
                f"a model-extracted claim MUST enter as PROPOSED (SIG-LLM-005), got "
                f"{self.claim_status!r}"
            )

    @property
    def writes_to_graph(self) -> bool:
        """Always False — model output reaches only the review queue (SIG-LLM-002)."""
        return False

    def to_row(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "value": self.value,
            "span": {
                "text": self.span.text,
                "start": self.span.start,
                "end": self.span.end,
                "locator": dict(self.span.locator),
            },
            "extraction": self.extraction.to_row(),
            "source_reliability": self.source_reliability,
            "claim_status": self.claim_status,
        }


def validate_output(raw_items: Sequence[Mapping[str, Any]]) -> None:
    """Validate raw model output against the extraction schema (SIG-LLM-003).

    Every candidate item MUST carry the schema's required claim fields, and its ``span``
    MUST carry the required span fields. A structurally invalid output is rejected before
    any span/capture check — the schema is the first gate model output passes.
    """
    schema = _schema()
    claim_required: list[str] = list(schema["schema"]["claim_field"]["required"])
    span_required: list[str] = list(schema["schema"]["span"]["required"])
    for i, item in enumerate(raw_items):
        missing = [key for key in claim_required if key not in item]
        if missing:
            raise ExtractionRejected(
                f"extraction item {i} is missing required field(s) {missing} (SIG-LLM-003)"
            )
        span = item["span"]
        if not isinstance(span, Mapping):
            raise ExtractionRejected(
                f"extraction item {i} 'span' must be an object with a locator (SIG-LLM-003)"
            )
        span_missing = [key for key in span_required if key not in span]
        if span_missing:
            raise ExtractionRejected(
                f"extraction item {i} span is missing required field(s) {span_missing} "
                "(SIG-LLM-003)"
            )


def extract_claims(
    raw_items: Sequence[Mapping[str, Any]],
    *,
    capture_text: str,
    extraction: ModelExtraction,
) -> list[ExtractedClaim]:
    """Build the R6/PROPOSED claims from raw model output, rejecting hallucinations.

    Runs the schema gate (SIG-LLM-003), then for every item validates its span against
    the capture (SIG-LLM-004) before constructing an :class:`ExtractedClaim` (which
    stamps R6/``PROPOSED``). Any item that fails a gate raises :class:`ExtractionRejected`:
    a span-less or unlocatable extraction never becomes a claim, and no claim is emitted
    at a lowered standard.
    """
    validate_output(raw_items)
    claims: list[ExtractedClaim] = []
    for item in raw_items:
        raw_span = item["span"]
        span = SourceSpan(
            text=str(raw_span["text"]),
            start=int(raw_span["start"]),
            end=int(raw_span["end"]),
            locator=dict(raw_span["locator"]),
        )
        validate_span(span, capture_text)
        claims.append(
            ExtractedClaim(
                subject=str(item["subject"]),
                predicate=str(item["predicate"]),
                value=str(item["value"]),
                span=span,
                extraction=extraction,
            )
        )
    return claims


class ModelClient(Protocol):
    """The minimal model interface the extraction scaffolding drives.

    ``available`` reports whether the model can be reached right now; ``extract`` returns
    the raw candidate items for a capture. The scaffolding never calls ``extract`` when
    ``available`` is False — the work queues instead (SIG-LLM-007). Injecting this keeps
    the module deterministic and offline-testable; no network call lives here.
    """

    @property
    def available(self) -> bool: ...

    def extract(
        self, capture_text: str, *, extraction_type: str
    ) -> Sequence[Mapping[str, Any]]: ...


@dataclass(frozen=True)
class ExtractionOutcome:
    """The result of attempting a model-assisted extraction (SIG-LLM-007).

    On success ``claims`` holds the R6/``PROPOSED`` proposals and ``queued`` is False.
    When the model is unavailable ``queued`` is True, ``claims`` is empty, and ``reason``
    records why — the work item waits rather than the pipeline failing, and **no claim is
    emitted at a lowered evidentiary standard** to compensate.
    """

    claims: tuple[ExtractedClaim, ...] = ()
    queued: bool = False
    reason: str | None = None

    @property
    def degraded(self) -> bool:
        """True when this outcome represents queued-not-failed degradation (SIG-LLM-007)."""
        return self.queued


def run_extraction(
    client: ModelClient,
    capture_text: str,
    *,
    extraction: ModelExtraction,
) -> ExtractionOutcome:
    """Run one model-assisted extraction, degrading gracefully (SIG-LLM-007).

    If the client is unavailable the work is queued (an empty ``queued=True`` outcome) —
    it does not raise and it emits no claim. When available, it extracts, validates every
    span against the capture, and returns the R6/``PROPOSED`` proposals. A hallucinated
    (unlocatable-span) item still raises :class:`ExtractionRejected`: degradation queues
    work, it never lowers the evidentiary bar.
    """
    if not client.available:
        return ExtractionOutcome(queued=True, reason=MODEL_UNAVAILABLE)
    raw = client.extract(capture_text, extraction_type=extraction.extraction_type)
    claims = extract_claims(raw, capture_text=capture_text, extraction=extraction)
    return ExtractionOutcome(claims=tuple(claims))


@dataclass(frozen=True)
class ExtractionTypePolicy:
    """Per-extraction-type human-review sampling + gold-accuracy demotion (SIG-LLM-006).

    ``review_sample_rate`` is the fraction of this type's proposals sampled for human
    review; ``accuracy_threshold`` is the gold-set accuracy floor. ``human_only`` is the
    demoted state: once measured accuracy falls below the floor the model is no longer
    trusted for this type and every item is routed to a human (the effective sample rate
    becomes total).
    """

    extraction_type: str
    review_sample_rate: float
    accuracy_threshold: float
    human_only: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.review_sample_rate <= 1.0:
            raise ValueError(f"review_sample_rate must be in [0, 1], got {self.review_sample_rate}")
        if not 0.0 <= self.accuracy_threshold <= 1.0:
            raise ValueError(f"accuracy_threshold must be in [0, 1], got {self.accuracy_threshold}")

    @property
    def effective_sample_rate(self) -> float:
        """The sampling rate in force: total when demoted to human-only (SIG-LLM-006)."""
        return 1.0 if self.human_only else self.review_sample_rate


def load_policies() -> dict[str, ExtractionTypePolicy]:
    """The per-extraction-type sampling/demotion policies from versioned data (SIG-LLM-006)."""
    policies: dict[str, ExtractionTypePolicy] = {}
    for entry in _schema()["extraction_type"]:
        policy = ExtractionTypePolicy(
            extraction_type=str(entry["name"]),
            review_sample_rate=float(entry["review_sample_rate"]),
            accuracy_threshold=float(entry["accuracy_threshold"]),
        )
        policies[policy.extraction_type] = policy
    return policies


def should_sample_for_review(policy: ExtractionTypePolicy, claim: ExtractedClaim) -> bool:
    """Deterministically decide whether a proposal is sampled for human review (SIG-LLM-006).

    Uses a stable hash of the claim's identity (type + span offsets + value) so the same
    proposal always gets the same decision — sampling is reproducible, not random. When
    the type is demoted to human-only, everything is sampled.
    """
    if policy.human_only or policy.review_sample_rate >= 1.0:
        return True
    if policy.review_sample_rate <= 0.0:
        return False
    key = f"{policy.extraction_type}|{claim.span.start}|{claim.span.end}|{claim.value}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") / float(1 << 64)
    return bucket < policy.review_sample_rate


def measure_accuracy(predictions: Sequence[bool], gold: Sequence[bool]) -> float:
    """Fraction of predictions that match the gold labels (SIG-LLM-006).

    The accuracy measured against the gold set on the published cadence; the value
    :func:`evaluate_demotion` compares against the type's floor.
    """
    if len(predictions) != len(gold):
        raise ValueError("predictions and gold must be the same length")
    if not gold:
        raise ValueError("cannot measure accuracy against an empty gold set")
    correct = sum(1 for p, g in zip(predictions, gold, strict=True) if p == g)
    return correct / len(gold)


def evaluate_demotion(
    policy: ExtractionTypePolicy, measured_accuracy: float
) -> ExtractionTypePolicy:
    """Demote a type to human-only when its gold accuracy falls below the floor (SIG-LLM-006).

    Returns a policy with ``human_only=True`` if ``measured_accuracy`` is below
    ``accuracy_threshold``; otherwise returns the policy unchanged. A passing measurement
    never silently re-promotes a type that was already demoted — re-promotion is a
    deliberate, separate act.
    """
    if measured_accuracy < policy.accuracy_threshold:
        return replace(policy, human_only=True)
    return policy
