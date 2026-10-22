# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""DCAT 3 catalog emission (P35.39 / SIG-TRANSP-016, J3 §6.6, J1 NEW-11).

``catalog.jsonld`` is the machine-readable, **linked** catalog the D-J3-7
"linked files only" posture requires — public pages point at it with
``<link rel="alternate" type="application/ld+json">``; no JSON-LD is ever
inlined into HTML.

Two documents come out of this module:

* the export-level ``catalog.jsonld`` — one ``dcat:Dataset`` per licence
  compartment, each artifact a ``dcat:Distribution`` carrying its
  ``dcat:downloadURL``, ``dcat:mediaType``, ``dcat:byteSize`` and an
  ``spdx:Checksum`` (the manifest's sha256, so a consumer can verify the
  download against exactly the digest the manifest recorded);
* the release-registry ``releases/catalog.jsonld`` — the
  ``dcat:DatasetSeries`` over activated releases: one ``dcat:Dataset`` per
  publication with ``dcat:previousVersion`` chaining to the prior activated
  publication and ``prov:wasGeneratedBy`` naming the export run's provenance
  node.

Every IRI mints under the owned bases — the ``ns`` base for vocabulary
anchors and the ``prov`` base for lineage nodes, each imported from its one
declared emitter (``exports.formats.SIG_NS`` / ``exports.provo.SIG``,
P35.38b / ADR-217's one-declared-base-per-surface rule). The retired
project host (ADR-217) is never reintroduced.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .formats import SIG_NS  # the one declared /ns/ emitter (P35.38b)
from .frictionless import license_url
from .manifest import Artifact, canonical_json
from .provo import SIG as SIG_PROV  # the one declared /prov/ emitter (P35.38b)

#: The public origin every ``dcat:downloadURL`` resolves against (P27.6 /
#: ADR-093 — the same canonical origin the web build stamps).
CANONICAL_ORIGIN = "https://surveillancegraph.org"

#: The JSON-LD context the catalogs share (DCAT 3 + DCTerms + PROV + SPDX).
CONTEXT: dict[str, Any] = {
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "prov": "http://www.w3.org/ns/prov#",
    "spdx": "http://spdx.org/rdf/terms#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "sig": SIG_NS,
}

#: The DatasetSeries IRI identifying the release line (the catalog's
#: ``dcat:seriesMember`` anchor and each dataset's ``dcat:inSeries``).
SERIES_IRI = f"{SIG_NS}series/sig-releases"

#: ``dct:accessRights`` values per publication posture — DCAT-AP style
#: controlled vocabulary anchors under the owned namespace.
_ACCESS_PUBLIC = f"{SIG_NS}accessRights/public"
_ACCESS_RESTRICTED = f"{SIG_NS}accessRights/restricted"


def _license_ref(license_id: str) -> dict[str, Any]:
    url = license_url(license_id)
    return {"@id": url or f"{SIG_NS}license/{license_id}"}


def _checksum(hexdigest: str) -> dict[str, Any]:
    return {
        "@type": "spdx:Checksum",
        "spdx:algorithm": {"@id": "spdx:checksumAlgorithm_sha256"},
        "spdx:checksumValue": hexdigest,
    }


def _distribution(artifact: Artifact, *, download_base: str) -> dict[str, Any]:
    """One artifact as a ``dcat:Distribution`` (downloadURL + mediaType +
    byteSize + the manifest's spdx:checksum)."""
    return {
        "@id": f"{SIG_NS}distribution/{artifact.path}",
        "@type": "dcat:Distribution",
        "dct:title": artifact.path,
        "dcat:downloadURL": {"@id": f"{download_base.rstrip('/')}/{artifact.path}"},
        "dcat:mediaType": artifact.media_type,
        "dcat:byteSize": artifact.byte_size,
        "spdx:checksum": _checksum(artifact.sha256),
        "dct:license": _license_ref(artifact.license),
    }


def export_catalog(
    artifacts: Sequence[Artifact],
    *,
    release_id: str,
    created: str,
    download_base: str = CANONICAL_ORIGIN,
    compartments_public: Iterable[str] = (),
    run_id: str | None = None,
) -> bytes:
    """The export-level ``catalog.jsonld``: one ``dcat:Dataset`` per compartment.

    ``compartments_public`` names the compartments cleared for public
    distribution (the publish-partitioned set); every other compartment is
    ``dct:accessRights`` restricted — the catalog *describes* the bundle
    without making a public claim about restricted bytes.
    ``run_id`` is the provenance run node (the release id by default) — each
    dataset's ``prov:wasGeneratedBy`` names it.
    """
    public = set(compartments_public)
    by_comp: dict[str, list[Artifact]] = {}
    for art in artifacts:
        if art.path == "catalog.jsonld":
            continue  # the catalog never distributes itself
        by_comp.setdefault(str(art.compartment), []).append(art)
    datasets: list[dict[str, Any]] = []
    for comp in sorted(by_comp):
        arts = sorted(by_comp[comp], key=lambda a: a.path)
        licenses = sorted({a.license for a in arts})
        ds: dict[str, Any] = {
            "@id": f"{SIG_NS}dataset/{release_id}/{comp}",
            "@type": "dcat:Dataset",
            "dct:title": f"SIG {comp} compartment — {release_id}",
            "dct:license": [_license_ref(lic) for lic in licenses],
            "dct:accessRights": {"@id": _ACCESS_PUBLIC if comp in public else _ACCESS_RESTRICTED},
            "dcat:inSeries": {"@id": SERIES_IRI},
            "dcat:version": release_id,
            "dct:issued": created,
            "prov:wasGeneratedBy": {"@id": f"{SIG_PROV}run/{run_id or release_id}"},
            "dcat:distribution": [_distribution(a, download_base=download_base) for a in arts],
        }
        datasets.append(ds)
    doc = {
        "@context": CONTEXT,
        "@id": f"{SIG_NS}catalog/{release_id}",
        "@type": "dcat:Catalog",
        "dct:title": f"SIG export catalog — {release_id}",
        "dct:issued": created,
        "dcat:dataset": datasets,
    }
    return canonical_json(doc)


def series_catalog(
    publications: Sequence[Mapping[str, Any]],
    *,
    activations: Mapping[str, Mapping[str, Any]] | None = None,
    download_base: str = CANONICAL_ORIGIN,
) -> bytes:
    """The release-registry ``releases/catalog.jsonld`` (DCAT 3).

    ``publications`` are the registry catalog's entries **in activation
    order**; ``activations`` maps ``publication_id`` → the recorded
    ``sig.activation/1`` receipt (its ``activated_at`` is each dataset's
    ``dct:issued``). ``dcat:previousVersion`` chains each member to the
    previously activated release, and ``prov:wasGeneratedBy`` names the
    release's export-run provenance node.
    """
    acts = activations or {}
    members: list[dict[str, Any]] = []
    prev_id: str | None = None
    for entry in publications:
        pub = str(entry.get("publication_id") or "")
        if not pub:
            continue
        issued = str((acts.get(pub) or {}).get("activated_at") or "") or None
        ds: dict[str, Any] = {
            "@id": f"{SIG_NS}release/{pub}",
            "@type": "dcat:Dataset",
            "dct:title": f"SIG release {pub}",
            "dcat:inSeries": {"@id": SERIES_IRI},
            "dcat:version": pub,
            "prov:wasGeneratedBy": {"@id": f"{SIG_PROV}run/{entry.get('data_release_id') or pub}"},
        }
        if issued:
            ds["dct:issued"] = issued
        if prev_id is not None:
            ds["dcat:previousVersion"] = {"@id": f"{SIG_NS}release/{prev_id}"}
        # The release's own landing + machine-readable entries are its
        # distributions (the catalog.json record carries the descriptors).
        dists: list[dict[str, Any]] = [
            {
                "@id": f"{SIG_NS}distribution/releases/{pub}",
                "@type": "dcat:Distribution",
                "dct:title": f"SIG release {pub} namespace",
                "dcat:accessURL": {"@id": f"{download_base}/releases/{pub}/"},
                "dcat:mediaType": "text/html",
            },
            {
                "@id": f"{SIG_NS}distribution/releases/{pub}/datapackage.json",
                "@type": "dcat:Distribution",
                "dct:title": f"SIG release {pub} Frictionless descriptor",
                "dcat:downloadURL": {"@id": f"{download_base}/releases/{pub}/datapackage.json"},
                "dcat:mediaType": "application/json",
            },
        ]
        ds["dcat:distribution"] = dists
        members.append(ds)
        prev_id = pub
    doc = {
        "@context": CONTEXT,
        "@id": f"{SIG_NS}catalog/releases",
        "@type": "dcat:Catalog",
        "dct:title": "SIG release series catalog",
        "dcat:dataset": [
            {
                "@id": SERIES_IRI,
                "@type": "dcat:DatasetSeries",
                "dct:title": "SIG releases",
                "dct:publisher": {"@id": f"{SIG_NS}publisher/sig"},
            },
            *members,
        ],
    }
    return canonical_json(doc)


__all__ = [
    "CANONICAL_ORIGIN",
    "CONTEXT",
    "SERIES_IRI",
    "SIG_NS",
    "SIG_PROV",
    "export_catalog",
    "series_catalog",
]
