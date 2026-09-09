# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deployment-lifecycle reconciliation (§29.4, SIG-RECON-038..042).

The four lifecycle tracks of §13.4 (procurement, physical, operational,
authorization) are **orthogonal** and MUST be resolved **independently** at each
point in time (SIG-RECON-038); there is no single-timeline reconciliation. Within
a track:

* Event-log transitions, where available, are the highest-quality evidence and are
  preferred over inferred transitions (SIG-RECON-039).
* Fuzzy-dated events are ordered by their **EDTF envelopes**; where two envelopes
  overlap so their order is indeterminate the timeline records them as
  **unordered-within-window** rather than inventing an order (SIG-RECON-040). The
  envelope derivation is the canonical :func:`db.edtf.derive_envelope`.

Two politically consequential renderings this module owns:

* **Vendor replacement** (SIG-RECON-041): a deployment reaching
  ``procurement:canceled|nonrenewed`` alongside a new deployment of the same
  technology family at the same organization within a window is a ``replaced_by``
  edge rendered **"vendor replaced,"** never "surveillance removed."
* **Canceled contract, hardware present** (SIG-RECON-042): ``procurement:canceled``
  coexisting with ``physical:installed`` is stated plainly and never smoothed into
  either summary.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from db.edtf import Envelope, derive_envelope

from .model import Contradiction, Evidence, ResearchTask

#: The four orthogonal lifecycle tracks (§13.4). Resolved independently.
TRACKS: tuple[str, ...] = ("procurement", "physical", "operational", "authorization")

#: Procurement end-states that, paired with a same-family successor, are a vendor
#: replacement rather than a removal (SIG-RECON-041).
_REPLACEMENT_END_STATES = frozenset({"canceled", "nonrenewed"})

RULE_VERSION = "p08.2/1"

_NEG_INF = datetime.min.replace(tzinfo=UTC)
_POS_INF = datetime.max.replace(tzinfo=UTC)


def _task_id() -> str:
    return f"task:{uuid.uuid4()}"


@dataclass(frozen=True)
class LifecycleEvent:
    """One dated state transition on one lifecycle track."""

    track: str
    state: str
    edtf: str
    #: SIG-RECON-039: an event-log transition outranks an inferred one.
    from_event_log: bool = False
    technology_family: str | None = None
    org_id: str | None = None
    evidence: Evidence | None = None
    claim_id: str = ""

    def __post_init__(self) -> None:
        if self.track not in TRACKS:
            raise ValueError(f"unknown lifecycle track {self.track!r} (§13.4 expects {TRACKS})")

    def envelope(self) -> Envelope:
        return derive_envelope(self.edtf)


def _lo(env: Envelope) -> datetime:
    return env.lower if env.lower is not None else _NEG_INF


def _hi(env: Envelope) -> datetime:
    return env.upper if env.upper is not None else _POS_INF


@dataclass(frozen=True)
class TimelineSlot:
    """One position in a track timeline. More than one event ⇒ their order is
    indeterminate: **unordered-within-window** (SIG-RECON-040)."""

    events: tuple[LifecycleEvent, ...]
    lower: datetime | None
    upper: datetime | None

    @property
    def unordered_within_window(self) -> bool:
        return len(self.events) > 1

    @property
    def states(self) -> tuple[str, ...]:
        return tuple(e.state for e in self.events)


@dataclass(frozen=True)
class TrackTimeline:
    """The independently-resolved timeline for one track (SIG-RECON-038)."""

    track: str
    slots: tuple[TimelineSlot, ...]

    @property
    def current_slot(self) -> TimelineSlot | None:
        return self.slots[-1] if self.slots else None

    def current_state(self) -> str | None:
        """The latest state, or ``None`` if the latest window is unordered."""
        slot = self.current_slot
        if slot is None or slot.unordered_within_window:
            return None
        return slot.events[0].state


