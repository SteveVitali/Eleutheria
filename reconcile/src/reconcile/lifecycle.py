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

import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from db.edtf import EdtfError, Envelope, derive_envelope

from .model import Contradiction, Evidence, ResearchTask

#: The four orthogonal lifecycle tracks (§13.4). Resolved independently.
TRACKS: tuple[str, ...] = ("procurement", "physical", "operational", "authorization")

#: The §13.4 state vocabulary per track (the LinkML enums are the single source;
#: mirrored here so event-from-claims can route a recorded state to its track —
#: SIG-ONTO-061). ``unknown`` is admissible on every track (SIG-ONTO-063) and is
#: deliberately absent from this map: an ``unknown`` transition carries no
#: track signal, so it can never be routed (honest skip, never a guess).
TRACK_STATES: dict[str, frozenset[str]] = {
    "procurement": frozenset(
        {
            "proposed",
            "rfp_issued",
            "awarded",
            "contracted",
            "cooperative_piggyback",
            "bundle_included",
            "free_trial",
            "donated",
            "third_party_funded",
            "grant_funded_pending",
            "renewed",
            "nonrenewed",
            "canceled",
            "rejected",
        }
    ),
    "physical": frozenset(
        {
            "not_installed",
            "installation",
            "installed",
            "installed_inactive",
            "decommissioning",
            "removed",
            "destroyed_or_lost",
        }
    ),
    "operational": frozenset(
        {"inactive", "pilot", "active", "expanded", "restricted", "suspended"}
    ),
    "authorization": frozenset(
        {
            "unauthorized",
            "approval_pending",
            "authorized",
            "authorized_expired",
            "moratorium",
            "sunset_by_ordinance",
        }
    ),
}

#: The claim predicates that carry dated lifecycle transitions (§23.7/§29.4).
LIFECYCLE_CLAIM_PREDICATES: frozenset[str] = frozenset(
    {"lifecycle_transition", "deployment_lifecycle_transition"}
)

#: The predicate whose claims ARE the event log — a §23.7 audit row is the
#: recorded transition itself, not an inference over evidence (SIG-RECON-039).
EVENT_LOG_PREDICATES: frozenset[str] = frozenset({"deployment_lifecycle_transition"})

#: The EDTF spelling SIG uses for a fully-unknown date (§16.7). An undated
#: transition's envelope is open on both ends — its order against every other
#: event is indeterminate, so it never enters the ordered resolution; the
#: surface lists it as an explicitly-undated event instead.
UNKNOWN_EDTF = ".."

#: Procurement end-states that, paired with a same-family successor, are a vendor
#: replacement rather than a removal (SIG-RECON-041).
_REPLACEMENT_END_STATES = frozenset({"canceled", "nonrenewed"})

RULE_VERSION = "p08.2/2"


def track_for_state(state: str) -> str | None:
    """The §13.4 track a state value belongs to, or ``None``.

    Returns the track when the state sits in exactly one track's vocabulary;
    ``None`` for ``unknown`` (admissible on all four — no track signal) and for
    out-of-vocabulary values (never silently routed).
    """
    if state == "unknown":
        return None
    hits = [t for t, states in TRACK_STATES.items() if state in states]
    return hits[0] if len(hits) == 1 else None


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

    @property
    def decided_state(self) -> str | None:
        """The state this slot's evidence *decides* (SIG-RECON-039).

        An event-log transition is the highest-quality transition evidence and
        MUST be preferred over inferred transitions: where exactly one event-log
        transition sits in the window it decides the state outright — the
        inferred members stay recorded (the slot is still
        ``unordered_within_window``, SIG-RECON-040) but they cannot out-vote the
        log. Two competing event-log transitions in one window — or a window of
        only inferred evidence — decide nothing: ``None``.
        """
        logged = [e for e in self.events if e.from_event_log]
        if len(logged) == 1:
            return logged[0].state
        if len(self.events) == 1:
            return self.events[0].state
        return None


