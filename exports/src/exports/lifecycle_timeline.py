# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Lifecycle events into the dossier ``timeline`` section (P37.9, R11-DATA-05).

The §29.4 reconciler (:mod:`reconcile.lifecycle`) is the single resolver —
this module is the thin surface adapter that turns its output into rows of the
frozen ``web/src/lib/dossier.ts`` ``Row`` contract so the export (and the API
answer served from release bytes) shows a **non-empty timeline wherever
lifecycle evidence exists** (the acceptance shape; F2a NEW-1's "always empty"
gap closed):

* each *dated* claim-built event resolves through :func:`reconcile.lifecycle
  .resolve_lifecycle` — event-log transitions decide where they speak once
  (SIG-RECON-039); windows whose order is indeterminate are marked
  ``unordered_within_window`` rather than given an invented order
  (SIG-RECON-040);
* fully-*undated* transitions never enter the ordering — they are listed as
  explicitly-undated events (``date_kind: "undated"``), the same posture the
  surfaces take for undated relationships (H-3);
* the two owned SIG-ONTO-065 soft-constraint detectors
  (:func:`reconcile.lifecycle.detect_soft_constraints`) emit flagged rows —
  flagged, never rejected.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from reconcile.lifecycle import (
    SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE,
    SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE,
    TRACKS,
    LifecycleEvent,
    LifecycleReconciliation,
    dated_events,
    detect_soft_constraints,
    is_undated,
    lifecycle_events_from_claims,
    resolve_lifecycle,
)

#: The extra row fields are additive over the frozen ``Row`` contract (label /
#: value / note stay the render keys); the four epistemic lifecycle fields let a
#: consumer branch without re-parsing prose.
_ROW_SCHEMA_NOTE = "sig.dossier-timeline/1"


def events_by_subject(claim_rows: Any) -> dict[str, list[LifecycleEvent]]:
    """``subject_id → LifecycleEvent list`` over lifecycle claim rows.

    Thin wrapper over :func:`reconcile.lifecycle.lifecycle_events_from_claims`
    kept beside the emission so the surface owns no logic of its own.
    """
    return lifecycle_events_from_claims(claim_rows or ())


def _event_row(
    event: LifecycleEvent,
    *,
    subject_id: str,
    subject_label: str,
    unordered: bool,
    decides: bool,
) -> dict[str, Any]:
    kind = "event_log" if event.from_event_log else "inferred"
    notes = [f"{subject_label} — {kind} transition (claim {event.claim_id or 'unrecorded'})"]
    if decides:
        notes.append("event log decides the window's state (SIG-RECON-039)")
    if unordered:
        notes.append("order indeterminate — unordered within window (SIG-RECON-040)")
    row: dict[str, Any] = {
        "label": event.edtf if not is_undated(event) else "undated",
        "value": f"{event.track}: {event.state}",
        "note": "; ".join(notes),
        "lifecycle_track": event.track,
        "lifecycle_state": event.state,
        "evidence_kind": kind,
        "subject_id": subject_id,
        "claim_id": event.claim_id or None,
        "schema_note": _ROW_SCHEMA_NOTE,
    }
    if is_undated(event):
        row["date_kind"] = "undated"
    if unordered:
        row["unordered_within_window"] = True
    if decides:
        row["decides_current_state"] = True
    return row


def subject_timeline_rows(
    subject_id: str,
    events: Sequence[LifecycleEvent],
    *,
    subject_label: str | None = None,
    as_of_edtf: str = "today",
) -> tuple[list[dict[str, Any]], LifecycleReconciliation]:
    """The ``timeline`` rows for ONE subject, plus its reconciliation.

    Dated events resolve per track (SIG-RECON-038); undated events append after
    each track's slots as explicitly-undated rows; the two owned SIG-ONTO-065
    detectors flag their combinations as soft-constraint rows. The returned
    reconciliation is the same object the flag rows derive from — the caller may
    also read it for decided current states.
    """
    label = subject_label or subject_id
    rows: list[dict[str, Any]] = []
    dated = dated_events(events)
    undated = [e for e in events if is_undated(e)]
    rec = resolve_lifecycle(subject_id, dated)
    for track in TRACKS:
        tl = rec.tracks[track]
        for slot in tl.slots:
            unordered = slot.unordered_within_window
            decided = slot.decided_state
            for e in slot.events:
                rows.append(
                    _event_row(
                        e,
                        subject_id=subject_id,
                        subject_label=label,
                        unordered=unordered,
                        decides=(decided is not None and e.state == decided and e.from_event_log),
                    )
                )
    for e in undated:
        rows.append(
            _event_row(
                e,
                subject_id=subject_id,
                subject_label=label,
                unordered=False,
                decides=False,
            )
        )
    report = detect_soft_constraints(rec, as_of_edtf=as_of_edtf)
    for f in report.findings:
        rows.append(
            {
                "label": "data error" if f.disposition == "data_error" else "wind-down flag",
                "value": f.rendering.split(" as of ")[0].removeprefix("data error: ").strip(),
                "note": f.rendering,
                "soft_constraint": f.code,
                "disposition": f.disposition,
                "subject_id": subject_id,
                "schema_note": _ROW_SCHEMA_NOTE,
            }
        )
    return rows, rec


def dossier_timeline_rows(
    subject_ids: Iterable[str],
    events_by: Mapping[str, Sequence[LifecycleEvent]],
    *,
    label_by_id: Mapping[str, str] | None = None,
    as_of_edtf: str = "today",
) -> list[dict[str, Any]]:
    """The ``timeline`` rows for the subjects attributed to one dossier.

    ``subject_ids`` is the dossier's member set (the placed leg / the declared
    bucket's site subjects). Only subjects WITH lifecycle events produce rows —
    a dossier with no lifecycle evidence keeps an empty section (honest
    absence), and an unattributed subject never lands on a dossier it was not
    placed under.
    """
    rows: list[dict[str, Any]] = []
    for sid in sorted(subject_ids):
        events = events_by.get(sid)
        if not events:
            continue
        subject_rows, _ = subject_timeline_rows(
            sid,
            events,
            subject_label=(label_by_id or {}).get(sid),
            as_of_edtf=as_of_edtf,
        )
        rows.extend(subject_rows)
    return rows


__all__ = [
    "SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE",
    "SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE",
    "dossier_timeline_rows",
    "events_by_subject",
    "subject_timeline_rows",
]
