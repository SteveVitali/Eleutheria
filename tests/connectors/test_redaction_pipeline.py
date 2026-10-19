# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The wired redaction pipeline (P36.15; SIG-PUB-015/016, SIG-EVID-011).

These tests drive the **production path**: propose → recorded human review →
apply — over a real OCFL root and the review mechanism. The decisions recorded
here are synthetic fixture decisions (a reviewer *role* label, a fixed
timestamp) — they stand in for the human act the mechanism requires; nothing
here claims a real redaction decision was taken.
"""

from __future__ import annotations

import json

import pytest
from connectors.capture_ocfl import (
    REDACTION_LOGICAL_PATH,
    OcflCaptureStore,
)
from connectors.redaction_pipeline import (
    enqueue_proposal,
    propose_redaction,
    redaction_item_id,
    run_redaction,
)
from evidence.digest import multihash
from evidence.ocfl import OcflStore
from evidence.redaction import (
    RedactionError,
    RedactionReviewRequired,
    extract_text,
)
from evidence.storage import LocalFileStore
from resolution.review_queue import ACCEPT, REJECT, ReviewQueue

PARENT = (
    "Council minutes: contract approved. Signed by Officer Jane M. Doe, "
    "records witness. Attest: City Clerk."
)
PARENT_DIGEST = multihash(PARENT.encode())


@pytest.fixture()
def store(tmp_path):
    return OcflCaptureStore(OcflStore(LocalFileStore(str(tmp_path))))


@pytest.fixture()
def parent(store):
    return store.put(PARENT.encode(), media_type="text/plain", source_uri="urn:minutes:1")


def _propose(store, parent_ref):
    return propose_redaction(
        parent_capture_id="cap-parent-1",
        parent_digest=parent_ref.digest,
        parent_bytes=store.get(parent_ref.digest),
        media_type="text/plain",
        literals=["Jane M. Doe"],
        method="text-layer-substitution",
        version="1",
        scope_note="officer name, contract minutes",
    )


def test_propose_lands_a_redaction_review_item_with_digest_bound_scope(store, parent) -> None:
    queue = ReviewQueue()
    item = _propose(store, parent)
    assert item.kind == "redaction"
    assert item.item_id.startswith("redaction:cap-parent-1:")
    payload = item.payload
    assert payload["schema"] == "sig.redaction-review/1"
    assert payload["parent_capture_id"] == "cap-parent-1"
    assert payload["method"] == "text-layer-substitution"
    # The record binds the scope by digests, never carrying the removed text.
    assert "Jane M. Doe" not in json.dumps(payload)
    assert payload["spans"][0]["sha256"]
    assert enqueue_proposal(queue, item) is True
    # Idempotent replay: the identical proposal dedups.
    assert enqueue_proposal(queue, item) is False


def test_apply_without_a_recorded_review_refuses_loudly(store, parent) -> None:
    queue = ReviewQueue()
    item = _propose(store, parent)
    enqueue_proposal(queue, item)
    with pytest.raises(RedactionReviewRequired):
        run_redaction(store, queue, item_id=item.item_id)


def test_apply_with_a_reject_decision_refuses(store, parent) -> None:
    queue = ReviewQueue()
    item = _propose(store, parent)
    enqueue_proposal(queue, item)
    queue.decide(item.item_id, REJECT, reviewer="records officer")
    with pytest.raises(RedactionReviewRequired):
        run_redaction(store, queue, item_id=item.item_id)


def test_reviewed_redaction_writes_a_new_ocfl_object(store, parent, tmp_path) -> None:
    """End to end: proposal → recorded accept → derivative object + record."""
    queue = ReviewQueue()
    item = _propose(store, parent)
    enqueue_proposal(queue, item)
    queue.decide(item.item_id, ACCEPT, reviewer="records officer")

    result = run_redaction(store, queue, item_id=item.item_id)

    deriv = result.capture_ref
    deriv_bytes = store.get(deriv.digest)
    # The redacted text is physically absent — raw bytes AND extracted layer.
    assert b"Jane M. Doe" not in deriv_bytes
    assert "Jane M. Doe" not in extract_text(deriv_bytes, "text/plain")
    assert b"[redacted]" in deriv_bytes
    # A NEW object, content-addressed; the parent's object is untouched.
    assert deriv.ocfl_object_id != parent.ocfl_object_id
    assert store.get(parent.digest) == PARENT.encode()
    # The applied record rides the derivative object — reviewer role, not name.
    ocfl = OcflStore(LocalFileStore(str(tmp_path)))
    record = json.loads(
        ocfl.resolve(deriv.ocfl_object_id, deriv.ocfl_version, REDACTION_LOGICAL_PATH)
    )
    assert record["schema"] == "sig.redaction-review/1"
    assert record["review"]["reviewer_role"] == "records officer"
    assert record["review"]["decision"] == "accept"
    assert "Jane M. Doe" not in json.dumps(record)
    meta = json.loads(ocfl.resolve(deriv.ocfl_object_id, deriv.ocfl_version, "metadata.json"))
    assert meta["parent_capture_id"] == "cap-parent-1"
    assert meta["redaction"]["method"] == "text-layer-substitution"


def test_the_parent_capture_object_is_never_modified(store, parent, tmp_path) -> None:
    queue = ReviewQueue()
    item = _propose(store, parent)
    enqueue_proposal(queue, item)
    queue.decide(item.item_id, ACCEPT, reviewer="records officer")
    run_redaction(store, queue, item_id=item.item_id)
    # Parent bytes still resolve at their original version — append-only.
    assert store.get(parent.digest) == PARENT.encode()


def test_reredaction_is_a_new_derivative_with_a_new_review(store, parent) -> None:
    """A re-redaction (new scope) is a new proposal → new review → new OCFL
    object — never an edit of the first derivative (§45.2-compatible)."""
    queue = ReviewQueue()
    item1 = _propose(store, parent)
    enqueue_proposal(queue, item1)
    queue.decide(item1.item_id, ACCEPT, reviewer="records officer")
    first = run_redaction(store, queue, item_id=item1.item_id)

    item2 = propose_redaction(
        parent_capture_id="cap-parent-1",
        parent_digest=parent.digest,
        parent_bytes=store.get(parent.digest),
        media_type="text/plain",
        literals=["Jane M. Doe", "City Clerk"],
        method="text-layer-substitution",
        version="1.1",
        scope_note="re-redaction: also remove the clerk name",
    )
    assert item2.item_id != item1.item_id
    enqueue_proposal(queue, item2)
    queue.decide(item2.item_id, ACCEPT, reviewer="records officer")
    second = run_redaction(store, queue, item_id=item2.item_id)

    assert second.capture_ref.ocfl_object_id != first.capture_ref.ocfl_object_id
    deriv2 = store.get(second.capture_ref.digest)
    assert b"Jane M. Doe" not in deriv2 and b"City Clerk" not in deriv2
    # Both derivatives remain resolvable — append-only evidence.
    assert store.get(first.capture_ref.digest) != deriv2


def test_store_drift_between_review_and_apply_fails_closed(store, parent, tmp_path) -> None:
    """The bytes the human reviewed are the bytes redacted — a store whose
    parent bytes no longer match the recorded digest refuses."""
    queue = ReviewQueue()
    item = propose_redaction(
        parent_capture_id="cap-parent-1",
        parent_digest="sha256:" + "0" * 64,
        parent_bytes=store.get(parent.digest),
        media_type="text/plain",
        literals=["Jane M. Doe"],
        method="text-layer-substitution",
        version="1",
    )
    enqueue_proposal(queue, item)
    queue.decide(item.item_id, ACCEPT, reviewer="records officer")
    with pytest.raises(RedactionError):
        run_redaction(store, queue, item_id=item.item_id)


def test_redaction_item_id_is_deterministic_per_scope() -> None:
    from evidence.redaction import RedactionSpan

    a = redaction_item_id("cap-1", (RedactionSpan(2, 6),))
    b = redaction_item_id("cap-1", (RedactionSpan(2, 6),))
    c = redaction_item_id("cap-1", (RedactionSpan(2, 7),))
    assert a == b != c