@dataclass(frozen=True)
class TrackTimeline:
    """The independently-resolved timeline for one track (SIG-RECON-038)."""

    track: str
    slots: tuple[TimelineSlot, ...]

    @property
    def current_slot(self) -> TimelineSlot | None:
        return self.slots[-1] if self.slots else None

    def current_state(self) -> str | None:
        """The latest *decided* state (SIG-RECON-039/040).

        ``None`` when the final window's order is indeterminate and no single
        event-log transition decides it — the event log alone may break the tie
        (see :meth:`TimelineSlot.decided_state`); pure-inferred ambiguity never
        invents an order.
        """
        slot = self.current_slot
        return slot.decided_state if slot is not None else None


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


# --- from claims: the event-log / inferred split (SIG-RECON-039) ---------------


def is_undated(event: LifecycleEvent) -> bool:
    """True when the event's date is fully unknown — its envelope is open on
    both ends, so its order against every other event is indeterminate and it
    never enters the ordered resolution (it is listed as undated instead)."""
    return event.edtf == UNKNOWN_EDTF


def _claim_field(row: Any, pos: int, *names: str) -> Any:
    """Read one field off a claim row — positional for sequence rows, named for
    mapping rows (``value``/``value_json`` both accepted for the value slot)."""
    if isinstance(row, Mapping):
        for n in names:
            if n in row:
                return row[n]
        return None
    try:
        return row[pos]
    except (TypeError, IndexError):
        return None


def _transition_value(raw: Any) -> Mapping[str, Any] | None:
    """Parse the claim's transition blob (``{"state", "date", "track"?}``).

    The value may arrive as the ``value_json`` text (a jsonb column read), an
    already-parsed mapping, or ``None``; an unparseable blob is honest absence —
    the claim is skipped, never guessed at.
    """
    if isinstance(raw, Mapping):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except ValueError:
            return None
        return parsed if isinstance(parsed, Mapping) else None
    return None


def lifecycle_events_from_claims(
    rows: Iterable[Any],
) -> dict[str, list[LifecycleEvent]]:
    """Build §29.4 ``LifecycleEvent``s from lifecycle claim rows (SIG-RECON-039).

    Each row names ``subject_id``, ``predicate_id``, the transition blob
    (``value_json``: ``{"state", "date"}`` — ``"track"`` optional), the
    ``claim_id``, and optional EDTF fallbacks (``observed_edtf`` then
    ``valid_edtf`` — a sequence row takes them at positions 4 and 5):

    * ``deployment_lifecycle_transition`` claims are the §23.7 **event log** —
      they build ``from_event_log=True`` events, the highest-quality transition
      evidence the resolver prefers (SIG-RECON-039).
    * ``lifecycle_transition`` claims are procurement-document transitions —
      inferred evidence (``from_event_log=False``).

    The track is the blob's explicit ``track`` when present, else the
    predicate's declared track (``lifecycle_transition`` is procurement per its
    §13.4 definition), else the recorded state's own vocabulary track
    (:func:`track_for_state`). A claim whose track cannot be established — an
    ``unknown``/out-of-vocabulary state, a missing or unparseable value — is
    skipped: routing a transition onto the wrong track is worse than recording
    none. A missing/unparseable date yields an undated event (``edtf`` ``..``);
    it is listed, never ordered.
    """
    out: dict[str, list[LifecycleEvent]] = {}
    for row in rows:
        subject = _claim_field(row, 0, "subject_id", "subject")
        predicate = _claim_field(row, 1, "predicate_id", "predicate")
        if not subject or predicate not in LIFECYCLE_CLAIM_PREDICATES:
            continue
        blob = _transition_value(_claim_field(row, 2, "value", "value_json", "value_json_text"))
        if blob is None:
            continue
        state = str(blob.get("state") or "")
        if not state or state == "unknown":
            continue
        track = str(blob.get("track") or "")
        if track not in TRACKS:
            track = (
                "procurement"
                if predicate == "lifecycle_transition"
                else (track_for_state(state) or "")
            )
        if track not in TRACKS:
            continue
        date_raw = blob.get("date")
        edtf = str(date_raw) if date_raw else ""
        if not edtf:
            for pos, name in ((4, "observed_edtf"), (5, "valid_edtf")):
                cand = _claim_field(row, pos, name)
                if cand:
                    edtf = str(cand)
                    break
        if not edtf:
            edtf = UNKNOWN_EDTF
        elif edtf != UNKNOWN_EDTF:
            try:
                derive_envelope(edtf)
            except EdtfError:
                edtf = UNKNOWN_EDTF
        event = LifecycleEvent(
            track=track,
            state=state,
            edtf=edtf,
            from_event_log=predicate in EVENT_LOG_PREDICATES,
            claim_id=str(_claim_field(row, 3, "claim_id") or ""),
        )
        out.setdefault(str(subject), []).append(event)
    return out


