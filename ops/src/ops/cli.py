# SPDX-License-Identifier: LicenseRef-SIG-Undetermined
# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final
# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md §42).
"""Plain-CLI entry point for the `ops` stage (SIG-ENG-013).

Every pipeline stage MUST be invocable as a plain CLI. This is the skeleton
convention every later ticket extends with real sub-commands; it deliberately
contains no domain logic yet.
"""

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `ops` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-ops",
        description="SIG ops stage (skeleton).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the `ops` CLI. Returns a process exit code."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
