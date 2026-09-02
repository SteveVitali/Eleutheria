# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Plain-CLI entry point for the `exports` stage (SIG-ENG-013).

Every pipeline stage MUST be invocable as a plain CLI. P02.3 adds `provo`, which
serialises a PROV-O lineage document (§21.6). P14.2 adds `build`, which builds a
versioned, licence-computed bulk-export release (§38) from a JSON build request,
writes every artifact + the manifest to an output directory, and optionally performs a
dry-run Zenodo deposit (concept + version DOIs). With no sub-command the CLI prints help
and exits 0 (the SIG-ENG-013 skeleton contract).
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the `exports` stage."""
    parser = argparse.ArgumentParser(
        prog="sig-exports",
        description="SIG exports stage.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    provo = subparsers.add_parser(
        "provo",
        help="Serialise an ingest-run lineage batch as PROV-O (SIG-INGEST-016).",
    )
    provo.add_argument(
        "lineage_json",
        help="Path to a lineage JSON document (see exports.provo.Lineage fields).",
    )
    provo.add_argument(
        "--format",
        default="turtle",
        help="rdflib serialisation format (turtle, nt, json-ld). Default: turtle.",
    )

    build = subparsers.add_parser(
        "build",
        help="Build a versioned, licence-computed bulk-export release (SIG-EXPORT-*).",
    )
    build.add_argument(
        "request_json",
        help="Path to an export build-request JSON (see exports.bundle_io fields).",
    )
    build.add_argument(
        "--out",
        required=True,
        help="Output directory the release artifacts + manifest are written to.",
    )
    build.add_argument(
        "--zenodo-dry-run",
        action="store_true",
        help="Perform an offline (deterministic) Zenodo deposit and print the DOIs.",
    )
    build.add_argument(
        "--store",
        help="Object-store provider:bucket for a distribution plan (e.g. cloudflare-r2:sig). "
        "A metered-egress provider fails the build (SIG-EXPORT-008).",
    )
    build.add_argument("--base-url", default="", help="Object-store base URL for the plan.")
    build.add_argument("--cdn-url", default="", help="CDN base URL for the plan.")
    return parser


def _run_provo(path: str, fmt: str) -> int:
    from .provo import export_lineage
    from .provo_io import lineage_from_json

    with open(path, encoding="utf-8") as fh:
        lineage = lineage_from_json(json.load(fh))
    sys.stdout.write(export_lineage(lineage, fmt=fmt))
    return 0


def _run_build(
    request_path: str,
    out_dir: str,
    zenodo_dry_run: bool,
    store: str | None,
    base_url: str,
    cdn_url: str,
) -> int:
    from .bundle import build_bundle
    from .bundle_io import build_request_from_json
    from .distribution import ObjectStore

    with open(request_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    build_spec, tables, rights, crosswalk = build_request_from_json(doc)
    object_store: ObjectStore | None = None
    if store:
        provider, _, bucket = store.partition(":")
        object_store = ObjectStore(provider=provider, bucket=bucket)
    bundle = build_bundle(
        build_spec,
        tables,
        rights,
        crosswalk=crosswalk,
        store=object_store,
        base_url=base_url,
        cdn_url=cdn_url,
    )
    bundle.write_to(out_dir)

    summary: dict[str, object] = {
        "release_id": build_spec.release_id(),
        "concept_id": build_spec.concept_id(),
        "artifact_count": len(bundle.manifest.artifacts),
        "licenses": sorted(bundle.manifest.licenses()),
        "out_dir": out_dir,
    }
    if zenodo_dry_run:
        from .zenodo import FakeZenodoTransport, deposit_release

        deposition = deposit_release(
            bundle.manifest,
            bundle.artifact_bytes,
            FakeZenodoTransport(),
            evidence_artifacts=bundle.evidence_artifacts,
        )
        summary["zenodo"] = deposition.as_json()
    sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the `exports` CLI. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "provo":
        return _run_provo(args.lineage_json, args.format)
    if args.command == "build":
        return _run_build(
            args.request_json,
            args.out,
            args.zenodo_dry_run,
            args.store,
            args.base_url,
            args.cdn_url,
        )
    parser.print_help()
    return 0
