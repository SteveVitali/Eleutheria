# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Fixture inputs for the P35.19 ``placement@1`` suite (K4 §3.3/§9, JUR-02b).

Like ``boundary_pack_fixtures`` these are **declared stand-ins** —
``build_pack`` runs with ``fixture_inputs=True`` so the manifest honestly
records ``gate.mode = "fixture-bypass"`` (``capture_kind: stand-in``; never
captured evidence). Unlike the P35.17 fixtures — whose one-degree boxes never
nest — every box here is drawn so the real containment hierarchy holds:
country ⊃ admin-1 ⊃ county ⊃ place, which is what a located chain needs.

The staged fixtures cover the contract's §7 set:

* **CA→FL** — a California-declared point inside the Florida box (R4,
  same-country ``outside_declared`` + the two-sided disclosure pair).
* **Cross-country** — a GB-declared point inside Indonesia (R4,
  ``outside_declared_country``).
* **MO/KS border** — a Missouri-declared point inside Kansas (R4, within
  country — the MoDOT-on-the-Kansas-side fixture).
* **on_boundary** — two Kansas counties share an overlap band; a point in it
  is a double hit resolved by the lowest-GEOID tie-break.
* **Coast tolerance** — Indonesia's box ends at lat 6.0; a point at 6.01 is a
  tolerance hit (NE ``+0.02°``), and a US-state point at the same offset is
  not (TIGER is full-resolution — no tolerance).
* **Nottingham swap** — the recorded ``(lat,lon)`` sits in no boundary while
  its swap lands inside the GB-ENG rollup (R3, ``axis_swap_suspected``).
* **GA/NZ sign flips** — a south-of-equator "Georgia" point and a
  north-of-equator "New Zealand" point flip back inside their declared
  boundaries (R3, ``sign_flip_suspected``).
* **ID/Indonesia + MN/Mongolia** — the two-way ISO/USPS keying fixtures.
* **Centerville** — two places with one name → ``name_ambiguous`` (R8).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _box(x0: float, y0: float, x1: float, y1: float) -> dict[str, Any]:
    """A lat/lon rectangle polygon — a stand-in, never surveyed."""
    return {
        "type": "Polygon",
        "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
    }


def _geojson(features: list[dict[str, Any]]) -> str:
    return json.dumps({"type": "FeatureCollection", "features": features}, sort_keys=True)


def _feat(props: dict[str, Any], box: tuple[float, float, float, float]) -> dict[str, Any]:
    return {"type": "Feature", "properties": props, "geometry": _box(*box)}


def _country(a2: str, a3: str, name: str, box: tuple[float, float, float, float]) -> dict:
    return _feat(
        {
            "ISO_A2_EH": a2,
            "ADM0_A3": a3,
            "NAME_EN": name,
            "NAME": name,
            "NAME_LONG": name,
            "NAME_SORT": name,
            "NAME_FR": name,
            "NAME_DE": name,
            "FORMAL_EN": name,
        },
        box,
    )


# --------------------------------------------------------------------------- #
# Countries (NE admin-0 stand-in) — the outermost boxes every state nests in.  #
# --------------------------------------------------------------------------- #

COUNTRIES = _geojson(
    [
        _country("US", "USA", "United States", (-125.0, 18.0, -66.0, 50.0)),
        _country("GB", "GBR", "United Kingdom", (-8.0, 49.5, 2.0, 60.0)),
        # Indonesia's northern edge at lat 6.0 drives the coast-tolerance
        # fixture: lat 6.01 is a tolerance hit, 6.05 is not.
        _country("ID", "IDN", "Indonesia", (95.0, -11.0, 141.0, 6.0)),
        _country("MN", "MNG", "Mongolia", (87.0, 41.0, 120.0, 52.0)),
        _country("NZ", "NZL", "New Zealand", (165.0, -48.0, 179.0, -33.0)),
    ]
)

# --------------------------------------------------------------------------- #
# US states (TIGER stand-in) — every box strictly inside the US country box.   #
# --------------------------------------------------------------------------- #

