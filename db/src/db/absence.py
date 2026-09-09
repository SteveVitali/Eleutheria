# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The four epistemic absence states and their distinguishable rendering (§9.5).

NULL cannot carry the difference between "we have not looked", "we looked and
found nothing", "a source affirms it does not exist", and "sources disagree and
we cannot resolve it". Conflating them is the most common temporal-model bug, so
SIG models four distinct states (SIG-TIME-010) and both the API and the UI MUST
render them distinguishably (SIG-TIME-012) — rendering `NOT_RESEARCHED`
identically to `NO_EVIDENCE_FOUND` is non-conformant.

The physical encoding already exists in the P02.1 schema; this module is the
single mapping between it and the four logical states, plus the distinguishable
presentation every read path uses:

* `NOT_RESEARCHED`      -> `coverage_record.absence_kind = 'not_researched'`
* `NO_EVIDENCE_FOUND`   -> `coverage_record.absence_kind = 'searched_not_found'`
                           (MUST name the sources searched, SIG-TIME-011)
* `EVIDENCE_OF_ABSENCE` -> a `claim` with `claim_polarity = 'denies'`
                           (`coverage_record.absence_kind = 'evidence_of_absence'`)
* `UNRESOLVED`          -> an L3 `resolution` row with
                           `contradiction_state = 'unresolved_conflict'`
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class AbsenceState(StrEnum):
    """The four states §9.5 forbids collapsing into NULL (SIG-TIME-010)."""

    NOT_RESEARCHED = "NOT_RESEARCHED"
    NO_EVIDENCE_FOUND = "NO_EVIDENCE_FOUND"
    EVIDENCE_OF_ABSENCE = "EVIDENCE_OF_ABSENCE"
    UNRESOLVED = "UNRESOLVED"


# The `coverage_record.absence_kind` vocabulary (§32.1, graph_annotations.sql).
# NOTE these four are NOT the four §9.5 epistemic *states*: `UNRESOLVED` is a
# state with no coverage kind (it lives on the L3 resolution row), and
# `not_applicable` is a coverage kind with no epistemic state (the predicate does
# not apply to the subject — it is not a species of "unknown").
NOT_APPLICABLE_KIND = "not_applicable"
ABSENCE_KINDS: frozenset[str] = frozenset(
    {"not_researched", "searched_not_found", "evidence_of_absence", NOT_APPLICABLE_KIND}
)

# AbsenceState <-> coverage_record.absence_kind (graph_annotations.sql). UNRESOLVED
# has no coverage_kind: it lives on the L3 resolution row, not a coverage record.
# `not_applicable` has no epistemic state: it is a coverage kind, not an "unknown".
_STATE_TO_COVERAGE_KIND: dict[AbsenceState, str] = {
    AbsenceState.NOT_RESEARCHED: "not_researched",
    AbsenceState.NO_EVIDENCE_FOUND: "searched_not_found",
    AbsenceState.EVIDENCE_OF_ABSENCE: "evidence_of_absence",
}
_COVERAGE_KIND_TO_STATE: dict[str, AbsenceState] = {
    v: k for k, v in _STATE_TO_COVERAGE_KIND.items()
}

# The L3 resolution contradiction_state that surfaces as UNRESOLVED (§16.4).
UNRESOLVED_CONTRADICTION_STATE = "unresolved_conflict"


def coverage_kind_for(state: AbsenceState) -> str:
    """The `coverage_record.absence_kind` for a coverage-recorded state."""
    try:
        return _STATE_TO_COVERAGE_KIND[state]
    except KeyError:
        raise ValueError(
            f"{state.value} is not encoded as a coverage record; it is an L3 "
            f"resolution outcome ({UNRESOLVED_CONTRADICTION_STATE})"
        ) from None


def state_from_coverage_kind(absence_kind: str) -> AbsenceState:
    """Map a `coverage_record.absence_kind` back to its logical state.

    `not_applicable` is a valid coverage kind but carries no §9.5 epistemic
    state (it is not a species of "unknown"), so it raises rather than being
    silently coerced into one.
    """
    try:
        return _COVERAGE_KIND_TO_STATE[absence_kind]
    except KeyError:
        if absence_kind == NOT_APPLICABLE_KIND:
            raise ValueError(
                f"{absence_kind!r} has no §9.5 epistemic state; the predicate does "
                "not apply to the subject, which is not a kind of unknown"
            ) from None
        raise ValueError(f"unknown coverage absence_kind {absence_kind!r}") from None


