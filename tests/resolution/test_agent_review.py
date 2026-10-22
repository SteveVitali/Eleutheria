# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.48 — the agent review lane (SIG-CONF-002; ADR-128/152/153; gate B-31).

These tests pin the lane's contract:

* the seeded weekly stratified sample is deterministic on (seed, corpus),
  covers the declared strata (50 sites + 30 edges incl. a fixed
  simple-random block), and records a shortfall honestly;
* packet items and their prompts are blind — no matcher internals, earlier
  labels, or the other verdict;
* every ``sig.agent-review/1`` record carries agent provenance and appends
  to the lane dir — never a ``human_eval_*`` table;
* agreement is ``agent_consensus`` (never "correct"), κ is agreement between
  two AI runs (never accuracy), and a disagreement routes to the §4.4 S4
  maintainer queue as a queue entry, never a decision;
* no gate (auto-write, eval-status promotion, release) reads the lane's
  records, and no item in a B5-reserved partition is labelled;
* the committed camera gold set is a development set whose adjudicator
  fields are "agent (Claude Opus 5.5), twice" — its stored label history
  preserved verbatim.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from resolution.agent_review import (
    CONTEXT_IDS,
    EDGE_STRATUM_QUOTAS,
    LANE_DIR,
    PACKET_SCHEMA_VERSION,
    QUEUE_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    RESERVED_PARTITIONS,
    SAMPLE_EDGES,
    SAMPLE_SITES,
    SCHEMA_VERSION,
    SIMPLE_RANDOM,
    SITE_STRATUM_QUOTAS,
    append_queue_entries,
    append_records,
    build_labelling_prompts,
    build_packet,
    cohens_kappa,
    lane_paths,
    lane_report,
    make_record,
    read_records,
    reserved_item_ids,
    route_verdicts,
    universe_digest,
    validate_record,
    write_run,
)
from support import REPO_ROOT

WEEK = "2026-W43"
MODEL = "claude-opus-5-5@p35-48-demo"


def _site(i: int, strata: tuple[str, ...] = ()) -> dict:
    return {
        "item_id": f"site-{i:03d}",
        "kind": "site",
        "strata": list(strata),
        "evidence": {
            "record_title": f"Municipal camera record {i}",
            "source_name": "fixture-registry",
            "upstream_excerpt": f"CCTV camera at pole {i}, installed 2024",
            "parsed_type": "cctv",
            "parsed_role": "traffic_monitoring",
            "parsed_date": "2024-01",
        },
    }


def _edge(i: int, strata: tuple[str, ...] = ()) -> dict:
    return {
        "item_id": f"edge-{i:03d}",
        "kind": "edge",
        "strata": list(strata),
        "evidence": {
            "record_title": f"Procurement record {i}",
            "snippet": f"contract for CCTV maintenance lot {i}",
        },
    }


def _universe(n_sites: int = 60, n_edges: int = 36) -> dict:
    items = []
    for i in range(n_sites):
        strata = []
        if i < 18:
            strata.append("new_sources")
        if 18 <= i < 33:
            strata.append("possible_duplicates")
        if 33 <= i < 45:
            strata.append("dossier_delta_sites")
        items.append(_site(i, tuple(strata)))
    for i in range(n_edges):
        items.append(_edge(i, ("operator_edges",) if i < 18 else ("procurement_edges",)))
    return {
        "version": "sig.agent-review-corpus/1",
        "capture_kind": "fixture",
        "items": items,
    }


def _records_for(packet: dict, model_id: str = MODEL) -> list[dict]:
    """Two blind verdicts per packet item — the fixture's honest run."""
    records = []
    prompts = build_labelling_prompts(packet)
    for item in packet["items"]:
        for ctx in CONTEXT_IDS:
            assert prompts[item["item_id"]][ctx]
            records.append(
                make_record(
                    packet,
                    item,
                    context_id=ctx,
                    verdict="relevant" if item["kind"] == "edge" else "faithful",
                    model_id=model_id,
                    labelled_at="2026-10-22T07:30:00Z",  # future-ok: synthetic: stand-in stamp
                )
            )
    return records


