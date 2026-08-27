# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The evidence-store facade (§17): capture set → OCFL version → capture rows.

:class:`EvidenceStore` is the seam every connector writes through. It takes a
capture set for one fetch of one source stream, writes the bytes once into the
OCFL object for that stream (deduplicating unchanged bytes, SIG-EVID-004), and
returns the ``evidence_capture`` / ``evidence_blob`` row values the DB layer
persists. One fetch is one OCFL version holding the capture-set files; each file
is a separate ``evidence_capture`` row sharing the artifact (SIG-EVID-005/008).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .capture import CaptureFile, RawCapture, capture_set
from .digest import blake3_hex, multihash
from .ocfl import AddedVersion, OcflStore
from .tiers import StorageTier


@dataclass(frozen=True)
class StoredCaptureSet:
    """The result of storing one fetch: the OCFL version + the DB rows to write."""

    object_id: str
    version: str
    added: AddedVersion
    capture_rows: tuple[dict[str, object], ...]
    blob_rows: tuple[dict[str, object], ...]


class EvidenceStore:
    """Write-once evidence store over an OCFL 1.1 root (ADR-006)."""

    def __init__(self, ocfl: OcflStore) -> None:
        self._ocfl = ocfl

    def store_capture_set(
        self,
        *,
        object_id: str,
        source_uri: str,
        raw: RawCapture,
        tier: StorageTier = StorageTier.PUBLIC,
        retrieved_by_run_id: str | None = None,
        capture_tool_version: str = "sig-evidence/0",
    ) -> StoredCaptureSet:
        """Store one fetch of a source stream and return its DB rows."""
        files = capture_set(raw)
        return self._store_files(
            object_id=object_id,
            source_uri=source_uri,
            files=files,
            tier=tier,
            retrieved_at=raw.captured_at,
            retrieved_by_run_id=retrieved_by_run_id,
            capture_tool_version=capture_tool_version,
        )

    def _store_files(
        self,
        *,
        object_id: str,
        source_uri: str,
        files: list[CaptureFile],
        tier: StorageTier,
        retrieved_at: datetime,
        retrieved_by_run_id: str | None,
        capture_tool_version: str,
    ) -> StoredCaptureSet:
        version_files = {f.logical_name: f.data for f in files}
        added = self._ocfl.add_version(
            object_id, version_files, message=f"capture {source_uri}", created=retrieved_at
        )
        capture_rows: list[dict[str, object]] = []
        blob_rows: list[dict[str, object]] = []
        seen_blobs: set[str] = set()
        for f in files:
            digest = multihash(f.data)
            capture_rows.append(
                {
                    "content_digest": digest,
                    "digest_blake3": blake3_hex(f.data),
                    "byte_size": len(f.data),
                    "media_type": f.media_type,
                    "source_uri": source_uri,
                    "ocfl_object_id": object_id,
                    "ocfl_version": added.version,
                    "storage_tier": tier.value,
                    "capture_method": f.role,
                    "capture_tool_version": capture_tool_version,
                    "retrieved_at": retrieved_at,
                    "retrieved_by_run_id": retrieved_by_run_id,
                    "logical_path": f.logical_name,
                }
            )
            deduplicated = f.logical_name in added.deduplicated
            if digest not in seen_blobs:
                seen_blobs.add(digest)
                blob_rows.append(
                    {
                        "blob_digest": digest,
                        "source_uri": source_uri,
                        "byte_size": len(f.data),
                        "ocfl_object_id": object_id,
                        "ocfl_version": added.version,
                        "deduplicated": deduplicated,
                    }
                )
        return StoredCaptureSet(
            object_id=object_id,
            version=added.version,
            added=added,
            capture_rows=tuple(capture_rows),
            blob_rows=tuple(blob_rows),
        )
