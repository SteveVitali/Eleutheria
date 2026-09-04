# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The parsing-stage CLI (SIG-ENG-013): `extract` runs the model-assisted-extraction
scaffolding and prints R6/`PROPOSED` proposals (rejecting a hallucinated span), and
`sampling` reports the per-type review rate and demotion decision (SIG-LLM-003/004/006)."""

from __future__ import annotations

import json

import pytest
from parsing.cli import main

_CAPTURE = "Acme Police Department operates 12 ALPR cameras on Main Street."


def _job(text: str) -> dict[str, object]:
    start = _CAPTURE.index(text)
    return {
        "capture_text": _CAPTURE,
        "model_id": "acme-extract-v2",
        "prompt_version": "claims-2026-08",
        "extraction_type": "structured_claim",
        "items": [
            {
                "subject": "acme_pd",
                "predicate": "operates",
                "value": "ALPR",
                "span": {
                    "text": text,
                    "start": start,
                    "end": start + len(text),
                    "locator": {"byte_range": [start]},
                },
            }
        ],
    }


def _write(tmp_path, job) -> str:
    path = tmp_path / "job.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    return str(path)


def test_extract_prints_proposed_claims(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["extract", _write(tmp_path, _job("ALPR cameras"))])
    out = capsys.readouterr().out
    assert code == 0
    assert "R6/PROPOSED" in out
    assert "writes_to_graph=False" in out


def test_extract_rejects_a_hallucinated_span(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    job = _job("ALPR cameras")
    job["items"][0]["span"]["text"] = "facial recognition"  # not in the capture
    code = main(["extract", _write(tmp_path, job)])
    out = capsys.readouterr().out
    assert code == 2
    assert "rejected" in out


def test_sampling_lists_policies(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["sampling"])
    out = capsys.readouterr().out
    assert code == 0
    assert "org_alias" in out
    assert "review_sample_rate" in out


def test_sampling_reports_demotion(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["sampling", "--type", "org_alias", "--accuracy", "0.1"])
    out = capsys.readouterr().out
    assert code == 0
    assert "human-only" in out
