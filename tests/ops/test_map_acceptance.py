# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.63 (K1 MAP-07): the map-acceptance leg declaration's contract tests.

The module is the committed declaration the deferred candidate/live legs
ride on — the tests pin the contract, never a living-record value: the leg
set names every leg K1 §9.5/§9.6 requires, each gated leg carries its
precondition + the ticket's verbatim re-run prompt, ``check`` verifies the
committed machinery without running anything, and ``run`` queues exit 42 on
every gated leg (prepared_not_executed — never a fabricated pass).
"""

from __future__ import annotations

import json

import pytest
from ops.map_acceptance import LEGS, RERUN_PROMPT

from ops import map_acceptance


def test_plan_shape() -> None:
    doc = map_acceptance.plan()
    assert doc["schema"] == "sig.map-acceptance/1"
    assert doc["ticket"] == "P37.63"
    assert doc["posture"] == "prepared_not_executed"
    assert doc["production_mutations"] == "none"
    assert doc["rerun_prompt"] == RERUN_PROMPT
    assert "live_verification=true" in str(doc["rerun_prompt"])
    legs = doc["legs"]
    assert [lg["leg_id"] for lg in legs] == [lg.leg_id for lg in LEGS]


def test_the_ticket_legs_are_all_named() -> None:
    ids = {lg.leg_id for lg in LEGS}
    # Deterministic legs — what this dispatch itself exercises.
    assert "journeys-fixture" in ids
    assert "budgets-fixture" in ids
    # The release-candidate legs K1 §9.4/§15 names.
    assert "candidate-tiles" in ids
    assert "candidate-lhci" in ids
    # The K1 §9.5/§9.6 post-promotion live legs.
    assert "live-journeys" in ids
    assert "live-lhci" in ids
    assert "live-tiles" in ids
    assert "cost-7d" in ids


def test_every_gated_leg_carries_its_precondition() -> None:
    gated = [lg for lg in LEGS if lg.stage != "deterministic"]
    assert gated, "the declaration must carry the deferred legs"
    for leg in gated:
        assert leg.precondition, f"{leg.leg_id} names no precondition"
        assert leg.command, f"{leg.leg_id} names no command"
        assert leg.artifact, f"{leg.leg_id} names no artifact"
    # The live legs all ride the post-P37.65b window.
    for leg in (lg for lg in LEGS if lg.stage == "live"):
        assert "P37.65b" in leg.precondition or "promotes" in leg.precondition


def test_leg_ids_are_unique_and_stages_valid() -> None:
    ids = [lg.leg_id for lg in LEGS]
    assert len(ids) == len(set(ids))
    assert {lg.stage for lg in LEGS} <= {"deterministic", "candidate", "live"}


def test_main_plan_prints_the_declaration(capsys) -> None:
    assert map_acceptance.main(["plan"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["schema"] == "sig.map-acceptance/1"


def test_main_check_verifies_committed_machinery(capsys) -> None:
    assert map_acceptance.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "committed legs present" in out


def test_run_queues_every_gated_leg(capsys) -> None:
    for leg in (lg for lg in LEGS if lg.stage != "deterministic"):
        rc = map_acceptance.main(["run", "--leg", leg.leg_id])
        assert rc == 42, f"{leg.leg_id} must queue exit 42"
        err = capsys.readouterr().err
        assert leg.precondition.split(";")[0] in err or "precondition" in err
        assert "live_verification=true" in err


def test_run_unknown_leg_is_a_usage_error(capsys) -> None:
    assert map_acceptance.main(["run", "--leg", "nonsense"]) == 2
    assert "unknown leg" in capsys.readouterr().err


@pytest.mark.parametrize("leg_id", [lg.leg_id for lg in LEGS if lg.stage == "deterministic"])
def test_deterministic_legs_have_runnable_committed_commands(leg_id: str) -> None:
    # The command a deterministic leg names must resolve to a committed
    # script — a renamed carrier file is a real acceptance gap, not prose.
    leg = next(lg for lg in LEGS if lg.leg_id == leg_id)
    assert "national_budget_leg.sh" in leg.command
