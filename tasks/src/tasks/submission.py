# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Contributor submissions: L0 entry, device routing, and data minimisation
(§34.1–34.3, SIG-CONTRIB-002/004/005).

A contribution is a *piece of evidence*, and SIG stores as little about the
person who made it as the work allows. Three rules are made executable here:

* **Enters at L0 (SIG-CONTRIB-002).** :func:`submit` produces an
  :class:`SubmissionReceipt` whose `entry_level` is L0 and whose
  `produces_l1_claim` is ``False``. There is no path in this module that writes a
  graph claim; promotion to L1 is reviewed resolution, downstream.
* **Device observations route away (SIG-CONTRIB-004).** For device observations
  specifically, SIG does not capture the observation — it routes the contributor
  to OSM/DeFlock (:func:`route_device_observation`). SIG's own capture is for the
  things OSM does not hold: operator evidence, signage, contracts, agenda items.
* **Data minimisation (SIG-CONTRIB-005).** *"What is not stored cannot be
  subpoenaed."* :class:`SubmissionRecord` carries no contributor real name, no
  device identifier, and no contributor geolocation beyond the submitted
  observation itself. Transient operational identifiers (IP) live only in an
  :class:`OperationalLog` that :meth:`~OperationalLog.purge_expired` empties past
  the short :data:`PII_MINIMISATION_WINDOW`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta
from enum import StrEnum

from .contributor import SUBMISSION_ENTRY_LEVEL, EvidenceLevel

__all__ = [
    "SubmissionKind",
    "SubmissionReceipt",
    "SubmissionRecord",
    "Referral",
    "OperationalLogEntry",
    "OperationalLog",
    "PII_MINIMISATION_WINDOW",
    "FORBIDDEN_CONTRIBUTOR_DATA",
    "SIG_CAPTURED_KINDS",
    "OSM_ROUTED_KINDS",
    "is_sig_capturable",
    "route_device_observation",
    "submit",
    "retained_submission_fields",
]


class SubmissionKind(StrEnum):
    """What a submission is evidence *of* (§34.2/§34.3).

    Device observations are routed to OSM/DeFlock (SIG-CONTRIB-004); the rest are
    the things OSM does not hold, which SIG captures itself.
    """

    #: A device sighting — routed to OSM/DeFlock, NOT captured by SIG.
    DEVICE_OBSERVATION = "device_observation"
    #: Evidence naming who operates a device (a contract, a portal record).
    OPERATOR_EVIDENCE = "operator_evidence"
    #: A photo of signage (a posted notice, a policy sign).
    SIGNAGE = "signage"
    #: A contract or procurement document.
    CONTRACT = "contract"
    #: A council/agency agenda item.
    AGENDA_ITEM = "agenda_item"
    #: A free-text report or tip.
    REPORT = "report"


#: The kinds SIG captures itself — the things OSM does not hold (SIG-CONTRIB-004).
SIG_CAPTURED_KINDS: frozenset[SubmissionKind] = frozenset(
    {
        SubmissionKind.OPERATOR_EVIDENCE,
        SubmissionKind.SIGNAGE,
        SubmissionKind.CONTRACT,
        SubmissionKind.AGENDA_ITEM,
        SubmissionKind.REPORT,
    }
)

#: The kinds SIG routes elsewhere rather than capturing (SIG-CONTRIB-004).
OSM_ROUTED_KINDS: frozenset[SubmissionKind] = frozenset({SubmissionKind.DEVICE_OBSERVATION})

#: The short window transient operational identifiers may be retained (SIG-CONTRIB-005).
#: Configurable; the default is deliberately short — retention is the exception.
PII_MINIMISATION_WINDOW: timedelta = timedelta(days=7)

#: The contributor-linked categories SIG MUST NOT store (SIG-CONTRIB-005). Named
#: here so the schema test can assert no :class:`SubmissionRecord` field carries
#: any of them; "what is not stored cannot be subpoenaed".
FORBIDDEN_CONTRIBUTOR_DATA: frozenset[str] = frozenset(
    {"real_name", "legal_name", "device_id", "device_identifier", "ip", "ip_address"}
)


class DeviceObservationNotCapturedError(ValueError):
    """Raised if a device observation is submitted to SIG's own capture (SIG-CONTRIB-004)."""


@dataclass(frozen=True)
class Referral:
    """A pointer sending a contributor to the right upstream project (SIG-CONTRIB-004)."""

    target: str
    reason: str


