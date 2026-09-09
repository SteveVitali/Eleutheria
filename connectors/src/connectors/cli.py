# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `connectors` stage (SIG-ENG-013, SIG-INGEST-021).

Every stage of the connector framework stays runnable as a plain CLI so the
orchestration choice is reversible (SIG-INGEST-021, ADR-014). The sub-commands:

* ``validate`` — the registry self-checks that must hold at every phase gate
  (SIG-INGEST-023..040).
* ``stages`` — list the eight stages in order (§21.1, SIG-INGEST-001).
* ``list-connectors`` — list the registered source connectors (the `osm`
  connector lands in P04.2; the plug-in seam they register through, SIG-INGEST-021).
* ``gate --source ID`` — report the connector-loader gate verdict for a source
  (SIG-INGEST-014/028): ingestion_permitted + compact_status + custody_posture.
* ``export-check`` — compute the export licence per compartment across the
  registry and exit non-zero on any incompatibility (SIG-LIC-010).

No fetching logic lives in the CLI; source-specific connectors are P04.2+.
"""

from __future__ import annotations

import argparse

from policy.licensing import LicenseIncompatibilityError, compartments

from . import __version__
from .ecosystem import GroupStatus, local_groups, partners
from .loader import assert_export_compatible, is_loadable, source_export_license
from .registry import get, sources
from .review import flip_ready, gate_breakdown, is_flip_ready, review_metadata_violations
from .stages import registered_connectors, stage_names


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `connectors` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-connectors",
        description="SIG connectors: connector framework, source registry, gate (§21/§22).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate", help="run the source-registry data-layer self-checks")
    sub.add_parser("stages", help="list the eight connector stages in order (§21.1)")
    sub.add_parser("list-connectors", help="list the registered source connectors")
    gate = sub.add_parser("gate", help="report the connector-loader gate verdict for a source")
    gate.add_argument("--source", required=True, help="source id to check")
    sub.add_parser("export-check", help="compute the export licence per compartment (SIG-LIC-010)")
    rev = sub.add_parser(
        "review-status",
        help="per-source rights-review gate breakdown + flip-ready count (P21.1)",
    )
    rev.add_argument("--source", default=None, help="show one source's five-field gate breakdown")
    runp = sub.add_parser(
        "run",
        help="run a connector over a fixture and assert claims into the selected sink (P19.4)",
    )
    runp.add_argument("--connector", required=True, help="registered connector name (e.g. atlas)")
    runp.add_argument("--source", required=True, help="source id for the run (SourceRecord)")
    runp.add_argument("--fixture", required=True, help="path to the committed fixture file")
    runp.add_argument("--kind", required=True, help="target kind (e.g. bulk_csv, overpass)")
    runp.add_argument("--media-type", required=True, help="fixture media type")
    runp.add_argument(
        "--sink",
        default="memory",
        choices=("memory", "pg"),
        help="claim sink: 'memory' (default) or 'pg' (requires --dsn)",
    )
    runp.add_argument("--dsn", default=None, help="PostgreSQL DSN when --sink pg")
    return parser


def _validate() -> int:
    srcs = sources()
    groups = local_groups()
    orgs = partners()
    undetermined = [s for s in srcs if s.rights.spdx.strip().upper() == "UNDETERMINED"]
    permitted = [s for s in srcs if s.ingestion_permitted]
    loadable = [s for s in srcs if is_loadable(s)]
    disappeared = [g for g in groups.values() if g.status is GroupStatus.DISAPPEARED]
    unlocated = [g for g in groups.values() if g.status is GroupStatus.UNLOCATED]
    print(f"registered sources: {len(srcs)}")
    print(f"  rights UNDETERMINED (export gate fails closed): {len(undetermined)}")
    print(f"  ingestion_permitted=true: {len(permitted)}")
    print(f"  loadable now (permitted + compact + custody): {len(loadable)}")
    print(
        f"local groups: {len(groups)} (unlocated {len(unlocated)}, disappeared {len(disappeared)})"
    )
    print(f"national partners: {len(orgs)}")
    # The flip-metadata rule (P21.1, SIG-INGEST-028/038, SIG-LIC-001/009): a row
    # flipped to ingestion_permitted=true is invalid without its review metadata.
    violations = review_metadata_violations(srcs)
    if violations:
        for msg in violations:
            print(f"VALIDATION FAILED: {msg}")
        return 1
    print("connectors registry self-checks OK")
    return 0


def _stages() -> int:
    for i, name in enumerate(stage_names(), start=1):
        print(f"{i}. {name}")
    return 0


def _list_connectors() -> int:
    names = sorted(registered_connectors())
    if not names:
        print("no source connectors registered yet (P04.1 is framework-only; see P04.2/P04.3)")
        return 0
    for name in names:
        print(name)
    return 0


def _gate(source_id: str) -> int:
    try:
        get(source_id)
    except KeyError:
        print(f"unknown source id: {source_id!r}")
        return 2
    ok = is_loadable(source_id)
    print(f"source {source_id!r}: {'LOADABLE' if ok else 'REFUSED'} (SIG-INGEST-014/028)")
    return 0 if ok else 1


def _export_check() -> int:
    # SIG-LIC-010: compute the export licence for each compartment's sources; any
    # incompatibility inside a compartment fails the build (non-zero exit).
    by_compartment: dict[str, list[str]] = {name: [] for name in compartments()}
    licence_to_compartment = {c["license"]: name for name, c in compartments().items()}
    for src in sources():
        if src.rights.spdx.strip().upper() == "UNDETERMINED":
            continue
        compartment = licence_to_compartment.get(source_export_license(src))
        if compartment is not None:
            by_compartment[compartment].append(src.id)
    failures = 0
    for compartment, ids in by_compartment.items():
        if not ids:
            continue
        try:
            licence = assert_export_compatible(ids)
            print(f"compartment {compartment!r}: {len(ids)} source(s) -> {licence}")
        except LicenseIncompatibilityError as exc:
            failures += 1
            print(f"compartment {compartment!r}: INCOMPATIBLE — {exc}")
    if failures:
        print(f"export-check FAILED: {failures} incompatible compartment(s) (SIG-LIC-010)")
        return 1
    print("export-check OK: every compartment exports under a single licence (SIG-LIC-010)")
    return 0


def _review_status(source_id: str | None) -> int:
    # Per-source gate breakdown (SIG-INGEST-014/028, §22.4, §8.4). With --source,
    # print the five gate fields; with no arg, print the same counts as `validate`
    # plus flip-ready and loadable-now.
    if source_id is not None:
        try:
            record = get(source_id)
        except KeyError:
            print(f"unknown source id: {source_id!r}")
            return 2
        bd = gate_breakdown(record)
        print(f"source {source_id!r}:")
        print(
            f"  ingestion_permitted={bd.ingestion_permitted} compact={bd.compact_ok} "
            f"custody={bd.custody_ok} rights={bd.rights_present} reviewed-by={bd.reviewed_by}"
        )
        print(f"  flip-ready: {is_flip_ready(record)}")
        print(f"  loadable now: {bd.loadable}")
        return 0

    srcs = sources()
    permitted = [s for s in srcs if s.ingestion_permitted]
    loadable = [s for s in srcs if is_loadable(s)]
    ready = flip_ready(srcs)
    print(f"registered sources: {len(srcs)}")
    print(f"  ingestion_permitted=true: {len(permitted)}")
    print(f"  flip-ready: {len(ready)}")
    print(f"  loadable now: {len(loadable)}")
    for s in ready:
        print(f"    flip-ready: {s.id}")
    return 0


def _run(args: argparse.Namespace) -> int:
    # Import the source connectors so they register (SIG-INGEST-021).
    from pathlib import Path

    from . import atlas, osm  # noqa: F401  (import side effect: @register)
    from .runner import run_connector_over_fixture

    if args.sink == "pg" and not args.dsn:
        print("--sink pg requires --dsn")
        return 2
    report = run_connector_over_fixture(
        args.connector,
        args.source,
        Path(args.fixture),
        media_type=args.media_type,
        kind=args.kind,
        sink_kind=args.sink,
        dsn=args.dsn,
    )
    print(
        f"connector {args.connector!r}: {len(report.claims)} claim(s), "
        f"{len(report.captures)} capture(s), asserted={report.asserted} "
        f"(sink={args.sink})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `connectors` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
    if args.command == "validate":
        return _validate()
    if args.command == "stages":
        return _stages()
    if args.command == "list-connectors":
        return _list_connectors()
    if args.command == "gate":
        return _gate(args.source)
    if args.command == "export-check":
        return _export_check()
    if args.command == "review-status":
        return _review_status(args.source)
    parser.print_help()
    return 0
