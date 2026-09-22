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
from typing import TYPE_CHECKING, Protocol

from .manifest import Artifact, Manifest, canonical_json, sha256_hex

if TYPE_CHECKING:
    import httpx

#: The path the release manifest is deposited under.
MANIFEST_PATH = "manifest.json"
#: The path the digest manifest (evidence-bytes stand-in) is deposited under.
DIGESTS_PATH = "digests.json"

#: The Zenodo REST API base URLs. The **sandbox** mints throwaway ``10.5072`` test DOIs
#: on a free account (HG-07); production mints real ``10.5281`` DOIs and is an operator
#: action only. A dry-run deposit contacts neither (``FakeZenodoTransport``).
ZENODO_SANDBOX_API = "https://sandbox.zenodo.org/api"
ZENODO_PRODUCTION_API = "https://zenodo.org/api"
#: The DOI prefixes the two Zenodo instances mint under (RISK-P21-08: sandbox ≠ prod).
ZENODO_SANDBOX_PREFIX = "10.5072/zenodo"
ZENODO_PRODUCTION_PREFIX = "10.5281/zenodo"


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


#: SPDX → Zenodo licence-id mapping (Zenodo uses its own vocabulary, not SPDX).
_ZENODO_LICENSE_IDS: dict[str, str] = {
    "CC-BY-4.0": "cc-by-4.0",
    "CC0-1.0": "cc-zero",
    "ODbL-1.0": "odbl-1.0",
    "Apache-2.0": "apache-2.0",
}


def zenodo_metadata(
    metadata: DepositMetadata, *, description: str | None = None
) -> dict[str, object]:
    """The Zenodo deposition ``metadata`` block, in the shape the REST API expects.

    Zenodo takes ONE primary ``license`` (its own vocabulary), so the most-open
    compartment licence is the primary and **every** compartment licence is spelled
    out in the description + keywords — the deposit is compartment-aware (SIG-LIC-004,
    §42): a reader sees that the release mixes an ODbL layer with a CC-BY graph.
    """
    spdx = tuple(metadata.licenses)
    # The most-open licence is the primary; CC0 > CC-BY > ODbL for "primary" ordering.
    order = {"CC0-1.0": 0, "CC-BY-4.0": 1, "Apache-2.0": 2, "ODbL-1.0": 3}
    primary = min(spdx, key=lambda s: order.get(s, 99)) if spdx else "CC-BY-4.0"
    licence_line = ", ".join(spdx) if spdx else "CC-BY-4.0"
    desc = description or (
        f"SIG bulk-export release {metadata.version}. "
        f"Per-compartment licences (§42, SIG-LIC-004): {licence_line}. "
        "The OSM-derived physical layer is a separate ODbL 1.0 compartment "
        "(attribution + share-alike); the SIG graph is CC-BY-4.0."
    )
    return {
        "title": metadata.title,
        "upload_type": "dataset",
        "version": metadata.version,
        "description": desc,
        "license": _ZENODO_LICENSE_IDS.get(primary, "cc-by-4.0"),
        "creators": [{"name": "The SIG project"}],
        "keywords": [
            "surveillance",
            "knowledge-graph",
            "provenance",
            *spdx,
        ],
    }


