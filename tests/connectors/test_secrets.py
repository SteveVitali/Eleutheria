# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""No credential ever lives in a file — env-only design (RISK-P21-05, HG-09).

Tokens/keys are read from the environment (``SIG_MUCKROCK_TOKEN``,
``SIG_DATA_GOV_KEY``, ``SIG_OVERPASS_ENDPOINT``, ``SIG_CIVICCLERK_BASE``); a
hardcoded token literal in a ``.py`` / ``.toml`` file, or an un-ignored ``.env``,
is a leak. This test is the guard the ticket requires (RISK-P21-05).

The same rule covers non-public *identifiers* that name real infrastructure
(go-live spec D3): this repository is public, so the GCP project id is written
as ``$SIG_GCP_PROJECT`` and resolved from the environment. Export
``SIG_GCP_PROJECT`` to arm that check; without it there is nothing to search for
and the check skips.
"""

from __future__ import annotations

import os
import re
import subprocess
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

#: The cadence.toml ``secrets = { ENV = "sig-name", … }`` binding maps env vars
#: to Secret Manager resource NAMES — never values (HG-09; the same pattern the
#: muckrock ``SIG_MUCKROCK_REFRESH`` row already carries). A Secret Manager name
#: is ``sig-<lowercase-hyphenated>``; no credential value takes that shape.
_SECRET_NAME_BINDING = re.compile(r"""\bsecrets\s*=\s*\{([^}]*)\}""")
_SECRET_NAME_VALUE = re.compile(r"""^sig-[a-z0-9-]+$""")


def _is_secret_name_binding(line: str) -> bool:
    """True when ``line`` is a ``secrets = { ENV = "sig-name", … }`` binding —
    every assigned literal is a Secret Manager *name*, never a credential."""
    match = _SECRET_NAME_BINDING.search(line)
    if not match:
        return False
    values = re.findall(r'=\s*"([^"]+)"', match.group(1))
    return bool(values) and all(_SECRET_NAME_VALUE.fullmatch(v) for v in values)


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
            if _is_secret_name_binding(line):
                continue  # a Secret Manager *name* binding, never a value (HG-09)
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


#: The scoped include list for the project-id leak check (ADR-119, the design's
#: ADR-R9-LEAKSCOPE; D-P30.4-4; operator Q7 = (a), ratified 2026-09-24). The
#: check guards the surfaces where a committed literal id is *deployable* —
#: every §47 package source tree, the schema/sqitch and ontology vocab +
#: generated trees, the whole ``ops/`` runtime composition, the whole ``web/``
#: package, the test suite, the CI/dev scripts, and the repo's build/deploy/CI
#: config files. ``docs/`` — including the append-only build memory under
#: ``docs/build/``, ``docs/tickets/`` and ``docs/adr/`` — is deliberately out
#: of scope: the project id is *recorded* there (run ledgers, ADR-098,
#: DEFERRALS), those records must not be rewritten (P1–P3), and a GCP project
#: id is not a credential. Root-level prose docs (README/AGENTS/CHANGELOG/
#: CONTRIBUTING/CITATION/LICENSE) are likewise documentation, not code +
#: config. The env-only rule itself is unchanged: a literal id in any file
#: below is a leak — write ``$SIG_GCP_PROJECT`` instead.
_PROJECT_ID_SCOPE = (
    # every §47 package source tree (SIG-ENG-012)
    "api/src",
    "connectors/src",
    "db/src",
    "evidence/src",
    "exports/src",
    "inference/src",
    "ontology/src",
    "ops/src",
    "orchestration/src",
    "parsing/src",
    "policy/src",
    "reconcile/src",
    "resolution/src",
    "tasks/src",
    # deployable schema migrations and their config
    "db/deploy",
    "db/revert",
    "db/verify",
    "db/sqitch.plan",
    "db/sqitch.conf",
    # ontology vocabulary + the committed generated artifacts
    "ontology/vocab",
    "ontology/generated",
    # the whole runtime composition (gcp scripts, Dockerfiles, cadence/config)
    "ops",
    # the whole web package — source, tests, scripts, config, static assets
    # (TypeScript is confined to web/, SIG-ENG-010)
    "web",
    # the test suite and the CI/dev/doc scripts
    "tests",
    "scripts",
    # repo build/deploy/CI config
    ".github",
    "Makefile",
    "pyproject.toml",
    "*/pyproject.toml",
    "uv.lock",
    "pylock.toml",
    ".python-version",
    ".gitignore",
    ".devinignore",
    # env files are gitignored; listed so a committed one can never hide an id
    ".env",
    ".env.*",
)


def test_gcp_project_id_is_env_resolved_not_committed() -> None:
    """The real project id appears in no code+config file — only ``$SIG_GCP_PROJECT`` (D3).

    Scoped per ADR-119 / D-P30.4-4 (operator Q7 = (a)): the check greps only the
    deployable surfaces in ``_PROJECT_ID_SCOPE``. The append-only build memory
    (`docs/build/`, `docs/tickets/`, `docs/adr/`) is exempt — it records the id
    as historical fact and cannot be rewritten (P1–P3).
    """
    project_id = os.environ.get("SIG_GCP_PROJECT", "").strip()
    # P34.2 (deliverable 7, H2 §5 S-4): the check fails closed — an unset
    # SIG_GCP_PROJECT means the scan has no needle, which used to pass vacuously.
    # The operator arms it via the `vars.SIG_GCP_PROJECT` repository variable
    # (OP-07); a local run needs `export SIG_GCP_PROJECT=<the id>`.
    if not project_id:
        import pytest

        pytest.fail(
            "SIG_GCP_PROJECT is unset — the leak check cannot run without the id "
            "it searches for (OP-07; fail-closed since P34.2, never a skip)"
        )

    # Guard: the include list must resolve to real tracked files — a typo'd
    # pathspec would silently scope the check to nothing.
    scoped = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--", *_PROJECT_ID_SCOPE],
        capture_output=True,
        text=True,
        check=True,
    )
    scoped_files = [line for line in scoped.stdout.splitlines() if line]
    assert scoped_files, "leak-check scope resolved to zero tracked files"

    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "grep", "-Il", "-e", project_id, "--", *_PROJECT_ID_SCOPE],
        capture_output=True,
        text=True,
        check=False,
    )
    # git grep exits 1 with no output when there is no match — the clean case.
    offenders = [line for line in tracked.stdout.splitlines() if line]
    # SIG-ENG-042: the non-vacuous report — how many files were candidates and
    # how many were actually scanned — is printed for the CI log.
    print(
        f"leak-check: candidates={len(scoped_files)} "
        f"evaluated={len(scoped_files)} offenders={len(offenders)}"
    )
    assert not offenders, (
        "GCP project id committed literally in code+config; write `$SIG_GCP_PROJECT` instead:\n"
        + "\n".join(offenders)
    )


# --- P26.4 (SOURCES.4): keyed-source credential hygiene ------------------------
#
# The keyed live sources (sam_gov, openstates, fbi_cde) authenticate on the
# request HEADER (`api_key_header` in the vocab tomls), never the URL — a keyed
# query would be recorded as the capture's `source_uri`, in fetch-record
# `rate_limit_events`, and in the `ops/runs` rows (the spine + committed build
# memory would then hold the key verbatim). These checks are the two halves of
# the ticket's no-key-literal invariant:
#
#  1. deterministic — no tracked file carries a credential-bearing URL query
#     param (an `api_key=<value>` / `apikey=<value>` in `?`/`&` position) — the
#     shape a leaked key takes.
#  2. env-armed — the *value* of any currently-exported `SIG_*` secret
#     (…_TOKEN/…_KEY/…_SECRET/…_PASSWORD/…_REFRESH, or a webhook URL) appears in
#     no tracked file. Skips when no secrets are exported (CI); armed in an
#     operator run shell.

#: A credential in URL query position — an `api_key`/`apikey` parameter carrying
#: a value after `?` or `&` (any case) — the leak shape the header seam exists to
#: prevent. `api_key=None`-style kwargs (no `?`/`&` before the name), prose
#: mentions, and non-credential params like OSM taginfo's `?key=…` do not match.
#: api.data.gov's published `DEMO_KEY` is upstream's documented public
#: placeholder (auth data published upstream, not a secret) — the one allowed
#: value.
_CREDENTIAL_URL_PARAM = re.compile(r"""[?&]api_?key\s*=\s*([^&\s"'`]+)""", re.IGNORECASE)
_PUBLIC_PLACEHOLDER_KEYS = frozenset({"demo_key"})

#: `SIG_*` env names whose *values* are credentials (mirrors ops.alerts'
#: SECRET_ENV_RE) plus names that embed a credential without the suffix.
_SECRET_ENV_RE = re.compile(r"^SIG_[A-Z0-9_]*(?:_TOKEN|_KEY|_SECRET|_PASSWORD|_REFRESH)$")
_SECRET_ENV_EXTRAS = ("SIG_ALERT_WEBHOOK_URL", "SIG_STAGING_DSN")


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / line for line in out.stdout.splitlines() if line]


