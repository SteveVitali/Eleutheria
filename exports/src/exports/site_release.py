# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.13 / SIG-REL-009 (G3 §6.2) — the ``sig.site-release/1`` object.

``release.json`` is the machine-readable release identity every stamped page
links (``<link rel="describedby" type="application/json" href="/release.json">``)
and the data source the stamp itself reads: release label, the two-axis
as-of pair, the build instant, the code commit (linked), the version block,
the evaluation status, the disclosure ids, the allow-list digest and the
integrity-manifest pointer. The object is a **rendering of the descriptor**
(SIG-MEM-011: the stamp's values come from the descriptor, never recomputed
facts) — every field derives from ``sig.publication-descriptor/2`` plus the
integrity-manifest digest the build just computed.

Placement (G3 §6.2 + ``ops/public_routes.toml``): the release build writes
``releases/<pub>/release.json`` (the immutable copy inside the release
namespace) and the release-tree root ``release.json`` (the site-root object
the ``/release.json`` link resolves to — the publish allow-list protects it,
``PROTECTED_NAMES``). The ``v/<pub>/`` and ``s/<pub>/`` copies ride the
publish rows' site-tree staging legs — ``RELEASE_TREE_TOP_LEVEL`` does not
yet admit ``v``/``s`` trees (the ``withBase`` refactor, J3 NEW-6).

A ``sig.site-release/1`` exists only for a v2 release: the schema's ``label``
is a mandatory ``sig-YYYY-MM-DD.N`` the v1 descriptor form never carries.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from . import release_identity as RI
from .manifest import canonical_json, sha256_hex

#: The wire schema id for the site-facing release identity object.
SITE_RELEASE_SCHEMA = "sig.site-release/1"

_PUBLICATION_RE = re.compile(r"^p-[0-9a-f]{64}$")


