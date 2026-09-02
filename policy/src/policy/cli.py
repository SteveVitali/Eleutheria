# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `policy` stage (SIG-ENG-013).

`policy validate` runs the data-layer self-checks that must hold at every phase
gate: the threat-model artifact validates (SIG-SEC-001) and the licence
compartment registry loads. Later tickets extend this with more sub-commands.
"""

from __future__ import annotations

import argparse

from . import __version__
from .crawler import conduct_rules
from .governance import intake_categories, permitted_outcomes
from .licensing import compartments
from .threat_model import ThreatModelError, load_threat_model, validate_threat_model


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `policy` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-policy",
        description="SIG policy stage: executable governing rules (§26/§42/§43/§44).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate", help="run the policy data-layer self-checks")
    return parser


def _validate() -> int:
    try:
        validate_threat_model()
    except ThreatModelError as exc:
        print(f"threat model INVALID: {exc}")
        return 1
    print(f"crawler conduct rules: {len(conduct_rules())}")
    print(f"licence compartments: {len(compartments())}")
    print(f"threat-model adversary rows: {len(load_threat_model())}")
    print(f"takedown intake categories: {len(intake_categories())}")
    print(f"takedown permitted outcomes: {len(permitted_outcomes())}")
    print("policy self-checks OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `policy` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        return _validate()
    parser.print_help()
    return 0
