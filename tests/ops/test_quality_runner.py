# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The quality harness runner (P34.44a, SIG-CONF-008/013): placement
selection, evaluated/candidate counts in the records, seam-deferred checks
reporting not_evaluable, the file scans for GQ-14/GQ-27, and the spine
evaluators' counting semantics over a stub connection."""

from __future__ import annotations

import json
from pathlib import Path

from exports.quality import PROBE_RUN_VERSION, REPORT_VERSION, load_registry
from ops.quality import (
    SEAM_DEFERRALS,
    EvalContext,
    eval_gq05,
    eval_gq07,
    eval_gq13,
    eval_gq14,
    eval_gq15,
    eval_gq18,
    eval_gq24,
    eval_gq27,
    probe_run_record,
    run_quality_probe,
)


class _Cursor:
    def __init__(self, cols: list[str], rows: list[tuple]) -> None:
        self.description = [type("D", (), {"name": c})() for c in cols]
        self._rows = rows

    def fetchall(self) -> list[tuple]:
        return self._rows


class FakeConn:
    """A stub psycopg connection: canned (cols, rows) per SQL substring."""

    def __init__(self, responses: dict[str, tuple[list[str], list[tuple]]]) -> None:
        self.responses = responses
        self.seen: list[str] = []

    def execute(self, sql: str, params: tuple = ()) -> _Cursor:
        self.seen.append(sql)
        for needle, (cols, rows) in self.responses.items():
            if needle in sql:
                return _Cursor(cols, rows)
        return _Cursor([], [])


# --- runner + records -------------------------------------------------------


def test_m_run_emits_report_and_probe_run() -> None:
    report = run_quality_probe(EvalContext(), placement="M", target="test")
    assert report["version"] == REPORT_VERSION
    probe = probe_run_record(report)
    assert probe["version"] == PROBE_RUN_VERSION
    assert probe["probe"] == "sig-quality"
    assert probe["placement"] == "M"
    assert "evaluated" in probe["checks"][0] and "offered" in probe["checks"][0]


def test_m_run_selects_m_placed_checks_only() -> None:
    report = run_quality_probe(EvalContext(), placement="M")
    placed = {c.check_id for c in load_registry().checks if "M" in c.placement}
    assert {c["id"] for c in report["checks"]} == placed


def test_seam_deferred_checks_report_not_evaluable_with_reason() -> None:
    report = run_quality_probe(EvalContext(), placement="M")
    rows = {c["id"]: c for c in report["checks"]}
    for check_id, seam in SEAM_DEFERRALS.items():
        if check_id in rows:
            assert rows[check_id]["outcome"] == "not_evaluable"
            assert seam.split("(")[1].rstrip(")") in rows[check_id]["reason"]


def test_spine_checks_without_connection_are_not_evaluable_not_pass() -> None:
    """SIG-ENG-042: no DSN ⇒ the spine checks can't run — they report
    not_evaluable, and the run overall is never a clean pass."""
    report = run_quality_probe(EvalContext(), placement="M")
    spine_rows = [c for c in report["checks"] if c["id"] in {"GQ-03", "GQ-07", "GQ-24"}]
    assert all(c["outcome"] == "not_evaluable" for c in spine_rows)
    assert "no spine connection" in spine_rows[0]["reason"]
    assert report["summary"]["overall"] != "pass"


def test_placement_without_checks_reports_empty_run() -> None:
    """An I-only placement run evaluates what it can (registry-declared I
    checks have no harness evaluators — the sink-side hooks are the ingest
    pipeline's), and says so honestly."""
    report = run_quality_probe(EvalContext(), placement="I")
    assert {c["id"] for c in report["checks"]} == {
        c.check_id for c in load_registry().checks if "I" in c.placement
    }
    assert all(c["outcome"] == "not_evaluable" for c in report["checks"])


def test_report_carries_registry_digest() -> None:
    report = run_quality_probe(EvalContext(), placement="M")
    assert report["registry"]["digest"] == load_registry().digest


