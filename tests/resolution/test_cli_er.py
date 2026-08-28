# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The probabilistic-ER CLI subcommands (SIG-ENG-013): `er-match` prints PROPOSED
proposals with their weights, and `block-size` sizes an equijoin blocking rule and
reports acceptance/rejection (SIG-IDENT-021/023/025)."""

from __future__ import annotations

import json

import pytest
from resolution.cli import main

_RECORDS = [
    {
        "unique_id": "b1",
        "normalized_name": "los angeles police department",
        "name_first_token": "los",
        "state": "CA",
        "organization_class": "us.le.municipal_police",
    },
    {
        "unique_id": "b2",
        "normalized_name": "los angeles police dept",
        "name_first_token": "los",
        "state": "CA",
        "organization_class": "us.le.municipal_police",
    },
    {
        "unique_id": "c1",
        "normalized_name": "harris county sheriff office",
        "name_first_token": "harris",
        "state": "TX",
        "organization_class": "us.le.sheriff",
    },
]


def _write(tmp_path, records) -> str:
    path = tmp_path / "records.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return str(path)


def test_er_match_prints_proposals(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["er-match", _write(tmp_path, _RECORDS)])
    out = capsys.readouterr().out
    assert code == 0
    assert "b1 ~ b2" in out
    assert "review" in out  # the PROPOSED disposition
    assert "weight" in out


def test_block_size_accepts_a_selective_rule(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["block-size", _write(tmp_path, _RECORDS), "state,name_first_token"])
    out = capsys.readouterr().out
    assert code == 0
    assert "accepted" in out


def test_block_size_rejects_state_alone(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["block-size", _write(tmp_path, _RECORDS), "state"])
    out = capsys.readouterr().out
    assert code == 2
    assert "rejected" in out


def test_er_match_on_no_matches_is_graceful(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    lonely = [_RECORDS[2]]  # a single record → no pairs to score
    code = main(["er-match", _write(tmp_path, lonely)])
    out = capsys.readouterr().out
    assert code == 0
    assert "no tier-4/5 proposals" in out
