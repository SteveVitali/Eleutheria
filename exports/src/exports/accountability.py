# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Epistemically-honest rendering of accountability events (§11.17, SIG-ONTO-038, P13.1).

``epistemic_status`` MUST be rendered in every surface, and the graph MUST NOT
flatten "a plaintiff alleged X in a pending lawsuit" into "X happened"
(OL-2E-AA-05). This module is the render-side guarantee of that contract: it
renders an accountability event into a sentence whose **verb is governed by the
event's epistemic status**, and it exposes a mechanical guard
(:func:`assert_not_flattened`) — the render analogue of
:func:`reconcile.rationale.check_template` — that refuses to emit an allegation
phrased as a confirmed fact.

Only a ``confirmed`` or ``adjudicated`` event is a fact that may take a bare
factual verb. Every other status (``alleged``, ``reported``, ``disputed``,
``retracted``, ``policy_action``, ``vendor_statement``) is **non-factual** and its
rendering MUST lead with the epistemic frame and MUST NOT assert the event as a
bare fact. The status vocabulary here mirrors the frozen ontology ``EpistemicStatus``
enum; a test asserts it stays in lock-step (drift is a failed test).

This is the *render* guard. The *write*-side contract (``epistemic_status``
required and preserved verbatim ingestion→resolution→read) lives in the
``accountability`` connector (:mod:`connectors.accountability`) and the resolver.
The production dossier surface (P15.2) consumes this module rather than
re-implementing verb selection.
"""

from __future__ import annotations

import re

# --- the epistemic-status vocabulary (mirrors the frozen ontology enum) -------

#: The full EpistemicStatus vocabulary (§11.17). Kept in lock-step with the
#: ontology enum by a test.
EPISTEMIC_STATUSES: frozenset[str] = frozenset(
    {
        "alleged",
        "reported",
        "confirmed",
        "adjudicated",
        "policy_action",
        "vendor_statement",
        "disputed",
        "retracted",
    }
)

#: The only statuses a rendered surface may state with a bare factual verb — a
#: confirmed or adjudicated event is a fact (SIG-ONTO-038). Everything else is
#: non-factual and MUST be hedged.
FACTUAL_STATUSES: frozenset[str] = frozenset({"confirmed", "adjudicated"})


def is_factual(status: str) -> bool:
    """Whether a status may carry a bare factual verb (only confirmed/adjudicated)."""
    return status in FACTUAL_STATUSES


#: The sentence frame each status leads with. A non-factual frame puts the
#: epistemic qualifier FIRST, so the sentence can never read as a bare fact; the
#: ``{clause}`` is the event described in the neutral third person. Every frame
#: names the status so ``epistemic_status`` is rendered on the surface (SIG-ONTO-038).
STATUS_FRAME: dict[str, str] = {
    "alleged": "It is alleged that {clause}",
    "reported": "It is reported that {clause}",
    "disputed": "It is disputed whether {clause}",
    "retracted": "A since-retracted report stated that {clause}",
    "policy_action": "A policy action was recorded: {clause}",
    "vendor_statement": "Per a vendor statement, {clause}",
    "confirmed": "It is confirmed that {clause}",
    "adjudicated": "A court adjudicated that {clause}",
}

#: The hedge marker each non-factual status's rendering MUST contain — the word
#: that makes the epistemic frame explicit. Used by :func:`assert_not_flattened`.
_HEDGE_MARKER: dict[str, str] = {
    "alleged": "alleged",
    "reported": "reported",
    "disputed": "disputed",
    "retracted": "retracted",
    "policy_action": "policy action",
    "vendor_statement": "vendor statement",
}

#: Bare factual verbs/phrases that assert an event as an unqualified fact. For a
#: NON-factual status, none of these may appear (that would be flattening,
#: OL-2E-AA-05). "confirmed"/"adjudicated" are the factual statuses' own markers
#: and are therefore only banned for non-factual statuses.
_FLATTENING_VERBS: tuple[str, ...] = (
    "happened",
    "occurred",
    "took place",
    "confirmed",
    "adjudicated",
    "proven",
    "proved",
    "established that",
    "is a fact",
    "did occur",
)


class UnknownEpistemicStatus(Exception):
    """Raised when a status outside the EpistemicStatus vocabulary reaches the renderer."""


class AllegationFlattened(Exception):
    """Raised when a non-factual event would render as a bare confirmed fact (OL-2E-AA-05)."""


def _event_label(event_type: str | None) -> str:
    return (event_type or "accountability event").replace("_", " ")


def render_event_phrase(
    subject_label: str,
    epistemic_status: str,
    *,
    event_type: str | None = None,
    detail: str = "",
) -> str:
    """Render one accountability event as an epistemically-honest sentence.

    The verb is governed by ``epistemic_status`` (SIG-ONTO-038): a non-factual
    status leads with its epistemic frame, so an allegation is never phrased as a
    confirmed fact (OL-2E-AA-05). The returned sentence is guaranteed to pass
    :func:`assert_not_flattened`.

    ``subject_label`` names the incident subject (e.g. an agency); ``detail`` is an
    optional neutral description of what is claimed.
    """
    if epistemic_status not in EPISTEMIC_STATUSES:
        raise UnknownEpistemicStatus(
            f"{epistemic_status!r} is not in the EpistemicStatus vocabulary "
            f"{sorted(EPISTEMIC_STATUSES)} (§11.17)"
        )
    label = _event_label(event_type)
    tail = f" {detail.strip()}" if detail.strip() else ""
    clause = f"{subject_label} was the subject of a {label}{tail}".strip()
    sentence = STATUS_FRAME[epistemic_status].format(clause=clause)
    if not sentence.endswith("."):
        sentence += "."
    # Belt-and-braces: the guard proves the render is not a flattening.
    assert_not_flattened(epistemic_status, sentence)
    return sentence


def flattening_findings(epistemic_status: str, rendered: str) -> list[str]:
    """Return the list of flattening violations for a rendered event (empty = ok).

    The mechanical form of OL-2E-AA-05, mirroring
    :func:`reconcile.rationale.check_template`:

    * a status outside the vocabulary is itself a finding;
    * a **non-factual** status MUST carry its hedge marker (so the epistemic
      qualifier is rendered) and MUST NOT contain a bare factual verb;
    * a factual status is unconstrained here (it is a fact).
    """
    problems: list[str] = []
    if epistemic_status not in EPISTEMIC_STATUSES:
        return [f"unknown epistemic_status {epistemic_status!r}"]
    if is_factual(epistemic_status):
        return problems
    low = rendered.lower()
    marker = _HEDGE_MARKER[epistemic_status]
    if marker not in low:
        problems.append(
            f"{epistemic_status}: rendered surface does not carry the epistemic qualifier "
            f"{marker!r} — epistemic_status must be rendered (SIG-ONTO-038)"
        )
    for verb in _FLATTENING_VERBS:
        # Word-boundary match so "occurred" is caught but "reoccurring" is not, and
        # so the hedge word for this status is not itself flagged.
        if verb == marker:
            continue
        if re.search(rf"\b{re.escape(verb)}\b", low):
            problems.append(
                f"{epistemic_status}: rendered surface asserts the event as a bare fact "
                f"({verb!r}); a non-factual event must never be flattened (OL-2E-AA-05)"
            )
    return problems


def assert_not_flattened(epistemic_status: str, rendered: str) -> str:
    """Return ``rendered`` if it does not flatten a non-factual event, else raise.

    The load-bearing render guard (SIG-ONTO-038, OL-2E-AA-05): a surface that
    phrases an ``alleged`` / ``disputed`` / ``retracted`` (or any non-factual)
    event as a confirmed fact raises :class:`AllegationFlattened`.
    """
    problems = flattening_findings(epistemic_status, rendered)
    if problems:
        raise AllegationFlattened("; ".join(problems))
    return rendered


__all__ = [
    "EPISTEMIC_STATUSES",
    "FACTUAL_STATUSES",
    "STATUS_FRAME",
    "AllegationFlattened",
    "UnknownEpistemicStatus",
    "assert_not_flattened",
    "flattening_findings",
    "is_factual",
    "render_event_phrase",
]
