# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.44 (CONF-09 / SIG-EVAL-003 + SIG-EVAL-006 + SIG-CONF-012): the mechanical
evaluation report.

The acceptance shape (the catalog's verbatim): the report carries numerator,
denominator, method and population per estimand. Human estimands are
``unavailable`` with named reasons — never substituted by mechanical or
agent evidence. Spine measures measure only what the latest completed
camera-site ER run recorded; a missing run is honest ``unavailable``, never
a fabricated figure. The corpus measures are real deterministic
measurements over the committed real-data regression corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exports import mech_eval

REPO = Path(__file__).resolve().parents[2]
CORPUS_PATH = REPO / "exports" / "src" / "exports" / "data" / "mech_eval_corpus.json"
RECORD_PATH = REPO / "exports" / "src" / "exports" / "data" / "mech_eval.json"


@pytest.fixture(scope="module")
def corpus_doc() -> dict:
    return json.loads(CORPUS_PATH.read_text())


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(RECORD_PATH.read_text())


def _run(
    *,
    checked: int = 4,
    failures: int = 0,
    namespaces: dict | None = None,
    links: list | None = None,
    corroboration: dict | None = None,
) -> dict:
    """A fabricated ``read_resolved_site_runs``-shaped run (no DB)."""
    return {
        "run_key": "run-test-1",
        "observation_count": 40,
        "cluster_count": 20,
        "auto_write_tiers": [0, 1, 2],
        "summary": {
            "rules_version": "3",
            "derivation_census": {
                "checked": checked,
                "gq23_failures": [
                    {"left": "a", "right": "b", "tier": 1, "token": "lin", "reason": "x"}
                ]
                * failures,
                "demote_next_run": [["lin", 1]] * failures,
                "origin_distinct_violations": 0,
                "origin_distinct_clusters": [],
            },
            "m1b_id_resolution_sample": namespaces or {},
            "count_intervals": {"national": {"lower": 18, "upper": 20}},
            **(corroboration or {}),
        },
        "links": links or [],
        "resolved_edges": [],
        "proposed_count": 0,
        "cannot_link_count": 0,
        "refused_count": 0,
    }


def _build(runs, corpus_doc, *, dedup_view=None, member_records=None) -> dict:
    return mech_eval.build_mech_eval(
        runs=runs,
        dedup_view=dedup_view,
        member_records=member_records or {},
        corpus_doc=corpus_doc,
        source_names={"src_a": "Source A"},
        ruleset_version="3",
        copy_tolerance_m=1.0,
        as_of="2026-11-12",
    )


# ---------------------------------------------------------------------------
# The acceptance shape — numerator, denominator, method, population
# ---------------------------------------------------------------------------


def test_committed_record_passes_the_lint(committed: dict) -> None:
    assert mech_eval.mech_eval_lint_errors(committed) == []


def test_every_estimand_carries_the_acceptance_shape(committed: dict) -> None:
    """Catalog verbatim: numerator, denominator, method and population per
    estimand — a regression here fails loud, never silently."""
    for section in ("estimands", "human_estimands"):
        assert committed[section], section
        for name, e in committed[section].items():
            for field in ("numerator", "denominator", "method", "population"):
                assert field in e, (section, name, field)
            assert e["population"].strip(), name
            if e["state"] == "measured":
                assert e["numerator"] is not None and e["denominator"] is not None
                assert e["method"], name


def test_human_estimands_are_unavailable_never_substituted(committed: dict) -> None:
    """ADR-152/153: the four EVAL-003 human estimands are unavailable with
    named reasons — no mechanical or agent figure stands in."""
    assert set(committed["human_estimands"]) == {
        "auto_positive_precision",
        "candidate_recall",
        "cluster_quality",
        "labelability",
    }
    for e in committed["human_estimands"].values():
        assert e["state"] == "unavailable"
        assert e["unavailable_reason"] == "no_human_reference"
        assert e["numerator"] is None and e["denominator"] is None


def test_estimands_are_labelled_mechanical(committed: dict) -> None:
    """SIG-CONF-012: every estimand's label carries the verbatim disclaimer —
    a mechanical measure is never presented as real-world precision/recall."""
    for name, e in committed["estimands"].items():
        assert "never an estimate of real-world precision or recall" in e["label"], name


def test_scope_names_eval006_fields(committed: dict) -> None:
    """SIG-EVAL-006: tiers, population, source mix, ruleset, time window."""
    scope = committed["scope"]
    assert scope["tiers"]["auto_collapse_derivation"] == [0, 1, 2]
    assert scope["tiers"]["review_only_inferential"] == [3, 4, 5]
    assert scope["ruleset"]["camera_site_rules_version"]
    assert scope["populations"]["spine"] and scope["populations"]["corpus"]
    assert "source_mix" in scope and "time_window" in scope
    assert scope["time_window"]["as_of"]


# ---------------------------------------------------------------------------
# The honest no-run posture vs a measured run
# ---------------------------------------------------------------------------


def test_no_run_reports_unavailable_never_fabricated(corpus_doc: dict) -> None:
    doc = _build([], corpus_doc)
    for mid in ("m1_derivation_census", "m3_cross_copy_agreement", "m9_corroboration"):
        e = doc["estimands"][mid]
        assert e["state"] == "unavailable", mid
        assert e["unavailable_reason"] == "no_completed_run"
        assert e["numerator"] is None and e["denominator"] is None
    for mid in ("m1b_id_resolution_sample", "m2_fidelity_sample"):
        assert doc["estimands"][mid]["unavailable_reason"] == "no_completed_run"
    # …while the corpus measures are genuinely measured.
    assert doc["estimands"]["m4_perturbation"]["state"] == "measured"
    assert doc["estimands"]["m5_hard_negatives"]["state"] == "measured"


def test_a_run_measures_m1_m3_m9(corpus_doc: dict) -> None:
    links = [
        {
            "left": "a",
            "right": "b",
            "disposition": "auto_write",
            "relation_type": "derived_from",
            "tier": 1,
            "site_id": "a",
            "evidence": {
                "distance_m": 0.4,
                "shared_upstream_ref": "51",
                "attribute_differences": ["name"],
            },
        },
        {
            "left": "a",
            "right": "c",
            "disposition": "auto_write",
            "relation_type": "derived_from",
            "tier": 2,
            "site_id": "a",
            "evidence": {"distance_m": 2.5, "shared_upstream_ref": "51"},
        },
    ]

    class _View:
        n_lineages = {"s1": 2, "s2": 1, "s3": 2}
        site_members = {"s1": ("a", "b"), "s2": ("c",), "s3": ("d", "e", "f")}

    run = _run(
        checked=4,
        failures=1,
        namespaces={"arcgis.src.objectid": {"collapses": 10, "sample_size": 10}},
        links=links,
        corroboration={"multi_record_sites_independently_corroborated": 2},
    )
    doc = _build([run], corpus_doc, dedup_view=_View(), member_records={"a": "src_a"})
    m1 = doc["estimands"]["m1_derivation_census"]
    assert m1["state"] == "measured"
    assert (m1["numerator"], m1["denominator"]) == (3, 4)
    m3 = doc["estimands"]["m3_cross_copy_agreement"]
    assert m3["state"] == "measured"
    assert (m3["numerator"], m3["denominator"]) == (1, 2)  # one link within 1.0 m
    m9 = doc["estimands"]["m9_corroboration"]
    assert m9["state"] == "measured"
    assert (m9["numerator"], m9["denominator"]) == (2, 2)
    # M-1b: the frame is drawn but the upstream GETs are deferred — recorded.
    m1b = doc["estimands"]["m1b_id_resolution_sample"]
    assert m1b["state"] == "unavailable"
    assert m1b["unavailable_reason"] == "upstream_gets_deferred"
    assert "10" in m1b["population"]
    m2 = doc["estimands"]["m2_fidelity_sample"]
    assert m2["unavailable_reason"] == "upstream_gets_deferred"
    assert mech_eval.mech_eval_lint_errors(doc) == []


# ---------------------------------------------------------------------------
# The committed corpus record is a real measurement, pinned
# ---------------------------------------------------------------------------


def test_corpus_record_is_the_harness_output(corpus_doc: dict) -> None:
    """The committed sig.mech-eval-corpus/1 record carries the P35.23
    harness's deterministic M-4/M-5 measurements — a drift in the corpus or
    the harness fails this pin, never silently ships."""
    from ops import rdc, rdc_harness

    corpus = rdc.load_corpus(REPO / "tests" / "rdc" / "data")
    report = rdc_harness.run_harness(corpus, with_pipeline=False, generated_at="static")
    assert corpus_doc["sections"]["m4_perturbation"] == report["sections"]["m4"]
    assert corpus_doc["sections"]["m5_hard_negatives"] == report["sections"]["m5"]
    assert mech_eval.corpus_lint_errors(corpus_doc) == []


def test_committed_record_matches_the_builder(corpus_doc: dict, committed: dict) -> None:
    """The canonical fixtures-mode record regenerates deterministically —
    ``scripts/eval/run_mech_eval.py`` output, never hand-edited bytes."""
    from resolution.camera_sites import CameraSiteRules

    rules = CameraSiteRules.from_data()
    rebuilt = _build([], corpus_doc)
    rebuilt["as_of"] = committed["as_of"]
    rebuilt2 = mech_eval.build_mech_eval(
        runs=[],
        dedup_view=None,
        member_records={},
        corpus_doc=corpus_doc,
        source_names={},
        ruleset_version=str(rules.version),
        copy_tolerance_m=float(rules.copy_tolerance_m),
        as_of=committed["as_of"],
    )
    assert rebuilt == rebuilt2
    assert rebuilt2 == committed


# ---------------------------------------------------------------------------
# The lint refuses contract violations
# ---------------------------------------------------------------------------


def test_lint_refuses_a_substituted_human_estimand(committed: dict) -> None:
    bad = json.loads(json.dumps(committed))
    bad["human_estimands"]["auto_positive_precision"]["state"] = "measured"
    bad["human_estimands"]["auto_positive_precision"]["numerator"] = 9
    errors = mech_eval.mech_eval_lint_errors(bad)
    assert any("never substituted" in e for e in errors)


def test_lint_refuses_an_unlabelled_estimand(committed: dict) -> None:
    bad = json.loads(json.dumps(committed))
    bad["estimands"]["m4_perturbation"]["label"] = "precision: great"
    errors = mech_eval.mech_eval_lint_errors(bad)
    assert any("disclaimer" in e for e in errors)


def test_lint_refuses_unavailable_without_a_reason(committed: dict) -> None:
    bad = json.loads(json.dumps(committed))
    bad["estimands"]["m1_derivation_census"]["unavailable_reason"] = None
    errors = mech_eval.mech_eval_lint_errors(bad)
    assert any("without a named reason" in e for e in errors)
