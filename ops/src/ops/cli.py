# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `ops` stage (SIG-ENG-013, P21.4, ADR-066).

`sig-ops` is the SIG **runtime composition** command: it stands the whole system
up as a service on one small machine (SIG-STORE-003, the zero-cost posture), not a
test suite. The stateful piece — the PG18+PostGIS claim spine with the real sqitch
plan deployed on start — lives in ``ops/docker-compose.yml``; the read API
(uvicorn) and the static server for ``web/dist`` are launched here as host
processes (the HG-12 local-staging default: uvicorn + a static file server), so
they run the host toolchain at HEAD without baking a platform-specific image.

Sub-commands (P21.4 deliverable 1):

* ``up --jurisdiction okc`` — bring up PG (+ sqitch deploy), then start the API and
  the static server; wait until all three answer.
* ``status`` — report PG / API / static health (exit non-zero if any is down).
* ``down`` — stop the API + static host processes and tear down the compose
  project (``down -v``), leaving **no containers** and no stray processes.
* ``seed --jurisdiction okc`` — load the Oklahoma City slice claims into the spine
  (the 299-vs-190 ``claimed_device_count`` contradiction and its neighbours),
  append-only, via ``db.claim_sink.PgClaimSink``.

Staging endpoints default to local and are overridable by env (HG-12):
``SIG_STAGING_DSN``, ``SIG_STAGING_API_URL``, ``SIG_STAGING_STATIC_URL``.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__

#: Repo root: ops/src/ops/cli.py -> parents[3].
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMPOSE_FILE = Path(__file__).resolve().parents[2] / "docker-compose.yml"
#: Gitignored runtime state (pids, ports) so a worktree's stack is self-describing.
_STATE_DIR = _REPO_ROOT / ".sig" / "ops"
_STATE_FILE = _STATE_DIR / "state.json"
_COMPOSE_PROJECT = "sig"


# --- staging endpoint defaults (HG-12: local staging is acceptable) -----------


def _pg_port() -> str:
    return os.environ.get("SIG_PG_PORT", "5432")


def default_dsn() -> str:
    user = os.environ.get("SIG_PG_USER", "sig")
    password = os.environ.get("SIG_PG_PASSWORD", "sig")
    db = os.environ.get("SIG_PG_DB", "sig")
    return os.environ.get(
        "SIG_STAGING_DSN",
        f"postgresql://{user}:{password}@127.0.0.1:{_pg_port()}/{db}",
    )


def _api_host_port() -> tuple[str, int]:
    return os.environ.get("SIG_API_HOST", "127.0.0.1"), int(os.environ.get("SIG_API_PORT", "8000"))


def default_api_url() -> str:
    host, port = _api_host_port()
    return os.environ.get("SIG_STAGING_API_URL", f"http://{host}:{port}")


def _static_host_port() -> tuple[str, int]:
    return (
        os.environ.get("SIG_STATIC_HOST", "127.0.0.1"),
        int(os.environ.get("SIG_STATIC_PORT", "4321")),
    )


def default_static_url() -> str:
    host, port = _static_host_port()
    return os.environ.get("SIG_STAGING_STATIC_URL", f"http://{host}:{port}")


def _curation_host_port() -> tuple[str, int]:
    # Bound to loopback by default: the curation surface is authenticated and MUST
    # NOT be world-reachable (P21.6, ADR-068, Part VIII §0.7, RISK-P21-10).
    return (
        os.environ.get("SIG_CURATION_HOST", "127.0.0.1"),
        int(os.environ.get("SIG_CURATION_PORT", "8001")),
    )


def default_curation_url() -> str:
    host, port = _curation_host_port()
    return os.environ.get("SIG_STAGING_CURATION_URL", f"http://{host}:{port}")