@dataclass
class ZenodoHttpTransport:
    """The real Zenodo REST transport over ``httpx`` (SIG-EXPORT-002).

    Implements the Zenodo deposition flow: create an empty deposition, PUT the
    bibliographic metadata, upload each file to the deposition's bucket, and publish —
    then read the ``conceptdoi`` (stable across versions) and the version ``doi`` off
    the published record. ``sandbox=True`` targets ``sandbox.zenodo.org`` (free,
    throwaway ``10.5072`` DOIs); production is an operator action.

    The network is only ever touched in production wiring, never in a test or a dry-run
    build — the deposit *policy* is decided against :class:`FakeZenodoTransport`.
    """

    token: str
    sandbox: bool = True
    api_base: str | None = None
    #: Injectable for tests: an ``httpx.MockTransport`` asserts the real request shapes
    #: without a live account (HG-07). Production leaves it ``None`` → a real client.
    transport: httpx.BaseTransport | None = None

    def _base(self) -> str:
        if self.api_base:
            return self.api_base
        return ZENODO_SANDBOX_API if self.sandbox else ZENODO_PRODUCTION_API

    def deposit(
        self,
        *,
        concept_id: str,
        version: str,
        files: Mapping[str, bytes],
        metadata: DepositMetadata,
    ) -> tuple[str, str]:
        import httpx

        params = {"access_token": self.token}
        client = httpx.Client(base_url=self._base(), transport=self.transport, timeout=60.0)
        try:
            created = client.post("/deposit/depositions", params=params, json={})
            created.raise_for_status()
            deposition = created.json()
            deposition_id = deposition["id"]
            bucket_url = deposition["links"]["bucket"]

            meta_resp = client.put(
                f"/deposit/depositions/{deposition_id}",
                params=params,
                json={"metadata": zenodo_metadata(metadata)},
            )
            meta_resp.raise_for_status()

            for name, data in sorted(files.items()):
                up = client.put(f"{bucket_url}/{name}", params=params, content=data)
                up.raise_for_status()

            published = client.post(
                f"/deposit/depositions/{deposition_id}/actions/publish", params=params
            )
            published.raise_for_status()
            record = published.json()
        finally:
            client.close()

        concept_doi = str(record.get("conceptdoi") or record.get("metadata", {}).get("conceptdoi"))
        version_doi = str(record.get("doi") or record.get("metadata", {}).get("doi"))
        return concept_doi, version_doi


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


def deposit_export_dir(
    export_dir: str,
    transport: ZenodoTransport,
    *,
    extra_files: Mapping[str, bytes] = {},
) -> Deposition:
    """Deposit a built export directory (``sig-exports build --out <dir>``) to Zenodo.

    Reads the on-disk ``manifest.json``, deposits every non-evidence artifact plus the
    manifest, the digest manifest, and any ``extra_files`` (the SBOM + ``CITATION.cff``,
    §38.2). The concept/version DOIs come from the manifest's identity so the deposit
    is a pure function of the release bytes.
    """
    import json
    import os

    with open(os.path.join(export_dir, "manifest.json"), encoding="utf-8") as fh:
        manifest_doc = json.load(fh)
    concept_id = str(manifest_doc["concept_id"])
    release_id = str(manifest_doc["release_id"])
    artifacts = manifest_doc.get("artifacts", [])
    licenses = tuple(sorted({str(a["license"]) for a in artifacts}))
    # Evidence bytes are excluded by size (§38.2); their digests still ride in digests.json.
    evidence_paths = {
        str(a["path"]) for a in artifacts if str(a.get("compartment", "")).startswith("evidence")
    }
    files: dict[str, bytes] = {}
    for a in artifacts:
        path = str(a["path"])
        if path in evidence_paths:
            continue
        with open(os.path.join(export_dir, path), "rb") as fh:
            files[path] = fh.read()
    files[MANIFEST_PATH] = canonical_json(manifest_doc)
    files[DIGESTS_PATH] = canonical_json({str(a["path"]): str(a["sha256"]) for a in artifacts})
    for name, data in extra_files.items():
        files[name] = data

    metadata = DepositMetadata(
        title=f"SIG dataset release {release_id}",
        version=release_id,
        concept_id=concept_id,
        licenses=licenses,
    )
    concept_doi, version_doi = transport.deposit(
        concept_id=concept_id, version=release_id, files=files, metadata=metadata
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
    "ZENODO_SANDBOX_API",
    "ZENODO_PRODUCTION_API",
    "ZENODO_SANDBOX_PREFIX",
    "ZENODO_PRODUCTION_PREFIX",
    "DepositMetadata",
    "Deposition",
    "ZenodoTransport",
    "FakeZenodoTransport",
    "ZenodoHttpTransport",
    "zenodo_metadata",
    "deposit_payload",
    "deposit_release",
    "deposit_export_dir",
]
