# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.52 (sig.map-tiles/2, ADR-156, K1-map §15 NEW-5): the deterministic
SYNTHETIC 50k-point tile-verify fixture — the dataset the CI verifier leg runs
`sig-exports tiles verify` against under the PINNED tippecanoe build.

Deliberate shapes (the checks need all of them):
  - clustered "cities"   — Gaussian clusters around invented metro centres;
  - co-located points    — several entities sharing an exact coordinate (the
                           old _DEDUP_CELL path would have coalesced them);
  - byte-identical pairs — two features with identical geometry+properties
                           (the ONLY dedupe the contract permits);
  - all tiled tiers      — tier 0/1/2 (tier-3 records publish no geometry and
                           are absent by construction — the verifier asserts
                           none slip through);
  - three compartments   — sig_graph (CC-BY-4.0), portal (CC-BY-SA-4.0),
                           osm_physical (ODbL-1.0) — one archive each, never a
                           licence-mixed public tile.

Determinism: one ``random.Random(SEED)`` drives every draw; two runs produce a
byte-identical tree. Every emitted name is invented. The fixture writes
nothing outside ``--out`` and mutates nothing.

Layout::

    <out>/
      manifest.json                 minimal release-shaped artifact list
      fixture.json                  sig.tile-fixture/1 provenance + sha256 map
      <comp>/sites.geojson          the source each archive verified against
      web/tiles/<comp>-sites.<sha8>.pmtiles
      web/tiles/index.json          the sig.map-tiles/2 index
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
sys.path.insert(0, str(REPO_ROOT / "exports" / "src"))
sys.path.insert(0, str(REPO_ROOT / "policy" / "src"))

from exports.manifest import canonical_json, tiles_index_document  # noqa: E402
from exports.tiles import (  # noqa: E402
    render_compartment_sites_pmtiles,
    tiles_index_entry,
)
from policy.sensitivity import apply_tier  # noqa: E402

SCHEMA = "sig.tile-fixture/1"
SEED = 35052052
TOTAL_POINTS = 50_000

#: (compartment, SPDX licence, share of the 50k located points, attribution)
COMPARTMENTS: tuple[tuple[str, str, float, str], ...] = (
    (
        "sig_graph",
        "CC-BY-4.0",
        0.60,
        "© Synthetic Tile Sources — CC-BY-4.0 (invented fixture data)",
    ),
    (
        "portal",
        "CC-BY-SA-4.0",
        0.24,
        "© Synthetic Portal Feeds — CC-BY-SA-4.0 (invented fixture data)",
    ),
    (
        "osm_physical",
        "ODbL-1.0",
        0.16,
        "© OpenStreetMap contributors (ODbL)",
    ),
)

#: Invented metro cluster centres (lat, lon) — a CONUS-ish spread so the low
#: zoom cells have realistic density contrast.
CLUSTER_CENTERS: tuple[tuple[float, float], ...] = (
    (35.4, -97.5),
    (32.7, -96.8),
    (41.8, -87.6),
    (40.7, -74.0),
    (34.0, -118.2),
    (29.7, -95.3),
    (39.7, -104.9),
    (33.4, -112.0),
    (47.6, -122.3),
    (42.3, -83.0),
)

_SOURCES = ("src:syn-tile-01", "src:syn-tile-02", "src:syn-tile-03")
#: Synthetic K4-form jurisdiction keys (invented GEOIDs — never a real place).
_JKEYS = tuple(
    f"us.census.geoid.place:{geoid:07d}" for geoid in (4805000, 4811000, 4835000, 4845000)
)


