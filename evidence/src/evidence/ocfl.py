# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""An OCFL 1.1 storage root for evidence bytes (§17.3, SIG-EVID-005).

Evidence bytes live in an OCFL 1.1 root: **one object per source stream, one
version per capture**, with ``sha512`` in the inventory manifest and BLAKE3 in
the ``fixity`` block. OCFL is chosen precisely because an object is **readable
without SIG's code** — the ``inventory.json`` is plain JSON next to the files and
resolves version → digest → content path (E5, §46.5 continuity).

Deduplication is by digest (SIG-EVID-004): a capture whose bytes match an earlier
version writes **no new content file**; the new version's ``state`` simply points
at the digest already in the manifest. A portal page fetched daily that has not
changed therefore produces one stored blob and N versions.

This module writes into a byte-addressed :class:`evidence.storage.BlobStore`, so
the same OCFL logic drives a local filesystem (tests, air-gapped restore) and an
S3 root (production) unchanged.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .digest import blake3_hex, sha512_hex

if TYPE_CHECKING:
    from .storage import BlobStore

OCFL_VERSION = "ocfl_1.1"
OCFL_OBJECT_VERSION = "ocfl_object_1.1"
INVENTORY_TYPE = "https://ocfl.io/1.1/spec/#inventory"
DIGEST_ALGORITHM = "sha512"
CONTENT_DIRECTORY = "content"
# Registered OCFL storage-layout extension (hashed + id n-tuple); recorded in
# ocfl_layout.json so a third party can locate an object from its id alone.
STORAGE_LAYOUT_EXTENSION = "0003-hash-and-id-n-tuple-storage-layout"

_ID_SAFE = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_")


def _percent_encode_id(object_id: str) -> str:
    """Percent-encode an object id for its encapsulation directory (ext 0003)."""
    out: list[str] = []
    for byte in object_id.encode("utf-8"):
        char = chr(byte)
        if char in _ID_SAFE:
            out.append(char)
        else:
            out.append(f"%{byte:02x}")
    return "".join(out)


def object_path(object_id: str) -> str:
    """The storage path (relative to the root) that holds ``object_id``.

    Extension 0003: three 2-char tuples of ``sha256(id)`` hex, then the
    percent-encoded id. Deterministic and reproducible from the id alone.
    """
    h = hashlib.sha256(object_id.encode("utf-8")).hexdigest()
    return f"{h[0:2]}/{h[2:4]}/{h[4:6]}/{_percent_encode_id(object_id)}"


def _sidecar(inventory_bytes: bytes) -> bytes:
    return f"{hashlib.sha512(inventory_bytes).hexdigest()}  inventory.json\n".encode()


def _canonical_json(obj: object) -> bytes:
    # Stable key order + compact-ish separators so a re-run is byte-identical.
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class AddedVersion:
    """The outcome of adding a capture to an object."""

    object_id: str
    version: str  # "v1", "v2", …
    new_content_paths: dict[str, str]  # logical path -> content path actually written
    deduplicated: tuple[str, ...]  # logical paths whose bytes were already stored


