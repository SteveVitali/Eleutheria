# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Redaction as a new capture (SIG-EVID-011) + the wired pipeline (P36.15)."""

from __future__ import annotations

import json
from hashlib import sha256

import pytest
from evidence.digest import multihash
from evidence.redaction import (
    RedactionError,
    RedactionReview,
    RedactionReviewRequired,
    RedactionSpan,
    apply_redaction,
    extract_text,
    redact,
    spans_for_strings,
)


def test_redaction_is_a_new_capture_pointing_at_the_parent() -> None:
    redacted = redact("parent-cap", b"redacted bytes", method="blackbox", version="2.1")
    row = redacted.to_row()
    assert row["parent_capture_id"] == "parent-cap"
    assert row["redaction_applied"] is True
    assert row["redaction_method"] == "blackbox"
    assert row["redaction_version"] == "2.1"
    # The derivative has its own digest; the original bytes are never edited.
    assert row["content_digest"] == multihash(b"redacted bytes")
    assert row["content_digest"] != multihash(b"original unredacted bytes")


def test_redaction_requires_method_and_version() -> None:
    with pytest.raises(ValueError):
        redact("parent-cap", b"x", method="", version="1")
    with pytest.raises(ValueError):
        redact("parent-cap", b"x", method="blackbox", version="")


# --- P36.15: the wired pipeline (SIG-PUB-015/016) -----------------------------

DOC = (
    "The council approved the contract. Officer Jane M. Doe signed for the city. "
    "Total: $1.2M over 36 months."
)


def _review(**kw: object) -> RedactionReview:
    """A synthetic recorded review — a fixture decision, never a real human act."""
    base: dict[str, object] = {
        "item_id": "redaction:cap-1:abc123",
        "decision": "accept",
        "reviewer_role": "records officer",
        "decided_at": "2026-10-14T00:00:00+00:00",
        "parent_capture_id": "cap-1",
        "method": "text-layer-substitution",
        "version": "1",
    }
    base.update(kw)
    return RedactionReview(**base)  # type: ignore[arg-type]


def _spans(text: str, needle: str) -> tuple[RedactionSpan, ...]:
    return spans_for_strings(text, [needle])


def test_apply_redaction_physically_removes_the_spans() -> None:
    """SIG-PUB-016: the redacted strings are absent from the derivative's
    bytes AND its extracted text layer — not overlaid, gone."""
    outcome = apply_redaction(
        parent_capture_id="cap-1",
        parent_content_digest=multihash(DOC.encode()),
        media_type="text/plain",
        parent_bytes=DOC.encode(),
        spans=_spans(DOC, "Jane M. Doe"),
        method="text-layer-substitution",
        version="1",
        review=_review(),
    )
    assert "Jane M. Doe" not in outcome.derivative_bytes.decode()
    assert "Jane M. Doe" not in extract_text(outcome.derivative_bytes, "text/plain")
    assert "[redacted]" in outcome.derivative_bytes.decode()
    # The derivative is a NEW capture, not an edit of the parent.
    assert outcome.capture.parent_capture_id == "cap-1"
    assert outcome.capture.redaction_applied is True
    assert outcome.capture.content_digest == multihash(outcome.derivative_bytes)
    assert outcome.capture.content_digest != multihash(DOC.encode())
    assert outcome.capture.redaction_method == "text-layer-substitution"


def test_apply_redaction_extracts_from_html_and_json() -> None:
    """The extraction proof covers the document containers we redact."""
    html_doc = "<html><body><p>Contact Officer J. Smith at ext. 41</p></body></html>"
    outcome = apply_redaction(
        parent_capture_id="cap-2",
        parent_content_digest=multihash(html_doc.encode()),
        media_type="text/html",
        parent_bytes=html_doc.encode(),
        spans=_spans(html_doc, "J. Smith"),
        method="text-layer-substitution",
        version="1",
        review=_review(parent_capture_id="cap-2"),
    )
    extracted = extract_text(outcome.derivative_bytes, "text/html")
    assert "J. Smith" not in extracted
    assert "<p>" in outcome.derivative_bytes.decode()  # markup survives
    json_doc = '{"officer": "Badge 4417", "unit": "patrol"}'
    outcome = apply_redaction(
        parent_capture_id="cap-3",
        parent_content_digest=multihash(json_doc.encode()),
        media_type="application/json",
        parent_bytes=json_doc.encode(),
        spans=_spans(json_doc, "Badge 4417"),
        method="text-layer-substitution",
        version="1",
        review=_review(parent_capture_id="cap-3"),
    )
    # The derivative remains well-formed JSON and the redacted text is absent.
    import json

    assert json.loads(outcome.derivative_bytes)["officer"] == "[redacted]"
    assert "Badge 4417" not in outcome.derivative_bytes.decode()


def test_apply_redaction_refuses_without_a_review() -> None:
    """SIG-PUB-015: a redaction attempted with no review fails loudly."""
    with pytest.raises(RedactionReviewRequired):
        apply_redaction(
            parent_capture_id="cap-1",
            parent_content_digest=multihash(DOC.encode()),
            media_type="text/plain",
            parent_bytes=DOC.encode(),
            spans=_spans(DOC, "Jane"),
            method="text-layer-substitution",
            version="1",
            review=None,
        )


