# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `inference` stage (SIG-ENG-013).

Every pipeline stage MUST be invocable as a plain CLI. This wires the four §32
inference surfaces to their existing modules (P19.5, LD-F15):

* ``coverage``      — probe queryable negative-space records for a predicate over a
  candidate set (``inference.coverage.probe_coverage_records``, §32.1).
* ``access-paths``  — enumerate bounded reachability paths from a source org over a
  set of sharing/integration edges (``inference.access_paths.close_access_paths``, §30.2).
* ``completeness``  — build a §32.5 completeness statement and prove it cannot imply a
  population total (``inference.completeness.assert_no_population_total``, §32.5).
* ``freshness``     — the §32.4 per-source freshness surface, honouring per-predicate
  volatility (``inference.freshness.source_freshness``, §32.4).

Each sub-command reads a small JSON payload from a file (``--input``) or, when none is
given, runs a built-in OKC-slice demonstration so the surface is exercisable out of the
box. Output is JSON on stdout. With no sub-command it prints help and exits 0.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from typing import Any

from . import __version__
from .access_paths import AccessEdge, close_access_paths
from .completeness import CompletenessMethod, CompletenessStatement, assert_no_population_total
from .coverage import probe_coverage_records
from .freshness import source_freshness


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `inference` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-inference",
        description="SIG inference stage: coverage, access paths, completeness, freshness (§32).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    cov = sub.add_parser("coverage", help="probe queryable negative-space records (§32.1)")
    cov.add_argument("--input", default=None, help="JSON file of a coverage probe payload")

    ap = sub.add_parser("access-paths", help="enumerate bounded reachability paths (§30.2)")
    ap.add_argument("--input", default=None, help="JSON file of {source, edges[], as_of}")

    comp = sub.add_parser("completeness", help="a denominated completeness statement (§32.5)")
    comp.add_argument("--input", default=None, help="JSON file of a completeness statement")

    fresh = sub.add_parser("freshness", help="the per-source freshness surface (§32.4)")
    fresh.add_argument("--input", default=None, help="JSON file of a freshness payload")
    return parser


def _load(path: str | None) -> dict[str, Any] | None:
    if path is None:
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _run_coverage(args: argparse.Namespace) -> int:
    payload = _load(args.input) or {
        "predicate_id": "active_device_count",
        "candidates": ["agency:okcpd", "agency:tulsapd", "agency:normanpd"],
        "present": ["agency:okcpd"],
        "sources_searched": ["src:eff_atlas", "src:deflock", "src:okc_procurement"],
        "subject_class": "us.le.municipal_police",
        "jurisdiction_id": "us/ok",
    }
    records = probe_coverage_records(
        predicate_id=str(payload["predicate_id"]),
        candidates=list(payload["candidates"]),
        present=list(payload["present"]),
        sources_searched=list(payload["sources_searched"]),
        subject_class=payload.get("subject_class"),
        jurisdiction_id=payload.get("jurisdiction_id"),
    )
    print(json.dumps([r.public_view() for r in records], indent=2, default=str))
    return 0


def _run_access_paths(args: argparse.Namespace) -> int:
    payload = _load(args.input)
    if payload is None:
        edges = [
            AccessEdge(
                from_org="agency:okcpd",
                to_org="agency:okc_rtcc",
                edge_label="configured_access",
                scope="region",
                evidence=("claim:okcpd-rtcc",),
                confidence="probable",
            ),
            AccessEdge(
                from_org="agency:okc_rtcc",
                to_org="vendor:flock",
                edge_label="federates_search_to",
                scope="region",
                evidence=("claim:rtcc-flock",),
                confidence="probable",
            ),
        ]
        source, as_of = "agency:okcpd", date(2026, 9, 1)
    else:
        edges = [
            AccessEdge(
                from_org=str(e["from_org"]),
                to_org=str(e["to_org"]),
                edge_label=str(e["edge_label"]),
                scope=str(e.get("scope", "all_data")),
                evidence=tuple(e.get("evidence", ("claim:cli",))),
                confidence=str(e.get("confidence", "probable")),
            )
            for e in payload["edges"]
        ]
        source = str(payload["source"])
        as_of = date.fromisoformat(str(payload.get("as_of", date.today().isoformat())))
    closure = close_access_paths(edges, source=source, as_of=as_of)
    out = [
        {
            "source": p.source,
            "target": p.target,
            "hops": [h.hop_view() for h in p.hops],
            "confidence": p.confidence,
            "temporal_status": p.temporal_status,
            "speculative": p.speculative,
            "is_headline": p.is_headline,
        }
        for p in closure.paths
    ]
    print(json.dumps(out, indent=2, default=str))
    return 0


def _run_completeness(args: argparse.Namespace) -> int:
    payload = _load(args.input) or {
        "method": "counted_with_denominator",
        "named_denominator": "agencies with a published surveillance-tech inventory",
        "value": 0.42,
        "violated_assumptions": [],
    }
    statement = CompletenessStatement(
        method=CompletenessMethod(str(payload["method"])),
        named_denominator=str(payload["named_denominator"]),
        value=float(payload["value"]),
        violated_assumptions=tuple(payload.get("violated_assumptions", ())),
    )
    # The choke point: a figure that could imply a population total fails here.
    checked = assert_no_population_total(statement)
    print(json.dumps(checked.as_json(), indent=2, default=str))
    return 0


def _run_freshness(args: argparse.Namespace) -> int:
    payload = _load(args.input) or {
        "source_id": "src:eff_atlas",
        "status": "healthy",
        "last_successful_run": "2026-08-25T00:00:00+00:00",
        "last_content_change": "2026-08-20T00:00:00+00:00",
        "observations": [
            ["active_device_count", "2026-08-20"],
            ["contract_end_date", "2021-01-01"],
        ],
        "as_of": "2026-09-01",
    }

    def _dt(value: Any) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    freshness = source_freshness(
        str(payload["source_id"]),
        status=str(payload["status"]),
        last_successful_run=_dt(payload.get("last_successful_run")),
        last_content_change=_dt(payload.get("last_content_change")),
        observations=[(str(p), date.fromisoformat(str(d))) for p, d in payload["observations"]],
        as_of=date.fromisoformat(str(payload["as_of"])),
    )
    print(
        json.dumps(
            {
                "source_id": freshness.source_id,
                "status": freshness.status,
                "stale_count": freshness.stale_count,
                "tracked_count": freshness.tracked_count,
                "last_successful_run": freshness.last_successful_run,
                "last_content_change": freshness.last_content_change,
            },
            indent=2,
            default=str,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `inference` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "coverage":
        return _run_coverage(args)
    if args.command == "access-paths":
        return _run_access_paths(args)
    if args.command == "completeness":
        return _run_completeness(args)
    if args.command == "freshness":
        return _run_freshness(args)
    parser.print_help()
    return 0
