# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Storage tiers and the sealed-capture public representation (§17.5).

Every capture carries a :class:`StorageTier` (SIG-EVID-009). A ``sealed`` capture
still has a **metadata-only public representation** (SIG-EVID-010): its
existence, source, date, digest, and the claims it supports are public even when
its bytes are not. This is what lets SIG say "we hold the contract, here is its
hash, here is what it establishes" without publishing the unredacted bytes.

The functions here are pure: they compute what may be published for a capture at
a given tier. The *bytes* are gated separately, in the object store and by DB row
level security; access to ``restricted``/``sealed`` bytes is audited
(:mod:`evidence.access_log`, SIG-EVID-012).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StorageTier(StrEnum):
    """The three evidence storage tiers (SIG-EVID-009)."""

    PUBLIC = "public"
    RESTRICTED = "restricted"
    SEALED = "sealed"

    @property
    def bytes_are_public(self) -> bool:
        return self is StorageTier.PUBLIC

    @property
    def bytes_are_audited(self) -> bool:
        """restricted and sealed byte access MUST be logged (SIG-EVID-012)."""
        return self in (StorageTier.RESTRICTED, StorageTier.SEALED)


@dataclass(frozen=True)
class CaptureMetadata:
    """The full metadata SIG holds for a capture.

    ``tier`` decides which of these fields are publishable (see
    :func:`public_representation`).
    """

    capture_id: str
    source_id: str
    source_uri: str
    retrieved_at: str  # ISO-8601 (the capture date)
    content_digest: str  # multihash (SIG-EVID-002)
    media_type: str
    tier: StorageTier
    claims_supported: tuple[str, ...] = field(default_factory=tuple)
    title: str | None = None
    excerpt: str | None = None
    byte_size: int | None = None


def public_representation(meta: CaptureMetadata) -> dict[str, object]:
    """What may be published for a capture, by tier (SIG-EVID-009/010).

    * ``public``    — full metadata + excerpt; bytes are at a public URL.
    * ``restricted``— full metadata, **redacted excerpt**; bytes access-controlled.
    * ``sealed``    — **metadata only**: existence, source, date, digest, claims;
      no excerpt, no title body, and the bytes are never exposed.
    """
    base: dict[str, object] = {
        "capture_id": meta.capture_id,
        "source_id": meta.source_id,
        "source_uri": meta.source_uri,
        "retrieved_at": meta.retrieved_at,
        "content_digest": meta.content_digest,
        "media_type": meta.media_type,
        "tier": meta.tier.value,
        "claims_supported": list(meta.claims_supported),
        "bytes_available": meta.tier.bytes_are_public,
    }
    if meta.tier is StorageTier.SEALED:
        # Existence, source, date, digest, claims supported — and nothing else.
        base["exists"] = True
        return base
    base["title"] = meta.title
    base["byte_size"] = meta.byte_size
    base["excerpt"] = "[redacted]" if meta.tier is StorageTier.RESTRICTED else meta.excerpt
    return base


# The metadata fields a sealed capture is permitted to expose publicly. Used by
# tests and callers to assert nothing sensitive leaks (SIG-EVID-010).
SEALED_PUBLIC_FIELDS: frozenset[str] = frozenset(
    {
        "capture_id",
        "source_id",
        "source_uri",
        "retrieved_at",
        "content_digest",
        "media_type",
        "tier",
        "claims_supported",
        "bytes_available",
        "exists",
    }
)