def test_apply_redaction_refuses_a_rejected_review() -> None:
    with pytest.raises(RedactionReviewRequired):
        apply_redaction(
            parent_capture_id="cap-1",
            parent_content_digest=multihash(DOC.encode()),
            media_type="text/plain",
            parent_bytes=DOC.encode(),
            spans=_spans(DOC, "Jane"),
            method="text-layer-substitution",
            version="1",
            review=_review(decision="reject"),
        )


def test_review_records_a_role_never_a_personal_identifier() -> None:
    """Part VIII §0.7 / ADR-163: the review carries a role; an e-mail-shaped or
    handle-shaped reviewer is not a role and is refused."""
    with pytest.raises(RedactionReviewRequired):
        _review(reviewer_role="jane.doe@city.example").validate()
    with pytest.raises(RedactionReviewRequired):
        _review(reviewer_role="").validate()
    with pytest.raises(RedactionReviewRequired):
        _review(decided_at="").validate()
    _review(reviewer_role="records officer").validate()


def test_review_binds_the_scope_it_approved() -> None:
    """The applied scope must equal the reviewed scope — a review does not
    approve a different parent, method, version, or span set."""
    kwargs: dict[str, object] = {
        "parent_capture_id": "cap-1",
        "parent_content_digest": multihash(DOC.encode()),
        "media_type": "text/plain",
        "parent_bytes": DOC.encode(),
        "spans": _spans(DOC, "Jane M. Doe"),
        "method": "text-layer-substitution",
        "version": "1",
    }
    with pytest.raises(RedactionError):
        apply_redaction(**kwargs, review=_review(parent_capture_id="cap-other"))  # type: ignore[arg-type]
    with pytest.raises(RedactionError):
        apply_redaction(**kwargs, review=_review(version="2"))  # type: ignore[arg-type]
    with pytest.raises(RedactionError):
        apply_redaction(
            **kwargs,
            review=_review(spans=_spans(DOC, "Total")),  # type: ignore[arg-type]
        )


def test_the_review_record_carries_digests_never_the_removed_text() -> None:
    """The applied record is publishable-safe: it names what was redacted by
    offsets + digests + role + timestamps — the removed text appears nowhere."""
    outcome = apply_redaction(
        parent_capture_id="cap-1",
        parent_content_digest=multihash(DOC.encode()),
        media_type="text/plain",
        parent_bytes=DOC.encode(),
        spans=_spans(DOC, "Jane M. Doe"),
        method="text-layer-substitution",
        version="1",
        review=_review(),
    )
    record_json = json.dumps(outcome.record)
    assert "Jane M. Doe" not in record_json
    assert outcome.record["schema"] == "sig.redaction-review/1"
    assert outcome.record["review"]["reviewer_role"] == "records officer"
    assert outcome.record["review"]["decision"] == "accept"
    span = outcome.record["spans"][0]
    assert span["removed_sha256"] == sha256(b"Jane M. Doe").hexdigest()


def test_apply_redaction_refuses_binary_media_and_bad_spans() -> None:
    """A container with no provably-redactable text layer is refused, not
    fake-redacted; so is an empty/overlapping/out-of-range scope."""
    with pytest.raises(RedactionError):
        apply_redaction(
            parent_capture_id="cap-1",
            parent_content_digest="x",
            media_type="application/pdf",
            parent_bytes=b"%PDF-1.4 ...",
            spans=[RedactionSpan(0, 4)],
            method="m",
            version="1",
            review=_review(),
        )
    base: dict[str, object] = {
        "parent_capture_id": "cap-1",
        "parent_content_digest": multihash(DOC.encode()),
        "media_type": "text/plain",
        "parent_bytes": DOC.encode(),
        "method": "text-layer-substitution",
        "version": "1",
        "review": _review(),
    }
    with pytest.raises(RedactionError):
        apply_redaction(**{**base, "spans": []})  # type: ignore[arg-type]
    with pytest.raises(RedactionError):
        apply_redaction(
            **{**base, "spans": [RedactionSpan(0, 10), RedactionSpan(5, 12)]}  # type: ignore[arg-type]
        )
    with pytest.raises(RedactionError):
        apply_redaction(**{**base, "spans": [RedactionSpan(5, len(DOC) + 1)]})  # type: ignore[arg-type]


def test_a_reviewed_scope_binds_the_exact_removed_bytes() -> None:
    """A span carrying the wrong removed-digest fails loudly — the review
    approved specific bytes, not whatever happens to sit at the offsets."""
    text = DOC
    span = RedactionSpan(start=text.index("Jane"), end=text.index("Jane") + 4, sha256="0" * 64)
    with pytest.raises(RedactionError):
        apply_redaction(
            parent_capture_id="cap-1",
            parent_content_digest=multihash(text.encode()),
            media_type="text/plain",
            parent_bytes=text.encode(),
            spans=[span],
            method="text-layer-substitution",
            version="1",
            review=_review(),
        )


def test_spans_for_strings_resolves_every_occurrence() -> None:
    spans = spans_for_strings("a Jane and a Jane", ["Jane"])
    assert [(s.start, s.end) for s in spans] == [(2, 6), (13, 17)]
    with pytest.raises(RedactionError):
        spans_for_strings("nothing here", ["Jane"])
    with pytest.raises(RedactionError):
        spans_for_strings("x", [""])
