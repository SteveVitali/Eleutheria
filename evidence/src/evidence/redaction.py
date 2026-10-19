# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Redaction as a new capture (§17.5, SIG-EVID-011, SIG-PUB-015/016).

Redaction MUST produce a **new capture** with ``parent_capture_id`` set — never an
edit of the original (SIG-EPIS-006). The redaction method and version MUST be
recorded so that a mis-redaction can be identified and re-done. The original bytes
are write-once in OCFL and are never touched; the redacted derivative is a fresh
OCFL version with its own digest.

P36.15 wires the pipeline end to end:

* **The review record.** :class:`RedactionReview` is the append-only record of the
  human redaction decision — the scope approved, the method and version, the
  reviewer *role* (never a personal name, Part VIII §0.7) and the recorded
  timestamp. It is carried on the curation-owned review mechanism
  (``review_item``/``review_decision`` — see
  :mod:`connectors.redaction_pipeline`); a redaction without one is a pipeline
  error, never a silent pass, and the pipeline never self-approves.
* **Irreversible text-layer removal (SIG-PUB-016).** :func:`apply_spans`
  substitutes each approved span with a marker *in the decoded bytes* — the
  redacted text is physically absent from the derivative, never an overlay on
  extractable text. :func:`extract_text` is the extraction proof surface: a
  derivative whose extraction still yields a redacted string is rejected.
* **The derivative descriptor.** :class:`RedactionDerivative` is what a capture's
  metadata carries once a derivative exists; every excerpt surface
  (:func:`evidence.tiers.publishable_excerpt`) reads it — never the parent's raw
  excerpt.

