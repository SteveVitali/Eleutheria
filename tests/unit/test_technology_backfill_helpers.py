# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.15b — pure helpers of the technology backfill (no Postgres needed).

The PG-side plan/apply is asserted in ``tests/db/test_technology_backfill.py``;
this file pins the deterministic pieces the fixture suite relies on:

* ``parse_subject`` splits ``traffic_camera:<src>:<tgt>:<ref>`` exactly on its
  first three colons — refs may carry colons — and refuses malformed keys;
* ``CaptureRow.bindable_for`` admits only byte-bearing actual occurrences that
  can be rebound verbatim (multihash digest, locator, source match);
* ``PlannedSubject.claim_record`` emits the honest ``sig.assertion/1`` shape —
  declared slug verbatim, backfill provenance, derived-from citations — and
  digests deterministically.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from db.claim_sink import content_digest
from db.technology_backfill import (
    CONNECTOR_NAME,
    EXTRACTION_METHOD,
    RATIONALE,
    CaptureRow,
    PlannedSubject,
    parse_subject,
)

_T = datetime(2026, 5, 1, tzinfo=UTC)


def _real_multihash() -> str:
    from evidence.digest import multihash

    return multihash(b"fixture-bytes")


def test_parse_subject_round_trips_colon_bearing_refs() -> None:
    assert parse_subject("traffic_camera:src:tgt:cam-1") == ("src", "tgt", "cam-1")
    assert parse_subject("traffic_camera:src:tgt:a:b:c") == ("src", "tgt", "a:b:c")


@pytest.mark.parametrize(
    "value",
    [
        "traffic_camera:src:tgt",  # missing ref
        "traffic_camera:src::ref",  # empty target
        "traffic_camera::tgt:ref",  # empty source
        "traffic_camera:src:tgt:",  # empty ref
        "other:src:tgt:ref",  # wrong family
        "traffic_camera:",
    ],
)
def test_parse_subject_refuses_malformed_keys(value: str) -> None:
    assert parse_subject(value) is None


def _cap(**kw: object) -> CaptureRow:
    base = {
        "capture_id": "cap-1",
        "retrieved_at": _T,
        "content_digest": _real_multihash(),
        "byte_size": 42,
        "media_type": "application/json",
        "ocfl_object_id": "sig:capture:x",
        "ocfl_version": "v1",
        "retrieved_by_run_id": "run-1",
        "classification": "actual",
        "stable_locator": "https://example.test/layer",
        "artifact_source_id": "src_a",
    }
    base.update(kw)
    return CaptureRow(**base)  # type: ignore[arg-type]


def test_bindable_requires_actual_multihash_and_source_match() -> None:
    assert _cap().bindable_for("src_a")
    # A synthetic per-run capture is never rebound.
    assert not _cap(classification="synthetic").bindable_for("src_a")
    # A non-multihash (hex) digest cannot be verified.
    assert not _cap(content_digest="f" * 64).bindable_for("src_a")
    # An artifact under a different source would mint, not resolve.
    assert not _cap(artifact_source_id="src_b").bindable_for("src_a")
    assert not _cap(stable_locator=None).bindable_for("src_a")
    assert not _cap(retrieved_at=None).bindable_for("src_a")


def test_binding_carries_the_occurrence_verbatim() -> None:
    cap = _cap()
    binding = cap.binding()
    assert binding["digest"] == cap.content_digest
    assert binding["source_uri"] == cap.stable_locator
    assert binding["retrieved_at"] == _T
    assert binding["ocfl_version"] == "v1"
    assert binding["original_run_id"] == "run-1"


def _subject(**kw: object) -> PlannedSubject:
    base = {
        "subject": "traffic_camera:src_a:tgt_alpr:cam-1",
        "entity_id": "ent-1",
        "source_id": "src_a",
        "target_id": "tgt_alpr",
        "slug": "alpr-fixed",
        "license_spdx": "CC0-1.0",
        "derived_from": ["b-claim", "a-claim"],
    }
    base.update(kw)
    return PlannedSubject(**base)  # type: ignore[arg-type]


def test_claim_record_is_the_honest_backfill_shape() -> None:
    record = _subject().claim_record()
    assert record["predicate_id"] == "technology"
    assert record["value"] == "alpr-fixed"  # declared slug verbatim
    assert record["raw_value"] == "alpr-fixed"
    assert record["record_kind"] == "claim"
    assert record["subject_id"] == "traffic_camera:src_a:tgt_alpr:cam-1"
    assert record["evidence_genre"] == "camera_registry"
    assert record["extraction_method"] == EXTRACTION_METHOD
    assert "P35.15b" in RATIONALE and "never" in RATIONALE
    assert record["assertion_rationale"] == RATIONALE
    assert record["derived_from_claim_ids"] == ["b-claim", "a-claim"]
    assert record["license"] == "CC0-1.0"
    assert record["source_id"] == "src_a"
    # The run identity — the backfill is labelled, never connector-fresh.
    assert CONNECTOR_NAME == "technology-backfill"


def test_claim_record_digest_is_deterministic_per_subject() -> None:
    a = _subject().claim_record()
    b = _subject().claim_record()
    assert content_digest(a) == content_digest(b)
    other = _subject(slug="fixed-camera-cctv").claim_record()
    assert content_digest(other) != content_digest(a)
    no_license = _subject(license_spdx=None).claim_record()
    assert "license" not in no_license
    assert content_digest(no_license) != content_digest(a)