# ---------------------------------------------------------------------------
# The seeded weekly stratified sampler


def test_packet_is_deterministic_on_seed_and_corpus() -> None:
    u = _universe()
    p1 = build_packet(u, seed="w43", week=WEEK)
    p2 = build_packet(u, seed="w43", week=WEEK)
    assert p1 == p2
    assert p1["version"] == PACKET_SCHEMA_VERSION
    assert p1["corpus_digest"] == universe_digest(u)


def test_packet_changes_with_seed_or_corpus() -> None:
    u = _universe()
    base = build_packet(u, seed="w43", week=WEEK)
    other_seed = build_packet(u, seed="w44", week=WEEK)
    assert other_seed["packet_id"] != base["packet_id"]
    u2 = _universe(n_sites=61)
    other_corpus = build_packet(u2, seed="w43", week=WEEK)
    assert other_corpus["corpus_digest"] != base["corpus_digest"]
    assert other_corpus["packet_id"] != base["packet_id"]


def test_packet_hits_the_weekly_design() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    sites = [i for i in p["items"] if i["kind"] == "site"]
    edges = [i for i in p["items"] if i["kind"] == "edge"]
    assert len(sites) == SAMPLE_SITES
    assert len(edges) == SAMPLE_EDGES
    # The fixed simple-random block: exactly its declared quota drew.
    srs_sites = [i for i in sites if i["stratum"] == SIMPLE_RANDOM]
    srs_edges = [i for i in edges if i["stratum"] == SIMPLE_RANDOM]
    assert len(srs_sites) == SITE_STRATUM_QUOTAS[SIMPLE_RANDOM]
    assert len(srs_edges) == EDGE_STRATUM_QUOTAS[SIMPLE_RANDOM]
    # Every packet item carries exactly one declared stratum.
    for item in sites:
        assert item["stratum"] in SITE_STRATUM_QUOTAS
    for item in edges:
        assert item["stratum"] in EDGE_STRATUM_QUOTAS


def test_first_pass_draws_respect_quotas() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    draws = p["strata_draws"]
    # New sources 18 candidates for a 15 quota, poss-dup 15 for 15,
    # dossier deltas 12 for 10, SRS 10 — every declared quota reachable.
    assert len(draws["site"]["new_sources"]) >= SITE_STRATUM_QUOTAS["new_sources"]
    assert len(draws["edge"]["procurement_edges"]) >= EDGE_STRATUM_QUOTAS["procurement_edges"]
    # Item ids unique inside a kind.
    for kind in ("site", "edge"):
        ids = [i["item_id"] for i in p["items"] if i["kind"] == kind]
        assert len(ids) == len(set(ids))


def test_shortfall_is_recorded_honestly() -> None:
    tiny = {"version": "sig.agent-review-corpus/1", "capture_kind": "fixture", "items": [_site(0)]}
    p = build_packet(tiny, seed="s", week=WEEK)
    assert p["n_sites"] == 1
    assert p["n_edges"] == 0
    assert len(p["items"]) == 1  # never padded


def test_reserved_partitions_are_never_labelled() -> None:
    u = _universe()
    # An item carrying a reserved partition on its face is excluded.
    u["items"][0]["partition"] = "sealed_final"
    p = build_packet(u, seed="w43", week=WEEK, reserved_ids={"site-001"})
    drawn = {i["item_id"] for i in p["items"]}
    assert "site-000" not in drawn
    assert "site-001" not in drawn


def test_reserved_item_ids_reads_human_eval_rows() -> None:
    rows = [
        {"pair_id": "pair-1", "partition": "sealed_final"},
        {"sample_id": "s-9", "partition": "pilot"},
        {"item_id": "ok-1", "partition": "training"},
        {"left_ref": "l-1", "right_ref": "r-1", "partition": "calibration"},
    ]
    reserved = reserved_item_ids(rows)
    assert reserved == frozenset({"pair-1", "s-9", "l-1", "r-1"})
    assert set(reserved_item_ids([])) == set()


