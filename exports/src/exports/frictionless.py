# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Frictionless Data Package + RO-Crate packaging descriptors (§38.1, SIG-EXPORT-002).

Tabular exports ship as a **Frictionless Data Package** (a ``datapackage.json``
descriptor over the tabular resources); evidence bundles ship as an **RO-Crate** (a
``ro-crate-metadata.json`` describing the bundle). Both descriptors are built from the
release :class:`~exports.manifest.Manifest`, so they inherit its checksums and per-file
licences (SIG-EXPORT-001) and are byte-stable (they carry no wall-clock state — the only
date is the release's observation-time snapshot).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .manifest import Artifact, BuildSpec, canonical_json

#: SPDX id -> canonical licence URL, for the descriptor licence fields.
_LICENSE_URLS: dict[str, str] = {
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "ODbL-1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
    "Apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
}


def license_url(spdx: str) -> str:
    """The canonical URL for an SPDX id (falls back to an SPDX detail URL)."""
    return _LICENSE_URLS.get(spdx, f"https://spdx.org/licenses/{spdx}.html")


def _resource(artifact: Artifact) -> dict[str, object]:
    # Frictionless `format` is the file extension (csv, parquet, jsonl, …), not the
    # media subtype — the media type is carried separately in `mediatype`.
    fmt = artifact.path.rsplit(".", 1)[-1] if "." in artifact.path else ""
    return {
        "name": artifact.name,
        "path": artifact.path,
        "format": fmt,
        "mediatype": artifact.media_type,
        "bytes": artifact.byte_size,
        "hash": f"sha256:{artifact.sha256}",
        "licenses": [{"name": artifact.license, "path": license_url(artifact.license)}],
    }


def data_package(artifacts: Sequence[Artifact], build_spec: BuildSpec) -> bytes:
    """A Frictionless ``datapackage.json`` over the tabular ``artifacts`` (SIG-EXPORT-002).

    Each resource carries its own licence and checksum, because a package spans multiple
    compartments (§42.2) and a consumer must know each resource's licence individually.
    """
    licenses = sorted({a.license for a in artifacts})
    descriptor = {
        "profile": "data-package",
        "name": build_spec.release_id(),
        "id": build_spec.concept_id(),
        "version": build_spec.release_id(),
        "created": build_spec.as_of_snapshot.isoformat(),
        "licenses": [{"name": lic, "path": license_url(lic)} for lic in licenses],
        "resources": [_resource(a) for a in sorted(artifacts, key=lambda a: a.path)],
    }
    return canonical_json(descriptor)


def ro_crate(artifacts: Sequence[Artifact], build_spec: BuildSpec) -> bytes:
    """An RO-Crate ``ro-crate-metadata.json`` over the evidence ``artifacts`` (SIG-EXPORT-002).

    Conforms to RO-Crate 1.1: a metadata descriptor entity that is ``about`` the root
    ``Dataset``, the dataset with its ``hasPart`` file list, and one ``File`` entity per
    artifact carrying its content size, checksum, and licence.
    """
    sorted_artifacts = sorted(artifacts, key=lambda a: a.path)
    licenses = sorted({a.license for a in sorted_artifacts})
    graph: list[dict[str, object]] = [
        {
            "@type": "CreativeWork",
            "@id": "ro-crate-metadata.json",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"},
        },
        {
            "@type": "Dataset",
            "@id": "./",
            "name": f"SIG evidence bundle {build_spec.release_id()}",
            "datePublished": build_spec.as_of_snapshot.isoformat(),
            "version": build_spec.release_id(),
            "license": [{"@id": license_url(lic)} for lic in licenses],
            "hasPart": [{"@id": a.path} for a in sorted_artifacts],
        },
    ]
    for a in sorted_artifacts:
        graph.append(
            {
                "@type": "File",
                "@id": a.path,
                "name": a.name,
                "encodingFormat": a.media_type,
                "contentSize": a.byte_size,
                "sha256": a.sha256,
                "license": {"@id": license_url(a.license)},
            }
        )
    return canonical_json({"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": graph})


def collect_licenses(artifacts: Iterable[Artifact]) -> list[str]:
    """The distinct licences present across ``artifacts``, sorted."""
    return sorted({a.license for a in artifacts})


__all__ = [
    "license_url",
    "data_package",
    "ro_crate",
    "collect_licenses",
]
