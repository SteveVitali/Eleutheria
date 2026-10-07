# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.34b (ACT-16b, C4 NEW-26): build a REAL from-spine fixture export for the
CI export-mode web build — and never a hand-authored web fixture.

The producer runs the same pipeline the national export runs:

1. stand up PostgreSQL 18 + PostGIS in a throwaway container and deploy the
   real ``db/sqitch.plan`` (the ``tests/db/conftest.py`` harness the
   claim-spine suite uses, loaded from the file because ``tests/db`` is not an
   importable package — the ``tests/e2e/conftest.py`` pattern);
2. seed the small licence-safe fixture spine —
   ``tests/db/test_spine_export_over_seeded_spine.py:seed_export_spine`` is the
   single source of truth for the seed, so the bytes this produces are exactly
   the bytes the seeded-spine tests prove (ODbL subject + CC0 subject + an
   UNDETERMINED subject that must never ship);
3. run :func:`exports.spine_export.run_spine_export` over that spine — the
   same read-only repeatable-read snapshot the production path uses — and
   ``write_to`` the export directory ``SIG_EXPORT_DIR`` points at;
4. optionally (``--release``) run :func:`exports.release.build_release` +
   :func:`exports.release.validate_release` so the immutable release tree
   exists for the archive-record Lighthouse URL.

Nothing here reads ``web/src/lib/*-fixture*`` or
``web/scripts/build-fixture-export.ts`` — feeding serialized web fixtures to
``SIG_DATA_SOURCE=export`` is exactly the C4 NEW-26 substitution this row's
regression guard forbids.

This is a CI script, not a pytest module: a missing Docker daemon is a HARD
FAILURE (non-zero exit), never a skip — a green run must mean the leg ran.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_CONFTEST = REPO_ROOT / "tests" / "db" / "conftest.py"
SEED_MODULE = REPO_ROOT / "tests" / "db" / "test_spine_export_over_seeded_spine.py"


def _load_module(path: Path, name: str) -> Any:
    """Load a repo file as a module (``tests/db`` is not a package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def produce(
    conn: Any,
    out_dir: Path,
    *,
    as_of: str,
    release_dir: Path | None = None,
    renderer_revision: str | None = None,
) -> dict[str, Any]:
    """Seed the fixture spine on ``conn``, run the real export, write it.

    ``conn`` holds an open transaction (autocommit off): the seed writes and
    ``run_spine_export``'s reads share it, so the uncommitted seed is visible —
    the same test seam ``tests/db`` uses. The session is left rolled back; the
    spine is never committed or mutated durably.

    Returns a JSON-able provenance summary (artifact/digest names only — the
    bytes live in ``out_dir``).
    """
    from exports.release import build_release, validate_release
    from exports.spine_export import digest_web_artifacts, run_spine_export

    seed_mod = _load_module(SEED_MODULE, "_sig_seeded_spine_test")
    subject_ids: dict[str, str] = seed_mod.seed_export_spine(conn.cursor())

    export = run_spine_export(
        conn,
        as_of=as_of,
        note="P34.34b CI export-mode fixture (seeded spine; not web fixtures)",
        spine_label="ci seeded fixture spine",
    )
    export.write_to(out_dir)

    summary: dict[str, Any] = {
        "kind": "from-spine fixture export (run_spine_export over the seeded "
        "tests/db spine — never web fixtures)",
        "as_of": as_of,
        "subjects": subject_ids,
        **export.summary(),
        "web_sha256": digest_web_artifacts(export),
    }

    if release_dir is not None:
        if not renderer_revision:
            raise ValueError("--release requires --renderer-revision")
        build = build_release(out_dir, release_dir, renderer_revision=renderer_revision)
        report = validate_release(release_dir)
        if report.failures or report.state != "complete":
            raise RuntimeError(
                "the built release failed its own validation (incl. the "
                f"same-origin link crawl): {report.failures}"
            )
        summary["release"] = {
            "publication_id": build.publication_id,
            "records": build.report["records"],
            "compartments": sorted(m["compartment"] for m in build.report["compartments"]),
            "validation": {
                "state": report.state,
                "artifacts_checked": report.artifacts_checked,
                "failures": report.failures,
            },
        }
    return summary


def _head_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path, help="the export dir (SIG_EXPORT_DIR)")
    ap.add_argument(
        "--release",
        type=Path,
        default=None,
        help="also build + validate the immutable release tree into this dir",
    )
    ap.add_argument(
        "--renderer-revision",
        default=None,
        help="release descriptor's renderer revision (default: HEAD sha)",
    )
    ap.add_argument(
        "--as-of",
        default=datetime.now(UTC).date().isoformat(),
        help="export as_of date (default: today's UTC date)",
    )
    ap.add_argument("--json-summary", type=Path, default=None)
    args = ap.parse_args(argv)

    db = _load_module(DB_CONFTEST, "_sig_db_conftest")
    if not db._docker_reachable():
        print(
            "build_from_spine_fixture_export: Docker daemon is not reachable — "
            "the from-spine export CANNOT be produced; failing loud (a green "
            "run must mean the leg ran; this leg does not skip)",
            file=sys.stderr,
        )
        return 2

    import psycopg

    with db.pg_container() as (network, host, port):
        db.create_plan_database(host, port, db.PG_DB)
        db.run_sqitch(network, "deploy", "--verify", dbname=db.PG_DB)
        conn = psycopg.connect(
            host=host,
            port=port,
            user=db.PG_USER,
            password=db.PG_PASSWORD,
            dbname=db.PG_DB,
            autocommit=False,
        )
        try:
            summary = produce(
                conn,
                args.out,
                as_of=args.as_of,
                release_dir=args.release,
                renderer_revision=args.renderer_revision or _head_sha(),
            )
        finally:
            conn.rollback()
            conn.close()

    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.json_summary:
        args.json_summary.parent.mkdir(parents=True, exist_ok=True)
        args.json_summary.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
