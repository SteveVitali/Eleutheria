# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.45 honest-evaluation posture (ADR-152/153, GQ-24/GQ-27): the
cross-cutting invariants that hold the whole ticket together.

* the committed v3-interim ruleset declares the inferential tiers
  review-only and only tier 1 (a derivation, not an inference) as an
  auto-write candidate;
* no inferential tier can auto-write without an independent human (B5)
  certification — however clean agent/LLM-derived precision looks;
* the committed gold set's provenance is ``agent``, never human;
* the committed posture report states every human estimand ``unavailable``
  and carries a basis class on every figure;
* the quality registry runs GQ-24 and GQ-27 in ``enforce``.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from resolution.camera_sites import (
    CameraSiteRules,
    TierMeasurement,
    decide_auto_write_tiers,
)

REPO = Path(__file__).resolve().parents[2]
GOLD_JSON = REPO / "resolution/src/resolution/data/camera_site_gold.json"
REPORT = REPO / "docs/build/reports/2026-10-09_honest_evaluation_posture.md"
REGISTRY = REPO / "exports/src/exports/data/quality_checks.toml"


def test_v3_interim_ruleset_shape() -> None:
    rules = CameraSiteRules.from_data()
    assert rules.version == "3-interim"
    assert rules.inferential_tiers == frozenset({3, 4, 5})
    # Tier 1 is the shared-upstream-ref DERIVATION — still a measured
    # auto-write candidate; no inferential tier is.
    assert rules.candidate_auto_write == frozenset({1})
    assert rules.inferential_tiers.isdisjoint(rules.candidate_auto_write)


def test_inferential_tier_never_auto_writes_on_agent_evidence() -> None:
    """Perfect agent-derived holdout precision still cannot certify an
    inferential tier — the demotion is explicit, not silent."""
    measured = {
        3: TierMeasurement(tier=3, predicted=100, match=100, non_match=0, not_enough_information=0),
        4: TierMeasurement(tier=4, predicted=60, match=60, non_match=0, not_enough_information=0),
        5: TierMeasurement(tier=5, predicted=50, match=50, non_match=0, not_enough_information=0),
    }
    auto, decisions = decide_auto_write_tiers(
        measured,
        candidate_tiers={3, 4, 5},
        threshold=0.98,
        min_pairs=50,
        inferential_tiers={3, 4, 5},
        certified_tiers=(),
    )
    assert auto == frozenset()
    assert {d.tier for d in decisions} == {3, 4, 5}
    for d in decisions:
        assert d.demoted and d.reason == "no_certifying_evaluation"


def test_human_certification_can_still_enable_an_inferential_tier() -> None:
    """The gate is about *certification*, not a hard-coded tier blocklist:
    a B5-certified inferential tier follows the measured path."""
    measured = {
        3: TierMeasurement(tier=3, predicted=100, match=99, non_match=1, not_enough_information=0),
    }
    auto, decisions = decide_auto_write_tiers(
        measured,
        candidate_tiers={3},
        threshold=0.98,
        min_pairs=50,
        inferential_tiers={3, 4, 5},
        certified_tiers={3},
    )
    assert auto == frozenset({3})
    assert not decisions[0].demoted


def test_derivation_tier_1_still_auto_writes_on_measured_evidence() -> None:
    measured = {
        1: TierMeasurement(tier=1, predicted=80, match=80, non_match=0, not_enough_information=0),
    }
    auto, _ = decide_auto_write_tiers(
        measured,
        candidate_tiers={1},
        threshold=0.98,
        min_pairs=50,
        inferential_tiers={3, 4, 5},
        certified_tiers=(),
    )
    assert auto == frozenset({1})


def test_committed_gold_set_provenance_is_agent_never_human() -> None:
    gold = json.loads(GOLD_JSON.read_text(encoding="utf-8"))
    assert gold["rules_version"] == CameraSiteRules.from_data().version
    assert gold["provenance"] == "agent"
    assert gold["verifier"].startswith("agent:")
    assert gold["llm"].startswith("llm:")
    text = GOLD_JSON.read_text(encoding="utf-8")
    assert "human-verified" not in text and "human verified" not in text


def test_committed_posture_report_states_unavailable_with_basis() -> None:
    assert REPORT.is_file()
    text = REPORT.read_text(encoding="utf-8")
    # Every human estimand is rendered unavailable — never measured.
    for name in (
        "auto_positive_precision",
        "candidate_recall",
        "cluster_quality",
        "labelability",
    ):
        assert f"### {name} — unavailable" in text
    # Basis classes are on the figures; agent evidence is named as agent.
    assert "basis class: `agent`" in text
    assert "`no_human_reference`" in text
    # The report never claims the labels are human truth.
    assert not re.search(r"\bhuman-verified\b", text)


def test_registry_enforces_gq24_and_gq27() -> None:
    checks = {c["id"]: c for c in tomllib.loads(REGISTRY.read_text(encoding="utf-8"))["check"]}
    assert checks["GQ-24"]["mode"] == "enforce"
    assert checks["GQ-27"]["mode"] == "enforce"