US_STATES = _geojson(
    [
        _feat(
            {"STUSPS": "CA", "GEOID": "06", "NAME": "California", "NAMELSAD": "California"},
            (-116.0, 33.0, -113.0, 36.0),
        ),
        _feat(
            {"STUSPS": "FL", "GEOID": "12", "NAME": "Florida", "NAMELSAD": "Florida"},
            (-83.0, 25.0, -80.0, 28.0),
        ),
        _feat(
            {"STUSPS": "GA", "GEOID": "13", "NAME": "Georgia", "NAMELSAD": "Georgia"},
            (-84.0, 31.0, -81.0, 34.0),
        ),
        _feat(
            {"STUSPS": "KS", "GEOID": "20", "NAME": "Kansas", "NAMELSAD": "Kansas"},
            (-98.0, 38.0, -95.0, 40.0),
        ),
        _feat(
            {"STUSPS": "MO", "GEOID": "29", "NAME": "Missouri", "NAMELSAD": "Missouri"},
            (-93.0, 38.0, -91.0, 40.0),
        ),
        _feat(
            {"STUSPS": "ID", "GEOID": "16", "NAME": "Idaho", "NAMELSAD": "Idaho"},
            (-114.0, 43.0, -111.0, 45.0),
        ),
        _feat(
            {"STUSPS": "MN", "GEOID": "27", "NAME": "Minnesota", "NAMELSAD": "Minnesota"},
            (-94.0, 45.0, -91.0, 47.0),
        ),
    ]
)

# --------------------------------------------------------------------------- #
# Counties — Verdin County sits inside California; the two Kansas counties    #
# overlap on the band x ∈ [-96.6, -96.5] so a point there is a double hit.    #
# --------------------------------------------------------------------------- #

US_COUNTIES = _geojson(
    [
        _feat(
            {
                "GEOID": "06037",
                "STATEFP": "06",
                "NAME": "Verdin",
                "NAMELSAD": "Verdin County",
            },
            (-115.5, 33.5, -114.5, 34.5),
        ),
        _feat(
            {
                "GEOID": "20100",
                "STATEFP": "20",
                "NAME": "Briar",
                "NAMELSAD": "Briar County",
            },
            (-97.2, 38.6, -96.5, 39.4),
        ),
        _feat(
            {
                "GEOID": "20101",
                "STATEFP": "20",
                "NAME": "Kaw",
                "NAMELSAD": "Kaw County",
            },
            (-96.6, 38.6, -96.0, 39.4),
        ),
    ]
)

# --------------------------------------------------------------------------- #
# Places — Verdin nests inside Verdin County; the two Centervilles are the    #
# name-ambiguity fixture (R8).                                                #
# --------------------------------------------------------------------------- #

US_PLACES = _geojson(
    [
        _feat(
            {
                "GEOID": "0644000",
                "STATEFP": "06",
                "NAME": "Verdin",
                "NAMELSAD": "Verdin city",
            },
            (-115.2, 33.8, -114.9, 34.2),
        ),
        _feat(
            {
                "GEOID": "0612670",
                "STATEFP": "06",
                "NAME": "Centerville",
                "NAMELSAD": "Centerville city",
            },
            (-114.4, 34.6, -114.1, 34.9),
        ),
        _feat(
            {
                "GEOID": "2012670",
                "STATEFP": "20",
                "NAME": "Centerville",
                "NAMELSAD": "Centerville city",
            },
            (-97.8, 38.1, -97.4, 38.4),
        ),
    ]
)

# --------------------------------------------------------------------------- #
# GB admin-1 (NE stand-in) — both units roll up to iso3166-2:GB-ENG via        #
# geonunit; the northern box covers the swapped Nottingham point.             #
# --------------------------------------------------------------------------- #

GB_ADMIN1 = _geojson(
    [
        _feat(
            {
                "iso_3166_2": "GB-XN1",
                "adm1_code": "GBR-1",
                "name": "Northern England",
                "name_en": "",
                "name_alt": "",
                "name_local": "",
                "geonunit": "England",
            },
            (-2.5, 52.5, -1.0, 54.5),
        ),
        _feat(
            {
                "iso_3166_2": "GB-XS1",
                "adm1_code": "GBR-2",
                "name": "Southern England",
                "name_en": "",
                "name_alt": "",
                "name_local": "",
                "geonunit": "England",
            },
            (-0.5, 51.0, 1.0, 52.0),
        ),
    ]
)

# --------------------------------------------------------------------------- #
# The spec — the sig.boundary-pack/1 vocabulary narrowed to the fixture set.   #
# --------------------------------------------------------------------------- #