def test_reserved_guard_is_defence_in_depth() -> None:
    u = _universe(n_sites=1, n_edges=0)
    u["items"][0]["partition"] = "calibration"
    p = build_packet(u, seed="s", week=WEEK)
    assert p["items"] == []  # the only item is reserved — never drawn


def test_every_reserved_partition_constant_matches_human_eval() -> None:
    from resolution.human_eval import PARTITIONS

    # Permitted uses for the agent lane are training/development only —
    # every other human_eval partition must be reserved here.
    assert set(RESERVED_PARTITIONS) == set(PARTITIONS) - {"training", "development"}


# ---------------------------------------------------------------------------
# Blindness


def test_evidence_with_matcher_internals_is_refused() -> None:
    u = _universe(n_sites=1, n_edges=0)
    u["items"][0]["evidence"]["match_tier"] = 3
    with pytest.raises(ValueError, match="not blind"):
        build_packet(u, seed="s", week=WEEK)


@pytest.mark.parametrize(
    "key",
    ["label_history", "cluster_id", "other_verdict", "expected", "partition", "score"],
)
def test_forbidden_evidence_keys_are_refused(key: str) -> None:
    u = _universe(n_sites=1, n_edges=0)
    u["items"][0]["evidence"][key] = "x"
    with pytest.raises(ValueError, match="not blind"):
        build_packet(u, seed="s", week=WEEK)


def test_packet_items_carry_only_the_blind_payload() -> None:
    p = build_packet(_universe(), seed="s", week=WEEK)
    for item in p["items"]:
        assert set(item) == {"item_id", "kind", "stratum", "question", "evidence"}
        blob = json.dumps(item["evidence"]).lower()
        for token in ("tier", "label", "verdict", "cluster", "partition"):
            assert f'"{token}' not in blob


def test_two_blind_prompts_per_item_neither_sees_the_other() -> None:
    p = build_packet(_universe(), seed="seed-ZX9", week=WEEK)
    prompts = build_labelling_prompts(p)
    assert len(prompts) == len(p["items"])
    for item in p["items"]:
        pair = prompts[item["item_id"]]
        assert set(pair) == set(CONTEXT_IDS)
        assert pair["a"] != pair["b"]  # different wordings
        for text in pair.values():
            # The prompt carries the item's evidence only — never packet
            # metadata, never the other's verdict, never a planted answer.
            assert (
                json.dumps(
                    item["evidence"]["upstream_excerpt"]
                    if item["kind"] == "site"
                    else item["evidence"]["snippet"]
                )
                in text
                or item["evidence"]["upstream_excerpt" if item["kind"] == "site" else "snippet"]
                in text
            )
            assert str(p["seed"]) not in text
            assert p["corpus_digest"] not in text
            assert p["packet_id"] not in text


# ---------------------------------------------------------------------------
# The sig.agent-review/1 record + append-only storage


def test_record_carries_full_agent_provenance() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    item = p["items"][0]
    rec = make_record(
        p,
        item,
        context_id="a",
        verdict="faithful",
        model_id=MODEL,
        labelled_at="2026-10-22T07:30:00Z",  # future-ok: synthetic: stand-in fixture stamp
        rationale="parsed fields match the excerpt",
    )
    assert rec["version"] == SCHEMA_VERSION
    assert rec["labeller_kind"] == "agent"
    assert rec["model_id"] == MODEL
    assert rec["prompt_digest"].startswith("sha256:")
    assert rec["context_id"] == "a"
    assert rec["seed"] == p["seed"]
    assert rec["corpus_digest"] == p["corpus_digest"]
    assert rec["basis_class"] == "B3"
    assert rec["basis_label"] == "agent review"
    assert validate_record(rec) == []


