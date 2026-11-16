# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Software Heritage "save code now" (SIG-GOV-022/023/024, §46.5, ADR-067).

Software Heritage is the source-code half of the succession plan: a free public archive
that will hold the SIG repository so the *code* survives even if the git forge and the
primary domain vanish. Its "save code now" endpoint takes a repo URL and needs **no
token for public repositories** (a token only raises rate limits), so this is a genuine
zero-cost path.

This module builds the request; sending it is opt-in (``--now``) and, since the
repository went public (E1 NEW-14), an **operator-only, in-ticket verbatim go**
(P37.55, OM-20 — an irreversible external archival deposit is never pre-authorised).
``--now`` also requires the Q-E2-23 ordering to be discharged: a ``--scan-report``
naming a ``sig.history-scan/1`` report whose ``disposition`` is ``clean`` — scan the
public history first, then submit (the retained P34.18 handles are the disclosed
class, A-0.4). No live SWH call is made without both.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

#: The public Software Heritage "save code now" API (no token needed for public repos).
SWH_SAVE_API = "https://archive.softwareheritage.org/api/1/origin/save"

#: The history-scan report schema ``--scan-report`` must name (Q-E2-23).
HISTORY_SCAN_SCHEMA = "sig.history-scan/1"


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


def default_origin_url(repo_root: str | Path = ".") -> str | None:
    """The repository's ``origin`` remote as an HTTPS URL, or ``None``.

    Since the repository is public (E1 NEW-14) the origin URL is the natural
    default for the save request — the operator's ``sig-ops swh-save --now``
    needs no flag. ``git@…`` SSH forms are normalised to ``https://…`` and a
    trailing ``.git`` is stripped (SWH accepts either, the canonical form is
    cleaner in the record).
    """
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    if not url:
        return None
    if url.startswith("git@"):
        host, _, path = url[4:].partition(":")
        url = f"https://{host}/{path}"
    if url.endswith(".git"):
        url = url[: -len(".git")]
    return url


def scan_report_clean(report_path: str | Path) -> tuple[bool, str]:
    """Whether ``report_path`` is a ``sig.history-scan/1`` report with
    ``disposition == "clean"`` — the Q-E2-23 ordering gate for ``--now``.

    Returns ``(ok, reason)``; every refusal names what failed (missing file,
    wrong schema, red disposition) so the gate is fail-closed, never silent.
    """
    path = Path(report_path)
    if not path.is_file():
        return False, f"history-scan report not found: {path}"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"history-scan report unreadable ({exc})"
    if doc.get("schema") != HISTORY_SCAN_SCHEMA:
        return False, f"not a {HISTORY_SCAN_SCHEMA} report (schema={doc.get('schema')!r})"
    if doc.get("disposition") != "clean":
        return False, (
            f"history-scan disposition is {doc.get('disposition')!r}, not 'clean' — "
            "remediate or disclose the findings before the archival submission "
            "(Q-E2-23: scan first, then submit)"
        )
    return True, "clean"


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


__all__ = [
    "HISTORY_SCAN_SCHEMA",
    "SWH_SAVE_API",
    "SwhSaveRequest",
    "build_save_request",
    "default_origin_url",
    "scan_report_clean",
    "submit",
]
