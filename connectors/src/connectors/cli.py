# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `connectors` stage (SIG-ENG-013).

`connectors validate` runs the registry self-checks that must hold at every
phase gate: the source registry, local-group registry, and partner roster all
load and satisfy their invariants (SIG-INGEST-023..040). Later tickets extend
this with the actual connector sub-commands (§47); no fetching logic lives here.
"""

from __future__ import annotations

import argparse

from . import __version__
from .ecosystem import GroupStatus, local_groups, partners
from .registry import sources


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `connectors` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-connectors",
        description="SIG connectors stage: the seeded source registry and ingestion gate (§22).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate", help="run the source-registry data-layer self-checks")
    return parser


def _validate() -> int:
    srcs = sources()
    groups = local_groups()
    orgs = partners()
    undetermined = [s for s in srcs if s.rights.spdx.strip().upper() == "UNDETERMINED"]
    permitted = [s for s in srcs if s.ingestion_permitted]
    disappeared = [g for g in groups.values() if g.status is GroupStatus.DISAPPEARED]
    unlocated = [g for g in groups.values() if g.status is GroupStatus.UNLOCATED]
    print(f"registered sources: {len(srcs)}")
    print(f"  rights UNDETERMINED (export gate fails closed): {len(undetermined)}")
    print(f"  ingestion_permitted=true: {len(permitted)}")
    print(
        f"local groups: {len(groups)} (unlocated {len(unlocated)}, disappeared {len(disappeared)})"
    )
    print(f"national partners: {len(orgs)}")
    print("connectors registry self-checks OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `connectors` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        return _validate()
    parser.print_help()
    return 0
