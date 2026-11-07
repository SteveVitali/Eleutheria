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

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from policy.rights import is_refused, is_undetermined

from .loader import compact_permits_ingestion, custody_permits_fetch
from .registry import SourceRecord, sources

#: The repository root derived from this module's location
#: (``connectors/src/connectors/review.py`` → 3 levels up). ``review_packet``
#: values are repo-relative paths; existence is checked against this root.
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: The recorded flip marker (P37.6 / ADR-235): a flip's registry note reads
#: ``FLIPPED <YYYY-MM-DD> (<gate|ADR>…)``.
_FLIPPED_MARKER = re.compile(r"FLIPPED \d{4}-\d{2}-\d{2}")

#: The loader's ``retrieval_date`` fallback for a rights block that carries no
#: explicit key (``connectors.registry._rights_record``: ``date(2026, 8, 20)``).
#: The fallback exists so an UNDETERMINED row stays well-formed; a *reviewed*
#: row that still carries it simply never recorded its terms retrieval — the
#: sentinel value is exactly the drift this audit flags.
_FALLBACK_RETRIEVAL = date(2026, 8, 20)


def has_rights_block(record: SourceRecord) -> bool:
    """Whether the source carries a resolved (non-``UNDETERMINED``) rights block."""
    return not is_undetermined(record.rights)


def has_review_metadata(record: SourceRecord) -> bool:
    """Whether the flip-audit metadata (reviewer role + date) is present."""
    return bool(record.rights_reviewed_by) and record.rights_reviewed_on is not None


@dataclass(frozen=True)
class GateBreakdown:
    """The gate fields for one source (SIG-INGEST-014/028, §22.4, §8.4, 046c)."""

    source_id: str
    ingestion_permitted: bool
    compact_ok: bool
    custody_ok: bool
    rights_present: bool
    reviewed_by: bool
    #: P36.1a (SIG-INGEST-046c): the rights record carries a recorded
    #: affirmative machine-readable rights reservation — a *refused* state,
    #: distinct from UNDETERMINED, honoured as a refusal.
    rights_reserved: bool = False

    @property
    def flip_ready(self) -> bool:
        """Ready to flip: everything true except the flag (which is still false).

        A reserved source is never flip-ready (SIG-INGEST-046c): the recorded
        refusal closes the conversation — it routes to the operator, not to a
        flag flip.
        """
        return (
            not self.ingestion_permitted
            and not self.rights_reserved
            and self.compact_ok
            and self.custody_ok
            and self.rights_present
        )

    @property
    def loadable(self) -> bool:
        """The runtime loader verdict (matches :func:`connectors.loader.is_loadable`)."""
        return (
            self.ingestion_permitted
            and not self.rights_reserved
            and self.compact_ok
            and self.custody_ok
        )


def gate_breakdown(record: SourceRecord) -> GateBreakdown:
    """Compute the :class:`GateBreakdown` for one source record."""
    return GateBreakdown(
        source_id=record.id,
        ingestion_permitted=record.ingestion_permitted,
        compact_ok=compact_permits_ingestion(record.compact_status),
        custody_ok=custody_permits_fetch(record.custody_posture),
        rights_present=has_rights_block(record),
        reviewed_by=bool(record.rights_reviewed_by),
        rights_reserved=is_refused(record.rights),
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
        # SIG-INGEST-046c: a recorded affirmative rights reservation is honoured
        # as a refusal — the source MUST NOT be flipped while it stands (a
        # refusal is a distinct state from UNDETERMINED, never a pending flip).
        if r.ingestion_permitted and is_refused(r.rights):
            kind = r.rights.reservation.kind if r.rights.reservation else "?"
            violations.append(
                f"source {r.id!r} has ingestion_permitted=true but carries a recorded "
                f"affirmative rights reservation ({kind}); a reservation is honoured "
                "as a refusal and refuses the flip (SIG-INGEST-046c)."
            )
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


def rights_record_consistency_violations(
    records: Iterable[SourceRecord] | None = None,
) -> list[str]:
    """The rights-record consistency rule (P37.6 / ADR-235, SIG-INGEST-028/038).

    Extends :func:`review_metadata_violations` over the **record** half of a
    flip: a row with ``ingestion_permitted = true`` asserts a recorded human
    review, so every field that makes that review auditable must be present
    and self-consistent — never implied:

    * ``review_packet`` names a repo-relative path that **resolves to an
      existing file** — the packet the review was recorded in (a per-source
      packet or a batch annex such as ``rights/annex/p2616/<id>.md``). A
      missing field or a dead path is drift the reader cannot audit.
    * ``notes`` carries the recorded flip marker ``FLIPPED <YYYY-MM-DD>``
      (the Record-rule form: date + gate/ADR citation) **and** the
      ``rights_reviewed_on`` ISO date — the review act and the flip act are
      distinct recorded events (P27.2's reviewed-then-flipped rows carry
      both dates).
    * The ADR-194 resolver tuple is complete: ``rights.attribution`` and
      ``rights.terms_url`` are populated, and ``rights.retrieval_date`` is an
      explicit recorded date (never the loader's ``2026-08-20`` fallback, which
      marks a block that recorded no retrieval), so the claim sink's
      ``(source_id, spdx, attribution, terms_url)`` rights-record key never
      mints a mis-attributed record (SIG-CONTRIB-020).

    Returns one message per offending source, naming the id, so
    ``sig-connectors validate`` can report it. An empty list means the rule
    holds across the set.
    """
    records = list(records) if records is not None else sources()
    violations: list[str] = []
    for r in records:
        if not r.ingestion_permitted:
            continue
        problems: list[str] = []
        if not r.review_packet:
            problems.append("review_packet (the recorded review's packet path)")
        elif not (_REPO_ROOT / r.review_packet).is_file():
            problems.append(f"a review_packet that resolves ({r.review_packet!r} is not a file)")
        if not _FLIPPED_MARKER.search(r.notes or ""):
            problems.append("the recorded flip marker 'FLIPPED <YYYY-MM-DD>' in notes")
        if r.rights_reviewed_on is not None and str(r.rights_reviewed_on) not in (r.notes or ""):
            problems.append(
                "the rights_reviewed_on date inside notes (the review act and the "
                "flip act are distinct recorded events)"
            )
        if not r.rights.attribution.strip():
            problems.append("rights.attribution (ADR-194 resolver tuple)")
        if not r.rights.terms_url.strip():
            problems.append("rights.terms_url (ADR-194 resolver tuple)")
        if r.rights.retrieval_date == _FALLBACK_RETRIEVAL:
            problems.append(
                "an explicit rights.retrieval_date (the row still carries the "
                "loader's 2026-08-20 fallback — no terms retrieval was recorded)"
            )
        if problems:
            violations.append(
                f"source {r.id!r} has ingestion_permitted=true but is missing "
                f"{', '.join(problems)}; a flip's record is incomplete or "
                "inconsistent (P37.6 / ADR-235, SIG-INGEST-028/038)."
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
    "rights_record_consistency_violations",
]