def test_no_credential_query_param_in_any_tracked_file() -> None:
    """No committed file (reports, run ledgers, code) carries a keyed URL."""
    offenders: list[str] = []
    for path in _tracked_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in _CREDENTIAL_URL_PARAM.finditer(line):
                if match.group(1).strip().lower() in _PUBLIC_PLACEHOLDER_KEYS:
                    continue  # api.data.gov's published DEMO_KEY is not a secret
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
                break
    assert not offenders, "credential-bearing URL param(s) committed:\n" + "\n".join(offenders)


def test_no_exported_secret_value_in_any_tracked_file() -> None:
    """The value of an exported SIG_* credential appears in no tracked file.

    Env-armed (HG-09): with no credentials exported there is nothing to search
    for and the check skips; in a shell holding the real keys it proves the
    operator's run left no key literal in the repo or committed reports.
    """
    secrets = {
        name: value
        for name, value in os.environ.items()
        if value and len(value) >= 8 and (_SECRET_ENV_RE.search(name) or name in _SECRET_ENV_EXTRAS)
    }
    if not secrets:
        import pytest

        pytest.skip("no SIG_* credential env vars exported; nothing to search for")
    tracked = _tracked_files()
    offenders: list[str] = []
    for name, value in secrets.items():
        needle = value.encode("utf-8")
        for path in tracked:
            try:
                if needle in path.read_bytes():
                    offenders.append(f"{name} value found in {path.relative_to(REPO_ROOT)}")
            except OSError:
                continue
    assert not offenders, "exported credential value(s) committed:\n" + "\n".join(offenders)