# --- spine evaluators over a stub connection ---------------------------------


def test_gq24_counts_inferential_auto_writes() -> None:
    conn = FakeConn(
        {
            "FROM camera_site_execution": (["run_key"], [("rk1",)]),
            "disposition = 'auto_write'": (
                ["match_id", "match_tier", "tier_label", "run_key"],
                [
                    # the namespace variant is a deterministic join — legal
                    ("m1", 1, "1g:shared_upstream_ref", "rk1"),
                    ("m2", 3, "3g:coincident_point", "rk1"),
                    ("m3", 4, "4g:proximate_unique", "rk1"),
                    ("m4", 0, "0g:unknown", "rk1"),
                    # an unknown 1g label is not a namespace join — fail closed
                    ("m5", 1, "1g:unlabelled_inference", "rk1"),
                    # a superseded run's inferential auto-write: disclosed,
                    # never re-judged — the append-only spine keeps it forever
                    ("m6", 3, "3g:coincident_point", "rk0"),
                ],
            ),
            "count(*) AS n FROM camera_site_match": (["n"], [(4,)]),
        }
    )
    m = eval_gq24(EvalContext(conn=conn))
    assert m.offered == 4 and m.evaluated == 4 and m.measured == 3
    assert m.detail["latest_run_key"] == "rk1"
    assert m.detail["historical_inferential_auto_writes"] == 1


def test_gq24_is_never_a_vacuous_pass() -> None:
    """No completed execution, or a latest run with no inferential-tier
    decisions, reports evaluated=0 — the ratchet's vacuous-pass guard fails it."""
    empty = FakeConn({})
    m = eval_gq24(EvalContext(conn=empty))
    assert m.evaluated == 0 and m.measured is None
    no_inferential = FakeConn(
        {
            "FROM camera_site_execution": (["run_key"], [("rk9",)]),
            "count(*) AS n FROM camera_site_match": (["n"], [(0,)]),
        }
    )
    m2 = eval_gq24(EvalContext(conn=no_inferential))
    assert m2.evaluated == 0 and m2.measured is None


def test_gq07_counts_publisher_strings_and_bad_literals() -> None:
    conn = FakeConn(
        {
            "camera_operator": (
                ["claim_id", "value_text", "object_entity", "entity_type"],
                [
                    ("c1", None, "e1", "organization"),
                    ("c2", "unknown", None, None),
                    ("c3", "Flock Safety", None, None),
                    ("c4", None, "e2", "physical_asset"),
                ],
            )
        }
    )
    m = eval_gq07(EvalContext(conn=conn))
    assert m.measured == 2 and m.detail["publisher_blocklist_hits"] == 1


def test_gq13_counts_uncontested_disagreements() -> None:
    conn = FakeConn(
        {
            "FROM resolution": (
                ["resolution_id", "contradiction_state", "dissent_n", "distinct_vals"],
                [
                    ("r1", "uncontested", 0, 2),  # violation
                    ("r2", "uncontested", 0, 1),  # unanimous — not in population
                    ("r3", "unresolved_conflict", 0, 3),  # contested
                    ("r4", "uncontested", 2, 2),  # dissent recorded
                ],
            )
        }
    )
    m = eval_gq13(EvalContext(conn=conn))
    assert m.offered == 4 and m.evaluated == 3 and m.measured == 1


def test_gq15_counts_undated_epoch_and_duplicate_edges() -> None:
    conn = FakeConn(
        {
            "FROM relationship": (
                [
                    "relationship_id",
                    "from_entity",
                    "to_entity",
                    "edge_type",
                    "has_observed",
                    "undated",
                    "valid_from_kind",
                    "epoch_start",
                ],
                [
                    ("r1", "a", "b", "operates", False, True, "unknown", False),
                    ("r2", "a", "b", "operates", False, True, "unknown", False),
                    ("r3", "c", "d", "operates", True, False, "exact", True),
                    ("r4", "e", "f", "integrates_with", False, False, "never", False),
                ],
            )
        }
    )
    m = eval_gq15(EvalContext(conn=conn))
    # undated: r1+r2 (2), epoch: r3 (1), duplicates: (a,b,operates) x2 → 1
    assert m.measured == 4
    assert m.detail == {"undated": 2, "epoch_start": 1, "duplicate_edges": 1}