# --- parser -------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `ops` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-ops",
        description="SIG runtime composition (P21.4): compose the PG spine + API + static site.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    up = sub.add_parser("up", help="bring up PG (+ sqitch deploy), the API, and the static server")
    up.add_argument("--jurisdiction", default="okc", help="jurisdiction slug (default okc)")
    up.add_argument("--seed", action="store_true", help="also seed the jurisdiction after up")
    up.add_argument(
        "--no-static",
        action="store_true",
        help="skip the static server (e.g. web/dist not built yet)",
    )

    sub.add_parser("status", help="report PG / API / static health (non-zero if any is down)")
    sub.add_parser("down", help="stop the API + static processes and tear down the compose project")

    seed = sub.add_parser("seed", help="load a jurisdiction's slice claims into the spine")
    seed.add_argument("--jurisdiction", default="okc", help="jurisdiction slug (default okc)")
    seed.add_argument("--dsn", default=None, help="PostgreSQL DSN (default: SIG_STAGING_DSN/local)")

    egress = sub.add_parser(
        "egress-report",
        help="check monthly egress against the ops/config.toml budget (§38.5, RISK-P21-09)",
    )
    egress.add_argument(
        "--config", default=None, help="ops/config.toml path (default: ops/config.toml)"
    )
    egress.add_argument(
        "--usage-gb",
        type=float,
        default=None,
        help="observed monthly egress (GB); omit when no live usage API (gate pending: HG-07).",
    )

    swh = sub.add_parser(
        "swh-save", help="build a Software Heritage save-code-now request (SIG-GOV-022/023/024)"
    )
    swh.add_argument("--repo-url", default=None, help="the public repository origin URL to save.")
    swh.add_argument("--visit-type", default="git", help="SWH visit type (default: git).")
    swh.add_argument(
        "--now",
        action="store_true",
        help="actually submit to Software Heritage (default: print the request only, untriggered).",
    )

    degraded = sub.add_parser(
        "degraded",
        help="build the fully static site with NO API (degraded-but-alive, SIG-GOV-021)",
    )
    degraded.add_argument(
        "--data-source",
        default="fixtures",
        choices=["fixtures", "export"],
        help="fixtures (committed typed fixtures) or export (last committed export snapshot).",
    )
    degraded.add_argument("--export-dir", default=None, help="export snapshot dir (export mode).")
    return parser


# --- state --------------------------------------------------------------------


def _read_state() -> dict[str, object]:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())  # type: ignore[no-any-return]
        except (ValueError, OSError):
            return {}
    return {}


def _write_state(state: dict[str, object]) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True))


# --- helpers ------------------------------------------------------------------


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = ["docker", "compose", "-p", _COMPOSE_PROJECT, "-f", str(_COMPOSE_FILE), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check, cwd=str(_REPO_ROOT))


