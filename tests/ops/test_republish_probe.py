# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21b — `sig-ops republish-probe` / `sig.probe-run/1` offline contract.

The L2 pre-flight record pinned on fixtures: the absence leg probes the
cadence ``http-absent`` targets with an injectable check; the handle crawl is
counts-only (a matched handle never appears in the record); a downloaded
bucket listing is counted + handle-scanned; the tile sample needs a ranged
200/206; the attribution sample fails when an ``attribution_required`` row
lacks a holder or a ``terms_url``; skipped legs make the record ``partial`` —
never a fabricated pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from ops.republish_probe import (
    PROBE_RUN_VERSION,
    absence_check,
    attribution_sample_check,
    handle_crawl_check,
    read_release_record,
    run_republish_probe,
    tile_sample_check,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_CADENCE = """\
[[probes.targets]]
name = "denied-visual-language"
kind = "http-absent"
url = "https://example.test"
path = "/visual-language/"

[[probes.targets]]
name = "denied-entity"
kind = "http-absent"
url_env = "SIG_TEST_ABSENT_URL"
path = "/entity/x/"

[[probes.targets]]
name = "api-health"
kind = "http"
url_env = "SIG_TEST_API_URL"
path = "/health"
"""


@pytest.fixture()
def cadence(tmp_path: Path) -> Path:
    p = tmp_path / "cadence.toml"
    p.write_text(_CADENCE)
    return p


def _crawl_runner(report: dict):
    """A fake handle_crawl_check invocation returning its JSON report."""

    def run(cmd, capture_output, text, check):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(
            cmd,
            0 if report.get("verdict") == "pass" else 1,
            stdout=json.dumps(report),
            stderr="",
        )

    return run


# --- absence ---------------------------------------------------------------------


def test_absence_probes_denied_routes_and_reports_unresolved(cadence: Path) -> None:
    seen: list[str] = []

    def check(url: str) -> tuple[bool, str]:
        seen.append(url)
        return True, "404"

    result = absence_check(
        cadence, env={"SIG_TEST_ABSENT_URL": "https://example.test"}, check_absent=check
    )
    assert result.verdict == "pass"
    assert result.detail["count"] == 2
    assert result.detail["failed"] == 0
    assert seen == [
        "https://example.test/visual-language/",
        "https://example.test/entity/x/",
    ]


def test_absence_fails_when_a_denied_route_is_present(cadence: Path) -> None:
    result = absence_check(
        cadence,
        env={"SIG_TEST_ABSENT_URL": "https://example.test"},
        check_absent=lambda url: ("/entity/" in url, "200"),
    )
    assert result.verdict == "fail"
    assert result.detail["failed"] == 1
    statuses = {p["name"]: p["detail"] for p in result.detail["probes"]}
    assert statuses["denied-entity"] == "200"


def test_absence_skipped_when_no_targets_resolve(tmp_path: Path) -> None:
    p = tmp_path / "cadence.toml"
    p.write_text(
        '[[probes.targets]]\nname = "d"\nkind = "http-absent"\n'
        'url_env = "SIG_TEST_NEVER_SET"\npath = "/x/"\n'
    )
    result = absence_check(p, env={})
    assert result.verdict == "skipped"
    assert "d" in result.detail["unresolved"]


# --- handle crawl ------------------------------------------------------------------


def test_handle_crawl_counts_only_and_scans_the_listing(tmp_path: Path) -> None:
    handles = tmp_path / "handles.txt"
    handles.write_text("handle-alice\nhandle-bob\n")
    listing = tmp_path / "listing.txt"
    listing.write_text(
        "gs://bucket/manifest.json\ngs://bucket/handle-alice-sites.csv\ngs://bucket/ok.csv\n"
    )
    report = {
        "verdict": "pass",
        "handles_checked": 2,
        "hits": {"functional": 0, "retained": 3, "other": 0},
        "files_with_hits": {"functional": 0, "retained": 2, "other": 0},
    }
    result = handle_crawl_check(
        handle_list=handles,
        bucket_listing=listing,
        runner=_crawl_runner(report),
    )
    assert result.verdict == "fail"  # the listing carried a live handle
    assert result.detail["sig_public_listing"]["objects"] == 3
    assert result.detail["sig_public_listing"]["handle_hits"] == 1
    # counts only — the matched string never appears in the record
    assert "handle-alice" not in json.dumps(result.as_json())


def test_handle_crawl_clean_listing_and_repo_pass(tmp_path: Path) -> None:
    handles = tmp_path / "handles.txt"
    handles.write_text("handle-alice\n")
    listing = tmp_path / "listing.txt"
    listing.write_text("gs://bucket/manifest.json\n")
    report = {
        "verdict": "pass",
        "handles_checked": 1,
        "hits": {"functional": 0, "retained": 0, "other": 0},
        "files_with_hits": {"functional": 0, "retained": 0, "other": 0},
    }
    result = handle_crawl_check(
        handle_list=handles,
        bucket_listing=listing,
        runner=_crawl_runner(report),
    )
    assert result.verdict == "pass"


def test_handle_crawl_skips_honestly_without_the_list(tmp_path: Path) -> None:
    result = handle_crawl_check(handle_list=tmp_path / "absent.txt")
    assert result.verdict == "skipped"


# --- tile sample -------------------------------------------------------------------


def test_tile_sample_needs_a_ranged_2xx() -> None:
    result = tile_sample_check(
        ["https://example.test/tiles.pmtiles", "https://example.test/m.pmtiles"],
        probe=lambda url: 206 if url.endswith("tiles.pmtiles") else 404,
    )
    assert result.verdict == "fail"
    assert result.detail["failed"] == 1
    ok = tile_sample_check(["https://example.test/t.pmtiles"], probe=lambda url: 206)
    assert ok.verdict == "pass"


def test_tile_sample_skipped_without_urls() -> None:
    assert tile_sample_check([]).verdict == "skipped"


# --- attribution sample ------------------------------------------------------------


def _row(rights: dict) -> str:
    return json.dumps({"site_id": "s1", "_rights": rights})


def test_attribution_sample_requires_holder_and_terms_url(tmp_path: Path) -> None:
    pub = tmp_path / "public" / "comp"
    pub.mkdir(parents=True)
    (pub / "claims.jsonl").write_text(
        _row(
            {
                "attribution_required": True,
                "attribution": "Peel Regional Police",
                "terms_url": "https://example.test/terms",
            }
        )
        + "\n"
        + _row({"attribution_required": True, "attribution": "", "terms_url": ""})
        + "\n"
        + _row({"attribution_required": False})
        + "\n"
    )
    result = attribution_sample_check(tmp_path / "public")
    assert result.verdict == "fail"
    assert result.detail["rows_checked"] == 2
    assert result.detail["missing_attribution"] == 1
    assert result.detail["missing_terms_url"] == 1


def test_attribution_sample_passes_on_complete_rows(tmp_path: Path) -> None:
    pub = tmp_path / "public"
    pub.mkdir()
    (pub / "sites.jsonl").write_text(
        _row(
            {
                "attribution_required": True,
                "attribution": "Town of X",
                "terms_url": "https://example.test/t",
            }
        )
        + "\n"
    )
    assert attribution_sample_check(pub).verdict == "pass"


def test_attribution_sample_skipped_without_dir() -> None:
    assert attribution_sample_check(None).verdict == "skipped"


# --- the record --------------------------------------------------------------------


def test_probe_run_record_shape_and_partial_verdict(tmp_path: Path, cadence: Path) -> None:
    record = run_republish_probe(
        cadence_path=cadence,
        env={},
        handle_list=tmp_path / "absent.txt",
        now="2026-10-05T12:00:00Z",
        check_absent=lambda url: (True, "404"),
        release={"release_id": "web-2026-10-05"},
    )
    assert record["version"] == PROBE_RUN_VERSION == "sig.probe-run/1"
    assert record["generated_at"] == "2026-10-05T12:00:00Z"
    assert record["release"]["release_id"] == "web-2026-10-05"
    # absence pass + handle skipped + tiles skipped + attribution skipped
    assert record["overall"] == "partial"
    assert record["checks"]["absence"]["verdict"] == "pass"
    assert record["checks"]["handle_crawl"]["verdict"] == "skipped"
    json.dumps(record)  # serialisable


def test_probe_run_overall_fail_on_failed_leg(tmp_path: Path, cadence: Path) -> None:
    record = run_republish_probe(
        cadence_path=cadence,
        env={"SIG_TEST_ABSENT_URL": "https://example.test"},
        handle_list=tmp_path / "absent.txt",
        check_absent=lambda url: (False, "200"),
    )
    assert record["overall"] == "fail"


def test_read_release_record(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / ".sig-release.json").write_text(
        json.dumps({"release_id": "web-1", "data_release": "exp-9", "extra": 1})
    )
    rel = read_release_record(dist)
    assert rel == {"release_id": "web-1", "data_release": "exp-9"}
    assert read_release_record(tmp_path / "none") == {}


# --- the CLI verb -------------------------------------------------------------------


def test_cli_republish_probe_writes_the_record(tmp_path: Path) -> None:
    cadence = tmp_path / "cadence.toml"
    # env-only targets: unresolvable offline → the absence leg skips honestly
    # instead of hitting the network.
    cadence.write_text(
        '[[probes.targets]]\nname = "d"\nkind = "http-absent"\n'
        'url_env = "SIG_TEST_NEVER_SET"\npath = "/denied/"\n'
    )
    out = tmp_path / "probe.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ops",
            "republish-probe",
            "--cadence",
            str(cadence),
            "--handle-list",
            str(tmp_path / "absent-handles.txt"),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPO_ROOT / "ops" / "src")},
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(out.read_text())
    assert record["version"] == "sig.probe-run/1"
    assert record["overall"] == "partial"  # absence skipped (unresolved envs)
    assert "generated_at" in record
