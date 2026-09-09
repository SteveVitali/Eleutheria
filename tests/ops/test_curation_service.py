# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""`sig-ops` wires the authenticated curation service separately (P21.6, ADR-068).

The curation surface is a SECOND API process, bound to loopback and disabled by
default (RISK-P21-10, Part VIII §0.7): `sig-ops status` reports it on its own line,
`sig-api serve-curation` refuses without the flag, and the compose service binds
to 127.0.0.1 only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from api.cli import _serve_curation
from api.cli import build_parser as api_parser
from ops.cli import _cmd_status, default_curation_url

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_serve_curation_refuses_when_disabled(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("SIG_CURATION_ENABLED", raising=False)
    assert _serve_curation("127.0.0.1", 8001) == 3  # refuses, does not bind
    assert "disabled by default" in capsys.readouterr().out


def test_api_cli_has_serve_curation_subcommand() -> None:
    parser = api_parser()
    args = parser.parse_args(["serve-curation", "--port", "8001"])
    assert args.command == "serve-curation"
    assert args.host == "127.0.0.1"  # loopback default (non-public)


def test_curation_url_is_loopback_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIG_STAGING_CURATION_URL", raising=False)
    monkeypatch.delenv("SIG_CURATION_HOST", raising=False)
    assert default_curation_url().startswith("http://127.0.0.1:")


def test_status_reports_curation_on_its_own_line(capsys: pytest.CaptureFixture[str]) -> None:
    import argparse

    _cmd_status(argparse.Namespace())
    out = capsys.readouterr().out
    lines = out.splitlines()
    # A dedicated curation line, marked authenticated + non-public, distinct from API.
    curation_lines = [ln for ln in lines if ln.strip().startswith("curation")]
    assert len(curation_lines) == 1
    assert "authenticated, non-public" in curation_lines[0]
    assert any(ln.strip().startswith("API") for ln in lines)


def test_compose_defines_api_curation_bound_to_loopback() -> None:
    compose = (_REPO_ROOT / "ops" / "docker-compose.yml").read_text()
    assert "api-curation:" in compose
    assert "SIG_CURATION_ENABLED" in compose
    # The published port is bound to loopback, never 0.0.0.0.
    assert "127.0.0.1:${SIG_CURATION_PORT:-8001}:8001" in compose