def _http_ok(url: str, *, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - local staging
            return 200 <= resp.status < 500
    except (urllib.error.URLError, ConnectionError, OSError, ValueError):
        return False


def _pg_ready(dsn: str) -> bool:
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any failure means "not ready"
        return False


def _wait(predicate: object, *, label: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    check = predicate  # callable
    while time.time() < deadline:
        if check():  # type: ignore[operator]
            return True
        time.sleep(1.0)
    print(f"  timed out waiting for {label}")
    return False


# --- up -----------------------------------------------------------------------


def _cmd_up(args: argparse.Namespace) -> int:
    dsn = default_dsn()
    print("sig-ops up: composing the SIG runtime (PG spine + API + static)")

    # 1. PG spine + sqitch deploy (containers).
    print("  → docker compose up -d (PG18+PostGIS, sqitch deploy)")
    try:
        _compose("up", "-d", "--wait", "db")
    except subprocess.CalledProcessError as exc:
        print(exc.stderr or exc.stdout)
        print("  docker compose failed to start the DB — is the Docker daemon running?")
        return 1
    if not _wait(lambda: _pg_ready(dsn), label="PostgreSQL"):
        return 1
    # sqitch is a one-shot deploy that exits 0; run it to completion.
    print("  → sqitch deploy db/sqitch.plan")
    deploy = _compose("run", "--rm", "sqitch", check=False)
    if deploy.returncode != 0:
        # sqitch exits non-zero if there is nothing to deploy on some versions; treat
        # "Nothing to deploy" as success but surface any real error.
        combined = (deploy.stdout or "") + (deploy.stderr or "")
        if "Nothing to deploy" not in combined:
            print(combined)
            print("  sqitch deploy failed")
            return 1

    state = _read_state()
    state["dsn"] = dsn

    # 2. API (uvicorn) as a host process over the PG spine.
    api_host, api_port = _api_host_port()
    print(f"  → sig-api serve --dsn <staging> on {api_host}:{api_port}")
    api_log = _STATE_DIR / "api.log"
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    api_proc = subprocess.Popen(
        ["sig-api", "serve", "--host", api_host, "--port", str(api_port), "--dsn", dsn],
        stdout=api_log.open("w"),
        stderr=subprocess.STDOUT,
        cwd=str(_REPO_ROOT),
        start_new_session=True,
    )
    state["api_pid"] = api_proc.pid
    state["api_url"] = default_api_url()

    # 2b. The AUTHENTICATED curation service (P21.6, ADR-068) as a SEPARATE host
    # process, bound to loopback and gated on SIG_CURATION_ENABLED=1 (RISK-P21-10,
    # Part VIII §0.7). It is never the public read API and never world-reachable.
    cur_host, cur_port = _curation_host_port()
    print(f"  → sig-api serve-curation on {cur_host}:{cur_port} (authenticated, non-public)")
    curation_log = _STATE_DIR / "curation.log"
    curation_env = {**os.environ, "SIG_CURATION_ENABLED": "1"}
    curation_proc = subprocess.Popen(
        ["sig-api", "serve-curation", "--host", cur_host, "--port", str(cur_port)],
        stdout=curation_log.open("w"),
        stderr=subprocess.STDOUT,
        cwd=str(_REPO_ROOT),
        env=curation_env,
        start_new_session=True,
    )
    state["curation_pid"] = curation_proc.pid
    state["curation_url"] = default_curation_url()

    # 3. Static server for web/dist as a host process.
    if not args.no_static:
        static_host, static_port = _static_host_port()
        dist = _REPO_ROOT / "web" / "dist"
        if not dist.exists():
            print(f"  ! web/dist not found ({dist}); run the web build first. Skipping static.")
        else:
            print(f"  → static server for web/dist on {static_host}:{static_port}")
            static_log = _STATE_DIR / "static.log"
            static_proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "http.server",
                    str(static_port),
                    "--bind",
                    static_host,
                    "--directory",
                    str(dist),
                ],
                stdout=static_log.open("w"),
                stderr=subprocess.STDOUT,
                cwd=str(_REPO_ROOT),
                start_new_session=True,
            )
            state["static_pid"] = static_proc.pid
            state["static_url"] = default_static_url()
    _write_state(state)

    ok_api = _wait(lambda: _http_ok(default_api_url() + "/"), label="API", timeout=45)
    ok_curation = _wait(
        lambda: _http_ok(default_curation_url() + "/"), label="curation", timeout=45
    )
    if not ok_curation:
        print("  ! curation service did not become healthy (see .sig/ops/curation.log)")
    ok_static = True
    if not args.no_static and "static_pid" in state:
        ok_static = _wait(lambda: _http_ok(default_static_url()), label="static", timeout=30)

    if args.seed:
        _cmd_seed(argparse.Namespace(jurisdiction=args.jurisdiction, dsn=dsn))

    if ok_api and ok_static and ok_curation:
        print("sig-ops up: OK — run `sig-ops status` to confirm.")
        return 0
    print("sig-ops up: one or more services did not become healthy (see `sig-ops status`).")
    return 1


# --- status -------------------------------------------------------------------


def _cmd_status(_args: argparse.Namespace) -> int:
    state = _read_state()
    dsn = str(state.get("dsn") or default_dsn())
    api_url = str(state.get("api_url") or default_api_url())
    static_url = str(state.get("static_url") or default_static_url())
    curation_url = str(state.get("curation_url") or default_curation_url())

    pg = _pg_ready(dsn)
    api = _http_ok(api_url + "/")
    curation = _http_ok(curation_url + "/")
    # A static file server has no health route; the root listing is the signal.
    static = _http_ok(static_url)

    def mark(ok: bool) -> str:
        return "healthy" if ok else "DOWN"

    print(f"PG        ({dsn}): {mark(pg)}")
    print(f"API       ({api_url}): {mark(api)}")
    # The curation service is reported SEPARATELY: it is a distinct, authenticated,
    # non-public process (P21.6, ADR-068), never folded into the public API line.
    print(f"curation  ({curation_url}): {mark(curation)}  [authenticated, non-public]")
    print(f"static    ({static_url}): {mark(static)}")
    return 0 if (pg and api and static and curation) else 1