@dataclass(frozen=True)
class AbsenceRendering:
    """A distinguishable presentation of an absence state (SIG-TIME-012).

    `state` is the §9.5 epistemic state, or `None` for the `not_applicable`
    coverage kind, which carries no epistemic state (it is not a kind of
    "unknown"). Distinguishability keys off `code`, which is never `None` and
    never shared between two renderings.
    """

    state: AbsenceState | None
    label: str
    detail: str
    # A stable machine token every surface keys off; never NULL, never shared
    # between two states (this is what makes them distinguishable).
    code: str


def render_absence(
    state: AbsenceState,
    *,
    sources_searched: Sequence[str] | None = None,
    dissenting_claim_count: int | None = None,
) -> AbsenceRendering:
    """Render an absence state distinguishably (SIG-TIME-011/012).

    `NO_EVIDENCE_FOUND` MUST name the sources searched (SIG-TIME-011): "not in
    the Atlas" and "not in the Atlas, not in any portal, and not in three years of
    council minutes" are different statements, and a `NO_EVIDENCE_FOUND` without
    sources is rejected.
    """
    if state is AbsenceState.NOT_RESEARCHED:
        return AbsenceRendering(
            state=state,
            label="Not researched",
            detail="SIG has not yet looked for this.",
            code=state.value,
        )
    if state is AbsenceState.NO_EVIDENCE_FOUND:
        if not sources_searched:
            raise ValueError("NO_EVIDENCE_FOUND MUST name the sources searched (SIG-TIME-011)")
        listed = ", ".join(sources_searched)
        return AbsenceRendering(
            state=state,
            label="Searched, none found",
            detail=f"Searched and found nothing in: {listed}.",
            code=state.value,
        )
    if state is AbsenceState.EVIDENCE_OF_ABSENCE:
        return AbsenceRendering(
            state=state,
            label="Evidence of absence",
            detail="A source affirmatively states this does not exist.",
            code=state.value,
        )
    count = dissenting_claim_count if dissenting_claim_count is not None else 0
    return AbsenceRendering(
        state=AbsenceState.UNRESOLVED,
        label="Unresolved",
        detail=(
            "Evidence exists and disagrees; no resolution is defensible"
            + (f" ({count} dissenting claims)." if count else ".")
        ),
        code=AbsenceState.UNRESOLVED.value,
    )


# The distinguishable rendering token for the fourth coverage kind. It is neither
# an `AbsenceState` (not a kind of "unknown") nor blank; it keys off its own token
# so the API and UI never conflate "does not apply" with "not yet researched".
NOT_APPLICABLE_CODE = "NOT_APPLICABLE"


def render_coverage_kind(
    absence_kind: str,
    *,
    sources_searched: Sequence[str] | None = None,
) -> AbsenceRendering:
    """Render any of the four §32.1 coverage `absence_kind`s distinguishably.

    The three "unknown"-family kinds delegate to :func:`render_absence` via their
    §9.5 state; `not_applicable` — the predicate does not apply to the subject —
    gets its own distinguishable rendering, because collapsing it into
    `not_researched` (SIG-TIME-012) would misreport a deliberate non-question as an
    unmet research obligation. `searched_not_found` still MUST name the sources
    searched (SIG-TIME-011); an empty `sources_searched` is rejected.
    """
    if absence_kind == NOT_APPLICABLE_KIND:
        return AbsenceRendering(
            state=None,  # no §9.5 epistemic state: not a kind of "unknown"
            label="Not applicable",
            detail="This predicate does not apply to this subject.",
            code=NOT_APPLICABLE_CODE,
        )
    if absence_kind not in ABSENCE_KINDS:
        raise ValueError(f"unknown coverage absence_kind {absence_kind!r}")
    return render_absence(state_from_coverage_kind(absence_kind), sources_searched=sources_searched)
