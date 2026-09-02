# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Egress-friendly distribution of the bulk artifacts (§38.5, SIG-EXPORT-008/009).

**Egress pricing, not storage or compute, is the existential cost** for a bulk-data
project: a 2 GB export downloaded 5,000 times a month is 10 TB of egress — free on some
providers, a four-figure monthly bill on others. So the distribution *plan* is
first-class and its storage target must be **zero-or-low-egress** (SIG-EXPORT-008);
:func:`assert_low_egress` fails the build if a metered-egress provider is chosen, so the
mistake is caught at build time rather than on the first month's invoice.

For the **largest** artifacts, torrent and IPFS distribution SHOULD be offered
(SIG-EXPORT-009) — both to shed egress cost and for takedown resilience (§46.5). The
BitTorrent v2 magnet (``urn:btmh``) and the IPFS CIDv1 are derived deterministically
from the artifact's SHA-256, so they are stable content addresses a mirror can honour
without re-hashing the bytes.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass

from .manifest import Artifact, Manifest

#: Object-storage providers and their egress class. Zero/low egress is the whole point
#: of SIG-EXPORT-008; a metered provider is rejected. This is data, extend as needed.
EGRESS_CLASS: dict[str, str] = {
    "cloudflare-r2": "zero",
    "backblaze-b2": "low",
    "wasabi": "zero",
    "aws-s3": "metered",
    "gcs": "metered",
}

#: Artifacts at or above this size get torrent + IPFS references by default (SIG-EXPORT-009).
DEFAULT_LARGE_THRESHOLD_BYTES = 50_000_000


class EgressError(Exception):
    """Raised when the chosen storage target is not zero-or-low-egress (SIG-EXPORT-008)."""


@dataclass(frozen=True)
class ObjectStore:
    """An object-storage target for the bulk artifacts (S3-style)."""

    provider: str
    bucket: str

    @property
    def egress_class(self) -> str:
        return EGRESS_CLASS.get(self.provider, "unknown")


def assert_low_egress(store: ObjectStore) -> None:
    """Fail the build unless the storage target is zero-or-low-egress (SIG-EXPORT-008)."""
    if store.egress_class not in {"zero", "low"}:
        raise EgressError(
            f"object-store provider {store.provider!r} has egress class "
            f"{store.egress_class!r}; SIG-EXPORT-008 requires zero-or-low egress. "
            "Success is the failure mode: a metered provider turns popularity into a bill."
        )


def ipfs_cidv1_raw(sha256_hex_digest: str) -> str:
    """A deterministic IPFS CIDv1 (raw codec, sha2-256) for an artifact's digest.

    CIDv1 = multibase(base32) of ``<version 0x01><codec raw 0x55><multihash 0x12 0x20 …>``.
    A stable content address derived from the checksum SIG already publishes.
    """
    digest = bytes.fromhex(sha256_hex_digest)
    payload = bytes([0x01, 0x55, 0x12, 0x20]) + digest
    b32 = base64.b32encode(payload).decode("ascii").rstrip("=").lower()
    return "b" + b32


def torrent_magnet_v2(sha256_hex_digest: str, name: str) -> str:
    """A BitTorrent v2 magnet link (``urn:btmh``, sha2-256 multihash) for an artifact."""
    return f"magnet:?xt=urn:btmh:1220{sha256_hex_digest}&dn={name}"


@dataclass(frozen=True)
class ArtifactDistribution:
    """Where and how one artifact is served."""

    path: str
    primary_url: str
    cdn_url: str
    mirror_urls: tuple[str, ...] = ()
    ipfs_cid: str | None = None
    torrent_magnet: str | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "primary_url": self.primary_url,
            "cdn_url": self.cdn_url,
            "mirror_urls": list(self.mirror_urls),
            "ipfs_cid": self.ipfs_cid,
            "torrent_magnet": self.torrent_magnet,
        }


@dataclass(frozen=True)
class DistributionPlan:
    """The full distribution plan for a release."""

    store: ObjectStore
    artifacts: tuple[ArtifactDistribution, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "store": {
                "provider": self.store.provider,
                "bucket": self.store.bucket,
                "egress_class": self.store.egress_class,
            },
            "artifacts": [a.as_json() for a in self.artifacts],
        }

    def peer_distributed(self) -> tuple[ArtifactDistribution, ...]:
        """The artifacts offered over torrent/IPFS (SIG-EXPORT-009)."""
        return tuple(a for a in self.artifacts if a.ipfs_cid or a.torrent_magnet)


def plan_distribution(
    manifest: Manifest,
    *,
    store: ObjectStore,
    base_url: str,
    cdn_url: str,
    mirror_base_urls: Sequence[str] = (),
    large_threshold_bytes: int = DEFAULT_LARGE_THRESHOLD_BYTES,
) -> DistributionPlan:
    """Plan egress-friendly distribution for every artifact in ``manifest``.

    Validates the storage target is low-egress (SIG-EXPORT-008), routes every artifact
    through the CDN, and adds torrent + IPFS references for the largest artifacts
    (SIG-EXPORT-009). Deterministic: derived entirely from the manifest.
    """
    assert_low_egress(store)
    release = manifest.build_spec.release_id()
    dists: list[ArtifactDistribution] = []
    for artifact in sorted(manifest.artifacts, key=lambda a: a.path):
        rel = f"{release}/{artifact.path}"
        large = artifact.byte_size >= large_threshold_bytes
        dists.append(
            ArtifactDistribution(
                path=artifact.path,
                primary_url=f"{base_url.rstrip('/')}/{rel}",
                cdn_url=f"{cdn_url.rstrip('/')}/{rel}",
                mirror_urls=tuple(f"{m.rstrip('/')}/{rel}" for m in mirror_base_urls),
                ipfs_cid=ipfs_cidv1_raw(artifact.sha256) if large else None,
                torrent_magnet=torrent_magnet_v2(artifact.sha256, artifact.name) if large else None,
            )
        )
    return DistributionPlan(store=store, artifacts=tuple(dists))


def largest_artifact(artifacts: Sequence[Artifact]) -> Artifact | None:
    """The largest artifact by byte size (ties broken by path), or ``None`` if empty."""
    if not artifacts:
        return None
    return max(artifacts, key=lambda a: (a.byte_size, a.path))


__all__ = [
    "EGRESS_CLASS",
    "DEFAULT_LARGE_THRESHOLD_BYTES",
    "EgressError",
    "ObjectStore",
    "assert_low_egress",
    "ipfs_cidv1_raw",
    "torrent_magnet_v2",
    "ArtifactDistribution",
    "DistributionPlan",
    "plan_distribution",
    "largest_artifact",
]
