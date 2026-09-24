# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The France acceptance module (P24.6 / JURIS.2 / GL-JURIS-01).

These pin the *shape* of the second jurisdiction's own acceptance queries —
France-shaped subjects and questions (never relabelled OKC ids), the fixture
subset that must pass, and the honest `blocked` rows for the HG-03/HG-04-pending
carriers. The real run is `run_france.sh`; a stub API stands in for the composed
stack here.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import acceptance.live_api_france as fr

REPO_ROOT = Path(__file__).resolve().parents[2]


class _StubApi(fr._Api):
    """A deterministic stand-in for the composed France stack (no network)."""

    def __init__(self) -> None:
        self.base = "stub://france"

    def get(self, path: str) -> tuple[int, Any]:
        def fact(subject: str, predicate: str, value: Any) -> tuple[int, Any]:
            return 200, {
                "fact": {
                    "subject_id": subject,
                    "predicate_id": predicate,
                    "envelope": {
                        "value": value,
                        "resolution_status": "RESOLVED",
                        "agreement": "UNCONTESTED",
                        "considered_claim_ids": ["00000000-0000-0000-0000-000000000001"],
                    },
                }
            }

        table = {
            f"/v1/resolution/{fr.DEPLOYMENT}/authorization_state": fact(
                fr.DEPLOYMENT, "authorization_state", "authorized"
            ),
            f"/v1/resolution/{fr.DEPLOYMENT}/statutory_citation": fact(
                fr.DEPLOYMENT,
                "statutory_citation",
                "Code de la sécurité intérieure, art. L251-1 à L255-1",
            ),
            f"/v1/resolution/{fr.DEPLOYMENT}/deployment_exists": fact(
                fr.DEPLOYMENT, "deployment_exists", True
            ),
            f"/v1/resolution/{fr.DEPLOYMENT}/implements_technology": fact(
                fr.DEPLOYMENT, "implements_technology", "camera-fixed-cctv"
            ),
            f"/v1/resolution/{fr.CONTRACT}/contract_value": fact(
                fr.CONTRACT, "contract_value", 50754
            ),
            "/v1/search?q=france": (
                200,
                {
                    "results": [
                        {"entity_id": "e1", "label": "Police municipale de Gex"},
                        {"entity_id": "e2", "label": "Police Municipale de la Ville de Gex"},
                    ]
                },
            ),
        }
        return table.get(path, (404, None))


def _france_export(tmp_path: Path) -> Path:
    """Build the real France export into tmp_path (deterministic, in-process)."""
    from exports.cli import _run_build

    rc = _run_build(
        None,
        str(tmp_path / "export"),
        zenodo_dry_run=False,
        store=None,
        base_url="",
        cdn_url="",
        jurisdiction="france",
    )
    assert rc == 0
    return tmp_path / "export"


def test_france_queries_are_france_shaped_not_okc() -> None:
    # The second jurisdiction is not a relabelled copy: no OKC ids or the US
    # acceptance questions anywhere in the module.
    blob = json.dumps({"q": fr._QUESTIONS, "carriers": fr._CARRIERS, "dep": fr.DEPLOYMENT}).lower()
    assert "okc" not in blob and "flock" not in blob
    assert "299" not in blob
    assert "fr.cada" in json.dumps(fr._CARRIERS) or "cada" in blob
    for qid, question in fr._QUESTIONS.items():
        assert qid.startswith("FR-")
        assert question.endswith("?")


def test_france_fixture_subset_passes_against_the_stack(tmp_path: Path) -> None:
    export_dir = _france_export(tmp_path)
    api = _StubApi()
    queries = fr._run_queries(api, export_dir)
    subset = [q for q in queries if q.in_fixture_subset]
    assert all(q.status == "pass" for q in subset), [asdict(q) for q in subset]
    # The seven fixture-subset carriers: FR-1..FR-7.
    assert len(subset) == 7


def test_france_blocked_queries_carry_the_gate_commands() -> None:
    api = _StubApi()
    queries = fr._run_queries(api, Path("exports/out/france"))
    blocked = [q for q in queries if q.status == "blocked"]
    assert len(blocked) == 3  # FR-8/FR-9/FR-10 — the live-source carriers
    for q in blocked:
        assert "HG-03-pending" in q.blocker
        assert "--mode live" in q.blocker


def test_france_report_shape_and_summary(tmp_path: Path, monkeypatch) -> None:
    export_dir = _france_export(tmp_path)
    monkeypatch.setattr(fr, "_Api", lambda _url: _StubApi())
    report = fr.run_acceptance("stub://france", export_dir=export_dir)
    assert report.jurisdiction == "france"
    assert "HG-03" in report.mode or "shadow" in report.mode
    assert report.traversal["status"] == "pass"
    s = report.summary
    assert s["total"] == len(fr._QUESTIONS)
    assert s["passed"] == 7 and s["blocked"] == 3 and s["failed"] == 0
    assert s["fixture_subset_all_pass"] is True


def test_france_publication_gate_check_fails_loud_without_the_flag() -> None:
    # A dossier missing the FR-flagged officer-name row fails the FR-7 check —
    # the withholding is asserted, not assumed.
    api = _StubApi()
    empty_dir = Path("exports/out/atlantis")
    r = fr._run_queries(api, empty_dir)
    fr7 = next(q for q in r if q.id == "FR-7")
    assert fr7.status == "fail"


def test_france_main_writes_the_report(tmp_path: Path, monkeypatch) -> None:
    export_dir = _france_export(tmp_path)
    monkeypatch.setattr(fr, "_Api", lambda _url: _StubApi())
    out = tmp_path / "acceptance_france.json"
    rc = fr.main(["--api-url", "stub://france", "--out", str(out), "--export-dir", str(export_dir)])
    assert rc == 0
    report = json.loads(out.read_text())
    assert report["jurisdiction"] == "france"
    assert report["summary"]["fixture_subset_all_pass"] is True


def test_run_france_script_runs_the_france_acceptance() -> None:
    script = REPO_ROOT / "docs" / "build" / "tools" / "run_france.sh"
    text = script.read_text()
    assert "acceptance.live_api_france" in text
    assert "--export-dir" in text
