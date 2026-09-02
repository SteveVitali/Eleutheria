# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Zenodo quarterly-release deposit (§38.2, SIG-EXPORT-002).

Each quarterly release is deposited to Zenodo with **two DOIs**: a *concept DOI* that
cites the dataset across all its versions, and a *version DOI* that pins this one
release forever. That split is the whole point — an academic cites the concept DOI in a
paper and a reader can still fetch the exact bytes the analysis ran against via the
version DOI (the "Academic analysis" downstream class, §38.4).

**Evidence bytes are excluded by size** (§38.2): a full evidence corpus is far too large
to deposit, so the deposit carries the release artifacts plus the **manifest of
digests** — every evidence file's SHA-256 — instead. A citation therefore still pins
exactly which evidence the release comprised, without shipping terabytes.

The network is behind a :class:`ZenodoTransport` seam (mirroring the ``ReadStore`` seam
in the API): the deposit *policy* — what to include, the concept/version split, the
digest-manifest substitution — is decided and tested here against a deterministic
:class:`FakeZenodoTransport`; the real HTTP client is wired in production, never in a
test or an offline build.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from .manifest import Artifact, Manifest, canonical_json, sha256_hex

#: The path the release manifest is deposited under.
MANIFEST_PATH = "manifest.json"
#: The path the digest manifest (evidence-bytes stand-in) is deposited under.
DIGESTS_PATH = "digests.json"


@dataclass(frozen=True)
class DepositMetadata:
    """The bibliographic metadata a Zenodo deposition carries."""

    title: str
    version: str
    concept_id: str
    licenses: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "title": self.title,
            "version": self.version,
            "concept_id": self.concept_id,
            "licenses": list(self.licenses),
            "upload_type": "dataset",
        }


@dataclass(frozen=True)
class Deposition:
    """The result of a deposit: the two DOIs and the exact files deposited."""

    concept_doi: str
    version_doi: str
    files: tuple[str, ...]
    excluded_evidence: tuple[str, ...] = ()

    def as_json(self) -> dict[str, object]:
        return {
            "concept_doi": self.concept_doi,
            "version_doi": self.version_doi,
            "files": list(self.files),
            "excluded_evidence": list(self.excluded_evidence),
        }


class ZenodoTransport(Protocol):
    """The network seam. Returns the concept + version DOI for a deposited release."""

    def deposit(
        self,
        *,
        concept_id: str,
        version: str,
        files: Mapping[str, bytes],
        metadata: DepositMetadata,
    ) -> tuple[str, str]: ...


@dataclass
class FakeZenodoTransport:
    """A deterministic, offline transport for tests and dry-run builds.

    The concept DOI is a stable function of the ``concept_id`` (so every release of the
    dataset shares it); the version DOI is a function of the ``version`` (so each release
    gets its own). No network, no wall clock — the deposit is reproducible.
    """

    prefix: str = "10.5281/zenodo"
    calls: list[dict[str, object]] = field(default_factory=list)

    def _doi(self, key: str) -> str:
        return f"{self.prefix}.{int(sha256_hex(key.encode('utf-8'))[:12], 16)}"

    def deposit(
        self,
        *,
        concept_id: str,
        version: str,
        files: Mapping[str, bytes],
        metadata: DepositMetadata,
    ) -> tuple[str, str]:
        self.calls.append({"concept_id": concept_id, "version": version, "files": sorted(files)})
        return self._doi(concept_id), self._doi(f"{concept_id}@{version}")


def deposit_payload(
    manifest: Manifest,
    artifact_bytes: Mapping[str, bytes],
    *,
    evidence_paths: frozenset[str] = frozenset(),
) -> dict[str, bytes]:
    """The exact set of files deposited for a release (SIG-EXPORT-002).

    Every artifact's bytes EXCEPT evidence bytes (excluded by size), plus the release
    manifest and the digest manifest — so the deposit pins the release without shipping
    the evidence corpus.
    """
    files: dict[str, bytes] = {
        path: data for path, data in artifact_bytes.items() if path not in evidence_paths
    }
    files[MANIFEST_PATH] = manifest.to_bytes()
    files[DIGESTS_PATH] = canonical_json(manifest.digest_manifest())
    return files


def deposit_release(
    manifest: Manifest,
    artifact_bytes: Mapping[str, bytes],
    transport: ZenodoTransport,
    *,
    evidence_artifacts: tuple[Artifact, ...] = (),
) -> Deposition:
    """Deposit a quarterly release to Zenodo and return its concept + version DOIs.

    ``evidence_artifacts`` name the artifacts whose *bytes* are excluded by size; their
    digests still travel in the deposited digest manifest (§38.2).
    """
    evidence_paths = frozenset(a.path for a in evidence_artifacts)
    files = deposit_payload(manifest, artifact_bytes, evidence_paths=evidence_paths)
    metadata = DepositMetadata(
        title=f"SIG dataset release {manifest.build_spec.release_id()}",
        version=manifest.build_spec.release_id(),
        concept_id=manifest.build_spec.concept_id(),
        licenses=tuple(sorted(manifest.licenses())),
    )
    concept_doi, version_doi = transport.deposit(
        concept_id=manifest.build_spec.concept_id(),
        version=manifest.build_spec.release_id(),
        files=files,
        metadata=metadata,
    )
    return Deposition(
        concept_doi=concept_doi,
        version_doi=version_doi,
        files=tuple(sorted(files)),
        excluded_evidence=tuple(sorted(evidence_paths)),
    )


__all__ = [
    "MANIFEST_PATH",
    "DIGESTS_PATH",
    "DepositMetadata",
    "Deposition",
    "ZenodoTransport",
    "FakeZenodoTransport",
    "deposit_payload",
    "deposit_release",
]