def dated_events(events: Iterable[LifecycleEvent]) -> tuple[LifecycleEvent, ...]:
    """The events with a usable date — the ordered-resolution input set."""
    return tuple(e for e in events if not is_undated(e))


def undated_events(events: Iterable[LifecycleEvent]) -> tuple[LifecycleEvent, ...]:
    """The fully-undated events — listed, never ordered (see :data:`UNKNOWN_EDTF`)."""
    return tuple(e for e in events if is_undated(e))


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


# --- SIG-ONTO-065: the forbidden-combination SOFT constraints -----------------
#
# The four §13.4 cross-track combinations are flagged, never rejected — the
# interesting cases are real. Two are detected elsewhere
# (``procurement=canceled ∧ physical=installed`` by
# :func:`render_lifecycle_status`; ``authorization=authorized ∧
# physical=not_installed`` by the §33.2 ``authorized_not_deployed`` task type).
# This module owns the remaining two detectors:
#
#   * ``physical=removed ∧ operational=active`` — impossible; a **data error**,
#     surfaced as a ``temporal_impossibility`` contradiction plus the research
#     task that resolves it (the detector→task contract, SIG-RECON-057).
#   * ``procurement=canceled ∧ operational=active`` — **legal during wind-down**;
#     flagged for a research task, never a contradiction.

#: The soft-constraint combination codes the detector emits (SIG-ONTO-065).
SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE = "physical_removed_operational_active"
SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE = "procurement_canceled_operational_active"


@dataclass(frozen=True)
class SoftConstraintFinding:
    """One flagged SIG-ONTO-065 combination — a soft constraint: recorded and
    surfaced, never rejected."""

    code: str
    subject_id: str
    rendering: str
    #: ``data_error`` for the impossible combination; ``wind_down`` for the
    #: legal-during-wind-down flag.
    disposition: str
    contradiction: Contradiction | None = None
    task: ResearchTask | None = None


@dataclass(frozen=True)
class SoftConstraintReport:
    """The findings over one reconciliation's decided current states."""

    subject_id: str
    findings: tuple[SoftConstraintFinding, ...]

    @property
    def contradictions(self) -> tuple[Contradiction, ...]:
        return tuple(f.contradiction for f in self.findings if f.contradiction is not None)

    @property
    def tasks(self) -> tuple[ResearchTask, ...]:
        return tuple(f.task for f in self.findings if f.task is not None)

    def fired(self, code: str) -> bool:
        return any(f.code == code for f in self.findings)


