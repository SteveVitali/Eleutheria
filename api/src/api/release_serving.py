# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.57 / SIG-REL-010 (G3 §6.4, REL-05) — release-backed serving.

The parity rule: every API route whose answer the site shows MUST serve the
**current promoted release's files** (or ``?release=<publication_id>`` for any
promoted release) and name that release — ``X-SIG-Basis: release`` plus a body
``release {label, publication_id, as_of_world}`` block. Every other route keeps
serving the live claim spine and labels itself ``live-spine``.

The API-slice file contract this module serves — a release declares the
machine-readable JSON twins of its site-visible answers under
``r/<pub>/api/`` (manifest-pinned, immutable bytes, like every other release
artifact):

    /v1/export                ->  r/<pub>/api/export.json
    /v1/changes               ->  r/<pub>/api/changes.json
    /v1/sources               ->  r/<pub>/api/sources.json
    /v1/sources/<id>          ->  r/<pub>/api/sources/<id>.json
    /v1/dossier/<scope>       ->  r/<pub>/api/dossier/<scope path>.json
    /v1/coverage/<scope>      ->  r/<pub>/api/coverage/<scope path>.json

``<scope path>`` maps the scope token's ``:``-separated segments to directory
levels (``jurisdiction:okc`` -> ``api/dossier/jurisdiction/okc.json``); every
segment must match ``[A-Za-z0-9._-]+`` and may never be ``.`` or ``..``, so no
scope can escape the release's ``api/`` directory. ``/v1/releases/**`` answers
from the registry's own files (``latest.json``, the catalog, the descriptor).

``r/<pub>/api/index.json`` (schema ``sig.api-slice/1``) is the emitter's
declaration of the complete slice — the V7 promotion preflight
(``ops.release_publish_verify``) refuses a release whose declared documents
are missing or unpinned, and refuses a release that stages dossier pages the
slice does not cover. The serving path itself resolves files by contract, so
an index is never needed to answer.

Failure posture (fail closed, never a placeholder — DR-C3-12 / ACT-08):

* an unknown or unpromoted ``?release=`` -> 404 ``unknown_publication``;
* an unknown scope (no file in the release) -> 404 ``scope_not_available``;
* a family file the release should carry but does not -> 503
  ``release_artifact_absent`` (a servability defect V7 exists to prevent);
* a file present but absent from the integrity manifest, or failing digest
  verification -> 503 ``release_artifact_unpinned`` / ``release_verification_failed``;
* a release document whose embedded ``release`` block names a different
  publication -> 503 ``release_metadata_mismatch``;
* a withdrawn route -> 410 ``withdrawn`` (the CURRENT withdrawal registry is
  re-evaluated per request — the same one P32.5 policy ``route_access``);
* no promoted release at all -> 503 ``no_current_release``.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exports.release import ReleaseRegistry, route_access

from .release_search import PUBLICATION_RE

#: The api-slice index schema the release emitter declares.
API_SLICE_SCHEMA = "sig.api-slice/1"

#: One path segment of an API-slice file name — never ``/``, ``.`` or ``..``.
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")

_MANIFEST_CACHE_CAP = 8


