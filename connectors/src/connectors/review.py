# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Per-source rights-review status and the flip-metadata rule (P21.1, §42, §22.4).

Turning "0 of N sources loadable" into a reviewable, one-line-per-source decision
needs two things the loader gate (:mod:`connectors.loader`) does not itself model:

* **The flip-metadata rule (SIG-INGEST-028/038, SIG-LIC-001/009, RISK-P21-01).**
  A source may only be flipped to ``ingestion_permitted = true`` if it carries the
  review metadata that makes the flip auditable: a resolved rights block, a reviewer
  *role* (``rights_reviewed_by`` — never a personal name, Part VIII §0.7), a review
  date (``rights_reviewed_on``), and a ``last_verified`` date. A flip without them is
  a data error, surfaced by :func:`review_metadata_violations` and failed loudly by
  ``sig-connectors validate``. This is the invariant P21.1 owns; P21.3 refuses to
  fetch any source whose review-status is not fully green.

* **Flip-readiness.** A source is *flip-ready* when everything a reviewer needs is
  already true except the flag itself: a resolved rights block, a
  content-fetching custody posture, and a compact status that permits ingestion —
  with ``ingestion_permitted`` still false. These are the sources a reviewer can
  unblock with a flag flip plus recorded metadata, without further research.

Nothing here decides a flip or asserts a legal conclusion; it reports the gate
state so a human can act (SIG-LIC-009: a recorded reviewer role, not a legal opinion).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from policy.rights import is_undetermined

from .loader import compact_permits_ingestion, custody_permits_fetch
from .registry import SourceRecord, sources


def has_rights_block(record: SourceRecord) -> bool:
    """Whether the source carries a resolved (non-``UNDETERMINED``) rights block."""
    return not is_undetermined(record.rights)


def has_review_metadata(record: SourceRecord) -> bool:
    """Whether the flip-audit metadata (reviewer role + date) is present."""
    return bool(record.rights_reviewed_by) and record.rights_reviewed_on is not None


@dataclass(frozen=True)
class GateBreakdown:
    """The five gate fields for one source (SIG-INGEST-014/028, §22.4, §8.4)."""

    source_id: str
    ingestion_permitted: bool
    compact_ok: bool
    custody_ok: bool
    rights_present: bool
    reviewed_by: bool

    @property
    def flip_ready(self) -> bool:
        """Ready to flip: everything true except the flag (which is still false)."""
        return (
            not self.ingestion_permitted
            and self.compact_ok
            and self.custody_ok
            and self.rights_present
        )

    @property
    def loadable(self) -> bool:
        """The runtime loader verdict (matches :func:`connectors.loader.is_loadable`)."""
        return self.ingestion_permitted and self.compact_ok and self.custody_ok


def gate_breakdown(record: SourceRecord) -> GateBreakdown:
    """Compute the :class:`GateBreakdown` for one source record."""
    return GateBreakdown(
        source_id=record.id,
        ingestion_permitted=record.ingestion_permitted,
        compact_ok=compact_permits_ingestion(record.compact_status),
        custody_ok=custody_permits_fetch(record.custody_posture),
        rights_present=has_rights_block(record),
        reviewed_by=bool(record.rights_reviewed_by),
    )


def is_flip_ready(record: SourceRecord) -> bool:
    """Whether the source is flip-ready (rights + compact + custody, flag false)."""
    return gate_breakdown(record).flip_ready


def flip_ready(records: Iterable[SourceRecord] | None = None) -> list[SourceRecord]:
    """Every flip-ready source, ordered by id."""
    records = list(records) if records is not None else sources()
    return [r for r in records if is_flip_ready(r)]


def review_metadata_violations(records: Iterable[SourceRecord] | None = None) -> list[str]:
    """The flip-metadata rule (SIG-INGEST-028/038, SIG-LIC-001/009, RISK-P21-01).

    Returns one message per offending source: a row with
    ``ingestion_permitted = true`` MUST carry a resolved rights block **and**
    ``rights_reviewed_by`` **and** ``rights_reviewed_on`` **and** ``last_verified``.
    Each message names the offending id so ``validate`` can report it. An empty
    list means the rule holds across the set.
    """
    records = list(records) if records is not None else sources()
    violations: list[str] = []
    for r in records:
        if not r.ingestion_permitted:
            continue
        missing: list[str] = []
        if not has_rights_block(r):
            missing.append("a resolved rights block (not UNDETERMINED)")
        if not r.rights_reviewed_by:
            missing.append("rights_reviewed_by")
        if r.rights_reviewed_on is None:
            missing.append("rights_reviewed_on")
        if r.last_verified is None:
            missing.append("last_verified")
        if missing:
            violations.append(
                f"source {r.id!r} has ingestion_permitted=true but is missing "
                f"{', '.join(missing)}; a flip is invalid without its review metadata "
                "(SIG-INGEST-028/038, SIG-LIC-001)."
            )
    return violations


__all__ = [
    "GateBreakdown",
    "flip_ready",
    "gate_breakdown",
    "has_review_metadata",
    "has_rights_block",
    "is_flip_ready",
    "review_metadata_violations",
]
