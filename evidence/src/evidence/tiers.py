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

from .redaction import REDACTION_MARKER, RedactionDerivative


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
    retrieved_at: str  # full ISO-8601 UTC (S-10 — never a date-only string)
    content_digest: str  # multihash (SIG-EVID-002)
    media_type: str
    tier: StorageTier
    claims_supported: tuple[str, ...] = field(default_factory=tuple)
    #: P35.31 (F-400): the basis the served ``tier`` was produced on —
    #: ``recorded`` (the row's stored tier stands), ``derived_at_read`` (the
    #: read path's lane+class floor tightened a pre-fix constant-tier row) or
    #: ``seal_register`` (a protective-seal disposition forced the sealed
    #: representation). The label is emitted so a tightened row names its basis.
    tier_basis: str = "recorded"
    #: The row's recorded tier, populated only when it differs from the served
    #: ``tier`` — the honest record that the served value was tightened.
    recorded_tier: str | None = None
    title: str | None = None
    excerpt: str | None = None
    byte_size: int | None = None
    #: P32.2's byte-bearing marker (``actual`` | ``synthetic`` | ``legacy``):
    #: only an ``actual`` capture has bytes stored in an OCFL object — a
    #: ``synthetic`` one is a run record that never carried bytes. ``None``
    #: = unknown (a meta built without the classification — treated as
    #: "not proven byte-bearing" by :func:`bytes_available`).
    capture_classification: str | None = None
    #: P34.49 (ADR-185): the F-406/I7/PUB-002 class ids this capture is
    #: protectively sealed under — recorded on the restricted surface so an
    #: authorized review sees *why*; the public rep stays the four sealed
    #: fields (SIG-EVID-010) and never carries them.
    seal_rules: tuple[str, ...] = ()
    #: P36.15 (SIG-PUB-015/016): the redaction derivative once one exists —
    #: populated by the store's read path (the child row with
    #: ``parent_capture_id = capture_id``). Every excerpt surface serves the
    #: derivative, never the parent's raw bytes, where one exists.
    derivative: RedactionDerivative | None = None


def bytes_available(meta: CaptureMetadata) -> bool:
    """Are this capture's bytes actually in the public archive? (P34.25)

    ``bytes_available`` may be claimed only where bytes are public: the
    capture's storage tier is ``public`` AND the capture is recorded as
    byte-bearing (``capture_classification == 'actual'``). A public-tier
    ``synthetic`` run record or a ``legacy``/unclassified row that cannot
    prove stored bytes does not claim availability.
    """
    return meta.tier.bytes_are_public and meta.capture_classification == "actual"


def bytes_unavailable_reason(meta: CaptureMetadata) -> str | None:
    """The safe machine-readable reason :func:`bytes_available` is False.

    ``tier:<value>`` when the storage tier withholds the bytes;
    ``classification:<value>`` when the capture is not proven byte-bearing
    (``synthetic``, ``legacy``, or unclassified). ``None`` when the bytes
    are public.
    """
    if bytes_available(meta):
        return None
    if not meta.tier.bytes_are_public:
        return f"tier:{meta.tier.value}"
    return f"classification:{meta.capture_classification or 'unclassified'}"


def publishable_excerpt(meta: CaptureMetadata) -> str | None:
    """The excerpt any public surface may serve for this capture (SIG-PUB-016).

    * A ``restricted`` capture serves the literal ``[redacted]``.
    * A ``public`` capture with a redaction derivative serves the
      **derivative's** excerpt — the parent's raw excerpt is withheld, never
      served, once a reviewed derivative exists (P36.15). Where the derivative
      carries no recorded excerpt, ``None`` is served (fail-closed — the raw
      excerpt does not leak back in).
    * Otherwise the capture's own excerpt.
    """
    if meta.tier is StorageTier.RESTRICTED:
        return REDACTION_MARKER
    if meta.tier is StorageTier.SEALED:
        return None
    if meta.derivative is not None:
        return meta.derivative.excerpt
    return meta.excerpt


def public_representation(meta: CaptureMetadata) -> dict[str, object]:
    """What may be published for a capture, by tier (SIG-EVID-009/010).

    * ``public``    — full metadata + excerpt; bytes are at a public URL.
    * ``restricted``— full metadata, **redacted excerpt**, **no upstream URI**;
      bytes access-controlled.
    * ``sealed``    — **metadata only**: existence, source, date, digest, claims;
      no excerpt, no title body, no upstream URI, and the bytes are never
      exposed.

    ``source_uri`` is served only for the ``public`` tier (P35.31 / F-400,
    SIG-TRANSP-020): the upstream URL of a restricted or sealed capture is not
    itself a public fact — the field is absent from their representations,
    not nulled.

    ``tier_basis`` labels how the served tier was produced — ``recorded``,
    ``derived_at_read`` (the read path's lane+class floor tightened a pre-fix
    constant-tier row) or ``seal_register`` (a protective-seal disposition) —
    and ``recorded_tier`` carries the stored value when it differs.

    The excerpt is :func:`publishable_excerpt` (SIG-PUB-015/016, P36.15): where a
    redaction derivative exists its own recorded excerpt is served and the
    parent's raw excerpt never reaches a public surface; the representation
    names the derivative (its capture id + digest + method/version) so a
    consumer can always resolve which bytes stand behind the excerpt.

    ``bytes_available`` is honest (P34.25): only a public-tier capture
    proven byte-bearing (``capture_classification == 'actual'``) claims it.
    """
    base: dict[str, object] = {
        "capture_id": meta.capture_id,
        "source_id": meta.source_id,
        "retrieved_at": meta.retrieved_at,
        "content_digest": meta.content_digest,
        "media_type": meta.media_type,
        "tier": meta.tier.value,
        "tier_basis": meta.tier_basis,
        "claims_supported": list(meta.claims_supported),
        "bytes_available": bytes_available(meta),
    }
    if meta.recorded_tier is not None:
        base["recorded_tier"] = meta.recorded_tier
    if meta.tier is StorageTier.PUBLIC:
        base["source_uri"] = meta.source_uri
    if meta.tier is StorageTier.SEALED:
        # Existence, source, date, digest, claims supported — and nothing else.
        base["exists"] = True
        return base
    base["title"] = meta.title
    base["byte_size"] = meta.byte_size
    base["excerpt"] = publishable_excerpt(meta)
    if meta.derivative is not None:
        base["redaction_derivative"] = meta.derivative.to_row()
    return base


# The metadata fields a sealed capture is permitted to expose publicly. Used by
# tests and callers to assert nothing sensitive leaks (SIG-EVID-010).
SEALED_PUBLIC_FIELDS: frozenset[str] = frozenset(
    {
        "capture_id",
        "source_id",
        "retrieved_at",
        "content_digest",
        "media_type",
        "tier",
        "tier_basis",
        "recorded_tier",
        "claims_supported",
        "bytes_available",
        "exists",
    }
)