def site_release_document(
    descriptor: Mapping[str, Any],
    publication_id: str,
    *,
    integrity_manifest_sha256: str,
    routes_sha256: str | None,
    template_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Assemble the ``sig.site-release/1`` document from a v2 descriptor.

    ``descriptor`` MUST be a validated ``sig.publication-descriptor/2`` —
    this function reads ``label``/``snapshot``/``code``/``versions``/
    ``evaluation``/``disclosures``/``build`` verbatim and never recomputes
    them (the descriptor is the stamp's only data source). ``routes_sha256``
    is the digest of the committed ``ops/public_routes.toml`` the release's
    route set is governed by (G3 §5.4); ``None`` is the honest declared-empty
    when no allow-list file was presented to the build.
    """
    if descriptor.get("schema") != RI.DESCRIPTOR_SCHEMA_V2:
        raise ValueError(
            f"site_release_document needs a {RI.DESCRIPTOR_SCHEMA_V2} descriptor, "
            f"got schema {descriptor.get('schema')!r}"
        )
    snap = descriptor.get("snapshot") or {}
    code = descriptor.get("code") or {}
    evaluation = descriptor.get("evaluation") or {}
    build = descriptor.get("build") or {}
    commit = code.get("commit")
    repository = code.get("repository") or RI.CODE_REPOSITORY
    return {
        "schema": SITE_RELEASE_SCHEMA,
        "label": descriptor.get("label"),
        "publication_id": publication_id,
        "descriptor_sha256": sha256_hex(canonical_json(descriptor)),
        "as_of_world": snap.get("as_of_world"),
        "as_of_belief": snap.get("as_of_belief"),
        "belief_pinned": bool(snap.get("belief_pinned")),
        "spine_watermark": snap.get("spine_watermark"),
        "built_at": build.get("built_at"),
        "code": {
            "commit": commit,
            "url": f"{repository}/commit/{commit}" if commit else None,
            "repository": repository,
        },
        "versions": dict(descriptor.get("versions") or {}),
        "evaluation": {
            "status": evaluation.get("status"),
            "deferral_refs": list(evaluation.get("deferral_refs") or []),
        },
        "disclosures": [str(d.get("id")) for d in (descriptor.get("disclosures") or [])],
        "routes_sha256": routes_sha256,
        "template_fingerprint": template_fingerprint,
        "integrity_manifest": {
            "path": f"releases/{publication_id}/integrity_manifest.json",
            "sha256": integrity_manifest_sha256,
        },
    }


def validate_site_release(doc: Mapping[str, Any]) -> list[str]:
    """Fail-closed field validation for ``sig.site-release/1``.

    Returns one line per violation; an empty list means the document carries
    every §6.2 field, populated or explicitly declared-empty. The label is
    load-bearing (the stamp prints it), so it — like the publication id, the
    two instants, the build instant and the manifest pointer — must be
    populated; ancillary fields may be ``None`` (declared-empty).
    """
    failures: list[str] = []
    if doc.get("schema") != SITE_RELEASE_SCHEMA:
        failures.append(f"schema {doc.get('schema')!r} != {SITE_RELEASE_SCHEMA!r}")
    label = doc.get("label")
    if not isinstance(label, str) or not RI.LABEL_RE.match(label):
        failures.append(f"label {label!r} is not sig-YYYY-MM-DD.N")
    pub = doc.get("publication_id")
    if not isinstance(pub, str) or not _PUBLICATION_RE.match(pub):
        failures.append(f"publication_id {pub!r} is not p-<64hex>")
    dsha = doc.get("descriptor_sha256")
    if not isinstance(dsha, str) or not RI._is_hex(dsha, 64):
        failures.append(f"descriptor_sha256 {dsha!r} is not 64-hex")
    if RI.parse_instant(doc.get("as_of_world")) is None:
        failures.append("as_of_world is not an ISO instant")
    if RI.parse_instant(doc.get("as_of_belief")) is None:
        failures.append("as_of_belief is not an ISO instant")
    if not isinstance(doc.get("belief_pinned"), bool):
        failures.append("belief_pinned is not a bool")
    if not (doc.get("spine_watermark") is None or isinstance(doc.get("spine_watermark"), str)):
        failures.append("spine_watermark is not a string or null")
    if RI.parse_instant(doc.get("built_at")) is None:
        failures.append("built_at is not an ISO instant")
    code = doc.get("code")
    if not isinstance(code, Mapping):
        failures.append("code block absent")
    else:
        commit = code.get("commit")
        if not isinstance(commit, str) or not RI._is_hex(commit, 40):
            failures.append(f"code.commit {commit!r} is not 40-hex")
        for field in ("url", "repository"):
            if not isinstance(code.get(field), str) or not code.get(field):
                failures.append(f"code.{field} absent — the commit must link somewhere")
    if not isinstance(doc.get("versions"), Mapping):
        failures.append("versions block absent")
    evaluation = doc.get("evaluation")
    if not isinstance(evaluation, Mapping):
        failures.append("evaluation block absent")
    else:
        if not isinstance(evaluation.get("status"), str) or not evaluation.get("status"):
            failures.append("evaluation.status absent")
        if not isinstance(evaluation.get("deferral_refs"), list):
            failures.append("evaluation.deferral_refs is not a list")
    disclosures = doc.get("disclosures")
    if not isinstance(disclosures, list) or not all(isinstance(d, str) for d in disclosures):
        failures.append("disclosures is not a list of ids")
    routes_sha = doc.get("routes_sha256")
    if routes_sha is not None and not (isinstance(routes_sha, str) and RI._is_hex(routes_sha, 64)):
        failures.append(f"routes_sha256 {routes_sha!r} is not 64-hex or null")
    fingerprint = doc.get("template_fingerprint")
    if fingerprint is not None and not (
        isinstance(fingerprint, str) and RI._is_hex(fingerprint, 64)
    ):
        failures.append(f"template_fingerprint {fingerprint!r} is not 64-hex or null")
    integrity = doc.get("integrity_manifest")
    if not isinstance(integrity, Mapping):
        failures.append("integrity_manifest block absent")
    else:
        if not isinstance(integrity.get("path"), str) or not integrity.get("path"):
            failures.append("integrity_manifest.path absent")
        isha = integrity.get("sha256")
        if not isinstance(isha, str) or not RI._is_hex(isha, 64):
            failures.append(f"integrity_manifest.sha256 {isha!r} is not 64-hex")
    return failures


__all__ = [
    "SITE_RELEASE_SCHEMA",
    "site_release_document",
    "validate_site_release",
]