class OcflStore:
    """An OCFL 1.1 storage root backed by a byte-addressed blob store."""

    def __init__(self, store: BlobStore, root_prefix: str = "") -> None:
        self._store = store
        self._prefix = root_prefix.strip("/")

    # -- root ----------------------------------------------------------------
    def _key(self, *parts: str) -> str:
        segments = [self._prefix, *[p.strip("/") for p in parts if p != ""]]
        return "/".join(s for s in segments if s)

    def initialize_root(self) -> None:
        """Write the storage-root conformance declaration + layout description."""
        self._store.put(self._key(f"0={OCFL_VERSION}"), f"{OCFL_VERSION}\n".encode())
        self._store.put(
            self._key("ocfl_layout.json"),
            _canonical_json(
                {
                    "extension": STORAGE_LAYOUT_EXTENSION,
                    "description": (
                        "Objects are addressed by three 2-char tuples of the SHA-256 of the "
                        "object id, then the percent-encoded id."
                    ),
                }
            ),
        )

    def root_initialized(self) -> bool:
        return self._store.exists(self._key(f"0={OCFL_VERSION}"))

    # -- read ----------------------------------------------------------------
    def read_inventory(self, object_id: str) -> dict:
        raw = self._store.get(self._key(object_path(object_id), "inventory.json"))
        return json.loads(raw)

    def object_exists(self, object_id: str) -> bool:
        return self._store.exists(self._key(object_path(object_id), f"0={OCFL_OBJECT_VERSION}"))

    def resolve(self, object_id: str, version: str, logical_path: str) -> bytes:
        """Resolve version → digest → content path → bytes (as OCFL prescribes)."""
        inventory = self.read_inventory(object_id)
        state = inventory["versions"][version]["state"]
        digest = _find_digest(state, logical_path)
        if digest is None:
            raise KeyError(f"{logical_path!r} is not in {object_id} {version}")
        content_path = inventory["manifest"][digest][0]
        return self._store.get(self._key(object_path(object_id), content_path))

    # -- write ---------------------------------------------------------------
    def add_version(
        self,
        object_id: str,
        files: dict[str, bytes],
        *,
        message: str = "",
        user: dict[str, str] | None = None,
        created: datetime | None = None,
    ) -> AddedVersion:
        """Add one capture as a new OCFL version; dedup content by digest."""
        if not files:
            raise ValueError("a capture must contain at least one file")
        if not self.root_initialized():
            self.initialize_root()

        obj_root = object_path(object_id)
        existing = self.read_inventory(object_id) if self.object_exists(object_id) else None
        manifest: dict[str, list[str]] = (
            {k: list(v) for k, v in existing["manifest"].items()} if existing else {}
        )
        fixity: dict[str, dict[str, list[str]]] = (
            {"blake3": {k: list(v) for k, v in existing["fixity"]["blake3"].items()}}
            if existing and "fixity" in existing
            else {"blake3": {}}
        )
        versions: dict[str, dict] = dict(existing["versions"]) if existing else {}
        next_n = len(versions) + 1
        version = f"v{next_n}"

        state: dict[str, list[str]] = {}
        new_content: dict[str, str] = {}
        deduped: list[str] = []
        for logical_path in sorted(files):
            data = files[logical_path]
            digest = sha512_hex(data)
            state.setdefault(digest, []).append(logical_path)
            if digest in manifest:
                deduped.append(logical_path)
                continue
            content_path = f"{version}/{CONTENT_DIRECTORY}/{logical_path}"
            manifest[digest] = [content_path]
            fixity["blake3"].setdefault(blake3_hex(data), []).append(content_path)
            new_content[logical_path] = content_path
            self._store.put(self._key(obj_root, content_path), data)

        created_at = (created or datetime.now(UTC)).astimezone(UTC)
        versions[version] = {
            "created": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "state": state,
            "message": message,
            "user": user or {"name": "sig-evidence", "address": "https://sig-project.org"},
        }

        inventory = {
            "id": object_id,
            "type": INVENTORY_TYPE,
            "digestAlgorithm": DIGEST_ALGORITHM,
            "head": version,
            "contentDirectory": CONTENT_DIRECTORY,
            "manifest": manifest,
            "versions": versions,
            "fixity": fixity,
        }
        inventory_bytes = _canonical_json(inventory)
        sidecar = _sidecar(inventory_bytes)

        # Object conformance declaration (idempotent) + root and per-version copies
        # of the inventory (OCFL requires the version copy for recoverability).
        self._store.put(
            self._key(obj_root, f"0={OCFL_OBJECT_VERSION}"),
            f"{OCFL_OBJECT_VERSION}\n".encode(),
        )
        self._store.put(self._key(obj_root, "inventory.json"), inventory_bytes)
        self._store.put(self._key(obj_root, "inventory.json.sha512"), sidecar)
        self._store.put(self._key(obj_root, version, "inventory.json"), inventory_bytes)
        self._store.put(self._key(obj_root, version, "inventory.json.sha512"), sidecar)
        return AddedVersion(
            object_id=object_id,
            version=version,
            new_content_paths=new_content,
            deduplicated=tuple(deduped),
        )


def _find_digest(state: dict[str, list[str]], logical_path: str) -> str | None:
    for digest, paths in state.items():
        if logical_path in paths:
            return digest
    return None
