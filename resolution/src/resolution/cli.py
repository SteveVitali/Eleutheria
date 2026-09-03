# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `resolution` stage (SIG-ENG-013).

Sub-commands expose the identity substrate (§11.1-11.3, §14):

* ``geoid CODE LEVEL``  — validate a Census GEOID against its level (SIG-IDENT-005).
* ``agency-name NAME``  — parse a colon-delimited agency name into parent + unit (SIG-IDENT-011).
* ``relation-types``    — list the seven OrganizationRelation types (SIG-IDENT-016).
* ``normalize NAME``    — versioned organisation-name normalisation (SIG-IDENT-022).
* ``ori VALUE``         — validate an ORI9 and report the civil-ORI flag (SIG-IDENT-002/003).
* ``scheme CLASS``      — the canonical identifier scheme for a class (SIG-IDENT-001).
* ``slug SLUG``         — parse a vendor-portal slug into a name hypothesis (SIG-IDENT-015).

With no sub-command it prints help and exits 0 (the SIG-ENG-013 convention).
"""

from __future__ import annotations

import argparse

from . import __version__
from .crosswalk import canonical_scheme_for
from .geoid import GeoidValidationError, validate_geoid
from .identity import parse_agency_name
from .normalize import NORMALIZE_RULESET_VERSION, normalize_org_name
from .ori import OriValidationError, is_civil_ori, validate_ori
from .slug import parse_slug
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

    normalize = sub.add_parser("normalize", help="normalise an organisation name (versioned)")
    normalize.add_argument("name")

    ori = sub.add_parser("ori", help="validate an ORI9 and report the civil-ORI flag")
    ori.add_argument("value")

    scheme = sub.add_parser("scheme", help="the canonical identifier scheme for a class")
    scheme.add_argument("organization_class")

    slug = sub.add_parser("slug", help="parse a vendor-portal slug into a name hypothesis")
    slug.add_argument("slug")
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
    if args.command == "normalize":
        print(normalize_org_name(args.name))
        print(f"(ruleset v{NORMALIZE_RULESET_VERSION})")
        return 0
    if args.command == "ori":
        try:
            validate_ori(args.value)
        except OriValidationError as exc:
            print(str(exc))
            return 2
        print(f"valid: {args.value}")
        print(f"civil/applicant ORI: {is_civil_ori(args.value)}")
        return 0
    if args.command == "scheme":
        res = canonical_scheme_for(args.organization_class)
        if res.is_surrogate:
            print(f"{args.organization_class}: SIG surrogate (no external canonical scheme)")
        else:
            print(f"{args.organization_class}: {res.canonical_scheme}")
            if res.secondary_schemes:
                print(f"  secondary: {', '.join(res.secondary_schemes)}")
        return 0
    if args.command == "slug":
        hypothesis = parse_slug(args.slug)
        if hypothesis is None:
            print("(denied: vendor-internal test tenant or empty slug)")
            return 0
        print(f"name hypothesis: {hypothesis.name_hypothesis}")
        print(f"(grammar v{hypothesis.grammar_version}; hypothesis only, not an identity)")
        return 0

    parser.print_help()
    return 0
