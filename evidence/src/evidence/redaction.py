# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Redaction as a new capture (§17.5, SIG-EVID-011).

Redaction MUST produce a **new capture** with ``parent_capture_id`` set — never an
edit of the original (SIG-EPIS-006). The redaction method and version MUST be
recorded so that a mis-redaction can be identified and re-done. The original bytes
are write-once in OCFL and are never touched; the redacted derivative is a fresh
OCFL version with its own digest.
"""

from __future__ import annotations

from dataclasses import dataclass

from .digest import multihash


@dataclass(frozen=True)
class RedactedCapture:
    """A redacted derivative capture, pointing back at the original."""

    parent_capture_id: str
    redaction_method: str
    redaction_version: str
    content_digest: str  # multihash of the redacted bytes
    byte_size: int
    redaction_applied: bool = True

    def to_row(self) -> dict[str, object]:
        """The ``evidence_capture`` column values for the redacted derivative."""
        return {
            "parent_capture_id": self.parent_capture_id,
            "redaction_applied": self.redaction_applied,
            "redaction_method": self.redaction_method,
            "redaction_version": self.redaction_version,
            "content_digest": self.content_digest,
            "byte_size": self.byte_size,
        }


def redact(
    parent_capture_id: str,
    redacted_bytes: bytes,
    *,
    method: str,
    version: str,
) -> RedactedCapture:
    """Build a redacted derivative capture (SIG-EVID-011).

    ``method`` and ``version`` are required — a redaction with no recorded method
    cannot be audited or re-done, so it is rejected.
    """
    if not method or not version:
        raise ValueError("redaction method and version are required (SIG-EVID-011)")
    return RedactedCapture(
        parent_capture_id=parent_capture_id,
        redaction_method=method,
        redaction_version=version,
        content_digest=multihash(redacted_bytes),
        byte_size=len(redacted_bytes),
    )
