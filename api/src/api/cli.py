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
    serve = sub.add_parser("serve", help="Run the read API under uvicorn.")
    serve.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    serve.add_argument("--port", type=int, default=8000, help="Bind port (default 8000).")
    serve.add_argument(
        "--dsn",
        default=None,
        help="Serve over the PostgreSQL claim spine (PgReadStore) instead of the demo store.",
    )
    serve.add_argument(
        "--role",
        default=None,
        help="Optional PostgreSQL read role to SET ROLE to (e.g. sig_read_public); RLS stays on.",
    )

    # The AUTHENTICATED curation surface (§34, ADR-068). A SEPARATE process from
    # `serve`, bound to a non-public interface, mounted only when SIG_CURATION_ENABLED=1
    # (RISK-P21-10). It is never the public read API (Part VIII §0.7).
    curate = sub.add_parser(
        "serve-curation",
        help="Run the authenticated curation service (needs SIG_CURATION_ENABLED=1).",
    )
    curate.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    curate.add_argument("--port", type=int, default=8001, help="Bind port (default 8001).")
    return parser


def _serve(host: str, port: int, dsn: str | None = None, role: str | None = None) -> int:
    import uvicorn

    from .app import create_app
    from .store import ReadStore

    store: ReadStore
    if dsn:
        from .store_pg import build_pg_store

        store = build_pg_store(dsn, role=role)
    else:
        from .demo import build_demo_store

        store = build_demo_store()
    uvicorn.run(create_app(store), host=host, port=port)
    return 0


def _serve_curation(host: str, port: int) -> int:
    import uvicorn

    from .curation import create_curation_app, curation_enabled

    if not curation_enabled():
        print(
            "refusing to serve: SIG_CURATION_ENABLED is not 1 — the curation surface is "
            "disabled by default (RISK-P21-10). Set SIG_CURATION_ENABLED=1 to enable it "
            "on this non-public process only."
        )
        return 3
    uvicorn.run(create_curation_app(), host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `api` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.host, args.port, args.dsn, args.role)
    if args.command == "serve-curation":
        return _serve_curation(args.host, args.port)
    parser.print_help()
    return 0
