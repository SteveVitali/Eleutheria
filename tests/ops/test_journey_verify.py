# SPDX-License-Identifier: Apache-2.0
"""Offline tests for the P32.24 investigation-journey verification harness
(SIG-FIND-007, ADR-143).

These cover the DB-free seams: the acceptance corpus's declared expectations,
the full ``sig.journey-portfolio/1`` run over the real ``build_release`` path,
the fail-closed behaviour when a released byte changes under the verifier, the
evidence-class discipline (nothing human-labelled passes without recorded
volunteers), and the CLI wiring. The durable receipt→moderation→canonical-
correction journey is Docker-gated in ``tests/db/test_journey_portfolio_pg.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ops import journey_verify as jv

CANDIDATE = (
    Path(__file__).resolve().parents[2] / "docs" / "build" / "reports" / "p32.23a-release-candidate"
)


@pytest.fixture(scope="module")
def portfolio(tmp_path_factory) -> dict:
    """One shared portfolio run — the corpus build + release + stage is the
    expensive part; the checks below all read the SAME emitted evidence."""
    out = tmp_path_factory.mktemp("jv")
    return jv.run_portfolio(candidate_dir=CANDIDATE, out_dir=out)


def _check(portfolio: dict, check_id: str) -> dict:
    for c in portfolio["checks"]:
        if c["id"] == check_id:
            return c
    raise AssertionError(f"check {check_id} absent from the portfolio")


# ---------------------------------------------------------------------------
# The corpus itself — declared expectations, real-contract shape.
# ---------------------------------------------------------------------------


def test_corpus_declares_the_representative_cases(tmp_path: Path) -> None:
    corpus = jv.build_acceptance_export(tmp_path / "export")
    assert corpus["schema"] == jv.CORPUS_SCHEMA
    cases = corpus["cases"]
    # representative tail / unlocated / withheld / ghost-claim cases are all
    # declared — a corpus that forgets one fails here
    assert len(cases["unlocated_entities"]) == 5
    assert len(cases["unreported_jurisdiction_entities"]) == 5
    assert len(cases["unresolved_point_entities"]) == 3
    assert cases["withheld_entity"] == jv.WITHHELD_ENTITY
    assert cases["withheld_claim"] == jv.WITHHELD_CLAIM
    assert cases["denied_entity"] == jv.DENIED_ENTITY
    assert cases["ghost_entity"] == jv.GHOST_ENTITY
    assert len(corpus["edges"]) == 3
    assert {e["access_kind"] for e in corpus["edges"]} == {
        "configured_access",
        "observed_use",
        "declared_policy",
    }
    # the declared interpretive answers exist for the unknown-state cases
    for key in ("configured_vs_observed", "unlocated_claim", "withheld"):
        assert corpus["expected_answers"][key]
    # the export is the real-contract shape build_release consumes
    exp_dir = tmp_path / "export"
    assert (exp_dir / "manifest.json").exists()
    assert (exp_dir / f"{jv.COMP_A}/sites.jsonl").exists()
    assert (exp_dir / f"{jv.COMP_A}/record_claims.jsonl").exists()
    for name in ("evidence.json", "dossiers.json", "network.json"):
        assert (exp_dir / "web" / name).exists(), name


# ---------------------------------------------------------------------------
# The full portfolio — verdict, evidence classes, digest pinning.
# ---------------------------------------------------------------------------


def test_portfolio_is_green_with_no_failed_check(portfolio: dict) -> None:
    assert portfolio["schema"] == jv.PORTFOLIO_SCHEMA
    assert portfolio["requirement"] == "SIG-FIND-007"
    assert portfolio["verdict"] == "pass"
    failed = [c for c in portfolio["checks"] if c["status"] == "fail"]
    assert failed == []


def test_portfolio_pins_the_candidate_it_verified(portfolio: dict) -> None:
    subj = portfolio["subject"]
    assert (
        subj["publication_id"]
        == "p-17b713cee4f4f605f73d72c6b13c824499d0d35005e4295f86c989e52dc98587"
    )
    assert subj["evaluation"]["status"] == "deferred"
    assert subj["evaluation"]["decision"] is None
    assert subj["published"] is False
    assert subj["provisional"] is True


def test_every_check_names_an_owner_and_a_landing(portfolio: dict) -> None:
    # the acceptance rule: every check — pass or otherwise — must be closable
    for c in portfolio["checks"]:
        assert c["owner"], c["id"]
        assert c["landing"], c["id"]
        assert c["evidence"], c["id"]


def test_journey_legs_cover_the_three_documented_journeys(portfolio: dict) -> None:
    ids = {c["id"] for c in portfolio["checks"]}
    assert {
        "A.records_reachable",
        "A.search",
        "A.evidence_anchors",
        "A.dossiers",
        "A.static_vs_json",
    } <= ids
    assert {"B.edges_typed", "B.edge_claims_resolve", "B.bounded"} <= ids
    assert {
        "C.receipt_to_moderation",
        "C.apply_canonical_once",
        "C.publish_linkage",
        "C.citation_persists",
    } <= ids


def test_candidate_surface_reports_the_honest_zero(portfolio: dict) -> None:
    c = _check(portfolio, "candidate.record_surface")
    assert c["status"] == "not_applicable"  # never a fabricated record pass
    assert "output_records=0" in c["detail"]
    n = _check(portfolio, "B.candidate_network")
    assert n["status"] == "not_applicable"
    assert "nodes=0" in n["detail"]


def test_eval_and_human_sessions_stay_deferred(portfolio: dict) -> None:
    ev = _check(portfolio, "B.eval_deferred")
    assert ev["status"] == "deferred"
    assert "2026-10-19" in ev["detail"]
    ux = _check(portfolio, "UX.independent_sessions")
    assert ux["status"] == "deferred"
    assert ux["evidence_kind"] == "independent_human"
    assert "D-R10-USERS-1" in ux["owner"]


def test_intake_checks_are_marked_verified_by_test(portfolio: dict) -> None:
    """Without a supplied PG proof the intake legs are honestly marked
    verified_by_test — never claimed as run in this process."""
    for cid in ("C.receipt_to_moderation", "C.apply_canonical_once"):
        assert _check(portfolio, cid)["status"] == "verified_by_test"


def _fake_build(tmp_path: Path) -> SimpleNamespace:
    """A build_release-shaped namespace over a REAL emitted acceptance
    release — what _journey_c_checks reads."""
    from exports.release import build_release

    jv.build_acceptance_export(tmp_path / "export")
    return build_release(tmp_path / "export", tmp_path / "rel", renderer_revision="t")


def test_intake_proof_is_folded_in_when_supplied(tmp_path: Path) -> None:
    build = _fake_build(tmp_path)
    proof = {
        "schema": jv.INTAKE_PROOF_SCHEMA,
        "steps": [
            {"step": "submit_durable", "ok": True},
            {"step": "survives_restart", "ok": True},
            {"step": "applied_canonical", "ok": True},
            {"step": "exactly_once", "ok": True},
            {"step": "published_linkage", "ok": True},
            {"step": "receiver_no_fact_write", "ok": True},
            {"step": "resolved_state", "ok": True},
        ],
    }
    checks = jv._journey_c_checks(build, intake_proof=proof)
    by_id = {c["id"]: c for c in checks}
    assert by_id["C.receipt_to_moderation"]["status"] == "pass"
    assert (
        "submit_durable" not in by_id["C.receipt_to_moderation"]["detail"]
        or "steps ok" in by_id["C.receipt_to_moderation"]["detail"]
    )


def test_intake_proof_with_a_failed_step_fails_the_check(tmp_path: Path) -> None:
    build = _fake_build(tmp_path)
    proof = {
        "schema": jv.INTAKE_PROOF_SCHEMA,
        "steps": [{"step": "submit_durable", "ok": False, "detail": "conn refused"}],
    }
    checks = jv._journey_c_checks(build, intake_proof=proof)
    by_id = {c["id"]: c for c in checks}
    assert by_id["C.receipt_to_moderation"]["status"] == "fail"
    assert by_id["C.receipt_to_moderation"]["owner"]


# ---------------------------------------------------------------------------
# Fail-closed behaviour — a mutated released byte is detected.
# ---------------------------------------------------------------------------


def test_tampered_release_fails_the_integrity_check(tmp_path: Path) -> None:
    build = _fake_build(tmp_path)
    pub = build.publication_id
    index_path = build.out_dir / f"r/{pub}/c/{jv.COMP_A}/records.index.jsonl"
    first = index_path.read_bytes()
    assert first
    # corrupt one released byte — the integrity manifest must disagree
    index_path.write_bytes(first + b" ")
    from exports.release import validate_release

    report = validate_release(build.out_dir)
    assert report.state != "complete"
    assert any("records.index.jsonl" in f for f in report.failures)


def test_expected_answer_is_recorded_for_the_interpretive_checks(
    portfolio: dict,
) -> None:
    for cid in ("A.search", "B.edges_typed", "A.evidence_anchors"):
        assert _check(portfolio, cid)["expected_answer"]


# ---------------------------------------------------------------------------
# The markdown renderer keeps the honest-gaps section + the deferrals.
# ---------------------------------------------------------------------------


def test_markdown_discloses_the_gap_class(portfolio: dict) -> None:
    md = jv.render_portfolio_markdown(portfolio)
    assert "sig.journey-portfolio/1" in md
    assert "SIG-FIND-007" in md
    assert "not_applicable" in md
    assert "deferred" in md
    assert "D-R10-USERS-1" in md
    # the honest-gaps section exists and carries owner→landing pairs
    assert "## Honest gaps" in md


def test_portfolio_writes_the_emitted_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "report"
    jv.run_portfolio(candidate_dir=CANDIDATE, out_dir=out)
    for name in ("JOURNEY_PORTFOLIO.json", "JOURNEY_PORTFOLIO.md"):
        assert (out / name).exists(), name
    assert (out / "corpus_export" / "manifest.json").exists()
    assert (out / "corpus_release").is_dir()


# ---------------------------------------------------------------------------
# The CLI verb is wired and fails loudly.
# ---------------------------------------------------------------------------


def test_cli_requires_out() -> None:
    from ops.cli import main

    with pytest.raises(SystemExit):
        main(["journey-verify"])


def test_cli_runs_and_reports(tmp_path: Path, capsys) -> None:
    from ops.cli import main

    rc = main(["journey-verify", "--out", str(tmp_path / "report")])
    assert rc == 0
    captured = capsys.readouterr()
    assert "verdict=pass" in captured.out
    assert (tmp_path / "report" / "JOURNEY_PORTFOLIO.json").exists()


def test_cli_journey_intake_requires_publication(capsys) -> None:
    from ops.cli import main

    assert main(["journey-intake"]) == 2
    err = capsys.readouterr().err
    assert "--publication" in err


def test_cli_journey_verify_fails_when_a_check_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    """A forced check failure lands owner+landing on the failing row and the
    verb exits 1 — the report never emits a bare 'fail' with no owner."""
    from ops.cli import main

    monkeypatch.setattr(
        jv,
        "_walkthrough_checks",
        lambda *a, **k: [
            {
                "id": "WT.sabotaged",
                "journey": "walkthrough",
                "title": "forced",
                "evidence_kind": "agent_walkthrough",
                "status": "fail",
                "detail": "forced failure",
                "expected_answer": "x",
                "evidence": ["sabotage"],
                "owner": "P32.24",
                "landing": "docs/build/reports/p32.24-investigation-journey-verification/",
            }
        ],
    )
    rc = main(["journey-verify", "--out", str(tmp_path / "report")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL WT.sabotaged" in out
    assert "owner=P32.24" in out
    portfolio = json.loads((tmp_path / "report" / "JOURNEY_PORTFOLIO.json").read_text())
    assert portfolio["verdict"] == "fail"


# ---------------------------------------------------------------------------
# volunteers are NEVER implicit — the human gate stays shut
# ---------------------------------------------------------------------------


def test_independent_sessions_need_recorded_volunteers() -> None:
    check = jv._check(
        "UX.independent_sessions",
        "UX",
        "moderated usability sessions",
        "independent_human",
        "deferred",
        "none recorded",
        owner="D-R10-USERS-1",
        landing="docs/build/reports/p32.24-investigation-journey-verification/USABILITY_TASK_PROTOCOL.md",
    )
    assert check["evidence_kind"] == "independent_human"
    assert check["status"] == "deferred"


def test_a_human_check_cannot_pass_without_disposition_owner(tmp_path: Path) -> None:
    """The honest-gaps rule is structural: a deferred/not_applicable/fail row
    with no owner+landing cannot even be constructed."""
    with pytest.raises(jv.PortfolioError):
        jv._check(
            "UX.fake",
            "UX",
            "fabricated session",
            "independent_human",
            "deferred",
            "no owner",
        )
