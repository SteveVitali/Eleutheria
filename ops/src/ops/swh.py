# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Software Heritage "save code now" (SIG-GOV-022/023/024, §46.5, ADR-067).

Software Heritage is the source-code half of the succession plan: a free public archive
that will hold the SIG repository so the *code* survives even if the git forge and the
primary domain vanish. Its "save code now" endpoint takes a repo URL and needs **no
token for public repositories** (a token only raises rate limits), so this is a genuine
zero-cost path.

This module builds the request; sending it is opt-in (``--now``). This run is
**untriggered** (gate pending: no public repo URL to save yet) — the request shape is
built and tested, but no live SWH call is made.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The public Software Heritage "save code now" API (no token needed for public repos).
SWH_SAVE_API = "https://archive.softwareheritage.org/api/1/origin/save"


@dataclass(frozen=True)
class SwhSaveRequest:
    """A prepared Software Heritage save request (method, URL, headers, body)."""

    visit_type: str
    origin_url: str
    token: str | None = None

    @property
    def url(self) -> str:
        return f"{SWH_SAVE_API}/{self.visit_type}/url/{self.origin_url}/"

    @property
    def method(self) -> str:
        return "POST"

    @property
    def headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def as_json(self) -> dict[str, object]:
        return {
            "method": self.method,
            "url": self.url,
            "visit_type": self.visit_type,
            "origin_url": self.origin_url,
            "authenticated": self.token is not None,
        }


def build_save_request(
    origin_url: str, *, visit_type: str = "git", token: str | None = None
) -> SwhSaveRequest:
    """Build a Software Heritage save-code-now request for ``origin_url``."""
    if not origin_url:
        raise ValueError("a repository origin URL is required to save to Software Heritage")
    return SwhSaveRequest(visit_type=visit_type, origin_url=origin_url, token=token)


def submit(request: SwhSaveRequest, *, transport: object | None = None) -> dict[str, object]:
    """Submit a save request to Software Heritage (only when explicitly invoked).

    ``transport`` is an injectable ``httpx.BaseTransport`` so the request path is tested
    without a live call (HG-07). Production leaves it ``None`` → a real client.
    """
    import httpx

    client = httpx.Client(transport=transport, timeout=30.0)  # type: ignore[arg-type]
    try:
        resp = client.post(request.url, headers=request.headers)
        resp.raise_for_status()
        body = resp.json()
    finally:
        client.close()
    return {"status": resp.status_code, "body": body}


__all__ = ["SWH_SAVE_API", "SwhSaveRequest", "build_save_request", "submit"]
