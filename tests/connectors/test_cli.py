# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The connectors CLI: stages / gate / export-check (SIG-INGEST-014/021, SIG-LIC-010)."""

from __future__ import annotations

import pytest
from connectors.cli import main


def test_stages_lists_the_eight_stages(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stages"]) == 0
    out = capsys.readouterr().out
    for name in ("discover", "fetch", "capture", "parse", "extract", "normalize", "link", "load"):
        assert name in out


def test_list_connectors_includes_the_osm_connector(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # P04.2 lands the first source connector on the P04.1 registration seam
    # (SIG-INGEST-021): `osm` now appears in the CLI listing.
    assert main(["list-connectors"]) == 0
    assert "osm" in capsys.readouterr().out.split()


def test_list_connectors_includes_the_atlas_connector(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # P04.3 lands the second source connector on the same seam (SIG-INGEST-021):
    # `atlas` now appears in the CLI listing.
    assert main(["list-connectors"]) == 0
    assert "atlas" in capsys.readouterr().out.split()


def test_gate_reports_refused_for_a_gated_source(capsys: pytest.CaptureFixture[str]) -> None:
    # No seeded source is permitted at this phase => the gate refuses.
    code = main(["gate", "--source", "eyes_on_flock"])
    assert code == 1
    assert "REFUSED" in capsys.readouterr().out


def test_gate_unknown_source_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["gate", "--source", "no_such_source"]) == 2


def test_export_check_passes_on_the_seeded_registry(capsys: pytest.CaptureFixture[str]) -> None:
    # SIG-LIC-010: each compartment in the seeded registry exports under one licence.
    assert main(["export-check"]) == 0
    assert "export-check OK" in capsys.readouterr().out


def test_validate_still_runs(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate"]) == 0
    assert "self-checks OK" in capsys.readouterr().out