def resolve_track(track: str, events: Sequence[LifecycleEvent]) -> TrackTimeline:
    """Order one track's events by EDTF envelope, grouping the indeterminate.

    Events are merged into windows by envelope overlap; events sharing a window are
    unordered-within-window (SIG-RECON-040). Ties within a window are stabilised by
    (event-log first, then EDTF spelling) so the output is deterministic — the
    event-log preference of SIG-RECON-039 surfaces the authoritative transition
    first without discarding the inferred one.
    """
    track_events = [e for e in events if e.track == track]
    ordered = sorted(
        track_events,
        key=lambda e: (_lo(e.envelope()), _hi(e.envelope()), not e.from_event_log, e.edtf),
    )
    slots: list[TimelineSlot] = []
    window: list[LifecycleEvent] = []
    win_lo: datetime | None = None
    win_hi: datetime | None = None
    for e in ordered:
        env = e.envelope()
        lo, hi = _lo(env), _hi(env)
        if not window:
            window, win_lo, win_hi = [e], lo, hi
            continue
        assert win_hi is not None and win_lo is not None
        # Overlaps the running window ⇒ order is indeterminate: same window.
        if lo < win_hi:
            window.append(e)
            win_hi = max(win_hi, hi)
        else:
            slots.append(_slot(window, win_lo, win_hi))
            window, win_lo, win_hi = [e], lo, hi
    if window:
        assert win_lo is not None and win_hi is not None
        slots.append(_slot(window, win_lo, win_hi))
    return TrackTimeline(track=track, slots=tuple(slots))


def _slot(events: Sequence[LifecycleEvent], lo: datetime, hi: datetime) -> TimelineSlot:
    return TimelineSlot(
        events=tuple(events),
        lower=None if lo == _NEG_INF else lo,
        upper=None if hi == _POS_INF else hi,
    )


@dataclass(frozen=True)
class LifecycleReconciliation:
    """The §29.4 output: one timeline per track, resolved independently."""

    subject_id: str
    tracks: dict[str, TrackTimeline]

    def current_states(self) -> dict[str, str | None]:
        return {t: tl.current_state() for t, tl in self.tracks.items()}


def resolve_lifecycle(subject_id: str, events: Sequence[LifecycleEvent]) -> LifecycleReconciliation:
    """Resolve all four tracks independently for one deployment (SIG-RECON-038)."""
    return LifecycleReconciliation(
        subject_id=subject_id,
        tracks={t: resolve_track(t, events) for t in TRACKS},
    )


# --- SIG-RECON-041: vendor replacement, never "surveillance removed" ----------

REPLACEMENT_RENDER = "vendor replaced"
REMOVAL_RENDER_FORBIDDEN = "surveillance removed"


@dataclass(frozen=True)
class ReplacedByEdge:
    """A ``replaced_by`` edge (EdgeType.replaced_by): B supersedes A for the same
    capability at the same org — rendered "vendor replaced," never as removal."""

    prior_deployment_id: str
    successor_deployment_id: str
    org_id: str
    technology_family: str
    rendering: str = REPLACEMENT_RENDER
    edge_type: str = "replaced_by"


@dataclass(frozen=True)
class Deployment:
    """A deployment reduced to what §29.4 replacement detection needs."""

    deployment_id: str
    org_id: str
    technology_family: str
    procurement_state: str
    #: EDTF date the procurement end-state was reached (for canceled/nonrenewed).
    procurement_end_edtf: str | None = None
    #: EDTF date the deployment began (for a successor).
    begin_edtf: str | None = None
    physical_state: str = "unknown"


