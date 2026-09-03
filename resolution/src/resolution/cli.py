# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `resolution` stage (SIG-ENG-013).

Sub-commands expose the identity substrate (§11.1-11.3, §14):

* ``geoid CODE LEVEL``  — validate a Census GEOID against its level (SIG-IDENT-005).
* ``agency-name NAME``  — parse a colon-delimited agency name into parent + unit (SIG-IDENT-011).
* ``relation-types``    — list the seven OrganizationRelation types (SIG-IDENT-016).

With no sub-command it prints help and exits 0 (the SIG-ENG-013 convention).
"""

from __future__ import annotations

import argparse

from . import __version__
from .geoid import GeoidValidationError, validate_geoid
from .identity import parse_agency_name
from .temporal_identity import OrganizationRelationType


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `resolution` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-resolution",
        description="SIG resolution stage: the identity registries (§11.1-11.3, §14).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    geoid = sub.add_parser("geoid", help="validate a Census GEOID against its level")
    geoid.add_argument("code")
    geoid.add_argument("level")

    agency = sub.add_parser("agency-name", help="parse a colon-delimited agency name")
    agency.add_argument("name")

    sub.add_parser("relation-types", help="list the seven OrganizationRelation types")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the `resolution` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "geoid":
        try:
            print(validate_geoid(args.code, args.level))
        except GeoidValidationError as exc:
            print(str(exc))
            return 2
        return 0
    if args.command == "agency-name":
        parsed = parse_agency_name(args.name)
        print(f"parent: {parsed.parent or '(none)'}")
        print(f"unit:   {parsed.unit}")
        return 0
    if args.command == "relation-types":
        for value in OrganizationRelationType:
            print(value.value)
        return 0

    parser.print_help()
    return 0