def gen_features(compartment: str, count: int, rng: random.Random) -> list[dict[str, Any]]:
    """``count`` synthetic located features for one compartment.

    Distribution: ~85 % clustered around a metro centre (~0.8°σ), ~15 % a
    wide rural spread; every 97th city point is co-located with its neighbour
    (distinct entity, exact coordinate — the never-coalesce case); every
    4093rd is a byte-identical twin of the previous feature (the only allowed
    dedupe). Tiers: ~55 % tier 0, ~30 % tier 1 (truncated on-grid via the real
    ``apply_tier``), ~15 % tier 2 (1000 m binned).
    """
    features: list[dict[str, Any]] = []
    prev: dict[str, Any] | None = None
    for i in range(count):
        center_lat, center_lon = CLUSTER_CENTERS[i % len(CLUSTER_CENTERS)]
        spread = 0.8 if rng.random() < 0.85 else 4.0
        # resample until inside the web-mercator domain — the renderer clamps
        # out-of-range latitudes at ±85.05 and the verifier rightfully fails
        # the fidelity check on a source point it can never reproduce.
        lat, lon = 90.0, 0.0
        while not (-85.0 <= lat <= 85.0 and -179.5 <= lon <= 179.5):
            lat = rng.gauss(center_lat, spread)
            lon = rng.gauss(center_lon, spread)
        tier_roll = rng.random()
        tier = 0 if tier_roll < 0.55 else (1 if tier_roll < 0.85 else 2)
        if i % 97 == 0 and features:
            # co-located: the EXACT published point of the previous feature,
            # a DIFFERENT entity at the same tier (the F-414 coalescing case
            # in miniature — and the coord must ride the previous point's
            # tier so a tier-1 feature stays on its truncation grid).
            prev_feat = features[-1]
            tier = int(prev_feat["properties"]["sensitivity_tier"])
            lon, lat = (
                prev_feat["geometry"]["coordinates"][0],
                prev_feat["geometry"]["coordinates"][1],
            )
        else:
            reduced = apply_tier(lat, lon, tier)
            assert reduced is not None, "tier 0–2 always reduce to a point"
            lat, lon = reduced
        props: dict[str, Any] = {
            "entity_id": f"{compartment}:syn-{i:06d}",
            "entity_type": "deployment",
            "sensitivity_tier": tier,
            "jurisdiction": _JKEYS[i % len(_JKEYS)],
            "source_ids": [_SOURCES[i % len(_SOURCES)]],
        }
        feat: dict[str, Any] = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props,
        }
        if i % 4093 == 0 and prev is not None:
            # byte-identical duplicate — the only pair the dedupe may collapse
            feat = json.loads(json.dumps(prev))
        features.append(feat)
        prev = feat
    return features


def _write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def build(out_dir: Path) -> dict[str, Any]:
    rng = random.Random(SEED)
    digests: dict[str, str] = {}
    artifacts: list[dict[str, Any]] = []
    index_entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for compartment, licence, share, attribution in COMPARTMENTS:
        n = int(TOTAL_POINTS * share)
        features = gen_features(compartment, n, rng)
        geojson = json.dumps(
            {"type": "FeatureCollection", "features": features},
            separators=(",", ":"),
        ).encode("utf-8")
        counts[compartment] = len(features)
        rel_src = f"{compartment}/sites.geojson"
        digests[rel_src] = _write(out_dir / rel_src, geojson)
        artifacts.append(
            {
                "path": rel_src,
                "compartment": compartment,
                "license": licence,
                "sha256": digests[rel_src],
                "bytes": len(geojson),
            }
        )
        rendered = render_compartment_sites_pmtiles(
            compartment, geojson, licence, attribution=attribution
        )
        tile_path = f"web/tiles/{compartment}-sites.{rendered.sha256[:8]}.pmtiles"
        digests[tile_path] = _write(out_dir / tile_path, rendered.data)
        artifacts.append(
            {
                "path": tile_path,
                "compartment": compartment,
                "license": licence,
                "sha256": digests[tile_path],
                "bytes": len(rendered.data),
            }
        )
        index_entries.append(
            tiles_index_entry(
                compartment=compartment,
                path=tile_path,
                license_id=licence,
                attribution=attribution,
                rendered=rendered,
                source=rel_src,
            )
        )
        print(
            f"[tile-fixture] {compartment}: {len(features)} features → "
            f"{tile_path} ({len(rendered.data)} B, {rendered.renderer})",
            flush=True,
        )

    index_bytes = canonical_json(tiles_index_document(index_entries))
    digests["web/tiles/index.json"] = _write(out_dir / "web/tiles/index.json", index_bytes)
    artifacts.append(
        {
            "path": "web/tiles/index.json",
            "compartment": "web",
            "license": "CC-BY-4.0",
            "sha256": digests["web/tiles/index.json"],
            "bytes": len(index_bytes),
        }
    )

    digests["manifest.json"] = _write(
        out_dir / "manifest.json",
        canonical_json(
            {
                "schema": "sig.export-manifest/1",
                "release_id": "syn-tile-fixture",
                "reproducibility_inputs": {
                    "as_of_snapshot": "2025-06-01T00:00:00Z",
                    "as_of_belief": "2025-06-01T00:00:00Z",
                    "ruleset_version": "tile-fixture-1.0",
                },
                "artifacts": artifacts,
            }
        ),
    )
    block = {
        "schema": SCHEMA,
        "seed": SEED,
        "synthetic": True,
        "invented_names_only": True,
        "counts": {"total_points": TOTAL_POINTS, "by_compartment": counts},
        "sha256": digests,
        "generator": "scripts/ci/build_tile_fixture.py",
    }
    _write(out_dir / "fixture.json", canonical_json(block))
    return block


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="output directory")
    args = ap.parse_args(argv)
    block = build(args.out)
    print(
        f"[tile-fixture] done: {block['counts']} → {args.out}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
