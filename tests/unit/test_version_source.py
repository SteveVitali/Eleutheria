# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""One version source (SIG-REL-014, P34.23; G3 §9.3).

Every Python package's ``__version__`` is derived from its installed
distribution metadata — which ``uv sync`` builds from that package's
``pyproject.toml`` — and ``web/package.json`` carries the same version, so
there is exactly one place a version is declared (the pyproject/package.json
pair) and ``0.0.0`` can never be reported. These tests fail if a package
re-hardcodes a literal, if a pyproject diverges from its ``__version__``, or
if the web package drifts from the Python set.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import re
import tomllib

import pytest
from support import PY_PACKAGES, REPO_ROOT


def _dist_name(pkg: str) -> str:
    """The installed distribution name for workspace member ``pkg``."""
    return f"sig-{pkg}"


def _pyproject_version(pkg: str) -> str:
    with (REPO_ROOT / pkg / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return str(data["project"]["version"])


def _web_version() -> str:
    data = json.loads((REPO_ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    return str(data["version"])


@pytest.mark.parametrize("pkg", PY_PACKAGES)
def test_version_single_source(pkg: str) -> None:
    """pyproject version == installed metadata == __version__; never 0.0.0."""
    py_version = _pyproject_version(pkg)
    dist_version = importlib.metadata.version(_dist_name(pkg))
    module_version = importlib.import_module(pkg).__version__

    assert py_version == dist_version == module_version, (
        f"{pkg}: pyproject {py_version!r} / installed metadata {dist_version!r} / "
        f"__version__ {module_version!r} disagree — run `uv sync` and fix the drift"
    )
    assert module_version != "0.0.0", f"{pkg} reports 0.0.0 (SIG-REL-014)"


@pytest.mark.parametrize("pkg", PY_PACKAGES)
def test_version_derived_from_importlib_metadata(pkg: str) -> None:
    """The ``__init__.py`` derives ``__version__`` — no hard-coded literal.

    The pin is on the *mechanism* (one version source), not a current value:
    a hand-typed literal — even a correct one — fails here because it is a
    second source that can silently diverge again (the NEW-3 defect).
    """
    init = (REPO_ROOT / pkg / "src" / pkg / "__init__.py").read_text(encoding="utf-8")
    assert "importlib.metadata" in init and "version(" in init, (
        f"{pkg}/src/{pkg}/__init__.py must derive __version__ via "
        f"importlib.metadata.version (SIG-REL-014) — a literal is a second source"
    )
    assert 'version("sig-' in init or "version('sig-" in init, (
        f"{pkg}: __version__ must come from the sig-{pkg} distribution metadata"
    )


def test_web_version_matches_python_packages() -> None:
    """``web/package.json`` carries the same version as every Python package."""
    web_version = _web_version()
    assert web_version != "0.0.0", "web reports 0.0.0 (SIG-REL-014)"
    for pkg in PY_PACKAGES:
        assert _pyproject_version(pkg) == web_version, (
            f"web/package.json {web_version!r} diverges from {pkg}/pyproject.toml "
            f"{_pyproject_version(pkg)!r} — bump them together (scripts/bump_version.py)"
        )


def test_pyproject_names_match_sig_dist_convention() -> None:
    """Each workspace member's dist name is ``sig-<pkg>`` — the name the
    ``__init__.py`` looks its version up under."""
    for pkg in PY_PACKAGES:
        with (REPO_ROOT / pkg / "pyproject.toml").open("rb") as fh:
            data = tomllib.load(fh)
        assert data["project"]["name"] == _dist_name(pkg)


def test_no_version_literal_in_init_files() -> None:
    """No ``__init__.py`` carries a semver literal as its ``__version__``."""
    for pkg in PY_PACKAGES:
        init = (REPO_ROOT / pkg / "src" / pkg / "__init__.py").read_text(encoding="utf-8")
        line = next(ln for ln in init.splitlines() if ln.startswith("__version__"))
        rhs = line.split("=", 1)[1].strip()
        assert not re.match(r'^["\']', rhs), (
            f"{pkg}: __version__ is a literal {line!r} — a second version source"
        )
