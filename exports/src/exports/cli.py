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
import os
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
        nargs="?",
        default=None,
        help="Path to an export build-request JSON (see exports.bundle_io fields). "
        "Optional when --jurisdiction is given (a jurisdiction request is built in-code).",
    )
    build.add_argument(
        "--jurisdiction",
        default=None,
        help="Build a jurisdiction release from the committed slice (P21.4): the licence "
        "compartments (ODbL osm_physical + CC-BY sig_graph) AND web/dossiers.json — the "
        "web-shaped dossier bundle the static site is built from (SIG_DATA_SOURCE=export).",
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

    deposit = subparsers.add_parser(
        "deposit",
        help="Deposit a built export to Zenodo (SIG-EXPORT-002). --dry-run is the default.",
    )
    deposit.add_argument("--in", dest="in_dir", required=True, help="A built export directory.")
    deposit.add_argument(
        "--sandbox",
        action="store_true",
        help="Target sandbox.zenodo.org (a REAL sandbox deposit unless --dry-run); needs "
        "SIG_ZENODO_SANDBOX_TOKEN. Without --sandbox the deposit is always offline (dry-run).",
    )
    deposit.add_argument(
        "--dry-run",
        action="store_true",
        help="Force an offline deterministic deposit (FakeZenodoTransport); no network.",
    )
    deposit.add_argument(
        "--deposits-md",
        default="docs/build/DEPOSITS.md",
        help="The append-only deposit ledger to record the DOIs in.",
    )

    tiles = subparsers.add_parser(
        "tiles",
        help="Render a GeoJSON layer to PMTiles (LD-F07/H08); tippecanoe else pure-Python.",
    )
    tiles.add_argument("--in", dest="in_geojson", required=True, help="Input GeoJSON export.")
    tiles.add_argument("--out", required=True, help="Output PMTiles path.")
    tiles.add_argument("--layer", default="devices", help="Vector layer id (default: devices).")
    tiles.add_argument(
        "--license", default="ODbL-1.0", help="Layer SPDX licence (default ODbL-1.0)."
    )

    torrent = subparsers.add_parser(
        "torrent",
        help="Produce a .torrent for a bulk artifact (pure-Python bencode, SIG-EXPORT-009).",
    )
    torrent.add_argument("--in", dest="in_file", required=True, help="The artifact to seed.")
    torrent.add_argument(
        "--out", default=None, help="Output .torrent path (default: <in>.torrent)."
    )
    torrent.add_argument(
        "--tracker", action="append", default=[], help="Announce URL (repeatable; may be omitted)."
    )

    push = subparsers.add_parser(
        "push",
        help="Upload a built export to an S3-compatible store under content-hash keys.",
    )
    push.add_argument("--in", dest="in_dir", required=True, help="A built export directory.")
    push.add_argument("--store", required=True, help="s3://bucket or provider:bucket target.")
    push.add_argument(
        "--endpoint-url", default=None, help="S3-compatible endpoint (SIG_OBJECT_STORE_URL)."
    )
    push.add_argument(
        "--provider",
        default="cloudflare-r2",
        help="Egress provider for the SIG-EXPORT-008 gate (default cloudflare-r2, zero-egress).",
    )
    return parser


def _run_provo(path: str, fmt: str) -> int:
    from .provo import export_lineage
    from .provo_io import lineage_from_json

    with open(path, encoding="utf-8") as fh:
        lineage = lineage_from_json(json.load(fh))
    sys.stdout.write(export_lineage(lineage, fmt=fmt))
    return 0


def _jurisdiction_request(jurisdiction: str) -> dict[str, object]:
    """The in-code export build-request for a jurisdiction (P21.4, fixture-backed).

    Two licence compartments: the OSM-derived physical device layer (ODbL 1.0, its
    OWN separate compartment — §42, HG-02, included in exports with attribution +
    share-alike) and the SIG graph (CC-BY-4.0). No green sources → fixture values.
    """
    if jurisdiction != "okc":
        raise ValueError("only the 'okc' jurisdiction export is buildable in P21.4")
    return {
        "build_spec": {
            "as_of_snapshot": "2026-08-20",
            "as_of_belief": "2026-08-20",
            "ruleset_version": "resolver-ruleset-2026.07",
            "resolver_version": "p08.1/1.0.0",
        },
        "rights": [
            {
                "source_id": "osm",
                "spdx": "ODbL-1.0",
                "attribution": "© OpenStreetMap contributors, ODbL 1.0 (share-alike)",
                "redistributable": True,
                "derivative_permitted": True,
                "terms_url": "https://opendatacommons.org/licenses/odbl/1-0/",
                "retrieval_date": "2026-08-20",
            },
            {
                "source_id": "sig",
                "spdx": "CC-BY-4.0",
                "attribution": "© SIG",
                "redistributable": True,
                "derivative_permitted": True,
                "terms_url": "https://creativecommons.org/licenses/by/4.0/",
                "retrieval_date": "2026-08-20",
            },
        ],
        "tables": [
            {
                "name": "devices",
                "kind": "geo",
                "compartment": "osm_physical",
                "rows": [
                    {
                        "source_id": "osm",
                        "data": {
                            "subject_id": "sig:asset:okc-pole-1",
                            "geometry": {"type": "Point", "coordinates": [-97.5164, 35.4676]},
                            "jurisdiction": "Oklahoma City, Oklahoma",
                        },
                    }
                ],
            },
            {
                "name": "claims",
                "kind": "tabular",
                "rows": [
                    {
                        "source_id": "sig",
                        "data": {
                            "subject_id": "sig:deployment:okc-okcpd-flock",
                            "predicate_id": "claimed_device_count",
                            "value_low": 190,
                            "value_high": 299,
                            "resolution_status": "UNRESOLVED",
                        },
                    }
                ],
            },
        ],
    }


def _run_build(
    request_path: str | None,
    out_dir: str,
    zenodo_dry_run: bool,
    store: str | None,
    base_url: str,
    cdn_url: str,
    jurisdiction: str | None = None,
) -> int:
    from .bundle import build_bundle
    from .bundle_io import build_request_from_json
    from .distribution import ObjectStore

    if jurisdiction is not None:
        doc: dict[str, object] = _jurisdiction_request(jurisdiction)
    else:
        if request_path is None:
            print("sig-exports build: request_json is required unless --jurisdiction is given")
            return 2
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

    # A jurisdiction release also emits the web-shaped dossier bundle the static
    # site reads under SIG_DATA_SOURCE=export (LD-V08). It is JSON derived from the
    # committed slice + the resolver — the same /v1 dossier contract the fixtures
    # carry — so `web/` builds identically from fixtures or from the export.
    if jurisdiction is not None:
        import os

        from .web_dossier import build_web_dossiers

        dossiers = build_web_dossiers(jurisdiction)
        web_dir = os.path.join(out_dir, "web")
        os.makedirs(web_dir, exist_ok=True)
        with open(os.path.join(web_dir, "dossiers.json"), "w", encoding="utf-8") as fh:
            json.dump(dossiers, fh, indent=2, ensure_ascii=False)
        summary["jurisdiction"] = jurisdiction
        summary["dossiers"] = [d["slug"] for d in dossiers]
        summary["web_dossiers_path"] = os.path.join(web_dir, "dossiers.json")

        # The §7 contribution-back leverage metric (P21.7, ADR-069): replay the
        # recorded OSM changeset feed and emit web/leverage.json so the site's
        # /contribution-back page reads the (fixture-replayed) attributions in
        # `export` mode. Fixtures-only — no live OSM poll — and it stores only
        # changeset id + comment (no OSM usernames, Part VIII §0.7). Absent fixtures
        # → a zeroed metric (never fabricate a count we did not measure, §3.1).
        from pathlib import Path as _Path

        from tasks.contribution import LeverageLedger
        from tasks.osm_feed import DEFAULT_FIXTURE_GLOB, leverage_metric_json, pull_files

        repo_root = _Path(__file__).resolve().parents[3]
        fixture_paths = sorted(repo_root.glob(DEFAULT_FIXTURE_GLOB))
        ledger = pull_files(fixture_paths).ledger if fixture_paths else LeverageLedger()
        leverage = leverage_metric_json(ledger)
        with open(os.path.join(web_dir, "leverage.json"), "w", encoding="utf-8") as fh:
            json.dump(leverage, fh, indent=2, sort_keys=True)
        summary["web_leverage_path"] = os.path.join(web_dir, "leverage.json")

        # Render REAL vector tiles for the map (LD-F07/H08 closed, §40, ADR-048/051):
        # the ODbL physical layer's GeoJSON → a PMTiles v3 archive the web build serves
        # at /tiles/sig-infrastructure.pmtiles. The ODbL licence + OSM attribution ride
        # in the tile metadata (§42) — the OSM layer stays its separate compartment.
        from .tiles import ODBL_ATTRIBUTION, render_pmtiles_file

        geojson_path = os.path.join(out_dir, "osm_physical", "devices.geojson")
        if os.path.exists(geojson_path):
            tiles_dir = os.path.join(web_dir, "tiles")
            os.makedirs(tiles_dir, exist_ok=True)
            tiles_out = os.path.join(tiles_dir, "sig-infrastructure.pmtiles")
            renderer = render_pmtiles_file(
                geojson_path,
                tiles_out,
                layer_name="devices",
                license_id="ODbL-1.0",
                attribution=ODBL_ATTRIBUTION,
            )
            summary["tiles"] = {"path": tiles_out, "renderer": renderer, "license": "ODbL-1.0"}
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


def _run_deposit(in_dir: str, sandbox: bool, dry_run: bool, deposits_md: str) -> int:
    """Deposit a built export to Zenodo (SIG-EXPORT-002).

    - no ``--sandbox`` → always an offline dry-run (FakeZenodoTransport, production-shaped
      DOIs) — production deposit is an operator-only action, out of scope here.
    - ``--sandbox --dry-run`` → offline dry-run with the sandbox (``10.5072``) prefix.
    - ``--sandbox`` (no ``--dry-run``) → a REAL sandbox deposit; needs
      ``SIG_ZENODO_SANDBOX_TOKEN`` — absent, exit 4 (``gate pending: HG-07``), write nothing.
    """
    import datetime

    from .deposits import DepositRecord, append_record
    from .zenodo import (
        ZENODO_PRODUCTION_PREFIX,
        ZENODO_SANDBOX_PREFIX,
        FakeZenodoTransport,
        ZenodoHttpTransport,
        ZenodoTransport,
        deposit_export_dir,
    )

    live_sandbox = sandbox and not dry_run
    token = os.environ.get("SIG_ZENODO_SANDBOX_TOKEN")
    if live_sandbox and not token:
        print(
            "sig-exports deposit: gate pending: HG-07 — SIG_ZENODO_SANDBOX_TOKEN not set; "
            "no Zenodo account credential available. Wrote nothing.",
            file=sys.stderr,
        )
        return 4

    extra: dict[str, bytes] = {}
    for extra_name in ("CITATION.cff", "sbom.cdx.json"):
        # Repo-root files that travel with every deposit (§38.2).
        for base in (".", os.path.dirname(os.path.abspath(in_dir))):
            candidate = os.path.join(base, extra_name)
            if os.path.exists(candidate):
                with open(candidate, "rb") as fh:
                    extra[extra_name] = fh.read()
                break

    transport: ZenodoTransport
    if live_sandbox:
        assert token is not None
        transport = ZenodoHttpTransport(token=token, sandbox=True)
        environment = "sandbox"
    else:
        prefix = ZENODO_SANDBOX_PREFIX if sandbox else ZENODO_PRODUCTION_PREFIX
        transport = FakeZenodoTransport(prefix=prefix)
        environment = "sandbox-dry-run" if sandbox else "dry-run"

    deposition = deposit_export_dir(in_dir, transport, extra_files=extra)

    import json as _json

    with open(os.path.join(in_dir, "manifest.json"), encoding="utf-8") as fh:
        release_id = str(_json.load(fh)["release_id"])
    record = DepositRecord(
        release_id=release_id,
        environment=environment,
        deposition=deposition,
        when=datetime.date.today(),
    )
    existing = None
    if os.path.exists(deposits_md):
        with open(deposits_md, encoding="utf-8") as fh:
            existing = fh.read()
    os.makedirs(os.path.dirname(deposits_md) or ".", exist_ok=True)
    with open(deposits_md, "w", encoding="utf-8") as fh:
        fh.write(append_record(existing, record))

    sys.stdout.write(
        json.dumps(
            {
                "environment": environment,
                "release_id": release_id,
                "concept_doi": deposition.concept_doi,
                "version_doi": deposition.version_doi,
                "files": list(deposition.files),
                "deposits_md": deposits_md,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0


def _run_tiles(in_geojson: str, out: str, layer: str, license_id: str) -> int:
    from .tiles import ODBL_ATTRIBUTION, render_pmtiles_file

    renderer = render_pmtiles_file(
        in_geojson, out, layer_name=layer, license_id=license_id, attribution=ODBL_ATTRIBUTION
    )
    sys.stdout.write(
        json.dumps({"out": out, "renderer": renderer, "layer": layer, "license": license_id}) + "\n"
    )
    return 0


def _run_torrent(in_file: str, out: str | None, trackers: list[str]) -> int:
    from .torrent import infohash_v1, make_torrent

    with open(in_file, "rb") as fh:
        data = fh.read()
    out_path = out or (in_file + ".torrent")
    name = os.path.basename(in_file)
    torrent_bytes = make_torrent(data, name, announce_list=trackers, comment="SIG bulk export")
    with open(out_path, "wb") as fh:
        fh.write(torrent_bytes)
    sys.stdout.write(
        json.dumps({"out": out_path, "name": name, "infohash": infohash_v1(torrent_bytes)}) + "\n"
    )
    return 0


def _run_push(in_dir: str, store: str, endpoint_url: str | None, provider: str) -> int:
    from .distribution import ObjectStore
    from .push import build_s3_client, push_export_dir, push_summary

    # Accept both s3://bucket and provider:bucket.
    if store.startswith("s3://"):
        bucket = store[len("s3://") :].split("/", 1)[0]
    else:
        provider, _, bucket = store.partition(":")
    obj_store = ObjectStore(provider=provider, bucket=bucket)
    client = build_s3_client(obj_store, endpoint_url=endpoint_url)
    results = push_export_dir(in_dir, obj_store, client)
    sys.stdout.write(
        json.dumps(dict(push_summary(results, obj_store)), indent=2, sort_keys=True) + "\n"
    )
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
            jurisdiction=args.jurisdiction,
        )
    if args.command == "deposit":
        return _run_deposit(args.in_dir, args.sandbox, args.dry_run, args.deposits_md)
    if args.command == "tiles":
        return _run_tiles(args.in_geojson, args.out, args.layer, args.license)
    if args.command == "torrent":
        return _run_torrent(args.in_file, args.out, args.tracker)
    if args.command == "push":
        return _run_push(args.in_dir, args.store, args.endpoint_url, args.provider)
    parser.print_help()
    return 0
