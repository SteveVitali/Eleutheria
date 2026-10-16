# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tests for ``ops.truth_scan`` + ``ops.probe_registry`` — the P35.3
fixture-sentinel scan (SIG-OPS-012), the claim-marker binding (DR-C3-03), the
production-truth probe-sweep legs, and the registry's dry-run resolution
(G10/SIG-OPS-011).

Each leg is exercised on a small fixture tree under ``tmp_path``: planted
sentinels fail, declared compartments exempt, undisclosed stand-ins fail,
unregistered domains fail, human-completion assertions need a recorded marker
(an agent label never counts), and a probe leg that offered a non-empty
candidate set but evaluated none fails (SIG-ENG-042).
"""

from __future__ import annotations

import json
from pathlib import Path

from ops.probe_run import PROBE_RUN_VERSION, build_record, overall_for

from ops import truth_scan as ts

REPO_ROOT = Path(__file__).resolve().parents[2]

SENTINELS = """schema = "sig.sentinels/1"
standin_disclosure_keys = ["disclosure", "disclosed"]
standin_posture_keys = ["acquisition"]

[[sentinel]]
id = "sig-example-domain"
kind = "literal"
pattern = "sig.example"
note = "retired placeholder"

[[sentinel]]
id = "demo-marker"
kind = "regex"
pattern = '\\bdemo_[A-Za-z0-9_]'
note = "demo ids"

[[sentinel]]
id = "loopback-url"
kind = "regex"
pattern = '\\b(127\\.0\\.0\\.1|localhost)(:[0-9]{2,5})?\\b'
note = "loopback"

[[sentinel]]
id = "standin-undisclosed"
kind = "rule"
pattern = "capture-kind-standin-disclosure"
note = "undisclosed stand-in"

[[compartment]]
id = "demo-comp"
paths = ["dist/exhibit/**"]
allow = ["demo-marker"]
reason = "the declared exhibit compartment"

[[compartment]]
id = "owed-comp"
paths = ["dist/owed/**"]
allow = ["sig-example-domain"]
reason = "bounded placeholder exposure, owed"
debt = "D-TEST-1"

[contact_registry]
sources = ["data/sources.toml"]
fields = ["contact"]
registered_domains = ["real.example.org"]

[[claim_marker]]
id = "human-verified"
assert = ['\\bhuman[- ]verified\\b']
safe = ['\\bnot human[- ]verified\\b']

