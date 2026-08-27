# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `exports` stage (SIG-ENG-013).

Every pipeline stage MUST be invocable as a plain CLI. P02.3 adds the first real
sub-command, `provo`, which serialises a PROV-O lineage document (§21.6). With no
sub-command the CLI prints help and exits 0 (the SIG-ENG-013 skeleton contract).
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `exports` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-exports",
        description="SIG exports stage.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    provo = subparsers.add_parser(
        "provo",
        help="Serialise an ingest-run lineage batch as PROV-O (SIG-INGEST-016).",
    )
    provo.add_argument(
        "lineage_json",
        help="Path to a lineage JSON document (see exports.provo.Lineage fields).",
    )
    provo.add_argument(
        "--format",
        default="turtle",
        help="rdflib serialisation format (turtle, nt, json-ld). Default: turtle.",
    )
    return parser


def _run_provo(path: str, fmt: str) -> int:
    from .provo import export_lineage
    from .provo_io import lineage_from_json

    with open(path, encoding="utf-8") as fh:
        lineage = lineage_from_json(json.load(fh))
    sys.stdout.write(export_lineage(lineage, fmt=fmt))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `exports` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "provo":
        return _run_provo(args.lineage_json, args.format)
    parser.print_help()
    return 0