def test_gq18_worst_source_share() -> None:
    conn = FakeConn(
        {
            "WITH src": (
                ["source_id", "total", "bound"],
                [("src-a", 10, 8), ("src-b", 4, 4), ("(unbound)", 2, 0)],
            )
        }
    )
    m = eval_gq18(EvalContext(conn=conn))
    assert m.measured == 0.0  # the unbound group floors the worst-source share
    assert m.offered == 16


def test_gq05_not_evaluable_without_two_runs() -> None:
    conn = FakeConn(
        {
            "camera_latitude": (
                ["source_id", "subject_id", "run_id", "lat", "lon"],
                [("s1", "subj1", "run1", 1.0, 1.0)],
            ),
            "FROM ingest_run": (["run_id"], [("run1",)]),
        }
    )
    m = eval_gq05(EvalContext(conn=conn))
    # one run ⇒ nothing comparable — evaluated 0, and the engine will fail it
    assert m.evaluated == 0 and m.offered == 1


def test_gq05_moved_subjects() -> None:
    conn = FakeConn(
        {
            "camera_latitude": (
                ["source_id", "subject_id", "run_id", "lat", "lon"],
                [
                    ("s1", "subj1", "run1", 1.0, 1.0),
                    ("s1", "subj1", "run2", 1.001, 1.0),  # moved 0.001 > 0.0005
                    ("s1", "subj2", "run1", 2.0, 2.0),
                    ("s1", "subj2", "run2", 2.0, 2.0),  # stable
                ],
            ),
            "FROM ingest_run": (["run_id"], [("run1",), ("run2",)]),
        }
    )
    m = eval_gq05(EvalContext(conn=conn))
    assert m.evaluated == 2 and m.measured == 0.5 and m.detail["moved"] == 1


# --- file scans --------------------------------------------------------------


