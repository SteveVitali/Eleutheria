# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `evidence` stage (SIG-ENG-013).

Sub-commands operate on the write-once evidence store (§17):

* ``digest FILE``       — print the base32 multihash of a file (SIG-EVID-002).
* ``object-path ID``    — print the OCFL storage path for a source-stream id.
* ``env``               — print the deterministic ingestion environment (SIG-EVID-018).
* ``lock-config``       — print the governance-mode Object Lock config (SIG-EVID-006).

Live web capture (``sig-evidence[capture]``) drives a real browser and is invoked
by the connectors, not from this diagnostic CLI.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .digest import multihash
from .ingest_run import deterministic_environment
from .ocfl import object_path
from .storage import governance_object_lock_configuration


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `evidence` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-evidence",
        description="SIG evidence stage: the OCFL write-once evidence store (§17).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_digest = sub.add_parser("digest", help="print the base32 multihash of a file")
    p_digest.add_argument("file", type=Path)

    p_path = sub.add_parser("object-path", help="print the OCFL path for a source-stream id")
    p_path.add_argument("object_id")

    sub.add_parser("env", help="print the deterministic ingestion environment")
    sub.add_parser("lock-config", help="print the governance-mode Object Lock config")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the `evidence` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "digest":
        print(multihash(args.file.read_bytes()))
        return 0
    if args.command == "object-path":
        print(object_path(args.object_id))
        return 0
    if args.command == "env":
        print(json.dumps(deterministic_environment(), sort_keys=True))
        return 0
    if args.command == "lock-config":
        print(json.dumps(governance_object_lock_configuration(), sort_keys=True))
        return 0
    parser.print_help()
    return 0
