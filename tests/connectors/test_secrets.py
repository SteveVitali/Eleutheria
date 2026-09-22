# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""No credential ever lives in a file — env-only design (RISK-P21-05, HG-09).

Tokens/keys are read from the environment (``SIG_MUCKROCK_TOKEN``,
``SIG_DATA_GOV_KEY``, ``SIG_OVERPASS_ENDPOINT``, ``SIG_CIVICCLERK_BASE``); a
hardcoded token literal in a ``.py`` / ``.toml`` file, or an un-ignored ``.env``,
is a leak. This test is the guard the ticket requires (RISK-P21-05).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    ".astro",
}

# A hardcoded credential is an env name assigned a *string literal*, or an
# `api_key`/`token` assigned a literal — not a read from `os.environ`.
_TOKEN_LITERAL = re.compile(r"""SIG_[A-Z0-9_]*(?:TOKEN|KEY)\s*=\s*["'][^"']""")
_API_KEY_LITERAL = re.compile(r"""\bapi_key\s*=\s*["'][^"']""")


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in {".py", ".toml"} and path.is_file():
            files.append(path)
    return files


def test_no_hardcoded_token_literal_in_py_or_toml() -> None:
    offenders: list[str] = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "os.environ" in line or "getenv" in line:
                continue  # an env read is the sanctioned pattern
            if _TOKEN_LITERAL.search(line) or _API_KEY_LITERAL.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, "hardcoded credential literal(s) found:\n" + "\n".join(offenders)


def test_env_files_are_gitignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    patterns = set(gitignore.splitlines())
    # `.env*` coverage: the AC requires `.env*` be ignored; we ignore .env and
    # .env.* (and *.env), which together cover every .env* variant.
    assert ".env" in patterns
    assert any(p in patterns for p in (".env.*", ".env*", "*.env"))
