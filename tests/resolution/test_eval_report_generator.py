# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Lock the committed P28.1 eval report's key invariants (ADR-099).

The report at ``docs/build/reports/P28.1_resolution_eval.md`` is decision-relevant
evidence (the operator reads it at the P28.5 pause). This guards the generator so a
silent change to the eval machinery cannot quietly move the published numbers.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GEN = Path(__file__).resolve().parents[2] / "scripts" / "eval" / "run_resolution_eval.py"


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("run_resolution_eval", _GEN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_eval_is_reproducible_and_honest(gen) -> None:
    from resolution.eval_loop import run_eval

    pairs, tier_by_pair_id, llm_labels, gold_set, pred_c, gold_c = gen.build()
    report = run_eval(
        gold_set=gold_set,
        pairs=pairs,
        tier_by_pair_id=tier_by_pair_id,
        llm_label_by_pair_id=llm_labels,
        seed_adjudicator=gen.SEED_ADJ,
        llm_adjudicator=gen.LLM.adjudicator_id,
        predicted_clusters=pred_c,
        gold_clusters=gold_c,
    )
    # κ clears the published bar → the LLM is trusted as gold (design §2.3).
    assert report.kappa >= report.kappa_bar
    assert report.llm_trusted
    # The measured floor is the raised 0.98 (ADR-099); deterministic tier 0 clears it.
    assert report.auto_write_threshold == 0.98
    assert report.tier_precisions.get(0) == 1.0
    assert not report.any_demoted
    # Genuine seed↔LLM disagreements are surfaced as disputed, never silently picked.
    assert len(report.disputed_pair_ids) > 0
    # Probabilistic tiers 4/5 + disputed + active-learning route to review.
    assert report.review_routed >= len(report.disputed_pair_ids)


def test_committed_report_matches_the_generator(gen) -> None:
    from resolution.eval_loop import render_report_md, run_eval

    pairs, tier_by_pair_id, llm_labels, gold_set, pred_c, gold_c = gen.build()
    report = run_eval(
        gold_set=gold_set,
        pairs=pairs,
        tier_by_pair_id=tier_by_pair_id,
        llm_label_by_pair_id=llm_labels,
        seed_adjudicator=gen.SEED_ADJ,
        llm_adjudicator=gen.LLM.adjudicator_id,
        predicted_clusters=pred_c,
        gold_clusters=gold_c,
    )
    md = render_report_md(report, title="P28.1 — Resolution eval report (Round 6 keystone)")
    committed = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "build"
        / "reports"
        / "P28.1_resolution_eval.md"
    ).read_text(encoding="utf-8")
    # The committed report's calibration line must match the generator (no drift).
    assert f"Cohen's κ (LLM vs seed): **{report.kappa:.3f}**" in committed
    assert "auto-write precision floor: **0.980**" in md


def test_committed_report_carries_the_hosted_scale_measurement(gen) -> None:
    """P30.2/P30.2a: the Scale section is the committed hosted measurement, never a
    fabricated number, and the PROVISIONAL-eval disclosure is retained (D-R6.1-EVAL OPEN)."""
    scale = gen.load_scale()
    assert scale is not None, "the P30.2 hosted-scale measurement is committed"
    kwargs, notes = gen.scale_kwargs(scale)
    committed = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "build"
        / "reports"
        / "P28.1_resolution_eval.md"
    ).read_text(encoding="utf-8")
    assert f"- observations considered: {kwargs['observation_count']}" in committed
    na = lambda v, f="": "n/a" if v is None else format(v, f)  # noqa: E731
    assert f"- resolved sites / decisions: {na(kwargs['resolved_site_count'])}" in committed
    assert f"- resolution envelopes materialized: {kwargs['resolutions_materialized']}" in committed
    assert f"- dedup ratio: {na(kwargs['dedup_ratio'], '.3f')}" in committed
    assert "**PROVISIONAL**" in committed
    # N resolved sites can never exceed the M observation-level sites (no overclaim).
    for n_sites in (kwargs["resolved_site_count"], kwargs["value_resolved_site_count"]):
        assert n_sites is None or n_sites <= kwargs["observation_count"]
    assert all(n in committed for n in notes)


def test_value_resolution_is_never_labelled_deduplication(gen) -> None:
    """P30.2a (ADR-104): value decisions within one source's record are reported on their
    own line, explicitly NOT as deduplication, next to the measured entity merges."""
    scale = gen.load_scale()
    kwargs, _ = gen.scale_kwargs(scale)
    committed = (
        Path(__file__).resolve().parents[2] / "docs/build/reports/P28.1_resolution_eval.md"
    ).read_text(encoding="utf-8")
    assert kwargs["value_resolved_site_count"] is not None
    assert (
        "(within each source's own record — NOT deduplication): "
        f"{kwargs['value_resolved_site_count']}" in committed
    )
    assert f"- entity-level merges (cross-source dedup): {kwargs['entity_merges']}" in committed
    # A dedup site count is not claimed until entity resolution (P30.2b) measures it.
    if kwargs["entity_merges"] == 0:
        assert kwargs["resolved_site_count"] is None


def test_scale_is_na_when_no_measurement_is_committed(gen) -> None:
    kwargs, notes = gen.scale_kwargs(None)
    assert set(kwargs.values()) == {None}
    assert notes and "DEFERRED" in notes[0]
