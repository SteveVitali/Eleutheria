# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The wired redaction pipeline (P36.15; SIG-PUB-015, SIG-PUB-016, SIG-EVID-011).

Until this row ``evidence.redaction.redact`` was a helper with no caller. This
module is the non-test path that drives it, end to end:

1. **Propose** — :func:`propose_redaction` records the redaction proposal as a
   ``kind="redaction"`` :class:`~resolution.review_queue.ReviewItem` whose
   payload binds the parent capture, the exact spans (offsets + the removed
   bytes' digests — never the removed text itself), the method and the version.
   The item id is deterministic so a re-proposal of the same scope dedups.
2. **Review** — the human adjudicates through the curation-owned review
   mechanism (``review_decision``, append-only): the recorded reviewer is a
   *role*, never a personal name (Part VIII §0.7). This module never writes a
   decision — the pipeline **never self-approves** a redaction.
3. **Apply** — :func:`run_redaction` reads the latest decision; anything short
   of a recorded ``accept`` is a loud refusal
   (:class:`~evidence.redaction.RedactionReviewRequired`). It verifies the
   stored parent bytes, applies the reviewed scope through
   :func:`evidence.redaction.apply_redaction` (which calls ``redact()`` and
   proves the removed text is absent from the derivative's text layer), and
   writes the derivative as a **new OCFL object** via
   :meth:`~connectors.capture_ocfl.OcflCaptureStore.put_derivative` carrying the
   ``sig.redaction-review/1`` applied-record sidecar. The parent's bytes are
   write-once and never touched (SIG-EPIS-006).

A re-redaction is a *new* derivative — a fresh proposal (new scope → new item
id), a fresh review, a fresh OCFL object — never an edit (§45.2 stays
compatible: replace-in-place is expressed as a new capture + new review).

Staging boundary: this module mutates only the stores it is handed — an OCFL
root (new object only) and the review queue (proposal + reads). Whether the
derivative's ``evidence_capture`` row lands on the spine is the caller's act
under the review record; this module never writes the claim spine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from evidence.digest import multihash
from evidence.redaction import (
    REVIEW_SCHEMA,
    RedactionError,
    RedactionOutcome,
    RedactionReview,
    RedactionReviewRequired,
    RedactionSpan,
    apply_redaction,
    decode_document,
    spans_for_strings,
)
from resolution.review_queue import ReviewItem

from .capture_ocfl import OcflCaptureStore, capture_object_id

if TYPE_CHECKING:
    from resolution.review_queue import ReviewQueue

#: The ``review_item.kind`` a redaction proposal enqueues as — one more proposal
#: kind on the curation-owned mechanism (beside ``er_match``/``model_extraction``).
REDACTION = "redaction"


@dataclass(frozen=True)
class RedactionResult:
    """The product of :func:`run_redaction`: the derivative's capture ref, the
    ``evidence_capture`` row values, and the applied review record."""

    outcome: RedactionOutcome
    capture_ref: Any  # connectors.stages.CaptureRef
    review_item_id: str

    def to_row(self) -> dict[str, Any]:
        """A JSON-safe summary (record carries digests, never removed text)."""
        return {
            "item_id": self.review_item_id,
            "derivative_digest": self.outcome.capture.content_digest,
            "derivative_object_id": self.capture_ref.ocfl_object_id,
            "ocfl_version": self.capture_ref.ocfl_version,
            "byte_size": self.capture_ref.byte_size,
            "record": self.outcome.record,
        }


def redaction_item_id(parent_capture_id: str, spans: tuple[RedactionSpan, ...]) -> str:
    """The deterministic review-item id for a proposed scope.

    Same parent + same scope ⇒ same item — a re-proposal dedups; a *new* scope
    (a re-redaction) is a new item and so a new review and a new derivative.
    """
    scope = json.dumps([s.to_row() for s in sorted(spans, key=lambda s: s.start)], sort_keys=True)
    digest = sha256(f"{parent_capture_id}:{scope}".encode()).hexdigest()[:16]
    return f"redaction:{parent_capture_id}:{digest}"


def propose_redaction(
    *,
    parent_capture_id: str,
    parent_digest: str,
    parent_bytes: bytes,
    media_type: str,
    spans: tuple[RedactionSpan, ...] | None = None,
    literals: tuple[str, ...] | list[str] | None = None,
    method: str,
    version: str,
    scope_note: str = "",
) -> ReviewItem:
    """Build the ``kind="redaction"`` proposal a human reviews (step 1).

    ``spans`` name code-point offsets over the decoded document (the canonical
    scope form); ``literals`` name the exact strings to remove — resolved
    against the decoded bytes to *every* occurrence, each bound by its digest.
    Exactly one of the two must be given. The proposal records digests, never
    the removed text, so the review item itself is publishable-safe.
    """
    text = decode_document(parent_bytes, media_type)
    if (spans is None) == (not literals):
        raise RedactionError("scope the redaction by exactly one of spans or literals")
    if literals:
        resolved = spans_for_strings(text, literals)
    else:
        assert spans is not None
        # Digest-bind every span so the proposal names the exact bytes the
        # review approves, never the text itself.
        resolved = tuple(
            sorted(
                (
                    RedactionSpan(
                        start=s.start,
                        end=s.end,
                        sha256=(s.sha256 or sha256(text[s.start : s.end].encode()).hexdigest()),
                    )
                    for s in spans
                ),
                key=lambda s: s.start,
            )
        )
        if not resolved:
            raise RedactionError("a redaction proposal must scope at least one span")
        for s in resolved:
            if s.end > len(text) or s.start < 0 or s.end <= s.start:
                raise RedactionError(f"redaction span [{s.start}:{s.end}] is outside the document")
    # The note rides the publishable-safe record — it must never carry the
    # text being redacted.
    if scope_note:
        for s in resolved:
            if text[s.start : s.end] and text[s.start : s.end] in scope_note:
                raise RedactionError("the scope note must not contain the text being redacted")
    item = ReviewItem(
        item_id=redaction_item_id(parent_capture_id, resolved),
        kind=REDACTION,
        summary=(
            f"redact {len(resolved)} span(s) of capture {parent_capture_id} ({method} {version})"
        ),
        payload={
            "schema": REVIEW_SCHEMA,
            "parent_capture_id": parent_capture_id,
            "parent_digest": parent_digest,
            "media_type": media_type,
            "method": method,
            "version": version,
            "spans": [s.to_row() for s in resolved],
            "span_count": len(resolved),
            "scope_note": scope_note,
            "proposed_at": datetime.now(UTC).isoformat(),
        },
    )
    return item


def _item_spans(item: ReviewItem) -> tuple[RedactionSpan, ...]:
    return tuple(
        RedactionSpan(start=int(s["start"]), end=int(s["end"]), sha256=str(s.get("sha256") or ""))
        for s in (item.payload.get("spans") or [])
    )


def _decisions_for(queue: Any, item_id: str) -> tuple[Any, ...]:
    """The item's append-only decision history on either queue backend."""
    try:
        return tuple(queue.decisions(item_id))
    except TypeError:
        return tuple(d for d in queue.decisions() if d.item_id == item_id)


def run_redaction(
    store: OcflCaptureStore,
    queue: ReviewQueue | Any,
    *,
    item_id: str,
    retrieved_at: datetime | None = None,
) -> RedactionResult:
    """Apply a *reviewed* redaction: derivative OCFL object + review record (step 3).

    Reads the recorded decision history for the proposal — the **latest**
    decision must be a recorded human ``accept``; none, or a latest
    ``reject``, refuses loudly. The parent's bytes are read from the OCFL
    store and verified against the proposal's recorded digest before the
    reviewed scope is applied — a store whose bytes drifted from the reviewed
    evidence fails closed.
    """
    item = queue.get(item_id)
    if item is None or item.kind != REDACTION:
        raise RedactionError(f"no redaction review item {item_id!r}")
    for key in ("parent_capture_id", "parent_digest", "media_type", "method", "version"):
        if not item.payload.get(key):
            raise RedactionError(
                f"redaction review item {item_id!r} carries no {key!r} in its "
                "payload — the proposal is malformed, refuse to apply"
            )
    history = _decisions_for(queue, item_id)
    if not history:
        raise RedactionReviewRequired(
            f"redaction {item_id!r} has no recorded human review — the pipeline "
            "refuses; review is required, never optional (SIG-PUB-015)"
        )
    latest = history[-1]
    review = RedactionReview(
        item_id=item_id,
        decision=latest.decision,
        reviewer_role=latest.reviewer,
        decided_at=latest.decided_at,
        parent_capture_id=str(item.payload.get("parent_capture_id") or ""),
        method=str(item.payload.get("method") or ""),
        version=str(item.payload.get("version") or ""),
        spans=_item_spans(item),
    )

    parent_digest = str(item.payload.get("parent_digest") or "")
    if not store.has(parent_digest):
        raise RedactionError(
            f"the reviewed parent capture {parent_digest} is not in the store — "
            "refuse to redact evidence that is absent"
        )
    parent_bytes = store.get(parent_digest)
    actual_digest = multihash(parent_bytes)
    if actual_digest != parent_digest:
        raise RedactionError(
            f"the stored parent bytes digest to {actual_digest}, not the reviewed "
            f"{parent_digest} — refuse to redact evidence that drifted"
        )

    outcome = apply_redaction(
        parent_capture_id=str(item.payload["parent_capture_id"]),
        parent_content_digest=parent_digest,
        media_type=str(item.payload["media_type"]),
        parent_bytes=parent_bytes,
        spans=_item_spans(item),
        method=str(item.payload["method"]),
        version=str(item.payload["version"]),
        review=review,
    )
    ref = store.put_derivative(
        outcome.derivative_bytes,
        media_type=str(item.payload["media_type"]),
        parent_capture_id=str(item.payload["parent_capture_id"]),
        parent_digest=parent_digest,
        redaction=outcome.record,
        source_uri="",  # provenance lives on the parent's metadata sidecar
        retrieved_at=retrieved_at,
    )
    return RedactionResult(outcome=outcome, capture_ref=ref, review_item_id=item_id)


def enqueue_proposal(queue: ReviewQueue | Any, item: ReviewItem) -> bool:
    """Record the proposal on the review mechanism; returns ``True`` if new.

    The PG backend dedups on ``item_id`` (``ON CONFLICT DO NOTHING``); the
    in-memory queue raises on a duplicate, which this surfaces as ``False``
    only when the queued item is the identical proposal (idempotent replay).
    """
    try:
        result = queue.enqueue(item)
    except ValueError:
        existing = queue.get(item.item_id)
        if existing is not None and existing.payload == item.payload:
            return False
        raise
    return bool(result) if result is not None else True


__all__ = [
    "REDACTION",
    "RedactionResult",
    "capture_object_id",
    "enqueue_proposal",
    "propose_redaction",
    "redaction_item_id",
    "run_redaction",
]
