# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Parser-drift defences (§24.3): committed fixtures fail a test when a parser's output
drifts (SIG-PARSE-007), and a structural canary *alerts* — never silently drops — when a
live sample's shape drifts (SIG-PARSE-008, R11)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from parsing.drift import (
    EACH,
    FixtureCase,
    ParserDrift,
    StructuralExpectation,
    assert_no_drift,
    check_fixtures,
    run_canary,
    structural_findings,
)

_CANARY = Path(__file__).parent / "fixtures" / "canary"


def _parse_csv_first_row(data: bytes) -> list[str]:
    """A tiny stand-in parser: the header cells of a CSV."""
    return data.decode().splitlines()[0].split(",")


_FIXTURE = FixtureCase(
    name="roster-header",
    input_bytes=b"agency,cameras\nOKC PD,12\n",
    expected=["agency", "cameras"],
)


def test_committed_fixture_passes_for_an_unchanged_parser() -> None:
    results = check_fixtures(_parse_csv_first_row, [_FIXTURE])
    assert [r.passed for r in results] == [True]
    assert_no_drift(_parse_csv_first_row, [_FIXTURE])  # does not raise


def test_a_drifted_parser_fails_the_fixture_assertion() -> None:
    # SIG-PARSE-007 / AC5: an upstream redesign (or careless parser edit) fails loudly.
    def drifted(data: bytes) -> list[str]:
        return data.decode().splitlines()[0].split(";")  # wrong delimiter

    results = check_fixtures(drifted, [_FIXTURE])
    assert results[0].passed is False
    assert "roster-header" in results[0].failure_line()
    with pytest.raises(ParserDrift, match="1 parser fixture\\(s\\) drifted"):
        assert_no_drift(drifted, [_FIXTURE])


# The structural expectations the records-index parser depends on.
_EXPECTATIONS = [
    StructuralExpectation("a top-level records list is present", ("records",)),
    StructuralExpectation("every record has an id", ("records", EACH, "id")),
    StructuralExpectation("every record has an attachments list", ("records", EACH, "attachments")),
    StructuralExpectation(
        "every attachment has a name", ("records", EACH, "attachments", EACH, "name")
    ),
]


def test_canary_is_clean_on_the_expected_shape() -> None:
    sample = json.loads((_CANARY / "records_index_ok.json").read_text())
    report = run_canary("records_index", sample, _EXPECTATIONS)
    assert report.findings == ()
    assert report.alerted is False


def test_canary_alerts_and_does_not_drop_on_structural_drift() -> None:
    # SIG-PARSE-008: the live shape changed (`attachments`→`files`, `name`→`filename`); the
    # canary reports the violated expectations rather than silently accepting the new shape.
    sample = json.loads((_CANARY / "records_index_drift.json").read_text())
    report = run_canary("records_index", sample, _EXPECTATIONS)
    assert report.alerted is True
    assert "every record has an attachments list" in report.findings
    assert "every attachment has a name" in report.findings
    # It alerts — it does not raise or drop — so the nightly job decides what to do.
    assert isinstance(report.findings, tuple)


def test_structural_findings_handles_missing_top_level_and_non_list() -> None:
    assert structural_findings({}, _EXPECTATIONS) == [
        "a top-level records list is present",
        "every record has an id",
        "every record has an attachments list",
        "every attachment has a name",
    ]
    # EACH over a non-list is a violation, not a crash.
    assert structural_findings({"records": {"id": 1}}, [_EXPECTATIONS[1]]) == [
        "every record has an id"
    ]
