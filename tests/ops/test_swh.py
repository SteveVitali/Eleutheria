# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Software Heritage save-code-now (SIG-GOV-022/023/024): request shape, untriggered."""

from __future__ import annotations

from pathlib import Path

import pytest

from ops import swh as S


def test_save_request_targets_the_public_swh_api() -> None:
    req = S.build_save_request("https://github.com/sig-project/sig")
    assert req.method == "POST"
    assert req.url.startswith("https://archive.softwareheritage.org/api/1/origin/save/git/url/")
    assert req.token is None  # no token needed for a public repo
    assert "Authorization" not in req.headers
    assert req.as_json()["authenticated"] is False


def test_token_is_optional_and_only_raises_rate_limits() -> None:
    req = S.build_save_request("https://example.com/repo.git", token="t")
    assert req.headers["Authorization"] == "Bearer t"


def test_empty_origin_url_is_rejected() -> None:
    with pytest.raises(ValueError):
        S.build_save_request("")


def test_submit_uses_injected_transport_no_live_call() -> None:
    import httpx

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"save_request_status": "accepted"})

    req = S.build_save_request("https://github.com/SteveVitali/Eleutheria")
    result = S.submit(req, transport=httpx.MockTransport(handler))
    assert result["status"] == 200
    assert result["body"]["save_request_status"] == "accepted"
    assert seen and "origin/save/git/url" in seen[0]


# --- P37.55 (Q-E2-23): the public-repo default + the scan-first gate ---------


def test_default_origin_url_reads_the_git_remote(tmp_path: Path) -> None:
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", "git@github.com:Org/Repo.git"],
        check=True,
    )
    # SSH form is normalised to the canonical HTTPS origin, `.git` stripped.
    assert S.default_origin_url(repo) == "https://github.com/Org/Repo"
    subprocess.run(
        ["git", "-C", str(repo), "remote", "set-url", "origin", "https://github.com/Org/Repo.git"],
        check=True,
    )
    assert S.default_origin_url(repo) == "https://github.com/Org/Repo"
    # No remote → None, never a fabricated URL.
    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    subprocess.run(["git", "-C", str(repo2), "init", "-q"], check=True)
    assert S.default_origin_url(repo2) is None


def _scan_doc(disposition: str) -> bytes:
    import json

    return json.dumps({"schema": S.HISTORY_SCAN_SCHEMA, "disposition": disposition}).encode()


def test_scan_report_clean_gate(tmp_path: Path) -> None:
    clean = tmp_path / "clean.json"
    clean.write_bytes(_scan_doc("clean"))
    assert S.scan_report_clean(clean) == (True, "clean")
    red = tmp_path / "red.json"
    red.write_bytes(_scan_doc("findings"))
    ok, reason = S.scan_report_clean(red)
    assert not ok and "findings" in reason
    ok, reason = S.scan_report_clean(tmp_path / "absent.json")
    assert not ok and "not found" in reason
    wrong = tmp_path / "wrong.json"
    wrong.write_bytes(b'{"schema": "other/1"}')
    ok, reason = S.scan_report_clean(wrong)
    assert not ok and "not a" in reason


def test_cli_now_requires_a_clean_scan_report(tmp_path: Path) -> None:
    """`--now` without a clean sig.history-scan/1 report is gate-pending —
    exit 4, nothing submitted (Q-E2-23 + OM-20)."""
    from ops import cli as C

    class Args:
        repo_url = "https://github.com/sig-project/sig"
        visit_type = "git"
        now = True
        scan_report = None

    assert C._cmd_swh_save(Args()) == 4  # no --scan-report at all
    Args.scan_report = str(tmp_path / "red.json")
    (tmp_path / "red.json").write_bytes(_scan_doc("findings"))
    assert C._cmd_swh_save(Args()) == 4  # a red report refuses
    # A clean report proceeds to submit — which we cannot let hit the network
    # in a test; the gate semantics are proven by the two refusals.
