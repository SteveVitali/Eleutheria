# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.47 — the ``sig-ops acceptance-sweep`` gate + probe-run/1 writer.

Invariants under test (never a living record): the gate refuses (queued,
never run) while P34.46's L2 leg is outstanding or the window floor has
not passed; the sweep never fabricates a surface (a skipped leg is
skipped); handle values are never in the record; a claim word in a
disclosed context is not an undisclosed hit; RI-01 reports not-checked —
never passed — when the handle list is absent.
"""

from __future__ import annotations

import json
import subprocess
import sys

from support import REPO_ROOT

from ops import acceptance


def _gate_inputs(**kw) -> dict:
    base = {
        "now": "2026-10-09T12:00:00Z",
        "p34_46_l2_landed": True,
        "p34_46_l3_soak_read": True,
        "handle_list_present": True,
    }
    base.update(kw)
    return base


# --- the gate ------------------------------------------------------------------


def test_gate_queued_before_window():
    g = acceptance.evaluate_gate(_gate_inputs(now="2026-10-09T12:00:00Z"))
    assert g.decision == "queued"
    assert any("window" in r for r in g.refusals)


def test_gate_queued_without_l2():
    g = acceptance.evaluate_gate(_gate_inputs(now="2026-10-20T15:00:00Z", p34_46_l2_landed=False))
    assert g.decision == "queued"
    assert any("p34_46_l2" in r for r in g.refusals)


def test_gate_run_after_l2_in_window():
    g = acceptance.evaluate_gate(_gate_inputs(now="2026-10-15T09:00:00Z"))
    assert g.decision == "run"
    assert g.to_record()["rerun_prompt"] is None


def test_gate_soak_and_handle_list_are_advisories_not_blockers():
    g = acceptance.evaluate_gate(
        _gate_inputs(
            now="2026-10-15T09:00:00Z",
            p34_46_l3_soak_read=False,
            handle_list_present=False,
        )
    )
    assert g.decision == "run"
    assert len(g.advisories) == 2


def test_gate_record_carries_rerun_prompt():
    g = acceptance.evaluate_gate(_gate_inputs(now="2020-01-01T00:00:00Z"))
    rec = g.to_record()
    assert rec["kind"] == "sig.acceptance-gate/1"
    assert "259_P34.47" in rec["rerun_prompt"]


def test_map_derived_inputs(tmp_path):
    mp = tmp_path / "m.toml"
    mp.write_text(
        '[[row]]\nkey = "P34.46"\n[[row.legs]]\nid = "P34.46-slot"\n'
        '[[row.legs]]\nid = "P34.46-soak"\n',
        encoding="utf-8",
    )
    inputs = acceptance.map_derived_inputs(
        mp, now="2026-10-09T12:00:00Z", handle_list=tmp_path / "absent.txt"
    )
    assert inputs["p34_46_l2_landed"] is False
    assert inputs["p34_46_l3_soak_read"] is False
    assert inputs["handle_list_present"] is False
    mp.write_text('[[row]]\nkey = "P34.46"\n[[row.legs]]\nid = "P34.46-soak"\n')
    inputs = acceptance.map_derived_inputs(mp, now="2026-10-15T00:00:00Z")
    assert inputs["p34_46_l2_landed"] is True
    assert inputs["p34_46_l3_soak_read"] is False


# --- the scanners ---------------------------------------------------------------


def test_scan_text_counts_only_never_values(tmp_path):
    handles = ["testhandle-xyzzy"]
    text = "a line\ncreated by testhandle-xyzzy and again testhandle-xyzzy\n"
    res = acceptance.scan_text(text, handles)
    assert res["handle_hits"] == 2
    assert "testhandle-xyzzy" not in json.dumps(res)


def test_scan_text_word_disclosed_vs_undisclosed():
    text = (
        "Reviewed by our editorial board\n"  # both undisclosed
        "checked automatically — no human check performed\n"  # disclosed
        "the download is complete\n"  # undisclosed
        "incomplete data\n"  # disclosed ('incomplete' marker on the line)
        "Reviewed: pending\n"  # 'pending' discloses
    )
    res = acceptance.scan_text(text, [])
    words = res["claim_words"]
    assert words["Reviewed"]["hits"] == 2
    assert words["Reviewed"]["undisclosed"] == 1  # line 5 disclosed by 'pending'
    assert words["editorial board"]["undisclosed"] == 1
    assert words["complete"]["hits"] == 1
    assert words["complete"]["undisclosed"] == 1
    assert "incomplete" not in res["claim_words"].get("complete", {})


def test_scan_text_word_boundaries():
    res = acceptance.scan_text("incomplete and completing\n", [])
    assert res["claim_words"].get("complete", {}).get("hits", 0) == 0


def test_scan_bytes_counts():
    handles = ["hh-secret"]
    res = acceptance.scan_bytes(b"\x00\xff certified hh-secret bytes", handles)
    assert res["handle_hits"] == 1
    assert res["claim_words"]["certified"]["undisclosed"] == 1


# --- the legs --------------------------------------------------------------------


def test_surface_leg_fail_on_hits():
    fetches = {
        "https://e/a": (200, "clean page\n"),
        "https://e/b": (200, "this page is complete\n"),
    }
    leg = acceptance.surface_leg(list(fetches), ["nope"], fetcher=lambda u: fetches[u])
    assert leg["verdict"] == "fail"
    assert leg["undisclosed_word_hits"] == 1
    assert leg["handle_hits"] == 0


def test_surface_leg_partial_on_unreachable():
    fetches = {"https://e/a": (None, None), "https://e/b": (200, "fine\n")}
    leg = acceptance.surface_leg(list(fetches), [], fetcher=lambda u: fetches[u])
    assert leg["verdict"] == "partial"
    assert leg["unreachable"] == 1


def test_surface_leg_skipped_without_urls():
    assert acceptance.surface_leg([], [])["verdict"] == "skipped"


def test_listing_leg(tmp_path):
    lst = tmp_path / "listing.txt"
    lst.write_text("obj/a.json\nobj/b-tiles.pmtiles\n", encoding="utf-8")
    leg = acceptance.listing_leg(lst, ["hh-x"])
    assert leg["verdict"] == "pass" and leg["objects"] == 2
    lst.write_text("obj/hh-x.json\n", encoding="utf-8")
    assert acceptance.listing_leg(lst, ["hh-x"])["verdict"] == "fail"
    assert acceptance.listing_leg(None, [])["verdict"] == "skipped"


# --- run_sweep --------------------------------------------------------------------


_CADENCE = REPO_ROOT / "tests" / "ops" / "fixtures" / "acceptance_cadence.toml"


def _fake_crawl(cmd, capture_output, text, check):
    class R:
        returncode = 0
        stdout = json.dumps(
            {"verdict": "pass", "handles_checked": 3, "hits": 0, "files_with_hits": 0}
        )
        stderr = ""

    return R()


def test_run_sweep_pass(tmp_path):
    handles = tmp_path / "handles.txt"
    handles.write_text("hh-x\n", encoding="utf-8")
    listing = tmp_path / "lst.txt"
    listing.write_text("obj/a\n", encoding="utf-8")
    rec = acceptance.run_sweep(
        site_urls=["u"],
        api_urls=["a"],
        tile_urls=["t"],
        listing_file=listing,
        handle_list=handles,
        l3_soak_read=True,
        reads={"scheduler": {"triggers": 2}, "billing_export": {"present": True}},
        now="2026-10-15T00:00:00Z",
        cadence_path=_CADENCE,
        fetch_text=lambda u: (200, "clean body\n"),
        fetch_bytes=lambda u: (206, b"clean bytes"),
        check_absent=lambda u: (True, "404"),
        crawl_runner=_fake_crawl,
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["overall"] == "pass"
    assert rec["checks"]["absence_probe"]["verdict"] == "pass"
    assert rec["checks"]["ri01"]["verdict"] == "pass"
    assert "hh-x" not in json.dumps(rec)


def test_run_sweep_exit5_skipped_until_soak(tmp_path):
    handles = tmp_path / "handles.txt"
    handles.write_text("hh-x\n", encoding="utf-8")
    rec = acceptance.run_sweep(
        site_urls=["u"],
        api_urls=[],
        tile_urls=[],
        listing_file=None,
        handle_list=handles,
        l3_soak_read=False,
        cadence_path=_CADENCE,
        fetch_text=lambda u: (200, "clean\n"),
        check_absent=lambda u: (True, "404"),
        crawl_runner=_fake_crawl,
    )
    assert rec["checks"]["exit_item_5_soak"]["verdict"] == "skipped"
    assert rec["checks"]["reads"]["verdict"] == "skipped"
    assert rec["overall"] == "partial"


def test_run_sweep_ri01_not_checked_when_list_absent(tmp_path):
    rec = acceptance.run_sweep(
        site_urls=["u"],
        api_urls=[],
        tile_urls=[],
        listing_file=None,
        handle_list=tmp_path / "absent.txt",
        cadence_path=_CADENCE,
        fetch_text=lambda u: (200, "clean\n"),
        check_absent=lambda u: (True, "404"),
        crawl_runner=_fake_crawl,
    )
    assert rec["checks"]["ri01"]["verdict"] == "skipped"
    assert rec["checks"]["repo_tip"]["verdict"] == "skipped"
    assert rec["overall"] != "pass"


def test_run_sweep_fail_on_handle_hit(tmp_path):
    handles = tmp_path / "handles.txt"
    handles.write_text("hh-x\n", encoding="utf-8")
    rec = acceptance.run_sweep(
        site_urls=["u"],
        api_urls=[],
        tile_urls=[],
        listing_file=None,
        handle_list=handles,
        cadence_path=_CADENCE,
        fetch_text=lambda u: (200, "made by hh-x\n"),
        check_absent=lambda u: (True, "404"),
        crawl_runner=_fake_crawl,
    )
    assert rec["overall"] == "fail"
    assert rec["checks"]["ri01"]["verdict"] == "fail"


def test_suppressed_record():
    rec = acceptance.suppressed_record(
        reasons=["p34_46_l2: not landed"], generated_at="2026-10-09T12:00:00Z"
    )
    assert rec["version"] == "sig.probe-run/1"
    assert rec["overall"] == "suppressed"
    assert rec["checks"] == {}
    assert "259_P34.47" in rec["rerun_prompt"]


# --- the CLI ----------------------------------------------------------------------


def test_cli_check_exit42(tmp_path):
    inputs = tmp_path / "in.json"
    inputs.write_text(json.dumps(_gate_inputs(now="2026-10-09T12:00:00Z")), encoding="utf-8")
    out = tmp_path / "rec.json"
    rc = acceptance.main(["--check", "--inputs", str(inputs), "--record-out", str(out)])
    assert rc == 42
    assert json.loads(out.read_text())["overall"] == "suppressed"


def test_cli_check_run(tmp_path):
    inputs = tmp_path / "in.json"
    inputs.write_text(json.dumps(_gate_inputs(now="2026-10-15T12:00:00Z")), encoding="utf-8")
    assert acceptance.main(["--check", "--inputs", str(inputs)]) == 0


def test_cli_bad_inputs_exit2(tmp_path):
    inputs = tmp_path / "bad.json"
    inputs.write_text("not json", encoding="utf-8")
    assert acceptance.main(["--check", "--inputs", str(inputs)]) == 2


def test_cli_subprocess_gate(tmp_path):
    inputs = tmp_path / "in.json"
    inputs.write_text(json.dumps(_gate_inputs(now="2026-10-09T12:00:00Z")), encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "ops",
            "acceptance-sweep",
            "--check",
            "--inputs",
            str(inputs),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert r.returncode == 42
