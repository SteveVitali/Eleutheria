# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.73 — the ``sig-ops acceptance-sweep-11c`` gate + probe-run/1 writer.

Invariants under test (never a living record): the gate refuses (queued,
never run) while P36.72b's promote leg is outstanding or no recorded
instant was supplied; the sweep never fabricates a surface (a skipped leg
is skipped); a suppressed record is never a pass; the verbatim re-run
prompt is recorded on every refusal; and the 11C legs judge their
caller-supplied routes honestly — advertised-route mismatches, measured
budget overages, bare-UUID labels, digest mismatches, under-resolving
search queries and missing rate-limit headers are findings, zero counts
are recorded — never inferred.
"""

from __future__ import annotations

import json

from ops import acceptance_11c as a11c


def _gate_inputs(**kw) -> dict:
    base = {
        "now": "2026-11-05T13:00:00Z",  # future-ok: synthetic: a recorded test instant
        "p36_72b_promoted": True,
        "p36_72b_row_present": True,
    }
    base.update(kw)
    return base


# --- the gate ------------------------------------------------------------------


def test_gate_queued_while_promotion_leg_outstanding():
    g = a11c.evaluate_gate(_gate_inputs(p36_72b_promoted=False))
    assert g.decision == "queued"
    assert any("p36_72b_promotion" in r for r in g.refusals)


def test_gate_queued_without_a_recorded_instant():
    g = a11c.evaluate_gate(_gate_inputs(now=None))
    assert g.decision == "queued"
    assert any("window" in r for r in g.refusals)


def test_gate_queued_when_the_row_is_absent():
    g = a11c.evaluate_gate(_gate_inputs(p36_72b_promoted=False, p36_72b_row_present=False))
    assert g.decision == "queued"
    assert any("no P36.72b row" in r for r in g.refusals)


def test_gate_run_once_the_release_is_promoted():
    g = a11c.evaluate_gate(_gate_inputs())
    assert g.decision == "run"
    assert g.to_record()["rerun_prompt"] is None
    assert g.to_record()["window"] == "after P36.72 promotion"


def test_gate_advisories_never_block():
    g = a11c.evaluate_gate(_gate_inputs(routes={}, disposition_set_present=False))
    assert g.decision == "run"
    assert len(g.advisories) == 4


def test_gate_record_carries_the_verbatim_rerun_prompt():
    g = a11c.evaluate_gate(_gate_inputs(p36_72b_promoted=False))
    rec = g.to_record()
    assert rec["kind"] == "sig.acceptance-gate/1"
    assert rec["leg"] == "P36.73-sweep-packet"
    assert rec["rerun_prompt"] == (
        "implement-spec "
        "spec=docs/tickets/419_P36.73__sub-round-11c-acceptance.md "
        "live_verification=true"
    )


def test_map_read_promote_leg_absent_means_promoted(tmp_path):
    m = tmp_path / "map.toml"
    m.write_text(
        '[[row]]\nkey = "P36.72b"\n[[row.legs]]\nid = "P36.72b-other-leg"\n',
        encoding="utf-8",
    )
    inp = a11c.map_derived_inputs(m, now="2026-11-05T00:00:00Z")
    assert inp["p36_72b_promoted"] is True


def test_map_read_promote_leg_queued_means_not_promoted(tmp_path):
    m = tmp_path / "map.toml"
    m.write_text(
        '[[row]]\nkey = "P36.72b"\n[[row.legs]]\nid = "P36.72b-promote"\n',
        encoding="utf-8",
    )
    inp = a11c.map_derived_inputs(m, now="2026-11-05T00:00:00Z")
    assert inp["p36_72b_promoted"] is False
    assert inp["queued_p36_72b_legs"] == ["P36.72b-promote"]


def test_map_read_missing_row_never_assumed(tmp_path):
    m = tmp_path / "map.toml"
    m.write_text('[[row]]\nkey = "P36.70"\n', encoding="utf-8")
    inp = a11c.map_derived_inputs(m, now="2026-11-05T00:00:00Z")
    assert inp["p36_72b_row_present"] is False
    assert inp["p36_72b_promoted"] is False


def test_map_read_unreadable_is_a_usage_error(tmp_path):
    m = tmp_path / "map.toml"
    m.write_text("not toml [", encoding="utf-8")
    try:
        a11c.map_derived_inputs(m)
    except a11c.Acceptance11CError as exc:
        assert "cannot read" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected Acceptance11CError")


# --- the suppressed record -----------------------------------------------------


def test_suppressed_record_is_never_a_pass():
    rec = a11c.suppressed_record(
        reasons=["p36_72b_promotion: queued"], generated_at="2026-11-05T13:00:00Z"
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["overall"] == "suppressed"
    assert rec["checks"] == {}
    assert rec["leg"] == "P36.73-sweep-packet"
    assert rec["target"] == "11c-promoted-release"
    assert rec["rerun_prompt"].startswith("implement-spec spec=docs/tickets/419_")
    assert "Suppressed is not a pass" in rec["suppression_note"]


# --- advertised routes ----------------------------------------------------------


def test_advertised_routes_skip_when_empty():
    out = a11c.advertised_routes_leg([], fetcher=lambda u: (200, "x"))
    assert out["verdict"] == "skipped"


def test_advertised_routes_resolve_and_flag_mismatch():
    pages = {
        "https://x/": (200, "a"),
        "https://x/gone": (404, "b"),
        "https://x/down": (None, None),
    }
    out = a11c.advertised_routes_leg(
        [{"url": "https://x/"}, {"url": "https://x/gone"}, {"url": "https://x/down"}],
        fetcher=lambda u: pages[u],
    )
    assert out["verdict"] == "fail"
    assert out["resolved"] == 1


def test_advertised_routes_declared_status_honoured():
    out = a11c.advertised_routes_leg(
        [{"url": "https://x/tomb", "expect": 410}],
        fetcher=lambda u: (410, "gone"),
    )
    assert out["verdict"] == "pass"


# --- budgets --------------------------------------------------------------------


def test_budget_leg_skips_when_empty():
    out = a11c.budget_leg([], fetcher=lambda u: (200, b"x"))
    assert out["verdict"] == "skipped"


def test_budget_leg_measures_wire_bytes_against_the_ceiling():
    out = a11c.budget_leg(
        [{"url": "https://x/a", "ceiling_bytes": 10}],
        fetcher=lambda u: (200, b"1234567890"),
    )
    assert out["verdict"] == "pass"
    assert out["route_detail"][0]["measured_bytes"] == 10


def test_budget_leg_over_ceiling_is_a_finding():
    out = a11c.budget_leg(
        [{"url": "https://x/a", "ceiling_bytes": 4}],
        fetcher=lambda u: (200, b"12345"),
    )
    assert out["verdict"] == "fail"
    assert out["over_ceiling"] == 1


# --- labels ---------------------------------------------------------------------


def test_labels_leg_flags_bare_uuid_labels_and_unpinned_pages():
    body = (
        "<html><body><p>ok label</p><p>123e4567-e89b-12d3-a456-426614174000</p>"
        '<a href="/r/p-deadbeef1234/x">evidence</a></body></html>'
    )
    out = a11c.labels_leg(["https://x/p"], fetcher=lambda u: (200, body))
    assert out["verdict"] == "fail"
    assert out["uuid_only_labels"] == 1


def test_labels_leg_passes_pinned_uuid_free_pages():
    body = "<html><body><p>camera sites</p><p>release p-deadbeef1234</p></body></html>"
    out = a11c.labels_leg(["https://x/p"], fetcher=lambda u: (200, body))
    assert out["verdict"] == "pass"


# --- changelog + mirrors --------------------------------------------------------


def test_changelog_leg_requires_its_markers():
    out = a11c.changelog_leg(
        [{"url": "https://x/changes/", "required": ["p-deadbeef"]}],
        fetcher=lambda u: (200, "release p-deadbeef landed"),
    )
    assert out["verdict"] == "pass"
    out = a11c.changelog_leg(
        [{"url": "https://x/changes/", "required": ["p-cafe"]}],
        fetcher=lambda u: (200, "release p-deadbeef landed"),
    )
    assert out["verdict"] == "fail"


def test_mirrors_leg_binds_the_digest_when_supplied():
    import hashlib

    body = b'{"versions": []}'
    sha = hashlib.sha256(body).hexdigest()
    out = a11c.mirrors_leg(
        [{"url": "https://m/versions.json", "sha256": sha}],
        fetcher=lambda u: (200, body),
    )
    assert out["verdict"] == "pass"
    assert out["digest_checked"] == 1
    out = a11c.mirrors_leg(
        [{"url": "https://m/versions.json", "sha256": "0" * 64}],
        fetcher=lambda u: (200, body),
    )
    assert out["verdict"] == "fail"


def test_mirrors_leg_empty_is_skipped_not_failed():
    out = a11c.mirrors_leg([], fetcher=lambda u: (200, b"x"))
    assert out["verdict"] == "skipped"
    assert "D-P36.68-1" in out["reason"]


# --- search resolve + rate limit -------------------------------------------------


def test_search_resolve_counts_rows_against_the_minimum():
    body = json.dumps({"results": [{"a": 1}, {"b": 2}]})
    out = a11c.search_resolve_leg(
        [{"url": "https://x/s?q=ok", "min_results": 2}],
        fetcher=lambda u: (200, body),
    )
    assert out["verdict"] == "pass"
    out = a11c.search_resolve_leg(
        [{"url": "https://x/s?q=miss", "min_results": 3}],
        fetcher=lambda u: (200, body),
    )
    assert out["verdict"] == "fail"


def test_ratelimit_leg_reads_response_headers():
    out = a11c.ratelimit_leg(
        ["https://api/v1/dossier/x"],
        fetcher=lambda u: (200, {"ratelimit-remaining": "59"}),
    )
    assert out["verdict"] == "pass"
    out = a11c.ratelimit_leg(["https://api/v1/dossier/x"], fetcher=lambda u: (200, {}))
    assert out["verdict"] == "fail"


def test_ratelimit_leg_unreachable_is_partial():
    out = a11c.ratelimit_leg(["https://api/x"], fetcher=lambda u: (None, {}))
    assert out["verdict"] == "partial"


# --- the full record -------------------------------------------------------------


def test_run_sweep_overall_and_skipped_legs():
    rec = a11c.run_sweep(
        routes={},
        now="2026-11-05T13:00:00Z",
        fetch_text=lambda u: (200, "x"),
        fetch_bytes=lambda u: (200, b"x"),
        fetch_headers=lambda u: (200, {}),
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["probe"] == "sig-11c-acceptance"
    assert rec["overall"] == "partial"  # every leg skipped with a reason
    assert all(c["verdict"] == "skipped" for c in rec["checks"].values())


def test_run_sweep_a_failing_leg_marks_the_record():
    rec = a11c.run_sweep(
        routes={"advertised_routes": [{"url": "https://x/gone"}]},
        now="2026-11-05T13:00:00Z",
        fetch_text=lambda u: (404, "x"),
    )
    assert rec["overall"] == "fail"


# --- the CLI ---------------------------------------------------------------------


def test_main_check_writes_the_suppressed_record(tmp_path, capsys):
    out = tmp_path / "rec.json"
    m = tmp_path / "map.toml"
    m.write_text(
        '[[row]]\nkey = "P36.72b"\n[[row.legs]]\nid = "P36.72b-promote"\n',
        encoding="utf-8",
    )
    rc = a11c.main(
        [
            "--check",
            "--map",
            str(m),
            "--at",
            "2026-11-05T13:00:00Z",
            "--record-out",
            str(out),
        ]
    )
    assert rc == 42
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["overall"] == "suppressed"
    assert rec["window"] == "after P36.72 promotion"


def test_main_usage_error_exit_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    rc = a11c.main(["--inputs", str(bad)])
    assert rc == 2