PLACEMENT_SPEC_TOML = """\
[pack]
schema = "sig.boundary-pack/1"
pack_id = "boundaries-placement-fixture"

[pack.vintages]
tiger = "tiger-2025"
natural_earth = "ne-5.1"

[registry]
license = "CC-BY-4.0"
attribution = ["fixture stand-in upstreams — never captured evidence"]
standing_note = "fixture: placement@1 matrix stand-ins, capture_kind stand-in"

[[layers]]
id = "countries"
source = "fx_ne"
file = "countries.geojson"
format = "geojson"
role = "non_us"
vintage = "ne-5.1"
level = "country"
key_scheme = "iso3166-1"
[layers.fields]
code = "ISO_A2_EH"
iso3 = "ADM0_A3"
name = "NAME_EN"
alternates = ["NAME", "NAME_LONG", "NAME_SORT", "NAME_FR", "NAME_DE", "FORMAL_EN"]

[[layers]]
id = "us_states"
source = "fx_tiger"
file = "us_states.geojson"
format = "geojson"
role = "us_containment"
vintage = "tiger-2025"
level = "state_province"
key_scheme = "us.state_abbr"
[layers.fields]
code = "STUSPS"
geoid = "GEOID"
name = "NAME"
namelsad = "NAMELSAD"

[[layers]]
id = "us_counties"
source = "fx_tiger"
file = "us_counties.geojson"
format = "geojson"
role = "us_containment"
vintage = "tiger-2025"
level = "county"
key_scheme = "us.census.geoid.county"
[layers.fields]
geoid = "GEOID"
statefp = "STATEFP"
name = "NAME"
namelsad = "NAMELSAD"

[[layers]]
id = "us_places"
source = "fx_tiger"
file = "us_places.geojson"
format = "geojson"
role = "us_containment"
vintage = "tiger-2025"
level = "municipality"
key_scheme = "us.census.geoid.place"
[layers.fields]
geoid = "GEOID"
statefp = "STATEFP"
name = "NAME"
namelsad = "NAMELSAD"

[[layers]]
id = "gb_admin1"
source = "fx_ne"
file = "gb_admin1.geojson"
format = "geojson"
role = "non_us"
vintage = "ne-5.1"
level = "state_province"
key_scheme = "iso3166-2"
[layers.fields]
code = "iso_3166_2"
adm1_code = "adm1_code"
name = "name"
alternates = ["name_en", "name_alt", "name_local"]
[layers.rollup]
field = "geonunit"
prefix = "GB"
map = { "England" = "ENG" }
"""

PLACEMENT_INPUTS: dict[str, str] = {
    "countries.geojson": COUNTRIES,
    "us_states.geojson": US_STATES,
    "us_counties.geojson": US_COUNTIES,
    "us_places.geojson": US_PLACES,
    "gb_admin1.geojson": GB_ADMIN1,
}


@dataclass(frozen=True)
class PlacementEnv:
    """One built placement input set — spec + verified pack + bound registry."""

    spec_path: Path
    inputs_dir: Path
    pack_dir: Path
    manifest: dict[str, Any]
    registry_doc: dict[str, Any]
    registry_path: Path


def build_placement_env(root: Path) -> PlacementEnv:
    """Materialise spec + inputs, build the pack (fixture_inputs=True — the
    manifest honestly records the bypass), derive + persist the registry."""
    from exports import boundary_pack as bp
    from exports import jurisdictions as jr

    root = Path(root)
    inputs = root / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    for name, content in PLACEMENT_INPUTS.items():
        (inputs / name).write_text(content, encoding="utf-8")
    spec_path = root / "spec.toml"
    spec_path.write_text(PLACEMENT_SPEC_TOML, encoding="utf-8")
    spec = bp.load_spec(spec_path)
    pack_dir = root / "pack"
    manifest = bp.build_pack(spec, inputs, pack_dir, fixture_inputs=True)
    registry_doc = jr.build_registry(spec, pack_dir)
    registry_path = root / "jurisdictions.json"
    jr.write_registry(registry_doc, registry_path)
    return PlacementEnv(
        spec_path=spec_path,
        inputs_dir=inputs,
        pack_dir=pack_dir,
        manifest=manifest,
        registry_doc=registry_doc,
        registry_path=registry_path,
    )
