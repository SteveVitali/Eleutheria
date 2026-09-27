#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P32.14 (SIG-FIND-003, ADR-133) — representative-corpus search benchmark.

Measures the released-corpus search contract over a BUILT release directory
(one `search_index.sqlite` per compartment, integrity-manifest verified):

* cold staging cost — sha256 re-verification + contract check per index;
* warm query latency — 8 concurrent readers over the serving-shaped call
  path (`exports.search_index.search` on verified read-only connections);
* bounded pagination — a complete cursor walk of the largest compartment
  (the tail-reachability AC) plus spot walks elsewhere;
* disk + memory — per-compartment index bytes and process RSS delta.

Usage:
    python3 docs/build/tools/p3214_search_benchmark.py <release_dir> [--readers 8]

Prints the JSON measurement to stdout (the run ledger quotes it).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import resource
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "exports" / "src"))
from exports import search_index as si  # noqa: E402


def _rss() -> int:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r if sys.platform == "darwin" else r * 1024


def _pctl(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = min(len(xs) - 1, max(0, round((p / 100.0) * (len(xs) - 1))))
    return xs[int(k)] * 1000.0


def _open_verified(path: Path, manifest_entry: dict) -> tuple[sqlite3.Connection, dict, float]:
    """The serving-side cold open: manifest verify → ro connect → contract."""
    t0 = time.monotonic()
    data = path.read_bytes()
    ok = (
        hashlib.sha256(data).hexdigest() == manifest_entry["sha256"]
        and len(data) == manifest_entry["byte_size"]
    )
    if not ok:
        raise SystemExit(f"verification failed for {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    meta = si.check_index_contract(conn)
    return conn, meta, (time.monotonic() - t0) * 1000.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("release_dir")
    ap.add_argument("--readers", type=int, default=8)
    ap.add_argument("--rounds", type=int, default=6, help="measured rounds per query kind")
    args = ap.parse_args()
    root = Path(args.release_dir)
    pub = json.loads((root / "release/build_report.json").read_text())["publication_id"]
    manifest = json.loads((root / f"releases/{pub}/integrity_manifest.json").read_text())
    entries = {a["path"]: a for a in manifest["artifacts"]}
    comps = [c["compartment"] for c in manifest["compartments"]]

    report: dict = {
        "schema": "sig.search-index-benchmark/1",
        "publication_id": pub,
        "release_dir": str(root),
        "readers": args.readers,
        "rounds": args.rounds,
        "compartments": {},
        "totals": {},
    }
    rss0 = _rss()

    conns: dict[str, tuple[sqlite3.Connection, dict]] = {}
    for comp in comps:
        rel = f"r/{pub}/c/{comp}/{si.INDEX_FILE}"
        conn, meta, stage_ms = _open_verified(root / rel, entries[rel])
        conns[comp] = (conn, meta)
        report["compartments"][comp] = {
            "index_bytes": entries[rel]["byte_size"],
            "indexed_records": meta["scope"]["indexed_records"],
            "staging_ms": round(stage_ms, 1),
        }

    # -- representative query shapes -------------------------------------- #
    # A common FTS term per compartment: take the first label's first >=3
    # char token (guaranteed present), plus a facet + exact ids from edges.
    def sample(conn: sqlite3.Connection) -> dict:
        first = conn.execute(
            "SELECT record_key, label, jurisdiction FROM records ORDER BY label_sort,"
            " entity_type, entity_id LIMIT 1"
        ).fetchone()
        last = conn.execute(
            "SELECT record_key, label, jurisdiction FROM records ORDER BY label_sort"
            " DESC, entity_type DESC, entity_id DESC LIMIT 1"
        ).fetchone()
        term = next(
            (t for t in (first[1] or "").split() if len(t) >= si.MIN_TEXT_QUERY),
            "camera",
        )
        jur = first[2] or "unreported"
        return {"term": term, "first_key": first[0], "last_key": last[0], "jur": jur}

    samples = {c: sample(conns[c][0]) for c in comps}
    errors: list[str] = []

    def run(comp: str, params: si.SearchParams) -> float:
        """The serving shape: one fresh verified ro connection per request —
        shared sqlite connections cannot be iterated by concurrent readers."""
        rel = f"r/{pub}/c/{comp}/{si.INDEX_FILE}"
        t0 = time.monotonic()
        conn = sqlite3.connect(f"file:{root / rel}?mode=ro", uri=True)
        try:
            meta = si.check_index_contract(conn)
            try:
                si.search(conn, meta, params)
            except si.SearchIndexError as exc:
                errors.append(f"{comp}: {exc.code}: {exc.detail}")
        finally:
            conn.close()
        return time.monotonic() - t0

    lat: dict[str, list[float]] = {k: [] for k in ("browse", "fts", "exact", "facet", "mixed")}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.readers) as pool:
        for _ in range(args.rounds):
            futs = []
            for comp in comps:
                s = samples[comp]
                for kind in lat:
                    if kind == "browse":
                        p = si.parse_params(
                            q=None,
                            kind=None,
                            jurisdiction=None,
                            source=None,
                            location=None,
                            technology=None,
                            limit=50,
                            cursor=None,
                        )
                    elif kind == "fts":
                        p = si.parse_params(
                            q=s["term"],
                            kind=None,
                            jurisdiction=None,
                            source=None,
                            location=None,
                            technology=None,
                            limit=50,
                            cursor=None,
                        )
                    elif kind == "exact":
                        p = si.parse_params(
                            q=s["last_key"],
                            kind=None,
                            jurisdiction=None,
                            source=None,
                            location=None,
                            technology=None,
                            limit=50,
                            cursor=None,
                        )
                    elif kind == "facet":
                        p = si.parse_params(
                            q=None,
                            kind=None,
                            jurisdiction=s["jur"],
                            source=None,
                            location=None,
                            technology=None,
                            limit=50,
                            cursor=None,
                        )
                    else:
                        p = si.parse_params(
                            q=s["term"],
                            kind=None,
                            jurisdiction=s["jur"],
                            source=None,
                            location=None,
                            technology=None,
                            limit=50,
                            cursor=None,
                        )
                    futs.append((kind, pool.submit(run, comp, p)))
            for kind, f in futs:
                lat[kind].append(f.result())

    report["latency_ms"] = {
        k: {
            "n": len(v),
            "p50": round(_pctl(v, 50), 2),
            "p95": round(_pctl(v, 95), 2),
            "max": round(max(v) * 1000.0, 2) if v else 0.0,
        }
        for k, v in lat.items()
    }
    report["errors"] = errors

    # -- tail reachability: full cursor walk of the largest compartment ---- #
    biggest = max(comps, key=lambda c: report["compartments"][c]["indexed_records"])
    conn, meta = conns[biggest]
    seen: list[str] = []
    cursor = None
    t0 = time.monotonic()
    while True:
        res = si.search(
            conn,
            meta,
            si.parse_params(
                q=None,
                kind=None,
                jurisdiction=None,
                source=None,
                location=None,
                technology=None,
                limit=50,
                cursor=cursor,
            ),
        )
        seen.extend(r["record_key"] for r in res["results"])
        cursor = res["next_cursor"]
        if cursor is None:
            break
    report["tail_walk"] = {
        "compartment": biggest,
        "pages": (len(seen) + 49) // 50,
        "records_seen": len(seen),
        "distinct_keys": len(set(seen)),
        "indexed_records": report["compartments"][biggest]["indexed_records"],
        "last_key": seen[-1] if seen else None,
        "expected_last_key": samples[biggest]["last_key"],
        "wall_ms": round((time.monotonic() - t0) * 1000.0, 1),
        "complete": (
            len(seen) == len(set(seen)) == report["compartments"][biggest]["indexed_records"]
            and seen[-1] == samples[biggest]["last_key"]
        ),
    }

    # -- a second, small-compartment walk (different corpus) --------------- #
    smallest = min(comps, key=lambda c: report["compartments"][c]["indexed_records"])
    conn, meta = conns[smallest]
    n = 0
    cursor = None
    while True:
        res = si.search(
            conn,
            meta,
            si.parse_params(
                q=None,
                kind=None,
                jurisdiction=None,
                source=None,
                location=None,
                technology=None,
                limit=50,
                cursor=cursor,
            ),
        )
        n += len(res["results"])
        cursor = res["next_cursor"]
        if cursor is None:
            break
    report["tail_walk_small"] = {
        "compartment": smallest,
        "records_seen": n,
        "indexed_records": report["compartments"][smallest]["indexed_records"],
        "complete": n == report["compartments"][smallest]["indexed_records"],
    }

    report["totals"] = {
        "index_bytes": sum(c["index_bytes"] for c in report["compartments"].values()),
        "indexed_records": sum(c["indexed_records"] for c in report["compartments"].values()),
        "peak_rss_bytes_after_load": _rss(),
        "rss_delta_bytes": _rss() - rss0,
    }
    for c in conns.values():
        c[0].close()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