@dataclass(frozen=True)
class SubmissionReceipt:
    """The result of a contributor submission — an L0 artifact, never an L1 claim.

    `entry_level` is L0 and `produces_l1_claim` is ``False`` by construction
    (SIG-CONTRIB-002): a submission is evidence, and the L0→L1 promotion is
    reviewed resolution downstream, not a side effect of submitting.
    """

    submission_id: str
    kind: SubmissionKind
    evidence_ref: str
    entry_level: EvidenceLevel = SUBMISSION_ENTRY_LEVEL
    produces_l1_claim: bool = False

    def __post_init__(self) -> None:
        if self.entry_level is not EvidenceLevel.L0_EVIDENCE:
            raise ValueError("a submission MUST enter at L0, never L1 (SIG-CONTRIB-002)")
        if self.produces_l1_claim:
            raise ValueError("a submission MUST NOT create an L1 claim directly (SIG-CONTRIB-002)")


@dataclass(frozen=True)
class SubmissionRecord:
    """What SIG retains about a submission — deliberately PII-minimal (SIG-CONTRIB-005).

    Every field here is either about the *observation* (the device's location, not
    the contributor's) or a pseudonymous handle. There is no contributor real
    name, no device identifier, and no contributor geolocation beyond the
    submitted observation. The absence is the design (see
    :data:`FORBIDDEN_CONTRIBUTOR_DATA`).
    """

    submission_id: str
    #: The contributor's pseudonymous handle — never a legal name (SIG-CONTRIB-006).
    contributor_handle: str
    kind: SubmissionKind
    evidence_ref: str
    #: The location *of the observed thing* (a device/site), the submitted datum
    #: itself — not the contributor's location or any location history.
    observation_location: str | None = None
    submitted_at: datetime | None = None


@dataclass
class OperationalLogEntry:
    """A transient operational record (e.g. an IP for abuse mitigation)."""

    kind: str
    value: str
    at: datetime


@dataclass
class OperationalLog:
    """Short-lived operational identifiers, purged past the window (SIG-CONTRIB-005).

    IP and other transient identifiers are kept only long enough to mitigate
    active abuse and are then discarded, never archived. :meth:`purge_expired`
    drops every entry older than the window, so retention past it is impossible
    rather than merely discouraged.
    """

    _entries: list[OperationalLogEntry] = field(default_factory=list)

    def record(self, kind: str, value: str, *, at: datetime) -> None:
        """Record a transient operational identifier at time `at`."""
        self._entries.append(OperationalLogEntry(kind=kind, value=value, at=at))

    def entries(self) -> list[OperationalLogEntry]:
        """The currently-retained entries (a copy)."""
        return list(self._entries)

    def purge_expired(
        self, now: datetime, *, window: timedelta = PII_MINIMISATION_WINDOW
    ) -> list[OperationalLogEntry]:
        """Drop every entry older than `window`; return the purged entries.

        An entry is expired once ``now - entry.at >= window``. The retained set is
        replaced in place with only the still-fresh entries.
        """
        kept: list[OperationalLogEntry] = []
        purged: list[OperationalLogEntry] = []
        for entry in self._entries:
            (purged if now - entry.at >= window else kept).append(entry)
        self._entries = kept
        return purged


def is_sig_capturable(kind: SubmissionKind) -> bool:
    """Whether SIG captures this kind itself, vs routing it upstream (SIG-CONTRIB-004)."""
    return kind in SIG_CAPTURED_KINDS


def route_device_observation() -> Referral:
    """Route a device observation to OSM/DeFlock rather than capturing it (SIG-CONTRIB-004)."""
    return Referral(
        target="OSM/DeFlock",
        reason=(
            "device observations belong to OSM/DeFlock (non-goal N7, OL-1.2-03); SIG captures "
            "operator evidence, signage, contracts, and agenda items — the things OSM does not hold"
        ),
    )


def submit(
    *,
    submission_id: str,
    kind: SubmissionKind,
    evidence_ref: str,
) -> SubmissionReceipt:
    """Accept a contributor submission as an L0 evidence artifact (SIG-CONTRIB-002).

    Refuses a device observation: those route to OSM/DeFlock via
    :func:`route_device_observation` (SIG-CONTRIB-004). For every capturable kind
    the receipt is L0 with no L1 claim produced.
    """
    if kind in OSM_ROUTED_KINDS:
        raise DeviceObservationNotCapturedError(
            "device observations are not captured by SIG; route to OSM/DeFlock (SIG-CONTRIB-004)"
        )
    return SubmissionReceipt(submission_id=submission_id, kind=kind, evidence_ref=evidence_ref)


def retained_submission_fields() -> tuple[str, ...]:
    """The field names :class:`SubmissionRecord` retains (for the schema test)."""
    return tuple(f.name for f in fields(SubmissionRecord))