def test_the_two_contexts_carry_distinct_prompt_digests() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    item = p["items"][0]
    a = make_record(p, item, context_id="a", verdict="faithful", model_id=MODEL, labelled_at="t")
    b = make_record(p, item, context_id="b", verdict="faithful", model_id=MODEL, labelled_at="t")
    assert a["prompt_digest"] != b["prompt_digest"]
    assert a["record_id"] != b["record_id"]


@pytest.mark.parametrize(
    "field,bad",
    [
        ("labeller_kind", "human"),
        ("basis_class", "B5"),
        ("basis_label", "independent human review"),
        ("model_id", ""),
        ("prompt_digest", ""),
        ("context_id", "c"),
        ("verdict", "correct"),
        ("item_kind", "site"),
    ],
)
def test_invalid_records_are_refused(field: str, bad: object) -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    item = p["items"][0]
    rec = make_record(p, item, context_id="a", verdict="faithful", model_id=MODEL, labelled_at="t")
    rec[field] = bad if field != "item_kind" else "not-a-kind"
    assert validate_record(rec) != []


def test_append_records_is_append_only_and_idempotent(tmp_path: Path) -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    records = _records_for(p)
    path = tmp_path / "labels.jsonl"
    assert append_records(path, records) == len(records)
    # A re-run appends nothing — dedupe on record_id.
    assert append_records(path, records) == 0
    stored = read_records(path)
    assert len(stored) == len(records)
    # An invalid record refuses the whole append.
    bad = dict(records[0], record_id="ar-x", labeller_kind="human")
    with pytest.raises(ValueError):
        append_records(path, [bad])


def test_lane_artifacts_live_under_the_lane_dir_only(tmp_path: Path) -> None:
    u = _universe()
    p = build_packet(u, seed="w43", week=WEEK)
    records = _records_for(p)
    routed = route_verdicts(
        p,
        records,
        queued_at="2026-10-22T07:45:00Z",  # future-ok: synthetic: stand-in fixture stamp
    )
    report = lane_report(
        p,
        records,
        routed["queue_entries"],
        generated_at="2026-10-22T07:45:00Z",  # future-ok: synthetic: stand-in fixture stamp
    )
    paths = write_run(tmp_path, p, records, routed["queue_entries"], report, universe=u)
    for path in paths.values():
        assert path.exists()
        assert "human_eval" not in str(path)
    packet_doc = json.loads(paths["packet"].read_text())
    assert packet_doc["packet_id"] == p["packet_id"]
    report_doc = json.loads(paths["report"].read_text())
    assert report_doc["version"] == REPORT_SCHEMA_VERSION
    assert paths["labels"].name == f"labels-{p['packet_id']}.jsonl"
    assert paths["queue"].name == "maintainer-queue-s4.jsonl"
    assert paths["universe"].name.startswith("universe-")


def test_lane_dir_is_the_committed_reports_prefix() -> None:
    assert str(LANE_DIR) == "docs/build/reports/agent-review"
    assert "human_eval" not in str(LANE_DIR)


# ---------------------------------------------------------------------------
# Consensus, disagreement routing, and the κ disclosure


def test_agreement_is_agent_consensus_never_correct() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    records = _records_for(p)
    routed = route_verdicts(
        p,
        records,
        queued_at="2026-10-22T08:00:00Z",  # future-ok: synthetic: stand-in fixture stamp
    )
    assert len(routed["consensus"]) == len(p["items"])
    assert routed["queue_entries"] == []
    assert routed["unpaired"] == []
    for verdict in routed["consensus"].values():
        assert verdict in ("faithful", "relevant")  # never "correct"


