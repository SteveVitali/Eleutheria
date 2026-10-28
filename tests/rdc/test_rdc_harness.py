# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.23 (SIG-CONF-008/012, GQ-26): the corpus harness legs — M-4 perturbation
known-answers, M-5 mechanical hard negatives, M-6 metamorphic invariants — plus
the pipeline legs over the committed slices.

Every number here is a mechanical census over declared classes; the report
header names each estimand and disclaims real-world precision/recall
(SIG-CONF-012). These tests run in the PR lane.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ops import rdc, rdc_harness

DATA = Path(__file__).resolve().parent / "data"


@pytest.fixture(scope="module")
def corpus() -> rdc.Corpus:
    return rdc.load_corpus(DATA)


@pytest.fixture(scope="module")
def report(corpus: rdc.Corpus) -> dict:
    return rdc_harness.run_harness(corpus, generated_at="2026-10-15T00:00:00Z")


# ---------------------------------------------------------------------------
# The whole-harness verdict + report shape
# ---------------------------------------------------------------------------


def test_harness_verdict_pass(report: dict) -> None:
    assert report["verdict"] == "pass", report["failures"]
    assert report["slices_evaluated"] == 4
    assert set(report["slices_deferred_unmaterialized"]) == {
        "eff_data_driven_2016_2017",
        "legistar_tenant_collision",
        "osm_okc_surveillance",
    }


def test_report_estimand_headers_verbatim(report: dict) -> None:
    """SIG-CONF-012: every leg names its estimand and disclaims real-world
    precision/recall — verbatim, never reframed."""
    assert rdc.report_lint_errors(report) == []
    for leg in ("m4", "m5", "m6"):
        assert "never an estimate of real-world precision or recall" in report["estimand"][leg]


# ---------------------------------------------------------------------------
# M-4 perturbation
# ---------------------------------------------------------------------------


def test_m4_every_class_meets_its_known_answer(report: dict) -> None:
    m4 = report["sections"]["m4"]
    assert m4["outcome"] == "pass"
    assert m4["violations"] == 0
    assert m4["sample_size"] >= 20
    for cls, expected in rdc_harness.M4_CLASSES.items():
        d = m4["classes"][cls]
        assert d["expected"] == expected
        assert d["tested"] >= 20, cls
        assert d["mismatches"] == 0, (cls, d["examples"])


def test_m4_measured_rates_are_honest(report: dict) -> None:
    """The measured join rates are reported, not asserted away: join classes
    measure 1.0, separate classes measure 0.0 — both recorded."""
    m4 = report["sections"]["m4"]
    for cls, d in m4["classes"].items():
        if d["expected"] == "join":
            assert d["join_rate"] == 1.0, cls
        else:
            assert d["join_rate"] == 0.0, cls


# ---------------------------------------------------------------------------
# M-5 hard negatives
# ---------------------------------------------------------------------------


def test_m5_no_declared_negative_merges(report: dict) -> None:
    m5 = report["sections"]["m5"]
    assert m5["outcome"] == "pass"
    assert m5["violations"] == 0
    for cls, d in m5["classes"].items():
        assert d["merged"] == 0, (cls, d["examples"])
        assert d["tested"] > 0


def test_m5_uses_real_co_located_pairs(report: dict) -> None:
    """The DC slice contributes real co-located multi-view pairs — the
    ia_dot_multiview analog — not only synthetic templates."""
    assert report["sections"]["m5"]["real_co_located_pairs"] >= 10
    d = report["sections"]["m5"]["classes"]["unique_distinct_ids_one_namespace"]
    assert d["tested"] >= 30
    assert d["assessed"] > 0  # the pairs were genuinely evaluated, not skipped


# ---------------------------------------------------------------------------
# M-6 / GQ-26 metamorphic invariants
# ---------------------------------------------------------------------------


def test_m6_all_invariants_hold(report: dict) -> None:
    m6 = report["sections"]["m6"]
    assert m6["outcome"] == "pass"
    assert m6["violations"] == 0
    for name in (
        "input_order_permutation",
        "page_size_change",
        "remove_declared_mirror",
        "add_origin_with_existing_mirror",
        "rerun_plus_zero",
    ):
        assert m6["checks"][name]["outcome"] == "pass", name
        assert m6["checks"][name]["same"] is True, name


def test_m6_exercises_real_collapses(report: dict) -> None:
    """The metamorphic set actually collapses mirrors (15 sites / 30 records)
    — the invariants run over real merge decisions, not singletons."""
    base = report["sections"]["m6"]["checks"]["baseline_sites"]
    assert base["records"] == 30
    assert base["distinct_sites"] == 15
    assert base["decisions"] >= 15


# ---------------------------------------------------------------------------
# Pipeline legs — the real connector over the captured bytes
# ---------------------------------------------------------------------------


def test_dc_pipeline_fails_closed_on_the_non_unique_key(report: dict) -> None:
    """The recorded il_dot_objectid-class defect live: `ID` values collide,
    the P35.24/GQ-04 uniqueness check aborts — never a silent merge."""
    pipe = report["sections"]["slices"]["camreg_dc_multiview"]["pipeline"]
    assert pipe["run"] == "failed"
    assert pipe["error_class"] == "SubjectKeyCollision"
    assert "minted twice" in pipe["error"]


def test_nottingham_pipeline_mints_flagged_entities(report: dict) -> None:
    pipe = report["sections"]["slices"]["camreg_nottingham_axis"]["pipeline"]
    assert pipe["run"] == "completed"
    assert pipe["distinct_subjects"] == 562
    # the recorded transposition: every entity flags geometry_defect
    assert pipe["predicate_counts"].get("geometry_defect") == 562


def test_atlas_pipeline_mints_distinct_subjects_per_state_name(report: dict) -> None:
    pipe = report["sections"]["slices"]["eff_atlas_multistate"]["pipeline"]
    assert pipe["run"] == "completed"
    assert pipe["distinct_subjects"] > 500


def test_usaspending_pipeline_matches_keywords(report: dict) -> None:
    pipe = report["sections"]["slices"]["usaspending_topical"]["pipeline"]
    assert pipe["run"] == "completed"
    assert pipe["predicate_counts"].get("matched_keyword", 0) > 0


def test_pipeline_expectations_recorded(report: dict) -> None:
    for sid, sec in report["sections"]["slices"].items():
        for check in sec.get("pipeline_expectations", []):
            assert check["ok"], (sid, check)


# ---------------------------------------------------------------------------
# Record projection
# ---------------------------------------------------------------------------


def test_arcgis_projection_shape(corpus: rdc.Corpus) -> None:
    s = next(x for x in corpus.slices if x.slice_id == "camreg_dc_multiview")
    records = rdc_harness.project_records(s)
    assert len(records) == 1060
    for r in records[:5]:
        assert r["subject_id"].startswith("rdc:camreg_dc_multiview:")
        assert r["latitude"] is not None and r["longitude"] is not None
        assert r["id_namespace"] == "arcgis.camreg_washington_dc.objectid"
        assert r["technology"] == "fixed-camera-cctv"
