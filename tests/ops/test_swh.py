# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Software Heritage save-code-now (SIG-GOV-022/023/024): request shape, untriggered."""

from __future__ import annotations

import pytest

from ops import swh as S


def test_save_request_targets_the_public_swh_api() -> None:
    req = S.build_save_request("https://github.com/SteveVitali/Eleutheria")
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