Media coverage: the pipeline redacts the **text layer** of text-bearing captures
(``text/*``, JSON, XML, HTML). A binary container (PDF, PNG, WACZ, zip) has no
provably-redactable text layer here, so it is *refused* — a document-format
redactor (true PDF redaction, not overlay boxes) is a separate, deliberate act.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
from typing import Any

from .digest import multihash

#: The schema tag for the review/decision record a redaction proposal carries
#: (the ``review_item.payload`` of a ``kind="redaction"`` item) and for the
#: applied-redaction sidecar stored inside the derivative OCFL object.
REVIEW_SCHEMA = "sig.redaction-review/1"

#: The literal substituted for each redacted span in the derivative's text
#: layer — the same literal the ``restricted`` tier's excerpt surface uses.
REDACTION_MARKER = "[redacted]"

#: The media types whose captures carry a provably-redactable text layer.
#: Anything else is refused by :func:`apply_redaction` — a PDF/PNG/WACZ/zip has
#: bytes SIG cannot edit in place with an irreversibility guarantee.
TEXT_LAYER_MEDIA: frozenset[str] = frozenset(
    {
        "text/plain",
        "text/csv",
        "text/markdown",
        "text/html",
        "application/json",
        "application/geo+json",
        "application/ld+json",
        "text/xml",
        "application/xml",
        "application/xhtml+xml",
    }
)


class RedactionError(ValueError):
    """A redaction-pipeline failure — loud, never a silent pass."""


class RedactionReviewRequired(RedactionError):
    """No recorded (accepted) human review exists for this redaction."""


@dataclass(frozen=True)
class RedactionSpan:
    """One span of the raw document text to remove (code-point offsets).

    ``sha256`` is the hex digest of the exact removed text — recorded so the
    review binds *these bytes*, never the removed text itself (the record names
    what was redacted without carrying it).
    """

    start: int
    end: int
    sha256: str = ""

    def to_row(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "sha256": self.sha256}


@dataclass(frozen=True)
class RedactedCapture:
    """A redacted derivative capture, pointing back at the original."""

    parent_capture_id: str
    redaction_method: str
    redaction_version: str
    content_digest: str  # multihash of the redacted bytes
    byte_size: int
    redaction_applied: bool = True

    def to_row(self) -> dict[str, object]:
        """The ``evidence_capture`` column values for the redacted derivative."""
        return {
            "parent_capture_id": self.parent_capture_id,
            "redaction_applied": self.redaction_applied,
            "redaction_method": self.redaction_method,
            "redaction_version": self.redaction_version,
            "content_digest": self.content_digest,
            "byte_size": self.byte_size,
        }


@dataclass(frozen=True)
class RedactionReview:
    """The recorded human review a redaction must carry (append-only).

    Built by the pipeline from the curation review mechanism — a ``redaction``
    ``review_item`` (the proposal: parent, scope, method, version) plus the
    human's ``accept`` ``review_decision`` (the reviewer role + the recorded
    timestamp). ``decision`` MUST be ``accept`` — a redaction whose latest
    review is a rejection, or which has no review at all, is refused.
    """

    item_id: str
    decision: str
    reviewer_role: str  # a role, never a personal name (Part VIII §0.7)
    decided_at: str  # the review store's recorded timestamp
    parent_capture_id: str
    method: str
    version: str
    spans: tuple[RedactionSpan, ...] = ()

    def validate(self) -> None:
        """Fail-closed shape check — a malformed record is not a review."""
        if self.decision != "accept":
            raise RedactionReviewRequired(
                f"redaction review for {self.item_id!r} is {self.decision!r}, not an "
                "accept — a redaction requires a recorded human accept"
            )
        if not self.reviewer_role or len(self.reviewer_role) > 120:
            raise RedactionReviewRequired(
                "a redaction review MUST record the reviewer role (never a personal "
                "name, Part VIII §0.7)"
            )
        if "@" in self.reviewer_role or "://" in self.reviewer_role:
            raise RedactionReviewRequired(
                "the reviewer field must be a role (e.g. 'records officer'), never a "
                "personal identifier — an e-mail address or handle is not a role "
                "(Part VIII §0.7)"
            )
        if not self.decided_at:
            raise RedactionReviewRequired(
                "a redaction review MUST carry the decision's recorded timestamp"
            )
        if not self.parent_capture_id or not self.method or not self.version:
            raise RedactionError(
                "the redaction review MUST bind parent_capture_id, method and version (SIG-PUB-015)"
            )


@dataclass(frozen=True)
class RedactionDerivative:
    """The descriptor a capture's metadata carries once a redaction derivative
    exists — what every excerpt surface reads instead of the parent's bytes
    (SIG-PUB-015/016).

    ``excerpt`` is the derivative's own recorded excerpt (``None`` where none is
    bound yet — fail-closed: the parent's raw excerpt is never served instead).
    """

    capture_id: str
    content_digest: str
    method: str
    version: str
    excerpt: str | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "content_digest": self.content_digest,
            "redaction_method": self.method,
            "redaction_version": self.version,
        }


@dataclass(frozen=True)
class RedactionOutcome:
    """The product of :func:`apply_redaction`: the derivative bytes, the
    ``evidence_capture`` row values, the review record, and the sidecar the
    derivative object carries."""

    derivative_bytes: bytes
    capture: RedactedCapture
    review: RedactionReview
    record: dict[str, Any]  # the sig.redaction-review/1 sidecar payload


def _media(media_type: str) -> str:
    return media_type.split(";", 1)[0].strip().lower()


def decode_document(data: bytes, media_type: str) -> str:
    """Decode a text-bearing capture's raw bytes to text — strictly.

    Refused (``RedactionError``) for a media type with no provably-redactable
    text layer or for bytes that do not decode as UTF-8 — the pipeline fails
    closed rather than produce a non-irreversible "redaction".
    """
    mt = _media(media_type)
    if mt not in TEXT_LAYER_MEDIA and not mt.startswith("text/"):
        raise RedactionError(
            f"media type {media_type!r} has no text layer this pipeline can redact "
            "irreversibly (SIG-PUB-016) — binary captures need a format-aware "
            "redactor, never an overlay"
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RedactionError(f"capture bytes do not decode as UTF-8 under {media_type!r}") from exc


class _TextExtractor(HTMLParser):
    """Collects the *readable* text of an HTML document (tags stripped)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:  # noqa: D102
        self._parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self._parts)


def extract_text(data: bytes, media_type: str) -> str:
    """The *readable text layer* of a capture — the SIG-PUB-016 proof surface.

    ``text/*`` yields the decoded document; HTML/XHTML yields tag-stripped
    text; JSON yields every string key and value; XML yields element text. A
    derivative is acceptable only if none of the redacted strings can be
    recovered from this layer (or from the raw bytes — the stronger check
    :func:`apply_redaction` also runs).
    """
    mt = _media(media_type)
    text = decode_document(data, media_type)
    if mt in {"text/html", "application/xhtml+xml"}:
        extractor = _TextExtractor()
        extractor.feed(text)
        return extractor.text
    if mt in {"text/xml", "application/xml"}:
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise RedactionError(f"XML capture does not parse: {exc}") from exc
        return "".join(root.itertext())
    if mt in {"application/json", "application/geo+json", "application/ld+json"}:
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RedactionError(f"JSON capture does not parse: {exc}") from exc
        parts: list[str] = []

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    parts.append(str(key))
                    _walk(value)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)
            elif isinstance(node, str):
                parts.append(node)

        _walk(doc)
        return "\n".join(parts)
    return text


def spans_for_strings(text: str, needles: list[str] | tuple[str, ...]) -> tuple[RedactionSpan, ...]:
    """Resolve literal strings to spans over ``text`` — every occurrence.

    A redaction proposal scopes *what* to remove by the literal the reviewer
    saw; the record then carries the resolved offsets + the removed text's
    digest. A literal not present, or an empty literal, is refused — the
    proposal must name real, extant text.
    """
    spans: list[RedactionSpan] = []
    for needle in needles:
        if not needle:
            raise RedactionError("a redaction literal must be non-empty")
        at = text.find(needle)
        if at < 0:
            raise RedactionError(
                "a redaction literal is not present in the capture's text — the "
                "scope must name extant content"
            )
        while at >= 0:
            end = at + len(needle)
            spans.append(
                RedactionSpan(start=at, end=end, sha256=sha256(text[at:end].encode()).hexdigest())
            )
            at = text.find(needle, end)
    spans.sort(key=lambda s: s.start)
    return tuple(spans)


def apply_spans(
    text: str, spans: tuple[RedactionSpan, ...] | list[RedactionSpan]
) -> tuple[str, tuple[str, ...]]:
    """Physically substitute each span with :data:`REDACTION_MARKER`.

    Returns ``(derivative_text, removed_sha256)`` — one digest per span, in
    span order. The removed characters are gone from the derivative; the record
    carries only their digests, never the text.
    """
    ordered = sorted(spans, key=lambda s: s.start)
    if not ordered:
        raise RedactionError("a redaction must remove at least one span")
    cursor = 0
    removed: list[str] = []
    out: list[str] = []
    for span in ordered:
        if span.start < cursor:
            raise RedactionError("redaction spans overlap")
        if span.start < 0 or span.end <= span.start or span.end > len(text):
            raise RedactionError(
                f"redaction span [{span.start}:{span.end}] is outside the document"
            )
        removed_text = text[span.start : span.end]
        # If the review recorded the removed text's digest, it binds exactly —
        # a scope naming different bytes than the ones removed fails loudly.
        if span.sha256 and sha256(removed_text.encode()).hexdigest() != span.sha256:
            raise RedactionError(
                f"span [{span.start}:{span.end}] removes different bytes than the "
                "reviewed scope records"
            )
        out.append(text[cursor : span.start])
        out.append(REDACTION_MARKER)
        removed.append(sha256(removed_text.encode()).hexdigest())
        cursor = span.end
    out.append(text[cursor:])
    return "".join(out), tuple(removed)


def redact(
    parent_capture_id: str,
    redacted_bytes: bytes,
    *,
    method: str,
    version: str,
) -> RedactedCapture:
    """Build a redacted derivative capture (SIG-EVID-011).

    ``method`` and ``version`` are required — a redaction with no recorded method
    cannot be audited or re-done, so it is rejected.
    """
    if not method or not version:
        raise ValueError("redaction method and version are required (SIG-EVID-011)")
    return RedactedCapture(
        parent_capture_id=parent_capture_id,
        redaction_method=method,
        redaction_version=version,
        content_digest=multihash(redacted_bytes),
        byte_size=len(redacted_bytes),
    )


def apply_redaction(
    *,
    parent_capture_id: str,
    parent_content_digest: str,
    media_type: str,
    parent_bytes: bytes,
    spans: tuple[RedactionSpan, ...] | list[RedactionSpan],
    method: str,
    version: str,
    review: RedactionReview | None,
) -> RedactionOutcome:
    """The wired redaction step (SIG-PUB-015/016).

    Produces the derivative bytes for one reviewed redaction: the approved spans
    are physically removed from the text layer, the removal is proven absent by
    extraction, and the :class:`RedactedCapture` row is built via
    :func:`redact` (the derivative itself is written by the caller as a NEW OCFL
    object — the parent's bytes are write-once, SIG-EPIS-006).

    ``review`` is the recorded human review — required, never optional: a
    redaction attempted without one is a pipeline error
    (:class:`RedactionReviewRequired`), and the record must bind the *same*
    parent, method, version and spans the pipeline is asked to apply — the
    review approves a scope, not a blank cheque. The pipeline never approves
    anything itself.
    """
    if review is None:
        raise RedactionReviewRequired(
            "a redaction requires a recorded human review (reviewer role + "
            "timestamp on the append-only review record) — absent, the pipeline "
            "refuses (SIG-PUB-015)"
        )
    review.validate()
    if review.parent_capture_id != parent_capture_id:
        raise RedactionError(
            "the recorded review names a different parent capture — the approval "
            "does not cover this redaction"
        )
    if review.method != method or review.version != version:
        raise RedactionError(
            "the recorded review names a different method/version — re-review the "
            "scope under the method being applied"
        )
    if review.spans and tuple(sorted(review.spans, key=lambda s: s.start)) != tuple(
        sorted(spans, key=lambda s: s.start)
    ):
        raise RedactionError(
            "the recorded review approves a different span set — the applied scope "
            "must equal the reviewed scope"
        )

    text = decode_document(parent_bytes, media_type)
    derivative_text, removed_digests = apply_spans(text, spans)
    derivative_bytes = derivative_text.encode("utf-8")

    # SIG-PUB-016 self-check: the removed text must be unrecoverable from the
    # derivative — absent from the raw bytes AND from the extracted text layer.
    extracted = extract_text(derivative_bytes, media_type)
    for span in sorted(spans, key=lambda s: s.start):
        removed = text[span.start : span.end]
        if removed.encode() in derivative_bytes or removed in derivative_text:
            raise RedactionError("the derivative still carries a redacted span")
        if removed in extracted:
            raise RedactionError(
                "the redacted text is still recoverable from the derivative's "
                "text layer (SIG-PUB-016)"
            )

    # The derivative must remain a well-formed document of its media type — a
    # substitution that corrupts the container is a pipeline error.
    extract_text(derivative_bytes, media_type)

    capture = redact(parent_capture_id, derivative_bytes, method=method, version=version)
    record: dict[str, Any] = {
        "schema": REVIEW_SCHEMA,
        "parent_capture_id": parent_capture_id,
        "parent_content_digest": parent_content_digest,
        "derivative_content_digest": capture.content_digest,
        "redaction_method": method,
        "redaction_version": version,
        "marker": REDACTION_MARKER,
        "spans": [
            {
                "start": s.start,
                "end": s.end,
                "removed_sha256": d,
            }
            for s, d in zip(sorted(spans, key=lambda s: s.start), removed_digests, strict=True)
        ],
        "review": {
            "item_id": review.item_id,
            "decision": review.decision,
            "reviewer_role": review.reviewer_role,
            "decided_at": review.decided_at,
        },
    }
    return RedactionOutcome(
        derivative_bytes=derivative_bytes,
        capture=capture,
        review=review,
        record=record,
    )
