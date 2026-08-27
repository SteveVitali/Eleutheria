# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Storage tiers + the sealed metadata-only representation (SIG-EVID-009/010)."""

from __future__ import annotations

from evidence.tiers import (
    SEALED_PUBLIC_FIELDS,
    CaptureMetadata,
    StorageTier,
    public_representation,
)


def _meta(tier: StorageTier) -> CaptureMetadata:
    return CaptureMetadata(
        capture_id="cap-1",
        source_id="portal",
        source_uri="urn:sig:source:portal:x",
        retrieved_at="2026-05-01T00:00:00Z",
        content_digest="bxyz",
        media_type="application/pdf",
        tier=tier,
        claims_supported=("claim-1", "claim-2"),
        title="The contract",
        excerpt="secret body text",
        byte_size=1234,
    )


def test_sealed_exposes_metadata_only() -> None:
    """SIG-EVID-010: existence, source, date, digest, claims — and nothing else."""
    rep = public_representation(_meta(StorageTier.SEALED))
    assert set(rep) <= SEALED_PUBLIC_FIELDS
    assert rep["exists"] is True
    assert rep["content_digest"] == "bxyz"
    assert rep["claims_supported"] == ["claim-1", "claim-2"]
    assert rep["bytes_available"] is False
    # The sensitive body never appears.
    assert "excerpt" not in rep
    assert "title" not in rep
    assert "secret body text" not in repr(rep)


def test_restricted_redacts_the_excerpt_but_keeps_metadata() -> None:
    rep = public_representation(_meta(StorageTier.RESTRICTED))
    assert rep["excerpt"] == "[redacted]"
    assert rep["title"] == "The contract"
    assert rep["bytes_available"] is False


def test_public_exposes_full_metadata_and_excerpt() -> None:
    rep = public_representation(_meta(StorageTier.PUBLIC))
    assert rep["excerpt"] == "secret body text"
    assert rep["bytes_available"] is True


def test_audited_tiers() -> None:
    assert not StorageTier.PUBLIC.bytes_are_audited
    assert StorageTier.RESTRICTED.bytes_are_audited
    assert StorageTier.SEALED.bytes_are_audited
