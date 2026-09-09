# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Epistemically-honest rendering of accountability events (§11.17, SIG-ONTO-038, P13.1).

The agentic AC of the ticket: a surface/render test asserts an
alleged/disputed/retracted event is NEVER phrased as a confirmed fact (OL-2E-AA-05).
"""

from __future__ import annotations

import pytest
from exports.accountability import (
    EPISTEMIC_STATUSES,
    FACTUAL_STATUSES,
    AllegationFlattened,
    UnknownEpistemicStatus,
    assert_not_flattened,
    flattening_findings,
    is_factual,
    render_event_phrase,
)
from support import load_schemaview

_NON_FACTUAL = sorted(EPISTEMIC_STATUSES - FACTUAL_STATUSES)


# --- OL-2E-AA-05: an allegation never renders with a factual verb ------------


@pytest.mark.parametrize("status", ["alleged", "disputed", "retracted"])
def test_the_three_named_non_factual_statuses_never_render_as_a_bare_fact(status: str) -> None:
    rendered = render_event_phrase(
        "Oklahoma City PD", status, event_type="wrongful_arrest", detail="involving ALPR data"
    )
    low = rendered.lower()
    # the epistemic qualifier is on the surface (SIG-ONTO-038)...
    assert status in low
    # ...and the event is NOT asserted as a bare fact (OL-2E-AA-05).
    for factual in ("happened", "occurred", "took place"):
        assert factual not in low
    assert flattening_findings(status, rendered) == []


@pytest.mark.parametrize("status", _NON_FACTUAL)
def test_every_non_factual_status_renders_hedged(status: str) -> None:
    rendered = render_event_phrase("An agency", status, event_type="data_breach")
    assert flattening_findings(status, rendered) == []


@pytest.mark.parametrize("status", sorted(FACTUAL_STATUSES))
def test_a_confirmed_or_adjudicated_event_may_state_the_fact(status: str) -> None:
    assert is_factual(status)
    rendered = render_event_phrase("A court", status, event_type="wrongful_arrest")
    assert flattening_findings(status, rendered) == []


# --- the mechanical guard rejects a flattened allegation ---------------------


def test_the_guard_rejects_an_allegation_phrased_as_a_fact() -> None:
    with pytest.raises(AllegationFlattened):
        assert_not_flattened("alleged", "The wrongful arrest occurred.")
    with pytest.raises(AllegationFlattened):
        assert_not_flattened("disputed", "The data breach happened in 2024.")
    with pytest.raises(AllegationFlattened):
        # confirming an allegation is the precise flattening OL-2E-AA-05 forbids.
        assert_not_flattened("alleged", "It is confirmed that the breach took place.")


def test_the_guard_requires_the_epistemic_qualifier_on_the_surface() -> None:
    # A sentence with no hedge word for a non-factual status is a flattening even
    # without a banned verb — epistemic_status MUST be rendered (SIG-ONTO-038).
    problems = flattening_findings("alleged", "The agency was the subject of a wrongful arrest.")
    assert problems


def test_a_true_confirmed_fact_passes_the_guard() -> None:
    assert_not_flattened("confirmed", "It is confirmed that the audit finding occurred.")


def test_an_unknown_status_is_rejected() -> None:
    with pytest.raises(UnknownEpistemicStatus):
        render_event_phrase("X", "probably_true")


# --- lock-step with the frozen ontology enum --------------------------------


def test_render_status_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    assert EPISTEMIC_STATUSES == set(sv.get_enum("EpistemicStatus").permissible_values)
