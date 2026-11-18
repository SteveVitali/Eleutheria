# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.64 (K2 GX-10 + K6 VIZ-05): the explore-acceptance leg declaration's
contract tests.

The module is the committed declaration the deferred post-promotion verify
leg rides on — the tests pin the contract, never a living-record value: the
leg set names every leg the ticket requires, each gated leg carries its
precondition + the ticket's verbatim re-run prompt, ``check`` verifies the
committed machinery without running anything, and ``run`` queues exit 42 on
every gated leg (prepared_not_executed — never a fabricated pass).
"""

from __future__ import annotations

import pytest
from ops import explore_acceptance
from ops.explore_acceptance import LEGS, RERUN_PROMPT


def test_plan_shape() -> None:
    doc = explore_acceptance.plan()
    assert doc["schema"] == "sig.explore-acceptance/1"
    assert doc["ticket"] == "P37.64"
    assert doc["posture"] == "prepared_not_executed"
    assert doc["production_mutations"] == "none"
    assert doc["rerun_prompt"] == RERUN_PROMPT
    assert "live_verification=true" in str(doc["rerun_prompt"])
    legs = doc["legs"]
    assert [lg["leg_id"] for lg in legs] == [lg.leg_id for lg in LEGS]


def test_the_ticket_legs_are_all_named() -> None:
    ids = {lg.leg_id for lg in LEGS}
    # Deterministic legs — what this dispatch itself exercises.
    assert "dist-sweep" in ids
    assert "journeys" in ids
    assert "budgets" in ids
    # The gated leg — the plan's verbatim `1: verify after P37.65b promotes`.
    assert "live-verify" in ids
    live = next(lg for lg in LEGS if lg.leg_id == "live-verify")
    assert live.stage == "live"
    assert "P37.65b" in live.precondition
    assert "live_verification=true" in live.precondition


def test_check_verifies_committed_machinery() -> None:
    assert explore_acceptance.check() == 0


def test_run_queues_the_gated_leg(capsys: pytest.CaptureFixture[str]) -> None:
    rc = explore_acceptance.run("live-verify")
    assert rc == 42
    err = capsys.readouterr().err
    assert "queues" in err
    assert RERUN_PROMPT in err


def test_run_rejects_unknown_leg(capsys: pytest.CaptureFixture[str]) -> None:
    assert explore_acceptance.run("no-such-leg") == 2
    assert "unknown leg" in capsys.readouterr().err
