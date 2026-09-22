# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""J-1 + Q-1…Q-13 executed against a RUNNING API (P21.4, SIG-CHART-009).

This is the ``--live-api`` acceptance path: when ``SIG_STAGING_API_URL`` names a
reachable read API (the composed stack `sig-ops up` brought up, seeded with the OKC
slice), the whole Q-1…Q-13 set + J-1 are run against it and the fixture-backed
subset must pass. Without the env var it skips cleanly, so ``make check`` is
unchanged; ``docs/build/tools/run_okc.sh`` sets it and exercises this path, writing
``docs/build/okc/acceptance_<date>.json``.

The standalone runner (`python -m acceptance.live_api --api-url … --out …`) is the
CLI form of the same code; this test is its in-suite gate.
"""

from __future__ import annotations

import os
import urllib.request

import pytest
from acceptance.live_api import run_acceptance

_API_URL = os.environ.get("SIG_STAGING_API_URL")


def _reachable(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "/", timeout=3) as resp:  # noqa: S310 - local staging
            return 200 <= resp.status < 500
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(
    not (_API_URL and _reachable(_API_URL)),
    reason="SIG_STAGING_API_URL not set/reachable; the live-api path is run by run_okc.sh",
)
def test_live_api_acceptance_fixture_subset_passes() -> None:
    report = run_acceptance(_API_URL or "")
    # J-1 executed end to end (12 hops; contested count hop confirmed on the API).
    assert report.j1["hop_count"] == 12, report.j1
    # Every query in the fixture-backed subset passes; blocked queries record their
    # HG-03-pending command but never fail the run (no green sources on this build).
    assert report.summary["fixture_subset_all_pass"], [
        q for q in report.queries if q["in_fixture_subset"] and q["status"] != "pass"
    ]
    assert report.summary["failed"] == 0, [q for q in report.queries if q["status"] == "fail"]
    # The 299-vs-190 contradiction (Q-6) is answered by the composed stack.
    q6 = next(q for q in report.queries if q["id"] == "Q-6")
    assert q6["status"] == "pass", q6
