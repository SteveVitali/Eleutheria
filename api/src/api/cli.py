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
import os

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
    serve.add_argument(
        "--release-registry",
        default=None,
        help="Path to the activated release registry (staged/ + withdrawals.json) — "
        "enables /v1/releases/<pub>/compartments/<comp>/search over the verified "
        "per-compartment FTS5 indexes (P32.14, SIG-FIND-003).",
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
    curate.add_argument(
        "--dsn",
        default=None,
        help="Back the review queue with PostgreSQL (P31.10: review_item / "
        "append-only review_decision) instead of the demo seed queue.",
    )
    curate.add_argument(
        "--role",
        default=None,
        help="Optional PostgreSQL role to SET ROLE to on the queue connection "
        "(e.g. sig_materialize, the least-privilege write role).",
    )
    curate.add_argument(
        "--intake-dsn",
        default=None,
        help="Also mount the private intake-moderation surface (P32.16): the "
        "/v1/curation/intake/* queue + event routes over the `intake` schema "
        "(SET ROLE sig_intake_reviewer on its own connection).",
    )

    # The PUBLIC anonymous correction receiver (P32.16, ADR-135, SIG-FIND-006) —
    # a THIRD separate process, neither the read API nor curation. It serves the
    # no-JS /intake/new form + POST /intake/v1/reports + POST /intake/v1/status.
    # SIG_INTAKE_ENABLED=1 mounts the surface; ACCEPTING reports additionally
    # requires [intake].operational=true in ops/config.toml AND
    # SIG_INTAKE_OPERATIONAL=1 AND the two env secrets — an unstaffed receiver
    # answers receiver_not_operating and is never advertised as live.
    intake = sub.add_parser(
        "serve-intake",
        help="Run the anonymous correction receiver (needs SIG_INTAKE_ENABLED=1).",
    )
    intake.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    intake.add_argument("--port", type=int, default=8002, help="Bind port (default 8002).")
    intake.add_argument(
        "--dsn",
        required=True,
        help="PostgreSQL DSN for the durable intake store (required — the "
        "receiver's purpose is durable receipts; SET ROLE sig_intake_receiver).",
    )
    intake.add_argument(
        "--ops-config",
        default=None,
        help="Path to ops/config.toml for the [intake].operational gate "
        "(default: the repo's ops/config.toml).",
    )

    # The retention sweep (P32.16): expunges payloads past the ratified schedule
    # and lists review-ceiling breaches — an operator verb, run on a schedule.
    purge = sub.add_parser(
        "intake-purge",
        help="Run the intake retention sweep (expunge due payloads; list overdue reviews).",
    )
    purge.add_argument(
        "--dsn",
        required=True,
        help="PostgreSQL DSN (SET ROLE sig_intake_reviewer).",
    )
    purge.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be expunged/flagged without writing.",
    )
    return parser


def _serve(
    host: str,
    port: int,
    dsn: str | None = None,
    role: str | None = None,
    release_registry: str | None = None,
) -> int:
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
    # P25.10: pre-compute the watermark-keyed annotation set in the background so
    # even the first /v1/contradiction request is warm (a no-op for stores whose
    # surfaces are already materialised).
    store.warmup()
    # P35.57 (SIG-REL-010): the registry can also come from the deployment env
    # (Cloud Run sets env, not argv — SIG_RELEASE_REGISTRY carries the mount
    # path, ops/gcp config.sh's SIG_RELEASE_REGISTRY_DIR value).
    release_registry = release_registry or os.environ.get("SIG_RELEASE_REGISTRY") or None
    release_search = None
    release_serving = None
    if release_registry:
        from .release_search import ReleaseSearchStore
        from .release_serving import ReleaseServingStore

        release_search = ReleaseSearchStore(release_registry)
        release_serving = ReleaseServingStore(release_registry)
    # P34.25 (A-20=a): the promoted release this service is pinned to, where one
    # exists — the live-spine basis label discloses it on every response; unset
    # answers "not pinned".
    release_id = os.environ.get("SIG_RELEASE_ID") or None
    uvicorn.run(
        create_app(
            store,
            release_search,
            release_id=release_id,
            release_serving=release_serving,
        ),
        host=host,
        port=port,
    )
    return 0


