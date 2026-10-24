# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.51 (SIG-FIND-005, F-173, K0 §4.12.6): the deterministic SYNTHETIC national
fixture — the real-sized dataset the page-type budgets and the generated
Lighthouse gate measure against.

What this is NOT: a production export, a disguised subset of one, or a hand-authored
web fixture. Every name it emits is invented — the ``assert_no_real_names`` guard
fails the build if any emitted human-readable string matches the committed
real-name blocklist, so a synthetic row can never masquerade as an observed one.
The fixture is an overlay the web build reads only when ``SIG_DATA_SOURCE=national``
is set explicitly (``web/src/lib/data.ts``); it writes nothing outside ``--out``
and mutates nothing.

Floors (K0 §4.12.6, the ticket's declared counts):
  - ≥ 232,000 sites      (``SITE_COUNT``)
  - ≥ 5,000 agencies     (``AGENCY_COUNT``)
  - ≥ 400,000 sharing edges (``SHARING_EDGE_COUNT``)

Determinism: a single ``random.Random(SEED)`` drives every draw; two runs produce
byte-identical trees (``tests/unit/test_national_fixture.py`` proves it by
rebuilding and comparing sha256s). The PMTiles archive is rendered by the SAME
``exports.tiles.render_compartment_sites_pmtiles`` the real export uses — the
tile path the map measures is the production renderer, not a stub.

Layout (the national overlay layout — ``web/src/lib/data.ts#nationalDir``)::

    <out>/
      manifest.json                    release-shaped manifest + the fixture block
      fixture.json                     sig.national-fixture/1 provenance + sha256 map
      sig_graph/ATTRIBUTION.json       invented-source attribution index
      web/map.json                     sig map layer — ≥232k invented assets
      web/network.json                 nodes/edges/access_paths — ≥5k agencies, ≥400k edges
      web/tiles/sig_graph-sites.<sha8>.pmtiles
      web/tiles/index.json           sig.map-tiles/2 index (P35.52, ADR-156)
      sig_graph/sites.geojson        the source geojson the verifier replays
      web/analytics/density_bins.json  H3 res-3 bins computed over the synthetic sites
      web/analytics/centrality.json    declares the synthetic ego-focus entity
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
# The exports workspace member supplies the real PMTiles renderer and the real
# H3 res-3 binning the production analytics run uses.
sys.path.insert(0, str(REPO_ROOT / "exports" / "src"))
sys.path.insert(0, str(REPO_ROOT / "policy" / "src"))

import h3  # noqa: E402
from exports.manifest import canonical_json, tiles_index_document  # noqa: E402
from exports.tiles import (  # noqa: E402
    render_compartment_sites_pmtiles,
    tiles_index_entry,
)
from policy.sensitivity import apply_tier  # noqa: E402

# --------------------------------------------------------------------------- #
# The declared fixture parameters — the floors live here so the test suite can
# assert them verbatim (K0 §4.12.6).
# --------------------------------------------------------------------------- #

SCHEMA = "sig.national-fixture/1"
SEED = 20261022
SITE_COUNT = 232_500
AGENCY_COUNT = 5_200
PARTNER_COUNT = 1_260
SHARING_EDGE_COUNT = 405_000
ACCESS_PATH_COUNT = 48
#: The synthetic ego-focus the centrality artifact declares — invented, never
#: the committed demo corpus's ``agency:okcpd``.
FOCUS_ENTITY_ID = "agency:syn-focus"
JURISDICTION_COUNT = 52
COMPARTMENT = "sig_graph"
LICENSE_ID = "CC0-1.0"
DENSITY_H3_RESOLUTION = 3  # the same resolution exports.analytics uses (§19.5)

#: Invented-name token every generated human-readable name carries — the
#: synthetic family marker the name guard asserts on every emitted label.
SYN = "Syn"

#: Real organisation/jurisdiction names that must never appear in an emitted
#: label (F-173). Case-insensitive substring match over every emitted
#: human-readable string — the guard is deliberately broad (a real name inside
#: any label fails the build).
REAL_NAME_BLOCKLIST = (
    # Vendors named anywhere in the corpus/spec.
    "flock",
    "motorola",
    "axon",
    "verkada",
    "genetec",
    "shotspotter",
    "soundthinking",
    "palantir",
    "peregrine",
    "vigilant",
    "rekor",
    "clearview",
    "hikvision",
    "dahua",
    "banjo",
    "dataminr",
    "predpol",
    "geolitica",
    "leonardo",
    "nec",
    "thales",
    "anduril",
    "briefcam",
    "cobra",
    "fusus",
    "platevision",
    "novoa",
    "lexipol",
    "powerdms",
    # Jurisdictions named in the committed fixtures/dossiers.
    "oklahoma",
    "tulsa",
    "brussels",
    "paris",
    "chicago",
    "detroit",
    "atlanta",
    "memphis",
    "new orleans",
    "new york",
    "los angeles",
    "san francisco",
    "seattle",
    "baltimore",
    "oakland",
    "denver",
)

TECHNOLOGIES = (
    "alpr-fixed",
    "alpr-mobile",
    "fixed-camera-cctv",
    "fixed-camera-unspecified",
    "private-camera-integration-live-feeds",
)
ACCESS_KINDS = ("declared_policy", "observed_use", "configured_access")
ACCESS_WEIGHTS = (0.60, 0.25, 0.15)
SUPPORTS = ("STRONGLY_SUPPORTED", "PROBABLE", "WEAKLY_SUPPORTED", "UNSUPPORTED")
SUPPORT_WEIGHTS = (0.55, 0.30, 0.10, 0.05)
RELATIONS = {
    "declared_policy": "shares data under a declared policy",
    "observed_use": "observed sharing in use",
    "configured_access": "configured technical access",
}
PRECISIONS = ("~100 m grid", "cell centroid", "jurisdiction centroid")
ABSENCE_KINDS = ("NOT_RESEARCHED", "NO_EVIDENCE_FOUND", "UNRESOLVED")

# CONUS-ish bounding box — invented coordinates inside it only.
LAT_MIN, LAT_MAX = 25.0, 48.0
LON_MIN, LON_MAX = -124.0, -67.0


# --------------------------------------------------------------------------- #
# Name guard (F-173): every emitted human-readable string is invented.
# --------------------------------------------------------------------------- #


def _iter_strings(node: Any):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _iter_strings(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _iter_strings(v)


def assert_no_real_names(node: Any, *, where: str) -> None:
    """F-173: refuse any emitted string carrying a real-name blocklist token.

    Ids/paths are structural (``site:syn-…``); the guard scans every string —
    a real name anywhere in the tree is a build error, never a dropped label.
    """
    for s in _iter_strings(node):
        low = s.lower()
        for token in REAL_NAME_BLOCKLIST:
            if token in low:
                raise ValueError(
                    f"F-173 name guard: {where} emitted a string containing "
                    f"real-name token {token!r}: {s!r}"
                )


def _check_generated_name(name: str) -> str:
    """Every generated label carries the invented-name marker — a name that
    doesn't is a generator bug, not a coincidence to bless."""
    if SYN.lower() not in name.lower():
        raise ValueError(f"generated name lacks the {SYN!r} invented marker: {name!r}")
    assert_no_real_names(name, where="name")
    return name


# --------------------------------------------------------------------------- #
# Generators — one seeded RNG drives every draw.
# --------------------------------------------------------------------------- #


def _jurisdiction_centers() -> list[tuple[float, float]]:
    """One invented metro cluster centre per synthetic jurisdiction — a 8×7 grid
    over the CONUS-ish box. Real jurisdiction geography clusters; a uniform
    scatter would put every key in every density cell (an unrealistic
    mixed-key annotation AND a dishonestly worst-case document)."""
    centers: list[tuple[float, float]] = []
    cols, rows = 8, 7
    lat_span = LAT_MAX - LAT_MIN
    lon_span = LON_MAX - LON_MIN
    for r in range(rows):
        for c in range(cols):
            lat = LAT_MIN + lat_span * (r + 0.5) / rows
            lon = LON_MIN + lon_span * (c + 0.5) / cols
            centers.append((lat, lon))
    return centers[:JURISDICTION_COUNT]


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def gen_sites(rng: random.Random) -> list[dict[str, Any]]:
    """≥232k invented map assets (~90% locatable, ~10% jurisdiction-indicated),
    geographically clustered around each synthetic jurisdiction's centre —
    the shape a real corpus has."""
    centers = _jurisdiction_centers()
    sites: list[dict[str, Any]] = []
    for i in range(SITE_COUNT):
        ji = i % JURISDICTION_COUNT
        jurisdiction = f"syn.state.{ji + 1:02d}"
        tech = TECHNOLOGIES[i % len(TECHNOLOGIES)]
        # ~90% publishable point, ~10% location absence → jurisdiction indicator.
        located = rng.random() < 0.90
        asset: dict[str, Any] = {
            "id": f"site:syn-{i:06d}",
            "label": _check_generated_name(f"Synthetic {tech.replace('-', ' ').title()} {i:06d}"),
            "jurisdiction": jurisdiction,
            "technology": tech,
            "technologyStatus": "resolved",
            # the two invented sources (the attribution block names them) —
            # source_ids feed the cells layer's `ns` (distinct sources).
            "source_id": ("src:syn-municipal-01", "src:syn-bulletins-02")[i % 2],
        }
        if located:
            tier_roll = rng.random()
            tier = 0 if tier_roll < 0.55 else (1 if tier_roll < 0.90 else 2)
            asset["tier"] = tier
            clat, clon = centers[ji]
            # ~85% tight cluster (~1.5°σ), ~15% a wider rural spread — both stay
            # inside the box; an H3 cell is then dominated by one jurisdiction
            # the way real cells are.
            spread = 1.5 if rng.random() < 0.85 else 6.0
            asset["lat"] = round(_clamp(rng.gauss(clat, spread), LAT_MIN, LAT_MAX), 6)
            asset["lon"] = round(_clamp(rng.gauss(clon, spread), LON_MIN, LON_MAX), 6)
            asset["precision"] = PRECISIONS[i % len(PRECISIONS)]
        else:
            asset["tier"] = 3
            asset["lat"] = None
            asset["lon"] = None
            asset["precision"] = "no publishable point"
            asset["locationAbsence"] = ABSENCE_KINDS[i % len(ABSENCE_KINDS)]
        sites.append(asset)
    return sites


def gen_jurisdiction_indicators(
    sites: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """The no-point roll-up the map's jurisdiction indicators render."""
    by: dict[str, list[str]] = {}
    for a in sites:
        if a["lat"] is None or a["lon"] is None or a["tier"] == 3:
            by.setdefault(a["jurisdiction"], []).append(a["id"])
    return [
        {"jurisdiction": j, "count": len(ids), "assetIds": ids} for j, ids in sorted(by.items())
    ]


def gen_network(rng: random.Random) -> dict[str, Any]:
    """≥5k agency nodes + partner nodes + ≥400k sharing edges + access paths."""
    nodes: list[dict[str, Any]] = [
        {
            "id": FOCUS_ENTITY_ID,
            "label": _check_generated_name("Synthetic Metro Police Department"),
            "type": "agency",
            "label_basis": "source_name",
        }
    ]
    agencies = [FOCUS_ENTITY_ID]
    for i in range(AGENCY_COUNT - 1):
        nid = f"agency:syn-{i:05d}"
        agencies.append(nid)
        nodes.append(
            {
                "id": nid,
                "label": _check_generated_name(f"Synthetic Municipal Agency {i:05d}"),
                "type": "agency",
                "label_basis": "source_name",
            }
        )
    partners: list[str] = []
    for i in range(PARTNER_COUNT):
        ntype = "vendor" if i % 5 else "rtcc"
        nid = f"{ntype}:syn-{i:05d}"
        partners.append(nid)
        label = (
            f"Synthetic Vendor Systems {i:05d}"
            if ntype == "vendor"
            else f"Synthetic Regional Centre {i:05d}"
        )
        nodes.append(
            {
                "id": nid,
                "label": _check_generated_name(label),
                "type": ntype,
                "label_basis": "source_name",
            }
        )

    # A bounded claim-id pool — ids are structural, never names.
    claim_pool = [f"claim:syn-{i:05d}" for i in range(640)]

    edges: list[dict[str, Any]] = []
    n_agencies = len(agencies)
    n_partners = len(partners)
    for i in range(SHARING_EDGE_COUNT):
        # Focus gets a guaranteed ~300-edge ego neighbourhood first so the
        # bounded view's "50 of N" truncation is exercised at real scale.
        if i < 300:
            frm = FOCUS_ENTITY_ID
            to = partners[i % n_partners]
        else:
            frm = agencies[1 + (i % (n_agencies - 1))]
            to = partners[rng.randrange(n_partners)]
        kind = rng.choices(ACCESS_KINDS, weights=ACCESS_WEIGHTS, k=1)[0]
        support = rng.choices(SUPPORTS, weights=SUPPORT_WEIGHTS, k=1)[0]
        roll = rng.random()
        edge: dict[str, Any] = {
            "from": frm,
            "to": to,
            "access_kind": kind,
            "relation": RELATIONS[kind],
            "support": support,
            "evidence_count": 1 + (i % 4),
            "evidence": [claim_pool[i % len(claim_pool)]],
            "claim_ids": [claim_pool[i % len(claim_pool)]],
            "source": f"Synthetic Source {i % 97:02d}",
            "sources": [f"Synthetic Source {i % 97:02d}"],
        }
        if roll < 0.05:
            # ~5% ended edges — the visibly-marked "ended/undated" block.
            edge.update(
                {
                    "observed_at": "2024-03-15",
                    "date_kind": "observed",
                    "valid_from_kind": "unknown",
                    "valid_to_kind": "exact",
                    "valid_to": "2025-06-30",
                    "historical": True,
                }
            )
        elif roll < 0.10:
            # ~5% undated — the honest "not dated" class (SIG-TIME-012).
            edge.update(
                {
                    "observed_at": None,
                    "date_kind": "undated",
                    "valid_from_kind": "unknown",
                    "valid_to_kind": "unknown",
                }
            )
        else:
            edge.update(
                {
                    "observed_at": f"2025-{(i % 12) + 1:02d}-15",
                    "date_kind": "observed",
                    "valid_from_kind": "unknown",
                    "valid_to_kind": "unknown",
                }
            )
        edges.append(edge)

    # Access paths: contiguous two-hop chains over real generated nodes, every
    # hop evidenced (SIG-UI-025 — an unexplained hop is a forbidden edge).
    paths: list[dict[str, Any]] = []
    for i in range(ACCESS_PATH_COUNT):
        a = agencies[1 + (i % (n_agencies - 1))]
        m = partners[i % n_partners]
        b = agencies[1 + ((i + 7) % (n_agencies - 1))]
        hops = [
            {
                "from_org": a,
                "to_org": m,
                "edge_label": "declared sharing",
                "scope": "records",
                "confidence": "probable",
                "evidence": [claim_pool[(i * 3) % len(claim_pool)]],
            },
            {
                "from_org": m,
                "to_org": b,
                "edge_label": "onward sharing",
                "scope": "records",
                "confidence": "possible",
                "evidence": [claim_pool[(i * 3 + 1) % len(claim_pool)]],
            },
        ]
        paths.append({"hops": hops})

    return {"nodes": nodes, "edges": edges, "access_paths": paths}


def gen_density_bins(sites: list[dict[str, Any]]) -> dict[str, Any]:
    """H3 res-3 bins over the synthetic tier-0 located points — the same cell
    resolution ``exports.analytics`` uses (§19.5)."""
    cells: dict[str, dict[str, Any]] = {}
    n = 0
    for a in sites:
        if a["tier"] != 0 or a["lat"] is None or a["lon"] is None:
            continue
        cell = h3.latlng_to_cell(a["lat"], a["lon"], DENSITY_H3_RESOLUTION)
        agg = cells.setdefault(cell, {"count": 0, "sources": set(), "jurisdictions": {}})
        agg["count"] += 1
        agg["sources"].add("synthetic")
        j = a["jurisdiction"]
        agg["jurisdictions"][j] = agg["jurisdictions"].get(j, 0) + 1
        n += 1
    bins = [
        {
            "h3": cell,
            "jurisdiction": sorted(agg["jurisdictions"].items(), key=lambda kv: (-kv[1], kv[0]))[0][
                0
            ],
            "jurisdiction_counts": dict(sorted(agg["jurisdictions"].items())),
            "recordCount": agg["count"],
            "coverage": "low",
        }
        for cell, agg in sorted(cells.items())
    ]
    return {
        "schema": "sig/analytics-density-bins/1",
        "as_of": "2025-06-01",
        "denominator": f"{n} tier-0 synthetic published points (invented fixture data)",
        "is_population_total": False,
        "source_compartments": [COMPARTMENT],
        "bins": bins,
    }


def gen_centrality() -> dict[str, Any]:
    """The focus declaration — the synthetic ego-focus, never the demo focus."""
    return {
        "schema": "sig/analytics-centrality/1",
        "as_of": "2025-06-01",
        "denominator": f"{AGENCY_COUNT + PARTNER_COUNT} synthetic nodes (invented fixture data)",
        "is_population_total": False,
        "source_compartments": [COMPARTMENT],
        "focus": {
            "entity_id": FOCUS_ENTITY_ID,
            "rule": "declared synthetic fixture focus — a high-degree invented agency node",
        },
        "statistics": [],
    }


def gen_geojson(sites: list[dict[str, Any]]) -> bytes:
    """The sites.geojson the PMTiles renderer consumes — located, non-tier-3
    points only. P35.52 (sig.map-tiles/2): the coordinates go through the REAL
    tier transform (``policy.sensitivity.apply_tier`` — tier 1 truncated, tier 2
    binned) so the verifier's precision check measures true tier behaviour, and
    each feature carries the ``source_ids`` the ``ns`` cell property counts."""
    features = []
    for a in sites:
        if a["lat"] is None or a["lon"] is None or a["tier"] == 3:
            continue
        reduced = apply_tier(a["lat"], a["lon"], a["tier"])
        if reduced is None:
            continue
        lat, lon = reduced
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "entity_id": a["id"],
                    "entity_type": "surveillance_device",
                    "label": a["label"],
                    "jurisdiction": a["jurisdiction"],
                    "sensitivity_tier": a["tier"],
                    "precision": a["precision"],
                    "source_ids": [a["source_id"]],
                },
            }
        )
    return json.dumps(
        {"type": "FeatureCollection", "features": features},
        separators=(",", ":"),
    ).encode("utf-8")


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #


def _write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _dump(node: Any) -> bytes:
    return (json.dumps(node, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _dump_compact(node: Any) -> bytes:
    """Compact serialization for the heavy artifacts — pretty-printing 232k
    sites / 405k edges nearly doubles the bytes for zero reader benefit."""
    return json.dumps(node, separators=(",", ":")).encode("utf-8")


def build(out_dir: Path) -> dict[str, Any]:
    rng = random.Random(SEED)
    print(f"[national-fixture] seed={SEED} out={out_dir}", flush=True)

    sites = gen_sites(rng)
    assert_no_real_names(sites, where="map assets")
    indicators = gen_jurisdiction_indicators(sites)
    map_doc = {
        "layers": [
            {
                "id": "physical_devices",
                "label": "Physical devices",
                "kind": "observed",
                "description": "Cameras, ALPRs, and other hardware SIG has a location claim for.",
            }
        ],
        "assets": sites,
        "jurisdiction_indicators": indicators,
    }

    network = gen_network(rng)
    assert_no_real_names(network, where="network")

    density = gen_density_bins(sites)
    centrality = gen_centrality()
    attribution = {
        "sources": [
            {
                "name": "Synthetic Municipal Records 01",
                "attribution": "© Synthetic Municipal Records — CC0-1.0 (invented fixture data)",
            },
            {
                "name": "Synthetic Regional Bulletins 02",
                "attribution": "© Synthetic Regional Bulletins — CC0-1.0 (invented fixture data)",
            },
        ]
    }
    assert_no_real_names(attribution, where="attribution")

    geojson = gen_geojson(sites)
    print(f"[national-fixture] rendering PMTiles over {len(sites)} sites…", flush=True)
    rendered = render_compartment_sites_pmtiles(COMPARTMENT, geojson, LICENSE_ID)
    print(
        f"[national-fixture] PMTiles renderer={rendered.renderer} bytes={len(rendered.data)}",
        flush=True,
    )
    # P35.52 (sig.map-tiles/2, ADR-156): the content-hashed archive name +
    # web/tiles/index.json + the source geojson the verifier replays.
    tile_path = f"web/tiles/{COMPARTMENT}-sites.{rendered.sha256[:8]}.pmtiles"
    tiles_index = canonical_json(
        tiles_index_document(
            [
                tiles_index_entry(
                    compartment=COMPARTMENT,
                    path=tile_path,
                    license_id=LICENSE_ID,
                    attribution=f"© The SIG project — {LICENSE_ID}",
                    rendered=rendered,
                    source=f"{COMPARTMENT}/sites.geojson",
                )
            ]
        )
    )

    files: dict[str, tuple[str, bytes]] = {
        "web/map.json": (COMPARTMENT, _dump_compact(map_doc)),
        "web/network.json": (COMPARTMENT, _dump_compact(network)),
        "web/analytics/density_bins.json": ("web", _dump(density)),
        "web/analytics/centrality.json": ("web", _dump(centrality)),
        tile_path: (COMPARTMENT, rendered.data),
        "web/tiles/index.json": ("web", tiles_index),
        f"{COMPARTMENT}/sites.geojson": (COMPARTMENT, geojson),
        f"{COMPARTMENT}/ATTRIBUTION.json": (COMPARTMENT, _dump(attribution)),
    }

    digests: dict[str, str] = {}
    artifacts: list[dict[str, Any]] = []
    for rel, (compartment, data) in files.items():
        digest = _write(out_dir / rel, data)
        digests[rel] = digest
        artifacts.append(
            {
                "path": rel,
                "compartment": compartment,
                "license": LICENSE_ID if compartment == COMPARTMENT else "CC-BY-4.0",
                "sha256": digest,
                "bytes": len(data),
            }
        )

    fixture_block = {
        "schema": SCHEMA,
        "seed": SEED,
        "synthetic": True,
        "invented_names_only": True,
        "focus_entity_id": FOCUS_ENTITY_ID,
        "counts": {
            "sites": len(sites),
            "locatable_sites": sum(1 for a in sites if a["lat"] is not None and a["tier"] != 3),
            "agencies": AGENCY_COUNT,
            "nodes": len(network["nodes"]),
            "sharing_edges": len(network["edges"]),
            "access_paths": len(network["access_paths"]),
        },
        "sha256": digests,
        "generator": "scripts/ci/build_national_fixture.py",
    }

    manifest = {
        "schema": "sig.export-manifest/1",
        "release_id": "syn-national-fixture",
        "reproducibility_inputs": {
            "as_of_snapshot": "2025-06-01T00:00:00Z",
            "as_of_belief": "2025-06-01T00:00:00Z",
            "ruleset_version": "national-fixture-1.0",
        },
        "artifacts": artifacts,
        "fixture": fixture_block,
    }
    digests["manifest.json"] = _write(out_dir / "manifest.json", _dump(manifest))
    digests["fixture.json"] = _write(out_dir / "fixture.json", _dump(fixture_block))
    return fixture_block


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "web" / "national",
        help="output directory (default: web/national — gitignored)",
    )
    args = ap.parse_args(argv)
    block = build(args.out)
    print(
        "[national-fixture] done: "
        f"{block['counts']['sites']} sites, "
        f"{block['counts']['nodes']} nodes, "
        f"{block['counts']['sharing_edges']} edges → {args.out}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