class ReleaseServingError(Exception):
    """A release-serving refusal mapped to a typed ``{detail, code, **extra}``
    body — the same error shape as ``SearchIndexError`` (P32.14 idiom)."""

    def __init__(
        self,
        status: int,
        code: str,
        detail: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.extra = extra or {}


class _ArtifactAbsent(Exception):
    """The staged file does not exist — the caller maps it to a typed error
    (404 for an unknown scope, 503 for a family the release should carry)."""


@dataclass(frozen=True)
class ReleaseIdentity:
    """The ``release {label, publication_id, as_of_world}`` block every
    release-backed answer names — fields absent from the registry are
    omitted, never fabricated."""

    publication_id: str
    label: str | None = None
    as_of_world: str | None = None

    def block(self) -> dict[str, str]:
        out: dict[str, str] = {"publication_id": self.publication_id}
        if self.label:
            out["label"] = self.label
        if self.as_of_world:
            out["as_of_world"] = self.as_of_world
        return out

    def header(self) -> str:
        """The ``X-SIG-Release`` header value: ``<label> <pub>`` (G3 §6.3)."""
        return f"{self.label} {self.publication_id}" if self.label else self.publication_id


def api_path(pub: str, family: str, name: str | None = None) -> str:
    """The release-relative path of an api-slice document — the single source
    of truth for the contract the emitter writes and the server reads.

    ``name`` is a scope/key token; its ``:``-separated segments become
    directory levels. A segment outside ``[A-Za-z0-9._-]+`` (or ``.``/``..``)
    is rejected — it names no document in the release."""
    base = f"r/{pub}/api/{family}"
    if name is None:
        return f"{base}.json"
    segments = name.split(":")
    if any(not _SEGMENT_RE.match(seg) or seg in {".", ".."} for seg in segments):
        raise _ArtifactAbsent(f"{family}:{name}")
    return f"{base}/{'/'.join(segments)}.json"


class ReleaseServingStore:
    """Verified read-only serving of a release's api-slice files.

    ``registry_root`` is the activated release registry — ``latest.json`` the
    current-pointer, ``catalog.json`` the promoted publications, ``staged/``
    the immutable bytes, ``withdrawals.json`` the current disposition set.
    """

    def __init__(self, registry_root: Path | str) -> None:
        self.registry_root = Path(registry_root)
        self.staged = self.registry_root / "staged"
        #: (pub, path) entries that passed integrity-manifest verification —
        #: bytes under a namespace can never change, so re-hashing per request
        #: is wasted (the ReleaseSearchStore idiom, P32.14).
        self._verified: set[tuple[str, str]] = set()
        self._manifests: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    # -- registry state ----------------------------------------------------- #

    def _registry(self) -> ReleaseRegistry:
        """A fresh registry view per call — catalog/latest/withdrawals are
        mutable serving files re-read on every request so a promotion or a
        withhold recorded mid-process takes effect at once."""
        return ReleaseRegistry(self.registry_root)

    def catalog(self) -> dict[str, Any]:
        return self._registry().catalog()

    def latest(self) -> dict[str, Any] | None:
        return self._registry().latest()

    def catalog_entry(self, pub: str) -> dict[str, Any] | None:
        return self._registry().find(pub)

    def publications(self) -> list[dict[str, Any]]:
        """The promoted-release list for ``/v1/releases`` — safe summary
        fields only (the catalog entry is already the external record)."""
        out: list[dict[str, Any]] = []
        for entry in self.catalog().get("publications") or []:
            compat = entry.get("compat") or {}
            out.append(
                {
                    "publication_id": entry.get("publication_id"),
                    "label": entry.get("data_release_id"),
                    "manifest_sha256": entry.get("manifest_sha256"),
                    "as_of_world": compat.get("as_of_world"),
                    "as_of_belief": compat.get("as_of_belief"),
                    "compartments": [c.get("compartment") for c in entry.get("compartments") or []],
                    "href": f"/v1/releases/{entry.get('publication_id')}",
                }
            )
        return out

    # -- identity / resolution ---------------------------------------------- #

    def identity(self, pub: str) -> ReleaseIdentity:
        """The release block for a promoted publication — ``label`` is the
        catalog entry's ``data_release_id``, ``as_of_world`` its compat pair
        (descriptor fallback). Unknown/unpromoted pubs refuse 404."""
        entry = self.catalog_entry(pub)
        if entry is None:
            raise ReleaseServingError(
                404,
                "unknown_publication",
                f"publication {pub} is not a promoted release",
            )
        as_of_world = (entry.get("compat") or {}).get("as_of_world")
        if as_of_world is None:
            try:
                descriptor = self.read_json(pub, f"releases/{pub}/descriptor.json")
                as_of_world = descriptor.get("as_of_world")
            except (_ArtifactAbsent, ReleaseServingError):
                as_of_world = None
        return ReleaseIdentity(
            publication_id=pub,
            label=entry.get("data_release_id"),
            as_of_world=as_of_world,
        )

    def current_identity(self) -> ReleaseIdentity | None:
        """The promoted release the current pointer names — ``None`` (never a
        fabricated id) when no promotion has happened."""
        latest = self.latest() or {}
        pub = latest.get("publication_id")
        if not pub:
            return None
        entry = self.catalog_entry(str(pub)) or {}
        return ReleaseIdentity(
            publication_id=str(pub),
            label=entry.get("data_release_id") or latest.get("data_release_id"),
            as_of_world=(entry.get("compat") or {}).get("as_of_world"),
        )

    def resolve_publication(self, requested: str | None) -> str:
        """The publication a release-backed route serves: ``?release=<pub>``
        for any promoted release, else the current pointer."""
        if requested is not None:
            if not PUBLICATION_RE.match(requested):
                raise ReleaseServingError(
                    404, "unknown_publication", f"unknown publication {requested!r}"
                )
            if self.catalog_entry(requested) is None:
                raise ReleaseServingError(
                    404,
                    "unknown_publication",
                    f"publication {requested} is not a promoted release",
                )
            return requested
        latest = self.latest() or {}
        pub = latest.get("publication_id")
        if not pub:
            raise ReleaseServingError(
                503,
                "no_current_release",
                "no promoted release is current — the registry carries no latest pointer",
            )
        return str(pub)

    # -- verified reads ------------------------------------------------------ #

    def _integrity_manifest(self, pub: str) -> dict[str, Any]:
        with self._lock:
            cached = self._manifests.get(pub)
            if cached is not None:
                self._manifests.move_to_end(pub)
                return cached
        path = self.staged / f"releases/{pub}/integrity_manifest.json"
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ReleaseServingError(
                503,
                "release_not_staged",
                f"release {pub} has no staged integrity manifest",
            ) from exc
        with self._lock:
            self._manifests[pub] = manifest
            self._manifests.move_to_end(pub)
            while len(self._manifests) > _MANIFEST_CACHE_CAP:
                self._manifests.popitem(last=False)
        return manifest

    def _verify(self, pub: str, rel: str, path: Path) -> None:
        """Digest-pin a staged file to its release's integrity manifest — a
        file that exists but is not manifest-pinned (or whose bytes drift)
        fails closed, never served."""
        manifest = self._integrity_manifest(pub)
        entry = next(
            (a for a in manifest.get("artifacts") or [] if a.get("path") == rel),
            None,
        )
        if entry is None:
            raise ReleaseServingError(
                503,
                "release_artifact_unpinned",
                f"{rel} is not pinned by the release integrity manifest",
            )
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise _ArtifactAbsent(rel) from exc
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry.get("sha256") or len(data) != entry.get("byte_size"):
            raise ReleaseServingError(
                503,
                "release_verification_failed",
                f"{rel} bytes do not match the release integrity manifest",
            )
        self._verified.add((pub, rel))

    def read_bytes(self, pub: str, rel: str) -> bytes:
        """Read a manifest-pinned release file from the staged tree."""
        target = self.staged / rel
        if not target.is_file():
            raise _ArtifactAbsent(rel)
        if (pub, rel) not in self._verified:
            self._verify(pub, rel, target)
        return target.read_bytes()

    def read_json(self, pub: str, rel: str) -> Any:
        data = self.read_bytes(pub, rel)
        try:
            return json.loads(data)
        except ValueError as exc:
            raise ReleaseServingError(
                503,
                "release_artifact_malformed",
                f"{rel} is not parseable JSON",
            ) from exc

    # -- the api-slice contract ---------------------------------------------- #

    def api_document(
        self,
        requested_pub: str | None,
        family: str,
        name: str | None = None,
        *,
        absent_status: int = 404,
        absent_code: str = "scope_not_available",
    ) -> tuple[dict[str, Any], ReleaseIdentity]:
        """Serve one api-slice document for ``family``/``name`` under the
        resolved publication. Returns ``(payload, identity)`` where the
        payload's ``release`` block is the resolved identity — the file's own
        ``release`` field, when present, must agree."""
        pub = self.resolve_publication(requested_pub)
        ident = self.identity(pub)
        try:
            rel = api_path(pub, family, name)
        except _ArtifactAbsent:
            raise ReleaseServingError(
                absent_status,
                absent_code,
                f"release {pub} holds no api/{family} document for {name!r}",
            ) from None
        # The withdrawal barrier dominates, re-evaluated per request: a
        # release-level (or route-level) deny answers 410, never stale bytes.
        access = route_access(self.registry_root, rel)
        if not access.get("permitted"):
            raise ReleaseServingError(
                410,
                "withdrawn",
                "withdrawn under the current publication-disposition policy",
                extra={"tombstone": access.get("tombstone") or {}},
            )
        try:
            payload = self.read_json(pub, rel)
        except _ArtifactAbsent:
            raise ReleaseServingError(
                absent_status,
                absent_code,
                f"release {pub} holds no api/{family} document for {name or 'the family index'}",
            ) from None
        if not isinstance(payload, dict):
            raise ReleaseServingError(
                503,
                "release_artifact_malformed",
                f"{rel} is not a JSON object",
            )
        embedded = payload.get("release")
        if (
            isinstance(embedded, dict)
            and embedded.get("publication_id") is not None
            and str(embedded.get("publication_id")) != pub
        ):
            raise ReleaseServingError(
                503,
                "release_metadata_mismatch",
                f"{rel} names a different publication than the release it is served under",
            )
        return {**payload, "release": ident.block()}, ident

    # -- the /v1/releases registry routes ------------------------------------ #

    def releases_index(self) -> tuple[dict[str, Any], ReleaseIdentity]:
        """``/v1/releases`` — the promoted publications + the current pointer."""
        ident = self.current_identity()
        if ident is None:
            raise ReleaseServingError(
                503,
                "no_current_release",
                "no promoted release is current — the registry carries no latest pointer",
            )
        latest = self.latest() or {}
        return (
            {
                "publications": self.publications(),
                "latest": {
                    "publication_id": latest.get("publication_id"),
                    "label": latest.get("data_release_id"),
                    "manifest_sha256": latest.get("manifest_sha256"),
                },
                "release": ident.block(),
            },
            ident,
        )

    def latest_document(self) -> tuple[dict[str, Any], ReleaseIdentity]:
        """``/v1/releases/latest`` — the current pointer + its descriptor."""
        ident = self.current_identity()
        if ident is None:
            raise ReleaseServingError(
                503,
                "no_current_release",
                "no promoted release is current — the registry carries no latest pointer",
            )
        descriptor = self.read_json(
            ident.publication_id, f"releases/{ident.publication_id}/descriptor.json"
        )
        return (
            {
                "latest": self.latest(),
                "descriptor": descriptor,
                "release": ident.block(),
            },
            ident,
        )

    def release_document(self, pub: str) -> tuple[dict[str, Any], ReleaseIdentity]:
        """``/v1/releases/{publication_id}`` — the promoted release's
        descriptor + catalog record (the external signed entry)."""
        if not PUBLICATION_RE.match(pub):
            raise ReleaseServingError(404, "unknown_publication", f"unknown publication {pub!r}")
        ident = self.identity(pub)
        descriptor = self.read_json(pub, f"releases/{pub}/descriptor.json")
        entry = self.catalog_entry(pub) or {}
        return (
            {
                "publication": {
                    "publication_id": entry.get("publication_id"),
                    "label": entry.get("data_release_id"),
                    "manifest_sha256": entry.get("manifest_sha256"),
                    "artifact_count": entry.get("artifact_count"),
                    "compartments": [c.get("compartment") for c in entry.get("compartments") or []],
                },
                "descriptor": descriptor,
                "release": ident.block(),
            },
            ident,
        )
