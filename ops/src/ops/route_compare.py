# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.40 deliverable 6 — the byte-compare dark check.

Every route on the public allow-list (``ops/public_routes.toml``) is fetched
and fingerprinted: HTTP status + body sha256 + byte length. A *capture*
records the fingerprint set for an origin; a *verify* diffs two captures —
the AC's "0 differences on every allow-listed route" is exactly an empty
diff, and any difference fails the leg.

Deny-covered routes (``[[denied]]``) are captured too: a route that must be
absent flipping 404 → something is the leak detector firing. A fetch that
cannot reach the origin is a hard error — a dead origin is never read as a
successful deny (the contract's fail-closed rule).

The probe is read-only GETs. It runs against the canonical origin and the
``*.run.app`` service URL at leg time, and against the composed edge in the
e2e — one code path, one fingerprint format (``route-capture/1``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .publish import load_allowlist

CAPTURE_SCHEMA = "route-capture/1"

#: Seconds a single route GET may take before the origin counts as down.
FETCH_TIMEOUT = 20


def route_paths(allowlist_path: str | Path | None = None) -> list[str]:
    """The deterministic probe set: every allow-listed top-level entry (a
    directory entry probes ``/<entry>/``, a file probes ``/<entry>``) plus
    every ``[[denied]]`` route. Sorted; the allow-list is the only source.
    """
    allow = load_allowlist(allowlist_path)
    paths: list[str] = []
    for entry in sorted(allow.top_level):
        paths.append(f"/{entry}" if "." in entry.rsplit("/", 1)[-1] else f"/{entry}/")
    for denied in allow.denied_routes:
        paths.append(denied)
    return sorted(set(paths))


def _fetch(url: str) -> tuple[int, bytes]:
    """GET ``url`` → (status, body). Raises RuntimeError on a dead origin —
    never mapped to a status, so an unreachable host cannot masquerade as a
    denied route."""
    req = urllib.request.Request(url, headers={"User-Agent": "sig-route-compare/1"})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:  # noqa: S310
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:  # a real HTTP answer, e.g. 404
        return e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"origin unreachable for {url}: {e}") from e


def capture(
    base_url: str,
    *,
    allowlist_path: str | Path | None = None,
    fetcher: Callable[[str], tuple[int, bytes]] = _fetch,
) -> dict[str, Any]:
    """Fingerprint every allow-listed route on ``base_url``."""
    base = base_url.rstrip("/")
    routes: dict[str, Any] = {}
    for path in route_paths(allowlist_path):
        status, body = fetcher(base + path)
        routes[path] = {
            "status": status,
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
        }
    return {
        "schema": CAPTURE_SCHEMA,
        "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_url": base,
        "routes": routes,
    }


def verify(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """The diff between two captures — one line per changed route:
    status drift, byte drift, or a route present on only one side."""
    diffs: list[str] = []
    ra, rb = a.get("routes", {}), b.get("routes", {})
    for path in sorted(set(ra) | set(rb)):
        if path not in ra:
            diffs.append(f"{path}: only in {b.get('base_url', 'B')} ({rb[path]})")
            continue
        if path not in rb:
            diffs.append(f"{path}: only in {a.get('base_url', 'A')} ({ra[path]})")
            continue
        fa, fb = ra[path], rb[path]
        if fa["status"] != fb["status"]:
            diffs.append(f"{path}: status {fa['status']} → {fb['status']}")
        elif fa["sha256"] != fb["sha256"]:
            diffs.append(
                f"{path}: body changed (status {fa['status']}, {fa['bytes']}B → {fb['bytes']}B)"
            )
    return diffs


def _write(capture_doc: dict[str, Any], out: str) -> None:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(capture_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops route-compare",
        description="P34.40 dark check: byte-compare every allow-listed "
        "route between two captures (status + body sha256). Read-only GETs; "
        "an unreachable origin is an error, never a deny.",
    )
    sub = parser.add_subparsers(dest="rc_command", required=True)

    cap = sub.add_parser("capture", help="fingerprint an origin → route-capture/1 JSON")
    cap.add_argument("--base", required=True, help="origin base URL (no trailing slash)")
    cap.add_argument("--out", required=True, help="capture JSON path")
    cap.add_argument(
        "--allowlist",
        default=None,
        help="ops/public_routes.toml path (default: the committed file)",
    )

    ver = sub.add_parser(
        "verify",
        help="diff two captures — empty diff passes (exit 0), any difference fails",
    )
    ver.add_argument("--a", required=True, help="the before capture")
    ver.add_argument("--b", required=True, help="the after capture")

    args = parser.parse_args(argv)
    if args.rc_command == "capture":
        doc = capture(args.base, allowlist_path=args.allowlist)
        _write(doc, args.out)
        print(f"route-compare capture: {len(doc['routes'])} routes → {args.out}")
        return 0
    if args.rc_command == "verify":
        a = json.loads(Path(args.a).read_text(encoding="utf-8"))
        b = json.loads(Path(args.b).read_text(encoding="utf-8"))
        diffs = verify(a, b)
        if diffs:
            for d in diffs:
                print(f"DIFF: {d}")
            return 4
        print(
            f"route-compare verify: {len(set(a.get('routes', {})) & set(b.get('routes', {})))} "
            "routes byte-identical"
        )
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