[markers]
record_glob = ["reviews/**"]
required = ["reviewer:", "recorded", "subject:"]
agent_label = '(?i)\\b(agent|bot|devin)\\b'
"""


def _cfg(tmp_path: Path, toml: str = SENTINELS) -> tuple[ts.SentinelsConfig, list[str]]:
    cfg_path = tmp_path / "sentinels.toml"
    cfg_path.write_text(toml)
    return ts.load_sentinels(cfg_path)


def _scan_tree(tmp_path: Path, files: dict[str, str]) -> list[tuple[Path, str, list[str]]]:
    root = tmp_path / "scan"
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return ts._iter_files([root], tmp_path)


def _def(tmp_path: Path, ids: list[str]) -> Path:
    d = tmp_path / "docs" / "tickets"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "DEFERRALS.md"
    p.write_text(
        "\n".join(f"| {i} | F | item | why | unblocked | verify | proxy | OPEN |" for i in ids)
    )
    return tmp_path


def test_committed_sentinels_table_loads_clean() -> None:
    cfg, errs = ts.load_sentinels(ts.SENTINELS_PATH)
    assert errs == []
    assert {s.id for s in cfg.sentinels} >= {
        "sig-example-domain",
        "loopback-url",
        "standin-undisclosed",
    }


def test_planted_sentinels_fail(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    files = _scan_tree(
        tmp_path,
        {
            "dist/page/index.html": '<a href="http://127.0.0.1:8000/x">x</a>',
            "dist/feed/uid.txt": "event@sig.example",
            "dist/e2/item.json": '{"id": "demo_thing"}',
        },
    )
    violations, hits, exempted = ts.sentinel_scan(cfg, files)
    kinds = {v.sentinel for v in violations}
    assert {"loopback-url", "sig-example-domain", "demo-marker"} <= kinds
    assert hits["loopback-url"] >= 1


def test_declared_compartment_exempts(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    files = _scan_tree(
        tmp_path,
        {
            "dist/exhibit/item.json": '{"id": "demo_thing"}',
        },
    )
    violations, _hits, exempted = ts.sentinel_scan(cfg, files)
    assert violations == []
    assert exempted.get("demo-comp") == 1


def test_hit_outside_compartment_still_fails(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    files = _scan_tree(tmp_path, {"dist/other/item.json": '{"id": "demo_thing"}'})
    violations, _h, _e = ts.sentinel_scan(cfg, files)
    assert [v.sentinel for v in violations] == ["demo-marker"]


def test_compartment_debt_must_exist_in_deferrals(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    root = _def(tmp_path, [])  # the debt id is absent
    result = ts.compartments_check(cfg, root)
    assert result.verdict == "fail"
    assert "D-TEST-1" in json.dumps(result.detail)


def test_compartment_debt_present_passes(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    root = _def(tmp_path, ["D-TEST-1"])
    result = ts.compartments_check(cfg, root)
    assert result.verdict == "pass"


def test_undisclosed_standin_fails_disclosed_passes(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    files = _scan_tree(
        tmp_path,
        {
            "dist/a.json": json.dumps({"capture_kind": "stand-in", "bytes": 12}),
            "dist/b.json": json.dumps({"capture_kind": "stand-in", "acquisition": "stand_in"}),
            "dist/c.json": json.dumps(
                {"capture_kind": "stand-in", "disclosure": "committed hand bytes"}
            ),
        },
    )
    findings, candidates = ts._standin_scan(files, cfg)
    assert candidates == 3
    assert [f.path for f in findings] == ["scan/dist/a.json"]


def test_contact_domain_registered_passes_unregistered_fails(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    data = tmp_path / "data"
    data.mkdir()
    (data / "sources.toml").write_text(
        '[[source]]\nid = "a"\ncontact = "ops@real.example.org"\n'
        '[[source]]\nid = "b"\ncontact = "x@sig-project.org"\n'
    )
    result, domains = ts.contact_domain_check(cfg, tmp_path)
    assert result.verdict == "fail"
    assert domains == 2
    # redaction-safe: the finding names the sentinel + path, never the domain
    assert "unregistered-contact-domain" in json.dumps(result.detail)
    assert "sig-project.org" not in json.dumps(result.detail)


def test_claim_marker_without_record_fails(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    files = _scan_tree(tmp_path, {"dist/p/index.html": "<b>human-verified</b>"})
    violations, assertions, _e, checked = ts.claim_marker_scan(cfg, files, tmp_path)
    assert assertions["human-verified"] == 1
    assert len(violations) == 1


def test_claim_marker_safe_phrasing_passes(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    files = _scan_tree(tmp_path, {"dist/p/index.html": "not human-verified"})
    violations, assertions, _e, _c = ts.claim_marker_scan(cfg, files, tmp_path)
    assert violations == []
    assert assertions["human-verified"] == 0


def test_claim_marker_with_human_record_passes(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    (tmp_path / "reviews").mkdir()
    (tmp_path / "reviews" / "r1.md").write_text(
        "reviewer: J. Operator\nrecorded: 2026-10-16\nsubject: dist/p\n"
    )
    files = _scan_tree(
        tmp_path,
        {"dist/p/index.html": "human-verified (marker:reviews/r1.md)"},
    )
    violations, assertions, _e, checked = ts.claim_marker_scan(cfg, files, tmp_path)
    assert violations == []
    assert checked == 1


def test_agent_label_marker_never_counts(tmp_path: Path) -> None:
    cfg, errs = _cfg(tmp_path)
    assert errs == []
    (tmp_path / "reviews").mkdir()
    (tmp_path / "reviews" / "r1.md").write_text(
        "reviewer: devin agent\nrecorded: 2026-10-16\nsubject: dist/p\n"
    )
    files = _scan_tree(
        tmp_path,
        {"dist/p/index.html": "human-verified (marker:reviews/r1.md)"},
    )
    violations, _a, _e, _c = ts.claim_marker_scan(cfg, files, tmp_path)
    assert len(violations) == 1
    assert "agent" in violations[0].note


def test_jurisdiction_coordinate_legs(tmp_path: Path) -> None:
    pub = tmp_path / "pub"
    pub.mkdir()
    (pub / "rows.jsonl").write_text(
        '{"lat": 35.5, "lon": -97.5}\n{"lat": 0, "lon": 0}\n{"lat": 95, "lon": 10}\n'
    )
    result = ts.jurisdiction_coordinate_check(pub)
    assert result.verdict == "fail"
    assert result.detail["evaluated"] == 3
    assert len(result.detail["violations"]) == 2


def test_coordinate_vacuous_fails() -> None:
    # candidates > 0, evaluated 0 — SIG-ENG-042 applied to probes
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        pub = Path(td)
        (pub / "rows.jsonl").write_text('{"name": "no coords"}\n')
        result = ts.jurisdiction_coordinate_check(pub)
    assert result.verdict == "fail"
    assert result.detail["evaluated"] == 0


def test_coordinate_no_input_is_skipped_never_fabricated(tmp_path: Path) -> None:
    result = ts.jurisdiction_coordinate_check(None)
    assert result.verdict == "skipped"


def test_api_release_parity(tmp_path: Path) -> None:
    rel = tmp_path / "rel"
    api = tmp_path / "api"
    (rel / "d").mkdir(parents=True)
    (api / "d").mkdir(parents=True)
    body = {"ok": True}
    (rel / "d" / "x.json").write_text(json.dumps(body))
    (api / "d" / "x.json").write_text(json.dumps(body))
    (api / "d" / "y.json").write_text(json.dumps({"ok": False}))
    result = ts.api_release_parity_check(api, rel)
    assert result.verdict == "fail"
    assert len(result.detail["violations"]) == 1


def test_number_truth(tmp_path: Path) -> None:
    pub = tmp_path / "pub"
    pub.mkdir()
    (pub / "manifest.json").write_text(json.dumps({"files": {"a.jsonl": 2}}))
    (pub / "a.jsonl").write_text("{}\n{}\n")
    assert ts.number_truth_check(pub).verdict == "pass"
    (pub / "a.jsonl").write_text("{}\n")
    assert ts.number_truth_check(pub).verdict == "fail"


def test_sweep_record_is_probe_run_1(tmp_path: Path) -> None:
    rec = ts.sweep_record("number-truth", public_dir=None, api_sample=None, release_dir=None)
    assert rec["version"] == PROBE_RUN_VERSION
    assert rec["overall"] == "partial"  # skipped leg, never a fabricated pass


def test_probe_registry_resolves_committed_tree() -> None:
    from ops.probe_registry import registry_report

    report = registry_report(REPO_ROOT)
    assert report["errors"] == []
    assert report["probe_count"] >= 10
    assert report["via_total"] == report["via_resolved"]


# The registry-contract negatives (a probe without trigger points, empty or
# unknown triggers, an unresolvable `via:`) are exercised precisely in
# docs/build/tools/test_check_round_close.py — the checker IS the validator
# (`load_sweep`); `probe_registry.registry_report` consumes the same verdict.


def test_overall_rollup_and_vacuous_rule() -> None:
    assert overall_for(["pass", "pass"]) == "pass"
    assert overall_for(["pass", "skipped"]) == "partial"
    assert overall_for(["skipped", "fail"]) == "fail"
    assert overall_for([]) == "partial"
    rec = build_record("p", {})
    assert rec["version"] == PROBE_RUN_VERSION
    assert rec["overall"] == "partial"
