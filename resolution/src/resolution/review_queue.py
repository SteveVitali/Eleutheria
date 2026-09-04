# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The internal review queue and curation contract (§14.6, §25, §27).

This is where a human adjudicates the two kinds of *proposal* the pipeline produces and
which are forbidden to reach the graph on their own:

* **Tier-4/5 probabilistic ER matches** (:class:`resolution.probabilistic.ProbabilisticMatch`,
  P05.1), each carrying the per-comparison match-weight decomposition that is surfaced
  inline as the **confidence explanation** (SIG-IDENT-025) — an unexplainable merge is a
  violation of the defining standard.
* **Model-assisted extractions** (:class:`parsing.extraction.ExtractedClaim`, P05.2),
  each R6/``PROPOSED`` and carrying its ``model_id``/``prompt_version`` provenance.

Two load-bearing invariants, both pinned by tests:

* **Nothing here writes to the graph.** A :class:`ReviewQueue` records a
  :class:`ReviewDecision`; it has no path that mutates an entity, mints an identifier, or
  emits a claim. LLM output reaches *only* this queue (SIG-IDENT-026, SIG-LLM-002).
* **Every decision on a model-assisted item logs the model id and prompt version**
  (SIG-IDENT-026): :meth:`ReviewQueue.decide` copies them from the item onto the
  decision, so a human adjudication of model output is always attributable to the exact
  model and prompt that proposed it.

The queue is a plain, file-serialisable value object (JSON via :meth:`to_dict` /
:meth:`from_dict`), the persistence P05.1 deferred here; the curation *UI* is the plain
CLI in :mod:`resolution.cli` (``review`` sub-commands) — the public web surface is P15.x.
This module takes a *forward* pipeline dependency on :mod:`parsing.extraction` (parsing
runs upstream of resolution); parsing never imports resolution.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from parsing.extraction import ExtractedClaim

from .probabilistic import ProbabilisticMatch

__all__ = [
    "ER_MATCH",
    "MODEL_EXTRACTION",
    "ACCEPT",
    "REJECT",
    "ConfidenceFactor",
    "ReviewItem",
    "ReviewDecision",
    "ReviewQueue",
    "review_item_from_match",
    "review_item_from_extraction",
    "surface_confidence_explanation",
]

# The two kinds of proposal the queue adjudicates.
ER_MATCH = "er_match"
MODEL_EXTRACTION = "model_extraction"

# The two decisions a reviewer can record. Accept/reject only — the queue neither
# resolves contradictions nor edits the proposal (SIG-LLM-002).
ACCEPT = "accept"
REJECT = "reject"
_DECISIONS = frozenset({ACCEPT, REJECT})


@dataclass(frozen=True)
class ConfidenceFactor:
    """One line of the confidence explanation surfaced to the reviewer (SIG-IDENT-025).

    For a probabilistic match, ``name`` is the compared column, ``weight`` is that
    column's Bayes factor (``m/u``), and ``detail`` is the human-readable comparison-level
    label — the per-comparison decomposition that makes the match weight explainable.
    """

    name: str
    weight: float
    detail: str

    def to_row(self) -> dict[str, Any]:
        return {"name": self.name, "weight": self.weight, "detail": self.detail}

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> ConfidenceFactor:
        return cls(name=str(row["name"]), weight=float(row["weight"]), detail=str(row["detail"]))


