# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Storage tiers + the sealed metadata-only representation (SIG-EVID-009/010)."""

from __future__ import annotations

import dataclasses

from evidence.redaction import RedactionDerivative
from evidence.tiers import (
    SEALED_PUBLIC_FIELDS,
    CaptureMetadata,
    StorageTier,
    bytes_available,
    bytes_unavailable_reason,
    public_representation,
    publishable_excerpt,
)


def _meta(tier: StorageTier, *, classification: str | None = "actual") -> CaptureMetadata:
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
        capture_classification=classification,
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


# --- P35.31 (F-400): the upstream URI is a public-tier fact only ----------------


def test_source_uri_publishes_only_for_the_public_tier() -> None:
    """SIG-TRANSP-020: the upstream URL of a restricted or sealed capture is
    not itself a public fact — the field is ABSENT from their representations,
    not nulled."""
    public = public_representation(_meta(StorageTier.PUBLIC))
    assert public["source_uri"] == "urn:sig:source:portal:x"
    for tier in (StorageTier.RESTRICTED, StorageTier.SEALED):
        rep = public_representation(_meta(tier))
        assert "source_uri" not in rep, tier
        assert "urn:sig:source" not in repr(rep)


def test_every_representation_names_its_tier_basis() -> None:
    """A served tier labels how it was produced; a tightened row also names
    the stored value it tightened — never a silent upgrade."""
    rep = public_representation(_meta(StorageTier.RESTRICTED))
    assert rep["tier"] == "restricted" and rep["tier_basis"] == "recorded"
    assert "recorded_tier" not in rep
    tightened = dataclasses.replace(
        _meta(StorageTier.SEALED),
        tier_basis="derived_at_read",
        recorded_tier="public",
    )
    rep = public_representation(tightened)
    assert rep["tier"] == "sealed"
    assert rep["tier_basis"] == "derived_at_read"
    assert rep["recorded_tier"] == "public"
    assert set(rep) <= SEALED_PUBLIC_FIELDS  # the labels stay inside the allowlist


def test_bytes_available_only_where_bytes_are_public() -> None:
    """P34.25: bytes availability is claimed only for a public-tier capture
    proven byte-bearing ('actual'); every other combination is False with a
    safe machine-readable reason."""
    for cls in ("synthetic", "legacy", None):
        rep = public_representation(_meta(StorageTier.PUBLIC, classification=cls))
        assert rep["bytes_available"] is False, cls
        assert bytes_unavailable_reason(_meta(StorageTier.PUBLIC, classification=cls)) == (
            f"classification:{cls or 'unclassified'}"
        )
    for tier in (StorageTier.RESTRICTED, StorageTier.SEALED):
        meta = _meta(tier, classification="actual")
        assert public_representation(meta)["bytes_available"] is False
        assert bytes_unavailable_reason(meta) == f"tier:{tier.value}"
    meta = _meta(StorageTier.PUBLIC, classification="actual")
    assert bytes_available(meta) is True and bytes_unavailable_reason(meta) is None


def test_audited_tiers() -> None:
    assert not StorageTier.PUBLIC.bytes_are_audited
    assert StorageTier.RESTRICTED.bytes_are_audited
    assert StorageTier.SEALED.bytes_are_audited


# --- P36.15: derivative-sourced excerpts (SIG-PUB-015/016) --------------------


def _derivative() -> RedactionDerivative:
    return RedactionDerivative(
        capture_id="cap-1-redacted",
        content_digest="bderiv",
        method="text-layer-substitution",
        version="1",
        excerpt="the derivative's redacted excerpt",
    )


def test_public_with_derivative_serves_the_derivative_excerpt() -> None:
    """SIG-PUB-016: once a derivative exists the parent's raw excerpt never
    reaches a public representation — the derivative's own excerpt is served."""
    meta = dataclasses.replace(_meta(StorageTier.PUBLIC), derivative=_derivative())
    rep = public_representation(meta)
    assert rep["excerpt"] == "the derivative's redacted excerpt"
    assert "secret body text" not in repr(rep)
    assert rep["redaction_derivative"] == {
        "capture_id": "cap-1-redacted",
        "content_digest": "bderiv",
        "redaction_method": "text-layer-substitution",
        "redaction_version": "1",
    }
    assert publishable_excerpt(meta) == "the derivative's redacted excerpt"


def test_derivative_without_an_excerpt_fails_closed() -> None:
    """A derivative with no recorded excerpt serves ``None`` — the parent's
    raw excerpt does NOT leak back in (fail closed, SIG-PUB-016)."""
    deriv = RedactionDerivative(
        capture_id="cap-1-redacted",
        content_digest="bderiv",
        method="text-layer-substitution",
        version="1",
    )
    meta = dataclasses.replace(_meta(StorageTier.PUBLIC), derivative=deriv)
    assert publishable_excerpt(meta) is None
    assert "secret body text" not in repr(public_representation(meta))


def test_restricted_and_sealed_behaviour_survives_a_derivative() -> None:
    """The tier ladder still binds above the derivative rule."""
    deriv = _derivative()
    restricted = dataclasses.replace(_meta(StorageTier.RESTRICTED), derivative=deriv)
    assert public_representation(restricted)["excerpt"] == "[redacted]"
    sealed = dataclasses.replace(_meta(StorageTier.SEALED), derivative=deriv)
    rep = public_representation(sealed)
    assert set(rep) <= SEALED_PUBLIC_FIELDS
    assert "excerpt" not in rep