def detect_soft_constraints(
    reconciliation: LifecycleReconciliation, *, as_of_edtf: str
) -> SoftConstraintReport:
    """Run the two owned SIG-ONTO-065 detectors over the decided current states.

    Reads ``reconciliation.current_states()`` — an undecided (``None``) track
    fires nothing: a soft constraint flags only on states the evidence decides.
    ``free_trial`` is deliberately not flagged anywhere (SIG-ONTO-064):
    ``free_trial → operational:active`` with no procurement transition is a
    legal path, the discovery-mission edge — the detector never treats it as
    an error.
    """
    states = reconciliation.current_states()
    findings: list[SoftConstraintFinding] = []

    # physical=removed ∧ operational=active — impossible; flag as a data error.
    if states.get("physical") == "removed" and states.get("operational") == "active":
        rendering = (
            "data error: physical:removed recorded alongside operational:active "
            f"as of {as_of_edtf} (SIG-ONTO-065 — flagged, never rejected)"
        )
        task = ResearchTask(
            task_id=_task_id(),
            task_type="impossible_lifecycle_combination",
            subject_id=reconciliation.subject_id,
            closing_condition=(
                "Resolve the impossible combination: the hardware is recorded removed "
                "while the deployment is recorded operationally active — establish which "
                "record is wrong and correct the losing claim."
            ),
            detector_version=RULE_VERSION,
            priority=0.9,
            note=rendering,
        )
        contradiction = Contradiction(
            contradiction_type="temporal_impossibility",
            subject_id=reconciliation.subject_id,
            predicate_id="lifecycle_physical_vs_operational",
            claim_values=(states["physical"] or "", states["operational"] or ""),
            note=(
                "A deployment cannot be simultaneously removed and operationally "
                "active; both states are retained and flagged as a data error, "
                "never silently reconciled (SIG-ONTO-065)."
            ),
            severity="blocking",
            research_task_ids=(task.task_id,),
        )
        findings.append(
            SoftConstraintFinding(
                code=SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE,
                subject_id=reconciliation.subject_id,
                rendering=rendering,
                disposition="data_error",
                contradiction=contradiction,
                task=task,
            )
        )

    # procurement=canceled ∧ operational=active — legal during wind-down; flag
    # for a research task (no contradiction: the combination is real).
    if states.get("procurement") == "canceled" and states.get("operational") == "active":
        rendering = (
            "contract canceled; still operationally active during wind-down "
            f"as of {as_of_edtf} (SIG-ONTO-065 — legal; flagged for research)"
        )
        task = ResearchTask(
            task_id=_task_id(),
            task_type="canceled_contract_still_active",
            subject_id=reconciliation.subject_id,
            closing_condition=(
                "Establish the wind-down state: the procurement contract is canceled "
                "while the deployment remains operationally active — determine whether "
                "service continues unpaid, under a successor arrangement, or past a "
                "recorded end date."
            ),
            detector_version=RULE_VERSION,
            priority=0.7,
            note=rendering,
        )
        findings.append(
            SoftConstraintFinding(
                code=SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE,
                subject_id=reconciliation.subject_id,
                rendering=rendering,
                disposition="wind_down",
                task=task,
            )
        )

    return SoftConstraintReport(subject_id=reconciliation.subject_id, findings=tuple(findings))


__all__ = [
    "EVENT_LOG_PREDICATES",
    "LIFECYCLE_CLAIM_PREDICATES",
    "REPLACEMENT_RENDER",
    "REMOVAL_RENDER_FORBIDDEN",
    "RULE_VERSION",
    "SOFT_PHYSICAL_REMOVED_OPERATIONAL_ACTIVE",
    "SOFT_PROCUREMENT_CANCELED_OPERATIONAL_ACTIVE",
    "TRACKS",
    "TRACK_STATES",
    "UNKNOWN_EDTF",
    "Deployment",
    "LifecycleEvent",
    "LifecycleReconciliation",
    "LifecycleStatus",
    "ReplacedByEdge",
    "SoftConstraintFinding",
    "SoftConstraintReport",
    "TimelineSlot",
    "TrackTimeline",
    "dated_events",
    "detect_soft_constraints",
    "detect_vendor_replacement",
    "is_undated",
    "lifecycle_events_from_claims",
    "render_lifecycle_status",
    "resolve_lifecycle",
    "resolve_track",
    "track_for_state",
    "undated_events",
]
