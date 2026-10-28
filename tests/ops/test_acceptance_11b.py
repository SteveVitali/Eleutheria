# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.64 — the ``sig-ops acceptance-sweep-11b`` gate + probe-run/1 writer.

Invariants under test (never a living record): the gate refuses (queued,
never run) while P35.63's promotion leg is outstanding or no recorded
instant was supplied; the sweep never fabricates a surface (a skipped leg
is skipped); a suppressed record is never a pass; the verbatim re-run
prompt is recorded on every refusal; and the surface legs judge their
caller-supplied routes honestly (unpinned pages, non-410 aliases, UUID
labels, parity mismatches and missing disclosures are findings, zero
counts are recorded — never inferred).
"""

from __future__ import annotations

import json
import sys

from ops import acceptance_11b as a11b


def _gate_inputs(**kw) -> dict:
    base = {
        "now": "2026-10-25T05:30:00Z",  # future-ok: synthetic: a recorded test instant
        "p35_63_promoted": True,
        "p35_63_row_present": True,
    }
    base.update(kw)
    return base


# --- the gate ------------------------------------------------------------------


def test_gate_queued_while_promotion_leg_outstanding():
    g = a11b.evaluate_gate(_gate_inputs(p35_63_promoted=False))
    assert g.decision == "queued"
    assert any("p35_63_promotion" in r for r in g.refusals)


def test_gate_queued_without_a_recorded_instant():
    g = a11b.evaluate_gate(_gate_inputs(now=None))
    assert g.decision == "queued"
    assert any("window" in r for r in g.refusals)


def test_gate_run_once_the_release_is_promoted():
    g = a11b.evaluate_gate(_gate_inputs())
    assert g.decision == "run"
    assert g.to_record()["rerun_prompt"] is None
    assert g.to_record()["window"] == "after P35.63 promotion"


def test_gate_advisories_never_block():
    g = a11b.evaluate_gate(_gate_inputs(routes={}, disposition_set_present=False))
    assert g.decision == "run"
    assert len(g.advisories) == 3


def test_gate_record_carries_the_verbatim_rerun_prompt():
    g = a11b.evaluate_gate(_gate_inputs(p35_63_promoted=False))
    rec = g.to_record()
    assert rec["kind"] == "sig.acceptance-gate/1"
    assert rec["leg"] == "P35.64-sweep-packet"
    assert rec["rerun_prompt"] == (
        "implement-spec "
        "spec=docs/tickets/342_P35.64__sub-round-11b-acceptance.md "
        "live_verification=true"
    )


def test_map_read_promotion_leg_absent_means_promoted(tmp_path):
    m = tmp_path / "map.toml"
    m.write_text(
        '[[row]]\nkey = "P35.63"\n[[row.legs]]\nid = "P35.63-dispatch-stage-verify-readout"\n',
        encoding="utf-8",
    )
    inp = a11b.map_derived_inputs(m, now="2026-10-25T00:00:00Z")
    # future-ok: synthetic instant in the line above
    assert inp["p35_63_promoted"] is True
    assert inp["queued_p35_63_legs"] == ["P35.63-dispatch-stage-verify-readout"]


def test_map_read_promotion_leg_present_means_queued(tmp_path):
    m = tmp_path / "map.toml"
    m.write_text(
        '[[row]]\nkey = "P35.63"\n'
        '[[row.legs]]\nid = "P35.63-dispatch-stage-verify-readout"\n'
        '[[row.legs]]\nid = "P35.63-promote-under-hg11"\n',
        encoding="utf-8",
    )
    inp = a11b.map_derived_inputs(m, now="2026-10-25T00:00:00Z")
    # future-ok: synthetic instant in the line above
    assert inp["p35_63_promoted"] is False
    assert "P35.63-promote-under-hg11" in inp["queued_p35_63_legs"]


def test_map_read_absent_row_recorded_not_assumed(tmp_path):
    m = tmp_path / "map.toml"
    m.write_text('[[row]]\nkey = "P35.62"\n', encoding="utf-8")
    inp = a11b.map_derived_inputs(m, now="2026-10-25T00:00:00Z")
    # future-ok: synthetic instant in the line above
    assert inp["p35_63_promoted"] is False
    assert inp["p35_63_row_present"] is False


# --- the suppressed record ------------------------------------------------------


def test_suppressed_record_is_never_a_pass():
    rec = a11b.suppressed_record(
        reasons=["p35_63_promotion: still queued"],
        generated_at="2026-10-25T00:00:00Z",  # future-ok: synthetic: a recorded instant
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["overall"] == "suppressed"
    assert rec["checks"] == {}
    assert "342_P35.64" in rec["rerun_prompt"]
    assert "after P35.63 promotion" in rec["window"]


# --- the surface legs ------------------------------------------------------------


def _fetch_ok(body: str = "<html><body data-release='p-abcdef12'></body></html>"):
    def fetch(url):
        return 200, body

    return fetch


def test_release_routes_leg_skipped_without_routes():
    leg = a11b.release_routes_leg([], fetcher=_fetch_ok())
    assert leg["verdict"] == "skipped"
    assert "reason" in leg


def test_release_routes_leg_unpinned_page_is_a_finding():
    leg = a11b.release_routes_leg(
        ["https://x.test/releases/"], fetcher=_fetch_ok("<html>no pin</html>")
    )
    assert leg["verdict"] == "fail"
    assert leg["unpinned"] == 1


def test_release_routes_leg_passes_a_pinned_page():
    leg = a11b.release_routes_leg(["https://x.test/releases/"], fetcher=_fetch_ok())
    assert leg["verdict"] == "pass"
    assert leg["unpinned"] == 0


def test_withdrawal_leg_410_tombstone_required():
    fetch = lambda url: (410, "<h1>withdrawn</h1>")  # noqa: E731
    leg = a11b.withdrawal_leg(["https://x.test/r/p-abc12345/"], fetcher=fetch)
    assert leg["verdict"] == "pass"
    assert leg["aliases_410"] == 1


def test_withdrawal_leg_200_alias_is_a_finding():
    fetch = lambda url: (200, "still serving")  # noqa: E731
    leg = a11b.withdrawal_leg(["https://x.test/r/p-abc12345/"], fetcher=fetch)
    assert leg["verdict"] == "fail"


def test_withdrawal_leg_410_without_tombstone_is_a_finding():
    fetch = lambda url: (410, "")  # noqa: E731
    leg = a11b.withdrawal_leg(["https://x.test/r/p-abc12345/"], fetcher=fetch)
    assert leg["verdict"] == "fail"


def test_network_leg_uuid_only_label_is_a_finding():
    body = "<html><body><a>a1b2c3d4-0000-4000-8000-abcdef012345</a></body></html>"
    leg = a11b.network_leg("https://x.test/network/", fetcher=_fetch_ok(body))
    assert leg["verdict"] == "fail"
    assert leg["uuid_only_labels"] == 1


def test_network_leg_clean_page_passes():
    body = (
        "<html><body><figure>"
        "<img src='x.png'/><figcaption>fig</figcaption>"
        "<a href='/r/p-abc12345/fig/'>evidence</a></figure>"
        "</body></html>"
    )
    leg = a11b.network_leg("https://x.test/network/", fetcher=_fetch_ok(body))
    assert leg["verdict"] == "pass"
    assert leg["uuid_only_labels"] == 0
    assert leg["figures_without_evidence_link"] == 0


def test_parity_leg_status_mismatch_is_a_finding():
    def fetch(url):
        return (200, "ok") if url.startswith("https://api") else (404, None)

    leg = a11b.parity_leg(
        [{"api": "https://api.test/r/x", "web": "https://x.test/r/x"}],
        fetcher=fetch,
    )
    assert leg["verdict"] == "fail"


def test_disclosure_leg_missing_wording_is_a_finding():
    leg = a11b.disclosure_leg(
        [
            {
                "url": "https://x.test/methodology/",
                "required": ["no human check performed"],
            }
        ],
        fetcher=_fetch_ok("<html>provisional</html>"),
    )
    assert leg["verdict"] == "fail"
    assert leg["route_detail"][0]["missing"] == ["no human check performed"]


def test_tiles_leg_unreachable_tile_is_a_finding():
    fetch = lambda url: (None, None)  # noqa: E731
    leg = a11b.tiles_leg(["https://x.test/tiles/sites.pmtiles"], fetcher=fetch)
    assert leg["verdict"] == "fail"
    assert leg["unreachable"] == 1


def test_sweep_overall_partial_when_a_leg_skips():
    rec = a11b.run_sweep(routes={"release_routes": ["https://x.test/releases/"]})
    assert rec["overall"] == "partial"
    assert rec["checks"]["withdrawal"]["verdict"] == "skipped"
    assert rec["checks"]["release_routes"]["verdict"] in ("pass", "fail", "partial")


def test_sweep_overall_fail_on_a_finding():
    fetch = lambda url: (200, "unpinned")  # noqa: E731
    rec = a11b.run_sweep(routes={"release_routes": ["https://x.test/releases/"]}, fetch_text=fetch)
    assert rec["overall"] == "fail"
    assert rec["version"] == "sig.probe-run/1"


# --- the CLI ---------------------------------------------------------------------


def test_cli_check_queued_exits_42(tmp_path, capsys):
    m = tmp_path / "map.toml"
    m.write_text(
        '[[row]]\nkey = "P35.63"\n[[row.legs]]\nid = "P35.63-promote-under-hg11"\n',
        encoding="utf-8",
    )
    rec = tmp_path / "out.json"
    rc = a11b.main(
        ["--check", "--map", str(m), "--at", "2026-10-25T00:00:00Z", "--record-out", str(rec)]
    )  # future-ok: synthetic instant on the line above
    assert rc == 42
    record = json.loads(rec.read_text(encoding="utf-8"))
    assert record["overall"] == "suppressed"
    assert "342_P35.64" in record["rerun_prompt"]


def test_cli_bad_dossier_arg_exits_2(tmp_path, capsys):
    m = tmp_path / "map.toml"
    m.write_text('[[row]]\nkey = "P35.63"\n', encoding="utf-8")
    rc = a11b.main(["--map", str(m), "--at", "2026-10-25T00:00:00Z", "--dossier", "nourl"])
    # future-ok: synthetic instant on the line above
    assert rc == 2


def test_cli_routes_file_must_be_an_object(tmp_path, capsys):
    m = tmp_path / "map.toml"
    m.write_text('[[row]]\nkey = "P35.63"\n', encoding="utf-8")
    rf = tmp_path / "routes.json"
    rf.write_text("[1,2]", encoding="utf-8")
    rc = a11b.main(
        ["--map", str(m), "--at", "2026-10-25T00:00:00Z", "--routes-file", str(rf)]
    )  # future-ok: synthetic instant on the line above
    assert rc == 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(__import__("pytest").main([__file__, "-q"]))