# --- down ---------------------------------------------------------------------


def _kill_pid(pid: object) -> None:
    if not isinstance(pid, int):
        return
    try:
        # start_new_session=True => the child leads its own process group.
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass


def _cmd_down(_args: argparse.Namespace) -> int:
    print("sig-ops down: tearing down the SIG runtime")
    state = _read_state()
    for key in ("api_pid", "curation_pid", "static_pid"):
        _kill_pid(state.get(key))
    print("  → docker compose down -v")
    try:
        _compose("down", "-v", check=False)
    except FileNotFoundError:
        print("  docker not found on PATH")
    if _STATE_FILE.exists():
        _STATE_FILE.unlink()
    print("sig-ops down: OK — no SIG containers or host processes remain.")
    return 0


# --- seed ---------------------------------------------------------------------


def _cmd_seed(args: argparse.Namespace) -> int:
    from .seed import seed_jurisdiction

    dsn = args.dsn or default_dsn()
    if args.jurisdiction != "okc":
        print(f"only the 'okc' jurisdiction slice is seedable in P21.4 (got {args.jurisdiction!r})")
        return 2
    report = seed_jurisdiction(dsn)
    print(
        f"seeded jurisdiction {args.jurisdiction!r}: {report['inserted']} claim(s) inserted, "
        f"{report['duplicates']} duplicate(s), {report['entities']} entity(ies)"
    )
    return 0


def _cmd_egress_report(args: argparse.Namespace) -> int:
    from .egress import EgressConfig, build_report, exit_code_for

    config_path = args.config or (_COMPOSE_FILE.parent / "config.toml")
    config = EgressConfig.from_toml(config_path)
    report = build_report(config, args.usage_gb)
    print(json.dumps(report.as_json(), indent=2, sort_keys=True))
    if report.gate_pending:
        print(
            "gate pending: HG-07 — no live object-store usage API (no credentials); "
            f"budget threshold {config.monthly_budget_gb} GB documented, not measured "
            "(RISK-P21-09).",
            file=sys.stderr,
        )
    return exit_code_for(report)


def _cmd_swh_save(args: argparse.Namespace) -> int:
    from .swh import build_save_request, submit

    repo_url = args.repo_url or os.environ.get("SIG_REPO_URL")
    if not repo_url:
        print(
            "gate pending: no public repository URL to save (pass --repo-url or set "
            "SIG_REPO_URL). Software Heritage save NOT triggered this run.",
            file=sys.stderr,
        )
        return 4
    token = os.environ.get("SIG_SWH_TOKEN")
    request = build_save_request(repo_url, visit_type=args.visit_type, token=token)
    if not args.now:
        print(json.dumps(request.as_json(), indent=2, sort_keys=True))
        print(
            "(untriggered — re-run with --now to submit to Software Heritage; "
            "no token is needed for a public repo)",
            file=sys.stderr,
        )
        return 0
    result = submit(request)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def _cmd_degraded(args: argparse.Namespace) -> int:
    from .degraded import DegradedBuildError, build_static_site

    print("sig-ops degraded: building the fully static site (NO API; last-export banner)")
    try:
        dist = build_static_site(
            repo_root=_REPO_ROOT,
            data_source=args.data_source,
            export_dir=args.export_dir,
        )
    except DegradedBuildError as exc:
        print(str(exc), file=sys.stderr)
        print("sig-ops degraded: FAILED — the site could not be rebuilt.", file=sys.stderr)
        return 1
    print(f"sig-ops degraded: OK — static site at {dist} (cost = $0 beyond the static host).")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `ops` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "up":
        return _cmd_up(args)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "down":
        return _cmd_down(args)
    if args.command == "seed":
        return _cmd_seed(args)
    if args.command == "egress-report":
        return _cmd_egress_report(args)
    if args.command == "swh-save":
        return _cmd_swh_save(args)
    if args.command == "degraded":
        return _cmd_degraded(args)
    parser.print_help()
    return 0
