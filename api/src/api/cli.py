# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `api` stage (SIG-ENG-013).

``sig-api serve`` runs the public read API (§37) under uvicorn against the demo
in-memory store, so the whole surface can be driven locally. The bare ``sig-api``
prints help, keeping the skeleton convention every stage shares.
"""

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `api` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-api",
        description="SIG public read API (§37).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="Run the read API under uvicorn (demo store).")
    serve.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    serve.add_argument("--port", type=int, default=8000, help="Bind port (default 8000).")
    return parser


def _serve(host: str, port: int) -> int:
    import uvicorn

    from .app import create_app
    from .demo import build_demo_store

    uvicorn.run(create_app(build_demo_store()), host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `api` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.host, args.port)
    parser.print_help()
    return 0