def test_disagreement_routes_to_the_s4_queue_never_a_decision() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    records = _records_for(p)
    # Flip context b's verdict on one item — an honest disagreement.
    item_id = p["items"][0]["item_id"]
    flip = next(r for r in records if r["item_id"] == item_id and r["context_id"] == "b")
    flip["verdict"] = "unsure"
    flip["record_id"] = "ar-flipped"
    routed = route_verdicts(
        p,
        records,
        queued_at="2026-10-22T08:00:00Z",  # future-ok: synthetic: stand-in fixture stamp
    )
    assert item_id not in routed["consensus"]
    assert len(routed["queue_entries"]) == 1
    entry = routed["queue_entries"][0]
    assert entry["version"] == QUEUE_SCHEMA_VERSION
    assert entry["queue"] == "maintainer"
    assert entry["stratum"] == "S4"
    assert entry["reason"] == "agent_disagreement"
    assert entry["item_id"] == item_id
    assert "not a decision" in entry["note"]
    assert len(entry["record_ids"]) == 2


def test_unpaired_items_are_neither_consensus_nor_routed() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    records = _records_for(p)[:2]  # only context a+b for item 0, then drop b
    records = [r for r in records if r["context_id"] == "a"]
    routed = route_verdicts(p, records, queued_at="t")
    assert routed["consensus"] == {}
    assert routed["queue_entries"] == []
    assert len(routed["unpaired"]) == len(p["items"])


def test_queue_entries_append_idempotently(tmp_path: Path) -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    records = _records_for(p)
    flip = next(
        r for r in records if r["item_id"] == p["items"][0]["item_id"] and r["context_id"] == "b"
    )
    flip["verdict"] = "unsure"
    flip["record_id"] = "ar-flip2"
    entries = route_verdicts(p, records, queued_at="t")["queue_entries"]
    path = tmp_path / "maintainer-queue-s4.jsonl"
    assert append_queue_entries(path, entries) == 1
    assert append_queue_entries(path, entries) == 0
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    assert rows[0]["stratum"] == "S4"


def test_kappa_is_agreement_between_two_ai_runs_never_accuracy() -> None:
    p = build_packet(_universe(), seed="w43", week=WEEK)
    records = _records_for(p)
    routed = route_verdicts(p, records, queued_at="t")
    report = lane_report(p, records, routed["queue_entries"], generated_at="t")
    assert report["agent_agent_kappa"] == pytest.approx(1.0)
    assert "agreement between two AI runs" in report["disclosure"]
    assert "never" in report["disclosure"]
    assert "accuracy" in report["disclosure"]  # named as what it is NOT
    blob = json.dumps(report).lower()
    # The report may say what the lane never claims; it may never ASSERT
    # correctness or accuracy.
    assert '"verdict": "correct"' not in blob
    assert report["basis_class"] == "B3"
    assert report["basis_label"] == "agent review"
    assert report["labeller_kind"] == "agent"
    assert report["same_model_family"] is True


def test_cohens_kappa_values() -> None:
    assert cohens_kappa(["a", "a", "b"], ["a", "a", "b"]) == pytest.approx(1.0)
    assert cohens_kappa([], []) is None
    assert cohens_kappa(["a", "b"], ["b", "a"]) == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# Segregation — never a human_eval_* write, never a gate input


def test_agent_verdicts_cannot_enter_the_human_label_adapter() -> None:
    """``record_label`` refuses any non-reference label before a connection —
    the lane's vocabulary (faithful/relevant/unsure/agent_consensus) can
    never be recorded as a human label."""
    from resolution.human_eval import REFERENCE_LABELS
    from resolution.human_eval_pg import record_label

    for lane_word in ("faithful", "relevant", "off_topic", "unsure", "agent_consensus"):
        assert lane_word not in REFERENCE_LABELS
        with pytest.raises(ValueError, match="label must be one of"):
            record_label(
                None,
                campaign_id="c",
                sample_id="s",
                reviewer_id="r",
                round="r1",
                label=lane_word,
                reason_codes=(),
                evidence_refs=(),
                rubric_version="v",
                packet_digest="d",
                attestation_id="a",
                label_digest="x",
            )


