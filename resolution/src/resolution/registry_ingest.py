# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Registry-ingest guard: a zero-record run fails, and absent is not not-observed
(§14.2, SIG-IDENT-008).

A silent zero is how coverage metrics become lies. Any registry-ingest job that
returns **zero** records for a jurisdiction MUST fail the run rather than persist a
zero — and it MUST distinguish a source that *affirms there are none*
(``EVIDENCE_OF_ABSENCE`` — a positive coverage finding) from *we looked and found
nothing* (``NO_EVIDENCE_FOUND``, which MUST name the sources searched). Both fail
the run; conflating them, or writing a bare ``0``, is the bug this guard forbids.
It reuses the four-state absence model already built in P02.3 (:mod:`db.absence`).
"""

from __future__ import annotations

from collections.abc import Sequence

from db.absence import AbsenceState, render_absence


class ZeroRecordIngest(RuntimeError):
    """A registry ingest returned zero records for a jurisdiction (SIG-IDENT-008)."""

    def __init__(self, jurisdiction: str, absence_state: AbsenceState, detail: str) -> None:
        self.jurisdiction = jurisdiction
        self.absence_state = absence_state
        self.detail = detail
        super().__init__(
            f"zero-record ingest for {jurisdiction!r} fails the run "
            f"({absence_state.value}): {detail} (SIG-IDENT-008)"
        )


def classify_zero(*, source_asserts_absent: bool) -> AbsenceState:
    """Which absence state a zero result represents (SIG-IDENT-008).

    ``source_asserts_absent`` — the source affirmatively says there are none — is
    ``EVIDENCE_OF_ABSENCE``; otherwise the zero is ``NO_EVIDENCE_FOUND`` (we
    searched and found nothing), which is only meaningful with the sources named.
    """
    if source_asserts_absent:
        return AbsenceState.EVIDENCE_OF_ABSENCE
    return AbsenceState.NO_EVIDENCE_FOUND


def assert_registry_records_present(
    record_count: int,
    *,
    jurisdiction: str,
    sources_searched: Sequence[str] | None = None,
    source_asserts_absent: bool = False,
) -> int:
    """Fail the run on a zero-record ingest; otherwise return the count (SIG-IDENT-008).

    On zero, raises :class:`ZeroRecordIngest` carrying the distinguished
    :class:`~db.absence.AbsenceState` so the caller records absent-vs-not-observed
    as a coverage fact instead of persisting a silent zero. A ``NO_EVIDENCE_FOUND``
    zero MUST name the sources searched (SIG-TIME-011), enforced via
    :func:`db.absence.render_absence`.
    """
    if record_count < 0:
        raise ValueError(f"record_count cannot be negative: {record_count}")
    if record_count > 0:
        return record_count
    state = classify_zero(source_asserts_absent=source_asserts_absent)
    rendering = render_absence(state, sources_searched=sources_searched)
    raise ZeroRecordIngest(jurisdiction, state, rendering.detail)
