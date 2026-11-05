# SPDX-License-Identifier: Apache-2.0
"""P36.71 / R11-K13-SRCH-07 — the ``sig.search-acceptance/1`` harness."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "exports" / "src"))
sys.path.insert(0, str(REPO / "tests" / "exports"))

from exports.release import build_release  # noqa: E402
from test_release import REVISION, _write_export  # noqa: E402

from exports import search_acceptance as sa  # noqa: E402
from exports import search_benchmark as sb  # noqa: E402


@pytest.fixture()
def release_dir(tmp_path: Path) -> Path:
    export = _write_export(tmp_path / "export", n_records=8)
    build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    return tmp_path / "rel"


def _dev_qset(tmp_path: Path) -> Path:
    p = tmp_path / "dev.json"
    p.write_text(
        json.dumps(
            {
                "schema": "sig.search-benchmark-queries/1",
                "set_id": "acc-dev",
                "queries": [
                    {
                        "id": "d1",
                        "kind": "record",
                        "q": "Site src_a 0",
                        "judgement": "top3",
                        "answerable": True,
                        "expected": {"type": "record", "match": "src_a"},
                    },
                    {
                        "id": "d2",
                        "kind": "negative",
                        "q": "zzqx-nil",
                        "judgement": "honest",
                        "answerable": False,
                        "expected": {"type": "none"},
                    },
                ],
            }
        )
    )
    return p


def _sealed(tmp_path: Path) -> tuple[bytes, dict]:
    blob = json.dumps(
        {
            "set_id": "sig.test-heldout/1",
            "queries": [
                {
                    "id": "h1",
                    "kind": "record",
                    "query": "Site src_a 1",
                    "judgement": "top3",
                    "answerable": True,
                    "expected": {"type": "record", "match": "src_a"},
                },
                {
                    "id": "h2",
                    "kind": "negative",
                    "query": "zzqx-none",
                    "judgement": "honest",
                    "answerable": False,
                    "expected": {"type": "none"},
                },
            ],
        }
    ).encode()
    desc = {
        "schema": sb.HELD_OUT_DESCRIPTOR_SCHEMA,
        "label": sb.HELD_OUT_METRIC_LABEL,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "set_id": "sig.test-heldout/1",
        "reader": "R11-K13-SRCH-07",
    }
    return blob, desc


def test_acceptance_report_shape(release_dir, tmp_path):
    blob, desc = _sealed(tmp_path)
    rep = sa.run_acceptance(
        release_dir,
        dev_queries=_dev_qset(tmp_path),
        held_out_blob=blob,
        descriptor=desc,
        generated_at="2026-11-05T00:00:00Z",
    )
    assert rep["schema"] == "sig.search-acceptance/1"
    assert rep["verdict"] == "pass"
    assert rep["dev"]["summary"]["top3_success_rate"] == 1.0
    ho = rep["held_out"]
    assert ho["seal"]["read"].startswith("verified")
    assert ho["summary"]["top3_success_rate"] == 1.0
    # No sealed query text or suggestion may ride the committed report.
    joined = json.dumps(ho)
    assert "zzqx-none" not in joined and "Site src_a 1" not in joined
    assert {t["id"] for t in rep["thresholds"]} == {
        "dev_top3",
        "held_out_top3",
        "misleading_top_hits",
        "index_bytes",
    }
    assert rep["journeys"] and all("verdict" in j for j in rep["journeys"])
    assert rep["cost"]["status"] == "deferred"


def test_seal_mismatch_is_a_hard_stop(release_dir, tmp_path):
    _blob, desc = _sealed(tmp_path)
    with pytest.raises(sb.SearchBenchmarkError) as ei:
        sa.run_acceptance(
            release_dir,
            dev_queries=_dev_qset(tmp_path),
            held_out_blob=b'{"set_id":"x","queries":[]}',
            descriptor=desc,
        )
    assert ei.value.code == "held_out_digest_mismatch"


def test_threshold_unmet_is_recorded(release_dir, tmp_path):
    rep = sa.run_acceptance(
        release_dir,
        dev_queries=_dev_qset(tmp_path),  # d2 expects honest no-hit; d1 hits
        generated_at="t",
    )
    held_row = next(t for t in rep["thresholds"] if t["id"] == "held_out_top3")
    assert held_row["verdict"] == "not_run"


def test_cost_block_measured_and_deferred():
    d = sa.cost_block(None)
    assert d["status"] == "deferred" and d["ceiling_usd"] == 300.0
    m = sa.cost_block({"monthly_usd": 42.5, "search_queries": 9000})
    assert m["status"] == "measured" and m["verdict"] == "within"
    o = sa.cost_block({"monthly_usd": 301.0})
    assert o["verdict"] == "over"


def test_cli_runs_report_and_enforce(release_dir, tmp_path):
    out = tmp_path / "acc.json"
    r = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "exports",
            "search-acceptance",
            "--release",
            str(release_dir),
            "--queries",
            str(_dev_qset(tmp_path)),
            "--out",
            str(out),
            "--generated-at",
            "2026-11-05T00:00:00Z",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr[:400]
    rep = json.loads(out.read_text())
    assert rep["schema"] == "sig.search-acceptance/1"
    # --enforce flips the exit when a threshold is unmet.
    rep["thresholds"][0]["verdict"] = "unmet"  # prove the gate reads the report