_GATE_MODULES = (
    "resolution/src/resolution/camera_sites.py",
    "resolution/src/resolution/evaluator.py",
    "resolution/src/resolution/camera_sites_pg.py",
    "resolution/src/resolution/human_eval.py",
    "resolution/src/resolution/human_eval_pg.py",
    "resolution/src/resolution/review_queue.py",
    "resolution/src/resolution/camera_site_review.py",
    "exports/src/exports/quality.py",
    "exports/src/exports/release.py",
    "ops/src/ops/release_candidate.py",
    "db/src/db/claim_sink.py",
    "connectors/src/connectors/loader.py",
)


def test_no_gate_module_imports_or_reads_the_lane() -> None:
    """The lane's records may never feed an auto-write gate, eval-status
    promotion, or a release gate. The gate modules neither import
    ``resolution.agent_review`` nor reference the record family / lane dir."""
    for rel in _GATE_MODULES:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "agent_review" not in node.module, f"{rel} imports the lane"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "agent_review" not in alias.name, f"{rel} imports the lane"
        text = path.read_text(encoding="utf-8")
        assert "sig.agent-review" not in text, f"{rel} names the record family"
        assert "docs/build/reports/agent-review" not in text, f"{rel} names the lane dir"


def test_lane_dir_holds_no_human_eval_artifacts() -> None:
    lane = REPO_ROOT / LANE_DIR
    if not lane.exists():
        pytest.skip("lane records dir not yet populated")
    for path in lane.rglob("*"):
        assert "human_eval" not in path.name


# ---------------------------------------------------------------------------
# The camera gold set — a development set, never the auto-write reference


def test_gold_set_is_labelled_agent_twice_and_marked_development() -> None:
    path = REPO_ROOT / "resolution/src/resolution/data/camera_site_gold.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    status = raw["status"]
    assert status["role"] == "development"
    assert status["auto_write_reference"] is False
    assert status["adjudicator_fields"] == "agent (Claude Opus 5.5), twice"
    # Stored label history is preserved verbatim: the adjudicator identities
    # and their labels are untouched by the annotation.
    pair = raw["pairs"][0]
    adjudicators = {a["adjudicator"] for a in pair["adjudications"]}
    assert "agent:claude-opus-5-5@sig-maintainer-seed" in adjudicators
    assert "llm:claude-opus-5-5@camera-rules-v1-blind" in adjudicators
    assert len(raw["pairs"]) == 540


def test_gold_precision_never_certifies_an_auto_write() -> None:
    """Every candidate auto-write tier is census-waived (C0–C2 derivations)
    or B5-gated (inferential) — the agent-labelled holdout is a reference
    measurement, never the reference that admits a tier."""
    from resolution.camera_sites import CameraSiteRules, decide_auto_write_tiers

    rules = CameraSiteRules.from_data()
    # The structural guard: no candidate tier lives outside the waived and
    # inferential sets — if a future ruleset added one, gold precision would
    # be the auto-write reference again and this test must fail.
    assert rules.candidate_auto_write <= rules.collapse_tiers | rules.inferential_tiers
    # An uncertified inferential tier demotes however clean the measured
    # precision looks.
    from resolution.camera_sites import TierMeasurement

    perfect = {
        4: TierMeasurement(tier=4, predicted=60, match=60, non_match=0, not_enough_information=0)
    }
    auto, demotions = decide_auto_write_tiers(
        perfect,
        candidate_tiers={4},
        threshold=0.9,
        min_pairs=50,
        inferential_tiers={4},
        certified_tiers=(),
    )
    assert auto == frozenset()
    assert demotions[0].reason == "no_certifying_evaluation"
    assert demotions[0].precision == pytest.approx(1.0)


def test_lane_paths_stay_inside_the_lane_dir() -> None:
    paths = lane_paths("docs/build/reports/agent-review", "arp-x")
    for path in paths.values():
        assert str(path).startswith("docs/build/reports/agent-review/")