@dataclass(frozen=True)
class ReviewItem:
    """A proposal awaiting human adjudication — an ER match or a model extraction.

    ``confidence`` holds the per-comparison decomposition surfaced inline (SIG-IDENT-025);
    ``overall_weight`` is the match weight for an ER match (``None`` for an extraction —
    a model does not produce a confidence value, SIG-LLM-002.4). ``model_id`` /
    ``prompt_version`` are set for model-assisted items and ``None`` for a deterministic
    ER match; :attr:`model_assisted` reads them.
    """

    item_id: str
    kind: str
    summary: str
    confidence: tuple[ConfidenceFactor, ...] = ()
    overall_weight: float | None = None
    model_id: str | None = None
    prompt_version: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    @property
    def model_assisted(self) -> bool:
        """True when the proposal came from a model (its decision must log model/prompt)."""
        return self.model_id is not None

    def to_row(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "kind": self.kind,
            "summary": self.summary,
            "confidence": [factor.to_row() for factor in self.confidence],
            "overall_weight": self.overall_weight,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> ReviewItem:
        weight = row.get("overall_weight")
        return cls(
            item_id=str(row["item_id"]),
            kind=str(row["kind"]),
            summary=str(row["summary"]),
            confidence=tuple(ConfidenceFactor.from_row(f) for f in row.get("confidence", [])),
            overall_weight=None if weight is None else float(weight),
            model_id=row.get("model_id"),
            prompt_version=row.get("prompt_version"),
            payload=dict(row.get("payload", {})),
        )


@dataclass(frozen=True)
class ReviewDecision:
    """A human adjudication of one queue item (SIG-IDENT-026).

    ``decision`` is ``accept`` or ``reject``; ``reviewer`` names the human. For a
    model-assisted item ``model_id`` and ``prompt_version`` MUST be present — they are the
    provenance logged with every decision on model output (SIG-IDENT-026); the queue sets
    them from the item. ``rationale`` MAY carry a model-generated review rationale
    (SIG-LLM-001) — it is a note for the human, never an authority.
    """

    item_id: str
    decision: str
    reviewer: str
    decided_at: str
    model_id: str | None = None
    prompt_version: str | None = None
    rationale: str | None = None

    def __post_init__(self) -> None:
        if self.decision not in _DECISIONS:
            raise ValueError(f"decision must be one of {sorted(_DECISIONS)}, got {self.decision!r}")
        if not self.reviewer:
            raise ValueError("a review decision MUST record the human reviewer (SIG-IDENT-026)")

    @property
    def accepted(self) -> bool:
        return self.decision == ACCEPT

    def to_row(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "decision": self.decision,
            "reviewer": self.reviewer,
            "decided_at": self.decided_at,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "rationale": self.rationale,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> ReviewDecision:
        return cls(
            item_id=str(row["item_id"]),
            decision=str(row["decision"]),
            reviewer=str(row["reviewer"]),
            decided_at=str(row["decided_at"]),
            model_id=row.get("model_id"),
            prompt_version=row.get("prompt_version"),
            rationale=row.get("rationale"),
        )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ReviewQueue:
    """The internal review queue: pending proposals, decided proposals, and decisions.

    A proposal is :meth:`enqueue`\\ d, appears in :meth:`pending`, and is moved out by
    :meth:`decide`, which records an append-only :class:`ReviewDecision`. The queue has
    **no** graph-write path — accepting an item records the decision; the downstream
    claim-table writer that acts on an accepted decision is P08.x. Decisions are
    append-only: an item, once decided, is not re-decided (SIG-IDENT-026, P1–P3).
    """

    def __init__(self) -> None:
        self._pending: dict[str, ReviewItem] = {}
        self._decided: dict[str, ReviewItem] = {}
        self._decisions: list[ReviewDecision] = []

    def enqueue(self, item: ReviewItem) -> None:
        """Add a proposal to the queue (SIG-LLM-002: the only sink for model output)."""
        if item.item_id in self._pending or item.item_id in self._decided:
            raise ValueError(f"review item {item.item_id!r} is already in the queue")
        self._pending[item.item_id] = item

    def pending(self) -> tuple[ReviewItem, ...]:
        """The undecided proposals, ordered by id (deterministic for the UI/tests)."""
        return tuple(self._pending[k] for k in sorted(self._pending))

    def decisions(self) -> tuple[ReviewDecision, ...]:
        """Every decision recorded so far, in the order they were made (append-only)."""
        return tuple(self._decisions)

    def get(self, item_id: str) -> ReviewItem | None:
        return self._pending.get(item_id) or self._decided.get(item_id)

    def decide(
        self,
        item_id: str,
        decision: str,
        *,
        reviewer: str,
        rationale: str | None = None,
        decided_at: str | None = None,
    ) -> ReviewDecision:
        """Record a human accept/reject on a pending item (SIG-IDENT-026).

        Copies the item's ``model_id``/``prompt_version`` onto the decision so a decision
        on model output always logs the model and prompt that produced it. Moves the item
        out of ``pending`` and appends the decision; it does **not** write to the graph.
        """
        item = self._pending.get(item_id)
        if item is None:
            if item_id in self._decided:
                raise ValueError(f"review item {item_id!r} has already been decided")
            raise ValueError(f"no pending review item {item_id!r}")
        record = ReviewDecision(
            item_id=item_id,
            decision=decision,
            reviewer=reviewer,
            decided_at=decided_at if decided_at is not None else _now_iso(),
            model_id=item.model_id,
            prompt_version=item.prompt_version,
            rationale=rationale,
        )
        # A model-assisted decision without its provenance is a violation (SIG-IDENT-026).
        if item.model_assisted and (record.model_id is None or record.prompt_version is None):
            raise ValueError(
                "a decision on model-assisted output MUST log model_id and prompt_version "
                "(SIG-IDENT-026)"
            )
        del self._pending[item_id]
        self._decided[item_id] = item
        self._decisions.append(record)
        return record

    def to_dict(self) -> dict[str, Any]:
        """Serialise the whole queue to a JSON-safe dict (the persistence P05.1 deferred)."""
        return {
            "pending": [item.to_row() for item in self.pending()],
            "decided": [self._decided[k].to_row() for k in sorted(self._decided)],
            "decisions": [decision.to_row() for decision in self._decisions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReviewQueue:
        queue = cls()
        for row in data.get("pending", []):
            item = ReviewItem.from_row(row)
            queue._pending[item.item_id] = item
        for row in data.get("decided", []):
            item = ReviewItem.from_row(row)
            queue._decided[item.item_id] = item
        for row in data.get("decisions", []):
            queue._decisions.append(ReviewDecision.from_row(row))
        return queue


def review_item_from_match(match: ProbabilisticMatch) -> ReviewItem:
    """A review item for a tier-4/5 probabilistic ER match (SIG-IDENT-025).

    The confidence explanation is the match's per-comparison Bayes-factor decomposition,
    surfaced inline; ``overall_weight`` is the Fellegi–Sunter match weight (computed by
    rule from the model, not a model-produced confidence). Not model-assisted.
    """
    return ReviewItem(
        item_id=f"er_match:{match.left}~{match.right}",
        kind=ER_MATCH,
        summary=(
            f"tier {match.tier_label}: {match.left} ~ {match.right} "
            f"(weight {match.match_weight:+.2f}, p={match.match_probability:.3f})"
        ),
        confidence=tuple(
            ConfidenceFactor(name=c.column, weight=c.bayes_factor, detail=c.label)
            for c in match.decomposition
        ),
        overall_weight=match.match_weight,
        payload=dict(match.match_evidence),
    )


def review_item_from_extraction(claim: ExtractedClaim) -> ReviewItem:
    """A review item for a model-assisted extraction (SIG-LLM-004/005, SIG-IDENT-026).

    Carries the model provenance so its decision logs model/prompt; the confidence
    explanation records the source span (a model does not produce a confidence value,
    SIG-LLM-002.4). The payload is the full R6/``PROPOSED`` claim row.
    """
    span = claim.span
    return ReviewItem(
        item_id=f"model_extraction:{claim.extraction.model_id}:{span.start}:{span.end}",
        kind=MODEL_EXTRACTION,
        summary=(
            f"{claim.subject} {claim.predicate} {claim.value!r} "
            f"[{claim.source_reliability}/{claim.claim_status}]"
        ),
        confidence=(
            ConfidenceFactor(
                name="source_span",
                weight=float(span.end - span.start),
                detail=f"{span.text!r} @ [{span.start}:{span.end}]",
            ),
        ),
        overall_weight=None,
        model_id=claim.extraction.model_id,
        prompt_version=claim.extraction.prompt_version,
        payload=claim.to_row(),
    )


def surface_confidence_explanation(item: ReviewItem) -> str:
    """Render the inline confidence explanation a reviewer sees (SIG-IDENT-025).

    For an ER match this is the per-comparison decomposition and the total match weight;
    for a model extraction it is the model/prompt provenance and the source span. The
    text is what the curation UI shows next to the accept/reject control.
    """
    lines = [item.summary]
    if item.model_assisted:
        lines.append(f"  model: {item.model_id}  prompt: {item.prompt_version}")
    if item.overall_weight is not None:
        lines.append(f"  overall match weight: {item.overall_weight:+.2f}")
    for factor in item.confidence:
        lines.append(f"    {factor.name}: {factor.weight:+.3f}  [{factor.detail}]")
    return "\n".join(lines)