def detect_vendor_replacement(
    prior: Deployment,
    successor: Deployment,
    *,
    window_days: int,
) -> ReplacedByEdge | None:
    """Detect the vendor-replacement pattern between two deployments (SIG-RECON-041).

    Fires when ``prior`` reached ``procurement:canceled|nonrenewed`` and
    ``successor`` — same organization, same technology family — began within
    ``window_days`` of that end. Returns a ``replaced_by`` edge rendered
    **"vendor replaced"**; returns ``None`` when the pattern does not hold (a genuine
    removal is left as a removal).
    """
    if prior.org_id != successor.org_id:
        return None
    if prior.technology_family != successor.technology_family:
        return None
    if prior.procurement_state not in _REPLACEMENT_END_STATES:
        return None
    if not (prior.procurement_end_edtf and successor.begin_edtf):
        return None
    end = _hi(derive_envelope(prior.procurement_end_edtf))
    begin = _lo(derive_envelope(successor.begin_edtf))
    if begin < _lo(derive_envelope(prior.procurement_end_edtf)):
        return None  # successor predates the cancellation — not a replacement
    gap_days = (begin - end).days
    if gap_days > window_days:
        return None
    return ReplacedByEdge(
        prior_deployment_id=prior.deployment_id,
        successor_deployment_id=successor.deployment_id,
        org_id=prior.org_id,
        technology_family=prior.technology_family,
    )


# --- SIG-RECON-042: canceled contract, hardware still present -----------------


@dataclass(frozen=True)
class LifecycleStatus:
    """A plain-language lifecycle status that never collapses the two tracks."""

    procurement_state: str
    physical_state: str
    rendering: str
    hardware_present_despite_cancellation: bool
    contradiction: Contradiction | None = None
    task: ResearchTask | None = None


def render_lifecycle_status(
    subject_id: str,
    *,
    procurement_state: str,
    physical_state: str,
    as_of_edtf: str,
) -> LifecycleStatus:
    """Render the procurement/physical pair plainly (SIG-RECON-042).

    Where ``procurement:canceled`` coexists with ``physical:installed`` the status
    states both — *"contract canceled; hardware still present as of <date>"* — the
    single most politically consequential distinction the system makes, and it is
    never smoothed into either summary. A research task is generated to establish
    the hardware's disposition.
    """
    both = procurement_state == "canceled" and physical_state == "installed"
    if both:
        rendering = f"contract canceled; hardware still present as of {as_of_edtf}"
        task = ResearchTask(
            task_id=_task_id(),
            task_type="canceled_contract_hardware_present",
            subject_id=subject_id,
            closing_condition=(
                "Establish the disposition of the physically-installed hardware whose "
                "procurement contract is canceled (removed? transferred? operating unpaid?)."
            ),
            detector_version=RULE_VERSION,
            priority=0.7,
            note=rendering,
        )
        contradiction = Contradiction(
            contradiction_type="value_disagreement",
            subject_id=subject_id,
            predicate_id="lifecycle_procurement_vs_physical",
            claim_values=(procurement_state, physical_state),
            note=(
                "Procurement is canceled but hardware is still installed; both states "
                "retained and rendered plainly, never smoothed (SIG-RECON-042)."
            ),
            severity="notable",
            research_task_ids=(task.task_id,),
        )
        return LifecycleStatus(
            procurement_state=procurement_state,
            physical_state=physical_state,
            rendering=rendering,
            hardware_present_despite_cancellation=True,
            contradiction=contradiction,
            task=task,
        )
    return LifecycleStatus(
        procurement_state=procurement_state,
        physical_state=physical_state,
        rendering=f"procurement:{procurement_state}; physical:{physical_state}",
        hardware_present_despite_cancellation=False,
    )


__all__ = [
    "REPLACEMENT_RENDER",
    "REMOVAL_RENDER_FORBIDDEN",
    "RULE_VERSION",
    "TRACKS",
    "Deployment",
    "LifecycleEvent",
    "LifecycleReconciliation",
    "LifecycleStatus",
    "ReplacedByEdge",
    "TimelineSlot",
    "TrackTimeline",
    "detect_vendor_replacement",
    "render_lifecycle_status",
    "resolve_lifecycle",
    "resolve_track",
]
