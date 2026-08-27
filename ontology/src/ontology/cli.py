# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `ontology` stage (SIG-ENG-013).

The ontology is code before it is data (§51.1): one LinkML source generates every
downstream form (§20.1, ADR-007). Sub-commands:

* ``generate`` — regenerate all committed artifacts (SQL DDL, JSON Schema,
  OWL/SHACL, Pydantic, docs, SKOS vocabularies, the predicate registry, and the
  external crosswalks) from the single source; ``--check`` verifies the committed
  artifacts equal a fresh generation without touching the tree (the SIG-ENG-016
  gate, wired into ``make verify-gen``).
"""

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `ontology` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-ontology",
        description="SIG ontology stage: the single ontology source and its generators (§20.1).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    gen = sub.add_parser("generate", help="regenerate all artifacts from the single source")
    gen.add_argument(
        "--check",
        action="store_true",
        help="verify committed artifacts match a fresh generation (SIG-ENG-016 gate)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the `ontology` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "generate":
        from .generate import generate

        rc = generate(check=args.check)
        if args.command == "generate" and not args.check and rc == 0:
            print("ontology artifacts regenerated")
        elif args.check and rc == 0:
            print("ontology artifacts up to date")
        return rc
    parser.print_help()
    return 0
