# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `parsing` CLI surface for the layered stack (§24, SIG-ENG-013): `classify` (per
member for a ZIP), `layers`, and `reason` (normalize + reverse)."""

from __future__ import annotations

from pathlib import Path

from parsing.cli import main

_MIXED = Path(__file__).parent / "fixtures" / "records" / "mixed_response.zip"


def test_layers_lists_the_seven_layers_cheapest_first(capsys) -> None:
    assert main(["layers"]) == 0
    out = capsys.readouterr().out
    assert "structured_import" in out
    assert out.index("structured_import") < out.index("human_transcription")


def test_reason_normalizes_and_reports_signal(capsys) -> None:
    assert main(["reason", "constrained_dropdown", "Criminal Investigation"]) == 0
    out = capsys.readouterr().out
    assert "criminal_investigation" in out
    assert "signal=strong" in out


def test_reason_reverse_lists_variants(capsys) -> None:
    assert main(["reason", "free_text", "--reverse", "traffic_enforcement"]) == 0
    out = capsys.readouterr().out
    assert "traffic stop" in out


def test_reason_reverse_unknown_code_is_a_nonzero_exit(capsys) -> None:
    assert main(["reason", "free_text", "--reverse", "no_such_code"]) == 2


def test_classify_reports_per_member_for_a_mixed_archive(capsys) -> None:
    assert main(["classify", str(_MIXED)]) == 0
    out = capsys.readouterr().out
    assert "ZIP archive, 6 member(s)" in out
    assert "scanned_fax.tiff" in out and "ocr" in out
    assert "protected.pdf" in out and "human_transcription" in out
    assert "native_export.xlsx" in out and "multi_sheet=True" in out


def test_classify_reports_a_single_file(capsys, tmp_path) -> None:
    csv = tmp_path / "roster.csv"
    csv.write_bytes(b"agency,cameras\nOKC PD,12\n")
    assert main(["classify", str(csv)]) == 0
    out = capsys.readouterr().out
    assert "csv" in out and "structured_import" in out


def test_no_subcommand_prints_help_and_exits_zero(capsys) -> None:
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()
