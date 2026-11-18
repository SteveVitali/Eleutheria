# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.68b (R11-K13-CAP-01, split b): the capstone-journalist leg
declaration's contract tests.

The module is the committed declaration the deferred live/operator legs ride
on — the tests pin the contract, never a living-record value: the leg set
names every leg the ticket requires (the J1–J5 battery at all four
viewport/JS cells, the committed-ledger cost read, the promoted-release and
operator halves), each gated leg carries its precondition + the ticket's
verbatim re-run prompt, ``check`` verifies the committed machinery without
running anything, and ``run`` queues exit 42 on every gated leg
(prepared_not_executed — never a fabricated pass). J4's durable ``/s/<pub>/``
half is pinned to ACT-24 (HG-11) and J5's diff to the activated
predecessor (CF-13) — the declaration names both, never quietly.
"""

from __future__ import annotations

import json

import pytest
from ops.capstone_journalist import LEGS, RERUN_PROMPT

from ops import capstone_journalist


def test_plan_shape() -> None:
    doc = capstone_journalist.plan()
    assert doc["schema"] == "sig.capstone-journalist/1"
    assert doc["ticket"] == "P37.68b"
    assert doc["posture"] == "prepared_not_executed"
    assert doc["production_mutations"] == "none"
    assert doc["rerun_prompt"] == RERUN_PROMPT
    assert "live_verification=true" in str(doc["rerun_prompt"])
    assert doc["journeys"] == ["J1", "J2", "J3", "J4", "J5"]
    assert doc["cells"] == ["1440-js", "390-js", "1440-nojs", "390-nojs"]
    legs = doc["legs"]
    assert [lg["leg_id"] for lg in legs] == [lg.leg_id for lg in LEGS]


def test_the_ticket_legs_are_all_named() -> None:
    ids = {lg.leg_id for lg in LEGS}
    # Deterministic legs — what this dispatch itself exercises.
    assert "journeys-fixture" in ids
    assert "cost-ledger" in ids
    # The promoted-release + operator halves K13 §8 / SIG-UI-081 name.
    assert "live-journeys" in ids
    assert "cost-read" in ids
    assert "walkthrough" in ids


def test_every_gated_leg_carries_its_precondition() -> None:
    gated = [lg for lg in LEGS if lg.stage != "deterministic"]
    assert gated, "the declaration must carry the deferred legs"
    for leg in gated:
        assert leg.precondition, f"{leg.leg_id} names no precondition"
        assert leg.command, f"{leg.leg_id} names no command"
        assert leg.artifact, f"{leg.leg_id} names no artifact"
    # The live legs all ride the promoted release.
    for leg in (lg for lg in LEGS if lg.stage == "live"):
        assert "P37.65" in leg.precondition or "promot" in leg.precondition


def test_the_journey_specific_gates_are_named() -> None:
    """J4's durable half rides ACT-24; J5's diff rides the predecessor."""
    live = next(lg for lg in LEGS if lg.leg_id == "live-journeys")
    assert "ACT-24" in live.precondition
    assert "predecessor" in live.precondition or "diff" in live.precondition
    gates = capstone_journalist.plan()["journey_gates"]
    assert "J4" in gates and "J5" in gates


def test_leg_ids_are_unique_and_stages_valid() -> None:
    ids = [lg.leg_id for lg in LEGS]
    assert len(ids) == len(set(ids))
    assert {lg.stage for lg in LEGS} <= {"deterministic", "candidate", "live", "operator"}


def test_main_plan_prints_the_declaration(capsys) -> None:
    assert capstone_journalist.main(["plan"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["schema"] == "sig.capstone-journalist/1"


def test_main_check_verifies_committed_machinery(capsys) -> None:
    assert capstone_journalist.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "committed legs present" in out


def test_run_queues_every_gated_leg(capsys) -> None:
    for leg in (lg for lg in LEGS if lg.stage != "deterministic"):
        rc = capstone_journalist.main(["run", "--leg", leg.leg_id])
        assert rc == 42, f"{leg.leg_id} must queue exit 42"
        err = capsys.readouterr().err
        assert "precondition" in err
        assert "live_verification=true" in err or "operator" in leg.precondition


def test_run_unknown_leg_is_a_usage_error(capsys) -> None:
    assert capstone_journalist.main(["run", "--leg", "nonsense"]) == 2
    assert "unknown leg" in capsys.readouterr().err


def test_cost_ledger_read_is_labelled_and_bounded(capsys) -> None:
    rc = capstone_journalist.main(["run", "--leg", "cost-ledger"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert doc["schema"] == "sig.capstone-cost-read/1"
    assert doc["ticket"] == "P37.68b"
    assert doc["ceiling_usd"] == 300.0
    # The committed ledger carries named labels; a pending row is reported,
    # never silently summed into the ceiling comparison.
    gcp = doc["gcp_cloud_account"]
    assert isinstance(gcp["pending_rows"], list)
    assert doc["verdict"]


@pytest.mark.parametrize("leg_id", [lg.leg_id for lg in LEGS if lg.stage == "deterministic"])
def test_deterministic_legs_have_committed_commands(leg_id: str) -> None:
    leg = next(lg for lg in LEGS if lg.leg_id == leg_id)
    assert leg.command
