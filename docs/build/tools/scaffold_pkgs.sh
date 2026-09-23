set -euo pipefail
HDR='# SPDX-License-Identifier: LicenseRef-SIG-Undetermined
# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final
# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md §42).'

PKGS="ontology db connectors parsing resolution reconcile inference tasks api exports orchestration policy ops"

for p in $PKGS; do
  mkdir -p "$p/src/$p"

  # per-package pyproject
  cat > "$p/pyproject.toml" <<EOF
[project]
name = "sig-$p"
version = "0.0.0"
description = "SIG $p package (skeleton; see docs/2_canonical_design_spec.md §47)."
requires-python = ">=3.11"
dependencies = []

[project.scripts]
sig-$p = "$p.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/$p"]
EOF

  # __init__.py
  cat > "$p/src/$p/__init__.py" <<EOF
$HDR
"""SIG \`$p\` package (skeleton — no domain logic yet; see §47)."""

__version__ = "0.0.0"
EOF

  # cli.py
  cat > "$p/src/$p/cli.py" <<EOF
$HDR
"""Plain-CLI entry point for the \`$p\` stage (SIG-ENG-013).

Every pipeline stage MUST be invocable as a plain CLI. This is the skeleton
convention every later ticket extends with real sub-commands; it deliberately
contains no domain logic yet.
"""

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the \`$p\` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-$p",
        description="SIG $p stage (skeleton).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="sig-$p %(prog)s".replace("%(prog)s", __version__),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the \`$p\` CLI. Returns a process exit code."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
EOF

  # __main__.py
  cat > "$p/src/$p/__main__.py" <<EOF
$HDR
"""Enable \`python -m $p\` (SIG-ENG-013)."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
EOF
done
echo "scaffolded: $PKGS"
