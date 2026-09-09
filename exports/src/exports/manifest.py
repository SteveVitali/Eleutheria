# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The release manifest and versioning contract for bulk exports (§38.1).

P14.2 **owns** this contract; the Phase-15 download surfaces reference it, and the
Zenodo deposit (§38.2) deposits it. Two invariants live here rather than in prose:

* **A release is a pure function of its inputs (SIG-EXPORT-003).** A bulk export is
  reproducible from ``(as_of pair + ruleset version + resolver version)`` — the four
  values of :class:`BuildSpec`. The :meth:`BuildSpec.release_id` is derived
  deterministically from exactly those inputs, so "a hand-built export is a different
  dataset wearing the same name" (§38.1) is structurally impossible: two builds from
  the same :class:`BuildSpec` produce the same release id and byte-identical artifacts.
* **Every artifact carries a checksum (SIG-EXPORT-001).** The manifest lists each
  artifact with its SHA-256, byte size, media type, and — crucially for the licence
  model — its compartment and computed licence, so a consumer can verify integrity and
  know the governing licence of every file without opening it.

The **concept id** is stable across every release of the dataset (it maps to the
Zenodo *concept DOI*, §38.2); the **release id** identifies one versioned release (the
Zenodo *version DOI*). That concept/version split is the whole point of the Zenodo
deposit: cite the dataset once, pin a run forever.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date

#: The canonical JSON encoding for every manifest/descriptor artifact SIG writes:
#: sorted keys, compact separators, a trailing newline. Byte-stable across runs and
#: platforms, so a release artifact is diffable and its digest is reproducible.
_JSON_KW: dict[str, object] = {"sort_keys": True, "separators": (",", ":"), "ensure_ascii": False}


def canonical_json(obj: object) -> bytes:
    """Serialise ``obj`` to the canonical, byte-stable JSON encoding (UTF-8, newline)."""
    return (json.dumps(obj, **_JSON_KW) + "\n").encode("utf-8")  # type: ignore[arg-type]


def sha256_hex(data: bytes) -> str:
    """The SHA-256 hex digest of ``data`` (SIG-EXPORT-001 checksums)."""
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class BuildSpec:
    """The reproducibility inputs of one bulk-export release (SIG-EXPORT-003).

    Exactly the four values §38.1 names: the two-axis as-of cut (observation-time
    snapshot + assertion-time belief), the ruleset version, and the resolver version.
    Everything derived from a :class:`BuildSpec` — the release id, the artifact bytes,
    the manifest — is a deterministic function of these, so the same spec always names
    and produces the same release.
    """

    #: Observation-time cut, the T4 snapshot axis (§37.2 ``as_of_snapshot``).
    as_of_snapshot: date
    #: Assertion-time cut, the belief axis (§37.2 ``as_of_belief``).
    as_of_belief: date
    #: The reconciliation ruleset version the resolver ran under (SIG-RECON-*).
    ruleset_version: str
    #: The resolver code version (SIG-EXPORT-003 names it distinctly from the ruleset).
    resolver_version: str
    #: Stable dataset slug; the concept-level identity, constant across releases.
    dataset_slug: str = "sig"

    def __post_init__(self) -> None:
        if not self.ruleset_version:
            raise ValueError("BuildSpec requires a ruleset_version (SIG-EXPORT-003)")
        if not self.resolver_version:
            raise ValueError("BuildSpec requires a resolver_version (SIG-EXPORT-003)")
        if not self.dataset_slug:
            raise ValueError("BuildSpec requires a dataset_slug")

    def reproducibility_inputs(self) -> dict[str, str]:
        """The `(as_of pair + ruleset + resolver)` tuple, as stable strings."""
        return {
            "as_of_snapshot": self.as_of_snapshot.isoformat(),
            "as_of_belief": self.as_of_belief.isoformat(),
            "ruleset_version": self.ruleset_version,
            "resolver_version": self.resolver_version,
        }

    def content_key(self) -> str:
        """The deterministic digest of the reproducibility inputs.

        Two :class:`BuildSpec`s produce the same key iff they would produce the same
        dataset. It is the version fingerprint that makes a hand-built export
        detectable as a different dataset (§38.1).
        """
        return sha256_hex(canonical_json(self.reproducibility_inputs()))

    def concept_id(self) -> str:
        """The dataset-level identity, stable across releases (Zenodo concept DOI)."""
        return self.dataset_slug

    def release_id(self) -> str:
        """The versioned release identity (Zenodo version DOI).

        Derived from the dataset slug, the observation-time snapshot (the release
        period), and a short content fingerprint — so the id both reads meaningfully
        (``sig-2026-06-30-1a2b3c4d``) and changes iff any reproducibility input changes.
        """
        return f"{self.dataset_slug}-{self.as_of_snapshot.isoformat()}-{self.content_key()[:8]}"


@dataclass(frozen=True)
class Artifact:
    """One published artifact, with the integrity + licence facts a consumer needs.

    ``compartment`` and ``license`` are load-bearing, not decoration: a bulk consumer
    must be able to tell the ODbL file from the CC-BY file without opening either
    (SIG-EXPORT-005), and the checksum lets them verify the download (SIG-EXPORT-001).
    """

    name: str
    path: str
    media_type: str
    compartment: str
    license: str
    sha256: str
    byte_size: int
    row_count: int | None = None

    @classmethod
    def of(
        cls,
        *,
        name: str,
        path: str,
        media_type: str,
        compartment: str,
        license: str,
        data: bytes,
        row_count: int | None = None,
    ) -> Artifact:
        """Build an artifact record from its bytes, computing size + checksum."""
        return cls(
            name=name,
            path=path,
            media_type=media_type,
            compartment=compartment,
            license=license,
            sha256=sha256_hex(data),
            byte_size=len(data),
            row_count=row_count,
        )

    def as_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "media_type": self.media_type,
            "compartment": self.compartment,
            "license": self.license,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "row_count": self.row_count,
        }


@dataclass(frozen=True)
class Manifest:
    """The release manifest: the build spec plus every artifact's integrity record."""

    build_spec: BuildSpec
    artifacts: tuple[Artifact, ...] = field(default_factory=tuple)

    def _sorted(self) -> list[Artifact]:
        # Sort by path so the manifest (and its digest) is order-independent.
        return sorted(self.artifacts, key=lambda a: a.path)

    def as_json(self) -> dict[str, object]:
        return {
            "concept_id": self.build_spec.concept_id(),
            "release_id": self.build_spec.release_id(),
            "reproducibility_inputs": self.build_spec.reproducibility_inputs(),
            "content_key": self.build_spec.content_key(),
            "artifacts": [a.as_json() for a in self._sorted()],
        }

    def to_bytes(self) -> bytes:
        """The canonical, byte-stable manifest document (SIG-EXPORT-001)."""
        return canonical_json(self.as_json())

    def digest_manifest(self) -> dict[str, str]:
        """The ``path -> sha256`` map deposited to Zenodo in place of evidence bytes.

        Evidence bytes are excluded from the Zenodo deposit by size (§38.2); the
        manifest of digests is deposited instead, so a citation still pins exactly
        which bytes the release comprised.
        """
        return {a.path: a.sha256 for a in self._sorted()}

    def licenses(self) -> set[str]:
        """The distinct licences present across the release's artifacts."""
        return {a.license for a in self.artifacts}


__all__ = [
    "BuildSpec",
    "Artifact",
    "Manifest",
    "canonical_json",
    "sha256_hex",
]