def _serve_curation(
    host: str,
    port: int,
    dsn: str | None = None,
    role: str | None = None,
    intake_dsn: str | None = None,
) -> int:
    import uvicorn

    from .curation import create_curation_app, curation_enabled

    if not curation_enabled():
        print(
            "refusing to serve: SIG_CURATION_ENABLED is not 1 — the curation surface is "
            "disabled by default (RISK-P21-10). Set SIG_CURATION_ENABLED=1 to enable it "
            "on this non-public process only."
        )
        return 3
    queue = None
    if dsn:
        from resolution.camera_sites_pg import set_role
        from resolution.review_pg import PgReviewQueue

        queue = PgReviewQueue.from_dsn(dsn)
        if role:
            set_role(queue.conn, role)
    uvicorn.run(
        create_curation_app(review_queue=queue, intake_store=intake_dsn),
        host=host,
        port=port,
    )
    return 0


def _serve_intake(host: str, port: int, dsn: str, ops_config: str | None = None) -> int:
    import uvicorn

    from .intake import (
        INTAKE_ABUSE_SECRET_ENV,
        INTAKE_FORM_SECRET_ENV,
        create_intake_app,
        intake_enabled,
        intake_operational,
        receiver_store_from_dsn,
    )

    if not intake_enabled():
        print(
            "refusing to serve: SIG_INTAKE_ENABLED is not 1 — the correction receiver "
            "is disabled by default (P32.16). Set SIG_INTAKE_ENABLED=1 to mount it."
        )
        return 3
    operational = intake_operational(config_path=ops_config)
    if operational:
        import os

        missing = [
            name
            for name in (INTAKE_FORM_SECRET_ENV, INTAKE_ABUSE_SECRET_ENV)
            if not os.environ.get(name)
        ]
        if missing:
            print(
                "refusing to serve an operational receiver without its secrets: "
                + ", ".join(missing)
                + " (HG-09 — env only, never committed)"
            )
            return 3
        print(
            "intake receiver OPERATIONAL — [intake].operational=true and "
            "SIG_INTAKE_OPERATIONAL=1 (D-R10-PUBLISH-1 operating approval)"
        )
    else:
        print(
            "intake receiver running NON-OPERATIONAL (staging): /intake/* present, "
            "new reports refused with receiver_not_operating. To operate: commit "
            "[intake].operational=true and export SIG_INTAKE_OPERATIONAL=1 plus the "
            "two secrets (see docs/governance/intake-receiver-operating-packet.md)."
        )
    uvicorn.run(
        create_intake_app(
            store=receiver_store_from_dsn(dsn),
            enabled=True,
            operational=operational,
        ),
        host=host,
        port=port,
    )
    return 0


def _intake_purge(dsn: str, dry_run: bool = False) -> int:
    from datetime import UTC, datetime

    from db.intake import PgIntakeReviewerStore

    from policy import intake as pint

    store = PgIntakeReviewerStore.from_dsn(dsn)
    try:
        retention = pint.contract()["retention"]
        report = store.expunge_due(
            after_disposition_days=int(retention["payload_days_after_disposition"]),
            ceiling_days=int(retention["payload_ceiling_days"]),
            now=datetime.now(UTC),
            dry_run=dry_run,
        )
    finally:
        store.close()
    import json

    print(
        json.dumps(
            {
                "action": "dry_run" if dry_run else "expunge",
                "expunged": report["expunged"],
                "expunged_count": len(report["expunged"]),
                "review_overdue": report["review_overdue"],
                "review_overdue_count": len(report["review_overdue"]),
                "legal_hold_skipped": report["legal_hold_skipped"],
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `api` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.host, args.port, args.dsn, args.role, args.release_registry)
    if args.command == "serve-curation":
        return _serve_curation(args.host, args.port, args.dsn, args.role, args.intake_dsn)
    if args.command == "serve-intake":
        return _serve_intake(args.host, args.port, args.dsn, args.ops_config)
    if args.command == "intake-purge":
        return _intake_purge(args.dsn, args.dry_run)
    parser.print_help()
    return 0
