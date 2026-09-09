# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `inference` CLI wires the four §32 surfaces (P19.5, LD-F15)."""

from __future__ import annotations

import json

import pytest
from inference.cli import main

_SUBCOMMANDS = ("coverage", "access-paths", "completeness", "freshness")


@pytest.mark.parametrize("cmd", _SUBCOMMANDS)
def test_subcommand_help_exits_zero(cmd: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([cmd, "--help"])
    assert exc.value.code == 0


@pytest.mark.parametrize("cmd", _SUBCOMMANDS)
def test_subcommand_default_demo_exits_zero_and_prints_json(
    cmd: str, capsys: pytest.CaptureFixture[str]
) -> None:
    # Each subcommand runs its built-in OKC-slice demonstration and prints JSON.
    assert main([cmd]) == 0
    out = capsys.readouterr().out
    json.loads(out)  # valid JSON on stdout


def test_coverage_reports_searched_not_found_for_absent_candidates(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["coverage"]) == 0
    records = json.loads(capsys.readouterr().out)
    # tulsapd/normanpd are candidates without the predicate present → negative space.
    kinds = {r["absence_kind"] for r in records}
    assert "searched_not_found" in kinds


def test_completeness_refuses_a_reality_denominator(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    from inference.completeness import ProhibitedEstimateError

    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "method": "counted_with_denominator",
                "named_denominator": "true population",
                "value": 0.9,
            }
        )
    )
    with pytest.raises(ProhibitedEstimateError):
        main(["completeness", "--input", str(bad)])