def _write_sites(d: Path, rows: list[dict]) -> None:
    (d / "comp").mkdir(parents=True, exist_ok=True)
    (d / "comp" / "sites.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_gq14_flags_uuid_and_missing_labels(tmp_path: Path) -> None:
    _write_sites(
        tmp_path,
        [
            {"entity_id": "a", "label": "Camera 12"},
            {"entity_id": "b", "label": "83e9a0f4-1234-4abc-9def-000000000000"},
            {"entity_id": "c", "label": ""},
            {"entity_id": "d"},  # no label key at all
        ],
    )
    m = eval_gq14(EvalContext(scan_dir=tmp_path))
    assert m.offered == 4 and m.measured == 3
    assert m.detail["uuid_labels"] == 1 and m.detail["unlabeled"] == 2


def test_gq14_not_evaluable_without_artifacts(tmp_path: Path) -> None:
    m = eval_gq14(EvalContext(scan_dir=tmp_path))
    assert m.not_evaluable_reason


def test_gq27_flags_claim_phrases_and_unbased_figures(tmp_path: Path) -> None:
    (tmp_path / "report.json").write_text(
        json.dumps(
            {
                "version": "sig.evaluation/1",
                "verdict": "independently reviewed",  # no B5 marker
                "metrics": [{"name": "precision", "value": 0.9}],  # no basis
            }
        )
    )
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured and m.measured >= 2


def test_gq27_passes_labelled_figures(tmp_path: Path) -> None:
    # A figure naming its basis class inside a document carrying the report
    # context (population, source-mix digest, ruleset, window) passes — the
    # context is inherited from the enclosing object; n is the figure's own.
    (tmp_path / "ok.json").write_text(
        json.dumps(
            {
                "version": "sig.evaluation/1",
                "population": "auto-write match decisions",
                "source_mix_digest": "sha256:feed",
                "ruleset": "camera_site_rules v3-interim",
                "window": "2026-10-14T14:00Z run",  # future-ok: synthetic: fixture window label
                "metrics": [{"name": "p", "value": 0.9, "n": 70, "basis_class": "B2"}],
            }
        )
    )
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured == 0 and m.evaluated == 1


def test_gq27_figure_needs_its_full_context_and_one_basis(tmp_path: Path) -> None:
    # A labelled figure still fails when the statement's context is absent —
    # and two different basis labels is exactly the ambiguity GQ-27 bans.
    (tmp_path / "bare.json").write_text(
        json.dumps({"metrics": [{"name": "p", "value": 0.9, "basis_class": "B2"}]})
    )
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured == 1
    assert "missing context" in m.detail["violations"][0]
    (tmp_path / "bare.json").write_text(
        json.dumps(
            {
                "population": "x",
                "source_mix_digest": "d",
                "ruleset": "r",
                "window": "w",
                "metrics": [
                    {"name": "p", "value": 0.9, "n": 5, "basis_class": "B2", "basis": "agent"}
                ],
            }
        )
    )
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured == 1 and "more than one basis" in m.detail["violations"][0]


def test_gq27_verified_is_a_claim_phrase(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("the corpus was verified end to end\n")
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured == 1
    (tmp_path / "doc.md").write_text("unverified estimates are labelled agent\n")
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured == 0  # "unverified" is a disclosure, not a claim


def test_gq27_text_claim_needs_b5(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("this result was certified by review\n")
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured == 1
    (tmp_path / "doc.md").write_text("certified by review (basis: B5 campaign c1)\n")
    m = eval_gq27(EvalContext(scan_dir=tmp_path))
    assert m.measured == 0


# --- read-only posture -------------------------------------------------------


def test_runner_never_issues_writes() -> None:
    """The evaluators are SELECT-only; assert the recorded SQL is read-only."""
    conn = FakeConn(
        {
            "duplicate_members": (["total", "duplicate_members"], [(0, 0)]),
            "camera_latitude": (["source_id", "subject_id", "run_id", "lat", "lon"], []),
            "FROM ingest_run": (["run_id"], []),
            "ST_DWithin": (["a_src", "b_src", "a_within", "a_n", "b_n"], []),
            "FROM camera_site_match": (["match_id", "match_tier", "tier_label"], []),
            "FROM relationship": (
                [
                    "relationship_id",
                    "from_entity",
                    "to_entity",
                    "edge_type",
                    "has_observed",
                    "undated",
                    "valid_from_kind",
                    "epoch_start",
                ],
                [],
            ),
            "FROM resolution": (
                ["resolution_id", "contradiction_state", "dissent_n", "distinct_vals"],
                [],
            ),
            "WITH src": (["source_id", "total", "bound"], []),
            "FROM entity": (["deployments", "with_operator"], [(0, 0)]),
            "camera_operator": (["claim_id", "value_text", "object_entity", "entity_type"], []),
        }
    )
    report = run_quality_probe(EvalContext(conn=conn), placement="M", target="t")
    assert report["version"] == REPORT_VERSION
    for sql in conn.seen:
        assert "INSERT" not in sql.upper()
        assert "UPDATE" not in sql.upper()
        assert "DELETE" not in sql.upper()
        assert "CREATE" not in sql.upper()
        assert "ALTER" not in sql.upper()
        assert "DROP" not in sql.upper()


def test_connect_readonly_sets_the_audit_posture() -> None:
    import inspect

    from ops import quality as q

    src = inspect.getsource(q.connect_readonly)
    assert "default_transaction_read_only" in src
    assert "statement_timeout" in src
