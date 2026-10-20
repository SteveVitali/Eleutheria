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

from collections.abc import Iterable, Mapping, Sequence

from .manifest import PUBLICATION_BASIS, Artifact, BuildSpec, canonical_json


def license_url(spdx: str) -> str | None:
    """The canonical licence URL (P34.21a), or ``None`` for an internal LicenseRef.

    Delegates to :func:`policy.licensing.license_url`: the ``license_url`` fact in
    ``licenses.toml`` wins, then the canonical map, then the SPDX detail page —
    never a fabricated SPDX URL for a ``LicenseRef-*`` (it would 404).
    """
    from policy.licensing import license_url as _url

    return _url(spdx)


def _license_entry(license_id: str) -> dict[str, object]:
    """A Frictionless ``licenses`` entry — ``path`` only when a real URL exists."""
    url = license_url(license_id)
    entry: dict[str, object] = {"name": license_id}
    if url:
        entry["path"] = url
    return entry


def _resource(
    artifact: Artifact,
    *,
    schema_path: str | None = None,
    sources: Sequence[str] = (),
) -> dict[str, object]:
    # Frictionless `format` is the file extension (csv, parquet, jsonl, …), not the
    # media subtype — the media type is carried separately in `mediatype`.
    fmt = artifact.path.rsplit(".", 1)[-1] if "." in artifact.path else ""
    out: dict[str, object] = {
        "name": artifact.name,
        "path": artifact.path,
        "format": fmt,
        "mediatype": artifact.media_type,
        "bytes": artifact.byte_size,
        "hash": f"sha256:{artifact.sha256}",
        "licenses": [_license_entry(artifact.license)],
    }
    # P35.39 (SIG-TRANSP-016 / J3 §6.5): the linked Table Schema the registry
    # generated for this resource's columns + the upstream sources it draws on.
    if schema_path is not None:
        out["schema"] = schema_path
    if sources:
        out["sources"] = [{"title": s} for s in sorted(set(sources))]
    return out


def data_package(
    artifacts: Sequence[Artifact],
    build_spec: BuildSpec | None,
    *,
    schema_by_path: Mapping[str, str] | None = None,
    sources_by_path: Mapping[str, Sequence[str]] | None = None,
    version: str | None = None,
    created: str | None = None,
    package_id: str | None = None,
) -> bytes:
    """A Frictionless **v2** ``datapackage.json`` over the tabular ``artifacts``
    (SIG-EXPORT-002; P35.39 / J3 §6.5 NEW-11).

    Each resource carries its own licence and checksum, because a package spans multiple
    compartments (§42.2) and a consumer must know each resource's licence individually.
    ``schema_by_path`` links every registry-covered resource to its generated
    ``schemas/<resource>.tableschema.json``; ``sources_by_path`` names the
    upstream source ids each resource draws on. ``version``/``created`` default
    to the build's release identity — the publication-bound descriptor emitted
    at activation (``build_spec=None``) passes ``version=<publication_id>``,
    ``created=<activation>``, ``package_id=<the release's concept>``.
    """
    licenses = sorted({a.license for a in artifacts})
    schema_map = schema_by_path or {}
    sources_map = sources_by_path or {}
    if build_spec is not None:
        name = version or build_spec.release_id()
        pkg_id = package_id or build_spec.concept_id()
        default_version = build_spec.release_id()
        default_created = build_spec.as_of_snapshot.isoformat()
    else:
        name = version or "sig-release"
        pkg_id = package_id or name
        default_version = version or ""
        default_created = created or ""
    descriptor = {
        "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
        "profile": "data-package",
        "name": name,
        "id": pkg_id,
        "version": version or default_version,
        "created": created or default_created,
        # P34.21a (E2 H-6, OM-08, ADR-167/ADR-182): the publication-basis label,
        # the same string manifest.json and LICENCES.json carry.
        "publication_basis": PUBLICATION_BASIS,
        "contributors": [
            {
                "title": "Surveillance Infrastructure Graph (SIG)",
                "role": "publisher",
            }
        ],
        "licenses": [_license_entry(lic) for lic in licenses],
        "resources": [
            _resource(
                a,
                schema_path=schema_map.get(a.path),
                sources=sources_map.get(a.path, ()),
            )
            for a in sorted(artifacts, key=lambda a: a.path)
        ],
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
            "license": [{"@id": license_url(lic) or lic} for lic in licenses],
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
                "license": {"@id": license_url(a.license) or a.license},
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
